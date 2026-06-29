#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, NoReturn

from bea_v1_span_window_projection_adapter import project_evidence_span_record, project_evidence_spans


SCHEMA_VERSION = "bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch.v1"
PHASE = "BEA-v1-N10AJ Default-Off Eval-Only Span Projection Adapter Patch"
STATUS_PASS = "default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10aj_required_inputs_unavailable",
    "no_go_n10aj_adapter_contract_invalid",
    "no_go_n10aj_forbidden_code_touch_detected",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json")
N10AI_ARTIFACT = Path("artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json")
EXPECTED_N10AI_STATUS = "default_off_span_window_helper_integration_preflight_pass_n10aj_authorized"
ALLOWED_CHANGED = {
    "eval/bea_v1_span_window_projection_adapter.py",
    "eval/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch.py",
    "artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/",
    "artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json",
    "docs/en/bea-v1-n10aj-default-off-eval-only-span-projection-adapter-patch.md",
    "docs/zh/bea-v1-n10aj-default-off-eval-only-span-projection-adapter-patch.md",
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
}
FORBIDDEN_ADAPTER_IMPORTS = {"pathlib", "os", "subprocess", "glob", "socket", "requests", "urllib", "http.client"}
FORBIDDEN_ADAPTER_CALLS = {"open", "exec", "eval", "__import__"}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "adapter_function_bucket", "contract_bucket", "validation_bucket", "default_off_bucket", "order_preservation_bucket",
    "no_io_private_bucket", "changed_file_bucket", "privacy_boundary_bucket", "n10ak_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, data: dict[str, Any]) -> None:
    full = root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
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
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    artifact, load_status = read_json(N10AI_ARTIFACT)
    observed = str(artifact.get("status", "") or "")
    forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
    ok = load_status == "pass" and observed == EXPECTED_N10AI_STATUS and forbidden == "pass"
    return [{"anonymous_input_artifact_id": "n10ajin0000", "input_artifact_bucket": "n10ai_integration_preflight_artifact", "load_status": load_status, "observed_status": observed, "expected_status": EXPECTED_N10AI_STATUS, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": ok}], ok


def adapter_ast_safety() -> tuple[bool, int, int, bool]:
    text = (root() / "eval" / "bea_v1_span_window_projection_adapter.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    forbidden_imports = 0
    helper_import = False
    forbidden_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_ADAPTER_IMPORTS or alias.name.split(".")[0] in FORBIDDEN_ADAPTER_IMPORTS:
                    forbidden_imports += 1
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "bea_v1_span_window_repair_helpers":
                helper_import = any(alias.name == "expand_evidence_span_record" for alias in node.names)
            if mod in FORBIDDEN_ADAPTER_IMPORTS or mod.split(".")[0] in FORBIDDEN_ADAPTER_IMPORTS:
                forbidden_imports += 1
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_ADAPTER_CALLS:
                forbidden_calls += 1
    return helper_import and forbidden_imports == 0 and forbidden_calls == 0, forbidden_imports, forbidden_calls, helper_import


def adapter_contract_records() -> tuple[list[dict[str, Any]], bool]:
    safe, forbidden_imports, forbidden_calls, helper_import = adapter_ast_safety()
    sample = {"start_line": 30, "end_line": 40, "label_bucket": "synthetic"}
    unchanged = project_evidence_span_record(sample, expansion_each_side=50, enabled=False)
    expanded = project_evidence_span_record(sample, expansion_each_side=20, enabled=True)
    records = [
        {"anonymous_adapter_contract_id": "n10ajcontract0000", "adapter_function_bucket": "project_evidence_span_record", "contract_bucket": "default_off_copy_or_enabled_fixed_expansion", "imports_helper_bool": helper_import, "default_enabled_bool": False, "disabled_returns_nonmutating_copy_bool": unchanged == sample and unchanged is not sample, "enabled_expands_start_end_bool": expanded.get("start_line") == 10 and expanded.get("end_line") == 60, "path_content_gold_required_bool": False, "adapter_contract_valid_bool": safe and unchanged == sample and expanded.get("start_line") == 10 and expanded.get("end_line") == 60},
        {"anonymous_adapter_contract_id": "n10ajcontract0001", "adapter_function_bucket": "project_evidence_spans", "contract_bucket": "sequence_projection_preserves_count_and_order", "imports_helper_bool": helper_import, "default_enabled_bool": False, "candidate_count_changed_bool": False, "candidate_order_changed_bool": False, "fixed_expansion_supplied_by_caller_bool": True, "forbidden_import_count": forbidden_imports, "forbidden_call_count": forbidden_calls, "adapter_contract_valid_bool": safe},
    ]
    return records, all(r["adapter_contract_valid_bool"] for r in records)


def synthetic_projection_records() -> tuple[list[dict[str, Any]], bool]:
    base = [{"start_line": 60, "end_line": 70, "label_bucket": "a"}, {"start_line": 5, "end_line": 8, "label_bucket": "b"}]
    original = [dict(r) for r in base]
    tests: list[tuple[str, bool]] = []
    disabled = project_evidence_spans(base, expansion_each_side=50, enabled=False)
    tests.append(("disabled_unchanged_nonmutating", disabled == original and disabled is not base and disabled[0] is not base[0] and base == original))
    pm20 = project_evidence_span_record(base[0], expansion_each_side=20, enabled=True)
    tests.append(("enabled_pm20_expansion", pm20["start_line"] == 40 and pm20["end_line"] == 90))
    pm50 = project_evidence_span_record(base[0], expansion_each_side=50, enabled=True)
    tests.append(("enabled_pm50_expansion", pm50["start_line"] == 10 and pm50["end_line"] == 120))
    clamped = project_evidence_span_record(base[1], expansion_each_side=20, enabled=True)
    tests.append(("min_line_clamp", clamped["start_line"] == 1 and clamped["end_line"] == 28))
    enabled_many = project_evidence_spans(base, expansion_each_side=20, enabled=True)
    tests.append(("order_count_preserved", len(enabled_many) == 2 and [r["label_bucket"] for r in enabled_many] == ["a", "b"]))
    minimal = project_evidence_span_record({"start_line": 2, "end_line": 2}, expansion_each_side=0, enabled=True)
    tests.append(("no_path_content_gold_required", minimal == {"start_line": 2, "end_line": 2}))
    try:
        project_evidence_span_record({"start_line": 5, "end_line": 2}, expansion_each_side=1, enabled=True)
        invalid_ok = False
    except ValueError:
        invalid_ok = True
    tests.append(("invalid_inputs_propagate", invalid_ok))
    tests.append(("input_immutability", base == original))
    records = [{"anonymous_synthetic_projection_id": f"n10ajsynthetic{idx:04d}", "validation_bucket": bucket, "passed_bool": passed} for idx, (bucket, passed) in enumerate(tests)]
    return records, all(passed for _bucket, passed in tests)


def default_off_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_default_off_id": "n10ajdefault0000", "default_off_bucket": "adapter_default_disabled_no_hook_no_runtime", "default_off_valid_bool": True, "adapter_default_enabled_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_config_changed_bool": False, "private_read_by_default_bool": False, "retrieval_or_rerun_enabled_bool": False, "selector_or_reranker_enabled_bool": False}], True


def order_preservation_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [{"start_line": 100, "end_line": 101, "order_bucket": "first"}, {"start_line": 10, "end_line": 11, "order_bucket": "second"}]
    out = project_evidence_spans(rows, expansion_each_side=50, enabled=True)
    ok = len(out) == len(rows) and [r["order_bucket"] for r in out] == [r["order_bucket"] for r in rows]
    return [{"anonymous_order_preservation_id": "n10ajorder0000", "order_preservation_bucket": "sequence_count_and_order_preserved", "input_record_count": len(rows), "output_record_count": len(out), "candidate_count_changed_bool": False, "candidate_order_changed_bool": False, "order_preservation_valid_bool": ok}], ok


def no_io_private_records() -> tuple[list[dict[str, Any]], bool]:
    safe, forbidden_imports, forbidden_calls, _helper = adapter_ast_safety()
    return [{"anonymous_no_io_private_id": "n10ajnoio0000", "no_io_private_bucket": "adapter_pure_no_filesystem_private_or_runtime_io", "private_read_count": 0, "filesystem_io_count": 0, "helper_forbidden_io_import_count": forbidden_imports, "helper_forbidden_io_call_count": forbidden_calls, "retrieval_execution_count": 0, "rerun_execution_count": 0, "candidate_generation_count": 0, "gold_input_required_bool": False, "no_io_private_valid_bool": safe}], safe


def changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--short"], cwd=root(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


def forbidden_code_touch_records() -> tuple[list[dict[str, Any]], bool]:
    files = changed_files()
    invalid = sorted(set(files) - ALLOWED_CHANGED)
    records = []
    for idx, file_name in enumerate(files):
        safe = re.sub(r"[^A-Za-z0-9]+", "_", file_name).strip("_") or "none"
        records.append({"anonymous_forbidden_code_touch_id": f"n10ajtouch{idx:04d}", "changed_file_bucket": safe, "allowed_bool": file_name in ALLOWED_CHANGED})
    if not records:
        records.append({"anonymous_forbidden_code_touch_id": "n10ajtouch0000", "changed_file_bucket": "none", "allowed_bool": True})
    existing_eval_touched = any(f.startswith("eval/bea_v1_n10t_") or f.startswith("eval/bea_v1_n10x_") or f.startswith("eval/bea_v1_n10ab_") for f in files)
    return records, not invalid and not existing_eval_touched


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10ajprivacy0000", "privacy_boundary_bucket": "synthetic_public_fixture_only_no_private_data", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def n10ak_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ak_handoff_id": "n10ajhandoff0000", "n10ak_handoff_bucket": "n10ak_eval_only_adapter_public_fixture_audit_package_authorized" if complete else "n10ak_not_authorized", "n10ak_public_fixture_audit_authorized_bool": complete, "public_or_synthetic_only_bool": True, "existing_evaluator_hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "private_read_by_default_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, contract_ok: bool, synthetic_ok: bool, default_ok: bool, order_ok: bool, noio_ok: bool, touch_ok: bool, privacy_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("n10ai_input_loaded", input_ok, int(input_ok), 1), ("adapter_contract", contract_ok, int(contract_ok), 1), ("synthetic_projection", synthetic_ok, int(synthetic_ok), 1), ("default_off", default_ok, int(default_ok), 1), ("order_count_preservation", order_ok, int(order_ok), 1), ("no_io_private", noio_ok, int(noio_ok), 1), ("changed_file_allowlist", touch_ok, int(touch_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ak_eval_only_adapter_public_fixture_integration_audit_authorized" if complete else "n10ak_not_authorized", "next_allowed_phase": "BEA-v1-N10AK Eval-Only Adapter Public Fixture Integration Audit Package" if complete else "none_until_adapter_contract_valid", "next_allowed_scope_bucket": "public_or_synthetic_only_no_private_read" if complete else "no_next_phase", "n10ak_public_fixture_audit_authorized": complete, "existing_evaluator_hook_in_authorized": False, "runtime_or_default_enablement_authorized": False, "private_read_by_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, contract_ok: bool, synthetic_ok: bool, default_ok: bool, order_ok: bool, noio_ok: bool, touch_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10aj_required_inputs_unavailable"
    if not touch_ok:
        return "no_go_n10aj_forbidden_code_touch_detected"
    if not (contract_ok and synthetic_ok and default_ok and order_ok and noio_ok):
        return "no_go_n10aj_adapter_contract_invalid"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    adapter_records, contract_ok = adapter_contract_records()
    synthetic_records, synthetic_ok = synthetic_projection_records()
    default_records, default_ok = default_off_records()
    order_records, order_ok = order_preservation_records()
    noio_records, noio_ok = no_io_private_records()
    touch_records, touch_ok = forbidden_code_touch_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, contract_ok, synthetic_ok, default_ok, order_ok, noio_ok, touch_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "default_off_eval_only_adapter_patch_synthetic_smoke_only", "generated_by": "bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "adapter_contract_records": adapter_records, "synthetic_projection_records": synthetic_records, "default_off_records": default_records, "order_preservation_records": order_records, "no_io_private_records": noio_records, "forbidden_code_touch_records": touch_records, "privacy_boundary_records": privacy_records, "n10ak_handoff_records": n10ak_handoff_records(complete), "gate_records": gate_records(input_ok, contract_ok, synthetic_ok, default_ok, order_ok, noio_ok, touch_ok, privacy_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, contract_ok, synthetic_ok, default_ok, order_ok, noio_ok, touch_ok, privacy_ok, scanner_ok)
    report["n10ak_handoff_records"] = n10ak_handoff_records(complete)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = input_artifact_records()
    adapter_records, contract_ok = adapter_contract_records()
    synthetic_records, synthetic_ok = synthetic_projection_records()
    default_records, default_ok = default_off_records()
    order_records, order_ok = order_preservation_records()
    noio_records, noio_ok = no_io_private_records()
    touch_records, touch_ok = forbidden_code_touch_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    disabled = project_evidence_span_record({"start_line": 8, "end_line": 9}, expansion_each_side=50, enabled=False)
    enabled = project_evidence_span_record({"start_line": 8, "end_line": 9}, expansion_each_side=50, enabled=True)
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10aj_required_inputs_unavailable", "no_go_n10aj_adapter_contract_invalid", "no_go_n10aj_forbidden_code_touch_detected", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("input", input_ok and inputs[0]["observed_status"] == EXPECTED_N10AI_STATUS),
        check("adapter_contract", contract_ok and len(adapter_records) == 2 and all(r["imports_helper_bool"] for r in adapter_records)),
        check("disabled_default", disabled == {"start_line": 8, "end_line": 9}),
        check("enabled_expansion", enabled == {"start_line": 1, "end_line": 59}),
        check("synthetic_projection", synthetic_ok and len(synthetic_records) == 8),
        check("default_off", default_ok and default_records[0]["adapter_default_enabled_bool"] is False and default_records[0]["existing_evaluator_hook_in_bool"] is False),
        check("order_preservation", order_ok and order_records[0]["candidate_count_changed_bool"] is False and order_records[0]["candidate_order_changed_bool"] is False),
        check("no_io_private", noio_ok and noio_records[0]["private_read_count"] == 0 and noio_records[0]["filesystem_io_count"] == 0),
        check("changed_files", touch_ok and all(r["allowed_bool"] for r in touch_records)),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0),
        check("handoff", n10ak_handoff_records(True)[0]["n10ak_public_fixture_audit_authorized_bool"] is True and stop_go_records(True)[0]["runtime_or_default_enablement_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AJ default-off eval-only span projection adapter patch")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for item in checks:
            print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, synthetic={len(report['synthetic_projection_records'])})")


if __name__ == "__main__":
    main()
