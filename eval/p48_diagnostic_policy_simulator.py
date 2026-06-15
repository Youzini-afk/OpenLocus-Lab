#!/usr/bin/env python3
"""P48 Diagnostic Policy Simulator / Request-More-Context Overlay.

P48 is a deterministic, SCORE-phase-only simulator.  It overlays the
`request_more_context` span-geometry gate from P47 on top of the P25
`bucket_routed_v0` and P30 `admission_v3_h4b` route policies and measures how
many risky primary actions would be replaced by a context request.

Hard constraints:
* No remote calls; `remote_calls_by_p48=0`.
* No source reads; `source_reads_attempted_by_p48=false`.
* No EvidenceCore semantics change; request-more-context is not evidence.
* No default promotion; `promotion_ready=false`, `default_should_change=false`.
* Public outputs are aggregate-only: no task IDs, candidate IDs, paths, spans,
  gold spans, private labels, route features, snippets, prompts, responses, or
  provider URLs/keys.
* Missing/unavailable/fallback data is marked explicitly; never zero-filled.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p25_bucket_policy as p25
import p46_candidate_reach_cost_map as p46
import p47_request_more_context as p47

try:
    import p30_admission_model_v3 as p30
except Exception:  # pragma: no cover
    p30 = None  # type: ignore[assignment]

SCHEMA_VERSION = "p48-diagnostic-policy-simulator-v1"
GENERATED_BY = "eval/p48_diagnostic_policy_simulator.py"

DEFAULT_OUT = Path("artifacts/p48_diagnostic_policy_simulator/p48_diagnostic_policy_simulator_report.json")
DEFAULT_DOC = Path("docs/en/p48-diagnostic-policy-simulator.md")

# Risky candidate-derived primary/actions that the overlay may replace.
P25_RMC_ELIGIBLE_ACTIONS = {
    "candidate_baseline",
    "llm_span_narrow",
    "admit_symbol_regex_union",
    "admit_rrf_primary",
    "admit_llm_span_narrow",
}

H4B_RMC_ELIGIBLE_ACTIONS = {
    "admit_symbol_regex_union",
    "admit_rrf_primary",
}

# Map an emitted action to the candidate pool used for the request-more-context gate.
ACTION_TO_POOL_STRATEGY = {
    "candidate_baseline": "candidate_baseline",
    "llm_span_narrow": "llm_span_narrow",
    "admit_symbol_regex_union": "symbol_regex_union",
    "admit_rrf_primary": "rrf_primary",
    "admit_llm_span_narrow": "llm_span_narrow",
}

# Outcome-key resolution for non-P25 actions (P30-H4B emits admit_* and apply_llm_filter).
H4B_ACTION_OUTCOME_MAP: dict[str, str] = {
    "abstain": "llm_abstain_filter",
    "admit_symbol_regex_union": "symbol_regex_union",
    "admit_rrf_primary": "rrf_primary",
    "admit_llm_span_narrow": "llm_span_narrow",
    "apply_llm_filter": "llm_filter",
    "supporting_only": "supporting_only",
    "weak_candidate_only": "weak_candidate_only",
}
if p30 is not None:
    H4B_ACTION_OUTCOME_MAP = p30.ACTION_OUTCOME_MAP

P25_ACTION_KEYS = {"candidate_baseline", "llm_span_narrow", "llm_filter", "llm_abstain_filter"}

# Primary actions for aggregate accounting (candidate-derived primary evidence).
PRIMARY_ACTIONS = {
    "candidate_baseline",
    "llm_span_narrow",
    "admit_symbol_regex_union",
    "admit_rrf_primary",
    "admit_llm_span_narrow",
}

FORBIDDEN_PUBLIC_KEYS = set(p46.FORBIDDEN_PUBLIC_KEYS) | {
    "task_id",
    "repo_id",
    "candidate_id",
    "path",
    "start_line",
    "end_line",
    "content_sha",
    "gold",
    "gold_spans",
    "label",
    "labels",
    "query",
    "prompt",
    "snippet",
    "response",
    "route_features",
    "source_text",
    "provider_key",
    "base_url",
    "api_key",
    "raw_candidates",
    "per_task",
}

P48_SAFETY_FLAG_KEYS = set(p46.SAFETY_FLAG_KEYS) | {
    "aggregate_only_public_artifact",
    "candidate_not_fact",
    "conversion_admission_simulated",
    "default_should_change",
    "evidencecore_semantics_changed",
    "lane_availability",
    "overlay_lanes",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "p46_materialization_availability",
    "p48_carry_forward",
    "p48_default_ready",
    "p48_promotion_ready",
    "p50_gate_source",
    "p50_quality_gate_status",
    "promotion_ready",
    "reference_lanes",
    "remote_calls_by_p48",
    "request_more_context_geometry",
    "request_more_context_not_evidence",
    "route_simulation",
    "source_reads_attempted_by_p48",
    "span_geometry_only_context",
    "score_phase_only_metrics",
    # lane names
    "reference_bucket_routed_v0",
    "reference_admission_v3_h4b",
    "p48_p25_rmc_overlay_v0",
    "p48_h4b_rmc_overlay_v0",
    "p48_conversion_admission_unavailable",
    # metric keys
    "action_counts",
    "action_span_cost",
    "availability",
    "candidate_count",
    "considered_candidate_count",
    "cost_fallback_rate",
    "demoted_primary_count",
    "demoted_primary_rate",
    "gap_type_distribution",
    "geometry_gold_capture_count",
    "geometry_only",
    "gold_gain_geometry_only",
    "measured_primary_cost",
    "missing_action_outcome_count",
    "not_evidence",
    "outcome_fallback_rate",
    "primary_action_count",
    "primary_action_rate",
    "quality_comparable",
    "raw_line_budget",
    "expanded_line_budget",
    "rejected_candidate_count",
    "request_more_context_count",
    "request_more_context_rate",
    "selected_count",
    "source_reads_attempted",
    "accept_count",
    "reject_count",
    "accept_rate",
    "mean_lines",
    "p95_lines",
    "overfetch_ratio",
    "no_gold_expanded_count",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _percentile(values: Sequence[int | float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n == 1:
        return float(s[0])
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return float(s[f] * (c - k) + s[c] * (k - f))


def _span_width(span: dict[str, Any]) -> int:
    start = int(span.get("start_line") or 0)
    end = int(span.get("end_line") or 0)
    if start <= 0 or end <= 0 or end < start:
        return 0
    return end - start + 1


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    """Recursively reject keys that must not appear in public artifacts."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P48_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _lookup_outcome(task: dict[str, Any], action: str) -> dict[str, Any]:
    """Outcome metadata for an action; request_more_context is explicitly missing."""
    if action == "request_more_context":
        return {"outcome_present": False, "cost_available": False}

    if action in P25_ACTION_KEYS:
        key = action
    else:
        key = H4B_ACTION_OUTCOME_MAP.get(action, action)

    out = task.get("outcomes", {}).get(key, {})
    present = bool(out.get("outcome_present"))
    cost = bool(out.get("cost_available"))
    return {
        "outcome_present": present,
        "cost_available": cost,
        "added_gold_span": out.get("added_gold_span"),
        "added_false_span": out.get("added_false_span"),
    }


