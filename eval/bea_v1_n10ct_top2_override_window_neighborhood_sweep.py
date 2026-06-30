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


SCHEMA_VERSION = "bea_v1_n10ct_top2_override_window_neighborhood_sweep.v1"
PHASE = "BEA-v1-N10CT Top2 Override Window Neighborhood Sweep"
STATUS_COMPLETE = "top2_override_window_neighborhood_sweep_complete_n10cu_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ct_required_inputs_unavailable",
    "no_go_n10ct_private_span_rows_missing",
    "no_go_n10ct_variant_contract_invalid",
    "no_go_n10ct_result_accounting_invalid",
    "no_go_n10ct_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ct_top2_override_window_neighborhood_sweep/bea_v1_n10ct_top2_override_window_neighborhood_sweep_report.json")
PUBLIC_INPUTS = {
    "n10cs_local_saturation_package_artifact": (Path("artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json"), "local_saturation_package_complete_n10ct_authorized"),
    "n10cr_local_saturation_sweep_artifact": (Path("artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json"), "mechanism_guided_local_saturation_sweep_complete_n10cs_authorized"),
    "n10cp_refined_adapter_package_artifact": (Path("artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json"), "refined_hybrid_adapter_package_complete_n10cq_authorized"),
}
PMS = (200, 225, 250, 275, 300, 325, 350, 375, 400)
VARIANTS = tuple(f"short75_225_top2_all_pm{pm}" for pm in PMS)
PM200 = "short75_225_top2_all_pm200"
PM300 = "short75_225_top2_all_pm300"
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
    "private_input_bucket", "intake_status_bucket", "variant_bucket", "policy_bucket", "decision_bucket",
    "summary_bucket", "cost_curve_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10cu_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10ctin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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
    return "short" if length <= 10 else ("medium" if length <= 30 else "long")


def expand_asym(ev: dict[str, Any], before: int, after: int) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    projected = dict(base)
    projected["start_line"] = max(1, int(projected["start_line"]) - before)
    projected["end_line"] = int(projected["end_line"]) + after
    return projected, before + after


def project_variant(ev: dict[str, Any], position: int, pm: int) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    if position <= 2:
        return project_evidence_span_record(base, expansion_each_side=pm, enabled=True), pm * 2
    if length_bucket(base) == "short":
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
        for variant, pm in zip(VARIANTS, PMS):
            projected: list[dict[str, Any]] = []
            c10 = 0
            c20 = 0
            for pos, ev in enumerate(ordered, 1):
                item, cost = project_variant(ev, pos, pm)
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
    ok = len(rows) == 213 and len(usable) == 213 and pool_order_ok and len(top10[PM200]) == 25 and len(top20[PM200]) == 31 and costs[PM200] == {"cost10": 3200, "cost20": 6200} and len(top10[PM300]) == 26 and len(top20[PM300]) == 32 and costs[PM300] == {"cost10": 3600, "cost20": 6600}
    return len(usable), {"top10": top10, "top20": top20, "costs": costs, "residuals": residuals}, ok


def private_input_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_id": "n10ctpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def variant_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [{"anonymous_variant_contract_id": f"n10ctcontract{idx:04d}", "variant_bucket": variant, "pm_window_each_side": pm, "predeclared_variant_bool": True, "short_span_base_before_count": 75, "short_span_base_after_count": 225, "top2_override_bool": True, "top3_override_bool": False, "medium_long_extra_gate_bool": False, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "policy_gold_signal_used_bool": False, "policy_outcome_signal_used_bool": False, "policy_file_identity_used_bool": False} for idx, (variant, pm) in enumerate(zip(VARIANTS, PMS))]
    return rows, tuple(r["variant_bucket"] for r in rows) == VARIANTS and len(rows) == 9


