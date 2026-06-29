#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10am_eval_only_adapter_integration_result_audit_package.v1"
PHASE = "BEA-v1-N10AM Eval-Only Adapter Integration Result Audit Package"
STATUS_PASS = "eval_only_adapter_integration_result_audit_package_complete_n10an_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10am_required_public_inputs_unavailable",
    "no_go_n10am_integration_chain_mismatch",
    "no_go_n10am_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json")
INPUTS = {
    "n10al_integration_smoke_artifact": (Path("artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json"), "scoped_eval_only_adapter_integration_smoke_pass_n10am_authorized"),
    "n10ak_adapter_audit_package_artifact": (Path("artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json"), "eval_only_adapter_public_fixture_audit_package_complete_n10al_authorized"),
    "n10aj_adapter_patch_artifact": (Path("artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json"), "default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized"),
    "n10ab_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
    "n10ad_independent_recompute_artifact": (Path("artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json"), "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized"),
}
EXPECTED = {
    "eligible_denominator_count": 213,
    "baseline_top10_span_overlap_count": 9,
    "baseline_top20_span_overlap_count": 10,
    "pm50_top10_span_overlap_count": 19,
    "pm50_top20_span_overlap_count": 23,
    "delta_top10_vs_baseline_count": 10,
    "original_span_hit_lost_count": 0,
}
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
    "chain_bucket", "adapter_result_bucket", "claim_boundary_bucket", "forbidden_claim_bucket", "no_private_recompute_bucket",
    "n10an_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

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
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10amin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def integration_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10al = artifacts.get("n10al_integration_smoke_artifact", {})
    n10ak = artifacts.get("n10ak_adapter_audit_package_artifact", {})
    n10aj = artifacts.get("n10aj_adapter_patch_artifact", {})
    al_import = (n10al.get("adapter_import_boundary_records") or [{}])[0]
    al_comp = (n10al.get("comparison_to_n10ab_records") or [{}])[0]
    ak_chain = (n10ak.get("adapter_chain_records") or [{}])[0]
    aj_contracts = n10aj.get("adapter_contract_records", [])
    ok = (
        n10al.get("status") == INPUTS["n10al_integration_smoke_artifact"][1]
        and n10ak.get("status") == INPUTS["n10ak_adapter_audit_package_artifact"][1]
        and n10aj.get("status") == INPUTS["n10aj_adapter_patch_artifact"][1]
        and al_import.get("adapter_import_boundary_valid_bool") is True
        and al_import.get("existing_evaluator_imported_bool") is False
        and al_import.get("existing_evaluator_hook_in_bool") is False
        and al_comp.get("comparison_passed_bool") is True
        and ak_chain.get("adapter_chain_valid_bool") is True
        and isinstance(aj_contracts, list) and len(aj_contracts) == 2 and all(isinstance(r, dict) and r.get("adapter_contract_valid_bool") is True for r in aj_contracts)
    )
    return [{"anonymous_integration_chain_id": "n10amchain0000", "chain_bucket": "n10aj_adapter_n10ak_package_n10al_empirical_match", "n10al_status_valid_bool": n10al.get("status") == INPUTS["n10al_integration_smoke_artifact"][1], "n10ak_status_valid_bool": n10ak.get("status") == INPUTS["n10ak_adapter_audit_package_artifact"][1], "n10aj_status_valid_bool": n10aj.get("status") == INPUTS["n10aj_adapter_patch_artifact"][1], "adapter_import_boundary_valid_bool": al_import.get("adapter_import_boundary_valid_bool") is True, "existing_evaluator_imported_bool": bool(al_import.get("existing_evaluator_imported_bool", True)), "existing_evaluator_hook_in_bool": bool(al_import.get("existing_evaluator_hook_in_bool", True)), "comparison_to_n10ab_n10ad_passed_bool": al_comp.get("comparison_passed_bool") is True, "adapter_chain_valid_bool": ak_chain.get("adapter_chain_valid_bool") is True, "integration_chain_valid_bool": ok}], ok


def adapter_result_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10al = artifacts.get("n10al_integration_smoke_artifact", {})
    result = (n10al.get("adapter_integration_result_records") or [{}])[0]
    ok = (
        result.get("eligible_denominator_count") == 213
        and result.get("baseline_top10_span_overlap_count") == 9
        and result.get("baseline_top20_span_overlap_count") == 10
        and result.get("pm50_top10_span_overlap_count") == 19
        and result.get("pm50_top20_span_overlap_count") == 23
        and result.get("delta_top10_vs_baseline_count") == 10
        and result.get("original_span_hit_lost_count") == 0
        and result.get("candidate_pool_changed_bool") is False
        and result.get("order_changed_bool") is False
    )
    return [{"anonymous_adapter_result_id": "n10amresult0000", "adapter_result_bucket": "eval_only_adapter_reproduces_scoped_n1_pm50_aggregate", "eligible_denominator_count": int(result.get("eligible_denominator_count", 0)), "baseline_top10_span_overlap_count": int(result.get("baseline_top10_span_overlap_count", 0)), "baseline_top20_span_overlap_count": int(result.get("baseline_top20_span_overlap_count", 0)), "pm50_top10_span_overlap_count": int(result.get("pm50_top10_span_overlap_count", 0)), "pm50_top20_span_overlap_count": int(result.get("pm50_top20_span_overlap_count", 0)), "delta_top10_vs_baseline_count": int(result.get("delta_top10_vs_baseline_count", 0)), "original_span_hit_lost_count": int(result.get("original_span_hit_lost_count", 0)), "candidate_pool_changed_bool": bool(result.get("candidate_pool_changed_bool", True)), "order_changed_bool": bool(result.get("order_changed_bool", True)), "adapter_result_valid_bool": ok}], ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_claim_boundary_id": "n10amclaim0000", "claim_boundary_bucket": "eval_only_adapter_reproduces_scoped_n1_pm50_aggregate_only", "allowed_claim_bool": True, "runtime_default_promotion_claim_bool": False, "existing_evaluator_hook_in_claim_bool": False, "private_read_by_default_claim_bool": False, "retrieval_rerun_claim_bool": False, "candidate_generation_claim_bool": False, "selector_reranker_claim_bool": False, "p5_v1a_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": True}]
    return records, True


