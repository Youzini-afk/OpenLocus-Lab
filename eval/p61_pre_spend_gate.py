#!/usr/bin/env python3
"""P61 Pre-Spend Gate v0.

P61 is a deterministic, no-live-LLM, no-provider, aggregate-only readiness gate
that consumes ONLY existing aggregate reports (P57, P58, P59, P60, P51-B required;
P52C optional) and emits a precondition-readiness decision about whether a FUTURE
P51-C live LLM micro-run is worth considering.

P61 NEVER calls providers, NEVER constructs prompts, NEVER reads source/ephemeral
records, NEVER admits Evidence, NEVER changes defaults, NEVER promotes, NEVER
authorizes provider spend. It only reports preconditions; opening a live run stays
a separate explicit workflow_dispatch/human decision.

Hard constraints:
* NOT quality evidence, NOT authorization, NOT live-readiness, NOT promotion.
* No remote/LLM/provider calls.
* No prompt construction, no source reads, no provider config reads.
* Aggregate-only public artifact; no per-task/per-candidate rows.
* Only reads aggregate JSON reports from the listed upstream phases.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "p61-pre-spend-gate-v0"
GENERATED_BY = "p61_pre_spend_gate"
STAGE = "P61 Pre-Spend Gate v0"

DEFAULT_OUT = Path("artifacts/p61_pre_spend_gate/p61_pre_spend_gate_report.json")
DEFAULT_DOC = Path("docs/en/p61-pre-spend-gate.md")

REQUIRED_PHASES = ["p57", "p58", "p59", "p60", "p51b"]
OPTIONAL_PHASES = ["p52c"]

ALLOWED_STATUS = {
    "micro_run_preconditions_met",
    "blocked_missing_actionability",
    "insufficient_inputs",
    "blocked_safety",
    "self_test_only",
}

PHASE_ALLOWED_STATUS = {
    "p57": {
        "diagnostic_matrix_complete",
        "diagnostic_matrix_unstable",
        "insufficient_matrix",
        "blocked_safety",
    },
    "p58": {
        "diagnostic_calibration_available",
        "diagnostic_calibration_partial",
        "diagnostic_calibration_unavailable",
        "insufficient_upstream",
        "blocked_safety",
        "self_test_only",
    },
    "p59": {
        "diagnostic_coverage_available",
        "diagnostic_coverage_partial",
        "insufficient_records",
        "blocked_safety",
        "self_test_only",
    },
    "p60": {
        "diagnostic_policy_matrix_available",
        "diagnostic_policy_matrix_partial",
        "insufficient_records",
        "blocked_safety",
        "self_test_only",
    },
    "p51b": {"ok", "self_test_only", "insufficient_task_detail", "blocked_safety"},
    "p52c": {"ok", "self_test_only", "insufficient_task_detail", "blocked_safety"},
}

# Keys that must never appear in the public artifact.
FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "candidate_id",
    "repo_id",
    "dataset",
    "path",
    "start_line",
    "end_line",
    "span",
    "content_sha",
    "digest",
    "hash",
    "gold",
    "gold_spans",
    "private_label",
    "private_labels",
    "label",
    "labels",
    "query",
    "raw_query",
    "snippet",
    "source_text",
    "raw_source",
    "prompt",
    "response",
    "output",
    "raw_output",
    "provider",
    "model",
    "base_url",
    "api_key",
    "api_token",
    "provider_key",
    "endpoint",
    "repo_lock",
    "repo_lock_path",
    "source_root",
    "corpus_root",
    "tasks",
    "records",
    "per_task",
    "per_task_results",
    "per_candidate",
    "per_candidate_results",
    "per_slice_rows",
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
    "request_payload",
    "request_envelope",
    "raw_request_envelope",
    "raw_request_envelopes",
}

# Keys that are intentionally public safety flags or aggregate-only metric names.
P61_SAFETY_FLAG_KEYS = {
    # schema
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    "not_quality_evidence",
    "precondition_report_only",
    "micro_run_not_authorized",
    "provider_spend_authorized",
    "workflow_dispatch_required_for_live_run",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "evidence_admission_performed",
    "aggregate_only_public_artifact",
    "p61_uses_no_score_phase",
    "gold_used_by_p61",
    "remote_calls_by_p61",
    "llm_calls_by_p61",
    "remote_requests_by_p61",
    "provider_config_read_by_p61",
    "prompt_construction_by_p61",
    "source_reads_attempted_by_p61",
    "raw_text_stored",
    "raw_source_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_query_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
    "elapsed_ms",
    # blocks
    "input_summary",
    "upstream_safety_summary",
    "decision_inputs",
    "readiness_decision",
    "upstream_status_summary",
    "warnings",
    "blockers",
    "conclusion",
    "validation",
    # input_summary
    "required_reports",
    "optional_reports",
    "required_present_count",
    "optional_present_count",
    "required_missing",
    "invalid_json_count",
    "upstream_status_by_phase",
    "upstream_safety_blocked_count",
    # upstream_safety_summary / upstream_status_summary
    "by_phase",
    "report_present",
    "status",
    "safety_blocker",
    "safety_warnings",
    # decision_inputs
    "p57_matrix_complete",
    "p57_required_slice_count_met",
    "p58_calibration_available",
    "p59_actionability_bucket",
    "p59_actionability_precondition_met",
    "p60_p51c_route_available",
    "p60_llm_eligible_route_available",
    "p60_policy_count_with_p51c_route",
    "p60_policy_count_with_llm_eligible_route",
    "p60_routing_is_precondition_only",
    "p51b_contract_precondition_met",
    "p51b_eligibility_is_precondition_only",
    "p51b_budget_violation_absent",
    "p51b_redaction_required_absent",
    "p51b_schema_validation_precondition_met",
    "p52c_optional_score_availability",
    "p52c_optional_present",
    # readiness_decision
    "decision",
    "decision_is_authorization",
    "provider_spend_authorized",
    "requires_separate_human_or_workflow_dispatch",
    "reasons",
    # common helpers
    "count",
    "rate",
    "value",
    "availability",
    "bucket",
    "precondition_only",
    "true",
    "false",
}

RAW_FLAGS = [
    "raw_text_stored",
    "raw_source_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_query_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
]

COMMON_FLAGS = {
    "promotion_ready": False,
    "default_should_change": False,
    "evidencecore_semantics_changed": False,
    "candidate_not_fact": True,
    "aggregate_only_public_artifact": True,
}

PHASE_SAFETY = {
    "p57": {
        "remote": "remote_calls_by_p57",
        "llm": "llm_calls_by_p57",
        "prompt": "prompt_construction_by_p57",
        "source_reads": "source_reads_attempted_by_p57",
        "extra": {},
    },
    "p58": {
        "remote": "remote_calls_by_p58",
        "llm": "llm_calls_by_p58",
        "prompt": "prompt_construction_by_p58",
        "source_reads": "source_reads_attempted_by_p58",
        "extra": {"remote_requests_by_p58": 0, "action_hints_not_admission": True},
    },
    "p59": {
        "remote": "remote_calls_by_p59",
        "llm": "llm_calls_by_p59",
        "prompt": "prompt_construction_by_p59",
        "source_reads": "source_reads_attempted_by_p59",
        "extra": {
            "run_phase_gold_free": True,
            "gold_used_for_pack_construction": False,
        },
    },
    "p60": {
        "remote": "remote_calls_by_p60",
        "llm": "llm_calls_by_p60",
        "prompt": "prompt_construction_by_p60",
        "source_reads": "source_reads_attempted_by_p60",
        "extra": {
            "rmc_not_evidence": True,
            "rmc_not_admission": True,
            "rmc_next_action_only": True,
            "policy_comparison_not_ranking": True,
            "expected_cost_latency_are_estimates": True,
            "run_phase_gold_free": True,
            "gold_used_for_policy_selection": False,
        },
    },
    "p51b": {
        "remote": "remote_calls_by_p51b",
        "llm": "llm_calls_by_p51b",
        "prompt": "prompt_construction_by_p51b",
        "extra": {
            "remote_requests_by_p51b": 0,
            "dry_run_payload_validation_only": True,
            "p51b_live_calls_disabled": True,
            "contract_not_quality_evidence": True,
        },
    },
    "p52c": {
        "remote": "remote_calls_by_p52c",
        "llm": "llm_calls_by_p52c",
        "prompt": "prompt_construction_by_p52c",
        "source_reads": "source_reads_attempted_by_p52c",
        "source_bounded": "source_reads_bounded_by_p52c",
        "extra": {},
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_path(data: Any, path: list[str]) -> Any:
    value = data
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def _safe_status(data: dict[str, Any] | None, phase: str) -> str:
    if data is None:
        return "not_provided"
    if data.get("_invalid_json"):
        return "invalid_json"
    if data.get("_aggregate_contract_violation"):
        return "aggregate_contract_violation"
    status = data.get("status")
    allowed = PHASE_ALLOWED_STATUS.get(phase, set())
    if isinstance(status, str) and status in allowed:
        return status
    return "unrecognized_status"


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P61_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _scan_values_for_leaks_minimal(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            violations.extend(_scan_values_for_leaks_minimal(value, prefix + str(key) + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_values_for_leaks_minimal(value, prefix + str(idx) + "."))
    elif isinstance(obj, str):
        text = obj.strip()
        if len(text) > 1 and (text.startswith("/") or text.startswith("\\")):
            violations.append(prefix + " looks like an absolute path")
        elif "://" in text:
            violations.append(prefix + " looks like a URL")
        elif re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
            violations.append(prefix + " looks like an API key")
    return violations


def _scan_values_for_leaks(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            violations.extend(_scan_values_for_leaks(value, prefix + str(key) + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_values_for_leaks(value, prefix + str(idx) + "."))
    elif isinstance(obj, str):
        text = obj.strip()
        if not text:
            return violations
        # Absolute path
        if len(text) > 1 and (text.startswith("/") or text.startswith("\\")):
            violations.append(prefix + " looks like an absolute path")
            return violations
        # URL
        if "://" in text:
            violations.append(prefix + " looks like a URL")
            return violations
        # API key
        if re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
            violations.append(prefix + " looks like an API key")
            return violations
        # Relative path-like strings
        if (
            text.startswith("./")
            or text.startswith("../")
            or text.startswith("artifacts/")
            or text.startswith("docs/")
            or text.startswith("eval/")
            or text.startswith("src/")
        ):
            violations.append(prefix + " looks like a relative path")
            return violations
        # Path-ish with file extension
        if "/" in text:
            for segment in text.split("/"):
                if re.search(r"\.[A-Za-z0-9]{1,6}$", segment):
                    violations.append(prefix + " looks like a path with file extension")
                    return violations
        # Hex digest/hash-like
        if re.fullmatch(r"[0-9a-fA-F]{32,}", text):
            violations.append(prefix + " looks like a hex digest")
            return violations
        # Long opaque string without spaces
        if len(text) > 200 and " " not in text:
            violations.append(prefix + " looks like a long opaque string")
            return violations
    return violations


def _read_aggregate_report(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_invalid_json": True, "status": "invalid_json"}
    if not isinstance(data, dict):
        return {"_invalid_json": True, "status": "invalid_json"}
    key_violations = _reject_forbidden_keys(data)
    value_violations = _scan_values_for_leaks_minimal(data)
    if key_violations or value_violations:
        return {
            "_aggregate_contract_violation": True,
            "status": "aggregate_contract_violation",
        }
    return data


def _load_reports_from_args(args: argparse.Namespace) -> dict[str, dict[str, Any] | None]:
    reports: dict[str, dict[str, Any] | None] = {}
    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        path = getattr(args, f"{phase}_report", None)
        reports[phase] = _read_aggregate_report(path)
    return reports


def _verify_upstream_safety(phase: str, data: dict[str, Any] | None, *, required: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "report_present": data is not None and not data.get("_invalid_json"),
        "status": _safe_status(data, phase),
        "safety_blocker": False,
        "safety_warnings": [],
    }
    if data is None or data.get("_invalid_json"):
        result["safety_warnings"].append("report_missing_or_invalid")
        return result
    if data.get("_aggregate_contract_violation"):
        result["safety_blocker"] = True
        result["safety_warnings"].append("aggregate_only_input_contract_violation")
        return result

    # Common top-level safety flags.
    for flag, expected in COMMON_FLAGS.items():
        if flag in data:
            if data[flag] is not expected:
                result["safety_blocker"] = True
                result["safety_warnings"].append(f"{flag}_violation")
        else:
            if required:
                result["safety_blocker"] = True
            result["safety_warnings"].append(f"missing_{flag}")

    # Raw/private content flags must be False if present.
    for flag in RAW_FLAGS:
        if flag in data and data[flag] is not False:
            result["safety_blocker"] = True
            result["safety_warnings"].append(f"{flag}_violation")

    cfg = PHASE_SAFETY.get(phase, {})

    def _check_bool(key: str | None, expected: Any, label: str, blocker: bool) -> None:
        if key is None:
            return
        if key in data:
            if data[key] is not expected:
                if blocker:
                    result["safety_blocker"] = True
                    result["safety_warnings"].append(f"{label}_violation")
                else:
                    result["safety_warnings"].append(f"{label}_unexpected")
        else:
            if required:
                result["safety_blocker"] = True
            result["safety_warnings"].append(f"missing_{label}")

    _check_bool(cfg.get("remote"), 0, "remote_calls_zero", blocker=True)
    _check_bool(cfg.get("llm"), 0, "llm_calls_zero", blocker=True)
    _check_bool(cfg.get("prompt"), False, "prompt_construction_false", blocker=True)

    source_reads_key = cfg.get("source_reads")
    source_bounded_key = cfg.get("source_bounded")
    if source_reads_key:
        if source_bounded_key:
            # Source-read phases must attempt and be bounded.
            attempted = data.get(source_reads_key)
            bounded = data.get(source_bounded_key)
            if attempted is not True:
                if required:
                    result["safety_blocker"] = True
                result["safety_warnings"].append("source_reads_not_attempted")
            if bounded is not True:
                result["safety_blocker"] = True
                result["safety_warnings"].append("source_reads_not_bounded")
        else:
            # Non-source-read phases must not attempt source reads.
            _check_bool(source_reads_key, False, "source_reads_not_attempted", blocker=True)

    for key, expected in cfg.get("extra", {}).items():
        if key in data:
            if data[key] != expected:
                result["safety_blocker"] = True
                result["safety_warnings"].append(f"{key}_violation")
        else:
            if required:
                result["safety_blocker"] = True
            result["safety_warnings"].append(f"missing_{key}")

    return result


def _input_summary(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    required_present = 0
    optional_present = 0
    required_missing: list[str] = []
    invalid_json_count = 0
    upstream_status_by_phase: dict[str, str] = {}

    for phase in REQUIRED_PHASES:
        data = reports.get(phase)
        present = data is not None and not data.get("_invalid_json")
        if present:
            required_present += 1
        else:
            required_missing.append(phase)
        if data and data.get("_invalid_json"):
            invalid_json_count += 1
        if data and data.get("_aggregate_contract_violation"):
            invalid_json_count += 1
        upstream_status_by_phase[phase] = _safe_status(data, phase)

    for phase in OPTIONAL_PHASES:
        data = reports.get(phase)
        if data is not None and not data.get("_invalid_json"):
            optional_present += 1
        if data and data.get("_invalid_json"):
            invalid_json_count += 1
        if data and data.get("_aggregate_contract_violation"):
            invalid_json_count += 1
        upstream_status_by_phase[phase] = _safe_status(data, phase)

    return {
        "required_reports": list(REQUIRED_PHASES),
        "optional_reports": list(OPTIONAL_PHASES),
        "required_present_count": required_present,
        "optional_present_count": optional_present,
        "required_missing": required_missing,
        "invalid_json_count": invalid_json_count,
        "upstream_status_by_phase": upstream_status_by_phase,
    }


def _upstream_safety_summary(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    by_phase: dict[str, Any] = {}
    blocker_count = 0
    warning_count = 0
    checked = 0

    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        data = reports.get(phase)
        if data is not None and not data.get("_invalid_json"):
            checked += 1
        required = (phase in REQUIRED_PHASES) or (phase == "p52c" and data is not None)
        v = _verify_upstream_safety(phase, data, required=required)
        by_phase[phase] = v
        if v["safety_blocker"]:
            blocker_count += 1
        warning_count += len(v["safety_warnings"])

    return {
        "checked_phase_count": checked,
        "safety_blocker_count": blocker_count,
        "safety_warning_count": warning_count,
        "by_phase": by_phase,
    }


def _upstream_status_summary(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    return {
        "collapsed_status_by_phase": {
            phase: _safe_status(reports.get(phase), phase)
            for phase in REQUIRED_PHASES + OPTIONAL_PHASES
        }
    }


def _p57_slice_count(reports: dict[str, dict[str, Any] | None]) -> tuple[int | None, int | None]:
    p57 = reports.get("p57") or {}
    summary = p57.get("input_summary") or {}
    slice_count = _as_int(summary.get("slice_count"))
    included = _as_int(summary.get("included_generalization_slice_count"))
    return slice_count, included


ALLOWED_ACTIONABILITY_BUCKETS = {
    "actionable",
    "partial",
    "blocked_missing_gold_candidate",
    "blocked_missing_hard_distractor",
    "blocked_missing_both",
    "insufficient_denominator",
}


def _p59_actionability_bucket_raw(reports: dict[str, dict[str, Any] | None]) -> str | None:
    p59 = reports.get("p59") or {}
    by_strategy = _get_path(p59, ["metrics", "by_strategy"]) or {}
    strategy = by_strategy.get("anchor_contrast_pack_v0") or {}
    cf = strategy.get("counterfactual_actionability") or {}
    bucket = cf.get("llm_spend_actionability_bucket")
    return bucket if isinstance(bucket, str) else None


def _p59_actionability_bucket(reports: dict[str, dict[str, Any] | None]) -> str:
    raw = _p59_actionability_bucket_raw(reports)
    if raw is None:
        return "unrecognized_bucket"
    if raw in ALLOWED_ACTIONABILITY_BUCKETS:
        return raw
    return "unrecognized_bucket"


def _p60_policy_routing(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p60 = reports.get("p60") or {}
    by_policy = _get_path(p60, ["metrics", "by_policy"]) or {}
    p51c_count = 0
    llm_eligible_count = 0
    p51c_policies: list[str] = []
    llm_eligible_policies: list[str] = []

    for policy_name, block in by_policy.items():
        if not isinstance(block, dict):
            continue
        nac = block.get("next_action_counts") or {}
        if _as_int(nac.get("p51c_span_narrow", 0)) and _as_int(nac.get("p51c_span_narrow", 0)) > 0:
            p51c_count += 1
            p51c_policies.append(policy_name)
        elig = block.get("rmc_to_llm_eligibility") or {}
        if _as_int(elig.get("eligible_count", 0)) and _as_int(elig.get("eligible_count", 0)) > 0:
            llm_eligible_count += 1
            llm_eligible_policies.append(policy_name)

    comparison = p60.get("comparison_frame") or {}
    return {
        "p60_p51c_route_available": p51c_count > 0,
        "p60_llm_eligible_route_available": llm_eligible_count > 0,
        "p60_policy_count_with_p51c_route": p51c_count,
        "p60_policy_count_with_llm_eligible_route": llm_eligible_count,
        "p60_routing_is_precondition_only": bool(
            comparison.get("no_winner_selected")
            and comparison.get("no_default_recommendation")
            and comparison.get("policy_comparison_not_ranking")
        ),
    }


def _p51b_contract_readiness(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p51b = reports.get("p51b") or {}
    metrics = p51b.get("metrics") or {}

    gate = metrics.get("future_live_gate_readiness") or {}
    live_ready = bool(gate.get("p51b_live_gate_ready"))
    reason = gate.get("p51b_live_gate_ready_reason")

    elig = metrics.get("eligibility") or {}
    eligible_candidate_count = _as_int(elig.get("eligible_candidate_count"))
    eligible_pack_count = _as_int(elig.get("eligible_pack_count"))
    eligibility_availability = elig.get("eligibility_availability")
    source_backed_live = bool(elig.get("source_backed_live_eligibility_available"))

    blueprint = metrics.get("request_envelope_blueprint") or {}
    blueprint_count = _as_int(blueprint.get("request_envelope_blueprint_count"))
    budget_violation_rate = _as_float(blueprint.get("max_budget_violation_rate"))
    redaction_rate = _as_float(blueprint.get("redaction_required_rate"))

    schema = metrics.get("role_output_schema_validation") or {}
    valid_rate = _as_float(schema.get("role_output_schema_valid_rate"))

    contract_precondition = (
        live_ready
        and reason == "contract_valid_dry_run_only"
        and eligible_candidate_count is not None and eligible_candidate_count > 0
        and eligible_pack_count is not None and eligible_pack_count > 0
        and blueprint_count is not None and blueprint_count > 0
        and eligibility_availability == "available_source_backed"
        and source_backed_live
        and valid_rate == 1.0
    )

    budget_violation_absent = budget_violation_rate in {0, 0.0, None}
    redaction_absent = redaction_rate in {0, 0.0, None}

    return {
        "p51b_contract_precondition_met": contract_precondition,
        "p51b_eligibility_is_precondition_only": True,
        "p51b_live_gate_ready": live_ready,
        "p51b_live_gate_ready_reason": reason,
        "p51b_eligible_candidate_count": eligible_candidate_count,
        "p51b_eligible_pack_count": eligible_pack_count,
        "p51b_request_envelope_blueprint_count": blueprint_count,
        "p51b_eligibility_availability": eligibility_availability,
        "p51b_source_backed_live_eligibility_available": source_backed_live,
        "p51b_role_output_schema_valid_rate": valid_rate,
        "p51b_budget_violation_absent": budget_violation_absent,
        "p51b_redaction_required_absent": redaction_absent,
        "p51b_schema_validation_precondition_met": valid_rate == 1.0,
    }


def _p52c_optional_summary(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p52c = reports.get("p52c")
    if p52c is None or p52c.get("_invalid_json"):
        return {
            "p52c_optional_present": False,
            "p52c_optional_score_availability": "not_provided",
        }
    sa = _get_path(p52c, ["metrics", "score_availability"]) or {}
    return {
        "p52c_optional_present": True,
        "p52c_optional_score_availability": sa.get("p52c_score_availability") or "not_provided",
    }


def compute_status(reports: dict[str, dict[str, Any] | None]) -> tuple[str, list[str], dict[str, Any]]:
    """Return (status, reasons, decision_inputs) from the readiness algorithm.

    This helper is public so the self-test can assert on it directly.
    """
    reasons: list[str] = []
    inputs: dict[str, Any] = {}

    input_summary = _input_summary(reports)
    safety_summary = _upstream_safety_summary(reports)

    # 1) missing/invalid required reports
    if input_summary.get("required_missing") or input_summary.get("invalid_json_count", 0) > 0:
        if input_summary.get("required_missing"):
            for phase in input_summary["required_missing"]:
                reasons.append(f"missing_required_report:{phase}")
        if input_summary.get("invalid_json_count", 0) > 0:
            for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
                data = reports.get(phase)
                if data and (data.get("_invalid_json") or data.get("_aggregate_contract_violation")):
                    reasons.append(f"invalid_json:{phase}")
        inputs.update({
            "p57_matrix_complete": False,
            "p57_required_slice_count_met": False,
            "p58_calibration_available": False,
            "p59_actionability_bucket": "not_provided",
            "p59_actionability_precondition_met": False,
            "p60_p51c_route_available": False,
            "p60_llm_eligible_route_available": False,
            "p60_policy_count_with_p51c_route": 0,
            "p60_policy_count_with_llm_eligible_route": 0,
            "p60_routing_is_precondition_only": True,
            "p51b_contract_precondition_met": False,
            "p51b_eligibility_is_precondition_only": True,
            "p51b_budget_violation_absent": False,
            "p51b_redaction_required_absent": False,
            "p51b_schema_validation_precondition_met": False,
        })
        inputs.update(_p52c_optional_summary(reports))
        return "insufficient_inputs", reasons, inputs

    # 2) upstream aggregate/public contract violation
    if safety_summary.get("safety_blocker_count", 0) > 0:
        for phase, v in safety_summary.get("by_phase", {}).items():
            if v.get("safety_blocker"):
                reasons.append(f"upstream_safety_blocker:{phase}")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_safety", reasons, inputs

    # 3) any required upstream status == blocked_safety
    status_summary = _upstream_status_summary(reports)
    for phase in REQUIRED_PHASES:
        if status_summary["collapsed_status_by_phase"].get(phase) == "blocked_safety":
            reasons.append(f"upstream_blocked_safety:{phase}")
    if reasons:
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_safety", reasons, inputs

    # 4) any required report self_test
    for phase in REQUIRED_PHASES:
        data = reports.get(phase)
        if data and data.get("self_test") is True:
            reasons.append(f"upstream_self_test:{phase}")
    if reasons:
        inputs = _build_decision_inputs(reports, safety_summary)
        return "insufficient_inputs", reasons, inputs

    # 5) P57
    p57_status = status_summary["collapsed_status_by_phase"].get("p57")
    p57_slice_count, p57_included = _p57_slice_count(reports)
    p57_slice_met = (
        p57_slice_count is not None and p57_slice_count >= 4
        and p57_included is not None and p57_included >= 4
    )
    if p57_status != "diagnostic_matrix_complete" or not p57_slice_met:
        if p57_status != "diagnostic_matrix_complete":
            reasons.append("p57_matrix_not_complete")
        if not p57_slice_met:
            reasons.append("single_slice_or_insufficient_matrix:p57")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "insufficient_inputs", reasons, inputs

    # 6) P58
    if status_summary["collapsed_status_by_phase"].get("p58") != "diagnostic_calibration_available":
        reasons.append("p58_calibration_not_available")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_missing_actionability", reasons, inputs

    # 7) P59
    if status_summary["collapsed_status_by_phase"].get("p59") != "diagnostic_coverage_available":
        reasons.append("p59_coverage_not_available")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_missing_actionability", reasons, inputs

    p59_bucket = _p59_actionability_bucket(reports)
    p59_bucket_raw = _p59_actionability_bucket_raw(reports)
    if p59_bucket_raw is None:
        reasons.append("p59_actionability_bucket_missing")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "insufficient_inputs", reasons, inputs
    if p59_bucket != "actionable":
        reasons.append("p59_actionability_not_actionable")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_missing_actionability", reasons, inputs

    # 8) P60
    if status_summary["collapsed_status_by_phase"].get("p60") != "diagnostic_policy_matrix_available":
        reasons.append("p60_policy_matrix_not_available")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_missing_actionability", reasons, inputs

    p60 = reports.get("p60") or {}
    comparison = p60.get("comparison_frame") or {}
    p60_precondition_only = bool(
        comparison.get("no_winner_selected")
        and comparison.get("no_default_recommendation")
        and comparison.get("policy_comparison_not_ranking")
    )
    routing = _p60_policy_routing(reports)
    if not p60_precondition_only:
        reasons.append("p60_comparison_frame_not_precondition_only")
    # rmc_not_evidence/rmc_not_admission/rmc_next_action_only are already checked
    # in safety; if they are missing here it is a safety issue, but we additionally
    # require them as precondition flags.
    for flag in ("rmc_not_evidence", "rmc_not_admission", "rmc_next_action_only"):
        if p60.get(flag) is not True:
            reasons.append(f"p60_{flag}_false")
    if not routing["p60_p51c_route_available"] and not routing["p60_llm_eligible_route_available"]:
        reasons.append("p60_no_p51c_or_llm_eligible_route")
    if reasons:
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_missing_actionability", reasons, inputs

    # 9) P51B
    p51b_status = status_summary["collapsed_status_by_phase"].get("p51b")
    if p51b_status != "ok":
        reasons.append(f"p51b_status_not_ok:{p51b_status}")
        inputs = _build_decision_inputs(reports, safety_summary)
        return "insufficient_inputs", reasons, inputs

    p51b = _p51b_contract_readiness(reports)
    if not p51b["p51b_contract_precondition_met"]:
        reasons.append("p51b_contract_precondition_unmet")
    if not p51b["p51b_budget_violation_absent"]:
        reasons.append("p51b_budget_violation")
    if not p51b["p51b_redaction_required_absent"]:
        reasons.append("p51b_redaction_required")
    if not p51b["p51b_schema_validation_precondition_met"]:
        reasons.append("p51b_schema_validation_failed")
    if reasons:
        inputs = _build_decision_inputs(reports, safety_summary)
        return "blocked_missing_actionability", reasons, inputs

    # 10) optional P52C safety already folded into safety_summary; if present and
    # unsafe we would have already returned blocked_safety. If present and safe,
    # it is a positive signal.
    p52c_summary = _p52c_optional_summary(reports)
    if p52c_summary["p52c_optional_present"]:
        p52c_data = reports.get("p52c")
        if p52c_data and p52c_data.get("status") in {"blocked_safety", "insufficient_task_detail"}:
            # Safe but not actionable; warn, not block.
            pass

    inputs = _build_decision_inputs(reports, safety_summary)
    return "micro_run_preconditions_met", ["all_required_preconditions_present"], inputs


def _build_decision_inputs(reports: dict[str, dict[str, Any] | None], safety_summary: dict[str, Any]) -> dict[str, Any]:
    status_summary = _upstream_status_summary(reports)
    p57_status = status_summary["collapsed_status_by_phase"].get("p57")
    p58_status = status_summary["collapsed_status_by_phase"].get("p58")
    p59_status = status_summary["collapsed_status_by_phase"].get("p59")
    p60_status = status_summary["collapsed_status_by_phase"].get("p60")
    p51b_status = status_summary["collapsed_status_by_phase"].get("p51b")

    p57_slice_count, p57_included = _p57_slice_count(reports)
    p57_slice_met = (
        p57_slice_count is not None and p57_slice_count >= 4
        and p57_included is not None and p57_included >= 4
    )

    p59_bucket = _p59_actionability_bucket(reports)
    p59_actionable = p59_bucket == "actionable"

    p60 = reports.get("p60") or {}
    comparison = p60.get("comparison_frame") or {}
    p60_precondition_only = bool(
        comparison.get("no_winner_selected")
        and comparison.get("no_default_recommendation")
        and comparison.get("policy_comparison_not_ranking")
    )
    routing = _p60_policy_routing(reports)

    p51b = _p51b_contract_readiness(reports)
    p52c_summary = _p52c_optional_summary(reports)

    return {
        "p57_matrix_complete": p57_status == "diagnostic_matrix_complete",
        "p57_required_slice_count_met": p57_slice_met,
        "p58_calibration_available": p58_status == "diagnostic_calibration_available",
        "p59_actionability_bucket": p59_bucket or "not_provided",
        "p59_actionability_precondition_met": p59_actionable,
        "p60_p51c_route_available": routing["p60_p51c_route_available"],
        "p60_llm_eligible_route_available": routing["p60_llm_eligible_route_available"],
        "p60_policy_count_with_p51c_route": routing["p60_policy_count_with_p51c_route"],
        "p60_policy_count_with_llm_eligible_route": routing["p60_policy_count_with_llm_eligible_route"],
        "p60_routing_is_precondition_only": p60_precondition_only,
        "p51b_contract_precondition_met": p51b["p51b_contract_precondition_met"],
        "p51b_eligibility_is_precondition_only": p51b["p51b_eligibility_is_precondition_only"],
        "p51b_budget_violation_absent": p51b["p51b_budget_violation_absent"],
        "p51b_redaction_required_absent": p51b["p51b_redaction_required_absent"],
        "p51b_schema_validation_precondition_met": p51b["p51b_schema_validation_precondition_met"],
        "p52c_optional_score_availability": p52c_summary["p52c_optional_score_availability"],
        "p52c_optional_present": p52c_summary["p52c_optional_present"],
    }


def _build_report(
    reports: dict[str, dict[str, Any] | None],
    *,
    self_test: bool,
    elapsed_ms: int,
) -> dict[str, Any]:
    input_summary = _input_summary(reports)
    safety_summary = _upstream_safety_summary(reports)
    status_summary = _upstream_status_summary(reports)

    if self_test:
        status = "self_test_only"
        status_reason = "Self-test-only aggregate precondition readiness; not quality evidence and not authorization."
        decision_reasons = ["self_test_only"]
    else:
        status, decision_reasons, _ = compute_status(reports)
        status_reason = "; ".join(decision_reasons) if decision_reasons else "precondition evaluation complete"

    _, _, decision_inputs = compute_status(reports)

    warnings: list[str] = []
    blockers: list[str] = []

    for phase in input_summary.get("required_missing", []):
        blockers.append(f"Required upstream aggregate report {phase} missing or unreadable.")
    if input_summary.get("invalid_json_count", 0) > 0:
        warnings.append(f"Invalid JSON or contract-violating upstream reports: {input_summary['invalid_json_count']}.")

    for phase, v in safety_summary.get("by_phase", {}).items():
        if v.get("safety_blocker"):
            blockers.append(f"Upstream safety flag violations in phase {phase}.")
        for w in v.get("safety_warnings", []):
            warnings.append(f"{phase}: {w}")

    for phase in OPTIONAL_PHASES:
        data = reports.get(phase)
        if data is None or data.get("_invalid_json"):
            warnings.append(f"Optional upstream report {phase} not provided or invalid.")
        elif data.get("self_test") is True:
            warnings.append(f"Optional upstream report {phase} is self_test_only.")

    if status == "micro_run_preconditions_met" and not self_test:
        warnings.append(
            "Preconditions are met for *consideration* of a future P51-C live LLM micro-run. "
            "This is not authorization; a separate workflow_dispatch or human decision is required."
        )
    elif status == "blocked_missing_actionability":
        warnings.append("Upstream reports are present and safe, but actionability preconditions for a P51-C live run are not met.")
    elif status == "insufficient_inputs":
        warnings.append("Required upstream aggregate reports are missing, invalid, self-test-only, or P57 generalization is insufficient.")
    elif status == "blocked_safety":
        warnings.append("Upstream safety flag violations prevent P61 from declaring any readiness.")

    conclusion: list[str] = [
        "P61 Pre-Spend Gate v0 is a deterministic, aggregate-only precondition-readiness report.",
        "P61 does not call providers, does not construct prompts, and does not read source or ephemeral records.",
        "P61 is not quality evidence, not Evidence, not authorization, not promotion, and not live-readiness.",
        "A future P51-C live LLM micro-run remains a separate explicit workflow_dispatch or human decision.",
    ]
    if self_test:
        conclusion.append("This self-test exercised the precondition-readiness paths with synthetic upstream aggregate reports.")
    if blockers:
        conclusion.append(f"Blocker(s): {len(blockers)}.")
    if warnings:
        conclusion.append(f"Warning(s): {len(warnings)}.")
    conclusion.append(
        f"Current status: {status}. "
        f"P61 recommends no provider spend and no live LLM calls without a separate explicit decision."
    )

    readiness_decision = {
        "decision": status,
        "decision_is_authorization": False,
        "provider_spend_authorized": False,
        "requires_separate_human_or_workflow_dispatch": True,
        "reasons": decision_reasons,
    }

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": status_reason,
        "self_test": self_test,
        "not_quality_evidence": True,
        "precondition_report_only": True,
        "micro_run_not_authorized": True,
        "provider_spend_authorized": False,
        "workflow_dispatch_required_for_live_run": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "evidence_admission_performed": False,
        "aggregate_only_public_artifact": True,
        "p61_uses_no_score_phase": True,
        "gold_used_by_p61": False,
        "remote_calls_by_p61": 0,
        "llm_calls_by_p61": 0,
        "remote_requests_by_p61": 0,
        "provider_config_read_by_p61": False,
        "prompt_construction_by_p61": False,
        "source_reads_attempted_by_p61": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_query_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "private_labels_committed": False,
        "elapsed_ms": elapsed_ms,
        "input_summary": input_summary,
        "upstream_safety_summary": safety_summary,
        "upstream_status_summary": status_summary,
        "decision_inputs": decision_inputs,
        "readiness_decision": readiness_decision,
        "warnings": warnings,
        "blockers": blockers,
        "conclusion": conclusion,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P61 public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        errors.append("generated_by mismatch")
    if report.get("stage") != STAGE:
        errors.append("stage mismatch")
    if report.get("status") not in ALLOWED_STATUS:
        errors.append(f"status must be one of {ALLOWED_STATUS}")

    for flag, expected in [
        ("remote_calls_by_p61", 0),
        ("llm_calls_by_p61", 0),
        ("remote_requests_by_p61", 0),
    ]:
        if report.get(flag) != expected:
            errors.append(f"{flag} must be {expected}")

    for flag in [
        "prompt_construction_by_p61",
        "source_reads_attempted_by_p61",
        "provider_config_read_by_p61",
        "provider_spend_authorized",
        "evidence_admission_performed",
        "gold_used_by_p61",
    ]:
        if report.get(flag) is not False:
            errors.append(f"{flag} must be false")

    for flag in [
        "not_quality_evidence",
        "precondition_report_only",
        "micro_run_not_authorized",
        "workflow_dispatch_required_for_live_run",
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "candidate_not_fact",
        "aggregate_only_public_artifact",
        "p61_uses_no_score_phase",
        "raw_text_stored",
        "raw_source_stored",
        "raw_snippets_stored",
        "raw_snippets_committed",
        "raw_snippets_sent_to_provider",
        "raw_prompts_stored",
        "raw_responses_stored",
        "raw_query_stored",
        "raw_paths_in_artifact",
        "raw_line_ranges_in_artifact",
        "raw_digests_in_artifact",
        "provider_keys_in_artifact",
        "gold_spans_in_artifact",
        "private_labels_committed",
    ]:
        expected = flag in {
            "not_quality_evidence",
            "precondition_report_only",
            "micro_run_not_authorized",
            "workflow_dispatch_required_for_live_run",
            "candidate_not_fact",
            "aggregate_only_public_artifact",
            "p61_uses_no_score_phase",
        }
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("self_test") and report.get("status") != "self_test_only":
        errors.append("self_test must set status=self_test_only")
    if report.get("status") == "self_test_only" and report.get("self_test") is not True:
        errors.append("status self_test_only requires self_test=true")
    if report.get("status") == "micro_run_preconditions_met" and report.get("self_test"):
        errors.append("self_test must not emit micro_run_preconditions_met")

    rd = report.get("readiness_decision") or {}
    if rd.get("decision") not in ALLOWED_STATUS:
        errors.append(f"readiness_decision.decision must be one of {ALLOWED_STATUS}")
    if rd.get("decision_is_authorization") is not False:
        errors.append("readiness_decision.decision_is_authorization must be false")
    if rd.get("provider_spend_authorized") is not False:
        errors.append("readiness_decision.provider_spend_authorized must be false")
    if rd.get("requires_separate_human_or_workflow_dispatch") is not True:
        errors.append("readiness_decision.requires_separate_human_or_workflow_dispatch must be true")

    for forbidden in ("tasks", "records", "per_task_results", "per_candidate_results", "per_slice_rows", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_scan_values_for_leaks(report))

    # Forbidden claims scan in text fields.
    forbidden_claims = [
        "authorized",
        "spend authorized",
        "safe to spend",
        "safe to run",
        "provider-ready",
        "LLM-ready",
        "quality evidence",
        "evidence admitted",
        "admission passed",
        "promotion ready",
        "default should change",
        "winner",
        "best policy",
        "recommended policy",
        "outperforms",
        "safe to deploy",
    ]
    text_fields: list[str] = []
    for field in ("status_reason", "conclusion", "warnings", "blockers"):
        val = report.get(field)
        if isinstance(val, str):
            text_fields.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    text_fields.append(item)
    reasons = rd.get("reasons") or []
    if isinstance(reasons, list):
        for item in reasons:
            if isinstance(item, str):
                text_fields.append(item)
    for text in text_fields:
        lower = text.lower()
        for claim in forbidden_claims:
            # Allow explicit negation.
            negated = f"not {claim}"
            if claim in lower and negated not in lower:
                errors.append(f"forbidden claim in text: {claim}")

    return errors


def _make_synthetic_upstream_report(phase: str, *, status: str = "self_test_only", self_test: bool = True) -> dict[str, Any]:
    """Build a minimal safe aggregate upstream report in memory for self-test."""
    cfg = PHASE_SAFETY.get(phase, {})
    report: dict[str, Any] = {
        "schema_version": f"{phase}-aggregate-report-v0",
        "status": status,
        "self_test": self_test,
        "not_quality_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
    }
    for flag in RAW_FLAGS:
        report[flag] = False
    remote_key = cfg.get("remote")
    if remote_key:
        report[remote_key] = 0
    llm_key = cfg.get("llm")
    if llm_key:
        report[llm_key] = 0
    prompt_key = cfg.get("prompt")
    if prompt_key:
        report[prompt_key] = False
    source_reads_key = cfg.get("source_reads")
    if source_reads_key:
        report[source_reads_key] = False
    source_bounded_key = cfg.get("source_bounded")
    if source_bounded_key:
        report[source_bounded_key] = True
    for key, expected in cfg.get("extra", {}).items():
        report[key] = expected
    return report


def _make_actionable_set() -> dict[str, dict[str, Any] | None]:
    """All-actionable set that would pass except P61 self-test forces self_test_only."""
    reports: dict[str, dict[str, Any] | None] = {}
    for phase in REQUIRED_PHASES:
        reports[phase] = _make_synthetic_upstream_report(phase, status="ok", self_test=False)
    reports["p52c"] = _make_synthetic_upstream_report("p52c", status="ok", self_test=False)

    # P57
    reports["p57"]["status"] = "diagnostic_matrix_complete"
    reports["p57"]["input_summary"] = {
        "slice_count": 4,
        "included_generalization_slice_count": 4,
        "required_present_count": 10,
        "required_missing": [],
    }
    reports["p57"]["generalization_matrix"] = {"readiness_status": "diagnostic_matrix_complete"}

    # P58
    reports["p58"]["status"] = "diagnostic_calibration_available"
    reports["p58"]["input_summary"] = {
        "required_present_count": 4,
        "required_missing": [],
        "upstream_status_by_phase": {"p57": "diagnostic_matrix_complete"},
    }

    # P59
    reports["p59"]["status"] = "diagnostic_coverage_available"
    reports["p59"]["metrics"] = {
        "by_strategy": {
            "anchor_contrast_pack_v0": {
                "counterfactual_actionability": {
                    "llm_spend_actionability_bucket": "actionable",
                }
            }
        }
    }

    # P60
    reports["p60"]["status"] = "diagnostic_policy_matrix_available"
    reports["p60"]["comparison_frame"] = {
        "no_winner_selected": True,
        "no_default_recommendation": True,
        "policy_comparison_not_ranking": True,
    }
    reports["p60"]["rmc_not_evidence"] = True
    reports["p60"]["rmc_not_admission"] = True
    reports["p60"]["rmc_next_action_only"] = True
    reports["p60"]["metrics"] = {
        "by_policy": {
            "policy_a": {
                "next_action_counts": {"p51c_span_narrow": 1},
                "rmc_to_llm_eligibility": {"eligible_count": 0},
            },
            "policy_b": {
                "next_action_counts": {"p51c_span_narrow": 0},
                "rmc_to_llm_eligibility": {"eligible_count": 1},
            },
        }
    }

    # P51B
    reports["p51b"]["status"] = "ok"
    reports["p51b"]["metrics"] = {
        "future_live_gate_readiness": {
            "p51b_live_gate_ready": True,
            "p51b_live_gate_ready_reason": "contract_valid_dry_run_only",
        },
        "eligibility": {
            "eligible_candidate_count": 10,
            "eligible_pack_count": 5,
            "eligibility_availability": "available_source_backed",
            "source_backed_live_eligibility_available": True,
        },
        "request_envelope_blueprint": {
            "request_envelope_blueprint_count": 3,
            "max_budget_violation_rate": 0.0,
            "redaction_required_rate": 0.0,
        },
        "role_output_schema_validation": {
            "role_output_schema_valid_rate": 1.0,
        },
    }

    # P52C
    reports["p52c"]["status"] = "ok"
    reports["p52c"]["source_reads_attempted_by_p52c"] = True
    reports["p52c"]["source_reads_bounded_by_p52c"] = True

    return reports


def _make_self_test_reports() -> dict[str, dict[str, Any] | None]:
    """In-memory synthetic reports covering all self-test scenarios."""
    # Start with the actionable set; self-test flag will be forced later.
    return _make_actionable_set()


def _make_p59_blocked_actionability() -> dict[str, dict[str, Any] | None]:
    reports = _make_actionable_set()
    reports["p59"]["metrics"]["by_strategy"]["anchor_contrast_pack_v0"]["counterfactual_actionability"]["llm_spend_actionability_bucket"] = "blocked_missing_hard_distractor"
    return reports


def _make_missing_required() -> dict[str, dict[str, Any] | None]:
    reports = _make_actionable_set()
    reports["p59"] = None
    return reports


def _make_upstream_blocked_safety() -> dict[str, dict[str, Any] | None]:
    reports = _make_actionable_set()
    reports["p60"]["prompt_construction_by_p60"] = True
    return reports


def _make_single_slice_p57() -> dict[str, dict[str, Any] | None]:
    reports = _make_actionable_set()
    reports["p57"]["input_summary"]["slice_count"] = 1
    reports["p57"]["input_summary"]["included_generalization_slice_count"] = 0
    return reports


def _make_missing_safety_flag() -> dict[str, dict[str, Any] | None]:
    reports = _make_actionable_set()
    reports["p57"].pop("remote_calls_by_p57", None)
    return reports


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
        f"- Remote calls by P61: {report['remote_calls_by_p61']}",
        f"- LLM calls by P61: {report['llm_calls_by_p61']}",
        f"- Prompt construction by P61: {report['prompt_construction_by_p61']}",
        f"- Provider config read by P61: {report['provider_config_read_by_p61']}",
        "",
    ])

    lines.extend([
        "## Purpose",
        "",
        "P61 Pre-Spend Gate v0 consumes only public aggregate JSON reports from upstream diagnostics (P57, P58, P59, P60, P51-B required; P52C optional) and emits a precondition-readiness decision about whether a future P51-C live LLM micro-run is worth *considering*. ",
        "It is **not** quality evidence, **not** authorization, **not** Evidence, **not** a promotion/default gate, and **not** a claim that a live run is safe or ready. ",
        "No source files, candidate pools, ephemeral records, prompts, responses, provider configs, or per-task/per-candidate rows are read.",
        "",
        "## Methodology",
        "",
        "- Read only aggregate upstream report JSON (no `--input`, `--repo-lock`, `--source-root`, no provider/model/prompt arguments).",
        "- Required upstream reports: P57, P58, P59, P60, P51-B.",
        "- Optional upstream report: P52C.",
        "- Collapse upstream statuses to an allowlisted safe enum.",
        "- Verify upstream safety flags: promotion/default false, `candidate_not_fact=true`, aggregate-only true, remote/LLM/prompt counters zero, source reads not attempted.",
        "- Apply deterministic readiness gates: P57 generalization complete and slice count >= 4, P58 calibration available, P59 actionable, P60 precondition-only routing with a P51-C or LLM-eligible route, P51-B contract ready with source-backed eligibility and zero budget/redaction violations.",
        "- Emit a `readiness_decision` that explicitly states it is not authorization and requires a separate workflow_dispatch or human decision.",
        "",
        "## Safety notes",
        "",
        "- P61 makes no remote, LLM, or provider calls.",
        "- P61 does not construct prompts, read source files, or access ephemeral records.",
        "- P61 does not publish task IDs, candidate IDs, repo IDs, datasets, paths, spans, line ranges, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.",
        "- P61 output is aggregate-only and explicitly flagged as not quality evidence, not authorization, not Evidence, and not default/promotion/live readiness.",
        "",
    ])

    inp = report["input_summary"]
    lines.extend([
        "## Input summary",
        "",
        f"- Required reports: {', '.join(inp['required_reports'])}",
        f"- Optional reports: {', '.join(inp['optional_reports'])}",
        f"- Required present count: {inp['required_present_count']}/{len(inp['required_reports'])}",
        f"- Optional present count: {inp['optional_present_count']}/{len(inp['optional_reports'])}",
        f"- Required missing: {', '.join(inp['required_missing']) if inp['required_missing'] else 'none'}",
        f"- Invalid JSON or contract-violating upstream reports: {inp['invalid_json_count']}",
        "",
        "### Upstream status by phase",
        "",
        "| Phase | Status |",
        "|---|---|",
    ])
    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        lines.append(f"| {phase} | `{inp['upstream_status_by_phase'].get(phase, 'not_provided')}` |")
    lines.append("")

    sg = report["upstream_safety_summary"]
    lines.extend([
        "## Upstream safety summary",
        "",
        f"- Checked phase count: {sg['checked_phase_count']}",
        f"- Safety blocker count: {sg['safety_blocker_count']}",
        f"- Safety warning count: {sg['safety_warning_count']}",
        "",
        "| Phase | Present | Status | Safety blocker | Warnings |",
        "|---|---|---|---|---|",
    ])
    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        v = sg["by_phase"].get(phase, {})
        lines.append(
            f"| {phase} | {v.get('report_present', False)} | `{v.get('status', 'not_provided')}` | "
            f"{v.get('safety_blocker', False)} | {len(v.get('safety_warnings', []))} |"
        )
    lines.append("")

    di = report["decision_inputs"]
    lines.extend([
        "## Decision inputs",
        "",
        f"- P57 matrix complete: {di['p57_matrix_complete']}",
        f"- P57 required slice count met: {di['p57_required_slice_count_met']}",
        f"- P58 calibration available: {di['p58_calibration_available']}",
        f"- P59 actionability bucket: `{di['p59_actionability_bucket']}`",
        f"- P59 actionability precondition met: {di['p59_actionability_precondition_met']}",
        f"- P60 P51-C route available: {di['p60_p51c_route_available']}",
        f"- P60 LLM-eligible route available: {di['p60_llm_eligible_route_available']}",
        f"- P60 policy count with P51-C route: {di['p60_policy_count_with_p51c_route']}",
        f"- P60 policy count with LLM-eligible route: {di['p60_policy_count_with_llm_eligible_route']}",
        f"- P60 routing is precondition-only: {di['p60_routing_is_precondition_only']}",
        f"- P51-B contract precondition met: {di['p51b_contract_precondition_met']}",
        f"- P51-B eligibility is precondition-only: {di['p51b_eligibility_is_precondition_only']}",
        f"- P51-B budget violation absent: {di['p51b_budget_violation_absent']}",
        f"- P51-B redaction required absent: {di['p51b_redaction_required_absent']}",
        f"- P51-B schema validation precondition met: {di['p51b_schema_validation_precondition_met']}",
        f"- P52C optional score availability: `{di['p52c_optional_score_availability']}`",
        f"- P52C optional present: {di['p52c_optional_present']}",
        "",
    ])

    rd = report["readiness_decision"]
    lines.extend([
        "## Readiness decision",
        "",
        f"- Decision: `{rd['decision']}`",
        f"- Decision is authorization flag: {rd['decision_is_authorization']}",
        f"- Provider spend authorization flag: {rd['provider_spend_authorized']}",
        f"- Requires separate human or workflow_dispatch: {rd['requires_separate_human_or_workflow_dispatch']}",
        f"- Reasons: {', '.join(rd['reasons']) if rd['reasons'] else 'none'}",
        "",
    ])

    lines.extend([
        "## Blockers",
        "",
    ])
    if report["blockers"]:
        for b in report["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend([
        "## Warnings",
        "",
    ])
    if report["warnings"]:
        for w in report["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend([
        "## Conclusion",
        "",
    ])
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--p57-report", type=Path, default=None, help="P57 aggregate report path.")
    parser.add_argument("--p58-report", type=Path, default=None, help="P58 aggregate report path.")
    parser.add_argument("--p59-report", type=Path, default=None, help="P59 aggregate report path.")
    parser.add_argument("--p60-report", type=Path, default=None, help="P60 aggregate report path.")
    parser.add_argument("--p51b-report", type=Path, default=None, help="P51-B aggregate report path.")
    parser.add_argument("--p52c-report", type=Path, default=None, help="Optional P52C aggregate report path.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    if not args.self_test:
        missing = [name for name in REQUIRED_PHASES if getattr(args, f"{name}_report") is None]
        if missing:
            parser.error(f"Required reports missing: {', '.join(missing)}. Use --self-test to run synthetic self-test.")

    start = time.monotonic()

    if args.self_test:
        reports = _make_self_test_reports()

        # a) all-actionable set WOULD pass except self-test forces self_test_only.
        status_a, reasons_a, _ = compute_status(reports)
        if status_a != "micro_run_preconditions_met":
            raise RuntimeError(f"P61 self-test actionable set unexpectedly returned {status_a}: {reasons_a}")

        # b) P59 blocked_missing_actionability
        blocked_p59 = _make_p59_blocked_actionability()
        status_b, reasons_b, _ = compute_status(blocked_p59)
        if status_b != "blocked_missing_actionability":
            raise RuntimeError(f"P61 self-test P59 blocked actionability did not return blocked_missing_actionability: {status_b}, {reasons_b}")
        if not any("p59_actionability_not_actionable" in r for r in reasons_b):
            raise RuntimeError("P61 self-test P59 blocked actionability missing expected reason")

        # c) missing required report
        missing_reports = _make_missing_required()
        status_c, reasons_c, _ = compute_status(missing_reports)
        if status_c != "insufficient_inputs":
            raise RuntimeError(f"P61 self-test missing required report did not return insufficient_inputs: {status_c}, {reasons_c}")
        if not any("missing_required_report:p59" in r for r in reasons_c):
            raise RuntimeError("P61 self-test missing required report missing expected reason")

        # d) upstream blocked_safety
        unsafe_reports = _make_upstream_blocked_safety()
        status_d, reasons_d, _ = compute_status(unsafe_reports)
        if status_d != "blocked_safety":
            raise RuntimeError(f"P61 self-test upstream blocked safety did not return blocked_safety: {status_d}, {reasons_d}")
        if not any("upstream_safety_blocker:p60" in r for r in reasons_d):
            raise RuntimeError("P61 self-test upstream blocked safety missing expected reason")

        # e) single-slice P57
        single_slice = _make_single_slice_p57()
        status_e, reasons_e, _ = compute_status(single_slice)
        if status_e != "insufficient_inputs":
            raise RuntimeError(f"P61 self-test single-slice P57 did not return insufficient_inputs: {status_e}, {reasons_e}")
        if not any("single_slice_or_insufficient_matrix:p57" in r for r in reasons_e):
            raise RuntimeError("P61 self-test single-slice P57 missing expected reason")

        # f) missing required safety flag must be fail-closed -> blocked_safety
        missing_safety = _make_missing_safety_flag()
        status_f, reasons_f, _ = compute_status(missing_safety)
        if status_f != "blocked_safety":
            raise RuntimeError(f"P61 self-test missing required safety flag did not return blocked_safety: {status_f}, {reasons_f}")
        if not any("upstream_safety_blocker:p57" in r for r in reasons_f):
            raise RuntimeError("P61 self-test missing required safety flag missing expected reason")

    else:
        reports = _load_reports_from_args(args)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    report = _build_report(reports, self_test=args.self_test, elapsed_ms=elapsed_ms)

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P61 report written to {args.out}")
    print(f"P61 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
