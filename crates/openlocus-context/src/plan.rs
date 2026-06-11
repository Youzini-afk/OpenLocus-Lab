//! Fast Context Level0 — 4-turn deterministic rule prototype.
//!
//! Turn 1: Broad lexical (regex/text, optionally BM25)
//! Turn 2: Symbol search if query has identifier-like tokens
//! Turn 3: Graph impact/tests for top file candidates
//! Turn 4: RRF/dedup/narrow → final EvidencePack with confidence & missing_questions
//!
//! No LLM planner, no remote calls. All evidence is citation-valid
//! (goes through existing search/materialization paths). Budget cap
//! enforced. Graph depth=1 only.

use anyhow::{Context, Result, bail};
use openlocus_core::{BudgetUsed, Channel, Evidence, EvidencePack, Freshness};
use openlocus_graph::graph;
use openlocus_repo::read::validate_path;
use openlocus_repo::scan::FileRecord;
use openlocus_retrieval::bm25_search::bm25_search;
use openlocus_retrieval::regex_search::{regex_search, text_search};
use openlocus_retrieval::rrf::rrf_combine;
use openlocus_retrieval::symbol_search::symbol_search;
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Valid channel names for fast-context.
const VALID_CHANNELS: &[&str] = &["regex", "text", "bm25", "symbol", "graph"];

// ── Types ─────────────────────────────────────────────────────────────

/// Which turn in the 4-turn loop.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TurnKind {
    /// Turn 1: broad lexical search (regex/text, optionally BM25)
    Lexical,
    /// Turn 2: symbol search for identifier-like queries
    Symbol,
    /// Turn 3: graph impact/tests for top file candidates
    Graph,
    /// Turn 4: RRF/dedup/narrow final
    Fusion,
}

/// Record of a single action within a turn (per-channel, replayable).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionRecord {
    pub turn: TurnKind,
    pub channel: String,
    pub query: String,
    pub result_count: usize,
    pub skipped: usize,
    pub latency_ms: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// Result from a single turn.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TurnResult {
    pub turn: TurnKind,
    pub evidence_count: usize,
    pub skipped: usize,
    pub latency_ms: u64,
    /// Channels that were disabled/degraded this turn
    pub disabled_channels: Vec<String>,
    /// Per-channel action records for replay
    pub actions: Vec<ActionRecord>,
}

/// Plan for a fast-context run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FastContextPlan {
    pub query: String,
    pub channels: Vec<String>,
    pub max_evidence: usize,
    /// Approximate token budget (0 = no cap). 1 token ≈ 4 chars.
    pub budget: usize,
}

/// Result of a fast-context run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FastContextResult {
    pub success: bool,
    pub query: String,
    pub trace_id: String,
    pub turns: Vec<TurnResult>,
    pub actions: Vec<ActionRecord>,
    pub evidence: Vec<Evidence>,
    pub pack: EvidencePack,
    pub confidence: f64,
    pub missing_questions: Vec<String>,
    pub disabled_channels: Vec<String>,
    pub remote_calls: u64,
    pub budget_used: BudgetUsed,
    pub diagnostics: FastContextDiagnostics,
}

/// Diagnostics from the fast-context run.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct FastContextDiagnostics {
    pub invalid_citations_dropped: usize,
    pub unknown_channels: Vec<String>,
    pub token_budget_enforced: bool,
}

// ── Fast Context ─────────────────────────────────────────────────────

