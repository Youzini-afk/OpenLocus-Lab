#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10v_independent_recompute_n1_span_surface_proxy.v1"
PHASE = "BEA-v1-N10V Independent Recompute N1 Span-Surface Proxy"
GENERATED_BY = "bea_v1_n10v_independent_recompute_n1_span_surface_proxy"
STATUS_PASS = "independent_recompute_n1_span_surface_proxy_pass_n10w_authorized"

STATUSES = (
    STATUS_PASS,
    "no_go_n10v_required_inputs_unavailable",
    "no_go_n10v_private_span_rows_missing",
    "no_go_n10v_recompute_mismatch",
    "no_go_n10v_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

ARMS = (
    "baseline_n1_span_order",
    "span_extra_depth_promote_before_primary_prefix_4",
    "span_bounded_interleave_primary2_extra1",
    "span_late_extra_depth_demote_after_primary_prefix_8",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json")
INPUTS = {
    "n10u_proxy_result_audit_artifact": (
        Path("artifacts/bea_v1_n10u_n1_span_surface_proxy_result_audit/bea_v1_n10u_n1_span_surface_proxy_result_audit_report.json"),
        "n1_span_surface_proxy_result_audit_pass_n10v_authorized",
    ),
    "n10t_proxy_validation_artifact": (
        Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json"),
        "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized",
    ),
    "n10r_preflight_artifact": (
        Path("artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json"),
        "no_go_n10r_target_denominator_insufficient",
    ),
    "n9_replication_package_artifact": (
        Path("artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json"),
        "recovered_fixed_pool_result_replication_package_complete",
    ),
}
EXPECTED = {
    "eligible_denominator_count": 213,
    "reachable_in_pool_count": 52,
    "baseline_top10_file_reach_count": 0,
    "baseline_top20_file_reach_count": 0,
    "best_arm_bucket": "span_extra_depth_promote_before_primary_prefix_4",
    "best_top10_file_reach_count": 34,
    "best_top20_file_reach_count": 44,
    "best_delta_top10_vs_baseline": 34,
    "best_case_regression_count_vs_baseline": 0,
    "delta_top10_threshold": 11,
    "case_regression_threshold": 3,
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "private_input_bucket", "intake_status_bucket", "recompute_bucket", "arm_bucket", "result_status_bucket",
    "comparison_bucket", "best_arm_bucket", "threshold_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10w_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10vin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def load_span_rows() -> tuple[list[dict[str, Any]], str]:
    full = root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with full.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "schema_invalid"
                rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def schema_ok(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if not isinstance(row.get("p4_evidence"), list) or not isinstance(row.get("gold_paths"), list):
            return False
        for ev in row.get("p4_evidence", [])[:3]:
            if not isinstance(ev, dict) or "path" not in ev:
                return False
    return True


def eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if isinstance(row.get("p4_evidence"), list) and row.get("p4_evidence") and isinstance(row.get("gold_paths"), list) and row.get("gold_paths")]


def private_span_recompute_input_records(rows: list[dict[str, Any]], load_status: str, valid_schema: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_span_recompute_input_id": "n10vpriv0000", "private_input_bucket": "same_scoped_n1_span_rows", "intake_status_bucket": "pass" if valid_schema else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "same_private_span_rows_read_bool": load_status == "pass", "other_private_file_read_count": 0, "schema_valid_bool": valid_schema, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def order_for(arm: str, evidence: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    indexed = list(enumerate(evidence, start=1))
    primary = [item for item in indexed if item[0] <= 20]
    extra = [item for item in indexed if item[0] > 20]
    if arm == "baseline_n1_span_order":
        return indexed
    if arm == "span_extra_depth_promote_before_primary_prefix_4":
        return extra + primary[:4] + primary[4:]
    if arm == "span_bounded_interleave_primary2_extra1":
        out: list[tuple[int, dict[str, Any]]] = []
        p = e = 0
        while p < len(primary) or e < len(extra):
            out.extend(primary[p:p + 2])
            p += 2
            if e < len(extra):
                out.append(extra[e])
                e += 1
            if p >= len(primary):
                break
        out.extend(primary[p:])
        out.extend(extra[e:])
        return out
    if arm == "span_late_extra_depth_demote_after_primary_prefix_8":
        return primary[:8] + primary[8:] + extra
    raise ValueError("unknown arm")


def first_hit(order: list[tuple[int, dict[str, Any]]], gold: set[str]) -> int | None:
    for idx, (_original_position, ev) in enumerate(order, start=1):
        if str(ev.get("path", "")) in gold:
            return idx
    return None


def recompute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    eligible = eligible_rows(rows)
    reachable = 0
    positions: dict[str, list[int | None]] = {arm: [] for arm in ARMS}
    baseline_top10: list[bool] = []
    for row in eligible:
        gold = {str(item) for item in row.get("gold_paths", []) if item}
        evidence = row.get("p4_evidence", [])
        reachable += int(any(str(ev.get("path", "")) in gold for ev in evidence if isinstance(ev, dict)))
        for arm in ARMS:
            positions[arm].append(first_hit(order_for(arm, evidence), gold))
        base_pos = positions["baseline_n1_span_order"][-1]
        baseline_top10.append(base_pos is not None and base_pos <= 10)
    baseline_count = sum(baseline_top10)
    records: list[dict[str, Any]] = []
    for idx, arm in enumerate(ARMS):
        arm_positions = positions[arm]
        top10 = sum(1 for pos in arm_positions if pos is not None and pos <= 10)
        top20 = sum(1 for pos in arm_positions if pos is not None and pos <= 20)
        regressions = sum(1 for base_hit, pos in zip(baseline_top10, arm_positions) if base_hit and not (pos is not None and pos <= 10))
        delta = top10 - baseline_count
        records.append({"anonymous_per_arm_independent_result_id": f"n10vres{idx:04d}", "arm_bucket": arm, "result_status_bucket": "independent_proxy_threshold_candidate" if delta > 0 else "independent_proxy_no_gain", "eligible_denominator_count": len(eligible), "reachable_in_pool_count": reachable, "top10_file_reach_count": top10, "top20_file_reach_count": top20, "delta_top10_vs_baseline": delta, "case_regression_count_vs_baseline": regressions, "candidate_pool_changed_bool": False, "candidate_added_count": 0, "candidate_removed_count": 0})
    best = max(records, key=lambda r: int(r["delta_top10_vs_baseline"])) if records else {}
    import math
    delta_threshold = max(10, math.ceil(0.05 * len(eligible)))
    regression_threshold = math.ceil(0.01 * len(eligible))
    summary = {"recompute_bucket": "independent_same_span_rows_same_four_arms", "eligible_denominator_count": len(eligible), "reachable_in_pool_count": reachable, "baseline_top10_file_reach_count": next(r["top10_file_reach_count"] for r in records if r["arm_bucket"] == "baseline_n1_span_order") if records else 0, "baseline_top20_file_reach_count": next(r["top20_file_reach_count"] for r in records if r["arm_bucket"] == "baseline_n1_span_order") if records else 0, "best_arm_bucket": str(best.get("arm_bucket", "")), "best_top10_file_reach_count": int(best.get("top10_file_reach_count", 0)), "best_top20_file_reach_count": int(best.get("top20_file_reach_count", 0)), "best_delta_top10_vs_baseline": int(best.get("delta_top10_vs_baseline", 0)), "best_case_regression_count_vs_baseline": int(best.get("case_regression_count_vs_baseline", 0)), "delta_top10_threshold": delta_threshold, "case_regression_threshold": regression_threshold, "threshold_passed_bool": int(best.get("delta_top10_vs_baseline", 0)) >= delta_threshold and int(best.get("case_regression_count_vs_baseline", 0)) <= regression_threshold, "gold_used_for_ordering_bool": False, "candidate_pool_changed_bool": False, "new_arm_search_bool": False}
    exact = all(summary[k] == v for k, v in EXPECTED.items()) and summary["threshold_passed_bool"] is True
    return records, summary, exact


def independent_recompute_records(summary: dict[str, Any], exact: bool) -> list[dict[str, Any]]:
    return [{"anonymous_independent_recompute_id": "n10vrecompute0000", **summary, "recompute_matches_expected_bool": exact, "transform_implemented_independently_bool": True, "n10t_code_called_bool": False}]


def comparison_to_n10t_records(n10t: dict[str, Any], summary: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    threshold = (n10t.get("threshold_decision_records") or [{}])[0]
    denominator = (n10t.get("span_surface_denominator_records") or [{}])[0]
    by_arm = {row.get("arm_bucket"): row for row in n10t.get("per_arm_proxy_result_records", []) if isinstance(row, dict)}
    baseline = by_arm.get("baseline_n1_span_order", {})
    best = by_arm.get(EXPECTED["best_arm_bucket"], {})
    source = {
        "eligible_denominator_count": denominator.get("eligible_denominator_count"),
        "reachable_in_pool_count": denominator.get("reachable_in_pool_count"),
        "baseline_top10_file_reach_count": baseline.get("top10_file_reach_count"),
        "baseline_top20_file_reach_count": baseline.get("top20_file_reach_count"),
        "best_arm_bucket": threshold.get("best_arm_bucket"),
        "best_top10_file_reach_count": threshold.get("best_top10_file_reach_count"),
        "best_top20_file_reach_count": threshold.get("best_top20_file_reach_count"),
        "best_delta_top10_vs_baseline": threshold.get("best_delta_top10_vs_baseline"),
        "best_case_regression_count_vs_baseline": threshold.get("best_case_regression_count_vs_baseline"),
        "delta_top10_threshold": threshold.get("delta_top10_threshold"),
        "case_regression_threshold": threshold.get("case_regression_threshold"),
        "threshold_passed_bool": threshold.get("threshold_passed_bool"),
    }
    # Best arm source top10/top20 are also present in per-arm rows; prefer explicit arm rows if threshold fields drift.
    source["best_top10_file_reach_count"] = best.get("top10_file_reach_count", source["best_top10_file_reach_count"])
    source["best_top20_file_reach_count"] = best.get("top20_file_reach_count", source["best_top20_file_reach_count"])
    ok = all(source.get(k) == summary.get(k) for k in source)
    return [{"anonymous_comparison_to_n10t_id": "n10vcmp0000", "comparison_bucket": "n10t_public_aggregate_match", "source_eligible_denominator_count": int(source.get("eligible_denominator_count", -1)), "independent_eligible_denominator_count": int(summary.get("eligible_denominator_count", -1)), "source_reachable_in_pool_count": int(source.get("reachable_in_pool_count", -1)), "independent_reachable_in_pool_count": int(summary.get("reachable_in_pool_count", -1)), "source_best_arm_bucket": str(source.get("best_arm_bucket", "")), "independent_best_arm_bucket": str(summary.get("best_arm_bucket", "")), "source_best_top10_file_reach_count": int(source.get("best_top10_file_reach_count", -1)), "independent_best_top10_file_reach_count": int(summary.get("best_top10_file_reach_count", -1)), "source_best_top20_file_reach_count": int(source.get("best_top20_file_reach_count", -1)), "independent_best_top20_file_reach_count": int(summary.get("best_top20_file_reach_count", -1)), "source_best_delta_top10_vs_baseline": int(source.get("best_delta_top10_vs_baseline", -1)), "independent_best_delta_top10_vs_baseline": int(summary.get("best_delta_top10_vs_baseline", -1)), "source_best_case_regression_count_vs_baseline": int(source.get("best_case_regression_count_vs_baseline", -1)), "independent_best_case_regression_count_vs_baseline": int(summary.get("best_case_regression_count_vs_baseline", -1)), "comparison_match_bool": ok}], ok


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10vprivacy0000", "privacy_boundary_bucket": "public_counts_only_no_span_or_path_content", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10vnoexec0000", "no_execution_boundary_bucket": "single_private_span_read_independent_proxy_recompute", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "n10t_code_call_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "support_labeling_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10w_handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10w_handoff_id": "n10vhandoff0000", "n10w_handoff_bucket": "n10w_public_replication_package_authorized" if pass_status else "n10w_not_authorized", "n10w_replication_package_authorized_bool": pass_status, "public_replication_package_scope_only_bool": pass_status, "broad_private_read_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, rows_ok: bool, recompute_ok: bool, comparison_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [
        ("public_inputs_loaded", input_ok, int(input_ok), 1),
        ("private_span_rows_read", rows_ok, 213 if rows_ok else 0, 213),
        ("eligible_denominator_count", recompute_ok, EXPECTED["eligible_denominator_count"] if recompute_ok else 0, EXPECTED["eligible_denominator_count"]),
        ("reachable_in_pool_count", recompute_ok, EXPECTED["reachable_in_pool_count"] if recompute_ok else 0, EXPECTED["reachable_in_pool_count"]),
        ("best_top10_file_reach_count", recompute_ok, EXPECTED["best_top10_file_reach_count"] if recompute_ok else 0, EXPECTED["best_top10_file_reach_count"]),
        ("best_top20_file_reach_count", recompute_ok, EXPECTED["best_top20_file_reach_count"] if recompute_ok else 0, EXPECTED["best_top20_file_reach_count"]),
        ("best_delta_top10_vs_baseline", recompute_ok, EXPECTED["best_delta_top10_vs_baseline"] if recompute_ok else 0, EXPECTED["best_delta_top10_vs_baseline"]),
        ("best_regressions", recompute_ok, EXPECTED["best_case_regression_count_vs_baseline"] if recompute_ok else -1, EXPECTED["best_case_regression_count_vs_baseline"]),
        ("comparison_to_n10t", comparison_ok, int(comparison_ok), 1),
        ("privacy_boundary", privacy_ok, int(privacy_ok), 1),
        ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1),
        ("forbidden_scan", scanner_ok, int(scanner_ok), 1),
    ]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10w_replication_package_authorized" if pass_status else "n10w_not_authorized", "next_allowed_phase": "BEA-v1-N10W N1 Span-Surface Proxy Replication Package" if pass_status else "none_until_independent_proxy_recompute_matches_n10t", "next_allowed_scope_bucket": "n10w_public_package_only" if pass_status else "no_next_phase", "n10w_replication_package_authorized": pass_status, "broad_private_read_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "p5_authorized": False, "v1_a_authorized": False, "selector_or_reranker_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "new_arm_search_authorized": False, "counterfactual_authorized": False, "policy_change_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, valid_schema: bool, recompute_ok: bool, comparison_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10v_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10v_private_span_rows_missing"
    if not valid_schema or not recompute_ok or not comparison_ok:
        return "no_go_n10v_recompute_mismatch"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10v_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    rows, load_status = load_span_rows()
    valid_schema = load_status == "pass" and schema_ok(rows)
    per_arm, summary, recompute_ok = recompute(rows) if valid_schema else ([], {}, False)
    recompute_records = independent_recompute_records(summary, recompute_ok) if summary else []
    comparison_records, comparison_ok = comparison_to_n10t_records(artifacts.get("n10t_proxy_validation_artifact", {}), summary) if summary else ([], False)
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, valid_schema, recompute_ok, comparison_ok, privacy_ok, noexec_ok)
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "independent_recompute_n1_span_surface_proxy_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_span_recompute_input_records": private_span_recompute_input_records(rows, load_status, valid_schema), "independent_recompute_records": recompute_records, "per_arm_independent_result_records": per_arm, "comparison_to_n10t_records": comparison_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records, "n10w_handoff_records": n10w_handoff_records(pass_status), "gate_records": gate_records(input_ok, valid_schema, recompute_ok, comparison_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(pass_status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    pass_status = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, valid_schema, recompute_ok, comparison_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10w_handoff_records"] = n10w_handoff_records(pass_status)
    report["stop_go_records"] = stop_go_records(pass_status)
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
    inputs, artifacts, input_ok = input_artifact_records()
    rows, load_status = load_span_rows()
    valid_schema = load_status == "pass" and schema_ok(rows)
    per_arm, summary, recompute_ok = recompute(rows) if valid_schema else ([], {}, False)
    recompute_records = independent_recompute_records(summary, recompute_ok) if summary else []
    comparison_records, comparison_ok = comparison_to_n10t_records(artifacts.get("n10t_proxy_validation_artifact", {}), summary) if summary else ([], False)
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10v_required_inputs_unavailable", "no_go_n10v_private_span_rows_missing", "no_go_n10v_recompute_mismatch", "no_go_n10v_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 4),
        check("private_input", load_status == "pass" and valid_schema and len(rows) == 213),
        check("recompute", recompute_ok and recompute_records[0]["eligible_denominator_count"] == 213 and recompute_records[0]["reachable_in_pool_count"] == 52),
        check("per_arm", len(per_arm) == 4 and {r["arm_bucket"] for r in per_arm} == set(ARMS)),
        check("best_metrics", summary.get("best_arm_bucket") == EXPECTED["best_arm_bucket"] and summary.get("best_top10_file_reach_count") == 34 and summary.get("best_top20_file_reach_count") == 44 and summary.get("best_delta_top10_vs_baseline") == 34 and summary.get("best_case_regression_count_vs_baseline") == 0),
        check("threshold", summary.get("delta_top10_threshold") == 11 and summary.get("case_regression_threshold") == 3 and summary.get("threshold_passed_bool") is True),
        check("comparison", comparison_ok and comparison_records[0]["comparison_match_bool"] is True),
        check("privacy", privacy_ok and privacy_records[0]["private_path_public_bool"] is False and privacy_records[0]["gold_path_public_bool"] is False),
        check("no_execution", noexec_ok and noexec_records[0]["private_span_input_read_count"] == 1 and noexec_records[0]["other_private_file_read_count"] == 0 and noexec_records[0]["n10t_code_call_count"] == 0),
        check("handoff", n10w_handoff_records(True)[0]["n10w_replication_package_authorized_bool"] is True and n10w_handoff_records(True)[0]["broad_private_read_authorized_bool"] is False),
        check("status_expected", status_for(True, True, "pass", True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10V independent recompute N1 span-surface proxy")
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
    rec = report["independent_recompute_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, best_top10={rec['best_top10_file_reach_count']})")


if __name__ == "__main__":
    main()
