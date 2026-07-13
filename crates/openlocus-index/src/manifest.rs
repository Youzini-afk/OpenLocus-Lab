//! Manifest for persistent BM25 index.
//!
//! Tracks schema_version, file/chunk counts, policy hash, and per-file
//! metadata (path, content_sha, size_bytes, language, indexed/skipped_reason).
//!
//! R8 adds `chunk_strategy` and AST stats to the manifest.
//! Schema version `r8-bm25-v2` is required for AST-built indexes.
//! The manifest loader refuses indexes with unrecognized schema versions
//! or chunk strategies.

use anyhow::{Context, Result, bail};
use openlocus_core::Policy;
use serde::{Deserialize, Serialize};
use std::path::Path;

use crate::path_safety;

/// Current schema version for R8 persistent BM25 index.
pub const SCHEMA_VERSION: &str = "r8-bm25-v2";

/// Legacy R7 schema version (still accepted for `line_window_v1` strategy).
pub const SCHEMA_VERSION_R7: &str = "r7-bm25-v1";

/// Relative path to the index directory within .openlocus.
pub const INDEX_DIR_RELATIVE: &str = ".openlocus/index";

/// Relative path to the Tantivy index data.
pub const TANTIVY_DIR_RELATIVE: &str = ".openlocus/index/tantivy";

/// Relative path to the manifest file.
pub const MANIFEST_PATH_RELATIVE: &str = ".openlocus/index/manifest.json";

/// Chunk strategy used when building the index.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChunkStrategy {
    /// Fixed-size line windows (R7 default).
    LineWindowV1,
    /// AST-bounded chunks with fallback line windows (R8 experimental).
    AstV1,
}

impl ChunkStrategy {
    /// Parse from CLI string: "line" or "ast".
    pub fn from_cli_str(s: &str) -> Option<Self> {
        match s {
            "line" => Some(Self::LineWindowV1),
            "ast" => Some(Self::AstV1),
            _ => None,
        }
    }

    /// Short CLI string.
    pub fn to_cli_str(&self) -> &'static str {
        match self {
            Self::LineWindowV1 => "line",
            Self::AstV1 => "ast",
        }
    }
}

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

/// AST-related stats stored in the manifest (only for ast_v1 strategy).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AstManifestStats {
    pub supported_files: u64,
    pub fallback_files: u64,
    pub parser_error_files: u64,
    pub ast_chunks: u64,
    pub fallback_chunks: u64,
}

/// Index manifest tracking all indexed files and policy hash.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexManifest {
    pub schema_version: String,
    pub file_count: u64,
    pub chunk_count: u64,
    pub policy_hash: String,
    pub files: Vec<ManifestFileEntry>,
    /// Chunk strategy used when building the index.
    #[serde(default = "default_chunk_strategy")]
    pub chunk_strategy: ChunkStrategy,
    /// AST stats (present only for ast_v1 strategy).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ast_stats: Option<AstManifestStats>,
}

