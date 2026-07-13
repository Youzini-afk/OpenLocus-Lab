use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Component, Path, PathBuf};

// ── TraceEvent ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceEvent {
    pub trace_id: String,
    pub timestamp: String,
    pub event: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub input: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub output: Option<serde_json::Value>,
}

impl TraceEvent {
    pub fn new(event: impl Into<String>) -> Self {
        Self {
            trace_id: format!("tr-{}", Utc::now().timestamp_millis()),
            timestamp: Utc::now().to_rfc3339(),
            event: event.into(),
            input: None,
            output: None,
        }
    }

    pub fn with_trace_id(mut self, id: impl Into<String>) -> Self {
        self.trace_id = id.into();
        self
    }

    pub fn with_input(mut self, val: serde_json::Value) -> Self {
        self.input = Some(val);
        self
    }

    pub fn with_output(mut self, val: serde_json::Value) -> Self {
        self.output = Some(val);
        self
    }
}

/// Append a trace event as JSONL under `.openlocus/traces/trajectory-YYYYMMDD.jsonl`.
/// Creates the directory and file if they don't exist.
///
/// B0 safety closure: this is the public legacy single-root entry point.
/// It is now fully checked — it canonicalizes the trust anchor, creates
/// `.openlocus` and `.openlocus/traces` one component at a time (never via
/// `create_dir_all`, which would follow preexisting links), rejects
/// symlinks / Windows reparse points / special files / wrong-kind
/// ancestors, and rechecks the final daily JSONL right before append.
/// There is no unchecked legacy route: this delegates to the same checked
/// single-root implementation as [`append_trace_at_roots`].
pub fn append_trace(root: &Path, event: &TraceEvent) -> anyhow::Result<()> {
    let canonical_state = canonicalize_trace_anchor(root)?;
    append_trace_checked(&canonical_state, event)
}

// ── B0 filesystem-safety closure: checked trace path ───────────────────
//
// Persistent separated CLI commands' best-effort traces live under
// `state_root/.openlocus/traces`, NEVER falling back to source. This
// module adds a narrow source-aware checked trace append/write path that:
// - validates source vs actual trace artifact overlap (when separated),
// - preflights `.openlocus`, `.openlocus/traces`, the final daily JSONL,
//   and (for the direct FastContext trace JSON) the final trace file,
// - rejects links/reparse/special files/non-directory ancestors,
// - creates directories one component at a time (never via
//   `create_dir_all`, which would follow preexisting links),
// - rechecks the final path right before append/write.
//
// Threat boundary: quiescent-tree, preexisting-redirection only. This is
// NOT concurrent path-swap resistance, hard-link/bind-mount/network-FS
// protection, or an OS sandbox.

/// Windows `FILE_ATTRIBUTE_REPARSE_POINT` (0x400).
#[cfg(windows)]
const FILE_ATTRIBUTE_REPARSE_POINT: u32 = 0x400;

/// Artifact kind observed via `symlink_metadata`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TraceArtifactKind {
    RegularFile,
    Directory,
    Absent,
}

/// Classify a single component's metadata: reject symlink/reparse/special-
/// file. Only a definite `io::ErrorKind::NotFound` returns `Absent`.
fn classify_trace_metadata(md: &std::fs::Metadata) -> anyhow::Result<TraceArtifactKind> {
    let ft = md.file_type();
    if ft.is_symlink() {
        anyhow::bail!("symlink in trace artifact path is not allowed");
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::FileTypeExt;
        if ft.is_fifo() || ft.is_socket() || ft.is_block_device() || ft.is_char_device() {
            anyhow::bail!("special file in trace artifact path is not allowed");
        }
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        let attrs = md.file_attributes();
        if attrs & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
            anyhow::bail!("reparse point in trace artifact path is not allowed");
        }
    }
    if ft.is_dir() {
        Ok(TraceArtifactKind::Directory)
    } else if ft.is_file() {
        Ok(TraceArtifactKind::RegularFile)
    } else {
        anyhow::bail!("unexpected file type in trace artifact path");
    }
}

fn classify_trace_at(path: &Path) -> anyhow::Result<TraceArtifactKind> {
    use std::io;
    match path.symlink_metadata() {
        Ok(md) => classify_trace_metadata(&md),
        Err(err) if err.kind() == io::ErrorKind::NotFound => Ok(TraceArtifactKind::Absent),
        Err(err) => anyhow::bail!(
            "cannot stat trace artifact component {}: {}",
            path.display(),
            err
        ),
    }
}

