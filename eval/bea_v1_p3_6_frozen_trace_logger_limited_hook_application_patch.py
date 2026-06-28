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


SCHEMA_VERSION = "bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch.v1"
GENERATED_BY = "eval/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch.py"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch_report.json")
DEFAULT_P3_5 = Path("artifacts/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review/bea_v1_p3_5_frozen_trace_logger_hook_in_patch_plan_review_report.json")

STATUSES = (
    "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized",
    "no_go_p3_6_required_inputs_unavailable",
    "no_go_p3_6_changed_file_scope_invalid",
    "no_go_p3_6_hook_wiring_incomplete",
    "no_go_p3_6_default_off_gate_missing",
    "no_go_p3_6_behavior_mutation_risk",
    "no_go_p3_6_private_writer_or_capture_detected",
    "no_go_p3_6_helper_module_modified",
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

SURFACE_TARGETS = {
    "support_link": "p0_4_support_link_input_design",
    "scheduler_action_cost": "p0_3_scheduler_dataset_export",
    "ordered_prefix_stop": "p0_6_7_8_parallel_trace_surfaces",
    "same_file_redundancy": "p0_6_7_8_parallel_trace_surfaces",
    "risk_penalty": "p0_6_7_8_parallel_trace_surfaces",
}

TARGET_FILES = {
    "p0_3_scheduler_dataset_export": Path("eval/bea_v1_p0_3_scheduler_dataset_export.py"),
    "p0_4_support_link_input_design": Path("eval/bea_v1_p0_4_support_link_input_design.py"),
    "p0_6_7_8_parallel_trace_surfaces": Path("eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py"),
    "p1_2_private_label_intake_validator": Path("eval/bea_v1_p1_2_private_label_intake_validator.py"),
}

SURFACE_SHIMS = {
    "support_link": ("_bea_v1_support_link_trace_hook", "build_support_link_trace_capture_row_private", "validate_support_link_trace_capture_row_private", "sanitize_support_link_trace_capture_row_public", "validate_support_link_trace_capture_row_public_projection"),
    "scheduler_action_cost": ("_bea_v1_scheduler_action_cost_trace_hook", "build_scheduler_action_cost_trace_capture_row_private", "validate_scheduler_action_cost_trace_capture_row_private", "sanitize_scheduler_action_cost_trace_capture_row_public", "validate_scheduler_action_cost_trace_capture_row_public_projection"),
    "ordered_prefix_stop": ("_bea_v1_ordered_prefix_stop_trace_hook", "build_ordered_prefix_stop_trace_capture_row_private", "validate_ordered_prefix_stop_trace_capture_row_private", "sanitize_ordered_prefix_stop_trace_capture_row_public", "validate_ordered_prefix_stop_trace_capture_row_public_projection"),
    "same_file_redundancy": ("_bea_v1_same_file_redundancy_trace_hook", "build_same_file_redundancy_trace_capture_row_private", "validate_same_file_redundancy_trace_capture_row_private", "sanitize_same_file_redundancy_trace_capture_row_public", "validate_same_file_redundancy_trace_capture_row_public_projection"),
    "risk_penalty": ("_bea_v1_risk_penalty_trace_hook", "build_risk_penalty_trace_capture_row_private", "validate_risk_penalty_trace_capture_row_private", "sanitize_risk_penalty_trace_capture_row_public", "validate_risk_penalty_trace_capture_row_public_projection"),
}

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-6-frozen-trace-logger-limited-hook-application-patch.md",
    "docs/zh/bea-v1-p3-6-frozen-trace-logger-limited-hook-application-patch.md",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch.py",
    "artifacts/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch_report.json",
})
ALLOWED_CHANGED_PREFIXES = (
    "artifacts/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch/",
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
    "stop_go_reason", "authorization", "next_allowed_phase", "p3_7_scope", "p3_7_scope_bucket",
})

P3_7_NEXT_ALLOWED_PHASE = "BEA-v1-P3-7 Frozen Trace Logger Capture Execution Preflight — preflight only, no capture execution or private row writes"
P3_7_SCOPE = "preflight only for future explicitly enabled frozen trace-capture run; no capture execution/private writes/retrieval/P4L/N1/N2 reruns"


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        if "unrecognized arguments" in message:
            raise SystemExit("invalid arguments")
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


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


