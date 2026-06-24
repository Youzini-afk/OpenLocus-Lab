#!/usr/bin/env python3
"""BEA-v1-P4I: Disjoint Denominator Reservoir Audit.

P4I is a bounded **denominator/source audit** performed after the BEA-v1-P4H
No-Go.  It does **not** run P2/P3/P4 scheduler arms, does **not** validate a
scheduler, does **not** expand retrieval, does **not** execute a
selector/reranker, and does **not** authorize P5 / BEA-v1-A.

Objective: empirically determine whether the P4H blocker
(``no_go_p4h_insufficient_denominator`` with 73/80 disjoint file-miss records)
is just the current ContextBench/RepoQA Python-frame denominator being
exhausted, or whether disjoint file-miss denominator scarcity is structural.

P4I scans only already-supported external benchmark raw frames/adapters that
can be evaluated with the existing ``current_bea_candidate_pool_replay``
diagnostic arm.  A candidate denominator record is a baseline/current
candidate pool *miss* of the gold file.  The scan does **not** stop at an
80-record target; it counts the full cumulative disjoint file-miss reservoir.
When the P4H per-row exact keys are not available (the committed P4H artifact
is aggregate-only), the reported count is an upper bound after FD1 exact
BEA-4/5 exclusion, not a qualified all-prior-disjoint denominator.

The public artifact is aggregate-only and records-only.  Per-record scan
traces are written only under ``/tmp`` (or an ignored runs/private path) and
are never uploaded.  No private raw keys/ids/paths are serialized; the only
provenance hash permitted is the private scan manifest hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_p4_latency_aware_retrieval_scheduler_smoke as p4  # noqa: E402
import bea_v1_p4h_disjoint_scheduler_validation as p4h  # noqa: E402

SCHEMA_VERSION = "bea_v1_p4i_disjoint_denominator_reservoir_audit.v1"
GENERATED_BY = "eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py"
CLAIM_LEVEL = "bea_v1_p4i_disjoint_denominator_reservoir_audit_only"
MODE = "bea_v1_p4i_disjoint_denominator_reservoir_audit"
PHASE = "BEA-v1-P4I"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p4i_disjoint_denominator_reservoir_audit/"
    "bea_v1_p4i_disjoint_denominator_reservoir_audit_report.json"
)
DEFAULT_FD1_ARTIFACT = p4.DEFAULT_FD1_ARTIFACT
DEFAULT_P4H_ARTIFACT = p4h.DEFAULT_OUT

# --- P4H binding context (read-only motivation) ---
P4H_RESULT_CHECKPOINT = "9305701"
P4H_RESULT_STATUS = "no_go_p4h_insufficient_denominator"
P4H_CI_RUN_ID = "28132121958"
P4H_FULL_FRAME_SCAN_FIX = "0dfeb27"
P4H_LOCAL_CHECKPOINT = "dee1ce1"
P4H_DENOMINATOR_COUNT = 73
P4H_DENOMINATOR_MIN = 80
P4H_RAW_SCAN_ATTEMPTED_RECORDS = 127
P4H_RAW_SCAN_YIELD_FILE_MISS_RECORDS = 73
P4H_RAW_SCAN_PRIOR_EXACT_EXCLUDED_RECORDS = 239

# --- P4 binding context (read-only) ---
V1_P4_RESULT_CHECKPOINT = "f0e99ca"
V1_P4_RESULT_STATUS = "bea_v1_p4_latency_aware_retrieval_scheduler_pass"

FIXED_BUDGET = p4.FIXED_BUDGET
FIXED_METHODS = p4.FIXED_METHODS
EXPECTED_RECORDS_DECOMPOSED = p4.EXPECTED_RECORDS_DECOMPOSED
EXPECTED_PRIVATE_DECOMP_ROWS = p4.EXPECTED_PRIVATE_DECOMP_ROWS
ORIGINAL_P1234_DENOMINATOR_COUNT = 119

# The ONLY diagnostic arm.  P2/P3/P4 scheduler arms are NOT run.
DIAGNOSTIC_ARM = "current_bea_candidate_pool_replay"
POLICY_ARMS = (DIAGNOSTIC_ARM,)

P4I_RESERVOIR_MIN_COUNT = 80
P4I_RAW_SOURCE_PHASE = "P4I-RAW"
P4I_RAW_CONTEXTBENCH_OFFSET = 0
P4I_RAW_CONTEXTBENCH_LIMIT = 480
P4I_RAW_REPOQA_OFFSET = 0
P4I_RAW_REPOQA_LIMIT = 240
P4I_RAW_WINDOWS = (
    {
        "benchmark": "contextbench",
        "window_name": "contextbench_raw_full_frame_reservoir_scan",
        "raw_offset_requested": P4I_RAW_CONTEXTBENCH_OFFSET,
        "raw_limit_requested": P4I_RAW_CONTEXTBENCH_LIMIT,
    },
    {
        "benchmark": "repoqa",
        "window_name": "repoqa_raw_full_frame_reservoir_scan",
        "raw_offset_requested": P4I_RAW_REPOQA_OFFSET,
        "raw_limit_requested": P4I_RAW_REPOQA_LIMIT,
    },
)
EXACT_EXCLUSION_SCOPE = "fd1_private_exact_bea4_bea5_raw_keys_only"

STATUSES = (
    "reservoir_ready_for_frozen_p4h_rerun",
    "no_go_disjoint_denominator_reservoir_insufficient",
    "no_go_disjoint_denominator_reservoir_unqualified",
    "fail_schema_contract",
    "fail_forbidden_scan",
    "unavailable_with_reason",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "reservoir_ready_for_frozen_p4h_rerun",
    "no_go_disjoint_denominator_reservoir_insufficient",
    "no_go_disjoint_denominator_reservoir_unqualified",
})

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "records_only_public_artifact": True,
    "diagnostic_only": True,
    "denominator_source_audit_only": True,
    "fd1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "p4h_artifact_read": False,
    "retrieval_policy_executed": False,
    "bea_v1_p4i_audit_evaluator_no_provider_calls": True,
    "bea_v1_p4i_audit_evaluator_no_selector_executed": True,
    "bea_v1_p4i_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p4i_audit_evaluator_no_role_proxy": True,
    "bea_v1_p4i_audit_evaluator_latency_not_in_relevance": True,
    "bea_v1_p4i_audit_evaluator_no_p2_p3_p4_scheduler_arms": True,
    "bea_v1_p4i_audit_evaluator_no_retrieval_expansion": True,
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
    "algorithm_changed_during_bea_v1_p4i": False,
    "weights_tuned_during_bea_v1_p4i": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p4i": False,
    "v1_a_selector_executed": False,
    "v1_a_coverage_preserving_selector_promoted": False,
    "selector_or_reranker_changed": False,
    "selector_or_reranker_executed": False,
    "fd2b_executed": False,
    "fd2c_executed": False,
    "legacy_role_proxy_p4_executed": False,
    "p5_executed": False,
    "p5_authorized": False,
    "v1_a_authorized": False,
    "runtime_promotion_authorized": False,
    "method_winner_authorized": False,
    "broad_retrieval_expansion_authorized": False,
    "frozen_p4h_rerun_authorized": False,
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
    "p2_depth_only_reference_executed": False,
    "p3_constrained_depth_policy_reference_executed": False,
    "p4_latency_aware_action_scheduler_executed": False,
    "new_records_added_during_bea_v1_p4i": False,
}
LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_p4i_disjoint_denominator_reservoir_audit",
}

FAILURE_CATEGORIES_AUDIT = tuple(dict.fromkeys((*p4h.FAILURE_CATEGORIES_AUDIT,
    "reservoir_insufficient",
    "exact_prior_exclusion_unavailable",
    "p4h_overlap_not_resolved",
    "denominator_reservoir_scan_not_attempted",
)))
BLOCKING_FAILURE_CATEGORIES = tuple(dict.fromkeys((
    *p4.BLOCKING_FAILURE_CATEGORIES,
    "raw_denominator_scan_failed",
    "raw_denominator_scan_not_attempted",
    "denominator_reservoir_scan_not_attempted",
    "raw_denominator_clone_failed",
    "exact_prior_exclusion_unavailable",
)))


class ReservoirRecord:
    """One private disjoint file-miss reservoir record.

    The public artifact only exposes aggregate counts.  Private row identity,
    query text, gold paths, repository location, and baseline candidate paths
    remain in memory or ``/tmp`` JSONL only.
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
        self.source_phase = P4I_RAW_SOURCE_PHASE
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