def _build_action_table(
    actions: list[str],
    tasks: list[dict[str, Any]],
    *,
    quality_comparable: bool,
) -> dict[str, Any]:
    """Aggregate action/outcome/cost table for a route lane.

    `actions` is parallel to `tasks` and contains the selected action per task.
    """
    selected_count = len(actions)
    by_action: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "task_count": 0,
            "positive_count": 0,
            "no_gold_count": 0,
            "outcome_present_count": 0,
            "outcome_missing_count": 0,
            "cost_present_count": 0,
            "cost_missing_count": 0,
            "added_gold_span": 0,
            "added_false_span": 0,
        }
    )

    missing_outcome_count = 0
    missing_cost_count = 0
    primary_action_count = 0
    request_more_context_count = 0

    for task, action in zip(tasks, actions):
        info = _lookup_outcome(task, action)
        b = by_action[action]
        b["task_count"] += 1
        if task.get("has_gold"):
            b["positive_count"] += 1
        else:
            b["no_gold_count"] += 1

        if info["outcome_present"]:
            b["outcome_present_count"] += 1
        else:
            b["outcome_missing_count"] += 1
            missing_outcome_count += 1

        if info["cost_available"]:
            b["cost_present_count"] += 1
            ag = info.get("added_gold_span")
            af = info.get("added_false_span")
            if ag is not None:
                b["added_gold_span"] += ag
            if af is not None:
                b["added_false_span"] += af
        else:
            b["cost_missing_count"] += 1
            missing_cost_count += 1

        if action in PRIMARY_ACTIONS:
            primary_action_count += 1
        if action == "request_more_context":
            request_more_context_count += 1

    action_counts = {action: b["task_count"] for action, b in by_action.items()}

    action_span_cost: dict[str, Any] = {}
    for action, b in by_action.items():
        if b["task_count"] == 0:
            continue
        if b["cost_missing_count"] == 0:
            availability = "available"
        elif b["cost_present_count"] == 0:
            availability = "missing_cost_fields"
        else:
            availability = "partial_missing_cost_fields"
        action_span_cost[action] = {
            "availability": availability,
            "task_count": b["task_count"],
            "positive_task_count": b["positive_count"],
            "no_gold_task_count": b["no_gold_count"],
            "outcome_present_count": b["outcome_present_count"],
            "outcome_missing_count": b["outcome_missing_count"],
            "cost_present_count": b["cost_present_count"],
            "cost_missing_count": b["cost_missing_count"],
            "added_gold_span": b["added_gold_span"] if b["cost_present_count"] > 0 else None,
            "added_false_span": b["added_false_span"] if b["cost_present_count"] > 0 else None,
        }

    # Measured primary cost: existing primary actions with measured cost only.
    measured_added_gold: int | None = None
    measured_added_false: int | None = None
    measured_primary_count = 0
    for action, b in by_action.items():
        if action == "request_more_context":
            continue
        if action not in PRIMARY_ACTIONS:
            continue
        if b["cost_present_count"] > 0:
            measured_primary_count += b["cost_present_count"]
            measured_added_gold = (measured_added_gold or 0) + b["added_gold_span"]
            measured_added_false = (measured_added_false or 0) + b["added_false_span"]

    if measured_primary_count > 0:
        mpc_availability = "available"
    elif any(action in PRIMARY_ACTIONS and action != "request_more_context" for action in by_action):
        mpc_availability = "partial_missing_cost"
    else:
        mpc_availability = "missing_primary_actions"

    policy_availability: str
    if missing_cost_count == 0 and missing_outcome_count == 0:
        policy_availability = "available"
    elif missing_cost_count == selected_count or missing_outcome_count == selected_count:
        policy_availability = "missing_outcomes_or_cost"
    else:
        policy_availability = "partial_missing_cost_fields"

    return {
        "availability": policy_availability,
        "selected_count": selected_count,
        "action_counts": action_counts,
        "primary_action_count": primary_action_count,
        "primary_action_rate": _rate(primary_action_count, selected_count),
        "request_more_context_count": request_more_context_count,
        "request_more_context_rate": _rate(request_more_context_count, selected_count),
        "missing_action_outcome_count": missing_outcome_count,
        "outcome_fallback_rate": _rate(missing_outcome_count, selected_count),
        "missing_action_cost_count": missing_cost_count,
        "cost_fallback_rate": _rate(missing_cost_count, selected_count),
        "quality_comparable": quality_comparable and missing_outcome_count == 0 and missing_cost_count == 0,
        "action_span_cost": action_span_cost,
        "measured_primary_cost": {
            "availability": mpc_availability,
            "primary_action_count": measured_primary_count,
            "added_gold_span": measured_added_gold,
            "added_false_span": measured_added_false,
        },
    }


