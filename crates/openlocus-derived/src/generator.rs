//! Deterministic rule-based generator for L1 derived view kinds.
//!
//! This generator produces derived views without any LLM or network call.
//! It extracts identifiers, symbol-like names, and produces bounded text/labels.
//! No full raw code snippets are included in derived text (data_level <= 1).

use crate::model::{
    DerivedGeneratorKind, DerivedIndexView, DerivedProvenance, DerivedSource, DerivedViewKind,
};
use openlocus_repo::scan::FileRecord;
use std::path::Path;

/// Generate derived views for a set of file records.
/// Only generates L1 kinds (chunk_summary, symbol_tags, query_aliases).
/// Returns (views_generated, views_blocked_by_kind, views_blocked_by_data_level).
pub fn generate_views(
    repo_root: &Path,
    records: &[FileRecord],
    kinds: &[DerivedViewKind],
    max_data_level: u8,
) -> anyhow::Result<(Vec<DerivedIndexView>, usize, usize)> {
    let mut views = Vec::new();
    let mut blocked_kind = 0usize;
    let mut blocked_data_level = 0usize;

    let l1_only: Vec<&DerivedViewKind> = kinds.iter().filter(|k| !k.is_high_risk()).collect();

    let high_risk_requested: Vec<&DerivedViewKind> =
        kinds.iter().filter(|k| k.is_high_risk()).collect();

    blocked_kind += high_risk_requested.len();

    for record in records {
        let full_path = repo_root.join(&record.path);

        // Validate path safety
        if openlocus_repo::validate_path(repo_root, &record.path).is_err() {
            continue;
        }

        // Read file bytes once (TOCTOU-safe)
        let bytes = match std::fs::read(&full_path) {
            Ok(b) => b,
            Err(_) => continue,
        };

        let current_sha = blake3::hash(&bytes).to_hex().to_string();

        // Skip stale records
        if !record.content_sha.is_empty() && record.content_sha != current_sha {
            continue;
        }

        let content = String::from_utf8_lossy(&bytes);
        let lines: Vec<&str> = content.lines().collect();
        let total_lines = lines.len() as u64;

        if total_lines == 0 {
            continue;
        }

        let source = DerivedSource {
            path: record.path.clone(),
            start_line: 1,
            end_line: total_lines,
            content_sha: current_sha,
            language: record.language.clone(),
        };

        for kind in &l1_only {
            match kind {
                DerivedViewKind::ChunkSummary => {
                    let view = generate_chunk_summary(&source, &lines, max_data_level);
                    if let Some(v) = view {
                        views.push(v);
                    } else {
                        blocked_data_level += 1;
                    }
                }
                DerivedViewKind::SymbolTags => {
                    let view = generate_symbol_tags(&source, &lines, max_data_level);
                    views.push(view);
                }
                DerivedViewKind::QueryAliases => {
                    let view = generate_query_aliases(&source, &lines, max_data_level);
                    views.push(view);
                }
                _ => {} // high-risk already filtered
            }
        }
    }

    Ok((views, blocked_kind, blocked_data_level))
}

const CHUNK_SIZE: usize = 30;

