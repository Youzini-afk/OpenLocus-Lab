#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10u_n1_span_surface_proxy_result_audit.v1"
PHASE = "BEA-v1-N10U N1 Span-Surface Proxy Result Audit"
GENERATED_BY = "bea_v1_n10u_n1_span_surface_proxy_result_audit"
STATUS_PASS = "n1_span_surface_proxy_result_audit_pass_n10v_authorized"

STATUSES = (
    STATUS_PASS,
    "no_go_n10u_required_inputs_unavailable",
    "no_go_n10u_n10t_not_pass",
    "no_go_n10u_proxy_boundary_invalid",
    "no_go_n10u_result_consistency_invalid",
    "no_go_n10u_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10u_n1_span_surface_proxy_result_audit/bea_v1_n10u_n1_span_surface_proxy_result_audit_report.json")
INPUTS = {
    "n10t_proxy_validation_artifact": (
        Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json"),
        "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized",
    ),
    "n10r_preflight_artifact": (
        Path("artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json"),
        "no_go_n10r_target_denominator_insufficient",
    ),
    "n9_replication_package_artifact": (
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
    "surface_bucket", "audit_bucket", "best_arm_bucket", "threshold_bucket", "decision_bucket", "privacy_boundary_bucket",
    "claim_boundary_bucket", "no_execution_boundary_bucket", "n10v_handoff_bucket", "authorization", "next_allowed_phase",
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
        records.append({"anonymous_input_artifact_id": f"n10uin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def proxy_boundary_audit_records(n10t: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    claim_ok = n10t.get("claim_level") == "n1_span_surface_proxy_validation_only"
    semantics = n10t.get("span_arm_semantics_records", [])
    semantics_ok = len(semantics) == 4 and all(
        r.get("arm_semantics_bucket") == "n1_span_surface_fixed_pool_order_transform_only"
        and r.get("position_rule_bucket") == "original_position_le_20_primary_position_gt_20_extra_depth_no_gold_signal"
        and r.get("candidate_pool_changed_bool") is False
        and r.get("gold_used_for_ordering_bool") is False
        for r in semantics if isinstance(r, dict)
    )
    ok = claim_ok and semantics_ok
    return [{"anonymous_proxy_boundary_audit_id": "n10uboundary0000", "surface_bucket": "n1_span_p4_evidence_order_proxy", "audit_bucket": "proxy_surface_not_n2_equivalent", "proxy_surface_bool": True, "n2_equivalent_validation_bool": False, "runtime_policy_claim_bool": False, "fixed_pool_order_transform_only_bool": semantics_ok, "gold_only_after_ordering_bool": True, "proxy_boundary_valid_bool": ok}], ok


def result_consistency_audit_records(n10t: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    denominator = (n10t.get("span_surface_denominator_records") or [{}])[0]
    by_arm = {r.get("arm_bucket"): r for r in n10t.get("per_arm_proxy_result_records", []) if isinstance(r, dict)}
    subgroup = (n10t.get("subgroup_result_records") or [{}])[0]
    baseline = by_arm.get("baseline_n1_span_order", {})
    best = by_arm.get(EXPECTED["best_arm_bucket"], {})
    ok = (
        denominator.get("eligible_denominator_count") == EXPECTED["eligible_denominator_count"]
        and denominator.get("reachable_in_pool_count") == EXPECTED["reachable_in_pool_count"]
        and baseline.get("top10_file_reach_count") == EXPECTED["baseline_top10_file_reach_count"]
        and baseline.get("top20_file_reach_count") == EXPECTED["baseline_top20_file_reach_count"]
        and subgroup.get("best_arm_bucket") == EXPECTED["best_arm_bucket"]
        and best.get("top10_file_reach_count") == EXPECTED["best_top10_file_reach_count"]
        and best.get("top20_file_reach_count") == EXPECTED["best_top20_file_reach_count"]
        and best.get("delta_top10_vs_baseline") == EXPECTED["best_delta_top10_vs_baseline"]
        and best.get("case_regression_count_vs_baseline") == EXPECTED["best_case_regression_count_vs_baseline"]
    )
    return [{"anonymous_result_consistency_audit_id": "n10uresult0000", "audit_bucket": "n10t_public_result_consistency", "eligible_denominator_count": int(denominator.get("eligible_denominator_count", -1)), "reachable_in_pool_count": int(denominator.get("reachable_in_pool_count", -1)), "baseline_top10_file_reach_count": int(baseline.get("top10_file_reach_count", -1)), "baseline_top20_file_reach_count": int(baseline.get("top20_file_reach_count", -1)), "best_arm_bucket": str(subgroup.get("best_arm_bucket", "")), "best_top10_file_reach_count": int(best.get("top10_file_reach_count", -1)), "best_top20_file_reach_count": int(best.get("top20_file_reach_count", -1)), "best_delta_top10_vs_baseline": int(best.get("delta_top10_vs_baseline", -1)), "best_case_regression_count_vs_baseline": int(best.get("case_regression_count_vs_baseline", -1)), "result_consistency_valid_bool": ok}], ok


def threshold_audit_records(n10t: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    threshold = (n10t.get("threshold_decision_records") or [{}])[0]
    ok = (
        threshold.get("delta_top10_threshold") == EXPECTED["delta_top10_threshold"]
        and threshold.get("case_regression_threshold") == EXPECTED["case_regression_threshold"]
        and threshold.get("best_delta_top10_vs_baseline") == EXPECTED["best_delta_top10_vs_baseline"]
        and threshold.get("best_case_regression_count_vs_baseline") == EXPECTED["best_case_regression_count_vs_baseline"]
        and threshold.get("threshold_passed_bool") is True
    )
    return [{"anonymous_threshold_audit_id": "n10uthreshold0000", "threshold_bucket": "delta_top10_ge_max_10_or_5pct_and_regressions_le_1pct", "decision_bucket": "threshold_audit_pass" if ok else "threshold_audit_invalid", "delta_top10_threshold": int(threshold.get("delta_top10_threshold", -1)), "case_regression_threshold": int(threshold.get("case_regression_threshold", -1)), "observed_delta_top10_vs_baseline": int(threshold.get("best_delta_top10_vs_baseline", -1)), "observed_case_regression_count_vs_baseline": int(threshold.get("best_case_regression_count_vs_baseline", -1)), "threshold_passed_bool": bool(threshold.get("threshold_passed_bool", False)), "threshold_audit_valid_bool": ok}], ok


def privacy_boundary_audit_records(n10t: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    privacy = (n10t.get("privacy_boundary_records") or [{}])[0]
    ok = privacy.get("privacy_boundary_complete_bool") is True and all(privacy.get(k) is False for k in ("private_path_public_bool", "candidate_list_public_bool", "gold_path_public_bool", "span_public_bool", "snippet_public_bool", "hash_public_bool", "provider_payload_public_bool"))
    return [{"anonymous_privacy_boundary_audit_id": "n10uprivacy0000", "privacy_boundary_bucket": "public_artifact_only_no_private_leak", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": ok}], ok


def claim_boundary_audit_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_audit_id": "n10uclaim0000", "claim_boundary_bucket": "proxy_result_audit_only_no_promotion_no_winner", "runtime_or_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "method_winner_claimed_bool": False, "downstream_value_claim_authorized_bool": False, "downstream_value_claimed_bool": False, "p5_authorized_bool": False, "v1_a_authorized_bool": False, "selector_reranker_authorized_bool": False, "retrieval_authorized_bool": False, "rerun_authorized_bool": False, "new_arm_search_authorized_bool": False, "counterfactual_authorized_bool": False, "policy_change_authorized_bool": False, "claim_boundary_valid_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10unoexec0000", "no_execution_boundary_bucket": "public_artifact_audit_no_private_read_no_recompute", "private_read_count": 0, "recompute_count": 0, "n10t_code_call_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "policy_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_complete_bool": True}], True


def n10v_handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10v_handoff_id": "n10uhandoff0000", "n10v_handoff_bucket": "n10v_independent_recompute_same_private_span_rows" if pass_status else "n10v_not_authorized", "n10v_independent_recompute_authorized_bool": pass_status, "n10v_same_private_span_rows_read_authorized_bool": pass_status, "broad_private_read_authorized_bool": False, "audit_or_recompute_scope_only_bool": pass_status, "runtime_or_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, status_ok: bool, proxy_ok: bool, result_ok: bool, threshold_ok: bool, privacy_ok: bool, claim_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [
        ("public_inputs_loaded", input_ok, int(input_ok), 1),
        ("n10t_status_pass", status_ok, int(status_ok), 1),
        ("proxy_boundary_valid", proxy_ok, int(proxy_ok), 1),
        ("eligible_denominator_count", result_ok, EXPECTED["eligible_denominator_count"] if result_ok else 0, EXPECTED["eligible_denominator_count"]),
        ("reachable_in_pool_count", result_ok, EXPECTED["reachable_in_pool_count"] if result_ok else 0, EXPECTED["reachable_in_pool_count"]),
        ("best_top10_file_reach_count", result_ok, EXPECTED["best_top10_file_reach_count"] if result_ok else 0, EXPECTED["best_top10_file_reach_count"]),
        ("best_top20_file_reach_count", result_ok, EXPECTED["best_top20_file_reach_count"] if result_ok else 0, EXPECTED["best_top20_file_reach_count"]),
        ("best_delta_top10_vs_baseline", result_ok, EXPECTED["best_delta_top10_vs_baseline"] if result_ok else 0, EXPECTED["best_delta_top10_vs_baseline"]),
        ("best_regressions", result_ok, EXPECTED["best_case_regression_count_vs_baseline"] if result_ok else -1, EXPECTED["best_case_regression_count_vs_baseline"]),
        ("threshold_passed", threshold_ok, int(threshold_ok), 1),
        ("privacy_boundary", privacy_ok, int(privacy_ok), 1),
        ("claim_boundary", claim_ok, int(claim_ok), 1),
        ("no_execution", noexec_ok, int(noexec_ok), 1),
        ("forbidden_scan", scanner_ok, int(scanner_ok), 1),
    ]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10v_independent_recompute_authorized" if pass_status else "n10v_not_authorized", "next_allowed_phase": "BEA-v1-N10V Independent Recompute N1 Span-Surface Proxy" if pass_status else "none_until_valid_n10t_proxy_result_audit_inputs_exist", "next_allowed_scope_bucket": "n10v_same_private_span_rows_proxy_recompute_only" if pass_status else "no_next_phase", "n10v_independent_recompute_authorized": pass_status, "n10v_same_private_span_rows_read_authorized": pass_status, "broad_private_read_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "p5_authorized": False, "v1_a_authorized": False, "selector_or_reranker_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "new_arm_search_authorized": False, "counterfactual_authorized": False, "policy_change_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, n10t_status_ok: bool, proxy_ok: bool, result_ok: bool, threshold_ok: bool, privacy_ok: bool, claim_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10u_required_inputs_unavailable"
    if not n10t_status_ok:
        return "no_go_n10u_n10t_not_pass"
    if not proxy_ok:
        return "no_go_n10u_proxy_boundary_invalid"
    if not result_ok or not threshold_ok:
        return "no_go_n10u_result_consistency_invalid"
    if not privacy_ok or not claim_ok or not noexec_ok:
        return "no_go_n10u_privacy_or_claim_boundary_invalid"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    n10t = artifacts.get("n10t_proxy_validation_artifact", {})
    n10t_status_ok = n10t.get("status") == "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"
    proxy_records, proxy_ok = proxy_boundary_audit_records(n10t)
    result_records, result_ok = result_consistency_audit_records(n10t)
    threshold_records, threshold_ok = threshold_audit_records(n10t)
    privacy_records, privacy_ok = privacy_boundary_audit_records(n10t)
    claim_records, claim_ok = claim_boundary_audit_records()
    noexec_records, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, n10t_status_ok, proxy_ok, result_ok, threshold_ok, privacy_ok, claim_ok, noexec_ok)
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_artifact_proxy_result_audit_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "proxy_boundary_audit_records": proxy_records, "result_consistency_audit_records": result_records, "threshold_audit_records": threshold_records, "privacy_boundary_audit_records": privacy_records, "claim_boundary_audit_records": claim_records, "no_execution_records": noexec_records, "n10v_handoff_records": n10v_handoff_records(pass_status), "gate_records": gate_records(input_ok, n10t_status_ok, proxy_ok, result_ok, threshold_ok, privacy_ok, claim_ok, noexec_ok, True), "stop_go_records": stop_go_records(pass_status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    pass_status = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, n10t_status_ok, proxy_ok, result_ok, threshold_ok, privacy_ok, claim_ok, noexec_ok, scanner_ok)
    report["n10v_handoff_records"] = n10v_handoff_records(pass_status)
    report["stop_go_records"] = stop_go_records(pass_status)
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
    n10t = artifacts.get("n10t_proxy_validation_artifact", {})
    n10t_status_ok = n10t.get("status") == "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"
    proxy_records, proxy_ok = proxy_boundary_audit_records(n10t)
    result_records, result_ok = result_consistency_audit_records(n10t)
    threshold_records, threshold_ok = threshold_audit_records(n10t)
    privacy_records, privacy_ok = privacy_boundary_audit_records(n10t)
    claim_records, claim_ok = claim_boundary_audit_records()
    noexec_records, noexec_ok = no_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10u_required_inputs_unavailable", "no_go_n10u_n10t_not_pass", "no_go_n10u_proxy_boundary_invalid", "no_go_n10u_result_consistency_invalid", "no_go_n10u_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 3),
        check("n10t_status", n10t_status_ok),
        check("proxy_boundary", proxy_ok and proxy_records[0]["surface_bucket"] == "n1_span_p4_evidence_order_proxy" and proxy_records[0]["n2_equivalent_validation_bool"] is False),
        check("result_consistency", result_ok and result_records[0]["eligible_denominator_count"] == 213 and result_records[0]["best_top10_file_reach_count"] == 34 and result_records[0]["best_top20_file_reach_count"] == 44),
        check("threshold", threshold_ok and threshold_records[0]["delta_top10_threshold"] == 11 and threshold_records[0]["case_regression_threshold"] == 3 and threshold_records[0]["threshold_passed_bool"] is True),
        check("privacy", privacy_ok and privacy_records[0]["private_path_public_bool"] is False and privacy_records[0]["span_public_bool"] is False),
        check("claim_boundary", claim_ok and claim_records[0]["p5_authorized_bool"] is False and claim_records[0]["method_winner_claim_authorized_bool"] is False),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("handoff", n10v_handoff_records(True)[0]["n10v_independent_recompute_authorized_bool"] is True and n10v_handoff_records(True)[0]["broad_private_read_authorized_bool"] is False),
        check("stop_go", stop_go_records(True)[0]["n10v_independent_recompute_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_promotion_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10U N1 span-surface proxy result audit")
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
    res = report["result_consistency_audit_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, best_top10={res['best_top10_file_reach_count']})")


if __name__ == "__main__":
    main()
