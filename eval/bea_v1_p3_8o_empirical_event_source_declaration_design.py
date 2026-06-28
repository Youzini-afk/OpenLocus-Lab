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


SCHEMA_VERSION = "bea_v1_p3_8o_empirical_event_source_declaration_design.v1"
PHASE = "BEA-v1-P3-8O"
GENERATED_BY = "bea_v1_p3_8o_empirical_event_source_declaration_design"
STATUS_PASS = "empirical_event_source_declaration_design_pass_p3_8p_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8o_required_inputs_unavailable",
    "no_go_p3_8o_declaration_schema_incomplete",
    "no_go_p3_8o_surface_source_requirements_incomplete",
    "no_go_p3_8o_validation_rules_incomplete",
    "no_go_p3_8o_privacy_or_claim_boundary_incomplete",
    "no_go_p3_8o_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8o_empirical_event_source_declaration_design/bea_v1_p3_8o_empirical_event_source_declaration_design_report.json")
P3_8N_ARTIFACT = Path("artifacts/bea_v1_p3_8n_empirical_fixture_acquisition_preflight/bea_v1_p3_8n_empirical_fixture_acquisition_preflight_report.json")
SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
SOURCE_MODES = ("existing_materialized_event_log", "explicit_future_capture_mode_plan")
FUTURE_SCHEMA_VERSION = "bea_v1_p3_8p_empirical_event_source_declaration.v1"
FUTURE_FIELDS = (
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
SURFACE_FIELD_SPEC_BUCKETS = {
    "support_link": "p3_8m_support_link_empirical_fields",
    "scheduler_action_cost": "p3_8m_scheduler_action_cost_empirical_fields",
    "ordered_prefix_stop": "p3_8m_ordered_prefix_stop_empirical_fields",
    "same_file_redundancy": "p3_8m_same_file_redundancy_empirical_fields",
    "risk_penalty": "p3_8m_risk_penalty_empirical_fields",
}
SURFACE_SOURCE_BUCKETS = {
    "support_link": "frozen_materialized_support_link_event_source",
    "scheduler_action_cost": "frozen_materialized_scheduler_arm_event_source",
    "ordered_prefix_stop": "frozen_materialized_ordered_prefix_event_source",
    "same_file_redundancy": "frozen_materialized_same_file_redundancy_event_source",
    "risk_penalty": "frozen_materialized_risk_penalty_event_source",
}

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8o-empirical-event-source-declaration-design.md",
    "docs/zh/bea-v1-p3-8o-empirical-event-source-declaration-design.md",
    "eval/bea_v1_p3_8o_empirical_event_source_declaration_design.py",
    "artifacts/bea_v1_p3_8o_empirical_event_source_declaration_design/bea_v1_p3_8o_empirical_event_source_declaration_design_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8o_empirical_event_source_declaration_design/",)
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


def _load_input() -> tuple[dict[str, Any], str]:
    return _load_json(P3_8N_ARTIFACT)


def _input_artifact_records(artifact: Mapping[str, Any], load: str) -> tuple[list[dict[str, Any]], bool]:
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    stop = _first_record(artifact, "stop_go_records")
    source = _first_record(artifact, "empirical_source_declaration_records")
    ok = (
        load == "pass"
        and artifact.get("status") == "no_go_p3_8n_empirical_event_source_not_declared"
        and scan == "pass"
        and source.get("empirical_event_source_declared_bool") is False
        and stop.get("p3_8o_empirical_event_source_declaration_design_authorized") is True
        and stop.get("fixture_generation_authorized") is False
        and stop.get("empirical_trace_capture_authorized") is False
        and stop.get("private_trace_row_write_authorized") is False
        and stop.get("retrieval_execution_authorized") is False
    )
    return [{"anonymous_input_artifact_id": "p38oi0000", "input_artifact_bucket": "p3_8n_empirical_fixture_acquisition_preflight", "load_status": load, "observed_status": str(artifact.get("status", "") or ""), "expected_status": "no_go_p3_8n_empirical_event_source_not_declared", "forbidden_scan_status": scan, "empirical_event_source_declared_bool": bool(source.get("empirical_event_source_declared_bool", True)), "p3_8o_design_authorized_bool": bool(stop.get("p3_8o_empirical_event_source_declaration_design_authorized", False)), "fixture_generation_authorized_bool": bool(stop.get("fixture_generation_authorized", True)), "capture_authorized_bool": bool(stop.get("empirical_trace_capture_authorized", True)), "private_trace_write_authorized_bool": bool(stop.get("private_trace_row_write_authorized", True)), "retrieval_execution_authorized_bool": bool(stop.get("retrieval_execution_authorized", True)), "input_gate_passed_bool": ok}], ok