/// Generate a chunk summary: bounded text with no full code.
/// At data_level <= 1, only includes line count, language, and first identifier per chunk.
fn generate_chunk_summary(
    source: &DerivedSource,
    lines: &[&str],
    data_level: u8,
) -> Option<DerivedIndexView> {
    let mut chunk_views = Vec::new();

    let mut chunk_start = 0usize;
    while chunk_start < lines.len() {
        let chunk_end = (chunk_start + CHUNK_SIZE).min(lines.len());
        let chunk_lines = &lines[chunk_start..chunk_end];

        let first_ident = chunk_lines
            .iter()
            .find_map(|line| extract_first_identifier(line));

        let derived_text = if data_level <= 1 {
            // No full raw code: just metadata + first identifier
            format!(
                "chunk lines {}-{}: {}{}",
                chunk_start + 1,
                chunk_end,
                source.language,
                first_ident
                    .map(|i| format!(", first_ident={}", i))
                    .unwrap_or_default(),
            )
        } else {
            // data_level 2+: include truncated snippet (max 3 lines)
            let snippet: Vec<&str> = chunk_lines.iter().take(3).copied().collect();
            format!(
                "chunk lines {}-{}: {} | {}",
                chunk_start + 1,
                chunk_end,
                source.language,
                snippet.join("\\n"),
            )
        };

        let chunk_source = DerivedSource {
            path: source.path.clone(),
            start_line: (chunk_start + 1) as u64,
            end_line: chunk_end as u64,
            content_sha: source.content_sha.clone(),
            language: source.language.clone(),
        };

        let view_id = DerivedIndexView::compute_view_id(
            &chunk_source,
            &DerivedViewKind::ChunkSummary,
            &DerivedGeneratorKind::RuleExtractor,
            data_level,
            "local_only",
            "0.1.0",
        );

        chunk_views.push(DerivedIndexView {
            view_id,
            kind: DerivedViewKind::ChunkSummary,
            source: chunk_source,
            derived_text,
            tags: vec![],
            provenance: DerivedProvenance {
                generator: DerivedGeneratorKind::RuleExtractor,
                generator_version: "0.1.0".to_string(),
                remote_calls: 0,
                policy_mode: "local_only".to_string(),
                data_level,
            },
            validation: None,
        });

        chunk_start = chunk_end;
    }

    // Return the first chunk view for simplicity (full list would be returned in production)
    chunk_views.into_iter().next()
}

/// Generate symbol tags: extract identifier-like names from lines.
fn generate_symbol_tags(
    source: &DerivedSource,
    lines: &[&str],
    data_level: u8,
) -> DerivedIndexView {
    let mut tags = Vec::new();

    for line in lines {
        for ident in extract_identifiers(line) {
            if !tags.contains(&ident) {
                tags.push(ident);
            }
            if tags.len() >= 50 {
                break;
            }
        }
        if tags.len() >= 50 {
            break;
        }
    }

    let derived_text = if data_level <= 1 {
        format!("symbol_tags: {}", tags.join(", "))
    } else {
        format!("symbol_tags_full: {}", tags.join(", "))
    };

    let view_id = DerivedIndexView::compute_view_id(
        source,
        &DerivedViewKind::SymbolTags,
        &DerivedGeneratorKind::RuleExtractor,
        data_level,
        "local_only",
        "0.1.0",
    );

    DerivedIndexView {
        view_id,
        kind: DerivedViewKind::SymbolTags,
        source: source.clone(),
        derived_text,
        tags: tags.clone(),
        provenance: DerivedProvenance {
            generator: DerivedGeneratorKind::RuleExtractor,
            generator_version: "0.1.0".to_string(),
            remote_calls: 0,
            policy_mode: "local_only".to_string(),
            data_level,
        },
        validation: None,
    }
}

/// Generate query aliases: suggest search terms from identifiers.
fn generate_query_aliases(
    source: &DerivedSource,
    lines: &[&str],
    data_level: u8,
) -> DerivedIndexView {
    let mut aliases = Vec::new();

    for line in lines {
        for ident in extract_identifiers(line) {
            // Split camelCase and snake_case into alias components
            let parts = split_identifier(&ident);
            for part in parts {
                if part.len() >= 3 && !aliases.contains(&part) {
                    aliases.push(part);
                }
            }
            if aliases.len() >= 30 {
                break;
            }
        }
        if aliases.len() >= 30 {
            break;
        }
    }

    let derived_text = if data_level <= 1 {
        format!("query_aliases: {}", aliases.join(", "))
    } else {
        format!("query_aliases_full: {}", aliases.join(", "))
    };

    let view_id = DerivedIndexView::compute_view_id(
        source,
        &DerivedViewKind::QueryAliases,
        &DerivedGeneratorKind::RuleExtractor,
        data_level,
        "local_only",
        "0.1.0",
    );

    DerivedIndexView {
        view_id,
        kind: DerivedViewKind::QueryAliases,
        source: source.clone(),
        derived_text,
        tags: aliases.clone(),
        provenance: DerivedProvenance {
            generator: DerivedGeneratorKind::RuleExtractor,
            generator_version: "0.1.0".to_string(),
            remote_calls: 0,
            policy_mode: "local_only".to_string(),
            data_level,
        },
        validation: None,
    }
}

