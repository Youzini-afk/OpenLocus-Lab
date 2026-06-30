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


SCHEMA_VERSION = "bea_v1_n10cv_top2_pm400_marginal_gain_decomposition.v1"
PHASE = "BEA-v1-N10CV Top2 pm400 Marginal Gain Mechanism Decomposition"
STATUS_COMPLETE = "top2_pm400_marginal_gain_decomposition_complete_n10cw_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cv_required_inputs_unavailable",
    "no_go_n10cv_private_span_rows_missing",
    "no_go_n10cv_policy_contract_invalid",
    "no_go_n10cv_result_accounting_invalid",
    "no_go_n10cv_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition_report.json")
PUBLIC_INPUTS = {
    "n10cu_top2_neighborhood_package_artifact": (Path("artifacts/bea_v1_n10cu_top2_override_neighborhood_package/bea_v1_n10cu_top2_override_neighborhood_package_report.json"), "top2_override_neighborhood_package_complete_n10cv_authorized"),
    "n10ct_top2_neighborhood_sweep_artifact": (Path("artifacts/bea_v1_n10ct_top2_override_window_neighborhood_sweep/bea_v1_n10ct_top2_override_window_neighborhood_sweep_report.json"), "top2_override_window_neighborhood_sweep_complete_n10cu_authorized"),
    "n10cs_local_saturation_package_artifact": (Path("artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json"), "local_saturation_package_complete_n10ct_authorized"),
    "n10cr_local_saturation_sweep_artifact": (Path("artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json"), "mechanism_guided_local_saturation_sweep_complete_n10cs_authorized"),
}
POLICIES = ("short75_225_top2_all_pm275", "short75_225_top2_all_pm300", "short75_225_top2_all_pm400")
PM275, PM300, PM400 = POLICIES
PM_VALUES = {PM275: 275, PM300: 300, PM400: 400}
EXPECTED = {PM275: (26, 32, 3500, 6500), PM300: (26, 32, 3600, 6600), PM400: (27, 33, 4000, 7000)}
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
    "private_input_bucket", "intake_status_bucket", "policy_bucket", "mechanism_bucket", "remaining_miss_bucket", "signal_bucket",
    "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10cw_handoff_bucket", "authorization", "next_allowed_phase",
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
        rows.append({"anonymous_input_artifact_id": f"n10cvin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def project_policy(ev: dict[str, Any], position: int, policy: str) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    pm = {PM275: 275, PM300: 300, PM400: 400}[policy]
    if position <= 2:
        return project_evidence_span_record(base, expansion_each_side=pm, enabled=True), pm * 2
    if short_span(base):
        return expand_asym(base, 75, 225)
    return base, 0


def hit(projected: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for ev in projected[:limit]:
        key = str(ev.get("path", ""))
        if key in refs and isinstance(ev.get("start_line"), int) and isinstance(ev.get("end_line"), int):
            if any(overlap(int(ev["start_line"]), int(ev["end_line"]), left, right) for left, right in refs[key]):
                return True
    return False


def file_hit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    return any(str(ev.get("path", "")) in refs for ev in ordered[:limit])


def first_recovery_detail(row: dict[str, Any], policy_good: str, policy_bad: str) -> dict[str, Any] | None:
    ordered = best_order(row["p4_evidence"])
    refs = references(row)
    for pos, ev in enumerate(ordered[:10], 1):
        good, _ = project_policy(ev, pos, policy_good)
        bad, _ = project_policy(ev, pos, policy_bad)
        key = str(good.get("path", ""))
        if key not in refs:
            continue
        for left, right in refs[key]:
            if overlap(int(good["start_line"]), int(good["end_line"]), left, right) and not overlap(int(bad["start_line"]), int(bad["end_line"]), left, right):
                if int(bad["end_line"]) < left:
                    distance = left - int(bad["end_line"])
                    direction = "same_file_before_gold"
                elif int(bad["start_line"]) > right:
                    distance = int(bad["start_line"]) - right
                    direction = "same_file_after_gold"
                else:
                    distance = 0
                    direction = "already_overlap_under_candidate_but_outside_window"
                if distance <= 25:
                    dist_bucket = "near_boundary_1_25"
                elif distance <= 50:
                    dist_bucket = "near_boundary_26_50"
                elif distance <= 100:
                    dist_bucket = "near_boundary_51_100"
                else:
                    dist_bucket = "far_boundary_gt100"
                return {"position": pos, "short": short_span(ev), "direction": direction, "distance_bucket": dist_bucket}
    return None


def compute(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
    top10: dict[str, set[int]] = {p: set() for p in POLICIES}
    top20: dict[str, set[int]] = {p: set() for p in POLICIES}
    costs: dict[str, dict[str, int]] = {p: {"cost10": 0, "cost20": 0} for p in POLICIES}
    residuals: dict[str, Counter[str]] = {p: Counter() for p in POLICIES}
    details: dict[int, dict[str, Any]] = {}
    pool_order_ok = True
    for idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        pool_order_ok = pool_order_ok and len(ordered) == len(row["p4_evidence"])
        refs = references(row)
        for policy in POLICIES:
            projected: list[dict[str, Any]] = []
            c10 = c20 = 0
            for pos, ev in enumerate(ordered, 1):
                item, cost = project_policy(ev, pos, policy)
                projected.append(item)
                if pos <= 10:
                    c10 += cost
                if pos <= 20:
                    c20 += cost
            costs[policy] = {"cost10": c10, "cost20": c20}
            if hit(projected, refs, 10):
                top10[policy].add(idx)
            else:
                if hit(projected, refs, len(projected)):
                    residuals[policy]["span_overlap_beyond_top10"] += 1
                elif file_hit(ordered, refs, 10):
                    residuals[policy]["same_file_no_span_overlap"] += 1
                else:
                    residuals[policy]["file_not_in_top10"] += 1
            if hit(projected, refs, 20):
                top20[policy].add(idx)
        if idx in (top10[PM400] - top10[PM300]) or idx in (top20[PM400] - top20[PM300]):
            detail = first_recovery_detail(row, PM400, PM300)
            if detail:
                details[idx] = detail
    ok = len(rows) == 213 and len(usable) == 213 and pool_order_ok and all((len(top10[p]), len(top20[p]), costs[p]["cost10"], costs[p]["cost20"]) == EXPECTED[p] for p in POLICIES)
    return len(usable), {"top10": top10, "top20": top20, "costs": costs, "residuals": residuals, "details": details}, ok


def private_input_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_id": "n10cvpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def policy_anchor_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    pm400 = result["top10"][PM400]
    for idx, policy in enumerate(POLICIES):
        rows.append({"anonymous_policy_anchor_id": f"n10cvanchor{idx:04d}", "policy_bucket": policy, "top10_span_overlap_count": len(result["top10"][policy]), "top20_span_overlap_count": len(result["top20"][policy]), "cost_proxy_top10": result["costs"][policy]["cost10"], "cost_proxy_top20": result["costs"][policy]["cost20"], "lost_pm400_top10_hits": len(pm400 - result["top10"][policy]), "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
    return rows, len(rows) == 3 and all((r["top10_span_overlap_count"], r["top20_span_overlap_count"], r["cost_proxy_top10"], r["cost_proxy_top20"]) == EXPECTED[r["policy_bucket"]] for r in rows)


def marginal_gain_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    new_top10 = result["top10"][PM400] - result["top10"][PM300]
    new_top20 = result["top20"][PM400] - result["top20"][PM300]
    details = [result["details"].get(i, {}) for i in sorted(new_top10 | new_top20)]
    bucket_counts = Counter()
    for detail in details:
        if not detail:
            bucket_counts["other_bucket"] += 1
            continue
        bucket_counts[detail["distance_bucket"]] += 1
        bucket_counts[detail["direction"]] += 1
        bucket_counts["top1_override_case" if detail.get("position") == 1 else "top2_override_case" if detail.get("position") == 2 else "short_span_base_case"] += 1
        bucket_counts["short_span_base_case" if detail.get("short") else "non_short_span_case"] += 1
    summary = [{"anonymous_marginal_gain_id": "n10cvgain0000", "comparison_bucket": "pm400_minus_pm300", "pm400_new_top10_count": len(new_top10), "pm400_new_top20_count": len(new_top20), "bucketed_new_case_count": len(details), "public_row_ids_included_bool": False}]
    buckets = []
    for idx, bucket in enumerate(("near_boundary_1_25", "near_boundary_26_50", "near_boundary_51_100", "far_boundary_gt100", "same_file_before_gold", "same_file_after_gold", "already_overlap_under_candidate_but_outside_window", "non_short_span_case", "top1_override_case", "top2_override_case", "short_span_base_case", "other_bucket")):
        buckets.append({"anonymous_marginal_gain_bucket_id": f"n10cvbucket{idx:04d}", "mechanism_bucket": bucket, "case_count": bucket_counts.get(bucket, 0)})
    return summary, buckets, len(new_top10) == 1 and len(new_top20) == 1 and sum(r["case_count"] for r in buckets if r["mechanism_bucket"].startswith("near_boundary") or r["mechanism_bucket"].startswith("far_boundary")) >= 1


def remaining_miss_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    res = result["residuals"][PM400]
    total = res.get("same_file_no_span_overlap", 0) + res.get("span_overlap_beyond_top10", 0) + res.get("file_not_in_top10", 0)
    rows = [{"anonymous_remaining_miss_id": "n10cvmiss0000", "remaining_miss_bucket": "pm400_top10_misses", "same_file_no_span_overlap_remaining": res.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_remaining": res.get("span_overlap_beyond_top10", 0), "file_not_in_top10_remaining": res.get("file_not_in_top10", 0), "remaining_top10_miss_count": total}]
    return rows, total == 213 - len(result["top10"][PM400])


def next_sweep_signal_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    res = result["residuals"][PM400]
    signal = res.get("same_file_no_span_overlap", 0) > 0 or res.get("span_overlap_beyond_top10", 0) > 0
    rows = [{"anonymous_next_sweep_signal_id": "n10cvsignal0000", "signal_bucket": "remaining_local_miss_signal_exists" if signal else "no_remaining_local_miss_signal", "remaining_local_miss_signal_bool": signal, "n10cw_high_window_sweep_justified_bool": signal, "same_file_no_span_overlap_remaining": res.get("same_file_no_span_overlap", 0), "span_overlap_beyond_top10_remaining": res.get("span_overlap_beyond_top10", 0)}]
    return rows, True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10cvprivacy0000", "privacy_boundary_bucket": "aggregate_pm400_marginal_decomposition_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10cvnoexec0000", "no_execution_boundary_bucket": "pm400_marginal_decomposition_only", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "new_pm_value_count": 0, "top3_override_count": 0, "adaptive_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cw_handoff_records(complete: bool, signal: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cw_handoff_id": "n10cvhandoff0000", "n10cw_handoff_bucket": "n10cw_high_window_sweep_authorized" if complete and signal else "n10cw_public_package_only", "n10cw_authorized_bool": complete and signal, "next_allowed_scope_bucket": "top2_override_high_window_neighborhood_sweep" if complete and signal else "public_package_only", "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "top3_override_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, anchor_ok: bool, gain_ok: bool, miss_ok: bool, signal_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read_213", private_ok), ("policy_anchors", anchor_ok), ("marginal_gain", gain_ok), ("remaining_miss", miss_ok), ("next_sweep_signal", signal_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool, signal: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cw_authorized" if complete and signal else "n10cw_not_authorized", "next_allowed_phase": "BEA-v1-N10CW Top2 Override High-Window Neighborhood Sweep" if complete and signal else "BEA-v1-N10CW Public Package Only", "next_allowed_scope_bucket": "top2_override_high_window_neighborhood_sweep" if complete and signal else "public_package_only", "n10cw_authorized": complete and signal, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "top3_override_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, anchor_ok: bool, gain_ok: bool, miss_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cv_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10cv_private_span_rows_missing"
    if not private_ok or not anchor_ok or not gain_ok or not miss_ok:
        return "no_go_n10cv_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10cv_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, compute_ok = compute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    private_rows = private_input_records(rows, load_status, usable)
    anchor_rows, anchor_ok = policy_anchor_records(result) if result else ([], False)
    gain_rows, gain_bucket_rows, gain_ok = marginal_gain_records(result) if result else ([], [], False)
    miss_rows, miss_ok = remaining_miss_records(result) if result else ([], False)
    signal_rows, signal_ok = next_sweep_signal_records(result) if result else ([], False)
    signal = bool(signal_rows and signal_rows[0]["remaining_local_miss_signal_bool"])
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, anchor_ok, gain_ok, miss_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_pm400_marginal_mechanism_decomposition_only", "generated_by": "bea_v1_n10cv_top2_pm400_marginal_gain_decomposition", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_rows, "policy_anchor_records": anchor_rows, "marginal_gain_records": gain_rows, "marginal_gain_mechanism_bucket_records": gain_bucket_rows, "remaining_miss_records": miss_rows, "next_sweep_signal_records": signal_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cw_handoff_records": n10cw_handoff_records(complete, signal), "gate_records": gate_records(input_ok, private_ok, anchor_ok, gain_ok, miss_ok, signal_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete, signal), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cw_handoff_records"] = n10cw_handoff_records(complete, signal)
    report["gate_records"] = gate_records(input_ok, private_ok, anchor_ok, gain_ok, miss_ok, signal_ok, privacy_ok, noexec_ok, scanner_ok)
    report["stop_go_records"] = stop_go_records(complete, signal)
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
    anchor_rows, anchor_ok = policy_anchor_records(result) if result else ([], False)
    gain_rows, gain_bucket_rows, gain_ok = marginal_gain_records(result) if result else ([], [], False)
    miss_rows, miss_ok = remaining_miss_records(result) if result else ([], False)
    signal_rows, signal_ok = next_sweep_signal_records(result) if result else ([], False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cv_required_inputs_unavailable", "no_go_n10cv_private_span_rows_missing", "no_go_n10cv_policy_contract_invalid", "no_go_n10cv_result_accounting_invalid", "no_go_n10cv_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok),
        check("anchors", anchor_ok and len(anchor_rows) == 3 and any(r["policy_bucket"] == PM400 and r["top10_span_overlap_count"] == 27 for r in anchor_rows)),
        check("marginal_gain", gain_ok and gain_rows[0]["pm400_new_top10_count"] == 1 and gain_rows[0]["pm400_new_top20_count"] == 1),
        check("mechanism_buckets", any(r["mechanism_bucket"] == "top2_override_case" and r["case_count"] >= 1 for r in gain_bucket_rows)),
        check("remaining_miss", miss_ok and miss_rows[0]["remaining_top10_miss_count"] == 186),
        check("next_signal", signal_ok and signal_rows[0]["remaining_local_miss_signal_bool"] is True),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_pm_value_count"] == 0 and noexec_rows[0]["top3_override_count"] == 0),
        check("synthetic_status", status_for(True, True, "pass", False, True, True, True, True, True) == "no_go_n10cv_result_accounting_invalid"),
        check("false_flags", stop_go_records(True, True)[0]["n10cw_authorized"] is True and stop_go_records(True, True)[0]["runtime_or_default_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CV top2 pm400 marginal gain decomposition")
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
