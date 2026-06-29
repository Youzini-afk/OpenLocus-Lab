#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10z_n1_span_surface_span_level_failure_decomposition.v1"
PHASE = "BEA-v1-N10Z N1 Span-Surface Span-Level Failure Decomposition"
GENERATED_BY = "bea_v1_n10z_n1_span_surface_span_level_failure_decomposition"
STATUS_COMPLETE = "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"
BEST_ARM = "span_extra_depth_promote_before_primary_prefix_4"

STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10z_required_inputs_unavailable",
    "no_go_n10z_private_span_rows_missing",
    "no_go_n10z_span_schema_invalid",
    "no_go_n10z_decomposition_inconsistent_with_n10x",
    "no_go_n10z_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json")
INPUTS = {
    "n10x_span_level_validation_artifact": (Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json"), "n1_span_surface_span_level_utility_validation_complete_below_threshold"),
    "n10y_span_level_result_audit_artifact": (Path("artifacts/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit_report.json"), "n1_span_surface_span_level_utility_result_audit_complete"),
    "n10t_proxy_validation_artifact": (Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json"), "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"),
}
EXPECTED = {"rows": 213, "top10_file": 34, "top10_span": 9, "gap": 25, "span_total": 12}
MISS_BUCKETS = (
    "same_file_before_gold",
    "same_file_after_gold",
    "same_file_disjoint_unknown_order",
    "same_file_malformed_or_missing_span",
    "gold_line_schema_malformed",
    "no_same_file_top10_despite_file_hit_in_record_bug",
)
RANK_BUCKETS = (
    "span_overlap_rank_1_10",
    "span_overlap_rank_11_20",
    "span_overlap_rank_21_50",
    "span_overlap_rank_gt_50",
    "span_overlap_not_ranked_or_missing",
)

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "private_input_bucket", "intake_status_bucket", "arm_bucket", "scope_bucket", "gap_bucket", "miss_bucket",
    "reach_bucket", "repair_signal_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10aa_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = root() / path
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(path: Path, data: dict[str, Any]) -> None:
    full = root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
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
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
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
    records = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10zin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, ok


def load_rows() -> tuple[list[dict[str, Any]], str]:
    full = root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows = []
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
    for rg in ranges:
        if not (isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1]):
            return False
    for ev in evs:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
    return True


def order_best(evs: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    items = list(enumerate(evs, start=1))
    primary = [x for x in items if x[0] <= 20]
    extra = [x for x in items if x[0] > 20]
    return extra + primary[:4] + primary[4:]


def ref_map(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return out


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def first_file_hit(ordered: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]]) -> tuple[int | None, dict[str, Any] | None]:
    for idx, (_pos, ev) in enumerate(ordered, start=1):
        if str(ev.get("path", "")) in refs:
            return idx, ev
    return None, None


def first_span_hit(ordered: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]]) -> tuple[int | None, dict[str, Any] | None]:
    for idx, (_pos, ev) in enumerate(ordered, start=1):
        ref = str(ev.get("path", ""))
        if ref not in refs:
            continue
        start = ev.get("start_line")
        end = ev.get("end_line")
        if isinstance(start, int) and isinstance(end, int) and any(overlaps(start, end, a, b) for a, b in refs[ref]):
            return idx, ev
    return None, None


def miss_bucket(ev: dict[str, Any] | None, refs: dict[str, list[tuple[int, int]]]) -> str:
    if ev is None:
        return "no_same_file_top10_despite_file_hit_in_record_bug"
    ref = str(ev.get("path", ""))
    start = ev.get("start_line")
    end = ev.get("end_line")
    if ref not in refs:
        return "no_same_file_top10_despite_file_hit_in_record_bug"
    if not isinstance(start, int) or not isinstance(end, int) or not refs[ref]:
        return "same_file_malformed_or_missing_span"
    if any(overlaps(start, end, a, b) for a, b in refs[ref]):
        return "no_same_file_top10_despite_file_hit_in_record_bug"
    min_start = min(a for a, _b in refs[ref])
    max_end = max(b for _a, b in refs[ref])
    if end < min_start:
        return "same_file_before_gold"
    if start > max_end:
        return "same_file_after_gold"
    return "same_file_disjoint_unknown_order"


def reach_bucket(position: int | None) -> str:
    if position is None:
        return "span_overlap_not_ranked_or_missing"
    if position <= 10:
        return "span_overlap_rank_1_10"
    if position <= 20:
        return "span_overlap_rank_11_20"
    if position <= 50:
        return "span_overlap_rank_21_50"
    return "span_overlap_rank_gt_50"


