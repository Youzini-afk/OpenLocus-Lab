#!/usr/bin/env python3
"""BEA-v1-P2: Candidate Availability / Retrieval Reach Smoke (Public Records-Only).

BEA-v1-P2 is the **second phase of BEA v1 Hierarchical Actionable Evidence
Acquisition**, run after the BEA-v1-P1 result checkpoint ``d96e860``.
P1 parsed the validated FD1 private replay (86040 rows / 239 groups) and
rejected selector-only BEA-v1-A: ``gold_file_absent`` denominator=119,
file-selector lower-bound recoverable count=1, retrieval availability
rate=0.991597. A selector cannot recover absent gold files. P2 tests
candidate availability / retrieval reach, not selection.

Goal
----

Run a deterministic, provider-free, network-enabled retrieval reach smoke
over the FD1 ``gold_file_absent`` denominator (exactly 119 records).
Compare the current BEA candidate pool with small runtime-clean
expansion arms to determine whether gold files become available before
selector work.

Arms (3 + optional combined):

1. ``current_bea_candidate_pool_replay`` — current BEA runtime-clean
   retrieval pool (bm25/regex/symbol + RRF/derived RRF). Anchors the
   v1-P1 baseline.
2. ``expanded_pool_more_depth_same_methods`` — same methods, larger
   candidate generation depth before packing. Tests truncation vs
   true retrieval miss.
3. ``expanded_pool_query_anchor_variants`` — runtime-clean query
   variants from public task text only (identifier tokens, path-like
   tokens, symbol-like tokens, import/package tokens if present,
   camel/snake splits). No gold paths, private labels, role/support
   proxy, or post-hoc tuning.
4. (optional combined) ``expanded_pool_depth_plus_query_anchor`` —
   depth expansion + query-anchor variants together. Only included if
   cheap and does not change the discipline.

Binding invariants
------------------

* claim_level = ``bea_v1_p2_candidate_availability_reach_smoke_only``
* status: ``bea_v1_p2_retrieval_reach_pass`` |
  ``no_go_retrieval_reach_insufficient`` |
  ``no_go_retrieval_reach_latency_or_pool_cost`` |
  ``no_go_replay_mismatch`` | ``unavailable_with_reason`` |
  ``fail_forbidden_scan`` | ``fail_schema_contract``
* mode = ``bea_v1_p2_candidate_availability_reach_smoke``; phase =
  ``BEA-v1-P2``

* The BEA-v1-P2 evaluator itself does NOT run retrieval/selector
  provider calls; the CI workflow regenerates the FD1 private
  decomposition under ``$RUNNER_TEMP`` AND reruns the BEA-v1-P2
  retrieval smoke (network + OpenLocus binary, no provider secrets).
  Gold/private labels are used ONLY for evaluation/scoring reach,
  never to construct queries/candidates.
* No role/support proxies. No v0.4 repair. No FD2-B/FD2-C. No
  v0.31/v0.32 tuning. No B16-K. No dense/graph/QuIVer quality mixing.
  No selector/packer runtime change.
* Public artifact is aggregate-only and records-only. No public record
  IDs, paths, queries, snippets, gold files, candidate lists, per-record
  ranks, private trace paths, or private row payloads.

Network / CI policy (binding)
-----------------------------

* Default no-network self-test passes without HuggingFace/GitHub and
  without the committed FD1 / FD2-A1 artifacts or any private JSONL
  (self-test uses synthetic FD1 aggregate and synthetic reach rows).
* Default no-network / no-private-JSONL artifact is truthfully
  ``no_go_replay_mismatch`` (no fake pass). The CI workflow
  regenerates the FD1 private decomposition under ``/tmp``,
  validates it, reruns the P2 retrieval smoke, and passes the JSONL +
  replay report + reach results via CLI args.
* CI is a separate explicit workflow_dispatch job; it must NOT run on
  PR/push by default, must use no provider secrets/vars/model env, and
  must upload only the aggregate report. Private JSONL/JSON files are
  NEVER uploaded.

Run::

    python3 -m py_compile eval/bea_v1_p2_candidate_availability_reach_smoke.py
    python3 eval/bea_v1_p2_candidate_availability_reach_smoke.py --self-test
    python3 eval/bea_v1_p2_candidate_availability_reach_smoke.py \\
        --out artifacts/bea_v1_p2_candidate_availability_reach/\\
bea_v1_p2_candidate_availability_reach_smoke_report.json

To authorize v1-A reopen, the CI workflow regenerates the FD1 private
decomposition AND runs the P2 retrieval smoke, then passes the results
to the evaluator::

    python3 eval/bea_fd1_failure_decomposition.py \\
        --enable-external-benchmark-network \\
        --private-decomposition-dir /tmp/fd1_private \\
        --openlocus target/release/openlocus \\
        --out /tmp/fd1_replay_report.json
    python3 eval/bea_v1_p2_candidate_availability_reach_smoke.py \\
        --enable-external-benchmark-network \\
        --openlocus target/release/openlocus \\
        --fd1-private-decomposition-jsonl /tmp/fd1_private/bea_fd1.decomposition.jsonl \\
        --fd1-replay-artifact /tmp/fd1_replay_report.json \\
        --out artifacts/bea_v1_p2_candidate_availability_reach/bea_v1_p2_candidate_availability_reach_smoke_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

# Reuse the P1 evaluator's scanner composition, FD1 replay validation,
# and c5a helpers. BEA-v1-P2 does NOT import any BEA-v0.4-P1/P2/P3
# module, does NOT use role proxies, and does NOT run a selector.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea_v1_p1_actionability_audit as bea_v1_p1  # noqa: E402
import bea_fd1_failure_decomposition as bea_fd1  # noqa: E402
import bea4_external_scale_smoke as bea4  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import bea1_mechanism_ablation as bea1  # noqa: E402
import bea5_frozen_policy_robustness as bea5  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402

# --- Schema / claim constants ---
SCHEMA_VERSION = "bea_v1_p2_candidate_availability_reach_smoke.v1"
GENERATED_BY = "eval/bea_v1_p2_candidate_availability_reach_smoke.py"
CLAIM_LEVEL = "bea_v1_p2_candidate_availability_reach_smoke_only"
MODE = "bea_v1_p2_candidate_availability_reach_smoke"
PHASE = "BEA-v1-P2"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p2_candidate_availability_reach/"
    "bea_v1_p2_candidate_availability_reach_smoke_report.json"
)
DEFAULT_FD1_ARTIFACT = bea_fd1.DEFAULT_OUT
DEFAULT_FD2A1_ARTIFACT = Path(
    "artifacts/bea_fd2a1_failure_attribution/"
    "bea_fd2a1_failure_attribution_replay_report.json"
)

# --- P1 binding context (read-only) ---
V1_P1_RESULT_CHECKPOINT = "d96e860"
V1_P1_RESULT_STATUS = "no_go_retrieval_availability_limit"
V1_P1_GOLD_FILE_ABSENT_DENOMINATOR = 119
V1_P1_FILE_SELECTOR_LOWER_BOUND = 1
V1_P1_RETRIEVAL_AVAILABILITY_RATE = 0.991597

FD1_SOURCE_CI_RUN_ID = "28011901294"
FD1_SOURCE_LOCAL_CHECKPOINT = "29c5a1a"
FD1_SOURCE_STATUS = "bea_fd1_decomposition_pass"
FD1_SOURCE_SCHEMA_VERSION = bea_fd1.SCHEMA_VERSION

# Fixed budget / methods inherited from FD1 (reach smoke does not
# change them; expanded arms change depth/query construction only).
FIXED_BUDGET = bea_fd1.FIXED_BUDGET  # 5
FIXED_METHODS = tuple(bea_fd1.FIXED_METHODS.split(","))  # bm25,regex,symbol

# FD1 frame expectations (binding).
EXPECTED_RECORDS_DECOMPOSED = bea_fd1.EXPECTED_DECOMPOSED_RECORDS  # 239
EXPECTED_PRIVATE_DECOMP_ROWS = bea_fd1.EXPECTED_PRIVATE_DECOMP_ROWS  # 86040
EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR = 119

# --- Retrieval reach arms ---
REACH_ARMS = (
    "current_bea_candidate_pool_replay",
    "expanded_pool_more_depth_same_methods",
    "expanded_pool_query_anchor_variants",
    "expanded_pool_depth_plus_query_anchor",
)

# Depth multipliers for expanded arms (vs current pool's default depth).
DEFAULT_DEPTH_MULTIPLIER = 1
EXPANDED_DEPTH_MULTIPLIER = 4  # 4x candidate generation depth
DEFAULT_RETRIEVAL_LIMIT = 20
MAX_QUERY_VARIANTS_PER_ARM = 4

# Rank bands for reach bucketing.
RANK_BANDS = (10, 50, 100, 200)

# --- Statuses enum (binding) ---
STATUSES = (
    "bea_v1_p2_retrieval_reach_pass",
    "no_go_retrieval_reach_insufficient",
    "no_go_retrieval_reach_latency_or_pool_cost",
    "no_go_replay_mismatch",
    "unavailable_with_reason",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "bea_v1_p2_retrieval_reach_pass",
    "no_go_retrieval_reach_insufficient",
    "no_go_retrieval_reach_latency_or_pool_cost",
    "no_go_replay_mismatch",
})

# --- Stop / go thresholds (binding; mirror plan stop rules) ---
# Newly reachable gold files on the 119 denominator must be material.
GO_NEWLY_AVAILABLE_COUNT_MIN = 25
GO_AVAILABILITY_LIFT_MIN = 0.20
# Pool / latency cost safety.
NO_GO_POOL_SIZE_MAX_MULTIPLIER = 4  # pool <= 4x baseline
NO_GO_LATENCY_MAX_MULTIPLIER = 2  # latency <= 2x baseline

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "fd1_artifact_read": False,
    "fd2a1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd2a1_artifact_modified": False,
    "bea_v1_p2_reach_smoke_performed": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "retrieval_reach_executed": False,
    "bea_v1_p2_audit_evaluator_no_provider_calls": True,
    "bea_v1_p2_audit_evaluator_no_selector_executed": True,
    "bea_v1_p2_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p2_audit_evaluator_no_role_proxy": True,
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
    "algorithm_changed_during_bea_v1_p2": False,
    "weights_tuned_during_bea_v1_p2": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p2": False,
    "v1_a_selector_executed": False,
    "v1_a_coverage_preserving_selector_promoted": False,
    "fd2b_executed": False,
    "fd2c_executed": False,
    "p4_executed": False,
    "p5_executed": False,
    "v031_tuning_executed": False,
    "v032_tuning_executed": False,
    "b16k_executed": False,
    "role_proxy_assigned": False,
    "posthoc_threshold_search": False,
    "private_decomposition_used_for_selection": False,
    "gold_labels_used_for_selection": False,
    "gold_labels_used_for_query_construction": False,
    "new_records_added_during_bea_v1_p2": False,
    "heldout_validation_claimed": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_candidate_availability_reach_smoke",
}

# Audit-level failure categories (NOT the FD1 categories).
FAILURE_CATEGORIES_AUDIT = (
    "fd1_artifact_missing", "fd1_artifact_parse_failed",
    "fd1_schema_version_mismatch", "fd1_status_mismatch",
    "fd1_records_decomposed_mismatch", "fd1_private_manifest_mismatch",
    "fd1_availability_table_missing", "fd1_category_summary_missing",
    "fd1_private_decomposition_missing",
    "fd1_private_decomposition_parse_failed",
    "fd1_private_decomposition_count_mismatch",
    "fd1_private_decomposition_group_mismatch",
    "fd1_replay_artifact_missing",
    "fd1_replay_artifact_parse_failed",
    "fd1_replay_artifact_schema_mismatch",
    "fd1_replay_artifact_status_mismatch",
    "fd1_replay_artifact_records_mismatch",
    "fd1_replay_artifact_manifest_mismatch",
    "fd1_replay_artifact_manifest_hash_mismatch",
    "fd1_replay_artifact_forbidden_scan_failed",
    "denominator_mismatch",
    "denominator_mapping_failed",
    "retrieval_smoke_failed",
    "openlocus_binary_missing",
    "network_required_but_disabled",
    "scanner_self_test_failed", "forbidden_leak_blocked",
    "duplicate_record_key_blocked",
    "unexpected_exception",
)
BLOCKING_FAILURE_CATEGORIES = (
    "forbidden_leak_blocked", "unexpected_exception",
    "fd1_artifact_missing", "fd1_artifact_parse_failed",
)

# ---------------------------------------------------------------------------
# Scanner (strict, fail-closed). Composes the P1 scanner; adds
# BEA-v1-P2-specific reach-private rejections.
# ---------------------------------------------------------------------------

# BEA-v1-P2 forbidden extra top-level keys (reach-private / per-record /
# claim / dynamic-dict mirrors / forbidden scope). Inherits the full
# FD1 + P1 forbidden-key discipline via ``bea_v1_p1._scan_v1_p1``.
V1_P2_FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        # private trace paths / dirs (BEA-v1-P2 must not serialize them)
        "private_trace_dir", "trace_dir", "private_score_dir",
        "private_audit_dir", "audit_trace_path",
        "private_decomposition_dir", "private_reach_dir",
        "private_decomposition_path", "private_decomposition_file",
        "private_reach_path", "private_reach_file",
        "retrieval_trace_path", "candidate_trace_path",
        # per-record reach detail (aggregate counts only)
        "per_record_reach", "per_record_candidates",
        "per_record_query_variants", "per_record_gold_match",
        "per_record_pool_size", "per_record_latency",
        "per_record_ranks", "record_reach_detail",
        "record_candidate_lists", "record_query_variants",
        # private / per-record candidate / query / path / span / snippet
        "candidate_paths", "candidate_keys", "candidate_list",
        "candidates", "final_candidates", "accepted_candidates",
        "query_text", "queries", "query_variants",
        "gold_paths", "gold_lines", "gold_spans", "gold_content",
        "gold_files", "gold_file_set", "gold_match_labels",
        "snippets", "selected_paths", "selected_order",
        "private_record_ids", "record_ids", "private_record_id",
        "benchmark_row_id", "phase_run_id", "run_id",
        "task_id", "row_id", "needle_id", "instance_id",
        "repo_url", "base_commit", "repo_slug", "repo_name",
        # objective-config / weights / raw trace payloads (audit-private)
        "objective_config_payload", "fd1_category_weights_payload",
        "weight_derivation_payload", "frozen_weights_payload",
        "raw_score_row", "raw_decision_row",
        "raw_feature_row", "raw_decomposition_row",
        "raw_reach_row", "raw_candidate_row",
        # FD1 / FD2-A1 / P1 source artifact paths (private; only hash/schema)
        "fd1_source_artifact_path", "fd2a1_source_artifact_path",
        "fd2a_source_artifact_path", "v1_p1_source_artifact_path",
        "fd1_replay_artifact_path", "reach_results_path",
        # claim / promotion (BEA-v1-P2 is reach smoke only)
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion", "calibration",
        "method_winner", "best_method",
        # self-test details (counts only)
        "self_test_checks", "self_test_details", "self_test_list",
        "checks", "check_list",
        # dynamic dict mirrors (forbidden as top-level; records-only)
        "hard_gates", "failure_category_counts",
        "arm_reach_counts", "arm_delta_counts",
        "reach_bucket_counts", "rank_band_counts",
        "cost_safety_counts", "stop_go_counts",
        # forbidden scope flags (BEA-v1-P2 is NOT these)
        "is_v04_repair", "is_fd2_b", "is_fd2_c", "is_p4", "is_p5",
        "is_v031_tuning", "is_v032_tuning", "is_b16k",
        "is_selector_phase", "is_acquisition_phase",
        "is_dense_quality_mixing", "is_graph_quality_mixing",
        "is_quiver_quality_mixing",
        "role_proxy", "role_proxy_assignment", "target_proxy",
        "support_proxy", "target_anchor", "target_support_pair",
        "role_proxy_used", "target_support_proxy_used",
    }
)

# Container keys whose record rows may legitimately carry a key that is
# forbidden as a top-level field (records-only discipline).
V1_P2_CONTAINER_KEYS = frozenset({
    "source_run_records", "denominator_records",
    "arm_reach_records", "arm_delta_records",
    "reach_bucket_records", "rank_band_records",
    "cost_safety_records", "stop_go_records",
    "gate_records", "private_manifest_records",
    "failure_category_count_records", "framing",
})


def _is_v1_p2_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in V1_P2_CONTAINER_KEYS


def _scan_v1_p2_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_v1_p2_schema_key_container(sub_path)
                if (key_str in V1_P2_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_v1_p2_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


# BEA-v1-P2-specific safe VALUE path last-key segments. These keys MAY
# hold long policy strings or 64-char hex artifact hashes without
# triggering the primitive long_string / hex_digest_value checks.
V1_P2_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version", "generated_by", "generated_at",
        "claim_level", "status", "mode", "phase",
        "failure_reason_category", "signal_strength",
        "storage_class", "openlocus_binary_source", "network_mode",
        "source_sampling_protocol", "sampling_protocol_version",
        "source_artifact_status", "source_phase", "source_status",
        "source_checkpoint", "source_ci_run_id",
        "source_local_checkpoint",
        "replay_mismatch_reason", "replay_match_basis",
        "ceiling_name", "ceiling_class", "ceiling_basis",
        "ceiling_reason", "cell_class", "action_layer",
        "failure_category", "stop_go_decision", "stop_go_reason",
        "tradeoff_axis", "tradeoff_class", "tradeoff_basis",
        "tradeoff_reason",
        "gate", "threshold_relation", "manifest_name",
        "fd1_source_schema_version", "fd1_source_artifact_hash",
        "fd1_source_status", "fd2a1_source_schema_version",
        "fd2a1_source_artifact_hash", "fd2a1_result_checkpoint",
        "fd2a1_result_status", "manifest_hash",
        "replay_artifact_manifest_hash",
        "replay_artifact_schema_version",
        "replay_artifact_manifest_schema_version",
        "replay_artifact_status",
        "v1_p1_result_checkpoint", "v1_p1_result_status",
        "arm_name", "arm_class", "reach_bucket", "rank_band",
        "cost_safety_axis", "cost_safety_class",
        "treatment_arm", "baseline_arm",
        "fd1_overlap_policy", "fd1_source_overlap_policy",
        "excluded_prior_windows_policy",
    }
)


def _v1_p2_safe_value_path(path: str) -> bool:
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in V1_P2_SAFE_VALUE_PATH_LAST_KEYS


def _scan_v1_p2(obj: Any) -> list[dict[str, Any]]:
    # Compose with the P1 scanner (which composes FD1/BEA-5/BEA-3),
    # then add BEA-v1-P2-specific rejections. Filter primitive false
    # positives for BEA-v1-P2-safe value paths.
    violations = bea_v1_p1._scan_v1_p1(obj)
    violations.extend(_scan_v1_p2_forbidden_keys(obj))
    filtered: list[dict[str, Any]] = []
    for v in violations:
        cat = v.get("category")
        if cat in ("long_string", "hex_digest_value",
                   "forbidden_field_name_value",
                   "repo_slug_value",
                   "line_range_value") and _v1_p2_safe_value_path(
                v.get("path", "")):
            continue
        filtered.append(v)
    return filtered


def _v1_p2_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p2(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_v1_p2_no_forbidden(obj: Any) -> None:
    scan = _v1_p2_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return c5a._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    c5a._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5a._check(name, ok)


def _check_unique_records(
    records: list[dict[str, Any]], key_fn: Any, table_name: str,
) -> list[dict[str, Any]]:
    return bea_v1_p1._check_unique_records(records, key_fn, table_name)


# --- Natural keys for BEA-v1-P2 public record tables ---


def _srr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["source_ci_run_id"])


def _dnr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["benchmark"])


def _arr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"],)


def _adr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"],)


def _rbr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"], rec["reach_bucket"])


def _rkr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"], rec["rank_band"])


def _csr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["cost_safety_axis"],)


def _sgr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["stop_go_decision"],)


def _gr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["gate"],)


def _pmr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["manifest_name"],)


def _fccr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["failure_category"],)


# ---------------------------------------------------------------------------
# FD1 private decomposition parser + denominator extractor
# (reuse P1's ParsedPrivateDecomposition / parser, extend for denominator)
# ---------------------------------------------------------------------------


def _parse_private_decomposition_jsonl(
    path: Path | None,
) -> bea_v1_p1.ParsedPrivateDecomposition:
    """Delegate to P1's parser (identical schema)."""
    return bea_v1_p1._parse_private_decomposition_jsonl(path)


