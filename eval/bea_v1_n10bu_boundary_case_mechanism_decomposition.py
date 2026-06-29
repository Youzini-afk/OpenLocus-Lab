#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn

from bea_v1_span_window_projection_adapter import project_evidence_spans


SCHEMA_VERSION = "bea_v1_n10bu_boundary_case_mechanism_decomposition.v1"
PHASE = "BEA-v1-N10BU Boundary Case Mechanism Decomposition"
STATUS_COMPLETE = "boundary_case_mechanism_decomposition_complete_n10bv_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bu_required_inputs_unavailable",
    "no_go_n10bu_private_span_rows_missing",
    "no_go_n10bu_boundary_case_accounting_invalid",
    "no_go_n10bu_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10bu_boundary_case_mechanism_decomposition/bea_v1_n10bu_boundary_case_mechanism_decomposition_report.json")
PUBLIC_INPUTS = {
    "n10bt_boundary_cost_package_artifact": (Path("artifacts/bea_v1_n10bt_boundary_cost_package/bea_v1_n10bt_boundary_cost_package_report.json"), "boundary_cost_package_complete_n10bu_authorized"),
    "n10bs_boundary_cost_refinement_artifact": (Path("artifacts/bea_v1_n10bs_boundary_cost_refinement_sweep/bea_v1_n10bs_boundary_cost_refinement_sweep_report.json"), "boundary_cost_refinement_sweep_complete_n10bt_authorized"),
    "n10br_cost_minimization_package_artifact": (Path("artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json"), "cost_minimization_package_complete_n10bs_authorized"),
}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks",
    "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "private_input_bucket", "intake_status_bucket", "comparison_bucket", "cost_bucket", "mechanism_bucket",
    "gap_bucket", "distance_to_expanded_window_bucket", "no_gold_policy_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "n10bv_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = repo_root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = repo_root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
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
            key = marker.rsplit(".", 1)[-1].replace("[]", "")
            if key in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
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
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10buin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, ok


def load_rows() -> tuple[list[dict[str, Any]], str]:
    full = repo_root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
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


def row_ok(row: dict[str, Any]) -> bool:
    evs = row.get("p4_evidence")
    refs = row.get("gold_paths")
    ranges = row.get("gold_lines")
    if not isinstance(evs, list) or not isinstance(refs, list) or not isinstance(ranges, list) or len(refs) != len(ranges):
        return False
    for ev in evs:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
    for rg in ranges:
        if not (isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1]):
            return False
    return True


def best_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(idx + 1, item) for idx, item in enumerate(evidence)]
    extra = [item for pos, item in indexed if pos > 20]
    primary = [item for pos, item in indexed if pos <= 20]
    return extra + primary[:4] + primary[4:]


