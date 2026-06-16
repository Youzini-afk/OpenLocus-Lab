#!/usr/bin/env python3
"""P60 RMC Policy v2 v0 — deterministic diagnostic policy comparison matrix.

P60 is a deterministic, no-live-LLM, no-provider, aggregate-only diagnostic
policy COMPARISON layer that advances ``request_more_context`` (RMC) from P47/P48
geometry/overlay into a comparable policy matrix.  For the same frozen
candidate/task inputs, each policy selects only the NEXT diagnostic action; P60
reports aggregate routing counts plus SCORE-phase gold reach / false cost
diagnostics and labeled cost/latency ESTIMATES.

RMC is NOT evidence/admission/default.  P60 declares NO winner and recommends
NO default.

Hard constraints:
* No LLM/remote calls; ``remote_calls_by_p60=0``, ``llm_calls_by_p60=0``.
* No provider config reads; ``provider_config_read_by_p60=false``.
* No prompt construction; ``prompt_construction_by_p60=false``.
* No source reads; ``source_reads_attempted_by_p60=false``.
* RUN phase is gold-free.  SCORE phase loads labels only after selections are
  frozen and is explicitly flagged ``score_phase_only_metrics=true``.
* Public output is aggregate-only: no task IDs, candidate IDs, repo IDs, paths,
  spans, line ranges, digests, queries, snippets, prompts, responses, gold spans,
  private labels, provider keys, or per-task/per-candidate rows.
* No promotion/default/evidence claims; no winner; no default recommendation.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p25_bucket_policy as p25
import p30_admission_model_v3 as p30
import p46_candidate_reach_cost_map as p46
import p49_contrastive_candidate_pack_scaffold as p49

try:
    import p52c_local_verifier_scoring_simulator as p52c
except Exception:  # pragma: no cover
    p52c = None  # type: ignore[assignment]

SCHEMA_VERSION = "p60-rmc-policy-v2-v0"
GENERATED_BY = "p60_rmc_policy_v2"
STAGE = "P60 RMC Policy v2 v0"

DEFAULT_OUT = Path("artifacts/p60_rmc_policy_v2/p60_rmc_policy_v2_report.json")
DEFAULT_DOC = Path("docs/en/p60-rmc-policy-v2.md")

ALLOWED_STATUS = {
    "self_test_only",
    "diagnostic_policy_matrix_available",
    "diagnostic_policy_matrix_partial",
    "insufficient_records",
    "blocked_safety",
}

ALLOWED_NEXT_ACTIONS = {
    "local_verifier",
    "contrastive_pack",
    "p51c_span_narrow",
    "filter",
    "weak_candidate_only",
}

FORBIDDEN_OUTPUT_ACTIONS = {
    "admit_symbol_regex_union",
    "admit_rrf_primary",
    "admit_llm_span_narrow",
    "candidate_baseline_primary",
    "primary_admit",
    "evidence",
    "accept_evidence",
}

# Eight policies required by the spec.
POLICY_NAMES = [
    "baseline_p25_bucket_routed_v0",
    "h4b_selective_readmission",
    "rmc_all_uncertain",
    "rmc_high_diagnostic_only",
    "rmc_span_overlap_only",
    "rmc_symbol_regex_fusion_only",
    "rmc_high_score_plus_contrast_pack",
    "rmc_high_score_plus_source_backed_verifier",
]

POLICY_FAMILIES = {
    "baseline_p25_bucket_routed_v0": "reference",
    "h4b_selective_readmission": "reference",
    "rmc_all_uncertain": "rmc",
    "rmc_high_diagnostic_only": "rmc",
    "rmc_span_overlap_only": "rmc",
    "rmc_symbol_regex_fusion_only": "rmc",
    "rmc_high_score_plus_contrast_pack": "rmc",
    "rmc_high_score_plus_source_backed_verifier": "rmc",
}

# Top-level keys / safety flags that are intentionally public and must be
# allowlisted during the recursive forbidden-key scan.
P60_SAFETY_FLAG_KEYS = {
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
    "rmc_not_evidence",
    "rmc_not_admission",
    "rmc_next_action_only",
    "policy_comparison_not_ranking",
    "run_phase_gold_free",
    "score_phase_only_metrics",
    "gold_used_for_policy_selection",
    "labels_loaded_after_policy_selection",
    "aggregate_only_public_artifact",
    "remote_calls_by_p60",
    "llm_calls_by_p60",
    "provider_config_read_by_p60",
    "prompt_construction_by_p60",
    "source_reads_attempted_by_p60",
    "expected_cost_latency_are_estimates",
    "cost_latency_measurements_taken_by_p60",
    "raw_prompts_stored",
    "raw_query_stored",
    "raw_responses_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_text_stored",
    "raw_source_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
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
    "comparison_frame",
    "metrics",
    "conclusion",
    "validation",
    "upstream_carry_forward",
    # comparison_frame keys
    "comparison_denominator_aligned",
    "same_input_records_for_all_policies",
    "no_winner_selected",
    "no_default_recommendation",
    # metrics blocks
    "by_policy",
    "denominators",
    "policy_name",
    "policy_family",
    "availability",
    "candidate_denominator",
    "task_denominator",
    "rmc_candidate_count",
    "rmc_candidate_rate",
    "rmc_task_count",
    "rmc_task_rate",
    "next_action_counts",
    "next_action_rates",
    "gold_reach_diagnostics",
    "false_cost_diagnostics",
    "rmc_to_llm_eligibility",
    "expected_provider_spend_estimates",
    # gold_reach_diagnostics
    "score_phase_only",
    "not_used_for_policy_selection",
    "positive_task_denominator",
    "gold_file_reach_count",
    "gold_file_reach_rate",
    "gold_span_overlap_reach_count",
    "gold_span_overlap_reach_rate",
    "file_right_span_wrong_count",
    "file_right_span_wrong_rate",
    # false_cost_diagnostics
    "no_gold_task_denominator",
    "rmc_on_no_gold_count",
    "rmc_on_no_gold_rate",
    "false_cost_count",
    "false_cost_rate",
    "false_per_gold_reached",
    # rmc_to_llm_eligibility
    "eligibility_source",
    "eligibility_not_authorization",
    "eligible_count",
    "eligible_rate",
    "ineligible_count",
    "missing_contract_count",
    # expected_provider_spend_estimates
    "estimate_only_not_measurement",
    "provider_calls_by_p60",
    "estimated_provider_calls",
    "estimated_latency_ms",
    "estimated_cost_usd",
    "estimate_parameter_profile",
    "per_next_action_estimates",
}

# Exact keys that must never appear in the public artifact.  Safety flag keys
# above are explicitly allowlisted.
FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "repo_id",
    "candidate_id",
    "path",
    "start_line",
    "end_line",
    "span",
    "content_sha",
    "digest",
    "hash",
    "query",
    "raw_query",
    "snippet",
    "source_text",
    "raw_source",
    "prompt",
    "response",
    "provider",
    "model",
    "base_url",
    "api_key",
    "api_token",
    "provider_key",
    "endpoint",
    "gold_spans",
    "private_label",
    "private_labels",
    "label",
    "labels",
    "tasks",
    "records",
    "per_task",
    "per_task_results",
    "per_candidate_results",
    "decision_records",
    "candidate_pool",
    "raw_candidates",
    "pack_items",
    "winner",
    "best_policy",
    "recommended_policy",
    "promotable_policy",
    "default_policy",
    "promotion_decision",
    "default_decision",
    "admission_decision",
    "evidence_valid",
}

# Keys that carry gold or label information and are stripped before RUN-phase
# normalization.
_GOLD_LABEL_KEYS = {
    "label",
    "labels",
    "p31_score_gold",
    "gold",
    "gold_spans",
    "has_gold",
    "score_group",
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
    """Recursively reject exact keys that must not appear in public artifacts."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P60_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _scan_values_for_leaks(obj: Any, prefix: str = "") -> list[str]:
    """Reject absolute paths, URLs, and API-key-like strings in values."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            violations.extend(_scan_values_for_leaks(value, prefix + str(key) + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_values_for_leaks(value, prefix + str(idx) + "."))
    elif isinstance(obj, str):
        text = obj.strip()
        if len(text) > 1 and (text.startswith("/") or text.startswith("\\")):
            violations.append(prefix + " looks like an absolute path")
        elif "://" in text:
            violations.append(prefix + " looks like a URL")
        elif re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
            violations.append(prefix + " looks like an API key")
    return violations


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata."""
    source_key = f"{report_name}_report_source"
    status_key = f"{report_name}_status"
    if path is None or not path.exists():
        return {
            source_key: "not_provided",
            status_key: "not_provided",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            source_key: "invalid_json",
            status_key: "invalid_json",
        }
    result: dict[str, Any] = {source_key: "provided_report"}
    status = data.get("status")
    if not isinstance(status, str):
        status = "not_provided"
    result[status_key] = status
    return result


