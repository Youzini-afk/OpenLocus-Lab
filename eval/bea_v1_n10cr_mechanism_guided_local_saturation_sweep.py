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


SCHEMA_VERSION = "bea_v1_n10cr_mechanism_guided_local_saturation_sweep.v1"
PHASE = "BEA-v1-N10CR Mechanism-Guided Local Saturation Sweep"
STATUS_COMPLETE = "mechanism_guided_local_saturation_sweep_complete_n10cs_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cr_required_inputs_unavailable",
    "no_go_n10cr_private_span_rows_missing",
    "no_go_n10cr_variant_contract_invalid",
    "no_go_n10cr_result_accounting_invalid",
    "no_go_n10cr_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json")
PUBLIC_INPUTS = {
    "n10cq_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10cq_refined_hybrid_mechanism_decomposition/bea_v1_n10cq_refined_hybrid_mechanism_decomposition_report.json"), "refined_hybrid_mechanism_decomposition_complete_n10cr_authorized"),
    "n10cp_refined_adapter_package_artifact": (Path("artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json"), "refined_hybrid_adapter_package_complete_n10cq_authorized"),
    "n10cn_refinement_package_artifact": (Path("artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json"), "winning_hybrid_cost_refinement_package_complete_n10co_authorized"),
    "n10cg_hybrid_sweep_artifact": (Path("artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json"), "observable_hybrid_span_shape_rule_sweep_complete_n10ch_authorized"),
}
VARIANTS = (
    "anchor_refined_top2_pm200_short75_225",
    "anchor_pm200_all_spans",
    "top2_pm200_short90_270",
    "top2_pm200_short100_300",
    "top2_pm200_short75_225_medium40_120",
    "top2_pm200_short75_225_medium75_225",
    "top2_pm200_short75_225_medium75_225_long75_225",
    "top2_pm300_short75_225",
)
REFINED = "anchor_refined_top2_pm200_short75_225"
PM200 = "anchor_pm200_all_spans"
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks",
    "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status", "private_input_bucket", "intake_status_bucket", "variant_bucket", "decision_bucket", "saturation_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10cs_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation"})


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
                if str(key) in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + str(key))
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
        rows.append({"anonymous_input_artifact_id": f"n10crin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def length_bucket(ev: dict[str, Any]) -> str:
    length = int(ev["end_line"]) - int(ev["start_line"]) + 1
    if length <= 10:
        return "short"
    if length <= 30:
        return "medium"
    return "long"


def expand_asym(ev: dict[str, Any], before: int, after: int) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    projected = dict(base)
    projected["start_line"] = max(1, int(projected["start_line"]) - before)
    projected["end_line"] = int(projected["end_line"]) + after
    return projected, before + after


def project_variant(ev: dict[str, Any], position: int, variant: str) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    bucket = length_bucket(base)
    if variant == PM200:
        return project_evidence_span_record(base, expansion_each_side=200, enabled=True), 400
    if variant == "top2_pm300_short75_225" and position <= 2:
        return project_evidence_span_record(base, expansion_each_side=300, enabled=True), 600
    if position <= 2:
        return project_evidence_span_record(base, expansion_each_side=200, enabled=True), 400
    if variant == "top2_pm200_short90_270" and bucket == "short":
        return expand_asym(base, 90, 270)
    if variant == "top2_pm200_short100_300" and bucket == "short":
        return expand_asym(base, 100, 300)
    if bucket == "short":
        return expand_asym(base, 75, 225)
    if variant == "top2_pm200_short75_225_medium40_120" and bucket == "medium":
        return expand_asym(base, 40, 120)
    if variant in ("top2_pm200_short75_225_medium75_225", "top2_pm200_short75_225_medium75_225_long75_225") and bucket == "medium":
        return expand_asym(base, 75, 225)
    if variant == "top2_pm200_short75_225_medium75_225_long75_225" and bucket == "long":
        return expand_asym(base, 75, 225)
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


def compute(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
    top10: dict[str, set[int]] = {v: set() for v in VARIANTS}
    top20: dict[str, set[int]] = {v: set() for v in VARIANTS}
    costs: dict[str, dict[str, int]] = {v: {"cost10": 0, "cost20": 0} for v in VARIANTS}
    residuals: dict[str, Counter[str]] = {v: Counter() for v in VARIANTS}
    pool_order_ok = True
    for idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        pool_order_ok = pool_order_ok and len(ordered) == len(row["p4_evidence"])
        refs = references(row)
        for variant in VARIANTS:
            projected: list[dict[str, Any]] = []
            c10 = 0
            c20 = 0
            for pos, ev in enumerate(ordered, 1):
                item, cost = project_variant(ev, pos, variant)
                projected.append(item)
                if pos <= 10:
                    c10 += cost
                if pos <= 20:
                    c20 += cost
            costs[variant] = {"cost10": c10, "cost20": c20}
            if hit(projected, refs, 10):
                top10[variant].add(idx)
            else:
                if hit(projected, refs, len(projected)):
                    residuals[variant]["span_overlap_beyond_top10"] += 1
                elif file_hit(ordered, refs, 10):
                    residuals[variant]["same_file_no_span_overlap"] += 1
                else:
                    residuals[variant]["file_not_in_top10"] += 1
            if hit(projected, refs, 20):
                top20[variant].add(idx)
    ok = len(rows) == 213 and len(usable) == 213 and pool_order_ok and len(top10[REFINED]) == 25 and len(top20[REFINED]) == 31 and costs[REFINED] == {"cost10": 3200, "cost20": 6200} and len(top10[PM200]) == 25 and len(top20[PM200]) == 30 and costs[PM200] == {"cost10": 4000, "cost20": 8000}
    return len(usable), {"top10": top10, "top20": top20, "costs": costs, "residuals": residuals}, ok


def private_input_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_id": "n10crpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def variant_contract_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_variant_contract_id": f"n10crcontract{idx:04d}", "variant_bucket": variant, "predeclared_variant_bool": True, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "policy_gold_signal_used_bool": False, "policy_outcome_signal_used_bool": False} for idx, variant in enumerate(VARIANTS)], len(VARIANTS) == 8


def variant_result_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    refined = result["top10"][REFINED]
    rows = []
    for idx, variant in enumerate(VARIANTS):
        t10 = len(result["top10"][variant])
        t20 = len(result["top20"][variant])
        lost = len(refined - result["top10"][variant])
        if t10 > 25 and lost <= 1:
            decision = "local_window_improves_refined"
        elif t10 == 25 and t20 > 31 and lost == 0:
            decision = "local_window_improves_top20_only"
        else:
            decision = "local_window_saturated"
        res = result["residuals"][variant]
        rows.append({"anonymous_variant_result_id": f"n10crresult{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": t10, "top20_span_overlap_count": t20, "delta_top10_vs_refined": t10 - 25, "delta_top20_vs_refined": t20 - 31, "lost_refined_top10_hits": lost, "cost_proxy_top10": result["costs"][variant]["cost10"], "cost_proxy_top20": result["costs"][variant]["cost20"], "same_file_no_span_overlap_remaining_count": res.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_remaining_count": res.get("span_overlap_beyond_top10", 0), "file_not_in_top10_remaining_count": res.get("file_not_in_top10", 0), "decision_bucket": decision, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
    return rows, len(rows) == 8 and any(r["variant_bucket"] == REFINED and r["top10_span_overlap_count"] == 25 and r["top20_span_overlap_count"] == 31 for r in rows)


def local_miss_residual_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    for idx, variant in enumerate(VARIANTS):
        res = result["residuals"][variant]
        total = res.get("same_file_no_span_overlap", 0) + res.get("span_overlap_beyond_top10", 0) + res.get("file_not_in_top10", 0)
        rows.append({"anonymous_local_miss_residual_id": f"n10crmiss{idx:04d}", "variant_bucket": variant, "same_file_no_span_overlap_remaining_count": res.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_remaining_count": res.get("span_overlap_beyond_top10", 0), "file_not_in_top10_remaining_count": res.get("file_not_in_top10", 0), "remaining_top10_miss_count": total})
    return rows, all(r["remaining_top10_miss_count"] == 213 - len(result["top10"][r["variant_bucket"]]) for r in rows)


def saturation_decision_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    max_top10 = max(len(result["top10"][v]) for v in VARIANTS)
    max_top20 = max(len(result["top20"][v]) for v in VARIANTS)
    overall = max_top10 <= 25 and max_top20 <= 31
    best_top10 = [v for v in VARIANTS if len(result["top10"][v]) == max_top10]
    best_top20 = [v for v in VARIANTS if len(result["top20"][v]) == max_top20]
    rows = [{"anonymous_saturation_decision_id": "n10crsaturation0000", "saturation_bucket": "local_window_saturated" if overall else "local_window_not_saturated", "max_top10_span_overlap_count": max_top10, "max_top20_span_overlap_count": max_top20, "overall_saturation_bool": overall, "best_top10_variant_count": len(best_top10), "best_top20_variant_count": len(best_top20), "rank_file_reach_pivot_allowed_next_bool": overall}]
    return rows, True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10crprivacy0000", "privacy_boundary_bucket": "aggregate_saturation_sweep_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10crnoexec0000", "no_execution_boundary_bucket": "local_saturation_sweep_only", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "rank_file_promotion_count": 0, "adaptive_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cs_handoff_records(complete: bool, saturated: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cs_handoff_id": "n10crhandoff0000", "n10cs_handoff_bucket": "n10cs_public_package_authorized" if complete else "n10cs_not_authorized", "n10cs_authorized_bool": complete, "public_package_only_bool": complete, "n10ct_rank_file_reach_preflight_may_be_authorized_by_n10cs_bool": bool(complete and saturated), "runtime_default_authorized_bool": False, "rank_file_promotion_authorized_in_n10cr_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, residual_ok: bool, saturation_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read_213", private_ok), ("variant_contract", contract_ok), ("variant_results", result_ok), ("local_miss_residuals", residual_ok), ("saturation_decision", saturation_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cs_authorized" if complete else "n10cs_not_authorized", "next_allowed_phase": "BEA-v1-N10CS Local Saturation Sweep Public Package" if complete else "none_until_saturation_sweep_valid", "next_allowed_scope_bucket": "public_package_only" if complete else "no_next_phase", "n10cs_authorized": complete, "runtime_or_default_authorized": False, "existing_evaluator_hook_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "rank_file_promotion_authorized_in_n10cr": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, residual_ok: bool, saturation_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cr_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10cr_private_span_rows_missing"
    if not contract_ok:
        return "no_go_n10cr_variant_contract_invalid"
    if not private_ok or not result_ok or not residual_ok or not saturation_ok:
        return "no_go_n10cr_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10cr_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, compute_ok = compute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    private_rows = private_input_records(rows, load_status, usable)
    contract_rows, contract_ok = variant_contract_records()
    variant_rows, result_ok = variant_result_records(result) if result else ([], False)
    residual_rows, residual_ok = local_miss_residual_records(result) if result else ([], False)
    saturation_rows, saturation_ok = saturation_decision_records(result) if result else ([], False)
    saturated = bool(saturation_rows and saturation_rows[0]["overall_saturation_bool"])
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, contract_ok, result_ok, residual_ok, saturation_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_local_window_saturation_sweep_only", "generated_by": "bea_v1_n10cr_mechanism_guided_local_saturation_sweep", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_rows, "variant_contract_records": contract_rows, "variant_result_records": variant_rows, "local_miss_residual_records": residual_rows, "saturation_decision_records": saturation_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cs_handoff_records": n10cs_handoff_records(complete, saturated), "gate_records": gate_records(input_ok, private_ok, contract_ok, result_ok, residual_ok, saturation_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cs_handoff_records"] = n10cs_handoff_records(complete, saturated)
    report["gate_records"] = gate_records(input_ok, private_ok, contract_ok, result_ok, residual_ok, saturation_ok, privacy_ok, noexec_ok, scanner_ok)
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
    usable, result, compute_ok = compute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    contract_rows, contract_ok = variant_contract_records()
    variant_rows, result_ok = variant_result_records(result) if result else ([], False)
    residual_rows, residual_ok = local_miss_residual_records(result) if result else ([], False)
    saturation_rows, saturation_ok = saturation_decision_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cr_required_inputs_unavailable", "no_go_n10cr_private_span_rows_missing", "no_go_n10cr_variant_contract_invalid", "no_go_n10cr_result_accounting_invalid", "no_go_n10cr_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok),
        check("contract", contract_ok and len(contract_rows) == 8 and tuple(r["variant_bucket"] for r in contract_rows) == VARIANTS),
        check("variant_results", result_ok and len(variant_rows) == 8 and any(r["variant_bucket"] == REFINED and r["top10_span_overlap_count"] == 25 for r in variant_rows)),
        check("pm200_anchor", any(r["variant_bucket"] == PM200 and r["top10_span_overlap_count"] == 25 and r["top20_span_overlap_count"] == 30 for r in variant_rows)),
        check("residuals", residual_ok and len(residual_rows) == 8),
        check("saturation", saturation_ok and saturation_rows[0]["max_top10_span_overlap_count"] >= 25 and saturation_rows[0]["max_top20_span_overlap_count"] >= 31),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["candidate_generation_count"] == 0 and noexec_rows[0]["rank_file_promotion_count"] == 0),
        check("synthetic_status", status_for(True, True, "pass", True, False, True, True, True, True, True) == "no_go_n10cr_variant_contract_invalid"),
        check("false_flags", stop_go_records(True)[0]["n10cs_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["rank_file_promotion_authorized_in_n10cr"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CR mechanism-guided local saturation sweep")
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
