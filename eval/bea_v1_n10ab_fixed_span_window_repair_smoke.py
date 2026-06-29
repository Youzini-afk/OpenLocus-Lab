#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ab_fixed_span_window_repair_smoke.v1"
PHASE = "BEA-v1-N10AB Fixed Span-Window Repair Smoke"
GENERATED_BY = "bea_v1_n10ab_fixed_span_window_repair_smoke"
STATUS_PASS = "fixed_span_window_repair_smoke_pass_n10ac_authorized"
STATUS_BELOW = "fixed_span_window_repair_smoke_complete_below_threshold"
BEST_ARM = "span_extra_depth_promote_before_primary_prefix_4"

STATUSES = (
    STATUS_PASS,
    STATUS_BELOW,
    "no_go_n10ab_required_inputs_unavailable",
    "no_go_n10ab_private_span_rows_missing",
    "no_go_n10ab_n10aa_preflight_invalid",
    "no_go_n10ab_span_schema_invalid",
    "no_go_n10ab_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json")
INPUTS = {
    "n10aa_repair_preflight_artifact": (Path("artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json"), "span_window_repair_preflight_pass_n10ab_authorized"),
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
    "n10x_span_level_validation_artifact": (Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json"), "n1_span_surface_span_level_utility_validation_complete_below_threshold"),
}
VARIANTS = (
    ("fixed_symmetric_span_expansion_pm50_lines", "primary", 50),
    ("fixed_symmetric_span_expansion_pm20_lines", "secondary_sensitivity", 20),
    ("fixed_symmetric_span_expansion_pm100_lines", "secondary_sensitivity", 100),
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
    "private_input_bucket", "intake_status_bucket", "variant_bucket", "variant_role_bucket", "execution_bucket",
    "decision_bucket", "metric_bucket", "overreach_bucket", "policy_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10ac_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        records.append({"anonymous_input_artifact_id": f"n10abin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, ok


def n10aa_preflight_valid() -> bool:
    artifact, load_status = load_json(INPUTS["n10aa_repair_preflight_artifact"][0])
    if load_status != "pass" or artifact.get("status") != "span_window_repair_preflight_pass_n10ab_authorized":
        return False
    variants = artifact.get("repair_variant_design_records", [])
    metric = (artifact.get("n10ab_metric_contract_records") or [{}])[0]
    return len(variants) == 3 and metric.get("baseline_n10x_best_arm_top10_span_overlap_count") == 9 and metric.get("pass_threshold_count") == 11


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


def span_hit_topk(ordered: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]], k: int, expand: int) -> bool:
    for _idx, ev in ordered[:k]:
        ref = str(ev.get("path", ""))
        if ref not in refs:
            continue
        start = ev.get("start_line")
        end = ev.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        expanded_start = max(1, start - expand)
        expanded_end = end + expand
        if any(overlaps(expanded_start, expanded_end, a, b) for a, b in refs[ref]):
            return True
    return False


def file_hit_topk(ordered: list[tuple[int, dict[str, Any]]], refs: dict[str, list[tuple[int, int]]], k: int) -> bool:
    return any(str(ev.get("path", "")) in refs for _idx, ev in ordered[:k])


def compute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    eligible = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    baseline_top10 = baseline_top20 = top10_file = 0
    variant_counts: dict[str, dict[str, int]] = {bucket: {"top10": 0, "top20": 0, "lost": 0, "file_without_expanded_top10": 0} for bucket, _role, _amount in VARIANTS}
    for row in eligible:
        refs = ref_map(row)
        ordered = order_best(row["p4_evidence"])
        base10 = span_hit_topk(ordered, refs, 10, 0)
        base20 = span_hit_topk(ordered, refs, 20, 0)
        file10 = file_hit_topk(ordered, refs, 10)
        baseline_top10 += int(base10)
        baseline_top20 += int(base20)
        top10_file += int(file10)
        for bucket, _role, amount in VARIANTS:
            exp10 = span_hit_topk(ordered, refs, 10, amount)
            exp20 = span_hit_topk(ordered, refs, 20, amount)
            variant_counts[bucket]["top10"] += int(exp10)
            variant_counts[bucket]["top20"] += int(exp20)
            variant_counts[bucket]["lost"] += int(base10 and not exp10)
            variant_counts[bucket]["file_without_expanded_top10"] += int(file10 and not exp10)
    records = []
    overreach_records = []
    for idx, (bucket, role, amount) in enumerate(VARIANTS):
        counts = variant_counts[bucket]
        records.append({"anonymous_repair_variant_execution_id": f"n10abvar{idx:04d}", "variant_bucket": bucket, "variant_role_bucket": role, "execution_bucket": "fixed_symmetric_expansion_evaluated_on_existing_top10_evidence", "expansion_each_side_count": amount, "eligible_denominator_count": len(eligible), "top10_file_hit_count": top10_file, "baseline_unexpanded_top10_span_overlap_count": baseline_top10, "baseline_unexpanded_top20_span_overlap_count": baseline_top20, "top10_expanded_span_overlap_count": counts["top10"], "top20_expanded_span_overlap_count": counts["top20"], "delta_top10_vs_unexpanded_best_arm": counts["top10"] - baseline_top10, "original_span_hit_lost_count": counts["lost"], "gold_signal_used_for_window_bool": False, "miss_direction_used_for_window_bool": False, "content_aware_adjustment_bool": False, "candidate_pool_changed_bool": False, "candidate_added_count": 0, "candidate_removed_count": 0})
        overreach_records.append({"anonymous_expansion_overreach_bucket_id": f"n10abover{idx:04d}", "variant_bucket": bucket, "overreach_bucket": "top10_file_hit_without_expanded_span_overlap", "case_count": counts["file_without_expanded_top10"]})
    exact = len(eligible) == 213 and baseline_top10 == 9 and baseline_top20 == 10 and top10_file == 34
    return records, overreach_records, exact


