//! JSONL-based derived view store.
//!
//! Stores views in `.openlocus/derived/views.jsonl` and an audit log in
//! `.openlocus/derived/audit.jsonl`. Supports upsert, list, and purge.

use crate::model::DerivedIndexView;
use anyhow::Result;
use std::fs;
use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};

const VIEWS_FILENAME: &str = "views.jsonl";
const AUDIT_FILENAME: &str = "audit.jsonl";
const DERIVED_DIR: &str = "derived";

/// Result of listing views from the JSONL store.
#[derive(Debug)]
pub struct ListResult {
    pub views: Vec<DerivedIndexView>,
    pub parse_errors: usize,
}

/// JSONL-based derived view store.
pub struct JsonlDerivedViewStore {
    views_path: PathBuf,
    audit_path: PathBuf,
}

impl JsonlDerivedViewStore {
    /// Create a store rooted under `.openlocus/derived/` in the repo.
    pub fn new(repo_root: &Path) -> Self {
        let derived_dir = repo_root.join(".openlocus").join(DERIVED_DIR);
        Self {
            views_path: derived_dir.join(VIEWS_FILENAME),
            audit_path: derived_dir.join(AUDIT_FILENAME),
        }
    }

    /// Ensure the derived directory exists.
    fn ensure_dir(&self) -> Result<()> {
        if let Some(parent) = self.views_path.parent() {
            fs::create_dir_all(parent)?;
        }
        Ok(())
    }

    /// Upsert views: replace existing views with same view_id, append new ones.
    /// Returns (upserted_count, replaced_count).
    pub fn upsert(&self, views: &[DerivedIndexView]) -> Result<(usize, usize)> {
        self.ensure_dir()?;

        // Read existing views
        let existing = self.list()?;
        let mut existing_map: std::collections::HashMap<String, DerivedIndexView> = existing
            .into_iter()
            .map(|v| (v.view_id.clone(), v))
            .collect();

        let mut replaced = 0usize;
        for view in views {
            if existing_map
                .insert(view.view_id.clone(), view.clone())
                .is_some()
            {
                replaced += 1;
            }
        }

        // Write all views back
        let mut file = fs::File::create(&self.views_path)?;
        for view in existing_map.values() {
            writeln!(file, "{}", serde_json::to_string(view)?)?;
        }

        let upserted = views.len();
        // Audit entry
        self.append_audit("upsert", upserted, replaced)?;

        Ok((upserted, replaced))
    }

    /// List all views from the JSONL file.
    /// Silently skips parse errors (use list_with_errors for error reporting).
    pub fn list(&self) -> Result<Vec<DerivedIndexView>> {
        Ok(self.list_with_errors()?.views)
    }

    /// List all views from the JSONL file, also returning parse error count.
    pub fn list_with_errors(&self) -> Result<ListResult> {
        if !self.views_path.exists() {
            return Ok(ListResult {
                views: Vec::new(),
                parse_errors: 0,
            });
        }

        let file = fs::File::open(&self.views_path)?;
        let reader = std::io::BufReader::new(file);
        let mut views = Vec::new();
        let mut parse_errors = 0usize;

        for line in reader.lines() {
            let line = line?;
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            match serde_json::from_str::<DerivedIndexView>(trimmed) {
                Ok(view) => views.push(view),
                Err(_) => {
                    parse_errors += 1;
                }
            }
        }

        Ok(ListResult {
            views,
            parse_errors,
        })
    }

    /// Purge all stored views and audit log.
    /// Returns number of views purged.
    pub fn purge(&self) -> Result<usize> {
        let count = self.list()?.len();

        if self.views_path.exists() {
            fs::remove_file(&self.views_path)?;
        }
        if self.audit_path.exists() {
            fs::remove_file(&self.audit_path)?;
        }

        // Remove directory if empty
        if let Some(parent) = self.views_path.parent()
            && parent.exists()
            && fs::read_dir(parent)?.next().is_none()
        {
            fs::remove_dir(parent)?;
        }

        Ok(count)
    }

    /// Get the views file path.
    pub fn views_path(&self) -> &Path {
        &self.views_path
    }

    /// Get the audit file path.
    pub fn audit_path(&self) -> &Path {
        &self.audit_path
    }

