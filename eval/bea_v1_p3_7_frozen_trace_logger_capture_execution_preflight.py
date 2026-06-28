#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight.v1"
GENERATED_BY = "eval/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight.py"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight_report.json")
DEFAULT_P3_6 = Path("artifacts/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch_report.json")

STATUSES = (
    "frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized",
    "no_go_p3_7_required_inputs_unavailable",
    "no_go_p3_7_changed_file_scope_invalid",
    "no_go_p3_7_hook_static_readiness_failed",
    "no_go_p3_7_explicit_enable_contract_incomplete",
    "no_go_p3_7_private_output_root_not_ready",
    "no_go_p3_7_manifest_schema_incomplete",
    "no_go_p3_7_synthetic_helper_preflight_failed",
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

TARGET_FILES = {
    "support_link": Path("eval/bea_v1_p0_4_support_link_input_design.py"),
    "scheduler_action_cost": Path("eval/bea_v1_p0_3_scheduler_dataset_export.py"),
    "ordered_prefix_stop": Path("eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py"),
    "same_file_redundancy": Path("eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py"),
    "risk_penalty": Path("eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py"),
}

SURFACE_SHIMS = {
    "support_link": ("_bea_v1_support_link_trace_hook", "build_support_link_trace_capture_row_private", "validate_support_link_trace_capture_row_private", "sanitize_support_link_trace_capture_row_public", "validate_support_link_trace_capture_row_public_projection"),
    "scheduler_action_cost": ("_bea_v1_scheduler_action_cost_trace_hook", "build_scheduler_action_cost_trace_capture_row_private", "validate_scheduler_action_cost_trace_capture_row_private", "sanitize_scheduler_action_cost_trace_capture_row_public", "validate_scheduler_action_cost_trace_capture_row_public_projection"),
    "ordered_prefix_stop": ("_bea_v1_ordered_prefix_stop_trace_hook", "build_ordered_prefix_stop_trace_capture_row_private", "validate_ordered_prefix_stop_trace_capture_row_private", "sanitize_ordered_prefix_stop_trace_capture_row_public", "validate_ordered_prefix_stop_trace_capture_row_public_projection"),
    "same_file_redundancy": ("_bea_v1_same_file_redundancy_trace_hook", "build_same_file_redundancy_trace_capture_row_private", "validate_same_file_redundancy_trace_capture_row_private", "sanitize_same_file_redundancy_trace_capture_row_public", "validate_same_file_redundancy_trace_capture_row_public_projection"),
    "risk_penalty": ("_bea_v1_risk_penalty_trace_hook", "build_risk_penalty_trace_capture_row_private", "validate_risk_penalty_trace_capture_row_private", "sanitize_risk_penalty_trace_capture_row_public", "validate_risk_penalty_trace_capture_row_public_projection"),
}

REQUIRED_EVENT_FIELDS = {
    "support_link": ("anonymous_design_join_key", "queue_item_join_key", "support_relation_bucket", "target_hit_bucket", "support_hit_bucket", "conjunction_bucket", "evidence_role_bucket", "leakage_risk_bucket", "source_context_linkage_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
    "scheduler_action_cost": ("locked_denominator_join_key", "arm_bucket", "action_sequence_bucket", "latency_bucket", "pool_size_bucket", "pool_delta_bucket", "hard_cap_bucket", "file_reach_bucket", "cost_state_bucket", "scheduler_state_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "ordered_prefix_stop": ("prefix_join_key", "arm_bucket", "prefix_position_bucket", "prefix_cost_bucket", "budget_remaining_bucket", "marginal_gain_bucket", "stop_policy_bucket", "continue_reference_bucket", "early_stop_signal_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "same_file_redundancy": ("redundancy_join_key", "action_layer_bucket", "action_arm_bucket", "duplicate_pressure_bucket", "same_file_candidate_count_bucket", "topk_file_diversity_bucket", "gold_file_displacement_bucket", "marginal_utility_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "risk_penalty": ("risk_join_key", "action_layer_bucket", "action_arm_bucket", "risk_class_bucket", "risk_policy_bucket", "removed_gold_bucket", "replacement_bucket", "topk_effect_bucket", "counterfactual_keep_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
}

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-7-frozen-trace-logger-capture-execution-preflight.md",
    "docs/zh/bea-v1-p3-7-frozen-trace-logger-capture-execution-preflight.md",
    "eval/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight.py",
    "artifacts/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight/",)
FORBIDDEN_MODIFIED_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = ("src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")

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
    "stop_go_reason", "authorization", "p3_8_scope", "p3_8_scope_bucket",
    "next_allowed_phase",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
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
        return [(line[:2], line[3:].strip()) for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool, dict[str, Any]]:
    artifact, load_status = _load_json(args.p3_6_artifact)
    expected = "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized"
    scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    observed = str(artifact.get("status", "") or "")
    hook_records = artifact.get("target_hook_wiring_records", []) if isinstance(artifact.get("target_hook_wiring_records"), list) else []
    gate_records = artifact.get("default_off_gate_records", []) if isinstance(artifact.get("default_off_gate_records"), list) else []
    helper_ok = not any(bool(row.get("helper_module_modified_bool")) for row in artifact.get("helper_import_review_records", []) if isinstance(row, dict))
    p3_6_ok = (
        load_status == "pass"
        and observed == expected
        and scan_status == "pass"
        and len(hook_records) == 5
        and len(gate_records) == 5
        and helper_ok
        and not any(bool(row.get("hook_called_from_default_path_bool")) for row in hook_records if isinstance(row, dict))
        and not any(bool(row.get("real_capture_execution_in_p3_6_bool") or row.get("private_write_in_p3_6_bool")) for row in hook_records if isinstance(row, dict))
    )
    return [{"input_artifact_bucket": "p3_6_frozen_trace_logger_limited_hook_application_patch", "source_phase_bucket": "BEA-v1-P3-6", "load_status": load_status, "expected_status": expected, "observed_status": observed, "forbidden_scan_status": scan_status, "target_hook_wiring_record_count": len(hook_records), "default_off_gate_record_count": len(gate_records), "helper_module_modified_bool": not helper_ok, "input_gate_passed": p3_6_ok}], p3_6_ok, artifact


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    entries, available = _git_status_entries()
    disallowed = 0
    helper_or_forbidden_target = 0
    runtime_scope = 0
    for _, name in entries:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if not allowed:
            disallowed += 1
        if name in FORBIDDEN_MODIFIED_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_"):
            helper_or_forbidden_target += 1
        if name.startswith(FORBIDDEN_PREFIXES):
            runtime_scope += 1
    ok = available and disallowed == 0 and helper_or_forbidden_target == 0 and runtime_scope == 0
    return [{"anonymous_changed_file_allowlist_id": "p37cf0000", "git_status_available_bool": available, "workspace_change_count": len(entries), "disallowed_changed_file_count": disallowed, "helper_or_forbidden_target_modified_bool": helper_or_forbidden_target > 0, "runtime_retrieval_selector_or_config_modified_bool": runtime_scope > 0, "changed_file_scope_valid_bool": ok}], ok


def _target_source(surface: str) -> str:
    full = _repo_root() / TARGET_FILES[surface]
    return full.read_text(encoding="utf-8") if full.exists() else ""


def _shim_body(source: str, shim_name: str) -> str:
    marker = "def " + shim_name
    start = source.find(marker)
    if start < 0:
        return ""
    next_def = source.find("\ndef ", start + len(marker))
    return source[start:] if next_def < 0 else source[start:next_def]


def _target_hook_static_readiness_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    all_ok = True
    for idx, surface in enumerate(SURFACES):
        source = _target_source(surface)
        shim, builder, private_validator, sanitizer, public_validator = SURFACE_SHIMS[surface]
        body = _shim_body(source, shim)
        shim_present = bool(body)
        default_off = "BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED = False" in source and "enabled: bool = BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED" in body
        keyword_only = "*, enabled:" in body
        default_path_call = re.search(r"(?<!def )" + re.escape(shim) + r"\(", source) is not None
        helper_refs = all(token in body for token in (builder, private_validator, sanitizer, public_validator))
        env_cli_private = bool(re.search(r"os\.environ|getenv|add_argument|private_path|private.*Path", body))
        row_ok = shim_present and default_off and keyword_only and helper_refs and not default_path_call and not env_cli_private
        all_ok = all_ok and row_ok
        rows.append({"anonymous_static_readiness_id": f"p37sr{idx:04d}", "surface_bucket": surface, "target_bucket": surface + "_target", "shim_present_bool": shim_present, "default_off_bool": default_off, "keyword_only_enabled_arg_bool": keyword_only, "no_default_path_call_bool": not default_path_call, "helper_refs_present_bool": helper_refs, "env_cli_private_path_enablement_present_bool": env_cli_private, "hook_static_readiness_passed_bool": row_ok})
    return rows, all_ok


def _explicit_enable_contract_records(parser_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    rows = [{"anonymous_enable_contract_id": "p37ec0000", "enablement_mode_bucket": "explicit_p3_8_evaluator_argument_only", "no_env_var_enablement_bool": True, "no_existing_evaluator_cli_enablement_bool": True, "no_global_default_enablement_bool": True, "private_output_arg_allowed_only_in_p3_8_evaluator_bool": True, "safe_parser_hides_unknown_argument_values_bool": parser_ok, "explicit_enable_contract_complete_bool": parser_ok}]
    return rows, parser_ok


def _private_output_root_preflight_records() -> tuple[list[dict[str, Any]], bool]:
    repo = _repo_root()
    root = repo / ".openlocus" / "research-private"
    ignored = False
    try:
        proc = subprocess.run(["git", "check-ignore", "-q", ".openlocus/research-private"], cwd=repo, check=False, capture_output=True, text=True, timeout=10)
        ignored = proc.returncode == 0
    except Exception:
        ignored = False
    ok = root.exists() and root.is_dir() and ignored
    rows = [{"anonymous_private_root_preflight_id": "p37pr0000", "research_private_root_bucket": "openlocus_research_private", "root_exists_bool": root.exists() and root.is_dir(), "root_gitignored_bool": ignored, "private_output_path_publicly_serialized_bool": False, "private_manifest_schema_defined_bool": True, "private_write_permitted_in_p3_7_bool": False, "private_output_root_preflight_passed_bool": ok}]
    return rows, ok


def _private_manifest_schema_records() -> tuple[list[dict[str, Any]], bool]:
    fields = ("capture_run_id_bucket", "surface_bucket", "private_jsonl_rel_bucket", "row_count", "schema_valid_count", "scanner_public_projection_status", "frozen_event_source_bucket", "capture_execution_mode_bucket")
    rows = [{"anonymous_manifest_schema_id": "p37ms0000", "manifest_schema_version": "bea_v1_p3_8_frozen_trace_capture_private_manifest.v1", "required_field_buckets": list(fields), "required_field_count": len(fields), "private_manifest_schema_complete_bool": True, "private_manifest_write_authorized_in_p3_7_bool": False}]
    return rows, True


def _load_helpers() -> Any:
    eval_dir = Path(__file__).resolve().parent
    if str(eval_dir) not in sys.path:
        sys.path.insert(0, str(eval_dir))
    return importlib.import_module("bea_v1_frozen_trace_logger_helpers")


def _synthetic_event(surface: str) -> dict[str, Any]:
    event: dict[str, Any] = {"trace_completeness_bucket": "synthetic_complete"}
    for key in REQUIRED_EVENT_FIELDS[surface]:
        event[key] = "synthetic_" + key.replace("_bucket", "")
    event["anonymous_public_trace_id"] = "synthetic_public_trace"
    return event


def _synthetic_helper_preflight_records() -> tuple[list[dict[str, Any]], bool]:
    helpers = _load_helpers()
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, surface in enumerate(SURFACES):
        shim, builder_name, private_validator_name, sanitizer_name, public_validator_name = SURFACE_SHIMS[surface]
        builder = getattr(helpers, builder_name)
        private_validator = getattr(helpers, private_validator_name)
        sanitizer = getattr(helpers, sanitizer_name)
        public_validator = getattr(helpers, public_validator_name)
        private_row = builder(_synthetic_event(surface))
        private_status = private_validator(private_row)
        public_row = sanitizer({**private_row, "anonymous_public_trace_id": "synthetic_public_trace"})
        public_status = public_validator(public_row)
        passed = private_status.get("validation_status") == "pass" and public_status.get("validation_status") == "pass" and _scan_summary(public_row)["status"] == "pass"
        ok = ok and passed
        rows.append({"anonymous_synthetic_helper_preflight_id": f"p37hp{idx:04d}", "surface_bucket": surface, "helper_only_synthetic_in_memory_bool": True, "target_evaluator_imported_bool": False, "hook_shim_called_bool": False, "private_row_written_bool": False, "real_capture_execution_bool": False, "private_validation_status_bucket": str(private_status.get("validation_status", "")), "public_validation_status_bucket": str(public_status.get("validation_status", "")), "synthetic_helper_preflight_passed_bool": passed})
    return rows, ok


def _per_surface_capture_readiness_records(static_rows: list[dict[str, Any]], root_ok: bool, manifest_ok: bool, helper_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    static_by_surface = {row["surface_bucket"]: row for row in static_rows}
    helper_by_surface = {row["surface_bucket"]: row for row in helper_rows}
    for idx, surface in enumerate(SURFACES):
        ready = bool(static_by_surface[surface]["hook_static_readiness_passed_bool"] and helper_by_surface[surface]["synthetic_helper_preflight_passed_bool"] and root_ok and manifest_ok)
        ok = ok and ready
        rows.append({
            "anonymous_surface_capture_readiness_id": f"p37cr{idx:04d}",
            "surface_bucket": surface,
            "hook_shim_present_bool": bool(static_by_surface[surface]["shim_present_bool"]),
            "default_off_gate_present_bool": bool(static_by_surface[surface]["default_off_bool"]),
            "default_path_call_absent_bool": bool(static_by_surface[surface]["no_default_path_call_bool"]),
            "helper_contract_validated_synthetically_bool": bool(helper_by_surface[surface]["synthetic_helper_preflight_passed_bool"]),
            "future_event_source_required_bool": True,
            "future_private_manifest_required_bool": True,
            "static_readiness_passed_bool": bool(static_by_surface[surface]["hook_static_readiness_passed_bool"]),
            "synthetic_helper_preflight_passed_bool": bool(helper_by_surface[surface]["synthetic_helper_preflight_passed_bool"]),
            "private_root_preflight_passed_bool": root_ok,
            "manifest_schema_passed_bool": manifest_ok,
            "ready_for_p3_8_explicit_capture_smoke_bool": ready,
            "capture_execution_ready_for_p3_8_preflight_bool": ready,
            "capture_execution_authorized_in_p3_7_bool": False,
        })
    return rows, ok


def _no_execution_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [{"anonymous_no_execution_boundary_id": "p37ne0000", "target_evaluator_import_count": 0, "target_evaluator_execution_count": 0, "hook_shim_execution_count": 0, "private_write_count": 0, "real_capture_execution_count": 0, "retrieval_execution_count": 0, "p4l_execution_count": 0, "n1_n2_execution_count": 0, "support_label_execution_count": 0, "denominator_audit_execution_count": 0, "counterfactual_execution_count": 0, "no_execution_boundary_passed_bool": True}]
    return rows, True


def _p3_8_handoff_records() -> list[dict[str, Any]]:
    return [{"anonymous_handoff_id": "p37h0000", "handoff_bucket": "BEA-v1-P3-8 Frozen Trace Logger Explicit Capture Smoke", "p3_8_explicit_capture_smoke_authorized": True, "p3_8_scope": "BEA-v1-P3-8 Frozen Trace Logger Explicit Capture Smoke — explicitly enabled separate-phase smoke using predeclared frozen/materialized event fixtures only; no retrieval/P4L/N1/N2 reruns/support labeling/counterfactuals/policy/P5/v1-A/runtime/default promotion/broad retrieval.", "requires_separate_phase_bool": True, "capture_execution_authorized_in_p3_7_bool": False, "private_trace_row_write_authorized_in_p3_7_bool": False, "retrieval_execution_authorized_bool": False, "p4l_n1_n2_rerun_authorized_bool": False}]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]], parser_ok: bool) -> dict[str, Any]:
    start = time.perf_counter()
    input_rows, input_ok, _ = _input_artifact_records(args)
    changed_rows, changed_ok = _changed_file_allowlist_records()
    static_rows, static_ok = _target_hook_static_readiness_records()
    enable_rows, enable_ok = _explicit_enable_contract_records(parser_ok)
    root_rows, root_ok = _private_output_root_preflight_records()
    manifest_rows, manifest_ok = _private_manifest_schema_records()
    helper_rows, helper_ok = _synthetic_helper_preflight_records()
    readiness_rows, readiness_ok = _per_surface_capture_readiness_records(static_rows, root_ok, manifest_ok, helper_rows)
    no_exec_rows, no_exec_ok = _no_execution_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_7_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_7_changed_file_scope_invalid"
    elif not static_ok:
        status = "no_go_p3_7_hook_static_readiness_failed"
    elif not enable_ok:
        status = "no_go_p3_7_explicit_enable_contract_incomplete"
    elif not root_ok:
        status = "no_go_p3_7_private_output_root_not_ready"
    elif not manifest_ok:
        status = "no_go_p3_7_manifest_schema_incomplete"
    elif not helper_ok or not readiness_ok or not no_exec_ok:
        status = "no_go_p3_7_synthetic_helper_preflight_failed"
    else:
        status = "frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "frozen_trace_logger_capture_execution_preflight_only",
        "phase": "BEA-v1-P3-7",
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "failure_reason_category": "" if status == "frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized" else status.replace("no_go_p3_7_", "").replace("fail_", ""),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_rows,
        "changed_file_allowlist_records": changed_rows,
        "target_hook_static_readiness_records": static_rows,
        "explicit_enable_contract_records": enable_rows,
        "private_output_root_preflight_records": root_rows,
        "private_manifest_schema_records": manifest_rows,
        "per_surface_capture_readiness_records": readiness_rows,
        "synthetic_helper_preflight_records": helper_rows,
        "no_execution_boundary_records": no_exec_rows,
        "p3_8_handoff_records": _p3_8_handoff_records(),
        "gate_records": [
            {"gate": "p3_6_input_pass", "passed": input_ok, "threshold_relation": "boolean", "value": int(input_ok), "threshold_value": 1},
            {"gate": "changed_files_subset_allowlist", "passed": changed_ok, "threshold_relation": "boolean", "value": int(changed_ok), "threshold_value": 1},
            {"gate": "hook_static_readiness_5_of_5", "passed": static_ok, "threshold_relation": "equals", "value": sum(1 for row in static_rows if row["hook_static_readiness_passed_bool"]), "threshold_value": 5},
            {"gate": "explicit_enable_contract_complete", "passed": enable_ok, "threshold_relation": "boolean", "value": int(enable_ok), "threshold_value": 1},
            {"gate": "private_output_root_ready", "passed": root_ok, "threshold_relation": "boolean", "value": int(root_ok), "threshold_value": 1},
            {"gate": "manifest_schema_defined", "passed": manifest_ok, "threshold_relation": "boolean", "value": int(manifest_ok), "threshold_value": 1},
            {"gate": "synthetic_helper_preflight_5_of_5", "passed": helper_ok, "threshold_relation": "equals", "value": sum(1 for row in helper_rows if row["synthetic_helper_preflight_passed_bool"]), "threshold_value": 5},
            {"gate": "no_execution_boundary_zero_counts", "passed": no_exec_ok, "threshold_relation": "equals", "value": no_exec_rows[0]["real_capture_execution_count"], "threshold_value": 0},
            {"gate": "p3_8_handoff_preflight_only", "passed": True, "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{"stop_go_decision": status, "stop_go_reason": "capture_execution_preflight_complete" if status == "frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized" else "capture_execution_preflight_blocked", "authorization": "frozen_trace_logger_capture_execution_preflight_only", "next_allowed_phase": "BEA-v1-P3-8 Frozen Trace Logger Explicit Capture Smoke — explicitly enabled separate-phase smoke using predeclared frozen/materialized event fixtures only", "p3_8_explicit_capture_smoke_authorized": status == "frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized", "p3_8_scope": "BEA-v1-P3-8 Frozen Trace Logger Explicit Capture Smoke — explicitly enabled separate-phase smoke using predeclared frozen/materialized event fixtures only; no retrieval/P4L/N1/N2 reruns/support labeling/counterfactuals/policy/P5/v1-A/runtime/default promotion/broad retrieval.", "capture_execution_authorized_in_p3_7": False, "private_trace_row_write_authorized_in_p3_7": False, "current_phase_trace_capture_execution_authorized": False, "current_phase_private_trace_row_write_authorized": False, "target_evaluator_execution_authorized": False, "target_evaluator_import_authorized": False, "hook_shim_execution_authorized_in_p3_7": False, "target_hook_shim_call_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "implementation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}],
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


def _parser_unknown_arg_hidden() -> bool:
    try:
        build_parser().parse_args(["--unknown-secret", "SHOULD_NOT_SURFACE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SHOULD_NOT_SURFACE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool, bool]:
    parser_ok = _parser_unknown_arg_hidden()
    input_ok = _input_artifact_records(build_parser().parse_args([]))[1]
    changed_rows, changed_ok = _changed_file_allowlist_records()
    static_rows, static_ok = _target_hook_static_readiness_records()
    enable_rows, enable_ok = _explicit_enable_contract_records(parser_ok)
    root_rows, root_ok = _private_output_root_preflight_records()
    manifest_rows, manifest_ok = _private_manifest_schema_records()
    helper_rows, helper_ok = _synthetic_helper_preflight_records()
    readiness_rows, readiness_ok = _per_surface_capture_readiness_records(static_rows, root_ok, manifest_ok, helper_rows)
    no_exec_rows, no_exec_ok = _no_execution_boundary_records()
    handoff = _p3_8_handoff_records()[0]
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized", "no_go_p3_7_required_inputs_unavailable", "no_go_p3_7_changed_file_scope_invalid", "no_go_p3_7_hook_static_readiness_failed", "no_go_p3_7_explicit_enable_contract_incomplete", "no_go_p3_7_private_output_root_not_ready", "no_go_p3_7_manifest_schema_incomplete", "no_go_p3_7_synthetic_helper_preflight_failed", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("p3_6_fixture_valid", input_ok),
        _check("changed_file_allowlist", changed_ok and _scan_summary(changed_rows)["status"] == "pass"),
        _check("target_evaluators_forbidden_in_p3_7_change_scope", not any(str(path) in ALLOWED_CHANGED_EXACT for path in TARGET_FILES.values()) and all(str(path) in FORBIDDEN_MODIFIED_EXACT for path in TARGET_FILES.values())),
        _check("static_hook_readiness", static_ok and len(static_rows) == 5),
        _check("explicit_enable_contract", enable_ok and enable_rows[0]["enablement_mode_bucket"] == "explicit_p3_8_evaluator_argument_only"),
        _check("private_root_fixture_gate", root_ok and root_rows[0]["root_exists_bool"] and root_rows[0]["root_gitignored_bool"]),
        _check("manifest_schema", manifest_ok and manifest_rows[0]["required_field_count"] == 8),
        _check("per_surface_readiness", readiness_ok and len(readiness_rows) == 5),
        _check("helper_only_synthetic_validation", helper_ok and all(not row["target_evaluator_imported_bool"] and not row["hook_shim_called_bool"] and not row["private_row_written_bool"] for row in helper_rows)),
        _check("no_execution_boundary", no_exec_ok and no_exec_rows[0]["target_evaluator_import_count"] == 0 and no_exec_rows[0]["hook_shim_execution_count"] == 0),
        _check("per_surface_readiness_contract_fields", readiness_ok and all(row.get("ready_for_p3_8_explicit_capture_smoke_bool") and row.get("future_event_source_required_bool") and row.get("future_private_manifest_required_bool") for row in readiness_rows)),
        _check("p3_8_handoff", handoff["p3_8_explicit_capture_smoke_authorized"] and not handoff["capture_execution_authorized_in_p3_7_bool"] and "BEA-v1-P3-8 Frozen Trace Logger Explicit Capture Smoke" in handoff["p3_8_scope"]),
        _check("scanner_accepts_records", _scan_summary({"target_hook_static_readiness_records": static_rows, "explicit_enable_contract_records": enable_rows, "private_output_root_preflight_records": root_rows, "synthetic_helper_preflight_records": helper_rows})["status"] == "pass"),
        _check("scanner_rejects_path_key", _scan_summary({"path": "blocked"})["status"] == "fail"),
        _check("safe_parser_generic_invalid_args", parser_ok),
    ]
    return checks, all(c["passed"] for c in checks), parser_ok


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-7 frozen trace logger capture execution preflight")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p3-6-artifact", type=Path, default=DEFAULT_P3_6)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok, parser_ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(args, checks, parser_ok)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, surfaces={len(report['per_surface_capture_readiness_records'])}, p3_8={report['p3_8_handoff_records'][0]['p3_8_explicit_capture_smoke_authorized']})")


if __name__ == "__main__":
    main()
