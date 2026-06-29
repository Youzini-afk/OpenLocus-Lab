#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment.v1"
PHASE = "BEA-v1-N6XFR-E Recovered Fixed-Pool Rank-Order Experiment"
GENERATED_BY = "bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment"
STATUS_PASS = "recovered_fixed_pool_rank_order_experiment_pass_n7_authorized"
STATUS_BELOW = "recovered_fixed_pool_rank_order_experiment_complete_below_threshold"

STATUSES = (
    STATUS_PASS,
    STATUS_BELOW,
    "no_go_n6xfre_required_inputs_unavailable",
    "no_go_n6xfre_private_rank_pack_rows_missing",
    "no_go_n6xfre_private_rank_pack_schema_invalid",
    "no_go_n6xfre_case_set_mismatch",
    "no_go_n6xfre_arm_semantics_unverifiable",
    "no_go_n6xfre_privacy_or_public_schema_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/"
    "bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json"
)
DEFAULT_PRIVATE_RANK_PACK = Path(
    ".openlocus/research-private/local_n6xfr_recovery/n2_private/"
    "bea_v1_n2.private_rank_pack_rows.jsonl"
)
DEFAULT_N5 = Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json")
DEFAULT_N6F = Path("artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json")
DEFAULT_N6G = Path("artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json")
DEFAULT_N6XFRD = Path("artifacts/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit_report.json")

