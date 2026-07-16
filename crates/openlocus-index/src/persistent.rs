//! Persistent BM25 index operations.
//!
//! build_index: Full rebuild, writes Tantivy index + manifest.
//! status_index: Quick check of index state.
//! validate_index: Full validation of manifest entries against filesystem.
//! purge_index: Safe deletion of R7/R8 index artifacts.
//! search_persistent_bm25: Search with mandatory re-verification of every hit.
//!
//! Safety gates (oracle review R7 + R8):
//! - Policy gate: search/validate refuse if manifest policy_hash ≠ current policy.
//! - validate_path on every Tantivy hit path before reading file.
//! - Empty index_content_sha → skip (cannot verify stale check).
//! - chunk range strictly validated: 1 ≤ start ≤ end ≤ total_lines; no clamping.
//! - build_index filters unsafe FileRecord paths via validate_path.
//! - R8: chunk_strategy gate — search/validate refuse if manifest chunk_strategy
//!   is unrecognized or missing; schema mismatch also triggers rebuild.
//! - R8: AST chunks are only candidate boundaries; evidence still verified
//!   from current filesystem path/range/hash/excerpt/freshness.

use anyhow::{Context, Result, bail};
use openlocus_ast::{AstChunkKind, AstStatus, extract_ast_chunks};
use openlocus_core::{Channel, Evidence, Freshness, Policy, ScoreParts};
use openlocus_repo::scan::FileRecord;
use openlocus_repo::validate_path;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::Instant;
use tantivy::collector::TopDocs;
use tantivy::query::{Query, QueryParser};
use tantivy::schema::*;
use tantivy::tokenizer::TokenStream;
use tantivy::{DocAddress, Index, ReloadPolicy, Score, Searcher, doc};

use crate::manifest::*;
use crate::path_safety;

/// Maximum chunk size in lines for indexing (line-window strategy).
const MAX_CHUNK_LINES: u64 = 30;
/// Context lines around a matching center for tightened evidence.
const CONTEXT_LINES: u64 = 2;
/// Maximum evidence span in lines.
const MAX_EVIDENCE_SPAN: u64 = 7;

// ── Root separation validation ─────────────────────────────────────────

/// Validate that `source_root` and `state_root` are safe to use in
/// separated mode (where they differ).
///
/// In colocated mode (`source_root == state_root`, lexically), this is a
/// no-op: state artifacts live under `source_root/.openlocus/index/` by
/// definition, which is the legacy R7/R8 layout.
///
/// In separated mode, the actual future/current artifact subtree
/// `A = state_root/.openlocus/index/` is compared component-wise against
/// the canonical source root `S`. The relation is rejected when:
/// - `A == S` (artifact subtree is exactly the source root),
/// - `A` is below `S` (`A.starts_with(S)` — writing artifacts would modify
///   the source tree), or
/// - `S` is below `A` (`S.starts_with(A)` — the source is consumed by the
///   artifact subtree).
///
/// Source-below-state-root is otherwise allowed when the source is a
/// sibling/outside `.openlocus/index`; that configuration is safe because
/// the artifact subtree does not overlap the source.
///
/// `source_root` must exist and canonicalize. `A` may not yet exist (the
/// build creates it); in that case it is resolved through its nearest
/// existing canonical ancestor and only validated `Normal` suffix
/// components are appended. No raw-path fallback is used: if no
/// canonicalizable ancestor exists, the call errors. Symlink/canonical
/// aliases are handled fail-closed: when `A` and `S` resolve to the same
/// canonical path or an ancestor/descendant relation, the call is rejected.
///
/// B0 API-surface closure: this is `pub(crate)` — it is an internal
/// safety gate called by every public high-level source-aware operation
/// (`build_index_at_state_root`, `update_index_at_state_root`,
/// `purge_index_at_state_root`, `search_persistent_bm25_at_state_root`,
/// `validate_index_at_state_root`, `status_index_at_state_root`,
/// `dirty_index_at_state_root`, `PersistentIndex::open_at_state_root`).
/// No external crate may invoke the overlap check directly; there is no
/// public state-only manifest mutation route that bypasses it.
pub(crate) fn validate_separated_roots(source_root: &Path, state_root: &Path) -> Result<()> {
    // Colocated mode: identical lexical paths never need separation.
    if source_root == state_root {
        return Ok(());
    }

    let canonical_source = source_root.canonicalize().with_context(|| {
        format!(
            "source root does not exist or cannot be canonicalized: {}",
            source_root.display()
        )
    })?;

    check_artifact_source_overlap(&canonical_source, state_root)
}

/// Validate separation AND return the canonical source root, canonicalized
/// once (fail-closed). Used by callers that need to **bind** the canonical
/// source — currently [`PersistentBm25Index::open_at_state_root`], which
/// stores the canonical source/state pair on the handle and enforces
/// source-root binding at search time. This avoids a second inconsistent
/// canonicalization of the source in those callers.
///
/// Unlike [`validate_separated_roots`], this canonicalizes `source_root`
/// **even in colocated mode** (`source_root == state_root` lexically),
/// because the caller needs the canonical source for binding. Therefore
/// `source_root` must exist; a non-existent colocated source fails
/// fail-closed (which is correct — the index cannot exist there either).
///
/// Canonical aliases resolving to the exact same canonical source directory
/// are accepted: comparison is by canonical equality, not lexical string
/// equality.
pub(crate) fn validate_separated_roots_canonical(
    source_root: &Path,
    state_root: &Path,
) -> Result<PathBuf> {
    let canonical_source = source_root.canonicalize().with_context(|| {
        format!(
            "source root does not exist or cannot be canonicalized: {}",
            source_root.display()
        )
    })?;

    if source_root != state_root {
        check_artifact_source_overlap(&canonical_source, state_root)?;
    }

    Ok(canonical_source)
}

/// Check the artifact/source overlap given an already-canonical source.
///
/// Actual future/current artifact subtree: `state_root/.openlocus/index`.
/// Comparing the state root itself would over-reject (e.g. source under
/// state but outside `.openlocus/index` is safe). Rejects when the canonical
/// artifact subtree `A` equals, is below, or contains the canonical source
/// `S` (component-wise via `starts_with`).
fn check_artifact_source_overlap(canonical_source: &Path, state_root: &Path) -> Result<()> {
    let artifact_path = state_root.join(INDEX_DIR_RELATIVE);
    let canonical_artifact = canonicalize_artifact_path(&artifact_path)?;

    if canonical_artifact == canonical_source
        || canonical_artifact.starts_with(canonical_source)
        || canonical_source.starts_with(&canonical_artifact)
    {
        bail!(
            "state artifact subtree overlaps source root in separated mode; use colocated mode (no flags) or a state root whose .openlocus/index is disjoint from the source: artifact={}, source={}",
            canonical_artifact.display(),
            canonical_source.display()
        );
    }

    Ok(())
}

/// Resolve `path` to a canonical path for separation comparison.
///
/// If `path` exists (possibly through symlinks), `path.canonicalize()` is
/// used directly — symlinks are resolved fail-closed.
///
/// If `path` does not exist, walk up to the nearest existing ancestor,
/// canonicalize that, and re-attach the non-existent suffix. The suffix
/// must consist of only `Normal` (and no-op `CurDir`) components;
/// `ParentDir`, `RootDir`, and `Prefix` components in the unresolved
/// suffix are rejected (they could escape the canonical ancestor).
///
/// Fail-closed error policy (no raw-path fallback, no `Path::exists()`
/// ambiguity):
/// - Only a definite `io::ErrorKind::NotFound` for a genuinely absent
///   path/component may enter nearest-existing-ancestor reconstruction.
///   Any other canonicalize/symlink_metadata/metadata error
///   (PermissionDenied, TooManyLinks/symlink loop, invalid input, etc.)
///   returns an error immediately.
/// - `symlink_metadata` is used (not `metadata`) at every candidate so a
///   symlink is observable even when its target is absent. A dangling
///   symlink or symlink loop at ANY component — including the final
///   component of `path` itself — is rejected and never treated as an
///   unresolved `Normal` suffix appended to the canonical ancestor.
///   Existing symlinks must canonicalize successfully (resolving through
///   their target) or fail.
/// - No existing canonicalizable ancestor exists for `path` => error.
/// - The canonical ancestor cannot be canonicalized => error.
/// - The unresolved suffix contains a non-`Normal` component => error.
fn canonicalize_artifact_path(path: &Path) -> Result<PathBuf> {
    use std::io;

    // First, observe `path` itself with symlink_metadata so a symlink is
    // visible even when its target is absent. A dangling link or symlink
    // loop at the FINAL component of `path` must reject here — it can
    // never be treated as an unresolved Normal suffix appended to the
    // ancestor (that would let a hostile dangling link silently pass
    // separation validation).
    match path.symlink_metadata() {
        Ok(_md) => {
            // `path` exists (or is itself a symlink). Canonicalize so
            // symlink loops / dangling links at the final component reject
            // here. Only NotFound falls through to walk-up reconstruction;
            // every other canonicalize error fail-closes.
            match path.canonicalize() {
                Ok(c) => return Ok(c),
                Err(err) if err.kind() == io::ErrorKind::NotFound => {
                    // symlink_metadata succeeded but canonicalize returned
                    // NotFound → the link itself exists but its target is
                    // absent (dangling symlink). Reject.
                    return Err(anyhow::anyhow!(
                        "dangling symlink at state artifact path: {}: {}",
                        path.display(),
                        err
                    ));
                }
                Err(err) => {
                    return Err(anyhow::anyhow!(
                        "cannot canonicalize state artifact path: {}: {}",
                        path.display(),
                        err
                    ));
                }
            }
        }
        Err(err) if err.kind() == io::ErrorKind::NotFound => {
            // `path` is genuinely absent (and not a symlink) — fall through
            // to nearest-existing-ancestor reconstruction.
        }
        Err(err) => {
            // PermissionDenied / loop / invalid / etc. — fail-closed.
            return Err(anyhow::anyhow!(
                "cannot stat state artifact path: {}: {}",
                path.display(),
                err
            ));
        }
    }

    // Walk up to the nearest existing ancestor WITHOUT using Path::exists()
    // (which silently masks non-NotFound errors). For each candidate use
    // symlink_metadata so a symlink is observable even when its target is
    // absent (dangling link / loop). A real existing component is then
    // canonicalized; a NotFound lets the walk continue; any other metadata
    // error fail-closes immediately.
    let mut canonical_ancestor: Option<PathBuf> = None;
    let mut existing_ancestor: Option<PathBuf> = None;
    let mut current = path.to_path_buf();
    while let Some(parent) = current.parent() {
        match parent.symlink_metadata() {
            Ok(_md) => {
                // Exists (or is itself a symlink). Canonicalize so symlink
                // loops / dangling links in the ancestor chain reject here
                // rather than being appended as an unresolved Normal suffix.
                match parent.canonicalize() {
                    Ok(c) => {
                        existing_ancestor = Some(parent.to_path_buf());
                        canonical_ancestor = Some(c);
                        break;
                    }
                    Err(err) if err.kind() == io::ErrorKind::NotFound => {
                        // symlink_metadata succeeded but canonicalize returned
                        // NotFound → dangling symlink in the ancestor chain.
                        // Reject (never treated as an unresolved Normal suffix).
                        return Err(anyhow::anyhow!(
                            "dangling symlink in state artifact ancestor chain: {}: {}",
                            parent.display(),
                            err
                        ));
                    }
                    Err(err) => {
                        return Err(anyhow::anyhow!(
                            "cannot canonicalize state artifact ancestor: {}: {}",
                            parent.display(),
                            err
                        ));
                    }
                }
            }
            Err(err) if err.kind() == io::ErrorKind::NotFound => {
                // Genuinely absent — continue walking up.
                current = parent.to_path_buf();
                continue;
            }
            Err(err) => {
                // PermissionDenied / loop / invalid / etc. — fail-closed.
                return Err(anyhow::anyhow!(
                    "cannot stat state artifact ancestor: {}: {}",
                    parent.display(),
                    err
                ));
            }
        }
    }

    let ancestor = existing_ancestor.ok_or_else(|| {
        anyhow::anyhow!(
            "cannot resolve state artifact path: no existing ancestor found for {}",
            path.display()
        )
    })?;
    // `canonical_ancestor` is set iff `existing_ancestor` is set — both are
    // assigned together in the only `break` branch above.
    let canonical_ancestor =
        canonical_ancestor.expect("canonical_ancestor is set iff existing_ancestor is set");

    let suffix = path.strip_prefix(&ancestor).unwrap_or(Path::new(""));

    // Validate suffix components: only Normal (and no-op CurDir) are allowed.
    // Reject ParentDir (..), RootDir (leading /), and Prefix (Windows drive).
    for component in suffix.components() {
        match component {
            std::path::Component::Normal(_) | std::path::Component::CurDir => {}
            std::path::Component::ParentDir => bail!(
                "state artifact path contains a parent-dir component in unresolved suffix: {}",
                path.display()
            ),
            std::path::Component::RootDir => bail!(
                "state artifact path contains a root-dir component in unresolved suffix: {}",
                path.display()
            ),
            std::path::Component::Prefix(_) => bail!(
                "state artifact path contains a prefix component in unresolved suffix: {}",
                path.display()
            ),
        }
    }

    Ok(canonical_ancestor.join(suffix))
}

// ── Build ──────────────────────────────────────────────────────────────

/// Result of building a persistent index.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BuildResult {
    pub success: bool,
    pub file_count: u64,
    pub chunk_count: u64,
    pub schema_version: String,
    pub policy_hash: String,
    pub chunk_strategy: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ast_stats: Option<AstManifestStats>,
}

/// Build a persistent Tantivy BM25 index from file records.
/// Writes the index to .openlocus/index/tantivy/ and manifest to .openlocus/index/manifest.json.
/// This is a full rebuild — any existing index is replaced.
///
/// `chunk_strategy` controls how source is chunked:
/// - `line_window_v1` (default): fixed-size line windows, same as R7.
/// - `ast_v1` (experimental): AST-bounded chunks with fallback line windows.
///
/// Safety: filters FileRecord paths through validate_path; unsafe paths are skipped.
///
/// Legacy entry point: assumes colocated mode where `repo_root` is both source
/// root and state root. Delegates to [`build_index_at_state_root`].
pub fn build_index(
    repo_root: &Path,
    records: &[FileRecord],
    policy: &Policy,
    chunk_strategy: ChunkStrategy,
) -> Result<BuildResult> {
    build_index_at_state_root(repo_root, repo_root, records, policy, chunk_strategy)
}

pub fn build_index_at_state_root(
    source_root: &Path,
    state_root: &Path,
    records: &[FileRecord],
    policy: &Policy,
    chunk_strategy: ChunkStrategy,
) -> Result<BuildResult> {
    validate_separated_roots(source_root, state_root)?;
    let policy_hash = compute_policy_hash(policy);

    // B0: establish state_root as trust anchor (canonicalize, creating
    // missing ancestor components one-at-a-time and rechecking each).
    // NOTE: `ensure_state_root` may itself create the wholly absent state
    // root and its missing ancestors — that IS a filesystem mutation
    // above `.openlocus`. The full typed preflight below runs BEFORE any
    // EXISTING index-artifact mutation (`.openlocus/index`, manifest,
    // manifest tmp, tantivy); it does not claim that creating the absent
    // trust anchor is non-mutation.
    let canonical_state = path_safety::ensure_state_root(state_root)?;

    // B0: one full typed preflight over ALL known persistent-index targets
    // before any EXISTING index-artifact mutation. Enforces the EXACT
    // expected kind per artifact (`.openlocus/index`: absent or directory;
    // `manifest.json` / `manifest.json.tmp`: absent or regular file;
    // `tantivy`: absent or directory, recursively preflighted when
    // present). Rejects preexisting descendant symlinks/reparse/special-
    // files/non-directory ancestors and wrong-kind artifacts.
    path_safety::preflight_index_artifacts(&canonical_state)?;

    // State paths for index/manifest writes
    let index_dir_rel = INDEX_DIR_RELATIVE;
    let tantivy_dir_rel = TANTIVY_DIR_RELATIVE;

    // B0: create `.openlocus/index` directory component-by-component (with
    // recheck of each existing component) — never `create_dir_all`, which
    // would follow preexisting links.
    path_safety::ensure_artifact_dir(&canonical_state, index_dir_rel)?;

    // B0: recheck the tantivy subtree before removing/rebuilding. The full
    // preflight above already did this once; this is the immediate
    // pre-mutation recheck.
    path_safety::preflight_artifact_subtree(&canonical_state, tantivy_dir_rel)?;
    let tantivy_dir = canonical_state.join(tantivy_dir_rel);

    // B0: remove the existing Tantivy index using the TYPED preflight
    // result — not a raw `symlink_metadata().is_ok()`, which would hide
    // wrong-kind and non-`NotFound` errors. Only a genuine directory is
    // removed; an absent tantivy dir skips; a regular file / wrong kind
    // is rejected fail-closed (never overwritten or silently removed).
    // The preflight above guarantees the subtree is free of links/reparse,
    // so remove_dir_all cannot follow a descendant link to outside the
    // index.
    match path_safety::preflight_artifact_at(&canonical_state, tantivy_dir_rel)? {
        path_safety::ArtifactKind::Directory => {
            std::fs::remove_dir_all(&tantivy_dir)
                .with_context(|| "failed to remove existing tantivy index")?;
        }
        path_safety::ArtifactKind::Absent => { /* nothing to remove */ }
        path_safety::ArtifactKind::RegularFile => bail!(
            "tantivy dir is a regular file, not a directory; refusing to remove or overwrite: {}",
            tantivy_dir.display()
        ),
    }
    // B0: create the tantivy dir component-by-component, rechecking.
    path_safety::ensure_artifact_dir(&canonical_state, tantivy_dir_rel)?;
    // B0: recheck the tantivy dir immediately before Index::create_in_dir.
    match path_safety::preflight_artifact_at(&canonical_state, tantivy_dir_rel)? {
        path_safety::ArtifactKind::Directory => {}
        other => bail!(
            "tantivy dir is not a directory before Index::create_in_dir: {:?}",
            other
        ),
    }

    // Build schema
    let mut schema_builder = Schema::builder();
    let path_field = schema_builder.add_text_field("path", STRING | STORED);
    let language_field = schema_builder.add_text_field("language", STRING | STORED);
    let content_sha_field = schema_builder.add_text_field("content_sha", STRING | STORED);
    let start_line_field = schema_builder.add_u64_field("start_line", STORED);
    let end_line_field = schema_builder.add_u64_field("end_line", STORED);
    let content_field = schema_builder.add_text_field("content", TEXT | STORED);
    let schema = schema_builder.build();

    let index = Index::create_in_dir(&tantivy_dir, schema)?;
    let mut index_writer = index.writer(50_000_000)?;

    let mut manifest_files = Vec::new();
    let mut total_chunks: u64 = 0;
    let mut ast_stats = AstManifestStats::default();

    for record in records {
        // Path safety gate: validate_path against SOURCE root before indexing
        if validate_path(source_root, &record.path).is_err() {
            manifest_files.push(ManifestFileEntry {
                path: record.path.clone(),
                content_sha: record.content_sha.clone(),
                size_bytes: record.size,
                language: record.language.clone(),
                status: "skipped".into(),
                skipped_reason: Some("path_unsafe".into()),
            });
            continue;
        }

        // Read current file content from SOURCE root
        let full_path = source_root.join(&record.path);

        // Read current file content
        let content = match std::fs::read_to_string(&full_path) {
            Ok(c) => c,
            Err(_) => {
                manifest_files.push(ManifestFileEntry {
                    path: record.path.clone(),
                    content_sha: record.content_sha.clone(),
                    size_bytes: record.size,
                    language: record.language.clone(),
                    status: "skipped".into(),
                    skipped_reason: Some("read_error".into()),
                });
                continue;
            }
        };

        // Compute current content_sha
        let current_sha = blake3::hash(content.as_bytes()).to_hex().to_string();

        let lines: Vec<&str> = content.lines().collect();
        let total_lines = lines.len() as u64;

        if total_lines == 0 {
            manifest_files.push(ManifestFileEntry {
                path: record.path.clone(),
                content_sha: current_sha,
                size_bytes: record.size,
                language: record.language.clone(),
                status: "skipped".into(),
                skipped_reason: Some("empty_file".into()),
            });
            continue;
        }

        // Determine chunks based on strategy
        let chunks = match chunk_strategy {
            ChunkStrategy::LineWindowV1 => {
                // R7 line-window chunking
                let mut chunks = Vec::new();
                let mut chunk_start = 0u64;
                while chunk_start < total_lines {
                    let chunk_end = (chunk_start + MAX_CHUNK_LINES).min(total_lines);
                    chunks.push((chunk_start + 1, chunk_end)); // 1-based
                    chunk_start = chunk_end;
                }
                chunks
            }
            ChunkStrategy::AstV1 => {
                // R8 AST-bounded chunking
                let ast_result =
                    extract_ast_chunks(&record.path, &record.language, &content, MAX_CHUNK_LINES);

                // Track AST stats
                match ast_result.status {
                    AstStatus::Supported => ast_stats.supported_files += 1,
                    AstStatus::FallbackUnsupported => ast_stats.fallback_files += 1,
                    AstStatus::FallbackParseError => ast_stats.parser_error_files += 1,
                }
                for chunk in &ast_result.chunks {
                    match chunk.kind {
                        AstChunkKind::AstNode => ast_stats.ast_chunks += 1,
                        AstChunkKind::FallbackLineWindow => ast_stats.fallback_chunks += 1,
                    }
                }

                ast_result
                    .chunks
                    .iter()
                    .map(|c| (c.start_line, c.end_line))
                    .collect()
            }
        };

        // Index each chunk
        for (start_line, end_line) in &chunks {
            let start_idx = (*start_line - 1) as usize;
            let end_idx = *end_line as usize;
            let chunk_content = if start_idx < lines.len() && end_idx <= lines.len() {
                lines[start_idx..end_idx].join("\n")
            } else {
                continue; // Invalid range, skip
            };

            index_writer.add_document(doc!(
                path_field => record.path.as_str(),
                language_field => record.language.as_str(),
                content_sha_field => current_sha.as_str(),
                start_line_field => *start_line,
                end_line_field => *end_line,
                content_field => chunk_content.as_str(),
            ))?;

            total_chunks += 1;
        }

        manifest_files.push(ManifestFileEntry {
            path: record.path.clone(),
            content_sha: current_sha,
            size_bytes: record.size,
            language: record.language.clone(),
            status: "indexed".into(),
            skipped_reason: None,
        });
    }

    // B0: recursively recheck the Tantivy subtree before writer commit.
    path_safety::preflight_artifact_subtree(&canonical_state, tantivy_dir_rel)?;

    index_writer.commit()?;

    // Write manifest with chunk strategy to STATE root (B0: routed through
    // checked tmp-in-same-directory + rename helper).
    let ast_stats_opt = if chunk_strategy == ChunkStrategy::AstV1 {
        Some(ast_stats)
    } else {
        None
    };
    let manifest = IndexManifest::new_with_strategy(
        policy_hash.clone(),
        manifest_files,
        total_chunks,
        chunk_strategy.clone(),
        ast_stats_opt.clone(),
    );
    manifest.save_at_state_root(state_root)?;

    Ok(BuildResult {
        success: true,
        file_count: manifest.file_count,
        chunk_count: total_chunks,
        schema_version: SCHEMA_VERSION.to_string(),
        policy_hash,
        chunk_strategy: chunk_strategy.to_cli_str().to_string(),
        ast_stats: ast_stats_opt,
    })
}

// ── Status ─────────────────────────────────────────────────────────────

/// Quick status check of the persistent index.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct StatusResult {
    pub exists: bool,
    pub schema_version: Option<String>,
    pub file_count: Option<u64>,
    pub chunk_count: Option<u64>,
    pub policy_hash_matches: Option<bool>,
    pub requires_rebuild: bool,
    /// Quick stale check: count of manifest files whose content_sha doesn't
    /// match current file. This is bounded by reading each file once.
    pub stale_files_fast: Option<u64>,
    /// Chunk strategy from manifest.
    pub chunk_strategy: Option<String>,
    /// AST stats from manifest (if present).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ast_stats: Option<AstManifestStats>,
}

/// Quick status check of the persistent index.
///
/// Legacy entry point: assumes colocated mode. Delegates to
/// [`status_index_at_state_root`].
pub fn status_index(repo_root: &Path, policy: &Policy) -> Result<StatusResult> {
    status_index_at_state_root(repo_root, repo_root, policy)
}

/// Quick status check of the persistent index with explicit source/state roots.
///
/// - Manifest and Tantivy index are read from `state_root`.
/// - Currentness (stale/deleted/unsafe) checks re-read files from
///   `source_root` via `validate_path(source_root, ...)`.
pub fn status_index_at_state_root(
    source_root: &Path,
    state_root: &Path,
    policy: &Policy,
) -> Result<StatusResult> {
    validate_separated_roots(source_root, state_root)?;
    let canonical_state = path_safety::canonicalize_state_root(state_root)?;

    // B0: preflight the manifest + Tantivy subtree before path-based read.
    // A genuinely absent manifest is OK; an unsafe path (link/reparse/
    // special-file/non-directory ancestor) rejects fail-closed.
    let manifest_present = path_safety::checked_exists(&canonical_state, MANIFEST_PATH_RELATIVE)?;
    if !manifest_present {
        return Ok(StatusResult {
            exists: false,
            schema_version: None,
            file_count: None,
            chunk_count: None,
            policy_hash_matches: None,
            requires_rebuild: true,
            stale_files_fast: None,
            chunk_strategy: None,
            ast_stats: None,
        });
    }
    // B0: preflight the Tantivy subtree before opening (so later Tantivy
    // operations cannot follow descendants).
    path_safety::preflight_artifact_subtree(&canonical_state, TANTIVY_DIR_RELATIVE)?;

    let manifest = IndexManifest::load_at_state_root(state_root)?;

    let current_policy_hash = compute_policy_hash(policy);
    let policy_hash_matches = manifest.policy_hash == current_policy_hash;

    let schema_ok =
        manifest.schema_version == SCHEMA_VERSION || manifest.schema_version == SCHEMA_VERSION_R7;

    // R8: chunk_strategy must be recognized
    let strategy_ok = manifest.chunk_strategy == ChunkStrategy::LineWindowV1
        || manifest.chunk_strategy == ChunkStrategy::AstV1;

    // Quick stale check: for each indexed file, check if content_sha matches current file.
    // Files are re-read from SOURCE root.
    let mut stale_count: u64 = 0;
    let mut deleted_count: u64 = 0;
    let mut unsafe_count: u64 = 0;
    for entry in &manifest.files {
        if entry.status != "indexed" {
            continue;
        }
        let full_path = match validate_path(source_root, &entry.path) {
            Ok(path) => path,
            Err(_) => {
                unsafe_count += 1;
                continue;
            }
        };
        if !full_path.exists() {
            deleted_count += 1;
            continue;
        }
        if let Ok(bytes) = std::fs::read(&full_path) {
            let current_sha = blake3::hash(&bytes).to_hex().to_string();
            if current_sha != entry.content_sha {
                stale_count += 1;
            }
        }
    }

    let requires_rebuild = !schema_ok
        || !policy_hash_matches
        || !strategy_ok
        || stale_count > 0
        || deleted_count > 0
        || unsafe_count > 0;

    Ok(StatusResult {
        exists: true,
        schema_version: Some(manifest.schema_version),
        file_count: Some(manifest.file_count),
        chunk_count: Some(manifest.chunk_count),
        policy_hash_matches: Some(policy_hash_matches),
        requires_rebuild,
        stale_files_fast: Some(stale_count + deleted_count + unsafe_count),
        chunk_strategy: Some(manifest.chunk_strategy.to_cli_str().to_string()),
        ast_stats: manifest.ast_stats,
    })
}

// ── Dirty ──────────────────────────────────────────────────────────────

/// Dirty summary: manifest-vs-current scan result.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DirtyResult {
    /// True if index is fully clean (no added/modified/deleted, policy/schema match).
    pub clean: bool,
    /// True if any file-level update is needed (added/modified/deleted).
    pub requires_update: bool,
    /// True if full rebuild is required (policy/schema/strategy mismatch, or no index).
    pub requires_rebuild: bool,
    /// Policy-included files on disk but not in manifest.
    pub added_files: Vec<String>,
    /// Manifest entries whose current content_sha differs.
    pub modified_files: Vec<String>,
    /// Manifest entries whose files no longer exist on disk.
    pub deleted_files: Vec<String>,
    pub added_count: u64,
    pub modified_count: u64,
    pub deleted_count: u64,
    pub policy_hash_matches: bool,
    pub schema_matches: bool,
    pub chunk_strategy: Option<String>,
}

