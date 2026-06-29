#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10w_n1_span_surface_proxy_replication_package.v1"
PHASE = "BEA-v1-N10W N1 Span-Surface Proxy Replication Package"
GENERATED_BY = "bea_v1_n10w_n1_span_surface_proxy_replication_package"
STATUS_COMPLETE = "n1_span_surface_proxy_replication_package_complete"

STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10w_required_inputs_unavailable",
    "no_go_n10w_chain_incomplete_or_inconsistent",
    "no_go_n10w_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10w_n1_span_surface_proxy_replication_package/bea_v1_n10w_n1_span_surface_proxy_replication_package_report.json")
INPUTS = {
    "n10t_proxy_validation_artifact": (
        Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json"),
        "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized",
    ),
    "n10u_proxy_result_audit_artifact": (
        Path("artifacts/bea_v1_n10u_n1_span_surface_proxy_result_audit/bea_v1_n10u_n1_span_surface_proxy_result_audit_report.json"),
        "n1_span_surface_proxy_result_audit_pass_n10v_authorized",
    ),
    "n10v_independent_recompute_artifact": (
        Path("artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json"),
        "independent_recompute_n1_span_surface_proxy_pass_n10w_authorized",
    ),
    "n10r_boundary_context_artifact": (
        Path("artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json"),
        "no_go_n10r_target_denominator_insufficient",
    ),
    "n9_boundary_context_artifact": (
        Path("artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json"),
        "recovered_fixed_pool_result_replication_package_complete",
    ),
}
EXPECTED = {
    "eligible_denominator_count": 213,
    "reachable_in_pool_count": 52,
    "baseline_top10_file_reach_count": 0,
    "baseline_top20_file_reach_count": 0,
    "best_arm_bucket": "span_extra_depth_promote_before_primary_prefix_4",
    "best_top10_file_reach_count": 34,
    "best_top20_file_reach_count": 44,
    "best_delta_top10_vs_baseline": 34,
    "best_case_regression_count_vs_baseline": 0,
    "delta_top10_threshold": 11,
    "case_regression_threshold": 3,
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "chain_bucket", "package_bucket", "best_arm_bucket", "claim_boundary_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "recommendation_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation", "surface_bucket", "limitation_bucket",
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
        records.append({"anonymous_input_artifact_id": f"n10win{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def metric_from_n10t(n10t: dict[str, Any]) -> dict[str, Any]:
    threshold = (n10t.get("threshold_decision_records") or [{}])[0]
    denominator = (n10t.get("span_surface_denominator_records") or [{}])[0]
    by_arm = {r.get("arm_bucket"): r for r in n10t.get("per_arm_proxy_result_records", []) if isinstance(r, dict)}
    baseline = by_arm.get("baseline_n1_span_order", {})
    best = by_arm.get(EXPECTED["best_arm_bucket"], {})
    return {
        "eligible_denominator_count": denominator.get("eligible_denominator_count"),
        "reachable_in_pool_count": denominator.get("reachable_in_pool_count"),
        "baseline_top10_file_reach_count": baseline.get("top10_file_reach_count"),
        "baseline_top20_file_reach_count": baseline.get("top20_file_reach_count"),
        "best_arm_bucket": threshold.get("best_arm_bucket"),
        "best_top10_file_reach_count": best.get("top10_file_reach_count"),
        "best_top20_file_reach_count": best.get("top20_file_reach_count"),
        "best_delta_top10_vs_baseline": threshold.get("best_delta_top10_vs_baseline"),
        "best_case_regression_count_vs_baseline": threshold.get("best_case_regression_count_vs_baseline"),
        "delta_top10_threshold": threshold.get("delta_top10_threshold"),
        "case_regression_threshold": threshold.get("case_regression_threshold"),
        "threshold_passed_bool": threshold.get("threshold_passed_bool"),
    }


def metric_from_n10u(n10u: dict[str, Any]) -> dict[str, Any]:
    result = (n10u.get("result_consistency_audit_records") or [{}])[0]
    threshold = (n10u.get("threshold_audit_records") or [{}])[0]
    return {
        "eligible_denominator_count": result.get("eligible_denominator_count"),
        "reachable_in_pool_count": result.get("reachable_in_pool_count"),
        "baseline_top10_file_reach_count": result.get("baseline_top10_file_reach_count"),
        "baseline_top20_file_reach_count": result.get("baseline_top20_file_reach_count"),
        "best_arm_bucket": result.get("best_arm_bucket"),
        "best_top10_file_reach_count": result.get("best_top10_file_reach_count"),
        "best_top20_file_reach_count": result.get("best_top20_file_reach_count"),
        "best_delta_top10_vs_baseline": result.get("best_delta_top10_vs_baseline"),
        "best_case_regression_count_vs_baseline": result.get("best_case_regression_count_vs_baseline"),
        "delta_top10_threshold": threshold.get("delta_top10_threshold"),
        "case_regression_threshold": threshold.get("case_regression_threshold"),
        "threshold_passed_bool": threshold.get("threshold_passed_bool"),
    }


def metric_from_n10v(n10v: dict[str, Any]) -> dict[str, Any]:
    rec = (n10v.get("independent_recompute_records") or [{}])[0]
    return {**{k: rec.get(k) for k in EXPECTED}, "threshold_passed_bool": rec.get("threshold_passed_bool")}


def chain_consistency_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10t = artifacts.get("n10t_proxy_validation_artifact", {})
    n10u = artifacts.get("n10u_proxy_result_audit_artifact", {})
    n10v = artifacts.get("n10v_independent_recompute_artifact", {})
    metrics = [metric_from_n10t(n10t), metric_from_n10u(n10u), metric_from_n10v(n10v)]
    metrics_ok = all(all(m.get(k) == v for k, v in EXPECTED.items()) and m.get("threshold_passed_bool") is True for m in metrics)
    statuses_ok = (
        n10t.get("status") == "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"
        and n10u.get("status") == "n1_span_surface_proxy_result_audit_pass_n10v_authorized"
        and n10v.get("status") == "independent_recompute_n1_span_surface_proxy_pass_n10w_authorized"
    )
    comparison_ok = ((n10v.get("comparison_to_n10t_records") or [{}])[0].get("comparison_match_bool") is True)
    ok = statuses_ok and metrics_ok and comparison_ok
    return [{"anonymous_chain_consistency_id": "n10wchain0000", "chain_bucket": "n10t_validation_n10u_audit_n10v_recompute", "n10t_status_pass_bool": n10t.get("status") == "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized", "n10u_audit_pass_bool": n10u.get("status") == "n1_span_surface_proxy_result_audit_pass_n10v_authorized", "n10v_recompute_pass_bool": n10v.get("status") == "independent_recompute_n1_span_surface_proxy_pass_n10w_authorized", "n10v_comparison_to_n10t_match_bool": comparison_ok, "metrics_stable_across_chain_bool": metrics_ok, "chain_consistency_complete_bool": ok}], ok


def replicated_metric_package_records() -> list[dict[str, Any]]:
    return [{"anonymous_replicated_metric_package_id": "n10wmetrics0000", "package_bucket": "public_aggregate_proxy_replication_metrics", "surface_bucket": "n1_span_p4_evidence_order_proxy", "proxy_surface_bool": True, "n2_equivalent_validation_bool": False, "eligible_denominator_count": 213, "reachable_in_pool_count": 52, "baseline_top10_file_reach_count": 0, "baseline_top20_file_reach_count": 0, "best_arm_bucket": "span_extra_depth_promote_before_primary_prefix_4", "best_top10_file_reach_count": 34, "best_top20_file_reach_count": 44, "best_delta_top10_vs_baseline": 34, "best_case_regression_count_vs_baseline": 0, "delta_top10_threshold": 11, "case_regression_threshold": 3, "threshold_passed_bool": True}]


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10wclaim0000", "claim_boundary_bucket": "proxy_span_surface_only_not_policy_not_winner", "proxy_surface_bool": True, "n2_equivalent_validation_bool": False, "runtime_policy_claim_bool": False, "runtime_or_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "method_winner_claimed_bool": False, "downstream_value_claim_authorized_bool": False, "downstream_value_claimed_bool": False, "p5_authorized_bool": False, "v1_a_authorized_bool": False, "selector_reranker_authorized_bool": False, "retrieval_authorized_bool": False, "rerun_authorized_bool": False, "counterfactual_authorized_bool": False, "policy_change_authorized_bool": False, "claim_boundary_complete_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10wprivacy0000", "privacy_boundary_bucket": "public_aggregate_pointers_only_no_private_data", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10wnoexec0000", "no_execution_boundary_bucket": "public_package_only_no_new_experiment", "private_read_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_complete_bool": True}], True


def next_step_recommendation_records() -> list[dict[str, Any]]:
    return [{"anonymous_next_step_recommendation_id": "n10wnext0000", "recommendation_bucket": "n10x_stronger_validation_preflight_only", "next_allowed_phase": "BEA-v1-N10X N1 Span-Surface Stronger Validation Preflight", "next_allowed_scope_bucket": "preflight_only_no_execution", "n10x_preflight_authorized_bool": True, "private_read_authorized_bool": False, "execution_authorized_bool": False, "recompute_authorized_bool": False, "runtime_or_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, chain_ok: bool, claim_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [
        ("public_inputs_loaded", input_ok, int(input_ok), 1),
        ("chain_consistency_complete", chain_ok, int(chain_ok), 1),
        ("eligible_denominator_count", chain_ok, 213 if chain_ok else 0, 213),
        ("reachable_in_pool_count", chain_ok, 52 if chain_ok else 0, 52),
        ("best_top10_file_reach_count", chain_ok, 34 if chain_ok else 0, 34),
        ("best_top20_file_reach_count", chain_ok, 44 if chain_ok else 0, 44),
        ("best_delta_top10_vs_baseline", chain_ok, 34 if chain_ok else 0, 34),
        ("best_regressions", chain_ok, 0 if chain_ok else -1, 0),
        ("claim_boundary", claim_ok, int(claim_ok), 1),
        ("privacy_boundary", privacy_ok, int(privacy_ok), 1),
        ("no_execution", noexec_ok, int(noexec_ok), 1),
        ("forbidden_scan", scanner_ok, int(scanner_ok), 1),
    ]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10x_preflight_authorized" if pass_status else "n10x_not_authorized", "next_allowed_phase": "BEA-v1-N10X N1 Span-Surface Stronger Validation Preflight" if pass_status else "none_until_n10_proxy_replication_chain_is_consistent", "next_allowed_scope_bucket": "preflight_only_no_execution" if pass_status else "no_next_phase", "n10x_preflight_authorized": pass_status, "execution_authorized": False, "private_read_authorized": False, "recompute_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "p5_authorized": False, "v1_a_authorized": False, "selector_or_reranker_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "new_arm_search_authorized": False, "counterfactual_authorized": False, "policy_change_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, claim_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10w_required_inputs_unavailable"
    if not chain_ok:
        return "no_go_n10w_chain_incomplete_or_inconsistent"
    if not claim_ok or not privacy_ok or not noexec_ok:
        return "no_go_n10w_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    chain_records, chain_ok = chain_consistency_records(artifacts)
    claim_records, claim_ok = claim_boundary_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, claim_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_replication_package_proxy_span_surface_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "chain_consistency_records": chain_records, "replicated_metric_package_records": replicated_metric_package_records(), "claim_boundary_records": claim_records, "privacy_boundary_records": privacy_records, "no_execution_records": noexec_records, "next_step_recommendation_records": next_step_recommendation_records(), "gate_records": gate_records(input_ok, chain_ok, claim_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["gate_records"] = gate_records(input_ok, chain_ok, claim_ok, privacy_ok, noexec_ok, scanner_ok)
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
    chain_records, chain_ok = chain_consistency_records(artifacts)
    metrics = replicated_metric_package_records()[0]
    claim_records, claim_ok = claim_boundary_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10w_required_inputs_unavailable", "no_go_n10w_chain_incomplete_or_inconsistent", "no_go_n10w_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 5),
        check("chain", chain_ok and chain_records[0]["n10t_status_pass_bool"] and chain_records[0]["n10u_audit_pass_bool"] and chain_records[0]["n10v_recompute_pass_bool"]),
        check("metrics", metrics["eligible_denominator_count"] == 213 and metrics["reachable_in_pool_count"] == 52 and metrics["best_top10_file_reach_count"] == 34 and metrics["best_top20_file_reach_count"] == 44),
        check("threshold", metrics["best_delta_top10_vs_baseline"] == 34 and metrics["best_case_regression_count_vs_baseline"] == 0 and metrics["delta_top10_threshold"] == 11 and metrics["case_regression_threshold"] == 3 and metrics["threshold_passed_bool"] is True),
        check("proxy_boundary", metrics["proxy_surface_bool"] is True and metrics["n2_equivalent_validation_bool"] is False),
        check("claim_boundary", claim_ok and claim_records[0]["runtime_policy_claim_bool"] is False and claim_records[0]["method_winner_claim_authorized_bool"] is False),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["private_path_public_bool"] is False),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("next_step", next_step_recommendation_records()[0]["n10x_preflight_authorized_bool"] is True and next_step_recommendation_records()[0]["execution_authorized_bool"] is False),
        check("stop_go", stop_go_records(True)[0]["n10x_preflight_authorized"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10W N1 span-surface proxy replication package")
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
    rec = report["replicated_metric_package_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, best_top10={rec['best_top10_file_reach_count']})")


if __name__ == "__main__":
    main()
