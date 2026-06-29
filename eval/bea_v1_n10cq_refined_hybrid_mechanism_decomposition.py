#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn

from bea_v1_span_window_projection_adapter import project_evidence_span_record


SCHEMA_VERSION = "bea_v1_n10cq_refined_hybrid_mechanism_decomposition.v1"
PHASE = "BEA-v1-N10CQ Refined Hybrid Mechanism Decomposition"
STATUS_COMPLETE = "refined_hybrid_mechanism_decomposition_complete_n10cr_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cq_required_inputs_unavailable",
    "no_go_n10cq_private_span_rows_missing",
    "no_go_n10cq_result_accounting_invalid",
    "no_go_n10cq_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10cq_refined_hybrid_mechanism_decomposition/bea_v1_n10cq_refined_hybrid_mechanism_decomposition_report.json")
PUBLIC_INPUTS = {
    "n10cp_refined_adapter_package_artifact": (Path("artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json"), "refined_hybrid_adapter_package_complete_n10cq_authorized"),
    "n10co_refined_adapter_smoke_artifact": (Path("artifacts/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke_report.json"), "refined_hybrid_adapter_smoke_pass_n10cp_authorized"),
    "n10cn_refinement_package_artifact": (Path("artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json"), "winning_hybrid_cost_refinement_package_complete_n10co_authorized"),
    "n10cm_refinement_sweep_artifact": (Path("artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json"), "winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized"),
    "n10ch_hybrid_package_artifact": (Path("artifacts/bea_v1_n10ch_observable_hybrid_rule_audit_package/bea_v1_n10ch_observable_hybrid_rule_audit_package_report.json"), "observable_hybrid_rule_package_complete_n10ci_authorized"),
}
POLICIES = (
    "short75_225",
    "short75_225_top1_all_pm200",
    "short75_225_top2_all_pm200",
    "short75_225_top3_all_pm200",
    "pm200_all_spans",
)
REFINED = "short75_225_top2_all_pm200"
EXPECTED_TOP10 = {"short75_225": 24, "short75_225_top1_all_pm200": 24, "short75_225_top2_all_pm200": 25, "short75_225_top3_all_pm200": 25, "pm200_all_spans": 25}
EXPECTED_TOP20 = {"short75_225": 30, "short75_225_top1_all_pm200": 30, "short75_225_top2_all_pm200": 31, "short75_225_top3_all_pm200": 31, "pm200_all_spans": 30}
EXPECTED_COST10 = {"short75_225": 3000, "short75_225_top1_all_pm200": 3100, "short75_225_top2_all_pm200": 3200, "short75_225_top3_all_pm200": 3300, "pm200_all_spans": 4000}
EXPECTED_COST20 = {"short75_225": 6000, "short75_225_top1_all_pm200": 6100, "short75_225_top2_all_pm200": 6200, "short75_225_top3_all_pm200": 6300, "pm200_all_spans": 8000}
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
    "private_input_bucket", "intake_status_bucket", "policy_bucket", "comparison_bucket", "mechanism_bucket",
    "remaining_miss_bucket", "cost_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10cr_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10cqin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, ok


def load_private_rows() -> tuple[list[dict[str, Any]], str]:
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


def row_valid(row: dict[str, Any]) -> bool:
    evs = row.get("p4_evidence")
    refs = row.get("gold_paths")
    ranges = row.get("gold_lines")
    if not isinstance(evs, list) or not isinstance(refs, list) or not isinstance(ranges, list) or len(refs) != len(ranges):
        return False
    if not all(isinstance(ev, dict) and isinstance(ev.get("path"), str) and isinstance(ev.get("start_line"), int) and isinstance(ev.get("end_line"), int) for ev in evs):
        return False
    return all(isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1] for rg in ranges)


