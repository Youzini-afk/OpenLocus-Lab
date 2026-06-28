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


SCHEMA_VERSION = "bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review.v1"
GENERATED_BY = "eval/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review.py"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review_report.json")
DEFAULT_P3_3 = Path("artifacts/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review_report.json")
DEFAULT_P3_4 = Path("artifacts/bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design/bea_v1_p3_4_frozen_trace_logger_hook_in_preflight_design_report.json")

STATUSES = (
    "frozen_trace_logger_hook_in_patch_plan_review_pass_p3_6_authorized",
    "no_go_p3_5_required_inputs_unavailable",
    "no_go_p3_5_patch_plan_incomplete",
    "no_go_p3_5_feature_gate_or_default_boundary_incomplete",
    "no_go_p3_5_private_writer_boundary_incomplete",
    "no_go_p3_5_behavior_preservation_plan_incomplete",
    "no_go_p3_5_forbidden_code_touch_detected",
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

TARGET_BUCKETS = {
    "support_link": "p0_4_support_link_input_design",
    "scheduler_action_cost": "p0_3_scheduler_dataset_export_and_p4l_locked_scheduler_validation",
    "ordered_prefix_stop": "p0_6_7_8_parallel_trace_surfaces",
    "same_file_redundancy": "p0_6_7_8_parallel_trace_surfaces",
    "risk_penalty": "p0_6_7_8_parallel_trace_surfaces",
}

HOOK_POINT_BUCKETS = {
    "support_link": "support_target_join_before_label_validation",
    "scheduler_action_cost": "frozen_arm_event_before_export_projection",
    "ordered_prefix_stop": "prefix_cost_state_before_stop_projection",
    "same_file_redundancy": "candidate_grouping_before_redundancy_projection",
    "risk_penalty": "risk_policy_eval_before_penalty_projection",
}

STATIC_TARGETS = (
    ("p0_3_scheduler_dataset_export", Path("eval/bea_v1_p0_3_scheduler_dataset_export.py"), ("scheduler_dataset_export", "PRIVATE_ARM_SCHEMA", "sanitize_private_arm_rows")),
    ("p0_4_support_link_input_design", Path("eval/bea_v1_p0_4_support_link_input_design.py"), ("support_link", "support_relation", "target_hit")),
    ("p0_6_7_8_parallel_trace_surfaces", Path("eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py"), ("same_file_redundancy", "risk_penalty", "ordered_prefix")),
    ("p1_2_private_label_intake_validator", Path("eval/bea_v1_p1_2_private_label_intake_validator.py"), ("private_label", "intake", "support")),
    ("p4l_locked_scheduler_validation_optional", Path("eval/bea_v1_p4l_locked_non_python_scheduler_validation.py"), ("p4l", "scheduler")),
    ("bea_v1_frozen_trace_logger_helpers", Path("eval/bea_v1_frozen_trace_logger_helpers.py"), ("build_support_link_trace_capture_row_private", "sanitize_support_link_trace_capture_row_public", "validate_risk_penalty_trace_capture_row_public_projection")),
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-5-frozen-trace-logger-hook-in-patch-plan-review.md",
    "docs/zh/bea-v1-p3-5-frozen-trace-logger-hook-in-patch-plan-review.md",
    "eval/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review.py",
    "artifacts/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review_report.json",
})
ALLOWED_CHANGED_PREFIXES = (
    "artifacts/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review/",
)

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "exact_path", "private_path",
    "span", "spans", "line", "lines", "snippet", "snippets", "content",
    "candidate", "candidate_list", "rank_list", "provider", "prompt", "response",
    "payload", "hash", "hashes", "private_id", "queue_item_id", "anonymous_design_id",
    "repo", "repo_id", "task_id", "raw", "text", "diff", "raw_diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "generated_by", "generated_at", "claim_level", "status", "phase",
    "failure_reason_category", "gate", "threshold_relation", "stop_go_decision",
    "stop_go_reason", "authorization", "next_allowed_phase", "p3_6_scope_bucket", "p3_6_scope",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        if "unrecognized arguments" in message:
            raise SystemExit("invalid arguments")
        raise SystemExit("argument_error")


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
    hex_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

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
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": key, "count": value} for key, value in sorted(counts.items())]}


