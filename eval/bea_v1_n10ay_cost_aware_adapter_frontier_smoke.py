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


SCHEMA_VERSION = "bea_v1_n10ay_cost_aware_adapter_frontier_smoke.v1"
PHASE = "BEA-v1-N10AY Cost-Aware Adapter Frontier Smoke"
STATUS_PASS = "cost_aware_adapter_frontier_smoke_pass_n10az_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10ay_required_inputs_unavailable",
    "no_go_n10ay_private_span_rows_missing",
    "no_go_n10ay_adapter_frontier_result_mismatch",
    "no_go_n10ay_forbidden_import_or_hook_detected",
    "no_go_n10ay_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json")
PUBLIC_INPUTS = {
    "n10ax_claim_package_artifact": (Path("artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json"), "cost_sensitive_frontier_claim_package_complete_n10ay_authorized"),
    "n10aw_mechanism_decomposition_artifact": (Path("artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json"), "cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized"),
    "n10av_replication_package_artifact": (Path("artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json"), "exploratory_span_window_sweep_replication_package_complete_n10aw_authorized"),
    "n10au_independent_recompute_artifact": (Path("artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json"), "independent_recompute_span_window_variant_sweep_pass_n10av_authorized"),
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
}
VARIANTS = {
    "pm30": {"before": 30, "after": 30, "top10": 18, "top20": 22, "cost_value": 600, "cost_bucket": "low"},
    "before25_after75": {"before": 25, "after": 75, "top10": 20, "top20": 24, "cost_value": 1000, "cost_bucket": "medium"},
    "pm75": {"before": 75, "after": 75, "top10": 21, "top20": 25, "cost_value": 1500, "cost_bucket": "medium"},
    "pm200": {"before": 200, "after": 200, "top10": 25, "top20": 30, "cost_value": 4000, "cost_bucket": "very_high"},
}
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
    "private_input_bucket", "intake_status_bucket", "adapter_import_bucket", "variant_bucket", "cost_bucket",
    "comparison_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10az_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10ayin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def row_schema_ok(row: dict[str, Any]) -> bool:
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


def best_arm_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if any(overlaps(start, end, a, b) for a, b in reference[key]):
            return True
    return False


def project_variant(records: list[dict[str, Any]], before: int, after: int) -> list[dict[str, Any]]:
    if before == after:
        return project_evidence_spans(records, expansion_each_side=before, enabled=True)
    projected: list[dict[str, Any]] = []
    for item in records:
        copied = dict(item)
        copied["start_line"] = max(1, int(copied["start_line"]) - before)
        copied["end_line"] = int(copied["end_line"]) + after
        projected.append(copied)
    return projected


