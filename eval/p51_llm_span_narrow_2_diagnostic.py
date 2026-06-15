#!/usr/bin/env python3
"""P51 LLM Span Narrow 2.0 / Candidate Filter Diagnostic Scaffold.

P51 first tranche is deterministic: no new LLM calls, no remote calls, no prompt
construction. It selects diagnostic candidates, publishes prompt-blueprint
metadata only, and replays/correlates existing P21 LLM role outcomes if present.

Hard constraints:
* No remote calls; `remote_calls_by_p51=0`.
* No LLM calls; `llm_calls_by_p51=0`.
* No prompt construction; `prompt_construction_by_p51=false`.
* No source reads; `source_reads_attempted_by_p51=false`.
* No EvidenceCore semantics change; no default promotion.
* Public outputs are aggregate-only: no task IDs, candidate IDs, paths, spans,
  gold spans, private labels, route features, snippets, prompts, responses, or
  provider URLs/keys.
* Gold/outcomes are used only inside explicitly-marked SCORE-phase diagnostics
  after candidate selection.
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
import p49_contrastive_candidate_pack_scaffold as p49
import p52_metadata_local_verifier_scaffold as p52

SCHEMA_VERSION = "p51-llm-span-narrow-2-diagnostic-v1"
GENERATED_BY = "eval/p51_llm_span_narrow_2_diagnostic.py"
STAGE = "P51 LLM Span Narrow 2.0 / Candidate Filter Diagnostic"

DEFAULT_OUT = Path("artifacts/p51_llm_span_narrow_2_diagnostic/p51_llm_span_narrow_2_diagnostic_report.json")
DEFAULT_DOC = Path("docs/en/p51-llm-span-narrow-2-diagnostic.md")

ACTION_NAMES = ["span_narrow", "filter", "abstain"]
ROLE_FOR_ACTION = {
    "span_narrow": "llm_span_narrow",
    "filter": "llm_filter",
    "abstain": "llm_abstain_filter",
}

LINE_BUDGET_PROXY_CAP = p49.LINE_BUDGET_PROXY_CAP

# Forbidden exact keys. Must never appear in public artifacts.
FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "repo_id",
    "candidate_id",
    "path",
    "candidate_path",
    "start_line",
    "end_line",
    "content_sha",
    "sha",
    "hash",
    "digest",
    "gold",
    "gold_spans",
    "label",
    "labels",
    "query",
    "raw_query",
    "query_terms",
    "identifier",
    "symbol_text",
    "prompt",
    "prompts",
    "response",
    "responses",
    "snippet",
    "source_text",
    "raw_text",
    "raw_source",
    "provider",
    "provider_key",
    "base_url",
    "api_key",
    "route_features",
    "records",
    "per_task",
    "per_candidate",
    "pack_items",
    "decision_records",
}

P51_SAFETY_FLAG_KEYS = {
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    "not_quality_evidence",
    "real_evaluation",
    "input_sources",
    "input_source_count",
    "insufficient_input_source_count",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "llm_output_not_evidence",
    "source_feature_not_evidence",
    "materialized_candidate_not_evidence",
    "remote_calls_by_p51",
    "llm_calls_by_p51",
    "prompt_construction_by_p51",
    "source_reads_attempted_by_p51",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_snippets_stored",
    "raw_snippets_sent_to_provider",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "raw_query_stored",
    "raw_text_stored",
    "raw_snippets_committed",
    "private_labels_committed",
    "aggregate_only_public_artifact",
    "score_phase_only_metrics",
    "p51_first_tranche_no_live_llm",
    "prompt_blueprint_not_prompt",
    "candidate_not_fact",
    "llm_output_not_evidence",
    "source_feature_not_evidence",
    "materialized_candidate_not_evidence",
    "elapsed_ms",
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "candidate_pool_availability",
    "gold_span_availability",
    "reach_metrics_available",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "input_sources",
    "p52b_report_source",
    "p52a_report_source",
    "p52_report_source",
    "p49_report_source",
    "p50_report_source",
    "p48_report_source",
    "p52b_quality_gate_status",
    "p52a_quality_gate_status",
    "p52_quality_gate_status",
    "p49_pack_not_evidence",
    "p50_quality_gate_status",
    "p48_overlay_availability",
    "metrics",
    "conclusion",
    "validation",
    # metric block keys public by design
    "candidate_selection",
    "prompt_blueprint",
    "existing_role_replay",
    "high_uncertainty_diagnostic",
    "score_phase_diagnostic_correlation",
    "p51_candidate_selection_v0",
    "p51_existing_role_replay_v0",
    "p51_prompt_blueprint_v0",
    "p51_live_opt_in_v0",
    "gold_free_deterministic",
    "source_reads_by_p51",
    "replayed_roles",
    "retrospective_correlation_only",
    "disabled_first_tranche",
    "candidate_denominator",
    "pack_denominator",
    "selected_for_span_narrow_count",
    "selected_for_span_narrow_rate",
    "selected_for_filter_count",
    "selected_for_filter_rate",
    "selected_for_abstain_review_count",
    "selected_for_abstain_review_rate",
    "selection_unavailable_count",
    "selection_unavailable_rate",
    "skip_reason_counts",
    "skip_reason_rates",
    "missing_candidate_pool",
    "no_contrast_pack",
    "metadata_high_risk",
    "source_feature_bucket_unavailable",
    "missing_existing_role_output",
    "prompt_blueprint_availability",
    "prompt_blueprint_count",
    "mean_candidates_per_blueprint",
    "p95_candidates_per_blueprint",
    "mean_source_lines_budget",
    "p95_source_lines_budget",
    "mean_context_chars_budget",
    "p95_context_chars_budget",
    "pack_strategy_mix",
    "source_feature_bucket_mix",
    "metadata_risk_bucket_mix",
    "path_kind_mix",
    "prompt_construction_by_p51",
    "raw_prompt_text_available",
    "existing_role_output_availability",
    "tasks_with_baseline_outcomes_count",
    "tasks_with_llm_filter_outcomes_count",
    "tasks_with_llm_span_narrow_outcomes_count",
    "tasks_with_llm_abstain_filter_outcomes_count",
    "role_output_coverage_rate",
    "llm_span_narrow_delta_span_f0_5_mean",
    "llm_span_narrow_delta_span_f0_5_p95",
    "llm_span_narrow_added_gold_delta_mean",
    "llm_span_narrow_added_false_delta_mean",
    "llm_filter_false_primary_delta_mean",
    "llm_abstain_filter_abstained_rate",
    "high_uncertainty_candidate_count",
    "high_uncertainty_candidate_rate",
    "high_uncertainty_tasks_with_existing_role_outputs_count",
    "high_uncertainty_tasks_with_existing_role_outputs_rate",
    "existing_role_helped_count",
    "existing_role_helped_rate",
    "existing_role_harmed_count",
    "existing_role_harmed_rate",
    "not_used_for_selection",
    "diagnostic_correlation_only",
    "gold_file_rate_selected",
    "gold_span_rate_selected",
    "file_right_span_wrong_rate_selected",
    "no_gold_selected_rate",
    "existing_role_added_gold_span_delta_mean",
    "existing_role_added_false_span_delta_mean",
    "existing_role_false_per_gold",
    "availability",
    "disabled_first_tranche",
    "not_used_for_pack_construction",
    "by_metadata_risk_bucket",
    "by_path_kind",
    "by_pack_strategy",
    "per_candidate_source_feature_mix_unavailable",
    "metadata_low_risk",
    "metadata_medium_risk",
    "metadata_high_risk",
    "metadata_unavailable",
    "source_feature_low_risk",
    "source_feature_medium_risk",
    "source_feature_high_risk",
    "source_feature_unavailable",
    "anchor_contrast_pack_v0",
    "topk_flat_pack_v0",
    "conservative_anchor_pack_v0",
    "count",
    "rate",
    "mean",
    "p95",
    "value",
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


def _as_float(value: Any) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value == int(value):
            return int(value)
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P51_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status/metadata."""
    source_key = f"{report_name}_report_source"
    status_key = f"{report_name}_quality_gate_status"
    not_provided: dict[str, Any] = {source_key: "not_provided", status_key: "not_provided"}
    if report_name == "p48":
        not_provided["p48_overlay_availability"] = "not_provided"
    if report_name == "p49":
        not_provided["p49_pack_not_evidence"] = "not_provided"
    if path is None or not path.exists():
        return not_provided
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        result = {source_key: "invalid_json", status_key: "not_provided"}
        if report_name == "p48":
            result["p48_overlay_availability"] = "not_provided"
        if report_name == "p49":
            result["p49_pack_not_evidence"] = "not_provided"
        return result

    result: dict[str, Any] = {source_key: "provided_report"}
    status = data.get("status") or data.get("quality_gate_status") or "not_provided"
    if not isinstance(status, str):
        status = "not_provided"
    result[status_key] = status
    if report_name == "p48":
        overlay = data.get("route_simulation", {}).get("p48_p25_rmc_overlay_v0", {}).get("availability")
        result["p48_overlay_availability"] = overlay if isinstance(overlay, str) else "not_provided"
    if report_name == "p49":
        pne = data.get("pack_not_evidence")
        result["p49_pack_not_evidence"] = bool(pne) if isinstance(pne, bool) else "not_provided"
    return result