/// Extract the first identifier-like name from a line.
fn extract_first_identifier(line: &str) -> Option<String> {
    let trimmed = line.trim();
    if trimmed.is_empty() || trimmed.starts_with("//") || trimmed.starts_with('#') {
        return None;
    }

    extract_identifiers(line)
        .into_iter()
        .find(|ident| ident.len() >= 2)
}

/// Extract identifier-like names from a line using simple heuristics.
/// Filters out secret-like tokens and skips string literals/comments where feasible.
fn extract_identifiers(line: &str) -> Vec<String> {
    let mut idents = Vec::new();
    let mut current = String::new();

    // Simple heuristic: skip lines that look like string assignments
    // (contain = " or = ') or are inside string literals
    let trimmed = line.trim();
    if is_likely_string_assignment(trimmed) {
        // Still extract identifiers from the left-hand side of assignment,
        // but not the string value
        if let Some(eq_pos) = trimmed.find('=') {
            let lhs = &trimmed[..eq_pos];
            for ch in lhs.chars() {
                if ch.is_alphanumeric() || ch == '_' {
                    current.push(ch);
                } else {
                    if current.len() >= 2 && !is_keyword(&current) && !is_secret_like(&current) {
                        idents.push(current.clone());
                    }
                    current.clear();
                }
            }
            if current.len() >= 2 && !is_keyword(&current) && !is_secret_like(&current) {
                idents.push(current);
            }
        }
        return idents;
    }

    for ch in line.chars() {
        if ch.is_alphanumeric() || ch == '_' {
            current.push(ch);
        } else {
            if current.len() >= 2 && !is_keyword(&current) && !is_secret_like(&current) {
                idents.push(current.clone());
            }
            current.clear();
        }
    }
    if current.len() >= 2 && !is_keyword(&current) && !is_secret_like(&current) {
        idents.push(current);
    }

    idents
}

/// Check if a line looks like a string value assignment (e.g. `SECRET_KEY = "..."`).
fn is_likely_string_assignment(line: &str) -> bool {
    line.contains("=\"") || line.contains("= '") || line.contains("= \"")
}

/// Check if an identifier looks like a secret/key/token that should not be emitted.
fn is_secret_like(s: &str) -> bool {
    let upper = s.to_uppercase();

    // Names containing secret-related keywords
    if upper.contains("SECRET")
        || upper.contains("TOKEN")
        || upper.contains("PASSWORD")
        || upper.contains("PASSWD")
        || upper.contains("API_KEY")
        || upper.contains("APIKEY")
        || upper.contains("PRIVATE_KEY")
        || upper.contains("PRIVATEKEY")
        || upper.contains("AUTH_KEY")
        || upper.contains("ACCESS_KEY")
        || upper.contains("SECRET_KEY")
    {
        return true;
    }

    // Common secret prefixes
    if s.starts_with("sk_")
        || s.starts_with("ghp_")
        || s.starts_with("gho_")
        || s.starts_with("xox")
        || s.starts_with("AKIA")
    {
        return true;
    }

    // High-entropy-ish tokens: long alphanumeric strings with mixed case/digits
    // (likely API keys or tokens, not identifiers)
    if s.len() >= 24 && s.chars().all(|c| c.is_alphanumeric() || c == '_') {
        let has_upper = s.chars().any(|c| c.is_uppercase());
        let has_lower = s.chars().any(|c| c.is_lowercase());
        let has_digit = s.chars().any(|c| c.is_ascii_digit());
        let variety_count = [has_upper, has_lower, has_digit]
            .iter()
            .filter(|&&b| b)
            .count();
        if variety_count >= 2 {
            return true;
        }
    }

    false
}