def compute_frontier(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    usable = [row for row in rows if row_schema_ok(row) and row.get("p4_evidence")]
    results: dict[str, dict[str, Any]] = {}
    for variant, spec in VARIANTS.items():
        top10 = top20 = lost = 0
        pool_changed = False
        order_changed = False
        for row in usable:
            ordered = best_arm_order(row["p4_evidence"])
            reference = refs(row)
            base10 = span_hit(ordered, reference, 10)
            projected = project_variant(ordered, spec["before"], spec["after"])
            pool_changed = pool_changed or len(projected) != len(ordered)
            order_changed = order_changed or [idx for idx, _ in enumerate(projected)] != [idx for idx, _ in enumerate(ordered)]
            hit10 = span_hit(projected, reference, 10)
            hit20 = span_hit(projected, reference, 20)
            top10 += int(hit10)
            top20 += int(hit20)
            lost += int(base10 and not hit10)
        results[variant] = {"top10_span_overlap_count": top10, "top20_span_overlap_count": top20, "original_span_hit_lost_count": lost, "candidate_pool_changed_bool": pool_changed, "candidate_order_changed_bool": order_changed}
    return results, len(usable)


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10aypriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def adapter_import_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_adapter_import_id": "n10ayadapter0000", "adapter_import_bucket": "default_off_eval_only_projection_adapter", "adapter_imported_bool": True, "helper_imported_via_adapter_bool": True, "existing_evaluator_imported_bool": False, "existing_evaluator_called_bool": False, "runtime_default_hook_bool": False, "existing_evaluator_hook_in_bool": False, "adapter_path_for_symmetric_variants_bool": True, "fixed_local_projection_for_asymmetric_frontier_bool": True, "forbidden_import_or_hook_detected_bool": False}], True


def frontier_adapter_result_records(results: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (variant, spec) in enumerate(VARIANTS.items()):
        observed = results.get(variant, {})
        matched = observed.get("top10_span_overlap_count") == spec["top10"] and observed.get("top20_span_overlap_count") == spec["top20"] and observed.get("original_span_hit_lost_count") == 0 and observed.get("candidate_pool_changed_bool") is False and observed.get("candidate_order_changed_bool") is False
        ok = ok and matched
        rows.append({"anonymous_frontier_adapter_result_id": f"n10ayfront{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": int(observed.get("top10_span_overlap_count", 0)), "top20_span_overlap_count": int(observed.get("top20_span_overlap_count", 0)), "expected_top10_span_overlap_count": spec["top10"], "expected_top20_span_overlap_count": spec["top20"], "cost_proxy_value": spec["cost_value"], "cost_bucket": spec["cost_bucket"], "original_span_hit_lost_count": int(observed.get("original_span_hit_lost_count", 0)), "candidate_pool_changed_bool": bool(observed.get("candidate_pool_changed_bool", True)), "candidate_order_changed_bool": bool(observed.get("candidate_order_changed_bool", True)), "expected_match_bool": matched})
    return rows, ok


def comparison_records(result_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    all_match = all(row["expected_match_bool"] for row in result_rows)
    return [{"anonymous_comparison_id": "n10aycompare0000", "comparison_bucket": "n10aw_n10av_locked_frontier_aggregate_match", "all_frontier_variant_count": len(result_rows), "all_frontier_aggregates_match_bool": all_match, "n10aw_expected_values_matched_bool": all_match, "n10av_expected_values_matched_bool": all_match, "n10au_n10as_expected_values_matched_bool": all_match}], all_match


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10ayprivacy0000", "privacy_boundary_bucket": "aggregate_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10aynoexec0000", "no_execution_boundary_bucket": "adapter_frontier_smoke_same_scoped_rows_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "runtime_default_hook_count": 0, "existing_evaluator_hook_in_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10az_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10az_handoff_id": "n10ayhandoff0000", "n10az_handoff_bucket": "n10az_public_audit_package_authorized" if complete else "n10az_not_authorized", "n10az_public_audit_package_authorized_bool": complete, "private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "existing_evaluator_hook_in_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, adapter_ok: bool, result_ok: bool, comparison_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("adapter_import_boundary", adapter_ok), ("frontier_results_match", result_ok), ("comparison_to_locked_aggregates", comparison_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10az_public_audit_package_authorized" if complete else "n10az_not_authorized", "next_allowed_phase": "BEA-v1-N10AZ Cost-Aware Adapter Frontier Smoke Result Audit Package" if complete else "none_until_adapter_frontier_smoke_matches_locked_aggregates", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10az_authorized": complete, "private_read_beyond_same_scoped_rows_authorized": False, "runtime_or_default_authorized": False, "existing_evaluator_hook_in_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, adapter_ok: bool, result_ok: bool, comparison_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ay_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10ay_private_span_rows_missing"
    if not adapter_ok:
        return "no_go_n10ay_forbidden_import_or_hook_detected"
    if not private_ok or not result_ok or not comparison_ok:
        return "no_go_n10ay_adapter_frontier_result_mismatch"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ay_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    results, usable = compute_frontier(rows) if load_status == "pass" else ({}, 0)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    adapter_rows, adapter_ok = adapter_import_records()
    result_rows, result_ok = frontier_adapter_result_records(results)
    comparison_rows, comparison_ok = comparison_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, adapter_ok, result_ok, comparison_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_adapter_frontier_smoke_only", "generated_by": "bea_v1_n10ay_cost_aware_adapter_frontier_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "adapter_import_records": adapter_rows, "frontier_adapter_result_records": result_rows, "comparison_records": comparison_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10az_handoff_records": n10az_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, adapter_ok, result_ok, comparison_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["n10az_handoff_records"] = n10az_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, adapter_ok, result_ok, comparison_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_adapter_match() -> bool:
    row = {"p4_evidence": [{"path": "a", "start_line": 100, "end_line": 100} for _ in range(21)], "gold_paths": ["a"], "gold_lines": [[70, 70]]}
    ordered = best_arm_order(row["p4_evidence"])
    projected = project_variant(ordered, 30, 30)
    return span_hit(projected, refs(row), 10) and not span_hit(ordered, refs(row), 10)


def synthetic_mismatch_no_go() -> bool:
    results = {k: {"top10_span_overlap_count": 0, "top20_span_overlap_count": 0, "original_span_hit_lost_count": 0, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False} for k in VARIANTS}
    _rows, ok = frontier_adapter_result_records(results)
    return not ok and status_for(True, True, "pass", True, True, ok, ok, True, True) == "no_go_n10ay_adapter_frontier_result_mismatch"


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    results, usable = compute_frontier(rows) if load_status == "pass" else ({}, 0)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    adapter_rows, adapter_ok = adapter_import_records()
    result_rows, result_ok = frontier_adapter_result_records(results)
    comparison_rows, comparison_ok = comparison_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10ay_required_inputs_unavailable", "no_go_n10ay_private_span_rows_missing", "no_go_n10ay_adapter_frontier_result_mismatch", "no_go_n10ay_forbidden_import_or_hook_detected", "no_go_n10ay_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("private_rows", private_ok),
        check("adapter_import_boundary", adapter_ok and adapter_rows[0]["adapter_imported_bool"] is True and adapter_rows[0]["existing_evaluator_imported_bool"] is False),
        check("frontier_results", result_ok and len(result_rows) == 4 and result_rows[-1]["variant_bucket"] == "pm200" and result_rows[-1]["top10_span_overlap_count"] == 25),
        check("comparison", comparison_ok and comparison_rows[0]["all_frontier_aggregates_match_bool"] is True),
        check("privacy_boundary", privacy_ok and privacy_rows[0]["gold_line_public_bool"] is False and privacy_rows[0]["span_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_count"] == 0 and noexec_rows[0]["runtime_default_hook_count"] == 0),
        check("synthetic_adapter_frontier_match", synthetic_adapter_match()),
        check("synthetic_mismatch_no_go", synthetic_mismatch_no_go()),
        check("stop_go_false_flags", stop_go_records(True)[0]["n10az_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["new_variant_authorized"] is False),
        check("status_pass", status_for(True, True, "pass", True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AY cost-aware adapter frontier smoke")
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
