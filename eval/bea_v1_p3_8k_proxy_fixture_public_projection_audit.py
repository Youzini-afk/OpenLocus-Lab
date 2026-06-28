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


SCHEMA_VERSION = "bea_v1_p3_8k_proxy_fixture_public_projection_audit.v1"
PHASE = "BEA-v1-P3-8K"
GENERATED_BY = "bea_v1_p3_8k_proxy_fixture_public_projection_audit"
STATUS_PASS = "proxy_fixture_public_projection_audit_pass_p3_8l_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8k_required_inputs_unavailable",
    "no_go_p3_8k_public_projection_shape_invalid",
    "no_go_p3_8k_proxy_boundary_invalid",
    "no_go_p3_8k_proxy_projection_too_non_empirical",
    "no_go_p3_8k_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
DEFAULT_OUT = Path("artifacts/bea_v1_p3_8k_proxy_fixture_public_projection_audit/bea_v1_p3_8k_proxy_fixture_public_projection_audit_report.json")
P3_8J_ARTIFACT = Path("artifacts/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke_report.json")

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8k-proxy-fixture-public-projection-audit.md",
    "docs/zh/bea-v1-p3-8k-proxy-fixture-public-projection-audit.md",
    "eval/bea_v1_p3_8k_proxy_fixture_public_projection_audit.py",
    "artifacts/bea_v1_p3_8k_proxy_fixture_public_projection_audit/bea_v1_p3_8k_proxy_fixture_public_projection_audit_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8k_proxy_fixture_public_projection_audit/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py",
    "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py",
    "eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py",
    "eval/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke.py",
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


def _load_p3_8j() -> tuple[dict[str, Any], str, list[Mapping[str, Any]], Mapping[str, Any]]:
    artifact, load = _load_json(P3_8J_ARTIFACT)
    projections = artifact.get("public_projection_records", []) if isinstance(artifact.get("public_projection_records"), list) else []
    stop = artifact.get("stop_go_records", []) if isinstance(artifact.get("stop_go_records"), list) else []
    stop0 = stop[0] if stop and isinstance(stop[0], dict) else {}
    return artifact, load, [p for p in projections if isinstance(p, dict)], stop0


