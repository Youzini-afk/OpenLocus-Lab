#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design.v1"
GENERATED_BY = "eval/bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design.py"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design/bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design_report.json")

INPUTS = (
    ("p3_0_frozen_upstream_trace_capture_harness_design", "BEA-v1-P3-0", "frozen_upstream_trace_capture_harness_design_pass", Path("artifacts/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design_report.json")),
    ("p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight", "BEA-v1-P3-1", "frozen_trace_capture_preflight_pass_patch_design_authorized", Path("artifacts/bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight/bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight_report.json")),
    ("p3_2_frozen_trace_logger_patch_design", "BEA-v1-P3-2", "frozen_trace_logger_patch_design_pass_p3_3_authorized", Path("artifacts/bea_v1_p3_2_frozen_trace_logger_patch_design/bea_v1_p3_2_frozen_trace_logger_patch_design_report.json")),
    ("p3_3_frozen_trace_logger_isolated_helper_patch_review", "BEA-v1-P3-3", "frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized", Path("artifacts/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review_report.json")),
)

STATUSES = (
    "frozen_trace_logger_hook_in_preflight_design_pass_p3_5_authorized",
    "no_go_p3_4_required_inputs_unavailable",
    "no_go_p3_4_static_anchor_missing",
    "no_go_p3_4_hook_point_mapping_incomplete",
    "no_go_p3_4_helper_call_contract_incomplete",
    "no_go_p3_4_privacy_or_behavior_boundary_incomplete",
    "no_go_p3_4_forbidden_code_touch_detected",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SURFACES = (
    "support_link",
    "scheduler_action_cost",
    "ordered_prefix_stop",
    "same_file_redundancy",
    "risk_penalty",
)

SURFACE_TARGET = {
    "support_link": "p0_4_support_link_input_design",
    "scheduler_action_cost": "p0_3_scheduler_dataset_export",
    "ordered_prefix_stop": "p0_6_7_8_parallel_trace_surfaces",
    "same_file_redundancy": "p0_6_7_8_parallel_trace_surfaces",
    "risk_penalty": "p0_6_7_8_parallel_trace_surfaces",
}

STATIC_TARGETS = (
    ("p0_3_scheduler_dataset_export", Path("eval/bea_v1_p0_3_scheduler_dataset_export.py"), ("scheduler_dataset_export", "PRIVATE_ARM_SCHEMA", "sanitize_private_arm_rows"), True),
    ("p0_4_support_link_input_design", Path("eval/bea_v1_p0_4_support_link_input_design.py"), ("support_link", "support_relation", "target_hit"), True),
    ("p0_6_7_8_parallel_trace_surfaces", Path("eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py"), ("same_file_redundancy", "risk_penalty", "ordered_prefix"), True),
    ("p1_2_private_label_intake_validator", Path("eval/bea_v1_p1_2_private_label_intake_validator.py"), ("private_label", "intake", "support"), True),
    ("p4l_locked_scheduler_validation_optional", Path("eval/bea_v1_p4l_locked_non_python_scheduler_validation.py"), ("p4l", "scheduler"), False),
    ("bea_v1_frozen_trace_logger_helpers", Path("eval/bea_v1_frozen_trace_logger_helpers.py"), ("build_support_link_trace_capture_row_private", "sanitize_support_link_trace_capture_row_public", "validate_risk_penalty_trace_capture_row_public_projection"), True),
)

FORBIDDEN_PUBLIC_KEYS = frozenset({"path", "paths", "file_path", "source_path", "exact_path", "private_path", "span", "line", "snippet", "content", "candidate", "candidate_list", "rank_list", "provider", "prompt", "response", "payload", "hash", "private_id", "queue_item_id", "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "text"})
SAFE_VALUE_KEYS = frozenset({"schema_version", "generated_by", "generated_at", "claim_level", "status", "mode", "phase", "failure_reason_category", "gate", "threshold_relation", "stop_go_decision", "stop_go_reason", "authorization"})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(input_file: Path) -> tuple[dict[str, Any], str]:
    if not input_file.exists():
        return {}, "missing"
    try:
        data = json.loads(input_file.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(output_file: Path, obj: dict[str, Any]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    hex_re = re.compile(r"\b[0-9a-f]{64}\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                sub = marker + "." + key_s
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, sub)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
            if hex_re.search(value):
                violations.append({"category": "hex_digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": key, "count": value} for key, value in sorted(counts.items())]}


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for bucket, phase, expected, input_file in INPUTS:
        artifact, load_status = _load_json(input_file)
        scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
        observed = str(artifact.get("status", "") or "")
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"input_artifact_bucket": bucket, "source_phase_bucket": phase, "load_status": load_status, "expected_status": expected, "observed_status": observed, "forbidden_scan_status": scan_status, "input_gate_passed": passed})
    return rows, ok


def _static_target_inspection_records() -> tuple[list[dict[str, Any]], bool]:
    repo = Path(__file__).resolve().parent.parent
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, rel, markers, required) in enumerate(STATIC_TARGETS):
        source = ""
        exists = (repo / rel).exists()
        if exists:
            source = (repo / rel).read_text(encoding="utf-8")
        count = sum(1 for marker in markers if marker in source)
        passed = (not required and not exists) or (exists and count == len(markers))
        ok = ok and passed
        rows.append({"anonymous_static_target_inspection_id": f"p34st{idx:04d}", "static_target_bucket": bucket, "required_target_bool": required, "exists_bool": exists, "static_text_inspection_only_bool": True, "import_or_execution_performed_bool": False, "required_marker_count": count, "required_marker_total": len(markers), "inspection_status_bucket": "ready" if passed else "missing_or_incomplete"})
    return rows, ok


def _surface_hook_point_design_records() -> list[dict[str, Any]]:
    moments = {
        "support_link": "after_support_candidate_pair_materialization_before_label_or_pack_mutation",
        "scheduler_action_cost": "after_frozen_arm_outcome_materialized_before_aggregate_export",
        "ordered_prefix_stop": "at_prefix_boundary_after_state_materialization_before_stop_decision_output",
        "same_file_redundancy": "after_candidate_pool_materialization_before_final_pack_selection",
        "risk_penalty": "at_risk_accounting_decision_before_filter_or_demote_output_materialized",
    }
    return [{
        "anonymous_hook_point_id": f"p34h{idx:04d}",
        "surface_bucket": surface,
        "target_bucket": SURFACE_TARGET[surface],
        "hook_point_bucket": moments[surface],
        "helper_builder_bucket": "build_" + surface + "_trace_capture_row_private",
        "helper_sanitizer_bucket": "sanitize_" + surface + "_trace_capture_row_public",
        "helper_private_validator_bucket": "validate_" + surface + "_trace_capture_row_private",
        "helper_public_validator_bucket": "validate_" + surface + "_trace_capture_row_public_projection",
        "hook_application_authorized_bool": False,
        "trace_capture_execution_authorized_bool": False,
        "private_trace_row_write_authorized_bool": False,
        "runtime_behavior_mutation_required_bool": False,
        "hook_point_design_complete_bool": True,
    } for idx, surface in enumerate(SURFACES)]


def _hook_event_contract_records() -> list[dict[str, Any]]:
    field_counts = {
        "support_link": 11,
        "scheduler_action_cost": 14,
        "ordered_prefix_stop": 13,
        "same_file_redundancy": 12,
        "risk_penalty": 12,
    }
    return [{
        "anonymous_hook_event_contract_id": f"p34ev{idx:04d}",
        "surface_bucket": surface,
        "event_contract_bucket": "bucketed_trace_event_no_raw_payloads",
        "required_bucket_field_count": field_counts[surface],
        "required_bucket_fields_present_bool": True,
        "source_payload_allowed_bool": False,
        "candidate_list_allowed_bool": False,
        "provider_payload_allowed_bool": False,
        "private_identifier_allowed_bool": False,
        "hook_event_contract_complete_bool": True,
    } for idx, surface in enumerate(SURFACES)]


def _helper_call_contract_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_helper_call_contract_id": f"p34hc{idx:04d}",
        "surface_bucket": surface,
        "private_builder_helper_bucket": "build_" + surface + "_trace_capture_row_private",
        "private_validator_helper_bucket": "validate_" + surface + "_trace_capture_row_private",
        "public_sanitizer_helper_bucket": "sanitize_" + surface + "_trace_capture_row_public",
        "public_validator_helper_bucket": "validate_" + surface + "_trace_capture_row_public_projection",
        "call_order_bucket": "build_private_then_validate_private_then_sanitize_public_then_validate_public",
        "helper_module_bucket": "bea_v1_frozen_trace_logger_helpers",
        "helper_module_already_reviewed_by_p3_3_bool": True,
        "helper_call_authorized_in_p3_4_bool": False,
        "private_trace_row_write_authorized_bool": False,
        "helper_call_contract_complete_bool": True,
    } for idx, surface in enumerate(SURFACES)]


