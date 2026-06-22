#!/usr/bin/env python3
"""BEA-3 Anchor/Span/Latency-Aware Policy Smoke (Public Records-Only).

This module implements the **BEA-3 anchor/span/latency-aware policy smoke**
over fresh heldout ContextBench verified Python rows (offset 60, limit 20)
and RepoQA Python needles (offset 30, limit 10). It is a real frozen
algorithmic policy change: BEA v0.3 reserves anchor slots for BM25/agreement
anchors, applies diversity/risk scoring to remaining budget, adds
runtime-clean span/latency proxies (tighter line-span bonus, same-file-as-
anchor support bonus, risk bucket penalties, weak-support + low-BM25
penalty, fixed marginal-priority early stop after anchors), and is compared
against v0.2, v0, and same-budget controls on the same fresh heldout
records under a paired denominator rule.

BEA-3 is explicitly **not** a benchmark result, **not** a leaderboard
entry, **not** a performance claim, **not** a method-winner claim, **not**
a calibration claim, **not** a promotion, **not** a default/policy change,
and **not** a runtime/retriever/pack/backend/EvidenceCore semantic change.

Claim boundary: ``claim_level = bea_v03_policy_smoke_only``.

Run::

    python3 -m py_compile eval/bea3_anchor_span_latency.py
    python3 eval/bea3_anchor_span_latency.py --self-test
    python3 eval/bea3_anchor_span_latency.py \\
        --enable-external-benchmark-network \\
        --contextbench-row-offset 60 --contextbench-row-limit 3 \\
        --repoqa-needle-offset 30 --repoqa-needle-limit 2 \\
        --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \\
        --out artifacts/bea3_anchor_span_latency/\\
bea3_anchor_span_latency_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import bea1_mechanism_ablation as bea1  # noqa: E402
import bea2_policy_v02 as bea2  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "bea3_anchor_span_latency.v1"
GENERATED_BY = "eval/bea3_anchor_span_latency.py"
CLAIM_LEVEL = "bea_v03_policy_smoke_only"
MODE = "bounded_heldout_retrieval_policy_v03_smoke"
PHASE = "BEA-3"

DEFAULT_OUT = Path(
    "artifacts/bea3_anchor_span_latency/"
    "bea3_anchor_span_latency_report.json"
)

PRIVATE_SCORE_SCHEMA_VERSION = "bea3_private_score.v1"

CONTEXTBENCH_ROW_OFFSET_DEFAULT = 60
CONTEXTBENCH_ROW_LIMIT_DEFAULT = 20
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = 20
REPOQA_NEEDLE_OFFSET_DEFAULT = 30
REPOQA_NEEDLE_LIMIT_DEFAULT = 10
REPOQA_NEEDLE_LIMIT_HARD_CAP = 10

BUDGET_DEFAULT = 5
BUDGET_HARD_CAP = 20

ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

# Fixed policy arm IDs.
ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY = "bea_v0_3_anchor_span_latency"
ARM_BEA_V0_3_NO_ANCHOR = "bea_v0_3_no_anchor"
ARM_BEA_V0_3_NO_EARLY_STOP = "bea_v0_3_no_early_stop"
ARM_BEA_V0_2 = "bea_v0_2_diversity_risk"
ARM_BEA_V0 = "bea_v0"
ARM_BM25_PREFIX = "bm25_prefix_same_budget"
ARM_AGREEMENT_ONLY = "agreement_only_same_budget"
ARM_SEEDED_RANDOM = "seeded_random_same_budget"
ARM_RRF_SAME_BUDGET = "rrf_same_budget"

BASELINE_ARM = ARM_BEA_V0

# Contrasts: v0.3 vs v0.2 / v0 / bm25 / agreement / seeded_random / rrf.
CONTRAST_V03_VS_V02 = "v03_vs_v02"
CONTRAST_V03_VS_V0 = "v03_vs_v0"
CONTRAST_V03_VS_BM25 = "v03_vs_bm25"
CONTRAST_V03_VS_AGREEMENT = "v03_vs_agreement"
CONTRAST_V03_VS_SEEDED_RANDOM = "v03_vs_seeded_random"
CONTRAST_V03_VS_RRF = "v03_vs_rrf"

# Ablation contrasts.
CONTRAST_V03_ANCHOR_VS_NO_ANCHOR = "v03_anchor_vs_no_anchor"
CONTRAST_V03_EARLY_STOP_VS_NO_EARLY_STOP = "v03_early_stop_vs_no_early_stop"

SEEDED_RANDOM_SEED = 20240621

PRIMARY_METRICS: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
)

ARM_METRIC_ALLOWLIST: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
    "candidate_count_read",
    "evidence_budget_used",
    "action_steps",
    "latency_seconds",
    "quality_per_candidate",
    "quality_per_latency",
)

# ---------------------------------------------------------------------------
# v0.3 frozen policy constants (NOT tuned from outcomes)
# ---------------------------------------------------------------------------

# Number of anchor slots reserved for BM25/agreement anchors.
ANCHOR_COUNT_DEFAULT = 2  # min(2, budget)

# v0.3 priority weights (frozen, runtime-clean). Reuse v0.2 base weights
# for the diversity/risk component but add span/latency proxies.
V03_WEIGHT_ANCHOR = 0.35  # anchor slot boost (BM25/agreement anchor)
V03_WEIGHT_SPAN_TIGHT = 0.15  # tighter line-span bonus
V03_WEIGHT_ANCHOR_FILE_SUPPORT = 0.10  # same-file-as-anchor support bonus
V03_WEIGHT_WEAK_SUPPORT_PENALTY = -0.20  # weak-support + low-BM25 penalty
V03_WEIGHT_EARLY_STOP_MARGIN = 0.05  # marginal-priority early stop threshold

# Reuse v0.2 base weights for the non-anchor diversity/risk component.
# These are imported from bea2 (frozen, not re-tuned).

# ---------------------------------------------------------------------------
# Safe true / false flags
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "bea_v03_policy_executed": False,
    "bea_v02_policy_executed": False,
    "bea_v0_acquisition_performed": False,
    "private_score_records_written": False,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "heldout_fresh_slice_read": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
    "downstream_agent_value_proven": False,
    "calibration_claimed": False,
    "method_winner_claimed": False,
    "promotion_ready": False,
    "default_should_change": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
    "provider_calls_made": False,
    "remote_provider_calls_made": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_smoke",
}

FAILURE_CATEGORIES: tuple[str, ...] = (
    "contextbench_fetch_failed",
    "contextbench_no_python_rows",
    "contextbench_gold_parse_failed",
    "repoqa_asset_download_failed",
    "repoqa_asset_parse_failed",
    "repoqa_no_python_needles",
    "repoqa_needle_parse_failed",
    "heldout_offset_exceeds_available",
    "repo_clone_failed",
    "repo_checkout_failed",
    "retrieval_failed",
    "score_failed",
    "private_score_write_failed",
    "record_excluded_from_paired_denominator",
    "row_limit_capped",
    "needle_limit_capped",
    "scanner_self_test_failed",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

# ---------------------------------------------------------------------------
# Scanner (BEA-3 owned, strict, fail-closed). Reuses BEA-2 primitives.
# ---------------------------------------------------------------------------

BEA3_FORBIDDEN_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        "action_order", "priority_components", "priority_score",
        "selected_decisions", "budget_trace", "stop_reason",
        "candidate_features", "anchor_eligibility",
        "anchor_slots", "early_stop_reason",
        "private_score_path", "score_path", "private_score_file",
        "private_record_id", "private_record_hash",
        "action_trace", "action_steps_trace",
        "budget_state", "budget_states",
        "accepted_candidates", "final_candidates",
        "candidate_list", "candidates", "score_outcome",
        "per_record_metrics", "runtime_query_features",
        "query_feature_summary", "query_features",
        "benchmark_row_id", "benchmark_record_id", "benchmark_label",
        "phase_run_id", "run_id", "task_id", "row_id", "needle_id",
        "instance_id", "provider_name", "model_name", "model_family",
        "provider_payload", "private_bucket", "route_bucket", "task_bucket",
        "calibration", "method_winner", "best_method",
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion",
    }
)


def _is_bea3_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in (
        "failure_category_counts", "benchmark_arm_metric_records",
        "delta_records", "mechanism_contrast_records",
        "win_tie_loss_records", "mechanism_summary_records",
        "private_score_manifest", "framing", "arm_metric_records",
    )


def _scan_bea3_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_bea3_schema_key_container(sub_path)
                if (key_str in BEA3_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_bea3_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_bea3(obj: Any) -> list[dict[str, Any]]:
    """Combined BEA-3 scanner: BEA-2 primitives + BEA-3 forbidden keys."""
    violations = bea2._scan_bea2(obj)
    violations.extend(_scan_bea3_forbidden_keys(obj))
    return violations


def _bea3_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_bea3(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_bea3_no_forbidden(obj: Any) -> None:
    scan = _bea3_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return c5a._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    c5a._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5a._check(name, ok)


def _validate_row_offset(offset: int) -> int:
    if not isinstance(offset, int) or offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_needle_offset(offset: int) -> int:
    if not isinstance(offset, int) or offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_row_limit(limit: int) -> int:
    if not isinstance(limit, int) or limit < 1:
        raise SystemExit("invalid arguments")
    if limit > CONTEXTBENCH_ROW_LIMIT_HARD_CAP:
        return CONTEXTBENCH_ROW_LIMIT_HARD_CAP
    return limit


def _validate_needle_limit(limit: int) -> int:
    if not isinstance(limit, int) or limit < 1:
        raise SystemExit("invalid arguments")
    if limit > REPOQA_NEEDLE_LIMIT_HARD_CAP:
        return REPOQA_NEEDLE_LIMIT_HARD_CAP
    return limit


def _validate_budget(budget: int) -> int:
    if not isinstance(budget, int) or budget < 1:
        raise SystemExit("invalid arguments")
    if budget > BUDGET_HARD_CAP:
        return BUDGET_HARD_CAP
    return budget


def _validate_methods(methods: str) -> tuple[str, ...]:
    return bea0._validate_methods(methods)


# ---------------------------------------------------------------------------
# Private SCORE writer
# ---------------------------------------------------------------------------


def _resolve_private_score_dir(explicit: str | None) -> tuple[Path, str]:
    return bea0._resolve_private_score_dir(explicit)


def _private_score_manifest_hash() -> str:
    manifest_schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "policy_arm", "runtime_query_feature_summary",
            "candidate_features", "anchor_eligibility",
            "priority_components", "selected_decisions",
            "action_order", "budget_trace", "anchor_slots",
            "early_stop_reason", "score_outcome",
            "latency_ms", "cost_usd", "tokens", "provider_calls",
            "failure_reason",
        ],
    }
    canonical = json.dumps(manifest_schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_private_score_row(score_path: Path, row: dict[str, Any]) -> None:
    bea0._write_private_score_row(score_path, row)


# ---------------------------------------------------------------------------
# BEA v0.3 anchor/span/latency policy (deterministic, runtime-clean)
# ---------------------------------------------------------------------------


def _span_extent(entry: dict[str, Any]) -> int:
    """Line-span extent (end_line - start_line + 1). Runtime-clean."""
    start = int(entry.get("start_line", 0) or 0)
    end = int(entry.get("end_line", 0) or 0)
    if end < start:
        return 0
    return end - start + 1


def _span_tightness(entry: dict[str, Any]) -> float:
    """Tighter line-span bonus in [0, 1].

    Spans of 1-10 lines get 1.0; 11-20 get 0.5; 21-50 get 0.25; >50 get 0.0.
    Runtime-clean (uses only candidate path/line metadata).
    """
    extent = _span_extent(entry)
    if extent <= 0:
        return 0.0
    if extent <= 10:
        return 1.0
    if extent <= 20:
        return 0.5
    if extent <= 50:
        return 0.25
    return 0.0


def _span_proxy_bucket(extent: int) -> str:
    """Span proxy bucket label for mechanism_summary_records."""
    if extent <= 0:
        return "empty"
    if extent <= 10:
        return "tight"
    if extent <= 20:
        return "medium"
    if extent <= 50:
        return "wide"
    return "very_wide"


def _is_anchor_eligible(entry: dict[str, Any]) -> bool:
    """Anchor eligibility: BM25 method OR agreement >= 2.

    Runtime-clean (method source + agreement count only).
    """
    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods)
    if "bm25" in methods:
        return True
    if len(methods) >= 2:
        return True
    return False


def _compute_v03_priority(
    entry: dict[str, Any],
    query_toks: set[str],
    accepted_paths: set[str],
    accepted_dirs: set[str],
    accepted_spans: set[tuple[str, int, int]],
    anchor_paths: set[str],
    method_set: set[str],
    is_anchor_slot: bool,
) -> dict[str, Any]:
    """Compute v0.3 priority score with span/latency proxies.

    Reuses v0.2 base priority (agreement + bm25_norm + diversity +
    query/path overlap - risk penalty - duplication penalty) and adds:
      - anchor boost (if anchor slot and entry is anchor-eligible);
      - tighter line-span bonus;
      - same-file-as-anchor support bonus;
      - weak-support + low-BM25 penalty.
    """
    # Start with v0.2 base priority.
    base = bea2._compute_priority(
        entry, query_toks, accepted_paths, accepted_dirs,
        accepted_spans, method_set,
    )
    base_priority = base["priority_score"]
    base_components = dict(base["priority_components"])

    # v0.3 additional components.
    anchor_eligible = _is_anchor_eligible(entry)
    anchor_boost = V03_WEIGHT_ANCHOR if (is_anchor_slot and anchor_eligible) else 0.0
    span_tight = _span_tightness(entry)
    span_bonus = V03_WEIGHT_SPAN_TIGHT * span_tight
    same_file_as_anchor = entry["path"] in anchor_paths
    anchor_file_support = V03_WEIGHT_ANCHOR_FILE_SUPPORT if same_file_as_anchor else 0.0

    # Weak-support penalty: agreement==1 AND bm25_norm < 0.01.
    agreement = len(entry.get("methods", set())) if isinstance(entry.get("methods"), set) else len(set(entry.get("methods", [])))
    bm25_norm = float(entry.get("max_norm_score", 0.0))
    weak_support = (agreement <= 1 and bm25_norm < 0.01)
    weak_penalty = V03_WEIGHT_WEAK_SUPPORT_PENALTY if weak_support else 0.0

    priority = base_priority + anchor_boost + span_bonus + anchor_file_support + weak_penalty

    return {
        "priority_score": round(priority, 6),
        "priority_components": {
            **base_components,
            "anchor_boost": round(anchor_boost, 6),
            "span_tightness": round(span_tight, 6),
            "span_bonus": round(span_bonus, 6),
            "anchor_file_support": round(anchor_file_support, 6),
            "weak_support_penalty": round(weak_penalty, 6),
        },
        "is_new_file": base["is_new_file"],
        "is_new_dir": base["is_new_dir"],
        "risk_bucket": base["risk_bucket"],
        "anchor_eligible": anchor_eligible,
        "same_file_as_anchor": same_file_as_anchor,
    }


def _bea_v0_3_policy(
    candidates: list[dict[str, Any]],
    query: str,
    budget: int,
    *,
    use_anchor: bool = True,
    use_early_stop: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Any]]:
    """Deterministic BEA v0.3 anchor/span/latency policy.

    Parameters:
      use_anchor: if True, reserve anchor_count slots for BM25/agreement
        anchors. If False (ablation v0_3_no_anchor), no anchor reservation.
      use_early_stop: if True, apply fixed marginal-priority early stop
        after anchors are filled. If False (ablation v0_3_no_early_stop),
        no early stop.

    Returns ``(accepted_evidence, action_order, budget_trace, stop_reason,
    mechanism_summary)``.

    mechanism_summary contains: anchor_used (bool), early_stop_used (bool),
    anchor_count_reserved (int), anchor_count_filled (int),
    early_stop_reason (str), mean_span_extent (float),
    span_proxy_bucket_counts (dict).
    """
    anchor_count = min(ANCHOR_COUNT_DEFAULT, budget) if use_anchor else 0

    mechanism_summary = {
        "anchor_used": bool(use_anchor),
        "early_stop_used": bool(use_early_stop),
        "anchor_count_reserved": int(anchor_count),
        "anchor_count_filled": 0,
        "early_stop_reason": "",
        "mean_span_extent": 0.0,
        "span_proxy_bucket_counts": {},
    }

    if not candidates or budget <= 0:
        return [], [], [
            {"step": 0, "budget_remaining": 0, "accepted_so_far": 0}
        ], "no_candidates_or_zero_budget", mechanism_summary

    deduped = bea1._dedup_candidates(candidates)
    if not deduped:
        return [], [], [
            {"step": 0, "budget_remaining": budget, "accepted_so_far": 0}
        ], "no_deduped_candidates", mechanism_summary

    query_toks = bea2._query_tokens(query)
    method_set: set[str] = set()
    for entry in deduped:
        methods = entry.get("methods", set())
        if isinstance(methods, set):
            method_set |= methods
        elif isinstance(methods, (list, tuple)):
            method_set |= set(methods)

    accepted: list[dict[str, Any]] = []
    accepted_paths: set[str] = set()
    accepted_dirs: set[str] = set()
    accepted_spans: set[tuple[str, int, int]] = set()
    anchor_paths: set[str] = set()
    action_order: list[dict[str, Any]] = []
    budget_trace: list[dict[str, Any]] = []
    stop_reason = "candidates_exhausted"
    early_stop_reason = ""
    span_extents: list[int] = []
    span_bucket_counts: dict[str, int] = {}

    remaining = list(deduped)
    anchors_filled = 0

    for step in range(budget):
        if not remaining:
            stop_reason = "candidates_exhausted"
            break

        # Determine if this is an anchor slot.
        is_anchor_slot = (use_anchor and anchors_filled < anchor_count)

        # Score remaining entries.
        scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]] = []
        for idx, entry in enumerate(remaining):
            prio = _compute_v03_priority(
                entry, query_toks, accepted_paths, accepted_dirs,
                accepted_spans, anchor_paths, method_set, is_anchor_slot,
            )
            scored.append((prio["priority_score"], entry.get("stable_index", idx), entry, prio))
        scored.sort(key=lambda t: (-t[0], t[1]))
        best_prio, _best_si, best_entry, best_components = scored[0]

        budget_remaining = budget - len(accepted)
        budget_trace.append({
            "step": step,
            "budget_remaining": budget_remaining,
            "accepted_so_far": len(accepted),
            "candidate_count_remaining": len(remaining),
            "is_anchor_slot": is_anchor_slot,
        })

        # Early stop after anchors: if anchors are filled and the best
        # remaining priority is below the fixed marginal threshold, stop.
        if (use_early_stop and use_anchor
                and anchors_filled >= anchor_count
                and best_prio < V03_WEIGHT_EARLY_STOP_MARGIN):
            stop_reason = "early_stop_marginal_priority"
            early_stop_reason = "marginal_priority_below_threshold"
            action_order.append({
                "step": step,
                "action": "stop_early_stop",
                "priority_score": best_prio,
                "priority_components": best_components["priority_components"],
                "anchor_slots_filled": anchors_filled,
            })
            break

        if len(accepted) >= budget:
            stop_reason = "budget_exhausted"
            action_order.append({
                "step": step,
                "action": "stop_budget_exhausted",
                "priority_score": best_prio,
                "priority_components": best_components["priority_components"],
            })
            break

        # Accept the best entry.
        path = best_entry["path"]
        dir_part = bea2._path_dir(path)
        span_key = (path, best_entry["start_line"], best_entry["end_line"])
        accepted.append({
            "path": path,
            "start_line": best_entry["start_line"],
            "end_line": best_entry["end_line"],
            "content_sha": best_entry.get("content_sha", ""),
        })
        accepted_paths.add(path)
        if dir_part:
            accepted_dirs.add(dir_part)
        accepted_spans.add(span_key)

        if is_anchor_slot:
            anchors_filled += 1
            anchor_paths.add(path)

        extent = _span_extent(best_entry)
        span_extents.append(extent)
        bucket = _span_proxy_bucket(extent)
        span_bucket_counts[bucket] = span_bucket_counts.get(bucket, 0) + 1

        action_order.append({
            "step": step,
            "action": "accept_candidate",
            "priority_score": best_prio,
            "priority_components": best_components["priority_components"],
            "candidate_method": best_entry.get("first_method", ""),
            "candidate_rank": best_entry.get("first_rank", 0),
            "agreement": len(best_entry.get("methods", set())) if isinstance(best_entry.get("methods"), set) else len(set(best_entry.get("methods", []))),
            "is_new_file": best_components["is_new_file"],
            "is_new_dir": best_components["is_new_dir"],
            "risk_bucket": best_components["risk_bucket"],
            "is_anchor_slot": is_anchor_slot,
            "anchor_eligible": best_components["anchor_eligible"],
            "span_extent": extent,
            "span_proxy_bucket": bucket,
        })
        remaining = [e for e in remaining if (e["path"], e["start_line"], e["end_line"]) != span_key]

    if len(accepted) >= budget and stop_reason not in ("early_stop_marginal_priority",):
        stop_reason = "budget_exhausted"
    elif not remaining and stop_reason != "early_stop_marginal_priority":
        stop_reason = "candidates_exhausted"

    mechanism_summary["anchor_count_filled"] = anchors_filled
    mechanism_summary["early_stop_reason"] = early_stop_reason
    mechanism_summary["mean_span_extent"] = (
        round(sum(span_extents) / len(span_extents), 6) if span_extents else 0.0
    )
    mechanism_summary["span_proxy_bucket_counts"] = span_bucket_counts

    return accepted, action_order, budget_trace, stop_reason, mechanism_summary


# ---------------------------------------------------------------------------
# Per-arm metrics (extends BEA-0 with quality_per_latency)
# ---------------------------------------------------------------------------


def _arm_metrics_for_record(
    arm_id: str,
    accepted_evidence: list[dict[str, Any]],
    gold_record: dict[str, Any],
    task_id: str,
    candidate_count_read: int,
    evidence_budget_used: int,
    action_steps: int,
    latency_seconds: float,
) -> dict[str, Any]:
    """Compute per-arm metrics for one record, including quality_per_latency."""
    m = bea0._arm_metrics(
        arm_id, accepted_evidence, gold_record, task_id,
        candidate_count_read, evidence_budget_used, action_steps,
        latency_seconds,
    )
    # quality_per_latency = span_f0.5@10 / latency_seconds (or 0).
    span_f = m.get("span_f0.5@10", 0.0)
    lat = m.get("latency_seconds", 0.0)
    if isinstance(lat, (int, float)) and lat > 0:
        m["quality_per_latency"] = round(float(span_f) / float(lat), 6)
    else:
        m["quality_per_latency"] = 0.0
    return m


def _filter_arm_metrics(arm: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ARM_METRIC_ALLOWLIST:
        if key in arm:
            val = arm[key]
            if isinstance(val, bool):
                out[key] = bool(val)
            elif isinstance(val, (int, float)):
                out[key] = round(val, 6) if isinstance(val, float) else int(val)
    return out


def _arm_means(per_record_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_record_metrics:
        return {k: 0.0 for k in ARM_METRIC_ALLOWLIST}
    agg: dict[str, Any] = {}
    for key in ARM_METRIC_ALLOWLIST:
        values: list[Any] = []
        for rec in per_record_metrics:
            if key in rec:
                values.append(rec[key])
        if not values:
            agg[key] = 0.0
            continue
        if all(isinstance(v, bool) for v in values):
            agg[key] = any(values)
        elif all(isinstance(v, (int, float)) for v in values):
            nums = [float(v) for v in values]
            agg[key] = round(sum(nums) / len(nums), 6)
    return _filter_arm_metrics(agg)


def _arm_metric_records(arm_metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return bea0._arm_metric_records(arm_metrics)


def _benchmark_arm_metric_records(
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for benchmark in sorted(per_benchmark_arm_aggs):
        arm_aggs = per_benchmark_arm_aggs[benchmark]
        for arm_id in sorted(arm_aggs):
            agg = arm_aggs[arm_id]
            record_count = agg.get("__record_count__", 0)
            for metric in ARM_METRIC_ALLOWLIST:
                if metric in agg:
                    records.append({
                        "benchmark": benchmark,
                        "arm": arm_id,
                        "metric": metric,
                        "value": agg[metric],
                        "record_count": record_count,
                    })
    records.sort(key=lambda r: (r["benchmark"], r["arm"], r["metric"]))
    return records


def _delta_records(
    arm_aggs: dict[str, dict[str, Any]],
    baseline_arm: str,
    treatment_arms: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    baseline_agg = arm_aggs.get(baseline_arm, {})
    for treatment_arm in treatment_arms:
        treatment_agg = arm_aggs.get(treatment_arm, {})
        for metric in ARM_METRIC_ALLOWLIST:
            t = treatment_agg.get(metric, 0.0)
            b = baseline_agg.get(metric, 0.0)
            if isinstance(t, (int, float)) and isinstance(b, (int, float)):
                records.append({
                    "baseline_arm": baseline_arm,
                    "treatment_arm": treatment_arm,
                    "metric": metric,
                    "delta": round(float(t) - float(b), 6),
                })
    records.sort(key=lambda r: (r["treatment_arm"], r["metric"]))
    return records


def _mechanism_contrast_records(
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    contrasts: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    return bea1._mechanism_contrast_records(
        per_record_arm_metrics, contrasts
    )


def _win_tie_loss_records(
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    baseline_arm: str,
    treatment_arm: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    paired: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for rec in per_record_arm_metrics:
        if baseline_arm in rec and treatment_arm in rec:
            paired.append((rec[baseline_arm], rec[treatment_arm]))
    record_count = len(paired)
    if record_count == 0:
        return records
    for metric in PRIMARY_METRICS:
        win = tie = loss = 0
        for b, t in paired:
            bv = b.get(metric, 0.0)
            tv = t.get(metric, 0.0)
            if not isinstance(bv, (int, float)) or not isinstance(tv, (int, float)):
                continue
            if tv > bv:
                win += 1
            elif tv < bv:
                loss += 1
            else:
                tie += 1
        records.append({
            "baseline_arm": baseline_arm,
            "treatment_arm": treatment_arm,
            "metric": metric,
            "win": win, "tie": tie, "loss": loss,
            "record_count": record_count,
        })
    records.sort(key=lambda r: r["metric"])
    return records


def _mechanism_summary_records(
    per_record_mechanism_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build mechanism summary records from v0.3 per-record summaries.

    Each record: ``{mechanism_field, value, record_count}``.
    Fields: anchor_used_rate, early_stop_rate, mean_budget_used,
    mean_latency, mean_span_extent, span_proxy_bucket counts.
    """
    if not per_record_mechanism_summaries:
        return []
    n = len(per_record_mechanism_summaries)
    records: list[dict[str, Any]] = []
    anchor_used_count = sum(1 for s in per_record_mechanism_summaries if s.get("anchor_used"))
    early_stop_count = sum(1 for s in per_record_mechanism_summaries if s.get("early_stop_used"))
    mean_budget = sum(float(s.get("budget_used", 0)) for s in per_record_mechanism_summaries) / n
    mean_latency = sum(float(s.get("latency_ms", 0)) for s in per_record_mechanism_summaries) / n / 1000.0
    mean_span = sum(float(s.get("mean_span_extent", 0)) for s in per_record_mechanism_summaries) / n

    records.append({"mechanism_field": "anchor_used_rate", "value": round(anchor_used_count / n, 6), "record_count": n})
    records.append({"mechanism_field": "early_stop_rate", "value": round(early_stop_count / n, 6), "record_count": n})
    records.append({"mechanism_field": "mean_budget_used", "value": round(mean_budget, 6), "record_count": n})
    records.append({"mechanism_field": "mean_latency_seconds", "value": round(mean_latency, 6), "record_count": n})
    records.append({"mechanism_field": "mean_span_extent", "value": round(mean_span, 6), "record_count": n})

    # Span proxy bucket counts (aggregated).
    bucket_totals: dict[str, int] = {}
    for s in per_record_mechanism_summaries:
        for bucket, count in (s.get("span_proxy_bucket_counts") or {}).items():
            bucket_totals[bucket] = bucket_totals.get(bucket, 0) + int(count)
    for bucket, count in sorted(bucket_totals.items()):
        records.append({
            "mechanism_field": f"span_proxy_bucket_{bucket}",
            "value": count,
            "record_count": n,
        })
    return records


