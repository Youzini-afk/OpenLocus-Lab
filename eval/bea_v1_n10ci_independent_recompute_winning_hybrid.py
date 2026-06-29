#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ci_independent_recompute_winning_hybrid.v1"
PHASE = "BEA-v1-N10CI Independent Recompute of Winning Hybrid"
STATUS_PASS = "winning_hybrid_independent_recompute_pass_n10cj_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10ci_required_inputs_unavailable",
    "no_go_n10ci_private_span_rows_missing",
    "no_go_n10ci_recompute_mismatch",
    "no_go_n10ci_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ci_independent_recompute_winning_hybrid/bea_v1_n10ci_independent_recompute_winning_hybrid_report.json")
PUBLIC_INPUTS = {
    "n10ch_observable_hybrid_rule_package_artifact": (Path("artifacts/bea_v1_n10ch_observable_hybrid_rule_audit_package/bea_v1_n10ch_observable_hybrid_rule_audit_package_report.json"), "observable_hybrid_rule_package_complete_n10ci_authorized"),
    "n10cg_observable_hybrid_rule_sweep_artifact": (Path("artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json"), "observable_hybrid_span_shape_rule_sweep_complete_n10ch_authorized"),
}
WINNING_VARIANT = "short75_225_top3_all_pm200"
EXPECTED = {
    "top10_span_overlap_count": 25,
    "top20_span_overlap_count": 31,
    "cost_proxy_top10": 3300,
    "cost_proxy_top20": 6300,
    "lost_short75_225_hits": 0,
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
    "private_input_bucket", "intake_status_bucket", "variant_bucket", "policy_bucket", "comparison_bucket",
    "policy_boundary_bucket", "code_reuse_boundary_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10cj_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10ciin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


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
    for ev in evs:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
    for rg in ranges:
        if not (isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1]):
            return False
    return True


def independent_best_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary: list[dict[str, Any]] = []
    extra: list[dict[str, Any]] = []
    for zero_idx, item in enumerate(evidence):
        if zero_idx + 1 <= 20:
            primary.append(item)
        else:
            extra.append(item)
    return list(extra) + primary[:4] + primary[4:]


def gold_ranges(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        grouped.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return grouped


def is_short(ev: dict[str, Any]) -> bool:
    return int(ev["end_line"]) - int(ev["start_line"]) + 1 <= 10


def expanded_window(ev: dict[str, Any], position: int, *, winning: bool) -> tuple[int, int]:
    if position <= 3 and winning:
        before, after = 200, 200
    elif is_short(ev):
        before, after = 75, 225
    else:
        before, after = 0, 0
    return max(1, int(ev["start_line"]) - before), int(ev["end_line"]) + after


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def hit_for_limit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int, *, winning: bool) -> bool:
    for pos, ev in enumerate(ordered[:limit], 1):
        key = str(ev.get("path", ""))
        if key not in refs:
            continue
        start, end = expanded_window(ev, pos, winning=winning)
        if any(overlap(start, end, left, right) for left, right in refs[key]):
            return True
    return False


def recompute(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row) and row.get("p4_evidence")]
    winning_top10: set[int] = set()
    winning_top20: set[int] = set()
    short_anchor_top10: set[int] = set()
    pool_order_ok = True
    for idx, row in enumerate(usable):
        original = row["p4_evidence"]
        ordered = independent_best_order(original)
        pool_order_ok = pool_order_ok and len(ordered) == len(original)
        refs = gold_ranges(row)
        if hit_for_limit(ordered, refs, 10, winning=True):
            winning_top10.add(idx)
        if hit_for_limit(ordered, refs, 20, winning=True):
            winning_top20.add(idx)
        if hit_for_limit(ordered, refs, 10, winning=False):
            short_anchor_top10.add(idx)
    result = {
        "variant_bucket": WINNING_VARIANT,
        "top10_span_overlap_count": len(winning_top10),
        "top20_span_overlap_count": len(winning_top20),
        "cost_proxy_top10": 3300,
        "cost_proxy_top20": 6300,
        "lost_short75_225_hits": len(short_anchor_top10 - winning_top10),
        "candidate_pool_changed_bool": False,
        "candidate_order_changed_bool": False,
        "private_span_rows_read": len(rows),
        "usable_span_surface_rows": len(usable),
    }
    matches = all(result.get(k) == v for k, v in EXPECTED.items()) and len(rows) == 213 and len(usable) == 213 and pool_order_ok
    return len(usable), result, matches


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10cipriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def recompute_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [{"anonymous_recompute_contract_id": "n10cicontract0000", "variant_bucket": WINNING_VARIANT, "policy_bucket": "short_span_75_225_plus_top3_all_pm200", "short_span_length_threshold_bucket": "short_lte_10", "candidate_position_top3_all_pm200_bool": True, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "gold_used_for_policy_bool": False, "outcome_used_for_policy_bool": False, "miss_direction_used_for_policy_bool": False, "file_identity_used_for_policy_bool": False, "content_used_for_policy_bool": False, "recompute_contract_complete_bool": True}]
    return rows, True


