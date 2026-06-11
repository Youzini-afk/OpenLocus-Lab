//! BM25 search over bounded line chunks using Tantivy.
//!
//! Builds an in-temp Tantivy index from scanned file records, indexes content
//! in bounded chunks (max ~30 lines), then returns Evidence tightened to the
//! best-matching line ±2 context, capped at 7 lines.
//!
//! Key design decisions:
//! - Each chunk hit is line-scored against query tokens; chunk center is never
//!   used as the span anchor. If no query token overlap exists in the chunk,
//!   the hit is skipped (precision-biased).
//! - content_sha from index time is compared to current file hash; stale hits
//!   are skipped.
//! - Line range is strictly guarded: 1 ≤ start ≤ end ≤ total_lines.

use anyhow::Result;
use openlocus_core::{Channel, Evidence, Freshness, ScoreParts};
use openlocus_repo::scan::FileRecord;
use std::path::Path;
use tantivy::collector::TopDocs;
use tantivy::query::QueryParser;
use tantivy::schema::*;
use tantivy::{Index, ReloadPolicy, doc};

/// Maximum chunk size in lines for indexing.
const MAX_CHUNK_LINES: u64 = 30;
/// Context lines around a matching center for tightened evidence.
const CONTEXT_LINES: u64 = 2;
/// Maximum evidence span in lines.
const MAX_EVIDENCE_SPAN: u64 = 7;