def _build_construction_tasks(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the RUN-phase gold-free construction view directly from raw records.

    Any raw key that carries gold/label information is stripped from a shallow
    copy before normalization, so the construction view cannot contain gold
    spans, labels, or has_gold state.  Only public task metadata and candidate
    metadata are retained.
    """
    construction_tasks: list[dict[str, Any]] = []
    for raw in raw_records:
        stripped = {k: v for k, v in raw.items() if k not in _GOLD_LABEL_KEYS}
        nt = p46.normalize_task(stripped)
        if nt:
            construction_tasks.append(nt)
    return construction_tasks


def _extract_labels(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract gold/label information from the original raw records.

    This is the SCORE-phase label load.  It must be called only after policy
    selections are frozen from the gold-free construction view.
    """
    labels: list[dict[str, Any]] = []
    for raw in raw_records:
        t = p46.normalize_task(raw)
        if t is None:
            labels.append({"has_gold": False, "has_gold_spans": False, "label": {}})
        else:
            labels.append({
                "has_gold": bool(t.get("has_gold")),
                "has_gold_spans": bool(t.get("has_gold_spans")),
                "label": t.get("label", {}),
            })
    return labels


def _normalize_candidates(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize candidate pools using P49 helper on the construction view."""
    return p49._normalize_candidates(task)


def _gold_files(label: dict[str, Any]) -> set[str]:
    return label.get("gold_files", set())


def _gold_spans(label: dict[str, Any]) -> set[tuple[str, int, int]]:
    out: set[tuple[str, int, int]] = set()
    for gs in label.get("gold_spans", []):
        path = gs.get("path", "")
        start = gs.get("start_line", 0)
        end = gs.get("end_line", 0)
        if path:
            out.add((path, start, end))
    return out


def _is_file_reached(cand: dict[str, Any], label: dict[str, Any]) -> bool:
    path = str(cand.get("_path") or cand.get("path") or "").lower()
    return bool(path and path in _gold_files(label))


def _is_span_reached(cand: dict[str, Any], label: dict[str, Any]) -> bool:
    gold_spans = _gold_spans(label)
    if not gold_spans:
        return False
    path = str(cand.get("_path") or cand.get("path") or "").lower()
    start = _as_int(cand.get("_start") or cand.get("start_line")) or 0
    end = _as_int(cand.get("_end") or cand.get("end_line")) or 0
    for gp, gs, ge in gold_spans:
        if path == gp and end >= gs and start <= ge:
            return True
    return False


def _is_file_right_span_wrong(cand: dict[str, Any], label: dict[str, Any]) -> bool:
    return _is_file_reached(cand, label) and not _is_span_reached(cand, label)


def _diagnostic_score_bucket(cand: dict[str, Any], task: dict[str, Any]) -> str:
    """Deterministic gold-free diagnostic score bucket from candidate metadata."""
    subtype = cand.get("subtype") or {}
    path_kind = str(cand.get("path_kind") or "unknown")
    source_class = str(subtype.get("source_class") or "other")
    agreement_class = str(subtype.get("agreement_class") or "other")
    rrf_backing = bool(subtype.get("rrf_backing"))

    score = 0
    if path_kind == "source":
        score += 1
    if path_kind in {"generated_or_vendor", "unknown"}:
        score -= 1
    if source_class == "symbol_regex_fusion":
        score += 2
    elif source_class == "symbol_only":
        score += 1
    elif source_class == "regex_only":
        score -= 2
    if agreement_class == "span_overlap":
        score += 2
    elif agreement_class == "same_file_only":
        score += 1
    elif agreement_class == "disagree":
        score -= 1
    elif agreement_class == "single_source":
        score -= 2
    if rrf_backing:
        score += 1
    if source_class == "symbol_regex_fusion" and agreement_class == "span_overlap" and rrf_backing:
        score += 2

    if score >= 4:
        return "diagnostic_score_high"
    if score >= 2:
        return "diagnostic_score_medium"
    if score <= -2:
        return "diagnostic_score_low"
    return "diagnostic_score_medium"


def _is_high_diagnostic(cand: dict[str, Any]) -> bool:
    return _diagnostic_score_bucket(cand, {}) == "diagnostic_score_high"


def _is_span_overlap(cand: dict[str, Any]) -> bool:
    subtype = cand.get("subtype") or {}
    return str(subtype.get("agreement_class") or "") == "span_overlap"


def _is_symbol_regex_fusion(cand: dict[str, Any]) -> bool:
    subtype = cand.get("subtype") or {}
    return (
        str(subtype.get("source_class") or "") == "symbol_regex_fusion"
        and str(subtype.get("agreement_class") or "") == "span_overlap"
    )


def _source_backed_metadata_available(task: dict[str, Any]) -> bool:
    """True if gold-free subtype metadata is present for any candidate in the task."""
    for cand in _normalize_candidates(task):
        if cand.get("subtype"):
            return True
    return False


def _has_contrastive_pack(task: dict[str, Any]) -> bool:
    """True if the P49 anchor_contrast_pack_v0 contains contrastive information."""
    candidates = _normalize_candidates(task)
    if not candidates:
        return False
    pack = p49._build_anchor_contrast_pack_v0(candidates)
    selected = pack.get("selected", [])
    if not selected:
        return False
    kinds = {c.get("path_kind") for c in selected}
    return len(kinds) > 1 or any(c.get("path_kind") in {"test", "doc", "config", "generated_or_vendor"} for c in selected)


def _p25_next_action(task: dict[str, Any]) -> str:
    """Reference: P25 bucket-routed v0 translated to a next diagnostic action."""
    bucket = str(task.get("task_bucket", "unknown"))
    tags = {str(t).lower() for t in (task.get("task_risk_tags") or [])}

    if bucket in {"exact_symbol", "exact_symbol_unique", "config", "route_handler"}:
        return "local_verifier"
    if "weak_candidates" in tags or "stale-like" in tags:
        return "weak_candidate_only"
    if bucket in {"positive", "likely_positive", "high_confidence"}:
        return "contrastive_pack"
    if bucket in {"negative", "dense_false_positive", "hard_distractor", "dense_quiver_trap"}:
        return "filter"
    if bucket == "ambiguous" or "ambiguous" in tags or "hallucination_risk" in tags:
        return "filter"
    return "p51c_span_narrow"


def _as_p30_task(task: dict[str, Any]) -> dict[str, Any]:
    """Create a gold-free task view compatible with P30 admission functions."""
    rc = task.get("route_context") or {}
    p30_task = dict(task)
    p30_task.update(rc)
    # Ensure p30 helpers can see the top-level route features.
    if "route_features" not in p30_task and rc.get("route_features"):
        p30_task["route_features"] = rc["route_features"]
    return p30_task


def _h4b_next_action(task: dict[str, Any]) -> str:
    """Reference: P30-H4B action translated to a next diagnostic action."""
    h4b_result = p30.route_admission_v3_h4b(_as_p30_task(task))
    action = str(h4b_result.get("action", "weak_candidate_only"))
    mapping = {
        "abstain": "filter",
        "apply_llm_filter": "filter",
        "supporting_only": "contrastive_pack",
        "weak_candidate_only": "weak_candidate_only",
        "admit_symbol_regex_union": "local_verifier",
        "admit_rrf_primary": "local_verifier",
        "admit_llm_span_narrow": "p51c_span_narrow",
    }
    return mapping.get(action, "weak_candidate_only")


def _policy_available(policy_name: str, task: dict[str, Any], candidates: list[dict[str, Any]]) -> bool:
    """Check whether a policy has the gold-free handoff it needs."""
    if policy_name == "baseline_p25_bucket_routed_v0":
        return bool(task.get("route_context"))
    # H4B is a reference lane that always falls back to weak_candidate_only when
    # the P33B handoff is missing, so it is considered available even without it.
    if policy_name == "h4b_selective_readmission":
        return True
    if policy_name in {
        "rmc_high_diagnostic_only",
        "rmc_span_overlap_only",
        "rmc_symbol_regex_fusion_only",
        "rmc_high_score_plus_contrast_pack",
        "rmc_high_score_plus_source_backed_verifier",
    }:
        return any(cand.get("subtype") for cand in candidates) or _source_backed_metadata_available(task)
    return True


def _select_next_action(policy_name: str, task: dict[str, Any], cand: dict[str, Any]) -> str:
    """Select a next diagnostic action for a candidate using only gold-free features."""
    if policy_name == "baseline_p25_bucket_routed_v0":
        return _p25_next_action(task)
    if policy_name == "h4b_selective_readmission":
        return _h4b_next_action(task)
    if policy_name == "rmc_all_uncertain":
        return "local_verifier"
    if policy_name == "rmc_high_diagnostic_only":
        if _is_high_diagnostic(cand):
            return "local_verifier"
        return "filter"
    if policy_name == "rmc_span_overlap_only":
        if _is_span_overlap(cand):
            return "p51c_span_narrow"
        return "filter"
    if policy_name == "rmc_symbol_regex_fusion_only":
        if _is_symbol_regex_fusion(cand):
            return "local_verifier"
        return "filter"
    if policy_name == "rmc_high_score_plus_contrast_pack":
        if _is_high_diagnostic(cand) and _has_contrastive_pack(task):
            return "contrastive_pack"
        return "filter"
    if policy_name == "rmc_high_score_plus_source_backed_verifier":
        if _is_high_diagnostic(cand) and _source_backed_metadata_available(task):
            return "local_verifier"
        return "filter"
    return "weak_candidate_only"


def _build_policy_selections(
    construction_tasks: list[dict[str, Any]],
) -> dict[str, list[list[str]]]:
    """RUN phase: build and freeze all policy selections from the gold-free view.

    Returns a dict mapping policy_name -> list of candidate-action lists aligned
    with construction_tasks.  No gold/label data is used.
    """
    selections: dict[str, list[list[str]]] = {policy: [] for policy in POLICY_NAMES}
    for task in construction_tasks:
        candidates = _normalize_candidates(task)
        for policy in POLICY_NAMES:
            if not _policy_available(policy, task, candidates):
                selections[policy].append([])
            else:
                selections[policy].append([_select_next_action(policy, task, cand) for cand in candidates])
    return selections


def _compute_policy_metrics(
    selections: list[list[str]],
    construction_tasks: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    policy_name: str,
) -> dict[str, Any]:
    """Compute aggregate metrics for a single policy from frozen selections."""
    if len(selections) != len(labels) or len(selections) != len(construction_tasks):
        raise ValueError("selections, construction_tasks, and labels must be aligned")

    candidate_denominator = 0
    task_denominator = 0
    rmc_candidate_count = 0
    rmc_task_count = 0
    next_action_counts: dict[str, int] = {action: 0 for action in ALLOWED_NEXT_ACTIONS}

    # Main candidate-level counting loop.
    for task_actions, task in zip(selections, construction_tasks):
        candidates = _normalize_candidates(task)
        has_candidates = bool(candidates)
        if has_candidates:
            task_denominator += 1
        task_has_action = False
        for cand, action in zip(candidates, task_actions):
            if action not in ALLOWED_NEXT_ACTIONS:
                action = "weak_candidate_only"
            candidate_denominator += 1
            next_action_counts[action] += 1
            rmc_candidate_count += 1
            if not task_has_action:
                rmc_task_count += 1
                task_has_action = True

    # False cost diagnostics (task-level counts so rates stay in [0,1]).
    positive_task_denominator = 0
    no_gold_task_denominator = 0
    rmc_on_no_gold_count = 0
    false_cost_count = 0

    for task_actions, task, lab in zip(selections, construction_tasks, labels):
        candidates = _normalize_candidates(task)
        if not candidates:
            continue
        if lab.get("has_gold"):
            positive_task_denominator += 1
        else:
            no_gold_task_denominator += 1
            task_actions_set = set(task_actions)
            if task_actions_set:
                rmc_on_no_gold_count += 1
            if task_actions_set & {"p51c_span_narrow", "filter"}:
                false_cost_count += 1

    # Candidate-level reach diagnostics (SCORE phase only).
    gold_file_reach_count = 0
    gold_span_overlap_reach_count = 0
    file_right_span_wrong_count = 0

    for task_actions, task, lab in zip(selections, construction_tasks, labels):
        candidates = _normalize_candidates(task)
        if not (lab.get("has_gold") and lab.get("has_gold_spans")):
            continue
        for cand in candidates:
            if _is_file_reached(cand, lab["label"]):
                gold_file_reach_count += 1
            if _is_span_reached(cand, lab["label"]):
                gold_span_overlap_reach_count += 1
            if _is_file_right_span_wrong(cand, lab["label"]):
                file_right_span_wrong_count += 1

    # LLM eligibility (candidate-level).
    eligible_count = 0
    ineligible_count = 0
    missing_contract_count = 0

    for task_actions, task in zip(selections, construction_tasks):
        candidates = _normalize_candidates(task)
        for cand, action in zip(candidates, task_actions):
            if action in {"p51c_span_narrow", "filter"}:
                eligible_count += 1
            elif action in {"local_verifier", "contrastive_pack", "weak_candidate_only"}:
                ineligible_count += 1
            else:
                missing_contract_count += 1

    # Determine availability.
    is_subtype_policy = policy_name in {
        "rmc_high_diagnostic_only",
        "rmc_span_overlap_only",
        "rmc_symbol_regex_fusion_only",
        "rmc_high_score_plus_contrast_pack",
        "rmc_high_score_plus_source_backed_verifier",
    }
    has_handoff = any(
        bool(_normalize_candidates(task))
        and any(cand.get("subtype") for cand in _normalize_candidates(task))
        for task in construction_tasks
    )
    if is_subtype_policy and not has_handoff:
        availability = "unavailable_missing_gold_free_handoff"
    elif candidate_denominator == 0:
        availability = "unavailable_missing_candidate_pool"
    elif is_subtype_policy and rmc_candidate_count == 0:
        availability = "partial"
    elif rmc_candidate_count == 0 and candidate_denominator > 0:
        availability = "partial"
    else:
        availability = "available"

    next_action_rates = {action: _rate(next_action_counts[action], rmc_candidate_count) for action in ALLOWED_NEXT_ACTIONS}

    gold_reach_diagnostics = {
        "score_phase_only": True,
        "not_used_for_policy_selection": True,
        "positive_task_denominator": positive_task_denominator,
        "gold_file_reach_count": gold_file_reach_count,
        "gold_file_reach_rate": _rate(gold_file_reach_count, rmc_candidate_count),
        "gold_span_overlap_reach_count": gold_span_overlap_reach_count,
        "gold_span_overlap_reach_rate": _rate(gold_span_overlap_reach_count, rmc_candidate_count),
        "file_right_span_wrong_count": file_right_span_wrong_count,
        "file_right_span_wrong_rate": _rate(file_right_span_wrong_count, rmc_candidate_count),
    }

    false_cost_diagnostics = {
        "score_phase_only": True,
        "not_used_for_policy_selection": True,
        "no_gold_task_denominator": no_gold_task_denominator,
        "rmc_on_no_gold_count": rmc_on_no_gold_count,
        "rmc_on_no_gold_rate": _rate(rmc_on_no_gold_count, no_gold_task_denominator),
        "false_cost_count": false_cost_count,
        "false_cost_rate": _rate(false_cost_count, no_gold_task_denominator),
        "false_per_gold_reached": _rate(false_cost_count, gold_span_overlap_reach_count) if gold_span_overlap_reach_count else None,
    }

    rmc_to_llm_eligibility = {
        "eligibility_source": "p60_rmc_policy_v2_aggregate_only",
        "eligibility_not_authorization": True,
        "eligible_count": eligible_count,
        "eligible_rate": _rate(eligible_count, rmc_candidate_count),
        "ineligible_count": ineligible_count,
        "missing_contract_count": missing_contract_count,
    }

    per_next_action_estimates = {
        "local_verifier": {
            "estimated_provider_calls": 0,
            "estimated_latency_ms": 0,
            "estimated_cost_usd": 0.0,
        },
        "contrastive_pack": {
            "estimated_provider_calls": 0,
            "estimated_latency_ms": 0,
            "estimated_cost_usd": 0.0,
        },
        "weak_candidate_only": {
            "estimated_provider_calls": 0,
            "estimated_latency_ms": 0,
            "estimated_cost_usd": 0.0,
        },
        "p51c_span_narrow": {
            "estimated_provider_calls": 1,
            "estimated_latency_ms": None,
            "estimated_cost_usd": None,
        },
        "filter": {
            "estimated_provider_calls": 1,
            "estimated_latency_ms": None,
            "estimated_cost_usd": None,
        },
    }

    estimated_provider_calls = sum(
        next_action_counts[action] * (per_next_action_estimates[action]["estimated_provider_calls"] or 0)
        for action in ALLOWED_NEXT_ACTIONS
    )
    estimated_latency_ms = None
    estimated_cost_usd = None

    expected_provider_spend_estimates = {
        "estimate_only_not_measurement": True,
        "provider_calls_by_p60": 0,
        "estimated_provider_calls": estimated_provider_calls,
        "estimated_latency_ms": estimated_latency_ms,
        "estimated_cost_usd": estimated_cost_usd,
        "estimate_parameter_profile": "p60_default_v0",
        "per_next_action_estimates": per_next_action_estimates,
    }

    return {
        "policy_name": policy_name,
        "policy_family": POLICY_FAMILIES.get(policy_name, "unknown"),
        "availability": availability,
        "candidate_denominator": candidate_denominator,
        "task_denominator": task_denominator,
        "rmc_candidate_count": rmc_candidate_count,
        "rmc_candidate_rate": _rate(rmc_candidate_count, candidate_denominator),
        "rmc_task_count": rmc_task_count,
        "rmc_task_rate": _rate(rmc_task_count, task_denominator),
        "next_action_counts": next_action_counts,
        "next_action_rates": next_action_rates,
        "gold_reach_diagnostics": gold_reach_diagnostics,
        "false_cost_diagnostics": false_cost_diagnostics,
        "rmc_to_llm_eligibility": rmc_to_llm_eligibility,
        "expected_provider_spend_estimates": expected_provider_spend_estimates,
    }


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate schema, safety flags, forbidden-key/value scan, and invariants."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        errors.append("generated_by mismatch")
    if report.get("stage") != STAGE:
        errors.append("stage mismatch")
    if report.get("status") not in ALLOWED_STATUS:
        errors.append(f"status must be one of {ALLOWED_STATUS}")

    expected = {
        "not_quality_evidence": True,
        "real_evaluation": False,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "rmc_not_evidence": True,
        "rmc_not_admission": True,
        "rmc_next_action_only": True,
        "policy_comparison_not_ranking": True,
        "run_phase_gold_free": True,
        "score_phase_only_metrics": True,
        "gold_used_for_policy_selection": False,
        "labels_loaded_after_policy_selection": True,
        "aggregate_only_public_artifact": True,
        "remote_calls_by_p60": 0,
        "llm_calls_by_p60": 0,
        "provider_config_read_by_p60": False,
        "prompt_construction_by_p60": False,
        "source_reads_attempted_by_p60": False,
        "expected_cost_latency_are_estimates": True,
        "cost_latency_measurements_taken_by_p60": False,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "private_labels_committed": False,
    }
    for flag, value in expected.items():
        if report.get(flag) is not value:
            errors.append(f"{flag} must be {value}")

    comparison = report.get("comparison_frame", {})
    for key, value in {
        "comparison_denominator_aligned": True,
        "same_input_records_for_all_policies": True,
        "policy_comparison_not_ranking": True,
        "no_winner_selected": True,
        "no_default_recommendation": True,
    }.items():
        if comparison.get(key) is not value:
            errors.append(f"comparison_frame.{key} must be {value}")

    # No top-level per-task rows.
    for forbidden in ("tasks", "records", "per_task_results", "per_candidate_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    # Forbidden key and value scans.
    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_scan_values_for_leaks(report))

    # Conservation invariants.
    by_policy = report.get("metrics", {}).get("by_policy", {})
    for policy_name, block in by_policy.items():
        counts = block.get("next_action_counts", {})
        rmc_count = block.get("rmc_candidate_count")
        if isinstance(rmc_count, int):
            total = sum(counts.get(a, 0) for a in ALLOWED_NEXT_ACTIONS)
            if total != rmc_count:
                errors.append(f"{policy_name}: next_action_counts sum {total} != rmc_candidate_count {rmc_count}")
        cand_denom = block.get("candidate_denominator")
        if isinstance(cand_denom, int) and isinstance(rmc_count, int):
            if cand_denom < rmc_count:
                errors.append(f"{policy_name}: candidate_denominator < rmc_candidate_count")
        # Rate invariants.
        for rate_key, rate_value in block.get("next_action_rates", {}).items():
            if rate_value is not None and not (0.0 <= float(rate_value) <= 1.0 + 1e-9):
                errors.append(f"{policy_name}: {rate_key} out of range")
        for diag in (block.get("gold_reach_diagnostics", {}), block.get("false_cost_diagnostics", {})):
            for rate_key, rate_value in diag.items():
                if rate_key.endswith("_rate") and rate_value is not None:
                    if not (0.0 <= float(rate_value) <= 1.0 + 1e-9):
                        errors.append(f"{policy_name}: {rate_key} out of range")

    # No ranking/winner/default/evidence claims in conclusion/status text.
    forbidden_phrases = [
        "best policy",
        "winner",
        "outperforms",
        "promotable",
        "promotion candidate",
        "default should change",
        "safe to deploy",
        "verifier passed",
        "evidence admitted",
        "LLM-ready",
        "provider-ready",
        "quality evidence",
        "recommended_policy",
        "best_policy",
    ]
    text = " ".join(report.get("conclusion", [])) + " " + str(report.get("status_reason") or "")
    for phrase in forbidden_phrases:
        for match in re.finditer(r"\b" + re.escape(phrase) + r"\b", text, re.IGNORECASE):
            start = match.start()
            prefix = text[:start].rstrip()
            if re.search(r"\b(not|no|non-)\s*$", prefix, re.IGNORECASE):
                continue
            errors.append(f"forbidden claim: {phrase}")

    return errors


def _determine_status(
    construction_tasks: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    self_test: bool,
    validation_errors: list[str] | None,
) -> tuple[str, str | None]:
    if validation_errors:
        return "blocked_safety", "P60 public report validation failed safety/contract checks."
    if self_test:
        return "self_test_only", "Self-test-only deterministic RMC policy comparison matrix; not quality evidence."
    if not labels:
        return "insufficient_records", "No per-task ephemeral records were available for P60."
    if not any(t.get("has_candidate_pool") for t in construction_tasks):
        return "insufficient_records", "Ephemeral records did not contain candidate pools required for P60."
    if any(t.get("has_candidate_pool") for t in construction_tasks):
        return "diagnostic_policy_matrix_available", "Aggregate diagnostic policy matrix available from gold-free RMC selections."
    return "diagnostic_policy_matrix_partial", "Partial policy matrix available."


def build_report(
    construction_tasks: list[dict[str, Any]],
    task_records: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    input_source_count: int,
    insufficient_input_source_count: int,
    optional_reports: dict[str, Any],
) -> dict[str, Any]:
    if len(construction_tasks) != len(task_records):
        raise ValueError("construction_tasks and task_records must be aligned")

    # RUN phase: freeze all policy selections from the gold-free construction view.
    policy_selections = _build_policy_selections(construction_tasks)

    # SCORE phase: only after selections are frozen, load labels from the original
    # raw records.
    labels = _extract_labels(task_records)

    if len(construction_tasks) != len(labels):
        raise ValueError("construction_tasks and labels must be aligned after extraction")

    candidate_pool_availability = (
        "available" if construction_tasks and all(t.get("has_candidate_pool") for t in construction_tasks)
        else "partial" if construction_tasks and any(t.get("has_candidate_pool") for t in construction_tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available" if labels and all(lab.get("has_gold_spans") for lab in labels if lab.get("has_gold"))
        else "partial" if labels and any(lab.get("has_gold_spans") for lab in labels if lab.get("has_gold"))
        else "missing_gold_spans"
    )
    reach_metrics_available = (
        candidate_pool_availability != "missing_candidate_pool"
        and gold_span_availability != "missing_gold_spans"
    )

    p31_h1_handoff_detected = bool(
        construction_tasks and any(
            t.get("has_candidate_pool") and lab.get("has_gold_spans")
            for t, lab in zip(construction_tasks, labels)
        )
    )
    p31_h1_handoff_detected_count = sum(
        1 for t, lab in zip(construction_tasks, labels)
        if t.get("has_candidate_pool") and lab.get("has_gold_spans")
    )
    p33b_handoff_detected = bool(construction_tasks and any(t.get("subtypes") for t in construction_tasks))
    p33b_handoff_detected_count = sum(1 for t in construction_tasks if t.get("subtypes"))

    by_policy: dict[str, Any] = {}
    for policy in POLICY_NAMES:
        by_policy[policy] = _compute_policy_metrics(
            policy_selections[policy], construction_tasks, labels, policy
        )

    status, reason = _determine_status(construction_tasks, labels, self_test, None)

    conclusion_lines: list[str] = []
    if status not in {"diagnostic_policy_matrix_available", "self_test_only"}:
        conclusion_lines.append(
            "P60 declares no winner and recommends no default policy."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only deterministic RMC policy matrix evaluated {len(labels)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P60 evaluated {len(labels)} real ephemeral P25 records and compared {len(POLICY_NAMES)} RMC next-action policies."
            )
        conclusion_lines.append(
            "Policy selection was gold-free and used only public task metadata, route features, and candidate metadata; labels were loaded only after selections were frozen."
        )
        conclusion_lines.append(
            "P60 does not call an LLM, does not create evidence, does not admit candidates, does not read source files, and does not recommend a default policy and declares no winner."
        )
        conclusion_lines.append(
            "P60 reports only aggregate next-action routing rates and SCORE-phase reach/false-cost diagnostics; all policies are treated as diagnostic alternatives, not promotion candidates."
        )
        for policy in POLICY_NAMES:
            m = by_policy[policy]
            conclusion_lines.append(
                f"{policy}: rmc_candidate_count={m['rmc_candidate_count']} "
                f"next_actions={dict(m['next_action_counts'])}."
            )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": True,
        "real_evaluation": bool(status == "diagnostic_policy_matrix_available" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": input_source_count,
        "insufficient_input_source_count": insufficient_input_source_count,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "rmc_not_evidence": True,
        "rmc_not_admission": True,
        "rmc_next_action_only": True,
        "policy_comparison_not_ranking": True,
        "run_phase_gold_free": True,
        "score_phase_only_metrics": True,
        "gold_used_for_policy_selection": False,
        "labels_loaded_after_policy_selection": True,
        "aggregate_only_public_artifact": True,
        "remote_calls_by_p60": 0,
        "llm_calls_by_p60": 0,
        "provider_config_read_by_p60": False,
        "prompt_construction_by_p60": False,
        "source_reads_attempted_by_p60": False,
        "expected_cost_latency_are_estimates": True,
        "cost_latency_measurements_taken_by_p60": False,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "private_labels_committed": False,
        "elapsed_ms": elapsed_ms,
        "task_count": len(labels),
        "positive_task_count": sum(1 for lab in labels if lab.get("has_gold")),
        "no_gold_task_count": sum(1 for lab in labels if not lab.get("has_gold")),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": p31_h1_handoff_detected_count,
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": p33b_handoff_detected_count,
        "comparison_frame": {
            "comparison_denominator_aligned": True,
            "same_input_records_for_all_policies": True,
            "policy_comparison_not_ranking": True,
            "no_winner_selected": True,
            "no_default_recommendation": True,
        },
        "upstream_carry_forward": optional_reports,
        "metrics": {"by_policy": by_policy},
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P60 public report validation failed: {errors}")
    return report


def _fmt_scalar(x: Any) -> str:
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, int):
        return str(x)
    if x is None:
        return "n/a"
    return str(x)


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P60: {report['remote_calls_by_p60']}",
        f"- LLM calls by P60: {report['llm_calls_by_p60']}",
        f"- Provider config read by P60: {report['provider_config_read_by_p60']}",
        f"- Prompt construction by P60: {report['prompt_construction_by_p60']}",
        f"- Source reads attempted by P60: {report['source_reads_attempted_by_p60']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- Reach metrics available: {report['reach_metrics_available']}",
        "",
    ])

    if report["status"] not in {"diagnostic_policy_matrix_available", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P60 advances the `request_more_context` (RMC) diagnostic from P47/P48 geometry/overlay into a comparable policy matrix. "
        "For the same frozen candidate/task inputs, each policy selects only the **next diagnostic action**. "
        "P60 reports aggregate routing counts, SCORE-phase gold-reach/false-cost diagnostics, and labeled cost/latency **estimates**. "
        "RMC is not evidence, not admission, and not a default; P60 declares no winner and recommends no default policy.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Build a RUN-phase gold-free construction view: strip `label`, `labels`, `p31_score_gold`, `gold`, `gold_spans`, `has_gold`, and `score_group` before normalization.",
        "- Freeze each policy's per-candidate next-action selection using only public task bucket, risk tags, allowlisted route features, and gold-free candidate/subtype metadata.",
        "- After all selections are frozen, load private labels only for the explicitly-marked `gold_reach_diagnostics` and `false_cost_diagnostics` blocks.",
        "- Output is aggregate-only: counts, rates, and cost/latency estimates by policy; no per-task/per-candidate rows; no winner or default recommendation.",
        "",
        "## Safety notes\n",
        "- P60 does not call an LLM or any remote provider.",
        "- P60 does not create evidence or admit candidates.",
        "- P60 does not read source files.",
        "- P60 does not read provider configuration.",
        "- P60 does not construct prompts or request envelopes.",
        "- P60 does not change defaults or recommend a promotion.",
        "- All cost/latency values are labeled estimates; P60 does not measure real provider spend or latency.",
        "",
    ])

    lines.append("## Policy comparison matrix\n")
    lines.append(
        "| Policy | Family | Availability | CandDenom | RMC_Cands | RMC_Rate | local_verifier | contrastive_pack | p51c_span_narrow | filter | weak_candidate_only |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for policy in POLICY_NAMES:
        m = report["metrics"]["by_policy"][policy]
        c = m["next_action_counts"]
        lines.append(
            f"| {policy} | {m['policy_family']} | `{m['availability']}` | {m['candidate_denominator']} | {m['rmc_candidate_count']} | "
            f"{_fmt_scalar(m['rmc_candidate_rate'])} | {c['local_verifier']} | {c['contrastive_pack']} | {c['p51c_span_narrow']} | {c['filter']} | {c['weak_candidate_only']} |"
        )
    lines.append("")

    lines.append("## Gold reach diagnostics (SCORE-phase only)\n")
    lines.append(
        "| Policy | PosDenom | GoldFileReach | GoldSpanOverlap | FileRightSpanWrong |"
    )
    lines.append("|---|---:|---:|---:|---:|")
    for policy in POLICY_NAMES:
        g = report["metrics"]["by_policy"][policy]["gold_reach_diagnostics"]
        lines.append(
            f"| {policy} | {g['positive_task_denominator']} | {g['gold_file_reach_count']} | {g['gold_span_overlap_reach_count']} | {g['file_right_span_wrong_count']} |"
        )
    lines.append("")

    lines.append("## False cost diagnostics (SCORE-phase only)\n")
    lines.append(
        "| Policy | NoGoldDenom | RMC_on_NoGold | FalseCost | FalseRate | FalsePerGoldReached |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for policy in POLICY_NAMES:
        f = report["metrics"]["by_policy"][policy]["false_cost_diagnostics"]
        lines.append(
            f"| {policy} | {f['no_gold_task_denominator']} | {f['rmc_on_no_gold_count']} | {f['false_cost_count']} | "
            f"{_fmt_scalar(f['false_cost_rate'])} | {_fmt_scalar(f['false_per_gold_reached'])} |"
        )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def make_self_test_records() -> list[dict[str, Any]]:
    """Deterministic synthetic ephemeral P25-policy records for P60 self-test."""
    def pool(
        items: list[tuple[str, int, int, str, dict[str, Any] | None]],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i, (path, start, end, kind, extra) in enumerate(items):
            row: dict[str, Any] = {
                "rank": i + 1,
                "path": path,
                "start_line": start,
                "end_line": end,
                "candidate_id": f"cid_{i+1}",
                "score": 0.9 - i * 0.05,
                "channels": ["candidate_baseline"],
            }
            if extra:
                row.update(extra)
            out.append(row)
        return out

    def gold(path: str, start: int, end: int) -> dict[str, Any]:
        return {"has_gold": True, "gold_spans": [{"path": path, "start_line": start, "end_line": end}]}

    def subtype(
        source_class: str,
        agreement_class: str,
        rrf_backing: bool,
    ) -> dict[str, Any]:
        return {
            "source_class": source_class,
            "agreement_class": agreement_class,
            "rank_bin": "top3",
            "candidate_count_bin": "small",
            "span_width_bin": "short",
            "rrf_backing": rrf_backing,
        }

    def subtypes(cids: list[str], subtype_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "candidate_id": cid,
                "rank": 1,
                **subtype_map[cid],
            }
            for cid in cids
        ]

    tasks: list[dict[str, Any]] = []

    # 1. Positive high-diagnostic span_overlap symbol_regex_fusion -> local_verifier / contrastive_pack.
    tasks.append({
        "task_id": "p60-st-001",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {"candidate_count": 3, "candidate_support_exists": True, "symbol_regex_agree_span": True, "local_anchor": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 10, 15, "source", {"channels": ["candidate_baseline", "symbol_regex_union"]}),
                ("src/other.py", 20, 25, "source", {"channels": ["rrf_primary"]}),
                ("tests/test_app.py", 1, 5, "test", {"channels": ["candidate_baseline"]}),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": subtypes(
            ["cid_1", "cid_2", "cid_3"],
            {
                "cid_1": subtype("symbol_regex_fusion", "span_overlap", True),
                "cid_2": subtype("symbol_regex_fusion", "span_overlap", True),
                "cid_3": subtype("symbol_only", "same_file_only", False),
            },
        ),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 2. Positive with span_overlap only -> p51c_span_narrow for rmc_span_overlap_only.
    tasks.append({
        "task_id": "p60-st-002",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["symbol_anchor"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True, "symbol_anchor": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 50, 55, "source", {"channels": ["symbol_primary"]}),
                ("src/app.py", 60, 65, "source", {"channels": ["regex_primary"]}),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 50, 55),
        "p33b_anchor_subtypes": subtypes(
            ["cid_1", "cid_2"],
            {
                "cid_1": subtype("symbol_only", "span_overlap", False),
                "cid_2": subtype("regex_only", "span_overlap", False),
            },
        ),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 3. Negative/dense -> filter.
    tasks.append({
        "task_id": "p60-st-003",
        "repo_id": "py_flask",
        "task_bucket": "negative",
        "task_risk_tags": ["dense_false_positive", "hard_distractor"],
        "score_group": "no_gold",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/noise.py", 1, 5, "source", None),
                ("node_modules/noise.py", 1, 5, "generated_or_vendor", None),
            ]),
        },
        "p31_score_gold": {"has_gold": False, "gold_spans": []},
        "p33b_anchor_subtypes": subtypes(
            ["cid_1", "cid_2"],
            {
                "cid_1": subtype("regex_only", "single_source", False),
                "cid_2": subtype("regex_only", "single_source", False),
            },
        ),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 4. Weak candidates -> weak_candidate_only.
    tasks.append({
        "task_id": "p60-st-004",
        "repo_id": "js_express",
        "task_bucket": "ambiguous",
        "task_risk_tags": ["weak_candidates"],
        "score_group": "no_gold",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.js", 1, 5, "source", None),
                ("src/other.js", 20, 25, "source", None),
            ]),
        },
        "p31_score_gold": {"has_gold": False, "gold_spans": []},
        "p33b_anchor_subtypes": subtypes(
            ["cid_1", "cid_2"],
            {
                "cid_1": subtype("symbol_only", "single_source", False),
                "cid_2": subtype("regex_only", "single_source", False),
            },
        ),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 5. Missing subtype handoff -> unavailable for subtype-dependent policies.
    tasks.append({
        "task_id": "p60-st-005",
        "repo_id": "js_express",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.js", 10, 15, "source", None),
                ("src/app.js", 100, 105, "source", None),
            ]),
        },
        "p31_score_gold": gold("src/app.js", 10, 15),
        "p33b_anchor_subtypes": [],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 6. Exact symbol / config bucket -> local_verifier.
    tasks.append({
        "task_id": "p60-st-006",
        "repo_id": "py_flask",
        "task_bucket": "exact_symbol",
        "task_risk_tags": ["exact_symbol_match"],
        "score_group": "positive",
        "route_features": {"candidate_count": 1, "candidate_support_exists": True, "exact_unique_symbol_anchor": True, "unique_symbol_anchor": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/config.py", 5, 10, "source", {"channels": ["symbol_primary"]}),
            ]),
        },
        "p31_score_gold": gold("src/config.py", 5, 10),
        "p33b_anchor_subtypes": subtypes(
            ["cid_1"],
            {"cid_1": subtype("symbol_only", "span_overlap", True)},
        ),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 7. No-gold task with contrastive pack -> false_cost diagnostic.
    tasks.append({
        "task_id": "p60-st-007",
        "repo_id": "js_express",
        "task_bucket": "ambiguous",
        "task_risk_tags": ["ambiguous"],
        "score_group": "no_gold",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/noise.js", 1, 5, "source", None),
                ("src/other.js", 20, 25, "source", None),
            ]),
        },
        "p31_score_gold": {"has_gold": False, "gold_spans": []},
        "p33b_anchor_subtypes": subtypes(
            ["cid_1", "cid_2"],
            {
                "cid_1": subtype("symbol_regex_fusion", "span_overlap", True),
                "cid_2": subtype("symbol_regex_fusion", "span_overlap", True),
            },
        ),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 8. Positive with source-backed verifier but not high diagnostic -> source_backed availability.
    tasks.append({
        "task_id": "p60-st-008",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True, "local_anchor": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 200, 205, "source", None),
                ("src/app.py", 210, 215, "source", None),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 200, 205),
        "p33b_anchor_subtypes": subtypes(
            ["cid_1", "cid_2"],
            {
                "cid_1": subtype("symbol_only", "same_file_only", True),
                "cid_2": subtype("symbol_only", "same_file_only", True),
            },
        ),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    return tasks


def _assert_self_test_invariants(report: dict[str, Any], records: list[dict[str, Any]]) -> None:
    """Self-test assertions: conservation, coverage, and leakage."""
    assert report["task_count"] >= 8, "self-test should cover at least 8 tasks"
    assert report["positive_task_count"] >= 4, "self-test should include positive tasks"
    assert report["no_gold_task_count"] >= 2, "self-test should include no-gold tasks"
    assert report["p33b_handoff_detected"] is True, "self-test should include P33-B handoff"

    by_policy = report["metrics"]["by_policy"]
    all_actions_seen: set[str] = set()
    for policy in POLICY_NAMES:
        m = by_policy[policy]
        counts = m["next_action_counts"]
        assert sum(counts.values()) == m["rmc_candidate_count"], f"{policy}: conservation failed"
        assert m["candidate_denominator"] >= m["rmc_candidate_count"], f"{policy}: denominator invariant failed"
        all_actions_seen.update(a for a, c in counts.items() if c > 0)
    assert all_actions_seen == ALLOWED_NEXT_ACTIONS, f"self-test must exercise all allowed next actions: missing {ALLOWED_NEXT_ACTIONS - all_actions_seen}"

    # At least one unavailable/missing-handoff path when the entire dataset lacks handoff.
    no_handoff_records = copy.deepcopy(records)
    for r in no_handoff_records:
        r["p33b_anchor_subtypes"] = []
    no_handoff_construction = _build_construction_tasks(no_handoff_records)
    no_handoff_selections = _build_policy_selections(no_handoff_construction)
    for policy in [
        "rmc_high_diagnostic_only",
        "rmc_span_overlap_only",
        "rmc_symbol_regex_fusion_only",
        "rmc_high_score_plus_contrast_pack",
        "rmc_high_score_plus_source_backed_verifier",
    ]:
        m = _compute_policy_metrics(no_handoff_selections[policy], no_handoff_construction, _extract_labels(no_handoff_records), policy)
        assert m["availability"] == "unavailable_missing_gold_free_handoff", f"{policy} should be unavailable when handoff is missing"

    # Leakage invariant: RUN selections must not change when labels are removed or shuffled.
    # We already built the report with labels removed during construction; re-run a shuffled
    # version to prove byte-identical RUN selections.
    shuffled = copy.deepcopy(records)
    labels = [r.get("p31_score_gold") for r in shuffled]
    import random
    rng = random.Random(42)
    rng.shuffle(labels)
    for r, lab in zip(shuffled, labels):
        r["p31_score_gold"] = lab
    construction_shuffled = _build_construction_tasks(shuffled)
    selections_shuffled = _build_policy_selections(construction_shuffled)
    construction_stripped = _build_construction_tasks(records)
    selections_stripped = _build_policy_selections(construction_stripped)
    for policy in POLICY_NAMES:
        assert selections_shuffled[policy] == selections_stripped[policy], f"{policy}: RUN selections differ with labels shuffled"


def main() -> int:
    parser = argparse.ArgumentParser(description="P60 RMC Policy v2 v0")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 aggregate report for status carry-forward.")
    parser.add_argument("--p59-report", type=Path, default=None, help="Optional P59 aggregate report for status carry-forward.")
    parser.add_argument("--p58-report", type=Path, default=None, help="Optional P58 aggregate report for status carry-forward.")
    parser.add_argument("--p51b-report", type=Path, default=None, help="Optional P51B aggregate report for status carry-forward.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 aggregate report for status carry-forward.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_records = make_self_test_records()
    elif args.input:
        input_paths = list(args.input)
        raw_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "diagnostic_policy_matrix_available"
    reason: str | None = None
    insufficient_count = 0
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P60.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P60 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_records"
            reason = marker_reasons[marker]
            insufficient_count += 1
            continue
        task_records.append(rec)

    if not task_records and status == "diagnostic_policy_matrix_available":
        status = "insufficient_records"
        reason = "No per-task records found."

    construction_tasks = _build_construction_tasks(task_records)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    optional_reports: dict[str, Any] = {}
    for name, path in [
        ("p48", args.p48_report),
        ("p59", args.p59_report),
        ("p58", args.p58_report),
        ("p51b", args.p51b_report),
        ("p50", args.p50_report),
    ]:
        optional_reports.update(_read_optional_report(path, name))

    report = build_report(
        construction_tasks,
        task_records,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        input_source_count=1 if args.self_test else max(1, len(args.input or [])),
        insufficient_input_source_count=insufficient_count,
        optional_reports=optional_reports,
    )

    if args.self_test:
        _assert_self_test_invariants(report, task_records)

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P60 report written to {args.out}")
    print(f"P60 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