def _event_source_declaration_schema_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_declaration_schema_id": "p38ods0000", "future_schema_version": FUTURE_SCHEMA_VERSION, "required_field_count": len(FUTURE_FIELDS), "required_field_bucket_list_public": list(FUTURE_FIELDS), "allowed_source_mode_count": len(SOURCE_MODES), "allowed_source_mode_buckets": list(SOURCE_MODES), "existing_materialized_event_log_allowed_bool": True, "explicit_future_capture_mode_plan_allowed_bool": True, "proxy_source_modes_allowed_bool": False, "proxy_fixture_source_allowed_bool": False, "committed_aggregate_proxy_source_allowed_bool": False, "contract_template_source_allowed_bool": False, "schema_design_complete_bool": input_ok}
    ok = record["required_field_count"] == 14 and record["allowed_source_mode_count"] == 2 and record["existing_materialized_event_log_allowed_bool"] and record["explicit_future_capture_mode_plan_allowed_bool"] and not record["proxy_source_modes_allowed_bool"] and record["schema_design_complete_bool"]
    return [record], ok


def _per_surface_source_requirement_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    records = []
    for index, surface in enumerate(SURFACES):
        records.append({"anonymous_surface_source_requirement_id": f"p38osr{index:04d}", "surface_bucket": surface, "required_empirical_source_bucket": SURFACE_SOURCE_BUCKETS[surface], "minimum_event_count_bucket": "at_least_one_empirical_event", "required_field_spec_bucket": SURFACE_FIELD_SPEC_BUCKETS[surface], "proxy_or_contract_source_allowed_bool": False, "retrieval_rerun_required_bool": False, "surface_source_requirement_complete_bool": input_ok})
    ok = len(records) == 5 and all(r["surface_source_requirement_complete_bool"] and r["minimum_event_count_bucket"] == "at_least_one_empirical_event" and not r["proxy_or_contract_source_allowed_bool"] for r in records)
    return records, ok


def _declaration_validation_rule_records() -> tuple[list[dict[str, Any]], bool]:
    rule_buckets = (
        "schema_version_matches",
        "surface_coverage_is_five",
        "source_mode_allowed",
        "proxy_source_modes_rejected",
        "frozen_denominator_declared",
        "frozen_event_source_declared",
        "retrieval_or_rerun_required_false",
        "policy_mutation_required_false",
        "private_root_bucket_declared",
        "public_scanner_required",
        "fail_closed_on_missing_empirical_field_coverage",
    )
    records = [{"anonymous_validation_rule_id": f"p38ovr{index:04d}", "validation_rule_bucket": bucket, "required_for_p3_8p_bool": True, "failure_status_bucket": f"no_go_p3_8p_{bucket}", "rule_design_complete_bool": True} for index, bucket in enumerate(rule_buckets)]
    return records, len(records) >= 10 and all(r["rule_design_complete_bool"] for r in records)


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_privacy_boundary_id": "p38opb0000", "private_paths_publicly_serialized_bool": False, "private_filenames_publicly_serialized_bool": False, "raw_event_payloads_publicly_serialized_bool": False, "source_paths_spans_snippets_publicly_serialized_bool": False, "candidate_lists_publicly_serialized_bool": False, "provider_payloads_publicly_serialized_bool": False, "gold_labels_publicly_serialized_bool": False, "public_summary_bucketed_only_bool": True, "privacy_boundary_complete_bool": True}
    ok = record["public_summary_bucketed_only_bool"] and record["privacy_boundary_complete_bool"] and all(value is False for key, value in record.items() if key.endswith("_bool") and key not in {"public_summary_bucketed_only_bool", "privacy_boundary_complete_bool"})
    return [record], ok


