#!/usr/bin/env python3
"""P58 Source-Backed Verifier Calibration v0.

P58 is a deterministic, no-live-LLM, no-provider, aggregate-only calibration
report. It consumes only public aggregate JSON reports from upstream diagnostics
(P48, P52C, P51B, P57, and optionally P52B/P52A/P49) and turns their
availability/distributions into coarse planning/action-hint buckets.

Hard constraints:
* NOT a verifier, NOT admission, NOT Evidence, NOT default/promotion/live readiness.
* No remote or LLM calls (`remote_calls_by_p58=0`, `llm_calls_by_p58=0`,
  `remote_requests_by_p58=0`).
* No prompt construction (`prompt_construction_by_p58=false`).
* No source reads (`source_reads_attempted_by_p58=false`).
* No provider/model/config reads (`provider_config_read_by_p58=false`).
* Public output is aggregate-only: no task IDs, candidate IDs, repo IDs, datasets,
  paths, spans, line ranges, digests, queries, snippets, prompts, responses,
  provider/model/base URL/API key, gold spans, or private labels.
* Reads only aggregate upstream report JSON. Does not read source files,
  candidate pools, tasks, repo locks, or per-candidate rows.
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

SCHEMA_VERSION = "p58-source-backed-verifier-calibration-v0"
GENERATED_BY = "p58_source_backed_verifier_calibration"
STAGE = "P58 Source-Backed Verifier Calibration v0"

DEFAULT_OUT = Path("artifacts/p58_source_backed_verifier_calibration/p58_source_backed_verifier_calibration_report.json")
DEFAULT_DOC = Path("docs/en/p58-source-backed-verifier-calibration.md")

REQUIRED_PHASES = ["p48", "p52c", "p51b", "p57"]
OPTIONAL_PHASES = ["p52b", "p52a", "p49"]

ALLOWED_STATUS = {
    "blocked_safety",
    "insufficient_upstream",
    "diagnostic_calibration_unavailable",
    "diagnostic_calibration_partial",
    "diagnostic_calibration_available",
    "self_test_only",
}

SAFE_UPSTREAM_STATUS = {
    "ok",
    "self_test_only",
    "insufficient_task_detail",
    "insufficient_matrix",
    "diagnostic_matrix_complete",
    "diagnostic_matrix_unstable",
    "blocked_safety",
    "invalid_json",
    "not_provided",
    "aggregate_contract_violation",
}

# Exact forbidden public keys. Keys that are intentionally allowed as P58 safety
# flags or metric block names are listed in P58_SAFETY_FLAG_KEYS.
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
    "query",
    "snippet",
    "prompt",
    "response",
    "provider",
    "model",
    "base_url",
    "api_key",
    "repo_lock",
    "source_root",
    "tasks",
    "records",
    "per_task_results",
    "per_candidate_results",
    "per_slice_rows",
    "candidate_score",
    "raw_candidate_score",
    "diagnostic_score_v0",
    "local_verifier_score",
    "verifier_pass",
    "verifier_fail",
    "evidence_valid",
    "admission_decision",
    "promotion_decision",
    "default_decision",
}

P58_SAFETY_FLAG_KEYS = {
    # top-level
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    "not_quality_evidence",
    "real_evaluation",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "score_phase_only_metrics",
    "aggregate_only_public_artifact",
    "remote_calls_by_p58",
    "llm_calls_by_p58",
    "remote_requests_by_p58",
    "prompt_construction_by_p58",
    "source_reads_attempted_by_p58",
    "provider_config_read_by_p58",
    "calibration_not_evidence",
    "action_hints_not_admission",
    "p52c_score_not_pass_fail",
    "p52c_score_not_evidence",
    "source_backed_not_verification",
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
    "calibration_denominators",
    "source_backed_coverage",
    "p52c_bucket_carry_forward",
    "request_more_context_calibration",
    "local_verifier_priority_calibration",
    "p51c_eligibility_calibration",
    "warnings",
    "blockers",
    "conclusion",
    "validation",
    # input_summary keys
    "required_reports",
    "optional_reports",
    "required_present_count",
    "optional_present_count",
    "required_missing",
    "invalid_json_count",
    "upstream_status_by_phase",
    # upstream_safety_summary keys
    "checked_phase_count",
    "safety_blocker_count",
    "safety_warning_count",
    "p57_insufficient_matrix_acceptable",
    "by_phase",
    "report_present",
    "status",
    "safety_blocker",
    "safety_warnings",
    # calibration_denominators keys
    "p52c_candidate_denominator",
    "p52c_score_candidate_denominator",
    "p51b_candidate_denominator",
    "p51b_eligible_candidate_count",
    "p48_selected_count",
    "p48_request_more_context_count",
    "calibration_denominator_available",
    # source_backed_coverage keys
    "source_backed_coverage_bucket",
    "p52c_score_availability",
    "source_backed_score_candidate_denominator",
    "metadata_only_candidate_denominator",
    "score_unavailable_candidate_rate",
    # p52c_bucket_carry_forward keys
    "score_bucket_distribution_available",
    "diagnostic_score_high_rate",
    "diagnostic_score_medium_rate",
    "diagnostic_score_low_rate",
    "diagnostic_score_unavailable_rate",
    "p52c_distribution_not_pass_fail",
    # request_more_context_calibration keys
    "hint_bucket",
    "request_more_context_rate",
    "demoted_primary_rate",
    "p52c_low_or_unavailable_rate",
    "calibration_basis",
    "diagnostic_only",
    "not_admission",
    # local_verifier_priority_calibration keys
    "source_backed_coverage_bucket",
    "diagnostic_score_distribution_available",
    "component_coverage_available",
    # p51c_eligibility_calibration keys
    "eligibility_availability",
    "source_backed_live_eligibility_available",
    "eligible_candidate_rate",
    "request_envelope_blueprint_count",
    "budget_violation_rate",
    "redaction_required_rate",
    "not_live_readiness",
    "not_provider_authorization",
    # common helpers
    "count",
    "rate",
    "value",
    "availability",
}

PHASE_SAFETY = {
    "p48": {
        "remote": "remote_calls_by_p48",
        "llm": None,
        "prompt": None,
        "source_reads": "source_reads_attempted_by_p48",
        "source_bounded": None,
        "extra": {},
    },
    "p52c": {
        "remote": "remote_calls_by_p52c",
        "llm": "llm_calls_by_p52c",
        "prompt": "prompt_construction_by_p52c",
        "source_reads": "source_reads_attempted_by_p52c",
        "source_bounded": "source_reads_bounded_by_p52c",
        "extra": {},
    },
    "p51b": {
        "remote": "remote_calls_by_p51b",
        "llm": "llm_calls_by_p51b",
        "prompt": "prompt_construction_by_p51b",
        "source_reads": "source_reads_attempted_by_p51b",
        "source_bounded": None,
        "extra": {
            "remote_requests_by_p51b": 0,
            "dry_run_payload_validation_only": True,
            "p51b_live_calls_disabled": True,
        },
    },
    "p57": {
        "remote": "remote_calls_by_p57",
        "llm": "llm_calls_by_p57",
        "prompt": "prompt_construction_by_p57",
        "source_reads": "source_reads_attempted_by_p57",
        "source_bounded": None,
        "extra": {},
    },
    "p52b": {
        "remote": "remote_calls_by_p52b",
        "llm": "llm_calls_by_p52b",
        "prompt": "prompt_construction_by_p52b",
        "source_reads": "source_reads_attempted_by_p52b",
        "source_bounded": "source_reads_bounded_by_p52b",
        "extra": {},
    },
    "p52a": {
        "remote": "remote_calls_by_p52a",
        "llm": "llm_calls_by_p52a",
        "prompt": "prompt_construction_by_p52a",
        "source_reads": "source_reads_attempted_by_p52a",
        "source_bounded": "source_reads_bounded_by_p52a",
        "extra": {},
    },
    "p49": {
        "remote": "remote_calls_by_p49",
        "llm": "llm_calls_by_p49",
        "prompt": "prompt_construction_by_p49",
        "source_reads": "source_reads_attempted_by_p49",
        "source_bounded": None,
        "extra": {},
    },
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
    "score_phase_only_metrics": True,
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


def _rate(num: Any, den: Any) -> float | None:
    n = _as_int(num)
    d = _as_int(den)
    if n is None or d is None or d <= 0:
        return None
    return round(n / d, 6)


def _get_path(data: Any, path: list[str]) -> Any:
    value = data
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def _safe_status(data: dict[str, Any] | None) -> str:
    if data is None:
        return "not_provided"
    if data.get("_invalid_json"):
        return "invalid_json"
    status = data.get("status")
    if isinstance(status, str) and status in SAFE_UPSTREAM_STATUS:
        return status
    return "unrecognized_status"


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P58_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
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
        if len(text) > 1 and (text.startswith("/") or text.startswith("\\")):
            violations.append(prefix + " looks like an absolute path")
        elif "://" in text:
            violations.append(prefix + " looks like a URL")
        elif re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
            violations.append(prefix + " looks like an API key")
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
    value_violations = _scan_values_for_leaks(data)
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


def _verify_upstream_safety(phase: str, data: dict[str, Any] | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "report_present": data is not None and not data.get("_invalid_json"),
        "status": _safe_status(data),
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
        upstream_status_by_phase[phase] = _safe_status(data)

    for phase in OPTIONAL_PHASES:
        data = reports.get(phase)
        if data is not None and not data.get("_invalid_json"):
            optional_present += 1
        if data and data.get("_invalid_json"):
            invalid_json_count += 1
        if data and data.get("_aggregate_contract_violation"):
            invalid_json_count += 1
        upstream_status_by_phase[phase] = _safe_status(data)

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
        v = _verify_upstream_safety(phase, data)
        by_phase[phase] = v
        if v["safety_blocker"]:
            blocker_count += 1
        warning_count += len(v["safety_warnings"])

    return {
        "checked_phase_count": checked,
        "safety_blocker_count": blocker_count,
        "safety_warning_count": warning_count,
        "p57_insufficient_matrix_acceptable": True,
        "by_phase": by_phase,
    }


def _calibration_denominators(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p52c = reports.get("p52c") or {}
    p48 = reports.get("p48") or {}
    p51b = reports.get("p51b") or {}

    p52c_avail = _get_path(p52c, ["metrics", "score_availability"]) or {}
    p48_route = _get_path(p48, ["route_simulation", "p48_p25_rmc_overlay_v0"]) or {}
    p51b_elig = _get_path(p51b, ["metrics", "eligibility"]) or {}

    p52c_candidate_denominator = _as_int(p52c_avail.get("candidate_denominator"))
    p52c_score_candidate_denominator = _as_int(p52c_avail.get("score_candidate_denominator"))
    p51b_candidate_denominator = _as_int(p51b_elig.get("candidate_denominator"))
    p51b_eligible_candidate_count = _as_int(p51b_elig.get("eligible_candidate_count"))
    p48_selected_count = _as_int(p48_route.get("selected_count"))
    if p48_selected_count is None:
        p48_selected_count = _as_int(p48.get("task_count"))
    p48_request_more_context_count = _as_int(p48_route.get("request_more_context_count"))

    required_values = [
        p52c_candidate_denominator,
        p52c_score_candidate_denominator,
        p51b_candidate_denominator,
        p51b_eligible_candidate_count,
        p48_selected_count,
        p48_request_more_context_count,
    ]
    available_count = sum(1 for v in required_values if v is not None)
    if available_count == len(required_values):
        availability = "available"
    elif available_count > 0:
        availability = "partial"
    else:
        availability = "unavailable"

    return {
        "p52c_candidate_denominator": p52c_candidate_denominator,
        "p52c_score_candidate_denominator": p52c_score_candidate_denominator,
        "p51b_candidate_denominator": p51b_candidate_denominator,
        "p51b_eligible_candidate_count": p51b_eligible_candidate_count,
        "p48_selected_count": p48_selected_count,
        "p48_request_more_context_count": p48_request_more_context_count,
        "calibration_denominator_available": availability,
    }


def _source_backed_coverage(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p52c = reports.get("p52c") or {}
    p52c_avail = _get_path(p52c, ["metrics", "score_availability"]) or {}

    availability = p52c_avail.get("p52c_score_availability") or "not_provided"
    source_backed = _as_int(p52c_avail.get("source_backed_score_candidate_denominator"))
    metadata_only = _as_int(p52c_avail.get("metadata_only_candidate_denominator"))
    score_unavailable_rate = _as_float(p52c_avail.get("score_unavailable_candidate_rate"))

    if availability in {"available_source_backed"}:
        bucket = "source_backed_available"
    elif availability in {"partial_source_backed"}:
        bucket = "source_backed_partial"
    elif availability in {"partial_metadata_only"}:
        bucket = "metadata_only"
    elif availability in {"unavailable_no_source_reads", "unavailable_missing_upstream_contract"}:
        bucket = "source_unavailable"
    elif availability in {"unavailable_missing_candidate_pool"}:
        bucket = "missing_candidate_pool"
    else:
        bucket = "unavailable"

    return {
        "source_backed_coverage_bucket": bucket,
        "p52c_score_availability": availability,
        "source_backed_score_candidate_denominator": source_backed,
        "metadata_only_candidate_denominator": metadata_only,
        "score_unavailable_candidate_rate": score_unavailable_rate,
        "source_backed_not_verification": True,
    }


def _p52c_bucket_carry_forward(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p52c = reports.get("p52c") or {}
    dist = _get_path(p52c, ["metrics", "diagnostic_score_distribution"]) or {}
    rates = dist.get("diagnostic_score_bucket_rates") or {}

    available = isinstance(rates, dict) and all(
        k in rates for k in ("diagnostic_score_high", "diagnostic_score_medium", "diagnostic_score_low", "diagnostic_score_unavailable")
    )

    return {
        "score_bucket_distribution_available": available,
        "diagnostic_score_high_rate": _as_float(rates.get("diagnostic_score_high")) if available else None,
        "diagnostic_score_medium_rate": _as_float(rates.get("diagnostic_score_medium")) if available else None,
        "diagnostic_score_low_rate": _as_float(rates.get("diagnostic_score_low")) if available else None,
        "diagnostic_score_unavailable_rate": _as_float(rates.get("diagnostic_score_unavailable")) if available else None,
        "p52c_distribution_not_pass_fail": True,
    }


def _request_more_context_calibration(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p48 = reports.get("p48") or {}
    p48_route = _get_path(p48, ["route_simulation", "p48_p25_rmc_overlay_v0"]) or {}
    rmc_rate = _as_float(p48_route.get("request_more_context_rate"))
    demoted_rate = _as_float(p48_route.get("demoted_primary_rate"))

    p52c = reports.get("p52c") or {}
    p52c_carry = _p52c_bucket_carry_forward(reports)
    low_rate = p52c_carry.get("diagnostic_score_low_rate")
    unavailable_rate = p52c_carry.get("diagnostic_score_unavailable_rate")

    if rmc_rate is None or low_rate is None or unavailable_rate is None:
        hint_bucket = "unavailable"
        low_or_unavailable = None
    else:
        low_or_unavailable = round((low_rate or 0.0) + (unavailable_rate or 0.0), 6)
        if rmc_rate >= 0.25 or low_or_unavailable >= 0.40:
            hint_bucket = "high"
        elif rmc_rate >= 0.10 or low_or_unavailable >= 0.20:
            hint_bucket = "medium"
        else:
            hint_bucket = "low"

    return {
        "hint_bucket": hint_bucket,
        "request_more_context_rate": rmc_rate,
        "demoted_primary_rate": demoted_rate,
        "p52c_low_or_unavailable_rate": low_or_unavailable,
        "calibration_basis": "aggregate_p48_p52c",
        "diagnostic_only": True,
        "not_admission": True,
    }


def _local_verifier_priority_calibration(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    coverage = _source_backed_coverage(reports)
    p52c_carry = _p52c_bucket_carry_forward(reports)

    p52c = reports.get("p52c") or {}
    p52c_avail = _get_path(p52c, ["metrics", "score_availability"]) or {}
    score_denom = _as_int(p52c_avail.get("score_candidate_denominator"))
    source_backed = _as_int(p52c_avail.get("source_backed_score_candidate_denominator"))
    source_backed_rate = _rate(source_backed, score_denom) if score_denom else None

    dist = _get_path(p52c, ["metrics", "diagnostic_score_distribution"]) or {}
    component_coverage = dist.get("component_coverage") or {}
    component_coverage_available = bool(
        component_coverage
        and isinstance(component_coverage, dict)
        and any(v.get("availability") == "available" for v in component_coverage.values() if isinstance(v, dict))
    )

    distribution_available = p52c_carry.get("score_bucket_distribution_available", False)

    if not distribution_available or score_denom is None or score_denom <= 0:
        hint_bucket = "unavailable"
    elif (source_backed_rate is not None and source_backed_rate >= 0.50) and component_coverage_available:
        hint_bucket = "high"
    elif score_denom is not None and score_denom > 0:
        hint_bucket = "medium"
    else:
        hint_bucket = "low"

    return {
        "hint_bucket": hint_bucket,
        "source_backed_coverage_bucket": coverage.get("source_backed_coverage_bucket"),
        "diagnostic_score_distribution_available": distribution_available,
        "component_coverage_available": component_coverage_available,
        "diagnostic_only": True,
        "not_verifier_pass_fail": True,
        "not_admission": True,
    }


def _p51c_eligibility_calibration(reports: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    p51b = reports.get("p51b") or {}
    p51b_elig = _get_path(p51b, ["metrics", "eligibility"]) or {}
    p51b_blueprint = _get_path(p51b, ["metrics", "request_envelope_blueprint"]) or {}

    eligibility_availability = p51b_elig.get("eligibility_availability") or "not_provided"
    source_backed_live = bool(p51b_elig.get("source_backed_live_eligibility_available"))
    eligible_rate = _as_float(p51b_elig.get("eligible_candidate_rate"))
    blueprint_count = _as_int(p51b_blueprint.get("request_envelope_blueprint_count"))
    budget_violation_rate = _as_float(p51b_blueprint.get("max_budget_violation_rate"))
    redaction_rate = _as_float(p51b_blueprint.get("redaction_required_rate"))

    if eligibility_availability in {"available_source_backed"}:
        hint_bucket = "p51c_planning_source_backed"
    elif eligibility_availability in {"partial_metadata_only"}:
        hint_bucket = "p51c_planning_metadata_only"
    elif eligibility_availability in {
        "unavailable_missing_candidate_pool",
        "unavailable_missing_upstream_contract",
        "unavailable_no_source_reads",
        "not_provided",
    }:
        hint_bucket = "p51c_planning_unavailable"
    elif budget_violation_rate is not None and budget_violation_rate > 0:
        hint_bucket = "p51c_planning_contract_budget_attention"
    else:
        hint_bucket = "p51c_planning_partial"

    return {
        "hint_bucket": hint_bucket,
        "eligibility_availability": eligibility_availability,
        "source_backed_live_eligibility_available": source_backed_live,
        "eligible_candidate_rate": eligible_rate,
        "request_envelope_blueprint_count": blueprint_count,
        "budget_violation_rate": budget_violation_rate,
        "redaction_required_rate": redaction_rate,
        "diagnostic_only": True,
        "not_live_readiness": True,
        "not_provider_authorization": True,
    }


def _determine_status(
    input_summary: dict[str, Any],
    safety_summary: dict[str, Any],
    denominators: dict[str, Any],
    coverage: dict[str, Any],
    p52c_carry: dict[str, Any],
    p51c_cal: dict[str, Any],
    self_test: bool,
) -> tuple[str, str | None]:
    if self_test:
        return "self_test_only", "Self-test-only aggregate calibration; not quality evidence."

    if input_summary.get("required_missing") or input_summary.get("invalid_json_count", 0) > 0:
        return "insufficient_upstream", "Required upstream aggregate reports are missing or unreadable."

    if safety_summary.get("safety_blocker_count", 0) > 0:
        return "blocked_safety", "Upstream safety flag violations detected."

    # P57 insufficient_matrix is acceptable; other upstream unstable statuses
    # still allow calibration but may reduce availability.
    p57_status = input_summary.get("upstream_status_by_phase", {}).get("p57")
    if p57_status == "blocked_safety":
        return "blocked_safety", "P57 reported blocked_safety."

    denom_avail = denominators.get("calibration_denominator_available")
    coverage_bucket = coverage.get("source_backed_coverage_bucket")
    score_available = p52c_carry.get("score_bucket_distribution_available", False)
    elig_available = p51c_cal.get("eligibility_availability") not in {
        "not_provided",
        "unavailable_missing_candidate_pool",
        "unavailable_missing_upstream_contract",
        "unavailable_no_source_reads",
    }

    if denom_avail == "available" and coverage_bucket not in {"unavailable", "missing_candidate_pool"} and score_available and elig_available:
        return "diagnostic_calibration_available", "Aggregate diagnostic calibration is available from upstream reports."
    if denom_avail in {"available", "partial"} or score_available or elig_available:
        return "diagnostic_calibration_partial", "Partial aggregate diagnostic calibration from upstream reports."
    return "diagnostic_calibration_unavailable", "Upstream diagnostic availability does not support coarse calibration."


def _make_synthetic_upstream_report(phase: str) -> dict[str, Any]:
    """Build a minimal aggregate upstream report in memory for self-test."""
    cfg = PHASE_SAFETY.get(phase, {})
    report: dict[str, Any] = {
        "schema_version": f"{phase}-aggregate-report-v0",
        "status": "self_test_only",
        "self_test": True,
        "not_quality_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
    }
    for key, expected in COMMON_FLAGS.items():
        report[key] = expected
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
        report[source_reads_key] = bool(cfg.get("source_bounded"))
    source_bounded_key = cfg.get("source_bounded")
    if source_bounded_key:
        report[source_bounded_key] = True
    for key, expected in cfg.get("extra", {}).items():
        report[key] = expected
    return report


def _make_self_test_reports() -> dict[str, dict[str, Any] | None]:
    reports: dict[str, dict[str, Any] | None] = {}
    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        reports[phase] = _make_synthetic_upstream_report(phase)

    # P48: shape request-more-context overlay.
    reports["p48"]["route_simulation"] = {
        "p48_p25_rmc_overlay_v0": {
            "availability": "available",
            "selected_count": 100,
            "request_more_context_count": 20,
            "request_more_context_rate": 0.20,
            "demoted_primary_count": 10,
            "demoted_primary_rate": 0.10,
        },
    }

    # P52C: score availability and diagnostic distribution.
    reports["p52c"]["metrics"] = {
        "score_availability": {
            "p52c_score_availability": "available_source_backed",
            "candidate_denominator": 100,
            "score_candidate_denominator": 95,
            "source_backed_score_candidate_denominator": 60,
            "metadata_only_candidate_denominator": 35,
            "score_unavailable_candidate_rate": 0.05,
        },
        "diagnostic_score_distribution": {
            "diagnostic_score_bucket_counts": {
                "diagnostic_score_high": 19,
                "diagnostic_score_medium": 48,
                "diagnostic_score_low": 19,
                "diagnostic_score_unavailable": 10,
            },
            "diagnostic_score_bucket_rates": {
                "diagnostic_score_high": 0.20,
                "diagnostic_score_medium": 0.505263,
                "diagnostic_score_low": 0.20,
                "diagnostic_score_unavailable": 0.10,
            },
            "component_coverage": {
                "source_read_success": {"availability": "available"},
                "line_range_valid": {"availability": "available"},
            },
        },
    }

    # P51B: eligibility and blueprint.
    reports["p51b"]["metrics"] = {
        "eligibility": {
            "candidate_denominator": 100,
            "eligible_candidate_count": 40,
            "eligible_candidate_rate": 0.40,
            "eligibility_availability": "available_source_backed",
            "source_backed_live_eligibility_available": True,
        },
        "request_envelope_blueprint": {
            "request_envelope_blueprint_count": 10,
            "max_budget_violation_rate": 0.10,
            "redaction_required_rate": 0.20,
        },
    }

    # P57: insufficient_matrix acceptable for self-test/single slice.
    reports["p57"]["status"] = "insufficient_matrix"
    reports["p57"]["generalization_matrix"] = {
        "readiness_status": "insufficient_matrix",
    }
    reports["p57"]["upstream_safety_gate"] = {
        "checked_count": 4,
        "blocker_count": 0,
        "warning_count": 0,
        "by_phase": {},
    }
    return reports


def _build_report(
    reports: dict[str, dict[str, Any] | None],
    *,
    self_test: bool,
    elapsed_ms: int,
) -> dict[str, Any]:
    input_summary = _input_summary(reports)
    safety_summary = _upstream_safety_summary(reports)
    denominators = _calibration_denominators(reports)
    coverage = _source_backed_coverage(reports)
    p52c_carry = _p52c_bucket_carry_forward(reports)
    rmc_cal = _request_more_context_calibration(reports)
    lv_cal = _local_verifier_priority_calibration(reports)
    p51c_cal = _p51c_eligibility_calibration(reports)

    status, status_reason = _determine_status(
        input_summary, safety_summary, denominators, coverage, p52c_carry, p51c_cal, self_test
    )

    warnings: list[str] = []
    blockers: list[str] = []

    for phase in input_summary.get("required_missing", []):
        blockers.append(f"Required upstream report {phase} missing or unreadable.")
    if input_summary.get("invalid_json_count", 0) > 0:
        warnings.append(f"Invalid JSON upstream reports: {input_summary['invalid_json_count']}.")

    for phase, v in safety_summary.get("by_phase", {}).items():
        if v.get("safety_blocker"):
            blockers.append(f"Upstream safety flag violations in phase {phase}.")

    for phase in OPTIONAL_PHASES:
        data = reports.get(phase)
        if data is None or data.get("_invalid_json"):
            warnings.append(f"Optional upstream report {phase} not provided or invalid.")

    if input_summary.get("upstream_status_by_phase", {}).get("p57") == "insufficient_matrix":
        warnings.append("P57 reports insufficient_matrix; this is acceptable for P58 calibration.")

    if denominators.get("calibration_denominator_available") != "available":
        warnings.append("Calibration denominators are partial or unavailable.")
    if coverage.get("source_backed_coverage_bucket") in {"unavailable", "missing_candidate_pool"}:
        warnings.append("Source-backed coverage unavailable from upstream P52C.")
    if not p52c_carry.get("score_bucket_distribution_available"):
        warnings.append("P52C diagnostic score-bucket distribution unavailable.")
    if p51c_cal.get("eligibility_availability") in {
        "not_provided",
        "unavailable_missing_candidate_pool",
        "unavailable_missing_upstream_contract",
        "unavailable_no_source_reads",
    }:
        warnings.append("P51-B eligibility calibration unavailable.")

    conclusion: list[str] = [
        "P58 Source-Backed Verifier Calibration v0 is a deterministic, aggregate-only planning-hint report.",
        "P58 does not read source files, candidate pools, prompts, responses, provider configs, or per-candidate rows.",
        "P58 does not call LLMs, providers, or networks, and does not construct prompts.",
        "P58 is not quality evidence, not a verifier pass/fail, not Evidence, not admission, and not default/promotion/live readiness.",
    ]
    if self_test:
        conclusion.append("This self-test exercised the calibration paths with synthetic upstream aggregate reports.")
    if blockers:
        conclusion.append(f"Calibration blocker(s): {len(blockers)}.")
    if warnings:
        conclusion.append(f"Calibration warning(s): {len(warnings)}.")
    conclusion.append(
        f"Current status: {status}. "
        f"Source-backed coverage bucket: {coverage.get('source_backed_coverage_bucket')}; "
        f"request-more-context hint: {rmc_cal.get('hint_bucket')}; "
        f"local-verifier priority hint: {lv_cal.get('hint_bucket')}; "
        f"P51-C eligibility hint: {p51c_cal.get('hint_bucket')}."
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": status_reason,
        "self_test": self_test,
        "not_quality_evidence": True,
        "real_evaluation": bool(status == "ok" and not self_test),
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "remote_calls_by_p58": 0,
        "llm_calls_by_p58": 0,
        "remote_requests_by_p58": 0,
        "prompt_construction_by_p58": False,
        "source_reads_attempted_by_p58": False,
        "provider_config_read_by_p58": False,
        "calibration_not_evidence": True,
        "action_hints_not_admission": True,
        "p52c_score_not_pass_fail": True,
        "p52c_score_not_evidence": True,
        "source_backed_not_verification": True,
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
        "calibration_denominators": denominators,
        "source_backed_coverage": coverage,
        "p52c_bucket_carry_forward": p52c_carry,
        "request_more_context_calibration": rmc_cal,
        "local_verifier_priority_calibration": lv_cal,
        "p51c_eligibility_calibration": p51c_cal,
        "warnings": warnings,
        "blockers": blockers,
        "conclusion": conclusion,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P58 public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    for flag, expected in [
        ("remote_calls_by_p58", 0),
        ("llm_calls_by_p58", 0),
        ("remote_requests_by_p58", 0),
    ]:
        if report.get(flag) != expected:
            errors.append(f"{flag} must be {expected}")
    for flag in ["prompt_construction_by_p58", "source_reads_attempted_by_p58", "provider_config_read_by_p58"]:
        if report.get(flag) is not False:
            errors.append(f"{flag} must be false")
    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "calibration_not_evidence": True,
        "action_hints_not_admission": True,
        "p52c_score_not_pass_fail": True,
        "p52c_score_not_evidence": True,
        "source_backed_not_verification": True,
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
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")
    if report.get("status") not in ALLOWED_STATUS:
        errors.append(f"status must be one of {ALLOWED_STATUS}")
    for block in [
        "input_summary",
        "upstream_safety_summary",
        "calibration_denominators",
        "source_backed_coverage",
        "p52c_bucket_carry_forward",
        "request_more_context_calibration",
        "local_verifier_priority_calibration",
        "p51c_eligibility_calibration",
        "warnings",
        "blockers",
        "validation",
    ]:
        if block not in report:
            errors.append(f"missing required block {block}")
    for forbidden in ("tasks", "records", "per_task_results", "per_candidate_results", "per_slice_rows"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")
    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_scan_values_for_leaks(report))
    return errors


def _fmt_scalar(x: Any) -> str:
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, int):
        return str(x)
    if x is None:
        return "n/a"
    return str(x)


def _fmt_bucket(bucket: str) -> str:
    return bucket.replace("_", " ")


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P58: {report['remote_calls_by_p58']}",
        f"- LLM calls by P58: {report['llm_calls_by_p58']}",
        f"- Prompt construction by P58: {report['prompt_construction_by_p58']}",
        f"- Source reads attempted by P58: {report['source_reads_attempted_by_p58']}",
        f"- Provider config read by P58: {report['provider_config_read_by_p58']}",
        "",
    ])

    lines.extend([
        "## Purpose",
        "",
        "P58 Source-Backed Verifier Calibration v0 consumes only public aggregate JSON reports from upstream diagnostics (P48, P52C, P51B, P57, and optionally P52B/P52A/P49) and turns their availability/distributions into coarse, deterministic planning/action-hint buckets. ",
        "It is **not** a verifier, **not** admission, **not** Evidence, **not** default/promotion, and **not** live-readiness evidence. ",
        "No source files, candidate pools, prompts, responses, provider configs, or per-candidate rows are read.",
        "",
        "## Methodology",
        "",
        "- Read only aggregate upstream report JSON (no `--input`, `--repo-lock`, `--source-root`, no provider/model/prompt arguments).",
        "- Required upstream reports: P48, P52C, P51B, P57.",
        "- Optional upstream reports: P52B, P52A, P49.",
        "- Collapse upstream statuses to an allowlisted safe enum.",
        "- Verify upstream safety flags where present: promotion/default false, `candidate_not_fact=true`, aggregate-only true, remote/LLM/prompt counters zero or bounded-source-reads only for source-read phases.",
        "- Extract only aggregate counts/rates from known paths; missing fields are `null` plus availability enum, never fake zeros.",
        "- Emit coarse hint buckets for request-more-context priority, local-verifier priority, and P51-C eligibility planning.",
        "",
        "## Safety notes",
        "",
        "- P58 makes no remote, LLM, or provider calls.",
        "- P58 does not construct prompts, read source files, or access candidate pools.",
        "- P58 does not publish task IDs, candidate IDs, repo IDs, datasets, paths, spans, line ranges, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.",
        "- P58 output is aggregate-only and explicitly flagged as not quality evidence, not a verifier pass/fail, not admission, and not default/promotion/live readiness.",
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
        f"- Invalid JSON upstream reports: {inp['invalid_json_count']}",
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
        f"- P57 `insufficient_matrix` acceptable: {sg['p57_insufficient_matrix_acceptable']}",
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

    cd = report["calibration_denominators"]
    lines.extend([
        "## Calibration denominators",
        "",
        f"- P52C candidate denominator: {_fmt_scalar(cd['p52c_candidate_denominator'])}",
        f"- P52C score candidate denominator: {_fmt_scalar(cd['p52c_score_candidate_denominator'])}",
        f"- P51B candidate denominator: {_fmt_scalar(cd['p51b_candidate_denominator'])}",
        f"- P51B eligible candidate count: {_fmt_scalar(cd['p51b_eligible_candidate_count'])}",
        f"- P48 selected count: {_fmt_scalar(cd['p48_selected_count'])}",
        f"- P48 request-more-context count: {_fmt_scalar(cd['p48_request_more_context_count'])}",
        f"- Calibration denominator availability: `{cd['calibration_denominator_available']}`",
        "",
    ])

    sbc = report["source_backed_coverage"]
    lines.extend([
        "## Source-backed coverage",
        "",
        f"- Source-backed coverage bucket: `{sbc['source_backed_coverage_bucket']}`",
        f"- P52C score availability: `{sbc['p52c_score_availability']}`",
        f"- Source-backed score candidate denominator: {_fmt_scalar(sbc['source_backed_score_candidate_denominator'])}",
        f"- Metadata-only candidate denominator: {_fmt_scalar(sbc['metadata_only_candidate_denominator'])}",
        f"- Score unavailable candidate rate: {_fmt_scalar(sbc['score_unavailable_candidate_rate'])}",
        f"- Source-backed is not verification: {sbc['source_backed_not_verification']}",
        "",
    ])

    p52c = report["p52c_bucket_carry_forward"]
    lines.extend([
        "## P52C bucket carry-forward",
        "",
        f"- Score bucket distribution available: {p52c['score_bucket_distribution_available']}",
        f"- Diagnostic score high rate: {_fmt_scalar(p52c['diagnostic_score_high_rate'])}",
        f"- Diagnostic score medium rate: {_fmt_scalar(p52c['diagnostic_score_medium_rate'])}",
        f"- Diagnostic score low rate: {_fmt_scalar(p52c['diagnostic_score_low_rate'])}",
        f"- Diagnostic score unavailable rate: {_fmt_scalar(p52c['diagnostic_score_unavailable_rate'])}",
        f"- P52C distribution is not pass/fail: {p52c['p52c_distribution_not_pass_fail']}",
        "",
    ])

    rmc = report["request_more_context_calibration"]
    lines.extend([
        "## Request-more-context calibration",
        "",
        f"- Hint bucket: `{rmc['hint_bucket']}`",
        f"- Request-more-context rate: {_fmt_scalar(rmc['request_more_context_rate'])}",
        f"- Demoted primary rate: {_fmt_scalar(rmc['demoted_primary_rate'])}",
        f"- P52C low/unavailable rate: {_fmt_scalar(rmc['p52c_low_or_unavailable_rate'])}",
        f"- Calibration basis: `{rmc['calibration_basis']}`",
        f"- Diagnostic only: {rmc['diagnostic_only']}",
        f"- Not admission: {rmc['not_admission']}",
        "",
    ])

    lvc = report["local_verifier_priority_calibration"]
    lines.extend([
        "## Local verifier priority calibration",
        "",
        f"- Hint bucket: `{lvc['hint_bucket']}`",
        f"- Source-backed coverage bucket: `{lvc['source_backed_coverage_bucket']}`",
        f"- Diagnostic score distribution available: {lvc['diagnostic_score_distribution_available']}",
        f"- Component coverage available: {lvc['component_coverage_available']}",
        f"- Diagnostic only: {lvc['diagnostic_only']}",
        f"- Not verifier pass/fail: {lvc['not_verifier_pass_fail']}",
        f"- Not admission: {lvc['not_admission']}",
        "",
    ])

    p51c = report["p51c_eligibility_calibration"]
    lines.extend([
        "## P51-C eligibility calibration",
        "",
        f"- Hint bucket: `{p51c['hint_bucket']}`",
        f"- Eligibility availability: `{p51c['eligibility_availability']}`",
        f"- Source-backed live eligibility available: {p51c['source_backed_live_eligibility_available']}",
        f"- Eligible candidate rate: {_fmt_scalar(p51c['eligible_candidate_rate'])}",
        f"- Request-envelope blueprint count: {_fmt_scalar(p51c['request_envelope_blueprint_count'])}",
        f"- Budget violation rate: {_fmt_scalar(p51c['budget_violation_rate'])}",
        f"- Redaction required rate: {_fmt_scalar(p51c['redaction_required_rate'])}",
        f"- Diagnostic only: {p51c['diagnostic_only']}",
        f"- Not live readiness: {p51c['not_live_readiness']}",
        f"- Not provider authorization flag set: {p51c['not_provider_authorization']}",
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
    parser.add_argument("--p48-report", type=Path, default=None, help="P48 aggregate report path.")
    parser.add_argument("--p52c-report", type=Path, default=None, help="P52C aggregate report path.")
    parser.add_argument("--p51b-report", type=Path, default=None, help="P51B aggregate report path.")
    parser.add_argument("--p57-report", type=Path, default=None, help="P57 aggregate report path.")
    parser.add_argument("--p52b-report", type=Path, default=None, help="Optional P52B aggregate report path.")
    parser.add_argument("--p52a-report", type=Path, default=None, help="Optional P52A aggregate report path.")
    parser.add_argument("--p49-report", type=Path, default=None, help="Optional P49 aggregate report path.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()

    if args.self_test:
        reports = _make_self_test_reports()
        # Exercise the missing-upstream path without writing it.
        missing_reports = dict(reports)
        missing_reports["p48"] = None
        missing_report = _build_report(missing_reports, self_test=False, elapsed_ms=0)
        if missing_report.get("status") != "insufficient_upstream":
            raise RuntimeError("P58 missing-upstream self-test path did not trigger insufficient_upstream")
        # Exercise a required-reports-present but partially available aggregate
        # path. P58 must degrade to partial calibration without fake zeroes.
        partial_reports = _make_self_test_reports()
        p52c_partial = dict(partial_reports["p52c"] or {})
        p52c_metrics = dict(p52c_partial.get("metrics") or {})
        p52c_metrics.pop("diagnostic_score_distribution", None)
        p52c_partial["metrics"] = p52c_metrics
        partial_reports["p52c"] = p52c_partial
        partial_report = _build_report(partial_reports, self_test=False, elapsed_ms=0)
        if partial_report.get("status") != "diagnostic_calibration_partial":
            raise RuntimeError("P58 partial-calibration self-test path did not trigger diagnostic_calibration_partial")
        if partial_report.get("p52c_bucket_carry_forward", {}).get("score_bucket_distribution_available") is not False:
            raise RuntimeError("P58 partial-calibration self-test did not preserve unavailable score distribution")
        # Exercise upstream aggregate-only contract violation path without writing it.
        unsafe_reports = _make_self_test_reports()
        unsafe_reports["p48"] = dict(unsafe_reports["p48"] or {}, tasks=[{"path": "src/private.py"}])
        unsafe_path = args.out.parent / "p58_unsafe_upstream_selftest_tmp.json"
        unsafe_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            unsafe_path.write_text(json.dumps(unsafe_reports["p48"]), encoding="utf-8")
            loaded = _read_aggregate_report(unsafe_path)
        finally:
            try:
                unsafe_path.unlink()
            except FileNotFoundError:
                pass
        if not (loaded and loaded.get("_aggregate_contract_violation")):
            raise RuntimeError("P58 upstream aggregate-only contract self-test did not detect forbidden private structure")
    else:
        reports = _load_reports_from_args(args)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    report = _build_report(reports, self_test=args.self_test, elapsed_ms=elapsed_ms)

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P58 report written to {args.out}")
    print(f"P58 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
