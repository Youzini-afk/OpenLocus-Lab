//! B0 filesystem-safety closure for the persistent index state layout.
//!
//! Threat boundary (oracle-approved, quiescent-tree, preexisting-redirection):
//! reject symlinks and — on Windows — every reparse point already present
//! below the selected state-root trust anchor when checked. This is NOT
//! concurrent path-swap resistance, hard-link/bind-mount/network-FS/hostile-OS
//! protection, or an OS sandbox.
//!
//! This module is a narrow internal state-layout safety helper, not a
//! generic public sandbox. It is consumed by [`crate::persistent`] and
//! [`crate::manifest`] (private/raw deletion and atomic writes), and exposes
//! one narrow public checked-trace API used by the CLI. It must not become a
//! broad sandbox API.
//!
//! Design constraints:
//! - Use `std::fs::symlink_metadata` (not `Path::exists` or `metadata`) at
//!   every candidate so a symlink is observable even when its target is
//!   absent. On Windows, additionally reject `FILE_ATTRIBUTE_REPARSE_POINT`
//!   (0x400) via `std::os::windows::fs::MetadataExt::file_attributes()`.
//! - Canonicalize `state_root` itself as the trust anchor (resolves
//!   symlinks above and at the anchor); NEVER follow a descendant artifact
//!   component. Descendants are inspected lexically below the canonical
//!   anchor.
//! - Fail-closed on every metadata/traversal error except a genuine
//!   `io::ErrorKind::NotFound` for an absent suffix component.

use std::io;
use std::path::{Component, Path, PathBuf};

use anyhow::{Context, Result, bail};

use crate::manifest::{INDEX_DIR_RELATIVE, MANIFEST_PATH_RELATIVE, TANTIVY_DIR_RELATIVE};

/// Windows `FILE_ATTRIBUTE_REPARSE_POINT` (0x400). Defined here as a plain
/// `u32` constant so the non-windows path does not need the windows-specific
/// trait import.
#[cfg(windows)]
const FILE_ATTRIBUTE_REPARSE_POINT: u32 = 0x400;

/// Relative path of the manifest tmp file inside the index directory.
/// `manifest.json` with extension replaced by `json.tmp` is `manifest.json.tmp`.
pub(crate) const MANIFEST_TMP_RELATIVE: &str = ".openlocus/index/manifest.json.tmp";

/// What a preflighted artifact path resolves to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum ArtifactKind {
    /// Final component exists as a regular file.
    RegularFile,
    /// Final component exists as a directory.
    Directory,
    /// Final component does not exist (genuinely absent — not a dangling link).
    Absent,
}

/// Classify a single component's metadata: reject symlink/reparse/special-file.
///
/// On Unix, additionally rejects FIFO/socket/block/char devices. On Windows,
/// additionally rejects any file with `FILE_ATTRIBUTE_REPARSE_POINT` set
/// (covers symlinks, junctions, mount points, and other reparse points).
/// Returns `RegularFile`, `Directory`, or errors.
fn classify_metadata(md: &std::fs::Metadata) -> Result<ArtifactKind> {
    let ft = md.file_type();

    // Cross-platform: reject any symlink. On Windows `is_symlink()` is true
    // for symlink files/dirs and junctions (reparse points tagged as
    // symlinks); the explicit reparse attribute check below catches the rest
    // (mount points, dedup, etc.).
    if ft.is_symlink() {
        bail!("symlink in state artifact path is not allowed");
    }

    #[cfg(unix)]
    {
        use std::os::unix::fs::FileTypeExt;
        if ft.is_fifo() || ft.is_socket() || ft.is_block_device() || ft.is_char_device() {
            bail!("special file in state artifact path is not allowed");
        }
    }

    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        let attrs = md.file_attributes();
        if attrs & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
            bail!("reparse point in state artifact path is not allowed");
        }
    }

    if ft.is_dir() {
        Ok(ArtifactKind::Directory)
    } else if ft.is_file() {
        Ok(ArtifactKind::RegularFile)
    } else {
        bail!("unexpected file type in state artifact path");
    }
}