def _compute_file_selector_lower_bound(
    pt: bea_v1_p1.ParsedPrivateDecomposition,
) -> None:
    """Delegate to P1's lower-bound computer."""
    bea_v1_p1._compute_file_selector_lower_bound(pt)


def _validate_fd1_replay_artifact(
    replay_artifact_path: Path | None,
    committed_fd1_manifest_hash: str,
) -> bea_v1_p1.Fd1ReplayArtifactValidation:
    """Delegate to P1's replay-artifact validator."""
    return bea_v1_p1._validate_fd1_replay_artifact(
        replay_artifact_path, committed_fd1_manifest_hash)


def _load_committed_artifact(
    artifact_path: Path,
) -> tuple[dict[str, Any], str, str, str]:
    return bea_v1_p1._load_committed_artifact(artifact_path)


# ---------------------------------------------------------------------------
# FD1 denominator extraction (gold_file_absent records)
# ---------------------------------------------------------------------------


class DenominatorRecord:
    """One FD1 gold_file_absent denominator record (in-memory only).

    Maps an FD1 private_record_id (e.g. ``contextbench-3``) back to its
    source benchmark record. All fields are private; only aggregate
    counts are published.
    """

    def __init__(
        self, private_record_id: str, source_phase: str, benchmark: str,
        record_index: int,
    ) -> None:
        self.private_record_id = private_record_id
        self.source_phase = source_phase
        self.benchmark = benchmark
        self.record_index = record_index  # heldout offset in source benchmark


