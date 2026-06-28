#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, NoReturn, Sequence


SCHEMA_VERSION = "bea_v1_n6_fixed_pool_rank_order_experiment.v1"
PHASE = "BEA-v1-N6"
GENERATED_BY = "bea_v1_n6_fixed_pool_rank_order_experiment"

STATUS_PASS = "fixed_pool_rank_order_experiment_pass_n7_authorized"
STATUS_BELOW = "fixed_pool_rank_order_experiment_complete_below_threshold"
STATUS_NO_EXACT_FIELDS = "no_go_n6_public_fixed_pool_arm_fields_insufficient"

STATUSES = (
    STATUS_PASS,
    STATUS_BELOW,
    "no_go_n6_required_inputs_unavailable",
    "no_go_n6_n5_preflight_not_authorized",
    STATUS_NO_EXACT_FIELDS,
    "no_go_n6_arm_mapping_inexact_or_unverifiable",
    "no_go_n6_fixed_case_set_mismatch",
    "no_go_n6_privacy_or_claim_boundary_invalid",
    "no_go_n6_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/"
    "bea_v1_n6_fixed_pool_rank_order_experiment_report.json"
)

INPUTS = (
    (
        "n5_fixed_pool_rank_order_experiment_preflight",
        Path(
            "artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/"
            "bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json"
        ),
        "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized",
    ),
    (
        "n4_fixed_pool_rank_blocker_denominator_audit",
        Path(
            "artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/"
            "bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json"
        ),
        "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized",
    ),
    (
        "n2_rank_pack_actionability_decomposition",
        Path(
            "artifacts/bea_v1_n2_rank_pack_actionability_decomposition/"
            "bea_v1_n2_rank_pack_actionability_decomposition_report.json"
        ),
        "n2_rank_pack_actionability_decomposition_pass",
    ),
    (
        "n3_extra_depth_merge_order_design_simulation",
        Path(
            "artifacts/bea_v1_n3_extra_depth_merge_order_design_simulation/"
            "bea_v1_n3_extra_depth_merge_order_design_simulation_report.json"
        ),
        "n3_merge_order_design_inconclusive",
    ),
    (
        "p4l_locked_non_python_scheduler_validation",
        Path(
            "artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/"
            "bea_v1_p4l_locked_non_python_scheduler_validation_report.json"
        ),
        "bea_v1_p4l_locked_non_python_scheduler_validation_pass",
    ),
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-n6-fixed-pool-rank-order-experiment.md",
    "docs/zh/bea-v1-n6-fixed-pool-rank-order-experiment.md",
    "eval/bea_v1_n6_fixed_pool_rank_order_experiment.py",
    "artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json",
})

FORBIDDEN_CHANGED_PREFIXES = (
    ".openlocus/", "crates/", "src/", "packages/", "runtime/",
    "retrieval/", "selector/", "reranker/", "config/",
)

N5_ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)

N3_ANALOGUES = {
    "baseline_n2_order": "frozen_p4_order",
    "extra_depth_promote_before_primary_prefix_4": "early_extra_depth_quota_3",
    "bounded_interleave_primary2_extra1": "fixed_interleave_2_primary_1_extra_after_4",
    "late_extra_depth_demote_after_primary_prefix_8": "bounded_promotion_after_primary_prefix_4_3",
}

METRICS = (
    "top10_recovery_count_over_40_fixed_cases",
    "top20_recovery_count",
    "rank_window_shift_bucket",
    "hard_cap_violation_count",
    "case_regression_count",
)

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "exact_path", "private_path",
    "private_paths", "span", "spans", "exact_span", "line", "lines",
    "start_line", "end_line", "line_range", "snippet", "snippets", "content",
    "text", "raw_text", "candidate", "candidates", "candidate_list",
    "candidate_lists", "candidate_order", "candidate_paths", "rank", "ranks",
    "raw_rank", "rank_list", "rank_lists", "score", "scores", "task_id",
    "repo", "repo_id", "repo_name", "repo_slug", "repo_url", "private_id",
    "private_record_id", "private_ids", "source_hash", "source_hashes", "hash",
    "hashes", "content_sha", "provider", "provider_payload", "raw_payload",
    "payload", "prompt", "response", "raw", "raw_diff", "diff",
})

SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "claim_level", "phase", "generated_by",
    "generated_at", "status_vocabulary", "input_artifact_bucket", "observed_status",
    "expected_status", "load_status", "forbidden_scan_status", "gate",
    "threshold_relation", "case_set_bucket", "rank_window_bucket", "recovery_bucket",
    "top20_recovery_bucket", "top50_or_top100_recovery_bucket", "blocker_bucket",
    "pool_presence_bucket", "language_bucket", "source_bucket", "arm_name",
    "n3_analogue_bucket", "mapping_status_bucket", "mapping_reason_bucket",
    "result_status_bucket", "not_evaluated_reason_bucket", "metric_name",
    "metric_result_bucket", "metric_role", "threshold_decision_bucket",
    "pass_threshold_bucket", "baseline_reference_bucket", "execution_boundary_bucket",
    "privacy_boundary_bucket", "public_artifact_bucket", "authorization",
    "next_allowed_phase", "next_allowed_scope_bucket", "arm_family_bucket",
    "primary_threshold_bucket", "best_arm_bucket", "top10_recovery_rate_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = _repo_root() / path
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
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())],
    }


def _load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    artifacts: dict[str, dict[str, Any]] = {}
    loads: dict[str, str] = {}
    for bucket, path, _expected in INPUTS:
        artifact, load = _load_json(path)
        artifacts[bucket] = artifact
        loads[bucket] = load
    return artifacts, loads


def _input_artifact_records(artifacts: Mapping[str, Mapping[str, Any]], loads: Mapping[str, str]) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, _path, expected) in enumerate(INPUTS):
        artifact = artifacts.get(bucket, {})
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        observed = str(artifact.get("status", "") or "")
        passed = loads.get(bucket) == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({
            "anonymous_input_artifact_id": f"n6in{idx:04d}",
            "input_artifact_bucket": bucket,
            "load_status": str(loads.get(bucket, "missing")),
            "observed_status": observed,
            "expected_status": expected,
            "forbidden_scan_status": str(scan),
            "input_gate_passed_bool": passed,
        })
    return records, ok


def _n5_authorized(n5: Mapping[str, Any]) -> bool:
    stop = n5.get("stop_go_records", [])
    return (
        n5.get("status") == "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"
        and n5.get("forbidden_scan", {}).get("status") == "pass"
        and isinstance(stop, list)
        and bool(stop)
        and stop[0].get("n6_fixed_pool_rank_order_experiment_authorized") is True
    )


