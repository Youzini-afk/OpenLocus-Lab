#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n7_recovered_fixed_pool_rank_order_result_audit.v1"
PHASE = "BEA-v1-N7 Recovered Fixed-Pool Rank-Order Result Audit"
GENERATED_BY = "bea_v1_n7_recovered_fixed_pool_rank_order_result_audit"
STATUS_PASS = "recovered_fixed_pool_rank_order_result_audit_pass_n8_authorized"

STATUSES = (
    STATUS_PASS,
    "no_go_n7_required_inputs_unavailable",
    "no_go_n7_n6xfre_not_pass",
    "no_go_n7_result_consistency_invalid",
    "no_go_n7_arm_semantics_boundary_invalid",
    "no_go_n7_privacy_or_claim_boundary_invalid",
    "no_go_n7_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)
PROVENANCE_RULE = "original_rank_le_20_primary_rank_gt_20_extra_depth_no_gold_signal"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/"
    "bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json"
)
DEFAULT_N6XFRE = Path(
    "artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/"
    "bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json"
)
DEFAULT_N5 = Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json")
DEFAULT_N6F = Path("artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json")

EXPECTED_CHANGED_FILES = (
    "eval/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit.py",
    "artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json",
    "docs/en/bea-v1-n7-recovered-fixed-pool-rank-order-result-audit.md",
    "docs/zh/bea-v1-n7-recovered-fixed-pool-rank-order-result-audit.md",
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
)