def _parse_record_id(rid: str) -> tuple[str, int] | None:
    """Parse an FD1 private_record_id like ``contextbench-3`` or
    ``repoqa-7`` into ``(benchmark, index)``. Returns None if the
    format is unrecognized.
    """
    m = re.match(r"^(contextbench|repoqa)-(\d+)$", rid)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def _extract_denominator_from_private(
    pt: bea_v1_p1.ParsedPrivateDecomposition,
) -> list[DenominatorRecord]:
    """Extract the FD1 ``gold_file_absent`` denominator from the parsed
    private decomposition rows.

    A record is in the denominator iff v0.3 ``file_recall@10`` == 0 AND
    ``success_rate`` == 0 (matches FD1's
    ``_classify_from_private_rows`` rule and P1's lower-bound logic).

    Returns the list of :class:`DenominatorRecord` (in-memory only;
    never serialized). Each record's ``record_index`` is the heldout
    offset in the source benchmark (BEA-4: contextbench offset 80 +
    idx, repoqa offset 40 + idx; BEA-5: contextbench idx, repoqa idx).
    """
    # Index treatment_value by (source_phase, private_record_id, metric).
    # BEA-4 and BEA-5 both use ids like contextbench-0 / repoqa-0; using the
    # bare id would merge distinct source runs and reproduce the exact class
    # of bug fixed in BEA-v1-P1.
    treatment_lookup: dict[tuple[str, str, str], float] = {}
    all_keys: set[tuple[str, str]] = set()
    for row in pt.rows:
        rid = str(row.get("private_record_id", "") or "")
        if not rid:
            continue
        sp = str(row.get("source_phase", "") or "")
        if not sp:
            continue
        all_keys.add((sp, rid))
        metric = str(row.get("metric", "") or "")
        if metric in ("file_recall@10", "success_rate"):
            try:
                t_val = float(row.get("treatment_value", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            treatment_lookup.setdefault((sp, rid, metric), t_val)

    denominator: list[DenominatorRecord] = []
    for sp, rid in sorted(all_keys):
        file_recall = treatment_lookup.get((sp, rid, "file_recall@10"), 0.0)
        success = treatment_lookup.get((sp, rid, "success_rate"), 0.0)
        if file_recall == 0.0 and success == 0.0:
            parsed = _parse_record_id(rid)
            if parsed is None:
                continue
            benchmark, idx = parsed
            denominator.append(DenominatorRecord(
                private_record_id=rid,
                source_phase=sp,
                benchmark=benchmark,
                record_index=idx,
            ))
    return denominator


# ---------------------------------------------------------------------------
# Runtime-clean query variant construction (public task text only)
# ---------------------------------------------------------------------------


def _build_query_variants(query: str) -> list[str]:
    """Build runtime-clean query variants from public task text only.

    No gold paths, private labels, role/support proxy, or post-hoc
    tuning. Variants:
      - identifier tokens (CamelCase / snake_case / ALL_CAPS)
      - path-like tokens (foo/bar/baz.py)
      - symbol-like tokens (def/class names, dotted imports)
      - import/package tokens (import foo.bar)
      - camel/snake splits

    Returns a list of variant queries (deduplicated; the original
    query is always included as the first element).
    """
    variants: list[str] = [query]
    seen: set[str] = {query}

    def _add(v: str) -> None:
        v = v.strip()
        if v and v not in seen and len(v) >= 2:
            seen.add(v)
            variants.append(v)

    # Identifier tokens: CamelCase, snake_case, ALL_CAPS.
    for m in re.finditer(r"\b[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b", query):
        _add(m.group(0))
    for m in re.finditer(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", query):
        _add(m.group(0))
    for m in re.finditer(r"\b[A-Z][A-Z0-9_]{2,}\b", query):
        _add(m.group(0))

    # Path-like tokens: foo/bar/baz.py or foo/bar/baz
    for m in re.finditer(r"\b[a-zA-Z0-9_\-]+(?:/[a-zA-Z0-9_\-\.]+)+\b", query):
        _add(m.group(0))

    # Symbol-like tokens: def foo, class Foo, foo.bar.baz
    for m in re.finditer(r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+\b", query):
        _add(m.group(0))

    # Import/package tokens: import foo, from foo.bar import baz
    for m in re.finditer(r"(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_\.]+)", query):
        _add(m.group(1))

    # Camel/snake splits: split CamelCase into words, split snake_case.
    for token in list(seen):
        # CamelCase split
        parts = re.split(r"(?=[A-Z])", token)
        if len(parts) > 1:
            joined = " ".join(p for p in parts if p)
            _add(joined)
        # snake_case split
        if "_" in token:
            parts = token.split("_")
            joined = " ".join(p for p in parts if p)
            _add(joined)

    return variants


def _regex_safe_query(query: str) -> str:
    """Return a literal regex pattern for runtime-clean task text."""
    return re.escape(str(query or "")[:512])


def _symbol_safe_query(query: str) -> str:
    """Return a regex-safe symbol-ish query token.

    Symbol search mode can fall back to regex internally. Feeding the raw
    public issue text can fail on unmatched brackets or other regex syntax.
    This helper keeps the source runtime-clean while preventing query syntax
    from becoming a retrieval failure.
    """
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,80}", str(query or ""))
    if tokens:
        return re.escape(tokens[0])
    words = re.findall(r"[A-Za-z0-9_]{2,80}", str(query or ""))
    if words:
        return re.escape(words[0])
    return re.escape(str(query or "")[:80]) or r"$^"


def _collect_method_candidates_limited(
    openlocus_bin: str,
    method: str,
    query: str,
    cwd: Path,
    limit: int,
) -> tuple[list[dict[str, Any]], int, str]:
    """Collect candidates with explicit depth where the CLI supports it.

    ``bea0._collect_method_candidates`` intentionally uses the default CLI
    limit. P2's depth arm needs a real larger candidate frontier, so this
    local helper shells out with ``--limit`` for bm25/symbol/RRF. Regex has no
    limit flag in the current CLI, so it remains the runtime-clean regex
    default.
    """
    if method == "regex":
        cmd = [openlocus_bin, "search", "regex", _regex_safe_query(query), "--json"]
    elif method == "bm25":
        cmd = [
            openlocus_bin, "search", "bm25", query, "--json",
            "--limit", str(int(limit)),
        ]
    elif method == "symbol":
        cmd = [
            openlocus_bin, "search", "symbol", _symbol_safe_query(query), "--json",
            "--limit", str(int(limit)),
        ]
    else:
        return [], 0, "retrieval_failed"
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, check=False, text=True, capture_output=True, cwd=str(cwd),
            timeout=60,
        )
    except Exception:
        return [], 0, "retrieval_failed"
    latency_ms = int((time.perf_counter() - t0) * 1000)
    if proc.returncode != 0:
        return [], latency_ms, f"returncode_{proc.returncode}"
    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else []
    except json.JSONDecodeError:
        return [], latency_ms, "invalid_json"
    if not isinstance(raw, list):
        raw = []
    candidates = [
        bea0._normalize_candidate(method, idx + 1, ev)
        for idx, ev in enumerate(raw)
        if isinstance(ev, dict)
    ]
    if candidates:
        max_score = max(abs(c["score"]) for c in candidates) or 0.0
        if max_score > 0:
            for cand in candidates:
                cand["normalized_score"] = round(cand["score"] / max_score, 6)
    return candidates, latency_ms, (proc.stderr[:500] if proc.stderr else "")


def _derive_rrf_candidates_from_candidates(
    candidates: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Derive RRF candidates from already-collected method ranks.

    The CLI ``retrieve`` path runs a regex channel internally. Some public
    task text contains regex metacharacters, so P2 derives the required RRF
    baseline from the bm25/regex/symbol result lists after method-specific
    runtime-safe query normalization instead of invoking raw ``retrieve``.
    """
    fused: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for cand in candidates:
        key = (
            str(cand.get("path", "") or ""),
            int(cand.get("start_line", 0) or 0),
            int(cand.get("end_line", 0) or 0),
            str(cand.get("content_sha", "") or ""),
        )
        if not key[0]:
            continue
        rank = max(1, int(cand.get("rank", 0) or 1))
        rec = fused.setdefault(key, {
            "method": "rrf",
            "rank": 0,
            "score": 0.0,
            "normalized_score": 0.0,
            "path": key[0],
            "start_line": key[1],
            "end_line": key[2],
            "content_sha": key[3],
            "extension": bea0._path_extension(key[0]),
        })
        rec["score"] = float(rec.get("score", 0.0) or 0.0) + 1.0 / (60.0 + rank)
    ordered = sorted(fused.values(), key=lambda r: (-float(r.get("score", 0.0)), str(r.get("path", ""))))
    top = ordered[: max(0, int(limit))]
    max_score = max((float(c.get("score", 0.0) or 0.0) for c in top), default=0.0)
    for idx, cand in enumerate(top, start=1):
        cand["rank"] = idx
        cand["normalized_score"] = round(float(cand.get("score", 0.0) or 0.0) / max_score, 6) if max_score > 0 else 0.0
    return top


def _collect_rrf_candidates_limited(
    openlocus_bin: str,
    query: str,
    cwd: Path,
    limit: int,
) -> tuple[list[dict[str, Any]], int, str]:
    cmd = [
        openlocus_bin, "retrieve", query, "--json", "--channels",
        "regex,bm25,symbol", "--max-results", str(int(limit)),
    ]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, check=False, text=True, capture_output=True, cwd=str(cwd),
            timeout=60,
        )
    except Exception:
        return [], 0, "retrieval_failed"
    latency_ms = int((time.perf_counter() - t0) * 1000)
    if proc.returncode != 0:
        return [], latency_ms, f"returncode_{proc.returncode}"
    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        return [], latency_ms, "invalid_json"
    evidence = raw.get("evidence", []) if isinstance(raw, dict) else []
    if not isinstance(evidence, list):
        evidence = []
    candidates = [
        bea0._normalize_candidate("rrf", idx + 1, ev)
        for idx, ev in enumerate(evidence)
        if isinstance(ev, dict)
    ]
    if candidates:
        max_score = max(abs(c["score"]) for c in candidates) or 0.0
        if max_score > 0:
            for cand in candidates:
                cand["normalized_score"] = round(cand["score"] / max_score, 6)
    return candidates, latency_ms, (proc.stderr[:500] if proc.stderr else "")


# ---------------------------------------------------------------------------
# Retrieval reach runner (per-arm candidate collection + gold-file reach)
# ---------------------------------------------------------------------------


class ReachResult:
    """Per-arm reach result for one denominator record (in-memory only).

    All fields are private; only aggregate counts are published.
    """

    def __init__(self, arm_name: str, private_record_id: str) -> None:
        self.arm_name = arm_name
        self.private_record_id = private_record_id
        self.gold_file_available: bool = False
        self.first_gold_file_rank: int = 0  # 0 = not found
        self.candidate_pool_size: int = 0
        self.retrieval_latency_seconds: float = 0.0
        self.duplicate_file_count: int = 0
        self.gold_file_rank_band: str = "not_found"
        self.candidate_paths_private: list[str] = []
        self.query_variants_private: list[str] = []
        self.retrieval_error: bool = False


def _reach_rank_band(rank: int) -> str:
    """Map a rank to a reach bucket label."""
    if rank <= 0:
        return "not_found"
    if rank <= 10:
        return "rank_1_10"
    if rank <= 50:
        return "rank_11_50"
    if rank <= 100:
        return "rank_51_100"
    if rank <= 200:
        return "rank_101_200"
    return "rank_above_200"


def _run_reach_for_record(
    *, arm_name: str, openlocus_bin: str, repo_root: Path,
    query: str, gold_paths: list[str],
    depth_multiplier: int, query_variants: list[str] | None,
    methods: tuple[str, ...] = FIXED_METHODS,
) -> ReachResult:
    """Run one retrieval reach measurement for one denominator record.

    Returns a :class:`ReachResult`. Never raises; on failure returns a
    result with ``gold_file_available=False`` and zero pool size.

    Gold paths are used ONLY to check whether any retrieved candidate
    matches a gold file — never to construct the query or candidates.
    """
    rr = ReachResult(arm_name=arm_name, private_record_id="")
    gold_set = {str(p) for p in gold_paths if p}
    t0 = time.perf_counter()
    total_latency_ms = 0
    try:
        # Collect per-method candidates at explicit depth. Query-variant arms
        # use up to MAX_QUERY_VARIANTS_PER_ARM runtime-clean variants; depth
        # arms increase the CLI limit for bm25/symbol/RRF.
        all_candidates: list[dict[str, Any]] = []
        limit = DEFAULT_RETRIEVAL_LIMIT * max(1, int(depth_multiplier))
        queries = [query]
        if query_variants:
            queries = list(query_variants)[:MAX_QUERY_VARIANTS_PER_ARM]
        for method in methods:
            for q in queries:
                cands, latency_ms, err = _collect_method_candidates_limited(
                    openlocus_bin, method, q, repo_root, limit,
                )
                if (err in {"retrieval_failed", "invalid_json"}
                        or err.startswith("returncode_")):
                    rr.retrieval_error = True
                total_latency_ms += latency_ms
                all_candidates.extend(cands)
        # Derive RRF from the runtime-safe method result lists instead of
        # invoking raw ``openlocus retrieve`` with regex-unsafe task text.
        all_candidates.extend(
            _derive_rrf_candidates_from_candidates(all_candidates, limit)
        )
        # Deduplicate candidates (reuse BEA-1's dedup).
        deduped = bea1._dedup_candidates(all_candidates)
        rr.candidate_pool_size = len(deduped)
        # Check gold-file reach.
        pred_paths = [str(c.get("path", "") or "") for c in deduped]
        rr.candidate_paths_private = pred_paths[:500]
        rr.query_variants_private = list(query_variants or [query])[:50]
        # Duplicate-file rate.
        unique_files = set(pred_paths)
        rr.duplicate_file_count = len(pred_paths) - len(unique_files)
        # First gold-file rank.
        for idx, path in enumerate(pred_paths, start=1):
            if path in gold_set:
                rr.gold_file_available = True
                rr.first_gold_file_rank = idx
                break
        rr.gold_file_rank_band = _reach_rank_band(rr.first_gold_file_rank)
    except Exception:
        rr.gold_file_available = False
    measured_wall = time.perf_counter() - t0
    rr.retrieval_latency_seconds = (
        round(total_latency_ms / 1000.0, 6)
        if total_latency_ms > 0
        else measured_wall
    )
    return rr


def _resolve_private_reach_dir() -> Path:
    """Return a /tmp-only private trace dir for BEA-v1-P2 reach rows."""
    raw = os.environ.get("OPENLOCUS_BEA_V1_P2_PRIVATE_REACH_DIR", "")
    base = Path(raw) if raw else Path(
        f"/tmp/openlocus_bea_v1_p2_reach_{os.getpid()}"
    )
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private reach dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _append_private_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _private_file_manifest(path: Path, *, manifest_name: str,
                           schema_version: str) -> dict[str, Any]:
    count = 0
    digest = hashlib.sha256()
    if path.exists():
        with path.open("rb") as fh:
            for line in fh:
                count += 1
                digest.update(line)
    return {
        "manifest_name": manifest_name,
        "schema_version": schema_version,
        "storage_class": "private_tmp_only",
        "record_count": int(count),
        "records_written": bool(count > 0),
        "path_publicly_serialized": False,
        "manifest_hash": digest.hexdigest() if count else "",
    }


# ---------------------------------------------------------------------------
# Public record builders (records-only; no dynamic dict mirrors)
# ---------------------------------------------------------------------------


def _source_run_records(
    *, fd1_schema_version: str, fd1_source_artifact_hash: str,
    fd1_status: str, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    fd1_committed_manifest_hash: str,
    v1_p1_result_checkpoint: str, v1_p1_result_status: str,
    v1_p1_gold_file_absent_denominator: int,
    v1_p1_file_selector_lower_bound: int,
    v1_p1_retrieval_availability_rate: float,
    fd1_private_decomposition_supplied: bool = False,
    fd1_private_decomposition_parsed: bool = False,
    fd1_private_decomposition_row_count: int = 0,
    fd1_private_decomposition_group_count: int = 0,
    fd1_private_decomposition_denominator: int = 0,
    fd1_private_decomposition_lower_bound: int = 0,
    replay_artifact_supplied: bool = False,
    replay_artifact_parsed: bool = False,
    replay_artifact_validated: bool = False,
    replay_artifact_status: str = "",
    replay_artifact_schema_version: str = "",
    replay_artifact_records_decomposed: int = 0,
    replay_artifact_manifest_record_count: int = 0,
    replay_artifact_manifest_records_written: bool = False,
    replay_artifact_manifest_path_publicly_serialized: bool = True,
    replay_artifact_manifest_schema_version: str = "",
    replay_artifact_manifest_hash: str = "",
    replay_artifact_manifest_hash_match: bool = False,
    replay_artifact_forbidden_scan_pass: bool = False,
    replay_artifact_failure_category: str = "",
    audit_match: bool, audit_mismatch_reason: str,
) -> list[dict[str, Any]]:
    """One source_run_records row describing the FD1 + P1 audit source."""
    del fd1_committed_manifest_hash
    return [{
        "source_phase": "BEA-v1-P1",
        "source_ci_run_id": FD1_SOURCE_CI_RUN_ID,
        "source_checkpoint": V1_P1_RESULT_CHECKPOINT,
        "source_local_checkpoint": FD1_SOURCE_LOCAL_CHECKPOINT,
        "source_status": fd1_status or FD1_SOURCE_STATUS,
        "source_artifact_status": "audit_match" if audit_match
        else "audit_mismatch",
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "expected_records_decomposed": EXPECTED_RECORDS_DECOMPOSED,
        "audited_records_decomposed": fd1_records_decomposed,
        "expected_private_manifest_record_count":
            EXPECTED_PRIVATE_DECOMP_ROWS,
        "audited_private_manifest_record_count":
            fd1_private_manifest_record_count,
        "fd1_source_schema_version": fd1_schema_version,
        "fd1_source_artifact_hash": fd1_source_artifact_hash,
        "v1_p1_result_checkpoint": v1_p1_result_checkpoint,
        "v1_p1_result_status": v1_p1_result_status,
        "v1_p1_gold_file_absent_denominator":
            v1_p1_gold_file_absent_denominator,
        "v1_p1_file_selector_lower_bound":
            v1_p1_file_selector_lower_bound,
        "v1_p1_retrieval_availability_rate":
            v1_p1_retrieval_availability_rate,
        "fd1_private_decomposition_supplied":
            bool(fd1_private_decomposition_supplied),
        "fd1_private_decomposition_parsed":
            bool(fd1_private_decomposition_parsed),
        "fd1_private_decomposition_row_count":
            int(fd1_private_decomposition_row_count),
        "fd1_private_decomposition_group_count":
            int(fd1_private_decomposition_group_count),
        "fd1_private_decomposition_denominator":
            int(fd1_private_decomposition_denominator),
        "fd1_private_decomposition_lower_bound":
            int(fd1_private_decomposition_lower_bound),
        "replay_artifact_supplied": bool(replay_artifact_supplied),
        "replay_artifact_parsed": bool(replay_artifact_parsed),
        "replay_artifact_validated": bool(replay_artifact_validated),
        "replay_artifact_status": str(replay_artifact_status),
        "replay_artifact_schema_version":
            str(replay_artifact_schema_version),
        "replay_artifact_records_decomposed":
            int(replay_artifact_records_decomposed),
        "replay_artifact_manifest_record_count":
            int(replay_artifact_manifest_record_count),
        "replay_artifact_manifest_records_written":
            bool(replay_artifact_manifest_records_written),
        "replay_artifact_manifest_path_publicly_serialized":
            bool(replay_artifact_manifest_path_publicly_serialized),
        "replay_artifact_manifest_schema_version":
            str(replay_artifact_manifest_schema_version),
        "replay_artifact_manifest_hash":
            str(replay_artifact_manifest_hash),
        "replay_artifact_manifest_hash_match":
            bool(replay_artifact_manifest_hash_match),
        "replay_artifact_forbidden_scan_pass":
            bool(replay_artifact_forbidden_scan_pass),
        "replay_artifact_failure_category":
            str(replay_artifact_failure_category),
        "replay_protocol_match": bool(audit_match),
        "replay_mismatch_reason": audit_mismatch_reason,
        "replay_match_basis":
            "fd1_committed_aggregate_and_validated_private_replay"
            if fd1_private_decomposition_parsed and replay_artifact_validated
            else "fd1_committed_aggregate_only_no_validated_private_replay",
    }]


def _denominator_records(
    denominator: list[DenominatorRecord],
) -> list[dict[str, Any]]:
    """Per-(source_phase, benchmark) denominator count records.

    Records-only: no private_record_id, no record_index. Natural key
    ``(source_phase, benchmark)``.
    """
    counts: dict[tuple[str, str], int] = {}
    for d in denominator:
        key = (d.source_phase, d.benchmark)
        counts[key] = counts.get(key, 0) + 1
    rows = [
        {"source_phase": sp, "benchmark": bm,
         "denominator_record_count": cnt}
        for (sp, bm), cnt in sorted(counts.items())
    ]
    return rows


def _arm_reach_records(
    arm_results: dict[str, list[ReachResult]],
    denominator_count: int,
) -> list[dict[str, Any]]:
    """Per-arm aggregate reach records over the denominator.

    Natural key ``(arm_name,)``.
    """
    rows: list[dict[str, Any]] = []
    denom = denominator_count if denominator_count > 0 else 1
    for arm_name in REACH_ARMS:
        results = arm_results.get(arm_name, [])
        if not results:
            rows.append({
                "arm_name": arm_name,
                "denominator_record_count": int(denominator_count),
                "gold_file_available_any_pool": 0,
                "gold_file_available_rate": 0.0,
                "gold_file_available_at_50": 0,
                "gold_file_available_at_100": 0,
                "gold_file_available_at_200": 0,
                "first_gold_file_rank_mean": 0.0,
                "first_gold_file_rank_median": 0.0,
                "candidate_pool_size_mean": 0.0,
                "retrieval_latency_mean_seconds": 0.0,
                "duplicate_file_rate": 0.0,
                "newly_reachable_count": 0,
                "still_unavailable_count": int(denominator_count),
            })
            continue
        available = sum(1 for r in results if r.gold_file_available)
        at_50 = sum(1 for r in results
                    if 0 < r.first_gold_file_rank <= 50)
        at_100 = sum(1 for r in results
                     if 0 < r.first_gold_file_rank <= 100)
        at_200 = sum(1 for r in results
                     if 0 < r.first_gold_file_rank <= 200)
        ranks = [r.first_gold_file_rank for r in results
                 if r.first_gold_file_rank > 0]
        pool_sizes = [r.candidate_pool_size for r in results]
        latencies = [r.retrieval_latency_seconds for r in results]
        dup_files = sum(r.duplicate_file_count for r in results)
        total_files = sum(r.candidate_pool_size for r in results)
        # newly_reachable vs baseline (current_bea_candidate_pool_replay)
        baseline = arm_results.get(
            "current_bea_candidate_pool_replay", [])
        baseline_available_rids = {
            r.private_record_id for r in baseline if r.gold_file_available}
        newly_reachable = sum(
            1 for r in results
            if r.gold_file_available
            and r.private_record_id not in baseline_available_rids)
        still_unavailable = sum(1 for r in results if not r.gold_file_available)
        rows.append({
            "arm_name": arm_name,
            "denominator_record_count": int(denominator_count),
            "gold_file_available_any_pool": int(available),
            "gold_file_available_rate": round(available / denom, 6),
            "gold_file_available_at_50": int(at_50),
            "gold_file_available_at_100": int(at_100),
            "gold_file_available_at_200": int(at_200),
            "first_gold_file_rank_mean": (
                round(statistics.mean(ranks), 6) if ranks else 0.0),
            "first_gold_file_rank_median": (
                round(statistics.median(ranks), 6) if ranks else 0.0),
            "candidate_pool_size_mean": (
                round(statistics.mean(pool_sizes), 6) if pool_sizes else 0.0),
            "retrieval_latency_mean_seconds": (
                round(statistics.mean(latencies), 6) if latencies else 0.0),
            "duplicate_file_rate": (
                round(dup_files / total_files, 6) if total_files > 0 else 0.0),
            "newly_reachable_count": int(newly_reachable),
            "still_unavailable_count": int(still_unavailable),
        })
    rows.sort(key=lambda r: r["arm_name"])
    return rows


def _arm_delta_records(
    arm_results: dict[str, list[ReachResult]],
) -> list[dict[str, Any]]:
    """Per-arm delta vs baseline (current_bea_candidate_pool_replay).

    Natural key ``(arm_name,)``.
    """
    rows: list[dict[str, Any]] = []
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_available = sum(1 for r in baseline if r.gold_file_available)
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    baseline_latency = (
        statistics.mean([r.retrieval_latency_seconds for r in baseline])
        if baseline else 0.0)
    for arm_name in REACH_ARMS:
        if arm_name == "current_bea_candidate_pool_replay":
            continue
        results = arm_results.get(arm_name, [])
        available = sum(1 for r in results if r.gold_file_available)
        pool = (
            statistics.mean([r.candidate_pool_size for r in results])
            if results else 0.0)
        latency = (
            statistics.mean([r.retrieval_latency_seconds for r in results])
            if results else 0.0)
        pool_mult = round(pool / baseline_pool, 6) if baseline_pool > 0 else 0.0
        latency_mult = round(latency / baseline_latency, 6) if baseline_latency > 0 else 0.0
        rows.append({
            "arm_name": arm_name,
            "available_delta": int(available - baseline_available),
            "available_lift_rate": (
                round((available - baseline_available) / max(
                    len(baseline), 1), 6)),
            "pool_size_multiplier": pool_mult,
            "latency_multiplier": latency_mult,
        })
    rows.sort(key=lambda r: r["arm_name"])
    return rows


def _reach_bucket_records(
    arm_results: dict[str, list[ReachResult]],
) -> list[dict[str, Any]]:
    """Per-(arm, reach_bucket) count records.

    Natural key ``(arm_name, reach_bucket)``.
    """
    rows: list[dict[str, Any]] = []
    for arm_name in REACH_ARMS:
        results = arm_results.get(arm_name, [])
        bucket_counts: dict[str, int] = {}
        for r in results:
            bucket_counts[r.gold_file_rank_band] = (
                bucket_counts.get(r.gold_file_rank_band, 0) + 1)
        for bucket in ("not_found", "rank_1_10", "rank_11_50",
                        "rank_51_100", "rank_101_200", "rank_above_200"):
            rows.append({
                "arm_name": arm_name,
                "reach_bucket": bucket,
                "record_count": int(bucket_counts.get(bucket, 0)),
            })
    rows.sort(key=lambda r: (r["arm_name"], r["reach_bucket"]))
    return rows


def _rank_band_records(
    arm_results: dict[str, list[ReachResult]],
) -> list[dict[str, Any]]:
    """Per-(arm, rank_band) count records using the RANK_BANDS cutoffs.

    Natural key ``(arm_name, rank_band)``.
    """
    rows: list[dict[str, Any]] = []
    band_labels = [f"rank_le_{b}" for b in RANK_BANDS] + ["rank_above_200", "not_found"]
    for arm_name in REACH_ARMS:
        results = arm_results.get(arm_name, [])
        band_counts: dict[str, int] = {b: 0 for b in band_labels}
        for r in results:
            if r.first_gold_file_rank <= 0:
                band_counts["not_found"] += 1
            elif r.first_gold_file_rank <= RANK_BANDS[0]:
                band_counts[f"rank_le_{RANK_BANDS[0]}"] += 1
            elif r.first_gold_file_rank <= RANK_BANDS[1]:
                band_counts[f"rank_le_{RANK_BANDS[1]}"] += 1
            elif r.first_gold_file_rank <= RANK_BANDS[2]:
                band_counts[f"rank_le_{RANK_BANDS[2]}"] += 1
            elif r.first_gold_file_rank <= RANK_BANDS[3]:
                band_counts[f"rank_le_{RANK_BANDS[3]}"] += 1
            else:
                band_counts["rank_above_200"] += 1
        for band in band_labels:
            rows.append({
                "arm_name": arm_name,
                "rank_band": band,
                "record_count": int(band_counts.get(band, 0)),
            })
    rows.sort(key=lambda r: (r["arm_name"], r["rank_band"]))
    return rows


def _cost_safety_records(
    arm_results: dict[str, list[ReachResult]],
) -> list[dict[str, Any]]:
    """Cost-safety axis records (pool size and latency multipliers).

    Natural key ``(cost_safety_axis,)``.
    """
    rows: list[dict[str, Any]] = []
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    baseline_latency = (
        statistics.mean([r.retrieval_latency_seconds for r in baseline])
        if baseline else 0.0)
    # Pool size multiplier axis.
    max_pool_mult = 0.0
    max_latency_mult = 0.0
    for arm_name in REACH_ARMS:
        if arm_name == "current_bea_candidate_pool_replay":
            continue
        results = arm_results.get(arm_name, [])
        if not results:
            continue
        pool = statistics.mean([r.candidate_pool_size for r in results])
        latency = statistics.mean([r.retrieval_latency_seconds for r in results])
        if baseline_pool > 0:
            max_pool_mult = max(max_pool_mult, pool / baseline_pool)
        if baseline_latency > 0:
            max_latency_mult = max(max_latency_mult, latency / baseline_latency)
    rows.append({
        "cost_safety_axis": "max_pool_size_multiplier",
        "cost_safety_class": "ok" if max_pool_mult <= NO_GO_POOL_SIZE_MAX_MULTIPLIER
        else "exceeded",
        "value": round(max_pool_mult, 6),
        "threshold": float(NO_GO_POOL_SIZE_MAX_MULTIPLIER),
    })
    rows.append({
        "cost_safety_axis": "max_latency_multiplier",
        "cost_safety_class": "ok" if max_latency_mult <= NO_GO_LATENCY_MAX_MULTIPLIER
        else "exceeded",
        "value": round(max_latency_mult, 6),
        "threshold": float(NO_GO_LATENCY_MAX_MULTIPLIER),
    })
    rows.sort(key=lambda r: r["cost_safety_axis"])
    return rows


def _stop_go_records(
    *, denominator_count: int,
    arm_results: dict[str, list[ReachResult]],
    pool_cost_exceeded: bool, retrieval_reach_executed: bool,
) -> list[dict[str, Any]]:
    """One stop/go row describing the v1-A reopen decision.

    Go (reopen BEA-v1-A) only if:
    1. newly_available >= 25 OR availability lift >= 0.20.
    2. pool <= 4x baseline and latency <= 2x baseline.
    3. At least one runtime-clean mechanism dominates (depth, query, or
       combined arm has newly_reachable > 0).
    4. No gold/private labels used at runtime (binding flag).
    5. Expanded pool leaves a selector/packer problem (gold reachable but
       often below final budget — proxied by first_gold_file_rank_mean
       > budget).
    """
    if not retrieval_reach_executed or denominator_count == 0:
        return [{
            "stop_go_decision": "no_go_replay_mismatch",
            "stop_go_reason": "retrieval_reach_not_executed_or_denominator_zero",
            "newly_available_count": 0,
            "availability_lift": 0.0,
            "pool_cost_exceeded": False,
            "latency_cost_exceeded": False,
            "runtime_clean_mechanism_dominates": False,
            "go_threshold_newly_available_min": GO_NEWLY_AVAILABLE_COUNT_MIN,
            "go_threshold_availability_lift_min": GO_AVAILABILITY_LIFT_MIN,
            "no_go_threshold_pool_size_max_multiplier":
                NO_GO_POOL_SIZE_MAX_MULTIPLIER,
            "no_go_threshold_latency_max_multiplier":
                NO_GO_LATENCY_MAX_MULTIPLIER,
        }]
    # Find best expanded arm by newly_reachable.
    best_arm = ""
    best_newly = 0
    best_available = 0
    baseline_available = 0
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_available = sum(1 for r in baseline if r.gold_file_available)
    for arm_name in REACH_ARMS:
        if arm_name == "current_bea_candidate_pool_replay":
            continue
        results = arm_results.get(arm_name, [])
        available = sum(1 for r in results if r.gold_file_available)
        baseline_rids = {r.private_record_id for r in baseline
                         if r.gold_file_available}
        newly = sum(1 for r in results
                    if r.gold_file_available
                    and r.private_record_id not in baseline_rids)
        if newly > best_newly:
            best_newly = newly
            best_arm = arm_name
            best_available = available
    availability_lift = best_newly / max(denominator_count, 1)
    # Latency cost check.
    latency_exceeded = False
    if baseline:
        baseline_latency = statistics.mean(
            [r.retrieval_latency_seconds for r in baseline])
        for arm_name in REACH_ARMS:
            if arm_name == "current_bea_candidate_pool_replay":
                continue
            results = arm_results.get(arm_name, [])
            if not results:
                continue
            arm_latency = statistics.mean(
                [r.retrieval_latency_seconds for r in results])
            if (baseline_latency > 0
                    and arm_latency / baseline_latency
                    > NO_GO_LATENCY_MAX_MULTIPLIER):
                latency_exceeded = True
                break
    runtime_clean_dominates = best_newly > 0
    # Selector/packer problem: gold reachable but often below final budget.
    # Proxy: best arm's first_gold_file_rank_mean > budget.
    best_results = arm_results.get(best_arm, [])
    ranks = [r.first_gold_file_rank for r in best_results
             if r.first_gold_file_rank > 0]
    rank_mean = statistics.mean(ranks) if ranks else 0.0
    selector_problem_remains = rank_mean > FIXED_BUDGET

    newly_material = (best_newly >= GO_NEWLY_AVAILABLE_COUNT_MIN
                      or availability_lift >= GO_AVAILABILITY_LIFT_MIN)
    if pool_cost_exceeded or latency_exceeded:
        decision = "no_go_retrieval_reach_latency_or_pool_cost"
        reason = (f"pool_or_latency_cost_exceeded; "
                  f"best_arm={best_arm}; newly={best_newly}; "
                  f"pool_cost_exceeded={pool_cost_exceeded}; "
                  f"latency_exceeded={latency_exceeded}")
    elif not newly_material:
        decision = "no_go_retrieval_reach_insufficient"
        reason = (f"newly_available_below_material_threshold; "
                  f"best_arm={best_arm}; newly={best_newly}; "
                  f"availability_lift={availability_lift:.6f}")
    elif not runtime_clean_dominates:
        decision = "no_go_retrieval_reach_insufficient"
        reason = "no_runtime_clean_mechanism_dominates"
    elif not selector_problem_remains:
        decision = "no_go_retrieval_reach_insufficient"
        reason = ("expanded_pool_does_not_leave_selector_problem; "
                  "gold_reachable_but_rank_too_low_for_selector_value")
    else:
        decision = "bea_v1_p2_retrieval_reach_pass"
        reason = (f"newly_available_material; best_arm={best_arm}; "
                  f"newly={best_newly}; availability_lift="
                  f"{availability_lift:.6f}; selector_problem_remains=True")
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "best_arm": best_arm,
        "newly_available_count": int(best_newly),
        "availability_lift": round(availability_lift, 6),
        "pool_cost_exceeded": bool(pool_cost_exceeded),
        "latency_cost_exceeded": bool(latency_exceeded),
        "runtime_clean_mechanism_dominates": bool(runtime_clean_dominates),
        "selector_problem_remains": bool(selector_problem_remains),
        "go_threshold_newly_available_min": GO_NEWLY_AVAILABLE_COUNT_MIN,
        "go_threshold_availability_lift_min": GO_AVAILABILITY_LIFT_MIN,
        "no_go_threshold_pool_size_max_multiplier":
            NO_GO_POOL_SIZE_MAX_MULTIPLIER,
        "no_go_threshold_latency_max_multiplier":
            NO_GO_LATENCY_MAX_MULTIPLIER,
    }]


def _gate_records(
    *, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    denominator_count: int,
    fd1_private_decomposition_parsed: bool,
    replay_artifact_validated: bool,
    retrieval_reach_executed: bool,
    forbidden_scan_pass: bool,
    pool_cost_exceeded: bool,
    latency_cost_exceeded: bool,
    blocking_failure_count: int,
) -> list[dict[str, Any]]:
    def _g(gate: str, value: float, relation: str, threshold: float,
           passed: bool) -> dict[str, Any]:
        return {
            "gate": gate, "value": round(float(value), 6),
            "threshold_relation": relation,
            "threshold_value": round(float(threshold), 6),
            "passed": bool(passed),
        }

    return [
        _g("fd1_records_decomposed", float(fd1_records_decomposed), "==",
           float(EXPECTED_RECORDS_DECOMPOSED),
           fd1_records_decomposed == EXPECTED_RECORDS_DECOMPOSED),
        _g("fd1_private_manifest_record_count",
           float(fd1_private_manifest_record_count), "==",
           float(EXPECTED_PRIVATE_DECOMP_ROWS),
           fd1_private_manifest_record_count == EXPECTED_PRIVATE_DECOMP_ROWS),
        _g("denominator_count", float(denominator_count), "==",
           float(EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR),
           denominator_count == EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR),
        _g("fd1_private_decomposition_parsed",
           1.0 if fd1_private_decomposition_parsed else 0.0,
           "boolean", 1.0, fd1_private_decomposition_parsed),
        _g("replay_artifact_validated",
           1.0 if replay_artifact_validated else 0.0,
           "boolean", 1.0, replay_artifact_validated),
        _g("retrieval_reach_executed",
           1.0 if retrieval_reach_executed else 0.0,
           "boolean", 1.0, retrieval_reach_executed),
        _g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0,
           "boolean", 1.0, forbidden_scan_pass),
        _g("pool_cost_exceeded",
           1.0 if pool_cost_exceeded else 0.0,
           "boolean_false", 0.0, not pool_cost_exceeded),
        _g("latency_cost_exceeded",
           1.0 if latency_cost_exceeded else 0.0,
           "boolean_false", 0.0, not latency_cost_exceeded),
        _g("blocking_failure_count", float(blocking_failure_count), "==",
           0.0, blocking_failure_count == 0),
    ]


def _private_manifest_records(
    fd1_artifact: dict[str, Any], storage_class: str,
    extra_manifests: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Echo private manifest rows (counts and hashes only)."""
    m = bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact)
    rows = [{
        "manifest_name": "fd1_private_decomposition_manifest",
        "records_written": bool(m.get("records_written", False)),
        "record_count": int(m.get("record_count", 0) or 0),
        "schema_version": str(m.get("schema_version", "") or ""),
        "manifest_hash": str(m.get("manifest_hash", "") or ""),
        "storage_class": storage_class,
        "path_publicly_serialized": False,
    }]
    rows.extend(extra_manifests or [])
    return rows


def _failure_category_count_records(
    fcc: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {"failure_category": str(k), "count": int(v)}
        for k, v in sorted(fcc.items())
    ]


def _blocking_failure_count(fcc: dict[str, int]) -> int:
    return sum(int(fcc.get(cat, 0)) for cat in BLOCKING_FAILURE_CATEGORIES)


# ---------------------------------------------------------------------------
# Status decision
# ---------------------------------------------------------------------------


def _decide_status(
    *, audit_match: bool, blocking_failure_count: int,
    fd1_private_decomposition_parsed: bool,
    replay_artifact_validated: bool,
    denominator_count: int,
    retrieval_reach_executed: bool,
    pool_cost_exceeded: bool,
    stop_go_decision: str,
) -> str:
    if blocking_failure_count > 0:
        return "fail_schema_contract"
    if not audit_match:
        return "unavailable_with_reason"
    if (not fd1_private_decomposition_parsed
            or not replay_artifact_validated
            or denominator_count != EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR):
        return "no_go_replay_mismatch"
    if not retrieval_reach_executed:
        return "no_go_replay_mismatch"
    # Map stop_go_decision to status.
    if stop_go_decision == "bea_v1_p2_retrieval_reach_pass":
        return "bea_v1_p2_retrieval_reach_pass"
    if stop_go_decision == "no_go_retrieval_reach_latency_or_pool_cost":
        return "no_go_retrieval_reach_latency_or_pool_cost"
    if stop_go_decision == "no_go_retrieval_reach_insufficient":
        return "no_go_retrieval_reach_insufficient"
    if stop_go_decision == "no_go_replay_mismatch":
        return "no_go_replay_mismatch"
    return "no_go_retrieval_reach_insufficient"


# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str, *, self_test_passed: bool,
    self_test_checks_total: int = 0,
    self_test_checks_passed: int | None = None,
    openlocus_binary_source: str, network_mode: str,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)

    source_runs = _source_run_records(
        fd1_schema_version="",
        fd1_source_artifact_hash="",
        fd1_status="",
        fd1_records_decomposed=0,
        fd1_private_manifest_record_count=0,
        fd1_committed_manifest_hash="",
        v1_p1_result_checkpoint=V1_P1_RESULT_CHECKPOINT,
        v1_p1_result_status=V1_P1_RESULT_STATUS,
        v1_p1_gold_file_absent_denominator=V1_P1_GOLD_FILE_ABSENT_DENOMINATOR,
        v1_p1_file_selector_lower_bound=V1_P1_FILE_SELECTOR_LOWER_BOUND,
        v1_p1_retrieval_availability_rate=V1_P1_RETRIEVAL_AVAILABILITY_RATE,
        audit_match=False,
        audit_mismatch_reason=failure_reason_category,
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": "unavailable_with_reason",
        "mode": MODE,
        "phase": PHASE,
        "budget": FIXED_BUDGET,
        "methods": list(FIXED_METHODS),
        "reach_arms": list(REACH_ARMS),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "records_decomposed": 0,
        "private_manifest_record_count": 0,
        "denominator_count": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_count_records": _failure_category_count_records(fcc),
        "source_run_records": source_runs,
        "denominator_records": [],
        "arm_reach_records": [],
        "arm_delta_records": [],
        "reach_bucket_records": [],
        "rank_band_records": [],
        "cost_safety_records": [],
        "stop_go_records": _stop_go_records(
            denominator_count=0, arm_results={},
            pool_cost_exceeded=False,
            retrieval_reach_executed=False,
        ),
        "gate_records": _gate_records(
            fd1_records_decomposed=0,
            fd1_private_manifest_record_count=0,
            denominator_count=0,
            fd1_private_decomposition_parsed=False,
            replay_artifact_validated=False,
            retrieval_reach_executed=False,
            forbidden_scan_pass=True,
            pool_cost_exceeded=False,
            latency_cost_exceeded=False,
            blocking_failure_count=_blocking_failure_count(fcc),
        ),
        "private_manifest_records": _private_manifest_records(
            {}, "no_fd1_artifact",
        ),
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None
            and self_test_passed else (self_test_checks_passed or 0)
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "heldout_validation_claimed": False,
            "signal_strength":
                "bea_v1_p2_candidate_availability_reach_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
            "is_v04_repair": False,
            "is_fd2_b": False,
            "is_fd2_c": False,
            "is_p4": False,
            "is_p5": False,
            "is_v031_tuning": False,
            "is_v032_tuning": False,
            "is_b16k": False,
            "is_dense_quality_mixing": False,
            "is_graph_quality_mixing": False,
            "is_quiver_quality_mixing": False,
            "is_failure_attribution_only": False,
            "is_candidate_availability_reach_smoke": True,
        },
    }
    scan = _v1_p2_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_reach_report(
    *, self_test_passed: bool, self_test_checks_total: int,
    self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any],
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
    fd1_committed_manifest_hash: str,
    pt: bea_v1_p1.ParsedPrivateDecomposition | None,
    rav: bea_v1_p1.Fd1ReplayArtifactValidation | None,
    denominator: list[DenominatorRecord],
    arm_results: dict[str, list[ReachResult]],
    retrieval_reach_executed: bool,
    audit_match: bool, audit_mismatch_reason: str,
    failure_category_counts: dict[str, int],
    aggregate_runtime_seconds: float,
    extra_private_manifests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    fd1_status = bea_v1_p1._fd1_status(fd1_artifact)
    fd1_records_decomposed = bea_v1_p1._fd1_records_decomposed(fd1_artifact)
    fd1_manifest = bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact)
    fd1_manifest_count = int(fd1_manifest.get("record_count", 0) or 0)

    fd1_private_decomposition_parsed = (
        pt is not None and pt.computed
        and pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS
        and pt.group_count == EXPECTED_RECORDS_DECOMPOSED
    )
    replay_artifact_validated = (rav is not None and rav.validated)
    if (pt is not None and pt.path_supplied
            and not replay_artifact_validated):
        if rav is not None and rav.failure_category:
            fcc[rav.failure_category] = max(
                fcc.get(rav.failure_category, 0), 1)
        fd1_private_decomposition_parsed = False

    denominator_count = len(denominator)

    # Cost safety.
    cost_safety = _cost_safety_records(arm_results)
    pool_cost_exceeded = any(
        r.get("cost_safety_class") == "exceeded"
        and r.get("cost_safety_axis") == "max_pool_size_multiplier"
        for r in cost_safety)
    latency_cost_exceeded = any(
        r.get("cost_safety_class") == "exceeded"
        and r.get("cost_safety_axis") == "max_latency_multiplier"
        for r in cost_safety)

    stop_go = _stop_go_records(
        denominator_count=denominator_count,
        arm_results=arm_results,
        pool_cost_exceeded=pool_cost_exceeded,
        retrieval_reach_executed=retrieval_reach_executed,
    )

    blocking_failure_count = _blocking_failure_count(fcc)

    status = _decide_status(
        audit_match=audit_match,
        blocking_failure_count=blocking_failure_count,
        fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
        replay_artifact_validated=replay_artifact_validated,
        denominator_count=denominator_count,
        retrieval_reach_executed=retrieval_reach_executed,
        pool_cost_exceeded=pool_cost_exceeded,
        stop_go_decision=stop_go[0]["stop_go_decision"] if stop_go else "",
    )

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["fd1_artifact_read"] = True
    safe_true["bea_v1_p2_reach_smoke_performed"] = retrieval_reach_executed
    safe_true["fd1_private_decomposition_parsed"] = bool(
        fd1_private_decomposition_parsed)
    safe_true["retrieval_reach_executed"] = bool(retrieval_reach_executed)
    if rav is not None:
        safe_true["fd1_private_decomposition_replay_supplied"] = bool(
            rav.supplied)
        safe_true["fd1_private_decomposition_replay_validated"] = bool(
            rav.validated)
        safe_true[
            "fd1_private_decomposition_replay_executed_by_workflow"] = bool(
            rav.supplied and rav.validated)

    source_runs = _source_run_records(
        fd1_schema_version=fd1_source_schema_version,
        fd1_source_artifact_hash=fd1_source_artifact_hash,
        fd1_status=fd1_status,
        fd1_records_decomposed=fd1_records_decomposed,
        fd1_private_manifest_record_count=fd1_manifest_count,
        fd1_committed_manifest_hash=fd1_committed_manifest_hash,
        v1_p1_result_checkpoint=V1_P1_RESULT_CHECKPOINT,
        v1_p1_result_status=V1_P1_RESULT_STATUS,
        v1_p1_gold_file_absent_denominator=V1_P1_GOLD_FILE_ABSENT_DENOMINATOR,
        v1_p1_file_selector_lower_bound=V1_P1_FILE_SELECTOR_LOWER_BOUND,
        v1_p1_retrieval_availability_rate=V1_P1_RETRIEVAL_AVAILABILITY_RATE,
        fd1_private_decomposition_supplied=(
            pt.path_supplied if pt is not None else False),
        fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
        fd1_private_decomposition_row_count=(
            pt.row_count if pt is not None else 0),
        fd1_private_decomposition_group_count=(
            pt.group_count if pt is not None else 0),
        fd1_private_decomposition_denominator=(
            pt.gold_file_absent_denominator if pt is not None else 0),
        fd1_private_decomposition_lower_bound=(
            pt.recoverable_lower_bound if pt is not None else 0),
        replay_artifact_supplied=(rav.supplied if rav is not None else False),
        replay_artifact_parsed=(rav.parsed if rav is not None else False),
        replay_artifact_validated=(rav.validated if rav is not None else False),
        replay_artifact_status=(rav.replay_status if rav is not None else ""),
        replay_artifact_schema_version=(
            rav.replay_schema_version if rav is not None else ""),
        replay_artifact_records_decomposed=(
            rav.replay_records_decomposed if rav is not None else 0),
        replay_artifact_manifest_record_count=(
            rav.replay_manifest_record_count if rav is not None else 0),
        replay_artifact_manifest_records_written=(
            rav.replay_manifest_records_written if rav is not None else False),
        replay_artifact_manifest_path_publicly_serialized=(
            rav.replay_manifest_path_publicly_serialized
            if rav is not None else True),
        replay_artifact_manifest_schema_version=(
            rav.replay_manifest_schema_version if rav is not None else ""),
        replay_artifact_manifest_hash=(
            rav.replay_manifest_hash if rav is not None else ""),
        replay_artifact_manifest_hash_match=(
            rav.manifest_hash_match if rav is not None else False),
        replay_artifact_forbidden_scan_pass=(
            rav.replay_forbidden_scan_pass if rav is not None else False),
        replay_artifact_failure_category=(
            rav.failure_category if rav is not None else ""),
        audit_match=audit_match,
        audit_mismatch_reason=audit_mismatch_reason,
    )

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
        "reach_arms": list(REACH_ARMS),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "records_decomposed": fd1_records_decomposed,
        "private_manifest_record_count": fd1_manifest_count,
        "denominator_count": int(denominator_count),
        "failure_reason_category": "",
        "failure_category_count_records": _failure_category_count_records(fcc),
        "source_run_records": source_runs,
        "denominator_records": _denominator_records(denominator),
        "arm_reach_records": _arm_reach_records(arm_results, denominator_count),
        "arm_delta_records": _arm_delta_records(arm_results),
        "reach_bucket_records": _reach_bucket_records(arm_results),
        "rank_band_records": _rank_band_records(arm_results),
        "cost_safety_records": cost_safety,
        "stop_go_records": stop_go,
        "gate_records": _gate_records(
            fd1_records_decomposed=fd1_records_decomposed,
            fd1_private_manifest_record_count=fd1_manifest_count,
            denominator_count=denominator_count,
            fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
            replay_artifact_validated=replay_artifact_validated,
            retrieval_reach_executed=retrieval_reach_executed,
            forbidden_scan_pass=True,
            pool_cost_exceeded=pool_cost_exceeded,
            latency_cost_exceeded=latency_cost_exceeded,
            blocking_failure_count=blocking_failure_count,
        ),
        "private_manifest_records": _private_manifest_records(
            fd1_artifact, "fd1_committed_artifact",
            extra_manifests=extra_private_manifests,
        ),
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None
            and self_test_passed else (self_test_checks_passed or 0)
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "heldout_validation_claimed": False,
            "signal_strength":
                "bea_v1_p2_candidate_availability_reach_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
            "is_v04_repair": False,
            "is_fd2_b": False,
            "is_fd2_c": False,
            "is_p4": False,
            "is_p5": False,
            "is_v031_tuning": False,
            "is_v032_tuning": False,
            "is_b16k": False,
            "is_dense_quality_mixing": False,
            "is_graph_quality_mixing": False,
            "is_quiver_quality_mixing": False,
            "is_failure_attribution_only": False,
            "is_candidate_availability_reach_smoke": True,
        },
    }
    scan = _v1_p2_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Real reach runner (network + openlocus + FD1 private replay)