/// BM25 search over scanned files. Returns Evidence with Channel::Bm25,
/// narrow spans (≤7 lines), content_sha from current file, and excerpt.
///
/// Span selection: for each Tantivy chunk hit, we score each line within the
/// chunk's original range by query token overlap. The best-scoring line
/// becomes the center, ± CONTEXT_LINES, capped at MAX_EVIDENCE_SPAN.
/// If no line has any query token overlap, the hit is skipped entirely.
pub fn bm25_search(
    repo_root: &Path,
    records: &[FileRecord],
    query: &str,
    max_results: usize,
) -> Result<Vec<Evidence>> {
    let mut schema_builder = Schema::builder();

    let path_field = schema_builder.add_text_field("path", STRING | STORED);
    let language_field = schema_builder.add_text_field("language", STRING | STORED);
    let content_sha_field = schema_builder.add_text_field("content_sha", STRING | STORED);
    let start_line_field = schema_builder.add_u64_field("start_line", STORED);
    let end_line_field = schema_builder.add_u64_field("end_line", STORED);
    let content_field = schema_builder.add_text_field("content", TEXT | STORED);

    let schema = schema_builder.build();

    let temp_dir = tempfile::tempdir()?;
    let index = Index::create_in_dir(temp_dir.path(), schema)?;
    let mut index_writer = index.writer(50_000_000)?;

    // Index chunks from files
    for record in records {
        let full_path = repo_root.join(&record.path);
        let content = match std::fs::read_to_string(&full_path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let lines: Vec<&str> = content.lines().collect();
        let total_lines = lines.len() as u64;

        // Create bounded chunks
        let mut chunk_start = 0u64;
        while chunk_start < total_lines {
            let chunk_end = (chunk_start + MAX_CHUNK_LINES).min(total_lines);
            let chunk_content = lines[chunk_start as usize..chunk_end as usize].join("\n");

            index_writer.add_document(doc!(
                path_field => record.path.as_str(),
                language_field => record.language.as_str(),
                content_sha_field => record.content_sha.as_str(),
                start_line_field => chunk_start + 1, // 1-indexed
                end_line_field => chunk_end,
                content_field => chunk_content.as_str(),
            ))?;

            chunk_start = chunk_end;
        }
    }

    index_writer.commit()?;

    let reader = index
        .reader_builder()
        .reload_policy(ReloadPolicy::Manual)
        .try_into()?;
    let searcher = reader.searcher();

    // Parse query with a precision-biased fallback. Never fall back to `*`,
    // because all-doc fallback creates citation-valid but semantically empty
    // evidence candidates.
    let query_parser = QueryParser::for_index(&index, vec![content_field]);
    let parsed_query = match query_parser.parse_query(query) {
        Ok(parsed) => parsed,
        Err(_) => {
            let sanitized = query.replace([':', '/', '(', ')', '"'], " ");
            match query_parser.parse_query(sanitized.trim()) {
                Ok(parsed) => parsed,
                Err(_) => return Ok(Vec::new()),
            }
        }
    };

    let top_docs = searcher.search(&parsed_query, &TopDocs::with_limit(max_results * 2))?;

    // Tokenize query for line-level scoring
    let query_tokens = tokenize_query(query);

    let mut results = Vec::new();

    for (_score, doc_address) in top_docs {
        if results.len() >= max_results {
            break;
        }

        let doc: TantivyDocument = searcher.doc(doc_address)?;
        let path_val = doc
            .get_first(path_field)
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let index_content_sha = doc
            .get_first(content_sha_field)
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let chunk_start_line = doc
            .get_first(start_line_field)
            .and_then(|v| v.as_u64())
            .unwrap_or(1);
        let chunk_end_line = doc
            .get_first(end_line_field)
            .and_then(|v| v.as_u64())
            .unwrap_or(1);
        let language_val = doc
            .get_first(language_field)
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string();

        // Re-read the current file
        let full_path = repo_root.join(&path_val);
        let content = match std::fs::read_to_string(&full_path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let current_content_sha = blake3::hash(content.as_bytes()).to_hex().to_string();

        // Stale check: skip if index-time hash doesn't match current file
        if !index_content_sha.is_empty() && index_content_sha != current_content_sha {
            continue;
        }

        let lines: Vec<&str> = content.lines().collect();
        let total_lines = lines.len() as u64;

        // Guard: if file shrank, skip
        if total_lines == 0 {
            continue;
        }

        // Clamp chunk range to current file bounds
        let effective_start = chunk_start_line.min(total_lines);
        let effective_end = chunk_end_line.min(total_lines);
        if effective_start > effective_end {
            continue;
        }

        // Line-level scoring: find the best-matching line in the chunk range
        let best_line =
            find_best_matching_line(&lines, effective_start, effective_end, &query_tokens);

        // If no query token overlap, skip this hit (precision-biased)
        let best_line = match best_line {
            Some(l) => l,
            None => continue,
        };

        // Tighten around best line ± context, cap at MAX_EVIDENCE_SPAN
        let tight_start = best_line.saturating_sub(CONTEXT_LINES).max(1);
        let mut tight_end = (best_line + CONTEXT_LINES).min(total_lines);

        // Cap span at MAX_EVIDENCE_SPAN
        tight_end = tight_end.min(tight_start + MAX_EVIDENCE_SPAN - 1);
        // Ensure tight_start stays valid after cap
        let tight_start = tight_start.max(1);
        let tight_end = tight_end.min(total_lines);

        // Strict guard: 1 ≤ start ≤ end ≤ total_lines
        if tight_start < 1 || tight_start > tight_end || tight_end > total_lines {
            continue;
        }

        let excerpt = lines[(tight_start - 1) as usize..tight_end as usize].join("\n");

        let bm25_score = _score as f64;

        let evidence = Evidence::new(
            &path_val,
            tight_start,
            tight_end,
            &current_content_sha,
            bm25_score,
            vec![format!("bm25 match: {}", query)],
            vec![Channel::Bm25],
        )
        .with_excerpt(&excerpt)
        .with_language(&language_val)
        .with_freshness(Freshness::VerifiedCurrent)
        .with_score_parts(ScoreParts {
            bm25: Some(bm25_score),
            ..Default::default()
        });

        results.push(evidence);
    }

    Ok(results)
}

/// Tokenize a query into lowercase tokens, filtering out short noise words
/// and field-syntax-like tokens.
fn tokenize_query(query: &str) -> Vec<String> {
    query
        .split(|c: char| {
            c.is_whitespace() || c == ':' || c == '/' || c == '"' || c == '(' || c == ')'
        })
        .map(|t| t.trim().to_lowercase())
        .filter(|t| t.len() >= 2 && !t.starts_with('_'))
        .collect()
}

/// Find the line within [start_line, end_line] (1-indexed) that has the
/// highest query token overlap score. Returns None if no line has any overlap.
fn find_best_matching_line(
    lines: &[&str],
    start_line: u64,
    end_line: u64,
    query_tokens: &[String],
) -> Option<u64> {
    if query_tokens.is_empty() {
        return None;
    }

    let mut best_score: u32 = 0;
    let mut best_line: Option<u64> = None;

    for line_num in start_line..=end_line {
        let idx = (line_num - 1) as usize;
        if idx >= lines.len() {
            break;
        }
        let line_lower = lines[idx].to_lowercase();
        let mut score: u32 = 0;
        for token in query_tokens {
            if line_lower.contains(token.as_str()) {
                score += 1;
            }
        }
        if score > best_score {
            best_score = score;
            best_line = Some(line_num);
        }
    }

    // Only return if there was actual token overlap
    if best_score > 0 { best_line } else { None }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    /// Helper: compute content_sha for a file at root/path
    fn compute_sha(root: &Path, path: &str) -> String {
        let bytes = std::fs::read(root.join(path)).unwrap();
        blake3::hash(&bytes).to_hex().to_string()
    }

    #[test]
    fn bm25_finds_matching_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(
            root.join("app.rs"),
            "fn authenticate_user() {}\nfn process_request() {}\n",
        )
        .unwrap();
        std::fs::write(
            root.join("lib.rs"),
            "struct Config {\n    name: String,\n}\n",
        )
        .unwrap();

        let records = vec![
            FileRecord {
                path: "app.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "app.rs"),
                language: "rust".into(),
            },
            FileRecord {
                path: "lib.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "lib.rs"),
                language: "rust".into(),
            },
        ];

        let results = bm25_search(root, &records, "authenticate", 10).unwrap();
        assert!(!results.is_empty(), "should find matches");
        let first = &results[0];
        assert_eq!(first.core.path, "app.rs");
        assert_eq!(first.core.channels[0], Channel::Bm25);
        // Span should be bounded
        let span = first.core.end_line - first.core.start_line + 1;
        assert!(
            span <= MAX_EVIDENCE_SPAN,
            "span should be <= {}, got {}",
            MAX_EVIDENCE_SPAN,
            span
        );
    }

    #[test]
    fn bm25_content_sha_from_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let content = "fn authenticate() {}\n";
        std::fs::write(root.join("auth.rs"), content).unwrap();

        let expected_sha = blake3::hash(content.as_bytes()).to_hex().to_string();

        // Use matching content_sha so the stale check doesn't skip this hit
        let records = vec![FileRecord {
            path: "auth.rs".into(),
            size: 0,
            content_sha: expected_sha.clone(),
            language: "rust".into(),
        }];

        let results = bm25_search(root, &records, "authenticate", 10).unwrap();
        if !results.is_empty() {
            assert_eq!(
                results[0].core.content_sha, expected_sha,
                "content_sha should come from current file"
            );
        }
    }

    #[test]
    fn bm25_stale_check_skips_hash_mismatch() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Write file, compute sha
        let content = "fn authenticate() {}\n";
        std::fs::write(root.join("auth.rs"), content).unwrap();

        // Use WRONG content_sha in record (simulating stale index)
        let records = vec![FileRecord {
            path: "auth.rs".into(),
            size: 0,
            content_sha: "definitely_wrong_sha".into(),
            language: "rust".into(),
        }];

        let results = bm25_search(root, &records, "authenticate", 10).unwrap();
        // Stale hit should be skipped entirely
        assert!(
            results.is_empty(),
            "BM25 should skip hits where index-time sha doesn't match current file"
        );
    }

    #[test]
    fn bm25_span_bounded() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Create a file with many lines where "authentication" appears throughout
        let mut content = String::new();
        for i in 1..=100 {
            content.push_str(&format!(
                "line {} has important data about authentication\n",
                i
            ));
        }
        std::fs::write(root.join("big.rs"), content).unwrap();

        let records = vec![FileRecord {
            path: "big.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "big.rs"),
            language: "rust".into(),
        }];

        let results = bm25_search(root, &records, "authentication", 10).unwrap();
        for ev in &results {
            let span = ev.core.end_line - ev.core.start_line + 1;
            assert!(
                span <= MAX_EVIDENCE_SPAN,
                "evidence span {} exceeds max {}",
                span,
                MAX_EVIDENCE_SPAN
            );
        }
    }

    #[test]
    fn bm25_freshness_is_verified_current() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("test.rs"), "fn hello() {}\n").unwrap();

        let records = vec![FileRecord {
            path: "test.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "test.rs"),
            language: "rust".into(),
        }];

        let results = bm25_search(root, &records, "hello", 10).unwrap();
        if let Some(ev) = results.first() {
            assert_eq!(
                ev.meta.as_ref().unwrap().freshness,
                Some(Freshness::VerifiedCurrent)
            );
        }
    }

    #[test]
    fn bm25_skips_chunk_with_no_token_overlap() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // File with "apple" — query "banana" should not return chunk center
        std::fs::write(root.join("fruit.rs"), "fn apple() {}\nfn orange() {}\n").unwrap();

        let records = vec![FileRecord {
            path: "fruit.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "fruit.rs"),
            language: "rust".into(),
        }];

        let results = bm25_search(root, &records, "banana", 10).unwrap();
        // "banana" has no token overlap with the file content
        assert!(
            results.is_empty(),
            "BM25 should skip chunks with no query token overlap"
        );
    }

    #[test]
    fn bm25_parse_failure_does_not_return_all_docs() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("alpha.rs"), "fn alpha() {}\n").unwrap();

        let records = vec![FileRecord {
            path: "alpha.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "alpha.rs"),
            language: "rust".into(),
        }];

        let results = bm25_search(root, &records, "\"", 10).unwrap();
        assert!(
            results.is_empty(),
            "parse failures must not fall back to all-document retrieval"
        );
    }

    #[test]
    fn bm25_line_guard_prevents_invalid_range() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // One-line file
        std::fs::write(root.join("tiny.rs"), "fn tiny() {}\n").unwrap();

        let records = vec![FileRecord {
            path: "tiny.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "tiny.rs"),
            language: "rust".into(),
        }];

        let results = bm25_search(root, &records, "tiny", 10).unwrap();
        for ev in &results {
            assert!(ev.core.start_line >= 1, "start_line must be >= 1");
            assert!(
                ev.core.start_line <= ev.core.end_line,
                "start_line must be <= end_line"
            );
            assert!(
                ev.core.end_line <= 1,
                "end_line must be <= total_lines for 1-line file"
            );
        }
    }

    #[test]
    fn tokenize_query_filters_noise() {
        let tokens = tokenize_query("field:term OR other");
        assert!(tokens.contains(&"term".to_string()));
        assert!(tokens.contains(&"other".to_string()));
        // "or" is >= 2 chars so it passes — that's fine for BM25
        assert!(!tokens.iter().any(|t| t.is_empty()));
    }
}
