#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package.v1"
PHASE = "BEA-v1-N10AG Fixed Span-Window Repair Claim-Boundary Audit Package"
STATUS_COMPLETE = "fixed_span_window_repair_claim_boundary_package_complete_n10ah_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ag_required_public_inputs_unavailable",
    "no_go_n10ag_result_chain_mismatch",
    "no_go_n10ag_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package_report.json")
INPUTS = {
    "n10ab_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
    "n10ac_result_audit_artifact": (Path("artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json"), "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized"),
    "n10ad_independent_recompute_artifact": (Path("artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json"), "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized"),
    "n10ae_replication_package_artifact": (Path("artifacts/bea_v1_n10ae_fixed_span_window_repair_replication_package/bea_v1_n10ae_fixed_span_window_repair_replication_package_report.json"), "fixed_span_window_repair_replication_package_complete_n10af_authorized"),
    "n10af_robustness_artifact": (Path("artifacts/bea_v1_n10af_fixed_span_window_repair_robustness_validation/bea_v1_n10af_fixed_span_window_repair_robustness_validation_report.json"), "fixed_span_window_repair_robustness_validation_pass_n10ag_authorized"),
    "n10x_span_level_validation_artifact": (Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json"), "n1_span_surface_span_level_utility_validation_complete_below_threshold"),
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
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
    "chain_bucket", "allowed_claim_bucket", "forbidden_claim_bucket", "robustness_bucket", "replication_bucket",
    "decision_bucket", "privacy_boundary_bucket", "no_private_recompute_boundary_bucket", "n10ah_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        records.append({"anonymous_input_artifact_id": f"n10agin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def _var(records: list[Any], bucket: str) -> dict[str, Any]:
    for row in records:
        if isinstance(row, dict) and row.get("variant_bucket") == bucket:
            return row
    return {}


def result_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ab = artifacts.get("n10ab_repair_smoke_artifact", {})
    pm20 = _var(n10ab.get("repair_variant_execution_records", []), "fixed_symmetric_span_expansion_pm20_lines")
    pm50 = _var(n10ab.get("repair_variant_execution_records", []), "fixed_symmetric_span_expansion_pm50_lines")
    pm100 = _var(n10ab.get("repair_variant_execution_records", []), "fixed_symmetric_span_expansion_pm100_lines")
    ok = n10ab.get("status") == "fixed_span_window_repair_smoke_pass_n10ac_authorized" and pm50.get("eligible_denominator_count") == 213 and pm50.get("baseline_unexpanded_top10_span_overlap_count") == 9 and pm50.get("top10_expanded_span_overlap_count") == 19 and pm50.get("delta_top10_vs_unexpanded_best_arm") == 10 and pm50.get("original_span_hit_lost_count") == 0 and pm20.get("top10_expanded_span_overlap_count") == 15 and pm100.get("top10_expanded_span_overlap_count") == 21
    return [{"anonymous_result_chain_id": "n10agchain0000", "chain_bucket": "n10ab_fixed_pm50_repair_smoke_pass", "denominator_count": int(pm50.get("eligible_denominator_count", -1)), "baseline_top10_span_overlap_count": int(pm50.get("baseline_unexpanded_top10_span_overlap_count", -1)), "pm50_top10_span_overlap_count": int(pm50.get("top10_expanded_span_overlap_count", -1)), "pm50_top20_span_overlap_count": int(pm50.get("top20_expanded_span_overlap_count", -1)), "pm50_delta_top10_span_overlap_count": int(pm50.get("delta_top10_vs_unexpanded_best_arm", -1)), "pm50_original_span_hit_lost_count": int(pm50.get("original_span_hit_lost_count", -1)), "pm20_top10_span_overlap_count": int(pm20.get("top10_expanded_span_overlap_count", -1)), "pm100_top10_span_overlap_count": int(pm100.get("top10_expanded_span_overlap_count", -1)), "result_chain_valid_bool": ok}], ok


def replication_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ad = artifacts.get("n10ad_independent_recompute_artifact", {})
    n10ae = artifacts.get("n10ae_replication_package_artifact", {})
    n10ac = artifacts.get("n10ac_result_audit_artifact", {})
    match = all(isinstance(r, dict) and r.get("aggregate_match_bool") is True for r in n10ad.get("aggregate_match_records", [])) and len(n10ad.get("aggregate_match_records", [])) == 4
    code_call = (n10ad.get("independence_boundary_records") or [{}])[0].get("n10ab_code_call_count")
    ok = n10ac.get("status") == "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized" and n10ad.get("status") == "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized" and n10ae.get("status") == "fixed_span_window_repair_replication_package_complete_n10af_authorized" and match and code_call == 0
    return [{"anonymous_replication_chain_id": "n10agrep0000", "replication_bucket": "n10ac_audit_n10ad_independent_match_n10ae_package", "n10ac_audit_complete_bool": n10ac.get("status") == "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized", "n10ad_independent_recompute_pass_bool": n10ad.get("status") == "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized", "n10ad_aggregate_match_bool": match, "n10ad_n10ab_code_call_count": int(code_call if isinstance(code_call, int) else -1), "n10ae_replication_package_complete_bool": n10ae.get("status") == "fixed_span_window_repair_replication_package_complete_n10af_authorized", "replication_chain_valid_bool": ok}], ok


def robustness_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10af = artifacts.get("n10af_robustness_artifact", {})
    decision = (n10af.get("robustness_decision_records") or [{}])[0]
    global_row = (n10af.get("global_result_reproduction_records") or [{}])[0]
    ok = n10af.get("status") == "fixed_span_window_repair_robustness_validation_pass_n10ag_authorized" and decision.get("positive_delta_subgroup_count") == 7 and decision.get("baseline_span_hit_negative_delta_count") == 0 and decision.get("robustness_pass_bool") is True and global_row.get("pm50_top10_span_overlap_count") == 19
    return [{"anonymous_robustness_chain_id": "n10agrobust0000", "robustness_bucket": "n10af_predeclared_subgroup_robustness_pass", "positive_delta_subgroup_count": int(decision.get("positive_delta_subgroup_count", -1)), "baseline_span_hit_negative_delta_count": int(decision.get("baseline_span_hit_negative_delta_count", -1)), "pm50_top10_span_overlap_count": int(global_row.get("pm50_top10_span_overlap_count", -1)), "pm50_lost_original_span_hit_count": int(global_row.get("pm50_lost_original_span_hit_count", -1)), "robustness_pass_bool": bool(decision.get("robustness_pass_bool", False)), "robustness_chain_valid_bool": ok}], ok


def allowed_claim_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_allowed_claim_id": "n10agallow0000", "allowed_claim_bucket": "scoped_n1_span_surface_fixed_pool_pm50_repair_smoke_robustness_pass", "n1_span_surface_proxy_scope_bool": True, "fixed_pool_existing_evidence_scope_bool": True, "fixed_pm50_span_window_scope_bool": True, "smoke_and_robustness_pass_bool": True, "default_off_bool": True, "allowed_claim_valid_bool": True}], True


def forbidden_claim_records() -> tuple[list[dict[str, Any]], bool]:
    claims = [
        "runtime_default_promotion", "method_winner", "downstream_value", "p5_or_v1_a", "broad_generalization", "selector_reranker", "retrieval_or_rerun", "candidate_generation", "gold_as_policy", "adaptive_tuning",
    ]
    return [{"anonymous_forbidden_claim_id": f"n10agforbid{idx:04d}", "forbidden_claim_bucket": claim, "authorized_bool": False, "claimed_bool": False} for idx, claim in enumerate(claims)], True


def claim_boundary_decision_records(result_ok: bool, replication_ok: bool, robustness_ok: bool, allowed_ok: bool, forbidden_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    complete = result_ok and replication_ok and robustness_ok and allowed_ok and forbidden_ok
    return [{"anonymous_claim_boundary_decision_id": "n10agdecision0000", "decision_bucket": "claim_boundary_package_complete" if complete else "claim_boundary_incomplete", "result_chain_valid_bool": result_ok, "replication_chain_valid_bool": replication_ok, "robustness_chain_valid_bool": robustness_ok, "allowed_claim_valid_bool": allowed_ok, "forbidden_claims_all_false_bool": forbidden_ok, "claim_boundary_complete_bool": complete}], complete


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10agprivacy0000", "privacy_boundary_bucket": "public_claim_package_aggregate_buckets_only", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_private_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_private_recompute_id": "n10agnoexec0000", "no_private_recompute_boundary_bucket": "public_artifact_package_only", "private_read_count": 0, "private_scan_count": 0, "recompute_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_private_recompute_complete_bool": True}], True


def n10ah_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ah_handoff_id": "n10aghandoff0000", "n10ah_handoff_bucket": "default_off_implementation_feasibility_preflight_only" if complete else "n10ah_not_authorized", "n10ah_preflight_authorized_bool": complete, "actual_runtime_implementation_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "private_read_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, result_ok: bool, replication_ok: bool, robustness_ok: bool, claim_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("result_chain", result_ok, int(result_ok), 1), ("replication_chain", replication_ok, int(replication_ok), 1), ("robustness_chain", robustness_ok, int(robustness_ok), 1), ("claim_boundary", claim_ok, int(claim_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_private_recompute", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ah_default_off_implementation_feasibility_preflight_authorized" if complete else "n10ah_not_authorized", "next_allowed_phase": "BEA-v1-N10AH Default-Off Implementation Feasibility Preflight" if complete else "none_until_claim_boundary_package_valid", "next_allowed_scope_bucket": "default_off_implementation_feasibility_preflight_only" if complete else "no_next_phase", "n10ah_preflight_authorized": complete, "private_read_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, result_ok: bool, replication_ok: bool, robustness_ok: bool, claim_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ag_required_public_inputs_unavailable"
    if not result_ok or not replication_ok or not robustness_ok:
        return "no_go_n10ag_result_chain_mismatch"
    if not claim_ok or not privacy_ok or not noexec_ok:
        return "no_go_n10ag_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    result_records, result_ok = result_chain_records(artifacts)
    replication_records, replication_ok = replication_chain_records(artifacts)
    robustness_records, robustness_ok = robustness_chain_records(artifacts)
    allowed_records, allowed_ok = allowed_claim_records()
    forbidden_records, forbidden_ok = forbidden_claim_records()
    decision_records, claim_ok = claim_boundary_decision_records(result_ok, replication_ok, robustness_ok, allowed_ok, forbidden_ok)
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_private_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, result_ok, replication_ok, robustness_ok, claim_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_claim_boundary_package_only", "generated_by": "bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "result_chain_records": result_records, "allowed_claim_records": allowed_records, "forbidden_claim_records": forbidden_records, "robustness_chain_records": robustness_records, "replication_chain_records": replication_records, "claim_boundary_decision_records": decision_records, "privacy_boundary_records": privacy_records, "no_private_recompute_records": noexec_records, "n10ah_handoff_records": n10ah_handoff_records(complete), "gate_records": gate_records(input_ok, result_ok, replication_ok, robustness_ok, claim_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["gate_records"] = gate_records(input_ok, result_ok, replication_ok, robustness_ok, claim_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10ah_handoff_records"] = n10ah_handoff_records(complete)
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
    result_records, result_ok = result_chain_records(artifacts)
    replication_records, replication_ok = replication_chain_records(artifacts)
    robustness_records, robustness_ok = robustness_chain_records(artifacts)
    allowed_records, allowed_ok = allowed_claim_records()
    forbidden_records, forbidden_ok = forbidden_claim_records()
    decision_records, claim_ok = claim_boundary_decision_records(result_ok, replication_ok, robustness_ok, allowed_ok, forbidden_ok)
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_private_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ag_required_public_inputs_unavailable", "no_go_n10ag_result_chain_mismatch", "no_go_n10ag_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 7),
        check("result_chain", result_ok and result_records[0]["denominator_count"] == 213 and result_records[0]["baseline_top10_span_overlap_count"] == 9 and result_records[0]["pm50_top10_span_overlap_count"] == 19 and result_records[0]["pm20_top10_span_overlap_count"] == 15 and result_records[0]["pm100_top10_span_overlap_count"] == 21),
        check("replication_chain", replication_ok and replication_records[0]["n10ad_aggregate_match_bool"] is True and replication_records[0]["n10ad_n10ab_code_call_count"] == 0),
        check("robustness_chain", robustness_ok and robustness_records[0]["positive_delta_subgroup_count"] == 7 and robustness_records[0]["baseline_span_hit_negative_delta_count"] == 0),
        check("allowed_claim", allowed_ok and allowed_records[0]["n1_span_surface_proxy_scope_bool"] is True and allowed_records[0]["default_off_bool"] is True),
        check("forbidden_claims", forbidden_ok and len(forbidden_records) == 10 and all(r["authorized_bool"] is False and r["claimed_bool"] is False for r in forbidden_records)),
        check("decision", claim_ok and decision_records[0]["claim_boundary_complete_bool"] is True),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["span_public_bool"] is False),
        check("no_private_recompute", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("handoff", n10ah_handoff_records(True)[0]["n10ah_handoff_bucket"] == "default_off_implementation_feasibility_preflight_only" and stop_go_records(True)[0]["n10ah_preflight_authorized"] is True),
        check("status_expected", status_for(True, True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AG fixed span-window repair claim-boundary package")
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
    chain = report["result_chain_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={chain['pm50_top10_span_overlap_count']})")


if __name__ == "__main__":
    main()
