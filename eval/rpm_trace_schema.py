#!/usr/bin/env python3
"""OpenLocus v2 Phase 1 RPM trace schema validator/report.

This module intentionally implements only the enabling schema/closure phase.  It
does not capture traces, train RPM policies, run retrieval, call providers, or
publish private rows.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = REPO / "artifacts" / "rpm_trace_schema" / "rpm_trace_schema_report.json"

ROW_SCHEMA_VERSION = "rpm_state_action_trace_v2_phase1"
REPORT_SCHEMA_VERSION = "rpm_trace_schema_public_report_v1"

TOP_LEVEL_KEYS = [
    "trace_identity",
    "task_state",
    "state_features",
    "action",
    "policy_learning_support",
    "observation_result",
    "evidencecore_linkage",
    "outcome_label",
    "privacy_execution",
    "stop_go_source_locks_readback",
]

GROUP_FIELDS: dict[str, list[str]] = {
    "trace_identity": [
        "schema_version",
        "trace_id",
        "step_id",
        "episode_step_index",
        "created_order_index",
        "runner_kind",
    ],
    "task_state": [
        "task_bucket",
        "task_type",
        "objective_bucket",
        "route_family",
        "source_lock_id",
        "current_route_status",
    ],
    "state_features": [
        "query_shape_bucket",
        "repo_size_bucket",
        "candidate_count_bucket",
        "evidence_coverage_bucket",
        "currentness_bucket",
        "ambiguity_bucket",
        "dirty_state_bucket",
        "features_label_blind_bool",
    ],
    "action": [
        "action_type",
        "action_scope_bucket",
        "retrieval_budget_bucket",
        "source_scan_scope",
        "candidate_generation_policy",
        "pack_policy",
        "action_feature_keys",
    ],
    "policy_learning_support": [
        "behavior_policy_id",
        "behavior_policy_kind",
        "deterministic_bool",
        "action_probability",
        "action_probability_bucket",
        "propensity_available_bool",
        "eligible_actions_bucket",
    ],
    "observation_result": [
        "observation_status",
        "result_bucket",
        "evidence_delta_bucket",
        "latency_bucket",
        "failure_bucket",
        "observation_after_action_bool",
    ],
    "evidencecore_linkage": [
        "evidencecore_required_bool",
        "evidencecore_link_status",
        "currentness_verification_status",
        "stale_evidence_detected_bool",
        "materialization_status",
        "path_range_hash_private_only_bool",
    ],
    "outcome_label": [
        "label_available_bool",
        "label_timing",
        "label_source",
        "outcome_bucket",
        "label_used_in_state_or_action_bool",
    ],
    "privacy_execution": [
        "private_trace_bool",
        "public_report_level",
        "raw_publication_bool",
        "provider_payload_public_bool",
        "network_access",
        "ci_execution",
        "private_values_public_bool",
    ],
    "stop_go_source_locks_readback": [
        "source_lock_readback_status",
        "allowed_next_phase",
        "forbidden_next_phases",
        "overauthorization_bool",
        "readback_consistency_status",
    ],
}

ENUMS: dict[str, set[str]] = {
    "schema_version": {ROW_SCHEMA_VERSION},
    "runner_kind": {"manual_local", "offline_replay_logger", "product_workflow_logger"},
    "task_bucket": {"count_1", "count_2_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"},
    "task_type": {"retrieval_fact", "code_navigation", "product_workflow", "rpm_trace_capture"},
    "objective_bucket": {"current_evidence", "trace_policy_learning", "workflow_completion", "diagnostic_only"},
    "route_family": {"openlocus_v2", "frk_product", "rpm_d0"},
    "source_lock_id": {"current_route_closure_2026_07_04", "operator_private_lock"},
    "current_route_status": {"closed_routes_locked", "trace_schema_only", "executable_capture_ready"},
    "query_shape_bucket": {"none", "short", "medium", "long", "structured"},
    "repo_size_bucket": {"unknown", "files_1_to_100", "files_101_to_1000", "files_1001_to_10000", "files_gt_10000"},
    "candidate_count_bucket": {"count_0", "count_1", "count_2_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"},
    "evidence_coverage_bucket": {"coverage_none", "coverage_low", "coverage_medium", "coverage_high"},
    "currentness_bucket": {"not_checked", "verified_current", "stale_rejected", "drift_detected"},
    "ambiguity_bucket": {"low", "medium", "high"},
    "dirty_state_bucket": {"clean", "dirty_safe", "dirty_requires_update", "unknown"},
    "action_type": {"abstain", "read_current_source", "bounded_retrieval", "validate_evidence", "ask_clarifying", "workflow_step"},
    "action_scope_bucket": {"scope_none", "scope_single_file", "scope_small_bounded", "scope_workflow_bounded"},
    "retrieval_budget_bucket": {"budget_0", "budget_1_to_5", "budget_6_to_20", "budget_21_to_50"},
    "source_scan_scope": {"none", "explicit_bounded", "current_evidence_only"},
    "candidate_generation_policy": {"none", "existing_candidates_only", "bounded_current_source_only"},
    "pack_policy": {"none", "fixed_order", "evidencecore_validated", "workflow_order"},
    "behavior_policy_kind": {"deterministic_rule", "logged_policy", "manual_operator"},
    "action_probability_bucket": {"probability_0_to_0_25", "probability_0_25_to_0_5", "probability_0_5_to_1", "probability_1"},
    "eligible_actions_bucket": {"count_1", "count_2_to_5", "count_6_to_20"},
    "observation_status": {"not_observed", "observed", "failed_safe", "abstained"},
    "result_bucket": {"not_applicable", "no_change", "evidence_added", "evidence_rejected", "workflow_advanced", "failure"},
    "evidence_delta_bucket": {"delta_0", "delta_1", "delta_2_to_5", "delta_6_to_20"},
    "latency_bucket": {"unknown", "lt_1s", "1s_to_10s", "10s_to_60s", "gt_60s"},
    "failure_bucket": {"none", "stale_evidence", "unsafe_path", "missing_source", "validation_failed", "other"},
    "evidencecore_link_status": {"not_required", "linked_current", "missing", "stale_rejected", "unsafe_rejected"},
    "currentness_verification_status": {"not_required", "verified_current", "stale", "unsafe", "unavailable"},
    "materialization_status": {"not_required", "materialized_current", "rejected", "unavailable"},
    "label_timing": {"not_available", "after_action", "after_episode", "offline_eval_only"},
    "label_source": {"none", "private_eval_only", "operator_private", "heldout_private"},
    "outcome_bucket": {"not_evaluated", "success_bucket", "partial_bucket", "failure_bucket", "abstain_bucket"},
    "public_report_level": {"aggregate_schema_only"},
    "network_access": {"no_network"},
    "ci_execution": {"not_ci", "local_manual_only"},
    "source_lock_readback_status": {"passed", "unavailable_fail_closed"},
    "allowed_next_phase": {"rpm_d0_trace_capture", "frk_product_workflow_benchmark"},
    "readback_consistency_status": {"passed"},
}

BOOLEAN_FIELDS = {
    "features_label_blind_bool",
    "deterministic_bool",
    "propensity_available_bool",
    "observation_after_action_bool",
    "evidencecore_required_bool",
    "stale_evidence_detected_bool",
    "path_range_hash_private_only_bool",
    "label_available_bool",
    "label_used_in_state_or_action_bool",
    "private_trace_bool",
    "raw_publication_bool",
    "provider_payload_public_bool",
    "private_values_public_bool",
    "overauthorization_bool",
}

FORBIDDEN_NEXT_PHASES = {
    "rpm_training",
    "default_claim",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "provider_claim",
    "network_claim",
    "ci_claim",
    "runtime_default_claim",
    "frk_j",
    "frk_b_c_resurrection",
    "ldi_b_easy_slice_continuation",
    "haae_sg",
    "haae_t",
    "broad_source_scan",
    "candidate_generation_expansion",
    "retrieval_pack_rerun_new_algorithm",
    "raw_publication",
}

REQUIRED_CONSTRAINTS = [
    "no_unknown_top_level_keys",
    "closed_enums",
    "unique_trace_step_ids",
    "monotonic_step_ordering",
    "labels_after_action_or_offline_only",
    "state_action_label_blind",
    "behavior_policy_probability_marker_required",
    "evidencecore_currentness_required_when_linked",
    "aggregate_only_publication",
    "stop_go_fail_closed",
]

EXPECTED_MUTATIONS = [
    "missing_field",
    "bad_enum",
    "stale_evidence_currentness_drift",
    "label_leakage",
    "public_leak",
    "report_selftest_drop_fail",
    "report_schema_group_drop_fail",
    "report_status_drift_fail",
    "report_selection_rule_drift_fail",
    "overauthorization",
    "report_stop_go_training_overauth_fail",
    "duplicate_step",
    "non_monotonic_order",
    "unknown_top_level_key",
    "fake_unconditional_validator_pass_prevention",
]

EXPECTED_SELF_TEST_TOTAL = len(EXPECTED_MUTATIONS) + 1

LABEL_LEAK_TERMS = re.compile(r"(gold|answer|outcome|success|failure_label|relevant|judg(e|ment)|label)", re.I)
RAW_PATH_RE = re.compile(r"(^|[\s\"'])((/[^\s\"']+)|(\.{1,2}/[^\s\"']+)|([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[^\s\"']+))")
HASH_RE = re.compile(r"\b[a-f0-9]{32,}\b", re.I)
RISKY_PUBLIC_KEY_RE = re.compile(
    r"(^|_)(filepath|filename|basename|task_id|prompt|response|snippet|content_hash|exact_value|row_value|raw_path)s?($|_)",
    re.I,
)


class ValidationError(Exception):
    pass


def _walk(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = [(prefix, obj)]
    if isinstance(obj, dict):
        for k, v in obj.items():
            items.extend(_walk(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            items.extend(_walk(v, f"{prefix}[{i}]"))
    return items


def validate_trace_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not isinstance(rows, list) or not rows:
        return ["trace rows must be a non-empty list"]

    seen_trace_step: set[tuple[str, str]] = set()
    seen_step_ids: set[str] = set()
    last_step_by_trace: dict[str, int] = {}
    last_order_by_trace: dict[str, int] = {}

    for idx, row in enumerate(rows):
        loc = f"row[{idx}]"
        if not isinstance(row, dict):
            errors.append(f"{loc}: row must be an object")
            continue
        keys = set(row)
        expected = set(TOP_LEVEL_KEYS)
        if keys != expected:
            missing = sorted(expected - keys)
            unknown = sorted(keys - expected)
            if missing:
                errors.append(f"{loc}: missing top-level keys {missing}")
            if unknown:
                errors.append(f"{loc}: unknown top-level keys {unknown}")
        for group in TOP_LEVEL_KEYS:
            value = row.get(group)
            if not isinstance(value, dict):
                errors.append(f"{loc}.{group}: group must be an object")
                continue
            fields = set(value)
            expected_fields = set(GROUP_FIELDS[group])
            if fields != expected_fields:
                missing = sorted(expected_fields - fields)
                unknown = sorted(fields - expected_fields)
                if missing:
                    errors.append(f"{loc}.{group}: missing fields {missing}")
                if unknown:
                    errors.append(f"{loc}.{group}: unknown fields {unknown}")

        flat: dict[str, Any] = {}
        for group in TOP_LEVEL_KEYS:
            if isinstance(row.get(group), dict):
                for field, value in row[group].items():
                    flat[field] = value

        for field, choices in ENUMS.items():
            if field in flat and flat[field] not in choices:
                errors.append(f"{loc}.{field}: value {flat[field]!r} not in closed enum")
        for field in BOOLEAN_FIELDS:
            if field in flat and not isinstance(flat[field], bool):
                errors.append(f"{loc}.{field}: must be boolean")
        for field in ("trace_id", "step_id", "behavior_policy_id"):
            if field in flat and (not isinstance(flat[field], str) or not flat[field].startswith("private_ref_")):
                errors.append(f"{loc}.{field}: must be an opaque private_ref_* identifier")
        for field in ("episode_step_index", "created_order_index"):
            if field in flat and (not isinstance(flat[field], int) or flat[field] < 0):
                errors.append(f"{loc}.{field}: must be a non-negative integer")

        trace_id = flat.get("trace_id")
        step_id = flat.get("step_id")
        step_index = flat.get("episode_step_index")
        order_index = flat.get("created_order_index")
        if isinstance(trace_id, str) and isinstance(step_id, str):
            pair = (trace_id, step_id)
            if pair in seen_trace_step:
                errors.append(f"{loc}: duplicate trace/step id pair")
            seen_trace_step.add(pair)
            if step_id in seen_step_ids:
                errors.append(f"{loc}: duplicate step_id")
            seen_step_ids.add(step_id)
        if isinstance(trace_id, str) and isinstance(step_index, int):
            prior = last_step_by_trace.get(trace_id)
            if prior is not None and step_index <= prior:
                errors.append(f"{loc}: non-monotonic episode_step_index for trace")
            last_step_by_trace[trace_id] = step_index
        if isinstance(trace_id, str) and isinstance(order_index, int):
            prior = last_order_by_trace.get(trace_id)
            if prior is not None and order_index <= prior:
                errors.append(f"{loc}: non-monotonic created_order_index for trace")
            last_order_by_trace[trace_id] = order_index

        if flat.get("features_label_blind_bool") is not True:
            errors.append(f"{loc}: state features must be label-blind")
        if flat.get("label_used_in_state_or_action_bool") is not False:
            errors.append(f"{loc}: label leakage flag must remain false")
        for group in ("state_features", "action"):
            for subpath, value in _walk(row.get(group, {}), group):
                if subpath.endswith("features_label_blind_bool"):
                    continue
                if isinstance(value, str) and LABEL_LEAK_TERMS.search(value):
                    errors.append(f"{loc}.{subpath}: label/gold/outcome leakage term in state/action value")
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and LABEL_LEAK_TERMS.search(item):
                            errors.append(f"{loc}.{subpath}: label/gold/outcome leakage term in state/action feature list")

        if flat.get("label_available_bool") is True:
            if flat.get("label_timing") not in {"after_action", "after_episode", "offline_eval_only"}:
                errors.append(f"{loc}: available labels must be after action/episode or offline eval only")
            if flat.get("label_source") == "none" or flat.get("outcome_bucket") == "not_evaluated":
                errors.append(f"{loc}: available label requires private label source and outcome bucket")
        else:
            if flat.get("label_timing") != "not_available" or flat.get("label_source") != "none":
                errors.append(f"{loc}: unavailable labels must not carry label timing/source")

        if flat.get("deterministic_bool") is True:
            if flat.get("action_probability") != 1.0 or flat.get("action_probability_bucket") != "probability_1":
                errors.append(f"{loc}: deterministic behavior policy requires probability 1.0 marker")
        else:
            prob = flat.get("action_probability")
            if not isinstance(prob, (float, int)) or not (0.0 < float(prob) < 1.0):
                errors.append(f"{loc}: stochastic behavior policy requires 0<p<1 probability")
            if flat.get("propensity_available_bool") is not True:
                errors.append(f"{loc}: stochastic behavior policy requires available propensity")
            if flat.get("action_probability_bucket") == "probability_1":
                errors.append(f"{loc}: stochastic behavior policy cannot use probability_1 bucket")

        if flat.get("evidencecore_required_bool") is True:
            if flat.get("stale_evidence_detected_bool") is True:
                if flat.get("evidencecore_link_status") != "stale_rejected":
                    errors.append(f"{loc}: stale evidence must be rejected")
            else:
                if flat.get("evidencecore_link_status") != "linked_current":
                    errors.append(f"{loc}: required EvidenceCore must link to current evidence")
                if flat.get("currentness_verification_status") != "verified_current":
                    errors.append(f"{loc}: required EvidenceCore must be verified current")
                if flat.get("materialization_status") != "materialized_current":
                    errors.append(f"{loc}: required EvidenceCore must materialize current source")
        if flat.get("path_range_hash_private_only_bool") is not True:
            errors.append(f"{loc}: path/range/content identifiers must remain private only")

        if flat.get("private_trace_bool") is not True:
            errors.append(f"{loc}: rows are private traces")
        if flat.get("public_report_level") != "aggregate_schema_only":
            errors.append(f"{loc}: public report level must be aggregate_schema_only")
        for field in ("raw_publication_bool", "provider_payload_public_bool", "private_values_public_bool"):
            if flat.get(field) is not False:
                errors.append(f"{loc}.{field}: must be false")
        if flat.get("network_access") != "no_network":
            errors.append(f"{loc}: provider/network execution is not authorized")

        forbidden = flat.get("forbidden_next_phases")
        if not isinstance(forbidden, list) or set(forbidden) != FORBIDDEN_NEXT_PHASES:
            errors.append(f"{loc}: forbidden_next_phases must exactly lock all forbidden routes")
        if flat.get("overauthorization_bool") is not False:
            errors.append(f"{loc}: overauthorization must be false")
        if flat.get("allowed_next_phase") in FORBIDDEN_NEXT_PHASES:
            errors.append(f"{loc}: allowed next phase is forbidden")

    return errors


def valid_fixture_rows() -> list[dict[str, Any]]:
    base = {
        "trace_identity": {
            "schema_version": ROW_SCHEMA_VERSION,
            "trace_id": "private_ref_trace_a",
            "step_id": "private_ref_step_a0",
            "episode_step_index": 0,
            "created_order_index": 0,
            "runner_kind": "manual_local",
        },
        "task_state": {
            "task_bucket": "count_2_to_5",
            "task_type": "rpm_trace_capture",
            "objective_bucket": "trace_policy_learning",
            "route_family": "openlocus_v2",
            "source_lock_id": "current_route_closure_2026_07_04",
            "current_route_status": "trace_schema_only",
        },
        "state_features": {
            "query_shape_bucket": "structured",
            "repo_size_bucket": "files_101_to_1000",
            "candidate_count_bucket": "count_6_to_20",
            "evidence_coverage_bucket": "coverage_medium",
            "currentness_bucket": "verified_current",
            "ambiguity_bucket": "medium",
            "dirty_state_bucket": "clean",
            "features_label_blind_bool": True,
        },
        "action": {
            "action_type": "validate_evidence",
            "action_scope_bucket": "scope_small_bounded",
            "retrieval_budget_bucket": "budget_6_to_20",
            "source_scan_scope": "current_evidence_only",
            "candidate_generation_policy": "existing_candidates_only",
            "pack_policy": "evidencecore_validated",
            "action_feature_keys": ["currentness_bucket", "evidence_coverage_bucket"],
        },
        "policy_learning_support": {
            "behavior_policy_id": "private_ref_behavior_policy_a",
            "behavior_policy_kind": "deterministic_rule",
            "deterministic_bool": True,
            "action_probability": 1.0,
            "action_probability_bucket": "probability_1",
            "propensity_available_bool": True,
            "eligible_actions_bucket": "count_2_to_5",
        },
        "observation_result": {
            "observation_status": "observed",
            "result_bucket": "evidence_added",
            "evidence_delta_bucket": "delta_1",
            "latency_bucket": "1s_to_10s",
            "failure_bucket": "none",
            "observation_after_action_bool": True,
        },
        "evidencecore_linkage": {
            "evidencecore_required_bool": True,
            "evidencecore_link_status": "linked_current",
            "currentness_verification_status": "verified_current",
            "stale_evidence_detected_bool": False,
            "materialization_status": "materialized_current",
            "path_range_hash_private_only_bool": True,
        },
        "outcome_label": {
            "label_available_bool": False,
            "label_timing": "not_available",
            "label_source": "none",
            "outcome_bucket": "not_evaluated",
            "label_used_in_state_or_action_bool": False,
        },
        "privacy_execution": {
            "private_trace_bool": True,
            "public_report_level": "aggregate_schema_only",
            "raw_publication_bool": False,
            "provider_payload_public_bool": False,
            "network_access": "no_network",
            "ci_execution": "not_ci",
            "private_values_public_bool": False,
        },
        "stop_go_source_locks_readback": {
            "source_lock_readback_status": "passed",
            "allowed_next_phase": "rpm_d0_trace_capture",
            "forbidden_next_phases": sorted(FORBIDDEN_NEXT_PHASES),
            "overauthorization_bool": False,
            "readback_consistency_status": "passed",
        },
    }
    second = copy.deepcopy(base)
    second["trace_identity"]["step_id"] = "private_ref_step_a1"
    second["trace_identity"]["episode_step_index"] = 1
    second["trace_identity"]["created_order_index"] = 1
    second["action"]["action_type"] = "read_current_source"
    second["outcome_label"] = {
        "label_available_bool": True,
        "label_timing": "after_action",
        "label_source": "private_eval_only",
        "outcome_bucket": "success_bucket",
        "label_used_in_state_or_action_bool": False,
    }
    third = copy.deepcopy(base)
    third["trace_identity"]["trace_id"] = "private_ref_trace_b"
    third["trace_identity"]["step_id"] = "private_ref_step_b0"
    third["trace_identity"]["episode_step_index"] = 0
    third["trace_identity"]["created_order_index"] = 0
    third["task_state"]["task_type"] = "product_workflow"
    third["task_state"]["route_family"] = "frk_product"
    third["action"]["action_type"] = "workflow_step"
    third["stop_go_source_locks_readback"]["allowed_next_phase"] = "frk_product_workflow_benchmark"
    return [base, second, third]


def public_leak_errors(obj: Any) -> list[str]:
    errors: list[str] = []
    for path, value in _walk(obj):
        key = path.rsplit(".", 1)[-1].split("[", 1)[0]
        if RISKY_PUBLIC_KEY_RE.search(key):
            errors.append(f"public leak risky key {path}")
        if isinstance(value, str):
            if RAW_PATH_RE.search(value):
                errors.append(f"public leak raw path-like string at {path}")
            if HASH_RE.search(value):
                errors.append(f"public leak hash-like string at {path}")
    return errors


def build_public_report(self_test_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = valid_fixture_rows()
    row_errors = validate_trace_rows(rows)
    if row_errors:
        raise ValidationError("valid fixture failed: " + "; ".join(row_errors))
    field_presence = {
        group: {field: "count_2_to_5" for field in fields}
        for group, fields in GROUP_FIELDS.items()
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": "openlocus_v2_phase1_route_closure_rpm_trace_schema",
        "status": "complete_schema_and_route_closure_only",
        "privacy_contract": {
            "publication_level": "aggregate_schema_only",
            "raw_rows_public": False,
            "private_identifiers_public": False,
            "provider_payloads_public": False,
            "network_or_ci_claims": False,
        },
        "schema": {
            "row_schema_version": ROW_SCHEMA_VERSION,
            "required_groups": TOP_LEVEL_KEYS,
            "required_field_presence_buckets": field_presence,
            "closed_enum_field_count_bucket": "count_21_to_50",
            "required_constraints": REQUIRED_CONSTRAINTS,
        },
        "validation_summary": {
            "private_fixture_rows_validated_bucket": "count_2_to_5",
            "strict_row_validation": "passed",
            "public_leak_scan": "passed",
            "route_closure_readback": "passed",
            "fake_pass_prevention": "passed",
        },
        "self_test": self_test_summary
        or {"status": "not_embedded", "checks_passed_bucket": "count_0"},
        "stop_go": {
            "authorized_next_phase_options": [
                "rpm_d0_trace_capture",
                "frk_product_workflow_benchmark",
            ],
            "selection_rule": "choose_exactly_one_executable_schema_conformant_private_trace_or_product_workflow_benchmark_phase",
            "next_phase_public_output": "aggregate_only_report",
            "explicitly_not_authorized": sorted(FORBIDDEN_NEXT_PHASES),
        },
    }
    leaks = public_leak_errors(report)
    if leaks:
        raise ValidationError("generated public report leaked private data: " + "; ".join(leaks))
    return report


REPORT_TOP_LEVEL_KEYS = {
    "schema_version",
    "phase",
    "status",
    "privacy_contract",
    "schema",
    "validation_summary",
    "self_test",
    "stop_go",
}


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    if set(report) != REPORT_TOP_LEVEL_KEYS:
        errors.append("report has missing or unknown top-level keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("bad report schema_version")
    if report.get("phase") != "openlocus_v2_phase1_route_closure_rpm_trace_schema":
        errors.append("bad phase")
    if report.get("status") != "complete_schema_and_route_closure_only":
        errors.append("bad status")
    if report.get("privacy_contract", {}).get("publication_level") != "aggregate_schema_only":
        errors.append("report publication level must be aggregate_schema_only")
    for field in (
        "raw_rows_public",
        "private_identifiers_public",
        "provider_payloads_public",
        "network_or_ci_claims",
    ):
        if report.get("privacy_contract", {}).get(field) is not False:
            errors.append(f"privacy_contract.{field} must be false")
    schema = report.get("schema", {})
    if schema.get("required_groups") != TOP_LEVEL_KEYS:
        errors.append("required group readback mismatch")
    if schema.get("row_schema_version") != ROW_SCHEMA_VERSION:
        errors.append("bad row schema version")
    if schema.get("required_constraints") != REQUIRED_CONSTRAINTS:
        errors.append("required constraints drift")
    if schema.get("closed_enum_field_count_bucket") != "count_21_to_50":
        errors.append("closed enum field count bucket drift")
    presence = schema.get("required_field_presence_buckets", {})
    if set(presence) != set(GROUP_FIELDS):
        errors.append("required field group set drift")
    else:
        for group, fields in GROUP_FIELDS.items():
            group_presence = presence.get(group, {})
            if set(group_presence) != set(fields):
                errors.append(f"required fields drift for {group}")
            if any(value != "count_2_to_5" for value in group_presence.values()):
                errors.append(f"required field bucket drift for {group}")
    summary = report.get("validation_summary", {})
    for field in (
        "strict_row_validation",
        "public_leak_scan",
        "route_closure_readback",
        "fake_pass_prevention",
    ):
        if summary.get(field) != "passed":
            errors.append(f"validation_summary.{field} must be passed")
    if summary.get("private_fixture_rows_validated_bucket") != "count_2_to_5":
        errors.append("private fixture validation bucket drift")
    self_test = report.get("self_test", {})
    if self_test.get("status") != "passed":
        errors.append("self-test status must be passed")
    if self_test.get("checks_total") != EXPECTED_SELF_TEST_TOTAL or self_test.get("checks_passed") != EXPECTED_SELF_TEST_TOTAL:
        errors.append("self-test count drift")
    if self_test.get("failed_checks") != []:
        errors.append("self-test failed checks must be empty")
    if self_test.get("mutation_checks") != EXPECTED_MUTATIONS:
        errors.append("self-test mutation set drift")
    stop_go = report.get("stop_go", {})
    allowed = set(stop_go.get("authorized_next_phase_options", []))
    if allowed != {"rpm_d0_trace_capture", "frk_product_workflow_benchmark"}:
        errors.append("stop/go must authorize only RPM-D0 trace capture or FRK product workflow benchmark options")
    forbidden = set(stop_go.get("explicitly_not_authorized", []))
    if forbidden != FORBIDDEN_NEXT_PHASES:
        errors.append("forbidden phase set mismatch")
    if allowed & forbidden:
        errors.append("forbidden phase appears in authorized options")
    if stop_go.get("selection_rule") != "choose_exactly_one_executable_schema_conformant_private_trace_or_product_workflow_benchmark_phase":
        errors.append("stop/go selection rule drift")
    if stop_go.get("next_phase_public_output") != "aggregate_only_report":
        errors.append("stop/go next public output drift")
    leaks = public_leak_errors(report)
    errors.extend(leaks)
    return errors


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool, str]] = []

    def expect_failure(name: str, rows: list[dict[str, Any]], needle: str) -> None:
        errors = validate_trace_rows(rows)
        ok = any(needle in e for e in errors)
        checks.append((name, ok, "; ".join(errors[:3])))

    valid = valid_fixture_rows()
    checks.append(("valid_fixture_passes", not validate_trace_rows(valid), ""))

    rows = copy.deepcopy(valid)
    del rows[0]["task_state"]["task_type"]
    expect_failure("missing_field", rows, "missing fields")

    rows = copy.deepcopy(valid)
    rows[0]["action"]["action_type"] = "train_rpm"
    expect_failure("bad_enum", rows, "not in closed enum")

    rows = copy.deepcopy(valid)
    rows[0]["evidencecore_linkage"]["currentness_verification_status"] = "stale"
    rows[0]["evidencecore_linkage"]["evidencecore_link_status"] = "linked_current"
    expect_failure("stale_evidence_currentness_drift", rows, "verified current")

    rows = copy.deepcopy(valid)
    rows[0]["action"]["action_feature_keys"].append("gold_label_hit")
    expect_failure("label_leakage", rows, "leakage")

    valid_summary = {
        "status": "passed",
        "checks_passed": EXPECTED_SELF_TEST_TOTAL,
        "checks_total": EXPECTED_SELF_TEST_TOTAL,
        "mutation_checks": EXPECTED_MUTATIONS,
        "failed_checks": [],
    }
    report = build_public_report(valid_summary)
    bad_report = copy.deepcopy(report)
    bad_report["schema"]["raw_path_example"] = "/private/repo/file.rs"
    checks.append(("public_leak", bool(validate_public_report(bad_report)), ""))

    bad_report = copy.deepcopy(report)
    bad_report["self_test"]["mutation_checks"] = bad_report["self_test"]["mutation_checks"][:-1]
    checks.append(("report_selftest_drop_fail", any("mutation set" in e for e in validate_public_report(bad_report)), ""))

    bad_report = copy.deepcopy(report)
    bad_report["schema"]["required_groups"] = bad_report["schema"]["required_groups"][:-1]
    checks.append(("report_schema_group_drop_fail", any("required group" in e for e in validate_public_report(bad_report)), ""))

    bad_report = copy.deepcopy(report)
    bad_report["status"] = "rpm_training_ready"
    checks.append(("report_status_drift_fail", any("bad status" in e for e in validate_public_report(bad_report)), ""))

    bad_report = copy.deepcopy(report)
    bad_report["stop_go"]["selection_rule"] = "choose_multiple_preflight_or_training_phases"
    checks.append(("report_selection_rule_drift_fail", any("selection rule" in e for e in validate_public_report(bad_report)), ""))

    rows = copy.deepcopy(valid)
    rows[0]["stop_go_source_locks_readback"]["allowed_next_phase"] = "rpm_training"
    expect_failure("overauthorization", rows, "not in closed enum")

    bad_report = copy.deepcopy(report)
    bad_report["stop_go"]["authorized_next_phase_options"].append("rpm_training")
    checks.append(("report_stop_go_training_overauth_fail", any("forbidden" in e or "authorize" in e for e in validate_public_report(bad_report)), ""))

    rows = copy.deepcopy(valid)
    rows[1]["trace_identity"]["step_id"] = rows[0]["trace_identity"]["step_id"]
    expect_failure("duplicate_step", rows, "duplicate step_id")

    rows = copy.deepcopy(valid)
    rows[1]["trace_identity"]["episode_step_index"] = 0
    expect_failure("non_monotonic_order", rows, "non-monotonic episode_step_index")

    rows = copy.deepcopy(valid)
    rows[0]["unknown_top"] = {}
    expect_failure("unknown_top_level_key", rows, "unknown top-level keys")

    checks.append(("fake_unconditional_validator_pass_prevention", bool(validate_trace_rows([{}])), ""))

    failed = [name for name, ok, _detail in checks if not ok]
    summary = {
        "status": "passed" if not failed else "failed",
        "checks_passed": sum(1 for _name, ok, _detail in checks if ok),
        "checks_total": len(checks),
        "mutation_checks": [name for name, _ok, _detail in checks if name != "valid_fixture_passes"],
        "failed_checks": failed,
    }
    if summary["mutation_checks"] != EXPECTED_MUTATIONS:
        failed.append("mutation_set_order")
        summary["status"] = "failed"
        summary["failed_checks"] = failed
    if failed:
        details = {name: detail for name, ok, detail in checks if not ok}
        raise ValidationError(f"self-test failed: {json.dumps(details, sort_keys=True)}")
    return summary


def write_report(path: Path) -> dict[str, Any]:
    self_test_summary = run_self_tests()
    report = build_public_report(self_test_summary)
    errors = validate_public_report(report)
    if errors:
        raise ValidationError("report validation failed: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate/regenerate OpenLocus v2 RPM trace schema public report")
    parser.add_argument("--self-test", action="store_true", help="run schema validator mutation self-tests")
    parser.add_argument("--validate-report", type=Path, help="validate an aggregate-only public report")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT, help="report output path for default regeneration")
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            summary = run_self_tests()
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
            errors = validate_public_report(report)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"Validation passed: {args.validate_report}")
            return 0
        report = write_report(args.output)
        print(f"Wrote aggregate-only schema report: {args.output}")
        print(json.dumps({"status": report["status"], "schema_version": report["schema_version"]}, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
