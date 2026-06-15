#!/usr/bin/env python3
"""P51-B LLM Opt-In Contract / Dry-Run Payload Validator.

P51-B defines and validates a future live LLM opt-in contract without making
provider calls, without constructing prompt strings, and without persisting raw
request/output/snippet data. It computes aggregate eligibility and
request-envelope budget metadata from P51/P52C/P49 signals and validates
synthetic role-output schemas fail-closed.

Hard constraints:
* No live LLM/provider calls; `remote_calls_by_p51b=0`, `llm_calls_by_p51b=0`,
  `remote_requests_by_p51b=0`.
* No prompt construction; `prompt_construction_by_p51b=false`.
* No raw request envelopes, prompts, outputs/responses, snippets, source text,
  queries, paths, spans, digests, providers, models, or keys in public artifacts.
* No per-task/per-candidate rows.
* Eligibility is deterministic and gold-free.
* P51-B output is not Evidence, not quality evidence, and not a live run.
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
import p51_llm_span_narrow_2_diagnostic as p51

SCHEMA_VERSION = "p51b-llm-opt-in-contract-v1"
GENERATED_BY = "eval/p51b_llm_opt_in_contract.py"
STAGE = "P51-B LLM Opt-In Contract / Dry-Run Payload Validator"

DEFAULT_OUT = Path("artifacts/p51b_llm_opt_in_contract/p51b_llm_opt_in_contract_report.json")
DEFAULT_DOC = Path("docs/en/p51b-llm-opt-in-contract.md")

SUPPORTED_ROLES = ["span_narrow", "filter", "abstain"]
SUPPORTED_OUTPUT_MODES = ["json_object", "json_schema_strict", "tool_call"]

# Future envelope caps published in the contract only.
MAX_REMOTE_CALLS_FUTURE_CAP = 1
MAX_CANDIDATES_PER_REQUEST = 6
MAX_LINES_PER_CANDIDATE = 120
MAX_TOTAL_LINES_PER_REQUEST = 360
MAX_REQUEST_CHARS_FUTURE_CAP = 16000
MAX_OUTPUT_CHARS_FUTURE_CAP = 4000
TIMEOUT_SECONDS_FUTURE_CAP = 60
RETRY_POLICY_FUTURE_CAP = {"max_retries": 1, "retry_on_schema_error": True}
SCHEMA_REPAIR_RETRY_FUTURE_CAP = 1

# Role-output schema validation bounds (synthetic, in-memory).
ROLE_OUTPUT_SCHEMA_ALLOWED_KEYS = {"not_evidence", "role", "candidate_ref", "line_delta"}
ROLE_OUTPUT_ALLOWED_ROLES = {"span_narrow", "filter", "abstain"}
ROLE_OUTPUT_MAX_CANDIDATE_REF = 5
ROLE_OUTPUT_LINE_DELTA_MIN = -50
ROLE_OUTPUT_LINE_DELTA_MAX = 50

# Public forbidden keys. Combine upstream lists and extend for this stage.
FORBIDDEN_PUBLIC_KEYS = set(p51.FORBIDDEN_PUBLIC_KEYS) | {
    "model",
    "model_id",
    "provider",
    "api_key",
    "base_url",
    "provider_key",
    "repo_lock_path",
    "corpus_root",
    "raw_query",
    "query_terms",
    "identifier",
    "symbol_text",
    "digest",
    "digest_value",
    "contract_score",
    "role_output_schema_score",
}

# Keys that are intentionally public safety flags or metric names.
P51B_SAFETY_FLAG_KEYS = {
    # top-level safety flags
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
    "request_envelope_not_prompt",
    "contract_not_quality_evidence",
    "remote_calls_by_p51b",
    "llm_calls_by_p51b",
    "remote_requests_by_p51b",
    "prompt_construction_by_p51b",
    "dry_run_payload_validation_only",
    "raw_request_envelopes_stored",
    "raw_prompts_stored",
    "raw_outputs_stored",
    "raw_responses_stored",
    "raw_snippets_committed",
    "raw_snippets_stored",
    "raw_snippets_sent_to_provider",
    "provider_keys_in_artifact",
    "raw_query_stored",
    "private_labels_committed",
    "gold_spans_in_artifact",
    "p51b_live_calls_disabled",
    "aggregate_only_public_artifact",
    "score_phase_only_metrics",
    "candidate_pool_availability",
    "gold_span_availability",
    "reach_metrics_available",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "elapsed_ms",
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    # upstream enum carry-forward
    "p51_report_source",
    "p51_quality_gate_status",
    "p52c_report_source",
    "p52c_quality_gate_status",
    "p52c_score_availability",
    "p52b_report_source",
    "p52b_quality_gate_status",
    "p52a_report_source",
    "p52a_quality_gate_status",
    "p52_report_source",
    "p52_quality_gate_status",
    "p49_report_source",
    "p49_quality_gate_status",
    "p49_pack_not_evidence",
    "p50_report_source",
    "p50_quality_gate_status",
    "p48_report_source",
    "p48_quality_gate_status",
    "p48_overlay_availability",
    # metric block names
    "metrics",
    "contract_manifest",
    "eligibility",
    "request_envelope_blueprint",
    "role_output_schema_validation",
    "future_live_gate_readiness",
    "conclusion",
    "validation",
    # contract manifest keys
    "contract_schema_version",
    "supported_roles",
    "supported_role_count",
    "supported_output_modes",
    "live_call_lane_availability",
    "allowed_remote_mode",
    "max_remote_calls_future_cap",
    "max_candidates_per_request",
    "max_lines_per_candidate",
    "max_total_lines_per_request",
    "max_request_chars_future_cap",
    "max_output_chars_future_cap",
    "timeout_seconds_future_cap",
    "retry_policy_future_cap",
    "schema_repair_retry_future_cap",
    # eligibility keys
    "candidate_denominator",
    "eligible_candidate_count",
    "eligible_candidate_rate",
    "eligible_pack_count",
    "eligible_pack_rate",
    "eligible_by_role",
    "ineligible_reason_counts",
    "ineligible_reason_rates",
    "eligibility_availability",
    "source_backed_live_eligibility_available",
    # request envelope blueprint keys
    "request_envelope_blueprint_count",
    "mean_candidates_per_envelope",
    "p95_candidates_per_envelope",
    "mean_line_budget",
    "p95_line_budget",
    "mean_context_char_budget",
    "p95_context_char_budget",
    "max_budget_violation_count",
    "max_budget_violation_rate",
    "redaction_required_count",
    "redaction_required_rate",
    "secret_scan_availability",
    # role output schema keys
    "role_output_schema_self_test_count",
    "role_output_schema_valid_count",
    "role_output_schema_valid_rate",
    "role_output_schema_invalid_reject_count",
    "role_output_schema_invalid_reject_rate",
    "unknown_field_reject_count",
    "not_evidence_missing_reject_count",
    "line_delta_out_of_bounds_reject_count",
    "candidate_ref_out_of_bounds_reject_count",
    # future gate readiness
    "p51b_live_gate_ready",
    "p51b_live_gate_ready_reason",
    # common helpers
    "count",
    "rate",
    "value",
    "availability",
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


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P51B_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata."""
    source_key = f"{report_name}_report_source"
    status_key = f"{report_name}_quality_gate_status"
    not_provided: dict[str, Any] = {source_key: "not_provided", status_key: "not_provided"}
    if report_name == "p48":
        not_provided["p48_overlay_availability"] = "not_provided"
    if report_name == "p49":
        not_provided["p49_pack_not_evidence"] = "not_provided"
    if report_name == "p52c":
        not_provided["p52c_score_availability"] = "not_provided"
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
        if report_name == "p52c":
            result["p52c_score_availability"] = "not_provided"
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
    if report_name == "p52c":
        sa = data.get("metrics", {}).get("score_availability", {}).get("p52c_score_availability")
        result["p52c_score_availability"] = sa if isinstance(sa, str) else "not_provided"
    return result