# ---------------------------------------------------------------------------


def _run_reach_smoke(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    fd1_artifact_path: Path,
    fd1_private_decomposition_jsonl: Path | None,
    fd1_replay_artifact: Path | None,
    enable_network: bool,
) -> dict[str, Any]:
    """Run the full P2 reach smoke: validate FD1 replay, extract
    denominator, rerun retrieval reach on denominator records, build
    the public report. No provider calls.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    start = time.perf_counter()

    fd1_artifact, fd1_schema, fd1_hash, fd1_status = (
        _load_committed_artifact(fd1_artifact_path))
    if fd1_status != "pass":
        fcc["fd1_artifact_missing" if fd1_status == "artifact_missing"
            else "fd1_artifact_parse_failed"] = 1
        return _build_unavailable_report(
            fd1_status, self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode, failure_category_counts=fcc)

    # Validate FD1 schema/status/counts.
    audit_mismatch_reasons: list[str] = []
    if fd1_schema != FD1_SOURCE_SCHEMA_VERSION:
        fcc["fd1_schema_version_mismatch"] = 1
        audit_mismatch_reasons.append(f"fd1_schema_mismatch:{fd1_schema}")
    fd1_artifact_status = bea_v1_p1._fd1_status(fd1_artifact)
    if fd1_artifact_status != FD1_SOURCE_STATUS:
        fcc["fd1_status_mismatch"] = 1
        audit_mismatch_reasons.append(
            f"fd1_status_mismatch:{fd1_artifact_status}")
    if bea_v1_p1._fd1_records_decomposed(fd1_artifact) != EXPECTED_RECORDS_DECOMPOSED:
        fcc["fd1_records_decomposed_mismatch"] = 1
        audit_mismatch_reasons.append(
            f"records_decomposed_mismatch:"
            f"{bea_v1_p1._fd1_records_decomposed(fd1_artifact)}_vs_"
            f"{EXPECTED_RECORDS_DECOMPOSED}")
    fd1_manifest = bea_v1_p1._fd1_private_decomposition_manifest(fd1_artifact)
    fd1_manifest_count = int(fd1_manifest.get("record_count", 0) or 0)
    if fd1_manifest_count != EXPECTED_PRIVATE_DECOMP_ROWS:
        fcc["fd1_private_manifest_mismatch"] = 1
        audit_mismatch_reasons.append(
            f"private_manifest_count_mismatch:{fd1_manifest_count}_vs_"
            f"{EXPECTED_PRIVATE_DECOMP_ROWS}")

    audit_match = not audit_mismatch_reasons
    audit_mismatch_reason = ";".join(audit_mismatch_reasons)

    # Parse + validate FD1 private decomposition replay.
    pt = _parse_private_decomposition_jsonl(fd1_private_decomposition_jsonl)
    if pt.path_supplied and not pt.file_existed:
        fcc["fd1_private_decomposition_missing"] = 1
    if pt.parse_failures > 0:
        fcc["fd1_private_decomposition_parse_failed"] = pt.parse_failures
    if pt.path_supplied and pt.file_existed and pt.parse_failures == 0:
        if pt.row_count != EXPECTED_PRIVATE_DECOMP_ROWS:
            fcc["fd1_private_decomposition_count_mismatch"] = 1
        if pt.group_count != EXPECTED_RECORDS_DECOMPOSED:
            fcc["fd1_private_decomposition_group_mismatch"] = 1
    _compute_file_selector_lower_bound(pt)

    # Validate FD1 replay artifact.
    committed_manifest_hash = str(
        fd1_manifest.get("manifest_hash", "") or "")
    rav = _validate_fd1_replay_artifact(
        fd1_replay_artifact, committed_manifest_hash)
    if rav.supplied and rav.failure_category:
        fcc[rav.failure_category] = max(fcc.get(rav.failure_category, 0), 1)

    # Extract denominator.
    denominator: list[DenominatorRecord] = []
    if pt is not None and pt.computed:
        denominator = _extract_denominator_from_private(pt)
    if len(denominator) != EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR:
        fcc["denominator_mismatch"] = 1
        if len(denominator) != 0:
            fcc["denominator_mapping_failed"] = 1

    # Run retrieval reach smoke (only if all validation passed).
    arm_results: dict[str, list[ReachResult]] = {arm: [] for arm in REACH_ARMS}
    private_reach_manifest: dict[str, Any] | None = None
    retrieval_reach_executed = False
    if (enable_network and audit_match
            and fd1_private_decomposition_parsed_check(pt, rav)
            and len(denominator) == EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR):
        try:
            arm_results, reach_fcc, private_reach_manifest = _execute_retrieval_reach(
                openlocus_bin=openlocus_bin,
                denominator=denominator,
            )
            for k, v in reach_fcc.items():
                if k in fcc:
                    fcc[k] += v
            retrieval_reach_executed = True
        except Exception:
            fcc["retrieval_smoke_failed"] = 1
            fcc["unexpected_exception"] = 1
    elif not enable_network:
        fcc["network_required_but_disabled"] = 1

    aggregate_runtime_seconds = time.perf_counter() - start

    return _build_reach_report(
        self_test_passed=self_test_passed,
        self_test_checks_total=self_test_checks_total,
        self_test_checks_passed=None,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        fd1_artifact=fd1_artifact,
        fd1_source_schema_version=fd1_schema,
        fd1_source_artifact_hash=fd1_hash,
        fd1_committed_manifest_hash=committed_manifest_hash,
        pt=pt, rav=rav, denominator=denominator,
        arm_results=arm_results,
        extra_private_manifests=(
            [private_reach_manifest] if private_reach_manifest is not None else []
        ),
        retrieval_reach_executed=retrieval_reach_executed,
        audit_match=audit_match,
        audit_mismatch_reason=audit_mismatch_reason,
        failure_category_counts=fcc,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
    )


def fd1_private_decomposition_parsed_check(
    pt: bea_v1_p1.ParsedPrivateDecomposition | None,
    rav: bea_v1_p1.Fd1ReplayArtifactValidation | None,
) -> bool:
    """Check if FD1 private decomposition is parsed AND replay validated."""
    parsed = (
        pt is not None and pt.computed
        and pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS
        and pt.group_count == EXPECTED_RECORDS_DECOMPOSED
    )
    validated = (rav is not None and rav.validated)
    if pt is not None and pt.path_supplied and not validated:
        parsed = False
    return parsed


def _execute_retrieval_reach(
    *, openlocus_bin: str,
    denominator: list[DenominatorRecord],
) -> tuple[dict[str, list[ReachResult]], dict[str, int], dict[str, Any]]:
    """Execute the retrieval reach smoke on denominator records.

    Fetches the source benchmark rows, clones repos, and runs the
    retrieval arms. Returns ``(arm_results, fcc)``. No provider calls.
    """
    fcc: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    arm_results: dict[str, list[ReachResult]] = {arm: [] for arm in REACH_ARMS}
    reach_manifest: dict[str, Any] = {
        "manifest_name": "bea_v1_p2_private_reach_manifest",
        "schema_version": "bea_v1_p2_private_reach.v1",
        "storage_class": "private_tmp_only",
        "record_count": 0,
        "records_written": False,
        "path_publicly_serialized": False,
        "manifest_hash": "",
    }
    try:
        private_reach_dir = _resolve_private_reach_dir()
        private_reach_path = private_reach_dir / "bea_v1_p2.private_reach.jsonl"
        if private_reach_path.exists():
            private_reach_path.unlink()
    except Exception:
        private_reach_path = None
        fcc["retrieval_smoke_failed"] += 1

    # Group denominator records by (source_phase, benchmark).
    by_phase_bench: dict[tuple[str, str], list[DenominatorRecord]] = {}
    for d in denominator:
        key = (d.source_phase, d.benchmark)
        by_phase_bench.setdefault(key, []).append(d)

    # Fetch source benchmark rows and run retrieval.
    for (sp, bm), denom_records in by_phase_bench.items():
        # Determine the fetch offsets/limits for this benchmark.
        # BEA-4: contextbench offset 80 limit 80; repoqa offset 40 limit 40.
        # BEA-5: contextbench offset 0 limit 480; repoqa offset 0 limit 240.
        if sp == "BEA-4":
            if bm == "contextbench":
                cb_offset, cb_limit = 80, 80
            else:
                cb_offset, cb_limit = 40, 40
        else:  # BEA-5
            if bm == "contextbench":
                cb_offset, cb_limit = 0, 480
            else:
                cb_offset, cb_limit = 0, 240

        if bm == "contextbench":
            rows, fetch_status, _, fetch_fcc = bea4._fetch_heldout_contextbench_rows(
                cb_offset, cb_limit)
        else:
            rows, fetch_status, _, fetch_fcc = bea4._fetch_heldout_repoqa_needles(
                cb_offset, cb_limit)
        for k, v in fetch_fcc.items():
            if k in fcc:
                fcc[k] += v
        if fetch_status != "pass" or not rows:
            fcc["denominator_mapping_failed"] += 1
            continue

        # For each denominator record, find the matching source row and
        # run retrieval.
        for d in denom_records:
            idx = d.record_index
            if idx >= len(rows):
                fcc["denominator_mapping_failed"] += 1
                continue
            row = rows[idx]
            # Parse gold paths and query from the source row.
            if bm == "contextbench":
                gold_paths, _, gc_status = c5a._parse_gold_context(
                    row.get("gold_context"))
                if gc_status != "pass":
                    fcc["denominator_mapping_failed"] += 1
                    continue
                query = c5a._sanitize_query(
                    row.get("problem_statement", ""), "first_paragraph")
                if not query:
                    fcc["denominator_mapping_failed"] += 1
                    continue
                repo_url = row.get("repo_url", "")
                base_commit = row.get("base_commit", "")
            else:  # repoqa
                needle_path = str(
                    row.get("needle_path", row.get("path", "")) or ""
                )
                gold_paths = [needle_path] if needle_path else []
                if not gold_paths:
                    fcc["denominator_mapping_failed"] += 1
                    continue
                desc = c5d._sanitize_needle_description(
                    str(row.get("needle_description", row.get("description", "")) or ""))
                query = desc
                if not query:
                    fcc["denominator_mapping_failed"] += 1
                    continue
                repo_url = row.get("repo_url", "")
                base_commit = row.get("commit_sha", row.get("base_commit", ""))
            if not repo_url or not base_commit:
                fcc["denominator_mapping_failed"] += 1
                continue

            # Clone the repo.
            with tempfile.TemporaryDirectory(prefix=f"v1p2_{bm}_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(
                    repo_url, base_commit, rwd)
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    continue
                repo_root = rwd / "repo"

                # Build query variants for the query-anchor arm.
                query_variants = _build_query_variants(query)

                # Run each arm.
                for arm_name in REACH_ARMS:
                    if arm_name == "current_bea_candidate_pool_replay":
                        depth_mult = DEFAULT_DEPTH_MULTIPLIER
                        q_variants = None
                    elif arm_name == "expanded_pool_more_depth_same_methods":
                        depth_mult = EXPANDED_DEPTH_MULTIPLIER
                        q_variants = None
                    elif arm_name == "expanded_pool_query_anchor_variants":
                        depth_mult = DEFAULT_DEPTH_MULTIPLIER
                        q_variants = query_variants
                    else:  # expanded_pool_depth_plus_query_anchor
                        depth_mult = EXPANDED_DEPTH_MULTIPLIER
                        q_variants = query_variants
                    rr = _run_reach_for_record(
                        arm_name=arm_name,
                        openlocus_bin=openlocus_bin,
                        repo_root=repo_root,
                        query=query,
                        gold_paths=gold_paths,
                        depth_multiplier=depth_mult,
                        query_variants=q_variants,
                    )
                    rr.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                    arm_results[arm_name].append(rr)
                    if private_reach_path is not None:
                        try:
                            _append_private_jsonl(private_reach_path, {
                                "schema_version": "bea_v1_p2_private_reach.v1",
                                "source_phase": d.source_phase,
                                "benchmark": d.benchmark,
                                "private_record_id": d.private_record_id,
                                "arm_name": arm_name,
                                "gold_file_available": rr.gold_file_available,
                                "first_gold_file_rank": rr.first_gold_file_rank,
                                "gold_file_rank_band": rr.gold_file_rank_band,
                                "candidate_pool_size": rr.candidate_pool_size,
                                "duplicate_file_count": rr.duplicate_file_count,
                                "retrieval_latency_seconds": round(
                                    rr.retrieval_latency_seconds, 6),
                                "query_variants_private": rr.query_variants_private,
                                "candidate_paths_private": rr.candidate_paths_private,
                            })
                        except Exception:
                            fcc["retrieval_smoke_failed"] += 1
                    if rr.retrieval_error:
                        fcc["retrieval_smoke_failed"] += 1

    if private_reach_path is not None:
        reach_manifest = _private_file_manifest(
            private_reach_path,
            manifest_name="bea_v1_p2_private_reach_manifest",
            schema_version="bea_v1_p2_private_reach.v1",
        )
    return arm_results, fcc, reach_manifest


# ---------------------------------------------------------------------------
# Synthetic builders (self-test only)
# ---------------------------------------------------------------------------


def _build_synthetic_fd1_artifact() -> dict[str, Any]:
    """Reuse P1's synthetic FD1 artifact."""
    return bea_v1_p1._build_synthetic_fd1_artifact()


