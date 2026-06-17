#!/usr/bin/env python3
"""P51-C0 Live LLM Micro-Run Planner / Explicit Opt-In Gate.

P51-C0 is a planner-only, explicit opt-in gate. It validates whether a future
P51-C live LLM micro-run may be manually launched, but it does NOT call
providers, construct prompts, read source, admit evidence, change defaults, or
authorize spend. It publishes only aggregate planning/gate information.

Hard constraints:
* No live LLM/provider calls; `remote_calls_by_p51c=0`, `llm_calls_by_p51c=0`,
  `remote_requests_by_p51c=0`.
* No prompt construction; `prompt_construction_by_p51c=false`.
* No raw request envelopes, prompts, outputs/responses, snippets, source text,
  queries, paths, spans, digests, providers, models, or keys in public artifacts.
* Aggregate-only public artifact; no per-task/per-candidate rows.
* Not quality evidence, not authorization, not live-readiness, not promotion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "p51c-live-micro-run-planner-v0"
GENERATED_BY = "p51c_live_micro_run_planner.py"
STAGE = "P51-C0 Live LLM Micro-Run Planner / Explicit Opt-In Gate"

DEFAULT_OUT = Path("artifacts/p51c_live_micro_run_planner/p51c_live_micro_run_planner_report.json")
DEFAULT_DOC = Path("docs/en/p51c-live-micro-run-planner.md")

REQUIRED_ACK = "I_UNDERSTAND_P51C_NOT_EVIDENCE"

ALLOWED_DATASETS = {"self_test", "ci_smoke"}
ALLOWED_REPOS = {"py_flask", "js_express", "go_gin", "rust_ripgrep"}
ALLOWED_OUTPUT_MODES_PLANNER_READY = {"json_schema_strict", "tool_call"}
ALLOWED_STATUS = {
    "self_test_only",
    "planner_ready",
    "blocked_missing_opt_in",
    "blocked_preconditions",
    "blocked_privacy",
    "blocked_budget",
    "blocked_schema_contract",
    "blocked_provider_config",
    "blocked_safety",
}

PLANNER_CONFIG_KEYS = {
    "ack_not_evidence",
    "dataset",
    "llm_output_mode",
    "max_candidates_per_request",
    "max_output_chars",
    "max_remote_calls_total",
    "max_request_chars",
    "max_total_lines_per_request",
    "p51c_live_opt_in",
    "repo_scope",
    "timeout_seconds",
}

# Keys that must never appear in the public artifact (values are also scanned).
FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "candidate_id",
    "repo_id",
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
    "model",
    "model_id",
    "provider",
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
    "candidate",
    "candidates",
}

# Keys that are intentionally public safety flags or aggregate-only metric names.
P51C_SAFETY_FLAG_KEYS = {
    # schema / status
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    # top-level safety flags
    "not_quality_evidence",
    "planner_only",
    "p51c_live_calls_disabled",
    "provider_spend_authorized",
    "live_run_authorized",
    "llm_calls_by_p51c",
    "remote_calls_by_p51c",
    "remote_requests_by_p51c",
    "prompt_construction_by_p51c",
    "raw_request_envelopes_stored",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_query_stored",
    "raw_text_stored",
    "raw_source_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "private_labels_committed",
    "gold_spans_in_artifact",
    "candidate_not_fact",
    "llm_output_not_evidence",
    "evidence_admission_performed",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "aggregate_only_public_artifact",
    # blocks
    "input_summary",
    "p61_input_summary",
    "p51b_input_summary",
    "gate_checks",
    "budget_check",
    "planner_config",
    "conclusion",
    "validation",
    # input_summary
    "report_present",
    "status",
    "micro_run_preconditions_met",
    "decision_is_authorization",
    "requires_separate_dispatch",
    "schema_valid",
    "self_test_flag_absent",
    "p61_safety_flags_ok",
    "p51b_live_gate_ready",
    "p51b_live_gate_ready_reason",
    "eligible_candidate_count",
    "eligible_pack_count",
    "request_envelope_blueprint_count",
    "source_backed_live_eligibility_available",
    "role_output_schema_valid_rate",
    "role_output_schema_invalid_reject_rate",
    "role_output_schema_invalid_rejected",
    "unknown_field_reject_count",
    "not_evidence_missing_reject_count",
    "redaction_policy_precondition_satisfied",
    "redaction_policy_consistent",
    "runtime_redaction_still_required_by_p51c",
    "eligibility_availability",
    "p51b_safety_flags_ok",
    "p51b_dry_run_contract_ok",
    "p51b_budget_violations_absent",
    # gate_checks
    "opt_in_present",
    "ack_required_matches",
    "dataset_allowed",
    "repo_in_allowlist",
    "output_mode_allowed",
    "p61_report_present",
    "p51b_report_present",
    "p61_preconditions_met",
    "p51b_contract_ready",
    "p51b_budget_caps_respected",
    "provider_config_safe",
    # budget_check
    "requested_max_remote_calls_total",
    "requested_max_request_chars",
    "requested_max_output_chars",
    "requested_max_candidates_per_request",
    "requested_max_total_lines_per_request",
    "requested_timeout_seconds",
    "p51b_max_remote_calls_future_cap",
    "p51b_max_request_chars_future_cap",
    "p51b_max_output_chars_future_cap",
    "p51b_max_candidates_per_request",
    "p51b_max_total_lines_per_request",
    "p51b_timeout_seconds_future_cap",
    "budget_reasons",
    # planner_config
    "p51c_live_opt_in",
    "ack_not_evidence",
    "dataset",
    "llm_output_mode",
    "max_remote_calls_total",
    "max_request_chars",
    "max_output_chars",
    "max_candidates_per_request",
    "max_total_lines_per_request",
    "timeout_seconds",
    "repo_scope",
    "allowed_output_modes",
    "allowed_datasets",
    # validation
    "forbidden_key_scan_ok",
    "value_leak_scan_ok",
    "forbidden_claims_scan_ok",
    # common helpers
    "count",
    "rate",
    "value",
}

BANNED_VALUE_SUBSTRINGS = [
    "base_url",
    "api_key",
    "api_token",
    "provider_key",
    "sk-",
    "://",
]


@dataclass(frozen=True)
class PlannerConfig:
    live_opt_in: bool
    ack_not_evidence: str
    dataset: str
    repo_id: str
    max_remote_calls_total: int
    max_request_chars: int
    max_output_chars: int
    max_candidates_per_request: int
    max_total_lines_per_request: int
    timeout_seconds: int
    llm_output_mode: str


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


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P51C_SAFETY_FLAG_KEYS:
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
        if not text:
            return violations
        # Absolute path
        if len(text) > 1 and (text.startswith("/") or text.startswith("\\")):
            violations.append(prefix + " looks like an absolute path")
            return violations
        # URL-like
        if "://" in text:
            violations.append(prefix + " looks like a URL")
            return violations
        # API key
        if re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
            violations.append(prefix + " looks like an API key")
            return violations
        # Relative path-like strings that may expose repo layout
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
        # Disallowed secret/config substrings
        lower = text.lower()
        for bad in BANNED_VALUE_SUBSTRINGS:
            if bad in lower:
                violations.append(prefix + f" contains disallowed substring {bad!r}")
                return violations
    return violations


def _scan_forbidden_claims(report: dict[str, Any]) -> list[str]:
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
    for field in ("status_reason", "conclusion"):
        val = report.get(field)
        if isinstance(val, str):
            text_fields.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    text_fields.append(item)
    rd = report.get("readiness_decision")
    if isinstance(rd, dict):
        reasons = rd.get("reasons") or []
        if isinstance(reasons, list):
            for item in reasons:
                if isinstance(item, str):
                    text_fields.append(item)
    violations: list[str] = []
    for text in text_fields:
        lower = text.lower()
        for claim in forbidden_claims:
            negated = f"not {claim}"
            if claim in lower and negated not in lower:
                violations.append(f"forbidden claim in text: {claim}")
    return violations


def _read_aggregate_report(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_invalid": True, "status": "invalid_json"}
    if not isinstance(data, dict):
        return {"_invalid": True, "status": "invalid_json"}
    return data


def _coerce_config(args: argparse.Namespace) -> PlannerConfig:
    return PlannerConfig(
        live_opt_in=args.p51c_live_opt_in,
        ack_not_evidence=args.ack_not_evidence or "",
        dataset=args.dataset,
        repo_id=args.repo_id,
        max_remote_calls_total=_as_int(args.max_remote_calls_total) or 0,
        max_request_chars=_as_int(args.max_request_chars) or 0,
        max_output_chars=_as_int(args.max_output_chars) or 0,
        max_candidates_per_request=_as_int(args.max_candidates_per_request) or 0,
        max_total_lines_per_request=_as_int(args.max_total_lines_per_request) or 0,
        timeout_seconds=_as_int(args.timeout_seconds) or 0,
        llm_output_mode=args.llm_output_mode,
    )


def _p61_summary(p61: dict[str, Any] | None) -> dict[str, Any]:
    if not p61:
        return {"report_present": False, "status": "not_provided"}
    rd = p61.get("readiness_decision") or {}
    p61_safety_flags_ok = (
        p61.get("schema_version") == "p61-pre-spend-gate-v0"
        and p61.get("self_test") is False
        and p61.get("not_quality_evidence") is True
        and p61.get("aggregate_only_public_artifact") is True
        and p61.get("candidate_not_fact") is True
        and p61.get("remote_calls_by_p61") == 0
        and p61.get("llm_calls_by_p61") == 0
        and p61.get("remote_requests_by_p61") == 0
        and p61.get("prompt_construction_by_p61") is False
        and p61.get("provider_config_read_by_p61") is False
        and p61.get("source_reads_attempted_by_p61") is False
        and p61.get("provider_spend_authorized") is False
        and p61.get("evidence_admission_performed") is False
        and p61.get("promotion_ready") is False
        and p61.get("default_should_change") is False
        and p61.get("evidencecore_semantics_changed") is False
        and p61.get("provider_keys_in_artifact") is False
        and p61.get("raw_prompts_stored") is False
        and p61.get("raw_responses_stored") is False
        and p61.get("raw_snippets_stored") is False
        and p61.get("raw_snippets_committed") is False
        and p61.get("raw_snippets_sent_to_provider") is False
        and p61.get("raw_query_stored") is False
        and p61.get("raw_text_stored") is False
        and p61.get("raw_source_stored") is False
        and p61.get("raw_paths_in_artifact") is False
        and p61.get("raw_line_ranges_in_artifact") is False
        and p61.get("raw_digests_in_artifact") is False
        and p61.get("private_labels_committed") is False
        and p61.get("gold_spans_in_artifact") is False
    )
    return {
        "report_present": True,
        "status": p61.get("status") or "not_provided",
        "schema_valid": p61.get("schema_version") == "p61-pre-spend-gate-v0",
        "self_test_flag_absent": p61.get("self_test") is False,
        "micro_run_preconditions_met": p61.get("status") == "micro_run_preconditions_met",
        "provider_spend_authorized": bool(rd.get("provider_spend_authorized")),
        "decision_is_authorization": bool(rd.get("decision_is_authorization")),
        "requires_separate_dispatch": bool(rd.get("requires_separate_human_or_workflow_dispatch")),
        "p61_safety_flags_ok": p61_safety_flags_ok,
    }


def _p51b_summary(p51b: dict[str, Any] | None) -> dict[str, Any]:
    if not p51b:
        return {"report_present": False, "status": "not_provided"}
    metrics = p51b.get("metrics") or {}
    gate = metrics.get("future_live_gate_readiness") or {}
    elig = metrics.get("eligibility") or {}
    blueprint = metrics.get("request_envelope_blueprint") or {}
    schema = metrics.get("role_output_schema_validation") or {}
    redaction_count = _as_int(blueprint.get("redaction_required_count"))
    redaction_rate = _as_float(blueprint.get("redaction_required_rate"))
    redaction_required_flag = blueprint.get("redaction_policy_required")
    redaction_status = blueprint.get("redaction_policy_status")
    redaction_policy_consistent = False
    if redaction_status == "not_required":
        redaction_policy_consistent = (
            redaction_required_flag is False
            and redaction_count == 0
            and redaction_rate == 0.0
        )
    elif redaction_status == "required_defined_satisfied":
        redaction_policy_consistent = (
            redaction_required_flag is True
            and redaction_count is not None
            and redaction_count > 0
            and redaction_rate is not None
            and redaction_rate > 0.0
        )
    budget_violation_count = _as_int(blueprint.get("max_budget_violation_count"))
    budget_violation_rate = _as_float(blueprint.get("max_budget_violation_rate"))
    invalid_reject_count = _as_int(schema.get("role_output_schema_invalid_reject_count"))
    invalid_reject_rate = _as_float(schema.get("role_output_schema_invalid_reject_rate"))
    unknown_field_reject_count = _as_int(schema.get("unknown_field_reject_count"))
    not_evidence_missing_reject_count = _as_int(schema.get("not_evidence_missing_reject_count"))
    p51b_safety_flags_ok = (
        p51b.get("schema_version") == "p51b-llm-opt-in-contract-v1"
        and p51b.get("status") == "ok"
        and p51b.get("self_test") is False
        and p51b.get("aggregate_only_public_artifact") is True
        and p51b.get("candidate_not_fact") is True
        and p51b.get("llm_output_not_evidence") is True
        and p51b.get("remote_calls_by_p51b") == 0
        and p51b.get("llm_calls_by_p51b") == 0
        and p51b.get("remote_requests_by_p51b") == 0
        and p51b.get("prompt_construction_by_p51b") is False
        and p51b.get("dry_run_payload_validation_only") is True
        and p51b.get("p51b_live_calls_disabled") is True
        and p51b.get("provider_keys_in_artifact") is False
        and p51b.get("raw_request_envelopes_stored") is False
        and p51b.get("raw_prompts_stored") is False
        and p51b.get("raw_outputs_stored") is False
        and p51b.get("raw_responses_stored") is False
        and p51b.get("raw_snippets_stored") is False
        and p51b.get("raw_snippets_committed") is False
        and p51b.get("raw_snippets_sent_to_provider") is False
        and p51b.get("raw_query_stored") is False
        and p51b.get("raw_text_stored") is False
        and p51b.get("raw_source_stored") is False
        and p51b.get("raw_paths_in_artifact") is False
        and p51b.get("raw_line_ranges_in_artifact") is False
        and p51b.get("raw_digests_in_artifact") is False
        and p51b.get("private_labels_committed") is False
        and p51b.get("gold_spans_in_artifact") is False
        and p51b.get("promotion_ready") is False
        and p51b.get("default_should_change") is False
        and p51b.get("evidencecore_semantics_changed") is False
    )
    return {
        "report_present": True,
        "status": p51b.get("status") or "not_provided",
        "p51b_live_gate_ready": bool(gate.get("p51b_live_gate_ready")),
        "p51b_live_gate_ready_reason": gate.get("p51b_live_gate_ready_reason") or "missing",
        "eligible_candidate_count": _as_int(elig.get("eligible_candidate_count")) or 0,
        "eligible_pack_count": _as_int(elig.get("eligible_pack_count")) or 0,
        "request_envelope_blueprint_count": _as_int(blueprint.get("request_envelope_blueprint_count")) or 0,
        "eligibility_availability": elig.get("eligibility_availability") or "missing",
        "source_backed_live_eligibility_available": bool(elig.get("source_backed_live_eligibility_available")),
        "role_output_schema_valid_rate": _as_float(schema.get("role_output_schema_valid_rate")),
        "role_output_schema_invalid_reject_rate": invalid_reject_rate,
        "role_output_schema_invalid_rejected": invalid_reject_count is not None and invalid_reject_count > 0 and invalid_reject_rate == 1.0,
        "unknown_field_reject_count": unknown_field_reject_count or 0,
        "not_evidence_missing_reject_count": not_evidence_missing_reject_count or 0,
        "redaction_policy_precondition_satisfied": blueprint.get("redaction_policy_precondition_satisfied") is True,
        "redaction_policy_consistent": redaction_policy_consistent,
        "runtime_redaction_still_required_by_p51c": blueprint.get("runtime_redaction_still_required_by_p51c") is True,
        "p51b_safety_flags_ok": p51b_safety_flags_ok,
        "p51b_dry_run_contract_ok": p51b.get("dry_run_payload_validation_only") is True and p51b.get("p51b_live_calls_disabled") is True,
        "p51b_budget_violations_absent": budget_violation_count == 0 and budget_violation_rate == 0.0,
    }


def evaluate_plan(
    reports: dict[str, dict[str, Any] | None],
    config: PlannerConfig,
    *,
    self_test: bool,
) -> tuple[str, list[str], dict[str, Any], dict[str, int], dict[str, int | None]]:
    """Return (status, reasons, gate_checks, requested_caps, p51b_caps)."""
    p61 = reports.get("p61") or {}
    p51b = reports.get("p51b") or {}

    p61_present = bool(p61 and not p61.get("_invalid"))
    p51b_present = bool(p51b and not p51b.get("_invalid"))

    p61_summary = _p61_summary(p61 if p61_present else None)
    p51b_summary = _p51b_summary(p51b if p51b_present else None)

    checks: dict[str, Any] = {
        "opt_in_present": bool(config.live_opt_in),
        "ack_required_matches": config.ack_not_evidence == REQUIRED_ACK,
        "dataset_allowed": config.dataset in ALLOWED_DATASETS,
        "repo_in_allowlist": config.repo_id in ALLOWED_REPOS,
        "output_mode_allowed": config.llm_output_mode in ALLOWED_OUTPUT_MODES_PLANNER_READY,
        "p61_report_present": p61_present,
        "p51b_report_present": p51b_present,
    }

    # P61 readiness
    p61_pre = (
        p61_present
        and p61_summary["schema_valid"]
        and p61_summary["self_test_flag_absent"]
        and p61_summary["micro_run_preconditions_met"]
        and not p61_summary["decision_is_authorization"]
        and not p61_summary["provider_spend_authorized"]
        and p61_summary["requires_separate_dispatch"]
        and p61_summary["p61_safety_flags_ok"]
    )
    checks["p61_preconditions_met"] = p61_pre

    # P51-B contract readiness
    p51b_contract_ready = False
    if p51b_present:
        p51b_contract_ready = (
            p51b_summary["p51b_live_gate_ready"]
            and p51b_summary["p51b_live_gate_ready_reason"] == "contract_valid_dry_run_only"
            and p51b_summary["eligible_candidate_count"] > 0
            and p51b_summary["eligible_pack_count"] > 0
            and p51b_summary["request_envelope_blueprint_count"] > 0
            and p51b_summary["eligibility_availability"] == "available_source_backed"
            and p51b_summary["source_backed_live_eligibility_available"]
            and p51b_summary["role_output_schema_valid_rate"] == 1.0
            and p51b_summary["role_output_schema_invalid_rejected"]
            and p51b_summary["unknown_field_reject_count"] > 0
            and p51b_summary["not_evidence_missing_reject_count"] > 0
            and p51b_summary["redaction_policy_precondition_satisfied"]
            and p51b_summary["redaction_policy_consistent"]
            and p51b_summary["runtime_redaction_still_required_by_p51c"]
            and p51b_summary["p51b_safety_flags_ok"]
            and p51b_summary["p51b_dry_run_contract_ok"]
            and p51b_summary["p51b_budget_violations_absent"]
        )
    checks["p51b_contract_ready"] = p51b_contract_ready

    # Budget caps from P51-B contract manifest
    p51b_metrics = p51b.get("metrics") or {} if p51b_present else {}
    manifest = p51b_metrics.get("contract_manifest") or {}
    p51b_caps: dict[str, int | None] = {
        "max_remote_calls_total": _as_int(manifest.get("max_remote_calls_future_cap")),
        "max_request_chars": _as_int(manifest.get("max_request_chars_future_cap")),
        "max_output_chars": _as_int(manifest.get("max_output_chars_future_cap")),
        "max_candidates_per_request": _as_int(manifest.get("max_candidates_per_request")),
        "max_total_lines_per_request": _as_int(manifest.get("max_total_lines_per_request")),
        "timeout_seconds": _as_int(manifest.get("timeout_seconds_future_cap")),
    }
    requested: dict[str, int] = {
        "max_remote_calls_total": config.max_remote_calls_total,
        "max_request_chars": config.max_request_chars,
        "max_output_chars": config.max_output_chars,
        "max_candidates_per_request": config.max_candidates_per_request,
        "max_total_lines_per_request": config.max_total_lines_per_request,
        "timeout_seconds": config.timeout_seconds,
    }
    budget_reasons: list[str] = []
    budget_ok = True
    for key, val in requested.items():
        cap = p51b_caps.get(key)
        if cap is None:
            budget_ok = False
            budget_reasons.append(f"missing_p51b_cap:{key}")
        elif val > cap:
            budget_ok = False
            budget_reasons.append(f"{key}_exceeds_p51b_cap")
    if requested["max_remote_calls_total"] != 1:
        budget_ok = False
        budget_reasons.append("max_remote_calls_total_must_be_1")
    checks["p51b_budget_caps_respected"] = budget_ok

    provider_config_safe = not (
        bool(p61.get("provider_keys_in_artifact"))
        or bool(p51b.get("provider_keys_in_artifact"))
    )
    checks["provider_config_safe"] = provider_config_safe

    reasons: list[str] = [
        f"opt_in={config.live_opt_in}",
        f"ack_matches={checks['ack_required_matches']}",
        f"dataset={config.dataset}",
        f"repo_in_allowlist={checks['repo_in_allowlist']}",
        f"output_mode_allowed={checks['output_mode_allowed']}",
        f"p61_present={p61_present}",
        f"p61_preconditions_met={p61_pre}",
        f"p51b_present={p51b_present}",
        f"p51b_contract_ready={p51b_contract_ready}",
        f"budget_ok={budget_ok}",
    ]

    if self_test:
        if not checks["opt_in_present"] or not checks["ack_required_matches"]:
            status = "blocked_missing_opt_in"
        elif not checks["dataset_allowed"]:
            status = "blocked_preconditions"
        elif not checks["output_mode_allowed"]:
            status = "blocked_schema_contract"
        elif not checks["repo_in_allowlist"]:
            status = "blocked_preconditions"
        elif not p61_present:
            status = "blocked_preconditions"
        elif not p51b_present:
            status = "blocked_schema_contract"
        elif not p61_pre:
            status = "blocked_preconditions"
        elif not p51b_contract_ready:
            if not p51b_summary["redaction_policy_precondition_satisfied"] or not p51b_summary["redaction_policy_consistent"] or not p51b_summary["runtime_redaction_still_required_by_p51c"]:
                status = "blocked_privacy"
            else:
                status = "blocked_schema_contract"
        elif not budget_ok:
            status = "blocked_budget"
        elif not provider_config_safe:
            status = "blocked_provider_config"
        else:
            status = "self_test_only"
    else:
        if not checks["opt_in_present"] or not checks["ack_required_matches"]:
            status = "blocked_missing_opt_in"
        elif not checks["dataset_allowed"] or config.dataset != "ci_smoke":
            status = "blocked_preconditions"
        elif not checks["repo_in_allowlist"]:
            status = "blocked_preconditions"
        elif not checks["output_mode_allowed"]:
            status = "blocked_schema_contract"
        elif not p61_present:
            status = "blocked_preconditions"
        elif not p51b_present:
            status = "blocked_schema_contract"
        elif not p61_pre:
            status = "blocked_preconditions"
        elif not p51b_contract_ready:
            if not p51b_summary["redaction_policy_precondition_satisfied"] or not p51b_summary["redaction_policy_consistent"] or not p51b_summary["runtime_redaction_still_required_by_p51c"]:
                status = "blocked_privacy"
            else:
                status = "blocked_schema_contract"
        elif not budget_ok:
            status = "blocked_budget"
        elif not provider_config_safe:
            status = "blocked_provider_config"
        else:
            status = "planner_ready"

    return status, reasons, checks, requested, p51b_caps


def build_report(
    reports: dict[str, dict[str, Any] | None],
    config: PlannerConfig,
    *,
    self_test: bool,
    elapsed_ms: int,
) -> dict[str, Any]:
    status, reasons, checks, requested, p51b_caps = evaluate_plan(
        reports, config, self_test=self_test
    )

    if self_test:
        status = "self_test_only"
        status_reason = "Self-test-only planner/gate validation; not quality evidence, not authorization, and not live readiness."
    else:
        status_reason = "; ".join(reasons) if reasons else "planner evaluation complete"

    repo_scope = "public_ci_smoke_allowlist" if config.repo_id in ALLOWED_REPOS else "not_in_allowlist"

    planner_config = {
        "p51c_live_opt_in": config.live_opt_in,
        "ack_not_evidence": config.ack_not_evidence,
        "dataset": config.dataset,
        "repo_scope": repo_scope,
        "llm_output_mode": config.llm_output_mode,
        "max_remote_calls_total": config.max_remote_calls_total,
        "max_request_chars": config.max_request_chars,
        "max_output_chars": config.max_output_chars,
        "max_candidates_per_request": config.max_candidates_per_request,
        "max_total_lines_per_request": config.max_total_lines_per_request,
        "timeout_seconds": config.timeout_seconds,
        "allowed_output_modes": sorted(ALLOWED_OUTPUT_MODES_PLANNER_READY),
        "allowed_datasets": sorted(ALLOWED_DATASETS),
    }

    budget_check: dict[str, Any] = {
        "requested_max_remote_calls_total": requested["max_remote_calls_total"],
        "requested_max_request_chars": requested["max_request_chars"],
        "requested_max_output_chars": requested["max_output_chars"],
        "requested_max_candidates_per_request": requested["max_candidates_per_request"],
        "requested_max_total_lines_per_request": requested["max_total_lines_per_request"],
        "requested_timeout_seconds": requested["timeout_seconds"],
        "p51b_max_remote_calls_future_cap": p51b_caps["max_remote_calls_total"],
        "p51b_max_request_chars_future_cap": p51b_caps["max_request_chars"],
        "p51b_max_output_chars_future_cap": p51b_caps["max_output_chars"],
        "p51b_max_candidates_per_request": p51b_caps["max_candidates_per_request"],
        "p51b_max_total_lines_per_request": p51b_caps["max_total_lines_per_request"],
        "p51b_timeout_seconds_future_cap": p51b_caps["timeout_seconds"],
    }
    _status, _reasons, _checks, _requested, _caps = evaluate_plan(
        reports, config, self_test=False
    )
    budget_check["budget_reasons"] = []
    for key, val in _requested.items():
        cap = _caps.get(key)
        if cap is None:
            budget_check["budget_reasons"].append(f"missing_p51b_cap:{key}")
        elif val > cap:
            budget_check["budget_reasons"].append(f"{key}_exceeds_p51b_cap")
    if _requested.get("max_remote_calls_total") != 1:
        budget_check["budget_reasons"].append("max_remote_calls_total_must_be_1")

    conclusion: list[str] = [
        "P51-C0 Live LLM Micro-Run Planner is a planner-only explicit opt-in gate.",
        "P51-C0 does not call providers, does not construct prompts, does not read source, and does not authorize spend.",
        "P51-C0 is not quality evidence, not Evidence, not authorization, not default/promotion, and not live readiness.",
        "A future P51-C live LLM micro-run remains a separate explicit human or workflow_dispatch decision.",
    ]
    if self_test:
        conclusion.append("This self-test exercised the planning/gate logic with synthetic aggregate inputs.")
    if status == "planner_ready":
        conclusion.append("Planner-ready flag is set only as an aggregate precondition signal; live run authorization flag remains false.")
    conclusion.append(f"Current planner status: {status}.")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": status_reason,
        "self_test": self_test,
        "not_quality_evidence": True,
        "planner_only": True,
        "p51c_live_calls_disabled": True,
        "provider_spend_authorized": False,
        "live_run_authorized": False,
        "llm_calls_by_p51c": 0,
        "remote_calls_by_p51c": 0,
        "remote_requests_by_p51c": 0,
        "prompt_construction_by_p51c": False,
        "raw_request_envelopes_stored": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_query_stored": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "provider_keys_in_artifact": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "evidence_admission_performed": False,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "aggregate_only_public_artifact": True,
        "elapsed_ms": elapsed_ms,
        "input_summary": {
            "p61_input_summary": _p61_summary(reports.get("p61")),
            "p51b_input_summary": _p51b_summary(reports.get("p51b")),
        },
        "gate_checks": checks,
        "budget_check": budget_check,
        "planner_config": planner_config,
        "conclusion": conclusion,
        "validation": {
            "forbidden_key_scan_ok": True,
            "value_leak_scan_ok": True,
            "forbidden_claims_scan_ok": True,
        },
    }

    errors = validate_report(report)
    if errors:
        raise RuntimeError(f"P51-C0 public report validation failed: {errors}")
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
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
        ("remote_calls_by_p51c", 0),
        ("llm_calls_by_p51c", 0),
        ("remote_requests_by_p51c", 0),
    ]:
        if report.get(flag) != expected:
            errors.append(f"{flag} must be {expected}")

    for flag in [
        "prompt_construction_by_p51c",
        "provider_spend_authorized",
        "live_run_authorized",
        "evidence_admission_performed",
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "raw_request_envelopes_stored",
        "raw_prompts_stored",
        "raw_responses_stored",
        "raw_snippets_stored",
        "raw_snippets_committed",
        "raw_snippets_sent_to_provider",
        "raw_query_stored",
        "raw_text_stored",
        "raw_source_stored",
        "raw_paths_in_artifact",
        "raw_line_ranges_in_artifact",
        "raw_digests_in_artifact",
        "provider_keys_in_artifact",
        "private_labels_committed",
        "gold_spans_in_artifact",
    ]:
        if report.get(flag) is not False:
            errors.append(f"{flag} must be false")

    for flag in [
        "not_quality_evidence",
        "planner_only",
        "p51c_live_calls_disabled",
        "candidate_not_fact",
        "llm_output_not_evidence",
        "aggregate_only_public_artifact",
    ]:
        if report.get(flag) is not True:
            errors.append(f"{flag} must be true")

    if report.get("self_test") and report.get("status") != "self_test_only":
        errors.append("self_test must set status=self_test_only")
    if report.get("status") == "self_test_only" and report.get("self_test") is not True:
        errors.append("status self_test_only requires self_test=true")
    if report.get("status") == "planner_ready" and report.get("self_test"):
        errors.append("self_test must not emit planner_ready")

    for forbidden in ("tasks", "records", "per_task_results", "per_candidate_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_scan_values_for_leaks(report))
    errors.extend(_scan_forbidden_claims(report))

    # Validate planner_config does not expose raw repo identity.
    pc = report.get("planner_config") or {}
    if pc.get("repo_scope") not in {"public_ci_smoke_allowlist", "not_in_allowlist"}:
        errors.append("planner_config.repo_scope invalid")
    if "repo_id" in pc:
        errors.append("planner_config must not contain raw repo_id")
    if pc.get("p51c_live_opt_in") not in (True, False):
        errors.append("planner_config.p51c_live_opt_in must be boolean")

    return errors


def _fmt_scalar(x: Any) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, bool):
        return str(x).lower()
    return str(x)


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Planner only: {report['planner_only']}",
        f"- P51-C live calls disabled: {report['p51c_live_calls_disabled']}",
        f"- Remote calls by P51-C: {report['remote_calls_by_p51c']}",
        f"- LLM calls by P51-C: {report['llm_calls_by_p51c']}",
        f"- Remote requests by P51-C: {report['remote_requests_by_p51c']}",
        f"- Prompt construction by P51-C: {report['prompt_construction_by_p51c']}",
        f"- Provider spend authorization flag: {report['provider_spend_authorized']}",
        f"- Live run authorization flag: {report['live_run_authorized']}",
        "",
    ])

    lines.extend([
        "## Purpose",
        "",
        "P51-C0 is a planner-only explicit opt-in gate. It validates whether a future P51-C live LLM micro-run may be manually launched. ",
        "It is **not** quality evidence, **not** authorization, **not** Evidence, **not** a promotion/default gate, and **not** a claim that a live run is safe or ready.",
        "No provider calls, prompt construction, source reads, ephemeral record reads, or spend authorization are performed.",
        "",
        "## Methodology",
        "",
        "- Require `--p51c-live-opt-in` and a matching `--ack-not-evidence` string.",
        "- Read only aggregate upstream reports (`--p61-report`, `--p51b-report`).",
        "- Confirm P61 status is `micro_run_preconditions_met`, provider spend is not authorized, the decision is not authorization, and a separate dispatch is required.",
        "- Confirm P51-B contract readiness, source-backed eligibility, role-output schema validity, and redaction preconditions are satisfied.",
        "- Validate requested budget caps do not exceed the P51-B dry-run contract caps and that exactly one remote call is planned.",
        "- Confirm the output mode is `json_schema_strict` or `tool_call` and the dataset/repo are within allowlists.",
        "- Emit an aggregate planner config that uses `repo_scope='public_ci_smoke_allowlist'` and never exposes raw repo identity, paths, spans, prompts, responses, providers, models, or keys.",
        "",
        "## Safety notes",
        "",
        "- P51-C0 makes no remote, LLM, or provider calls.",
        "- P51-C0 does not construct prompts, read source files, or access ephemeral records.",
        "- P51-C0 does not publish task IDs, candidate IDs, repo IDs, paths, spans, line ranges, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.",
        "- P51-C0 output is aggregate-only and explicitly flagged as not quality evidence, not authorization, not Evidence, and not default/promotion/live readiness.",
        "",
    ])

    inp = report["input_summary"]
    p61_in = inp["p61_input_summary"]
    p51b_in = inp["p51b_input_summary"]
    lines.extend([
        "## Input summary",
        "",
        f"- P61 report present: {p61_in['report_present']}",
        f"- P61 status: `{p61_in.get('status', 'n/a')}`",
        f"- P61 preconditions met: {p61_in.get('micro_run_preconditions_met', False)}",
        f"- P51-B report present: {p51b_in['report_present']}",
        f"- P51-B status: `{p51b_in.get('status', 'n/a')}`",
        f"- P51-B live gate ready: {p51b_in.get('p51b_live_gate_ready', False)}",
        f"- P51-B live gate ready reason: `{p51b_in.get('p51b_live_gate_ready_reason', 'n/a')}`",
        f"- P51-B eligible candidates: {p51b_in.get('eligible_candidate_count', 0)}",
        f"- P51-B eligible packs: {p51b_in.get('eligible_pack_count', 0)}",
        f"- P51-B blueprint count: {p51b_in.get('request_envelope_blueprint_count', 0)}",
        f"- P51-B source-backed eligibility available: {p51b_in.get('source_backed_live_eligibility_available', False)}",
        f"- P51-B schema valid rate: {_fmt_scalar(p51b_in.get('role_output_schema_valid_rate'))}",
        f"- P51-B redaction precondition satisfied: {p51b_in.get('redaction_policy_precondition_satisfied', False)}",
        f"- P51-B redaction policy consistent: {p51b_in.get('redaction_policy_consistent', False)}",
        f"- P51-B runtime redaction still required by P51-C: {p51b_in.get('runtime_redaction_still_required_by_p51c', False)}",
        "",
    ])

    gc = report["gate_checks"]
    lines.extend([
        "## Gate checks",
        "",
        f"- Explicit opt-in present: {gc.get('opt_in_present', False)}",
        f"- Acknowledgement matches required string: {gc.get('ack_required_matches', False)}",
        f"- Dataset allowed: {gc.get('dataset_allowed', False)}",
        f"- Repo in allowlist: {gc.get('repo_in_allowlist', False)}",
        f"- Output mode allowed: {gc.get('output_mode_allowed', False)}",
        f"- P61 report present: {gc.get('p61_report_present', False)}",
        f"- P61 preconditions met: {gc.get('p61_preconditions_met', False)}",
        f"- P51-B report present: {gc.get('p51b_report_present', False)}",
        f"- P51-B contract ready: {gc.get('p51b_contract_ready', False)}",
        f"- P51-B budget caps respected: {gc.get('p51b_budget_caps_respected', False)}",
        f"- Provider config safe: {gc.get('provider_config_safe', False)}",
        "",
    ])

    bc = report["budget_check"]
    lines.extend([
        "## Budget check",
        "",
        f"- Requested max remote calls total: {bc['requested_max_remote_calls_total']} (P51-B cap: {_fmt_scalar(bc['p51b_max_remote_calls_future_cap'])}, must equal 1)",
        f"- Requested max request chars: {bc['requested_max_request_chars']} (P51-B cap: {_fmt_scalar(bc['p51b_max_request_chars_future_cap'])})",
        f"- Requested max output chars: {bc['requested_max_output_chars']} (P51-B cap: {_fmt_scalar(bc['p51b_max_output_chars_future_cap'])})",
        f"- Requested max candidates per request: {bc['requested_max_candidates_per_request']} (P51-B cap: {_fmt_scalar(bc['p51b_max_candidates_per_request'])})",
        f"- Requested max total lines per request: {bc['requested_max_total_lines_per_request']} (P51-B cap: {_fmt_scalar(bc['p51b_max_total_lines_per_request'])})",
        f"- Requested timeout seconds: {bc['requested_timeout_seconds']} (P51-B cap: {_fmt_scalar(bc['p51b_timeout_seconds_future_cap'])})",
        "",
    ])

    pc = report["planner_config"]
    lines.extend([
        "## Planner config",
        "",
        f"- p51c_live_opt_in: {pc['p51c_live_opt_in']}",
        f"- ack_not_evidence: `{pc['ack_not_evidence']}`",
        f"- dataset: `{pc['dataset']}`",
        f"- repo_scope: `{pc['repo_scope']}`",
        f"- llm_output_mode: `{pc['llm_output_mode']}`",
        f"- max_remote_calls_total: {pc['max_remote_calls_total']}",
        f"- max_request_chars: {pc['max_request_chars']}",
        f"- max_output_chars: {pc['max_output_chars']}",
        f"- max_candidates_per_request: {pc['max_candidates_per_request']}",
        f"- max_total_lines_per_request: {pc['max_total_lines_per_request']}",
        f"- timeout_seconds: {pc['timeout_seconds']}",
        f"- allowed output modes: {pc['allowed_output_modes']}",
        f"- allowed datasets: {pc['allowed_datasets']}",
        "",
    ])

    lines.extend([
        "## Conclusion",
        "",
    ])
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test helpers: minimal synthetic aggregate upstream reports.
# ---------------------------------------------------------------------------

def _make_synthetic_p61(*, status: str = "micro_run_preconditions_met") -> dict[str, Any]:
    return {
        "schema_version": "p61-pre-spend-gate-v0",
        "status": status,
        "self_test": False,
        "not_quality_evidence": True,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "remote_calls_by_p61": 0,
        "llm_calls_by_p61": 0,
        "remote_requests_by_p61": 0,
        "prompt_construction_by_p61": False,
        "provider_config_read_by_p61": False,
        "source_reads_attempted_by_p61": False,
        "provider_spend_authorized": False,
        "evidence_admission_performed": False,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "provider_keys_in_artifact": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_query_stored": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "readiness_decision": {
            "decision": status,
            "decision_is_authorization": False,
            "provider_spend_authorized": False,
            "requires_separate_human_or_workflow_dispatch": True,
        },
    }


def _make_synthetic_p51b(
    *,
    redaction_precondition_satisfied: bool = True,
    redaction_consistent: bool = True,
    runtime_redaction_required: bool = True,
    source_backed: bool = True,
) -> dict[str, Any]:
    redaction_status = "required_defined_satisfied" if redaction_precondition_satisfied else "required_policy_unsatisfied"
    return {
        "schema_version": "p51b-llm-opt-in-contract-v1",
        "status": "ok",
        "self_test": False,
        "not_quality_evidence": False,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "dry_run_payload_validation_only": True,
        "p51b_live_calls_disabled": True,
        "remote_calls_by_p51b": 0,
        "llm_calls_by_p51b": 0,
        "remote_requests_by_p51b": 0,
        "prompt_construction_by_p51b": False,
        "provider_keys_in_artifact": False,
        "raw_request_envelopes_stored": False,
        "raw_prompts_stored": False,
        "raw_outputs_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_query_stored": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "metrics": {
            "future_live_gate_readiness": {
                "p51b_live_gate_ready": True,
                "p51b_live_gate_ready_reason": "contract_valid_dry_run_only",
            },
            "eligibility": {
                "eligible_candidate_count": 10,
                "eligible_pack_count": 5,
                "eligibility_availability": "available_source_backed" if source_backed else "partial_metadata_only",
                "source_backed_live_eligibility_available": source_backed,
            },
            "request_envelope_blueprint": {
                "request_envelope_blueprint_count": 3,
                "max_budget_violation_count": 0,
                "max_budget_violation_rate": 0.0,
                "redaction_required_count": 3,
                "redaction_required_rate": 1.0,
                "redaction_policy_contract_version": "p51b-redaction-policy-precondition-v1",
                "redaction_policy_required": True,
                "redaction_policy_defined": True,
                "redaction_policy_precondition_satisfied": redaction_precondition_satisfied,
                "redaction_policy_precondition_only": True,
                "redaction_policy_consistent": redaction_consistent,
                "redaction_policy_status": redaction_status,
                "runtime_redaction_still_required_by_p51c": runtime_redaction_required,
            },
            "role_output_schema_validation": {
                "role_output_schema_invalid_reject_count": 6,
                "role_output_schema_invalid_reject_rate": 1.0,
                "role_output_schema_valid_rate": 1.0,
                "unknown_field_reject_count": 2,
                "not_evidence_missing_reject_count": 1,
            },
            "contract_manifest": {
                "max_remote_calls_future_cap": 1,
                "max_request_chars_future_cap": 16000,
                "max_output_chars_future_cap": 4000,
                "max_candidates_per_request": 6,
                "max_total_lines_per_request": 360,
                "timeout_seconds_future_cap": 60,
            },
        },
    }


def _make_actionable_set() -> dict[str, dict[str, Any] | None]:
    return {
        "p61": _make_synthetic_p61(),
        "p51b": _make_synthetic_p51b(),
    }


def _make_config(**overrides: Any) -> PlannerConfig:
    defaults: dict[str, Any] = {
        "live_opt_in": True,
        "ack_not_evidence": REQUIRED_ACK,
        "dataset": "ci_smoke",
        "repo_id": "py_flask",
        "max_remote_calls_total": 1,
        "max_request_chars": 16000,
        "max_output_chars": 4000,
        "max_candidates_per_request": 6,
        "max_total_lines_per_request": 360,
        "timeout_seconds": 60,
        "llm_output_mode": "json_schema_strict",
    }
    defaults.update(overrides)
    return PlannerConfig(**defaults)


def run_self_tests() -> None:
    # 1) ready non-self-test synthetic -> planner_ready
    reports = _make_actionable_set()
    config = _make_config()
    status, _reasons, _checks, _requested, _caps = evaluate_plan(reports, config, self_test=False)
    if status != "planner_ready":
        raise RuntimeError(f"expected planner_ready for actionable set, got {status}")

    # 2) no opt-in -> blocked_missing_opt_in
    no_opt = _make_config(live_opt_in=False)
    status2, _, _, _, _ = evaluate_plan(_make_actionable_set(), no_opt, self_test=False)
    if status2 != "blocked_missing_opt_in":
        raise RuntimeError(f"expected blocked_missing_opt_in without opt-in, got {status2}")

    # 3) bad ack -> blocked_missing_opt_in
    bad_ack = _make_config(ack_not_evidence="wrong")
    status3, _, _, _, _ = evaluate_plan(_make_actionable_set(), bad_ack, self_test=False)
    if status3 != "blocked_missing_opt_in":
        raise RuntimeError(f"expected blocked_missing_opt_in with bad ack, got {status3}")

    # 4) bad dataset -> blocked_preconditions
    bad_ds = _make_config(dataset="unknown_dataset")
    status4, _, _, _, _ = evaluate_plan(_make_actionable_set(), bad_ds, self_test=False)
    if status4 != "blocked_preconditions":
        raise RuntimeError(f"expected blocked_preconditions for bad dataset, got {status4}")

    # 5) prompt_only output mode -> blocked_schema_contract
    prompt_only = _make_config(llm_output_mode="prompt_only")
    status5, _, _, _, _ = evaluate_plan(_make_actionable_set(), prompt_only, self_test=False)
    if status5 != "blocked_schema_contract":
        raise RuntimeError(f"expected blocked_schema_contract for prompt_only, got {status5}")

    # 6) missing P61 -> blocked_preconditions
    missing_p61 = {**_make_actionable_set(), "p61": None}
    status6, _, _, _, _ = evaluate_plan(missing_p61, config, self_test=False)
    if status6 != "blocked_preconditions":
        raise RuntimeError(f"expected blocked_preconditions for missing p61, got {status6}")

    # 7) P61 not preconditions -> blocked_preconditions
    p61_bad = {**_make_actionable_set(), "p61": _make_synthetic_p61(status="insufficient_inputs")}
    status7, _, _, _, _ = evaluate_plan(p61_bad, config, self_test=False)
    if status7 != "blocked_preconditions":
        raise RuntimeError(f"expected blocked_preconditions for p61 not preconditions, got {status7}")

    # 8) P51-B redaction missing -> blocked_privacy
    p51b_bad = {
        **_make_actionable_set(),
        "p51b": _make_synthetic_p51b(redaction_precondition_satisfied=False),
    }
    status8, _, _, _, _ = evaluate_plan(p51b_bad, config, self_test=False)
    if status8 != "blocked_privacy":
        raise RuntimeError(f"expected blocked_privacy for missing redaction, got {status8}")

    # 9) self-test status overrides to self_test_only even when ready
    status9, _, _, _, _ = evaluate_plan(_make_actionable_set(), config, self_test=True)
    if status9 != "self_test_only":
        raise RuntimeError(f"expected self_test_only in self-test mode, got {status9}")


def main() -> int:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--p61-report", type=Path, default=None, help="Path to P61 aggregate report.")
    parser.add_argument("--p51b-report", type=Path, default=None, help="Path to P51-B aggregate report.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--p51c-live-opt-in", action="store_true", help="Explicit opt-in to plan a future P51-C live LLM micro-run.")
    parser.add_argument("--ack-not-evidence", type=str, default="", help="Acknowledgement that P51-C output is not evidence.")
    parser.add_argument("--dataset", type=str, default="self_test", help="Dataset source for the planned run.")
    parser.add_argument("--repo-id", type=str, default="py_flask", help="CI corpus repo id (not published raw).")
    parser.add_argument("--max-remote-calls-total", type=int, default=1, help="Maximum remote calls total.")
    parser.add_argument("--max-request-chars", type=int, default=16000, help="Maximum request characters.")
    parser.add_argument("--max-output-chars", type=int, default=4000, help="Maximum output characters.")
    parser.add_argument("--max-candidates-per-request", type=int, default=6, help="Maximum candidates per request.")
    parser.add_argument("--max-total-lines-per-request", type=int, default=360, help="Maximum total lines per request.")
    parser.add_argument("--timeout-seconds", type=int, default=60, help="Timeout seconds.")
    parser.add_argument("--llm-output-mode", type=str, default="json_schema_strict", help="Planned LLM structured output mode.")
    args = parser.parse_args()

    config = _coerce_config(args)

    if not args.self_test:
        missing: list[str] = []
        if args.p61_report is None:
            missing.append("--p61-report")
        if args.p51b_report is None:
            missing.append("--p51b-report")
        if missing:
            parser.error(f"Required reports missing: {', '.join(missing)}. Use --self-test to run synthetic self-test.")

    start = time.monotonic()

    if args.self_test:
        run_self_tests()
        # Use a planner-ready config for the committed self-test artifact while still forcing self_test_only.
        config = _make_config()
        reports: dict[str, dict[str, Any] | None] = _make_actionable_set()
    else:
        reports = {
            "p61": _read_aggregate_report(args.p61_report),
            "p51b": _read_aggregate_report(args.p51b_report),
        }

    elapsed_ms = int((time.monotonic() - start) * 1000)
    report = build_report(reports, config, self_test=args.self_test, elapsed_ms=elapsed_ms)

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P51-C0 report written to {args.out}")
    print(f"P51-C0 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
