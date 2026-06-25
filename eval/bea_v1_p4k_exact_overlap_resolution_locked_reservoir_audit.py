#!/usr/bin/env python3
"""BEA-v1-P4K: Exact Overlap Resolution & Locked Reservoir Audit.

P4K is a bounded **denominator/source audit** performed after the BEA-v1-P4J
No-Go (CI ``28146407493``, ``no_go_cross_source_reservoir_unqualified``,
upper-bound reservoir 333 but qualified count 0 because P4H/P4I overlap was
unresolved).  It does **not** run P2/P3/P4 scheduler arms, does **not**
validate a scheduler, does **not** expand retrieval, does **not** execute a
selector/reranker, does **not** call any provider, does **not** run
runtime/default promotion or method-winner logic, and does **not** authorize
P5 / BEA-v1-A / frozen P4 validation / frozen P4 rerun.

Objective: empirically reconstruct exact selected raw keys for P4H (expected
73), P4I (expected 73), and P4J (expected 333) privately under ``/tmp`` using
deterministic source ordering and the same ``current_bea_candidate_pool_replay``
baseline classifier used by those phases, then compute P4J overlap with P4H/P4I
and the post-exclusion locked cross-source reservoir count.

The reconstruction re-runs the same deterministic scans:
- P4H/P4I Python-frame scan: ContextBench Python (offset 0, limit 480) +
  RepoQA Python (offset 0, limit 240), FD1 BEA-4/5 exact-key exclusion,
  baseline file-miss selection.  P4H had target 80 (never reached, found 73);
  P4I scanned full frame (found 73).  Both use the same Python frame and
  classifier, so their reconstructed key sets are identical (73).
- P4J cross-source scan: ContextBench all-languages + RepoQA non-Python, FD1
  BEA-4/5 exact-key exclusion (Python rows via python-ordinal; non-Python
  by-construction disjoint), baseline file-miss selection (333).

Canonical overlap keys:
- Python rows: ``("python", benchmark, python_ordinal)`` — matches across
  P4H/P4I/P4J Python scans because the Nth Python row in any fetch is the
  same dataset row.
- Non-Python rows: ``("non_python", source_frame, language, raw_idx)`` —
  unique to P4J, by-construction disjoint from P4H/P4I (Python-only).

If reconstruction counts cannot exactly match expected aggregates (73/73/333),
the status is ``no_go_exact_overlap_resolution_unavailable`` (conservative,
never invents keys or uses public aggregate approximations).

The public artifact is aggregate-only and records-only.  Private exact-key
sets/rows/manifests stay under ``/tmp`` only and are never uploaded.  No public
raw keys, row IDs, repo URLs, paths, queries, gold files, candidate lists,
snippets, private exact-key hashes, or private path hashes are serialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
import bea_v1_p4i_disjoint_denominator_reservoir_audit as p4i  # noqa: E402
import bea_v1_p4j_cross_source_reservoir_unlock_audit as p4j  # noqa: E402

SCHEMA_VERSION = "bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.v1"
GENERATED_BY = "eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py"
CLAIM_LEVEL = "bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_only"
MODE = "bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit"
PHASE = "BEA-v1-P4K"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit/"
    "bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_report.json"
)
DEFAULT_FD1_ARTIFACT = p4.DEFAULT_FD1_ARTIFACT
DEFAULT_P4H_ARTIFACT = p4h.DEFAULT_OUT
DEFAULT_P4I_ARTIFACT = p4i.DEFAULT_OUT
DEFAULT_P4J_ARTIFACT = p4j.DEFAULT_OUT

# --- P4J binding context (read-only motivation) ---
P4J_RESULT_CHECKPOINT = "28146407493"
P4J_RESULT_STATUS = "no_go_cross_source_reservoir_unqualified"
P4J_CI_RUN_ID = "28146407493"
P4J_UPPER_BOUND_COUNT = 333
P4J_QUALIFIED_COUNT = 0

# --- P4I binding context (read-only motivation) ---
P4I_RESULT_CHECKPOINT = "cc19f5b"
P4I_RESULT_STATUS = "no_go_disjoint_denominator_reservoir_insufficient"
P4I_CI_RUN_ID = "28137455572"
P4I_RESERVOIR_COUNT = 73

# --- P4H binding context (read-only motivation) ---
P4H_RESULT_CHECKPOINT = "9305701"
P4H_RESULT_STATUS = "no_go_p4h_insufficient_denominator"
P4H_CI_RUN_ID = "28132121958"
P4H_DENOMINATOR_COUNT = 73

# --- P4 binding context (read-only) ---
V1_P4_RESULT_CHECKPOINT = "f0e99ca"
V1_P4_RESULT_STATUS = "bea_v1_p4_latency_aware_retrieval_scheduler_pass"

FIXED_BUDGET = p4.FIXED_BUDGET
FIXED_METHODS = p4.FIXED_METHODS
EXPECTED_RECORDS_DECOMPOSED = p4.EXPECTED_RECORDS_DECOMPOSED
EXPECTED_PRIVATE_DECOMP_ROWS = p4.EXPECTED_PRIVATE_DECOMP_ROWS

# The ONLY diagnostic arm.  P2/P3/P4 scheduler arms are NOT run.
DIAGNOSTIC_ARM = "current_bea_candidate_pool_replay"
POLICY_ARMS = (DIAGNOSTIC_ARM,)

# Expected reconstruction counts (from P4H/P4I/P4J committed artifacts).
P4K_EXPECTED_P4H_COUNT = 73
P4K_EXPECTED_P4I_COUNT = 73
P4K_EXPECTED_P4J_COUNT = 333
P4K_EXPECTED_P4J_PYTHON_COUNT = 61
P4K_EXPECTED_P4J_NON_PYTHON_COUNT = 272
P4K_LOCKED_RESERVOIR_MIN_COUNT = 80

# Python-frame scan windows (same as P4H/P4I).
P4K_PYTHON_CONTEXTBENCH_OFFSET = 0
P4K_PYTHON_CONTEXTBENCH_LIMIT = 480
P4K_PYTHON_REPOQA_OFFSET = 0
P4K_PYTHON_REPOQA_LIMIT = 240

# Cross-source scan windows (same as P4J).
P4K_CROSS_CONTEXTBENCH_ALL_LIMIT = 480
P4K_CROSS_REPOQA_NON_PYTHON_PER_LANG_LIMIT = 60

EXACT_OVERLAP_RESOLUTION_SCOPE = (
    "deterministic_source_ordering_baseline_candidate_pool_replay_classifier_reconstruction"
)

STATUSES = (
    "cross_source_locked_reservoir_ready_for_locked_p4_validation_design",
    "no_go_locked_cross_source_reservoir_insufficient",
    "no_go_exact_overlap_resolution_unavailable",
    "fail_schema_contract",
    "fail_forbidden_scan",
    "unavailable_with_reason",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "cross_source_locked_reservoir_ready_for_locked_p4_validation_design",
    "no_go_locked_cross_source_reservoir_insufficient",
    "no_go_exact_overlap_resolution_unavailable",
})

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "records_only_public_artifact": True,
    "diagnostic_only": True,
    "denominator_source_audit_only": True,
    "exact_overlap_resolution_audit_only": True,
    "fd1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "p4h_artifact_read": False,
    "p4i_artifact_read": False,
    "p4j_artifact_read": False,
    "retrieval_policy_executed": False,
    "bea_v1_p4k_audit_evaluator_no_provider_calls": True,
    "bea_v1_p4k_audit_evaluator_no_selector_executed": True,
    "bea_v1_p4k_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p4k_audit_evaluator_no_role_proxy": True,
    "bea_v1_p4k_audit_evaluator_latency_not_in_relevance": True,
    "bea_v1_p4k_audit_evaluator_no_p2_p3_p4_scheduler_arms": True,
    "bea_v1_p4k_audit_evaluator_no_retrieval_expansion": True,
    "bea_v1_p4k_audit_evaluator_no_method_winner_logic": True,
    "bea_v1_p4k_audit_evaluator_no_runtime_default_promotion": True,
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
    "algorithm_changed_during_bea_v1_p4k": False,
    "weights_tuned_during_bea_v1_p4k": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p4k": False,
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
    "locked_p4_validation_executed": False,
    "locked_p4_validation_design_authorized": False,
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
    "new_records_added_during_bea_v1_p4k": False,
}
LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_p4k_exact_overlap_resolution_locked_reservoir_audit",
}

FAILURE_CATEGORIES_AUDIT = tuple(dict.fromkeys((*p4h.FAILURE_CATEGORIES_AUDIT,
    "exact_overlap_resolution_unavailable",
    "locked_reservoir_insufficient",
    "p4h_reconstruction_count_mismatch",
    "p4i_reconstruction_count_mismatch",
    "p4j_reconstruction_count_mismatch",
    "exact_overlap_resolution_scan_not_attempted",
    "exact_overlap_resolution_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
)))
BLOCKING_FAILURE_CATEGORIES = tuple(dict.fromkeys((
    *p4.BLOCKING_FAILURE_CATEGORIES,
    "exact_overlap_resolution_scan_not_attempted",
    "exact_overlap_resolution_scan_failed",
    "cross_source_asset_download_failed",
    "cross_source_asset_decompress_failed",
    "raw_denominator_scan_failed",
    "raw_denominator_scan_not_attempted",
    "raw_denominator_parse_failed",
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


def _resolve_private_reconstruction_dir() -> Path:
    raw = os.environ.get("OPENLOCUS_BEA_V1_P4K_PRIVATE_RECONSTRUCTION_DIR", "")
    base = Path(raw) if raw else Path(f"/tmp/openlocus_bea_v1_p4k_reconstruction_{os.getpid()}")
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private reconstruction dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _canonical_python_key(benchmark: str, python_ordinal: int) -> tuple[str, str, int]:
    """Canonical overlap key for a Python row (matches across P4H/P4I/P4J)."""
    return ("python", benchmark, int(python_ordinal))


def _canonical_non_python_key(source_frame: str, language: str, raw_idx: int) -> tuple[str, str, str, int]:
    """Canonical overlap key for a non-Python row (unique to P4J, disjoint)."""
    return ("non_python", source_frame, language, int(raw_idx))


def _reconstruct_python_frame_keys(
    *, openlocus_bin: str, prior_raw_keys: set[tuple[str, int]],
    use_exact_prior_keys: bool, private_path: Path, fcc: dict[str, int],
) -> tuple[set[tuple[str, str, int]], int, dict[str, Any]]:
    """Reconstruct P4H/P4I selected keys from the Python-frame scan.

    Scans ContextBench Python (offset 0, limit 480) + RepoQA Python (offset 0,
    limit 240), excludes FD1 BEA-4/5 exact keys, runs the baseline classifier,
    and records canonical Python keys for each file-miss record.

    Returns ``(key_set, count, scan_meta)``.  The key set is private (in-memory
    or ``/tmp`` only, never serialized publicly).
    """
    keys: set[tuple[str, str, int]] = set()
    fetched_total = attempted = prior_excluded = 0
    parse_excluded = clone_excluded = baseline_reached = baseline_error = 0
    scan_meta: dict[str, Any] = {
        "contextbench_fetched": 0, "contextbench_file_miss": 0,
        "repoqa_fetched": 0, "repoqa_file_miss": 0,
    }

    # --- ContextBench Python ---
    rows, fetch_status, _, fetch_fcc = p4.bea4._fetch_heldout_contextbench_rows(
        P4K_PYTHON_CONTEXTBENCH_OFFSET, P4K_PYTHON_CONTEXTBENCH_LIMIT)
    for k, v in fetch_fcc.items():
        if k in fcc:
            fcc[k] += int(v)
    if fetch_status not in ("pass",) or not rows:
        fcc["exact_overlap_resolution_scan_failed"] = (
            fcc.get("exact_overlap_resolution_scan_failed", 0) + 1)
        return keys, 0, scan_meta
    scan_meta["contextbench_fetched"] = len(rows)
    fetched_total += len(rows)
    for local_idx, row in enumerate(rows):
        raw_idx = P4K_PYTHON_CONTEXTBENCH_OFFSET + local_idx
        if use_exact_prior_keys and ("contextbench", raw_idx) in prior_raw_keys:
            prior_excluded += 1
            continue
        attempted += 1
        query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval("contextbench", row)
        if not ok:
            parse_excluded += 1
            fcc["raw_denominator_parse_failed"] = (
                fcc.get("raw_denominator_parse_failed", 0) + 1)
            continue
        with tempfile.TemporaryDirectory(prefix=f"v1p4k_py_cb_{raw_idx}_") as tmp:
            work = Path(tmp)
            clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if not clone_ok:
                clone_excluded += 1
                fcc["raw_denominator_clone_failed"] = (
                    fcc.get("raw_denominator_clone_failed", 0) + 1)
                continue
            repo_root = work / "repo"
            rr = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
            if rr.retrieval_error:
                baseline_error += 1
                fcc["retrieval_policy_failed"] = (
                    fcc.get("retrieval_policy_failed", 0) + 1)
                continue
            p4._append_private_jsonl(private_path, {
                "schema_version": "bea_v1_p4k_private_reconstruction.v1",
                "source_phase": "P4K-PYTHON-RECONSTRUCTION",
                "benchmark": "contextbench",
                "language": "python",
                "raw_record_index_private": raw_idx,
                "baseline_gold_file_available": rr.gold_file_available,
                "selected_for_overlap": not rr.gold_file_available,
                "config_hash": p4._config_hash(),
            })
            if rr.gold_file_available:
                baseline_reached += 1
                continue
            keys.add(_canonical_python_key("contextbench", raw_idx))
            scan_meta["contextbench_file_miss"] += 1

    # --- RepoQA Python ---
    rows, fetch_status, _, fetch_fcc = p4.bea4._fetch_heldout_repoqa_needles(
        P4K_PYTHON_REPOQA_OFFSET, P4K_PYTHON_REPOQA_LIMIT)
    for k, v in fetch_fcc.items():
        if k in fcc:
            fcc[k] += int(v)
    if fetch_status not in ("pass",) or not rows:
        fcc["exact_overlap_resolution_scan_failed"] = (
            fcc.get("exact_overlap_resolution_scan_failed", 0) + 1)
        return keys, len(keys), scan_meta
    scan_meta["repoqa_fetched"] = len(rows)
    fetched_total += len(rows)
    for local_idx, row in enumerate(rows):
        raw_idx = P4K_PYTHON_REPOQA_OFFSET + local_idx
        if use_exact_prior_keys and ("repoqa", raw_idx) in prior_raw_keys:
            prior_excluded += 1
            continue
        attempted += 1
        query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval("repoqa", row)
        if not ok:
            parse_excluded += 1
            fcc["raw_denominator_parse_failed"] = (
                fcc.get("raw_denominator_parse_failed", 0) + 1)
            continue
        with tempfile.TemporaryDirectory(prefix=f"v1p4k_py_rq_{raw_idx}_") as tmp:
            work = Path(tmp)
            clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if not clone_ok:
                clone_excluded += 1
                fcc["raw_denominator_clone_failed"] = (
                    fcc.get("raw_denominator_clone_failed", 0) + 1)
                continue
            repo_root = work / "repo"
            rr = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
            if rr.retrieval_error:
                baseline_error += 1
                fcc["retrieval_policy_failed"] = (
                    fcc.get("retrieval_policy_failed", 0) + 1)
                continue
            p4._append_private_jsonl(private_path, {
                "schema_version": "bea_v1_p4k_private_reconstruction.v1",
                "source_phase": "P4K-PYTHON-RECONSTRUCTION",
                "benchmark": "repoqa",
                "language": "python",
                "raw_record_index_private": raw_idx,
                "baseline_gold_file_available": rr.gold_file_available,
                "selected_for_overlap": not rr.gold_file_available,
                "config_hash": p4._config_hash(),
            })
            if rr.gold_file_available:
                baseline_reached += 1
                continue
            keys.add(_canonical_python_key("repoqa", raw_idx))
            scan_meta["repoqa_file_miss"] += 1

    scan_meta.update({
        "fetched_total": fetched_total,
        "attempted": attempted,
        "prior_exact_excluded": prior_excluded,
        "parse_excluded": parse_excluded,
        "clone_excluded": clone_excluded,
        "baseline_reached": baseline_reached,
        "baseline_error": baseline_error,
        "file_miss_selected": len(keys),
    })
    return keys, len(keys), scan_meta


def _reconstruct_cross_source_keys(
    *, openlocus_bin: str, prior_raw_keys: set[tuple[str, int]],
    use_exact_prior_keys: bool, parsed_asset: Any, private_path: Path,
    fcc: dict[str, int],
) -> tuple[set[tuple], int, dict[str, Any]]:
    """Reconstruct P4J selected keys from the cross-source scan.

    Scans ContextBench all-languages + RepoQA non-Python, excludes FD1 BEA-4/5
    exact keys (Python via python-ordinal; non-Python by-construction disjoint),
    runs the baseline classifier, and records canonical keys for each file-miss
    record.

    Returns ``(key_set, count, scan_meta)``.  The key set is private.
    """
    keys: set[tuple] = set()
    fetched_total = attempted = prior_excluded = by_construction = 0
    parse_excluded = clone_excluded = baseline_reached = baseline_error = 0
    non_python_file_miss = python_file_miss = 0
    per_language: list[dict[str, Any]] = []
    scan_meta: dict[str, Any] = {
        "contextbench_all_fetched": 0,
        "contextbench_all_file_miss": 0,
        "repoqa_non_python_fetched": 0,
        "repoqa_non_python_file_miss": 0,
    }

    # --- ContextBench all-languages ---
    rows, fetch_status, _, fetch_fcc = p4.c5a._fetch_contextbench_rows(
        P4K_CROSS_CONTEXTBENCH_ALL_LIMIT, "all")
    for k, v in fetch_fcc.items():
        if k in fcc:
            fcc[k] += int(v)
    if fetch_status != "pass" or not rows:
        fcc["exact_overlap_resolution_scan_failed"] = (
            fcc.get("exact_overlap_resolution_scan_failed", 0) + 1)
        return keys, 0, scan_meta
    if len(rows) > P4K_CROSS_CONTEXTBENCH_ALL_LIMIT:
        rows = rows[:P4K_CROSS_CONTEXTBENCH_ALL_LIMIT]
    scan_meta["contextbench_all_fetched"] = len(rows)
    fetched_total += len(rows)
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
            fcc["raw_denominator_parse_failed"] = (
                fcc.get("raw_denominator_parse_failed", 0) + 1)
            if is_python:
                python_ordinal += 1
            continue
        with tempfile.TemporaryDirectory(prefix=f"v1p4k_cs_cb_{local_idx}_") as tmp:
            work = Path(tmp)
            clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
            for k, v in clone_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if not clone_ok:
                clone_excluded += 1
                fcc["raw_denominator_clone_failed"] = (
                    fcc.get("raw_denominator_clone_failed", 0) + 1)
                if is_python:
                    python_ordinal += 1
                continue
            repo_root = work / "repo"
            rr = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
            if rr.retrieval_error:
                baseline_error += 1
                fcc["retrieval_policy_failed"] = (
                    fcc.get("retrieval_policy_failed", 0) + 1)
                if is_python:
                    python_ordinal += 1
                continue
            p4._append_private_jsonl(private_path, {
                "schema_version": "bea_v1_p4k_private_reconstruction.v1",
                "source_phase": "P4K-CROSS-SOURCE-RECONSTRUCTION",
                "source_frame": "contextbench_all_languages",
                "benchmark": "contextbench",
                "language": lang,
                "raw_record_index_private": local_idx,
                "python_ordinal_private": python_ordinal if is_python else None,
                "baseline_gold_file_available": rr.gold_file_available,
                "selected_for_overlap": not rr.gold_file_available,
                "config_hash": p4._config_hash(),
            })
            if rr.gold_file_available:
                baseline_reached += 1
                if is_python:
                    python_ordinal += 1
                continue
            if is_python:
                keys.add(_canonical_python_key("contextbench", python_ordinal))
                python_file_miss += 1
            else:
                keys.add(_canonical_non_python_key("contextbench_all_languages", lang, local_idx))
                non_python_file_miss += 1
            scan_meta["contextbench_all_file_miss"] += 1
        if is_python:
            python_ordinal += 1

    # --- RepoQA non-Python ---
    if isinstance(parsed_asset, dict):
        non_python_langs = sorted(
            str(k) for k in parsed_asset
            if k != "python" and isinstance(parsed_asset.get(k), list))
        for lang in non_python_langs:
            needles, needle_status, needle_fcc = p4.c5d._parse_repoqa_needles(
                parsed_asset, lang, P4K_CROSS_REPOQA_NON_PYTHON_PER_LANG_LIMIT)
            for k, v in needle_fcc.items():
                if k in fcc:
                    fcc[k] += int(v)
            if needle_status != "pass":
                if needle_status != "unavailable_no_python_needles":
                    fcc["raw_denominator_parse_failed"] = (
                        fcc.get("raw_denominator_parse_failed", 0) + 1)
                    fcc["exact_overlap_resolution_scan_failed"] = (
                        fcc.get("exact_overlap_resolution_scan_failed", 0) + 1)
                continue
            if not needles:
                continue
            lang_fetched = len(needles)
            lang_file_miss = 0
            fetched_total += lang_fetched
            scan_meta["repoqa_non_python_fetched"] += lang_fetched
            for local_idx, needle in enumerate(needles):
                by_construction += 1
                attempted += 1
                query, gold_paths, repo_url, base_commit, ok = p4h._parse_raw_row_for_retrieval("repoqa", needle)
                if not ok:
                    parse_excluded += 1
                    fcc["raw_denominator_parse_failed"] = (
                        fcc.get("raw_denominator_parse_failed", 0) + 1)
                    continue
                with tempfile.TemporaryDirectory(prefix=f"v1p4k_cs_rq_{lang}_{local_idx}_") as tmp:
                    work = Path(tmp)
                    clone_ok, _, clone_fcc = p4.c5d._clone_and_checkout(repo_url, base_commit, work)
                    for k, v in clone_fcc.items():
                        if k in fcc:
                            fcc[k] += int(v)
                    if not clone_ok:
                        clone_excluded += 1
                        fcc["raw_denominator_clone_failed"] = (
                            fcc.get("raw_denominator_clone_failed", 0) + 1)
                        continue
                    repo_root = work / "repo"
                    rr = p4._run_baseline_arm(openlocus_bin=openlocus_bin, repo_root=repo_root, query=query, gold_set={str(x) for x in gold_paths if x})
                    if rr.retrieval_error:
                        baseline_error += 1
                        fcc["retrieval_policy_failed"] = (
                            fcc.get("retrieval_policy_failed", 0) + 1)
                        continue
                    p4._append_private_jsonl(private_path, {
                        "schema_version": "bea_v1_p4k_private_reconstruction.v1",
                        "source_phase": "P4K-CROSS-SOURCE-RECONSTRUCTION",
                        "source_frame": "repoqa_non_python_languages",
                        "benchmark": "repoqa",
                        "language": lang,
                        "raw_record_index_private": local_idx,
                        "baseline_gold_file_available": rr.gold_file_available,
                        "selected_for_overlap": not rr.gold_file_available,
                        "config_hash": p4._config_hash(),
                    })
                    if rr.gold_file_available:
                        baseline_reached += 1
                        continue
                    keys.add(_canonical_non_python_key("repoqa_non_python_languages", lang, local_idx))
                    non_python_file_miss += 1
                    lang_file_miss += 1
                    scan_meta["repoqa_non_python_file_miss"] += 1
            per_language.append({
                "language": lang,
                "fetched": lang_fetched,
                "file_miss": lang_file_miss,
            })

    scan_meta.update({
        "fetched_total": fetched_total,
        "attempted": attempted,
        "prior_exact_excluded": prior_excluded,
        "by_construction_disjoint_records": by_construction,
        "parse_excluded": parse_excluded,
        "clone_excluded": clone_excluded,
        "baseline_reached": baseline_reached,
        "baseline_error": baseline_error,
        "file_miss_selected": len(keys),
        "non_python_file_miss": non_python_file_miss,
        "python_file_miss": python_file_miss,
        "per_language": per_language,
    })
    return keys, len(keys), scan_meta


def _compute_locked_reservoir(
    *, p4h_keys: set, p4i_keys: set, p4j_keys: set,
) -> dict[str, Any]:
    """Compute overlap and post-exclusion locked cross-source reservoir.

    All key sets are private (in-memory only).  Returns aggregate counts only.
    """
    overlap_p4h = p4j_keys & p4h_keys
    overlap_p4i = p4j_keys & p4i_keys
    locked = p4j_keys - p4h_keys - p4i_keys
    non_python_locked = sum(1 for k in locked if k[0] == "non_python")
    python_locked = sum(1 for k in locked if k[0] == "python")
    return {
        "p4j_overlap_with_p4h_count": len(overlap_p4h),
        "p4j_overlap_with_p4i_count": len(overlap_p4i),
        "locked_cross_source_reservoir_count": len(locked),
        "non_python_locked_reservoir_count": int(non_python_locked),
        "python_locked_reservoir_count": int(python_locked),
    }


def _run_exact_overlap_resolution(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    fd1_artifact_path: Path, fd1_private_decomposition_jsonl: Path | None,
    fd1_replay_artifact: Path | None, p4h_artifact_path: Path | None,
    p4i_artifact_path: Path | None, p4j_artifact_path: Path | None,
    enable_network: bool,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    start = time.perf_counter()
    fd1_artifact, fd1_schema, fd1_hash, fd1_status = p4._load_committed_artifact(fd1_artifact_path)
    if fd1_status != "pass":
        fcc["fd1_artifact_missing" if fd1_status == "artifact_missing" else "fd1_artifact_parse_failed"] = 1
        return _base_report(status="unavailable_with_reason", failure_reason_category=fd1_status, self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fcc_in=fcc)
    p4h_artifact: dict[str, Any] = {}
    p4i_artifact: dict[str, Any] = {}
    p4j_artifact: dict[str, Any] = {}
    if p4h_artifact_path is not None:
        try:
            p4h_artifact, _, _, _ = p4._load_committed_artifact(p4h_artifact_path)
        except Exception:
            p4h_artifact = {}
    if p4i_artifact_path is not None:
        try:
            p4i_artifact, _, _, _ = p4._load_committed_artifact(p4i_artifact_path)
        except Exception:
            p4i_artifact = {}
    if p4j_artifact_path is not None:
        try:
            p4j_artifact, _, _, _ = p4._load_committed_artifact(p4j_artifact_path)
        except Exception:
            p4j_artifact = {}
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

    recon_meta: dict[str, Any] = {
        "p4h_exact_keys_reconstructed": False,
        "p4i_exact_keys_reconstructed": False,
        "p4j_exact_keys_reconstructed": False,
        "p4h_reconstructed_denominator_count": 0,
        "p4i_reconstructed_reservoir_count": 0,
        "p4j_reconstructed_upper_bound_count": 0,
        "p4j_overlap_with_p4h_count": 0,
        "p4j_overlap_with_p4i_count": 0,
        "locked_cross_source_reservoir_count": 0,
        "non_python_locked_reservoir_count": 0,
        "python_locked_reservoir_count": 0,
        "p4j_reconstructed_python_count": 0,
        "p4j_reconstructed_non_python_count": 0,
        "exact_overlap_resolution_attempted": False,
        "exact_prior_exclusion_used": False,
        "fd1_prior_exclusion_used": False,
        "python_frame_scan_meta": {},
        "cross_source_scan_meta": {},
        "reconstruction_mismatch_reasons": [],
    }
    manifests: list[dict[str, Any]] = []

    if enable_network and audit_match and pt.computed and rav.validated:
        prior_raw_keys, _ = p4h._prior_raw_keys_from_fd1_private(pt)
        use_exact_prior_keys = bool(prior_raw_keys)
        recon_meta["exact_prior_exclusion_used"] = use_exact_prior_keys
        recon_meta["fd1_prior_exclusion_used"] = use_exact_prior_keys
        if not use_exact_prior_keys:
            fcc["exact_overlap_resolution_unavailable"] = 1
        else:
            private_dir = _resolve_private_reconstruction_dir()
            private_path = private_dir / "bea_v1_p4k.private_reconstruction.jsonl"
            if private_path.exists():
                private_path.unlink()
            recon_meta["exact_overlap_resolution_attempted"] = True
            try:
                # --- Reconstruct P4H/P4I keys (Python frame, shared) ---
                p4h_keys, p4h_count, py_meta = _reconstruct_python_frame_keys(
                    openlocus_bin=openlocus_bin, prior_raw_keys=prior_raw_keys,
                    use_exact_prior_keys=use_exact_prior_keys,
                    private_path=private_path, fcc=fcc)
                recon_meta["python_frame_scan_meta"] = py_meta
                # P4H and P4I scan the same Python frame with the same
                # classifier; P4H had target 80 (found 73), P4I scanned full
                # (found 73).  Their key sets are identical.
                p4i_keys = set(p4h_keys)
                p4i_count = p4h_count
                recon_meta["p4h_reconstructed_denominator_count"] = p4h_count
                recon_meta["p4i_reconstructed_reservoir_count"] = p4i_count
                if p4h_count == P4K_EXPECTED_P4H_COUNT:
                    recon_meta["p4h_exact_keys_reconstructed"] = True
                else:
                    fcc["p4h_reconstruction_count_mismatch"] = 1
                    recon_meta["reconstruction_mismatch_reasons"].append(
                        f"p4h_expected={P4K_EXPECTED_P4H_COUNT};reconstructed={p4h_count}")
                if p4i_count == P4K_EXPECTED_P4I_COUNT:
                    recon_meta["p4i_exact_keys_reconstructed"] = True
                else:
                    fcc["p4i_reconstruction_count_mismatch"] = 1
                    recon_meta["reconstruction_mismatch_reasons"].append(
                        f"p4i_expected={P4K_EXPECTED_P4I_COUNT};reconstructed={p4i_count}")

                # --- Reconstruct P4J keys (cross-source) ---
                asset_bytes, dl_status, dl_fcc = p4.c5d._download_asset_to_bytes(p4.c5d.ASSET_URL)
                for k, v in dl_fcc.items():
                    if k in fcc:
                        fcc[k] += int(v)
                if dl_status != "pass" or not asset_bytes:
                    fcc["cross_source_asset_download_failed"] = 1
                    fcc["exact_overlap_resolution_scan_failed"] = 1
                else:
                    parsed_asset, parse_status, parse_fcc = p4.c5d._decompress_asset(asset_bytes)
                    del asset_bytes
                    for k, v in parse_fcc.items():
                        if k in fcc:
                            fcc[k] += int(v)
                    if parse_status != "pass" or parsed_asset is None:
                        fcc["cross_source_asset_decompress_failed"] = 1
                        fcc["exact_overlap_resolution_scan_failed"] = 1
                    else:
                        p4j_keys, p4j_count, cs_meta = _reconstruct_cross_source_keys(
                            openlocus_bin=openlocus_bin, prior_raw_keys=prior_raw_keys,
                            use_exact_prior_keys=use_exact_prior_keys,
                            parsed_asset=parsed_asset, private_path=private_path, fcc=fcc)
                        recon_meta["cross_source_scan_meta"] = cs_meta
                        recon_meta["p4j_reconstructed_upper_bound_count"] = p4j_count
                        p4j_python_count = sum(1 for k in p4j_keys if k[0] == "python")
                        p4j_non_python_count = sum(1 for k in p4j_keys if k[0] == "non_python")
                        recon_meta["p4j_reconstructed_python_count"] = int(p4j_python_count)
                        recon_meta["p4j_reconstructed_non_python_count"] = int(p4j_non_python_count)
                        if (p4j_count == P4K_EXPECTED_P4J_COUNT
                                and p4j_python_count == P4K_EXPECTED_P4J_PYTHON_COUNT
                                and p4j_non_python_count == P4K_EXPECTED_P4J_NON_PYTHON_COUNT):
                            recon_meta["p4j_exact_keys_reconstructed"] = True
                        else:
                            fcc["p4j_reconstruction_count_mismatch"] = 1
                            recon_meta["reconstruction_mismatch_reasons"].append(
                                f"p4j_expected={P4K_EXPECTED_P4J_COUNT};reconstructed={p4j_count};"
                                f"python_expected={P4K_EXPECTED_P4J_PYTHON_COUNT};python_reconstructed={p4j_python_count};"
                                f"non_python_expected={P4K_EXPECTED_P4J_NON_PYTHON_COUNT};non_python_reconstructed={p4j_non_python_count}")
                        # --- Compute overlap and locked reservoir ---
                        overlap = _compute_locked_reservoir(
                            p4h_keys=p4h_keys, p4i_keys=p4i_keys, p4j_keys=p4j_keys)
                        recon_meta.update(overlap)
                scan_manifest = p4._private_file_manifest(
                    private_path,
                    manifest_name="bea_v1_p4k_private_reconstruction_manifest",
                    schema_version="bea_v1_p4k_private_reconstruction.v1")
                manifests.append(scan_manifest)
                if recon_meta["locked_cross_source_reservoir_count"] < P4K_LOCKED_RESERVOIR_MIN_COUNT:
                    if (recon_meta["p4h_exact_keys_reconstructed"]
                            and recon_meta["p4i_exact_keys_reconstructed"]
                            and recon_meta["p4j_exact_keys_reconstructed"]):
                        fcc["locked_reservoir_insufficient"] = 1
            except Exception:
                fcc["retrieval_policy_failed"] = 1
                fcc["unexpected_exception"] = 1
    elif enable_network:
        fcc["exact_overlap_resolution_scan_not_attempted"] = 1
    else:
        fcc["network_required_but_disabled"] = 1
    return _base_report(status="auto", failure_reason_category="", self_test_passed=self_test_passed, self_test_checks_total=self_test_checks_total, self_test_checks_passed=None, openlocus_binary_source=openlocus_binary_source, network_mode=network_mode, fd1_artifact=fd1_artifact, fd1_schema=fd1_schema, fd1_hash=fd1_hash, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4i_artifact=p4i_artifact, p4j_artifact=p4j_artifact, recon_meta=recon_meta, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason, fcc_in=fcc, extra_manifests=manifests, aggregate_runtime_seconds=time.perf_counter() - start)


def _stop_go_records(
    *, recon_meta: dict[str, Any], blocking_failure_count: int,
    exact_prior_exclusion_used: bool, attempt_made: bool,
) -> list[dict[str, Any]]:
    p4h_ok = bool(recon_meta.get("p4h_exact_keys_reconstructed", False))
    p4i_ok = bool(recon_meta.get("p4i_exact_keys_reconstructed", False))
    p4j_ok = bool(recon_meta.get("p4j_exact_keys_reconstructed", False))
    locked = int(recon_meta.get("locked_cross_source_reservoir_count", 0))
    if not exact_prior_exclusion_used:
        decision = "fail_schema_contract"
        reason = "fd1_exact_prior_exclusion_required_for_overlap_resolution"
    elif blocking_failure_count > 0:
        decision = "fail_schema_contract"
        reason = "blocking_failure_present_cannot_be_overlap_resolution"
    elif not attempt_made:
        decision = "fail_schema_contract"
        reason = "exact_overlap_resolution_not_attempted"
    elif not (p4h_ok and p4i_ok and p4j_ok):
        decision = "no_go_exact_overlap_resolution_unavailable"
        reasons = recon_meta.get("reconstruction_mismatch_reasons", [])
        reason = "exact_reconstruction_count_mismatch: " + ";".join(reasons) if reasons else "exact_keys_not_reproducible_deterministically"
    elif locked < P4K_LOCKED_RESERVOIR_MIN_COUNT:
        decision = "no_go_locked_cross_source_reservoir_insufficient"
        reason = f"locked_cross_source_reservoir_count={locked}; min={P4K_LOCKED_RESERVOIR_MIN_COUNT}"
    else:
        decision = "cross_source_locked_reservoir_ready_for_locked_p4_validation_design"
        reason = "qualified_locked_cross_source_reservoir_reaches_min_with_overlap_resolved"
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "p4h_reconstructed_denominator_count": int(recon_meta.get("p4h_reconstructed_denominator_count", 0)),
        "p4i_reconstructed_reservoir_count": int(recon_meta.get("p4i_reconstructed_reservoir_count", 0)),
        "p4j_reconstructed_upper_bound_count": int(recon_meta.get("p4j_reconstructed_upper_bound_count", 0)),
        "p4j_overlap_with_p4h_count": int(recon_meta.get("p4j_overlap_with_p4h_count", 0)),
        "p4j_overlap_with_p4i_count": int(recon_meta.get("p4j_overlap_with_p4i_count", 0)),
        "locked_cross_source_reservoir_count": int(locked),
        "non_python_locked_reservoir_count": int(recon_meta.get("non_python_locked_reservoir_count", 0)),
        "python_locked_reservoir_count": int(recon_meta.get("python_locked_reservoir_count", 0)),
        "p4h_exact_keys_reconstructed": bool(p4h_ok),
        "p4i_exact_keys_reconstructed": bool(p4i_ok),
        "p4j_exact_keys_reconstructed": bool(p4j_ok),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "exact_overlap_resolution_attempted": bool(attempt_made),
        "locked_p4_validation_design_authorized": bool(decision == "cross_source_locked_reservoir_ready_for_locked_p4_validation_design"),
        "scheduler_validation_authorized": False,
        "locked_p4_validation_executed": False,
        "frozen_p4_rerun_authorized": False,
        "frozen_p4_validation_executed": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "method_winner_authorized": False,
        "broad_retrieval_expansion_authorized": False,
    }]


def _gate_records(
    *, fd1_records_decomposed: int, fd1_private_manifest_record_count: int,
    recon_meta: dict[str, Any], fd1_private_decomposition_parsed: bool,
    replay_artifact_validated: bool, forbidden_scan_pass: bool,
    blocking_failure_count: int, exact_prior_exclusion_used: bool,
) -> list[dict[str, Any]]:
    def g(name: str, value: float, relation: str, threshold: float, passed: bool) -> dict[str, Any]:
        return {"gate": name, "value": round(float(value), 6), "threshold_relation": relation, "threshold_value": round(float(threshold), 6), "passed": bool(passed)}
    locked = int(recon_meta.get("locked_cross_source_reservoir_count", 0))
    return [
        g("fd1_records_decomposed", fd1_records_decomposed, "==", EXPECTED_RECORDS_DECOMPOSED, fd1_records_decomposed == EXPECTED_RECORDS_DECOMPOSED),
        g("fd1_private_manifest_record_count", fd1_private_manifest_record_count, "==", EXPECTED_PRIVATE_DECOMP_ROWS, fd1_private_manifest_record_count == EXPECTED_PRIVATE_DECOMP_ROWS),
        g("fd1_private_decomposition_parsed", 1.0 if fd1_private_decomposition_parsed else 0.0, "boolean", 1.0, fd1_private_decomposition_parsed),
        g("replay_artifact_validated", 1.0 if replay_artifact_validated else 0.0, "boolean", 1.0, replay_artifact_validated),
        g("exact_prior_exclusion_used", 1.0 if exact_prior_exclusion_used else 0.0, "boolean", 1.0, bool(exact_prior_exclusion_used)),
        g("p4h_exact_keys_reconstructed", 1.0 if recon_meta.get("p4h_exact_keys_reconstructed") else 0.0, "boolean", 1.0, bool(recon_meta.get("p4h_exact_keys_reconstructed"))),
        g("p4i_exact_keys_reconstructed", 1.0 if recon_meta.get("p4i_exact_keys_reconstructed") else 0.0, "boolean", 1.0, bool(recon_meta.get("p4i_exact_keys_reconstructed"))),
        g("p4j_exact_keys_reconstructed", 1.0 if recon_meta.get("p4j_exact_keys_reconstructed") else 0.0, "boolean", 1.0, bool(recon_meta.get("p4j_exact_keys_reconstructed"))),
        g("locked_cross_source_reservoir_min", locked, ">=", P4K_LOCKED_RESERVOIR_MIN_COUNT, locked >= P4K_LOCKED_RESERVOIR_MIN_COUNT),
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


def _source_run_records(
    *, fd1_schema_version: str, fd1_source_artifact_hash: str,
    fd1_status: str, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    pt: Any, rav: Any,
    p4h_artifact: dict[str, Any] | None, p4i_artifact: dict[str, Any] | None,
    p4j_artifact: dict[str, Any] | None,
    audit_match: bool, audit_mismatch_reason: str,
) -> list[dict[str, Any]]:
    p4h_art = p4h_artifact or {}
    p4i_art = p4i_artifact or {}
    p4j_art = p4j_artifact or {}
    return [{
        "source_phase": "BEA-v1-P4J",
        "source_checkpoint": P4J_RESULT_CHECKPOINT,
        "source_status": P4J_RESULT_STATUS,
        "source_ci_run_id": P4J_CI_RUN_ID,
        "source_upper_bound_count": P4J_UPPER_BOUND_COUNT,
        "source_qualified_count": P4J_QUALIFIED_COUNT,
        "audit_objective": "resolve_exact_p4h_p4i_overlap_and_compute_locked_cross_source_reservoir",
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "denominator_source_protocol": "exact_overlap_resolution_locked_reservoir_audit.v1",
        "expected_p4h_count": P4K_EXPECTED_P4H_COUNT,
        "expected_p4i_count": P4K_EXPECTED_P4I_COUNT,
        "expected_p4j_count": P4K_EXPECTED_P4J_COUNT,
        "expected_p4j_python_count": P4K_EXPECTED_P4J_PYTHON_COUNT,
        "expected_p4j_non_python_count": P4K_EXPECTED_P4J_NON_PYTHON_COUNT,
        "locked_reservoir_min_count": P4K_LOCKED_RESERVOIR_MIN_COUNT,
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
        "p4h_committed_denominator_count": int(p4h_art.get("denominator_count", P4H_DENOMINATOR_COUNT) or 0),
        "p4i_artifact_read": bool(p4i_art),
        "p4i_committed_reservoir_count": int(p4i_art.get("denominator_count", P4I_RESERVOIR_COUNT) or 0),
        "p4j_artifact_read": bool(p4j_art),
        "p4j_committed_upper_bound_count": int(p4j_art.get("reservoir_upper_bound_count", P4J_UPPER_BOUND_COUNT) or 0),
        "p4h_result_checkpoint": P4H_RESULT_CHECKPOINT,
        "p4h_result_status": P4H_RESULT_STATUS,
        "p4i_result_checkpoint": P4I_RESULT_CHECKPOINT,
        "p4i_result_status": P4I_RESULT_STATUS,
        "v1_p4_result_checkpoint": V1_P4_RESULT_CHECKPOINT,
        "v1_p4_result_status": V1_P4_RESULT_STATUS,
        "config_hash": p4._config_hash(),
    }]


def _reconstruction_records(recon_meta: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "reconstruction_phase": "P4H_python_frame",
        "expected_count": P4K_EXPECTED_P4H_COUNT,
        "reconstructed_count": int(recon_meta.get("p4h_reconstructed_denominator_count", 0)),
        "exact_keys_reconstructed": bool(recon_meta.get("p4h_exact_keys_reconstructed", False)),
    }, {
        "reconstruction_phase": "P4I_python_frame",
        "expected_count": P4K_EXPECTED_P4I_COUNT,
        "reconstructed_count": int(recon_meta.get("p4i_reconstructed_reservoir_count", 0)),
        "exact_keys_reconstructed": bool(recon_meta.get("p4i_exact_keys_reconstructed", False)),
    }, {
        "reconstruction_phase": "P4J_cross_source",
        "expected_count": P4K_EXPECTED_P4J_COUNT,
        "reconstructed_count": int(recon_meta.get("p4j_reconstructed_upper_bound_count", 0)),
        "exact_keys_reconstructed": bool(recon_meta.get("p4j_exact_keys_reconstructed", False)),
    }, {
        "reconstruction_phase": "P4J_cross_source_python_subset",
        "expected_count": P4K_EXPECTED_P4J_PYTHON_COUNT,
        "reconstructed_count": int(recon_meta.get("p4j_reconstructed_python_count", 0)),
        "exact_keys_reconstructed": bool(recon_meta.get("p4j_exact_keys_reconstructed", False)),
    }, {
        "reconstruction_phase": "P4J_cross_source_non_python_subset",
        "expected_count": P4K_EXPECTED_P4J_NON_PYTHON_COUNT,
        "reconstructed_count": int(recon_meta.get("p4j_reconstructed_non_python_count", 0)),
        "exact_keys_reconstructed": bool(recon_meta.get("p4j_exact_keys_reconstructed", False)),
    }]


def _overlap_records(recon_meta: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "overlap_pair": "P4J_with_P4H",
        "overlap_count": int(recon_meta.get("p4j_overlap_with_p4h_count", 0)),
    }, {
        "overlap_pair": "P4J_with_P4I",
        "overlap_count": int(recon_meta.get("p4j_overlap_with_p4i_count", 0)),
    }]


FORBIDDEN_PUBLIC_KEYS = frozenset(p4h.FORBIDDEN_PUBLIC_KEYS | {
    "reconstructed_keys_private", "exact_keys_private", "p4h_exact_keys",
    "p4i_exact_keys", "p4j_exact_keys", "prior_exact_raw_keys",
    "canonical_keys", "overlap_keys_private", "locked_keys_private",
    "python_ordinal_private", "reconstruction_trace_path",
    "reconstruction_private_path", "reconstruction_jsonl_path",
    "repo_url_private", "base_commit_private", "gold_paths_private",
    "candidate_paths_private", "query_private",
})


def _scan_v1_p4k(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                ks = str(k)
                sub = f"{path}.{ks}"
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_v1_p4k_public_key", "path": sub})
                if isinstance(v, str) and len(v) > 240 and ks not in {"stop_go_reason", "audit_objective"}:
                    violations.append({"category": "long_string", "path": sub})
                walk(v, sub)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(obj)
    return violations


def _v1_p4k_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p4k(obj)
    cats: dict[str, int] = {}
    for v in violations:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    violation_categories = [{"category": c, "count": int(n)} for c, n in sorted(cats.items())]
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": violation_categories,
    }


def _enforce_v1_p4k_no_forbidden(obj: Any) -> None:
    if _v1_p4k_forbidden_scan_summary(obj)["status"] != "pass":
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
    recon_meta: dict[str, Any] | None = None,
    retrieval_policy_executed: bool = False, audit_match: bool = False,
    audit_mismatch_reason: str = "", fcc_in: dict[str, int] | None = None,
    extra_manifests: list[dict[str, Any]] | None = None,
    aggregate_runtime_seconds: float = 0.0,
) -> dict[str, Any]:
    fd1_artifact = fd1_artifact or {}
    recon_meta = recon_meta or {
        "p4h_exact_keys_reconstructed": False,
        "p4i_exact_keys_reconstructed": False,
        "p4j_exact_keys_reconstructed": False,
        "p4h_reconstructed_denominator_count": 0,
        "p4i_reconstructed_reservoir_count": 0,
        "p4j_reconstructed_upper_bound_count": 0,
        "p4j_overlap_with_p4h_count": 0,
        "p4j_overlap_with_p4i_count": 0,
        "locked_cross_source_reservoir_count": 0,
        "non_python_locked_reservoir_count": 0,
        "python_locked_reservoir_count": 0,
        "p4j_reconstructed_python_count": 0,
        "p4j_reconstructed_non_python_count": 0,
        "exact_overlap_resolution_attempted": False,
        "exact_prior_exclusion_used": False,
        "fd1_prior_exclusion_used": False,
        "python_frame_scan_meta": {},
        "cross_source_scan_meta": {},
        "reconstruction_mismatch_reasons": [],
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
    exact_prior_exclusion_used = bool(recon_meta.get("exact_prior_exclusion_used", False))
    blocking = _blocking_failure_count(fcc)
    stop_go = _stop_go_records(
        recon_meta=recon_meta, blocking_failure_count=blocking,
        exact_prior_exclusion_used=exact_prior_exclusion_used,
        attempt_made=bool(recon_meta.get("exact_overlap_resolution_attempted", False)))
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
            status = "no_go_exact_overlap_resolution_unavailable"
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
        "denominator_source_protocol": "exact_overlap_resolution_locked_reservoir_audit.v1",
        "exact_overlap_resolution_scope": EXACT_OVERLAP_RESOLUTION_SCOPE,
        "records_decomposed": int(fd1_records),
        "private_manifest_record_count": int(fd1_manifest_count),
        "failure_reason_category": failure_reason_category,
        "p4h_exact_keys_reconstructed": bool(recon_meta.get("p4h_exact_keys_reconstructed", False)),
        "p4i_exact_keys_reconstructed": bool(recon_meta.get("p4i_exact_keys_reconstructed", False)),
        "p4j_exact_keys_reconstructed": bool(recon_meta.get("p4j_exact_keys_reconstructed", False)),
        "p4h_reconstructed_denominator_count": int(recon_meta.get("p4h_reconstructed_denominator_count", 0)),
        "p4i_reconstructed_reservoir_count": int(recon_meta.get("p4i_reconstructed_reservoir_count", 0)),
        "p4j_reconstructed_upper_bound_count": int(recon_meta.get("p4j_reconstructed_upper_bound_count", 0)),
        "p4j_reconstructed_python_count": int(recon_meta.get("p4j_reconstructed_python_count", 0)),
        "p4j_reconstructed_non_python_count": int(recon_meta.get("p4j_reconstructed_non_python_count", 0)),
        "p4j_overlap_with_p4h_count": int(recon_meta.get("p4j_overlap_with_p4h_count", 0)),
        "p4j_overlap_with_p4i_count": int(recon_meta.get("p4j_overlap_with_p4i_count", 0)),
        "locked_cross_source_reservoir_count": int(recon_meta.get("locked_cross_source_reservoir_count", 0)),
        "non_python_locked_reservoir_count": int(recon_meta.get("non_python_locked_reservoir_count", 0)),
        "python_locked_reservoir_count": int(recon_meta.get("python_locked_reservoir_count", 0)),
        "exact_overlap_resolution_attempted": bool(recon_meta.get("exact_overlap_resolution_attempted", False)),
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "fd1_prior_exclusion_used": bool(recon_meta.get("fd1_prior_exclusion_used", False)),
        "locked_reservoir_min_count": P4K_LOCKED_RESERVOIR_MIN_COUNT,
        "source_run_records": _source_run_records(fd1_schema_version=fd1_schema, fd1_source_artifact_hash=fd1_hash, fd1_status=fd1_status, fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, pt=pt, rav=rav, p4h_artifact=p4h_artifact, p4i_artifact=p4i_artifact, p4j_artifact=p4j_artifact, audit_match=audit_match, audit_mismatch_reason=audit_mismatch_reason),
        "reconstruction_records": _reconstruction_records(recon_meta),
        "overlap_records": _overlap_records(recon_meta),
        "stop_go_records": stop_go,
        "gate_records": _gate_records(fd1_records_decomposed=fd1_records, fd1_private_manifest_record_count=fd1_manifest_count, recon_meta=recon_meta, fd1_private_decomposition_parsed=fd1_private_parsed, replay_artifact_validated=replay_validated, forbidden_scan_pass=True, blocking_failure_count=blocking, exact_prior_exclusion_used=exact_prior_exclusion_used),
        "private_manifest_records": _private_manifest_records(fd1_artifact, extra_manifests),
        "failure_category_count_records": _failure_category_count_records(fcc),
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "private_key_hashes_publicly_serialized": False,
        "exact_keys_publicly_serialized": False,
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
            "is_exact_overlap_resolution_locked_reservoir_audit": True,
            "is_latency_in_relevance": False,
            "signal_strength": "bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_aggregate_only",
            "locked_validation_design_authorization_scope": "stop_go_records_only",
        },
    }
    scan = _v1_p4k_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["stop_go_records"] = [{
            **stop_go[0],
            "stop_go_decision": "fail_forbidden_scan",
            "stop_go_reason": "forbidden_content_leak_blocked",
        }]
    return report


def _build_synthetic_reconstruction(
    *, p4h_count: int = 73, p4i_count: int = 73, p4j_count: int = 333,
    p4j_overlap_with_p4h: int = 61, p4j_overlap_with_p4i: int = 61,
    p4j_python_count: int = 61, p4j_non_python_count: int = 272,
    p4h_match: bool = True, p4i_match: bool = True, p4j_match: bool = True,
    exact_prior_exclusion_used: bool = True,
) -> dict[str, Any]:
    """Build synthetic reconstruction metadata for self-test."""
    locked = p4j_count - p4j_overlap_with_p4h - p4j_overlap_with_p4i
    # For synthetic: overlap with P4H == overlap with P4I (same Python frame)
    # so locked = p4j - 2*overlap only if overlap_p4h != overlap_p4i.  But
    # since P4H==P4I keys, the actual set subtraction is p4j - p4h_keys (not
    # double-counted).  We model this correctly: locked = p4j - overlap_p4h
    # (since p4i_keys == p4h_keys, subtracting both is same as subtracting once).
    locked = p4j_count - p4j_overlap_with_p4h
    non_python_locked = max(0, locked - (p4j_overlap_with_p4h if p4j_overlap_with_p4h > 0 else 0))
    # Actually: locked = non_python rows (since python rows overlap with P4H/P4I)
    non_python_locked = locked
    python_locked = 0
    return {
        "p4h_exact_keys_reconstructed": bool(p4h_match),
        "p4i_exact_keys_reconstructed": bool(p4i_match),
        "p4j_exact_keys_reconstructed": bool(p4j_match),
        "p4h_reconstructed_denominator_count": int(p4h_count),
        "p4i_reconstructed_reservoir_count": int(p4i_count),
        "p4j_reconstructed_upper_bound_count": int(p4j_count),
        "p4j_reconstructed_python_count": int(p4j_python_count),
        "p4j_reconstructed_non_python_count": int(p4j_non_python_count),
        "p4j_overlap_with_p4h_count": int(p4j_overlap_with_p4h),
        "p4j_overlap_with_p4i_count": int(p4j_overlap_with_p4i),
        "locked_cross_source_reservoir_count": int(locked),
        "non_python_locked_reservoir_count": int(non_python_locked),
        "python_locked_reservoir_count": int(python_locked),
        "exact_overlap_resolution_attempted": True,
        "exact_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "fd1_prior_exclusion_used": bool(exact_prior_exclusion_used),
        "python_frame_scan_meta": {"file_miss_selected": p4h_count},
        "cross_source_scan_meta": {
            "file_miss_selected": p4j_count,
            "non_python_file_miss": p4j_non_python_count,
            "python_file_miss": p4j_python_count,
        },
        "reconstruction_mismatch_reasons": [] if (p4h_match and p4i_match and p4j_match) else [
            f"p4h_expected={P4K_EXPECTED_P4H_COUNT};reconstructed={p4h_count}" if not p4h_match else "",
            f"p4i_expected={P4K_EXPECTED_P4I_COUNT};reconstructed={p4i_count}" if not p4i_match else "",
            f"p4j_expected={P4K_EXPECTED_P4J_COUNT};reconstructed={p4j_count}" if not p4j_match else "",
        ],
    }


METRIC_TABLE_KEYS = (
    "source_run_records", "reconstruction_records", "overlap_records",
    "stop_go_records", "gate_records", "private_manifest_records",
    "failure_category_count_records",
)


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("identity_schema", SCHEMA_VERSION == "bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.v1"))
    checks.append(_check("phase_p4k", PHASE == "BEA-v1-P4K"))
    checks.append(_check("claim_level_audit_only", CLAIM_LEVEL == "bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_only"))
    checks.append(_check("diagnostic_arm_baseline_only", DIAGNOSTIC_ARM == "current_bea_candidate_pool_replay"))
    checks.append(_check("policy_arms_count_1", len(POLICY_ARMS) == 1))
    checks.append(_check("no_p2_p3_p4_in_policy_arms", "p2_depth_only_reference" not in POLICY_ARMS and "p3_constrained_depth_policy_reference" not in POLICY_ARMS and "p4_latency_aware_action_scheduler" not in POLICY_ARMS))
    checks.append(_check("expected_p4h_count_73", P4K_EXPECTED_P4H_COUNT == 73))
    checks.append(_check("expected_p4i_count_73", P4K_EXPECTED_P4I_COUNT == 73))
    checks.append(_check("expected_p4j_count_333", P4K_EXPECTED_P4J_COUNT == 333))
    checks.append(_check("locked_reservoir_min_80", P4K_LOCKED_RESERVOIR_MIN_COUNT == 80))
    checks.append(_check("p4j_upper_bound_333", P4J_UPPER_BOUND_COUNT == 333))
    checks.append(_check("p4j_qualified_0", P4J_QUALIFIED_COUNT == 0))
    checks.append(_check("expected_p4j_python_count_61", P4K_EXPECTED_P4J_PYTHON_COUNT == 61))
    checks.append(_check("expected_p4j_non_python_count_272", P4K_EXPECTED_P4J_NON_PYTHON_COUNT == 272))
    checks.append(_check("p4i_reservoir_73", P4I_RESERVOIR_COUNT == 73))
    checks.append(_check("p4h_denominator_73", P4H_DENOMINATOR_COUNT == 73))
    checks.append(_check("latency_not_in_relevance_false", DEFAULT_FALSE_FLAGS["latency_in_candidate_relevance"] is False))
    checks.append(_check("no_selector_change", DEFAULT_FALSE_FLAGS["selector_or_reranker_changed"] is False))
    checks.append(_check("no_selector_executed", DEFAULT_FALSE_FLAGS["selector_or_reranker_executed"] is False))
    checks.append(_check("p5_authorized_false", DEFAULT_FALSE_FLAGS["p5_authorized"] is False))
    checks.append(_check("v1_a_authorized_false", DEFAULT_FALSE_FLAGS["v1_a_authorized"] is False))
    checks.append(_check("frozen_p4_rerun_authorized_false", DEFAULT_FALSE_FLAGS["frozen_p4_rerun_authorized"] is False))
    checks.append(_check("frozen_p4_validation_executed_false", DEFAULT_FALSE_FLAGS["frozen_p4_validation_executed"] is False))
    checks.append(_check("locked_p4_validation_executed_false", DEFAULT_FALSE_FLAGS["locked_p4_validation_executed"] is False))
    checks.append(_check("p2_p3_p4_arms_not_executed_flags", DEFAULT_FALSE_FLAGS["p2_depth_only_reference_executed"] is False and DEFAULT_FALSE_FLAGS["p3_constrained_depth_policy_reference_executed"] is False and DEFAULT_FALSE_FLAGS["p4_latency_aware_action_scheduler_executed"] is False))
    # Canonical key functions
    checks.append(_check("canonical_python_key_format", _canonical_python_key("contextbench", 5) == ("python", "contextbench", 5)))
    checks.append(_check("canonical_non_python_key_format", _canonical_non_python_key("repoqa_non_python_languages", "cpp", 3) == ("non_python", "repoqa_non_python_languages", "cpp", 3)))
    checks.append(_check("canonical_python_key_equality", _canonical_python_key("contextbench", 5) == _canonical_python_key("contextbench", 5)))
    checks.append(_check("canonical_non_python_disjoint_from_python", _canonical_non_python_key("x", "cpp", 0) != _canonical_python_key("x", 0)))
    # Overlap computation
    p4h_keys = {_canonical_python_key("contextbench", i) for i in range(73)}
    p4i_keys = set(p4h_keys)
    p4j_keys = {_canonical_python_key("contextbench", i) for i in range(61)} | {_canonical_non_python_key("contextbench_all_languages", "cpp", i) for i in range(272)}
    overlap = _compute_locked_reservoir(p4h_keys=p4h_keys, p4i_keys=p4i_keys, p4j_keys=p4j_keys)
    checks.append(_check("overlap_p4h_count_61", overlap["p4j_overlap_with_p4h_count"] == 61))
    checks.append(_check("overlap_p4i_count_61", overlap["p4j_overlap_with_p4i_count"] == 61))
    checks.append(_check("locked_count_272", overlap["locked_cross_source_reservoir_count"] == 272))
    checks.append(_check("non_python_locked_272", overlap["non_python_locked_reservoir_count"] == 272))
    checks.append(_check("python_locked_0", overlap["python_locked_reservoir_count"] == 0))
    with tempfile.TemporaryDirectory(prefix="v1p4k_st_") as sd:
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
        scan_manifest = {
            "manifest_name": "bea_v1_p4k_private_reconstruction_manifest",
            "schema_version": "bea_v1_p4k_private_reconstruction.v1",
            "storage_class": "private_tmp_only",
            "record_count": 73 + 333,
            "records_written": True,
            "path_publicly_serialized": False,
            "manifest_hash": "e" * 64,
        }
        # --- Ready (all match, locked >= 80) ---
        recon_ready = _build_synthetic_reconstruction(
            p4h_count=73, p4i_count=73, p4j_count=333,
            p4j_overlap_with_p4h=61, p4j_overlap_with_p4i=61,
            p4j_python_count=61, p4j_non_python_count=272)
        report_ready = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta=recon_ready, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        for table in METRIC_TABLE_KEYS:
            checks.append(_check(f"table_{table}_is_list", isinstance(report_ready.get(table), list)))
        checks.append(_check("ready_status", report_ready.get("status") == "cross_source_locked_reservoir_ready_for_locked_p4_validation_design"))
        checks.append(_check("ready_forbidden_scan_pass", report_ready.get("forbidden_scan", {}).get("status") == "pass"))
        checks.append(_check("ready_locked_count_272", report_ready.get("locked_cross_source_reservoir_count") == 272))
        checks.append(_check("ready_non_python_locked_272", report_ready.get("non_python_locked_reservoir_count") == 272))
        checks.append(_check("ready_python_locked_0", report_ready.get("python_locked_reservoir_count") == 0))
        checks.append(_check("ready_overlap_p4h_61", report_ready.get("p4j_overlap_with_p4h_count") == 61))
        checks.append(_check("ready_overlap_p4i_61", report_ready.get("p4j_overlap_with_p4i_count") == 61))
        checks.append(_check("ready_p4j_python_count_61", report_ready.get("p4j_reconstructed_python_count") == 61))
        checks.append(_check("ready_p4j_non_python_count_272", report_ready.get("p4j_reconstructed_non_python_count") == 272))
        checks.append(_check("ready_authorization_flags_false", report_ready.get("stop_go_records", [{}])[0].get("p5_authorized") is False and report_ready.get("stop_go_records", [{}])[0].get("v1_a_authorized") is False and report_ready.get("stop_go_records", [{}])[0].get("runtime_promotion_authorized") is False and report_ready.get("stop_go_records", [{}])[0].get("method_winner_authorized") is False and report_ready.get("stop_go_records", [{}])[0].get("broad_retrieval_expansion_authorized") is False))
        checks.append(_check("ready_locked_design_authorized_true", report_ready.get("stop_go_records", [{}])[0].get("locked_p4_validation_design_authorized") is True))
        checks.append(_check("ready_scheduler_validation_authorized_false", report_ready.get("stop_go_records", [{}])[0].get("scheduler_validation_authorized") is False))
        checks.append(_check("ready_locked_p4_validation_executed_false", report_ready.get("stop_go_records", [{}])[0].get("locked_p4_validation_executed") is False))
        checks.append(_check("ready_frozen_p4_rerun_false", report_ready.get("stop_go_records", [{}])[0].get("frozen_p4_rerun_authorized") is False))
        checks.append(_check("ready_frozen_p4_validation_executed_false", report_ready.get("stop_go_records", [{}])[0].get("frozen_p4_validation_executed") is False))
        checks.append(_check("ready_top_level_design_scope_stop_go_only", report_ready.get("locked_p4_validation_executed") is False and report_ready.get("framing", {}).get("locked_validation_design_authorization_scope") == "stop_go_records_only"))
        checks.append(_check("ready_p4h_reconstructed_true", report_ready.get("p4h_exact_keys_reconstructed") is True))
        checks.append(_check("ready_p4i_reconstructed_true", report_ready.get("p4i_exact_keys_reconstructed") is True))
        checks.append(_check("ready_p4j_reconstructed_true", report_ready.get("p4j_exact_keys_reconstructed") is True))
        checks.append(_check("ready_exact_keys_not_serialized", report_ready.get("exact_keys_publicly_serialized") is False))
        # --- Insufficient (locked < 80) ---
        recon_insuf = _build_synthetic_reconstruction(
            p4h_count=73, p4i_count=73, p4j_count=100,
            p4j_overlap_with_p4h=73, p4j_overlap_with_p4i=73,
            p4j_python_count=73, p4j_non_python_count=27,
            p4j_match=True)
        report_insuf = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta=recon_insuf, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("insufficient_status", report_insuf.get("status") == "no_go_locked_cross_source_reservoir_insufficient"))
        checks.append(_check("insufficient_locked_27", report_insuf.get("locked_cross_source_reservoir_count") == 27))
        checks.append(_check("insufficient_no_design_auth", report_insuf.get("stop_go_records", [{}])[0].get("locked_p4_validation_design_authorized") is False))
        checks.append(_check("insufficient_scheduler_validation_authorized_false", report_insuf.get("stop_go_records", [{}])[0].get("scheduler_validation_authorized") is False))
        # --- Unavailable (count mismatch) ---
        recon_unavail = _build_synthetic_reconstruction(
            p4h_count=70, p4i_count=73, p4j_count=333,
            p4h_match=False, p4i_match=True, p4j_match=True)
        report_unavail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta=recon_unavail, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("unavailable_status", report_unavail.get("status") == "no_go_exact_overlap_resolution_unavailable"))
        checks.append(_check("unavailable_p4h_mismatch", report_unavail.get("p4h_exact_keys_reconstructed") is False))
        checks.append(_check("unavailable_no_design_auth", report_unavail.get("stop_go_records", [{}])[0].get("locked_p4_validation_design_authorized") is False))
        checks.append(_check("unavailable_scheduler_validation_authorized_false", report_unavail.get("stop_go_records", [{}])[0].get("scheduler_validation_authorized") is False))
        # --- P4J count mismatch ---
        recon_p4j_mismatch = _build_synthetic_reconstruction(
            p4h_count=73, p4i_count=73, p4j_count=330,
            p4h_match=True, p4i_match=True, p4j_match=False)
        report_p4j_mm = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta=recon_p4j_mismatch, audit_match=True, extra_manifests=[scan_manifest], aggregate_runtime_seconds=0.5)
        checks.append(_check("p4j_mismatch_unavailable", report_p4j_mm.get("status") == "no_go_exact_overlap_resolution_unavailable"))
        # --- Default no-network ---
        report_default = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="missing", network_mode="disabled_opt_in", fcc_in={"network_required_but_disabled": 1})
        checks.append(_check("default_unavailable_with_reason", report_default.get("status") == "unavailable_with_reason"))
        checks.append(_check("default_not_ready", report_default.get("status") != "cross_source_locked_reservoir_ready_for_locked_p4_validation_design"))
        checks.append(_check("default_stop_go_unavailable", report_default.get("stop_go_records", [{}])[0].get("stop_go_decision") == "unavailable_with_reason"))
        # --- Blocking failures ---
        report_scan_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta=recon_ready, audit_match=True, fcc_in={"exact_overlap_resolution_scan_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("scan_failure_fail_closed", report_scan_fail.get("status") == "fail_schema_contract"))
        report_clone_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta=recon_ready, audit_match=True, fcc_in={"raw_denominator_clone_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("clone_failure_fail_closed", report_clone_fail.get("status") == "fail_schema_contract"))
        report_asset_fail = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta=recon_ready, audit_match=True, fcc_in={"cross_source_asset_download_failed": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("asset_failure_fail_closed", report_asset_fail.get("status") == "fail_schema_contract"))
        report_exact_missing = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta={**recon_ready, "exact_prior_exclusion_used": False}, audit_match=True, fcc_in={"exact_overlap_resolution_unavailable": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("exact_prior_missing_fail_closed", report_exact_missing.get("status") == "fail_schema_contract"))
        report_not_attempted = _base_report(status="auto", failure_reason_category="", self_test_passed=True, self_test_checks_total=0, self_test_checks_passed=None, openlocus_binary_source="self_test", network_mode="self_test", fd1_artifact=fd1_art, fd1_schema=p4.FD1_SOURCE_SCHEMA_VERSION, fd1_hash="b" * 64, pt=pt, rav=rav, p4h_artifact=p4h_art, p4i_artifact=p4i_art, p4j_artifact=p4j_art, recon_meta={**recon_ready, "exact_overlap_resolution_attempted": False}, audit_match=True, fcc_in={"exact_overlap_resolution_scan_not_attempted": 1}, aggregate_runtime_seconds=0.5)
        checks.append(_check("not_attempted_fail_closed", report_not_attempted.get("status") == "fail_schema_contract"))
        # --- Public shape / privacy ---
        checks.append(_check("public_shape_no_dynamic_dicts", _has_dynamic_dict(report_ready) is False))
        checks.append(_check("manifest_fields_safe", _manifest_fields_safe(report_ready.get("private_manifest_records", [])) is True))
        manifest_has_hash = any(m.get("manifest_hash") for m in report_ready.get("private_manifest_records", []) if isinstance(m, dict))
        checks.append(_check("manifest_has_provenance_hash", manifest_has_hash is True))
        checks.append(_check("manifest_no_private_paths", all(m.get("path_publicly_serialized") is False for m in report_ready.get("private_manifest_records", []) if isinstance(m, dict))))
        # --- Forbidden scanner ---
        leaked = dict(report_ready)
        leaked["private_record_id"] = "leak"
        checks.append(_check("scanner_rejects_private_record_id", _v1_p4k_forbidden_scan_summary(leaked)["status"] == "fail"))
        leaked2 = dict(report_ready)
        leaked2["exact_keys_private"] = ["leak"]
        checks.append(_check("scanner_rejects_exact_keys_private", _v1_p4k_forbidden_scan_summary(leaked2)["status"] == "fail"))
        leaked3 = dict(report_ready)
        leaked3["p4h_exact_keys"] = "leak"
        checks.append(_check("scanner_rejects_p4h_exact_keys", _v1_p4k_forbidden_scan_summary(leaked3)["status"] == "fail"))
        leaked4 = dict(report_ready)
        leaked4["canonical_keys"] = "leak"
        checks.append(_check("scanner_rejects_canonical_keys", _v1_p4k_forbidden_scan_summary(leaked4)["status"] == "fail"))
        leaked5 = dict(report_ready)
        leaked5["reconstruction_private_path"] = "leak"
        checks.append(_check("scanner_rejects_reconstruction_path", _v1_p4k_forbidden_scan_summary(leaked5)["status"] == "fail"))
        checks.append(_check("forbidden_violation_categories_is_list", isinstance(report_ready.get("forbidden_scan", {}).get("violation_categories"), list)))
        # --- Gates ---
        checks.append(_check("ready_locked_gate_pass", bool(report_ready.get("gate_records") and any(g.get("gate") == "locked_cross_source_reservoir_min" and g.get("passed") is True for g in report_ready.get("gate_records", [])))))
        checks.append(_check("insufficient_locked_gate_fail", bool(report_insuf.get("gate_records") and any(g.get("gate") == "locked_cross_source_reservoir_min" and g.get("passed") is False for g in report_insuf.get("gate_records", [])))))
        checks.append(_check("ready_p4h_reconstruction_gate_pass", bool(report_ready.get("gate_records") and any(g.get("gate") == "p4h_exact_keys_reconstructed" and g.get("passed") is True for g in report_ready.get("gate_records", [])))))
        checks.append(_check("unavailable_p4h_gate_fail", bool(report_unavail.get("gate_records") and any(g.get("gate") == "p4h_exact_keys_reconstructed" and g.get("passed") is False for g in report_unavail.get("gate_records", [])))))
        # --- Reconstruction/overlap records ---
        checks.append(_check("reconstruction_records_count_5", len(report_ready.get("reconstruction_records", [])) == 5))
        checks.append(_check("overlap_records_count_2", len(report_ready.get("overlap_records", [])) == 2))
        checks.append(_check("reconstruction_records_no_keys", all("exact_keys" not in r and "canonical_keys" not in r for r in report_ready.get("reconstruction_records", []))))
    parser = build_parser()
    opts = {opt for action in parser._actions for opt in action.option_strings}
    for opt in ("--self-test", "--out", "--fd1-artifact", "--fd1-private-decomposition-jsonl", "--fd1-replay-artifact", "--p4h-artifact", "--p4i-artifact", "--p4j-artifact", "--openlocus", "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in opts))
    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(description="BEA-v1-P4K Exact Overlap Resolution & Locked Reservoir Audit")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd1-private-decomposition-jsonl", type=Path, default=None)
    ap.add_argument("--fd1-replay-artifact", type=Path, default=None)
    ap.add_argument("--p4h-artifact", type=Path, default=DEFAULT_P4H_ARTIFACT)
    ap.add_argument("--p4i-artifact", type=Path, default=DEFAULT_P4I_ARTIFACT)
    ap.add_argument("--p4j-artifact", type=Path, default=DEFAULT_P4J_ARTIFACT)
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
        report = _base_report(status="fail_schema_contract", failure_reason_category="openlocus_binary_missing", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source, network_mode=network_mode, fcc_in={"openlocus_binary_missing": 1, "exact_overlap_resolution_scan_failed": 1})
    elif not enable_network:
        report = _base_report(status="unavailable_with_reason", failure_reason_category="network_required_but_disabled", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "missing", network_mode=network_mode, fcc_in={"network_required_but_disabled": 1})
    else:
        try:
            report = _run_exact_overlap_resolution(openlocus_bin=openlocus_bin or "", openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, self_test_passed=True, self_test_checks_total=len(checks), fd1_artifact_path=args.fd1_artifact, fd1_private_decomposition_jsonl=args.fd1_private_decomposition_jsonl, fd1_replay_artifact=args.fd1_replay_artifact, p4h_artifact_path=args.p4h_artifact, p4i_artifact_path=args.p4i_artifact, p4j_artifact_path=args.p4j_artifact, enable_network=enable_network)
        except Exception:
            report = _base_report(status="fail_schema_contract", failure_reason_category="unexpected_exception", self_test_passed=True, self_test_checks_total=len(checks), self_test_checks_passed=None, openlocus_binary_source=openlocus_source or "explicit", network_mode=network_mode, fcc_in={"unexpected_exception": 1, "exact_overlap_resolution_scan_failed": 1})
    if report.get("provider_calls_made") is not False or report.get("latency_in_candidate_relevance") is not False or report.get("gold_labels_used_for_policy") is not False or report.get("query_anchors_used_in_p4_arm") is not False or report.get("p2_depth_only_reference_executed") is not False or report.get("p3_constrained_depth_policy_reference_executed") is not False or report.get("p4_latency_aware_action_scheduler_executed") is not False or report.get("selector_or_reranker_executed") is not False or report.get("v1_a_selector_executed") is not False:
        report["status"] = "fail_schema_contract"
    _enforce_v1_p4k_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    sgr = report.get("stop_go_records", [{}])[0] if report.get("stop_go_records") else {}
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, status={report['status']}, phase={report['phase']}, locked_count={report.get('locked_cross_source_reservoir_count', 0)}, stop_go_decision={sgr.get('stop_go_decision', '')})")
    if not enable_network:
        print("enable_external_benchmark_network is false; skipping real BEA-v1-P4K exact overlap resolution audit.")


if __name__ == "__main__":
    main()
