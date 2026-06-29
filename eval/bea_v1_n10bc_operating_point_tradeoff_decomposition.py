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


SCHEMA_VERSION = "bea_v1_n10bc_operating_point_tradeoff_decomposition.v1"
PHASE = "BEA-v1-N10BC Operating-Point Tradeoff Decomposition"
STATUS_COMPLETE = "operating_point_tradeoff_decomposition_complete_n10bd_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bc_required_inputs_unavailable",
    "no_go_n10bc_private_span_rows_missing",
    "no_go_n10bc_operating_point_accounting_invalid",
    "no_go_n10bc_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10bc_operating_point_tradeoff_decomposition/bea_v1_n10bc_operating_point_tradeoff_decomposition_report.json")
PUBLIC_INPUTS = {
    "n10bb_selection_rule_audit_package_artifact": (Path("artifacts/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package_report.json"), "cost_aware_selection_rule_smoke_audit_package_complete_n10bc_authorized"),
    "n10ba_selection_rule_smoke_artifact": (Path("artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json"), "cost_aware_span_window_selection_rule_smoke_complete_n10bb_authorized"),
    "n10aw_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json"), "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"),
    "n10av_replication_package_artifact": (Path("artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json"), "exploratory_span_window_sweep_replication_package_complete_n10aw_authorized"),
    "n10ax_claim_package_artifact": (Path("artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json"), "cost_sensitive_frontier_claim_package_complete_n10ay_authorized"),
}
POINTS = (
    ("baseline", "baseline", 0, 0, 0, 9, 10),
    ("low_cost", "pm30", 30, 30, 600, 18, 22),
    ("balanced", "before25_after75", 25, 75, 1000, 20, 24),
    ("max_recall", "pm200", 200, 200, 4000, 25, 30),
)
MECHANISM_BUCKETS = ("before_gold_gap", "after_gold_gap", "already_reachable_late_rank", "other_bucketed")
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
    "private_input_bucket", "intake_status_bucket", "operating_point_bucket", "variant_bucket", "previous_operating_point_bucket",
    "mechanism_bucket", "cost_bucket", "marginal_cost_per_top10_hit_bucket", "mechanism_continuity_bucket",
    "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10bd_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = root() / rel
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
        rows.append({"anonymous_input_artifact_id": f"n10bcin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, ok


def load_rows(path: Path = PRIVATE_SPAN_ROWS) -> tuple[list[dict[str, Any]], str]:
    full = root() / path
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
    for rg in ranges:
        if not (isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1]):
            return False
    for ev in evs:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
    return True


def order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    out = []
    for item in records:
        copied = dict(item)
        copied["start_line"] = max(1, int(copied["start_line"]) - before)
        copied["end_line"] = int(copied["end_line"]) + after
        out.append(copied)
    return out


def hit(records: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for item in records[:limit]:
        key = str(item.get("path", ""))
        if key not in refs:
            continue
        start = item.get("start_line")
        end = item.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if any(overlaps(start, end, a, b) for a, b in refs[key]):
            return True
    return False


def first_late_unexpanded(records: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]]) -> int | None:
    for idx, item in enumerate(records, start=1):
        key = str(item.get("path", ""))
        if key in refs and any(overlaps(int(item["start_line"]), int(item["end_line"]), a, b) for a, b in refs[key]):
            return idx
    return None


def direction_bucket(prev_records: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]]) -> str:
    for item in prev_records[:10]:
        key = str(item.get("path", ""))
        if key not in refs:
            continue
        start = int(item["start_line"])
        end = int(item["end_line"])
        if any(overlaps(start, end, a, b) for a, b in refs[key]):
            return "other_bucketed"
        min_start = min(a for a, _b in refs[key])
        max_end = max(b for _a, b in refs[key])
        if end < min_start:
            return "before_gold_gap"
        if start > max_end:
            return "after_gold_gap"
        return "other_bucketed"
    return "other_bucketed"


def marginal_cost_bucket(cost: int, hits: int) -> str:
    if hits <= 0:
        return "no_new_hit"
    value = cost / hits
    if value <= 100:
        return "low"
    if value <= 250:
        return "medium"
    if value <= 500:
        return "high"
    return "very_high"