def _frozen_replay_precondition_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(SURFACES):
        scheduler = surface == "scheduler_action_cost"
        rows.append({
            "anonymous_frozen_replay_precondition_id": f"p34fr{idx:04d}",
            "surface_bucket": surface,
            "denominator_bucket": "p4l_locked_non_python_272" if scheduler else "must_be_declared_before_any_hook_application_or_capture",
            "frozen_denominator_declared_before_hook_application_bool": True,
            "frozen_arm_set_declared_before_hook_application_bool": True,
            "no_retrieval_expansion_bool": True,
            "no_ranking_mutation_bool": True,
            "no_packing_mutation_bool": True,
            "no_selection_mutation_bool": True,
            "no_policy_mutation_bool": True,
            "no_provider_calls_bool": True,
            "aggregate_reproduction_gate_required_bool": True if scheduler else False,
            "private_output_path_contract_required_bool": True,
            "public_scanner_required_bool": True,
            "locked_denominator_count_bucket": "p4l_locked_non_python_272" if scheduler else "not_applicable",
            "expected_arm_count_bucket": "four_frozen_arms" if scheduler else "not_applicable",
            "expected_private_row_count_bucket": "one_thousand_eighty_eight" if scheduler else "not_applicable",
        })
    return rows


def _public_private_output_contract_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_output_contract_id": f"p34oc{idx:04d}",
        "surface_bucket": surface,
        "private_output_contract_bucket": "project_ignored_research_private_jsonl_future_only",
        "public_output_contract_bucket": "scanner_safe_bucketed_projection_future_only",
        "private_path_publicly_serialized_bool": False,
        "exact_source_location_publicly_serialized_bool": False,
        "source_snippet_publicly_serialized_bool": False,
        "candidate_list_publicly_serialized_bool": False,
        "provider_payload_publicly_serialized_bool": False,
        "private_write_authorized_in_p3_4_bool": False,
        "public_projection_write_authorized_in_p3_4_bool": False,
        "output_contract_complete_bool": True,
    } for idx, surface in enumerate(SURFACES)]