/// `symlink_metadata` at `path`, classifying the result fail-closed.
///
/// Only a definite `io::ErrorKind::NotFound` returns `ArtifactKind::Absent`.
/// Every other error (PermissionDenied, loop, invalid input, etc.) is
/// fail-closed.
fn classify_at(path: &Path) -> Result<ArtifactKind> {
    match path.symlink_metadata() {
        Ok(md) => classify_metadata(&md),
        Err(err) if err.kind() == io::ErrorKind::NotFound => Ok(ArtifactKind::Absent),
        Err(err) => bail!(
            "cannot stat state artifact component {}: {}",
            path.display(),
            err
        ),
    }
}

/// Reject non-`Normal` (and no-op `CurDir`) suffix components. Used when
/// reconstructing a canonical path from an existing ancestor + an unresolved
/// suffix — `ParentDir`, `RootDir`, and `Prefix` would let the suffix escape
/// the canonical ancestor and must be rejected.
fn reject_non_normal_suffix(suffix: &Path) -> Result<()> {
    for component in suffix.components() {
        match component {
            Component::Normal(_) | Component::CurDir => {}
            Component::ParentDir => bail!(
                "state artifact path contains a parent-dir component in unresolved suffix: {}",
                suffix.display()
            ),
            Component::RootDir => bail!(
                "state artifact path contains a root-dir component in unresolved suffix: {}",
                suffix.display()
            ),
            Component::Prefix(_) => bail!(
                "state artifact path contains a prefix component in unresolved suffix: {}",
                suffix.display()
            ),
        }
    }
    Ok(())
}

/// Canonicalize `state_root` as the trust anchor.
///
/// `state_root` itself may be a symlink (it is the user-chosen anchor and
/// canonicalize resolves it once); NO descendant artifact component is
/// followed. If `state_root` does not yet exist, walk up to the nearest
/// existing ancestor (using `symlink_metadata` so dangling links/loops in
/// the ancestor chain reject), canonicalize that, and re-attach the
/// unresolved `Normal` suffix. The suffix is validated to contain only
/// `Normal`/`CurDir` components.
pub(crate) fn canonicalize_state_root(state_root: &Path) -> Result<PathBuf> {
    match state_root.symlink_metadata() {
        Ok(_md) => match state_root.canonicalize() {
            Ok(c) => Ok(c),
            Err(err) if err.kind() == io::ErrorKind::NotFound => bail!(
                "dangling symlink at state root: {}: {}",
                state_root.display(),
                err
            ),
            Err(err) => bail!(
                "cannot canonicalize state root {}: {}",
                state_root.display(),
                err
            ),
        },
        Err(err) if err.kind() == io::ErrorKind::NotFound => {
            // State root is genuinely absent — reconstruct via nearest
            // existing ancestor + validated Normal suffix.
            let mut current = state_root.to_path_buf();
            while let Some(parent) = current.parent() {
                match parent.symlink_metadata() {
                    Ok(_md) => match parent.canonicalize() {
                        Ok(c) => {
                            let suffix = state_root.strip_prefix(parent).unwrap_or(Path::new(""));
                            reject_non_normal_suffix(suffix)?;
                            return Ok(c.join(suffix));
                        }
                        Err(err) if err.kind() == io::ErrorKind::NotFound => bail!(
                            "dangling symlink in state root ancestor chain: {}: {}",
                            parent.display(),
                            err
                        ),
                        Err(err) => bail!(
                            "cannot canonicalize state root ancestor {}: {}",
                            parent.display(),
                            err
                        ),
                    },
                    Err(err) if err.kind() == io::ErrorKind::NotFound => {
                        current = parent.to_path_buf();
                        continue;
                    }
                    Err(err) => bail!(
                        "cannot stat state root ancestor {}: {}",
                        parent.display(),
                        err
                    ),
                }
            }
            bail!(
                "state root does not exist and has no canonicalizable ancestor: {}",
                state_root.display()
            )
        }
        Err(err) => bail!("cannot stat state root {}: {}", state_root.display(), err),
    }
}

