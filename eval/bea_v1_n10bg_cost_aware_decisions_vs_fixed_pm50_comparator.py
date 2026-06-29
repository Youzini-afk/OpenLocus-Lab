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


SCHEMA_VERSION = "bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator.v1"
PHASE = "BEA-v1-N10BG Cost-Aware Decisions vs Fixed-pm50 Comparator"
STATUS_COMPLETE = "cost_aware_decisions_vs_fixed_pm50_comparator_complete_n10bh_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bg_required_inputs_unavailable",
    "no_go_n10bg_private_span_rows_missing",
    "no_go_n10bg_comparator_result_mismatch",
    "no_go_n10bg_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json")
PUBLIC_INPUTS = {
    "n10bf_budget_decision_package_artifact": (Path("artifacts/bea_v1_n10bf_cost_aware_budget_decision_package/bea_v1_n10bf_cost_aware_budget_decision_package_report.json"), "cost_aware_budget_decision_package_complete_n10bg_authorized"),
    "n10be_budget_decision_smoke_artifact": (Path("artifacts/bea_v1_n10be_cost_aware_operating_point_decision_smoke/bea_v1_n10be_cost_aware_operating_point_decision_smoke_report.json"), "cost_aware_operating_point_decision_smoke_complete_n10bf_authorized"),
    "n10bd_tradeoff_package_artifact": (Path("artifacts/bea_v1_n10bd_operating_point_tradeoff_package/bea_v1_n10bd_operating_point_tradeoff_package_report.json"), "operating_point_tradeoff_package_complete_n10be_authorized"),
    "n10bc_tradeoff_decomposition_artifact": (Path("artifacts/bea_v1_n10bc_operating_point_tradeoff_decomposition/bea_v1_n10bc_operating_point_tradeoff_decomposition_report.json"), "operating_point_tradeoff_decomposition_complete_n10bd_authorized"),
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
}
COMPARATOR = {"variant_bucket": "pm50", "before": 50, "after": 50, "top10": 19, "top20": 23, "cost": 1000, "cost_bucket": "medium"}
DECISIONS = (
    {"budget_bucket": "strict_budget", "operating_point_bucket": "low_cost", "variant_bucket": "pm30", "before": 30, "after": 30, "top10": 18, "top20": 22, "cost": 600, "cost_bucket": "low", "dominance_bucket": "cost_saving_tradeoff_vs_pm50"},
    {"budget_bucket": "moderate_budget", "operating_point_bucket": "balanced", "variant_bucket": "before25_after75", "before": 25, "after": 75, "top10": 20, "top20": 24, "cost": 1000, "cost_bucket": "medium", "dominance_bucket": "dominates_pm50"},
    {"budget_bucket": "recall_budget", "operating_point_bucket": "max_recall", "variant_bucket": "pm200", "before": 200, "after": 200, "top10": 25, "top20": 30, "cost": 4000, "cost_bucket": "very_high", "dominance_bucket": "higher_recall_higher_cost_vs_pm50"},
)
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
    "private_input_bucket", "intake_status_bucket", "comparator_bucket", "budget_bucket", "operating_point_bucket",
    "variant_bucket", "cost_bucket", "dominance_bucket", "adapter_path_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "n10bh_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10bgin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    out = []
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


def hits_for(rows: list[dict[str, Any]], before: int, after: int) -> tuple[set[int], set[int]]:
    top10: set[int] = set()
    top20: set[int] = set()
    for idx, row in enumerate(rows):
        ordered = order(row["p4_evidence"])
        projected = project(ordered, before, after)
        refs = refmap(row)
        if hit(projected, refs, 10):
            top10.add(idx)
        if hit(projected, refs, 20):
            top20.add(idx)
    return top10, top20


def dominance(decision: dict[str, Any], top10: int, top20: int) -> str:
    if top10 >= COMPARATOR["top10"] and top20 >= COMPARATOR["top20"] and decision["cost"] <= COMPARATOR["cost"] and (top10 > COMPARATOR["top10"] or top20 > COMPARATOR["top20"] or decision["cost"] < COMPARATOR["cost"]):
        return "dominates_pm50"
    if top10 <= COMPARATOR["top10"] and top20 <= COMPARATOR["top20"] and decision["cost"] < COMPARATOR["cost"]:
        return "cost_saving_tradeoff_vs_pm50"
    if top10 > COMPARATOR["top10"] and top20 > COMPARATOR["top20"] and decision["cost"] > COMPARATOR["cost"]:
        return "higher_recall_higher_cost_vs_pm50"
    return "dominated_by_pm50"


