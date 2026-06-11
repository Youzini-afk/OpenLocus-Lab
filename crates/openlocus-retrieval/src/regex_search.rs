use anyhow::Result;
use openlocus_core::{Channel, Evidence, Freshness};
use openlocus_repo::scan::FileRecord;
use regex::Regex;
use std::path::Path;

/// Search scanned files with a regex pattern, returning one Evidence per matching line.
///
/// This is a line-based regex search only. Multiline patterns (patterns that span
/// across line boundaries, e.g. containing `\n`) are NOT supported. Each matching
/// line produces its own narrow Evidence with start_line == end_line. If you need
/// multiline regex or cross-line matching, that requires a different implementation.
///
/// `records` should come from a prior scan; `repo_root` is used to read file content.
/// Limits results to `max_results` (default 100).
/// content_sha is computed from the actual file bytes (not reused from scan).
pub fn regex_search(
    repo_root: &Path,
    records: &[FileRecord],
    pattern: &str,
    max_results: usize,
) -> Result<Vec<Evidence>> {
    let re = Regex::new(pattern)?;
    do_search(
        repo_root,
        records,
        |line| re.is_match(line),
        pattern,
        max_results,
        "regex",
    )
}

/// Search scanned files with a plain text query (regex-escaped), returning one Evidence per matching line.
///
/// Line-based only, same semantics as `regex_search`. The query is regex-escaped
/// so special characters are treated literally.
pub fn text_search(
    repo_root: &Path,
    records: &[FileRecord],
    query: &str,
    max_results: usize,
) -> Result<Vec<Evidence>> {
    let escaped = regex::escape(query);
    let re = Regex::new(&escaped)?;
    do_search(
        repo_root,
        records,
        |line| re.is_match(line),
        query,
        max_results,
        "text",
    )
}

/// Core search implementation: line-based. Each matching line produces its own Evidence
/// with start_line == end_line (narrow single-line span). This avoids returning a huge
/// range from first match to last match within a file.
fn do_search<F>(
    repo_root: &Path,
    records: &[FileRecord],
    matcher: F,
    query: &str,
    max_results: usize,
    channel_name: &str,
) -> Result<Vec<Evidence>>
where
    F: Fn(&str) -> bool,
{
    let mut results = Vec::new();
    let channel = Channel::Regex;

    for record in records {
        if results.len() >= max_results {
            break;
        }

        let full_path = repo_root.join(&record.path);

        let content = match std::fs::read_to_string(&full_path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        // Compute content_sha from actual file bytes, not from scan record.
        // This ensures the hash matches the content we actually read.
        let content_sha = blake3::hash(content.as_bytes()).to_hex().to_string();

        for (i, line) in content.lines().enumerate() {
            if results.len() >= max_results {
                break;
            }
            if matcher(line) {
                let line_num = (i + 1) as u64;
                let evidence = Evidence::new(
                    &record.path,
                    line_num,
                    line_num,
                    &content_sha,
                    1.0,
                    vec![format!("{} match: {}", channel_name, query)],
                    vec![channel.clone()],
                )
                .with_excerpt(line)
                .with_language(&record.language)
                .with_freshness(Freshness::VerifiedCurrent);

                results.push(evidence);
            }
        }
    }

    Ok(results)
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use openlocus_repo::scan::FileRecord;

    /// Two matching lines far apart in the same file should produce
    /// two separate Evidence items, each with a narrow single-line span.
    #[test]
    fn distant_matches_return_separate_evidence() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Line 1 and line 1001 both match, far apart
        let mut content = String::from("fn main() {}\n");
        for i in 2..=1000 {
            content.push_str(&format!("// line {}\n", i));
        }
        content.push_str("fn helper() {}\n");
        std::fs::write(root.join("app.rs"), content).unwrap();

        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: "unused".into(),
            language: "rust".into(),
        }];

        let results = regex_search(root, &records, r"fn \w+", 100).unwrap();
        assert_eq!(results.len(), 2, "should find exactly 2 matches");
        // First match at line 1
        assert_eq!(results[0].core.start_line, 1);
        assert_eq!(
            results[0].core.end_line, 1,
            "span should be narrow (single line)"
        );
        // Second match at line 1001
        assert_eq!(results[1].core.start_line, 1001);
        assert_eq!(
            results[1].core.end_line, 1001,
            "span should be narrow (single line)"
        );
    }

    #[test]
    fn regex_search_finds_matches() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("app.rs"), "fn main() {}\nfn helper() {}\n").unwrap();
        std::fs::write(root.join("readme.txt"), "no code here\n").unwrap();

        let records = vec![
            FileRecord {
                path: "app.rs".into(),
                size: 28,
                content_sha: "sha1".into(),
                language: "rust".into(),
            },
            FileRecord {
                path: "readme.txt".into(),
                size: 14,
                content_sha: "sha2".into(),
                language: "unknown".into(),
            },
        ];

        let results = regex_search(root, &records, r"fn \w+", 100).unwrap();
        assert_eq!(
            results.len(),
            2,
            "each matching line is a separate Evidence"
        );
        assert_eq!(results[0].core.path, "app.rs");
        assert_eq!(results[0].core.start_line, 1);
        assert_eq!(results[0].core.end_line, 1);
        assert_eq!(results[1].core.start_line, 2);
        assert_eq!(results[1].core.end_line, 2);
    }

    #[test]
    fn text_search_escapes_query() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("data.txt"), "price is $5.00\nno match\n").unwrap();

        let records = vec![FileRecord {
            path: "data.txt".into(),
            size: 24,
            content_sha: "sha".into(),
            language: "unknown".into(),
        }];

        let results = text_search(root, &records, "$5.00", 100).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].core.start_line, 1);
        assert_eq!(results[0].core.end_line, 1);
    }

    #[test]
    fn search_respects_limit() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.txt"), "hello\n").unwrap();
        std::fs::write(root.join("b.txt"), "hello\n").unwrap();
        std::fs::write(root.join("c.txt"), "hello\n").unwrap();

        let records = vec![
            FileRecord {
                path: "a.txt".into(),
                size: 6,
                content_sha: "s1".into(),
                language: "unknown".into(),
            },
            FileRecord {
                path: "b.txt".into(),
                size: 6,
                content_sha: "s2".into(),
                language: "unknown".into(),
            },
            FileRecord {
                path: "c.txt".into(),
                size: 6,
                content_sha: "s3".into(),
                language: "unknown".into(),
            },
        ];

        let results = text_search(root, &records, "hello", 2).unwrap();
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn search_computes_content_sha_from_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let content = "hello world\n";
        std::fs::write(root.join("greet.txt"), content).unwrap();

        let expected_sha = blake3::hash(content.as_bytes()).to_hex().to_string();

        let records = vec![FileRecord {
            path: "greet.txt".into(),
            size: 12,
            content_sha: "stale_scan_sha".into(), // intentionally wrong
            language: "unknown".into(),
        }];

        let results = text_search(root, &records, "hello", 100).unwrap();
        assert_eq!(results.len(), 1);
        // content_sha should come from actual file, not scan record
        assert_eq!(results[0].core.content_sha, expected_sha);
    }
}
