#!/usr/bin/env python3
"""BEA-v1-P4L: Locked Non-Python P4 Scheduler Validation.

P4L is a bounded **scheduler-validation phase** performed after the BEA-v1-P4K
result checkpoint ``dccfb64`` (CI ``28151914531``,
``cross_source_locked_reservoir_ready_for_locked_p4_validation_design``,
locked non-Python denominator 272).  It validates whether the frozen BEA-v1-P4
retrieval-action scheduler generalizes from the original same-frame Python
denominator to the P4K-locked, all-prior-disjoint non-Python cross-source
reservoir.

P4L does **not** run P5, BEA-v1-A, selector/reranker work, runtime/default
promotion, or method-winner claims.  It does **not** tune P4 parameters, search
thresholds, add arms, expand retrieval beyond frozen prior arms, call providers,
or rerun frozen P4 on the old Python 73-record denominator.

The fixed denominator is the P4K locked reservoir exactly:
- P4H reconstructed: 73/73
- P4I reconstructed: 73/73
- P4J reconstructed: 333/333 (61 Python + 272 non-Python)
- P4J overlap with P4H/P4I: 61
- locked denominator: 272, all non-Python

The implementation must reconstruct the locked denominator before running any
scheduler arm.  If the reconstructed denominator is not exactly 272 (or P4K/P4J
split/overlap does not reproduce), the status is
``no_go_p4l_locked_denominator_unavailable`` or ``fail_schema_contract``; it
must NOT silently change the denominator.

Allowed frozen arms (definitions frozen from prior committed P2/P3/P4 code):
1. ``baseline_current_candidate_pool``
2. ``p2_depth_only_reference``
3. ``p3_constrained_depth_policy_reference``
4. ``p4_latency_aware_action_scheduler_frozen``

The public artifact is aggregate-only and records-only.  Private per-record arm
outcomes / scheduler traces are written under ``/tmp`` only with manifest
rows/hashes and ``path_publicly_serialized=false``.  No private row IDs, raw
keys, repo URLs, base commits, queries, candidate paths, gold paths, snippets,
or provider payloads are serialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
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
import bea_v1_p4j_cross_source_reservoir_unlock_audit as p4j  # noqa: E402
import bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit as p4k  # noqa: E402

SCHEMA_VERSION = "bea_v1_p4l_locked_non_python_scheduler_validation.v1"
GENERATED_BY = "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py"
CLAIM_LEVEL = "bea_v1_p4l_locked_non_python_scheduler_validation_only"
MODE = "bea_v1_p4l_locked_non_python_scheduler_validation"
PHASE = "BEA-v1-P4L"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/"
    "bea_v1_p4l_locked_non_python_scheduler_validation_report.json"
)
DEFAULT_FD1_ARTIFACT = p4.DEFAULT_FD1_ARTIFACT
DEFAULT_P4H_ARTIFACT = p4h.DEFAULT_OUT
DEFAULT_P4I_ARTIFACT = p4i.DEFAULT_OUT
DEFAULT_P4J_ARTIFACT = p4j.DEFAULT_OUT
DEFAULT_P4K_ARTIFACT = p4k.DEFAULT_OUT

# --- P4K binding context (read-only motivation; locked denominator source) ---
P4K_RESULT_CHECKPOINT = "dccfb64"
P4K_CI_RUN_ID = "28151914531"
P4K_RESULT_STATUS = "cross_source_locked_reservoir_ready_for_locked_p4_validation_design"
P4K_LOCKED_DENOMINATOR_COUNT = 272
P4K_P4H_RECONSTRUCTED_COUNT = 73
P4K_P4I_RECONSTRUCTED_COUNT = 73
P4K_P4J_RECONSTRUCTED_COUNT = 333
P4K_P4J_PYTHON_SPLIT = 61
P4K_P4J_NON_PYTHON_SPLIT = 272
P4K_P4J_OVERLAP = 61

# --- P4H binding context (read-only) ---
P4H_RESULT_STATUS = "no_go_p4h_insufficient_denominator"
P4H_DENOMINATOR_COUNT = 73

# --- P4I binding context (read-only) ---
P4I_RESULT_STATUS = "no_go_disjoint_denominator_reservoir_insufficient"
P4I_RESERVOIR_COUNT = 73

# --- P4J binding context (read-only) ---
P4J_RESULT_STATUS = "no_go_cross_source_reservoir_unqualified"
P4J_UPPER_BOUND_COUNT = 333

# --- P4 binding context (read-only) ---
V1_P4_RESULT_CHECKPOINT = "f0e99ca"
V1_P4_RESULT_STATUS = "bea_v1_p4_latency_aware_retrieval_scheduler_pass"

FIXED_BUDGET = p4.FIXED_BUDGET
FIXED_METHODS = p4.FIXED_METHODS
EXPECTED_RECORDS_DECOMPOSED = p4.EXPECTED_RECORDS_DECOMPOSED
EXPECTED_PRIVATE_DECOMP_ROWS = p4.EXPECTED_PRIVATE_DECOMP_ROWS

# Frozen P4 scheduler constants (binding; no tuning).
P4L_HARD_CANDIDATE_CAP = p4.P4_HARD_CANDIDATE_CAP
P4L_UNIQUE_FILE_CAP = p4.P4_UNIQUE_FILE_CAP
P4L_BASELINE_DEPTH_MULTIPLIER = p4.BASELINE_DEPTH_MULTIPLIER
P4L_DEPTH_REFERENCE_MULTIPLIER = p4.DEPTH_REFERENCE_MULTIPLIER
# Frozen thresholds (from prior P4; explicit, no post-hoc tuning).
P4L_REACH_PRESERVATION_DEPTH_RATIO = p4.P4_REACH_PRESERVATION_DEPTH_RATIO  # 0.75
P4L_LATENCY_MULT_MAX = p4.P4_LATENCY_MULT_MAX  # 2.0
P4L_LATENCY_VS_P3_IMPROVEMENT_MIN = p4.P4_LATENCY_VS_P3_IMPROVEMENT_MIN  # 0.10
P4L_POOL_MULT_MAX = p4.P4_POOL_MULT_MAX  # 4.0
P4L_HARD_CAP_VIOLATION_MAX = p4.P4_HARD_CAP_VIOLATION_MAX  # 0

# Allowed frozen arms (4, fixed; no new arm).
P4L_ARMS = (
    "baseline_current_candidate_pool",
    "p2_depth_only_reference",
    "p3_constrained_depth_policy_reference",
    "p4_latency_aware_action_scheduler_frozen",
)
DIAGNOSTIC_ARM = "current_bea_candidate_pool_replay"

STATUSES = (
    "bea_v1_p4l_locked_non_python_scheduler_validation_pass",
    "no_go_p4l_locked_non_python_scheduler_validation_failed",
    "no_go_p4l_locked_denominator_unavailable",
    "fail_schema_contract",
    "fail_forbidden_scan",
    "unavailable_with_reason",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "bea_v1_p4l_locked_non_python_scheduler_validation_pass",
    "no_go_p4l_locked_non_python_scheduler_validation_failed",
    "no_go_p4l_locked_denominator_unavailable",
})

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "records_only_public_artifact": True,
    "scheduler_validation_only": True,
    "locked_non_python_scheduler_validation_only": True,
    "fd1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "p4h_artifact_read": False,
    "p4i_artifact_read": False,
    "p4j_artifact_read": False,
    "p4k_artifact_read": False,
    "bea_v1_p4l_audit_evaluator_no_provider_calls": True,
    "bea_v1_p4l_audit_evaluator_no_selector_executed": True,
    "bea_v1_p4l_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p4l_audit_evaluator_no_role_proxy": True,
    "bea_v1_p4l_audit_evaluator_latency_not_in_relevance": True,
    "bea_v1_p4l_audit_evaluator_no_p5_selector": True,
    "bea_v1_p4l_audit_evaluator_no_v1_a": True,
    "bea_v1_p4l_audit_evaluator_no_broad_retrieval_expansion": True,
    "bea_v1_p4l_audit_evaluator_no_threshold_search": True,
    "bea_v1_p4l_audit_evaluator_no_parameter_tuning": True,
    "bea_v1_p4l_audit_evaluator_no_new_arms": True,
    "bea_v1_p4l_audit_evaluator_no_runtime_default_promotion": True,
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
    "algorithm_changed_during_bea_v1_p4l": False,
    "weights_tuned_during_bea_v1_p4l": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p4l": False,
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
    "frozen_p4_validation_executed": False,
    "locked_p4_validation_authorized": False,
    "future_locked_p4_validation_authorized": False,
    "threshold_search_executed": False,
    "posthoc_threshold_search": False,
    "parameter_tuning_executed": False,
    "new_arms_added": False,
    "v031_tuning_executed": False,
    "v032_tuning_executed": False,
    "b16k_executed": False,
    "role_proxy_assigned": False,
    "latency_in_candidate_relevance": False,
    "private_decomposition_used_for_selection": False,
    "gold_labels_used_for_selection": False,
    "gold_labels_used_for_query_construction": False,
    "gold_labels_used_for_policy": False,
    "query_anchors_used_in_p4_arm": False,
    "p2_depth_only_reference_executed": False,
    "p3_constrained_depth_policy_reference_executed": False,
    "p4_latency_aware_action_scheduler_executed": False,
    "new_records_added_during_bea_v1_p4l": False,
}
LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_p4l_locked_non_python_scheduler_validation",
}

FAILURE_CATEGORIES_AUDIT = tuple(dict.fromkeys((*p4.FAILURE_CATEGORIES_AUDIT,
    "locked_denominator_unavailable",
    "locked_denominator_mismatch",
    "p4l_scheduler_validation_failed",
    "p4l_arms_not_executed",
    "p4k_artifact_status_mismatch",
    "p4k_locked_count_mismatch",
    "p4k_split_or_overlap_mismatch",
    "p4l_scan_not_attempted",
    "p4l_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "raw_denominator_parse_failed",
    "raw_denominator_scan_failed",
    "raw_denominator_scan_not_attempted",
    "raw_denominator_clone_failed",
    "retrieval_policy_failed",
)))
BLOCKING_FAILURE_CATEGORIES = tuple(dict.fromkeys((
    *p4.BLOCKING_FAILURE_CATEGORIES,
    "p4l_scan_not_attempted",
    "p4l_scan_failed",
    "p4k_artifact_status_mismatch",
    "p4k_locked_count_mismatch",
    "p4k_split_or_overlap_mismatch",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "raw_denominator_parse_failed",
    "raw_denominator_scan_failed",
    "raw_denominator_scan_not_attempted",
    "raw_denominator_clone_failed",
    "retrieval_policy_failed",
    "unexpected_exception",
)))


def _now_iso() -> str:
    return p4._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    p4._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return p4._check(name, ok)


def _resolve_private_validation_dir() -> Path:
    raw = os.environ.get("OPENLOCUS_BEA_V1_P4L_PRIVATE_VALIDATION_DIR", "")
    project_private = Path(__file__).resolve().parents[1] / ".openlocus" / "research-private"
    base = Path(raw) if raw else project_private / f"bea_v1_p4l_validation_{os.getpid()}"
    resolved = base.resolve()
    allowed_project = project_private.resolve()
    if not (str(resolved).startswith(str(allowed_project)) or str(resolved).startswith("/tmp/")):
        raise ValueError("invalid private validation dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _reconstruct_locked_denominator(
    *, openlocus_bin: str, pt: Any, private_path: Path, fcc: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconstruct the P4K locked non-Python denominator.

    Returns ``(denominator_records, recon_meta)`` where each record is a
    private dict with keys: source_frame, benchmark, language, raw_idx,
    python_ordinal (None for non-Python), query, repo_url, base_commit,
    gold_paths.  All private; only aggregate counts are publicly serialized.
    """
    prior_raw_keys, _ = p4h._prior_raw_keys_from_fd1_private(pt)
    use_exact_prior_keys = bool(prior_raw_keys)
    denominator: list[dict[str, Any]] = []
    repo_parent = private_path.parent / "repos"
    repo_parent.mkdir(parents=True, exist_ok=True)
    fetched_total = attempted = prior_excluded = by_construction = 0
    parse_excluded = clone_excluded = baseline_reached = baseline_error = 0
    python_locked = non_python_locked = 0
    cb_fetched = rq_fetched = 0
    cb_file_miss = rq_file_miss = 0

    # --- ContextBench all-languages (P4J frame) ---
    rows, fetch_status, _, fetch_fcc = p4.c5a._fetch_contextbench_rows(
        p4j.P4J_CONTEXTBENCH_ALL_LIMIT, "all")
    for k, v in fetch_fcc.items():
        if k in fcc:
            fcc[k] += int(v)
    if fetch_status != "pass" or not rows:
        fcc["p4l_scan_failed"] = fcc.get("p4l_scan_failed", 0) + 1
        fcc["raw_denominator_scan_failed"] = fcc.get("raw_denominator_scan_failed", 0) + 1
        return denominator, {"reconstructed": False}
    if len(rows) > p4j.P4J_CONTEXTBENCH_ALL_LIMIT:
        rows = rows[:p4j.P4J_CONTEXTBENCH_ALL_LIMIT]
    cb_fetched = len(rows)
    fetched_total += cb_fetched
    python_ordinal = 0
    for local_idx, row in enumerate(rows):
        lang = str(row.get("language", "") or "")
        is_python = (lang == "python")
        if use_exact_prior_keys and is_python and ("contextbench", python_ordinal) in prior_raw_keys:
            prior_excluded += 1
            if is_python:
                python_ordinal += 1
            continue
        if use_exact_prior_keys and not is_python:
            by_construction += 1
        attempted += 1
        query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval("contextbench", row)
        if not ok:
            parse_excluded += 1
            fcc["raw_denominator_parse_failed"] = fcc.get("raw_denominator_parse_failed", 0) + 1
            if is_python:
                python_ordinal += 1
            continue
        work = repo_parent / f"contextbench_{local_idx}"
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True, exist_ok=True)
        try:
            clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if not clone_ok:
                clone_excluded += 1
                fcc["raw_denominator_clone_failed"] = fcc.get("raw_denominator_clone_failed", 0) + 1
                if is_python:
                    python_ordinal += 1
                continue
            repo_root = work / "repo"
            rr = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
            if rr.retrieval_error:
                baseline_error += 1
                fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
                if is_python:
                    python_ordinal += 1
                continue
            p4._append_private_jsonl(private_path, {
                "schema_version": "bea_v1_p4l_private_reconstruction.v1",
                "source_phase": "P4L-LOCKED-RECONSTRUCTION",
                "source_frame": "contextbench_all_languages",
                "benchmark": "contextbench",
                "language": lang,
                "raw_record_index_private": local_idx,
                "python_ordinal_private": python_ordinal if is_python else None,
                "baseline_gold_file_available": rr.gold_file_available,
                "selected_for_denominator": not rr.gold_file_available and not is_python,
                "config_hash": p4._config_hash(),
            })
            if rr.gold_file_available:
                baseline_reached += 1
                if is_python:
                    python_ordinal += 1
                continue
            # File-miss; non-Python only counts toward locked denominator
            if not is_python:
                denominator.append({
                    "source_frame": "contextbench_all_languages",
                    "benchmark": "contextbench",
                    "language": lang,
                    "raw_idx": local_idx,
                    "python_ordinal": None,
                    "query": query,
                    "repo_url": repo_url,
                    "base_commit": base_commit,
                    "gold_paths": gold_paths,
                    "repo_root": repo_root,
                })
                non_python_locked += 1
                cb_file_miss += 1
            else:
                python_locked += 1
        except Exception:
            fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
            fcc["unexpected_exception"] = fcc.get("unexpected_exception", 0) + 1
        if is_python:
            python_ordinal += 1

    # --- RepoQA non-Python (P4J frame) ---
    asset_bytes, dl_status, dl_fcc = p4.c5d._download_asset_to_bytes(p4.c5d.ASSET_URL)
    for k, v in dl_fcc.items():
        if k in fcc:
            fcc[k] += int(v)
    if dl_status != "pass" or not asset_bytes:
        fcc["cross_source_asset_download_failed"] = 1
        fcc["p4l_scan_failed"] = fcc.get("p4l_scan_failed", 0) + 1
        return denominator, {"reconstructed": False}
    parsed_asset, parse_status, parse_fcc = p4.c5d._decompress_asset(asset_bytes)
    del asset_bytes
    for k, v in parse_fcc.items():
        if k in fcc:
            fcc[k] += int(v)
    if parse_status != "pass" or parsed_asset is None:
        fcc["cross_source_asset_decompress_failed"] = 1
        fcc["p4l_scan_failed"] = fcc.get("p4l_scan_failed", 0) + 1
        return denominator, {"reconstructed": False}
    if isinstance(parsed_asset, dict):
        non_python_langs = sorted(
            str(k) for k in parsed_asset
            if k != "python" and isinstance(parsed_asset.get(k), list))
        for lang in non_python_langs:
            needles, needle_status, needle_fcc = p4.c5d._parse_repoqa_needles(
                parsed_asset, lang, p4j.P4J_REPOQA_NON_PYTHON_PER_LANG_LIMIT)
            for k, v in needle_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if needle_status != "pass":
                if needle_status != "unavailable_no_python_needles":
                    fcc["raw_denominator_parse_failed"] = fcc.get("raw_denominator_parse_failed", 0) + 1
                    fcc["p4l_scan_failed"] = fcc.get("p4l_scan_failed", 0) + 1
                continue
            if not needles:
                continue
            rq_fetched += len(needles)
            fetched_total += len(needles)
            for local_idx, needle in enumerate(needles):
                by_construction += 1
                attempted += 1
                query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval("repoqa", needle)
                if not ok:
                    parse_excluded += 1
                    fcc["raw_denominator_parse_failed"] = fcc.get("raw_denominator_parse_failed", 0) + 1
                    continue
                safe_lang = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(lang))[:64]
                work = repo_parent / f"repoqa_{safe_lang}_{local_idx}"
                if work.exists():
                    shutil.rmtree(work)
                work.mkdir(parents=True, exist_ok=True)
                try:
                    clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
                    for k, v in clone_fcc.items():
                        if k in fcc:
                            fcc[k] += int(v)
                    if not clone_ok:
                        clone_excluded += 1
                        fcc["raw_denominator_clone_failed"] = fcc.get("raw_denominator_clone_failed", 0) + 1
                        continue
                    repo_root = work / "repo"
                    rr = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
                    if rr.retrieval_error:
                        baseline_error += 1
                        fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
                        continue
                    p4._append_private_jsonl(private_path, {
                        "schema_version": "bea_v1_p4l_private_reconstruction.v1",
                        "source_phase": "P4L-LOCKED-RECONSTRUCTION",
                        "source_frame": "repoqa_non_python_languages",
                        "benchmark": "repoqa",
                        "language": lang,
                        "raw_record_index_private": local_idx,
                        "baseline_gold_file_available": rr.gold_file_available,
                        "selected_for_denominator": not rr.gold_file_available,
                        "config_hash": p4._config_hash(),
                    })
                    if rr.gold_file_available:
                        baseline_reached += 1
                        continue
                    denominator.append({
                        "source_frame": "repoqa_non_python_languages",
                        "benchmark": "repoqa",
                        "language": lang,
                        "raw_idx": local_idx,
                        "python_ordinal": None,
                        "query": query,
                        "repo_url": repo_url,
                        "base_commit": base_commit,
                        "gold_paths": gold_paths,
                        "repo_root": repo_root,
                    })
                    non_python_locked += 1
                    rq_file_miss += 1
                except Exception:
                    fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
                    fcc["unexpected_exception"] = fcc.get("unexpected_exception", 0) + 1

    recon_meta = {
        "reconstructed": True,
        "fetched_total": fetched_total,
        "attempted": attempted,
        "prior_exact_excluded": prior_excluded,
        "by_construction_disjoint_records": by_construction,
        "parse_excluded": parse_excluded,
        "clone_excluded": clone_excluded,
        "baseline_reached": baseline_reached,
        "baseline_error": baseline_error,
        "non_python_locked_count": non_python_locked,
        "python_locked_count": python_locked,
        "p4j_reconstructed_upper_bound_count": python_locked + non_python_locked,
        "p4j_reconstructed_python_count": python_locked,
        "p4j_reconstructed_non_python_count": non_python_locked,
        "contextbench_fetched": cb_fetched,
        "contextbench_file_miss": cb_file_miss,
        "repoqa_fetched": rq_fetched,
        "repoqa_file_miss": rq_file_miss,
        "exact_prior_exclusion_used": use_exact_prior_keys,
    }
    return denominator, recon_meta


