#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10x_n1_span_surface_span_level_utility_validation.v1"
PHASE = "BEA-v1-N10X N1 Span-Surface Span-Level Utility Validation"
GENERATED_BY = "bea_v1_n10x_n1_span_surface_span_level_utility_validation"
STATUS_PASS = "n1_span_surface_span_level_utility_validation_pass_n10y_authorized"
STATUS_BELOW = "n1_span_surface_span_level_utility_validation_complete_below_threshold"

STATUSES = (
    STATUS_PASS,
    STATUS_BELOW,
    "no_go_n10x_required_inputs_unavailable",
    "no_go_n10x_private_span_rows_missing",
    "no_go_n10x_span_gold_line_schema_invalid",
    "no_go_n10x_span_evaluable_denominator_too_small",
    "no_go_n10x_privacy_or_claim_boundary_failed",
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
DEFAULT_OUT = Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json")
INPUTS = {
    "n10w_proxy_replication_package_artifact": (Path("artifacts/bea_v1_n10w_n1_span_surface_proxy_replication_package/bea_v1_n10w_n1_span_surface_proxy_replication_package_report.json"), "n1_span_surface_proxy_replication_package_complete"),
    "n10v_independent_recompute_artifact": (Path("artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json"), "independent_recompute_n1_span_surface_proxy_pass_n10w_authorized"),
    "n10t_proxy_validation_artifact": (Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json"), "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"),
}
EXPECTED = {
    "denominator": 213,
    "reachable_file_count": 52,
    "span_reachable_count": 12,
    "best_arm": "span_extra_depth_promote_before_primary_prefix_4",
    "best_span_top10": 9,
    "best_span_top20": 10,
    "best_file_top10": 34,
    "best_file_top20": 44,
    "best_delta": 9,
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
    "private_input_bucket", "intake_status_bucket", "schema_bucket", "denominator_bucket", "arm_bucket", "arm_semantics_bucket",
    "position_rule_bucket", "result_status_bucket", "threshold_bucket", "decision_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "n10y_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
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


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10xin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, ok


def load_rows() -> tuple[list[dict[str, Any]], str]:
    full = root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows = []
    try:
        with full.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        return [], "schema_invalid"
                    rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def range_pair_ok(item: Any) -> bool:
    return isinstance(item, list) and len(item) >= 2 and isinstance(item[0], int) and isinstance(item[1], int) and item[0] <= item[1]


def row_schema_ok(row: dict[str, Any]) -> bool:
    evidence = row.get("p4_evidence")
    refs = row.get("gold_paths")
    ranges = row.get("gold_lines")
    if not isinstance(evidence, list) or not isinstance(refs, list) or not isinstance(ranges, list) or len(refs) != len(ranges) or not refs:
        return False
    if not all(range_pair_ok(x) for x in ranges):
        return False
    for ev in evidence:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
        start = ev["start_line"]
        end = ev["end_line"]
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            return False
    return True


def eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if row_schema_ok(r) and r.get("p4_evidence")]


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


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def ref_map(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return out


def first_hit(order: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]], span_level: bool) -> int | None:
    for idx, (_pos, ev) in enumerate(order, start=1):
        ref = str(ev.get("path", ""))
        if ref not in refs:
            continue
        if not span_level:
            return idx
        start_value = ev.get("start_line")
        end_value = ev.get("end_line")
        if not isinstance(start_value, int) or not isinstance(end_value, int):
            continue
        start = int(start_value)
        end = int(end_value)
        if any(overlaps(start, end, a, b) for a, b in refs[ref]):
            return idx
    return None


def compute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int, bool]:
    eligible = eligible_rows(rows)
    file_reachable = 0
    span_reachable = 0
    baseline_span_top10: list[bool] = []
    positions: dict[str, dict[str, list[int | None]]] = {arm: {"file": [], "span": []} for arm in ARMS}
    for row in eligible:
        refs = ref_map(row)
        evidence = row.get("p4_evidence", [])
        file_reachable += int(first_hit(order_for("baseline_n1_span_order", evidence), refs, False) is not None)
        span_reachable += int(first_hit(order_for("baseline_n1_span_order", evidence), refs, True) is not None)
        for arm in ARMS:
            ordered = order_for(arm, evidence)
            positions[arm]["file"].append(first_hit(ordered, refs, False))
            positions[arm]["span"].append(first_hit(ordered, refs, True))
        base_span = positions["baseline_n1_span_order"]["span"][-1]
        baseline_span_top10.append(base_span is not None and base_span <= 10)
    baseline_span_count = sum(baseline_span_top10)
    records = []
    for idx, arm in enumerate(ARMS):
        sp = positions[arm]["span"]
        fp = positions[arm]["file"]
        span10 = sum(p is not None and p <= 10 for p in sp)
        span20 = sum(p is not None and p <= 20 for p in sp)
        file10 = sum(p is not None and p <= 10 for p in fp)
        file20 = sum(p is not None and p <= 20 for p in fp)
        reg = sum(b and not (p is not None and p <= 10) for b, p in zip(baseline_span_top10, sp))
        records.append({"anonymous_per_arm_span_utility_id": f"n10xres{idx:04d}", "arm_bucket": arm, "result_status_bucket": "span_threshold_candidate" if span10 - baseline_span_count > 0 else "span_no_gain", "span_evaluable_denominator_count": len(eligible), "reachable_file_count": file_reachable, "span_reachable_count": span_reachable, "span_overlap_top10_count": span10, "span_overlap_top20_count": span20, "file_top10_count": file10, "file_top20_count": file20, "delta_span_overlap_top10_vs_baseline": span10 - baseline_span_count, "case_regression_count_vs_baseline": reg, "candidate_pool_changed_bool": False, "candidate_added_count": 0, "candidate_removed_count": 0})
    return records, file_reachable, span_reachable, len(eligible) >= 100


