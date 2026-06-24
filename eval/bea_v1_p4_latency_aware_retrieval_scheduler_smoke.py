#!/usr/bin/env python3
"""BEA-v1-P4: Latency-Aware Retrieval Action Scheduler Smoke (Public
Records-Only).

BEA-v1-P4 is the **fourth phase of BEA v1 Hierarchical Actionable
Evidence Acquisition**, run after the BEA-v1-P3 result checkpoint
``eda2087``. P3 ran a constrained retrieval policy smoke over the FD1
``gold_file_absent`` denominator (119 records) and produced a strong
retrieval-action mechanism signal but failed latency safety: baseline
reached 32/119; P2 depth-only reached 59/119 (+27); P3 constrained
reached 58/119 (+26), pool 41.50 / 2.08x baseline, latency 3.645s /
2.17x baseline > 2.0 gate, efficiency 1.208122. P3 status is
``no_go_p3_cost_exceeded``. P3 preserved reach and pool efficiency but
failed latency safety, and the next question is whether P3's latency
failure came from avoidable sequential / redundant retrieval actions.

Goal
----

P4 isolates whether P3's latency failure came from avoidable sequential
/ redundant retrieval actions and tests **one runtime-clean scheduler
fix** that reduces latency while preserving P3 / P2 reach. This is a
real retrieval-action scheduler smoke, NOT selector / default /
promotion. Latency / cost remain in retrieval action scheduling /
stop decisions, NOT candidate relevance scoring.

Arms (4, fixed)
---------------

1. ``current_bea_candidate_pool_replay`` -- baseline depth=1, expected
   ~32/119.
2. ``p2_depth_only_reference`` -- depth=4 all methods, expected ~59/119,
   reference only.
3. ``p3_constrained_depth_policy_reference`` -- exact P3 policy,
   expected ~58/119, latency ~2.17x, failure reference.
4. ``p4_latency_aware_action_scheduler`` -- main treatment, same
   retrieval methods, no query anchors, action scheduling only.

P4 scheduler mechanism (runtime-clean retrieval-action scheduler)
-----------------------------------------------------------------

The P4 arm is a **retrieval-action scheduler**, NOT candidate relevance
scoring. Latency is measured and used only to decide actions / stop and
for cost gates, never to rank candidates.

* **Baseline round**: run bm25, literal-regex, symbol at depth=1
  **per-channel** (cached); derive RRF from the method result lists.
* **Runtime-clean diagnostics per channel**: non-empty channels, unique
  file count, duplicate-file rate, method agreement, per-channel
  new-file yield from baseline, score mass / spread, query-token /
  path-token overlap, per-channel elapsed time from current run.
* **Extra-depth channel gating**: instead of P3's full extra-depth round
  across all channels, choose extra-depth actions per channel:
  - Run extra depth only for channels whose baseline result is sparse or
    high-yield-looking.
  - Skip channels that are empty / failing, saturated, duplicate-heavy,
    or already overlapped by another channel.
  - Stop when unique-file cap / candidate cap / action budget reached.
  - Cache / reuse baseline channel outputs so extra-depth does not
    rerun the same baseline work.
  - Keep one simple predeclared policy, no threshold search / matrix.
* **No query anchors** in P4.
* **Latency can be measured and used only to decide actions / stop and
  for cost gates, not to rank candidates.**

Binding invariants
------------------

* claim_level = ``bea_v1_p4_latency_aware_retrieval_scheduler_smoke_only``
* status: ``bea_v1_p4_latency_aware_retrieval_scheduler_pass`` |
  ``no_go_p4_reach_not_preserved`` |
  ``no_go_p4_latency_not_fixed`` |
  ``no_go_p4_cost_exceeded`` |
  ``no_go_p4_policy_degenerate`` |
  ``no_go_p4_replay_mismatch`` |
  ``unavailable_with_reason`` |
  ``fail_forbidden_scan`` |
  ``fail_schema_contract``
* mode = ``bea_v1_p4_latency_aware_retrieval_scheduler_smoke``; phase =
  ``BEA-v1-P4``

* The default no-network BEA-v1-P4 artifact does NOT run retrieval,
  selector, or provider calls. The explicit manual CI / network path
  regenerates the FD1 private decomposition under ``/tmp`` AND runs the
  BEA-v1-P4 retrieval scheduler smoke (network + OpenLocus binary, no
  provider secrets). Gold / private labels are used ONLY for
  evaluation / scoring reach, never to construct queries / candidates /
  policy.
* No role / support proxies. No v0.4 repair. No FD2-B / FD2-C. No
  v0.31 / v0.32 tuning. No B16-K. No dense / graph / QuIVer quality
  mixing. No selector / packer runtime change. No latency in candidate
  relevance scoring. No query anchors.
* Public artifact is aggregate-only and records-only. No public record
  IDs, paths, queries, snippets, gold files, candidate lists,
  per-record ranks, private trace paths, or private row payloads.

Network / CI policy (binding)
-----------------------------

* Default no-network self-test passes without HuggingFace / GitHub and
  without the committed FD1 / FD2-A1 artifacts or any private JSONL
  (self-test uses synthetic FD1 aggregate and synthetic reach rows).
* Default no-network / no-private-JSONL artifact is truthfully
  ``unavailable_with_reason`` (no fake pass). The CI workflow
  regenerates the FD1 private decomposition under ``/tmp``, validates
  it, reruns the P4 retrieval scheduler smoke, and passes the JSONL +
  replay report + reach results via CLI args.
* CI is a separate explicit workflow_dispatch job; it must NOT run on
  PR / push by default, must use no provider secrets / vars / model env,
  and must upload only the aggregate report. Private JSONL / JSON files
  are NEVER uploaded.

Run::

    python3 -m py_compile eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py
    python3 eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py --self-test
    python3 eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py \
        --out artifacts/bea_v1_p4_latency_aware_retrieval_scheduler/\
bea_v1_p4_latency_aware_retrieval_scheduler_smoke_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

# Reuse P3's scanner composition, FD1 replay validation, denominator
# extraction, and runtime-safe retrieval helpers. BEA-v1-P4 does NOT
# import any BEA-v0.4-P1/P2/P3 module (role-proxy line), does NOT use
# role proxies, and does NOT run a selector. It reuses P3's / P2's
# runtime-safe retrieval helpers (depth expansion, derived RRF, dedup)
# but applies them under a latency-aware retrieval-action scheduler.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea_v1_p3_constrained_retrieval_policy_smoke as bea_v1_p3  # noqa: E402
import bea_v1_p2_candidate_availability_reach_smoke as bea_v1_p2  # noqa: E402
import bea_v1_p1_actionability_audit as bea_v1_p1  # noqa: E402
import bea_fd1_failure_decomposition as bea_fd1  # noqa: E402
import bea4_external_scale_smoke as bea4  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import bea1_mechanism_ablation as bea1  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402

# --- Schema / claim constants ---
SCHEMA_VERSION = "bea_v1_p4_latency_aware_retrieval_scheduler_smoke.v1"
GENERATED_BY = "eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py"
CLAIM_LEVEL = "bea_v1_p4_latency_aware_retrieval_scheduler_smoke_only"
MODE = "bea_v1_p4_latency_aware_retrieval_scheduler_smoke"
PHASE = "BEA-v1-P4"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p4_latency_aware_retrieval_scheduler/"
    "bea_v1_p4_latency_aware_retrieval_scheduler_smoke_report.json"
)
DEFAULT_FD1_ARTIFACT = bea_fd1.DEFAULT_OUT

# --- P3 binding context (read-only) ---
V1_P3_RESULT_CHECKPOINT = "eda2087"
V1_P3_RESULT_STATUS = "no_go_p3_cost_exceeded"
V1_P3_CI_RUN_ID = "28102428194"
V1_P3_BASELINE_REACH = 32
V1_P3_DEPTH_REACH = 59
V1_P3_DEPTH_NEWLY = 27
V1_P3_CONSTRAINED_REACH = 58
V1_P3_CONSTRAINED_NEWLY = 26
V1_P3_AVAILABILITY_LIFT = 0.218487
V1_P3_POOL_MEAN = 41.504202
V1_P3_POOL_MULT = 2.076955
V1_P3_LATENCY_MEAN = 3.644513
V1_P3_LATENCY_MULT = 2.172635
V1_P3_EFFICIENCY = 1.208122
V1_P3_FIRST_GOLD_RANK_MEAN = 25.689655
V1_P3_RECORDS_FIRST_GOLD_RANK_ABOVE_BUDGET = 50

# --- P2 binding context (read-only) ---
V1_P2_RESULT_CHECKPOINT = "930dd48"
V1_P2_RESULT_STATUS = "no_go_retrieval_reach_latency_or_pool_cost"
V1_P2_CI_RUN_ID = "28093864524"
V1_P2_BASELINE_REACH = 32
V1_P2_DEPTH_REACH = 59
V1_P2_DEPTH_NEWLY = 27
V1_P2_DEPTH_EFFICIENCY = bea_v1_p3.V1_P2_DEPTH_EFFICIENCY  # 0.560146
V1_P2_COMBINED_EFFICIENCY = bea_v1_p3.V1_P2_COMBINED_EFFICIENCY  # 0.268648

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

FIXED_BUDGET = bea_fd1.FIXED_BUDGET  # 5
FIXED_METHODS = tuple(bea_fd1.FIXED_METHODS.split(","))  # bm25,regex,symbol

EXPECTED_RECORDS_DECOMPOSED = bea_fd1.EXPECTED_DECOMPOSED_RECORDS  # 239
EXPECTED_PRIVATE_DECOMP_ROWS = bea_fd1.EXPECTED_PRIVATE_DECOMP_ROWS  # 86040
EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR = 119

# --- Retrieval scheduler arms (4, fixed) ---
POLICY_ARMS = (
    "current_bea_candidate_pool_replay",
    "p2_depth_only_reference",
    "p3_constrained_depth_policy_reference",
    "p4_latency_aware_action_scheduler",
)

BASELINE_DEPTH_MULTIPLIER = 1
DEPTH_REFERENCE_MULTIPLIER = 4
DEFAULT_RETRIEVAL_LIMIT = 20
RANK_BANDS = (10, 50, 100, 200)

# --- P4 latency-aware scheduler constants (binding) ---
P4_HARD_CANDIDATE_CAP = 100
P4_UNIQUE_FILE_CAP = 80
# At most 2 extra-depth channel actions total (predeclared). P3 ran ONE
# full extra-depth round across ALL channels; P4 runs at most 1-2
# SELECTED channel actions.
P4_EXTRA_DEPTH_CHANNEL_ACTION_BUDGET_MAX = 2
P4_CHANNEL_MARGINAL_YIELD_MIN = 2
P4_CHANNEL_UNIQUE_FILE_CAP = 60
P4_CHANNEL_MIN_UNIQUE_SHARE = 0.10
P4_CHANNEL_DUP_FILE_RATE_MAX = 0.70
P4_CHANNEL_OVERLAP_MAX = 0.85
P4_QUERY_ANCHORS_ENABLED = False

STATUSES = (
    "bea_v1_p4_latency_aware_retrieval_scheduler_pass",
    "no_go_p4_reach_not_preserved",
    "no_go_p4_latency_not_fixed",
    "no_go_p4_cost_exceeded",
    "no_go_p4_policy_degenerate",
    "no_go_p4_replay_mismatch",
    "unavailable_with_reason",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "bea_v1_p4_latency_aware_retrieval_scheduler_pass",
    "no_go_p4_reach_not_preserved",
    "no_go_p4_latency_not_fixed",
    "no_go_p4_cost_exceeded",
    "no_go_p4_policy_degenerate",
})

# --- Research success gates (binding) ---
P4_REACH_PRESERVATION_NEWLY_MIN = 20
P4_REACH_PRESERVATION_DEPTH_RATIO = 0.75
P4_LATENCY_MULT_MAX = 2.0
P4_LATENCY_VS_P3_IMPROVEMENT_MIN = 0.10
P4_POOL_MULT_MAX = 4.0
P4_HARD_CAP_VIOLATION_MAX = 0
P4_EFFICIENCY_VS_P3_RATIO = 0.80
P4_ACTION_REDUCTION_SHARE_MIN = 0.25
P4_ACTION_REDUCTION_RECORDS_MIN = 20
P4_SELECTOR_RELEVANCE_MEAN_RANK_MIN = 5
P4_SELECTOR_RELEVANCE_RECORDS_MIN = 25

V1_P2_BASELINE_REACH_TOLERANCE = 3
V1_P2_DEPTH_REACH_TOLERANCE = 3
V1_P3_CONSTRAINED_REACH_TOLERANCE = 3

NO_GO_POOL_SIZE_MAX_MULTIPLIER = 4
NO_GO_LATENCY_MAX_MULTIPLIER = 2

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "fd1_artifact_read": False,
    "fd2a1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd2a1_artifact_modified": False,
    "bea_v1_p4_scheduler_smoke_performed": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "retrieval_policy_executed": False,
    "bea_v1_p4_audit_evaluator_no_provider_calls": True,
    "bea_v1_p4_audit_evaluator_no_selector_executed": True,
    "bea_v1_p4_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p4_audit_evaluator_no_role_proxy": True,
    "bea_v1_p4_audit_evaluator_latency_not_in_relevance": True,
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
    "algorithm_changed_during_bea_v1_p4": False,
    "weights_tuned_during_bea_v1_p4": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p4": False,
    "v1_a_selector_executed": False,
    "v1_a_coverage_preserving_selector_promoted": False,
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
    "new_records_added_during_bea_v1_p4": False,
    "heldout_validation_claimed": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_latency_aware_retrieval_scheduler_smoke",
}

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
    "retrieval_policy_failed",
    "baseline_reach_drift",
    "depth_reference_reach_drift",
    "p3_reference_reach_drift",
    "openlocus_binary_missing",
    "network_required_but_disabled",
    "scanner_self_test_failed", "forbidden_leak_blocked",
    "duplicate_record_key_blocked",
    "unexpected_exception",
)
BLOCKING_FAILURE_CATEGORIES = (
    "forbidden_leak_blocked", "unexpected_exception",
    "retrieval_policy_failed",
    "fd1_artifact_missing", "fd1_artifact_parse_failed",
)

# --- Scanner (composes P3 scanner; adds P4-specific rejections) ---

V1_P4_FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        "private_trace_dir", "trace_dir", "private_score_dir",
        "private_audit_dir", "audit_trace_path",
        "private_decomposition_dir", "private_reach_dir",
        "private_policy_dir", "policy_trace_dir",
        "private_scheduler_dir", "scheduler_trace_dir",
        "private_decomposition_path", "private_decomposition_file",
        "private_reach_path", "private_reach_file",
        "private_policy_path", "private_policy_file",
        "private_scheduler_path", "private_scheduler_file",
        "retrieval_trace_path", "candidate_trace_path",
        "policy_trace_path", "scheduler_trace_path",
        "per_record_reach", "per_record_candidates",
        "per_record_policy", "per_record_diagnostics",
        "per_record_actions", "per_record_stop_reason",
        "per_record_scheduler", "per_record_channel_actions",
        "per_record_query_variants", "per_record_gold_match",
        "per_record_pool_size", "per_record_latency",
        "per_record_ranks", "record_reach_detail",
        "record_policy_detail", "record_diagnostics_detail",
        "record_scheduler_detail", "record_channel_actions_detail",
        "record_candidate_lists", "record_query_variants",
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
        "objective_config_payload", "fd1_category_weights_payload",
        "weight_derivation_payload", "frozen_weights_payload",
        "policy_config_payload", "policy_thresholds_payload",
        "scheduler_config_payload", "scheduler_thresholds_payload",
        "raw_score_row", "raw_decision_row",
        "raw_feature_row", "raw_decomposition_row",
        "raw_reach_row", "raw_candidate_row",
        "raw_policy_row", "raw_diagnostics_row",
        "raw_scheduler_row", "raw_channel_action_row",
        "fd1_source_artifact_path", "fd2a1_source_artifact_path",
        "fd2a_source_artifact_path", "v1_p1_source_artifact_path",
        "v1_p2_source_artifact_path", "v1_p3_source_artifact_path",
        "fd1_replay_artifact_path", "reach_results_path",
        "policy_results_path", "scheduler_results_path",
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion", "calibration",
        "method_winner", "best_method",
        "self_test_checks", "self_test_details", "self_test_list",
        "checks", "check_list",
        "hard_gates", "failure_category_counts",
        "arm_reach_counts", "arm_delta_counts",
        "arm_cost_counts", "policy_action_counts",
        "policy_stop_reason_counts", "efficiency_counts",
        "reach_bucket_counts", "rank_band_counts",
        "arm_action_counts", "channel_action_counts",
        "scheduler_stop_reason_counts", "latency_decomposition_counts",
        "stop_go_counts",
        "is_v04_repair", "is_fd2_b", "is_fd2_c", "is_p5",
        "is_v031_tuning", "is_v032_tuning", "is_b16k",
        "is_selector_phase", "is_acquisition_phase",
        "is_dense_quality_mixing", "is_graph_quality_mixing",
        "is_quiver_quality_mixing",
        "role_proxy", "role_proxy_assignment", "target_proxy",
        "support_proxy", "target_anchor", "target_support_pair",
        "role_proxy_used", "target_support_proxy_used",
    }
)

V1_P4_CONTAINER_KEYS = frozenset({
    "source_run_records", "denominator_records",
    "arm_reach_records", "arm_delta_records",
    "arm_cost_records", "arm_action_records",
    "channel_action_records", "scheduler_stop_reason_records",
    "latency_decomposition_records", "efficiency_records",
    "reach_bucket_records", "rank_band_records",
    "cost_safety_records", "stop_go_records",
    "gate_records", "private_manifest_records",
    "failure_category_count_records", "framing",
})


def _is_v1_p4_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in V1_P4_CONTAINER_KEYS


def _scan_v1_p4_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_v1_p4_schema_key_container(sub_path)
                if (key_str in V1_P4_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_v1_p4_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


V1_P4_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
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
        "failure_category", "stop_go_decision", "stop_go_reason",
        "tradeoff_axis", "tradeoff_class", "tradeoff_basis",
        "tradeoff_reason",
        "gate", "threshold_relation", "manifest_name",
        "fd1_source_schema_version", "fd1_source_artifact_hash",
        "fd1_source_status",
        "replay_artifact_manifest_hash",
        "replay_artifact_schema_version",
        "replay_artifact_manifest_schema_version",
        "replay_artifact_status",
        "v1_p1_result_checkpoint", "v1_p1_result_status",
        "v1_p2_result_checkpoint", "v1_p2_result_status",
        "v1_p2_ci_run_id",
        "v1_p3_result_checkpoint", "v1_p3_result_status",
        "v1_p3_ci_run_id",
        "arm_name", "arm_class", "reach_bucket", "rank_band",
        "cost_safety_axis", "cost_safety_class",
        "cost_axis", "cost_class",
        "scheduler_action", "scheduler_action_class",
        "channel_name", "channel_action", "channel_action_class",
        "channel_eligibility", "channel_selection_reason",
        "stop_reason", "stop_reason_class",
        "scheduler_stop_reason", "scheduler_stop_reason_class",
        "latency_axis", "latency_class",
        "efficiency_axis", "efficiency_class",
        "treatment_arm", "baseline_arm", "reference_arm",
        "fd1_overlap_policy", "fd1_source_overlap_policy",
        "excluded_prior_windows_policy",
        "config_hash",
    }
)


def _v1_p4_safe_value_path(path: str) -> bool:
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in V1_P4_SAFE_VALUE_PATH_LAST_KEYS


def _scan_v1_p4(obj: Any) -> list[dict[str, Any]]:
    violations = bea_v1_p3._scan_v1_p3(obj)
    violations.extend(_scan_v1_p4_forbidden_keys(obj))
    filtered: list[dict[str, Any]] = []
    for v in violations:
        path = v.get("path", "")
        cat = v.get("category", "")
        if (cat.startswith("forbidden_") and cat.endswith("_key")
                and _is_v1_p4_schema_key_container(path)):
            continue
        if cat in ("long_string", "hex_digest_value",
                   "forbidden_field_name_value",
                   "repo_slug_value",
                   "line_range_value") and _v1_p4_safe_value_path(path):
            continue
        filtered.append(v)
    return filtered


def _v1_p4_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p4(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_v1_p4_no_forbidden(obj: Any) -> None:
    scan = _v1_p4_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


# --- Helpers ---

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


# --- Natural keys for BEA-v1-P4 public record tables ---

def _srr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["source_ci_run_id"])


def _dnr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["benchmark"])


def _arr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"],)


def _adr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"],)


def _acr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"], rec["cost_axis"])


def _aar_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm_name"], rec["scheduler_action"])


def _car_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["channel_name"], rec["channel_action"])


def _ssr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["scheduler_stop_reason"],)


def _ldr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["latency_axis"],)


def _efr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["efficiency_axis"],)


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


# --- FD1 private decomposition delegation (reuse P3 / P2) ---

def _parse_private_decomposition_jsonl(
    path: Path | None,
) -> bea_v1_p1.ParsedPrivateDecomposition:
    return bea_v1_p3._parse_private_decomposition_jsonl(path)


def _compute_file_selector_lower_bound(
    pt: bea_v1_p1.ParsedPrivateDecomposition,
) -> None:
    bea_v1_p3._compute_file_selector_lower_bound(pt)


def _validate_fd1_replay_artifact(
    replay_artifact_path: Path | None,
    committed_fd1_manifest_hash: str,
) -> bea_v1_p1.Fd1ReplayArtifactValidation:
    return bea_v1_p3._validate_fd1_replay_artifact(
        replay_artifact_path, committed_fd1_manifest_hash)


def _load_committed_artifact(
    artifact_path: Path,
) -> tuple[dict[str, Any], str, str, str]:
    return bea_v1_p1._load_committed_artifact(artifact_path)


def _extract_denominator_from_private(
    pt: bea_v1_p1.ParsedPrivateDecomposition,
) -> list[bea_v1_p2.DenominatorRecord]:
    return bea_v1_p3._extract_denominator_from_private(pt)


# ---------------------------------------------------------------------------
# Runtime-clean per-channel scheduler diagnostics (public signals only)
# ---------------------------------------------------------------------------


class ChannelDiagnostics:
    """Runtime-clean diagnostics for ONE retrieval channel (in-memory).

    All fields are derived from the channel's candidate list and the
    public task text only. No gold / private labels, no post-hoc tuning.
    """

    def __init__(self, channel_name: str) -> None:
        self.channel_name: str = channel_name
        self.candidate_count: int = 0
        self.unique_file_count: int = 0
        self.duplicate_file_rate: float = 0.0
        self.score_mass: float = 0.0
        self.score_spread: float = 0.0
        self.elapsed_seconds: float = 0.0
        self.failed: bool = False
        self.empty: bool = True
        self.unique_files: set[str] = set()
        self.new_file_yield_vs_baseline: int = 0
        self.overlap_with_baseline: float = 0.0
        self.eligible_for_extra_depth: bool = False
        self.eligibility_reason: str = ""


def _compute_channel_diagnostics(
    channel_name: str,
    candidates: list[dict[str, Any]],
    latency_ms: int,
    error: str,
    baseline_union_files: set[str],
) -> ChannelDiagnostics:
    """Compute runtime-clean diagnostics for one channel."""
    d = ChannelDiagnostics(channel_name)
    d.elapsed_seconds = round(latency_ms / 1000.0, 6)
    d.failed = (error in {"retrieval_failed", "invalid_json"}
                or error.startswith("returncode_"))
    d.candidate_count = len(candidates)
    if not candidates or d.failed:
        d.empty = True
        d.eligible_for_extra_depth = False
        d.eligibility_reason = (
            "empty_or_failed" if (not candidates or d.failed)
            else "empty_pool")
        return d
    d.empty = False
    paths = [str(c.get("path", "") or "") for c in candidates]
    d.unique_files = set(p for p in paths if p)
    d.unique_file_count = len(d.unique_files)
    total = len(paths)
    d.duplicate_file_rate = round(
        (total - d.unique_file_count) / total, 6) if total > 0 else 0.0
    norm_scores = [
        float(c.get("normalized_score", 0.0) or 0.0) for c in candidates
        if isinstance(c.get("normalized_score"), (int, float))]
    d.score_mass = round(sum(norm_scores), 6) if norm_scores else 0.0
    d.score_spread = round(
        max(norm_scores) - min(norm_scores), 6) if norm_scores else 0.0
    if baseline_union_files:
        d.new_file_yield_vs_baseline = len(
            d.unique_files - baseline_union_files)
        d.overlap_with_baseline = round(
            len(d.unique_files & baseline_union_files)
            / len(d.unique_files), 6) if d.unique_file_count > 0 else 0.0
    return d


def _select_eligible_extra_depth_channels(
    channels: dict[str, ChannelDiagnostics],
) -> list[str]:
    """Select eligible extra-depth channels (predeclared policy, no
    gold / private labels, no post-hoc tuning, no threshold search).

    Eligibility:
      - non-empty AND not failed AND
      - unique_file_count < cap OR new_file_yield >= min share of
        baseline union AND
      - duplicate rate <= max AND
      - overlap with already-selected channels < max.

    Selection order (runtime-clean action ordering, NOT candidate
    ranking by latency): prefer cheapest (lowest elapsed) then
    high-yield (most new files). Cap at budget.
    """
    baseline_total_files = len({f for cd in channels.values()
                               for f in cd.unique_files})
    eligible: list[tuple[str, ChannelDiagnostics]] = []
    for name, d in channels.items():
        if d.empty or d.failed:
            continue
        if d.unique_file_count == 0:
            continue
        is_sparse = d.unique_file_count < P4_CHANNEL_UNIQUE_FILE_CAP
        contributes_new = d.new_file_yield_vs_baseline >= max(
            1, int(P4_CHANNEL_MIN_UNIQUE_SHARE * max(1, baseline_total_files)))
        if not (is_sparse or contributes_new):
            d.eligible_for_extra_depth = False
            d.eligibility_reason = "saturated_no_new_yield"
            continue
        if d.duplicate_file_rate > P4_CHANNEL_DUP_FILE_RATE_MAX:
            d.eligible_for_extra_depth = False
            d.eligibility_reason = "duplicate_heavy"
            continue
        d.eligible_for_extra_depth = True
        d.eligibility_reason = "eligible_sparse_or_new_yield"
        eligible.append((name, d))

    eligible.sort(key=lambda kv: (
        kv[1].elapsed_seconds, -kv[1].new_file_yield_vs_baseline))
    selected: list[str] = []
    selected_union: set[str] = set()
    for name, d in eligible:
        if len(selected) >= P4_EXTRA_DEPTH_CHANNEL_ACTION_BUDGET_MAX:
            break
        if selected_union:
            overlap = (len(d.unique_files & selected_union)
                       / len(d.unique_files)) if d.unique_files else 0.0
            if overlap >= P4_CHANNEL_OVERLAP_MAX:
                d.eligible_for_extra_depth = False
                d.eligibility_reason = "high_overlap_with_selected"
                continue
        selected.append(name)
        selected_union |= d.unique_files
    return selected


# ---------------------------------------------------------------------------
# Retrieval scheduler runner (latency-aware retrieval-action scheduler)
# ---------------------------------------------------------------------------


class SchedulerReachResult:
    """Per-arm reach result for one denominator record (in-memory only).

    Extends the P3 concept with P4 scheduler fields: per-channel
    actions, scheduler stop reason, latency decomposition, and whether
    the hard candidate cap was hit. All fields are private; only
    aggregate counts are published.
    """

    def __init__(self, arm_name: str, private_record_id: str) -> None:
        self.arm_name = arm_name
        self.private_record_id = private_record_id
        self.gold_file_available: bool = False
        self.first_gold_file_rank: int = 0
        self.candidate_pool_size: int = 0
        self.retrieval_latency_seconds: float = 0.0
        self.duplicate_file_count: int = 0
        self.gold_file_rank_band: str = "not_found"
        self.candidate_paths_private: list[str] = []
        self.query_variants_private: list[str] = []
        self.retrieval_error: bool = False
        self.scheduler_action: str = ""
        self.scheduler_stop_reason: str = ""
        self.hard_cap_hit: bool = False
        self.unique_file_cap_hit: bool = False
        self.extra_depth_actions_executed: int = 0
        self.extra_depth_channels_selected_private: list[str] = []
        self.baseline_unique_file_count: int = 0
        self.final_unique_file_count: int = 0
        self.baseline_latency_seconds: float = 0.0
        self.extra_depth_latency_seconds: float = 0.0
        self.channel_actions_private: list[dict[str, Any]] = []
        self.p3_action_count_reference: int = 0


def _reach_rank_band(rank: int) -> str:
    return bea_v1_p2._reach_rank_band(rank)


def _collect_baseline_per_channel(
    openlocus_bin: str,
    query: str,
    cwd: Path,
    methods: tuple[str, ...] = FIXED_METHODS,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int],
           dict[str, str], bool]:
    """Collect baseline candidates PER CHANNEL (depth=1) with timings.

    Returns ``(per_channel_candidates, per_channel_latency_ms,
    per_channel_error, any_retrieval_error)``. This caches / reuses
    baseline channel outputs so extra-depth does NOT rerun the same
    baseline work (the P3 design reran baseline work inside its extra
    round; P4 caches it).
    """
    per_channel_candidates: dict[str, list[dict[str, Any]]] = {}
    per_channel_latency_ms: dict[str, int] = {}
    per_channel_error: dict[str, str] = {}
    any_error = False
    limit = DEFAULT_RETRIEVAL_LIMIT
    for method in methods:
        cands, latency_ms, err = (
            bea_v1_p2._collect_method_candidates_limited(
                openlocus_bin, method, query, cwd, limit)
        )
        if (err in {"retrieval_failed", "invalid_json"}
                or err.startswith("returncode_")):
            any_error = True
        per_channel_candidates[method] = cands
        per_channel_latency_ms[method] = latency_ms
        per_channel_error[method] = err
    return (per_channel_candidates, per_channel_latency_ms,
            per_channel_error, any_error)


def _merge_baseline_pool(
    per_channel_candidates: dict[str, list[dict[str, Any]]],
    limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge per-channel baseline candidates + derive RRF + dedup."""
    all_candidates: list[dict[str, Any]] = []
    for cands in per_channel_candidates.values():
        all_candidates.extend(cands)
    rrf = bea_v1_p2._derive_rrf_candidates_from_candidates(
        all_candidates, limit)
    merged = all_candidates + rrf
    deduped = bea1._dedup_candidates(merged)
    return deduped, rrf


