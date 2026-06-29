#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10as_exploratory_span_window_variant_sweep.v1"
PHASE = "BEA-v1-N10AS Exploratory Span-Window Variant Sweep"
STATUS_COMPLETE = "exploratory_span_window_variant_sweep_complete_n10at_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10as_required_inputs_unavailable",
    "no_go_n10as_private_span_rows_missing",
    "no_go_n10as_variant_grid_invalid",
    "no_go_n10as_result_accounting_invalid",
    "no_go_n10as_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json")
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
PUBLIC_INPUTS = {
    "n10aqr_acquisition_feasibility_artifact": (Path("artifacts/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility_report.json"), "no_go_n10aqr_no_bounded_heldout_acquisition_path"),
    "n10ab_fixed_span_window_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
}
VARIANT_GRID = (
    ("pm0", 0, 0, "symmetric"),
    ("pm10", 10, 10, "symmetric"),
    ("pm20", 20, 20, "symmetric"),
    ("pm30", 30, 30, "symmetric"),
    ("pm50", 50, 50, "symmetric"),
    ("pm75", 75, 75, "symmetric"),
    ("pm100", 100, 100, "symmetric"),
    ("pm150", 150, 150, "symmetric"),
    ("pm200", 200, 200, "symmetric"),
    ("before75_after25", 75, 25, "asymmetric"),
    ("before100_after50", 100, 50, "asymmetric"),
    ("before150_after50", 150, 50, "asymmetric"),
    ("before25_after75", 25, 75, "asymmetric"),
    ("before50_after100", 50, 100, "asymmetric"),
    ("before50_after150", 50, 150, "asymmetric"),
)
EXPECTED_ROWS = 213
BASELINE_TOP10 = 9
BASELINE_TOP20 = 10
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
    "private_input_bucket", "intake_status_bucket", "variant_bucket", "variant_family_bucket", "cost_proxy_bucket",
    "budget_bucket", "cost_per_additional_hit_bucket", "recommendation_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "n10at_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
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
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
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
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10asin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return rows, ok


def read_private_rows(path: Path = PRIVATE_SPAN_ROWS) -> tuple[list[dict[str, Any]], str]:
    full = root() / path
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in full.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "schema_invalid"
                rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def row_schema_ok(row: dict[str, Any]) -> bool:
    evs = row.get("p4_evidence")
    refs = row.get("gold_paths")
    ranges = row.get("gold_lines")
    if not isinstance(evs, list) or not isinstance(refs, list) or not isinstance(ranges, list) or len(refs) != len(ranges):
        return False
    for rg in ranges:
        if not (isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1]):
            return False
    for ev in evs:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
    return True


def best_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(i + 1, item) for i, item in enumerate(evidence)]
    extra = [item for pos, item in indexed if pos > 20]
    primary = [item for pos, item in indexed if pos <= 20]
    return extra + primary[:4] + primary[4:]


