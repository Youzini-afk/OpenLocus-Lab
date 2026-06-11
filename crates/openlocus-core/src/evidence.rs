use serde::{Deserialize, Serialize};

// ── Channel enum ──────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Channel {
    Regex,
    Path,
    Bm25,
    Dense,
    TreeSitter,
    Lsp,
    Scip,
    Graph,
    Manual,
}

impl Channel {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Regex => "regex",
            Self::Path => "path",
            Self::Bm25 => "bm25",
            Self::Dense => "dense",
            Self::TreeSitter => "tree_sitter",
            Self::Lsp => "lsp",
            Self::Scip => "scip",
            Self::Graph => "graph",
            Self::Manual => "manual",
        }
    }
}

// ── Freshness enum ────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Freshness {
    VerifiedCurrent,
    VerifiedCommit,
    Overlay,
    #[default]
    PossiblyStale,
    Invalid,
}

// ── DirtyState ────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DirtyState {
    Clean,
    Modified,
    Staged,
    Unstaged,
    Unsaved,
    Generated,
    Deleted,
    Renamed,
}

// ── Symbol ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Symbol {
    pub name: String,
    pub kind: SymbolKind,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub qualified_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub symbol_id: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SymbolKind {
    Function,
    Method,
    Class,
    Interface,
    Type,
    Variable,
    Module,
    Route,
    Test,
    Config,
    Unknown,
}

// ── ScoreParts ─────────────────────────────────────────────────────────

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ScoreParts {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lexical: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bm25: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dense: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub symbol: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub graph: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recency: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub overlay: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reranker: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub penalty_stale: Option<f64>,
}

// ── ExcerptPolicy ──────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExcerptPolicy {
    Full,
    Snippet,
    SignatureOnly,
    MetadataOnly,
    NoSnippet,
}

// ── PolicyInfo ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyInfo {
    pub outbound_allowed: bool,
    pub redacted: bool,
    pub data_level: u8,
}

// ── EvidenceCore (stable contract) ────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceCore {
    pub path: String,
    pub start_line: u64,
    pub end_line: u64,
    pub content_sha: String,
    pub score: f64,
    pub why: Vec<String>,
    pub channels: Vec<Channel>,
}

// ── EvidenceMeta (optional extension) ─────────────────────────────────

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EvidenceMeta {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub repo_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub workspace_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub branch: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub commit_sha: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub working_tree_id: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub language: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub start_byte: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub end_byte: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tree_sha: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dirty_state: Option<DirtyState>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub symbol: Option<Symbol>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub excerpt: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub excerpt_policy: Option<ExcerptPolicy>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub score_parts: Option<ScoreParts>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub freshness: Option<Freshness>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub policy: Option<PolicyInfo>,
}

// ── Evidence ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evidence {
    #[serde(flatten)]
    pub core: EvidenceCore,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub meta: Option<EvidenceMeta>,
}

impl Evidence {
    pub fn new(
        path: impl Into<String>,
        start_line: u64,
        end_line: u64,
        content_sha: impl Into<String>,
        score: f64,
        why: Vec<String>,
        channels: Vec<Channel>,
    ) -> Self {
        Self {
            core: EvidenceCore {
                path: path.into(),
                start_line,
                end_line,
                content_sha: content_sha.into(),
                score,
                why,
                channels,
            },
            meta: None,
        }
    }

    pub fn with_meta(mut self, meta: EvidenceMeta) -> Self {
        self.meta = Some(meta);
        self
    }

    pub fn with_excerpt(mut self, excerpt: impl Into<String>) -> Self {
        let m = self.meta.get_or_insert_with(EvidenceMeta::default);
        m.excerpt = Some(excerpt.into());
        m.excerpt_policy = Some(ExcerptPolicy::Snippet);
        self
    }

    pub fn with_language(mut self, lang: impl Into<String>) -> Self {
        let m = self.meta.get_or_insert_with(EvidenceMeta::default);
        m.language = Some(lang.into());
        self
    }

    pub fn with_freshness(mut self, f: Freshness) -> Self {
        let m = self.meta.get_or_insert_with(EvidenceMeta::default);
        m.freshness = Some(f);
        self
    }
}

// ── EvidencePack ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidencePack {
    pub task: String,
    pub intent: String,
    pub confidence: f64,
    pub evidence: Vec<Evidence>,
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub entrypoints: Vec<Evidence>,
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub related_tests: Vec<Evidence>,
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub risks: Vec<String>,
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub missing_questions: Vec<String>,
    pub trace_id: String,
    pub budget_used: BudgetUsed,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct BudgetUsed {
    pub latency_ms: u64,
    pub tokens_estimated: u64,
    pub remote_cost_estimated: f64,
}

// ── ContextLitePack ───────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextLitePack {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    pub generated_files: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub diagnostics: Option<Vec<Evidence>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dirty_summary: Option<Vec<Evidence>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recent_reads: Option<Vec<Evidence>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recent_edits: Option<Vec<Evidence>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub test_outputs: Option<Vec<TestOutput>>,
    pub trace_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestOutput {
    pub path: String,
    pub content_sha: String,
}

// ── JsonOutput helper ─────────────────────────────────────────────────

pub struct JsonOutput;

impl JsonOutput {
    pub fn to_json<T: Serialize>(val: &T) -> anyhow::Result<String> {
        Ok(serde_json::to_string(val)?)
    }

    pub fn to_json_pretty<T: Serialize>(val: &T) -> anyhow::Result<String> {
        Ok(serde_json::to_string_pretty(val)?)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evidence_core_serializes_with_snake_case() {
        let e = Evidence::new(
            "src/main.rs",
            1,
            10,
            "abc123",
            0.95,
            vec!["matched regex".into()],
            vec![Channel::Regex],
        );
        let json = serde_json::to_value(&e).unwrap();
        assert_eq!(json["path"], "src/main.rs");
        assert_eq!(json["start_line"], 1);
        assert_eq!(json["end_line"], 10);
        assert_eq!(json["content_sha"], "abc123");
        assert_eq!(json["channels"][0], "regex");
    }

    #[test]
    fn evidence_with_meta_roundtrip() {
        let e = Evidence::new("lib.rs", 5, 8, "sha", 1.0, vec![], vec![Channel::Path])
            .with_excerpt("fn main() {}")
            .with_language("rust")
            .with_freshness(Freshness::VerifiedCurrent);
        let json = serde_json::to_string(&e).unwrap();
        let back: Evidence = serde_json::from_str(&json).unwrap();
        assert_eq!(back.core.path, "lib.rs");
        assert_eq!(
            back.meta.as_ref().unwrap().excerpt.as_deref(),
            Some("fn main() {}")
        );
        assert_eq!(
            back.meta.as_ref().unwrap().freshness,
            Some(Freshness::VerifiedCurrent)
        );
    }

    #[test]
    fn channel_str_roundtrip() {
        let ch = Channel::TreeSitter;
        let json = serde_json::to_string(&ch).unwrap();
        assert_eq!(json, "\"tree_sitter\"");
        let back: Channel = serde_json::from_str(&json).unwrap();
        assert_eq!(back, Channel::TreeSitter);
    }

    #[test]
    fn evidence_pack_serializes() {
        let pack = EvidencePack {
            task: "find auth".into(),
            intent: "implementation_search".into(),
            confidence: 0.8,
            evidence: vec![],
            entrypoints: vec![],
            related_tests: vec![],
            risks: vec![],
            missing_questions: vec![],
            trace_id: "t1".into(),
            budget_used: BudgetUsed::default(),
        };
        let json = serde_json::to_string(&pack).unwrap();
        assert!(json.contains("find auth"));
    }
}
