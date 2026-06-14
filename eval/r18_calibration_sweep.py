#!/usr/bin/env python3
"""R18 Threshold/Guard Calibration Sweep.

Eval-layer research only. Does NOT change Rust core.

Sweeps threshold and guard configurations over R15 benchmark predictions
to find Pareto-optimal strategies that reduce negative_nonempty while
preserving recall. Uses deterministic repo-holdout split for R15-M.

Safety:
- Hard fail if source report safety_passed is not true
- Hard fail if citation_validity < 1.0 for any method with evidence
- Hard fail if citation_hash_checked is not true (or citation_not_applicable
  is not true) for any method
- Hard fail if canary_retrieval.passed is not true where present
- Citation safety is inherited from source validated predictions, not re-claimed
- No remote calls; all benchmarks are local-only
- No LLM/dense claims

Usage:
    python3 eval/r18_calibration_sweep.py \\
        --openlocus target/debug/openlocus \\
        --workspace . \\
        --out runs/r18-calibration-sweep.json

    # Reuse existing R18-owned source reports:
    python3 eval/r18_calibration_sweep.py \\
        --skip-run \\
        --workspace . \\
        --out runs/r18-calibration-sweep.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Resolve R17 helpers ─────────────────────────────────────────────────

SCHEMA_VERSION = "r18-v1"

METHODS = ["regex", "bm25", "symbol", "rrf"]

SWEEP_THRESHOLDS = [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.08]

# Deterministic repo split for R15-M: first 6 train, last 3 holdout (sorted)
TRAIN_REPO_COUNT = 6


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prediction_provenance(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "jsonl_lines": sum(1 for line in text.splitlines() if line.strip()),
    }


def generic_prediction_path(runs_dir: Path, tier_name: str, method: str) -> Path:
    return runs_dir / f"r15-{tier_name}-{method}-predictions.jsonl"


def owned_prediction_path(runs_dir: Path, tier_name: str, method: str) -> Path:
    return runs_dir / f"r18-r15-{tier_name}-{method}-predictions.jsonl"


def materialize_owned_prediction_artifacts(runs_dir: Path) -> dict[str, dict[str, Any]]:
    """Copy generic R15 prediction outputs into R18-owned artifact names."""
    provenance: dict[str, dict[str, Any]] = {}
    for tier_name in ["medium", "stress"]:
        provenance[tier_name] = {}
        for method in METHODS:
            src = generic_prediction_path(runs_dir, tier_name, method)
            dst = owned_prediction_path(runs_dir, tier_name, method)
            if not src.exists():
                print(f"CRITICAL: Missing generic prediction file after run: {src}", file=sys.stderr)
                sys.exit(1)
            shutil.copy2(src, dst)
            provenance[tier_name][method] = prediction_provenance(dst)
    return provenance


def require_owned_prediction_artifacts(runs_dir: Path) -> dict[str, dict[str, Any]]:
    """Require R18-owned prediction artifacts; never fall back to generic files."""
    provenance: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for tier_name in ["medium", "stress"]:
        provenance[tier_name] = {}
        for method in METHODS:
            path = owned_prediction_path(runs_dir, tier_name, method)
            if not path.exists():
                missing.append(str(path))
            else:
                provenance[tier_name][method] = prediction_provenance(path)
    if missing:
        print("CRITICAL: Missing R18-owned prediction artifacts:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        sys.exit(1)
    return provenance


def _import_r17_helpers(workspace: Path):
    """Import R17 helper functions, resolving sys.path robustly."""
    eval_dir = str(workspace / "eval")
    if eval_dir not in sys.path:
        sys.path.insert(0, eval_dir)
    try:
        from r17_router_guard_experiment import (  # type: ignore[import-not-found]
            load_jsonl,
            load_report,
            resolve_path,
            verify_safety_gates,
            check_baseline_prediction_consistency,
            score_predictions,
            compute_deltas,
            is_negative_noise_query,
            is_vague_multi_word_query,
            is_compound_snake_case_noise,
            is_exact_identifier,
            has_identifier_tokens,
            route_query_only_v0,
            route_rrf_guarded_by_symbol_regex,
            apply_strategy,
            NEGATIVE_NOISE_MARKERS,
            COMMON_WORDS,
        )
        return {
            "load_jsonl": load_jsonl,
            "load_report": load_report,
            "resolve_path": resolve_path,
            "verify_safety_gates": verify_safety_gates,
            "check_baseline_prediction_consistency": check_baseline_prediction_consistency,
            "score_predictions": score_predictions,
            "compute_deltas": compute_deltas,
            "is_negative_noise_query": is_negative_noise_query,
            "is_vague_multi_word_query": is_vague_multi_word_query,
            "is_compound_snake_case_noise": is_compound_snake_case_noise,
            "is_exact_identifier": is_exact_identifier,
            "has_identifier_tokens": has_identifier_tokens,
            "route_query_only_v0": route_query_only_v0,
            "route_rrf_guarded_by_symbol_regex": route_rrf_guarded_by_symbol_regex,
            "apply_strategy": apply_strategy,
            "NEGATIVE_NOISE_MARKERS": NEGATIVE_NOISE_MARKERS,
            "COMMON_WORDS": COMMON_WORDS,
        }
    except ImportError as e:
        print(
            f"ERROR: Cannot import R17 helpers from {eval_dir}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


# ── Query feature extraction (public only) ──────────────────────────────


def extract_query_features(
    query: str,
    predictions_by_method: dict[str, list[dict]],
    task_id: str,
    repo_id: str,
) -> dict[str, Any]:
    """Extract public query+prediction features for routing decisions.

    No labels or gold information is accessed.
    """
    features: dict[str, Any] = {
        "query": query,
        "repo_id": repo_id,
    }

    for method in METHODS:
        preds = predictions_by_method.get(method, [])
        pred = next((p for p in preds if p["task_id"] == task_id), None)
        evidence = pred.get("evidence", []) if pred else []
        features[f"{method}_evidence_count"] = len(evidence)
        features[f"{method}_has_evidence"] = len(evidence) > 0
        if evidence:
            features[f"{method}_top_score"] = evidence[0].get("score", 0.0)
            features[f"{method}_max_score"] = max(
                e.get("score", 0.0) for e in evidence
            )
            # Top evidence channel/why
            top = evidence[0]
            features[f"{method}_top_channels"] = top.get("channels", [])
            features[f"{method}_top_why"] = top.get("why", [])
        else:
            features[f"{method}_top_score"] = 0.0
            features[f"{method}_max_score"] = 0.0
            features[f"{method}_top_channels"] = []
            features[f"{method}_top_why"] = []

    return features


# ── Sweep strategy routing ──────────────────────────────────────────────


def is_query_noise(
    query: str,
    is_negative_noise_query_fn,
    is_vague_multi_word_query_fn,
    is_compound_snake_case_noise_fn,
) -> bool:
    """Check if query is negative/vague/noise using R17 heuristics."""
    return (
        is_negative_noise_query_fn(query)
        or is_vague_multi_word_query_fn(query)
        or is_compound_snake_case_noise_fn(query)
    )


def route_rrf_score_min(
    threshold: float,
    predictions_by_method: dict[str, list[dict]],
    task_id: str,
    repo_id: str,
    query: str,
) -> tuple[list[dict], str, str, dict[str, Any]]:
    """Use RRF if top RRF score >= threshold, else empty."""
    rrf_pred = next(
        (p for p in predictions_by_method.get("rrf", []) if p["task_id"] == task_id),
        None,
    )
    rrf_evidence = rrf_pred.get("evidence", []) if rrf_pred else []
    top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0
    features = {"rrf_top_score": top_score, "threshold": threshold}

    if top_score >= threshold and rrf_evidence:
        return rrf_evidence, f"rrf_score_min_{threshold}", "rrf", features
    return [], f"rrf_score_min_{threshold}_empty", "empty", features


def route_rrf_score_min_regex_or_symbol(
    threshold: float,
    predictions_by_method: dict[str, list[dict]],
    task_id: str,
    repo_id: str,
    query: str,
) -> tuple[list[dict], str, str, dict[str, Any]]:
    """Use RRF if top RRF score >= threshold AND (regex_has or symbol_has)."""
    rrf_pred = next(
        (p for p in predictions_by_method.get("rrf", []) if p["task_id"] == task_id),
        None,
    )
    regex_pred = next(
        (p for p in predictions_by_method.get("regex", []) if p["task_id"] == task_id),
        None,
    )
    symbol_pred = next(
        (p for p in predictions_by_method.get("symbol", []) if p["task_id"] == task_id),
        None,
    )

    rrf_evidence = rrf_pred.get("evidence", []) if rrf_pred else []
    regex_has = bool(regex_pred and regex_pred.get("evidence"))
    symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))
    top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0

    features = {
        "rrf_top_score": top_score,
        "threshold": threshold,
        "regex_has": regex_has,
        "symbol_has": symbol_has,
    }

    if top_score >= threshold and (regex_has or symbol_has) and rrf_evidence:
        return rrf_evidence, f"rrf_score_min_{threshold}_regex_or_symbol", "rrf", features
    return [], f"rrf_score_min_{threshold}_regex_or_symbol_empty", "empty", features


def route_rrf_score_min_symbol(
    threshold: float,
    predictions_by_method: dict[str, list[dict]],
    task_id: str,
    repo_id: str,
    query: str,
) -> tuple[list[dict], str, str, dict[str, Any]]:
    """Use RRF if top RRF score >= threshold AND symbol_has."""
    rrf_pred = next(
        (p for p in predictions_by_method.get("rrf", []) if p["task_id"] == task_id),
        None,
    )
    symbol_pred = next(
        (p for p in predictions_by_method.get("symbol", []) if p["task_id"] == task_id),
        None,
    )

    rrf_evidence = rrf_pred.get("evidence", []) if rrf_pred else []
    symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))
    top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0

    features = {
        "rrf_top_score": top_score,
        "threshold": threshold,
        "symbol_has": symbol_has,
    }

    if top_score >= threshold and symbol_has and rrf_evidence:
        return rrf_evidence, f"rrf_score_min_{threshold}_symbol", "rrf", features
    return [], f"rrf_score_min_{threshold}_symbol_empty", "empty", features


def route_query_noise_plus_rrf_score_min(
    threshold: float,
    predictions_by_method: dict[str, list[dict]],
    task_id: str,
    repo_id: str,
    query: str,
    is_negative_noise_query_fn,
    is_vague_multi_word_query_fn,
    is_compound_snake_case_noise_fn,
) -> tuple[list[dict], str, str, dict[str, Any]]:
    """If R17 negative/vague/noise query then empty, else RRF if score >= threshold."""
    noise = is_query_noise(
        query,
        is_negative_noise_query_fn,
        is_vague_multi_word_query_fn,
        is_compound_snake_case_noise_fn,
    )

    features: dict[str, Any] = {"query_noise": noise, "threshold": threshold}

    if noise:
        features["guard"] = "query_noise_guard"
        return [], f"query_noise_plus_rrf_score_min_{threshold}_noise_guard", "empty", features

    rrf_pred = next(
        (p for p in predictions_by_method.get("rrf", []) if p["task_id"] == task_id),
        None,
    )
    rrf_evidence = rrf_pred.get("evidence", []) if rrf_pred else []
    top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0
    features["rrf_top_score"] = top_score

    if top_score >= threshold and rrf_evidence:
        return rrf_evidence, f"query_noise_plus_rrf_score_min_{threshold}", "rrf", features
    return [], f"query_noise_plus_rrf_score_min_{threshold}_empty", "empty", features


def route_query_noise_plus_rrf_agree_min(
    threshold: float,
    predictions_by_method: dict[str, list[dict]],
    task_id: str,
    repo_id: str,
    query: str,
    is_negative_noise_query_fn,
    is_vague_multi_word_query_fn,
    is_compound_snake_case_noise_fn,
) -> tuple[list[dict], str, str, dict[str, Any]]:
    """If R17 negative/vague/noise then empty, else RRF if score >= threshold and regex_or_symbol."""
    noise = is_query_noise(
        query,
        is_negative_noise_query_fn,
        is_vague_multi_word_query_fn,
        is_compound_snake_case_noise_fn,
    )

    regex_pred = next(
        (p for p in predictions_by_method.get("regex", []) if p["task_id"] == task_id),
        None,
    )
    symbol_pred = next(
        (p for p in predictions_by_method.get("symbol", []) if p["task_id"] == task_id),
        None,
    )
    regex_has = bool(regex_pred and regex_pred.get("evidence"))
    symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))

    features: dict[str, Any] = {
        "query_noise": noise,
        "threshold": threshold,
        "regex_has": regex_has,
        "symbol_has": symbol_has,
    }

    if noise:
        features["guard"] = "query_noise_guard"
        return [], f"query_noise_plus_rrf_agree_min_{threshold}_noise_guard", "empty", features

    rrf_pred = next(
        (p for p in predictions_by_method.get("rrf", []) if p["task_id"] == task_id),
        None,
    )
    rrf_evidence = rrf_pred.get("evidence", []) if rrf_pred else []
    top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0
    features["rrf_top_score"] = top_score

    if top_score >= threshold and (regex_has or symbol_has) and rrf_evidence:
        return (
            rrf_evidence,
            f"query_noise_plus_rrf_agree_min_{threshold}",
            "rrf",
            features,
        )
    return (
        [],
        f"query_noise_plus_rrf_agree_min_{threshold}_empty",
        "empty",
        features,
    )


# ── Strategy family builder ─────────────────────────────────────────────


def build_strategy_family(thresholds: list[float]) -> list[dict[str, Any]]:
    """Build the full family of strategies to sweep.

    Each strategy dict has: name, type, and optional threshold.
    """
    strategies: list[dict[str, Any]] = []

    # Baselines
    for method in METHODS:
        strategies.append({"name": method, "type": "baseline"})

    # R17 fixed references
    strategies.append({"name": "query_only_router_v0", "type": "r17_fixed"})
    strategies.append({"name": "rrf_guarded_by_symbol_regex", "type": "r17_fixed"})

    # Sweep configs
    for t in thresholds:
        strategies.append(
            {"name": f"rrf_score_min_{t}", "type": "sweep", "threshold": t}
        )
        strategies.append(
            {
                "name": f"rrf_score_min_{t}_regex_or_symbol",
                "type": "sweep",
                "threshold": t,
            }
        )
        strategies.append(
            {"name": f"rrf_score_min_{t}_symbol", "type": "sweep", "threshold": t}
        )
        strategies.append(
            {
                "name": f"query_noise_plus_rrf_score_min_{t}",
                "type": "sweep",
                "threshold": t,
            }
        )
        strategies.append(
            {
                "name": f"query_noise_plus_rrf_agree_min_{t}",
                "type": "sweep",
                "threshold": t,
            }
        )

    return strategies


def apply_sweep_strategy(
    strategy: dict[str, Any],
    tasks: list[dict],
    predictions_by_method: dict[str, list[dict]],
    r17_helpers: dict,
) -> list[dict]:
    """Apply a strategy to produce predictions.

    Route decisions are made using only public query + prediction features.
    Labels/gold are NOT accessed.
    """
    name = strategy["name"]
    stype = strategy["type"]
    threshold = strategy.get("threshold", 0.0)

    results: list[dict] = []

    for task in tasks:
        task_id = task["task_id"]
        query = task["query"]
        repo_id = task.get("repo_id", "")

        # Extract public features (no labels)
        route_features = extract_query_features(
            query, predictions_by_method, task_id, repo_id
        )

        evidence: list[dict] = []
        route_decision = ""
        selected_method = ""

        if stype == "baseline":
            # Pass through method predictions directly
            preds = predictions_by_method.get(name, [])
            pred = next((p for p in preds if p["task_id"] == task_id), None)
            evidence = pred.get("evidence", []) if pred else []
            route_decision = f"baseline_{name}"
            selected_method = name

        elif stype == "r17_fixed":
            if name == "query_only_router_v0":
                evidence, route_decision, selected_method = r17_helpers[
                    "route_query_only_v0"
                ](query, predictions_by_method, task_id, repo_id)
            elif name == "rrf_guarded_by_symbol_regex":
                evidence, route_decision, selected_method = r17_helpers[
                    "route_rrf_guarded_by_symbol_regex"
                ](predictions_by_method, task_id, repo_id)

        elif stype == "sweep":
            if name.startswith("rrf_score_min_") and name.endswith("_symbol"):
                evidence, route_decision, selected_method, _ = (
                    route_rrf_score_min_symbol(
                        threshold, predictions_by_method, task_id, repo_id, query
                    )
                )
            elif name.startswith("rrf_score_min_") and name.endswith("_regex_or_symbol"):
                evidence, route_decision, selected_method, _ = (
                    route_rrf_score_min_regex_or_symbol(
                        threshold, predictions_by_method, task_id, repo_id, query
                    )
                )
            elif name.startswith("rrf_score_min_"):
                evidence, route_decision, selected_method, _ = (
                    route_rrf_score_min(
                        threshold, predictions_by_method, task_id, repo_id, query
                    )
                )
            elif name.startswith("query_noise_plus_rrf_agree_min_"):
                evidence, route_decision, selected_method, _ = (
                    route_query_noise_plus_rrf_agree_min(
                        threshold,
                        predictions_by_method,
                        task_id,
                        repo_id,
                        query,
                        r17_helpers["is_negative_noise_query"],
                        r17_helpers["is_vague_multi_word_query"],
                        r17_helpers["is_compound_snake_case_noise"],
                    )
                )
            elif name.startswith("query_noise_plus_rrf_score_min_"):
                evidence, route_decision, selected_method, _ = (
                    route_query_noise_plus_rrf_score_min(
                        threshold,
                        predictions_by_method,
                        task_id,
                        repo_id,
                        query,
                        r17_helpers["is_negative_noise_query"],
                        r17_helpers["is_vague_multi_word_query"],
                        r17_helpers["is_compound_snake_case_noise"],
                    )
                )

        results.append(
            {
                "task_id": task_id,
                "query": query,
                "method": name,
                "repo_id": repo_id,
                "evidence": evidence,
                "returncode": 0,
                "strategy_name": name,
                "selected_method": selected_method,
                "route_decision": route_decision,
                "route_features": route_features,
            }
        )

    return results


# ── Repo holdout split ──────────────────────────────────────────────────


def compute_repo_split(
    tasks: list[dict], train_count: int = TRAIN_REPO_COUNT
) -> tuple[list[str], list[str], dict[str, str]]:
    """Deterministic repo-holdout split: first N train, rest holdout, sorted by repo_id."""
    all_repos = sorted(set(t.get("repo_id", "") for t in tasks))
    train_repos = all_repos[:train_count]
    holdout_repos = all_repos[train_count:]
    assignment = {}
    for r in train_repos:
        assignment[r] = "train"
    for r in holdout_repos:
        assignment[r] = "holdout"
    return train_repos, holdout_repos, assignment


def split_predictions(
    predictions: list[dict], assignment: dict[str, str], split: str
) -> list[dict]:
    """Filter predictions to a specific split (train or holdout)."""
    return [p for p in predictions if assignment.get(p.get("repo_id", ""), "") == split]


def split_gold(
    gold: dict[str, dict], tasks: list[dict], assignment: dict[str, str], split: str
) -> dict[str, dict]:
    """Filter gold labels to a specific split."""
    task_ids = {
        t["task_id"]
        for t in tasks
        if assignment.get(t.get("repo_id", ""), "") == split
    }
    return {tid: g for tid, g in gold.items() if tid in task_ids}


# ── Pareto frontier ─────────────────────────────────────────────────────


def compute_pareto_frontier(
    strategy_metrics: dict[str, dict[str, Any]],
    maximize_keys: list[str],
    minimize_keys: list[str],
) -> list[dict[str, Any]]:
    """Compute Pareto frontier over strategy metrics.

    A strategy is Pareto-optimal if no other strategy is better or equal on
    all dimensions and strictly better on at least one.
    """
    names = list(strategy_metrics.keys())
    # Build objective vectors: maximize keys as-is, minimize keys negated
    vectors: dict[str, list[float]] = {}
    for name in names:
        m = strategy_metrics[name]
        vec = []
        for k in maximize_keys:
            vec.append(m.get(k, -float("inf")))
        for k in minimize_keys:
            vec.append(-m.get(k, float("inf")))
        vectors[name] = vec

    pareto: list[str] = []
    for name in names:
        dominated = False
        v = vectors[name]
        for other in names:
            if other == name:
                continue
            ov = vectors[other]
            # Check if 'other' dominates 'name':
            # other >= name on all dims, and strictly > on at least one
            all_ge = all(ov[i] >= v[i] for i in range(len(v)))
            any_gt = any(ov[i] > v[i] for i in range(len(v)))
            if all_ge and any_gt:
                dominated = True
                break
        if not dominated:
            pareto.append(name)

    # Return strategy names + metrics
    result = []
    for name in sorted(pareto):
        entry: dict[str, Any] = {"strategy_name": name}
        for k in maximize_keys + minimize_keys:
            val = strategy_metrics[name].get(k)
            if val is not None:
                entry[k] = val
        result.append(entry)

    return result


# ── Candidate selection ─────────────────────────────────────────────────


def select_calibration_candidate(
    strategy_metrics: dict[str, dict[str, Any]],
    rrf_train_metrics: dict[str, Any],
    strategies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select recommended calibration candidate from train split.

    Eligible if:
      - train negative_nonempty_rate@10 <= 0.05
      - train file_recall@1 >= (RRF_train file_recall@1 - 0.05)

    Among eligible, maximize train MRR, then minimize token_waste@10.
    If still tied, preserve deterministic strategy generation order.

    If no eligible, choose highest (FileRecall@1 - negative_nonempty penalty)
    and mark no_candidate_met_constraints.
    """
    rrf_recall1 = rrf_train_metrics.get("file_recall@1", 0.0)
    rrf_mrr = rrf_train_metrics.get("mrr", 0.0)

    eligible: list[tuple[str, dict[str, Any]]] = []
    ineligible: list[tuple[str, float, dict[str, Any]]] = []

    for strategy in strategies:
        name = strategy["name"]
        m = strategy_metrics.get(name)
        if m is None:
            continue

        neg_nonempty = m.get("negative_nonempty_rate@10", 1.0)
        recall1 = m.get("file_recall@1", 0.0)

        if neg_nonempty <= 0.05 and recall1 >= (rrf_recall1 - 0.05):
            eligible.append((name, m))
        else:
            score = recall1 - neg_nonempty * 2.0
            ineligible.append((name, score, m))

    if eligible:
        # Sort by MRR desc, then token_waste asc
        eligible.sort(key=lambda x: (-x[1].get("mrr", 0.0), x[1].get("token_waste@10", 1.0)))
        best_name, best_metrics = eligible[0]
        return {
            "strategy_name": best_name,
            "selection_rule": (
                "eligible if train negative_nonempty_rate@10<=0.05 AND "
                "train FileRecall@1>=(RRF_train FileRecall@1 - 0.05); "
                "among eligible maximize train MRR, then minimize token_waste@10, "
                "then preserve deterministic strategy generation order"
            ),
            "met_constraints": True,
            "metrics": best_metrics,
            "eligible_count": len(eligible),
        }

    # No eligible candidate
    ineligible.sort(key=lambda x: -x[1])
    best_name, _, best_metrics = ineligible[0] if ineligible else ("none", 0.0, {})
    return {
        "strategy_name": best_name,
        "selection_rule": (
            "no_candidate_met_constraints: fallback to highest "
            "(FileRecall@1 - 2*negative_nonempty)"
        ),
        "met_constraints": False,
        "metrics": best_metrics,
        "eligible_count": 0,
    }