def _behavior_preservation_gate_records() -> list[dict[str, Any]]:
    gates = (
        "p3_0_p3_1_p3_2_p3_3_inputs_pass_and_scanner_pass",
        "five_surface_hook_point_design_records_present",
        "required_static_targets_ready",
        "helper_call_contracts_defined_for_five_surfaces",
        "event_contracts_bucketed_no_raw_payloads",
        "future_private_writer_contract_no_p3_4_write",
        "no_existing_evaluator_modification",
        "no_helper_module_modification",
        "no_hook_application",
        "no_trace_capture_execution",
        "no_private_trace_row_write",
        "no_retrieval_execution",
        "no_p4l_n1_n2_rerun",
        "no_counterfactual_execution",
        "no_policy_or_selector_change",
        "public_scanner_pass",
        "p3_5_separate_phase_required",
    )
    return [{"anonymous_behavior_gate_id": f"p34bg{idx:04d}", "gate_bucket": gate, "fail_closed_bool": True, "design_only_bool": True, "execution_authorized_bool": False, "behavior_preservation_gate_complete_bool": True} for idx, gate in enumerate(gates)]


def _forbidden_code_touch_records() -> tuple[list[dict[str, Any]], bool]:
    repo = Path(__file__).resolve().parent.parent
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=repo, check=False, capture_output=True, text=True, timeout=10)
        entries = [line for line in proc.stdout.splitlines() if line.strip()]
        available = proc.returncode == 0
    except Exception:
        entries = []
        available = False
    forbidden_existing_mod_count = 0
    forbidden_helper_mod_count = 0
    for line in entries:
        status = line[:2]
        name = line[3:].strip()
        tracked_mod = not status.startswith("??")
        if tracked_mod and name.startswith(("src/", "crates/", "packages/")):
            forbidden_existing_mod_count += 1
        if tracked_mod and name.startswith("eval/") and not name.endswith("bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design.py"):
            forbidden_existing_mod_count += 1
        if tracked_mod and name.endswith("eval/bea_v1_frozen_trace_logger_helpers.py"):
            forbidden_helper_mod_count += 1
    ok = available and forbidden_existing_mod_count == 0 and forbidden_helper_mod_count == 0
    allowed_change_count = len(entries) - forbidden_existing_mod_count - forbidden_helper_mod_count
    disallowed_change_count = forbidden_existing_mod_count + forbidden_helper_mod_count
    return [{"anonymous_forbidden_code_touch_id": "p34ct0000", "git_status_check_available_bool": available, "workspace_change_count": len(entries), "allowed_change_count": allowed_change_count, "disallowed_change_count": disallowed_change_count, "forbidden_existing_evaluator_or_runtime_modification_count": forbidden_existing_mod_count, "frozen_helper_module_modification_count": forbidden_helper_mod_count, "existing_evaluator_files_modified_bool": forbidden_existing_mod_count > 0, "helper_module_modified_bool": forbidden_helper_mod_count > 0, "runtime_or_retrieval_files_modified_bool": False, "allowed_current_phase_change_buckets_only_bool": ok, "forbidden_code_touch_detected_bool": not ok}], ok


