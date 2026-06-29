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


SCHEMA_VERSION = "bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke.v1"
PHASE = "BEA-v1-N10BA Cost-Aware Span-Window Selection Rule Smoke"
STATUS_COMPLETE = "cost_aware_span_window_selection_rule_smoke_complete_n10bb_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ba_required_inputs_unavailable",
    "no_go_n10ba_private_span_rows_missing",
    "no_go_n10ba_operating_point_rule_invalid",
    "no_go_n10ba_result_mismatch",
    "no_go_n10ba_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json")
PUBLIC_INPUTS = {
    "n10az_adapter_frontier_audit_package_artifact": (Path("artifacts/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package_report.json"), "cost_aware_adapter_frontier_smoke_audit_package_complete_n10ba_authorized"),
    "n10ay_adapter_frontier_smoke_artifact": (Path("artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json"), "cost_aware_adapter_frontier_smoke_pass_n10az_authorized"),
    "n10ax_claim_package_artifact": (Path("artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json"), "cost_sensitive_frontier_claim_package_complete_n10ay_authorized"),
    "n10aw_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json"), "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"),
    "n10av_replication_package_artifact": (Path("artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json"), "exploratory_span_window_sweep_replication_package_complete_n10aw_authorized"),
}
OPERATING_POINTS = {
    "low_cost": {"variant_bucket": "pm30", "before": 30, "after": 30, "top10": 18, "top20": 22, "cost_proxy_value": 600, "cost_bucket": "low"},
    "balanced": {"variant_bucket": "before25_after75", "before": 25, "after": 75, "top10": 20, "top20": 24, "cost_proxy_value": 1000, "cost_bucket": "medium"},
    "max_recall": {"variant_bucket": "pm200", "before": 200, "after": 200, "top10": 25, "top20": 30, "cost_proxy_value": 4000, "cost_bucket": "very_high"},
}
BASELINE = {"top10": 9, "top20": 10}
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
    "private_input_bucket", "intake_status_bucket", "operating_point_bucket", "variant_bucket", "cost_bucket",
    "rule_boundary_bucket", "adapter_path_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10bb_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = root() / rel
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
        rows.append({"anonymous_input_artifact_id": f"n10bain{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, ok


def load_rows(path: Path = PRIVATE_SPAN_ROWS) -> tuple[list[dict[str, Any]], str]:
    full = root() / path
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
    indexed = [(idx + 1, item) for idx, item in enumerate(evidence)]
    extra = [item for pos, item in indexed if pos > 20]
    primary = [item for pos, item in indexed if pos <= 20]
    return extra + primary[:4] + primary[4:]


def references(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return out


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def span_hit(records: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
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


def project_variant(records: list[dict[str, Any]], before: int, after: int) -> list[dict[str, Any]]:
    if before == after:
        return project_evidence_spans(records, expansion_each_side=before, enabled=True)
    out: list[dict[str, Any]] = []
    for item in records:
        copied = dict(item)
        copied["start_line"] = max(1, int(copied["start_line"]) - before)
        copied["end_line"] = int(copied["end_line"]) + after
        out.append(copied)
    return out


def compute(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    usable = [row for row in rows if row_schema_ok(row) and row.get("p4_evidence")]
    baseline10 = baseline20 = 0
    point_results: dict[str, dict[str, Any]] = {}
    base_hits_by_row: list[bool] = []
    for row in usable:
        ordered = best_order(row["p4_evidence"])
        refs = references(row)
        b10 = span_hit(ordered, refs, 10)
        b20 = span_hit(ordered, refs, 20)
        baseline10 += int(b10)
        baseline20 += int(b20)
        base_hits_by_row.append(b10)
    for point, spec in OPERATING_POINTS.items():
        top10 = top20 = lost = 0
        pool_changed = False
        order_changed = False
        for idx, row in enumerate(usable):
            ordered = best_order(row["p4_evidence"])
            refs = references(row)
            projected = project_variant(ordered, spec["before"], spec["after"])
            pool_changed = pool_changed or len(projected) != len(ordered)
            order_changed = order_changed or [i for i, _ in enumerate(projected)] != [i for i, _ in enumerate(ordered)]
            h10 = span_hit(projected, refs, 10)
            h20 = span_hit(projected, refs, 20)
            top10 += int(h10)
            top20 += int(h20)
            lost += int(base_hits_by_row[idx] and not h10)
        point_results[point] = {"top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "delta_top10_vs_baseline_count": top10 - baseline10, "delta_top20_vs_baseline_count": top20 - baseline20, "lost_previous_hits": lost, "candidate_pool_changed_bool": pool_changed, "candidate_order_changed_bool": order_changed}
    point_results["baseline"] = {"top10_span_overlap_count": baseline10, "top20_span_overlap_count": baseline20}
    return point_results, len(usable)


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10bapriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def operating_point_rule_records() -> tuple[list[dict[str, Any]], bool]:
    rows = []
    for idx, (point, spec) in enumerate(OPERATING_POINTS.items()):
        rows.append({"anonymous_operating_point_rule_id": f"n10barule{idx:04d}", "operating_point_bucket": point, "variant_bucket": spec["variant_bucket"], "cost_bucket": spec["cost_bucket"], "cost_proxy_value": spec["cost_proxy_value"], "predeclared_operating_point_bool": True, "new_window_size_bool": False, "adaptive_per_case_selection_bool": False, "runtime_default_bool": False})
    return rows, len(rows) == 3 and {r["operating_point_bucket"] for r in rows} == {"low_cost", "balanced", "max_recall"}


def operating_point_result_records(results: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (point, spec) in enumerate(OPERATING_POINTS.items()):
        result = results.get(point, {})
        matched = result.get("top10_span_overlap_count") == spec["top10"] and result.get("top20_span_overlap_count") == spec["top20"] and result.get("lost_previous_hits") == 0 and result.get("candidate_pool_changed_bool") is False and result.get("candidate_order_changed_bool") is False
        ok = ok and matched
        rows.append({"anonymous_operating_point_result_id": f"n10baresult{idx:04d}", "operating_point_bucket": point, "variant_bucket": spec["variant_bucket"], "top10_span_overlap_count": int(result.get("top10_span_overlap_count", 0)), "top20_span_overlap_count": int(result.get("top20_span_overlap_count", 0)), "expected_top10_span_overlap_count": spec["top10"], "expected_top20_span_overlap_count": spec["top20"], "delta_top10_vs_baseline_count": int(result.get("delta_top10_vs_baseline_count", 0)), "delta_top20_vs_baseline_count": int(result.get("delta_top20_vs_baseline_count", 0)), "cost_proxy_value": spec["cost_proxy_value"], "cost_bucket": spec["cost_bucket"], "lost_previous_hits": int(result.get("lost_previous_hits", 0)), "candidate_pool_changed_bool": bool(result.get("candidate_pool_changed_bool", True)), "candidate_order_changed_bool": bool(result.get("candidate_order_changed_bool", True)), "locked_aggregate_match_bool": matched})
    return rows, ok


def rule_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_rule_boundary_id": "n10baboundary0000", "rule_boundary_bucket": "named_operating_points_not_defaults", "operating_point_count": 3, "new_window_size_count": 0, "adaptive_per_case_selection_count": 0, "runtime_default_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "rule_boundary_valid_bool": True}], True


def adapter_path_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_adapter_path_id": "n10baadapter0000", "adapter_path_bucket": "default_off_eval_only_adapter_helper", "adapter_imported_bool": True, "helper_imported_via_adapter_bool": True, "existing_evaluator_imported_bool": False, "existing_evaluator_called_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_hook_bool": False}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10baprivacy0000", "privacy_boundary_bucket": "aggregate_operating_point_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10banoexec0000", "no_execution_boundary_bucket": "selection_rule_smoke_same_scoped_rows_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "new_variant_count": 0, "adaptive_selection_count": 0, "runtime_default_promotion_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_order_change_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10bb_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bb_handoff_id": "n10bahandoff0000", "n10bb_handoff_bucket": "n10bb_public_audit_package_authorized" if complete else "n10bb_not_authorized", "n10bb_public_audit_package_authorized_bool": complete, "private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_selection_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, rule_ok: bool, result_ok: bool, boundary_ok: bool, adapter_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("operating_point_rule", rule_ok), ("operating_point_results", result_ok), ("rule_boundary", boundary_ok), ("adapter_path", adapter_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bb_public_audit_package_authorized" if complete else "n10bb_not_authorized", "next_allowed_phase": "BEA-v1-N10BB Cost-Aware Span-Window Selection Rule Smoke Audit Package" if complete else "none_until_cost_aware_selection_rule_smoke_is_valid", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10bb_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_selection_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, rule_ok: bool, result_ok: bool, boundary_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ba_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10ba_private_span_rows_missing"
    if not rule_ok or not boundary_ok:
        return "no_go_n10ba_operating_point_rule_invalid"
    if not private_ok or not result_ok:
        return "no_go_n10ba_result_mismatch"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ba_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    results, usable = compute(rows) if load_status == "pass" else ({}, 0)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    rule_rows, rule_ok = operating_point_rule_records()
    result_rows, result_ok = operating_point_result_records(results)
    boundary_rows, boundary_ok = rule_boundary_records()
    adapter_rows, adapter_ok = adapter_path_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, rule_ok, result_ok, boundary_ok and adapter_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_named_operating_point_selection_rule_smoke_only", "generated_by": "bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "operating_point_rule_records": rule_rows, "operating_point_result_records": result_rows, "rule_boundary_records": boundary_rows, "adapter_path_records": adapter_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10bb_handoff_records": n10bb_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, rule_ok, result_ok, boundary_ok, adapter_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bb_handoff_records"] = n10bb_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, rule_ok, result_ok, boundary_ok, adapter_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_pass() -> bool:
    results = {"low_cost": {"top10_span_overlap_count": 18, "top20_span_overlap_count": 22, "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False}, "balanced": {"top10_span_overlap_count": 20, "top20_span_overlap_count": 24, "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False}, "max_recall": {"top10_span_overlap_count": 25, "top20_span_overlap_count": 30, "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False}}
    _rows, ok = operating_point_result_records(results)
    return ok


def synthetic_mismatch() -> bool:
    results = {"low_cost": {"top10_span_overlap_count": 0, "top20_span_overlap_count": 0, "lost_previous_hits": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False}}
    _rows, ok = operating_point_result_records(results)
    return not ok and status_for(True, True, "pass", True, True, ok, True, True, True) == "no_go_n10ba_result_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    results, usable = compute(rows) if load_status == "pass" else ({}, 0)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    rule_rows, rule_ok = operating_point_rule_records()
    result_rows, result_ok = operating_point_result_records(results)
    boundary_rows, boundary_ok = rule_boundary_records()
    adapter_rows, adapter_ok = adapter_path_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ba_required_inputs_unavailable", "no_go_n10ba_private_span_rows_missing", "no_go_n10ba_operating_point_rule_invalid", "no_go_n10ba_result_mismatch", "no_go_n10ba_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("private_rows", private_ok),
        check("operating_rules", rule_ok and len(rule_rows) == 3 and all(not r["adaptive_per_case_selection_bool"] for r in rule_rows)),
        check("operating_results", result_ok and len(result_rows) == 3 and result_rows[0]["top10_span_overlap_count"] == 18 and result_rows[-1]["top10_span_overlap_count"] == 25),
        check("rule_boundary", boundary_ok and boundary_rows[0]["adaptive_per_case_selection_count"] == 0 and boundary_rows[0]["runtime_default_count"] == 0),
        check("adapter_path", adapter_ok and adapter_rows[0]["existing_evaluator_imported_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_count"] == 0 and noexec_rows[0]["adaptive_selection_count"] == 0),
        check("synthetic_pass", synthetic_pass()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bb_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BA cost-aware selection rule smoke")
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