def _build_synthetic_fd1_replay_artifact(
    path: Path | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return bea_v1_p1._build_synthetic_fd1_replay_artifact(path, **kwargs)


def _build_synthetic_private_decomposition_jsonl(
    path: Path,
    *,
    gold_file_absent_count: int = 119,
    recoverable_lower_bound: int = 1,
) -> int:
    """Write a synthetic FD1 private decomposition JSONL to ``path``
    for P2 self-test.

    Unlike P1's builder (which uses ``synth-record-NNNN`` IDs), this
    builder uses the REAL FD1 private_record_id format
    (``contextbench-{idx}`` / ``repoqa-{idx}``) so the denominator
    extractor can map records back to source benchmark offsets.

    239 records × 5 baselines × 12 categories × 6 metrics = 86040 rows.
    The first ``gold_file_absent_count`` records are gold_file_absent
    (v0.3 file_recall@10==0 and success_rate==0). Of those, the first
    ``recoverable_lower_bound`` have at least one baseline arm with
    baseline_value > 0 for file_recall@10.
    """
    arms_v03 = "bea_v0_3_anchor_span_latency"
    baselines = (
        "bea_v0_2_diversity_risk", "bea_v0", "bm25_prefix_same_budget",
        "agreement_only_same_budget", "rrf_same_budget",
    )
    categories = bea_fd1.FAILURE_CATEGORIES
    metrics = (
        "file_recall@10", "mrr", "span_f0.5@10", "success_rate",
        "quality_per_latency", "latency_seconds",
    )
    rows_written = 0
    with path.open("w", encoding="utf-8") as fh:
        for rid_idx in range(EXPECTED_RECORDS_DECOMPOSED):
            # Use real FD1 record ID format: BEA-4 first 120 are
            # contextbench (offset 80), then repoqa (offset 40); BEA-5
            # remaining 119 are contextbench + repoqa.
            if rid_idx < 80:
                rid = f"contextbench-{rid_idx}"
                sp = "BEA-4"
                bm = "contextbench"
            elif rid_idx < 120:
                rid = f"repoqa-{rid_idx - 80}"
                sp = "BEA-4"
                bm = "repoqa"
            elif rid_idx < 202:
                rid = f"contextbench-{rid_idx - 120}"
                sp = "BEA-5"
                bm = "contextbench"
            else:
                rid = f"repoqa-{rid_idx - 202}"
                sp = "BEA-5"
                bm = "repoqa"
            is_gold_absent = rid_idx < gold_file_absent_count
            is_recoverable = rid_idx < recoverable_lower_bound
            for baseline in baselines:
                for category in categories:
                    for metric in metrics:
                        if metric == "latency_seconds":
                            t_val = 3.0
                            b_val = 2.0
                        else:
                            if is_gold_absent:
                                t_val = 0.0
                                if (metric == "file_recall@10"
                                        and is_recoverable
                                        and baseline == baselines[0]):
                                    b_val = 1.0
                                else:
                                    b_val = 0.0
                            else:
                                t_val = 1.0 if metric in (
                                    "file_recall@10", "success_rate",
                                    "mrr") else 0.5
                                b_val = 0.5
                        loss = max(0.0, b_val - t_val) if metric != "latency_seconds" else max(0.0, t_val - b_val)
                        delta = t_val - b_val
                        row = {
                            "phase_run_id": "v1p2-self-test",
                            "source_phase": sp,
                            "benchmark": bm,
                            "private_record_id": rid,
                            "policy_arm": arms_v03,
                            "category": category,
                            "baseline_arm": baseline,
                            "treatment_arm": arms_v03,
                            "metric": metric,
                            "treatment_value": t_val,
                            "baseline_value": b_val,
                            "loss": round(loss, 6),
                            "delta": round(delta, 6),
                            "category_availability": "available",
                            "latency_ms": 0, "cost_usd": 0.0,
                            "tokens": 0, "provider_calls": 0,
                        }
                        fh.write(json.dumps(row) + "\n")
                        rows_written += 1
    return rows_written


def _build_synthetic_reach_results(
    denominator_count: int = EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR,
    baseline_available: int = 1,
    expanded_available: int = 30,
) -> dict[str, list[ReachResult]]:
    """Build synthetic reach results for self-test.

    Baseline (current_bea_candidate_pool_replay): baseline_available
    records have gold_file_available=True. Expanded arms: expanded_available
    records have gold_file_available=True, with newly_reachable =
    expanded_available - baseline_available.
    """
    arm_results: dict[str, list[ReachResult]] = {arm: [] for arm in REACH_ARMS}
    for i in range(denominator_count):
        rid = f"contextbench-{i}"
        # Baseline.
        rr_base = ReachResult(
            arm_name="current_bea_candidate_pool_replay",
            private_record_id=rid)
        rr_base.candidate_pool_size = 50
        rr_base.retrieval_latency_seconds = 1.0
        if i < baseline_available:
            rr_base.gold_file_available = True
            rr_base.first_gold_file_rank = 15
            rr_base.gold_file_rank_band = _reach_rank_band(15)
        arm_results["current_bea_candidate_pool_replay"].append(rr_base)
        # Expanded depth.
        rr_depth = ReachResult(
            arm_name="expanded_pool_more_depth_same_methods",
            private_record_id=rid)
        rr_depth.candidate_pool_size = 150
        rr_depth.retrieval_latency_seconds = 1.8
        if i < expanded_available:
            rr_depth.gold_file_available = True
            rr_depth.first_gold_file_rank = 12
            rr_depth.gold_file_rank_band = _reach_rank_band(12)
        arm_results["expanded_pool_more_depth_same_methods"].append(rr_depth)
        # Query variants.
        rr_qv = ReachResult(
            arm_name="expanded_pool_query_anchor_variants",
            private_record_id=rid)
        rr_qv.candidate_pool_size = 80
        rr_qv.retrieval_latency_seconds = 1.5
        if i < expanded_available:
            rr_qv.gold_file_available = True
            rr_qv.first_gold_file_rank = 8
            rr_qv.gold_file_rank_band = _reach_rank_band(8)
        arm_results["expanded_pool_query_anchor_variants"].append(rr_qv)
        # Combined.
        rr_combo = ReachResult(
            arm_name="expanded_pool_depth_plus_query_anchor",
            private_record_id=rid)
        rr_combo.candidate_pool_size = 200
        rr_combo.retrieval_latency_seconds = 1.9  # <= 2x baseline
        if i < expanded_available:
            rr_combo.gold_file_available = True
            rr_combo.first_gold_file_rank = 6
            rr_combo.gold_file_rank_band = _reach_rank_band(6)
        arm_results["expanded_pool_depth_plus_query_anchor"].append(rr_combo)
    return arm_results


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic FD1 + synthetic reach results)
# ---------------------------------------------------------------------------


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    # --- G1: Identity ---
    for k, v in [("schema_version", SCHEMA_VERSION),
                 ("claim_level", CLAIM_LEVEL),
                 ("mode", MODE), ("phase", PHASE),
                 ("generated_by", GENERATED_BY)]:
        checks.append(_check(f"identity_{k}", bool(k and v)))

    # --- G2: Safe true / false flags ---
    for flag in ("aggregate_only_public_artifact", "diagnostic_only",
                 "bea_v1_p2_audit_evaluator_no_provider_calls",
                 "bea_v1_p2_audit_evaluator_no_selector_executed",
                 "bea_v1_p2_audit_evaluator_no_weight_tuning",
                 "bea_v1_p2_audit_evaluator_no_role_proxy"):
        checks.append(_check(f"safe_true_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is True))
    checks.append(_check("safe_true_no_retrieval_claim_absent",
        "bea_v1_p2_audit_evaluator_no_retrieval_executed"
        not in SAFE_TRUE_FLAGS))
    for flag in ("fd1_private_decomposition_parsed",
                 "fd1_private_decomposition_replay_supplied",
                 "fd1_private_decomposition_replay_validated",
                 "fd1_private_decomposition_replay_executed_by_workflow",
                 "retrieval_reach_executed",
                 "bea_v1_p2_reach_smoke_performed"):
        checks.append(_check(f"safe_false_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is False))
    for flag in ("role_proxy_assigned",
                 "gold_labels_used_for_query_construction",
                 "gold_labels_used_for_selection",
                 "v1_a_selector_executed",
                 "v04_full_matrix_claimed",
                 "fd2b_executed", "fd2c_executed",
                 "p4_executed", "p5_executed",
                 "b16k_executed",
                 "weights_tuned_during_bea_v1_p2",
                 "algorithm_changed_during_bea_v1_p2",
                 "default_should_change", "promotion_ready",
                 "provider_calls_made"):
        checks.append(_check(f"false_{flag}",
            DEFAULT_FALSE_FLAGS.get(flag) is False))
    checks.append(_check("no_role_proxy_used_field",
        "role_proxy_used" not in SAFE_TRUE_FLAGS))

    # --- G3: Reach arms (4) ---
    checks.append(_check("reach_arms_count_4", len(REACH_ARMS) == 4))
    for arm in REACH_ARMS:
        checks.append(_check(f"reach_arm_present_{arm}", arm in REACH_ARMS))

    # --- G4: Statuses enum ---
    for status in STATUSES:
        checks.append(_check(f"status_enum_{status}", isinstance(status, str)))
    checks.append(_check("statuses_count_7", len(STATUSES) == 7))
    checks.append(_check("allowed_real_run_statuses_count_4",
        len(ALLOWED_REAL_RUN_STATUSES) == 4))

    # --- G5: Stop/go constants ---
    checks.append(_check("go_newly_available_min_25",
        GO_NEWLY_AVAILABLE_COUNT_MIN == 25))
    checks.append(_check("go_availability_lift_min_020",
        GO_AVAILABILITY_LIFT_MIN == 0.20))
    checks.append(_check("no_go_pool_max_mult_4",
        NO_GO_POOL_SIZE_MAX_MULTIPLIER == 4))
    checks.append(_check("no_go_latency_max_mult_2",
        NO_GO_LATENCY_MAX_MULTIPLIER == 2))

    # --- G6: Denominator expected 119 ---
    checks.append(_check("expected_denominator_119",
        EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR == 119))

    # --- G7: P1 binding context ---
    checks.append(_check("v1_p1_result_checkpoint",
        V1_P1_RESULT_CHECKPOINT == "d96e860"))
    checks.append(_check("v1_p1_result_status",
        V1_P1_RESULT_STATUS == "no_go_retrieval_availability_limit"))
    checks.append(_check("v1_p1_denominator_119",
        V1_P1_GOLD_FILE_ABSENT_DENOMINATOR == 119))
    checks.append(_check("v1_p1_lower_bound_1",
        V1_P1_FILE_SELECTOR_LOWER_BOUND == 1))
    checks.append(_check("v1_p1_retrieval_rate",
        V1_P1_RETRIEVAL_AVAILABILITY_RATE == 0.991597))

    # --- G8: Query variant construction (no gold/private labels) ---
    variants = _build_query_variants(
        "Fix bug in MyClass.handleRequest where import foo.bar.baz fails. "
        "See src/utils/handler.py for the path CamelCase snake_case "
        "ALL_CAPS_TOKEN")
    checks.append(_check("variants_nonempty", len(variants) > 0))
    checks.append(_check("variants_includes_original",
        variants[0].startswith("Fix bug")))
    # No gold paths leaked into variants (defensive — the query itself
    # is the only source).
    checks.append(_check("variants_deduplicated",
        len(variants) == len(set(variants))))
    checks.append(_check("regex_safe_escapes_brackets",
        _regex_safe_query("foo[bar]") == r"foo\[bar\]"))
    checks.append(_check("symbol_safe_returns_identifier",
        _symbol_safe_query("Fix FooBar [broken]") == "Fix"))
    rrf = _derive_rrf_candidates_from_candidates([
        {"method": "bm25", "rank": 1, "score": 1.0, "path": "a.py",
         "start_line": 1, "end_line": 2, "content_sha": ""},
        {"method": "regex", "rank": 1, "score": 1.0, "path": "a.py",
         "start_line": 1, "end_line": 2, "content_sha": ""},
        {"method": "symbol", "rank": 2, "score": 0.5, "path": "b.py",
         "start_line": 3, "end_line": 4, "content_sha": ""},
    ], 2)
    checks.append(_check("derived_rrf_nonempty", len(rrf) == 2))
    checks.append(_check("derived_rrf_agreement_first", rrf[0].get("path") == "a.py"))

    # --- G9: Denominator extraction ---
    # Build a synthetic private decomposition with 119 gold_file_absent.
    with tempfile.TemporaryDirectory(prefix="v1p2_st_") as sd:
        td = Path(sd)
        priv_jsonl = td / "bea_fd1.decomposition.jsonl"
        _build_synthetic_private_decomposition_jsonl(
            priv_jsonl, gold_file_absent_count=119,
            recoverable_lower_bound=1)
        pt = _parse_private_decomposition_jsonl(priv_jsonl)
        _compute_file_selector_lower_bound(pt)
        checks.append(_check("synth_pt_row_count_86040",
            pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS))
        checks.append(_check("synth_pt_group_count_239",
            pt.group_count == EXPECTED_RECORDS_DECOMPOSED))
        checks.append(_check("synth_pt_denominator_119",
            pt.gold_file_absent_denominator == 119))
        denominator = _extract_denominator_from_private(pt)
        checks.append(_check("synth_denominator_119",
            len(denominator) == 119))
        # Denominator records have no gold paths/queries (private only).
        for d in denominator[:5]:
            checks.append(_check("denom_no_gold_paths",
                not hasattr(d, "gold_paths")))

    # --- G10: Forbidden scanner ---
    safe_sample = {
        "schema_version": SCHEMA_VERSION,
        "status": "bea_v1_p2_retrieval_reach_pass",
        "arm_reach_records": [
            {"arm_name": "current_bea_candidate_pool_replay",
             "denominator_record_count": 119,
             "gold_file_available_any_pool": 1,
             "gold_file_available_rate": 0.008403,
             "gold_file_available_at_50": 1,
             "gold_file_available_at_100": 1,
             "gold_file_available_at_200": 1,
             "first_gold_file_rank_mean": 15.0,
             "first_gold_file_rank_median": 15.0,
             "candidate_pool_size_mean": 50.0,
             "retrieval_latency_mean_seconds": 1.0,
             "duplicate_file_rate": 0.1,
             "newly_reachable_count": 0,
             "still_unavailable_count": 118},
        ],
        "stop_go_records": [{
            "stop_go_decision": "bea_v1_p2_retrieval_reach_pass",
            "stop_go_reason": "test",
            "newly_available_count": 29,
            "availability_lift": 28.0,
            "pool_cost_exceeded": False,
            "latency_cost_exceeded": False,
            "runtime_clean_mechanism_dominates": True,
            "selector_problem_remains": True,
            "go_threshold_newly_available_min": 25,
            "go_threshold_availability_lift_min": 0.20,
            "no_go_threshold_pool_size_max_multiplier": 4,
            "no_go_threshold_latency_max_multiplier": 2,
        }],
        "private_manifest_records": [{
            "manifest_name": "fd1_private_decomposition_manifest",
            "records_written": True, "record_count": 86040,
            "schema_version": bea_fd1.PRIVATE_DECOMP_SCHEMA_VERSION,
            "manifest_hash": "a" * 64,
            "storage_class": "fd1_committed_artifact",
            "path_publicly_serialized": False,
        }],
        "framing": {"signal_strength":
            "bea_v1_p2_candidate_availability_reach_smoke_aggregate_only"},
        "fd1_source_artifact_hash": "b" * 64,
        "v1_p1_result_checkpoint": V1_P1_RESULT_CHECKPOINT,
    }
    checks.append(_check("scanner_allows_safe", not _scan_v1_p2(safe_sample)))
    # Forbidden leaks.
    for fk in ("private_trace_dir", "per_record_reach",
               "per_record_candidates", "per_record_query_variants",
               "candidate_paths", "candidate_keys", "query_text",
               "queries", "query_variants",
               "gold_paths", "gold_lines", "gold_files", "gold_match_labels",
               "snippets", "selected_order", "private_record_id",
               "private_record_ids", "repo_url", "base_commit",
               "raw_reach_row", "raw_candidate_row",
               "fd1_replay_artifact_path", "reach_results_path",
               "winner", "calibration", "method_winner",
               "recommended_default", "ranking", "decision",
               "hard_gates", "failure_category_counts",
               "arm_reach_counts", "self_test_checks",
               "role_proxy", "role_proxy_assignment",
               "is_v04_repair", "is_fd2_b", "is_fd2_c",
               "is_p4", "is_p5", "is_v031_tuning", "is_b16k",
               "is_dense_quality_mixing", "is_quiver_quality_mixing"):
        leaked = dict(safe_sample)
        leaked[fk] = "leak"
        checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_v1_p2(leaked))))

    # --- G11: Fail-closed enforcement ---
    try:
        _enforce_v1_p2_no_forbidden(safe_sample)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk in ("private_trace_dir", "per_record_reach",
               "gold_paths", "winner", "hard_gates",
               "self_test_checks", "candidate_paths",
               "repo_url", "query_variants"):
        leaked = dict(safe_sample)
        leaked[lk] = "leak"
        try:
            _enforce_v1_p2_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # --- G12: Build reach report (synthetic) ---
    fd1_art = _build_synthetic_fd1_artifact()
    priv_jsonl2 = Path(tempfile.mkdtemp(prefix="v1p2_rep_")) / "bea_fd1.decomposition.jsonl"
    _build_synthetic_private_decomposition_jsonl(
        priv_jsonl2, gold_file_absent_count=119,
        recoverable_lower_bound=1)
    pt2 = _parse_private_decomposition_jsonl(priv_jsonl2)
    _compute_file_selector_lower_bound(pt2)
    denominator2 = _extract_denominator_from_private(pt2)
    replay_path = Path(tempfile.mkdtemp(prefix="v1p2_rav_")) / "fd1_replay_report.json"
    _build_synthetic_fd1_replay_artifact(replay_path)
    rav2 = _validate_fd1_replay_artifact(replay_path, "a" * 64)
    arm_results = _build_synthetic_reach_results(
        denominator_count=119, baseline_available=1, expanded_available=30)
    report = _build_reach_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results,
        retrieval_reach_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
    )
    # Records-only shape.
    required_tables = (
        "source_run_records", "denominator_records",
        "arm_reach_records", "arm_delta_records",
        "reach_bucket_records", "rank_band_records",
        "cost_safety_records", "stop_go_records",
        "gate_records", "private_manifest_records",
        "failure_category_count_records",
    )
    for table in required_tables:
        checks.append(_check(f"table_{table}_is_list",
            isinstance(report.get(table), list)))
        checks.append(_check(f"table_{table}_nonempty",
            len(report.get(table, [])) > 0))
    checks.append(_check("framing_present",
        isinstance(report.get("framing"), dict)))
    checks.append(_check("forbidden_scan_present",
        isinstance(report.get("forbidden_scan"), dict)))
    checks.append(_check("forbidden_scan_pass",
        report.get("forbidden_scan", {}).get("status") == "pass"))
    # No forbidden top-level fields.
    for ff in ("private_trace_dir", "per_record_reach",
               "candidate_paths", "gold_paths", "query_text",
               "query_variants", "selected_order", "winner", "calibration",
               "hard_gates", "failure_category_counts",
               "arm_reach_counts", "self_test_checks",
               "repo_url", "base_commit",
               "role_proxy_used", "target_support_proxy_used",
               "is_v04_repair", "is_fd2_b", "is_p4", "is_b16k",
               "is_dense_quality_mixing"):
        checks.append(_check(f"no_top_level_{ff}", ff not in report))
    checks.append(_check("self_scan_clean", not _scan_v1_p2(report)))

    # --- G13: Records-only natural-key uniqueness ---
    checks.append(_check("srr_unique", not _check_unique_records(
        report.get("source_run_records", []), _srr_natural_key,
        "source_run_records")))
    checks.append(_check("dnr_unique", not _check_unique_records(
        report.get("denominator_records", []), _dnr_natural_key,
        "denominator_records")))
    checks.append(_check("arr_unique", not _check_unique_records(
        report.get("arm_reach_records", []), _arr_natural_key,
        "arm_reach_records")))
    checks.append(_check("adr_unique", not _check_unique_records(
        report.get("arm_delta_records", []), _adr_natural_key,
        "arm_delta_records")))
    checks.append(_check("rbr_unique", not _check_unique_records(
        report.get("reach_bucket_records", []), _rbr_natural_key,
        "reach_bucket_records")))
    checks.append(_check("rkr_unique", not _check_unique_records(
        report.get("rank_band_records", []), _rkr_natural_key,
        "rank_band_records")))
    checks.append(_check("csr_unique", not _check_unique_records(
        report.get("cost_safety_records", []), _csr_natural_key,
        "cost_safety_records")))
    checks.append(_check("sgr_unique", not _check_unique_records(
        report.get("stop_go_records", []), _sgr_natural_key,
        "stop_go_records")))
    checks.append(_check("gr_unique", not _check_unique_records(
        report.get("gate_records", []), _gr_natural_key, "gate_records")))
    checks.append(_check("pmr_unique", not _check_unique_records(
        report.get("private_manifest_records", []), _pmr_natural_key,
        "private_manifest_records")))
    checks.append(_check("fccr_unique", not _check_unique_records(
        report.get("failure_category_count_records", []), _fccr_natural_key,
        "failure_category_count_records")))

    # --- G14: Synthetic status pass ---
    # 119 denominator, baseline_available=1, expanded_available=30 →
    # newly_reachable=29 >= 25 → pass.
    checks.append(_check("synth_status_pass",
        report.get("status") == "bea_v1_p2_retrieval_reach_pass"))
    sgr = report.get("stop_go_records", [{}])[0] if report.get(
        "stop_go_records") else {}
    checks.append(_check("synth_stop_go_pass",
        sgr.get("stop_go_decision") == "bea_v1_p2_retrieval_reach_pass"))
    checks.append(_check("synth_newly_available_29",
        sgr.get("newly_available_count") == 29))

    # --- G15: Arm reach records (4 arms) ---
    arr_rows = report.get("arm_reach_records", [])
    checks.append(_check("arr_count_4", len(arr_rows) == 4))
    arr_arms = {r.get("arm_name") for r in arr_rows}
    for arm in REACH_ARMS:
        checks.append(_check(f"arr_has_{arm}", arm in arr_arms))

    # --- G16: Denominator records ---
    dnr_rows = report.get("denominator_records", [])
    checks.append(_check("dnr_nonempty", len(dnr_rows) > 0))
    total_denom = sum(r.get("denominator_record_count", 0) for r in dnr_rows)
    checks.append(_check("dnr_total_119", total_denom == 119))

    # --- G17: Status decision logic ---
    status_no_replay = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=False,
        replay_artifact_validated=False,
        denominator_count=0,
        retrieval_reach_executed=False,
        pool_cost_exceeded=False,
        stop_go_decision="no_go_replay_mismatch",
    )
    checks.append(_check("decide_status_no_replay",
        status_no_replay == "no_go_replay_mismatch"))
    status_blocking = _decide_status(
        audit_match=True, blocking_failure_count=1,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_reach_executed=True,
        pool_cost_exceeded=False,
        stop_go_decision="bea_v1_p2_retrieval_reach_pass",
    )
    checks.append(_check("decide_status_blocking",
        status_blocking == "fail_schema_contract"))
    status_cost = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_reach_executed=True,
        pool_cost_exceeded=True,
        stop_go_decision="no_go_retrieval_reach_latency_or_pool_cost",
    )
    checks.append(_check("decide_status_cost",
        status_cost == "no_go_retrieval_reach_latency_or_pool_cost"))
    status_insufficient = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_reach_executed=True,
        pool_cost_exceeded=False,
        stop_go_decision="no_go_retrieval_reach_insufficient",
    )
    checks.append(_check("decide_status_insufficient",
        status_insufficient == "no_go_retrieval_reach_insufficient"))

    # --- G18: Unavailable report ---
    unavail = _build_unavailable_report(
        "network_required_but_disabled", self_test_passed=True,
        openlocus_binary_source="self_test", network_mode="self_test",
    )
    checks.append(_check("unavail_status",
        unavail["status"] == "unavailable_with_reason"))
    checks.append(_check("unavail_scan_clean", not _scan_v1_p2(unavail)))
    for table in required_tables:
        if table in ("gate_records", "private_manifest_records",
                     "failure_category_count_records", "source_run_records",
                     "stop_go_records"):
            checks.append(_check(f"unavail_table_{table}_is_list",
                isinstance(unavail.get(table), list)))
        else:
            checks.append(_check(f"unavail_table_{table}_empty",
                unavail.get(table) == []))

    # --- G19: CLI surface ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for opt in ("--self-test", "--out", "--fd1-artifact",
                "--fd1-private-decomposition-jsonl",
                "--fd1-replay-artifact", "--openlocus",
                "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in option_strings))
    for opt in ("--budget", "--methods",
                "--private-trace-dir", "--private-decomposition-dir"):
        checks.append(_check(f"cli_no_{opt}", opt not in option_strings))

    # --- G20: No-provider-calls binding ---
    checks.append(_check("no_provider_calls_field",
        report.get("provider_calls_made") is False))
    checks.append(_check("unavail_no_provider_calls",
        unavail.get("provider_calls_made") is False))

    # --- G21: License fields ---
    for field, expected in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{field}",
            report.get(field) == expected))

    # --- G22: Framing is_candidate_availability_reach_smoke ---
    checks.append(_check("framing_is_reach_smoke",
        report.get("framing", {}).get(
            "is_candidate_availability_reach_smoke") is True))
    checks.append(_check("framing_not_v04_repair",
        report.get("framing", {}).get("is_v04_repair") is False))
    checks.append(_check("framing_not_fd2_b",
        report.get("framing", {}).get("is_fd2_b") is False))
    checks.append(_check("framing_not_dense_mixing",
        report.get("framing", {}).get(
            "is_dense_quality_mixing") is False))

    # --- G23: failure_category_count_records covers all audit categories ---
    fccr_cats = {r.get("failure_category")
                 for r in report.get("failure_category_count_records", [])}
    for cat in FAILURE_CATEGORIES_AUDIT:
        checks.append(_check(f"fccr_has_{cat}", cat in fccr_cats))

    # --- G24: Reach bucket records ---
    rbr_rows = report.get("reach_bucket_records", [])
    checks.append(_check("rbr_records_present", len(rbr_rows) > 0))
    # 4 arms x 6 buckets = 24 rows.
    checks.append(_check("rbr_count_24", len(rbr_rows) == 24))

    # --- G25: Rank band records ---
    rkr_rows = report.get("rank_band_records", [])
    checks.append(_check("rkr_records_present", len(rkr_rows) > 0))
    # 4 arms x 6 bands = 24 rows.
    checks.append(_check("rkr_count_24", len(rkr_rows) == 24))

    # --- G26: Cost safety records ---
    csr_rows = report.get("cost_safety_records", [])
    checks.append(_check("csr_count_2", len(csr_rows) == 2))
    csr_axes = {r.get("cost_safety_axis") for r in csr_rows}
    checks.append(_check("csr_has_pool_mult",
        "max_pool_size_multiplier" in csr_axes))
    checks.append(_check("csr_has_latency_mult",
        "max_latency_multiplier" in csr_axes))

    with tempfile.TemporaryDirectory(prefix="v1p2_manifest_st_") as sd:
        priv = Path(sd) / "reach.jsonl"
        _append_private_jsonl(priv, {"row": 1})
        _append_private_jsonl(priv, {"row": 2})
        pm = _private_file_manifest(
            priv,
            manifest_name="bea_v1_p2_private_reach_manifest",
            schema_version="bea_v1_p2_private_reach.v1",
        )
        checks.append(_check("private_reach_manifest_count_2",
            pm.get("record_count") == 2))
        checks.append(_check("private_reach_manifest_path_not_serialized",
            pm.get("path_publicly_serialized") is False))

    # --- G27: No-go when newly_available below threshold ---
    # Use a higher baseline (20) so that expanded_available=25 gives
    # newly=5 < 25 AND lift=0.25 >= 0.20. Actually with lift >= 0.20
    # this passes materiality. Use baseline=20, expanded=22 → newly=2
    # < 25 AND lift=0.1 < 0.20 → insufficient.
    arm_results_low = _build_synthetic_reach_results(
        denominator_count=119, baseline_available=20, expanded_available=22)
    report_low = _build_reach_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results_low,
        retrieval_reach_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
    )
    # newly_reachable = 22 - 20 = 2 < 25; lift = 2/20 = 0.1 < 0.20
    # → no_go_retrieval_reach_insufficient.
    checks.append(_check("low_newly_status_insufficient",
        report_low.get("status") == "no_go_retrieval_reach_insufficient"))
    checks.append(_check("low_newly_stop_go_insufficient",
        report_low["stop_go_records"][0]["stop_go_decision"]
        == "no_go_retrieval_reach_insufficient"))
    checks.append(_check("availability_lift_uses_denominator",
        report_low["stop_go_records"][0]["availability_lift"]
        == round(2 / EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR, 6)))

    # --- G28: No-go when denominator mismatch ---
    report_mismatch = _build_reach_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=[],  # empty denominator
        arm_results={arm: [] for arm in REACH_ARMS},
        retrieval_reach_executed=False,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
    )
    checks.append(_check("mismatch_status_no_go",
        report_mismatch.get("status") == "no_go_replay_mismatch"))

    all_passed = all(c["passed"] for c in checks if c is not None)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description="BEA-v1-P2 Candidate Availability / Retrieval Reach Smoke"
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument(
        "--fd1-private-decomposition-jsonl", type=Path, default=None,
        help="Path to a regenerated FD1 private decomposition JSONL.",
    )
    ap.add_argument(
        "--fd1-replay-artifact", type=Path, default=None,
        help="Path to the regenerated FD1 replay report (fd1_replay_report.json).",
    )
    ap.add_argument("--openlocus", default=None,
                    help="Path to the OpenLocus binary (for retrieval reach).")
    ap.add_argument("--enable-external-benchmark-network",
                    action="store_true")
    return ap


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            tag = "PASS" if c["passed"] else "FAIL"
            print(f"[{tag}] {c['check']}")
        passed_count = sum(1 for c in checks if c["passed"])
        print(f"self_test_passed={passed} "
              f"({passed_count}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    out_path = args.out if args.out is not None else DEFAULT_OUT
    fd1_artifact_path = (args.fd1_artifact if args.fd1_artifact is not None
                         else DEFAULT_FD1_ARTIFACT)
    fd1_private_jsonl = args.fd1_private_decomposition_jsonl
    fd1_replay_artifact_path = args.fd1_replay_artifact
    enable_network = bool(args.enable_external_benchmark_network)

    checks, self_test_passed = run_self_test_checks()
    self_test_checks_total = len(checks)
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact",
              file=sys.stderr)
        sys.exit(1)

    # Resolve OpenLocus binary.
    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(
        args.openlocus)

    if enable_network and openlocus_bin is None:
        fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
        fcc["openlocus_binary_missing"] = 1
        report = _build_unavailable_report(
            "openlocus_binary_missing",
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
            failure_category_counts=fcc,
        )
        _enforce_v1_p2_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    network_mode = "local_explicit" if enable_network else "disabled_opt_in"

    if not enable_network:
        # Default no-network: honest no_go_replay_mismatch (no fake pass).
        fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
        fcc["network_required_but_disabled"] = 1
        report = _build_unavailable_report(
            "network_required_but_disabled",
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source or "missing",
            network_mode=network_mode,
            failure_category_counts=fcc,
        )
        _enforce_v1_p2_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real "
              "BEA-v1-P2 retrieval reach smoke.")
        return

    try:
        report = _run_reach_smoke(
            openlocus_bin=openlocus_bin or "",
            openlocus_binary_source=openlocus_source or "explicit",
            network_mode=network_mode,
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            fd1_artifact_path=fd1_artifact_path,
            fd1_private_decomposition_jsonl=fd1_private_jsonl,
            fd1_replay_artifact=fd1_replay_artifact_path,
            enable_network=enable_network,
        )
    except Exception:
        fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
        fcc["unexpected_exception"] = 1
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source or "explicit",
            network_mode=network_mode,
            failure_category_counts=fcc,
        )

    if report.get("provider_calls_made") is not False:
        report["status"] = "fail_schema_contract"

    _enforce_v1_p2_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    sgr = report.get("stop_go_records", [{}])[0] if report.get(
        "stop_go_records") else {}
    print(f"wrote artifact (forbidden_scan="
          f"{report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"denominator_count={report.get('denominator_count', 0)}, "
          f"stop_go_decision={sgr.get('stop_go_decision', '')})")


if __name__ == "__main__":
    main()