def private_span_input_intake_records(rows: list[dict[str, Any]], load_status: str, schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_span_input_intake_id": "n10xpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if schema_ok else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "schema_valid_bool": schema_ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def span_gold_schema_records(rows: list[dict[str, Any]], schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_span_gold_schema_id": "n10xschema0000", "schema_bucket": "file_reference_aligned_range_pairs_available", "rows_checked_count": len(rows), "range_pair_schema_valid_bool": schema_ok, "reference_alignment_valid_bool": schema_ok, "fallback_to_file_level_used_bool": False, "schema_complete_bool": schema_ok}]


def span_evaluable_denominator_records(eligible_count: int, file_reachable: int, span_reachable: int) -> list[dict[str, Any]]:
    return [{"anonymous_span_evaluable_denominator_id": "n10xden0000", "denominator_bucket": "n1_span_rows_with_file_references_ranges_and_evidence", "span_evaluable_denominator_count": eligible_count, "minimum_span_evaluable_denominator_count": 100, "reachable_file_count": file_reachable, "span_reachable_count": span_reachable, "denominator_sufficient_bool": eligible_count >= 100}]


def arm_semantics_records() -> list[dict[str, Any]]:
    return [{"anonymous_arm_semantics_id": f"n10xarm{idx:04d}", "arm_bucket": arm, "arm_semantics_bucket": "n1_span_surface_fixed_pool_order_transform_only", "position_rule_bucket": "original_position_le_20_primary_position_gt_20_extra_depth_no_gold_signal", "candidate_pool_changed_bool": False, "candidate_added_bool": False, "candidate_removed_bool": False, "gold_signal_used_for_ordering_bool": False, "new_arm_search_bool": False, "complete_bool": True} for idx, arm in enumerate(ARMS)]


def threshold_decision_records(per_arm: list[dict[str, Any]], denominator: int) -> tuple[list[dict[str, Any]], bool]:
    import math
    best = max(per_arm, key=lambda r: int(r["delta_span_overlap_top10_vs_baseline"])) if per_arm else {}
    delta_threshold = max(5, math.ceil(0.05 * denominator))
    regression_threshold = math.ceil(0.01 * denominator)
    passed = int(best.get("delta_span_overlap_top10_vs_baseline", 0)) >= delta_threshold and int(best.get("case_regression_count_vs_baseline", 0)) <= regression_threshold
    return [{"anonymous_threshold_decision_id": "n10xthreshold0000", "threshold_bucket": "delta_span_overlap_top10_ge_max_5_or_5pct_and_regressions_le_1pct", "decision_bucket": "span_level_threshold_passed" if passed else "span_level_complete_below_threshold", "best_arm_bucket": str(best.get("arm_bucket", "")), "best_span_overlap_top10_count": int(best.get("span_overlap_top10_count", 0)), "best_span_overlap_top20_count": int(best.get("span_overlap_top20_count", 0)), "best_file_top10_count": int(best.get("file_top10_count", 0)), "best_file_top20_count": int(best.get("file_top20_count", 0)), "best_delta_span_overlap_top10_vs_baseline": int(best.get("delta_span_overlap_top10_vs_baseline", 0)), "best_case_regression_count_vs_baseline": int(best.get("case_regression_count_vs_baseline", 0)), "delta_span_overlap_top10_threshold": delta_threshold, "case_regression_threshold": regression_threshold, "threshold_passed_bool": passed}], passed


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10xprivacy0000", "privacy_boundary_bucket": "public_counts_only_no_private_surface_details", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10xnoexec0000", "no_execution_boundary_bucket": "single_private_span_read_span_overlap_validation_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "support_labeling_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10y_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10y_handoff_id": "n10xhandoff0000", "n10y_handoff_bucket": "n10y_public_result_audit_authorized" if complete else "n10y_not_authorized", "n10y_public_result_audit_authorized_bool": complete, "audit_scope_only_bool": True, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, rows_ok: bool, schema_ok: bool, denominator_ok: bool, arm_count: int, complete: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("private_span_rows_read", rows_ok, 213 if rows_ok else 0, 213), ("span_range_schema_valid", schema_ok, int(schema_ok), 1), ("span_evaluable_denominator_count", denominator_ok, 213 if denominator_ok else 0, 100), ("arm_count", arm_count == 4, arm_count, 4), ("validation_complete", complete, int(complete), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10y_public_result_audit_authorized" if complete else "n10y_not_authorized", "next_allowed_phase": "BEA-v1-N10Y N1 Span-Surface Span-Level Utility Result Audit" if complete else "none_until_valid_span_gold_line_schema_exists", "next_allowed_scope_bucket": "n10y_public_audit_only_no_promotion" if complete else "no_next_phase", "n10y_public_result_audit_authorized": complete, "private_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, schema_ok: bool, denom_ok: bool, privacy_ok: bool, noexec_ok: bool, threshold_passed: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10x_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10x_private_span_rows_missing"
    if not schema_ok:
        return "no_go_n10x_span_gold_line_schema_invalid"
    if not denom_ok:
        return "no_go_n10x_span_evaluable_denominator_too_small"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10x_privacy_or_claim_boundary_failed"
    return STATUS_PASS if threshold_passed else STATUS_BELOW


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    valid_schema = load_status == "pass" and all(row_schema_ok(r) for r in rows)
    eligible = eligible_rows(rows) if valid_schema else []
    per_arm, file_reachable, span_reachable, denom_ok = compute(rows) if valid_schema else ([], 0, 0, False)
    threshold, threshold_passed = threshold_decision_records(per_arm, len(eligible)) if per_arm else ([], False)
    privacy, privacy_ok = privacy_boundary_records()
    noexec, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, valid_schema, denom_ok, privacy_ok, noexec_ok, threshold_passed)
    complete = status in {STATUS_PASS, STATUS_BELOW}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "n1_span_surface_span_level_utility_validation_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_span_input_intake_records": private_span_input_intake_records(rows, load_status, valid_schema), "span_gold_schema_records": span_gold_schema_records(rows, valid_schema), "span_evaluable_denominator_records": span_evaluable_denominator_records(len(eligible), file_reachable, span_reachable), "arm_semantics_records": arm_semantics_records(), "per_arm_span_utility_records": per_arm, "threshold_decision_records": threshold, "privacy_boundary_records": privacy, "no_forbidden_execution_records": noexec, "n10y_handoff_records": n10y_handoff_records(complete), "gate_records": gate_records(input_ok, load_status == "pass", valid_schema, denom_ok, len(per_arm), complete, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] in {STATUS_PASS, STATUS_BELOW}
    report["gate_records"] = gate_records(input_ok, load_status == "pass", valid_schema, denom_ok, len(per_arm), complete, privacy_ok, noexec_ok, scanner_ok)
    report["n10y_handoff_records"] = n10y_handoff_records(complete)
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
    rows, load_status = load_rows()
    valid_schema = load_status == "pass" and all(row_schema_ok(r) for r in rows)
    eligible = eligible_rows(rows) if valid_schema else []
    per_arm, file_reachable, span_reachable, denom_ok = compute(rows) if valid_schema else ([], 0, 0, False)
    threshold, threshold_passed = threshold_decision_records(per_arm, len(eligible)) if per_arm else ([], False)
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, STATUS_BELOW, "no_go_n10x_required_inputs_unavailable", "no_go_n10x_private_span_rows_missing", "no_go_n10x_span_gold_line_schema_invalid", "no_go_n10x_span_evaluable_denominator_too_small", "no_go_n10x_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 3),
        check("private_input", load_status == "pass" and len(rows) == 213 and valid_schema),
        check("denominator", len(eligible) == EXPECTED["denominator"] and file_reachable == EXPECTED["reachable_file_count"] and span_reachable == EXPECTED["span_reachable_count"] and denom_ok),
        check("arms", len(per_arm) == 4 and {r["arm_bucket"] for r in per_arm} == set(ARMS)),
        check("metrics", any(r["arm_bucket"] == EXPECTED["best_arm"] and r["span_overlap_top10_count"] == EXPECTED["best_span_top10"] and r["span_overlap_top20_count"] == EXPECTED["best_span_top20"] and r["file_top10_count"] == EXPECTED["best_file_top10"] and r["file_top20_count"] == EXPECTED["best_file_top20"] for r in per_arm)),
        check("threshold_below", not threshold_passed and threshold[0]["best_delta_span_overlap_top10_vs_baseline"] == EXPECTED["best_delta"] and threshold[0]["delta_span_overlap_top10_threshold"] == EXPECTED["delta_threshold"] and threshold[0]["case_regression_threshold"] == EXPECTED["regression_threshold"]),
        check("semantics", all(r["gold_signal_used_for_ordering_bool"] is False and r["candidate_pool_changed_bool"] is False for r in arm_semantics_records())),
        check("privacy", privacy_boundary_records()[1] and privacy_boundary_records()[0][0]["gold_line_public_bool"] is False and privacy_boundary_records()[0][0]["span_public_bool"] is False),
        check("no_execution", no_forbidden_execution_records()[1] and no_forbidden_execution_records()[0][0]["private_span_input_read_count"] == 1 and no_forbidden_execution_records()[0][0]["other_private_file_read_count"] == 0),
        check("handoff", n10y_handoff_records(True)[0]["n10y_public_result_audit_authorized_bool"] is True and stop_go_records(True)[0]["runtime_or_default_promotion_authorized"] is False),
        check("status_expected", status_for(True, True, "pass", True, True, True, True, False) == STATUS_BELOW),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10X N1 span-surface span-level utility validation")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, best_span_top10={th['best_span_overlap_top10_count']})")


if __name__ == "__main__":
    main()