/// Ensure `state_root` exists as a real directory trust anchor.
///
/// Walks down from the nearest existing ancestor (canonicalized, with
/// `symlink_metadata` rejection of links/reparse/special-files at every
/// step) and creates missing `Normal` components one-at-a-time, rechecking
/// each after creation. Returns the canonical state_root.
///
/// This is the only function that creates ancestor directories of
/// `state_root`. Descendant artifact directories are created by
/// [`ensure_artifact_dir`].
pub(crate) fn ensure_state_root(state_root: &Path) -> Result<PathBuf> {
    // Fast path: state_root already exists.
    match state_root.symlink_metadata() {
        Ok(md) => {
            // Validate it's a real directory; canonicalize.
            match classify_metadata(&md)? {
                ArtifactKind::Directory => {}
                ArtifactKind::RegularFile => bail!(
                    "state root is a regular file, not a directory: {}",
                    state_root.display()
                ),
                ArtifactKind::Absent => unreachable!("symlink_metadata returned Ok"),
            }
            return state_root.canonicalize().with_context(|| {
                format!("cannot canonicalize state root: {}", state_root.display())
            });
        }
        Err(err) if err.kind() == io::ErrorKind::NotFound => { /* fall through */ }
        Err(err) => bail!("cannot stat state root {}: {}", state_root.display(), err),
    }

    // Reconstruct via nearest existing ancestor + Normal suffix, creating
    // each missing component one-at-a-time.
    let (canonical_ancestor, suffix) = nearest_existing_ancestor(state_root)?;
    reject_non_normal_suffix(&suffix)?;

    let mut current = canonical_ancestor;
    for component in suffix.components() {
        match component {
            Component::Normal(name) => {
                current = current.join(name);
            }
            Component::CurDir => continue,
            _ => unreachable!("reject_non_normal_suffix checked this"),
        }
        match current.symlink_metadata() {
            Ok(md) => match classify_metadata(&md)? {
                ArtifactKind::Directory => { /* already exists, OK */ }
                ArtifactKind::RegularFile => bail!(
                    "state root ancestor is a regular file, not a directory: {}",
                    current.display()
                ),
                ArtifactKind::Absent => unreachable!("symlink_metadata returned Ok"),
            },
            Err(err) if err.kind() == io::ErrorKind::NotFound => {
                std::fs::create_dir(&current).with_context(|| {
                    format!(
                        "failed to create state root component: {}",
                        current.display()
                    )
                })?;
                // Recheck after creation: a race-free quiescent-tree check
                // confirms the just-created directory is a real directory
                // and not (somehow) a link/reparse/special file.
                match current.symlink_metadata() {
                    Ok(md) => match classify_metadata(&md)? {
                        ArtifactKind::Directory => {}
                        _ => bail!(
                            "state root component is not a directory after creation: {}",
                            current.display()
                        ),
                    },
                    Err(err) => bail!(
                        "cannot stat state root component after creation {}: {}",
                        current.display(),
                        err
                    ),
                }
            }
            Err(err) => bail!(
                "cannot stat state root component {}: {}",
                current.display(),
                err
            ),
        }
    }
    current.canonicalize().with_context(|| {
        format!(
            "cannot canonicalize state root after creation: {}",
            state_root.display()
        )
    })
}

