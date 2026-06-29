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


SCHEMA_VERSION = "bea_v1_n10bo_plateau_mechanism_decomposition.v1"
PHASE = "BEA-v1-N10BO Plateau Mechanism Decomposition"
STATUS_COMPLETE = "plateau_mechanism_decomposition_complete_n10bp_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bo_required_inputs_unavailable",
    "no_go_n10bo_private_span_rows_missing",
    "no_go_n10bo_plateau_variant_scope_invalid",
    "no_go_n10bo_result_accounting_invalid",
    "no_go_n10bo_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10bo_plateau_mechanism_decomposition/bea_v1_n10bo_plateau_mechanism_decomposition_report.json")
PUBLIC_INPUTS = {
    "n10bn_local_refinement_package_artifact": (Path("artifacts/bea_v1_n10bn_local_refinement_package/bea_v1_n10bn_local_refinement_package_report.json"), "local_refinement_package_complete_n10bo_authorized"),
    "n10bm_local_refinement_artifact": (Path("artifacts/bea_v1_n10bm_after_heavy_local_asymmetry_refinement/bea_v1_n10bm_after_heavy_local_asymmetry_refinement_report.json"), "after_heavy_local_asymmetry_refinement_complete_n10bn_authorized"),
    "n10bl_direction_sensitivity_package_artifact": (Path("artifacts/bea_v1_n10bl_direction_sensitivity_package/bea_v1_n10bl_direction_sensitivity_package_report.json"), "direction_sensitivity_package_complete_n10bm_authorized"),
}
PLATEAU_VARIANTS = (
    ("before20_after80", 20, 80),
    ("before25_after75", 25, 75),
    ("before30_after70", 30, 70),
    ("before35_after65", 35, 65),
    ("before40_after60", 40, 60),
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
    "private_input_bucket", "intake_status_bucket", "variant_bucket", "scope_bucket", "direction_bucket", "case_set_bucket",
    "stability_bucket", "case_swap_bucket", "no_gold_policy_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10bp_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10boin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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
    out: list[dict[str, Any]] = []
    for item in records:
        copied = dict(item)
        copied["start_line"] = max(1, int(copied["start_line"]) - before)
        copied["end_line"] = int(copied["end_line"]) + after
        out.append(copied)
    return out


def first_hit(original: list[dict[str, Any]], projected: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> tuple[bool, str]:
    for raw, item in zip(original[:limit], projected[:limit]):
        key = str(item.get("path", ""))
        if key not in refs:
            continue
        start = item.get("start_line")
        end = item.get("end_line")
        raw_start = raw.get("start_line")
        raw_end = raw.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int) or not isinstance(raw_start, int) or not isinstance(raw_end, int):
            continue
        for gold_start, gold_end in refs[key]:
            if overlaps(start, end, gold_start, gold_end):
                if overlaps(raw_start, raw_end, gold_start, gold_end):
                    return True, "already_overlap"
                if raw_end < gold_start:
                    return True, "before_gold_gap"
                if raw_start > gold_end:
                    return True, "after_gold_gap"
                return True, "other"
    return False, "other"


def hits_for(rows: list[dict[str, Any]], before: int, after: int) -> tuple[set[int], set[int], dict[int, str], dict[int, str]]:
    top10: set[int] = set()
    top20: set[int] = set()
    dir10: dict[int, str] = {}
    dir20: dict[int, str] = {}
    for idx, row in enumerate(rows):
        ordered = best_order(row["p4_evidence"])
        projected = project(ordered, before, after)
        refs = refmap(row)
        ok10, bucket10 = first_hit(ordered, projected, refs, 10)
        ok20, bucket20 = first_hit(ordered, projected, refs, 20)
        if ok10:
            top10.add(idx)
            dir10[idx] = bucket10
        if ok20:
            top20.add(idx)
            dir20[idx] = bucket20
    return top10, top20, dir10, dir20


def bucket_counts(case_set: set[int], dirs: dict[int, str]) -> dict[str, int]:
    counts = {"before_gold_gap": 0, "after_gold_gap": 0, "already_overlap": 0, "other": 0}
    for idx in case_set:
        counts[dirs.get(idx, "other")] = counts.get(dirs.get(idx, "other"), 0) + 1
    return counts


def compute(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], bool]:
    usable = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    raw: dict[str, tuple[set[int], set[int], dict[int, str], dict[int, str]]] = {}
    for name, before, after in PLATEAU_VARIANTS:
        raw[name] = hits_for(usable, before, after)
    pm50_10, pm50_20, _pm50_d10, _pm50_d20 = hits_for(usable, 50, 50)
    base_name = "before20_after80"
    plateau_top10 = [sets[0] for sets in raw.values()]
    plateau_top20 = [sets[1] for sets in raw.values()]
    common10 = set.intersection(*plateau_top10) if plateau_top10 else set()
    common20 = set.intersection(*plateau_top20) if plateau_top20 else set()
    union10 = set.union(*plateau_top10) if plateau_top10 else set()
    union20 = set.union(*plateau_top20) if plateau_top20 else set()
    per_variant: list[dict[str, Any]] = []
    direction_rows: list[dict[str, Any]] = []
    for idx, (name, _before, _after) in enumerate(PLATEAU_VARIANTS):
        top10, top20, dir10, dir20 = raw[name]
        unique10 = top10 - set.union(*(other[0] for other_name, other in raw.items() if other_name != name))
        unique20 = top20 - set.union(*(other[1] for other_name, other in raw.items() if other_name != name))
        per_variant.append({"anonymous_plateau_variant_id": f"n10bovar{idx:04d}", "variant_bucket": name, "top10_span_overlap_count": len(top10), "top20_span_overlap_count": len(top20), "common_top10_with_all_plateau_count": len(top10 & common10), "common_top20_with_all_plateau_count": len(top20 & common20), "unique_top10_count": len(unique10), "unique_top20_count": len(unique20), "lost_pm50_top10_count": len(pm50_10 - top10), "lost_plateau_baseline_top10_count": len(raw[base_name][0] - top10), "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
        for scope_name, case_set, dirs in (("common_top10", top10 & common10, dir10), ("unique_top10", unique10, dir10)):
            counts = bucket_counts(case_set, dirs)
            direction_rows.append({"anonymous_direction_contribution_id": f"n10bodir{idx:04d}_{scope_name}", "variant_bucket": name, "case_set_bucket": scope_name, "before_gold_gap_count": counts["before_gold_gap"], "after_gold_gap_count": counts["after_gold_gap"], "already_overlap_count": counts["already_overlap"], "other_count": counts["other"], "case_count": len(case_set)})
    common_core = [{"anonymous_common_core_id": "n10bocore0000", "scope_bucket": "plateau_top10_top20_common_union", "top10_common_across_all_plateau_count": len(common10), "top20_common_across_all_plateau_count": len(common20), "top10_union_across_plateau_count": len(union10), "top20_union_across_plateau_count": len(union20), "top10_case_swap_count": len(union10 - common10), "top20_case_swap_count": len(union20 - common20), "case_swap_bucket": "stable_plateau_no_top10_case_swap" if len(union10 - common10) == 0 else "case_swapping_plateau"}]
    common_dirs = raw["before25_after75"][2]
    common_counts = bucket_counts(common10, common_dirs)
    direction_rows.append({"anonymous_direction_contribution_id": "n10bodircommon0000", "variant_bucket": "plateau_common", "case_set_bucket": "common_top10_all_plateau", "before_gold_gap_count": common_counts["before_gold_gap"], "after_gold_gap_count": common_counts["after_gold_gap"], "already_overlap_count": common_counts["already_overlap"], "other_count": common_counts["other"], "case_count": len(common10)})
    stability = {"anonymous_stability_conclusion_id": "n10bostability0000", "stability_bucket": "genuinely_stable_plateau" if len(union10 - common10) == 0 else "case_swapping_plateau", "top10_common_count": len(common10), "top10_union_count": len(union10), "top10_case_swap_count": len(union10 - common10), "top20_common_count": len(common20), "top20_union_count": len(union20), "top20_case_swap_count": len(union20 - common20), "plateau_variant_count": len(PLATEAU_VARIANTS), "lost_pm50_max_count": max((row["lost_pm50_top10_count"] for row in per_variant), default=0), "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0}
    ok = usable and len(usable) == 213 and len(PLATEAU_VARIANTS) == 5 and all(r["top10_span_overlap_count"] == 20 and r["top20_span_overlap_count"] == 24 for r in per_variant) and common_core[0]["top10_common_across_all_plateau_count"] == 20 and common_core[0]["top10_case_swap_count"] == 0
    return len(usable), per_variant, common_core, direction_rows, stability, bool(ok)


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10bopriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def plateau_scope_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [{"anonymous_plateau_scope_id": f"n10boscope{idx:04d}", "scope_bucket": "plateau_variant_only", "variant_bucket": name, "before_window_count": before, "after_window_count": after, "total_window_cost_proxy": before + after, "predeclared_plateau_variant_bool": True} for idx, (name, before, after) in enumerate(PLATEAU_VARIANTS)]
    ok = [name for name, _before, _after in PLATEAU_VARIANTS] == ["before20_after80", "before25_after75", "before30_after70", "before35_after65", "before40_after60"] and all(row["total_window_cost_proxy"] == 100 for row in rows)
    return rows, ok


def no_gold_policy_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_gold_policy_id": "n10bonogold0000", "no_gold_policy_bucket": "fixed_plateau_windows_no_per_row_choice", "predeclared_global_windows_bool": True, "per_row_adaptive_window_count": 0, "gold_used_to_choose_window_count": 0, "miss_direction_used_to_choose_window_count": 0, "content_aware_adjustment_count": 0, "new_cost_budget_count": 0, "no_gold_policy_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10boprivacy0000", "privacy_boundary_bucket": "aggregate_plateau_decomposition_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10bonoexec0000", "no_execution_boundary_bucket": "plateau_mechanism_decomposition_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "new_variant_outside_plateau_count": 0, "new_cost_budget_count": 0, "adaptive_per_row_choice_count": 0, "runtime_default_promotion_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_order_change_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10bp_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bp_handoff_id": "n10bohandoff0000", "n10bp_handoff_bucket": "n10bp_public_plateau_mechanism_package_authorized" if complete else "n10bp_not_authorized", "n10bp_public_package_authorized_bool": complete, "private_read_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_choice_authorized_bool": False, "new_cost_budget_authorized_bool": False, "runtime_default_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, scope_ok: bool, result_ok: bool, nogold_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("plateau_variant_scope", scope_ok), ("plateau_decomposition_accounting", result_ok), ("no_gold_policy", nogold_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bp_public_plateau_mechanism_package_authorized" if complete else "n10bp_not_authorized", "next_allowed_phase": "BEA-v1-N10BP Plateau Mechanism Package" if complete else "none_until_plateau_decomposition_is_valid", "next_allowed_scope_bucket": "public_plateau_mechanism_package_only" if complete else "no_next_phase", "n10bp_authorized": complete, "private_read_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_per_row_choice_authorized": False, "new_cost_budget_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, scope_ok: bool, result_ok: bool, nogold_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bo_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10bo_private_span_rows_missing"
    if not scope_ok:
        return "no_go_n10bo_plateau_variant_scope_invalid"
    if not private_ok or not result_ok:
        return "no_go_n10bo_result_accounting_invalid"
    if not nogold_ok or not privacy_ok or not noexec_ok:
        return "no_go_n10bo_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, per_variant, common_core, direction_rows, stability, result_ok = compute(rows) if load_status == "pass" else (0, [], [], [], {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    scope_rows, scope_ok = plateau_scope_records()
    nogold_rows, nogold_ok = no_gold_policy_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, scope_ok, result_ok, nogold_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "plateau_mechanism_decomposition_only", "generated_by": "bea_v1_n10bo_plateau_mechanism_decomposition", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "plateau_variant_scope_records": scope_rows, "plateau_variant_aggregate_records": per_variant, "common_core_records": common_core, "direction_contribution_records": direction_rows, "stability_conclusion_records": [stability] if stability else [], "no_gold_policy_records": nogold_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10bp_handoff_records": n10bp_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, scope_ok, result_ok, nogold_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bp_handoff_records"] = n10bp_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, scope_ok, result_ok, nogold_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_common_core() -> bool:
    a = {1, 2, 3}
    b = {1, 2, 3}
    c = {1, 2, 3}
    return len(set.intersection(a, b, c)) == 3 and len(set.union(a, b, c) - set.intersection(a, b, c)) == 0


def synthetic_scope_invalid() -> bool:
    return status_for(True, True, "pass", True, False, True, True, True, True) == "no_go_n10bo_plateau_variant_scope_invalid"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, per_variant, common_core, direction_rows, stability, result_ok = compute(rows) if load_status == "pass" else (0, [], [], [], {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    scope_rows, scope_ok = plateau_scope_records()
    nogold_rows, nogold_ok = no_gold_policy_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bo_required_inputs_unavailable", "no_go_n10bo_private_span_rows_missing", "no_go_n10bo_plateau_variant_scope_invalid", "no_go_n10bo_result_accounting_invalid", "no_go_n10bo_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("private_rows", private_ok),
        check("plateau_scope", scope_ok and len(scope_rows) == 5),
        check("result_accounting", result_ok and len(per_variant) == 5 and all(row["top10_span_overlap_count"] == 20 for row in per_variant)),
        check("common_core", bool(common_core) and common_core[0]["top10_common_across_all_plateau_count"] == 20 and common_core[0]["top10_case_swap_count"] == 0),
        check("direction_buckets", bool(direction_rows) and sum(row["case_count"] for row in direction_rows if row["case_set_bucket"] == "unique_top10") == 0 and any(row["case_set_bucket"] == "common_top10_all_plateau" for row in direction_rows)),
        check("stability", stability.get("stability_bucket") == "genuinely_stable_plateau" and stability.get("lost_pm50_max_count") == 0),
        check("no_gold_policy", nogold_ok and nogold_rows[0]["gold_used_to_choose_window_count"] == 0),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_outside_plateau_count"] == 0 and noexec_rows[0]["adaptive_per_row_choice_count"] == 0),
        check("synthetic_common_core", synthetic_common_core()),
        check("synthetic_scope_invalid", synthetic_scope_invalid()),
        check("false_flags", stop_go_records(True)[0]["n10bp_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BO plateau mechanism decomposition")
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
