#!/usr/bin/env python3
"""BEA-v1-P4H: Disjoint Latency-Aware Retrieval Scheduler Validation.

P4H is an empirical heldout validation of the frozen BEA-v1-P4 retrieval
action scheduler.  It intentionally reuses the P4 scheduler implementation
without changing thresholds, adding query anchors, introducing a selector, or
using latency in candidate relevance scoring.

The public artifact is aggregate-only / records-only.  Per-record manifests and
retrieval traces are written only under /tmp when a real network-enabled run is
explicitly requested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn, Sequence

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_p4_latency_aware_retrieval_scheduler_smoke as p4  # noqa: E402

SCHEMA_VERSION = "bea_v1_p4h_disjoint_scheduler_validation.v1"
GENERATED_BY = "eval/bea_v1_p4h_disjoint_scheduler_validation.py"
CLAIM_LEVEL = "bea_v1_p4h_disjoint_scheduler_validation_only"
MODE = "bea_v1_p4h_disjoint_scheduler_validation"
PHASE = "BEA-v1-P4H"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p4h_disjoint_scheduler_validation/"
    "bea_v1_p4h_disjoint_scheduler_validation_report.json"
)
DEFAULT_FD1_ARTIFACT = p4.DEFAULT_FD1_ARTIFACT

V1_P4_RESULT_CHECKPOINT = "f0e99ca"
V1_P4_RESULT_STATUS = "bea_v1_p4_latency_aware_retrieval_scheduler_pass"
V1_P4_BASELINE_REACH = 32
V1_P4_P2_DEPTH_REACH = 59
V1_P4_P3_REFERENCE_REACH = 58
V1_P4_REACH = 56
V1_P4_POOL_MULT = 2.056350
V1_P4_LATENCY_MULT = 1.749695
V1_P4_LATENCY_REDUCTION_VS_P3 = 0.193806
V1_P4_HARD_CAP_VIOLATIONS = 0
V1_P4_FIRST_GOLD_RANK_MEAN = 25.625
V1_P4_RECORDS_FIRST_GOLD_RANK_ABOVE_BUDGET = 48

FIXED_BUDGET = p4.FIXED_BUDGET
FIXED_METHODS = p4.FIXED_METHODS
EXPECTED_RECORDS_DECOMPOSED = p4.EXPECTED_RECORDS_DECOMPOSED
EXPECTED_PRIVATE_DECOMP_ROWS = p4.EXPECTED_PRIVATE_DECOMP_ROWS
ORIGINAL_P1234_DENOMINATOR_COUNT = 119
P4H_MIN_DENOMINATOR_COUNT = 80

POLICY_ARMS = (
    "current_bea_candidate_pool_replay",
    "p2_depth_only_reference",
    "p3_constrained_depth_policy_reference",
    "p4_latency_aware_action_scheduler_frozen",
)
P4_COMPAT_TREATMENT_ARM = "p4_latency_aware_action_scheduler"
P4H_TREATMENT_ARM = "p4_latency_aware_action_scheduler_frozen"

STATUSES = (
    "bea_v1_p4h_disjoint_scheduler_validation_pass",
    "no_go_p4h_insufficient_denominator",
    "no_go_p4h_replay_mismatch",
    "no_go_p4h_reach_not_replicated",
    "no_go_p4h_latency_not_fixed",
    "no_go_p4h_cost_exceeded",
    "no_go_p4h_policy_degenerate",
    "fail_forbidden_scan",
    "fail_schema_contract",
    "unavailable_with_reason",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "bea_v1_p4h_disjoint_scheduler_validation_pass",
    "no_go_p4h_insufficient_denominator",
    "no_go_p4h_reach_not_replicated",
    "no_go_p4h_latency_not_fixed",
    "no_go_p4h_cost_exceeded",
    "no_go_p4h_policy_degenerate",
})

P4H_REACH_P2_RATIO_MIN = 0.75
P4H_REACH_P3_RATIO_MIN = 0.90
P4H_LATENCY_MULT_MAX = 2.0
P4H_LATENCY_VS_P3_IMPROVEMENT_MIN = 0.10
P4H_POOL_MULT_MAX = 4.0
P4H_HARD_CAP_VIOLATION_MAX = 0
P4H_ACTION_REDUCTION_SHARE_MIN = 0.25
P4H_ACTION_REDUCTION_RECORDS_AT_119 = 20
P4H_SUBGROUP_MIN_N = 20
P4H_SUBGROUP_P2_GAIN_RATIO_MIN = 0.50
P4H_RANK_BUDGET_MEAN_RANK_MIN = 5
P4H_RANK_BUDGET_RECORDS_AT_119 = 25
P4H_RAW_CONTEXTBENCH_OFFSET = 0
P4H_RAW_CONTEXTBENCH_LIMIT = 480
P4H_RAW_REPOQA_OFFSET = 0
P4H_RAW_REPOQA_LIMIT = 240
P4H_RAW_DENOMINATOR_TARGET_COUNT = 80
P4H_RAW_SOURCE_PHASE = "P4H-RAW"
P4H_RAW_WINDOWS = (
    {
        "benchmark": "contextbench",
        "window_name": "contextbench_raw_full_frame_disjoint_scan",
        "raw_offset_requested": P4H_RAW_CONTEXTBENCH_OFFSET,
        "raw_limit_requested": P4H_RAW_CONTEXTBENCH_LIMIT,
    },
    {
        "benchmark": "repoqa",
        "window_name": "repoqa_raw_full_frame_disjoint_scan",
        "raw_offset_requested": P4H_RAW_REPOQA_OFFSET,
        "raw_limit_requested": P4H_RAW_REPOQA_LIMIT,
    },
)

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "records_only_public_artifact": True,
    "diagnostic_only": True,
    "heldout_validation": True,
    "frozen_p4_scheduler_equivalence_explicit": True,
    "fd1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "retrieval_policy_executed": False,
    "bea_v1_p4h_audit_evaluator_no_provider_calls": True,
    "bea_v1_p4h_audit_evaluator_no_selector_executed": True,
    "bea_v1_p4h_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p4h_audit_evaluator_no_role_proxy": True,
    "bea_v1_p4h_audit_evaluator_latency_not_in_relevance": True,
}
DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
    "downstream_agent_value_proven": False,
    "calibration_claimed": False,
    "method_winner_claimed": False,
    "promotion_ready": False,
    "default_should_change": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
    "provider_calls_made": False,
    "remote_provider_calls_made": False,
    "algorithm_changed_during_bea_v1_p4h": False,
    "weights_tuned_during_bea_v1_p4h": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p4h": False,
    "v1_a_selector_executed": False,
    "v1_a_coverage_preserving_selector_promoted": False,
    "selector_or_reranker_changed": False,
    "fd2b_executed": False,
    "fd2c_executed": False,
    "legacy_role_proxy_p4_executed": False,
    "p5_executed": False,
    "v031_tuning_executed": False,
    "v032_tuning_executed": False,
    "b16k_executed": False,
    "role_proxy_assigned": False,
    "posthoc_threshold_search": False,
    "latency_in_candidate_relevance": False,
    "private_decomposition_used_for_selection": False,
    "gold_labels_used_for_selection": False,
    "gold_labels_used_for_query_construction": False,
    "gold_labels_used_for_policy": False,
    "query_anchors_used_in_p4_arm": False,
    "new_records_added_during_bea_v1_p4h": False,
}
LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_p4h_disjoint_scheduler_validation",
}

FAILURE_CATEGORIES_AUDIT = tuple(dict.fromkeys((*p4.FAILURE_CATEGORIES_AUDIT,
    "prior_denominator_key_collision", "heldout_denominator_insufficient",
    "heldout_denominator_not_disjoint", "private_scheduler_rows_mismatch",
    "subgroup_collapse", "rank_budget_audit_missing",
    "raw_denominator_scan_failed", "raw_denominator_scan_not_attempted",
    "raw_denominator_parse_failed", "raw_denominator_clone_failed")))
BLOCKING_FAILURE_CATEGORIES = tuple(dict.fromkeys((
    *p4.BLOCKING_FAILURE_CATEGORIES,
    "raw_denominator_scan_failed",
    "raw_denominator_scan_not_attempted",
    "raw_denominator_clone_failed",
    "heldout_denominator_not_disjoint",
    "private_scheduler_rows_mismatch",
)))


class RawHeldoutDenominatorRecord:
    """One private raw heldout file-miss denominator record.

    The public artifact only exposes aggregate counts. Private row identity,
    query text, gold paths, repository location, and baseline candidate paths
    remain in memory or /tmp JSONL.
    """

    def __init__(
        self, *, private_record_id: str, benchmark: str, record_index: int,
        window_name: str, raw_window_offset: int, raw_window_limit: int,
        query_private: str = "", repo_url_private: str = "",
        base_commit_private: str = "",
        gold_paths_private: list[str] | None = None,
        baseline_result: p4.SchedulerReachResult | None = None,
    ) -> None:
        self.private_record_id = private_record_id
        self.source_phase = P4H_RAW_SOURCE_PHASE
        self.benchmark = benchmark
        self.record_index = int(record_index)
        self.window_name = window_name
        self.raw_window_offset = int(raw_window_offset)
        self.raw_window_limit = int(raw_window_limit)
        self.query_private = query_private
        self.repo_url_private = repo_url_private
        self.base_commit_private = base_commit_private
        self.gold_paths_private = list(gold_paths_private or [])
        self.baseline_result = baseline_result


def _now_iso() -> str:
    return p4._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    p4._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return p4._check(name, ok)


def _stable_private_key(d: p4.bea_v1_p2.DenominatorRecord) -> str:
    return "\x1f".join((d.source_phase, d.benchmark,
                         d.private_record_id, str(d.record_index)))


def _stable_private_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _raw_prior_exclusion_windows(benchmark: str) -> tuple[tuple[int, int, str], ...]:
    """Explicit public aggregate row-index windows excluded from P4H.

    These cover older fixed development/evaluation windows. BEA-4/BEA-5/P1-P4
    exact prior raw records are excluded from the FD1 private decomposition
    when available; exact private row ids are not published.
    """
    if benchmark == "contextbench":
        return (
            (40, 60, "BEA-2 ContextBench fixed window"),
            (60, 80, "BEA-3 ContextBench fixed window"),
            (80, 160, "BEA-4 ContextBench fixed window"),
        )
    if benchmark == "repoqa":
        return (
            (20, 30, "BEA-2 RepoQA fixed window"),
            (30, 40, "BEA-3 RepoQA fixed window"),
            (40, 80, "BEA-4 RepoQA fixed window"),
        )
    return ()


def _raw_index_exclusion_reason(benchmark: str, record_index: int) -> str:
    for start, end, label in _raw_prior_exclusion_windows(benchmark):
        if start <= record_index < end:
            return label
    return ""


def _prior_raw_keys_from_fd1_private(
    pt: p4.bea_v1_p1.ParsedPrivateDecomposition | None,
) -> tuple[set[tuple[str, int]], list[dict[str, Any]]]:
    """Return exact private prior raw keys plus public aggregate disclosures.

    The key set is private/in-memory only. Public records disclose only counts by
    source phase and benchmark plus the raw-index transform used for disjointness.
    """
    keys: set[tuple[str, int]] = set()
    by_group: dict[tuple[str, str, str], set[int]] = {}
    if pt is None or not getattr(pt, "computed", False):
        return keys, []
    all_record_keys: set[tuple[str, str]] = set()
    for row in getattr(pt, "rows", []):
        sp = str(row.get("source_phase", "") or "")
        rid = str(row.get("private_record_id", "") or "")
        if sp and rid:
            all_record_keys.add((sp, rid))
    for sp, rid in sorted(all_record_keys):
        parsed = p4.bea_v1_p2._parse_record_id(rid)
        if parsed is None:
            continue
        benchmark, local_idx = parsed
        if sp == "BEA-4":
            raw_idx = local_idx + (80 if benchmark == "contextbench" else 40)
            basis = "fd1_private_decomposition_exact_bea4_offset"
        elif sp == "BEA-5":
            raw_idx = local_idx
            basis = "fd1_private_decomposition_exact_bea5_raw_index"
        else:
            continue
        keys.add((benchmark, raw_idx))
        by_group.setdefault((sp, benchmark, basis), set()).add(raw_idx)
    records: list[dict[str, Any]] = []
    for (sp, benchmark, basis), idxs in sorted(by_group.items()):
        records.append({
            "source_phase": P4H_RAW_SOURCE_PHASE,
            "benchmark": benchmark,
            "exclusion_source_phase": sp,
            "exclusion_basis": basis,
            "excluded_raw_record_count": len(idxs),
            "private_row_ids_publicly_serialized": False,
        })
    return keys, records


def _extract_disjoint_heldout_denominator(
    pt: p4.bea_v1_p1.ParsedPrivateDecomposition,
) -> tuple[list[p4.bea_v1_p2.DenominatorRecord], dict[str, Any]]:
    """Build the P4H denominator before any P4H arm outcomes are inspected.

    The prior P1/P2/P3/P4 denominator is represented by the first 119
    stable-sorted private keys from the FD1-like gold_file_absent slice.  The
    public report receives only aggregate source/benchmark counts; private
    keys and hashes remain in memory or under /tmp only.
    """
    all_absent = p4._extract_denominator_from_private(pt)
    ordered = sorted(all_absent, key=_stable_private_key)
    prior = ordered[:ORIGINAL_P1234_DENOMINATOR_COUNT]
    prior_hashes = {_stable_private_hash(_stable_private_key(d)) for d in prior}
    heldout: list[p4.bea_v1_p2.DenominatorRecord] = []
    for d in ordered[ORIGINAL_P1234_DENOMINATOR_COUNT:]:
        h = _stable_private_hash(_stable_private_key(d))
        if h not in prior_hashes:
            heldout.append(d)
    heldout_hashes = {_stable_private_hash(_stable_private_key(d)) for d in heldout}
    meta = {
        "source_gold_file_absent_count": len(all_absent),
        "excluded_prior_window_count": len(prior_hashes),
        "heldout_denominator_count": len(heldout),
        "disjoint_from_prior": prior_hashes.isdisjoint(heldout_hashes),
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
    }
    return heldout, meta


def _compatible_arm_results(
    arm_results: dict[str, list[p4.SchedulerReachResult]],
) -> dict[str, list[p4.SchedulerReachResult]]:
    compat = {a: list(arm_results.get(a, [])) for a in POLICY_ARMS
              if a != P4H_TREATMENT_ARM}
    compat[P4_COMPAT_TREATMENT_ARM] = list(arm_results.get(P4H_TREATMENT_ARM, []))
    return compat


def _replace_treatment_name(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(P4_COMPAT_TREATMENT_ARM, P4H_TREATMENT_ARM)
    if isinstance(value, dict):
        return {k: _replace_treatment_name(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_treatment_name(v) for v in value]
    return value


def _p4_rows(fn: Any, arm_results: dict[str, list[p4.SchedulerReachResult]],
             *args: Any) -> list[dict[str, Any]]:
    return _replace_treatment_name(fn(_compatible_arm_results(arm_results), *args))


def _source_run_records(
    *, fd1_schema_version: str, fd1_source_artifact_hash: str,
    fd1_status: str, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    pt: p4.bea_v1_p1.ParsedPrivateDecomposition | None,
    rav: p4.bea_v1_p1.Fd1ReplayArtifactValidation | None,
    audit_match: bool, audit_mismatch_reason: str,
) -> list[dict[str, Any]]:
    return [{
        "source_phase": "BEA-v1-P4",
        "source_checkpoint": V1_P4_RESULT_CHECKPOINT,
        "source_status": fd1_status or p4.FD1_SOURCE_STATUS,
        "source_artifact_status": "audit_match" if audit_match else "audit_mismatch",
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": "raw_external_full_frame_disjoint_success_quota_scan.v1",
        "prior_fd1_denominator_reused": False,
        "raw_contextbench_offset_requested": P4H_RAW_CONTEXTBENCH_OFFSET,
        "raw_contextbench_limit_requested": P4H_RAW_CONTEXTBENCH_LIMIT,
        "raw_repoqa_offset_requested": P4H_RAW_REPOQA_OFFSET,
        "raw_repoqa_limit_requested": P4H_RAW_REPOQA_LIMIT,
        "raw_denominator_target_count": P4H_RAW_DENOMINATOR_TARGET_COUNT,
        "expected_records_decomposed": EXPECTED_RECORDS_DECOMPOSED,
        "audited_records_decomposed": int(fd1_records_decomposed),
        "expected_private_manifest_record_count": EXPECTED_PRIVATE_DECOMP_ROWS,
        "audited_private_manifest_record_count": int(fd1_private_manifest_record_count),
        "fd1_source_schema_version": fd1_schema_version,
        "fd1_source_artifact_hash": fd1_source_artifact_hash,
        "v1_p4_result_checkpoint": V1_P4_RESULT_CHECKPOINT,
        "v1_p4_result_status": V1_P4_RESULT_STATUS,
        "v1_p4_baseline_reach": V1_P4_BASELINE_REACH,
        "v1_p4_p2_depth_reach": V1_P4_P2_DEPTH_REACH,
        "v1_p4_p3_reference_reach": V1_P4_P3_REFERENCE_REACH,
        "v1_p4_reach": V1_P4_REACH,
        "v1_p4_pool_multiplier": V1_P4_POOL_MULT,
        "v1_p4_latency_multiplier": V1_P4_LATENCY_MULT,
        "v1_p4_latency_reduction_vs_p3": V1_P4_LATENCY_REDUCTION_VS_P3,
        "v1_p4_hard_cap_violations": V1_P4_HARD_CAP_VIOLATIONS,
        "fd1_private_decomposition_supplied": bool(pt.path_supplied if pt else False),
        "fd1_private_decomposition_parsed": bool(pt.computed if pt else False),
        "fd1_private_decomposition_row_count": int(pt.row_count if pt else 0),
        "fd1_private_decomposition_group_count": int(pt.group_count if pt else 0),
        "replay_artifact_supplied": bool(rav.supplied if rav else False),
        "replay_artifact_parsed": bool(rav.parsed if rav else False),
        "replay_artifact_validated": bool(rav.validated if rav else False),
        "replay_artifact_status": str(rav.replay_status if rav else ""),
        "replay_artifact_schema_version": str(rav.replay_schema_version if rav else ""),
        "replay_artifact_records_decomposed": int(rav.replay_records_decomposed if rav else 0),
        "replay_artifact_manifest_record_count": int(rav.replay_manifest_record_count if rav else 0),
        "replay_artifact_manifest_records_written": bool(rav.replay_manifest_records_written if rav else False),
        "replay_artifact_manifest_path_publicly_serialized": bool(rav.replay_manifest_path_publicly_serialized if rav else True),
        "replay_artifact_manifest_schema_version": str(rav.replay_manifest_schema_version if rav else ""),
        "replay_artifact_manifest_hash": str(rav.replay_manifest_hash if rav else ""),
        "replay_artifact_manifest_hash_match": bool(rav.manifest_hash_match if rav else False),
        "replay_artifact_forbidden_scan_pass": bool(rav.replay_forbidden_scan_pass if rav else False),
        "replay_artifact_failure_category": str(rav.failure_category if rav else ""),
        "replay_protocol_match": bool(audit_match),
        "replay_mismatch_reason": audit_mismatch_reason,
        "replay_match_basis": "fd1_committed_aggregate_and_validated_private_replay" if (pt and pt.computed and rav and rav.validated) else "fd1_committed_aggregate_only_no_validated_private_replay",
        "config_hash": p4._config_hash(),
    }]


def _denominator_records(denominator: list[Any]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str, str], int] = {}
    for d in denominator:
        key = (str(getattr(d, "source_phase", P4H_RAW_SOURCE_PHASE)),
               str(getattr(d, "benchmark", "")),
               str(getattr(d, "window_name", "raw_external_disjoint_scan")))
        counts[key] = counts.get(key, 0) + 1
    return [{
        "source_phase": sp,
        "benchmark": bm,
        "denominator_window": window,
        "denominator_record_count": int(cnt),
    } for (sp, bm, window), cnt in sorted(counts.items())]


def _denominator_scan_records(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("denominator_scan_records", [])
    return list(rows) if isinstance(rows, list) else []


def _prior_raw_exclusion_records(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("prior_raw_exclusion_records", [])
    return list(rows) if isinstance(rows, list) else []


def _arm_reach_records(arm_results: dict[str, list[p4.SchedulerReachResult]], denominator_count: int) -> list[dict[str, Any]]:
    return _p4_rows(p4._arm_reach_records, arm_results, denominator_count)


def _arm_delta_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _p4_rows(p4._arm_delta_records, arm_results)


def _arm_cost_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _p4_rows(p4._arm_cost_records, arm_results)


def _arm_action_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _p4_rows(p4._arm_action_records, arm_results)


def _channel_action_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return p4._channel_action_records(_compatible_arm_results(arm_results))


def _scheduler_stop_reason_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return p4._scheduler_stop_reason_records(_compatible_arm_results(arm_results))


def _latency_decomposition_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _replace_treatment_name(p4._latency_decomposition_records(_compatible_arm_results(arm_results)))


def _efficiency_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _p4_rows(p4._efficiency_records, arm_results)


def _reach_bucket_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _p4_rows(p4._reach_bucket_records, arm_results)


def _rank_band_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _p4_rows(p4._rank_band_records, arm_results)


def _cost_safety_records(arm_results: dict[str, list[p4.SchedulerReachResult]]) -> list[dict[str, Any]]:
    return _replace_treatment_name(p4._cost_safety_records(_compatible_arm_results(arm_results)))


def _group_results_by_subgroup(
    denominator: list[Any],
    arm_results: dict[str, list[p4.SchedulerReachResult]],
) -> dict[tuple[str, str], dict[str, list[p4.SchedulerReachResult]]]:
    rid_to_group = {f"{d.source_phase}:{d.private_record_id}": (d.source_phase, d.benchmark) for d in denominator}
    grouped: dict[tuple[str, str], dict[str, list[p4.SchedulerReachResult]]] = {}
    for arm in POLICY_ARMS:
        for rr in arm_results.get(arm, []):
            g = rid_to_group.get(rr.private_record_id)
            if g is None:
                continue
            grouped.setdefault(g, {a: [] for a in POLICY_ARMS})[arm].append(rr)
    return grouped


def _newly(results: list[p4.SchedulerReachResult], baseline: list[p4.SchedulerReachResult]) -> int:
    base = {r.private_record_id for r in baseline if r.gold_file_available}
    return sum(1 for r in results if r.gold_file_available and r.private_record_id not in base)


def _mean(vals: Sequence[float | int]) -> float:
    return float(statistics.mean(vals)) if vals else 0.0


def _subgroup_safety_records(
    denominator: list[Any],
    arm_results: dict[str, list[p4.SchedulerReachResult]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (sp, bm), arms in sorted(_group_results_by_subgroup(denominator, arm_results).items()):
        baseline = arms.get("current_bea_candidate_pool_replay", [])
        p2r = arms.get("p2_depth_only_reference", [])
        p4r = arms.get(P4H_TREATMENT_ARM, [])
        n = len(baseline)
        p2_gain = _newly(p2r, baseline)
        p4_gain = _newly(p4r, baseline)
        b_pool = _mean([r.candidate_pool_size for r in baseline])
        b_lat = _mean([r.retrieval_latency_seconds for r in baseline])
        p4_pool = _mean([r.candidate_pool_size for r in p4r])
        p4_lat = _mean([r.retrieval_latency_seconds for r in p4r])
        pool_mult = p4_pool / b_pool if b_pool > 0 else 0.0
        lat_mult = p4_lat / b_lat if b_lat > 0 else 0.0
        gain_ratio = p4_gain / p2_gain if p2_gain > 0 else 1.0
        mass_reported = n >= P4H_SUBGROUP_MIN_N
        passed = (not mass_reported) or (
            gain_ratio >= P4H_SUBGROUP_P2_GAIN_RATIO_MIN
            and pool_mult <= P4H_POOL_MULT_MAX
            and lat_mult <= P4H_LATENCY_MULT_MAX
        )
        rows.append({
            "source_phase": sp,
            "benchmark": bm,
            "subgroup_record_count": int(n),
            "subgroup_mass_reported": bool(mass_reported),
            "p2_depth_newly_reachable_count": int(p2_gain),
            "p4_frozen_newly_reachable_count": int(p4_gain),
            "p4_vs_p2_depth_gain_ratio": round(gain_ratio, 6),
            "p4_pool_multiplier": round(pool_mult, 6),
            "p4_latency_multiplier": round(lat_mult, 6),
            "subgroup_guard_passed": bool(passed),
        })
    return rows


def _rank_budget_audit_records(
    denominator_count: int,
    arm_results: dict[str, list[p4.SchedulerReachResult]],
) -> list[dict[str, Any]]:
    p4r = arm_results.get(P4H_TREATMENT_ARM, [])
    ranks = [r.first_gold_file_rank for r in p4r if r.first_gold_file_rank > 0]
    mean_rank = statistics.mean(ranks) if ranks else 0.0
    above = sum(1 for r in p4r if r.first_gold_file_rank > FIXED_BUDGET)
    threshold_records = math.ceil(P4H_RANK_BUDGET_RECORDS_AT_119 * max(denominator_count, 1) / ORIGINAL_P1234_DENOMINATOR_COUNT)
    confirmed = mean_rank > P4H_RANK_BUDGET_MEAN_RANK_MIN or above >= threshold_records
    return [{
        "audit_name": "p4h_rank_budget_bottleneck",
        "treatment_arm": P4H_TREATMENT_ARM,
        "denominator_record_count": int(denominator_count),
        "first_reachable_gold_rank_mean": round(mean_rank, 6),
        "records_first_reachable_gold_rank_above_budget": int(above),
        "rank_budget": int(FIXED_BUDGET),
        "mean_rank_threshold": float(P4H_RANK_BUDGET_MEAN_RANK_MIN),
        "records_above_budget_threshold": int(threshold_records),
        "rank_budget_bottleneck_confirmed": bool(confirmed),
        "selector_phase_justified": bool(confirmed),
    }]


def _failure_category_count_records(fcc: dict[str, int]) -> list[dict[str, Any]]:
    return [{"failure_category": str(k), "count": int(v)} for k, v in sorted(fcc.items())]


def _blocking_failure_count(fcc: dict[str, int]) -> int:
    return sum(int(fcc.get(cat, 0)) for cat in BLOCKING_FAILURE_CATEGORIES)


def _private_manifest_records(fd1_artifact: dict[str, Any], extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return p4._private_manifest_records(fd1_artifact, "fd1_committed_artifact", extra_manifests=extra or [])


def _scaled_count(records_at_119: int, denominator_count: int) -> int:
    return int(math.ceil(records_at_119 * max(denominator_count, 1) / ORIGINAL_P1234_DENOMINATOR_COUNT))


def _compute_decision_metrics(
    denominator_count: int,
    arm_results: dict[str, list[p4.SchedulerReachResult]],
    subgroup_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    p2r = arm_results.get("p2_depth_only_reference", [])
    p3r = arm_results.get("p3_constrained_depth_policy_reference", [])
    p4r = arm_results.get(P4H_TREATMENT_ARM, [])
    p2_new = _newly(p2r, baseline)
    p3_new = _newly(p3r, baseline)
    p4_new = _newly(p4r, baseline)
    b_pool = _mean([r.candidate_pool_size for r in baseline])
    b_lat = _mean([r.retrieval_latency_seconds for r in baseline])
    p3_lat = _mean([r.retrieval_latency_seconds for r in p3r])
    p4_pool = _mean([r.candidate_pool_size for r in p4r])
    p4_lat = _mean([r.retrieval_latency_seconds for r in p4r])
    p4_pool_mult = p4_pool / b_pool if b_pool > 0 else 0.0
    p4_lat_mult = p4_lat / b_lat if b_lat > 0 else 0.0
    latency_vs_p3 = (p3_lat - p4_lat) / p3_lat if p3_lat > 0 else 0.0
    hard_cap = sum(1 for r in p4r if r.candidate_pool_size > p4.P4_HARD_CANDIDATE_CAP)
    p4_actions = [r.extra_depth_actions_executed for r in p4r]
    p3_actions = [r.p3_action_count_reference for r in p4r]
    mean_p4_actions = _mean(p4_actions)
    mean_p3_actions = _mean(p3_actions)
    action_share_reduced = ((mean_p3_actions - mean_p4_actions) / mean_p3_actions) if mean_p3_actions > 0 else 0.0
    records_fewer_actions = sum(1 for a, b in zip(p4_actions, p3_actions) if a < b)
    action_records_min = _scaled_count(P4H_ACTION_REDUCTION_RECORDS_AT_119, denominator_count)
    p4_abs_min = _scaled_count(p4.P4_REACH_PRESERVATION_NEWLY_MIN, denominator_count)
    reach_ok = (
        p4_new >= P4H_REACH_P2_RATIO_MIN * p2_new
        or p4_new >= p4_abs_min
    ) and (p3_new <= 0 or p4_new >= P4H_REACH_P3_RATIO_MIN * p3_new)
    latency_ok = p4_lat_mult <= P4H_LATENCY_MULT_MAX and latency_vs_p3 >= P4H_LATENCY_VS_P3_IMPROVEMENT_MIN
    cost_ok = p4_pool_mult <= P4H_POOL_MULT_MAX and hard_cap <= P4H_HARD_CAP_VIOLATION_MAX
    action_ok = action_share_reduced >= P4H_ACTION_REDUCTION_SHARE_MIN or records_fewer_actions >= action_records_min
    subgroup_ok = all(r.get("subgroup_guard_passed") is True for r in subgroup_rows)
    private_rows = sum(len(arm_results.get(a, [])) for a in POLICY_ARMS)
    return {
        "baseline_reach": sum(1 for r in baseline if r.gold_file_available),
        "p2_depth_reach": sum(1 for r in p2r if r.gold_file_available),
        "p3_reference_reach": sum(1 for r in p3r if r.gold_file_available),
        "p4_frozen_reach": sum(1 for r in p4r if r.gold_file_available),
        "p2_newly_reachable_count": int(p2_new),
        "p3_newly_reachable_count": int(p3_new),
        "p4_newly_reachable_count": int(p4_new),
        "p4_reach_abs_min": int(p4_abs_min),
        "p4_pool_multiplier": round(p4_pool_mult, 6),
        "p4_latency_multiplier": round(p4_lat_mult, 6),
        "latency_vs_p3_improvement": round(latency_vs_p3, 6),
        "hard_cap_violation_count": int(hard_cap),
        "p4_mean_extra_depth_actions": round(mean_p4_actions, 6),
        "p3_mean_extra_depth_actions": round(mean_p3_actions, 6),
        "action_share_reduced": round(action_share_reduced, 6),
        "records_with_fewer_actions": int(records_fewer_actions),
        "action_reduction_records_min": int(action_records_min),
        "reach_replicated": bool(reach_ok),
        "latency_fixed": bool(latency_ok),
        "cost_safe": bool(cost_ok),
        "action_reduction_material": bool(action_ok),
        "subgroup_safety_passed": bool(subgroup_ok),
        "private_scheduler_rows": int(private_rows),
        "expected_private_scheduler_rows": int(denominator_count * len(POLICY_ARMS)),
    }


def _stop_go_records(
    *, denominator_count: int, retrieval_policy_executed: bool,
    replay_validated: bool, disjoint: bool, raw_scan_attempted: bool,
    metrics: dict[str, Any],
    rank_audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if denominator_count < P4H_MIN_DENOMINATOR_COUNT and raw_scan_attempted:
        decision = "no_go_p4h_insufficient_denominator"
        reason = f"heldout_denominator_count={denominator_count}; min={P4H_MIN_DENOMINATOR_COUNT}"
    elif not (retrieval_policy_executed and replay_validated and disjoint and raw_scan_attempted):
        decision = "no_go_p4h_replay_mismatch"
        reason = "retrieval_not_executed_or_replay_not_validated_or_denominator_not_disjoint_or_raw_scan_not_attempted"
    elif metrics.get("private_scheduler_rows") != metrics.get("expected_private_scheduler_rows"):
        decision = "no_go_p4h_replay_mismatch"
        reason = "private_scheduler_rows_mismatch"
    elif not metrics.get("latency_fixed", False):
        decision = "no_go_p4h_latency_not_fixed"
        reason = "p4h_latency_gate_failed"
    elif not metrics.get("cost_safe", False):
        decision = "no_go_p4h_cost_exceeded"
        reason = "p4h_pool_or_hard_cap_gate_failed"
    elif not metrics.get("reach_replicated", False):
        decision = "no_go_p4h_reach_not_replicated"
        reason = "p4h_reach_replication_gate_failed"
    elif not (metrics.get("action_reduction_material", False) and metrics.get("subgroup_safety_passed", False)):
        decision = "no_go_p4h_policy_degenerate"
        reason = "p4h_action_reduction_or_subgroup_guard_failed"
    else:
        decision = "bea_v1_p4h_disjoint_scheduler_validation_pass"
        reason = "frozen_p4_scheduler_replicated_on_disjoint_heldout"
    audit = rank_audit[0] if rank_audit else {}
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "denominator_record_count": int(denominator_count),
        "denominator_min": int(P4H_MIN_DENOMINATOR_COUNT),
        "denominator_disjoint_from_prior": bool(disjoint),
        "raw_denominator_scan_attempted": bool(raw_scan_attempted),
        **metrics,
        "reach_p2_ratio_min": P4H_REACH_P2_RATIO_MIN,
        "reach_p3_ratio_min": P4H_REACH_P3_RATIO_MIN,
        "latency_mult_max": P4H_LATENCY_MULT_MAX,
        "latency_vs_p3_improvement_min": P4H_LATENCY_VS_P3_IMPROVEMENT_MIN,
        "pool_mult_max": P4H_POOL_MULT_MAX,
        "hard_cap_violation_max": P4H_HARD_CAP_VIOLATION_MAX,
        "action_reduction_share_min": P4H_ACTION_REDUCTION_SHARE_MIN,
        "rank_budget_bottleneck_confirmed": bool(audit.get("rank_budget_bottleneck_confirmed", False)),
        "selector_phase_justified": bool(audit.get("selector_phase_justified", False) and decision == "bea_v1_p4h_disjoint_scheduler_validation_pass"),
    }]


def _gate_records(
    *, fd1_records_decomposed: int, fd1_private_manifest_record_count: int,
    denominator_meta: dict[str, Any], denominator_count: int,
    fd1_private_decomposition_parsed: bool, replay_artifact_validated: bool,
    retrieval_policy_executed: bool, forbidden_scan_pass: bool,
    blocking_failure_count: int, metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    def g(name: str, value: float, relation: str, threshold: float, passed: bool) -> dict[str, Any]:
        return {"gate": name, "value": round(float(value), 6), "threshold_relation": relation, "threshold_value": round(float(threshold), 6), "passed": bool(passed)}
    return [
        g("fd1_records_decomposed", fd1_records_decomposed, "==", EXPECTED_RECORDS_DECOMPOSED, fd1_records_decomposed == EXPECTED_RECORDS_DECOMPOSED),
        g("fd1_private_manifest_record_count", fd1_private_manifest_record_count, "==", EXPECTED_PRIVATE_DECOMP_ROWS, fd1_private_manifest_record_count == EXPECTED_PRIVATE_DECOMP_ROWS),
        g("fd1_private_decomposition_parsed", 1.0 if fd1_private_decomposition_parsed else 0.0, "boolean", 1.0, fd1_private_decomposition_parsed),
        g("replay_artifact_validated", 1.0 if replay_artifact_validated else 0.0, "boolean", 1.0, replay_artifact_validated),
        g("raw_denominator_scan_attempted", 1.0 if denominator_meta.get("raw_denominator_scan_attempted", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("raw_denominator_scan_attempted", False))),
        g("raw_denominator_attempted_records", denominator_meta.get("raw_scan_attempted_records", 0), ">=", denominator_count, denominator_meta.get("raw_scan_attempted_records", 0) >= denominator_count),
        g("prior_raw_windows_excluded", 1.0 if denominator_meta.get("prior_raw_windows_excluded", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("prior_raw_windows_excluded", False))),
        g("denominator_disjoint_from_prior", 1.0 if denominator_meta.get("disjoint_from_prior", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("disjoint_from_prior", False))),
        g("denominator_count_min", denominator_count, ">=", P4H_MIN_DENOMINATOR_COUNT, denominator_count >= P4H_MIN_DENOMINATOR_COUNT),
        g("private_scheduler_rows", metrics.get("private_scheduler_rows", 0), "==", metrics.get("expected_private_scheduler_rows", denominator_count * len(POLICY_ARMS)), metrics.get("private_scheduler_rows", 0) == metrics.get("expected_private_scheduler_rows", denominator_count * len(POLICY_ARMS))),
        g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0, "boolean", 1.0, forbidden_scan_pass),
        g("provider_calls_made", 0.0, "boolean_false", 0.0, True),
        g("latency_in_candidate_relevance", 0.0, "boolean_false", 0.0, True),
        g("retrieval_policy_executed", 1.0 if retrieval_policy_executed else 0.0, "boolean", 1.0, retrieval_policy_executed),
        g("blocking_failure_count", blocking_failure_count, "==", 0.0, blocking_failure_count == 0),
        g("subgroup_safety_passed", 1.0 if metrics.get("subgroup_safety_passed", False) else 0.0, "boolean", 1.0, bool(metrics.get("subgroup_safety_passed", False))),
    ]


FORBIDDEN_PUBLIC_KEYS = frozenset({
    "private_trace_dir", "trace_dir", "private_score_dir", "private_audit_dir",
    "private_decomposition_dir", "private_reach_dir", "private_scheduler_dir",
    "private_decomposition_path", "private_reach_path", "private_scheduler_path",
    "retrieval_trace_path", "candidate_trace_path", "scheduler_trace_path",
    "per_record_reach", "per_record_candidates", "per_record_policy",
    "per_record_diagnostics", "per_record_actions", "per_record_scheduler",
    "per_record_channel_actions", "record_candidate_lists", "candidate_paths",
    "candidate_keys", "candidate_list", "candidates", "final_candidates",
    "query_text", "queries", "query_variants", "gold_paths", "gold_lines",
    "gold_spans", "gold_content", "gold_files", "gold_file_set",
    "snippets", "selected_paths", "selected_order", "private_record_ids",
    "record_ids", "private_record_id", "benchmark_row_id", "phase_run_id",
    "run_id", "task_id", "row_id", "needle_id", "instance_id", "repo_url",
    "base_commit", "repo_slug", "repo_name", "raw_score_row", "raw_decision_row",
    "raw_feature_row", "raw_decomposition_row", "raw_reach_row",
    "raw_candidate_row", "raw_policy_row", "raw_scheduler_row",
    "fd1_source_artifact_path", "fd1_replay_artifact_path", "scheduler_results_path",
    "recommended_default", "recommended_method", "preferred_method",
    "default_method", "policy_decision", "decision", "ranking", "rank",
    "winner", "leaderboard", "promotion", "calibration", "method_winner",
    "best_method", "self_test_checks", "self_test_details", "self_test_list",
    "checks", "check_list", "hard_gates", "failure_category_counts",
    "arm_reach_counts", "arm_delta_counts", "arm_cost_counts",
    "arm_action_counts", "channel_action_counts", "scheduler_stop_reason_counts",
    "latency_decomposition_counts", "stop_go_counts", "role_proxy",
    "role_proxy_assignment", "target_proxy", "support_proxy", "role_proxy_used",
})


def _scan_v1_p4h(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    def walk(o: Any, path: str = "$", parent: str = "") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sub = f"{path}.{ks}"
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_v1_p4h_public_key", "path": sub})
                if isinstance(v, str) and len(v) > 240 and ks not in {"stop_go_reason"}:
                    violations.append({"category": "long_string", "path": sub})
                walk(v, sub, ks)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]", parent)
    walk(obj)
    return violations


def _v1_p4h_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p4h(obj)
    cats: dict[str, int] = {}
    for v in violations:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "categories": cats}


def _enforce_v1_p4h_no_forbidden(obj: Any) -> None:
    if _v1_p4h_forbidden_scan_summary(obj)["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


def _empty_metrics() -> dict[str, Any]:
    return {
        "baseline_reach": 0, "p2_depth_reach": 0, "p3_reference_reach": 0,
        "p4_frozen_reach": 0, "p2_newly_reachable_count": 0,
        "p3_newly_reachable_count": 0, "p4_newly_reachable_count": 0,
        "p4_reach_abs_min": 0, "p4_pool_multiplier": 0.0,
        "p4_latency_multiplier": 0.0, "latency_vs_p3_improvement": 0.0,
        "hard_cap_violation_count": 0, "p4_mean_extra_depth_actions": 0.0,
        "p3_mean_extra_depth_actions": 0.0, "action_share_reduced": 0.0,
        "records_with_fewer_actions": 0, "action_reduction_records_min": 0,
        "reach_replicated": False, "latency_fixed": False, "cost_safe": False,
        "action_reduction_material": False, "subgroup_safety_passed": False,
        "private_scheduler_rows": 0, "expected_private_scheduler_rows": 0,
    }


def _base_report(
    *, status: str, failure_reason_category: str, self_test_passed: bool,
    self_test_checks_total: int, self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any] | None = None,
    fd1_schema: str = "", fd1_hash: str = "", pt: Any = None,
    rav: Any = None, denominator: list[Any] | None = None,
    denominator_meta: dict[str, Any] | None = None,
    arm_results: dict[str, list[p4.SchedulerReachResult]] | None = None,
    retrieval_policy_executed: bool = False, audit_match: bool = False,
    audit_mismatch_reason: str = "", fcc_in: dict[str, int] | None = None,
    extra_manifests: list[dict[str, Any]] | None = None,
    aggregate_runtime_seconds: float = 0.0,
) -> dict[str, Any]:
    fd1_artifact = fd1_artifact or {}
    denominator = denominator or []
    denominator_meta = denominator_meta or {"denominator_source_protocol": "raw_external_full_frame_disjoint_success_quota_scan.v1", "raw_denominator_scan_attempted": False, "raw_scan_attempted_records": 0, "raw_scan_yield_file_miss_records": len(denominator), "prior_fd1_denominator_reused": False, "prior_raw_windows_excluded": True, "heldout_denominator_count": len(denominator), "disjoint_from_prior": True, "private_key_hashes_publicly_serialized": False, "denominator_constructed_before_scheduler_outcomes": True, "denominator_scan_records": [], "prior_raw_exclusion_records": []}
    arm_results = arm_results or {a: [] for a in POLICY_ARMS}
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    for k, v in (fcc_in or {}).items():
        if k in fcc:
            fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)
    fd1_status = p4.bea_v1_p1._fd1_status(fd1_artifact)
    fd1_records = p4.bea_v1_p1._fd1_records_decomposed(fd1_artifact)
    fd1_manifest = p4.bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact)
    fd1_manifest_count = int(fd1_manifest.get("record_count", 0) or 0)
    fd1_private_parsed = bool(pt is not None and getattr(pt, "computed", False) and getattr(pt, "row_count", 0) == EXPECTED_PRIVATE_DECOMP_ROWS and getattr(pt, "group_count", 0) == EXPECTED_RECORDS_DECOMPOSED)
    replay_validated = bool(rav is not None and getattr(rav, "validated", False))
    subgroup_rows = _subgroup_safety_records(denominator, arm_results)
    rank_audit = _rank_budget_audit_records(len(denominator), arm_results)
    metrics = _compute_decision_metrics(len(denominator), arm_results, subgroup_rows) if retrieval_policy_executed else _empty_metrics()
    stop_go = _stop_go_records(
        denominator_count=len(denominator), retrieval_policy_executed=retrieval_policy_executed,
        replay_validated=replay_validated, disjoint=bool(denominator_meta.get("disjoint_from_prior", False)),
        raw_scan_attempted=bool(denominator_meta.get("raw_denominator_scan_attempted", False)),
        metrics=metrics, rank_audit=rank_audit)
    blocking = _blocking_failure_count(fcc)
    if status == "auto":
        if blocking > 0:
            status = "fail_schema_contract"
        elif stop_go[0]["stop_go_decision"] in STATUSES:
            status = stop_go[0]["stop_go_decision"]
        else:
            status = "no_go_p4h_policy_degenerate"
    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true.update({
        "fd1_artifact_read": bool(fd1_artifact),
        "fd1_private_decomposition_parsed": fd1_private_parsed,
        "fd1_private_decomposition_replay_supplied": bool(rav.supplied if rav else False),
        "fd1_private_decomposition_replay_validated": replay_validated,
        "fd1_private_decomposition_replay_executed_by_workflow": bool(rav.supplied and rav.validated) if rav else False,
        "retrieval_policy_executed": bool(retrieval_policy_executed),
    })
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "budget": FIXED_BUDGET,
        "methods": list(FIXED_METHODS),
        "policy_arms": list(POLICY_ARMS),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": str(denominator_meta.get("denominator_source_protocol", "raw_external_full_frame_disjoint_success_quota_scan.v1")),
        "records_decomposed": int(fd1_records),
        "private_manifest_record_count": int(fd1_manifest_count),
        "denominator_count": int(len(denominator)),
        "failure_reason_category": failure_reason_category,
        "source_run_records": _source_run_records(fd1_schema_version=fd1_schema, fd1_source_artifact_hash=fd1_hash, fd1_status=fd1_status, fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, pt=pt, rav=rav, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason),
        "denominator_records": _denominator_records(denominator),
        "denominator_scan_records": _denominator_scan_records(denominator_meta),
        "prior_raw_exclusion_records": _prior_raw_exclusion_records(denominator_meta),
        "arm_reach_records": _arm_reach_records(arm_results, len(denominator)),
        "arm_delta_records": _arm_delta_records(arm_results),
        "arm_cost_records": _arm_cost_records(arm_results),
        "arm_action_records": _arm_action_records(arm_results),
        "channel_action_records": _channel_action_records(arm_results),
        "scheduler_stop_reason_records": _scheduler_stop_reason_records(arm_results),
        "latency_decomposition_records": _latency_decomposition_records(arm_results),
        "efficiency_records": _efficiency_records(arm_results),
        "reach_bucket_records": _reach_bucket_records(arm_results),
        "rank_band_records": _rank_band_records(arm_results),
        "cost_safety_records": _cost_safety_records(arm_results),
        "subgroup_safety_records": subgroup_rows,
        "rank_budget_audit_records": rank_audit,
        "stop_go_records": stop_go,
        "gate_records": _gate_records(fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, denominator_meta=denominator_meta, denominator_count=len(denominator), fd1_private_decomposition_parsed=fd1_private_parsed, replay_artifact_validated=replay_validated, retrieval_policy_executed=retrieval_policy_executed, forbidden_scan_pass=True, blocking_failure_count=blocking, metrics=metrics),
        "private_manifest_records": _private_manifest_records(fd1_artifact, extra_manifests),
        "failure_category_count_records": _failure_category_count_records(fcc),
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "raw_denominator_scan_attempted": bool(denominator_meta.get("raw_denominator_scan_attempted", False)),
        "raw_scan_attempted_records": int(denominator_meta.get("raw_scan_attempted_records", 0)),
        "raw_scan_prior_exact_excluded_records": int(denominator_meta.get("raw_scan_prior_exact_excluded_records", 0)),
        "raw_scan_prior_window_excluded_records": int(denominator_meta.get("raw_scan_prior_window_excluded_records", 0)),
        "raw_scan_yield_file_miss_records": int(denominator_meta.get("raw_scan_yield_file_miss_records", 0)),
        "prior_raw_exclusion_mode": str(denominator_meta.get("prior_raw_exclusion_mode", "not_attempted")),
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": bool(denominator_meta.get("prior_raw_windows_excluded", True)),
        "denominator_source_gold_file_absent_count": int(denominator_meta.get("source_gold_file_absent_count", 0)),
        "excluded_prior_windows_count": int(denominator_meta.get("excluded_prior_window_count", 0)),
        "denominator_disjoint_from_prior": bool(denominator_meta.get("disjoint_from_prior", False)),
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": bool(denominator_meta.get("denominator_constructed_before_scheduler_outcomes", True)),
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": bool(self_test_passed),
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(self_test_checks_total if self_test_checks_passed is None and self_test_passed else (self_test_checks_passed or 0)),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "heldout_validation_claimed": False,
            "signal_strength": "bea_v1_p4h_disjoint_scheduler_validation_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_latency_aware_retrieval_scheduler_validation": True,
            "is_latency_in_relevance": False,
        },
    }
    scan = _v1_p4h_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _resolve_private_scheduler_dir() -> Path:
    raw = os.environ.get("OPENLOCUS_BEA_V1_P4H_PRIVATE_SCHEDULER_DIR", "")
    base = Path(raw) if raw else Path(f"/tmp/openlocus_bea_v1_p4h_scheduler_{os.getpid()}")
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private scheduler dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _parse_raw_row_for_retrieval(
    benchmark: str, row: dict[str, Any],
) -> tuple[str, list[str], str, str, bool]:
    if benchmark == "contextbench":
        gold_paths, _, gc_status = p4.c5a._parse_gold_context(row.get("gold_context"))
        query = p4.c5a._sanitize_query(row.get("problem_statement", ""), "first_paragraph")
        repo_url = str(row.get("repo_url", "") or "")
        base_commit = str(row.get("base_commit", "") or "")
        ok = gc_status == "pass" and bool(gold_paths) and bool(query) and bool(repo_url) and bool(base_commit)
        return query, [str(x) for x in gold_paths if x], repo_url, base_commit, ok
    needle_path = str(row.get("needle_path", row.get("path", "")) or "")
    gold_paths = [needle_path] if needle_path else []
    query = p4.c5d._sanitize_needle_description(str(row.get("needle_description", row.get("description", "")) or ""))
    repo_url = str(row.get("repo_url", "") or "")
    base_commit = str(row.get("commit_sha", row.get("base_commit", "")) or "")
    ok = bool(gold_paths) and bool(query) and bool(repo_url) and bool(base_commit)
    return query, gold_paths, repo_url, base_commit, ok


def _initial_raw_scan_rows() -> list[dict[str, Any]]:
    return [{
        "source_phase": P4H_RAW_SOURCE_PHASE,
        "benchmark": str(w["benchmark"]),
        "denominator_window": str(w["window_name"]),
        "raw_offset_requested": int(w["raw_offset_requested"]),
        "raw_limit_requested": int(w["raw_limit_requested"]),
        "scan_protocol": "full_frame_disjoint_success_quota",
        "raw_rows_fetched": 0,
        "raw_rows_attempted": 0,
        "raw_rows_prior_exact_excluded": 0,
        "raw_rows_prior_window_excluded": 0,
        "raw_rows_parse_excluded": 0,
        "raw_rows_clone_excluded": 0,
        "raw_rows_baseline_reached_excluded": 0,
        "raw_rows_baseline_error_excluded": 0,
        "raw_rows_file_miss_selected": 0,
        "target_reached_in_window": False,
    } for w in P4H_RAW_WINDOWS]


def _scan_raw_heldout_denominator(
    *, openlocus_bin: str, pt: p4.bea_v1_p1.ParsedPrivateDecomposition | None,
) -> tuple[list[RawHeldoutDenominatorRecord], dict[str, int], dict[str, Any], dict[str, Any]]:
    """Scan full available raw frames with the baseline arm only.

    P2/P3/P4 treatment arms are not run here. The baseline result is cached on
    each selected denominator record and reused by the scheduler phase.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    denominator: list[RawHeldoutDenominatorRecord] = []
    scan_rows = _initial_raw_scan_rows()
    row_by_window = {r["denominator_window"]: r for r in scan_rows}
    private_dir = _resolve_private_scheduler_dir()
    private_path = private_dir / "bea_v1_p4h.private_denominator_scan.jsonl"
    if private_path.exists():
        private_path.unlink()
    attempted_total = 0
    fetched_total = 0
    excluded_prior_exact_total = 0
    excluded_prior_window_total = 0
    prior_raw_keys, exact_exclusion_records = _prior_raw_keys_from_fd1_private(pt)
    use_exact_prior_keys = bool(prior_raw_keys)
    explicit_window_records: list[dict[str, Any]] = []
    for w in P4H_RAW_WINDOWS:
        bm = str(w["benchmark"])
        for start, end, label in _raw_prior_exclusion_windows(bm):
            explicit_window_records.append({
                "source_phase": P4H_RAW_SOURCE_PHASE,
                "benchmark": bm,
                "exclusion_source_phase": "prior_fixed_window",
                "exclusion_basis": label,
                "excluded_window_start_inclusive": start,
                "excluded_window_end_exclusive": end,
                "exclusion_window_publicly_disclosed": True,
                "used_for_exclusion": not use_exact_prior_keys,
                "private_row_ids_publicly_serialized": False,
            })
    for w in P4H_RAW_WINDOWS:
        bm = str(w["benchmark"])
        window = str(w["window_name"])
        offset = int(w["raw_offset_requested"])
        limit = int(w["raw_limit_requested"])
        srow = row_by_window[window]
        if bm == "contextbench":
            rows, fetch_status, _, fetch_fcc = p4.bea4._fetch_heldout_contextbench_rows(offset, limit)
        else:
            rows, fetch_status, _, fetch_fcc = p4.bea4._fetch_heldout_repoqa_needles(offset, limit)
        for k, v in fetch_fcc.items():
            if k in fcc:
                fcc[k] += int(v)
        if fetch_status != "pass":
            fcc["raw_denominator_scan_failed"] += 1
            continue
        srow["raw_rows_fetched"] = len(rows)
        fetched_total += len(rows)
        if len(rows) > limit:
            fcc["raw_denominator_scan_failed"] += 1
            continue
        for local_idx, row in enumerate(rows):
            if len(denominator) >= P4H_RAW_DENOMINATOR_TARGET_COUNT:
                srow["target_reached_in_window"] = True
                break
            raw_idx = offset + local_idx
            if use_exact_prior_keys and (bm, raw_idx) in prior_raw_keys:
                srow["raw_rows_prior_exact_excluded"] += 1
                excluded_prior_exact_total += 1
                continue
            if not use_exact_prior_keys and _raw_index_exclusion_reason(bm, raw_idx):
                srow["raw_rows_prior_window_excluded"] += 1
                excluded_prior_window_total += 1
                continue
            attempted_total += 1
            srow["raw_rows_attempted"] += 1
            query, gold_paths, repo_url, base_commit, ok = _parse_raw_row_for_retrieval(bm, row)
            private_record_id = f"{bm}-raw-{raw_idx}"
            if not ok:
                srow["raw_rows_parse_excluded"] += 1
                fcc["raw_denominator_parse_failed"] += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"v1p4h_scan_{bm}_{raw_idx}_") as tmp:
                work = Path(tmp)
                clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += int(v)
                if not clone_ok:
                    srow["raw_rows_clone_excluded"] += 1
                    fcc["raw_denominator_clone_failed"] += 1
                    continue
                repo_root = work / "repo"
                rr_base = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
                rr_base.private_record_id = f"{P4H_RAW_SOURCE_PHASE}:{private_record_id}"
                if rr_base.retrieval_error:
                    srow["raw_rows_baseline_error_excluded"] += 1
                    fcc["retrieval_policy_failed"] += 1
                    continue
                p4._append_private_jsonl(private_path, {
                    "schema_version": "bea_v1_p4h_private_denominator_scan.v1",
                    "source_phase": P4H_RAW_SOURCE_PHASE,
                    "benchmark": bm,
                    "window_name": window,
                    "raw_record_index_private": raw_idx,
                    "private_record_id": private_record_id,
                    "query_private": query[:200],
                    "repo_url_private": repo_url,
                    "base_commit_private": base_commit,
                    "gold_paths_private": gold_paths,
                    "baseline_gold_file_available": rr_base.gold_file_available,
                    "baseline_first_gold_file_rank": rr_base.first_gold_file_rank,
                    "baseline_candidate_pool_size": rr_base.candidate_pool_size,
                    "baseline_candidate_paths_private": rr_base.candidate_paths_private,
                    "selected_for_denominator": not rr_base.gold_file_available,
                    "config_hash": p4._config_hash(),
                })
                if rr_base.gold_file_available:
                    srow["raw_rows_baseline_reached_excluded"] += 1
                    continue
                srow["raw_rows_file_miss_selected"] += 1
                denominator.append(RawHeldoutDenominatorRecord(
                    private_record_id=private_record_id,
                    benchmark=bm,
                    record_index=raw_idx,
                    window_name=window,
                    raw_window_offset=offset,
                    raw_window_limit=limit,
                    query_private=query,
                    repo_url_private=repo_url,
                    base_commit_private=base_commit,
                    gold_paths_private=gold_paths,
                    baseline_result=rr_base,
                ))
        if len(denominator) >= P4H_RAW_DENOMINATOR_TARGET_COUNT:
            break
    meta = {
        "denominator_source_protocol": "raw_external_full_frame_disjoint_success_quota_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "heldout_denominator_count": len(denominator),
        "raw_denominator_scan_attempted": True,
        "raw_scan_fetched_records": int(fetched_total),
        "raw_scan_attempted_records": int(attempted_total),
        "raw_scan_prior_exact_excluded_records": int(excluded_prior_exact_total),
        "raw_scan_prior_window_excluded_records": int(excluded_prior_window_total),
        "raw_scan_yield_file_miss_records": int(len(denominator)),
        "raw_scan_target_count": P4H_RAW_DENOMINATOR_TARGET_COUNT,
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": True,
        "prior_raw_exclusion_mode": "fd1_private_exact_raw_keys" if use_exact_prior_keys else "explicit_public_index_windows",
        "disjoint_from_prior": True,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": scan_rows,
        "prior_raw_exclusion_records": exact_exclusion_records + explicit_window_records,
    }
    manifest = p4._private_file_manifest(private_path, manifest_name="bea_v1_p4h_private_denominator_scan_manifest", schema_version="bea_v1_p4h_private_denominator_scan.v1")
    return denominator, fcc, meta, manifest


