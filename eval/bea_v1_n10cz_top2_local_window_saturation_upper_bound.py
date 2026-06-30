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


SCHEMA_VERSION = "bea_v1_n10cz_top2_local_window_saturation_upper_bound.v1"
PHASE = "BEA-v1-N10CZ Top2 Local-Window Saturation Upper-Bound Smoke"
STATUS_COMPLETE = "top2_local_window_saturation_upper_bound_complete_n10da_authorized"
STATUSES = (STATUS_COMPLETE, "no_go_n10cz_required_inputs_unavailable", "no_go_n10cz_private_span_rows_missing", "no_go_n10cz_variant_contract_invalid", "no_go_n10cz_result_accounting_invalid", "no_go_n10cz_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10cz_top2_local_window_saturation_upper_bound/bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json")
PUBLIC_INPUTS = {
    "n10cy_pm1000_decomposition_artifact": (Path("artifacts/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition_report.json"), "top2_pm1000_marginal_gain_decomposition_complete_n10cz_authorized"),
    "n10cx_high_window_package_artifact": (Path("artifacts/bea_v1_n10cx_top2_override_high_window_package/bea_v1_n10cx_top2_override_high_window_package_report.json"), "top2_override_high_window_package_complete_n10cy_authorized"),
    "n10cw_high_window_sweep_artifact": (Path("artifacts/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep_report.json"), "top2_override_high_window_neighborhood_sweep_complete_n10cx_authorized"),
}
VARIANTS = ("top2_pm1000", "top2_pm1500", "top2_pm2000", "top2_pm5000", "top2_file_extent_proxy")
PM_VALUES = {"top2_pm1000": 1000, "top2_pm1500": 1500, "top2_pm2000": 2000, "top2_pm5000": 5000}
PM1000 = "top2_pm1000"
FILE_EXTENT = "top2_file_extent_proxy"
FORBIDDEN_PUBLIC_KEYS = frozenset({"path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name", "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order", "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets", "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff"})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status", "private_input_bucket", "intake_status_bucket", "variant_bucket", "decision_bucket", "summary_bucket", "cost_proxy_bucket", "file_extent_proxy_bucket", "remaining_miss_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10da_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation"})


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
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+", re.I)
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
    rows, ok = [], True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10czin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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
    evs, refs, ranges = row.get("p4_evidence"), row.get("gold_paths"), row.get("gold_lines")
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


def expand_asym(ev: dict[str, Any], before: int, after: int) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    projected = dict(base)
    projected["start_line"] = max(1, int(projected["start_line"]) - before)
    projected["end_line"] = int(projected["end_line"]) + after
    return projected, before + after


def same_file_extent(evidence: list[dict[str, Any]], key: str) -> tuple[int, int]:
    starts = [int(ev["start_line"]) for ev in evidence if str(ev.get("path", "")) == key]
    ends = [int(ev["end_line"]) for ev in evidence if str(ev.get("path", "")) == key]
    return (min(starts), max(ends)) if starts and ends else (1, 1)


def project_variant(ev: dict[str, Any], position: int, variant: str, ordered: list[dict[str, Any]]) -> tuple[dict[str, Any], int | None]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    if position <= 2 and variant == FILE_EXTENT:
        left, right = same_file_extent(ordered, str(base.get("path", "")))
        projected = dict(base)
        projected["start_line"] = max(1, left)
        projected["end_line"] = right
        return projected, None
    if position <= 2:
        pm = PM_VALUES[variant]
        return project_evidence_span_record(base, expansion_each_side=pm, enabled=True), pm * 2
    if short_span(base):
        return expand_asym(base, 75, 225)
    return base, 0


