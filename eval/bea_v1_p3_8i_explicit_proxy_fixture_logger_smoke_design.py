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


SCHEMA_VERSION = "bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.v1"
GENERATED_BY = "eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py"
PHASE = "BEA-v1-P3-8I"
STATUS_PASS = "explicit_proxy_fixture_logger_smoke_design_pass_p3_8j_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8i_required_inputs_unavailable",
    "no_go_p3_8i_proxy_mode_design_incomplete",
    "no_go_p3_8i_boundary_or_default_mode_incomplete",
    "no_go_p3_8i_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design_report.json")
P3_8H_ARTIFACT = Path("artifacts/bea_v1_p3_8h_proxy_fixture_compatibility_preflight/bea_v1_p3_8h_proxy_fixture_compatibility_preflight_report.json")
P3_8G_ARTIFACT = Path("artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke_report.json")
SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8i-explicit-proxy-fixture-logger-smoke-design.md",
    "docs/zh/bea-v1-p3-8i-explicit-proxy-fixture-logger-smoke-design.md",
    "eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py",
    "artifacts/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py",
    "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = ("src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/", ".openlocus/research-private/")
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_out_dir", "private_filename", "private_filenames",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list",
    "provider", "prompt", "response", "payload", "raw_payload", "hash", "hashes", "private_id", "queue_item_id",
    "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "diff", "raw_diff",
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


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok_all = True

    p3_8h, h_load = _load_json(P3_8H_ARTIFACT)
    h_scan = str(p3_8h.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p3_8h.get("forbidden_scan"), dict) else "not_reported")
    h_stop = p3_8h.get("stop_go_records", []) if isinstance(p3_8h.get("stop_go_records"), list) else []
    h_stop0 = h_stop[0] if h_stop and isinstance(h_stop[0], dict) else {}
    h_ok = (
        h_load == "pass"
        and p3_8h.get("status") == "proxy_fixture_compatibility_preflight_pass_p3_8i_authorized"
        and h_scan == "pass"
        and h_stop0.get("p3_8i_explicit_proxy_fixture_logger_smoke_design_authorized") is True
        and h_stop0.get("p3_8_code_change_authorized") is False
        and h_stop0.get("p3_8_capture_execution_authorized") is False
        and h_stop0.get("private_trace_row_write_authorized") is False
        and h_stop0.get("proxy_mode_accepted_for_logger_smoke_only") is True
    )
    ok_all = ok_all and h_ok
    records.append({"anonymous_input_artifact_id": "p38ii0000", "input_artifact_bucket": "p3_8h_proxy_fixture_compatibility_preflight", "load_status": h_load, "observed_status": str(p3_8h.get("status", "") or ""), "expected_status": "proxy_fixture_compatibility_preflight_pass_p3_8i_authorized", "forbidden_scan_status": h_scan, "p3_8i_authorized_bool": bool(h_stop0.get("p3_8i_explicit_proxy_fixture_logger_smoke_design_authorized", False)), "p3_8_code_change_authorized_bool": bool(h_stop0.get("p3_8_code_change_authorized", True)), "p3_8_capture_execution_authorized_bool": bool(h_stop0.get("p3_8_capture_execution_authorized", True)), "private_trace_row_write_authorized_bool": bool(h_stop0.get("private_trace_row_write_authorized", True)), "proxy_mode_accepted_for_logger_smoke_only_bool": bool(h_stop0.get("proxy_mode_accepted_for_logger_smoke_only", False)), "input_gate_passed_bool": h_ok})

    p3_8g, g_load = _load_json(P3_8G_ARTIFACT)
    g_scan = str(p3_8g.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p3_8g.get("forbidden_scan"), dict) else "not_reported")
    g_writes = p3_8g.get("private_write_summary_records", []) if isinstance(p3_8g.get("private_write_summary_records"), list) else []
    g_write0 = g_writes[0] if g_writes and isinstance(g_writes[0], dict) else {}
    g_events = p3_8g.get("proxy_fixture_event_summary_records", []) if isinstance(p3_8g.get("proxy_fixture_event_summary_records"), list) else []
    g_event0 = g_events[0] if g_events and isinstance(g_events[0], dict) else {}
    g_stop = p3_8g.get("stop_go_records", []) if isinstance(p3_8g.get("stop_go_records"), list) else []
    g_stop0 = g_stop[0] if g_stop and isinstance(g_stop[0], dict) else {}
    g_ok = (
        g_load == "pass"
        and p3_8g.get("status") == "frozen_event_proxy_fixture_materialization_smoke_pass_p3_8h_authorized"
        and g_scan == "pass"
        and int(g_write0.get("private_files_written_count", 0) or 0) == 2
        and int(g_event0.get("event_count", 0) or 0) == 5
        and g_stop0.get("empirical_trace_fixture_claimed") is False
    )
    ok_all = ok_all and g_ok
    records.append({"anonymous_input_artifact_id": "p38ii0001", "input_artifact_bucket": "p3_8g_proxy_fixture_materialization_smoke", "load_status": g_load, "observed_status": str(p3_8g.get("status", "") or ""), "expected_status": "frozen_event_proxy_fixture_materialization_smoke_pass_p3_8h_authorized", "forbidden_scan_status": g_scan, "private_proxy_files_written_count": int(g_write0.get("private_files_written_count", 0) or 0), "proxy_event_count": int(g_event0.get("event_count", 0) or 0), "empirical_trace_fixture_claimed_bool": bool(g_stop0.get("empirical_trace_fixture_claimed", True)), "input_gate_passed_bool": g_ok})
    return records, ok_all