def _input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    specs = (
        ("p3_3_frozen_trace_logger_isolated_helper_patch_review", "BEA-v1-P3-3", "frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized", args.p3_3_artifact),
        ("p3_4_frozen_trace_logger_hook_in_preflight_design", "BEA-v1-P3-4", "frozen_trace_logger_hook_in_preflight_design_pass_p3_5_authorized", args.p3_4_artifact),
    )
    rows: list[dict[str, Any]] = []
    ok = True
    for bucket, phase, expected_status, input_file in specs:
        artifact, load_status = _load_json(input_file)
        observed = str(artifact.get("status", "") or "")
        scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
        passed = load_status == "pass" and observed == expected_status and scan_status == "pass"
        ok = ok and passed
        rows.append({"input_artifact_bucket": bucket, "source_phase_bucket": phase, "load_status": load_status, "expected_status": expected_status, "observed_status": observed, "forbidden_scan_status": scan_status, "input_gate_passed": passed})
    return rows, ok


def _static_plan_target_records() -> tuple[list[dict[str, Any]], bool]:
    repo = Path(__file__).resolve().parent.parent
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, rel_file, markers) in enumerate(STATIC_TARGETS):
        source = ""
        exists = (repo / rel_file).exists()
        if exists:
            source = (repo / rel_file).read_text(encoding="utf-8")
        marker_count = sum(1 for marker in markers if marker in source)
        passed = exists and marker_count == len(markers)
        ok = ok and passed
        rows.append({"anonymous_static_plan_target_id": f"p35st{idx:04d}", "static_target_bucket": bucket, "exists_bool": exists, "static_text_inspection_only_bool": True, "import_or_execution_performed_bool": False, "required_marker_count": marker_count, "required_marker_total": len(markers), "static_plan_target_ready_bool": passed})
    return rows, ok


def _surface_patch_plan_records() -> list[dict[str, Any]]:
    return [{"anonymous_surface_patch_plan_id": f"p35sp{idx:04d}", "surface_bucket": surface, "target_bucket": TARGET_BUCKETS[surface], "hook_point_bucket": HOOK_POINT_BUCKETS[surface], "planned_change_bucket": "default_off_logging_only_hook_plan", "helper_call_sequence_bucket": "build_validate_sanitize_validate_then_optional_private_append", "patch_application_in_p3_5_authorized_bool": False, "hook_execution_in_p3_5_authorized_bool": False, "trace_capture_execution_authorized_bool": False, "private_trace_row_write_authorized_bool": False, "runtime_behavior_mutation_required_bool": False, "surface_patch_plan_complete_bool": True} for idx, surface in enumerate(SURFACES)]


def _planned_diff_bucket_records() -> list[dict[str, Any]]:
    return [{"anonymous_planned_diff_bucket_id": f"p35df{idx:04d}", "surface_bucket": surface, "target_bucket": TARGET_BUCKETS[surface], "planned_diff_bucket": "add_default_off_logging_hook_branch_and_noop_default_path", "planned_import_bucket": "future_import_frozen_trace_logger_helpers_inside_default_off_gate", "planned_helper_call_bucket": "build_validate_sanitize_validate_then_future_writer", "planned_flag_or_gate_bucket": "explicit_trace_capture_flag_required", "line_numbers_publicly_serialized_bool": False, "source_snippets_publicly_serialized_bool": False, "raw_diff_publicly_serialized_bool": False} for idx, surface in enumerate(SURFACES)]