def _resolve_private_reservoir_dir() -> Path:
    raw = os.environ.get("OPENLOCUS_BEA_V1_P4I_PRIVATE_RESERVOIR_DIR", "")
    base = Path(raw) if raw else Path(f"/tmp/openlocus_bea_v1_p4i_reservoir_{os.getpid()}")
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private reservoir dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _initial_reservoir_scan_rows() -> list[dict[str, Any]]:
    return [{
        "source_phase": P4I_RAW_SOURCE_PHASE,
        "benchmark": str(w["benchmark"]),
        "denominator_window": str(w["window_name"]),
        "raw_offset_requested": int(w["raw_offset_requested"]),
        "raw_limit_requested": int(w["raw_limit_requested"]),
        "scan_protocol": "full_frame_disjoint_file_miss_reservoir_quota",
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
    } for w in P4I_RAW_WINDOWS]


def _prior_exclusion_disclosure_records(
    *, prior_raw_keys: set[tuple[str, int]],
    exact_exclusion_records: list[dict[str, Any]],
    use_exact_prior_keys: bool,
) -> list[dict[str, Any]]:
    """Build public aggregate prior-exclusion disclosure records.

    Exact BEA-4/5 raw keys (from FD1 private decomposition) are used for actual
    exclusion when available.  For P1/P2/P3/P4 the FD1 BEA-4/5 exact superset
    already covers their shared 119-record denominator, so only an aggregate
    disclosure is emitted.  For P4H the exact 73 selected keys are private
    (``/tmp`` only, never committed, not in FD1), so only an aggregate
    disclosure is emitted and exact keys are NOT faked.
    """
    records: list[dict[str, Any]] = list(exact_exclusion_records)
    # P1/P2/P3/P4 aggregate disclosure (covered by BEA-4/5 exact superset).
    records.append({
        "source_phase": P4I_RAW_SOURCE_PHASE,
        "exclusion_source_phase": "BEA-v1-P1/P2/P3/P4",
        "exclusion_basis": "covered_by_fd1_bea4_bea5_exact_superset",
        "excluded_record_count_aggregate": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "exact_keys_available_from_fd1": False,
        "used_for_exclusion": bool(use_exact_prior_keys),
        "private_row_ids_publicly_serialized": False,
    })
    # P4H aggregate disclosure (exact keys private/tmp only, never committed).
    records.append({
        "source_phase": P4I_RAW_SOURCE_PHASE,
        "exclusion_source_phase": "BEA-v1-P4H",
        "exclusion_basis": "p4h_exact_keys_private_tmp_only_aggregate_disclosure",
        "excluded_record_count_aggregate": P4H_DENOMINATOR_COUNT,
        "p4h_committed_denominator_count": P4H_DENOMINATOR_COUNT,
        "p4h_committed_denominator_min": P4H_DENOMINATOR_MIN,
        "exact_keys_available_from_fd1": False,
        "used_for_exclusion": False,
        "private_row_ids_publicly_serialized": False,
    })
    # BEA-2/3/4 explicit public index windows (disclosed; exact BEA-4 keys
    # supersede the BEA-4 window when exact keys are available).
    for bm in ("contextbench", "repoqa"):
        for start, end, label in p4h._raw_prior_exclusion_windows(bm):
            records.append({
                "source_phase": P4I_RAW_SOURCE_PHASE,
                "benchmark": bm,
                "exclusion_source_phase": "prior_fixed_window",
                "exclusion_basis": label,
                "excluded_window_start_inclusive": start,
                "excluded_window_end_exclusive": end,
                "exclusion_window_publicly_disclosed": True,
                "used_for_exclusion": not use_exact_prior_keys,
                "private_row_ids_publicly_serialized": False,
            })
    return records


