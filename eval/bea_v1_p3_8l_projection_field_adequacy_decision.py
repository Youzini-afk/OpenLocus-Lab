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


SCHEMA_VERSION = "bea_v1_p3_8l_projection_field_adequacy_decision.v1"
PHASE = "BEA-v1-P3-8L"
GENERATED_BY = "bea_v1_p3_8l_projection_field_adequacy_decision"
STATUS_PASS = "proxy_route_closure_empirical_fixtures_required"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8l_required_inputs_unavailable",
    "no_go_p3_8l_proxy_boundary_invalid",
    "no_go_p3_8l_decision_record_incomplete",
    "no_go_p3_8l_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8l_projection_field_adequacy_decision/bea_v1_p3_8l_projection_field_adequacy_decision_report.json")
P3_8K_ARTIFACT = Path("artifacts/bea_v1_p3_8k_proxy_fixture_public_projection_audit/bea_v1_p3_8k_proxy_fixture_public_projection_audit_report.json")

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8l-projection-field-adequacy-decision.md",
    "docs/zh/bea-v1-p3-8l-projection-field-adequacy-decision.md",
    "eval/bea_v1_p3_8l_projection_field_adequacy_decision.py",
    "artifacts/bea_v1_p3_8l_projection_field_adequacy_decision/bea_v1_p3_8l_projection_field_adequacy_decision_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8l_projection_field_adequacy_decision/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py",
    "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py",
    "eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py",
    "eval/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke.py",
    "eval/bea_v1_p3_8k_proxy_fixture_public_projection_audit.py",
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


def _load_input() -> tuple[dict[str, Any], str]:
    return _load_json(P3_8K_ARTIFACT)


