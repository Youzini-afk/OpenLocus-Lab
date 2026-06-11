//! Simple heuristic symbol extraction and search.
//!
//! Supports Rust (struct/enum/trait/fn/impl), Python (def/class),
//! TypeScript/JavaScript (function/class/const/export), Go (func/type).
//! Returns narrow Evidence around the signature line. Uses Channel::Regex
//! with why="simple_symbol" since we're not using a real TreeSitter parser.
//! Fills meta.symbol where extraction succeeds.
//!
//! Symbol name patterns use word-boundary delimiters to prevent
//! partial matches (e.g. "User" should not match "UserProfile").

use anyhow::Result;
use openlocus_core::{Channel, Evidence, Freshness, Symbol, SymbolKind};
use openlocus_repo::scan::FileRecord;
use regex::Regex;
use std::path::Path;

/// Search for symbol definitions matching a query.
/// Returns one Evidence per matching symbol definition, with narrow span
/// around the signature/head line.
pub fn symbol_search(
    repo_root: &Path,
    records: &[FileRecord],
    query: &str,
    max_results: usize,
) -> Result<Vec<Evidence>> {
    let mut results = Vec::new();

    for record in records {
        if results.len() >= max_results {
            break;
        }

        let full_path = repo_root.join(&record.path);
        let content = match std::fs::read_to_string(&full_path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let content_sha = blake3::hash(content.as_bytes()).to_hex().to_string();
        let lines: Vec<&str> = content.lines().collect();

        // Build patterns appropriate for this file's language
        let patterns = build_symbol_patterns(query, &record.language);

        for (i, line) in lines.iter().enumerate() {
            if results.len() >= max_results {
                break;
            }
            let line_num = (i + 1) as u64;

            for (re, kind) in &patterns {
                if let Some(caps) = re.captures(line) {
                    let name = caps
                        .name("name")
                        .map(|m| m.as_str().to_string())
                        .unwrap_or_else(|| query.to_string());

                    // Narrow span: just the signature line
                    let start = line_num;
                    let end = line_num;

                    let excerpt = line.to_string();

                    let evidence = Evidence::new(
                        &record.path,
                        start,
                        end,
                        &content_sha,
                        1.0,
                        vec![format!("simple_symbol: {}", name)],
                        vec![Channel::Regex],
                    )
                    .with_excerpt(&excerpt)
                    .with_language(&record.language)
                    .with_freshness(Freshness::VerifiedCurrent)
                    .with_symbol(Symbol {
                        name,
                        kind: kind.clone(),
                        qualified_name: None,
                        symbol_id: None,
                    });

                    results.push(evidence);
                }
            }
        }
    }

    Ok(results)
}

/// Build symbol patterns for matching definitions, filtered by language.
/// The query is matched as the symbol name with a word-boundary delimiter
/// to prevent partial matches (e.g. "User" won't match "UserProfile").
///
/// Since the Rust `regex` crate doesn't support lookahead, we match the
/// name followed by a non-identifier character or end-of-string using
/// an alternation pattern.
fn build_symbol_patterns(query: &str, language: &str) -> Vec<(Regex, SymbolKind)> {
    let q = regex::escape(query);
    let mut pats = Vec::new();

    let lang = language.to_lowercase();

    // Boundary: the name must be followed by a non-identifier char or end-of-line.
    // Since Rust regex doesn't support lookahead, we capture the name and require
    // it's followed by a non-identifier character or is at end of line.
    // Pattern: (?P<name>{q})(?:[^a-zA-Z0-9_]|$)
    let boundary = r"(?:[^a-zA-Z0-9_]|$)";

    // Rust patterns
    if lang == "rust" || lang == "unknown" {
        if let Ok(re) = Regex::new(&format!(
            r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(?P<name>{q}){boundary}"
        )) {
            pats.push((re, SymbolKind::Function));
        }
        if let Ok(re) = Regex::new(&format!(r"^\s*(?:pub\s+)?struct\s+(?P<name>{q}){boundary}")) {
            pats.push((re, SymbolKind::Class));
        }
        if let Ok(re) = Regex::new(&format!(r"^\s*(?:pub\s+)?enum\s+(?P<name>{q}){boundary}")) {
            pats.push((re, SymbolKind::Type));
        }
        if let Ok(re) = Regex::new(&format!(r"^\s*(?:pub\s+)?trait\s+(?P<name>{q}){boundary}")) {
            pats.push((re, SymbolKind::Interface));
        }
        if let Ok(re) = Regex::new(&format!(
            r"^\s*impl(?:<[^>]*>)?\s+(?:\w+\s+for\s+)?(?P<name>{q}){boundary}"
        )) {
            pats.push((re, SymbolKind::Class));
        }
    }

    // Python patterns
    if lang == "python" || lang == "unknown" {
        if let Ok(re) = Regex::new(&format!(r"^\s*def\s+(?P<name>{q}){boundary}")) {
            pats.push((re, SymbolKind::Function));
        }
        if let Ok(re) = Regex::new(&format!(r"^\s*class\s+(?P<name>{q}){boundary}")) {
            pats.push((re, SymbolKind::Class));
        }
    }

    // TypeScript/JavaScript patterns
    if lang == "typescript" || lang == "javascript" || lang == "unknown" {
        if let Ok(re) = Regex::new(&format!(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+(?P<name>{q}){boundary}"
        )) {
            pats.push((re, SymbolKind::Function));
        }
        if let Ok(re) = Regex::new(&format!(
            r"^\s*(?:export\s+)?class\s+(?P<name>{q}){boundary}"
        )) {
            pats.push((re, SymbolKind::Class));
        }
        if let Ok(re) = Regex::new(&format!(
            r"^\s*(?:export\s+)?const\s+(?P<name>{q}){boundary}"
        )) {
            pats.push((re, SymbolKind::Variable));
        }
    }

    // Go patterns
    if lang == "go" || lang == "unknown" {
        if let Ok(re) = Regex::new(&format!(
            r"^\s*func\s+(?:\([^)]*\)\s+)?(?P<name>{q}){boundary}"
        )) {
            pats.push((re, SymbolKind::Function));
        }
        if let Ok(re) = Regex::new(&format!(r"^\s*type\s+(?P<name>{q}){boundary}\s+struct")) {
            pats.push((re, SymbolKind::Class));
        }
        if let Ok(re) = Regex::new(&format!(r"^\s*type\s+(?P<name>{q}){boundary}\s+interface")) {
            pats.push((re, SymbolKind::Interface));
        }
    }

    pats
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn symbol_search_finds_rust_fn() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("main.rs"),
            "fn authenticate() {}\nfn other() {}\n",
        )
        .unwrap();

        let records = vec![FileRecord {
            path: "main.rs".into(),
            size: 0,
            content_sha: "unused".into(),
            language: "rust".into(),
        }];

        let results = symbol_search(root, &records, "authenticate", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].core.start_line, 1);
        assert_eq!(results[0].core.end_line, 1);
        let sym = results[0].meta.as_ref().unwrap().symbol.as_ref().unwrap();
        assert_eq!(sym.name, "authenticate");
        assert_eq!(sym.kind, SymbolKind::Function);
    }

    #[test]
    fn symbol_search_finds_struct() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("types.rs"),
            "pub struct EvidenceCore {\n    path: String,\n}\n",
        )
        .unwrap();

        let records = vec![FileRecord {
            path: "types.rs".into(),
            size: 0,
            content_sha: "unused".into(),
            language: "rust".into(),
        }];

        let results = symbol_search(root, &records, "EvidenceCore", 10).unwrap();
        assert_eq!(results.len(), 1);
        let sym = results[0].meta.as_ref().unwrap().symbol.as_ref().unwrap();
        assert_eq!(sym.name, "EvidenceCore");
        assert_eq!(sym.kind, SymbolKind::Class);
    }

    #[test]
    fn symbol_search_narrow_span() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("app.rs"),
            "// comment\nfn my_func() {}\n// other\n",
        )
        .unwrap();

        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: "unused".into(),
            language: "rust".into(),
        }];

        let results = symbol_search(root, &records, "my_func", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].core.start_line, 2);
        assert_eq!(
            results[0].core.end_line, 2,
            "symbol evidence should be narrow (single line)"
        );
    }

    #[test]
    fn symbol_search_python_class() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("models.py"), "class User:\n    pass\n").unwrap();

        let records = vec![FileRecord {
            path: "models.py".into(),
            size: 0,
            content_sha: "unused".into(),
            language: "python".into(),
        }];

        let results = symbol_search(root, &records, "User", 10).unwrap();
        assert_eq!(results.len(), 1);
        let sym = results[0].meta.as_ref().unwrap().symbol.as_ref().unwrap();
        assert_eq!(sym.name, "User");
        assert_eq!(sym.kind, SymbolKind::Class);
    }

    #[test]
    fn symbol_search_content_sha_from_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let content = "fn my_func() {}\n";
        std::fs::write(root.join("app.rs"), content).unwrap();

        let expected_sha = blake3::hash(content.as_bytes()).to_hex().to_string();

        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: "stale".into(),
            language: "rust".into(),
        }];

        let results = symbol_search(root, &records, "my_func", 10).unwrap();
        assert_eq!(results[0].core.content_sha, expected_sha);
    }

    #[test]
    fn symbol_boundary_prevents_partial_match() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        // "User" should NOT match "UserProfile"
        std::fs::write(
            root.join("models.rs"),
            "struct UserProfile {\n    name: String,\n}\nstruct User {\n    id: u32,\n}\n",
        )
        .unwrap();

        let records = vec![FileRecord {
            path: "models.rs".into(),
            size: 0,
            content_sha: "unused".into(),
            language: "rust".into(),
        }];

        let results = symbol_search(root, &records, "User", 10).unwrap();
        // Should only find "User", not "UserProfile"
        assert_eq!(results.len(), 1, "boundary should prevent partial match");
        let sym = results[0].meta.as_ref().unwrap().symbol.as_ref().unwrap();
        assert_eq!(sym.name, "User");
        assert_eq!(
            results[0].core.start_line, 4,
            "should match struct User at line 4"
        );
    }

    #[test]
    fn symbol_boundary_fn_partial() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        // "get" should NOT match "get_user"
        std::fs::write(root.join("api.rs"), "fn get_user() {}\nfn get() {}\n").unwrap();

        let records = vec![FileRecord {
            path: "api.rs".into(),
            size: 0,
            content_sha: "unused".into(),
            language: "rust".into(),
        }];

        let results = symbol_search(root, &records, "get", 10).unwrap();
        // Should only find "fn get()" at line 2, not "fn get_user()" at line 1
        assert_eq!(results.len(), 1, "boundary should prevent fn partial match");
        assert_eq!(results[0].core.start_line, 2);
    }

    #[test]
    fn symbol_pattern_matches_basic() {
        let boundary = r"(?:[^a-zA-Z0-9_]|$)";
        let q = regex::escape("authenticate");
        let pat = format!(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(?P<name>{q}){boundary}");
        let re = Regex::new(&pat).expect("pattern should compile");
        let caps = re.captures("fn authenticate() {}");
        assert!(caps.is_some(), "pattern should match, pattern was: {}", pat);
        let caps = caps.unwrap();
        assert_eq!(caps.name("name").unwrap().as_str(), "authenticate");
        // Should NOT match "fn authenticate_user()"
        let caps2 = re.captures("fn authenticate_user() {}");
        assert!(caps2.is_none(), "boundary should prevent partial match");
    }
}