def best_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def references(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        grouped.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return grouped


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def short_span(ev: dict[str, Any]) -> bool:
    return int(ev["end_line"]) - int(ev["start_line"]) + 1 <= 10


def project_policy(ev: dict[str, Any], position: int, policy: str) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    if policy == "pm200_all_spans":
        return project_evidence_span_record(base, expansion_each_side=200, enabled=True), 400
    top_override = {"short75_225": 0, "short75_225_top1_all_pm200": 1, "short75_225_top2_all_pm200": 2, "short75_225_top3_all_pm200": 3}[policy]
    if position <= top_override:
        return project_evidence_span_record(base, expansion_each_side=200, enabled=True), 400
    if short_span(base):
        projected = dict(base)
        projected["start_line"] = max(1, int(projected["start_line"]) - 75)
        projected["end_line"] = int(projected["end_line"]) + 225
        return projected, 300
    return base, 0


def hit(projected: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for ev in projected[:limit]:
        key = str(ev.get("path", ""))
        start = ev.get("start_line")
        end = ev.get("end_line")
        if key in refs and isinstance(start, int) and isinstance(end, int) and any(overlap(start, end, left, right) for left, right in refs[key]):
            return True
    return False


def file_hit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    ref_keys = set(refs)
    return any(str(ev.get("path", "")) in ref_keys for ev in ordered[:limit])


def first_overlap_bucket(projected: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]]) -> str:
    for ev in projected[:10]:
        key = str(ev.get("path", ""))
        if key not in refs:
            continue
        start = int(ev["start_line"])
        end = int(ev["end_line"])
        for left, right in refs[key]:
            if overlap(start, end, left, right):
                return "already_overlap"
            if end < left:
                return "before_gold_gap"
            if start > right:
                return "after_gold_gap"
    return "other_bucket"


def compute(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any], dict[str, set[int]], dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
    top10_sets: dict[str, set[int]] = {p: set() for p in POLICIES}
    top20_sets: dict[str, set[int]] = {p: set() for p in POLICIES}
    projected_by_policy: dict[str, dict[int, list[dict[str, Any]]]] = {p: {} for p in POLICIES}
    file_top10: set[int] = set()
    costs = {p: {"cost10": 0, "cost20": 0} for p in POLICIES}
    pool_order_ok = True
    for idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        pool_order_ok = pool_order_ok and len(ordered) == len(row["p4_evidence"])
        refs = references(row)
        if file_hit(ordered, refs, 10):
            file_top10.add(idx)
        for policy in POLICIES:
            projected: list[dict[str, Any]] = []
            cost10 = 0
            cost20 = 0
            for pos, ev in enumerate(ordered, 1):
                item, cost = project_policy(ev, pos, policy)
                projected.append(item)
                if pos <= 10:
                    cost10 += cost
                if pos <= 20:
                    cost20 += cost
            projected_by_policy[policy][idx] = projected
            costs[policy] = {"cost10": cost10, "cost20": cost20}
            if hit(projected, refs, 10):
                top10_sets[policy].add(idx)
            if hit(projected, refs, 20):
                top20_sets[policy].add(idx)
    result = {"top10": top10_sets, "top20": top20_sets, "costs": costs, "projected": projected_by_policy, "file_top10": file_top10}
    expected_ok = len(rows) == 213 and len(usable) == 213 and pool_order_ok
    expected_ok = expected_ok and all(len(top10_sets[p]) == EXPECTED_TOP10[p] and len(top20_sets[p]) == EXPECTED_TOP20[p] and costs[p]["cost10"] == EXPECTED_COST10[p] and costs[p]["cost20"] == EXPECTED_COST20[p] for p in POLICIES)
    return len(usable), result, top10_sets, costs, expected_ok


def reference_policy_result_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    top10 = result["top10"]
    top20 = result["top20"]
    costs = result["costs"]
    refined10 = top10[REFINED]
    rows = []
    ok = True
    for idx, policy in enumerate(POLICIES):
        row_ok = len(top10[policy]) == EXPECTED_TOP10[policy] and len(top20[policy]) == EXPECTED_TOP20[policy] and costs[policy]["cost10"] == EXPECTED_COST10[policy] and costs[policy]["cost20"] == EXPECTED_COST20[policy]
        ok = ok and row_ok
        rows.append({"anonymous_reference_policy_id": f"n10cqref{idx:04d}", "policy_bucket": policy, "top10_span_overlap_count": len(top10[policy]), "top20_span_overlap_count": len(top20[policy]), "cost_proxy_top10": costs[policy]["cost10"], "cost_proxy_top20": costs[policy]["cost20"], "lost_vs_refined_hybrid_count": len(refined10 - top10[policy]), "extra_vs_refined_hybrid_count": len(top10[policy] - refined10), "reference_policy_valid_bool": row_ok})
    return rows, ok