def _base_action_p25(task: dict[str, Any], calibrated_negative: str) -> str:
    return p25.route_bucket_routed_v0(task.get("route_context", {}), calibrated_negative)


def _base_action_h4b(task: dict[str, Any]) -> str:
    if p30 is None:
        return "unavailable"
    return p30.route_admission_v3_h4b(task.get("route_context", {}))["action"]


def _maybe_replace_with_rmc(
    task: dict[str, Any],
    base_action: str,
    eligible_actions: set[str],
    k: int = 5,
) -> str:
    """Return `request_more_context` if the base action is eligible and the P47 gate accepts the top candidate."""
    if base_action not in eligible_actions:
        return base_action
    strategy = ACTION_TO_POOL_STRATEGY.get(base_action)
    if not strategy:
        return base_action
    pool = task.get("pools", {}).get(strategy, [])
    if not pool:
        return base_action
    # Use rank-1 candidate from the same pool the base action would draw from.
    accept, _reason = p47._request_more_context_gate_v0(pool[0], 1, task)
    if accept:
        return "request_more_context"
    return base_action


def compute_route_simulation(tasks: list[dict[str, Any]], k: int = 5) -> dict[str, Any]:
    """Replay reference routes and build request-more-context overlay lanes."""
    if not tasks:
        return {
            "reference_bucket_routed_v0": {"availability": "missing tasks"},
            "reference_admission_v3_h4b": {"availability": "missing tasks"},
            "p48_p25_rmc_overlay_v0": {"availability": "missing tasks"},
            "p48_h4b_rmc_overlay_v0": {"availability": "missing tasks"},
            "p48_conversion_admission_unavailable": {
                "availability": "unavailable_source_read_unavailable",
                "conversion_admission_simulated": False,
            },
        }

    calibrated_negative = p25.choose_negative_strategy(tasks)

    base_p25: list[str] = []
    base_h4b: list[str] = []
    overlay_p25: list[str] = []
    overlay_h4b: list[str] = []

    for t in tasks:
        b25 = _base_action_p25(t, calibrated_negative)
        bh4b = _base_action_h4b(t)
        base_p25.append(b25)
        base_h4b.append(bh4b)
        overlay_p25.append(_maybe_replace_with_rmc(t, b25, P25_RMC_ELIGIBLE_ACTIONS, k))
        overlay_h4b.append(_maybe_replace_with_rmc(t, bh4b, H4B_RMC_ELIGIBLE_ACTIONS, k))

    def demoted_primary_count(base: list[str], overlay: list[str]) -> int:
        return sum(
            1
            for b, o in zip(base, overlay)
            if o == "request_more_context" and b in PRIMARY_ACTIONS
        )

    sim: dict[str, Any] = {
        "reference_bucket_routed_v0": _build_action_table(
            base_p25, tasks, quality_comparable=True
        ),
        "reference_admission_v3_h4b": _build_action_table(
            base_h4b, tasks, quality_comparable=True
        ),
        "p48_p25_rmc_overlay_v0": _build_action_table(
            overlay_p25, tasks, quality_comparable=False
        ),
        "p48_h4b_rmc_overlay_v0": _build_action_table(
            overlay_h4b, tasks, quality_comparable=False
        ),
        "p48_conversion_admission_unavailable": {
            "availability": "unavailable_source_read_unavailable",
            "conversion_admission_simulated": False,
            "reason": "P46 materialization remains source_read_unavailable; P48 conversion/admission lane is explicitly unavailable.",
        },
        "calibrated_negative_strategy": calibrated_negative,
    }
    sim["p48_p25_rmc_overlay_v0"]["demoted_primary_count"] = demoted_primary_count(
        base_p25, overlay_p25
    )
    sim["p48_p25_rmc_overlay_v0"]["demoted_primary_rate"] = _rate(
        sim["p48_p25_rmc_overlay_v0"]["demoted_primary_count"], len(base_p25)
    )
    sim["p48_h4b_rmc_overlay_v0"]["demoted_primary_count"] = demoted_primary_count(
        base_h4b, overlay_h4b
    )
    sim["p48_h4b_rmc_overlay_v0"]["demoted_primary_rate"] = _rate(
        sim["p48_h4b_rmc_overlay_v0"]["demoted_primary_count"], len(base_h4b)
    )
    return sim