/// Reject non-`Normal` suffix components when reconstructing a canonical
/// path from an existing ancestor + an unresolved suffix.
fn reject_non_normal_suffix(suffix: &Path) -> anyhow::Result<()> {
    for component in suffix.components() {
        match component {
            Component::Normal(_) | Component::CurDir => {}
            Component::ParentDir => anyhow::bail!(
                "trace artifact path contains a parent-dir component in unresolved suffix: {}",
                suffix.display()
            ),
            Component::RootDir => anyhow::bail!(
                "trace artifact path contains a root-dir component in unresolved suffix: {}",
                suffix.display()
            ),
            Component::Prefix(_) => anyhow::bail!(
                "trace artifact path contains a prefix component in unresolved suffix: {}",
                suffix.display()
            ),
        }
    }
    Ok(())
}

/// Resolve `path` to a canonical path WITHOUT following descendant
/// components beyond what already exists. Walks up to nearest existing
/// ancestor (using `symlink_metadata` so dangling links/loops in the
/// ancestor chain reject), canonicalizes that ancestor, and re-attaches
/// the validated `Normal` suffix. Returns the empty path if no canonical
/// ancestor exists below the trust anchor (used by overlap validation).
fn resolve_trace_canonical(path: &Path) -> anyhow::Result<PathBuf> {
    use std::io;
    match path.symlink_metadata() {
        Ok(_md) => match path.canonicalize() {
            Ok(c) => Ok(c),
            Err(err) if err.kind() == io::ErrorKind::NotFound => anyhow::bail!(
                "dangling symlink at trace artifact path: {}: {}",
                path.display(),
                err
            ),
            Err(err) => anyhow::bail!(
                "cannot canonicalize trace artifact path: {}: {}",
                path.display(),
                err
            ),
        },
        Err(err) if err.kind() == io::ErrorKind::NotFound => {
            let mut current = path.to_path_buf();
            while let Some(parent) = current.parent() {
                match parent.symlink_metadata() {
                    Ok(_md) => match parent.canonicalize() {
                        Ok(c) => {
                            let suffix = path.strip_prefix(parent).unwrap_or(Path::new(""));
                            reject_non_normal_suffix(suffix)?;
                            return Ok(c.join(suffix));
                        }
                        Err(err) if err.kind() == io::ErrorKind::NotFound => anyhow::bail!(
                            "dangling symlink in trace artifact ancestor chain: {}: {}",
                            parent.display(),
                            err
                        ),
                        Err(err) => anyhow::bail!(
                            "cannot canonicalize trace artifact ancestor: {}: {}",
                            parent.display(),
                            err
                        ),
                    },
                    Err(err) if err.kind() == io::ErrorKind::NotFound => {
                        current = parent.to_path_buf();
                        continue;
                    }
                    Err(err) => anyhow::bail!(
                        "cannot stat trace artifact ancestor: {}: {}",
                        parent.display(),
                        err
                    ),
                }
            }
            Ok(PathBuf::new())
        }
        Err(err) => anyhow::bail!(
            "cannot stat trace artifact path: {}: {}",
            path.display(),
            err
        ),
    }
}

/// Canonicalize `root` as a trust anchor (resolves `root` itself once;
/// does not follow descendant components). Bails if `root` does not exist
/// or is unsafe.
fn canonicalize_trace_anchor(root: &Path) -> anyhow::Result<PathBuf> {
    use std::io;
    match root.symlink_metadata() {
        Ok(md) => {
            classify_trace_metadata(&md)?;
            root.canonicalize().map_err(|err| {
                anyhow::anyhow!(
                    "cannot canonicalize trace anchor: {}: {}",
                    root.display(),
                    err
                )
            })
        }
        Err(err) if err.kind() == io::ErrorKind::NotFound => {
            anyhow::bail!("trace anchor does not exist: {}", root.display())
        }
        Err(err) => anyhow::bail!("cannot stat trace anchor {}: {}", root.display(), err),
    }
}

/// Validate source-vs-actual-trace-artifact overlap. Compares canonical
/// source root against canonical actual trace subtree
/// `state_root/.openlocus/traces`. Reject when the trace subtree equals,
/// is-below, or contains the source root. Source under `state_root` but
/// outside `.openlocus/traces` is allowed.
fn validate_trace_overlap(
    canonical_source_root: &Path,
    canonical_state_root: &Path,
) -> anyhow::Result<()> {
    let trace_path = canonical_state_root.join(".openlocus/traces");
    let canonical_trace = resolve_trace_canonical(&trace_path)?;
    if canonical_trace.as_os_str().is_empty() {
        return Ok(());
    }
    if canonical_trace == *canonical_source_root
        || canonical_trace.starts_with(canonical_source_root)
        || canonical_source_root.starts_with(&canonical_trace)
    {
        anyhow::bail!(
            "trace artifact subtree overlaps source root; use colocated mode or a state root whose .openlocus/traces is disjoint from the source: trace={}, source={}",
            canonical_trace.display(),
            canonical_source_root.display()
        );
    }
    Ok(())
}