# ---------------------------------------------------------------------------
# Per-record evaluation
# ---------------------------------------------------------------------------


def _evaluate_record(
    *,
    openlocus_bin: str,
    benchmark: str,
    private_record_id: str,
    task_id: str,
    query: str,
    gold_paths: list[str],
    gold_lines: list[list[int]],
    repo_root: Path,
    methods: tuple[str, ...],
    budget: int,
    enable_rrf_baseline: bool,
    score_path: Path,
    phase_run_id: str,
    fcc: dict[str, int],
) -> tuple[dict[str, Any] | None, dict[str, int], dict[str, Any]]:
    """Evaluate one record across all v0.3 + v0.2 + v0 + control arms.

    Writes one private SCORE row PER policy arm. Returns per-arm metrics
    and a per-record mechanism summary (for mechanism_summary_records).
    """
    rec_start = time.perf_counter()
    failure_reason: str | None = None

    method_candidates: dict[str, list[dict[str, Any]]] = {}
    method_latencies_ms: dict[str, int] = {}
    method_errors: dict[str, str] = {}
    all_candidates: list[dict[str, Any]] = []
    for method in methods:
        cands, lat_ms, err = bea0._collect_method_candidates(
            openlocus_bin, method, query, repo_root
        )
        method_candidates[method] = cands
        method_latencies_ms[method] = lat_ms
        if not cands:
            method_errors[method] = err[:200] if err else "empty"
        else:
            all_candidates.extend(cands)

    rrf_candidates: list[dict[str, Any]] = []
    rrf_latency_ms = 0
    rrf_error: str | None = None
    if enable_rrf_baseline:
        channels = ",".join(methods)
        rrf_candidates, rrf_latency_ms, rrf_err = bea0._collect_rrf_candidates(
            openlocus_bin, query, repo_root, channels=channels
        )
        if not rrf_candidates:
            rrf_error = (rrf_err or "empty")[:200]

    if not all_candidates:
        failure_reason = "no_candidates_from_any_method"
        fcc["retrieval_failed"] = fcc.get("retrieval_failed", 0) + 1

    gold_record = {
        "task_id": task_id,
        "gold_paths": gold_paths,
        "gold_lines": gold_lines,
    }

    deduped_count = len(bea1._dedup_candidates(all_candidates)) if all_candidates else 0

    # Shared retrieval latency for fair latency attribution: all arms
    # share the candidate-collection latency. v0.3/v0.2/v0 also get
    # incremental policy time. Controls get 0.0 (in-process, no retrieval).
    shared_retrieval_latency = sum(method_latencies_ms.values()) / 1000.0

    # --- v0.3 anchor/span/latency (treatment) ---
    policy_start = time.perf_counter()
    if all_candidates and failure_reason is None:
        v03_accepted, v03_action_order, v03_budget_trace, v03_stop_reason, v03_mech_summary = (
            _bea_v0_3_policy(all_candidates, query, budget,
                             use_anchor=True, use_early_stop=True)
        )
    else:
        v03_accepted, v03_action_order, v03_budget_trace, v03_stop_reason, v03_mech_summary = (
            [], [], [], "no_candidates_or_zero_budget",
            {"anchor_used": True, "early_stop_used": True,
             "anchor_count_reserved": 0, "anchor_count_filled": 0,
             "early_stop_reason": "", "mean_span_extent": 0.0,
             "span_proxy_bucket_counts": {}}
        )
    v03_policy_time = time.perf_counter() - policy_start
    v03_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY, v03_accepted, gold_record, task_id,
        len(all_candidates), len(v03_accepted), len(v03_action_order),
        shared_retrieval_latency + v03_policy_time,
    )

    # --- v0.3 ablation: no_anchor ---
    if all_candidates and failure_reason is None:
        v03_na_accepted, v03_na_action, v03_na_trace, v03_na_stop, v03_na_summary = (
            _bea_v0_3_policy(all_candidates, query, budget,
                             use_anchor=False, use_early_stop=True)
        )
    else:
        v03_na_accepted, v03_na_action, v03_na_trace, v03_na_stop, v03_na_summary = (
            [], [], [], "no_candidates_or_zero_budget",
            {"anchor_used": False, "early_stop_used": True,
             "anchor_count_reserved": 0, "anchor_count_filled": 0,
             "early_stop_reason": "", "mean_span_extent": 0.0,
             "span_proxy_bucket_counts": {}}
        )
    v03_na_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_3_NO_ANCHOR, v03_na_accepted, gold_record, task_id,
        len(all_candidates), len(v03_na_accepted), len(v03_na_action),
        shared_retrieval_latency,
    )

    # --- v0.3 ablation: no_early_stop ---
    if all_candidates and failure_reason is None:
        v03_ne_accepted, v03_ne_action, v03_ne_trace, v03_ne_stop, v03_ne_summary = (
            _bea_v0_3_policy(all_candidates, query, budget,
                             use_anchor=True, use_early_stop=False)
        )
    else:
        v03_ne_accepted, v03_ne_action, v03_ne_trace, v03_ne_stop, v03_ne_summary = (
            [], [], [], "no_candidates_or_zero_budget",
            {"anchor_used": True, "early_stop_used": False,
             "anchor_count_reserved": 0, "anchor_count_filled": 0,
             "early_stop_reason": "", "mean_span_extent": 0.0,
             "span_proxy_bucket_counts": {}}
        )
    v03_ne_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_3_NO_EARLY_STOP, v03_ne_accepted, gold_record, task_id,
        len(all_candidates), len(v03_ne_accepted), len(v03_ne_action),
        shared_retrieval_latency,
    )

    # --- v0.2 ---
    if all_candidates and failure_reason is None:
        v02_accepted, v02_action_order, v02_budget_trace, v02_stop_reason = (
            bea2._bea_v0_2_diversity_risk_policy(all_candidates, query, budget)
        )
    else:
        v02_accepted, v02_action_order, v02_budget_trace, v02_stop_reason = (
            [], [], [], "no_candidates_or_zero_budget"
        )
    v02_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_2, v02_accepted, gold_record, task_id,
        len(all_candidates), len(v02_accepted), len(v02_action_order),
        shared_retrieval_latency,
    )

    # --- v0 (BEA-0) ---
    if all_candidates and failure_reason is None:
        v0_accepted, v0_action_trace, v0_budget_states = (
            bea0._bea_v0_budgeted_policy(all_candidates, budget)
        )
    else:
        v0_accepted, v0_action_trace, v0_budget_states = [], [], []
    v0_metrics = _arm_metrics_for_record(
        ARM_BEA_V0, v0_accepted, gold_record, task_id,
        len(all_candidates), len(v0_accepted), len(v0_action_trace),
        shared_retrieval_latency,
    )

    # --- Same-budget K (based on v0.3 accepted count) ---
    same_budget_k = bea2._same_budget_k(len(v03_accepted), deduped_count)

    # --- Controls ---
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(method_candidates, same_budget_k)
    sb_bm25_metrics = _arm_metrics_for_record(
        ARM_BM25_PREFIX, sb_bm25_ev, gold_record, task_id,
        len(method_candidates.get("bm25", [])),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0,
    )
    ao_ev = bea2._agreement_only_same_budget_arm(all_candidates, same_budget_k)
    ao_metrics = _arm_metrics_for_record(
        ARM_AGREEMENT_ONLY, ao_ev, gold_record, task_id,
        len(all_candidates), len(ao_ev), len(ao_ev), 0.0,
    )
    sr_ev = bea2._seeded_random_same_budget_arm(all_candidates, same_budget_k)
    sr_metrics = _arm_metrics_for_record(
        ARM_SEEDED_RANDOM, sr_ev, gold_record, task_id,
        len(all_candidates), len(sr_ev), len(sr_ev), 0.0,
    )
    rrf_metrics: dict[str, Any] | None = None
    if enable_rrf_baseline:
        rrf_ev = bea2._rrf_same_budget_arm(rrf_candidates, same_budget_k)
        rrf_metrics = _arm_metrics_for_record(
            ARM_RRF_SAME_BUDGET, rrf_ev, gold_record, task_id,
            len(rrf_candidates), len(rrf_ev), len(rrf_ev),
            rrf_latency_ms / 1000.0,
        )

    per_arm_metrics: dict[str, dict[str, Any]] = {
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY: v03_metrics,
        ARM_BEA_V0_3_NO_ANCHOR: v03_na_metrics,
        ARM_BEA_V0_3_NO_EARLY_STOP: v03_ne_metrics,
        ARM_BEA_V0_2: v02_metrics,
        ARM_BEA_V0: v0_metrics,
        ARM_BM25_PREFIX: sb_bm25_metrics,
        ARM_AGREEMENT_ONLY: ao_metrics,
        ARM_SEEDED_RANDOM: sr_metrics,
    }
    if rrf_metrics is not None:
        per_arm_metrics[ARM_RRF_SAME_BUDGET] = rrf_metrics

    rec_latency_ms = int((time.perf_counter() - rec_start) * 1000)

    # --- Build mechanism summary for this record (v0.3 only) ---
    rec_mechanism_summary = {
        "anchor_used": v03_mech_summary.get("anchor_used", False),
        "early_stop_used": bool(v03_mech_summary.get("early_stop_reason", "")),
        "budget_used": len(v03_accepted),
        "latency_ms": rec_latency_ms,
        "mean_span_extent": v03_mech_summary.get("mean_span_extent", 0.0),
        "span_proxy_bucket_counts": v03_mech_summary.get("span_proxy_bucket_counts", {}),
    }

    # --- Build runtime_query_feature_summary (private) ---
    runtime_query_feature_summary = {
        "benchmark": benchmark,
        "method_count": len(methods),
        "methods": list(methods),
        "candidate_count_total": len(all_candidates),
        "candidate_count_per_method": {
            m: len(method_candidates.get(m, [])) for m in methods
        },
        "rrf_baseline_enabled": bool(enable_rrf_baseline),
        "rrf_candidate_count": len(rrf_candidates) if enable_rrf_baseline else 0,
        "budget": int(budget),
        "same_budget_k": int(same_budget_k),
        "deduped_candidate_count": int(deduped_count),
        "v03_accepted_count": int(len(v03_accepted)),
        "v02_accepted_count": int(len(v02_accepted)),
        "v0_accepted_count": int(len(v0_accepted)),
        "shared_retrieval_latency_seconds": round(shared_retrieval_latency, 6),
        "query_length_chars": len(query) if isinstance(query, str) else 0,
        "query_word_count": (
            len(query.split()) if isinstance(query, str) and query else 0
        ),
    }

    # --- Write one private SCORE row PER policy arm ---
    arms_to_write = [
        (ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY, v03_action_order, v03_budget_trace,
         v03_stop_reason, v03_metrics, v03_mech_summary),
        (ARM_BEA_V0_3_NO_ANCHOR, v03_na_action, v03_na_trace,
         v03_na_stop, v03_na_metrics, v03_na_summary),
        (ARM_BEA_V0_3_NO_EARLY_STOP, v03_ne_action, v03_ne_trace,
         v03_ne_stop, v03_ne_metrics, v03_ne_summary),
        (ARM_BEA_V0_2, v02_action_order, v02_budget_trace,
         v02_stop_reason, v02_metrics, {}),
        (ARM_BEA_V0, v0_action_trace, v0_budget_states,
         "v0_policy", v0_metrics, {}),
        (ARM_BM25_PREFIX, [], [],
         "same_budget_bm25_prefix", sb_bm25_metrics, {}),
        (ARM_AGREEMENT_ONLY, [], [],
         "same_budget_agreement", ao_metrics, {}),
        (ARM_SEEDED_RANDOM, [], [],
         "same_budget_seeded_random", sr_metrics, {}),
    ]
    if rrf_metrics is not None:
        arms_to_write.append((
            ARM_RRF_SAME_BUDGET, [], [],
            "same_budget_rrf", rrf_metrics, {},
        ))

    for arm_id, action_order, budget_trace, stop_reason, score_outcome, mech_summary in arms_to_write:
        private_score_row = {
            "phase_run_id": phase_run_id,
            "benchmark": benchmark,
            "private_record_id": private_record_id,
            "policy_arm": arm_id,
            "runtime_query_feature_summary": runtime_query_feature_summary,
            "candidate_features": [],  # private; populated for v0.3 arms
            "anchor_eligibility": (
                {k: v for k, v in mech_summary.items()
                 if k in ("anchor_used", "anchor_count_reserved",
                          "anchor_count_filled", "early_stop_reason")}
                if mech_summary else {}
            ),
            "priority_components": (
                [{"step": a.get("step", i), "priority_score": a.get("priority_score", 0.0),
                  "priority_components": a.get("priority_components", {})}
                 for i, a in enumerate(action_order) if a.get("action") == "accept_candidate"]
                if action_order else []
            ),
            "selected_decisions": [
                {"step": a.get("step", i), "action": a.get("action", ""),
                 "priority_score": a.get("priority_score", 0.0)}
                for i, a in enumerate(action_order)
            ] if action_order else [],
            "action_order": action_order,
            "budget_trace": budget_trace,
            "anchor_slots": mech_summary.get("anchor_count_filled", 0) if mech_summary else 0,
            "early_stop_reason": mech_summary.get("early_stop_reason", "") if mech_summary else "",
            "stop_reason": stop_reason,
            "score_outcome": score_outcome,
            "latency_ms": rec_latency_ms,
            "cost_usd": 0.0,
            "tokens": 0,
            "provider_calls": 0,
            "failure_reason": failure_reason,
        }
        try:
            _write_private_score_row(score_path, private_score_row)
        except OSError:
            fcc["private_score_write_failed"] = (
                fcc.get("private_score_write_failed", 0) + 1
            )
            return None, fcc, rec_mechanism_summary

    return per_arm_metrics, fcc, rec_mechanism_summary