def _has_rrf_backing(cand: dict[str, Any]) -> bool:
    subtype = cand.get("subtype") or {}
    if subtype.get("rrf_backing"):
        return True
    channels = cand.get("channels") or []
    if "rrf" in channels or "rrf_primary" in channels:
        return True
    strategies = cand.get("source_strategies") or set()
    if isinstance(strategies, set):
        return "rrf_primary" in strategies or "rrf" in strategies
    return False


def _candidate_metadata_risk(cand: dict[str, Any], task: dict[str, Any]) -> str:
    """Conservative metadata-only risk bucket. No source reads."""
    subtype = cand.get("subtype") or {}
    source_class = str(subtype.get("source_class") or "other")
    agreement_class = str(subtype.get("agreement_class") or "other")
    path_kind = str(cand.get("path_kind") or "unknown")
    tags = {str(t).lower() for t in (task.get("task_risk_tags") or [])}
    bucket = str(task.get("task_bucket") or "unknown").lower()

    if path_kind in {"generated_or_vendor", "unknown"}:
        return "metadata_high_risk"
    if source_class == "regex_only":
        return "metadata_high_risk"
    if agreement_class in {"single_source", "disagree"}:
        return "metadata_high_risk"
    if not _has_rrf_backing(cand) and source_class == "regex_only":
        return "metadata_high_risk"
    if any(t in tags for t in {"negative", "high_noise", "ambiguous"}):
        return "metadata_high_risk"
    if bucket in {"negative", "ambiguous", "hard_distractor", "dense_false_positive"}:
        return "metadata_high_risk"

    if path_kind in {"test", "config", "doc"}:
        return "metadata_medium_risk"
    if source_class == "symbol_regex_fusion":
        return "metadata_medium_risk"
    if agreement_class == "same_file_only":
        return "metadata_medium_risk"
    if bucket in {"config", "route_handler", "stale-like", "dense_quiver_trap"}:
        return "metadata_medium_risk"
    if not _has_rrf_backing(cand):
        return "metadata_medium_risk"

    if source_class == "symbol_only" and agreement_class == "span_overlap":
        return "metadata_low_risk"
    if path_kind == "source" and _has_rrf_backing(cand):
        return "metadata_low_risk"
    if source_class == "symbol_only":
        return "metadata_low_risk"
    return "metadata_medium_risk"