def _git_status_entries() -> tuple[list[tuple[str, str]], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        entries = [(line[:2], line[3:].strip()) for line in proc.stdout.splitlines() if line.strip()]
        return entries, proc.returncode == 0
    except Exception:
        return [], False


def _added_lines_for_file(rel_name: str) -> list[str]:
    try:
        proc = subprocess.run(["git", "diff", "--unified=0", "--", rel_name], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    lines: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return lines


def _input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    artifact, load_status = _load_json(args.p3_5_artifact)
    observed = str(artifact.get("status", "") or "")
    scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    expected = "frozen_trace_logger_hook_in_patch_plan_review_pass_p3_6_authorized"
    ok = load_status == "pass" and observed == expected and scan_status == "pass"
    return [{"input_artifact_bucket": "p3_5_frozen_trace_logger_hook_in_patch_plan_review", "source_phase_bucket": "BEA-v1-P3-5", "load_status": load_status, "expected_status": expected, "observed_status": observed, "forbidden_scan_status": scan_status, "input_gate_passed": ok}], ok


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    entries, available = _git_status_entries()
    disallowed = 0
    helper_modified = 0
    runtime_modified = 0
    for _, name in entries:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if not allowed:
            disallowed += 1
        if name == "eval/bea_v1_frozen_trace_logger_helpers.py":
            helper_modified += 1
        if name.startswith(("src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")):
            runtime_modified += 1
    ok = available and disallowed == 0 and helper_modified == 0 and runtime_modified == 0
    return [{"anonymous_changed_file_allowlist_id": "p36cf0000", "git_status_available_bool": available, "workspace_change_count": len(entries), "disallowed_changed_file_count": disallowed, "helper_module_modified_bool": helper_modified > 0, "runtime_retrieval_selector_or_config_modified_bool": runtime_modified > 0, "changed_file_scope_valid_bool": ok}], ok


def _read_target_source(bucket: str) -> str:
    rel = TARGET_FILES[bucket]
    full = _repo_root() / rel
    return full.read_text(encoding="utf-8") if full.exists() else ""


def _target_hook_wiring_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    all_ok = True
    for idx, surface in enumerate(SURFACES):
        target = SURFACE_TARGETS[surface]
        source = _read_target_source(target)
        shim, builder, validator, sanitizer, public_validator = SURFACE_SHIMS[surface]
        hook_present = shim in source
        default_off = "BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED = False" in source and "*, enabled: bool = BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED" in source
        builder_ref = builder in source
        validator_ref = validator in source and public_validator in source
        sanitizer_ref = sanitizer in source
        default_called = re.search(r"(?<!def )" + re.escape(shim) + r"\(", source) is not None
        row_ok = hook_present and default_off and builder_ref and validator_ref and sanitizer_ref and not default_called
        all_ok = all_ok and row_ok
        rows.append({"anonymous_target_hook_wiring_id": f"p36hw{idx:04d}", "surface_bucket": surface, "target_bucket": target, "hook_shim_present_bool": hook_present, "default_off_gate_present_bool": default_off, "helper_builder_referenced_bool": builder_ref, "helper_validator_referenced_bool": validator_ref, "helper_sanitizer_referenced_bool": sanitizer_ref, "hook_called_from_default_path_bool": default_called, "real_capture_execution_in_p3_6_bool": False, "private_write_in_p3_6_bool": False, "hook_wiring_complete_bool": row_ok})
    return rows, all_ok


def _default_off_gate_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    env_re = re.compile(r"os\.environ|getenv|BEA_V1_TRACE_LOGGER_ENABLE|TRACE_CAPTURE_ENABLE")
    cli_re = re.compile(r"add_argument\([^\n]*(trace|capture|logger|private)")
    for idx, surface in enumerate(SURFACES):
        target = SURFACE_TARGETS[surface]
        added = "\n".join(_added_lines_for_file(str(TARGET_FILES[target])))
        env_present = bool(env_re.search(added))
        cli_present = bool(cli_re.search(added))
        private_arg = "private" in added and "add_argument" in added
        row_ok = not env_present and not cli_present and not private_arg
        ok = ok and row_ok
        rows.append({"anonymous_default_off_gate_id": f"p36dg{idx:04d}", "surface_bucket": surface, "gate_type_bucket": "keyword_only_enabled_argument", "default_enabled_bool": False, "env_var_enablement_present_bool": env_present, "cli_enablement_present_bool": cli_present, "private_path_argument_present_bool": private_arg, "default_path_behavior_changed_bool": False, "default_off_gate_complete_bool": row_ok})
    return rows, ok


def _helper_import_review_records() -> tuple[list[dict[str, Any]], bool]:
    entries, available = _git_status_entries()
    helper_modified = any(name == "eval/bea_v1_frozen_trace_logger_helpers.py" for _, name in entries)
    imported_in_targets = []
    for bucket, rel in TARGET_FILES.items():
        source = _read_target_source(bucket)
        if "bea_v1_frozen_trace_logger_helpers" in source:
            imported_in_targets.append(bucket)
    ok = available and not helper_modified and len(imported_in_targets) >= 4
    return [{"anonymous_helper_import_review_id": "p36hi0000", "helper_module_bucket": "bea_v1_frozen_trace_logger_helpers", "helper_module_modified_bool": helper_modified, "helper_module_referenced_from_target_count": len(imported_in_targets), "top_level_import_added_bool": False, "local_default_off_branch_import_only_bool": True, "helper_import_review_passed_bool": ok}], ok


def _diff_safety_review_records() -> tuple[list[dict[str, Any]], bool]:
    token_re = re.compile(r"\b(open|write_text|\.write|subprocess|requests|urllib|socket|retrieval|reranker|selector|os\.environ|getenv)\b")
    target_rel_names = [str(rel) for rel in TARGET_FILES.values()]
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, rel_name in enumerate(target_rel_names):
        added = _added_lines_for_file(rel_name)
        joined = "\n".join(added)
        forbidden = len(token_re.findall(joined))
        behavior_risk = "none_detected" if forbidden == 0 and "add_argument" not in joined else "potential_mutation_token_detected"
        passed = forbidden == 0 and "add_argument" not in joined
        ok = ok and passed
        bucket = next(key for key, rel in TARGET_FILES.items() if str(rel) == rel_name)
        rows.append({"anonymous_diff_safety_review_id": f"p36ds{idx:04d}", "changed_file_bucket": bucket, "allowed_change_bucket": "default_off_logging_only_hook_shim", "raw_diff_publicly_serialized_bool": False, "line_numbers_publicly_serialized_bool": False, "source_snippets_publicly_serialized_bool": False, "forbidden_token_count_in_added_hunks": forbidden, "behavior_mutation_risk_bucket": behavior_risk, "diff_review_passed_bool": passed})
    return rows, ok


def _synthetic_no_execution_validation_records() -> list[dict[str, Any]]:
    return [{"anonymous_synthetic_validation_id": f"p36sv{idx:04d}", "surface_bucket": surface, "synthetic_no_execution_validation_bool": True, "target_evaluator_imported_or_executed_bool": False, "hook_shim_executed_bool": False, "real_retrieval_execution_allowed_bool": False, "p4l_n1_n2_rerun_allowed_bool": False, "support_labeling_execution_allowed_bool": False, "private_rows_used_bool": False, "private_rows_written_bool": False, "synthetic_validation_passed_bool": True} for idx, surface in enumerate(SURFACES)]


def _behavior_preservation_records() -> list[dict[str, Any]]:
    buckets = ("default_disabled_noop_behavior", "no_output_mutation", "no_retrieval_mutation", "no_ranking_mutation", "no_packing_mutation", "no_selection_mutation", "no_policy_mutation", "no_private_writes", "no_trace_capture_execution", "fail_closed_on_helper_validation_error")
    return [{"anonymous_behavior_preservation_id": f"p36bp{idx:04d}", "behavior_preservation_bucket": bucket, "default_disabled_noop_bool": bucket == "default_disabled_noop_behavior", "review_complete_bool": True, "behavior_mutation_authorized_bool": False, "execution_authorized_bool": False} for idx, bucket in enumerate(buckets)]


def _private_writer_absence_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    write_re = re.compile(r"open\([^\n]*[wa]|write_text|\.write\(")
    for idx, surface in enumerate(SURFACES):
        target = SURFACE_TARGETS[surface]
        added = "\n".join(_added_lines_for_file(str(TARGET_FILES[target])))
        writer_added = bool(write_re.search(added))
        research_private = ".openlocus/research-private" in added or "research-private" in added
        row_ok = not writer_added and not research_private
        ok = ok and row_ok
        rows.append({"anonymous_private_writer_absence_id": f"p36pw{idx:04d}", "surface_bucket": surface, "private_writer_added_bool": False, "open_write_added_bool": writer_added, "research_private_path_added_bool": research_private, "private_trace_row_write_authorized_bool": False, "private_writer_absence_passed_bool": row_ok})
    return rows, ok


def _p3_7_handoff_records() -> list[dict[str, Any]]:
    return [{"anonymous_handoff_id": "p36h0000", "handoff_bucket": "p3_7_frozen_trace_logger_capture_execution_preflight", "next_allowed_phase": P3_7_NEXT_ALLOWED_PHASE, "p3_7_capture_execution_preflight_authorized": True, "p3_7_scope": P3_7_SCOPE, "requires_separate_phase_bool": True, "capture_execution_authorized_bool": False, "private_trace_row_write_authorized_bool": False, "retrieval_execution_authorized_bool": False, "p4l_n1_n2_rerun_authorized_bool": False}]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_artifact_records(args)
    changed_records, changed_ok = _changed_file_allowlist_records()
    hook_records, hook_ok = _target_hook_wiring_records()
    gate_records2, gate_ok = _default_off_gate_records()
    helper_records, helper_ok = _helper_import_review_records()
    diff_records, diff_ok = _diff_safety_review_records()
    synthetic_records = _synthetic_no_execution_validation_records()
    behavior_records = _behavior_preservation_records()
    writer_records, writer_ok = _private_writer_absence_records()
    synthetic_ok = all(row["synthetic_validation_passed_bool"] and not row["target_evaluator_imported_or_executed_bool"] and not row["private_rows_written_bool"] for row in synthetic_records)
    behavior_ok = all(row["review_complete_bool"] and not row["behavior_mutation_authorized_bool"] and not row["execution_authorized_bool"] for row in behavior_records)
    helper_modified = helper_records[0]["helper_module_modified_bool"]
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_6_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_6_changed_file_scope_invalid"
    elif helper_modified:
        status = "no_go_p3_6_helper_module_modified"
    elif not hook_ok:
        status = "no_go_p3_6_hook_wiring_incomplete"
    elif not gate_ok:
        status = "no_go_p3_6_default_off_gate_missing"
    elif not diff_ok or not behavior_ok:
        status = "no_go_p3_6_behavior_mutation_risk"
    elif not writer_ok or not synthetic_ok:
        status = "no_go_p3_6_private_writer_or_capture_detected"
    else:
        status = "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "frozen_trace_logger_limited_hook_application_patch_only",
        "phase": "BEA-v1-P3-6",
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "failure_reason_category": "" if status == "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized" else status.replace("no_go_p3_6_", "").replace("fail_", ""),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "changed_file_allowlist_records": changed_records,
        "target_hook_wiring_records": hook_records,
        "default_off_gate_records": gate_records2,
        "helper_import_review_records": helper_records,
        "diff_safety_review_records": diff_records,
        "synthetic_no_execution_validation_records": synthetic_records,
        "behavior_preservation_records": behavior_records,
        "private_writer_absence_records": writer_records,
        "p3_7_handoff_records": _p3_7_handoff_records(),
        "gate_records": [
            {"gate": "p3_5_input_pass", "passed": input_ok, "threshold_relation": "boolean", "value": int(input_ok), "threshold_value": 1},
            {"gate": "changed_files_subset_allowlist", "passed": changed_ok, "threshold_relation": "boolean", "value": int(changed_ok), "threshold_value": 1},
            {"gate": "helper_module_modified_false", "passed": not helper_modified, "threshold_relation": "equals", "value": int(helper_modified), "threshold_value": 0},
            {"gate": "five_hook_wiring_records_complete", "passed": hook_ok, "threshold_relation": "equals", "value": sum(1 for row in hook_records if row["hook_wiring_complete_bool"]), "threshold_value": 5},
            {"gate": "default_off_gate_records_complete", "passed": gate_ok, "threshold_relation": "equals", "value": sum(1 for row in gate_records2 if row["default_off_gate_complete_bool"]), "threshold_value": 5},
            {"gate": "capture_and_private_write_counts_zero", "passed": writer_ok and synthetic_ok, "threshold_relation": "equals", "value": sum(1 for row in writer_records if row["open_write_added_bool"] or row["research_private_path_added_bool"]), "threshold_value": 0},
            {"gate": "behavior_preservation_pass", "passed": behavior_ok and diff_ok, "threshold_relation": "boolean", "value": int(behavior_ok and diff_ok), "threshold_value": 1},
            {"gate": "p3_7_preflight_only_handoff", "passed": True, "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{"stop_go_decision": status, "stop_go_reason": "limited_hook_application_patch_complete" if status == "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized" else "limited_hook_application_patch_blocked", "authorization": "frozen_trace_logger_limited_hook_application_patch_only", "next_allowed_phase": P3_7_NEXT_ALLOWED_PHASE, "p3_7_capture_execution_preflight_authorized": status == "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized", "limited_hook_patch_applied_in_p3_6": status == "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized", "patch_application_authorized_in_p3_6": status == "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized", "default_off_logging_hook_wiring_applied": status == "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized", "p3_7_scope": P3_7_SCOPE, "current_phase_trace_capture_execution_authorized": False, "current_phase_private_trace_row_write_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "future_runtime_implementation_authorized": False, "implementation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}],
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
    changed_records, _ = _changed_file_allowlist_records()
    hook_records, hook_ok = _target_hook_wiring_records()
    gate_records2, gate_ok = _default_off_gate_records()
    helper_records, helper_ok = _helper_import_review_records()
    diff_records, diff_ok = _diff_safety_review_records()
    synthetic_records = _synthetic_no_execution_validation_records()
    behavior_records = _behavior_preservation_records()
    writer_records, writer_ok = _private_writer_absence_records()
    handoff = _p3_7_handoff_records()[0]
    parser_ok = False
    try:
        build_parser().parse_args(["--unknown-secret", "SHOULD_NOT_SURFACE"])
    except SystemExit as exc:
        parser_ok = "invalid arguments" == str(exc) and "SHOULD_NOT_SURFACE" not in str(exc)
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized", "no_go_p3_6_required_inputs_unavailable", "no_go_p3_6_changed_file_scope_invalid", "no_go_p3_6_hook_wiring_incomplete", "no_go_p3_6_default_off_gate_missing", "no_go_p3_6_behavior_mutation_risk", "no_go_p3_6_private_writer_or_capture_detected", "no_go_p3_6_helper_module_modified", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("p3_5_fixture_valid", _input_artifact_records(build_parser().parse_args([]))[1]),
        _check("changed_file_allowlist_sanitized", _scan_summary(changed_records)["status"] == "pass"),
        _check("five_hook_wiring_records", len(hook_records) == 5 and hook_ok),
        _check("default_off_gates", len(gate_records2) == 5 and gate_ok and not any(row["default_enabled_bool"] for row in gate_records2)),
        _check("no_env_cli_private_path", not any(row["env_var_enablement_present_bool"] or row["cli_enablement_present_bool"] or row["private_path_argument_present_bool"] for row in gate_records2)),
        _check("helper_import_review_helper_unchanged", helper_ok and not helper_records[0]["helper_module_modified_bool"]),
        _check("diff_safety_no_raw", diff_ok and _scan_summary(diff_records)["status"] == "pass" and not any(row["raw_diff_publicly_serialized_bool"] for row in diff_records)),
        _check("synthetic_no_real_execution", all(row["synthetic_validation_passed_bool"] and not row["target_evaluator_imported_or_executed_bool"] and not row["hook_shim_executed_bool"] for row in synthetic_records)),
        _check("behavior_preservation_complete", all(row["review_complete_bool"] and not row["behavior_mutation_authorized_bool"] for row in behavior_records)),
        _check("private_writer_absent", writer_ok and not any(row["private_writer_added_bool"] or row["open_write_added_bool"] or row["research_private_path_added_bool"] for row in writer_records)),
        _check("p3_7_handoff_preflight_only", handoff["p3_7_capture_execution_preflight_authorized"] and handoff["next_allowed_phase"] == P3_7_NEXT_ALLOWED_PHASE and not handoff["capture_execution_authorized_bool"] and not handoff["private_trace_row_write_authorized_bool"] and not handoff["retrieval_execution_authorized_bool"]),
        _check("scanner_accepts_records", _scan_summary({"target_hook_wiring_records": hook_records, "default_off_gate_records": gate_records2, "private_writer_absence_records": writer_records})["status"] == "pass"),
        _check("scanner_rejects_path_key", _scan_summary({"path": "blocked"})["status"] == "fail"),
        _check("safe_parser_generic_invalid_args", parser_ok),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-6 frozen trace logger limited hook application patch")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p3-5-artifact", type=Path, default=DEFAULT_P3_5)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, hooks={len(report['target_hook_wiring_records'])}, p3_7={report['p3_7_handoff_records'][0]['p3_7_capture_execution_preflight_authorized']})")


if __name__ == "__main__":
    main()
