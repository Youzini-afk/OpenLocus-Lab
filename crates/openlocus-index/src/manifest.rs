//! Manifest for persistent BM25 index.
//!
//! Tracks schema_version, file/chunk counts, policy hash, and per-file
//! metadata (path, content_sha, size_bytes, language, indexed/skipped_reason).

use anyhow::{Context, Result};
use openlocus_core::Policy;
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Current schema version for R7 persistent BM25 index.
pub const SCHEMA_VERSION: &str = "r7-bm25-v1";

/// Relative path to the index directory within .openlocus.
pub const INDEX_DIR_RELATIVE: &str = ".openlocus/index";

/// Relative path to the Tantivy index data.
pub const TANTIVY_DIR_RELATIVE: &str = ".openlocus/index/tantivy";

/// Relative path to the manifest file.
pub const MANIFEST_PATH_RELATIVE: &str = ".openlocus/index/manifest.json";

/// Per-file entry in the manifest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestFileEntry {
    pub path: String,
    pub content_sha: String,
    pub size_bytes: u64,
    pub language: String,
    /// "indexed" or "skipped"
    pub status: String,
    /// None for indexed files; Some(reason) for skipped files
    #[serde(skip_serializing_if = "Option::is_none")]
    pub skipped_reason: Option<String>,
}

/// Index manifest tracking all indexed files and policy hash.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexManifest {
    pub schema_version: String,
    pub file_count: u64,
    pub chunk_count: u64,
    pub policy_hash: String,
    pub files: Vec<ManifestFileEntry>,
}

impl IndexManifest {
    /// Create a new manifest with the given fields.
    pub fn new(policy_hash: String, files: Vec<ManifestFileEntry>, chunk_count: u64) -> Self {
        let file_count = files.iter().filter(|f| f.status == "indexed").count() as u64;
        Self {
            schema_version: SCHEMA_VERSION.to_string(),
            file_count,
            chunk_count,
            policy_hash,
            files,
        }
    }

    /// Load manifest from the repo's .openlocus/index/manifest.json.
    pub fn load(repo_root: &Path) -> Result<Self> {
        let path = repo_root.join(MANIFEST_PATH_RELATIVE);
        let content =
            std::fs::read_to_string(&path).with_context(|| "failed to read manifest.json")?;
        let manifest: IndexManifest =
            serde_json::from_str(&content).with_context(|| "failed to parse manifest.json")?;
        Ok(manifest)
    }

    /// Save manifest to the repo's .openlocus/index/manifest.json.
    pub fn save(&self, repo_root: &Path) -> Result<()> {
        let path = repo_root.join(MANIFEST_PATH_RELATIVE);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let content =
            serde_json::to_string_pretty(self).with_context(|| "failed to serialize manifest")?;
        std::fs::write(&path, content).with_context(|| "failed to write manifest.json")?;
        Ok(())
    }

    /// Check if the manifest exists.
    pub fn exists(repo_root: &Path) -> bool {
        repo_root.join(MANIFEST_PATH_RELATIVE).exists()
    }
}

/// Compute a policy hash from the policy TOML representation.
/// Uses blake3 of the canonical TOML serialization.
pub fn compute_policy_hash(policy: &Policy) -> String {
    // Serialize policy to TOML for a stable, canonical representation
    let toml_str = toml::to_string(policy).unwrap_or_default();
    blake3::hash(toml_str.as_bytes()).to_hex().to_string()
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manifest_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let manifest = IndexManifest::new(
            "fake_policy_hash".to_string(),
            vec![
                ManifestFileEntry {
                    path: "src/main.rs".into(),
                    content_sha: "abc123".into(),
                    size_bytes: 100,
                    language: "rust".into(),
                    status: "indexed".into(),
                    skipped_reason: None,
                },
                ManifestFileEntry {
                    path: ".env".into(),
                    content_sha: "def456".into(),
                    size_bytes: 50,
                    language: "unknown".into(),
                    status: "skipped".into(),
                    skipped_reason: Some("policy excluded".into()),
                },
            ],
            5,
        );

        manifest.save(root).unwrap();
        let loaded = IndexManifest::load(root).unwrap();

        assert_eq!(loaded.schema_version, SCHEMA_VERSION);
        assert_eq!(loaded.file_count, 1); // only indexed files
        assert_eq!(loaded.chunk_count, 5);
        assert_eq!(loaded.files.len(), 2);
        assert_eq!(loaded.policy_hash, "fake_policy_hash");
    }

    #[test]
    fn manifest_exists_check() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        assert!(!IndexManifest::exists(root));

        let manifest = IndexManifest::new("hash".into(), vec![], 0);
        manifest.save(root).unwrap();

        assert!(IndexManifest::exists(root));
    }

    #[test]
    fn policy_hash_deterministic() {
        let p1 = Policy::default();
        let p2 = Policy::default();
        assert_eq!(compute_policy_hash(&p1), compute_policy_hash(&p2));
    }

    #[test]
    fn policy_hash_changes_with_policy() {
        let p1 = Policy::default();
        let mut p2 = Policy::default();
        p2.remote.allow = true;
        assert_ne!(compute_policy_hash(&p1), compute_policy_hash(&p2));
    }
}