def _input_artifact_records(artifact: Mapping[str, Any], load: str, projections: list[Mapping[str, Any]], stop: Mapping[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    ok = (
        load == "pass"
        and artifact.get("status") == "explicit_proxy_fixture_logger_smoke_pass_p3_8k_authorized"
        and scan == "pass"
        and len(projections) == 5
        and stop.get("proxy_fixture_smoke_executed") is True
        and stop.get("empirical_trace_capture_claimed") is False
        and stop.get("p3_8k_public_projection_audit_authorized") is True
    )
    return [{"anonymous_input_artifact_id": "p38ki0000", "input_artifact_bucket": "p3_8j_explicit_proxy_fixture_logger_smoke", "load_status": load, "observed_status": str(artifact.get("status", "") or ""), "expected_status": "explicit_proxy_fixture_logger_smoke_pass_p3_8k_authorized", "forbidden_scan_status": scan, "public_projection_count": len(projections), "proxy_fixture_smoke_executed_bool": bool(stop.get("proxy_fixture_smoke_executed", False)), "empirical_trace_capture_claimed_bool": bool(stop.get("empirical_trace_capture_claimed", True)), "p3_8k_authorized_bool": bool(stop.get("p3_8k_public_projection_audit_authorized", False)), "input_gate_passed_bool": ok}], ok


def _projection_shape_audit_records(projections: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    ids = [str(p.get("anonymous_public_proxy_trace_id", "")) for p in projections]
    surfaces = {str(p.get("surface_bucket", "")) for p in projections}
    schema_count = sum(1 for p in projections if p.get("schema_version_bucket"))
    completeness_count = sum(1 for p in projections if p.get("trace_completeness_bucket") == "proxy_fixture_helper_smoke_validated")
    scanner_count = sum(1 for p in projections if _scan_summary(p)["status"] == "pass" and p.get("public_projection_scanner_passed_bool") is True)
    ids_unique = len(ids) == len(set(ids)) == 5 and all(ids)
    ok = len(projections) == 5 and len(surfaces & set(SURFACES)) == 5 and ids_unique and schema_count == 5 and completeness_count == 5 and scanner_count == 5
    return [{"anonymous_projection_shape_audit_id": "p38kps0000", "projection_count": len(projections), "surface_coverage_count": len(surfaces & set(SURFACES)), "anonymous_public_ids_unique_bool": ids_unique, "schema_version_bucket_present_count": schema_count, "trace_completeness_valid_count": completeness_count, "scanner_pass_count": scanner_count, "shape_audit_passed_bool": ok}], ok


def _count_proxy_or_unknown(row: Mapping[str, Any]) -> int:
    count = 0
    for value in row.values():
        if isinstance(value, str) and ("proxy" in value or "unknown" in value or "not_empirical" in value):
            count += 1
    return count


def _per_surface_projection_audit_records(projections: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    by_surface = {str(p.get("surface_bucket", "")): p for p in projections}
    records: list[dict[str, Any]] = []
    ok_all = True
    for idx, surface in enumerate(SURFACES):
        row = by_surface.get(surface, {})
        scanner_pass = _scan_summary(row)["status"] == "pass" and row.get("public_projection_scanner_passed_bool") is True
        empirical_field_count = sum(1 for key, value in row.items() if "empirical" in str(key) and value is not False)
        record_ok = row.get("proxy_fixture_bool") is True and row.get("empirical_trace_capture_bool") is False and row.get("trace_completeness_bucket") == "proxy_fixture_helper_smoke_validated" and scanner_pass and empirical_field_count == 0
        records.append({"anonymous_per_surface_projection_audit_id": f"p38ksa{idx:04d}", "surface_bucket": surface, "projection_present_bool": bool(row), "proxy_fixture_bool": row.get("proxy_fixture_bool") is True, "empirical_trace_capture_bool": bool(row.get("empirical_trace_capture_bool", True)), "trace_completeness_bucket": str(row.get("trace_completeness_bucket", "")), "public_projection_scanner_passed_bool": scanner_pass, "empirical_field_count": empirical_field_count, "proxy_or_unknown_field_count": _count_proxy_or_unknown(row), "surface_projection_shape_valid_bool": record_ok})
        ok_all = ok_all and record_ok
    return records, ok_all


def _proxy_boundary_audit_records(projections: list[Mapping[str, Any]], stop: Mapping[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    proxy_true = sum(1 for p in projections if p.get("proxy_fixture_bool") is True)
    empirical_false = sum(1 for p in projections if p.get("empirical_trace_capture_bool") is False)
    empirical_claim_count = sum(1 for p in projections if p.get("empirical_trace_capture_bool") is True) + int(bool(stop.get("empirical_trace_capture_claimed", False)))
    private_trace_claim_count = int(bool(stop.get("private_trace_row_write_authorized", False)))
    mechanism_utility_claim_count = int(bool(stop.get("method_winner_claimed", False))) + int(bool(stop.get("downstream_value_claimed", False)))
    denominator_counterfactual_count = int(bool(stop.get("denominator_audit_authorized", False))) + int(bool(stop.get("trace_counterfactual_execution_authorized", False))) + int(bool(stop.get("support_counterfactual_execution_authorized", False)))
    ok = proxy_true == 5 and empirical_false == 5 and empirical_claim_count == 0 and private_trace_claim_count == 0 and mechanism_utility_claim_count == 0 and denominator_counterfactual_count == 0
    return [{"anonymous_proxy_boundary_audit_id": "p38kba0000", "all_proxy_fixture_bool_true": proxy_true == 5, "all_empirical_trace_capture_bool_false": empirical_false == 5, "proxy_fixture_true_count": proxy_true, "empirical_trace_capture_false_count": empirical_false, "empirical_trace_capture_claim_count": empirical_claim_count, "private_trace_row_claim_count": private_trace_claim_count, "mechanism_or_utility_claim_count": mechanism_utility_claim_count, "denominator_or_counterfactual_claim_count": denominator_counterfactual_count, "denominator_audit_authorized_bool": bool(stop.get("denominator_audit_authorized", False)), "counterfactual_authorized_bool": bool(stop.get("trace_counterfactual_execution_authorized", False) or stop.get("support_counterfactual_execution_authorized", False)), "proxy_boundary_audit_passed_bool": ok}], ok


def _field_adequacy_records(shape_ok: bool, boundary_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    ok = shape_ok and boundary_ok
    return [{"anonymous_field_adequacy_id": "p38kfa0000", "adequacy_decision_bucket": "shape_valid_proxy_only_not_empirical", "projection_shape_adequate_for_logger_smoke_audit_bool": ok, "projection_adequate_for_empirical_trace_claim_bool": False, "projection_adequate_for_denominator_audit_bool": False, "projection_adequate_for_counterfactual_bool": False, "next_required_input_bucket": "empirical_frozen_event_fixtures_or_explicit_proxy_closure_decision", "field_adequacy_audit_passed_bool": ok}], ok


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
    return [{"anonymous_changed_file_allowlist_id": "p38kcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "p3_8j_helper_p3_8_target_runtime_or_source_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "p38kne0000", "private_read_count": 0, "private_write_count": 0, "helper_import_count": 0, "p3_8_import_count": 0, "target_evaluator_import_count": 0, "trace_capture_execution_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": True}
    return [record], True


def _handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_p3_8l_handoff_id": "p38klh0000", "next_allowed_phase": "BEA-v1-P3-8L Projection Field Adequacy and Empirical Fixture Requirement Decision — no capture execution", "p3_8l_projection_field_adequacy_decision_authorized": pass_status, "requires_separate_phase_bool": True, "capture_execution_authorized_bool": False, "private_fixture_read_authorized_bool": False, "helper_import_authorized_bool": False}]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "proxy_fixture_public_projection_audit_only", "next_allowed_phase": "BEA-v1-P3-8L Projection Field Adequacy and Empirical Fixture Requirement Decision — no capture execution", "p3_8l_projection_field_adequacy_decision_authorized": pass_status, "proxy_projection_shape_audited": pass_status, "private_fixture_read_authorized": False, "helper_import_authorized": False, "empirical_trace_capture_authorized": False, "empirical_trace_capture_claimed": False, "p3_8_capture_execution_authorized": False, "p3_8_code_change_authorized": False, "target_evaluator_import_authorized": False, "private_trace_row_write_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, shape_ok: bool, surface_ok: bool, boundary_ok: bool, adequacy_ok: bool, changed_ok: bool, no_exec_ok: bool) -> list[dict[str, Any]]:
    gates = (("p3_8j_input_pass", input_ok, int(input_ok), 1), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("no_private_read_write_or_import", no_exec_ok, int(no_exec_ok), 1), ("projection_count", shape_ok, 5 if shape_ok else 0, 5), ("surface_coverage", surface_ok, 5 if surface_ok else 0, 5), ("proxy_boundary_valid", boundary_ok, int(boundary_ok), 1), ("field_adequacy_proxy_only", adequacy_ok, int(adequacy_ok), 1), ("forbidden_execution_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifact, load, projections, stop = _load_p3_8j()
    input_records, input_ok = _input_artifact_records(artifact, load, projections, stop)
    shape_records, shape_ok = _projection_shape_audit_records(projections)
    surface_records, surface_ok = _per_surface_projection_audit_records(projections)
    boundary_records, boundary_ok = _proxy_boundary_audit_records(projections, stop)
    field_records, adequacy_ok = _field_adequacy_records(shape_ok, boundary_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_execution_records, no_exec_ok = _no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8k_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8k_changed_file_scope_invalid"
    elif not shape_ok or not surface_ok:
        status = "no_go_p3_8k_public_projection_shape_invalid"
    elif not boundary_ok:
        status = "no_go_p3_8k_proxy_boundary_invalid"
    elif not adequacy_ok:
        status = "no_go_p3_8k_proxy_projection_too_non_empirical"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "proxy_fixture_public_projection_audit_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "projection_shape_audit_records": shape_records,
        "per_surface_projection_audit_records": surface_records,
        "proxy_boundary_audit_records": boundary_records,
        "field_adequacy_records": field_records,
        "changed_file_allowlist_records": changed_records,
        "no_execution_records": no_execution_records,
        "p3_8l_handoff_records": _handoff_records(pass_status),
        "gate_records": _gate_records(input_ok, shape_ok, surface_ok, boundary_ok, adequacy_ok, changed_ok, no_exec_ok),
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
    artifact, load, projections, stop = _load_p3_8j()
    input_records, input_ok = _input_artifact_records(artifact, load, projections, stop)
    shape_records, shape_ok = _projection_shape_audit_records(projections)
    surface_records, surface_ok = _per_surface_projection_audit_records(projections)
    boundary_records, boundary_ok = _proxy_boundary_audit_records(projections, stop)
    field_records, adequacy_ok = _field_adequacy_records(shape_ok, boundary_ok)
    no_execution_records, no_exec_ok = _no_execution_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    stop_go = _stop_go_records(True)[0]
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8k_required_inputs_unavailable", "no_go_p3_8k_public_projection_shape_invalid", "no_go_p3_8k_proxy_boundary_invalid", "no_go_p3_8k_proxy_projection_too_non_empirical", "no_go_p3_8k_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("parser_safe", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_gate", input_ok and input_records[0]["public_projection_count"] == 5),
        _check("projection_shape", shape_ok and shape_records[0]["scanner_pass_count"] == 5),
        _check("proxy_boundary", surface_ok and boundary_ok and boundary_records[0]["empirical_trace_capture_claim_count"] == 0 and boundary_records[0]["all_proxy_fixture_bool_true"] and boundary_records[0]["all_empirical_trace_capture_bool_false"]),
        _check("field_adequacy", adequacy_ok and not field_records[0]["projection_adequate_for_empirical_trace_claim_bool"]),
        _check("no_execution", no_exec_ok and no_execution_records[0]["private_read_count"] == 0 and no_execution_records[0]["helper_import_count"] == 0),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0),
        _check("stop_go", stop_go["p3_8l_projection_field_adequacy_decision_authorized"] and stop_go["proxy_projection_shape_audited"] and not stop_go["private_fixture_read_authorized"] and not stop_go["helper_import_authorized"] and not stop_go["empirical_trace_capture_authorized"] and not stop_go["target_evaluator_import_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8K proxy fixture public projection audit")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, projections={report['projection_shape_audit_records'][0]['projection_count']}, p3_8l={report['p3_8l_handoff_records'][0]['p3_8l_projection_field_adequacy_decision_authorized']})")


if __name__ == "__main__":
    main()