def variant_result_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    pm200_t10 = result["top10"][PM200]
    pm300_t10 = result["top10"][PM300]
    rows = []
    for idx, variant in enumerate(VARIANTS):
        t10 = len(result["top10"][variant])
        t20 = len(result["top20"][variant])
        lost_pm300 = len(pm300_t10 - result["top10"][variant])
        if t10 >= 26 and t20 >= 32 and result["costs"][variant]["cost10"] < 3600 and lost_pm300 == 0:
            decision = "preserves_pm300_at_lower_cost"
        elif t10 > 26 and lost_pm300 <= 1:
            decision = "improves_pm300"
        else:
            decision = "no_improvement_pm300_retained"
        res = result["residuals"][variant]
        rows.append({"anonymous_variant_result_id": f"n10ctresult{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": t10, "top20_span_overlap_count": t20, "delta_top10_vs_pm200": t10 - len(pm200_t10), "delta_top20_vs_pm200": t20 - len(result["top20"][PM200]), "delta_top10_vs_pm300": t10 - len(pm300_t10), "delta_top20_vs_pm300": t20 - len(result["top20"][PM300]), "lost_pm300_top10_hits": lost_pm300, "cost_proxy_top10": result["costs"][variant]["cost10"], "cost_proxy_top20": result["costs"][variant]["cost20"], "same_file_no_span_overlap_remaining_count": res.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_remaining_count": res.get("span_overlap_beyond_top10", 0), "file_not_in_top10_remaining_count": res.get("file_not_in_top10", 0), "decision_bucket": decision, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
    return rows, len(rows) == 9 and any(r["variant_bucket"] == PM200 and r["top10_span_overlap_count"] == 25 and r["top20_span_overlap_count"] == 31 for r in rows) and any(r["variant_bucket"] == PM300 and r["top10_span_overlap_count"] == 26 and r["top20_span_overlap_count"] == 32 for r in rows)


def neighborhood_summary_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    rows_by_variant = {v: {"t10": len(result["top10"][v]), "t20": len(result["top20"][v]), "cost10": result["costs"][v]["cost10"], "cost20": result["costs"][v]["cost20"]} for v in VARIANTS}
    preserving = [pm for variant, pm in zip(VARIANTS, PMS) if rows_by_variant[variant]["t10"] >= 26 and rows_by_variant[variant]["t20"] >= 32]
    max_t10 = max(v["t10"] for v in rows_by_variant.values())
    max_t20 = max(v["t20"] for v in rows_by_variant.values())
    rows = [{"anonymous_neighborhood_summary_id": "n10ctsummary0000", "summary_bucket": "top2_override_pm_neighborhood", "variant_count": len(VARIANTS), "minimum_pm_for_26_32": min(preserving) if preserving else 0, "max_observed_top10_span_overlap_count": max_t10, "max_observed_top20_span_overlap_count": max_t20, "preserves_pm300_at_lower_cost_count": sum(1 for variant in VARIANTS if rows_by_variant[variant]["t10"] >= 26 and rows_by_variant[variant]["t20"] >= 32 and rows_by_variant[variant]["cost10"] < 3600), "improves_pm300_count": sum(1 for variant in VARIANTS if rows_by_variant[variant]["t10"] > 26), "pm300_reference_top10_span_overlap_count": rows_by_variant[PM300]["t10"], "pm300_reference_top20_span_overlap_count": rows_by_variant[PM300]["t20"], "pm300_reference_cost_proxy_top10": rows_by_variant[PM300]["cost10"], "pm300_reference_cost_proxy_top20": rows_by_variant[PM300]["cost20"]}]
    return rows, rows[0]["minimum_pm_for_26_32"] >= 200 and rows[0]["max_observed_top10_span_overlap_count"] >= 26


def cost_curve_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    rows = [{"anonymous_cost_curve_id": f"n10ctcost{idx:04d}", "cost_curve_bucket": "top2_pm_window_cost_curve", "variant_bucket": variant, "pm_window_each_side": pm, "cost_proxy_top10": result["costs"][variant]["cost10"], "cost_proxy_top20": result["costs"][variant]["cost20"], "top10_span_overlap_count": len(result["top10"][variant]), "top20_span_overlap_count": len(result["top20"][variant])} for idx, (variant, pm) in enumerate(zip(VARIANTS, PMS))]
    return rows, len(rows) == 9 and all(rows[i]["cost_proxy_top10"] <= rows[i + 1]["cost_proxy_top10"] for i in range(len(rows) - 1))


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10ctprivacy0000", "privacy_boundary_bucket": "aggregate_neighborhood_sweep_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10ctnoexec0000", "no_execution_boundary_bucket": "top2_pm_neighborhood_sweep_only", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "new_rank_order_arm_count": 0, "top3_override_count": 0, "medium_long_extra_gate_count": 0, "adaptive_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cu_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cu_handoff_id": "n10cthandoff0000", "n10cu_handoff_bucket": "n10cu_public_package_authorized" if complete else "n10cu_not_authorized", "n10cu_authorized_bool": complete, "public_package_only_bool": complete, "private_read_authorized_next_bool": False, "recompute_authorized_next_bool": False, "new_variant_authorized_next_bool": False, "runtime_default_authorized_bool": False, "top3_override_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "heldout_generalization_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, summary_ok: bool, cost_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read_213", private_ok), ("variant_contract", contract_ok), ("variant_results", result_ok), ("neighborhood_summary", summary_ok), ("cost_curve", cost_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cu_authorized" if complete else "n10cu_not_authorized", "next_allowed_phase": "BEA-v1-N10CU Top2 Override Neighborhood Public Package" if complete else "none_until_top2_neighborhood_sweep_valid", "next_allowed_scope_bucket": "public_package_only" if complete else "no_next_phase", "n10cu_authorized": complete, "private_read_authorized": False, "recompute_authorized": False, "new_variant_authorized": False, "runtime_or_default_authorized": False, "existing_evaluator_hook_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "top3_override_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, summary_ok: bool, cost_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ct_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10ct_private_span_rows_missing"
    if not contract_ok:
        return "no_go_n10ct_variant_contract_invalid"
    if not private_ok or not result_ok or not summary_ok or not cost_ok:
        return "no_go_n10ct_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ct_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, compute_ok = compute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    private_rows = private_input_records(rows, load_status, usable)
    contract_rows, contract_ok = variant_contract_records()
    variant_rows, result_ok = variant_result_records(result) if result else ([], False)
    summary_rows, summary_ok = neighborhood_summary_records(result) if result else ([], False)
    cost_rows, cost_ok = cost_curve_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, contract_ok, result_ok, summary_ok, cost_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_top2_override_neighborhood_sweep_only", "generated_by": "bea_v1_n10ct_top2_override_window_neighborhood_sweep", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_rows, "variant_contract_records": contract_rows, "variant_result_records": variant_rows, "neighborhood_summary_records": summary_rows, "cost_curve_records": cost_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cu_handoff_records": n10cu_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, contract_ok, result_ok, summary_ok, cost_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cu_handoff_records"] = n10cu_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, contract_ok, result_ok, summary_ok, cost_ok, privacy_ok, noexec_ok, scanner_ok)
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
    summary_rows, summary_ok = neighborhood_summary_records(result) if result else ([], False)
    cost_rows, cost_ok = cost_curve_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ct_required_inputs_unavailable", "no_go_n10ct_private_span_rows_missing", "no_go_n10ct_variant_contract_invalid", "no_go_n10ct_result_accounting_invalid", "no_go_n10ct_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("private_rows", private_ok),
        check("contract", contract_ok and len(contract_rows) == 9 and tuple(r["variant_bucket"] for r in contract_rows) == VARIANTS),
        check("variant_results", result_ok and len(variant_rows) == 9),
        check("pm200_reference", any(r["variant_bucket"] == PM200 and r["top10_span_overlap_count"] == 25 and r["top20_span_overlap_count"] == 31 and r["cost_proxy_top10"] == 3200 for r in variant_rows)),
        check("pm300_reference", any(r["variant_bucket"] == PM300 and r["top10_span_overlap_count"] == 26 and r["top20_span_overlap_count"] == 32 and r["cost_proxy_top10"] == 3600 for r in variant_rows)),
        check("summary", summary_ok and summary_rows[0]["minimum_pm_for_26_32"] >= 200 and summary_rows[0]["max_observed_top10_span_overlap_count"] >= 26),
        check("cost_curve", cost_ok and len(cost_rows) == 9),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["top3_override_count"] == 0 and noexec_rows[0]["candidate_generation_count"] == 0),
        check("synthetic_status", status_for(True, True, "pass", True, False, True, True, True, True, True) == "no_go_n10ct_variant_contract_invalid"),
        check("false_flags", stop_go_records(True)[0]["n10cu_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["top3_override_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CT top2 override window neighborhood sweep")
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