/// Compute a dirty summary comparing manifest entries against the current
/// filesystem scan. Also discovers policy-included files not in the manifest.
///
/// Requires an existing index + manifest; otherwise returns requires_rebuild=true.
/// Policy-excluded added files are NOT reported as requiring update.
///
/// Legacy entry point: assumes colocated mode. Delegates to
/// [`dirty_index_at_state_root`].
pub fn dirty_index(
    repo_root: &Path,
    policy: &Policy,
    current_records: &[FileRecord],
) -> Result<DirtyResult> {
    dirty_index_at_state_root(repo_root, repo_root, policy, current_records)
}

/// Compute a dirty summary with explicit source/state roots.
///
/// - Manifest is read from `state_root`.
/// - Current file content for currentness checks is re-read from
///   `source_root` via `validate_path(source_root, ...)`.
pub fn dirty_index_at_state_root(
    source_root: &Path,
    state_root: &Path,
    policy: &Policy,
    current_records: &[FileRecord],
) -> Result<DirtyResult> {
    validate_separated_roots(source_root, state_root)?;
    let canonical_state = path_safety::canonicalize_state_root(state_root)?;

    // B0: preflight manifest + Tantivy subtree before path-based read.
    let manifest_present = path_safety::checked_exists(&canonical_state, MANIFEST_PATH_RELATIVE)?;
    if !manifest_present {
        return Ok(DirtyResult {
            clean: false,
            requires_update: false,
            requires_rebuild: true,
            added_files: vec![],
            modified_files: vec![],
            deleted_files: vec![],
            added_count: 0,
            modified_count: 0,
            deleted_count: 0,
            policy_hash_matches: false,
            schema_matches: false,
            chunk_strategy: None,
        });
    }
    path_safety::preflight_artifact_subtree(&canonical_state, TANTIVY_DIR_RELATIVE)?;

    let manifest = match IndexManifest::load_at_state_root(state_root) {
        Ok(m) => m,
        Err(_) => {
            // Manifest exists but is corrupt/unloadable → requires rebuild
            return Ok(DirtyResult {
                clean: false,
                requires_update: false,
                requires_rebuild: true,
                added_files: vec![],
                modified_files: vec![],
                deleted_files: vec![],
                added_count: 0,
                modified_count: 0,
                deleted_count: 0,
                policy_hash_matches: false,
                schema_matches: false,
                chunk_strategy: None,
            });
        }
    };
    let current_policy_hash = compute_policy_hash(policy);
    let policy_hash_matches = manifest.policy_hash == current_policy_hash;

    let schema_ok =
        manifest.schema_version == SCHEMA_VERSION || manifest.schema_version == SCHEMA_VERSION_R7;
    let strategy_ok = manifest.chunk_strategy == ChunkStrategy::LineWindowV1
        || manifest.chunk_strategy == ChunkStrategy::AstV1;

    // Build a set of ALL manifest paths (indexed + skipped) for added detection.
    // This prevents skipped entries from being falsely reported as "added".
    let manifest_all_paths: std::collections::HashSet<String> =
        manifest.files.iter().map(|f| f.path.clone()).collect();

    let mut modified_files = Vec::new();
    let mut deleted_files = Vec::new();

    for entry in &manifest.files {
        let full_path = match validate_path(source_root, &entry.path) {
            Ok(path) => path,
            Err(_) => {
                if entry.status == "indexed" {
                    modified_files.push(entry.path.clone());
                }
                continue;
            }
        };
        if !full_path.exists() {
            // File deleted from disk: always report as deleted regardless of status
            deleted_files.push(entry.path.clone());
            continue;
        }
        if entry.status == "indexed" {
            // Check if content changed
            if let Ok(bytes) = std::fs::read(&full_path) {
                let current_sha = blake3::hash(&bytes).to_hex().to_string();
                if current_sha != entry.content_sha {
                    modified_files.push(entry.path.clone());
                }
            }
        } else {
            // Skipped entry: re-run the SAME indexability semantics as
            // build_index/update_index to decide if it is now promotable
            // to indexed. Conditions (all must hold):
            //   (1) policy-included (present in current_records)
            //   (2) validate_path(source_root) succeeds — already checked
            //       above; an unsafe path `continue`s before reaching here
            //   (3) source is readable as UTF-8 (std::fs::read_to_string,
            //       matching build_index)
            //   (4) source is nonempty (lines().count() > 0, matching
            //       build_index's `total_lines == 0` skip)
            // If all hold, the entry is promotable even with unchanged SHA
            // — report as modified so update_index promotes it.
            //
            // Fail closed: unsafe path (continued above), absent from
            // current policy scan, unreadable/non-UTF8, or empty remains
            // skipped/clean UNLESS the SHA also changed (another actual
            // change that may require refreshing the manifest entry).
            // Never read outside source_root — validate_path enforces.
            let in_policy = current_records.iter().any(|r| r.path == entry.path);
            let bytes = std::fs::read(&full_path).ok();
            let current_sha = bytes.as_ref().map(|b| blake3::hash(b).to_hex().to_string());
            let sha_changed = current_sha.as_deref() != Some(entry.content_sha.as_str());

            let now_indexable = in_policy
                && match std::fs::read_to_string(&full_path) {
                    Ok(content) => content.lines().count() > 0,
                    Err(_) => false,
                };

            if now_indexable {
                // Promotable: report as modified regardless of SHA so
                // update_index re-chunks and flips status to "indexed".
                modified_files.push(entry.path.clone());
            } else if sha_changed {
                // Still unindexable, but content changed: report as
                // modified so update_index can refresh the manifest
                // entry's SHA / skipped_reason.
                modified_files.push(entry.path.clone());
            }
            // else: still unindexable AND SHA unchanged → clean (skip).
        }
    }

    // Added: policy-included files in current_records not in ANY manifest path
    let mut added_files = Vec::new();
    for record in current_records {
        if !manifest_all_paths.contains(&record.path) {
            added_files.push(record.path.clone());
        }
    }

    let requires_rebuild = !schema_ok || !policy_hash_matches || !strategy_ok;
    let requires_update = !requires_rebuild
        && (!added_files.is_empty() || !modified_files.is_empty() || !deleted_files.is_empty());
    let clean = !requires_rebuild && !requires_update;

    Ok(DirtyResult {
        clean,
        requires_update,
        requires_rebuild,
        added_files: added_files.clone(),
        modified_files: modified_files.clone(),
        deleted_files: deleted_files.clone(),
        added_count: added_files.len() as u64,
        modified_count: modified_files.len() as u64,
        deleted_count: deleted_files.len() as u64,
        policy_hash_matches,
        schema_matches: schema_ok,
        chunk_strategy: Some(manifest.chunk_strategy.to_cli_str().to_string()),
    })
}

// ── Update ────────────────────────────────────────────────────────────

/// Result of an incremental index update.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct UpdateResult {
    pub success: bool,
    pub added_count: u64,
    pub modified_count: u64,
    pub deleted_count: u64,
    pub commit_ms: u64,
    pub manifest_written: bool,
    pub post_status_clean: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// Incremental update of the persistent index.
///
/// Modes:
/// - `dirty=true`: compute added/modified/deleted from dirty summary, then apply batch.
/// - `path=Some(p)`: update only that single policy-included path.
///
/// Safety gates:
/// - If index/manifest missing → error (requires rebuild).
/// - If policy hash/schema/strategy mismatch → refuse update (requires rebuild).
/// - Chunk according to manifest chunk_strategy (do not mix strategies).
/// - Delete old Tantivy docs by path before adding new ones (prevent duplicates).
/// - Commit once after batch.
/// - Write manifest atomically (tmp + rename).
/// - Tantivy deletes are tombstones until merge; this is documented, not a bug.
///
/// Legacy entry point: assumes colocated mode. Delegates to
/// [`update_index_at_state_root`].
pub fn update_index(
    repo_root: &Path,
    policy: &Policy,
    current_records: &[FileRecord],
    dirty: bool,
    path: Option<&str>,
) -> Result<UpdateResult> {
    update_index_at_state_root(repo_root, repo_root, policy, current_records, dirty, path)
}

/// Incremental update with explicit source/state roots.
///
/// - Manifest and Tantivy index are read from and written to `state_root`.
/// - Source files for currentness and re-chunking are read from `source_root`
///   via `validate_path(source_root, ...)`.
/// - Manifest is atomically written to `state_root`.
pub fn update_index_at_state_root(
    source_root: &Path,
    state_root: &Path,
    policy: &Policy,
    current_records: &[FileRecord],
    dirty: bool,
    path: Option<&str>,
) -> Result<UpdateResult> {
    validate_separated_roots(source_root, state_root)?;
    let canonical_state = path_safety::canonicalize_state_root(state_root)?;
    let start = Instant::now();

    // B0: full preflight of ALL known persistent-index targets before any
    // mutation. Any link/reparse aborts before opening the index.
    path_safety::preflight_index_artifacts(&canonical_state)?;

    // Gate: manifest must exist (checked existence — unsafe rejects).
    let manifest_present = path_safety::checked_exists(&canonical_state, MANIFEST_PATH_RELATIVE)?;
    if !manifest_present {
        return Ok(UpdateResult {
            success: false,
            added_count: 0,
            modified_count: 0,
            deleted_count: 0,
            commit_ms: 0,
            manifest_written: false,
            post_status_clean: false,
            error: Some(
                "index manifest missing; rebuild the index with 'openlocus index build'".into(),
            ),
        });
    }

    let manifest = match IndexManifest::load_at_state_root(state_root) {
        Ok(m) => m,
        Err(e) => {
            return Ok(UpdateResult {
                success: false,
                added_count: 0,
                modified_count: 0,
                deleted_count: 0,
                commit_ms: 0,
                manifest_written: false,
                post_status_clean: false,
                error: Some(format!(
                    "manifest load failed: {}. Rebuild the index with 'openlocus index build'",
                    e
                )),
            });
        }
    };

    // Gate: policy hash must match
    let current_policy_hash = compute_policy_hash(policy);
    if manifest.policy_hash != current_policy_hash {
        return Ok(UpdateResult {
            success: false,
            added_count: 0,
            modified_count: 0,
            deleted_count: 0,
            commit_ms: 0,
            manifest_written: false,
            post_status_clean: false,
            error: Some(format!(
                "policy hash mismatch: manifest={}, current={}. Rebuild the index with 'openlocus index build'",
                manifest.policy_hash, current_policy_hash
            )),
        });
    }

    // Gate: schema must be recognized
    if manifest.schema_version != SCHEMA_VERSION && manifest.schema_version != SCHEMA_VERSION_R7 {
        return Ok(UpdateResult {
            success: false,
            added_count: 0,
            modified_count: 0,
            deleted_count: 0,
            commit_ms: 0,
            manifest_written: false,
            post_status_clean: false,
            error: Some(format!(
                "schema version mismatch: manifest={}. Rebuild the index with 'openlocus index build'",
                manifest.schema_version
            )),
        });
    }

    // Gate: chunk_strategy must be recognized
    if manifest.chunk_strategy != ChunkStrategy::LineWindowV1
        && manifest.chunk_strategy != ChunkStrategy::AstV1
    {
        return Ok(UpdateResult {
            success: false,
            added_count: 0,
            modified_count: 0,
            deleted_count: 0,
            commit_ms: 0,
            manifest_written: false,
            post_status_clean: false,
            error: Some(format!(
                "unrecognized chunk strategy: {:?}. Rebuild the index with 'openlocus index build'",
                manifest.chunk_strategy
            )),
        });
    }

    // Tantivy index lives in STATE root
    let tantivy_dir_rel = TANTIVY_DIR_RELATIVE;
    // B0: recheck the Tantivy subtree before opening (preflight before open).
    path_safety::preflight_artifact_subtree(&canonical_state, tantivy_dir_rel)?;
    let tantivy_present = path_safety::checked_exists(&canonical_state, tantivy_dir_rel)?;
    if !tantivy_present {
        return Ok(UpdateResult {
            success: false,
            added_count: 0,
            modified_count: 0,
            deleted_count: 0,
            commit_ms: start.elapsed().as_millis() as u64,
            manifest_written: false,
            post_status_clean: false,
            error: Some(
                "tantivy index directory missing; rebuild the index with 'openlocus index build'"
                    .into(),
            ),
        });
    }
    let tantivy_dir = canonical_state.join(tantivy_dir_rel);

    let index = Index::open_in_dir(&tantivy_dir)?;
    let schema = index.schema();
    let path_field = schema.get_field("path")?;
    let language_field = schema.get_field("language")?;
    let content_sha_field = schema.get_field("content_sha")?;
    let start_line_field = schema.get_field("start_line")?;
    let end_line_field = schema.get_field("end_line")?;
    let content_field = schema.get_field("content")?;

    let mut index_writer = index.writer(50_000_000)?;

    // Determine which paths to add/update/delete
    let (paths_to_add, paths_to_modify, paths_to_delete) = if dirty {
        let dirty_result =
            dirty_index_at_state_root(source_root, state_root, policy, current_records)?;
        if dirty_result.requires_rebuild {
            return Ok(UpdateResult {
                success: false,
                added_count: 0,
                modified_count: 0,
                deleted_count: 0,
                commit_ms: start.elapsed().as_millis() as u64,
                manifest_written: false,
                post_status_clean: false,
                error: Some("requires rebuild due to policy/schema/strategy mismatch".into()),
            });
        }
        (
            dirty_result.added_files,
            dirty_result.modified_files,
            dirty_result.deleted_files,
        )
    } else if let Some(p) = path {
        // Single-path update mode — validate against SOURCE root
        if validate_path(source_root, p).is_err() {
            return Ok(UpdateResult {
                success: false,
                added_count: 0,
                modified_count: 0,
                deleted_count: 0,
                commit_ms: start.elapsed().as_millis() as u64,
                manifest_written: false,
                post_status_clean: false,
                error: Some("path is unsafe; update path must be repo-relative".into()),
            });
        }

        let manifest_all_paths: std::collections::HashSet<String> =
            manifest.files.iter().map(|f| f.path.clone()).collect();

        let full_path = source_root.join(p);
        let record_map: std::collections::HashMap<String, &FileRecord> = current_records
            .iter()
            .map(|r| (r.path.clone(), r))
            .collect();

        if full_path.exists() {
            // File exists: check if it's policy-included
            let is_included = record_map.contains_key(p);
            if is_included {
                if manifest_all_paths.contains(p) {
                    // Path is in manifest (indexed or skipped): determine
                    // if it needs re-indexing under the SAME indexability
                    // semantics as build_index/dirty_index.
                    if let Some(entry) = manifest.files.iter().find(|f| f.path == p) {
                        let bytes = std::fs::read(&full_path).ok();
                        let current_sha =
                            bytes.as_ref().map(|b| blake3::hash(b).to_hex().to_string());
                        let sha_unchanged =
                            current_sha.as_deref() == Some(entry.content_sha.as_str());

                        if entry.status == "indexed" {
                            // Indexed + SHA-unchanged: true no-op fast path.
                            if sha_unchanged {
                                return Ok(UpdateResult {
                                    success: true,
                                    added_count: 0,
                                    modified_count: 0,
                                    deleted_count: 0,
                                    commit_ms: start.elapsed().as_millis() as u64,
                                    manifest_written: false,
                                    post_status_clean: true,
                                    error: None,
                                });
                            }
                        } else {
                            // Skipped: re-run the SAME indexability semantics.
                            // If now promotable (readable UTF-8 and nonempty
                            // — path safety and policy inclusion are already
                            // verified above), do NOT take the no-op fast
                            // path even with unchanged SHA; fall through to
                            // modify so the entry is promoted to indexed.
                            if sha_unchanged {
                                let now_indexable = match std::fs::read_to_string(&full_path) {
                                    Ok(content) => content.lines().count() > 0,
                                    Err(_) => false,
                                };
                                if !now_indexable {
                                    // Still unindexable + SHA unchanged: no-op.
                                    return Ok(UpdateResult {
                                        success: true,
                                        added_count: 0,
                                        modified_count: 0,
                                        deleted_count: 0,
                                        commit_ms: start.elapsed().as_millis() as u64,
                                        manifest_written: false,
                                        post_status_clean: true,
                                        error: None,
                                    });
                                }
                                // Now promotable with same SHA: fall
                                // through to modify path below.
                            }
                        }
                    }
                    (vec![], vec![p.to_string()], vec![])
                } else {
                    (vec![p.to_string()], vec![], vec![])
                }
            } else {
                return Ok(UpdateResult {
                    success: false,
                    added_count: 0,
                    modified_count: 0,
                    deleted_count: 0,
                    commit_ms: start.elapsed().as_millis() as u64,
                    manifest_written: false,
                    post_status_clean: false,
                    error: Some(format!("path '{}' is not policy-included", p)),
                });
            }
        } else {
            // File doesn't exist: if in manifest (indexed or skipped), delete it
            if manifest_all_paths.contains(p) {
                (vec![], vec![], vec![p.to_string()])
            } else {
                return Ok(UpdateResult {
                    success: false,
                    added_count: 0,
                    modified_count: 0,
                    deleted_count: 0,
                    commit_ms: start.elapsed().as_millis() as u64,
                    manifest_written: false,
                    post_status_clean: false,
                    error: Some(format!("path '{}' not in manifest and not on disk", p)),
                });
            }
        }
    } else {
        return Ok(UpdateResult {
            success: false,
            added_count: 0,
            modified_count: 0,
            deleted_count: 0,
            commit_ms: 0,
            manifest_written: false,
            post_status_clean: false,
            error: Some("either --dirty or --path <path> must be specified".into()),
        });
    };

    let chunk_strategy = manifest.chunk_strategy.clone();
    let mut total_added: u64 = 0;
    let mut total_modified: u64 = 0;
    let mut total_deleted: u64 = 0;
    let mut new_manifest_files = manifest.files.clone();

    // Build a record map for quick lookup
    let record_map: std::collections::HashMap<String, &FileRecord> = current_records
        .iter()
        .map(|r| (r.path.clone(), r))
        .collect();

    // Process deletions: delete Tantivy docs, remove from manifest
    for del_path in &paths_to_delete {
        // Delete all Tantivy docs with this path
        let delete_term = tantivy::Term::from_field_text(path_field, del_path);
        index_writer.delete_term(delete_term);
        total_deleted += 1;

        // Remove from manifest files
        new_manifest_files.retain(|f| f.path != *del_path);
    }

    // Process modifications: delete old docs, add new docs, update manifest
    for mod_path in &paths_to_modify {
        // Delete old docs first
        let delete_term = tantivy::Term::from_field_text(path_field, mod_path);
        index_writer.delete_term(delete_term);

        // Add new docs
        if let Some(record) = record_map.get(mod_path) {
            if validate_path(source_root, &record.path).is_err() {
                // Mark as skipped in manifest
                if let Some(entry) = new_manifest_files.iter_mut().find(|f| f.path == *mod_path) {
                    entry.status = "skipped".into();
                    entry.skipped_reason = Some("path_unsafe".into());
                }
                continue;
            }

            let full_path = source_root.join(&record.path);
            let content = match std::fs::read_to_string(&full_path) {
                Ok(c) => c,
                Err(_) => {
                    if let Some(entry) = new_manifest_files.iter_mut().find(|f| f.path == *mod_path)
                    {
                        entry.status = "skipped".into();
                        entry.skipped_reason = Some("read_error".into());
                    }
                    continue;
                }
            };

            let current_sha = blake3::hash(content.as_bytes()).to_hex().to_string();
            let lines: Vec<&str> = content.lines().collect();
            let total_lines = lines.len() as u64;

            if total_lines == 0 {
                if let Some(entry) = new_manifest_files.iter_mut().find(|f| f.path == *mod_path) {
                    entry.status = "skipped".into();
                    entry.skipped_reason = Some("empty_file".into());
                    entry.content_sha = current_sha;
                }
                continue;
            }

            let chunks = compute_chunks(
                &record.path,
                &record.language,
                &content,
                total_lines,
                &chunk_strategy,
                &mut AstManifestStats::default(),
            );

            for (start_line, end_line) in &chunks {
                let start_idx = (*start_line - 1) as usize;
                let end_idx = *end_line as usize;
                let chunk_content = if start_idx < lines.len() && end_idx <= lines.len() {
                    lines[start_idx..end_idx].join("\n")
                } else {
                    continue;
                };

                index_writer.add_document(doc!(
                    path_field => record.path.as_str(),
                    language_field => record.language.as_str(),
                    content_sha_field => current_sha.as_str(),
                    start_line_field => *start_line,
                    end_line_field => *end_line,
                    content_field => chunk_content.as_str(),
                ))?;
            }

            // Update manifest entry
            if let Some(entry) = new_manifest_files.iter_mut().find(|f| f.path == *mod_path) {
                entry.content_sha = current_sha.clone();
                entry.size_bytes = record.size;
                entry.status = "indexed".into();
                entry.skipped_reason = None;
            }

            total_modified += 1;
        }
    }

    // Process additions: add new docs, add manifest entries
    for add_path in &paths_to_add {
        if let Some(record) = record_map.get(add_path) {
            if validate_path(source_root, &record.path).is_err() {
                new_manifest_files.push(ManifestFileEntry {
                    path: record.path.clone(),
                    content_sha: record.content_sha.clone(),
                    size_bytes: record.size,
                    language: record.language.clone(),
                    status: "skipped".into(),
                    skipped_reason: Some("path_unsafe".into()),
                });
                continue;
            }

            let full_path = source_root.join(&record.path);
            let content = match std::fs::read_to_string(&full_path) {
                Ok(c) => c,
                Err(_) => {
                    new_manifest_files.push(ManifestFileEntry {
                        path: record.path.clone(),
                        content_sha: record.content_sha.clone(),
                        size_bytes: record.size,
                        language: record.language.clone(),
                        status: "skipped".into(),
                        skipped_reason: Some("read_error".into()),
                    });
                    continue;
                }
            };

            let current_sha = blake3::hash(content.as_bytes()).to_hex().to_string();
            let lines: Vec<&str> = content.lines().collect();
            let total_lines = lines.len() as u64;

            if total_lines == 0 {
                new_manifest_files.push(ManifestFileEntry {
                    path: record.path.clone(),
                    content_sha: current_sha,
                    size_bytes: record.size,
                    language: record.language.clone(),
                    status: "skipped".into(),
                    skipped_reason: Some("empty_file".into()),
                });
                continue;
            }

            let chunks = compute_chunks(
                &record.path,
                &record.language,
                &content,
                total_lines,
                &chunk_strategy,
                &mut AstManifestStats::default(),
            );

            for (start_line, end_line) in &chunks {
                let start_idx = (*start_line - 1) as usize;
                let end_idx = *end_line as usize;
                let chunk_content = if start_idx < lines.len() && end_idx <= lines.len() {
                    lines[start_idx..end_idx].join("\n")
                } else {
                    continue;
                };

                index_writer.add_document(doc!(
                    path_field => record.path.as_str(),
                    language_field => record.language.as_str(),
                    content_sha_field => current_sha.as_str(),
                    start_line_field => *start_line,
                    end_line_field => *end_line,
                    content_field => chunk_content.as_str(),
                ))?;
            }

            new_manifest_files.push(ManifestFileEntry {
                path: record.path.clone(),
                content_sha: current_sha,
                size_bytes: record.size,
                language: record.language.clone(),
                status: "indexed".into(),
                skipped_reason: None,
            });

            total_added += 1;
        }
    }

    // B0: recursively recheck the Tantivy subtree before writer commit.
    path_safety::preflight_artifact_subtree(&canonical_state, tantivy_dir_rel)?;

    // Commit once after batch
    index_writer.commit()?;

    let commit_ms = start.elapsed().as_millis() as u64;

    // Write manifest atomically (tmp + rename) to STATE root.
    //
    // B0: routed through [`path_safety::checked_write_file_atomic`]:
    // preflights parent dir + final + tmp sibling, rejects links/reparse/
    // special-files/non-directory ancestors, writes tmp, rechecks final
    // right before rename. If unsafe, this rejects AFTER the Tantivy
    // commit but BEFORE the manifest is overwritten — the existing
    // manifest remains unchanged. Callers observing this error should
    // treat the manifest as stale relative to the just-committed index
    // and re-run update or rebuild.
    let new_file_count = new_manifest_files
        .iter()
        .filter(|f| f.status == "indexed")
        .count() as u64;

    // Authoritative LIVE chunk count: open a fresh reader AFTER the single
    // commit above and read `Searcher::num_docs()`, which sums live
    // (non-deleted) doc counts across all segments. This is exactly the set
    // of chunks searchable — what `chunk_count` represents (cf. build_index
    // which sets chunk_count = number of add_document calls).
    //
    // Correct for: additions, modifications that change chunk count,
    // deletions of arbitrary chunk count, skipped<->indexed transitions,
    // and repeated incremental updates — in both colocated and split-root
    // mode. No schema migration or per-file chunk count is needed.
    let live_reader = index
        .reader_builder()
        .reload_policy(ReloadPolicy::Manual)
        .try_into()?;
    let new_chunk_count = live_reader.searcher().num_docs();

    let new_manifest = IndexManifest {
        schema_version: manifest.schema_version.clone(),
        file_count: new_file_count,
        chunk_count: new_chunk_count,
        policy_hash: current_policy_hash,
        files: new_manifest_files,
        chunk_strategy: manifest.chunk_strategy.clone(),
        ast_stats: manifest.ast_stats.clone(),
    };

    // B0: checked tmp + rename. Rechecks tmp and final right before rename.
    let manifest_content = serde_json::to_string_pretty(&new_manifest)
        .with_context(|| "failed to serialize manifest")?;
    path_safety::checked_write_file_atomic(
        &canonical_state,
        MANIFEST_PATH_RELATIVE,
        manifest_content.as_bytes(),
    )
    .with_context(|| "failed to write manifest.json atomically")?;

    // Check post-update status
    let post_dirty = dirty_index_at_state_root(source_root, state_root, policy, current_records)?;
    let post_status_clean = post_dirty.clean;

    Ok(UpdateResult {
        success: true,
        added_count: total_added,
        modified_count: total_modified,
        deleted_count: total_deleted,
        commit_ms,
        manifest_written: true,
        post_status_clean,
        error: None,
    })
}

/// Compute chunks for a file based on the given strategy.
/// Extracted from build_index to be reusable by update_index.
fn compute_chunks(
    path: &str,
    language: &str,
    content: &str,
    total_lines: u64,
    chunk_strategy: &ChunkStrategy,
    _ast_stats: &mut AstManifestStats,
) -> Vec<(u64, u64)> {
    match chunk_strategy {
        ChunkStrategy::LineWindowV1 => {
            let mut chunks = Vec::new();
            let mut chunk_start = 0u64;
            while chunk_start < total_lines {
                let chunk_end = (chunk_start + MAX_CHUNK_LINES).min(total_lines);
                chunks.push((chunk_start + 1, chunk_end)); // 1-based
                chunk_start = chunk_end;
            }
            chunks
        }
        ChunkStrategy::AstV1 => {
            let ast_result = extract_ast_chunks(path, language, content, MAX_CHUNK_LINES);
            ast_result
                .chunks
                .iter()
                .map(|c| (c.start_line, c.end_line))
                .collect()
        }
    }
}

// ── Validate ───────────────────────────────────────────────────────────

/// Full validation result.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ValidateResult {
    pub valid: bool,
    pub stale_files: Vec<String>,
    pub deleted_files: Vec<String>,
    pub policy_hash_matches: bool,
    /// Files where path validation fails (symlink escape, etc.)
    pub path_unsafe_files: Vec<String>,
    /// Chunk strategy from manifest.
    pub chunk_strategy: Option<String>,
}

/// Full validation of the persistent index against the filesystem.
/// Checks policy hash — if it doesn't match the current policy,
/// reports policy_hash_matches=false and valid=false.
/// R8: Also checks chunk_strategy is recognized; refuses unknown strategies.
///
/// Legacy entry point: assumes colocated mode. Delegates to
/// [`validate_index_at_state_root`].
pub fn validate_index(repo_root: &Path, policy: &Policy) -> Result<ValidateResult> {
    validate_index_at_state_root(repo_root, repo_root, policy)
}