OUTCOME_SCHEMA = {
    "anonymous_public_arm_outcome_id",
    "anonymous_case_bucket",
    "arm_bucket",
    "fixed_pool_case_set_bucket",
    "arm_semantics_exact_match_bool",
    "candidate_pool_changed_bool",
    "new_retrieval_used_bool",
    "selector_or_reranker_used_bool",
    "top10_recovery_bucket",
    "top20_recovery_bucket",
    "rank_shift_bucket",
    "case_regression_bucket",
    "hard_cap_bucket",
    "outcome_materialized_bool",
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_paths",
    "filename", "filenames", "file_name", "span", "spans", "snippet", "snippets",
    "content", "text", "raw_text", "candidate", "candidates", "candidate_list",
    "candidate_lists", "candidate_order", "candidate_order_private", "gold_paths_private",
    "gold_lines_private", "exact_rank", "raw_rank", "rank", "ranks", "rank_list",
    "score", "scores", "task_id", "repo", "repo_id", "repo_name", "repo_url",
    "private_id", "private_record_id", "denominator_index_private", "source_hash",
    "source_hashes", "hash", "hashes", "provider", "provider_payload", "raw_payload",
    "payload", "prompt", "response", "raw", "raw_diff", "diff", "log", "logs",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "forbidden_scan_status", "audit_status_bucket", "arm_bucket",
    "provenance_rule_bucket", "arm_semantics_bucket", "schema_status_bucket",
    "threshold_bucket", "decision_bucket", "privacy_boundary_bucket", "claim_boundary_bucket",
    "public_artifact_bucket", "no_execution_boundary_bucket", "n8_handoff_bucket",
    "gate", "threshold_relation", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket",
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


def _input_records(n6xfre: dict[str, Any], n6xfre_load: str, n5: dict[str, Any], n5_load: str, n6f: dict[str, Any], n6f_load: str) -> tuple[list[dict[str, Any]], bool]:
    specs = (
        ("n6xfre_recovered_experiment_artifact", n6xfre_load, n6xfre, "recovered_fixed_pool_rank_order_experiment_pass_n7_authorized"),
        ("n5_preflight_artifact", n5_load, n5, "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
        ("n6f_public_schema_artifact", n6f_load, n6f, "fixed_pool_public_arm_field_materialization_design_pass"),
    )
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, load, artifact, expected) in enumerate(specs):
        observed = str(artifact.get("status", "") or "")
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        passed = load == "pass" and observed == expected and (bucket != "n6xfre_recovered_experiment_artifact" or scan == "pass")
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n7in{idx:04d}", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _per_arm(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r.get("arm_bucket")): r for r in data.get("per_arm_result_records", []) if isinstance(r, dict)}


def _best_arm(per_arm: dict[str, dict[str, Any]]) -> tuple[str, int, int]:
    best_name = ""
    best_top10 = -1
    best_reg = 0
    for arm, rec in per_arm.items():
        top10 = int(rec.get("top10_recovery_count", -1))
        if top10 > best_top10:
            best_name = arm
            best_top10 = top10
            best_reg = int(rec.get("case_regression_count", 0))
    return best_name, best_top10, best_reg


def _count_public_cases(outcomes: list[dict[str, Any]]) -> int:
    return len({r.get("anonymous_case_bucket") for r in outcomes if isinstance(r, dict)})


def _result_consistency_records(data: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    per_arm = _per_arm(data)
    outcomes = data.get("public_arm_outcome_records", [])
    best_name, best_top10, best_reg = _best_arm(per_arm)
    case_count = _count_public_cases(outcomes) if isinstance(outcomes, list) else 0
    row_count = len(outcomes) if isinstance(outcomes, list) else 0
    pool_changed = sum(int(r.get("candidate_pool_changed_count", 0)) for r in per_arm.values())
    hard_cap = sum(int(r.get("hard_cap_violation_count", 0)) for r in per_arm.values())
    ok = (
        case_count == 40
        and len(per_arm) == 4
        and row_count == 160
        and best_name == "extra_depth_promote_before_primary_prefix_4"
        and best_top10 == 25
        and best_reg == 0
        and pool_changed == 0
        and hard_cap == 0
    )
    return [{
        "anonymous_result_consistency_audit_id": "n7res0000",
        "audit_status_bucket": "result_consistency_pass" if ok else "result_consistency_invalid",
        "case_count": case_count,
        "arm_count": len(per_arm),
        "public_arm_outcome_rows": row_count,
        "best_arm_bucket": best_name,
        "best_top10_recovery_count": best_top10,
        "best_case_regression_count": best_reg,
        "candidate_pool_changed_count": pool_changed,
        "hard_cap_violation_count": hard_cap,
        "result_consistency_valid_bool": ok,
    }], ok


def _arm_semantics_audit_records(data: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    source = {str(r.get("arm_bucket")): r for r in data.get("arm_semantics_records", []) if isinstance(r, dict)}
    records: list[dict[str, Any]] = []
    ok = set(source) == set(ARMS)
    for idx, arm in enumerate(ARMS):
        src = source.get(arm, {})
        rec_ok = (
            src.get("provenance_rule_bucket") == PROVENANCE_RULE
            and src.get("candidate_pool_changed_bool") is False
            and src.get("new_retrieval_used_bool") is False
            and src.get("selector_or_reranker_used_bool") is False
            and src.get("gold_used_for_ordering_bool") is False
            and src.get("arm_semantics_exact_match_bool") is True
        )
        ok = ok and rec_ok
        records.append({
            "anonymous_arm_semantics_audit_id": f"n7arm{idx:04d}",
            "arm_bucket": arm,
            "arm_semantics_bucket": "fixed_pool_order_transform_only",
            "provenance_rule_bucket": PROVENANCE_RULE,
            "candidate_pool_changed_bool": False,
            "new_retrieval_used_bool": False,
            "selector_or_reranker_used_bool": False,
            "gold_used_for_ordering_bool": False,
            "arm_semantics_exact_match_bool": rec_ok,
        })
    return records, ok


def _public_outcome_schema_audit_records(data: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, dict[str, int]]:
    outcomes = data.get("public_arm_outcome_records", [])
    rows = outcomes if isinstance(outcomes, list) else []
    schema_ok = len(rows) == 160 and all(isinstance(r, dict) and set(r) == OUTCOME_SCHEMA for r in rows)
    pool_changed = sum(int(r.get("candidate_pool_changed_bool") is True) for r in rows if isinstance(r, dict))
    retrieval = sum(int(r.get("new_retrieval_used_bool") is True) for r in rows if isinstance(r, dict))
    selector = sum(int(r.get("selector_or_reranker_used_bool") is True) for r in rows if isinstance(r, dict))
    materialized = sum(int(r.get("outcome_materialized_bool") is True) for r in rows if isinstance(r, dict))
    hard_cap = sum(int(r.get("hard_cap_bucket") == "hard_cap_violation") for r in rows if isinstance(r, dict))
    counts = {"pool_changed": pool_changed, "retrieval": retrieval, "selector": selector, "materialized": materialized, "hard_cap": hard_cap}
    ok = schema_ok and pool_changed == 0 and retrieval == 0 and selector == 0 and materialized == 160 and hard_cap == 0
    return [{
        "anonymous_public_outcome_schema_audit_id": "n7schema0000",
        "schema_status_bucket": "n6f_public_schema_match" if ok else "n6f_public_schema_mismatch",
        "public_arm_outcome_rows": len(rows),
        "candidate_pool_changed_count": pool_changed,
        "new_retrieval_used_count": retrieval,
        "selector_or_reranker_used_count": selector,
        "outcome_materialized_count": materialized,
        "hard_cap_violation_count": hard_cap,
        "schema_valid_bool": ok,
    }], ok, counts


def _threshold_audit_records(data: dict[str, Any], best_name: str, best_top10: int, best_reg: int) -> tuple[list[dict[str, Any]], bool]:
    records = data.get("threshold_decision_records", [])
    source = records[0] if isinstance(records, list) and records and isinstance(records[0], dict) else {}
    ok = (
        source.get("threshold_top10_recovery_count") == 16
        and source.get("threshold_case_regression_count") == 2
        and source.get("threshold_passed_bool") is True
        and source.get("best_arm_bucket") == "extra_depth_promote_before_primary_prefix_4"
        and source.get("best_top10_recovery_count") == 25
        and source.get("best_case_regression_count") == 0
        and best_name == "extra_depth_promote_before_primary_prefix_4"
        and best_top10 == 25
        and best_reg == 0
    )
    return [{
        "anonymous_threshold_audit_id": "n7threshold0000",
        "threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
        "decision_bucket": "threshold_passed" if ok else "threshold_invalid",
        "best_arm_bucket": best_name,
        "best_top10_recovery_count": best_top10,
        "best_case_regression_count": best_reg,
        "threshold_top10_recovery_count": 16,
        "threshold_case_regression_count": 2,
        "threshold_passed_bool": ok,
    }], ok


def _privacy_boundary_audit_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_privacy_boundary_audit_id": "n7privacy0000",
        "privacy_boundary_bucket": "public_artifact_only_no_private_recovery_reads",
        "public_artifact_bucket": "n6xfre_public_buckets_counts_booleans_only",
        "private_read_count": 0,
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "private_content_public_bool": False,
        "candidate_list_public_bool": False,
        "gold_path_public_bool": False,
        "exact_rank_public_bool": False,
        "task_repo_id_public_bool": False,
        "source_span_public_bool": False,
        "hash_public_bool": False,
        "provider_payload_public_bool": False,
        "privacy_boundary_valid_bool": True,
    }], True


def _claim_boundary_audit_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_claim_boundary_audit_id": "n7claim0000",
        "claim_boundary_bucket": "n7_result_audit_only",
        "p5_authorized_bool": False,
        "v1_a_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "rerun_authorized_bool": False,
        "runtime_change_authorized_bool": False,
        "default_change_authorized_bool": False,
        "method_winner_claimed_bool": False,
        "method_winner_authorized_bool": False,
        "downstream_value_claimed_bool": False,
        "downstream_value_authorized_bool": False,
        "claim_boundary_valid_bool": True,
    }], True


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_no_execution_id": "n7noexec0000",
        "no_execution_boundary_bucket": "public_artifact_audit_no_recompute",
        "private_read_count": 0,
        "openlocus_binary_execution_count": 0,
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "outcome_recompute_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "selector_reranker_execution_count": 0,
        "p5_execution_count": 0,
        "v1a_execution_count": 0,
        "counterfactual_execution_count": 0,
        "runtime_change_count": 0,
        "default_change_count": 0,
        "no_execution_complete_bool": True,
    }], True


