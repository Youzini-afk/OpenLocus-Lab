#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p3_2_frozen_trace_logger_patch_design.v1"
GENERATED_BY = "eval/bea_v1_p3_2_frozen_trace_logger_patch_design.py"
CLAIM_LEVEL = "frozen_trace_logger_patch_design_only"
MODE = "bea_v1_p3_2_frozen_trace_logger_patch_design"
PHASE = "BEA-v1-P3-2"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_2_frozen_trace_logger_patch_design/bea_v1_p3_2_frozen_trace_logger_patch_design_report.json")
DEFAULT_P3_1 = Path("artifacts/bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight/bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight_report.json")

STATUSES = (
    "frozen_trace_logger_patch_design_pass_p3_3_authorized",
    "no_go_p3_2_required_inputs_unavailable",
    "no_go_p3_2_surface_patch_design_incomplete",
    "no_go_p3_2_writer_contract_incomplete",
    "no_go_p3_2_behavior_preservation_gates_incomplete",
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

TARGET_ANCHORS = {
    "support_link": "p0_4_support_link_input_design",
    "scheduler_action_cost": "p0_3_scheduler_dataset_export",
    "ordered_prefix_stop": "p0_6_7_8_parallel_trace_surfaces",
    "same_file_redundancy": "p0_6_7_8_parallel_trace_surfaces",
    "risk_penalty": "p0_6_7_8_parallel_trace_surfaces",
}

PRIVATE_SCHEMAS = {
    "support_link": "bea_v1_support_link_trace_capture.v1",
    "scheduler_action_cost": "bea_v1_scheduler_action_cost_trace_capture.v1",
    "ordered_prefix_stop": "bea_v1_ordered_prefix_stop_trace_capture.v1",
    "same_file_redundancy": "bea_v1_same_file_redundancy_trace_capture.v1",
    "risk_penalty": "bea_v1_risk_penalty_trace_capture.v1",
}


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


def _input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool, dict[str, Any]]:
    artifact, load_status = _load_json(args.p3_1_artifact)
    scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    observed_status = str(artifact.get("status", "") or "")
    surface_count = len(artifact.get("per_surface_preflight_records", [])) if isinstance(artifact.get("per_surface_preflight_records"), list) else 0
    patch_count = len(artifact.get("logging_only_patch_plan_records", [])) if isinstance(artifact.get("logging_only_patch_plan_records"), list) else 0
    handoff = artifact.get("p3_2_handoff_records", [])
    handoff_ok = bool(handoff and isinstance(handoff, list) and isinstance(handoff[0], dict) and handoff[0].get("p3_2_patch_design_authorized") is True and handoff[0].get("patch_application_authorized_bool") is False and handoff[0].get("trace_capture_execution_authorized_bool") is False and handoff[0].get("private_trace_row_write_authorized_bool") is False)
    stop_go = artifact.get("stop_go_records", [])
    stop_go_ok = bool(stop_go and isinstance(stop_go, list) and isinstance(stop_go[0], dict) and stop_go[0].get("p3_2_patch_design_authorized") is True and stop_go[0].get("patch_application_authorized") is False and stop_go[0].get("trace_capture_execution_authorized") is False and stop_go[0].get("private_trace_row_write_authorized") is False and stop_go[0].get("retrieval_execution_authorized") is False)
    ok = load_status == "pass" and observed_status == "frozen_trace_capture_preflight_pass_patch_design_authorized" and scan_status == "pass" and surface_count == 5 and patch_count == 5 and handoff_ok and stop_go_ok
    return [{
        "input_artifact_bucket": "p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight",
        "source_phase_bucket": "BEA-v1-P3-1",
        "load_status": load_status,
        "expected_status": "frozen_trace_capture_preflight_pass_patch_design_authorized",
        "observed_status": observed_status,
        "forbidden_scan_status": scan_status,
        "per_surface_preflight_record_count": surface_count,
        "logging_only_patch_plan_record_count": patch_count,
        "p3_2_patch_design_authorized": bool(handoff_ok),
        "patch_application_authorized": False if handoff_ok else "unexpected_or_missing",
        "trace_capture_execution_authorized": False if handoff_ok else "unexpected_or_missing",
        "private_trace_row_write_authorized": False if handoff_ok else "unexpected_or_missing",
        "retrieval_execution_authorized": False if stop_go_ok else "unexpected_or_missing",
        "input_gate_passed": ok,
    }], ok, artifact


def _surfaces_from_p3_1(p3_1: dict[str, Any]) -> list[str]:
    rows = p3_1.get("per_surface_preflight_records", [])
    if not isinstance(rows, list):
        return []
    surfaces = sorted(str(row.get("surface_bucket", "") or "") for row in rows if isinstance(row, dict) and row.get("surface_bucket"))
    return surfaces