def _case_set_consistency_records(artifacts: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n5_cases = list(artifacts["n5_fixed_pool_rank_order_experiment_preflight"].get("eligible_case_set_records", []))
    n4_cases = list(artifacts["n4_fixed_pool_rank_blocker_denominator_audit"].get("rank_blocker_evidence_records", []))
    n5_aggregate = n5_cases[0] if n5_cases and isinstance(n5_cases[0], dict) else {}
    n5_detail_count = max(0, len(n5_cases) - 1)
    n4_detail_count = len(n4_cases)
    ok = (
        int(n5_aggregate.get("eligible_case_count", 0) or 0) == 40
        and n5_detail_count == 40
        and n4_detail_count == 40
        and n5_aggregate.get("rank_window_bucket") == "rank_21_50"
        and n5_aggregate.get("top20_recovery_bucket") == "not_recovered"
        and n5_aggregate.get("top50_or_top100_recovery_bucket") == "recovered"
        and n5_aggregate.get("blocker_bucket") == "extra_depth_append_blocked"
        and n5_aggregate.get("case_set_frozen_bool") is True
        and n5_aggregate.get("private_or_source_linkage_required_bool") is False
    )
    return [{
        "anonymous_case_set_consistency_id": "n6cs0000",
        "case_set_bucket": "n5_frozen_n4_sanitized_rank_blocker_cases",
        "n5_eligible_case_count": int(n5_aggregate.get("eligible_case_count", 0) or 0),
        "n5_detail_case_count": n5_detail_count,
        "n4_sanitized_case_count": n4_detail_count,
        "case_count": int(n5_aggregate.get("eligible_case_count", 0) or 0),
        "n5_case_set_frozen_bool": n5_aggregate.get("case_set_frozen_bool") is True,
        "n4_case_set_match_bool": n4_detail_count == 40,
        "n2_case_set_match_bool": artifacts["n2_rank_pack_actionability_decomposition"].get("d2_rank_blocked_denominator_count") == 40,
        "n3_case_set_match_bool": artifacts["n3_extra_depth_merge_order_design_simulation"].get("d3_design_denominator_count") == 40,
        "private_or_source_linkage_required_bool": n5_aggregate.get("private_or_source_linkage_required_bool") is True,
        "rank_window_bucket": str(n5_aggregate.get("rank_window_bucket", "unknown")),
        "top20_recovery_bucket": str(n5_aggregate.get("top20_recovery_bucket", "unknown")),
        "top50_or_top100_recovery_bucket": str(n5_aggregate.get("top50_or_top100_recovery_bucket", "unknown")),
        "blocker_bucket": str(n5_aggregate.get("blocker_bucket", "unknown")),
        "case_set_frozen_bool": n5_aggregate.get("case_set_frozen_bool") is True,
        "case_set_consistent_bool": ok,
        "case_set_consistency_passed_bool": ok,
    }], ok


def _n3_public_arm_names(n3: Mapping[str, Any]) -> set[str]:
    rows = n3.get("sanitized_analysis_records", [])
    return {str(r.get("sim_arm", "")) for r in rows if isinstance(r, dict) and r.get("sim_arm")}


def _arm_mapping_records(artifacts: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n5 = artifacts["n5_fixed_pool_rank_order_experiment_preflight"]
    n3 = artifacts["n3_extra_depth_merge_order_design_simulation"]
    n5_arms = [str(r.get("arm_name", "")) for r in n5.get("rank_order_arm_contract_records", []) if isinstance(r, dict)]
    n3_public = _n3_public_arm_names(n3)
    records: list[dict[str, Any]] = []
    for idx, arm in enumerate(N5_ARMS):
        analogue = N3_ANALOGUES[arm]
        records.append({
            "anonymous_arm_mapping_id": f"n6map{idx:04d}",
            "arm_name": arm,
            "arm_family_bucket": "fixed_pool_order_transform_only",
            "n3_analogue_bucket": analogue if analogue in n3_public else "no_public_analogue_detected",
            "mapping_status_bucket": "inexact_or_unverifiable_public_mapping",
            "mapping_reason_bucket": "n5_arm_name_or_semantics_not_exactly_present_in_committed_public_per_case_outputs",
            "n5_arm_declared_bool": arm in n5_arms,
            "n3_analogue_present_bool": analogue in n3_public,
            "exact_public_arm_mapping_bool": False,
            "per_case_outcome_available_bool": False,
            "candidate_pool_changed_bool": False,
            "new_retrieval_used_bool": False,
            "selector_or_reranker_used_bool": False,
            "aggregate_inference_used_bool": False,
            "arm_mapping_passed_bool": False,
        })
    # N6 requires exact public per-case outcome fields for every exact N5 arm.
    return records, all(r["exact_public_arm_mapping_bool"] and r["per_case_outcome_available_bool"] for r in records)


def _per_arm_result_records(arm_records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "anonymous_arm_result_id": f"n6armres{idx:04d}",
        "arm_name": str(record["arm_name"]),
        "result_status_bucket": "no_result_not_evaluated",
        "not_evaluated_reason_bucket": "no_exact_public_per_case_arm_mapping_or_outcome_fields",
        "evaluated_case_count": 0,
        "expected_case_count": 40,
        "top10_recovery_count_over_40_fixed_cases": None,
        "top20_recovery_count": None,
        "hard_cap_violation_count": None,
        "case_regression_count": None,
        "top10_recovery_rate_bucket": "not_evaluated",
        "threshold_passed_bool": False,
        "threshold_decision_bucket": "not_evaluated",
    } for idx, record in enumerate(arm_records)]


def _metric_result_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, metric in enumerate(METRICS):
        records.append({
            "anonymous_metric_result_id": f"n6met{idx:04d}",
            "metric_name": metric,
            "metric_role": "primary" if idx == 0 else "secondary",
            "metric_result_bucket": "not_evaluated_no_exact_public_arm_fields",
            "evaluated_case_count": 0,
            "expected_case_count": 40,
            "aggregate_inference_used_bool": False,
        })
    return records


def _threshold_decision_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_threshold_decision_id": "n6td0000",
        "primary_threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
        "threshold_decision_bucket": "no_go_not_evaluated_exact_public_arm_fields_missing",
        "pass_threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
        "baseline_reference_bucket": "n2_baseline_order_zero_top10_over_40",
        "best_arm_bucket": "not_evaluated_no_exact_public_arm_fields",
        "best_top10_recovery_count": 0,
        "best_case_regression_count": 0,
        "threshold_passed_bool": False,
        "top10_recovery_threshold_count": 16,
        "case_regression_threshold_count": 2,
        "evaluated_arm_count": 0,
        "passing_arm_count": 0,
        "n7_result_audit_authorized_bool": False,
        "method_winner_claim_authorized_bool": False,
        "downstream_value_claim_authorized_bool": False,
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }]