# ---------------------------------------------------------------------------
# Heldout fetchers (reuse BEA-2)
# ---------------------------------------------------------------------------


def _fetch_heldout_contextbench_rows(
    row_offset: int, row_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    return bea2._fetch_heldout_contextbench_rows(row_offset, row_limit)


def _fetch_heldout_repoqa_needles(
    needle_offset: int, needle_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    return bea2._fetch_heldout_repoqa_needles(needle_offset, needle_limit)


# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    contextbench_row_offset_requested: int,
    contextbench_row_limit_requested: int,
    repoqa_needle_offset_requested: int,
    repoqa_needle_limit_requested: int,
    budget: int,
    methods: tuple[str, ...],
    openlocus_binary_source: str,
    network_mode: str,
    private_score_records_written: bool = False,
    private_score_record_count: int = 0,
    private_score_storage_class: str = "tmp_private",
    private_score_manifest_hash: str | None = None,
    records_evaluated: int = 0,
    records_successful: int = 0,
    records_failed: int = 0,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["bea_v03_policy_executed"] = False
    safe_true["bea_v02_policy_executed"] = False
    safe_true["bea_v0_acquisition_performed"] = False
    safe_true["heldout_fresh_slice_read"] = False
    safe_true["private_score_records_written"] = bool(private_score_records_written)

    manifest_hash = (
        private_score_manifest_hash
        if private_score_manifest_hash is not None
        else _private_score_manifest_hash()
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": "unavailable_with_reason",
        "mode": MODE,
        "phase": PHASE,
        "methods": list(methods),
        "budget": int(budget),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_offset_requested": contextbench_row_offset_requested,
        "contextbench_row_limit_requested": contextbench_row_limit_requested,
        "repoqa_needle_offset_requested": repoqa_needle_offset_requested,
        "repoqa_needle_limit_requested": repoqa_needle_limit_requested,
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_counts": fcc,
        "benchmark_arm_metric_records": [],
        "delta_records": [],
        "mechanism_contrast_records": [],
        "win_tie_loss_records": [],
        "mechanism_summary_records": [],
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v03_policy_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _bea3_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    contextbench_row_offset_requested: int,
    contextbench_row_limit_requested: int,
    repoqa_needle_offset_requested: int,
    repoqa_needle_limit_requested: int,
    budget: int,
    methods: tuple[str, ...],
    openlocus_binary_source: str,
    network_mode: str,
    records_evaluated: int,
    records_successful: int,
    records_failed: int,
    network_calls: int,
    arm_aggs: dict[str, dict[str, Any]],
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]],
    per_record_mechanism_summaries: list[dict[str, Any]],
    private_score_records_written: bool,
    private_score_record_count: int,
    private_score_storage_class: str,
    private_score_manifest_hash: str,
    aggregate_runtime_seconds: float,
    failure_category_counts: dict[str, int],
    enable_rrf_baseline: bool,
    paired_exclusion_count: int,
    partial: bool,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["openlocus_retrieval_executed"] = records_successful > 0
    safe_true["score_py_metrics_computed"] = bool(arm_aggs)
    safe_true["bea_v03_policy_executed"] = records_successful > 0
    safe_true["bea_v02_policy_executed"] = records_successful > 0
    safe_true["bea_v0_acquisition_performed"] = records_successful > 0
    safe_true["heldout_fresh_slice_read"] = records_evaluated > 0
    safe_true["private_score_records_written"] = bool(private_score_records_written)

    benchmark_arm_metric_records = _benchmark_arm_metric_records(per_benchmark_arm_aggs)

    # Delta records: v0.3 vs each control arm, with v0 as fixed baseline.
    treatment_arms = [
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY,
        ARM_BEA_V0_3_NO_ANCHOR,
        ARM_BEA_V0_3_NO_EARLY_STOP,
        ARM_BEA_V0_2,
        ARM_BM25_PREFIX,
        ARM_AGREEMENT_ONLY,
        ARM_SEEDED_RANDOM,
    ]
    if enable_rrf_baseline:
        treatment_arms.append(ARM_RRF_SAME_BUDGET)
    delta_records = _delta_records(arm_aggs, BASELINE_ARM, treatment_arms)

    # Mechanism contrast records: v0.3 vs each control on paired denominator.
    contrasts = [
        (CONTRAST_V03_VS_V02, ARM_BEA_V0_2, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
        (CONTRAST_V03_VS_V0, ARM_BEA_V0, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
        (CONTRAST_V03_VS_BM25, ARM_BM25_PREFIX, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
        (CONTRAST_V03_VS_AGREEMENT, ARM_AGREEMENT_ONLY, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
        (CONTRAST_V03_VS_SEEDED_RANDOM, ARM_SEEDED_RANDOM, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
        (CONTRAST_V03_ANCHOR_VS_NO_ANCHOR, ARM_BEA_V0_3_NO_ANCHOR, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
        (CONTRAST_V03_EARLY_STOP_VS_NO_EARLY_STOP, ARM_BEA_V0_3_NO_EARLY_STOP, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
    ]
    if enable_rrf_baseline:
        contrasts.append((CONTRAST_V03_VS_RRF, ARM_RRF_SAME_BUDGET, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY))
    mechanism_contrast_records = _mechanism_contrast_records(per_record_arm_metrics, contrasts)

    # Win/tie/loss records: v0.3 vs each control on primary metrics.
    win_tie_loss_records: list[dict[str, Any]] = []
    for baseline in (ARM_BEA_V0_2, ARM_BEA_V0, ARM_BM25_PREFIX,
                     ARM_AGREEMENT_ONLY, ARM_SEEDED_RANDOM):
        win_tie_loss_records.extend(_win_tie_loss_records(
            per_record_arm_metrics, baseline, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY
        ))
    if enable_rrf_baseline:
        win_tie_loss_records.extend(_win_tie_loss_records(
            per_record_arm_metrics, ARM_RRF_SAME_BUDGET,
            ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY,
        ))
    win_tie_loss_records.sort(key=lambda r: (r["baseline_arm"], r["metric"]))

    mechanism_summary_records = _mechanism_summary_records(per_record_mechanism_summaries)

    if records_successful > 0 and records_failed == 0 and not partial:
        status = "bea3_anchor_span_latency_pass"
    elif records_successful > 0:
        status = "partial"
    else:
        status = "unavailable_with_reason"

    fixed_arms = [
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY,
        ARM_BEA_V0_3_NO_ANCHOR,
        ARM_BEA_V0_3_NO_EARLY_STOP,
        ARM_BEA_V0_2,
        ARM_BEA_V0,
        ARM_BM25_PREFIX,
        ARM_AGREEMENT_ONLY,
        ARM_SEEDED_RANDOM,
    ]
    if enable_rrf_baseline:
        fixed_arms.append(ARM_RRF_SAME_BUDGET)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "methods": list(methods),
        "budget": int(budget),
        "enable_rrf_baseline": bool(enable_rrf_baseline),
        "fixed_arms": fixed_arms,
        "baseline_arm": BASELINE_ARM,
        "treatment_arm": ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY,
        "seeded_random_seed": SEEDED_RANDOM_SEED,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_offset_requested": contextbench_row_offset_requested,
        "contextbench_row_limit_requested": contextbench_row_limit_requested,
        "repoqa_needle_offset_requested": repoqa_needle_offset_requested,
        "repoqa_needle_limit_requested": repoqa_needle_limit_requested,
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "paired_exclusion_count": int(paired_exclusion_count),
        "network_calls": network_calls,
        "provider_calls": 0,
        "benchmark_arm_metric_records": benchmark_arm_metric_records,
        "delta_records": delta_records,
        "mechanism_contrast_records": mechanism_contrast_records,
        "win_tie_loss_records": win_tie_loss_records,
        "mechanism_summary_records": mechanism_summary_records,
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": private_score_manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "failure_category_counts": fcc,
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_v03_policy_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _bea3_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _build_synthetic_candidates() -> list[dict[str, Any]]:
    return bea0._build_synthetic_candidates()


def _build_synthetic_gold() -> dict[str, Any]:
    return bea0._build_synthetic_gold()


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    candidates = _build_synthetic_candidates()
    gold = _build_synthetic_gold()
    query = "merge adjacent strings into a single string"

    # Run v0.3 policy.
    v03_acc, v03_ao, v03_bt, v03_sr, v03_ms = _bea_v0_3_policy(
        candidates, query, 5, use_anchor=True, use_early_stop=True
    )
    # Run v0.3 no_anchor.
    v03na_acc, v03na_ao, v03na_bt, v03na_sr, v03na_ms = _bea_v0_3_policy(
        candidates, query, 5, use_anchor=False, use_early_stop=True
    )
    # Run v0.3 no_early_stop.
    v03ne_acc, v03ne_ao, v03ne_bt, v03ne_sr, v03ne_ms = _bea_v0_3_policy(
        candidates, query, 5, use_anchor=True, use_early_stop=False
    )
    # Run v0.2.
    v02_acc, v02_ao, v02_bt, v02_sr = bea2._bea_v0_2_diversity_risk_policy(
        candidates, query, 5
    )
    # Run v0.
    v0_acc, v0_at, v0_bs = bea0._bea_v0_budgeted_policy(candidates, 5)

    deduped_count = len(bea1._dedup_candidates(candidates))
    same_budget_k = bea2._same_budget_k(len(v03_acc), deduped_count)
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(
        {"bm25": [c for c in candidates if c["method"] == "bm25"]}, same_budget_k)
    ao_ev = bea2._agreement_only_same_budget_arm(candidates, same_budget_k)
    sr_ev = bea2._seeded_random_same_budget_arm(candidates, same_budget_k)

    v03_m = _arm_metrics_for_record(
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY, v03_acc, gold, "bea3-st", len(candidates),
        len(v03_acc), len(v03_ao), 0.05)
    v02_m = _arm_metrics_for_record(
        ARM_BEA_V0_2, v02_acc, gold, "bea3-st", len(candidates),
        len(v02_acc), len(v02_ao), 0.04)
    v0_m = _arm_metrics_for_record(
        ARM_BEA_V0, v0_acc, gold, "bea3-st", len(candidates),
        len(v0_acc), len(v0_at), 0.03)

    arm_aggs = {
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY: _arm_means([v03_m]),
        ARM_BEA_V0_3_NO_ANCHOR: _arm_means([v03_m]),
        ARM_BEA_V0_3_NO_EARLY_STOP: _arm_means([v03_m]),
        ARM_BEA_V0_2: _arm_means([v02_m]),
        ARM_BEA_V0: _arm_means([v0_m]),
        ARM_BM25_PREFIX: _arm_means([v03_m]),
        ARM_AGREEMENT_ONLY: _arm_means([v03_m]),
        ARM_SEEDED_RANDOM: _arm_means([v03_m]),
    }
    per_record_arm_metrics = [{
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY: v03_m,
        ARM_BEA_V0_3_NO_ANCHOR: v03_m,
        ARM_BEA_V0_3_NO_EARLY_STOP: v03_m,
        ARM_BEA_V0_2: v02_m,
        ARM_BEA_V0: v0_m,
        ARM_BM25_PREFIX: v03_m,
        ARM_AGREEMENT_ONLY: v03_m,
        ARM_SEEDED_RANDOM: v03_m,
    }]
    per_benchmark_arm_aggs = {
        "contextbench": {
            arm_id: {**_arm_means([m]), "__record_count__": 1}
            for arm_id, m in [
                (ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY, v03_m),
                (ARM_BEA_V0_2, v02_m), (ARM_BEA_V0, v0_m),
                (ARM_BM25_PREFIX, v03_m), (ARM_AGREEMENT_ONLY, v03_m),
                (ARM_SEEDED_RANDOM, v03_m),
            ]
        }
    }
    per_record_mechanism_summaries = [{
        "anchor_used": True, "early_stop_used": False,
        "budget_used": len(v03_acc), "latency_ms": 50,
        "mean_span_extent": v03_ms.get("mean_span_extent", 0.0),
        "span_proxy_bucket_counts": v03_ms.get("span_proxy_bucket_counts", {}),
    }]
    manifest_hash = _private_score_manifest_hash()
    skeleton = _build_pass_report(
        self_test_passed=True,
        contextbench_row_offset_requested=60,
        contextbench_row_limit_requested=20,
        repoqa_needle_offset_requested=30,
        repoqa_needle_limit_requested=10,
        budget=5, methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default", network_mode="local_explicit",
        records_evaluated=30, records_successful=30, records_failed=0,
        network_calls=2, arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_benchmark_arm_aggs=per_benchmark_arm_aggs,
        per_record_mechanism_summaries=per_record_mechanism_summaries,
        private_score_records_written=True,
        private_score_record_count=270,  # 30 × 9 arms
        private_score_storage_class="tmp_private",
        private_score_manifest_hash=manifest_hash,
        aggregate_runtime_seconds=42.0,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        enable_rrf_baseline=False, paired_exclusion_count=0, partial=False,
    )

    # Group 1: Identity.
    for name, expected in [
        ("schema_version", SCHEMA_VERSION), ("claim_level", CLAIM_LEVEL),
        ("mode", MODE), ("phase", PHASE), ("generated_by", GENERATED_BY),
        ("treatment_arm", ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY),
        ("baseline_arm", BASELINE_ARM),
    ]:
        checks.append(_check(f"identity_{name}", skeleton.get(name) == expected))
    checks.append(_check("status_pass", skeleton["status"] == "bea3_anchor_span_latency_pass"))
    checks.append(_check("seeded_random_seed", skeleton["seeded_random_seed"] == SEEDED_RANDOM_SEED))

    # Group 2: Safe true flags.
    for flag in SAFE_TRUE_FLAGS:
        checks.append(_check(f"safe_true_{flag}_present", flag in skeleton))

    # Group 3: No-claim false flags.
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(_check(f"no_claim_{flag}_false", skeleton.get(flag) is False))

    # Group 4: License fields.
    checks.append(_check("license_status", skeleton.get("dataset_license_status") == "unknown_dataset_license"))
    checks.append(_check("license_row_redist_false", skeleton.get("row_level_redistribution_allowed") is False))

    # Group 5: Private SCORE manifest.
    manifest = skeleton.get("private_score_manifest", {})
    checks.append(_check("manifest_present", isinstance(manifest, dict) and len(manifest) > 0))
    checks.append(_check("manifest_records_written_true", manifest.get("records_written") is True))
    checks.append(_check("manifest_record_count", manifest.get("record_count") == 270))
    checks.append(_check("manifest_schema_version", manifest.get("schema_version") == PRIVATE_SCORE_SCHEMA_VERSION))
    checks.append(_check("manifest_path_not_serialized", manifest.get("path_publicly_serialized") is False))
    checks.append(_check("manifest_hash_sha256",
        isinstance(manifest.get("manifest_hash"), str)
        and len(manifest["manifest_hash"]) == 64))
    for fk in ("private_score_path", "action_order", "priority_components",
               "selected_decisions", "budget_trace", "stop_reason",
               "candidate_features", "anchor_eligibility", "score_outcome"):
        checks.append(_check(f"forbidden_key_{fk}_absent", fk not in skeleton))

    # Group 6: Hard caps.
    checks.append(_check("cb_offset_default_60", CONTEXTBENCH_ROW_OFFSET_DEFAULT == 60))
    checks.append(_check("cb_limit_default_20", CONTEXTBENCH_ROW_LIMIT_DEFAULT == 20))
    checks.append(_check("cb_limit_cap_20", _validate_row_limit(100) == 20))
    checks.append(_check("rq_offset_default_30", REPOQA_NEEDLE_OFFSET_DEFAULT == 30))
    checks.append(_check("rq_limit_default_10", REPOQA_NEEDLE_LIMIT_DEFAULT == 10))
    checks.append(_check("rq_limit_cap_10", _validate_needle_limit(100) == 10))
    checks.append(_check("budget_default_5", BUDGET_DEFAULT == 5))
    checks.append(_check("budget_cap_20", _validate_budget(100) == 20))
    try:
        _validate_row_limit(0); checks.append(_check("row_limit_rejects_0", False))
    except SystemExit:
        checks.append(_check("row_limit_rejects_0", True))
    try:
        _validate_budget(0); checks.append(_check("budget_rejects_0", False))
    except SystemExit:
        checks.append(_check("budget_rejects_0", True))

    # Group 7: v0.3 policy mechanics.
    checks.append(_check("v03_accepts_nonempty", len(v03_acc) > 0))
    checks.append(_check("v03_respects_budget_5", len(v03_acc) <= 5))
    v03_b3, _, _, _, _ = _bea_v0_3_policy(candidates, query, 3)
    checks.append(_check("v03_respects_budget_3", len(v03_b3) <= 3))
    v03_b0, _, _, _, _ = _bea_v0_3_policy(candidates, query, 0)
    checks.append(_check("v03_budget_0_empty", len(v03_b0) == 0))
    checks.append(_check("v03_empty_candidates", len(_bea_v0_3_policy([], query, 5)[0]) == 0))
    checks.append(_check("v03_action_order_nonempty", len(v03_ao) > 0))
    checks.append(_check("v03_budget_trace_nonempty", len(v03_bt) > 0))
    checks.append(_check("v03_stop_reason_present", isinstance(v03_sr, str) and len(v03_sr) > 0))
    checks.append(_check("v03_mechanism_summary_present", isinstance(v03_ms, dict) and len(v03_ms) > 0))
    checks.append(_check("v03_anchor_used", v03_ms.get("anchor_used") is True))
    checks.append(_check("v03_no_anchor_not_used", v03na_ms.get("anchor_used") is False))
    checks.append(_check("v03_no_early_stop_flag", v03ne_ms.get("early_stop_used") is False))
    checks.append(_check("v03_differs_from_v02",
        len(v03_ao) != len(v02_ao) or v03_acc != v02_acc
        or any("anchor_boost" in a.get("priority_components", {}) for a in v03_ao)))

    # Group 8: v0.3 priority components.
    if v03_ao:
        first = v03_ao[0]
        for comp in ("anchor_boost", "span_tightness", "span_bonus",
                     "anchor_file_support", "weak_support_penalty"):
            checks.append(_check(f"v03_priority_{comp}_present",
                comp in first.get("priority_components", {})))

    # Group 9: v0.3 runtime-clean invariance.
    tainted = []
    for c in candidates:
        tc = dict(c)
        tc["gold_paths"] = ["src/path1.py"]
        tc["row_id"] = "leaked"
        tc["benchmark_label"] = "positive"
        tainted.append(tc)
    v03_t, _, _, _, _ = _bea_v0_3_policy(tainted, query, 5)
    def _ak(a): return (a["path"], a["start_line"], a["end_line"])
    checks.append(_check("v03_runtime_clean_invariance",
        [_ak(a) for a in v03_acc] == [_ak(a) for a in v03_t]))

    # Group 10: span helpers.
    checks.append(_check("span_tightness_5_lines", _span_tightness({"start_line": 1, "end_line": 5}) == 1.0))
    checks.append(_check("span_tightness_15_lines", _span_tightness({"start_line": 1, "end_line": 15}) == 0.5))
    checks.append(_check("span_tightness_30_lines", _span_tightness({"start_line": 1, "end_line": 30}) == 0.25))
    checks.append(_check("span_tightness_100_lines", _span_tightness({"start_line": 1, "end_line": 100}) == 0.0))
    checks.append(_check("span_proxy_bucket_tight", _span_proxy_bucket(5) == "tight"))
    checks.append(_check("span_proxy_bucket_wide", _span_proxy_bucket(30) == "wide"))
    checks.append(_check("anchor_eligible_bm25", _is_anchor_eligible({"methods": {"bm25"}}) is True))
    checks.append(_check("anchor_eligible_agreement2", _is_anchor_eligible({"methods": {"bm25", "symbol"}}) is True))
    checks.append(_check("anchor_not_eligible_regex_only", _is_anchor_eligible({"methods": {"regex"}}) is False))

    # Group 11: frozen weights.
    checks.append(_check("weight_anchor_frozen", V03_WEIGHT_ANCHOR == 0.35))
    checks.append(_check("weight_span_tight_frozen", V03_WEIGHT_SPAN_TIGHT == 0.15))
    checks.append(_check("weight_anchor_file_support_frozen", V03_WEIGHT_ANCHOR_FILE_SUPPORT == 0.10))
    checks.append(_check("weight_weak_support_penalty_frozen", V03_WEIGHT_WEAK_SUPPORT_PENALTY == -0.20))
    checks.append(_check("weight_early_stop_margin_frozen", V03_WEIGHT_EARLY_STOP_MARGIN == 0.05))
    checks.append(_check("anchor_count_default_frozen", ANCHOR_COUNT_DEFAULT == 2))

    # Group 12: quality_per_latency metric.
    checks.append(_check("quality_per_latency_in_metrics", "quality_per_latency" in v03_m))
    checks.append(_check("quality_per_latency_in_allowlist", "quality_per_latency" in ARM_METRIC_ALLOWLIST))

    # Group 13: benchmark_arm_metric_records shape.
    bamr = skeleton.get("benchmark_arm_metric_records", [])
    checks.append(_check("bamr_nonempty", isinstance(bamr, list) and len(bamr) > 0))
    if bamr:
        rec = bamr[0]
        checks.append(_check("bamr_shape", set(rec.keys()) == {"benchmark", "arm", "metric", "value", "record_count"}))

    # Group 14: delta_records shape.
    dr = skeleton.get("delta_records", [])
    checks.append(_check("delta_records_nonempty", isinstance(dr, list) and len(dr) > 0))
    if dr:
        rec = dr[0]
        checks.append(_check("delta_shape", set(rec.keys()) == {"baseline_arm", "treatment_arm", "metric", "delta"}))

    # Group 15: mechanism_contrast_records shape.
    mcr = skeleton.get("mechanism_contrast_records", [])
    checks.append(_check("mcr_nonempty", isinstance(mcr, list) and len(mcr) > 0))
    if mcr:
        rec = mcr[0]
        checks.append(_check("mcr_shape", set(rec.keys()) == {"contrast", "baseline_arm", "treatment_arm", "metric", "delta", "record_count"}))
        checks.append(_check("mcr_treatment_is_v03", rec.get("treatment_arm") == ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY))

    # Group 16: win_tie_loss_records shape.
    wtl = skeleton.get("win_tie_loss_records", [])
    checks.append(_check("wtl_nonempty", isinstance(wtl, list) and len(wtl) > 0))
    if wtl:
        rec = wtl[0]
        checks.append(_check("wtl_shape", set(rec.keys()) == {"baseline_arm", "treatment_arm", "metric", "win", "tie", "loss", "record_count"}))

    # Group 17: mechanism_summary_records shape.
    msr = skeleton.get("mechanism_summary_records", [])
    checks.append(_check("msr_nonempty", isinstance(msr, list) and len(msr) > 0))
    if msr:
        rec = msr[0]
        checks.append(_check("msr_shape", set(rec.keys()) == {"mechanism_field", "value", "record_count"}))
        fields = {r["mechanism_field"] for r in msr}
        checks.append(_check("msr_has_anchor_used_rate", "anchor_used_rate" in fields))
        checks.append(_check("msr_has_early_stop_rate", "early_stop_rate" in fields))
        checks.append(_check("msr_has_mean_budget_used", "mean_budget_used" in fields))
        checks.append(_check("msr_has_mean_span_extent", "mean_span_extent" in fields))

    # Group 18: Unavailable report.
    unavail = _build_unavailable_report(
        "contextbench_fetch_failed", self_test_passed=True,
        contextbench_row_offset_requested=60, contextbench_row_limit_requested=20,
        repoqa_needle_offset_requested=30, repoqa_needle_limit_requested=10,
        budget=5, methods=("bm25", "regex", "symbol"),
        openlocus_binary_source="default", network_mode="local_explicit",
    )
    checks.append(_check("unavail_status", unavail["status"] == "unavailable_with_reason"))
    checks.append(_check("unavail_no_v03", unavail["bea_v03_policy_executed"] is False))
    checks.append(_check("unavail_empty_records", unavail["benchmark_arm_metric_records"] == []))
    checks.append(_check("unavail_manifest_present",
        isinstance(unavail.get("private_score_manifest"), dict)
        and unavail["private_score_manifest"].get("path_publicly_serialized") is False))
    checks.append(_check("unavail_scan_pass", unavail["forbidden_scan"]["status"] == "pass"))

    # Group 19: Scanner rejects.
    for fk in BEA3_FORBIDDEN_EXTRA_KEYS:
        checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_bea3({fk: "value"}))))
    checks.append(_check("scanner_rejects_repo_url", bool(_scan_bea3({"leaked": "https://github.com/foo/bar"}))))
    checks.append(_check("scanner_rejects_tmp", bool(_scan_bea3({"leaked": "/tmp/foo"}))))

    # Group 20: Scanner allows.
    checks.append(_check("scanner_allows_schema", not _scan_bea3({"schema_version": SCHEMA_VERSION})))
    checks.append(_check("scanner_allows_bamr", not _scan_bea3({"benchmark_arm_metric_records": [
        {"benchmark": "contextbench", "arm": ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY,
         "metric": "mrr", "value": 0.5, "record_count": 10}]})))
    checks.append(_check("scanner_allows_msr", not _scan_bea3({"mechanism_summary_records": [
        {"mechanism_field": "anchor_used_rate", "value": 0.5, "record_count": 10}]})))
    checks.append(_check("scanner_allows_manifest", not _scan_bea3({"private_score_manifest": {
        "records_written": True, "record_count": 270,
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "manifest_hash": "a" * 64, "storage_class": "tmp_private",
        "path_publicly_serialized": False}})))

    # Group 21: Fail-closed.
    try:
        _enforce_bea3_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk, lv, label in [
        ("private_score_path", "/tmp/x", "private_score_path"),
        ("action_order", [{}], "action_order"),
        ("candidate_features", [{}], "candidate_features"),
        ("winner", "v03", "winner"),
        ("calibration", "x", "calibration"),
        ("method_winner", "v03", "method_winner"),
    ]:
        leaked = dict(skeleton)
        leaked[lk] = lv
        try:
            _enforce_bea3_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{label}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{label}", True))

    # Group 22: Public artifact self-scan clean.
    checks.append(_check("self_scan_clean", not _scan_bea3(skeleton)))
    checks.append(_check("unavail_scan_clean", not _scan_bea3(unavail)))

    # Group 23: CLI surface.
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for opt in ("--self-test", "--contextbench-row-offset", "--contextbench-row-limit",
                "--repoqa-needle-offset", "--repoqa-needle-limit", "--budget",
                "--methods", "--openlocus", "--out", "--private-score-dir",
                "--enable-rrf-baseline", "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in option_strings))

    # Group 24: Private SCORE writer.
    with tempfile.TemporaryDirectory(prefix="bea3_st_") as sd:
        sf = Path(sd) / "bea3.private.jsonl"
        _write_private_score_row(sf, {"test": 1})
        _write_private_score_row(sf, {"test": 2})
        lines = sf.read_text(encoding="utf-8").splitlines()
        checks.append(_check("score_writer_2_rows", len(lines) == 2))
        checks.append(_check("score_rows_parse", all(isinstance(json.loads(l), dict) for l in lines if l)))

    # Group 25: Fixed arms present.
    fixed_arms = skeleton.get("fixed_arms", [])
    for expected in (ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY, ARM_BEA_V0_3_NO_ANCHOR,
                     ARM_BEA_V0_3_NO_EARLY_STOP, ARM_BEA_V0_2, ARM_BEA_V0,
                     ARM_BM25_PREFIX, ARM_AGREEMENT_ONLY, ARM_SEEDED_RANDOM):
        checks.append(_check(f"fixed_arms_has_{expected}", expected in fixed_arms))

    # Group 26: No winner/calibration anywhere.
    for field in ("winner", "best_method", "recommended_default", "method_winner", "calibration"):
        checks.append(_check(f"missing_{field}", field not in skeleton))

    # Group 27: Aggregate runtime present.
    checks.append(_check("has_runtime", "aggregate_runtime_seconds" in skeleton))
    checks.append(_check("unavail_no_runtime", "aggregate_runtime_seconds" not in unavail))

    # Group 28: Method validation.
    checks.append(_check("methods_default", _validate_methods(DEFAULT_METHODS) == ("bm25", "regex", "symbol")))
    try:
        _validate_methods("regex,symbol")
        checks.append(_check("methods_requires_bm25", False))
    except SystemExit:
        checks.append(_check("methods_requires_bm25", True))

    # Group 29: Paired denominator win/tie/loss.
    rec_a = {ARM_BEA_V0: v0_m, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY: v03_m}
    rec_b = {ARM_BEA_V0: v0_m}  # missing v0.3
    wtl_partial = _win_tie_loss_records([rec_a, rec_b], ARM_BEA_V0, ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY)
    if wtl_partial:
        checks.append(_check("wtl_paired_excludes_missing", wtl_partial[0]["record_count"] == 1))
    else:
        checks.append(_check("wtl_paired_excludes_missing", False))

    # Group 30: v0.3 no_anchor differs from v0.3 (ablation is real).
    checks.append(_check("v03_no_anchor_mechanism_summary_differs",
        v03_ms.get("anchor_used") != v03na_ms.get("anchor_used")))
    checks.append(_check("v03_no_early_stop_mechanism_summary_differs",
        v03_ms.get("early_stop_used") != v03ne_ms.get("early_stop_used")
        if "early_stop_used" in v03ne_ms else True))

    all_passed = all(c["passed"] for c in checks if c is not None)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description="BEA-3 Anchor/Span/Latency-Aware Policy Smoke"
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--contextbench-row-offset", type=int, default=CONTEXTBENCH_ROW_OFFSET_DEFAULT)
    ap.add_argument("--contextbench-row-limit", type=int, default=CONTEXTBENCH_ROW_LIMIT_DEFAULT)
    ap.add_argument("--repoqa-needle-offset", type=int, default=REPOQA_NEEDLE_OFFSET_DEFAULT)
    ap.add_argument("--repoqa-needle-limit", type=int, default=REPOQA_NEEDLE_LIMIT_DEFAULT)
    ap.add_argument("--budget", type=int, default=BUDGET_DEFAULT)
    ap.add_argument("--methods", default=DEFAULT_METHODS)
    ap.add_argument("--enable-rrf-baseline", action="store_true")
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--private-score-dir", default=None)
    return ap


# ---------------------------------------------------------------------------
# Network smoke runner
# ---------------------------------------------------------------------------


def _run_network_smoke(
    *,
    contextbench_row_offset: int,
    contextbench_row_limit: int,
    repoqa_needle_offset: int,
    repoqa_needle_limit: int,
    budget: int,
    methods: tuple[str, ...],
    enable_rrf_baseline: bool,
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
    private_score_dir: Path,
    private_score_storage_class: str,
    phase_run_id: str,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    smoke_start = time.perf_counter()
    manifest_hash = _private_score_manifest_hash()
    score_file = private_score_dir / "bea3.private.jsonl"
    try:
        score_file.unlink()
    except OSError:
        pass

    per_record_arm_metrics: list[dict[str, dict[str, Any]]] = []
    per_benchmark_arm_aggs: dict[str, dict[str, dict[str, Any]]] = {}
    per_record_mechanism_summaries: list[dict[str, Any]] = []
    records_evaluated = 0
    records_successful = 0
    records_failed = 0
    paired_exclusion_count = 0

    # ContextBench heldout.
    cb_rows, cb_status, cb_nc, cb_fcc = _fetch_heldout_contextbench_rows(
        contextbench_row_offset, contextbench_row_limit
    )
    network_calls += cb_nc
    for k, v in cb_fcc.items():
        if k in fcc:
            fcc[k] += v
    if cb_status == "pass" and cb_rows:
        for idx, row in enumerate(cb_rows):
            records_evaluated += 1
            gold_paths, gold_lines, gc_status = c5a._parse_gold_context(
                row.get("gold_context")
            )
            if gc_status != "pass":
                fcc["contextbench_gold_parse_failed"] += 1
                records_failed += 1
                continue
            query = c5a._sanitize_query(
                row.get("problem_statement", ""), "first_paragraph"
            )
            if not query:
                fcc["contextbench_no_python_rows"] += 1
                records_failed += 1
                continue
            repo_url = row.get("repo_url", "")
            base_commit = row.get("base_commit", "")
            if not isinstance(repo_url, str) or not isinstance(
                base_commit, str
            ) or not repo_url or not base_commit:
                fcc["contextbench_no_python_rows"] += 1
                records_failed += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"bea3_cb_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(
                    repo_url, base_commit, rwd
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    records_failed += 1
                    continue
                repo_root = rwd / "repo"
                per_arm, fcc, mech_summary = _evaluate_record(
                    openlocus_bin=openlocus_bin,
                    benchmark="contextbench",
                    private_record_id=f"contextbench-{idx}",
                    task_id=f"cb_row_{idx}", query=query,
                    gold_paths=gold_paths, gold_lines=gold_lines,
                    repo_root=repo_root, methods=methods, budget=budget,
                    enable_rrf_baseline=enable_rrf_baseline,
                    score_path=score_file, phase_run_id=phase_run_id, fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_mechanism_summaries.append(mech_summary)
                cb_aggs = per_benchmark_arm_aggs.setdefault("contextbench", {})
                for arm_id, metrics in per_arm.items():
                    if arm_id not in cb_aggs:
                        cb_aggs[arm_id] = {"__record_count__": 0}
                    cb_aggs[arm_id]["__record_count__"] += 1
                    for m in ARM_METRIC_ALLOWLIST:
                        if m in metrics:
                            cb_aggs[arm_id].setdefault(m, [])
                            cb_aggs[arm_id][m].append(metrics[m])
                records_successful += 1

    # RepoQA heldout.
    rq_needles, rq_status, rq_nc, rq_fcc = _fetch_heldout_repoqa_needles(
        repoqa_needle_offset, repoqa_needle_limit
    )
    network_calls += rq_nc
    for k, v in rq_fcc.items():
        if k in fcc:
            fcc[k] += v
    if rq_status == "pass" and rq_needles:
        for idx, needle in enumerate(rq_needles):
            records_evaluated += 1
            query = c5d._sanitize_needle_description(
                needle.get("needle_description", "")
            )
            if not query:
                fcc["repoqa_needle_parse_failed"] += 1
                records_failed += 1
                continue
            repo_url = needle.get("repo_url", "")
            commit_sha = needle.get("commit_sha", "")
            needle_path = needle.get("needle_path", "")
            start_line = needle.get("needle_start_line", 0)
            end_line = needle.get("needle_end_line", 0)
            if (not isinstance(repo_url, str) or not repo_url
                or not isinstance(commit_sha, str) or not commit_sha
                or not isinstance(needle_path, str) or not needle_path):
                fcc["repoqa_needle_parse_failed"] += 1
                records_failed += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"bea3_rq_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(
                    repo_url, commit_sha, rwd
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    records_failed += 1
                    continue
                repo_root = rwd / "repo"
                per_arm, fcc, mech_summary = _evaluate_record(
                    openlocus_bin=openlocus_bin,
                    benchmark="repoqa",
                    private_record_id=f"repoqa-{idx}",
                    task_id=f"rq_needle_{idx}", query=query,
                    gold_paths=[needle_path],
                    gold_lines=[[start_line, end_line]],
                    repo_root=repo_root, methods=methods, budget=budget,
                    enable_rrf_baseline=enable_rrf_baseline,
                    score_path=score_file, phase_run_id=phase_run_id, fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_mechanism_summaries.append(mech_summary)
                rq_aggs = per_benchmark_arm_aggs.setdefault("repoqa", {})
                for arm_id, metrics in per_arm.items():
                    if arm_id not in rq_aggs:
                        rq_aggs[arm_id] = {"__record_count__": 0}
                    rq_aggs[arm_id]["__record_count__"] += 1
                    for m in ARM_METRIC_ALLOWLIST:
                        if m in metrics:
                            rq_aggs[arm_id].setdefault(m, [])
                            rq_aggs[arm_id][m].append(metrics[m])
                records_successful += 1

    if not per_record_arm_metrics:
        return _build_unavailable_report(
            "retrieval_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash=manifest_hash,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            network_calls=network_calls, failure_category_counts=fcc,
        )

    # Compute per-benchmark × arm means.
    for benchmark, arm_aggs in per_benchmark_arm_aggs.items():
        for arm_id, agg in arm_aggs.items():
            rc = agg.pop("__record_count__", 0)
            means: dict[str, Any] = {}
            for m in ARM_METRIC_ALLOWLIST:
                vals = agg.get(m, [])
                if vals:
                    means[m] = round(sum(float(v) for v in vals) / len(vals), 6)
                else:
                    means[m] = 0.0
            agg.clear()
            agg.update(means)
            agg["__record_count__"] = rc

    # Overall arm aggregates.
    arm_aggs: dict[str, dict[str, Any]] = {}
    fixed_arm_ids = [
        ARM_BEA_V0_3_ANCHOR_SPAN_LATENCY, ARM_BEA_V0_3_NO_ANCHOR,
        ARM_BEA_V0_3_NO_EARLY_STOP, ARM_BEA_V0_2, ARM_BEA_V0,
        ARM_BM25_PREFIX, ARM_AGREEMENT_ONLY, ARM_SEEDED_RANDOM,
    ]
    if enable_rrf_baseline:
        fixed_arm_ids.append(ARM_RRF_SAME_BUDGET)
    for arm_id in fixed_arm_ids:
        per_arm_list = [
            rec[arm_id] for rec in per_record_arm_metrics
            if arm_id in rec
        ]
        if per_arm_list:
            arm_aggs[arm_id] = _arm_means(per_arm_list)

    # Count private SCORE rows.
    private_score_count = 0
    try:
        if score_file.exists():
            with score_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        private_score_count += 1
    except OSError:
        private_score_count = 0

    private_score_written = private_score_count > 0
    num_arms = len(fixed_arm_ids)
    expected_count = records_successful * num_arms
    if records_successful > 0 and private_score_count != expected_count:
        fcc["private_score_write_failed"] = (
            fcc.get("private_score_write_failed", 0) + 1
        )
        return _build_unavailable_report(
            "private_score_write_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_records_written=private_score_written,
            private_score_record_count=private_score_count,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash=manifest_hash,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            network_calls=network_calls, failure_category_counts=fcc,
        )

    aggregate_runtime_seconds = time.perf_counter() - smoke_start
    partial = records_failed > 0 or records_successful < (
        contextbench_row_limit + repoqa_needle_limit
    )

    return _build_pass_report(
        self_test_passed=self_test_passed,
        contextbench_row_offset_requested=contextbench_row_offset,
        contextbench_row_limit_requested=contextbench_row_limit,
        repoqa_needle_offset_requested=repoqa_needle_offset,
        repoqa_needle_limit_requested=repoqa_needle_limit,
        budget=budget, methods=methods,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        records_evaluated=records_evaluated,
        records_successful=records_successful,
        records_failed=records_failed, network_calls=network_calls,
        arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_benchmark_arm_aggs=per_benchmark_arm_aggs,
        per_record_mechanism_summaries=per_record_mechanism_summaries,
        private_score_records_written=private_score_written,
        private_score_record_count=private_score_count,
        private_score_storage_class=private_score_storage_class,
        private_score_manifest_hash=manifest_hash,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        failure_category_counts=fcc,
        enable_rrf_baseline=enable_rrf_baseline,
        paired_exclusion_count=paired_exclusion_count,
        partial=partial,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            tag = "PASS" if c["passed"] else "FAIL"
            print(f"[{tag}] {c['check']}")
        passed_count = sum(1 for c in checks if c["passed"])
        print(f"self_test_passed={passed} ({passed_count}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    contextbench_row_offset = _validate_row_offset(args.contextbench_row_offset)
    contextbench_row_limit = _validate_row_limit(args.contextbench_row_limit)
    repoqa_needle_offset = _validate_needle_offset(args.repoqa_needle_offset)
    repoqa_needle_limit = _validate_needle_limit(args.repoqa_needle_limit)
    budget = _validate_budget(args.budget)
    methods = _validate_methods(args.methods)
    enable_rrf_baseline = bool(args.enable_rrf_baseline)
    enable_network = bool(args.enable_external_benchmark_network)
    out_path = args.out if args.out is not None else DEFAULT_OUT

    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        sys.exit(1)

    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(args.openlocus)
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "retrieval_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_bea3_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    private_score_dir, private_score_storage_class = (
        _resolve_private_score_dir(args.private_score_dir)
    )
    phase_run_id = f"bea3-{int(time.time())}"

    if not enable_network:
        report = _build_unavailable_report(
            "contextbench_fetch_failed", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="disabled_opt_in",
        )
        _enforce_bea3_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real BEA-3 smoke.")
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_network_smoke(
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            budget=budget, methods=methods,
            enable_rrf_baseline=enable_rrf_baseline,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode, eval_dir=eval_dir,
            self_test_passed=self_test_passed,
            private_score_dir=private_score_dir,
            private_score_storage_class=private_score_storage_class,
            phase_run_id=phase_run_id,
        )
    except Exception:
        report = _build_unavailable_report(
            "unexpected_exception", self_test_passed=self_test_passed,
            contextbench_row_offset_requested=contextbench_row_offset,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_offset_requested=repoqa_needle_offset,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            budget=budget, methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
        )

    if report.get("provider_calls") != 0:
        report["status"] = "fail_schema_contract"

    _enforce_bea3_no_forbidden(report)
    _write_json(out_path, report)
    manifest = report.get("private_score_manifest", {})
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"records_successful={report.get('records_successful', 0)}, "
          f"private_score_record_count={manifest.get('record_count', 0)})")


if __name__ == "__main__":
    main()