def _make_self_test_records() -> list[dict[str, Any]]:
    """Return P46 synthetic records plus one P51-B envelope-eligible case."""
    records = list(p46.make_self_test_records())

    def pool(items: list[tuple[str, int, int]]) -> list[dict[str, Any]]:
        return [
            {"rank": i + 1, "path": path, "start_line": start, "end_line": end, "candidate_id": f"p51b_cid_{i+1}"}
            for i, (path, start, end) in enumerate(items)
        ]

    records.append({
        "task_id": "p51b-st-eligible",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {
            "candidate_count": 2,
            "candidate_support_exists": True,
            "symbol_anchor": True,
            "local_anchor": True,
            "symbol_regex_agree_span": True,
            "rrf_backed_by_anchor": True,
            "query_noise": 0.0,
        },
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/eligible.py", 10, 20),
                ("src/eligible.py", 30, 38),
            ]),
            "rrf_primary": pool([
                ("src/eligible.py", 10, 20),
                ("src/eligible.py", 30, 38),
            ]),
            "symbol_regex_union": pool([
                ("src/eligible.py", 10, 20),
                ("src/eligible.py", 30, 38),
            ]),
        },
        "p31_score_gold": {"has_gold": True, "gold_spans": [{"path": "src/eligible.py", "start_line": 10, "end_line": 20}]},
        "p33b_anchor_subtypes": [
            {
                "candidate_id": "p51b_cid_1",
                "rank": 1,
                "source_class": "symbol_only",
                "agreement_class": "span_overlap",
                "rank_bin": "top3",
                "candidate_count_bin": "small",
                "span_width_bin": "short",
                "rrf_backing": True,
            },
            {
                "candidate_id": "p51b_cid_2",
                "rank": 2,
                "source_class": "symbol_regex_fusion",
                "agreement_class": "span_overlap",
                "rank_bin": "top3",
                "candidate_count_bin": "small",
                "span_width_bin": "short",
                "rrf_backing": True,
            },
        ],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "candidate_baseline": {
            "file_recall_at_5": 1.0,
            "span_f0_5": 0.2,
            "primary_false_positive_rate": 0.0,
            "no_gold_false_primary_rate": 0.0,
            "added_gold_span": 1,
            "added_false_span": 1,
        },
    })
    return records