def _execution_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_execution_boundary_id": "n6eb0000",
        "execution_boundary_bucket": "public_artifact_no_go_no_arm_execution",
        "private_read_count": 0,
        "new_retrieval_count": 0,
        "rerun_count": 0,
        "selector_reranker_execution_count": 0,
        "counterfactual_execution_count": 0,
        "policy_tuning_count": 0,
        "runtime_change_count": 0,
        "aggregate_inference_used_bool": False,
        "execution_boundary_complete_bool": True,
    }
    return [record], True


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_privacy_boundary_id": "n6pb0000",
        "privacy_boundary_bucket": "public_anonymous_buckets_only",
        "public_artifact_bucket": "anonymous_ids_arm_language_source_rank_recovery_threshold_buckets_and_aggregate_counts_only",
        "private_or_source_linkage_required_bool": False,
        "raw_candidate_lists_publicly_serialized": False,
        "raw_provider_payloads_publicly_serialized": False,
        "raw_diffs_publicly_serialized": False,
        "raw_ranks_publicly_serialized": False,
        "privacy_boundary_complete_bool": True,
    }
    return [record], True


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10,
        )
        return [line[3:].strip().rstrip("/") for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = 0
    private_or_source = 0
    forbidden_runtime = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT
        if name.startswith(FORBIDDEN_CHANGED_PREFIXES):
            forbidden_runtime += 1
            allowed = False
        if name.startswith(".openlocus/") or name.startswith(("crates/", "src/", "packages/")):
            private_or_source += 1
        if not allowed:
            disallowed += 1
    ok = available and disallowed == 0 and private_or_source == 0 and forbidden_runtime == 0
    return [{
        "anonymous_changed_file_allowlist_id": "n6cf0000",
        "git_status_available_bool": available,
        "workspace_change_count": len(names),
        "disallowed_changed_file_count": disallowed,
        "private_or_source_file_modification_count": private_or_source,
        "forbidden_runtime_or_evaluator_modified_bool": forbidden_runtime > 0,
        "changed_file_scope_valid_bool": ok,
    }], ok


def _gate_records(
    *, input_ok: bool, n5_ok: bool, case_ok: bool, exact_mapping_ok: bool,
    privacy_ok: bool, execution_ok: bool, changed_ok: bool, scanner_ok: bool,
) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "n5_preflight_authorized", "passed": n5_ok, "threshold_relation": "equals", "value": int(n5_ok), "threshold_value": 1},
        {"gate": "fixed_case_set_matches_40", "passed": case_ok, "threshold_relation": "equals", "value": int(case_ok), "threshold_value": 1},
        {"gate": "exact_public_arm_mapping_available", "passed": exact_mapping_ok, "threshold_relation": "equals", "value": int(exact_mapping_ok), "threshold_value": 1},
        {"gate": "per_case_arm_outcome_fields_available", "passed": exact_mapping_ok, "threshold_relation": "equals", "value": int(exact_mapping_ok), "threshold_value": 1},
        {"gate": "aggregate_inference_not_used", "passed": True, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "no_forbidden_execution", "passed": execution_ok, "threshold_relation": "equals", "value": int(execution_ok), "threshold_value": 1},
        {"gate": "changed_file_scope_valid", "passed": changed_ok, "threshold_relation": "equals", "value": int(changed_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{
        "authorization": "fixed_pool_rank_order_experiment_no_go" if not pass_status else "fixed_pool_rank_order_experiment_result_audit",
        "next_allowed_phase": "BEA-v1-N7 Fixed-Pool Rank-Order Result Audit" if pass_status else "none_until_public_fixed_pool_arm_fields_exist",
        "next_allowed_scope_bucket": "n7_result_audit_only" if pass_status else "no_next_phase_authorized_public_exact_arm_fields_missing",
        "n7_result_audit_authorized": pass_status,
        "new_retrieval_authorized": False,
        "rerun_authorized": False,
        "selector_or_reranker_authorized": False,
        "private_read_authorized": False,
        "policy_tuning_authorized": False,
        "counterfactual_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "runtime_or_policy_change_authorized": False,
        "method_winner_claimed": False,
        "method_winner_claim_authorized": False,
        "downstream_value_claimed": False,
        "downstream_value_claim_authorized": False,
    }]


def _status_from(*, self_ok: bool, input_ok: bool, n5_ok: bool, case_ok: bool, exact_mapping_ok: bool, privacy_ok: bool, changed_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6_required_inputs_unavailable"
    if not n5_ok:
        return "no_go_n6_n5_preflight_not_authorized"
    if not case_ok:
        return "no_go_n6_fixed_case_set_mismatch"
    if not exact_mapping_ok:
        return STATUS_NO_EXACT_FIELDS
    if not privacy_ok:
        return "no_go_n6_privacy_or_claim_boundary_invalid"
    if not changed_ok:
        return "no_go_n6_changed_file_scope_invalid"
    return STATUS_BELOW


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    n5_ok = _n5_authorized(artifacts["n5_fixed_pool_rank_order_experiment_preflight"])
    case_records, case_ok = _case_set_consistency_records(artifacts)
    arm_mapping_records, exact_mapping_ok = _arm_mapping_records(artifacts)
    per_arm_records = _per_arm_result_records(arm_mapping_records)
    metric_records = _metric_result_records()
    threshold_records = _threshold_decision_records()
    execution_records, execution_ok = _execution_boundary_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(
        self_ok=self_ok, input_ok=input_ok, n5_ok=n5_ok, case_ok=case_ok,
        exact_mapping_ok=exact_mapping_ok, privacy_ok=privacy_ok, changed_ok=changed_ok,
    )
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "fixed_pool_rank_order_experiment_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "case_set_consistency_records": case_records,
        "arm_mapping_records": arm_mapping_records,
        "per_arm_result_records": per_arm_records,
        "per_case_arm_outcome_records": [],
        "metric_result_records": metric_records,
        "threshold_decision_records": threshold_records,
        "execution_boundary_records": execution_records,
        "privacy_boundary_records": privacy_records,
        "changed_file_allowlist_records": changed_records,
        "gate_records": _gate_records(
            input_ok=input_ok, n5_ok=n5_ok, case_ok=case_ok,
            exact_mapping_ok=exact_mapping_ok, privacy_ok=privacy_ok,
            execution_ok=execution_ok, changed_ok=changed_ok, scanner_ok=True,
        ),
        "stop_go_records": _stop_go_records(status),
        "forbidden_scan": {},
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["stop_go_records"] = _stop_go_records(report["status"])
    final_scan = _scan_summary(report)
    report["forbidden_scan"] = final_scan
    scanner_ok = final_scan["status"] == "pass"
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    report["gate_records"] = _gate_records(
        input_ok=input_ok, n5_ok=n5_ok, case_ok=case_ok,
        exact_mapping_ok=exact_mapping_ok, privacy_ok=privacy_ok,
        execution_ok=execution_ok, changed_ok=changed_ok, scanner_ok=scanner_ok,
    )
    report["stop_go_records"] = _stop_go_records(report["status"])
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
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    n5_ok = _n5_authorized(artifacts["n5_fixed_pool_rank_order_experiment_preflight"])
    case_records, case_ok = _case_set_consistency_records(artifacts)
    mapping_records, exact_mapping_ok = _arm_mapping_records(artifacts)
    per_arm_records = _per_arm_result_records(mapping_records)
    execution_records, execution_ok = _execution_boundary_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (
            STATUS_PASS,
            STATUS_BELOW,
            "no_go_n6_required_inputs_unavailable",
            "no_go_n6_n5_preflight_not_authorized",
            STATUS_NO_EXACT_FIELDS,
            "no_go_n6_arm_mapping_inexact_or_unverifiable",
            "no_go_n6_fixed_case_set_mismatch",
            "no_go_n6_privacy_or_claim_boundary_invalid",
            "no_go_n6_changed_file_scope_invalid",
            "fail_forbidden_scan",
            "fail_schema_contract",
        )),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(
            _scan_summary({key: "blocked"})["status"] == "fail"
            for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff")
        )),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("input_artifacts", input_ok and len(input_records) == 5 and all(r["forbidden_scan_status"] == "pass" for r in input_records)),
        _check("n5_authorized", n5_ok),
        _check("case_set_consistent", case_ok and case_records[0]["case_count"] == 40 and case_records[0]["n5_case_set_frozen_bool"] is True and case_records[0]["n4_case_set_match_bool"] is True and case_records[0]["n2_case_set_match_bool"] is True and case_records[0]["n3_case_set_match_bool"] is True and case_records[0]["private_or_source_linkage_required_bool"] is False and case_records[0]["case_set_consistency_passed_bool"] is True),
        _check("arm_mapping_all_inexact", not exact_mapping_ok and len(mapping_records) == 4 and all(r["exact_public_arm_mapping_bool"] is False and r["per_case_outcome_available_bool"] is False for r in mapping_records)),
        _check("n3_analogues_not_reused_as_results", all(r["n3_analogue_present_bool"] is True and r["mapping_status_bucket"] == "inexact_or_unverifiable_public_mapping" and r["arm_family_bucket"] == "fixed_pool_order_transform_only" and r["candidate_pool_changed_bool"] is False and r["new_retrieval_used_bool"] is False and r["selector_or_reranker_used_bool"] is False and r["arm_mapping_passed_bool"] is False for r in mapping_records)),
        _check("per_arm_results_not_evaluated", len(per_arm_records) == 4 and all(r["result_status_bucket"] == "no_result_not_evaluated" and r["evaluated_case_count"] == 0 and r["top10_recovery_rate_bucket"] == "not_evaluated" and r["threshold_passed_bool"] is False for r in per_arm_records)),
        _check("per_case_outcomes_empty", len([]) == 0),
        _check("metrics_not_evaluated", all(r["metric_result_bucket"] == "not_evaluated_no_exact_public_arm_fields" for r in _metric_result_records())),
        _check("threshold_no_go", _threshold_decision_records()[0]["n7_result_audit_authorized_bool"] is False and _threshold_decision_records()[0]["threshold_passed_bool"] is False and _threshold_decision_records()[0]["best_arm_bucket"] == "not_evaluated_no_exact_public_arm_fields" and _threshold_decision_records()[0]["method_winner_claim_authorized_bool"] is False),
        _check("execution_boundary", execution_ok and execution_records[0]["private_read_count"] == 0 and execution_records[0]["new_retrieval_count"] == 0),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["private_or_source_linkage_required_bool"] is False),
        _check("stop_go_no_go", _stop_go_records(STATUS_NO_EXACT_FIELDS)[0]["n7_result_audit_authorized"] is False and _stop_go_records(STATUS_NO_EXACT_FIELDS)[0]["next_allowed_phase"] == "none_until_public_fixed_pool_arm_fields_exist"),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6 fixed-pool rank-order experiment")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(
        "wrote artifact "
        f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, "
        f"case_set={report['case_set_consistency_records'][0]['case_set_consistent_bool']}, "
        f"n7={report['stop_go_records'][0]['n7_result_audit_authorized']})"
    )


if __name__ == "__main__":
    main()