def _compute_rmc_geometry_for_lane(
    tasks: list[dict[str, Any]],
    base_actions: list[str],
    *,
    small_window: int,
    medium_window: int,
    k: int = 5,
) -> dict[str, Any]:
    """Span-geometry diagnostics for candidates accepted by the P47 gate."""
    considered = 0
    accept_count = 0
    reject_count = 0
    raw_budget = 0
    expanded_budget = 0
    widths: list[int] = []
    gold_capture = 0
    no_gold_expanded = 0
    gold_gain = 0
    gap_counts: dict[str, int] = defaultdict(int)

    for task, base_action in zip(tasks, base_actions):
        strategy = ACTION_TO_POOL_STRATEGY.get(base_action)
        if not strategy:
            continue
        pool = task.get("pools", {}).get(strategy, [])[:k]
        for rank, ev in enumerate(pool, start=1):
            considered += 1
            accept, _ = p47._request_more_context_gate_v0(ev, rank, task)
            raw = p47._raw_span(ev)
            raw_w = _span_width(raw)
            if accept:
                accept_count += 1
                expanded = p47._expand_span(ev, small_window)
                exp_w = _span_width(expanded)
                raw_budget += raw_w
                expanded_budget += exp_w
                widths.append(exp_w)
                if not task.get("has_gold"):
                    no_gold_expanded += 1
                else:
                    reached_raw = p46._is_span_reached([raw], task["label"])
                    reached_exp = p46._is_span_reached([expanded], task["label"])
                    if reached_exp:
                        gold_capture += 1
                    if not reached_raw and reached_exp:
                        gold_gain += 1
                gap_counts[p47._gap_type(raw, task, small_window, medium_window)] += 1
            else:
                reject_count += 1

    overfetch: float | None = None
    if raw_budget > 0:
        overfetch = round((expanded_budget - raw_budget) / raw_budget, 6)

    gap_dist: dict[str, dict[str, Any]] = {}
    for gt in p47.GAP_TYPES:
        cnt = gap_counts.get(gt, 0)
        gap_dist[gt] = {"count": cnt, "rate": _rate(cnt, accept_count)}

    return {
        "geometry_only": True,
        "not_evidence": True,
        "source_reads_attempted": False,
        "considered_candidate_count": considered,
        "accept_count": accept_count,
        "reject_count": reject_count,
        "accept_rate": _rate(accept_count, considered),
        "raw_line_budget": raw_budget,
        "expanded_line_budget": expanded_budget,
        "mean_lines": _avg([float(w) for w in widths]) if widths else None,
        "p95_lines": _percentile(widths, 0.95),
        "overfetch_ratio": overfetch,
        "geometry_gold_capture_count": gold_capture,
        "no_gold_expanded_count": no_gold_expanded,
        "gold_gain_geometry_only": gold_gain,
        "gap_type_distribution": gap_dist,
    }


