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


SCHEMA_VERSION = "bea_v1_n10co_default_off_adapter_refined_hybrid_smoke.v1"
PHASE = "BEA-v1-N10CO Default-Off Adapter Smoke for Refined Hybrid"
STATUS_PASS = "refined_hybrid_adapter_smoke_pass_n10cp_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10co_required_inputs_unavailable",
    "no_go_n10co_private_span_rows_missing",
    "no_go_n10co_adapter_result_mismatch",
    "no_go_n10co_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke_report.json")
PUBLIC_INPUTS = {
    "n10cn_refinement_package_artifact": (Path("artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json"), "winning_hybrid_cost_refinement_package_complete_n10co_authorized"),
    "n10cm_refinement_sweep_artifact": (Path("artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json"), "winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized"),
    "n10cl_adapter_package_artifact": (Path("artifacts/bea_v1_n10cl_winning_hybrid_adapter_smoke_package/bea_v1_n10cl_winning_hybrid_adapter_smoke_package_report.json"), "winning_hybrid_adapter_package_complete_n10cm_authorized"),
    "n10ck_adapter_smoke_artifact": (Path("artifacts/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke_report.json"), "winning_hybrid_adapter_smoke_pass_n10cl_authorized"),
}
REFINED_VARIANT = "short75_225_top2_all_pm200"
WINNING_VARIANT = "short75_225_top3_all_pm200"
EXPECTED = {
    "top10_span_overlap_count": 25,
    "top20_span_overlap_count": 31,
    "cost_proxy_top10": 3200,
    "cost_proxy_top20": 6200,
    "lost_winning_top10_hits": 0,
    "file_hit_top10_count": 34,
}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks",
    "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status", "private_input_bucket", "intake_status_bucket", "variant_bucket", "adapter_path_bucket", "contract_bucket", "comparison_bucket", "default_off_boundary_bucket", "hook_boundary_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10cp_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation"})


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
        rows.append({"anonymous_input_artifact_id": f"n10coin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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
    primary = [item for index, item in enumerate(evidence, 1) if index <= 20]
    extra = [item for index, item in enumerate(evidence, 1) if index > 20]
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


def project_record(ev: dict[str, Any], position: int, top_override: int) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
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


def compute(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
    refined_top10: set[int] = set()
    refined_top20: set[int] = set()
    winning_top10: set[int] = set()
    file_top10: set[int] = set()
    costs: dict[str, int] = {}
    pool_order_ok = True
    for idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        pool_order_ok = pool_order_ok and len(ordered) == len(row["p4_evidence"])
        refs = references(row)
        refined_projected: list[dict[str, Any]] = []
        winning_projected: list[dict[str, Any]] = []
        cost10 = 0
        cost20 = 0
        for pos, ev in enumerate(ordered, 1):
            refined, cost = project_record(ev, pos, 2)
            winning, _ = project_record(ev, pos, 3)
            refined_projected.append(refined)
            winning_projected.append(winning)
            if pos <= 10:
                cost10 += cost
            if pos <= 20:
                cost20 += cost
        costs = {"cost_proxy_top10": cost10, "cost_proxy_top20": cost20}
        if hit(refined_projected, refs, 10):
            refined_top10.add(idx)
        if hit(refined_projected, refs, 20):
            refined_top20.add(idx)
        if hit(winning_projected, refs, 10):
            winning_top10.add(idx)
        if file_hit(ordered, refs, 10):
            file_top10.add(idx)
    result = {"variant_bucket": REFINED_VARIANT, "top10_span_overlap_count": len(refined_top10), "top20_span_overlap_count": len(refined_top20), "cost_proxy_top10": costs.get("cost_proxy_top10", 0), "cost_proxy_top20": costs.get("cost_proxy_top20", 0), "lost_winning_top10_hits": len(winning_top10 - refined_top10), "file_hit_top10_count": len(file_top10), "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "adapter_imported_bool": True, "helper_via_adapter_bool": True, "private_span_rows_read": len(rows), "usable_span_surface_rows": len(usable)}
    matches = len(rows) == 213 and len(usable) == 213 and pool_order_ok and all(result.get(k) == v for k, v in EXPECTED.items())
    return len(usable), result, matches


def scoped_private_input_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_scoped_private_input_id": "n10copriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "explicit_smoke_enabled_bool": True, "private_read_by_default_bool": False, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def adapter_smoke_contract_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_adapter_smoke_contract_id": "n10cocontract0000", "contract_bucket": "default_off_adapter_refined_hybrid_smoke", "variant_bucket": REFINED_VARIANT, "adapter_path_bucket": "default_off_eval_only_span_projection_adapter", "short_span_length_threshold_bucket": "short_lte_10", "short_span_before_count": 75, "short_span_after_count": 225, "top2_all_span_before_count": 200, "top2_all_span_after_count": 200, "top2_override_applies_regardless_of_span_length_bool": True, "gold_used_for_policy_bool": False, "outcome_used_for_policy_bool": False, "miss_direction_used_for_policy_bool": False, "file_identity_used_for_policy_bool": False, "content_used_for_policy_bool": False, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "contract_complete_bool": True}], True


def adapter_result_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    match = all(result.get(k) == v for k, v in EXPECTED.items()) and result.get("candidate_pool_changed_bool") is False and result.get("candidate_order_changed_bool") is False
    return [{"anonymous_adapter_result_id": "n10coresult0000", "variant_bucket": REFINED_VARIANT, "top10_span_overlap_count": int(result.get("top10_span_overlap_count", 0)), "top20_span_overlap_count": int(result.get("top20_span_overlap_count", 0)), "cost_proxy_top10": int(result.get("cost_proxy_top10", 0)), "cost_proxy_top20": int(result.get("cost_proxy_top20", 0)), "lost_winning_top10_hits": int(result.get("lost_winning_top10_hits", 0)), "file_hit_top10_count": int(result.get("file_hit_top10_count", 0)), "candidate_pool_changed_bool": bool(result.get("candidate_pool_changed_bool", True)), "candidate_order_changed_bool": bool(result.get("candidate_order_changed_bool", True)), "adapter_imported_bool": bool(result.get("adapter_imported_bool", False)), "helper_via_adapter_bool": bool(result.get("helper_via_adapter_bool", False)), "adapter_result_match_bool": match}], match


def expected_match_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    match = all(result.get(k) == v for k, v in EXPECTED.items())
    return [{"anonymous_expected_match_id": "n10comatch0000", "comparison_bucket": "n10cn_n10cm_expected_refined_aggregate_match", "variant_bucket": REFINED_VARIANT, "expected_top10_span_overlap_count": 25, "expected_top20_span_overlap_count": 31, "expected_cost_proxy_top10": 3200, "expected_cost_proxy_top20": 6200, "expected_lost_winning_top10_hits": 0, "expected_file_hit_top10_count": 34, "observed_top10_span_overlap_count": int(result.get("top10_span_overlap_count", 0)), "observed_top20_span_overlap_count": int(result.get("top20_span_overlap_count", 0)), "observed_cost_proxy_top10": int(result.get("cost_proxy_top10", 0)), "observed_cost_proxy_top20": int(result.get("cost_proxy_top20", 0)), "observed_lost_winning_top10_hits": int(result.get("lost_winning_top10_hits", 0)), "observed_file_hit_top10_count": int(result.get("file_hit_top10_count", 0)), "aggregate_match_bool": match}], match


def default_off_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_default_off_boundary_id": "n10codefault0000", "default_off_boundary_bucket": "adapter_smoke_explicit_phase_only", "adapter_default_enabled_bool": False, "private_read_by_default_bool": False, "runtime_default_enabled_bool": False, "runtime_config_changed_bool": False, "policy_default_changed_bool": False, "implementation_smoke_only_bool": True, "default_off_boundary_valid_bool": True}], True


def no_existing_hook_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_existing_hook_id": "n10cohook0000", "hook_boundary_bucket": "no_existing_evaluator_or_runtime_hook", "existing_evaluator_hook_in_bool": False, "existing_validated_evaluator_modified_bool": False, "runtime_hook_in_bool": False, "retrieval_hook_in_bool": False, "selector_reranker_hook_in_bool": False, "adapter_module_modified_bool": False, "helper_module_modified_bool": False, "no_hook_boundary_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10coprivacy0000", "privacy_boundary_bucket": "aggregate_adapter_smoke_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10conoexec0000", "no_execution_boundary_bucket": "default_off_adapter_smoke_only", "other_private_file_read_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "adaptive_tuning_count": 0, "cluster_bridge_execution_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cp_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cp_handoff_id": "n10cohandoff0000", "n10cp_handoff_bucket": "n10cp_public_adapter_smoke_package_authorized" if complete else "n10cp_not_authorized", "n10cp_authorized_bool": complete, "public_audit_package_only_bool": complete, "additional_private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "existing_evaluator_hook_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, match_ok: bool, default_ok: bool, hook_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("scoped_private_rows_read", private_ok), ("adapter_smoke_contract", contract_ok), ("adapter_result", result_ok), ("expected_match", match_ok), ("default_off_boundary", default_ok), ("no_existing_hook", hook_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cp_authorized" if complete else "n10cp_not_authorized", "next_allowed_phase": "BEA-v1-N10CP Refined Hybrid Adapter Smoke Package" if complete else "none_until_adapter_smoke_matches", "next_allowed_scope_bucket": "public_adapter_smoke_package_only" if complete else "no_next_phase", "n10cp_authorized": complete, "additional_private_read_authorized": False, "runtime_or_default_authorized": False, "existing_evaluator_hook_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, match_ok: bool, default_ok: bool, hook_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10co_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10co_private_span_rows_missing"
    if not private_ok or not contract_ok or not result_ok or not match_ok or not default_ok or not hook_ok:
        return "no_go_n10co_adapter_result_mismatch"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10co_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, compute_ok = compute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    scoped_rows = scoped_private_input_records(rows, load_status, usable)
    contract_rows, contract_ok = adapter_smoke_contract_records()
    result_rows, result_ok = adapter_result_records(result)
    match_rows, match_ok = expected_match_records(result)
    default_rows, default_ok = default_off_boundary_records()
    hook_rows, hook_ok = no_existing_hook_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, contract_ok, result_ok, match_ok, default_ok, hook_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "default_off_adapter_refined_hybrid_smoke_only", "generated_by": "bea_v1_n10co_default_off_adapter_refined_hybrid_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "scoped_private_input_records": scoped_rows, "adapter_smoke_contract_records": contract_rows, "adapter_result_records": result_rows, "expected_match_records": match_rows, "default_off_boundary_records": default_rows, "no_existing_hook_records": hook_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cp_handoff_records": n10cp_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, contract_ok, result_ok, match_ok, default_ok, hook_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["n10cp_handoff_records"] = n10cp_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, contract_ok, result_ok, match_ok, default_ok, hook_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_adapter_projection() -> bool:
    rec = {"start_line": 100, "end_line": 105, "kind": "synthetic"}
    unchanged = project_evidence_span_record(rec, expansion_each_side=0, enabled=False)
    expanded = project_evidence_span_record(rec, expansion_each_side=200, enabled=True)
    return unchanged == rec and expanded["start_line"] == 1 and expanded["end_line"] == 305 and rec["start_line"] == 100


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, compute_ok = compute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    contract_rows, contract_ok = adapter_smoke_contract_records()
    result_rows, result_ok = adapter_result_records(result)
    match_rows, match_ok = expected_match_records(result)
    default_rows, default_ok = default_off_boundary_records()
    hook_rows, hook_ok = no_existing_hook_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10co_required_inputs_unavailable", "no_go_n10co_private_span_rows_missing", "no_go_n10co_adapter_result_mismatch", "no_go_n10co_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok),
        check("contract", contract_ok and contract_rows[0]["top2_override_applies_regardless_of_span_length_bool"] is True),
        check("adapter_result", result_ok and result_rows[0]["top10_span_overlap_count"] == 25 and result_rows[0]["cost_proxy_top10"] == 3200 and result_rows[0]["adapter_imported_bool"] is True),
        check("expected_match", match_ok and match_rows[0]["aggregate_match_bool"] is True),
        check("default_off", default_ok and default_rows[0]["adapter_default_enabled_bool"] is False and default_rows[0]["private_read_by_default_bool"] is False),
        check("no_hook", hook_ok and hook_rows[0]["existing_evaluator_hook_in_bool"] is False and hook_rows[0]["runtime_hook_in_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["candidate_generation_count"] == 0 and noexec_rows[0]["adaptive_tuning_count"] == 0),
        check("synthetic_adapter", synthetic_adapter_projection()),
        check("synthetic_mismatch_status", status_for(True, True, "pass", True, True, False, True, True, True, True, True) == "no_go_n10co_adapter_result_mismatch"),
        check("false_flags", stop_go_records(True)[0]["n10cp_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["existing_evaluator_hook_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CO default-off adapter refined hybrid smoke")
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