def _helper_call_plan_records() -> list[dict[str, Any]]:
    return [{"anonymous_helper_call_plan_id": f"p35hc{idx:04d}", "surface_bucket": surface, "builder_helper_bucket": "build_" + surface + "_trace_capture_row_private", "private_validator_helper_bucket": "validate_" + surface + "_trace_capture_row_private", "public_sanitizer_helper_bucket": "sanitize_" + surface + "_trace_capture_row_public", "public_validator_helper_bucket": "validate_" + surface + "_trace_capture_row_public_projection", "helper_call_sequence_bucket": "build_validate_sanitize_validate_then_optional_private_append", "helper_call_execution_in_p3_5_authorized_bool": False, "helper_call_plan_complete_bool": True} for idx, surface in enumerate(SURFACES)]


def _feature_gate_and_default_records() -> list[dict[str, Any]]:
    return [{"anonymous_feature_gate_id": f"p35fg{idx:04d}", "surface_bucket": surface, "future_feature_gate_bucket": "explicit_trace_capture_flag_required", "default_enabled_bool": False, "default_runtime_behavior_changed_bool": False, "capture_requires_explicit_future_phase_bool": True, "private_write_requires_explicit_future_phase_bool": True, "feature_gate_boundary_complete_bool": True} for idx, surface in enumerate(SURFACES)]


def _private_writer_plan_records() -> list[dict[str, Any]]:
    return [{"anonymous_private_writer_plan_id": f"p35pw{idx:04d}", "surface_bucket": surface, "private_writer_plan_bucket": "future_project_ignored_research_private_jsonl_append_only", "private_write_authorized_in_p3_5_bool": False, "private_write_authorized_in_p3_6_bool": False, "private_path_publicly_serialized_bool": False, "schema_validation_before_write_required_bool": True, "public_scanner_before_public_projection_required_bool": True, "private_writer_boundary_complete_bool": True} for idx, surface in enumerate(SURFACES)]


def _synthetic_validation_plan_records() -> list[dict[str, Any]]:
    return [{"anonymous_synthetic_validation_plan_id": f"p35sv{idx:04d}", "surface_bucket": surface, "synthetic_hook_fixture_required_bool": True, "real_retrieval_execution_allowed_bool": False, "p4l_n1_n2_rerun_allowed_bool": False, "private_rows_used_bool": False, "behavior_snapshot_required_bool": True, "default_disabled_noop_test_required_bool": True, "synthetic_validation_plan_complete_bool": True} for idx, surface in enumerate(SURFACES)]


def _behavior_preservation_review_records() -> list[dict[str, Any]]:
    gates = (
        "default_disabled_noop_behavior_snapshot",
        "no_retrieval_result_change",
        "no_scheduler_arm_selection_change",
        "no_ranking_change",
        "no_packing_change",
        "no_support_labeling_change",
        "no_counterfactual_execution",
        "no_private_write_in_current_or_p3_6",
        "no_trace_capture_execution",
        "no_provider_or_network_execution",
        "scanner_pass_before_public_projection",
        "schema_validation_before_future_write",
        "fail_closed_on_gate_or_schema_error",
    )
    return [{"anonymous_behavior_review_id": f"p35br{idx:04d}", "behavior_preservation_bucket": gate, "review_complete_bool": True, "fail_closed_bool": True, "behavior_mutation_authorized_bool": False, "execution_authorized_bool": False} for idx, gate in enumerate(gates)]