def _scan_reservoir(
    *, openlocus_bin: str, pt: p4.bea_v1_p1.ParsedPrivateDecomposition | None,
) -> tuple[list[ReservoirRecord], dict[str, int], dict[str, Any], dict[str, Any]]:
    """Scan full available raw frames with the baseline diagnostic arm only.

    P2/P3/P4 treatment arms are NOT run.  The scan does not stop at an 80-record
    target; it counts the full cumulative disjoint file-miss reservoir.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    reservoir: list[ReservoirRecord] = []
    scan_rows = _initial_reservoir_scan_rows()
    row_by_window = {r["denominator_window"]: r for r in scan_rows}
    private_dir = _resolve_private_reservoir_dir()
    private_path = private_dir / "bea_v1_p4i.private_reservoir_scan.jsonl"
    if private_path.exists():
        private_path.unlink()
    attempted_total = 0
    fetched_total = 0
    excluded_prior_exact_total = 0
    excluded_prior_window_total = 0
    baseline_reached_total = 0
    baseline_error_total = 0
    prior_raw_keys, exact_exclusion_records = p4h._prior_raw_keys_from_fd1_private(pt)
    use_exact_prior_keys = bool(prior_raw_keys)
    for w in P4I_RAW_WINDOWS:
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
            raw_idx = offset + local_idx
            if use_exact_prior_keys and (bm, raw_idx) in prior_raw_keys:
                srow["raw_rows_prior_exact_excluded"] += 1
                excluded_prior_exact_total += 1
                continue
            if not use_exact_prior_keys and p4h._raw_index_exclusion_reason(bm, raw_idx):
                srow["raw_rows_prior_window_excluded"] += 1
                excluded_prior_window_total += 1
                continue
            attempted_total += 1
            srow["raw_rows_attempted"] += 1
            query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval(bm, row)
            private_record_id = f"{bm}-raw-{raw_idx}"
            if not ok:
                srow["raw_rows_parse_excluded"] += 1
                fcc["raw_denominator_parse_failed"] += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"v1p4i_scan_{bm}_{raw_idx}_") as tmp:
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
                rr_base.private_record_id = f"{P4I_RAW_SOURCE_PHASE}:{private_record_id}"
                if rr_base.retrieval_error:
                    srow["raw_rows_baseline_error_excluded"] += 1
                    baseline_error_total += 1
                    fcc["retrieval_policy_failed"] += 1
                    continue
                p4._append_private_jsonl(private_path, {
                    "schema_version": "bea_v1_p4i_private_reservoir_scan.v1",
                    "source_phase": P4I_RAW_SOURCE_PHASE,
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
                    "selected_for_reservoir": not rr_base.gold_file_available,
                    "config_hash": p4._config_hash(),
                })
                if rr_base.gold_file_available:
                    srow["raw_rows_baseline_reached_excluded"] += 1
                    baseline_reached_total += 1
                    continue
                srow["raw_rows_file_miss_selected"] += 1
                reservoir.append(ReservoirRecord(
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
        srow["target_reached_in_window"] = len(reservoir) >= P4I_RESERVOIR_MIN_COUNT
    disclosure_records = _prior_exclusion_disclosure_records(
        prior_raw_keys=prior_raw_keys,
        exact_exclusion_records=exact_exclusion_records,
        use_exact_prior_keys=use_exact_prior_keys,
    )
    meta = {
        "denominator_source_protocol": "raw_external_full_frame_disjoint_file_miss_reservoir_quota_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "reservoir_count": len(reservoir),
        "reservoir_upper_bound_count": len(reservoir),
        "qualified_denominator_reservoir_count": 0,
        "raw_denominator_scan_attempted": True,
        "raw_scan_fetched_records": int(fetched_total),
        "raw_scan_attempted_records": int(attempted_total),
        "raw_scan_prior_exact_excluded_records": int(excluded_prior_exact_total),
        "raw_scan_prior_window_excluded_records": int(excluded_prior_window_total),
        "raw_scan_yield_file_miss_records": int(len(reservoir)),
        "raw_scan_baseline_reached_records": int(baseline_reached_total),
        "raw_scan_baseline_error_records": int(baseline_error_total),
        "reservoir_min_count": P4I_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": bool(use_exact_prior_keys),
        "disjoint_from_exact_fd1_bea4_bea5_prior": bool(use_exact_prior_keys),
        "p4h_exact_keys_available_for_exclusion": False,
        "p4h_overlap_resolved": False,
        "reservoir_upper_bound_includes_possible_p4h_overlap": True,
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": True,
        "prior_raw_exclusion_mode": "fd1_private_exact_raw_keys" if use_exact_prior_keys else "explicit_public_index_windows",
        "disjoint_from_prior": False,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": scan_rows,
        "prior_raw_exclusion_records": disclosure_records,
    }
    manifest = p4._private_file_manifest(private_path, manifest_name="bea_v1_p4i_private_reservoir_scan_manifest", schema_version="bea_v1_p4i_private_reservoir_scan.v1")
    return reservoir, fcc, meta, manifest


def _denominator_reservoir_records(reservoir: list[Any]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str, str], int] = {}
    for d in reservoir:
        key = (str(getattr(d, "source_phase", P4I_RAW_SOURCE_PHASE)),
               str(getattr(d, "benchmark", "")),
               str(getattr(d, "window_name", "raw_external_reservoir_scan")))
        counts[key] = counts.get(key, 0) + 1
    return [{
        "source_phase": sp,
        "benchmark": bm,
        "denominator_window": window,
        "reservoir_record_count": int(cnt),
    } for (sp, bm, window), cnt in sorted(counts.items())]


def _denominator_scan_records(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("denominator_scan_records", [])
    return list(rows) if isinstance(rows, list) else []


def _prior_raw_exclusion_records(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("prior_raw_exclusion_records", [])
    return list(rows) if isinstance(rows, list) else []


def _subgroup_reservoir_records(reservoir: list[Any]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for d in reservoir:
        key = (str(getattr(d, "source_phase", P4I_RAW_SOURCE_PHASE)),
               str(getattr(d, "benchmark", "")))
        counts[key] = counts.get(key, 0) + 1
    return [{
        "source_phase": sp,
        "benchmark": bm,
        "subgroup_reservoir_count": int(cnt),
    } for (sp, bm), cnt in sorted(counts.items())]


def _source_run_records(
    *, fd1_schema_version: str, fd1_source_artifact_hash: str,
    fd1_status: str, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    pt: p4.bea_v1_p1.ParsedPrivateDecomposition | None,
    rav: p4.bea_v1_p1.Fd1ReplayArtifactValidation | None,
    p4h_artifact: dict[str, Any] | None, p4h_status: str, p4h_denominator_count: int,
    audit_match: bool, audit_mismatch_reason: str,
) -> list[dict[str, Any]]:
    p4h_art = p4h_artifact or {}
    return [{
        "source_phase": "BEA-v1-P4H",
        "source_checkpoint": P4H_RESULT_CHECKPOINT,
        "source_status": p4h_status,
        "source_ci_run_id": P4H_CI_RUN_ID,
        "source_full_frame_scan_fix": P4H_FULL_FRAME_SCAN_FIX,
        "source_local_checkpoint": P4H_LOCAL_CHECKPOINT,
        "source_denominator_count": int(p4h_denominator_count),
        "source_denominator_min": P4H_DENOMINATOR_MIN,
        "audit_objective": "determine_whether_disjoint_file_miss_denominator_scarcity_is_structural",
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": "raw_external_full_frame_disjoint_file_miss_reservoir_quota_scan.v1",
        "prior_fd1_denominator_reused": False,
        "raw_contextbench_offset_requested": P4I_RAW_CONTEXTBENCH_OFFSET,
        "raw_contextbench_limit_requested": P4I_RAW_CONTEXTBENCH_LIMIT,
        "raw_repoqa_offset_requested": P4I_RAW_REPOQA_OFFSET,
        "raw_repoqa_limit_requested": P4I_RAW_REPOQA_LIMIT,
        "reservoir_min_count": P4I_RESERVOIR_MIN_COUNT,
        "expected_records_decomposed": EXPECTED_RECORDS_DECOMPOSED,
        "audited_records_decomposed": int(fd1_records_decomposed),
        "expected_private_manifest_record_count": EXPECTED_PRIVATE_DECOMP_ROWS,
        "audited_private_manifest_record_count": int(fd1_private_manifest_record_count),
        "fd1_source_schema_version": fd1_schema_version,
        "fd1_source_artifact_hash": fd1_source_artifact_hash,
        "fd1_private_decomposition_supplied": bool(pt.path_supplied if pt else False),
        "fd1_private_decomposition_parsed": bool(pt.computed if pt else False),
        "fd1_private_decomposition_row_count": int(pt.row_count if pt else 0),
        "fd1_private_decomposition_group_count": int(pt.group_count if pt else 0),
        "replay_artifact_supplied": bool(rav.supplied if rav else False),
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
        "p4h_artifact_read": bool(p4h_art),
        "p4h_committed_status": str(p4h_art.get("status", "") or ""),
        "p4h_committed_denominator_count": int(p4h_art.get("denominator_count", 0) or 0),
        "p4h_committed_denominator_min": int(p4h_art.get("stop_go_records", [{}])[0].get("denominator_min", P4H_DENOMINATOR_MIN) if p4h_art.get("stop_go_records") else P4H_DENOMINATOR_MIN),
        "p4h_committed_raw_scan_attempted_records": int(p4h_art.get("raw_scan_attempted_records", P4H_RAW_SCAN_ATTEMPTED_RECORDS) or 0),
        "p4h_committed_raw_scan_yield_file_miss_records": int(p4h_art.get("raw_scan_yield_file_miss_records", P4H_RAW_SCAN_YIELD_FILE_MISS_RECORDS) or 0),
        "v1_p4_result_checkpoint": V1_P4_RESULT_CHECKPOINT,
        "v1_p4_result_status": V1_P4_RESULT_STATUS,
        "config_hash": p4._config_hash(),
    }]


def _stop_go_records(
    *, reservoir_count: int, raw_scan_attempted: bool, disjoint: bool,
    blocking_failure_count: int, exact_prior_exclusion_used: bool,
    p4h_overlap_resolved: bool,
) -> list[dict[str, Any]]:
    if not exact_prior_exclusion_used:
        decision = "fail_schema_contract"
        reason = "fd1_exact_bea4_bea5_prior_exclusion_required"
    elif blocking_failure_count > 0:
        decision = "fail_schema_contract"
        reason = "blocking_failure_present_cannot_be_reservoir_insufficient"
    elif not raw_scan_attempted:
        decision = "fail_schema_contract"
        reason = "denominator_reservoir_scan_not_attempted"
    elif reservoir_count < P4I_RESERVOIR_MIN_COUNT:
        decision = "no_go_disjoint_denominator_reservoir_insufficient"
        reason = f"cumulative_denominator_reservoir_upper_bound_count={reservoir_count}; min={P4I_RESERVOIR_MIN_COUNT}"
    elif not p4h_overlap_resolved:
        decision = "no_go_disjoint_denominator_reservoir_unqualified"
        reason = "reservoir_reaches_min_but_p4h_exact_keys_are_unavailable_for_overlap_exclusion"
    else:
        decision = "reservoir_ready_for_frozen_p4h_rerun"
        reason = "qualified_disjoint_file_miss_reservoir_reaches_min"
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "denominator_record_count": int(reservoir_count),
        "denominator_min": int(P4I_RESERVOIR_MIN_COUNT),
        "cumulative_denominator_reservoir_count": int(reservoir_count),
        "reservoir_upper_bound_count": int(reservoir_count),
        "qualified_denominator_reservoir_count": int(reservoir_count if p4h_overlap_resolved else 0),
        "denominator_disjoint_from_prior": bool(disjoint),
        "p4h_overlap_resolved": bool(p4h_overlap_resolved),
        "raw_denominator_scan_attempted": bool(raw_scan_attempted),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "reservoir_ready_authorized": bool(decision == "reservoir_ready_for_frozen_p4h_rerun"),
        "frozen_p4h_rerun_authorized": bool(decision == "reservoir_ready_for_frozen_p4h_rerun"),
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "method_winner_authorized": False,
        "broad_retrieval_expansion_authorized": False,
        "scheduler_validation_authorized": bool(decision == "reservoir_ready_for_frozen_p4h_rerun"),
    }]


def _gate_records(
    *, fd1_records_decomposed: int, fd1_private_manifest_record_count: int,
    denominator_meta: dict[str, Any], reservoir_count: int,
    fd1_private_decomposition_parsed: bool, replay_artifact_validated: bool,
    forbidden_scan_pass: bool, blocking_failure_count: int,
    exact_prior_exclusion_used: bool,
) -> list[dict[str, Any]]:
    def g(name: str, value: float, relation: str, threshold: float, passed: bool) -> dict[str, Any]:
        return {"gate": name, "value": round(float(value), 6), "threshold_relation": relation, "threshold_value": round(float(threshold), 6), "passed": bool(passed)}
    return [
        g("fd1_records_decomposed", fd1_records_decomposed, "==", EXPECTED_RECORDS_DECOMPOSED, fd1_records_decomposed == EXPECTED_RECORDS_DECOMPOSED),
        g("fd1_private_manifest_record_count", fd1_private_manifest_record_count, "==", EXPECTED_PRIVATE_DECOMP_ROWS, fd1_private_manifest_record_count == EXPECTED_PRIVATE_DECOMP_ROWS),
        g("fd1_private_decomposition_parsed", 1.0 if fd1_private_decomposition_parsed else 0.0, "boolean", 1.0, fd1_private_decomposition_parsed),
        g("replay_artifact_validated", 1.0 if replay_artifact_validated else 0.0, "boolean", 1.0, replay_artifact_validated),
        g("raw_denominator_scan_attempted", 1.0 if denominator_meta.get("raw_denominator_scan_attempted", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("raw_denominator_scan_attempted", False))),
        g("raw_denominator_attempted_records", denominator_meta.get("raw_scan_attempted_records", 0), ">=", 0.0, denominator_meta.get("raw_scan_attempted_records", 0) >= 0),
        g("exact_prior_exclusion_used", 1.0 if exact_prior_exclusion_used else 0.0, "boolean", 1.0, bool(exact_prior_exclusion_used)),
        g("prior_raw_windows_excluded", 1.0 if denominator_meta.get("prior_raw_windows_excluded", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("prior_raw_windows_excluded", False))),
        g("disjoint_from_exact_fd1_bea4_bea5_prior", 1.0 if denominator_meta.get("disjoint_from_exact_fd1_bea4_bea5_prior", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("disjoint_from_exact_fd1_bea4_bea5_prior", False))),
        g("p4h_overlap_resolved", 1.0 if denominator_meta.get("p4h_overlap_resolved", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("p4h_overlap_resolved", False))),
        g("denominator_disjoint_from_prior", 1.0 if denominator_meta.get("disjoint_from_prior", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("disjoint_from_prior", False))),
        g("reservoir_count_min", reservoir_count, ">=", P4I_RESERVOIR_MIN_COUNT, reservoir_count >= P4I_RESERVOIR_MIN_COUNT),
        g("denominator_constructed_before_scheduler_outcomes", 1.0 if denominator_meta.get("denominator_constructed_before_scheduler_outcomes", True) else 0.0, "boolean", 1.0, bool(denominator_meta.get("denominator_constructed_before_scheduler_outcomes", True))),
        g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0, "boolean", 1.0, forbidden_scan_pass),
        g("provider_calls_made", 0.0, "boolean_false", 0.0, True),
        g("latency_in_candidate_relevance", 0.0, "boolean_false", 0.0, True),
        g("p2_p3_p4_scheduler_arms_executed", 0.0, "boolean_false", 0.0, True),
        g("selector_or_reranker_executed", 0.0, "boolean_false", 0.0, True),
        g("retrieval_policy_executed", 0.0, "boolean_false", 0.0, True),
        g("blocking_failure_count", blocking_failure_count, "==", 0.0, blocking_failure_count == 0),
    ]


def _failure_category_count_records(fcc: dict[str, int]) -> list[dict[str, Any]]:
    return [{"failure_category": str(k), "count": int(v)} for k, v in sorted(fcc.items())]


def _blocking_failure_count(fcc: dict[str, int]) -> int:
    return sum(int(fcc.get(cat, 0)) for cat in BLOCKING_FAILURE_CATEGORIES)


def _private_manifest_records(fd1_artifact: dict[str, Any], extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return p4._private_manifest_records(fd1_artifact, "fd1_committed_artifact", extra_manifests=extra or [])


FORBIDDEN_PUBLIC_KEYS = frozenset(p4h.FORBIDDEN_PUBLIC_KEYS | {
    "reservoir_records_private", "reservoir_rows_private",
    "reservoir_private_paths", "reservoir_query_private",
    "p4h_private_denominator_scan_path", "p4h_exact_raw_keys",
    "prior_exact_raw_keys", "exact_raw_keys",
})


def _scan_v1_p4i(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sub = f"{path}.{ks}"
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_v1_p4i_public_key", "path": sub})
                if isinstance(v, str) and len(v) > 240 and ks not in {"stop_go_reason", "audit_objective"}:
                    violations.append({"category": "long_string", "path": sub})
                walk(v, sub)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(obj)
    return violations


def _v1_p4i_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p4i(obj)
    cats: dict[str, int] = {}
    for v in violations:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    violation_categories = [{"category": c, "count": int(n)} for c, n in sorted(cats.items())]
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": violation_categories,
    }


def _enforce_v1_p4i_no_forbidden(obj: Any) -> None:
    if _v1_p4i_forbidden_scan_summary(obj)["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


def _base_report(
    *, status: str, failure_reason_category: str, self_test_passed: bool,
    self_test_checks_total: int, self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any] | None = None,
    fd1_schema: str = "", fd1_hash: str = "", pt: Any = None,
    rav: Any = None, p4h_artifact: dict[str, Any] | None = None,
    p4h_status: str = "", p4h_denominator_count: int = P4H_DENOMINATOR_COUNT,
    reservoir: list[Any] | None = None,
    reservoir_meta: dict[str, Any] | None = None,
    retrieval_policy_executed: bool = False, audit_match: bool = False,
    audit_mismatch_reason: str = "", fcc_in: dict[str, int] | None = None,
    extra_manifests: list[dict[str, Any]] | None = None,
    aggregate_runtime_seconds: float = 0.0,
) -> dict[str, Any]:
    fd1_artifact = fd1_artifact or {}
    reservoir = reservoir or []
    reservoir_meta = reservoir_meta or {
        "denominator_source_protocol": "raw_external_full_frame_disjoint_file_miss_reservoir_quota_scan.v1",
        "raw_denominator_scan_attempted": False, "raw_scan_attempted_records": 0,
        "raw_scan_fetched_records": 0, "raw_scan_prior_exact_excluded_records": 0,
        "raw_scan_prior_window_excluded_records": 0,
        "raw_scan_yield_file_miss_records": len(reservoir),
        "raw_scan_baseline_reached_records": 0, "raw_scan_baseline_error_records": 0,
        "reservoir_min_count": P4I_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": False,
        "disjoint_from_exact_fd1_bea4_bea5_prior": False,
        "p4h_exact_keys_available_for_exclusion": False,
        "p4h_overlap_resolved": False,
        "reservoir_upper_bound_includes_possible_p4h_overlap": False,
        "reservoir_upper_bound_count": len(reservoir),
        "qualified_denominator_reservoir_count": 0,
        "prior_fd1_denominator_reused": False, "prior_raw_windows_excluded": True,
        "prior_raw_exclusion_mode": "not_attempted",
        "disjoint_from_prior": False,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": _initial_reservoir_scan_rows(),
        "prior_raw_exclusion_records": [],
    }
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
    exact_prior_exclusion_used = bool(reservoir_meta.get("exact_prior_exclusion_used", False))
    blocking = _blocking_failure_count(fcc)
    stop_go = _stop_go_records(
        reservoir_count=len(reservoir),
        raw_scan_attempted=bool(reservoir_meta.get("raw_denominator_scan_attempted", False)),
        disjoint=bool(reservoir_meta.get("disjoint_from_prior", False)),
        blocking_failure_count=blocking,
        exact_prior_exclusion_used=exact_prior_exclusion_used,
        p4h_overlap_resolved=bool(reservoir_meta.get("p4h_overlap_resolved", False)),
    )
    if status == "auto":
        if blocking > 0:
            status = "fail_schema_contract"
        elif stop_go[0]["stop_go_decision"] in STATUSES:
            status = stop_go[0]["stop_go_decision"]
        else:
            status = "no_go_disjoint_denominator_reservoir_insufficient"
    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true.update({
        "fd1_artifact_read": bool(fd1_artifact),
        "fd1_private_decomposition_parsed": fd1_private_parsed,
        "fd1_private_decomposition_replay_supplied": bool(rav.supplied if rav else False),
        "fd1_private_decomposition_replay_validated": replay_validated,
        "fd1_private_decomposition_replay_executed_by_workflow": bool(rav.supplied and rav.validated) if rav else False,
        "p4h_artifact_read": bool(p4h_artifact),
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
        "diagnostic_arm": DIAGNOSTIC_ARM,
        "policy_arms": list(POLICY_ARMS),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": str(reservoir_meta.get("denominator_source_protocol", "raw_external_full_frame_disjoint_file_miss_reservoir_quota_scan.v1")),
        "records_decomposed": int(fd1_records),
        "private_manifest_record_count": int(fd1_manifest_count),
        "denominator_count": int(len(reservoir)),
        "cumulative_denominator_reservoir_count": int(len(reservoir)),
        "reservoir_upper_bound_count": int(reservoir_meta.get("reservoir_upper_bound_count", len(reservoir))),
        "qualified_denominator_reservoir_count": int(reservoir_meta.get("qualified_denominator_reservoir_count", len(reservoir) if reservoir_meta.get("p4h_overlap_resolved", False) else 0)),
        "failure_reason_category": failure_reason_category,
        "source_run_records": _source_run_records(fd1_schema_version=fd1_schema, fd1_source_artifact_hash=fd1_hash, fd1_status=fd1_status, fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4h_status=p4h_status, p4h_denominator_count=p4h_denominator_count, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason),
        "denominator_reservoir_records": _denominator_reservoir_records(reservoir),
        "denominator_scan_records": _denominator_scan_records(reservoir_meta),
        "prior_raw_exclusion_records": _prior_raw_exclusion_records(reservoir_meta),
        "subgroup_reservoir_records": _subgroup_reservoir_records(reservoir),
        "stop_go_records": stop_go,
        "gate_records": _gate_records(fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, denominator_meta=reservoir_meta, reservoir_count=len(reservoir), fd1_private_decomposition_parsed=fd1_private_parsed, replay_artifact_validated=replay_validated, forbidden_scan_pass=True, blocking_failure_count=blocking, exact_prior_exclusion_used=exact_prior_exclusion_used),
        "private_manifest_records": _private_manifest_records(fd1_artifact, extra_manifests),
        "failure_category_count_records": _failure_category_count_records(fcc),
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "raw_denominator_scan_attempted": bool(reservoir_meta.get("raw_denominator_scan_attempted", False)),
        "raw_scan_fetched_records": int(reservoir_meta.get("raw_scan_fetched_records", 0)),
        "raw_scan_attempted_records": int(reservoir_meta.get("raw_scan_attempted_records", 0)),
        "raw_scan_prior_exact_excluded_records": int(reservoir_meta.get("raw_scan_prior_exact_excluded_records", 0)),
        "raw_scan_prior_window_excluded_records": int(reservoir_meta.get("raw_scan_prior_window_excluded_records", 0)),
        "raw_scan_yield_file_miss_records": int(reservoir_meta.get("raw_scan_yield_file_miss_records", 0)),
        "raw_scan_baseline_reached_records": int(reservoir_meta.get("raw_scan_baseline_reached_records", 0)),
        "raw_scan_baseline_error_records": int(reservoir_meta.get("raw_scan_baseline_error_records", 0)),
        "prior_raw_exclusion_mode": str(reservoir_meta.get("prior_raw_exclusion_mode", "not_attempted")),
        "exact_prior_exclusion_scope": str(reservoir_meta.get("exact_prior_exclusion_scope", EXACT_EXCLUSION_SCOPE)),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "disjoint_from_exact_fd1_bea4_bea5_prior": bool(reservoir_meta.get("disjoint_from_exact_fd1_bea4_bea5_prior", False)),
        "p4h_exact_keys_available_for_exclusion": bool(reservoir_meta.get("p4h_exact_keys_available_for_exclusion", False)),
        "p4h_overlap_resolved": bool(reservoir_meta.get("p4h_overlap_resolved", False)),
        "reservoir_upper_bound_includes_possible_p4h_overlap": bool(reservoir_meta.get("reservoir_upper_bound_includes_possible_p4h_overlap", False)),
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": bool(reservoir_meta.get("prior_raw_windows_excluded", True)),
        "denominator_source_gold_file_absent_count": int(reservoir_meta.get("source_gold_file_absent_count", 0)),
        "excluded_prior_windows_count": int(reservoir_meta.get("excluded_prior_window_count", 0)),
        "denominator_disjoint_from_prior": bool(reservoir_meta.get("disjoint_from_prior", False)),
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": bool(reservoir_meta.get("denominator_constructed_before_scheduler_outcomes", True)),
        "reservoir_min_count": P4I_RESERVOIR_MIN_COUNT,
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
            "scheduler_validation_claimed": False,
            "retrieval_expansion_claimed": False,
            "selector_or_reranker_executed": False,
            "is_full_external_benchmark_evaluation": False,
            "is_disjoint_denominator_reservoir_audit": True,
            "is_latency_in_relevance": False,
            "signal_strength": "bea_v1_p4i_disjoint_denominator_reservoir_audit_aggregate_only",
            "frozen_p4h_rerun_authorization_scope": "stop_go_records_only",
        },
    }
    scan = _v1_p4i_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        # refresh stop_go decision to reflect the privacy failure
        report["stop_go_records"] = [{
            **stop_go[0],
            "stop_go_decision": "fail_forbidden_scan",
            "stop_go_reason": "forbidden_content_leak_blocked",
        }]
    return report


def _run_reservoir_audit(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    fd1_artifact_path: Path, fd1_private_decomposition_jsonl: Path | None,
    fd1_replay_artifact: Path | None, p4h_artifact_path: Path | None,
    enable_network: bool,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    start = time.perf_counter()
    fd1_artifact, fd1_schema, fd1_hash, fd1_status = p4._load_committed_artifact(fd1_artifact_path)
    if fd1_status != "pass":
        fcc["fd1_artifact_missing" if fd1_status == "artifact_missing" else "fd1_artifact_parse_failed"] = 1
        return _base_report(status="unavailable_with_reason", failure_reason_category=fd1_status, self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fcc_in=fcc)
    # P4H committed artifact (motivation context + aggregate disclosure).
    p4h_artifact: dict[str, Any] = {}
    p4h_status_str = ""
    p4h_denom_count = P4H_DENOMINATOR_COUNT
    if p4h_artifact_path is not None:
        try:
            p4h_artifact, _, _, p4h_load_status = p4._load_committed_artifact(p4h_artifact_path)
            if p4h_load_status == "pass":
                p4h_status_str = str(p4h_artifact.get("status", "") or "")
                p4h_denom_count = int(p4h_artifact.get("denominator_count", P4H_DENOMINATOR_COUNT) or 0)
            else:
                p4h_artifact = {}
        except Exception:
            p4h_artifact = {}
    mismatch: list[str] = []
    fd1_artifact_status = p4.bea_v1_p1._fd1_status(fd1_artifact)
    fd1_manifest = p4.bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact)
    fd1_manifest_count = int(fd1_manifest.get("record_count", 0) or 0)
    if fd1_schema != p4.FD1_SOURCE_SCHEMA_VERSION:
        fcc["fd1_schema_version_mismatch"] = 1; mismatch.append("fd1_schema_version_mismatch")
    if fd1_artifact_status != p4.FD1_SOURCE_STATUS:
        fcc["fd1_status_mismatch"] = 1; mismatch.append("fd1_status_mismatch")
    fd1_records = p4.bea_v1_p1._fd1_records_decomposed(fd1_artifact)
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
    reservoir: list[ReservoirRecord] = []
    reservoir_meta: dict[str, Any] = {
        "denominator_source_protocol": "raw_external_full_frame_disjoint_file_miss_reservoir_quota_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "reservoir_count": 0,
        "raw_denominator_scan_attempted": False,
        "raw_scan_fetched_records": 0,
        "raw_scan_attempted_records": 0,
        "raw_scan_prior_exact_excluded_records": 0,
        "raw_scan_prior_window_excluded_records": 0,
        "raw_scan_yield_file_miss_records": 0,
        "raw_scan_baseline_reached_records": 0,
        "raw_scan_baseline_error_records": 0,
        "reservoir_min_count": P4I_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": False,
        "disjoint_from_exact_fd1_bea4_bea5_prior": False,
        "p4h_exact_keys_available_for_exclusion": False,
        "p4h_overlap_resolved": False,
        "reservoir_upper_bound_includes_possible_p4h_overlap": False,
        "reservoir_upper_bound_count": 0,
        "qualified_denominator_reservoir_count": 0,
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": True,
        "prior_raw_exclusion_mode": "not_attempted",
        "disjoint_from_prior": False,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": _initial_reservoir_scan_rows(),
        "prior_raw_exclusion_records": [],
    }
    manifests: list[dict[str, Any]] = []
    if enable_network and audit_match and pt.computed and rav.validated:
        try:
            reservoir, scan_fcc, reservoir_meta, scan_manifest = _scan_reservoir(openlocus_bin=openlocus_bin, pt=pt)
            manifests.append(scan_manifest)
            for k, v in scan_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if len(reservoir) < P4I_RESERVOIR_MIN_COUNT:
                fcc["reservoir_insufficient"] = 1
            if not reservoir_meta.get("exact_prior_exclusion_used"):
                fcc["exact_prior_exclusion_unavailable"] = 1
            if not reservoir_meta.get("p4h_overlap_resolved"):
                fcc["p4h_overlap_not_resolved"] = 1
        except Exception:
            fcc["retrieval_policy_failed"] = 1
            fcc["unexpected_exception"] = 1
    elif enable_network:
        fcc["denominator_reservoir_scan_not_attempted"] = 1
        fcc["raw_denominator_scan_not_attempted"] = 1
    else:
        fcc["network_required_but_disabled"] = 1
    return _base_report(status="auto", failure_reason_category="", self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fd1_artifact=fd1_artifact, fd1_schema=fd1_schema, fd1_hash=fd1_hash, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4h_status=p4h_status_str, p4h_denominator_count=p4h_denom_count, reservoir=reservoir, reservoir_meta=reservoir_meta, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason, fcc_in=fcc, extra_manifests=manifests, aggregate_runtime_seconds=time.perf_counter() - start)


def _build_synthetic_reservoir(
    count: int = 80, *, p4h_overlap_resolved: bool = False,
) -> tuple[list[ReservoirRecord], dict[str, Any]]:
    reservoir: list[ReservoirRecord] = []
    for i in range(count):
        bm = "contextbench" if i < count // 2 else "repoqa"
        offset = P4I_RAW_CONTEXTBENCH_OFFSET if bm == "contextbench" else P4I_RAW_REPOQA_OFFSET
        limit = P4I_RAW_CONTEXTBENCH_LIMIT if bm == "contextbench" else P4I_RAW_REPOQA_LIMIT
        window = "contextbench_raw_full_frame_reservoir_scan" if bm == "contextbench" else "repoqa_raw_full_frame_reservoir_scan"
        reservoir.append(ReservoirRecord(
            private_record_id=f"{bm}-raw-{offset + i}",
            benchmark=bm,
            record_index=offset + i,
            window_name=window,
            raw_window_offset=offset,
            raw_window_limit=limit,
        ))
    scan_rows = _initial_reservoir_scan_rows()
    for row in scan_rows:
        selected = sum(1 for d in reservoir if d.benchmark == row["benchmark"])
        row["raw_rows_fetched"] = int(row["raw_limit_requested"])
        row["raw_rows_attempted"] = selected
        row["raw_rows_file_miss_selected"] = selected
        row["target_reached_in_window"] = len(reservoir) >= P4I_RESERVOIR_MIN_COUNT
    prior_raw_keys = set()
    for bm in ("contextbench", "repoqa"):
        for i in range(ORIGINAL_P1234_DENOMINATOR_COUNT):
            prior_raw_keys.add((bm, i))
    exact_exclusion_records = []
    for sp in ("BEA-4", "BEA-5"):
        for bm in ("contextbench", "repoqa"):
            exact_exclusion_records.append({
                "source_phase": P4I_RAW_SOURCE_PHASE,
                "benchmark": bm,
                "exclusion_source_phase": sp,
                "exclusion_basis": "fd1_private_decomposition_exact_bea4_offset" if sp == "BEA-4" else "fd1_private_decomposition_exact_bea5_raw_index",
                "excluded_raw_record_count": ORIGINAL_P1234_DENOMINATOR_COUNT // 2,
                "private_row_ids_publicly_serialized": False,
            })
    disclosure_records = _prior_exclusion_disclosure_records(
        prior_raw_keys=prior_raw_keys,
        exact_exclusion_records=exact_exclusion_records,
        use_exact_prior_keys=True,
    )
    meta = {
        "denominator_source_protocol": "raw_external_full_frame_disjoint_file_miss_reservoir_quota_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "reservoir_count": len(reservoir),
        "reservoir_upper_bound_count": len(reservoir),
        "qualified_denominator_reservoir_count": len(reservoir) if p4h_overlap_resolved else 0,
        "raw_denominator_scan_attempted": True,
        "raw_scan_fetched_records": P4I_RAW_CONTEXTBENCH_LIMIT + P4I_RAW_REPOQA_LIMIT,
        "raw_scan_attempted_records": len(reservoir),
        "raw_scan_prior_exact_excluded_records": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "raw_scan_prior_window_excluded_records": 0,
        "raw_scan_yield_file_miss_records": len(reservoir),
        "raw_scan_baseline_reached_records": 0,
        "raw_scan_baseline_error_records": 0,
        "reservoir_min_count": P4I_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": True,
        "disjoint_from_exact_fd1_bea4_bea5_prior": True,
        "p4h_exact_keys_available_for_exclusion": bool(p4h_overlap_resolved),
        "p4h_overlap_resolved": bool(p4h_overlap_resolved),
        "reservoir_upper_bound_includes_possible_p4h_overlap": not p4h_overlap_resolved,
        "prior_fd1_denominator_reused": False,
        "prior_raw_windows_excluded": True,
        "prior_raw_exclusion_mode": "fd1_private_exact_raw_keys",
        "disjoint_from_prior": bool(p4h_overlap_resolved),
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": scan_rows,
        "prior_raw_exclusion_records": disclosure_records,
    }
    return reservoir, meta


def _synthetic_private_manifest(record_count: int) -> dict[str, Any]:
    digest = hashlib.sha256(f"bea_v1_p4i_synthetic_{record_count}".encode("utf-8")).hexdigest()
    return {
        "manifest_name": "bea_v1_p4i_private_reservoir_scan_manifest",
        "schema_version": "bea_v1_p4i_private_reservoir_scan.v1",
        "storage_class": "private_tmp_only",
        "record_count": int(record_count),
        "records_written": bool(record_count > 0),
        "path_publicly_serialized": False,
        "manifest_hash": digest,
    }


METRIC_TABLE_KEYS = (
    "source_run_records", "denominator_reservoir_records",
    "denominator_scan_records", "prior_raw_exclusion_records",
    "subgroup_reservoir_records", "stop_go_records", "gate_records",
    "private_manifest_records", "failure_category_count_records",
)


def _has_dynamic_dict(report: dict[str, Any]) -> bool:
    """Return True if the report contains a dynamic dict for public metrics.

    Allowed dicts (fixed schema, not dynamic): the root, ``framing``, and
    ``forbidden_scan`` (with ``violation_categories`` as a list).  All metric
    tables must be lists of flat scalar records (no nested dict values).
    """
    for k, v in report.items():
        if k in ("framing", "forbidden_scan"):
            continue
        if isinstance(v, dict):
            return True
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    for iv in item.values():
                        if isinstance(iv, (dict, list)):
                            return True
    fs = report.get("forbidden_scan", {})
    if isinstance(fs, dict) and isinstance(fs.get("violation_categories"), dict):
        return True
    return False


def _manifest_fields_safe(manifests: list[dict[str, Any]]) -> bool:
    allowed = {"manifest_name", "schema_version", "storage_class",
               "record_count", "records_written", "path_publicly_serialized",
               "manifest_hash"}
    forbidden_value_keys = {"private_record_id", "raw_record_index_private",
                            "query_private", "repo_url_private",
                            "base_commit_private", "gold_paths_private",
                            "candidate_paths_private", "row_hash", "key_hash",
                            "path_hash", "raw_key_hash"}
    for m in manifests:
        if not isinstance(m, dict):
            return False
        for k in m:
            if str(k) not in allowed and str(k) not in {"manifest_name"}:
                # only allowed provenance fields; reject row/key/path hashes
                if str(k).endswith("_hash") and str(k) != "manifest_hash":
                    return False
                if str(k) in forbidden_value_keys:
                    return False
        if "manifest_hash" in m and not isinstance(m["manifest_hash"], str):
            return False
        if "record_count" in m and not isinstance(m["record_count"], int):
            return False
    return True


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("identity_schema", SCHEMA_VERSION == "bea_v1_p4i_disjoint_denominator_reservoir_audit.v1"))
    checks.append(_check("phase_p4i", PHASE == "BEA-v1-P4I"))
    checks.append(_check("claim_level_audit_only", CLAIM_LEVEL == "bea_v1_p4i_disjoint_denominator_reservoir_audit_only"))
    checks.append(_check("diagnostic_arm_baseline_only", DIAGNOSTIC_ARM == "current_bea_candidate_pool_replay"))
    checks.append(_check("policy_arms_count_1", len(POLICY_ARMS) == 1))
    checks.append(_check("no_p2_p3_p4_in_policy_arms", "p2_depth_only_reference" not in POLICY_ARMS and "p3_constrained_depth_policy_reference" not in POLICY_ARMS and "p4_latency_aware_action_scheduler" not in POLICY_ARMS))
    checks.append(_check("reservoir_min_80", P4I_RESERVOIR_MIN_COUNT == 80))
    checks.append(_check("full_frame_contextbench_offset_0", P4I_RAW_CONTEXTBENCH_OFFSET == 0))
    checks.append(_check("full_frame_contextbench_limit_480", P4I_RAW_CONTEXTBENCH_LIMIT == 480))
    checks.append(_check("full_frame_repoqa_offset_0", P4I_RAW_REPOQA_OFFSET == 0))
    checks.append(_check("full_frame_repoqa_limit_240", P4I_RAW_REPOQA_LIMIT == 240))
    checks.append(_check("no_fixed_tail_window_names", all("after_" not in str(w.get("window_name", "")) for w in P4I_RAW_WINDOWS)))
    checks.append(_check("p4h_result_checkpoint_9305701", P4H_RESULT_CHECKPOINT == "9305701"))
    checks.append(_check("p4h_ci_run_id_28132121958", P4H_CI_RUN_ID == "28132121958"))
    checks.append(_check("p4h_denominator_count_73", P4H_DENOMINATOR_COUNT == 73))
    checks.append(_check("p4h_denominator_min_80", P4H_DENOMINATOR_MIN == 80))
    checks.append(_check("exact_exclusion_scope_bea4_bea5_only", EXACT_EXCLUSION_SCOPE == "fd1_private_exact_bea4_bea5_raw_keys_only"))
    checks.append(_check("latency_not_in_relevance_false", DEFAULT_FALSE_FLAGS["latency_in_candidate_relevance"] is False))
    checks.append(_check("no_selector_change", DEFAULT_FALSE_FLAGS["selector_or_reranker_changed"] is False))
    checks.append(_check("no_selector_executed", DEFAULT_FALSE_FLAGS["selector_or_reranker_executed"] is False))
    checks.append(_check("p5_authorized_false", DEFAULT_FALSE_FLAGS["p5_authorized"] is False))
    checks.append(_check("v1_a_authorized_false", DEFAULT_FALSE_FLAGS["v1_a_authorized"] is False))
    checks.append(_check("frozen_p4h_rerun_authorized_false_default", DEFAULT_FALSE_FLAGS["frozen_p4h_rerun_authorized"] is False))
    checks.append(_check("p2_p3_p4_arms_not_executed_flags", DEFAULT_FALSE_FLAGS["p2_depth_only_reference_executed"] is False and DEFAULT_FALSE_FLAGS["p3_constrained_depth_policy_reference_executed"] is False and DEFAULT_FALSE_FLAGS["p4_latency_aware_action_scheduler_executed"] is False))
    with tempfile.TemporaryDirectory(prefix="v1p4i_st_") as sd:
        td = Path(sd)
        priv = td / "bea_fd1.decomposition.jsonl"
        p4._build_synthetic_private_decomposition_jsonl(priv, gold_file_absent_count=199)
        pt = p4._parse_private_decomposition_jsonl(priv)
        p4._compute_file_selector_lower_bound(pt)
        checks.append(_check("synthetic_fd1_rows_86040", pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS))
        reservoir80, meta80 = _build_synthetic_reservoir(80, p4h_overlap_resolved=True)
        checks.append(_check("synthetic_reservoir_80", len(reservoir80) == 80))
        checks.append(_check("reservoir_source_protocol", meta80.get("denominator_source_protocol") == "raw_external_full_frame_disjoint_file_miss_reservoir_quota_scan.v1"))
        checks.append(_check("reservoir_scan_attempted", meta80.get("raw_denominator_scan_attempted") is True))
        checks.append(_check("prior_fd1_not_reused", meta80.get("prior_fd1_denominator_reused") is False))
        checks.append(_check("exact_prior_exclusion_used_true", meta80.get("exact_prior_exclusion_used") is True))
        checks.append(_check("raw_windows_excluded_prior", meta80.get("prior_raw_windows_excluded") is True))
        checks.append(_check("synthetic_ready_p4h_overlap_resolved", meta80.get("p4h_overlap_resolved") is True))
        checks.append(_check("synthetic_ready_not_upper_bound_only", meta80.get("reservoir_upper_bound_includes_possible_p4h_overlap") is False))
        checks.append(_check("prior_exclusion_disclosure_records_present", len(meta80.get("prior_raw_exclusion_records", [])) >= 4))
        checks.append(_check("scan_rows_disclose_full_frame_ranges", all("raw_offset_requested" in r and "raw_limit_requested" in r and "raw_rows_fetched" in r for r in meta80.get("denominator_scan_records", []))))
        checks.append(_check("scan_rows_no_private_ids", all("private_record_id" not in r and "record_ids" not in r for r in meta80.get("denominator_scan_records", []))))
        checks.append(_check("p4h_disclosure_record_present", any(r.get("exclusion_source_phase") == "BEA-v1-P4H" and r.get("excluded_record_count_aggregate") == 73 for r in meta80.get("prior_raw_exclusion_records", []))))
        checks.append(_check("p1p2p3p4_disclosure_record_present", any(r.get("exclusion_source_phase") == "BEA-v1-P1/P2/P3/P4" for r in meta80.get("prior_raw_exclusion_records", []))))
        replay_path = td / "fd1_replay_report.json"
        p4._build_synthetic_fd1_replay_artifact(replay_path)
        rav = p4._validate_fd1_replay_artifact(replay_path, "a" * 64)
        fd1_art = p4._build_synthetic_fd1_artifact()
        p4h_art = {"status": P4H_RESULT_STATUS, "denominator_count": P4H_DENOMINATOR_COUNT, "stop_go_records": [{"denominator_min": P4H_DENOMINATOR_MIN}], "raw_scan_attempted_records": P4H_RAW_SCAN_ATTEMPTED_RECORDS, "raw_scan_yield_file_miss_records": P4H_RAW_SCAN_YIELD_FILE_MISS_RECORDS}
        scan_manifest = _synthetic_private_manifest(len(reservoir80))
        report80 = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, reservoir=reservoir80, reservoir_meta=meta80, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        for table in METRIC_TABLE_KEYS:
            checks.append(_check(f"table_{table}_is_list", isinstance(report80.get(table), list)))
        checks.append(_check("synthetic_reservoir_80_ready", report80.get("status") == "reservoir_ready_for_frozen_p4h_rerun"))
        checks.append(_check("forbidden_scan_pass", report80.get("forbidden_scan", {}).get("status") == "pass"))
        checks.append(_check("reservoir_ready_authorization_flags_false", report80.get("stop_go_records", [{}])[0].get("p5_authorized") is False and report80.get("stop_go_records", [{}])[0].get("v1_a_authorized") is False and report80.get("stop_go_records", [{}])[0].get("runtime_promotion_authorized") is False and report80.get("stop_go_records", [{}])[0].get("method_winner_authorized") is False and report80.get("stop_go_records", [{}])[0].get("broad_retrieval_expansion_authorized") is False))
        checks.append(_check("reservoir_ready_frozen_p4h_rerun_authorized_true", report80.get("stop_go_records", [{}])[0].get("frozen_p4h_rerun_authorized") is True))
        checks.append(_check("top_level_frozen_p4h_rerun_authorization_stop_go_only", report80.get("frozen_p4h_rerun_authorized") is False and report80.get("framing", {}).get("frozen_p4h_rerun_authorization_scope") == "stop_go_records_only"))
        checks.append(_check("report_reservoir_records_present", len(report80.get("denominator_reservoir_records", [])) > 0))
        checks.append(_check("report_scan_records_present", len(report80.get("denominator_scan_records", [])) == 2))
        checks.append(_check("report_prior_exclusion_records_present", len(report80.get("prior_raw_exclusion_records", [])) >= 4))
        checks.append(_check("report_prior_fd1_not_reused", report80.get("prior_fd1_denominator_reused") is False))
        checks.append(_check("report_exact_prior_exclusion_used_true", report80.get("exact_prior_exclusion_used") is True))
        checks.append(_check("report_cumulative_reservoir_count", report80.get("cumulative_denominator_reservoir_count") == 80))
        checks.append(_check("report_qualified_denominator_reservoir_count_80", report80.get("qualified_denominator_reservoir_count") == 80))
        reservoir80_unqualified, meta80_unqualified = _build_synthetic_reservoir(80, p4h_overlap_resolved=False)
        report80_unqualified = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, reservoir=reservoir80_unqualified, reservoir_meta=meta80_unqualified, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("reservoir_80_unqualified_without_p4h_overlap", report80_unqualified.get("status") == "no_go_disjoint_denominator_reservoir_unqualified"))
        checks.append(_check("unqualified_no_frozen_p4h_rerun", report80_unqualified.get("stop_go_records", [{}])[0].get("frozen_p4h_rerun_authorized") is False))
        checks.append(_check("unqualified_upper_bound_count_80", report80_unqualified.get("reservoir_upper_bound_count") == 80 and report80_unqualified.get("qualified_denominator_reservoir_count") == 0))
        # reservoir < 80 => no_go insufficient
        reservoir79, meta79 = _build_synthetic_reservoir(79)
        report79 = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, aggregate_runtime_seconds=0.5)
        checks.append(_check("synthetic_reservoir_79_insufficient", report79.get("status") == "no_go_disjoint_denominator_reservoir_insufficient"))
        checks.append(_check("insufficient_reservoir_count", report79.get("cumulative_denominator_reservoir_count") == 79))
        # default no-network => unavailable_with_reason
        report_default = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="missing", network_mode="disabled_opt_in", fcc_in={"network_required_but_disabled": 1})
        checks.append(_check("default_unavailable_with_reason", report_default.get("status") == "unavailable_with_reason"))
        checks.append(_check("default_not_pass", report_default.get("status") != "reservoir_ready_for_frozen_p4h_rerun"))
        # blocking failures cannot be reported as insufficient denominator
        report_scan_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, fcc_in={"raw_denominator_scan_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("scan_failure_not_insufficient_no_go", report_scan_fail.get("status") == "fail_schema_contract"))
        report_clone_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, fcc_in={"raw_denominator_clone_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("clone_failure_not_insufficient_no_go", report_clone_fail.get("status") == "fail_schema_contract"))
        report_exact_missing = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79, "exact_prior_exclusion_used": False}, audit_match=True, fcc_in={"exact_prior_exclusion_unavailable": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("exact_prior_missing_fail_closed", report_exact_missing.get("status") == "fail_schema_contract"))
        report_not_attempted = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, reservoir=[], reservoir_meta={**meta79, "reservoir_count": 0, "raw_denominator_scan_attempted": False}, audit_match=True, fcc_in={"denominator_reservoir_scan_not_attempted": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("not_attempted_is_fail_not_insufficient", report_not_attempted.get("status") == "fail_schema_contract"))
        # public shape is records-only (no dynamic dicts)
        checks.append(_check("public_shape_no_dynamic_dicts", _has_dynamic_dict(report80) is False))
        # manifest count/hash shape safe (provenance hash allowed, no row/key/path hashes)
        checks.append(_check("manifest_fields_safe", _manifest_fields_safe(report80.get("private_manifest_records", [])) is True))
        manifest_has_hash = any(m.get("manifest_hash") for m in report80.get("private_manifest_records", []) if isinstance(m, dict))
        checks.append(_check("manifest_has_provenance_hash", manifest_has_hash is True))
        checks.append(_check("manifest_no_private_paths", all(m.get("path_publicly_serialized") is False for m in report80.get("private_manifest_records", []) if isinstance(m, dict))))
        # forbidden scanner rejects private keys/ids
        leaked = dict(report80)
        leaked["private_record_id"] = "leak"
        checks.append(_check("scanner_rejects_private_record_id", _v1_p4i_forbidden_scan_summary(leaked)["status"] == "fail"))
        leaked2 = dict(report80)
        leaked2["candidate_paths"] = ["leak"]
        checks.append(_check("scanner_rejects_candidate_paths", _v1_p4i_forbidden_scan_summary(leaked2)["status"] == "fail"))
        leaked3 = dict(report80)
        leaked3["exact_raw_keys"] = ["leak"]
        checks.append(_check("scanner_rejects_exact_raw_keys", _v1_p4i_forbidden_scan_summary(leaked3)["status"] == "fail"))
        # forbidden_scan.violation_categories is a list (records-only)
        checks.append(_check("forbidden_violation_categories_is_list", isinstance(report80.get("forbidden_scan", {}).get("violation_categories"), list)))
        # reservoir_ready requires >= 80 gate
        checks.append(_check("reservoir_80_gate_pass", bool(report80.get("gate_records") and any(g.get("gate") == "reservoir_count_min" and g.get("passed") is True for g in report80.get("gate_records", [])))))
        checks.append(_check("reservoir_79_gate_fail", bool(report79.get("gate_records") and any(g.get("gate") == "reservoir_count_min" and g.get("passed") is False for g in report79.get("gate_records", [])))))
    parser = build_parser()
    opts = {opt for action in parser._actions for opt in action.option_strings}
    for opt in ("--self-test", "--out", "--fd1-artifact", "--fd1-private-decomposition-jsonl", "--fd1-replay-artifact", "--p4h-artifact", "--openlocus", "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in opts))
    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-P4I Disjoint Denominator Reservoir Audit")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd1-private-decomposition-jsonl", type=Path, default=None)
    ap.add_argument("--fd1-replay-artifact", type=Path, default=None)
    ap.add_argument("--p4h-artifact", type=Path, default=DEFAULT_P4H_ARTIFACT)
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
            report = _run_reservoir_audit(openlocus_bin=openlocus_bin or "", openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, self_test_passed=True, self_test_checks_total=len(checks), fd1_artifact_path=args.fd1_artifact, fd1_private_decomposition_jsonl=args.fd1_private_decomposition_jsonl, fd1_replay_artifact=args.fd1_replay_artifact, p4h_artifact_path=args.p4h_artifact, enable_network=enable_network)
        except Exception:
            report = _base_report(status="unavailable_with_reason", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, fcc_in={"unexpected_exception": 1})
    if report.get("provider_calls_made") is not False or report.get("latency_in_candidate_relevance") is not False or report.get("gold_labels_used_for_policy") is not False or report.get("query_anchors_used_in_p4_arm") is not False or report.get("p2_depth_only_reference_executed") is not False or report.get("p3_constrained_depth_policy_reference_executed") is not False or report.get("p4_latency_aware_action_scheduler_executed") is not False:
        report["status"] = "fail_schema_contract"
    _enforce_v1_p4i_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    sgr = report.get("stop_go_records", [{}])[0] if report.get("stop_go_records") else {}
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={report['phase']}, denominator_count={report.get('denominator_count', 0)}, stop_go_decision={sgr.get('stop_go_decision', '')})")
    if not enable_network:
        print("enable_external_benchmark_network is false; skipping real BEA-v1-P4I disjoint denominator reservoir audit.")


if __name__ == "__main__":
    main()
