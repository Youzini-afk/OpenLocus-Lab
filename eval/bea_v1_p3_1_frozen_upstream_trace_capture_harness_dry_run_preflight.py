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


SCHEMA_VERSION = "bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight.v1"
GENERATED_BY = "eval/bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight.py"
CLAIM_LEVEL = "frozen_upstream_trace_capture_harness_dry_run_preflight_only"
MODE = "bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight"
PHASE = "BEA-v1-P3-1"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight/bea_v1_p3_1_frozen_upstream_trace_capture_harness_dry_run_preflight_report.json")
DEFAULT_P3_0 = Path("artifacts/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design_report.json")

STATUSES = (
    "frozen_trace_capture_preflight_pass_patch_design_authorized",
    "no_go_p3_1_required_inputs_unavailable",
    "no_go_p3_1_surface_preflight_incomplete",
    "no_go_p3_1_static_anchor_missing",
    "no_go_p3_1_privacy_or_fail_closed_boundary_incomplete",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

ANCHORS = (
    {
        "anchor_bucket": "p0_3_scheduler_dataset_export",
        "path": Path("eval/bea_v1_p0_3_scheduler_dataset_export.py"),
        "required": True,
        "markers": ("scheduler_dataset_export", "PRIVATE_ARM_SCHEMA", "_sanitize_private_arm_rows"),
    },
    {
        "anchor_bucket": "p0_4_support_link_input_design",
        "path": Path("eval/bea_v1_p0_4_support_link_input_design.py"),
        "required": True,
        "markers": ("support_link", "support_relation", "target_hit"),
    },
    {
        "anchor_bucket": "p0_6_7_8_parallel_trace_surfaces",
        "path": Path("eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py"),
        "required": True,
        "markers": ("same_file_redundancy", "risk_penalty", "ordered_prefix"),
    },
    {
        "anchor_bucket": "p1_2_private_label_intake_validator",
        "path": Path("eval/bea_v1_p1_2_private_label_intake_validator.py"),
        "required": True,
        "markers": ("private_label", "intake", "support"),
    },
    {
        "anchor_bucket": "p4l_locked_scheduler_validation_optional",
        "path": Path("eval/bea_v1_p4l_locked_non_python_scheduler_validation.py"),
        "required": False,
        "markers": ("p4l", "scheduler"),
    },
    {
        "anchor_bucket": "n1_span_refiner_optional",
        "path": Path("eval/bea_v1_n1_frozen_p4_span_refiner_smoke.py"),
        "required": False,
        "markers": ("span", "refiner"),
    },
    {
        "anchor_bucket": "n2_rank_pack_actionability_optional",
        "path": Path("eval/bea_v1_n2_rank_pack_actionability_decomposition.py"),
        "required": False,
        "markers": ("rank", "pack"),
    },
)

SURFACE_TO_ANCHOR = {
    "support_link": "p0_4_support_link_input_design",
    "scheduler_action_cost": "p0_3_scheduler_dataset_export",
    "ordered_prefix_stop": "p0_6_7_8_parallel_trace_surfaces",
    "same_file_redundancy": "p0_6_7_8_parallel_trace_surfaces",
    "risk_penalty": "p0_6_7_8_parallel_trace_surfaces",
}

HELPER_BUCKETS = {
    "support_link": "build_support_link_trace_capture_row_private_and_sanitize_support_link_trace_capture_row_public",
    "scheduler_action_cost": "build_scheduler_action_cost_trace_capture_row_private_and_sanitize_scheduler_action_cost_trace_capture_row_public",
    "ordered_prefix_stop": "build_ordered_prefix_stop_trace_capture_row_private_and_sanitize_ordered_prefix_stop_trace_capture_row_public",
    "same_file_redundancy": "build_same_file_redundancy_trace_capture_row_private_and_sanitize_same_file_redundancy_trace_capture_row_public",
    "risk_penalty": "build_risk_penalty_trace_capture_row_private_and_sanitize_risk_penalty_trace_capture_row_public",
}


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


def _input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool, dict[str, Any]]:
    artifact, load_status = _load_json(args.p3_0_artifact)
    scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    observed_status = str(artifact.get("status", "") or "")
    schema_count = len(artifact.get("trace_schema_records", [])) if isinstance(artifact.get("trace_schema_records"), list) else 0
    instrumentation_count = len(artifact.get("instrumentation_point_records", [])) if isinstance(artifact.get("instrumentation_point_records"), list) else 0
    handoff = artifact.get("p3_1_handoff_records", [])
    handoff_ok = bool(handoff and isinstance(handoff, list) and isinstance(handoff[0], dict) and handoff[0].get("p3_1_preflight_authorized") is True and handoff[0].get("trace_capture_execution_authorized_bool") is False)
    stop_go = artifact.get("stop_go_records", [])
    trace_capture_false = bool(stop_go and isinstance(stop_go, list) and isinstance(stop_go[0], dict) and stop_go[0].get("trace_capture_execution_authorized") is False)
    ok = load_status == "pass" and observed_status == "frozen_upstream_trace_capture_harness_design_pass" and scan_status == "pass" and schema_count == 5 and instrumentation_count == 5 and handoff_ok and trace_capture_false
    record = {
        "input_artifact_bucket": "p3_0_frozen_upstream_trace_capture_harness_design",
        "source_phase_bucket": "BEA-v1-P3-0",
        "load_status": load_status,
        "expected_status": "frozen_upstream_trace_capture_harness_design_pass",
        "observed_status": observed_status,
        "forbidden_scan_status": scan_status,
        "trace_schema_record_count": schema_count,
        "instrumentation_point_record_count": instrumentation_count,
        "p3_1_preflight_authorized": handoff_ok,
        "trace_capture_execution_authorized": False if trace_capture_false else "unexpected_or_missing",
        "input_gate_passed": ok,
    }
    return [record], ok, artifact