def _forbidden_code_touch_records() -> tuple[list[dict[str, Any]], bool]:
    repo = Path(__file__).resolve().parent.parent
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=repo, check=False, capture_output=True, text=True, timeout=10)
        entries = [line for line in proc.stdout.splitlines() if line.strip()]
        available = proc.returncode == 0
    except Exception:
        entries = []
        available = False
    forbidden_existing_or_runtime = 0
    forbidden_out_of_scope_change = 0
    helper_module_modified = 0
    current_phase_eval_count = 0
    for line in entries:
        status = line[:2]
        name = line[3:].strip()
        tracked_mod = not status.startswith("??")
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if not allowed:
            forbidden_out_of_scope_change += 1
        if name == "eval/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review.py":
            current_phase_eval_count += 1
        if tracked_mod and name == "eval/bea_v1_frozen_trace_logger_helpers.py":
            helper_module_modified += 1
        if tracked_mod and (name.startswith(("src/", "crates/", "packages/")) or (name.startswith("eval/") and name != "eval/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review.py")):
            forbidden_existing_or_runtime += 1
    ok = available and forbidden_existing_or_runtime == 0 and helper_module_modified == 0 and forbidden_out_of_scope_change == 0
    return [{"anonymous_forbidden_code_touch_id": "p35ct0000", "git_status_check_available_bool": available, "workspace_change_count": len(entries), "current_phase_evaluator_change_count": current_phase_eval_count, "helper_module_modified_in_p3_5_bool": helper_module_modified > 0, "forbidden_existing_evaluator_or_runtime_modification_count": forbidden_existing_or_runtime, "forbidden_out_of_scope_change_count": forbidden_out_of_scope_change, "forbidden_code_touch_detected_bool": not ok, "forbidden_code_touch_record_sanitized_bool": True}], ok


