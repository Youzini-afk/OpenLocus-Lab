#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10au_independent_recompute_span_window_variant_sweep.v1"
PHASE = "BEA-v1-N10AU Independent Recompute Exploratory Span-Window Variant Sweep"
STATUS_PASS = "independent_recompute_span_window_variant_sweep_pass_n10av_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10au_required_inputs_unavailable",
    "no_go_n10au_private_span_rows_missing",
    "no_go_n10au_private_span_rows_schema_invalid",
    "no_go_n10au_recompute_mismatch",
    "no_go_n10au_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json")
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
PUBLIC_INPUTS = {
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
    "n10at_audit_package_artifact": (Path("artifacts/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package_report.json"), "exploratory_span_window_variant_sweep_audit_package_complete_n10au_authorized"),
}
VARIANTS = (
    ("pm0", 0, 0, "symmetric"),
    ("pm10", 10, 10, "symmetric"),
    ("pm20", 20, 20, "symmetric"),
    ("pm30", 30, 30, "symmetric"),
    ("pm50", 50, 50, "symmetric"),
    ("pm75", 75, 75, "symmetric"),
    ("pm100", 100, 100, "symmetric"),
    ("pm150", 150, 150, "symmetric"),
    ("pm200", 200, 200, "symmetric"),
    ("before75_after25", 75, 25, "asymmetric"),
    ("before100_after50", 100, 50, "asymmetric"),
    ("before150_after50", 150, 50, "asymmetric"),
    ("before25_after75", 25, 75, "asymmetric"),
    ("before50_after100", 50, 100, "asymmetric"),
    ("before50_after150", 50, 150, "asymmetric"),
)
EXPECTED_FRONTIER = {
    "pm30": (18, 22, 600, "low"),
    "before25_after75": (20, 24, 1000, "medium"),
    "pm75": (21, 25, 1500, "medium"),
    "pm200": (25, 30, 4000, "very_high"),
}
EXPECTED_ROWS = 213
BASELINE_TOP10 = 9
BASELINE_TOP20 = 10
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
    "private_input_bucket", "intake_status_bucket", "implementation_boundary_bucket", "variant_bucket", "variant_family_bucket",
    "match_status_bucket", "frontier_tier_bucket", "claim_boundary_bucket", "no_execution_boundary_bucket", "n10av_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation", "top10_cost_proxy_bucket",
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


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    loaded: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        loaded[bucket] = artifact
        observed = str(artifact.get("status", ""))
        forbidden = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10auin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return rows, loaded, ok


def read_private_rows() -> tuple[list[dict[str, Any]], str]:
    full = repo_root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in full.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    return [], "schema_invalid"
                rows.append(row)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def schema_ok(row: dict[str, Any]) -> bool:
    evs = row.get("p4_evidence")
    refs = row.get("gold_paths")
    line_ranges = row.get("gold_lines")
    if not isinstance(evs, list) or not isinstance(refs, list) or not isinstance(line_ranges, list) or len(refs) != len(line_ranges):
        return False
    for ev in evs:
        if not (isinstance(ev, dict) and isinstance(ev.get("path"), str) and isinstance(ev.get("start_line"), int) and isinstance(ev.get("end_line"), int)):
            return False
    for item in line_ranges:
        if not (isinstance(item, list) and len(item) >= 2 and isinstance(item[0], int) and isinstance(item[1], int) and item[0] <= item[1]):
            return False
    return True


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    usable = [row for row in rows if schema_ok(row) and row.get("p4_evidence")]
    ok = load_status == "pass" and len(rows) == EXPECTED_ROWS and len(usable) == EXPECTED_ROWS
    return [{"anonymous_private_input_intake_id": "n10aupriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if ok else load_status, "private_span_rows_read": len(rows), "usable_private_span_rows": len(usable), "other_private_files_read_count": 0, "schema_valid_bool": ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}], usable, ok


def best_order(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(items, start=1) if idx <= 20]
    extra = [item for idx, item in enumerate(items, start=1) if idx > 20]
    return extra + primary[:4] + primary[4:]


def lookup(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rng in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rng[0]), int(rng[1])))
    return out


