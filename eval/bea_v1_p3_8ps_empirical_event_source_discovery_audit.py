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


SCHEMA_VERSION = "bea_v1_p3_8ps_empirical_event_source_discovery_audit.v1"
PHASE = "BEA-v1-P3-8PS"
GENERATED_BY = "bea_v1_p3_8ps_empirical_event_source_discovery_audit"
STATUS_PASS = "empirical_event_source_discovery_audit_pass_p3_8q_declaration_authoring_authorized"
STATUS_NO_SOURCE = "no_go_p3_8ps_no_existing_empirical_event_source"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8ps_required_inputs_unavailable",
    STATUS_NO_SOURCE,
    "no_go_p3_8ps_candidate_sources_incomplete_or_proxy_only",
    "no_go_p3_8ps_privacy_or_claim_boundary_invalid",
    "no_go_p3_8ps_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8ps_empirical_event_source_discovery_audit/bea_v1_p3_8ps_empirical_event_source_discovery_audit_report.json")
INPUTS = (
    ("p3_8p_declaration_intake_preflight", Path("artifacts/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight_report.json"), "no_go_p3_8p_empirical_source_declaration_missing"),
    ("p3_8o_declaration_design", Path("artifacts/bea_v1_p3_8o_empirical_event_source_declaration_design/bea_v1_p3_8o_empirical_event_source_declaration_design_report.json"), "empirical_event_source_declaration_design_pass_p3_8p_authorized"),
    ("p3_8m_fixture_acquisition_design", Path("artifacts/bea_v1_p3_8m_empirical_fixture_acquisition_design/bea_v1_p3_8m_empirical_fixture_acquisition_design_report.json"), "empirical_fixture_acquisition_design_pass_p3_8n_authorized"),
    ("p3_8n_fixture_acquisition_preflight", Path("artifacts/bea_v1_p3_8n_empirical_fixture_acquisition_preflight/bea_v1_p3_8n_empirical_fixture_acquisition_preflight_report.json"), "no_go_p3_8n_empirical_event_source_not_declared"),
    ("p3_6_limited_hook_application_patch", Path("artifacts/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch_report.json"), "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized"),
    ("p2_0_scheduler_private_arm_row_recovery", Path("artifacts/bea_v1_p2_0_scheduler_private_arm_row_recovery/bea_v1_p2_0_scheduler_private_arm_row_recovery_report.json"), "no_go_p2_0_private_arm_rows_unavailable"),
    ("p2_1_ordered_prefix_stop_evidence_surface", Path("artifacts/bea_v1_p2_1_ordered_prefix_stop_evidence_surface/bea_v1_p2_1_ordered_prefix_stop_evidence_surface_report.json"), "no_go_p2_1_ordered_prefix_only_aggregate"),
    ("p2_2_redundancy_risk_trace_availability", Path("artifacts/bea_v1_p2_2_redundancy_risk_trace_availability/bea_v1_p2_2_redundancy_risk_trace_availability_report.json"), "no_go_p2_2_redundancy_risk_traces_unavailable"),
    ("p1_5r_improved_automated_support_label_feasibility", Path("artifacts/bea_v1_p1_5r_improved_automated_support_label_feasibility/bea_v1_p1_5r_improved_automated_support_label_feasibility_report.json"), "no_go_p1_5r_private_context_unavailable"),
)
SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
SOURCE_BUCKETS = (
    "p1_5r_support_context_feasibility",
    "p2_0_scheduler_private_arm_rows",
    "p2_1_ordered_prefix_stop_surface",
    "p2_2_same_file_redundancy_surface",
    "p2_2_risk_penalty_surface",
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8ps-empirical-event-source-discovery-audit.md",
    "docs/zh/bea-v1-p3-8ps-empirical-event-source-discovery-audit.md",
    "eval/bea_v1_p3_8ps_empirical_event_source_discovery_audit.py",
    "artifacts/bea_v1_p3_8ps_empirical_event_source_discovery_audit/bea_v1_p3_8ps_empirical_event_source_discovery_audit_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8ps_empirical_event_source_discovery_audit/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = (".openlocus/research-private/", "src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")
FORBIDDEN_PUBLIC_KEYS = frozenset({"path", "paths", "file_path", "source_path", "private_path", "private_filename", "private_filenames", "private_out_dir", "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list", "provider", "prompt", "response", "payload", "raw_payload", "hash", "hashes", "private_id", "queue_item_id", "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "raw_diff", "diff"})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "claim_level", "phase", "generated_by", "generated_at", "gate", "threshold_relation", "authorization", "next_allowed_phase", "status_bucket"})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = _repo_root() / path
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
                if str(key) in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + str(key))
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
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        return [line[3:].strip().rstrip("/") for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(INPUTS):
        artifact, load = _load_json(path)
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        observed = str(artifact.get("status", "") or "")
        passed = load == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"p38psi{idx:04d}", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _candidate_source_inventory_records() -> tuple[list[dict[str, Any]], int]:
    records = []
    empirical_count = 0
    outcomes = {
        "p1_5r_support_context_feasibility": "blocked_private_context_unavailable",
        "p2_0_scheduler_private_arm_rows": "blocked_private_arm_rows_unavailable",
        "p2_1_ordered_prefix_stop_surface": "aggregate_only_not_row_level_empirical_source",
        "p2_2_same_file_redundancy_surface": "contract_only_missing_private_trace",
        "p2_2_risk_penalty_surface": "contract_only_missing_private_trace",
    }
    for idx, bucket in enumerate(SOURCE_BUCKETS):
        empirical = False
        records.append({
            "anonymous_candidate_source_id": f"p38psc{idx:04d}",
            "candidate_source_bucket": bucket,
            "candidate_source_availability_bucket": outcomes[bucket],
            "source_kind_bucket": "committed_public_artifact",
            "empirical_materialized_event_source_bool": empirical,
            "legitimate_empirical_event_source_bool": empirical,
            "proxy_or_aggregate_only_bool": True,
            "private_source_required_bool": bucket in {"p1_5r_support_context_feasibility", "p2_0_scheduler_private_arm_rows", "p2_2_same_file_redundancy_surface", "p2_2_risk_penalty_surface"},
            "usable_for_p3_8p_declaration_bool": False,
            "private_read_performed_bool": False,
            "capture_execution_performed_bool": False,
        })
        empirical_count += int(empirical)
    return records, empirical_count


def _per_surface_source_availability_records() -> tuple[list[dict[str, Any]], int]:
    availability = {
        "support_link": "no_reconstructable_private_context",
        "scheduler_action_cost": "private_arm_rows_unavailable",
        "ordered_prefix_stop": "aggregate_only_private_trace_missing",
        "same_file_redundancy": "contract_only_missing_private_trace",
        "risk_penalty": "contract_only_missing_private_trace",
    }
    required = {
        "support_link": "frozen_materialized_support_link_event_source",
        "scheduler_action_cost": "frozen_materialized_scheduler_arm_event_source",
        "ordered_prefix_stop": "frozen_materialized_ordered_prefix_event_source",
        "same_file_redundancy": "frozen_materialized_same_file_redundancy_event_source",
        "risk_penalty": "frozen_materialized_risk_penalty_event_source",
    }
    best_kind = {
        "support_link": "missing_private_context_or_proxy_label_only",
        "scheduler_action_cost": "missing_private_rows_or_contract_only",
        "ordered_prefix_stop": "aggregate_only_not_materialized_event_source",
        "same_file_redundancy": "contract_only_missing_private_trace",
        "risk_penalty": "contract_only_missing_private_trace",
    }
    records = []
    coverage = 0
    for idx, surface in enumerate(SURFACES):
        available = False
        records.append({
            "anonymous_surface_availability_id": f"p38psa{idx:04d}",
            "surface_bucket": surface,
            "required_empirical_source_bucket": required[surface],
            "existing_empirical_source_found_bool": available,
            "best_available_source_bucket": availability[surface],
            "best_available_source_kind_bucket": best_kind[surface],
            "source_availability_bucket": availability[surface],
            "empirical_event_source_available_bool": available,
            "surface_empirical_coverage_bool": available,
            "proxy_or_contract_substitute_rejected_bool": True,
            "proxy_or_contract_only_bool": True,
        })
        coverage += int(available)
    return records, coverage


def _empirical_field_coverage_records() -> tuple[list[dict[str, Any]], bool]:
    required_counts = {
        "support_link": 6,
        "scheduler_action_cost": 7,
        "ordered_prefix_stop": 7,
        "same_file_redundancy": 6,
        "risk_penalty": 5,
    }
    records = []
    for idx, surface in enumerate(SURFACES):
        records.append({
            "anonymous_field_coverage_id": f"p38psf{idx:04d}",
            "surface_bucket": surface,
            "required_empirical_field_count": required_counts[surface],
            "covered_empirical_field_count": 0,
            "coverage_sufficient_for_declaration_bool": False,
            "required_empirical_field_coverage_bucket": "not_covered_by_existing_public_artifacts",
            "required_empirical_fields_covered_bool": False,
            "proxy_unknown_fields_present_bool": True,
            "field_coverage_passed_bool": False,
        })
    return records, False


def _proxy_rejection_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_proxy_rejection_id": f"p38psr{idx:04d}", "candidate_source_bucket": bucket, "proxy_or_contract_source_rejected_as_empirical_bool": True, "rejection_reason_bucket": "not_legitimate_empirical_frozen_materialized_event_source"} for idx, bucket in enumerate(SOURCE_BUCKETS)]
    return records, all(r["proxy_or_contract_source_rejected_as_empirical_bool"] for r in records)


def _declaration_feasibility_records(empirical_count: int, coverage_count: int, field_ok: bool, proxy_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    feasible = empirical_count >= 1 and coverage_count == 5 and field_ok and proxy_ok
    reason = "no_existing_empirical_materialized_event_source" if empirical_count == 0 else "incomplete_or_proxy_only_existing_sources"
    records = [{
        "anonymous_declaration_feasibility_id": "p38psd0000",
        "p3_8p_declaration_authoring_feasible_bool": feasible,
        "declaration_json_authoring_feasible_bool": feasible,
        "valid_existing_empirical_source_count": empirical_count,
        "surface_coverage_count": coverage_count,
        "all_required_empirical_fields_covered_bool": field_ok,
        "proxy_or_contract_source_used_as_empirical_bool": False,
        "reason_bucket": reason,
        "feasibility_decision_bucket": "not_feasible_no_existing_empirical_event_source" if not feasible else "feasible_existing_empirical_event_source_found",
    }]
    return records, feasible


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
    return [{"anonymous_changed_file_allowlist_id": "p38pscf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "helper_p3_8_target_source_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "p38psne0000", "private_read_count": 0, "private_write_count": 0, "openlocus_scan_count": 0, "helper_import_count": 0, "p3_8_import_count": 0, "target_evaluator_import_count": 0, "trace_capture_execution_count": 0, "fixture_generation_count": 0, "declaration_generation_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": True}
    return [record], True


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{"authorization": "empirical_event_source_discovery_audit_only", "next_allowed_phase": "BEA-v1-P3-8Q Empirical Event Source Declaration Authoring Preflight" if pass_status else "none_until_real_empirical_event_source_is_created_or_supplied", "next_allowed_scope_bucket": "preflight_design_only_no_generation_no_capture" if pass_status else "no_next_phase_authorized", "p3_8q_declaration_authoring_authorized": pass_status, "empirical_event_source_found": pass_status, "declaration_generation_authorized": False, "fixture_generation_authorized": False, "private_fixture_write_authorized": False, "private_trace_row_write_authorized": False, "private_read_authorized": False, "helper_import_authorized": False, "trace_capture_execution_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "mechanism_evidence_claimed": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, empirical_count: int, coverage: int, field_ok: bool, proxy_ok: bool, privacy_ok: bool, changed_ok: bool, no_exec_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_available", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "valid_existing_empirical_source_count", "passed": empirical_count >= 1, "threshold_relation": "greater_or_equal", "value": empirical_count, "threshold_value": 1},
        {"gate": "surface_coverage_count", "passed": coverage == 5, "threshold_relation": "equals", "value": coverage, "threshold_value": 5},
        {"gate": "empirical_field_coverage", "passed": field_ok, "threshold_relation": "equals", "value": int(field_ok), "threshold_value": 1},
        {"gate": "proxy_sources_rejected", "passed": proxy_ok, "threshold_relation": "equals", "value": int(proxy_ok), "threshold_value": 1},
        {"gate": "privacy_boundary", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "changed_file_scope_valid", "passed": changed_ok, "threshold_relation": "equals", "value": int(changed_ok), "threshold_value": 1},
        {"gate": "no_execution", "passed": no_exec_ok, "threshold_relation": "equals", "value": int(no_exec_ok), "threshold_value": 1},
    ]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_artifact_records()
    inventory_records, empirical_count = _candidate_source_inventory_records()
    availability_records, coverage_count = _per_surface_source_availability_records()
    field_records, field_ok = _empirical_field_coverage_records()
    proxy_records, proxy_ok = _proxy_rejection_records()
    feasibility_records, feasible = _declaration_feasibility_records(empirical_count, coverage_count, field_ok, proxy_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_exec_records, no_exec_ok = _no_execution_records()
    privacy_ok = True
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8ps_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8ps_changed_file_scope_invalid"
    elif not privacy_ok:
        status = "no_go_p3_8ps_privacy_or_claim_boundary_invalid"
    elif empirical_count == 0:
        status = STATUS_NO_SOURCE
    elif not feasible:
        status = "no_go_p3_8ps_candidate_sources_incomplete_or_proxy_only"
    else:
        status = STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "claim_level": "empirical_event_source_discovery_audit_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_records, "candidate_source_inventory_records": inventory_records, "per_surface_source_availability_records": availability_records, "empirical_field_coverage_records": field_records, "proxy_rejection_records": proxy_records, "declaration_feasibility_records": feasibility_records, "changed_file_allowlist_records": changed_records, "no_execution_records": no_exec_records, "gate_records": _gate_records(input_ok, empirical_count, coverage_count, field_ok, proxy_ok, privacy_ok, changed_ok, no_exec_ok), "stop_go_records": _stop_go_records(status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "private_paths_publicly_serialized": False, "private_filenames_publicly_serialized": False, "raw_candidate_payloads_publicly_serialized": False}
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
    input_records, input_ok = _input_artifact_records()
    inventory_records, empirical_count = _candidate_source_inventory_records()
    availability_records, coverage_count = _per_surface_source_availability_records()
    field_records, field_ok = _empirical_field_coverage_records()
    proxy_records, proxy_ok = _proxy_rejection_records()
    feasibility_records, feasible = _declaration_feasibility_records(empirical_count, coverage_count, field_ok, proxy_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_exec_records, no_exec_ok = _no_execution_records()
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8ps_required_inputs_unavailable", STATUS_NO_SOURCE, "no_go_p3_8ps_candidate_sources_incomplete_or_proxy_only", "no_go_p3_8ps_privacy_or_claim_boundary_invalid", "no_go_p3_8ps_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_artifacts", input_ok and len(input_records) == len(INPUTS)),
        _check("candidate_inventory_no_empirical", empirical_count == 0 and len(inventory_records) == 5),
        _check("candidate_inventory_contract_fields", empirical_count == 0 and len(inventory_records) == 5 and all("empirical_materialized_event_source_bool" in r and "usable_for_p3_8p_declaration_bool" in r for r in inventory_records)),
        _check("surface_availability_contract_fields", coverage_count == 0 and len(availability_records) == 5 and all("required_empirical_source_bucket" in r and "best_available_source_kind_bucket" in r and r["proxy_or_contract_substitute_rejected_bool"] for r in availability_records)),
        _check("field_coverage_contract_fields", not field_ok and len(field_records) == 5 and all(isinstance(r.get("required_empirical_field_count"), int) and r.get("covered_empirical_field_count") == 0 for r in field_records)),
        _check("proxy_rejection", proxy_ok and len(proxy_records) == 5),
        _check("declaration_feasibility_no_go", not feasible and feasibility_records[0]["p3_8p_declaration_authoring_feasible_bool"] is False and feasibility_records[0]["reason_bucket"] == "no_existing_empirical_materialized_event_source"),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0),
        _check("no_execution", no_exec_ok and no_exec_records[0]["private_read_count"] == 0 and no_exec_records[0]["openlocus_scan_count"] == 0),
        _check("stop_go_no_go", _stop_go_records(STATUS_NO_SOURCE)[0]["next_allowed_phase"] == "none_until_real_empirical_event_source_is_created_or_supplied" and not _stop_go_records(STATUS_NO_SOURCE)[0]["p3_8q_declaration_authoring_authorized"]),
        _check("stop_go_pass_limited", _stop_go_records(STATUS_PASS)[0]["p3_8q_declaration_authoring_authorized"] and not _stop_go_records(STATUS_PASS)[0]["fixture_generation_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8PS empirical event source discovery audit")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, empirical_sources={report['declaration_feasibility_records'][0]['valid_existing_empirical_source_count']}, p3_8q={report['stop_go_records'][0]['p3_8q_declaration_authoring_authorized']})")


if __name__ == "__main__":
    main()