def _p3_5_handoff_records() -> list[dict[str, Any]]:
    return [{"anonymous_handoff_id": "p34h0000", "handoff_bucket": "p3_5_frozen_trace_logger_hook_in_patch_plan_review", "p3_5_static_patch_plan_review_authorized": True, "requires_separate_phase_bool": True, "patch_application_authorized_bool": False, "hook_execution_authorized_bool": False, "trace_capture_execution_authorized_bool": False, "private_trace_row_write_authorized_bool": False, "retrieval_execution_authorized_bool": False, "runtime_behavior_change_authorized_bool": False}]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_artifact_records()
    static_records, static_ok = _static_target_inspection_records()
    surface_rows = _surface_hook_point_design_records()
    event_rows = _hook_event_contract_records()
    helper_rows = _helper_call_contract_records()
    replay_rows = _frozen_replay_precondition_records()
    output_rows = _public_private_output_contract_records()
    behavior_rows = _behavior_preservation_gate_records()
    code_touch_rows, code_touch_ok = _forbidden_code_touch_records()
    boundary_ok = all(row["output_contract_complete_bool"] and not row["private_write_authorized_in_p3_4_bool"] and not row["public_projection_write_authorized_in_p3_4_bool"] for row in output_rows) and all(row["behavior_preservation_gate_complete_bool"] and not row["execution_authorized_bool"] for row in behavior_rows)
    surface_ok = len(surface_rows) == 5 and all(row["hook_point_design_complete_bool"] and not row["hook_application_authorized_bool"] for row in surface_rows) and len(event_rows) == 5 and len(helper_rows) == 5
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_4_required_inputs_unavailable"
    elif not static_ok:
        status = "no_go_p3_4_static_anchor_missing"
    elif not surface_ok:
        status = "no_go_p3_4_hook_point_mapping_incomplete"
    elif len(helper_rows) != 5 or not all(row["helper_call_contract_complete_bool"] for row in helper_rows):
        status = "no_go_p3_4_helper_call_contract_incomplete"
    elif not boundary_ok:
        status = "no_go_p3_4_privacy_or_behavior_boundary_incomplete"
    elif not code_touch_ok:
        status = "no_go_p3_4_forbidden_code_touch_detected"
    else:
        status = "frozen_trace_logger_hook_in_preflight_design_pass_p3_5_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": "frozen_trace_logger_hook_in_preflight_design_only",
        "mode": "bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design",
        "phase": "BEA-v1-P3-4",
        "status": status,
        "failure_reason_category": "" if status == "frozen_trace_logger_hook_in_preflight_design_pass_p3_5_authorized" else status.replace("no_go_p3_4_", "").replace("fail_", ""),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "static_target_inspection_records": static_records,
        "surface_hook_point_design_records": surface_rows,
        "hook_event_contract_records": event_rows,
        "helper_call_contract_records": helper_rows,
        "frozen_replay_precondition_records": replay_rows,
        "public_private_output_contract_records": output_rows,
        "behavior_preservation_gate_records": behavior_rows,
        "forbidden_code_touch_records": code_touch_rows,
        "p3_5_handoff_records": _p3_5_handoff_records(),
        "gate_records": [
            {"gate": "four_required_input_artifacts_pass", "passed": input_ok, "threshold_relation": "equals", "value": sum(1 for row in input_records if row["input_gate_passed"]), "threshold_value": 4},
            {"gate": "six_static_targets_inspected", "passed": static_ok, "threshold_relation": "equals", "value": sum(1 for row in static_records if row["inspection_status_bucket"] == "ready"), "threshold_value": 6},
            {"gate": "five_surface_hook_designs_complete", "passed": surface_ok, "threshold_relation": "equals", "value": len(surface_rows), "threshold_value": 5},
            {"gate": "output_and_behavior_boundaries_complete", "passed": boundary_ok, "threshold_relation": "boolean", "value": int(boundary_ok), "threshold_value": 1},
            {"gate": "forbidden_code_touch_absent", "passed": code_touch_ok, "threshold_relation": "boolean", "value": int(code_touch_ok), "threshold_value": 1},
            {"gate": "p3_5_patch_plan_review_only_handoff", "passed": True, "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{"stop_go_decision": status, "stop_go_reason": "hook_in_preflight_design_complete" if status == "frozen_trace_logger_hook_in_preflight_design_pass_p3_5_authorized" else "hook_in_preflight_blocked", "authorization": "frozen_trace_logger_hook_in_preflight_design_only", "next_allowed_phase": "BEA-v1-P3-5 Frozen Trace Logger Hook-In Patch Plan Review — static patch-plan review only, no patch application or trace capture execution", "p3_5_hook_in_patch_plan_review_authorized": status == "frozen_trace_logger_hook_in_preflight_design_pass_p3_5_authorized", "patch_application_authorized": False, "actual_hook_in_authorized": False, "existing_evaluator_hook_authorized": False, "helper_module_modification_authorized": False, "hook_execution_authorized": False, "trace_capture_execution_authorized": False, "private_trace_row_write_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "implementation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}],
        "aggregate_plus_sanitized_records_public_artifact": True,
        "raw_records_publicly_serialized": False,
        "private_paths_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "provider_payloads_publicly_serialized": False,
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    static_records, static_ok = _static_target_inspection_records()
    surface_rows = _surface_hook_point_design_records()
    event_rows = _hook_event_contract_records()
    helper_rows = _helper_call_contract_records()
    replay_rows = _frozen_replay_precondition_records()
    output_rows = _public_private_output_contract_records()
    behavior_rows = _behavior_preservation_gate_records()
    code_touch_rows, _ = _forbidden_code_touch_records()
    handoff = _p3_5_handoff_records()[0]
    parser_ok = False
    try:
        build_parser().parse_args(["--unexpected-secret", "SHOULD_NOT_APPEAR"])
    except SystemExit as exc:
        parser_ok = "SHOULD_NOT_APPEAR" not in str(exc)
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_trace_logger_hook_in_preflight_design_pass_p3_5_authorized", "no_go_p3_4_required_inputs_unavailable", "no_go_p3_4_static_anchor_missing", "no_go_p3_4_hook_point_mapping_incomplete", "no_go_p3_4_helper_call_contract_incomplete", "no_go_p3_4_privacy_or_behavior_boundary_incomplete", "no_go_p3_4_forbidden_code_touch_detected", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("six_static_target_records_present", len(static_records) == 6 and static_ok),
        _check("static_inspection_no_import_or_execution", all(row["static_text_inspection_only_bool"] and not row["import_or_execution_performed_bool"] for row in static_records)),
        _check("five_surface_hook_design_records_present", len(surface_rows) == 5 and {row["surface_bucket"] for row in surface_rows} == set(SURFACES)),
        _check("all_hook_designs_execution_false", not any(row["hook_application_authorized_bool"] or row["trace_capture_execution_authorized_bool"] or row["private_trace_row_write_authorized_bool"] for row in surface_rows)),
        _check("hook_event_contracts_block_raw_payloads", len(event_rows) == 5 and not any(row["source_payload_allowed_bool"] or row["provider_payload_allowed_bool"] or row["candidate_list_allowed_bool"] or row["private_identifier_allowed_bool"] for row in event_rows)),
        _check("helper_call_contracts_design_only", len(helper_rows) == 5 and not any(row["helper_call_authorized_in_p3_4_bool"] or row["private_trace_row_write_authorized_bool"] for row in helper_rows)),
        _check("frozen_replay_preconditions_forbid_mutation", len(replay_rows) == 5 and not any(not row["no_retrieval_expansion_bool"] or not row["no_policy_mutation_bool"] or not row["no_provider_calls_bool"] for row in replay_rows)),
        _check("public_private_output_blocks_forbidden_payloads", len(output_rows) == 5 and not any(row["private_path_publicly_serialized_bool"] or row["exact_source_location_publicly_serialized_bool"] or row["source_snippet_publicly_serialized_bool"] or row["candidate_list_publicly_serialized_bool"] or row["provider_payload_publicly_serialized_bool"] for row in output_rows)),
        _check("behavior_preservation_gates_complete", len(behavior_rows) >= 10 and all(row["fail_closed_bool"] and not row["execution_authorized_bool"] for row in behavior_rows)),
        _check("p3_5_handoff_patch_plan_review_not_execution", handoff["p3_5_static_patch_plan_review_authorized"] and not handoff["patch_application_authorized_bool"] and not handoff["trace_capture_execution_authorized_bool"] and not handoff["private_trace_row_write_authorized_bool"]),
        _check("scanner_accepts_records_and_rejects_path_key", _scan_summary({"static_target_inspection_records": static_records, "surface_hook_point_design_records": surface_rows, "forbidden_code_touch_records": code_touch_rows})["status"] == "pass" and _scan_summary({"path": "blocked"})["status"] == "fail"),
        _check("safe_parser_hides_unknown_arg_values", parser_ok),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-4 frozen trace logger hook-in preflight design")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(args, checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, surfaces={len(report['surface_hook_point_design_records'])}, static_targets={len(report['static_target_inspection_records'])}, p3_5={report['p3_5_handoff_records'][0]['p3_5_static_patch_plan_review_authorized']})")


if __name__ == "__main__":
    main()