/// Walk up from `path` to the nearest existing ancestor. Returns
/// `(canonical_ancestor, suffix)` where `suffix` is the unresolved `Normal`
/// components. Fail-closed: only `NotFound` continues the walk; dangling
/// links/loops at any ancestor reject.
fn nearest_existing_ancestor(path: &Path) -> Result<(PathBuf, PathBuf)> {
    let mut current = path.to_path_buf();
    while let Some(parent) = current.parent() {
        match parent.symlink_metadata() {
            Ok(_md) => match parent.canonicalize() {
                Ok(c) => {
                    let suffix = path
                        .strip_prefix(parent)
                        .unwrap_or(Path::new(""))
                        .to_path_buf();
                    return Ok((c, suffix));
                }
                Err(err) if err.kind() == io::ErrorKind::NotFound => bail!(
                    "dangling symlink in ancestor chain: {}: {}",
                    parent.display(),
                    err
                ),
                Err(err) => bail!("cannot canonicalize ancestor {}: {}", parent.display(), err),
            },
            Err(err) if err.kind() == io::ErrorKind::NotFound => {
                current = parent.to_path_buf();
                continue;
            }
            Err(err) => bail!("cannot stat ancestor {}: {}", parent.display(), err),
        }
    }
    bail!(
        "no existing ancestor found for state path: {}",
        path.display()
    )
}

/// Split `rel` into `Normal` components. Rejects absolute paths, `..`,
/// and Windows prefix components.
fn rel_components(rel: &str) -> Result<Vec<std::ffi::OsString>> {
    let mut out = Vec::new();
    for component in Path::new(rel).components() {
        match component {
            Component::Normal(name) => out.push(name.to_os_string()),
            Component::CurDir => {}
            Component::ParentDir => bail!("parent-dir component in state artifact path: {}", rel),
            Component::RootDir => bail!("root-dir component in state artifact path: {}", rel),
            Component::Prefix(_) => bail!("prefix component in state artifact path: {}", rel),
        }
    }
    Ok(out)
}

/// Preflight an artifact path `state_root/<rel>`, returning the kind of
/// the final component. Walks down from `canonical_state_root` using
/// `symlink_metadata` at every component: rejects symlink/reparse/special-
/// file/non-directory ancestor at every step.
///
/// `state_root` must already be canonicalized (or canonicalizable as a real
/// directory). Use [`canonicalize_state_root`] / [`ensure_state_root`] first.
pub(crate) fn preflight_artifact_at(
    canonical_state_root: &Path,
    rel: &str,
) -> Result<ArtifactKind> {
    let components = rel_components(rel)?;
    let mut current = canonical_state_root.to_path_buf();
    let last_idx = components.len();
    for (i, name) in components.iter().enumerate() {
        current.push(name);
        let kind = classify_at(&current)?;
        match kind {
            ArtifactKind::Absent => {
                if i + 1 < last_idx {
                    // An interior component is absent → all further
                    // components are also absent. Validate by walking the
                    // remaining suffix and confirming they are `Normal`
                    // (already validated by rel_components) and then return
                    // Absent.
                    return Ok(ArtifactKind::Absent);
                } else {
                    return Ok(ArtifactKind::Absent);
                }
            }
            ArtifactKind::RegularFile => {
                if i + 1 < last_idx {
                    bail!(
                        "non-directory component in state artifact path: {}",
                        current.display()
                    );
                }
                return Ok(ArtifactKind::RegularFile);
            }
            ArtifactKind::Directory => {
                if i + 1 == last_idx {
                    return Ok(ArtifactKind::Directory);
                }
                // Continue descending.
            }
        }
    }
    // `rel` was empty → the artifact is the state root itself, which is a
    // directory by construction.
    Ok(ArtifactKind::Directory)
}

