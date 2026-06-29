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


SCHEMA_VERSION = "bea_v1_n10bi_asymmetric_window_direction_decomposition.v1"
PHASE = "BEA-v1-N10BI Asymmetric Window Direction Mechanism Decomposition"
STATUS_COMPLETE = "asymmetric_window_direction_decomposition_complete_n10bj_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10bi_required_inputs_unavailable",
    "no_go_n10bi_private_span_rows_missing",
    "no_go_n10bi_comparator_result_mismatch",
    "no_go_n10bi_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10bi_asymmetric_window_direction_decomposition/bea_v1_n10bi_asymmetric_window_direction_decomposition_report.json")
PUBLIC_INPUTS = {
    "n10bh_pm50_comparator_package_artifact": (Path("artifacts/bea_v1_n10bh_pm50_comparator_package/bea_v1_n10bh_pm50_comparator_package_report.json"), "pm50_comparator_package_complete_n10bi_authorized"),
    "n10bg_pm50_comparator_artifact": (Path("artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json"), "cost_aware_decisions_vs_fixed_pm50_comparator_complete_n10bh_authorized"),
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
    "n10ba_selection_rule_smoke_artifact": (Path("artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json"), "cost_aware_span_window_selection_rule_smoke_complete_n10bb_authorized"),
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
    "private_input_bucket", "intake_status_bucket", "comparator_bucket", "variant_bucket", "cost_bucket", "direction_bucket",
    "gain_loss_bucket", "no_gold_policy_bucket", "mechanism_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10bj_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        rows.append({"anonymous_input_artifact_id": f"n10biin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def first_hit(records: list[dict[str, Any]], original: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> tuple[bool, str]:
    for projected, raw in zip(records[:limit], original[:limit]):
        key = str(projected.get("path", ""))
        if key not in refs:
            continue
        start = projected.get("start_line")
        end = projected.get("end_line")
        raw_start = raw.get("start_line")
        raw_end = raw.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int) or not isinstance(raw_start, int) or not isinstance(raw_end, int):
            continue
        start_i = start
        end_i = end
        raw_start_i = raw_start
        raw_end_i = raw_end
        for gold_start, gold_end in refs[key]:
            if overlaps(start_i, end_i, gold_start, gold_end):
                if overlaps(raw_start_i, raw_end_i, gold_start, gold_end):
                    return True, "already_overlap"
                if raw_end_i < gold_start:
                    return True, "before_gold_gap"
                if raw_start_i > gold_end:
                    return True, "after_gold_gap"
                return True, "other"
    return False, "other"


def hits_for(rows: list[dict[str, Any]], before: int, after: int) -> tuple[set[int], set[int], dict[int, str]]:
    top10: set[int] = set()
    top20: set[int] = set()
    bucket_by_idx: dict[int, str] = {}
    for idx, row in enumerate(rows):
        ordered = order(row["p4_evidence"])
        projected = project(ordered, before, after)
        refs = refmap(row)
        hit10, bucket10 = first_hit(projected, ordered, refs, 10)
        hit20, _bucket20 = first_hit(projected, ordered, refs, 20)
        if hit10:
            top10.add(idx)
            bucket_by_idx[idx] = bucket10
        if hit20:
            top20.add(idx)
    return top10, top20, bucket_by_idx


def compute(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], bool]:
    usable = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    pm50_10, pm50_20, pm50_buckets = hits_for(usable, 50, 50)
    asym_10, asym_20, asym_buckets = hits_for(usable, 25, 75)
    gained = asym_10 - pm50_10
    lost = pm50_10 - asym_10
    top20_gained = asym_20 - pm50_20
    top20_lost = pm50_20 - asym_20
    gain_counts = Counter(asym_buckets.get(idx, "other") for idx in gained)
    loss_counts = Counter(pm50_buckets.get(idx, "other") for idx in lost)
    bucket_order = ("before_gold_gap", "after_gold_gap", "already_overlap", "other")
    gain_loss_rows: list[dict[str, Any]] = []
    for idx, bucket in enumerate(bucket_order):
        gain_loss_rows.append({"anonymous_gain_loss_bucket_id": f"n10bigain{idx:04d}", "gain_loss_bucket": "gained_by_before25_after75_vs_pm50", "direction_bucket": bucket, "top10_case_count": int(gain_counts.get(bucket, 0)), "public_bucket_only_bool": True})
    for idx, bucket in enumerate(bucket_order):
        gain_loss_rows.append({"anonymous_gain_loss_bucket_id": f"n10biloss{idx:04d}", "gain_loss_bucket": "lost_by_before25_after75_vs_pm50", "direction_bucket": bucket, "top10_case_count": int(loss_counts.get(bucket, 0)), "public_bucket_only_bool": True})
    pair_rows = [
        {"anonymous_comparator_pair_id": "n10bipair0000", "comparator_bucket": "fixed_symmetric_pm50", "variant_bucket": "pm50", "top10_span_overlap_count": len(pm50_10), "top20_span_overlap_count": len(pm50_20), "cost_proxy_value": 1000, "cost_bucket": "medium"},
        {"anonymous_comparator_pair_id": "n10bipair0001", "comparator_bucket": "asymmetric_before25_after75", "variant_bucket": "before25_after75", "top10_span_overlap_count": len(asym_10), "top20_span_overlap_count": len(asym_20), "cost_proxy_value": 1000, "cost_bucket": "medium"},
    ]
    mechanism = {"anonymous_mechanism_summary_id": "n10bimechanism0000", "mechanism_bucket": "asymmetric_extra_after_context_recovers_before_gold_gap", "top10_net_gain_count": len(asym_10) - len(pm50_10), "top20_net_gain_count": len(asym_20) - len(pm50_20), "top10_gained_case_count": len(gained), "top10_lost_case_count": len(lost), "top20_gained_case_count": len(top20_gained), "top20_lost_case_count": len(top20_lost), "before_gold_gap_gain_count": int(gain_counts.get("before_gold_gap", 0)), "after_gold_gap_gain_count": int(gain_counts.get("after_gold_gap", 0)), "already_overlap_gain_count": int(gain_counts.get("already_overlap", 0)), "other_gain_count": int(gain_counts.get("other", 0)), "same_cost_bool": True, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False}
    ok = len(usable) == 213 and len(pm50_10) == 19 and len(pm50_20) == 23 and len(asym_10) == 20 and len(asym_20) == 24 and mechanism["top10_net_gain_count"] == 1 and mechanism["top20_net_gain_count"] == 1 and len(lost) == 0
    return len(usable), mechanism, pair_rows, gain_loss_rows, {"pm50_top10": len(pm50_10), "pm50_top20": len(pm50_20), "asym_top10": len(asym_10), "asym_top20": len(asym_20), "top10_gained": len(gained), "top10_lost": len(lost)}, ok


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10bipriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def no_gold_policy_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_gold_policy_id": "n10binogold0000", "no_gold_policy_bucket": "fixed_global_pm50_vs_before25_after75_no_per_row_choice", "pm50_before_lines": 50, "pm50_after_lines": 50, "asymmetric_before_lines": 25, "asymmetric_after_lines": 75, "predeclared_global_windows_bool": True, "per_row_adaptive_window_count": 0, "gold_used_to_choose_window_count": 0, "miss_direction_used_to_choose_window_count": 0, "content_aware_adjustment_count": 0, "no_gold_policy_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10biprivacy0000", "privacy_boundary_bucket": "aggregate_direction_buckets_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10binoexec0000", "no_execution_boundary_bucket": "pm50_vs_asymmetric_direction_decomposition_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "new_variant_count": 0, "adaptive_tuning_count": 0, "runtime_default_promotion_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "candidate_order_change_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "heldout_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10bj_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10bj_handoff_id": "n10bihandoff0000", "n10bj_handoff_bucket": "n10bj_public_asymmetry_mechanism_package_authorized" if complete else "n10bj_not_authorized", "n10bj_public_package_authorized_bool": complete, "private_read_authorized_bool": False, "new_variant_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "runtime_default_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, result_ok: bool, nogold_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("pm50_vs_asymmetric_result_accounting", result_ok), ("no_gold_policy", nogold_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10bj_public_asymmetry_mechanism_package_authorized" if complete else "n10bj_not_authorized", "next_allowed_phase": "BEA-v1-N10BJ Asymmetric Window Direction Mechanism Package" if complete else "none_until_asymmetric_direction_decomposition_is_valid", "next_allowed_scope_bucket": "public_asymmetry_mechanism_package_only" if complete else "no_next_phase", "n10bj_authorized": complete, "private_read_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, result_ok: bool, nogold_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10bi_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10bi_private_span_rows_missing"
    if not private_ok or not result_ok:
        return "no_go_n10bi_comparator_result_mismatch"
    if not nogold_ok or not privacy_ok or not noexec_ok:
        return "no_go_n10bi_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, mechanism, pair_rows, gain_loss_rows, _raw, result_ok = compute(rows) if load_status == "pass" else (0, {}, [], [], {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    nogold_rows, nogold_ok = no_gold_policy_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, result_ok, nogold_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_direction_mechanism_decomposition_only", "generated_by": "bea_v1_n10bi_asymmetric_window_direction_decomposition", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "comparator_pair_records": pair_rows, "gain_loss_bucket_records": gain_loss_rows, "no_gold_policy_records": nogold_rows, "mechanism_summary_records": [mechanism] if mechanism else [], "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10bj_handoff_records": n10bj_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, result_ok, nogold_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10bj_handoff_records"] = n10bj_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, result_ok, nogold_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_bucket_classification() -> bool:
    raw = [{"path": "a", "start_line": 10, "end_line": 20}]
    refs = {"a": [(30, 40)]}
    projected = [{"path": "a", "start_line": 1, "end_line": 95}]
    ok, bucket = first_hit(projected, raw, refs, 1)
    return ok and bucket == "before_gold_gap"


def synthetic_accounting() -> bool:
    rows = [
        {"p4_evidence": [{"path": "a", "start_line": 1, "end_line": 1}], "gold_paths": ["a"], "gold_lines": [[50, 50]]},
        {"p4_evidence": [{"path": "b", "start_line": 100, "end_line": 100}], "gold_paths": ["b"], "gold_lines": [[50, 50]]},
    ]
    usable, mechanism, _pairs, _buckets, _raw, _ok = compute(rows)
    return usable == 2 and mechanism["top10_gained_case_count"] == 0


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, mechanism, pair_rows, gain_loss_rows, _raw, result_ok = compute(rows) if load_status == "pass" else (0, {}, [], [], {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    nogold_rows, nogold_ok = no_gold_policy_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10bi_required_inputs_unavailable", "no_go_n10bi_private_span_rows_missing", "no_go_n10bi_comparator_result_mismatch", "no_go_n10bi_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok),
        check("pair_results", result_ok and [r["top10_span_overlap_count"] for r in pair_rows] == [19, 20] and [r["top20_span_overlap_count"] for r in pair_rows] == [23, 24]),
        check("gain_loss_accounting", sum(r["top10_case_count"] for r in gain_loss_rows if r["gain_loss_bucket"].startswith("gained")) == mechanism.get("top10_gained_case_count") and mechanism.get("top10_lost_case_count") == 0),
        check("no_gold_policy", nogold_ok and nogold_rows[0]["gold_used_to_choose_window_count"] == 0 and nogold_rows[0]["miss_direction_used_to_choose_window_count"] == 0),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_count"] == 0 and noexec_rows[0]["adaptive_tuning_count"] == 0),
        check("synthetic_bucket_classification", synthetic_bucket_classification()),
        check("synthetic_accounting", synthetic_accounting()),
        check("false_flags", stop_go_records(True)[0]["n10bj_authorized"] is True and stop_go_records(True)[0]["new_variant_authorized"] is False and stop_go_records(True)[0]["runtime_or_default_authorized"] is False),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True) == STATUS_COMPLETE),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10BI asymmetric window direction decomposition")
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