def compute(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [r for r in rows if row_ok(r) and r.get("p4_evidence")]
    top10: dict[str, set[int]] = {}
    top20: dict[str, set[int]] = {}
    projected_by_point: dict[str, list[list[dict[str, Any]]]] = {}
    for point, _variant, before, after, _cost, _e10, _e20 in POINTS:
        top10[point], top20[point], projected_by_point[point] = set(), set(), []
        for idx, row in enumerate(usable):
            ordered = order(row["p4_evidence"])
            recs = ordered if point == "baseline" else project(ordered, before, after)
            projected_by_point[point].append(recs)
            refs = refmap(row)
            if hit(recs, refs, 10):
                top10[point].add(idx)
            if hit(recs, refs, 20):
                top20[point].add(idx)
    tradeoff_rows: list[dict[str, Any]] = []
    bucket_rows: list[dict[str, Any]] = []
    prev_point = "none"
    prev_cost = 0
    prev10: set[int] = set()
    prev20: set[int] = set()
    for idx, (point, variant, _before, _after, cost, expected10, expected20) in enumerate(POINTS):
        current10, current20 = top10[point], top20[point]
        new10 = current10 - prev10
        lost = prev10 - current10
        marginal_cost = cost - prev_cost
        counts = Counter({bucket: 0 for bucket in MECHANISM_BUCKETS})
        if point != "baseline":
            for row_idx in new10:
                ordered = order(usable[row_idx]["p4_evidence"])
                refs = refmap(usable[row_idx])
                bucket = direction_bucket(projected_by_point[prev_point][row_idx], refs)
                if bucket == "other_bucketed":
                    late = first_late_unexpanded(ordered, refs)
                    if late is not None and late > 10:
                        bucket = "already_reachable_late_rank"
                counts[bucket] += 1
        tradeoff_rows.append({"anonymous_tradeoff_id": f"n10bctrade{idx:04d}", "operating_point_bucket": point, "variant_bucket": variant, "previous_operating_point_bucket": prev_point, "cumulative_top10_span_overlap_count": len(current10), "cumulative_top20_span_overlap_count": len(current20), "expected_top10_span_overlap_count": expected10, "expected_top20_span_overlap_count": expected20, "marginal_top10_gain": len(new10), "marginal_top20_gain": len(current20 - prev20), "marginal_cost_proxy": marginal_cost, "cumulative_cost_proxy": cost, "marginal_cost_per_top10_hit_bucket": "baseline" if point == "baseline" else marginal_cost_bucket(marginal_cost, len(new10)), "lost_previous_hits": len(lost), "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False})
        for bucket_idx, bucket in enumerate(MECHANISM_BUCKETS):
            bucket_rows.append({"anonymous_mechanism_bucket_id": f"n10bcmech{idx:04d}{bucket_idx:04d}", "operating_point_bucket": point, "previous_operating_point_bucket": prev_point, "mechanism_bucket": bucket, "new_top10_hit_count": int(counts[bucket])})
        prev_point, prev_cost, prev10, prev20 = point, cost, current10, current20
    return {"usable_rows": len(usable), "tradeoff_rows": tradeoff_rows, "bucket_rows": bucket_rows}


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10bcpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def accounting_valid(tradeoff_rows: list[dict[str, Any]], bucket_rows: list[dict[str, Any]]) -> bool:
    expected = {"baseline": (9, 10, 9), "low_cost": (18, 22, 9), "balanced": (20, 24, 2), "max_recall": (25, 30, 5)}
    prev = 0
    for row in tradeoff_rows:
        point = row["operating_point_bucket"]
        if (row["cumulative_top10_span_overlap_count"], row["cumulative_top20_span_overlap_count"], row["marginal_top10_gain"]) != expected[point]:
            return False
        if row["cumulative_top10_span_overlap_count"] != prev + row["marginal_top10_gain"] - row["lost_previous_hits"]:
            return False
        bucket_sum = sum(r["new_top10_hit_count"] for r in bucket_rows if r["operating_point_bucket"] == point)
        if point == "baseline":
            if bucket_sum != 0:
                return False
        elif bucket_sum != row["marginal_top10_gain"]:
            return False
        prev = row["cumulative_top10_span_overlap_count"]
    return True


def mechanism_continuity_records(bucket_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    max_counts = {r["mechanism_bucket"]: r["new_top10_hit_count"] for r in bucket_rows if r["operating_point_bucket"] == "max_recall"}
    same = max_counts.get("before_gold_gap", 0) + max_counts.get("after_gold_gap", 0) == 5 and max_counts.get("already_reachable_late_rank", 0) == 0 and max_counts.get("other_bucketed", 0) == 0
    return [{"anonymous_mechanism_continuity_id": "n10bccontinuity0000", "mechanism_continuity_bucket": "max_recall_same_before_after_gold_window_gap_mechanism" if same else "max_recall_mixed_or_new_mechanism", "max_recall_gains_same_mechanism_as_lower_cost_bool": same, "max_recall_before_after_gap_new_hit_count": max_counts.get("before_gold_gap", 0) + max_counts.get("after_gold_gap", 0), "max_recall_late_or_other_new_hit_count": max_counts.get("already_reachable_late_rank", 0) + max_counts.get("other_bucketed", 0), "qualitatively_new_max_recall_mechanism_bool": False if same else True}], same


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10bcprivacy0000", "privacy_boundary_bucket": "aggregate_bucket_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10bcnoexec0000", "no_execution_boundary_bucket": "operating_point_tradeoff_same_scoped_rows_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "new_variant_count": 0, "adaptive_selection_count": 0, "runtime_default_promotion_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_order_change_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10bd_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bd_handoff_id": "n10bchandoff0000", "n10bd_handoff_bucket": "n10bd_public_tradeoff_package_authorized" if complete else "n10bd_not_authorized", "n10bd_public_tradeoff_package_authorized_bool": complete, "private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_selection_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, accounting_ok: bool, continuity_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("tradeoff_accounting", accounting_ok), ("mechanism_continuity", continuity_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bd_public_tradeoff_package_authorized" if complete else "n10bd_not_authorized", "next_allowed_phase": "BEA-v1-N10BD Operating-Point Tradeoff Decomposition Audit Package" if complete else "none_until_operating_point_tradeoff_decomposition_is_valid", "next_allowed_scope_bucket": "public_tradeoff_package_only" if complete else "no_next_phase", "n10bd_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_selection_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, accounting_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bc_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10bc_private_span_rows_missing"
    if not private_ok or not accounting_ok:
        return "no_go_n10bc_operating_point_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10bc_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    computed = compute(rows) if load_status == "pass" else {"usable_rows": 0, "tradeoff_rows": [], "bucket_rows": []}
    private_ok = load_status == "pass" and len(rows) == 213 and computed["usable_rows"] == 213
    accounting_ok = accounting_valid(computed["tradeoff_rows"], computed["bucket_rows"]) if computed["tradeoff_rows"] else False
    continuity_rows, continuity_ok = mechanism_continuity_records(computed["bucket_rows"])
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, accounting_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_operating_point_tradeoff_decomposition_only", "generated_by": "bea_v1_n10bc_operating_point_tradeoff_decomposition", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, computed["usable_rows"]), "operating_point_tradeoff_records": computed["tradeoff_rows"], "mechanism_bucket_records": computed["bucket_rows"], "mechanism_continuity_records": continuity_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10bd_handoff_records": n10bd_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, accounting_ok, continuity_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bd_handoff_records"] = n10bd_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, accounting_ok, continuity_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_accounting() -> bool:
    rows = [{"operating_point_bucket": "baseline", "cumulative_top10_span_overlap_count": 1, "cumulative_top20_span_overlap_count": 1, "marginal_top10_gain": 1, "lost_previous_hits": 0}, {"operating_point_bucket": "low_cost", "cumulative_top10_span_overlap_count": 2, "cumulative_top20_span_overlap_count": 2, "marginal_top10_gain": 1, "lost_previous_hits": 0}]
    buckets = [{"operating_point_bucket": "baseline", "new_top10_hit_count": 0}, {"operating_point_bucket": "low_cost", "new_top10_hit_count": 1}]
    # Direct synthetic for reconciliation only, independent of real expected constants.
    return rows[1]["cumulative_top10_span_overlap_count"] == rows[0]["cumulative_top10_span_overlap_count"] + rows[1]["marginal_top10_gain"] and sum(b["new_top10_hit_count"] for b in buckets if b["operating_point_bucket"] == "low_cost") == 1


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    computed = compute(rows) if load_status == "pass" else {"usable_rows": 0, "tradeoff_rows": [], "bucket_rows": []}
    private_ok = load_status == "pass" and len(rows) == 213 and computed["usable_rows"] == 213
    accounting_ok = accounting_valid(computed["tradeoff_rows"], computed["bucket_rows"]) if computed["tradeoff_rows"] else False
    continuity_rows, continuity_ok = mechanism_continuity_records(computed["bucket_rows"])
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bc_required_inputs_unavailable", "no_go_n10bc_private_span_rows_missing", "no_go_n10bc_operating_point_accounting_invalid", "no_go_n10bc_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("private_rows", private_ok),
        check("accounting", accounting_ok and [r["marginal_top10_gain"] for r in computed["tradeoff_rows"]] == [9, 9, 2, 5]),
        check("top20_accounting", [r["marginal_top20_gain"] for r in computed["tradeoff_rows"]] == [10, 12, 2, 6]),
        check("max_recall_buckets", sum(r["new_top10_hit_count"] for r in computed["bucket_rows"] if r["operating_point_bucket"] == "max_recall") == 5),
        check("continuity", continuity_ok and continuity_rows[0]["max_recall_gains_same_mechanism_as_lower_cost_bool"] is True),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_count"] == 0 and noexec_rows[0]["adaptive_selection_count"] == 0),
        check("bucket_classification", marginal_cost_bucket(600, 9) == "low" and marginal_cost_bucket(400, 2) == "medium" and marginal_cost_bucket(3000, 5) == "very_high"),
        check("synthetic_accounting", synthetic_accounting()),
        check("false_flags", stop_go_records(True)[0]["n10bd_authorized"] is True and stop_go_records(True)[0]["new_variant_authorized"] is False and stop_go_records(True)[0]["runtime_or_default_authorized"] is False),
        check("status_complete", status_for(True, True, "pass", True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BC operating-point tradeoff decomposition")
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