fn default_chunk_strategy() -> ChunkStrategy {
    ChunkStrategy::LineWindowV1
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
            chunk_strategy: ChunkStrategy::LineWindowV1,
            ast_stats: None,
        }
    }

    /// Create a new manifest with explicit chunk strategy and AST stats.
    pub fn new_with_strategy(
        policy_hash: String,
        files: Vec<ManifestFileEntry>,
        chunk_count: u64,
        chunk_strategy: ChunkStrategy,
        ast_stats: Option<AstManifestStats>,
    ) -> Self {
        let file_count = files.iter().filter(|f| f.status == "indexed").count() as u64;
        Self {
            schema_version: SCHEMA_VERSION.to_string(),
            file_count,
            chunk_count,
            policy_hash,
            files,
            chunk_strategy,
            ast_stats,
        }
    }

    /// Load manifest from the repo's .openlocus/index/manifest.json.
    /// Validates schema version and chunk strategy; refuses unrecognized.
    ///
    /// Legacy entry point: assumes colocated mode where `repo_root` is both
    /// source root and state root. Delegates to [`Self::load_at_state_root`].
    pub fn load(repo_root: &Path) -> Result<Self> {
        Self::load_at_state_root(repo_root)
    }

    /// Load manifest from `state_root/.openlocus/index/manifest.json`.
    ///
    /// In separated mode `state_root` is the persistent state location and
    /// differs from the source root. The manifest is a state artifact: it is
    /// always read from the state root, never from the source root.
    ///
    /// B0 safety closure: rejects unsafe manifest paths (symlink/reparse/
    /// special-file/non-directory ancestor) before reading. Fail-closed on
    /// every metadata/traversal error except genuine `NotFound`.
    ///
    /// B0 API-surface closure: this is `pub(crate)` — the public entry
    /// point is the legacy [`Self::load`]. High-level source-aware
    /// operations in [`crate::persistent`] call this internally; no
    /// external crate may bypass the legacy entry point to mutate state.
    pub(crate) fn load_at_state_root(state_root: &Path) -> Result<Self> {
        let canonical_state = path_safety::canonicalize_state_root(state_root)?;
        let bytes = path_safety::checked_read_file(&canonical_state, MANIFEST_PATH_RELATIVE)
            .with_context(|| "failed to read manifest.json")?;
        let content =
            std::str::from_utf8(&bytes).with_context(|| "manifest.json is not valid UTF-8")?;
        let manifest: IndexManifest =
            serde_json::from_str(content).with_context(|| "failed to parse manifest.json")?;

        // Validate schema version
        if manifest.schema_version != SCHEMA_VERSION && manifest.schema_version != SCHEMA_VERSION_R7
        {
            bail!(
                "unrecognized manifest schema_version: {}. Expected {} or {}. Rebuild the index.",
                manifest.schema_version,
                SCHEMA_VERSION,
                SCHEMA_VERSION_R7
            );
        }

        Ok(manifest)
    }

    /// Save manifest to the repo's .openlocus/index/manifest.json.
    ///
    /// Legacy entry point: delegates to [`Self::save_at_state_root`].
    pub fn save(&self, repo_root: &Path) -> Result<()> {
        self.save_at_state_root(repo_root)
    }

    /// Save manifest to `state_root/.openlocus/index/manifest.json`.
    ///
    /// The manifest is a state artifact: it is always written to the state
    /// root, never to the source root. No absolute source path is persisted;
    /// only repo-relative paths are stored in `ManifestFileEntry::path`.
    ///
    /// B0 safety closure: routes through [`path_safety::checked_write_file_atomic`]
    /// — checked tmp-in-same-directory + rename, with preflight of the
    /// parent dir, final path, and tmp sibling. Rejects links/reparse/
    /// special-files/non-directory ancestors. Never direct-writes the
    /// final file.
    ///
    /// B0 API-surface closure: this is `pub(crate)` — the public entry
    /// point is the legacy [`Self::save`]. No external crate may bypass
    /// the legacy entry point to write state.
    pub(crate) fn save_at_state_root(&self, state_root: &Path) -> Result<()> {
        let canonical_state = path_safety::canonicalize_state_root(state_root)?;
        let content =
            serde_json::to_string_pretty(self).with_context(|| "failed to serialize manifest")?;
        path_safety::checked_write_file_atomic(
            &canonical_state,
            MANIFEST_PATH_RELATIVE,
            content.as_bytes(),
        )
        .with_context(|| "failed to write manifest.json")?;
        Ok(())
    }

    /// Check if the manifest exists.
    ///
    /// Legacy entry point: delegates to [`Self::exists_at_state_root`].
    pub fn exists(repo_root: &Path) -> bool {
        Self::exists_at_state_root(repo_root)
    }

    /// Check if the manifest exists at `state_root/.openlocus/index/manifest.json`.
    ///
    /// Legacy bool entry point: returns `false` when the manifest is
    /// genuinely absent or when an unsafe path is detected. Mutating
    /// operations (build/update/purge) must NOT rely on this mapping —
    /// they must use [`Self::checked_exists_at_state_root`] or
    /// [`path_safety::preflight_index_artifacts`] instead.
    ///
    /// B0 API-surface closure: this is `pub(crate)` — the public entry
    /// point is the legacy bool [`Self::exists`]. The legacy entry point
    /// remains behavior-compatible (maps errors to `false`).
    pub(crate) fn exists_at_state_root(state_root: &Path) -> bool {
        Self::checked_exists_at_state_root(state_root).unwrap_or(false)
    }

    /// Checked existence: returns `Ok(true)` only when the manifest is a
    /// safe regular file; `Ok(false)` when genuinely absent; `Err` when
    /// the path is unsafe (symlink/reparse/special-file/non-directory
    /// ancestor) or cannot be stat'd fail-closed.
    ///
    /// This is the source of truth mutating operations must consult; the
    /// legacy bool [`Self::exists_at_state_root`] is a thin wrapper that
    /// maps errors to `false` for backward compatibility.
    pub(crate) fn checked_exists_at_state_root(state_root: &Path) -> Result<bool> {
        let canonical_state = path_safety::canonicalize_state_root(state_root)?;
        path_safety::checked_exists(&canonical_state, MANIFEST_PATH_RELATIVE)
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
        assert_eq!(loaded.chunk_strategy, ChunkStrategy::LineWindowV1);
    }

    #[test]
    fn manifest_with_ast_strategy() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let manifest = IndexManifest::new_with_strategy(
            "fake_policy_hash".to_string(),
            vec![ManifestFileEntry {
                path: "src/main.rs".into(),
                content_sha: "abc123".into(),
                size_bytes: 100,
                language: "rust".into(),
                status: "indexed".into(),
                skipped_reason: None,
            }],
            3,
            ChunkStrategy::AstV1,
            Some(AstManifestStats {
                supported_files: 1,
                fallback_files: 0,
                parser_error_files: 0,
                ast_chunks: 2,
                fallback_chunks: 1,
            }),
        );

        manifest.save(root).unwrap();
        let loaded = IndexManifest::load(root).unwrap();

        assert_eq!(loaded.chunk_strategy, ChunkStrategy::AstV1);
        assert!(loaded.ast_stats.is_some());
        assert_eq!(loaded.ast_stats.unwrap().ast_chunks, 2);
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
    fn manifest_at_state_root_loads_from_state_root_not_caller_cwd() {
        let source_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = source_dir.path();
        let state_root = state_dir.path();

        // No manifest anywhere yet
        assert!(!IndexManifest::exists_at_state_root(state_root));
        assert!(!IndexManifest::exists_at_state_root(source_root));

        let manifest = IndexManifest::new("policy-hash-state".into(), vec![], 0);
        manifest.save_at_state_root(state_root).unwrap();

        // State root has the manifest; source root does not
        assert!(IndexManifest::exists_at_state_root(state_root));
        assert!(!IndexManifest::exists_at_state_root(source_root));

        // load_at_state_root reads from state_root, not source_root
        let loaded = IndexManifest::load_at_state_root(state_root).unwrap();
        assert_eq!(loaded.policy_hash, "policy-hash-state");

        // Legacy load on source_root must fail (no manifest there)
        assert!(IndexManifest::load_at_state_root(source_root).is_err());
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

    #[test]
    fn r7_manifest_loads() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Write an R7-style manifest (no chunk_strategy field)
        let r7_manifest = r#"{
            "schema_version": "r7-bm25-v1",
            "file_count": 1,
            "chunk_count": 3,
            "policy_hash": "fake",
            "files": []
        }"#;
        let path = root.join(MANIFEST_PATH_RELATIVE);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, r7_manifest).unwrap();

        let loaded = IndexManifest::load(root).unwrap();
        assert_eq!(loaded.schema_version, SCHEMA_VERSION_R7);
        // Default chunk_strategy for R7 manifests
        assert_eq!(loaded.chunk_strategy, ChunkStrategy::LineWindowV1);
    }

    #[test]
    fn unknown_schema_refused() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let bad_manifest = r#"{
            "schema_version": "r99-bm25-v99",
            "file_count": 0,
            "chunk_count": 0,
            "policy_hash": "fake",
            "files": []
        }"#;
        let path = root.join(MANIFEST_PATH_RELATIVE);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, bad_manifest).unwrap();

        let result = IndexManifest::load(root);
        assert!(result.is_err());
        let err = format!("{}", result.unwrap_err());
        assert!(err.contains("unrecognized manifest schema_version"));
    }

    #[test]
    fn chunk_strategy_from_cli() {
        assert_eq!(
            ChunkStrategy::from_cli_str("line"),
            Some(ChunkStrategy::LineWindowV1)
        );
        assert_eq!(
            ChunkStrategy::from_cli_str("ast"),
            Some(ChunkStrategy::AstV1)
        );
        assert_eq!(ChunkStrategy::from_cli_str("other"), None);
    }
}