def _static_anchor_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, spec in enumerate(ANCHORS):
        exists = spec["path"].exists()
        marker_count = 0
        if exists:
            try:
                body = spec["path"].read_text(encoding="utf-8", errors="replace")
                marker_count = sum(1 for marker in spec["markers"] if marker in body)
            except Exception:
                marker_count = 0
        all_markers = marker_count == len(spec["markers"])
        anchor_ok = exists and (all_markers if spec["required"] else marker_count > 0)
        rows.append({
            "anonymous_static_anchor_id": f"p31a{idx:04d}",
            "anchor_bucket": spec["anchor_bucket"],
            "required_anchor_bool": bool(spec["required"]),
            "exists_bool": bool(exists),
            "required_text_marker_count": marker_count,
            "required_text_marker_total": len(spec["markers"]),
            "expected_static_tokens_bucket": "plus".join(spec["markers"]),
            "all_markers_present_bool": bool(all_markers),
            "static_text_inspection_only_bool": True,
            "import_or_execution_performed_bool": False,
            "anchor_status_bucket": "required_anchor_ready" if anchor_ok and spec["required"] else "optional_anchor_observed" if anchor_ok else "required_anchor_missing_or_incomplete" if spec["required"] else "optional_anchor_unavailable",
        })
    return rows


