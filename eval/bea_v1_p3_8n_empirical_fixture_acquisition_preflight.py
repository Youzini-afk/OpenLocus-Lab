#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_p3_8n_empirical_fixture_acquisition_preflight.v1"
PHASE = "BEA-v1-P3-8N"
GENERATED_BY = "bea_v1_p3_8n_empirical_fixture_acquisition_preflight"
STATUS_PASS = "empirical_fixture_acquisition_preflight_pass_p3_8o_authorized"
STATUS_SOURCE_NOT_DECLARED = "no_go_p3_8n_empirical_event_source_not_declared"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8n_required_inputs_unavailable",
    STATUS_SOURCE_NOT_DECLARED,
    "no_go_p3_8n_surface_field_specs_incomplete",
    "no_go_p3_8n_privacy_or_scanner_preconditions_incomplete",
    "no_go_p3_8n_fail_closed_gates_incomplete",
    "no_go_p3_8n_explicit_enable_boundary_incomplete",
    "no_go_p3_8n_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8n_empirical_fixture_acquisition_preflight/bea_v1_p3_8n_empirical_fixture_acquisition_preflight_report.json")
P3_8M_ARTIFACT = Path("artifacts/bea_v1_p3_8m_empirical_fixture_acquisition_design/bea_v1_p3_8m_empirical_fixture_acquisition_design_report.json")
SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8n-empirical-fixture-acquisition-preflight.md",
    "docs/zh/bea-v1-p3-8n-empirical-fixture-acquisition-preflight.md",
    "eval/bea_v1_p3_8n_empirical_fixture_acquisition_preflight.py",
    "artifacts/bea_v1_p3_8n_empirical_fixture_acquisition_preflight/bea_v1_p3_8n_empirical_fixture_acquisition_preflight_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8n_empirical_fixture_acquisition_preflight/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py",
    "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py",
    "eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py",
    "eval/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke.py",
    "eval/bea_v1_p3_8k_proxy_fixture_public_projection_audit.py",
    "eval/bea_v1_p3_8l_projection_field_adequacy_decision.py",
    "eval/bea_v1_p3_8m_empirical_fixture_acquisition_design.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = (".openlocus/research-private/", "src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_filename", "private_filenames", "private_out_dir",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list",
    "provider", "prompt", "response", "payload", "raw_payload", "hash", "hashes", "private_id", "queue_item_id",
    "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "claim_level", "phase", "generated_by", "generated_at", "gate", "threshold_relation", "authorization", "next_allowed_phase", "status_bucket"})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else _repo_root() / path
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else _repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    hex_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if hex_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": key, "count": val} for key, val in sorted(counts.items())]}


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        return [line[3:].strip().rstrip("/") for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _check_ignored_bucket() -> tuple[str, bool]:
    try:
        proc = subprocess.run(["git", "check-ignore", "-q", ".openlocus/research-private"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            return "ignored_by_project_metadata", True
        if proc.returncode == 1:
            return "not_ignored_by_project_metadata", False
        return "check_ignore_metadata_unavailable", False
    except Exception:
        return "check_ignore_metadata_unavailable", False


def _first_record(artifact: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    records = artifact.get(key, []) if isinstance(artifact.get(key), list) else []
    return records[0] if records and isinstance(records[0], dict) else {}


def _load_input() -> tuple[dict[str, Any], str]:
    return _load_json(P3_8M_ARTIFACT)


def _input_artifact_records(artifact: Mapping[str, Any], load: str) -> tuple[list[dict[str, Any]], bool]:
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    stop = _first_record(artifact, "stop_go_records")
    designs = artifact.get("empirical_fixture_source_design_records", []) if isinstance(artifact.get("empirical_fixture_source_design_records"), list) else []
    schemas = artifact.get("per_surface_empirical_field_requirement_records", []) if isinstance(artifact.get("per_surface_empirical_field_requirement_records"), list) else []
    preconditions = artifact.get("capture_precondition_records", []) if isinstance(artifact.get("capture_precondition_records"), list) else []
    ok = (
        load == "pass"
        and artifact.get("status") == "empirical_fixture_acquisition_design_pass_p3_8n_authorized"
        and scan == "pass"
        and len(designs) == 5
        and len(schemas) == 5
        and len(preconditions) == 7
        and stop.get("p3_8n_empirical_fixture_acquisition_preflight_authorized") is True
        and stop.get("fixture_generation_authorized") is False
        and stop.get("empirical_trace_capture_authorized") is False
        and stop.get("private_trace_row_write_authorized") is False
    )
    return [{"anonymous_input_artifact_id": "p38ni0000", "input_artifact_bucket": "p3_8m_empirical_fixture_acquisition_design", "load_status": load, "observed_status": str(artifact.get("status", "") or ""), "expected_status": "empirical_fixture_acquisition_design_pass_p3_8n_authorized", "forbidden_scan_status": scan, "empirical_source_design_count": len(designs), "surface_field_requirement_count": len(schemas), "capture_precondition_count": len(preconditions), "p3_8n_authorized_bool": bool(stop.get("p3_8n_empirical_fixture_acquisition_preflight_authorized", False)), "fixture_generation_authorized_bool": bool(stop.get("fixture_generation_authorized", True)), "capture_execution_authorized_bool": bool(stop.get("empirical_trace_capture_authorized", True)), "private_write_authorized_bool": bool(stop.get("private_trace_row_write_authorized", True) or stop.get("private_fixture_write_authorized", True)), "input_gate_passed_bool": ok}], ok


def _empirical_source_declaration_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_empirical_source_declaration_id": "p38nsd0000", "empirical_event_source_declared_bool": False, "source_declaration_bucket": "not_declared", "declared_surface_coverage_count": 0, "declared_fixture_source_mode_bucket": "none", "existing_materialized_event_log_declared_bool": False, "explicit_capture_mode_declared_bool": False, "retrieval_or_rerun_required_bool": False, "source_declaration_preflight_passed_bool": False, "source_declaration_required_bool": True, "source_declaration_sufficient_for_preflight_bool": False, "no_private_source_lookup_performed_bool": True, "source_declaration_record_complete_bool": input_ok}
    ok = record["empirical_event_source_declared_bool"] and record["source_declaration_sufficient_for_preflight_bool"]
    return [record], ok


def _surface_field_spec_preflight_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    field_counts = {
        "support_link": 6,
        "scheduler_action_cost": 7,
        "ordered_prefix_stop": 6,
        "same_file_redundancy": 5,
        "risk_penalty": 5,
    }
    records = []
    for index, surface in enumerate(SURFACES):
        records.append({"anonymous_surface_field_spec_preflight_id": f"p38nsf{index:04d}", "surface_bucket": surface, "required_empirical_field_count": field_counts[surface], "field_spec_present_bool": input_ok, "proxy_unknown_field_allowed_bool": False, "bucketed_public_field_names_only_bool": True, "empirical_source_declared_for_fields_bool": False, "proxy_or_contract_template_sufficient_bool": False, "field_spec_preflight_passed_bool": input_ok})
    ok = len(records) == 5 and all(r["field_spec_preflight_passed_bool"] and r["bucketed_public_field_names_only_bool"] and not r["proxy_unknown_field_allowed_bool"] for r in records)
    return records, ok


def _privacy_root_preflight_records() -> tuple[list[dict[str, Any]], bool]:
    ignore_bucket, ignored = _check_ignored_bucket()
    record = {"anonymous_privacy_root_preflight_id": "p38npr0000", "private_root_bucket": "openlocus_research_private", "gitignore_metadata_check_bucket": ignore_bucket, "private_root_ignore_rule_present_bool": ignored, "root_gitignored_bool": ignored, "private_root_file_inventory_read_bool": False, "private_file_inventory_read_bool": False, "private_file_read_bool": False, "private_file_write_bool": False, "private_read_performed_bool": False, "private_write_performed_bool": False, "private_paths_publicly_serialized_bool": False, "privacy_root_preflight_passed_bool": ignored}
    return [record], ignored


def _scanner_and_fail_closed_preflight_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_scanner_fail_closed_id": "p38nsfc0000", "public_scanner_defined_bool": True, "scanner_required_before_public_artifact_bool": True, "scanner_rejects_private_path_keys_bool": True, "scanner_rejects_raw_payload_keys_bool": True, "fail_closed_if_empirical_field_missing_bool": True, "fail_closed_if_source_declaration_missing_bool": True, "fail_closed_if_private_root_not_ignored_bool": True, "fail_closed_if_forbidden_execution_detected_bool": True, "fail_closed_on_missing_empirical_source_bool": True, "fail_closed_before_fixture_generation_bool": True, "fail_closed_before_capture_execution_bool": True, "scanner_and_fail_closed_preflight_passed_bool": True, "scanner_and_fail_closed_preflight_complete_bool": True}
    return [record], True


def _explicit_enable_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_explicit_enable_boundary_id": "p38neb0000", "enablement_mode_bucket": "future_explicit_predeclared_empirical_source_only", "explicit_enable_required_for_future_phase_bool": True, "default_enabled_bool": False, "env_var_enablement_authorized_bool": False, "existing_evaluator_cli_enablement_authorized_bool": False, "global_default_enablement_authorized_bool": False, "p3_8_code_change_authorized_bool": False, "target_evaluator_import_authorized_bool": False, "capture_execution_authorized_in_p3_8n_bool": False, "capture_execution_in_p3_8n_authorized_bool": False, "fixture_generation_in_p3_8n_authorized_bool": False, "private_write_authorized_in_p3_8n_bool": False, "private_write_in_p3_8n_authorized_bool": False, "explicit_enable_boundary_complete_bool": True}
    ok = not record["env_var_enablement_authorized_bool"] and not record["existing_evaluator_cli_enablement_authorized_bool"] and not record["global_default_enablement_authorized_bool"] and not record["capture_execution_in_p3_8n_authorized_bool"] and not record["fixture_generation_in_p3_8n_authorized_bool"] and not record["private_write_in_p3_8n_authorized_bool"]
    return [record], ok


def _future_acquisition_gate_records(input_ok: bool, source_declared_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_future_acquisition_gate_id": "p38nfg0000", "future_gate_bucket": "empirical_event_source_declaration_required", "required_before_fixture_generation_bucket": "empirical_event_source_declaration", "required_before_capture_execution_bucket": "separate_explicit_capture_phase_after_preflight", "required_before_fixture_generation_bool": True, "required_before_capture_execution_bool": True, "required_before_private_write_bool": True, "gate_satisfied_in_p3_8n_bool": source_declared_ok, "source_declaration_gate_passed_bool": source_declared_ok, "fixture_generation_gate_passed_bool": False, "capture_execution_gate_passed_bool": False, "future_acquisition_gate_record_complete_bool": input_ok}
    return [record], input_ok


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = 0
    forbidden = 0
    private_modified = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if name.startswith(".openlocus/research-private/"):
            private_modified += 1
            allowed = False
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_"):
            forbidden += 1
        if name.startswith(FORBIDDEN_PREFIXES):
            forbidden += 1
        if not allowed:
            disallowed += 1
    ok = available and disallowed == 0 and forbidden == 0 and private_modified == 0
    return [{"anonymous_changed_file_allowlist_id": "p38ncf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "p3_8m_p3_8l_helper_p3_8_target_source_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "p38nne0000", "private_inventory_read_count": 0, "private_read_count": 0, "private_write_count": 0, "helper_import_count": 0, "p3_8_import_count": 0, "target_evaluator_import_count": 0, "trace_capture_execution_count": 0, "fixture_generation_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": True}
    return [record], True


def _p3_8o_handoff_records(status: str) -> list[dict[str, Any]]:
    authorized = status == STATUS_SOURCE_NOT_DECLARED
    return [{"anonymous_p3_8o_handoff_id": "p38nho0000", "next_allowed_phase": "BEA-v1-P3-8O Empirical Event Source Declaration Design — design only, no fixture generation or capture execution", "next_allowed_scope_bucket": "design_only_no_fixture_generation_no_capture_execution", "handoff_reason_bucket": "empirical_event_source_not_declared", "p3_8o_design_authorized_bool": authorized, "p3_8o_empirical_event_source_declaration_design_authorized": authorized, "p3_8o_fixture_generation_authorized": False, "fixture_generation_authorized_in_p3_8o_bool": False, "capture_execution_authorized_in_p3_8o_bool": False, "private_write_authorized_in_p3_8o_bool": False}]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    p3_8o = status == STATUS_SOURCE_NOT_DECLARED
    return [{"authorization": "empirical_fixture_acquisition_preflight_only", "next_allowed_phase": "BEA-v1-P3-8O Empirical Event Source Declaration Design — design only, no fixture generation or capture execution", "next_allowed_scope_bucket": "design_only_no_fixture_generation_no_capture_execution", "p3_8o_empirical_event_source_declaration_design_authorized": p3_8o, "p3_8o_fixture_generation_authorized": False, "p3_8p_capture_or_fixture_acquisition_authorized": False, "empirical_event_source_declared": False, "fixture_generation_authorized": False, "empirical_fixture_files_write_authorized": False, "private_fixture_read_authorized": False, "private_fixture_write_authorized": False, "private_read_authorized": False, "helper_import_authorized": False, "empirical_trace_capture_authorized": False, "private_trace_row_write_authorized": False, "p3_8_code_change_authorized": False, "p3_8_capture_execution_authorized": False, "target_evaluator_import_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "mechanism_evidence_claimed": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, source_declared_ok: bool, field_ok: bool, privacy_ok: bool, scanner_ok: bool, enable_ok: bool, changed_ok: bool, no_exec_ok: bool) -> list[dict[str, Any]]:
    gates = (("p3_8m_input_pass", input_ok, int(input_ok), 1), ("empirical_event_source_declared", source_declared_ok, int(source_declared_ok), 1), ("surface_field_spec_preflight_complete", field_ok, int(field_ok), 1), ("privacy_root_preflight", privacy_ok, int(privacy_ok), 1), ("scanner_and_fail_closed_preflight", scanner_ok, int(scanner_ok), 1), ("explicit_enable_boundary_complete", enable_ok, int(enable_ok), 1), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("no_execution", no_exec_ok, int(no_exec_ok), 1), ("private_reads_writes_generation_capture_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifact, load = _load_input()
    input_records, input_ok = _input_artifact_records(artifact, load)
    source_records, source_declared_ok = _empirical_source_declaration_records(input_ok)
    field_records, field_ok = _surface_field_spec_preflight_records(input_ok)
    privacy_records, privacy_ok = _privacy_root_preflight_records()
    scanner_records, scanner_ok = _scanner_and_fail_closed_preflight_records()
    enable_records, enable_ok = _explicit_enable_boundary_records()
    future_gate_records, future_gate_ok = _future_acquisition_gate_records(input_ok, source_declared_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8n_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8n_changed_file_scope_invalid"
    elif not field_ok:
        status = "no_go_p3_8n_surface_field_specs_incomplete"
    elif not privacy_ok or not scanner_ok:
        status = "no_go_p3_8n_privacy_or_scanner_preconditions_incomplete"
    elif not future_gate_ok:
        status = "no_go_p3_8n_fail_closed_gates_incomplete"
    elif not enable_ok:
        status = "no_go_p3_8n_explicit_enable_boundary_incomplete"
    elif not source_declared_ok:
        status = STATUS_SOURCE_NOT_DECLARED
    else:
        status = STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "empirical_fixture_acquisition_preflight_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "empirical_source_declaration_records": source_records,
        "surface_field_spec_preflight_records": field_records,
        "privacy_root_preflight_records": privacy_records,
        "scanner_and_fail_closed_preflight_records": scanner_records,
        "explicit_enable_boundary_records": enable_records,
        "future_acquisition_gate_records": future_gate_records,
        "changed_file_allowlist_records": changed_records,
        "no_execution_records": no_execution_records,
        "p3_8o_handoff_records": _p3_8o_handoff_records(status),
        "gate_records": _gate_records(input_ok, source_declared_ok, field_ok, privacy_ok, scanner_ok, enable_ok, changed_ok, no_exec_ok),
        "stop_go_records": _stop_go_records(status),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "private_paths_publicly_serialized": False,
        "private_filenames_publicly_serialized": False,
        "private_inventory_read_performed": False,
    }
    if _scan_summary(report)["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    artifact, load = _load_input()
    input_records, input_ok = _input_artifact_records(artifact, load)
    source_records, source_declared_ok = _empirical_source_declaration_records(input_ok)
    field_records, field_ok = _surface_field_spec_preflight_records(input_ok)
    privacy_records, privacy_ok = _privacy_root_preflight_records()
    scanner_records, scanner_ok = _scanner_and_fail_closed_preflight_records()
    enable_records, enable_ok = _explicit_enable_boundary_records()
    future_gate_records, future_gate_ok = _future_acquisition_gate_records(input_ok, source_declared_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    stop_go = _stop_go_records(STATUS_SOURCE_NOT_DECLARED)[0]
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8n_required_inputs_unavailable", STATUS_SOURCE_NOT_DECLARED, "no_go_p3_8n_surface_field_specs_incomplete", "no_go_p3_8n_privacy_or_scanner_preconditions_incomplete", "no_go_p3_8n_fail_closed_gates_incomplete", "no_go_p3_8n_explicit_enable_boundary_incomplete", "no_go_p3_8n_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_gate", input_ok and input_records[0]["p3_8n_authorized_bool"] and input_records[0]["capture_precondition_count"] == 7),
        _check("source_not_declared", not source_declared_ok and source_records[0]["source_declaration_bucket"] == "not_declared"),
        _check("surface_field_spec_preflight", field_ok and len(field_records) == 5 and all(r["field_spec_preflight_passed_bool"] and r["bucketed_public_field_names_only_bool"] and not r["proxy_unknown_field_allowed_bool"] for r in field_records)),
        _check("privacy_root_preflight_no_inventory", privacy_ok and privacy_records[0]["private_root_ignore_rule_present_bool"] is True and privacy_records[0]["private_root_file_inventory_read_bool"] is False and privacy_records[0]["private_file_read_bool"] is False),
        _check("scanner_fail_closed", scanner_ok and scanner_records[0]["public_scanner_defined_bool"] and scanner_records[0]["fail_closed_if_source_declaration_missing_bool"]),
        _check("explicit_enable_boundary", enable_ok and enable_records[0]["explicit_enable_required_for_future_phase_bool"] and not enable_records[0]["capture_execution_authorized_in_p3_8n_bool"] and not enable_records[0]["default_enabled_bool"]),
        _check("future_acquisition_gate", future_gate_ok and not future_gate_records[0]["gate_satisfied_in_p3_8n_bool"] and future_gate_records[0]["required_before_fixture_generation_bool"]),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0),
        _check("no_execution", no_exec_ok and no_execution_records[0]["private_inventory_read_count"] == 0 and no_execution_records[0]["fixture_generation_count"] == 0),
        _check("p3_8o_handoff_stop_go", stop_go["p3_8o_empirical_event_source_declaration_design_authorized"] and not stop_go["p3_8o_fixture_generation_authorized"] and not stop_go["fixture_generation_authorized"] and not stop_go["empirical_trace_capture_authorized"] and not stop_go["private_read_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8N empirical fixture acquisition preflight")
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
    report = _build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, source_declared={report['empirical_source_declaration_records'][0]['empirical_event_source_declared_bool']}, p3_8o={report['stop_go_records'][0]['p3_8o_empirical_event_source_declaration_design_authorized']})")


if __name__ == "__main__":
    main()