def _execute_retrieval_scheduler(
    *, openlocus_bin: str, denominator: list[RawHeldoutDenominatorRecord],
) -> tuple[dict[str, list[p4.SchedulerReachResult]], dict[str, int], dict[str, Any]]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    arm_results: dict[str, list[p4.SchedulerReachResult]] = {a: [] for a in POLICY_ARMS}
    private_dir = _resolve_private_scheduler_dir()
    private_path = private_dir / "bea_v1_p4h.private_scheduler.jsonl"
    if private_path.exists():
        private_path.unlink()
    for d in denominator:
        with tempfile.TemporaryDirectory(prefix=f"v1p4h_sched_{d.benchmark}_{d.record_index}_") as tmp:
            work = Path(tmp)
            clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(d.repo_url_private, d.base_commit_private, work)
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if not clone_ok:
                fcc["denominator_mapping_failed"] += 1
                fcc["raw_denominator_clone_failed"] += 1
                continue
            repo_root = work / "repo"
            gold_set = {str(x) for x in d.gold_paths_private if x}
            rid = f"{d.source_phase}:{d.private_record_id}"
            rr_base = d.baseline_result or p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=d.query_private, gold_set=gold_set)
            rr_depth = p4._run_depth_reference_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=d.query_private, gold_set=gold_set)
            rr_p3 = p4._run_p3_reference_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=d.query_private, gold_set=gold_set)
            rr_p4 = p4._run_p4_latency_aware_scheduler_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=d.query_private, gold_set=gold_set)
            rr_p4.arm_name = P4H_TREATMENT_ARM
            rr_p4.p3_action_count_reference = rr_p3.p3_action_count_reference
            for rr in (rr_base, rr_depth, rr_p3, rr_p4):
                rr.private_record_id = rid
            arm_results["current_bea_candidate_pool_replay"].append(rr_base)
            arm_results["p2_depth_only_reference"].append(rr_depth)
            arm_results["p3_constrained_depth_policy_reference"].append(rr_p3)
            arm_results[P4H_TREATMENT_ARM].append(rr_p4)
            for rr in (rr_base, rr_depth, rr_p3, rr_p4):
                p4._append_private_jsonl(private_path, {
                    "schema_version": "bea_v1_p4h_private_scheduler.v1",
                    "source_phase": d.source_phase,
                    "benchmark": d.benchmark,
                    "window_name": d.window_name,
                    "private_record_id": d.private_record_id,
                    "arm_name": rr.arm_name,
                    "gold_file_available": rr.gold_file_available,
                    "first_gold_file_rank": rr.first_gold_file_rank,
                    "candidate_pool_size": rr.candidate_pool_size,
                    "retrieval_latency_seconds": round(rr.retrieval_latency_seconds, 6),
                    "candidate_paths_private": rr.candidate_paths_private,
                    "query_private": d.query_private[:200],
                    "scheduler_action": rr.scheduler_action,
                    "scheduler_stop_reason": rr.scheduler_stop_reason,
                    "extra_depth_actions_executed": rr.extra_depth_actions_executed,
                    "p3_action_count_reference": rr.p3_action_count_reference,
                    "config_hash": p4._config_hash(),
                })
                if rr.retrieval_error:
                    fcc["retrieval_policy_failed"] += 1
    expected_rows = len(denominator) * len(POLICY_ARMS)
    actual_rows = sum(len(arm_results.get(a, [])) for a in POLICY_ARMS)
    if actual_rows != expected_rows:
        fcc["private_scheduler_rows_mismatch"] += 1
    manifest = p4._private_file_manifest(private_path, manifest_name="bea_v1_p4h_private_scheduler_manifest", schema_version="bea_v1_p4h_private_scheduler.v1")
    return arm_results, fcc, manifest


