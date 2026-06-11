//! Validation of derived views against current filesystem state.
//!
//! Checks: path safe, source content_sha matches, range valid, kind allowed,
//! data_level allowed. No remote calls.

use crate::model::{DerivedIndexView, DerivedValidation};
use std::path::Path;

/// Validate a derived view against the current filesystem.
/// Returns the validation status (valid, stale, blocked, etc.).
pub fn validate_derived_view(
    repo_root: &Path,
    view: &DerivedIndexView,
    max_data_level: u8,
) -> DerivedValidation {
    // Check kind allowed (high-risk blocked by default)
    if view.kind.is_high_risk() {
        return DerivedValidation::BlockedKind;
    }

    // Check data_level
    if view.provenance.data_level > max_data_level {
        return DerivedValidation::BlockedDataLevel;
    }

    // Validate path
    if openlocus_repo::validate_path(repo_root, &view.source.path).is_err() {
        return DerivedValidation::PathUnsafe;
    }

    let full_path = repo_root.join(&view.source.path);
    if !full_path.exists() || !full_path.is_file() {
        return DerivedValidation::Stale;
    }

    // Read file bytes once (TOCTOU-safe)
    let bytes = match std::fs::read(&full_path) {
        Ok(b) => b,
        Err(_) => return DerivedValidation::Stale,
    };

    let current_sha = blake3::hash(&bytes).to_hex().to_string();

    // Check content_sha matches
    if view.source.content_sha != current_sha {
        return DerivedValidation::Stale;
    }

    // Validate range
    let content = String::from_utf8_lossy(&bytes);
    let total_lines = content.lines().count() as u64;

    if view.source.start_line < 1
        || view.source.start_line > view.source.end_line
        || view.source.end_line > total_lines
    {
        return DerivedValidation::InvalidRange;
    }

    DerivedValidation::Valid
}

/// Validate all views and return (valid_count, stale_count, blocked_kind_count,
/// blocked_data_level_count, path_unsafe_count, invalid_range_count).
pub fn validate_all_views(
    repo_root: &Path,
    views: &[DerivedIndexView],
    max_data_level: u8,
) -> (usize, usize, usize, usize, usize, usize) {
    let mut valid = 0;
    let mut stale = 0;
    let mut blocked_kind = 0;
    let mut blocked_data_level = 0;
    let mut path_unsafe = 0;
    let mut invalid_range = 0;

    for view in views {
        match validate_derived_view(repo_root, view, max_data_level) {
            DerivedValidation::Valid => valid += 1,
            DerivedValidation::Stale => stale += 1,
            DerivedValidation::BlockedKind => blocked_kind += 1,
            DerivedValidation::BlockedDataLevel => blocked_data_level += 1,
            DerivedValidation::PathUnsafe => path_unsafe += 1,
            DerivedValidation::InvalidRange => invalid_range += 1,
        }
    }

    (
        valid,
        stale,
        blocked_kind,
        blocked_data_level,
        path_unsafe,
        invalid_range,
    )
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{DerivedGeneratorKind, DerivedProvenance, DerivedSource, DerivedViewKind};

    fn make_view(
        path: &str,
        sha: &str,
        kind: DerivedViewKind,
        data_level: u8,
        start: u64,
        end: u64,
    ) -> DerivedIndexView {
        let source = DerivedSource {
            path: path.to_string(),
            start_line: start,
            end_line: end,
            content_sha: sha.to_string(),
            language: "rust".to_string(),
        };
        let view_id = DerivedIndexView::compute_view_id(
            &source,
            &kind,
            &DerivedGeneratorKind::RuleExtractor,
            data_level,
            "local_only",
            "0.1.0",
        );
        DerivedIndexView {
            view_id,
            kind,
            source,
            derived_text: "test".to_string(),
            tags: vec![],
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

    #[test]
    fn validate_valid_view() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("lib.rs"), "fn test() {}\n").unwrap();
        let bytes = std::fs::read(root.join("lib.rs")).unwrap();
        let sha = blake3::hash(&bytes).to_hex().to_string();

        let view = make_view("lib.rs", &sha, DerivedViewKind::ChunkSummary, 1, 1, 1);
        let result = validate_derived_view(root, &view, 1);
        assert_eq!(result, DerivedValidation::Valid);
    }

    #[test]
    fn validate_stale_view() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("lib.rs"), "fn test() {}\n").unwrap();

        let view = make_view(
            "lib.rs",
            "stale_sha",
            DerivedViewKind::ChunkSummary,
            1,
            1,
            1,
        );
        let result = validate_derived_view(root, &view, 1);
        assert_eq!(result, DerivedValidation::Stale);
    }

    #[test]
    fn validate_blocked_kind() {
        let dir = tempfile::tempdir().unwrap();
        let view = make_view("lib.rs", "any", DerivedViewKind::CandidateEdge, 1, 1, 1);
        let result = validate_derived_view(dir.path(), &view, 1);
        assert_eq!(result, DerivedValidation::BlockedKind);
    }

    #[test]
    fn validate_blocked_data_level() {
        let dir = tempfile::tempdir().unwrap();
        let view = make_view("lib.rs", "any", DerivedViewKind::ChunkSummary, 5, 1, 1);
        let result = validate_derived_view(dir.path(), &view, 1);
        assert_eq!(result, DerivedValidation::BlockedDataLevel);
    }

    #[test]
    fn validate_path_unsafe() {
        let dir = tempfile::tempdir().unwrap();
        let view = make_view(
            "../../../etc/passwd",
            "any",
            DerivedViewKind::ChunkSummary,
            1,
            1,
            1,
        );
        let result = validate_derived_view(dir.path(), &view, 1);
        assert_eq!(result, DerivedValidation::PathUnsafe);
    }

    #[test]
    fn validate_invalid_range() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("lib.rs"), "fn test() {}\n").unwrap();
        let bytes = std::fs::read(root.join("lib.rs")).unwrap();
        let sha = blake3::hash(&bytes).to_hex().to_string();

        let view = make_view("lib.rs", &sha, DerivedViewKind::ChunkSummary, 1, 0, 1);
        let result = validate_derived_view(root, &view, 1);
        assert_eq!(result, DerivedValidation::InvalidRange);
    }
}