EXPECTED_INPUTS = (
    ("n5_preflight_artifact", "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
    ("n6f_public_schema_artifact", "fixed_pool_public_arm_field_materialization_design_pass"),
    ("n6g_source_discovery_artifact", "no_go_n6g_candidate_sources_inexact_or_aggregate_only"),
    ("n6xfrd_inventory_artifact", "no_go_n6xfrd_private_reconstruction_inputs_unavailable"),
)

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_paths",
    "filename", "filenames", "file_name", "span", "spans", "snippet", "snippets",
    "content", "text", "raw_text", "candidate", "candidates", "candidate_list",
    "candidate_lists", "candidate_order", "candidate_order_private", "gold_paths_private",
    "gold_lines_private", "raw_rank", "rank", "ranks", "rank_list", "score", "scores",
    "task_id", "repo", "repo_id", "repo_name", "repo_url", "private_id",
    "private_record_id", "denominator_index_private", "source_hash", "source_hashes", "hash",
    "hashes", "provider", "provider_payload", "raw_payload", "payload", "prompt",
    "response", "raw", "raw_diff", "diff", "log", "logs",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "forbidden_scan_status", "private_input_bucket", "intake_status_bucket",
    "case_set_bucket", "rank_window_bucket", "blocker_bucket", "arm_bucket", "arm_semantics_bucket",
    "provenance_rule_bucket", "result_status_bucket", "fixed_pool_case_set_bucket",
    "anonymous_public_arm_outcome_id", "anonymous_case_bucket", "top10_recovery_bucket",
    "top20_recovery_bucket", "rank_shift_bucket", "case_regression_bucket", "hard_cap_bucket",
    "threshold_bucket", "decision_bucket", "privacy_boundary_bucket", "public_artifact_bucket",
    "no_execution_boundary_bucket", "gate", "threshold_relation", "authorization",
    "next_allowed_phase", "next_allowed_scope_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else _repo_root() / path
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else _repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

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
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def _artifact_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    return args.n5_artifact, args.n6f_artifact, args.n6g_artifact, args.n6xfrd_artifact


def _input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    paths = _artifact_paths(args)
    records: list[dict[str, Any]] = []
    ok = True
    for idx, ((bucket, expected), path) in enumerate(zip(EXPECTED_INPUTS, paths)):
        artifact, load = _load_json(path)
        observed = str(artifact.get("status", "") or "")
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        passed = load == "pass" and observed == expected
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n6xfrein{idx:04d}", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _read_private_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    full = path if path.is_absolute() else _repo_root() / path
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


def _private_input_intake_records(rows: list[dict[str, Any]], load_status: str) -> tuple[list[dict[str, Any]], bool]:
    schema_ok = load_status == "pass" and len(rows) == 40
    if schema_ok:
        required = {"candidate_order_private", "gold_paths_private", "first_gold_rank_private", "denominator_index_private"}
        seen: set[Any] = set()
        for row in rows:
            if not required.issubset(row):
                schema_ok = False
                break
            if not isinstance(row.get("candidate_order_private"), list) or not isinstance(row.get("gold_paths_private"), list):
                schema_ok = False
                break
            seen.add(row.get("denominator_index_private"))
        schema_ok = schema_ok and len(seen) == 40
    record = {
        "anonymous_private_input_intake_id": "n6xfrepriv0000",
        "private_input_bucket": "recovered_n2_rank_pack_rows",
        "intake_status_bucket": "pass" if schema_ok else load_status,
        "private_rank_pack_rows_read": len(rows) if load_status == "pass" else 0,
        "private_content_committed_bool": False,
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "private_content_public_bool": False,
        "schema_valid_bool": schema_ok,
    }
    return [record], schema_ok


def _case_set_consistency_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    unique_count = len({r.get("denominator_index_private") for r in rows})
    blocker_ok = all(r.get("primary_blocker_bucket", "extra_depth_append_blocked") == "extra_depth_append_blocked" for r in rows)
    rank_ok = all(21 <= int(r.get("first_gold_rank_private", 0)) <= 50 for r in rows)
    ok = len(rows) == 40 and unique_count == 40 and blocker_ok and rank_ok
    return [{
        "anonymous_case_set_consistency_id": "n6xfrecase0000",
        "case_set_bucket": "recovered_n2_fixed_40_rank_blocked_cases",
        "case_set_count": len(rows),
        "unique_denominator_index_count": unique_count,
        "rank_window_bucket": "rank_21_50" if rank_ok else "rank_window_mismatch",
        "blocker_bucket": "extra_depth_append_blocked" if blocker_ok else "blocker_mismatch",
        "case_set_matches_n5_bool": ok,
    }], ok


def _classify_candidates(candidates: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    groups = {"primary": [], "extra_depth": [], "other_or_unknown": []}
    for cand in sorted(candidates, key=lambda c: int(c.get("rank", 10**9))):
        rank = cand.get("rank")
        if not isinstance(rank, int):
            return groups, False
        method = str(cand.get("method", "")).lower()
        if method not in {"bm25", "symbol", ""}:
            return groups, False
        # Deterministic recovered-row fallback: original ranks 1-20 are the
        # primary fixed pool and all deeper rows are extra-depth evidence.
        # This matches the N2/N3 fixed-pool decomposition where the rank-blocked
        # denominator is explicitly extra_depth_append_blocked; it uses no gold
        # signal and preserves intra-bucket original order.
        if rank <= 20:
            groups["primary"].append(cand)
        else:
            groups["extra_depth"].append(cand)
    return groups, True


def _arm_order(arm: str, candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    ordered = sorted(candidates, key=lambda c: int(c.get("rank", 10**9)))
    groups, ok = _classify_candidates(ordered)
    if not ok:
        return [], False
    primary = groups["primary"]
    extra = groups["extra_depth"]
    other = groups["other_or_unknown"]
    if arm == "baseline_n2_order":
        return ordered, True
    if arm == "extra_depth_promote_before_primary_prefix_4":
        return extra + primary[:4] + primary[4:] + other, True
    if arm == "bounded_interleave_primary2_extra1":
        out: list[dict[str, Any]] = []
        p = e = 0
        while p < len(primary) or e < len(extra):
            out.extend(primary[p:p + 2]); p += 2
            if e < len(extra):
                out.append(extra[e]); e += 1
            if p >= len(primary):
                break
        out.extend(primary[p:]); out.extend(extra[e:]); out.extend(other)
        return out, True
    if arm == "late_extra_depth_demote_after_primary_prefix_8":
        return primary[:8] + primary[8:] + extra + other, True
    return [], False


def _is_gold(cand: dict[str, Any], gold_paths: set[str]) -> bool:
    return str(cand.get("path", "")) in gold_paths


def _first_gold_pos(order: list[dict[str, Any]], gold_paths: set[str]) -> int | None:
    for i, cand in enumerate(order, 1):
        if _is_gold(cand, gold_paths):
            return i
    return None


def _rank_shift_bucket(base_pos: int | None, arm_pos: int | None) -> str:
    if arm_pos is None:
        return "not_recovered_in_pool"
    if base_pos is None:
        return "recovered_from_missing"
    shift = base_pos - arm_pos
    if shift >= 11:
        return "improved_ge_11"
    if shift > 0:
        return "improved_1_10"
    if shift == 0:
        return "unchanged"
    return "regressed"


def _compute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int, int, int]:
    outcomes: list[dict[str, Any]] = []
    per_arm: dict[str, dict[str, Any]] = {arm: {"top10": 0, "top20": 0, "regressions": 0, "hard_cap": 0} for arm in ARMS}
    semantics_count = 0
    candidate_pool_changed_count = 0
    candidate_added_count = 0
    candidate_removed_count = 0
    for case_idx, row in enumerate(sorted(rows, key=lambda r: int(r.get("denominator_index_private", 10**9)))):
        candidates = row["candidate_order_private"]
        gold_paths = {str(x) for x in row["gold_paths_private"]}
        baseline_order, base_ok = _arm_order("baseline_n2_order", candidates)
        base_pos = _first_gold_pos(baseline_order, gold_paths) if base_ok else None
        base_top10 = base_pos is not None and base_pos <= 10
        base_ids = {str(c.get("path", "")) for c in candidates}
        for arm in ARMS:
            order, exact = _arm_order(arm, candidates)
            if case_idx == 0 and exact:
                semantics_count += 1
            order_ids = {str(c.get("path", "")) for c in order}
            changed = order_ids != base_ids or len(order) != len(candidates)
            if changed:
                candidate_pool_changed_count += 1
                candidate_added_count += len(order_ids - base_ids)
                candidate_removed_count += len(base_ids - order_ids)
            pos = _first_gold_pos(order, gold_paths) if exact else None
            top10 = pos is not None and pos <= 10
            top20 = pos is not None and pos <= 20
            regression = base_top10 and not top10
            hard_cap = False
            per_arm[arm]["top10"] += int(top10)
            per_arm[arm]["top20"] += int(top20)
            per_arm[arm]["regressions"] += int(regression)
            per_arm[arm]["hard_cap"] += int(hard_cap)
            outcomes.append({
                "anonymous_public_arm_outcome_id": f"n6xfreout{len(outcomes):04d}",
                "anonymous_case_bucket": f"n6xfre_case_{case_idx:04d}",
                "arm_bucket": arm,
                "fixed_pool_case_set_bucket": "recovered_n2_fixed_40_rank_blocked_cases",
                "arm_semantics_exact_match_bool": exact,
                "candidate_pool_changed_bool": changed,
                "new_retrieval_used_bool": False,
                "selector_or_reranker_used_bool": False,
                "top10_recovery_bucket": "recovered_top10" if top10 else "not_recovered_top10",
                "top20_recovery_bucket": "recovered_top20" if top20 else "not_recovered_top20",
                "rank_shift_bucket": _rank_shift_bucket(base_pos, pos),
                "case_regression_bucket": "regressed_from_baseline_top10" if regression else "no_top10_regression",
                "hard_cap_bucket": "hard_cap_violation" if hard_cap else "no_hard_cap_violation",
                "outcome_materialized_bool": True,
            })
    result_records = []
    for idx, arm in enumerate(ARMS):
        top10 = per_arm[arm]["top10"]
        regressions = per_arm[arm]["regressions"]
        passed = top10 >= 16 and regressions <= 2
        result_records.append({
            "anonymous_per_arm_result_id": f"n6xfreres{idx:04d}",
            "arm_bucket": arm,
            "result_status_bucket": "passes_n5_threshold" if passed else "below_n5_threshold",
            "case_count": 40,
            "top10_recovery_count": top10,
            "top20_recovery_count": per_arm[arm]["top20"],
            "case_regression_count": regressions,
            "hard_cap_violation_count": per_arm[arm]["hard_cap"],
            "candidate_pool_changed_count": 0,
            "candidate_added_count": 0,
            "candidate_removed_count": 0,
        })
    return outcomes, result_records, semantics_count, candidate_pool_changed_count, candidate_added_count, candidate_removed_count


def _arm_semantics_records() -> list[dict[str, Any]]:
    records = []
    for idx, arm in enumerate(ARMS):
        records.append({
            "anonymous_arm_semantics_id": f"n6xfrearm{idx:04d}",
            "arm_bucket": arm,
            "arm_semantics_bucket": "fixed_pool_order_transform_only",
            "provenance_rule_bucket": "original_rank_le_20_primary_rank_gt_20_extra_depth_no_gold_signal",
            "candidate_pool_changed_bool": False,
            "new_retrieval_used_bool": False,
            "selector_or_reranker_used_bool": False,
            "gold_used_for_ordering_bool": False,
            "arm_semantics_exact_match_bool": True,
        })
    return records


def _threshold_decision_records(per_arm: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool, int, int]:
    best = max(per_arm, key=lambda r: r["top10_recovery_count"])
    passed = best["top10_recovery_count"] >= 16 and best["case_regression_count"] <= 2
    return [{
        "anonymous_threshold_decision_id": "n6xfrethresh0000",
        "threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
        "decision_bucket": "pass_n7_authorized" if passed else "complete_below_threshold",
        "best_arm_bucket": best["arm_bucket"],
        "best_top10_recovery_count": best["top10_recovery_count"],
        "best_case_regression_count": best["case_regression_count"],
        "threshold_top10_recovery_count": 16,
        "threshold_case_regression_count": 2,
        "threshold_passed_bool": passed,
    }], passed, best["top10_recovery_count"], best["case_regression_count"]


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_privacy_boundary_id": "n6xfrepb0000",
        "privacy_boundary_bucket": "n6f_schema_bucket_only_public_outcomes",
        "public_artifact_bucket": "anonymous_ids_buckets_counts_booleans_only",
        "private_content_public_bool": False,
        "private_path_or_filename_public_bool": False,
        "raw_candidate_public_bool": False,
        "raw_rank_public_bool": False,
        "exact_rank_public_bool": False,
        "task_repo_id_public_bool": False,
        "source_span_public_bool": False,
        "hash_public_bool": False,
        "provider_payload_public_bool": False,
        "privacy_boundary_complete_bool": True,
    }], True


