#!/usr/bin/env python3
"""BEA-v1-P4J: Cross-Source File-Miss Reservoir Unlock Audit.

P4J is a bounded **cross-source denominator/source audit** performed after the
BEA-v1-P4I No-Go (checkpoint ``cc19f5b``).  It does **not** run P2/P3/P4
scheduler arms, does **not** validate a scheduler, does **not** expand
retrieval, does **not** execute a selector/reranker, does **not** call any
provider, does **not** run runtime/default promotion or method-winner logic,
and does **not** authorize P5 / BEA-v1-A / frozen P4 rerun.

Objective: determine whether the P4H/P4I denominator blocker
(``no_go_p4h_insufficient_denominator`` with 73/80 disjoint file-miss records,
followed by ``no_go_disjoint_denominator_reservoir_insufficient``) is specific
to the currently supported ContextBench/RepoQA **Python** frame, or whether
alternative already-supported **cross-source frames** can unlock at least 80
baseline file-miss denominator records.

P4J scans only already-supported source frames, evaluated with the existing
``current_bea_candidate_pool_replay`` diagnostic arm:

1. ContextBench ``contextbench_verified/train`` with ``language_filter="all"``
   via ``c5a._fetch_contextbench_rows(limit, "all")``.  The ``default`` config
   is NOT used (that would be new dataset integration).
2. RepoQA non-Python top-level asset languages via
   ``c5d._download_asset_to_bytes`` + ``c5d._decompress_asset`` +
   ``c5d._parse_repoqa_needles(parsed, lang, limit)``.  The c5d CLI is bypassed
   because its argparse currently only allows Python.

SWE-Explore / CORE-Bench / SWE-bench original / ContextBench default config are
excluded (documented in ``docs``).

A candidate denominator record is a baseline/current candidate pool *miss* of
the gold file.  The scan does **not** stop at an 80-record target; it counts
the full cumulative cross-source file-miss reservoir.

Exact BEA-4/5 prior raw-key exclusion from FD1 private replay is used **where
applicable** (ContextBench Python rows mapped via python-ordinal).  For
non-Python frames a by-construction disjoint basis is disclosed (BEA-4/5 only
ran on the Python frame).  P4H/P4I exact selected keys remain unavailable
unless a private exact-key source is regenerated under ``/tmp``; overlap with
P4H/P4I is therefore kept unresolved and the qualified all-prior-disjoint
reservoir count remains 0 unless overlap is resolved.

The public artifact is aggregate-only and records-only.  Per-record scan
traces are written only under ``/tmp`` (or an ignored runs/private path) and
are never uploaded.  No private raw keys/ids/paths/queries/gold/candidate
paths/snippets/prompts/provider payloads/private hashes are serialized; the
only provenance hash permitted is the private scan manifest hash.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
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
import bea_v1_p4i_disjoint_denominator_reservoir_audit as p4i  # noqa: E402

SCHEMA_VERSION = "bea_v1_p4j_cross_source_reservoir_unlock_audit.v1"
GENERATED_BY = "eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py"
CLAIM_LEVEL = "bea_v1_p4j_cross_source_reservoir_unlock_audit_only"
MODE = "bea_v1_p4j_cross_source_reservoir_unlock_audit"
PHASE = "BEA-v1-P4J"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p4j_cross_source_reservoir_unlock_audit/"
    "bea_v1_p4j_cross_source_reservoir_unlock_audit_report.json"
)
DEFAULT_FD1_ARTIFACT = p4.DEFAULT_FD1_ARTIFACT
DEFAULT_P4H_ARTIFACT = p4h.DEFAULT_OUT
DEFAULT_P4I_ARTIFACT = p4i.DEFAULT_OUT

# --- P4I binding context (read-only motivation) ---
P4I_RESULT_CHECKPOINT = "cc19f5b"
P4I_RESULT_STATUS = "no_go_disjoint_denominator_reservoir_insufficient"
P4I_CI_RUN_ID = "28137455572"
P4I_DENOMINATOR_COUNT = 73
P4I_DENOMINATOR_MIN = 80
P4I_RAW_SCAN_YIELD_FILE_MISS_RECORDS = 73
P4I_RAW_SCAN_ATTEMPTED_RECORDS = 127

# --- P4H binding context (read-only motivation) ---
P4H_RESULT_CHECKPOINT = "9305701"
P4H_RESULT_STATUS = "no_go_p4h_insufficient_denominator"
P4H_DENOMINATOR_COUNT = 73
P4H_DENOMINATOR_MIN = 80

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

P4J_RESERVOIR_MIN_COUNT = 80
P4J_RAW_SOURCE_PHASE = "P4J-CROSS-SOURCE-RAW"

# Cross-source frame 1: ContextBench "all" languages (NOT the default config).
P4J_CONTEXTBENCH_ALL_OFFSET = 0
P4J_CONTEXTBENCH_ALL_LIMIT = 480
P4J_CONTEXTBENCH_ALL_LANGUAGE_FILTER = "all"
P4J_CONTEXTBENCH_ALL_FRAME = "contextbench_all_languages"

# Cross-source frame 2: RepoQA non-Python asset languages.  Languages are
# discovered dynamically from the downloaded asset at scan time; the c5d CLI
# is bypassed because its argparse only allows Python.
P4J_REPOQA_NON_PYTHON_FRAME = "repoqa_non_python_languages"
P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT = 60

# Source frames attempted (the RepoQA per-language breakdown is discovered at
# scan time and disclosed in ``cross_source_frame_records``).
P4J_SOURCE_FRAMES = (
    {
        "source_frame": P4J_CONTEXTBENCH_ALL_FRAME,
        "benchmark": "contextbench",
        "language_filter": P4J_CONTEXTBENCH_ALL_LANGUAGE_FILTER,
        "window_name": "contextbench_all_languages_reservoir_scan",
        "raw_offset_requested": P4J_CONTEXTBENCH_ALL_OFFSET,
        "raw_limit_requested": P4J_CONTEXTBENCH_ALL_LIMIT,
        "config_excluded": "contextbench_default_config_not_integrated",
    },
    {
        "source_frame": P4J_REPOQA_NON_PYTHON_FRAME,
        "benchmark": "repoqa",
        "language_filter": "non_python_dynamic",
        "window_name": "repoqa_non_python_languages_reservoir_scan",
        "raw_offset_requested": 0,
        "raw_limit_requested": P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT,
        "cli_bypassed": "c5d_argparse_only_allows_python",
    },
)

# Excluded source frames (documented; not scanned).
P4J_EXCLUDED_SOURCE_FRAMES = (
    {
        "source_frame": "swe_explore",
        "exclusion_basis": "schema_row_map_only_no_repo_url_base_commit_clone_path",
    },
    {
        "source_frame": "core_bench",
        "exclusion_basis": "readiness_probe_only_no_row_to_retrieval_adapter",
    },
    {
        "source_frame": "swe_bench_original",
        "exclusion_basis": "no_adapter_in_repo",
    },
    {
        "source_frame": "contextbench_default_config",
        "exclusion_basis": "not_yet_integrated_new_dataset_integration_excluded",
    },
)

EXACT_EXCLUSION_SCOPE = "fd1_private_exact_bea4_bea5_raw_keys_where_applicable_by_construction_disjoint_for_non_python_frames"
CROSS_SOURCE_DISJOINT_BASIS = (
    "fd1_bea4_bea5_exact_keys_for_contextbench_python_rows_by_construction_"
    "disjoint_for_non_python_frames_p4h_p4i_overlap_unresolved"
)

STATUSES = (
    "cross_source_reservoir_ready_for_locked_p4_validation_design",
    "no_go_cross_source_file_miss_reservoir_insufficient",
    "no_go_cross_source_reservoir_unqualified",
    "fail_schema_contract",
    "fail_forbidden_scan",
    "unavailable_with_reason",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "cross_source_reservoir_ready_for_locked_p4_validation_design",
    "no_go_cross_source_file_miss_reservoir_insufficient",
    "no_go_cross_source_reservoir_unqualified",
})

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "records_only_public_artifact": True,
    "diagnostic_only": True,
    "denominator_source_audit_only": True,
    "cross_source_audit_only": True,
    "fd1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "p4h_artifact_read": False,
    "p4i_artifact_read": False,
    "retrieval_policy_executed": False,
    "bea_v1_p4j_audit_evaluator_no_provider_calls": True,
    "bea_v1_p4j_audit_evaluator_no_selector_executed": True,
    "bea_v1_p4j_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p4j_audit_evaluator_no_role_proxy": True,
    "bea_v1_p4j_audit_evaluator_latency_not_in_relevance": True,
    "bea_v1_p4j_audit_evaluator_no_p2_p3_p4_scheduler_arms": True,
    "bea_v1_p4j_audit_evaluator_no_retrieval_expansion": True,
    "bea_v1_p4j_audit_evaluator_no_method_winner_logic": True,
    "bea_v1_p4j_audit_evaluator_no_runtime_default_promotion": True,
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
    "algorithm_changed_during_bea_v1_p4j": False,
    "weights_tuned_during_bea_v1_p4j": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p4j": False,
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
    "frozen_p4_rerun_authorized": False,
    "locked_p4_validation_executed": False,
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
    "new_records_added_during_bea_v1_p4j": False,
}
LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_p4j_cross_source_reservoir_unlock_audit",
}

FAILURE_CATEGORIES_AUDIT = tuple(dict.fromkeys((*p4h.FAILURE_CATEGORIES_AUDIT,
    "cross_source_reservoir_insufficient",
    "exact_prior_exclusion_unavailable",
    "p4h_p4i_overlap_not_resolved",
    "cross_source_reservoir_scan_not_attempted",
    "cross_source_reservoir_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
)))
BLOCKING_FAILURE_CATEGORIES = tuple(dict.fromkeys((
    *p4.BLOCKING_FAILURE_CATEGORIES,
    "cross_source_reservoir_scan_not_attempted",
    "cross_source_reservoir_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "raw_denominator_scan_failed",
    "raw_denominator_scan_not_attempted",
    "raw_denominator_clone_failed",
    "raw_denominator_parse_failed",
    "exact_prior_exclusion_unavailable",
)))


class ReservoirRecord:
    """One private cross-source file-miss reservoir record.

    The public artifact only exposes aggregate counts.  Private row identity,
    query text, gold paths, repository location, language, and baseline
    candidate paths remain in memory or ``/tmp`` JSONL only.
    """

    def __init__(
        self, *, private_record_id: str, source_frame: str, benchmark: str,
        language: str, record_index: int, window_name: str,
        raw_window_offset: int, raw_window_limit: int,
        query_private: str = "", repo_url_private: str = "",
        base_commit_private: str = "",
        gold_paths_private: list[str] | None = None,
        baseline_result: p4.SchedulerReachResult | None = None,
    ) -> None:
        self.private_record_id = private_record_id
        self.source_phase = P4J_RAW_SOURCE_PHASE
        self.source_frame = source_frame
        self.benchmark = benchmark
        self.language = language
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
    raw = os.environ.get("OPENLOCUS_BEA_V1_P4J_PRIVATE_RESERVOIR_DIR", "")
    base = Path(raw) if raw else Path(f"/tmp/openlocus_bea_v1_p4j_reservoir_{os.getpid()}")
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private reservoir dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _initial_cross_source_scan_rows() -> list[dict[str, Any]]:
    return [{
        "source_phase": P4J_RAW_SOURCE_PHASE,
        "source_frame": str(w["source_frame"]),
        "benchmark": str(w["benchmark"]),
        "language_filter": str(w["language_filter"]),
        "denominator_window": str(w["window_name"]),
        "raw_offset_requested": int(w["raw_offset_requested"]),
        "raw_limit_requested": int(w["raw_limit_requested"]),
        "scan_protocol": "cross_source_file_miss_reservoir_unlock_quota",
        "raw_rows_fetched": 0,
        "raw_rows_attempted": 0,
        "raw_rows_prior_exact_excluded": 0,
        "raw_rows_by_construction_disjoint_records": 0,
        "raw_rows_parse_excluded": 0,
        "raw_rows_clone_excluded": 0,
        "raw_rows_baseline_reached_excluded": 0,
        "raw_rows_baseline_error_excluded": 0,
        "raw_rows_file_miss_selected": 0,
        "target_reached_in_window": False,
    } for w in P4J_SOURCE_FRAMES]


def _prior_exclusion_disclosure_records(
    *, prior_raw_keys: set[tuple[str, int]],
    exact_exclusion_records: list[dict[str, Any]],
    use_exact_prior_keys: bool,
) -> list[dict[str, Any]]:
    """Build public aggregate prior-exclusion disclosure records.

    Exact BEA-4/5 raw keys (from FD1 private decomposition) are used for
    actual exclusion **where applicable** (ContextBench Python rows mapped via
    python-ordinal).  For non-Python frames a by-construction disjoint basis is
    disclosed (BEA-4/5 only ran on the Python frame).  P4H/P4I exact selected
    keys remain private (``/tmp`` only, never committed, not in FD1), so only
    an aggregate disclosure is emitted and exact keys are NOT faked.
    """
    records: list[dict[str, Any]] = list(exact_exclusion_records)
    # P1/P2/P3/P4 aggregate disclosure (covered by BEA-4/5 exact superset).
    records.append({
        "source_phase": P4J_RAW_SOURCE_PHASE,
        "exclusion_source_phase": "BEA-v1-P1/P2/P3/P4",
        "exclusion_basis": "covered_by_fd1_bea4_bea5_exact_superset_python_frame_only",
        "excluded_record_count_aggregate": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "exact_keys_available_from_fd1": bool(use_exact_prior_keys),
        "used_for_exclusion": bool(use_exact_prior_keys),
        "private_row_ids_publicly_serialized": False,
    })
    # P4H aggregate disclosure (exact keys private/tmp only, never committed).
    records.append({
        "source_phase": P4J_RAW_SOURCE_PHASE,
        "exclusion_source_phase": "BEA-v1-P4H",
        "exclusion_basis": "p4h_exact_keys_private_tmp_only_aggregate_disclosure",
        "excluded_record_count_aggregate": P4H_DENOMINATOR_COUNT,
        "p4h_committed_denominator_count": P4H_DENOMINATOR_COUNT,
        "p4h_committed_denominator_min": P4H_DENOMINATOR_MIN,
        "exact_keys_available_from_fd1": False,
        "used_for_exclusion": False,
        "private_row_ids_publicly_serialized": False,
    })
    # P4I aggregate disclosure (exact keys private/tmp only, never committed).
    records.append({
        "source_phase": P4J_RAW_SOURCE_PHASE,
        "exclusion_source_phase": "BEA-v1-P4I",
        "exclusion_basis": "p4i_exact_keys_private_tmp_only_aggregate_disclosure",
        "excluded_record_count_aggregate": P4I_DENOMINATOR_COUNT,
        "p4i_committed_denominator_count": P4I_DENOMINATOR_COUNT,
        "p4i_committed_denominator_min": P4I_DENOMINATOR_MIN,
        "exact_keys_available_from_fd1": False,
        "used_for_exclusion": False,
        "private_row_ids_publicly_serialized": False,
    })
    # By-construction disjoint basis for non-Python frames (FD1 BEA-4/5 only
    # ran on the Python frame; non-Python rows have no prior keys).
    records.append({
        "source_phase": P4J_RAW_SOURCE_PHASE,
        "exclusion_source_phase": "cross_source_non_python_frames",
        "exclusion_basis": "by_construction_disjoint_from_fd1_bea4_bea5_python_prior",
        "excluded_record_count_aggregate": 0,
        "exact_keys_available_from_fd1": False,
        "used_for_exclusion": bool(use_exact_prior_keys),
        "private_row_ids_publicly_serialized": False,
    })
    # BEA-2/3/4 explicit public index windows (Python frame; disclosed).
    for bm in ("contextbench", "repoqa"):
        for start, end, label in p4h._raw_prior_exclusion_windows(bm):
            records.append({
                "source_phase": P4J_RAW_SOURCE_PHASE,
                "benchmark": bm,
                "exclusion_source_phase": "prior_fixed_window_python_frame",
                "exclusion_basis": label,
                "excluded_window_start_inclusive": start,
                "excluded_window_end_exclusive": end,
                "exclusion_window_publicly_disclosed": True,
                "used_for_exclusion": not use_exact_prior_keys,
                "private_row_ids_publicly_serialized": False,
            })
    return records


def _scan_contextbench_all_frame(
    *, openlocus_bin: str, prior_raw_keys: set[tuple[str, int]],
    use_exact_prior_keys: bool, srow: dict[str, Any],
    private_path: Path, fcc: dict[str, int], reservoir: list[ReservoirRecord],
) -> tuple[int, int, int, int, int, int, int, int]:
    """Scan the ContextBench "all" languages frame with the baseline arm only.

    Returns ``(fetched, attempted, prior_exact_excluded, by_construction_excluded,
    parse_excluded, clone_excluded, baseline_reached, baseline_error)``.

    Python rows are mapped to python-ordinal space for FD1 BEA-4/5 exact-key
    exclusion; non-Python rows are by-construction disjoint (no prior keys).
    """
    rows, fetch_status, _, fetch_fcc = p4.c5a._fetch_contextbench_rows(
        P4J_CONTEXTBENCH_ALL_LIMIT, P4J_CONTEXTBENCH_ALL_LANGUAGE_FILTER)
    for k, v in fetch_fcc.items():
        if k in fcc:
            fcc[k] += int(v)
    if fetch_status != "pass" or not rows:
        # Partial ContextBench fetches can result from a mid-scan network/page
        # failure.  P4J must not convert an incomplete source scan into a
        # reservoir-insufficient No-Go.
        srow["raw_rows_fetched"] = len(rows)
        fcc["cross_source_reservoir_scan_failed"] = (
            fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
        return (len(rows), 0, 0, 0, 0, 0, 0, 0)
    if len(rows) > P4J_CONTEXTBENCH_ALL_LIMIT:
        fcc["cross_source_reservoir_scan_failed"] = (
            fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
        rows = rows[:P4J_CONTEXTBENCH_ALL_LIMIT]
    srow["raw_rows_fetched"] = len(rows)
    fetched = len(rows)
    attempted = prior_exact_excluded = by_construction_excluded = 0
    parse_excluded = clone_excluded = baseline_reached = baseline_error = 0
    python_ordinal = 0  # python-ordinal in FD1 BEA-4/5 key space
    for local_idx, row in enumerate(rows):
        lang = str(row.get("language", "") or "")
        is_python = (lang == "python")
        if use_exact_prior_keys and is_python and ("contextbench", python_ordinal) in prior_raw_keys:
            srow["raw_rows_prior_exact_excluded"] += 1
            prior_exact_excluded += 1
            if is_python:
                python_ordinal += 1
            continue
        # Non-Python rows: by-construction disjoint from FD1 BEA-4/5 (python-only).
        if use_exact_prior_keys and not is_python:
            srow["raw_rows_by_construction_disjoint_records"] += 1
            by_construction_excluded += 1
        attempted += 1
        srow["raw_rows_attempted"] += 1
        query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval("contextbench", row)
        private_record_id = f"contextbench-all-{local_idx}"
        if not ok:
            srow["raw_rows_parse_excluded"] += 1
            parse_excluded += 1
            fcc["raw_denominator_parse_failed"] = (
                fcc.get("raw_denominator_parse_failed", 0) + 1)
            if is_python:
                python_ordinal += 1
            continue
        with tempfile.TemporaryDirectory(prefix=f"v1p4j_cb_all_{local_idx}_") as tmp:
            work = Path(tmp)
            clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if not clone_ok:
                srow["raw_rows_clone_excluded"] += 1
                clone_excluded += 1
                fcc["raw_denominator_clone_failed"] = (
                    fcc.get("raw_denominator_clone_failed", 0) + 1)
                if is_python:
                    python_ordinal += 1
                continue
            repo_root = work / "repo"
            rr_base = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
            rr_base.private_record_id = f"{P4J_RAW_SOURCE_PHASE}:{private_record_id}"
            if rr_base.retrieval_error:
                srow["raw_rows_baseline_error_excluded"] += 1
                baseline_error += 1
                fcc["retrieval_policy_failed"] = (
                    fcc.get("retrieval_policy_failed", 0) + 1)
                if is_python:
                    python_ordinal += 1
                continue
            p4._append_private_jsonl(private_path, {
                "schema_version": "bea_v1_p4j_private_reservoir_scan.v1",
                "source_phase": P4J_RAW_SOURCE_PHASE,
                "source_frame": P4J_CONTEXTBENCH_ALL_FRAME,
                "benchmark": "contextbench",
                "language": lang,
                "window_name": srow["denominator_window"],
                "raw_record_index_private": local_idx,
                "python_ordinal_private": python_ordinal if is_python else None,
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
                baseline_reached += 1
                if is_python:
                    python_ordinal += 1
                continue
            srow["raw_rows_file_miss_selected"] += 1
            reservoir.append(ReservoirRecord(
                private_record_id=private_record_id,
                source_frame=P4J_CONTEXTBENCH_ALL_FRAME,
                benchmark="contextbench",
                language=lang,
                record_index=local_idx,
                window_name=srow["denominator_window"],
                raw_window_offset=P4J_CONTEXTBENCH_ALL_OFFSET,
                raw_window_limit=P4J_CONTEXTBENCH_ALL_LIMIT,
                query_private=query,
                repo_url_private=repo_url,
                base_commit_private=base_commit,
                gold_paths_private=gold_paths,
                baseline_result=rr_base,
            ))
        if is_python:
            python_ordinal += 1
    return (fetched, attempted, prior_exact_excluded, by_construction_excluded,
            parse_excluded, clone_excluded, baseline_reached, baseline_error)


def _scan_repoqa_non_python_frame(
    *, openlocus_bin: str, parsed_asset: Any,
    srow: dict[str, Any], private_path: Path, fcc: dict[str, int],
    reservoir: list[ReservoirRecord],
) -> tuple[list[dict[str, Any]], int, int, int, int, int, int, int]:
    """Scan RepoQA non-Python asset languages with the baseline arm only.

    Returns ``(per_language_records, fetched, attempted, by_construction_excluded,
    parse_excluded, clone_excluded, baseline_reached, baseline_error)``.

    The c5d CLI is bypassed (argparse only allows Python).  All non-Python
    needles are by-construction disjoint from FD1 BEA-4/5 (Python-only).
    """
    per_language_records: list[dict[str, Any]] = []
    if not isinstance(parsed_asset, dict):
        fcc["cross_source_reservoir_scan_failed"] = (
            fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
        return (per_language_records, 0, 0, 0, 0, 0, 0, 0)
    non_python_langs = sorted(
        str(k) for k in parsed_asset
        if k != "python" and isinstance(parsed_asset.get(k), list))
    fetched = attempted = by_construction_excluded = 0
    parse_excluded = clone_excluded = baseline_reached = baseline_error = 0
    for lang in non_python_langs:
        needles, needle_status, needle_fcc = p4.c5d._parse_repoqa_needles(
            parsed_asset, lang, P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT)
        for k, v in needle_fcc.items():
            if k in fcc:
                fcc[k] += int(v)
        if needle_status not in ("pass",) or not needles:
            # Empty/missing non-Python language buckets are source absence, but
            # parser/schema failures must be fail-closed rather than counted as
            # a genuine file-miss reservoir shortfall.
            parse_failures = int(needle_fcc.get("asset_parse_failed", 0) or 0) + int(needle_fcc.get("needle_parse_failed", 0) or 0)
            if parse_failures > 0:
                fcc["raw_denominator_parse_failed"] = (
                    fcc.get("raw_denominator_parse_failed", 0) + parse_failures)
                fcc["cross_source_reservoir_scan_failed"] = (
                    fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
            continue
        lang_fetched = len(needles)
        lang_attempted = lang_by_construction = 0
        lang_parse_excluded = lang_clone_excluded = 0
        lang_baseline_reached = lang_baseline_error = 0
        lang_file_miss = 0
        fetched += lang_fetched
        srow["raw_rows_fetched"] += lang_fetched
        for local_idx, needle in enumerate(needles):
            # Non-Python needles: by-construction disjoint from FD1 BEA-4/5.
            srow["raw_rows_by_construction_disjoint_records"] += 1
            by_construction_excluded += 1
            lang_by_construction += 1
            attempted += 1
            srow["raw_rows_attempted"] += 1
            lang_attempted += 1
            query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval("repoqa", needle)
            private_record_id = f"repoqa-{lang}-{local_idx}"
            if not ok:
                srow["raw_rows_parse_excluded"] += 1
                parse_excluded += 1
                lang_parse_excluded += 1
                fcc["raw_denominator_parse_failed"] = (
                    fcc.get("raw_denominator_parse_failed", 0) + 1)
                continue
            with tempfile.TemporaryDirectory(prefix=f"v1p4j_rq_{lang}_{local_idx}_") as tmp:
                work = Path(tmp)
                clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += int(v)
                if not clone_ok:
                    srow["raw_rows_clone_excluded"] += 1
                    clone_excluded += 1
                    lang_clone_excluded += 1
                    fcc["raw_denominator_clone_failed"] = (
                        fcc.get("raw_denominator_clone_failed", 0) + 1)
                    continue
                repo_root = work / "repo"
                rr_base = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
                rr_base.private_record_id = f"{P4J_RAW_SOURCE_PHASE}:{private_record_id}"
                if rr_base.retrieval_error:
                    srow["raw_rows_baseline_error_excluded"] += 1
                    baseline_error += 1
                    lang_baseline_error += 1
                    fcc["retrieval_policy_failed"] = (
                        fcc.get("retrieval_policy_failed", 0) + 1)
                    continue
                p4._append_private_jsonl(private_path, {
                    "schema_version": "bea_v1_p4j_private_reservoir_scan.v1",
                    "source_phase": P4J_RAW_SOURCE_PHASE,
                    "source_frame": P4J_REPOQA_NON_PYTHON_FRAME,
                    "benchmark": "repoqa",
                    "language": lang,
                    "window_name": srow["denominator_window"],
                    "raw_record_index_private": local_idx,
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
                    baseline_reached += 1
                    lang_baseline_reached += 1
                    continue
                srow["raw_rows_file_miss_selected"] += 1
                lang_file_miss += 1
                reservoir.append(ReservoirRecord(
                    private_record_id=private_record_id,
                    source_frame=P4J_REPOQA_NON_PYTHON_FRAME,
                    benchmark="repoqa",
                    language=lang,
                    record_index=local_idx,
                    window_name=srow["denominator_window"],
                    raw_window_offset=0,
                    raw_window_limit=P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT,
                    query_private=query,
                    repo_url_private=repo_url,
                    base_commit_private=base_commit,
                    gold_paths_private=gold_paths,
                    baseline_result=rr_base,
                ))
        per_language_records.append({
            "source_frame": P4J_REPOQA_NON_PYTHON_FRAME,
            "language": lang,
            "raw_rows_fetched": lang_fetched,
            "raw_rows_attempted": lang_attempted,
            "raw_rows_by_construction_disjoint_records": lang_by_construction,
            "raw_rows_parse_excluded": lang_parse_excluded,
            "raw_rows_clone_excluded": lang_clone_excluded,
            "raw_rows_baseline_reached_excluded": lang_baseline_reached,
            "raw_rows_baseline_error_excluded": lang_baseline_error,
            "raw_rows_file_miss_selected": lang_file_miss,
        })
    return (per_language_records, fetched, attempted, by_construction_excluded,
            parse_excluded, clone_excluded, baseline_reached, baseline_error)


def _sanitize_exception_category(exc: BaseException) -> str:
    """Return a safe public exception category with no message/path values."""
    if isinstance(exc, json.JSONDecodeError):
        return "json_decode_error"
    if isinstance(exc, (OSError, IOError)):
        return "os_error"
    if isinstance(exc, subprocess.SubprocessError):
        return "subprocess_error"
    if isinstance(exc, TimeoutError):
        return "timeout_error"
    if isinstance(exc, (TypeError, ValueError, KeyError, IndexError)):
        return type(exc).__name__.lower()
    return "unexpected_exception_type"


def _scan_exception_record(phase: str, exc: BaseException) -> dict[str, Any]:
    return {
        "scan_phase": str(phase),
        "exception_category": _sanitize_exception_category(exc),
        "private_exception_message_publicly_serialized": False,
        "private_path_publicly_serialized": False,
    }


def _scan_cross_source_reservoir(
    *, openlocus_bin: str, pt: p4.bea_v1_p1.ParsedPrivateDecomposition | None,
) -> tuple[list[ReservoirRecord], dict[str, int], dict[str, Any], dict[str, Any]]:
    """Scan cross-source frames with the baseline diagnostic arm only.

    P2/P3/P4 treatment arms are NOT run.  The scan does not stop at an 80-record
    target; it counts the full cumulative cross-source file-miss reservoir.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    reservoir: list[ReservoirRecord] = []
    scan_rows = _initial_cross_source_scan_rows()
    row_by_frame = {r["source_frame"]: r for r in scan_rows}
    private_dir = _resolve_private_reservoir_dir()
    private_path = private_dir / "bea_v1_p4j.private_reservoir_scan.jsonl"
    if private_path.exists():
        private_path.unlink()
    prior_raw_keys, exact_exclusion_records = p4h._prior_raw_keys_from_fd1_private(pt)
    use_exact_prior_keys = bool(prior_raw_keys)
    fetched_total = attempted_total = prior_exact_total = 0
    by_construction_total = parse_total = clone_total = 0
    baseline_reached_total = baseline_error_total = 0
    per_language_records: list[dict[str, Any]] = []
    scan_diagnostic_records: list[dict[str, Any]] = []

    # --- Frame 1: ContextBench "all" languages ---
    cb_row = row_by_frame[P4J_CONTEXTBENCH_ALL_FRAME]
    try:
        (cb_fetched, cb_attempted, cb_prior, cb_bcd, cb_parse, cb_clone,
         cb_reached, cb_error) = _scan_contextbench_all_frame(
            openlocus_bin=openlocus_bin, prior_raw_keys=prior_raw_keys,
            use_exact_prior_keys=use_exact_prior_keys, srow=cb_row,
            private_path=private_path, fcc=fcc, reservoir=reservoir)
        fetched_total += cb_fetched
        attempted_total += cb_attempted
        prior_exact_total += cb_prior
        by_construction_total += cb_bcd
        parse_total += cb_parse
        clone_total += cb_clone
        baseline_reached_total += cb_reached
        baseline_error_total += cb_error
    except Exception as exc:
        # Fail closed, but keep aggregate scan state for diagnosis.  No private
        # exception message, path, row id, query, repo, or gold value is exposed.
        fcc["cross_source_reservoir_scan_failed"] = (
            fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
        fcc["unexpected_exception"] = fcc.get("unexpected_exception", 0) + 1
        scan_diagnostic_records.append(
            _scan_exception_record("contextbench_all_languages_frame", exc))
        fetched_total += int(cb_row.get("raw_rows_fetched", 0) or 0)
        attempted_total += int(cb_row.get("raw_rows_attempted", 0) or 0)
        prior_exact_total += int(cb_row.get("raw_rows_prior_exact_excluded", 0) or 0)
        by_construction_total += int(cb_row.get("raw_rows_by_construction_disjoint_records", 0) or 0)
        parse_total += int(cb_row.get("raw_rows_parse_excluded", 0) or 0)
        clone_total += int(cb_row.get("raw_rows_clone_excluded", 0) or 0)
        baseline_reached_total += int(cb_row.get("raw_rows_baseline_reached_excluded", 0) or 0)
        baseline_error_total += int(cb_row.get("raw_rows_baseline_error_excluded", 0) or 0)

    # --- Frame 2: RepoQA non-Python asset languages ---
    rq_row = row_by_frame[P4J_REPOQA_NON_PYTHON_FRAME]
    try:
        asset_bytes, dl_status, dl_fcc = p4.c5d._download_asset_to_bytes(p4.c5d.ASSET_URL)
        for k, v in dl_fcc.items():
            if k in fcc:
                fcc[k] += int(v)
        if dl_status != "pass" or not asset_bytes:
            fcc["cross_source_asset_download_failed"] = (
                fcc.get("cross_source_asset_download_failed", 0) + 1)
            fcc["cross_source_reservoir_scan_failed"] = (
                fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
        else:
            parsed_asset, parse_status, parse_fcc = p4.c5d._decompress_asset(asset_bytes)
            del asset_bytes
            for k, v in parse_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if parse_status != "pass" or parsed_asset is None:
                fcc["cross_source_asset_decompress_failed"] = (
                    fcc.get("cross_source_asset_decompress_failed", 0) + 1)
                fcc["cross_source_reservoir_scan_failed"] = (
                    fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
            else:
                (rq_per_lang, rq_fetched, rq_attempted, rq_bcd, rq_parse,
                 rq_clone, rq_reached, rq_error) = _scan_repoqa_non_python_frame(
                    openlocus_bin=openlocus_bin, parsed_asset=parsed_asset,
                    srow=rq_row, private_path=private_path, fcc=fcc, reservoir=reservoir)
                per_language_records = rq_per_lang
                fetched_total += rq_fetched
                attempted_total += rq_attempted
                by_construction_total += rq_bcd
                parse_total += rq_parse
                clone_total += rq_clone
                baseline_reached_total += rq_reached
                baseline_error_total += rq_error
    except Exception as exc:
        fcc["cross_source_reservoir_scan_failed"] = (
            fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
        fcc["unexpected_exception"] = fcc.get("unexpected_exception", 0) + 1
        scan_diagnostic_records.append(
            _scan_exception_record("repoqa_non_python_languages_frame", exc))
        fetched_total += int(rq_row.get("raw_rows_fetched", 0) or 0)
        attempted_total += int(rq_row.get("raw_rows_attempted", 0) or 0)
        by_construction_total += int(rq_row.get("raw_rows_by_construction_disjoint_records", 0) or 0)
        parse_total += int(rq_row.get("raw_rows_parse_excluded", 0) or 0)
        clone_total += int(rq_row.get("raw_rows_clone_excluded", 0) or 0)
        baseline_reached_total += int(rq_row.get("raw_rows_baseline_reached_excluded", 0) or 0)
        baseline_error_total += int(rq_row.get("raw_rows_baseline_error_excluded", 0) or 0)

    for r in scan_rows:
        r["target_reached_in_window"] = len(reservoir) >= P4J_RESERVOIR_MIN_COUNT

    non_python_reservoir_count = sum(
        1 for d in reservoir if d.language != "python")
    python_reservoir_count = sum(
        1 for d in reservoir if d.language == "python")

    disclosure_records = _prior_exclusion_disclosure_records(
        prior_raw_keys=prior_raw_keys,
        exact_exclusion_records=exact_exclusion_records,
        use_exact_prior_keys=use_exact_prior_keys,
    )
    meta = {
        "denominator_source_protocol": "cross_source_file_miss_reservoir_unlock_audit_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "reservoir_count": len(reservoir),
        "reservoir_upper_bound_count": len(reservoir),
        "qualified_cross_source_reservoir_count": 0,
        "cross_source_non_python_reservoir_count": int(non_python_reservoir_count),
        "cross_source_python_reservoir_count": int(python_reservoir_count),
        "cross_source_reservoir_scan_attempted": True,
        "raw_scan_fetched_records": int(fetched_total),
        "raw_scan_attempted_records": int(attempted_total),
        "raw_scan_prior_exact_excluded_records": int(prior_exact_total),
        "raw_scan_by_construction_disjoint_records": int(by_construction_total),
        "raw_scan_yield_file_miss_records": int(len(reservoir)),
        "raw_scan_baseline_reached_records": int(baseline_reached_total),
        "raw_scan_baseline_error_records": int(baseline_error_total),
        "reservoir_min_count": P4J_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": bool(use_exact_prior_keys),
        "cross_source_disjoint_basis": CROSS_SOURCE_DISJOINT_BASIS,
        "p4h_exact_keys_available_for_exclusion": False,
        "p4i_exact_keys_available_for_exclusion": False,
        "p4h_p4i_overlap_resolved": False,
        "reservoir_upper_bound_includes_possible_p4h_p4i_overlap": True,
        "prior_fd1_denominator_reused": False,
        "by_construction_disjoint_non_python_frames": True,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": scan_rows,
        "cross_source_frame_records": per_language_records,
        "prior_raw_exclusion_records": disclosure_records,
        "scan_diagnostic_records": scan_diagnostic_records,
    }
    try:
        manifest = p4._private_file_manifest(
            private_path,
            manifest_name="bea_v1_p4j_private_reservoir_scan_manifest",
            schema_version="bea_v1_p4j_private_reservoir_scan.v1")
    except Exception as exc:
        fcc["cross_source_reservoir_scan_failed"] = (
            fcc.get("cross_source_reservoir_scan_failed", 0) + 1)
        fcc["unexpected_exception"] = fcc.get("unexpected_exception", 0) + 1
        scan_diagnostic_records.append(
            _scan_exception_record("private_reservoir_manifest", exc))
        manifest = {
            "manifest_name": "bea_v1_p4j_private_reservoir_scan_manifest",
            "schema_version": "bea_v1_p4j_private_reservoir_scan.v1",
            "storage_class": "private_tmp_only",
            "record_count": 0,
            "records_written": False,
            "path_publicly_serialized": False,
            "manifest_hash": "",
        }
    return reservoir, fcc, meta, manifest


def _denominator_reservoir_records(reservoir: list[Any]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str, str], int] = {}
    for d in reservoir:
        key = (str(getattr(d, "source_phase", P4J_RAW_SOURCE_PHASE)),
               str(getattr(d, "source_frame", "")),
               str(getattr(d, "window_name", "cross_source_reservoir_scan")))
        counts[key] = counts.get(key, 0) + 1
    return [{
        "source_phase": sp,
        "source_frame": sf,
        "denominator_window": window,
        "reservoir_record_count": int(cnt),
    } for (sp, sf, window), cnt in sorted(counts.items())]


def _denominator_scan_records(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("denominator_scan_records", [])
    return list(rows) if isinstance(rows, list) else []


def _cross_source_frame_records(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("cross_source_frame_records", [])
    return list(rows) if isinstance(rows, list) else []


def _prior_raw_exclusion_records(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("prior_raw_exclusion_records", [])
    return list(rows) if isinstance(rows, list) else []


def _subgroup_reservoir_records(reservoir: list[Any]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for d in reservoir:
        key = (str(getattr(d, "source_frame", "")),
               str(getattr(d, "language", "")))
        counts[key] = counts.get(key, 0) + 1
    return [{
        "source_frame": sf,
        "language": lang,
        "subgroup_reservoir_count": int(cnt),
    } for (sf, lang), cnt in sorted(counts.items())]


def _excluded_source_frame_records() -> list[dict[str, Any]]:
    return [{
        "source_frame": str(w["source_frame"]),
        "exclusion_basis": str(w["exclusion_basis"]),
    } for w in P4J_EXCLUDED_SOURCE_FRAMES]


def _source_run_records(
    *, fd1_schema_version: str, fd1_source_artifact_hash: str,
    fd1_status: str, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    pt: p4.bea_v1_p1.ParsedPrivateDecomposition | None,
    rav: p4.bea_v1_p1.Fd1ReplayArtifactValidation | None,
    p4h_artifact: dict[str, Any] | None, p4h_status: str,
    p4h_denominator_count: int,
    p4i_artifact: dict[str, Any] | None, p4i_status: str,
    p4i_denominator_count: int,
    audit_match: bool, audit_mismatch_reason: str,
) -> list[dict[str, Any]]:
    p4h_art = p4h_artifact or {}
    p4i_art = p4i_artifact or {}
    return [{
        "source_phase": "BEA-v1-P4I",
        "source_checkpoint": P4I_RESULT_CHECKPOINT,
        "source_status": p4i_status,
        "source_ci_run_id": P4I_CI_RUN_ID,
        "source_denominator_count": int(p4i_denominator_count),
        "source_denominator_min": P4I_DENOMINATOR_MIN,
        "audit_objective": "determine_whether_cross_source_frames_unlock_file_miss_reservoir_denominator",
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": "cross_source_file_miss_reservoir_unlock_audit_scan.v1",
        "prior_fd1_denominator_reused": False,
        "contextbench_all_language_filter": P4J_CONTEXTBENCH_ALL_LANGUAGE_FILTER,
        "contextbench_all_offset_requested": P4J_CONTEXTBENCH_ALL_OFFSET,
        "contextbench_all_limit_requested": P4J_CONTEXTBENCH_ALL_LIMIT,
        "repoqa_non_python_per_lang_limit": P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT,
        "repoqa_cli_bypassed": True,
        "reservoir_min_count": P4J_RESERVOIR_MIN_COUNT,
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
        "p4h_committed_denominator_count": int(p4h_art.get("denominator_count", P4H_DENOMINATOR_COUNT) or 0),
        "p4h_committed_denominator_min": int(p4h_art.get("stop_go_records", [{}])[0].get("denominator_min", P4H_DENOMINATOR_MIN) if p4h_art.get("stop_go_records") else P4H_DENOMINATOR_MIN),
        "p4i_artifact_read": bool(p4i_art),
        "p4i_committed_status": str(p4i_art.get("status", "") or ""),
        "p4i_committed_denominator_count": int(p4i_art.get("denominator_count", P4I_DENOMINATOR_COUNT) or 0),
        "p4i_committed_denominator_min": P4I_DENOMINATOR_MIN,
        "p4h_result_checkpoint": P4H_RESULT_CHECKPOINT,
        "p4h_result_status": P4H_RESULT_STATUS,
        "v1_p4_result_checkpoint": V1_P4_RESULT_CHECKPOINT,
        "v1_p4_result_status": V1_P4_RESULT_STATUS,
        "config_hash": p4._config_hash(),
    }]


def _stop_go_records(
    *, reservoir_count: int, raw_scan_attempted: bool,
    blocking_failure_count: int, exact_prior_exclusion_used: bool,
    p4h_p4i_overlap_resolved: bool,
) -> list[dict[str, Any]]:
    if not exact_prior_exclusion_used:
        decision = "fail_schema_contract"
        reason = "fd1_exact_bea4_bea5_prior_exclusion_required"
    elif blocking_failure_count > 0:
        decision = "fail_schema_contract"
        reason = "blocking_failure_present_cannot_be_cross_source_insufficient"
    elif not raw_scan_attempted:
        decision = "fail_schema_contract"
        reason = "cross_source_reservoir_scan_not_attempted"
    elif reservoir_count < P4J_RESERVOIR_MIN_COUNT:
        decision = "no_go_cross_source_file_miss_reservoir_insufficient"
        reason = f"cross_source_reservoir_upper_bound_count={reservoir_count}; min={P4J_RESERVOIR_MIN_COUNT}"
    elif not p4h_p4i_overlap_resolved:
        decision = "no_go_cross_source_reservoir_unqualified"
        reason = "reservoir_reaches_min_but_p4h_p4i_overlap_unresolved"
    else:
        decision = "cross_source_reservoir_ready_for_locked_p4_validation_design"
        reason = "qualified_cross_source_disjoint_reservoir_reaches_min_with_overlap_resolved"
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "denominator_record_count": int(reservoir_count),
        "denominator_min": int(P4J_RESERVOIR_MIN_COUNT),
        "cumulative_cross_source_reservoir_count": int(reservoir_count),
        "reservoir_upper_bound_count": int(reservoir_count),
        "qualified_cross_source_reservoir_count": int(reservoir_count if p4h_p4i_overlap_resolved else 0),
        "p4h_p4i_overlap_resolved": bool(p4h_p4i_overlap_resolved),
        "cross_source_reservoir_scan_attempted": bool(raw_scan_attempted),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "cross_source_reservoir_unlock_authorized": bool(decision == "cross_source_reservoir_ready_for_locked_p4_validation_design"),
        "locked_p4_validation_design_authorized": bool(decision == "cross_source_reservoir_ready_for_locked_p4_validation_design"),
        "locked_p4_validation_executed": False,
        "frozen_p4_rerun_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "method_winner_authorized": False,
        "broad_retrieval_expansion_authorized": False,
        "scheduler_validation_authorized": False,
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
        g("cross_source_reservoir_scan_attempted", 1.0 if denominator_meta.get("cross_source_reservoir_scan_attempted", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("cross_source_reservoir_scan_attempted", False))),
        g("cross_source_attempted_records", denominator_meta.get("raw_scan_attempted_records", 0), ">=", 0.0, denominator_meta.get("raw_scan_attempted_records", 0) >= 0),
        g("exact_prior_exclusion_used", 1.0 if exact_prior_exclusion_used else 0.0, "boolean", 1.0, bool(exact_prior_exclusion_used)),
        g("by_construction_disjoint_non_python_frames", 1.0 if denominator_meta.get("by_construction_disjoint_non_python_frames", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("by_construction_disjoint_non_python_frames", False))),
        g("p4h_p4i_overlap_resolved", 1.0 if denominator_meta.get("p4h_p4i_overlap_resolved", False) else 0.0, "boolean", 1.0, bool(denominator_meta.get("p4h_p4i_overlap_resolved", False))),
        g("reservoir_count_min", reservoir_count, ">=", P4J_RESERVOIR_MIN_COUNT, reservoir_count >= P4J_RESERVOIR_MIN_COUNT),
        g("denominator_constructed_before_scheduler_outcomes", 1.0 if denominator_meta.get("denominator_constructed_before_scheduler_outcomes", True) else 0.0, "boolean", 1.0, bool(denominator_meta.get("denominator_constructed_before_scheduler_outcomes", True))),
        g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0, "boolean", 1.0, forbidden_scan_pass),
        g("provider_calls_made", 0.0, "boolean_false", 0.0, True),
        g("latency_in_candidate_relevance", 0.0, "boolean_false", 0.0, True),
        g("p2_p3_p4_scheduler_arms_executed", 0.0, "boolean_false", 0.0, True),
        g("selector_or_reranker_executed", 0.0, "boolean_false", 0.0, True),
        g("retrieval_policy_executed", 0.0, "boolean_false", 0.0, True),
        g("method_winner_logic_executed", 0.0, "boolean_false", 0.0, True),
        g("runtime_default_promotion_executed", 0.0, "boolean_false", 0.0, True),
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
    "p4h_private_denominator_scan_path", "p4i_private_denominator_scan_path",
    "p4h_exact_raw_keys", "p4i_exact_raw_keys",
    "prior_exact_raw_keys", "exact_raw_keys",
    "repo_url_private", "base_commit_private", "gold_paths_private",
    "candidate_paths_private", "query_private",
    "repoqa_non_python_languages_private",
})


def _scan_v1_p4j(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sub = f"{path}.{ks}"
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_v1_p4j_public_key", "path": sub})
                if isinstance(v, str) and len(v) > 240 and ks not in {"stop_go_reason", "audit_objective", "cross_source_disjoint_basis", "exact_prior_exclusion_scope"}:
                    violations.append({"category": "long_string", "path": sub})
                walk(v, sub)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(obj)
    return violations


def _v1_p4j_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p4j(obj)
    cats: dict[str, int] = {}
    for v in violations:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    violation_categories = [{"category": c, "count": int(n)} for c, n in sorted(cats.items())]
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": violation_categories,
    }


def _enforce_v1_p4j_no_forbidden(obj: Any) -> None:
    if _v1_p4j_forbidden_scan_summary(obj)["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


def _base_report(
    *, status: str, failure_reason_category: str, self_test_passed: bool,
    self_test_checks_total: int, self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any] | None = None,
    fd1_schema: str = "", fd1_hash: str = "", pt: Any = None,
    rav: Any = None, p4h_artifact: dict[str, Any] | None = None,
    p4h_status: str = "", p4h_denominator_count: int = P4H_DENOMINATOR_COUNT,
    p4i_artifact: dict[str, Any] | None = None, p4i_status: str = "",
    p4i_denominator_count: int = P4I_DENOMINATOR_COUNT,
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
        "denominator_source_protocol": "cross_source_file_miss_reservoir_unlock_audit_scan.v1",
        "cross_source_reservoir_scan_attempted": False,
        "raw_scan_attempted_records": 0,
        "raw_scan_fetched_records": 0,
        "raw_scan_prior_exact_excluded_records": 0,
        "raw_scan_by_construction_disjoint_records": 0,
        "raw_scan_yield_file_miss_records": len(reservoir),
        "raw_scan_baseline_reached_records": 0,
        "raw_scan_baseline_error_records": 0,
        "reservoir_min_count": P4J_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": False,
        "cross_source_disjoint_basis": CROSS_SOURCE_DISJOINT_BASIS,
        "p4h_exact_keys_available_for_exclusion": False,
        "p4i_exact_keys_available_for_exclusion": False,
        "p4h_p4i_overlap_resolved": False,
        "reservoir_upper_bound_includes_possible_p4h_p4i_overlap": False,
        "reservoir_upper_bound_count": len(reservoir),
        "qualified_cross_source_reservoir_count": 0,
        "cross_source_non_python_reservoir_count": 0,
        "cross_source_python_reservoir_count": 0,
        "prior_fd1_denominator_reused": False,
        "by_construction_disjoint_non_python_frames": True,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": _initial_cross_source_scan_rows(),
        "cross_source_frame_records": [],
        "prior_raw_exclusion_records": [],
        "scan_diagnostic_records": [],
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
        raw_scan_attempted=bool(reservoir_meta.get("cross_source_reservoir_scan_attempted", False)),
        blocking_failure_count=blocking,
        exact_prior_exclusion_used=exact_prior_exclusion_used,
        p4h_p4i_overlap_resolved=bool(reservoir_meta.get("p4h_p4i_overlap_resolved", False)),
    )
    if status == "unavailable_with_reason":
        stop_go = [{
            **stop_go[0],
            "stop_go_decision": "unavailable_with_reason",
            "stop_go_reason": failure_reason_category or "network_required_but_disabled",
            "cross_source_reservoir_unlock_authorized": False,
            "locked_p4_validation_design_authorized": False,
            "locked_p4_validation_executed": False,
            "frozen_p4_rerun_authorized": False,
            "p5_authorized": False,
            "v1_a_authorized": False,
            "runtime_promotion_authorized": False,
            "method_winner_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "scheduler_validation_authorized": False,
        }]
    if status == "auto":
        if blocking > 0:
            status = "fail_schema_contract"
        elif stop_go[0]["stop_go_decision"] in STATUSES:
            status = stop_go[0]["stop_go_decision"]
        else:
            status = "no_go_cross_source_file_miss_reservoir_insufficient"
    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true.update({
        "fd1_artifact_read": bool(fd1_artifact),
        "fd1_private_decomposition_parsed": fd1_private_parsed,
        "fd1_private_decomposition_replay_supplied": bool(rav.supplied if rav else False),
        "fd1_private_decomposition_replay_validated": replay_validated,
        "fd1_private_decomposition_replay_executed_by_workflow": bool(rav.supplied and rav.validated) if rav else False,
        "p4h_artifact_read": bool(p4h_artifact),
        "p4i_artifact_read": bool(p4i_artifact),
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
        "denominator_source_protocol": str(reservoir_meta.get("denominator_source_protocol", "cross_source_file_miss_reservoir_unlock_audit_scan.v1")),
        "records_decomposed": int(fd1_records),
        "private_manifest_record_count": int(fd1_manifest_count),
        "denominator_count": int(len(reservoir)),
        "cumulative_cross_source_reservoir_count": int(len(reservoir)),
        "reservoir_upper_bound_count": int(reservoir_meta.get("reservoir_upper_bound_count", len(reservoir))),
        "qualified_cross_source_reservoir_count": int(reservoir_meta.get("qualified_cross_source_reservoir_count", len(reservoir) if reservoir_meta.get("p4h_p4i_overlap_resolved", False) else 0)),
        "cross_source_non_python_reservoir_count": int(reservoir_meta.get("cross_source_non_python_reservoir_count", 0)),
        "cross_source_python_reservoir_count": int(reservoir_meta.get("cross_source_python_reservoir_count", 0)),
        "failure_reason_category": failure_reason_category,
        "source_run_records": _source_run_records(fd1_schema_version=fd1_schema, fd1_source_artifact_hash=fd1_hash, fd1_status=fd1_status, fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4h_status=p4h_status, p4h_denominator_count=p4h_denominator_count, p4i_artifact=p4i_artifact, p4i_status=p4i_status, p4i_denominator_count=p4i_denominator_count, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason),
        "denominator_reservoir_records": _denominator_reservoir_records(reservoir),
        "denominator_scan_records": _denominator_scan_records(reservoir_meta),
        "cross_source_frame_records": _cross_source_frame_records(reservoir_meta),
        "excluded_source_frame_records": _excluded_source_frame_records(),
        "prior_raw_exclusion_records": _prior_raw_exclusion_records(reservoir_meta),
        "scan_diagnostic_records": list(reservoir_meta.get("scan_diagnostic_records", []) or []),
        "subgroup_reservoir_records": _subgroup_reservoir_records(reservoir),
        "stop_go_records": stop_go,
        "gate_records": _gate_records(fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, denominator_meta=reservoir_meta, reservoir_count=len(reservoir), fd1_private_decomposition_parsed=fd1_private_parsed, replay_artifact_validated=replay_validated, forbidden_scan_pass=True, blocking_failure_count=blocking, exact_prior_exclusion_used=exact_prior_exclusion_used),
        "private_manifest_records": _private_manifest_records(fd1_artifact, extra_manifests),
        "failure_category_count_records": _failure_category_count_records(fcc),
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "cross_source_reservoir_scan_attempted": bool(reservoir_meta.get("cross_source_reservoir_scan_attempted", False)),
        "raw_scan_fetched_records": int(reservoir_meta.get("raw_scan_fetched_records", 0)),
        "raw_scan_attempted_records": int(reservoir_meta.get("raw_scan_attempted_records", 0)),
        "raw_scan_prior_exact_excluded_records": int(reservoir_meta.get("raw_scan_prior_exact_excluded_records", 0)),
        "raw_scan_by_construction_disjoint_records": int(reservoir_meta.get("raw_scan_by_construction_disjoint_records", 0)),
        "raw_scan_yield_file_miss_records": int(reservoir_meta.get("raw_scan_yield_file_miss_records", 0)),
        "raw_scan_baseline_reached_records": int(reservoir_meta.get("raw_scan_baseline_reached_records", 0)),
        "raw_scan_baseline_error_records": int(reservoir_meta.get("raw_scan_baseline_error_records", 0)),
        "exact_prior_exclusion_scope": str(reservoir_meta.get("exact_prior_exclusion_scope", EXACT_EXCLUSION_SCOPE)),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "cross_source_disjoint_basis": str(reservoir_meta.get("cross_source_disjoint_basis", CROSS_SOURCE_DISJOINT_BASIS)),
        "p4h_exact_keys_available_for_exclusion": bool(reservoir_meta.get("p4h_exact_keys_available_for_exclusion", False)),
        "p4i_exact_keys_available_for_exclusion": bool(reservoir_meta.get("p4i_exact_keys_available_for_exclusion", False)),
        "p4h_p4i_overlap_resolved": bool(reservoir_meta.get("p4h_p4i_overlap_resolved", False)),
        "reservoir_upper_bound_includes_possible_p4h_p4i_overlap": bool(reservoir_meta.get("reservoir_upper_bound_includes_possible_p4h_p4i_overlap", False)),
        "prior_fd1_denominator_reused": False,
        "by_construction_disjoint_non_python_frames": bool(reservoir_meta.get("by_construction_disjoint_non_python_frames", True)),
        "denominator_source_gold_file_absent_count": int(reservoir_meta.get("source_gold_file_absent_count", 0)),
        "excluded_prior_windows_count": int(reservoir_meta.get("excluded_prior_window_count", 0)),
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": bool(reservoir_meta.get("denominator_constructed_before_scheduler_outcomes", True)),
        "reservoir_min_count": P4J_RESERVOIR_MIN_COUNT,
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
            "is_cross_source_reservoir_unlock_audit": True,
            "is_latency_in_relevance": False,
            "signal_strength": "bea_v1_p4j_cross_source_reservoir_unlock_audit_aggregate_only",
            "locked_p4_validation_design_authorization_scope": "stop_go_records_only",
        },
    }
    scan = _v1_p4j_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
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
    p4i_artifact_path: Path | None, enable_network: bool,
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
    # P4I committed artifact (motivation context + aggregate disclosure).
    p4i_artifact: dict[str, Any] = {}
    p4i_status_str = ""
    p4i_denom_count = P4I_DENOMINATOR_COUNT
    if p4i_artifact_path is not None:
        try:
            p4i_artifact, _, _, p4i_load_status = p4._load_committed_artifact(p4i_artifact_path)
            if p4i_load_status == "pass":
                p4i_status_str = str(p4i_artifact.get("status", "") or "")
                p4i_denom_count = int(p4i_artifact.get("denominator_count", P4I_DENOMINATOR_COUNT) or 0)
            else:
                p4i_artifact = {}
        except Exception:
            p4i_artifact = {}
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
        "denominator_source_protocol": "cross_source_file_miss_reservoir_unlock_audit_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "reservoir_count": 0,
        "cross_source_reservoir_scan_attempted": False,
        "raw_scan_fetched_records": 0,
        "raw_scan_attempted_records": 0,
        "raw_scan_prior_exact_excluded_records": 0,
        "raw_scan_by_construction_disjoint_records": 0,
        "raw_scan_yield_file_miss_records": 0,
        "raw_scan_baseline_reached_records": 0,
        "raw_scan_baseline_error_records": 0,
        "reservoir_min_count": P4J_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": False,
        "cross_source_disjoint_basis": CROSS_SOURCE_DISJOINT_BASIS,
        "p4h_exact_keys_available_for_exclusion": False,
        "p4i_exact_keys_available_for_exclusion": False,
        "p4h_p4i_overlap_resolved": False,
        "reservoir_upper_bound_includes_possible_p4h_p4i_overlap": False,
        "reservoir_upper_bound_count": 0,
        "qualified_cross_source_reservoir_count": 0,
        "cross_source_non_python_reservoir_count": 0,
        "cross_source_python_reservoir_count": 0,
        "prior_fd1_denominator_reused": False,
        "by_construction_disjoint_non_python_frames": True,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": _initial_cross_source_scan_rows(),
        "cross_source_frame_records": [],
        "prior_raw_exclusion_records": [],
    }
    manifests: list[dict[str, Any]] = []
    if enable_network and audit_match and pt.computed and rav.validated:
        try:
            reservoir, scan_fcc, reservoir_meta, scan_manifest = _scan_cross_source_reservoir(openlocus_bin=openlocus_bin, pt=pt)
            manifests.append(scan_manifest)
            for k, v in scan_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if len(reservoir) < P4J_RESERVOIR_MIN_COUNT:
                fcc["cross_source_reservoir_insufficient"] = 1
            if not reservoir_meta.get("exact_prior_exclusion_used"):
                fcc["exact_prior_exclusion_unavailable"] = 1
            if not reservoir_meta.get("p4h_p4i_overlap_resolved"):
                fcc["p4h_p4i_overlap_not_resolved"] = 1
        except Exception as exc:
            fcc["cross_source_reservoir_scan_failed"] = 1
            fcc["unexpected_exception"] = 1
            reservoir_meta = {
                **reservoir_meta,
                "cross_source_reservoir_scan_attempted": True,
                "scan_diagnostic_records": [
                    _scan_exception_record("cross_source_reservoir_scan", exc)
                ],
            }
    elif enable_network:
        fcc["cross_source_reservoir_scan_not_attempted"] = 1
    else:
        fcc["network_required_but_disabled"] = 1
    return _base_report(status="auto", failure_reason_category="", self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fd1_artifact=fd1_artifact, fd1_schema=fd1_schema, fd1_hash=fd1_hash, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4h_status=p4h_status_str, p4h_denominator_count=p4h_denom_count, p4i_artifact=p4i_artifact, p4i_status=p4i_status_str, p4i_denominator_count=p4i_denom_count, reservoir=reservoir, reservoir_meta=reservoir_meta, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason, fcc_in=fcc, extra_manifests=manifests, aggregate_runtime_seconds=time.perf_counter() - start)


def _build_synthetic_reservoir(
    count: int = 80, *, p4h_p4i_overlap_resolved: bool = False,
    non_python_count: int | None = None,
) -> tuple[list[ReservoirRecord], dict[str, Any]]:
    """Build a synthetic cross-source reservoir for self-test.

    The first ``non_python_count`` records are non-Python (by-construction
    disjoint from FD1 BEA-4/5); the rest are Python (may overlap P4H/P4I).
    """
    reservoir: list[ReservoirRecord] = []
    if non_python_count is None:
        non_python_count = count // 2
    non_python_count = min(non_python_count, count)
    for i in range(count):
        if i < non_python_count:
            sf = P4J_REPOQA_NON_PYTHON_FRAME
            bm = "repoqa"
            lang = "cpp" if i % 2 == 0 else "java"
            offset = 0
            limit = P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT
            window = "repoqa_non_python_languages_reservoir_scan"
        else:
            sf = P4J_CONTEXTBENCH_ALL_FRAME
            bm = "contextbench"
            lang = "python"
            offset = P4J_CONTEXTBENCH_ALL_OFFSET
            limit = P4J_CONTEXTBENCH_ALL_LIMIT
            window = "contextbench_all_languages_reservoir_scan"
        reservoir.append(ReservoirRecord(
            private_record_id=f"{bm}-{lang}-raw-{i}",
            source_frame=sf,
            benchmark=bm,
            language=lang,
            record_index=i,
            window_name=window,
            raw_window_offset=offset,
            raw_window_limit=limit,
        ))
    scan_rows = _initial_cross_source_scan_rows()
    for row in scan_rows:
        if row["source_frame"] == P4J_CONTEXTBENCH_ALL_FRAME:
            selected = sum(1 for d in reservoir if d.source_frame == P4J_CONTEXTBENCH_ALL_FRAME)
            row["raw_rows_fetched"] = P4J_CONTEXTBENCH_ALL_LIMIT
        else:
            selected = sum(1 for d in reservoir if d.source_frame == P4J_REPOQA_NON_PYTHON_FRAME)
            row["raw_rows_fetched"] = selected
        row["raw_rows_attempted"] = selected
        row["raw_rows_file_miss_selected"] = selected
        row["target_reached_in_window"] = len(reservoir) >= P4J_RESERVOIR_MIN_COUNT
    non_python_reservoir_count = sum(1 for d in reservoir if d.language != "python")
    python_reservoir_count = sum(1 for d in reservoir if d.language == "python")
    prior_raw_keys = set()
    for bm in ("contextbench", "repoqa"):
        for i in range(ORIGINAL_P1234_DENOMINATOR_COUNT):
            prior_raw_keys.add((bm, i))
    exact_exclusion_records = []
    for sp in ("BEA-4", "BEA-5"):
        for bm in ("contextbench", "repoqa"):
            exact_exclusion_records.append({
                "source_phase": P4J_RAW_SOURCE_PHASE,
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
    per_language_records = []
    for lang in ("cpp", "java"):
        cnt = sum(1 for d in reservoir if d.language == lang)
        if cnt:
            per_language_records.append({
                "source_frame": P4J_REPOQA_NON_PYTHON_FRAME,
                "language": lang,
                "raw_rows_fetched": cnt,
                "raw_rows_attempted": cnt,
                "raw_rows_by_construction_disjoint_records": cnt,
                "raw_rows_parse_excluded": 0,
                "raw_rows_clone_excluded": 0,
                "raw_rows_baseline_reached_excluded": 0,
                "raw_rows_baseline_error_excluded": 0,
                "raw_rows_file_miss_selected": cnt,
            })
    meta = {
        "denominator_source_protocol": "cross_source_file_miss_reservoir_unlock_audit_scan.v1",
        "source_gold_file_absent_count": 0,
        "excluded_prior_window_count": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "reservoir_count": len(reservoir),
        "reservoir_upper_bound_count": len(reservoir),
        "qualified_cross_source_reservoir_count": len(reservoir) if p4h_p4i_overlap_resolved else 0,
        "cross_source_non_python_reservoir_count": int(non_python_reservoir_count),
        "cross_source_python_reservoir_count": int(python_reservoir_count),
        "cross_source_reservoir_scan_attempted": True,
        "raw_scan_fetched_records": P4J_CONTEXTBENCH_ALL_LIMIT + non_python_reservoir_count,
        "raw_scan_attempted_records": len(reservoir),
        "raw_scan_prior_exact_excluded_records": ORIGINAL_P1234_DENOMINATOR_COUNT,
        "raw_scan_by_construction_disjoint_records": non_python_reservoir_count,
        "raw_scan_yield_file_miss_records": len(reservoir),
        "raw_scan_baseline_reached_records": 0,
        "raw_scan_baseline_error_records": 0,
        "reservoir_min_count": P4J_RESERVOIR_MIN_COUNT,
        "exact_prior_exclusion_scope": EXACT_EXCLUSION_SCOPE,
        "exact_prior_exclusion_used": True,
        "cross_source_disjoint_basis": CROSS_SOURCE_DISJOINT_BASIS,
        "p4h_exact_keys_available_for_exclusion": bool(p4h_p4i_overlap_resolved),
        "p4i_exact_keys_available_for_exclusion": bool(p4h_p4i_overlap_resolved),
        "p4h_p4i_overlap_resolved": bool(p4h_p4i_overlap_resolved),
        "reservoir_upper_bound_includes_possible_p4h_p4i_overlap": not p4h_p4i_overlap_resolved,
        "prior_fd1_denominator_reused": False,
        "by_construction_disjoint_non_python_frames": True,
        "private_key_hashes_publicly_serialized": False,
        "denominator_constructed_before_scheduler_outcomes": True,
        "denominator_scan_records": scan_rows,
        "cross_source_frame_records": per_language_records,
        "prior_raw_exclusion_records": disclosure_records,
    }
    return reservoir, meta


def _synthetic_private_manifest(record_count: int) -> dict[str, Any]:
    digest = hashlib.sha256(f"bea_v1_p4j_synthetic_{record_count}".encode("utf-8")).hexdigest()
    return {
        "manifest_name": "bea_v1_p4j_private_reservoir_scan_manifest",
        "schema_version": "bea_v1_p4j_private_reservoir_scan.v1",
        "storage_class": "private_tmp_only",
        "record_count": int(record_count),
        "records_written": bool(record_count > 0),
        "path_publicly_serialized": False,
        "manifest_hash": digest,
    }


METRIC_TABLE_KEYS = (
    "source_run_records", "denominator_reservoir_records",
    "denominator_scan_records", "cross_source_frame_records",
    "excluded_source_frame_records", "prior_raw_exclusion_records",
    "scan_diagnostic_records",
    "subgroup_reservoir_records", "stop_go_records", "gate_records",
    "private_manifest_records", "failure_category_count_records",
)


def _has_dynamic_dict(report: dict[str, Any]) -> bool:
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
                            "path_hash", "raw_key_hash", "python_ordinal_private"}
    for m in manifests:
        if not isinstance(m, dict):
            return False
        for k in m:
            if str(k) not in allowed and str(k) not in {"manifest_name"}:
                if str(k).endswith("_hash") and str(k) != "manifest_hash":
                    return False
                if str(k) in forbidden_value_keys:
                    return False
        if "manifest_hash" in m and not isinstance(m["manifest_hash"], str):
            return False
        if "record_count" in m and not isinstance(m["record_count"], int):
            return False
    return True


def _build_synthetic_repoqa_non_python_asset() -> bytes:
    """Build a synthetic RepoQA-like ``.json.gz`` asset with non-Python langs."""
    def _repo(lang: str, path: str) -> dict[str, Any]:
        return {
            "repo": f"synthetic/{lang}-repo",
            "commit_sha": "0" * 40,
            "entrypoint_path": f"src/synthetic_{lang}",
            "topic": "synthetic topic",
            "content": "synthetic content placeholder",
            "dependency": "synthetic dependency",
            "functions": ["synthetic_function"],
            "needles": [
                {
                    "name": f"synthetic_needle_{lang}",
                    "path": path,
                    "start_line": 10,
                    "end_line": 20,
                    "start_byte": 100,
                    "end_byte": 200,
                    "global_start_line": 10,
                    "global_end_line": 20,
                    "global_start_byte": 100,
                    "global_end_byte": 200,
                    "code_ratio": 0.1,
                    "description": (
                        f"1. **Purpose**: To handle {lang} merging of adjacent "
                        f"strings into a single string within a line of code.\n"
                        f"2. **Input**: A line of code and indices.\n"
                        f"3. **Output**: A merged string.\n"
                    ),
                }
            ],
        }
    synthetic: dict[str, Any] = {
        "python": [_repo("python", "src/synthetic.py")],
        "cpp": [_repo("cpp", "src/synthetic.cpp")],
        "java": [_repo("java", "src/synthetic.java")],
        "typescript": [_repo("typescript", "src/synthetic.ts")],
    }
    raw = json.dumps(synthetic).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw)
    return buf.getvalue()


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("identity_schema", SCHEMA_VERSION == "bea_v1_p4j_cross_source_reservoir_unlock_audit.v1"))
    checks.append(_check("phase_p4j", PHASE == "BEA-v1-P4J"))
    checks.append(_check("claim_level_audit_only", CLAIM_LEVEL == "bea_v1_p4j_cross_source_reservoir_unlock_audit_only"))
    checks.append(_check("diagnostic_arm_baseline_only", DIAGNOSTIC_ARM == "current_bea_candidate_pool_replay"))
    checks.append(_check("policy_arms_count_1", len(POLICY_ARMS) == 1))
    checks.append(_check("no_p2_p3_p4_in_policy_arms", "p2_depth_only_reference" not in POLICY_ARMS and "p3_constrained_depth_policy_reference" not in POLICY_ARMS and "p4_latency_aware_action_scheduler" not in POLICY_ARMS))
    checks.append(_check("reservoir_min_80", P4J_RESERVOIR_MIN_COUNT == 80))
    checks.append(_check("contextbench_all_offset_0", P4J_CONTEXTBENCH_ALL_OFFSET == 0))
    checks.append(_check("contextbench_all_limit_480", P4J_CONTEXTBENCH_ALL_LIMIT == 480))
    checks.append(_check("contextbench_all_language_filter_all", P4J_CONTEXTBENCH_ALL_LANGUAGE_FILTER == "all"))
    checks.append(_check("contextbench_all_frame_name", P4J_CONTEXTBENCH_ALL_FRAME == "contextbench_all_languages"))
    checks.append(_check("repoqa_non_python_frame_name", P4J_REPOQA_NON_PYTHON_FRAME == "repoqa_non_python_languages"))
    checks.append(_check("repoqa_cli_bypassed_per_lang_limit", P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT == 60))
    checks.append(_check("no_fixed_tail_window_names", all("after_" not in str(w.get("window_name", "")) for w in P4J_SOURCE_FRAMES)))
    checks.append(_check("excluded_swe_explore", any(w["source_frame"] == "swe_explore" for w in P4J_EXCLUDED_SOURCE_FRAMES)))
    checks.append(_check("excluded_core_bench", any(w["source_frame"] == "core_bench" for w in P4J_EXCLUDED_SOURCE_FRAMES)))
    checks.append(_check("excluded_swe_bench_original", any(w["source_frame"] == "swe_bench_original" for w in P4J_EXCLUDED_SOURCE_FRAMES)))
    checks.append(_check("excluded_contextbench_default_config", any(w["source_frame"] == "contextbench_default_config" for w in P4J_EXCLUDED_SOURCE_FRAMES)))
    checks.append(_check("p4i_result_checkpoint_cc19f5b", P4I_RESULT_CHECKPOINT == "cc19f5b"))
    checks.append(_check("p4i_ci_run_id_28137455572", P4I_CI_RUN_ID == "28137455572"))
    checks.append(_check("p4i_denominator_count_73", P4I_DENOMINATOR_COUNT == 73))
    checks.append(_check("p4h_denominator_count_73", P4H_DENOMINATOR_COUNT == 73))
    checks.append(_check("exact_exclusion_scope_bea4_bea5_where_applicable", EXACT_EXCLUSION_SCOPE.startswith("fd1_private_exact_bea4_bea5_raw_keys_where_applicable")))
    checks.append(_check("latency_not_in_relevance_false", DEFAULT_FALSE_FLAGS["latency_in_candidate_relevance"] is False))
    checks.append(_check("no_selector_change", DEFAULT_FALSE_FLAGS["selector_or_reranker_changed"] is False))
    checks.append(_check("no_selector_executed", DEFAULT_FALSE_FLAGS["selector_or_reranker_executed"] is False))
    checks.append(_check("p5_authorized_false", DEFAULT_FALSE_FLAGS["p5_authorized"] is False))
    checks.append(_check("v1_a_authorized_false", DEFAULT_FALSE_FLAGS["v1_a_authorized"] is False))
    checks.append(_check("frozen_p4_rerun_authorized_false_default", DEFAULT_FALSE_FLAGS["frozen_p4_rerun_authorized"] is False))
    checks.append(_check("locked_p4_validation_executed_false", DEFAULT_FALSE_FLAGS["locked_p4_validation_executed"] is False))
    checks.append(_check("p2_p3_p4_arms_not_executed_flags", DEFAULT_FALSE_FLAGS["p2_depth_only_reference_executed"] is False and DEFAULT_FALSE_FLAGS["p3_constrained_depth_policy_reference_executed"] is False and DEFAULT_FALSE_FLAGS["p4_latency_aware_action_scheduler_executed"] is False))
    with tempfile.TemporaryDirectory(prefix="v1p4j_st_") as sd:
        td = Path(sd)
        priv = td / "bea_fd1.decomposition.jsonl"
        p4._build_synthetic_private_decomposition_jsonl(priv, gold_file_absent_count=199)
        pt = p4._parse_private_decomposition_jsonl(priv)
        p4._compute_file_selector_lower_bound(pt)
        checks.append(_check("synthetic_fd1_rows_86040", pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS))
        # --- Synthetic repoqa non-python asset parse ---
        asset_bytes = _build_synthetic_repoqa_non_python_asset()
        parsed, parse_status, _ = p4.c5d._decompress_asset(asset_bytes)
        checks.append(_check("synthetic_repoqa_asset_decompress_pass", parse_status == "pass"))
        non_python_langs = sorted(k for k in parsed if k != "python")
        checks.append(_check("synthetic_asset_has_non_python_langs", set(non_python_langs) == {"cpp", "java", "typescript"}))
        for lang in non_python_langs:
            needles, needle_status, _ = p4.c5d._parse_repoqa_needles(parsed, lang, P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT)
            checks.append(_check(f"synthetic_repoqa_{lang}_needles_parsed", needle_status == "pass" and len(needles) == 1))
        # --- Qualified ready (overlap resolved) ---
        reservoir80, meta80 = _build_synthetic_reservoir(80, p4h_p4i_overlap_resolved=True)
        checks.append(_check("synthetic_reservoir_80", len(reservoir80) == 80))
        checks.append(_check("reservoir_source_protocol", meta80.get("denominator_source_protocol") == "cross_source_file_miss_reservoir_unlock_audit_scan.v1"))
        checks.append(_check("reservoir_scan_attempted", meta80.get("cross_source_reservoir_scan_attempted") is True))
        checks.append(_check("prior_fd1_not_reused", meta80.get("prior_fd1_denominator_reused") is False))
        checks.append(_check("exact_prior_exclusion_used_true", meta80.get("exact_prior_exclusion_used") is True))
        checks.append(_check("by_construction_disjoint_non_python_true", meta80.get("by_construction_disjoint_non_python_frames") is True))
        checks.append(_check("synthetic_ready_p4h_p4i_overlap_resolved", meta80.get("p4h_p4i_overlap_resolved") is True))
        checks.append(_check("synthetic_ready_not_upper_bound_only", meta80.get("reservoir_upper_bound_includes_possible_p4h_p4i_overlap") is False))
        checks.append(_check("prior_exclusion_disclosure_records_present", len(meta80.get("prior_raw_exclusion_records", [])) >= 5))
        checks.append(_check("scan_rows_disclose_cross_source_frames", all("source_frame" in r and "raw_rows_fetched" in r for r in meta80.get("denominator_scan_records", []))))
        checks.append(_check("scan_rows_no_private_ids", all("private_record_id" not in r and "record_ids" not in r for r in meta80.get("denominator_scan_records", []))))
        checks.append(_check("p4h_disclosure_record_present", any(r.get("exclusion_source_phase") == "BEA-v1-P4H" and r.get("excluded_record_count_aggregate") == 73 for r in meta80.get("prior_raw_exclusion_records", []))))
        checks.append(_check("p4i_disclosure_record_present", any(r.get("exclusion_source_phase") == "BEA-v1-P4I" and r.get("excluded_record_count_aggregate") == 73 for r in meta80.get("prior_raw_exclusion_records", []))))
        checks.append(_check("by_construction_disjoint_disclosure_present", any(r.get("exclusion_source_phase") == "cross_source_non_python_frames" for r in meta80.get("prior_raw_exclusion_records", []))))
        checks.append(_check("cross_source_frame_records_present", len(meta80.get("cross_source_frame_records", [])) > 0))
        replay_path = td / "fd1_replay_report.json"
        p4._build_synthetic_fd1_replay_artifact(replay_path)
        rav = p4._validate_fd1_replay_artifact(replay_path, "a" * 64)
        fd1_art = p4._build_synthetic_fd1_artifact()
        p4h_art = {"status": P4H_RESULT_STATUS, "denominator_count": P4H_DENOMINATOR_COUNT, "stop_go_records": [{"denominator_min": P4H_DENOMINATOR_MIN}]}
        p4i_art = {"status": P4I_RESULT_STATUS, "denominator_count": P4I_DENOMINATOR_COUNT}
        scan_manifest = _synthetic_private_manifest(len(reservoir80))
        report80 = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir80, reservoir_meta=meta80, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        for table in METRIC_TABLE_KEYS:
            checks.append(_check(f"table_{table}_is_list", isinstance(report80.get(table), list)))
        checks.append(_check("synthetic_reservoir_80_ready", report80.get("status") == "cross_source_reservoir_ready_for_locked_p4_validation_design"))
        checks.append(_check("forbidden_scan_pass", report80.get("forbidden_scan", {}).get("status") == "pass"))
        checks.append(_check("ready_authorization_flags_false", report80.get("stop_go_records", [{}])[0].get("p5_authorized") is False and report80.get("stop_go_records", [{}])[0].get("v1_a_authorized") is False and report80.get("stop_go_records", [{}])[0].get("runtime_promotion_authorized") is False and report80.get("stop_go_records", [{}])[0].get("method_winner_authorized") is False and report80.get("stop_go_records", [{}])[0].get("broad_retrieval_expansion_authorized") is False))
        checks.append(_check("ready_locked_p4_validation_design_authorized_true", report80.get("stop_go_records", [{}])[0].get("locked_p4_validation_design_authorized") is True))
        checks.append(_check("ready_scheduler_validation_authorized_false", report80.get("stop_go_records", [{}])[0].get("scheduler_validation_authorized") is False))
        checks.append(_check("ready_locked_p4_validation_executed_false", report80.get("stop_go_records", [{}])[0].get("locked_p4_validation_executed") is False))
        checks.append(_check("ready_frozen_p4_rerun_authorized_false", report80.get("stop_go_records", [{}])[0].get("frozen_p4_rerun_authorized") is False))
        checks.append(_check("top_level_locked_p4_design_authorization_stop_go_only", report80.get("locked_p4_validation_executed") is False and report80.get("framing", {}).get("locked_p4_validation_design_authorization_scope") == "stop_go_records_only"))
        checks.append(_check("report_reservoir_records_present", len(report80.get("denominator_reservoir_records", [])) > 0))
        checks.append(_check("report_scan_records_present", len(report80.get("denominator_scan_records", [])) == 2))
        checks.append(_check("report_cross_source_frame_records_present", len(report80.get("cross_source_frame_records", [])) > 0))
        checks.append(_check("report_excluded_source_frame_records_present", len(report80.get("excluded_source_frame_records", [])) == 4))
        checks.append(_check("report_prior_exclusion_records_present", len(report80.get("prior_raw_exclusion_records", [])) >= 5))
        checks.append(_check("report_prior_fd1_not_reused", report80.get("prior_fd1_denominator_reused") is False))
        checks.append(_check("report_exact_prior_exclusion_used_true", report80.get("exact_prior_exclusion_used") is True))
        checks.append(_check("report_cumulative_reservoir_count", report80.get("cumulative_cross_source_reservoir_count") == 80))
        checks.append(_check("report_qualified_cross_source_reservoir_count_80", report80.get("qualified_cross_source_reservoir_count") == 80))
        checks.append(_check("by_construction_disjoint_records_field_name", "raw_scan_by_construction_disjoint_records" in report80 and "raw_scan_by_construction_disjoint_excluded_records" not in report80))
        # --- Unqualified (overlap unresolved) ---
        reservoir80_unq, meta80_unq = _build_synthetic_reservoir(80, p4h_p4i_overlap_resolved=False)
        report80_unq = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir80_unq, reservoir_meta=meta80_unq, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("reservoir_80_unqualified_without_overlap", report80_unq.get("status") == "no_go_cross_source_reservoir_unqualified"))
        checks.append(_check("unqualified_no_locked_p4_design", report80_unq.get("stop_go_records", [{}])[0].get("locked_p4_validation_design_authorized") is False))
        checks.append(_check("unqualified_upper_bound_count_80", report80_unq.get("reservoir_upper_bound_count") == 80 and report80_unq.get("qualified_cross_source_reservoir_count") == 0))
        # --- Insufficient (< 80) ---
        reservoir79, meta79 = _build_synthetic_reservoir(79)
        report79 = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, aggregate_runtime_seconds=0.5)
        checks.append(_check("synthetic_reservoir_79_insufficient", report79.get("status") == "no_go_cross_source_file_miss_reservoir_insufficient"))
        checks.append(_check("insufficient_reservoir_count", report79.get("cumulative_cross_source_reservoir_count") == 79))
        # --- Default no-network => unavailable_with_reason ---
        report_default = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="missing", network_mode="disabled_opt_in", fcc_in={"network_required_but_disabled": 1})
        checks.append(_check("default_unavailable_with_reason", report_default.get("status") == "unavailable_with_reason"))
        checks.append(_check("default_stop_go_unavailable", report_default.get("stop_go_records", [{}])[0].get("stop_go_decision") == "unavailable_with_reason"))
        checks.append(_check("default_not_ready", report_default.get("status") != "cross_source_reservoir_ready_for_locked_p4_validation_design"))
        # --- Blocking failures cannot be reported as insufficient ---
        report_scan_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, fcc_in={"cross_source_reservoir_scan_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("scan_failure_not_insufficient_no_go", report_scan_fail.get("status") == "fail_schema_contract"))
        report_parser_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, fcc_in={"cross_source_reservoir_scan_failed": 1, "raw_denominator_parse_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("repoqa_parser_failure_fail_closed", report_parser_fail.get("status") == "fail_schema_contract"))
        report_clone_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, fcc_in={"raw_denominator_clone_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("clone_failure_not_insufficient_no_go", report_clone_fail.get("status") == "fail_schema_contract"))
        report_asset_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79}, audit_match=True, fcc_in={"cross_source_asset_download_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("asset_download_failure_fail_closed", report_asset_fail.get("status") == "fail_schema_contract"))
        report_exact_missing = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=reservoir79, reservoir_meta={**meta79, "reservoir_count": 79, "exact_prior_exclusion_used": False}, audit_match=True, fcc_in={"exact_prior_exclusion_unavailable": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("exact_prior_missing_fail_closed", report_exact_missing.get("status") == "fail_schema_contract"))
        report_not_attempted = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4h_status=P4H_RESULT_STATUS, p4h_denominator_count=P4H_DENOMINATOR_COUNT, p4i_artifact=p4i_art, p4i_status=P4I_RESULT_STATUS, p4i_denominator_count=P4I_DENOMINATOR_COUNT, reservoir=[], reservoir_meta={**meta79, "reservoir_count": 0, "cross_source_reservoir_scan_attempted": False}, audit_match=True, fcc_in={"cross_source_reservoir_scan_not_attempted": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("not_attempted_is_fail_not_insufficient", report_not_attempted.get("status") == "fail_schema_contract"))
        # --- Public shape is records-only (no dynamic dicts) ---
        checks.append(_check("public_shape_no_dynamic_dicts", _has_dynamic_dict(report80) is False))
        checks.append(_check("manifest_fields_safe", _manifest_fields_safe(report80.get("private_manifest_records", [])) is True))
        manifest_has_hash = any(m.get("manifest_hash") for m in report80.get("private_manifest_records", []) if isinstance(m, dict))
        checks.append(_check("manifest_has_provenance_hash", manifest_has_hash is True))
        checks.append(_check("manifest_no_private_paths", all(m.get("path_publicly_serialized") is False for m in report80.get("private_manifest_records", []) if isinstance(m, dict))))
        # --- Forbidden scanner rejects private keys/ids ---
        leaked = dict(report80)
        leaked["private_record_id"] = "leak"
        checks.append(_check("scanner_rejects_private_record_id", _v1_p4j_forbidden_scan_summary(leaked)["status"] == "fail"))
        leaked2 = dict(report80)
        leaked2["candidate_paths"] = ["leak"]
        checks.append(_check("scanner_rejects_candidate_paths", _v1_p4j_forbidden_scan_summary(leaked2)["status"] == "fail"))
        leaked3 = dict(report80)
        leaked3["exact_raw_keys"] = ["leak"]
        checks.append(_check("scanner_rejects_exact_raw_keys", _v1_p4j_forbidden_scan_summary(leaked3)["status"] == "fail"))
        leaked4 = dict(report80)
        leaked4["repo_url_private"] = "leak"
        checks.append(_check("scanner_rejects_repo_url_private", _v1_p4j_forbidden_scan_summary(leaked4)["status"] == "fail"))
        checks.append(_check("forbidden_violation_categories_is_list", isinstance(report80.get("forbidden_scan", {}).get("violation_categories"), list)))
        # --- Reservoir gate ---
        checks.append(_check("reservoir_80_gate_pass", bool(report80.get("gate_records") and any(g.get("gate") == "reservoir_count_min" and g.get("passed") is True for g in report80.get("gate_records", [])))))
        checks.append(_check("reservoir_79_gate_fail", bool(report79.get("gate_records") and any(g.get("gate") == "reservoir_count_min" and g.get("passed") is False for g in report79.get("gate_records", [])))))
        # --- Non-python subset disclosed ---
        checks.append(_check("report_non_python_reservoir_count_disclosed", report80.get("cross_source_non_python_reservoir_count", 0) >= 0))
        checks.append(_check("report_python_reservoir_count_disclosed", report80.get("cross_source_python_reservoir_count", 0) >= 0))
    parser = build_parser()
    opts = {opt for action in parser._actions for opt in action.option_strings}
    for opt in ("--self-test", "--out", "--fd1-artifact", "--fd1-private-decomposition-jsonl", "--fd1-replay-artifact", "--p4h-artifact", "--p4i-artifact", "--openlocus", "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in opts))
    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-P4J Cross-Source File-Miss Reservoir Unlock Audit")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd1-private-decomposition-jsonl", type=Path, default=None)
    ap.add_argument("--fd1-replay-artifact", type=Path, default=None)
    ap.add_argument("--p4h-artifact", type=Path, default=DEFAULT_P4H_ARTIFACT)
    ap.add_argument("--p4i-artifact", type=Path, default=DEFAULT_P4I_ARTIFACT)
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
        report = _base_report(status="fail_schema_contract", failure_reason_category="openlocus_binary_missing", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source, network_mode=network_mode, fcc_in={"openlocus_binary_missing": 1})
    elif not enable_network:
        report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "missing", network_mode=network_mode, fcc_in={"network_required_but_disabled": 1})
    else:
        try:
            report = _run_reservoir_audit(openlocus_bin=openlocus_bin or "", openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, self_test_passed=True, self_test_checks_total=len(checks), fd1_artifact_path=args.fd1_artifact, fd1_private_decomposition_jsonl=args.fd1_private_decomposition_jsonl, fd1_replay_artifact=args.fd1_replay_artifact, p4h_artifact_path=args.p4h_artifact, p4i_artifact_path=args.p4i_artifact, enable_network=enable_network)
        except Exception:
            report = _base_report(status="fail_schema_contract", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, fcc_in={"unexpected_exception": 1})
    if report.get("provider_calls_made") is not False or report.get("latency_in_candidate_relevance") is not False or report.get("gold_labels_used_for_policy") is not False or report.get("query_anchors_used_in_p4_arm") is not False or report.get("p2_depth_only_reference_executed") is not False or report.get("p3_constrained_depth_policy_reference_executed") is not False or report.get("p4_latency_aware_action_scheduler_executed") is not False or report.get("selector_or_reranker_executed") is not False or report.get("v1_a_selector_executed") is not False:
        report["status"] = "fail_schema_contract"
    _enforce_v1_p4j_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    sgr = report.get("stop_go_records", [{}])[0] if report.get("stop_go_records") else {}
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={report['phase']}, denominator_count={report.get('denominator_count', 0)}, stop_go_decision={sgr.get('stop_go_decision', '')})")
    if not enable_network:
        print("enable_external_benchmark_network is false; skipping real BEA-v1-P4J cross-source reservoir unlock audit.")


if __name__ == "__main__":
    main()