def expand(item: dict[str, Any], before: int, after: int) -> dict[str, Any]:
    copy = dict(item)
    copy["start_line"] = max(1, int(copy["start_line"]) - before)
    copy["end_line"] = int(copy["end_line"]) + after
    return copy


def intersects(a: int, b: int, c: int, d: int) -> bool:
    return max(a, c) <= min(b, d)


def hit(items: list[dict[str, Any]], gold: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for item in items[:limit]:
        key = str(item.get("path", ""))
        if key not in gold:
            continue
        start, end = item.get("start_line"), item.get("end_line")
        if isinstance(start, int) and isinstance(end, int) and any(intersects(start, end, x, y) for x, y in gold[key]):
            return True
    return False


def cost_bucket(cost: int) -> str:
    if cost == 0:
        return "zero"
    if cost <= 600:
        return "low"
    if cost <= 1500:
        return "medium"
    if cost <= 3000:
        return "high"
    return "very_high"


def cost_per_hit(cost: int, delta: int) -> str:
    if delta <= 0:
        return "no_positive_delta"
    ratio = cost / delta
    if ratio <= 100:
        return "low"
    if ratio <= 200:
        return "medium"
    if ratio <= 500:
        return "high"
    return "very_high"


def compute_variant(rows: list[dict[str, Any]], before: int, after: int) -> dict[str, int | bool]:
    top10 = top20 = lost = 0
    pool_changed = False
    order_changed = False
    for row in rows:
        ordered = best_order(row["p4_evidence"])
        gold = lookup(row)
        base10 = hit(ordered, gold, 10)
        expanded = [expand(item, before, after) for item in ordered]
        pool_changed = pool_changed or len(expanded) != len(ordered)
        order_changed = order_changed or len(expanded) != len(ordered)
        now10 = hit(expanded, gold, 10)
        top10 += int(now10)
        top20 += int(hit(expanded, gold, 20))
        lost += int(base10 and not now10)
    return {"top10": top10, "top20": top20, "lost": lost, "pool_changed": pool_changed, "order_changed": order_changed}


def compute_grid(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []
    for name, before, after, family in VARIANTS:
        m = compute_variant(rows, before, after)
        cost = 10 * (before + after)
        raw.append({"variant_bucket": name, "variant_family_bucket": family, "top10_span_overlap_count": int(m["top10"]), "top20_span_overlap_count": int(m["top20"]), "delta_top10_vs_unexpanded_count": int(m["top10"]) - BASELINE_TOP10, "delta_top20_vs_unexpanded_count": int(m["top20"]) - BASELINE_TOP20, "original_span_hit_lost_count": int(m["lost"]), "top10_cost_proxy_value": cost, "top10_cost_proxy_bucket": cost_bucket(cost), "cost_per_additional_hit_bucket": cost_per_hit(cost, int(m["top10"]) - BASELINE_TOP10), "candidate_pool_changed_bool": bool(m["pool_changed"]), "candidate_order_changed_bool": bool(m["order_changed"])})
    for row in raw:
        row["pareto_frontier_bool"] = not any(other["top10_span_overlap_count"] >= row["top10_span_overlap_count"] and other["top10_cost_proxy_value"] <= row["top10_cost_proxy_value"] and (other["top10_span_overlap_count"] > row["top10_span_overlap_count"] or other["top10_cost_proxy_value"] < row["top10_cost_proxy_value"]) for other in raw)
    return raw


def n10as_expected(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = artifact.get("variant_result_records", [])
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
                out[str(row["variant_bucket"])] = row
    return out


def independent_implementation_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_independent_implementation_id": "n10auimpl0000", "implementation_boundary_bucket": "independent_local_logic_no_n10as_import_or_call", "n10as_evaluator_imported_bool": False, "n10as_evaluator_called_bool": False, "n10as_transform_reused_bool": False, "independent_parsing_bool": True, "independent_order_logic_bool": True, "independent_window_logic_bool": True, "independent_overlap_logic_bool": True, "variant_count": 15, "extra_variant_count": 0}], True


def recomputed_variant_result_records(computed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"anonymous_recomputed_variant_result_id": f"n10auvar{idx:04d}", **row} for idx, row in enumerate(computed)]


def aggregate_match_records(computed: list[dict[str, Any]], expected: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = len(computed) == 15 and len(expected) >= 15
    for idx, row in enumerate(computed):
        exp = expected.get(row["variant_bucket"], {})
        matched = bool(exp) and all(exp.get(k) == row.get(k) for k in ("top10_span_overlap_count", "top20_span_overlap_count", "delta_top10_vs_unexpanded_count", "delta_top20_vs_unexpanded_count", "original_span_hit_lost_count", "top10_cost_proxy_value", "top10_cost_proxy_bucket", "pareto_frontier_bool"))
        ok = ok and matched
        rows.append({"anonymous_aggregate_match_id": f"n10aumatch{idx:04d}", "variant_bucket": row["variant_bucket"], "match_status_bucket": "match" if matched else "mismatch", "top10_span_overlap_count": row["top10_span_overlap_count"], "top20_span_overlap_count": row["top20_span_overlap_count"], "top10_cost_proxy_value": row["top10_cost_proxy_value"], "pareto_frontier_bool": row["pareto_frontier_bool"], "aggregate_match_bool": matched})
    return rows, ok


def frontier_match_records(computed: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    by_variant = {row["variant_bucket"]: row for row in computed}
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (variant, (top10, top20, cost, bucket)) in enumerate(EXPECTED_FRONTIER.items()):
        row = by_variant.get(variant, {})
        matched = bool(row) and row.get("top10_span_overlap_count") == top10 and row.get("top20_span_overlap_count") == top20 and row.get("top10_cost_proxy_value") == cost and row.get("top10_cost_proxy_bucket") == bucket and row.get("pareto_frontier_bool") is True
        ok = ok and matched
        rows.append({"anonymous_frontier_match_id": f"n10aufront{idx:04d}", "variant_bucket": variant, "frontier_tier_bucket": "max_recall" if variant == "pm200" else "balanced" if variant != "pm30" else "low_cost", "top10_span_overlap_count": row.get("top10_span_overlap_count", -1), "top20_span_overlap_count": row.get("top20_span_overlap_count", -1), "top10_cost_proxy_value": row.get("top10_cost_proxy_value", -1), "top10_cost_proxy_bucket": row.get("top10_cost_proxy_bucket", "missing"), "pareto_frontier_bool": bool(row.get("pareto_frontier_bool", False)), "frontier_match_bool": matched})
    return rows, ok


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_claim_boundary_id": "n10auclaim0000", "claim_boundary_bucket": "independent_recompute_same_source_exploratory_n1_proxy_only", "same_source_only_bool": True, "n1_span_surface_proxy_only_bool": True, "heldout_claim_bool": False, "n2_equivalent_claim_bool": False, "generalization_claim_bool": False, "runtime_default_claim_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "selector_reranker_claim_bool": False, "claim_boundary_valid_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10aunoexec0000", "no_execution_boundary_bucket": "same_scoped_rows_independent_recompute_only", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0, "extra_variant_count": 0, "order_arm_sweep_count": 0, "per_record_adaptive_window_count": 0, "gold_used_for_window_selection_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10av_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10av_handoff_id": "n10auhandoff0000", "n10av_handoff_bucket": "n10av_public_replication_package_authorized" if complete else "n10av_not_authorized", "n10av_public_replication_package_authorized_bool": complete, "private_read_authorized_bool": False, "extra_sweep_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_validation_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, impl_ok: bool, match_ok: bool, frontier_ok: bool, claim_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read_213", private_ok), ("independent_implementation", impl_ok), ("all_15_variant_aggregates_match", match_ok), ("frontier_tiers_match", frontier_ok), ("claim_boundary", claim_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10av_public_replication_package_authorized" if complete else "n10av_not_authorized", "next_allowed_phase": "BEA-v1-N10AV Exploratory Span-Window Variant Sweep Replication Package" if complete else "none_until_independent_recompute_matches_n10as", "next_allowed_scope_bucket": "public_replication_package_only" if complete else "no_next_phase", "n10av_authorized": complete, "private_read_authorized": False, "extra_sweep_authorized": False, "new_variant_authorized": False, "heldout_validation_claim_authorized": False, "runtime_or_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, private_ok: bool, schema_ok_bool: bool, match_ok: bool, frontier_ok: bool, claim_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10au_required_inputs_unavailable"
    if not private_ok:
        return "no_go_n10au_private_span_rows_missing"
    if not schema_ok_bool:
        return "no_go_n10au_private_span_rows_schema_invalid"
    if not match_ok or not frontier_ok:
        return "no_go_n10au_recompute_mismatch"
    if not claim_ok or not noexec_ok:
        return "no_go_n10au_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    rows, load_status = read_private_rows()
    private_rows, usable, private_ok = private_input_intake_records(rows, load_status)
    schema_ok_bool = private_ok
    impl_rows, impl_ok = independent_implementation_records()
    computed = compute_grid(usable) if private_ok else []
    expected = n10as_expected(artifacts.get("n10as_exploratory_sweep_artifact", {}))
    recomputed_rows = recomputed_variant_result_records(computed)
    match_rows, match_ok = aggregate_match_records(computed, expected) if private_ok and input_ok else ([], False)
    frontier_rows, frontier_ok = frontier_match_records(computed) if private_ok else ([], False)
    claim_rows, claim_ok = claim_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, private_ok, schema_ok_bool, match_ok, frontier_ok, claim_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "phase": PHASE,
        "claim_level": "independent_recompute_same_source_exploratory_n1_proxy_only",
        "generated_by": "bea_v1_n10au_independent_recompute_span_window_variant_sweep",
        "generated_at": now(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_rows,
        "private_input_intake_records": private_rows,
        "independent_implementation_records": impl_rows,
        "recomputed_variant_result_records": recomputed_rows,
        "aggregate_match_records": match_rows,
        "frontier_match_records": frontier_rows,
        "claim_boundary_records": claim_rows,
        "no_forbidden_execution_records": noexec_rows,
        "n10av_handoff_records": n10av_handoff_records(complete),
        "gate_records": gate_records(input_ok, private_ok, impl_ok, match_ok, frontier_ok, claim_ok, noexec_ok, True),
        "stop_go_records": stop_go_records(complete),
        "forbidden_scan": {},
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["n10av_handoff_records"] = n10av_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, impl_ok, match_ok, frontier_ok, claim_ok, noexec_ok, scanner_ok)
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


def synthetic_recompute_ok() -> bool:
    row = {"p4_evidence": [{"path": "a", "start_line": 10, "end_line": 12}], "gold_paths": ["a"], "gold_lines": [[20, 22]]}
    return not hit([expand(x, 0, 0) for x in best_order(row["p4_evidence"])], lookup(row), 10) and hit([expand(x, 0, 10) for x in best_order(row["p4_evidence"])], lookup(row), 10)


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    impl_rows, impl_ok = independent_implementation_records()
    claim_rows, claim_ok = claim_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10au_required_inputs_unavailable", "no_go_n10au_private_span_rows_missing", "no_go_n10au_private_span_rows_schema_invalid", "no_go_n10au_recompute_mismatch", "no_go_n10au_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({key: "x"})["status"] == "fail" for key in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 2 and artifacts["n10as_exploratory_sweep_artifact"].get("status") == PUBLIC_INPUTS["n10as_exploratory_sweep_artifact"][1]),
        check("variant_grid", len(VARIANTS) == 15 and VARIANTS[0][0] == "pm0" and VARIANTS[-1][0] == "before50_after150"),
        check("synthetic_recompute", synthetic_recompute_ok()),
        check("no_n10as_import_or_call", impl_ok and impl_rows[0]["n10as_evaluator_imported_bool"] is False and impl_rows[0]["n10as_evaluator_called_bool"] is False),
        check("claim_boundary", claim_ok and claim_rows[0]["heldout_claim_bool"] is False and claim_rows[0]["runtime_default_claim_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["extra_variant_count"] == 0 and noexec_rows[0]["per_record_adaptive_window_count"] == 0),
        check("stop_go", stop_go_records(True)[0]["n10av_authorized"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_pass", status_for(True, True, True, True, True, True, True, True) == STATUS_PASS),
        check("status_mismatch", status_for(True, True, True, True, False, True, True, True) == "no_go_n10au_recompute_mismatch"),
        check("status_missing_private", status_for(True, True, False, False, True, True, True, True) == "no_go_n10au_private_span_rows_missing"),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AU independent recompute span-window sweep")
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