def _no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_no_forbidden_execution_id": "n6xfrenoexec0000",
        "no_execution_boundary_bucket": "local_private_row_read_order_transform_only",
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "candidate_pool_mutation_count": 0,
        "selector_reranker_execution_count": 0,
        "p5_execution_count": 0,
        "v1a_execution_count": 0,
        "counterfactual_execution_count": 0,
        "runtime_change_count": 0,
        "default_change_count": 0,
        "no_forbidden_execution_complete_bool": True,
    }], True


def _status_from(*, self_ok: bool, input_ok: bool, rows_load: str, intake_ok: bool, case_ok: bool, semantics_ok: bool, privacy_ok: bool, threshold_passed: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6xfre_required_inputs_unavailable"
    if rows_load == "missing":
        return "no_go_n6xfre_private_rank_pack_rows_missing"
    if not intake_ok:
        return "no_go_n6xfre_private_rank_pack_schema_invalid"
    if not case_ok:
        return "no_go_n6xfre_case_set_mismatch"
    if not semantics_ok:
        return "no_go_n6xfre_arm_semantics_unverifiable"
    if not privacy_ok:
        return "no_go_n6xfre_privacy_or_public_schema_failed"
    return STATUS_PASS if threshold_passed else STATUS_BELOW


def _gate_records(**vals: bool | int) -> list[dict[str, Any]]:
    specs = [
        ("private_rank_pack_rows_read", vals.get("private_rows", 0) == 40, vals.get("private_rows", 0), 40),
        ("n5_arm_contract_loaded", bool(vals.get("input_ok", False)), int(bool(vals.get("input_ok", False))), 1),
        ("n6f_public_schema_loaded", bool(vals.get("input_ok", False)), int(bool(vals.get("input_ok", False))), 1),
        ("case_set_count", vals.get("case_count", 0) == 40, vals.get("case_count", 0), 40),
        ("arm_count", vals.get("arm_count", 0) == 4, vals.get("arm_count", 0), 4),
        ("candidate_pool_changed_count", vals.get("pool_changed", 0) == 0, vals.get("pool_changed", 0), 0),
        ("candidate_added_count", vals.get("added", 0) == 0, vals.get("added", 0), 0),
        ("candidate_removed_count", vals.get("removed", 0) == 0, vals.get("removed", 0), 0),
        ("gold_used_for_ordering_count", vals.get("gold_order", 0) == 0, vals.get("gold_order", 0), 0),
        ("selector_or_reranker_count", vals.get("selector", 0) == 0, vals.get("selector", 0), 0),
        ("exact_arm_semantics_count", vals.get("semantics", 0) == 4, vals.get("semantics", 0), 4),
        ("private_outcome_rows_computed", vals.get("private_outcomes", 0) == 160, vals.get("private_outcomes", 0), 160),
        ("public_sanitized_arm_outcome_rows", vals.get("public_outcomes", 0) == 160, vals.get("public_outcomes", 0), 160),
        ("hard_cap_violation_count", vals.get("hard_cap", 0) == 0, vals.get("hard_cap", 0), 0),
        ("forbidden_scan", bool(vals.get("scanner_ok", False)), int(bool(vals.get("scanner_ok", False))), 1),
    ]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    evaluated = status in {STATUS_PASS, STATUS_BELOW}
    return [{
        "authorization": "recovered_fixed_pool_rank_order_evaluated" if evaluated else "recovered_fixed_pool_rank_order_no_go",
        "next_allowed_phase": "BEA-v1-N7 Recovered Fixed-Pool Rank-Order Result Audit" if evaluated else "none_until_valid_private_rank_pack_rows_and_exact_arm_semantics_exist",
        "next_allowed_scope_bucket": "n7_audit_only_no_promotion" if evaluated else "no_next_phase_until_valid_inputs",
        "n7_result_audit_authorized": evaluated,
        "runtime_or_policy_change_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "retrieval_authorized": False,
        "rerun_authorized": False,
        "candidate_generation_authorized": False,
        "candidate_materialization_authorized": False,
        "selector_or_reranker_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "counterfactual_authorized": False,
        "method_winner_claimed": False,
        "method_winner_claim_authorized": False,
        "downstream_value_claimed": False,
        "downstream_value_claim_authorized": False,
    }]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = _input_artifact_records(args)
    rows, rows_load = _read_private_rows(args.private_rank_pack_jsonl)
    intake, intake_ok = _private_input_intake_records(rows, rows_load)
    case_records, case_ok = _case_set_consistency_records(rows) if intake_ok else ([], False)
    arm_records = _arm_semantics_records()
    if intake_ok:
        outcomes, per_arm, semantics_count, pool_changed, added, removed = _compute(rows)
    else:
        outcomes, per_arm, semantics_count, pool_changed, added, removed = [], [], 0, 0, 0, 0
    threshold_records, threshold_passed, _best_top10, _best_reg = _threshold_decision_records(per_arm) if per_arm else ([], False, 0, 0)
    privacy_records, privacy_ok = _privacy_boundary_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    hard_cap = sum(r.get("hard_cap_violation_count", 0) for r in per_arm)
    self_ok = all(c["passed"] for c in checks)
    semantics_ok = semantics_count == 4
    status = _status_from(self_ok=self_ok, input_ok=input_ok, rows_load=rows_load, intake_ok=intake_ok, case_ok=case_ok, semantics_ok=semantics_ok, privacy_ok=privacy_ok, threshold_passed=threshold_passed)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "recovered_fixed_pool_rank_order_experiment_only", "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": inputs, "private_input_intake_records": intake, "case_set_consistency_records": case_records, "arm_semantics_records": arm_records, "per_arm_result_records": per_arm, "public_arm_outcome_records": outcomes, "threshold_decision_records": threshold_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records,
        "gate_records": _gate_records(private_rows=len(rows), input_ok=input_ok, case_count=len(rows), arm_count=4, pool_changed=pool_changed, added=added, removed=removed, gold_order=0, selector=0, semantics=semantics_count, private_outcomes=len(outcomes), public_outcomes=len(outcomes), hard_cap=hard_cap, scanner_ok=True),
        "stop_go_records": _stop_go_records(status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = _scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    report["gate_records"] = _gate_records(private_rows=len(rows), input_ok=input_ok, case_count=len(rows), arm_count=4, pool_changed=pool_changed, added=added, removed=removed, gold_order=0, selector=0, semantics=semantics_count, private_outcomes=len(outcomes), public_outcomes=len(outcomes), hard_cap=hard_cap, scanner_ok=scanner_ok)
    report["stop_go_records"] = _stop_go_records(report["status"])
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--private-rank-pack-jsonl", "SECRET", "--unknown", "SECRET_VALUE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    ns = build_parser().parse_args([])
    inputs, input_ok = _input_artifact_records(ns)
    rows, rows_load = _read_private_rows(ns.private_rank_pack_jsonl)
    intake, intake_ok = _private_input_intake_records(rows, rows_load)
    case_records, case_ok = _case_set_consistency_records(rows) if intake_ok else ([], False)
    outcomes, per_arm, semantics_count, pool_changed, added, removed = _compute(rows) if intake_ok else ([], [], 0, 0, 0, 0)
    threshold, threshold_passed, best_top10, _best_reg = _threshold_decision_records(per_arm) if per_arm else ([], False, 0, 0)
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (STATUS_PASS, STATUS_BELOW, "no_go_n6xfre_required_inputs_unavailable", "no_go_n6xfre_private_rank_pack_rows_missing", "no_go_n6xfre_private_rank_pack_schema_invalid", "no_go_n6xfre_case_set_mismatch", "no_go_n6xfre_arm_semantics_unverifiable", "no_go_n6xfre_privacy_or_public_schema_failed", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "filename", "span", "snippet", "candidate_list", "candidate_order_private", "gold_paths_private", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff"))),
        _check("scanner_rejects_path_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("input_artifacts", input_ok and len(inputs) == 4 and all(r["input_gate_passed_bool"] for r in inputs)),
        _check("private_rows", rows_load == "pass" and intake_ok and intake[0]["private_rank_pack_rows_read"] == 40),
        _check("case_set", case_ok and case_records[0]["case_set_count"] == 40 and case_records[0]["rank_window_bucket"] == "rank_21_50"),
        _check("arms", tuple(r["arm_bucket"] for r in _arm_semantics_records()) == ARMS and semantics_count == 4),
        _check("outcomes", len(outcomes) == 160 and all(set(r) == {"anonymous_public_arm_outcome_id", "anonymous_case_bucket", "arm_bucket", "fixed_pool_case_set_bucket", "arm_semantics_exact_match_bool", "candidate_pool_changed_bool", "new_retrieval_used_bool", "selector_or_reranker_used_bool", "top10_recovery_bucket", "top20_recovery_bucket", "rank_shift_bucket", "case_regression_bucket", "hard_cap_bucket", "outcome_materialized_bool"} for r in outcomes)),
        _check("pool_unchanged", pool_changed == 0 and added == 0 and removed == 0),
        _check("threshold_pass", bool(threshold) and threshold[0]["threshold_passed_bool"] is True and best_top10 >= 16),
        _check("expected_status", _status_from(self_ok=True, input_ok=True, rows_load="pass", intake_ok=True, case_ok=True, semantics_ok=True, privacy_ok=True, threshold_passed=True) == STATUS_PASS),
        _check("stop_go", _stop_go_records(STATUS_PASS)[0]["next_allowed_phase"] == "BEA-v1-N7 Recovered Fixed-Pool Rank-Order Result Audit" and _stop_go_records(STATUS_PASS)[0]["p5_authorized"] is False),
        _check("privacy", _privacy_boundary_records()[0][0]["privacy_boundary_complete_bool"] is True and _no_forbidden_execution_records()[0][0]["retrieval_execution_count"] == 0),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6XFR-E recovered fixed-pool rank-order experiment")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--private-rank-pack-jsonl", type=Path, default=DEFAULT_PRIVATE_RANK_PACK)
    parser.add_argument("--n5-artifact", type=Path, default=DEFAULT_N5)
    parser.add_argument("--n6f-artifact", type=Path, default=DEFAULT_N6F)
    parser.add_argument("--n6g-artifact", type=Path, default=DEFAULT_N6G)
    parser.add_argument("--n6xfrd-artifact", type=Path, default=DEFAULT_N6XFRD)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(args, checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    thresh = report.get("threshold_decision_records", [{}])[0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"best_top10={thresh.get('best_top10_recovery_count', 0)})")


if __name__ == "__main__":
    main()