def _surface_preflight_records(p3_0: dict[str, Any], anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schema_surfaces = {str(row.get("surface_bucket", "") or "") for row in p3_0.get("trace_schema_records", []) if isinstance(row, dict)} if isinstance(p3_0.get("trace_schema_records"), list) else set()
    schema_by_surface = {str(row.get("surface_bucket", "") or ""): str(row.get("schema_version_bucket", "") or "") for row in p3_0.get("trace_schema_records", []) if isinstance(row, dict)} if isinstance(p3_0.get("trace_schema_records"), list) else {}
    instrumentation_surfaces = {str(row.get("surface_bucket", "") or "") for row in p3_0.get("instrumentation_point_records", []) if isinstance(row, dict)} if isinstance(p3_0.get("instrumentation_point_records"), list) else set()
    anchor_status = {row["anchor_bucket"]: row for row in anchors}
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(sorted(SURFACE_TO_ANCHOR)):
        anchor_bucket = SURFACE_TO_ANCHOR[surface]
        anchor_ready = anchor_status.get(anchor_bucket, {}).get("anchor_status_bucket") == "required_anchor_ready"
        schema_available = surface in schema_surfaces
        instrumentation_available = surface in instrumentation_surfaces
        ready = bool(schema_available and instrumentation_available and anchor_ready)
        if not schema_available or not instrumentation_available:
            readiness = "blocked_missing_schema_or_instrumentation"
        elif not anchor_ready:
            readiness = "blocked_missing_static_anchor"
        else:
            readiness = "ready_for_logging_only_patch_design"
        rows.append({
            "anonymous_surface_preflight_id": f"p31s{idx:04d}",
            "surface_bucket": surface,
            "trace_schema_available_bool": bool(schema_available),
            "instrumentation_point_available_bool": bool(instrumentation_available),
            "private_schema_bucket": schema_by_surface.get(surface, "missing_private_schema_bucket"),
            "public_projection_bucket": "scanner_safe_bucketed_public_projection",
            "static_anchor_bucket": anchor_bucket,
            "static_anchor_available_bool": bool(anchor_ready),
            "future_logger_required_bool": True,
            "logging_only_patch_plan_defined_bool": ready,
            "runtime_behavior_mutation_required_bool": False,
            "dry_run_preflight_complete_bool": ready,
            "preflight_readiness_bucket": readiness,
            "trace_capture_execution_authorized_bool": False,
            "private_trace_row_write_authorized_bool": False,
            "patch_application_authorized_bool": False,
            "retrieval_execution_authorized_bool": False,
        })
    return rows


def _logging_only_patch_plan_records(surface_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(surface_rows):
        rows.append({
            "anonymous_patch_plan_id": f"p31p{idx:04d}",
            "surface_bucket": surface["surface_bucket"],
            "patch_plan_bucket": "logging_only_patch_design_for_future_trace_logger",
            "target_file_bucket": surface["static_anchor_bucket"],
            "new_helper_bucket": HELPER_BUCKETS.get(surface["surface_bucket"], "future_trace_capture_helper_required"),
            "private_writer_bucket": "project_ignored_research_private_jsonl_future_only",
            "public_projection_bucket": surface.get("public_projection_bucket", "scanner_safe_bucketed_public_projection"),
            "mutation_boundary_bucket": "no_retrieval_ranking_packing_selection_policy_change",
            "expected_private_schema_bucket": surface.get("private_schema_bucket", "missing_private_schema_bucket"),
            "expected_public_projection_bucket": surface.get("public_projection_bucket", "scanner_safe_bucketed_public_projection"),
            "fail_closed_on_schema_or_scanner_failure_bool": True,
            "execution_authorized_bool": False,
            "patch_application_authorized_bool": False,
            "code_execution_authorized_bool": False,
            "trace_capture_execution_authorized_bool": False,
            "retrieval_execution_authorized_bool": False,
            "runtime_behavior_change_authorized_bool": False,
            "private_trace_row_write_authorized_bool": False,
            "mutation_allowed_bool": False,
        })
    return rows


def _privacy_boundary_preflight_records(surface_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(surface_rows):
        rows.append({
            "anonymous_privacy_preflight_id": f"p31b{idx:04d}",
            "surface_bucket": surface["surface_bucket"],
            "private_storage_bucket": "project_ignored_research_private_jsonl_future_only",
            "public_projection_bucket": "bucketed_aggregate_rows_only",
            "raw_payload_public_bool": False,
            "private_location_public_bool": False,
            "source_location_public_bool": False,
            "source_span_public_bool": False,
            "snippet_public_bool": False,
            "candidate_list_public_bool": False,
            "provider_payload_public_bool": False,
            "digest_public_bool": False,
            "privacy_boundary_complete_bool": True,
        })
    return rows


def _fail_closed_preflight_records() -> list[dict[str, Any]]:
    gates = (
        "p3_0_input_shape_valid",
        "required_static_anchors_ready",
        "five_surface_preflight_complete",
        "privacy_boundary_complete",
        "logging_only_patch_design_no_application",
        "no_trace_capture_execution",
        "no_private_rows_written",
        "separate_p3_2_required_for_patch_design",
    )
    return [{"anonymous_fail_closed_preflight_id": f"p31f{idx:04d}", "gate_bucket": gate, "fail_closed_bool": True, "execution_in_p3_1_bool": False} for idx, gate in enumerate(gates)]


def _p3_2_handoff_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_handoff_id": "p31h0000",
        "handoff_bucket": "p3_2_frozen_trace_logger_patch_design",
        "p3_2_patch_design_authorized": True,
        "p3_2_scope_bucket": "logging_only_code_change_design_no_application",
        "requires_separate_phase_bool": True,
        "patch_application_authorized_bool": False,
        "code_execution_authorized_bool": False,
        "trace_capture_execution_authorized_bool": False,
        "private_trace_row_write_authorized_bool": False,
    }]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok, p3_0 = _input_artifact_records(args)
    anchors = _static_anchor_records()
    surface_rows = _surface_preflight_records(p3_0, anchors)
    patch_rows = _logging_only_patch_plan_records(surface_rows)
    privacy_rows = _privacy_boundary_preflight_records(surface_rows)
    fail_closed_rows = _fail_closed_preflight_records()
    handoff_rows = _p3_2_handoff_records()
    self_tests_ok = all(c["passed"] for c in checks)
    required_anchor_ok = all(row["anchor_status_bucket"] == "required_anchor_ready" for row in anchors if row["required_anchor_bool"])
    surface_ok = len(surface_rows) == 5 and all(row["dry_run_preflight_complete_bool"] for row in surface_rows)
    privacy_ok = len(privacy_rows) == 5 and all(row["privacy_boundary_complete_bool"] and not row["raw_payload_public_bool"] and not row["source_location_public_bool"] and not row["source_span_public_bool"] and not row["candidate_list_public_bool"] and not row["provider_payload_public_bool"] for row in privacy_rows)
    fail_closed_ok = len(fail_closed_rows) >= 8 and all(row["fail_closed_bool"] and not row["execution_in_p3_1_bool"] for row in fail_closed_rows)
    patch_ok = len(patch_rows) == 5 and all(not row["patch_application_authorized_bool"] and not row["code_execution_authorized_bool"] and not row["trace_capture_execution_authorized_bool"] for row in patch_rows)
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_1_required_inputs_unavailable"
    elif not required_anchor_ok:
        status = "no_go_p3_1_static_anchor_missing"
    elif not surface_ok:
        status = "no_go_p3_1_surface_preflight_incomplete"
    elif not (privacy_ok and fail_closed_ok and patch_ok):
        status = "no_go_p3_1_privacy_or_fail_closed_boundary_incomplete"
    else:
        status = "frozen_trace_capture_preflight_pass_patch_design_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "frozen_trace_capture_preflight_pass_patch_design_authorized" else "required_inputs_unavailable" if status == "no_go_p3_1_required_inputs_unavailable" else "static_anchor_missing" if status == "no_go_p3_1_static_anchor_missing" else "surface_preflight_incomplete" if status == "no_go_p3_1_surface_preflight_incomplete" else "privacy_or_fail_closed_boundary_incomplete" if status == "no_go_p3_1_privacy_or_fail_closed_boundary_incomplete" else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "static_anchor_records": anchors,
        "per_surface_preflight_records": surface_rows,
        "logging_only_patch_plan_records": patch_rows,
        "privacy_boundary_preflight_records": privacy_rows,
        "fail_closed_preflight_records": fail_closed_rows,
        "p3_2_handoff_records": handoff_rows,
        "gate_records": [
            {"gate": "p3_0_required_input_pass", "passed": input_ok, "threshold_relation": "boolean", "value": int(input_ok), "threshold_value": 1},
            {"gate": "required_static_anchors_ready", "passed": required_anchor_ok, "threshold_relation": "boolean", "value": int(required_anchor_ok), "threshold_value": 1},
            {"gate": "five_surface_preflight_records_complete", "passed": surface_ok, "threshold_relation": "equals", "value": sum(1 for row in surface_rows if row["dry_run_preflight_complete_bool"]), "threshold_value": 5},
            {"gate": "logging_only_patch_plans_no_execution", "passed": patch_ok, "threshold_relation": "boolean", "value": int(patch_ok), "threshold_value": 1},
            {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "boolean", "value": int(privacy_ok), "threshold_value": 1},
            {"gate": "fail_closed_preflight_complete", "passed": fail_closed_ok, "threshold_relation": "boolean", "value": int(fail_closed_ok), "threshold_value": 1},
            {"gate": "p3_2_patch_design_authorized_not_application", "passed": handoff_rows[0]["p3_2_patch_design_authorized"] and not handoff_rows[0]["patch_application_authorized_bool"], "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "static_preflight_pass_patch_design_authorized" if status == "frozen_trace_capture_preflight_pass_patch_design_authorized" else "preflight_blocked",
            "authorization": "frozen_upstream_trace_capture_harness_dry_run_preflight_only",
            "next_allowed_phase": "BEA-v1-P3-2 Frozen Trace Logger Patch Design — logging-only code change design, no trace capture execution",
            "p3_2_patch_design_authorized": status == "frozen_trace_capture_preflight_pass_patch_design_authorized",
            "patch_application_authorized": False,
            "runtime_behavior_patch_authorized": False,
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
    p3_0_fixture = {
        "status": "frozen_upstream_trace_capture_harness_design_pass",
        "forbidden_scan": {"status": "pass"},
        "trace_schema_records": [{"surface_bucket": surface, "schema_version_bucket": f"bea_v1_{surface}_trace_capture.v1"} for surface in SURFACE_TO_ANCHOR],
        "instrumentation_point_records": [{"surface_bucket": surface} for surface in SURFACE_TO_ANCHOR],
        "p3_1_handoff_records": [{"p3_1_preflight_authorized": True, "trace_capture_execution_authorized_bool": False}],
        "stop_go_records": [{"trace_capture_execution_authorized": False}],
    }
    anchors = [{"anchor_bucket": bucket, "anchor_status_bucket": "required_anchor_ready", "required_anchor_bool": True} for bucket in sorted(set(SURFACE_TO_ANCHOR.values()))]
    surface_rows = _surface_preflight_records(p3_0_fixture, anchors)
    patch_rows = _logging_only_patch_plan_records(surface_rows)
    privacy_rows = _privacy_boundary_preflight_records(surface_rows)
    fail_closed = _fail_closed_preflight_records()
    handoff = _p3_2_handoff_records()[0]
    parser_ok = False
    try:
        build_parser().parse_args(["--unknown-secret-value", "SHOULD_NOT_APPEAR"])
    except SystemExit as exc:
        parser_ok = "SHOULD_NOT_APPEAR" not in str(exc)
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_trace_capture_preflight_pass_patch_design_authorized", "no_go_p3_1_required_inputs_unavailable", "no_go_p3_1_surface_preflight_incomplete", "no_go_p3_1_static_anchor_missing", "no_go_p3_1_privacy_or_fail_closed_boundary_incomplete", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("fixture_p3_0_shape", len(p3_0_fixture["trace_schema_records"]) == 5 and len(p3_0_fixture["instrumentation_point_records"]) == 5 and p3_0_fixture["p3_1_handoff_records"][0]["p3_1_preflight_authorized"] is True),
        _check("five_surface_records", len(surface_rows) == 5 and all(row["dry_run_preflight_complete_bool"] for row in surface_rows)),
        _check("all_patch_plans_execution_false", not any(row["patch_application_authorized_bool"] or row["code_execution_authorized_bool"] or row.get("execution_authorized_bool") for row in patch_rows)),
        _check("patch_plans_define_helper_and_writer_buckets", all(row.get("new_helper_bucket") and row.get("private_writer_bucket") and row.get("expected_private_schema_bucket") for row in patch_rows)),
        _check("surface_readiness_buckets_ready", all(row.get("preflight_readiness_bucket") == "ready_for_logging_only_patch_design" and row.get("runtime_behavior_mutation_required_bool") is False for row in surface_rows)),
        _check("trace_capture_false", not any(row["trace_capture_execution_authorized_bool"] for row in surface_rows + patch_rows)),
        _check("privacy_blocks_raw", not any(row["raw_payload_public_bool"] or row["source_location_public_bool"] or row["source_span_public_bool"] or row["provider_payload_public_bool"] for row in privacy_rows)),
        _check("fail_closed_gates", len(fail_closed) >= 8 and all(row["fail_closed_bool"] and not row["execution_in_p3_1_bool"] for row in fail_closed)),
        _check("scanner_accepts", tg._scan_summary({"per_surface_preflight_records": surface_rows, "logging_only_patch_plan_records": patch_rows, "privacy_boundary_preflight_records": privacy_rows})["status"] == "pass"),
        _check("scanner_rejects_path_key", tg._scan_summary({"path": "x"})["status"] == "fail"),
        _check("p3_2_handoff_patch_design_not_execution", handoff["p3_2_patch_design_authorized"] is True and handoff["requires_separate_phase_bool"] is True and handoff["patch_application_authorized_bool"] is False and handoff["trace_capture_execution_authorized_bool"] is False),
        _check("safe_parser_hides_unknown_arg_values", parser_ok),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-1 frozen upstream trace-capture harness dry-run preflight")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p3-0-artifact", type=Path, default=DEFAULT_P3_0)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, surfaces={len(report['per_surface_preflight_records'])}, anchors={len(report['static_anchor_records'])}, p3_2={report['p3_2_handoff_records'][0]['p3_2_patch_design_authorized']})")


if __name__ == "__main__":
    main()