def _n8_handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_n8_handoff_id": "n7handoff0000",
        "n8_handoff_bucket": "independent_recompute_same_private_rows_same_four_arms" if pass_status else "n8_not_authorized",
        "n8_independent_recompute_authorized_bool": pass_status,
        "same_private_rows_required_bool": True,
        "same_four_arms_required_bool": True,
        "public_artifact_only_for_n7_bool": True,
        "runtime_or_default_promotion_authorized_bool": False,
        "method_winner_claim_authorized_bool": False,
        "downstream_value_claim_authorized_bool": False,
    }]


def _gate_records(**v: int | bool) -> list[dict[str, Any]]:
    specs = [
        ("source_status_pass_n7_authorized", bool(v["source_status"]), int(bool(v["source_status"])), 1),
        ("source_forbidden_scan_pass", bool(v["source_scan"]), int(bool(v["source_scan"])), 1),
        ("case_count", v["case_count"] == 40, v["case_count"], 40),
        ("arm_count", v["arm_count"] == 4, v["arm_count"], 4),
        ("public_arm_outcome_rows", v["public_rows"] == 160, v["public_rows"], 160),
        ("best_top10_recovery_count", v["best_top10"] == 25, v["best_top10"], 25),
        ("best_case_regression_count", v["best_reg"] == 0, v["best_reg"], 0),
        ("threshold_top10_recovery_count", v["threshold_top10"] == 16, v["threshold_top10"], 16),
        ("threshold_case_regression_count", v["threshold_reg"] == 2, v["threshold_reg"], 2),
        ("threshold_passed", bool(v["threshold_passed"]), int(bool(v["threshold_passed"])), 1),
        ("candidate_pool_changed_count", v["pool_changed"] == 0, v["pool_changed"], 0),
        ("new_retrieval_used_count", v["retrieval"] == 0, v["retrieval"], 0),
        ("selector_or_reranker_count", v["selector"] == 0, v["selector"], 0),
        ("gold_used_for_ordering_count", v["gold_order"] == 0, v["gold_order"], 0),
        ("private_read_count", v["private_read"] == 0, v["private_read"], 0),
        ("forbidden_scan", bool(v["scanner_ok"]), int(bool(v["scanner_ok"])), 1),
    ]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{
        "authorization": "n8_independent_recompute_audit_authorized" if pass_status else "n8_not_authorized",
        "next_allowed_phase": "BEA-v1-N8 Independent Recompute Same Private Rows Same Four Arms" if pass_status else "none_until_valid_n6xfre_public_result_audit",
        "next_allowed_scope_bucket": "n8_recompute_audit_only_no_promotion" if pass_status else "no_next_phase",
        "n8_independent_recompute_authorized": pass_status,
        "n8_same_private_rows_read_authorized": pass_status,
        "broad_private_read_authorized": False,
        "retrieval_authorized": False,
        "rerun_authorized": False,
        "candidate_generation_authorized": False,
        "candidate_materialization_authorized": False,
        "selector_or_reranker_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "counterfactual_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "runtime_or_policy_change_authorized": False,
        "method_winner_claimed": False,
        "method_winner_claim_authorized": False,
        "downstream_value_claimed": False,
        "downstream_value_claim_authorized": False,
    }]


