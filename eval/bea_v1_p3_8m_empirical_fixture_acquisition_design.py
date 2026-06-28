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


SCHEMA_VERSION = "bea_v1_p3_8m_empirical_fixture_acquisition_design.v1"
PHASE = "BEA-v1-P3-8M"
GENERATED_BY = "bea_v1_p3_8m_empirical_fixture_acquisition_design"
STATUS_PASS = "empirical_fixture_acquisition_design_pass_p3_8n_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8m_required_inputs_unavailable",
    "no_go_p3_8m_empirical_source_design_incomplete",
    "no_go_p3_8m_surface_field_requirements_incomplete",
    "no_go_p3_8m_privacy_or_precondition_design_incomplete",
    "no_go_p3_8m_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8m_empirical_fixture_acquisition_design/bea_v1_p3_8m_empirical_fixture_acquisition_design_report.json")
P3_8L_ARTIFACT = Path("artifacts/bea_v1_p3_8l_projection_field_adequacy_decision/bea_v1_p3_8l_projection_field_adequacy_decision_report.json")

SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
SOURCE_BUCKETS = {
    "support_link": "future_frozen_materialized_support_pair_event",
    "scheduler_action_cost": "future_frozen_materialized_scheduler_arm_event",
    "ordered_prefix_stop": "future_frozen_materialized_ordered_prefix_event",
    "same_file_redundancy": "future_frozen_materialized_candidate_pool_event",
    "risk_penalty": "future_frozen_materialized_risk_decision_event",
}
FIELD_REQUIREMENTS = {
    "support_link": [
        "target_context_ref_bucket",
        "support_context_ref_bucket",
        "target_hit_observed_bucket",
        "support_hit_observed_bucket",
        "relation_observed_bucket",
        "leakage_observed_bucket",
    ],
    "scheduler_action_cost": [
        "frozen_denominator_ref_bucket",
        "arm_bucket",
        "observed_action_sequence_bucket",
        "observed_pool_size_bucket",
        "observed_latency_bucket",
        "observed_file_reach_bucket",
        "observed_hard_cap_bucket",
    ],
    "ordered_prefix_stop": [
        "frozen_run_ref_bucket",
        "observed_prefix_position_bucket",
        "observed_prefix_cost_bucket",
        "observed_budget_remaining_bucket",
        "observed_stop_reason_bucket",
        "observed_continue_reference_bucket",
    ],
    "same_file_redundancy": [
        "frozen_candidate_pool_ref_bucket",
        "observed_same_file_count_bucket",
        "observed_duplicate_pressure_bucket",
        "observed_file_diversity_bucket",
        "observed_gold_displacement_bucket",
    ],
    "risk_penalty": [
        "frozen_risk_decision_ref_bucket",
        "observed_risk_class_bucket",
        "observed_policy_action_bucket",
        "observed_removed_or_demoted_gold_bucket",
        "observed_replacement_bucket",
    ],
}
CAPTURE_PRECONDITIONS = (
    "frozen_denominator_declared",
    "event_source_declared",
    "existing_materialized_log_or_explicit_capture_mode_declared",
    "no_retrieval_ranking_packing_selection_policy_mutation",
    "private_output_root_ignored",
    "public_scanner_defined",
    "fail_closed_if_empirical_field_missing",
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8m-empirical-fixture-acquisition-design.md",
    "docs/zh/bea-v1-p3-8m-empirical-fixture-acquisition-design.md",
    "eval/bea_v1_p3_8m_empirical_fixture_acquisition_design.py",
    "artifacts/bea_v1_p3_8m_empirical_fixture_acquisition_design/bea_v1_p3_8m_empirical_fixture_acquisition_design_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8m_empirical_fixture_acquisition_design/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py",
    "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py",
    "eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py",
    "eval/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke.py",
    "eval/bea_v1_p3_8k_proxy_fixture_public_projection_audit.py",
    "eval/bea_v1_p3_8l_projection_field_adequacy_decision.py",
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
    return _load_json(P3_8L_ARTIFACT)


def _input_artifact_records(artifact: Mapping[str, Any], load: str) -> tuple[list[dict[str, Any]], bool]:
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    req = _first_record(artifact, "empirical_fixture_requirement_records")
    route = _first_record(artifact, "proxy_route_decision_records")
    stop = _first_record(artifact, "stop_go_records")
    ok = (
        load == "pass"
        and artifact.get("status") == "proxy_route_closure_empirical_fixtures_required"
        and scan == "pass"
        and route.get("decision_bucket") == "proxy_route_closed_for_mechanism_work"
        and req.get("empirical_fixture_required_bool") is True
        and req.get("required_next_input_bucket") == "true_empirical_frozen_materialized_event_fixtures"
        and req.get("proxy_fixtures_sufficient_bool") is False
        and req.get("private_trace_capture_required_before_mechanism_work_bool") is True
        and stop.get("p3_8m_empirical_fixture_acquisition_design_authorized") is True
        and stop.get("empirical_trace_capture_authorized") is False
        and stop.get("private_trace_row_write_authorized") is False
    )
    return [{"anonymous_input_artifact_id": "p38mi0000", "input_artifact_bucket": "p3_8l_projection_field_adequacy_decision", "load_status": load, "observed_status": str(artifact.get("status", "") or ""), "expected_status": "proxy_route_closure_empirical_fixtures_required", "forbidden_scan_status": scan, "proxy_route_closed_for_mechanism_work": route.get("decision_bucket") == "proxy_route_closed_for_mechanism_work", "empirical_fixture_required_bool": bool(req.get("empirical_fixture_required_bool", False)), "proxy_fixtures_sufficient_bool": bool(req.get("proxy_fixtures_sufficient_bool", True)), "p3_8m_authorized_bool": bool(stop.get("p3_8m_empirical_fixture_acquisition_design_authorized", False)), "capture_authorized_bool": bool(stop.get("empirical_trace_capture_authorized", True)), "private_trace_write_authorized_bool": bool(stop.get("private_trace_row_write_authorized", True)), "input_gate_passed_bool": ok}], ok


def _empirical_fixture_source_design_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    records = []
    for index, surface in enumerate(SURFACES):
        records.append({
            "anonymous_source_design_id": f"p38msd{index:04d}",
            "surface_bucket": surface,
            "required_fixture_source_bucket": SOURCE_BUCKETS[surface],
            "allowed_source_mode_bucket": "future_explicit_empirical_capture_or_existing_materialized_event_log",
            "proxy_or_contract_template_allowed_bool": False,
            "proxy_or_contract_source_allowed_bool": False,
            "retrieval_rerun_required_in_p3_8m_bool": False,
            "capture_execution_authorized_in_p3_8m_bool": False,
            "source_design_complete_bool": input_ok,
        })
    ok = len(records) == 5 and all(r["source_design_complete_bool"] and not r["proxy_or_contract_source_allowed_bool"] and not r["retrieval_rerun_required_in_p3_8m_bool"] and not r["capture_execution_authorized_in_p3_8m_bool"] for r in records)
    return records, ok


def _per_surface_empirical_field_requirement_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    records = []
    for index, surface in enumerate(SURFACES):
        fields = FIELD_REQUIREMENTS[surface]
        records.append({
            "anonymous_field_requirement_id": f"p38mfr{index:04d}",
            "surface_bucket": surface,
            "required_empirical_field_count": len(fields),
            "required_field_bucket_list_public": fields,
            "proxy_unknown_field_allowed_bool": False,
            "field_requirement_complete_bool": input_ok,
        })
    ok = len(records) == 5 and all(r["field_requirement_complete_bool"] and r["required_empirical_field_count"] == len(FIELD_REQUIREMENTS[r["surface_bucket"]]) and not r["proxy_unknown_field_allowed_bool"] for r in records)
    return records, ok


def _capture_precondition_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    for index, precondition in enumerate(CAPTURE_PRECONDITIONS):
        records.append({
            "anonymous_capture_precondition_id": f"p38mcp{index:04d}",
            "future_phase_bucket": "BEA-v1-P3-8N",
            "precondition_bucket": precondition,
            "capture_execution_authorized_in_p3_8m_bool": False,
            "retrieval_rerun_authorized_in_p3_8m_bool": False,
            "target_import_authorized_in_p3_8m_bool": False,
            "private_write_authorized_in_p3_8m_bool": False,
            "precondition_required_for_future_execution_bool": True,
        })
    ok = len(records) == len(CAPTURE_PRECONDITIONS) and all(r["precondition_required_for_future_execution_bool"] and not r["capture_execution_authorized_in_p3_8m_bool"] and not r["retrieval_rerun_authorized_in_p3_8m_bool"] and not r["private_write_authorized_in_p3_8m_bool"] for r in records)
    return records, ok


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_privacy_boundary_id": "p38mpb0000",
        "private_fixture_payloads_publicly_serialized_bool": False,
        "private_paths_publicly_serialized_bool": False,
        "raw_event_payloads_publicly_serialized_bool": False,
        "source_paths_spans_snippets_publicly_serialized_bool": False,
        "candidate_lists_publicly_serialized_bool": False,
        "provider_payloads_publicly_serialized_bool": False,
        "public_summary_bucketed_only_bool": True,
        "privacy_boundary_complete_bool": True,
    }
    ok = record["public_summary_bucketed_only_bool"] and all(record[k] is False for k in record if k.endswith("publicly_serialized_bool"))
    return [record], ok