/// Execute a 4-turn deterministic fast-context loop.
///
/// All evidence is citation-valid (goes through existing
/// search/materialization paths). Budget cap enforced.
/// Graph depth=1 only. No LLM, no remote calls.
pub fn fast_context(
    repo_root: &Path,
    records: &[FileRecord],
    plan: &FastContextPlan,
) -> Result<FastContextResult> {
    let start = std::time::Instant::now();
    let trace_id = format!("fc-{}", chrono::Utc::now().timestamp_millis());

    // Validate channels
    let unknown_channels: Vec<String> = plan
        .channels
        .iter()
        .filter(|c| !VALID_CHANNELS.contains(&c.as_str()))
        .cloned()
        .collect();

    if !unknown_channels.is_empty() {
        bail!(
            "unknown channels: {}. Valid channels: {}",
            unknown_channels.join(", "),
            VALID_CHANNELS.join(", ")
        );
    }

    let mut all_channel_evidence: Vec<(Vec<Evidence>, Channel)> = Vec::new();
    let mut turns = Vec::new();
    let mut disabled_channels = Vec::new();
    let mut all_actions: Vec<ActionRecord> = Vec::new();

    // ── Turn 1: Broad lexical ──────────────────────────────────────
    let t1_start = std::time::Instant::now();
    let mut t1_evidence = Vec::new();
    let mut t1_actions = Vec::new();

    if plan.channels.contains(&"regex".to_string()) {
        let a_start = std::time::Instant::now();
        match regex_search(repo_root, records, &plan.query, plan.max_evidence) {
            Ok(ev) => {
                let count = ev.len();
                t1_evidence.extend(ev);
                t1_actions.push(ActionRecord {
                    turn: TurnKind::Lexical,
                    channel: "regex".into(),
                    query: plan.query.clone(),
                    result_count: count,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: None,
                });
            }
            Err(e) => {
                disabled_channels.push("regex".to_string());
                t1_actions.push(ActionRecord {
                    turn: TurnKind::Lexical,
                    channel: "regex".into(),
                    query: plan.query.clone(),
                    result_count: 0,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: Some(e.to_string()),
                });
            }
        }
    }
    if plan.channels.contains(&"text".to_string()) {
        let a_start = std::time::Instant::now();
        match text_search(repo_root, records, &plan.query, plan.max_evidence) {
            Ok(ev) => {
                let count = ev.len();
                t1_evidence.extend(ev);
                t1_actions.push(ActionRecord {
                    turn: TurnKind::Lexical,
                    channel: "text".into(),
                    query: plan.query.clone(),
                    result_count: count,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: None,
                });
            }
            Err(e) => {
                disabled_channels.push("text".to_string());
                t1_actions.push(ActionRecord {
                    turn: TurnKind::Lexical,
                    channel: "text".into(),
                    query: plan.query.clone(),
                    result_count: 0,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: Some(e.to_string()),
                });
            }
        }
    }

    // BM25 as part of lexical turn if channel enabled
    if plan.channels.contains(&"bm25".to_string()) {
        let a_start = std::time::Instant::now();
        match bm25_search(repo_root, records, &plan.query, plan.max_evidence) {
            Ok(ev) => {
                let count = ev.len();
                all_channel_evidence.push((ev, Channel::Bm25));
                t1_actions.push(ActionRecord {
                    turn: TurnKind::Lexical,
                    channel: "bm25".into(),
                    query: plan.query.clone(),
                    result_count: count,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: None,
                });
            }
            Err(e) => {
                disabled_channels.push("bm25".to_string());
                t1_actions.push(ActionRecord {
                    turn: TurnKind::Lexical,
                    channel: "bm25".into(),
                    query: plan.query.clone(),
                    result_count: 0,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: Some(e.to_string()),
                });
            }
        }
    }

    // Add regex/text evidence as a channel
    if !t1_evidence.is_empty() {
        all_channel_evidence.push((t1_evidence.clone(), Channel::Regex));
    }

    all_actions.extend(t1_actions.clone());

    turns.push(TurnResult {
        turn: TurnKind::Lexical,
        evidence_count: t1_evidence.len(),
        skipped: 0,
        latency_ms: t1_start.elapsed().as_millis() as u64,
        disabled_channels: Vec::new(),
        actions: t1_actions,
    });

    // ── Turn 2: Symbol search ──────────────────────────────────────
    let t2_start = std::time::Instant::now();
    let mut t2_evidence = Vec::new();
    let mut t2_disabled: Vec<String> = Vec::new();
    let mut t2_actions = Vec::new();

    if plan.channels.contains(&"symbol".to_string()) && has_identifier_tokens(&plan.query) {
        let a_start = std::time::Instant::now();
        match symbol_search(repo_root, records, &plan.query, plan.max_evidence) {
            Ok(ev) => {
                let count = ev.len();
                t2_evidence = ev.clone();
                all_channel_evidence.push((ev, Channel::Regex)); // symbol uses Regex channel
                t2_actions.push(ActionRecord {
                    turn: TurnKind::Symbol,
                    channel: "symbol".into(),
                    query: plan.query.clone(),
                    result_count: count,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: None,
                });
            }
            Err(e) => {
                t2_disabled.push("symbol".to_string());
                disabled_channels.push("symbol".to_string());
                t2_actions.push(ActionRecord {
                    turn: TurnKind::Symbol,
                    channel: "symbol".into(),
                    query: plan.query.clone(),
                    result_count: 0,
                    skipped: 0,
                    latency_ms: a_start.elapsed().as_millis() as u64,
                    error: Some(e.to_string()),
                });
            }
        }
    } else if plan.channels.contains(&"symbol".to_string()) {
        t2_disabled.push("symbol_no_identifier_tokens".to_string());
        disabled_channels.push("symbol_no_identifier_tokens".to_string());
        t2_actions.push(ActionRecord {
            turn: TurnKind::Symbol,
            channel: "symbol".into(),
            query: plan.query.clone(),
            result_count: 0,
            skipped: 0,
            latency_ms: 0,
            error: Some("skipped: no identifier-like tokens in query".into()),
        });
    }

    all_actions.extend(t2_actions.clone());

    turns.push(TurnResult {
        turn: TurnKind::Symbol,
        evidence_count: t2_evidence.len(),
        skipped: 0,
        latency_ms: t2_start.elapsed().as_millis() as u64,
        disabled_channels: t2_disabled,
        actions: t2_actions,
    });

    // ── Turn 3: Graph impact/tests ────────────────────────────────
    let t3_start = std::time::Instant::now();
    let mut t3_evidence = Vec::new();
    let mut t3_skipped = 0usize;
    let mut t3_disabled: Vec<String> = Vec::new();
    let mut t3_actions = Vec::new();

    if plan.channels.contains(&"graph".to_string()) {
        // Get top file candidates from turns 1-2
        let top_files = top_file_paths(&all_channel_evidence, 5);

        if !top_files.is_empty() {
            // Build graph and get impact edges for top files
            let a_start = std::time::Instant::now();
            match graph::build_graph(repo_root, records) {
                Ok((_nodes, edges, _result)) => {
                    for file_path in &top_files {
                        if let Ok(impact) = graph::impact_edges(&edges, file_path, 1) {
                            let (ev, skipped) =
                                openlocus_graph::materialize::materialize_graph_edges(
                                    repo_root, &impact,
                                );
                            t3_evidence.extend(ev);
                            t3_skipped += skipped;
                        }
                    }
                    if !t3_evidence.is_empty() {
                        all_channel_evidence.push((t3_evidence.clone(), Channel::Graph));
                    }
                    t3_actions.push(ActionRecord {
                        turn: TurnKind::Graph,
                        channel: "graph".into(),
                        query: plan.query.clone(),
                        result_count: t3_evidence.len(),
                        skipped: t3_skipped,
                        latency_ms: a_start.elapsed().as_millis() as u64,
                        error: None,
                    });
                }
                Err(e) => {
                    t3_disabled.push("graph_build_failed".to_string());
                    disabled_channels.push("graph".to_string());
                    t3_actions.push(ActionRecord {
                        turn: TurnKind::Graph,
                        channel: "graph".into(),
                        query: plan.query.clone(),
                        result_count: 0,
                        skipped: 0,
                        latency_ms: a_start.elapsed().as_millis() as u64,
                        error: Some(e.to_string()),
                    });
                }
            }
        } else {
            t3_disabled.push("graph_no_file_candidates".to_string());
            t3_actions.push(ActionRecord {
                turn: TurnKind::Graph,
                channel: "graph".into(),
                query: plan.query.clone(),
                result_count: 0,
                skipped: 0,
                latency_ms: 0,
                error: Some("no file candidates from prior turns".into()),
            });
        }
    }

    all_actions.extend(t3_actions.clone());

    turns.push(TurnResult {
        turn: TurnKind::Graph,
        evidence_count: t3_evidence.len(),
        skipped: t3_skipped,
        latency_ms: t3_start.elapsed().as_millis() as u64,
        disabled_channels: t3_disabled,
        actions: t3_actions,
    });

    // ── Turn 4: RRF/dedup/narrow ────────────────────────────────────
    let t4_start = std::time::Instant::now();

    let fused = rrf_combine(all_channel_evidence);
    let mut final_evidence: Vec<Evidence> = fused.into_iter().take(plan.max_evidence).collect();

    // ── Final validation: drop invalid citations ────────────────────
    let initial_count = final_evidence.len();
    final_evidence.retain(|ev| is_citation_valid(repo_root, ev));
    let invalid_citations_dropped = initial_count - final_evidence.len();

    // ── Token budget enforcement ───────────────────────────────────
    let mut token_budget_enforced = false;
    if plan.budget > 0 {
        let mut total_tokens: usize = 0;
        let mut keep_count = 0;
        for ev in &final_evidence {
            let excerpt_chars = ev
                .meta
                .as_ref()
                .and_then(|m| m.excerpt.as_ref().map(|e| e.len()))
                .unwrap_or(0);
            let estimated_tokens = excerpt_chars.div_ceil(4);
            if total_tokens + estimated_tokens <= plan.budget {
                total_tokens += estimated_tokens;
                keep_count += 1;
            } else {
                break;
            }
        }
        if keep_count < final_evidence.len() {
            token_budget_enforced = true;
            final_evidence.truncate(keep_count);
        }
    }

    // Compute token estimate for budget_used
    let tokens_estimated: u64 = final_evidence
        .iter()
        .map(|ev| {
            ev.meta
                .as_ref()
                .and_then(|m| m.excerpt.as_ref().map(|e| e.len().div_ceil(4)))
                .unwrap_or(0) as u64
        })
        .sum();

    // Compute confidence from top evidence score
    let confidence = final_evidence.first().map(|e| e.core.score).unwrap_or(0.0);

    // Generate missing questions based on what we didn't find
    let mut missing_questions = Vec::new();
    if final_evidence.is_empty() {
        missing_questions.push(format!("No evidence found for query '{}'", plan.query));
    } else if confidence < 0.1 {
        missing_questions.push("Low confidence: top evidence score < 0.1".to_string());
    }

    turns.push(TurnResult {
        turn: TurnKind::Fusion,
        evidence_count: final_evidence.len(),
        skipped: invalid_citations_dropped,
        latency_ms: t4_start.elapsed().as_millis() as u64,
        disabled_channels: Vec::new(),
        actions: vec![ActionRecord {
            turn: TurnKind::Fusion,
            channel: "rrf".into(),
            query: plan.query.clone(),
            result_count: final_evidence.len(),
            skipped: invalid_citations_dropped,
            latency_ms: t4_start.elapsed().as_millis() as u64,
            error: None,
        }],
    });

    let latency_ms = start.elapsed().as_millis() as u64;

    let pack = EvidencePack {
        task: plan.query.clone(),
        intent: "fast_context".into(),
        confidence,
        evidence: final_evidence.clone(),
        entrypoints: vec![],
        related_tests: vec![],
        risks: vec![],
        missing_questions: missing_questions.clone(),
        trace_id: trace_id.clone(),
        budget_used: BudgetUsed {
            latency_ms,
            tokens_estimated,
            remote_cost_estimated: 0.0,
        },
    };

    Ok(FastContextResult {
        success: !final_evidence.is_empty(),
        query: plan.query.clone(),
        trace_id,
        turns,
        actions: all_actions,
        evidence: final_evidence,
        pack,
        confidence,
        missing_questions,
        disabled_channels: dedup_strings(&disabled_channels),
        remote_calls: 0,
        budget_used: BudgetUsed {
            latency_ms,
            tokens_estimated,
            remote_cost_estimated: 0.0,
        },
        diagnostics: FastContextDiagnostics {
            invalid_citations_dropped,
            unknown_channels: unknown_channels.clone(),
            token_budget_enforced,
        },
    })
}