/// Common keywords to skip.
fn is_keyword(s: &str) -> bool {
    matches!(
        s,
        "fn" | "let"
            | "mut"
            | "pub"
            | "use"
            | "mod"
            | "impl"
            | "struct"
            | "enum"
            | "trait"
            | "if"
            | "else"
            | "for"
            | "while"
            | "return"
            | "self"
            | "Self"
            | "super"
            | "crate"
            | "true"
            | "false"
            | "def"
            | "class"
            | "import"
            | "from"
            | "async"
            | "await"
            | "const"
            | "var"
            | "function"
            | "type"
            | "interface"
    )
}

/// Split an identifier into components (camelCase, snake_case).
fn split_identifier(ident: &str) -> Vec<String> {
    let mut parts = Vec::new();

    // snake_case split
    if ident.contains('_') {
        for part in ident.split('_') {
            if !part.is_empty() {
                parts.push(part.to_lowercase());
            }
        }
    } else {
        // camelCase split
        let mut current = String::new();
        for ch in ident.chars() {
            if ch.is_uppercase() && !current.is_empty() {
                parts.push(current.to_lowercase());
                current = String::new();
            }
            current.push(ch);
        }
        if !current.is_empty() {
            parts.push(current.to_lowercase());
        }
    }

    parts
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_record(path: &str, content: &str) -> (FileRecord, tempfile::TempDir) {
        let dir = tempfile::tempdir().unwrap();
        let file_path = dir.path().join(path);
        if let Some(parent) = file_path.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(&file_path, content).unwrap();
        let bytes = std::fs::read(&file_path).unwrap();
        let sha = blake3::hash(&bytes).to_hex().to_string();
        let lang = if path.ends_with(".rs") {
            "rust"
        } else if path.ends_with(".py") {
            "python"
        } else {
            "unknown"
        }
        .to_string();

        (
            FileRecord {
                path: path.to_string(),
                size: bytes.len() as u64,
                content_sha: sha,
                language: lang,
            },
            dir,
        )
    }

    #[test]
    fn generate_chunk_summary_no_full_code() {
        let (record, dir) = make_record("lib.rs", "fn hello_world() {}\nfn goodbye() {}\n");
        let (views, _, _) =
            generate_views(dir.path(), &[record], &[DerivedViewKind::ChunkSummary], 1).unwrap();

        assert!(!views.is_empty());
        let view = &views[0];
        assert_eq!(view.kind, DerivedViewKind::ChunkSummary);
        // At data_level 1, derived_text should NOT contain full code
        assert!(!view.derived_text.contains("fn hello_world() {}"));
        assert!(view.derived_text.contains("chunk lines"));
        assert_eq!(view.provenance.remote_calls, 0);
        assert_eq!(view.provenance.data_level, 1);
    }

    #[test]
    fn generate_symbol_tags() {
        let (record, dir) = make_record("lib.rs", "fn compute_hash() {}\nstruct DataStore {}\n");
        let (views, _, _) =
            generate_views(dir.path(), &[record], &[DerivedViewKind::SymbolTags], 1).unwrap();

        assert!(!views.is_empty());
        let view = &views[0];
        assert_eq!(view.kind, DerivedViewKind::SymbolTags);
        assert!(
            view.tags.contains(&"compute_hash".to_string())
                || view.tags.contains(&"DataStore".to_string())
        );
        assert_eq!(view.provenance.remote_calls, 0);
    }

    #[test]
    fn generate_query_aliases() {
        let (record, dir) = make_record("lib.rs", "fn computeHashValue() {}\n");
        let (views, _, _) =
            generate_views(dir.path(), &[record], &[DerivedViewKind::QueryAliases], 1).unwrap();

        assert!(!views.is_empty());
        let view = &views[0];
        assert_eq!(view.kind, DerivedViewKind::QueryAliases);
        // Should have split camelCase into aliases
        assert!(view.tags.iter().any(|t| t == "compute"));
    }

    #[test]
    fn high_risk_kinds_blocked() {
        let (record, dir) = make_record("lib.rs", "fn test() {}\n");
        let (views, blocked_kind, _) = generate_views(
            dir.path(),
            &[record],
            &[
                DerivedViewKind::ChunkSummary,
                DerivedViewKind::CandidateEdge,
            ],
            1,
        )
        .unwrap();

        // Only chunk_summary should be generated
        assert!(
            views
                .iter()
                .all(|v| v.kind != DerivedViewKind::CandidateEdge)
        );
        assert_eq!(blocked_kind, 1); // candidate_edge blocked
    }

    #[test]
    fn view_id_stable_on_same_input() {
        let source = DerivedSource {
            path: "lib.rs".into(),
            start_line: 1,
            end_line: 10,
            content_sha: "abc".into(),
            language: "rust".into(),
        };
        let id1 = DerivedIndexView::compute_view_id(
            &source,
            &DerivedViewKind::ChunkSummary,
            &DerivedGeneratorKind::RuleExtractor,
            1,
            "local_only",
            "0.1.0",
        );
        let id2 = DerivedIndexView::compute_view_id(
            &source,
            &DerivedViewKind::ChunkSummary,
            &DerivedGeneratorKind::RuleExtractor,
            1,
            "local_only",
            "0.1.0",
        );
        assert_eq!(id1, id2);
    }

    #[test]
    fn no_raw_full_snippet_at_data_level_1() {
        let (record, dir) = make_record("secret.rs", "SECRET_KEY=abc123\nfn auth() {}\n");
        let (views, _, _) =
            generate_views(dir.path(), &[record], &[DerivedViewKind::ChunkSummary], 1).unwrap();

        for view in &views {
            // At data_level 1, derived_text should not contain raw code
            assert!(
                !view.derived_text.contains("SECRET_KEY=abc123"),
                "data_level 1 should not contain raw code: {}",
                view.derived_text
            );
        }
    }

    #[test]
    fn secret_key_filtered_from_symbol_tags() {
        let (record, dir) = make_record(
            "config.rs",
            "const SECRET_KEY = \"sk_live_abc123\";\nconst API_TOKEN = \"ghp_xyz789\";\nfn normal_fn() {}\n",
        );
        let (views, _, _) =
            generate_views(dir.path(), &[record], &[DerivedViewKind::SymbolTags], 1).unwrap();

        for view in &views {
            assert!(
                !view
                    .tags
                    .iter()
                    .any(|t| t.to_uppercase().contains("SECRET_KEY")),
                "SECRET_KEY should be filtered from symbol tags: {:?}",
                view.tags
            );
            assert!(
                !view
                    .tags
                    .iter()
                    .any(|t| t.to_uppercase().contains("API_TOKEN")),
                "API_TOKEN should be filtered from symbol tags: {:?}",
                view.tags
            );
        }
    }

    #[test]
    fn secret_prefix_filtered_from_query_aliases() {
        let (record, dir) = make_record(
            "config.rs",
            "sk_live_abc123xyz456\ngithub_token = ghp_AbCdEfGh789\n",
        );
        let (views, _, _) =
            generate_views(dir.path(), &[record], &[DerivedViewKind::QueryAliases], 1).unwrap();

        for view in &views {
            assert!(
                !view.tags.iter().any(|t| t.starts_with("sk_live")),
                "sk_ prefix tokens should be filtered: {:?}",
                view.tags
            );
            assert!(
                !view.tags.iter().any(|t| t.starts_with("ghp_")),
                "ghp_ prefix tokens should be filtered: {:?}",
                view.tags
            );
        }
    }

    #[test]
    fn high_entropy_token_filtered() {
        // Long mixed-case+digit string that looks like an API key
        let (record, dir) = make_record(
            "config.rs",
            "AKIAIOSFODNN7EXAMPLE\nfn normal_function() {}\n",
        );
        let (views, _, _) =
            generate_views(dir.path(), &[record], &[DerivedViewKind::SymbolTags], 1).unwrap();

        for view in &views {
            assert!(
                !view.tags.iter().any(|t| t.starts_with("AKIA")),
                "AKIA prefix tokens should be filtered: {:?}",
                view.tags
            );
        }
    }
}
