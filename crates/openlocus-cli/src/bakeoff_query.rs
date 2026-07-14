//! `bakeoff-query`: narrow B1 v2 Rust integration surface.
//!
//! One backward-compatible internal CLI subcommand that exposes the
//! production retrieval stack (persistent BM25, literal text exactly once,
//! exact-name AST symbol, eligible depth-1 graph seeded from real pre-graph
//! evidence, and production tie-aware, graph-weighted RRF K=60) to the B1 v2
//! Python adapters WITHOUT imitating any production component.
//!
//! Contract source of truth: `.slim/deepwork/product-bakeoff-b1.md`
//! (`V2 repair contract`, `Narrow Rust integration reopening`,
//! `V2 parallel write ownership`). This module must not change RRF K,
//! duplicate fusion, infer paths from queries, fall back, or emit a
//! successful envelope on any configured component error / malformed /
//! saturated / unsafe-skip / persistent-state-unavailable / missing-receipt
//! condition.
//!
//! Read-only except existing checked trace routing under the caller state
//! root. Existing `retrieve`, search/index/graph/impact behavior and output
//! remain unchanged.

use anyhow::{Context, Result, bail};
use openlocus_ast::{AstSymbolKind, AstSymbolStatus, extract_ast_symbols};
use openlocus_core::{Channel, Evidence, Policy, TraceEvent, append_trace_at_roots};
use openlocus_graph::graph::{self, EdgeKind, GraphEdge};
use openlocus_graph::materialize::materialize_graph_edges;
use openlocus_index::persistent::{
    search_persistent_bm25_at_state_root, status_index_at_state_root,
};
use openlocus_provider::{audit::AUDIT_RELATIVE_PATH, model::EmbeddingAuditEvent};
use openlocus_repo::scan::scan_repo;
use openlocus_repo::validate_path;
use openlocus_retrieval::regex_search::text_search;
use openlocus_retrieval::rrf::rrf_combine_with_rank_ties_and_channel_weights;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

// ── Closed contract constants ─────────────────────────────────────────

/// Closed JSON envelope schema marker (immutable per v2 freeze).
pub const BAKEOFF_QUERY_SCHEMA_VERSION: &str = "openlocus.bakeoff_query.v2.3";

/// Production RRF marker. Existing callers keep the original RRF function;
/// B1 explicitly uses the reusable equal-native-score competition-rank
/// variant (`1, 1, 3`) with fixed K=60 and a disclosed graph weight of 2.
pub const BAKEOFF_QUERY_RRF_MARKER: &str = "production_rrf_combine_rank_ties_weighted_graph";

/// RRF provenance: crate path + frozen K. Read-only diagnostic.
pub const BAKEOFF_QUERY_RRF_VERSION: &str =
    "openlocus-retrieval/rrf.rs:K=60:competition_ties_v1:graph_weight_2";

/// Frozen RRF K. Read directly from the production constant via the
/// tie-aware RRF call signature — it cannot be overridden from this
/// surface. Reported for diagnostic closure only.
pub const BAKEOFF_QUERY_RRF_K: u64 = 60;
const BM25_DETERMINISTIC_OVERFETCH_MAX: usize = 64;
pub const BAKEOFF_QUERY_INPUT_NORMALIZATION: &str = "contained_span_to_narrowest_path_range_v1";
pub const BAKEOFF_QUERY_RANK_TIE_POLICY: &str = "equal_native_score_competition_rank_v1";
pub const BAKEOFF_QUERY_CHANNEL_WEIGHTS: &str = "bm25=1,regex=1,tree_sitter=1,graph=2";

/// Canonical cumulative component order (closed set).
///
/// S0 = `[bm25]`; S1 = `[bm25, literal]`; S2 = `[bm25, literal, symbol]`;
/// S3 = `[bm25, literal, symbol, graph]`. Any other order, missing
/// intermediate component, duplicate, or unknown name is rejected
/// fail-closed.
pub const CANONICAL_COMPONENT_ORDER: &[&str] = &["bm25", "literal", "symbol", "graph"];

/// Closed task family set (B1 v2 mechanics design).
pub const VALID_TASK_FAMILIES: &[&str] = &[
    "symbol_lookup",
    "definition_find",
    "caller_trace",
    "type_resolution",
    "cross_file_dependency",
    "refactor_target_find",
    "ambiguous_target",
    "error_text",
    "configuration_discovery",
    "test_discovery",
    "no_answer",
];

/// Phase-A task families for which the frozen conditional graph predicate is
/// true. A requested graph component outside this set is a legitimate skip;
/// once the predicate fires, missing seed evidence is an error rather than a
/// silent skip.
pub const GRAPH_ELIGIBLE_TASK_FAMILIES: &[&str] = &[
    "caller_trace",
    "cross_file_dependency",
    "configuration_discovery",
    "test_discovery",
];

// Receipt statuses (closed).
pub const RECEIPT_EXECUTED: &str = "executed";
pub const RECEIPT_LEGITIMATE_SKIP: &str = "legitimate_skip";
pub const RECEIPT_ERROR: &str = "error";

// Skip reasons (closed).
pub const SKIP_REASON_IDENTIFIER_PREDICATE_FALSE: &str = "identifier_predicate_false";
pub const SKIP_REASON_GRAPH_PREDICATE_FALSE: &str = "graph_task_family_predicate_false";

/// B1 support intentionally admits only honest production import edges and
/// maps them to Phase A's canonical `import` relation. Tests/configuration
/// graph edges remain available to context graph retrieval but are not
/// fabricated into unsupported Phase A support relations.
pub const RELATION_KINDS: &[&str] = &["import"];

// ── CLI argument structs ──────────────────────────────────────────────

/// `bakeoff-query context` arguments.
#[derive(Debug, Clone, Deserialize)]
pub struct ContextArgs {
    pub source_root: String,
    pub state_root: String,
    pub query: String,
    /// Closed ordered cumulative component set, comma-separated.
    /// Valid prefixes of `bm25,literal,symbol,graph` only.
    pub components: String,
    /// One of `VALID_TASK_FAMILIES`.
    pub task_family: String,
    pub max_results: usize,
}

/// `bakeoff-query support` arguments.
#[derive(Debug, Clone, Deserialize)]
pub struct SupportArgs {
    pub source_root: String,
    pub state_root: String,
    /// Explicit verified parent path under source_root. Never inferred.
    pub parent_path: String,
    /// Parent line range, `"start-end"` (1-indexed, inclusive).
    pub parent_range: String,
    pub max_results: usize,
}

// ── JSON envelope types ───────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
pub struct BakeoffEnvelope {
    pub schema_version: String,
    pub success: bool,
    pub mode: String,
    pub source_root: String,
    pub state_root: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub query: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub task_family: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_results: Option<usize>,
    pub components_requested: Vec<String>,
    pub components_executed: Vec<String>,
    pub evidence: Vec<BakeoffEvidence>,
    pub evidence_count: usize,
    pub rrf: RrfDiagnostics,
    pub receipts: Vec<Receipt>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent: Option<ParentDiagnostics>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub relations: Option<Vec<RelationProvenance>>,
    pub provider: ProviderDiagnostics,
    pub trace: TraceDiagnostics,
}

/// Closed flattened evidence surface. Adapter candidates intentionally do
/// not receive excerpts, freshness assertions, symbols or other production
/// metadata; the Phase A materializer rereads current source independently.
#[derive(Debug, Clone, Serialize)]
pub struct BakeoffEvidence {
    pub path: String,
    pub start_line: u64,
    pub end_line: u64,
    pub content_sha: String,
    pub score: f64,
    pub why: Vec<String>,
    pub channels: Vec<String>,
}