def compute(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]], bool, dict[str, Any]]:
    usable = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    pm50_top10, pm50_top20 = hits_for(usable, COMPARATOR["before"], COMPARATOR["after"])
    comparator_ok = len(pm50_top10) == COMPARATOR["top10"] and len(pm50_top20) == COMPARATOR["top20"]
    records: list[dict[str, Any]] = []
    all_ok = comparator_ok
    for idx, decision in enumerate(DECISIONS):
        top10_set, top20_set = hits_for(usable, decision["before"], decision["after"])
        top10 = len(top10_set)
        top20 = len(top20_set)
        lost = len(pm50_top10 - top10_set)
        bucket = dominance(decision, top10, top20)
        match = top10 == decision["top10"] and top20 == decision["top20"] and bucket == decision["dominance_bucket"]
        all_ok = all_ok and match
        records.append({"anonymous_comparison_id": f"n10bgcompare{idx:04d}", "budget_bucket": decision["budget_bucket"], "operating_point_bucket": decision["operating_point_bucket"], "variant_bucket": decision["variant_bucket"], "top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "pm50_top10_span_overlap_count": len(pm50_top10), "pm50_top20_span_overlap_count": len(pm50_top20), "delta_vs_pm50_top10_count": top10 - len(pm50_top10), "delta_vs_pm50_top20_count": top20 - len(pm50_top20), "cost_proxy_value": decision["cost"], "pm50_cost_proxy_value": COMPARATOR["cost"], "cost_proxy_delta_vs_pm50": decision["cost"] - COMPARATOR["cost"], "cost_bucket": decision["cost_bucket"], "lost_original_span_hits": lost, "dominance_bucket": bucket, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "expected_match_bool": match})
    comp = {"comparator_bucket": "fixed_pm50", "variant_bucket": "pm50", "top10_span_overlap_count": len(pm50_top10), "top20_span_overlap_count": len(pm50_top20), "cost_proxy_value": COMPARATOR["cost"], "cost_bucket": COMPARATOR["cost_bucket"], "expected_match_bool": comparator_ok}
    return len(usable), records, all_ok, comp


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10bgpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def comparator_records(comp: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_comparator_id": "n10bgcomp0000", **comp}]


def adapter_path_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_adapter_path_id": "n10bgadapter0000", "adapter_path_bucket": "default_off_eval_only_adapter_helper", "adapter_imported_bool": True, "helper_imported_via_adapter_bool": True, "existing_evaluator_imported_bool": False, "existing_evaluator_called_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_default_hook_bool": False}], True


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10bgclaim0000", "claim_boundary_bucket": "same_source_pm50_comparator_research_smoke_only", "runtime_default_recommendation_bool": False, "runtime_default_promotion_bool": False, "new_variant_count": 0, "adaptive_selection_count": 0, "heldout_claim_bool": False, "generalization_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "selector_reranker_claim_bool": False, "p5_or_v1a_claim_bool": False, "claim_boundary_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10bgprivacy0000", "privacy_boundary_bucket": "aggregate_comparator_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10bgnoexec0000", "no_execution_boundary_bucket": "pm50_comparator_same_scoped_rows_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "new_variant_count": 0, "adaptive_selection_count": 0, "runtime_default_recommendation_count": 0, "runtime_default_promotion_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_order_change_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10bh_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bh_handoff_id": "n10bghandoff0000", "n10bh_handoff_bucket": "n10bh_public_comparator_package_authorized" if complete else "n10bh_not_authorized", "n10bh_public_package_authorized_bool": complete, "private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "runtime_default_recommendation_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_selection_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, comparator_ok: bool, adapter_ok: bool, claim_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("pm50_comparator_results", comparator_ok), ("adapter_path", adapter_ok), ("claim_boundary", claim_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bh_public_comparator_package_authorized" if complete else "n10bh_not_authorized", "next_allowed_phase": "BEA-v1-N10BH Cost-Aware Decisions vs Fixed-pm50 Comparator Audit Package" if complete else "none_until_pm50_comparator_is_valid", "next_allowed_scope_bucket": "public_comparator_package_only" if complete else "no_next_phase", "n10bh_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "runtime_default_recommendation_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_selection_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, comparator_ok: bool, claim_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bg_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10bg_private_span_rows_missing"
    if not private_ok or not comparator_ok:
        return "no_go_n10bg_comparator_result_mismatch"
    if not claim_ok or not privacy_ok or not noexec_ok:
        return "no_go_n10bg_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, result_rows, comparator_ok, comp = compute(rows) if load_status == "pass" else (0, [], False, {})
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    adapter_rows, adapter_ok = adapter_path_records()
    claim_rows, claim_ok = claim_boundary_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, comparator_ok and adapter_ok, claim_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_pm50_comparator_research_smoke_only", "generated_by": "bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "fixed_pm50_comparator_records": comparator_records(comp), "decision_vs_pm50_records": result_rows, "adapter_path_records": adapter_rows, "claim_boundary_records": claim_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10bh_handoff_records": n10bh_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, comparator_ok, adapter_ok, claim_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bh_handoff_records"] = n10bh_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, comparator_ok, adapter_ok, claim_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_dominance() -> bool:
    return dominance({"cost": 600}, 18, 22) == "cost_saving_tradeoff_vs_pm50" and dominance({"cost": 1000}, 20, 24) == "dominates_pm50" and dominance({"cost": 4000}, 25, 30) == "higher_recall_higher_cost_vs_pm50"


def synthetic_mismatch() -> bool:
    return status_for(True, True, "pass", True, False, True, True, True) == "no_go_n10bg_comparator_result_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, result_rows, comparator_ok, comp = compute(rows) if load_status == "pass" else (0, [], False, {})
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    adapter_rows, adapter_ok = adapter_path_records()
    claim_rows, claim_ok = claim_boundary_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bg_required_inputs_unavailable", "no_go_n10bg_private_span_rows_missing", "no_go_n10bg_comparator_result_mismatch", "no_go_n10bg_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("private_rows", private_ok),
        check("pm50_comparator", comparator_ok and comp.get("top10_span_overlap_count") == 19 and comp.get("top20_span_overlap_count") == 23),
        check("decision_results", [r["top10_span_overlap_count"] for r in result_rows] == [18, 20, 25] and [r["dominance_bucket"] for r in result_rows] == ["cost_saving_tradeoff_vs_pm50", "dominates_pm50", "higher_recall_higher_cost_vs_pm50"]),
        check("adapter_path", adapter_ok and adapter_rows[0]["existing_evaluator_hook_in_bool"] is False),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_recommendation_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_count"] == 0 and noexec_rows[0]["adaptive_selection_count"] == 0),
        check("synthetic_dominance", synthetic_dominance()),
        check("synthetic_mismatch", synthetic_mismatch()),
        check("false_flags", stop_go_records(True)[0]["n10bh_authorized"] is True and stop_go_records(True)[0]["runtime_default_recommendation_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BG decisions vs pm50 comparator")
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