def _collect_extra_depth_channel(
    openlocus_bin: str,
    method: str,
    query: str,
    cwd: Path,
    depth_multiplier: int,
) -> tuple[list[dict[str, Any]], int, str]:
    """Collect extra-depth candidates for ONE selected channel."""
    limit = DEFAULT_RETRIEVAL_LIMIT * max(1, int(depth_multiplier))
    return bea_v1_p2._collect_method_candidates_limited(
        openlocus_bin, method, query, cwd, limit)


def _check_gold_file_reach(
    candidates: list[dict[str, Any]], gold_set: set[str],
) -> tuple[bool, int, str, int]:
    """Check gold-file reach in a candidate pool.

    Returns ``(gold_available, first_gold_rank, rank_band, dup_files)``.
    Gold paths are used ONLY to check reach, never to construct the pool.
    """
    pred_paths = [str(c.get("path", "") or "") for c in candidates]
    unique_files = set(pred_paths)
    dup_files = len(pred_paths) - len(unique_files)
    gold_available = False
    first_gold_rank = 0
    for idx, path in enumerate(pred_paths, start=1):
        if path in gold_set:
            gold_available = True
            first_gold_rank = idx
            break
    return (gold_available, first_gold_rank,
            _reach_rank_band(first_gold_rank), dup_files)


def _run_baseline_arm(
    *, openlocus_bin: str, repo_root: Path, query: str, gold_set: set[str],
) -> SchedulerReachResult:
    """Run the baseline arm (depth=1, no query anchors)."""
    rr = SchedulerReachResult(
        arm_name="current_bea_candidate_pool_replay",
        private_record_id="")
    rr.scheduler_action = "baseline_only"
    rr.scheduler_stop_reason = "baseline_arm"
    t0 = time.perf_counter()
    cands, latency_ms, _, err = bea_v1_p3._collect_all_method_candidates(
        openlocus_bin, query, repo_root, BASELINE_DEPTH_MULTIPLIER)
    rr.retrieval_error = err
    rr.candidate_pool_size = len(cands)
    (rr.gold_file_available, rr.first_gold_file_rank,
     rr.gold_file_rank_band, rr.duplicate_file_count) = (
        _check_gold_file_reach(cands, gold_set))
    rr.candidate_paths_private = [str(c.get("path", "") or "")
                                  for c in cands][:500]
    rr.query_variants_private = [query][:50]
    rr.retrieval_latency_seconds = round(latency_ms / 1000.0, 6)
    rr.final_unique_file_count = len(
        {p for p in rr.candidate_paths_private if p})
    rr.baseline_unique_file_count = rr.final_unique_file_count
    rr.baseline_latency_seconds = rr.retrieval_latency_seconds
    if rr.retrieval_error:
        rr.scheduler_stop_reason = "retrieval_failed"
    rr.retrieval_latency_seconds = rr.retrieval_latency_seconds or (
        time.perf_counter() - t0)
    return rr


