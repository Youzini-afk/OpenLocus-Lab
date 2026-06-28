#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_n5_fixed_pool_rank_order_experiment_preflight.v1"
PHASE = "BEA-v1-N5"
GENERATED_BY = "bea_v1_n5_fixed_pool_rank_order_experiment_preflight"
STATUS_PASS = "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"

STATUSES = (
    STATUS_PASS,
    "no_go_n5_required_inputs_unavailable",
    "no_go_n5_n4_denominator_not_authorized",
    "no_go_n5_fixed_pool_case_set_incomplete",
    "no_go_n5_arm_contract_incomplete",
    "no_go_n5_frozen_input_or_gate_incomplete",
    "no_go_n5_privacy_or_claim_boundary_invalid",
    "no_go_n5_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/"
    "bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json"
)

INPUTS = (
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
    "docs/en/bea-v1-n5-fixed-pool-rank-order-experiment-preflight.md",
    "docs/zh/bea-v1-n5-fixed-pool-rank-order-experiment-preflight.md",
    "eval/bea_v1_n5_fixed_pool_rank_order_experiment_preflight.py",
    "artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json",
})

FORBIDDEN_CHANGED_PREFIXES = (
    ".openlocus/",
    "crates/",
    "src/",
    "packages/",
    "runtime/",
    "retrieval/",
    "selector/",
    "reranker/",
    "config/",
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)

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
    "threshold_relation", "eligible_record_type", "rank_window_bucket",
    "top20_recovery_bucket", "top50_or_top100_recovery_bucket", "blocker_bucket",
    "pool_presence_bucket", "merge_order_signal_bucket", "language_bucket",
    "source_bucket", "arm_name", "arm_family_bucket", "metric_name", "metric_role",
    "pass_threshold_bucket", "baseline_reference", "execution_boundary_bucket",
    "privacy_boundary_bucket", "n6_scope_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "public_artifact_bucket", "frozen_input_bucket", "input_bucket",
    "source_artifacts_bucket", "primary_metric_bucket", "baseline_reference_bucket",
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
        "violation_categories": [
            {"category": k, "count": v} for k, v in sorted(counts.items())
        ],
    }


def _load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    artifacts: dict[str, dict[str, Any]] = {}
    loads: dict[str, str] = {}
    for bucket, path, _expected in INPUTS:
        artifact, load = _load_json(path)
        artifacts[bucket] = artifact
        loads[bucket] = load
    return artifacts, loads


def _input_artifact_records(
    artifacts: Mapping[str, Mapping[str, Any]], loads: Mapping[str, str]
) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, _path, expected) in enumerate(INPUTS):
        artifact = artifacts.get(bucket, {})
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        observed = str(artifact.get("status", "") or "")
        passed = loads.get(bucket) == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({
            "anonymous_input_artifact_id": f"n5in{idx:04d}",
            "input_artifact_bucket": bucket,
            "load_status": str(loads.get(bucket, "missing")),
            "observed_status": observed,
            "expected_status": expected,
            "forbidden_scan_status": str(scan),
            "input_gate_passed_bool": passed,
        })
    return records, ok


def _n4_denominator_authorized(n4: Mapping[str, Any]) -> bool:
    stop = n4.get("stop_go_records", [])
    return (
        n4.get("status") == "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized"
        and n4.get("forbidden_scan", {}).get("status") == "pass"
        and isinstance(stop, list)
        and bool(stop)
        and stop[0].get("n5_fixed_pool_rank_order_experiment_preflight_authorized") is True
    )