def _run_scheduler_validation(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int, fd1_artifact_path: Path,
    fd1_private_decomposition_jsonl: Path | None, fd1_replay_artifact: Path | None,
    enable_network: bool,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    start = time.perf_counter()
    fd1_artifact, fd1_schema, fd1_hash, fd1_status = p4._load_committed_artifact(fd1_artifact_path)
    if fd1_status != "pass":
        fcc["fd1_artifact_missing" if fd1_status == "artifact_missing" else "fd1_artifact_parse_failed"] = 1
        return _base_report(status="unavailable_with_reason", failure_reason_category=fd1_status, self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fcc_in=fcc)
    mismatch: list[str] = []
    fd1_artifact_status = p4.bea_v1_p1._fd1_status(fd1_artifact)
    fd1_records = p4.bea_v1_p1._fd1_records_decomposed(fd1_artifact)
    fd1_manifest = p4.bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact)
    fd1_manifest_count = int(fd1_manifest.get("record_count", 0) or 0)
    if fd1_schema != p4.FD1_SOURCE_SCHEMA_VERSION:
        fcc["fd1_schema_version_mismatch"] = 1; mismatch.append("fd1_schema_version_mismatch")
    if fd1_artifact_status != p4.FD1_SOURCE_STATUS:
        fcc["fd1_status_mismatch"] = 1; mismatch.append("fd1_status_mismatch")
    if fd1_records != EXPECTED_RECORDS_DECOMPOSED:
        fcc["fd1_records_decomposed_mismatch"] = 1; mismatch.append("fd1_records_decomposed_mismatch")
    if fd1_manifest_count != EXPECTED_PRIVATE_DECOMP_ROWS:
        fcc["fd1_private_manifest_mismatch"] = 1; mismatch.append("fd1_private_manifest_mismatch")
    audit_match = not mismatch
    audit_mismatch_reason = ";".join(mismatch)
    pt = p4._parse_private_decomposition_jsonl(fd1_private_decomposition_jsonl)
    if pt.path_supplied and not pt.file_existed:
        fcc["fd1_private_decomposition_missing"] = 1
    if pt.parse_failures:
        fcc["fd1_private_decomposition_parse_failed"] = int(pt.parse_failures)
    p4._compute_file_selector_lower_bound(pt)
    rav = p4._validate_fd1_replay_artifact(fd1_replay_artifact, str(fd1_manifest.get("manifest_hash", "") or ""))
    if rav.supplied and rav.failure_category and rav.failure_category in fcc:
        fcc[rav.failure_category] = max(fcc.get(rav.failure_category, 0), 1)
    denominator: list[RawHeldoutDenominatorRecord] = []
    denominator_meta: dict[str, Any] = {
        "denominator_source_protocol": "raw_external_full_frame_disjoint_success_quota_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "heldout_denominator_count": 0,
        "raw_denominator_scan_attempted": False,
        "raw_scan_fetched_records": 0,
        "raw_scan_attempted_records": 0,
        "raw_scan_prior_exact_excluded_records": 0,
        "raw_scan_prior_window_excluded_records": 0,
        "raw_scan_yield_file_miss_records": 0,
        "raw_scan_target_count": P4H_RAW_DENOMINATOR_TARGET_COUNT,
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": True,
        "prior_raw_exclusion_mode": "not_attempted",
        "disjoint_from_prior": True,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": _initial_raw_scan_rows(),
        "prior_raw_exclusion_records": [],
    }
    arm_results = {a: [] for a in POLICY_ARMS}
    retrieval_policy_executed = False
    manifests: list[dict[str, Any]] = []
    if enable_network and audit_match and pt.computed and rav.validated:
        try:
            denominator, scan_fcc, denominator_meta, scan_manifest = _scan_raw_heldout_denominator(openlocus_bin=openlocus_bin, pt=pt)
            manifests.append(scan_manifest)
            for k, v in scan_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if len(denominator) < P4H_MIN_DENOMINATOR_COUNT:
                fcc["heldout_denominator_insufficient"] = 1
            elif fcc.get("retrieval_policy_failed", 0) > 0:
                pass
            else:
                arm_results, sfcc, sched_manifest = _execute_retrieval_scheduler(openlocus_bin=openlocus_bin, denominator=denominator)
                manifests.append(sched_manifest)
                for k, v in sfcc.items():
                    if k in fcc:
                        fcc[k] += int(v)
                retrieval_policy_executed = fcc.get("retrieval_policy_failed", 0) == 0 and fcc.get("private_scheduler_rows_mismatch", 0) == 0
        except Exception:
            fcc["retrieval_policy_failed"] = 1
            fcc["unexpected_exception"] = 1
    elif enable_network:
        fcc["raw_denominator_scan_not_attempted"] = 1
    else:
        fcc["network_required_but_disabled"] = 1
    return _base_report(status="auto", failure_reason_category="", self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fd1_artifact=fd1_artifact, fd1_schema=fd1_schema, fd1_hash=fd1_hash, pt=pt, rav=rav, denominator=denominator, denominator_meta=denominator_meta, arm_results=arm_results, retrieval_policy_executed=retrieval_policy_executed, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason, fcc_in=fcc, extra_manifests=manifests, aggregate_runtime_seconds=time.perf_counter() - start)