def _run_depth_reference_arm(
    *, openlocus_bin: str, repo_root: Path, query: str, gold_set: set[str],
) -> SchedulerReachResult:
    """Run the P2 depth-only reference arm (depth=4, no query anchors)."""
    rr = SchedulerReachResult(
        arm_name="p2_depth_only_reference",
        private_record_id="")
    rr.scheduler_action = "depth_reference_only"
    rr.scheduler_stop_reason = "depth_reference_arm"
    t0 = time.perf_counter()
    cands, latency_ms, _, err = bea_v1_p3._collect_all_method_candidates(
        openlocus_bin, query, repo_root, DEPTH_REFERENCE_MULTIPLIER)
    rr.retrieval_error = err
    rr.candidate_pool_size = len(cands)
    (rr.gold_file_available, rr.first_gold_file_rank,
     rr.gold_file_rank_band, rr.duplicate_file_count) = (
        _check_gold_file_reach(cands, gold_set))
    rr.candidate_paths_private = [str(c.get("path", "") or "")
                                  for c in cands][:500]
    rr.query_variants_private = [query][:50]
    rr.retrieval_latency_seconds = round(latency_ms / 1000.0, 6)
    rr.final_unique_file_count = len(
        {p for p in rr.candidate_paths_private if p})
    rr.baseline_unique_file_count = rr.final_unique_file_count
    rr.baseline_latency_seconds = rr.retrieval_latency_seconds
    if rr.retrieval_error:
        rr.scheduler_stop_reason = "retrieval_failed"
    rr.retrieval_latency_seconds = rr.retrieval_latency_seconds or (
        time.perf_counter() - t0)
    return rr


def _run_p3_reference_arm(
    *, openlocus_bin: str, repo_root: Path, query: str, gold_set: set[str],
) -> SchedulerReachResult:
    """Run the exact P3 constrained policy arm as a failure reference.

    Delegates to P3's constrained policy runner, then maps the result
    into a P4 SchedulerReachResult. This arm reproduces P3's latency
    failure (~2.17x) so P4 can be compared against it.
    """
    p3_rr = bea_v1_p3._run_p3_constrained_policy_arm(
        openlocus_bin=openlocus_bin, repo_root=repo_root,
        query=query, gold_set=gold_set)
    rr = SchedulerReachResult(
        arm_name="p3_constrained_depth_policy_reference",
        private_record_id="")
    rr.scheduler_action = "p3_reference_replay"
    rr.scheduler_stop_reason = p3_rr.policy_stop_reason or "p3_reference"
    rr.retrieval_error = p3_rr.retrieval_error
    rr.candidate_pool_size = p3_rr.candidate_pool_size
    rr.gold_file_available = p3_rr.gold_file_available
    rr.first_gold_file_rank = p3_rr.first_gold_file_rank
    rr.gold_file_rank_band = p3_rr.gold_file_rank_band
    rr.duplicate_file_count = p3_rr.duplicate_file_count
    rr.candidate_paths_private = p3_rr.candidate_paths_private
    rr.query_variants_private = p3_rr.query_variants_private
    rr.retrieval_latency_seconds = p3_rr.retrieval_latency_seconds
    rr.final_unique_file_count = p3_rr.final_unique_file_count
    rr.baseline_unique_file_count = p3_rr.baseline_unique_file_count
    rr.baseline_latency_seconds = p3_rr.retrieval_latency_seconds
    # P3 ran ONE full extra-depth round across ALL channels (3 methods).
    rr.p3_action_count_reference = (3 if p3_rr.extra_depth_round_executed
                                    else 0)
    rr.extra_depth_actions_executed = rr.p3_action_count_reference
    rr.hard_cap_hit = p3_rr.hard_cap_hit
    rr.unique_file_cap_hit = p3_rr.unique_file_cap_hit
    return rr


def _run_p4_latency_aware_scheduler_arm(
    *, openlocus_bin: str, repo_root: Path, query: str, gold_set: set[str],
) -> SchedulerReachResult:
    """Run the P4 latency-aware retrieval-action scheduler for one record.

    Scheduler steps:
      1. Baseline round: collect bm25 / literal-regex / symbol at
         depth=1 PER CHANNEL (cached with timings); derive RRF.
      2. Compute runtime-clean per-channel diagnostics.
      3. Select eligible extra-depth channels (predeclared policy).
      4. Execute at most 1-2 extra-depth channel actions total (NOT all
         channels like P3). Reuse cached baseline; extra-depth only runs
         the SELECTED channels at depth=4.
      5. Merge baseline + NEW unique-file candidates from chosen
         extra-depth channels; cap candidates <=100, unique files <=80.
      6. Compute gold-file reach on the final merged + deduped + capped
         pool.

    No gold / private labels are used in scheduler / query construction.
    Latency is measured and used only to decide actions / stop and for
    cost gates, NOT to rank candidates.
    """
    rr = SchedulerReachResult(
        arm_name="p4_latency_aware_action_scheduler",
        private_record_id="")
    rr.scheduler_action = "baseline_only"
    rr.scheduler_stop_reason = "baseline_no_extra"
    t0 = time.perf_counter()

    # Round 1: baseline per-channel (cached).
    (per_channel_cands, per_channel_lat_ms, per_channel_err,
     base_err) = _collect_baseline_per_channel(
        openlocus_bin, query, repo_root)
    rr.retrieval_error = base_err
    baseline_cands, _rrf = _merge_baseline_pool(
        per_channel_cands, DEFAULT_RETRIEVAL_LIMIT)
    baseline_latency_ms = sum(per_channel_lat_ms.values())
    rr.baseline_latency_seconds = round(baseline_latency_ms / 1000.0, 6)

    baseline_union_files = {str(c.get("path", "") or "")
                            for c in baseline_cands if c.get("path")}
    rr.baseline_unique_file_count = len(baseline_union_files)

    per_channel_files = {
        method: {str(c.get("path", "") or "")
                 for c in per_channel_cands.get(method, []) if c.get("path")}
        for method in FIXED_METHODS
    }

    channels: dict[str, ChannelDiagnostics] = {}
    for method in FIXED_METHODS:
        other_channel_files = set().union(*[
            files for m, files in per_channel_files.items() if m != method
        ]) if len(per_channel_files) > 1 else set()
        channels[method] = _compute_channel_diagnostics(
            method, per_channel_cands.get(method, []),
            per_channel_lat_ms.get(method, 0),
            per_channel_err.get(method, ""),
            other_channel_files)

    for name, d in channels.items():
        rr.channel_actions_private.append({
            "channel_name": name,
            "phase": "baseline",
            "channel_action": "baseline_collected",
            "candidate_count": d.candidate_count,
            "unique_file_count": d.unique_file_count,
            "duplicate_file_rate": d.duplicate_file_rate,
            "elapsed_seconds": d.elapsed_seconds,
            "new_file_yield_vs_baseline": d.new_file_yield_vs_baseline,
            "overlap_with_baseline": d.overlap_with_baseline,
            "eligible_for_extra_depth": d.eligible_for_extra_depth,
            "eligibility_reason": d.eligibility_reason,
            "failed": d.failed,
        })

    selected_channels = _select_eligible_extra_depth_channels(channels)
    rr.extra_depth_channels_selected_private = list(selected_channels)

    final_cands: list[dict[str, Any]] = list(baseline_cands)
    extra_latency_ms = 0
    hard_cap_hit = False
    unique_file_cap_hit = False

    if selected_channels:
        seen_files = set(baseline_union_files)
        merged: list[dict[str, Any]] = list(baseline_cands)
        for method in selected_channels:
            extra_cands, ch_lat_ms, ch_err = _collect_extra_depth_channel(
                openlocus_bin, method, query, repo_root,
                DEPTH_REFERENCE_MULTIPLIER)
            if ch_err:
                rr.retrieval_error = True
            extra_latency_ms += ch_lat_ms
            ch_new_files = {str(c.get("path", "") or "")
                            for c in extra_cands if c.get("path")}
            ch_new = ch_new_files - seen_files
            if len(ch_new) >= P4_CHANNEL_MARGINAL_YIELD_MIN:
                rr.channel_actions_private.append({
                    "channel_name": method,
                    "phase": "extra_depth",
                    "channel_action": "extra_depth_executed",
                    "candidate_count": len(extra_cands),
                    "unique_file_count": len(ch_new_files),
                    "new_file_yield_vs_baseline": len(ch_new),
                    "elapsed_seconds": round(ch_lat_ms / 1000.0, 6),
                    "failed": bool(ch_err),
                })
                for c in extra_cands:
                    p = str(c.get("path", "") or "")
                    if p and p not in seen_files:
                        merged.append(c)
                        seen_files.add(p)
                    if len(merged) >= P4_HARD_CANDIDATE_CAP:
                        hard_cap_hit = True
                        break
                    if len(seen_files) >= P4_UNIQUE_FILE_CAP:
                        unique_file_cap_hit = True
                        break
                if hard_cap_hit or unique_file_cap_hit:
                    break
            else:
                rr.channel_actions_private.append({
                    "channel_name": method,
                    "phase": "extra_depth",
                    "channel_action": "extra_depth_skipped_low_yield",
                    "candidate_count": len(extra_cands),
                    "new_file_yield_vs_baseline": len(ch_new),
                    "elapsed_seconds": round(ch_lat_ms / 1000.0, 6),
                })
        final_cands = merged[:P4_HARD_CANDIDATE_CAP]
        rr.extra_depth_actions_executed = len(selected_channels)
        rr.scheduler_action = "extra_depth_selected"
        if hard_cap_hit:
            rr.scheduler_stop_reason = "hard_candidate_cap_reached"
        elif unique_file_cap_hit:
            rr.scheduler_stop_reason = "unique_file_cap_reached"
        else:
            rr.scheduler_stop_reason = "extra_depth_actions_executed"
    else:
        rr.scheduler_action = "baseline_only"
        rr.scheduler_stop_reason = "no_eligible_channels"

    rr.hard_cap_hit = hard_cap_hit
    rr.unique_file_cap_hit = unique_file_cap_hit
    rr.candidate_pool_size = len(final_cands)
    (rr.gold_file_available, rr.first_gold_file_rank,
     rr.gold_file_rank_band, rr.duplicate_file_count) = (
        _check_gold_file_reach(final_cands, gold_set))
    rr.candidate_paths_private = [str(c.get("path", "") or "")
                                  for c in final_cands][:500]
    rr.query_variants_private = [query][:50]
    rr.final_unique_file_count = len(
        {p for p in rr.candidate_paths_private if p})
    rr.extra_depth_latency_seconds = round(extra_latency_ms / 1000.0, 6)
    total_latency_ms = baseline_latency_ms + extra_latency_ms
    rr.retrieval_latency_seconds = round(total_latency_ms / 1000.0, 6)
    if rr.retrieval_error and not rr.scheduler_stop_reason:
        rr.scheduler_stop_reason = "retrieval_failed"
    rr.retrieval_latency_seconds = rr.retrieval_latency_seconds or (
        time.perf_counter() - t0)
    return rr


def _resolve_private_scheduler_dir() -> Path:
    """Return a /tmp-only private trace dir for BEA-v1-P4 scheduler rows."""
    raw = os.environ.get("OPENLOCUS_BEA_V1_P4_PRIVATE_SCHEDULER_DIR", "")
    base = Path(raw) if raw else Path(
        f"/tmp/openlocus_bea_v1_p4_scheduler_{os.getpid()}")
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private scheduler dir")
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


def _config_hash() -> str:
    """Stable hash of the P4 scheduler configuration (private; not uploaded)."""
    config = json.dumps({
        "hard_candidate_cap": P4_HARD_CANDIDATE_CAP,
        "unique_file_cap": P4_UNIQUE_FILE_CAP,
        "extra_depth_channel_action_budget_max":
            P4_EXTRA_DEPTH_CHANNEL_ACTION_BUDGET_MAX,
        "channel_marginal_yield_min": P4_CHANNEL_MARGINAL_YIELD_MIN,
        "channel_unique_file_cap": P4_CHANNEL_UNIQUE_FILE_CAP,
        "channel_min_unique_share": P4_CHANNEL_MIN_UNIQUE_SHARE,
        "channel_dup_file_rate_max": P4_CHANNEL_DUP_FILE_RATE_MAX,
        "channel_overlap_max": P4_CHANNEL_OVERLAP_MAX,
        "query_anchors_enabled": P4_QUERY_ANCHORS_ENABLED,
        "baseline_depth_multiplier": BASELINE_DEPTH_MULTIPLIER,
        "depth_reference_multiplier": DEPTH_REFERENCE_MULTIPLIER,
        "methods": list(FIXED_METHODS),
        "budget": FIXED_BUDGET,
    }, sort_keys=True)
    return hashlib.sha256(config.encode("utf-8")).hexdigest()

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
    v1_p2_result_checkpoint: str, v1_p2_result_status: str,
    v1_p2_ci_run_id: str,
    v1_p2_baseline_reach: int, v1_p2_depth_reach: int,
    v1_p2_depth_newly: int,
    v1_p3_result_checkpoint: str, v1_p3_result_status: str,
    v1_p3_ci_run_id: str,
    v1_p3_constrained_reach: int, v1_p3_constrained_newly: int,
    v1_p3_latency_mult: float,
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
    config_hash: str,
) -> list[dict[str, Any]]:
    """One source_run_records row describing the FD1 + P1 + P2 + P3 source."""
    del fd1_committed_manifest_hash
    return [{
        "source_phase": "BEA-v1-P3",
        "source_ci_run_id": V1_P3_CI_RUN_ID,
        "source_checkpoint": V1_P3_RESULT_CHECKPOINT,
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
        "v1_p2_result_checkpoint": v1_p2_result_checkpoint,
        "v1_p2_result_status": v1_p2_result_status,
        "v1_p2_ci_run_id": v1_p2_ci_run_id,
        "v1_p2_baseline_reach": v1_p2_baseline_reach,
        "v1_p2_depth_reach": v1_p2_depth_reach,
        "v1_p2_depth_newly": v1_p2_depth_newly,
        "v1_p3_result_checkpoint": v1_p3_result_checkpoint,
        "v1_p3_result_status": v1_p3_result_status,
        "v1_p3_ci_run_id": v1_p3_ci_run_id,
        "v1_p3_constrained_reach": v1_p3_constrained_reach,
        "v1_p3_constrained_newly": v1_p3_constrained_newly,
        "v1_p3_latency_mult": v1_p3_latency_mult,
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
        "config_hash": config_hash,
    }]


def _denominator_records(
    denominator: list[bea_v1_p2.DenominatorRecord],
) -> list[dict[str, Any]]:
    return bea_v1_p2._denominator_records(denominator)


