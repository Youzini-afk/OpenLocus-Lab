#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10y_n1_span_surface_span_level_utility_result_audit.v1"
PHASE = "BEA-v1-N10Y N1 Span-Surface Span-Level Utility Result Audit"
GENERATED_BY = "bea_v1_n10y_n1_span_surface_span_level_utility_result_audit"
STATUS_COMPLETE = "n1_span_surface_span_level_utility_result_audit_complete"

STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10y_required_inputs_unavailable",
    "no_go_n10y_n10x_result_invalid",
    "no_go_n10y_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit_report.json")
INPUTS = {
    "n10x_span_level_validation_artifact": (Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json"), "n1_span_surface_span_level_utility_validation_complete_below_threshold"),
    "n10w_proxy_replication_package_artifact": (Path("artifacts/bea_v1_n10w_n1_span_surface_proxy_replication_package/bea_v1_n10w_n1_span_surface_proxy_replication_package_report.json"), "n1_span_surface_proxy_replication_package_complete"),
    "n10v_independent_recompute_artifact": (Path("artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json"), "independent_recompute_n1_span_surface_proxy_pass_n10w_authorized"),
    "n10t_proxy_validation_artifact": (Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json"), "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"),
}
EXPECTED = {
    "denominator": 213,
    "reachable_file": 52,
    "span_reachable": 12,
    "best_arm": "span_extra_depth_promote_before_primary_prefix_4",
    "best_span_top10": 9,
    "best_span_top20": 10,
    "best_file_top10": 34,
    "best_file_top20": 44,
    "delta": 9,
    "regressions": 0,
    "delta_threshold": 11,
    "regression_threshold": 3,
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
    "audit_bucket", "best_arm_bucket", "threshold_bucket", "decision_bucket", "interpretation_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "recommendation_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation",
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
    records = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10yin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def result_audit_records(n10x: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    den = (n10x.get("span_evaluable_denominator_records") or [{}])[0]
    th = (n10x.get("threshold_decision_records") or [{}])[0]
    schema = (n10x.get("span_gold_schema_records") or [{}])[0]
    ok = (
        n10x.get("status") == "n1_span_surface_span_level_utility_validation_complete_below_threshold"
        and den.get("span_evaluable_denominator_count") == EXPECTED["denominator"]
        and den.get("reachable_file_count") == EXPECTED["reachable_file"]
        and den.get("span_reachable_count") == EXPECTED["span_reachable"]
        and th.get("best_arm_bucket") == EXPECTED["best_arm"]
        and th.get("best_span_overlap_top10_count") == EXPECTED["best_span_top10"]
        and th.get("best_span_overlap_top20_count") == EXPECTED["best_span_top20"]
        and th.get("best_file_top10_count") == EXPECTED["best_file_top10"]
        and th.get("best_file_top20_count") == EXPECTED["best_file_top20"]
        and th.get("best_delta_span_overlap_top10_vs_baseline") == EXPECTED["delta"]
        and th.get("best_case_regression_count_vs_baseline") == EXPECTED["regressions"]
        and schema.get("fallback_to_file_level_used_bool") is False
    )
    return [{"anonymous_result_audit_id": "n10yresult0000", "audit_bucket": "n10x_below_threshold_span_level_result", "span_evaluable_denominator_count": int(den.get("span_evaluable_denominator_count", -1)), "reachable_file_count": int(den.get("reachable_file_count", -1)), "span_reachable_count": int(den.get("span_reachable_count", -1)), "best_arm_bucket": str(th.get("best_arm_bucket", "")), "best_span_overlap_top10_count": int(th.get("best_span_overlap_top10_count", -1)), "best_span_overlap_top20_count": int(th.get("best_span_overlap_top20_count", -1)), "best_file_top10_count": int(th.get("best_file_top10_count", -1)), "best_file_top20_count": int(th.get("best_file_top20_count", -1)), "best_delta_span_overlap_top10_vs_baseline": int(th.get("best_delta_span_overlap_top10_vs_baseline", -1)), "best_case_regression_count_vs_baseline": int(th.get("best_case_regression_count_vs_baseline", -1)), "fallback_to_file_level_used_bool": bool(schema.get("fallback_to_file_level_used_bool", True)), "result_audit_valid_bool": ok}], ok


def threshold_audit_records(n10x: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    th = (n10x.get("threshold_decision_records") or [{}])[0]
    ok = th.get("delta_span_overlap_top10_threshold") == EXPECTED["delta_threshold"] and th.get("case_regression_threshold") == EXPECTED["regression_threshold"] and th.get("best_delta_span_overlap_top10_vs_baseline") == EXPECTED["delta"] and th.get("best_case_regression_count_vs_baseline") == EXPECTED["regressions"] and th.get("threshold_passed_bool") is False
    return [{"anonymous_threshold_audit_id": "n10ythreshold0000", "threshold_bucket": "delta_span_overlap_top10_ge_max_5_or_5pct_and_regressions_le_1pct", "decision_bucket": "complete_below_threshold_confirmed" if ok else "threshold_invalid", "delta_span_overlap_top10_threshold": int(th.get("delta_span_overlap_top10_threshold", -1)), "case_regression_threshold": int(th.get("case_regression_threshold", -1)), "observed_delta_span_overlap_top10_vs_baseline": int(th.get("best_delta_span_overlap_top10_vs_baseline", -1)), "observed_case_regression_count_vs_baseline": int(th.get("best_case_regression_count_vs_baseline", -1)), "threshold_passed_bool": bool(th.get("threshold_passed_bool", True)), "threshold_audit_valid_bool": ok}], ok


def boundary_interpretation_records(result_ok: bool, threshold_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_boundary_interpretation_id": "n10yboundary0000", "interpretation_bucket": "file_level_proxy_gain_does_not_pass_span_level_utility_gate", "complete_below_threshold_result_bool": result_ok and threshold_ok, "infrastructure_failure_bool": False, "file_level_proxy_improvement_bool": True, "span_level_utility_gate_passed_bool": False, "promotion_or_method_winner_supported_bool": False}]


def privacy_boundary_records(n10x: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    privacy = (n10x.get("privacy_boundary_records") or [{}])[0]
    ok = privacy.get("privacy_boundary_complete_bool") is True and all(privacy.get(k) is False for k in ("private_path_public_bool", "private_filename_public_bool", "private_content_public_bool", "candidate_list_public_bool", "gold_path_public_bool", "gold_line_public_bool", "exact_rank_public_bool", "span_public_bool", "snippet_public_bool", "hash_public_bool", "provider_payload_public_bool"))
    return [{"anonymous_privacy_boundary_id": "n10yprivacy0000", "privacy_boundary_bucket": "public_audit_no_private_or_span_detail_leak", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": ok}], ok


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10ynoexec0000", "no_execution_boundary_bucket": "public_artifact_audit_no_private_read_no_recompute", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_complete_bool": True}], True


def next_step_recommendation_records() -> list[dict[str, Any]]:
    return [{"anonymous_next_step_recommendation_id": "n10ynext0000", "recommendation_bucket": "span_level_failure_decomposition_preflight", "next_allowed_phase": "BEA-v1-N10Z Span-Level Failure Decomposition Preflight", "next_allowed_scope_bucket": "preflight_only_no_execution", "n10z_preflight_authorized_bool": True, "private_read_authorized_bool": False, "execution_authorized_bool": False, "recompute_authorized_bool": False, "promotion_authorized_bool": False}]


def gate_records(input_ok: bool, result_ok: bool, threshold_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("n10x_result_valid", result_ok, int(result_ok), 1), ("threshold_below_confirmed", threshold_ok, int(threshold_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10z_preflight_authorized" if complete else "n10z_not_authorized", "next_allowed_phase": "BEA-v1-N10Z Span-Level Failure Decomposition Preflight" if complete else "none_until_valid_n10x_span_level_result_exists", "next_allowed_scope_bucket": "preflight_only_no_execution" if complete else "no_next_phase", "n10z_preflight_authorized": complete, "private_read_authorized": False, "recompute_authorized": False, "execution_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "openlocus_execution_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "counterfactual_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, result_ok: bool, threshold_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10y_required_inputs_unavailable"
    if not result_ok or not threshold_ok:
        return "no_go_n10y_n10x_result_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10y_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    n10x = artifacts.get("n10x_span_level_validation_artifact", {})
    result_records, result_ok = result_audit_records(n10x)
    threshold_records, threshold_ok = threshold_audit_records(n10x)
    privacy_records, privacy_ok = privacy_boundary_records(n10x)
    noexec_records, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, result_ok, threshold_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_audit_of_below_threshold_span_level_result", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "result_audit_records": result_records, "threshold_audit_records": threshold_records, "boundary_interpretation_records": boundary_interpretation_records(result_ok, threshold_ok), "privacy_boundary_records": privacy_records, "no_execution_records": noexec_records, "next_step_recommendation_records": next_step_recommendation_records(), "gate_records": gate_records(input_ok, result_ok, threshold_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["gate_records"] = gate_records(input_ok, result_ok, threshold_ok, privacy_ok, noexec_ok, scanner_ok)
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
    inputs, artifacts, input_ok = input_artifact_records()
    n10x = artifacts.get("n10x_span_level_validation_artifact", {})
    result_records, result_ok = result_audit_records(n10x)
    threshold_records, threshold_ok = threshold_audit_records(n10x)
    privacy_records, privacy_ok = privacy_boundary_records(n10x)
    noexec_records, noexec_ok = no_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10y_required_inputs_unavailable", "no_go_n10y_n10x_result_invalid", "no_go_n10y_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 4),
        check("result", result_ok and result_records[0]["span_evaluable_denominator_count"] == 213 and result_records[0]["best_span_overlap_top10_count"] == 9),
        check("threshold", threshold_ok and threshold_records[0]["threshold_passed_bool"] is False and threshold_records[0]["delta_span_overlap_top10_threshold"] == 11),
        check("interpretation", boundary_interpretation_records(True, True)[0]["infrastructure_failure_bool"] is False and boundary_interpretation_records(True, True)[0]["span_level_utility_gate_passed_bool"] is False),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["gold_line_public_bool"] is False),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("next_step", next_step_recommendation_records()[0]["n10z_preflight_authorized_bool"] is True and next_step_recommendation_records()[0]["execution_authorized_bool"] is False),
        check("stop_go", stop_go_records(True)[0]["n10z_preflight_authorized"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10Y N1 span-surface span-level utility result audit")
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
    res = report["result_audit_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, best_span_top10={res['best_span_overlap_top10_count']})")


if __name__ == "__main__":
    main()