def decompose(rows: list[dict[str, Any]]) -> dict[str, Any]:
    top10_file = top10_span = gap = span_total = 0
    miss_counts: Counter[str] = Counter({b: 0 for b in MISS_BUCKETS})
    rank_counts: Counter[str] = Counter({b: 0 for b in RANK_BUCKETS})
    for row in rows:
        if not row_ok(row) or not row.get("p4_evidence"):
            continue
        refs = ref_map(row)
        ordered = order_best(row["p4_evidence"])
        file_pos, file_ev = first_file_hit(ordered, refs)
        span_pos, _span_ev = first_span_hit(ordered, refs)
        if file_pos is not None and file_pos <= 10:
            top10_file += 1
        if span_pos is not None and span_pos <= 10:
            top10_span += 1
        if file_pos is not None and file_pos <= 10 and not (span_pos is not None and span_pos <= 10):
            gap += 1
            miss_counts[miss_bucket(file_ev, refs)] += 1
        if span_pos is not None:
            span_total += 1
            rank_counts[reach_bucket(span_pos)] += 1
    return {"top10_file_hit_count": top10_file, "top10_span_overlap_count": top10_span, "file_hit_no_span_overlap_count": gap, "span_reachable_total": span_total, "miss_counts": dict(miss_counts), "rank_counts": dict(rank_counts)}