def _task_contrast_feasible(candidates: list[dict[str, Any]]) -> bool:
    # A contrast pack needs at least an anchor and one other candidate.
    return len(candidates) >= 2


def _task_action(task: dict[str, Any]) -> str:
    """Deterministic action assignment from public bucket/risk metadata only."""
    bucket = str(task.get("task_bucket") or "unknown").lower()
    tags = {str(t).lower() for t in (task.get("task_risk_tags") or [])}
    if bucket in {"negative", "hard_distractor", "dense_false_positive", "dense_quiver_trap", "stale-like"}:
        return "filter"
    if any(t in tags for t in {"negative", "high_noise", "ambiguous"}):
        return "filter"
    if bucket in {"ambiguous"}:
        return "abstain"
    return "span_narrow"


def _compute_candidate_selection(
    tasks: list[dict[str, Any]],
    report_sources: dict[str, Any],
) -> dict[str, Any]:
    rmc_ok = (
        report_sources.get("p47_report_source") == "provided_report"
        and report_sources.get("p48_report_source") == "provided_report"
        and report_sources.get("p48_overlay_availability") in {"available", "partial"}
    )

    candidate_denominator = 0
    skip_reason_counts: dict[str, int] = defaultdict(int)
    selected_counts: dict[str, int] = {"span_narrow": 0, "filter": 0, "abstain": 0}
    selected_tasks: set[str] = set()
    metadata_risk_counts: dict[str, int] = defaultdict(int)

    for task in tasks:
        candidates = p49._normalize_candidates(task)
        n = len(candidates)
        candidate_denominator += n
        if n == 0:
            skip_reason_counts["missing_candidate_pool"] += 1
            continue

        action = _task_action(task)
        contrast_ok = _task_contrast_feasible(candidates)

        for cand in candidates:
            risk = _candidate_metadata_risk(cand, task)
            metadata_risk_counts[risk] += 1
            if risk in {"metadata_high_risk", "metadata_unavailable"}:
                skip_reason_counts["metadata_high_risk"] += 1
                continue
            if not contrast_ok:
                skip_reason_counts["no_contrast_pack"] += 1
                continue
            selected_counts[action] += 1
            selected_tasks.add(str(task["task_id"]))

    selected_total = sum(selected_counts.values())
    selection_unavailable = candidate_denominator - selected_total - sum(skip_reason_counts.values())
    if selection_unavailable < 0:
        selection_unavailable = 0

    skip_reason_counts["selection_unavailable"] = selection_unavailable
    skip_reason_rates = {k: _rate(v, candidate_denominator) for k, v in skip_reason_counts.items()}

    return {
        "candidate_denominator": candidate_denominator,
        "pack_denominator": len(selected_tasks),
        "selected_for_span_narrow_count": selected_counts["span_narrow"],
        "selected_for_span_narrow_rate": _rate(selected_counts["span_narrow"], candidate_denominator),
        "selected_for_filter_count": selected_counts["filter"],
        "selected_for_filter_rate": _rate(selected_counts["filter"], candidate_denominator),
        "selected_for_abstain_review_count": selected_counts["abstain"],
        "selected_for_abstain_review_rate": _rate(selected_counts["abstain"], candidate_denominator),
        "selection_unavailable_count": selection_unavailable,
        "selection_unavailable_rate": _rate(selection_unavailable, candidate_denominator),
        "skip_reason_counts": dict(skip_reason_counts),
        "skip_reason_rates": skip_reason_rates,
        "metadata_risk_bucket_mix": {
            "metadata_low_risk_count": metadata_risk_counts.get("metadata_low_risk", 0),
            "metadata_medium_risk_count": metadata_risk_counts.get("metadata_medium_risk", 0),
            "metadata_high_risk_count": metadata_risk_counts.get("metadata_high_risk", 0),
            "metadata_unavailable_count": metadata_risk_counts.get("metadata_unavailable", 0),
        },
        "rmc_overlay_available": rmc_ok,
        "source_feature_per_candidate_unavailable": True,
    }


def _compute_prompt_blueprint(
    tasks: list[dict[str, Any]],
    selection: dict[str, Any],
) -> dict[str, Any]:
    selected_tasks = set()
    per_pack_candidates: list[int] = []
    per_pack_lines: list[int] = []
    per_pack_chars: list[int] = []
    pack_strategy_mix: dict[str, int] = defaultdict(int)
    path_kind_mix: dict[str, int] = defaultdict(int)
    metadata_risk_counts: dict[str, int] = defaultdict(int)

    for task in tasks:
        candidates = p49._normalize_candidates(task)
        if not candidates:
            continue
        # Only build blueprints for tasks that would pass the conservative selector.
        selected = [
            c for c in candidates
            if _candidate_metadata_risk(c, task) not in {"metadata_high_risk", "metadata_unavailable"}
            and _task_contrast_feasible(candidates)
        ]
        if not selected:
            continue
        selected_tasks.add(str(task["task_id"]))
        for strategy in p49.PACK_STRATEGIES:
            pack = p49._build_pack(selected, strategy)
            selected_list = pack.get("selected") or []
            if not selected_list:
                continue
            n = len(selected_list)
            per_pack_candidates.append(n)
            line_budget = pack.get("line_budget_proxy") or 0
            if line_budget == 0:
                line_budget = min(sum(
                    (c.get("span_width") or 1) for c in selected_list
                ), LINE_BUDGET_PROXY_CAP)
            per_pack_lines.append(line_budget)
            per_pack_chars.append(line_budget * 40)
            pack_strategy_mix[strategy] += 1
            for c in selected_list:
                path_kind_mix[str(c.get("path_kind") or "unknown")] += 1
                risk = _candidate_metadata_risk(c, task)
                metadata_risk_counts[risk] += 1

    count = len(per_pack_candidates)
    availability = "available" if count > 0 else "unavailable"
    return {
        "prompt_blueprint_availability": availability,
        "prompt_blueprint_count": count,
        "mean_candidates_per_blueprint": _avg([float(x) for x in per_pack_candidates]),
        "p95_candidates_per_blueprint": _percentile(per_pack_candidates, 0.95),
        "mean_source_lines_budget": _avg([float(x) for x in per_pack_lines]),
        "p95_source_lines_budget": _percentile(per_pack_lines, 0.95),
        "mean_context_chars_budget": _avg([float(x) for x in per_pack_chars]),
        "p95_context_chars_budget": _percentile(per_pack_chars, 0.95),
        "pack_strategy_mix": dict(pack_strategy_mix),
        "source_feature_bucket_mix": {
            "availability": "unavailable",
            "reason": "per_candidate_source_feature_mix_unavailable_first_tranche",
        },
        "metadata_risk_bucket_mix": {
            "metadata_low_risk_count": metadata_risk_counts.get("metadata_low_risk", 0),
            "metadata_medium_risk_count": metadata_risk_counts.get("metadata_medium_risk", 0),
            "metadata_high_risk_count": metadata_risk_counts.get("metadata_high_risk", 0),
            "metadata_unavailable_count": metadata_risk_counts.get("metadata_unavailable", 0),
        },
        "path_kind_mix": dict(path_kind_mix),
        "prompt_construction_by_p51": False,
        "raw_prompt_text_available": False,
        "per_candidate_source_feature_mix_unavailable": True,
    }