def _run_arm_on_denominator(
    *, arm_name: str, openlocus_bin: str, denom: list[dict[str, Any]],
    private_path: Path, fcc: dict[str, int],
) -> dict[str, Any]:
    """Run one frozen arm on every denominator record.

    Returns aggregate metrics dict.  Private per-record outcomes are written
    to ``private_path`` (under ``/tmp`` only).
    """
    reached = 0
    total_latency = 0.0
    pool_sizes: list[int] = []
    hard_cap_violations = 0
    errors = 0
    first_gold_ranks: list[int] = []
    for i, rec in enumerate(denom):
        repo_root = rec["repo_root"]
        query = rec["query"]
        gold_set = {str(x) for x in rec["gold_paths"] if x}
        try:
            if arm_name == "baseline_current_candidate_pool":
                rr = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set=gold_set)
            elif arm_name == "p2_depth_only_reference":
                rr = p4._run_depth_reference_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set=gold_set)
            elif arm_name == "p3_constrained_depth_policy_reference":
                rr = p4._run_p3_reference_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set=gold_set)
            elif arm_name == "p4_latency_aware_action_scheduler_frozen":
                rr = p4._run_p4_latency_aware_scheduler_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set=gold_set)
            else:
                fcc["p4l_arms_not_executed"] = fcc.get("p4l_arms_not_executed", 0) + 1
                continue
        except Exception:
            errors += 1
            fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
            continue
        if rr.retrieval_error:
            errors += 1
            fcc["retrieval_policy_failed"] = fcc.get("retrieval_policy_failed", 0) + 1
            continue
        if rr.gold_file_available:
            reached += 1
            first_gold_ranks.append(rr.first_gold_file_rank)
        total_latency += rr.retrieval_latency_seconds
        pool_sizes.append(rr.candidate_pool_size)
        if rr.candidate_pool_size > P4L_HARD_CANDIDATE_CAP:
            hard_cap_violations += 1
        p4._append_private_jsonl(private_path, {
            "schema_version": "bea_v1_p4l_private_arm_outcome.v1",
            "source_phase": "P4L-VALIDATION",
            "arm_name": arm_name,
            "denominator_index_private": i,
            "gold_file_available": rr.gold_file_available,
            "first_gold_file_rank": rr.first_gold_file_rank,
            "candidate_pool_size": rr.candidate_pool_size,
            "retrieval_latency_seconds": rr.retrieval_latency_seconds,
            "hard_cap_hit": rr.hard_cap_hit,
            "unique_file_cap_hit": rr.unique_file_cap_hit,
            "extra_depth_actions_executed": getattr(rr, "extra_depth_actions_executed", 0),
            "config_hash": p4._config_hash(),
        })
    n = len(denom)
    mean_latency = (total_latency / n) if n else 0.0
    mean_pool = (sum(pool_sizes) / len(pool_sizes)) if pool_sizes else 0.0
    return {
        "arm_name": arm_name,
        "denominator_count": n,
        "file_reach_count": reached,
        "file_reach_rate": round(reached / n, 6) if n else 0.0,
        "mean_latency_seconds": round(mean_latency, 6),
        "mean_candidate_pool_size": round(mean_pool, 6),
        "hard_cap_violation_count": hard_cap_violations,
        "retrieval_error_count": errors,
        "first_gold_file_rank_mean": round(sum(first_gold_ranks) / len(first_gold_ranks), 6) if first_gold_ranks else 0.0,
    }


