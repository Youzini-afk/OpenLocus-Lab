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


SCHEMA_VERSION = "bea_v1_p3_0_frozen_upstream_trace_capture_harness_design.v1"
GENERATED_BY = "eval/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design.py"
CLAIM_LEVEL = "frozen_upstream_trace_capture_harness_design_only"
MODE = "bea_v1_p3_0_frozen_upstream_trace_capture_harness_design"
PHASE = "BEA-v1-P3-0"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design_report.json")
DEFAULT_P2_3 = Path("artifacts/bea_v1_p2_3_late_trace_surface_closure/bea_v1_p2_3_late_trace_surface_closure_report.json")

STATUSES = (
    "frozen_upstream_trace_capture_harness_design_pass",
    "no_go_p3_0_required_inputs_unavailable",
    "no_go_p3_0_surface_mapping_incomplete",
    "no_go_p3_0_instrumentation_plan_incomplete",
    "no_go_p3_0_privacy_boundary_incomplete",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SURFACES = (
    {
        "surface_bucket": "support_link",
        "schema_version_bucket": "bea_v1_support_link_trace_capture.v1",
        "private_required_field_count": 12,
        "public_projection_field_count": 8,
        "private_field_buckets": ["anonymous_design_join_key", "queue_item_join_key", "support_relation_bucket", "target_hit_bucket", "support_hit_bucket", "conjunction_bucket", "evidence_role_bucket", "leakage_risk_bucket", "source_context_linkage_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"],
        "public_field_buckets": ["surface_bucket", "relation_bucket", "target_hit_bucket", "support_hit_bucket", "conjunction_bucket", "role_bucket", "risk_bucket", "trace_completeness_bucket"],
        "instrumentation_target_bucket": "support_candidate_selection_and_context_pack_join",
        "existing_eval_or_helper_bucket": "p0_4_support_link_input_design_and_p1_2_private_label_intake_validator",
        "capture_moment_bucket": "after_target_and_support_candidate_materialization_before_pack_mutation",
        "denominator_source_bucket": "p1_1_support_labeling_queue_or_future_frozen_trace_denominator",
    },
    {
        "surface_bucket": "scheduler_action_cost",
        "schema_version_bucket": "bea_v1_scheduler_action_cost_trace_capture.v1",
        "private_required_field_count": 14,
        "public_projection_field_count": 9,
        "private_field_buckets": ["locked_denominator_join_key", "arm_bucket", "action_sequence_bucket", "latency_bucket", "pool_size_bucket", "pool_delta_bucket", "hard_cap_bucket", "file_reach_bucket", "cost_state_bucket", "scheduler_state_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"],
        "public_field_buckets": ["surface_bucket", "arm_bucket", "latency_bucket", "pool_delta_bucket", "hard_cap_bucket", "file_reach_bucket", "cost_state_bucket", "trace_completeness_bucket", "replay_freeze_bucket"],
        "instrumentation_target_bucket": "p4l_frozen_action_scheduler_arm_evaluation",
        "existing_eval_or_helper_bucket": "p4l_locked_non_python_scheduler_validation_and_p0_3_scheduler_dataset_export",
        "capture_moment_bucket": "after_each_frozen_scheduler_arm_before_aggregate_export",
        "denominator_source_bucket": "p4l_locked_non_python_denominator_272",
    },
    {
        "surface_bucket": "ordered_prefix_stop",
        "schema_version_bucket": "bea_v1_ordered_prefix_stop_trace_capture.v1",
        "private_required_field_count": 13,
        "public_projection_field_count": 9,
        "private_field_buckets": ["prefix_join_key", "arm_bucket", "prefix_position_bucket", "prefix_cost_bucket", "budget_remaining_bucket", "marginal_gain_bucket", "stop_policy_bucket", "continue_reference_bucket", "early_stop_signal_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"],
        "public_field_buckets": ["surface_bucket", "arm_bucket", "prefix_position_bucket", "prefix_cost_bucket", "budget_remaining_bucket", "marginal_gain_bucket", "stop_policy_bucket", "continue_bucket", "trace_completeness_bucket"],
        "instrumentation_target_bucket": "ordered_prefix_scheduler_stop_decision",
        "existing_eval_or_helper_bucket": "p0_6_7_8_parallel_trace_surfaces_and_future_frozen_replay_logger",
        "capture_moment_bucket": "at_each_prefix_boundary_before_stop_or_continue_decision",
        "denominator_source_bucket": "future_frozen_ordered_prefix_trace_denominator_declared_before_capture",
    },
    {
        "surface_bucket": "same_file_redundancy",
        "schema_version_bucket": "bea_v1_same_file_redundancy_trace_capture.v1",
        "private_required_field_count": 12,
        "public_projection_field_count": 8,
        "private_field_buckets": ["redundancy_join_key", "action_layer_bucket", "action_arm_bucket", "duplicate_pressure_bucket", "same_file_candidate_count_bucket", "topk_file_diversity_bucket", "gold_file_displacement_bucket", "marginal_utility_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"],
        "public_field_buckets": ["surface_bucket", "action_layer_bucket", "action_arm_bucket", "duplicate_pressure_bucket", "same_file_count_bucket", "diversity_bucket", "gold_effect_bucket", "trace_completeness_bucket"],
        "instrumentation_target_bucket": "rank_pack_materialization_and_setwise_packer_redundancy",
        "existing_eval_or_helper_bucket": "p0_6_7_8_parallel_trace_surfaces_and_future_frozen_pack_logger",
        "capture_moment_bucket": "after_candidate_pool_materialization_before_final_pack_selection",
        "denominator_source_bucket": "future_frozen_redundancy_trace_denominator_declared_before_capture",
    },
    {
        "surface_bucket": "risk_penalty",
        "schema_version_bucket": "bea_v1_risk_penalty_trace_capture.v1",
        "private_required_field_count": 12,
        "public_projection_field_count": 9,
        "private_field_buckets": ["risk_join_key", "action_layer_bucket", "action_arm_bucket", "risk_class_bucket", "risk_policy_bucket", "removed_gold_bucket", "replacement_bucket", "topk_effect_bucket", "counterfactual_keep_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"],
        "public_field_buckets": ["surface_bucket", "action_layer_bucket", "action_arm_bucket", "risk_class_bucket", "risk_policy_bucket", "removed_gold_bucket", "replacement_bucket", "counterfactual_keep_bucket", "trace_completeness_bucket"],
        "instrumentation_target_bucket": "file_selector_or_risk_accounting_filter",
        "existing_eval_or_helper_bucket": "p0_6_7_8_parallel_trace_surfaces_and_future_risk_policy_logger",
        "capture_moment_bucket": "at_risk_penalty_decision_before_filter_output_is_materialized",
        "denominator_source_bucket": "future_frozen_risk_trace_denominator_declared_before_capture",
    },
)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _trace_schema_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, surface in enumerate(SURFACES):
        rows.append({
            "anonymous_trace_schema_id": f"p30s{i:04d}",
            "surface_bucket": surface["surface_bucket"],
            "schema_version_bucket": surface["schema_version_bucket"],
            "private_required_field_count": surface["private_required_field_count"],
            "public_projection_field_count": surface["public_projection_field_count"],
            "private_required_field_buckets": surface["private_field_buckets"],
            "public_projection_field_buckets": surface["public_field_buckets"],
            "schema_scope_bucket": "private_trace_rows_with_scanner_safe_public_projection",
            "schema_status_bucket": "design_only_not_executed",
        })
    return rows


def _instrumentation_point_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, surface in enumerate(SURFACES):
        rows.append({
            "anonymous_instrumentation_point_id": f"p30i{i:04d}",
            "surface_bucket": surface["surface_bucket"],
            "static_target_bucket": surface["instrumentation_target_bucket"],
            "existing_eval_or_helper_bucket": surface["existing_eval_or_helper_bucket"],
            "capture_moment_bucket": surface["capture_moment_bucket"],
            "target_implementation_bucket": "future_frozen_trace_logger_required",
            "private_output_schema_bucket": surface["schema_version_bucket"],
            "public_projection_schema_bucket": "scanner_safe_bucketed_public_projection",
            "mutation_allowed_bool": False,
            "execution_in_p3_0_bool": False,
            "trace_capture_execution_authorized_bool": False,
            "retrieval_execution_authorized_bool": False,
        })
    return rows


def _frozen_replay_requirement_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, surface in enumerate(SURFACES):
        scheduler = surface["surface_bucket"] == "scheduler_action_cost"
        rows.append({
            "anonymous_frozen_replay_requirement_id": f"p30r{i:04d}",
            "surface_bucket": surface["surface_bucket"],
            "denominator_source_bucket": surface["denominator_source_bucket"],
            "locked_denominator_count": 272 if scheduler else 0,
            "frozen_arm_count": 4 if scheduler else 0,
            "expected_private_row_count": 1088 if scheduler else 0,
            "denominator_declared_before_capture_bool": bool(scheduler),
            "denominator_must_be_declared_before_p3_1_execution_bool": True,
            "retrieval_expansion_allowed_bool": False,
            "policy_mutation_allowed_bool": False,
            "runtime_promotion_allowed_bool": False,
            "provider_execution_allowed_bool": False,
            "p4l_rerun_allowed_bool": False,
            "n1_n2_rerun_allowed_bool": False,
        })
    return rows


def _public_private_boundary_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, surface in enumerate(SURFACES):
        rows.append({
            "anonymous_boundary_id": f"p30b{i:04d}",
            "surface_bucket": surface["surface_bucket"],
            "private_storage_bucket": "project_ignored_research_private_jsonl",
            "public_projection_bucket": "aggregate_and_bucketed_rows_only",
            "raw_payload_public_bool": False,
            "private_location_public_bool": False,
            "source_location_public_bool": False,
            "source_span_public_bool": False,
            "snippet_public_bool": False,
            "candidate_list_public_bool": False,
            "provider_payload_public_bool": False,
            "digest_public_bool": False,
        })
    return rows


def _fail_closed_validation_gate_records() -> list[dict[str, Any]]:
    gates = [
        "p2_3_input_status_and_scan_pass",
        "private_schema_version_present",
        "public_projection_scanner_pass",
        "no_public_source_location_or_span",
        "no_public_payload_or_candidate_list",
        "capture_phase_separate_from_execution",
        "frozen_denominator_declared_before_capture",
        "p3_1_preflight_required_before_any_capture",
    ]
    return [{"anonymous_validation_gate_id": f"p30g{i:04d}", "gate_bucket": gate, "fail_closed_bool": True, "execution_in_p3_0_bool": False} for i, gate in enumerate(gates)]


def _p3_1_handoff_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_handoff_id": "p30h0000",
        "handoff_bucket": "p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight",
        "authorization_bucket": "p3_1_preflight_authorized_design_only",
        "p3_1_preflight_authorized": True,
        "p3_1_scope_bucket": "dry_run_preflight_design_only",
        "trace_capture_execution_authorized_bool": False,
        "retrieval_execution_authorized_bool": False,
        "policy_mutation_authorized_bool": False,
        "requires_separate_phase_bool": True,
    }]