def _build_synthetic_private_decomposition_jsonl(path: Path, *, gold_file_absent_count: int = 199, recoverable_lower_bound: int = 1) -> int:
    return p4._build_synthetic_private_decomposition_jsonl(path, gold_file_absent_count=gold_file_absent_count, recoverable_lower_bound=recoverable_lower_bound)


def _build_synthetic_raw_denominator(count: int = 80) -> tuple[list[RawHeldoutDenominatorRecord], dict[str, Any]]:
    denominator: list[RawHeldoutDenominatorRecord] = []
    for i in range(count):
        bm = "contextbench" if i < count // 2 else "repoqa"
        offset = P4H_RAW_CONTEXTBENCH_OFFSET if bm == "contextbench" else P4H_RAW_REPOQA_OFFSET
        limit = P4H_RAW_CONTEXTBENCH_LIMIT if bm == "contextbench" else P4H_RAW_REPOQA_LIMIT
        window = "contextbench_raw_full_frame_disjoint_scan" if bm == "contextbench" else "repoqa_raw_full_frame_disjoint_scan"
        denominator.append(RawHeldoutDenominatorRecord(
            private_record_id=f"{bm}-raw-{offset + i}",
            benchmark=bm,
            record_index=offset + i,
            window_name=window,
            raw_window_offset=offset,
            raw_window_limit=limit,
        ))
    scan_rows = _initial_raw_scan_rows()
    for row in scan_rows:
        selected = sum(1 for d in denominator if d.benchmark == row["benchmark"])
        row["raw_rows_fetched"] = int(row["raw_limit_requested"])
        row["raw_rows_attempted"] = selected
        row["raw_rows_file_miss_selected"] = selected
        row["target_reached_in_window"] = len(denominator) >= P4H_RAW_DENOMINATOR_TARGET_COUNT
    prior_rows = []
    for bm in ("contextbench", "repoqa"):
        for start, end, label in _raw_prior_exclusion_windows(bm):
            prior_rows.append({
                "source_phase": P4H_RAW_SOURCE_PHASE,
                "benchmark": bm,
                "exclusion_source_phase": "prior_fixed_window",
                "exclusion_basis": label,
                "excluded_window_start_inclusive": start,
                "excluded_window_end_exclusive": end,
                "exclusion_window_publicly_disclosed": True,
                "used_for_exclusion": False,
                "private_row_ids_publicly_serialized": False,
            })
    meta = {
        "denominator_source_protocol": "raw_external_full_frame_disjoint_success_quota_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "heldout_denominator_count": len(denominator),
        "raw_denominator_scan_attempted": True,
        "raw_scan_fetched_records": P4H_RAW_CONTEXTBENCH_LIMIT + P4H_RAW_REPOQA_LIMIT,
        "raw_scan_attempted_records": len(denominator),
        "raw_scan_prior_exact_excluded_records": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "raw_scan_prior_window_excluded_records": 0,
        "raw_scan_yield_file_miss_records": len(denominator),
        "raw_scan_target_count": P4H_RAW_DENOMINATOR_TARGET_COUNT,
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": True,
        "prior_raw_exclusion_mode": "fd1_private_exact_raw_keys",
        "disjoint_from_prior": True,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": scan_rows,
        "prior_raw_exclusion_records": prior_rows,
    }
    return denominator, meta