def _run_scheduler_validation(
    *, openlocus_bin: str, denom: list[dict[str, Any]],
    private_path: Path, fcc: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run all 4 frozen arms on the locked denominator.

    Returns ``(arm_metrics_list, validation_meta)``.
    """
    arm_metrics: list[dict[str, Any]] = []
    for arm in P4L_ARMS:
        am = _run_arm_on_denominator(
            arm_name=arm, openlocus_bin=openlocus_bin, denom=denom,
            private_path=private_path, fcc=fcc)
        arm_metrics.append(am)
    # Compute cross-arm deltas.
    by_arm = {a["arm_name"]: a for a in arm_metrics}
    baseline = by_arm.get("baseline_current_candidate_pool", {})
    p2 = by_arm.get("p2_depth_only_reference", {})
    p3 = by_arm.get("p3_constrained_depth_policy_reference", {})
    p4_arm = by_arm.get("p4_latency_aware_action_scheduler_frozen", {})
    baseline_reach = int(baseline.get("file_reach_count", 0))
    p2_reach = int(p2.get("file_reach_count", 0))
    p3_reach = int(p3.get("file_reach_count", 0))
    p4_reach = int(p4_arm.get("file_reach_count", 0))
    p2_gain = max(0, p2_reach - baseline_reach)
    p4_delta_vs_baseline = p4_reach - baseline_reach
    # P4 retained-gain ratio: P4's improvement over baseline / P2's improvement over baseline
    p4_retained_gain_ratio = round(p4_delta_vs_baseline / p2_gain, 6) if p2_gain > 0 else 0.0
    p3_latency = float(p3.get("mean_latency_seconds", 0.0))
    p4_latency = float(p4_arm.get("mean_latency_seconds", 0.0))
    p4_vs_p3_latency_ratio = round(p4_latency / p3_latency, 6) if p3_latency > 0 else 0.0
    p4_latency_reduction = round((p3_latency - p4_latency) / p3_latency, 6) if p3_latency > 0 else 0.0
    baseline_pool = float(baseline.get("mean_candidate_pool_size", 0.0))
    p4_pool = float(p4_arm.get("mean_candidate_pool_size", 0.0))
    p4_pool_growth_ratio = round(p4_pool / baseline_pool, 6) if baseline_pool > 0 else 0.0
    p4_hard_cap_violations = int(p4_arm.get("hard_cap_violation_count", 0))
    reference_hard_cap_violations = sum(
        int(a.get("hard_cap_violation_count", 0))
        for a in arm_metrics
        if a.get("arm_name") != "p4_latency_aware_action_scheduler_frozen")
    all_arm_hard_cap_violations = p4_hard_cap_violations + reference_hard_cap_violations
    validation_meta = {
        "p4_delta_vs_baseline_reach": int(p4_delta_vs_baseline),
        "p4_retained_gain_ratio": p4_retained_gain_ratio,
        "p4_vs_p3_latency_ratio": p4_vs_p3_latency_ratio,
        "p4_latency_reduction_vs_p3": p4_latency_reduction,
        "p4_pool_growth_ratio": p4_pool_growth_ratio,
        "hard_cap_violation_count_total": int(p4_hard_cap_violations),
        "p4_treatment_hard_cap_violation_count": int(p4_hard_cap_violations),
        "reference_arm_hard_cap_violation_count_total": int(reference_hard_cap_violations),
        "all_arm_hard_cap_violation_count_total": int(all_arm_hard_cap_violations),
        "baseline_reach": baseline_reach,
        "p2_reach": p2_reach,
        "p3_reach": p3_reach,
        "p4_reach": p4_reach,
        "p2_gain_over_baseline": int(p2_gain),
    }
    return arm_metrics, validation_meta


def _compute_subgroup_records(
    denom: list[dict[str, Any]], arm_metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per-source/per-language subgroup aggregate records (counts only)."""
    counts: dict[tuple[str, str], int] = {}
    for rec in denom:
        key = (str(rec.get("source_frame", "")), str(rec.get("language", "")))
        counts[key] = counts.get(key, 0) + 1
    return [{
        "source_frame": sf,
        "language": lang,
        "denominator_count": int(cnt),
    } for (sf, lang), cnt in sorted(counts.items())]


def _stop_go_records(
    *, recon_meta: dict[str, Any], validation_meta: dict[str, Any],
    blocking_failure_count: int, exact_prior_exclusion_used: bool,
    arms_executed: bool, subgroup_collapse: bool,
) -> list[dict[str, Any]]:
    locked_count = int(recon_meta.get("non_python_locked_count", 0))
    python_count = int(recon_meta.get("python_locked_count", 0))
    p4j_count = int(recon_meta.get("p4j_reconstructed_upper_bound_count", python_count + locked_count))
    split_match = (
        p4j_count == P4K_P4J_RECONSTRUCTED_COUNT
        and python_count == P4K_P4J_PYTHON_SPLIT
        and locked_count == P4K_P4J_NON_PYTHON_SPLIT
    )
    denom_match = (locked_count == P4K_LOCKED_DENOMINATOR_COUNT and split_match)
    if not exact_prior_exclusion_used:
        decision = "fail_schema_contract"
        reason = "fd1_exact_prior_exclusion_required_for_locked_denominator"
    elif blocking_failure_count > 0:
        decision = "fail_schema_contract"
        reason = "blocking_failure_present_cannot_validate_scheduler"
    elif not denom_match:
        decision = "no_go_p4l_locked_denominator_unavailable"
        reason = (f"locked_denominator_count={locked_count}; expected={P4K_LOCKED_DENOMINATOR_COUNT};"
                  f"p4j_reconstructed={p4j_count}; expected_p4j={P4K_P4J_RECONSTRUCTED_COUNT};"
                  f"python_split={python_count}; expected_python={P4K_P4J_PYTHON_SPLIT}")
    elif not arms_executed:
        decision = "fail_schema_contract"
        reason = "scheduler_arms_not_executed"
    elif subgroup_collapse:
        decision = "no_go_p4l_locked_non_python_scheduler_validation_failed"
        reason = "subgroup_collapse_detected"
    else:
        vm = validation_meta
        p4_reach = vm.get("p4_reach", 0)
        baseline_reach = vm.get("baseline_reach", 0)
        p4_retained = vm.get("p4_retained_gain_ratio", 0.0)
        p4_latency_ratio = vm.get("p4_vs_p3_latency_ratio", 0.0)
        p4_latency_reduction = vm.get("p4_latency_reduction_vs_p3", 0.0)
        p4_pool_growth = vm.get("p4_pool_growth_ratio", 0.0)
        hard_cap = vm.get("p4_treatment_hard_cap_violation_count", vm.get("hard_cap_violation_count_total", 0))
        gates_pass = (
            p4_reach > baseline_reach
            and p4_retained >= P4L_REACH_PRESERVATION_DEPTH_RATIO
            and p4_latency_ratio <= P4L_LATENCY_MULT_MAX
            and p4_latency_reduction >= P4L_LATENCY_VS_P3_IMPROVEMENT_MIN
            and p4_pool_growth <= P4L_POOL_MULT_MAX
            and hard_cap <= P4L_HARD_CAP_VIOLATION_MAX
        )
        if gates_pass:
            decision = "bea_v1_p4l_locked_non_python_scheduler_validation_pass"
            reason = "frozen_p4_scheduler_generalizes_to_locked_non_python_denominator"
        else:
            decision = "no_go_p4l_locked_non_python_scheduler_validation_failed"
            reason = (f"p4_reach={p4_reach};baseline={baseline_reach};"
                      f"retained={p4_retained};latency_ratio={p4_latency_ratio};"
                      f"latency_reduction={p4_latency_reduction};pool_growth={p4_pool_growth};"
                      f"p4_hard_cap={hard_cap}")
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "locked_denominator_count": int(locked_count),
        "expected_locked_denominator_count": P4K_LOCKED_DENOMINATOR_COUNT,
        "p4j_reconstructed_upper_bound_count": int(p4j_count),
        "expected_p4j_reconstructed_upper_bound_count": P4K_P4J_RECONSTRUCTED_COUNT,
        "p4j_reconstructed_python_count": int(python_count),
        "expected_p4j_reconstructed_python_count": P4K_P4J_PYTHON_SPLIT,
        "p4j_reconstructed_non_python_count": int(locked_count),
        "expected_p4j_reconstructed_non_python_count": P4K_P4J_NON_PYTHON_SPLIT,
        "denominator_exact_match": bool(denom_match),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "scheduler_arms_executed": bool(arms_executed),
        "p4l_locked_scheduler_validation_executed": bool(arms_executed),
        "p4_reach": int(validation_meta.get("p4_reach", 0)),
        "baseline_reach": int(validation_meta.get("baseline_reach", 0)),
        "p4_retained_gain_ratio": float(validation_meta.get("p4_retained_gain_ratio", 0.0)),
        "p4_vs_p3_latency_ratio": float(validation_meta.get("p4_vs_p3_latency_ratio", 0.0)),
        "p4_latency_reduction_vs_p3": float(validation_meta.get("p4_latency_reduction_vs_p3", 0.0)),
        "p4_pool_growth_ratio": float(validation_meta.get("p4_pool_growth_ratio", 0.0)),
        "hard_cap_violation_count_total": int(validation_meta.get("hard_cap_violation_count_total", 0)),
        "p4_treatment_hard_cap_violation_count": int(validation_meta.get("p4_treatment_hard_cap_violation_count", validation_meta.get("hard_cap_violation_count_total", 0))),
        "reference_arm_hard_cap_violation_count_total": int(validation_meta.get("reference_arm_hard_cap_violation_count_total", 0)),
        "all_arm_hard_cap_violation_count_total": int(validation_meta.get("all_arm_hard_cap_violation_count_total", validation_meta.get("hard_cap_violation_count_total", 0))),
        "subgroup_collapse_detected": bool(subgroup_collapse),
        "locked_p4_validation_authorized": False,
        "future_locked_p4_validation_authorized": False,
        "frozen_p4_rerun_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "method_winner_authorized": False,
        "broad_retrieval_expansion_authorized": False,
    }]


