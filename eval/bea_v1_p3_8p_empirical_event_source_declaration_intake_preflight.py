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


SCHEMA_VERSION = "bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight.v1"
DECLARATION_SCHEMA_VERSION = "bea_v1_p3_8p_empirical_event_source_declaration.v1"
PHASE = "BEA-v1-P3-8P"
GENERATED_BY = "bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight"
STATUS_PASS = "empirical_event_source_declaration_intake_preflight_pass_p3_8q_authorized"
STATUS_MISSING = "no_go_p3_8p_empirical_source_declaration_missing"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8p_required_inputs_unavailable",
    STATUS_MISSING,
    "no_go_p3_8p_declaration_schema_invalid",
    "no_go_p3_8p_surface_coverage_incomplete",
    "no_go_p3_8p_proxy_source_mode_rejected",
    "no_go_p3_8p_retrieval_or_policy_required",
    "no_go_p3_8p_privacy_or_claim_boundary_invalid",
    "no_go_p3_8p_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight_report.json")
P3_8O_ARTIFACT = Path("artifacts/bea_v1_p3_8o_empirical_event_source_declaration_design/bea_v1_p3_8o_empirical_event_source_declaration_design_report.json")
SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
ALLOWED_SOURCE_MODES = ("existing_materialized_event_log", "explicit_future_capture_mode_plan")
REQUIRED_DECLARATION_FIELDS = (
    "declaration_id_bucket",
    "declaration_origin_bucket",
    "source_mode_bucket",
    "surface_coverage_count",
    "frozen_denominator_declared_bool",
    "frozen_event_source_declared_bool",
    "existing_materialized_event_log_declared_bool",
    "explicit_future_capture_mode_declared_bool",
    "retrieval_or_rerun_required_bool",
    "policy_mutation_required_bool",
    "private_output_root_bucket",
    "public_scanner_required_bool",
    "fail_closed_if_field_missing_bool",
    "empirical_trace_claim_boundary_bucket",
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8p-empirical-event-source-declaration-intake-preflight.md",
    "docs/zh/bea-v1-p3-8p-empirical-event-source-declaration-intake-preflight.md",
    "eval/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight.py",
    "artifacts/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight/",)
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
    "eval/bea_v1_p3_8n_empirical_fixture_acquisition_preflight.py",
    "eval/bea_v1_p3_8o_empirical_event_source_declaration_design.py",
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