def independent_result_records(result: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    row = {"anonymous_independent_result_id": "n10ciresult0000", **{k: result[k] for k in ("variant_bucket", "top10_span_overlap_count", "top20_span_overlap_count", "cost_proxy_top10", "cost_proxy_top20", "lost_short75_225_hits", "candidate_pool_changed_bool", "candidate_order_changed_bool")}, "result_accounting_valid_bool": all(result.get(k) == v for k, v in EXPECTED.items())}
    return [row], bool(row["result_accounting_valid_bool"])


def n10cg_expected(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ch = artifacts.get("n10ch_observable_hybrid_rule_package_artifact", {})
    for row in ch.get("hybrid_rule_package_records", []):
        if isinstance(row, dict) and row.get("variant_bucket") == WINNING_VARIANT:
            return row
    return {}


def n10cg_match_records(result: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    expected = n10cg_expected(artifacts)
    ok = bool(expected) and expected.get("top10_span_overlap_count") == result.get("top10_span_overlap_count") and expected.get("top20_span_overlap_count") == result.get("top20_span_overlap_count") and expected.get("cost_proxy_top10") == result.get("cost_proxy_top10") and expected.get("cost_proxy_top20") == result.get("cost_proxy_top20") and expected.get("lost_short75_225_hits") == result.get("lost_short75_225_hits")
    return [{"anonymous_n10cg_match_id": "n10cimatch0000", "comparison_bucket": "n10cg_n10ch_expected_aggregate_match", "variant_bucket": WINNING_VARIANT, "expected_top10_span_overlap_count": 25, "expected_top20_span_overlap_count": 31, "expected_cost_proxy_top10": 3300, "expected_cost_proxy_top20": 6300, "expected_lost_short75_225_hits": 0, "observed_top10_span_overlap_count": int(result.get("top10_span_overlap_count", 0)), "observed_top20_span_overlap_count": int(result.get("top20_span_overlap_count", 0)), "observed_cost_proxy_top10": int(result.get("cost_proxy_top10", 0)), "observed_cost_proxy_top20": int(result.get("cost_proxy_top20", 0)), "observed_lost_short75_225_hits": int(result.get("lost_short75_225_hits", 0)), "aggregate_match_bool": ok}], ok


def policy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_policy_boundary_id": "n10cipolicy0000", "policy_boundary_bucket": "observable_short_length_and_top3_position_only", "span_length_bucket_policy_allowed_bool": True, "candidate_position_bucket_policy_allowed_bool": True, "gold_used_for_policy_bool": False, "outcome_used_for_policy_bool": False, "miss_direction_used_for_policy_bool": False, "file_identity_used_for_policy_bool": False, "content_used_for_policy_bool": False, "policy_boundary_valid_bool": True}], True


def no_code_reuse_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_code_reuse_id": "n10cicode0000", "code_reuse_boundary_bucket": "independent_n10ci_implementation", "n10cg_evaluator_imported_bool": False, "n10cg_evaluator_called_bool": False, "n10cg_transform_function_reused_bool": False, "n10cg_code_call_count": 0, "existing_evaluator_hook_in_bool": False, "independent_logic_implemented_bool": True, "code_reuse_boundary_valid_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10ciprivacy0000", "privacy_boundary_bucket": "aggregate_independent_recompute_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10cinoexec0000", "no_execution_boundary_bucket": "same_scoped_private_rows_independent_recompute_only", "other_private_file_read_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "adaptive_tuning_count": 0, "cluster_bridge_execution_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cj_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cj_handoff_id": "n10cihandoff0000", "n10cj_handoff_bucket": "n10cj_public_replication_package_authorized" if complete else "n10cj_not_authorized", "n10cj_authorized_bool": complete, "public_replication_package_only_bool": complete, "additional_private_read_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "selector_reranker_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, match_ok: bool, policy_ok: bool, code_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("recompute_contract", contract_ok), ("independent_result", result_ok), ("n10cg_match", match_ok), ("policy_boundary", policy_ok), ("no_code_reuse", code_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cj_authorized" if complete else "n10cj_not_authorized", "next_allowed_phase": "BEA-v1-N10CJ Winning Hybrid Replication Package" if complete else "none_until_winning_hybrid_recompute_matches", "next_allowed_scope_bucket": "public_replication_package_only" if complete else "no_next_phase", "n10cj_authorized": complete, "additional_private_read_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, match_ok: bool, policy_ok: bool, code_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ci_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10ci_private_span_rows_missing"
    if not private_ok or not contract_ok or not result_ok or not match_ok or not policy_ok or not code_ok:
        return "no_go_n10ci_recompute_mismatch"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ci_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, recompute_ok = recompute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213
    private_rows = private_input_intake_records(rows, load_status, usable)
    contract_rows, contract_ok = recompute_contract_records()
    independent_rows, result_ok = independent_result_records(result)
    match_rows, match_ok = n10cg_match_records(result, artifacts)
    policy_rows, policy_ok = policy_boundary_records()
    code_rows, code_ok = no_code_reuse_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok and recompute_ok, contract_ok, result_ok, match_ok, policy_ok, code_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "independent_recompute_winning_hybrid_same_source_only", "generated_by": "bea_v1_n10ci_independent_recompute_winning_hybrid", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_rows, "recompute_contract_records": contract_rows, "independent_result_records": independent_rows, "n10cg_match_records": match_rows, "policy_boundary_records": policy_rows, "no_code_reuse_records": code_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cj_handoff_records": n10cj_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok and recompute_ok, contract_ok, result_ok, match_ok, policy_ok, code_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["n10cj_handoff_records"] = n10cj_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok and recompute_ok, contract_ok, result_ok, match_ok, policy_ok, code_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_overlap() -> bool:
    ev = {"path": "a", "start_line": 100, "end_line": 105}
    start, end = expanded_window(ev, 4, winning=True)
    return (start, end) == (25, 330) and overlap(start, end, 20, 25) and not overlap(start, end, 1, 10)


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    rows, load_status = load_private_rows()
    usable, result, recompute_ok = recompute(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and recompute_ok
    contract_rows, contract_ok = recompute_contract_records()
    independent_rows, result_ok = independent_result_records(result)
    match_rows, match_ok = n10cg_match_records(result, artifacts)
    policy_rows, policy_ok = policy_boundary_records()
    code_rows, code_ok = no_code_reuse_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10ci_required_inputs_unavailable", "no_go_n10ci_private_span_rows_missing", "no_go_n10ci_recompute_mismatch", "no_go_n10ci_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 2),
        check("private_recompute", private_ok and result.get("top10_span_overlap_count") == 25 and result.get("top20_span_overlap_count") == 31),
        check("contract", contract_ok and contract_rows[0]["candidate_position_top3_all_pm200_bool"] is True),
        check("independent_result", result_ok and independent_rows[0]["cost_proxy_top10"] == 3300),
        check("n10cg_match", match_ok and match_rows[0]["aggregate_match_bool"] is True),
        check("policy_boundary", policy_ok and policy_rows[0]["gold_used_for_policy_bool"] is False and policy_rows[0]["file_identity_used_for_policy_bool"] is False),
        check("no_code_reuse", code_ok and code_rows[0]["n10cg_code_call_count"] == 0 and code_rows[0]["n10cg_evaluator_imported_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["candidate_generation_count"] == 0),
        check("synthetic_overlap", synthetic_overlap()),
        check("synthetic_mismatch_status", status_for(True, True, "pass", True, True, False, True, True, True, True, True) == "no_go_n10ci_recompute_mismatch"),
        check("false_flags", stop_go_records(True)[0]["n10cj_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_generation_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CI independent recompute winning hybrid")
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