def _input_record(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    artifact, load_status = _load_json(args.p2_3_artifact)
    scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    observed_status = str(artifact.get("status", "") or "")
    ok = load_status == "pass" and observed_status == "late_trace_surface_closure_no_go" and scan_status == "pass"
    return [{
        "input_artifact_bucket": "p2_3_late_trace_surface_closure",
        "source_phase_bucket": "BEA-v1-P2-3",
        "load_status": load_status,
        "expected_status": "late_trace_surface_closure_no_go",
        "observed_status": observed_status,
        "forbidden_scan_status": scan_status,
        "input_gate_passed": ok,
    }], ok


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = _input_record(args)
    schemas = _trace_schema_records()
    instrumentation = _instrumentation_point_records()
    replay = _frozen_replay_requirement_records()
    boundaries = _public_private_boundary_records()
    gates = _fail_closed_validation_gate_records()
    handoff = _p3_1_handoff_records()
    self_tests_ok = all(c["passed"] for c in checks)
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_0_required_inputs_unavailable"
    else:
        status = "frozen_upstream_trace_capture_harness_design_pass"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "frozen_upstream_trace_capture_harness_design_pass" else "required_inputs_unavailable" if status == "no_go_p3_0_required_inputs_unavailable" else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": inputs,
        "trace_schema_records": schemas,
        "instrumentation_point_records": instrumentation,
        "frozen_replay_requirement_records": replay,
        "public_private_boundary_records": boundaries,
        "fail_closed_validation_gate_records": gates,
        "p3_1_handoff_records": handoff,
        "gate_records": [
            {"gate": "p2_3_input_status_and_scan_pass", "passed": input_ok, "threshold_relation": "boolean", "value": int(input_ok), "threshold_value": 1},
            {"gate": "five_trace_schema_records", "passed": len(schemas) == 5, "threshold_relation": "equals", "value": len(schemas), "threshold_value": 5},
            {"gate": "five_instrumentation_point_records", "passed": len(instrumentation) == 5, "threshold_relation": "equals", "value": len(instrumentation), "threshold_value": 5},
            {"gate": "execution_not_in_p3_0", "passed": not any(row["execution_in_p3_0_bool"] for row in instrumentation), "threshold_relation": "boolean", "value": 1 if not any(row["execution_in_p3_0_bool"] for row in instrumentation) else 0, "threshold_value": 1},
            {"gate": "p3_1_preflight_authorized", "passed": handoff[0]["p3_1_preflight_authorized"], "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "frozen_upstream_trace_capture_harness_design_ready" if status == "frozen_upstream_trace_capture_harness_design_pass" else "required_inputs_unavailable",
            "next_allowed_phase": "BEA-v1-P3-1 Frozen Upstream Trace-Capture Harness Dry-Run Preflight",
            "authorization": "frozen_upstream_trace_capture_harness_design_only",
            "p3_1_preflight_authorized": status == "frozen_upstream_trace_capture_harness_design_pass",
            "trace_capture_execution_authorized": False,
            "retrieval_execution_authorized": False,
            "p4l_rerun_authorized": False,
            "n1_n2_rerun_authorized": False,
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
    schemas = _trace_schema_records()
    instr = _instrumentation_point_records()
    replay = _frozen_replay_requirement_records()
    boundaries = _public_private_boundary_records()
    handoff = _p3_1_handoff_records()[0]
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_upstream_trace_capture_harness_design_pass", "no_go_p3_0_required_inputs_unavailable", "no_go_p3_0_surface_mapping_incomplete", "no_go_p3_0_instrumentation_plan_incomplete", "no_go_p3_0_privacy_boundary_incomplete", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("five_trace_schema_records_present", len(schemas) == 5 and {row["surface_bucket"] for row in schemas} == {s["surface_bucket"] for s in SURFACES}),
        _check("five_instrumentation_point_records_present", len(instr) == 5 and {row["surface_bucket"] for row in instr} == {s["surface_bucket"] for s in SURFACES}),
        _check("instrumentation_records_have_schema_links", all(row.get("private_output_schema_bucket") and row.get("public_projection_schema_bucket") for row in instr)),
        _check("all_schema_records_have_private_and_public_projection", all(row["private_required_field_count"] > 0 and row["public_projection_field_count"] > 0 for row in schemas)),
        _check("all_instrumentation_records_execution_false", not any(row["execution_in_p3_0_bool"] for row in instr)),
        _check("frozen_replay_requirements_forbid_policy_mutation", not any(row["policy_mutation_allowed_bool"] or row["retrieval_expansion_allowed_bool"] or row["runtime_promotion_allowed_bool"] for row in replay)),
        _check("public_private_boundary_blocks_raw_payloads", not any(row["raw_payload_public_bool"] or row["provider_payload_public_bool"] or row["candidate_list_public_bool"] for row in boundaries)),
        _check("scanner_accepts_design_rows", tg._scan_summary({"trace_schema_records": schemas, "instrumentation_point_records": instr, "public_private_boundary_records": boundaries})["status"] == "pass"),
        _check("scanner_rejects_path_key", tg._scan_summary({"path": "x"})["status"] == "fail"),
        _check("p3_1_handoff_requires_separate_phase", handoff["p3_1_preflight_authorized"] is True and handoff["authorization_bucket"] == "p3_1_preflight_authorized_design_only" and handoff["requires_separate_phase_bool"] is True and handoff["trace_capture_execution_authorized_bool"] is False),
        _check("safe_parser_hides_unknown_argument_values", _safe_parser_hides_unknown_argument_values()),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _safe_parser_hides_unknown_argument_values() -> bool:
    try:
        build_parser().parse_args(["--private-path", "/tmp/private/should/not/leak"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments"
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-0 frozen upstream trace-capture harness design")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p2-3-artifact", type=Path, default=DEFAULT_P2_3)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, schemas={len(report['trace_schema_records'])}, instrumentation={len(report['instrumentation_point_records'])}, p3_1={report['p3_1_handoff_records'][0]['p3_1_preflight_authorized']})")


if __name__ == "__main__":
    main()