def _claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_claim_boundary_id": "p38ocb0000", "claim_level_bucket": "empirical_event_source_declaration_design_only", "empirical_source_declaration_created_in_p3_8o_bool": False, "empirical_fixtures_generated_bool": False, "empirical_trace_capture_executed_bool": False, "private_fixture_write_executed_bool": False, "mechanism_evidence_claimed_bool": False, "denominator_audit_authorized_bool": False, "counterfactual_authorized_bool": False, "claim_boundary_complete_bool": True}
    ok = record["claim_boundary_complete_bool"] and all(value is False for key, value in record.items() if key.endswith("_bool") and key != "claim_boundary_complete_bool")
    return [record], ok


def _future_intake_preflight_plan_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_future_intake_preflight_plan_id": "p38ofp0000", "next_allowed_phase": "BEA-v1-P3-8P Empirical Event Source Declaration Intake Preflight", "next_allowed_scope_bucket": "preflight_only_validate_declaration_no_fixture_generation", "p3_8p_intake_preflight_authorized_bool": input_ok, "fixture_generation_authorized_in_p3_8p_bool": False, "capture_execution_authorized_in_p3_8p_bool": False, "private_write_authorized_in_p3_8p_bool": False, "future_intake_preflight_plan_complete_bool": input_ok}
    ok = record["future_intake_preflight_plan_complete_bool"] and record["p3_8p_intake_preflight_authorized_bool"] and not record["fixture_generation_authorized_in_p3_8p_bool"] and not record["capture_execution_authorized_in_p3_8p_bool"]
    return [record], ok


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
    return [{"anonymous_changed_file_allowlist_id": "p38ocf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "helper_p3_8_target_source_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "p38one0000", "private_inventory_read_count": 0, "private_read_count": 0, "private_write_count": 0, "helper_import_count": 0, "p3_8_import_count": 0, "target_evaluator_import_count": 0, "trace_capture_execution_count": 0, "fixture_generation_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": True}
    return [record], True


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "empirical_event_source_declaration_design_only", "next_allowed_phase": "BEA-v1-P3-8P Empirical Event Source Declaration Intake Preflight — preflight only, no fixture generation or capture execution", "next_allowed_scope_bucket": "preflight_only_validate_declaration_no_fixture_generation", "p3_8p_empirical_event_source_declaration_intake_preflight_authorized": pass_status, "empirical_event_source_declaration_created": False, "fixture_generation_authorized": False, "empirical_fixture_files_write_authorized": False, "private_fixture_read_authorized": False, "private_fixture_write_authorized": False, "private_read_authorized": False, "helper_import_authorized": False, "empirical_trace_capture_authorized": False, "private_trace_row_write_authorized": False, "p3_8_code_change_authorized": False, "p3_8_capture_execution_authorized": False, "target_evaluator_import_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "mechanism_evidence_claimed": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, schema_ok: bool, surface_ok: bool, validation_ok: bool, boundaries_ok: bool, plan_ok: bool, changed_ok: bool, no_exec_ok: bool) -> list[dict[str, Any]]:
    gates = (("p3_8n_input_pass", input_ok, int(input_ok), 1), ("declaration_schema_complete", schema_ok, int(schema_ok), 1), ("surface_requirements_complete", surface_ok, int(surface_ok), 1), ("validation_rules_complete", validation_ok, int(validation_ok), 1), ("privacy_and_claim_boundaries_complete", boundaries_ok, int(boundaries_ok), 1), ("future_intake_preflight_plan_complete", plan_ok, int(plan_ok), 1), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("no_execution", no_exec_ok, int(no_exec_ok), 1), ("private_reads_writes_generation_capture_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifact, load = _load_input()
    input_records, input_ok = _input_artifact_records(artifact, load)
    schema_records, schema_ok = _event_source_declaration_schema_records(input_ok)
    surface_records, surface_ok = _per_surface_source_requirement_records(input_ok)
    validation_records, validation_ok = _declaration_validation_rule_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    claim_records, claim_ok = _claim_boundary_records()
    plan_records, plan_ok = _future_intake_preflight_plan_records(input_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    boundaries_ok = privacy_ok and claim_ok
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8o_required_inputs_unavailable"
    elif not schema_ok:
        status = "no_go_p3_8o_declaration_schema_incomplete"
    elif not surface_ok:
        status = "no_go_p3_8o_surface_source_requirements_incomplete"
    elif not validation_ok:
        status = "no_go_p3_8o_validation_rules_incomplete"
    elif not boundaries_ok or not plan_ok:
        status = "no_go_p3_8o_privacy_or_claim_boundary_incomplete"
    elif not changed_ok:
        status = "no_go_p3_8o_changed_file_scope_invalid"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    if not pass_status:
        plan_records, _ = _future_intake_preflight_plan_records(False)
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "claim_level": "empirical_event_source_declaration_design_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_records, "event_source_declaration_schema_records": schema_records, "per_surface_source_requirement_records": surface_records, "declaration_validation_rule_records": validation_records, "privacy_boundary_records": privacy_records, "claim_boundary_records": claim_records, "future_intake_preflight_plan_records": plan_records, "changed_file_allowlist_records": changed_records, "no_execution_records": no_execution_records, "gate_records": _gate_records(input_ok, schema_ok, surface_ok, validation_ok, boundaries_ok, plan_ok, changed_ok, no_exec_ok), "stop_go_records": _stop_go_records(pass_status), "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "private_paths_publicly_serialized": False, "private_filenames_publicly_serialized": False, "raw_source_payloads_publicly_serialized": False}
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
    schema_records, schema_ok = _event_source_declaration_schema_records(input_ok)
    surface_records, surface_ok = _per_surface_source_requirement_records(input_ok)
    validation_records, validation_ok = _declaration_validation_rule_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    claim_records, claim_ok = _claim_boundary_records()
    plan_records, plan_ok = _future_intake_preflight_plan_records(input_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    stop_go = _stop_go_records(True)[0]
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8o_required_inputs_unavailable", "no_go_p3_8o_declaration_schema_incomplete", "no_go_p3_8o_surface_source_requirements_incomplete", "no_go_p3_8o_validation_rules_incomplete", "no_go_p3_8o_privacy_or_claim_boundary_incomplete", "no_go_p3_8o_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_gate", input_ok and input_records[0]["p3_8o_design_authorized_bool"]),
        _check("schema_fourteen_fields", schema_ok and schema_records[0]["future_schema_version"] == FUTURE_SCHEMA_VERSION and schema_records[0]["required_field_count"] == 14),
        _check("source_modes_no_proxy", schema_records[0]["allowed_source_mode_buckets"] == list(SOURCE_MODES) and not schema_records[0]["proxy_source_modes_allowed_bool"]),
        _check("surface_requirements", surface_ok and len(surface_records) == 5 and all(not r["proxy_or_contract_source_allowed_bool"] and r["minimum_event_count_bucket"] == "at_least_one_empirical_event" for r in surface_records)),
        _check("validation_rules", validation_ok and len(validation_records) >= 10),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["public_summary_bucketed_only_bool"] and not privacy_records[0]["private_paths_publicly_serialized_bool"]),
        _check("claim_boundary", claim_ok and not claim_records[0]["mechanism_evidence_claimed_bool"] and not claim_records[0]["empirical_source_declaration_created_in_p3_8o_bool"]),
        _check("future_intake_preflight", plan_ok and plan_records[0]["p3_8p_intake_preflight_authorized_bool"]),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0),
        _check("no_execution", no_exec_ok and no_execution_records[0]["private_read_count"] == 0 and no_execution_records[0]["fixture_generation_count"] == 0),
        _check("stop_go", stop_go["p3_8p_empirical_event_source_declaration_intake_preflight_authorized"] and not stop_go["empirical_event_source_declaration_created"] and not stop_go["fixture_generation_authorized"] and not stop_go["empirical_trace_capture_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8O empirical event source declaration design")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, schema_fields={report['event_source_declaration_schema_records'][0]['required_field_count']}, p3_8p={report['stop_go_records'][0]['p3_8p_empirical_event_source_declaration_intake_preflight_authorized']})")


if __name__ == "__main__":
    main()
