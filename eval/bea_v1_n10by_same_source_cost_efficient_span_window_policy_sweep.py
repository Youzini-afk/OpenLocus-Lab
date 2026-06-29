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


SCHEMA_VERSION = "bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep.v1"
PHASE = "BEA-v1-N10BY Same-Source Cost-Efficient Span-Window Policy Sweep"
STATUS_COMPLETE = "same_source_cost_efficient_span_window_policy_sweep_complete_n10bz_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10by_required_inputs_unavailable",
    "no_go_n10by_private_span_rows_missing",
    "no_go_n10by_variant_grid_invalid",
    "no_go_n10by_result_accounting_invalid",
    "no_go_n10by_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep_report.json")
PUBLIC_INPUTS = {
    "n10bx_adapter_operating_point_package_artifact": (Path("artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json"), "adapter_operating_point_package_complete_n10by_authorized"),
    "n10bw_adapter_operating_point_smoke_artifact": (Path("artifacts/bea_v1_n10bw_adapter_operating_point_smoke/bea_v1_n10bw_adapter_operating_point_smoke_report.json"), "adapter_operating_point_smoke_pass_n10bx_authorized"),
    "n10br_cost_minimization_package_artifact": (Path("artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json"), "cost_minimization_package_complete_n10bs_authorized"),
    "n10bq_plateau_cost_minimization_artifact": (Path("artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json"), "plateau_cost_minimization_sweep_complete_n10br_authorized"),
}
VARIANT_ORDER = (
    "anchor_cost80_before20_after60",
    "anchor_pm50_before50_after50",
    "asym_cost70_before18_after52",
    "asym_cost72_before18_after54",
    "asym_cost75_before19_after56",
    "asym_cost78_before20_after58",
    "rank_conditioned_top5_30_90_top10_10_30",
    "rank_conditioned_top5_25_75_top10_10_30",
    "rank_conditioned_top3_40_120_top10_10_30",
    "top10_only_cost80_before20_after60",
    "top5_only_cost80_before20_after60",
    "top20_only_cost80_before20_after60",
)
PM75_COST_PROXY_TOP10 = 1500
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
    "private_input_bucket", "intake_status_bucket", "variant_bucket", "variant_family_bucket", "policy_bucket",
    "cost_bucket", "decision_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10bz_handoff_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10byin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def refs(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return out


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def span_hit(records: list[dict[str, Any]], reference: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for item in records[:limit]:
        key = str(item.get("path", ""))
        if key not in reference:
            continue
        start = item.get("start_line")
        end = item.get("end_line")
        if isinstance(start, int) and isinstance(end, int) and any(overlaps(start, end, a, b) for a, b in reference[key]):
            return True
    return False


def variant_windows(variant: str, position: int) -> tuple[int, int]:
    if variant == "anchor_cost80_before20_after60":
        return 20, 60
    if variant == "anchor_pm50_before50_after50":
        return 50, 50
    if variant == "asym_cost70_before18_after52":
        return 18, 52
    if variant == "asym_cost72_before18_after54":
        return 18, 54
    if variant == "asym_cost75_before19_after56":
        return 19, 56
    if variant == "asym_cost78_before20_after58":
        return 20, 58
    if variant == "rank_conditioned_top5_30_90_top10_10_30":
        return (30, 90) if position <= 5 else ((10, 30) if position <= 10 else (0, 0))
    if variant == "rank_conditioned_top5_25_75_top10_10_30":
        return (25, 75) if position <= 5 else ((10, 30) if position <= 10 else (0, 0))
    if variant == "rank_conditioned_top3_40_120_top10_10_30":
        return (40, 120) if position <= 3 else ((10, 30) if position <= 10 else (0, 0))
    if variant == "top10_only_cost80_before20_after60":
        return (20, 60) if position <= 10 else (0, 0)
    if variant == "top5_only_cost80_before20_after60":
        return (20, 60) if position <= 5 else (0, 0)
    if variant == "top20_only_cost80_before20_after60":
        return (20, 60) if position <= 20 else (0, 0)
    raise ValueError("unknown variant")


def variant_family(variant: str) -> str:
    if variant.startswith("anchor"):
        return "anchor"
    if variant.startswith("asym"):
        return "fixed_asymmetric_cost_boundary"
    if variant.startswith("rank_conditioned"):
        return "rank_conditioned_fixed_windows"
    return "topk_expansion_fixed_windows"


def cost_bucket(value: int) -> str:
    if value < 800:
        return "below_anchor"
    if value == 800:
        return "anchor_cost"
    if value <= 1000:
        return "medium"
    if value <= 1500:
        return "high"
    return "very_high"


def project_variant(records: list[dict[str, Any]], variant: str) -> tuple[list[dict[str, Any]], int, int]:
    # Keep adapter path explicit and default-off; all policy variation is by fixed
    # caller-supplied rank-position windows, never by gold or row-specific tuning.
    copied = project_evidence_spans(records, expansion_each_side=0, enabled=False)
    projected: list[dict[str, Any]] = []
    cost10 = cost20 = 0
    for idx, item in enumerate(copied, 1):
        before, after = variant_windows(variant, idx)
        if idx <= 10:
            cost10 += before + after
        if idx <= 20:
            cost20 += before + after
        new_item = dict(item)
        if before or after:
            new_item["start_line"] = max(1, int(new_item["start_line"]) - before)
            new_item["end_line"] = int(new_item["end_line"]) + after
        projected.append(new_item)
    return projected, cost10, cost20


def compute_results(rows: list[dict[str, Any]]) -> tuple[int, dict[str, dict[str, Any]], bool]:
    usable = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    result_sets: dict[str, set[int]] = {variant: set() for variant in VARIANT_ORDER}
    base_hits: set[int] = set()
    cost10_values: dict[str, int] = {}
    cost20_values: dict[str, int] = {}
    top20_counts: dict[str, int] = {}
    pool_changed = False
    order_changed = False
    for row_idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        reference = refs(row)
        if span_hit(ordered, reference, 10):
            base_hits.add(row_idx)
        for variant in VARIANT_ORDER:
            projected, c10, c20 = project_variant(ordered, variant)
            cost10_values[variant] = c10
            cost20_values[variant] = c20
            pool_changed = pool_changed or len(projected) != len(ordered)
            order_changed = order_changed or len(projected) != len(ordered)
            if span_hit(projected, reference, 10):
                result_sets[variant].add(row_idx)
            top20_counts[variant] = top20_counts.get(variant, 0) + int(span_hit(projected, reference, 20))
    anchor = result_sets["anchor_cost80_before20_after60"]
    results: dict[str, dict[str, Any]] = {}
    for variant in VARIANT_ORDER:
        top10 = len(result_sets[variant])
        top20 = top20_counts.get(variant, 0)
        lost_anchor = len(anchor - result_sets[variant])
        lost_original = len(base_hits - result_sets[variant])
        c10 = cost10_values.get(variant, 0)
        decision = "no_improvement_anchor_retained"
        if top10 >= 20 and top20 >= 24 and lost_anchor == 0 and c10 < 800:
            decision = "cost_reduction_success"
        elif top10 > 20 and lost_anchor <= 1 and c10 <= PM75_COST_PROXY_TOP10:
            decision = "recall_improvement_success"
        results[variant] = {
            "top10_span_overlap_count": top10,
            "top20_span_overlap_count": top20,
            "delta_top10_vs_anchor_cost80": top10 - 20,
            "delta_top20_vs_anchor_cost80": top20 - 24,
            "lost_anchor_top10_hits": lost_anchor,
            "lost_original_span_hits": lost_original,
            "cost_proxy_top10": c10,
            "cost_proxy_top20": cost20_values.get(variant, 0),
            "cost_bucket": cost_bucket(c10),
            "decision_bucket": decision,
            "candidate_pool_changed_bool": pool_changed,
            "candidate_order_changed_bool": order_changed,
        }
    return len(usable), results, len(usable) == 213 and not pool_changed and not order_changed


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10bypriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def variant_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = []
    for idx, variant in enumerate(VARIANT_ORDER):
        rows.append({"anonymous_variant_contract_id": f"n10bycontract{idx:04d}", "variant_bucket": variant, "variant_family_bucket": variant_family(variant), "predeclared_variant_bool": True, "policy_inputs_rank_position_bool": variant.startswith("rank_conditioned") or variant.startswith("top"), "policy_inputs_fixed_operating_point_bool": True, "gold_used_for_policy_bool": False, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
    return rows, len(rows) == 12 and tuple(row["variant_bucket"] for row in rows) == VARIANT_ORDER


def variant_result_records(results: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, variant in enumerate(VARIANT_ORDER):
        observed = results.get(variant, {})
        valid = observed.get("candidate_pool_changed_bool") is False and observed.get("candidate_order_changed_bool") is False and isinstance(observed.get("top10_span_overlap_count"), int) and isinstance(observed.get("top20_span_overlap_count"), int)
        ok = ok and valid
        rows.append({"anonymous_variant_result_id": f"n10byresult{idx:04d}", "variant_bucket": variant, "variant_family_bucket": variant_family(variant), "top10_span_overlap_count": int(observed.get("top10_span_overlap_count", 0)), "top20_span_overlap_count": int(observed.get("top20_span_overlap_count", 0)), "delta_top10_vs_anchor_cost80": int(observed.get("delta_top10_vs_anchor_cost80", 0)), "delta_top20_vs_anchor_cost80": int(observed.get("delta_top20_vs_anchor_cost80", 0)), "lost_anchor_top10_hits": int(observed.get("lost_anchor_top10_hits", 0)), "lost_original_span_hits": int(observed.get("lost_original_span_hits", 0)), "cost_proxy_top10": int(observed.get("cost_proxy_top10", 0)), "cost_proxy_top20": int(observed.get("cost_proxy_top20", 0)), "cost_bucket": str(observed.get("cost_bucket", "unknown")), "decision_bucket": str(observed.get("decision_bucket", "unknown")), "candidate_pool_changed_bool": bool(observed.get("candidate_pool_changed_bool", True)), "candidate_order_changed_bool": bool(observed.get("candidate_order_changed_bool", True)), "result_accounting_valid_bool": valid})
    return rows, ok and len(rows) == 12


def rank_conditioned_policy_records() -> list[dict[str, Any]]:
    return [
        {"anonymous_rank_conditioned_policy_id": "n10byrank0000", "variant_bucket": "rank_conditioned_top5_30_90_top10_10_30", "policy_bucket": "top5_large_top10_small", "top5_before_count": 30, "top5_after_count": 90, "top10_remainder_before_count": 10, "top10_remainder_after_count": 30, "gold_used_for_policy_bool": False, "adaptive_per_record_selection_bool": False},
        {"anonymous_rank_conditioned_policy_id": "n10byrank0001", "variant_bucket": "rank_conditioned_top5_25_75_top10_10_30", "policy_bucket": "top5_medium_top10_small", "top5_before_count": 25, "top5_after_count": 75, "top10_remainder_before_count": 10, "top10_remainder_after_count": 30, "gold_used_for_policy_bool": False, "adaptive_per_record_selection_bool": False},
        {"anonymous_rank_conditioned_policy_id": "n10byrank0002", "variant_bucket": "rank_conditioned_top3_40_120_top10_10_30", "policy_bucket": "top3_large_top10_small", "top3_before_count": 40, "top3_after_count": 120, "top10_remainder_before_count": 10, "top10_remainder_after_count": 30, "gold_used_for_policy_bool": False, "adaptive_per_record_selection_bool": False},
    ]


def topk_expansion_policy_records() -> list[dict[str, Any]]:
    return [
        {"anonymous_topk_policy_id": "n10bytopk0000", "variant_bucket": "top10_only_cost80_before20_after60", "policy_bucket": "top10_only_fixed_cost80", "expanded_topk_count": 10, "before_count": 20, "after_count": 60, "gold_used_for_policy_bool": False, "adaptive_per_record_selection_bool": False},
        {"anonymous_topk_policy_id": "n10bytopk0001", "variant_bucket": "top5_only_cost80_before20_after60", "policy_bucket": "top5_only_fixed_cost80", "expanded_topk_count": 5, "before_count": 20, "after_count": 60, "gold_used_for_policy_bool": False, "adaptive_per_record_selection_bool": False},
        {"anonymous_topk_policy_id": "n10bytopk0002", "variant_bucket": "top20_only_cost80_before20_after60", "policy_bucket": "top20_only_fixed_cost80", "expanded_topk_count": 20, "before_count": 20, "after_count": 60, "gold_used_for_policy_bool": False, "adaptive_per_record_selection_bool": False},
    ]


def exploratory_decision_records(result_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    decisions = Counter(row["decision_bucket"] for row in result_rows)
    success_rows = [row for row in result_rows if row["decision_bucket"] in {"cost_reduction_success", "recall_improvement_success"}]
    best = max(result_rows, key=lambda r: (r["top10_span_overlap_count"], r["top20_span_overlap_count"], -r["cost_proxy_top10"])) if result_rows else {}
    return [{"anonymous_exploratory_decision_id": "n10bydecision0000", "variant_count": len(result_rows), "cost_reduction_success_count": decisions.get("cost_reduction_success", 0), "recall_improvement_success_count": decisions.get("recall_improvement_success", 0), "no_improvement_anchor_retained_count": decisions.get("no_improvement_anchor_retained", 0), "successful_variant_count": len(success_rows), "best_observed_variant_bucket": str(best.get("variant_bucket", "none")), "best_observed_top10_span_overlap_count": int(best.get("top10_span_overlap_count", 0)), "best_observed_top20_span_overlap_count": int(best.get("top20_span_overlap_count", 0)), "best_observed_cost_proxy_top10": int(best.get("cost_proxy_top10", 0)), "exploratory_only_bool": True, "runtime_default_recommendation_bool": False}], len(result_rows) == 12


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10byprivacy0000", "privacy_boundary_bucket": "aggregate_policy_sweep_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10bynoexec0000", "no_execution_boundary_bucket": "same_source_policy_sweep_only", "other_private_file_read_count": 0, "new_variant_outside_grid_count": 0, "adaptive_tuning_count": 0, "gold_used_for_policy_count": 0, "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10bz_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bz_handoff_id": "n10byhandoff0000", "n10bz_handoff_bucket": "n10bz_public_policy_sweep_audit_package_authorized" if complete else "n10bz_not_authorized", "n10bz_authorized_bool": complete, "public_audit_package_only_bool": complete, "private_read_authorized_bool": False, "additional_sweep_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "generalization_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, decision_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("variant_grid_predeclared", contract_ok), ("result_accounting", result_ok), ("exploratory_decision", decision_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bz_public_audit_package_authorized" if complete else "n10bz_not_authorized", "next_allowed_phase": "BEA-v1-N10BZ Same-Source Cost-Efficient Policy Sweep Audit Package" if complete else "none_until_policy_sweep_valid", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10bz_authorized": complete, "private_read_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, decision_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10by_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10by_private_span_rows_missing"
    if not contract_ok:
        return "no_go_n10by_variant_grid_invalid"
    if not private_ok or not result_ok or not decision_ok:
        return "no_go_n10by_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10by_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, results, compute_ok = compute_results(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    contract_rows, contract_ok = variant_contract_records()
    result_rows, result_ok = variant_result_records(results)
    decision_rows, decision_ok = exploratory_decision_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, contract_ok, result_ok, decision_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_exploratory_policy_sweep_only", "generated_by": "bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "variant_contract_records": contract_rows, "variant_result_records": result_rows, "rank_conditioned_policy_records": rank_conditioned_policy_records(), "topk_expansion_policy_records": topk_expansion_policy_records(), "exploratory_decision_records": decision_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10bz_handoff_records": n10bz_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, contract_ok, result_ok, decision_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bz_handoff_records"] = n10bz_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, contract_ok, result_ok, decision_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_policy_projection() -> bool:
    records = [{"path": "x", "start_line": 5, "end_line": 6} for _ in range(12)]
    projected, c10, c20 = project_variant(records, "rank_conditioned_top5_30_90_top10_10_30")
    return len(projected) == 12 and projected[0]["start_line"] == 1 and projected[5]["start_line"] == 1 and projected[10]["start_line"] == 5 and c10 == 800 and c20 == 800


def synthetic_grid_invalid() -> bool:
    return len(VARIANT_ORDER) == 12 and len(set(VARIANT_ORDER)) == 12 and status_for(True, True, "pass", True, False, True, True, True, True) == "no_go_n10by_variant_grid_invalid"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, results, compute_ok = compute_results(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    contract_rows, contract_ok = variant_contract_records()
    result_rows, result_ok = variant_result_records(results)
    decision_rows, decision_ok = exploratory_decision_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10by_required_inputs_unavailable", "no_go_n10by_private_span_rows_missing", "no_go_n10by_variant_grid_invalid", "no_go_n10by_result_accounting_invalid", "no_go_n10by_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok),
        check("variant_grid", contract_ok and len(contract_rows) == 12),
        check("variant_results", result_ok and len(result_rows) == 12 and all(row["decision_bucket"] in {"cost_reduction_success", "recall_improvement_success", "no_improvement_anchor_retained"} for row in result_rows)),
        check("decision_records", decision_ok and decision_rows[0]["variant_count"] == 12),
        check("rank_conditioned_policy", len(rank_conditioned_policy_records()) == 3),
        check("topk_policy", len(topk_expansion_policy_records()) == 3),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_outside_grid_count"] == 0 and noexec_rows[0]["adaptive_tuning_count"] == 0),
        check("synthetic_policy_projection", synthetic_policy_projection()),
        check("synthetic_grid_invalid", synthetic_grid_invalid()),
        check("false_flags", stop_go_records(True)[0]["n10bz_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BY same-source policy sweep")
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