def _compute_existing_role_replay(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_count = 0
    span_count = 0
    filter_count = 0
    abstain_count = 0

    span_deltas: list[float] = []
    added_gold_deltas: list[float] = []
    added_false_deltas: list[float] = []
    filter_pfp_deltas: list[float] = []
    abstain_flags: list[bool] = []

    for task in tasks:
        outcomes = task.get("outcomes", {})
        base = outcomes.get("candidate_baseline", {})
        if base.get("outcome_present"):
            baseline_count += 1

        span = outcomes.get("llm_span_narrow", {})
        if span.get("outcome_present"):
            span_count += 1
            if base.get("outcome_present"):
                sf = _as_float(span.get("span_f0_5"))
                bsf = _as_float(base.get("span_f0_5"))
                if sf is not None and bsf is not None:
                    span_deltas.append(sf - bsf)
                ag = _as_int(span.get("added_gold_span"))
                bg = _as_int(base.get("added_gold_span"))
                if ag is not None and bg is not None:
                    added_gold_deltas.append(float(ag - bg))
                af = _as_int(span.get("added_false_span"))
                bf = _as_int(base.get("added_false_span"))
                if af is not None and bf is not None:
                    added_false_deltas.append(float(af - bf))

        filt = outcomes.get("llm_filter", {})
        if filt.get("outcome_present"):
            filter_count += 1
            if base.get("outcome_present"):
                rpfp = _as_float(filt.get("primary_false_positive_rate"))
                bpfp = _as_float(base.get("primary_false_positive_rate"))
                if rpfp is not None and bpfp is not None:
                    filter_pfp_deltas.append(rpfp - bpfp)

        abst = outcomes.get("llm_abstain_filter", {})
        if abst.get("outcome_present"):
            abstain_count += 1
            abstain_flags.append(bool(abst.get("abstained")))

    total = len(tasks)
    coverage = None
    if total > 0:
        coverage = round(
            sum(1 for t in tasks if all(
                t.get("outcomes", {}).get(role, {}).get("outcome_present")
                for role in ("candidate_baseline", "llm_span_narrow", "llm_filter", "llm_abstain_filter")
            )) / total,
            6,
        )

    if coverage == 1.0:
        availability = "available"
    elif baseline_count or span_count or filter_count or abstain_count:
        availability = "partial_existing_role_outputs"
    else:
        availability = "missing_existing_role_outputs"

    return {
        "existing_role_output_availability": availability,
        "tasks_with_baseline_outcomes_count": baseline_count,
        "tasks_with_llm_filter_outcomes_count": filter_count,
        "tasks_with_llm_span_narrow_outcomes_count": span_count,
        "tasks_with_llm_abstain_filter_outcomes_count": abstain_count,
        "role_output_coverage_rate": coverage,
        "llm_span_narrow_delta_span_f0_5_mean": _avg(span_deltas),
        "llm_span_narrow_delta_span_f0_5_p95": _percentile(span_deltas, 0.95),
        "llm_span_narrow_added_gold_delta_mean": _avg(added_gold_deltas),
        "llm_span_narrow_added_false_delta_mean": _avg(added_false_deltas),
        "llm_filter_false_primary_delta_mean": _avg(filter_pfp_deltas),
        "llm_abstain_filter_abstained_rate": _rate(sum(abstain_flags), len(abstain_flags)) if abstain_flags else None,
    }


def _compute_high_uncertainty_diagnostic(
    tasks: list[dict[str, Any]],
    selection: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    high_uncertainty_tasks: set[str] = set()
    high_uncertainty_with_outputs: set[str] = set()
    span_deltas: list[float] = []

    for task in tasks:
        candidates = p49._normalize_candidates(task)
        if not candidates:
            continue
        if not _task_contrast_feasible(candidates):
            continue
        if any(_candidate_metadata_risk(c, task) in {"metadata_high_risk", "metadata_unavailable"} for c in candidates):
            continue
        tid = str(task["task_id"])
        high_uncertainty_tasks.add(tid)
        outcomes = task.get("outcomes", {})
        base = outcomes.get("candidate_baseline", {})
        span = outcomes.get("llm_span_narrow", {})
        if base.get("outcome_present") and span.get("outcome_present"):
            high_uncertainty_with_outputs.add(tid)
            sf = _as_float(span.get("span_f0_5"))
            bsf = _as_float(base.get("span_f0_5"))
            if sf is not None and bsf is not None:
                span_deltas.append(sf - bsf)

    candidate_denominator = selection.get("candidate_denominator") or 0
    task_denominator = len(high_uncertainty_tasks)
    helped = sum(1 for d in span_deltas if d > 0)
    harmed = sum(1 for d in span_deltas if d < 0)
    selection_count = selection.get("selected_for_span_narrow_count", 0) + selection.get("selected_for_filter_count", 0) + selection.get("selected_for_abstain_review_count", 0)

    return {
        "high_uncertainty_candidate_count": selection_count,
        "high_uncertainty_candidate_rate": _rate(selection_count, candidate_denominator),
        "high_uncertainty_tasks_with_existing_role_outputs_count": len(high_uncertainty_with_outputs),
        "high_uncertainty_tasks_with_existing_role_outputs_rate": _rate(len(high_uncertainty_with_outputs), task_denominator),
        "existing_role_helped_count": helped if span_deltas else None,
        "existing_role_helped_rate": _rate(helped, len(span_deltas)) if span_deltas else None,
        "existing_role_harmed_count": harmed if span_deltas else None,
        "existing_role_harmed_rate": _rate(harmed, len(span_deltas)) if span_deltas else None,
    }


def _compute_score_phase_correlation(tasks: list[dict[str, Any]], selection: dict[str, Any]) -> dict[str, Any]:
    selected_count = 0
    gold_file_count = 0
    gold_span_count = 0
    file_right_span_wrong_count = 0
    no_gold_selected_count = 0

    added_gold_deltas: list[float] = []
    added_false_deltas: list[float] = []

    for task in tasks:
        candidates = p49._normalize_candidates(task)
        if not candidates:
            continue
        selected = [
            c for c in candidates
            if _candidate_metadata_risk(c, task) not in {"metadata_high_risk", "metadata_unavailable"}
            and _task_contrast_feasible(candidates)
        ]
        if not selected:
            continue
        label = task.get("label") or {}
        gold_files = label.get("gold_files") or set()
        gold_spans = set()
        for gs in label.get("gold_spans", []):
            try:
                gold_spans.add((str(gs.get("path") or "").lower(), int(gs.get("start_line") or 0), int(gs.get("end_line") or 0)))
            except (TypeError, ValueError):
                continue
        has_gold = bool(gold_spans)

        for c in selected:
            selected_count += 1
            cpath = c.get("_path", "").lower()
            cstart = c.get("_start", 0)
            cend = c.get("_end", 0)
            if not has_gold:
                no_gold_selected_count += 1
                continue
            if cpath in gold_files:
                gold_file_count += 1
            span_match = any(
                cpath == gp and cend >= gs and cstart <= ge
                for gp, gs, ge in gold_spans
            )
            if span_match:
                gold_span_count += 1
            elif cpath in gold_files:
                file_right_span_wrong_count += 1

        outcomes = task.get("outcomes", {})
        base = outcomes.get("candidate_baseline", {})
        span = outcomes.get("llm_span_narrow", {})
        if base.get("outcome_present") and span.get("outcome_present"):
            ag = _as_int(span.get("added_gold_span"))
            bg = _as_int(base.get("added_gold_span"))
            if ag is not None and bg is not None:
                added_gold_deltas.append(float(ag - bg))
            af = _as_int(span.get("added_false_span"))
            bf = _as_int(base.get("added_false_span"))
            if af is not None and bf is not None:
                added_false_deltas.append(float(af - bf))

    total_added_gold = sum(added_gold_deltas) if added_gold_deltas else None
    total_added_false = sum(added_false_deltas) if added_false_deltas else None
    false_per_gold = None
    if total_added_gold and total_added_gold > 0 and total_added_false is not None:
        false_per_gold = round(total_added_false / total_added_gold, 6)

    return {
        "not_used_for_selection": True,
        "diagnostic_correlation_only": True,
        "gold_file_rate_selected": _rate(gold_file_count, selected_count),
        "gold_span_rate_selected": _rate(gold_span_count, selected_count),
        "file_right_span_wrong_rate_selected": _rate(file_right_span_wrong_count, selected_count),
        "no_gold_selected_rate": _rate(no_gold_selected_count, selected_count),
        "existing_role_added_gold_span_delta_mean": _avg(added_gold_deltas),
        "existing_role_added_false_span_delta_mean": _avg(added_false_deltas),
        "existing_role_false_per_gold": false_per_gold,
    }


def build_report(
    tasks: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    input_source_count: int,
    insufficient_input_source_count: int,
    report_sources: dict[str, Any],
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

    selection = _compute_candidate_selection(tasks, report_sources)
    blueprint = _compute_prompt_blueprint(tasks, selection)
    replay = _compute_existing_role_replay(tasks)
    high_uncertainty = _compute_high_uncertainty_diagnostic(tasks, selection, replay)
    score_correlation = _compute_score_phase_correlation(tasks, selection)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append("P51 LLM Span Narrow 2.0 diagnostic scaffold is ready; real per-task ephemeral P25 records are required.")
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only scaffold selected {selection['selected_for_span_narrow_count'] + selection['selected_for_filter_count'] + selection['selected_for_abstain_review_count']} candidates across {len(tasks)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P51 built candidate-filter diagnostics for {len(tasks)} ephemeral P25 records."
            )
        conclusion_lines.append(
            "Candidate selection used aggregate metadata and public risk tags only. "
            "Gold, source text, and raw queries were not used for selection."
        )
        conclusion_lines.append(
            "Prompt blueprints are metadata-only shapes, not constructed prompts, and are not sent to any provider."
        )
        conclusion_lines.append(
            "Existing P21 LLM role outcomes were replayed only when present; missing outcomes are reported as unavailable."
        )
        conclusion_lines.append(
            "P51 does not call an LLM, does not create Evidence, does not validate EvidenceCore, and does not change defaults or promote candidates."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_sources": {"p25_policy_records": "ephemeral_v1", **report_sources},
        "input_source_count": input_source_count,
        "insufficient_input_source_count": insufficient_input_source_count,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "source_feature_not_evidence": True,
        "materialized_candidate_not_evidence": True,
        "remote_calls_by_p51": 0,
        "llm_calls_by_p51": 0,
        "prompt_construction_by_p51": False,
        "source_reads_attempted_by_p51": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_sent_to_provider": False,
        "provider_keys_in_artifact": False,
        "raw_query_stored": False,
        "raw_text_stored": False,
        "raw_snippets_committed": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "p51_first_tranche_no_live_llm": True,
        "prompt_blueprint_not_prompt": True,
        "elapsed_ms": elapsed_ms,
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
        **report_sources,
        "metrics": {
            "candidate_selection": selection,
            "prompt_blueprint": blueprint,
            "existing_role_replay": replay,
            "high_uncertainty_diagnostic": high_uncertainty,
            "score_phase_diagnostic_correlation": score_correlation,
            "p51_candidate_selection_v0": {
                "gold_free_deterministic": True,
                "source_reads_by_p51": False,
            },
            "p51_existing_role_replay_v0": {
                "replayed_roles": ["candidate_baseline", "llm_filter", "llm_span_narrow", "llm_abstain_filter"],
                "retrospective_correlation_only": True,
            },
            "p51_prompt_blueprint_v0": {
                "prompt_construction_by_p51": False,
                "raw_prompt_text_available": False,
            },
            "p51_live_opt_in_v0": {
                "availability": "disabled_first_tranche",
                "remote_calls_by_p51": 0,
                "llm_calls_by_p51": 0,
            },
        },
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P51 public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p51") != 0:
        errors.append("remote_calls_by_p51 must be 0")
    if report.get("llm_calls_by_p51") != 0:
        errors.append("llm_calls_by_p51 must be 0")
    if report.get("prompt_construction_by_p51") is not False:
        errors.append("prompt_construction_by_p51 must be false")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "source_feature_not_evidence": True,
        "materialized_candidate_not_evidence": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "p51_first_tranche_no_live_llm": True,
        "prompt_blueprint_not_prompt": True,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_sent_to_provider": False,
        "provider_keys_in_artifact": False,
        "raw_query_stored": False,
        "raw_text_stored": False,
        "raw_snippets_committed": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    for forbidden in ("tasks", "records", "per_task_results", "decision_records", "per_candidate"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    return errors


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P51 LLM Span Narrow 2.0 / Candidate Filter Diagnostic\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P51: {report['remote_calls_by_p51']}",
        f"- LLM calls by P51: {report['llm_calls_by_p51']}",
        f"- Prompt construction by P51: {report['prompt_construction_by_p51']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- Reach metrics available: {report['reach_metrics_available']}",
        f"- P52B report source: `{report.get('p52b_report_source')}`",
        f"- P52A report source: `{report.get('p52a_report_source')}`",
        f"- P52 report source: `{report.get('p52_report_source')}`",
        f"- P49 report source: `{report.get('p49_report_source')}`",
        f"- P50 report source: `{report.get('p50_report_source')}`",
        f"- P48 report source: `{report.get('p48_report_source')}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    def fmt_rate(x: Any) -> str:
        if isinstance(x, dict):
            r = x.get("rate")
            return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"
        return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"

    def fmt_int(x: Any) -> str:
        return str(x) if isinstance(x, int) else "n/a"

    def fmt_scalar(x: Any) -> str:
        return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"

    lines.extend([
        "## Purpose\n",
        "P51 selects diagnostic candidates for a future LLM span-narrow/filter/abstain phase and publishes "
        "prompt-blueprint metadata only. It is a deterministic first-tranche scaffold with no live LLM calls.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Normalize candidates with P46/P49 helpers, preserving only public metadata in memory.",
        "- Apply a gold-free, deterministic selector based on metadata risk, public task bucket/risk tags, "
        "and contrast-pack feasibility; P47/P48 RMC overlay availability is reported separately.",
        "- Build metadata-only prompt-blueprint shapes from selected candidates; no prompt strings are constructed.",
        "- Replay existing P21 role outcomes where present and report aggregate task-level deltas; missing outcomes are unavailable.",
        "- SCORE-phase diagnostics correlate selected candidates with private gold spans after selection; they are not used for selection.",
        "",
        "## Safety notes\n",
        "- P51 first tranche does not call an LLM.",
        "- P51 prompt blueprints are not prompts and are not sent to any provider.",
        "- P51 does not create Evidence, validate EvidenceCore, admit candidates, or change defaults.",
        "- LLM outputs remain candidate/supporting diagnostics only.",
        "- No quality/default/promotion claim is made.",
        "",
    ])

    cs = report["metrics"]["candidate_selection"]
    lines.append("## Candidate selection\n")
    lines.append(f"- Candidate denominator: {cs['candidate_denominator']}")
    lines.append(f"- Pack denominator: {cs['pack_denominator']}")
    lines.append(f"- Selected for span narrow: {cs['selected_for_span_narrow_count']} ({fmt_rate(cs['selected_for_span_narrow_rate'])})")
    lines.append(f"- Selected for filter: {cs['selected_for_filter_count']} ({fmt_rate(cs['selected_for_filter_rate'])})")
    lines.append(f"- Selected for abstain review: {cs['selected_for_abstain_review_count']} ({fmt_rate(cs['selected_for_abstain_review_rate'])})")
    lines.append(f"- Selection unavailable: {cs['selection_unavailable_count']} ({fmt_rate(cs['selection_unavailable_rate'])})")
    lines.append("- Skip reason counts:")
    for reason, count in cs["skip_reason_counts"].items():
        rate = cs["skip_reason_rates"].get(reason)
        lines.append(f"  - {reason}: {count} ({fmt_scalar(rate)})")
    lines.append("")

    pb = report["metrics"]["prompt_blueprint"]
    lines.append("## Prompt blueprint metadata\n")
    lines.append(f"- Availability: `{pb['prompt_blueprint_availability']}`")
    lines.append(f"- Blueprint count: {pb['prompt_blueprint_count']}")
    lines.append(f"- Mean candidates per blueprint: {fmt_scalar(pb['mean_candidates_per_blueprint'])}")
    lines.append(f"- P95 candidates per blueprint: {fmt_scalar(pb['p95_candidates_per_blueprint'])}")
    lines.append(f"- Mean source-lines budget: {fmt_scalar(pb['mean_source_lines_budget'])}")
    lines.append(f"- P95 source-lines budget: {fmt_scalar(pb['p95_source_lines_budget'])}")
    lines.append(f"- Mean context-chars budget: {fmt_scalar(pb['mean_context_chars_budget'])}")
    lines.append(f"- P95 context-chars budget: {fmt_scalar(pb['p95_context_chars_budget'])}")
    lines.append(f"- Pack strategy mix: {pb['pack_strategy_mix']}")
    lines.append(f"- Metadata risk bucket mix: {pb['metadata_risk_bucket_mix']}")
    lines.append(f"- Path kind mix: {pb['path_kind_mix']}")
    lines.append(f"- Source-feature bucket mix: `{pb['source_feature_bucket_mix']['availability']}` ({pb['source_feature_bucket_mix']['reason']})")
    lines.append(f"- Prompt construction by P51: `{pb['prompt_construction_by_p51']}`")
    lines.append(f"- Raw prompt text available: `{pb['raw_prompt_text_available']}`\n")

    er = report["metrics"]["existing_role_replay"]
    lines.append("## Existing role replay\n")
    lines.append(f"- Existing role output availability: `{er['existing_role_output_availability']}`")
    lines.append(f"- Tasks with baseline outcomes: {fmt_int(er['tasks_with_baseline_outcomes_count'])}")
    lines.append(f"- Tasks with llm_span_narrow outcomes: {fmt_int(er['tasks_with_llm_span_narrow_outcomes_count'])}")
    lines.append(f"- Tasks with llm_filter outcomes: {fmt_int(er['tasks_with_llm_filter_outcomes_count'])}")
    lines.append(f"- Tasks with llm_abstain_filter outcomes: {fmt_int(er['tasks_with_llm_abstain_filter_outcomes_count'])}")
    lines.append(f"- Role output coverage rate: {fmt_scalar(er['role_output_coverage_rate'])}")
    lines.append(f"- llm_span_narrow ΔSpanF0.5 mean: {fmt_scalar(er['llm_span_narrow_delta_span_f0_5_mean'])}")
    lines.append(f"- llm_span_narrow ΔSpanF0.5 p95: {fmt_scalar(er['llm_span_narrow_delta_span_f0_5_p95'])}")
    lines.append(f"- llm_span_narrow added-gold delta mean: {fmt_scalar(er['llm_span_narrow_added_gold_delta_mean'])}")
    lines.append(f"- llm_span_narrow added-false delta mean: {fmt_scalar(er['llm_span_narrow_added_false_delta_mean'])}")
    lines.append(f"- llm_filter false-primary delta mean: {fmt_scalar(er['llm_filter_false_primary_delta_mean'])}")
    lines.append(f"- llm_abstain_filter abstained rate: {fmt_scalar(er['llm_abstain_filter_abstained_rate'])}\n")

    hu = report["metrics"]["high_uncertainty_diagnostic"]
    lines.append("## High-uncertainty diagnostic\n")
    lines.append(f"- High-uncertainty candidate count: {fmt_int(hu['high_uncertainty_candidate_count'])} ({fmt_scalar(hu['high_uncertainty_candidate_rate'])})")
    lines.append(f"- High-uncertainty tasks with existing role outputs: {fmt_int(hu['high_uncertainty_tasks_with_existing_role_outputs_count'])} ({fmt_scalar(hu['high_uncertainty_tasks_with_existing_role_outputs_rate'])})")
    lines.append(f"- Existing role helped count: {fmt_int(hu['existing_role_helped_count'])} ({fmt_scalar(hu['existing_role_helped_rate'])})")
    lines.append(f"- Existing role harmed count: {fmt_int(hu['existing_role_harmed_count'])} ({fmt_scalar(hu['existing_role_harmed_rate'])})")
    lines.append("")

    sp = report["metrics"]["score_phase_diagnostic_correlation"]
    lines.append("## SCORE-phase diagnostic correlation (not used for selection)\n")
    lines.append(f"- Gold-file rate selected: {fmt_scalar(sp['gold_file_rate_selected'])}")
    lines.append(f"- Gold-span rate selected: {fmt_scalar(sp['gold_span_rate_selected'])}")
    lines.append(f"- File-right-span-wrong rate selected: {fmt_scalar(sp['file_right_span_wrong_rate_selected'])}")
    lines.append(f"- No-gold selected rate: {fmt_scalar(sp['no_gold_selected_rate'])}")
    lines.append(f"- Existing role added-gold span delta mean: {fmt_scalar(sp['existing_role_added_gold_span_delta_mean'])}")
    lines.append(f"- Existing role added-false span delta mean: {fmt_scalar(sp['existing_role_added_false_span_delta_mean'])}")
    lines.append(f"- Existing role false-per-gold: {fmt_scalar(sp['existing_role_false_per_gold'])}\n")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def _inject_self_test_missing_outcomes(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Inject synthetic tasks to exercise selection and availability logic."""
    records = [dict(r) for r in records]

    def pool(paths: list[tuple[str, int, int]]) -> list[dict[str, Any]]:
        return [
            {"rank": i + 1, "path": p, "start_line": s, "end_line": e, "candidate_id": f"cid_{i+1}"}
            for i, (p, s, e) in enumerate(paths)
        ]

    def gold(path: str, start: int, end: int) -> dict[str, Any]:
        return {"has_gold": True, "gold_spans": [{"path": path, "start_line": start, "end_line": end}]}

    # Positive task with two low-risk, contrast-feasible candidates and existing span-narrow outcome.
    records.append({
        "task_id": "p51-st-select-span",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {
            "candidate_count": 2,
            "candidate_support_exists": True,
            "symbol_anchor": True,
            "rrf_backed_by_anchor": True,
            "query_noise": 0.0,
        },
        "p31_candidate_pools": {
            "candidate_baseline": pool([("src/a.py", 10, 15), ("src/b.py", 20, 25)]),
            "symbol_regex_union": pool([("src/a.py", 10, 15)]),
            "rrf_primary": pool([("src/a.py", 10, 15), ("src/b.py", 20, 25)]),
        },
        "p33b_anchor_subtypes": [
            {"candidate_id": "cid_1", "rank": 1, "source_class": "symbol_only", "agreement_class": "span_overlap", "rrf_backing": True, "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short"},
            {"candidate_id": "cid_2", "rank": 2, "source_class": "symbol_only", "agreement_class": "span_overlap", "rrf_backing": True, "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short"},
        ],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "p31_score_gold": gold("src/a.py", 10, 15),
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.25, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.30, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
        "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.20, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "llm_abstain_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.18, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0, "abstained": False},
    })

    # No-gold task with two medium-risk candidates and existing filter/abstain outcomes.
    records.append({
        "task_id": "p51-st-select-filter",
        "repo_id": "js_express",
        "task_bucket": "negative",
        "task_risk_tags": ["negative"],
        "score_group": "no_gold",
        "route_features": {
            "candidate_count": 2,
            "candidate_support_exists": True,
            "query_noise": 0.5,
        },
        "p31_candidate_pools": {
            "candidate_baseline": pool([("src/noise1.py", 1, 5), ("src/noise2.py", 10, 14)]),
            "symbol_regex_union": pool([("src/noise1.py", 1, 5), ("src/noise2.py", 10, 14)]),
        },
        "p33b_anchor_subtypes": [
            {"candidate_id": "cid_1", "rank": 1, "source_class": "symbol_regex_fusion", "agreement_class": "span_overlap", "rrf_backing": False, "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short"},
            {"candidate_id": "cid_2", "rank": 2, "source_class": "symbol_regex_fusion", "agreement_class": "span_overlap", "rrf_backing": False, "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short"},
        ],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "p31_score_gold": {"has_gold": False, "gold_spans": []},
        "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.40, "no_gold_false_primary_rate": 0.40, "added_gold_span": 0, "added_false_span": 4},
        "llm_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.10, "added_gold_span": 0, "added_false_span": 1},
        "llm_abstain_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0, "abstained": True},
    })

    # Positive task with contrast-feasible candidates but missing LLM role outcomes.
    records.append({
        "task_id": "p51-st-missing-roles",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["likely_positive"],
        "score_group": "positive",
        "route_features": {
            "candidate_count": 2,
            "candidate_support_exists": True,
            "symbol_anchor": True,
            "rrf_backed_by_anchor": True,
            "query_noise": 0.1,
        },
        "p31_candidate_pools": {
            "candidate_baseline": pool([("src/app.py", 10, 15), ("src/util.py", 5, 8)]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.20, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        # Intentionally omit llm_span_narrow, llm_filter, llm_abstain_filter outcomes.
    })

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="P51 LLM Span Narrow 2.0 / Candidate Filter Diagnostic")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--p52b-report", type=Path, default=None, help="Optional P52B report for aggregate availability.")
    parser.add_argument("--p52a-report", type=Path, default=None, help="Optional P52A report for aggregate availability.")
    parser.add_argument("--p52-report", type=Path, default=None, help="Optional P52 report for aggregate availability.")
    parser.add_argument("--p49-report", type=Path, default=None, help="Optional P49 report for aggregate availability.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 report for aggregate availability.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 report for aggregate availability.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_records = _inject_self_test_missing_outcomes(p46.make_self_test_records())
    elif args.input:
        input_paths = list(args.input)
        raw_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_count = 0
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P51 diagnostic selection.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P51 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_task_detail"
            reason = marker_reasons[marker]
            insufficient_count += 1
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (p46.normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P51 normalization."

    report_sources: dict[str, Any] = {}
    report_sources.update(_read_optional_report(args.p52b_report, "p52b"))
    report_sources.update(_read_optional_report(args.p52a_report, "p52a"))
    report_sources.update(_read_optional_report(args.p52_report, "p52"))
    report_sources.update(_read_optional_report(args.p49_report, "p49"))
    report_sources.update(_read_optional_report(args.p50_report, "p50"))
    # P47 is not a CLI arg in first tranche; derive availability from P48 report context only.
    report_sources["p47_report_source"] = "not_provided"
    report_sources["p47_quality_gate_status"] = "not_provided"
    report_sources.update(_read_optional_report(args.p48_report, "p48"))

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        normalized_tasks,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        input_source_count=1 if args.self_test else max(1, len(args.input or [])),
        insufficient_input_source_count=insufficient_count,
        report_sources=report_sources,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P51 report written to {args.out}")
    print(f"P51 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