/// Recursively preflight an existing artifact subtree top-down.
///
/// Uses `symlink_metadata` before descending into each entry. Rejects any
/// symlink/reparse/special-file and every non-`NotFound` error. The root
/// itself is checked first; if absent, this is a no-op (the subtree does
/// not exist yet — caller may create it via [`ensure_artifact_dir`]).
///
/// A regular-file root is NOT accepted: a subtree preflight expects a
/// directory to recurse into. Callers that need to accept a regular file
/// at this path must use [`preflight_artifact_at`] directly and check the
/// returned kind. This is the generic helper behavior — the canonical
/// all-target preflight [`preflight_index_artifacts`] also enforces the
/// expected kind per-artifact before recursing.
pub(crate) fn preflight_artifact_subtree(canonical_state_root: &Path, rel: &str) -> Result<()> {
    let root_kind = preflight_artifact_at(canonical_state_root, rel)?;
    match root_kind {
        ArtifactKind::Absent => return Ok(()),
        ArtifactKind::RegularFile => bail!(
            "expected a directory for subtree preflight but found a regular file: {}",
            canonical_state_root.join(rel).display()
        ),
        ArtifactKind::Directory => {}
    }
    let mut stack: Vec<PathBuf> = vec![canonical_state_root.join(rel)];
    while let Some(dir) = stack.pop() {
        let entries = match std::fs::read_dir(&dir) {
            Ok(rd) => rd,
            Err(err) if err.kind() == io::ErrorKind::NotFound => continue,
            Err(err) => bail!(
                "cannot read state artifact directory {}: {}",
                dir.display(),
                err
            ),
        };
        for entry in entries {
            let entry = match entry {
                Ok(e) => e,
                Err(err) => bail!(
                    "cannot iterate state artifact directory {}: {}",
                    dir.display(),
                    err
                ),
            };
            let path = entry.path();
            // symlink_metadata on the entry path BEFORE any further
            // traversal. read_dir's entry.file_type() would follow links;
            // we must not.
            let kind = classify_at(&path)?;
            match kind {
                ArtifactKind::RegularFile | ArtifactKind::Directory => {}
                ArtifactKind::Absent => continue,
            }
            if kind == ArtifactKind::Directory {
                stack.push(path);
            }
        }
    }
    Ok(())
}

/// Ensure `state_root/<rel>` exists as a real directory, creating missing
/// components one-at-a-time and rechecking each. Preflights existing
/// components with `symlink_metadata` (rejecting links/reparse/special
/// files/non-directory ancestors).
pub(crate) fn ensure_artifact_dir(canonical_state_root: &Path, rel: &str) -> Result<()> {
    let components = rel_components(rel)?;
    let mut current = canonical_state_root.to_path_buf();
    for name in components {
        current.push(&name);
        match classify_at(&current)? {
            ArtifactKind::Directory => { /* already exists, OK */ }
            ArtifactKind::RegularFile => bail!(
                "state artifact component is a regular file, not a directory: {}",
                current.display()
            ),
            ArtifactKind::Absent => {
                std::fs::create_dir(&current).with_context(|| {
                    format!("failed to create state artifact dir: {}", current.display())
                })?;
                // Recheck after creation.
                match classify_at(&current)? {
                    ArtifactKind::Directory => {}
                    _ => bail!(
                        "state artifact dir is not a directory after creation: {}",
                        current.display()
                    ),
                }
            }
        }
    }
    Ok(())
}

