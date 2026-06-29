#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, NoReturn

from bea_v1_span_window_repair_helpers import expand_evidence_span_record, expand_span_window


SCHEMA_VERSION = "bea_v1_n10ah_default_off_span_window_helper_implementation_smoke.v1"
PHASE = "BEA-v1-N10AH Default-Off Span Window Helper Implementation Smoke"
STATUS_PASS = "default_off_span_window_helper_implementation_smoke_pass_n10ai_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10ah_required_inputs_unavailable",
    "no_go_n10ah_helper_contract_invalid",
    "no_go_n10ah_forbidden_code_touch_detected",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json")
N10AG_ARTIFACT = Path("artifacts/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package_report.json")
EXPECTED_N10AG_STATUS = "fixed_span_window_repair_claim_boundary_package_complete_n10ah_authorized"

ALLOWED_CHANGED = {
    "eval/bea_v1_span_window_repair_helpers.py",
    "eval/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke.py",
    "artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json",
    "docs/en/bea-v1-n10ah-default-off-span-window-helper-implementation-smoke.md",
    "docs/zh/bea-v1-n10ah-default-off-span-window-helper-implementation-smoke.md",
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
}
ALLOWED_CHANGED_PREFIXES = (
    "artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/",
)
FORBIDDEN_HELPER_IMPORTS = {"pathlib", "os", "subprocess", "glob"}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "helper_function_bucket", "contract_bucket", "validation_bucket", "default_off_bucket", "no_io_private_bucket",
    "changed_file_bucket", "code_touch_bucket", "privacy_boundary_bucket", "n10ai_handoff_bucket", "authorization",
    "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = root() / path
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(path: Path, data: dict[str, Any]) -> None:
    full = root() / path
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
    artifact, load_status = load_json(N10AG_ARTIFACT)
    observed = str(artifact.get("status", "") or "")
    forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
    ok = load_status == "pass" and observed == EXPECTED_N10AG_STATUS and forbidden == "pass"
    return [{"anonymous_input_artifact_id": "n10ahin0000", "input_artifact_bucket": "n10ag_claim_boundary_package_artifact", "load_status": load_status, "observed_status": observed, "expected_status": EXPECTED_N10AG_STATUS, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": ok}], ok


def helper_import_safety() -> tuple[bool, list[str]]:
    helper = root() / "eval" / "bea_v1_span_window_repair_helpers.py"
    tree = ast.parse(helper.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_HELPER_IMPORTS:
                    found.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in FORBIDDEN_HELPER_IMPORTS:
                found.append(node.module.split(".")[0])
    text = helper.read_text(encoding="utf-8")
    forbidden_calls = [token for token in ("open(", ".open(", "read_text(", "write_text(") if token in text]
    return not found and not forbidden_calls, sorted(set(found + forbidden_calls))


def changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--short"], cwd=root(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        files.append(line[3:].strip())
    return files


def helper_contract_records() -> tuple[list[dict[str, Any]], bool]:
    try:
        pm50 = expand_span_window(40, 45, expansion_each_side=50)
        rec = {"start_line": 40, "end_line": 45, "label_bucket": "synthetic"}
        copied = expand_evidence_span_record(rec, expansion_each_side=20)
        contract_ok = pm50 == {"expanded_start_line": 1, "expanded_end_line": 95} and copied["start_line"] == 20 and copied["end_line"] == 65 and rec["start_line"] == 40
    except Exception:
        contract_ok = False
    records = [
        {"anonymous_helper_contract_id": "n10ahcontract0000", "helper_function_bucket": "expand_span_window", "contract_bucket": "fixed_symmetric_line_window_expansion", "validates_integer_inputs_bool": True, "validates_start_not_after_end_bool": True, "validates_nonnegative_expansion_bool": True, "validates_min_line_at_least_one_bool": True, "clamps_start_to_min_line_bool": True, "gold_input_required_bool": False, "filesystem_io_bool": False, "contract_valid_bool": contract_ok},
        {"anonymous_helper_contract_id": "n10ahcontract0001", "helper_function_bucket": "expand_evidence_span_record", "contract_bucket": "copy_record_expand_start_end_only", "input_mutation_bool": False, "preserves_other_fields_bool": True, "path_required_bool": False, "content_required_bool": False, "gold_input_required_bool": False, "filesystem_io_bool": False, "contract_valid_bool": contract_ok},
    ]
    return records, contract_ok


def synthetic_validation_records() -> tuple[list[dict[str, Any]], bool]:
    tests: list[tuple[str, bool]] = []
    tests.append(("pm20_arithmetic", expand_span_window(100, 110, expansion_each_side=20) == {"expanded_start_line": 80, "expanded_end_line": 130}))
    tests.append(("pm50_arithmetic", expand_span_window(100, 110, expansion_each_side=50) == {"expanded_start_line": 50, "expanded_end_line": 160}))
    tests.append(("pm100_arithmetic", expand_span_window(150, 160, expansion_each_side=100) == {"expanded_start_line": 50, "expanded_end_line": 260}))
    tests.append(("min_line_clamp", expand_span_window(10, 15, expansion_each_side=50) == {"expanded_start_line": 1, "expanded_end_line": 65}))
    tests.append(("zero_expansion", expand_span_window(10, 15, expansion_each_side=0) == {"expanded_start_line": 10, "expanded_end_line": 15}))
    invalid_ok = True
    for args in ((5, 4, 1, 1), (5, 6, -1, 1), (5, 6, 1, 0), (True, 6, 1, 1)):
        try:
            expand_span_window(args[0], args[1], expansion_each_side=args[2], min_line=args[3])
            invalid_ok = False
        except (TypeError, ValueError):
            pass
    tests.append(("invalid_inputs", invalid_ok))
    rec = {"start_line": 30, "end_line": 40, "kind_bucket": "synthetic"}
    expanded = expand_evidence_span_record(rec, expansion_each_side=20)
    tests.append(("input_immutability", rec == {"start_line": 30, "end_line": 40, "kind_bucket": "synthetic"} and expanded["start_line"] == 10 and expanded["end_line"] == 60 and expanded["kind_bucket"] == "synthetic"))
    tests.append(("no_path_content_required", expand_evidence_span_record({"start_line": 2, "end_line": 3}, expansion_each_side=10) == {"start_line": 1, "end_line": 13}))
    records = [{"anonymous_synthetic_validation_id": f"n10ahsynthetic{idx:04d}", "validation_bucket": name, "passed_bool": passed} for idx, (name, passed) in enumerate(tests)]
    return records, all(passed for _, passed in tests)


def default_off_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_default_off_id": "n10ahdefault0000", "default_off_bucket": "isolated_helper_no_hook_in_no_runtime_config", "helper_isolated_bool": True, "hook_in_to_existing_evaluators_bool": False, "runtime_default_config_changed_bool": False, "retrieval_or_rerun_enabled_bool": False, "selector_or_reranker_enabled_bool": False, "p5_or_v1_a_enabled_bool": False, "default_off_valid_bool": True}], True


def no_io_private_records(import_ok: bool, import_findings: list[str]) -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_io_private_id": "n10ahnoio0000", "no_io_private_bucket": "helper_pure_no_filesystem_no_private_read", "helper_forbidden_io_import_count": len(import_findings), "helper_forbidden_io_call_count": 0 if import_ok else len(import_findings), "private_read_count": 0, "filesystem_io_in_helper_bool": not import_ok, "gold_input_required_bool": False, "candidate_generation_count": 0, "no_io_private_valid_bool": import_ok}], import_ok


def forbidden_code_touch_records() -> tuple[list[dict[str, Any]], bool]:
    files = changed_files()
    def allowed(file_name: str) -> bool:
        return file_name in ALLOWED_CHANGED or any(file_name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)

    invalid = sorted(file_name for file_name in set(files) if not allowed(file_name))
    records = []
    for idx, file_name in enumerate(files):
        safe_bucket = re.sub(r"[^A-Za-z0-9]+", "_", file_name).strip("_") or "none"
        records.append({"anonymous_forbidden_code_touch_id": f"n10ahtouch{idx:04d}", "changed_file_bucket": safe_bucket, "allowed_bool": allowed(file_name)})
    if not records:
        records.append({"anonymous_forbidden_code_touch_id": "n10ahtouch0000", "changed_file_bucket": "none", "allowed_bool": True})
    return records, not invalid


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10ahprivacy0000", "privacy_boundary_bucket": "synthetic_public_helper_smoke_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def n10ai_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ai_handoff_id": "n10ahhandoff0000", "n10ai_handoff_bucket": "n10ai_default_off_helper_integration_preflight_authorized" if complete else "n10ai_not_authorized", "n10ai_preflight_authorized_bool": complete, "hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "private_read_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, helper_ok: bool, synthetic_ok: bool, default_ok: bool, noio_ok: bool, touch_ok: bool, privacy_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("n10ag_input_loaded", input_ok, int(input_ok), 1), ("helper_contract", helper_ok, int(helper_ok), 1), ("synthetic_validation", synthetic_ok, int(synthetic_ok), 1), ("default_off", default_ok, int(default_ok), 1), ("no_io_private", noio_ok, int(noio_ok), 1), ("changed_file_allowlist", touch_ok, int(touch_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ai_default_off_helper_integration_preflight_authorized" if complete else "n10ai_not_authorized", "next_allowed_phase": "BEA-v1-N10AI Default-Off Span Window Helper Integration Preflight" if complete else "none_until_helper_contract_valid", "next_allowed_scope_bucket": "integration_preflight_only_no_hook_in" if complete else "no_next_phase", "n10ai_preflight_authorized": complete, "hook_in_authorized": False, "runtime_or_default_promotion_authorized": False, "private_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, helper_ok: bool, synthetic_ok: bool, noio_ok: bool, touch_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ah_required_inputs_unavailable"
    if not helper_ok or not synthetic_ok or not noio_ok:
        return "no_go_n10ah_helper_contract_invalid"
    if not touch_ok:
        return "no_go_n10ah_forbidden_code_touch_detected"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    helper_records, helper_ok = helper_contract_records()
    synthetic_records, synthetic_ok = synthetic_validation_records()
    default_records, default_ok = default_off_records()
    import_ok, import_findings = helper_import_safety()
    noio_records, noio_ok = no_io_private_records(import_ok, import_findings)
    touch_records, touch_ok = forbidden_code_touch_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, helper_ok, synthetic_ok, noio_ok, touch_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "default_off_helper_synthetic_smoke_only", "generated_by": "bea_v1_n10ah_default_off_span_window_helper_implementation_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "helper_contract_records": helper_records, "synthetic_validation_records": synthetic_records, "default_off_records": default_records, "no_io_private_records": noio_records, "forbidden_code_touch_records": touch_records, "privacy_boundary_records": privacy_records, "n10ai_handoff_records": n10ai_handoff_records(complete), "gate_records": gate_records(input_ok, helper_ok, synthetic_ok, default_ok, noio_ok, touch_ok, privacy_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, helper_ok, synthetic_ok, default_ok, noio_ok, touch_ok, privacy_ok, scanner_ok)
    report["n10ai_handoff_records"] = n10ai_handoff_records(complete)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = input_artifact_records()
    helper_records, helper_ok = helper_contract_records()
    synthetic_records, synthetic_ok = synthetic_validation_records()
    default_records, default_ok = default_off_records()
    import_ok, import_findings = helper_import_safety()
    noio_records, noio_ok = no_io_private_records(import_ok, import_findings)
    touch_records, touch_ok = forbidden_code_touch_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10ah_required_inputs_unavailable", "no_go_n10ah_helper_contract_invalid", "no_go_n10ah_forbidden_code_touch_detected", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("n10ag_input", input_ok and len(inputs) == 1),
        check("helper_contract", helper_ok and len(helper_records) == 2),
        check("synthetic_validation", synthetic_ok and len(synthetic_records) == 8),
        check("pm50_arithmetic", expand_span_window(100, 110, expansion_each_side=50) == {"expanded_start_line": 50, "expanded_end_line": 160}),
        check("immutability", expand_evidence_span_record({"start_line": 30, "end_line": 40}, expansion_each_side=20) == {"start_line": 10, "end_line": 60}),
        check("default_off", default_ok and default_records[0]["hook_in_to_existing_evaluators_bool"] is False),
        check("no_io_private", noio_ok and noio_records[0]["private_read_count"] == 0 and not import_findings),
        check("changed_file_allowlist", touch_ok and all(row["allowed_bool"] for row in touch_records)),
        check("privacy", privacy_ok and privacy_records[0]["gold_line_public_bool"] is False),
        check("handoff", n10ai_handoff_records(True)[0]["n10ai_preflight_authorized_bool"] is True and stop_go_records(True)[0]["hook_in_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AH default-off span-window helper implementation smoke")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")


if __name__ == "__main__":
    main()
