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


SCHEMA_VERSION = "bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package.v1"
PHASE = "BEA-v1-N10AK Eval-Only Adapter Public Fixture Integration Audit Package"
STATUS_PASS = "eval_only_adapter_public_fixture_audit_package_complete_n10al_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10ak_required_public_inputs_unavailable",
    "no_go_n10ak_adapter_chain_mismatch",
    "no_go_n10ak_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json")
INPUTS = {
    "n10aj_adapter_patch_artifact": (Path("artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json"), "default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized"),
    "n10ai_integration_preflight_artifact": (Path("artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json"), "default_off_span_window_helper_integration_preflight_pass_n10aj_authorized"),
    "n10ah_helper_smoke_artifact": (Path("artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json"), "default_off_span_window_helper_implementation_smoke_pass_n10ai_authorized"),
}
ALLOWED_CHANGED = {
    "eval/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package.py",
    "artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/",
    "artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json",
    "docs/en/bea-v1-n10ak-eval-only-adapter-public-fixture-audit-package.md",
    "docs/zh/bea-v1-n10ak-eval-only-adapter-public-fixture-audit-package.md",
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
}
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
    "chain_bucket", "validation_bucket", "default_off_boundary_bucket", "forbidden_claim_bucket", "no_private_recompute_bucket",
    "n10al_handoff_bucket", "changed_file_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation",
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


def load_inputs() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = read_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10akin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def static_source_checks() -> tuple[bool, bool, bool, int, int]:
    adapter_path = root() / "eval" / "bea_v1_span_window_projection_adapter.py"
    helper_path = root() / "eval" / "bea_v1_span_window_repair_helpers.py"
    adapter_exists = adapter_path.exists()
    helper_exists = helper_path.exists()
    imports_helper = False
    forbidden_import_count = 0
    forbidden_call_count = 0
    if adapter_exists:
        tree = ast.parse(adapter_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports_helper = imports_helper or (node.module == "bea_v1_span_window_repair_helpers" and any(alias.name == "expand_evidence_span_record" for alias in node.names))
                if (node.module or "") in {"pathlib", "os", "subprocess", "glob", "socket", "requests", "urllib"}:
                    forbidden_import_count += 1
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in {"pathlib", "os", "subprocess", "glob", "socket", "requests", "urllib"}:
                        forbidden_import_count += 1
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"open", "eval", "exec", "__import__"}:
                forbidden_call_count += 1
    return adapter_exists, helper_exists, imports_helper, forbidden_import_count, forbidden_call_count


def adapter_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10aj = artifacts.get("n10aj_adapter_patch_artifact", {})
    n10ai = artifacts.get("n10ai_integration_preflight_artifact", {})
    n10ah = artifacts.get("n10ah_helper_smoke_artifact", {})
    adapter_exists, helper_exists, imports_helper, forbidden_import_count, forbidden_call_count = static_source_checks()
    n10ai_targets = n10ai.get("candidate_hook_point_records", [])
    target_ok = any(isinstance(r, dict) and r.get("recommended_hook_target_bool") is True and r.get("hook_candidate_bucket") == "future_eval_only_span_projection_adapter" for r in n10ai_targets)
    n10aj_contracts = n10aj.get("adapter_contract_records", [])
    contracts_ok = isinstance(n10aj_contracts, list) and len(n10aj_contracts) == 2 and all(isinstance(r, dict) and r.get("adapter_contract_valid_bool") is True and r.get("imports_helper_bool") is True for r in n10aj_contracts)
    ok = adapter_exists and helper_exists and imports_helper and forbidden_import_count == 0 and forbidden_call_count == 0 and target_ok and contracts_ok and n10ah.get("status") == INPUTS["n10ah_helper_smoke_artifact"][1]
    return [{"anonymous_adapter_chain_id": "n10akchain0000", "chain_bucket": "n10ah_helper_n10ai_future_adapter_n10aj_patch", "n10ah_helper_status_valid_bool": n10ah.get("status") == INPUTS["n10ah_helper_smoke_artifact"][1], "n10ai_future_adapter_target_bool": target_ok, "n10aj_adapter_status_valid_bool": n10aj.get("status") == INPUTS["n10aj_adapter_patch_artifact"][1], "adapter_source_exists_bool": adapter_exists, "helper_source_exists_bool": helper_exists, "adapter_imports_helper_bool": imports_helper, "adapter_forbidden_import_count": forbidden_import_count, "adapter_forbidden_call_count": forbidden_call_count, "adapter_contracts_valid_bool": contracts_ok, "adapter_chain_valid_bool": ok}], ok


