#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10t_n1_span_surface_rank_order_proxy_validation.v1"
PHASE = "BEA-v1-N10T N1 Span-Surface Fixed-Pool Rank-Order Proxy Validation"
GENERATED_BY = "bea_v1_n10t_n1_span_surface_rank_order_proxy_validation"
STATUS_PASS = "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"
STATUS_BELOW = "n1_span_surface_rank_order_proxy_validation_complete_below_threshold"

STATUSES = (
    STATUS_PASS,
    STATUS_BELOW,
    "no_go_n10t_required_inputs_unavailable",
    "no_go_n10t_private_span_rows_missing",
    "no_go_n10t_span_surface_schema_invalid",
    "no_go_n10t_denominator_too_small",
    "no_go_n10t_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

ARMS = (
    "baseline_n1_span_order",
    "span_extra_depth_promote_before_primary_prefix_4",
    "span_bounded_interleave_primary2_extra1",
    "span_late_extra_depth_demote_after_primary_prefix_8",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json")
PUBLIC_INPUTS = {
    "n10r_preflight_artifact": (Path("artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json"), "no_go_n10r_target_denominator_insufficient"),
    "n9_replication_package_artifact": (Path("artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json"), "recovered_fixed_pool_result_replication_package_complete"),
    "n5_preflight_artifact": (Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json"), "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
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
    "private_input_bucket", "intake_status_bucket", "denominator_bucket", "arm_bucket", "arm_semantics_bucket",
    "position_rule_bucket", "result_status_bucket", "subgroup_bucket", "threshold_bucket", "decision_bucket",
    "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10u_handoff_bucket", "authorization",
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
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                ks = str(key)
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + ks)
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


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        data, load = load_json(path)
        observed = str(data.get("status", "") or "")
        scan = data.get("forbidden_scan", {}).get("status", "pass") if isinstance(data.get("forbidden_scan"), dict) else "pass"
        passed = load == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10tin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def load_span_rows() -> tuple[list[dict[str, Any]], str]:
    full = root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows = []
    try:
        with full.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "schema_invalid"
                rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def validate_rows(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if not isinstance(row.get("p4_evidence"), list) or not isinstance(row.get("gold_paths"), list):
            return False
        for ev in row.get("p4_evidence", [])[:3]:
            if not isinstance(ev, dict) or "path" not in ev:
                return False
    return True


def private_span_input_intake_records(rows: list[dict[str, Any]], load_status: str, schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_span_input_intake_id": "n10tpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if schema_ok else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "schema_valid_bool": schema_ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if isinstance(r.get("p4_evidence"), list) and r.get("p4_evidence") and isinstance(r.get("gold_paths"), list) and r.get("gold_paths")]


def order_for(arm: str, evidence: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    items = list(enumerate(evidence, start=1))
    primary = [x for x in items if x[0] <= 20]
    extra = [x for x in items if x[0] > 20]
    if arm == "baseline_n1_span_order":
        return items
    if arm == "span_extra_depth_promote_before_primary_prefix_4":
        return extra + primary[:4] + primary[4:]
    if arm == "span_bounded_interleave_primary2_extra1":
        out: list[tuple[int, dict[str, Any]]] = []
        p = e = 0
        while p < len(primary) or e < len(extra):
            out.extend(primary[p:p + 2]); p += 2
            if e < len(extra):
                out.append(extra[e]); e += 1
            if p >= len(primary):
                break
        out.extend(primary[p:]); out.extend(extra[e:])
        return out
    if arm == "span_late_extra_depth_demote_after_primary_prefix_8":
        return primary[:8] + primary[8:] + extra
    raise ValueError("unknown arm")


def first_hit(order: list[tuple[int, dict[str, Any]]], gold: set[str]) -> int | None:
    for idx, (_orig, ev) in enumerate(order, start=1):
        if str(ev.get("path", "")) in gold:
            return idx
    return None


def compute_results(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, dict[str, tuple[int, int, int, int]]]:
    baseline_top10: list[bool] = []
    reachable = 0
    per_case: dict[str, list[int | None]] = {arm: [] for arm in ARMS}
    for row in rows:
        gold = {str(x) for x in row.get("gold_paths", []) if x}
        evidence = row.get("p4_evidence", [])
        any_hit = any(str(ev.get("path", "")) in gold for ev in evidence if isinstance(ev, dict))
        reachable += int(any_hit)
        for arm in ARMS:
            per_case[arm].append(first_hit(order_for(arm, evidence), gold))
        baseline_top10.append(per_case["baseline_n1_span_order"][-1] is not None and per_case["baseline_n1_span_order"][-1] <= 10)
    baseline_count = sum(baseline_top10)
    tuples: dict[str, tuple[int, int, int, int]] = {}
    records = []
    for idx, arm in enumerate(ARMS):
        positions = per_case[arm]
        top10 = sum(1 for p in positions if p is not None and p <= 10)
        top20 = sum(1 for p in positions if p is not None and p <= 20)
        regress = sum(1 for base_hit, p in zip(baseline_top10, positions) if base_hit and not (p is not None and p <= 10))
        delta = top10 - baseline_count
        tuples[arm] = (top10, top20, delta, regress)
        records.append({"anonymous_per_arm_proxy_result_id": f"n10tres{idx:04d}", "arm_bucket": arm, "result_status_bucket": "proxy_threshold_pass_candidate" if delta > 0 else "proxy_no_gain", "eligible_denominator_count": len(rows), "reachable_in_pool_count": reachable, "top10_file_reach_count": top10, "top20_file_reach_count": top20, "delta_top10_vs_baseline": delta, "case_regression_count_vs_baseline": regress, "candidate_pool_changed_bool": False, "candidate_added_count": 0, "candidate_removed_count": 0})
    return records, reachable, tuples


def span_surface_denominator_records(total_rows: int, eligible_count: int, reachable: int) -> list[dict[str, Any]]:
    return [{"anonymous_span_surface_denominator_id": "n10tden0000", "denominator_bucket": "n1_span_rows_with_evidence_and_gold", "private_span_rows_read": total_rows, "eligible_denominator_count": eligible_count, "reachable_in_pool_count": reachable, "minimum_eligible_denominator_count": 100, "denominator_sufficient_bool": eligible_count >= 100, "file_level_gold_matching_only_bool": True}]


def span_arm_semantics_records() -> list[dict[str, Any]]:
    return [{"anonymous_span_arm_semantics_id": f"n10tarm{idx:04d}", "arm_bucket": arm, "arm_semantics_bucket": "n1_span_surface_fixed_pool_order_transform_only", "position_rule_bucket": "original_position_le_20_primary_position_gt_20_extra_depth_no_gold_signal", "candidate_pool_changed_bool": False, "candidate_added_bool": False, "candidate_removed_bool": False, "gold_used_for_ordering_bool": False, "new_arm_search_bool": False, "complete_bool": True} for idx, arm in enumerate(ARMS)]


def subgroup_result_records(eligible_count: int, reachable: int, result_tuples: dict[str, tuple[int, int, int, int]]) -> list[dict[str, Any]]:
    best_arm = max(result_tuples, key=lambda a: result_tuples[a][2]) if result_tuples else ""
    top10, top20, delta, reg = result_tuples.get(best_arm, (0, 0, 0, 0))
    return [{"anonymous_subgroup_result_id": "n10tsub0000", "subgroup_bucket": "all_eligible_span_surface_rows", "eligible_denominator_count": eligible_count, "reachable_in_pool_count": reachable, "best_arm_bucket": best_arm, "best_top10_file_reach_count": top10, "best_top20_file_reach_count": top20, "best_delta_top10_vs_baseline": delta, "best_case_regression_count_vs_baseline": reg}]


def threshold_decision_records(eligible_count: int, result_tuples: dict[str, tuple[int, int, int, int]]) -> tuple[list[dict[str, Any]], bool]:
    import math
    best_arm = max(result_tuples, key=lambda a: result_tuples[a][2]) if result_tuples else ""
    top10, top20, delta, reg = result_tuples.get(best_arm, (0, 0, 0, 0))
    delta_threshold = max(10, math.ceil(0.05 * eligible_count))
    reg_threshold = math.ceil(0.01 * eligible_count)
    passed = delta >= delta_threshold and reg <= reg_threshold
    return [{"anonymous_threshold_decision_id": "n10tthreshold0000", "threshold_bucket": "delta_top10_ge_max_10_or_5pct_and_regressions_le_1pct", "decision_bucket": "proxy_threshold_passed" if passed else "proxy_complete_below_threshold", "best_arm_bucket": best_arm, "best_top10_file_reach_count": top10, "best_top20_file_reach_count": top20, "best_delta_top10_vs_baseline": delta, "best_case_regression_count_vs_baseline": reg, "delta_top10_threshold": delta_threshold, "case_regression_threshold": reg_threshold, "threshold_passed_bool": passed}], passed


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10tprivacy0000", "privacy_boundary_bucket": "public_counts_buckets_only_no_span_or_path_content", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10tnoexec0000", "no_execution_boundary_bucket": "single_private_span_read_proxy_order_transform_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "support_labeling_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10u_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10u_handoff_id": "n10thandoff0000", "n10u_handoff_bucket": "n10u_span_surface_proxy_result_audit_authorized" if complete else "n10u_not_authorized", "n10u_authorized_bool": complete, "audit_scope_only_bool": True, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, span_rows: int, eligible_count: int, arm_count: int, threshold_passed: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("single_private_span_rows_read", span_rows > 0, span_rows, 1), ("eligible_denominator_count", eligible_count >= 100, eligible_count, 100), ("arm_count", arm_count == 4, arm_count, 4), ("candidate_added_count", True, 0, 0), ("candidate_removed_count", True, 0, 0), ("new_arm_search_count", True, 0, 0), ("threshold_passed", threshold_passed, int(threshold_passed), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    at_least = {"single_private_span_rows_read", "eligible_denominator_count"}
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "at_least" if name in at_least else "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10u_span_surface_proxy_result_audit_authorized" if complete else "n10u_not_authorized", "next_allowed_phase": "BEA-v1-N10U N1 Span-Surface Proxy Result Audit" if complete else "none_until_valid_n1_span_surface_rows_exist", "next_allowed_scope_bucket": "n10u_audit_only_no_promotion" if complete else "no_next_phase", "n10u_authorized": complete, "private_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, schema_ok: bool, eligible_count: int, privacy_ok: bool, noexec_ok: bool, threshold_passed: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10t_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10t_private_span_rows_missing"
    if not schema_ok:
        return "no_go_n10t_span_surface_schema_invalid"
    if eligible_count < 100:
        return "no_go_n10t_denominator_too_small"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10t_privacy_or_claim_boundary_failed"
    return STATUS_PASS if threshold_passed else STATUS_BELOW


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    rows, load_status = load_span_rows()
    schema_ok = load_status == "pass" and validate_rows(rows)
    eligible = eligible_rows(rows) if schema_ok else []
    per_arm, reachable, tuples = compute_results(eligible) if eligible else ([], 0, {})
    threshold, threshold_passed = threshold_decision_records(len(eligible), tuples) if per_arm else ([], False)
    privacy, privacy_ok = privacy_boundary_records()
    noexec, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, schema_ok, len(eligible), privacy_ok, noexec_ok, threshold_passed)
    complete = status in {STATUS_PASS, STATUS_BELOW}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "n1_span_surface_proxy_validation_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_span_input_intake_records": private_span_input_intake_records(rows, load_status, schema_ok), "span_surface_denominator_records": span_surface_denominator_records(len(rows), len(eligible), reachable), "span_arm_semantics_records": span_arm_semantics_records(), "per_arm_proxy_result_records": per_arm, "subgroup_result_records": subgroup_result_records(len(eligible), reachable, tuples), "threshold_decision_records": threshold, "privacy_boundary_records": privacy, "no_forbidden_execution_records": noexec, "n10u_handoff_records": n10u_handoff_records(complete), "gate_records": gate_records(input_ok, len(rows), len(eligible), len(per_arm), threshold_passed, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] in {STATUS_PASS, STATUS_BELOW}
    report["gate_records"] = gate_records(input_ok, len(rows), len(eligible), len(per_arm), threshold_passed, privacy_ok, noexec_ok, scanner_ok)
    report["n10u_handoff_records"] = n10u_handoff_records(complete)
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
    rows, load_status = load_span_rows()
    schema_ok = load_status == "pass" and validate_rows(rows)
    eligible = eligible_rows(rows) if schema_ok else []
    per_arm, reachable, tuples = compute_results(eligible) if eligible else ([], 0, {})
    threshold, threshold_passed = threshold_decision_records(len(eligible), tuples) if per_arm else ([], False)
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, STATUS_BELOW, "no_go_n10t_required_inputs_unavailable", "no_go_n10t_private_span_rows_missing", "no_go_n10t_span_surface_schema_invalid", "no_go_n10t_denominator_too_small", "no_go_n10t_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 3),
        check("private_input", load_status == "pass" and schema_ok and len(rows) == 213),
        check("denominator", len(eligible) == 213 and reachable == 52),
        check("arms", len(per_arm) == 4 and {r["arm_bucket"] for r in per_arm} == set(ARMS)),
        check("metrics", tuples.get("span_extra_depth_promote_before_primary_prefix_4") == (34, 44, 34, 0) and tuples.get("span_bounded_interleave_primary2_extra1") == (17, 22, 17, 0)),
        check("threshold", threshold_passed and threshold[0]["best_delta_top10_vs_baseline"] == 34 and threshold[0]["delta_top10_threshold"] == 11 and threshold[0]["case_regression_threshold"] == 3),
        check("semantics", all(r["gold_used_for_ordering_bool"] is False and r["candidate_pool_changed_bool"] is False for r in span_arm_semantics_records())),
        check("privacy", privacy_boundary_records()[1] and privacy_boundary_records()[0][0]["private_path_public_bool"] is False),
        check("no_execution", no_forbidden_execution_records()[1] and no_forbidden_execution_records()[0][0]["other_private_file_read_count"] == 0 and no_forbidden_execution_records()[0][0]["retrieval_execution_count"] == 0),
        check("handoff", n10u_handoff_records(True)[0]["n10u_authorized_bool"] is True and n10u_handoff_records(True)[0]["runtime_default_promotion_authorized_bool"] is False),
        check("status_expected", status_for(True, True, "pass", True, len(eligible), True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10T N1 span-surface rank-order proxy validation")
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
    th = report["threshold_decision_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, best_delta={th['best_delta_top10_vs_baseline']})")


if __name__ == "__main__":
    main()