def private_span_input_intake_records(rows: list[dict[str, Any]], load_status: str, schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_span_input_intake_id": "n10abpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if schema_ok else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "schema_valid_bool": schema_ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def primary_decision_records(variant_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    primary = next((r for r in variant_records if r["variant_bucket"] == "fixed_symmetric_span_expansion_pm50_lines"), {})
    passed = int(primary.get("top10_expanded_span_overlap_count", 0)) >= 11 and int(primary.get("original_span_hit_lost_count", 1)) == 0
    return [{"anonymous_primary_decision_id": "n10abdecision0000", "decision_bucket": "pm50_pass" if passed else "pm50_below_threshold", "metric_bucket": "top10_expanded_span_overlap_count_pm50", "baseline_unexpanded_top10_span_overlap_count": 9, "pass_threshold_count": 11, "observed_top10_expanded_span_overlap_count": int(primary.get("top10_expanded_span_overlap_count", 0)), "observed_top20_expanded_span_overlap_count": int(primary.get("top20_expanded_span_overlap_count", 0)), "delta_top10_vs_unexpanded_best_arm": int(primary.get("delta_top10_vs_unexpanded_best_arm", 0)), "original_span_hit_lost_count": int(primary.get("original_span_hit_lost_count", 0)), "primary_pass_bool": passed}], passed


def gold_free_execution_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_gold_free_execution_boundary_id": "n10abgold0000", "policy_bucket": "fixed_windows_no_gold_no_direction_no_content_adjustment", "gold_signal_used_for_window_bool": False, "miss_direction_used_for_window_bool": False, "content_aware_adjustment_bool": False, "path_change_bool": False, "candidate_add_remove_bool": False, "gold_only_for_evaluation_bool": True, "boundary_complete_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10abprivacy0000", "privacy_boundary_bucket": "public_counts_only_no_private_surface_details", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10abnoexec0000", "no_execution_boundary_bucket": "single_private_span_read_fixed_window_smoke_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10ac_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ac_handoff_id": "n10abhandoff0000", "n10ac_handoff_bucket": "n10ac_public_repair_smoke_audit_authorized" if complete else "n10ac_not_authorized", "n10ac_public_repair_smoke_audit_authorized_bool": complete, "public_audit_scope_only_bool": True, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, preflight_ok: bool, schema_ok: bool, exact: bool, complete: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("n10aa_preflight_valid", preflight_ok, int(preflight_ok), 1), ("private_span_rows_read", schema_ok, 213 if schema_ok else 0, 213), ("baseline_metrics_match", exact, int(exact), 1), ("smoke_complete", complete, int(complete), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ac_public_repair_smoke_audit_authorized" if complete else "n10ac_not_authorized", "next_allowed_phase": "BEA-v1-N10AC Fixed Span-Window Repair Smoke Result Audit" if complete else "none_until_valid_fixed_span_window_repair_smoke_exists", "next_allowed_scope_bucket": "public_audit_only_no_promotion" if complete else "no_next_phase", "n10ac_public_audit_authorized": complete, "private_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, preflight_ok: bool, schema_ok: bool, exact: bool, privacy_ok: bool, noexec_ok: bool, primary_pass: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ab_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10ab_private_span_rows_missing"
    if not preflight_ok:
        return "no_go_n10ab_n10aa_preflight_invalid"
    if not schema_ok or not exact:
        return "no_go_n10ab_span_schema_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ab_privacy_or_claim_boundary_failed"
    return STATUS_PASS if primary_pass else STATUS_BELOW


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    preflight_ok = n10aa_preflight_valid()
    rows, load_status = load_rows()
    schema_ok = load_status == "pass" and len(rows) == 213 and all(row_ok(r) for r in rows)
    variant_records, overreach_records, exact = compute(rows) if schema_ok else ([], [], False)
    decision_records, primary_pass = primary_decision_records(variant_records) if variant_records else ([], False)
    gold_records, gold_ok = gold_free_execution_boundary_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, preflight_ok and gold_ok, schema_ok, exact, privacy_ok, noexec_ok, primary_pass)
    complete = status in {STATUS_PASS, STATUS_BELOW}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "fixed_span_window_repair_smoke_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_span_input_intake_records": private_span_input_intake_records(rows, load_status, schema_ok), "repair_variant_execution_records": variant_records, "primary_decision_records": decision_records, "expansion_overreach_bucket_records": overreach_records, "gold_free_execution_boundary_records": gold_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records, "n10ac_handoff_records": n10ac_handoff_records(complete), "gate_records": gate_records(input_ok, preflight_ok, schema_ok, exact, complete, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] in {STATUS_PASS, STATUS_BELOW}
    report["gate_records"] = gate_records(input_ok, preflight_ok, schema_ok, exact, complete, privacy_ok, noexec_ok, scanner_ok)
    report["n10ac_handoff_records"] = n10ac_handoff_records(complete)
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
    variant_records, overreach_records, exact = compute(rows) if schema_ok else ([], [], False)
    decision_records, primary_pass = primary_decision_records(variant_records) if variant_records else ([], False)
    by_variant = {r["variant_bucket"]: r for r in variant_records}
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, STATUS_BELOW, "no_go_n10ab_required_inputs_unavailable", "no_go_n10ab_private_span_rows_missing", "no_go_n10ab_n10aa_preflight_invalid", "no_go_n10ab_span_schema_invalid", "no_go_n10ab_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 3 and n10aa_preflight_valid()),
        check("private_input", load_status == "pass" and schema_ok and len(rows) == 213),
        check("baseline", exact and variant_records[0]["baseline_unexpanded_top10_span_overlap_count"] == 9 and variant_records[0]["top10_file_hit_count"] == 34),
        check("pm20", by_variant["fixed_symmetric_span_expansion_pm20_lines"]["top10_expanded_span_overlap_count"] == 15 and by_variant["fixed_symmetric_span_expansion_pm20_lines"]["top20_expanded_span_overlap_count"] == 19),
        check("pm50", by_variant["fixed_symmetric_span_expansion_pm50_lines"]["top10_expanded_span_overlap_count"] == 19 and by_variant["fixed_symmetric_span_expansion_pm50_lines"]["top20_expanded_span_overlap_count"] == 23),
        check("pm100", by_variant["fixed_symmetric_span_expansion_pm100_lines"]["top10_expanded_span_overlap_count"] == 21 and by_variant["fixed_symmetric_span_expansion_pm100_lines"]["top20_expanded_span_overlap_count"] == 25),
        check("decision", primary_pass and decision_records[0]["observed_top10_expanded_span_overlap_count"] == 19 and decision_records[0]["delta_top10_vs_unexpanded_best_arm"] == 10),
        check("gold_free", gold_free_execution_boundary_records()[0][0]["gold_signal_used_for_window_bool"] is False and all(r["original_span_hit_lost_count"] == 0 for r in variant_records)),
        check("privacy", privacy_boundary_records()[1] and privacy_boundary_records()[0][0]["gold_line_public_bool"] is False),
        check("no_execution", no_forbidden_execution_records()[1] and no_forbidden_execution_records()[0][0]["private_span_input_read_count"] == 1 and no_forbidden_execution_records()[0][0]["other_private_file_read_count"] == 0),
        check("handoff", n10ac_handoff_records(True)[0]["n10ac_public_repair_smoke_audit_authorized_bool"] is True and stop_go_records(True)[0]["runtime_or_default_promotion_authorized"] is False),
        check("status_expected", status_for(True, True, "pass", True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AB fixed span-window repair smoke")
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
    decision = report["primary_decision_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={decision['observed_top10_expanded_span_overlap_count']})")


if __name__ == "__main__":
    main()