/// Full validation with explicit source/state roots.
///
/// - Manifest is read from `state_root`.
/// - Current file content for currentness is re-read from `source_root`
///   via `validate_path(source_root, ...)`.
pub fn validate_index_at_state_root(
    source_root: &Path,
    state_root: &Path,
    policy: &Policy,
) -> Result<ValidateResult> {
    validate_separated_roots(source_root, state_root)?;
    let canonical_state = path_safety::canonicalize_state_root(state_root)?;

    // B0: preflight manifest + Tantivy subtree before path-based read.
    let manifest_present = path_safety::checked_exists(&canonical_state, MANIFEST_PATH_RELATIVE)?;
    if !manifest_present {
        return Ok(ValidateResult {
            valid: false,
            stale_files: vec![],
            deleted_files: vec![],
            policy_hash_matches: false,
            path_unsafe_files: vec![],
            chunk_strategy: None,
        });
    }
    path_safety::preflight_artifact_subtree(&canonical_state, TANTIVY_DIR_RELATIVE)?;

    let manifest = IndexManifest::load_at_state_root(state_root)?;

    let current_policy_hash = compute_policy_hash(policy);
    let policy_hash_matches = manifest.policy_hash == current_policy_hash;

    // R8: chunk_strategy must be recognized
    let strategy_ok = manifest.chunk_strategy == ChunkStrategy::LineWindowV1
        || manifest.chunk_strategy == ChunkStrategy::AstV1;

    let mut stale_files = Vec::new();
    let mut deleted_files = Vec::new();
    let mut path_unsafe_files = Vec::new();

    for entry in &manifest.files {
        if entry.status != "indexed" {
            continue;
        }

        // Path safety check against SOURCE root
        if validate_path(source_root, &entry.path).is_err() {
            path_unsafe_files.push(entry.path.clone());
            continue;
        }

        let full_path = source_root.join(&entry.path);
        if !full_path.exists() {
            deleted_files.push(entry.path.clone());
            continue;
        }

        if let Ok(bytes) = std::fs::read(&full_path) {
            let current_sha = blake3::hash(&bytes).to_hex().to_string();
            if current_sha != entry.content_sha {
                stale_files.push(entry.path.clone());
            }
        }
    }

    let schema_ok =
        manifest.schema_version == SCHEMA_VERSION || manifest.schema_version == SCHEMA_VERSION_R7;

    let valid = policy_hash_matches
        && strategy_ok
        && stale_files.is_empty()
        && deleted_files.is_empty()
        && path_unsafe_files.is_empty()
        && schema_ok;

    Ok(ValidateResult {
        valid,
        stale_files,
        deleted_files,
        policy_hash_matches,
        path_unsafe_files,
        chunk_strategy: Some(manifest.chunk_strategy.to_cli_str().to_string()),
    })
}

// ── Purge ──────────────────────────────────────────────────────────────

/// Result of purging the index.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PurgeResult {
    pub purged: bool,
    pub removed_paths: Vec<String>,
}

/// Safely delete R7/R8 persistent index artifacts.
///
/// Safety: Only deletes under .openlocus/index/ and does not follow symlinks
/// that would escape the repo root.
///
/// Legacy entry point: assumes colocated mode. Delegates to
/// [`purge_index_at_state_root`].
pub fn purge_index(repo_root: &Path) -> Result<PurgeResult> {
    purge_index_at_state_root(repo_root, repo_root)
}

/// Safely delete R7/R8 persistent index artifacts from the state root.
///
/// Source-aware: takes both `source_root` and `state_root` and performs
/// bidirectional source-vs-actual-artifact overlap validation itself before
/// any private raw deletion. There is no public state-only split-root
/// destructive bypass; the raw deletion logic is private to this function.
///
/// Purge is a state-only destructive operation: it deletes only
/// `state_root/.openlocus/index/` artifacts (manifest + tmp + tantivy
/// directory) and never touches the source tree.
///
/// B0 safety closure: preflights the COMPLETE known artifact set before
/// deleting anything. Any link/reparse point / special-file / non-directory
/// ancestor in `.openlocus/index`, `manifest.json`, `manifest.json.tmp`,
/// or the full `tantivy/**` subtree aborts ALL deletion — purge deletes
/// nothing. Only checked manifest/tmp/Tantivy known artifacts and a safe
/// empty index dir (as existing semantics permit) are removed; unknown
/// regular files may remain. Never operates through a canonicalized target
/// (no `Path::canonicalize()` of a descendant, no `Path::exists()` for
/// safety decisions).
pub fn purge_index_at_state_root(source_root: &Path, state_root: &Path) -> Result<PurgeResult> {
    // B0: source-aware overlap validation. This is the ONLY public entry
    // point for purge; there is no public state-only destructive bypass.
    validate_separated_roots(source_root, state_root)?;
    let canonical_state = path_safety::canonicalize_state_root(state_root)?;

    // B0: full preflight of ALL known persistent-index targets before any
    // deletion. Any link/reparse aborts ALL deletion (purge deletes nothing).
    path_safety::preflight_index_artifacts(&canonical_state)?;

    // Remove only known R7/R8 artifact paths, not arbitrary files.
    let mut removed = Vec::new();

    let tantivy_dir_rel = TANTIVY_DIR_RELATIVE;
    let manifest_path_rel = MANIFEST_PATH_RELATIVE;
    let manifest_tmp_rel = path_safety::MANIFEST_TMP_RELATIVE;

    // B0: checked manifest final. If it exists as a safe regular file,
    // remove (never follow). If absent, skip. If unsafe, the preflight
    // above already rejected.
    if path_safety::checked_exists(&canonical_state, manifest_path_rel)? {
        let manifest_path = canonical_state.join(manifest_path_rel);
        std::fs::remove_file(&manifest_path)
            .with_context(|| format!("failed to remove manifest: {}", manifest_path.display()))?;
        removed.push(manifest_path_rel.to_string());
    }

    // B0: checked manifest tmp. Remove if a safe regular file (stale
    // temp); never follow a link.
    if path_safety::checked_exists(&canonical_state, manifest_tmp_rel)? {
        let tmp_path = canonical_state.join(manifest_tmp_rel);
        std::fs::remove_file(&tmp_path)
            .with_context(|| format!("failed to remove manifest tmp: {}", tmp_path.display()))?;
        removed.push(manifest_tmp_rel.to_string());
    }

    // B0: checked Tantivy dir. The recursive preflight above guarantees
    // the subtree is free of links/reparse, so remove_dir_all cannot
    // follow a descendant link to outside the index. Remove only if it
    // exists as a safe directory.
    if path_safety::checked_exists(&canonical_state, tantivy_dir_rel)? {
        let tantivy_dir = canonical_state.join(tantivy_dir_rel);
        std::fs::remove_dir_all(&tantivy_dir)
            .with_context(|| format!("failed to remove tantivy dir: {}", tantivy_dir.display()))?;
        removed.push(tantivy_dir_rel.to_string());
    }

    // B0: best-effort cleanup of an empty `.openlocus/index` dir. Use the
    // TYPED preflight result — not a raw `symlink_metadata().is_ok()`,
    // which would hide wrong-kind and non-`NotFound` errors. Only a
    // genuine directory is removed (best-effort `remove_dir` succeeds only
    // on an empty real directory); absent skips; a regular file is left
    // untouched (the full preflight above already rejected a wrong-kind
    // index dir, so this arm is defensive). `remove_dir` never follows a
    // link.
    match path_safety::preflight_artifact_at(&canonical_state, INDEX_DIR_RELATIVE)? {
        path_safety::ArtifactKind::Directory => {
            let index_dir = canonical_state.join(INDEX_DIR_RELATIVE);
            let _ = std::fs::remove_dir(&index_dir); // best-effort; may fail if not empty
        }
        path_safety::ArtifactKind::Absent => {}
        path_safety::ArtifactKind::RegularFile => {
            // Defensive: the full preflight above already rejected a
            // regular-file index dir. Do not remove a wrong-kind artifact.
        }
    }

    Ok(PurgeResult {
        purged: true,
        removed_paths: removed,
    })
}

// ── Search ─────────────────────────────────────────────────────────────

/// Stats from a persistent BM25 search.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SearchStats {
    pub query_ms: u64,
    pub materialize_ms: u64,
    pub stale_hits_skipped: u64,
    pub invalid_hits_skipped: u64,
}

/// Error returned when policy hash doesn't match.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PolicyMismatchError {
    pub manifest_policy_hash: String,
    pub current_policy_hash: String,
}

/// Search the persistent BM25 index. Every hit is re-verified against
/// the current filesystem: content_sha compared, range validated,
/// and line-level query token scoring performed.
/// Stale or invalid hits are skipped (not emitted as stale evidence).
///
/// Policy gate: if manifest policy_hash doesn't match current policy,
/// returns an error — refuses to search a stale-policy index.
/// Schema gate: refuses if schema_version doesn't match.
/// Strategy gate (R8): refuses if chunk_strategy is unrecognized or missing.
///
/// Legacy entry point: assumes colocated mode. Delegates to
/// [`search_persistent_bm25_at_state_root`].
pub fn search_persistent_bm25(
    repo_root: &Path,
    query: &str,
    max_results: usize,
    policy: &Policy,
) -> Result<(Vec<Evidence>, SearchStats)> {
    search_persistent_bm25_at_state_root(repo_root, repo_root, query, max_results, policy)
}

/// Collect enough scored documents to include the complete score tie at the
/// requested boundary. Tantivy's default tie order uses process-local
/// document addresses, which may change after an otherwise identical index
/// rebuild. Expanding until the collector tail is strictly below the target
/// boundary makes the later path/range ordering authoritative.
fn collect_deterministic_top_docs(
    searcher: &Searcher,
    query: &dyn Query,
    requested_limit: usize,
) -> Result<Vec<(Score, DocAddress)>> {
    if requested_limit == 0 {
        return Ok(Vec::new());
    }
    let document_count = usize::try_from(searcher.num_docs()).unwrap_or(usize::MAX);
    if document_count == 0 {
        return Ok(Vec::new());
    }

    let target = requested_limit.min(document_count);
    let mut probe_limit = target;
    loop {
        let documents = searcher.search(query, &TopDocs::with_limit(probe_limit))?;
        if documents.len() < probe_limit || probe_limit >= document_count {
            return Ok(documents);
        }

        let boundary_score = documents[target - 1].0;
        let tail_score = documents
            .last()
            .expect("a full positive TopDocs probe must have a tail")
            .0;
        if boundary_score.total_cmp(&tail_score).is_gt() {
            return Ok(documents);
        }

        let next_limit = probe_limit.saturating_mul(2).min(document_count);
        if next_limit == probe_limit {
            return Ok(documents);
        }
        probe_limit = next_limit;
    }
}

fn sort_dedup_and_truncate_bm25_results(results: &mut Vec<Evidence>, max_results: usize) {
    let mut best_by_cell: BTreeMap<(String, u64, u64, String), Evidence> = BTreeMap::new();
    for evidence in results.drain(..) {
        let key = (
            evidence.core.path.clone(),
            evidence.core.start_line,
            evidence.core.end_line,
            evidence.core.content_sha.clone(),
        );
        match best_by_cell.entry(key) {
            std::collections::btree_map::Entry::Vacant(entry) => {
                entry.insert(evidence);
            }
            std::collections::btree_map::Entry::Occupied(mut entry) => {
                if evidence
                    .core
                    .score
                    .total_cmp(&entry.get().core.score)
                    .is_gt()
                {
                    entry.insert(evidence);
                }
            }
        }
    }
    results.extend(best_by_cell.into_values());
    results.sort_by(|a, b| {
        b.core
            .score
            .total_cmp(&a.core.score)
            .then_with(|| a.core.path.cmp(&b.core.path))
            .then_with(|| a.core.start_line.cmp(&b.core.start_line))
            .then_with(|| a.core.end_line.cmp(&b.core.end_line))
            .then_with(|| a.core.content_sha.cmp(&b.core.content_sha))
    });
    results.truncate(max_results);
}