def _first_record(artifact: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    records = artifact.get(key, []) if isinstance(artifact.get(key), list) else []
    return records[0] if records and isinstance(records[0], dict) else {}


def _input_artifact_records(artifact: Mapping[str, Any], load: str) -> tuple[list[dict[str, Any]], bool]:
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    shape = _first_record(artifact, "projection_shape_audit_records")
    boundary = _first_record(artifact, "proxy_boundary_audit_records")
    adequacy = _first_record(artifact, "field_adequacy_records")
    stop = _first_record(artifact, "stop_go_records")
    ok = (
        load == "pass"
        and artifact.get("status") == "proxy_fixture_public_projection_audit_pass_p3_8l_authorized"
        and scan == "pass"
        and int(shape.get("projection_count", 0) or 0) == 5
        and int(shape.get("surface_coverage_count", 0) or 0) == 5
        and boundary.get("proxy_boundary_audit_passed_bool") is True
        and adequacy.get("adequacy_decision_bucket") == "shape_valid_proxy_only_not_empirical"
        and adequacy.get("projection_shape_adequate_for_logger_smoke_audit_bool") is True
        and adequacy.get("projection_adequate_for_empirical_trace_claim_bool") is False
        and adequacy.get("projection_adequate_for_denominator_audit_bool") is False
        and adequacy.get("projection_adequate_for_counterfactual_bool") is False
        and stop.get("p3_8l_projection_field_adequacy_decision_authorized") is True
    )
    return [{"anonymous_input_artifact_id": "p38li0000", "input_artifact_bucket": "p3_8k_proxy_fixture_public_projection_audit", "load_status": load, "observed_status": str(artifact.get("status", "") or ""), "expected_status": "proxy_fixture_public_projection_audit_pass_p3_8l_authorized", "forbidden_scan_status": scan, "public_projection_count": int(shape.get("projection_count", 0) or 0), "surface_coverage_count": int(shape.get("surface_coverage_count", 0) or 0), "proxy_boundary_audit_passed_bool": bool(boundary.get("proxy_boundary_audit_passed_bool", False)), "adequacy_decision_bucket": str(adequacy.get("adequacy_decision_bucket", "")), "logger_smoke_adequate_bool": bool(adequacy.get("projection_shape_adequate_for_logger_smoke_audit_bool", False)), "empirical_trace_adequate_bool": bool(adequacy.get("projection_adequate_for_empirical_trace_claim_bool", True)), "denominator_audit_adequate_bool": bool(adequacy.get("projection_adequate_for_denominator_audit_bool", True)), "counterfactual_adequate_bool": bool(adequacy.get("projection_adequate_for_counterfactual_bool", True)), "p3_8l_authorized_bool": bool(stop.get("p3_8l_projection_field_adequacy_decision_authorized", False)), "input_gate_passed_bool": ok}], ok


def _proxy_route_decision_records(input_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_proxy_route_decision_id": "p38lrd0000", "decision_bucket": "proxy_route_closed_for_mechanism_work", "proxy_projection_shape_valid_bool": input_ok, "proxy_projection_empirical_bool": False, "proxy_projection_adequate_for_logger_smoke_bool": input_ok, "proxy_projection_adequate_for_empirical_trace_claim_bool": False, "proxy_projection_adequate_for_denominator_audit_bool": False, "proxy_projection_adequate_for_counterfactual_bool": False, "proxy_route_closure_reason_bucket": "shape_valid_proxy_only_not_empirical", "proxy_route_decision_complete_bool": input_ok}
    ok = record["proxy_route_decision_complete_bool"] and record["decision_bucket"] == "proxy_route_closed_for_mechanism_work" and not record["proxy_projection_empirical_bool"] and not record["proxy_projection_adequate_for_empirical_trace_claim_bool"] and not record["proxy_projection_adequate_for_denominator_audit_bool"] and not record["proxy_projection_adequate_for_counterfactual_bool"]
    return [record], ok


def _empirical_fixture_requirement_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_empirical_fixture_requirement_id": "p38lefr0000", "empirical_fixture_required_bool": True, "required_next_input_bucket": "true_empirical_frozen_materialized_event_fixtures", "proxy_fixtures_sufficient_bool": False, "committed_aggregate_proxy_sufficient_bool": False, "contract_template_sufficient_bool": False, "private_trace_capture_required_before_mechanism_work_bool": True, "requirement_record_complete_bool": True}
    ok = record["empirical_fixture_required_bool"] and not record["proxy_fixtures_sufficient_bool"] and not record["committed_aggregate_proxy_sufficient_bool"] and not record["contract_template_sufficient_bool"] and record["private_trace_capture_required_before_mechanism_work_bool"]
    return [record], ok


def _closed_authorization_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_closed_authorization_id": "p38lca0000", "denominator_audit_authorized_bool": False, "counterfactual_authorized_bool": False, "mechanism_evidence_claimed_bool": False, "empirical_trace_capture_authorized_bool": False, "private_trace_row_write_authorized_bool": False, "proxy_route_further_smoke_authorized_bool": False, "closed_authorization_record_complete_bool": True}
    ok = all(value is False for key, value in record.items() if key.endswith("_bool") and key != "closed_authorization_record_complete_bool") and record["closed_authorization_record_complete_bool"]
    return [record], ok


def _next_experiment_design_records(pass_status: bool) -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_next_experiment_design_id": "p38lnx0000", "next_allowed_phase": "BEA-v1-P3-8M Empirical Frozen Event Fixture Acquisition Design — design only, no capture execution", "next_allowed_scope_bucket": "design_only_no_capture_execution", "empirical_fixture_acquisition_design_authorized_bool": pass_status, "capture_execution_authorized_in_next_phase_bool": False, "private_write_authorized_in_next_phase_bool": False, "next_experiment_design_record_complete_bool": pass_status}
    ok = record["next_experiment_design_record_complete_bool"] and record["empirical_fixture_acquisition_design_authorized_bool"] and not record["capture_execution_authorized_in_next_phase_bool"] and not record["private_write_authorized_in_next_phase_bool"]
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
    return [{"anonymous_changed_file_allowlist_id": "p38lcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "p3_8k_p3_8j_helper_p3_8_target_source_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "p38lne0000", "private_read_count": 0, "private_write_count": 0, "helper_import_count": 0, "p3_8_import_count": 0, "target_evaluator_import_count": 0, "trace_capture_execution_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": True}
    return [record], True


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "projection_field_adequacy_decision_only", "next_allowed_phase": "BEA-v1-P3-8M Empirical Frozen Event Fixture Acquisition Design — design only, no capture execution", "next_allowed_scope_bucket": "design_only_no_capture_execution", "proxy_route_closed_for_mechanism_work": pass_status, "proxy_fixture_smoke_route_authorized": False, "p3_8m_empirical_fixture_acquisition_design_authorized": pass_status, "private_fixture_read_authorized": False, "private_fixture_write_authorized": False, "helper_import_authorized": False, "empirical_trace_capture_authorized": False, "private_trace_row_write_authorized": False, "p3_8_code_change_authorized": False, "p3_8_capture_execution_authorized": False, "target_evaluator_import_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "mechanism_evidence_claimed": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, boundary_ok: bool, decision_ok: bool, changed_ok: bool, no_exec_ok: bool) -> list[dict[str, Any]]:
    gates = (("p3_8k_input_pass", input_ok, int(input_ok), 1), ("proxy_boundary_valid", boundary_ok, int(boundary_ok), 1), ("decision_records_complete", decision_ok, int(decision_ok), 1), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("no_execution", no_exec_ok, int(no_exec_ok), 1), ("forbidden_execution_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifact, load = _load_input()
    input_records, input_ok = _input_artifact_records(artifact, load)
    route_records, route_ok = _proxy_route_decision_records(input_ok)
    requirement_records, requirement_ok = _empirical_fixture_requirement_records()
    closed_records, closed_ok = _closed_authorization_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    decision_ok = route_ok and requirement_ok and closed_ok
    next_records, next_ok = _next_experiment_design_records(decision_ok)
    decision_ok = decision_ok and next_ok
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8l_required_inputs_unavailable"
    elif not route_ok:
        status = "no_go_p3_8l_proxy_boundary_invalid"
    elif not decision_ok:
        status = "no_go_p3_8l_decision_record_incomplete"
    elif not changed_ok:
        status = "no_go_p3_8l_changed_file_scope_invalid"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    if not pass_status:
        next_records, _ = _next_experiment_design_records(False)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "projection_field_adequacy_decision_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "proxy_route_decision_records": route_records,
        "empirical_fixture_requirement_records": requirement_records,
        "closed_authorization_records": closed_records,
        "next_experiment_design_records": next_records,
        "changed_file_allowlist_records": changed_records,
        "no_execution_records": no_execution_records,
        "gate_records": _gate_records(input_ok, route_ok, decision_ok, changed_ok, no_exec_ok),
        "stop_go_records": _stop_go_records(pass_status),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "private_paths_publicly_serialized": False,
        "private_filenames_publicly_serialized": False,
        "raw_projection_payloads_publicly_serialized": False,
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
    route_records, route_ok = _proxy_route_decision_records(input_ok)
    requirement_records, requirement_ok = _empirical_fixture_requirement_records()
    closed_records, closed_ok = _closed_authorization_records()
    next_records, next_ok = _next_experiment_design_records(True)
    no_execution_records, no_exec_ok = _no_execution_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    stop_go = _stop_go_records(True)[0]
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8l_required_inputs_unavailable", "no_go_p3_8l_proxy_boundary_invalid", "no_go_p3_8l_decision_record_incomplete", "no_go_p3_8l_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_gate", input_ok and input_records[0]["public_projection_count"] == 5),
        _check("proxy_route_decision", route_ok and route_records[0]["decision_bucket"] == "proxy_route_closed_for_mechanism_work"),
        _check("empirical_fixture_requirement", requirement_ok and requirement_records[0]["empirical_fixture_required_bool"]),
        _check("closure_authorizations", closed_ok and not closed_records[0]["mechanism_evidence_claimed_bool"] and not closed_records[0]["empirical_trace_capture_authorized_bool"] and not closed_records[0]["proxy_route_further_smoke_authorized_bool"]),
        _check("next_experiment_design", next_ok and next_records[0]["next_allowed_scope_bucket"] == "design_only_no_capture_execution"),
        _check("no_execution", no_exec_ok and no_execution_records[0]["private_read_count"] == 0 and no_execution_records[0]["helper_import_count"] == 0),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0),
        _check("stop_go", stop_go["proxy_route_closed_for_mechanism_work"] and stop_go["p3_8m_empirical_fixture_acquisition_design_authorized"] and not stop_go["empirical_trace_capture_authorized"] and not stop_go["private_fixture_write_authorized"] and not stop_go["p3_8_code_change_authorized"] and not stop_go["target_evaluator_import_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8L projection field adequacy decision")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, proxy_closed={report['stop_go_records'][0]['proxy_route_closed_for_mechanism_work']}, p3_8m={report['stop_go_records'][0]['p3_8m_empirical_fixture_acquisition_design_authorized']})")


if __name__ == "__main__":
    main()