def _arm_reach_records(
    arm_results: dict[str, list[SchedulerReachResult]],
    denominator_count: int,
) -> list[dict[str, Any]]:
    """Per-arm aggregate reach records over the denominator."""
    rows: list[dict[str, Any]] = []
    denom = denominator_count if denominator_count > 0 else 1
    for arm_name in POLICY_ARMS:
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
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-arm delta vs baseline (current_bea_candidate_pool_replay)."""
    rows: list[dict[str, Any]] = []
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_available = sum(1 for r in baseline if r.gold_file_available)
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    baseline_latency = (
        statistics.mean([r.retrieval_latency_seconds for r in baseline])
        if baseline else 0.0)
    for arm_name in POLICY_ARMS:
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


def _arm_cost_records(
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-arm cost records (pool size + latency multipliers + hard cap)."""
    rows: list[dict[str, Any]] = []
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    baseline_latency = (
        statistics.mean([r.retrieval_latency_seconds for r in baseline])
        if baseline else 0.0)
    for arm_name in POLICY_ARMS:
        results = arm_results.get(arm_name, [])
        if not results:
            rows.append({
                "arm_name": arm_name, "cost_axis": "pool_size_multiplier",
                "cost_class": "no_data", "value": 0.0,
                "threshold": float(NO_GO_POOL_SIZE_MAX_MULTIPLIER),
            })
            rows.append({
                "arm_name": arm_name, "cost_axis": "latency_multiplier",
                "cost_class": "no_data", "value": 0.0,
                "threshold": float(NO_GO_LATENCY_MAX_MULTIPLIER),
            })
            continue
        pool = statistics.mean([r.candidate_pool_size for r in results])
        latency = statistics.mean([r.retrieval_latency_seconds for r in results])
        pool_mult = pool / baseline_pool if baseline_pool > 0 else 0.0
        latency_mult = latency / baseline_latency if baseline_latency > 0 else 0.0
        rows.append({
            "arm_name": arm_name, "cost_axis": "pool_size_multiplier",
            "cost_class": (["ok"] if pool_mult <= NO_GO_POOL_SIZE_MAX_MULTIPLIER
                           else ["exceeded"])[0],
            "value": round(pool_mult, 6),
            "threshold": float(NO_GO_POOL_SIZE_MAX_MULTIPLIER),
        })
        rows.append({
            "arm_name": arm_name, "cost_axis": "latency_multiplier",
            "cost_class": (["ok"] if latency_mult <= NO_GO_LATENCY_MAX_MULTIPLIER
                           else ["exceeded"])[0],
            "value": round(latency_mult, 6),
            "threshold": float(NO_GO_LATENCY_MAX_MULTIPLIER),
        })
    p4_results = arm_results.get("p4_latency_aware_action_scheduler", [])
    hard_cap_violations = sum(1 for r in p4_results
                              if r.candidate_pool_size > P4_HARD_CANDIDATE_CAP)
    rows.append({
        "arm_name": "p4_latency_aware_action_scheduler",
        "cost_axis": "hard_cap_violation_count",
        "cost_class": (["ok"] if hard_cap_violations <= P4_HARD_CAP_VIOLATION_MAX
                       else ["exceeded"])[0],
        "value": float(hard_cap_violations),
        "threshold": float(P4_HARD_CAP_VIOLATION_MAX),
    })
    rows.sort(key=lambda r: (r["arm_name"], r["cost_axis"]))
    return rows