/// Persistent BM25 search with explicit source/state roots.
///
/// - Tantivy index and manifest are read from `state_root`.
/// - Every hit is re-verified against the current filesystem by re-reading
///   from `source_root` via `validate_path(source_root, ...)`. Stale or
///   invalid hits are skipped. Currentness remains authoritative source
///   re-read; the Tantivy index is never trusted as Evidence.
pub fn search_persistent_bm25_at_state_root(
    source_root: &Path,
    state_root: &Path,
    query: &str,
    max_results: usize,
    policy: &Policy,
) -> Result<(Vec<Evidence>, SearchStats)> {
    validate_separated_roots(source_root, state_root)?;
    let canonical_state = path_safety::canonicalize_state_root(state_root)?;
    let query_start = Instant::now();

    // B0: preflight the Tantivy subtree before path-based read/open so
    // later Tantivy operations cannot follow descendants.
    path_safety::preflight_artifact_subtree(&canonical_state, TANTIVY_DIR_RELATIVE)?;
    let tantivy_dir = canonical_state.join(TANTIVY_DIR_RELATIVE);
    if tantivy_dir.symlink_metadata().is_err() {
        return Ok((
            vec![],
            SearchStats {
                query_ms: 0,
                materialize_ms: 0,
                stale_hits_skipped: 0,
                invalid_hits_skipped: 0,
            },
        ));
    }

    // Manifest/policy/schema/strategy gate — all from STATE root.
    // B0: checked existence — unsafe manifest rejects fail-closed.
    let manifest_present = path_safety::checked_exists(&canonical_state, MANIFEST_PATH_RELATIVE)?;
    if !manifest_present {
        bail!("persistent index manifest missing; rebuild the index with 'openlocus index build'");
    }

    let manifest = IndexManifest::load_at_state_root(state_root)?;
    let current_policy_hash = compute_policy_hash(policy);
    if manifest.policy_hash != current_policy_hash {
        bail!(
            "persistent index policy hash mismatch: manifest={}, current={}. Rebuild the index with 'openlocus index build'",
            manifest.policy_hash,
            current_policy_hash
        );
    }
    // Schema gate
    if manifest.schema_version != SCHEMA_VERSION && manifest.schema_version != SCHEMA_VERSION_R7 {
        bail!(
            "persistent index schema version mismatch: manifest={}, current={}. Rebuild the index with 'openlocus index build'",
            manifest.schema_version,
            SCHEMA_VERSION
        );
    }
    // Strategy gate (R8): chunk_strategy must be recognized
    if manifest.chunk_strategy != ChunkStrategy::LineWindowV1
        && manifest.chunk_strategy != ChunkStrategy::AstV1
    {
        bail!(
            "persistent index chunk strategy unrecognized: {:?}. Rebuild the index with 'openlocus index build'",
            manifest.chunk_strategy
        );
    }

    let index = Index::open_in_dir(&tantivy_dir)?;
    let schema = index.schema();

    // Find field handles by name
    let path_field = schema.get_field("path")?;
    let language_field = schema.get_field("language")?;
    let content_sha_field = schema.get_field("content_sha")?;
    let start_line_field = schema.get_field("start_line")?;
    let end_line_field = schema.get_field("end_line")?;
    let content_field = schema.get_field("content")?;

    let reader = index
        .reader_builder()
        .reload_policy(ReloadPolicy::Manual)
        .try_into()?;
    let searcher = reader.searcher();

    // Parse query
    let query_parser = QueryParser::for_index(&index, vec![content_field]);
    let parsed_query = match query_parser.parse_query(query) {
        Ok(p) => p,
        Err(_) => {
            let sanitized = query.replace([':', '/', '(', ')', '"'], " ");
            match query_parser.parse_query(sanitized.trim()) {
                Ok(p) => p,
                Err(_) => {
                    return Ok((
                        vec![],
                        SearchStats {
                            query_ms: query_start.elapsed().as_millis() as u64,
                            materialize_ms: 0,
                            stale_hits_skipped: 0,
                            invalid_hits_skipped: 0,
                        },
                    ));
                }
            }
        }
    };

    let top_docs = collect_deterministic_top_docs(
        &searcher,
        parsed_query.as_ref(),
        max_results.saturating_mul(2),
    )?;

    let query_ms = query_start.elapsed().as_millis() as u64;

    // Tokenize with the content field's actual Tantivy analyzer so the
    // line-level verifier cannot disagree with the index/query parser about
    // punctuation, underscores, one-character terms, or long-token removal.
    let query_tokens = tokenize_query(&index, content_field, query)?;

    let materialize_start = Instant::now();
    let mut results = Vec::new();
    let mut stale_hits_skipped: u64 = 0;
    let mut invalid_hits_skipped: u64 = 0;

    for (_score, doc_address) in top_docs {
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

        // Empty content_sha → cannot verify stale check → skip
        if index_content_sha.is_empty() {
            invalid_hits_skipped += 1;
            continue;
        }

        // Path safety: validate_path against SOURCE root before reading file
        if validate_path(source_root, &path_val).is_err() {
            invalid_hits_skipped += 1;
            continue;
        }

        // Re-read the current file from SOURCE root (mandatory verification)
        let full_path = source_root.join(&path_val);
        let content = match std::fs::read_to_string(&full_path) {
            Ok(c) => c,
            Err(_) => {
                invalid_hits_skipped += 1;
                continue;
            }
        };

        // Compute current content_sha and compare (stale check)
        let current_content_sha = blake3::hash(content.as_bytes()).to_hex().to_string();
        if index_content_sha != current_content_sha {
            stale_hits_skipped += 1;
            continue;
        }

        let lines: Vec<&str> = content.lines().collect();
        let total_lines = lines.len() as u64;

        if total_lines == 0 {
            invalid_hits_skipped += 1;
            continue;
        }

        // Strict chunk range validation: 1 ≤ start ≤ end ≤ total_lines; no clamping
        if chunk_start_line < 1 || chunk_start_line > chunk_end_line || chunk_end_line > total_lines
        {
            invalid_hits_skipped += 1;
            continue;
        }

        // Line-level scoring: find the best-matching line
        let best_line =
            find_best_matching_line(&lines, chunk_start_line, chunk_end_line, &query_tokens);

        let best_line = match best_line {
            Some(l) => l,
            None => {
                // No query token overlap — skip (precision-biased)
                invalid_hits_skipped += 1;
                continue;
            }
        };

        // Tighten around best line ± context, cap at MAX_EVIDENCE_SPAN
        let tight_start = best_line.saturating_sub(CONTEXT_LINES).max(1);
        let mut tight_end = (best_line + CONTEXT_LINES).min(total_lines);
        tight_end = tight_end.min(tight_start + MAX_EVIDENCE_SPAN - 1);
        let tight_start = tight_start.max(1);
        let tight_end = tight_end.min(total_lines);

        // Strict guard: 1 ≤ start ≤ end ≤ total_lines
        if tight_start < 1 || tight_start > tight_end || tight_end > total_lines {
            invalid_hits_skipped += 1;
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
            vec![format!("persistent_bm25: {}", query)],
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

    sort_dedup_and_truncate_bm25_results(&mut results, max_results);

    let materialize_ms = materialize_start.elapsed().as_millis() as u64;

    Ok((
        results,
        SearchStats {
            query_ms,
            materialize_ms,
            stale_hits_skipped,
            invalid_hits_skipped,
        },
    ))
}

// ── Reusable index handle ─────────────────────────────────────────────

/// A reusable persistent BM25 index handle that opens once and can be
/// queried multiple times without re-opening the Tantivy index.
///
/// **Source-root binding (oracle blocker closure):** the handle binds the
/// canonical source root and canonical state root at open time (via
/// [`Self::open_at_state_root`]). Every search — including legacy
/// [`Self::search`] — must be called with a source root that canonicalizes
/// to the **same** canonical source bound at open time. A different source
/// root is rejected explicitly before query/materialization, even if it
/// contains the same relative paths and identical bytes. This closes
/// wrong-source contamination of a Phase B comparison cell where an index
/// built from source A could otherwise be searched against source B. The
/// bound roots are private fields; there is no new public canonical API.
pub struct PersistentBm25Index {
    index: Index,
    searcher: tantivy::Searcher,
    path_field: Field,
    language_field: Field,
    content_sha_field: Field,
    start_line_field: Field,
    end_line_field: Field,
    content_field: Field,
    /// Canonical source root bound at open time. All search-time
    /// `validate_path` / `join` / current-content rereads MUST use this,
    /// not a caller-provided path. Private: no new public canonical API.
    canonical_source: PathBuf,
    /// Canonical state root bound at open time. The Tantivy index and
    /// manifest were opened from here. Private: no new public canonical API.
    canonical_state: PathBuf,
}

impl PersistentBm25Index {
    /// Open the persistent BM25 index for reuse.
    /// Validates policy hash, schema version, and chunk strategy.
    /// Returns error if index doesn't exist or policy/schema/strategy mismatches.
    ///
    /// Legacy entry point: assumes colocated mode. Delegates to
    /// [`Self::open_at_state_root`].
    pub fn open(repo_root: &Path, policy: &Policy) -> Result<Self> {
        Self::open_at_state_root(repo_root, repo_root, policy)
    }

    /// Open the persistent BM25 index for reuse with explicit source/state roots.
    ///
    /// The Tantivy index and manifest are opened from `state_root`. The
    /// `source_root` is **bound** to the handle: it is canonicalized
    /// fail-closed and stored on the handle, and every subsequent search
    /// (including legacy [`Self::search`]) must be called with a source
    /// root that canonicalizes to the **same** canonical source. A
    /// different source root is rejected explicitly before
    /// query/materialization. This prevents wrong-source contamination
    /// where an index built from source A could otherwise be searched
    /// against source B.
    ///
    /// Canonical aliases resolving to the exact same canonical source
    /// directory are accepted (comparison is by canonical equality, not
    /// lexical string equality).
    ///
    /// Policy/schema/strategy gates use the manifest from `state_root` and
    /// the caller-provided `policy` (which the caller should load from
    /// `source_root`).
    pub fn open_at_state_root(
        source_root: &Path,
        state_root: &Path,
        policy: &Policy,
    ) -> Result<Self> {
        // Validate separation AND get the canonical source in a single
        // canonicalization (avoids a second inconsistent canonicalization).
        let canonical_source = validate_separated_roots_canonical(source_root, state_root)?;
        let canonical_state = path_safety::canonicalize_state_root(state_root)?;

        // B0: preflight the Tantivy subtree before opening (so later
        // Tantivy operations cannot follow descendants).
        path_safety::preflight_artifact_subtree(&canonical_state, TANTIVY_DIR_RELATIVE)?;
        let tantivy_dir = canonical_state.join(TANTIVY_DIR_RELATIVE);
        if tantivy_dir.symlink_metadata().is_err() {
            bail!("persistent index does not exist; run 'openlocus index build' first");
        }

        // Manifest/policy/schema/strategy gate — all from STATE root.
        // B0: checked existence — unsafe manifest rejects fail-closed.
        let manifest_present =
            path_safety::checked_exists(&canonical_state, MANIFEST_PATH_RELATIVE)?;
        if !manifest_present {
            bail!("persistent index manifest missing; rebuild the index");
        }

        let manifest = IndexManifest::load_at_state_root(state_root)?;
        let current_policy_hash = compute_policy_hash(policy);
        if manifest.policy_hash != current_policy_hash {
            bail!(
                "persistent index policy hash mismatch: manifest={}, current={}. Rebuild the index",
                manifest.policy_hash,
                current_policy_hash
            );
        }
        if manifest.schema_version != SCHEMA_VERSION && manifest.schema_version != SCHEMA_VERSION_R7
        {
            bail!(
                "persistent index schema version mismatch: manifest={}, current={}. Rebuild the index",
                manifest.schema_version,
                SCHEMA_VERSION
            );
        }
        if manifest.chunk_strategy != ChunkStrategy::LineWindowV1
            && manifest.chunk_strategy != ChunkStrategy::AstV1
        {
            bail!(
                "persistent index chunk strategy unrecognized: {:?}. Rebuild the index",
                manifest.chunk_strategy
            );
        }

        let index = Index::open_in_dir(&tantivy_dir)?;
        let schema = index.schema();

        let path_field = schema.get_field("path")?;
        let language_field = schema.get_field("language")?;
        let content_sha_field = schema.get_field("content_sha")?;
        let start_line_field = schema.get_field("start_line")?;
        let end_line_field = schema.get_field("end_line")?;
        let content_field = schema.get_field("content")?;

        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::Manual)
            .try_into()?;
        let searcher = reader.searcher();

        Ok(Self {
            index,
            searcher,
            path_field,
            language_field,
            content_sha_field,
            start_line_field,
            end_line_field,
            content_field,
            canonical_source,
            canonical_state,
        })
    }

    /// Search using this opened index handle. Same safety gates as
    /// search_persistent_bm25: validate_path, empty sha skip, strict range.
    ///
    /// Legacy entry point: assumes colocated mode. Delegates to
    /// [`Self::search_at_source_root`].
    pub fn search(
        &self,
        repo_root: &Path,
        query: &str,
        max_results: usize,
    ) -> Result<(Vec<Evidence>, SearchStats)> {
        self.search_at_source_root(repo_root, query, max_results)
    }

    /// Search using this opened index handle, re-reading current source from
    /// the source root **bound at open time** (via
    /// [`Self::open_at_state_root`]).
    ///
    /// **Source-root binding (oracle blocker closure):** BEFORE
    /// query/search/materialization, the caller-provided `source_root` is
    /// canonicalized fail-closed and required to equal the handle's bound
    /// canonical source. A different source root is rejected explicitly —
    /// even if it contains the same relative paths and identical bytes —
    /// so an index built from source A cannot be searched against source B.
    /// The supported source/state overlap relationship is then re-run
    /// against the bound canonical roots so the search operation itself
    /// cannot bypass the split-root relation. All `validate_path` / `join` /
    /// current-content rereads use the **handle's** bound canonical source,
    /// not the caller path.
    ///
    /// Canonical aliases resolving to the exact same canonical source
    /// directory are accepted (comparison is by canonical equality, not
    /// lexical string equality).
    ///
    /// Same hit-level safety gates as
    /// [`search_persistent_bm25_at_state_root`]: empty sha skip, strict
    /// range. Every hit is re-verified against the current source
    /// filesystem.
    pub fn search_at_source_root(
        &self,
        source_root: &Path,
        query: &str,
        max_results: usize,
    ) -> Result<(Vec<Evidence>, SearchStats)> {
        // ── Source-root binding gate (before query/search/materialization) ──
        //
        // Canonicalize the caller path fail-closed, then require canonical
        // equality with the bound source. This closes wrong-source
        // contamination even when the wrong source contains the same
        // relative path and identical bytes (the hash match would otherwise
        // pass stale filtering, contaminating a Phase B comparison cell).
        let canonical_caller_source = source_root.canonicalize().with_context(|| {
            format!(
                "source root does not exist or cannot be canonicalized: {}",
                source_root.display()
            )
        })?;
        if canonical_caller_source != self.canonical_source {
            bail!(
                "source root mismatch: persistent index handle was opened with source {} but search was called with source {}. The handle binds the source root at open time; reopen the index with the intended source root.",
                self.canonical_source.display(),
                canonical_caller_source.display()
            );
        }
        // Defense-in-depth: re-run the supported source/state overlap
        // relationship against the bound canonical roots so the search
        // operation itself cannot bypass the split-root relation.
        validate_separated_roots(&self.canonical_source, &self.canonical_state)?;

        // All validate_path / join / current-content rereads use the
        // HANDLE'S bound canonical source, not the caller path.
        let bound_source: &Path = &self.canonical_source;

        let query_start = Instant::now();

        let query_parser = QueryParser::for_index(&self.index, vec![self.content_field]);
        let parsed_query = match query_parser.parse_query(query) {
            Ok(p) => p,
            Err(_) => {
                let sanitized = query.replace([':', '/', '(', ')', '"'], " ");
                match query_parser.parse_query(sanitized.trim()) {
                    Ok(p) => p,
                    Err(_) => {
                        return Ok((
                            vec![],
                            SearchStats {
                                query_ms: query_start.elapsed().as_millis() as u64,
                                materialize_ms: 0,
                                stale_hits_skipped: 0,
                                invalid_hits_skipped: 0,
                            },
                        ));
                    }
                }
            }
        };

        let top_docs = collect_deterministic_top_docs(
            &self.searcher,
            parsed_query.as_ref(),
            max_results.saturating_mul(2),
        )?;

        let query_ms = query_start.elapsed().as_millis() as u64;
        let query_tokens = tokenize_query(&self.index, self.content_field, query)?;

        let materialize_start = Instant::now();
        let mut results = Vec::new();
        let mut stale_hits_skipped: u64 = 0;
        let mut invalid_hits_skipped: u64 = 0;

        for (_score, doc_address) in top_docs {
            let doc: TantivyDocument = self.searcher.doc(doc_address)?;
            let path_val = doc
                .get_first(self.path_field)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let index_content_sha = doc
                .get_first(self.content_sha_field)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let chunk_start_line = doc
                .get_first(self.start_line_field)
                .and_then(|v| v.as_u64())
                .unwrap_or(1);
            let chunk_end_line = doc
                .get_first(self.end_line_field)
                .and_then(|v| v.as_u64())
                .unwrap_or(1);
            let language_val = doc
                .get_first(self.language_field)
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
                .to_string();

            // Empty content_sha → cannot verify → skip
            if index_content_sha.is_empty() {
                invalid_hits_skipped += 1;
                continue;
            }

            // Path safety against the HANDLE'S bound canonical source.
            if validate_path(bound_source, &path_val).is_err() {
                invalid_hits_skipped += 1;
                continue;
            }

            // Re-read current file from the HANDLE'S bound canonical source.
            let full_path = bound_source.join(&path_val);
            let content = match std::fs::read_to_string(&full_path) {
                Ok(c) => c,
                Err(_) => {
                    invalid_hits_skipped += 1;
                    continue;
                }
            };

            // Stale check
            let current_content_sha = blake3::hash(content.as_bytes()).to_hex().to_string();
            if index_content_sha != current_content_sha {
                stale_hits_skipped += 1;
                continue;
            }

            let lines: Vec<&str> = content.lines().collect();
            let total_lines = lines.len() as u64;

            if total_lines == 0 {
                invalid_hits_skipped += 1;
                continue;
            }

            // Strict range validation: no clamping
            if chunk_start_line < 1
                || chunk_start_line > chunk_end_line
                || chunk_end_line > total_lines
            {
                invalid_hits_skipped += 1;
                continue;
            }

            // Line-level scoring
            let best_line =
                find_best_matching_line(&lines, chunk_start_line, chunk_end_line, &query_tokens);

            let best_line = match best_line {
                Some(l) => l,
                None => {
                    invalid_hits_skipped += 1;
                    continue;
                }
            };

            // Tighten around best line
            let tight_start = best_line.saturating_sub(CONTEXT_LINES).max(1);
            let mut tight_end = (best_line + CONTEXT_LINES).min(total_lines);
            tight_end = tight_end.min(tight_start + MAX_EVIDENCE_SPAN - 1);
            let tight_start = tight_start.max(1);
            let tight_end = tight_end.min(total_lines);

            if tight_start < 1 || tight_start > tight_end || tight_end > total_lines {
                invalid_hits_skipped += 1;
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
                vec![format!("persistent_bm25: {}", query)],
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

        sort_dedup_and_truncate_bm25_results(&mut results, max_results);

        let materialize_ms = materialize_start.elapsed().as_millis() as u64;

        Ok((
            results,
            SearchStats {
                query_ms,
                materialize_ms,
                stale_hits_skipped,
                invalid_hits_skipped,
            },
        ))
    }
}

// ── Helpers ────────────────────────────────────────────────────────────

/// Tokenize a query with the exact analyzer configured for the persistent
/// content field.
///
/// The prior verifier used an independent hand-written splitter and dropped
/// every token beginning with `_`.  Tantivy's default analyzer instead splits
/// `_private_symbol` into `private` and `symbol`, so the index could return a
/// hit that the verifier then rejected as having no line-level overlap.  By
/// resolving the tokenizer from the field schema, indexing, query parsing, and
/// current-source line verification share one token contract.
fn tokenize_query(index: &Index, content_field: Field, query: &str) -> Result<Vec<String>> {
    let schema = index.schema();
    let field_entry = schema.get_field_entry(content_field);
    let FieldType::Str(text_options) = field_entry.field_type() else {
        bail!("persistent content field is not text");
    };
    let indexing = text_options
        .get_indexing_options()
        .context("persistent content field is not indexed")?;
    let tokenizer_name = indexing.tokenizer();
    let mut analyzer = index.tokenizers().get(tokenizer_name).with_context(|| {
        format!("persistent content tokenizer {tokenizer_name:?} is unavailable")
    })?;
    let mut stream = analyzer.token_stream(query);
    let mut tokens = Vec::new();
    stream.process(&mut |token| tokens.push(token.text.clone()));
    Ok(tokens)
}

/// Find the line within [start_line, end_line] that has the highest query
/// token overlap score. Returns None if no line has any overlap.
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

    if best_score > 0 { best_line } else { None }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn compute_sha(root: &Path, path: &str) -> String {
        let bytes = std::fs::read(root.join(path)).unwrap();
        blake3::hash(&bytes).to_hex().to_string()
    }

    fn write_file(root: &Path, path: &str, content: &str) {
        let full_path = root.join(path);
        if let Some(parent) = full_path.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(full_path, content).unwrap();
    }

    fn file_record(root: &Path, path: &str) -> FileRecord {
        FileRecord {
            path: path.into(),
            size: std::fs::metadata(root.join(path))
                .map(|m| m.len())
                .unwrap_or(0),
            content_sha: compute_sha(root, path),
            language: "rust".into(),
        }
    }

    fn assert_current_evidence(root: &Path, evidence: &Evidence, path: &str, needle: &str) {
        assert_eq!(evidence.core.path, path);
        assert_eq!(evidence.core.content_sha, compute_sha(root, path));
        assert!(evidence.core.start_line >= 1);
        assert!(evidence.core.start_line <= evidence.core.end_line);
        let content = std::fs::read_to_string(root.join(path)).unwrap();
        let lines: Vec<&str> = content.lines().collect();
        assert!(evidence.core.end_line <= lines.len() as u64);
        let excerpt = lines
            [(evidence.core.start_line - 1) as usize..evidence.core.end_line as usize]
            .join("\n");
        let meta = evidence.meta.as_ref().unwrap();
        assert_eq!(meta.excerpt.as_deref(), Some(excerpt.as_str()));
        assert!(excerpt.contains(needle), "excerpt was: {excerpt}");
        assert_eq!(meta.freshness, Some(Freshness::VerifiedCurrent));
    }

    #[cfg(unix)]
    fn symlink_file(src: &Path, dst: &Path) -> std::io::Result<()> {
        std::os::unix::fs::symlink(src, dst)
    }

    #[cfg(windows)]
    fn symlink_file(src: &Path, dst: &Path) -> std::io::Result<()> {
        std::os::windows::fs::symlink_file(src, dst)
    }

    #[cfg(unix)]
    fn symlink_dir(src: &Path, dst: &Path) -> std::io::Result<()> {
        std::os::unix::fs::symlink(src, dst)
    }

    #[cfg(windows)]
    fn symlink_dir(src: &Path, dst: &Path) -> std::io::Result<()> {
        std::os::windows::fs::symlink_dir(src, dst)
    }

    #[cfg(windows)]
    fn symlink_unavailable_for_test(err: &std::io::Error) -> bool {
        err.raw_os_error() == Some(1314)
    }

    #[cfg(not(windows))]
    fn symlink_unavailable_for_test(_err: &std::io::Error) -> bool {
        false
    }

    fn create_symlink_file_for_test(src: &Path, dst: &Path) -> bool {
        match symlink_file(src, dst) {
            Ok(()) => true,
            Err(err) if symlink_unavailable_for_test(&err) => false,
            Err(err) => panic!("failed to create symlink test fixture: {err}"),
        }
    }

    fn create_symlink_dir_for_test(src: &Path, dst: &Path) -> bool {
        match symlink_dir(src, dst) {
            Ok(()) => true,
            Err(err) if symlink_unavailable_for_test(&err) => false,
            Err(err) => panic!("failed to create symlink dir test fixture: {err}"),
        }
    }

    fn manifest_entry(root: &Path, path: &str) -> ManifestFileEntry {
        let manifest = IndexManifest::load(root).unwrap();
        manifest
            .files
            .into_iter()
            .find(|entry| entry.path == path)
            .unwrap()
    }

    // ── Separated root tests (B0) ───────────────────────────────────────

    /// Helper: build a small source tree under `source_root`.
    fn write_source_tree(source_root: &Path) {
        write_file(
            source_root,
            "src/app.rs",
            "fn authenticate_user() {}\nfn process_request() {}\n",
        );
        write_file(
            source_root,
            "src/lib.rs",
            "struct Config {\n    name: String,\n}\n",
        );
    }

    /// Helper: compute blake3 of a file under `root`.
    fn source_digest(root: &Path, path: &str) -> String {
        compute_sha(root, path)
    }

    /// Test 1: legacy APIs write to repo_root/.openlocus/index.
    #[test]
    fn legacy_apis_use_repo_root_openlocus_index() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_source_tree(root);

        let policy = Policy::default();
        let records = vec![
            file_record(root, "src/app.rs"),
            file_record(root, "src/lib.rs"),
        ];

        let result = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        assert!(result.success);

        // Legacy layout: artifacts under repo_root/.openlocus/index
        assert!(root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(root.join(MANIFEST_PATH_RELATIVE).exists());
        assert!(IndexManifest::exists(root));
        assert!(IndexManifest::exists_at_state_root(root));

        // Legacy status/dirty/validate/search all work via repo_root
        let status = status_index(root, &policy).unwrap();
        assert!(status.exists);

        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(dirty.clean);

        let validate = validate_index(root, &policy).unwrap();
        assert!(validate.valid);

        let (evidence, _stats) = search_persistent_bm25(root, "authenticate", 10, &policy).unwrap();
        assert!(!evidence.is_empty());

        let handle = PersistentBm25Index::open(root, &policy).unwrap();
        let (h_ev, _h_stats) = handle.search(root, "authenticate", 10).unwrap();
        assert!(!h_ev.is_empty());

        let purged = purge_index(root).unwrap();
        assert!(purged.purged);
        assert!(!root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(!root.join(MANIFEST_PATH_RELATIVE).exists());
    }

    /// Test 2: separated build/status/dirty/update/validate/search/open/purge
    /// all use state root; no source-root `.openlocus` created; source digest
    /// and file list unchanged.
    #[test]
    fn separated_build_writes_to_state_root_only() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        // Snapshot source digests before build
        let app_sha_before = source_digest(source_root, "src/app.rs");
        let lib_sha_before = source_digest(source_root, "src/lib.rs");

        let policy = Policy::default();
        let records = vec![
            file_record(source_root, "src/app.rs"),
            file_record(source_root, "src/lib.rs"),
        ];

        let result = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        assert!(result.success);
        assert_eq!(result.file_count, 2);

        // State root has the index artifacts
        assert!(state_root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(state_root.join(MANIFEST_PATH_RELATIVE).exists());
        assert!(IndexManifest::exists_at_state_root(state_root));

        // Source root has NO .openlocus directory at all
        assert!(
            !source_root.join(".openlocus").exists(),
            "source root must not have .openlocus created in separated mode"
        );

        // Source digests unchanged
        assert_eq!(source_digest(source_root, "src/app.rs"), app_sha_before);
        assert_eq!(source_digest(source_root, "src/lib.rs"), lib_sha_before);

        // Source file list unchanged (only the two we wrote)
        let mut source_files: Vec<String> = std::fs::read_dir(source_root)
            .unwrap()
            .map(|e| e.unwrap().file_name().to_string_lossy().to_string())
            .collect();
        source_files.sort();
        assert_eq!(source_files, vec!["src".to_string()]);
    }

    #[test]
    fn separated_status_uses_state_root_and_source_for_currentness() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // status reads manifest from state_root, files from source_root
        let status = status_index_at_state_root(source_root, state_root, &policy).unwrap();
        assert!(status.exists);
        assert!(!status.requires_rebuild);

        // Modify source file → status should detect stale via source re-read
        write_file(source_root, "src/app.rs", "fn changed() {}\nfn more() {}\n");
        let status2 = status_index_at_state_root(source_root, state_root, &policy).unwrap();
        assert!(status2.requires_rebuild);
        assert_eq!(status2.stale_files_fast, Some(1));
    }

    #[test]
    fn separated_dirty_uses_state_root_and_source_for_currentness() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let dirty = dirty_index_at_state_root(source_root, state_root, &policy, &records).unwrap();
        assert!(dirty.clean);

        // Modify source → dirty should detect via source re-read
        write_file(source_root, "src/app.rs", "fn modified_after_build() {}\n");
        let dirty2 = dirty_index_at_state_root(source_root, state_root, &policy, &records).unwrap();
        assert!(!dirty2.clean);
        assert!(dirty2.modified_files.contains(&"src/app.rs".to_string()));
    }

    #[test]
    fn separated_validate_uses_state_root_and_source_for_currentness() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let validate = validate_index_at_state_root(source_root, state_root, &policy).unwrap();
        assert!(validate.valid);

        // Modify source → validate should report stale
        write_file(source_root, "src/app.rs", "fn stale_after_build() {}\n");
        let validate2 = validate_index_at_state_root(source_root, state_root, &policy).unwrap();
        assert!(!validate2.valid);
        assert!(validate2.stale_files.contains(&"src/app.rs".to_string()));
    }

    #[test]
    fn separated_search_uses_state_root_index_and_source_for_reread() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let (evidence, stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "authenticate",
            10,
            &policy,
        )
        .unwrap();
        assert!(!evidence.is_empty(), "should find matches via state index");
        assert_eq!(evidence[0].core.path, "src/app.rs");
        assert_eq!(stats.stale_hits_skipped, 0);

        // Evidence must be re-verified against source content
        assert_current_evidence(source_root, &evidence[0], "src/app.rs", "authenticate");
    }

    #[test]
    fn persistent_bm25_equal_score_boundary_ignores_index_insertion_order() {
        let dir = tempfile::tempdir().unwrap();
        let source_root = dir.path().join("source");
        let state_a = dir.path().join("state-a");
        let state_b = dir.path().join("state-b");
        std::fs::create_dir_all(source_root.join("src")).unwrap();
        std::fs::create_dir_all(&state_a).unwrap();
        std::fs::create_dir_all(&state_b).unwrap();

        for index in 0..48 {
            write_file(
                &source_root,
                &format!("src/item_{index:03}.rs"),
                "pub fn stableboundarytoken() {}\n",
            );
        }
        let mut records: Vec<FileRecord> = (0..48)
            .map(|index| file_record(&source_root, &format!("src/item_{index:03}.rs")))
            .collect();
        let policy = Policy::default();
        build_index_at_state_root(
            &source_root,
            &state_a,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        records.reverse();
        build_index_at_state_root(
            &source_root,
            &state_b,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let search = |state_root: &Path| {
            let (evidence, stats) = search_persistent_bm25_at_state_root(
                &source_root,
                state_root,
                "stableboundarytoken",
                5,
                &policy,
            )
            .unwrap();
            assert_eq!(stats.stale_hits_skipped, 0);
            assert_eq!(stats.invalid_hits_skipped, 0);
            evidence
                .into_iter()
                .map(|item| {
                    (
                        item.core.path,
                        item.core.start_line,
                        item.core.end_line,
                        item.core.score.to_bits(),
                    )
                })
                .collect::<Vec<_>>()
        };
        let first = search(&state_a);
        let second = search(&state_b);
        assert_eq!(first, second);
        assert_eq!(
            first.iter().map(|item| item.0.clone()).collect::<Vec<_>>(),
            (0..5)
                .map(|index| format!("src/item_{index:03}.rs"))
                .collect::<Vec<_>>()
        );

        let search_open_handle = |state_root: &Path| {
            let handle =
                PersistentBm25Index::open_at_state_root(&source_root, state_root, &policy).unwrap();
            let (evidence, stats) = handle
                .search_at_source_root(&source_root, "stableboundarytoken", 5)
                .unwrap();
            assert_eq!(stats.stale_hits_skipped, 0);
            assert_eq!(stats.invalid_hits_skipped, 0);
            evidence
                .into_iter()
                .map(|item| {
                    (
                        item.core.path,
                        item.core.start_line,
                        item.core.end_line,
                        item.core.score.to_bits(),
                    )
                })
                .collect::<Vec<_>>()
        };
        assert_eq!(search_open_handle(&state_a), first);
        assert_eq!(search_open_handle(&state_b), first);
    }

    #[test]
    #[ignore = "large synthetic determinism stress; run via the Linux stress script"]
    fn persistent_bm25_large_equal_score_boundary_stress() {
        let file_count = std::env::var("OPENLOCUS_DETERMINISM_STRESS_FILES")
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(20_000);
        assert!((32..=100_000).contains(&file_count));

        let dir = tempfile::tempdir().unwrap();
        let source_root = dir.path().join("source");
        let state_a = dir.path().join("state-a");
        let state_b = dir.path().join("state-b");
        std::fs::create_dir_all(source_root.join("src")).unwrap();
        std::fs::create_dir_all(&state_a).unwrap();
        std::fs::create_dir_all(&state_b).unwrap();

        for index in 0..file_count {
            write_file(
                &source_root,
                &format!("src/item_{index:06}.rs"),
                "pub fn stableboundarytoken() {}\n",
            );
        }
        let mut records: Vec<FileRecord> = (0..file_count)
            .map(|index| file_record(&source_root, &format!("src/item_{index:06}.rs")))
            .collect();
        let policy = Policy::default();
        build_index_at_state_root(
            &source_root,
            &state_a,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        records.reverse();
        build_index_at_state_root(
            &source_root,
            &state_b,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let signature = |state_root: &Path| {
            let (evidence, stats) = search_persistent_bm25_at_state_root(
                &source_root,
                state_root,
                "stableboundarytoken",
                64,
                &policy,
            )
            .unwrap();
            assert_eq!(stats.stale_hits_skipped, 0);
            assert_eq!(stats.invalid_hits_skipped, 0);
            evidence
                .into_iter()
                .map(|item| {
                    (
                        item.core.path,
                        item.core.start_line,
                        item.core.end_line,
                        item.core.score.to_bits(),
                    )
                })
                .collect::<Vec<_>>()
        };
        let first = signature(&state_a);
        assert_eq!(signature(&state_b), first);
        assert_eq!(
            first.iter().map(|item| item.0.clone()).collect::<Vec<_>>(),
            (0..64)
                .map(|index| format!("src/item_{index:06}.rs"))
                .collect::<Vec<_>>()
        );

        for state_root in [&state_a, &state_b] {
            let handle =
                PersistentBm25Index::open_at_state_root(&source_root, state_root, &policy).unwrap();
            let (evidence, stats) = handle
                .search_at_source_root(&source_root, "stableboundarytoken", 64)
                .unwrap();
            assert_eq!(stats.stale_hits_skipped, 0);
            assert_eq!(stats.invalid_hits_skipped, 0);
            let handle_signature = evidence
                .into_iter()
                .map(|item| {
                    (
                        item.core.path,
                        item.core.start_line,
                        item.core.end_line,
                        item.core.score.to_bits(),
                    )
                })
                .collect::<Vec<_>>();
            assert_eq!(handle_signature, first);
        }
    }

    #[test]
    fn separated_open_and_search_at_state_root() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let handle =
            PersistentBm25Index::open_at_state_root(source_root, state_root, &policy).unwrap();
        let (evidence, stats) = handle
            .search_at_source_root(source_root, "authenticate", 10)
            .unwrap();
        assert!(!evidence.is_empty());
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_current_evidence(source_root, &evidence[0], "src/app.rs", "authenticate");
    }

    // ── Oracle blocker: source-root binding closure (B0) ──────────────
    //
    // `PersistentBm25Index::open_at_state_root(A, state, policy)` must bind
    // the canonical source A; `search_at_source_root(B, ...)` must then
    // reject B before query/materialization, even when B contains the same
    // relative path and identical bytes. This closes wrong-source
    // contamination of a Phase B comparison cell where an index built from
    // A could otherwise be searched against B (hash match would pass stale
    // filtering). Legacy colocated open+search and canonical aliases remain
    // accepted.

    /// Test 1: wrong-source contamination closes even with matching
    /// content/hash. Build/open with source A + state; create source B
    /// containing the same relative path and identical bytes;
    /// `search_at_source_root(B, ...)` must return Err before
    /// search/materialization — not empty/stale filtering.
    #[test]
    fn search_at_source_root_rejects_wrong_source_even_with_matching_content() {
        let src_a_dir = tempfile::tempdir().unwrap();
        let src_b_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_a = src_a_dir.path();
        let source_b = src_b_dir.path();
        let state_root = state_dir.path();

        // Build identical source trees under A and B (same relative path,
        // identical bytes → same content_sha).
        write_source_tree(source_a);
        write_source_tree(source_b);

        let policy = Policy::default();
        let records = vec![file_record(source_a, "src/app.rs")];
        build_index_at_state_root(
            source_a,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Open with source A.
        let handle =
            PersistentBm25Index::open_at_state_root(source_a, state_root, &policy).unwrap();

        // Search with source B (same relative path, identical bytes) must
        // Err BEFORE search/materialization — not empty/stale filtering.
        let err = handle
            .search_at_source_root(source_b, "authenticate", 10)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("source root mismatch"),
            "wrong-source search must be rejected before search/materialization, got: {}",
            err
        );
        // The rejection must be at the source-binding gate, not a downstream
        // stale/invalid filter (which would contaminate the cell silently).
        assert!(
            !err.contains("stale") && !err.contains("invalid"),
            "rejection must be at the source-binding gate, not stale/invalid filtering"
        );
    }

    /// Test 2: legacy colocated `open(root)` + `search(root)` remains
    /// success after the source-root binding fix. The bound canonical
    /// source matches the canonicalized caller path.
    #[test]
    fn legacy_open_and_search_remains_success_after_binding_fix() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_source_tree(root);

        let policy = Policy::default();
        let records = vec![file_record(root, "src/app.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let handle = PersistentBm25Index::open(root, &policy).unwrap();
        let (evidence, stats) = handle.search(root, "authenticate", 10).unwrap();
        assert!(!evidence.is_empty());
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_current_evidence(root, &evidence[0], "src/app.rs", "authenticate");
    }

    /// Test 3: a canonical alias path resolving to the bound canonical
    /// source directory is accepted by canonical equality (not lexical
    /// string equality). Gated by symlink availability on the host.
    ///
    /// When symlinks are unavailable (e.g. Windows without admin
    /// privileges), the test documents the fail-closed rule and skips —
    /// path safety is NOT weakened. The fail-closed rule: a caller source
    /// that cannot be canonicalized (non-existent, dangling symlink, loop)
    /// is rejected at the source-binding gate before query/materialization.
    #[test]
    fn search_at_source_root_accepts_canonical_alias_of_bound_source() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let link_parent = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        // Create a symlink alias to the source root.
        let source_alias = link_parent.path().join("source-alias");
        if !create_symlink_dir_for_test(source_root, &source_alias) {
            eprintln!(
                "skipping canonical-alias test: symlinks unavailable on this host; \
                 fail-closed rule: a non-canonicalizable caller source is rejected \
                 at the source-binding gate (canonicalize fails fail-closed)"
            );
            return;
        }

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Open with the real source root.
        let handle =
            PersistentBm25Index::open_at_state_root(source_root, state_root, &policy).unwrap();

        // Search via the alias — must be accepted by canonical equality
        // (the alias canonicalizes to the bound canonical source).
        let (evidence, stats) = handle
            .search_at_source_root(&source_alias, "authenticate", 10)
            .unwrap();
        assert!(!evidence.is_empty());
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_current_evidence(source_root, &evidence[0], "src/app.rs", "authenticate");
    }

    /// Fail-closed: a non-existent caller source is rejected at the
    /// source-binding gate (canonicalization fails fail-closed), not later
    /// as stale/invalid filtering. Complements test 3's fail-closed rule.
    #[test]
    fn search_at_source_root_rejects_nonexistent_caller_source_fail_closed() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let handle =
            PersistentBm25Index::open_at_state_root(source_root, state_root, &policy).unwrap();

        let nonexistent_source = state_dir.path().join("nonexistent-source-root");
        let err = handle
            .search_at_source_root(&nonexistent_source, "authenticate", 10)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("source root does not exist or cannot be canonicalized"),
            "nonexistent caller source must be rejected fail-closed, got: {}",
            err
        );
    }

    #[test]
    fn separated_update_uses_state_root_for_writes_source_for_reads() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Modify source file
        write_file(
            source_root,
            "src/app.rs",
            "fn authorize() {}\nfn extra() {}\n",
        );
        let new_records = vec![file_record(source_root, "src/app.rs")];

        let result =
            update_index_at_state_root(source_root, state_root, &policy, &new_records, true, None)
                .unwrap();
        assert!(result.success);
        assert_eq!(result.modified_count, 1);
        assert!(result.post_status_clean);

        // New content is searchable; old term is not
        let (new_ev, _stats) =
            search_persistent_bm25_at_state_root(source_root, state_root, "authorize", 10, &policy)
                .unwrap();
        assert!(!new_ev.is_empty());

        let (old_ev, old_stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "authenticate",
            10,
            &policy,
        )
        .unwrap();
        assert!(old_ev.is_empty());
        assert_eq!(old_stats.stale_hits_skipped, 0);
    }

    /// Test 3: changed/deleted source hits remain skipped/validated against source root.
    #[test]
    fn separated_stale_source_hit_is_skipped() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_file(source_root, "src/stale.rs", "fn stale_kernel_target() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/stale.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Edit source after build
        write_file(source_root, "src/stale.rs", "fn changed_after_index() {}\n");

        let (evidence, stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "stale_kernel_target",
            10,
            &policy,
        )
        .unwrap();
        assert!(evidence.is_empty(), "stale hit must not be emitted");
        assert_eq!(stats.stale_hits_skipped, 1);

        let validate = validate_index_at_state_root(source_root, state_root, &policy).unwrap();
        assert!(!validate.valid);
        assert!(validate.stale_files.contains(&"src/stale.rs".to_string()));
    }

    #[test]
    fn separated_deleted_source_hit_is_skipped_and_validate_reports_deleted() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_file(
            source_root,
            "src/deleted.rs",
            "fn deleted_kernel_target() {}\n",
        );

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/deleted.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Delete source file after build
        std::fs::remove_file(source_root.join("src/deleted.rs")).unwrap();

        let (evidence, stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "deleted_kernel_target",
            10,
            &policy,
        )
        .unwrap();
        assert!(evidence.is_empty(), "deleted file must not be emitted");
        assert_eq!(stats.invalid_hits_skipped, 1);

        let validate = validate_index_at_state_root(source_root, state_root, &policy).unwrap();
        assert!(!validate.valid);
        assert!(
            validate
                .deleted_files
                .contains(&"src/deleted.rs".to_string())
        );
    }

    /// Test 4: conflicting source-looking files under state root are never
    /// indexed, read, or returned. We place a "poison" file at the same
    /// relative path under state_root with different content; search must
    /// return source content, not state-root content.
    #[test]
    fn separated_state_root_conflicting_files_are_never_indexed_or_read() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_file(source_root, "src/app.rs", "fn authenticate_user() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Drop a poison file under state_root at the same relative path,
        // with completely different content + a unique token.
        write_file(
            state_root,
            "src/app.rs",
            "fn POISON_TOKEN_NEVER_RETURNED() {}\n",
        );

        // Search for the poison token: must return nothing (state file is
        // not indexed and not read).
        let (poison_ev, _poison_stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "POISON_TOKEN_NEVER_RETURNED",
            10,
            &policy,
        )
        .unwrap();
        assert!(
            poison_ev.is_empty(),
            "state-root poison file must not be searchable: {:?}",
            poison_ev
        );

        // Search for the real source token: must return source content.
        let (real_ev, _real_stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "authenticate",
            10,
            &policy,
        )
        .unwrap();
        assert!(!real_ev.is_empty());
        assert_eq!(real_ev[0].core.path, "src/app.rs");
        // Excerpt must come from source content, not poison.
        let meta = real_ev[0].meta.as_ref().unwrap();
        assert!(
            meta.excerpt
                .as_deref()
                .unwrap()
                .contains("authenticate_user"),
            "excerpt must be from source, not state-root poison: {:?}",
            meta.excerpt
        );
    }

    /// Test 5: two state roots for one source are independent; warm reusable open works.
    #[test]
    fn separated_two_state_roots_for_one_source_are_independent() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_a_dir = tempfile::tempdir().unwrap();
        let state_b_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_a = state_a_dir.path();
        let state_b = state_b_dir.path();

        write_file(source_root, "src/app.rs", "fn shared_kernel_target() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];

        // Build into state_a only.
        build_index_at_state_root(
            source_root,
            state_a,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // state_a has the index; state_b does not.
        assert!(IndexManifest::exists_at_state_root(state_a));
        assert!(!IndexManifest::exists_at_state_root(state_b));

        // Search via state_a succeeds.
        let (a_ev, _a_stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_a,
            "shared_kernel_target",
            10,
            &policy,
        )
        .unwrap();
        assert!(!a_ev.is_empty());

        // Search via state_b returns empty (no index).
        let (b_ev, _b_stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_b,
            "shared_kernel_target",
            10,
            &policy,
        )
        .unwrap();
        assert!(b_ev.is_empty());

        // Build into state_b too — independent index.
        build_index_at_state_root(
            source_root,
            state_b,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        assert!(IndexManifest::exists_at_state_root(state_b));

        // Warm reusable open works on each.
        let handle_a =
            PersistentBm25Index::open_at_state_root(source_root, state_a, &policy).unwrap();
        let handle_b =
            PersistentBm25Index::open_at_state_root(source_root, state_b, &policy).unwrap();
        let (a_handle_ev, _a_h_stats) = handle_a
            .search_at_source_root(source_root, "shared_kernel_target", 10)
            .unwrap();
        let (b_handle_ev, _b_h_stats) = handle_b
            .search_at_source_root(source_root, "shared_kernel_target", 10)
            .unwrap();
        assert!(!a_handle_ev.is_empty());
        assert!(!b_handle_ev.is_empty());

        // Purge state_a does NOT affect state_b.
        purge_index_at_state_root(source_root, state_a).unwrap();
        assert!(!IndexManifest::exists_at_state_root(state_a));
        assert!(IndexManifest::exists_at_state_root(state_b));
    }

    /// Test 6: purge only state index; cannot delete source.
    #[test]
    fn separated_purge_only_state_index_cannot_delete_source() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Source files exist before purge
        assert!(source_root.join("src/app.rs").exists());

        purge_index_at_state_root(source_root, state_root).unwrap();

        // State index is gone
        assert!(!state_root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(!state_root.join(MANIFEST_PATH_RELATIVE).exists());

        // Source files are untouched
        assert!(source_root.join("src/app.rs").exists());
        assert!(source_root.join("src/lib.rs").exists());

        // Source root has no .openlocus at all (never created)
        assert!(!source_root.join(".openlocus").exists());
    }

    /// Test 7: policy is loaded from source root. We place a custom policy
    /// at source_root/.openlocus/policy.toml and verify the manifest's
    /// policy_hash matches the source-root policy, not a default.
    #[test]
    fn separated_policy_loaded_from_source_root() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_file(source_root, "src/app.rs", "fn authenticate_user() {}\n");

        // Place a custom policy.toml at source_root/.openlocus/policy.toml
        write_file(
            source_root,
            ".openlocus/policy.toml",
            "[index]\ninclude = [\"**/*\"]\nexclude = [\".openlocus\", \"target\"]\ninclude_gitignored = false\n\n[remote]\nallow = false\ndefault_mode = \"local_only\"\n\n[secrets]\nscan_before_remote = true\n\n[retention]\nlocal_index_ttl_days = 90\n",
        );

        let policy_from_source = Policy::load_from_repo(source_root);
        // Sanity: this is the policy we just wrote, not a default.
        assert!(!policy_from_source.remote.allow);

        let records = vec![file_record(source_root, "src/app.rs")];
        let result = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy_from_source,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        assert!(result.success);

        // Manifest policy_hash must match the source-root policy's hash
        let manifest = IndexManifest::load_at_state_root(state_root).unwrap();
        assert_eq!(
            manifest.policy_hash,
            compute_policy_hash(&policy_from_source),
            "manifest policy_hash must match source-root policy"
        );

        // No policy.toml under state_root
        assert!(!state_root.join(".openlocus/policy.toml").exists());

        // status with the source-root policy is clean
        let status =
            status_index_at_state_root(source_root, state_root, &policy_from_source).unwrap();
        assert!(status.policy_hash_matches.unwrap());
        assert!(!status.requires_rebuild);
    }

    // ── validate_separated_roots fail-closed tests (B0) ─────────────────
    //
    // Oracle-approved relation: in separated mode, compare canonical source
    // S against actual future/current artifact subtree A = state_root/.openlocus/index.
    // Reject when A == S, A below S, or S below A (component-wise via starts_with).
    // Source under state_root but outside .openlocus/index is allowed (safe).

    /// Test 1: colocated mode (source_root == state_root) is always Ok.
    #[test]
    fn validate_separated_roots_colocated_is_ok() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        // Same path → colocated mode → Ok
        assert!(validate_separated_roots(root, root).is_ok());
    }

    /// Test 2: artifact subtree A == source root S is rejected.
    /// source_root = state_root/.openlocus/index  →  A = state_root/.openlocus/index == S.
    #[test]
    fn validate_separated_roots_rejects_artifact_equals_source() {
        let state_dir = tempfile::tempdir().unwrap();
        let state_root = state_dir.path();
        // Source root is exactly the future artifact subtree.
        let source_root = state_root.join(INDEX_DIR_RELATIVE);
        std::fs::create_dir_all(&source_root).unwrap();
        let err = validate_separated_roots(&source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("artifact subtree overlaps source root"),
            "got: {}",
            err
        );
    }

    /// Test 3: artifact subtree A below source root S is rejected.
    /// state_root = source_root/.openlocus/external-state
    ///   → A = source_root/.openlocus/external-state/.openlocus/index
    ///   → A.starts_with(S) is true.
    #[test]
    fn validate_separated_roots_rejects_artifact_below_source() {
        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        // State root = a subdirectory of source_root
        let state_root = source_root.join(".openlocus/external-state");
        std::fs::create_dir_all(&state_root).unwrap();
        let err = validate_separated_roots(source_root, &state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("artifact subtree overlaps source root"),
            "got: {}",
            err
        );
    }

    /// Test 4: source root S below artifact subtree A is rejected.
    /// source_root = state_root/.openlocus/index/sub
    ///   → A = state_root/.openlocus/index
    ///   → S.starts_with(A) is true.
    #[test]
    fn validate_separated_roots_rejects_source_below_artifact() {
        let state_dir = tempfile::tempdir().unwrap();
        let state_root = state_dir.path();
        // Source root is below the future artifact subtree.
        let source_root = state_root.join(INDEX_DIR_RELATIVE).join("sub");
        std::fs::create_dir_all(&source_root).unwrap();
        let err = validate_separated_roots(&source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("artifact subtree overlaps source root"),
            "got: {}",
            err
        );
    }

    /// Test 5: source under state_root but outside `.openlocus/index` is
    /// allowed (safe — artifact subtree does not overlap source).
    /// source_root = state_root/src, state_root = state_root
    ///   → A = state_root/.openlocus/index, S = state_root/src
    ///   → no overlap.
    #[test]
    fn validate_separated_roots_allows_source_under_state_outside_index() {
        let state_dir = tempfile::tempdir().unwrap();
        let state_root = state_dir.path();
        let source_root = state_root.join("src");
        std::fs::create_dir_all(&source_root).unwrap();
        assert!(
            validate_separated_roots(&source_root, state_root).is_ok(),
            "source under state but outside .openlocus/index must be allowed"
        );
    }

    /// Test 6: unrelated (disjoint) roots are allowed.
    #[test]
    fn validate_separated_roots_allows_state_outside_source() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        assert!(validate_separated_roots(source_root, state_root).is_ok());
    }

    /// Test 7: nonexistent state whose future artifact would be below
    /// source is rejected. state_root = source_root/external-state (does not
    /// exist) → A would be source_root/external-state/.openlocus/index
    /// which is below S.
    #[test]
    fn validate_separated_roots_rejects_nonexistent_state_inside_source() {
        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        // State root is a non-existent subdirectory of source_root.
        // Must still be rejected (would modify source when created).
        let state_root = source_root.join("external-state");
        assert!(!state_root.exists());
        let err = validate_separated_roots(source_root, &state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("artifact subtree overlaps source root"),
            "got: {}",
            err
        );
    }

    /// Test 8: nonexistent disjoint future artifact is allowed.
    #[test]
    fn validate_separated_roots_allows_nonexistent_state_outside_source() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_parent = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        // Non-existent state root that is NOT inside source_root
        let state_root = state_parent.path().join("new-state-dir");
        assert!(!state_root.exists());
        assert!(validate_separated_roots(source_root, &state_root).is_ok());
    }

    /// Test 9 + 10: symlink/canonical alias cases both directions, gated by
    /// symlink availability on the host. When state_root is a symlink that
    /// aliases source_root (or vice versa) the canonical comparison must
    /// fail-closed: A resolves to source_root/.openlocus/index which is
    /// below S → rejected.
    #[test]
    fn validate_separated_roots_rejects_canonical_aliases_both_directions() {
        // Direction A: state_root is a symlink to source_root.
        //   A = state_root/.openlocus/index resolves through the symlink to
        //   source_root/.openlocus/index, which is below S → reject.
        {
            let src_dir = tempfile::tempdir().unwrap();
            let source_root = src_dir.path();
            let link_parent = tempfile::tempdir().unwrap();
            let state_link = link_parent.path().join("state-alias");
            if !create_symlink_dir_for_test(source_root, &state_link) {
                eprintln!("skipping symlink direction A: symlinks unavailable");
            } else {
                let err = validate_separated_roots(source_root, &state_link)
                    .unwrap_err()
                    .to_string();
                assert!(
                    err.contains("artifact subtree overlaps source root"),
                    "direction A (state→source symlink) got: {}",
                    err
                );
            }
        }

        // Direction B: source_root is a symlink to state_root.
        //   A = state_root/.openlocus/index; S resolves to state_root (via
        //   the symlink), so A is below S → reject.
        {
            let state_dir = tempfile::tempdir().unwrap();
            let state_root = state_dir.path();
            let link_parent = tempfile::tempdir().unwrap();
            let source_link = link_parent.path().join("source-alias");
            if !create_symlink_dir_for_test(state_root, &source_link) {
                eprintln!("skipping symlink direction B: symlinks unavailable");
            } else {
                let err = validate_separated_roots(&source_link, state_root)
                    .unwrap_err()
                    .to_string();
                assert!(
                    err.contains("artifact subtree overlaps source root"),
                    "direction B (source→state symlink) got: {}",
                    err
                );
            }
        }

        // Direction C: lexically distinct, canonically equal split intent.
        //   Two distinct symlink paths that both resolve to the same canonical
        //   source directory. validate_separated_roots must treat them as
        //   colocated-only: A resolves to S/.openlocus/index which is below S.
        {
            let target_dir = tempfile::tempdir().unwrap();
            let target = target_dir.path();
            let link_parent = tempfile::tempdir().unwrap();
            let link_a = link_parent.path().join("alias-a");
            let link_b = link_parent.path().join("alias-b");
            if !create_symlink_dir_for_test(target, &link_a)
                || !create_symlink_dir_for_test(target, &link_b)
            {
                eprintln!("skipping canonically-equal split test: symlinks unavailable");
            } else {
                // link_a != link_b lexically, but both canonicalize to `target`.
                // validate_separated_roots(link_a, link_b): A = link_b/.openlocus/index
                // resolves through the symlink to target/.openlocus/index, which is
                // below S = target → reject.
                let err = validate_separated_roots(&link_a, &link_b)
                    .unwrap_err()
                    .to_string();
                assert!(
                    err.contains("artifact subtree overlaps source root"),
                    "canonically-equal split got: {}",
                    err
                );
            }
        }
    }

    /// Raw-path fallback removed: when no canonicalizable ancestor exists
    /// for the artifact path, validate_separated_roots must error rather
    /// than fall back to the raw path. We construct an artifact path whose
    /// only existing ancestor is the source root itself, but where the
    /// suffix contains a `..` (ParentDir) component — this must error.
    #[test]
    fn validate_separated_roots_rejects_parent_dir_in_unresolved_suffix() {
        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        // state_root contains a `..` in the unresolved suffix; the existing
        // ancestor is source_root, and the suffix `.openlocus/../escape/...`
        // contains a ParentDir component which must be rejected (rather than
        // being appended raw and potentially escaping the canonical ancestor).
        let state_root = source_root.join(".openlocus/../escape-state");
        let err = validate_separated_roots(source_root, &state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("parent-dir component")
                || err.contains("artifact subtree overlaps source root"),
            "got: {}",
            err
        );
    }

    // ── integrated oracle blocker: fail-closed on non-NotFound errors ──
    //
    // The previous `if let Ok` + `Path::exists()` implementation collapsed
    // canonicalize/metadata errors (PermissionDenied, symlink loop, dangling
    // symlink) into absence, letting a hostile path silently pass separation
    // validation. The new policy admits ONLY definite NotFound into
    // nearest-existing-ancestor reconstruction; every other error reject.
    // These tests cover the dangling-symlink and symlink-loop cases that
    // were previously treated as unresolved Normal suffixes.

    /// Dangling symlink AT the artifact path (final component): the link
    /// itself is observable via symlink_metadata but its target is absent,
    /// so canonicalize returns NotFound. The fast path must reject with
    /// "dangling symlink at state artifact path" — never treat the link as
    /// an unresolved Normal suffix appended to its parent. Source/state
    /// sentinel bytes must remain (validation rejects before any mutation).
    #[test]
    fn validate_separated_roots_rejects_dangling_symlink_at_artifact_path() {
        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_dir = tempfile::tempdir().unwrap();
        let state_root = state_dir.path();

        // Real .openlocus/ dir + sentinel bytes inside it.
        let openlocus_dir = state_root.join(".openlocus");
        std::fs::create_dir_all(&openlocus_dir).unwrap();
        let sentinel_path = openlocus_dir.join("policy.toml");
        let sentinel_bytes = b"# sentinel bytes must remain\n";
        std::fs::write(&sentinel_path, sentinel_bytes).unwrap();

        // `.openlocus/index` itself is a dangling symlink (target absent).
        let artifact_link = openlocus_dir.join("index");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-target-for-openlocus-test"),
            &artifact_link,
        ) {
            eprintln!(
                "skipping dangling-symlink-at-artifact test: symlinks unavailable on this host"
            );
            return;
        }

        let err = validate_separated_roots(source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("dangling symlink at state artifact path")
                || err.contains("cannot canonicalize state artifact path"),
            "got: {}",
            err
        );

        // Sentinel intact: validation rejected before any state mutation.
        let after = std::fs::read(&sentinel_path).unwrap();
        assert_eq!(
            after.as_slice(),
            sentinel_bytes,
            "sentinel bytes must remain untouched when validation rejects"
        );
    }

    /// Dangling symlink IN the ancestor chain (non-final component): the
    /// artifact path itself cannot be stat'd (NotFound) because the
    /// dangling `.openlocus` link makes `.openlocus/index` unreachable.
    /// Walk-up then observes the dangling link via symlink_metadata, and
    /// canonicalize of the link returns NotFound — must reject with
    /// "dangling symlink in state artifact ancestor chain", never treat
    /// the link as an unresolved Normal suffix.
    #[test]
    fn validate_separated_roots_rejects_dangling_symlink_in_ancestor_chain() {
        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_dir = tempfile::tempdir().unwrap();
        let state_root = state_dir.path();

        // Sentinel at state_root level — `.openlocus` is a symlink below,
        // so we cannot place the sentinel inside it.
        let sentinel_path = state_root.join("sentinel-marker.txt");
        let sentinel_bytes = b"state-root sentinel\n";
        std::fs::write(&sentinel_path, sentinel_bytes).unwrap();

        // `.openlocus` itself is a dangling symlink (target absent). The
        // artifact path `state_root/.openlocus/index` is therefore
        // unreachable through the dangling link.
        let dangling_link = state_root.join(".openlocus");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-target-for-openlocus-ancestor-test"),
            &dangling_link,
        ) {
            eprintln!("skipping dangling-symlink-ancestor test: symlinks unavailable on this host");
            return;
        }

        let err = validate_separated_roots(source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("dangling symlink in state artifact ancestor chain")
                || err.contains("cannot stat state artifact path"),
            "got: {}",
            err
        );

        // Sentinel intact.
        let after = std::fs::read(&sentinel_path).unwrap();
        assert_eq!(
            after.as_slice(),
            sentinel_bytes,
            "sentinel bytes must remain untouched when validation rejects"
        );
    }

    /// Symlink loop at the artifact path: the link is observable via
    /// symlink_metadata but canonicalize fails with a loop error (NOT
    /// NotFound). The fast path must reject with "cannot canonicalize
    /// state artifact path" — never fall through to walk-up. Sentinel
    /// bytes must remain.
    #[test]
    fn validate_separated_roots_rejects_symlink_loop_at_artifact_path() {
        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_dir = tempfile::tempdir().unwrap();
        let state_root = state_dir.path();

        let openlocus_dir = state_root.join(".openlocus");
        std::fs::create_dir_all(&openlocus_dir).unwrap();
        let sentinel_path = openlocus_dir.join("policy.toml");
        let sentinel_bytes = b"# sentinel bytes must remain\n";
        std::fs::write(&sentinel_path, sentinel_bytes).unwrap();

        // `.openlocus/index` is a self-referential symlink loop. The link
        // target string is just `index` (relative), so resolving it loops
        // forever and the kernel returns ELOOP.
        let artifact_link = openlocus_dir.join("index");
        if !create_symlink_file_for_test(&artifact_link, &artifact_link) {
            eprintln!("skipping symlink-loop test: symlinks unavailable on this host");
            return;
        }

        let err = validate_separated_roots(source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("cannot canonicalize state artifact path"),
            "got: {}",
            err
        );

        // Sentinel intact.
        let after = std::fs::read(&sentinel_path).unwrap();
        assert_eq!(
            after.as_slice(),
            sentinel_bytes,
            "sentinel bytes must remain untouched when validation rejects"
        );
    }

    /// Deterministic, capability-independent coverage of the non-NotFound
    /// error classification: a path with an interior NUL byte is invalid
    /// on every platform and produces a non-NotFound metadata error. The
    /// fail-closed path must reject it rather than collapsing the error
    /// into absence (the original `if let Ok` + `Path::exists()` bug).
    /// This test does NOT require symlink or privilege support. It is
    /// honestly skipped if the host happens to accept NUL paths or maps
    /// them to NotFound.
    #[test]
    fn canonicalize_artifact_path_rejects_non_notfound_metadata_error() {
        let bad = Path::new("\u{0}invalid-path-for-test");
        // Test precondition: confirm the host actually produces a
        // non-NotFound metadata error for this path. If it does not,
        // there is nothing deterministic to assert here.
        match bad.symlink_metadata() {
            Ok(_) => {
                eprintln!(
                    "skipping non-NotFound metadata test: host accepts NUL path (no error produced)"
                );
            }
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => {
                eprintln!(
                    "skipping non-NotFound metadata test: NUL path returns NotFound on this host"
                );
            }
            Err(_) => {
                let result = canonicalize_artifact_path(bad);
                assert!(
                    result.is_err(),
                    "non-NotFound metadata error must reject fail-closed, got: {:?}",
                    result
                );
                let msg = result.unwrap_err().to_string();
                assert!(
                    msg.contains("cannot stat state artifact path"),
                    "got: {}",
                    msg
                );
            }
        }
    }

    /// Conflicting source-looking files under state root are never indexed
    /// even when a build is run after the poison file exists. This verifies
    /// build never scans state_root for source.
    #[test]
    fn separated_build_ignores_state_root_files_entirely() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();

        // Source has one file
        write_file(source_root, "src/app.rs", "fn source_only_token() {}\n");

        // State root has a "poison" source-looking file at a DIFFERENT path
        // that does NOT exist in source. It must not be indexed.
        write_file(
            state_root,
            "src/poison.rs",
            "fn POISON_TOKEN_MUST_NOT_BE_INDEXED() {}\n",
        );

        let policy = Policy::default();
        // records come from scan_repo(source_root), so poison is not in records.
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Searching for the poison token returns nothing
        let (poison_ev, _stats) = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "POISON_TOKEN_MUST_NOT_BE_INDEXED",
            10,
            &policy,
        )
        .unwrap();
        assert!(
            poison_ev.is_empty(),
            "state-root-only file must not be indexed"
        );

        // Manifest must not contain the poison path
        let manifest = IndexManifest::load_at_state_root(state_root).unwrap();
        assert!(
            !manifest.files.iter().any(|f| f.path == "src/poison.rs"),
            "state-root-only file must not appear in manifest: {:?}",
            manifest.files
        );
    }

    /// No persisted absolute source path: manifest entries use repo-relative
    /// paths only, identical to colocated mode. No schema migration.
    #[test]
    fn separated_manifest_has_no_absolute_source_path() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_file(source_root, "src/app.rs", "fn authenticate_user() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let manifest = IndexManifest::load_at_state_root(state_root).unwrap();
        for entry in &manifest.files {
            assert!(
                !entry.path.contains(':'),
                "manifest path must not be absolute: {}",
                entry.path
            );
            assert!(
                !entry.path.starts_with('/') && !entry.path.starts_with('\\'),
                "manifest path must not be absolute: {}",
                entry.path
            );
            // Same schema version as colocated mode (no migration)
            assert_eq!(manifest.schema_version, SCHEMA_VERSION);
        }
    }

    #[test]
    fn build_and_search() {
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

        let policy = Policy::default();
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

        let result = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        assert!(result.success);
        assert_eq!(result.file_count, 2);
        assert!(result.chunk_count > 0);
        assert_eq!(result.chunk_strategy, "line");

        let (evidence, stats) = search_persistent_bm25(root, "authenticate", 10, &policy).unwrap();
        assert!(!evidence.is_empty(), "should find matches");
        assert_eq!(evidence[0].core.path, "app.rs");
        assert_eq!(evidence[0].core.channels[0], Channel::Bm25);
        assert_eq!(stats.stale_hits_skipped, 0);
    }

    #[test]
    fn regression_current_indexed_hit_materializes_verified_current_evidence() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(
            root,
            "src/current.rs",
            "fn before() {}\nfn current_kernel_target() {\n    let currentness = true;\n}\nfn after() {}\n",
        );

        let policy = Policy::default();
        let records = vec![file_record(root, "src/current.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let (evidence, stats) =
            search_persistent_bm25(root, "current_kernel_target", 10, &policy).unwrap();
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 0);
        let first = evidence.first().expect("expected current indexed hit");
        assert_current_evidence(root, first, "src/current.rs", "current_kernel_target");

        let handle = PersistentBm25Index::open(root, &policy).unwrap();
        let (handle_evidence, handle_stats) =
            handle.search(root, "current_kernel_target", 10).unwrap();
        assert_eq!(handle_stats.stale_hits_skipped, 0);
        assert_eq!(handle_stats.invalid_hits_skipped, 0);
        let first = handle_evidence
            .first()
            .expect("expected current indexed hit from reusable handle");
        assert_current_evidence(root, first, "src/current.rs", "current_kernel_target");
    }

    #[test]
    fn regression_leading_underscore_identifier_uses_content_field_tokenizer() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(
            root,
            "src/private.py",
            "def before():\n    return 0\n\ndef _hidden_symbol():\n    return 1\n",
        );

        let policy = Policy::default();
        let records = vec![file_record(root, "src/private.py")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let index = Index::open_in_dir(root.join(TANTIVY_DIR_RELATIVE)).unwrap();
        let content_field = index.schema().get_field("content").unwrap();
        assert_eq!(
            tokenize_query(&index, content_field, "_hidden_symbol").unwrap(),
            vec!["hidden", "symbol"]
        );
        assert_eq!(
            tokenize_query(&index, content_field, "feature.flag").unwrap(),
            vec!["feature", "flag"]
        );
        assert_eq!(
            tokenize_query(&index, content_field, "x").unwrap(),
            vec!["x"]
        );

        let (evidence, stats) =
            search_persistent_bm25(root, "_hidden_symbol", 10, &policy).unwrap();
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 0);
        let first = evidence
            .first()
            .expect("expected underscore-leading identifier from persistent search");
        assert_current_evidence(root, first, "src/private.py", "_hidden_symbol");

        let handle = PersistentBm25Index::open(root, &policy).unwrap();
        let (handle_evidence, handle_stats) = handle.search(root, "_hidden_symbol", 10).unwrap();
        assert_eq!(handle_stats.stale_hits_skipped, 0);
        assert_eq!(handle_stats.invalid_hits_skipped, 0);
        let first = handle_evidence
            .first()
            .expect("expected underscore-leading identifier from reusable handle");
        assert_current_evidence(root, first, "src/private.py", "_hidden_symbol");
    }

    #[test]
    fn regression_stale_edit_after_build_is_skipped_and_counted() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(root, "src/stale.rs", "fn stale_kernel_target() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(root, "src/stale.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        write_file(root, "src/stale.rs", "fn changed_after_index() {}\n");

        let (evidence, stats) =
            search_persistent_bm25(root, "stale_kernel_target", 10, &policy).unwrap();
        assert!(evidence.is_empty(), "stale hit must not be emitted");
        assert_eq!(stats.stale_hits_skipped, 1);
        assert_eq!(stats.invalid_hits_skipped, 0);
    }

    #[test]
    fn regression_deleted_file_after_build_is_skipped_and_validate_reports_deleted() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(root, "src/deleted.rs", "fn deleted_kernel_target() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(root, "src/deleted.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        std::fs::remove_file(root.join("src/deleted.rs")).unwrap();

        let (evidence, stats) =
            search_persistent_bm25(root, "deleted_kernel_target", 10, &policy).unwrap();
        assert!(evidence.is_empty(), "deleted file must not be emitted");
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 1);

        let validate = validate_index(root, &policy).unwrap();
        assert!(!validate.valid);
        assert!(
            validate
                .deleted_files
                .contains(&"src/deleted.rs".to_string())
        );
    }

    #[test]
    fn regression_moved_old_path_not_emitted_and_rebuilt_new_path_emits_current() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(root, "src/old_path.rs", "fn moved_kernel_target() {}\n");

        let policy = Policy::default();
        let old_records = vec![file_record(root, "src/old_path.rs")];
        build_index(root, &old_records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        std::fs::rename(root.join("src/old_path.rs"), root.join("src/new_path.rs")).unwrap();

        let (old_evidence, old_stats) =
            search_persistent_bm25(root, "moved_kernel_target", 10, &policy).unwrap();
        assert!(
            old_evidence.is_empty(),
            "moved old path must not be emitted"
        );
        assert_eq!(old_stats.invalid_hits_skipped, 1);

        let validate = validate_index(root, &policy).unwrap();
        assert!(
            validate
                .deleted_files
                .contains(&"src/old_path.rs".to_string())
        );

        let new_records = vec![file_record(root, "src/new_path.rs")];
        build_index(root, &new_records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        let (new_evidence, new_stats) =
            search_persistent_bm25(root, "moved_kernel_target", 10, &policy).unwrap();
        assert_eq!(new_stats.stale_hits_skipped, 0);
        assert_eq!(new_stats.invalid_hits_skipped, 0);
        let first = new_evidence.first().expect("expected rebuilt new path hit");
        assert_current_evidence(root, first, "src/new_path.rs", "moved_kernel_target");
    }

    #[test]
    fn regression_line_insertion_invalidates_old_index_until_rebuild() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(
            root,
            "src/insert.rs",
            "fn before() {}\nfn insertion_kernel_target() {}\nfn after() {}\n",
        );

        let policy = Policy::default();
        let records = vec![file_record(root, "src/insert.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        write_file(
            root,
            "src/insert.rs",
            "fn inserted_line() {}\nfn before() {}\nfn insertion_kernel_target() {}\nfn after() {}\n",
        );

        let (stale_evidence, stale_stats) =
            search_persistent_bm25(root, "insertion_kernel_target", 10, &policy).unwrap();
        assert!(stale_evidence.is_empty(), "pre-insertion hit must be stale");
        assert_eq!(stale_stats.stale_hits_skipped, 1);
        let validate = validate_index(root, &policy).unwrap();
        assert!(validate.stale_files.contains(&"src/insert.rs".to_string()));

        let rebuilt_records = vec![file_record(root, "src/insert.rs")];
        build_index(root, &rebuilt_records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        let (fresh_evidence, fresh_stats) =
            search_persistent_bm25(root, "insertion_kernel_target", 10, &policy).unwrap();
        assert_eq!(fresh_stats.stale_hits_skipped, 0);
        let first = fresh_evidence
            .first()
            .expect("expected rematerialized hit after rebuild");
        assert_current_evidence(root, first, "src/insert.rs", "insertion_kernel_target");
    }

    #[test]
    fn regression_same_content_duplicate_does_not_rescue_stale_original_path() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let original_content = "fn duplicate_kernel_target() {}\n";
        write_file(root, "src/original.rs", original_content);
        write_file(root, "src/duplicate.rs", original_content);

        let policy = Policy::default();
        let records = vec![
            file_record(root, "src/original.rs"),
            file_record(root, "src/duplicate.rs"),
        ];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        write_file(root, "src/original.rs", "fn edited_original() {}\n");

        let (evidence, stats) =
            search_persistent_bm25(root, "duplicate_kernel_target", 10, &policy).unwrap();
        assert_eq!(stats.stale_hits_skipped, 1);
        assert!(
            evidence.iter().all(|ev| ev.core.path != "src/original.rs"),
            "stale original path must not be emitted: {evidence:?}"
        );
        assert!(
            evidence.iter().any(|ev| ev.core.path == "src/duplicate.rs"),
            "current duplicate may be emitted, but must not rescue original path"
        );
        for ev in &evidence {
            if ev.core.path == "src/duplicate.rs" {
                assert_current_evidence(root, ev, "src/duplicate.rs", "duplicate_kernel_target");
            }
        }
    }

    #[test]
    fn regression_unsafe_record_path_is_skipped_by_build_and_not_searchable() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(root, "safe.rs", "fn safe_kernel_target() {}\n");

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "../escape.rs".into(),
            size: 0,
            content_sha: "not-used".into(),
            language: "rust".into(),
        }];
        let result = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        assert_eq!(result.file_count, 0);
        assert_eq!(result.chunk_count, 0);
        let entry = manifest_entry(root, "../escape.rs");
        assert_eq!(entry.status, "skipped");
        assert_eq!(entry.skipped_reason.as_deref(), Some("path_unsafe"));

        let (evidence, stats) = search_persistent_bm25(root, "escape", 10, &policy).unwrap();
        assert!(evidence.is_empty());
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 0);
    }

    #[test]
    fn regression_validate_reports_manifest_indexed_unsafe_path() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let policy = Policy::default();
        let unsafe_entry = ManifestFileEntry {
            path: "../escape.rs".into(),
            content_sha: "sha".into(),
            size_bytes: 1,
            language: "rust".into(),
            status: "indexed".into(),
            skipped_reason: None,
        };
        let manifest = IndexManifest::new_with_strategy(
            compute_policy_hash(&policy),
            vec![unsafe_entry],
            1,
            ChunkStrategy::LineWindowV1,
            None,
        );
        manifest.save(root).unwrap();

        let validate = validate_index(root, &policy).unwrap();
        assert!(!validate.valid);
        assert_eq!(validate.path_unsafe_files, vec!["../escape.rs".to_string()]);
    }

    #[test]
    fn regression_symlink_escape_after_build_is_skipped_by_search_and_validate() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let outside = tempfile::tempdir().unwrap();
        let outside_file = outside.path().join("outside.rs");
        std::fs::write(&outside_file, "fn symlink_escape_target() {}\n").unwrap();
        write_file(root, "src/link.rs", "fn symlink_escape_target() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(root, "src/link.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        std::fs::remove_file(root.join("src/link.rs")).unwrap();
        if !create_symlink_file_for_test(&outside_file, &root.join("src/link.rs")) {
            return;
        }

        let (evidence, stats) =
            search_persistent_bm25(root, "symlink_escape_target", 10, &policy).unwrap();
        assert!(evidence.is_empty(), "symlink escape must not be emitted");
        assert_eq!(stats.invalid_hits_skipped, 1);
        assert_eq!(stats.stale_hits_skipped, 0);

        let validate = validate_index(root, &policy).unwrap();
        assert!(!validate.valid);
        assert!(
            validate
                .path_unsafe_files
                .contains(&"src/link.rs".to_string())
        );
    }

    #[test]
    fn status_and_dirty_reject_manifest_indexed_parent_escape_as_unclean() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let outside_path = dir.path().parent().unwrap().join("escape.rs");
        std::fs::write(&outside_path, "fn outside_escape_target() {}\n").unwrap();

        let policy = Policy::default();
        let manifest = IndexManifest::new_with_strategy(
            compute_policy_hash(&policy),
            vec![ManifestFileEntry {
                path: "../escape.rs".into(),
                content_sha: blake3::hash(std::fs::read(&outside_path).unwrap().as_slice())
                    .to_hex()
                    .to_string(),
                size_bytes: 1,
                language: "rust".into(),
                status: "indexed".into(),
                skipped_reason: None,
            }],
            1,
            ChunkStrategy::LineWindowV1,
            None,
        );
        manifest.save(root).unwrap();

        let status = status_index(root, &policy).unwrap();
        assert!(status.requires_rebuild, "unsafe indexed path is not clean");
        assert_eq!(status.stale_files_fast, Some(1));

        let dirty = dirty_index(root, &policy, &[]).unwrap();
        assert!(!dirty.clean, "unsafe indexed path is not clean");
        assert!(dirty.requires_update);
        assert!(dirty.modified_files.contains(&"../escape.rs".to_string()));

        let _ = std::fs::remove_file(outside_path);
    }

    #[test]
    fn status_and_dirty_reject_indexed_symlink_escape_even_with_matching_content() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let outside = tempfile::tempdir().unwrap();
        let content = "fn symlink_dirty_escape_target() {}\n";
        let outside_file = outside.path().join("outside.rs");
        std::fs::write(&outside_file, content).unwrap();
        write_file(root, "src/link.rs", content);

        let policy = Policy::default();
        let records = vec![file_record(root, "src/link.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        std::fs::remove_file(root.join("src/link.rs")).unwrap();
        if !create_symlink_file_for_test(&outside_file, &root.join("src/link.rs")) {
            return;
        }

        let status = status_index(root, &policy).unwrap();
        assert!(
            status.requires_rebuild,
            "symlink escape is not current/clean"
        );
        assert_eq!(status.stale_files_fast, Some(1));

        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(!dirty.clean, "symlink escape must require safe action");
        assert!(dirty.requires_update);
        assert!(dirty.modified_files.contains(&"src/link.rs".to_string()));
    }

    #[test]
    fn dirty_skipped_unsafe_entry_does_not_read_outside_root() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let outside_path = dir.path().parent().unwrap().join("skipped_escape.rs");
        std::fs::write(&outside_path, "changed outside content\n").unwrap();

        let policy = Policy::default();
        let manifest = IndexManifest::new_with_strategy(
            compute_policy_hash(&policy),
            vec![ManifestFileEntry {
                path: "../skipped_escape.rs".into(),
                content_sha: "original-skipped-sha".into(),
                size_bytes: 1,
                language: "rust".into(),
                status: "skipped".into(),
                skipped_reason: Some("path_unsafe".into()),
            }],
            0,
            ChunkStrategy::LineWindowV1,
            None,
        );
        manifest.save(root).unwrap();

        let dirty = dirty_index(root, &policy, &[]).unwrap();
        assert!(
            dirty.modified_files.is_empty(),
            "skipped unsafe path must not be read outside repo and reported modified"
        );
        assert!(dirty.deleted_files.is_empty());
        assert!(
            dirty.clean,
            "unchanged skipped unsafe entry should remain skipped-only clean"
        );

        let _ = std::fs::remove_file(outside_path);
    }

    #[test]
    fn build_ast_strategy() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(
            root.join("app.rs"),
            "fn authenticate_user() -> bool {\n    true\n}\n\nfn helper() -> i32 { 1 }\n",
        )
        .unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "app.rs"),
            language: "rust".into(),
        }];

        let result = build_index(root, &records, &policy, ChunkStrategy::AstV1).unwrap();
        assert!(result.success);
        assert_eq!(result.chunk_strategy, "ast");
        assert!(result.ast_stats.is_some());
        let ast = result.ast_stats.unwrap();
        assert_eq!(ast.supported_files, 1);
        assert!(ast.ast_chunks > 0, "should have AST chunks");

        // Search should work with AST-built index
        let (evidence, stats) = search_persistent_bm25(root, "authenticate", 10, &policy).unwrap();
        assert!(!evidence.is_empty(), "should find matches");
        assert_eq!(stats.stale_hits_skipped, 0);
    }

    #[test]
    fn search_skips_stale_hit() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("auth.rs"), "fn authenticate() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "auth.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "auth.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Modify the file after indexing
        std::fs::write(root.join("auth.rs"), "fn authorize() {}\nfn extra() {}\n").unwrap();

        let (evidence, stats) = search_persistent_bm25(root, "authenticate", 10, &policy).unwrap();
        assert!(
            evidence.is_empty() || stats.stale_hits_skipped > 0,
            "stale hits should be skipped or no results"
        );
    }

    #[test]
    fn search_skips_deleted_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("temp.rs"), "fn temp() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "temp.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "temp.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Delete the file after indexing
        std::fs::remove_file(root.join("temp.rs")).unwrap();

        let (evidence, stats) = search_persistent_bm25(root, "temp", 10, &policy).unwrap();
        assert!(
            evidence.is_empty(),
            "deleted file should produce no evidence"
        );
        assert!(stats.invalid_hits_skipped > 0);
    }

    #[test]
    fn policy_gate_refuses_mismatched_policy() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("app.rs"), "fn authenticate() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "app.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Change policy
        let mut different_policy = Policy::default();
        different_policy.remote.allow = true;

        let result = search_persistent_bm25(root, "authenticate", 10, &different_policy);
        assert!(result.is_err(), "search should refuse with policy mismatch");
        let err_msg = format!("{}", result.unwrap_err());
        assert!(
            err_msg.contains("policy hash mismatch"),
            "error should mention policy hash mismatch: got {}",
            err_msg
        );
    }

    #[test]
    fn empty_content_sha_skipped() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("test.rs"), "fn hello() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "test.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "test.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let (evidence, stats) = search_persistent_bm25(root, "hello", 10, &policy).unwrap();
        if !evidence.is_empty() {
            assert_eq!(stats.invalid_hits_skipped, 0);
        }
    }

    #[test]
    fn strict_range_validation_no_clamp() {
        let lines = vec!["line1", "line2", "line3"];
        let query_tokens = vec!["line".to_string()];

        let result = find_best_matching_line(&lines, 1, 3, &query_tokens);
        assert!(result.is_some());

        let result = find_best_matching_line(&lines, 3, 1, &query_tokens);
        assert!(result.is_none());
    }

    #[test]
    fn status_after_build() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("test.rs"), "fn test() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "test.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "test.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let status = status_index(root, &policy).unwrap();
        assert!(status.exists);
        assert_eq!(status.schema_version.as_deref(), Some(SCHEMA_VERSION));
        assert_eq!(status.file_count, Some(1));
        assert_eq!(status.policy_hash_matches, Some(true));
        assert!(!status.requires_rebuild);
        assert_eq!(status.chunk_strategy.as_deref(), Some("line"));
    }

    #[test]
    fn status_after_ast_build() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("test.rs"), "fn test() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "test.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "test.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::AstV1).unwrap();

        let status = status_index(root, &policy).unwrap();
        assert!(status.exists);
        assert_eq!(status.chunk_strategy.as_deref(), Some("ast"));
        assert!(status.ast_stats.is_some());
        assert!(!status.requires_rebuild);
    }

    #[test]
    fn status_detects_stale() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("app.rs"), "fn old() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "app.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        std::fs::write(root.join("app.rs"), "fn new() {}\nfn extra() {}\n").unwrap();

        let status = status_index(root, &policy).unwrap();
        assert!(status.requires_rebuild);
        assert_eq!(status.stale_files_fast, Some(1));
    }

    #[test]
    fn validate_after_build() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("v.rs"), "fn valid() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "v.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "v.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let validate = validate_index(root, &policy).unwrap();
        assert!(validate.valid);
        assert!(validate.stale_files.is_empty());
        assert!(validate.deleted_files.is_empty());
        assert_eq!(validate.chunk_strategy.as_deref(), Some("line"));
    }

    #[test]
    fn validate_detects_stale() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("s.rs"), "fn stale() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "s.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "s.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        std::fs::write(root.join("s.rs"), "fn updated() {}\n").unwrap();

        let validate = validate_index(root, &policy).unwrap();
        assert!(!validate.valid);
        assert!(validate.stale_files.contains(&"s.rs".to_string()));
    }

    #[test]
    fn validate_detects_deleted() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("d.rs"), "fn del() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "d.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "d.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        std::fs::remove_file(root.join("d.rs")).unwrap();

        let validate = validate_index(root, &policy).unwrap();
        assert!(!validate.valid);
        assert!(validate.deleted_files.contains(&"d.rs".to_string()));
    }

    #[test]
    fn validate_detects_policy_mismatch() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("v.rs"), "fn valid() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "v.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "v.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let mut different_policy = Policy::default();
        different_policy.remote.allow = true;

        let validate = validate_index(root, &different_policy).unwrap();
        assert!(!validate.valid);
        assert!(!validate.policy_hash_matches);
    }

    #[test]
    fn purge_removes_artifacts() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("p.rs"), "fn purge() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "p.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "p.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        assert!(root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(root.join(MANIFEST_PATH_RELATIVE).exists());

        let result = purge_index(root).unwrap();
        assert!(result.purged);
        assert!(!root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(!root.join(MANIFEST_PATH_RELATIVE).exists());
    }

    #[test]
    fn purge_idempotent() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let result = purge_index(root).unwrap();
        assert!(result.purged);
    }

    #[test]
    fn search_no_token_overlap_skipped() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("fruit.rs"), "fn apple() {}\nfn orange() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "fruit.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "fruit.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let (evidence, _stats) = search_persistent_bm25(root, "banana", 10, &policy).unwrap();
        assert!(evidence.is_empty(), "no token overlap should skip");
    }

    #[test]
    fn search_span_bounded() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let mut content = String::new();
        for i in 1..=100 {
            content.push_str(&format!("line {} has authentication data\n", i));
        }
        std::fs::write(root.join("big.rs"), &content).unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "big.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "big.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let (evidence, _stats) =
            search_persistent_bm25(root, "authentication", 10, &policy).unwrap();
        for ev in &evidence {
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
    fn search_freshness_verified_current() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("test.rs"), "fn hello() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "test.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "test.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let (evidence, _stats) = search_persistent_bm25(root, "hello", 10, &policy).unwrap();
        if let Some(ev) = evidence.first() {
            assert_eq!(
                ev.meta.as_ref().unwrap().freshness,
                Some(Freshness::VerifiedCurrent)
            );
        }
    }

    #[test]
    fn build_empty_records() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let policy = Policy::default();
        let result = build_index(root, &[], &policy, ChunkStrategy::LineWindowV1).unwrap();
        assert!(result.success);
        assert_eq!(result.file_count, 0);
        assert_eq!(result.chunk_count, 0);
    }

    #[test]
    fn status_no_index() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let policy = Policy::default();
        let status = status_index(root, &policy).unwrap();
        assert!(!status.exists);
        assert!(status.requires_rebuild);
    }

    #[test]
    fn validate_no_index() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let policy = Policy::default();
        let validate = validate_index(root, &policy).unwrap();
        assert!(!validate.valid);
    }

    #[test]
    fn reusable_index_handle_open_and_search() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("app.rs"), "fn authenticate_user() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "app.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let handle = PersistentBm25Index::open(root, &policy).unwrap();
        let (evidence, stats) = handle.search(root, "authenticate", 10).unwrap();
        assert!(!evidence.is_empty());
        assert_eq!(stats.stale_hits_skipped, 0);
    }

    #[test]
    fn reusable_index_handle_policy_mismatch() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("app.rs"), "fn authenticate() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "app.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let mut different_policy = Policy::default();
        different_policy.remote.allow = true;

        let result = PersistentBm25Index::open(root, &different_policy);
        assert!(
            result.is_err(),
            "should refuse to open with mismatched policy"
        );
    }

    #[test]
    fn search_and_reusable_open_refuse_missing_manifest() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("app.rs"), "fn authenticate() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "app.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "app.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        std::fs::remove_file(root.join(MANIFEST_PATH_RELATIVE)).unwrap();

        let search_result = search_persistent_bm25(root, "authenticate", 10, &policy);
        assert!(
            search_result.is_err(),
            "persistent search must refuse when manifest is missing"
        );
        let search_err = format!("{}", search_result.unwrap_err());
        assert!(search_err.contains("manifest missing"));

        let open_result = PersistentBm25Index::open(root, &policy);
        assert!(
            open_result.is_err(),
            "reusable index open must refuse when manifest is missing"
        );
        let open_err = format!("{}", open_result.err().unwrap());
        assert!(open_err.contains("manifest missing"));
    }

    #[test]
    fn dirty_clean_after_build() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn a() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(dirty.clean);
        assert!(!dirty.requires_update);
        assert!(!dirty.requires_rebuild);
        assert!(dirty.added_files.is_empty());
        assert!(dirty.modified_files.is_empty());
        assert!(dirty.deleted_files.is_empty());
        assert!(dirty.policy_hash_matches);
        assert!(dirty.schema_matches);
    }

    #[test]
    fn dirty_detects_modified() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn old() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Modify file
        std::fs::write(root.join("a.rs"), "fn new() {}\nfn extra() {}\n").unwrap();

        // Re-scan to get updated records (but the old ones are fine for dirty check)
        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(!dirty.clean);
        assert!(dirty.requires_update);
        assert!(dirty.modified_files.contains(&"a.rs".to_string()));
    }

    #[test]
    fn dirty_detects_deleted() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn a() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Delete file
        std::fs::remove_file(root.join("a.rs")).unwrap();

        let dirty = dirty_index(root, &policy, &[]).unwrap();
        assert!(!dirty.clean);
        assert!(dirty.deleted_files.contains(&"a.rs".to_string()));
    }

    #[test]
    fn dirty_detects_added() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn a() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Add a new file
        std::fs::write(root.join("b.rs"), "fn b() {}\n").unwrap();
        let new_records = vec![
            FileRecord {
                path: "a.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "a.rs"),
                language: "rust".into(),
            },
            FileRecord {
                path: "b.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "b.rs"),
                language: "rust".into(),
            },
        ];

        let dirty = dirty_index(root, &policy, &new_records).unwrap();
        assert!(!dirty.clean);
        assert!(dirty.added_files.contains(&"b.rs".to_string()));
    }

    #[test]
    fn dirty_no_index_requires_rebuild() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let policy = Policy::default();
        let dirty = dirty_index(root, &policy, &[]).unwrap();
        assert!(dirty.requires_rebuild);
        assert!(!dirty.clean);
    }

    #[test]
    fn update_dirty_modified_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn authenticate() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Modify file
        std::fs::write(root.join("a.rs"), "fn authorize() {}\nfn extra() {}\n").unwrap();

        // Re-scan
        let new_records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let result = update_index(root, &policy, &new_records, true, None).unwrap();
        assert!(result.success);
        assert_eq!(result.modified_count, 1);
        assert!(result.post_status_clean);

        // Search should find the new content
        let (evidence, stats) = search_persistent_bm25(root, "authorize", 10, &policy).unwrap();
        assert!(!evidence.is_empty(), "should find updated content");
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 0);

        let (old_evidence, old_stats) =
            search_persistent_bm25(root, "authenticate", 10, &policy).unwrap();
        assert!(
            old_evidence.is_empty(),
            "old modified term must not emit evidence"
        );
        assert_eq!(old_stats.stale_hits_skipped, 0);
        assert_eq!(old_stats.invalid_hits_skipped, 0);

        let validate = validate_index(root, &policy).unwrap();
        assert!(
            validate.valid,
            "validate after dirty modify update: {validate:?}"
        );
        let dirty = dirty_index(root, &policy, &new_records).unwrap();
        assert!(dirty.clean, "dirty after dirty modify update: {dirty:?}");
    }

    #[test]
    fn update_dirty_added_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn authenticate() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Add a new file
        std::fs::write(root.join("b.rs"), "fn new_function() {}\n").unwrap();
        let new_records = vec![
            FileRecord {
                path: "a.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "a.rs"),
                language: "rust".into(),
            },
            FileRecord {
                path: "b.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "b.rs"),
                language: "rust".into(),
            },
        ];

        let result = update_index(root, &policy, &new_records, true, None).unwrap();
        assert!(result.success);
        assert_eq!(result.added_count, 1);
        assert!(result.post_status_clean);

        // Search should find the new file
        let (evidence, stats) = search_persistent_bm25(root, "new_function", 10, &policy).unwrap();
        assert!(!evidence.is_empty(), "should find newly added file");
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 0);

        let validate = validate_index(root, &policy).unwrap();
        assert!(
            validate.valid,
            "validate after dirty add update: {validate:?}"
        );
        let dirty = dirty_index(root, &policy, &new_records).unwrap();
        assert!(dirty.clean, "dirty after dirty add update: {dirty:?}");
    }

    #[test]
    fn update_dirty_deleted_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn authenticate() {}\n").unwrap();
        std::fs::write(root.join("b.rs"), "fn other() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![
            FileRecord {
                path: "a.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "a.rs"),
                language: "rust".into(),
            },
            FileRecord {
                path: "b.rs".into(),
                size: 0,
                content_sha: compute_sha(root, "b.rs"),
                language: "rust".into(),
            },
        ];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Delete file b.rs
        std::fs::remove_file(root.join("b.rs")).unwrap();

        let new_records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let result = update_index(root, &policy, &new_records, true, None).unwrap();
        assert!(result.success);
        assert_eq!(result.deleted_count, 1);
        assert!(result.post_status_clean);

        // Search should not find deleted file
        let (evidence, stats) = search_persistent_bm25(root, "other", 10, &policy).unwrap();
        assert!(
            evidence.is_empty(),
            "deleted file should not appear in search"
        );
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 0);

        let validate = validate_index(root, &policy).unwrap();
        assert!(
            validate.valid,
            "validate after dirty delete update: {validate:?}"
        );
        let dirty = dirty_index(root, &policy, &new_records).unwrap();
        assert!(dirty.clean, "dirty after dirty delete update: {dirty:?}");
    }

    #[test]
    fn update_refuses_missing_manifest() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let policy = Policy::default();
        let result = update_index(root, &policy, &[], true, None).unwrap();
        assert!(!result.success);
        assert!(result.error.is_some());
        assert!(result.error.unwrap().contains("manifest missing"));
    }

    #[test]
    fn update_refuses_policy_mismatch() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn a() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let mut different_policy = Policy::default();
        different_policy.remote.allow = true;

        let result = update_index(root, &different_policy, &records, true, None).unwrap();
        assert!(!result.success);
        assert!(result.error.is_some());
        let err = result.error.unwrap();
        assert!(err.contains("policy hash mismatch"), "got: {}", err);
    }

    #[test]
    fn update_single_path() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn authenticate() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Modify file
        std::fs::write(root.join("a.rs"), "fn authorize() {}\nfn extra() {}\n").unwrap();

        let new_records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let result = update_index(root, &policy, &new_records, false, Some("a.rs")).unwrap();
        assert!(result.success);
        assert_eq!(result.modified_count, 1);
        assert!(result.post_status_clean);
    }

    #[test]
    fn dirty_skipped_empty_file_clean_after_build() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Empty policy-included file → skipped in manifest
        std::fs::write(root.join("empty.rs"), "").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "empty.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "empty.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Dirty should report clean (skipped entry, sha unchanged)
        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(
            dirty.clean,
            "skipped empty file should not dirty: {:?}",
            dirty
        );
        assert!(!dirty.requires_update);
        // Should NOT appear in added_files
        assert!(
            !dirty.added_files.contains(&"empty.rs".to_string()),
            "skipped empty file should not be in added_files: {:?}",
            dirty.added_files
        );
    }

    #[test]
    fn dirty_skipped_to_nonempty_modified() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Empty file → skipped
        std::fs::write(root.join("grow.rs"), "").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "grow.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "grow.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // File becomes non-empty
        std::fs::write(root.join("grow.rs"), "fn new_content() {}\n").unwrap();
        let new_records = vec![FileRecord {
            path: "grow.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "grow.rs"),
            language: "rust".into(),
        }];

        let dirty = dirty_index(root, &policy, &new_records).unwrap();
        assert!(!dirty.clean, "skipped→nonempty should dirty");
        assert!(dirty.requires_update);
        // Should appear in modified_files, NOT added_files
        assert!(
            dirty.modified_files.contains(&"grow.rs".to_string()),
            "skipped→nonempty should be in modified_files: {:?}",
            dirty.modified_files
        );
        assert!(
            !dirty.added_files.contains(&"grow.rs".to_string()),
            "skipped→nonempty should NOT be in added_files: {:?}",
            dirty.added_files
        );
    }

    #[test]
    fn update_skipped_to_nonempty_promotes_to_indexed() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Empty file → skipped
        std::fs::write(root.join("grow.rs"), "").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "grow.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "grow.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // File becomes non-empty
        std::fs::write(root.join("grow.rs"), "fn searchable_content() {}\n").unwrap();
        let new_records = vec![FileRecord {
            path: "grow.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "grow.rs"),
            language: "rust".into(),
        }];

        let result = update_index(root, &policy, &new_records, true, None).unwrap();
        assert!(result.success);
        assert!(
            result.modified_count >= 1,
            "skipped→nonempty should count as modified"
        );
        assert!(result.post_status_clean);

        // Should now be searchable
        let (evidence, stats) =
            search_persistent_bm25(root, "searchable_content", 10, &policy).unwrap();
        assert!(!evidence.is_empty(), "promoted file should be searchable");
        assert_eq!(stats.stale_hits_skipped, 0);
        assert_eq!(stats.invalid_hits_skipped, 0);

        let validate = validate_index(root, &policy).unwrap();
        assert!(
            validate.valid,
            "validate after skipped-to-indexed update: {validate:?}"
        );
        let dirty = dirty_index(root, &policy, &new_records).unwrap();
        assert!(
            dirty.clean,
            "dirty after skipped-to-indexed update: {dirty:?}"
        );
    }

    #[test]
    fn update_single_path_rejects_absolute_and_parent_paths_before_probe() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write_file(root, "a.rs", "fn a() {}\n");

        let policy = Policy::default();
        let records = vec![file_record(root, "a.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let absolute = root.join("a.rs");
        let abs_result = update_index(
            root,
            &policy,
            &records,
            false,
            Some(absolute.to_str().unwrap()),
        )
        .unwrap();
        assert!(!abs_result.success);
        assert!(abs_result.error.unwrap().contains("path is unsafe"));

        let parent_result = update_index(root, &policy, &records, false, Some("../a.rs")).unwrap();
        assert!(!parent_result.success);
        assert!(parent_result.error.unwrap().contains("path is unsafe"));
    }

    #[test]
    fn dirty_skipped_unchanged_clean() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Empty file → skipped
        std::fs::write(root.join("skip.rs"), "").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "skip.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "skip.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // File still empty — no change
        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(dirty.clean, "unchanged skipped file should be clean");
    }

    #[test]
    fn update_refuses_schema_mismatch() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn a() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Corrupt the schema version in the manifest by writing raw JSON
        let manifest_path = root.join(MANIFEST_PATH_RELATIVE);
        let raw = std::fs::read_to_string(&manifest_path).unwrap();
        let corrupted = raw.replace("\"r8-bm25-v2\"", "\"unknown-v99\"");
        std::fs::write(&manifest_path, corrupted).unwrap();

        // dirty_index should require rebuild due to load failure
        let dirty = dirty_index(root, &policy, &records);
        if let Ok(d) = dirty {
            assert!(d.requires_rebuild, "should require rebuild for bad schema");
        }

        // update_index should also fail
        let result = update_index(root, &policy, &records, true, None).unwrap();
        assert!(!result.success, "should refuse update for bad schema");
    }

    #[test]
    fn update_refuses_chunk_strategy_mismatch() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn a() {}\n").unwrap();

        let policy = Policy::default();
        let records = vec![FileRecord {
            path: "a.rs".into(),
            size: 0,
            content_sha: compute_sha(root, "a.rs"),
            language: "rust".into(),
        }];

        let _ = build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Corrupt chunk_strategy in the manifest by writing raw JSON
        let manifest_path = root.join(MANIFEST_PATH_RELATIVE);
        let raw = std::fs::read_to_string(&manifest_path).unwrap();
        let corrupted = raw.replace("\"line_window_v1\"", "\"unknown_strategy\"");
        std::fs::write(&manifest_path, corrupted).unwrap();

        // dirty_index should require rebuild due to load failure
        let dirty = dirty_index(root, &policy, &records);
        if let Ok(d) = dirty {
            assert!(
                d.requires_rebuild,
                "should require rebuild for bad strategy"
            );
        }

        // update_index should also fail
        let result = update_index(root, &policy, &records, true, None).unwrap();
        assert!(!result.success, "should refuse update for bad strategy");
    }

    // ── B0 correctness: chunk_count == Tantivy live num_docs ──────────

    /// Open the Tantivy index at `state_root` and return the authoritative
    /// live (non-deleted) doc count from a freshly built searcher.
    fn live_num_docs(state_root: &Path) -> u64 {
        let tantivy_dir = state_root.join(TANTIVY_DIR_RELATIVE);
        let index = Index::open_in_dir(&tantivy_dir).expect("open tantivy index");
        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::Manual)
            .try_into()
            .expect("build reader");
        reader.searcher().num_docs()
    }

    /// Load the manifest at `state_root` and return its `chunk_count`.
    fn manifest_chunk_count(state_root: &Path) -> u64 {
        IndexManifest::load_at_state_root(state_root)
            .expect("load manifest")
            .chunk_count
    }

    /// Assert manifest chunk_count == Tantivy live num_docs (problem #1).
    fn assert_chunk_count_matches_live(state_root: &Path, context: &str) {
        let mc = manifest_chunk_count(state_root);
        let live = live_num_docs(state_root);
        assert_eq!(
            mc, live,
            "manifest.chunk_count ({}) != Tantivy live num_docs ({}) after {}",
            mc, live, context
        );
    }

    /// Helper: produce `num_lines` lines of distinct content for chunk tests.
    fn lines_content(num_lines: usize, prefix: &str) -> String {
        (0..num_lines)
            .map(|i| format!("{prefix}_line_{i}();\n"))
            .collect()
    }

    /// Problem #1: after a 1-chunk file is modified to span many chunks,
    /// manifest.chunk_count must equal Tantivy live num_docs (not the old
    /// rough estimate which would over/under-count).
    #[test]
    fn update_chunk_count_matches_tantivy_after_1_to_many_modification() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // 1 line → 1 chunk
        std::fs::write(root.join("a.rs"), "fn seed() {}\n").unwrap();
        let policy = Policy::default();
        let records = vec![file_record(root, "a.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        assert_chunk_count_matches_live(root, "build (1 chunk)");
        assert_eq!(manifest_chunk_count(root), 1);

        // Modify to 95 lines → ceil(95/30) = 4 chunks
        let big = lines_content(95, "fn");
        std::fs::write(root.join("a.rs"), &big).unwrap();
        let new_records = vec![file_record(root, "a.rs")];

        let result = update_index(root, &policy, &new_records, true, None).unwrap();
        assert!(result.success);
        assert_eq!(result.modified_count, 1);
        assert_chunk_count_matches_live(root, "update 1→many chunks");
        assert_eq!(
            manifest_chunk_count(root),
            4,
            "95 lines / 30 = 4 chunks expected"
        );

        // Searchable in the new state
        let (ev, _stats) = search_persistent_bm25(root, "fn_line_0", 10, &policy).unwrap();
        assert!(!ev.is_empty());
    }

    /// Problem #1: deleting files with differing chunk counts must leave
    /// manifest.chunk_count == Tantivy live num_docs (not a `total_deleted*2`
    /// estimate).
    #[test]
    fn update_chunk_count_matches_tantivy_after_deletion_of_differing_chunk_counts() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // a: 1 chunk (1 line), b: 4 chunks (95 lines), c: 2 chunks (35 lines)
        std::fs::write(root.join("a.rs"), "fn a() {}\n").unwrap();
        std::fs::write(root.join("b.rs"), lines_content(95, "b")).unwrap();
        std::fs::write(root.join("c.rs"), lines_content(35, "c")).unwrap();

        let policy = Policy::default();
        let records = vec![
            file_record(root, "a.rs"),
            file_record(root, "b.rs"),
            file_record(root, "c.rs"),
        ];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        assert_chunk_count_matches_live(root, "build (1+4+2=7 chunks)");
        assert_eq!(manifest_chunk_count(root), 7);

        // Delete b (4 chunks) and c (2 chunks): only a (1 chunk) remains.
        std::fs::remove_file(root.join("b.rs")).unwrap();
        std::fs::remove_file(root.join("c.rs")).unwrap();
        let new_records = vec![file_record(root, "a.rs")];

        let result = update_index(root, &policy, &new_records, true, None).unwrap();
        assert!(result.success);
        assert_eq!(result.deleted_count, 2);
        assert_chunk_count_matches_live(root, "delete b(4)+c(2) chunks");
        assert_eq!(manifest_chunk_count(root), 1);
    }

    /// Problem #1: repeated incremental updates (add/modify/delete cycle)
    /// must keep manifest.chunk_count == Tantivy live num_docs at every step.
    #[test]
    fn update_chunk_count_matches_tantivy_after_repeated_incremental_updates() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("a.rs"), "fn a1() {}\n").unwrap();
        let policy = Policy::default();
        let records = vec![file_record(root, "a.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();
        assert_chunk_count_matches_live(root, "initial build");

        // Step 1: add b (3 chunks)
        std::fs::write(root.join("b.rs"), lines_content(65, "b")).unwrap();
        let records = vec![file_record(root, "a.rs"), file_record(root, "b.rs")];
        let r = update_index(root, &policy, &records, true, None).unwrap();
        assert!(r.success);
        assert_chunk_count_matches_live(root, "after add b");
        // a=1 + b=ceil(65/30)=3 → 4
        assert_eq!(manifest_chunk_count(root), 4);

        // Step 2: modify a to 2 chunks (31 lines)
        std::fs::write(root.join("a.rs"), lines_content(31, "a")).unwrap();
        let records = vec![file_record(root, "a.rs"), file_record(root, "b.rs")];
        let r = update_index(root, &policy, &records, true, None).unwrap();
        assert!(r.success);
        assert_chunk_count_matches_live(root, "after modify a");
        // a=ceil(31/30)=2 + b=3 → 5
        assert_eq!(manifest_chunk_count(root), 5);

        // Step 3: delete b
        std::fs::remove_file(root.join("b.rs")).unwrap();
        let records = vec![file_record(root, "a.rs")];
        let r = update_index(root, &policy, &records, true, None).unwrap();
        assert!(r.success);
        assert_chunk_count_matches_live(root, "after delete b");
        // only a=2 → 2
        assert_eq!(manifest_chunk_count(root), 2);

        // Step 4: no-op update (clean dirty) — count unchanged
        let r = update_index(root, &policy, &records, true, None).unwrap();
        assert!(r.success);
        assert_chunk_count_matches_live(root, "after no-op update");
        assert_eq!(manifest_chunk_count(root), 2);
    }

    /// Problem #1: split-root mode must also keep manifest.chunk_count ==
    /// Tantivy live num_docs after a modify that changes chunk count.
    #[test]
    fn update_chunk_count_matches_tantivy_split_root_mode() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();

        write_file(source_root, "src/app.rs", "fn seed() {}\n");
        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        assert_chunk_count_matches_live(state_root, "split-root build");
        assert_eq!(manifest_chunk_count(state_root), 1);

        // Modify to 95 lines → 4 chunks
        write_file(source_root, "src/app.rs", &lines_content(95, "fn"));
        let new_records = vec![file_record(source_root, "src/app.rs")];

        let result =
            update_index_at_state_root(source_root, state_root, &policy, &new_records, true, None)
                .unwrap();
        assert!(result.success);
        assert_chunk_count_matches_live(state_root, "split-root update 1→4 chunks");
        assert_eq!(manifest_chunk_count(state_root), 4);

        // Source tree must not have been mutated by the state write.
        assert!(!source_root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(!source_root.join(MANIFEST_PATH_RELATIVE).exists());
    }

    // ── B0 correctness: skipped→promotable with same SHA ──────────────

    /// Write a synthetic manifest directly, marking `files` as the manifest
    /// entries with the given `chunk_count`. Used to construct deterministic
    /// skipped fixtures (e.g. read_error on a file that is actually readable)
    /// that build_index could not produce on its own.
    fn write_synthetic_manifest(
        state_root: &Path,
        policy_hash: &str,
        files: Vec<ManifestFileEntry>,
        chunk_count: u64,
    ) {
        let manifest = IndexManifest::new_with_strategy(
            policy_hash.to_string(),
            files,
            chunk_count,
            ChunkStrategy::LineWindowV1,
            None,
        );
        manifest.save_at_state_root(state_root).unwrap();
    }

    /// Problem #2: a skipped (read_error) manifest entry whose file is now
    /// readable UTF-8 and nonempty must be reported as modified EVEN WHEN
    /// the content SHA is unchanged — so update_index can promote it.
    #[test]
    fn dirty_skipped_read_error_now_readable_same_sha_is_modified() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // File on disk is readable, nonempty UTF-8.
        let content = "fn promoted() {}\n";
        std::fs::write(root.join("grow.rs"), content).unwrap();
        let sha = compute_sha(root, "grow.rs");

        // Build an empty index (creates Tantivy dir + empty manifest).
        let policy = Policy::default();
        build_index(root, &[], &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Overwrite manifest with a synthetic skipped (read_error) entry
        // whose content_sha MATCHES the file's actual bytes.
        write_synthetic_manifest(
            root,
            &compute_policy_hash(&policy),
            vec![ManifestFileEntry {
                path: "grow.rs".into(),
                content_sha: sha.clone(),
                size_bytes: content.len() as u64,
                language: "rust".into(),
                status: "skipped".into(),
                skipped_reason: Some("read_error".into()),
            }],
            0,
        );

        // current_records must include grow.rs for the policy-included check.
        let records = vec![file_record(root, "grow.rs")];

        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(
            !dirty.clean,
            "skipped read_error now readable same SHA must be dirty: {:?}",
            dirty
        );
        assert!(dirty.requires_update);
        assert!(
            dirty.modified_files.contains(&"grow.rs".to_string()),
            "should be in modified_files: {:?}",
            dirty.modified_files
        );
        assert!(
            !dirty.added_files.contains(&"grow.rs".to_string()),
            "should NOT be in added_files"
        );
    }

    /// Problem #2: update_index must promote a skipped (read_error) entry
    /// to indexed when the file is now readable, even with unchanged SHA.
    #[test]
    fn update_skipped_read_error_now_readable_same_sha_promotes() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let content = "fn promoted() {}\n";
        std::fs::write(root.join("grow.rs"), content).unwrap();
        let sha = compute_sha(root, "grow.rs");

        let policy = Policy::default();
        build_index(root, &[], &policy, ChunkStrategy::LineWindowV1).unwrap();
        write_synthetic_manifest(
            root,
            &compute_policy_hash(&policy),
            vec![ManifestFileEntry {
                path: "grow.rs".into(),
                content_sha: sha,
                size_bytes: content.len() as u64,
                language: "rust".into(),
                status: "skipped".into(),
                skipped_reason: Some("read_error".into()),
            }],
            0,
        );

        let records = vec![file_record(root, "grow.rs")];
        let result = update_index(root, &policy, &records, true, None).unwrap();
        assert!(result.success);
        assert!(
            result.modified_count >= 1,
            "skipped→promotable should count as modified"
        );
        assert!(result.post_status_clean);

        // Promoted file is now searchable
        let (ev, stats) = search_persistent_bm25(root, "promoted", 10, &policy).unwrap();
        assert!(!ev.is_empty(), "promoted file should be searchable");
        assert_eq!(stats.stale_hits_skipped, 0);

        // Manifest entry is now indexed, no skipped_reason
        let entry = manifest_entry(root, "grow.rs");
        assert_eq!(entry.status, "indexed");
        assert_eq!(entry.skipped_reason, None);

        // chunk_count is authoritative (problem #1): 1 chunk for 1 line.
        assert_chunk_count_matches_live(root, "promote skipped→indexed");
        assert_eq!(manifest_chunk_count(root), 1);
    }

    /// Problem #2: an empty file that is STILL empty (same SHA) must remain
    /// clean — do not mark every skipped entry modified (would cause a
    /// permanent dirty loop).
    #[test]
    fn dirty_skipped_empty_unchanged_remains_clean() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("empty.rs"), "").unwrap();
        let policy = Policy::default();
        let records = vec![file_record(root, "empty.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        // Confirm it was skipped as empty_file
        let entry = manifest_entry(root, "empty.rs");
        assert_eq!(entry.status, "skipped");
        assert_eq!(entry.skipped_reason.as_deref(), Some("empty_file"));

        // No change → must remain clean
        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(
            dirty.clean,
            "unchanged empty skipped entry must be clean: {:?}",
            dirty
        );
        assert!(!dirty.modified_files.contains(&"empty.rs".to_string()));
    }

    /// Problem #2: a non-UTF-8 file (read_error) whose bytes are unchanged
    /// must remain clean — still unreadable under the same indexability
    /// semantics, SHA unchanged.
    #[test]
    fn dirty_skipped_non_utf8_unchanged_remains_clean() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        // Invalid UTF-8 bytes (build_index will skip as read_error)
        let invalid_utf8: &[u8] = &[0xFF, 0xFE, 0x00, 0x01, 0xC0, 0xC1];
        std::fs::write(root.join("bin.rs"), invalid_utf8).unwrap();

        let policy = Policy::default();
        let records = vec![file_record(root, "bin.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let entry = manifest_entry(root, "bin.rs");
        assert_eq!(entry.status, "skipped");
        assert_eq!(entry.skipped_reason.as_deref(), Some("read_error"));

        // No change → must remain clean (still non-UTF-8, SHA unchanged)
        let dirty = dirty_index(root, &policy, &records).unwrap();
        assert!(
            dirty.clean,
            "unchanged non-UTF-8 skipped entry must be clean: {:?}",
            dirty
        );
        assert!(!dirty.modified_files.contains(&"bin.rs".to_string()));
    }

    /// Problem #2: single-path update's unchanged fast path must NOT return
    /// no-op for a skipped entry that is now promotable with same SHA — it
    /// must fall through and promote.
    #[test]
    fn single_path_update_promotes_skipped_same_sha() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        let content = "fn via_path() {}\n";
        std::fs::write(root.join("p.rs"), content).unwrap();
        let sha = compute_sha(root, "p.rs");

        let policy = Policy::default();
        build_index(root, &[], &policy, ChunkStrategy::LineWindowV1).unwrap();
        write_synthetic_manifest(
            root,
            &compute_policy_hash(&policy),
            vec![ManifestFileEntry {
                path: "p.rs".into(),
                content_sha: sha,
                size_bytes: content.len() as u64,
                language: "rust".into(),
                status: "skipped".into(),
                skipped_reason: Some("read_error".into()),
            }],
            0,
        );

        let records = vec![file_record(root, "p.rs")];

        // Single-path update with same SHA must NOT be a no-op: it must
        // promote the skipped entry to indexed.
        let result = update_index(root, &policy, &records, false, Some("p.rs")).unwrap();
        assert!(result.success);
        // manifest_written=true because the entry was promoted
        assert!(
            result.manifest_written,
            "single-path update of promotable skipped entry must write manifest"
        );

        // Promoted file is now searchable
        let (ev, _stats) = search_persistent_bm25(root, "via_path", 10, &policy).unwrap();
        assert!(!ev.is_empty());

        let entry = manifest_entry(root, "p.rs");
        assert_eq!(entry.status, "indexed");
        assert_eq!(entry.skipped_reason, None);
        assert_chunk_count_matches_live(root, "single-path promote");
    }

    /// Problem #2: single-path update of a skipped entry that is STILL
    /// unindexable (empty, same SHA) must remain a no-op fast path — no
    /// dirty loop.
    #[test]
    fn single_path_update_skipped_still_empty_same_sha_is_noop() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();

        std::fs::write(root.join("e.rs"), "").unwrap();
        let policy = Policy::default();
        let records = vec![file_record(root, "e.rs")];
        build_index(root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let entry = manifest_entry(root, "e.rs");
        assert_eq!(entry.skipped_reason.as_deref(), Some("empty_file"));

        let result = update_index(root, &policy, &records, false, Some("e.rs")).unwrap();
        assert!(result.success);
        assert!(
            !result.manifest_written,
            "still-empty same-SHA skipped entry must be a no-op"
        );

        // Still skipped
        let entry = manifest_entry(root, "e.rs");
        assert_eq!(entry.status, "skipped");
        assert_eq!(entry.skipped_reason.as_deref(), Some("empty_file"));
    }

    /// Problem #2: dirty_index must never read outside source_root. A
    /// skipped entry whose path is unsafe (symlink escape) is `continue`d
    /// before any content read, so changes to the out-of-root target are
    /// invisible. Cross-platform: gracefully skips when symlinks are
    /// unavailable (Windows without SeCreateSymbolicLinkPrivilege).
    #[test]
    fn dirty_skipped_unsafe_symlink_does_not_read_outside_root() {
        let outside_dir = tempfile::tempdir().unwrap();
        let outside_file = outside_dir.path().join("target.rs");
        std::fs::write(&outside_file, "fn original() {}\n").unwrap();

        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let link_path = source_root.join("link.rs");
        if !create_symlink_file_for_test(&outside_file, &link_path) {
            eprintln!("skipping symlink test: symlinks unavailable on this platform");
            return;
        }

        let policy = Policy::default();
        // Build: link.rs is skipped as path_unsafe (validate_path rejects
        // the symlink escape). The manifest stores record.content_sha,
        // which was computed by the scanner following the symlink.
        let records = vec![file_record(source_root, "link.rs")];
        build_index(source_root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let entry = manifest_entry(source_root, "link.rs");
        assert_eq!(entry.status, "skipped");
        assert_eq!(entry.skipped_reason.as_deref(), Some("path_unsafe"));

        // Mutate the OUTSIDE-root target file.
        std::fs::write(&outside_file, "fn changed() {}\n").unwrap();

        // dirty_index must NOT detect this change (never reads outside
        // source_root). If it did, the SHA would differ and it would be
        // reported as modified.
        let dirty = dirty_index(source_root, &policy, &records).unwrap();
        assert!(
            dirty.clean,
            "must not detect outside-root change (would mean we read outside source_root): {:?}",
            dirty
        );
        assert!(!dirty.modified_files.contains(&"link.rs".to_string()));
    }

    /// Problem #2: formerly-unsafe symlink replaced by a safe regular file
    /// with the SAME bytes (and thus same SHA) must become dirty and
    /// promote to indexed. Cross-platform: skips when symlinks unavailable.
    #[test]
    fn dirty_skipped_unsafe_symlink_now_safe_same_bytes_promotes() {
        let outside_dir = tempfile::tempdir().unwrap();
        let outside_file = outside_dir.path().join("target.rs");
        let content = "fn promoted() {}\n";
        std::fs::write(&outside_file, content).unwrap();

        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let link_path = source_root.join("link.rs");
        if !create_symlink_file_for_test(&outside_file, &link_path) {
            eprintln!("skipping symlink test: symlinks unavailable on this platform");
            return;
        }

        let policy = Policy::default();
        let records = vec![file_record(source_root, "link.rs")];
        build_index(source_root, &records, &policy, ChunkStrategy::LineWindowV1).unwrap();

        let entry = manifest_entry(source_root, "link.rs");
        assert_eq!(entry.status, "skipped");
        assert_eq!(entry.skipped_reason.as_deref(), Some("path_unsafe"));

        // Replace symlink with a regular file containing the SAME bytes.
        // SHA is unchanged, but the path is now safe → promotable.
        std::fs::remove_file(&link_path).unwrap();
        std::fs::write(&link_path, content).unwrap();

        let dirty = dirty_index(source_root, &policy, &records).unwrap();
        assert!(
            !dirty.clean,
            "skipped unsafe→safe same SHA must be dirty: {:?}",
            dirty
        );
        assert!(dirty.modified_files.contains(&"link.rs".to_string()));

        // update promotes to indexed
        let result = update_index(source_root, &policy, &records, true, None).unwrap();
        assert!(result.success);
        assert!(result.modified_count >= 1);

        // Promoted file is searchable
        let (ev, _stats) = search_persistent_bm25(source_root, "promoted", 10, &policy).unwrap();
        assert!(!ev.is_empty(), "promoted file should be searchable");

        let entry = manifest_entry(source_root, "link.rs");
        assert_eq!(entry.status, "indexed");
        assert_eq!(entry.skipped_reason, None);
        assert_chunk_count_matches_live(source_root, "unsafe→safe promote");
    }

    // ── B0 filesystem-safety closure tests ─────────────────────────────
    //
    // Quiescent-tree, preexisting-redirection boundary: reject preexisting
    // descendant symlinks (Unix) and reparse points (Windows) below the
    // state-root trust anchor when checked. Prove rejection BEFORE
    // mutation: source/outside sentinels byte-identical; existing regular
    // index/manifest unchanged where relevant; purge deletes nothing.
    //
    // Non-vacuous on Linux (real symlinks). On Windows, file-symlink
    // fixtures skip when privilege is unavailable (error 1314); junction
    // fixtures cover the reparse-point case on windows-latest.

    /// Helper: write a sentinel file with known bytes; return its path.
    fn write_sentinel(dir: &Path, name: &str, bytes: &[u8]) -> PathBuf {
        let path = dir.join(name);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(&path, bytes).unwrap();
        path
    }

    /// Helper: read sentinel bytes back, asserting they are unchanged.
    fn assert_sentinel_unchanged(path: &Path, expected: &[u8]) {
        let after = std::fs::read(path).unwrap();
        assert_eq!(
            after.as_slice(),
            expected,
            "sentinel at {} must be byte-identical after rejection",
            path.display()
        );
    }

    /// Linked `.openlocus/index` directory: build must reject BEFORE
    /// deleting/rebuilding anything. Source sentinels remain byte-identical.
    /// Non-vacuous on Unix; on Windows directory symlinks require privilege
    /// (junction fixtures are covered separately).
    #[test]
    fn b0_build_rejects_linked_index_dir_before_mutation() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let source_sentinel =
            write_sentinel(source_root, "src/sentinel.b0", b"source-sentinel-bytes\n");

        let openlocus_dir = state_root.join(".openlocus");
        std::fs::create_dir_all(&openlocus_dir).unwrap();
        let state_sentinel = write_sentinel(&openlocus_dir, "policy.toml", b"# state sentinel\n");

        // Build a real index first so the preflight has something to find.
        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        // Now replace `.openlocus/index` with a symlink to an OUTSIDE dir.
        std::fs::remove_dir_all(state_root.join(INDEX_DIR_RELATIVE)).unwrap();
        let outside_dir = tempfile::tempdir().unwrap();
        let link_path = state_root.join(INDEX_DIR_RELATIVE);
        if !create_symlink_dir_for_test(outside_dir.path(), &link_path) {
            eprintln!("skipping b0 linked-index-dir test: symlinks unavailable on this host");
            return;
        }

        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path")
                || err.contains("cannot stat state artifact"),
            "got: {}",
            err
        );

        assert_sentinel_unchanged(&source_sentinel, b"source-sentinel-bytes\n");
        assert_sentinel_unchanged(&state_sentinel, b"# state sentinel\n");
        assert!(
            outside_dir
                .path()
                .read_dir()
                .map(|mut r| r.next().is_none())
                .unwrap_or(true),
            "outside target must remain empty after rejection"
        );
    }

    /// Linked manifest.json: build must reject BEFORE writing. Outside
    /// target untouched.
    #[test]
    fn b0_build_rejects_linked_manifest_final_before_mutation() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let manifest_path = state_root.join(MANIFEST_PATH_RELATIVE);
        let outside = tempfile::tempdir().unwrap();
        let outside_target = outside.path().join("outside-manifest.json");
        std::fs::write(&outside_target, b"# outside manifest\n").unwrap();
        std::fs::remove_file(&manifest_path).unwrap();
        if !create_symlink_file_for_test(&outside_target, &manifest_path) {
            eprintln!("skipping b0 linked-manifest-final test: symlinks unavailable on this host");
            return;
        }

        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path"),
            "got: {}",
            err
        );

        let after = std::fs::read(&outside_target).unwrap();
        assert_eq!(after.as_slice(), b"# outside manifest\n");
    }

    /// Linked manifest.json.tmp: a preexisting LINK at the tmp path
    /// rejects before write. Existing manifest byte-identical.
    #[test]
    fn b0_build_rejects_linked_manifest_tmp_before_mutation() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        let manifest_before = std::fs::read(state_root.join(MANIFEST_PATH_RELATIVE)).unwrap();

        let tmp_path = state_root.join(".openlocus/index/manifest.json.tmp");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-tmp-target-for-openlocus-b0-test"),
            &tmp_path,
        ) {
            eprintln!("skipping b0 linked-manifest-tmp test: symlinks unavailable on this host");
            return;
        }

        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path")
                || err.contains("dangling symlink"),
            "got: {}",
            err
        );

        let manifest_after = std::fs::read(state_root.join(MANIFEST_PATH_RELATIVE)).unwrap();
        assert_eq!(
            manifest_after.as_slice(),
            manifest_before.as_slice(),
            "existing manifest must be byte-identical after rejection"
        );
    }

    /// Linked Tantivy dir: build must reject BEFORE deleting/rebuilding.
    #[test]
    fn b0_build_rejects_linked_tantivy_dir_before_mutation() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        std::fs::create_dir_all(state_root.join(INDEX_DIR_RELATIVE)).unwrap();
        let outside = tempfile::tempdir().unwrap();
        let tantivy_link = state_root.join(TANTIVY_DIR_RELATIVE);
        if !create_symlink_dir_for_test(outside.path(), &tantivy_link) {
            eprintln!("skipping b0 linked-tantivy-dir test: symlinks unavailable on this host");
            return;
        }

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path"),
            "got: {}",
            err
        );

        assert!(
            outside
                .path()
                .read_dir()
                .map(|mut r| r.next().is_none())
                .unwrap_or(true),
            "outside target must remain empty after rejection"
        );
    }

    /// Linked descendant INSIDE the Tantivy subtree: a symlink placed
    /// inside an existing real tantivy dir must reject before mutation.
    #[test]
    fn b0_build_rejects_linked_tantivy_descendant_before_mutation() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        let tantivy_dir = state_root.join(TANTIVY_DIR_RELATIVE);

        let in_root_link = tantivy_dir.join("hostile-link");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-in-root-target-for-openlocus-b0-test"),
            &in_root_link,
        ) {
            eprintln!(
                "skipping b0 linked-tantivy-descendant test: symlinks unavailable on this host"
            );
            return;
        }

        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path"),
            "got: {}",
            err
        );
    }

    /// Linked `.openlocus` directory itself: build must reject.
    #[test]
    fn b0_build_rejects_linked_openlocus_dir_before_mutation() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let state_sentinel = write_sentinel(state_root, "sentinel.b0", b"state-sentinel\n");

        let outside = tempfile::tempdir().unwrap();
        let openlocus_link = state_root.join(".openlocus");
        if !create_symlink_dir_for_test(outside.path(), &openlocus_link) {
            eprintln!("skipping b0 linked-openlocus-dir test: symlinks unavailable on this host");
            return;
        }

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path")
                || err.contains("dangling symlink"),
            "got: {}",
            err
        );

        assert_sentinel_unchanged(&state_sentinel, b"state-sentinel\n");
        assert!(
            outside
                .path()
                .read_dir()
                .map(|mut r| r.next().is_none())
                .unwrap_or(true),
            "outside target must remain empty after rejection"
        );
    }

    /// Purge: any link in the artifact set aborts ALL deletion. Purge
    /// deletes nothing; sentinels byte-identical.
    #[test]
    fn b0_purge_rejects_linked_artifact_and_deletes_nothing() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        let manifest_before = std::fs::read(state_root.join(MANIFEST_PATH_RELATIVE)).unwrap();

        let tmp_path = state_root.join(".openlocus/index/manifest.json.tmp");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-purge-tmp-target-for-openlocus-b0-test"),
            &tmp_path,
        ) {
            eprintln!("skipping b0 purge link test: symlinks unavailable on this host");
            return;
        }

        let err = purge_index_at_state_root(source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path")
                || err.contains("dangling symlink"),
            "got: {}",
            err
        );

        let manifest_after = std::fs::read(state_root.join(MANIFEST_PATH_RELATIVE)).unwrap();
        assert_eq!(
            manifest_after.as_slice(),
            manifest_before.as_slice(),
            "manifest must be byte-identical after purge rejection"
        );
        assert!(
            state_root.join(TANTIVY_DIR_RELATIVE).exists(),
            "tantivy dir must remain after purge rejection"
        );
    }

    /// Status/dirty/validate/search/open: preflight before path-based
    /// read/open. A linked manifest rejects before reading.
    #[test]
    fn b0_status_rejects_linked_manifest_before_read() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let manifest_path = state_root.join(MANIFEST_PATH_RELATIVE);
        let outside = tempfile::tempdir().unwrap();
        let outside_target = outside.path().join("outside-manifest.json");
        std::fs::write(&outside_target, b"# outside manifest\n").unwrap();
        std::fs::remove_file(&manifest_path).unwrap();
        if !create_symlink_file_for_test(&outside_target, &manifest_path) {
            eprintln!("skipping b0 status link test: symlinks unavailable on this host");
            return;
        }

        let status_err = status_index_at_state_root(source_root, state_root, &policy)
            .unwrap_err()
            .to_string();
        assert!(
            status_err.contains("symlink in state artifact path")
                || status_err.contains("reparse point in state artifact path"),
            "got: {}",
            status_err
        );

        let after = std::fs::read(&outside_target).unwrap();
        assert_eq!(after.as_slice(), b"# outside manifest\n");

        let dirty_err = dirty_index_at_state_root(source_root, state_root, &policy, &records)
            .unwrap_err()
            .to_string();
        assert!(
            dirty_err.contains("symlink in state artifact path")
                || dirty_err.contains("reparse point in state artifact path"),
            "got: {}",
            dirty_err
        );

        let validate_err = validate_index_at_state_root(source_root, state_root, &policy)
            .unwrap_err()
            .to_string();
        assert!(
            validate_err.contains("symlink in state artifact path")
                || validate_err.contains("reparse point in state artifact path"),
            "got: {}",
            validate_err
        );

        let search_err = search_persistent_bm25_at_state_root(
            source_root,
            state_root,
            "authenticate",
            10,
            &policy,
        )
        .unwrap_err()
        .to_string();
        assert!(
            search_err.contains("symlink in state artifact path")
                || search_err.contains("reparse point in state artifact path"),
            "got: {}",
            search_err
        );

        let open_err = PersistentBm25Index::open_at_state_root(source_root, state_root, &policy)
            .err()
            .unwrap_or_else(|| panic!("open must reject linked manifest"))
            .to_string();
        assert!(
            open_err.contains("symlink in state artifact path")
                || open_err.contains("reparse point in state artifact path"),
            "got: {}",
            open_err
        );
    }

    /// Update: linked manifest tmp rejects BEFORE the Tantivy commit, so
    /// the existing manifest remains unchanged.
    #[test]
    fn b0_update_rejects_linked_manifest_tmp_before_commit() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        let manifest_before = std::fs::read(state_root.join(MANIFEST_PATH_RELATIVE)).unwrap();

        write_file(source_root, "src/app.rs", "fn changed_after_build() {}\n");
        let new_records = vec![file_record(source_root, "src/app.rs")];

        let tmp_path = state_root.join(".openlocus/index/manifest.json.tmp");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-update-tmp-target-for-openlocus-b0-test"),
            &tmp_path,
        ) {
            eprintln!("skipping b0 update link test: symlinks unavailable on this host");
            return;
        }

        let err =
            update_index_at_state_root(source_root, state_root, &policy, &new_records, true, None)
                .unwrap_err()
                .to_string();
        assert!(
            err.contains("symlink in state artifact path")
                || err.contains("reparse point in state artifact path")
                || err.contains("dangling symlink"),
            "got: {}",
            err
        );

        let manifest_after = std::fs::read(state_root.join(MANIFEST_PATH_RELATIVE)).unwrap();
        assert_eq!(
            manifest_after.as_slice(),
            manifest_before.as_slice(),
            "existing manifest must be byte-identical after rejection"
        );
    }

    /// Compatibility/happy-path: colocated API behavior preserved, and
    /// nonexistent state root is created by build. Source under state
    /// but outside .openlocus/index is allowed.
    #[test]
    fn b0_colocated_and_nonexistent_state_root_compatibility() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let result = purge_index(root).unwrap();
        assert!(result.purged);
        assert!(result.removed_paths.is_empty());

        // Separated mode with a nonexistent state root: build creates it.
        let src_dir = tempfile::tempdir().unwrap();
        let state_parent = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_parent.path().join("nonexistent-state-dir");
        assert!(!state_root.exists());
        write_file(source_root, "src/app.rs", "fn authenticate_user() {}\n");
        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        let result = build_index_at_state_root(
            source_root,
            &state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        assert!(result.success);
        assert!(state_root.join(MANIFEST_PATH_RELATIVE).exists());

        // Source under state but outside .openlocus/index is allowed.
        let state_dir = tempfile::tempdir().unwrap();
        let state_root = state_dir.path();
        let source_root = state_root.join("src");
        std::fs::create_dir_all(&source_root).unwrap();
        write_file(&source_root, "app.rs", "fn authenticate_user() {}\n");
        let policy = Policy::default();
        let records = vec![file_record(&source_root, "app.rs")];
        let result = build_index_at_state_root(
            &source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        assert!(result.success);
        assert!(source_root.join("app.rs").exists());
    }

    /// Idempotent purge: a second purge on an already-purged state root
    /// succeeds and removes nothing.
    #[test]
    fn b0_purge_idempotent_after_first_purge() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();

        let first = purge_index_at_state_root(source_root, state_root).unwrap();
        assert!(first.purged);
        assert!(!state_root.join(TANTIVY_DIR_RELATIVE).exists());
        assert!(!state_root.join(MANIFEST_PATH_RELATIVE).exists());

        let second = purge_index_at_state_root(source_root, state_root).unwrap();
        assert!(second.purged);
        assert!(second.removed_paths.is_empty());
    }

    // ── Windows-specific reparse-point fixtures ───────────────────────
    //
    // On Windows, junctions are reparse points that don't require the
    // SeCreateSymbolicLinkPrivilege. They are created via `cmd /C mklink /J`.
    // These fixtures are non-vacuous on windows-latest.

    #[cfg(windows)]
    fn create_junction_for_test(src: &Path, dst: &Path) -> bool {
        let src_str = src.to_string_lossy();
        let dst_str = dst.to_string_lossy();
        let output = std::process::Command::new("cmd")
            .args(["/C", "mklink", "/J", &dst_str, &src_str])
            .output();
        match output {
            Ok(out) => out.status.success(),
            Err(_) => false,
        }
    }

    #[cfg(not(windows))]
    #[allow(dead_code)]
    fn create_junction_for_test(_src: &Path, _dst: &Path) -> bool {
        false
    }

    #[cfg(windows)]
    fn assert_is_reparse_point(path: &Path) {
        use std::os::windows::fs::MetadataExt;
        let md = std::fs::symlink_metadata(path)
            .unwrap_or_else(|e| panic!("cannot stat reparse fixture {}: {}", path.display(), e));
        const REPARSE: u32 = 0x400;
        assert!(
            md.file_attributes() & REPARSE != 0,
            "fixture {} must have FILE_ATTRIBUTE_REPARSE_POINT set (non-vacuous reparse fixture)",
            path.display()
        );
    }

    #[cfg(not(windows))]
    #[allow(dead_code)]
    fn assert_is_reparse_point(_path: &Path) {}

    /// Windows junction at `.openlocus/index`: build must reject before
    /// mutation. Non-vacuous on windows-latest.
    #[cfg(windows)]
    #[test]
    fn b0_windows_build_rejects_junction_at_index_dir() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        std::fs::create_dir_all(state_root.join(".openlocus")).unwrap();
        let outside = tempfile::tempdir().unwrap();
        let junction_path = state_root.join(INDEX_DIR_RELATIVE);
        if !create_junction_for_test(outside.path(), &junction_path) {
            eprintln!("skipping b0 windows junction-at-index test: junction creation unavailable");
            return;
        }
        assert_is_reparse_point(&junction_path);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("reparse point in state artifact path")
                || err.contains("symlink in state artifact path"),
            "got: {}",
            err
        );

        assert!(
            outside
                .path()
                .read_dir()
                .map(|mut r| r.next().is_none())
                .unwrap_or(true),
            "outside target must remain empty after rejection"
        );
        let _ = std::fs::remove_dir(&junction_path);
    }

    /// Windows junction at the Tantivy dir inside an existing real index.
    #[cfg(windows)]
    #[test]
    fn b0_windows_build_rejects_junction_at_tantivy_dir() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        write_source_tree(source_root);

        std::fs::create_dir_all(state_root.join(INDEX_DIR_RELATIVE)).unwrap();
        let outside = tempfile::tempdir().unwrap();
        let junction_path = state_root.join(TANTIVY_DIR_RELATIVE);
        if !create_junction_for_test(outside.path(), &junction_path) {
            eprintln!(
                "skipping b0 windows junction-at-tantivy test: junction creation unavailable"
            );
            return;
        }
        assert_is_reparse_point(&junction_path);

        let policy = Policy::default();
        let records = vec![file_record(source_root, "src/app.rs")];
        let err = build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("reparse point in state artifact path")
                || err.contains("symlink in state artifact path"),
            "got: {}",
            err
        );

        let _ = std::fs::remove_dir(&junction_path);
    }

    /// Windows junction at the traces dir: append_trace_at_roots must
    /// reject. Non-vacuous on windows-latest.
    #[cfg(windows)]
    #[test]
    fn b0_windows_trace_rejects_junction_at_traces_dir() {
        use openlocus_core::{TraceEvent, append_trace_at_roots};
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();

        let sentinel = write_sentinel(state_root, "sentinel.b0", b"state-sentinel\n");

        std::fs::create_dir_all(state_root.join(".openlocus")).unwrap();
        let outside = tempfile::tempdir().unwrap();
        let junction_path = state_root.join(".openlocus/traces");
        if !create_junction_for_test(outside.path(), &junction_path) {
            eprintln!("skipping b0 windows trace-junction test: junction creation unavailable");
            return;
        }
        assert_is_reparse_point(&junction_path);

        let err = append_trace_at_roots(source_root, state_root, &TraceEvent::new("x"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("reparse point in trace artifact path")
                || err.contains("symlink in trace artifact path"),
            "got: {}",
            err
        );

        assert_sentinel_unchanged(&sentinel, b"state-sentinel\n");
        let _ = std::fs::remove_dir(&junction_path);
    }

    /// Windows file symlink at the daily trace file (privilege-permitting).
    #[cfg(windows)]
    #[test]
    fn b0_windows_trace_rejects_file_symlink_at_daily_file() {
        // This test uses the core's append_trace_at_roots which computes
        // the daily filename internally. We don't need to know the exact
        // filename — we place a symlink at the traces DIR level instead
        // (the core's own tests cover the daily-file case on Unix).
        // Here we use a junction at the traces dir (already covered by
        // b0_windows_trace_rejects_junction_at_traces_dir) so this test
        // is a no-op stub on Windows. The core module's
        // append_trace_at_roots_rejects_dangling_symlink_at_final covers
        // the Unix daily-file case.
        eprintln!("covered by b0_windows_trace_rejects_junction_at_traces_dir + core Unix tests");
    }

    // ── B0 Blocker C: exact-kind enforcement before index-artifact mutation ──
    //
    // Adversarial production-chain tests. `preflight_index_artifacts` must
    // require each artifact to be the EXACT expected kind (or absent):
    // `.openlocus/index` / `tantivy`: absent or directory; `manifest.json` /
    // `manifest.json.tmp`: absent or regular file. A wrong-kind artifact is
    // rejected BEFORE any EXISTING index-artifact mutation. Build/purge/
    // update must preserve the preexisting regular Tantivy tree + manifest
    // bytes (full relative-path/kind/file-byte snapshot, excluding timestamps).
    // The malformed setup itself is NOT overwritten by test preparation or
    // by the rejected operation.

    /// Deterministic snapshot entry: a directory or a regular file's bytes.
    /// Timestamps are excluded (bytes compared, not metadata).
    #[derive(Debug, Clone, PartialEq, Eq)]
    enum SnapEntry {
        Dir,
        File(Vec<u8>),
    }

    /// Deterministic snapshot of relative paths, kinds, and file bytes under
    /// `root`. Sorted by relative path so comparisons are order-independent.
    /// Uses `symlink_metadata` so a link is NOT followed (links are out of
    /// scope for these regular-file/dir kind tests). Excludes timestamps.
    fn snapshot_tree(root: &Path) -> Vec<(String, SnapEntry)> {
        let mut out = Vec::new();
        snapshot_tree_into(root, root, &mut out);
        out.sort_by(|a, b| a.0.cmp(&b.0));
        out
    }

    fn snapshot_tree_into(base: &Path, cur: &Path, out: &mut Vec<(String, SnapEntry)>) {
        let rd = match std::fs::read_dir(cur) {
            Ok(rd) => rd,
            Err(_) => return,
        };
        for entry in rd.flatten() {
            let path = entry.path();
            let rel = path
                .strip_prefix(base)
                .unwrap_or(Path::new(""))
                .to_string_lossy()
                .replace('\\', "/");
            let md = match std::fs::symlink_metadata(&path) {
                Ok(md) => md,
                Err(_) => continue,
            };
            if md.is_dir() {
                out.push((rel.clone(), SnapEntry::Dir));
                snapshot_tree_into(base, &path, out);
            } else if md.is_file() {
                out.push((
                    rel,
                    SnapEntry::File(std::fs::read(&path).unwrap_or_default()),
                ));
            }
        }
    }

    /// Build a valid preexisting index at `state_root` from `source_root`
    /// so the preflight has a real Tantivy tree + manifest to preserve.
    fn build_valid_index(source_root: &Path, state_root: &Path) {
        write_source_tree(source_root);
        let policy = Policy::default();
        let records = vec![
            file_record(source_root, "src/app.rs"),
            file_record(source_root, "src/lib.rs"),
        ];
        build_index_at_state_root(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
    }

    /// Table test: `preflight_index_artifacts` rejects each wrong-kind
    /// artifact with a precise error and does NOT overwrite the malformed
    /// setup. Covers index=file, manifest=directory, tmp=directory,
    /// tantivy=file.
    #[test]
    fn preflight_index_artifacts_rejects_wrong_kind_per_artifact_table() {
        fn index_file(root: &Path) {
            let p = root.join(INDEX_DIR_RELATIVE);
            if p.exists() {
                std::fs::remove_dir_all(&p).unwrap();
            }
            if let Some(parent) = p.parent() {
                std::fs::create_dir_all(parent).unwrap();
            }
            std::fs::write(&p, b"index-dir-is-a-file\n").unwrap();
        }
        fn manifest_dir(root: &Path) {
            let p = root.join(MANIFEST_PATH_RELATIVE);
            if p.exists() {
                std::fs::remove_file(&p).unwrap();
            }
            if let Some(parent) = p.parent() {
                std::fs::create_dir_all(parent).unwrap();
            }
            std::fs::create_dir_all(&p).unwrap();
        }
        fn tmp_dir(root: &Path) {
            let p = root.join(path_safety::MANIFEST_TMP_RELATIVE);
            if p.exists() {
                let _ = std::fs::remove_file(&p);
                let _ = std::fs::remove_dir_all(&p);
            }
            if let Some(parent) = p.parent() {
                std::fs::create_dir_all(parent).unwrap();
            }
            std::fs::create_dir_all(&p).unwrap();
        }
        fn tantivy_file(root: &Path) {
            let p = root.join(TANTIVY_DIR_RELATIVE);
            if p.exists() {
                std::fs::remove_dir_all(&p).unwrap();
            }
            if let Some(parent) = p.parent() {
                std::fs::create_dir_all(parent).unwrap();
            }
            std::fs::write(&p, b"tantivy-dir-is-a-file\n").unwrap();
        }

        // (label, setup fn, expected error substring, shape-verify fn)
        struct WrongKindCase {
            label: &'static str,
            setup: fn(&Path),
            expect: &'static str,
            verify: fn(&Path) -> bool,
        }
        let cases: &[WrongKindCase] = &[
            WrongKindCase {
                label: "index=file",
                setup: index_file,
                expect: "index dir is a regular file",
                verify: |p| p.join(INDEX_DIR_RELATIVE).is_file(),
            },
            WrongKindCase {
                label: "manifest=directory",
                setup: manifest_dir,
                expect: "manifest.json is a directory",
                verify: |p| p.join(MANIFEST_PATH_RELATIVE).is_dir(),
            },
            WrongKindCase {
                label: "tmp=directory",
                setup: tmp_dir,
                expect: "manifest.json.tmp is a directory",
                verify: |p| p.join(path_safety::MANIFEST_TMP_RELATIVE).is_dir(),
            },
            WrongKindCase {
                label: "tantivy=file",
                setup: tantivy_file,
                expect: "tantivy dir is a regular file",
                verify: |p| p.join(TANTIVY_DIR_RELATIVE).is_file(),
            },
        ];

        for case in cases {
            let dir = tempfile::tempdir().unwrap();
            let root = dir.path();
            // Establish a real `.openlocus/index` dir as the baseline the
            // malformed shape is introduced into.
            std::fs::create_dir_all(root.join(INDEX_DIR_RELATIVE)).unwrap();
            (case.setup)(root);
            // Confirm the malformed setup took (not overwritten by prep).
            assert!(
                (case.verify)(root),
                "case {}: malformed setup must be present before preflight",
                case.label
            );
            let canonical = path_safety::canonicalize_state_root(root).unwrap();
            let err = path_safety::preflight_index_artifacts(&canonical)
                .unwrap_err()
                .to_string();
            assert!(
                err.contains(case.expect),
                "case {}: expected error containing '{}', got: {}",
                case.label,
                case.expect,
                err
            );
            // Malformed setup preserved (preflight is non-mutating).
            assert!(
                (case.verify)(root),
                "case {}: malformed setup must be preserved after rejected preflight",
                case.label
            );
        }
    }

    /// Build with a directory-shaped `manifest.json` final must reject
    /// BEFORE mutating any existing index artifact, and preserve the
    /// complete preexisting regular Tantivy tree (byte-identical). The
    /// malformed directory-shaped manifest is itself preserved (not
    /// overwritten by the rejected build).
    #[test]
    fn build_rejects_directory_shaped_manifest_final_preserves_tantivy() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        build_valid_index(source_root, state_root);

        // Snapshot preexisting regular Tantivy tree (paths + kinds + bytes).
        let tantivy_root = state_root.join(TANTIVY_DIR_RELATIVE);
        let snap_before = snapshot_tree(&tantivy_root);
        assert!(
            !snap_before.is_empty(),
            "Tantivy tree must be non-empty after a valid build"
        );

        // Introduce malformed: replace manifest.json (regular file) with a
        // directory. The manifest FILE is destroyed by this setup (that is
        // the malformed shape); the Tantivy tree is untouched.
        let manifest_path = state_root.join(MANIFEST_PATH_RELATIVE);
        std::fs::remove_file(&manifest_path).unwrap();
        std::fs::create_dir_all(&manifest_path).unwrap();

        // Attempt build → must reject at the preflight (before mutation).
        let err = build_index_at_state_root(
            source_root,
            state_root,
            &[
                file_record(source_root, "src/app.rs"),
                file_record(source_root, "src/lib.rs"),
            ],
            &Policy::default(),
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(err.contains("manifest.json is a directory"), "got: {}", err);

        // Preexisting Tantivy tree byte-identical (no mutation).
        let snap_after = snapshot_tree(&tantivy_root);
        assert_eq!(
            snap_after, snap_before,
            "preexisting Tantivy tree must be byte-identical after rejected build"
        );
        // Malformed directory-shaped manifest preserved (not overwritten).
        assert!(
            manifest_path.is_dir(),
            "malformed directory-shaped manifest.json must be preserved (not overwritten)"
        );
    }

    /// Build with a directory-shaped `manifest.json.tmp` must reject BEFORE
    /// mutating any existing index artifact, preserve the complete
    /// preexisting regular Tantivy tree AND the preexisting manifest bytes,
    /// and leave the malformed tmp directory in place.
    #[test]
    fn build_rejects_directory_shaped_tmp_preserves_tantivy_and_manifest() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        build_valid_index(source_root, state_root);

        // Snapshot preexisting Tantivy tree + manifest bytes.
        let tantivy_root = state_root.join(TANTIVY_DIR_RELATIVE);
        let snap_tantivy_before = snapshot_tree(&tantivy_root);
        let manifest_path = state_root.join(MANIFEST_PATH_RELATIVE);
        let manifest_bytes_before = std::fs::read(&manifest_path).unwrap();

        // Introduce malformed: directory at manifest.json.tmp.
        let tmp_path = state_root.join(path_safety::MANIFEST_TMP_RELATIVE);
        std::fs::create_dir_all(&tmp_path).unwrap();

        // Attempt build → must reject at the preflight (before mutation).
        let err = build_index_at_state_root(
            source_root,
            state_root,
            &[
                file_record(source_root, "src/app.rs"),
                file_record(source_root, "src/lib.rs"),
            ],
            &Policy::default(),
            ChunkStrategy::LineWindowV1,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("manifest.json.tmp is a directory"),
            "got: {}",
            err
        );

        // Preexisting Tantivy tree byte-identical.
        let snap_tantivy_after = snapshot_tree(&tantivy_root);
        assert_eq!(
            snap_tantivy_after, snap_tantivy_before,
            "preexisting Tantivy tree must be byte-identical after rejected build"
        );
        // Preexisting manifest bytes unchanged.
        let manifest_bytes_after = std::fs::read(&manifest_path).unwrap();
        assert_eq!(
            manifest_bytes_after, manifest_bytes_before,
            "preexisting manifest bytes must be unchanged after rejected build"
        );
        // Malformed tmp directory preserved.
        assert!(
            tmp_path.is_dir(),
            "malformed directory-shaped manifest.json.tmp must be preserved"
        );
    }

    /// Purge with a safe manifest final + a directory-shaped tmp must
    /// delete NOTHING: the whole index tree (Tantivy + manifest + malformed
    /// tmp) is preserved. The preflight aborts ALL deletion.
    #[test]
    fn purge_rejects_directory_shaped_tmp_deletes_nothing_preserves_tree() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        build_valid_index(source_root, state_root);

        // Snapshot the whole index tree before malformed setup.
        let index_root = state_root.join(INDEX_DIR_RELATIVE);
        let snap_before = snapshot_tree(&index_root);

        // Introduce malformed: directory at manifest.json.tmp (safe final).
        let tmp_path = state_root.join(path_safety::MANIFEST_TMP_RELATIVE);
        std::fs::create_dir_all(&tmp_path).unwrap();

        // Attempt purge → must reject at the preflight (before any deletion).
        let err = purge_index_at_state_root(source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("manifest.json.tmp is a directory"),
            "got: {}",
            err
        );

        // Nothing deleted: every preexisting entry still present + byte-identical.
        let snap_after = snapshot_tree(&index_root);
        for (rel, entry) in &snap_before {
            let found = snap_after.iter().find(|(r, _)| r == rel);
            assert!(
                found.is_some(),
                "preexisting entry {} must still exist after rejected purge",
                rel
            );
            assert_eq!(
                found.unwrap().1,
                *entry,
                "preexisting entry {} must be byte-identical after rejected purge",
                rel
            );
        }
        // Tantivy dir + manifest file survive.
        assert!(
            state_root.join(TANTIVY_DIR_RELATIVE).is_dir(),
            "Tantivy dir must survive rejected purge"
        );
        assert!(
            state_root.join(MANIFEST_PATH_RELATIVE).is_file(),
            "manifest file must survive rejected purge"
        );
        // Malformed tmp dir preserved.
        assert!(
            tmp_path.is_dir(),
            "malformed directory-shaped tmp must be preserved (not deleted)"
        );
    }

    /// Purge with a file-shaped Tantivy (regular file where a directory is
    /// expected) must delete NOTHING and preserve the whole tree: the
    /// file-shaped Tantivy, the manifest file (byte-identical), the index
    /// dir, and an absent tmp.
    #[test]
    fn purge_rejects_file_shaped_tantivy_deletes_nothing_preserves_tree() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        build_valid_index(source_root, state_root);

        // Snapshot manifest bytes (Tantivy tree destroyed by malformed setup).
        let manifest_path = state_root.join(MANIFEST_PATH_RELATIVE);
        let manifest_bytes_before = std::fs::read(&manifest_path).unwrap();
        let tantivy_file_bytes = b"tantivy-dir-is-a-file\n".to_vec();

        // Introduce malformed: replace Tantivy DIR with a regular FILE.
        let tantivy_path = state_root.join(TANTIVY_DIR_RELATIVE);
        std::fs::remove_dir_all(&tantivy_path).unwrap();
        std::fs::write(&tantivy_path, &tantivy_file_bytes).unwrap();

        // Attempt purge → must reject at the preflight (before any deletion).
        let err = purge_index_at_state_root(source_root, state_root)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("tantivy dir is a regular file"),
            "got: {}",
            err
        );

        // File-shaped Tantivy preserved (not deleted, not overwritten).
        assert!(
            tantivy_path.is_file(),
            "file-shaped Tantivy must be preserved (not deleted)"
        );
        assert_eq!(
            std::fs::read(&tantivy_path).unwrap(),
            tantivy_file_bytes,
            "file-shaped Tantivy bytes must be unchanged"
        );
        // Manifest file preserved (byte-identical).
        assert!(
            manifest_path.is_file(),
            "manifest file must survive rejected purge"
        );
        assert_eq!(
            std::fs::read(&manifest_path).unwrap(),
            manifest_bytes_before,
            "manifest bytes must be unchanged after rejected purge"
        );
        // Tmp absent (never created).
        assert!(
            !state_root.join(path_safety::MANIFEST_TMP_RELATIVE).exists(),
            "tmp must remain absent"
        );
        // Index dir still exists.
        assert!(
            state_root.join(INDEX_DIR_RELATIVE).is_dir(),
            "index dir must survive rejected purge"
        );
    }

    /// Update with a directory-shaped `manifest.json.tmp` must reject
    /// BEFORE commit and preserve the manifest bytes + the complete Tantivy
    /// tree structure/file bytes. The preflight aborts before the writer is
    /// opened or any commit/manifest-write occurs.
    #[test]
    fn update_rejects_directory_shaped_tmp_before_commit_preserves_manifest_and_tantivy() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        build_valid_index(source_root, state_root);

        // Snapshot manifest bytes + Tantivy tree structure/file bytes.
        let manifest_path = state_root.join(MANIFEST_PATH_RELATIVE);
        let manifest_bytes_before = std::fs::read(&manifest_path).unwrap();
        let tantivy_root = state_root.join(TANTIVY_DIR_RELATIVE);
        let snap_tantivy_before = snapshot_tree(&tantivy_root);

        // Introduce malformed: directory at manifest.json.tmp.
        let tmp_path = state_root.join(path_safety::MANIFEST_TMP_RELATIVE);
        std::fs::create_dir_all(&tmp_path).unwrap();

        // Attempt update (dirty) → must reject at the preflight, BEFORE
        // commit. The preflight uses `?` so this is a hard Err (not an
        // Ok(UpdateResult { success: false }) soft-error).
        let err = update_index_at_state_root(
            source_root,
            state_root,
            &Policy::default(),
            &[
                file_record(source_root, "src/app.rs"),
                file_record(source_root, "src/lib.rs"),
            ],
            true,
            None,
        )
        .unwrap_err()
        .to_string();
        assert!(
            err.contains("manifest.json.tmp is a directory"),
            "got: {}",
            err
        );

        // Manifest bytes unchanged (no commit, no manifest write).
        let manifest_bytes_after = std::fs::read(&manifest_path).unwrap();
        assert_eq!(
            manifest_bytes_after, manifest_bytes_before,
            "manifest bytes must be unchanged after rejected update (before commit)"
        );
        // Tantivy tree structure/file bytes unchanged.
        let snap_tantivy_after = snapshot_tree(&tantivy_root);
        assert_eq!(
            snap_tantivy_after, snap_tantivy_before,
            "Tantivy tree must be byte-identical after rejected update (before commit)"
        );
        // Malformed tmp preserved.
        assert!(
            tmp_path.is_dir(),
            "malformed directory-shaped tmp must be preserved"
        );
    }
}
