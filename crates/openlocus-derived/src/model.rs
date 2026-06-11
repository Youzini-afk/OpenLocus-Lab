//! Derived index view model types.
//!
//! DerivedIndexView is NOT Evidence. It is a derived/indexed artifact that
//! describes source code regions but cannot be used as authoritative evidence
//! without materialization through the store gate.

use serde::{Deserialize, Serialize};

/// Kinds of derived views. L1 kinds are safe for Level0.
/// High-risk kinds are disabled by default.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DerivedViewKind {
    /// Summary of a chunk (bounded text, no full code)
    ChunkSummary,
    /// Tags extracted from symbol-like names
    SymbolTags,
    /// Query alias suggestions derived from identifiers
    QueryAliases,
    /// Candidate edge between code regions (high-risk, disabled by default)
    CandidateEdge,
    /// Bug symptom hint (high-risk, disabled by default)
    BugSymptomHint,
}

impl DerivedViewKind {
    /// Whether this kind is high-risk and disabled by default.
    pub fn is_high_risk(&self) -> bool {
        matches!(self, Self::CandidateEdge | Self::BugSymptomHint)
    }

    /// All L1 (safe) kinds.
    pub fn l1_kinds() -> &'static [DerivedViewKind] {
        &[Self::ChunkSummary, Self::SymbolTags, Self::QueryAliases]
    }

    /// Parse from string.
    pub fn from_str_loose(s: &str) -> Option<Self> {
        match s {
            "chunk_summary" | "chunk-summary" => Some(Self::ChunkSummary),
            "symbol_tags" | "symbol-tags" => Some(Self::SymbolTags),
            "query_aliases" | "query-aliases" => Some(Self::QueryAliases),
            "candidate_edge" | "candidate-edge" => Some(Self::CandidateEdge),
            "bug_symptom_hint" | "bug-symptom-hint" => Some(Self::BugSymptomHint),
            _ => None,
        }
    }
}

/// Source reference for a derived view.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DerivedSource {
    pub path: String,
    pub start_line: u64,
    pub end_line: u64,
    pub content_sha: String,
    pub language: String,
}

/// What generator produced this view.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DerivedGeneratorKind {
    /// Deterministic rule-based extractor (no LLM)
    RuleExtractor,
    /// Mock LLM (placeholder, deterministic)
    MockLlm,
}

/// Provenance tracking for a derived view.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DerivedProvenance {
    pub generator: DerivedGeneratorKind,
    pub generator_version: String,
    pub remote_calls: u64,
    pub policy_mode: String,
    pub data_level: u8,
}

/// Validation status of a derived view.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DerivedValidation {
    Valid,
    Stale,
    InvalidRange,
    BlockedKind,
    BlockedDataLevel,
    PathUnsafe,
}

/// A derived index view — NOT Evidence.
///
/// Describes a derived artifact about source code. Must go through
/// materialization gate if ever used to produce Evidence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DerivedIndexView {
    /// Deterministic ID: hash of (source_path, source_sha, kind, generator, data_level)
    pub view_id: String,
    pub kind: DerivedViewKind,
    pub source: DerivedSource,
    /// Bounded derived text (no full raw code snippets at data_level <= 1)
    pub derived_text: String,
    /// Optional tags/labels
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,
    pub provenance: DerivedProvenance,
    /// Validation status (set after validation)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub validation: Option<DerivedValidation>,
}

impl DerivedIndexView {
    /// Compute deterministic view ID from source, kind, generator, data_level,
    /// policy_mode, and generator_version.
    /// Same inputs always produce the same ID.
    pub fn compute_view_id(
        source: &DerivedSource,
        kind: &DerivedViewKind,
        generator: &DerivedGeneratorKind,
        data_level: u8,
        policy_mode: &str,
        generator_version: &str,
    ) -> String {
        let preimage = format!(
            "{}:{}:{}:{}:{}:{}:{}:{}:{}",
            source.path,
            source.start_line,
            source.end_line,
            source.content_sha,
            serde_json::to_string(kind).unwrap_or_default(),
            serde_json::to_string(generator).unwrap_or_default(),
            data_level,
            policy_mode,
            generator_version,
        );
        blake3::hash(preimage.as_bytes()).to_hex().to_string()[..16].to_string()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_source(path: &str, sha: &str) -> DerivedSource {
        DerivedSource {
            path: path.to_string(),
            start_line: 1,
            end_line: 10,
            content_sha: sha.to_string(),
            language: "rust".to_string(),
        }
    }

    #[test]
    fn view_id_is_deterministic() {
        let source = make_source("lib.rs", "abc123");
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
    fn view_id_changes_on_source_change() {
        let source1 = make_source("lib.rs", "abc123");
        let source2 = make_source("lib.rs", "def456");
        let id1 = DerivedIndexView::compute_view_id(
            &source1,
            &DerivedViewKind::ChunkSummary,
            &DerivedGeneratorKind::RuleExtractor,
            1,
            "local_only",
            "0.1.0",
        );
        let id2 = DerivedIndexView::compute_view_id(
            &source2,
            &DerivedViewKind::ChunkSummary,
            &DerivedGeneratorKind::RuleExtractor,
            1,
            "local_only",
            "0.1.0",
        );
        assert_ne!(id1, id2);
    }

    #[test]
    fn view_id_changes_on_kind_change() {
        let source = make_source("lib.rs", "abc123");
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
            &DerivedViewKind::SymbolTags,
            &DerivedGeneratorKind::RuleExtractor,
            1,
            "local_only",
            "0.1.0",
        );
        assert_ne!(id1, id2);
    }

    #[test]
    fn view_id_changes_on_policy_mode_change() {
        let source = make_source("lib.rs", "abc123");
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
            "remote_allowed",
            "0.1.0",
        );
        assert_ne!(id1, id2);
    }

    #[test]
    fn view_id_changes_on_generator_version_change() {
        let source = make_source("lib.rs", "abc123");
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
            "0.2.0",
        );
        assert_ne!(id1, id2);
    }

    #[test]
    fn high_risk_kinds() {
        assert!(!DerivedViewKind::ChunkSummary.is_high_risk());
        assert!(!DerivedViewKind::SymbolTags.is_high_risk());
        assert!(!DerivedViewKind::QueryAliases.is_high_risk());
        assert!(DerivedViewKind::CandidateEdge.is_high_risk());
        assert!(DerivedViewKind::BugSymptomHint.is_high_risk());
    }

    #[test]
    fn kind_from_str_loose() {
        assert_eq!(
            DerivedViewKind::from_str_loose("chunk-summary"),
            Some(DerivedViewKind::ChunkSummary)
        );
        assert_eq!(
            DerivedViewKind::from_str_loose("symbol_tags"),
            Some(DerivedViewKind::SymbolTags)
        );
        assert_eq!(DerivedViewKind::from_str_loose("bogus"), None);
    }
}