/// Checked atomic write of a regular-file artifact: write to a `.tmp`
/// sibling in the SAME directory (after preflighting the sibling), then
/// recheck the final path, then rename. The tmp sibling name is
/// `<final>.tmp` (i.e., appended; not extension replacement, to avoid
/// surprises with multi-dot filenames like `manifest.json`).
///
/// If the tmp sibling preexisting as a safe regular file, it is removed
/// (never followed) before the write. If the tmp or final path is a
/// link/reparse/special-file/non-regular-file, the operation rejects
/// BEFORE the rename so the existing artifact (if any) is unchanged.
pub(crate) fn checked_write_file_atomic(
    canonical_state_root: &Path,
    rel: &str,
    content: &[u8],
) -> Result<()> {
    // Preflight the full subtree up to the parent directory (reject any
    // link/reparse in ancestors) and ensure the parent dir exists.
    let parent_rel = parent_rel(rel)?;
    ensure_artifact_dir(canonical_state_root, &parent_rel)?;

    let final_path = canonical_state_root.join(rel);
    let tmp_rel = format!("{}.tmp", rel);
    let tmp_path = canonical_state_root.join(&tmp_rel);

    // Recheck final immediately before write: reject links/reparse/special.
    match preflight_artifact_at(canonical_state_root, rel)? {
        ArtifactKind::RegularFile | ArtifactKind::Absent => { /* OK to (over)write */ }
        ArtifactKind::Directory => bail!(
            "cannot write file: target is an existing directory: {}",
            final_path.display()
        ),
    }

    // Tmp sibling: if preexisting as a safe regular file, remove (never
    // follow). If it's a link/reparse/special, reject.
    match preflight_artifact_at(canonical_state_root, &tmp_rel)? {
        ArtifactKind::RegularFile => {
            std::fs::remove_file(&tmp_path).with_context(|| {
                format!(
                    "failed to remove stale safe temp file: {}",
                    tmp_path.display()
                )
            })?;
        }
        ArtifactKind::Absent => {}
        ArtifactKind::Directory => bail!(
            "cannot write temp file: target is an existing directory: {}",
            tmp_path.display()
        ),
    }

    std::fs::write(&tmp_path, content)
        .with_context(|| format!("failed to write temp file: {}", tmp_path.display()))?;

    // Recheck final right before rename: a quiescent-tree recheck ensures
    // the final path has not been swapped to a link/reparse/special-file
    // between the preflight above and the rename.
    match preflight_artifact_at(canonical_state_root, rel)? {
        ArtifactKind::RegularFile | ArtifactKind::Absent => {}
        ArtifactKind::Directory => bail!(
            "final path became a directory between preflight and rename: {}",
            final_path.display()
        ),
    }

    std::fs::rename(&tmp_path, &final_path).with_context(|| {
        format!(
            "failed to rename temp file {} to {}",
            tmp_path.display(),
            final_path.display()
        )
    })?;
    Ok(())
}

fn parent_rel(rel: &str) -> Result<String> {
    let p = Path::new(rel);
    match p.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => {
            Ok(parent.to_string_lossy().replace('\\', "/"))
        }
        _ => Ok(String::new()),
    }
}