def _proxy_mode_design_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{
        "anonymous_proxy_mode_design_id": "p38ipm0000",
        "proxy_mode_name_bucket": "explicit_proxy_fixture_logger_smoke_mode",
        "separate_evaluator_required_bool": True,
        "p3_8_empirical_mode_unchanged_bool": True,
        "proxy_mode_default_enabled_bool": False,
        "explicit_proxy_mode_argument_required_bool": True,
        "proxy_fixtures_required_bool": True,
        "capture_scope_bucket": "proxy_fixture_logger_smoke_only",
        "empirical_trace_capture_claimed_bool": False,
        "proxy_mode_design_complete_bool": True,
    }]
    ok = all(r["proxy_mode_design_complete_bool"] and r["proxy_mode_name_bucket"] == "explicit_proxy_fixture_logger_smoke_mode" and r["separate_evaluator_required_bool"] and not r["proxy_mode_default_enabled_bool"] and r["explicit_proxy_mode_argument_required_bool"] and not r["empirical_trace_capture_claimed_bool"] for r in records)
    return records, ok


def _proxy_fixture_input_contract_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_proxy_fixture_input_contract_id": "p38ific0000", "proxy_manifest_bucket": "p3_8g_proxy_fixture_manifest_private", "proxy_events_bucket": "p3_8g_proxy_fixture_events_private", "required_proxy_event_count": 5, "required_surface_coverage_count": 5, "raw_fixture_payloads_publicly_serialized_bool": False, "private_filenames_publicly_serialized_bool": False, "private_paths_publicly_serialized_bool": False, "input_contract_complete_bool": True}]
    return records, all(r["input_contract_complete_bool"] for r in records)


def _helper_capture_plan_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    for idx, surface in enumerate(SURFACES):
        records.append({"anonymous_helper_capture_plan_id": f"p38ihp{idx:04d}", "surface_bucket": surface, "helper_capture_mode_bucket": "helper_only_proxy_fixture_capture", "target_evaluator_import_authorized_bool": False, "p3_8_import_authorized_bool": False, "helper_module_import_authorized_in_p3_8j_bool": True, "private_trace_row_write_authorized_in_p3_8i_bool": False, "private_trace_row_write_authorized_in_p3_8j_bool": False, "public_projection_only_in_p3_8j_bool": True, "helper_capture_plan_complete_bool": True})
    ok = all(r["helper_capture_plan_complete_bool"] and not r["target_evaluator_import_authorized_bool"] and not r["p3_8_import_authorized_bool"] and r["helper_module_import_authorized_in_p3_8j_bool"] and not r["private_trace_row_write_authorized_in_p3_8i_bool"] and not r["private_trace_row_write_authorized_in_p3_8j_bool"] for r in records)
    return records, ok


def _public_projection_plan_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_public_projection_plan_id": "p38ipp0000", "projection_scope_bucket": "sanitized_public_summary_only", "public_projection_only_in_p3_8j_bool": True, "private_paths_publicly_serialized_bool": False, "raw_fixture_payloads_publicly_serialized_bool": False, "queue_or_design_ids_publicly_serialized_bool": False, "public_scanner_required_bool": True, "public_projection_plan_complete_bool": True}]
    return records, all(r["public_projection_plan_complete_bool"] for r in records)


def _default_mode_isolation_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_default_mode_isolation_id": "p38idmi0000", "p3_8_empirical_mode_change_authorized_bool": False, "p3_8_code_change_authorized_bool": False, "runtime_default_change_authorized_bool": False, "proxy_mode_requires_separate_evaluator_bool": True, "default_mode_isolation_complete_bool": True}]
    return records, all(r["default_mode_isolation_complete_bool"] and not r["p3_8_empirical_mode_change_authorized_bool"] and not r["p3_8_code_change_authorized_bool"] and not r["runtime_default_change_authorized_bool"] and r["proxy_mode_requires_separate_evaluator_bool"] for r in records)