def _arm_action_records(
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-(arm, scheduler_action) count records (p4 arm only)."""
    rows: list[dict[str, Any]] = []
    p4_results = arm_results.get("p4_latency_aware_action_scheduler", [])
    action_counts: dict[str, int] = {}
    for r in p4_results:
        a = r.scheduler_action or "unknown"
        action_counts[a] = action_counts.get(a, 0) + 1
    all_actions = (
        "baseline_only", "extra_depth_selected",
    )
    for action in all_actions:
        rows.append({
            "arm_name": "p4_latency_aware_action_scheduler",
            "scheduler_action": action,
            "record_count": int(action_counts.get(action, 0)),
        })
    for action, cnt in sorted(action_counts.items()):
        if action not in all_actions:
            rows.append({
                "arm_name": "p4_latency_aware_action_scheduler",
                "scheduler_action": action,
                "record_count": int(cnt),
            })
    rows.sort(key=lambda r: (r["arm_name"], r["scheduler_action"]))
    return rows


def _channel_action_records(
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-(channel_name, channel_action) aggregate count records
    (p4 arm only)."""
    rows: list[dict[str, Any]] = []
    p4_results = arm_results.get("p4_latency_aware_action_scheduler", [])
    counts: dict[tuple[str, str], int] = {}
    for r in p4_results:
        for ca in r.channel_actions_private:
            key = (str(ca.get("channel_name", "")),
                   str(ca.get("channel_action", "")))
            counts[key] = counts.get(key, 0) + 1
    for method in FIXED_METHODS:
        for action in ("baseline_collected",):
            counts.setdefault((method, action), 0)
    for (channel, action), cnt in sorted(counts.items()):
        rows.append({
            "channel_name": channel,
            "channel_action": action,
            "record_count": int(cnt),
        })
    rows.sort(key=lambda r: (r["channel_name"], r["channel_action"]))
    return rows


def _scheduler_stop_reason_records(
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-scheduler-stop-reason count records (p4 arm only)."""
    rows: list[dict[str, Any]] = []
    p4_results = arm_results.get("p4_latency_aware_action_scheduler", [])
    stop_counts: dict[str, int] = {}
    for r in p4_results:
        s = r.scheduler_stop_reason or "unknown"
        stop_counts[s] = stop_counts.get(s, 0) + 1
    all_reasons = (
        "baseline_arm", "baseline_no_extra", "no_eligible_channels",
        "extra_depth_actions_executed", "hard_candidate_cap_reached",
        "unique_file_cap_reached", "retrieval_failed",
        "depth_reference_arm", "p3_reference",
    )
    for reason in all_reasons:
        rows.append({
            "scheduler_stop_reason": reason,
            "record_count": int(stop_counts.get(reason, 0)),
        })
    for reason, cnt in sorted(stop_counts.items()):
        if reason not in all_reasons:
            rows.append({
                "scheduler_stop_reason": reason,
                "record_count": int(cnt),
            })
    rows.sort(key=lambda r: r["scheduler_stop_reason"])
    return rows


def _latency_decomposition_records(
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-latency-axis records (p4 arm only): baseline vs extra-depth
    latency decomposition."""
    rows: list[dict[str, Any]] = []
    p4_results = arm_results.get("p4_latency_aware_action_scheduler", [])
    if not p4_results:
        rows.append({
            "latency_axis": "p4_baseline_latency_mean_seconds",
            "latency_class": "no_data", "value": 0.0,
        })
        rows.append({
            "latency_axis": "p4_extra_depth_latency_mean_seconds",
            "latency_class": "no_data", "value": 0.0,
        })
        rows.append({
            "latency_axis": "p4_extra_depth_latency_share",
            "latency_class": "no_data", "value": 0.0,
        })
        return rows
    baseline_lats = [r.baseline_latency_seconds for r in p4_results
                     if r.baseline_latency_seconds > 0]
    extra_lats = [r.extra_depth_latency_seconds for r in p4_results]
    total_lats = [r.retrieval_latency_seconds for r in p4_results
                  if r.retrieval_latency_seconds > 0]
    baseline_mean = statistics.mean(baseline_lats) if baseline_lats else 0.0
    extra_mean = statistics.mean(extra_lats) if extra_lats else 0.0
    total_mean = statistics.mean(total_lats) if total_lats else 0.0
    extra_share = round(extra_mean / total_mean, 6) if total_mean > 0 else 0.0
    rows.append({
        "latency_axis": "p4_baseline_latency_mean_seconds",
        "latency_class": "ok", "value": round(baseline_mean, 6),
    })
    rows.append({
        "latency_axis": "p4_extra_depth_latency_mean_seconds",
        "latency_class": "ok", "value": round(extra_mean, 6),
    })
    rows.append({
        "latency_axis": "p4_extra_depth_latency_share",
        "latency_class": "ok", "value": extra_share,
    })
    rows.sort(key=lambda r: r["latency_axis"])
    return rows


def _efficiency_records(
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-arm efficiency records (newly_reachable_per_added_candidate)."""
    rows: list[dict[str, Any]] = []
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    for arm_name in POLICY_ARMS:
        if arm_name == "current_bea_candidate_pool_replay":
            continue
        results = arm_results.get(arm_name, [])
        if not results or baseline_pool <= 0:
            rows.append({
                "efficiency_axis": f"{arm_name}_newly_per_added_candidate",
                "efficiency_class": "no_data", "value": 0.0,
                "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
                "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY,
                "p3_efficiency": V1_P3_EFFICIENCY,
            })
            continue
        pool = statistics.mean([r.candidate_pool_size for r in results])
        added = pool - baseline_pool
        baseline_rids = {r.private_record_id for r in baseline
                         if r.gold_file_available}
        newly = sum(1 for r in results
                    if r.gold_file_available
                    and r.private_record_id not in baseline_rids)
        eff = newly / added if added > 0 else 0.0
        rows.append({
            "efficiency_axis": f"{arm_name}_newly_per_added_candidate",
            "efficiency_class": "ok",
            "value": round(eff, 6),
            "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
            "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY,
            "p3_efficiency": V1_P3_EFFICIENCY,
        })
    rows.sort(key=lambda r: r["efficiency_axis"])
    return rows


def _reach_bucket_records(
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-(arm, reach_bucket) count records."""
    rows: list[dict[str, Any]] = []
    for arm_name in POLICY_ARMS:
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
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Per-(arm, rank_band) count records using the RANK_BANDS cutoffs."""
    rows: list[dict[str, Any]] = []
    band_labels = [f"rank_le_{b}" for b in RANK_BANDS] + ["rank_above_200", "not_found"]
    for arm_name in POLICY_ARMS:
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
    arm_results: dict[str, list[SchedulerReachResult]],
) -> list[dict[str, Any]]:
    """Cost-safety axis records for the P4 treatment arm.

    Reference arms are controls, not the treatment under test. Per-arm
    costs for ALL arms (including P2 and P3 references) are still
    recorded in ``arm_cost_records``.
    """
    rows: list[dict[str, Any]] = []
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    baseline_latency = (
        statistics.mean([r.retrieval_latency_seconds for r in baseline])
        if baseline else 0.0)
    max_pool_mult = 0.0
    max_latency_mult = 0.0
    for arm_name in POLICY_ARMS:
        if arm_name != "p4_latency_aware_action_scheduler":
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
        "cost_safety_class": (["ok"] if max_pool_mult <= NO_GO_POOL_SIZE_MAX_MULTIPLIER
                              else ["exceeded"])[0],
        "value": round(max_pool_mult, 6),
        "threshold": float(NO_GO_POOL_SIZE_MAX_MULTIPLIER),
    })
    rows.append({
        "cost_safety_axis": "max_latency_multiplier",
        "cost_safety_class": (["ok"] if max_latency_mult <= NO_GO_LATENCY_MAX_MULTIPLIER
                              else ["exceeded"])[0],
        "value": round(max_latency_mult, 6),
        "threshold": float(NO_GO_LATENCY_MAX_MULTIPLIER),
    })
    rows.sort(key=lambda r: r["cost_safety_axis"])
    return rows


def _stop_go_records(
    *, denominator_count: int,
    arm_results: dict[str, list[SchedulerReachResult]],
    pool_cost_exceeded: bool, latency_cost_exceeded: bool,
    hard_cap_violation_count: int,
    retrieval_policy_executed: bool,
    baseline_reach: int, depth_reference_reach: int,
    p3_reference_reach: int,
    baseline_reach_drift: bool, depth_reference_reach_drift: bool,
    p3_reference_reach_drift: bool,
    p3_reference_latency_mean: float,
) -> list[dict[str, Any]]:
    """One stop/go row describing the P4 latency-aware scheduler decision.

    Pass only if ALL research success gates hold:
      1. Reach preservation.
      2. Latency fix (<=2.0x AND < P3 by >=10%).
      3. Pool safety (pool <= 4x, hard cap violations=0).
      4. Efficiency / action improvement.
      5. Selector relevance remains.
    """
    if (not retrieval_policy_executed or denominator_count == 0
            or baseline_reach_drift or depth_reference_reach_drift
            or p3_reference_reach_drift):
        return [{
            "stop_go_decision": "no_go_p4_replay_mismatch",
            "stop_go_reason": (
                "retrieval_policy_not_executed_or_replay_drift_or_zero_denom"),
            "newly_reachable_count": 0,
            "availability_lift": 0.0,
            "pool_cost_exceeded": bool(pool_cost_exceeded),
            "latency_cost_exceeded": bool(latency_cost_exceeded),
            "hard_cap_violation_count": int(hard_cap_violation_count),
            "latency_fixed": False,
            "runtime_clean_scheduler_dominates": False,
            "selector_problem_remains": False,
            "reach_preservation_min": P4_REACH_PRESERVATION_NEWLY_MIN,
            "reach_preservation_depth_ratio": P4_REACH_PRESERVATION_DEPTH_RATIO,
            "latency_mult_max": P4_LATENCY_MULT_MAX,
            "latency_vs_p3_improvement_min": P4_LATENCY_VS_P3_IMPROVEMENT_MIN,
            "pool_mult_max": P4_POOL_MULT_MAX,
            "hard_cap_violation_max": P4_HARD_CAP_VIOLATION_MAX,
            "efficiency_vs_p3_ratio": P4_EFFICIENCY_VS_P3_RATIO,
            "action_reduction_share_min": P4_ACTION_REDUCTION_SHARE_MIN,
            "action_reduction_records_min": P4_ACTION_REDUCTION_RECORDS_MIN,
            "selector_relevance_mean_rank_min": P4_SELECTOR_RELEVANCE_MEAN_RANK_MIN,
            "selector_relevance_records_min": P4_SELECTOR_RELEVANCE_RECORDS_MIN,
            "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
            "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY,
            "p3_efficiency": V1_P3_EFFICIENCY,
            "baseline_reach_observed": int(baseline_reach),
            "depth_reference_reach_observed": int(depth_reference_reach),
            "p3_reference_reach_observed": int(p3_reference_reach),
            "baseline_reach_drift": bool(baseline_reach_drift),
            "depth_reference_reach_drift": bool(depth_reference_reach_drift),
            "p3_reference_reach_drift": bool(p3_reference_reach_drift),
        }]
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_rids = {r.private_record_id for r in baseline
                     if r.gold_file_available}
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    baseline_latency = (
        statistics.mean([r.retrieval_latency_seconds for r in baseline])
        if baseline else 0.0)
    p4_results = arm_results.get("p4_latency_aware_action_scheduler", [])
    p4_newly = sum(1 for r in p4_results
                   if r.gold_file_available
                   and r.private_record_id not in baseline_rids)
    p4_pool = (
        statistics.mean([r.candidate_pool_size for r in p4_results])
        if p4_results else 0.0)
    p4_latency = (
        statistics.mean([r.retrieval_latency_seconds for r in p4_results])
        if p4_results else 0.0)
    added = p4_pool - baseline_pool if baseline_pool > 0 else 0.0
    p4_efficiency = (p4_newly / added) if added > 0 else 0.0
    availability_lift = p4_newly / max(denominator_count, 1)
    p4_latency_mult = (p4_latency / baseline_latency
                       if baseline_latency > 0 else 0.0)
    latency_vs_p3_improvement = (
        (p3_reference_latency_mean - p4_latency) / p3_reference_latency_mean
        if p3_reference_latency_mean > 0 else 0.0)

    reach_preserved = (
        p4_newly >= P4_REACH_PRESERVATION_NEWLY_MIN
        or p4_newly >= P4_REACH_PRESERVATION_DEPTH_RATIO * V1_P2_DEPTH_NEWLY)
    latency_fixed = (
        p4_latency_mult <= P4_LATENCY_MULT_MAX
        and latency_vs_p3_improvement >= P4_LATENCY_VS_P3_IMPROVEMENT_MIN)
    cost_safe = (
        not pool_cost_exceeded
        and hard_cap_violation_count <= P4_HARD_CAP_VIOLATION_MAX)
    efficiency_ok = (
        p4_efficiency >= P4_EFFICIENCY_VS_P3_RATIO * V1_P3_EFFICIENCY
        or p4_efficiency > V1_P2_COMBINED_EFFICIENCY)
    p4_action_counts = [r.extra_depth_actions_executed for r in p4_results]
    p3_action_counts = [r.p3_action_count_reference for r in p4_results]
    records_with_fewer_actions = sum(
        1 for p4a, p3a in zip(p4_action_counts, p3_action_counts)
        if p4a < p3a)
    mean_p4_actions = statistics.mean(p4_action_counts) if p4_action_counts else 0.0
    mean_p3_actions = statistics.mean(p3_action_counts) if p3_action_counts else 0.0
    action_share_reduced = (
        (mean_p3_actions - mean_p4_actions) / mean_p3_actions
        if mean_p3_actions > 0 else 0.0)
    action_improvement = (
        action_share_reduced >= P4_ACTION_REDUCTION_SHARE_MIN
        or records_with_fewer_actions >= P4_ACTION_REDUCTION_RECORDS_MIN)
    p4_ranks = [r.first_gold_file_rank for r in p4_results
                if r.first_gold_file_rank > 0]
    rank_mean = statistics.mean(p4_ranks) if p4_ranks else 0.0
    records_above_budget = sum(
        1 for r in p4_results
        if r.first_gold_file_rank > FIXED_BUDGET)
    selector_problem_remains = (
        rank_mean > P4_SELECTOR_RELEVANCE_MEAN_RANK_MIN
        or records_above_budget >= P4_SELECTOR_RELEVANCE_RECORDS_MIN)
    runtime_clean_dominates = p4_newly > 0

    if not latency_fixed:
        decision = "no_go_p4_latency_not_fixed"
        reason = (
            f"latency_not_fixed; p4_latency_mult={p4_latency_mult:.6f}; "
            f"max={P4_LATENCY_MULT_MAX}; "
            f"latency_vs_p3_improvement={latency_vs_p3_improvement:.6f}; "
            f"min={P4_LATENCY_VS_P3_IMPROVEMENT_MIN}; "
            f"p4_latency={p4_latency:.6f}; p3_latency="
            f"{p3_reference_latency_mean:.6f}")
    elif not cost_safe:
        decision = "no_go_p4_cost_exceeded"
        reason = (
            f"pool_or_hard_cap_exceeded; "
            f"p4_newly={p4_newly}; pool_cost_exceeded={pool_cost_exceeded}; "
            f"hard_cap_violations={hard_cap_violation_count}")
    elif not reach_preserved:
        decision = "no_go_p4_reach_not_preserved"
        reason = (
            f"reach_not_preserved; p4_newly={p4_newly}; "
            f"min={P4_REACH_PRESERVATION_NEWLY_MIN}; "
            f"depth_ratio_target="
            f"{P4_REACH_PRESERVATION_DEPTH_RATIO * V1_P2_DEPTH_NEWLY:.2f}; "
            f"availability_lift={availability_lift:.6f}")
    elif not (efficiency_ok and action_improvement):
        decision = "no_go_p4_policy_degenerate"
        reason = (
            f"policy_degenerate; p4_eff={p4_efficiency:.6f}; "
            f"p3_eff={V1_P3_EFFICIENCY:.6f}; "
            f"efficiency_ok={efficiency_ok}; "
            f"action_share_reduced={action_share_reduced:.6f}; "
            f"records_with_fewer_actions={records_with_fewer_actions}; "
            f"action_improvement={action_improvement}")
    elif not runtime_clean_dominates:
        decision = "no_go_p4_policy_degenerate"
        reason = "no_runtime_clean_scheduler_dominance"
    elif not selector_problem_remains:
        decision = "no_go_p4_policy_degenerate"
        reason = (
            "scheduler_leaves_no_selector_problem; "
            "gold_reachable_but_rank_too_low_for_selector_value")
    else:
        decision = "bea_v1_p4_latency_aware_retrieval_scheduler_pass"
        reason = (
            f"latency_aware_scheduler_pass; p4_newly={p4_newly}; "
            f"availability_lift={availability_lift:.6f}; "
            f"p4_eff={p4_efficiency:.6f}; "
            f"p4_latency_mult={p4_latency_mult:.6f}; "
            f"latency_vs_p3_improvement={latency_vs_p3_improvement:.6f}; "
            f"records_with_fewer_actions={records_with_fewer_actions}; "
            f"selector_problem_remains=True")
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "newly_reachable_count": int(p4_newly),
        "availability_lift": round(availability_lift, 6),
        "pool_cost_exceeded": bool(pool_cost_exceeded),
        "latency_cost_exceeded": bool(latency_cost_exceeded),
        "hard_cap_violation_count": int(hard_cap_violation_count),
        "latency_fixed": bool(latency_fixed),
        "runtime_clean_scheduler_dominates": bool(runtime_clean_dominates),
        "selector_problem_remains": bool(selector_problem_remains),
        "reach_preservation_min": P4_REACH_PRESERVATION_NEWLY_MIN,
        "reach_preservation_depth_ratio": P4_REACH_PRESERVATION_DEPTH_RATIO,
        "latency_mult_max": P4_LATENCY_MULT_MAX,
        "latency_vs_p3_improvement_min": P4_LATENCY_VS_P3_IMPROVEMENT_MIN,
        "pool_mult_max": P4_POOL_MULT_MAX,
        "hard_cap_violation_max": P4_HARD_CAP_VIOLATION_MAX,
        "efficiency_vs_p3_ratio": P4_EFFICIENCY_VS_P3_RATIO,
        "action_reduction_share_min": P4_ACTION_REDUCTION_SHARE_MIN,
        "action_reduction_records_min": P4_ACTION_REDUCTION_RECORDS_MIN,
        "selector_relevance_mean_rank_min": P4_SELECTOR_RELEVANCE_MEAN_RANK_MIN,
        "selector_relevance_records_min": P4_SELECTOR_RELEVANCE_RECORDS_MIN,
        "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
        "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY,
        "p3_efficiency": V1_P3_EFFICIENCY,
        "p4_efficiency": round(p4_efficiency, 6),
        "p4_latency_multiplier": round(p4_latency_mult, 6),
        "latency_vs_p3_improvement": round(latency_vs_p3_improvement, 6),
        "p4_first_gold_rank_mean": round(rank_mean, 6),
        "p4_records_first_gold_rank_above_budget": int(records_above_budget),
        "p4_mean_extra_depth_actions": round(mean_p4_actions, 6),
        "p3_mean_extra_depth_actions": round(mean_p3_actions, 6),
        "p4_action_share_reduced": round(action_share_reduced, 6),
        "p4_records_with_fewer_actions": int(records_with_fewer_actions),
        "baseline_reach_observed": int(baseline_reach),
        "depth_reference_reach_observed": int(depth_reference_reach),
        "p3_reference_reach_observed": int(p3_reference_reach),
        "baseline_reach_drift": bool(baseline_reach_drift),
        "depth_reference_reach_drift": bool(depth_reference_reach_drift),
        "p3_reference_reach_drift": bool(p3_reference_reach_drift),
    }]


def _gate_records(
    *, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    denominator_count: int,
    fd1_private_decomposition_parsed: bool,
    replay_artifact_validated: bool,
    retrieval_policy_executed: bool,
    forbidden_scan_pass: bool,
    pool_cost_exceeded: bool,
    latency_cost_exceeded: bool,
    hard_cap_violation_count: int,
    blocking_failure_count: int,
    baseline_reach: int, depth_reference_reach: int,
    p3_reference_reach: int,
    private_reach_rows: int, expected_private_reach_rows: int,
) -> list[dict[str, Any]]:
    def _g(gate: str, value: float, relation: str, threshold: float,
           passed: bool) -> dict[str, Any]:
        return {
            "gate": gate, "value": round(float(value), 6),
            "threshold_relation": relation,
            "threshold_value": round(float(threshold), 6),
            "passed": bool(passed),
        }

    baseline_in_tol = abs(baseline_reach - V1_P2_BASELINE_REACH) <= V1_P2_BASELINE_REACH_TOLERANCE
    depth_in_tol = abs(depth_reference_reach - V1_P2_DEPTH_REACH) <= V1_P2_DEPTH_REACH_TOLERANCE
    p3_in_tol = abs(p3_reference_reach - V1_P3_CONSTRAINED_REACH) <= V1_P3_CONSTRAINED_REACH_TOLERANCE
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
        _g("retrieval_policy_executed",
           1.0 if retrieval_policy_executed else 0.0,
           "boolean", 1.0, retrieval_policy_executed),
        _g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0,
           "boolean", 1.0, forbidden_scan_pass),
        _g("pool_cost_exceeded",
           1.0 if pool_cost_exceeded else 0.0,
           "boolean_false", 0.0, not pool_cost_exceeded),
        _g("latency_cost_exceeded",
           1.0 if latency_cost_exceeded else 0.0,
           "boolean_false", 0.0, not latency_cost_exceeded),
        _g("hard_cap_violation_count",
           float(hard_cap_violation_count), "<=",
           float(P4_HARD_CAP_VIOLATION_MAX),
           hard_cap_violation_count <= P4_HARD_CAP_VIOLATION_MAX),
        _g("blocking_failure_count", float(blocking_failure_count), "==",
           0.0, blocking_failure_count == 0),
        _g("baseline_reach_reproduced", float(baseline_reach),
           "within_tolerance",
           float(V1_P2_BASELINE_REACH), baseline_in_tol),
        _g("depth_reference_reach_reproduced", float(depth_reference_reach),
           "within_tolerance",
           float(V1_P2_DEPTH_REACH), depth_in_tol),
        _g("p3_reference_reach_reproduced", float(p3_reference_reach),
           "within_tolerance",
           float(V1_P3_CONSTRAINED_REACH), p3_in_tol),
        _g("private_reach_rows", float(private_reach_rows), "==",
           float(expected_private_reach_rows),
           private_reach_rows == expected_private_reach_rows),
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
    retrieval_policy_executed: bool,
    pool_cost_exceeded: bool,
    latency_cost_exceeded: bool,
    hard_cap_violation_count: int,
    baseline_reach_drift: bool,
    depth_reference_reach_drift: bool,
    p3_reference_reach_drift: bool,
    stop_go_decision: str,
) -> str:
    if blocking_failure_count > 0:
        return "fail_schema_contract"
    if not audit_match:
        return "unavailable_with_reason"
    if (not fd1_private_decomposition_parsed
            or not replay_artifact_validated
            or denominator_count != EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR
            or baseline_reach_drift or depth_reference_reach_drift
            or p3_reference_reach_drift):
        return "no_go_p4_replay_mismatch"
    if not retrieval_policy_executed:
        return "no_go_p4_replay_mismatch"
    if stop_go_decision == "bea_v1_p4_latency_aware_retrieval_scheduler_pass":
        return "bea_v1_p4_latency_aware_retrieval_scheduler_pass"
    if stop_go_decision == "no_go_p4_cost_exceeded":
        return "no_go_p4_cost_exceeded"
    if stop_go_decision == "no_go_p4_latency_not_fixed":
        return "no_go_p4_latency_not_fixed"
    if stop_go_decision == "no_go_p4_reach_not_preserved":
        return "no_go_p4_reach_not_preserved"
    if stop_go_decision == "no_go_p4_policy_degenerate":
        return "no_go_p4_policy_degenerate"
    if stop_go_decision == "no_go_p4_replay_mismatch":
        return "no_go_p4_replay_mismatch"
    return "no_go_p4_policy_degenerate"

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
        v1_p2_result_checkpoint=V1_P2_RESULT_CHECKPOINT,
        v1_p2_result_status=V1_P2_RESULT_STATUS,
        v1_p2_ci_run_id=V1_P2_CI_RUN_ID,
        v1_p2_baseline_reach=V1_P2_BASELINE_REACH,
        v1_p2_depth_reach=V1_P2_DEPTH_REACH,
        v1_p2_depth_newly=V1_P2_DEPTH_NEWLY,
        v1_p3_result_checkpoint=V1_P3_RESULT_CHECKPOINT,
        v1_p3_result_status=V1_P3_RESULT_STATUS,
        v1_p3_ci_run_id=V1_P3_CI_RUN_ID,
        v1_p3_constrained_reach=V1_P3_CONSTRAINED_REACH,
        v1_p3_constrained_newly=V1_P3_CONSTRAINED_NEWLY,
        v1_p3_latency_mult=V1_P3_LATENCY_MULT,
        audit_match=False,
        audit_mismatch_reason=failure_reason_category,
        config_hash=_config_hash(),
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
        "policy_arms": list(POLICY_ARMS),
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
        "arm_cost_records": [],
        "arm_action_records": [],
        "channel_action_records": [],
        "scheduler_stop_reason_records": [],
        "latency_decomposition_records": [],
        "efficiency_records": [],
        "reach_bucket_records": [],
        "rank_band_records": [],
        "cost_safety_records": [],
        "stop_go_records": _stop_go_records(
            denominator_count=0, arm_results={},
            pool_cost_exceeded=False,
            latency_cost_exceeded=False,
            hard_cap_violation_count=0,
            retrieval_policy_executed=False,
            baseline_reach=0, depth_reference_reach=0,
            p3_reference_reach=0,
            baseline_reach_drift=False,
            depth_reference_reach_drift=False,
            p3_reference_reach_drift=False,
            p3_reference_latency_mean=V1_P3_LATENCY_MEAN,
        ),
        "gate_records": _gate_records(
            fd1_records_decomposed=0,
            fd1_private_manifest_record_count=0,
            denominator_count=0,
            fd1_private_decomposition_parsed=False,
            replay_artifact_validated=False,
            retrieval_policy_executed=False,
            forbidden_scan_pass=True,
            pool_cost_exceeded=False,
            latency_cost_exceeded=False,
            hard_cap_violation_count=0,
            blocking_failure_count=_blocking_failure_count(fcc),
            baseline_reach=0, depth_reference_reach=0,
            p3_reference_reach=0,
            private_reach_rows=0, expected_private_reach_rows=0,
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
                "bea_v1_p4_latency_aware_retrieval_scheduler_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
            "is_v04_repair": False,
            "is_fd2_b": False,
            "is_fd2_c": False,
            "is_p5": False,
            "is_v031_tuning": False,
            "is_v032_tuning": False,
            "is_b16k": False,
            "is_dense_quality_mixing": False,
            "is_graph_quality_mixing": False,
            "is_quiver_quality_mixing": False,
            "is_failure_attribution_only": False,
            "is_candidate_availability_reach_smoke": False,
            "is_constrained_retrieval_policy_smoke": False,
            "is_latency_aware_retrieval_scheduler_smoke": True,
            "is_latency_in_relevance": False,
        },
    }
    scan = _v1_p4_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_scheduler_report(
    *, self_test_passed: bool, self_test_checks_total: int,
    self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any],
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
    fd1_committed_manifest_hash: str,
    pt: bea_v1_p1.ParsedPrivateDecomposition | None,
    rav: bea_v1_p1.Fd1ReplayArtifactValidation | None,
    denominator: list[bea_v1_p2.DenominatorRecord],
    arm_results: dict[str, list[SchedulerReachResult]],
    retrieval_policy_executed: bool,
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

    cost_safety = _cost_safety_records(arm_results)
    pool_cost_exceeded = any(
        r.get("cost_safety_class") == "exceeded"
        and r.get("cost_safety_axis") == "max_pool_size_multiplier"
        for r in cost_safety)
    latency_cost_exceeded = any(
        r.get("cost_safety_class") == "exceeded"
        and r.get("cost_safety_axis") == "max_latency_multiplier"
        for r in cost_safety)
    p4_results = arm_results.get("p4_latency_aware_action_scheduler", [])
    hard_cap_violation_count = sum(
        1 for r in p4_results
        if r.candidate_pool_size > P4_HARD_CANDIDATE_CAP)

    baseline_results = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_reach = sum(1 for r in baseline_results if r.gold_file_available)
    depth_ref_results = arm_results.get("p2_depth_only_reference", [])
    depth_reference_reach = sum(
        1 for r in depth_ref_results if r.gold_file_available)
    p3_ref_results = arm_results.get("p3_constrained_depth_policy_reference", [])
    p3_reference_reach = sum(
        1 for r in p3_ref_results if r.gold_file_available)
    p3_ref_latencies = [r.retrieval_latency_seconds for r in p3_ref_results]
    p3_reference_latency_mean = (
        statistics.mean(p3_ref_latencies) if p3_ref_latencies
        else V1_P3_LATENCY_MEAN)
    baseline_reach_drift = (
        retrieval_policy_executed
        and abs(baseline_reach - V1_P2_BASELINE_REACH)
        > V1_P2_BASELINE_REACH_TOLERANCE)
    depth_reference_reach_drift = (
        retrieval_policy_executed
        and abs(depth_reference_reach - V1_P2_DEPTH_REACH)
        > V1_P2_DEPTH_REACH_TOLERANCE)
    p3_reference_reach_drift = (
        retrieval_policy_executed
        and abs(p3_reference_reach - V1_P3_CONSTRAINED_REACH)
        > V1_P3_CONSTRAINED_REACH_TOLERANCE)
    if baseline_reach_drift:
        fcc["baseline_reach_drift"] = max(fcc.get("baseline_reach_drift", 0), 1)
    if depth_reference_reach_drift:
        fcc["depth_reference_reach_drift"] = max(
            fcc.get("depth_reference_reach_drift", 0), 1)
    if p3_reference_reach_drift:
        fcc["p3_reference_reach_drift"] = max(
            fcc.get("p3_reference_reach_drift", 0), 1)

    stop_go = _stop_go_records(
        denominator_count=denominator_count,
        arm_results=arm_results,
        pool_cost_exceeded=pool_cost_exceeded,
        latency_cost_exceeded=latency_cost_exceeded,
        hard_cap_violation_count=hard_cap_violation_count,
        retrieval_policy_executed=retrieval_policy_executed,
        baseline_reach=baseline_reach,
        depth_reference_reach=depth_reference_reach,
        p3_reference_reach=p3_reference_reach,
        baseline_reach_drift=baseline_reach_drift,
        depth_reference_reach_drift=depth_reference_reach_drift,
        p3_reference_reach_drift=p3_reference_reach_drift,
        p3_reference_latency_mean=p3_reference_latency_mean,
    )

    blocking_failure_count = _blocking_failure_count(fcc)

    status = _decide_status(
        audit_match=audit_match,
        blocking_failure_count=blocking_failure_count,
        fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
        replay_artifact_validated=replay_artifact_validated,
        denominator_count=denominator_count,
        retrieval_policy_executed=retrieval_policy_executed,
        pool_cost_exceeded=pool_cost_exceeded,
        latency_cost_exceeded=latency_cost_exceeded,
        hard_cap_violation_count=hard_cap_violation_count,
        baseline_reach_drift=baseline_reach_drift,
        depth_reference_reach_drift=depth_reference_reach_drift,
        p3_reference_reach_drift=p3_reference_reach_drift,
        stop_go_decision=stop_go[0]["stop_go_decision"] if stop_go else "",
    )

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["fd1_artifact_read"] = True
    safe_true["bea_v1_p4_scheduler_smoke_performed"] = retrieval_policy_executed
    safe_true["fd1_private_decomposition_parsed"] = bool(
        fd1_private_decomposition_parsed)
    safe_true["retrieval_policy_executed"] = bool(retrieval_policy_executed)
    if rav is not None:
        safe_true["fd1_private_decomposition_replay_supplied"] = bool(
            rav.supplied)
        safe_true["fd1_private_decomposition_replay_validated"] = bool(
            rav.validated)
        safe_true[
            "fd1_private_decomposition_replay_executed_by_workflow"] = bool(
            rav.supplied and rav.validated)

    expected_private_reach_rows = denominator_count * len(POLICY_ARMS)
    private_reach_rows = sum(
        len(arm_results.get(a, [])) for a in POLICY_ARMS)

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
        v1_p2_result_checkpoint=V1_P2_RESULT_CHECKPOINT,
        v1_p2_result_status=V1_P2_RESULT_STATUS,
        v1_p2_ci_run_id=V1_P2_CI_RUN_ID,
        v1_p2_baseline_reach=V1_P2_BASELINE_REACH,
        v1_p2_depth_reach=V1_P2_DEPTH_REACH,
        v1_p2_depth_newly=V1_P2_DEPTH_NEWLY,
        v1_p3_result_checkpoint=V1_P3_RESULT_CHECKPOINT,
        v1_p3_result_status=V1_P3_RESULT_STATUS,
        v1_p3_ci_run_id=V1_P3_CI_RUN_ID,
        v1_p3_constrained_reach=V1_P3_CONSTRAINED_REACH,
        v1_p3_constrained_newly=V1_P3_CONSTRAINED_NEWLY,
        v1_p3_latency_mult=V1_P3_LATENCY_MULT,
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
        config_hash=_config_hash(),
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
        "policy_arms": list(POLICY_ARMS),
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
        "arm_cost_records": _arm_cost_records(arm_results),
        "arm_action_records": _arm_action_records(arm_results),
        "channel_action_records": _channel_action_records(arm_results),
        "scheduler_stop_reason_records": _scheduler_stop_reason_records(
            arm_results),
        "latency_decomposition_records": _latency_decomposition_records(
            arm_results),
        "efficiency_records": _efficiency_records(arm_results),
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
            retrieval_policy_executed=retrieval_policy_executed,
            forbidden_scan_pass=True,
            pool_cost_exceeded=pool_cost_exceeded,
            latency_cost_exceeded=latency_cost_exceeded,
            hard_cap_violation_count=hard_cap_violation_count,
            blocking_failure_count=blocking_failure_count,
            baseline_reach=baseline_reach,
            depth_reference_reach=depth_reference_reach,
            p3_reference_reach=p3_reference_reach,
            private_reach_rows=private_reach_rows,
            expected_private_reach_rows=expected_private_reach_rows,
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
                "bea_v1_p4_latency_aware_retrieval_scheduler_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
            "is_v04_repair": False,
            "is_fd2_b": False,
            "is_fd2_c": False,
            "is_p5": False,
            "is_v031_tuning": False,
            "is_v032_tuning": False,
            "is_b16k": False,
            "is_dense_quality_mixing": False,
            "is_graph_quality_mixing": False,
            "is_quiver_quality_mixing": False,
            "is_failure_attribution_only": False,
            "is_candidate_availability_reach_smoke": False,
            "is_constrained_retrieval_policy_smoke": False,
            "is_latency_aware_retrieval_scheduler_smoke": True,
            "is_latency_in_relevance": False,
        },
    }
    scan = _v1_p4_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Real scheduler runner (network + openlocus + FD1 private replay)
# ---------------------------------------------------------------------------


def _fd1_private_decomposition_parsed_check(
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


def _run_scheduler_smoke(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    fd1_artifact_path: Path,
    fd1_private_decomposition_jsonl: Path | None,
    fd1_replay_artifact: Path | None,
    enable_network: bool,
) -> dict[str, Any]:
    """Run the full P4 scheduler smoke: validate FD1 replay, extract
    denominator, rerun the latency-aware retrieval scheduler on
    denominator records, build the public report. No provider calls.
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

    committed_manifest_hash = str(
        fd1_manifest.get("manifest_hash", "") or "")
    rav = _validate_fd1_replay_artifact(
        fd1_replay_artifact, committed_manifest_hash)
    if rav.supplied and rav.failure_category:
        fcc[rav.failure_category] = max(fcc.get(rav.failure_category, 0), 1)

    denominator: list[bea_v1_p2.DenominatorRecord] = []
    if pt is not None and pt.computed:
        denominator = _extract_denominator_from_private(pt)
    if len(denominator) != EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR:
        fcc["denominator_mismatch"] = 1
        if len(denominator) != 0:
            fcc["denominator_mapping_failed"] = 1

    arm_results: dict[str, list[SchedulerReachResult]] = {
        arm: [] for arm in POLICY_ARMS}
    private_scheduler_manifest: dict[str, Any] | None = None
    retrieval_policy_executed = False
    if (enable_network and audit_match
            and _fd1_private_decomposition_parsed_check(pt, rav)
            and len(denominator) == EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR):
        try:
            arm_results, scheduler_fcc, private_scheduler_manifest = (
                _execute_retrieval_scheduler(
                    openlocus_bin=openlocus_bin,
                    denominator=denominator,
                ))
            for k, v in scheduler_fcc.items():
                if k in fcc:
                    fcc[k] += v
            retrieval_policy_executed = True
        except Exception:
            fcc["retrieval_policy_failed"] = 1
            fcc["unexpected_exception"] = 1
    elif not enable_network:
        fcc["network_required_but_disabled"] = 1

    aggregate_runtime_seconds = time.perf_counter() - start

    return _build_scheduler_report(
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
            [private_scheduler_manifest] if private_scheduler_manifest is not None
            else []
        ),
        retrieval_policy_executed=retrieval_policy_executed,
        audit_match=audit_match,
        audit_mismatch_reason=audit_mismatch_reason,
        failure_category_counts=fcc,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
    )


def _execute_retrieval_scheduler(
    *, openlocus_bin: str,
    denominator: list[bea_v1_p2.DenominatorRecord],
) -> tuple[dict[str, list[SchedulerReachResult]], dict[str, int], dict[str, Any]]:
    """Execute the latency-aware retrieval scheduler on denominator records.

    Fetches the source benchmark rows, clones repos, and runs the 4
    scheduler arms. Returns ``(arm_results, fcc, scheduler_manifest)``.
    No provider calls.
    """
    fcc: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    arm_results: dict[str, list[SchedulerReachResult]] = {
        arm: [] for arm in POLICY_ARMS}
    scheduler_manifest: dict[str, Any] = {
        "manifest_name": "bea_v1_p4_private_scheduler_manifest",
        "schema_version": "bea_v1_p4_private_scheduler.v1",
        "storage_class": "private_tmp_only",
        "record_count": 0,
        "records_written": False,
        "path_publicly_serialized": False,
        "manifest_hash": "",
    }
    try:
        private_scheduler_dir = _resolve_private_scheduler_dir()
        private_scheduler_path = (
            private_scheduler_dir / "bea_v1_p4.private_scheduler.jsonl")
        if private_scheduler_path.exists():
            private_scheduler_path.unlink()
    except Exception:
        private_scheduler_path = None
        fcc["retrieval_policy_failed"] += 1

    by_phase_bench: dict[tuple[str, str], list[bea_v1_p2.DenominatorRecord]] = {}
    for d in denominator:
        key = (d.source_phase, d.benchmark)
        by_phase_bench.setdefault(key, []).append(d)

    for (sp, bm), denom_records in by_phase_bench.items():
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

        for d in denom_records:
            idx = d.record_index
            if idx >= len(rows):
                fcc["denominator_mapping_failed"] += 1
                continue
            row = rows[idx]
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
                    row.get("needle_path", row.get("path", "")) or "")
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

            with tempfile.TemporaryDirectory(prefix=f"v1p4_{bm}_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(
                    repo_url, base_commit, rwd)
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    continue
                repo_root = rwd / "repo"
                gold_set = {str(p) for p in gold_paths if p}

                rr_base = _run_baseline_arm(
                    openlocus_bin=openlocus_bin, repo_root=repo_root,
                    query=query, gold_set=gold_set)
                rr_base.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                arm_results["current_bea_candidate_pool_replay"].append(rr_base)
                rr_depth = _run_depth_reference_arm(
                    openlocus_bin=openlocus_bin, repo_root=repo_root,
                    query=query, gold_set=gold_set)
                rr_depth.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                arm_results["p2_depth_only_reference"].append(rr_depth)
                rr_p3 = _run_p3_reference_arm(
                    openlocus_bin=openlocus_bin, repo_root=repo_root,
                    query=query, gold_set=gold_set)
                rr_p3.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                arm_results["p3_constrained_depth_policy_reference"].append(rr_p3)
                rr_p4 = _run_p4_latency_aware_scheduler_arm(
                    openlocus_bin=openlocus_bin, repo_root=repo_root,
                    query=query, gold_set=gold_set)
                rr_p4.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                # P4 action count reference: P3 ran 3 channel actions if
                # it triggered extra depth; P4 ran fewer if it selected
                # fewer channels.
                rr_p4.p3_action_count_reference = rr_p3.p3_action_count_reference
                arm_results["p4_latency_aware_action_scheduler"].append(rr_p4)

                if private_scheduler_path is not None:
                    for rr in (rr_base, rr_depth, rr_p3, rr_p4):
                        try:
                            _append_private_jsonl(private_scheduler_path, {
                                "schema_version":
                                    "bea_v1_p4_private_scheduler.v1",
                                "source_phase": d.source_phase,
                                "benchmark": d.benchmark,
                                "private_record_id": d.private_record_id,
                                "arm_name": rr.arm_name,
                                "gold_file_available": rr.gold_file_available,
                                "first_gold_file_rank": rr.first_gold_file_rank,
                                "gold_file_rank_band": rr.gold_file_rank_band,
                                "candidate_pool_size": rr.candidate_pool_size,
                                "duplicate_file_count": rr.duplicate_file_count,
                                "retrieval_latency_seconds": round(
                                    rr.retrieval_latency_seconds, 6),
                                "candidate_paths_private":
                                    rr.candidate_paths_private,
                                "query_private": query[:200],
                                "scheduler_action": rr.scheduler_action,
                                "scheduler_stop_reason": rr.scheduler_stop_reason,
                                "hard_cap_hit": rr.hard_cap_hit,
                                "unique_file_cap_hit": rr.unique_file_cap_hit,
                                "extra_depth_actions_executed":
                                    rr.extra_depth_actions_executed,
                                "baseline_unique_file_count":
                                    rr.baseline_unique_file_count,
                                "final_unique_file_count":
                                    rr.final_unique_file_count,
                                "baseline_latency_seconds":
                                    rr.baseline_latency_seconds,
                                "extra_depth_latency_seconds":
                                    rr.extra_depth_latency_seconds,
                                "channel_actions_private":
                                    rr.channel_actions_private if rr.arm_name == "p4_latency_aware_action_scheduler" else [],
                                "p3_action_count_reference":
                                    rr.p3_action_count_reference,
                                "config_hash": _config_hash(),
                            })
                        except Exception:
                            fcc["retrieval_policy_failed"] += 1
                    for rr in (rr_base, rr_depth, rr_p3, rr_p4):
                        if rr.retrieval_error:
                            fcc["retrieval_policy_failed"] += 1

    if private_scheduler_path is not None:
        scheduler_manifest = _private_file_manifest(
            private_scheduler_path,
            manifest_name="bea_v1_p4_private_scheduler_manifest",
            schema_version="bea_v1_p4_private_scheduler.v1",
        )
    return arm_results, fcc, scheduler_manifest


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
    """Delegate to P3's synthetic private decomposition JSONL builder."""
    return bea_v1_p3._build_synthetic_private_decomposition_jsonl(
        path,
        gold_file_absent_count=gold_file_absent_count,
        recoverable_lower_bound=recoverable_lower_bound,
    )


def _build_synthetic_scheduler_results(
    denominator_count: int = EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR,
    baseline_available: int = V1_P2_BASELINE_REACH,
    depth_available: int = V1_P2_DEPTH_REACH,
    p3_available: int = V1_P3_CONSTRAINED_REACH,
    p4_available: int = V1_P3_CONSTRAINED_REACH,
    p4_latency: float = 2.0,
    p4_pool: int = 35,
) -> dict[str, list[SchedulerReachResult]]:
    """Build synthetic scheduler results for self-test.

    Baseline reaches 32. Depth reference reaches 59. P3 reference
    reaches 58 with P3 latency (3.645s). P4 latency-aware scheduler
    reaches 58 (preserves P3 reach) with reduced latency (2.0s, <
    P3 by >10%) and bounded pool (35, < 4x baseline 20).
    """
    arm_results: dict[str, list[SchedulerReachResult]] = {
        arm: [] for arm in POLICY_ARMS}
    for i in range(denominator_count):
        rid = f"contextbench-{i}"
        rr_base = SchedulerReachResult(
            arm_name="current_bea_candidate_pool_replay",
            private_record_id=rid)
        rr_base.candidate_pool_size = 20
        rr_base.retrieval_latency_seconds = 1.8
        rr_base.baseline_latency_seconds = 1.8
        rr_base.scheduler_action = "baseline_only"
        rr_base.scheduler_stop_reason = "baseline_arm"
        rr_base.baseline_unique_file_count = 13
        rr_base.final_unique_file_count = 13
        if i < baseline_available:
            rr_base.gold_file_available = True
            rr_base.first_gold_file_rank = 12
            rr_base.gold_file_rank_band = _reach_rank_band(12)
        arm_results["current_bea_candidate_pool_replay"].append(rr_base)
        rr_depth = SchedulerReachResult(
            arm_name="p2_depth_only_reference",
            private_record_id=rid)
        rr_depth.candidate_pool_size = 68
        rr_depth.retrieval_latency_seconds = 2.12
        rr_depth.baseline_latency_seconds = 2.12
        rr_depth.scheduler_action = "depth_reference_only"
        rr_depth.scheduler_stop_reason = "depth_reference_arm"
        rr_depth.baseline_unique_file_count = 44
        rr_depth.final_unique_file_count = 44
        if i < depth_available:
            rr_depth.gold_file_available = True
            rr_depth.first_gold_file_rank = 27
            rr_depth.gold_file_rank_band = _reach_rank_band(27)
        arm_results["p2_depth_only_reference"].append(rr_depth)
        rr_p3 = SchedulerReachResult(
            arm_name="p3_constrained_depth_policy_reference",
            private_record_id=rid)
        rr_p3.candidate_pool_size = 41
        rr_p3.retrieval_latency_seconds = V1_P3_LATENCY_MEAN
        rr_p3.baseline_latency_seconds = V1_P3_LATENCY_MEAN
        rr_p3.scheduler_action = "p3_reference_replay"
        rr_p3.scheduler_stop_reason = "extra_depth_round_executed"
        rr_p3.extra_depth_actions_executed = 3
        rr_p3.p3_action_count_reference = 3
        rr_p3.baseline_unique_file_count = 13
        rr_p3.final_unique_file_count = 28
        if i < p3_available:
            rr_p3.gold_file_available = True
            rr_p3.first_gold_file_rank = 21
            rr_p3.gold_file_rank_band = _reach_rank_band(21)
        arm_results["p3_constrained_depth_policy_reference"].append(rr_p3)
        rr_p4 = SchedulerReachResult(
            arm_name="p4_latency_aware_action_scheduler",
            private_record_id=rid)
        rr_p4.candidate_pool_size = p4_pool
        rr_p4.retrieval_latency_seconds = p4_latency
        rr_p4.baseline_latency_seconds = 1.8
        rr_p4.extra_depth_latency_seconds = round(p4_latency - 1.8, 6)
        rr_p4.scheduler_action = "extra_depth_selected"
        rr_p4.scheduler_stop_reason = "extra_depth_actions_executed"
        rr_p4.extra_depth_actions_executed = 1
        rr_p4.p3_action_count_reference = 3
        rr_p4.baseline_unique_file_count = 13
        rr_p4.final_unique_file_count = 25
        if i < p4_available:
            rr_p4.gold_file_available = True
            rr_p4.first_gold_file_rank = 18
            rr_p4.gold_file_rank_band = _reach_rank_band(18)
        arm_results["p4_latency_aware_action_scheduler"].append(rr_p4)
    return arm_results


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic FD1 + synthetic scheduler results)
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
                 "bea_v1_p4_audit_evaluator_no_provider_calls",
                 "bea_v1_p4_audit_evaluator_no_selector_executed",
                 "bea_v1_p4_audit_evaluator_no_weight_tuning",
                 "bea_v1_p4_audit_evaluator_no_role_proxy",
                 "bea_v1_p4_audit_evaluator_latency_not_in_relevance"):
        checks.append(_check(f"safe_true_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is True))
    for flag in ("fd1_private_decomposition_parsed",
                 "fd1_private_decomposition_replay_supplied",
                 "fd1_private_decomposition_replay_validated",
                 "fd1_private_decomposition_replay_executed_by_workflow",
                 "retrieval_policy_executed",
                 "bea_v1_p4_scheduler_smoke_performed"):
        checks.append(_check(f"safe_false_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is False))
    for flag in ("role_proxy_assigned",
                 "gold_labels_used_for_query_construction",
                 "gold_labels_used_for_selection",
                 "gold_labels_used_for_policy",
                 "latency_in_candidate_relevance",
                 "query_anchors_used_in_p4_arm",
                 "v1_a_selector_executed",
                 "v04_full_matrix_claimed",
                 "fd2b_executed", "fd2c_executed",
                 "legacy_role_proxy_p4_executed",
                 "p5_executed", "b16k_executed",
                 "weights_tuned_during_bea_v1_p4",
                 "algorithm_changed_during_bea_v1_p4",
                 "default_should_change", "promotion_ready",
                 "provider_calls_made"):
        checks.append(_check(f"false_{flag}",
            DEFAULT_FALSE_FLAGS.get(flag) is False))
    checks.append(_check("no_role_proxy_used_field",
        "role_proxy_used" not in SAFE_TRUE_FLAGS))

    # --- G3: Policy arms (4) ---
    checks.append(_check("policy_arms_count_4", len(POLICY_ARMS) == 4))
    for arm in POLICY_ARMS:
        checks.append(_check(f"policy_arm_present_{arm}", arm in POLICY_ARMS))
    checks.append(_check("query_anchors_disabled",
        P4_QUERY_ANCHORS_ENABLED is False))

    # --- G4: Statuses enum ---
    for status in STATUSES:
        checks.append(_check(f"status_enum_{status}", isinstance(status, str)))
    checks.append(_check("statuses_count_9", len(STATUSES) == 9))
    checks.append(_check("allowed_real_run_statuses_count_5",
        len(ALLOWED_REAL_RUN_STATUSES) == 5))
    checks.append(_check("allowed_real_run_statuses_exclude_replay_mismatch",
        "no_go_p4_replay_mismatch" not in ALLOWED_REAL_RUN_STATUSES))

    # --- G5: P4 scheduler constants ---
    checks.append(_check("hard_cap_100", P4_HARD_CANDIDATE_CAP == 100))
    checks.append(_check("hard_cap_le_120", P4_HARD_CANDIDATE_CAP <= 120))
    checks.append(_check("unique_file_cap_80", P4_UNIQUE_FILE_CAP == 80))
    checks.append(_check("action_budget_2",
        P4_EXTRA_DEPTH_CHANNEL_ACTION_BUDGET_MAX == 2))
    checks.append(_check("channel_marginal_yield_2",
        P4_CHANNEL_MARGINAL_YIELD_MIN == 2))
    checks.append(_check("channel_unique_file_cap_60",
        P4_CHANNEL_UNIQUE_FILE_CAP == 60))
    checks.append(_check("channel_min_unique_share_010",
        P4_CHANNEL_MIN_UNIQUE_SHARE == 0.10))
    checks.append(_check("channel_dup_rate_max_070",
        P4_CHANNEL_DUP_FILE_RATE_MAX == 0.70))
    checks.append(_check("channel_overlap_max_085",
        P4_CHANNEL_OVERLAP_MAX == 0.85))

    # --- G6: Research success gates ---
    checks.append(_check("reach_preservation_newly_min_20",
        P4_REACH_PRESERVATION_NEWLY_MIN == 20))
    checks.append(_check("reach_preservation_depth_ratio_075",
        P4_REACH_PRESERVATION_DEPTH_RATIO == 0.75))
    checks.append(_check("latency_mult_max_2", P4_LATENCY_MULT_MAX == 2.0))
    checks.append(_check("latency_vs_p3_improvement_min_010",
        P4_LATENCY_VS_P3_IMPROVEMENT_MIN == 0.10))
    checks.append(_check("pool_mult_max_4", P4_POOL_MULT_MAX == 4.0))
    checks.append(_check("hard_cap_violation_max_0",
        P4_HARD_CAP_VIOLATION_MAX == 0))
    checks.append(_check("efficiency_vs_p3_ratio_080",
        P4_EFFICIENCY_VS_P3_RATIO == 0.80))
    checks.append(_check("action_reduction_share_min_025",
        P4_ACTION_REDUCTION_SHARE_MIN == 0.25))
    checks.append(_check("action_reduction_records_min_20",
        P4_ACTION_REDUCTION_RECORDS_MIN == 20))
    checks.append(_check("selector_relevance_mean_rank_min_5",
        P4_SELECTOR_RELEVANCE_MEAN_RANK_MIN == 5))
    checks.append(_check("selector_relevance_records_min_25",
        P4_SELECTOR_RELEVANCE_RECORDS_MIN == 25))

    # --- G7: Denominator expected 119 ---
    checks.append(_check("expected_denominator_119",
        EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR == 119))

    # --- G8: P3 binding context ---
    checks.append(_check("v1_p3_result_checkpoint",
        V1_P3_RESULT_CHECKPOINT == "eda2087"))
    checks.append(_check("v1_p3_result_status",
        V1_P3_RESULT_STATUS == "no_go_p3_cost_exceeded"))
    checks.append(_check("v1_p3_ci_run_id",
        V1_P3_CI_RUN_ID == "28102428194"))
    checks.append(_check("v1_p3_constrained_reach_58",
        V1_P3_CONSTRAINED_REACH == 58))
    checks.append(_check("v1_p3_constrained_newly_26",
        V1_P3_CONSTRAINED_NEWLY == 26))
    checks.append(_check("v1_p3_latency_mult_217",
        V1_P3_LATENCY_MULT == 2.172635))
    checks.append(_check("v1_p3_efficiency_positive",
        V1_P3_EFFICIENCY > 0))
    checks.append(_check("v1_p3_latency_mean_positive",
        V1_P3_LATENCY_MEAN > 0))

    # --- G9: P2 / P1 binding context ---
    checks.append(_check("v1_p2_result_checkpoint",
        V1_P2_RESULT_CHECKPOINT == "930dd48"))
    checks.append(_check("v1_p2_baseline_reach_32",
        V1_P2_BASELINE_REACH == 32))
    checks.append(_check("v1_p2_depth_reach_59",
        V1_P2_DEPTH_REACH == 59))
    checks.append(_check("v1_p2_depth_newly_27",
        V1_P2_DEPTH_NEWLY == 27))
    checks.append(_check("v1_p1_result_checkpoint",
        V1_P1_RESULT_CHECKPOINT == "d96e860"))
    checks.append(_check("v1_p1_denominator_119",
        V1_P1_GOLD_FILE_ABSENT_DENOMINATOR == 119))

    # --- G10: Channel diagnostics (no gold/private labels) ---
    diag_cands = [
        {"path": "src/a.py", "method": "bm25", "rank": 1,
         "score": 1.0, "normalized_score": 1.0},
        {"path": "src/b.py", "method": "bm25", "rank": 2,
         "score": 0.5, "normalized_score": 0.5},
    ]
    baseline_union = {"src/a.py", "src/c.py"}
    d = _compute_channel_diagnostics(
        "bm25", diag_cands, 100, "", baseline_union)
    checks.append(_check("diag_unique_file_count_2",
        d.unique_file_count == 2))
    checks.append(_check("diag_not_failed", d.failed is False))
    checks.append(_check("diag_not_empty", d.empty is False))
    checks.append(_check("diag_new_file_yield_1",
        d.new_file_yield_vs_baseline == 1))  # src/b.py is new
    checks.append(_check("diag_elapsed_positive",
        d.elapsed_seconds > 0))
    # Empty channel diagnostics.
    empty_d = _compute_channel_diagnostics(
        "regex", [], 0, "retrieval_failed", set())
    checks.append(_check("empty_diag_unique_0",
        empty_d.unique_file_count == 0))
    checks.append(_check("empty_diag_failed", empty_d.failed is True))
    checks.append(_check("empty_diag_empty", empty_d.empty is True))

    # --- G11: Channel eligibility selection ---
    channels = {
        "bm25": _compute_channel_diagnostics(
            "bm25", diag_cands, 50, "", baseline_union),
        "regex": _compute_channel_diagnostics(
            "regex", [], 0, "retrieval_failed", baseline_union),
        "symbol": _compute_channel_diagnostics(
            "symbol", [{"path": "src/a.py", "normalized_score": 1.0}],
            30, "", baseline_union),
    }
    selected = _select_eligible_extra_depth_channels(channels)
    checks.append(_check("eligible_excludes_failed",
        "regex" not in selected))
    checks.append(_check("eligible_within_budget",
        len(selected) <= P4_EXTRA_DEPTH_CHANNEL_ACTION_BUDGET_MAX))
    # bm25 has new files and is sparse -> eligible.
    checks.append(_check("bm25_eligible",
        channels["bm25"].eligible_for_extra_depth is True))
    # symbol has no new files, unique=1 < 60 -> sparse -> eligible.
    checks.append(_check("symbol_sparse_eligible",
        channels["symbol"].eligible_for_extra_depth is True))

    # --- G12: Denominator extraction (delegated to P3 / P2) ---
    with tempfile.TemporaryDirectory(prefix="v1p4_st_") as sd:
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

    # --- G13: Forbidden scanner ---
    safe_sample = {
        "schema_version": SCHEMA_VERSION,
        "status": "bea_v1_p4_latency_aware_retrieval_scheduler_pass",
        "arm_reach_records": [
            {"arm_name": "current_bea_candidate_pool_replay",
             "denominator_record_count": 119,
             "gold_file_available_any_pool": 32,
             "newly_reachable_count": 0},
        ],
        "arm_cost_records": [
            {"arm_name": "p4_latency_aware_action_scheduler",
             "cost_axis": "pool_size_multiplier",
             "cost_class": "ok", "value": 2.0, "threshold": 4.0},
        ],
        "arm_action_records": [
            {"arm_name": "p4_latency_aware_action_scheduler",
             "scheduler_action": "extra_depth_selected",
             "record_count": 100},
        ],
        "channel_action_records": [
            {"channel_name": "bm25",
             "channel_action": "baseline_collected",
             "record_count": 119},
        ],
        "scheduler_stop_reason_records": [
            {"scheduler_stop_reason": "extra_depth_actions_executed",
             "record_count": 100},
        ],
        "latency_decomposition_records": [
            {"latency_axis": "p4_baseline_latency_mean_seconds",
             "latency_class": "ok", "value": 1.8},
        ],
        "efficiency_records": [
            {"efficiency_axis":
                "p4_latency_aware_action_scheduler_newly_per_added_candidate",
             "efficiency_class": "ok", "value": 1.0,
             "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
             "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY,
             "p3_efficiency": V1_P3_EFFICIENCY},
        ],
        "stop_go_records": [{
            "stop_go_decision":
                "bea_v1_p4_latency_aware_retrieval_scheduler_pass",
            "stop_go_reason": "test",
            "newly_reachable_count": 26,
            "availability_lift": 0.218487,
            "latency_fixed": True,
            "pool_cost_exceeded": False,
            "latency_cost_exceeded": False,
            "hard_cap_violation_count": 0,
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
            "bea_v1_p4_latency_aware_retrieval_scheduler_smoke_aggregate_only"},
        "fd1_source_artifact_hash": "b" * 64,
        "v1_p3_result_checkpoint": V1_P3_RESULT_CHECKPOINT,
        "config_hash": "c" * 64,
    }
    checks.append(_check("scanner_allows_safe", not _scan_v1_p4(safe_sample)))
    for fk in ("private_trace_dir", "per_record_reach",
               "per_record_scheduler", "per_record_channel_actions",
               "candidate_paths", "candidate_keys", "query_text",
               "queries", "query_variants",
               "gold_paths", "gold_lines", "gold_files", "gold_match_labels",
               "snippets", "selected_order", "private_record_id",
               "private_record_ids", "repo_url", "base_commit",
               "raw_scheduler_row", "raw_channel_action_row",
               "fd1_replay_artifact_path", "scheduler_results_path",
               "scheduler_trace_path", "private_scheduler_path",
               "winner", "calibration", "method_winner",
               "recommended_default", "ranking", "decision",
               "hard_gates", "failure_category_counts",
               "arm_reach_counts", "arm_cost_counts",
               "arm_action_counts", "channel_action_counts",
               "scheduler_stop_reason_counts", "latency_decomposition_counts",
               "self_test_checks", "role_proxy", "role_proxy_assignment",
               "is_v04_repair", "is_fd2_b", "is_fd2_c",
               "is_p5", "is_v031_tuning", "is_b16k",
               "is_dense_quality_mixing", "is_quiver_quality_mixing"):
        leaked = dict(safe_sample)
        leaked[fk] = "leak"
        checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_v1_p4(leaked))))

    # --- G14: Fail-closed enforcement ---
    try:
        _enforce_v1_p4_no_forbidden(safe_sample)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk in ("private_trace_dir", "per_record_scheduler",
               "gold_paths", "winner", "hard_gates",
               "self_test_checks", "candidate_paths",
               "repo_url", "query_variants",
               "scheduler_trace_path", "private_scheduler_path"):
        leaked = dict(safe_sample)
        leaked[lk] = "leak"
        try:
            _enforce_v1_p4_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # --- G15: Build scheduler report (synthetic) ---
    fd1_art = _build_synthetic_fd1_artifact()
    priv_jsonl2 = Path(tempfile.mkdtemp(prefix="v1p4_rep_")) / "bea_fd1.decomposition.jsonl"
    _build_synthetic_private_decomposition_jsonl(
        priv_jsonl2, gold_file_absent_count=119,
        recoverable_lower_bound=1)
    pt2 = _parse_private_decomposition_jsonl(priv_jsonl2)
    _compute_file_selector_lower_bound(pt2)
    denominator2 = _extract_denominator_from_private(pt2)
    replay_path = Path(tempfile.mkdtemp(prefix="v1p4_rav_")) / "fd1_replay_report.json"
    _build_synthetic_fd1_replay_artifact(replay_path)
    rav2 = _validate_fd1_replay_artifact(replay_path, "a" * 64)
    arm_results = _build_synthetic_scheduler_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=58, p4_available=58,
        p4_latency=2.0, p4_pool=35)
    report = _build_scheduler_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results,
        retrieval_policy_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
    )
    required_tables = (
        "source_run_records", "denominator_records",
        "arm_reach_records", "arm_delta_records",
        "arm_cost_records", "arm_action_records",
        "channel_action_records", "scheduler_stop_reason_records",
        "latency_decomposition_records", "efficiency_records",
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
    for ff in ("private_trace_dir", "per_record_reach",
               "per_record_scheduler", "candidate_paths", "gold_paths",
               "query_text", "query_variants", "selected_order",
               "winner", "calibration", "hard_gates",
               "failure_category_counts", "arm_reach_counts",
               "arm_cost_counts", "arm_action_counts",
               "channel_action_counts", "scheduler_stop_reason_counts",
               "latency_decomposition_counts", "self_test_checks",
               "repo_url", "base_commit", "role_proxy_used",
               "is_v04_repair", "is_fd2_b", "is_p5", "is_b16k",
               "is_dense_quality_mixing",
               "scheduler_trace_path", "private_scheduler_path"):
        checks.append(_check(f"no_top_level_{ff}", ff not in report))
    checks.append(_check("latency_in_candidate_relevance_false",
        report.get("latency_in_candidate_relevance") is False))
    checks.append(_check("gold_labels_used_for_policy_false",
        report.get("gold_labels_used_for_policy") is False))
    checks.append(_check("query_anchors_used_in_p4_arm_false",
        report.get("query_anchors_used_in_p4_arm") is False))
    checks.append(_check("self_scan_clean", not _scan_v1_p4(report)))

    # --- G16: Records-only natural-key uniqueness ---
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
    checks.append(_check("acr_unique", not _check_unique_records(
        report.get("arm_cost_records", []), _acr_natural_key,
        "arm_cost_records")))
    checks.append(_check("aar_unique", not _check_unique_records(
        report.get("arm_action_records", []), _aar_natural_key,
        "arm_action_records")))
    checks.append(_check("car_unique", not _check_unique_records(
        report.get("channel_action_records", []), _car_natural_key,
        "channel_action_records")))
    checks.append(_check("ssr_unique", not _check_unique_records(
        report.get("scheduler_stop_reason_records", []), _ssr_natural_key,
        "scheduler_stop_reason_records")))
    checks.append(_check("ldr_unique", not _check_unique_records(
        report.get("latency_decomposition_records", []), _ldr_natural_key,
        "latency_decomposition_records")))
    checks.append(_check("efr_unique", not _check_unique_records(
        report.get("efficiency_records", []), _efr_natural_key,
        "efficiency_records")))
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

    # --- G17: Synthetic status pass ---
    # p4_newly=26 (58-32) >=20 AND >= 0.75*27=20.25 -> reach preserved.
    # p4_latency_mult = 2.0/1.8 = 1.111 <= 2.0 AND
    # latency_vs_p3_improvement = (3.645-2.0)/3.645 = 0.451 >= 0.10.
    # pool = 35, baseline=20 -> pool_mult=1.75 <= 4.0 ok.
    # hard_cap_violations = 0 (35 <= 100).
    # p4_eff = 26/(35-20) = 1.733 >= 0.8*1.208 = 0.967 ok.
    # action: p4=1, p3=3 -> share_reduced = 0.667 >= 0.25 ok.
    # p4 first_gold_rank_mean = 18 > 5 -> selector problem remains.
    checks.append(_check("synth_status_pass",
        report.get("status")
        == "bea_v1_p4_latency_aware_retrieval_scheduler_pass"))
    sgr = report.get("stop_go_records", [{}])[0] if report.get(
        "stop_go_records") else {}
    checks.append(_check("synth_stop_go_pass",
        sgr.get("stop_go_decision")
        == "bea_v1_p4_latency_aware_retrieval_scheduler_pass"))
    checks.append(_check("synth_latency_fixed",
        sgr.get("latency_fixed") is True))
    checks.append(_check("synth_newly_reachable_26",
        sgr.get("newly_reachable_count") == 26))

    bad_latency_results = _build_synthetic_scheduler_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=58, p4_available=58,
        p4_latency=4.0, p4_pool=35)
    bad_cost_safety = _cost_safety_records(bad_latency_results)
    bad_latency_exceeded = any(
        r.get("cost_safety_axis") == "max_latency_multiplier"
        and r.get("cost_safety_class") == "exceeded"
        for r in bad_cost_safety)
    bad_sgr = _stop_go_records(
        denominator_count=119,
        arm_results=bad_latency_results,
        pool_cost_exceeded=False,
        latency_cost_exceeded=bad_latency_exceeded,
        hard_cap_violation_count=0,
        retrieval_policy_executed=True,
        baseline_reach=32,
        depth_reference_reach=59,
        p3_reference_reach=58,
        baseline_reach_drift=False,
        depth_reference_reach_drift=False,
        p3_reference_reach_drift=False,
        p3_reference_latency_mean=V1_P3_LATENCY_MEAN,
    )[0]
    checks.append(_check("latency_failure_classified_as_latency_not_cost",
        bad_sgr.get("stop_go_decision") == "no_go_p4_latency_not_fixed"))
    checks.append(_check("latency_failure_not_cost_exceeded",
        bad_sgr.get("stop_go_decision") != "no_go_p4_cost_exceeded"))

    # --- G18: Arm reach records (4 arms) ---
    arr_rows = report.get("arm_reach_records", [])
    checks.append(_check("arr_count_4", len(arr_rows) == 4))
    arr_arms = {r.get("arm_name") for r in arr_rows}
    for arm in POLICY_ARMS:
        checks.append(_check(f"arr_has_{arm}", arm in arr_arms))

    # --- G19: Arm cost records (4 arms x 2 axes + 1 hard cap = 9) ---
    acr_rows = report.get("arm_cost_records", [])
    checks.append(_check("acr_count_9", len(acr_rows) == 9))
    hard_cap_rows = [r for r in acr_rows
                     if r.get("cost_axis") == "hard_cap_violation_count"]
    checks.append(_check("acr_has_hard_cap_axis", len(hard_cap_rows) == 1))
    checks.append(_check("acr_hard_cap_violations_0",
        hard_cap_rows[0].get("value") == 0.0
        if hard_cap_rows else False))

    # --- G20: Arm action records ---
    aar_rows = report.get("arm_action_records", [])
    aar_actions = {r.get("scheduler_action") for r in aar_rows}
    checks.append(_check("aar_has_extra_depth_selected",
        "extra_depth_selected" in aar_actions))

    # --- G21: Channel action records ---
    car_rows = report.get("channel_action_records", [])
    checks.append(_check("car_nonempty", len(car_rows) > 0))
    car_channels = {r.get("channel_name") for r in car_rows}
    for method in FIXED_METHODS:
        checks.append(_check(f"car_has_{method}", method in car_channels))

    # --- G22: Scheduler stop reason records ---
    ssr_rows = report.get("scheduler_stop_reason_records", [])
    ssr_reasons = {r.get("scheduler_stop_reason") for r in ssr_rows}
    checks.append(_check("ssr_has_extra_depth_actions_executed",
        "extra_depth_actions_executed" in ssr_reasons))

    # --- G23: Latency decomposition records ---
    ldr_rows = report.get("latency_decomposition_records", [])
    checks.append(_check("ldr_count_3", len(ldr_rows) == 3))
    ldr_axes = {r.get("latency_axis") for r in ldr_rows}
    checks.append(_check("ldr_has_baseline",
        "p4_baseline_latency_mean_seconds" in ldr_axes))
    checks.append(_check("ldr_has_extra_depth",
        "p4_extra_depth_latency_mean_seconds" in ldr_axes))
    checks.append(_check("ldr_has_share",
        "p4_extra_depth_latency_share" in ldr_axes))

    # --- G24: Efficiency records (3 non-baseline arms) ---
    efr_rows = report.get("efficiency_records", [])
    checks.append(_check("efr_count_3", len(efr_rows) == 3))
    efr_p4 = [r for r in efr_rows
              if "p4_latency_aware_action_scheduler" in r.get("efficiency_axis", "")]
    checks.append(_check("efr_has_p4", len(efr_p4) == 1))

    # --- G25: Denominator records ---
    dnr_rows = report.get("denominator_records", [])
    checks.append(_check("dnr_nonempty", len(dnr_rows) > 0))
    total_denom = sum(r.get("denominator_record_count", 0) for r in dnr_rows)
    checks.append(_check("dnr_total_119", total_denom == 119))

    # --- G26: Status decision logic ---
    status_no_replay = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=False,
        replay_artifact_validated=False,
        denominator_count=0,
        retrieval_policy_executed=False,
        pool_cost_exceeded=False, latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False, depth_reference_reach_drift=False,
        p3_reference_reach_drift=False,
        stop_go_decision="no_go_p4_replay_mismatch")
    checks.append(_check("decide_status_no_replay",
        status_no_replay == "no_go_p4_replay_mismatch"))
    status_blocking = _decide_status(
        audit_match=True, blocking_failure_count=1,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119, retrieval_policy_executed=True,
        pool_cost_exceeded=False, latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False, depth_reference_reach_drift=False,
        p3_reference_reach_drift=False,
        stop_go_decision="bea_v1_p4_latency_aware_retrieval_scheduler_pass")
    checks.append(_check("decide_status_blocking",
        status_blocking == "fail_schema_contract"))
    status_cost = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119, retrieval_policy_executed=True,
        pool_cost_exceeded=True, latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False, depth_reference_reach_drift=False,
        p3_reference_reach_drift=False,
        stop_go_decision="no_go_p4_cost_exceeded")
    checks.append(_check("decide_status_cost",
        status_cost == "no_go_p4_cost_exceeded"))
    status_p3_drift = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119, retrieval_policy_executed=True,
        pool_cost_exceeded=False, latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False, depth_reference_reach_drift=False,
        p3_reference_reach_drift=True,
        stop_go_decision="bea_v1_p4_latency_aware_retrieval_scheduler_pass")
    checks.append(_check("decide_status_p3_drift",
        status_p3_drift == "no_go_p4_replay_mismatch"))

    # --- G27: Unavailable report ---
    unavail = _build_unavailable_report(
        "network_required_but_disabled", self_test_passed=True,
        openlocus_binary_source="self_test", network_mode="self_test")
    checks.append(_check("unavail_status",
        unavail["status"] == "unavailable_with_reason"))
    checks.append(_check("unavail_scan_clean", not _scan_v1_p4(unavail)))
    for table in required_tables:
        if table in ("gate_records", "private_manifest_records",
                     "failure_category_count_records", "source_run_records",
                     "stop_go_records"):
            checks.append(_check(f"unavail_table_{table}_is_list",
                isinstance(unavail.get(table), list)))
        else:
            checks.append(_check(f"unavail_table_{table}_empty",
                unavail.get(table) == []))

    # --- G28: No-go when latency not fixed ---
    # p4_latency = 3.5 (close to P3 3.645, improvement < 10%).
    arm_results_latency = _build_synthetic_scheduler_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=58, p4_available=58,
        p4_latency=3.5, p4_pool=35)
    report_latency = _build_scheduler_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results_latency,
        retrieval_policy_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5)
    # latency_vs_p3_improvement = (3.645-3.5)/3.645 = 0.0398 < 0.10.
    checks.append(_check("latency_not_fixed_status",
        report_latency.get("status") == "no_go_p4_latency_not_fixed"))

    # --- G29: No-go when cost exceeded ---
    arm_results_cost = _build_synthetic_scheduler_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=58, p4_available=58,
        p4_latency=2.0, p4_pool=35)
    for rr in arm_results_cost["p4_latency_aware_action_scheduler"]:
        rr.candidate_pool_size = 200
    report_cost = _build_scheduler_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results_cost,
        retrieval_policy_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5)
    checks.append(_check("cost_exceeded_status",
        report_cost.get("status") == "no_go_p4_cost_exceeded"))

    # --- G30: No-go when denominator mismatch ---
    report_mismatch = _build_scheduler_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=[],
        arm_results={arm: [] for arm in POLICY_ARMS},
        retrieval_policy_executed=False,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5)
    checks.append(_check("mismatch_status_no_go",
        report_mismatch.get("status") == "no_go_p4_replay_mismatch"))

    # --- G31: Reach bucket + rank band records (4 arms x 6 = 24 each) ---
    rbr_rows = report.get("reach_bucket_records", [])
    checks.append(_check("rbr_count_24", len(rbr_rows) == 24))
    rkr_rows = report.get("rank_band_records", [])
    checks.append(_check("rkr_count_24", len(rkr_rows) == 24))

    # --- G32: Private scheduler manifest ---
    with tempfile.TemporaryDirectory(prefix="v1p4_manifest_st_") as sd:
        priv = Path(sd) / "scheduler.jsonl"
        _append_private_jsonl(priv, {"row": 1})
        _append_private_jsonl(priv, {"row": 2})
        pm = _private_file_manifest(
            priv,
            manifest_name="bea_v1_p4_private_scheduler_manifest",
            schema_version="bea_v1_p4_private_scheduler.v1")
        checks.append(_check("private_scheduler_manifest_count_2",
            pm.get("record_count") == 2))
        checks.append(_check("private_scheduler_manifest_path_not_serialized",
            pm.get("path_publicly_serialized") is False))

    # --- G33: Config hash ---
    ch = _config_hash()
    checks.append(_check("config_hash_64_hex",
        len(ch) == 64 and all(c in "0123456789abcdef" for c in ch)))
    checks.append(_check("config_hash_stable",
        _config_hash() == ch))

    # --- G34: No-provider-calls binding ---
    checks.append(_check("no_provider_calls_field",
        report.get("provider_calls_made") is False))
    checks.append(_check("unavail_no_provider_calls",
        unavail.get("provider_calls_made") is False))

    # --- G35: License fields ---
    for field, expected in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{field}",
            report.get(field) == expected))

    # --- G36: Framing is_latency_aware_retrieval_scheduler_smoke ---
    checks.append(_check("framing_is_scheduler_smoke",
        report.get("framing", {}).get(
            "is_latency_aware_retrieval_scheduler_smoke") is True))
    checks.append(_check("framing_not_policy_smoke",
        report.get("framing", {}).get(
            "is_constrained_retrieval_policy_smoke") is False))
    checks.append(_check("framing_not_latency_in_relevance",
        report.get("framing", {}).get("is_latency_in_relevance") is False))

    # --- G37: failure_category_count_records covers all audit categories ---
    fccr_cats = {r.get("failure_category")
                 for r in report.get("failure_category_count_records", [])}
    for cat in FAILURE_CATEGORIES_AUDIT:
        checks.append(_check(f"fccr_has_{cat}", cat in fccr_cats))

    # --- G38: cost_safety_records (2 axes) ---
    csr_rows = report.get("cost_safety_records", [])
    checks.append(_check("csr_count_2", len(csr_rows) == 2))
    csr_axes = {r.get("cost_safety_axis") for r in csr_rows}
    checks.append(_check("csr_has_pool_mult",
        "max_pool_size_multiplier" in csr_axes))
    checks.append(_check("csr_has_latency_mult",
        "max_latency_multiplier" in csr_axes))

    # --- G39: CLI surface ---
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
                "--private-trace-dir", "--private-decomposition-dir",
                "--scheduler-thresholds"):
        checks.append(_check(f"cli_no_{opt}", opt not in option_strings))

    # --- G40: Drift gates fire on baseline/P3 drift ---
    arm_results_drift = _build_synthetic_scheduler_results(
        denominator_count=119, baseline_available=10,
        depth_available=59, p3_available=58, p4_available=58,
        p4_latency=2.0, p4_pool=35)
    report_drift = _build_scheduler_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results_drift,
        retrieval_policy_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5)
    checks.append(_check("drift_status_replay_mismatch",
        report_drift.get("status") == "no_go_p4_replay_mismatch"))

    # --- G41: P4 preserves selector problem ---
    p4_arr = [r for r in report.get("arm_reach_records", [])
              if r.get("arm_name") == "p4_latency_aware_action_scheduler"]
    checks.append(_check("p4_arr_present", len(p4_arr) == 1))
    if p4_arr:
        checks.append(_check("p4_first_gold_rank_mean_above_budget",
            p4_arr[0].get("first_gold_file_rank_mean") > FIXED_BUDGET))

    # --- G42: P3 reference arm fields ---
    p3_arr = [r for r in report.get("arm_reach_records", [])
              if r.get("arm_name") == "p3_constrained_depth_policy_reference"]
    checks.append(_check("p3_arr_present", len(p3_arr) == 1))
    if p3_arr:
        checks.append(_check("p3_reach_58",
            p3_arr[0].get("gold_file_available_any_pool") == 58))

    # --- G43: Private reach rows = 119 x 4 = 476 ---
    private_reach_rows = sum(len(arm_results.get(a, [])) for a in POLICY_ARMS)
    checks.append(_check("private_reach_rows_476",
        private_reach_rows == 119 * 4))

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
        description="BEA-v1-P4 Latency-Aware Retrieval Action Scheduler Smoke")
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
                    help="Path to the OpenLocus binary (for retrieval scheduler).")
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
        _enforce_v1_p4_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    network_mode = "local_explicit" if enable_network else "disabled_opt_in"

    if not enable_network:
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
        _enforce_v1_p4_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real "
              "BEA-v1-P4 latency-aware retrieval scheduler smoke.")
        return

    try:
        report = _run_scheduler_smoke(
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
    if report.get("latency_in_candidate_relevance") is not False:
        report["status"] = "fail_schema_contract"
    if report.get("gold_labels_used_for_policy") is not False:
        report["status"] = "fail_schema_contract"
    if report.get("query_anchors_used_in_p4_arm") is not False:
        report["status"] = "fail_schema_contract"

    _enforce_v1_p4_no_forbidden(report)
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