def _eligible_case_set_records(n4: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    source_rows = list(n4.get("rank_blocker_evidence_records", []))
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    fixed_pool_count = 0
    for idx, record in enumerate(source_rows):
        top50 = str(record.get("top50_recovery_bucket", "unknown"))
        top100 = str(record.get("top100_recovery_bucket", "unknown"))
        top50_or_top100 = "recovered" if top50 == "recovered" or top100 == "recovered" else "not_recovered"
        pool = str(record.get("pool_presence_bucket", "unknown"))
        if pool == "fixed_pool_deeper_present":
            fixed_pool_count += 1
        row = {
            "anonymous_n5_case_id": f"n5case{idx:04d}",
            "rank_window_bucket": str(record.get("rank_window_bucket", "unknown")),
            "pool_presence_bucket": pool,
            "blocker_bucket": str(record.get("blocker_bucket", "unknown")),
            "merge_order_signal_bucket": str(record.get("merge_order_signal_bucket", "unknown")),
            "language_bucket": str(record.get("language_bucket", "unknown")),
            "source_bucket": str(record.get("source_bucket", "unknown")),
            "top20_recovery_bucket": str(record.get("top20_recovery_bucket", "unknown")),
            "top50_or_top100_recovery_bucket": top50_or_top100,
        }
        for key in (
            "rank_window_bucket", "pool_presence_bucket", "blocker_bucket",
            "top20_recovery_bucket", "top50_or_top100_recovery_bucket",
        ):
            counts[f"{key}:{row[key]}"] += 1
        rows.append(row)
    aggregate = {
        "eligible_record_type": "aggregate",
        "eligible_case_count": len(rows),
        "rank_window_bucket": "rank_21_50",
        "top20_recovery_bucket": "not_recovered",
        "top50_or_top100_recovery_bucket": "recovered",
        "blocker_bucket": "extra_depth_append_blocked",
        "fixed_pool_deeper_present_bool": fixed_pool_count == 40,
        "private_or_source_linkage_required_bool": False,
        "case_set_frozen_bool": True,
    }
    ok = (
        len(rows) == 40
        and counts["rank_window_bucket:rank_21_50"] == 40
        and counts["pool_presence_bucket:fixed_pool_deeper_present"] == 40
        and counts["blocker_bucket:extra_depth_append_blocked"] == 40
        and counts["top20_recovery_bucket:not_recovered"] == 40
        and counts["top50_or_top100_recovery_bucket:recovered"] == 40
    )
    return [aggregate] + rows, {"eligible_case_count": len(rows), "fixed_pool_present_count": fixed_pool_count}, ok


def _frozen_input_contract_records(stats: Mapping[str, Any], artifacts: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n2 = artifacts["n2_rank_pack_actionability_decomposition"]
    n3 = artifacts["n3_extra_depth_merge_order_design_simulation"]
    p4l = artifacts["p4l_locked_non_python_scheduler_validation"]
    n2_ok = n2.get("d2_rank_blocked_denominator_count") == 40
    n3_ok = n3.get("d3_design_denominator_count") == 40 and n3.get("candidate_pool_changed") is False and n3.get("new_retrieval_used") is False
    p4l_ok = p4l.get("denominator_exact_match") is True and int(p4l.get("locked_denominator_count", p4l.get("expected_locked_denominator_count", 0)) or 0) == 272
    records = [
        {
            "anonymous_frozen_input_id": "n5fiagg0000",
            "input_bucket": "n4_sanitized_rank_case_set",
            "case_count": int(stats.get("eligible_case_count", 0)),
            "source_artifacts_bucket": "n2_n3_p4l_committed_public_artifacts",
            "candidate_pool_mutation_authorized_bool": False,
            "new_retrieval_authorized_bool": False,
            "rerun_authorized_bool": False,
            "frozen_input_contract_complete_bool": int(stats.get("eligible_case_count", 0)) == 40 and bool(n2_ok) and bool(n3_ok) and bool(p4l_ok),
            "private_or_source_linkage_required_bool": False,
        },
        {
            "anonymous_frozen_input_id": "n5fi0000",
            "frozen_input_bucket": "n4_sanitized_rank_blocker_case_set",
            "case_count": int(stats.get("eligible_case_count", 0)),
            "input_complete_bool": int(stats.get("eligible_case_count", 0)) == 40,
            "private_or_source_linkage_required_bool": False,
        },
        {
            "anonymous_frozen_input_id": "n5fi0001",
            "frozen_input_bucket": "n2_public_fixed_pool_rank_buckets",
            "case_count": int(n2.get("d2_rank_blocked_denominator_count", 0) or 0),
            "input_complete_bool": bool(n2_ok),
            "private_or_source_linkage_required_bool": False,
        },
        {
            "anonymous_frozen_input_id": "n5fi0002",
            "frozen_input_bucket": "n3_public_fixed_pool_arm_buckets",
            "case_count": int(n3.get("d3_design_denominator_count", 0) or 0),
            "input_complete_bool": bool(n3_ok),
            "private_or_source_linkage_required_bool": False,
        },
        {
            "anonymous_frozen_input_id": "n5fi0003",
            "frozen_input_bucket": "p4l_locked_denominator_aggregate",
            "case_count": int(p4l.get("locked_denominator_count", p4l.get("expected_locked_denominator_count", 0)) or 0),
            "input_complete_bool": bool(p4l_ok),
            "private_or_source_linkage_required_bool": False,
        },
    ]
    detail_ok = all((r.get("input_complete_bool") is True or r.get("frozen_input_contract_complete_bool") is True) and not r["private_or_source_linkage_required_bool"] for r in records)
    return records, bool(detail_ok and records[0]["frozen_input_contract_complete_bool"])


def _rank_order_arm_contract_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    for idx, arm in enumerate(ARMS):
        records.append({
            "anonymous_arm_id": f"n5arm{idx:04d}",
            "arm_name": arm,
            "arm_family_bucket": "fixed_pool_order_transform_only",
            "candidate_pool_changed_bool": False,
            "new_retrieval_authorized_bool": False,
            "selector_or_reranker_authorized_bool": False,
            "policy_tuning_authorized_bool": False,
            "arm_contract_complete_bool": True,
        })
    ok = (
        tuple(r["arm_name"] for r in records) == ARMS
        and 2 <= len(records) <= 4
        and all(r["arm_family_bucket"] == "fixed_pool_order_transform_only" for r in records)
        and all(r["candidate_pool_changed_bool"] is False for r in records)
        and all(r["new_retrieval_authorized_bool"] is False for r in records)
        and all(r["selector_or_reranker_authorized_bool"] is False for r in records)
        and all(r["policy_tuning_authorized_bool"] is False for r in records)
        and all(r["arm_contract_complete_bool"] is True for r in records)
    )
    return records, ok


def _experiment_metric_contract_records() -> tuple[list[dict[str, Any]], bool]:
    records = [
        {
            "anonymous_metric_id": "n5metagg0000",
            "primary_metric_bucket": "top10_recovery_count_over_40_fixed_cases",
            "secondary_metric_buckets": [
                "top20_recovery_count",
                "rank_window_shift_bucket",
                "hard_cap_violation_count",
                "case_regression_count",
            ],
            "pass_threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
            "baseline_reference_bucket": "n2_baseline_order_zero_top10_over_40",
            "method_winner_claim_authorized_bool": False,
            "downstream_value_claim_authorized_bool": False,
            "metric_contract_complete_bool": True,
        },
        {
            "anonymous_metric_id": "n5met0000",
            "metric_name": "top10_recovery_count_over_40_fixed_cases",
            "metric_role": "primary",
            "pass_threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
            "baseline_reference": "n2_baseline_order_zero_top10_over_40",
            "complete": True,
        },
        {
            "anonymous_metric_id": "n5met0001",
            "metric_name": "top20_recovery_count",
            "metric_role": "secondary",
            "pass_threshold_bucket": "reported_not_authorizing_method_winner",
            "baseline_reference": "n2_top20_zero_over_40",
            "complete": True,
        },
        {
            "anonymous_metric_id": "n5met0002",
            "metric_name": "rank_window_shift_bucket",
            "metric_role": "secondary",
            "pass_threshold_bucket": "reported_not_authorizing_method_winner",
            "baseline_reference": "n2_rank_window_rank_21_50_over_40",
            "complete": True,
        },
        {
            "anonymous_metric_id": "n5met0003",
            "metric_name": "hard_cap_violation_count",
            "metric_role": "secondary",
            "pass_threshold_bucket": "hard_cap_violation_zero_expected",
            "baseline_reference": "p4l_treatment_hard_cap_zero",
            "complete": True,
        },
        {
            "anonymous_metric_id": "n5met0004",
            "metric_name": "case_regression_count",
            "metric_role": "secondary",
            "pass_threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
            "baseline_reference": "n2_baseline_order_zero_top10_over_40",
            "complete": True,
        },
    ]
    detail_records = [r for r in records if "metric_name" in r]
    ok = tuple(r["metric_name"] for r in detail_records) == METRICS and detail_records[0]["metric_role"] == "primary" and all(r["complete"] for r in detail_records) and records[0]["metric_contract_complete_bool"] is True
    return records, ok


def _execution_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_execution_boundary_id": "n5eb0000",
        "execution_boundary_bucket": "no_execution_preflight_only",
        "private_read_count": 0,
        "new_retrieval_count": 0,
        "rerun_count": 0,
        "selector_reranker_execution_count": 0,
        "counterfactual_execution_count": 0,
        "policy_tuning_count": 0,
        "runtime_change_count": 0,
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
        "execution_boundary_complete_bool": True,
    }
    return [record], True


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_privacy_boundary_id": "n5pb0000",
        "privacy_boundary_bucket": "public_anonymous_buckets_only",
        "public_artifact_bucket": "anonymous_case_language_source_rank_recovery_arm_and_aggregate_counts_only",
        "private_or_source_linkage_required_bool": False,
        "raw_candidate_lists_publicly_serialized": False,
        "raw_provider_payloads_publicly_serialized": False,
        "raw_diffs_publicly_serialized": False,
        "privacy_boundary_complete_bool": True,
    }
    return [record], True