def _source_backed_available(report_sources: dict[str, Any]) -> bool:
    sa = report_sources.get("p52c_score_availability") or "not_provided"
    return sa in {"available_source_backed", "partial_source_backed"}


def _candidate_eligible(cand: dict[str, Any], task: dict[str, Any]) -> tuple[bool, str | None]:
    """Deterministic, gold-free eligibility filter."""
    risk = p51._candidate_metadata_risk(cand, task)
    if risk == "metadata_unavailable":
        return False, "metadata_unavailable"
    if risk == "metadata_high_risk":
        return False, "metadata_high_risk"
    path_kind = str(cand.get("path_kind") or "unknown")
    if path_kind in {"generated_or_vendor", "unknown"}:
        return False, "risky_path_kind"
    subtype = cand.get("subtype") or {}
    source_class = str(subtype.get("source_class") or "other")
    agreement_class = str(subtype.get("agreement_class") or "other")
    if source_class == "regex_only" or agreement_class in {"single_source", "disagree"}:
        return False, "high_risk_subtype"
    return True, None


def _eligible_candidates_for_task(task: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Return candidates passing the exact P51-B gold-free eligibility rules."""
    candidates = p49._normalize_candidates(task)
    if not candidates:
        return [], []
    if not p51._task_contrast_feasible(candidates):
        return [], ["no_contrast_pack"] * len(candidates)

    eligible: list[dict[str, Any]] = []
    reasons: list[str] = []
    for cand in candidates:
        ok, reason = _candidate_eligible(cand, task)
        if ok:
            eligible.append(cand)
        else:
            reasons.append(reason or "ineligible_other")
    return eligible, reasons


def _compute_eligibility(
    tasks: list[dict[str, Any]],
    report_sources: dict[str, Any],
) -> dict[str, Any]:
    candidate_denominator = 0
    eligible_candidate_count = 0
    eligible_pack_count = 0
    eligible_by_role: dict[str, int] = {"span_narrow": 0, "filter": 0, "abstain": 0}
    ineligible_reason_counts: dict[str, int] = defaultdict(int)
    source_backed = _source_backed_available(report_sources)
    p52c_avail = report_sources.get("p52c_score_availability") or "not_provided"

    for task in tasks:
        raw_candidates = p49._normalize_candidates(task)
        if not raw_candidates:
            continue
        action = p51._task_action(task)
        candidates, reasons = _eligible_candidates_for_task(task)
        for reason in reasons:
            ineligible_reason_counts[reason] += 1
        task_had_eligible = False
        candidate_denominator += len(raw_candidates)
        for _cand in candidates:
            eligible_candidate_count += 1
            eligible_by_role[action] += 1
            task_had_eligible = True
        if task_had_eligible:
            eligible_pack_count += 1

    if candidate_denominator == 0:
        eligibility_availability = "unavailable_missing_candidate_pool"
    elif p52c_avail == "unavailable_missing_candidate_pool":
        eligibility_availability = "unavailable_missing_candidate_pool"
    elif source_backed:
        eligibility_availability = "available_source_backed"
    elif p52c_avail in {"partial_metadata_only", "not_provided", "unavailable_no_source_reads"}:
        eligibility_availability = "partial_metadata_only"
    else:
        eligibility_availability = "unavailable_missing_upstream_contract"

    pack_denominator = len(tasks)
    ineligible_reason_rates = {
        k: _rate(v, candidate_denominator) for k, v in ineligible_reason_counts.items()
    }

    return {
        "candidate_denominator": candidate_denominator,
        "eligible_candidate_count": eligible_candidate_count,
        "eligible_candidate_rate": _rate(eligible_candidate_count, candidate_denominator),
        "eligible_pack_count": eligible_pack_count,
        "eligible_pack_rate": _rate(eligible_pack_count, pack_denominator),
        "eligible_by_role": {
            "span_narrow_count": eligible_by_role["span_narrow"],
            "span_narrow_rate": _rate(eligible_by_role["span_narrow"], candidate_denominator),
            "filter_count": eligible_by_role["filter"],
            "filter_rate": _rate(eligible_by_role["filter"], candidate_denominator),
            "abstain_count": eligible_by_role["abstain"],
            "abstain_rate": _rate(eligible_by_role["abstain"], candidate_denominator),
        },
        "ineligible_reason_counts": dict(ineligible_reason_counts),
        "ineligible_reason_rates": ineligible_reason_rates,
        "eligibility_availability": eligibility_availability,
        "source_backed_live_eligibility_available": source_backed,
    }


def _compute_request_envelope_blueprint(
    tasks: list[dict[str, Any]],
    eligibility: dict[str, Any],
) -> dict[str, Any]:
    source_backed = eligibility.get("source_backed_live_eligibility_available", False)
    per_envelope_candidates: list[int] = []
    per_envelope_lines: list[int] = []
    per_envelope_chars: list[int] = []
    budget_violation_count = 0
    redaction_required_count = 0

    for task in tasks:
        candidates, _reasons = _eligible_candidates_for_task(task)
        if not candidates:
            continue
        for strategy in p49.PACK_STRATEGIES:
            pack = p49._build_pack(candidates, strategy)
            selected = pack.get("selected") or []
            if not selected:
                continue
            n = len(selected)
            line_budget = pack.get("line_budget_proxy") or 0
            if line_budget == 0:
                line_budget = min(
                    sum((c.get("span_width") or 1) for c in selected),
                    p49.LINE_BUDGET_PROXY_CAP,
                )
            char_budget = line_budget * 40
            per_envelope_candidates.append(n)
            per_envelope_lines.append(line_budget)
            per_envelope_chars.append(char_budget)

            violates = (
                n > MAX_CANDIDATES_PER_REQUEST
                or line_budget > MAX_TOTAL_LINES_PER_REQUEST
                or char_budget > MAX_REQUEST_CHARS_FUTURE_CAP
                or any((c.get("span_width") or 0) > MAX_LINES_PER_CANDIDATE for c in selected)
            )
            if violates:
                budget_violation_count += 1

            redaction_needed = (
                not source_backed
                or any(str(c.get("path_kind") or "unknown") != "source" for c in selected)
            )
            if redaction_needed:
                redaction_required_count += 1

    count = len(per_envelope_candidates)
    return {
        "request_envelope_blueprint_count": count,
        "mean_candidates_per_envelope": _avg([float(x) for x in per_envelope_candidates]),
        "p95_candidates_per_envelope": _percentile(per_envelope_candidates, 0.95),
        "mean_line_budget": _avg([float(x) for x in per_envelope_lines]),
        "p95_line_budget": _percentile(per_envelope_lines, 0.95),
        "mean_context_char_budget": _avg([float(x) for x in per_envelope_chars]),
        "p95_context_char_budget": _percentile(per_envelope_chars, 0.95),
        "max_budget_violation_count": budget_violation_count,
        "max_budget_violation_rate": _rate(budget_violation_count, count),
        "redaction_required_count": redaction_required_count,
        "redaction_required_rate": _rate(redaction_required_count, count),
        "secret_scan_availability": "aggregate_metadata_only",
        "request_envelope_not_prompt": True,
        "raw_request_envelopes_stored": False,
    }


def _validate_one_role_output(obj: Any) -> tuple[bool, str | None]:
    """Fail-closed validation of a single synthetic role-output object."""
    if not isinstance(obj, dict):
        return False, "unknown_field"
    extra = set(obj.keys()) - ROLE_OUTPUT_SCHEMA_ALLOWED_KEYS
    if extra:
        return False, "unknown_field"
    if obj.get("not_evidence") is not True:
        return False, "not_evidence_missing"
    if obj.get("role") not in ROLE_OUTPUT_ALLOWED_ROLES:
        return False, "unknown_field"
    cref = _as_int(obj.get("candidate_ref"))
    if "candidate_ref" in obj:
        if cref is None or cref < 0 or cref > ROLE_OUTPUT_MAX_CANDIDATE_REF:
            return False, "candidate_ref_out_of_bounds"
    ld = _as_int(obj.get("line_delta"))
    if "line_delta" in obj:
        if ld is None or ld < ROLE_OUTPUT_LINE_DELTA_MIN or ld > ROLE_OUTPUT_LINE_DELTA_MAX:
            return False, "line_delta_out_of_bounds"
    return True, None


def _compute_role_output_schema_validation() -> dict[str, Any]:
    """Validate synthetic role-output schemas in memory only."""
    valid_fixtures = [
        {"not_evidence": True, "role": "span_narrow"},
        {"not_evidence": True, "role": "filter", "candidate_ref": 0},
        {"not_evidence": True, "role": "abstain", "candidate_ref": 1, "line_delta": -3},
    ]
    invalid_fixtures = [
        {"not_evidence": True, "role": "span_narrow", "extra_field": 1},
        {"role": "filter"},
        {"not_evidence": True, "role": "abstain", "candidate_ref": -1},
        {"not_evidence": True, "role": "span_narrow", "candidate_ref": 10},
        {"not_evidence": True, "role": "filter", "line_delta": -100},
        {"not_evidence": True, "role": "abstain", "line_delta": 200},
    ]

    valid_passed = 0
    for fixture in valid_fixtures:
        ok, _ = _validate_one_role_output(fixture)
        if ok:
            valid_passed += 1

    invalid_rejected = 0
    reason_counts: dict[str, int] = defaultdict(int)
    for fixture in invalid_fixtures:
        ok, reason = _validate_one_role_output(fixture)
        if not ok:
            invalid_rejected += 1
            reason_counts[reason or "unknown_field"] += 1

    valid_total = len(valid_fixtures)
    invalid_total = len(invalid_fixtures)
    total_tested = valid_total + invalid_total
    return {
        "role_output_schema_self_test_count": total_tested,
        "role_output_schema_valid_count": valid_passed,
        "role_output_schema_valid_rate": _rate(valid_passed, valid_total),
        "role_output_schema_invalid_reject_count": invalid_rejected,
        "role_output_schema_invalid_reject_rate": _rate(invalid_rejected, invalid_total),
        "unknown_field_reject_count": reason_counts.get("unknown_field", 0),
        "not_evidence_missing_reject_count": reason_counts.get("not_evidence_missing", 0),
        "line_delta_out_of_bounds_reject_count": reason_counts.get("line_delta_out_of_bounds", 0),
        "candidate_ref_out_of_bounds_reject_count": reason_counts.get("candidate_ref_out_of_bounds", 0),
    }


def _compute_future_live_gate_readiness(
    eligibility: dict[str, Any],
    blueprint: dict[str, Any],
    schema_validation: dict[str, Any],
) -> dict[str, Any]:
    candidate_denominator = eligibility.get("candidate_denominator") or 0
    eligible_candidate_count = eligibility.get("eligible_candidate_count") or 0
    eligible_pack_count = eligibility.get("eligible_pack_count") or 0
    blueprint_count = blueprint.get("request_envelope_blueprint_count") or 0
    valid_count = schema_validation.get("role_output_schema_valid_count") or 0
    invalid_count = schema_validation.get("role_output_schema_invalid_reject_count") or 0
    valid_rate = schema_validation.get("role_output_schema_valid_rate")

    if candidate_denominator <= 0:
        ready = False
        reason = "missing_candidate_pool"
    elif eligible_candidate_count <= 0 or eligible_pack_count <= 0:
        ready = False
        reason = "no_eligible_candidates"
    elif blueprint_count <= 0:
        ready = False
        reason = "no_eligible_envelopes"
    elif valid_count <= 0 or valid_rate != 1.0:
        ready = False
        reason = "schema_validation_failed"
    elif invalid_count <= 0:
        ready = False
        reason = "schema_validation_failed"
    else:
        ready = True
        reason = "contract_valid_dry_run_only"

    return {
        "p51b_live_gate_ready": ready,
        "p51b_live_gate_ready_reason": reason,
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

    eligibility = _compute_eligibility(tasks, report_sources)
    blueprint = _compute_request_envelope_blueprint(tasks, eligibility)
    schema_validation = _compute_role_output_schema_validation()
    gate = _compute_future_live_gate_readiness(eligibility, blueprint, schema_validation)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P51-B LLM Opt-In Contract / Dry-Run Payload Validator is ready; real per-task ephemeral P25 records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only contract validation processed {len(tasks)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P51-B validated a dry-run opt-in contract for {len(tasks)} ephemeral P25 records."
            )
        conclusion_lines.append(
            "P51-B does not call an LLM, does not construct prompts, and does not send requests to any provider."
        )
        conclusion_lines.append(
            "Eligibility is deterministic and uses only public metadata and P52C aggregate availability; gold and outcomes are not used."
        )
        conclusion_lines.append(
            "Request-envelope blueprints are metadata-only shapes; raw prompts, snippets, outputs, and responses are not stored."
        )
        conclusion_lines.append(
            "Role-output schema validation is performed on synthetic in-memory fixtures only."
        )
        conclusion_lines.append(
            "This is a contract-readiness dry run, not Evidence, not quality evidence, and not a live run."
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
        "request_envelope_not_prompt": True,
        "contract_not_quality_evidence": True,
        "remote_calls_by_p51b": 0,
        "llm_calls_by_p51b": 0,
        "remote_requests_by_p51b": 0,
        "prompt_construction_by_p51b": False,
        "dry_run_payload_validation_only": True,
        "raw_request_envelopes_stored": False,
        "raw_prompts_stored": False,
        "raw_outputs_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_stored": False,
        "raw_snippets_sent_to_provider": False,
        "provider_keys_in_artifact": False,
        "raw_query_stored": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "p51b_live_calls_disabled": True,
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
            "contract_manifest": {
                "contract_schema_version": SCHEMA_VERSION,
                "supported_roles": list(SUPPORTED_ROLES),
                "supported_role_count": len(SUPPORTED_ROLES),
                "supported_output_modes": list(SUPPORTED_OUTPUT_MODES),
                "live_call_lane_availability": "disabled_p51b",
                "allowed_remote_mode": "future_remote_opt_in_only",
                "max_remote_calls_future_cap": MAX_REMOTE_CALLS_FUTURE_CAP,
                "max_candidates_per_request": MAX_CANDIDATES_PER_REQUEST,
                "max_lines_per_candidate": MAX_LINES_PER_CANDIDATE,
                "max_total_lines_per_request": MAX_TOTAL_LINES_PER_REQUEST,
                "max_request_chars_future_cap": MAX_REQUEST_CHARS_FUTURE_CAP,
                "max_output_chars_future_cap": MAX_OUTPUT_CHARS_FUTURE_CAP,
                "timeout_seconds_future_cap": TIMEOUT_SECONDS_FUTURE_CAP,
                "retry_policy_future_cap": RETRY_POLICY_FUTURE_CAP,
                "schema_repair_retry_future_cap": SCHEMA_REPAIR_RETRY_FUTURE_CAP,
            },
            "eligibility": eligibility,
            "request_envelope_blueprint": blueprint,
            "role_output_schema_validation": schema_validation,
            "future_live_gate_readiness": gate,
        },
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P51-B public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p51b") != 0:
        errors.append("remote_calls_by_p51b must be 0")
    if report.get("llm_calls_by_p51b") != 0:
        errors.append("llm_calls_by_p51b must be 0")
    if report.get("remote_requests_by_p51b") != 0:
        errors.append("remote_requests_by_p51b must be 0")
    if report.get("prompt_construction_by_p51b") is not False:
        errors.append("prompt_construction_by_p51b must be false")
    if report.get("dry_run_payload_validation_only") is not True:
        errors.append("dry_run_payload_validation_only must be true")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "source_feature_not_evidence": True,
        "materialized_candidate_not_evidence": True,
        "request_envelope_not_prompt": True,
        "contract_not_quality_evidence": True,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "p51b_live_calls_disabled": True,
        "raw_request_envelopes_stored": False,
        "raw_prompts_stored": False,
        "raw_outputs_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_stored": False,
        "raw_snippets_sent_to_provider": False,
        "provider_keys_in_artifact": False,
        "raw_query_stored": False,
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


def _fmt_scalar(x: Any) -> str:
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, int):
        return str(x)
    return "n/a"


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P51-B LLM Opt-In Contract / Dry-Run Payload Validator\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P51-B: {report['remote_calls_by_p51b']}",
        f"- LLM calls by P51-B: {report['llm_calls_by_p51b']}",
        f"- Remote requests by P51-B: {report['remote_requests_by_p51b']}",
        f"- Prompt construction by P51-B: {report['prompt_construction_by_p51b']}",
        f"- Dry-run payload validation only: {report['dry_run_payload_validation_only']}",
        f"- P51-B live calls disabled: {report['p51b_live_calls_disabled']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- P51 report source: `{report.get('p51_report_source')}`",
        f"- P52C report source: `{report.get('p52c_report_source')}`",
        f"- P52B report source: `{report.get('p52b_report_source')}`",
        f"- P49 report source: `{report.get('p49_report_source')}`",
        f"- P50 report source: `{report.get('p50_report_source')}`",
        f"- P48 report source: `{report.get('p48_report_source')}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P51-B defines a future live LLM opt-in contract and validates dry-run payload schemas. "
        "It performs no provider calls, constructs no prompts, and stores no raw requests, outputs, snippets, or responses.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Normalize candidates with P46/P49 helpers and apply deterministic P51 eligibility filters using public metadata only; gold and outcomes are not used.",
        "- Consume upstream aggregate reports (P51/P52C/P49/P52B/P52A/P52/P50/P48) as enum/status carry-forward only.",
        "- Build request-envelope blueprint metadata from eligible candidates: candidate counts, line/character budgets, and future cap violations; no prompt strings are constructed.",
        "- Validate synthetic role-output schemas in memory with fail-closed rules (`not_evidence=true`, role enum, no unknown fields, bounded candidate refs and line deltas).",
        "- Emit aggregate readiness diagnostics and a contract manifest with future caps only; no provider, model, URL, or key is published.",
        "",
        "## Safety notes\n",
        "- P51-B does not call an LLM or any remote provider.",
        "- P51-B does not construct prompts.",
        "- P51-B does not store raw request envelopes, prompts, outputs, responses, snippets, source text, queries, paths, spans, or digests.",
        "- P51-B does not publish providers, models, base URLs, or API keys.",
        "- P51-B output is not Evidence, not quality evidence, and does not indicate live readiness or default/promotion.",
        "- Role-output schema validation uses synthetic in-memory fixtures only.",
        "",
    ])

    cm = report["metrics"]["contract_manifest"]
    lines.append("## Contract manifest\n")
    lines.append(f"- Contract schema version: `{cm['contract_schema_version']}`")
    lines.append(f"- Supported roles: {cm['supported_roles']} ({cm['supported_role_count']})")
    lines.append(f"- Supported output modes: {cm['supported_output_modes']}")
    lines.append(f"- Live-call lane availability: `{cm['live_call_lane_availability']}`")
    lines.append(f"- Allowed remote mode: `{cm['allowed_remote_mode']}`")
    lines.append("- Future caps:")
    lines.append(f"  - max_remote_calls_future_cap: {cm['max_remote_calls_future_cap']}")
    lines.append(f"  - max_candidates_per_request: {cm['max_candidates_per_request']}")
    lines.append(f"  - max_lines_per_candidate: {cm['max_lines_per_candidate']}")
    lines.append(f"  - max_total_lines_per_request: {cm['max_total_lines_per_request']}")
    lines.append(f"  - max_request_chars_future_cap: {cm['max_request_chars_future_cap']}")
    lines.append(f"  - max_output_chars_future_cap: {cm['max_output_chars_future_cap']}")
    lines.append(f"  - timeout_seconds_future_cap: {cm['timeout_seconds_future_cap']}")
    lines.append(f"  - retry_policy_future_cap: {cm['retry_policy_future_cap']}")
    lines.append(f"  - schema_repair_retry_future_cap: {cm['schema_repair_retry_future_cap']}\n")

    el = report["metrics"]["eligibility"]
    lines.append("## Eligibility\n")
    lines.append(f"- Candidate denominator: {el['candidate_denominator']}")
    lines.append(f"- Eligible candidates: {el['eligible_candidate_count']} ({_fmt_scalar(el['eligible_candidate_rate'])})")
    lines.append(f"- Eligible packs: {el['eligible_pack_count']} ({_fmt_scalar(el['eligible_pack_rate'])})")
    er = el["eligible_by_role"]
    lines.append(f"- Eligible span_narrow: {er['span_narrow_count']} ({_fmt_scalar(er['span_narrow_rate'])})")
    lines.append(f"- Eligible filter: {er['filter_count']} ({_fmt_scalar(er['filter_rate'])})")
    lines.append(f"- Eligible abstain: {er['abstain_count']} ({_fmt_scalar(er['abstain_rate'])})")
    lines.append(f"- Eligibility availability: `{el['eligibility_availability']}`")
    lines.append(f"- Source-backed live eligibility available: {el['source_backed_live_eligibility_available']}")
    lines.append("- Ineligible reason counts:")
    for reason, count in el["ineligible_reason_counts"].items():
        rate = el["ineligible_reason_rates"].get(reason)
        lines.append(f"  - {reason}: {count} ({_fmt_scalar(rate)})")
    lines.append("")

    bp = report["metrics"]["request_envelope_blueprint"]
    lines.append("## Request-envelope blueprint\n")
    lines.append(f"- Blueprint count: {bp['request_envelope_blueprint_count']}")
    lines.append(f"- Mean candidates per envelope: {_fmt_scalar(bp['mean_candidates_per_envelope'])}")
    lines.append(f"- P95 candidates per envelope: {_fmt_scalar(bp['p95_candidates_per_envelope'])}")
    lines.append(f"- Mean line budget: {_fmt_scalar(bp['mean_line_budget'])}")
    lines.append(f"- P95 line budget: {_fmt_scalar(bp['p95_line_budget'])}")
    lines.append(f"- Mean context-char budget: {_fmt_scalar(bp['mean_context_char_budget'])}")
    lines.append(f"- P95 context-char budget: {_fmt_scalar(bp['p95_context_char_budget'])}")
    lines.append(f"- Max budget violation count/rate: {bp['max_budget_violation_count']} / {_fmt_scalar(bp['max_budget_violation_rate'])}")
    lines.append(f"- Redaction required count/rate: {bp['redaction_required_count']} / {_fmt_scalar(bp['redaction_required_rate'])}")
    lines.append(f"- Secret-scan availability: `{bp['secret_scan_availability']}`")
    lines.append(f"- Request-envelope-not-prompt: `{bp['request_envelope_not_prompt']}`")
    lines.append(f"- Raw request envelopes stored: `{bp['raw_request_envelopes_stored']}`\n")

    rs = report["metrics"]["role_output_schema_validation"]
    lines.append("## Role-output schema validation\n")
    lines.append(f"- Self-test count: {rs['role_output_schema_self_test_count']}")
    lines.append(f"- Valid count/rate: {rs['role_output_schema_valid_count']} / {_fmt_scalar(rs['role_output_schema_valid_rate'])}")
    lines.append(f"- Invalid reject count/rate: {rs['role_output_schema_invalid_reject_count']} / {_fmt_scalar(rs['role_output_schema_invalid_reject_rate'])}")
    lines.append(f"- Unknown-field rejections: {rs['unknown_field_reject_count']}")
    lines.append(f"- Missing `not_evidence` rejections: {rs['not_evidence_missing_reject_count']}")
    lines.append(f"- Line-delta out-of-bounds rejections: {rs['line_delta_out_of_bounds_reject_count']}")
    lines.append(f"- Candidate-ref out-of-bounds rejections: {rs['candidate_ref_out_of_bounds_reject_count']}\n")

    gl = report["metrics"]["future_live_gate_readiness"]
    lines.append("## Future live gate readiness\n")
    lines.append(f"- p51b_live_gate_ready: {gl['p51b_live_gate_ready']}")
    lines.append(f"- p51b_live_gate_ready_reason: `{gl['p51b_live_gate_ready_reason']}`\n")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--p51-report", type=Path, default=None, help="Optional P51 report for enum/status carry-forward.")
    parser.add_argument("--p52c-report", type=Path, default=None, help="Optional P52C report for enum/status carry-forward.")
    parser.add_argument("--p52b-report", type=Path, default=None, help="Optional P52B report for enum/status carry-forward.")
    parser.add_argument("--p52a-report", type=Path, default=None, help="Optional P52A report for enum/status carry-forward.")
    parser.add_argument("--p52-report", type=Path, default=None, help="Optional P52 report for enum/status carry-forward.")
    parser.add_argument("--p49-report", type=Path, default=None, help="Optional P49 report for enum/status carry-forward.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 report for enum/status carry-forward.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 report for enum/status carry-forward.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_records = _make_self_test_records()
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
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P51-B contract validation.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P51-B requires p25-policy-records-ephemeral-v1 input schema.",
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
        reason = "Records lacked required fields for P51-B normalization."

    report_sources: dict[str, Any] = {}
    report_sources.update(_read_optional_report(args.p51_report, "p51"))
    report_sources.update(_read_optional_report(args.p52c_report, "p52c"))
    report_sources.update(_read_optional_report(args.p52b_report, "p52b"))
    report_sources.update(_read_optional_report(args.p52a_report, "p52a"))
    report_sources.update(_read_optional_report(args.p52_report, "p52"))
    report_sources.update(_read_optional_report(args.p49_report, "p49"))
    report_sources.update(_read_optional_report(args.p50_report, "p50"))
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

    print(f"P51-B report written to {args.out}")
    print(f"P51-B markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