    fn append_audit(&self, action: &str, count: usize, replaced: usize) -> Result<()> {
        self.ensure_dir()?;
        let mut file = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.audit_path)?;
        let entry = serde_json::json!({
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "action": action,
            "count": count,
            "replaced": replaced,
        });
        writeln!(file, "{}", serde_json::to_string(&entry)?)?;
        Ok(())
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{DerivedGeneratorKind, DerivedProvenance, DerivedSource, DerivedViewKind};

    fn make_view(id_suffix: &str, path: &str, sha: &str) -> DerivedIndexView {
        let source = DerivedSource {
            path: path.to_string(),
            start_line: 1,
            end_line: 10,
            content_sha: sha.to_string(),
            language: "rust".to_string(),
        };
        let view_id = DerivedIndexView::compute_view_id(
            &source,
            &DerivedViewKind::ChunkSummary,
            &DerivedGeneratorKind::RuleExtractor,
            1,
            "local_only",
            "0.1.0",
        );
        DerivedIndexView {
            view_id: format!("{}-{}", view_id, id_suffix),
            kind: DerivedViewKind::ChunkSummary,
            source,
            derived_text: format!("test-{}", id_suffix),
            tags: vec![],
            provenance: DerivedProvenance {
                generator: DerivedGeneratorKind::RuleExtractor,
                generator_version: "0.1.0".to_string(),
                remote_calls: 0,
                policy_mode: "local_only".to_string(),
                data_level: 1,
            },
            validation: None,
        }
    }

    #[test]
    fn upsert_and_list() {
        let dir = tempfile::tempdir().unwrap();
        let store = JsonlDerivedViewStore::new(dir.path());

        let v1 = make_view("1", "lib.rs", "sha1");
        let v2 = make_view("2", "main.rs", "sha2");

        let (upserted, replaced) = store.upsert(&[v1.clone(), v2.clone()]).unwrap();
        assert_eq!(upserted, 2);
        assert_eq!(replaced, 0);

        let views = store.list().unwrap();
        assert_eq!(views.len(), 2);
    }

    #[test]
    fn upsert_replaces_existing() {
        let dir = tempfile::tempdir().unwrap();
        let store = JsonlDerivedViewStore::new(dir.path());

        let v1 = make_view("1", "lib.rs", "sha1");
        store.upsert(std::slice::from_ref(&v1)).unwrap();

        // Upsert with same view_id but different text
        let mut v1_updated = v1.clone();
        v1_updated.derived_text = "updated".to_string();
        let (upserted, replaced) = store.upsert(&[v1_updated]).unwrap();
        assert_eq!(upserted, 1);
        assert_eq!(replaced, 1);

        let views = store.list().unwrap();
        assert_eq!(views.len(), 1);
        assert_eq!(views[0].derived_text, "updated");
    }

    #[test]
    fn purge_removes_artifacts() {
        let dir = tempfile::tempdir().unwrap();
        let store = JsonlDerivedViewStore::new(dir.path());

        let v1 = make_view("1", "lib.rs", "sha1");
        store.upsert(&[v1]).unwrap();
        assert!(store.views_path().exists());

        let purged = store.purge().unwrap();
        assert_eq!(purged, 1);
        assert!(!store.views_path().exists());
        assert!(!store.audit_path().exists());
    }

    #[test]
    fn list_empty_store() {
        let dir = tempfile::tempdir().unwrap();
        let store = JsonlDerivedViewStore::new(dir.path());
        let views = store.list().unwrap();
        assert!(views.is_empty());
    }

    #[test]
    fn corrupt_jsonl_yields_parse_errors() {
        let dir = tempfile::tempdir().unwrap();
        let store = JsonlDerivedViewStore::new(dir.path());

        // Write a valid view first
        let v1 = make_view("1", "lib.rs", "sha1");
        store.upsert(&[v1]).unwrap();

        // Append a corrupt line to the JSONL file
        use std::io::Write;
        let mut f = fs::OpenOptions::new()
            .append(true)
            .open(store.views_path())
            .unwrap();
        writeln!(f, "THIS IS NOT VALID JSON").unwrap();

        let result = store.list_with_errors().unwrap();
        assert_eq!(result.views.len(), 1); // valid view still readable
        assert_eq!(result.parse_errors, 1); // corrupt line counted
    }
}