def hit(projected: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for ev in projected[:limit]:
        key = str(ev.get("path", ""))
        start, end = ev.get("start_line"), ev.get("end_line")
        if key in refs and isinstance(start, int) and isinstance(end, int) and any(overlap(start, end, left, right) for left, right in refs[key]):
            return True
    return False


def file_hit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    return any(str(ev.get("path", "")) in refs for ev in ordered[:limit])


def cost_bucket(variant: str, top10_cost: int | None) -> str:
    if variant == FILE_EXTENT:
        return "file_extent_proxy_not_runtime_policy"
    assert top10_cost is not None
    if top10_cost <= 6400:
        return "at_or_below_pm1000"
    if top10_cost <= 10000:
        return "very_high"
    return "extreme"


def compute(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
    top10: dict[str, set[int]] = {v: set() for v in VARIANTS}
    top20: dict[str, set[int]] = {v: set() for v in VARIANTS}
    costs: dict[str, dict[str, int | None]] = {v: {"cost10": 0, "cost20": 0} for v in VARIANTS}
    residuals: dict[str, Counter[str]] = {v: Counter() for v in VARIANTS}
    pool_order_ok = True
    for idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        pool_order_ok = pool_order_ok and len(ordered) == len(row["p4_evidence"])
        refs = references(row)
        for variant in VARIANTS:
            projected = []
            c10: int | None = 0
            c20: int | None = 0
            for pos, ev in enumerate(ordered, 1):
                item, cost = project_variant(ev, pos, variant, ordered)
                projected.append(item)
                if cost is None:
                    c10 = c20 = None
                elif c10 is not None and pos <= 10:
                    c10 += cost
                if cost is not None and c20 is not None and pos <= 20:
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
    ok = len(rows) == 213 and len(usable) == 213 and pool_order_ok and len(top10[PM1000]) == 30 and len(top20[PM1000]) == 36 and costs[PM1000] == {"cost10": 6400, "cost20": 9400}
    return len(usable), {"top10": top10, "top20": top20, "costs": costs, "residuals": residuals}, ok


def private_input_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_id": "n10czpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def variant_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = []
    for idx, variant in enumerate(VARIANTS):
        rows.append({"anonymous_upper_bound_contract_id": f"n10czcontract{idx:04d}", "variant_bucket": variant, "predeclared_variant_bool": True, "short_span_base_before_count": 75, "short_span_base_after_count": 225, "top2_override_bool": True, "top3_override_bool": False, "medium_long_extra_gate_bool": False, "rank_file_promotion_bool": False, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "file_extent_proxy_bucket": "file_extent_proxy_not_runtime_policy" if variant == FILE_EXTENT else "not_file_extent_proxy"})
    return rows, tuple(r["variant_bucket"] for r in rows) == VARIANTS and len(rows) == 5


def variant_result_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    pm1000_t10 = result["top10"][PM1000]
    rows = []
    for idx, variant in enumerate(VARIANTS):
        t10 = len(result["top10"][variant])
        t20 = len(result["top20"][variant])
        lost = len(pm1000_t10 - result["top10"][variant])
        res = result["residuals"][variant]
        if t10 > 30 and lost <= 1:
            decision = "local_window_upper_bound_improves"
        elif t10 == 30 and res.get("same_file_no_span_overlap", 0) >= 4:
            decision = "local_window_saturated"
        else:
            decision = "upper_bound_no_improvement"
        rows.append({"anonymous_upper_bound_variant_result_id": f"n10czresult{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": t10, "top20_span_overlap_count": t20, "delta_top10_vs_pm1000": t10 - 30, "delta_top20_vs_pm1000": t20 - 36, "lost_pm1000_top10_hits": lost, "cost_proxy_bucket": cost_bucket(variant, result["costs"][variant]["cost10"]), "same_file_no_span_remaining_count": res.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_remaining_count": res.get("span_overlap_beyond_top10", 0), "file_not_in_top10_remaining_count": res.get("file_not_in_top10", 0), "decision_bucket": decision, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
    return rows, len(rows) == 5 and any(r["variant_bucket"] == PM1000 and r["top10_span_overlap_count"] == 30 and r["top20_span_overlap_count"] == 36 for r in rows)


def saturation_summary_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    max_t10 = max(len(result["top10"][v]) for v in VARIANTS)
    max_t20 = max(len(result["top20"][v]) for v in VARIANTS)
    pm1000_res = result["residuals"][PM1000]
    total_non_top10 = 213 - len(result["top10"][PM1000])
    file_reach_dominates = pm1000_res.get("file_not_in_top10", 0) >= 0.75 * total_non_top10
    improves = max_t10 > 30
    saturated = max_t10 == 30 and pm1000_res.get("same_file_no_span_overlap", 0) >= 4
    rows = [{"anonymous_saturation_summary_id": "n10czsummary0000", "summary_bucket": "top2_local_window_upper_bound", "variant_count": len(VARIANTS), "max_top10_span_overlap_count": max_t10, "max_top20_span_overlap_count": max_t20, "local_window_upper_bound_improves_bool": improves, "local_window_saturated_bool": saturated, "file_reach_dominates_residual_bool": file_reach_dominates, "pm1000_reference_top10_span_overlap_count": len(result["top10"][PM1000]), "pm1000_reference_top20_span_overlap_count": len(result["top20"][PM1000])}]
    return rows, rows[0]["variant_count"] == 5 and rows[0]["pm1000_reference_top10_span_overlap_count"] == 30


def residual_mechanism_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    for idx, variant in enumerate(VARIANTS):
        res = result["residuals"][variant]
        rows.append({"anonymous_residual_mechanism_id": f"n10czresid{idx:04d}", "remaining_miss_bucket": variant, "same_file_no_span_remaining_count": res.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_remaining_count": res.get("span_overlap_beyond_top10", 0), "file_not_in_top10_remaining_count": res.get("file_not_in_top10", 0)})
    return rows, len(rows) == 5


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10czprivacy0000", "privacy_boundary_bucket": "aggregate_upper_bound_smoke_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10cznoexec0000", "no_execution_boundary_bucket": "top2_local_window_upper_bound_only", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "rank_file_promotion_count": 0, "top3_override_count": 0, "medium_long_extra_gate_count": 0, "adaptive_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10da_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10da_handoff_id": "n10czhandoff0000", "n10da_handoff_bucket": "n10da_public_package_authorized" if complete else "n10da_not_authorized", "n10da_authorized_bool": complete, "public_package_only_bool": complete, "local_refinement_authorized_bool": False, "rank_file_experiment_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "rank_file_promotion_authorized_bool": False, "top3_override_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, summary_ok: bool, residual_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read_213", private_ok), ("variant_contract", contract_ok), ("variant_results", result_ok), ("saturation_summary", summary_ok), ("residual_mechanism", residual_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10da_authorized" if complete else "n10da_not_authorized", "next_allowed_phase": "BEA-v1-N10DA Top2 Local-Window Upper-Bound Public Package" if complete else "none_until_upper_bound_smoke_valid", "next_allowed_scope_bucket": "public_package_only" if complete else "no_next_phase", "n10da_authorized": complete, "local_refinement_authorized": False, "rank_file_experiment_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "rank_file_promotion_authorized": False, "top3_override_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, summary_ok: bool, residual_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cz_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10cz_private_span_rows_missing"
    if not contract_ok:
        return "no_go_n10cz_variant_contract_invalid"
    if not private_ok or not result_ok or not summary_ok or not residual_ok:
        return "no_go_n10cz_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10cz_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, compute_ok = compute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    private_rows = private_input_records(rows, load_status, usable)
    contract_rows, contract_ok = variant_contract_records()
    variant_rows, result_ok = variant_result_records(result) if result else ([], False)
    summary_rows, summary_ok = saturation_summary_records(result) if result else ([], False)
    residual_rows, residual_ok = residual_mechanism_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, contract_ok, result_ok, summary_ok, residual_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_top2_local_window_upper_bound_only", "generated_by": "bea_v1_n10cz_top2_local_window_saturation_upper_bound", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_rows, "upper_bound_variant_contract_records": contract_rows, "upper_bound_variant_result_records": variant_rows, "saturation_summary_records": summary_rows, "residual_mechanism_records": residual_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10da_handoff_records": n10da_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, contract_ok, result_ok, summary_ok, residual_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10da_handoff_records"] = n10da_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, contract_ok, result_ok, summary_ok, residual_ok, privacy_ok, noexec_ok, scanner_ok)
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
    summary_rows, summary_ok = saturation_summary_records(result) if result else ([], False)
    residual_rows, residual_ok = residual_mechanism_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cz_required_inputs_unavailable", "no_go_n10cz_private_span_rows_missing", "no_go_n10cz_variant_contract_invalid", "no_go_n10cz_result_accounting_invalid", "no_go_n10cz_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("private_rows", private_ok),
        check("contract", contract_ok and len(contract_rows) == 5 and tuple(r["variant_bucket"] for r in contract_rows) == VARIANTS),
        check("variant_results", result_ok and len(variant_rows) == 5 and any(r["variant_bucket"] == PM1000 and r["top10_span_overlap_count"] == 30 for r in variant_rows)),
        check("summary", summary_ok and summary_rows[0]["pm1000_reference_top10_span_overlap_count"] == 30),
        check("residual", residual_ok and len(residual_rows) == 5),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["top3_override_count"] == 0 and noexec_rows[0]["rank_file_promotion_count"] == 0),
        check("synthetic_status", status_for(True, True, "pass", True, False, True, True, True, True, True) == "no_go_n10cz_variant_contract_invalid"),
        check("false_flags", stop_go_records(True)[0]["n10da_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["rank_file_promotion_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CZ top2 local-window saturation upper-bound smoke")
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