def _first_record(artifact: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    records = artifact.get(key, []) if isinstance(artifact.get(key), list) else []
    return records[0] if records and isinstance(records[0], dict) else {}


def _input_artifact_records(artifact: Mapping[str, Any], load: str) -> tuple[list[dict[str, Any]], bool]:
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    schema = _first_record(artifact, "event_source_declaration_schema_records")
    stop = _first_record(artifact, "stop_go_records")
    ok = (
        load == "pass"
        and artifact.get("status") == "empirical_event_source_declaration_design_pass_p3_8p_authorized"
        and scan == "pass"
        and int(schema.get("required_field_count", 0) or schema.get("future_field_count", 0) or 0) == 14
        and stop.get(
            "p3_8p_declaration_intake_preflight_authorized",
            stop.get(
                "p3_8p_empirical_event_source_declaration_intake_preflight_authorized",
                stop.get("p3_8p_intake_preflight_authorized_bool"),
            ),
        ) is True
        and stop.get("fixture_generation_authorized") is False
        and stop.get("empirical_trace_capture_authorized") is False
        and stop.get("private_trace_row_write_authorized") is False
    )
    return [{"anonymous_input_artifact_id": "p38pi0000", "input_artifact_bucket": "p3_8o_empirical_event_source_declaration_design", "load_status": load, "observed_status": str(artifact.get("status", "") or ""), "expected_status": "empirical_event_source_declaration_design_pass_p3_8p_authorized", "forbidden_scan_status": scan, "declaration_schema_field_count": int(schema.get("required_field_count", 0) or schema.get("future_field_count", 0) or 0), "p3_8p_intake_preflight_authorized_bool": bool(stop.get("p3_8p_declaration_intake_preflight_authorized", stop.get("p3_8p_empirical_event_source_declaration_intake_preflight_authorized", stop.get("p3_8p_intake_preflight_authorized_bool", False)))), "fixture_generation_authorized_bool": bool(stop.get("fixture_generation_authorized", True)), "capture_authorized_bool": bool(stop.get("empirical_trace_capture_authorized", True)), "private_trace_write_authorized_bool": bool(stop.get("private_trace_row_write_authorized", True)), "input_gate_passed_bool": ok}], ok


def _load_declaration(path: Path | None) -> tuple[dict[str, Any], str, bool]:
    if path is None:
        return {}, "missing", False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, "missing", True
    except Exception:
        return {}, "parse_failed", True
    return (data, "pass", True) if isinstance(data, dict) else ({}, "parse_failed", True)


def _validate_declaration(decl: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_DECLARATION_FIELDS if field not in decl]
    surfaces = decl.get("surface_buckets", []) if isinstance(decl.get("surface_buckets"), list) else []
    source_mode = str(decl.get("source_mode_bucket", "") or "")
    proxy_detected = source_mode in {"proxy_fixture", "committed_aggregate_proxy", "contract_template", "automated_label_proxy"} or "proxy" in source_mode
    retrieval_or_rerun_required = decl.get("retrieval_or_rerun_required_bool") is True
    policy_mutation_required = decl.get("policy_mutation_required_bool") is True
    schema_ok = decl.get("schema_version") == DECLARATION_SCHEMA_VERSION and not missing
    surface_ok = int(decl.get("surface_coverage_count", 0) or 0) == 5 and (not surfaces or sorted(map(str, surfaces)) == sorted(SURFACES))
    source_allowed = source_mode in ALLOWED_SOURCE_MODES
    source_ok = source_allowed and not proxy_detected and decl.get("frozen_denominator_declared_bool") is True and decl.get("frozen_event_source_declared_bool") is True
    if source_mode == "existing_materialized_event_log":
        source_ok = source_ok and decl.get("existing_materialized_event_log_declared_bool") is True and decl.get("explicit_future_capture_mode_declared_bool") is False
    if source_mode == "explicit_future_capture_mode_plan":
        source_ok = source_ok and decl.get("explicit_future_capture_mode_declared_bool") is True and decl.get("existing_materialized_event_log_declared_bool") is False
    forbidden_exec_ok = not retrieval_or_rerun_required and not policy_mutation_required and decl.get("support_labeling_required_bool", False) is False and decl.get("counterfactual_required_bool", False) is False
    privacy_ok = decl.get("private_output_root_bucket") == "openlocus_research_private" and decl.get("public_scanner_required_bool") is True and decl.get("fail_closed_if_field_missing_bool") is True
    claim_ok = decl.get("empirical_trace_claim_boundary_bucket") == "source_declaration_only_no_mechanism_claim"
    return {"schema_valid_bool": schema_ok, "schema_version_valid_bool": decl.get("schema_version") == DECLARATION_SCHEMA_VERSION, "missing_required_field_count": len(missing), "required_field_present_count": len(REQUIRED_DECLARATION_FIELDS) - len(missing), "surface_coverage_valid_bool": surface_ok, "surface_coverage_count": len(set(map(str, surfaces))), "source_mode_allowed_bool": source_allowed, "proxy_source_mode_detected_bool": proxy_detected, "retrieval_or_rerun_required_bool": retrieval_or_rerun_required, "policy_mutation_required_bool": policy_mutation_required, "source_mode_valid_bool": source_ok and forbidden_exec_ok, "source_mode_bucket": source_mode or "missing", "privacy_boundary_valid_bool": privacy_ok and claim_ok, "retrieval_policy_support_counterfactual_boundary_valid_bool": forbidden_exec_ok, "valid_bool": schema_ok and surface_ok and source_ok and forbidden_exec_ok and privacy_ok and claim_ok}


def _declaration_intake_records(load: str, supplied: bool) -> list[dict[str, Any]]:
    return [{"anonymous_declaration_intake_id": "p38pdi0000", "declaration_supplied_bool": supplied, "declaration_source_bucket": "explicit_declaration_json_argument" if supplied else "not_supplied", "declaration_load_status": load if supplied else "not_supplied", "declaration_paths_publicly_serialized_bool": False, "declaration_filenames_publicly_serialized_bool": False, "broad_private_scan_performed_bool": False, "private_write_performed_bool": False, "intake_preflight_passed_bool": supplied and load == "pass"}]


def _schema_validation_records(validation: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_schema_validation_id": "p38psv0000", "expected_schema_version_bucket": "p3_8p_empirical_event_source_declaration_v1", "schema_version_valid_bool": bool(validation.get("schema_version_valid_bool", False)), "required_field_count": len(REQUIRED_DECLARATION_FIELDS), "required_field_present_count": int(validation.get("required_field_present_count", 0) or 0), "missing_required_field_count": int(validation.get("missing_required_field_count", 0) or 0), "schema_validation_passed_bool": bool(validation.get("schema_valid_bool", False))}]


def _surface_coverage_validation_records(validation: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_surface_coverage_validation_id": "p38psc0000", "required_surface_count": 5, "declared_surface_coverage_count": int(validation.get("surface_coverage_count", 0) or 0), "surface_coverage_validation_passed_bool": bool(validation.get("surface_coverage_valid_bool", False))}]


def _source_mode_validation_records(validation: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_source_mode_validation_id": "p38psm0000", "source_mode_bucket": str(validation.get("source_mode_bucket", "missing")), "source_mode_allowed_bool": bool(validation.get("source_mode_allowed_bool", False)), "proxy_source_mode_detected_bool": bool(validation.get("proxy_source_mode_detected_bool", False)), "retrieval_or_rerun_required_bool": bool(validation.get("retrieval_or_rerun_required_bool", False)), "policy_mutation_required_bool": bool(validation.get("policy_mutation_required_bool", False)), "source_mode_validation_passed_bool": bool(validation.get("source_mode_valid_bool", False))}]


def _privacy_and_claim_boundary_records(validation: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_privacy_claim_boundary_id": "p38ppb0000", "private_paths_publicly_serialized_bool": False, "private_filenames_publicly_serialized_bool": False, "raw_declaration_payload_publicly_serialized_bool": False, "empirical_trace_capture_claimed_bool": False, "empirical_fixture_generated_bool": False, "empirical_trace_capture_executed_bool": False, "fixture_generation_authorized_bool": False, "capture_execution_authorized_bool": False, "private_write_authorized_bool": False, "denominator_audit_authorized_bool": False, "counterfactual_authorized_bool": False, "mechanism_evidence_claimed_bool": False, "privacy_and_claim_boundary_passed_bool": bool(validation.get("privacy_boundary_valid_bool", False))}]


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = forbidden = private_modified = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if name.startswith(".openlocus/research-private/"):
            private_modified += 1
            allowed = False
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_") or name.startswith(FORBIDDEN_PREFIXES):
            forbidden += 1
        if not allowed:
            disallowed += 1
    ok = available and disallowed == 0 and forbidden == 0 and private_modified == 0
    return [{"anonymous_changed_file_allowlist_id": "p38pcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "helper_p3_8_target_source_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records(declaration_supplied: bool) -> list[dict[str, Any]]:
    return [{"anonymous_no_execution_id": "p38pne0000", "exact_declaration_read_count": int(declaration_supplied), "broad_private_scan_count": 0, "private_write_count": 0, "helper_import_count": 0, "p3_8_import_count": 0, "target_evaluator_import_count": 0, "trace_capture_execution_count": 0, "fixture_generation_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": True}]


def _p3_8q_handoff_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    next_phase = "BEA-v1-P3-8Q Empirical Fixture Acquisition Plan Preflight — preflight only, no fixture generation or capture execution" if pass_status else "none_until_empirical_event_source_declaration_exists"
    return [{"anonymous_p3_8q_handoff_id": "p38pho0000", "next_allowed_phase": next_phase, "next_allowed_scope_bucket": "preflight_only_no_fixture_generation_no_capture_execution" if pass_status else "blocked_until_valid_declaration", "p3_8q_fixture_acquisition_plan_preflight_authorized_bool": pass_status, "fixture_generation_authorized_in_p3_8q_bool": False, "capture_execution_authorized_in_p3_8q_bool": False, "private_write_authorized_in_p3_8q_bool": False}]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    next_phase = "BEA-v1-P3-8Q Empirical Fixture Acquisition Plan Preflight — preflight only, no fixture generation or capture execution" if pass_status else "none_until_empirical_event_source_declaration_exists"
    return [{"authorization": "empirical_event_source_declaration_intake_preflight_only", "next_allowed_phase": next_phase, "next_allowed_scope_bucket": "preflight_only_no_fixture_generation_no_capture_execution" if pass_status else "blocked_until_valid_declaration", "p3_8q_fixture_acquisition_plan_preflight_authorized": pass_status, "empirical_source_declaration_valid": pass_status, "fixture_generation_authorized": False, "empirical_fixture_files_write_authorized": False, "private_fixture_read_authorized": False, "private_fixture_write_authorized": False, "private_read_authorized": False, "private_write_authorized": False, "helper_import_authorized": False, "empirical_trace_capture_authorized": False, "private_trace_row_write_authorized": False, "p3_8_code_change_authorized": False, "p3_8_capture_execution_authorized": False, "target_evaluator_import_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "mechanism_evidence_claimed": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, supplied: bool, validation: Mapping[str, Any], changed_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "p3_8o_input_pass", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "declaration_supplied", "passed": supplied, "threshold_relation": "equals", "value": int(supplied), "threshold_value": 1},
        {"gate": "schema_valid", "passed": bool(validation.get("schema_valid_bool", False)), "threshold_relation": "equals", "value": int(bool(validation.get("schema_valid_bool", False))), "threshold_value": 1},
        {"gate": "surface_coverage_valid", "passed": bool(validation.get("surface_coverage_valid_bool", False)), "threshold_relation": "equals", "value": int(bool(validation.get("surface_coverage_valid_bool", False))), "threshold_value": 1},
        {"gate": "source_mode_valid", "passed": bool(validation.get("source_mode_valid_bool", False)), "threshold_relation": "equals", "value": int(bool(validation.get("source_mode_valid_bool", False))), "threshold_value": 1},
        {"gate": "privacy_claim_boundary_valid", "passed": bool(validation.get("privacy_boundary_valid_bool", False)), "threshold_relation": "equals", "value": int(bool(validation.get("privacy_boundary_valid_bool", False))), "threshold_value": 1},
        {"gate": "changed_file_scope_valid", "passed": changed_ok, "threshold_relation": "equals", "value": int(changed_ok), "threshold_value": 1},
        {"gate": "capture_generation_private_write_zero", "passed": True, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
    ]


def _status(input_ok: bool, load: str, supplied: bool, validation: Mapping[str, Any], changed_ok: bool) -> str:
    if not input_ok:
        return "no_go_p3_8p_required_inputs_unavailable"
    if not changed_ok:
        return "no_go_p3_8p_changed_file_scope_invalid"
    if not supplied or load == "missing":
        return STATUS_MISSING
    if load != "pass" or not validation.get("schema_valid_bool", False):
        return "no_go_p3_8p_declaration_schema_invalid"
    if not validation.get("surface_coverage_valid_bool", False):
        return "no_go_p3_8p_surface_coverage_incomplete"
    if validation.get("proxy_source_mode_detected_bool", False):
        return "no_go_p3_8p_proxy_source_mode_rejected"
    if validation.get("retrieval_or_rerun_required_bool", False) or validation.get("policy_mutation_required_bool", False):
        return "no_go_p3_8p_retrieval_or_policy_required"
    if not validation.get("source_mode_valid_bool", False):
        return "no_go_p3_8p_declaration_schema_invalid"
    if not validation.get("privacy_boundary_valid_bool", False):
        return "no_go_p3_8p_privacy_or_claim_boundary_invalid"
    return STATUS_PASS


def _build_report(checks: list[dict[str, Any]], declaration_json: Path | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    artifact, input_load = _load_json(P3_8O_ARTIFACT)
    input_records, input_ok = _input_artifact_records(artifact, input_load)
    decl, decl_load, supplied = _load_declaration(declaration_json)
    validation = _validate_declaration(decl) if decl_load == "pass" else {"schema_valid_bool": False, "missing_required_field_count": len(REQUIRED_DECLARATION_FIELDS), "surface_coverage_valid_bool": False, "surface_coverage_count": 0, "source_mode_valid_bool": False, "source_mode_bucket": "missing", "privacy_boundary_valid_bool": False, "retrieval_policy_support_counterfactual_boundary_valid_bool": False, "valid_bool": False}
    changed_records, changed_ok = _changed_file_allowlist_records()
    self_ok = all(c["passed"] for c in checks)
    status = "fail_schema_contract" if not self_ok else _status(input_ok, decl_load, supplied, validation, changed_ok)
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "claim_level": "empirical_event_source_declaration_intake_preflight_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_records, "declaration_intake_records": _declaration_intake_records(decl_load, supplied), "declaration_schema_validation_records": _schema_validation_records(validation), "surface_coverage_validation_records": _surface_coverage_validation_records(validation), "source_mode_validation_records": _source_mode_validation_records(validation), "privacy_and_claim_boundary_records": _privacy_and_claim_boundary_records(validation), "changed_file_allowlist_records": changed_records, "no_execution_records": _no_execution_records(supplied), "p3_8q_handoff_records": _p3_8q_handoff_records(status), "gate_records": _gate_records(input_ok, supplied, validation, changed_ok), "stop_go_records": _stop_go_records(status), "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "private_paths_publicly_serialized": False, "private_filenames_publicly_serialized": False, "raw_declaration_payload_publicly_serialized": False}
    if _scan_summary(report)["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _valid_decl() -> dict[str, Any]:
    return {"schema_version": DECLARATION_SCHEMA_VERSION, "declaration_id_bucket": "synthetic_valid_declaration", "declaration_origin_bucket": "self_test_synthetic", "source_mode_bucket": "existing_materialized_event_log", "surface_coverage_count": 5, "surface_buckets": list(SURFACES), "frozen_denominator_declared_bool": True, "frozen_event_source_declared_bool": True, "existing_materialized_event_log_declared_bool": True, "explicit_future_capture_mode_declared_bool": False, "retrieval_or_rerun_required_bool": False, "policy_mutation_required_bool": False, "private_output_root_bucket": "openlocus_research_private", "public_scanner_required_bool": True, "fail_closed_if_field_missing_bool": True, "empirical_trace_claim_boundary_bucket": "source_declaration_only_no_mechanism_claim"}


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    artifact, input_load = _load_json(P3_8O_ARTIFACT)
    _, input_ok = _input_artifact_records(artifact, input_load)
    valid = _validate_declaration(_valid_decl())
    proxy = dict(_valid_decl(), source_mode_bucket="proxy_fixture_materialized_from_committed_artifact_summary")
    retrieval = dict(_valid_decl(), retrieval_or_rerun_required_bool=True)
    privacy = dict(_valid_decl(), private_output_root_bucket="not_allowed")
    changed_records, changed_ok = _changed_file_allowlist_records()
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8p_required_inputs_unavailable", STATUS_MISSING, "no_go_p3_8p_declaration_schema_invalid", "no_go_p3_8p_surface_coverage_incomplete", "no_go_p3_8p_proxy_source_mode_rejected", "no_go_p3_8p_retrieval_or_policy_required", "no_go_p3_8p_privacy_or_claim_boundary_invalid", "no_go_p3_8p_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_gate", input_ok),
        _check("missing_declaration_no_go", _status(input_ok, "missing", False, {}, True) == STATUS_MISSING),
        _check("valid_synthetic_pass", _status(input_ok, "pass", True, valid, True) == STATUS_PASS and valid["valid_bool"]),
        _check("proxy_source_rejection", not _validate_declaration(proxy)["source_mode_valid_bool"]),
        _check("retrieval_policy_rejection", not _validate_declaration(retrieval)["source_mode_valid_bool"]),
        _check("privacy_boundary_invalid", not _validate_declaration(privacy)["privacy_boundary_valid_bool"]),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0),
        _check("no_private_write_or_execution", _no_execution_records(False)[0]["private_write_count"] == 0 and _no_execution_records(False)[0]["trace_capture_execution_count"] == 0),
        _check("stop_go_missing_false", not _stop_go_records(STATUS_MISSING)[0]["p3_8q_fixture_acquisition_plan_preflight_authorized"] and _stop_go_records(STATUS_MISSING)[0]["next_allowed_phase"] == "none_until_empirical_event_source_declaration_exists"),
        _check("stop_go_pass_limited", _stop_go_records(STATUS_PASS)[0]["p3_8q_fixture_acquisition_plan_preflight_authorized"] and not _stop_go_records(STATUS_PASS)[0]["fixture_generation_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8P empirical event source declaration intake preflight")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--declaration-json", type=Path, default=None)
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
    report = _build_report(checks, args.declaration_json)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, declaration_supplied={report['declaration_intake_records'][0]['declaration_supplied_bool']}, p3_8q={report['stop_go_records'][0]['p3_8q_fixture_acquisition_plan_preflight_authorized']})")


if __name__ == "__main__":
    main()