def _gate_records(
    *, recon_meta: dict[str, Any], validation_meta: dict[str, Any],
    blocking_failure_count: int, exact_prior_exclusion_used: bool,
    arms_executed: bool, subgroup_collapse: bool, forbidden_scan_pass: bool,
) -> list[dict[str, Any]]:
    def g(name: str, value: float, relation: str, threshold: float, passed: bool) -> dict[str, Any]:
        return {"gate": name, "value": round(float(value), 6), "threshold_relation": relation, "threshold_value": round(float(threshold), 6), "passed": bool(passed)}
    locked_count = int(recon_meta.get("non_python_locked_count", 0))
    python_count = int(recon_meta.get("python_locked_count", 0))
    p4j_count = int(recon_meta.get("p4j_reconstructed_upper_bound_count", python_count + locked_count))
    p4_retained = float(validation_meta.get("p4_retained_gain_ratio", 0.0))
    p4_latency_ratio = float(validation_meta.get("p4_vs_p3_latency_ratio", 0.0))
    p4_latency_reduction = float(validation_meta.get("p4_latency_reduction_vs_p3", 0.0))
    p4_pool_growth = float(validation_meta.get("p4_pool_growth_ratio", 0.0))
    hard_cap = int(validation_meta.get("p4_treatment_hard_cap_violation_count", validation_meta.get("hard_cap_violation_count_total", 0)))
    p4_reach = int(validation_meta.get("p4_reach", 0))
    baseline_reach = int(validation_meta.get("baseline_reach", 0))
    return [
        g("p4j_reconstructed_upper_bound_exact", p4j_count, "==", P4K_P4J_RECONSTRUCTED_COUNT, p4j_count == P4K_P4J_RECONSTRUCTED_COUNT),
        g("p4j_reconstructed_python_split_exact", python_count, "==", P4K_P4J_PYTHON_SPLIT, python_count == P4K_P4J_PYTHON_SPLIT),
        g("locked_denominator_non_python_exact", locked_count, "==", P4K_LOCKED_DENOMINATOR_COUNT, locked_count == P4K_LOCKED_DENOMINATOR_COUNT),
        g("exact_prior_exclusion_used", 1.0 if exact_prior_exclusion_used else 0.0, "boolean", 1.0, bool(exact_prior_exclusion_used)),
        g("scheduler_arms_executed", 1.0 if arms_executed else 0.0, "boolean", 1.0, bool(arms_executed)),
        g("p4_reach_gt_baseline", p4_reach, ">", baseline_reach, p4_reach > baseline_reach),
        g("p4_retained_gain_ratio_min", p4_retained, ">=", P4L_REACH_PRESERVATION_DEPTH_RATIO, p4_retained >= P4L_REACH_PRESERVATION_DEPTH_RATIO),
        g("p4_latency_ratio_max", p4_latency_ratio, "<=", P4L_LATENCY_MULT_MAX, p4_latency_ratio <= P4L_LATENCY_MULT_MAX),
        g("p4_latency_reduction_min", p4_latency_reduction, ">=", P4L_LATENCY_VS_P3_IMPROVEMENT_MIN, p4_latency_reduction >= P4L_LATENCY_VS_P3_IMPROVEMENT_MIN),
        g("p4_pool_growth_max", p4_pool_growth, "<=", P4L_POOL_MULT_MAX, p4_pool_growth <= P4L_POOL_MULT_MAX),
        g("p4_treatment_hard_cap_violations_zero", hard_cap, "==", P4L_HARD_CAP_VIOLATION_MAX, hard_cap == P4L_HARD_CAP_VIOLATION_MAX),
        g("subgroup_collapse_guard", 0.0 if subgroup_collapse else 1.0, "boolean_false", 0.0, not subgroup_collapse),
        g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0, "boolean", 1.0, forbidden_scan_pass),
        g("provider_calls_made", 0.0, "boolean_false", 0.0, True),
        g("latency_in_candidate_relevance", 0.0, "boolean_false", 0.0, True),
        g("selector_or_reranker_executed", 0.0, "boolean_false", 0.0, True),
        g("method_winner_logic_executed", 0.0, "boolean_false", 0.0, True),
        g("parameter_tuning_executed", 0.0, "boolean_false", 0.0, True),
        g("blocking_failure_count", blocking_failure_count, "==", 0.0, blocking_failure_count == 0),
    ]


def _failure_category_count_records(fcc: dict[str, int]) -> list[dict[str, Any]]:
    return [{"failure_category": str(k), "count": int(v)} for k, v in sorted(fcc.items())]


def _blocking_failure_count(fcc: dict[str, int]) -> int:
    return sum(int(fcc.get(cat, 0)) for cat in BLOCKING_FAILURE_CATEGORIES)