def compute_request_more_context_geometry(
    tasks: list[dict[str, Any]],
    route_simulation: dict[str, Any],
    *,
    small_window: int,
    medium_window: int,
    k: int = 5,
) -> dict[str, Any]:
    """Geometry-only metrics for accepted candidates in each overlay lane."""
    geometry: dict[str, Any] = {}
    lane_actions = {
        "p48_p25_rmc_overlay_v0": "reference_bucket_routed_v0",
        "p48_h4b_rmc_overlay_v0": "reference_admission_v3_h4b",
    }

    calibrated_negative = route_simulation.get("calibrated_negative_strategy", "llm_abstain_filter")

    for lane, ref_lane in lane_actions.items():
        block = route_simulation.get(ref_lane, {})
        if block.get("availability") in {"missing tasks", "route_error"}:
            geometry[lane] = {"availability": "missing_reference_lane"}
            continue
        if lane == "p48_p25_rmc_overlay_v0":
            base_actions = [_base_action_p25(t, calibrated_negative) for t in tasks]
        else:
            base_actions = [_base_action_h4b(t) for t in tasks]
        geometry[lane] = _compute_rmc_geometry_for_lane(
            tasks,
            base_actions,
            small_window=small_window,
            medium_window=medium_window,
            k=k,
        )

    return geometry