def _acquisition_preflight_plan_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_acquisition_preflight_plan_id": "p38map0000",
        "next_allowed_phase": "BEA-v1-P3-8N Empirical Fixture Acquisition Preflight — preflight only, no capture execution",
        "next_allowed_scope_bucket": "preflight_only_no_capture_execution",
        "p3_8n_preflight_authorized_bool": input_ok,
        "fixture_generation_authorized_bool": False,
        "capture_execution_authorized_bool": False,
        "private_write_authorized_bool": False,
        "fixture_generation_authorized_in_next_phase_bool": False,
        "capture_execution_authorized_in_next_phase_bool": False,
        "private_write_authorized_in_next_phase_bool": False,
        "retrieval_or_rerun_authorized_in_next_phase_bool": False,
        "preflight_plan_complete_bool": input_ok,
    }
    ok = record["preflight_plan_complete_bool"] and record["p3_8n_preflight_authorized_bool"] and not record["fixture_generation_authorized_bool"] and not record["capture_execution_authorized_bool"] and not record["private_write_authorized_bool"] and not record["fixture_generation_authorized_in_next_phase_bool"] and not record["capture_execution_authorized_in_next_phase_bool"] and not record["private_write_authorized_in_next_phase_bool"]
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
    return [{"anonymous_changed_file_allowlist_id": "p38mcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "p3_8l_helper_p3_8_target_source_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "p38mne0000", "private_read_count": 0, "private_write_count": 0, "helper_import_count": 0, "p3_8_import_count": 0, "target_evaluator_import_count": 0, "trace_capture_execution_count": 0, "fixture_generation_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": True}
    return [record], True


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{
        "authorization": "empirical_fixture_acquisition_design_only",
        "next_allowed_phase": "BEA-v1-P3-8N Empirical Fixture Acquisition Preflight — preflight only, no capture execution",
        "next_allowed_scope_bucket": "preflight_only_no_capture_execution",
        "p3_8n_empirical_fixture_acquisition_preflight_authorized": pass_status,
        "fixture_generation_authorized": False,
        "fixture_generation_authorized_in_p3_8m": False,
        "fixture_generation_authorized_in_p3_8n": False,
        "empirical_fixture_files_write_authorized": False,
        "private_fixture_read_authorized": False,
        "private_fixture_write_authorized": False,
        "helper_import_authorized": False,
        "empirical_trace_capture_authorized": False,
        "private_trace_row_write_authorized": False,
        "p3_8_code_change_authorized": False,
        "p3_8_capture_execution_authorized": False,
        "target_evaluator_import_authorized": False,
        "retrieval_execution_authorized": False,
        "p4l_rerun_authorized": False,
        "n1_n2_rerun_authorized": False,
        "support_labeling_authorized": False,
        "denominator_audit_authorized": False,
        "trace_counterfactual_execution_authorized": False,
        "support_counterfactual_execution_authorized": False,
        "mechanism_evidence_claimed": False,
        "policy_tuning_authorized": False,
        "selector_or_reranker_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "broad_retrieval_expansion_authorized": False,
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }]