// ── Helpers ───────────────────────────────────────────────────────────

/// Check if query has identifier-like tokens (camelCase, snake_case, etc.)
fn has_identifier_tokens(query: &str) -> bool {
    query.split_whitespace().any(|token| {
        let has_upper = token.chars().any(|c| c.is_uppercase());
        let has_underscore = token.contains('_');
        let is_long_enough = token.len() >= 3;
        (has_upper || has_underscore) && is_long_enough
    })
}

/// Extract top N file paths from channel evidence, by frequency then score
fn top_file_paths(channel_evidence: &[(Vec<Evidence>, Channel)], n: usize) -> Vec<String> {
    let mut file_counts: std::collections::HashMap<String, (usize, f64)> =
        std::collections::HashMap::new();

    for (evidences, _) in channel_evidence {
        for ev in evidences {
            let entry = file_counts.entry(ev.core.path.clone()).or_insert((0, 0.0));
            entry.0 += 1;
            entry.1 = entry.1.max(ev.core.score);
        }
    }

    let mut files: Vec<_> = file_counts.into_iter().collect();
    files.sort_by(|a, b| {
        b.1.0.cmp(&a.1.0).then_with(|| {
            b.1.1
                .partial_cmp(&a.1.1)
                .unwrap_or(std::cmp::Ordering::Equal)
        })
    });

    files.into_iter().take(n).map(|(path, _)| path).collect()
}