/// Ensure `canonical_root/<rel>` exists as a real directory, creating
/// missing `Normal` components one-at-a-time and rechecking each. Rejects
/// preexisting links/reparse/special-files/non-directory ancestors.
fn ensure_trace_dir(canonical_root: &Path, rel: &str) -> anyhow::Result<()> {
    let mut current = canonical_root.to_path_buf();
    for component in Path::new(rel).components() {
        match component {
            Component::Normal(name) => current.push(name),
            Component::CurDir => continue,
            _ => anyhow::bail!("invalid component in trace artifact path: {}", rel),
        }
        match classify_trace_at(&current)? {
            TraceArtifactKind::Directory => { /* OK */ }
            TraceArtifactKind::RegularFile => anyhow::bail!(
                "trace artifact component is a regular file, not a directory: {}",
                current.display()
            ),
            TraceArtifactKind::Absent => {
                fs::create_dir(&current).map_err(|err| {
                    anyhow::anyhow!("failed to create trace dir {}: {}", current.display(), err)
                })?;
                match classify_trace_at(&current)? {
                    TraceArtifactKind::Directory => {}
                    _ => anyhow::bail!(
                        "trace dir is not a directory after creation: {}",
                        current.display()
                    ),
                }
            }
        }
    }
    Ok(())
}

/// Preflight a single artifact path `canonical_root/<rel>`, returning the
/// kind of the final component. Rejects links/reparse/special-files/non-
/// directory ancestors.
fn preflight_trace_at(canonical_root: &Path, rel: &str) -> anyhow::Result<TraceArtifactKind> {
    let mut current = canonical_root.to_path_buf();
    let components: Vec<Component<'_>> = Path::new(rel).components().collect();
    let last_idx = components.len();
    for (i, component) in components.iter().enumerate() {
        match component {
            Component::Normal(name) => current.push(name),
            Component::CurDir => continue,
            _ => anyhow::bail!("invalid component in trace artifact path: {}", rel),
        }
        let kind = classify_trace_at(&current)?;
        match kind {
            TraceArtifactKind::Absent => return Ok(TraceArtifactKind::Absent),
            TraceArtifactKind::RegularFile => {
                if i + 1 < last_idx {
                    anyhow::bail!(
                        "non-directory component in trace artifact path: {}",
                        current.display()
                    );
                }
                return Ok(TraceArtifactKind::RegularFile);
            }
            TraceArtifactKind::Directory => {
                if i + 1 == last_idx {
                    return Ok(TraceArtifactKind::Directory);
                }
            }
        }
    }
    Ok(TraceArtifactKind::Directory)
}

/// Checked single-root append of a trace event under
/// `canonical_state/.openlocus/traces/trajectory-YYYYMMDD.jsonl`.
///
/// The single shared checked implementation used by both the public legacy
/// [`append_trace`] and [`append_trace_at_roots`]. The caller is
/// responsible for canonicalizing the trust anchor (and, in separated
/// mode, validating source-vs-state overlap) before calling this.
///
/// Performs the full B0 mutation gate:
/// - component-by-component directory creation for `.openlocus` and
///   `.openlocus/traces` (rejects preexisting links/reparse/special-files/
///   wrong-kind ancestors at every step, rechecks each created component),
/// - preflight of the final daily JSONL (rejects symlink/reparse/special-
///   file/directory-at-final-position),
/// - final recheck right before `OpenOptions::open`.
///
/// Threat boundary: quiescent-tree, preexisting-redirection only.
fn append_trace_checked(canonical_state: &Path, event: &TraceEvent) -> anyhow::Result<()> {
    ensure_trace_dir(canonical_state, ".openlocus")?;
    ensure_trace_dir(canonical_state, ".openlocus/traces")?;

    let date_str = Utc::now().format("%Y%m%d").to_string();
    let filename = format!("trajectory-{}.jsonl", date_str);
    let rel = format!(".openlocus/traces/{}", filename);

    match preflight_trace_at(canonical_state, &rel)? {
        TraceArtifactKind::RegularFile | TraceArtifactKind::Absent => {}
        TraceArtifactKind::Directory => anyhow::bail!(
            "trace daily file is a directory, not a regular file: {}",
            rel
        ),
    }

    let path = canonical_state.join(&rel);
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .map_err(|err| anyhow::anyhow!("failed to open trace file {}: {}", path.display(), err))?;
    let line = serde_json::to_string(event)?;
    writeln!(file, "{}", line)?;
    Ok(())
}