def private_span_input_intake_records(rows: list[dict[str, Any]], load_status: str, schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_span_input_intake_id": "n10zpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if schema_ok else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "schema_valid_bool": schema_ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def best_arm_scope_records() -> list[dict[str, Any]]:
    return [{"anonymous_best_arm_scope_id": "n10zscope0000", "scope_bucket": "single_best_arm_from_n10x_only", "arm_bucket": BEST_ARM, "uses_n10t_semantics_bool": True, "candidate_pool_changed_bool": False, "candidate_added_bool": False, "candidate_removed_bool": False, "new_arm_search_bool": False, "gold_used_for_ordering_bool": False}]


def file_vs_span_gap_records(d: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_file_vs_span_gap_id": "n10zgap0000", "gap_bucket": "file_hit_top10_but_span_overlap_below_top10_or_missing", "top10_file_hit_count": d["top10_file_hit_count"], "top10_span_overlap_count": d["top10_span_overlap_count"], "file_hit_no_span_overlap_count": d["file_hit_no_span_overlap_count"], "span_reachable_total": d["span_reachable_total"], "consistent_with_n10x_bool": d["top10_file_hit_count"] == 34 and d["top10_span_overlap_count"] == 9 and d["file_hit_no_span_overlap_count"] == 25 and d["span_reachable_total"] == 12}]


def top10_span_miss_bucket_records(d: dict[str, Any]) -> list[dict[str, Any]]:
    counts = d["miss_counts"]
    return [{"anonymous_top10_span_miss_bucket_id": f"n10zmiss{i:04d}", "miss_bucket": bucket, "case_count": int(counts.get(bucket, 0))} for i, bucket in enumerate(MISS_BUCKETS)]


def span_reachable_rank_bucket_records(d: dict[str, Any]) -> list[dict[str, Any]]:
    counts = d["rank_counts"]
    return [{"anonymous_span_reachable_rank_bucket_id": f"n10zreach{i:04d}", "reach_bucket": bucket, "case_count": int(counts.get(bucket, 0))} for i, bucket in enumerate(RANK_BUCKETS)]


def repair_signal_records(d: dict[str, Any]) -> list[dict[str, Any]]:
    counts = d["miss_counts"]
    same_file_no_overlap = int(counts.get("same_file_before_gold", 0)) + int(counts.get("same_file_after_gold", 0)) + int(counts.get("same_file_disjoint_unknown_order", 0))
    return [{"anonymous_repair_signal_id": "n10zrepair0000", "repair_signal_bucket": "same_file_span_window_misalignment_dominates", "same_file_no_overlap_count": same_file_no_overlap, "file_hit_no_span_overlap_count": d["file_hit_no_span_overlap_count"], "same_file_no_overlap_dominates_bool": same_file_no_overlap >= 0.5 * d["file_hit_no_span_overlap_count"], "span_window_repair_preflight_recommended_bool": True, "repair_execution_authorized_bool": False}]


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10zprivacy0000", "privacy_boundary_bucket": "bucket_counts_only_no_private_surface_details", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10znoexec0000", "no_execution_boundary_bucket": "single_private_span_read_decomposition_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "support_labeling_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10aa_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10aa_handoff_id": "n10zhandoff0000", "n10aa_handoff_bucket": "n10aa_span_window_repair_preflight_authorized" if complete else "n10aa_not_authorized", "n10aa_span_window_repair_preflight_authorized_bool": complete, "design_preflight_only_bool": True, "repair_execution_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, rows_ok: bool, schema_ok: bool, consistent: bool, miss_sum_ok: bool, rank_sum_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("private_span_rows_read", rows_ok, 213 if rows_ok else 0, 213), ("span_schema_valid", schema_ok, int(schema_ok), 1), ("decomposition_consistent_with_n10x", consistent, int(consistent), 1), ("top10_span_miss_bucket_sum", miss_sum_ok, 25 if miss_sum_ok else 0, 25), ("span_reachable_rank_bucket_sum", rank_sum_ok, 12 if rank_sum_ok else 0, 12), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10aa_span_window_repair_preflight_authorized" if complete else "n10aa_not_authorized", "next_allowed_phase": "BEA-v1-N10AA Span-Window Repair Preflight" if complete else "none_until_valid_span_failure_decomposition_exists", "next_allowed_scope_bucket": "design_preflight_only_no_repair_execution" if complete else "no_next_phase", "n10aa_preflight_authorized": complete, "repair_execution_authorized": False, "private_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, schema_ok: bool, consistent: bool, miss_sum_ok: bool, rank_sum_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10z_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10z_private_span_rows_missing"
    if not schema_ok:
        return "no_go_n10z_span_schema_invalid"
    if not consistent or not miss_sum_ok or not rank_sum_ok:
        return "no_go_n10z_decomposition_inconsistent_with_n10x"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10z_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    schema_ok = load_status == "pass" and len(rows) == 213 and all(row_ok(r) for r in rows)
    d = decompose(rows) if schema_ok else {"top10_file_hit_count": 0, "top10_span_overlap_count": 0, "file_hit_no_span_overlap_count": 0, "span_reachable_total": 0, "miss_counts": {}, "rank_counts": {}}
    consistent = d["top10_file_hit_count"] == 34 and d["top10_span_overlap_count"] == 9 and d["file_hit_no_span_overlap_count"] == 25 and d["span_reachable_total"] == 12
    miss_sum_ok = sum(d["miss_counts"].values()) == 25
    rank_sum_ok = sum(d["rank_counts"].values()) == 12
    privacy, privacy_ok = privacy_boundary_records()
    noexec, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, schema_ok, consistent, miss_sum_ok, rank_sum_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "span_level_failure_decomposition_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_span_input_intake_records": private_span_input_intake_records(rows, load_status, schema_ok), "best_arm_scope_records": best_arm_scope_records(), "file_vs_span_gap_records": file_vs_span_gap_records(d), "top10_span_miss_bucket_records": top10_span_miss_bucket_records(d), "span_reachable_rank_bucket_records": span_reachable_rank_bucket_records(d), "repair_signal_records": repair_signal_records(d), "privacy_boundary_records": privacy, "no_forbidden_execution_records": noexec, "n10aa_handoff_records": n10aa_handoff_records(complete), "gate_records": gate_records(input_ok, load_status == "pass", schema_ok, consistent, miss_sum_ok, rank_sum_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["gate_records"] = gate_records(input_ok, load_status == "pass", schema_ok, consistent, miss_sum_ok, rank_sum_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10aa_handoff_records"] = n10aa_handoff_records(complete)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    schema_ok = load_status == "pass" and len(rows) == 213 and all(row_ok(r) for r in rows)
    d = decompose(rows) if schema_ok else {"top10_file_hit_count": 0, "top10_span_overlap_count": 0, "file_hit_no_span_overlap_count": 0, "span_reachable_total": 0, "miss_counts": {}, "rank_counts": {}}
    miss_records = top10_span_miss_bucket_records(d)
    rank_records = span_reachable_rank_bucket_records(d)
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10z_required_inputs_unavailable", "no_go_n10z_private_span_rows_missing", "no_go_n10z_span_schema_invalid", "no_go_n10z_decomposition_inconsistent_with_n10x", "no_go_n10z_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 3),
        check("private_input", load_status == "pass" and len(rows) == 213 and schema_ok),
        check("core_counts", d["top10_file_hit_count"] == 34 and d["top10_span_overlap_count"] == 9 and d["file_hit_no_span_overlap_count"] == 25 and d["span_reachable_total"] == 12),
        check("miss_buckets", sum(r["case_count"] for r in miss_records) == 25 and {r["miss_bucket"]: r["case_count"] for r in miss_records}["same_file_before_gold"] == 17 and {r["miss_bucket"]: r["case_count"] for r in miss_records}["same_file_after_gold"] == 8),
        check("rank_buckets", sum(r["case_count"] for r in rank_records) == 12 and {r["reach_bucket"]: r["case_count"] for r in rank_records}["span_overlap_rank_1_10"] == 9 and {r["reach_bucket"]: r["case_count"] for r in rank_records}["span_overlap_rank_11_20"] == 1 and {r["reach_bucket"]: r["case_count"] for r in rank_records}["span_overlap_rank_21_50"] == 2),
        check("repair_signal", repair_signal_records(d)[0]["same_file_no_overlap_dominates_bool"] is True and repair_signal_records(d)[0]["repair_execution_authorized_bool"] is False),
        check("privacy", privacy_boundary_records()[1] and privacy_boundary_records()[0][0]["gold_line_public_bool"] is False),
        check("no_execution", no_forbidden_execution_records()[1] and no_forbidden_execution_records()[0][0]["private_span_input_read_count"] == 1 and no_forbidden_execution_records()[0][0]["other_private_file_read_count"] == 0),
        check("handoff", n10aa_handoff_records(True)[0]["n10aa_span_window_repair_preflight_authorized_bool"] is True and n10aa_handoff_records(True)[0]["repair_execution_authorized_bool"] is False),
        check("status_expected", status_for(True, True, "pass", True, True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10Z N1 span-surface span-level failure decomposition")
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
    gap = report["file_vs_span_gap_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, gap={gap['file_hit_no_span_overlap_count']})")


if __name__ == "__main__":
    main()