/// Full preflight over ALL known persistent-index artifact targets:
/// `.openlocus/index`, `manifest.json`, `manifest.json.tmp`, and the full
/// `tantivy/**` subtree. Rejects any link/reparse/special-file/non-directory
/// ancestor. Does NOT mutate; safe to call before any operation.
///
/// B0 kind enforcement: the canonical all-target preflight requires each
/// artifact to be the EXACT expected kind (or genuinely absent):
/// - `.openlocus/index`: absent or directory (a regular file here is
///   rejected — the index dir must be a directory);
/// - `manifest.json`: absent or regular file (a directory here is
///   rejected);
/// - `manifest.json.tmp`: absent or regular file (a directory here is
///   rejected);
/// - `tantivy`: absent or directory, recursively preflighted when present
///   (a regular file here is rejected — the tantivy dir must be a
///   directory). The recursive [`preflight_artifact_subtree`] also
///   rejects a regular-file root, so a wrong kind cannot slip through the
///   recursion even if a caller invokes the subtree helper directly.
///
/// A wrong-kind artifact is rejected BEFORE any existing index-artifact
/// mutation. Callers that establish a wholly absent state-root trust anchor
/// (via [`ensure_state_root`], which itself creates missing ancestor
/// directories — that IS a filesystem mutation above `.openlocus`) run
/// this full typed preflight before mutating any EXISTING index artifact.
pub(crate) fn preflight_index_artifacts(canonical_state_root: &Path) -> Result<()> {
    // `.openlocus/index`: absent or directory.
    match preflight_artifact_at(canonical_state_root, INDEX_DIR_RELATIVE)? {
        ArtifactKind::Absent | ArtifactKind::Directory => {}
        ArtifactKind::RegularFile => bail!(
            "index dir is a regular file, not a directory: {}",
            canonical_state_root.join(INDEX_DIR_RELATIVE).display()
        ),
    }
    // `manifest.json`: absent or regular file.
    match preflight_artifact_at(canonical_state_root, MANIFEST_PATH_RELATIVE)? {
        ArtifactKind::Absent | ArtifactKind::RegularFile => {}
        ArtifactKind::Directory => bail!(
            "manifest.json is a directory, not a regular file: {}",
            canonical_state_root.join(MANIFEST_PATH_RELATIVE).display()
        ),
    }
    // `manifest.json.tmp`: absent or regular file.
    match preflight_artifact_at(canonical_state_root, MANIFEST_TMP_RELATIVE)? {
        ArtifactKind::Absent | ArtifactKind::RegularFile => {}
        ArtifactKind::Directory => bail!(
            "manifest.json.tmp is a directory, not a regular file: {}",
            canonical_state_root.join(MANIFEST_TMP_RELATIVE).display()
        ),
    }
    // `tantivy`: absent or directory, recursively preflighted when present.
    // The subtree helper also rejects a regular-file root.
    match preflight_artifact_at(canonical_state_root, TANTIVY_DIR_RELATIVE)? {
        ArtifactKind::Absent => {}
        ArtifactKind::Directory => {
            preflight_artifact_subtree(canonical_state_root, TANTIVY_DIR_RELATIVE)?;
        }
        ArtifactKind::RegularFile => bail!(
            "tantivy dir is a regular file, not a directory: {}",
            canonical_state_root.join(TANTIVY_DIR_RELATIVE).display()
        ),
    }
    Ok(())
}

/// Checked existence check: returns `Ok(true)` only when the artifact
/// exists as a safe regular file or directory; `Ok(false)` when genuinely
/// absent. Errors (including unsafe link/reparse paths) propagate.
///
/// Use this in place of `Path::exists()` for safety decisions. Legacy
/// bool-returning public APIs may map errors to `false` for callers that
/// cannot act on errors, but no mutation may rely on that mapping.
pub(crate) fn checked_exists(canonical_state_root: &Path, rel: &str) -> Result<bool> {
    match preflight_artifact_at(canonical_state_root, rel)? {
        ArtifactKind::Absent => Ok(false),
        ArtifactKind::RegularFile | ArtifactKind::Directory => Ok(true),
    }
}

/// Read a checked artifact as a regular file. Rejects unsafe paths.
pub(crate) fn checked_read_file(canonical_state_root: &Path, rel: &str) -> Result<Vec<u8>> {
    match preflight_artifact_at(canonical_state_root, rel)? {
        ArtifactKind::RegularFile => {}
        ArtifactKind::Directory => bail!("cannot read directory as file: {}", rel),
        ArtifactKind::Absent => bail!("artifact file does not exist: {}", rel),
    }
    let path = canonical_state_root.join(rel);
    std::fs::read(&path)
        .with_context(|| format!("failed to read artifact file: {}", path.display()))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rel_components_rejects_parent_dir() {
        assert!(rel_components("../escape").is_err());
    }

    #[test]
    fn rel_components_rejects_absolute() {
        assert!(rel_components("/abs/path").is_err());
    }

    #[test]
    fn rel_components_normal_path_ok() {
        let comps = rel_components(".openlocus/index/tantivy").unwrap();
        assert_eq!(comps.len(), 3);
    }

    #[test]
    fn parent_rel_handles_multi_segment() {
        assert_eq!(parent_rel("a/b/c").unwrap(), "a/b");
        assert_eq!(parent_rel("a").unwrap(), "");
    }
}