def _execution_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_execution_boundary_id": "p38ieb0000", "private_file_read_count_in_p3_8i": 0, "private_file_write_count_in_p3_8i": 0, "trace_capture_execution_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "p5_or_v1_a_execution_count": 0, "execution_boundary_complete_bool": True}]
    return records, all(r["execution_boundary_complete_bool"] and all(r[k] == 0 for k in r if k.endswith("_count") or k.endswith("_count_in_p3_8i")) for r in records)


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
    return [{"anonymous_changed_file_allowlist_id": "p38icf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "p3_8_p3_8g_p3_8h_helper_target_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_p3_8j_handoff_id": "p38ijh0000", "next_allowed_phase": "BEA-v1-P3-8J Explicit Proxy Fixture Logger Smoke Evaluator Implementation — separate evaluator only, no empirical capture", "p3_8j_proxy_smoke_evaluator_authorized": pass_status, "separate_evaluator_only_bool": True, "p3_8_modification_authorized_bool": False, "empirical_capture_authorized_bool": False, "private_trace_row_write_authorized_bool": False}]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "explicit_proxy_fixture_logger_smoke_design_only", "next_allowed_phase": "BEA-v1-P3-8J Explicit Proxy Fixture Logger Smoke Evaluator Implementation — separate evaluator only, no empirical capture", "p3_8j_proxy_smoke_evaluator_authorized": pass_status, "p3_8_code_change_authorized": False, "p3_8_capture_execution_authorized": False, "empirical_trace_capture_authorized": False, "private_trace_row_write_authorized": False, "target_evaluator_import_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, design_ok: bool, boundary_ok: bool, changed_ok: bool) -> list[dict[str, Any]]:
    gates = (("required_inputs_available", input_ok, int(input_ok), 1), ("proxy_mode_design_complete", design_ok, int(design_ok), 1), ("boundary_and_default_mode_complete", boundary_ok, int(boundary_ok), 1), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("forbidden_execution_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_artifact_records()
    design_records, design_ok = _proxy_mode_design_records()
    input_contract_records, input_contract_ok = _proxy_fixture_input_contract_records()
    helper_records, helper_ok = _helper_capture_plan_records()
    projection_records, projection_ok = _public_projection_plan_records()
    default_records, default_ok = _default_mode_isolation_records()
    execution_records, execution_ok = _execution_boundary_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    boundary_ok = input_contract_ok and helper_ok and projection_ok and default_ok and execution_ok
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8i_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8i_changed_file_scope_invalid"
    elif not design_ok:
        status = "no_go_p3_8i_proxy_mode_design_incomplete"
    elif not boundary_ok:
        status = "no_go_p3_8i_boundary_or_default_mode_incomplete"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "explicit_proxy_fixture_logger_smoke_design_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "proxy_mode_design_records": design_records,
        "proxy_fixture_input_contract_records": input_contract_records,
        "helper_capture_plan_records": helper_records,
        "public_projection_plan_records": projection_records,
        "default_mode_isolation_records": default_records,
        "execution_boundary_records": execution_records,
        "changed_file_allowlist_records": changed_records,
        "p3_8j_handoff_records": _handoff_records(pass_status),
        "gate_records": _gate_records(input_ok, design_ok, boundary_ok, changed_ok),
        "stop_go_records": _stop_go_records(pass_status),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "private_paths_publicly_serialized": False,
        "private_filenames_publicly_serialized": False,
        "raw_fixture_payloads_publicly_serialized": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
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
    design_records, design_ok = _proxy_mode_design_records()
    input_contract_records, input_contract_ok = _proxy_fixture_input_contract_records()
    helper_records, helper_ok = _helper_capture_plan_records()
    projection_records, projection_ok = _public_projection_plan_records()
    default_records, default_ok = _default_mode_isolation_records()
    execution_records, execution_ok = _execution_boundary_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    stop = _stop_go_records(True)[0]
    checks = [
        _check("status_vocab_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8i_required_inputs_unavailable", "no_go_p3_8i_proxy_mode_design_incomplete", "no_go_p3_8i_boundary_or_default_mode_incomplete", "no_go_p3_8i_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("input_gates", input_ok and len(input_records) == 2),
        _check("record_completeness", design_ok and input_contract_ok and helper_ok and projection_ok and len(helper_records) == 5),
        _check("boundary", default_ok and execution_ok and not default_records[0]["p3_8_code_change_authorized_bool"] and execution_records[0]["private_file_read_count_in_p3_8i"] == 0),
        _check("allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0 and not changed_records[0]["p3_8_p3_8g_p3_8h_helper_target_or_runtime_modified_bool"]),
        _check("no_private_writes", execution_records[0]["private_file_write_count_in_p3_8i"] == 0),
        _check("parser_safety", _parser_hides_unknown()),
        _check("scanner", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("stop_go", stop["p3_8j_proxy_smoke_evaluator_authorized"] and not stop["p3_8_code_change_authorized"] and not stop["private_trace_row_write_authorized"] and not stop["empirical_trace_capture_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8I explicit proxy fixture logger smoke design")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, helper_plans={len(report['helper_capture_plan_records'])}, p3_8j={report['p3_8j_handoff_records'][0]['p3_8j_proxy_smoke_evaluator_authorized']})")


if __name__ == "__main__":
    main()