def public_fixture_validation_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10aj = artifacts.get("n10aj_adapter_patch_artifact", {})
    synthetic = n10aj.get("synthetic_projection_records", [])
    order = (n10aj.get("order_preservation_records") or [{}])[0]
    noio = (n10aj.get("no_io_private_records") or [{}])[0]
    synthetic_ok = isinstance(synthetic, list) and len(synthetic) == 8 and all(isinstance(r, dict) and r.get("passed_bool") is True for r in synthetic)
    ok = synthetic_ok and order.get("order_preservation_valid_bool") is True and order.get("candidate_count_changed_bool") is False and order.get("candidate_order_changed_bool") is False and noio.get("private_read_count") == 0 and noio.get("filesystem_io_count") == 0
    return [{"anonymous_public_fixture_validation_id": "n10akfixture0000", "validation_bucket": "n10aj_synthetic_public_fixture_package", "synthetic_projection_count": len(synthetic) if isinstance(synthetic, list) else 0, "synthetic_projection_passed_bool": synthetic_ok, "adapter_count_preservation_bool": order.get("candidate_count_changed_bool") is False, "adapter_order_preservation_bool": order.get("candidate_order_changed_bool") is False, "adapter_no_io_bool": noio.get("filesystem_io_count") == 0, "adapter_no_private_read_bool": noio.get("private_read_count") == 0, "empirical_metric_recompute_bool": False, "public_fixture_validation_valid_bool": ok}], ok


def default_off_boundary_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10aj = artifacts.get("n10aj_adapter_patch_artifact", {})
    default = (n10aj.get("default_off_records") or [{}])[0]
    ok = default.get("adapter_default_enabled_bool") is False and default.get("existing_evaluator_hook_in_bool") is False and default.get("runtime_default_config_changed_bool") is False and default.get("private_read_by_default_bool") is False and default.get("retrieval_or_rerun_enabled_bool") is False
    return [{"anonymous_default_off_boundary_id": "n10akdefault0000", "default_off_boundary_bucket": "adapter_exists_default_off_no_hook_no_runtime", "adapter_default_enabled_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_config_changed_bool": False, "private_read_by_default_bool": False, "retrieval_or_rerun_enabled_bool": False, "selector_or_reranker_enabled_bool": False, "default_off_boundary_valid_bool": ok}], ok


def forbidden_claim_records() -> tuple[list[dict[str, Any]], bool]:
    claims = [
        "runtime_default_promotion", "existing_evaluator_hook_in", "private_read_by_default", "retrieval_rerun",
        "candidate_generation", "selector_reranker", "p5_or_v1_a", "method_winner", "downstream_value",
    ]
    records = [{"anonymous_forbidden_claim_id": f"n10akclaim{idx:04d}", "forbidden_claim_bucket": claim, "claimed_bool": False, "authorized_bool": False} for idx, claim in enumerate(claims)]
    return records, True


def no_private_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_private_recompute_id": "n10aknoexec0000", "no_private_recompute_bucket": "public_synthetic_audit_package_only", "private_read_count": 0, "private_scan_count": 0, "empirical_recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0, "no_private_recompute_valid_bool": True}], True


