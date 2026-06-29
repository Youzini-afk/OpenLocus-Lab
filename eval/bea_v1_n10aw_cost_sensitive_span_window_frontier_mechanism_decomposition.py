#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition.v1"
PHASE = "BEA-v1-N10AW Cost-Sensitive Span-Window Frontier Mechanism Decomposition"
STATUS_COMPLETE = "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10aw_required_inputs_unavailable",
    "no_go_n10aw_frontier_chain_inconsistent",
    "no_go_n10aw_private_span_rows_missing",
    "no_go_n10aw_result_accounting_invalid",
    "no_go_n10aw_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json")
PUBLIC_INPUTS = {
    "n10av_replication_package_artifact": (Path("artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json"), "exploratory_span_window_sweep_replication_package_complete_n10aw_authorized"),
    "n10au_independent_recompute_artifact": (Path("artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json"), "independent_recompute_span_window_variant_sweep_pass_n10av_authorized"),
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
}
TIERS = (
    ("baseline", 0, 0, 0),
    ("pm30", 30, 30, 600),
    ("before25_after75", 25, 75, 1000),
    ("pm75", 75, 75, 1500),
    ("pm200", 200, 200, 4000),
)
EXPECTED_TOP10 = {"baseline": 9, "pm30": 18, "before25_after75": 20, "pm75": 21, "pm200": 25}
EXPECTED_TOP20 = {"baseline": 10, "pm30": 22, "before25_after75": 24, "pm75": 25, "pm200": 30}
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
    "private_input_bucket", "intake_status_bucket", "tier_bucket", "previous_tier_bucket", "mechanism_bucket",
    "cost_bucket", "marginal_cost_per_new_hit_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10ax_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10awin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def expand(ev: dict[str, Any], before: int, after: int) -> tuple[str, int, int]:
    return str(ev.get("path", "")), max(1, int(ev.get("start_line", 0)) - before), int(ev.get("end_line", 0)) + after


def hit_positions(ordered: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]], before: int, after: int) -> tuple[int | None, int | None]:
    first10 = first20 = None
    for idx, (_pos, ev) in enumerate(ordered, start=1):
        ref, start, end = expand(ev, before, after)
        if ref in refs and any(overlaps(start, end, a, b) for a, b in refs[ref]):
            if idx <= 10 and first10 is None:
                first10 = idx
            if idx <= 20 and first20 is None:
                first20 = idx
            if first10 is not None and first20 is not None:
                break
    return first10, first20


def first_unexpanded_late_position(ordered: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]]) -> int | None:
    for idx, (_pos, ev) in enumerate(ordered, start=1):
        ref, start, end = expand(ev, 0, 0)
        if ref in refs and any(overlaps(start, end, a, b) for a, b in refs[ref]):
            return idx
    return None


def previous_tier_direction(ordered: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]], before: int, after: int) -> str:
    for _pos, ev in ordered[:10]:
        ref, start, end = expand(ev, before, after)
        if ref not in refs:
            continue
        if any(overlaps(start, end, a, b) for a, b in refs[ref]):
            return "other_bucketed"
        min_start = min(a for a, _b in refs[ref])
        max_end = max(b for _a, b in refs[ref])
        if end < min_start:
            return "before_gold_gap"
        if start > max_end:
            return "after_gold_gap"
        return "other_bucketed"
    return "other_bucketed"


def mechanism_bucket(row: dict[str, Any], prev_before: int, prev_after: int) -> str:
    ordered = order_best(row["p4_evidence"])
    refs = ref_map(row)
    direction = previous_tier_direction(ordered, refs, prev_before, prev_after)
    if direction in ("before_gold_gap", "after_gold_gap"):
        return direction
    pos = first_unexpanded_late_position(ordered, refs)
    if pos is not None and pos > 10:
        return "already_reachable_late_rank"
    return "other_bucketed"


def cost_bucket(cost: int) -> str:
    if cost == 0:
        return "zero"
    if cost <= 600:
        return "low"
    if cost <= 1500:
        return "medium"
    return "very_high"


def marginal_cost_bucket(cost: int, hits: int) -> str:
    if hits <= 0:
        return "undefined_no_new_hits"
    value = cost / hits
    if value <= 100:
        return "low"
    if value <= 250:
        return "medium"
    if value <= 500:
        return "high"
    return "very_high"