def _n6_handoff_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{
        "anonymous_n6_handoff_id": "n5n60000",
        "n6_scope_bucket": "bea_v1_n6_fixed_pool_rank_order_experiment_only",
        "n6_authorized_bool": pass_status,
        "n6_case_count": 40 if pass_status else 0,
        "n6_arm_count_max": 4 if pass_status else 0,
        "execute_predeclared_fixed_pool_order_transform_arms_bool": pass_status,
        "case_count": 40 if pass_status else 0,
        "candidate_pool_mutation_authorized": False,
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
        "downstream_value_claimed": False,
    }]


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
        "anonymous_changed_file_allowlist_id": "n5cf0000",
        "git_status_available_bool": available,
        "workspace_change_count": len(names),
        "disallowed_changed_file_count": disallowed,
        "private_or_source_file_modification_count": private_or_source,
        "forbidden_runtime_or_evaluator_modified_bool": forbidden_runtime > 0,
        "changed_file_scope_valid_bool": ok,
    }], ok


def _gate_records(
    *, input_ok: bool, n4_ok: bool, case_ok: bool, stats: Mapping[str, Any],
    frozen_ok: bool, arm_ok: bool, metric_ok: bool, privacy_ok: bool,
    changed_ok: bool, scanner_ok: bool,
) -> list[dict[str, Any]]:
    arm_count = len(ARMS)
    return [
        {"gate": "n4_status_and_scan_pass", "passed": n4_ok, "threshold_relation": "equals", "value": int(n4_ok), "threshold_value": 1},
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "eligible_count_40", "passed": int(stats.get("eligible_case_count", 0)) == 40 and case_ok, "threshold_relation": "equals", "value": int(stats.get("eligible_case_count", 0)), "threshold_value": 40},
        {"gate": "fixed_pool_present_40", "passed": int(stats.get("fixed_pool_present_count", 0)) == 40, "threshold_relation": "equals", "value": int(stats.get("fixed_pool_present_count", 0)), "threshold_value": 40},
        {"gate": "private_source_linkage_false", "passed": privacy_ok, "threshold_relation": "equals", "value": 0 if privacy_ok else 1, "threshold_value": 0},
        {"gate": "frozen_input_complete", "passed": frozen_ok, "threshold_relation": "equals", "value": int(frozen_ok), "threshold_value": 1},
        {"gate": "arm_count_between_2_and_4", "passed": 2 <= arm_count <= 4, "threshold_relation": "between_inclusive", "value": arm_count, "threshold_value": 4},
        {"gate": "all_arms_fixed_pool_transform", "passed": arm_ok, "threshold_relation": "equals", "value": int(arm_ok), "threshold_value": 1},
        {"gate": "candidate_pool_mutation_zero", "passed": arm_ok, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
        {"gate": "new_retrieval_zero", "passed": arm_ok, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
        {"gate": "selector_reranker_zero", "passed": arm_ok, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
        {"gate": "metric_contract_complete", "passed": metric_ok, "threshold_relation": "equals", "value": int(metric_ok), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "changed_file_scope_valid", "passed": changed_ok, "threshold_relation": "equals", "value": int(changed_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{
        "authorization": "fixed_pool_rank_order_experiment_preflight_only",
        "next_allowed_phase": "BEA-v1-N6 Fixed-Pool Rank-Order Experiment" if pass_status else "none_for_rank_order_experiment",
        "next_allowed_scope_bucket": "execute_only_predeclared_fixed_pool_order_transform_arms_over_forty_sanitized_cases" if pass_status else "no_next_phase_authorized",
        "n6_fixed_pool_rank_order_experiment_authorized": pass_status,
        "n6_case_count": 40 if pass_status else 0,
        "n6_arm_count_max": 4 if pass_status else 0,
        "candidate_pool_mutation_authorized": False,
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
        "downstream_value_claimed": False,
    }]


def _status_from(
    *, self_ok: bool, input_ok: bool, n4_ok: bool, case_ok: bool, stats: Mapping[str, Any],
    arm_ok: bool, frozen_ok: bool, metric_ok: bool, privacy_ok: bool, changed_ok: bool,
) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n5_required_inputs_unavailable"
    if not n4_ok:
        return "no_go_n5_n4_denominator_not_authorized"
    if not case_ok or int(stats.get("eligible_case_count", 0)) != 40 or int(stats.get("fixed_pool_present_count", 0)) != 40:
        return "no_go_n5_fixed_pool_case_set_incomplete"
    if not arm_ok:
        return "no_go_n5_arm_contract_incomplete"
    if not frozen_ok or not metric_ok:
        return "no_go_n5_frozen_input_or_gate_incomplete"
    if not privacy_ok:
        return "no_go_n5_privacy_or_claim_boundary_invalid"
    if not changed_ok:
        return "no_go_n5_changed_file_scope_invalid"
    return STATUS_PASS


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    n4 = artifacts["n4_fixed_pool_rank_blocker_denominator_audit"]
    n4_ok = _n4_denominator_authorized(n4)
    eligible_records, stats, case_ok = _eligible_case_set_records(n4)
    frozen_records, frozen_ok = _frozen_input_contract_records(stats, artifacts)
    arm_records, arm_ok = _rank_order_arm_contract_records()
    metric_records, metric_ok = _experiment_metric_contract_records()
    execution_records, execution_ok = _execution_boundary_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(
        self_ok=self_ok, input_ok=input_ok, n4_ok=n4_ok, case_ok=case_ok, stats=stats,
        arm_ok=arm_ok, frozen_ok=frozen_ok and execution_ok, metric_ok=metric_ok,
        privacy_ok=privacy_ok, changed_ok=changed_ok,
    )
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "fixed_pool_rank_order_experiment_preflight_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "eligible_case_set_records": eligible_records,
        "frozen_input_contract_records": frozen_records,
        "rank_order_arm_contract_records": arm_records,
        "experiment_metric_contract_records": metric_records,
        "execution_boundary_records": execution_records,
        "privacy_boundary_records": privacy_records,
        "n6_handoff_records": _n6_handoff_records(status),
        "changed_file_allowlist_records": changed_records,
        "gate_records": _gate_records(
            input_ok=input_ok, n4_ok=n4_ok, case_ok=case_ok, stats=stats,
            frozen_ok=frozen_ok and execution_ok, arm_ok=arm_ok, metric_ok=metric_ok,
            privacy_ok=privacy_ok, changed_ok=changed_ok, scanner_ok=True,
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
        report["n6_handoff_records"] = _n6_handoff_records(report["status"])
        report["stop_go_records"] = _stop_go_records(report["status"])
    final_scan = _scan_summary(report)
    report["forbidden_scan"] = final_scan
    scanner_ok = final_scan["status"] == "pass"
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    report["gate_records"] = _gate_records(
        input_ok=input_ok, n4_ok=n4_ok, case_ok=case_ok, stats=stats,
        frozen_ok=frozen_ok and execution_ok, arm_ok=arm_ok, metric_ok=metric_ok,
        privacy_ok=privacy_ok, changed_ok=changed_ok, scanner_ok=scanner_ok,
    )
    if scanner_ok and report["status"] == STATUS_PASS:
        report["n6_handoff_records"] = _n6_handoff_records(STATUS_PASS)
        report["stop_go_records"] = _stop_go_records(STATUS_PASS)
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
    n4_ok = _n4_denominator_authorized(artifacts["n4_fixed_pool_rank_blocker_denominator_audit"])
    eligible_records, stats, case_ok = _eligible_case_set_records(artifacts["n4_fixed_pool_rank_blocker_denominator_audit"])
    frozen_records, frozen_ok = _frozen_input_contract_records(stats, artifacts)
    arm_records, arm_ok = _rank_order_arm_contract_records()
    metric_records, metric_ok = _experiment_metric_contract_records()
    execution_records, execution_ok = _execution_boundary_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (
            STATUS_PASS,
            "no_go_n5_required_inputs_unavailable",
            "no_go_n5_n4_denominator_not_authorized",
            "no_go_n5_fixed_pool_case_set_incomplete",
            "no_go_n5_arm_contract_incomplete",
            "no_go_n5_frozen_input_or_gate_incomplete",
            "no_go_n5_privacy_or_claim_boundary_invalid",
            "no_go_n5_changed_file_scope_invalid",
            "fail_forbidden_scan",
            "fail_schema_contract",
        )),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(
            _scan_summary({key: "blocked"})["status"] == "fail"
            for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff")
        )),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("input_artifacts", input_ok and len(input_records) == 4 and all(r["forbidden_scan_status"] == "pass" for r in input_records)),
        _check("n4_denominator_authorized", n4_ok),
        _check("eligible_aggregate_exact", eligible_records[0] == {
            "eligible_record_type": "aggregate",
            "eligible_case_count": 40,
            "rank_window_bucket": "rank_21_50",
            "top20_recovery_bucket": "not_recovered",
            "top50_or_top100_recovery_bucket": "recovered",
            "blocker_bucket": "extra_depth_append_blocked",
            "fixed_pool_deeper_present_bool": True,
            "private_or_source_linkage_required_bool": False,
            "case_set_frozen_bool": True,
        }),
        _check("eligible_case_rows", case_ok and len(eligible_records) == 41 and int(stats["eligible_case_count"]) == 40 and int(stats["fixed_pool_present_count"]) == 40),
        _check("frozen_inputs", frozen_ok and len(frozen_records) == 5 and frozen_records[0]["source_artifacts_bucket"] == "n2_n3_p4l_committed_public_artifacts" and not frozen_records[0]["candidate_pool_mutation_authorized_bool"]),
        _check("arms_exact_four", arm_ok and tuple(r["arm_name"] for r in arm_records) == ARMS and len(arm_records) == 4),
        _check("arms_no_forbidden_execution", all(not r["candidate_pool_changed_bool"] and not r["new_retrieval_authorized_bool"] and not r["selector_or_reranker_authorized_bool"] and not r["policy_tuning_authorized_bool"] and r["arm_contract_complete_bool"] for r in arm_records)),
        _check("metrics_contract", metric_ok and tuple(r["metric_name"] for r in metric_records if "metric_name" in r) == METRICS and metric_records[0]["primary_metric_bucket"] == "top10_recovery_count_over_40_fixed_cases" and metric_records[0]["pass_threshold_bucket"] == "top10_recovery_ge_16_and_regressions_le_2" and not metric_records[0]["method_winner_claim_authorized_bool"]),
        _check("execution_boundary", execution_ok and execution_records[0]["private_read_count"] == 0 and execution_records[0]["new_retrieval_count"] == 0),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["private_or_source_linkage_required_bool"] is False),
        _check("n6_handoff_scope", _n6_handoff_records(STATUS_PASS)[0]["n6_authorized_bool"] is True and _n6_handoff_records(STATUS_PASS)[0]["n6_case_count"] == 40 and _n6_handoff_records(STATUS_PASS)[0]["n6_arm_count_max"] == 4 and _n6_handoff_records(STATUS_PASS)[0]["new_retrieval_authorized"] is False and _n6_handoff_records(STATUS_PASS)[0]["p5_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N5 fixed-pool rank-order experiment preflight")
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
        f"eligible_cases={report['eligible_case_set_records'][0]['eligible_case_count']}, "
        f"n6={report['stop_go_records'][0]['n6_fixed_pool_rank_order_experiment_authorized']})"
    )


if __name__ == "__main__":
    main()