def changed_files_valid() -> bool:
    result = subprocess.run(["git", "status", "--short"], cwd=root(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    files = [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]
    return not (set(files) - ALLOWED_CHANGED)


def n10al_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10al_handoff_id": "n10akhandoff0000", "n10al_handoff_bucket": "n10al_scoped_eval_only_integration_smoke_authorized" if complete else "n10al_not_authorized", "n10al_authorized_bool": complete, "next_scope_bucket": "scoped_eval_only_integration_smoke_planning_or_patch" if complete else "none", "existing_evaluator_hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "private_read_by_default_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, chain_ok: bool, fixture_ok: bool, default_ok: bool, claims_ok: bool, noexec_ok: bool, touch_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("adapter_chain", chain_ok, int(chain_ok), 1), ("public_fixture_validation", fixture_ok, int(fixture_ok), 1), ("default_off_boundary", default_ok, int(default_ok), 1), ("claim_boundary", claims_ok, int(claims_ok), 1), ("no_private_recompute", noexec_ok, int(noexec_ok), 1), ("changed_file_allowlist", touch_ok, int(touch_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10al_scoped_eval_only_integration_smoke_authorized" if complete else "n10al_not_authorized", "next_allowed_phase": "BEA-v1-N10AL Scoped Eval-Only Adapter Integration Smoke" if complete else "none_until_adapter_chain_valid", "next_allowed_scope_bucket": "scoped_eval_only_integration_smoke_planning_or_patch" if complete else "no_next_phase", "n10al_authorized": complete, "existing_evaluator_hook_in_authorized": False, "runtime_or_default_enablement_authorized": False, "private_read_by_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, fixture_ok: bool, default_ok: bool, claims_ok: bool, noexec_ok: bool, touch_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ak_required_public_inputs_unavailable"
    if not chain_ok or not fixture_ok or not touch_ok:
        return "no_go_n10ak_adapter_chain_mismatch"
    if not default_ok or not claims_ok or not noexec_ok:
        return "no_go_n10ak_claim_boundary_invalid"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = load_inputs()
    chain_records, chain_ok = adapter_chain_records(artifacts)
    fixture_records, fixture_ok = public_fixture_validation_records(artifacts)
    default_records, default_ok = default_off_boundary_records(artifacts)
    claim_records, claims_ok = forbidden_claim_records()
    noexec_records, noexec_ok = no_private_recompute_records()
    touch_ok = changed_files_valid()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, fixture_ok, default_ok, claims_ok, noexec_ok, touch_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_synthetic_adapter_audit_package_only", "generated_by": "bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "adapter_chain_records": chain_records, "public_fixture_validation_records": fixture_records, "default_off_boundary_records": default_records, "forbidden_claim_records": claim_records, "no_private_recompute_records": noexec_records, "n10al_handoff_records": n10al_handoff_records(complete), "gate_records": gate_records(input_ok, chain_ok, fixture_ok, default_ok, claims_ok, noexec_ok, touch_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, chain_ok, fixture_ok, default_ok, claims_ok, noexec_ok, touch_ok, scanner_ok)
    report["n10al_handoff_records"] = n10al_handoff_records(complete)
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
    inputs, artifacts, input_ok = load_inputs()
    chain_records, chain_ok = adapter_chain_records(artifacts)
    fixture_records, fixture_ok = public_fixture_validation_records(artifacts)
    default_records, default_ok = default_off_boundary_records(artifacts)
    claim_records, claims_ok = forbidden_claim_records()
    noexec_records, noexec_ok = no_private_recompute_records()
    touch_ok = changed_files_valid()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10ak_required_public_inputs_unavailable", "no_go_n10ak_adapter_chain_mismatch", "no_go_n10ak_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 3),
        check("adapter_chain", chain_ok and chain_records[0]["adapter_imports_helper_bool"] is True and chain_records[0]["n10ai_future_adapter_target_bool"] is True),
        check("public_fixture", fixture_ok and fixture_records[0]["synthetic_projection_count"] == 8 and fixture_records[0]["adapter_no_private_read_bool"] is True),
        check("default_off", default_ok and default_records[0]["adapter_default_enabled_bool"] is False and default_records[0]["existing_evaluator_hook_in_bool"] is False),
        check("forbidden_claims", claims_ok and len(claim_records) == 9 and all(not r["claimed_bool"] and not r["authorized_bool"] for r in claim_records)),
        check("no_private_recompute", noexec_ok and noexec_records[0]["private_read_count"] == 0 and noexec_records[0]["empirical_recompute_count"] == 0),
        check("changed_files", touch_ok),
        check("handoff", n10al_handoff_records(True)[0]["n10al_authorized_bool"] is True and stop_go_records(True)[0]["existing_evaluator_hook_in_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AK eval-only adapter public fixture audit package")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, n10al={report['n10al_handoff_records'][0]['n10al_authorized_bool']})")


if __name__ == "__main__":
    main()