# ── Markdown generation ─────────────────────────────────────────────────


def _fmt(val: Any) -> str:
    if isinstance(val, float):
        return f"{val:.4f}"
    if val is None:
        return "N/A"
    return str(val)


def generate_markdown_report(
    all_strategy_metrics: dict[str, dict[str, dict[str, Any]]],
    split_repos: dict[str, Any],
    thresholds: list[float],
    pareto_frontier: list[dict[str, Any]],
    selected_candidate: dict[str, Any],
    deltas: dict[str, dict[str, float]],
    holdout_deltas: dict[str, dict[str, float]],
    stress_deltas: dict[str, dict[str, float]],
    safety_issues: list[str],
    source_safety: dict[str, Any],
    conclusions: list[str],
    caveats: list[str],
) -> str:
    lines = [
        "# R18 Threshold/Guard Calibration Sweep",
        "",
        "**Eval-layer research only. Does NOT change Rust core.**",
        "",
        "## Safety",
        "",
    ]

    if safety_issues:
        for issue in safety_issues:
            lines.append(f"- {issue}")
        lines.append("")
    else:
        lines.append("All source safety gates passed.")
        lines.append(
            "Citation safety is inherited from source validated predictions; "
            "no new citation validation is claimed."
        )
        lines.append("")

    lines.append("### Source Report Safety Summary")
    lines.append("")
    for key, val in source_safety.items():
        lines.append(f"- {key}: {val}")
    lines.append("")

    # Split info
    lines.append("## Repo Split")
    lines.append("")
    lines.append(f"- Train repos ({len(split_repos['train'])}): {', '.join(split_repos['train'])}")
    lines.append(f"- Holdout repos ({len(split_repos['holdout'])}): {', '.join(split_repos['holdout'])}")
    lines.append("")

    # Thresholds
    lines.append("## Sweep Thresholds")
    lines.append("")
    lines.append(f"{thresholds}")
    lines.append("")

    # Strategy metrics tables
    metric_keys = [
        "file_recall@1", "mrr", "span_f0.5@10",
        "token_waste@10",
        "hard_negative_hit_rate@10",
        "negative_nonempty_rate@10",
    ]

    for split_name in ["full_medium", "train_medium", "holdout_medium", "stress"]:
        sm = all_strategy_metrics.get(split_name, {})
        lines.append(f"## Strategy Metrics ({split_name})")
        lines.append("")
        if not sm:
            lines.append("_No data_")
        else:
            # Show top strategies: baselines + R17 fixed + best sweep
            show_strategies = list(METHODS) + [
                "query_only_router_v0",
                "rrf_guarded_by_symbol_regex",
            ]
            # Add candidate and top 5 sweep by negative_nonempty
            sweep_names = sorted(
                [n for n in sm if n not in METHODS and n not in [
                    "query_only_router_v0", "rrf_guarded_by_symbol_regex"
                ]],
                key=lambda n: sm[n].get("negative_nonempty_rate@10", 1.0),
            )
            show_strategies.extend(sweep_names[:5])
            if selected_candidate.get("strategy_name") not in show_strategies:
                show_strategies.append(selected_candidate.get("strategy_name", ""))

            header = "| Strategy | " + " | ".join(metric_keys) + " |"
            separator = "|---|" + "|".join("---" for _ in metric_keys) + "|"
            lines.append(header)
            lines.append(separator)

            for sname in show_strategies:
                if sname not in sm:
                    continue
                m = sm[sname]
                row = f"| {sname} |"
                for k in metric_keys:
                    val = m.get(k)
                    row += f" {_fmt(val)} |"
                lines.append(row)
        lines.append("")

    # Selected candidate
    lines.append("## Selected Calibration Candidate")
    lines.append("")
    lines.append(f"- **Strategy**: {selected_candidate.get('strategy_name', 'N/A')}")
    lines.append(f"- **Selection Rule**: {selected_candidate.get('selection_rule', 'N/A')}")
    lines.append(f"- **Met Constraints**: {selected_candidate.get('met_constraints', False)}")
    lines.append("")

    # Deltas vs RRF
    lines.append("### Selected Candidate Deltas vs RRF")
    lines.append("")
    for split_label, d in [
        ("Full R15-M", deltas),
        ("Holdout R15-M", holdout_deltas),
        ("R15-stress", stress_deltas),
    ]:
        if d and isinstance(d, dict):
            lines.append(f"**{split_label}:**")
            for k, v in d.items():
                if not isinstance(v, (int, float)):
                    continue
                sign = "+" if v >= 0 else ""
                lines.append(f"- {k}: {sign}{v:.4f}")
            lines.append("")

    # Pareto frontier
    lines.append("## Pareto Frontier (Full R15-M)")
    lines.append("")
    lines.append("Dimensions: maximize FileRecall@1, SpanF0.5@10; minimize negative_nonempty_rate@10, hard_negative_hit_rate@10")
    lines.append("")
    for entry in pareto_frontier:
        lines.append(f"- **{entry['strategy_name']}**: " + ", ".join(
            f"{k}={_fmt(entry.get(k))}" for k in [
                "file_recall@1", "span_f0.5@10",
                "negative_nonempty_rate@10", "hard_negative_hit_rate@10",
            ] if k in entry
        ))
    lines.append("")

    # Conclusions
    lines.append("## Conclusions")
    lines.append("")
    for i, conclusion in enumerate(conclusions, 1):
        lines.append(f"{i}. {conclusion}")
    lines.append("")

    # Caveats
    lines.append("## Caveats")
    lines.append("")
    for caveat in caveats:
        lines.append(f"- {caveat}")
    lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R18 Threshold/Guard Calibration Sweep"
    )
    parser.add_argument(
        "--openlocus",
        default="target/debug/openlocus",
        help="Path to openlocus binary",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root directory",
    )
    parser.add_argument(
        "--out",
        default="runs/r18-calibration-sweep.json",
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Reuse existing R18-owned source reports if present",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    out_path = (workspace / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Import R17 helpers
    r17 = _import_r17_helpers(workspace)

    # ── Step 1: Ensure R15 benchmark reports exist (R18-owned) ──────────

    runs_dir = workspace / "runs"
    openlocus = str(r17["resolve_path"](args.openlocus, workspace))
    r15m_report_path = workspace / "runs" / "r18-r15-m.json"
    r15stress_report_path = workspace / "runs" / "r18-r15-stress.json"

    if not args.skip_run:
        print("R18 Calibration Sweep: Running R15 benchmark matrices")
        runs_config = [
            {
                "name": "R15-M",
                "cmd": [
                    "python3",
                    str(workspace / "eval" / "r15_benchmark.py"),
                    "--manifest",
                    "fixtures/r15/dataset_manifest.json",
                    "--openlocus",
                    openlocus,
                    "--methods",
                    "regex,bm25,symbol,rrf",
                    "--tier",
                    "M",
                    "--out",
                    str(r15m_report_path),
                ],
            },
            {
                "name": "R15-stress",
                "cmd": [
                    "python3",
                    str(workspace / "eval" / "r15_benchmark.py"),
                    "--manifest",
                    "fixtures/r15/dataset_manifest.json",
                    "--openlocus",
                    openlocus,
                    "--methods",
                    "regex,bm25,symbol,rrf",
                    "--tier",
                    "stress",
                    "--out",
                    str(r15stress_report_path),
                ],
            },
        ]
        for config in runs_config:
            print(f"  Running: {' '.join(config['cmd'])}")
            result = subprocess.run(
                config["cmd"], check=False, capture_output=False, text=True, cwd=str(workspace)
            )
            if result.returncode != 0:
                print(
                    f"CRITICAL: {config['name']} failed with exit code {result.returncode}",
                    file=sys.stderr,
                )
                sys.exit(1)
        prediction_artifacts = materialize_owned_prediction_artifacts(runs_dir)
    else:
        print("R18 Calibration Sweep: --skip-run, reusing existing R18 reports")
        if not r15m_report_path.exists() or not r15stress_report_path.exists():
            print(
                "CRITICAL: --skip-run requires R18-owned source reports "
                "runs/r18-r15-m.json and runs/r18-r15-stress.json",
                file=sys.stderr,
            )
            sys.exit(1)
        prediction_artifacts = require_owned_prediction_artifacts(runs_dir)

    # ── Step 2: Verify safety gates on source reports ───────────────────

    print("Verifying safety gates on source reports...")

    all_safety_issues: list[str] = []

    r15m_report = r17["load_report"](r15m_report_path)
    r15stress_report = r17["load_report"](r15stress_report_path)

    all_safety_issues.extend(r17["verify_safety_gates"](r15m_report, "R15-M"))
    all_safety_issues.extend(r17["verify_safety_gates"](r15stress_report, "R15-stress"))

    if all_safety_issues:
        print("CRITICAL: Source report safety gate failures:", file=sys.stderr)
        for issue in all_safety_issues:
            print(f"  {issue}", file=sys.stderr)
        sys.exit(1)

    print("  Source safety gates: PASSED")

    # ── Step 3: Load public tasks and validated method predictions ───────

    fixtures_dir = workspace / "fixtures" / "r15"

    medium_tasks = r17["load_jsonl"](fixtures_dir / "tasks" / "medium.jsonl")
    stress_tasks = r17["load_jsonl"](fixtures_dir / "tasks" / "stress.jsonl")

    if not medium_tasks:
        print("ERROR: No medium tasks found", file=sys.stderr)
        sys.exit(1)
    if not stress_tasks:
        print("ERROR: No stress tasks found", file=sys.stderr)
        sys.exit(1)

    print(f"  Tasks: R15-M={len(medium_tasks)}, R15-stress={len(stress_tasks)}")

    # Load only R18-owned prediction artifacts. Generic r15-* prediction files
    # are never used directly in R18 because they may have been produced by a
    # prior benchmark run.

    def load_predictions_for_tier(tier_name: str) -> dict[str, list[dict]]:
        preds: dict[str, list[dict]] = {}
        for method in METHODS:
            pred_path = owned_prediction_path(runs_dir, tier_name, method)
            if not pred_path.exists():
                print(
                    f"ERROR: Prediction file not found: {pred_path}",
                    file=sys.stderr,
                )
                sys.exit(1)
            preds[method] = r17["load_jsonl"](pred_path)
        return preds

    medium_preds = load_predictions_for_tier("medium")
    stress_preds = load_predictions_for_tier("stress")

    # ── Step 4: Build strategy family and apply routing ──────────────────
    # IMPORTANT: Route phase happens BEFORE labels are loaded for scoring or
    # baseline consistency checking. All routing decisions below use only
    # public tasks + R18-owned prediction features.

    print("Building strategy family and applying routing...")

    strategies = build_strategy_family(SWEEP_THRESHOLDS)
    print(f"  Strategy count: {len(strategies)}")

    # Route tier data: all strategies for both tiers
    # NOTE: Route phase uses tasks + predictions only (no labels)
    all_strategy_predictions: dict[str, dict[str, list[dict]]] = {}

    route_tier_data = {
        "R15-M": (medium_tasks, medium_preds),
        "R15-stress": (stress_tasks, stress_preds),
    }

    for strategy in strategies:
        name = strategy["name"]
        all_strategy_predictions[name] = {}

        for tier_name, (tasks, preds) in route_tier_data.items():
            routed = apply_sweep_strategy(strategy, tasks, preds, r17)
            all_strategy_predictions[name][tier_name] = routed

    # ── Step 5: Load gold labels, verify consistency, score strategies ───
    # Labels are loaded here, AFTER all routing decisions have been made.
    # This preserves a strict ROUTE(public tasks + validated predictions) / SCORE(labels)
    # boundary for the experiment.

    print("Scoring all strategies...")

    # Reload labels (separate from consistency check to enforce boundary)
    medium_labels = r17["load_jsonl"](fixtures_dir / "labels" / "medium.jsonl")
    stress_labels = r17["load_jsonl"](fixtures_dir / "labels" / "stress.jsonl")
    medium_gold = {l["task_id"]: l for l in medium_labels}
    stress_gold = {l["task_id"]: l for l in stress_labels}

    print("Verifying baseline prediction consistency...")
    recomputed_medium: dict[str, dict[str, Any]] = {}
    recomputed_stress: dict[str, dict[str, Any]] = {}
    for method in METHODS:
        recomputed_medium[method] = r17["score_predictions"](
            medium_preds[method], medium_gold
        )
        recomputed_stress[method] = r17["score_predictions"](
            stress_preds[method], stress_gold
        )

    consistency_issues: list[str] = []
    consistency_issues.extend(
        r17["check_baseline_prediction_consistency"](
            r15m_report, recomputed_medium, "R15-M"
        )
    )
    consistency_issues.extend(
        r17["check_baseline_prediction_consistency"](
            r15stress_report, recomputed_stress, "R15-stress"
        )
    )
    if consistency_issues:
        print("CRITICAL: Prediction/report consistency failures:", file=sys.stderr)
        for issue in consistency_issues:
            print(f"  {issue}", file=sys.stderr)
        sys.exit(1)
    print("  Baseline prediction consistency: PASSED")

    # Compute repo split for R15-M
    train_repos, holdout_repos, repo_assignment = compute_repo_split(medium_tasks)
    print(
        f"  Repo split: train={train_repos}, holdout={holdout_repos}"
    )

    # Score every strategy on full R15-M and R15-stress
    strategy_metrics: dict[str, dict[str, dict[str, Any]]] = {
        "full_medium": {},
        "train_medium": {},
        "holdout_medium": {},
        "stress": {},
    }

    for strategy in strategies:
        name = strategy["name"]

        # Full R15-M
        strategy_metrics["full_medium"][name] = r17["score_predictions"](
            all_strategy_predictions[name]["R15-M"], medium_gold
        )

        # Train R15-M
        train_preds = split_predictions(
            all_strategy_predictions[name]["R15-M"], repo_assignment, "train"
        )
        train_gold = split_gold(medium_gold, medium_tasks, repo_assignment, "train")
        strategy_metrics["train_medium"][name] = r17["score_predictions"](
            train_preds, train_gold
        )

        # Holdout R15-M
        holdout_preds = split_predictions(
            all_strategy_predictions[name]["R15-M"], repo_assignment, "holdout"
        )
        holdout_gold = split_gold(medium_gold, medium_tasks, repo_assignment, "holdout")
        strategy_metrics["holdout_medium"][name] = r17["score_predictions"](
            holdout_preds, holdout_gold
        )

        # R15-stress
        strategy_metrics["stress"][name] = r17["score_predictions"](
            all_strategy_predictions[name]["R15-stress"], stress_gold
        )

    # ── Step 7: Select calibration candidate ─────────────────────────────

    print("Selecting calibration candidate...")

    selected_candidate = select_calibration_candidate(
        strategy_metrics["train_medium"],
        strategy_metrics["train_medium"].get("rrf", {}),
        strategies,
    )

    # Compute deltas for selected candidate vs RRF and vs symbol
    cand_name = selected_candidate["strategy_name"]
    rrf_full = strategy_metrics["full_medium"].get("rrf", {})
    symbol_full = strategy_metrics["full_medium"].get("symbol", {})
    cand_full = strategy_metrics["full_medium"].get(cand_name, {})

    cand_deltas = r17["compute_deltas"](cand_full, rrf_full)

    rrf_holdout = strategy_metrics["holdout_medium"].get("rrf", {})
    cand_holdout = strategy_metrics["holdout_medium"].get(cand_name, {})
    cand_holdout_deltas = r17["compute_deltas"](cand_holdout, rrf_holdout)

    rrf_stress = strategy_metrics["stress"].get("rrf", {})
    cand_stress = strategy_metrics["stress"].get(cand_name, {})
    cand_stress_deltas = r17["compute_deltas"](cand_stress, rrf_stress)

    # Also compute deltas vs symbol for holdout and stress
    symbol_holdout = strategy_metrics["holdout_medium"].get("symbol", {})
    symbol_stress = strategy_metrics["stress"].get("symbol", {})

    cand_holdout_vs_symbol = r17["compute_deltas"](cand_holdout, symbol_holdout)
    cand_stress_vs_symbol = r17["compute_deltas"](cand_stress, symbol_stress)

    # ── Step 8: Compute Pareto frontier ──────────────────────────────────

    print("Computing Pareto frontier...")

    pareto_frontier = compute_pareto_frontier(
        strategy_metrics["full_medium"],
        maximize_keys=["file_recall@1", "span_f0.5@10"],
        minimize_keys=["negative_nonempty_rate@10", "hard_negative_hit_rate@10"],
    )

    # ── Step 9: Build source safety summary ─────────────────────────────

    source_safety: dict[str, Any] = {
        "R15-M_safety_passed": r15m_report.get("safety_passed", False),
        "R15-M_canary_passed": r15m_report.get("canary_retrieval", {}).get(
            "passed", False
        ),
        "R15-stress_safety_passed": r15stress_report.get("safety_passed", False),
        "R15-stress_canary_passed": r15stress_report.get("canary_retrieval", {}).get(
            "passed", False
        ),
        "citation_inherited_from_validated_methods": True,
        "baseline_prediction_consistency_checked": True,
        "citation_hash_checked_all_methods": all(
            r15m_report.get("metrics", {})
            .get(m, {})
            .get("citation_hash_checked", False)
            or r15m_report.get("metrics", {})
            .get(m, {})
            .get("citation_not_applicable", False)
            for m in METHODS
        )
        and all(
            r15stress_report.get("metrics", {})
            .get(m, {})
            .get("citation_hash_checked", False)
            or r15stress_report.get("metrics", {})
            .get(m, {})
            .get("citation_not_applicable", False)
            for m in METHODS
        ),
    }

    # ── Step 10: Generate conclusions ────────────────────────────────────

    # Extract actual numbers for conclusions
    cand_neg_m = cand_full.get("negative_nonempty_rate@10")
    rrf_neg_m = rrf_full.get("negative_nonempty_rate@10")
    symbol_neg_m = symbol_full.get("negative_nonempty_rate@10")

    cand_recall1_m = cand_full.get("file_recall@1")
    rrf_recall1_m = rrf_full.get("file_recall@1")

    cand_neg_holdout = cand_holdout.get("negative_nonempty_rate@10")
    rrf_neg_holdout = rrf_holdout.get("negative_nonempty_rate@10")

    cand_neg_stress = cand_stress.get("negative_nonempty_rate@10")
    rrf_neg_stress = rrf_stress.get("negative_nonempty_rate@10")
    symbol_neg_stress = symbol_stress.get("negative_nonempty_rate@10")

    cand_holdout_recall1 = cand_holdout.get("file_recall@1")
    rrf_holdout_recall1 = rrf_holdout.get("file_recall@1")

    conclusions: list[str] = []

    # Conclusion 1: Calibration candidate assessment
    met = selected_candidate.get("met_constraints", False)
    if met:
        neg_delta = (cand_neg_m or 0) - (rrf_neg_m or 0)
        recall_delta = (cand_recall1_m or 0) - (rrf_recall1_m or 0)
        if neg_delta < 0 and recall_delta >= -0.05:
            conclusions.append(
                f"Calibration is promising: selected candidate "
                f"'{cand_name}' improves R15-M negative_nonempty from "
                f"{rrf_neg_m:.3f} to {cand_neg_m:.3f} (delta {neg_delta:+.3f}) "
                f"with FileRecall@1 {cand_recall1_m:.3f} vs RRF {rrf_recall1_m:.3f} "
                f"(delta {recall_delta:+.3f}). Holdout result is reported separately; "
                f"selection did not use holdout/stress labels."
            )
        else:
            conclusions.append(
                f"Calibration candidate '{cand_name}' met train constraints but "
                f"R15-M negative_nonempty improvement is marginal or recall loss "
                f"exceeds tolerance. Further calibration needed."
            )
    else:
        conclusions.append(
            f"Calibration is NOT promising on current data: no candidate met "
            f"train constraints (negative_nonempty<=0.05 AND "
            f"FileRecall@1>=(RRF_train-0.05)). Best fallback: '{cand_name}'. "
            f"Threshold/guard choices on mined R15 data may be insufficient "
            f"without larger or human-verified validation."
        )

    # Conclusion 2: Holdout assessment
    if cand_neg_holdout is not None and rrf_neg_holdout is not None:
        holdout_neg_delta = cand_neg_holdout - rrf_neg_holdout
        holdout_recall_delta = (cand_holdout_recall1 or 0) - (rrf_holdout_recall1 or 0)
        if holdout_neg_delta < 0 and holdout_recall_delta >= -0.05:
            conclusions.append(
                f"Holdout supports candidate: negative_nonempty "
                f"{cand_neg_holdout:.3f} vs RRF {rrf_neg_holdout:.3f} "
                f"(delta {holdout_neg_delta:+.3f}), FileRecall@1 "
                f"{cand_holdout_recall1:.3f} vs {rrf_holdout_recall1:.3f} "
                f"(delta {holdout_recall_delta:+.3f})."
            )
        else:
            conclusions.append(
                f"Holdout does NOT fully validate candidate: negative_nonempty "
                f"{cand_neg_holdout:.3f} vs RRF {rrf_neg_holdout:.3f} "
                f"(delta {holdout_neg_delta:+.3f}), FileRecall@1 "
                f"{cand_holdout_recall1:.3f} vs {rrf_holdout_recall1:.3f} "
                f"(delta {holdout_recall_delta:+.3f}). "
                f"Calibration overfits train split or guard is too aggressive."
            )

    # Conclusion 3: Stress failure surface
    if symbol_neg_stress is not None and cand_neg_stress is not None:
        if cand_neg_stress > symbol_neg_stress:
            conclusions.append(
                f"R15-stress remains the critical failure surface: candidate "
                f"negative_nonempty {cand_neg_stress:.3f} remains above symbol "
                f"baseline {symbol_neg_stress:.3f}. Threshold/guard on "
                f"prediction features cannot fully suppress stress false positives."
            )
        else:
            conclusions.append(
                f"R15-stress candidate negative_nonempty {cand_neg_stress:.3f} "
                f"is at or below symbol baseline {symbol_neg_stress:.3f}. "
                f"However, stress tasks are few ({len(stress_tasks)}) and "
                f"results are not generalizable."
            )

    # Conclusion 4: Threshold/guard calibration is eval-layer
    conclusions.append(
        "Threshold/guard choices are calibrated on mined R15 data and require "
        "larger/human-verified validation before promotion. No core default "
        "promotion in R18; this is eval-layer calibration."
    )

    # Conclusion 5: No LLM/dense claims
    conclusions.append(
        "No LLM/dense/provider claims. All routing uses query text and "
        "prediction features only."
    )

    caveats = [
        "R18 is an eval-layer calibration sweep; does NOT change Rust core.",
        "Calibration is on mined R15 data; not human-verified.",
        "Repo-holdout split is deterministic but small (9 repos, 3 holdout); "
        "not a substitute for cross-dataset validation.",
        "R15-stress has only 19 tasks; metric estimates are noisy.",
        "Sweep thresholds are hand-chosen; exhaustive search would be exponential.",
        "Pareto frontier depends on chosen dimensions; different dimensions may "
        "yield different frontiers.",
        "No core default promotion unless both R15-M and R15-stress "
        "negative_nonempty improve without unacceptable recall/MRR regression.",
        "Citation safety is inherited from validated source predictions; "
        "no new citation validation is claimed for sweep-produced evidence.",
        "No LLM/dense/provider claims are made.",
        "Routing decisions are deterministic and reproducible from the same inputs.",
    ]

    # ── Step 11: Build JSON report ───────────────────────────────────────

    print("Building JSON report...")

    timestamp = datetime.now(timezone.utc).isoformat()

    # Build selected candidate details with deltas
    selected_detail: dict[str, Any] = {
        "strategy_name": cand_name,
        "selection_rule": selected_candidate["selection_rule"],
        "met_constraints": selected_candidate["met_constraints"],
        "eligible_count": selected_candidate.get("eligible_count", 0),
        "metrics": {
            "train_medium": strategy_metrics["train_medium"].get(cand_name, {}),
            "holdout_medium": strategy_metrics["holdout_medium"].get(cand_name, {}),
            "full_medium": strategy_metrics["full_medium"].get(cand_name, {}),
            "stress": strategy_metrics["stress"].get(cand_name, {}),
        },
        "deltas": {
            "full_medium_vs_rrf": cand_deltas,
            "holdout_medium_vs_rrf": cand_holdout_deltas,
            "holdout_medium_vs_symbol": cand_holdout_vs_symbol,
            "stress_vs_rrf": cand_stress_deltas,
            "stress_vs_symbol": cand_stress_vs_symbol,
        },
    }

    json_report = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "openlocus": openlocus,
        "workspace": str(workspace),
        "skip_run": args.skip_run,
        "source_reports": {
            "R15-M": {
                "path": str(r15m_report_path),
                "safety_passed": r15m_report.get("safety_passed", False),
                "canary_retrieval_passed": r15m_report.get(
                    "canary_retrieval", {}
                ).get("passed", False),
                "citation_hash_checked_all_methods": all(
                    r15m_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_hash_checked", False)
                    or r15m_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_not_applicable", False)
                    for m in METHODS
                ),
            },
            "R15-stress": {
                "path": str(r15stress_report_path),
                "safety_passed": r15stress_report.get("safety_passed", False),
                "canary_retrieval_passed": r15stress_report.get(
                    "canary_retrieval", {}
                ).get("passed", False),
                "citation_hash_checked_all_methods": all(
                    r15stress_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_hash_checked", False)
                    or r15stress_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_not_applicable", False)
                    for m in METHODS
                ),
            },
        },
        "prediction_artifacts": prediction_artifacts,
        "safety_summary": {
            "all_safety_passed": len(all_safety_issues) == 0,
            "issues": all_safety_issues,
        },
        "citation_inherited_from_validated_methods": True,
        "baseline_prediction_consistency_checked": True,
        "split_repos": {
            "train": train_repos,
            "holdout": holdout_repos,
        },
        "thresholds": SWEEP_THRESHOLDS,
        "strategies": [s["name"] for s in strategies],
        "strategy_metrics": {
            "full_medium": strategy_metrics["full_medium"],
            "train_medium": strategy_metrics["train_medium"],
            "holdout_medium": strategy_metrics["holdout_medium"],
            "stress": strategy_metrics["stress"],
        },
        "pareto_frontier": pareto_frontier,
        "selected_candidate": selected_detail,
        "conclusions": conclusions,
        "caveats": caveats,
        "remote_calls": 0,
        "dense_or_llm_claims": False,
        "core_changes": False,
    }

    out_path.write_text(
        json.dumps(json_report, indent=2) + "\n", encoding="utf-8"
    )

    # ── Step 12: Generate markdown report ────────────────────────────────

    md_content = generate_markdown_report(
        strategy_metrics,
        {"train": train_repos, "holdout": holdout_repos},
        SWEEP_THRESHOLDS,
        pareto_frontier,
        selected_candidate,
        cand_deltas,
        cand_holdout_deltas,
        cand_stress_deltas,
        all_safety_issues,
        source_safety,
        conclusions,
        caveats,
    )

    md_path = out_path.with_suffix(".md")
    md_path.write_text(md_content, encoding="utf-8")

    # ── Step 13: Write docs/en/r18-calibration-sweep.md ─────────────────────

    docs_r18 = workspace / "docs" / "r18-calibration-sweep.md"
    docs_r18.write_text(md_content, encoding="utf-8")

    # ── Step 14: Print summary ───────────────────────────────────────────

    print(f"\n{'='*60}")
    print("R18 Calibration Sweep Results")
    print(f"{'='*60}")

    for split_name in ["full_medium", "train_medium", "holdout_medium", "stress"]:
        sm = strategy_metrics[split_name]
        print(f"\n{split_name} (selected metrics):")
        display_names = list(dict.fromkeys(
            METHODS + ["query_only_router_v0", "rrf_guarded_by_symbol_regex", cand_name]
        ))
        for name in display_names:
            m = sm.get(name, {})
            if not m:
                continue
            recall1 = m.get("file_recall@1")
            mrr_val = m.get("mrr")
            neg = m.get("negative_nonempty_rate@10")
            span = m.get("span_f0.5@10")
            parts = []
            if recall1 is not None:
                parts.append(f"@1={recall1:.3f}")
            if mrr_val is not None:
                parts.append(f"MRR={mrr_val:.3f}")
            if span is not None:
                parts.append(f"SpanF0.5={span:.3f}")
            if neg is not None:
                parts.append(f"neg_nonempty={neg:.3f}")
            print(f"  {name}: {', '.join(parts)}")

    print(f"\nSelected candidate: {cand_name}")
    print(f"  Met constraints: {selected_candidate.get('met_constraints', False)}")

    if all_safety_issues:
        print(f"\nSafety issues: {len(all_safety_issues)}")
    else:
        print(f"\nAll safety checks passed")

    print(f"\nReport: {out_path}")
    print(f"Summary: {md_path}")
    print(f"Docs: {docs_r18}")

    if all_safety_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