def _private_manifest_records(fd1_artifact: dict[str, Any], extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return p4._private_manifest_records(fd1_artifact, "fd1_committed_artifact", extra_manifests=extra or [])


def _source_run_records(
    *, fd1_schema_version: str, fd1_source_artifact_hash: str,
    fd1_status: str, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    pt: Any, rav: Any,
    p4h_artifact: dict[str, Any] | None, p4i_artifact: dict[str, Any] | None,
    p4j_artifact: dict[str, Any] | None, p4k_artifact: dict[str, Any] | None,
    audit_match: bool, audit_mismatch_reason: str,
) -> list[dict[str, Any]]:
    p4h_art = p4h_artifact or {}
    p4i_art = p4i_artifact or {}
    p4j_art = p4j_artifact or {}
    p4k_art = p4k_artifact or {}
    return [{
        "source_phase": "BEA-v1-P4K",
        "source_checkpoint": P4K_RESULT_CHECKPOINT,
        "source_status": P4K_RESULT_STATUS,
        "source_ci_run_id": P4K_CI_RUN_ID,
        "source_locked_denominator_count": P4K_LOCKED_DENOMINATOR_COUNT,
        "audit_objective": "validate_frozen_p4_scheduler_generalizes_to_locked_non_python_denominator",
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": "locked_non_python_scheduler_validation.v1",
        "locked_denominator_count": P4K_LOCKED_DENOMINATOR_COUNT,
        "p4k_p4h_reconstructed_count": P4K_P4H_RECONSTRUCTED_COUNT,
        "p4k_p4i_reconstructed_count": P4K_P4I_RECONSTRUCTED_COUNT,
        "p4k_p4j_reconstructed_count": P4K_P4J_RECONSTRUCTED_COUNT,
        "p4k_p4j_python_split": P4K_P4J_PYTHON_SPLIT,
        "p4k_p4j_non_python_split": P4K_P4J_NON_PYTHON_SPLIT,
        "p4k_p4j_overlap": P4K_P4J_OVERLAP,
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
        "replay_protocol_match": bool(audit_match),
        "replay_mismatch_reason": audit_mismatch_reason,
        "p4h_artifact_read": bool(p4h_art),
        "p4i_artifact_read": bool(p4i_art),
        "p4j_artifact_read": bool(p4j_art),
        "p4k_artifact_read": bool(p4k_art),
        "p4k_committed_locked_count": int(p4k_art.get("locked_cross_source_reservoir_count", P4K_LOCKED_DENOMINATOR_COUNT) or 0),
        "p4k_committed_status": str(p4k_art.get("status", "") or ""),
        "v1_p4_result_checkpoint": V1_P4_RESULT_CHECKPOINT,
        "v1_p4_result_status": V1_P4_RESULT_STATUS,
        "config_hash": p4._config_hash(),
    }]


FORBIDDEN_PUBLIC_KEYS = frozenset(p4h.FORBIDDEN_PUBLIC_KEYS | {
    "denominator_records_private", "denominator_rows_private",
    "denominator_private_paths", "arm_outcomes_private",
    "scheduler_traces_private", "reconstruction_private_path",
    "validation_private_path", "validation_jsonl_path",
    "exact_keys_private", "canonical_keys", "overlap_keys_private",
    "locked_keys_private", "python_ordinal_private",
    "repo_url_private", "base_commit_private", "gold_paths_private",
    "candidate_paths_private", "query_private",
    "p4h_exact_keys", "p4i_exact_keys", "p4j_exact_keys",
    "self_test_checks", "self_test_details", "self_test_list",
    "checks", "check_list", "hard_gates",
})


def _scan_v1_p4l(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sub = f"{path}.{ks}"
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_v1_p4l_public_key", "path": sub})
                if isinstance(v, str) and len(v) > 240 and ks not in {"stop_go_reason", "audit_objective"}:
                    violations.append({"category": "long_string", "path": sub})
                walk(v, sub)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(obj)
    return violations


def _v1_p4l_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p4l(obj)
    cats: dict[str, int] = {}
    for v in violations:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    violation_categories = [{"category": c, "count": int(n)} for c, n in sorted(cats.items())]
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": violation_categories,
    }


def _enforce_v1_p4l_no_forbidden(obj: Any) -> None:
    if _v1_p4l_forbidden_scan_summary(obj)["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


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
    for m in manifests:
        if not isinstance(m, dict):
            return False
        for k in m:
            if str(k) not in allowed and str(k) not in {"manifest_name"}:
                if str(k).endswith("_hash") and str(k) != "manifest_hash":
                    return False
        if "manifest_hash" in m and not isinstance(m["manifest_hash"], str):
            return False
        if "record_count" in m and not isinstance(m["record_count"], int):
            return False
    return True


def _base_report(
    *, status: str, failure_reason_category: str, self_test_passed: bool,
    self_test_checks_total: int, self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any] | None = None,
    fd1_schema: str = "", fd1_hash: str = "", pt: Any = None,
    rav: Any = None, p4h_artifact: dict[str, Any] | None = None,
    p4i_artifact: dict[str, Any] | None = None,
    p4j_artifact: dict[str, Any] | None = None,
    p4k_artifact: dict[str, Any] | None = None,
    recon_meta: dict[str, Any] | None = None,
    arm_metrics: list[dict[str, Any]] | None = None,
    validation_meta: dict[str, Any] | None = None,
    subgroup_records: list[dict[str, Any]] | None = None,
    retrieval_policy_executed: bool = False, audit_match: bool = False,
    audit_mismatch_reason: str = "", fcc_in: dict[str, int] | None = None,
    extra_manifests: list[dict[str, Any]] | None = None,
    aggregate_runtime_seconds: float = 0.0,
) -> dict[str, Any]:
    fd1_artifact = fd1_artifact or {}
    recon_meta = recon_meta or {"reconstructed": False, "non_python_locked_count": 0, "python_locked_count": 0, "p4j_reconstructed_upper_bound_count": 0, "exact_prior_exclusion_used": False}
    arm_metrics = arm_metrics or []
    validation_meta = validation_meta or {}
    subgroup_records = subgroup_records or []
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
    exact_prior_exclusion_used = bool(recon_meta.get("exact_prior_exclusion_used", False))
    blocking = _blocking_failure_count(fcc)
    arms_executed = bool(arm_metrics) and all(a.get("denominator_count", 0) > 0 or a.get("retrieval_error_count", 0) > 0 for a in arm_metrics) if arm_metrics else False
    # subgroup collapse guard: pass if there are at least 2 distinct (source_frame, language) subgroups each with >=2 records
    subgroup_collapse = False
    if subgroup_records:
        qualifying = sum(1 for r in subgroup_records if r.get("denominator_count", 0) >= 2)
        subgroup_collapse = qualifying < 2
    stop_go = _stop_go_records(
        recon_meta=recon_meta, validation_meta=validation_meta,
        blocking_failure_count=blocking, exact_prior_exclusion_used=exact_prior_exclusion_used,
        arms_executed=arms_executed, subgroup_collapse=subgroup_collapse)
    if int(fcc.get("network_required_but_disabled", 0) or 0) > 0:
        stop_go = [{
            **stop_go[0],
            "stop_go_decision": "unavailable_with_reason",
            "stop_go_reason": "network_required_but_disabled",
        }]
    if status == "auto":
        if blocking > 0:
            status = "fail_schema_contract"
        elif stop_go[0]["stop_go_decision"] in STATUSES:
            status = stop_go[0]["stop_go_decision"]
        else:
            status = "no_go_p4l_locked_non_python_scheduler_validation_failed"
    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true.update({
        "fd1_artifact_read": bool(fd1_artifact),
        "fd1_private_decomposition_parsed": fd1_private_parsed,
        "fd1_private_decomposition_replay_supplied": bool(rav.supplied if rav else False),
        "fd1_private_decomposition_replay_validated": replay_validated,
        "fd1_private_decomposition_replay_executed_by_workflow": bool(rav.supplied and rav.validated) if rav else False,
        "p4h_artifact_read": bool(p4h_artifact),
        "p4i_artifact_read": bool(p4i_artifact),
        "p4j_artifact_read": bool(p4j_artifact),
        "p4k_artifact_read": bool(p4k_artifact),
        "retrieval_policy_executed": bool(retrieval_policy_executed or arms_executed),
        "p2_depth_only_reference_executed": arms_executed,
        "p3_constrained_depth_policy_reference_executed": arms_executed,
        "p4_latency_aware_action_scheduler_executed": arms_executed,
    })
    locked_count = int(recon_meta.get("non_python_locked_count", 0))
    python_count = int(recon_meta.get("python_locked_count", 0))
    p4j_count = int(recon_meta.get("p4j_reconstructed_upper_bound_count", python_count + locked_count))
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
        "policy_arms": list(P4L_ARMS),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": "locked_non_python_scheduler_validation.v1",
        "records_decomposed": int(fd1_records),
        "private_manifest_record_count": int(fd1_manifest_count),
        "failure_reason_category": failure_reason_category,
        "locked_denominator_count": locked_count,
        "expected_locked_denominator_count": P4K_LOCKED_DENOMINATOR_COUNT,
        "p4j_reconstructed_upper_bound_count": int(p4j_count),
        "expected_p4j_reconstructed_upper_bound_count": P4K_P4J_RECONSTRUCTED_COUNT,
        "p4j_reconstructed_python_count": int(python_count),
        "expected_p4j_reconstructed_python_count": P4K_P4J_PYTHON_SPLIT,
        "p4j_reconstructed_non_python_count": int(locked_count),
        "expected_p4j_reconstructed_non_python_count": P4K_P4J_NON_PYTHON_SPLIT,
        "denominator_exact_match": bool(locked_count == P4K_LOCKED_DENOMINATOR_COUNT and python_count == P4K_P4J_PYTHON_SPLIT and p4j_count == P4K_P4J_RECONSTRUCTED_COUNT),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "scheduler_arms_executed": bool(arms_executed),
        "p4l_locked_scheduler_validation_executed": bool(arms_executed),
        "source_run_records": _source_run_records(fd1_schema_version=fd1_schema, fd1_source_artifact_hash=fd1_hash, fd1_status=fd1_status, fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4i_artifact=p4i_artifact, p4j_artifact=p4j_artifact, p4k_artifact=p4k_artifact, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason),
        "arm_metrics_records": arm_metrics,
        "subgroup_records": subgroup_records,
        "stop_go_records": stop_go,
        "gate_records": _gate_records(recon_meta=recon_meta, validation_meta=validation_meta, blocking_failure_count=blocking, exact_prior_exclusion_used=exact_prior_exclusion_used, arms_executed=arms_executed, subgroup_collapse=subgroup_collapse, forbidden_scan_pass=True),
        "private_manifest_records": _private_manifest_records(fd1_artifact, extra_manifests),
        "failure_category_count_records": _failure_category_count_records(fcc),
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "p4_delta_vs_baseline_reach": int(validation_meta.get("p4_delta_vs_baseline_reach", 0)),
        "p4_retained_gain_ratio": float(validation_meta.get("p4_retained_gain_ratio", 0.0)),
        "p4_vs_p3_latency_ratio": float(validation_meta.get("p4_vs_p3_latency_ratio", 0.0)),
        "p4_latency_reduction_vs_p3": float(validation_meta.get("p4_latency_reduction_vs_p3", 0.0)),
        "p4_pool_growth_ratio": float(validation_meta.get("p4_pool_growth_ratio", 0.0)),
        "hard_cap_violation_count_total": int(validation_meta.get("hard_cap_violation_count_total", 0)),
        "p4_treatment_hard_cap_violation_count": int(validation_meta.get("p4_treatment_hard_cap_violation_count", validation_meta.get("hard_cap_violation_count_total", 0))),
        "reference_arm_hard_cap_violation_count_total": int(validation_meta.get("reference_arm_hard_cap_violation_count_total", 0)),
        "all_arm_hard_cap_violation_count_total": int(validation_meta.get("all_arm_hard_cap_violation_count_total", validation_meta.get("hard_cap_violation_count_total", 0))),
        "private_key_hashes_publicly_serialized": False,
        **DEFAULT_FALSE_FLAGS,
        **safe_true,
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
            "scheduler_validation_claimed": bool(status == "bea_v1_p4l_locked_non_python_scheduler_validation_pass"),
            "retrieval_expansion_claimed": False,
            "selector_or_reranker_executed": False,
            "is_full_external_benchmark_evaluation": False,
            "is_locked_non_python_scheduler_validation": True,
            "p4l_locked_scheduler_validation_executed": bool(arms_executed),
            "future_locked_p4_validation_authorized": False,
            "is_latency_in_relevance": False,
            "signal_strength": "bea_v1_p4l_locked_non_python_scheduler_validation_aggregate_only",
        },
    }
    scan = _v1_p4l_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["stop_go_records"] = [{
            **stop_go[0],
            "stop_go_decision": "fail_forbidden_scan",
            "stop_go_reason": "forbidden_content_leak_blocked",
        }]
    return report