def _build_synthetic_scheduler_results(denominator: list[Any], baseline_available: int = 24, depth_available: int = 48, p3_available: int = 47, p4_available: int = 45, p4_latency: float = 2.0, p4_pool: int = 35) -> dict[str, list[p4.SchedulerReachResult]]:
    arm_results = {a: [] for a in POLICY_ARMS}
    for i, d in enumerate(denominator):
        rid = f"{d.source_phase}:{d.private_record_id}"
        tmp = p4._build_synthetic_scheduler_results(denominator_count=1, baseline_available=1 if i < baseline_available else 0, depth_available=1 if i < depth_available else 0, p3_available=1 if i < p3_available else 0, p4_available=1 if i < p4_available else 0, p4_latency=p4_latency, p4_pool=p4_pool)
        for arm in ("current_bea_candidate_pool_replay", "p2_depth_only_reference", "p3_constrained_depth_policy_reference"):
            rr = tmp[arm][0]
            rr.private_record_id = rid
            arm_results[arm].append(rr)
        rr4 = tmp[P4_COMPAT_TREATMENT_ARM][0]
        rr4.arm_name = P4H_TREATMENT_ARM
        rr4.private_record_id = rid
        arm_results[P4H_TREATMENT_ARM].append(rr4)
    return arm_results


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("identity_schema", SCHEMA_VERSION == "bea_v1_p4h_disjoint_scheduler_validation.v1"))
    checks.append(_check("phase_p4h", PHASE == "BEA-v1-P4H"))
    checks.append(_check("policy_arms_count_4", len(POLICY_ARMS) == 4))
    checks.append(_check("frozen_treatment_name", P4H_TREATMENT_ARM in POLICY_ARMS))
    checks.append(_check("p4_checkpoint", V1_P4_RESULT_CHECKPOINT == "f0e99ca"))
    checks.append(_check("min_denominator_80", P4H_MIN_DENOMINATOR_COUNT == 80))
    checks.append(_check("full_frame_contextbench_offset_0", P4H_RAW_CONTEXTBENCH_OFFSET == 0))
    checks.append(_check("full_frame_contextbench_limit_480", P4H_RAW_CONTEXTBENCH_LIMIT == 480))
    checks.append(_check("full_frame_repoqa_offset_0", P4H_RAW_REPOQA_OFFSET == 0))
    checks.append(_check("full_frame_repoqa_limit_240", P4H_RAW_REPOQA_LIMIT == 240))
    checks.append(_check("no_fixed_tail_window_names", all("after_" not in str(w.get("window_name", "")) for w in P4H_RAW_WINDOWS)))
    checks.append(_check("latency_not_in_relevance_false", DEFAULT_FALSE_FLAGS["latency_in_candidate_relevance"] is False))
    checks.append(_check("no_selector_change", DEFAULT_FALSE_FLAGS["selector_or_reranker_changed"] is False))
    with tempfile.TemporaryDirectory(prefix="v1p4h_st_") as sd:
        td = Path(sd)
        priv = td / "bea_fd1.decomposition.jsonl"
        _build_synthetic_private_decomposition_jsonl(priv, gold_file_absent_count=199)
        pt = p4._parse_private_decomposition_jsonl(priv)
        p4._compute_file_selector_lower_bound(pt)
        fd1_tail_denominator, fd1_tail_meta = _extract_disjoint_heldout_denominator(pt)
        checks.append(_check("synthetic_fd1_rows_86040", pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS))
        checks.append(_check("legacy_fd1_tail_can_be_80_when_absent_199", len(fd1_tail_denominator) == 80))
        checks.append(_check("legacy_prior_excluded_119", fd1_tail_meta.get("excluded_prior_window_count") == 119))
        priv119 = td / "bea_fd1_119.decomposition.jsonl"
        _build_synthetic_private_decomposition_jsonl(priv119, gold_file_absent_count=119)
        pt119 = p4._parse_private_decomposition_jsonl(priv119)
        fd1_tail_119, _ = _extract_disjoint_heldout_denominator(pt119)
        checks.append(_check("fd1_tail_119_not_sufficient_for_p4h", len(fd1_tail_119) == 0))
        denominator, meta = _build_synthetic_raw_denominator(80)
        checks.append(_check("raw_denominator_80", len(denominator) == 80))
        checks.append(_check("raw_source_protocol", meta.get("denominator_source_protocol") == "raw_external_full_frame_disjoint_success_quota_scan.v1"))
        checks.append(_check("raw_scan_attempted", meta.get("raw_denominator_scan_attempted") is True))
        checks.append(_check("prior_fd1_not_reused", meta.get("prior_fd1_denominator_reused") is False))
        checks.append(_check("raw_windows_excluded_prior", meta.get("prior_raw_windows_excluded") is True))
        checks.append(_check("prior_raw_exclusion_records_public_aggregate", len(meta.get("prior_raw_exclusion_records", [])) >= 2))
        checks.append(_check("scan_rows_disclose_full_frame_ranges", all("raw_offset_requested" in r and "raw_limit_requested" in r and "raw_rows_fetched" in r for r in meta.get("denominator_scan_records", []))))
        checks.append(_check("scan_rows_no_private_ids", all("private_record_id" not in r and "record_ids" not in r for r in meta.get("denominator_scan_records", []))))
        empty_fixed_tail_meta = {
            **meta,
            "heldout_denominator_count": 0,
            "raw_denominator_scan_attempted": True,
            "raw_scan_fetched_records": 0,
            "raw_scan_attempted_records": 0,
            "raw_scan_yield_file_miss_records": 0,
            "denominator_scan_records": [{
                "source_phase": P4H_RAW_SOURCE_PHASE,
                "benchmark": "contextbench",
                "denominator_window": "obsolete_fixed_tail_window_simulation",
                "raw_offset_requested": 480,
                "raw_limit_requested": 240,
                "scan_protocol": "obsolete_fixed_tail_simulation",
                "raw_rows_fetched": 0,
                "raw_rows_attempted": 0,
                "raw_rows_prior_exact_excluded": 0,
                "raw_rows_prior_window_excluded": 0,
                "raw_rows_parse_excluded": 0,
                "raw_rows_clone_excluded": 0,
                "raw_rows_baseline_reached_excluded": 0,
                "raw_rows_baseline_error_excluded": 0,
                "raw_rows_file_miss_selected": 0,
                "target_reached_in_window": False,
            }],
        }
        checks.append(_check("raw_scan_failures_are_blocking",
            "raw_denominator_scan_failed" in BLOCKING_FAILURE_CATEGORIES))
        checks.append(_check("raw_clone_failures_are_blocking",
            "raw_denominator_clone_failed" in BLOCKING_FAILURE_CATEGORIES))
        checks.append(_check("private_scheduler_mismatch_blocking",
            "private_scheduler_rows_mismatch" in BLOCKING_FAILURE_CATEGORIES))
        replay_path = td / "fd1_replay_report.json"
        p4._build_synthetic_fd1_replay_artifact(replay_path)
        rav = p4._validate_fd1_replay_artifact(replay_path, "a" * 64)
        fd1_art = p4._build_synthetic_fd1_artifact()
        arm_results = _build_synthetic_scheduler_results(denominator)
        report = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, denominator=denominator, denominator_meta=meta, arm_results=arm_results, retrieval_policy_executed=True, audit_match=True, aggregate_runtime_seconds=0.5)
        required = ("source_run_records", "denominator_records", "denominator_scan_records", "prior_raw_exclusion_records", "arm_reach_records", "arm_delta_records", "arm_cost_records", "arm_action_records", "channel_action_records", "scheduler_stop_reason_records", "latency_decomposition_records", "efficiency_records", "reach_bucket_records", "rank_band_records", "cost_safety_records", "subgroup_safety_records", "rank_budget_audit_records", "stop_go_records", "gate_records", "private_manifest_records", "failure_category_count_records")
        for table in required:
            checks.append(_check(f"table_{table}_is_list", isinstance(report.get(table), list)))
        checks.append(_check("synthetic_status_pass", report.get("status") == "bea_v1_p4h_disjoint_scheduler_validation_pass"))
        checks.append(_check("forbidden_scan_pass", report.get("forbidden_scan", {}).get("status") == "pass"))
        checks.append(_check("private_rows_320", report.get("stop_go_records", [{}])[0].get("private_scheduler_rows") == 80 * 4))
        checks.append(_check("rank_budget_confirmed", report.get("rank_budget_audit_records", [{}])[0].get("rank_budget_bottleneck_confirmed") is True))
        checks.append(_check("subgroup_records_present", len(report.get("subgroup_safety_records", [])) > 0))
        checks.append(_check("report_raw_scan_records_present", len(report.get("denominator_scan_records", [])) == 2))
        checks.append(_check("report_prior_exclusion_records_present", len(report.get("prior_raw_exclusion_records", [])) >= 2))
        checks.append(_check("report_prior_fd1_not_reused", report.get("prior_fd1_denominator_reused") is False))
        bad_report = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, denominator=denominator[:79], denominator_meta={**meta, "heldout_denominator_count": 79}, arm_results={a: [] for a in POLICY_ARMS}, retrieval_policy_executed=False, audit_match=True, aggregate_runtime_seconds=0.5)
        checks.append(_check("insufficient_denominator_status", bad_report.get("status") == "no_go_p4h_insufficient_denominator"))
        empty_fixed_tail_report = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, denominator=[], denominator_meta=empty_fixed_tail_meta, arm_results={a: [] for a in POLICY_ARMS}, retrieval_policy_executed=False, audit_match=True, aggregate_runtime_seconds=0.5)
        checks.append(_check("empty_fixed_tail_simulation_no_schema_contract", empty_fixed_tail_report.get("status") == "no_go_p4h_insufficient_denominator"))
        scan_fail_report = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, denominator=denominator[:79], denominator_meta={**meta, "heldout_denominator_count": 79}, arm_results={a: [] for a in POLICY_ARMS}, retrieval_policy_executed=False, audit_match=True, fcc_in={"raw_denominator_scan_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("scan_failure_not_insufficient_no_go",
            scan_fail_report.get("status") == "fail_schema_contract"))
        clone_fail_report = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, denominator=denominator[:79], denominator_meta={**meta, "heldout_denominator_count": 79}, arm_results={a: [] for a in POLICY_ARMS}, retrieval_policy_executed=False, audit_match=True, fcc_in={"raw_denominator_clone_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("clone_failure_not_insufficient_no_go",
            clone_fail_report.get("status") == "fail_schema_contract"))
        leaked = dict(report)
        leaked["private_record_id"] = "leak"
        checks.append(_check("scanner_rejects_private_record_id", _v1_p4h_forbidden_scan_summary(leaked)["status"] == "fail"))
    parser = build_parser()
    opts = {opt for action in parser._actions for opt in action.option_strings}
    for opt in ("--self-test", "--out", "--fd1-artifact", "--fd1-private-decomposition-jsonl", "--fd1-replay-artifact", "--openlocus", "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in opts))
    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-P4H Disjoint Scheduler Validation")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd1-private-decomposition-jsonl", type=Path, default=None)
    ap.add_argument("--fd1-replay-artifact", type=Path, default=None)
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['check']}")
        print(f"self_test_passed={passed} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)
    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        sys.exit(1)
    out_path = args.out if args.out is not None else DEFAULT_OUT
    openlocus_bin, openlocus_source = p4.c5a._resolve_openlocus_binary(args.openlocus)
    enable_network = bool(args.enable_external_benchmark_network)
    network_mode = "local_explicit" if enable_network else "disabled_opt_in"
    if enable_network and openlocus_bin is None:
        report = _base_report(status="unavailable_with_reason", failure_reason_category="openlocus_binary_missing", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source, network_mode=network_mode, fcc_in={"openlocus_binary_missing": 1})
    elif not enable_network:
        report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "missing", network_mode=network_mode, fcc_in={"network_required_but_disabled": 1})
    else:
        try:
            report = _run_scheduler_validation(openlocus_bin=openlocus_bin or "", openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, self_test_passed=True, self_test_checks_total=len(checks), fd1_artifact_path=args.fd1_artifact, fd1_private_decomposition_jsonl=args.fd1_private_decomposition_jsonl, fd1_replay_artifact=args.fd1_replay_artifact, enable_network=enable_network)
        except Exception:
            report = _base_report(status="unavailable_with_reason", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, fcc_in={"unexpected_exception": 1})
    if report.get("provider_calls_made") is not False or report.get("latency_in_candidate_relevance") is not False or report.get("gold_labels_used_for_policy") is not False or report.get("query_anchors_used_in_p4_arm") is not False:
        report["status"] = "fail_schema_contract"
    _enforce_v1_p4h_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    sgr = report.get("stop_go_records", [{}])[0] if report.get("stop_go_records") else {}
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={report['phase']}, denominator_count={report.get('denominator_count', 0)}, stop_go_decision={sgr.get('stop_go_decision', '')})")
    if not enable_network:
        print("enable_external_benchmark_network is false; skipping real BEA-v1-P4H disjoint scheduler validation.")


if __name__ == "__main__":
    main()
