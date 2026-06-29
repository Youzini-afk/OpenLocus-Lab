#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package.v1"
PHASE = "BEA-v1-N10AP Adapter-Enabled Variant Evaluator Result Audit Package"
STATUS_PASS = "adapter_enabled_variant_evaluator_result_audit_package_complete_n10aq_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10ap_required_public_inputs_unavailable",
    "no_go_n10ap_variant_chain_mismatch",
    "no_go_n10ap_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package_report.json")
INPUTS = {
    "n10ao_variant_evaluator_artifact": (Path("artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator_report.json"), "default_off_adapter_enabled_variant_evaluator_pass_n10ap_authorized"),
    "n10an_hook_feasibility_preflight_artifact": (Path("artifacts/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight_report.json"), "default_off_existing_evaluator_hook_feasibility_preflight_pass_n10ao_authorized"),
    "n10am_adapter_integration_audit_package_artifact": (Path("artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json"), "eval_only_adapter_integration_result_audit_package_complete_n10an_authorized"),
    "n10al_adapter_integration_smoke_artifact": (Path("artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json"), "scoped_eval_only_adapter_integration_smoke_pass_n10am_authorized"),
    "n10aj_adapter_patch_artifact": (Path("artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json"), "default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized"),
}
EXPECTED = {
    "private_span_rows_read": 213,
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
    "variant_chain_bucket", "variant_result_bucket", "default_off_claim_bucket", "forbidden_claim_bucket",
    "no_private_recompute_bucket", "n10aq_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
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
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10apin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def variant_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ao = artifacts.get("n10ao_variant_evaluator_artifact", {})
    n10an = artifacts.get("n10an_hook_feasibility_preflight_artifact", {})
    n10am = artifacts.get("n10am_adapter_integration_audit_package_artifact", {})
    n10al = artifacts.get("n10al_adapter_integration_smoke_artifact", {})
    n10aj = artifacts.get("n10aj_adapter_patch_artifact", {})
    strategy = (n10an.get("hook_strategy_decision_records") or [{}])[0]
    enable = (n10ao.get("explicit_enablement_records") or [{}])[0]
    default = (n10ao.get("default_off_mode_records") or [{}])[0]
    compare = (n10ao.get("comparison_to_n10al_records") or [{}])[0]
    touch = (n10ao.get("forbidden_code_touch_records") or [{}])[-1]
    ok = (
        n10ao.get("status") == INPUTS["n10ao_variant_evaluator_artifact"][1]
        and n10an.get("status") == INPUTS["n10an_hook_feasibility_preflight_artifact"][1]
        and n10am.get("status") == INPUTS["n10am_adapter_integration_audit_package_artifact"][1]
        and n10al.get("status") == INPUTS["n10al_adapter_integration_smoke_artifact"][1]
        and n10aj.get("status") == INPUTS["n10aj_adapter_patch_artifact"][1]
        and strategy.get("selected_strategy_bucket") == "new_adapter_enabled_variant_evaluator"
        and strategy.get("modify_existing_validated_evaluator_bool") is False
        and enable.get("explicit_enablement_used_bool") is True
        and default.get("default_enabled_bool") is False
        and default.get("private_read_by_default_bool") is False
        and compare.get("comparison_passed_bool") is True
        and touch.get("existing_evaluator_imported_bool") is False
    )
    return [{"anonymous_variant_chain_id": "n10apchain0000", "variant_chain_bucket": "n10an_strategy_n10ao_variant_n10al_match", "n10ao_status_valid_bool": n10ao.get("status") == INPUTS["n10ao_variant_evaluator_artifact"][1], "n10an_strategy_valid_bool": strategy.get("selected_strategy_bucket") == "new_adapter_enabled_variant_evaluator", "n10am_status_valid_bool": n10am.get("status") == INPUTS["n10am_adapter_integration_audit_package_artifact"][1], "n10al_status_valid_bool": n10al.get("status") == INPUTS["n10al_adapter_integration_smoke_artifact"][1], "n10aj_status_valid_bool": n10aj.get("status") == INPUTS["n10aj_adapter_patch_artifact"][1], "explicit_enablement_used_bool": enable.get("explicit_enablement_used_bool") is True, "default_enabled_bool": bool(default.get("default_enabled_bool", True)), "private_read_by_default_bool": bool(default.get("private_read_by_default_bool", True)), "modify_existing_validated_evaluator_bool": bool(strategy.get("modify_existing_validated_evaluator_bool", True)), "existing_evaluator_imported_bool": bool(touch.get("existing_evaluator_imported_bool", True)), "comparison_to_n10al_passed_bool": compare.get("comparison_passed_bool") is True, "variant_chain_valid_bool": ok}], ok


def variant_result_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ao = artifacts.get("n10ao_variant_evaluator_artifact", {})
    result = (n10ao.get("adapter_variant_result_records") or [{}])[0]
    ok = (
        result.get("private_span_rows_read") == 213
        and result.get("eligible_denominator_count") == 213
        and result.get("baseline_top10_span_overlap_count") == 9
        and result.get("baseline_top20_span_overlap_count") == 10
        and result.get("pm50_top10_span_overlap_count") == 19
        and result.get("pm50_top20_span_overlap_count") == 23
        and result.get("delta_top10_vs_baseline_count") == 10
        and result.get("original_span_hit_lost_count") == 0
        and result.get("candidate_pool_changed_bool") is False
        and result.get("order_changed_bool") is False
    )
    return [{"anonymous_variant_result_id": "n10apresult0000", "variant_result_bucket": "new_eval_only_variant_reproduces_scoped_n1_pm50_aggregate", "private_span_rows_read": int(result.get("private_span_rows_read", 0)), "eligible_denominator_count": int(result.get("eligible_denominator_count", 0)), "baseline_top10_span_overlap_count": int(result.get("baseline_top10_span_overlap_count", 0)), "baseline_top20_span_overlap_count": int(result.get("baseline_top20_span_overlap_count", 0)), "pm50_top10_span_overlap_count": int(result.get("pm50_top10_span_overlap_count", 0)), "pm50_top20_span_overlap_count": int(result.get("pm50_top20_span_overlap_count", 0)), "delta_top10_vs_baseline_count": int(result.get("delta_top10_vs_baseline_count", 0)), "original_span_hit_lost_count": int(result.get("original_span_hit_lost_count", 0)), "candidate_pool_changed_bool": bool(result.get("candidate_pool_changed_bool", True)), "order_changed_bool": bool(result.get("order_changed_bool", True)), "variant_result_valid_bool": ok}], ok


def default_off_claim_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_default_off_claim_id": "n10apdefault0000", "default_off_claim_bucket": "explicit_enablement_only_default_off_variant", "allowed_claim_bool": True, "default_enabled_bool": False, "private_read_by_default_bool": False, "metric_recompute_by_default_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_enablement_bool": False, "default_off_claim_valid_bool": True}], True


def forbidden_claim_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_forbidden_claim_id": "n10apclaim0000", "forbidden_claim_bucket": "no_runtime_no_existing_hook_no_generalization_claims", "runtime_default_promotion_claim_bool": False, "existing_evaluator_hook_in_claim_bool": False, "modify_existing_validator_claim_bool": False, "retrieval_rerun_claim_bool": False, "candidate_generation_claim_bool": False, "new_window_tuning_claim_bool": False, "selector_reranker_claim_bool": False, "p5_v1a_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_private_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_private_recompute_id": "n10apnoexec0000", "no_private_recompute_bucket": "public_audit_package_only_no_private_read_no_recompute", "private_read_count": 0, "private_scan_count": 0, "empirical_recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "new_arm_or_window_tuning_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0, "existing_evaluator_hook_in_count": 0, "no_private_recompute_valid_bool": True}], True


def n10aq_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10aq_handoff_id": "n10aphandoff0000", "n10aq_handoff_bucket": "n10aq_heldout_external_validation_source_discovery_preflight_authorized" if complete else "n10aq_not_authorized", "n10aq_public_source_discovery_preflight_authorized_bool": complete, "direct_experiment_execution_authorized_bool": False, "private_read_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, chain_ok: bool, result_ok: bool, default_ok: bool, claim_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("variant_chain", chain_ok), ("variant_result", result_ok), ("default_off_claim", default_ok), ("forbidden_claim_boundary", claim_ok), ("no_private_recompute", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": int(passed), "threshold_value": 1} for name, passed in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10aq_public_source_discovery_preflight_authorized" if complete else "n10aq_not_authorized", "next_allowed_phase": "BEA-v1-N10AQ Heldout External Validation Source-Discovery Preflight" if complete else "none_until_variant_chain_valid", "next_allowed_scope_bucket": "public_source_discovery_preflight_only" if complete else "no_next_phase", "n10aq_preflight_authorized": complete, "direct_experiment_execution_authorized": False, "private_read_authorized": False, "existing_evaluator_hook_in_authorized": False, "modify_existing_validated_evaluator_authorized": False, "runtime_or_default_enablement_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "new_arm_or_window_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, result_ok: bool, default_ok: bool, claim_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ap_required_public_inputs_unavailable"
    if not chain_ok or not result_ok:
        return "no_go_n10ap_variant_chain_mismatch"
    if not default_ok or not claim_ok or not noexec_ok:
        return "no_go_n10ap_claim_boundary_invalid"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = variant_chain_records(artifacts)
    result_rows, result_ok = variant_result_records(artifacts)
    default_rows, default_ok = default_off_claim_records()
    claim_rows, claim_ok = forbidden_claim_records()
    noexec_rows, noexec_ok = no_private_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, result_ok, default_ok, claim_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_adapter_enabled_variant_result_audit_package_only", "generated_by": "bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "variant_chain_records": chain_rows, "variant_result_records": result_rows, "default_off_claim_records": default_rows, "forbidden_claim_records": claim_rows, "no_private_recompute_records": noexec_rows, "n10aq_handoff_records": n10aq_handoff_records(complete), "gate_records": gate_records(input_ok, chain_ok, result_ok, default_ok, claim_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, chain_ok, result_ok, default_ok, claim_ok, noexec_ok, scanner_ok)
    report["n10aq_handoff_records"] = n10aq_handoff_records(complete)
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
    chain_rows, chain_ok = variant_chain_records(artifacts)
    result_rows, result_ok = variant_result_records(artifacts)
    default_rows, default_ok = default_off_claim_records()
    claim_rows, claim_ok = forbidden_claim_records()
    noexec_rows, noexec_ok = no_private_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10ap_required_public_inputs_unavailable", "no_go_n10ap_variant_chain_mismatch", "no_go_n10ap_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 5),
        check("chain", chain_ok and chain_rows[0]["explicit_enablement_used_bool"] is True and chain_rows[0]["default_enabled_bool"] is False),
        check("strategy", chain_rows[0]["n10an_strategy_valid_bool"] is True and chain_rows[0]["modify_existing_validated_evaluator_bool"] is False),
        check("result", result_ok and result_rows[0]["private_span_rows_read"] == 213 and result_rows[0]["pm50_top10_span_overlap_count"] == 19),
        check("candidate_order", result_rows[0]["candidate_pool_changed_bool"] is False and result_rows[0]["order_changed_bool"] is False),
        check("default_claim", default_ok and default_rows[0]["private_read_by_default_bool"] is False and default_rows[0]["runtime_default_enablement_bool"] is False),
        check("forbidden_claims", claim_ok and claim_rows[0]["runtime_default_promotion_claim_bool"] is False and claim_rows[0]["downstream_value_claim_bool"] is False),
        check("no_private_recompute", noexec_ok and noexec_rows[0]["private_read_count"] == 0 and noexec_rows[0]["empirical_recompute_count"] == 0),
        check("handoff", n10aq_handoff_records(True)[0]["n10aq_public_source_discovery_preflight_authorized_bool"] is True and stop_go_records(True)[0]["direct_experiment_execution_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AP adapter-enabled variant evaluator result audit package")
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
    result = report["variant_result_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={result['pm50_top10_span_overlap_count']})")


if __name__ == "__main__":
    main()