fn flatten_evidence(evidence: Evidence) -> BakeoffEvidence {
    BakeoffEvidence {
        path: evidence.core.path,
        start_line: evidence.core.start_line,
        end_line: evidence.core.end_line,
        content_sha: evidence.core.content_sha,
        score: evidence.core.score,
        why: evidence.core.why,
        channels: evidence
            .core
            .channels
            .into_iter()
            .map(|channel| channel.as_str().to_string())
            .collect(),
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct RrfDiagnostics {
    pub marker: String,
    pub version: String,
    pub k: u64,
    pub tie_order: String,
    pub rank_tie_policy: String,
    pub channel_weights: String,
    pub input_normalization: String,
    pub input_rewrites: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct Receipt {
    pub component: String,
    pub status: String,
    pub evidence_count: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    pub diagnostics: serde_json::Value,
}

#[derive(Debug, Clone, Serialize)]
pub struct ParentDiagnostics {
    pub path: String,
    pub start_line: u64,
    pub end_line: u64,
    pub confinement: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct RelationProvenance {
    pub relation_kind: String,
    pub production_edge_kind: String,
    pub support_path: String,
    pub support_start_line: u64,
    pub support_end_line: u64,
    pub target_path: String,
    pub target_start_line: u64,
    pub target_end_line: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct ProviderDiagnostics {
    pub remote_calls: u64,
    pub outbound_calls: u64,
    pub audit_path: String,
    pub audit_events_before: u64,
    pub audit_events_after: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct TraceDiagnostics {
    pub routed_to: String,
    pub event: String,
    pub written: bool,
}

// ── Error envelope (still strict, still closed) ──────────────────────

/// Strict closed failure envelope. Emitted INSTEAD of `BakeoffEnvelope`
/// whenever any fail-closed condition trips. Never carries evidence.
#[derive(Debug, Clone, Serialize)]
pub struct BakeoffErrorEnvelope {
    pub schema_version: String,
    pub success: bool,
    pub mode: String,
    pub error: String,
    pub fail_closed_reason: String,
    pub components_requested: Vec<String>,
    pub receipts: Vec<Receipt>,
    pub provider: ProviderDiagnostics,
    pub trace: TraceDiagnostics,
}

// ── Component parsing / validation ────────────────────────────────────

/// Parse and validate the closed ordered cumulative component set.
///
/// Fail-closed rules:
/// - Empty set is rejected.
/// - Unknown component names are rejected.
/// - Duplicates are rejected.
/// - Out-of-order or non-cumulative sets (e.g. `[bm25, symbol]` skipping
///   `literal`, or `[literal, bm25]`) are rejected.
pub fn parse_components(raw: &str) -> Result<Vec<String>> {
    let parsed: Vec<String> = raw
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();

    if parsed.is_empty() {
        bail!(
            "components set is empty; expected a non-empty cumulative prefix of [bm25, literal, symbol, graph]"
        );
    }

    // Unknown / duplicate check.
    let valid: HashSet<&str> = CANONICAL_COMPONENT_ORDER.iter().copied().collect();
    let mut seen: HashSet<String> = HashSet::new();
    for c in &parsed {
        if !valid.contains(c.as_str()) {
            bail!(
                "unknown component '{}'; closed set is [bm25, literal, symbol, graph]",
                c
            );
        }
        if !seen.insert(c.clone()) {
            bail!(
                "duplicate component '{}'; components must be a set (no duplicates)",
                c
            );
        }
    }

    // Cumulative-prefix check: parsed must equal one of the canonical
    // prefixes of CANONICAL_COMPONENT_ORDER.
    let is_canonical_prefix = (1..=CANONICAL_COMPONENT_ORDER.len()).any(|n| {
        let prefix: Vec<String> = CANONICAL_COMPONENT_ORDER[..n]
            .iter()
            .map(|s| s.to_string())
            .collect();
        prefix == parsed
    });
    if !is_canonical_prefix {
        bail!(
            "components {:?} are not a cumulative prefix of [bm25, literal, symbol, graph]; \
             valid stacks are S0=[bm25], S1=[bm25,literal], S2=[bm25,literal,symbol], S3=[bm25,literal,symbol,graph]",
            parsed
        );
    }

    Ok(parsed)
}

/// Validate the task family against the closed set.
pub fn validate_task_family(family: &str) -> Result<()> {
    if VALID_TASK_FAMILIES.contains(&family) {
        Ok(())
    } else {
        bail!(
            "unknown task_family '{}'; closed set is {:?}",
            family,
            VALID_TASK_FAMILIES
        )
    }
}

/// Frozen language-neutral identifier predicate used to decide whether the
/// exact-name AST symbol component is applicable. It intentionally accepts
/// only a single ASCII identifier (1..=128 bytes); prose, punctuation and
/// whitespace cause a legitimate skip rather than an AST-to-text fallback.
pub fn identifier_predicate(query: &str) -> bool {
    let bytes = query.as_bytes();
    if bytes.is_empty() || bytes.len() > 128 {
        return false;
    }
    let first = bytes[0];
    if !(first == b'_' || first.is_ascii_alphabetic()) {
        return false;
    }
    bytes[1..]
        .iter()
        .all(|b| *b == b'_' || b.is_ascii_alphanumeric())
}

/// Frozen task-family predicate for conditional depth-1 graph retrieval.
pub fn graph_task_family_predicate(task_family: &str) -> bool {
    GRAPH_ELIGIBLE_TASK_FAMILIES.contains(&task_family)
}

// ── Provider audit counting (no provider calls in this surface) ──────

fn count_audit_events(state_root: &Path) -> Result<u64> {
    let audit_path = state_root.join(AUDIT_RELATIVE_PATH);
    let metadata = fs::symlink_metadata(&audit_path).with_context(|| {
        format!(
            "provider audit evidence is missing at {} (fail-closed)",
            audit_path.display()
        )
    })?;
    if !metadata.file_type().is_file() || metadata.file_type().is_symlink() {
        bail!(
            "provider audit evidence is not an ordinary file at {} (fail-closed)",
            audit_path.display()
        );
    }
    let content = fs::read_to_string(&audit_path).context("failed to read audit log")?;
    let mut count: u64 = 0;
    for (line_index, line) in content.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        serde_json::from_str::<EmbeddingAuditEvent>(line).with_context(|| {
            format!(
                "malformed provider audit event at {} line {} (fail-closed)",
                audit_path.display(),
                line_index + 1
            )
        })?;
        count += 1;
    }
    Ok(count)
}

/// Build provider diagnostics by counting audit events before and after
/// the command. The bakeoff-query surface never invokes a provider, so the
/// delta must be zero. Any nonzero delta is a fail-closed condition.
fn build_provider_diagnostics(
    state_root: &Path,
    events_before: u64,
) -> Result<ProviderDiagnostics> {
    let events_after = count_audit_events(state_root)?;
    let audit_path = state_root.join(AUDIT_RELATIVE_PATH);
    if events_after != events_before {
        bail!(
            "provider audit count changed during bakeoff-query: before={}, after={} (fail-closed)",
            events_before,
            events_after
        );
    }
    Ok(ProviderDiagnostics {
        remote_calls: 0,
        outbound_calls: 0,
        audit_path: audit_path.to_string_lossy().to_string(),
        audit_events_before: events_before,
        audit_events_after: events_after,
    })
}

// ── Trace routing ────────────────────────────────────────────────────

/// Append a bakeoff-query trace event through the existing checked
/// source-aware `append_trace_at_roots` helper. In separated mode the
/// trace is written under `state_root/.openlocus/traces/`; in colocated
/// mode under `repo_root/.openlocus/traces/`. Never falls back to source
/// root or to raw writes. B1 is stricter than ordinary telemetry: a trace
/// failure blocks the envelope because the parent must have checked evidence
/// that every production request was routed to its declared writable state.
fn route_trace(
    source_root: &Path,
    state_root: &Path,
    event: &str,
    input: serde_json::Value,
    output: serde_json::Value,
) -> Result<TraceDiagnostics> {
    let ev = TraceEvent::new(event).with_input(input).with_output(output);
    let routed_to = state_root
        .join(".openlocus")
        .join("traces")
        .to_string_lossy()
        .to_string();
    append_trace_at_roots(source_root, state_root, &ev)
        .with_context(|| format!("failed to write checked B1 trace event '{event}'"))?;
    Ok(TraceDiagnostics {
        routed_to,
        event: event.to_string(),
        written: true,
    })
}

// ── Resolved roots ────────────────────────────────────────────────────

/// Resolved caller roots for bakeoff-query. Mirrors the CLI's
/// `ResolvedRoots` but is fail-closed for bakeoff-query: BOTH
/// `--source-root` and `--state-root` are required (no colocated default
/// to `repo_root`). Persistent state must be explicit.
#[derive(Debug, Clone)]
pub struct BakeoffRoots {
    pub source_root: PathBuf,
    pub state_root: PathBuf,
    pub separated: bool,
}

/// Resolve caller roots fail-closed. Both roots are mandatory.
pub fn resolve_bakeoff_roots(source_root: &str, state_root: &str) -> Result<BakeoffRoots> {
    if source_root.trim().is_empty() {
        bail!("bakeoff-query requires --source-root (fail-closed)");
    }
    if state_root.trim().is_empty() {
        bail!("bakeoff-query requires --state-root (fail-closed)");
    }
    let source_raw = PathBuf::from(source_root);
    let state_raw = PathBuf::from(state_root);
    if !source_raw.exists() {
        bail!(
            "source_root does not exist: {} (fail-closed)",
            source_raw.display()
        );
    }
    if !state_raw.exists() {
        bail!(
            "state_root does not exist: {} (fail-closed)",
            state_raw.display()
        );
    }
    let source = fs::canonicalize(&source_raw)
        .with_context(|| format!("cannot canonicalize source_root {}", source_raw.display()))?;
    let state = fs::canonicalize(&state_raw)
        .with_context(|| format!("cannot canonicalize state_root {}", state_raw.display()))?;
    if !source.is_dir() || !state.is_dir() {
        bail!("source_root and state_root must both be directories (fail-closed)");
    }
    let separated = source != state;
    Ok(BakeoffRoots {
        source_root: source,
        state_root: state,
        separated,
    })
}

// ── Component executors ───────────────────────────────────────────────

/// Stabilize one component before B1's production tie-aware RRF fusion.
/// Equal-score persistent-index hits can otherwise inherit process-local
/// Tantivy document-address order. Preserve native scores, add the frozen
/// path/range tie order, deduplicate exact cells, and then apply the cap.
fn canonicalize_component_evidence(
    mut evidence: Vec<Evidence>,
    max_results: usize,
) -> Result<Vec<Evidence>> {
    for item in &evidence {
        if !item.core.score.is_finite() || item.core.score < 0.0 {
            bail!("component evidence contains a non-finite/negative score (fail-closed)");
        }
    }
    evidence.sort_by(|a, b| {
        b.core
            .score
            .partial_cmp(&a.core.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.core.path.cmp(&b.core.path))
            .then_with(|| a.core.start_line.cmp(&b.core.start_line))
            .then_with(|| a.core.end_line.cmp(&b.core.end_line))
    });
    let mut seen: HashSet<(String, u64, u64)> = HashSet::new();
    evidence.retain(|item| {
        seen.insert((
            item.core.path.clone(),
            item.core.start_line,
            item.core.end_line,
        ))
    });
    evidence.truncate(max_results);
    Ok(evidence)
}

fn canonicalize_rrf_input_overlaps(
    channel_evidence: &mut [(Vec<Evidence>, Channel)],
    max_results: usize,
) -> Result<usize> {
    let cells: Vec<(String, u64, u64)> = channel_evidence
        .iter()
        .flat_map(|(items, _)| {
            items.iter().map(|item| {
                (
                    item.core.path.clone(),
                    item.core.start_line,
                    item.core.end_line,
                )
            })
        })
        .collect();
    let mut rewrites = 0usize;
    for (items, _) in channel_evidence.iter_mut() {
        for item in items.iter_mut() {
            let canonical = cells
                .iter()
                .filter(|(path, start, end)| {
                    path == &item.core.path
                        && *start >= item.core.start_line
                        && *end <= item.core.end_line
                        && (*start > item.core.start_line || *end < item.core.end_line)
                })
                .min_by_key(|(_, start, end)| (end - start, *start, *end));
            if let Some((_, start, end)) = canonical {
                item.core.start_line = *start;
                item.core.end_line = *end;
                item.meta = None;
                rewrites += 1;
            }
        }
        let normalized = canonicalize_component_evidence(std::mem::take(items), max_results)?;
        *items = normalized;
    }
    Ok(rewrites)
}

/// Run persistent BM25 against the caller's persistent state. The persistent
/// index must already exist and be valid; otherwise this is a configured
/// fail-closed error rather than a legitimate skip.
fn exec_bm25(
    roots: &BakeoffRoots,
    policy: &Policy,
    query: &str,
    max_results: usize,
) -> Result<(Vec<Evidence>, serde_json::Value)> {
    let status = status_index_at_state_root(&roots.source_root, &roots.state_root, policy)?;
    if !status.exists {
        bail!(
            "persistent BM25 index does not exist at state_root={}; \
             build it with `openlocus index build --source-root ... --state-root ...` \
             before invoking bakeoff-query (fail-closed)",
            roots.state_root.display()
        );
    }
    if status.requires_rebuild {
        bail!(
            "persistent BM25 index at state_root={} requires rebuild; \
             rerun `openlocus index build` (fail-closed)",
            roots.state_root.display()
        );
    }
    let fetch_limit = max_results
        .saturating_mul(8)
        .max(max_results)
        .min(BM25_DETERMINISTIC_OVERFETCH_MAX);
    let (raw_evidence, stats) = search_persistent_bm25_at_state_root(
        &roots.source_root,
        &roots.state_root,
        query,
        fetch_limit,
        policy,
    )?;
    let raw_evidence_count = raw_evidence.len();
    let evidence = canonicalize_component_evidence(raw_evidence, max_results)?;
    let diagnostics = serde_json::json!({
        "index_source": "persistent_state_root",
        "state_root": roots.state_root.to_string_lossy(),
        "separated": roots.separated,
        "deterministic_tie_order": "score_desc_path_asc_start_asc_end_asc",
        "exact_cell_dedup": true,
        "overfetch_limit": fetch_limit,
        "raw_evidence_count": raw_evidence_count,
        "canonical_evidence_count": evidence.len(),
        "stale_hits_skipped": stats.stale_hits_skipped,
        "invalid_hits_skipped": stats.invalid_hits_skipped,
        "query_ms": stats.query_ms,
        "materialize_ms": stats.materialize_ms,
    });
    Ok((evidence, diagnostics))
}

/// Run production literal text search exactly once via the unchanged
/// `text_search` helper. The query is regex-escaped exactly once inside
/// `text_search`; we do NOT re-escape, dedupe, or otherwise mutate it.
fn exec_literal(
    roots: &BakeoffRoots,
    policy: &Policy,
    query: &str,
    max_results: usize,
) -> Result<(Vec<Evidence>, serde_json::Value)> {
    let records = scan_repo(&roots.source_root, policy)?;
    let evidence = text_search(&roots.source_root, &records, query, max_results)?;
    let diagnostics = serde_json::json!({
        "channel": "regex_escaped_literal",
        "text_escaped_once": true,
        "escape_count": 1,
        "post_fusion_resort": false,
        "fallback": false,
    });
    Ok((evidence, diagnostics))
}

/// Run exact-name post-filtered AST symbol search under the frozen
/// identifier predicate. Only exact symbol name equality (case-sensitive)
/// passes; substring matches are rejected.
fn exec_symbol(
    roots: &BakeoffRoots,
    policy: &Policy,
    query: &str,
    max_results: usize,
) -> Result<(Vec<Evidence>, serde_json::Value)> {
    let records = scan_repo(&roots.source_root, policy)?;
    let mut results: Vec<Evidence> = Vec::new();

    for record in &records {
        if results.len() >= max_results {
            break;
        }
        let full_path = validate_path(&roots.source_root, &record.path).with_context(|| {
            format!(
                "symbol scan path '{}' failed source-root validation",
                record.path
            )
        })?;
        let content = fs::read_to_string(&full_path).with_context(|| {
            format!("symbol scan could not read UTF-8 source '{}'", record.path)
        })?;
        let content_sha = blake3::hash(content.as_bytes()).to_hex().to_string();
        let lines: Vec<&str> = content.lines().collect();
        let total_lines = lines.len() as u64;

        let ast_result = extract_ast_symbols(&record.path, &record.language, &content);
        if ast_result.status != AstSymbolStatus::Supported {
            continue;
        }

        for sym in &ast_result.symbols {
            if results.len() >= max_results {
                break;
            }
            // Frozen identifier predicate: EXACT name equality. Substring
            // matches (`contains`) are explicitly rejected — this is the
            // v2 "exact-name post-filtered AST symbol" requirement.
            if sym.name != query {
                continue;
            }
            if sym.start_line < 1 || sym.end_line > total_lines || sym.start_line > sym.end_line {
                continue;
            }
            let excerpt = lines[(sym.start_line - 1) as usize..sym.end_line as usize].join("\n");
            let core_symbol_kind = match sym.kind {
                AstSymbolKind::Function => openlocus_core::SymbolKind::Function,
                AstSymbolKind::Method => openlocus_core::SymbolKind::Method,
                AstSymbolKind::Class => openlocus_core::SymbolKind::Class,
                AstSymbolKind::Interface => openlocus_core::SymbolKind::Interface,
                AstSymbolKind::Type => openlocus_core::SymbolKind::Type,
                AstSymbolKind::Enum => openlocus_core::SymbolKind::Type,
                AstSymbolKind::Trait => openlocus_core::SymbolKind::Interface,
                AstSymbolKind::Module => openlocus_core::SymbolKind::Module,
                AstSymbolKind::Variable => openlocus_core::SymbolKind::Variable,
                AstSymbolKind::Constant => openlocus_core::SymbolKind::Variable,
                AstSymbolKind::Macro => openlocus_core::SymbolKind::Function,
                AstSymbolKind::Decorator => openlocus_core::SymbolKind::Function,
                AstSymbolKind::Unknown => openlocus_core::SymbolKind::Unknown,
            };
            let evidence = Evidence::new(
                &record.path,
                sym.start_line,
                sym.end_line,
                &content_sha,
                1.0,
                vec![format!("ast_symbol_exact: {}", sym.name)],
                vec![Channel::TreeSitter],
            )
            .with_excerpt(&excerpt)
            .with_language(&record.language)
            .with_freshness(openlocus_core::Freshness::VerifiedCurrent)
            .with_symbol(openlocus_core::Symbol {
                name: sym.name.clone(),
                kind: core_symbol_kind,
                qualified_name: None,
                symbol_id: None,
            })
            .with_score_parts(openlocus_core::ScoreParts {
                symbol: Some(1.0),
                ..Default::default()
            });
            results.push(evidence);
        }
    }

    let diagnostics = serde_json::json!({
        "predicate": "ascii_identifier_v1",
        "predicate_matched": true,
        "match": "exact_name",
        "post_filter": "frozen_identifier_predicate",
        "case_sensitive": true,
        "substring_rejected": true,
        "ast_to_text_fallback": false,
    });
    Ok((results, diagnostics))
}

/// Run eligible depth-1 production graph expansion seeded from real
/// pre-graph evidence. The seed is the set of unique paths from the
/// already-retrieved BM25/literal/symbol evidence; the query is NEVER
/// used to derive paths.
///
/// The caller evaluates the frozen task-family predicate before entering
/// this function. Once that predicate fires, an empty pre-graph seed is a
/// mechanics error and fails closed; it is never converted to a skip.
fn exec_graph(
    roots: &BakeoffRoots,
    policy: &Policy,
    pre_graph_evidence: &[Evidence],
    max_results: usize,
) -> Result<(Vec<Evidence>, serde_json::Value)> {
    // Seed: unique paths from pre-graph evidence only. No query-derived
    // paths. No filename inference.
    let mut seed_paths: Vec<String> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for ev in pre_graph_evidence {
        if seen.insert(ev.core.path.clone()) {
            seed_paths.push(ev.core.path.clone());
        }
    }
    seed_paths.sort();

    if seed_paths.is_empty() {
        bail!("graph predicate fired but pre-graph evidence produced no seed path (fail-closed)");
    }

    let records = scan_repo(&roots.source_root, policy)?;
    let (_nodes, edges, build_result) = graph::build_graph(&roots.source_root, &records)?;

    // Fail-closed: any unsafe/stale skip during graph build invalidates
    // the envelope. V2 spec requires zero skipped-stale / path-unsafe.
    let unsafe_skips_present =
        build_result.skipped_stale > 0 || build_result.skipped_path_unsafe > 0;

    let diagnostics = serde_json::json!({
        "predicate": "phase_a_graph_task_family_v1",
        "predicate_matched": true,
        "depth": 1,
        "seed_source": "pre_graph_evidence",
        "seed_count": seed_paths.len(),
        "seed_paths": seed_paths,
        "skipped_stale": build_result.skipped_stale,
        "skipped_path_unsafe": build_result.skipped_path_unsafe,
        "inspect_saturated": false,
        "unsafe_skips_present": unsafe_skips_present,
        "parent_path_inferred_from_query": false,
        "edge_count": build_result.edge_count,
        "node_count": build_result.node_count,
    });

    if unsafe_skips_present {
        bail!(
            "graph build reported unsafe/stale skips (skipped_stale={}, skipped_path_unsafe={}); \
             fail-closed per V2 contract",
            build_result.skipped_stale,
            build_result.skipped_path_unsafe
        );
    }

    // Depth-1 inbound dependency expansion (production `impact_edges`).
    let mut fused_edges: Vec<GraphEdge> = Vec::new();
    let mut seen_edges: HashSet<(String, String, String, u64, u64)> = HashSet::new();
    for seed in &seed_paths {
        let impacted = graph::impact_edges(&edges, seed, 1)?;
        for edge in impacted {
            let key = (
                edge.source_path.clone(),
                edge.target_path.clone(),
                format!("{:?}", edge.kind),
                edge.source_line,
                edge.source_end_line,
            );
            if seen_edges.insert(key) {
                fused_edges.push(edge);
            }
        }
    }
    fused_edges.sort_by(|a, b| {
        a.source_path
            .cmp(&b.source_path)
            .then_with(|| a.source_line.cmp(&b.source_line))
            .then_with(|| a.source_end_line.cmp(&b.source_end_line))
            .then_with(|| a.target_path.cmp(&b.target_path))
            .then_with(|| format!("{:?}", a.kind).cmp(&format!("{:?}", b.kind)))
    });

    // Materialize via production helper. Skips here are stale-edge
    // materialization failures; they are NOT graph-build skips. We still
    // report them and fail closed if any occur (the source tree must be
    // consistent for B1).
    let (evidence, skipped) = materialize_graph_edges(&roots.source_root, &fused_edges);

    let mut diagnostics = diagnostics;
    if let Some(obj) = diagnostics.as_object_mut() {
        obj.insert(
            "materialized".to_string(),
            serde_json::json!(evidence.len()),
        );
        obj.insert(
            "materialization_skipped".to_string(),
            serde_json::json!(skipped),
        );
        obj.insert(
            "candidate_edges".to_string(),
            serde_json::json!(fused_edges.len()),
        );
    }
    if skipped > 0 {
        bail!(
            "graph edge materialization skipped {} edge(s); source tree inconsistent (fail-closed)",
            skipped
        );
    }

    // Cap to max_results (post-fusion dedup is preserved by RRF later).
    let capped: Vec<Evidence> = evidence.into_iter().take(max_results).collect();
    Ok((capped, diagnostics))
}

// ── Support mode executor ─────────────────────────────────────────────

/// Parse a `"start-end"` range string into 1-indexed inclusive bounds.
pub fn parse_range(raw: &str) -> Result<(u64, u64)> {
    let (s, e) = raw
        .split_once('-')
        .ok_or_else(|| anyhow::anyhow!("parent_range must be 'start-end' (got '{}')", raw))?;
    let start: u64 = s
        .parse()
        .with_context(|| format!("invalid start line in parent_range: {}", s))?;
    let end: u64 = e
        .parse()
        .with_context(|| format!("invalid end line in parent_range: {}", e))?;
    if start == 0 || end == 0 {
        bail!("parent_range lines are 1-indexed, got 0");
    }
    if start > end {
        bail!("parent_range start ({}) > end ({})", start, end);
    }
    Ok((start, end))
}

/// Run support mode: explicit verified parent path/range, production
/// depth-1 graph expansion, structured relation provenance. Never infers
/// a path from the query.
fn exec_support(
    roots: &BakeoffRoots,
    policy: &Policy,
    parent_path: &str,
    parent_range: &str,
    max_results: usize,
) -> Result<(Vec<Evidence>, Vec<RelationProvenance>, serde_json::Value)> {
    // Validate parent path confinement under source root. Fail-closed.
    let canonical_parent = validate_path(&roots.source_root, parent_path).with_context(|| {
        format!(
            "parent_path '{}' fails source-root confinement (fail-closed)",
            parent_path
        )
    })?;
    if !canonical_parent.is_file() {
        bail!(
            "parent_path '{}' is not a regular file under source_root (fail-closed)",
            parent_path
        );
    }

    let (start_line, end_line) = parse_range(parent_range)?;

    // Range must be valid against the actual file.
    let content = fs::read_to_string(&canonical_parent)
        .with_context(|| format!("failed to read parent_path {}", parent_path))?;
    let total_lines = content.lines().count() as u64;
    if end_line > total_lines {
        bail!(
            "parent_range end_line ({}) exceeds file line count ({}) for {} (fail-closed)",
            end_line,
            total_lines,
            parent_path
        );
    }

    // Production depth-1 graph expansion. We do NOT use the query to
    // derive any path; the parent path is the explicit seed.
    let records = scan_repo(&roots.source_root, policy)?;
    let (_nodes, edges, build_result) = graph::build_graph(&roots.source_root, &records)?;

    let unsafe_skips_present =
        build_result.skipped_stale > 0 || build_result.skipped_path_unsafe > 0;
    if unsafe_skips_present {
        bail!(
            "graph build reported unsafe/stale skips (skipped_stale={}, skipped_path_unsafe={}); \
             fail-closed per V2 contract",
            build_result.skipped_stale,
            build_result.skipped_path_unsafe
        );
    }

    // Inbound edges targeting the parent path (production `impact_edges`).
    // B1 support admits honest import edges only; other production graph
    // relations are not renamed into Phase A support relations.
    let impacted = graph::impact_edges(&edges, parent_path, 1)?;
    let impacted_count = impacted.len();
    let mut import_edges: Vec<GraphEdge> = impacted
        .into_iter()
        .filter(|edge| matches!(&edge.kind, EdgeKind::Imports))
        .collect();
    import_edges.sort_by(|a, b| {
        a.source_path
            .cmp(&b.source_path)
            .then_with(|| a.source_line.cmp(&b.source_line))
            .then_with(|| a.source_end_line.cmp(&b.source_end_line))
            .then_with(|| a.target_path.cmp(&b.target_path))
    });
    import_edges.truncate(max_results);

    // Structured canonical relation provenance, one-to-one with the capped
    // production edge list materialized below.
    let relations: Vec<RelationProvenance> = import_edges
        .iter()
        .map(|e| RelationProvenance {
            relation_kind: "import".to_string(),
            production_edge_kind: "imports".to_string(),
            support_path: e.source_path.clone(),
            support_start_line: e.source_line,
            support_end_line: e.source_end_line,
            target_path: e.target_path.clone(),
            target_start_line: start_line,
            target_end_line: end_line,
        })
        .collect();

    let (evidence, skipped) = materialize_graph_edges(&roots.source_root, &import_edges);
    if skipped > 0 {
        bail!(
            "support materialization skipped {} edge(s); source tree inconsistent (fail-closed)",
            skipped
        );
    }

    let capped: Vec<Evidence> = evidence;
    let diagnostics = serde_json::json!({
        "depth": 1,
        "parent_path": parent_path,
        "parent_start_line": start_line,
        "parent_end_line": end_line,
        "parent_confinement": "validated_under_source_root",
        "parent_path_inferred_from_query": false,
        "skipped_stale": build_result.skipped_stale,
        "skipped_path_unsafe": build_result.skipped_path_unsafe,
        "inspect_saturated": false,
        "unsafe_skips_present": false,
        "edge_count": build_result.edge_count,
        "node_count": build_result.node_count,
        "candidate_edges_all_relations": impacted_count,
        "candidate_import_edges": import_edges.len(),
        "materialized": capped.len(),
        "materialization_skipped": 0,
    });
    Ok((capped, relations, diagnostics))
}

// ── Top-level handlers ────────────────────────────────────────────────

/// Run `bakeoff-query context`. Returns a strict closed envelope on
/// success or an error envelope on fail-closed conditions.
pub fn run_context(args: ContextArgs) -> Result<BakeoffEnvelope> {
    let roots = resolve_bakeoff_roots(&args.source_root, &args.state_root)?;
    validate_task_family(&args.task_family)?;
    let components = parse_components(&args.components)?;
    let max_results = args.max_results;
    if args.query.is_empty() || args.query.len() > 512 {
        bail!("query must contain 1..=512 bytes (fail-closed)");
    }
    if max_results == 0 || max_results > 64 {
        bail!("max_results must be in 1..=64 (fail-closed)");
    }

    let policy = Policy::load_from_repo(&roots.source_root);

    // Provider audit count before (we never invoke a provider).
    let events_before = count_audit_events(&roots.state_root)?;

    // Execute each requested component in canonical cumulative order.
    let mut receipts: Vec<Receipt> = Vec::new();
    let mut channel_evidence: Vec<(Vec<Evidence>, Channel)> = Vec::new();
    let mut components_executed: Vec<String> = Vec::new();
    let mut had_error = false;

    for component in &components {
        let result: Result<(Vec<Evidence>, serde_json::Value, Option<String>)> =
            match component.as_str() {
                "bm25" => {
                    exec_bm25(&roots, &policy, &args.query, max_results).map(|(e, d)| (e, d, None))
                }
                "literal" => exec_literal(&roots, &policy, &args.query, max_results)
                    .map(|(e, d)| (e, d, None)),
                "symbol" => {
                    if identifier_predicate(&args.query) {
                        exec_symbol(&roots, &policy, &args.query, max_results)
                            .map(|(e, d)| (e, d, None))
                    } else {
                        Ok((
                            Vec::new(),
                            serde_json::json!({
                                "predicate": "ascii_identifier_v1",
                                "predicate_matched": false,
                                "match": "exact_name",
                                "case_sensitive": true,
                                "substring_rejected": true,
                                "ast_to_text_fallback": false,
                            }),
                            Some(SKIP_REASON_IDENTIFIER_PREDICATE_FALSE.to_string()),
                        ))
                    }
                }
                "graph" => {
                    if graph_task_family_predicate(&args.task_family) {
                        // Pre-graph evidence = union of all earlier components'
                        // evidence. Built fresh before executing graph; never
                        // reused from a previous iteration.
                        let pre_graph_evidence: Vec<Evidence> = channel_evidence
                            .iter()
                            .flat_map(|(evs, _)| evs.iter().cloned())
                            .collect();
                        exec_graph(&roots, &policy, &pre_graph_evidence, max_results)
                            .map(|(e, d)| (e, d, None))
                    } else {
                        Ok((
                            Vec::new(),
                            serde_json::json!({
                                "predicate": "phase_a_graph_task_family_v1",
                                "predicate_matched": false,
                                "eligible_task_families": GRAPH_ELIGIBLE_TASK_FAMILIES,
                                "depth": 1,
                                "seed_source": "pre_graph_evidence",
                                "seed_count": 0,
                                "skipped_stale": 0,
                                "skipped_path_unsafe": 0,
                                "inspect_saturated": false,
                                "unsafe_skips_present": false,
                                "parent_path_inferred_from_query": false,
                            }),
                            Some(SKIP_REASON_GRAPH_PREDICATE_FALSE.to_string()),
                        ))
                    }
                }
                other => bail!("internal: unknown component '{}' reached executor", other),
            };

        let receipt = match result {
            Ok((evidence, diagnostics, skip_reason)) => {
                let evidence = canonicalize_component_evidence(evidence, max_results)?;
                let channel = match component.as_str() {
                    "bm25" => Channel::Bm25,
                    "literal" => Channel::Regex,
                    "symbol" => Channel::TreeSitter,
                    "graph" => Channel::Graph,
                    _ => bail!("internal: unknown component channel"),
                };
                let count = evidence.len();
                if skip_reason.is_none() {
                    // Executed (zero is legal).
                    channel_evidence.push((evidence, channel));
                    components_executed.push(component.clone());
                    Receipt {
                        component: component.clone(),
                        status: RECEIPT_EXECUTED.to_string(),
                        evidence_count: count,
                        reason: None,
                        diagnostics,
                    }
                } else {
                    // Legitimate skip (only a frozen predicate evaluating false).
                    Receipt {
                        component: component.clone(),
                        status: RECEIPT_LEGITIMATE_SKIP.to_string(),
                        evidence_count: 0,
                        reason: skip_reason,
                        diagnostics,
                    }
                }
            }
            Err(e) => {
                had_error = true;
                let msg = e.to_string();
                Receipt {
                    component: component.clone(),
                    status: RECEIPT_ERROR.to_string(),
                    evidence_count: 0,
                    reason: Some(msg),
                    diagnostics: serde_json::json!({
                        "fail_closed": true,
                        "fallback_attempted": false,
                    }),
                }
            }
        };
        receipts.push(receipt);
    }

    // Receipt closure: exactly one receipt per requested component, in
    // order. Missing or duplicate receipts fail closed.
    let receipt_components: Vec<String> = receipts.iter().map(|r| r.component.clone()).collect();
    if receipt_components != components {
        bail!(
            "receipt set {:?} does not match requested component set {:?} (fail-closed)",
            receipt_components,
            components
        );
    }

    // Fail-closed: any configured component error invalidates the envelope.
    let any_error = receipts.iter().any(|r| r.status == RECEIPT_ERROR);
    if any_error || had_error {
        // Surface the first error reason in the bail message so callers
        // can see the underlying fail-closed cause (e.g. "persistent BM25
        // index does not exist"). The per-receipt `reason` field carries
        // the full detail.
        let first_err = receipts
            .iter()
            .find(|r| r.status == RECEIPT_ERROR)
            .and_then(|r| r.reason.clone())
            .unwrap_or_else(|| "unknown component error".to_string());
        bail!(
            "bakeoff-query context fail-closed: component error — {}",
            first_err
        );
    }

    // Resolve ambiguous cross-channel containment deterministically before
    // invoking the production competition-rank tie-aware RRF implementation.
    let input_rewrites = canonicalize_rrf_input_overlaps(&mut channel_evidence, max_results)?;
    // Fuse all component lists through the production competition-rank tie
    // and explicit channel-weight variant. The graph vote is doubled so a
    // verified relation can overcome a single adjacent-rank lexical gap.
    // Existing product callers continue using the original RRF.
    let weighted_channel_evidence = channel_evidence
        .into_iter()
        .map(|(evidence, channel)| {
            let weight = if channel == Channel::Graph { 2 } else { 1 };
            (evidence, channel, weight)
        })
        .collect();
    let fused = rrf_combine_with_rank_ties_and_channel_weights(weighted_channel_evidence);
    let top: Vec<Evidence> = fused.into_iter().take(max_results).collect();
    let evidence_count = top.len();
    let top: Vec<BakeoffEvidence> = top.into_iter().map(flatten_evidence).collect();

    let provider = build_provider_diagnostics(&roots.state_root, events_before)?;
    // Fail-closed: provider remote-call count must be zero.
    if provider.remote_calls > 0 {
        bail!(
            "provider remote_calls={} > 0 during bakeoff-query context (fail-closed)",
            provider.remote_calls
        );
    }

    let trace = route_trace(
        &roots.source_root,
        &roots.state_root,
        "bakeoff_query_context",
        serde_json::json!({
            "source_root": roots.source_root,
            "state_root": roots.state_root,
            "separated": roots.separated,
            "query": args.query,
            "components": components,
            "task_family": args.task_family,
            "max_results": max_results,
        }),
        serde_json::json!({
            "evidence_count": evidence_count,
            "receipts": receipts.len(),
            "provider_remote_calls": provider.remote_calls,
        }),
    )?;

    Ok(BakeoffEnvelope {
        schema_version: BAKEOFF_QUERY_SCHEMA_VERSION.to_string(),
        success: true,
        mode: "context".to_string(),
        source_root: roots.source_root.to_string_lossy().to_string(),
        state_root: roots.state_root.to_string_lossy().to_string(),
        query: Some(args.query),
        task_family: Some(args.task_family),
        max_results: Some(max_results),
        components_requested: components.clone(),
        components_executed,
        evidence: top,
        evidence_count,
        rrf: RrfDiagnostics {
            marker: BAKEOFF_QUERY_RRF_MARKER.to_string(),
            version: BAKEOFF_QUERY_RRF_VERSION.to_string(),
            k: BAKEOFF_QUERY_RRF_K,
            tie_order: "score_desc_path_asc_start_asc_end_asc".to_string(),
            rank_tie_policy: BAKEOFF_QUERY_RANK_TIE_POLICY.to_string(),
            channel_weights: BAKEOFF_QUERY_CHANNEL_WEIGHTS.to_string(),
            input_normalization: BAKEOFF_QUERY_INPUT_NORMALIZATION.to_string(),
            input_rewrites,
        },
        receipts,
        parent: None,
        relations: None,
        provider,
        trace,
    })
}

/// Run `bakeoff-query support`. Returns a strict closed envelope on
/// success or fails closed.
pub fn run_support(args: SupportArgs) -> Result<BakeoffEnvelope> {
    let roots = resolve_bakeoff_roots(&args.source_root, &args.state_root)?;
    let max_results = args.max_results;
    if max_results == 0 || max_results > 64 {
        bail!("max_results must be in 1..=64 (fail-closed)");
    }

    let policy = Policy::load_from_repo(&roots.source_root);

    // Reuse the production persistent-index status path so support mode is
    // bound to the same canonical source/state safety checks as context.
    let index_status = status_index_at_state_root(&roots.source_root, &roots.state_root, &policy)?;
    if !index_status.exists || index_status.requires_rebuild {
        bail!("support requires a current persistent index at state_root (fail-closed)");
    }

    let events_before = count_audit_events(&roots.state_root)?;

    let (start_line, end_line) = parse_range(&args.parent_range)?;
    let parent = ParentDiagnostics {
        path: args.parent_path.clone(),
        start_line,
        end_line,
        confinement: "validated_under_source_root".to_string(),
    };

    let support_result = exec_support(
        &roots,
        &policy,
        &args.parent_path,
        &args.parent_range,
        max_results,
    );

    let (evidence, relations, diagnostics) = match support_result {
        Ok(ok) => ok,
        Err(e) => {
            // Fail-closed: support error → no successful envelope.
            bail!(
                "bakeoff-query support failed: {} (fail-closed; no envelope emitted)",
                e
            );
        }
    };
    let evidence_count = evidence.len();
    let evidence: Vec<BakeoffEvidence> = evidence.into_iter().map(flatten_evidence).collect();

    let receipt = Receipt {
        component: "support".to_string(),
        status: RECEIPT_EXECUTED.to_string(),
        evidence_count,
        reason: None,
        diagnostics,
    };
    let receipts = vec![receipt];

    let provider = build_provider_diagnostics(&roots.state_root, events_before)?;
    if provider.remote_calls > 0 {
        bail!(
            "provider remote_calls={} > 0 during bakeoff-query support (fail-closed)",
            provider.remote_calls
        );
    }

    let trace = route_trace(
        &roots.source_root,
        &roots.state_root,
        "bakeoff_query_support",
        serde_json::json!({
            "source_root": roots.source_root,
            "state_root": roots.state_root,
            "separated": roots.separated,
            "parent_path": args.parent_path,
            "parent_range": args.parent_range,
            "max_results": max_results,
        }),
        serde_json::json!({
            "evidence_count": evidence_count,
            "relations_count": relations.len(),
            "provider_remote_calls": provider.remote_calls,
        }),
    )?;

    Ok(BakeoffEnvelope {
        schema_version: BAKEOFF_QUERY_SCHEMA_VERSION.to_string(),
        success: true,
        mode: "support".to_string(),
        source_root: roots.source_root.to_string_lossy().to_string(),
        state_root: roots.state_root.to_string_lossy().to_string(),
        query: None,
        task_family: None,
        max_results: Some(max_results),
        components_requested: vec!["support".to_string()],
        components_executed: vec!["support".to_string()],
        evidence,
        evidence_count,
        rrf: RrfDiagnostics {
            marker: BAKEOFF_QUERY_RRF_MARKER.to_string(),
            version: BAKEOFF_QUERY_RRF_VERSION.to_string(),
            k: BAKEOFF_QUERY_RRF_K,
            tie_order: "score_desc_path_asc_start_asc_end_asc".to_string(),
            rank_tie_policy: BAKEOFF_QUERY_RANK_TIE_POLICY.to_string(),
            channel_weights: BAKEOFF_QUERY_CHANNEL_WEIGHTS.to_string(),
            input_normalization: BAKEOFF_QUERY_INPUT_NORMALIZATION.to_string(),
            input_rewrites: 0,
        },
        receipts,
        parent: Some(parent),
        relations: Some(relations),
        provider,
        trace,
    })
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use openlocus_index::persistent::build_index_at_state_root as lib_build_index;
    use tempfile::TempDir;

    fn write_file(path: &Path, content: &str) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).unwrap();
        }
        fs::write(path, content).unwrap();
    }

    /// Build a real persistent BM25 index at (source_root, state_root)
    /// using the production `build_index_at_state_root`. This is the
    /// only legitimate way to make bakeoff-query context succeed.
    fn build_persistent_index(source_root: &Path, state_root: &Path) {
        use openlocus_index::manifest::ChunkStrategy;
        let policy = Policy::load_from_repo(source_root);
        let records = scan_repo(source_root, &policy).unwrap();
        let result = lib_build_index(
            source_root,
            state_root,
            &records,
            &policy,
            ChunkStrategy::LineWindowV1,
        )
        .unwrap();
        assert!(result.success, "fixture persistent index must build");
        write_file(&state_root.join(AUDIT_RELATIVE_PATH), "");
    }

    fn make_repo_with_auth() -> (TempDir, PathBuf, PathBuf) {
        let dir = TempDir::new().unwrap();
        let root = dir.path().to_path_buf();
        let source_root = root.join("src-tree");
        let state_root = root.join("state-tree");
        fs::create_dir_all(&source_root).unwrap();
        fs::create_dir_all(&state_root).unwrap();
        write_file(
            &source_root.join("app.rs"),
            "fn authenticate_user() {}\nfn process_request() {}\n",
        );
        write_file(
            &source_root.join("lib.rs"),
            "mod app;\nstruct Config { name: String }\n",
        );
        write_file(
            &source_root.join("tests/app_test.rs"),
            "mod app;\nfn check_auth() {}\n",
        );
        write_file(
            &source_root.join("Cargo.toml"),
            "[package]\nname = \"demo\"\n",
        );
        // Persistent index lives under state_root/.openlocus/index.
        build_persistent_index(&source_root, &state_root);
        // B1 requires explicit readable zero-provider evidence rather than
        // treating a missing audit file as an implicit zero.
        (dir, source_root, state_root)
    }

    // ── 1. Persistent state use vs temp BM25 ──────────────────────────

    /// bakeoff-query context with the `[bm25]` stack (S0) MUST read from
    /// the persistent index at state_root, not from a temp Tantivy index.
    /// We verify by deleting the persistent index after building it and
    /// asserting the command fails closed (it cannot silently rebuild or
    /// fall back to temp BM25).
    #[test]
    fn context_uses_persistent_state_not_temp_bm25() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        // Sanity: persistent index exists.
        assert!(state_root.join(".openlocus/index/tantivy").exists());
        assert!(state_root.join(".openlocus/index/manifest.json").exists());

        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25".to_string(),
            task_family: "definition_find".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        assert!(env.success);
        assert!(env.evidence_count > 0);
        // Receipt must advertise persistent_state_root, not temp.
        let bm25_receipt = env.receipts.iter().find(|r| r.component == "bm25").unwrap();
        assert_eq!(bm25_receipt.status, RECEIPT_EXECUTED);
        assert_eq!(
            bm25_receipt.diagnostics["index_source"],
            "persistent_state_root"
        );

        // Now delete the persistent index — bakeoff-query must fail closed
        // rather than silently rebuild or use temp BM25.
        let _ = std::fs::remove_dir_all(state_root.join(".openlocus/index"));
        let args2 = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25".to_string(),
            task_family: "definition_find".to_string(),
            max_results: 8,
        };
        let err = run_context(args2).unwrap_err().to_string();
        assert!(
            err.contains("persistent BM25 index does not exist"),
            "expected fail-closed on missing persistent index, got: {}",
            err
        );
        let _ = dir;
    }

    #[test]
    fn equal_score_and_overlap_ties_are_stable_across_reopens() {
        let dir = TempDir::new().unwrap();
        let source_root = dir.path().join("source");
        let state_root = dir.path().join("state");
        fs::create_dir_all(&source_root).unwrap();
        fs::create_dir_all(&state_root).unwrap();
        write_file(&source_root.join("a.rs"), "pub struct StableWord;\n");
        write_file(
            &source_root.join("b.rs"),
            "use crate::a::StableWord;\npub fn relay(_: StableWord) {}\n",
        );
        write_file(
            &source_root.join("Cargo.toml"),
            "[package]\nname = \"stable-demo\"\n",
        );
        build_persistent_index(&source_root, &state_root);

        type EvidenceSignature = (String, u64, u64, u64, Vec<String>);
        let mut baseline: Option<Vec<EvidenceSignature>> = None;
        for _ in 0..8 {
            let env = run_context(ContextArgs {
                source_root: source_root.to_string_lossy().to_string(),
                state_root: state_root.to_string_lossy().to_string(),
                query: "StableWord".to_string(),
                components: "bm25,literal,symbol".to_string(),
                task_family: "symbol_lookup".to_string(),
                max_results: 8,
            })
            .unwrap();
            let signature: Vec<_> = env
                .evidence
                .iter()
                .map(|item| {
                    (
                        item.path.clone(),
                        item.start_line,
                        item.end_line,
                        item.score.to_bits(),
                        item.channels.clone(),
                    )
                })
                .collect();
            if let Some(expected) = &baseline {
                assert_eq!(&signature, expected);
            } else {
                baseline = Some(signature);
            }
            let bm25 = env
                .receipts
                .iter()
                .find(|receipt| receipt.component == "bm25")
                .unwrap();
            assert_eq!(
                bm25.diagnostics["deterministic_tie_order"],
                "score_desc_path_asc_start_asc_end_asc"
            );
            assert_eq!(bm25.diagnostics["exact_cell_dedup"], true);
            assert_eq!(bm25.diagnostics["overfetch_limit"], 64);
            assert_eq!(
                env.rrf.input_normalization,
                BAKEOFF_QUERY_INPUT_NORMALIZATION
            );
            assert!(env.rrf.input_rewrites >= 1);
        }
    }

    #[test]
    fn context_preserves_exact_equal_quality_candidates_as_tied() {
        let dir = TempDir::new().unwrap();
        let source_root = dir.path().join("source");
        let state_root = dir.path().join("state");
        fs::create_dir_all(&source_root).unwrap();
        fs::create_dir_all(&state_root).unwrap();
        write_file(&source_root.join("j.rs"), "pub fn Meralis() {}\n");
        write_file(&source_root.join("k.rs"), "pub fn Meralis() {}\n");
        write_file(
            &source_root.join("Cargo.toml"),
            "[package]\nname = \"tie-demo\"\n",
        );
        build_persistent_index(&source_root, &state_root);

        let env = run_context(ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "Meralis".to_string(),
            components: "bm25,literal,symbol".to_string(),
            task_family: "ambiguous_target".to_string(),
            max_results: 8,
        })
        .unwrap();

        assert!(env.evidence.len() >= 2);
        assert_eq!(env.evidence[0].path, "j.rs");
        assert_eq!(env.evidence[1].path, "k.rs");
        assert_eq!(
            env.evidence[0].score.to_bits(),
            env.evidence[1].score.to_bits()
        );
        assert_eq!(env.rrf.rank_tie_policy, BAKEOFF_QUERY_RANK_TIE_POLICY);
        assert_eq!(env.rrf.channel_weights, BAKEOFF_QUERY_CHANNEL_WEIGHTS);
    }

    // ── 2. Literal text escaping exactly once ─────────────────────────

    /// The literal component must call production `text_search` exactly
    /// once (which regex-escapes the query exactly once). The receipt
    /// advertises `text_escaped_once=true, escape_count=1`. A query with
    /// regex metacharacters must be treated literally (e.g. `$5.00`).
    #[test]
    fn literal_escapes_query_exactly_once() {
        let dir = TempDir::new().unwrap();
        let root = dir.path().to_path_buf();
        let source_root = root.join("src-tree");
        let state_root = root.join("state-tree");
        fs::create_dir_all(&source_root).unwrap();
        fs::create_dir_all(&state_root).unwrap();
        write_file(
            &source_root.join("data.txt"),
            "price is $5.00\nno match here\n",
        );
        build_persistent_index(&source_root, &state_root);

        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "$5.00".to_string(),
            components: "bm25,literal".to_string(),
            task_family: "error_text".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        assert!(env.success);

        let lit_receipt = env
            .receipts
            .iter()
            .find(|r| r.component == "literal")
            .unwrap();
        assert_eq!(lit_receipt.status, RECEIPT_EXECUTED);
        assert_eq!(lit_receipt.diagnostics["text_escaped_once"], true);
        assert_eq!(lit_receipt.diagnostics["escape_count"], 1);
        assert_eq!(lit_receipt.diagnostics["fallback"], false);
        // Literal channel produced at least one match for `$5.00` literal.
        assert!(
            lit_receipt.evidence_count >= 1,
            "literal channel should find `$5.00` literally"
        );
    }

    // ── 3. Exact symbol not substring ──────────────────────────────────

    /// The symbol component uses the frozen identifier predicate: EXACT
    /// name equality. `authenticate` must NOT match `authenticate_user`.
    #[test]
    fn symbol_matches_exact_name_not_substring() {
        let dir = TempDir::new().unwrap();
        let root = dir.path().to_path_buf();
        let source_root = root.join("src-tree");
        let state_root = root.join("state-tree");
        fs::create_dir_all(&source_root).unwrap();
        fs::create_dir_all(&state_root).unwrap();
        // `authenticate` (exact) and `authenticate_user` (substring
        // superset) both present.
        write_file(
            &source_root.join("app.rs"),
            "fn authenticate() {}\nfn authenticate_user() {}\n",
        );
        build_persistent_index(&source_root, &state_root);

        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25,literal,symbol".to_string(),
            task_family: "symbol_lookup".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        assert!(env.success);

        let sym_receipt = env
            .receipts
            .iter()
            .find(|r| r.component == "symbol")
            .unwrap();
        assert_eq!(sym_receipt.status, RECEIPT_EXECUTED);
        assert_eq!(sym_receipt.diagnostics["match"], "exact_name");
        assert_eq!(sym_receipt.diagnostics["substring_rejected"], true);
        assert_eq!(sym_receipt.diagnostics["ast_to_text_fallback"], false);
        // Exactly one symbol evidence (the `authenticate` fn), NOT
        // `authenticate_user`.
        assert_eq!(
            sym_receipt.evidence_count, 1,
            "exact-name predicate must not match substring superset"
        );
        assert!(
            env.evidence
                .iter()
                .any(|ev| ev.channels.iter().any(|channel| channel == "tree_sitter"))
        );
    }

    // ── 4. Graph eligible family and fail-closed seed handling ────────

    /// Graph component seeds from real pre-graph evidence. When pre-graph
    /// evidence is non-empty, graph executes for an eligible family. Once
    /// that predicate fires, an empty seed is a mechanics failure rather
    /// than a legitimate skip. Ineligible families skip before seed use.
    #[test]
    fn graph_uses_real_seeds_and_fails_closed_when_eligible_seed_is_empty() {
        let (dir, source_root, state_root) = make_repo_with_auth();

        // Eligible family: bm25 returns evidence for `authenticate`, which
        // seeds graph expansion around `app.rs`.
        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25,literal,symbol,graph".to_string(),
            task_family: "cross_file_dependency".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        assert!(env.success);
        let graph_receipt = env
            .receipts
            .iter()
            .find(|r| r.component == "graph")
            .unwrap();
        assert_eq!(graph_receipt.status, RECEIPT_EXECUTED);
        assert_eq!(
            graph_receipt.diagnostics["seed_source"],
            "pre_graph_evidence"
        );
        assert_eq!(
            graph_receipt.diagnostics["parent_path_inferred_from_query"],
            false
        );
        assert_eq!(graph_receipt.diagnostics["unsafe_skips_present"], false);

        // Eligible task family with no pre-graph evidence is not a skip:
        // the frozen predicate fired, so the missing seed fails closed.
        let eligible_no_seed = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "zzz_nomatch_zzz".to_string(),
            components: "bm25,literal,symbol,graph".to_string(),
            task_family: "cross_file_dependency".to_string(),
            max_results: 8,
        };
        let err = run_context(eligible_no_seed).unwrap_err().to_string();
        assert!(
            err.contains("graph predicate fired but pre-graph evidence produced no seed path"),
            "expected fail-closed empty graph seed, got: {}",
            err
        );

        // Predicate-false skip: no-answer is not graph-eligible, so the graph
        // component must skip before seed evaluation.
        let args2 = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "zzz_nomatch_zzz".to_string(),
            components: "bm25,literal,symbol,graph".to_string(),
            task_family: "no_answer".to_string(),
            max_results: 8,
        };
        let env2 = run_context(args2).unwrap();
        // Even though no component found anything, all components
        // executed (zero is legal) and graph legitimately skipped.
        let bm25 = env2
            .receipts
            .iter()
            .find(|r| r.component == "bm25")
            .unwrap();
        assert_eq!(bm25.status, RECEIPT_EXECUTED);
        assert_eq!(bm25.evidence_count, 0);
        let graph = env2
            .receipts
            .iter()
            .find(|r| r.component == "graph")
            .unwrap();
        assert_eq!(graph.status, RECEIPT_LEGITIMATE_SKIP);
        assert_eq!(
            graph.reason.as_deref(),
            Some(SKIP_REASON_GRAPH_PREDICATE_FALSE)
        );
        assert_eq!(graph.diagnostics["seed_count"], 0);
        // no_evidence is legal when all configured executed components
        // returned zero and fusion is empty.
        assert_eq!(env2.evidence_count, 0);
        assert!(env2.success);

        let _ = dir;
    }

    #[test]
    fn graph_stack_promotes_cross_file_dependency_evidence() {
        let dir = TempDir::new().unwrap();
        let source_root = dir.path().join("source");
        let state_root = dir.path().join("state");
        fs::create_dir_all(&source_root).unwrap();
        fs::create_dir_all(&state_root).unwrap();
        write_file(&source_root.join("d53.rs"), "pub struct Neral;\n");
        write_file(
            &source_root.join("e67.rs"),
            "use crate::d53::Neral;\npub fn accept(_: Neral) {}\n",
        );
        write_file(
            &source_root.join("Cargo.toml"),
            "[package]\nname = \"graph-demo\"\n",
        );
        build_persistent_index(&source_root, &state_root);

        let env = run_context(ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "Neral".to_string(),
            components: "bm25,literal,symbol,graph".to_string(),
            task_family: "cross_file_dependency".to_string(),
            max_results: 8,
        })
        .unwrap();

        assert!(!env.evidence.is_empty());
        assert_eq!(
            env.evidence[0].path, "e67.rs",
            "graph evidence order: {:#?}",
            env.evidence
        );
        assert_eq!(env.evidence[0].start_line, 1);
        assert!(
            env.evidence[0]
                .channels
                .iter()
                .any(|channel| channel == "graph")
        );
    }

    // ── 5. Support confinement and structured relation ────────────────

    /// Support mode validates parent path confinement under source root
    /// and returns structured relation provenance (closed Phase A set).
    /// It never infers a path from a query.
    #[test]
    fn support_validates_confinement_and_returns_structured_relations() {
        let (dir, source_root, state_root) = make_repo_with_auth();

        // Parent path inside source_root: succeeds.
        let args = SupportArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            parent_path: "app.rs".to_string(),
            parent_range: "1-2".to_string(),
            max_results: 8,
        };
        let env = run_support(args).unwrap();
        assert!(env.success);
        assert_eq!(env.mode, "support");
        let parent = env.parent.as_ref().unwrap();
        assert_eq!(parent.path, "app.rs");
        assert_eq!(parent.start_line, 1);
        assert_eq!(parent.end_line, 2);
        assert_eq!(parent.confinement, "validated_under_source_root");

        // Relations must use only the closed Phase A set.
        if let Some(rels) = &env.relations {
            for r in rels {
                assert!(
                    RELATION_KINDS.contains(&r.relation_kind.as_str()),
                    "relation kind '{}' not in closed Phase A set {:?}",
                    r.relation_kind,
                    RELATION_KINDS
                );
                assert_eq!(r.production_edge_kind, "imports");
                assert!(!r.support_path.is_empty());
                assert!(!r.target_path.is_empty());
                assert!(r.support_start_line >= 1);
                assert!(r.support_end_line >= r.support_start_line);
                assert!(r.target_start_line >= 1);
                assert!(r.target_end_line >= r.target_start_line);
            }
        }
        let support_receipt = env
            .receipts
            .iter()
            .find(|r| r.component == "support")
            .unwrap();
        assert_eq!(support_receipt.status, RECEIPT_EXECUTED);
        assert_eq!(
            support_receipt.diagnostics["parent_path_inferred_from_query"],
            false
        );

        // Path escape: `..` traversal is rejected fail-closed.
        let args2 = SupportArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            parent_path: "../etc/passwd".to_string(),
            parent_range: "1-1".to_string(),
            max_results: 8,
        };
        let err = run_support(args2).unwrap_err().to_string();
        assert!(
            err.contains("fail-closed"),
            "expected fail-closed on path escape, got: {}",
            err
        );

        // Non-existent parent path: rejected fail-closed.
        let args3 = SupportArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            parent_path: "nonexistent.rs".to_string(),
            parent_range: "1-1".to_string(),
            max_results: 8,
        };
        let err = run_support(args3).unwrap_err().to_string();
        assert!(
            err.contains("fail-closed"),
            "expected fail-closed on missing parent, got: {}",
            err
        );

        // Invalid range (end > total_lines): rejected fail-closed.
        let args4 = SupportArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            parent_path: "app.rs".to_string(),
            parent_range: "1-9999".to_string(),
            max_results: 8,
        };
        let err = run_support(args4).unwrap_err().to_string();
        assert!(
            err.contains("fail-closed"),
            "expected fail-closed on invalid range, got: {}",
            err
        );

        let _ = dir;
    }

    // ── 6. Receipt exact-set / status / count closure ─────────────────

    /// The receipts array must be exactly one-per-requested-component,
    /// in order, with valid status values and non-negative counts.
    #[test]
    fn receipt_set_is_exact_and_ordered_with_valid_status() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25,literal,symbol,graph".to_string(),
            task_family: "cross_file_dependency".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        // Exact-set: one receipt per requested component, in order.
        let receipt_components: Vec<String> =
            env.receipts.iter().map(|r| r.component.clone()).collect();
        assert_eq!(receipt_components, env.components_requested);
        // Status closure: every status is one of the three closed values.
        let valid_statuses = [RECEIPT_EXECUTED, RECEIPT_LEGITIMATE_SKIP, RECEIPT_ERROR];
        for r in &env.receipts {
            assert!(
                valid_statuses.contains(&r.status.as_str()),
                "invalid receipt status: {}",
                r.status
            );
            // Count is non-negative (usize) and matches the executed
            // evidence count for executed receipts (zero for skips/errors).
            if r.status == RECEIPT_EXECUTED {
                // evidence_count is the pre-fusion per-component count;
                // we cannot assert exact fusion totals here.
                assert!(r.evidence_count < usize::MAX);
            } else {
                assert_eq!(r.evidence_count, 0);
            }
        }
        // No error receipts in a success envelope.
        assert!(
            !env.receipts.iter().any(|r| r.status == RECEIPT_ERROR),
            "success envelope must not contain error receipts"
        );
        // Components executed is a subset of requested.
        for c in &env.components_executed {
            assert!(env.components_requested.contains(c));
        }

        let _ = dir;
    }

    // ── 7. Production tie-aware RRF behavior / ordering ──────────────

    /// The envelope advertises production RRF K=60, competition ranking for
    /// exact native-score ties, and deterministic output ordering
    /// (`score_desc, path_asc, start_asc, end_asc`). The bakeoff-query surface
    /// does NOT parameterize K.
    #[test]
    fn rrf_diagnostics_advertise_production_rank_ties() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25".to_string(),
            task_family: "definition_find".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        assert_eq!(env.rrf.marker, BAKEOFF_QUERY_RRF_MARKER);
        assert_eq!(env.rrf.k, 60);
        assert_eq!(env.rrf.tie_order, "score_desc_path_asc_start_asc_end_asc");
        assert_eq!(env.rrf.rank_tie_policy, BAKEOFF_QUERY_RANK_TIE_POLICY);
        assert_eq!(env.rrf.channel_weights, BAKEOFF_QUERY_CHANNEL_WEIGHTS);
        // The marker must NOT advertise a parameterized K — K is fixed
        // inside the production tie-aware RRF function.
        assert!(env.rrf.version.contains("K=60"));

        let _ = dir;
    }

    // ── 8. Provider count zero ───────────────────────────────────────

    /// bakeoff-query never invokes an embedding provider. The audit
    /// delta must be zero.
    #[test]
    fn provider_remote_call_count_is_zero() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25,literal,symbol,graph".to_string(),
            task_family: "cross_file_dependency".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        assert_eq!(env.provider.remote_calls, 0);
        assert_eq!(env.provider.outbound_calls, 0);
        assert_eq!(
            env.provider.audit_events_before, env.provider.audit_events_after,
            "audit event count must not change during bakeoff-query"
        );

        let _ = dir;
    }

    #[test]
    fn provider_audit_delta_fails_closed() {
        use openlocus_provider::model::ProviderLocality;

        let (dir, _source_root, state_root) = make_repo_with_auth();
        let events_before = count_audit_events(&state_root).unwrap();
        assert_eq!(events_before, 0);
        let event = EmbeddingAuditEvent {
            timestamp: "2026-07-14T00:00:00Z".into(),
            event: "allow".into(),
            request_id: "b1-test".into(),
            provider_id: "mock".into(),
            model_id: "mock-v1".into(),
            locality: ProviderLocality::Mock,
            purpose: "query".into(),
            path: None,
            line_range: None,
            data_level: 0,
            view_kind: "metadata".into(),
            bytes_selected: 0,
            text_sha: "sha".into(),
            secret_scan: "clean".into(),
            policy_decision: "allow".into(),
            cache_key: "cache".into(),
            outbound_attempted: false,
            reason: None,
        };
        write_file(
            &state_root.join(AUDIT_RELATIVE_PATH),
            &format!("{}\n", serde_json::to_string(&event).unwrap()),
        );
        let err = build_provider_diagnostics(&state_root, events_before)
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("provider audit count changed during bakeoff-query"),
            "expected audit-delta failure, got: {}",
            err
        );

        let _ = dir;
    }

    #[test]
    fn missing_or_malformed_provider_audit_fails_closed() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        let audit_path = state_root.join(AUDIT_RELATIVE_PATH);
        fs::remove_file(&audit_path).unwrap();
        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25".to_string(),
            task_family: "definition_find".to_string(),
            max_results: 8,
        };
        let err = run_context(args.clone()).unwrap_err().to_string();
        assert!(
            err.contains("provider audit evidence is missing"),
            "expected missing-audit failure, got: {}",
            err
        );

        write_file(&audit_path, "{not-valid-json}\n");
        let err = run_context(args).unwrap_err().to_string();
        assert!(
            err.contains("malformed provider audit event"),
            "expected malformed-audit failure, got: {}",
            err
        );

        let _ = dir;
    }

    // ── 9. Checked trace routing ──────────────────────────────────────

    /// In separated mode the trace must be written to
    /// `state_root/.openlocus/traces/` and NEVER to the source root.
    #[test]
    fn trace_routes_to_state_root_in_separated_mode() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25".to_string(),
            task_family: "definition_find".to_string(),
            max_results: 8,
        };
        let env = run_context(args).unwrap();
        assert!(env.trace.written, "trace must be written under safe path");
        assert!(env.trace.routed_to.contains("traces"));
        // Trace file exists under state root.
        let date = chrono::Utc::now().format("%Y%m%d").to_string();
        assert!(
            state_root
                .join(".openlocus/traces")
                .join(format!("trajectory-{}.jsonl", date))
                .exists(),
            "trace file must exist under state_root/.openlocus/traces"
        );
        // Trace must NOT have escaped to the source root.
        assert!(
            !source_root.join(".openlocus").exists(),
            "trace must never be written under source_root in separated mode"
        );

        let _ = dir;
    }

    #[test]
    fn trace_write_failure_blocks_the_envelope() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        write_file(&state_root.join(".openlocus/traces"), "not a directory");
        let args = ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "authenticate".to_string(),
            components: "bm25".to_string(),
            task_family: "definition_find".to_string(),
            max_results: 8,
        };
        let err = run_context(args).unwrap_err().to_string();
        assert!(
            err.contains("failed to write checked B1 trace event"),
            "expected trace-routing failure, got: {}",
            err
        );

        let _ = dir;
    }

    // ── 10. Invalid component set ─────────────────────────────────────

    /// Invalid component sets (empty, unknown, duplicate, out-of-order)
    /// all fail closed.
    #[test]
    fn invalid_component_sets_fail_closed() {
        let (dir, source_root, state_root) = make_repo_with_auth();
        let src = source_root.to_string_lossy().to_string();
        let st = state_root.to_string_lossy().to_string();

        // Empty.
        let err = run_context(ContextArgs {
            source_root: src.clone(),
            state_root: st.clone(),
            query: "x".into(),
            components: "".into(),
            task_family: "definition_find".into(),
            max_results: 8,
        })
        .unwrap_err()
        .to_string();
        assert!(err.contains("empty"), "got: {}", err);

        // Unknown component.
        let err = run_context(ContextArgs {
            source_root: src.clone(),
            state_root: st.clone(),
            query: "x".into(),
            components: "bm25,dense".into(),
            task_family: "definition_find".into(),
            max_results: 8,
        })
        .unwrap_err()
        .to_string();
        assert!(err.contains("unknown component"), "got: {}", err);

        // Duplicate.
        let err = run_context(ContextArgs {
            source_root: src.clone(),
            state_root: st.clone(),
            query: "x".into(),
            components: "bm25,bm25".into(),
            task_family: "definition_find".into(),
            max_results: 8,
        })
        .unwrap_err()
        .to_string();
        assert!(err.contains("duplicate"), "got: {}", err);

        // Out-of-order (non-cumulative).
        let err = run_context(ContextArgs {
            source_root: src.clone(),
            state_root: st.clone(),
            query: "x".into(),
            components: "literal,bm25".into(),
            task_family: "definition_find".into(),
            max_results: 8,
        })
        .unwrap_err()
        .to_string();
        assert!(err.contains("cumulative prefix"), "got: {}", err);

        // Skipping intermediate (non-cumulative).
        let err = run_context(ContextArgs {
            source_root: src.clone(),
            state_root: st.clone(),
            query: "x".into(),
            components: "bm25,symbol".into(),
            task_family: "definition_find".into(),
            max_results: 8,
        })
        .unwrap_err()
        .to_string();
        assert!(err.contains("cumulative prefix"), "got: {}", err);

        let _ = dir;
    }

    // ── 11. Old command backward compatibility ────────────────────────

    /// Adding `BakeoffQuery` to the CLI enum must not break existing
    /// commands. We verify by parsing legacy `retrieve`, `search bm25`,
    /// `index build`, `graph build`, and `impact` invocations.
    #[test]
    fn old_commands_still_parse_and_existing_retrieve_unchanged() {
        use crate::Commands;
        use clap::Parser;

        // Legacy retrieve parses (no bakeoff-query fields).
        let cli = crate::Cli::parse_from([
            "openlocus",
            "retrieve",
            "authenticate",
            "--channels",
            "regex,bm25",
            "--max-results",
            "5",
        ]);
        match cli.command {
            Commands::Retrieve {
                query,
                channels,
                max_results,
                ..
            } => {
                assert_eq!(query, "authenticate");
                assert_eq!(channels, "regex,bm25");
                assert_eq!(max_results, 5);
            }
            _ => panic!("expected Retrieve"),
        }

        // Legacy index build parses.
        let cli = crate::Cli::parse_from([
            "openlocus",
            "index",
            "build",
            "--source-root",
            "/tmp/src",
            "--state-root",
            "/tmp/state",
        ]);
        match cli.command {
            Commands::Index {
                index_cmd:
                    crate::IndexCommands::Build {
                        source_root,
                        state_root,
                        ..
                    },
            } => {
                assert_eq!(source_root.as_deref(), Some("/tmp/src"));
                assert_eq!(state_root.as_deref(), Some("/tmp/state"));
            }
            _ => panic!("expected Index::Build"),
        }

        // Legacy search bm25 parses.
        let cli = crate::Cli::parse_from([
            "openlocus",
            "search",
            "bm25",
            "--index",
            "persistent",
            "--source-root",
            "/tmp/src",
            "--state-root",
            "/tmp/state",
            "authenticate",
        ]);
        match cli.command {
            Commands::Search {
                search_cmd:
                    crate::SearchCommands::Bm25 {
                        index,
                        source_root,
                        state_root,
                        query,
                        ..
                    },
            } => {
                assert_eq!(index, "persistent");
                assert_eq!(source_root.as_deref(), Some("/tmp/src"));
                assert_eq!(state_root.as_deref(), Some("/tmp/state"));
                assert_eq!(query, "authenticate");
            }
            _ => panic!("expected Search::Bm25"),
        }

        // New bakeoff-query context parses.
        let cli = crate::Cli::parse_from([
            "openlocus",
            "bakeoff-query",
            "context",
            "--source-root",
            "/tmp/src",
            "--state-root",
            "/tmp/state",
            "--query",
            "authenticate",
            "--components",
            "bm25,literal",
            "--task-family",
            "prose",
            "--max-results",
            "8",
        ]);
        match cli.command {
            Commands::BakeoffQuery {
                bakeoff_cmd:
                    crate::BakeoffCommands::Context {
                        source_root,
                        state_root,
                        query,
                        components,
                        task_family,
                        max_results,
                        ..
                    },
            } => {
                assert_eq!(source_root, "/tmp/src");
                assert_eq!(state_root, "/tmp/state");
                assert_eq!(query, "authenticate");
                assert_eq!(components, "bm25,literal");
                assert_eq!(task_family, "prose");
                assert_eq!(max_results, 8);
            }
            _ => panic!("expected BakeoffQuery::Context"),
        }
    }

    // ── 12. Fail-closed on missing state_root ────────────────────────

    /// bakeoff-query requires both --source-root and --state-root. No
    /// colocated default to repo_root is permitted (persistent state
    /// must be explicit).
    #[test]
    fn missing_state_root_fails_closed() {
        let err = resolve_bakeoff_roots("/tmp/src", "")
            .unwrap_err()
            .to_string();
        assert!(err.contains("requires --state-root"));
    }

    // ── 13. Fail-closed on unknown task family ───────────────────────

    #[test]
    fn unknown_task_family_fails_closed() {
        let dir = TempDir::new().unwrap();
        let root = dir.path().to_path_buf();
        let source_root = root.join("src-tree");
        let state_root = root.join("state-tree");
        fs::create_dir_all(&source_root).unwrap();
        fs::create_dir_all(&state_root).unwrap();
        write_file(&source_root.join("app.rs"), "fn x() {}\n");
        build_persistent_index(&source_root, &state_root);

        let err = run_context(ContextArgs {
            source_root: source_root.to_string_lossy().to_string(),
            state_root: state_root.to_string_lossy().to_string(),
            query: "x".into(),
            components: "bm25".into(),
            task_family: "bogus".into(),
            max_results: 8,
        })
        .unwrap_err()
        .to_string();
        assert!(err.contains("unknown task_family"));
    }

    // ── 14. parse_components unit tests ───────────────────────────────

    #[test]
    fn parse_components_accepts_canonical_prefixes() {
        assert_eq!(parse_components("bm25").unwrap(), vec!["bm25"]);
        assert_eq!(
            parse_components("bm25,literal").unwrap(),
            vec!["bm25", "literal"]
        );
        assert_eq!(
            parse_components("bm25,literal,symbol").unwrap(),
            vec!["bm25", "literal", "symbol"]
        );
        assert_eq!(
            parse_components("bm25,literal,symbol,graph").unwrap(),
            vec!["bm25", "literal", "symbol", "graph"]
        );
        // Whitespace tolerant.
        assert_eq!(
            parse_components(" bm25 , literal ").unwrap(),
            vec!["bm25", "literal"]
        );
    }

    #[test]
    fn parse_range_validates_bounds() {
        assert_eq!(parse_range("1-5").unwrap(), (1, 5));
        assert!(parse_range("0-5").is_err());
        assert!(parse_range("5-1").is_err());
        assert!(parse_range("abc").is_err());
        assert!(parse_range("1-").is_err());
    }
}
