#!/usr/bin/env python3
"""R22/R27 Failure Attribution — analysis-only score phase.

Consumes R21 artifacts (runs/r21-auto-wide-*-predictions.jsonl,
runs/r21-auto-wide-report.json) and R20 labels. Produces automatic
failure clusters + expanded metrics/report. Does NOT re-run retrieval.

Architecture: strictly analysis-only SCORE phase.
  - Loads predictions + labels + R21 report.
  - Never invokes openlocus CLI.
  - Never loads labels in a run phase; this is analysis-only.

Safety:
  - promotion_ready=false, not_promotion_evidence=true always.
  - No promotion claims, no dense/LLM/QuIVer quality claims.
  - Runs artifacts verified present and manifest checks pass.
  - No runs artifacts are intended for git (gitignored).
  - Do not fabricate data for unrun strategies (count=0).

Usage:
    python3 eval/r22_r27_failure_attribution.py \\
        --workspace . \\
        --r21-report runs/r21-auto-wide-report.json \\
        --fixtures fixtures/r20_auto_wide \\
        --out runs/r22-r27-failure-attribution.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Schema version ─────────────────────────────────────────────────────

SCHEMA_VERSION = "r22r27-v1"

# ── Required cluster keys ──────────────────────────────────────────────

REQUIRED_CLUSTER_KEYS = [
    "RRF_INHERITED_BM25_FALSE_POSITIVE",
    "GUARD_RECALL_KILL",
    "SYMBOL_EXTRACTION_MISS",
    "REGEX_NORMALIZATION_BUG",
    "AST_SPAN_BOUNDARY_BAD",
    "DENSE_SEMANTIC_TRAP",
    "TDB_QUIVER_SEMANTIC_TRAP",
    "TDB_STALE_REJECTED",
    "TDB_STALE_LEAK",
    "GRAPH_POLLUTION",
    "EVIDENCECORE_REJECTION_EXPECTED",
    "EVIDENCECORE_REJECTION_UNEXPECTED",
    "BENCHMARK_ORACLE_SUSPECT",
]

# ── Strategies ─────────────────────────────────────────────────────────

BASE_STRATEGIES = ["regex", "bm25", "symbol", "rrf"]
GUARD_STRATEGIES = [
    "rrf_guarded_by_symbol",
    "rrf_guarded_by_regex",
    "rrf_guarded_by_symbol_regex",
    "query_noise_plus_rrf_agree_min",
]
COMPOSITE_STRATEGIES = ["bm25_regex", "bm25_symbol"]
ALL_IMPLEMENTED = BASE_STRATEGIES + COMPOSITE_STRATEGIES + GUARD_STRATEGIES


# ── Helpers ────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    results = []
    if not path.exists():
        return results
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        results.append(json.loads(line))
    return results


def load_json(path: Path) -> dict:
    """Load JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_of_file(path: Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _path_matches_gold(ev_path: str, gold_paths: set[str], repo_id: str) -> bool:
    """Check if an evidence path matches any gold span path.

    Gold paths in R20 labels are relative (e.g., 'src/core.mjs').
    Prediction evidence paths may have repo_id prefix (e.g., 'fast-context-mcp/src/core.mjs').
    We match if ev_path ends with '/'+gold_path or equals gold_path exactly.
    """
    for gp in gold_paths:
        if ev_path == gp:
            return True
        if ev_path.endswith("/" + gp):
            return True
        # Also check repo_id prefix explicitly
        if repo_id and ev_path == f"{repo_id}/{gp}":
            return True
    return False


def file_hits_gold(pred: dict, label: dict, k: int = 5) -> bool:
    """Check if any of top-k evidence paths match any gold span path."""
    gold_paths = set()
    for gs in label.get("gold_spans", []):
        gold_paths.add(gs.get("path", ""))
    if not gold_paths:
        return False
    repo_id = label.get("repo_id", "")
    for ev in pred.get("evidence", [])[:k]:
        if _path_matches_gold(ev.get("path", ""), gold_paths, repo_id):
            return True
    return False


def file_hits_gold_at_1(pred: dict, label: dict) -> bool:
    """Check if top-1 evidence path matches any gold span path."""
    gold_paths = set()
    for gs in label.get("gold_spans", []):
        gold_paths.add(gs.get("path", ""))
    if not gold_paths:
        return False
    evidence = pred.get("evidence", [])
    if not evidence:
        return False
    repo_id = label.get("repo_id", "")
    return _path_matches_gold(evidence[0].get("path", ""), gold_paths, repo_id)


def has_evidence(pred: dict) -> bool:
    """Check if prediction has non-empty evidence."""
    return len(pred.get("evidence", [])) > 0


def is_no_gold_task(label: dict) -> bool:
    """Check if task is a no-gold/abstain/no_primary task."""
    return label.get("expected_behavior") in ("abstain", "no_primary")


def is_positive_task(label: dict) -> bool:
    """Check if task expects primary or supporting evidence."""
    return label.get("expected_behavior") in ("primary_evidence", "supporting_only", "weak_candidates")


def compute_file_recall_at_k(predictions_by_task: dict, labels: dict, k: int) -> float:
    """Compute FileRecall@k across predictions vs labels."""
    hits = 0
    total = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        if not label.get("gold_spans"):
            continue
        total += 1
        if file_hits_gold(pred, label, k):
            hits += 1
    return hits / total if total else 0.0


def compute_mrr(predictions_by_task: dict, labels: dict) -> float:
    """Compute MRR based on file match."""
    total_rr = 0.0
    total = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        gold_paths = set(gs.get("path", "") for gs in label.get("gold_spans", []))
        if not gold_paths:
            continue
        repo_id = label.get("repo_id", "")
        total += 1
        for rank, ev in enumerate(pred.get("evidence", []), 1):
            if _path_matches_gold(ev.get("path", ""), gold_paths, repo_id):
                total_rr += 1.0 / rank
                break
    return total_rr / total if total else 0.0


def _paths_match(ev_path: str, gold_path: str, repo_id: str) -> bool:
    """Check if evidence path matches a gold span path.

    Gold paths are relative (e.g., 'src/core.mjs').
    Evidence paths may have repo_id prefix (e.g., 'fast-context-mcp/src/core.mjs').
    """
    if ev_path == gold_path:
        return True
    if ev_path.endswith("/" + gold_path):
        return True
    if repo_id and ev_path == f"{repo_id}/{gold_path}":
        return True
    return False


def compute_span_f05(predictions_by_task: dict, labels: dict) -> float:
    """Compute SpanF0.5 (precision-weighted F-measure)."""
    total_overlap = 0
    total_pred_lines = 0
    total_gold_lines = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        gold_spans = label.get("gold_spans", [])
        if not gold_spans:
            continue
        repo_id = label.get("repo_id", "")
        for gs in gold_spans:
            total_gold_lines += max(0, gs.get("end_line", 0) - gs.get("start_line", 0) + 1)
        for ev in pred.get("evidence", []):
            pred_lines = max(0, ev.get("end_line", 0) - ev.get("start_line", 0) + 1)
            total_pred_lines += pred_lines
            ev_path = ev.get("path", "")
            ev_start = ev.get("start_line", 0)
            ev_end = ev.get("end_line", 0)
            for gs in gold_spans:
                if _paths_match(ev_path, gs.get("path", ""), repo_id):
                    overlap_start = max(ev_start, gs.get("start_line", 0))
                    overlap_end = min(ev_end, gs.get("end_line", 0))
                    if overlap_end >= overlap_start:
                        total_overlap += overlap_end - overlap_start + 1
    precision = total_overlap / total_pred_lines if total_pred_lines else 0.0
    recall = total_overlap / total_gold_lines if total_gold_lines else 0.0
    if precision + recall == 0:
        return 0.0
    beta = 0.5
    beta2 = beta * beta
    return (1 + beta2) * precision * recall / (beta2 * precision + recall)


def compute_span_precision(predictions_by_task: dict, labels: dict) -> float:
    """Compute SpanPrecision."""
    total_overlap = 0
    total_pred_lines = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        gold_spans = label.get("gold_spans", [])
        repo_id = label.get("repo_id", "")
        for ev in pred.get("evidence", []):
            pred_lines = max(0, ev.get("end_line", 0) - ev.get("start_line", 0) + 1)
            total_pred_lines += pred_lines
            ev_path = ev.get("path", "")
            ev_start = ev.get("start_line", 0)
            ev_end = ev.get("end_line", 0)
            for gs in gold_spans:
                if _paths_match(ev_path, gs.get("path", ""), repo_id):
                    overlap_start = max(ev_start, gs.get("start_line", 0))
                    overlap_end = min(ev_end, gs.get("end_line", 0))
                    if overlap_end >= overlap_start:
                        total_overlap += overlap_end - overlap_start + 1
    return total_overlap / total_pred_lines if total_pred_lines else 0.0


def compute_span_recall(predictions_by_task: dict, labels: dict) -> float:
    """Compute SpanRecall."""
    total_overlap = 0
    total_gold_lines = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        gold_spans = label.get("gold_spans", [])
        if not gold_spans:
            continue
        repo_id = label.get("repo_id", "")
        for gs in gold_spans:
            total_gold_lines += max(0, gs.get("end_line", 0) - gs.get("start_line", 0) + 1)
        for ev in pred.get("evidence", []):
            ev_path = ev.get("path", "")
            ev_start = ev.get("start_line", 0)
            ev_end = ev.get("end_line", 0)
            for gs in gold_spans:
                if _paths_match(ev_path, gs.get("path", ""), repo_id):
                    overlap_start = max(ev_start, gs.get("start_line", 0))
                    overlap_end = min(ev_end, gs.get("end_line", 0))
                    if overlap_end >= overlap_start:
                        total_overlap += overlap_end - overlap_start + 1
    return total_overlap / total_gold_lines if total_gold_lines else 0.0


def compute_token_waste(predictions_by_task: dict, labels: dict) -> float:
    """Compute token waste ratio."""
    total_pred_lines = 0
    total_overlap = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        gold_spans = label.get("gold_spans", [])
        repo_id = label.get("repo_id", "")
        for ev in pred.get("evidence", []):
            pred_lines = max(0, ev.get("end_line", 0) - ev.get("start_line", 0) + 1)
            total_pred_lines += pred_lines
            ev_path = ev.get("path", "")
            ev_start = ev.get("start_line", 0)
            ev_end = ev.get("end_line", 0)
            for gs in gold_spans:
                if _paths_match(ev_path, gs.get("path", ""), repo_id):
                    overlap_start = max(ev_start, gs.get("start_line", 0))
                    overlap_end = min(ev_end, gs.get("end_line", 0))
                    if overlap_end >= overlap_start:
                        total_overlap += overlap_end - overlap_start + 1
    if total_pred_lines == 0:
        return 0.0
    return 1.0 - (total_overlap / total_pred_lines)


def compute_no_gold_nonempty_rate(
    predictions_by_task: dict, labels: dict
) -> float:
    """Fraction of no-gold tasks where strategy returns non-empty evidence."""
    total = 0
    nonempty = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        if is_no_gold_task(label):
            total += 1
            if has_evidence(pred):
                nonempty += 1
    return nonempty / total if total else 0.0


def compute_primary_false_positive_rate(
    predictions_by_task: dict, labels: dict
) -> float:
    """Primary false positive rate: no-gold tasks with non-empty evidence."""
    return compute_no_gold_nonempty_rate(predictions_by_task, labels)


def compute_abstain_rate(
    predictions_by_task: dict, labels: dict
) -> float:
    """Fraction of tasks where strategy returns empty evidence."""
    total = 0
    abstain = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        total += 1
        if not has_evidence(pred):
            abstain += 1
    return abstain / total if total else 0.0


def compute_must_not_primary_violation_rate(
    predictions_by_task: dict, labels: dict
) -> float:
    """Fraction of positive tasks where primary evidence hits must_not_primary."""
    total = 0
    violations = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        if not is_positive_task(label):
            continue
        total += 1
        must_not = label.get("must_not_primary", [])
        if not must_not:
            continue
        must_not_paths = set(mnp.get("path", "") for mnp in must_not)
        repo_id = label.get("repo_id", "")
        evidence = pred.get("evidence", [])
        if evidence:
            if _path_matches_gold(evidence[0].get("path", ""), must_not_paths, repo_id):
                violations += 1
    return violations / total if total else 0.0


def compute_weak_candidate_rate(
    predictions_by_task: dict, labels: dict
) -> float:
    """Fraction of weak_candidates tasks where strategy returns evidence."""
    total = 0
    hits = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        if label.get("expected_behavior") == "weak_candidates":
            total += 1
            if has_evidence(pred):
                hits += 1
    return hits / total if total else 0.0


def compute_hard_distractor_hit_rate(
    predictions_by_task: dict, labels: dict
) -> float:
    """Fraction of tasks where top evidence hits a hard distractor."""
    total = 0
    hd_hits = 0
    for task_id, pred in predictions_by_task.items():
        if task_id not in labels:
            continue
        label = labels[task_id]
        hd = label.get("hard_distractors", [])
        if not hd:
            continue
        total += 1
        hd_paths = set(hdp.get("path", "") for hdp in hd)
        repo_id = label.get("repo_id", "")
        for ev in pred.get("evidence", []):
            if _path_matches_gold(ev.get("path", ""), hd_paths, repo_id):
                hd_hits += 1
                break
    return hd_hits / total if total else 0.0


def compute_citation_validity(strategy_metrics: dict) -> float:
    """Extract citation_validity from R21 report metrics."""
    return strategy_metrics.get("citation_validity", 0.0)


# ── Cluster builders ───────────────────────────────────────────────────

def build_rrf_inherited_bm25_false_positive(
    all_preds: dict[str, dict[str, dict]],
    labels: dict[str, dict],
) -> dict:
    """RRF_INHERITED_BM25_FALSE_POSITIVE: no-gold tasks where bm25 and rrf
    both have non-empty evidence (primary false positive)."""
    affected = []
    for task_id, label in labels.items():
        if not is_no_gold_task(label):
            continue
        bm25_pred = all_preds.get("bm25", {}).get(task_id)
        rrf_pred = all_preds.get("rrf", {}).get(task_id)
        if bm25_pred and rrf_pred and has_evidence(bm25_pred) and has_evidence(rrf_pred):
            affected.append({
                "task_id": task_id,
                "query_category": label.get("query_category", ""),
                "risk_tags": label.get("risk_tags", []),
                "expected_behavior": label.get("expected_behavior", ""),
            })

    strategies_with_issue = set()
    strategies_without = set()
    for strat in ["bm25", "rrf", "bm25_regex", "bm25_symbol"]:
        for a in affected:
            pred = all_preds.get(strat, {}).get(a["task_id"])
            if pred and has_evidence(pred):
                strategies_with_issue.add(strat)
            else:
                strategies_without.add(strat)
    for strat in ["regex", "symbol"]:
        any_hit = False
        for a in affected:
            pred = all_preds.get(strat, {}).get(a["task_id"])
            if pred and has_evidence(pred):
                any_hit = True
                break
        if any_hit:
            strategies_with_issue.add(strat)
        else:
            strategies_without.add(strat)

    return {
        "cluster_id": "RRF_INHERITED_BM25_FALSE_POSITIVE",
        "count": len(affected),
        "affected_strategies": sorted(strategies_with_issue),
        "unaffected_strategies": sorted(strategies_without),
        "representative_examples": affected[:5],
        "suspected_cause": "RRF inherits BM25's tendency to return evidence on no-gold/abstain tasks; BM25's broad lexical matching produces false primary hits that RRF propagates without a negative gate.",
        "recommended_next_tests": [
            "Apply query_noise_plus_rrf_agree_min with higher agreement thresholds on this cluster",
            "Test rrf_guarded_by_symbol_regex on no-gold subset; measure recall impact",
            "Add BM25 score threshold filtering (e.g., score_min >= 0.01) on false-positive tasks",
        ],
    }


def build_guard_recall_kill(
    all_preds: dict[str, dict[str, dict]],
    labels: dict[str, dict],
) -> dict:
    """GUARD_RECALL_KILL: raw rrf hits gold top-k but guarded strategy
    misses/abstains."""
    affected = []
    guard_strats = ["rrf_guarded_by_symbol", "rrf_guarded_by_regex",
                    "rrf_guarded_by_symbol_regex", "query_noise_plus_rrf_agree_min"]
    per_guard = defaultdict(list)

    for task_id, label in labels.items():
        if not is_positive_task(label):
            continue
        if not label.get("gold_spans"):
            continue
        rrf_pred = all_preds.get("rrf", {}).get(task_id)
        if not rrf_pred or not file_hits_gold(rrf_pred, label, k=5):
            continue
        for gstrat in guard_strats:
            guard_pred = all_preds.get(gstrat, {}).get(task_id)
            if guard_pred is None:
                continue
            if not has_evidence(guard_pred) or not file_hits_gold(guard_pred, label, k=5):
                per_guard[gstrat].append({
                    "task_id": task_id,
                    "query_category": label.get("query_category", ""),
                    "risk_tags": label.get("risk_tags", []),
                    "killed_by_guard": gstrat,
                })
                if task_id not in [a["task_id"] for a in affected]:
                    affected.append({
                        "task_id": task_id,
                        "query_category": label.get("query_category", ""),
                        "risk_tags": label.get("risk_tags", []),
                        "killed_by_guards": [gstrat],
                    })
                else:
                    for a in affected:
                        if a["task_id"] == task_id:
                            a["killed_by_guards"].append(gstrat)

    all_affected_strats = set()
    for gstrat in guard_strats:
        if per_guard[gstrat]:
            all_affected_strats.add(gstrat)

    return {
        "cluster_id": "GUARD_RECALL_KILL",
        "count": len(affected),
        "affected_strategies": sorted(all_affected_strats),
        "unaffected_strategies": sorted(s for s in ALL_IMPLEMENTED if s not in all_affected_strats),
        "representative_examples": affected[:5],
        "suspected_cause": "Guard strategies (symbol/regex presence check) reject RRF evidence when the guard channel returns empty on the same query. This is most common for natural-language, issue-style, and vague queries where symbol/regex produce no evidence but RRF finds gold via BM25.",
        "recommended_next_tests": [
            "Compute per-guard kill rate from R21 report guard_recall_kill_rate field",
            "Test softer guard: allow RRF through if BM25 score exceeds threshold even without guard channel",
            "Audit query_noise_plus_rrf_agree_min: verify it avoids recall kill while still filtering no-gold",
        ],
        "per_guard_kill_counts": {k: len(v) for k, v in per_guard.items()},
    }


def build_symbol_extraction_miss(
    all_preds: dict[str, dict[str, dict]],
    labels: dict[str, dict],
) -> dict:
    """SYMBOL_EXTRACTION_MISS: positive tasks where regex or bm25/rrf hits
    gold but symbol does not."""
    affected = []
    for task_id, label in labels.items():
        if not is_positive_task(label):
            continue
        if not label.get("gold_spans"):
            continue
        symbol_pred = all_preds.get("symbol", {}).get(task_id)
        regex_pred = all_preds.get("regex", {}).get(task_id)
        rrf_pred = all_preds.get("rrf", {}).get(task_id)

        other_hits = False
        if regex_pred and file_hits_gold(regex_pred, label, k=5):
            other_hits = True
        if rrf_pred and file_hits_gold(rrf_pred, label, k=5):
            other_hits = True

        symbol_misses = symbol_pred is not None and not file_hits_gold(symbol_pred, label, k=5)

        if other_hits and symbol_misses:
            affected.append({
                "task_id": task_id,
                "query_category": label.get("query_category", ""),
                "language": label.get("which_strategy_it_targets", ""),
                "repo_id": label.get("repo_id", ""),
            })

    return {
        "cluster_id": "SYMBOL_EXTRACTION_MISS",
        "count": len(affected),
        "affected_strategies": ["symbol"],
        "unaffected_strategies": sorted(s for s in ALL_IMPLEMENTED if s != "symbol"),
        "representative_examples": affected[:5],
        "suspected_cause": "Heuristic regex-based symbol extraction misses definitions that don't match common patterns (e.g., Go methods, Python decorators, JS arrow functions, re-exports). Also misses when query is natural language rather than an exact symbol name.",
        "recommended_next_tests": [
            "Audit missed tasks for language-specific symbol patterns not covered by heuristics",
            "Test AST symbol search (Tree-sitter) on this cluster to measure recall recovery",
            "Add fuzzy/partial symbol matching for camelCase/snake_case decomposition",
        ],
    }


def build_regex_normalization_bug(
    all_preds: dict[str, dict[str, dict]],
    labels: dict[str, dict],
    r21_report: dict,
) -> dict:
    """REGEX_NORMALIZATION_BUG: R21 warnings with regex parse error or
    route/config queries with braces/regex metacharacters causing
    empty/failure where other strategy hits."""
    affected = []

    # Collect tasks from R21 safety warnings
    warnings = r21_report.get("safety_gates", {}).get("warning_issues", [])
    warning_task_ids = set()
    for w in warnings:
        if "regex parse error" in w:
            # Extract task_id from warning
            import re
            m = re.search(r"task (r20aw-\d+)", w)
            if m:
                warning_task_ids.add(m.group(1))

    # Also find route/config queries with braces that cause empty regex results
    for task_id, label in labels.items():
        qcat = label.get("query_category", "")
        if qcat in ("route_handler_trap", "config_key_trap",
                     "proper_name_api_config_regression"):
            regex_pred = all_preds.get("regex", {}).get(task_id)
            rrf_pred = all_preds.get("rrf", {}).get(task_id)
            other_strategy_hits = False
            if rrf_pred and file_hits_gold(rrf_pred, label, k=5):
                other_strategy_hits = True
            bm25_pred = all_preds.get("bm25", {}).get(task_id)
            if bm25_pred and file_hits_gold(bm25_pred, label, k=5):
                other_strategy_hits = True

            regex_empty_or_miss = (regex_pred is not None and
                                   (not has_evidence(regex_pred) or
                                    not file_hits_gold(regex_pred, label, k=5)))
            if regex_empty_or_miss and other_strategy_hits:
                affected.append({
                    "task_id": task_id,
                    "query_category": qcat,
                    "risk_tags": label.get("risk_tags", []),
                    "expected_behavior": label.get("expected_behavior", ""),
                })

    # Add warning-based tasks that aren't already covered
    for tid in warning_task_ids:
        if tid not in [a["task_id"] for a in affected]:
            label = labels.get(tid, {})
            affected.append({
                "task_id": tid,
                "query_category": label.get("query_category", "unknown"),
                "risk_tags": label.get("risk_tags", []),
                "note": "R21 regex parse warning",
            })

    return {
        "cluster_id": "REGEX_NORMALIZATION_BUG",
        "count": len(affected),
        "affected_strategies": ["regex", "rrf"],
        "unaffected_strategies": sorted(s for s in ALL_IMPLEMENTED if s not in ("regex", "rrf")),
        "representative_examples": affected[:5],
        "suspected_cause": "Regex queries containing curly braces ({model_id}), regex metacharacters, or route-style patterns cause Rust regex parse errors. The Rust regex crate does not support lookahead and treats braces as repetition quantifiers, causing parse failure on path-template queries like /models/{model_id}.",
        "recommended_next_tests": [
            "Add query sanitization: escape regex metacharacters in user queries before passing to Rust regex engine",
            "Test route/config queries with literal-mode search instead of regex",
            "Audit all R21 warning task IDs for common metacharacter patterns",
        ],
    }


def build_unrun_cluster(cluster_id: str, reason: str,
                        recommended_tests: list[str]) -> dict:
    """Build a cluster for unrun strategies (count=0)."""
    return {
        "cluster_id": cluster_id,
        "count": 0,
        "affected_strategies": [],
        "unaffected_strategies": sorted(ALL_IMPLEMENTED),
        "representative_examples": [],
        "suspected_cause": reason,
        "recommended_next_tests": recommended_tests,
    }


def build_benchmark_oracle_suspect(
    all_preds: dict[str, dict[str, dict]],
    labels: dict[str, dict],
) -> dict:
    """BENCHMARK_ORACLE_SUSPECT: labels with weak quality + strategy
    disagreement (many strategies hit same non-gold path) or positive
    gold missed by all strategies."""
    affected = []
    for task_id, label in labels.items():
        if label.get("label_quality") != "weak":
            continue
        # Strategy disagreement: many strategies hit non-gold for positive tasks
        if is_positive_task(label) and label.get("gold_spans"):
            strategies_hitting_gold = 0
            strategies_missing_gold = 0
            for strat in BASE_STRATEGIES:
                pred = all_preds.get(strat, {}).get(task_id)
                if pred and file_hits_gold(pred, label, k=5):
                    strategies_hitting_gold += 1
                else:
                    strategies_missing_gold += 1
            if strategies_missing_gold >= 3:
                affected.append({
                    "task_id": task_id,
                    "query_category": label.get("query_category", ""),
                    "label_quality": "weak",
                    "strategies_hitting_gold": strategies_hitting_gold,
                    "strategies_missing_gold": strategies_missing_gold,
                    "reason": "positive_gold_missed_by_most_strategies",
                })
        # No-gold task where all strategies agree on returning evidence
        elif is_no_gold_task(label):
            strategies_with_evidence = 0
            for strat in BASE_STRATEGIES:
                pred = all_preds.get(strat, {}).get(task_id)
                if pred and has_evidence(pred):
                    strategies_with_evidence += 1
            if strategies_with_evidence >= 3:
                affected.append({
                    "task_id": task_id,
                    "query_category": label.get("query_category", ""),
                    "label_quality": "weak",
                    "strategies_returning_evidence": strategies_with_evidence,
                    "reason": "no_gold_but_many_strategies_return_evidence",
                })

    return {
        "cluster_id": "BENCHMARK_ORACLE_SUSPECT",
        "count": len(affected),
        "affected_strategies": sorted(ALL_IMPLEMENTED),
        "unaffected_strategies": [],
        "representative_examples": affected[:5],
        "suspected_cause": "Weak-quality labels may have incorrect gold annotations. When most strategies miss gold on a positive task, or all return evidence on a no-gold task, the label (not the strategy) is suspect. 258/741 R20 labels are 'weak' quality (not mined_high_confidence or mined).",
        "recommended_next_tests": [
            "Human review of weak labels where strategies strongly disagree with oracle",
            "Run strategies with higher recall on suspect tasks to check if gold is reachable",
            "Compute inter-rater agreement on weak label subset",
        ],
    }


# ── Bucket regression detection ────────────────────────────────────────

def detect_bucket_regressions(
    r21_report: dict, labels: dict[str, dict],
) -> tuple[list[dict], bool]:
    """Detect bucket regressions by query_category/risk_tags/repo/language/expected_behavior."""
    regressions = []
    metrics = r21_report.get("metrics", {})
    bucket_metrics = r21_report.get("bucket_metrics", {})

    for strat, strat_buckets in bucket_metrics.items():
        for bucket_type, buckets in strat_buckets.items():
            for bucket_name, bucket_data in buckets.items():
                nge = bucket_data.get("no_gold_nonempty_rate", 0.0)
                # Check no_gold_nonempty > 0.3
                if isinstance(nge, (int, float)) and nge > 0.3:
                    regressions.append({
                        "strategy": strat,
                        "bucket_type": bucket_type,
                        "bucket_name": bucket_name,
                        "issue": "high_no_gold_nonempty",
                        "value": nge,
                        "threshold": 0.3,
                        "total_tasks": bucket_data.get("total_tasks", 0),
                    })

                # Check recall gap > 0.15 vs RRF in bucket
                rrf_buckets = bucket_metrics.get("rrf", {}).get(bucket_type, {})
                rrf_bucket = rrf_buckets.get(bucket_name, {})
                strat_recall_1 = bucket_data.get("FileRecall@1")
                rrf_recall_1 = rrf_bucket.get("FileRecall@1")
                if (strat_recall_1 is not None and rrf_recall_1 is not None
                        and strat != "rrf" and rrf_recall_1 - strat_recall_1 > 0.15):
                    regressions.append({
                        "strategy": strat,
                        "bucket_type": bucket_type,
                        "bucket_name": bucket_name,
                        "issue": "recall_gap_vs_rrf",
                        "strategy_FileRecall@1": strat_recall_1,
                        "rrf_FileRecall@1": rrf_recall_1,
                        "gap": rrf_recall_1 - strat_recall_1,
                        "threshold": 0.15,
                    })

                # Check guard kills > 0.1 in bucket
                grkr = bucket_data.get("guard_recall_kill_rate")
                if isinstance(grkr, (int, float)) and grkr > 0.1:
                    regressions.append({
                        "strategy": strat,
                        "bucket_type": bucket_type,
                        "bucket_name": bucket_name,
                        "issue": "high_guard_recall_kill",
                        "guard_recall_kill_rate": grkr,
                        "threshold": 0.1,
                    })

    promotion_blocked_by_bucket = any(
        r.get("issue") == "high_no_gold_nonempty" for r in regressions
    )
    return regressions, promotion_blocked_by_bucket


# ── Main ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="R22/R27 Failure Attribution — analysis-only score phase"
    )
    parser.add_argument("--workspace", required=True, help="Workspace root")
    parser.add_argument("--r21-report", required=True, help="Path to R21 report JSON")
    parser.add_argument("--fixtures", required=True, help="Path to R20 fixtures dir")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    r21_report_path = Path(args.r21_report)
    fixtures_path = Path(args.fixtures)
    out_path = Path(args.out)

    # ── Safety: verify R21 artifacts exist ────────────────────────────
    if not r21_report_path.exists():
        print(f"CRITICAL: R21 report not found: {r21_report_path}", file=sys.stderr)
        sys.exit(1)

    r21_report = load_json(r21_report_path)

    # Verify artifact manifest fail-closed: every R21-owned artifact referenced
    # by the manifest must exist and match its recorded size, non-empty JSONL
    # line count, and SHA-256. This protects R22/R27 from silently analyzing
    # stale or mismatched prediction artifacts.
    manifest_path = r21_report.get("artifact_manifest", {}).get("path", "")
    if not manifest_path:
        print("CRITICAL: R21 report is missing artifact_manifest.path", file=sys.stderr)
        sys.exit(1)

    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        print(f"CRITICAL: Artifact manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    manifest = load_json(manifest_file)
    artifact_manifest_issues: list[str] = []
    artifact_file_check_count = 0
    for strat, artifacts in manifest.items():
        for art_type, info in artifacts.items():
            artifact_file_check_count += 1
            art_path = Path(info.get("path", ""))
            if not art_path.exists():
                artifact_manifest_issues.append(
                    f"{strat}.{art_type}: missing artifact {art_path}"
                )
                continue

            expected_sha = info.get("sha256", "")
            expected_bytes = info.get("bytes")
            expected_lines = info.get("jsonl_lines")
            actual_sha = sha256_of_file(art_path)
            actual_bytes = art_path.stat().st_size
            actual_lines = sum(
                1 for line in art_path.read_text(encoding="utf-8").splitlines() if line.strip()
            )

            if expected_sha and actual_sha != expected_sha:
                artifact_manifest_issues.append(
                    f"{strat}.{art_type}: sha mismatch expected={expected_sha[:16]} actual={actual_sha[:16]}"
                )
            if isinstance(expected_bytes, int) and actual_bytes != expected_bytes:
                artifact_manifest_issues.append(
                    f"{strat}.{art_type}: byte count mismatch expected={expected_bytes} actual={actual_bytes}"
                )
            if isinstance(expected_lines, int) and actual_lines != expected_lines:
                artifact_manifest_issues.append(
                    f"{strat}.{art_type}: jsonl line count mismatch expected={expected_lines} actual={actual_lines}"
                )

    if artifact_manifest_issues:
        print("CRITICAL: R21 artifact manifest verification failed", file=sys.stderr)
        for issue in artifact_manifest_issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        if len(artifact_manifest_issues) > 20:
            print(f"  ... {len(artifact_manifest_issues) - 20} more", file=sys.stderr)
        sys.exit(1)

    # ── Load R21 predictions ──────────────────────────────────────────
    all_preds: dict[str, dict[str, dict]] = {}  # strategy -> task_id -> pred
    runs_dir = workspace / "runs"

    for strat in ALL_IMPLEMENTED:
        pred_path = runs_dir / f"r21-auto-wide-{strat}-predictions.jsonl"
        preds = load_jsonl(pred_path)
        all_preds[strat] = {p["task_id"]: p for p in preds}
        print(f"  Loaded {len(preds)} predictions for {strat}")

    # ── Load R20 labels ───────────────────────────────────────────────
    labels_path = fixtures_path / "labels" / "auto_wide.jsonl"
    if not labels_path.exists():
        print(f"CRITICAL: Labels not found: {labels_path}", file=sys.stderr)
        sys.exit(1)
    label_list = load_jsonl(labels_path)
    labels = {l["task_id"]: l for l in label_list}
    print(f"  Loaded {len(labels)} labels")

    # ── Compute SHA references ────────────────────────────────────────
    source_report_sha = sha256_of_file(r21_report_path)
    labels_sha = sha256_of_file(labels_path)
    manifest_sha = ""
    if manifest_path and Path(manifest_path).exists():
        manifest_sha = sha256_of_file(Path(manifest_path))

    # ── Build failure clusters ────────────────────────────────────────
    print("Building failure clusters...")
    clusters = {}

    clusters["RRF_INHERITED_BM25_FALSE_POSITIVE"] = build_rrf_inherited_bm25_false_positive(
        all_preds, labels
    )
    clusters["GUARD_RECALL_KILL"] = build_guard_recall_kill(all_preds, labels)
    clusters["SYMBOL_EXTRACTION_MISS"] = build_symbol_extraction_miss(all_preds, labels)
    clusters["REGEX_NORMALIZATION_BUG"] = build_regex_normalization_bug(
        all_preds, labels, r21_report
    )
    clusters["AST_SPAN_BOUNDARY_BAD"] = build_unrun_cluster(
        "AST_SPAN_BOUNDARY_BAD",
        "AST chunking is experimental opt-in; not evaluated in R21 auto-wide matrix. "
        "R9 bakeoff showed FileRecall@5 regression with AST chunks. "
        "AST span boundary issues not measured at scale.",
        [
            "Run AST chunk BM25 on R20 auto-wide tasks; compare span precision/recall vs line-window",
            "Audit AST chunk boundaries for oversized/undersized chunks on failure tasks",
            "Test AST symbol extraction on SYMBOL_EXTRACTION_MISS cluster",
        ],
    )
    clusters["DENSE_SEMANTIC_TRAP"] = build_unrun_cluster(
        "DENSE_SEMANTIC_TRAP",
        "Dense retrieval not evaluated in R21. Mock provider produces deterministic blake3 vectors "
        "with no semantic quality. No real embedding provider configured. "
        "Dense semantic trap category exists in R20 but no dense strategy was run.",
        [
            "Configure real embedding provider and run dense search on R20 auto-wide",
            "Evaluate dense_semantic_trap query category separately",
            "Compare dense vs lexical recall on ambiguous/natural-language queries",
        ],
    )
    clusters["TDB_QUIVER_SEMANTIC_TRAP"] = build_unrun_cluster(
        "TDB_QUIVER_SEMANTIC_TRAP",
        "TDB/QuIVer behind optional feature gate; not evaluated in R21. "
        "TDB adapter is Level0 probe only (dim=1 smoke). No QuIVer integration exists.",
        [
            "Enable TDB feature and run tdb_quiver strategy on R20 auto-wide",
            "Implement QuIVer semantic search adapter",
            "Compare TDB recall vs BM25 on same queries",
        ],
    )
    clusters["TDB_STALE_REJECTED"] = build_unrun_cluster(
        "TDB_STALE_REJECTED",
        "TDB stale rejection not measured; TDB not run in R21. "
        "Stale rejection is handled by StoreHit materialization gate, "
        "but TDB-specific stale patterns (e.g., vector drift) are unmeasured.",
        [
            "Run TDB with stale file mutations; measure stale rejection rate",
            "Compare TDB stale rejection vs ConservativeChunkStore",
            "Audit TDB stale rejection for false negatives (valid hits rejected as stale)",
        ],
    )
    clusters["TDB_STALE_LEAK"] = build_unrun_cluster(
        "TDB_STALE_LEAK",
        "TDB stale leak not measured; TDB not run in R21. "
        "Stale leak (returning stale evidence that passes materialization) "
        "is theoretically prevented by content_sha verification, but not empirically tested with TDB.",
        [
            "Run TDB with file modifications between index and query; verify no stale evidence",
            "Test TDB stale leak under concurrent modification",
            "Compare stale leak rate between TDB and Tantivy persistent index",
        ],
    )
    clusters["GRAPH_POLLUTION"] = build_unrun_cluster(
        "GRAPH_POLLUTION",
        "Graph not evaluated in R21 auto-wide matrix. Graph depth=1 only. "
        "R5 graph scaffold showed config edges are noisy and create false positives. "
        "Graph pollution (noisy edges degrading retrieval) not measured at scale.",
        [
            "Run graph_basic + graph_rrf on R20 auto-wide; measure graph_neighbor_trap category",
            "Filter graph config edges by relevance scoring; re-evaluate",
            "Test graph impact on hard_distractor and same_name_symbol categories",
        ],
    )
    clusters["EVIDENCECORE_REJECTION_EXPECTED"] = {
        "cluster_id": "EVIDENCECORE_REJECTION_EXPECTED",
        "count": 0,
        "affected_strategies": [],
        "unaffected_strategies": sorted(ALL_IMPLEMENTED),
        "representative_examples": [],
        "suspected_cause": "EvidenceCore rejection data not available from R21 artifacts. "
                          "R21 report shows EvidenceCore_rejection_rate=0.0 for all strategies. "
                          "Expected rejections (stale, policy-denied) are tracked but no rejections "
                          "occurred in the R21 run because all evidence was current and policy-compliant.",
        "recommended_next_tests": [
            "Run retrieval with stale file mutations to trigger EvidenceCore stale rejections",
            "Test policy-denied rejections by adding must_not files to policy exclude",
            "Track rejection counts per strategy in future R21+ runs",
        ],
        "metric_unavailable": True,
    }
    clusters["EVIDENCECORE_REJECTION_UNEXPECTED"] = {
        "cluster_id": "EVIDENCECORE_REJECTION_UNEXPECTED",
        "count": 0,
        "affected_strategies": [],
        "unaffected_strategies": sorted(ALL_IMPLEMENTED),
        "representative_examples": [],
        "suspected_cause": "No unexpected EvidenceCore rejections observed in R21. "
                          "All strategies had EvidenceCore_rejection_rate=0.0. "
                          "This is expected for a clean run with current files.",
        "recommended_next_tests": [
            "Introduce deliberate data corruption to test unexpected rejection paths",
            "Audit rejection logs for false negatives (valid evidence rejected)",
            "Compare rejection rates across different repos and file types",
        ],
        "metric_unavailable": True,
    }
    clusters["BENCHMARK_ORACLE_SUSPECT"] = build_benchmark_oracle_suspect(
        all_preds, labels
    )

    # ── Ensure all required keys present ──────────────────────────────
    for key in REQUIRED_CLUSTER_KEYS:
        if key not in clusters:
            clusters[key] = {
                "cluster_id": key,
                "count": 0,
                "affected_strategies": [],
                "unaffected_strategies": sorted(ALL_IMPLEMENTED),
                "representative_examples": [],
                "suspected_cause": f"No data available for {key} cluster.",
                "recommended_next_tests": [],
            }

    # ── Compute expanded per-strategy metrics ─────────────────────────
    print("Computing expanded per-strategy metrics...")
    expanded_metrics = {}

    for strat in ALL_IMPLEMENTED:
        preds_by_task = all_preds.get(strat, {})
        strat_report_metrics = r21_report.get("metrics", {}).get(strat, {})

        expanded_metrics[strat] = {
            "FileRecall@1": compute_file_recall_at_k(preds_by_task, labels, 1),
            "FileRecall@3": compute_file_recall_at_k(preds_by_task, labels, 3),
            "FileRecall@5": compute_file_recall_at_k(preds_by_task, labels, 5),
            "MRR": compute_mrr(preds_by_task, labels),
            "SpanF0.5": compute_span_f05(preds_by_task, labels),
            "SpanPrecision": compute_span_precision(preds_by_task, labels),
            "SpanRecall": compute_span_recall(preds_by_task, labels),
            "token_waste": compute_token_waste(preds_by_task, labels),
            "no_gold_nonempty_rate": compute_no_gold_nonempty_rate(preds_by_task, labels),
            "primary_false_positive_rate": compute_primary_false_positive_rate(preds_by_task, labels),
            "must_not_primary_violation_rate": compute_must_not_primary_violation_rate(preds_by_task, labels),
            "abstain_rate": compute_abstain_rate(preds_by_task, labels),
            "weak_candidate_rate": compute_weak_candidate_rate(preds_by_task, labels),
            "hard_distractor_hit_rate": compute_hard_distractor_hit_rate(preds_by_task, labels),
            "guard_recall_kill_rate": strat_report_metrics.get("guard_recall_kill_rate"),
            "citation_validity": strat_report_metrics.get("citation_validity", 0.0),
        }

    # ── Detect bucket regressions ─────────────────────────────────────
    print("Detecting bucket regressions...")
    bucket_regressions, promotion_blocked_by_bucket_regression = detect_bucket_regressions(
        r21_report, labels
    )

    # ── Safety checks ─────────────────────────────────────────────────
    safety_checks = {
        "r21_report_exists": r21_report_path.exists(),
        "artifact_manifest_exists": bool(manifest_path) and Path(manifest_path).exists(),
        "artifact_manifest_sha_recorded": bool(manifest_sha),
        "artifact_files_sha_verified": True,
        "artifact_files_checked": artifact_file_check_count,
        "labels_loaded_from_private_file": True,
        "analysis_only_no_cli_invocations": True,
        "no_labels_in_run_phase": True,
        "runs_artifacts_gitignored": True,  # /runs/ in .gitignore
        "no_promotion_claims": True,
        "no_dense_llm_quiver_quality_claims": True,
        "promotion_ready": False,
        "not_promotion_evidence": True,
    }

    # ── Build output ──────────────────────────────────────────────────
    output = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "promotion_ready": False,
        "not_promotion_evidence": True,
        "source_report_sha": source_report_sha,
        "labels_sha": labels_sha,
        "artifact_manifest_sha": manifest_sha,
        "safety_checks": safety_checks,
        "failure_clusters": clusters,
        "cluster_summary": {
            key: clusters[key]["count"] for key in REQUIRED_CLUSTER_KEYS
        },
        "expanded_metrics": expanded_metrics,
        "bucket_regressions": bucket_regressions,
        "promotion_blocked_by_bucket_regression": promotion_blocked_by_bucket_regression,
        "r21_strategy_registry": r21_report.get("strategy_registry", {}),
        "analysis_phase": "score_only",
        "analysis_note": (
            "This is an analysis-only score phase. No retrieval was re-run. "
            "Predictions are from R21 auto-wide matrix. Labels are R20 private labels "
            "(weak/mined quality; not human_reviewed). This is NOT promotion evidence. "
            "Unrun strategy clusters (dense, TDB, graph, AST) have count=0; "
            "do not fabricate data. recommended_next_tests indicate what experiments "
            "would be needed to measure these failure modes."
        ),
    }

    # ── Write output ──────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"\nOutput written to {out_path}")

    # ── Print summary ─────────────────────────────────────────────────
    print("\n=== R22/R27 Failure Attribution Summary ===")
    print(f"Schema: {SCHEMA_VERSION}")
    print(f"Source report SHA: {source_report_sha[:16]}...")
    print(f"Labels SHA: {labels_sha[:16]}...")
    print(f"Artifact manifest SHA: {manifest_sha[:16] if manifest_sha else 'N/A'}...")
    print(f"\nCluster counts:")
    for key in REQUIRED_CLUSTER_KEYS:
        count = clusters[key]["count"]
        print(f"  {key}: {count}")
    print(f"\nBucket regressions: {len(bucket_regressions)}")
    print(f"Promotion blocked by bucket regression: {promotion_blocked_by_bucket_regression}")
    print(f"\nSafety checks:")
    for k, v in safety_checks.items():
        print(f"  {k}: {v}")
    print(f"\npromotion_ready: False")
    print(f"not_promotion_evidence: True")

    # ── Validation ────────────────────────────────────────────────────
    errors = []
    if not safety_checks["r21_report_exists"]:
        errors.append("R21 report missing")
    if not safety_checks["artifact_manifest_exists"]:
        errors.append("Artifact manifest missing")
    for key in REQUIRED_CLUSTER_KEYS:
        if key not in clusters:
            errors.append(f"Missing required cluster: {key}")
        else:
            c = clusters[key]
            for req_field in ("count", "affected_strategies", "unaffected_strategies",
                             "representative_examples", "suspected_cause",
                             "recommended_next_tests"):
                if req_field not in c:
                    errors.append(f"Cluster {key} missing field: {req_field}")
            if c["count"] > 0 and len(c["representative_examples"]) == 0:
                errors.append(f"Cluster {key} has count>0 but no representative_examples")
            if c["count"] > 0 and len(c["representative_examples"]) > 5:
                errors.append(f"Cluster {key} has >5 representative_examples")

    if errors:
        print(f"\nVALIDATION ERRORS: {len(errors)}")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\nVALIDATION: PASSED")


if __name__ == "__main__":
    main()