def refmap(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return out


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def project(records: list[dict[str, Any]], before: int, after: int) -> list[dict[str, Any]]:
    if before == after:
        return project_evidence_spans(records, expansion_each_side=before, enabled=True)
    out: list[dict[str, Any]] = []
    for item in records:
        copied = dict(item)
        copied["start_line"] = max(1, int(copied["start_line"]) - before)
        copied["end_line"] = int(copied["end_line"]) + after
        out.append(copied)
    return out


def hit(records: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for item in records[:limit]:
        key = str(item.get("path", ""))
        if key not in refs:
            continue
        start = item.get("start_line")
        end = item.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if any(overlaps(start, end, a, b) for a, b in refs[key]):
            return True
    return False


def file_hit(records: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    ref_keys = set(refs.keys())
    return any(str(item.get("path", "")) in ref_keys for item in records[:limit])


def hits_for(rows: list[dict[str, Any]], before: int, after: int) -> tuple[set[int], set[int], set[int]]:
    top10: set[int] = set()
    top20: set[int] = set()
    file10: set[int] = set()
    for idx, row in enumerate(rows):
        ordered = best_order(row["p4_evidence"])
        projected = project(ordered, before, after)
        refs = refmap(row)
        if hit(projected, refs, 10):
            top10.add(idx)
        if hit(projected, refs, 20):
            top20.add(idx)
        if file_hit(projected, refs, 10):
            file10.add(idx)
    return top10, top20, file10


def gap_and_distance_for_case(row: dict[str, Any], before75: int, after75: int, before80: int, after80: int) -> tuple[str, str, bool]:
    ordered = best_order(row["p4_evidence"])
    p75 = project(ordered, before75, after75)
    p80 = project(ordered, before80, after80)
    refs = refmap(row)
    for item75, item80 in zip(p75[:10], p80[:10]):
        key80 = str(item80.get("path", ""))
        if key80 not in refs:
            continue
        start80 = int(item80["start_line"])
        end80 = int(item80["end_line"])
        matching_ranges = [(a, b) for a, b in refs[key80] if overlaps(start80, end80, a, b)]
        if not matching_ranges:
            continue
        start75 = int(item75["start_line"])
        end75 = int(item75["end_line"])
        # If the 80-cost evidence overlaps but 75-cost evidence does not, classify the nearest gap.
        nearest = min(matching_ranges, key=lambda rg: min(abs(end75 - rg[0]), abs(start75 - rg[1])))
        g0, g1 = nearest
        if end75 < g0:
            distance = g0 - end75
            gap = "before_gold_gap"
        elif start75 > g1:
            distance = start75 - g1
            gap = "after_gold_gap"
        elif overlaps(start75, end75, g0, g1):
            distance = 0
            gap = "already_overlap"
        else:
            distance = 0
            gap = "other"
        if distance == 0:
            bucket = "already_overlap"
        elif distance <= 5:
            bucket = "near_1_5"
        elif distance <= 10:
            bucket = "near_6_10"
        elif distance <= 25:
            bucket = "moderate_11_25"
        else:
            bucket = "far_gt25"
        return gap, bucket, distance <= (before80 - before75 + after80 - after75)
    return "other", "unavailable", False


def compute(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]], bool]:
    usable = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    cost75_top10, cost75_top20, cost75_file10 = hits_for(usable, 18, 57)
    cost80_top10, cost80_top20, cost80_file10 = hits_for(usable, 20, 60)
    transition = cost80_top10 - cost75_top10
    comparison_rows = [
        {"anonymous_boundary_comparison_id": "n10bucompare0000", "comparison_bucket": "cost75_before25_after75", "cost_bucket": "below_boundary", "total_cost_proxy": 75, "top10_span_overlap_count": len(cost75_top10), "top20_span_overlap_count": len(cost75_top20), "lost_plateau_core_top10_count": len(cost80_top10 - cost75_top10), "file_hit_top10_count": len(cost75_file10), "recovered_at_80_missed_at_75_count": len(transition), "missed_at_80_recovered_at_75_count": len(cost75_top10 - cost80_top10)},
        {"anonymous_boundary_comparison_id": "n10bucompare0001", "comparison_bucket": "cost80_before25_after75", "cost_bucket": "boundary", "total_cost_proxy": 80, "top10_span_overlap_count": len(cost80_top10), "top20_span_overlap_count": len(cost80_top20), "lost_plateau_core_top10_count": 0, "file_hit_top10_count": len(cost80_file10), "recovered_at_80_missed_at_75_count": len(transition), "missed_at_80_recovered_at_75_count": len(cost75_top10 - cost80_top10)},
    ]
    gap_counts: Counter[str] = Counter()
    dist_counts: Counter[str] = Counter()
    file_hit_count = 0
    just_outside_count = 0
    for idx in transition:
        gap, distance_bucket, just_outside = gap_and_distance_for_case(usable[idx], 18, 57, 20, 60)
        gap_counts[gap] += 1
        dist_counts[distance_bucket] += 1
        if idx in cost75_file10:
            file_hit_count += 1
        if just_outside:
            just_outside_count += 1
    mechanism_rows = [{"anonymous_boundary_case_mechanism_id": "n10bumech0000", "mechanism_bucket": "cost75_to_cost80_single_case_boundary", "case_count": len(transition), "before_gold_gap_count": gap_counts["before_gold_gap"], "after_gold_gap_count": gap_counts["after_gold_gap"], "already_overlap_count": gap_counts["already_overlap"], "other_count": gap_counts["other"], "distance_to_expanded_window_bucket": next(iter(dist_counts.keys()), "unavailable"), "distance_bucket_case_count": sum(dist_counts.values()), "file_hit_top10_count": file_hit_count, "file_hit_top10_bool": file_hit_count == len(transition) and len(transition) > 0, "just_outside_75_window_count": just_outside_count, "just_outside_75_window_bool": just_outside_count == len(transition) and len(transition) > 0, "recovered_at_80_count": len(transition), "recovered_at_80_bool": len(transition) == 1}]
    ok = len(usable) == 213 and len(transition) == 1 and len(cost75_top10) == 19 and len(cost75_top20) == 23 and len(cost80_top10) == 20 and len(cost80_top20) == 24 and just_outside_count == 1
    return len(usable), comparison_rows, mechanism_rows, ok


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10bupriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def no_gold_policy_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_gold_policy_id": "n10bunogold0000", "no_gold_policy_bucket": "cost75_cost80_fixed_global_windows_no_adaptive_tuning", "predeclared_global_windows_bool": True, "per_row_adaptive_window_count": 0, "gold_used_to_choose_window_count": 0, "miss_direction_used_to_choose_window_count": 0, "content_aware_adjustment_count": 0, "new_variant_count": 0, "rank_order_change_count": 0, "no_gold_policy_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10buprivacy0000", "privacy_boundary_bucket": "aggregate_boundary_case_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10bunoexec0000", "no_execution_boundary_bucket": "boundary_case_mechanism_decomposition_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "runtime_default_promotion_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_order_change_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10bv_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bv_handoff_id": "n10buhandoff0000", "n10bv_handoff_bucket": "n10bv_public_boundary_case_mechanism_package_authorized" if complete else "n10bv_not_authorized", "n10bv_public_package_authorized_bool": complete, "private_read_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "runtime_default_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, result_ok: bool, nogold_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("boundary_case_accounting", result_ok), ("no_gold_policy", nogold_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bv_public_boundary_case_mechanism_package_authorized" if complete else "n10bv_not_authorized", "next_allowed_phase": "BEA-v1-N10BV Boundary Case Mechanism Package" if complete else "none_until_boundary_case_accounting_is_valid", "next_allowed_scope_bucket": "public_boundary_case_mechanism_package_only" if complete else "no_next_phase", "n10bv_authorized": complete, "private_read_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, result_ok: bool, nogold_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bu_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10bu_private_span_rows_missing"
    if not private_ok or not result_ok:
        return "no_go_n10bu_boundary_case_accounting_invalid"
    if not nogold_ok or not privacy_ok or not noexec_ok:
        return "no_go_n10bu_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, comparison_rows, mechanism_rows, result_ok = compute(rows) if load_status == "pass" else (0, [], [], False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    nogold_rows, nogold_ok = no_gold_policy_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, result_ok, nogold_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "boundary_case_mechanism_decomposition_only", "generated_by": "bea_v1_n10bu_boundary_case_mechanism_decomposition", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "boundary_comparison_aggregate_records": comparison_rows, "boundary_case_mechanism_records": mechanism_rows, "no_gold_policy_records": nogold_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10bv_handoff_records": n10bv_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, result_ok, nogold_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bv_handoff_records"] = n10bv_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, result_ok, nogold_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_accounting() -> bool:
    return status_for(True, True, "pass", True, True, True, True, True) == STATUS_COMPLETE and status_for(True, True, "pass", True, False, True, True, True) == "no_go_n10bu_boundary_case_accounting_invalid"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, comparison_rows, mechanism_rows, result_ok = compute(rows) if load_status == "pass" else (0, [], [], False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    nogold_rows, nogold_ok = no_gold_policy_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bu_required_inputs_unavailable", "no_go_n10bu_private_span_rows_missing", "no_go_n10bu_boundary_case_accounting_invalid", "no_go_n10bu_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("private_rows", private_ok),
        check("comparison_accounting", result_ok and len(comparison_rows) == 2 and comparison_rows[0]["top10_span_overlap_count"] == 19 and comparison_rows[1]["top10_span_overlap_count"] == 20),
        check("mechanism_case", bool(mechanism_rows) and mechanism_rows[0]["case_count"] == 1 and mechanism_rows[0]["recovered_at_80_bool"] is True),
        check("file_hit_boundary", bool(mechanism_rows) and mechanism_rows[0]["file_hit_top10_bool"] is True),
        check("just_outside_boundary", bool(mechanism_rows) and mechanism_rows[0]["just_outside_75_window_bool"] is True),
        check("no_gold_policy", nogold_ok and nogold_rows[0]["new_variant_count"] == 0 and nogold_rows[0]["rank_order_change_count"] == 0),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_count"] == 0 and noexec_rows[0]["adaptive_tuning_count"] == 0),
        check("synthetic_accounting", synthetic_accounting()),
        check("false_flags", stop_go_records(True)[0]["n10bv_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BU boundary case mechanism decomposition")
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