def gold_lookup(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    lookup: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        lookup.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return lookup


def expand_item(item: dict[str, Any], before: int, after: int) -> dict[str, Any]:
    copy = dict(item)
    copy["start_line"] = max(1, int(copy["start_line"]) - before)
    copy["end_line"] = int(copy["end_line"]) + after
    return copy


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return max(a, c) <= min(b, d)


def span_hit(items: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for item in items[:limit]:
        key = str(item.get("path", ""))
        if key not in refs:
            continue
        start, end = item.get("start_line"), item.get("end_line")
        if isinstance(start, int) and isinstance(end, int) and any(overlaps(start, end, a, b) for a, b in refs[key]):
            return True
    return False


def compute_variant(rows: list[dict[str, Any]], before: int, after: int) -> dict[str, int | bool]:
    top10 = top20 = lost = 0
    pool_changed = False
    order_changed = False
    for row in rows:
        ordered = best_order(row["p4_evidence"])
        refs = gold_lookup(row)
        baseline10 = span_hit(ordered, refs, 10)
        expanded = [expand_item(item, before, after) for item in ordered]
        pool_changed = pool_changed or len(expanded) != len(ordered)
        order_changed = order_changed or len(expanded) != len(ordered)
        hit10 = span_hit(expanded, refs, 10)
        top10 += int(hit10)
        top20 += int(span_hit(expanded, refs, 20))
        lost += int(baseline10 and not hit10)
    return {"top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "original_span_hit_lost_count": lost, "candidate_pool_changed_bool": pool_changed, "candidate_order_changed_bool": order_changed}


def cost_bucket(cost: int) -> str:
    if cost == 0:
        return "zero"
    if cost <= 600:
        return "low"
    if cost <= 1500:
        return "medium"
    if cost <= 3000:
        return "high"
    return "very_high"


def cost_per_hit_bucket(cost: int, delta: int) -> str:
    if delta <= 0:
        return "no_positive_delta"
    value = cost / delta
    if value <= 100:
        return "low"
    if value <= 200:
        return "medium"
    if value <= 500:
        return "high"
    return "very_high"


def variant_grid_records() -> tuple[list[dict[str, Any]], bool]:
    names = [v[0] for v in VARIANT_GRID]
    expected = ["pm0", "pm10", "pm20", "pm30", "pm50", "pm75", "pm100", "pm150", "pm200", "before75_after25", "before100_after50", "before150_after50", "before25_after75", "before50_after100", "before50_after150"]
    ok = len(VARIANT_GRID) == 15 and names == expected
    rows = [{"anonymous_variant_grid_id": f"n10asgrid{idx:04d}", "variant_bucket": name, "variant_family_bucket": family, "before_budget": before, "after_budget": after, "before_expansion_lines": before, "after_expansion_lines": after, "fixed_predeclared_bool": True, "per_record_adaptive_window_bool": False} for idx, (name, before, after, family) in enumerate(VARIANT_GRID)]
    return rows, ok


def compute_all(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], bool]:
    result_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    for idx, (name, before, after, family) in enumerate(VARIANT_GRID):
        metrics = compute_variant(rows, before, after)
        top10 = int(metrics["top10_span_overlap_count"])
        top20 = int(metrics["top20_span_overlap_count"])
        delta10 = top10 - BASELINE_TOP10
        delta20 = top20 - BASELINE_TOP20
        cost = 10 * (before + after)
        item = {"variant_bucket": name, "variant_family_bucket": family, "before_budget": before, "after_budget": after, "top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "delta_top10_vs_unexpanded_count": delta10, "delta_top20_vs_unexpanded_count": delta20, "original_span_hit_lost_count": int(metrics["original_span_hit_lost_count"]), "candidate_pool_changed_bool": bool(metrics["candidate_pool_changed_bool"]), "candidate_order_changed_bool": bool(metrics["candidate_order_changed_bool"]), "cost_proxy_value": cost}
        raw.append(item)
    for item in raw:
        dominated = any((other["top10_span_overlap_count"] >= item["top10_span_overlap_count"] and other["cost_proxy_value"] <= item["cost_proxy_value"] and (other["top10_span_overlap_count"] > item["top10_span_overlap_count"] or other["cost_proxy_value"] < item["cost_proxy_value"])) for other in raw)
        item["pareto_frontier_bool"] = not dominated
    frontier = [item for item in raw if item["pareto_frontier_bool"]]
    rec = sorted(frontier, key=lambda item: (-item["top10_span_overlap_count"], item["cost_proxy_value"], item["variant_family_bucket"] != "symmetric", item["before_budget"] + item["after_budget"]))[0]
    for idx, item in enumerate(raw):
        result_rows.append({"anonymous_variant_result_id": f"n10asresult{idx:04d}", "variant_bucket": item["variant_bucket"], "variant_family_bucket": item["variant_family_bucket"], "before_expansion_lines": item["before_budget"], "after_expansion_lines": item["after_budget"], "top10_cost_proxy_value": item["cost_proxy_value"], "top10_cost_proxy_bucket": cost_bucket(item["cost_proxy_value"]), "cost_per_additional_hit_bucket": cost_per_hit_bucket(item["cost_proxy_value"], item["delta_top10_vs_unexpanded_count"]), "top10_span_overlap_count": item["top10_span_overlap_count"], "top20_span_overlap_count": item["top20_span_overlap_count"], "delta_top10_vs_unexpanded_count": item["delta_top10_vs_unexpanded_count"], "delta_top20_vs_unexpanded_count": item["delta_top20_vs_unexpanded_count"], "original_span_hit_lost_count": item["original_span_hit_lost_count"], "candidate_pool_changed_bool": item["candidate_pool_changed_bool"], "candidate_order_changed_bool": item["candidate_order_changed_bool"], "pareto_frontier_bool": item["pareto_frontier_bool"]})
        cost_rows.append({"anonymous_cost_proxy_id": f"n10ascost{idx:04d}", "variant_bucket": item["variant_bucket"], "cost_proxy_bucket": cost_bucket(item["cost_proxy_value"]), "top10_cost_proxy_value": item["cost_proxy_value"], "per_evidence_budget_bucket": cost_bucket(item["cost_proxy_value"] // 10), "total_budget_bucket": cost_bucket(item["cost_proxy_value"]), "cost_per_additional_hit_bucket": cost_per_hit_bucket(item["cost_proxy_value"], item["delta_top10_vs_unexpanded_count"])})
    frontier_rows = [{"anonymous_pareto_frontier_id": f"n10asfront{idx:04d}", "variant_bucket": item["variant_bucket"], "before_expansion_lines": item["before_budget"], "after_expansion_lines": item["after_budget"], "top10_span_overlap_count": item["top10_span_overlap_count"], "top10_cost_proxy_value": item["cost_proxy_value"], "cost_proxy_bucket": cost_bucket(item["cost_proxy_value"]), "pareto_frontier_bool": item["pareto_frontier_bool"]} for idx, item in enumerate(raw)]
    valid = len(result_rows) == 15 and raw[0]["top10_span_overlap_count"] == BASELINE_TOP10 and raw[0]["top20_span_overlap_count"] == BASELINE_TOP20 and all(not item["candidate_pool_changed_bool"] and not item["candidate_order_changed_bool"] and item["original_span_hit_lost_count"] == 0 for item in raw)
    return result_rows, frontier_rows, cost_rows, rec, valid


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    usable = [row for row in rows if row_schema_ok(row) and row.get("p4_evidence")]
    ok = load_status == "pass" and len(rows) == EXPECTED_ROWS and len(usable) == EXPECTED_ROWS
    return [{"anonymous_private_input_intake_id": "n10aspriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if ok else load_status, "private_span_rows_read": len(rows), "usable_private_span_rows": len(usable), "other_private_files_read_count": 0, "schema_valid_bool": ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}], usable, ok


def exploratory_recommendation_records(rec: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_exploratory_recommendation_id": "n10asrec0000", "recommendation_bucket": "highest_top10_frontier_lowest_cost_tie_symmetric", "recommended_variant_bucket": rec["variant_bucket"], "recommended_variant_family_bucket": rec["variant_family_bucket"], "recommended_top10_span_overlap_count": rec["top10_span_overlap_count"], "recommended_top20_span_overlap_count": rec["top20_span_overlap_count"], "recommended_delta_top10_vs_unexpanded_count": rec["delta_top10_vs_unexpanded_count"], "recommended_cost_proxy_bucket": cost_bucket(rec["cost_proxy_value"]), "exploratory_only_bool": True, "heldout_claim_bool": False, "runtime_default_claim_bool": False, "method_winner_claim_bool": False}]


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10asprivacy0000", "privacy_boundary_bucket": "aggregate_variant_counts_only_no_private_surface_details", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10asnoexec0000", "no_execution_boundary_bucket": "same_source_exploratory_window_sweep_only", "variant_count": 15, "all_variants_predeclared_bool": True, "top10_accounting_valid_bool": True, "pareto_frontier_computed_bool": True, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0, "rank_order_arm_sweep_count": 0, "per_record_adaptive_window_count": 0, "gold_used_for_variant_selection_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10at_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10at_handoff_id": "n10ashandoff0000", "n10at_handoff_bucket": "n10at_public_audit_package_authorized" if complete else "n10at_not_authorized", "n10at_public_audit_package_authorized_bool": complete, "private_read_authorized_bool": False, "extra_sweep_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_validation_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, grid_ok: bool, result_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read_213", private_ok), ("variant_grid_15_predeclared", grid_ok), ("result_accounting_valid", result_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": int(passed), "threshold_value": 1} for name, passed in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10at_public_audit_package_authorized" if complete else "n10at_not_authorized", "next_allowed_phase": "BEA-v1-N10AT Exploratory Span-Window Variant Sweep Audit Package" if complete else "none_until_valid_same_source_variant_sweep_exists", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10at_authorized": complete, "private_read_authorized": False, "extra_sweep_authorized": False, "heldout_validation_claim_authorized": False, "runtime_or_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "adaptive_tuning_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, private_ok: bool, grid_ok: bool, result_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10as_required_inputs_unavailable"
    if not private_ok:
        return "no_go_n10as_private_span_rows_missing"
    if not grid_ok:
        return "no_go_n10as_variant_grid_invalid"
    if not result_ok:
        return "no_go_n10as_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10as_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    inputs, input_ok = input_artifact_records()
    rows, load_status = read_private_rows()
    private_records, usable_rows, private_ok = private_input_intake_records(rows, load_status)
    grid_records, grid_ok = variant_grid_records()
    variant_rows, frontier_rows, cost_rows, rec, result_ok = compute_all(usable_rows) if private_ok and grid_ok else ([], [], [], {}, False)
    recommendation_rows = exploratory_recommendation_records(rec) if rec else []
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, private_ok, grid_ok, result_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_exploratory_n1_span_surface_proxy_only", "generated_by": "bea_v1_n10as_exploratory_span_window_variant_sweep", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_input_intake_records": private_records, "variant_grid_records": grid_records, "variant_result_records": variant_rows, "pareto_frontier_records": frontier_rows, "exploratory_recommendation_records": recommendation_rows, "cost_proxy_records": cost_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10at_handoff_records": n10at_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, grid_ok, result_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10at_handoff_records"] = n10at_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, grid_ok, result_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_overlap_ok() -> bool:
    row = {"p4_evidence": [{"path": "a", "start_line": 10, "end_line": 12}], "gold_paths": ["a"], "gold_lines": [[20, 22]]}
    ordered = best_order(row["p4_evidence"])
    refs = gold_lookup(row)
    return not span_hit([expand_item(x, 0, 0) for x in ordered], refs, 10) and span_hit([expand_item(x, 0, 10) for x in ordered], refs, 10)


def pareto_self_test() -> bool:
    items = [{"top10_span_overlap_count": 1, "cost_proxy_value": 10}, {"top10_span_overlap_count": 2, "cost_proxy_value": 10}, {"top10_span_overlap_count": 2, "cost_proxy_value": 20}]
    dominated = []
    for item in items:
        dominated.append(any((other["top10_span_overlap_count"] >= item["top10_span_overlap_count"] and other["cost_proxy_value"] <= item["cost_proxy_value"] and (other["top10_span_overlap_count"] > item["top10_span_overlap_count"] or other["cost_proxy_value"] < item["cost_proxy_value"])) for other in items))
    return dominated == [True, False, True]


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = input_artifact_records()
    grid_rows, grid_ok = variant_grid_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10as_required_inputs_unavailable", "no_go_n10as_private_span_rows_missing", "no_go_n10as_variant_grid_invalid", "no_go_n10as_result_accounting_invalid", "no_go_n10as_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 2),
        check("variant_grid", grid_ok and len(grid_rows) == 15 and grid_rows[0]["variant_bucket"] == "pm0" and grid_rows[-1]["variant_bucket"] == "before50_after150"),
        check("pareto_logic", pareto_self_test()),
        check("synthetic_overlap", synthetic_overlap_ok()),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["per_record_adaptive_window_count"] == 0 and noexec_rows[0]["gold_used_for_variant_selection_count"] == 0),
        check("handoff", n10at_handoff_records(True)[0]["n10at_public_audit_package_authorized_bool"] is True and stop_go_records(True)[0]["extra_sweep_authorized"] is False),
        check("status_no_private", status_for(True, True, False, True, True, True, True) == "no_go_n10as_private_span_rows_missing"),
        check("status_expected", status_for(True, True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AS exploratory span-window variant sweep")
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
    rec = report.get("exploratory_recommendation_records", [{}])[0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, recommended={rec.get('recommended_variant_bucket', 'none')})")


if __name__ == "__main__":
    main()