def _gate_records(input_ok: bool, source_ok: bool, field_ok: bool, privacy_precondition_ok: bool, changed_ok: bool, no_exec_ok: bool) -> list[dict[str, Any]]:
    gates = (("p3_8l_input_pass", input_ok, int(input_ok), 1), ("empirical_source_design_complete", source_ok, int(source_ok), 1), ("surface_field_requirements_complete", field_ok, int(field_ok), 1), ("privacy_or_precondition_design_complete", privacy_precondition_ok, int(privacy_precondition_ok), 1), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("private_read_write_import_and_execution_zero", no_exec_ok, int(no_exec_ok), 1), ("fixture_generation_capture_and_private_write_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifact, load = _load_input()
    input_records, input_ok = _input_artifact_records(artifact, load)
    source_records, source_ok = _empirical_fixture_source_design_records(input_ok)
    field_records, field_ok = _per_surface_empirical_field_requirement_records(input_ok)
    precondition_records, precondition_ok = _capture_precondition_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    preflight_records, preflight_ok = _acquisition_preflight_plan_records(input_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    privacy_precondition_complete = precondition_ok and privacy_ok and preflight_ok and no_exec_ok
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8m_required_inputs_unavailable"
    elif not source_ok:
        status = "no_go_p3_8m_empirical_source_design_incomplete"
    elif not field_ok:
        status = "no_go_p3_8m_surface_field_requirements_incomplete"
    elif not privacy_precondition_complete:
        status = "no_go_p3_8m_privacy_or_precondition_design_incomplete"
    elif not changed_ok:
        status = "no_go_p3_8m_changed_file_scope_invalid"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    if not pass_status:
        preflight_records, _ = _acquisition_preflight_plan_records(False)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "empirical_fixture_acquisition_design_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "empirical_fixture_source_design_records": source_records,
        "per_surface_empirical_field_requirement_records": field_records,
        "capture_precondition_records": precondition_records,
        "privacy_boundary_records": privacy_records,
        "acquisition_preflight_plan_records": preflight_records,
        "changed_file_allowlist_records": changed_records,
        "no_execution_records": no_execution_records,
        "gate_records": _gate_records(input_ok, source_ok, field_ok, privacy_precondition_complete, changed_ok, no_exec_ok),
        "stop_go_records": _stop_go_records(pass_status),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "private_paths_publicly_serialized": False,
        "private_filenames_publicly_serialized": False,
        "raw_fixture_payloads_publicly_serialized": False,
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
    source_records, source_ok = _empirical_fixture_source_design_records(input_ok)
    field_records, field_ok = _per_surface_empirical_field_requirement_records(input_ok)
    precondition_records, precondition_ok = _capture_precondition_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    preflight_records, preflight_ok = _acquisition_preflight_plan_records(input_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    stop_go = _stop_go_records(True)[0]
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8m_required_inputs_unavailable", "no_go_p3_8m_empirical_source_design_incomplete", "no_go_p3_8m_surface_field_requirements_incomplete", "no_go_p3_8m_privacy_or_precondition_design_incomplete", "no_go_p3_8m_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_gate", input_ok and input_records[0]["p3_8m_authorized_bool"]),
        _check("empirical_source_design", source_ok and len(source_records) == 5 and all(not r["proxy_or_contract_source_allowed_bool"] and not r["retrieval_rerun_required_in_p3_8m_bool"] for r in source_records)),
        _check("surface_field_requirements", field_ok and len(field_records) == 5 and all(not r["proxy_unknown_field_allowed_bool"] and r["required_empirical_field_count"] >= 5 for r in field_records)),
        _check("capture_preconditions", precondition_ok and len(precondition_records) == len(CAPTURE_PRECONDITIONS) and all(r["precondition_required_for_future_execution_bool"] for r in precondition_records)),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["public_summary_bucketed_only_bool"] is True and privacy_records[0]["raw_event_payloads_publicly_serialized_bool"] is False),
        _check("p3_8n_preflight_plan", preflight_ok and preflight_records[0]["p3_8n_preflight_authorized_bool"] and not preflight_records[0]["capture_execution_authorized_bool"] and not preflight_records[0]["fixture_generation_authorized_bool"]),
        _check("no_execution", no_exec_ok and no_execution_records[0]["private_read_count"] == 0 and no_execution_records[0]["trace_capture_execution_count"] == 0),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0),
        _check("stop_go", stop_go["p3_8n_empirical_fixture_acquisition_preflight_authorized"] and not stop_go["fixture_generation_authorized"] and not stop_go["empirical_trace_capture_authorized"] and not stop_go["private_trace_row_write_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8M empirical fixture acquisition design")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, source_designs={len(report['empirical_fixture_source_design_records'])}, p3_8n={report['stop_go_records'][0]['p3_8n_empirical_fixture_acquisition_preflight_authorized']})")


if __name__ == "__main__":
    main()