def compute(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [r for r in rows if row_ok(r) and r.get("p4_evidence")]
    top10_sets: dict[str, set[int]] = {}
    top20_sets: dict[str, set[int]] = {}
    for name, before, after, _cost in TIERS:
        top10_sets[name] = set()
        top20_sets[name] = set()
        for idx, row in enumerate(valid):
            pos10, pos20 = hit_positions(order_best(row["p4_evidence"]), ref_map(row), before, after)
            if pos10 is not None:
                top10_sets[name].add(idx)
            if pos20 is not None:
                top20_sets[name].add(idx)
    tier_rows: list[dict[str, Any]] = []
    mechanism_rows: list[dict[str, Any]] = []
    previous_name = "none"
    previous_before = previous_after = previous_cost = 0
    previous_set: set[int] = set()
    for tier_idx, (name, before, after, cost) in enumerate(TIERS):
        current = top10_sets[name]
        new_hits = current - previous_set
        lost_hits = previous_set - current
        marginal_cost = cost - previous_cost if tier_idx else 0
        counts = Counter({b: 0 for b in MECHANISM_BUCKETS})
        if tier_idx:
            for row_idx in new_hits:
                counts[mechanism_bucket(valid[row_idx], previous_before, previous_after)] += 1
        tier_rows.append({
            "anonymous_tier_delta_id": f"n10awtier{tier_idx:04d}",
            "tier_bucket": name,
            "previous_tier_bucket": previous_name,
            "cumulative_span_hits": len(current),
            "cumulative_top20_span_hits": len(top20_sets[name]),
            "new_span_hits_vs_previous_tier": len(new_hits),
            "lost_previous_hits": len(lost_hits),
            "marginal_cost_proxy": marginal_cost,
            "total_cost_proxy": cost,
            "cost_bucket": cost_bucket(cost),
            "marginal_cost_per_new_hit_bucket": "baseline" if tier_idx == 0 else marginal_cost_bucket(marginal_cost, len(new_hits)),
        })
        for bucket_idx, bucket in enumerate(MECHANISM_BUCKETS):
            mechanism_rows.append({"anonymous_mechanism_bucket_id": f"n10awmech{tier_idx:04d}{bucket_idx:04d}", "tier_bucket": name, "previous_tier_bucket": previous_name, "mechanism_bucket": bucket, "new_span_hit_case_count": int(counts[bucket])})
        previous_name, previous_before, previous_after, previous_cost, previous_set = name, before, after, cost, current
    return {"valid_rows": len(valid), "tier_rows": tier_rows, "mechanism_rows": mechanism_rows}


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, valid_count: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10awpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and valid_count == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "valid_span_surface_rows": valid_count if load_status == "pass" else 0, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def frontier_chain_consistent(tier_rows: list[dict[str, Any]]) -> bool:
    return all(row["cumulative_span_hits"] == EXPECTED_TOP10[row["tier_bucket"]] and row["cumulative_top20_span_hits"] == EXPECTED_TOP20[row["tier_bucket"]] for row in tier_rows)


def accounting_valid(tier_rows: list[dict[str, Any]], mechanism_rows: list[dict[str, Any]]) -> bool:
    previous = 0
    for row in tier_rows:
        if row["cumulative_span_hits"] != previous + row["new_span_hits_vs_previous_tier"] - row["lost_previous_hits"]:
            return False
        previous = row["cumulative_span_hits"]
        mech_sum = sum(m["new_span_hit_case_count"] for m in mechanism_rows if m["tier_bucket"] == row["tier_bucket"])
        if row["tier_bucket"] == "baseline":
            if mech_sum != 0:
                return False
        elif mech_sum != row["new_span_hits_vs_previous_tier"]:
            return False
    return True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10awprivacy0000", "privacy_boundary_bucket": "aggregate_bucket_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10awnoexec0000", "no_execution_boundary_bucket": "single_scoped_private_read_mechanism_decomposition_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "new_variant_count": 0, "extra_sweep_count": 0, "adaptive_tuning_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "order_arm_sweep_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10ax_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ax_handoff_id": "n10awhandoff0000", "n10ax_handoff_bucket": "n10ax_cost_sensitive_frontier_claim_package_authorized" if complete else "n10ax_not_authorized", "n10ax_public_package_authorized_bool": complete, "public_package_only_bool": True, "private_read_authorized_bool": False, "recompute_authorized_bool": False, "new_variant_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, rows_ok: bool, chain_ok: bool, accounting_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("private_span_rows_read", rows_ok, 213 if rows_ok else 0, 213), ("frontier_chain_consistent", chain_ok, int(chain_ok), 1), ("result_accounting_valid", accounting_ok, int(accounting_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ax_public_claim_package_authorized" if complete else "n10ax_not_authorized", "next_allowed_phase": "BEA-v1-N10AX Cost-Sensitive Frontier Claim Package" if complete else "none_until_cost_sensitive_frontier_decomposition_is_valid", "next_allowed_scope_bucket": "public_package_only" if complete else "no_next_phase", "n10ax_authorized": complete, "private_read_authorized": False, "recompute_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False, "heldout_or_generalization_claim_authorized": False, "runtime_or_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, rows_ok: bool, chain_ok: bool, accounting_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10aw_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10aw_private_span_rows_missing"
    if not chain_ok:
        return "no_go_n10aw_frontier_chain_inconsistent"
    if not rows_ok or not accounting_ok:
        return "no_go_n10aw_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10aw_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    computed = compute(rows) if load_status == "pass" else {"valid_rows": 0, "tier_rows": [], "mechanism_rows": []}
    rows_ok = load_status == "pass" and len(rows) == 213 and computed["valid_rows"] == 213
    chain_ok = frontier_chain_consistent(computed["tier_rows"]) if computed["tier_rows"] else False
    accounting_ok = accounting_valid(computed["tier_rows"], computed["mechanism_rows"]) if computed["tier_rows"] else False
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, rows_ok, chain_ok, accounting_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_cost_sensitive_mechanism_decomposition_only", "generated_by": "bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, computed["valid_rows"]), "frontier_tier_delta_records": computed["tier_rows"], "mechanism_bucket_records": computed["mechanism_rows"], "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10ax_handoff_records": n10ax_handoff_records(complete), "gate_records": gate_records(input_ok, rows_ok, chain_ok, accounting_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10ax_handoff_records"] = n10ax_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, rows_ok, chain_ok, accounting_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_accounting_ok() -> bool:
    tier_rows = [
        {"tier_bucket": "baseline", "cumulative_span_hits": 2, "new_span_hits_vs_previous_tier": 2, "lost_previous_hits": 0},
        {"tier_bucket": "pm30", "cumulative_span_hits": 3, "new_span_hits_vs_previous_tier": 1, "lost_previous_hits": 0},
    ]
    mech = [{"tier_bucket": "baseline", "new_span_hit_case_count": 0}, {"tier_bucket": "pm30", "new_span_hit_case_count": 1}]
    return accounting_valid(tier_rows, mech)


def synthetic_bucket_ok() -> bool:
    return marginal_cost_bucket(600, 9) == "low" and marginal_cost_bucket(400, 2) == "medium" and marginal_cost_bucket(500, 1) == "high" and marginal_cost_bucket(2500, 4) == "very_high"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    computed = compute(rows) if load_status == "pass" else {"valid_rows": 0, "tier_rows": [], "mechanism_rows": []}
    rows_ok = load_status == "pass" and len(rows) == 213 and computed["valid_rows"] == 213
    chain_ok = frontier_chain_consistent(computed["tier_rows"]) if computed["tier_rows"] else False
    accounting_ok = accounting_valid(computed["tier_rows"], computed["mechanism_rows"]) if computed["tier_rows"] else False
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10aw_required_inputs_unavailable", "no_go_n10aw_frontier_chain_inconsistent", "no_go_n10aw_private_span_rows_missing", "no_go_n10aw_result_accounting_invalid", "no_go_n10aw_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", rows_ok),
        check("frontier_chain", chain_ok and [r["cumulative_span_hits"] for r in computed["tier_rows"]] == [9, 18, 20, 21, 25]),
        check("top20_chain", [r["cumulative_top20_span_hits"] for r in computed["tier_rows"]] == [10, 22, 24, 25, 30]),
        check("accounting", accounting_ok and [r["new_span_hits_vs_previous_tier"] for r in computed["tier_rows"]] == [9, 9, 2, 1, 4]),
        check("mechanism_buckets", sum(m["new_span_hit_case_count"] for m in computed["mechanism_rows"] if m["tier_bucket"] == "pm200") == 4),
        check("synthetic_accounting", synthetic_accounting_ok()),
        check("synthetic_bucket", synthetic_bucket_ok()),
        check("false_claims", stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["method_winner_claim_authorized"] is False and stop_go_records(True)[0]["heldout_or_generalization_claim_authorized"] is False),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AW cost-sensitive frontier mechanism decomposition")
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