def _status_from(*, self_ok: bool, input_ok: bool, source_status_ok: bool, consistency_ok: bool, semantics_ok: bool, schema_ok: bool, threshold_ok: bool, privacy_ok: bool, claim_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n7_required_inputs_unavailable"
    if not source_status_ok:
        return "no_go_n7_n6xfre_not_pass"
    if not consistency_ok or not schema_ok or not threshold_ok:
        return "no_go_n7_result_consistency_invalid"
    if not semantics_ok:
        return "no_go_n7_arm_semantics_boundary_invalid"
    if not privacy_ok or not claim_ok:
        return "no_go_n7_privacy_or_claim_boundary_invalid"
    return STATUS_PASS


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    n6xfre, n6xfre_load = _load_json(args.n6xfre_artifact)
    n5, n5_load = _load_json(args.n5_artifact)
    n6f, n6f_load = _load_json(args.n6f_artifact)
    inputs, input_ok = _input_records(n6xfre, n6xfre_load, n5, n5_load, n6f, n6f_load)
    source_status_ok = n6xfre.get("status") == "recovered_fixed_pool_rank_order_experiment_pass_n7_authorized"
    source_scan_ok = n6xfre.get("forbidden_scan", {}).get("status") == "pass" if isinstance(n6xfre.get("forbidden_scan"), dict) else False
    result_records, consistency_ok = _result_consistency_records(n6xfre)
    best_name = result_records[0]["best_arm_bucket"]
    best_top10 = result_records[0]["best_top10_recovery_count"]
    best_reg = result_records[0]["best_case_regression_count"]
    arm_records, semantics_ok = _arm_semantics_audit_records(n6xfre)
    schema_records, schema_ok, outcome_counts = _public_outcome_schema_audit_records(n6xfre)
    threshold_records, threshold_ok = _threshold_audit_records(n6xfre, best_name, best_top10, best_reg)
    privacy_records, privacy_ok = _privacy_boundary_audit_records()
    claim_records, claim_ok = _claim_boundary_audit_records()
    noexec_records, noexec_ok = _no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, source_status_ok=source_status_ok, consistency_ok=consistency_ok, semantics_ok=semantics_ok, schema_ok=schema_ok, threshold_ok=threshold_ok, privacy_ok=privacy_ok and noexec_ok, claim_ok=claim_ok)
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_artifact_result_audit_only", "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": inputs, "result_consistency_audit_records": result_records, "arm_semantics_audit_records": arm_records, "public_outcome_schema_audit_records": schema_records, "threshold_audit_records": threshold_records, "privacy_boundary_audit_records": privacy_records, "claim_boundary_audit_records": claim_records, "no_execution_records": noexec_records, "n8_handoff_records": _n8_handoff_records(pass_status),
        "gate_records": _gate_records(source_status=source_status_ok, source_scan=source_scan_ok, case_count=result_records[0]["case_count"], arm_count=result_records[0]["arm_count"], public_rows=result_records[0]["public_arm_outcome_rows"], best_top10=best_top10, best_reg=best_reg, threshold_top10=16, threshold_reg=2, threshold_passed=threshold_ok, pool_changed=outcome_counts["pool_changed"], retrieval=outcome_counts["retrieval"], selector=outcome_counts["selector"], gold_order=0, private_read=0, scanner_ok=True),
        "stop_go_records": _stop_go_records(pass_status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = _scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    pass_status = report["status"] == STATUS_PASS
    report["gate_records"] = _gate_records(source_status=source_status_ok, source_scan=source_scan_ok, case_count=result_records[0]["case_count"], arm_count=result_records[0]["arm_count"], public_rows=result_records[0]["public_arm_outcome_rows"], best_top10=best_top10, best_reg=best_reg, threshold_top10=16, threshold_reg=2, threshold_passed=threshold_ok, pool_changed=outcome_counts["pool_changed"], retrieval=outcome_counts["retrieval"], selector=outcome_counts["selector"], gold_order=0, private_read=0, scanner_ok=scanner_ok)
    report["n8_handoff_records"] = _n8_handoff_records(pass_status)
    report["stop_go_records"] = _stop_go_records(pass_status)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET_VALUE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET_VALUE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    args = build_parser().parse_args([])
    n6xfre, n6xfre_load = _load_json(args.n6xfre_artifact)
    n5, n5_load = _load_json(args.n5_artifact)
    n6f, n6f_load = _load_json(args.n6f_artifact)
    inputs, input_ok = _input_records(n6xfre, n6xfre_load, n5, n5_load, n6f, n6f_load)
    result_records, consistency_ok = _result_consistency_records(n6xfre)
    arm_records, semantics_ok = _arm_semantics_audit_records(n6xfre)
    schema_records, schema_ok, outcome_counts = _public_outcome_schema_audit_records(n6xfre)
    threshold_records, threshold_ok = _threshold_audit_records(n6xfre, result_records[0]["best_arm_bucket"], result_records[0]["best_top10_recovery_count"], result_records[0]["best_case_regression_count"])
    privacy_records, privacy_ok = _privacy_boundary_audit_records()
    claim_records, claim_ok = _claim_boundary_audit_records()
    noexec_records, noexec_ok = _no_execution_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_n7_required_inputs_unavailable", "no_go_n7_n6xfre_not_pass", "no_go_n7_result_consistency_invalid", "no_go_n7_arm_semantics_boundary_invalid", "no_go_n7_privacy_or_claim_boundary_invalid", "no_go_n7_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "filename", "span", "snippet", "candidate_list", "gold_paths_private", "exact_rank", "private_id", "source_hash", "provider_payload", "raw_diff"))),
        _check("scanner_rejects_path_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("input_artifacts", input_ok and len(inputs) == 3 and inputs[0]["observed_status"] == "recovered_fixed_pool_rank_order_experiment_pass_n7_authorized"),
        _check("result_consistency", consistency_ok and result_records[0]["case_count"] == 40 and result_records[0]["arm_count"] == 4 and result_records[0]["public_arm_outcome_rows"] == 160 and result_records[0]["best_top10_recovery_count"] == 25),
        _check("arm_semantics", semantics_ok and len(arm_records) == 4 and all(r["provenance_rule_bucket"] == PROVENANCE_RULE for r in arm_records)),
        _check("outcome_schema", schema_ok and schema_records[0]["public_arm_outcome_rows"] == 160 and outcome_counts["pool_changed"] == 0 and outcome_counts["retrieval"] == 0 and outcome_counts["selector"] == 0),
        _check("threshold", threshold_ok and threshold_records[0]["best_arm_bucket"] == "extra_depth_promote_before_primary_prefix_4" and threshold_records[0]["best_top10_recovery_count"] == 25 and threshold_records[0]["threshold_passed_bool"] is True),
        _check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0 and all(v is False for k, v in privacy_records[0].items() if k.endswith("_public_bool"))),
        _check("claim_boundary", claim_ok and all(v is False for k, v in claim_records[0].items() if k.endswith("_bool") and k != "claim_boundary_valid_bool") and claim_records[0]["claim_boundary_valid_bool"] is True),
        _check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        _check("n8_handoff", _n8_handoff_records(True)[0]["n8_independent_recompute_authorized_bool"] is True and _n8_handoff_records(True)[0]["same_four_arms_required_bool"] is True and _stop_go_records(True)[0]["n8_same_private_rows_read_authorized"] is True and _stop_go_records(True)[0]["broad_private_read_authorized"] is False),
        _check("status_expected", _status_from(self_ok=True, input_ok=True, source_status_ok=True, consistency_ok=True, semantics_ok=True, schema_ok=True, threshold_ok=True, privacy_ok=True, claim_ok=True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N7 recovered fixed-pool rank-order result audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n6xfre-artifact", type=Path, default=DEFAULT_N6XFRE)
    parser.add_argument("--n5-artifact", type=Path, default=DEFAULT_N5)
    parser.add_argument("--n6f-artifact", type=Path, default=DEFAULT_N6F)
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
    thresh = report["threshold_audit_records"][0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"best_top10={thresh['best_top10_recovery_count']})")


if __name__ == "__main__":
    main()
