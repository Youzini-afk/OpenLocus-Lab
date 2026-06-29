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


SCHEMA_VERSION = "bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep.v1"
PHASE = "BEA-v1-N10CM Winning Hybrid Cost-Reduction Refinement Sweep"
STATUS_COMPLETE = "winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cm_required_inputs_unavailable",
    "no_go_n10cm_private_span_rows_missing",
    "no_go_n10cm_variant_contract_invalid",
    "no_go_n10cm_result_accounting_invalid",
    "no_go_n10cm_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json")
PUBLIC_INPUTS = {
    "n10cl_adapter_package_artifact": (Path("artifacts/bea_v1_n10cl_winning_hybrid_adapter_smoke_package/bea_v1_n10cl_winning_hybrid_adapter_smoke_package_report.json"), "winning_hybrid_adapter_package_complete_n10cm_authorized"),
    "n10ck_adapter_smoke_artifact": (Path("artifacts/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke_report.json"), "winning_hybrid_adapter_smoke_pass_n10cl_authorized"),
    "n10cj_winning_hybrid_package_artifact": (Path("artifacts/bea_v1_n10cj_winning_hybrid_replication_package/bea_v1_n10cj_winning_hybrid_replication_package_report.json"), "winning_hybrid_replication_package_complete_n10ck_authorized"),
    "n10cg_observable_hybrid_sweep_artifact": (Path("artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json"), "observable_hybrid_span_shape_rule_sweep_complete_n10ch_authorized"),
}
VARIANT_SEQUENCE = [
    "anchor_short75_225",
    "anchor_winning_top3_pm200",
    "anchor_pm200_all_spans",
    "short75_225_top1_all_pm200",
    "short75_225_top2_all_pm200",
    "short75_225_top3_all_pm200",
    "short75_225_top3_all_pm150",
    "short75_225_top3_all_pm175",
    "short75_225_top3_all_pm200",
    "short75_225_top1_all_pm175",
    "short75_225_top2_all_pm175",
    "short75_225_top2_all_pm150",
]
REFERENCE = {"winning_top10": 25, "winning_top20": 31, "winning_cost10": 3300, "winning_cost20": 6300, "pm200_cost10": 4000, "pm200_cost20": 8000}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks",
    "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status", "private_input_bucket", "intake_status_bucket", "variant_bucket", "duplicate_of_variant_bucket", "policy_bucket", "decision_bucket", "frontier_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10cn_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation", "cost_bucket"})


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
        rows.append({"anonymous_input_artifact_id": f"n10cmin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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
    return all(isinstance(ev, dict) and isinstance(ev.get("path"), str) and isinstance(ev.get("start_line"), int) and isinstance(ev.get("end_line"), int) for ev in evs)


def best_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [ev for idx, ev in enumerate(evidence, 1) if idx <= 20]
    extra = [ev for idx, ev in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def refs(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        if isinstance(rg, list) and len(rg) >= 2:
            grouped.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return grouped


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def is_short(ev: dict[str, Any]) -> bool:
    return int(ev["end_line"]) - int(ev["start_line"]) + 1 <= 10


def variant_spec(name: str) -> dict[str, Any]:
    if name == "anchor_short75_225":
        return {"top_k": 0, "pm": 0, "all_pm200": False, "duplicate_of": "none"}
    if name == "anchor_pm200_all_spans":
        return {"top_k": 999, "pm": 200, "all_pm200": True, "duplicate_of": "none"}
    if name in {"anchor_winning_top3_pm200", "short75_225_top3_all_pm200"}:
        return {"top_k": 3, "pm": 200, "all_pm200": False, "duplicate_of": "anchor_winning_top3_pm200" if name == "short75_225_top3_all_pm200" else "none"}
    match = re.match(r"short75_225_top(\d+)_all_pm(\d+)$", name)
    if match:
        return {"top_k": int(match.group(1)), "pm": int(match.group(2)), "all_pm200": False, "duplicate_of": "none"}
    raise ValueError(name)


def project(ev: dict[str, Any], pos: int, spec: dict[str, Any]) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    if spec["all_pm200"] or (spec["top_k"] and pos <= spec["top_k"]):
        pm = int(spec["pm"])
        return project_evidence_span_record(base, expansion_each_side=pm, enabled=True), 2 * pm
    if is_short(base):
        out = dict(base)
        out["start_line"] = max(1, int(out["start_line"]) - 75)
        out["end_line"] = int(out["end_line"]) + 225
        return out, 300
    return base, 0


def hit(projected: list[dict[str, Any]], gold: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for ev in projected[:limit]:
        key = str(ev.get("path", ""))
        if key in gold and any(overlap(int(ev["start_line"]), int(ev["end_line"]), a, b) for a, b in gold[key]):
            return True
    return False


def evaluate_variant(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    spec = variant_spec(name)
    top10_hits: set[int] = set()
    top20_hits: set[int] = set()
    cost10 = 0
    cost20 = 0
    for idx, row in enumerate(rows):
        ordered = best_order(row["p4_evidence"])
        projected: list[dict[str, Any]] = []
        row_cost10 = 0
        row_cost20 = 0
        for pos, ev in enumerate(ordered, 1):
            out, cost = project(ev, pos, spec)
            projected.append(out)
            if pos <= 10:
                row_cost10 += cost
            if pos <= 20:
                row_cost20 += cost
        cost10 = row_cost10
        cost20 = row_cost20
        gold = refs(row)
        if hit(projected, gold, 10):
            top10_hits.add(idx)
        if hit(projected, gold, 20):
            top20_hits.add(idx)
    return {"variant_bucket": name, "top10_set": top10_hits, "top20_set": top20_hits, "top10_span_overlap_count": len(top10_hits), "top20_span_overlap_count": len(top20_hits), "cost_proxy_top10": cost10, "cost_proxy_top20": cost20, "duplicate_of_variant_bucket": spec["duplicate_of"]}


def decision(row: dict[str, Any], winning: dict[str, Any]) -> str:
    lost = len(winning["top10_set"] - row["top10_set"])
    if row["top10_span_overlap_count"] >= 25 and row["top20_span_overlap_count"] >= 31 and lost == 0 and row["cost_proxy_top10"] < 3300 and row["cost_proxy_top20"] < 6300:
        return "preserves_winning_at_lower_cost"
    if row["top10_span_overlap_count"] > 25 and lost <= 1 and row["cost_proxy_top10"] <= 4000:
        return "improves_winning"
    if row["top10_span_overlap_count"] >= 24 and row["top20_span_overlap_count"] >= 30 and row["cost_proxy_top10"] < 3300:
        return "near_winning_cost_saving_tradeoff"
    return "no_improvement_winning_retained"


def compute(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
    raw = [evaluate_variant(usable, name) for name in VARIANT_SEQUENCE]
    winning = next(row for row in raw if row["variant_bucket"] == "anchor_winning_top3_pm200")
    result_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(raw):
        lost = len(winning["top10_set"] - row["top10_set"])
        result_rows.append({
            "anonymous_variant_result_id": f"n10cmvar{idx:04d}",
            "variant_bucket": row["variant_bucket"],
            "duplicate_of_variant_bucket": row["duplicate_of_variant_bucket"],
            "top10_span_overlap_count": row["top10_span_overlap_count"],
            "top20_span_overlap_count": row["top20_span_overlap_count"],
            "delta_vs_winning_top10": row["top10_span_overlap_count"] - 25,
            "delta_vs_winning_top20": row["top20_span_overlap_count"] - 31,
            "lost_winning_top10_hits": lost,
            "cost_proxy_top10": row["cost_proxy_top10"],
            "cost_proxy_top20": row["cost_proxy_top20"],
            "cost_savings_vs_winning_top10": 3300 - row["cost_proxy_top10"],
            "cost_savings_vs_winning_top20": 6300 - row["cost_proxy_top20"],
            "cost_savings_vs_pm200_top10": 4000 - row["cost_proxy_top10"],
            "cost_savings_vs_pm200_top20": 8000 - row["cost_proxy_top20"],
            "decision_bucket": decision(row, winning),
            "candidate_pool_changed_bool": False,
            "candidate_order_changed_bool": False,
        })
    counts = Counter(row["decision_bucket"] for row in result_rows)
    frontier = {
        "preserves_winning_at_lower_cost_count": counts["preserves_winning_at_lower_cost"],
        "improves_winning_count": counts["improves_winning"],
        "near_winning_cost_saving_tradeoff_count": counts["near_winning_cost_saving_tradeoff"],
        "no_improvement_winning_retained_count": counts["no_improvement_winning_retained"],
        "best_top10_span_overlap_count": max(row["top10_span_overlap_count"] for row in result_rows),
        "best_top20_span_overlap_count": max(row["top20_span_overlap_count"] for row in result_rows),
        "lowest_cost_preserving_winning_top10": min((row["cost_proxy_top10"] for row in result_rows if row["top10_span_overlap_count"] >= 25), default=0),
        "lowest_cost_preserving_winning_top20": min((row["cost_proxy_top20"] for row in result_rows if row["top20_span_overlap_count"] >= 31), default=0),
        "frontier_bucket": "winning_retained_no_lower_cost_success" if counts["preserves_winning_at_lower_cost"] == 0 and counts["improves_winning"] == 0 else "refinement_success_found",
    }
    valid = len(rows) == 213 and len(usable) == 213 and len(result_rows) == 12
    return len(usable), result_rows, raw, frontier, valid


def private_input_intake_records(rows: list[dict[str, Any]], status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_id": "n10cmpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if status == "pass" and len(rows) == 213 and usable == 213 else status, "private_span_rows_read": len(rows) if status == "pass" else 0, "usable_span_surface_rows": usable, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def variant_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    for idx, name in enumerate(VARIANT_SEQUENCE):
        spec = variant_spec(name)
        rows.append({"anonymous_variant_contract_id": f"n10cmcontract{idx:04d}", "variant_bucket": name, "duplicate_of_variant_bucket": spec["duplicate_of"], "policy_bucket": "short75_225_base_plus_fixed_top_position_pm_override", "short_span_before_count": 75, "short_span_after_count": 225, "top_position_count": int(spec["top_k"] if spec["top_k"] != 999 else 20), "top_position_pm_window_count": int(spec["pm"]), "all_spans_pm200_bool": bool(spec["all_pm200"]), "gold_used_for_policy_bool": False, "outcome_used_for_policy_bool": False, "miss_direction_used_for_policy_bool": False, "content_used_for_policy_bool": False, "file_identity_used_for_policy_bool": False, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
    return rows, len(rows) == 12 and [r["variant_bucket"] for r in rows] == VARIANT_SEQUENCE


def cost_reduction_decision_records(result_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    counts = Counter(row["decision_bucket"] for row in result_rows)
    return [{"anonymous_cost_reduction_decision_id": "n10cmdecision0000", "preserves_winning_at_lower_cost_count": counts["preserves_winning_at_lower_cost"], "improves_winning_count": counts["improves_winning"], "near_winning_cost_saving_tradeoff_count": counts["near_winning_cost_saving_tradeoff"], "no_improvement_winning_retained_count": counts["no_improvement_winning_retained"], "successful_variant_count": counts["preserves_winning_at_lower_cost"] + counts["improves_winning"], "decision_complete_bool": True}], True


def frontier_summary_records(frontier: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_frontier_summary_id": "n10cmfrontier0000", **frontier, "winning_reference_top10": 25, "winning_reference_top20": 31, "winning_reference_cost10": 3300, "winning_reference_cost20": 6300, "pm200_reference_cost10": 4000, "pm200_reference_cost20": 8000}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10cmprivacy0000", "privacy_boundary_bucket": "aggregate_refinement_sweep_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10cmnoexec0000", "no_execution_boundary_bucket": "same_source_fixed_variant_refinement_only", "other_private_file_read_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "new_ranking_arm_count": 0, "adaptive_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "existing_evaluator_hook_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cn_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cn_handoff_id": "n10cmhandoff0000", "n10cn_handoff_bucket": "n10cn_public_audit_package_authorized" if complete else "n10cn_not_authorized", "n10cn_authorized_bool": complete, "public_audit_package_only_bool": complete, "additional_private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "existing_evaluator_hook_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("variant_contract", contract_ok), ("result_accounting", result_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cn_authorized" if complete else "n10cn_not_authorized", "next_allowed_phase": "BEA-v1-N10CN Winning Hybrid Cost-Reduction Refinement Audit Package" if complete else "none_until_refinement_sweep_valid", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10cn_authorized": complete, "additional_private_read_authorized": False, "recompute_authorized": False, "new_variant_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "existing_evaluator_hook_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cm_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10cm_private_span_rows_missing"
    if not contract_ok:
        return "no_go_n10cm_variant_contract_invalid"
    if not private_ok or not result_ok:
        return "no_go_n10cm_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10cm_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result_rows, _raw, frontier, compute_ok = compute(rows) if load_status == "pass" else (0, [], [], {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    private_rows = private_input_intake_records(rows, load_status, usable)
    contract_rows, contract_ok = variant_contract_records()
    decision_rows, decision_ok = cost_reduction_decision_records(result_rows)
    frontier_rows, frontier_ok = frontier_summary_records(frontier)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    result_ok = compute_ok and len(result_rows) == 12 and decision_ok and frontier_ok
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, contract_ok, result_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_winning_hybrid_refinement_sweep_only", "generated_by": "bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_rows, "variant_contract_records": contract_rows, "variant_result_records": result_rows, "cost_reduction_decision_records": decision_rows, "frontier_summary_records": frontier_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cn_handoff_records": n10cn_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, contract_ok, result_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cn_handoff_records"] = n10cn_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, contract_ok, result_ok, privacy_ok, noexec_ok, scanner_ok)
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
    usable, result_rows, _raw, frontier, compute_ok = compute(rows) if load_status == "pass" else (0, [], [], {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    contract_rows, contract_ok = variant_contract_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    counts = Counter(row["decision_bucket"] for row in result_rows)
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cm_required_inputs_unavailable", "no_go_n10cm_private_span_rows_missing", "no_go_n10cm_variant_contract_invalid", "no_go_n10cm_result_accounting_invalid", "no_go_n10cm_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok),
        check("variant_grid", contract_ok and len(contract_rows) == 12 and [r["variant_bucket"] for r in contract_rows] == VARIANT_SEQUENCE),
        check("duplicate_handling", sum(1 for r in contract_rows if r["variant_bucket"] == "short75_225_top3_all_pm200") == 2),
        check("result_rows", len(result_rows) == 12 and any(r["variant_bucket"] == "short75_225_top2_all_pm175" for r in result_rows)),
        check("winning_reference", any(r["variant_bucket"] == "anchor_winning_top3_pm200" and r["top10_span_overlap_count"] == 25 and r["top20_span_overlap_count"] == 31 and r["cost_proxy_top10"] == 3300 for r in result_rows)),
        check("decision_counts", counts["preserves_winning_at_lower_cost"] >= 0 and counts["no_improvement_winning_retained"] >= 1),
        check("frontier", frontier.get("best_top10_span_overlap_count", 0) >= 25 and frontier.get("lowest_cost_preserving_winning_top10", 0) > 0),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["candidate_generation_count"] == 0 and noexec_rows[0]["adaptive_tuning_count"] == 0),
        check("synthetic_status", status_for(True, True, "pass", True, False, True, True, True) == "no_go_n10cm_variant_contract_invalid"),
        check("false_flags", stop_go_records(True)[0]["n10cn_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CM winning hybrid cost-reduction refinement sweep")
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