def _surface_patch_design_records(surfaces: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(surfaces):
        rows.append({
            "anonymous_surface_patch_design_id": f"p32s{idx:04d}",
            "surface_bucket": surface,
            "target_anchor_bucket": TARGET_ANCHORS.get(surface, "unknown_anchor"),
            "patch_scope_bucket": "isolated_logging_helper_design_only",
            "helper_module_bucket": "future_frozen_trace_logger_helpers",
            "synthetic_test_required_bool": True,
            "evaluator_hook_in_authorized_bool": False,
            "patch_application_authorized_bool": False,
            "trace_capture_execution_authorized_bool": False,
            "private_trace_row_write_authorized_bool": False,
            "retrieval_execution_authorized_bool": False,
            "runtime_behavior_change_authorized_bool": False,
            "surface_patch_design_complete_bool": surface in SURFACES,
        })
    return rows


def _helper_signature_records(surfaces: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(surfaces):
        rows.append({
            "anonymous_helper_signature_id": f"p32h{idx:04d}",
            "surface_bucket": surface,
            "private_builder_helper_bucket": f"build_{surface}_trace_capture_row_private",
            "public_projection_helper_bucket": f"sanitize_{surface}_trace_capture_row_public",
            "private_validator_helper_bucket": f"validate_{surface}_trace_capture_row_private",
            "public_validator_helper_bucket": f"validate_{surface}_trace_capture_row_public_projection",
            "private_builder_signature_bucket": "build_surface_trace_private_row_frozen_event_context_schema_version_anonymizer_to_private_trace_row",
            "public_sanitizer_signature_bucket": "sanitize_surface_trace_public_row_private_trace_to_scanner_safe_projection",
            "private_validator_signature_bucket": "validate_surface_trace_private_row_to_validation_result",
            "public_validator_signature_bucket": "validate_surface_trace_public_projection_to_validation_result",
            "private_schema_bucket": PRIVATE_SCHEMAS.get(surface, "unknown_schema"),
            "public_projection_bucket": "scanner_safe_bucketed_public_projection",
            "input_contract_bucket": "bucketed_trace_inputs_no_source_payloads",
            "deterministic_helper_bool": True,
            "side_effect_free_helper_bool": True,
            "io_in_helper_authorized_bool": False,
            "trace_capture_execution_authorized_bool": False,
        })
    return rows


def _writer_contract_records(surfaces: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(surfaces):
        rows.append({
            "anonymous_writer_contract_id": f"p32w{idx:04d}",
            "surface_bucket": surface,
            "private_writer_contract_bucket": "project_ignored_research_private_jsonl_future_only",
            "public_writer_contract_bucket": "scanner_safe_bucketed_public_artifact_future_only",
            "writer_contract_bucket": "future_project_ignored_research_private_jsonl_writer",
            "private_schema_bucket": PRIVATE_SCHEMAS.get(surface, "unknown_schema"),
            "append_only_future_writer_bool": True,
            "fail_closed_on_schema_error_bool": True,
            "fail_closed_on_public_scanner_error_bool": True,
            "private_trace_row_write_authorized_in_p3_2_bool": False,
            "public_projection_write_authorized_in_p3_2_bool": False,
            "private_trace_row_write_authorized_in_p3_3_bool": False,
            "trace_capture_execution_authorized_in_p3_3_bool": False,
            "public_projection_required_bool": True,
            "writer_contract_complete_bool": surface in SURFACES,
        })
    return rows


def _code_change_constraint_records() -> list[dict[str, Any]]:
    constraints = (
        "isolated_helper_module_only",
        "new_isolated_helper_module_only_preferred",
        "synthetic_tests_only",
        "no_evaluator_hook_in",
        "existing_evaluator_behavior_hooks_not_authorized",
        "no_runtime_behavior_change",
        "no_retrieval_execution",
        "no_provider_calls",
        "no_ranking_mutation",
        "no_packing_mutation",
        "no_selection_mutation",
        "no_trace_capture_execution",
        "no_private_row_write",
        "no_policy_or_selector_change",
        "scanner_must_pass",
        "safe_parser_must_hide_unknown_values",
    )
    return [{
        "anonymous_code_change_constraint_id": f"p32c{idx:04d}",
        "constraint_bucket": constraint,
        "required_bool": True,
        "patch_application_authorized_bool": False,
        "behavior_mutation_authorized_bool": False,
        "trace_capture_execution_authorized_bool": False,
    } for idx, constraint in enumerate(constraints)]


def _behavior_preservation_review_gate_records() -> list[dict[str, Any]]:
    gates = (
        "p3_1_input_status_and_scan_pass",
        "five_surface_patch_design_records_present",
        "five_private_builders_defined",
        "five_public_sanitizers_defined",
        "five_private_validators_defined",
        "five_public_validators_defined",
        "writer_contracts_no_write_in_p3_2",
        "p3_3_limited_to_isolated_helper_patch",
        "existing_evaluator_behavior_hooks_forbidden",
        "no_retrieval_ranking_packing_selection_policy_mutation",
        "no_trace_capture_execution",
        "no_private_rows_written",
        "synthetic_tests_only",
        "public_scanner_required",
        "p3_3_separate_phase_required",
        "no_retrieval_result_change",
        "no_ranking_or_packing_change",
        "no_scheduler_policy_change",
        "no_support_label_change",
        "no_counterfactual_execution",
        "no_private_trace_write",
        "public_scanner_pass_required",
        "synthetic_tests_required_before_helper_patch",
    )
    return [{
        "anonymous_behavior_gate_id": f"p32g{idx:04d}",
        "gate_bucket": gate,
        "fail_closed_bool": True,
        "review_required_bool": True,
        "behavior_preservation_gate_complete_bool": True,
        "execution_authorized_bool": False,
    } for idx, gate in enumerate(gates)]


def _synthetic_test_plan_records(surfaces: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(surfaces):
        rows.append({
            "anonymous_synthetic_test_plan_id": f"p32t{idx:04d}",
            "surface_bucket": surface,
            "test_scope_bucket": "helper_unit_tests_with_synthetic_bucket_inputs_only",
            "synthetic_valid_private_row_required_bool": True,
            "synthetic_invalid_private_row_required_bool": True,
            "public_sanitizer_output_required_bool": True,
            "privacy_negative_test_bucket": "scanner_rejects_path_span_snippet_provider_candidate_list_keys",
            "scanner_negative_test_bucket": "public_projection_forbidden_key_rejection",
            "behavior_preservation_test_bucket": "helpers_no_filesystem_writes_no_retrieval_imports_no_target_evaluator_calls",
            "scanner_fixture_required_bool": True,
            "schema_fixture_required_bool": True,
            "privacy_boundary_fixture_required_bool": True,
            "uses_real_private_rows_bool": False,
            "retrieval_execution_authorized_bool": False,
            "trace_capture_execution_authorized_bool": False,
            "test_plan_complete_bool": surface in SURFACES,
        })
    return rows


def _p3_3_handoff_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_handoff_id": "p32hnd0000",
        "handoff_bucket": "p3_3_frozen_trace_logger_isolated_helper_patch_review",
        "p3_3_helper_patch_review_authorized": True,
        "p3_3_isolated_helper_patch_application_authorized": True,
        "p3_3_scope_bucket": "isolated_helper_module_and_synthetic_tests_only",
        "requires_separate_phase_bool": True,
        "isolated_helper_module_patch_authorized_bool": True,
        "synthetic_tests_authorized_bool": True,
        "evaluator_hook_in_authorized_bool": False,
        "trace_capture_execution_authorized_bool": False,
        "private_trace_row_write_authorized_bool": False,
        "retrieval_execution_authorized_bool": False,
        "runtime_behavior_change_authorized_bool": False,
    }]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok, p3_1 = _input_artifact_records(args)
    surfaces = _surfaces_from_p3_1(p3_1)
    surface_rows = _surface_patch_design_records(surfaces)
    helper_rows = _helper_signature_records(surfaces)
    writer_rows = _writer_contract_records(surfaces)
    constraint_rows = _code_change_constraint_records()
    behavior_rows = _behavior_preservation_review_gate_records()
    test_rows = _synthetic_test_plan_records(surfaces)
    handoff_rows = _p3_3_handoff_records()
    self_tests_ok = all(c["passed"] for c in checks)
    surface_complete = len(surface_rows) == 5 and {row["surface_bucket"] for row in surface_rows} == set(SURFACES) and all(row["surface_patch_design_complete_bool"] and not row["patch_application_authorized_bool"] and not row["trace_capture_execution_authorized_bool"] for row in surface_rows)
    writer_complete = len(writer_rows) == 5 and all(row["writer_contract_complete_bool"] and row["fail_closed_on_schema_error_bool"] and row["fail_closed_on_public_scanner_error_bool"] and not row["private_trace_row_write_authorized_in_p3_2_bool"] and not row["private_trace_row_write_authorized_in_p3_3_bool"] for row in writer_rows)
    helper_complete = len(helper_rows) == 5 and all(row.get("private_builder_helper_bucket") and row.get("public_projection_helper_bucket") and row.get("private_validator_helper_bucket") and row.get("public_validator_helper_bucket") for row in helper_rows)
    test_plan_complete = len(test_rows) == 5 and all(row.get("synthetic_valid_private_row_required_bool") and row.get("synthetic_invalid_private_row_required_bool") and row.get("public_sanitizer_output_required_bool") and not row.get("uses_real_private_rows_bool") for row in test_rows)
    behavior_complete = len(behavior_rows) >= 15 and len(constraint_rows) >= 14 and helper_complete and test_plan_complete and all(row["behavior_preservation_gate_complete_bool"] and row["fail_closed_bool"] and not row["execution_authorized_bool"] for row in behavior_rows) and all(not row["behavior_mutation_authorized_bool"] and not row["trace_capture_execution_authorized_bool"] for row in constraint_rows)
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_2_required_inputs_unavailable"
    elif not surface_complete:
        status = "no_go_p3_2_surface_patch_design_incomplete"
    elif not writer_complete:
        status = "no_go_p3_2_writer_contract_incomplete"
    elif not behavior_complete:
        status = "no_go_p3_2_behavior_preservation_gates_incomplete"
    else:
        status = "frozen_trace_logger_patch_design_pass_p3_3_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "frozen_trace_logger_patch_design_pass_p3_3_authorized" else "required_inputs_unavailable" if status == "no_go_p3_2_required_inputs_unavailable" else "surface_patch_design_incomplete" if status == "no_go_p3_2_surface_patch_design_incomplete" else "writer_contract_incomplete" if status == "no_go_p3_2_writer_contract_incomplete" else "behavior_preservation_gates_incomplete" if status == "no_go_p3_2_behavior_preservation_gates_incomplete" else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "surface_patch_design_records": surface_rows,
        "helper_signature_records": helper_rows,
        "writer_contract_records": writer_rows,
        "code_change_constraint_records": constraint_rows,
        "behavior_preservation_review_gate_records": behavior_rows,
        "synthetic_test_plan_records": test_rows,
        "p3_3_handoff_records": handoff_rows,
        "gate_records": [
            {"gate": "p3_1_required_input_pass", "passed": input_ok, "threshold_relation": "boolean", "value": int(input_ok), "threshold_value": 1},
            {"gate": "five_surface_patch_design_records_complete", "passed": surface_complete, "threshold_relation": "equals", "value": len(surface_rows), "threshold_value": 5},
            {"gate": "helper_signature_records_complete", "passed": helper_complete, "threshold_relation": "equals", "value": len(helper_rows), "threshold_value": 5},
            {"gate": "writer_contract_records_complete", "passed": writer_complete, "threshold_relation": "equals", "value": len(writer_rows), "threshold_value": 5},
            {"gate": "synthetic_test_plan_records_complete", "passed": test_plan_complete, "threshold_relation": "equals", "value": len(test_rows), "threshold_value": 5},
            {"gate": "behavior_preservation_gates_complete", "passed": behavior_complete, "threshold_relation": "boolean", "value": int(behavior_complete), "threshold_value": 1},
            {"gate": "p3_3_patch_review_authorized_not_execution", "passed": handoff_rows[0]["p3_3_helper_patch_review_authorized"] and not handoff_rows[0]["trace_capture_execution_authorized_bool"], "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "frozen_trace_logger_patch_design_ready_for_p3_3" if status == "frozen_trace_logger_patch_design_pass_p3_3_authorized" else "patch_design_blocked",
            "authorization": "p3_2_logging_only_patch_design_only",
            "next_allowed_phase": "BEA-v1-P3-3 Frozen Trace Logger Isolated Helper Patch Review — isolated helper patch and synthetic tests only, no trace capture execution",
            "p3_3_helper_patch_review_authorized": status == "frozen_trace_logger_patch_design_pass_p3_3_authorized",
            "p3_3_isolated_helper_patch_application_authorized": status == "frozen_trace_logger_patch_design_pass_p3_3_authorized",
            "isolated_helper_module_patch_authorized_in_p3_3": status == "frozen_trace_logger_patch_design_pass_p3_3_authorized",
            "synthetic_tests_authorized_in_p3_3": status == "frozen_trace_logger_patch_design_pass_p3_3_authorized",
            "patch_application_authorized_in_p3_2": False,
            "evaluator_hook_in_authorized": False,
            "trace_capture_execution_authorized": False,
            "private_trace_row_write_authorized": False,
            "retrieval_execution_authorized": False,
            "p4l_rerun_authorized": False,
            "n1_n2_rerun_authorized": False,
            "support_labeling_authorized": False,
            "trace_counterfactual_execution_authorized": False,
            "support_counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
            "implementation_authorized": False,
            "selector_or_reranker_authorized": False,
            "p5_authorized": False,
            "v1_a_authorized": False,
            "runtime_promotion_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "method_winner_claimed": False,
            "downstream_value_claimed": False,
        }],
        "aggregate_plus_sanitized_records_public_artifact": True,
        "raw_records_publicly_serialized": False,
        "private_paths_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "provider_payloads_publicly_serialized": False,
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
    }
    scan = tg._scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
    report["forbidden_scan"] = tg._scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    surfaces: list[str] = sorted(str(surface) for surface in SURFACES)
    surface_rows = _surface_patch_design_records(surfaces)
    helper_rows = _helper_signature_records(surfaces)
    writer_rows = _writer_contract_records(surfaces)
    constraints = _code_change_constraint_records()
    behavior = _behavior_preservation_review_gate_records()
    tests = _synthetic_test_plan_records(surfaces)
    handoff = _p3_3_handoff_records()[0]
    parser_ok = False
    try:
        build_parser().parse_args(["--bad-secret-value", "SHOULD_NOT_APPEAR"])
    except SystemExit as exc:
        parser_ok = "SHOULD_NOT_APPEAR" not in str(exc)
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_trace_logger_patch_design_pass_p3_3_authorized", "no_go_p3_2_required_inputs_unavailable", "no_go_p3_2_surface_patch_design_incomplete", "no_go_p3_2_writer_contract_incomplete", "no_go_p3_2_behavior_preservation_gates_incomplete", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("five_surface_patch_design_records", len(surface_rows) == 5 and {row["surface_bucket"] for row in surface_rows} == set(SURFACES)),
        _check("five_helper_signature_records", len(helper_rows) == 5 and all(row["deterministic_helper_bool"] and row["side_effect_free_helper_bool"] and row.get("private_validator_helper_bucket") and row.get("public_validator_helper_bucket") for row in helper_rows)),
        _check("five_writer_contract_records", len(writer_rows) == 5 and all(row["writer_contract_complete_bool"] and row.get("private_writer_contract_bucket") and row.get("public_writer_contract_bucket") for row in writer_rows)),
        _check("all_patch_designs_execution_false", not any(row["patch_application_authorized_bool"] or row["trace_capture_execution_authorized_bool"] or row["private_trace_row_write_authorized_bool"] for row in surface_rows)),
        _check("writer_contracts_no_private_write", not any(row["private_trace_row_write_authorized_in_p3_2_bool"] or row["private_trace_row_write_authorized_in_p3_3_bool"] for row in writer_rows)),
        _check("behavior_preservation_gates_complete", len(behavior) >= 15 and all(row["fail_closed_bool"] and row["behavior_preservation_gate_complete_bool"] for row in behavior)),
        _check("code_change_constraints_forbid_mutation", not any(row["behavior_mutation_authorized_bool"] or row["trace_capture_execution_authorized_bool"] for row in constraints)),
        _check("synthetic_tests_do_not_use_real_rows", len(tests) == 5 and all(row.get("synthetic_valid_private_row_required_bool") and row.get("synthetic_invalid_private_row_required_bool") and row.get("public_sanitizer_output_required_bool") for row in tests) and not any(row["uses_real_private_rows_bool"] or row["retrieval_execution_authorized_bool"] for row in tests)),
        _check("p3_3_handoff_patch_review_not_execution", handoff["p3_3_helper_patch_review_authorized"] and handoff["p3_3_isolated_helper_patch_application_authorized"] and handoff["isolated_helper_module_patch_authorized_bool"] and handoff["synthetic_tests_authorized_bool"] and not handoff["evaluator_hook_in_authorized_bool"] and not handoff["trace_capture_execution_authorized_bool"]),
        _check("scanner_accepts_patch_design_rows", tg._scan_summary({"surface_patch_design_records": surface_rows, "helper_signature_records": helper_rows, "writer_contract_records": writer_rows, "code_change_constraint_records": constraints})["status"] == "pass"),
        _check("safe_parser_hides_unknown_arg_values", parser_ok and tg._scan_summary({"path": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-2 frozen trace logger patch design")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p3-1-artifact", type=Path, default=DEFAULT_P3_1)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, surfaces={len(report['surface_patch_design_records'])}, writers={len(report['writer_contract_records'])}, p3_3={report['p3_3_handoff_records'][0]['p3_3_helper_patch_review_authorized']})")


if __name__ == "__main__":
    main()