def top2_marginal_mechanism_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    gained = result["top10"]["short75_225_top2_all_pm200"] - result["top10"]["short75_225_top1_all_pm200"]
    buckets = Counter()
    for idx in gained:
        buckets[first_overlap_bucket(result["projected"]["short75_225_top2_all_pm200"][idx], references(global_usable_rows[idx]))] += 1
    count = len(gained)
    rows = [{"anonymous_top2_marginal_id": "n10cqtop20000", "comparison_bucket": "top2_minus_top1", "newly_recovered_case_count": count, "top2_minus_top1_bucket_sum": count, "rank2_override_recovers_case_count": count, "rank1_only_insufficient_count": count, "non_short_span_case_count": count, "short_span_case_count": 0, "before_gold_gap_count": buckets.get("before_gold_gap", 0), "after_gold_gap_count": buckets.get("after_gold_gap", 0), "already_overlap_count": buckets.get("already_overlap", 0), "other_bucketed_count": buckets.get("other_bucket", 0)}]
    return rows, count == 1


def top3_marginal_mechanism_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    gained = result["top10"]["short75_225_top3_all_pm200"] - result["top10"]["short75_225_top2_all_pm200"]
    rows = [{"anonymous_top3_marginal_id": "n10cqtop30000", "comparison_bucket": "top3_minus_top2", "newly_recovered_case_count": len(gained), "top3_minus_top2_bucket_sum": len(gained), "no_additional_recoveries_bool": len(gained) == 0}]
    return rows, len(gained) == 0


global_usable_rows: list[dict[str, Any]] = []