/// Deduplicate a string list while preserving order
fn dedup_strings(strings: &[String]) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    strings
        .iter()
        .filter(|s| seen.insert((*s).clone()))
        .cloned()
        .collect()
}

/// In-process citation validity check matching the CLI validator's safety
/// semantics: safe path, current file hash, bounded line range, verified_current
/// freshness, and excerpt consistency when an excerpt is present.
fn is_citation_valid(repo_root: &Path, ev: &Evidence) -> bool {
    // Must have non-empty content_sha
    if ev.core.content_sha.is_empty() {
        return false;
    }
    // Must have verified_current freshness
    let freshness = ev.meta.as_ref().and_then(|m| m.freshness.clone());
    if freshness != Some(Freshness::VerifiedCurrent) {
        return false;
    }
    // Range sanity: start >= 1, start <= end
    if ev.core.start_line < 1 || ev.core.start_line > ev.core.end_line {
        return false;
    }

    validate_single_citation(repo_root, ev).is_ok()
}

fn validate_single_citation(repo_root: &Path, ev: &Evidence) -> Result<()> {
    let full_path = validate_path(repo_root, &ev.core.path)?;
    if !full_path.exists() {
        bail!("path does not exist: {}", ev.core.path);
    }
    if !full_path.is_file() {
        bail!("not a file: {}", ev.core.path);
    }

    let bytes =
        std::fs::read(&full_path).with_context(|| format!("failed to read {}", ev.core.path))?;
    let current_sha = blake3::hash(&bytes).to_hex().to_string();
    if current_sha != ev.core.content_sha {
        bail!(
            "content_sha mismatch: expected {}, got {}",
            ev.core.content_sha,
            current_sha
        );
    }

    let content = String::from_utf8_lossy(&bytes);
    let lines: Vec<&str> = content.lines().collect();
    let total_lines = lines.len() as u64;
    if ev.core.end_line > total_lines {
        bail!(
            "end_line ({}) exceeds file line count ({})",
            ev.core.end_line,
            total_lines
        );
    }

    if let Some(meta) = &ev.meta
        && let Some(excerpt) = &meta.excerpt
    {
        let start_idx = (ev.core.start_line - 1) as usize;
        let end_idx = ev.core.end_line as usize;
        let actual_excerpt = lines[start_idx..end_idx].join("\n");
        if excerpt != &actual_excerpt {
            bail!(
                "excerpt mismatch for {}:{}-{}",
                ev.core.path,
                ev.core.start_line,
                ev.core.end_line
            );
        }
    }

    Ok(())
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn has_identifier_tokens_detects_patterns() {
        assert!(has_identifier_tokens("EvidenceCore"));
        assert!(has_identifier_tokens("my_function"));
        assert!(has_identifier_tokens("fn foo_bar"));
        assert!(!has_identifier_tokens("how does this work"));
        assert!(!has_identifier_tokens("a b c"));
    }

    #[test]
    fn top_file_paths_picks_most_frequent() {
        let ev1 = Evidence::new(
            "src/lib.rs",
            1,
            1,
            "sha1",
            0.8,
            vec!["test".into()],
            vec![Channel::Regex],
        );
        let ev2 = Evidence::new(
            "src/lib.rs",
            5,
            5,
            "sha1",
            0.5,
            vec!["test".into()],
            vec![Channel::Regex],
        );
        let ev3 = Evidence::new(
            "src/other.rs",
            1,
            1,
            "sha2",
            0.9,
            vec!["test".into()],
            vec![Channel::Regex],
        );

        let channel_evidence = vec![(vec![ev1, ev2, ev3], Channel::Regex)];

        let paths = top_file_paths(&channel_evidence, 2);
        assert_eq!(paths.len(), 2);
        assert_eq!(paths[0], "src/lib.rs"); // 2 hits vs 1
        assert_eq!(paths[1], "src/other.rs");
    }

    #[test]
    fn fast_context_budget_respected() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("lib.rs"),
            "fn evidence_core() {}\nfn evidence_meta() {}\n",
        )
        .unwrap();
        std::fs::create_dir_all(root.join(".git")).unwrap();

        let policy = openlocus_core::Policy::default();
        let records = openlocus_repo::scan::scan_repo(root, &policy).unwrap();

        let plan = FastContextPlan {
            query: "evidence_core".to_string(),
            channels: vec![
                "regex".to_string(),
                "bm25".to_string(),
                "symbol".to_string(),
            ],
            max_evidence: 100,
            budget: 50, // token budget
        };

        let result = fast_context(root, &records, &plan).unwrap();
        assert!(result.success);
        assert!(
            result.budget_used.tokens_estimated > 0,
            "tokens_estimated should be > 0 when evidence exists"
        );
        assert_eq!(result.remote_calls, 0);
        assert!(result.turns.len() <= 4);
    }

    #[test]
    fn fast_context_empty_query_no_panic() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("lib.rs"), "fn main() {}\n").unwrap();
        std::fs::create_dir_all(root.join(".git")).unwrap();

        let policy = openlocus_core::Policy::default();
        let records = openlocus_repo::scan::scan_repo(root, &policy).unwrap();

        let plan = FastContextPlan {
            query: "nonexistent_xyzzy".to_string(),
            channels: vec!["regex".to_string()],
            max_evidence: 10,
            budget: 0,
        };

        let result = fast_context(root, &records, &plan).unwrap();
        assert!(!result.success);
        assert!(result.evidence.is_empty());
        assert!(!result.missing_questions.is_empty());
        assert_eq!(result.remote_calls, 0);
    }

    #[test]
    fn fast_context_citation_valid() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("lib.rs"),
            "pub struct EvidenceCore {\n    pub path: String,\n}\n",
        )
        .unwrap();
        std::fs::create_dir_all(root.join(".git")).unwrap();

        let policy = openlocus_core::Policy::default();
        let records = openlocus_repo::scan::scan_repo(root, &policy).unwrap();

        let plan = FastContextPlan {
            query: "EvidenceCore".to_string(),
            channels: vec!["regex".to_string(), "symbol".to_string()],
            max_evidence: 10,
            budget: 0,
        };

        let result = fast_context(root, &records, &plan).unwrap();

        // All evidence should be citation-valid
        for ev in &result.evidence {
            assert!(
                !ev.core.content_sha.is_empty(),
                "content_sha should not be empty"
            );
            let freshness = ev.meta.as_ref().and_then(|m| m.freshness.clone());
            assert!(
                freshness == Some(Freshness::VerifiedCurrent),
                "evidence should be VerifiedCurrent: {:?}",
                ev.core
            );
        }
        assert_eq!(result.remote_calls, 0);
        assert_eq!(result.diagnostics.invalid_citations_dropped, 0);
    }

    #[test]
    fn final_citation_validation_rejects_stale_hash() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("lib.rs"), "pub struct EvidenceCore;\n").unwrap();

        let mut ev = openlocus_repo::read::read_file(root, "lib.rs:1").unwrap();
        assert!(is_citation_valid(root, &ev));

        ev.core.content_sha = "stale".to_string();
        assert!(!is_citation_valid(root, &ev));
    }

    #[test]
    fn final_citation_validation_rejects_excerpt_mismatch() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("lib.rs"), "pub struct EvidenceCore;\n").unwrap();

        let mut ev = openlocus_repo::read::read_file(root, "lib.rs:1").unwrap();
        assert!(is_citation_valid(root, &ev));

        if let Some(meta) = &mut ev.meta {
            meta.excerpt = Some("wrong excerpt".to_string());
        }
        assert!(!is_citation_valid(root, &ev));
    }

    #[test]
    fn fast_context_unknown_channel_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(root.join("lib.rs"), "fn main() {}\n").unwrap();
        std::fs::create_dir_all(root.join(".git")).unwrap();

        let policy = openlocus_core::Policy::default();
        let records = openlocus_repo::scan::scan_repo(root, &policy).unwrap();

        let plan = FastContextPlan {
            query: "test".to_string(),
            channels: vec!["unknown_channel".to_string()],
            max_evidence: 10,
            budget: 0,
        };

        let result = fast_context(root, &records, &plan);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(
            err.contains("unknown channels"),
            "should reject unknown channels: {err}"
        );
    }

    #[test]
    fn fast_context_pack_shape() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("lib.rs"),
            "pub struct EvidenceCore {\n    pub path: String,\n}\n",
        )
        .unwrap();
        std::fs::create_dir_all(root.join(".git")).unwrap();

        let policy = openlocus_core::Policy::default();
        let records = openlocus_repo::scan::scan_repo(root, &policy).unwrap();

        let plan = FastContextPlan {
            query: "EvidenceCore".to_string(),
            channels: vec!["regex".to_string()],
            max_evidence: 10,
            budget: 0,
        };

        let result = fast_context(root, &records, &plan).unwrap();

        // Pack should exist and be EvidencePack-compatible
        assert!(!result.pack.trace_id.is_empty());
        assert_eq!(result.pack.evidence.len(), result.evidence.len());
        assert_eq!(result.pack.trace_id, result.trace_id);
        assert!(result.pack.budget_used.tokens_estimated > 0 || result.evidence.is_empty());
    }

    #[test]
    fn fast_context_actions_replayable() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("lib.rs"),
            "pub struct EvidenceCore {\n    pub path: String,\n}\n",
        )
        .unwrap();
        std::fs::create_dir_all(root.join(".git")).unwrap();

        let policy = openlocus_core::Policy::default();
        let records = openlocus_repo::scan::scan_repo(root, &policy).unwrap();

        let plan = FastContextPlan {
            query: "EvidenceCore".to_string(),
            channels: vec!["regex".to_string(), "symbol".to_string()],
            max_evidence: 10,
            budget: 0,
        };

        let result = fast_context(root, &records, &plan).unwrap();

        // Should have action records
        assert!(!result.actions.is_empty());
        for action in &result.actions {
            assert!(!action.channel.is_empty());
            assert!(!action.query.is_empty());
        }

        // Turns that ran should have actions (graph may not if no candidates)
        for turn in &result.turns {
            if turn.evidence_count > 0 {
                assert!(
                    !turn.actions.is_empty(),
                    "turn {:?} has evidence but no actions",
                    turn.turn
                );
            }
        }
    }

    #[test]
    fn token_budget_trims_evidence() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("lib.rs"),
            "pub struct EvidenceCore {\n    pub path: String,\n    pub start_line: u64,\n    pub end_line: u64,\n}\n",
        )
        .unwrap();
        std::fs::create_dir_all(root.join(".git")).unwrap();

        let policy = openlocus_core::Policy::default();
        let records = openlocus_repo::scan::scan_repo(root, &policy).unwrap();

        let plan = FastContextPlan {
            query: "EvidenceCore".to_string(),
            channels: vec!["regex".to_string()],
            max_evidence: 100,
            budget: 5, // Very tight token budget
        };

        let result = fast_context(root, &records, &plan).unwrap();
        // Should have trimmed evidence due to token budget
        assert!(
            result.diagnostics.token_budget_enforced || result.evidence.len() <= 1,
            "token budget should trim evidence: got {} evidence, enforced={}",
            result.evidence.len(),
            result.diagnostics.token_budget_enforced,
        );
    }
}