/// Checked append of a trace event under
/// `state_root/.openlocus/traces/trajectory-YYYYMMDD.jsonl`.
///
/// In separated mode (`source_root` lexically distinct from `state_root`),
/// validates source-vs-actual-trace-artifact overlap, then routes through
/// the same checked single-root implementation as the public legacy
/// [`append_trace`] (no recursion, no unchecked fallback).
///
/// In colocated mode (`source_root == state_root` lexically) the
/// source-vs-state overlap validation is skipped (it is trivially
/// satisfied), but the same checked implementation still runs: canonical
/// anchor, component-by-component directory creation, preexisting
/// symlink/Windows reparse/special/wrong-kind rejection, and final
/// daily-file recheck.
///
/// Returns an error on any unsafe path; callers that want best-effort
/// behavior must handle errors themselves (the CLI warns once and skips).
pub fn append_trace_at_roots(
    source_root: &Path,
    state_root: &Path,
    event: &TraceEvent,
) -> anyhow::Result<()> {
    // Colocated fast path: identical lexical paths never need separation.
    // Skip overlap validation only; the checked single-root implementation
    // still runs the full mutation gate (anchor, dir creation, preflight,
    // final recheck).
    if source_root == state_root {
        let canonical_state = canonicalize_trace_anchor(state_root)?;
        return append_trace_checked(&canonical_state, event);
    }

    let canonical_source = source_root.canonicalize().map_err(|err| {
        anyhow::anyhow!(
            "cannot canonicalize trace source root {}: {}",
            source_root.display(),
            err
        )
    })?;
    let canonical_state = canonicalize_trace_anchor(state_root)?;
    validate_trace_overlap(&canonical_source, &canonical_state)?;

    // Same checked implementation; no recursion into append_trace.
    append_trace_checked(&canonical_state, event)
}