def _p3_6_handoff_records() -> list[dict[str, Any]]:
    return [{"anonymous_handoff_id": "p35h0000", "handoff_bucket": "p3_6_frozen_trace_logger_limited_hook_application_patch", "next_allowed_phase": "BEA-v1-P3-6 Frozen Trace Logger Limited Hook Application Patch — default-off logging-only hook wiring, synthetic/no-execution validation only", "p3_6_limited_hook_application_patch_authorized": True, "p3_6_scope_bucket": "default-off logging-only hook wiring, synthetic/no-execution validation only, no trace capture/private writes/retrieval/P4L/N1/N2 reruns", "requires_separate_phase_bool": True, "current_phase_patch_application_authorized_bool": False, "p3_6_trace_capture_execution_authorized_bool": False, "p3_6_private_trace_row_write_authorized_bool": False, "p3_6_retrieval_execution_authorized_bool": False, "p3_6_p4l_n1_n2_rerun_authorized_bool": False}]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_artifact_records(args)
    static_records, static_ok = _static_plan_target_records()
    surface_rows = _surface_patch_plan_records()
    diff_rows = _planned_diff_bucket_records()
    helper_rows = _helper_call_plan_records()
    feature_rows = _feature_gate_and_default_records()
    writer_rows = _private_writer_plan_records()
    synthetic_rows = _synthetic_validation_plan_records()
    behavior_rows = _behavior_preservation_review_records()
    code_touch_rows, code_touch_ok = _forbidden_code_touch_records()
    p3_6_rows = _p3_6_handoff_records()
    patch_plan_ok = static_ok and len(surface_rows) == 5 and len(diff_rows) == 5 and len(helper_rows) == 5 and all(row["surface_patch_plan_complete_bool"] and not row["patch_application_in_p3_5_authorized_bool"] and not row["trace_capture_execution_authorized_bool"] for row in surface_rows)
    feature_ok = len(feature_rows) == 5 and all(row["feature_gate_boundary_complete_bool"] and row["default_enabled_bool"] is False and row["default_runtime_behavior_changed_bool"] is False and row["capture_requires_explicit_future_phase_bool"] for row in feature_rows)
    writer_ok = len(writer_rows) == 5 and all(row["private_writer_boundary_complete_bool"] and not row["private_write_authorized_in_p3_5_bool"] and not row["private_write_authorized_in_p3_6_bool"] and not row["private_path_publicly_serialized_bool"] for row in writer_rows)
    behavior_ok = len(behavior_rows) >= 12 and all(row["review_complete_bool"] and not row["behavior_mutation_authorized_bool"] and not row["execution_authorized_bool"] for row in behavior_rows) and all(row["synthetic_validation_plan_complete_bool"] and not row["real_retrieval_execution_allowed_bool"] and not row["private_rows_used_bool"] for row in synthetic_rows)
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_5_required_inputs_unavailable"
    elif not patch_plan_ok:
        status = "no_go_p3_5_patch_plan_incomplete"
    elif not feature_ok:
        status = "no_go_p3_5_feature_gate_or_default_boundary_incomplete"
    elif not writer_ok:
        status = "no_go_p3_5_private_writer_boundary_incomplete"
    elif not behavior_ok:
        status = "no_go_p3_5_behavior_preservation_plan_incomplete"
    elif not code_touch_ok:
        status = "no_go_p3_5_forbidden_code_touch_detected"
    else:
        status = "frozen_trace_logger_hook_in_patch_plan_review_pass_p3_6_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "frozen_trace_logger_hook_in_patch_plan_review_only",
        "phase": "BEA-v1-P3-5",
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "failure_reason_category": "" if status == "frozen_trace_logger_hook_in_patch_plan_review_pass_p3_6_authorized" else status.replace("no_go_p3_5_", "").replace("fail_", ""),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "static_plan_target_records": static_records,
        "surface_patch_plan_records": surface_rows,
        "planned_diff_bucket_records": diff_rows,
        "helper_call_plan_records": helper_rows,
        "feature_gate_and_default_records": feature_rows,
        "private_writer_plan_records": writer_rows,
        "synthetic_validation_plan_records": synthetic_rows,
        "behavior_preservation_review_records": behavior_rows,
        "forbidden_code_touch_records": code_touch_rows,
        "p3_6_handoff_records": p3_6_rows,
        "gate_records": [
            {"gate": "p3_3_and_p3_4_inputs_pass", "passed": input_ok, "threshold_relation": "equals", "value": sum(1 for row in input_records if row["input_gate_passed"]), "threshold_value": 2},
            {"gate": "patch_plan_complete", "passed": patch_plan_ok, "threshold_relation": "boolean", "value": int(patch_plan_ok), "threshold_value": 1},
            {"gate": "feature_gate_default_off_boundary_complete", "passed": feature_ok, "threshold_relation": "equals", "value": sum(1 for row in feature_rows if row["feature_gate_boundary_complete_bool"]), "threshold_value": 5},
            {"gate": "private_writer_boundary_complete", "passed": writer_ok, "threshold_relation": "equals", "value": sum(1 for row in writer_rows if row["private_writer_boundary_complete_bool"]), "threshold_value": 5},
            {"gate": "behavior_preservation_plan_complete", "passed": behavior_ok, "threshold_relation": "at_least", "value": len(behavior_rows), "threshold_value": 12},
            {"gate": "forbidden_code_touch_absent", "passed": code_touch_ok, "threshold_relation": "boolean", "value": int(code_touch_ok), "threshold_value": 1},
            {"gate": "p3_6_limited_handoff_only", "passed": True, "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{"stop_go_decision": status, "stop_go_reason": "patch_plan_review_complete" if status == "frozen_trace_logger_hook_in_patch_plan_review_pass_p3_6_authorized" else "patch_plan_review_blocked", "authorization": "frozen_trace_logger_hook_in_patch_plan_review_only", "next_allowed_phase": "BEA-v1-P3-6 Frozen Trace Logger Limited Hook Application Patch — default-off logging-only hook wiring, synthetic/no-execution validation only, no trace capture/private writes/retrieval/P4L/N1/N2 reruns", "p3_6_limited_hook_application_patch_authorized": status == "frozen_trace_logger_hook_in_patch_plan_review_pass_p3_6_authorized", "patch_application_authorized_in_p3_5": False, "p3_6_scope": "default-off logging-only hook wiring, synthetic/no-execution validation only, no trace capture/private writes/retrieval/P4L/N1/N2 reruns", "current_phase_patch_application_authorized": False, "hook_execution_authorized": False, "trace_capture_execution_authorized": False, "private_trace_row_write_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "implementation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}],
        "aggregate_plus_sanitized_records_public_artifact": True,
        "raw_records_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "source_snippets_publicly_serialized": False,
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
    surface_rows = _surface_patch_plan_records()
    diff_rows = _planned_diff_bucket_records()
    feature_rows = _feature_gate_and_default_records()
    writer_rows = _private_writer_plan_records()
    synthetic_rows = _synthetic_validation_plan_records()
    behavior_rows = _behavior_preservation_review_records()
    code_touch_rows, _ = _forbidden_code_touch_records()
    handoff = _p3_6_handoff_records()[0]
    parser_ok = False
    try:
        build_parser().parse_args(["--secret-unknown", "VALUE_SHOULD_NOT_APPEAR"])
    except SystemExit as exc:
        parser_ok = str(exc) == "invalid arguments"
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_trace_logger_hook_in_patch_plan_review_pass_p3_6_authorized", "no_go_p3_5_required_inputs_unavailable", "no_go_p3_5_patch_plan_incomplete", "no_go_p3_5_feature_gate_or_default_boundary_incomplete", "no_go_p3_5_private_writer_boundary_incomplete", "no_go_p3_5_behavior_preservation_plan_incomplete", "no_go_p3_5_forbidden_code_touch_detected", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("p3_3_p3_4_fixture_shape", len(_input_artifact_records(build_parser().parse_args([]))[0]) == 2),
        _check("five_surface_plans", len(surface_rows) == 5 and {row["surface_bucket"] for row in surface_rows} == set(SURFACES) and all(row["surface_patch_plan_complete_bool"] for row in surface_rows)),
        _check("bucketed_diff_no_raw", len(diff_rows) == 5 and not any(row["line_numbers_publicly_serialized_bool"] or row["source_snippets_publicly_serialized_bool"] or row["raw_diff_publicly_serialized_bool"] for row in diff_rows)),
        _check("feature_gates_default_off", len(feature_rows) == 5 and not any(row["default_enabled_bool"] or row["default_runtime_behavior_changed_bool"] for row in feature_rows)),
        _check("private_writer_no_writes", len(writer_rows) == 5 and not any(row["private_write_authorized_in_p3_5_bool"] or row["private_write_authorized_in_p3_6_bool"] or row["private_path_publicly_serialized_bool"] for row in writer_rows)),
        _check("synthetic_no_real_execution", len(synthetic_rows) == 5 and not any(row["real_retrieval_execution_allowed_bool"] or row["p4l_n1_n2_rerun_allowed_bool"] or row["private_rows_used_bool"] for row in synthetic_rows)),
        _check("behavior_preservation_complete", len(behavior_rows) >= 12 and all(row["review_complete_bool"] and not row["behavior_mutation_authorized_bool"] for row in behavior_rows)),
        _check("p3_6_handoff_limited_default_off_only", handoff["p3_6_limited_hook_application_patch_authorized"] and "BEA-v1-P3-6 Frozen Trace Logger Limited Hook Application Patch" in handoff["next_allowed_phase"] and "default-off logging-only hook wiring" in handoff["p3_6_scope_bucket"] and not handoff["p3_6_trace_capture_execution_authorized_bool"] and not handoff["p3_6_private_trace_row_write_authorized_bool"]),
        _check("scanner_accepts_records", _scan_summary({"surface_patch_plan_records": surface_rows, "planned_diff_bucket_records": diff_rows, "feature_gate_and_default_records": feature_rows, "forbidden_code_touch_records": code_touch_rows})["status"] == "pass"),
        _check("scanner_rejects_path_key", _scan_summary({"path": "blocked"})["status"] == "fail"),
        _check("safe_parser_generic_invalid_arguments", parser_ok),
        _check("forbidden_code_touch_sanitized", _scan_summary(code_touch_rows)["status"] == "pass" and code_touch_rows[0]["forbidden_code_touch_record_sanitized_bool"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-5 frozen trace logger hook-in patch-plan review")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p3-3-artifact", type=Path, default=DEFAULT_P3_3)
    parser.add_argument("--p3-4-artifact", type=Path, default=DEFAULT_P3_4)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, surfaces={len(report['surface_patch_plan_records'])}, p3_6={report['p3_6_handoff_records'][0]['p3_6_limited_hook_application_patch_authorized']})")


if __name__ == "__main__":
    main()