def _run_validation(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    fd1_artifact_path: Path, fd1_private_decomposition_jsonl: Path | None,
    fd1_replay_artifact: Path | None, p4h_artifact_path: Path | None,
    p4i_artifact_path: Path | None, p4j_artifact_path: Path | None,
    p4k_artifact_path: Path | None, enable_network: bool,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    start = time.perf_counter()
    fd1_artifact, fd1_schema, fd1_hash, fd1_status = p4._load_committed_artifact(fd1_artifact_path)
    if fd1_status != "pass":
        fcc["fd1_artifact_missing" if fd1_status == "artifact_missing" else "fd1_artifact_parse_failed"] = 1
        return _base_report(status="fail_schema_contract", failure_reason_category=fd1_status, self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fcc_in=fcc)
    p4h_artifact: dict[str, Any] = {}
    p4i_artifact: dict[str, Any] = {}
    p4j_artifact: dict[str, Any] = {}
    p4k_artifact: dict[str, Any] = {}
    for path, store in ((p4h_artifact_path, "p4h"), (p4i_artifact_path, "p4i"), (p4j_artifact_path, "p4j"), (p4k_artifact_path, "p4k")):
        if path is None:
            continue
        try:
            art, _, _, _ = p4._load_committed_artifact(path)
            if store == "p4h": p4h_artifact = art
            elif store == "p4i": p4i_artifact = art
            elif store == "p4j": p4j_artifact = art
            elif store == "p4k": p4k_artifact = art
        except Exception:
            pass
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
    if p4k_artifact:
        if p4k_artifact.get("status") != P4K_RESULT_STATUS:
            fcc["p4k_artifact_status_mismatch"] = 1; mismatch.append("p4k_artifact_status_mismatch")
        if int(p4k_artifact.get("locked_cross_source_reservoir_count", 0) or 0) != P4K_LOCKED_DENOMINATOR_COUNT:
            fcc["p4k_locked_count_mismatch"] = 1; mismatch.append("p4k_locked_count_mismatch")
        p4k_split_ok = (
            int(p4k_artifact.get("p4h_reconstructed_denominator_count", 0) or 0) == P4K_P4H_RECONSTRUCTED_COUNT
            and int(p4k_artifact.get("p4i_reconstructed_reservoir_count", 0) or 0) == P4K_P4I_RECONSTRUCTED_COUNT
            and int(p4k_artifact.get("p4j_reconstructed_upper_bound_count", 0) or 0) == P4K_P4J_RECONSTRUCTED_COUNT
            and int(p4k_artifact.get("p4j_reconstructed_python_count", 0) or 0) == P4K_P4J_PYTHON_SPLIT
            and int(p4k_artifact.get("p4j_reconstructed_non_python_count", 0) or 0) == P4K_P4J_NON_PYTHON_SPLIT
            and int(p4k_artifact.get("p4j_overlap_with_p4h_count", 0) or 0) == P4K_P4J_OVERLAP
            and int(p4k_artifact.get("p4j_overlap_with_p4i_count", 0) or 0) == P4K_P4J_OVERLAP
        )
        if not p4k_split_ok:
            fcc["p4k_split_or_overlap_mismatch"] = 1; mismatch.append("p4k_split_or_overlap_mismatch")
        if p4k_artifact.get("forbidden_scan", {}).get("status") != "pass":
            fcc["p4k_artifact_status_mismatch"] = 1; mismatch.append("p4k_forbidden_scan_mismatch")
    else:
        fcc["p4k_artifact_status_mismatch"] = 1; mismatch.append("p4k_artifact_missing")
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

    recon_meta: dict[str, Any] = {"reconstructed": False, "non_python_locked_count": 0, "python_locked_count": 0, "p4j_reconstructed_upper_bound_count": 0, "exact_prior_exclusion_used": False}
    arm_metrics: list[dict[str, Any]] = []
    validation_meta: dict[str, Any] = {}
    subgroup_records: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []

    if enable_network and audit_match and pt.computed and rav.validated:
        private_dir = _resolve_private_validation_dir()
        recon_path = private_dir / "bea_v1_p4l.private_reconstruction.jsonl"
        arm_path = private_dir / "bea_v1_p4l.private_arm_outcomes.jsonl"
        if recon_path.exists():
            recon_path.unlink()
        if arm_path.exists():
            arm_path.unlink()
        try:
            denom, recon_meta = _reconstruct_locked_denominator(
                openlocus_bin=openlocus_bin, pt=pt, private_path=recon_path, fcc=fcc)
            locked_count = int(recon_meta.get("non_python_locked_count", 0))
            python_count = int(recon_meta.get("python_locked_count", 0))
            p4j_count = int(recon_meta.get("p4j_reconstructed_upper_bound_count", python_count + locked_count))
            if (locked_count != P4K_LOCKED_DENOMINATOR_COUNT
                    or python_count != P4K_P4J_PYTHON_SPLIT
                    or p4j_count != P4K_P4J_RECONSTRUCTED_COUNT):
                fcc["locked_denominator_mismatch"] = 1
            if (locked_count == P4K_LOCKED_DENOMINATOR_COUNT
                    and python_count == P4K_P4J_PYTHON_SPLIT
                    and p4j_count == P4K_P4J_RECONSTRUCTED_COUNT
                    and denom):
                arm_metrics, validation_meta = _run_scheduler_validation(
                    openlocus_bin=openlocus_bin, denom=denom, private_path=arm_path, fcc=fcc)
                subgroup_records = _compute_subgroup_records(denom, arm_metrics)
                shutil.rmtree(private_dir / "repos", ignore_errors=True)
            recon_manifest = p4._private_file_manifest(
                recon_path, manifest_name="bea_v1_p4l_private_reconstruction_manifest",
                schema_version="bea_v1_p4l_private_reconstruction.v1")
            arm_manifest = p4._private_file_manifest(
                arm_path, manifest_name="bea_v1_p4l_private_arm_outcomes_manifest",
                schema_version="bea_v1_p4l_private_arm_outcome.v1")
            manifests.extend([recon_manifest, arm_manifest])
        except Exception:
            fcc["retrieval_policy_failed"] = 1
            fcc["unexpected_exception"] = 1
    elif enable_network:
        fcc["p4l_scan_not_attempted"] = 1
    else:
        fcc["network_required_but_disabled"] = 1
    return _base_report(status="auto", failure_reason_category="", self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fd1_artifact=fd1_artifact, fd1_schema=fd1_schema, fd1_hash=fd1_hash, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4i_artifact=p4i_artifact, p4j_artifact=p4j_artifact, p4k_artifact=p4k_artifact, recon_meta=recon_meta, arm_metrics=arm_metrics, validation_meta=validation_meta, subgroup_records=subgroup_records, retrieval_policy_executed=bool(arm_metrics), audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason, fcc_in=fcc, extra_manifests=manifests, aggregate_runtime_seconds=time.perf_counter() - start)


def _build_synthetic_recon_meta(
    *, non_python_locked: int = 272, exact_prior: bool = True,
) -> dict[str, Any]:
    python_locked = P4K_P4J_PYTHON_SPLIT if non_python_locked == P4K_P4J_NON_PYTHON_SPLIT else 0
    return {
        "reconstructed": True,
        "non_python_locked_count": non_python_locked,
        "python_locked_count": python_locked,
        "p4j_reconstructed_upper_bound_count": python_locked + non_python_locked,
        "p4j_reconstructed_python_count": python_locked,
        "p4j_reconstructed_non_python_count": non_python_locked,
        "exact_prior_exclusion_used": exact_prior,
        "fetched_total": 600,
        "attempted": 272,
        "prior_exact_excluded": 119,
        "by_construction_disjoint_records": 272,
        "parse_excluded": 0,
        "clone_excluded": 0,
        "baseline_reached": 0,
        "baseline_error": 0,
        "contextbench_fetched": 480,
        "contextbench_file_miss": 100,
        "repoqa_fetched": 120,
        "repoqa_file_miss": 172,
    }


def _build_synthetic_arm_metrics(
    *, baseline_reach: int = 100, p2_reach: int = 180, p3_reach: int = 175,
    p4_reach: int = 170, hard_cap: int = 0,
) -> list[dict[str, Any]]:
    def _arm(name: str, reach: int, latency: float, pool: float, hc: int = 0) -> dict[str, Any]:
        return {
            "arm_name": name,
            "denominator_count": 272,
            "file_reach_count": reach,
            "file_reach_rate": round(reach / 272, 6),
            "mean_latency_seconds": latency,
            "mean_candidate_pool_size": pool,
            "hard_cap_violation_count": hc,
            "retrieval_error_count": 0,
            "first_gold_file_rank_mean": 12.0,
        }
    return [
        _arm("baseline_current_candidate_pool", baseline_reach, 1.8, 20.0),
        _arm("p2_depth_only_reference", p2_reach, 3.6, 68.0),
        _arm("p3_constrained_depth_policy_reference", p3_reach, 3.645, 41.0),
        _arm("p4_latency_aware_action_scheduler_frozen", p4_reach, 2.0, 35.0, hard_cap),
    ]


def _build_synthetic_validation_meta(arm_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm = {a["arm_name"]: a for a in arm_metrics}
    baseline_reach = int(by_arm["baseline_current_candidate_pool"]["file_reach_count"])
    p2_reach = int(by_arm["p2_depth_only_reference"]["file_reach_count"])
    p3_reach = int(by_arm["p3_constrained_depth_policy_reference"]["file_reach_count"])
    p4_reach = int(by_arm["p4_latency_aware_action_scheduler_frozen"]["file_reach_count"])
    p2_gain = max(0, p2_reach - baseline_reach)
    p4_delta = p4_reach - baseline_reach
    p4_retained = round(p4_delta / p2_gain, 6) if p2_gain > 0 else 0.0
    p3_lat = float(by_arm["p3_constrained_depth_policy_reference"]["mean_latency_seconds"])
    p4_lat = float(by_arm["p4_latency_aware_action_scheduler_frozen"]["mean_latency_seconds"])
    p4_vs_p3 = round(p4_lat / p3_lat, 6) if p3_lat > 0 else 0.0
    p4_reduction = round((p3_lat - p4_lat) / p3_lat, 6) if p3_lat > 0 else 0.0
    baseline_pool = float(by_arm["baseline_current_candidate_pool"]["mean_candidate_pool_size"])
    p4_pool = float(by_arm["p4_latency_aware_action_scheduler_frozen"]["mean_candidate_pool_size"])
    p4_growth = round(p4_pool / baseline_pool, 6) if baseline_pool > 0 else 0.0
    p4_hard_cap = int(next((a.get("hard_cap_violation_count", 0) for a in arm_metrics if a.get("arm_name") == "p4_latency_aware_action_scheduler_frozen"), 0))
    reference_hard_cap = sum(int(a.get("hard_cap_violation_count", 0)) for a in arm_metrics if a.get("arm_name") != "p4_latency_aware_action_scheduler_frozen")
    return {
        "p4_delta_vs_baseline_reach": int(p4_delta),
        "p4_retained_gain_ratio": p4_retained,
        "p4_vs_p3_latency_ratio": p4_vs_p3,
        "p4_latency_reduction_vs_p3": p4_reduction,
        "p4_pool_growth_ratio": p4_growth,
        "hard_cap_violation_count_total": int(p4_hard_cap),
        "p4_treatment_hard_cap_violation_count": int(p4_hard_cap),
        "reference_arm_hard_cap_violation_count_total": int(reference_hard_cap),
        "all_arm_hard_cap_violation_count_total": int(p4_hard_cap + reference_hard_cap),
        "baseline_reach": baseline_reach,
        "p2_reach": p2_reach,
        "p3_reach": p3_reach,
        "p4_reach": p4_reach,
        "p2_gain_over_baseline": int(p2_gain),
    }


def _build_synthetic_subgroup_records() -> list[dict[str, Any]]:
    return [
        {"source_frame": "contextbench_all_languages", "language": "cpp", "denominator_count": 50},
        {"source_frame": "contextbench_all_languages", "language": "java", "denominator_count": 50},
        {"source_frame": "repoqa_non_python_languages", "language": "cpp", "denominator_count": 86},
        {"source_frame": "repoqa_non_python_languages", "language": "java", "denominator_count": 86},
    ]


METRIC_TABLE_KEYS = (
    "source_run_records", "arm_metrics_records", "subgroup_records",
    "stop_go_records", "gate_records", "private_manifest_records",
    "failure_category_count_records",
)


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("identity_schema", SCHEMA_VERSION == "bea_v1_p4l_locked_non_python_scheduler_validation.v1"))
    checks.append(_check("phase_p4l", PHASE == "BEA-v1-P4L"))
    checks.append(_check("claim_level_audit_only", CLAIM_LEVEL == "bea_v1_p4l_locked_non_python_scheduler_validation_only"))
    checks.append(_check("diagnostic_arm_baseline_only", DIAGNOSTIC_ARM == "current_bea_candidate_pool_replay"))
    checks.append(_check("arms_count_4", len(P4L_ARMS) == 4))
    checks.append(_check("arm_baseline_present", "baseline_current_candidate_pool" in P4L_ARMS))
    checks.append(_check("arm_p2_present", "p2_depth_only_reference" in P4L_ARMS))
    checks.append(_check("arm_p3_present", "p3_constrained_depth_policy_reference" in P4L_ARMS))
    checks.append(_check("arm_p4_frozen_present", "p4_latency_aware_action_scheduler_frozen" in P4L_ARMS))
    checks.append(_check("no_p5_in_arms", "p5" not in "|".join(P4L_ARMS).lower()))
    checks.append(_check("no_v1_a_in_arms", "v1_a" not in "|".join(P4L_ARMS).lower()))
    checks.append(_check("no_selector_in_arms", "selector" not in "|".join(P4L_ARMS).lower()))
    checks.append(_check("no_reranker_in_arms", "reranker" not in "|".join(P4L_ARMS).lower()))
    checks.append(_check("locked_denominator_272", P4K_LOCKED_DENOMINATOR_COUNT == 272))
    checks.append(_check("p4k_p4h_73", P4K_P4H_RECONSTRUCTED_COUNT == 73))
    checks.append(_check("p4k_p4i_73", P4K_P4I_RECONSTRUCTED_COUNT == 73))
    checks.append(_check("p4k_p4j_333", P4K_P4J_RECONSTRUCTED_COUNT == 333))
    checks.append(_check("p4k_p4j_python_61", P4K_P4J_PYTHON_SPLIT == 61))
    checks.append(_check("p4k_p4j_non_python_272", P4K_P4J_NON_PYTHON_SPLIT == 272))
    checks.append(_check("p4k_p4j_overlap_61", P4K_P4J_OVERLAP == 61))
    checks.append(_check("frozen_threshold_retained_ratio", P4L_REACH_PRESERVATION_DEPTH_RATIO == 0.75))
    checks.append(_check("frozen_threshold_latency_mult", P4L_LATENCY_MULT_MAX == 2.0))
    checks.append(_check("frozen_threshold_latency_improvement", P4L_LATENCY_VS_P3_IMPROVEMENT_MIN == 0.10))
    checks.append(_check("frozen_threshold_pool_mult", P4L_POOL_MULT_MAX == 4.0))
    checks.append(_check("frozen_threshold_hard_cap", P4L_HARD_CAP_VIOLATION_MAX == 0))
    checks.append(_check("latency_not_in_relevance_false", DEFAULT_FALSE_FLAGS["latency_in_candidate_relevance"] is False))
    checks.append(_check("no_selector_change", DEFAULT_FALSE_FLAGS["selector_or_reranker_changed"] is False))
    checks.append(_check("no_selector_executed_default", DEFAULT_FALSE_FLAGS["selector_or_reranker_executed"] is False))
    checks.append(_check("p5_authorized_false", DEFAULT_FALSE_FLAGS["p5_authorized"] is False))
    checks.append(_check("v1_a_authorized_false", DEFAULT_FALSE_FLAGS["v1_a_authorized"] is False))
    checks.append(_check("frozen_p4_rerun_authorized_false", DEFAULT_FALSE_FLAGS["frozen_p4_rerun_authorized"] is False))
    checks.append(_check("locked_p4_validation_authorized_false", DEFAULT_FALSE_FLAGS["locked_p4_validation_authorized"] is False))
    checks.append(_check("future_locked_p4_validation_authorized_false", DEFAULT_FALSE_FLAGS["future_locked_p4_validation_authorized"] is False))
    checks.append(_check("parameter_tuning_executed_false", DEFAULT_FALSE_FLAGS["parameter_tuning_executed"] is False))
    checks.append(_check("threshold_search_executed_false", DEFAULT_FALSE_FLAGS["threshold_search_executed"] is False))
    checks.append(_check("new_arms_added_false", DEFAULT_FALSE_FLAGS["new_arms_added"] is False))
    checks.append(_check("p2_p3_p4_arms_not_default_true", SAFE_TRUE_FLAGS["bea_v1_p4l_audit_evaluator_no_p5_selector"] is True))
    with tempfile.TemporaryDirectory(prefix="v1p4l_st_") as sd:
        td = Path(sd)
        priv = td / "bea_fd1.decomposition.jsonl"
        p4._build_synthetic_private_decomposition_jsonl(priv, gold_file_absent_count=199)
        pt = p4._parse_private_decomposition_jsonl(priv)
        p4._compute_file_selector_lower_bound(pt)
        checks.append(_check("synthetic_fd1_rows_86040", pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS))
        replay_path = td / "fd1_replay_report.json"
        p4._build_synthetic_fd1_replay_artifact(replay_path)
        rav = p4._validate_fd1_replay_artifact(replay_path, "a" * 64)
        fd1_art = p4._build_synthetic_fd1_artifact()
        p4h_art = {"status": P4H_RESULT_STATUS, "denominator_count": P4H_DENOMINATOR_COUNT}
        p4i_art = {"status": P4I_RESULT_STATUS, "denominator_count": P4I_RESERVOIR_COUNT}
        p4j_art = {"status": P4J_RESULT_STATUS, "reservoir_upper_bound_count": P4J_UPPER_BOUND_COUNT}
        p4k_art = {"status": P4K_RESULT_STATUS, "locked_cross_source_reservoir_count": P4K_LOCKED_DENOMINATOR_COUNT}
        recon_manifest = {"manifest_name": "bea_v1_p4l_private_reconstruction_manifest", "schema_version": "bea_v1_p4l_private_reconstruction.v1", "storage_class": "private_tmp_only", "record_count": 272, "records_written": True, "path_publicly_serialized": False, "manifest_hash": "f" * 64}
        arm_manifest = {"manifest_name": "bea_v1_p4l_private_arm_outcomes_manifest", "schema_version": "bea_v1_p4l_private_arm_outcome.v1", "storage_class": "private_tmp_only", "record_count": 272 * 4, "records_written": True, "path_publicly_serialized": False, "manifest_hash": "a" * 64}
        # --- Pass scenario ---
        recon_pass = _build_synthetic_recon_meta(non_python_locked=272)
        arms_pass = _build_synthetic_arm_metrics()
        vm_pass = _build_synthetic_validation_meta(arms_pass)
        sub_pass = _build_synthetic_subgroup_records()
        report_pass = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_pass, validation_meta=vm_pass, subgroup_records=sub_pass, audit_match=True, extra_manifests=[recon_manifest, arm_manifest], aggregate_runtime_seconds=0.5)
        for table in METRIC_TABLE_KEYS:
            checks.append(_check(f"table_{table}_is_list", isinstance(report_pass.get(table), list)))
        checks.append(_check("pass_status", report_pass.get("status") == "bea_v1_p4l_locked_non_python_scheduler_validation_pass"))
        checks.append(_check("pass_forbidden_scan", report_pass.get("forbidden_scan", {}).get("status") == "pass"))
        checks.append(_check("pass_locked_count_272", report_pass.get("locked_denominator_count") == 272))
        checks.append(_check("pass_p4j_count_333", report_pass.get("p4j_reconstructed_upper_bound_count") == 333))
        checks.append(_check("pass_python_split_61", report_pass.get("p4j_reconstructed_python_count") == 61))
        checks.append(_check("pass_non_python_split_272", report_pass.get("p4j_reconstructed_non_python_count") == 272))
        checks.append(_check("pass_denominator_exact", report_pass.get("denominator_exact_match") is True))
        checks.append(_check("pass_arms_executed", report_pass.get("scheduler_arms_executed") is True))
        checks.append(_check("pass_p4l_locked_scheduler_validation_executed_true", report_pass.get("p4l_locked_scheduler_validation_executed") is True))
        checks.append(_check("pass_p4_reach_gt_baseline", report_pass.get("p4_delta_vs_baseline_reach", 0) > 0))
        checks.append(_check("pass_p4_retained_ratio_ge_0_75", report_pass.get("p4_retained_gain_ratio", 0) >= 0.75))
        checks.append(_check("pass_p4_latency_ratio_le_2_0", report_pass.get("p4_vs_p3_latency_ratio", 99) <= 2.0))
        checks.append(_check("pass_p4_latency_reduction_ge_0_10", report_pass.get("p4_latency_reduction_vs_p3", 0) >= 0.10))
        checks.append(_check("pass_p4_pool_growth_le_4_0", report_pass.get("p4_pool_growth_ratio", 99) <= 4.0))
        checks.append(_check("pass_hard_cap_zero", report_pass.get("hard_cap_violation_count_total", 1) == 0))
        checks.append(_check("pass_hard_cap_p4_treatment_only", report_pass.get("p4_treatment_hard_cap_violation_count") == 0 and report_pass.get("reference_arm_hard_cap_violation_count_total") == 0))
        checks.append(_check("pass_authorization_flags_false", report_pass.get("stop_go_records", [{}])[0].get("p5_authorized") is False and report_pass.get("stop_go_records", [{}])[0].get("v1_a_authorized") is False and report_pass.get("stop_go_records", [{}])[0].get("runtime_promotion_authorized") is False and report_pass.get("stop_go_records", [{}])[0].get("method_winner_authorized") is False and report_pass.get("stop_go_records", [{}])[0].get("broad_retrieval_expansion_authorized") is False))
        checks.append(_check("pass_locked_p4_validation_authorized_false", report_pass.get("stop_go_records", [{}])[0].get("locked_p4_validation_authorized") is False))
        checks.append(_check("pass_stop_go_p4l_locked_scheduler_validation_executed_true", report_pass.get("stop_go_records", [{}])[0].get("p4l_locked_scheduler_validation_executed") is True))
        checks.append(_check("pass_future_locked_p4_validation_authorized_false", report_pass.get("stop_go_records", [{}])[0].get("future_locked_p4_validation_authorized") is False))
        checks.append(_check("pass_frozen_p4_rerun_false", report_pass.get("stop_go_records", [{}])[0].get("frozen_p4_rerun_authorized") is False))
        checks.append(_check("pass_subgroup_records_count_4", len(report_pass.get("subgroup_records", [])) == 4))
        checks.append(_check("pass_arm_metrics_count_4", len(report_pass.get("arm_metrics_records", [])) == 4))
        checks.append(_check("pass_retrieval_policy_executed_true", report_pass.get("retrieval_policy_executed") is True))
        checks.append(_check("pass_p2_depth_reference_executed_true", report_pass.get("p2_depth_only_reference_executed") is True))
        checks.append(_check("pass_p3_constrained_reference_executed_true", report_pass.get("p3_constrained_depth_policy_reference_executed") is True))
        checks.append(_check("pass_p4_latency_scheduler_executed_true", report_pass.get("p4_latency_aware_action_scheduler_executed") is True))
        # --- Failed scenario (P4 doesn't improve reach) ---
        arms_fail = _build_synthetic_arm_metrics(baseline_reach=100, p2_reach=180, p3_reach=175, p4_reach=90)
        vm_fail = _build_synthetic_validation_meta(arms_fail)
        report_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_fail, validation_meta=vm_fail, subgroup_records=sub_pass, audit_match=True, extra_manifests=[recon_manifest, arm_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("failed_status", report_fail.get("status") == "no_go_p4l_locked_non_python_scheduler_validation_failed"))
        checks.append(_check("failed_no_validation_auth", report_fail.get("stop_go_records", [{}])[0].get("locked_p4_validation_authorized") is False))
        # --- Denominator unavailable (count mismatch) ---
        recon_mismatch = _build_synthetic_recon_meta(non_python_locked=250)
        report_mismatch = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_mismatch, audit_match=True, extra_manifests=[recon_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("denominator_unavailable_status", report_mismatch.get("status") == "no_go_p4l_locked_denominator_unavailable"))
        checks.append(_check("denominator_unavailable_no_auth", report_mismatch.get("stop_go_records", [{}])[0].get("locked_p4_validation_authorized") is False))
        checks.append(_check("denominator_unavailable_arms_not_required", report_mismatch.get("p2_depth_only_reference_executed") is False and report_mismatch.get("p3_constrained_depth_policy_reference_executed") is False and report_mismatch.get("p4_latency_aware_action_scheduler_executed") is False))
        recon_split_mismatch = {**_build_synthetic_recon_meta(non_python_locked=272), "python_locked_count": 0, "p4j_reconstructed_upper_bound_count": 272}
        report_split_mismatch = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_split_mismatch, audit_match=True, extra_manifests=[recon_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("split_mismatch_denominator_unavailable", report_split_mismatch.get("status") == "no_go_p4l_locked_denominator_unavailable"))
        checks.append(_check("split_mismatch_denominator_exact_false", report_split_mismatch.get("denominator_exact_match") is False))
        report_count_drift = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta={**_build_synthetic_recon_meta(non_python_locked=273), "python_locked_count": 61, "p4j_reconstructed_upper_bound_count": 334}, audit_match=True, fcc_in={"locked_denominator_mismatch": 1}, extra_manifests=[recon_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("count_drift_denominator_unavailable_not_schema_fail", report_count_drift.get("status") == "no_go_p4l_locked_denominator_unavailable"))
        # --- Hard cap violation -> failed ---
        arms_hc = _build_synthetic_arm_metrics(hard_cap=5)
        vm_hc = _build_synthetic_validation_meta(arms_hc)
        report_hc = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_hc, validation_meta=vm_hc, subgroup_records=sub_pass, audit_match=True, extra_manifests=[recon_manifest, arm_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("hard_cap_failed_status", report_hc.get("status") == "no_go_p4l_locked_non_python_scheduler_validation_failed"))
        arms_ref_hc = _build_synthetic_arm_metrics(hard_cap=0)
        for arm in arms_ref_hc:
            if arm.get("arm_name") == "p2_depth_only_reference":
                arm["hard_cap_violation_count"] = 5
        vm_ref_hc = _build_synthetic_validation_meta(arms_ref_hc)
        report_ref_hc = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_ref_hc, validation_meta=vm_ref_hc, subgroup_records=sub_pass, audit_match=True, extra_manifests=[recon_manifest, arm_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("reference_hard_cap_not_gating_p4", report_ref_hc.get("status") == "bea_v1_p4l_locked_non_python_scheduler_validation_pass" and report_ref_hc.get("reference_arm_hard_cap_violation_count_total") == 5 and report_ref_hc.get("p4_treatment_hard_cap_violation_count") == 0))
        # --- Default no-network ---
        report_default = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="missing", network_mode="disabled_opt_in", fcc_in={"network_required_but_disabled": 1})
        checks.append(_check("default_unavailable_with_reason", report_default.get("status") == "unavailable_with_reason"))
        checks.append(_check("default_not_pass", report_default.get("status") != "bea_v1_p4l_locked_non_python_scheduler_validation_pass"))
        checks.append(_check("default_stop_go_unavailable", report_default.get("stop_go_records", [{}])[0].get("stop_go_decision") == "unavailable_with_reason"))
        # --- Blocking failures ---
        report_scan_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_pass, validation_meta=vm_pass, subgroup_records=sub_pass, audit_match=True, fcc_in={"p4l_scan_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("scan_failure_fail_closed", report_scan_fail.get("status") == "fail_schema_contract"))
        report_clone_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_pass, validation_meta=vm_pass, subgroup_records=sub_pass, audit_match=True, fcc_in={"raw_denominator_clone_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("clone_failure_fail_closed", report_clone_fail.get("status") == "fail_schema_contract"))
        report_asset_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_pass, validation_meta=vm_pass, subgroup_records=sub_pass, audit_match=True, fcc_in={"cross_source_asset_download_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("asset_failure_fail_closed", report_asset_fail.get("status") == "fail_schema_contract"))
        report_parse_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_pass, validation_meta=vm_pass, subgroup_records=sub_pass, audit_match=True, fcc_in={"raw_denominator_parse_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("raw_parse_failure_fail_closed", report_parse_fail.get("status") == "fail_schema_contract"))
        report_p4k_mismatch = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta=recon_pass, arm_metrics=arms_pass, validation_meta=vm_pass, subgroup_records=sub_pass, audit_match=True, fcc_in={"p4k_split_or_overlap_mismatch": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("p4k_mismatch_fail_closed", report_p4k_mismatch.get("status") == "fail_schema_contract"))
        report_exact_missing = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta={**recon_pass, "exact_prior_exclusion_used": False}, arm_metrics=arms_pass, validation_meta=vm_pass, subgroup_records=sub_pass, audit_match=True, fcc_in={"locked_denominator_mismatch": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("exact_prior_missing_fail_closed", report_exact_missing.get("status") == "fail_schema_contract"))
        report_not_attempted = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, p4k_artifact=p4k_art, recon_meta={"reconstructed": False, "non_python_locked_count": 0, "exact_prior_exclusion_used": False}, audit_match=True, fcc_in={"p4l_scan_not_attempted": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("not_attempted_fail_closed", report_not_attempted.get("status") == "fail_schema_contract"))
        # --- Public shape / privacy ---
        checks.append(_check("public_shape_no_dynamic_dicts", _has_dynamic_dict(report_pass) is False))
        checks.append(_check("manifest_fields_safe", _manifest_fields_safe(report_pass.get("private_manifest_records", [])) is True))
        manifest_has_hash = any(m.get("manifest_hash") for m in report_pass.get("private_manifest_records", []) if isinstance(m, dict))
        checks.append(_check("manifest_has_provenance_hash", manifest_has_hash is True))
        checks.append(_check("manifest_no_private_paths", all(m.get("path_publicly_serialized") is False for m in report_pass.get("private_manifest_records", []) if isinstance(m, dict))))
        # --- Forbidden scanner ---
        leaked = dict(report_pass)
        leaked["private_record_id"] = "leak"
        checks.append(_check("scanner_rejects_private_record_id", _v1_p4l_forbidden_scan_summary(leaked)["status"] == "fail"))
        leaked2 = dict(report_pass)
        leaked2["denominator_records_private"] = ["leak"]
        checks.append(_check("scanner_rejects_denominator_private", _v1_p4l_forbidden_scan_summary(leaked2)["status"] == "fail"))
        leaked3 = dict(report_pass)
        leaked3["scheduler_traces_private"] = "leak"
        checks.append(_check("scanner_rejects_scheduler_traces", _v1_p4l_forbidden_scan_summary(leaked3)["status"] == "fail"))
        leaked4 = dict(report_pass)
        leaked4["self_test_checks"] = ["leak"]
        checks.append(_check("scanner_rejects_self_test_checks_list", _v1_p4l_forbidden_scan_summary(leaked4)["status"] == "fail"))
        leaked5 = dict(report_pass)
        leaked5["canonical_keys"] = "leak"
        checks.append(_check("scanner_rejects_canonical_keys", _v1_p4l_forbidden_scan_summary(leaked5)["status"] == "fail"))
        checks.append(_check("forbidden_violation_categories_is_list", isinstance(report_pass.get("forbidden_scan", {}).get("violation_categories"), list)))
        # --- Gates ---
        checks.append(_check("pass_locked_denom_gate", bool(report_pass.get("gate_records") and any(g.get("gate") == "locked_denominator_non_python_exact" and g.get("passed") is True for g in report_pass.get("gate_records", [])))))
        checks.append(_check("pass_p4j_split_gates", bool(report_pass.get("gate_records") and any(g.get("gate") == "p4j_reconstructed_upper_bound_exact" and g.get("passed") is True for g in report_pass.get("gate_records", [])) and any(g.get("gate") == "p4j_reconstructed_python_split_exact" and g.get("passed") is True for g in report_pass.get("gate_records", [])))))
        checks.append(_check("mismatch_locked_denom_gate_fail", bool(report_mismatch.get("gate_records") and any(g.get("gate") == "locked_denominator_non_python_exact" and g.get("passed") is False for g in report_mismatch.get("gate_records", [])))))
        checks.append(_check("pass_retained_ratio_gate", bool(report_pass.get("gate_records") and any(g.get("gate") == "p4_retained_gain_ratio_min" and g.get("passed") is True for g in report_pass.get("gate_records", [])))))
        checks.append(_check("fail_retained_ratio_gate", bool(report_fail.get("gate_records") and any(g.get("gate") == "p4_retained_gain_ratio_min" and g.get("passed") is False for g in report_fail.get("gate_records", [])))))
        checks.append(_check("pass_hard_cap_gate", bool(report_pass.get("gate_records") and any(g.get("gate") == "p4_treatment_hard_cap_violations_zero" and g.get("passed") is True for g in report_pass.get("gate_records", [])))))
        # --- self_test fields are counts-only ---
        checks.append(_check("self_test_checks_total_is_int", isinstance(report_pass.get("self_test_checks_total"), int)))
        checks.append(_check("self_test_checks_passed_is_int", isinstance(report_pass.get("self_test_checks_passed"), int)))
        checks.append(_check("no_self_test_checks_list_field", "self_test_checks" not in report_pass))
    parser = build_parser()
    opts = {opt for action in parser._actions for opt in action.option_strings}
    for opt in ("--self-test", "--out", "--fd1-artifact", "--fd1-private-decomposition-jsonl", "--fd1-replay-artifact", "--p4h-artifact", "--p4i-artifact", "--p4j-artifact", "--p4k-artifact", "--openlocus", "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in opts))
    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-P4L Locked Non-Python P4 Scheduler Validation")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd1-private-decomposition-jsonl", type=Path, default=None)
    ap.add_argument("--fd1-replay-artifact", type=Path, default=None)
    ap.add_argument("--p4h-artifact", type=Path, default=DEFAULT_P4H_ARTIFACT)
    ap.add_argument("--p4i-artifact", type=Path, default=DEFAULT_P4I_ARTIFACT)
    ap.add_argument("--p4j-artifact", type=Path, default=DEFAULT_P4J_ARTIFACT)
    ap.add_argument("--p4k-artifact", type=Path, default=DEFAULT_P4K_ARTIFACT)
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
        report = _base_report(status="fail_schema_contract", failure_reason_category="openlocus_binary_missing", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source, network_mode=network_mode, fcc_in={"openlocus_binary_missing": 1, "p4l_scan_failed": 1})
    elif not enable_network:
        report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "missing", network_mode=network_mode, fcc_in={"network_required_but_disabled": 1})
    else:
        try:
            report = _run_validation(openlocus_bin=openlocus_bin or "", openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, self_test_passed=True, self_test_checks_total=len(checks), fd1_artifact_path=args.fd1_artifact, fd1_private_decomposition_jsonl=args.fd1_private_decomposition_jsonl, fd1_replay_artifact=args.fd1_replay_artifact, p4h_artifact_path=args.p4h_artifact, p4i_artifact_path=args.p4i_artifact, p4j_artifact_path=args.p4j_artifact, p4k_artifact_path=args.p4k_artifact, enable_network=enable_network)
        except Exception:
            report = _base_report(status="fail_schema_contract", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, fcc_in={"unexpected_exception": 1, "p4l_scan_failed": 1})
    arms_required = bool(enable_network and report.get("status") != "no_go_p4l_locked_denominator_unavailable")
    if enable_network and (report.get("provider_calls_made") is not False or report.get("latency_in_candidate_relevance") is not False or report.get("gold_labels_used_for_policy") is not False or report.get("query_anchors_used_in_p4_arm") is not False or (arms_required and report.get("p2_depth_only_reference_executed") is not True) or (arms_required and report.get("p3_constrained_depth_policy_reference_executed") is not True) or (arms_required and report.get("p4_latency_aware_action_scheduler_executed") is not True) or report.get("selector_or_reranker_executed") is not False or report.get("v1_a_selector_executed") is not False or report.get("parameter_tuning_executed") is not False or report.get("threshold_search_executed") is not False or report.get("new_arms_added") is not False):
        report["status"] = "fail_schema_contract"
    _enforce_v1_p4l_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    sgr = report.get("stop_go_records", [{}])[0] if report.get("stop_go_records") else {}
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={report['phase']}, locked_count={report.get('locked_denominator_count', 0)}, stop_go_decision={sgr.get('stop_go_decision', '')})")
    if not enable_network:
        print("enable_external_benchmark_network is false; skipping real BEA-v1-P4L locked non-Python scheduler validation.")


if __name__ == "__main__":
    main()