def no_private_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_private_recompute_id": "n10amnoexec0000", "no_private_recompute_bucket": "public_audit_package_only_no_private_read_no_recompute", "private_read_count": 0, "private_scan_count": 0, "empirical_recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0, "existing_evaluator_hook_in_count": 0, "no_private_recompute_valid_bool": True}], True


def n10an_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10an_handoff_id": "n10amhandoff0000", "n10an_handoff_bucket": "n10an_default_off_existing_evaluator_hook_feasibility_preflight_authorized" if complete else "n10an_not_authorized", "n10an_preflight_authorized_bool": complete, "preflight_public_static_only_bool": True, "existing_evaluator_hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "private_read_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, chain_ok: bool, result_ok: bool, claim_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("integration_chain", chain_ok, int(chain_ok), 1), ("adapter_result", result_ok, int(result_ok), 1), ("claim_boundary", claim_ok, int(claim_ok), 1), ("no_private_recompute", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10an_default_off_existing_evaluator_hook_feasibility_preflight_authorized" if complete else "n10an_not_authorized", "next_allowed_phase": "BEA-v1-N10AN Default-Off Existing-Evaluator Hook Feasibility Preflight" if complete else "none_until_integration_chain_valid", "next_allowed_scope_bucket": "public_static_feasibility_preflight_only" if complete else "no_next_phase", "n10an_preflight_authorized": complete, "existing_evaluator_hook_in_authorized": False, "runtime_or_default_enablement_authorized": False, "private_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, result_ok: bool, claim_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10am_required_public_inputs_unavailable"
    if not chain_ok or not result_ok:
        return "no_go_n10am_integration_chain_mismatch"
    if not claim_ok or not noexec_ok:
        return "no_go_n10am_claim_boundary_invalid"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    chain_records, chain_ok = integration_chain_records(artifacts)
    result_records, result_ok = adapter_result_records(artifacts)
    claim_records, claim_ok = claim_boundary_records()
    noexec_records, noexec_ok = no_private_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, result_ok, claim_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_adapter_integration_result_audit_package_only", "generated_by": "bea_v1_n10am_eval_only_adapter_integration_result_audit_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "integration_chain_records": chain_records, "adapter_result_records": result_records, "claim_boundary_records": claim_records, "no_private_recompute_records": noexec_records, "n10an_handoff_records": n10an_handoff_records(complete), "gate_records": gate_records(input_ok, chain_ok, result_ok, claim_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, chain_ok, result_ok, claim_ok, noexec_ok, scanner_ok)
    report["n10an_handoff_records"] = n10an_handoff_records(complete)
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
    inputs, artifacts, input_ok = input_artifact_records()
    chain_records, chain_ok = integration_chain_records(artifacts)
    result_records, result_ok = adapter_result_records(artifacts)
    claim_records, claim_ok = claim_boundary_records()
    noexec_records, noexec_ok = no_private_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10am_required_public_inputs_unavailable", "no_go_n10am_integration_chain_mismatch", "no_go_n10am_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 5),
        check("chain", chain_ok and chain_records[0]["existing_evaluator_imported_bool"] is False and chain_records[0]["existing_evaluator_hook_in_bool"] is False),
        check("result", result_ok and result_records[0]["eligible_denominator_count"] == 213 and result_records[0]["pm50_top10_span_overlap_count"] == 19),
        check("candidate_order", result_records[0]["candidate_pool_changed_bool"] is False and result_records[0]["order_changed_bool"] is False),
        check("claims", claim_ok and claim_records[0]["runtime_default_promotion_claim_bool"] is False and claim_records[0]["downstream_value_claim_bool"] is False),
        check("no_private_recompute", noexec_ok and noexec_records[0]["private_read_count"] == 0 and noexec_records[0]["empirical_recompute_count"] == 0),
        check("handoff", n10an_handoff_records(True)[0]["n10an_preflight_authorized_bool"] is True and stop_go_records(True)[0]["existing_evaluator_hook_in_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AM eval-only adapter integration result audit package")
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
    result = report["adapter_result_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={result['pm50_top10_span_overlap_count']})")


if __name__ == "__main__":
    main()