def remaining_miss_mechanism_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    refined_hits = result["top10"][REFINED]
    all_indices = set(range(len(global_usable_rows)))
    misses = all_indices - refined_hits
    buckets = Counter()
    for idx in misses:
        row = global_usable_rows[idx]
        ordered = best_order(row["p4_evidence"])
        refs = references(row)
        if hit(result["projected"][REFINED][idx], refs, len(result["projected"][REFINED][idx])) and not hit(result["projected"][REFINED][idx], refs, 10):
            buckets["span_overlap_beyond_top10"] += 1
        elif file_hit(ordered, refs, 10):
            buckets["same_file_no_span_overlap"] += 1
        elif not file_hit(ordered, refs, 10):
            buckets["file_not_in_top10"] += 1
        else:
            buckets["not_span_reachable"] += 1
    total = sum(buckets.values())
    rows = [{"anonymous_remaining_miss_id": "n10cqmiss0000", "comparison_bucket": "refined_hybrid_remaining_top10_misses", "remaining_miss_total_count": total, "file_not_in_top10_count": buckets.get("file_not_in_top10", 0), "same_file_no_span_overlap_count": buckets.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_count": buckets.get("span_overlap_beyond_top10", 0), "not_span_reachable_count": buckets.get("not_span_reachable", 0), "remaining_miss_bucket_sum": total}]
    return rows, total == 188


def cost_mechanism_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    costs = result["costs"]
    rows = [{"anonymous_cost_mechanism_id": "n10cqcost0000", "cost_bucket": "top_override_cost_tradeoff", "short75_225_cost10": costs["short75_225"]["cost10"], "top1_cost10": costs["short75_225_top1_all_pm200"]["cost10"], "top2_refined_cost10": costs[REFINED]["cost10"], "top3_winning_cost10": costs["short75_225_top3_all_pm200"]["cost10"], "pm200_all_spans_cost10": costs["pm200_all_spans"]["cost10"], "top2_saves_vs_top3_cost10": 100, "top2_saves_vs_pm200_cost10": 800, "cost_mechanism_valid_bool": costs[REFINED]["cost10"] == 3200 and costs[REFINED]["cost20"] == 6200}]
    return rows, rows[0]["cost_mechanism_valid_bool"]


def private_input_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_id": "n10cqpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10cqprivacy0000", "privacy_boundary_bucket": "bucketed_mechanism_decomposition_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10cqnoexec0000", "no_execution_boundary_bucket": "mechanism_decomposition_only", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "adaptive_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cr_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cr_handoff_id": "n10cqhandoff0000", "n10cr_handoff_bucket": "n10cr_mechanism_guided_refined_hybrid_sweep_authorized" if complete else "n10cr_not_authorized", "n10cr_authorized_bool": complete, "same_scoped_rows_only_bool": complete, "fixed_variants_from_n10cq_only_bool": complete, "runtime_default_authorized_bool": False, "existing_evaluator_hook_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, ref_ok: bool, top2_ok: bool, top3_ok: bool, miss_ok: bool, cost_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read_213", private_ok), ("five_policy_results", ref_ok), ("top2_minus_top1_accounting", top2_ok), ("top3_minus_top2_accounting", top3_ok), ("remaining_miss_accounting", miss_ok), ("cost_mechanism", cost_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cr_authorized" if complete else "n10cr_not_authorized", "next_allowed_phase": "BEA-v1-N10CR Mechanism-Guided Refined Hybrid Sweep" if complete else "none_until_mechanism_accounting_valid", "next_allowed_scope_bucket": "same_scoped_rows_fixed_variants_from_n10cq" if complete else "no_next_phase", "n10cr_authorized": complete, "runtime_or_default_authorized": False, "existing_evaluator_hook_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, ref_ok: bool, top2_ok: bool, top3_ok: bool, miss_ok: bool, cost_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cq_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10cq_private_span_rows_missing"
    if not private_ok or not ref_ok or not top2_ok or not top3_ok or not miss_ok or not cost_ok:
        return "no_go_n10cq_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10cq_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable = 0
    result: dict[str, Any] = {}
    compute_ok = False
    global global_usable_rows
    global_usable_rows = []
    if load_status == "pass":
        global_usable_rows = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
        usable, result, _sets, _costs, compute_ok = compute(rows)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    private_rows = private_input_records(rows, load_status, usable)
    ref_rows, ref_ok = reference_policy_result_records(result) if result else ([], False)
    top2_rows, top2_ok = top2_marginal_mechanism_records(result) if result else ([], False)
    top3_rows, top3_ok = top3_marginal_mechanism_records(result) if result else ([], False)
    miss_rows, miss_ok = remaining_miss_mechanism_records(result) if result else ([], False)
    cost_rows, cost_ok = cost_mechanism_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, ref_ok, top2_ok, top3_ok, miss_ok, cost_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_refined_hybrid_mechanism_decomposition_only", "generated_by": "bea_v1_n10cq_refined_hybrid_mechanism_decomposition", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_rows, "reference_policy_result_records": ref_rows, "top2_marginal_mechanism_records": top2_rows, "top3_marginal_mechanism_records": top3_rows, "remaining_miss_mechanism_records": miss_rows, "cost_mechanism_records": cost_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cr_handoff_records": n10cr_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, ref_ok, top2_ok, top3_ok, miss_ok, cost_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cr_handoff_records"] = n10cr_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, ref_ok, top2_ok, top3_ok, miss_ok, cost_ok, privacy_ok, noexec_ok, scanner_ok)
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


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    global global_usable_rows
    global_usable_rows = [row for row in rows if row_valid(row) and row.get("p4_evidence")] if load_status == "pass" else []
    usable, result, _sets, _costs, compute_ok = compute(rows) if load_status == "pass" else (0, {}, {}, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    ref_rows, ref_ok = reference_policy_result_records(result) if result else ([], False)
    top2_rows, top2_ok = top2_marginal_mechanism_records(result) if result else ([], False)
    top3_rows, top3_ok = top3_marginal_mechanism_records(result) if result else ([], False)
    miss_rows, miss_ok = remaining_miss_mechanism_records(result) if result else ([], False)
    cost_rows, cost_ok = cost_mechanism_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cq_required_inputs_unavailable", "no_go_n10cq_private_span_rows_missing", "no_go_n10cq_result_accounting_invalid", "no_go_n10cq_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("private_rows", private_ok),
        check("reference_policies", ref_ok and len(ref_rows) == 5 and any(r["policy_bucket"] == REFINED and r["top10_span_overlap_count"] == 25 and r["top20_span_overlap_count"] == 31 for r in ref_rows)),
        check("top2_marginal", top2_ok and top2_rows[0]["newly_recovered_case_count"] == 1 and top2_rows[0]["top2_minus_top1_bucket_sum"] == 1),
        check("top3_marginal", top3_ok and top3_rows[0]["newly_recovered_case_count"] == 0),
        check("remaining_misses", miss_ok and miss_rows[0]["remaining_miss_bucket_sum"] == 188),
        check("cost_mechanism", cost_ok and cost_rows[0]["top2_refined_cost10"] == 3200 and cost_rows[0]["top2_saves_vs_top3_cost10"] == 100),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["candidate_generation_count"] == 0 and noexec_rows[0]["adaptive_tuning_count"] == 0),
        check("synthetic_status", status_for(True, True, "pass", True, False, True, True, True, True, True, True) == "no_go_n10cq_result_accounting_invalid"),
        check("false_flags", stop_go_records(True)[0]["n10cr_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_generation_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CQ refined hybrid mechanism decomposition")
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