/// Checked write of a direct FastContext trace JSON file under
/// `state_root/.openlocus/traces/fast-context-<trace_id>.json`. Single
/// caller-supplied root (colocated): no overlap check is needed because
/// the root is the same for source and state. Creates directories one
/// component at a time; rejects preexisting links/reparse/special-files.
/// Rechecks the final file right before write.
pub fn write_fast_context_trace_at_roots(
    state_root: &Path,
    trace_id: &str,
    data: &serde_json::Value,
) -> anyhow::Result<()> {
    let canonical_state = canonicalize_trace_anchor(state_root)?;
    ensure_trace_dir(&canonical_state, ".openlocus")?;
    ensure_trace_dir(&canonical_state, ".openlocus/traces")?;

    let filename = format!("fast-context-{}.json", trace_id);
    let rel = format!(".openlocus/traces/{}", filename);

    match preflight_trace_at(&canonical_state, &rel)? {
        TraceArtifactKind::RegularFile | TraceArtifactKind::Absent => {}
        TraceArtifactKind::Directory => anyhow::bail!(
            "fast-context trace file is a directory, not a regular file: {}",
            rel
        ),
    }

    let content = serde_json::to_string_pretty(data)?;
    let path = canonical_state.join(&rel);
    fs::write(&path, content)
        .map_err(|err| anyhow::anyhow!("failed to write trace file {}: {}", path.display(), err))?;
    Ok(())
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trace_event_serializes() {
        let ev = TraceEvent::new("retrieval_call")
            .with_input(serde_json::json!({"query": "auth"}))
            .with_output(serde_json::json!({"count": 3}));
        let json = serde_json::to_string(&ev).unwrap();
        assert!(json.contains("retrieval_call"));
        assert!(json.contains("auth"));
    }

    #[test]
    fn append_trace_creates_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let ev = TraceEvent::new("test_event");
        append_trace(root, &ev).unwrap();

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let trace_file = root
            .join(".openlocus")
            .join("traces")
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(trace_file.exists());

        let content = fs::read_to_string(&trace_file).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(content.trim()).unwrap();
        assert_eq!(parsed["event"], "test_event");
    }

    // ── B0 filesystem-safety closure: checked trace path ───────────────

    #[cfg(unix)]
    fn symlink_dir(src: &Path, dst: &Path) -> std::io::Result<()> {
        std::os::unix::fs::symlink(src, dst)
    }

    #[cfg(unix)]
    fn symlink_file(src: &Path, dst: &Path) -> std::io::Result<()> {
        std::os::unix::fs::symlink(src, dst)
    }

    #[cfg(windows)]
    fn symlink_file(src: &Path, dst: &Path) -> std::io::Result<()> {
        std::os::windows::fs::symlink_file(src, dst)
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

    #[cfg(unix)]
    fn create_symlink_dir_for_test(src: &Path, dst: &Path) -> bool {
        match symlink_dir(src, dst) {
            Ok(()) => true,
            Err(err) if symlink_unavailable_for_test(&err) => false,
            Err(err) => panic!("failed to create symlink dir test fixture: {err}"),
        }
    }

    #[cfg(not(unix))]
    fn create_symlink_dir_for_test(_src: &Path, _dst: &Path) -> bool {
        false
    }

    #[test]
    fn append_trace_at_roots_colocated_matches_legacy() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let ev = TraceEvent::new("colocated_event");
        append_trace_at_roots(root, root, &ev).unwrap();

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let trace_file = root
            .join(".openlocus")
            .join("traces")
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(trace_file.exists());
        let content = fs::read_to_string(&trace_file).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(content.trim()).unwrap();
        assert_eq!(parsed["event"], "colocated_event");
    }

    #[test]
    fn append_trace_at_roots_separated_writes_to_state_only() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();
        let ev = TraceEvent::new("separated_event");
        append_trace_at_roots(source_root, state_root, &ev).unwrap();

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let trace_file = state_root
            .join(".openlocus")
            .join("traces")
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(trace_file.exists());
        assert!(
            !source_root.join(".openlocus").exists(),
            "source root must not have .openlocus created in separated trace mode"
        );

        let content = fs::read_to_string(&trace_file).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(content.trim()).unwrap();
        assert_eq!(parsed["event"], "separated_event");
    }

    #[test]
    fn append_trace_at_roots_rejects_dangling_symlink_at_final() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();

        let sentinel_path = state_root.join("sentinel.txt");
        let sentinel_bytes = b"sentinel bytes must remain\n";
        fs::write(&sentinel_path, sentinel_bytes).unwrap();

        fs::create_dir_all(state_root.join(".openlocus/traces")).unwrap();
        let date_str = Utc::now().format("%Y%m%d").to_string();
        let final_rel = format!("trajectory-{}.jsonl", date_str);
        let final_path = state_root.join(".openlocus/traces").join(&final_rel);
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-trace-target-for-openlocus-test"),
            &final_path,
        ) {
            eprintln!(
                "skipping dangling-symlink-at-trace-final test: symlinks unavailable on this host"
            );
            return;
        }

        let err = append_trace_at_roots(source_root, state_root, &TraceEvent::new("x"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("dangling symlink at trace artifact path")
                || err.contains("symlink in trace artifact path")
                || err.contains("reparse point in trace artifact path"),
            "got: {}",
            err
        );

        let after = fs::read(&sentinel_path).unwrap();
        assert_eq!(
            after.as_slice(),
            sentinel_bytes,
            "sentinel must remain untouched when trace validation rejects"
        );
    }

    #[test]
    fn append_trace_at_roots_rejects_dangling_symlink_at_traces_dir() {
        let src_dir = tempfile::tempdir().unwrap();
        let state_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let state_root = state_dir.path();

        let sentinel_path = state_root.join("sentinel.txt");
        let sentinel_bytes = b"sentinel bytes must remain\n";
        fs::write(&sentinel_path, sentinel_bytes).unwrap();

        fs::create_dir_all(state_root.join(".openlocus")).unwrap();
        let traces_link = state_root.join(".openlocus/traces");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-traces-target-for-openlocus-test"),
            &traces_link,
        ) {
            eprintln!(
                "skipping dangling-symlink-traces-dir test: symlinks unavailable on this host"
            );
            return;
        }

        let err = append_trace_at_roots(source_root, state_root, &TraceEvent::new("x"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("dangling symlink at trace artifact path")
                || err.contains("cannot stat trace artifact component")
                || err.contains("cannot canonicalize trace artifact path"),
            "got: {}",
            err
        );

        let after = fs::read(&sentinel_path).unwrap();
        assert_eq!(
            after.as_slice(),
            sentinel_bytes,
            "sentinel must remain untouched when trace validation rejects"
        );
    }

    #[test]
    fn append_trace_at_roots_rejects_trace_overlap_with_source() {
        let src_dir = tempfile::tempdir().unwrap();
        let source_root = src_dir.path();
        let link_parent = tempfile::tempdir().unwrap();
        let state_link = link_parent.path().join("state-alias");
        if !create_symlink_dir_for_test(source_root, &state_link) {
            eprintln!("skipping trace overlap test: symlinks unavailable on this host");
            return;
        }
        let err = append_trace_at_roots(source_root, &state_link, &TraceEvent::new("x"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("trace artifact subtree overlaps source root")
                || err.contains("symlink in trace artifact path")
                || err.contains("reparse point in trace artifact path"),
            "got: {}",
            err
        );
    }

    #[test]
    fn write_fast_context_trace_at_roots_writes_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let data = serde_json::json!({"trace_id": "abc", "event": "fast_context"});
        write_fast_context_trace_at_roots(root, "abc", &data).unwrap();

        let trace_file = root
            .join(".openlocus")
            .join("traces")
            .join("fast-context-abc.json");
        assert!(trace_file.exists());
        let content = fs::read_to_string(&trace_file).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(content.trim()).unwrap();
        assert_eq!(parsed["trace_id"], "abc");
    }

    #[test]
    fn write_fast_context_trace_at_roots_rejects_dangling_symlink_at_final() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let sentinel_path = root.join("sentinel.txt");
        let sentinel_bytes = b"sentinel bytes must remain\n";
        fs::write(&sentinel_path, sentinel_bytes).unwrap();

        fs::create_dir_all(root.join(".openlocus/traces")).unwrap();
        let final_path = root.join(".openlocus/traces").join("fast-context-zzz.json");
        if !create_symlink_file_for_test(
            Path::new("/nonexistent-fastcontext-target-for-openlocus-test"),
            &final_path,
        ) {
            eprintln!(
                "skipping fastcontext dangling-symlink test: symlinks unavailable on this host"
            );
            return;
        }

        let err = write_fast_context_trace_at_roots(root, "zzz", &serde_json::json!({}))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("dangling symlink at trace artifact path")
                || err.contains("symlink in trace artifact path")
                || err.contains("reparse point in trace artifact path"),
            "got: {}",
            err
        );
        let after = fs::read(&sentinel_path).unwrap();
        assert_eq!(after.as_slice(), sentinel_bytes);
    }

    // ── B0: direct production tests for the checked legacy/equal-root path ──
    //
    // The public legacy `append_trace(root, event)` and the equal-root
    // (`source_root == state_root`) branch of `append_trace_at_roots` MUST
    // route through the same checked single-root implementation. These
    // tests prove: (a) a linked traces dir and a linked daily file are
    // rejected before any mutation, and the symlink TARGET is not mutated;
    // (b) safe legacy append still succeeds. Linux symlink fixtures are
    // non-vacuous; Windows junction/reparse fixtures run where the
    // package-test matrix supports `mklink /J`.

    /// Safe legacy `append_trace` on a clean tree succeeds and writes the
    /// event. This is the positive counterpart to the rejection tests
    /// below — it confirms the checked path does not over-reject.
    #[test]
    fn append_trace_legacy_safe_succeeds_writes_event() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let ev = TraceEvent::new("legacy_safe_event");
        append_trace(root, &ev).unwrap();

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let trace_file = root
            .join(".openlocus")
            .join("traces")
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(trace_file.exists());
        let content = fs::read_to_string(&trace_file).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(content.trim()).unwrap();
        assert_eq!(parsed["event"], "legacy_safe_event");
    }

    /// Legacy `append_trace` rejects a symlinked traces dir and does NOT
    /// mutate the symlink target. Non-vacuous on Unix (real dir symlink).
    #[test]
    fn append_trace_legacy_rejects_symlinked_traces_dir_without_target_mutation() {
        let state_dir = tempfile::tempdir().unwrap();
        let root = state_dir.path();

        // Real outside target dir with a sentinel file inside it.
        let outside = tempfile::tempdir().unwrap();
        let outside_sentinel = outside.path().join("outside-sentinel.txt");
        let sentinel_bytes = b"outside target must remain untouched\n";
        fs::write(&outside_sentinel, sentinel_bytes).unwrap();

        fs::create_dir_all(root.join(".openlocus")).unwrap();
        let traces_link = root.join(".openlocus/traces");
        if !create_symlink_dir_for_test(outside.path(), &traces_link) {
            eprintln!(
                "skipping legacy symlinked-traces-dir test: dir symlinks unavailable on this host"
            );
            return;
        }

        let err = append_trace(root, &TraceEvent::new("must_not_write"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("symlink in trace artifact path")
                || err.contains("reparse point in trace artifact path"),
            "got: {}",
            err
        );

        // Target dir must NOT have a trajectory file written through the symlink.
        let date_str = Utc::now().format("%Y%m%d").to_string();
        let leaked = outside
            .path()
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(
            !leaked.exists(),
            "symlink target must not be mutated through the rejected traces-dir symlink"
        );
        // Sentinel inside the target dir unchanged.
        assert_eq!(
            fs::read(&outside_sentinel).unwrap().as_slice(),
            sentinel_bytes,
            "target dir contents must remain untouched"
        );
        // The symlink itself must remain (no raw create_dir_all overwrite).
        assert!(
            traces_link.symlink_metadata().is_ok(),
            "traces-dir symlink must still exist (no raw overwrite)"
        );
    }

    /// Legacy `append_trace` rejects a symlinked daily file and does NOT
    /// mutate (append to) the symlink target.
    #[test]
    fn append_trace_legacy_rejects_symlinked_daily_file_without_target_mutation() {
        let state_dir = tempfile::tempdir().unwrap();
        let root = state_dir.path();

        // Real outside target file with sentinel bytes.
        let outside = tempfile::tempdir().unwrap();
        let outside_target = outside.path().join("outside-target.jsonl");
        let sentinel_bytes = b"outside target file must remain untouched\n";
        fs::write(&outside_target, sentinel_bytes).unwrap();

        fs::create_dir_all(root.join(".openlocus/traces")).unwrap();
        let date_str = Utc::now().format("%Y%m%d").to_string();
        let daily_link = root
            .join(".openlocus")
            .join("traces")
            .join(format!("trajectory-{}.jsonl", date_str));
        if !create_symlink_file_for_test(&outside_target, &daily_link) {
            eprintln!(
                "skipping legacy symlinked-daily-file test: symlinks unavailable on this host"
            );
            return;
        }

        let err = append_trace(root, &TraceEvent::new("must_not_append"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("symlink in trace artifact path")
                || err.contains("reparse point in trace artifact path"),
            "got: {}",
            err
        );

        // Target file content unchanged — no append through the symlink.
        assert_eq!(
            fs::read(&outside_target).unwrap().as_slice(),
            sentinel_bytes,
            "symlink target file must not be appended to through the rejected daily-file symlink"
        );
        // The symlink itself must remain.
        assert!(
            daily_link.symlink_metadata().is_ok(),
            "daily-file symlink must still exist (no raw overwrite)"
        );
    }

    /// Equal-root `append_trace_at_roots(root, root, ...)` rejects a
    /// symlinked traces dir and does NOT mutate the symlink target. This
    /// proves the colocated branch runs the full checked gate (not an
    /// unchecked legacy fallback).
    #[test]
    fn append_trace_at_roots_colocated_rejects_symlinked_traces_dir_without_target_mutation() {
        let state_dir = tempfile::tempdir().unwrap();
        let root = state_dir.path();

        let outside = tempfile::tempdir().unwrap();
        let outside_sentinel = outside.path().join("outside-sentinel.txt");
        let sentinel_bytes = b"outside target must remain untouched\n";
        fs::write(&outside_sentinel, sentinel_bytes).unwrap();

        fs::create_dir_all(root.join(".openlocus")).unwrap();
        let traces_link = root.join(".openlocus/traces");
        if !create_symlink_dir_for_test(outside.path(), &traces_link) {
            eprintln!(
                "skipping colocated symlinked-traces-dir test: dir symlinks unavailable on this host"
            );
            return;
        }

        let err = append_trace_at_roots(root, root, &TraceEvent::new("must_not_write"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("symlink in trace artifact path")
                || err.contains("reparse point in trace artifact path"),
            "got: {}",
            err
        );

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let leaked = outside
            .path()
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(
            !leaked.exists(),
            "symlink target must not be mutated through the rejected traces-dir symlink"
        );
        assert_eq!(
            fs::read(&outside_sentinel).unwrap().as_slice(),
            sentinel_bytes,
            "target dir contents must remain untouched"
        );
        assert!(
            traces_link.symlink_metadata().is_ok(),
            "traces-dir symlink must still exist (no raw overwrite)"
        );
    }

    /// Equal-root `append_trace_at_roots(root, root, ...)` rejects a
    /// symlinked daily file and does NOT mutate the symlink target.
    #[test]
    fn append_trace_at_roots_colocated_rejects_symlinked_daily_file_without_target_mutation() {
        let state_dir = tempfile::tempdir().unwrap();
        let root = state_dir.path();

        let outside = tempfile::tempdir().unwrap();
        let outside_target = outside.path().join("outside-target.jsonl");
        let sentinel_bytes = b"outside target file must remain untouched\n";
        fs::write(&outside_target, sentinel_bytes).unwrap();

        fs::create_dir_all(root.join(".openlocus/traces")).unwrap();
        let date_str = Utc::now().format("%Y%m%d").to_string();
        let daily_link = root
            .join(".openlocus")
            .join("traces")
            .join(format!("trajectory-{}.jsonl", date_str));
        if !create_symlink_file_for_test(&outside_target, &daily_link) {
            eprintln!(
                "skipping colocated symlinked-daily-file test: symlinks unavailable on this host"
            );
            return;
        }

        let err = append_trace_at_roots(root, root, &TraceEvent::new("must_not_append"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("symlink in trace artifact path")
                || err.contains("reparse point in trace artifact path"),
            "got: {}",
            err
        );

        assert_eq!(
            fs::read(&outside_target).unwrap().as_slice(),
            sentinel_bytes,
            "symlink target file must not be appended to through the rejected daily-file symlink"
        );
        assert!(
            daily_link.symlink_metadata().is_ok(),
            "daily-file symlink must still exist (no raw overwrite)"
        );
    }

    // ── Windows junction/reparse-point fixtures ───────────────────────
    //
    // On Windows, junctions are reparse points created via `cmd /C mklink /J`
    // that do NOT require SeCreateSymbolicLinkPrivilege. These fixtures are
    // non-vacuous on windows-latest and are routed by the existing
    // package-test matrix (no extra privileges required).

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

    /// Windows junction at the traces dir: legacy `append_trace` must
    /// reject the reparse point and not mutate the junction target.
    #[cfg(windows)]
    #[test]
    fn append_trace_legacy_rejects_windows_junction_traces_dir_without_target_mutation() {
        let state_dir = tempfile::tempdir().unwrap();
        let root = state_dir.path();

        let outside = tempfile::tempdir().unwrap();
        let outside_sentinel = outside.path().join("outside-sentinel.txt");
        let sentinel_bytes = b"outside target must remain untouched\n";
        fs::write(&outside_sentinel, sentinel_bytes).unwrap();

        std::fs::create_dir_all(root.join(".openlocus")).unwrap();
        let junction_path = root.join(".openlocus/traces");
        if !create_junction_for_test(outside.path(), &junction_path) {
            eprintln!("skipping legacy windows junction-at-traces-dir test: mklink /J unavailable");
            return;
        }

        let err = append_trace(root, &TraceEvent::new("must_not_write"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("reparse point in trace artifact path")
                || err.contains("symlink in trace artifact path"),
            "got: {}",
            err
        );

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let leaked = outside
            .path()
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(
            !leaked.exists(),
            "junction target must not be mutated through the rejected traces-dir junction"
        );
        assert_eq!(
            fs::read(&outside_sentinel).unwrap().as_slice(),
            sentinel_bytes,
            "target dir contents must remain untouched"
        );
        let _ = std::fs::remove_dir(&junction_path);
    }

    /// Windows junction at the traces dir: equal-root `append_trace_at_roots`
    /// must reject the reparse point and not mutate the junction target.
    #[cfg(windows)]
    #[test]
    fn append_trace_at_roots_colocated_rejects_windows_junction_traces_dir_without_target_mutation()
    {
        let state_dir = tempfile::tempdir().unwrap();
        let root = state_dir.path();

        let outside = tempfile::tempdir().unwrap();
        let outside_sentinel = outside.path().join("outside-sentinel.txt");
        let sentinel_bytes = b"outside target must remain untouched\n";
        fs::write(&outside_sentinel, sentinel_bytes).unwrap();

        std::fs::create_dir_all(root.join(".openlocus")).unwrap();
        let junction_path = root.join(".openlocus/traces");
        if !create_junction_for_test(outside.path(), &junction_path) {
            eprintln!(
                "skipping colocated windows junction-at-traces-dir test: mklink /J unavailable"
            );
            return;
        }

        let err = append_trace_at_roots(root, root, &TraceEvent::new("must_not_write"))
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("reparse point in trace artifact path")
                || err.contains("symlink in trace artifact path"),
            "got: {}",
            err
        );

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let leaked = outside
            .path()
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(
            !leaked.exists(),
            "junction target must not be mutated through the rejected traces-dir junction"
        );
        assert_eq!(
            fs::read(&outside_sentinel).unwrap().as_slice(),
            sentinel_bytes,
            "target dir contents must remain untouched"
        );
        let _ = std::fs::remove_dir(&junction_path);
    }
}