def _read_p50_report(path: Path | None) -> dict[str, Any]:
    """Read a P50 report and extract only aggregate carry-forward metadata."""
    if path is None or not path.exists():
        return {"p50_gate_source": "not_provided", "p50_quality_gate_status": "not_provided"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"p50_gate_source": "invalid_json", "p50_quality_gate_status": "not_provided"}
    return {
        "p50_gate_source": "provided_report",
        "p50_quality_gate_status": data.get("quality_gate_status", "not_provided"),
    }


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate schema, safety flags, and public-key invariants."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p48") != 0:
        errors.append("remote_calls_by_p48 must be 0")
    if report.get("source_reads_attempted_by_p48") is not False:
        errors.append("source_reads_attempted_by_p48 must be false")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "request_more_context_not_evidence": True,
        "span_geometry_only_context": True,
        "p48_default_ready": False,
        "p48_promotion_ready": False,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    for forbidden in ("tasks", "records", "per_task_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    return errors


def build_report(
    tasks: list[dict[str, Any]],
    input_paths: list[Path],
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    insufficient_paths: list[str] | None,
    p50_report_path: Path | None,
    *,
    small_window: int,
    medium_window: int,
    medium_max_width: int,
) -> dict[str, Any]:
    candidate_pool_availability = (
        "available" if tasks and all(t.get("has_candidate_pool") for t in tasks)
        else "partial" if tasks and any(t.get("has_candidate_pool") for t in tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available" if tasks and all(t.get("has_gold_spans") for t in tasks if t["has_gold"])
        else "partial" if tasks and any(t.get("has_gold_spans") for t in tasks if t["has_gold"])
        else "missing_gold_spans"
    )
    reach_metrics_available = (
        candidate_pool_availability != "missing_candidate_pool"
        and gold_span_availability != "missing_gold_spans"
    )
    p31_h1_handoff_detected = bool(
        tasks and any(t.get("has_candidate_pool") and t.get("has_gold_spans") for t in tasks)
    )
    p31_h1_handoff_detected_count = sum(
        1 for t in tasks if t.get("has_candidate_pool") and t.get("has_gold_spans")
    )
    p33b_handoff_detected = bool(tasks and any(t.get("subtypes") for t in tasks))
    p33b_handoff_detected_count = sum(1 for t in tasks if t.get("subtypes"))

    route_simulation = compute_route_simulation(tasks)
    request_more_context_geometry = compute_request_more_context_geometry(
        tasks,
        route_simulation,
        small_window=small_window,
        medium_window=medium_window,
    )
    materialization = p46.compute_materialization_diagnostics(tasks)
    p50_meta = _read_p50_report(p50_report_path)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P48 Diagnostic Policy Simulator / Request-More-Context Overlay scaffold is ready; "
            "real per-task ephemeral P25 records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only scaffold simulated {len(tasks)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P48 route simulation scored {len(tasks)} real ephemeral P25 records."
            )
        p25_rmc = route_simulation["p48_p25_rmc_overlay_v0"]
        h4b_rmc = route_simulation["p48_h4b_rmc_overlay_v0"]
        conclusion_lines.append(
            "P48 is SCORE-phase-only. No source files were read and no EvidenceCore semantics were changed."
        )
        conclusion_lines.append(
            "`request_more_context` is a span-geometry diagnostic, not evidence, not admission, and not a default."
        )
        conclusion_lines.append(
            f"P25 overlay: request_more_context_count={p25_rmc.get('request_more_context_count')}, "
            f"demoted_primary_count={p25_rmc.get('demoted_primary_count')}, "
            f"quality_comparable={p25_rmc.get('quality_comparable')}."
        )
        conclusion_lines.append(
            f"H4B overlay: request_more_context_count={h4b_rmc.get('request_more_context_count')}, "
            f"demoted_primary_count={h4b_rmc.get('demoted_primary_count')}, "
            f"quality_comparable={h4b_rmc.get('quality_comparable')}."
        )
        conclusion_lines.append(
            f"P46 materialization availability: {materialization.get('materialization_availability')}. "
            "P48 conversion/admission lane is unavailable by design."
        )
        conclusion_lines.append("No policy is promotion-ready or default-ready.")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P48 Diagnostic Policy Simulator / Request-More-Context Overlay",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": len(input_paths),
        "insufficient_input_source_count": len(insufficient_paths or []),
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "remote_calls_by_p48": 0,
        "source_reads_attempted_by_p48": False,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "request_more_context_not_evidence": True,
        "span_geometry_only_context": True,
        "p48_default_ready": False,
        "p48_promotion_ready": False,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "elapsed_ms": elapsed_ms,
        "small_window": small_window,
        "medium_window": medium_window,
        "medium_max_width": medium_max_width,
        "task_count": len(tasks),
        "positive_task_count": sum(1 for t in tasks if t["has_gold"]),
        "no_gold_task_count": sum(1 for t in tasks if not t["has_gold"]),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": p31_h1_handoff_detected_count,
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": p33b_handoff_detected_count,
        "p46_materialization_availability": materialization.get("materialization_availability", "missing"),
        "p50_gate_source": p50_meta["p50_gate_source"],
        "p50_quality_gate_status": p50_meta["p50_quality_gate_status"],
        "route_simulation": route_simulation,
        "request_more_context_geometry": request_more_context_geometry,
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P48 public report validation failed: {errors}")
    return report


def _fmt_rate(x: Any) -> str:
    r = x.get("rate") if isinstance(x, dict) else None
    return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"


def _fmt_int(x: Any) -> str:
    return str(x) if isinstance(x, int) else "n/a"


def _fmt_scalar(x: Any) -> str:
    return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P48 Diagnostic Policy Simulator / Request-More-Context Overlay\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P48: {report['remote_calls_by_p48']}",
        f"- Source reads by P48: {report['source_reads_attempted_by_p48']}",
        f"- Request-more-context is not evidence: {report['request_more_context_not_evidence']}",
        f"- Span geometry only: {report['span_geometry_only_context']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- Reach metrics available: {report['reach_metrics_available']}",
        f"- P50 gate source: `{report['p50_gate_source']}`",
        f"- P50 quality gate status: `{report['p50_quality_gate_status']}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P48 overlays the P47 `request_more_context` span-geometry gate on the P25 `bucket_routed_v0` "
        "and P30-H4B `admission_v3_h4b` route policies. It simulates how many risky candidate-derived "
        "primary actions would be replaced by a geometry-only context request. NoEvidenceCore semantics "
        "change, no source reads occur, and no policy is promoted to default.",
        "",
        "## Methodology\n",
        "- Replay `reference_bucket_routed_v0` and `reference_admission_v3_h4b`.",
        "- Build `p48_p25_rmc_overlay_v0`: replace eligible P25 primary actions with `request_more_context` when the P47 gate accepts the top candidate.",
        "- Build `p48_h4b_rmc_overlay_v0`: replace eligible H4B primary admits with `request_more_context` when the P47 gate accepts.",
        "- Leave `p48_conversion_admission_unavailable` explicitly unavailable (P46 source-read materialization is not wired).",
        "- Report aggregate action counts, primary-action counts, request-more-context counts, demoted-primary counts, outcome/cost fallback rates, and measured primary cost only for existing actions.",
        "- Report span-geometry diagnostics (line budgets, overfetch, gap-type distribution, gold capture) only for accepted candidates after routing decisions.",
        "- No source files are read; no remote model calls are made; no per-task rows, paths, spans, gold spans, or private labels are emitted.",
        "",
        "## Route simulation summary\n",
        "| Lane | Availability | Selected | Primary | RMC count | Demoted primary | OutcomeFallback | CostFallback | QualityComparable |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])

    lane_order = [
        "reference_bucket_routed_v0",
        "reference_admission_v3_h4b",
        "p48_p25_rmc_overlay_v0",
        "p48_h4b_rmc_overlay_v0",
    ]
    for lane in lane_order:
        block = report["route_simulation"].get(lane, {})
        lines.append(
            f"| {lane} | {block.get('availability')} | {block.get('selected_count', 0)} | "
            f"{block.get('primary_action_count', 0)} | {block.get('request_more_context_count', 0)} | "
            f"{block.get('demoted_primary_count', 'n/a')} | {_fmt_rate(block.get('outcome_fallback_rate'))} | "
            f"{_fmt_rate(block.get('cost_fallback_rate'))} | {block.get('quality_comparable', False)} |"
        )

    # Conversion lane.
    conv = report["route_simulation"].get("p48_conversion_admission_unavailable", {})
    lines.append(
        f"| p48_conversion_admission_unavailable | {conv.get('availability')} | - | - | - | - | - | - | {conv.get('conversion_admission_simulated', False)} |"
    )
    lines.append("")

    lines.append("## Action distribution per lane\n")
    for lane in lane_order:
        block = report["route_simulation"].get(lane, {})
        counts = block.get("action_counts", {})
        if counts:
            items = ", ".join(f"{a}={c}" for a, c in sorted(counts.items()))
            lines.append(f"- **{lane}**: {items}")
        else:
            lines.append(f"- **{lane}**: n/a")
    lines.append("")

    lines.append("## Measured primary cost (existing primary actions only)\n")
    lines.append("| Lane | Availability | Primary actions with cost | added_gold | added_false |")
    lines.append("|---|---:|---:|---:|---:|")
    for lane in lane_order:
        block = report["route_simulation"].get(lane, {})
        mpc = block.get("measured_primary_cost", {})
        lines.append(
            f"| {lane} | {mpc.get('availability')} | {mpc.get('primary_action_count', 0)} | "
            f"{_fmt_int(mpc.get('added_gold_span'))} | {_fmt_int(mpc.get('added_false_span'))} |"
        )
    lines.append("")

    lines.append("## Request-more-context geometry (accepted candidates only)\n")
    lines.append(
        "| Lane | Considered | Accepted | Rejected | AcceptRate | RawBudget | ExpandedBudget | MeanLines | P95Lines | Overfetch | GoldCapture | NoGoldExpanded | GoldGain |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for lane in ("p48_p25_rmc_overlay_v0", "p48_h4b_rmc_overlay_v0"):
        geo = report["request_more_context_geometry"].get(lane, {})
        lines.append(
            f"| {lane} | {geo.get('considered_candidate_count', 0)} | {geo.get('accept_count', 0)} | "
            f"{geo.get('reject_count', 0)} | {_fmt_rate({'rate': geo.get('accept_rate')})} | "
            f"{geo.get('raw_line_budget', 0)} | {geo.get('expanded_line_budget', 0)} | "
            f"{_fmt_scalar(geo.get('mean_lines'))} | {_fmt_scalar(geo.get('p95_lines'))} | "
            f"{_fmt_scalar(geo.get('overfetch_ratio'))} | {geo.get('geometry_gold_capture_count', 0)} | "
            f"{geo.get('no_gold_expanded_count', 0)} | {geo.get('gold_gain_geometry_only', 0)} |"
        )
    lines.append("")

    lines.append("## Gap type distribution (accepted candidates)\n")
    lines.append("| Lane | Adjacent/Overlap | SameFileNear | SameFileFar | CandidateAbsent |")
    lines.append("|---|---:|---:|---:|---:|")
    for lane in ("p48_p25_rmc_overlay_v0", "p48_h4b_rmc_overlay_v0"):
        geo = report["request_more_context_geometry"].get(lane, {})
        dist = geo.get("gap_type_distribution", {})
        lines.append(
            f"| {lane} | {_fmt_rate(dist.get('adjacent_or_overlap'))} | "
            f"{_fmt_rate(dist.get('same_file_near'))} | {_fmt_rate(dist.get('same_file_far'))} | "
            f"{_fmt_rate(dist.get('candidate_absent'))} |"
        )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.extend([
        "## Safety notes\n",
        "- No remote model calls were made during P48 simulation.",
        "- No source files were read and no AST/source trim was attempted.",
        "- This report contains only aggregate counts/rates by lane and action.",
        "- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, or provider keys are stored.",
        "- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, "
        "`candidate_not_fact=true`, `remote_calls_by_p48=0`, `source_reads_attempted_by_p48=false`, "
        "`request_more_context_not_evidence=true`, `span_geometry_only_context=true`.",
        "- `request_more_context` is not evidence and does not change defaults or Rust/EvidenceCore.",
        "",
    ])
    return "\n".join(lines)


def compute_p48_carry_forward(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Public aggregate summary for P50 carry-forward. No per-task data."""
    if not tasks:
        return {
            "availability": "not_implemented",
            "p48_schema_version": SCHEMA_VERSION,
        }

    route_simulation = compute_route_simulation(tasks)

    def summarize(lane: str) -> dict[str, Any]:
        block = route_simulation.get(lane, {})
        return {
            "availability": block.get("availability", "missing"),
            "selected_count": block.get("selected_count", 0),
            "action_counts": dict(block.get("action_counts", {})),
            "request_more_context_count": block.get("request_more_context_count", 0),
            "demoted_primary_count": block.get("demoted_primary_count", 0),
            "quality_comparable": block.get("quality_comparable", False),
        }

    return {
        "availability": "available",
        "p48_schema_version": SCHEMA_VERSION,
        "request_more_context_not_evidence": True,
        "span_geometry_only_context": True,
        "overlay_lane_summary": {
            "p48_p25_rmc_overlay_v0": summarize("p48_p25_rmc_overlay_v0"),
            "p48_h4b_rmc_overlay_v0": summarize("p48_h4b_rmc_overlay_v0"),
            "p48_conversion_admission_unavailable": {
                "availability": route_simulation.get("p48_conversion_admission_unavailable", {}).get("availability"),
                "conversion_admission_simulated": False,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P48 Diagnostic Policy Simulator / Request-More-Context Overlay")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 report for gate carry-forward.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    parser.add_argument("--small-window", type=int, default=3, help="Small neighbor window in lines.")
    parser.add_argument("--medium-window", type=int, default=10, help="Medium neighbor window in lines.")
    parser.add_argument("--medium-max-width", type=int, default=50, help="Maximum raw span width eligible for medium window.")
    args = parser.parse_args()

    if args.small_window < 0 or args.medium_window < 0 or args.medium_max_width < 0:
        parser.error("Window sizes and width cap must be non-negative.")

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_records = p46.make_self_test_records()
    elif args.input:
        input_paths = list(args.input)
        raw_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_paths: list[str] = []
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P48 route simulation.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P48 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_task_detail"
            reason = marker_reasons[marker]
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (p46.normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P48 normalization."

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        normalized_tasks,
        input_paths,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        insufficient_paths=insufficient_paths,
        p50_report_path=args.p50_report,
        small_window=args.small_window,
        medium_window=args.medium_window,
        medium_max_width=args.medium_max_width,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P48 report written to {args.out}")
    print(f"P48 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
