#!/usr/bin/env python3
"""BEA-v1-P3: Constrained Retrieval Policy Smoke (Public Records-Only).

BEA-v1-P3 is the **third phase of BEA v1 Hierarchical Actionable
Evidence Acquisition**, run after the BEA-v1-P2 result checkpoint
``930dd48``. P2 ran a candidate-availability / retrieval-reach smoke
over the FD1 ``gold_file_absent`` denominator (119 records) and found
that runtime-clean retrieval expansion can recover additional gold
files, but naive broad expansion is too costly: baseline reached
32/119; depth-only reached 59/119 (+27, pool 3.41x, latency 1.18x);
query-anchor reached 60/119 (+28) but exceeded cost; combined
depth+query reached 81/119 (+49) but violated pool/latency safety
(10.13x pool, 3.89x latency). P2 status is
``no_go_retrieval_reach_latency_or_pool_cost``.

Goal
----

P3 is the **first real retrieval-action policy** in BEA v1 (not a
selector / default / promotion). It tests whether a runtime-clean
**constrained retrieval scheduler** can preserve most of the P2
depth-only reach while bounding pool / latency. The scheduler is a
retrieval-action policy, NOT candidate relevance scoring: latency is
measured and used only as a stop / safety metric, never as a
relevance signal.

Arms (3)
--------

1. ``current_bea_candidate_pool_replay`` -- current BEA runtime-clean
   retrieval pool (bm25/regex/symbol + derived RRF), depth=1. Anchors
   the v1-P1 / v1-P2 baseline. Expected ~32/119.
2. ``p2_depth_only_reference`` -- same P2 depth-only expansion
   (depth=4, same methods, no query anchors). Reference only.
   Expected ~59/119.
3. ``p3_constrained_depth_policy`` -- main treatment. A runtime-clean
   constrained retrieval scheduler that starts from the baseline
   pool, computes only public diagnostics, applies at most one extra
   depth round under predeclared under-retrieval conditions, merges
   with a marginal new-file-yield filter, and stops on a hard
   candidate cap / unique-file cap / action budget.

P3 policy mechanism (runtime-clean retrieval scheduler)
------------------------------------------------------

* Start with the baseline pool from bm25 / literal-regex / symbol +
  derived RRF.
* Compute only public / runtime-clean diagnostics: unique file count,
  duplicate-file rate, method agreement count / non-empty channels,
  normalized score mass / spread, query-token / path-token overlap if
  available.
* Apply extra depth only under simple **predeclared** under-retrieval
  conditions (low unique file count, too few non-empty channels, high
  duplicate-file rate, low score mass / spread). No gold / private
  labels. No post-hoc tuning.
* Merge and dedupe. Keep all baseline candidates + only NEW
  unique-file candidates from the extra round (marginal new-file
  yield filter).
* Stop on hard candidate cap (<=100-120), unique-file cap, action
  budget (<=1 extra round), or marginal new-file yield below
  threshold.
* Query anchors DISABLED in the main P3 arm (binding).
* Latency is measured and used only as a stop / safety metric, not
  relevance.

Binding invariants
------------------

* claim_level = ``bea_v1_p3_constrained_retrieval_policy_smoke_only``
* status: ``bea_v1_p3_constrained_retrieval_policy_pass`` |
  ``no_go_p3_reach_not_preserved`` |
  ``no_go_p3_cost_exceeded`` |
  ``no_go_p3_policy_degenerate`` |
  ``no_go_p3_replay_mismatch`` |
  ``unavailable_with_reason`` |
  ``fail_forbidden_scan`` |
  ``fail_schema_contract``
* mode = ``bea_v1_p3_constrained_retrieval_policy_smoke``; phase =
  ``BEA-v1-P3``

* The default no-network BEA-v1-P3 artifact does NOT run retrieval,
  selector, or provider calls. The explicit manual CI/network path
  regenerates the FD1 private decomposition under ``/tmp`` AND runs the
  BEA-v1-P3 retrieval policy smoke (network + OpenLocus binary, no
  provider secrets). Gold/private labels are used ONLY for
  evaluation/scoring reach, never to construct queries/candidates/policy.
* No role/support proxies. No v0.4 repair. No FD2-B/FD2-C. No
  v0.31/v0.32 tuning. No B16-K. No dense/graph/QuIVer quality mixing.
  No selector/packer runtime change. No latency in candidate
  relevance scoring.
* Public artifact is aggregate-only and records-only. No public record
  IDs, paths, queries, snippets, gold files, candidate lists,
  per-record ranks, private trace paths, or private row payloads.

Network / CI policy (binding)
-----------------------------

* Default no-network self-test passes without HuggingFace/GitHub and
  without the committed FD1 / FD2-A1 artifacts or any private JSONL
  (self-test uses synthetic FD1 aggregate and synthetic reach rows).
* Default no-network / no-private-JSONL artifact is truthfully
  ``no_go_p3_replay_mismatch`` (no fake pass). The CI workflow
  regenerates the FD1 private decomposition under ``/tmp``,
  validates it, reruns the P3 retrieval policy smoke, and passes the
  JSONL + replay report + reach results via CLI args.
* CI is a separate explicit workflow_dispatch job; it must NOT run on
  PR/push by default, must use no provider secrets/vars/model env, and
  must upload only the aggregate report. Private JSONL/JSON files are
  NEVER uploaded.

Run::

    python3 -m py_compile eval/bea_v1_p3_constrained_retrieval_policy_smoke.py
    python3 eval/bea_v1_p3_constrained_retrieval_policy_smoke.py --self-test
    python3 eval/bea_v1_p3_constrained_retrieval_policy_smoke.py \
        --out artifacts/bea_v1_p3_constrained_retrieval_policy/\
bea_v1_p3_constrained_retrieval_policy_smoke_report.json

To run the constrained retrieval policy, the CI workflow regenerates
the FD1 private decomposition AND runs the P3 retrieval policy smoke,
then passes the results to the evaluator::

    python3 eval/bea_fd1_failure_decomposition.py \
        --enable-external-benchmark-network \
        --private-decomposition-dir /tmp/fd1_private \
        --openlocus target/release/openlocus \
        --out /tmp/fd1_replay_report.json
    python3 eval/bea_v1_p3_constrained_retrieval_policy_smoke.py \
        --enable-external-benchmark-network \
        --openlocus target/release/openlocus \
        --fd1-private-decomposition-jsonl /tmp/fd1_private/bea_fd1.decomposition.jsonl \
        --fd1-replay-artifact /tmp/fd1_replay_report.json \
        --out artifacts/bea_v1_p3_constrained_retrieval_policy/bea_v1_p3_constrained_retrieval_policy_smoke_report.json
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

# Reuse P2's scanner composition, FD1 replay validation, denominator
# extraction, and runtime-safe retrieval helpers. BEA-v1-P3 does NOT
# import any BEA-v0.4-P1/P2/P3 module (role-proxy line), does NOT use
# role proxies, and does NOT run a selector. It reuses P2's
# runtime-safe retrieval helpers (depth expansion, derived RRF, dedup)
# but applies them under a constrained retrieval-action policy.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea_v1_p2_candidate_availability_reach_smoke as bea_v1_p2  # noqa: E402
import bea_v1_p1_actionability_audit as bea_v1_p1  # noqa: E402
import bea_fd1_failure_decomposition as bea_fd1  # noqa: E402
import bea4_external_scale_smoke as bea4  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import bea1_mechanism_ablation as bea1  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402

# --- Schema / claim constants ---
SCHEMA_VERSION = "bea_v1_p3_constrained_retrieval_policy_smoke.v1"
GENERATED_BY = "eval/bea_v1_p3_constrained_retrieval_policy_smoke.py"
CLAIM_LEVEL = "bea_v1_p3_constrained_retrieval_policy_smoke_only"
MODE = "bea_v1_p3_constrained_retrieval_policy_smoke"
PHASE = "BEA-v1-P3"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p3_constrained_retrieval_policy/"
    "bea_v1_p3_constrained_retrieval_policy_smoke_report.json"
)
DEFAULT_FD1_ARTIFACT = bea_fd1.DEFAULT_OUT

# --- P2 binding context (read-only) ---
V1_P2_RESULT_CHECKPOINT = "930dd48"
V1_P2_RESULT_STATUS = "no_go_retrieval_reach_latency_or_pool_cost"
V1_P2_CI_RUN_ID = "28093864524"
# P2 observed reach / cost values (from the committed P2 artifact).
V1_P2_BASELINE_REACH = 32
V1_P2_BASELINE_POOL_MEAN = 19.983193
V1_P2_BASELINE_LATENCY_MEAN = 1.804176
V1_P2_DEPTH_REACH = 59
V1_P2_DEPTH_NEWLY = 27
V1_P2_DEPTH_LIFT = 0.226891
V1_P2_DEPTH_POOL_MEAN = 68.184874
V1_P2_DEPTH_POOL_MULT = 3.412111
V1_P2_DEPTH_LATENCY_MEAN = 2.120445
V1_P2_DEPTH_LATENCY_MULT = 1.175298
V1_P2_QUERY_ANCHOR_REACH = 60
V1_P2_QUERY_ANCHOR_NEWLY = 28
V1_P2_QUERY_ANCHOR_POOL_MULT = 5.04037
V1_P2_QUERY_ANCHOR_LATENCY_MULT = 3.413331
V1_P2_COMBINED_REACH = 81
V1_P2_COMBINED_NEWLY = 49
V1_P2_COMBINED_LIFT = 0.411765
V1_P2_COMBINED_POOL_MEAN = 202.378151
V1_P2_COMBINED_POOL_MULT = 10.127418
V1_P2_COMBINED_LATENCY_MEAN = 7.025361
V1_P2_COMBINED_LATENCY_MULT = 3.893944
# P2 efficiency: newly_reachable / added_candidates (pool_mean - baseline_pool_mean)
V1_P2_DEPTH_EFFICIENCY = round(
    V1_P2_DEPTH_NEWLY / (V1_P2_DEPTH_POOL_MEAN - V1_P2_BASELINE_POOL_MEAN), 6)
V1_P2_COMBINED_EFFICIENCY = round(
    V1_P2_COMBINED_NEWLY / (V1_P2_COMBINED_POOL_MEAN - V1_P2_BASELINE_POOL_MEAN), 6)

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
# change them; the constrained policy changes depth scheduling only).
FIXED_BUDGET = bea_fd1.FIXED_BUDGET  # 5
FIXED_METHODS = tuple(bea_fd1.FIXED_METHODS.split(","))  # bm25,regex,symbol

# FD1 frame expectations (binding).
EXPECTED_RECORDS_DECOMPOSED = bea_fd1.EXPECTED_DECOMPOSED_RECORDS  # 239
EXPECTED_PRIVATE_DECOMP_ROWS = bea_fd1.EXPECTED_PRIVATE_DECOMP_ROWS  # 86040
EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR = 119

# --- Retrieval policy arms (3) ---
POLICY_ARMS = (
    "current_bea_candidate_pool_replay",
    "p2_depth_only_reference",
    "p3_constrained_depth_policy",
)

# Depth multipliers.
BASELINE_DEPTH_MULTIPLIER = 1
DEPTH_REFERENCE_MULTIPLIER = 4  # same as P2 depth-only (4x)
DEFAULT_RETRIEVAL_LIMIT = 20

# Rank bands for reach bucketing (inherited from P2).
RANK_BANDS = (10, 50, 100, 200)

# --- P3 constrained retrieval policy constants (binding) ---
# Hard candidate cap (per-record). <=120 as required.
P3_HARD_CANDIDATE_CAP = 100
# Unique-file cap (per-record). Stops merging once this many unique
# files are in the final pool.
P3_UNIQUE_FILE_CAP = 80
# Action budget: at most one extra-depth round.
P3_ACTION_BUDGET_MAX = 1
# Marginal new-file yield threshold: extra round must contribute at
# least this many NEW unique files to be merged. Below it, the policy
# keeps baseline only (degenerate extra round).
P3_MARGINAL_YIELD_MIN = 2

# Predeclared under-retrieval conditions (NO gold / private labels, NO
# post-hoc tuning). The extra depth round is triggered iff ANY holds.
P3_UNDER_RETRIEVAL_UNIQUE_FILE_MAX = 15
P3_UNDER_RETRIEVAL_DUP_FILE_RATE_MIN = 0.50
P3_UNDER_RETRIEVAL_NONEMPTY_CHANNELS_MAX = 2  # < 3 non-empty channels
P3_UNDER_RETRIEVAL_SCORE_MASS_MAX = 5.0  # low normalized score mass

# Query anchors DISABLED in the main P3 arm (binding).
P3_QUERY_ANCHORS_ENABLED = False

# --- Statuses enum (binding) ---
STATUSES = (
    "bea_v1_p3_constrained_retrieval_policy_pass",
    "no_go_p3_reach_not_preserved",
    "no_go_p3_cost_exceeded",
    "no_go_p3_policy_degenerate",
    "no_go_p3_replay_mismatch",
    "unavailable_with_reason",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "bea_v1_p3_constrained_retrieval_policy_pass",
    "no_go_p3_reach_not_preserved",
    "no_go_p3_cost_exceeded",
    "no_go_p3_policy_degenerate",
})

# --- Research success gates (binding) ---
# 1. Reach preservation: newly reachable >=20/119 OR retains >=75% of
#    P2 depth-only newly reachable (>=21 of +27).
P3_REACH_PRESERVATION_NEWLY_MIN = 20
P3_REACH_PRESERVATION_DEPTH_RATIO = 0.75  # >= 75% of P2 depth-only +27
# 2. Cost safety: mean pool mult <=4.0x; mean latency mult <=2.0x;
#    hard cap violation count = 0.
P3_POOL_MULT_MAX = 4.0
P3_LATENCY_MULT_MAX = 2.0
P3_HARD_CAP_VIOLATION_MAX = 0
# 3. Policy efficiency: newly_reachable_per_added_candidate better than
#    P2 combined and not materially worse than P2 depth-only.
#    "Better than combined" -> P3 eff > V1_P2_COMBINED_EFFICIENCY.
#    "Not materially worse than depth-only" -> P3 eff >= 80% of depth.
P3_EFFICIENCY_VS_DEPTH_RATIO = 0.80  # >= 80% of depth-only efficiency
# 4. Selector relevance remains: enough reachable gold files remain
#    outside final budget (mean first-gold rank > budget OR >=25
#    records have first-gold rank > budget).
P3_SELECTOR_RELEVANCE_MEAN_RANK_MIN = 5  # > FIXED_BUDGET
P3_SELECTOR_RELEVANCE_RECORDS_MIN = 25

# --- Hard validity gates (with tolerances to catch drift) ---
# Baseline reach must reproduce ~32 within tolerance.
V1_P2_BASELINE_REACH_TOLERANCE = 3  # baseline in [29, 35]
V1_P2_DEPTH_REACH_TOLERANCE = 3  # depth ref in [56, 62]

# --- Stop / go thresholds inherited from P2 cost safety ---
NO_GO_POOL_SIZE_MAX_MULTIPLIER = 4  # pool <= 4x baseline
NO_GO_LATENCY_MAX_MULTIPLIER = 2  # latency <= 2x baseline

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "fd1_artifact_read": False,
    "fd2a1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd2a1_artifact_modified": False,
    "bea_v1_p3_policy_smoke_performed": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
    "retrieval_policy_executed": False,
    "bea_v1_p3_audit_evaluator_no_provider_calls": True,
    "bea_v1_p3_audit_evaluator_no_selector_executed": True,
    "bea_v1_p3_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p3_audit_evaluator_no_role_proxy": True,
    "bea_v1_p3_audit_evaluator_latency_not_in_relevance": True,
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
    "algorithm_changed_during_bea_v1_p3": False,
    "weights_tuned_during_bea_v1_p3": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p3": False,
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
    "latency_in_candidate_relevance": False,
    "private_decomposition_used_for_selection": False,
    "gold_labels_used_for_selection": False,
    "gold_labels_used_for_query_construction": False,
    "gold_labels_used_for_policy": False,
    "query_anchors_used_in_p3_arm": False,
    "new_records_added_during_bea_v1_p3": False,
    "heldout_validation_claimed": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication":
        "aggregate_only_constrained_retrieval_policy_smoke",
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
    "retrieval_policy_failed",
    "baseline_reach_drift",
    "depth_reference_reach_drift",
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
# Scanner (strict, fail-closed). Composes the P2 scanner (which composes
# P1 / FD1 / BEA-5 / BEA-3); adds BEA-v1-P3-specific policy-private
# rejections.
# ---------------------------------------------------------------------------

# BEA-v1-P3 forbidden extra top-level keys (policy-private / per-record
# / claim / dynamic-dict mirrors / forbidden scope). Inherits the full
# FD1 + P1 + P2 forbidden-key discipline via ``bea_v1_p2._scan_v1_p2``.
V1_P3_FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        # private trace paths / dirs (BEA-v1-P3 must not serialize them)
        "private_trace_dir", "trace_dir", "private_score_dir",
        "private_audit_dir", "audit_trace_path",
        "private_decomposition_dir", "private_reach_dir",
        "private_policy_dir", "policy_trace_dir",
        "private_decomposition_path", "private_decomposition_file",
        "private_reach_path", "private_reach_file",
        "private_policy_path", "private_policy_file",
        "retrieval_trace_path", "candidate_trace_path",
        "policy_trace_path",
        # per-record policy / reach detail (aggregate counts only)
        "per_record_reach", "per_record_candidates",
        "per_record_policy", "per_record_diagnostics",
        "per_record_actions", "per_record_stop_reason",
        "per_record_query_variants", "per_record_gold_match",
        "per_record_pool_size", "per_record_latency",
        "per_record_ranks", "record_reach_detail",
        "record_policy_detail", "record_diagnostics_detail",
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
        # objective-config / weights / raw trace payloads (policy-private)
        "objective_config_payload", "fd1_category_weights_payload",
        "weight_derivation_payload", "frozen_weights_payload",
        "policy_config_payload", "policy_thresholds_payload",
        "raw_score_row", "raw_decision_row",
        "raw_feature_row", "raw_decomposition_row",
        "raw_reach_row", "raw_candidate_row",
        "raw_policy_row", "raw_diagnostics_row",
        # FD1 / FD2-A1 / P1 / P2 source artifact paths (private)
        "fd1_source_artifact_path", "fd2a1_source_artifact_path",
        "fd2a_source_artifact_path", "v1_p1_source_artifact_path",
        "v1_p2_source_artifact_path",
        "fd1_replay_artifact_path", "reach_results_path",
        "policy_results_path",
        # claim / promotion (BEA-v1-P3 is policy smoke only)
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
        "arm_cost_counts", "policy_action_counts",
        "policy_stop_reason_counts", "efficiency_counts",
        "reach_bucket_counts", "rank_band_counts",
        "stop_go_counts",
        # forbidden scope flags (BEA-v1-P3 is NOT these)
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
V1_P3_CONTAINER_KEYS = frozenset({
    "source_run_records", "denominator_records",
    "arm_reach_records", "arm_delta_records",
    "arm_cost_records", "policy_action_records",
    "policy_stop_reason_records", "efficiency_records",
    "reach_bucket_records", "rank_band_records",
    "cost_safety_records", "stop_go_records",
    "gate_records", "private_manifest_records",
    "failure_category_count_records", "framing",
})


def _is_v1_p3_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in V1_P3_CONTAINER_KEYS


def _scan_v1_p3_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_v1_p3_schema_key_container(sub_path)
                if (key_str in V1_P3_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_v1_p3_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


# BEA-v1-P3-specific safe VALUE path last-key segments. These keys MAY
# hold long policy strings or 64-char hex artifact hashes without
# triggering the primitive long_string / hex_digest_value checks.
V1_P3_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
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
        "arm_name", "arm_class", "reach_bucket", "rank_band",
        "cost_safety_axis", "cost_safety_class",
        "cost_axis", "cost_class",
        "policy_action", "policy_action_class",
        "stop_reason", "stop_reason_class",
        "efficiency_axis", "efficiency_class",
        "treatment_arm", "baseline_arm", "reference_arm",
        "fd1_overlap_policy", "fd1_source_overlap_policy",
        "excluded_prior_windows_policy",
        "config_hash",
    }
)


def _v1_p3_safe_value_path(path: str) -> bool:
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in V1_P3_SAFE_VALUE_PATH_LAST_KEYS


def _scan_v1_p3(obj: Any) -> list[dict[str, Any]]:
    # Compose with the P2 scanner (which composes P1/FD1/BEA-5/BEA-3),
    # then add BEA-v1-P3-specific rejections. Filter primitive false
    # positives for BEA-v1-P3-safe value paths.
    violations = bea_v1_p2._scan_v1_p2(obj)
    violations.extend(_scan_v1_p3_forbidden_keys(obj))
    filtered: list[dict[str, Any]] = []
    for v in violations:
        path = v.get("path", "")
        cat = v.get("category", "")
        # P3 container tables are under P3's records-only discipline.
        # Inherited scanners (FD1/BEA-2/3/5/P1/P2) do not know about
        # P3's new container tables and may flag legitimate record
        # field names (e.g. ``stop_reason``) that collide with their own
        # forbidden key sets. P3's own forbidden-key scanner already
        # enforces the correct container-aware discipline, so filter
        # inherited ``forbidden_*_key`` violations whose path is inside
        # a V1_P3_CONTAINER_KEYS container. (FD1 uses
        # ``forbidden_fd1_key``; BEA-2/3/5 use ``forbidden_*_extra_key``.)
        if (cat.startswith("forbidden_") and cat.endswith("_key")
                and _is_v1_p3_schema_key_container(path)):
            continue
        if cat in ("long_string", "hex_digest_value",
                   "forbidden_field_name_value",
                   "repo_slug_value",
                   "line_range_value") and _v1_p3_safe_value_path(path):
            continue
        filtered.append(v)
    return filtered


def _v1_p3_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p3(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_v1_p3_no_forbidden(obj: Any) -> None:
    scan = _v1_p3_forbidden_scan_summary(obj)
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


# --- Natural keys for BEA-v1-P3 public record tables ---


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


def _par_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["policy_action"],)


def _psr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["stop_reason"],)


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

# ---------------------------------------------------------------------------
# FD1 private decomposition parser + denominator extractor
# (reuse P2's parser + denominator extraction, identical schema)
# ---------------------------------------------------------------------------


def _parse_private_decomposition_jsonl(
    path: Path | None,
) -> bea_v1_p1.ParsedPrivateDecomposition:
    """Delegate to P2's parser (identical schema)."""
    return bea_v1_p2._parse_private_decomposition_jsonl(path)


def _compute_file_selector_lower_bound(
    pt: bea_v1_p1.ParsedPrivateDecomposition,
) -> None:
    """Delegate to P2's lower-bound computer."""
    bea_v1_p2._compute_file_selector_lower_bound(pt)


def _validate_fd1_replay_artifact(
    replay_artifact_path: Path | None,
    committed_fd1_manifest_hash: str,
) -> bea_v1_p1.Fd1ReplayArtifactValidation:
    """Delegate to P2's replay-artifact validator."""
    return bea_v1_p2._validate_fd1_replay_artifact(
        replay_artifact_path, committed_fd1_manifest_hash)


def _load_committed_artifact(
    artifact_path: Path,
) -> tuple[dict[str, Any], str, str, str]:
    return bea_v1_p1._load_committed_artifact(artifact_path)


def _extract_denominator_from_private(
    pt: bea_v1_p1.ParsedPrivateDecomposition,
) -> list[bea_v1_p2.DenominatorRecord]:
    """Delegate to P2's denominator extractor (identical schema)."""
    return bea_v1_p2._extract_denominator_from_private(pt)


# ---------------------------------------------------------------------------
# Runtime-clean policy diagnostics (public signals only; no gold labels)
# ---------------------------------------------------------------------------


class PolicyDiagnostics:
    """Runtime-clean diagnostics computed on a candidate pool (in-memory).

    All fields are derived from the candidate pool and the public task
    text only. No gold / private labels, no post-hoc tuning. Used by the
    constrained retrieval scheduler to decide whether to apply an extra
    depth round.
    """

    def __init__(self) -> None:
        self.unique_file_count: int = 0
        self.duplicate_file_rate: float = 0.0
        self.nonempty_channels: int = 0
        self.method_agreement_count: int = 0
        self.score_mass: float = 0.0
        self.score_spread: float = 0.0
        self.query_token_count: int = 0
        self.path_token_overlap: int = 0
        self.under_retrieved: bool = False
        self.triggered_conditions: list[str] = []


def _compute_policy_diagnostics(
    candidates: list[dict[str, Any]],
    query: str,
    methods: tuple[str, ...] = FIXED_METHODS,
) -> PolicyDiagnostics:
    """Compute runtime-clean policy diagnostics on a candidate pool.

    Returns a :class:`PolicyDiagnostics`. No gold / private labels.
    """
    d = PolicyDiagnostics()
    # Empty pool is always under-retrieved (no candidates at all).
    if not candidates:
        d.under_retrieved = True
        d.triggered_conditions = ["empty_pool"]
        return d
    paths = [str(c.get("path", "") or "") for c in candidates]
    unique_files = set(p for p in paths if p)
    d.unique_file_count = len(unique_files)
    total = len(paths)
    d.duplicate_file_rate = round(
        (total - len(unique_files)) / total, 6) if total > 0 else 0.0
    # Non-empty channels: methods that returned >=1 candidate.
    method_set = {str(c.get("method", "") or "") for c in candidates
                  if c.get("method")}
    # Count bm25/regex/symbol/rrf channels that are present.
    d.nonempty_channels = sum(
        1 for m in (*methods, "rrf") if m in method_set)
    # Method agreement count: candidates returned by >1 method
    # (approximated by unique files appearing via >1 method).
    file_methods: dict[str, set[str]] = {}
    for c in candidates:
        p = str(c.get("path", "") or "")
        m = str(c.get("method", "") or "")
        if p and m:
            file_methods.setdefault(p, set()).add(m)
    d.method_agreement_count = sum(
        1 for ms in file_methods.values() if len(ms) > 1)
    # Normalized score mass / spread.
    norm_scores = [
        float(c.get("normalized_score", 0.0) or 0.0) for c in candidates
        if isinstance(c.get("normalized_score"), (int, float))]
    d.score_mass = round(sum(norm_scores), 6) if norm_scores else 0.0
    d.score_spread = round(
        max(norm_scores) - min(norm_scores), 6) if norm_scores else 0.0
    # Query-token / path-token overlap (best-effort).
    q_tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,40}", str(query or "")))
    d.query_token_count = len(q_tokens)
    path_tokens: set[str] = set()
    for p in unique_files:
        path_tokens.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,40}", p))
    d.path_token_overlap = len(q_tokens & path_tokens) if q_tokens else 0
    # Predeclared under-retrieval conditions (NO gold labels, NO tuning).
    triggered: list[str] = []
    if d.unique_file_count < P3_UNDER_RETRIEVAL_UNIQUE_FILE_MAX:
        triggered.append("low_unique_file_count")
    if d.duplicate_file_rate > P3_UNDER_RETRIEVAL_DUP_FILE_RATE_MIN:
        triggered.append("high_duplicate_file_rate")
    if d.nonempty_channels <= P3_UNDER_RETRIEVAL_NONEMPTY_CHANNELS_MAX:
        triggered.append("too_few_nonempty_channels")
    if d.score_mass < P3_UNDER_RETRIEVAL_SCORE_MASS_MAX:
        triggered.append("low_score_mass")
    d.triggered_conditions = triggered
    d.under_retrieved = bool(triggered)
    return d


# ---------------------------------------------------------------------------
# Retrieval policy runner (constrained retrieval scheduler)
# ---------------------------------------------------------------------------


class PolicyReachResult:
    """Per-arm reach result for one denominator record (in-memory only).

    Extends the P2 ReachResult concept with P3 policy fields: the
    action taken, the stop reason, the diagnostics summary, and whether
    the hard candidate cap was hit. All fields are private; only
    aggregate counts are published.
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
        # P3 policy fields (p3_constrained_depth_policy arm only).
        self.policy_action: str = ""  # baseline_only / extra_depth_triggered / ...
        self.policy_stop_reason: str = ""  # baseline_no_extra / ...
        self.hard_cap_hit: bool = False
        self.unique_file_cap_hit: bool = False
        self.extra_depth_round_executed: bool = False
        self.under_retrieval_triggered: bool = False
        self.marginal_yield_new_files: int = 0
        self.baseline_unique_file_count: int = 0
        self.final_unique_file_count: int = 0
        self.triggered_conditions_private: list[str] = []


def _reach_rank_band(rank: int) -> str:
    """Map a rank to a reach bucket label (inherited from P2)."""
    return bea_v1_p2._reach_rank_band(rank)


def _collect_all_method_candidates(
    openlocus_bin: str,
    query: str,
    cwd: Path,
    depth_multiplier: int,
    methods: tuple[str, ...] = FIXED_METHODS,
    query_variants: list[str] | None = None,
) -> tuple[list[dict[str, Any]], int, str, bool]:
    """Collect per-method candidates at explicit depth (reuses P2 helpers).

    Returns ``(candidates, latency_ms, error_str, retrieval_error)``.
    Query anchors are DISABLED in the main P3 arm; this helper only
    honors ``query_variants`` when explicitly passed (which the main
    P3 arm never does).
    """
    all_candidates: list[dict[str, Any]] = []
    total_latency_ms = 0
    retrieval_error = False
    limit = DEFAULT_RETRIEVAL_LIMIT * max(1, int(depth_multiplier))
    queries = [query]
    if query_variants:
        queries = list(query_variants)[:bea_v1_p2.MAX_QUERY_VARIANTS_PER_ARM]
    for method in methods:
        for q in queries:
            cands, latency_ms, err = (
                bea_v1_p2._collect_method_candidates_limited(
                    openlocus_bin, method, q, cwd, limit)
            )
            if (err in {"retrieval_failed", "invalid_json"}
                    or err.startswith("returncode_")):
                retrieval_error = True
            total_latency_ms += latency_ms
            all_candidates.extend(cands)
    # Derive RRF from the runtime-safe method result lists (reuses P2).
    all_candidates.extend(
        bea_v1_p2._derive_rrf_candidates_from_candidates(
            all_candidates, limit)
    )
    # Deduplicate (reuses BEA-1's dedup).
    deduped = bea1._dedup_candidates(all_candidates)
    return deduped, total_latency_ms, "", retrieval_error


def _check_gold_file_reach(
    candidates: list[dict[str, Any]], gold_set: set[str],
) -> tuple[bool, int, str, int]:
    """Check gold-file reach in a candidate pool.

    Returns ``(gold_available, first_gold_rank, rank_band, dup_files)``.
    Gold paths are used ONLY to check reach, never to construct the
    pool.
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
) -> PolicyReachResult:
    """Run the baseline arm (depth=1, no query anchors)."""
    rr = PolicyReachResult(
        arm_name="current_bea_candidate_pool_replay",
        private_record_id="")
    rr.policy_action = "baseline_only"
    rr.policy_stop_reason = "baseline_arm"
    t0 = time.perf_counter()
    cands, latency_ms, _, err = _collect_all_method_candidates(
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
    if rr.retrieval_error:
        rr.policy_stop_reason = "retrieval_failed"
    rr.retrieval_latency_seconds = rr.retrieval_latency_seconds or (
        time.perf_counter() - t0)
    return rr


def _run_depth_reference_arm(
    *, openlocus_bin: str, repo_root: Path, query: str, gold_set: set[str],
) -> PolicyReachResult:
    """Run the P2 depth-only reference arm (depth=4, no query anchors)."""
    rr = PolicyReachResult(
        arm_name="p2_depth_only_reference",
        private_record_id="")
    rr.policy_action = "depth_reference_only"
    rr.policy_stop_reason = "depth_reference_arm"
    t0 = time.perf_counter()
    cands, latency_ms, _, err = _collect_all_method_candidates(
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
    if rr.retrieval_error:
        rr.policy_stop_reason = "retrieval_failed"
    rr.retrieval_latency_seconds = rr.retrieval_latency_seconds or (
        time.perf_counter() - t0)
    return rr


def _run_p3_constrained_policy_arm(
    *, openlocus_bin: str, repo_root: Path, query: str, gold_set: set[str],
) -> PolicyReachResult:
    """Run the P3 constrained retrieval policy for one record.

    Policy steps:
      1. Baseline round (depth=1, no query anchors).
      2. Compute runtime-clean diagnostics on the baseline pool.
      3. If under-retrieved (any predeclared condition) AND action
         budget remains, run ONE extra depth round (depth=4, no query
         anchors).
      4. Marginal new-file yield filter: only merge extra-round
         candidates whose file is NEW vs the baseline pool. Skip the
         merge entirely if the extra round yields < threshold new
         unique files.
      5. Stop on hard candidate cap, unique-file cap, or action budget.
      6. Compute gold-file reach on the final merged + deduped + capped
         pool.

    No gold / private labels are used in policy / query construction.
    Latency is measured and used only as a stop / safety metric.
    """
    rr = PolicyReachResult(
        arm_name="p3_constrained_depth_policy",
        private_record_id="")
    rr.policy_action = "baseline_only"
    rr.policy_stop_reason = "baseline_no_extra"
    t0 = time.perf_counter()
    # Round 1: baseline pool (depth=1, no query anchors).
    baseline_cands, baseline_latency_ms, _, base_err = (
        _collect_all_method_candidates(
            openlocus_bin, query, repo_root, BASELINE_DEPTH_MULTIPLIER))
    rr.retrieval_error = base_err
    # Compute runtime-clean diagnostics on the baseline pool.
    diag = _compute_policy_diagnostics(baseline_cands, query)
    rr.baseline_unique_file_count = diag.unique_file_count
    rr.under_retrieval_triggered = diag.under_retrieved
    rr.triggered_conditions_private = list(diag.triggered_conditions)

    final_cands: list[dict[str, Any]] = list(baseline_cands)
    extra_latency_ms = 0
    extra_round_executed = False
    hard_cap_hit = False
    unique_file_cap_hit = False

    if diag.under_retrieved and P3_ACTION_BUDGET_MAX >= 1:
        # Round 2: extra depth round (depth=4, no query anchors).
        extra_cands, extra_latency_ms, _, extra_err = (
            _collect_all_method_candidates(
                openlocus_bin, query, repo_root, DEPTH_REFERENCE_MULTIPLIER))
        if extra_err:
            rr.retrieval_error = True
        extra_round_executed = True
        # Marginal new-file yield: NEW unique files vs baseline.
        baseline_files = {str(c.get("path", "") or "")
                          for c in baseline_cands if c.get("path")}
        new_files = {str(c.get("path", "") or "")
                     for c in extra_cands if c.get("path")} - baseline_files
        rr.marginal_yield_new_files = len(new_files)
        if len(new_files) >= P3_MARGINAL_YIELD_MIN:
            # Merge: keep all baseline + only NEW unique-file candidates.
            merged: list[dict[str, Any]] = list(baseline_cands)
            seen_files = set(baseline_files)
            for c in extra_cands:
                p = str(c.get("path", "") or "")
                if p and p not in seen_files:
                    merged.append(c)
                    seen_files.add(p)
                if len(merged) >= P3_HARD_CANDIDATE_CAP:
                    hard_cap_hit = True
                    break
                if len(seen_files) >= P3_UNIQUE_FILE_CAP:
                    unique_file_cap_hit = True
                    break
            final_cands = merged[:P3_HARD_CANDIDATE_CAP]
            rr.policy_action = "extra_depth_triggered"
            if hard_cap_hit:
                rr.policy_stop_reason = "hard_candidate_cap_reached"
            elif unique_file_cap_hit:
                rr.policy_stop_reason = "unique_file_cap_reached"
            else:
                rr.policy_stop_reason = "extra_depth_round_executed"
        else:
            # Marginal yield below threshold: keep baseline only.
            rr.policy_action = "extra_depth_skipped_low_yield"
            rr.policy_stop_reason = "marginal_yield_below_threshold"
            final_cands = list(baseline_cands)
    else:
        # Not under-retrieved: keep baseline only.
        rr.policy_action = "baseline_only"
        rr.policy_stop_reason = "not_under_retrieved"

    rr.extra_depth_round_executed = extra_round_executed
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
    total_latency_ms = baseline_latency_ms + extra_latency_ms
    rr.retrieval_latency_seconds = round(total_latency_ms / 1000.0, 6)
    if rr.retrieval_error and not rr.policy_stop_reason:
        rr.policy_stop_reason = "retrieval_failed"
    rr.retrieval_latency_seconds = rr.retrieval_latency_seconds or (
        time.perf_counter() - t0)
    return rr


def _resolve_private_policy_dir() -> Path:
    """Return a /tmp-only private trace dir for BEA-v1-P3 policy rows."""
    raw = os.environ.get("OPENLOCUS_BEA_V1_P3_PRIVATE_POLICY_DIR", "")
    base = Path(raw) if raw else Path(
        f"/tmp/openlocus_bea_v1_p3_policy_{os.getpid()}"
    )
    resolved = base.resolve()
    if not str(resolved).startswith("/tmp/"):
        raise ValueError("invalid private policy dir")
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
    """Stable hash of the P3 policy configuration (private; not uploaded)."""
    config = json.dumps({
        "hard_candidate_cap": P3_HARD_CANDIDATE_CAP,
        "unique_file_cap": P3_UNIQUE_FILE_CAP,
        "action_budget_max": P3_ACTION_BUDGET_MAX,
        "marginal_yield_min": P3_MARGINAL_YIELD_MIN,
        "under_retrieval_unique_file_max":
            P3_UNDER_RETRIEVAL_UNIQUE_FILE_MAX,
        "under_retrieval_dup_file_rate_min":
            P3_UNDER_RETRIEVAL_DUP_FILE_RATE_MIN,
        "under_retrieval_nonempty_channels_max":
            P3_UNDER_RETRIEVAL_NONEMPTY_CHANNELS_MAX,
        "under_retrieval_score_mass_max":
            P3_UNDER_RETRIEVAL_SCORE_MASS_MAX,
        "query_anchors_enabled": P3_QUERY_ANCHORS_ENABLED,
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
    """One source_run_records row describing the FD1 + P1 + P2 source."""
    del fd1_committed_manifest_hash
    return [{
        "source_phase": "BEA-v1-P2",
        "source_ci_run_id": V1_P2_CI_RUN_ID,
        "source_checkpoint": V1_P2_RESULT_CHECKPOINT,
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
    """Per-(source_phase, benchmark) denominator count records (inherited)."""
    return bea_v1_p2._denominator_records(denominator)


def _arm_reach_records(
    arm_results: dict[str, list[PolicyReachResult]],
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
        # newly_reachable vs baseline.
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
    arm_results: dict[str, list[PolicyReachResult]],
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
    arm_results: dict[str, list[PolicyReachResult]],
) -> list[dict[str, Any]]:
    """Per-arm cost records (pool size + latency multipliers + hard cap).

    Natural key ``(arm_name, cost_axis)``.
    """
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
    # Hard cap violation count (p3 arm only).
    p3_results = arm_results.get("p3_constrained_depth_policy", [])
    hard_cap_violations = sum(1 for r in p3_results
                              if r.candidate_pool_size > P3_HARD_CANDIDATE_CAP)
    rows.append({
        "arm_name": "p3_constrained_depth_policy",
        "cost_axis": "hard_cap_violation_count",
        "cost_class": (["ok"] if hard_cap_violations <= P3_HARD_CAP_VIOLATION_MAX
                       else ["exceeded"])[0],
        "value": float(hard_cap_violations),
        "threshold": float(P3_HARD_CAP_VIOLATION_MAX),
    })
    rows.sort(key=lambda r: (r["arm_name"], r["cost_axis"]))
    return rows


def _policy_action_records(
    arm_results: dict[str, list[PolicyReachResult]],
) -> list[dict[str, Any]]:
    """Per-policy-action count records (p3 arm only).

    Natural key ``(policy_action,)``.
    """
    rows: list[dict[str, Any]] = []
    p3_results = arm_results.get("p3_constrained_depth_policy", [])
    action_counts: dict[str, int] = {}
    for r in p3_results:
        a = r.policy_action or "unknown"
        action_counts[a] = action_counts.get(a, 0) + 1
    all_actions = (
        "baseline_only", "extra_depth_triggered",
        "extra_depth_skipped_low_yield",
    )
    for action in all_actions:
        rows.append({
            "policy_action": action,
            "record_count": int(action_counts.get(action, 0)),
        })
    # Any unexpected actions (defensive; should be empty).
    for action, cnt in sorted(action_counts.items()):
        if action not in all_actions:
            rows.append({
                "policy_action": action,
                "record_count": int(cnt),
            })
    rows.sort(key=lambda r: r["policy_action"])
    return rows


def _policy_stop_reason_records(
    arm_results: dict[str, list[PolicyReachResult]],
) -> list[dict[str, Any]]:
    """Per-stop-reason count records (p3 arm only).

    Natural key ``(stop_reason,)``.
    """
    rows: list[dict[str, Any]] = []
    p3_results = arm_results.get("p3_constrained_depth_policy", [])
    stop_counts: dict[str, int] = {}
    for r in p3_results:
        s = r.policy_stop_reason or "unknown"
        stop_counts[s] = stop_counts.get(s, 0) + 1
    all_reasons = (
        "baseline_arm", "baseline_no_extra", "not_under_retrieved",
        "extra_depth_round_executed", "hard_candidate_cap_reached",
        "unique_file_cap_reached", "marginal_yield_below_threshold",
        "retrieval_failed", "depth_reference_arm",
    )
    for reason in all_reasons:
        rows.append({
            "stop_reason": reason,
            "record_count": int(stop_counts.get(reason, 0)),
        })
    for reason, cnt in sorted(stop_counts.items()):
        if reason not in all_reasons:
            rows.append({
                "stop_reason": reason,
                "record_count": int(cnt),
            })
    rows.sort(key=lambda r: r["stop_reason"])
    return rows


def _efficiency_records(
    arm_results: dict[str, list[PolicyReachResult]],
) -> list[dict[str, Any]]:
    """Per-arm efficiency records (newly_reachable_per_added_candidate).

    Natural key ``(efficiency_axis,)``. Compares P3 policy efficiency
    to P2 depth-only and P2 combined.
    """
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
        })
    rows.sort(key=lambda r: r["efficiency_axis"])
    return rows


def _reach_bucket_records(
    arm_results: dict[str, list[PolicyReachResult]],
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
    arm_results: dict[str, list[PolicyReachResult]],
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
    arm_results: dict[str, list[PolicyReachResult]],
) -> list[dict[str, Any]]:
    """Cost-safety axis records (max pool / latency multipliers across arms)."""
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
    arm_results: dict[str, list[PolicyReachResult]],
    pool_cost_exceeded: bool, latency_cost_exceeded: bool,
    hard_cap_violation_count: int,
    retrieval_policy_executed: bool,
    baseline_reach: int, depth_reference_reach: int,
    baseline_reach_drift: bool, depth_reference_reach_drift: bool,
) -> list[dict[str, Any]]:
    """One stop/go row describing the P3 constrained retrieval policy
    decision.

    Pass only if ALL research success gates hold:
      1. Reach preservation.
      2. Cost safety (pool <= 4x, latency <= 2x, hard cap violations=0).
      3. Policy efficiency (better than P2 combined, not materially
         worse than P2 depth-only).
      4. Selector relevance remains (gold reachable but often below
         final budget).
    """
    if (not retrieval_policy_executed or denominator_count == 0
            or baseline_reach_drift or depth_reference_reach_drift):
        return [{
            "stop_go_decision": "no_go_p3_replay_mismatch",
            "stop_go_reason": (
                "retrieval_policy_not_executed_or_replay_drift_or_zero_denom"),
            "newly_reachable_count": 0,
            "availability_lift": 0.0,
            "pool_cost_exceeded": bool(pool_cost_exceeded),
            "latency_cost_exceeded": bool(latency_cost_exceeded),
            "hard_cap_violation_count": int(hard_cap_violation_count),
            "runtime_clean_policy_dominates": False,
            "selector_problem_remains": False,
            "reach_preservation_min": P3_REACH_PRESERVATION_NEWLY_MIN,
            "reach_preservation_depth_ratio": P3_REACH_PRESERVATION_DEPTH_RATIO,
            "pool_mult_max": P3_POOL_MULT_MAX,
            "latency_mult_max": P3_LATENCY_MULT_MAX,
            "hard_cap_violation_max": P3_HARD_CAP_VIOLATION_MAX,
            "efficiency_vs_depth_ratio": P3_EFFICIENCY_VS_DEPTH_RATIO,
            "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
            "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY,
            "selector_relevance_mean_rank_min": P3_SELECTOR_RELEVANCE_MEAN_RANK_MIN,
            "selector_relevance_records_min": P3_SELECTOR_RELEVANCE_RECORDS_MIN,
            "baseline_reach_observed": int(baseline_reach),
            "depth_reference_reach_observed": int(depth_reference_reach),
            "baseline_reach_drift": bool(baseline_reach_drift),
            "depth_reference_reach_drift": bool(depth_reference_reach_drift),
        }]
    baseline = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_rids = {r.private_record_id for r in baseline
                     if r.gold_file_available}
    baseline_pool = (
        statistics.mean([r.candidate_pool_size for r in baseline])
        if baseline else 0.0)
    p3_results = arm_results.get("p3_constrained_depth_policy", [])
    p3_newly = sum(1 for r in p3_results
                   if r.gold_file_available
                   and r.private_record_id not in baseline_rids)
    p3_pool = (
        statistics.mean([r.candidate_pool_size for r in p3_results])
        if p3_results else 0.0)
    added = p3_pool - baseline_pool if baseline_pool > 0 else 0.0
    p3_efficiency = (p3_newly / added) if added > 0 else 0.0
    availability_lift = p3_newly / max(denominator_count, 1)

    # Gate 1: Reach preservation.
    reach_preserved = (
        p3_newly >= P3_REACH_PRESERVATION_NEWLY_MIN
        or p3_newly >= P3_REACH_PRESERVATION_DEPTH_RATIO * V1_P2_DEPTH_NEWLY)
    # Gate 2: Cost safety.
    cost_safe = (
        not pool_cost_exceeded and not latency_cost_exceeded
        and hard_cap_violation_count <= P3_HARD_CAP_VIOLATION_MAX)
    # Gate 3: Policy efficiency.
    efficiency_better_than_combined = (
        p3_efficiency > V1_P2_COMBINED_EFFICIENCY)
    efficiency_not_worse_than_depth = (
        p3_efficiency >= P3_EFFICIENCY_VS_DEPTH_RATIO * V1_P2_DEPTH_EFFICIENCY)
    # Gate 4: Selector relevance remains.
    p3_ranks = [r.first_gold_file_rank for r in p3_results
                if r.first_gold_file_rank > 0]
    rank_mean = statistics.mean(p3_ranks) if p3_ranks else 0.0
    records_above_budget = sum(
        1 for r in p3_results
        if r.first_gold_file_rank > FIXED_BUDGET)
    selector_problem_remains = (
        rank_mean > P3_SELECTOR_RELEVANCE_MEAN_RANK_MIN
        or records_above_budget >= P3_SELECTOR_RELEVANCE_RECORDS_MIN)
    runtime_clean_dominates = p3_newly > 0

    if not cost_safe:
        decision = "no_go_p3_cost_exceeded"
        reason = (
            f"pool_or_latency_or_hard_cap_exceeded; "
            f"p3_newly={p3_newly}; pool_cost_exceeded={pool_cost_exceeded}; "
            f"latency_cost_exceeded={latency_cost_exceeded}; "
            f"hard_cap_violations={hard_cap_violation_count}")
    elif not reach_preserved:
        decision = "no_go_p3_reach_not_preserved"
        reason = (
            f"reach_not_preserved; p3_newly={p3_newly}; "
            f"min={P3_REACH_PRESERVATION_NEWLY_MIN}; "
            f"depth_ratio_target="
            f"{P3_REACH_PRESERVATION_DEPTH_RATIO * V1_P2_DEPTH_NEWLY:.2f}; "
            f"availability_lift={availability_lift:.6f}")
    elif not (efficiency_better_than_combined
              and efficiency_not_worse_than_depth):
        decision = "no_go_p3_policy_degenerate"
        reason = (
            f"policy_efficiency_degenerate; p3_eff={p3_efficiency:.6f}; "
            f"combined={V1_P2_COMBINED_EFFICIENCY:.6f}; "
            f"depth={V1_P2_DEPTH_EFFICIENCY:.6f}; "
            f"better_than_combined={efficiency_better_than_combined}; "
            f"not_worse_than_depth={efficiency_not_worse_than_depth}")
    elif not runtime_clean_dominates:
        decision = "no_go_p3_policy_degenerate"
        reason = "no_runtime_clean_policy_dominance"
    elif not selector_problem_remains:
        decision = "no_go_p3_policy_degenerate"
        reason = (
            "policy_leaves_no_selector_problem; "
            "gold_reachable_but_rank_too_low_for_selector_value")
    else:
        decision = "bea_v1_p3_constrained_retrieval_policy_pass"
        reason = (
            f"constrained_policy_pass; p3_newly={p3_newly}; "
            f"availability_lift={availability_lift:.6f}; "
            f"p3_eff={p3_efficiency:.6f}; "
            f"selector_problem_remains=True")
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "newly_reachable_count": int(p3_newly),
        "availability_lift": round(availability_lift, 6),
        "pool_cost_exceeded": bool(pool_cost_exceeded),
        "latency_cost_exceeded": bool(latency_cost_exceeded),
        "hard_cap_violation_count": int(hard_cap_violation_count),
        "runtime_clean_policy_dominates": bool(runtime_clean_dominates),
        "selector_problem_remains": bool(selector_problem_remains),
        "reach_preservation_min": P3_REACH_PRESERVATION_NEWLY_MIN,
        "reach_preservation_depth_ratio": P3_REACH_PRESERVATION_DEPTH_RATIO,
        "pool_mult_max": P3_POOL_MULT_MAX,
        "latency_mult_max": P3_LATENCY_MULT_MAX,
        "hard_cap_violation_max": P3_HARD_CAP_VIOLATION_MAX,
        "efficiency_vs_depth_ratio": P3_EFFICIENCY_VS_DEPTH_RATIO,
        "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
        "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY,
        "selector_relevance_mean_rank_min": P3_SELECTOR_RELEVANCE_MEAN_RANK_MIN,
        "selector_relevance_records_min": P3_SELECTOR_RELEVANCE_RECORDS_MIN,
        "p3_efficiency": round(p3_efficiency, 6),
        "p3_first_gold_rank_mean": round(rank_mean, 6),
        "p3_records_first_gold_rank_above_budget": int(records_above_budget),
        "baseline_reach_observed": int(baseline_reach),
        "depth_reference_reach_observed": int(depth_reference_reach),
        "baseline_reach_drift": bool(baseline_reach_drift),
        "depth_reference_reach_drift": bool(depth_reference_reach_drift),
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
           float(P3_HARD_CAP_VIOLATION_MAX),
           hard_cap_violation_count <= P3_HARD_CAP_VIOLATION_MAX),
        _g("blocking_failure_count", float(blocking_failure_count), "==",
           0.0, blocking_failure_count == 0),
        _g("baseline_reach_reproduced", float(baseline_reach),
           "within_tolerance",
           float(V1_P2_BASELINE_REACH), baseline_in_tol),
        _g("depth_reference_reach_reproduced", float(depth_reference_reach),
           "within_tolerance",
           float(V1_P2_DEPTH_REACH), depth_in_tol),
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
    stop_go_decision: str,
) -> str:
    if blocking_failure_count > 0:
        return "fail_schema_contract"
    if not audit_match:
        return "unavailable_with_reason"
    if (not fd1_private_decomposition_parsed
            or not replay_artifact_validated
            or denominator_count != EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR
            or baseline_reach_drift or depth_reference_reach_drift):
        return "no_go_p3_replay_mismatch"
    if not retrieval_policy_executed:
        return "no_go_p3_replay_mismatch"
    # Map stop_go_decision to status.
    if stop_go_decision == "bea_v1_p3_constrained_retrieval_policy_pass":
        return "bea_v1_p3_constrained_retrieval_policy_pass"
    if stop_go_decision == "no_go_p3_cost_exceeded":
        return "no_go_p3_cost_exceeded"
    if stop_go_decision == "no_go_p3_reach_not_preserved":
        return "no_go_p3_reach_not_preserved"
    if stop_go_decision == "no_go_p3_policy_degenerate":
        return "no_go_p3_policy_degenerate"
    if stop_go_decision == "no_go_p3_replay_mismatch":
        return "no_go_p3_replay_mismatch"
    return "no_go_p3_policy_degenerate"


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
        "policy_action_records": [],
        "policy_stop_reason_records": [],
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
            baseline_reach_drift=False,
            depth_reference_reach_drift=False,
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
                "bea_v1_p3_constrained_retrieval_policy_smoke_unavailable",
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
            "is_candidate_availability_reach_smoke": False,
            "is_constrained_retrieval_policy_smoke": True,
            "is_latency_in_relevance": False,
        },
    }
    scan = _v1_p3_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_policy_report(
    *, self_test_passed: bool, self_test_checks_total: int,
    self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any],
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
    fd1_committed_manifest_hash: str,
    pt: bea_v1_p1.ParsedPrivateDecomposition | None,
    rav: bea_v1_p1.Fd1ReplayArtifactValidation | None,
    denominator: list[bea_v1_p2.DenominatorRecord],
    arm_results: dict[str, list[PolicyReachResult]],
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
    # Hard cap violations (p3 arm only).
    p3_results = arm_results.get("p3_constrained_depth_policy", [])
    hard_cap_violation_count = sum(
        1 for r in p3_results
        if r.candidate_pool_size > P3_HARD_CANDIDATE_CAP)

    # Baseline / depth reference reach (for drift gates).
    baseline_results = arm_results.get("current_bea_candidate_pool_replay", [])
    baseline_reach = sum(1 for r in baseline_results if r.gold_file_available)
    depth_ref_results = arm_results.get("p2_depth_only_reference", [])
    depth_reference_reach = sum(
        1 for r in depth_ref_results if r.gold_file_available)
    baseline_reach_drift = (
        retrieval_policy_executed
        and abs(baseline_reach - V1_P2_BASELINE_REACH)
        > V1_P2_BASELINE_REACH_TOLERANCE)
    depth_reference_reach_drift = (
        retrieval_policy_executed
        and abs(depth_reference_reach - V1_P2_DEPTH_REACH)
        > V1_P2_DEPTH_REACH_TOLERANCE)
    if baseline_reach_drift:
        fcc["baseline_reach_drift"] = max(fcc.get("baseline_reach_drift", 0), 1)
    if depth_reference_reach_drift:
        fcc["depth_reference_reach_drift"] = max(
            fcc.get("depth_reference_reach_drift", 0), 1)

    stop_go = _stop_go_records(
        denominator_count=denominator_count,
        arm_results=arm_results,
        pool_cost_exceeded=pool_cost_exceeded,
        latency_cost_exceeded=latency_cost_exceeded,
        hard_cap_violation_count=hard_cap_violation_count,
        retrieval_policy_executed=retrieval_policy_executed,
        baseline_reach=baseline_reach,
        depth_reference_reach=depth_reference_reach,
        baseline_reach_drift=baseline_reach_drift,
        depth_reference_reach_drift=depth_reference_reach_drift,
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
        stop_go_decision=stop_go[0]["stop_go_decision"] if stop_go else "",
    )

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["fd1_artifact_read"] = True
    safe_true["bea_v1_p3_policy_smoke_performed"] = retrieval_policy_executed
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
        "policy_action_records": _policy_action_records(arm_results),
        "policy_stop_reason_records": _policy_stop_reason_records(arm_results),
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
                "bea_v1_p3_constrained_retrieval_policy_smoke_aggregate_only",
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
            "is_candidate_availability_reach_smoke": False,
            "is_constrained_retrieval_policy_smoke": True,
            "is_latency_in_relevance": False,
        },
    }
    scan = _v1_p3_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Real policy runner (network + openlocus + FD1 private replay)
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


def _run_policy_smoke(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    fd1_artifact_path: Path,
    fd1_private_decomposition_jsonl: Path | None,
    fd1_replay_artifact: Path | None,
    enable_network: bool,
) -> dict[str, Any]:
    """Run the full P3 policy smoke: validate FD1 replay, extract
    denominator, rerun the constrained retrieval policy on denominator
    records, build the public report. No provider calls.
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

    arm_results: dict[str, list[PolicyReachResult]] = {
        arm: [] for arm in POLICY_ARMS}
    private_policy_manifest: dict[str, Any] | None = None
    retrieval_policy_executed = False
    if (enable_network and audit_match
            and _fd1_private_decomposition_parsed_check(pt, rav)
            and len(denominator) == EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR):
        try:
            arm_results, policy_fcc, private_policy_manifest = (
                _execute_retrieval_policy(
                    openlocus_bin=openlocus_bin,
                    denominator=denominator,
                ))
            for k, v in policy_fcc.items():
                if k in fcc:
                    fcc[k] += v
            retrieval_policy_executed = True
        except Exception:
            fcc["retrieval_policy_failed"] = 1
            fcc["unexpected_exception"] = 1
    elif not enable_network:
        fcc["network_required_but_disabled"] = 1

    aggregate_runtime_seconds = time.perf_counter() - start

    return _build_policy_report(
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
            [private_policy_manifest] if private_policy_manifest is not None
            else []
        ),
        retrieval_policy_executed=retrieval_policy_executed,
        audit_match=audit_match,
        audit_mismatch_reason=audit_mismatch_reason,
        failure_category_counts=fcc,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
    )


def _execute_retrieval_policy(
    *, openlocus_bin: str,
    denominator: list[bea_v1_p2.DenominatorRecord],
) -> tuple[dict[str, list[PolicyReachResult]], dict[str, int], dict[str, Any]]:
    """Execute the constrained retrieval policy on denominator records.

    Fetches the source benchmark rows, clones repos, and runs the 3
    policy arms. Returns ``(arm_results, fcc, policy_manifest)``. No
    provider calls.
    """
    fcc: dict[str, int] = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    arm_results: dict[str, list[PolicyReachResult]] = {
        arm: [] for arm in POLICY_ARMS}
    policy_manifest: dict[str, Any] = {
        "manifest_name": "bea_v1_p3_private_policy_manifest",
        "schema_version": "bea_v1_p3_private_policy.v1",
        "storage_class": "private_tmp_only",
        "record_count": 0,
        "records_written": False,
        "path_publicly_serialized": False,
        "manifest_hash": "",
    }
    try:
        private_policy_dir = _resolve_private_policy_dir()
        private_policy_path = (
            private_policy_dir / "bea_v1_p3.private_policy.jsonl")
        if private_policy_path.exists():
            private_policy_path.unlink()
    except Exception:
        private_policy_path = None
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

            with tempfile.TemporaryDirectory(prefix=f"v1p3_{bm}_{idx}_") as rds:
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

                # Arm 1: baseline.
                rr_base = _run_baseline_arm(
                    openlocus_bin=openlocus_bin, repo_root=repo_root,
                    query=query, gold_set=gold_set)
                rr_base.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                arm_results["current_bea_candidate_pool_replay"].append(rr_base)
                # Arm 2: depth reference.
                rr_depth = _run_depth_reference_arm(
                    openlocus_bin=openlocus_bin, repo_root=repo_root,
                    query=query, gold_set=gold_set)
                rr_depth.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                arm_results["p2_depth_only_reference"].append(rr_depth)
                # Arm 3: P3 constrained policy.
                rr_p3 = _run_p3_constrained_policy_arm(
                    openlocus_bin=openlocus_bin, repo_root=repo_root,
                    query=query, gold_set=gold_set)
                rr_p3.private_record_id = f"{d.source_phase}:{d.private_record_id}"
                arm_results["p3_constrained_depth_policy"].append(rr_p3)

                if private_policy_path is not None:
                    for rr in (rr_base, rr_depth, rr_p3):
                        try:
                            _append_private_jsonl(private_policy_path, {
                                "schema_version":
                                    "bea_v1_p3_private_policy.v1",
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
                                "policy_action": rr.policy_action,
                                "policy_stop_reason": rr.policy_stop_reason,
                                "hard_cap_hit": rr.hard_cap_hit,
                                "unique_file_cap_hit": rr.unique_file_cap_hit,
                                "extra_depth_round_executed":
                                    rr.extra_depth_round_executed,
                                "under_retrieval_triggered":
                                    rr.under_retrieval_triggered,
                                "marginal_yield_new_files":
                                    rr.marginal_yield_new_files,
                                "baseline_unique_file_count":
                                    rr.baseline_unique_file_count,
                                "final_unique_file_count":
                                    rr.final_unique_file_count,
                                "triggered_conditions_private":
                                    rr.triggered_conditions_private,
                                "config_hash": _config_hash(),
                            })
                        except Exception:
                            fcc["retrieval_policy_failed"] += 1
                    if rr_p3.retrieval_error:
                        fcc["retrieval_policy_failed"] += 1

    if private_policy_path is not None:
        policy_manifest = _private_file_manifest(
            private_policy_path,
            manifest_name="bea_v1_p3_private_policy_manifest",
            schema_version="bea_v1_p3_private_policy.v1",
        )
    return arm_results, fcc, policy_manifest


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
    """Delegate to P2's synthetic private decomposition JSONL builder
    (identical schema, real FD1 record-id format)."""
    return bea_v1_p2._build_synthetic_private_decomposition_jsonl(
        path,
        gold_file_absent_count=gold_file_absent_count,
        recoverable_lower_bound=recoverable_lower_bound,
    )


def _build_synthetic_policy_results(
    denominator_count: int = EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR,
    baseline_available: int = V1_P2_BASELINE_REACH,
    depth_available: int = V1_P2_DEPTH_REACH,
    p3_available: int = V1_P2_DEPTH_REACH,
) -> dict[str, list[PolicyReachResult]]:
    """Build synthetic policy results for self-test.

    Baseline reaches ``baseline_available`` (32). Depth reference
    reaches ``depth_available`` (59). P3 constrained policy reaches
    ``p3_available`` (59 by default -- preserves depth-only gain) with
    bounded pool (40, between baseline 20 and depth 68) and bounded
    latency (2.0s, between baseline 1.8 and depth 2.12).
    """
    arm_results: dict[str, list[PolicyReachResult]] = {
        arm: [] for arm in POLICY_ARMS}
    for i in range(denominator_count):
        rid = f"contextbench-{i}"
        # Baseline arm.
        rr_base = PolicyReachResult(
            arm_name="current_bea_candidate_pool_replay",
            private_record_id=rid)
        rr_base.candidate_pool_size = 20
        rr_base.retrieval_latency_seconds = 1.8
        rr_base.policy_action = "baseline_only"
        rr_base.policy_stop_reason = "baseline_arm"
        rr_base.baseline_unique_file_count = 13
        rr_base.final_unique_file_count = 13
        if i < baseline_available:
            rr_base.gold_file_available = True
            rr_base.first_gold_file_rank = 12
            rr_base.gold_file_rank_band = _reach_rank_band(12)
        arm_results["current_bea_candidate_pool_replay"].append(rr_base)
        # Depth reference arm.
        rr_depth = PolicyReachResult(
            arm_name="p2_depth_only_reference",
            private_record_id=rid)
        rr_depth.candidate_pool_size = 68
        rr_depth.retrieval_latency_seconds = 2.12
        rr_depth.policy_action = "depth_reference_only"
        rr_depth.policy_stop_reason = "depth_reference_arm"
        rr_depth.baseline_unique_file_count = 44
        rr_depth.final_unique_file_count = 44
        if i < depth_available:
            rr_depth.gold_file_available = True
            rr_depth.first_gold_file_rank = 27
            rr_depth.gold_file_rank_band = _reach_rank_band(27)
        arm_results["p2_depth_only_reference"].append(rr_depth)
        # P3 constrained policy arm.
        rr_p3 = PolicyReachResult(
            arm_name="p3_constrained_depth_policy",
            private_record_id=rid)
        # P3 pool bounded at 40 (between baseline 20 and depth 68),
        # well under hard cap (100) and pool mult (2.0x <= 4.0x).
        rr_p3.candidate_pool_size = 40
        rr_p3.retrieval_latency_seconds = 2.0  # <= 2x baseline (1.8)
        rr_p3.policy_action = "extra_depth_triggered"
        rr_p3.policy_stop_reason = "extra_depth_round_executed"
        rr_p3.extra_depth_round_executed = True
        rr_p3.under_retrieval_triggered = True
        rr_p3.marginal_yield_new_files = 18
        rr_p3.baseline_unique_file_count = 13
        rr_p3.final_unique_file_count = 31
        if i < p3_available:
            rr_p3.gold_file_available = True
            # First-gold rank > budget (5) so selector problem remains.
            rr_p3.first_gold_file_rank = 18
            rr_p3.gold_file_rank_band = _reach_rank_band(18)
        arm_results["p3_constrained_depth_policy"].append(rr_p3)
    return arm_results


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic FD1 + synthetic policy results)
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
                 "bea_v1_p3_audit_evaluator_no_provider_calls",
                 "bea_v1_p3_audit_evaluator_no_selector_executed",
                 "bea_v1_p3_audit_evaluator_no_weight_tuning",
                 "bea_v1_p3_audit_evaluator_no_role_proxy",
                 "bea_v1_p3_audit_evaluator_latency_not_in_relevance"):
        checks.append(_check(f"safe_true_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is True))
    for flag in ("fd1_private_decomposition_parsed",
                 "fd1_private_decomposition_replay_supplied",
                 "fd1_private_decomposition_replay_validated",
                 "fd1_private_decomposition_replay_executed_by_workflow",
                 "retrieval_policy_executed",
                 "bea_v1_p3_policy_smoke_performed"):
        checks.append(_check(f"safe_false_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is False))
    for flag in ("role_proxy_assigned",
                 "gold_labels_used_for_query_construction",
                 "gold_labels_used_for_selection",
                 "gold_labels_used_for_policy",
                 "latency_in_candidate_relevance",
                 "query_anchors_used_in_p3_arm",
                 "v1_a_selector_executed",
                 "v04_full_matrix_claimed",
                 "fd2b_executed", "fd2c_executed",
                 "p4_executed", "p5_executed",
                 "b16k_executed",
                 "weights_tuned_during_bea_v1_p3",
                 "algorithm_changed_during_bea_v1_p3",
                 "default_should_change", "promotion_ready",
                 "provider_calls_made"):
        checks.append(_check(f"false_{flag}",
            DEFAULT_FALSE_FLAGS.get(flag) is False))
    checks.append(_check("no_role_proxy_used_field",
        "role_proxy_used" not in SAFE_TRUE_FLAGS))

    # --- G3: Policy arms (3) ---
    checks.append(_check("policy_arms_count_3", len(POLICY_ARMS) == 3))
    for arm in POLICY_ARMS:
        checks.append(_check(f"policy_arm_present_{arm}", arm in POLICY_ARMS))
    checks.append(_check("query_anchors_disabled",
        P3_QUERY_ANCHORS_ENABLED is False))

    # --- G4: Statuses enum ---
    for status in STATUSES:
        checks.append(_check(f"status_enum_{status}", isinstance(status, str)))
    checks.append(_check("statuses_count_8", len(STATUSES) == 8))
    checks.append(_check("allowed_real_run_statuses_count_4",
        len(ALLOWED_REAL_RUN_STATUSES) == 4))
    checks.append(_check("allowed_real_run_statuses_exclude_replay_mismatch",
        "no_go_p3_replay_mismatch" not in ALLOWED_REAL_RUN_STATUSES))

    # --- G5: P3 policy constants ---
    checks.append(_check("hard_cap_100", P3_HARD_CANDIDATE_CAP == 100))
    checks.append(_check("hard_cap_le_120", P3_HARD_CANDIDATE_CAP <= 120))
    checks.append(_check("unique_file_cap_80", P3_UNIQUE_FILE_CAP == 80))
    checks.append(_check("action_budget_1", P3_ACTION_BUDGET_MAX == 1))
    checks.append(_check("marginal_yield_2", P3_MARGINAL_YIELD_MIN == 2))
    checks.append(_check(
        "under_retrieval_unique_file_max_15",
        P3_UNDER_RETRIEVAL_UNIQUE_FILE_MAX == 15))
    checks.append(_check(
        "under_retrieval_dup_rate_min_050",
        P3_UNDER_RETRIEVAL_DUP_FILE_RATE_MIN == 0.50))
    checks.append(_check(
        "under_retrieval_nonempty_channels_max_2",
        P3_UNDER_RETRIEVAL_NONEMPTY_CHANNELS_MAX == 2))
    checks.append(_check(
        "under_retrieval_score_mass_max_5",
        P3_UNDER_RETRIEVAL_SCORE_MASS_MAX == 5.0))

    # --- G6: Research success gates ---
    checks.append(_check("reach_preservation_newly_min_20",
        P3_REACH_PRESERVATION_NEWLY_MIN == 20))
    checks.append(_check("reach_preservation_depth_ratio_075",
        P3_REACH_PRESERVATION_DEPTH_RATIO == 0.75))
    checks.append(_check("pool_mult_max_4", P3_POOL_MULT_MAX == 4.0))
    checks.append(_check("latency_mult_max_2", P3_LATENCY_MULT_MAX == 2.0))
    checks.append(_check("hard_cap_violation_max_0",
        P3_HARD_CAP_VIOLATION_MAX == 0))
    checks.append(_check("efficiency_vs_depth_ratio_080",
        P3_EFFICIENCY_VS_DEPTH_RATIO == 0.80))
    checks.append(_check("selector_relevance_mean_rank_min_5",
        P3_SELECTOR_RELEVANCE_MEAN_RANK_MIN == 5))
    checks.append(_check("selector_relevance_records_min_25",
        P3_SELECTOR_RELEVANCE_RECORDS_MIN == 25))

    # --- G7: Denominator expected 119 ---
    checks.append(_check("expected_denominator_119",
        EXPECTED_GOLD_FILE_ABSENT_DENOMINATOR == 119))

    # --- G8: P2 binding context ---
    checks.append(_check("v1_p2_result_checkpoint",
        V1_P2_RESULT_CHECKPOINT == "930dd48"))
    checks.append(_check("v1_p2_result_status",
        V1_P2_RESULT_STATUS == "no_go_retrieval_reach_latency_or_pool_cost"))
    checks.append(_check("v1_p2_ci_run_id",
        V1_P2_CI_RUN_ID == "28093864524"))
    checks.append(_check("v1_p2_baseline_reach_32",
        V1_P2_BASELINE_REACH == 32))
    checks.append(_check("v1_p2_depth_reach_59",
        V1_P2_DEPTH_REACH == 59))
    checks.append(_check("v1_p2_depth_newly_27",
        V1_P2_DEPTH_NEWLY == 27))
    checks.append(_check("v1_p2_depth_pool_mult_341",
        V1_P2_DEPTH_POOL_MULT == 3.412111))
    checks.append(_check("v1_p2_depth_latency_mult_118",
        V1_P2_DEPTH_LATENCY_MULT == 1.175298))
    checks.append(_check("v1_p2_combined_pool_mult_1013",
        V1_P2_COMBINED_POOL_MULT == 10.127418))
    checks.append(_check("v1_p2_combined_latency_mult_389",
        V1_P2_COMBINED_LATENCY_MULT == 3.893944))
    checks.append(_check("v1_p2_depth_efficiency_positive",
        V1_P2_DEPTH_EFFICIENCY > 0))
    checks.append(_check("v1_p2_combined_efficiency_positive",
        V1_P2_COMBINED_EFFICIENCY > 0))
    checks.append(_check("v1_p2_depth_efficiency_better_than_combined",
        V1_P2_DEPTH_EFFICIENCY > V1_P2_COMBINED_EFFICIENCY))

    # --- G9: P1 binding context ---
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

    # --- G10: Policy diagnostics (no gold/private labels) ---
    diag_cands = [
        {"path": "src/a.py", "method": "bm25", "rank": 1,
         "score": 1.0, "normalized_score": 1.0},
        {"path": "src/a.py", "method": "regex", "rank": 1,
         "score": 1.0, "normalized_score": 1.0},
        {"path": "src/b.py", "method": "symbol", "rank": 2,
         "score": 0.5, "normalized_score": 0.5},
        {"path": "src/c.py", "method": "bm25", "rank": 2,
         "score": 0.4, "normalized_score": 0.4},
    ]
    diag = _compute_policy_diagnostics(
        diag_cands, "Fix FooBar in src/a.py handle_request")
    checks.append(_check("diag_unique_file_count_3",
        diag.unique_file_count == 3))
    # bm25/regex/symbol present in input (rrf only derived later, not
    # in the raw input candidates).
    checks.append(_check("diag_nonempty_channels_3",
        diag.nonempty_channels == 3))
    checks.append(_check("diag_method_agreement_1",
        diag.method_agreement_count == 1))  # src/a.py via 2 methods
    checks.append(_check("diag_score_mass_positive",
        diag.score_mass > 0))
    checks.append(_check("diag_score_spread_06",
        diag.score_spread == 0.6))
    checks.append(_check("diag_query_token_count_positive",
        diag.query_token_count > 0))
    checks.append(_check("diag_under_retrieved_true",
        diag.under_retrieved is True))
    checks.append(_check("diag_triggered_low_unique_file",
        "low_unique_file_count" in diag.triggered_conditions))
    # Empty pool diagnostics.
    empty_diag = _compute_policy_diagnostics([], "query")
    checks.append(_check("empty_diag_unique_0",
        empty_diag.unique_file_count == 0))
    checks.append(_check("empty_diag_under_retrieved_true",
        empty_diag.under_retrieved is True))
    checks.append(_check("empty_diag_triggered_empty_pool",
        "empty_pool" in empty_diag.triggered_conditions))

    # --- G11: Denominator extraction (delegated to P2) ---
    with tempfile.TemporaryDirectory(prefix="v1p3_st_") as sd:
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

    # --- G12: Forbidden scanner ---
    safe_sample = {
        "schema_version": SCHEMA_VERSION,
        "status": "bea_v1_p3_constrained_retrieval_policy_pass",
        "arm_reach_records": [
            {"arm_name": "current_bea_candidate_pool_replay",
             "denominator_record_count": 119,
             "gold_file_available_any_pool": 32,
             "newly_reachable_count": 0},
        ],
        "arm_cost_records": [
            {"arm_name": "p3_constrained_depth_policy",
             "cost_axis": "pool_size_multiplier",
             "cost_class": "ok", "value": 2.0, "threshold": 4.0},
        ],
        "policy_action_records": [
            {"policy_action": "extra_depth_triggered",
             "record_count": 100},
        ],
        "policy_stop_reason_records": [
            {"stop_reason": "extra_depth_round_executed",
             "record_count": 100},
        ],
        "efficiency_records": [
            {"efficiency_axis":
                "p3_constrained_depth_policy_newly_per_added_candidate",
             "efficiency_class": "ok", "value": 0.5,
             "p2_combined_efficiency": V1_P2_COMBINED_EFFICIENCY,
             "p2_depth_efficiency": V1_P2_DEPTH_EFFICIENCY},
        ],
        "stop_go_records": [{
            "stop_go_decision":
                "bea_v1_p3_constrained_retrieval_policy_pass",
            "stop_go_reason": "test",
            "newly_reachable_count": 27,
            "availability_lift": 0.226891,
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
            "bea_v1_p3_constrained_retrieval_policy_smoke_aggregate_only"},
        "fd1_source_artifact_hash": "b" * 64,
        "v1_p2_result_checkpoint": V1_P2_RESULT_CHECKPOINT,
        "config_hash": "c" * 64,
    }
    checks.append(_check("scanner_allows_safe", not _scan_v1_p3(safe_sample)))
    # Forbidden leaks.
    for fk in ("private_trace_dir", "per_record_reach",
               "per_record_policy", "per_record_diagnostics",
               "per_record_actions", "per_record_stop_reason",
               "candidate_paths", "candidate_keys", "query_text",
               "queries", "query_variants",
               "gold_paths", "gold_lines", "gold_files", "gold_match_labels",
               "snippets", "selected_order", "private_record_id",
               "private_record_ids", "repo_url", "base_commit",
               "raw_policy_row", "raw_diagnostics_row",
               "fd1_replay_artifact_path", "policy_results_path",
               "policy_trace_path", "private_policy_path",
               "winner", "calibration", "method_winner",
               "recommended_default", "ranking", "decision",
               "hard_gates", "failure_category_counts",
               "arm_reach_counts", "arm_cost_counts",
               "policy_action_counts", "policy_stop_reason_counts",
               "efficiency_counts", "self_test_checks",
               "role_proxy", "role_proxy_assignment",
               "is_v04_repair", "is_fd2_b", "is_fd2_c",
               "is_p4", "is_p5", "is_v031_tuning", "is_b16k",
               "is_dense_quality_mixing", "is_quiver_quality_mixing"):
        leaked = dict(safe_sample)
        leaked[fk] = "leak"
        checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_v1_p3(leaked))))

    # --- G13: Fail-closed enforcement ---
    try:
        _enforce_v1_p3_no_forbidden(safe_sample)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk in ("private_trace_dir", "per_record_policy",
               "gold_paths", "winner", "hard_gates",
               "self_test_checks", "candidate_paths",
               "repo_url", "query_variants",
               "policy_trace_path"):
        leaked = dict(safe_sample)
        leaked[lk] = "leak"
        try:
            _enforce_v1_p3_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # --- G14: Build policy report (synthetic) ---
    fd1_art = _build_synthetic_fd1_artifact()
    priv_jsonl2 = Path(tempfile.mkdtemp(prefix="v1p3_rep_")) / "bea_fd1.decomposition.jsonl"
    _build_synthetic_private_decomposition_jsonl(
        priv_jsonl2, gold_file_absent_count=119,
        recoverable_lower_bound=1)
    pt2 = _parse_private_decomposition_jsonl(priv_jsonl2)
    _compute_file_selector_lower_bound(pt2)
    denominator2 = _extract_denominator_from_private(pt2)
    replay_path = Path(tempfile.mkdtemp(prefix="v1p3_rav_")) / "fd1_replay_report.json"
    _build_synthetic_fd1_replay_artifact(replay_path)
    rav2 = _validate_fd1_replay_artifact(replay_path, "a" * 64)
    arm_results = _build_synthetic_policy_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=59)
    report = _build_policy_report(
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
    # Records-only shape.
    required_tables = (
        "source_run_records", "denominator_records",
        "arm_reach_records", "arm_delta_records",
        "arm_cost_records", "policy_action_records",
        "policy_stop_reason_records", "efficiency_records",
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
               "per_record_policy", "candidate_paths", "gold_paths",
               "query_text", "query_variants", "selected_order",
               "winner", "calibration", "hard_gates",
               "failure_category_counts", "arm_reach_counts",
               "arm_cost_counts", "policy_action_counts",
               "policy_stop_reason_counts", "efficiency_counts",
               "self_test_checks", "repo_url", "base_commit",
               "role_proxy_used", "target_support_proxy_used",
               "is_v04_repair", "is_fd2_b", "is_p4", "is_b16k",
               "is_dense_quality_mixing",
               "policy_trace_path", "private_policy_path"):
        checks.append(_check(f"no_top_level_{ff}", ff not in report))
    # latency_in_candidate_relevance is a binding FALSE flag (must be
    # present and False), NOT a forbidden key.
    checks.append(_check("latency_in_candidate_relevance_false",
        report.get("latency_in_candidate_relevance") is False))
    checks.append(_check("gold_labels_used_for_policy_false",
        report.get("gold_labels_used_for_policy") is False))
    checks.append(_check("query_anchors_used_in_p3_arm_false",
        report.get("query_anchors_used_in_p3_arm") is False))
    checks.append(_check("self_scan_clean", not _scan_v1_p3(report)))

    # --- G15: Records-only natural-key uniqueness ---
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
    checks.append(_check("par_unique", not _check_unique_records(
        report.get("policy_action_records", []), _par_natural_key,
        "policy_action_records")))
    checks.append(_check("psr_unique", not _check_unique_records(
        report.get("policy_stop_reason_records", []), _psr_natural_key,
        "policy_stop_reason_records")))
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

    # --- G16: Synthetic status pass ---
    # 119 denominator, baseline_available=32, p3_available=59 ->
    # p3_newly = 27 >= 20 AND >= 0.75*27 = 20.25 -> reach preserved.
    # pool = 40, baseline_pool = 20 -> pool_mult = 2.0 <= 4.0 ok.
    # latency = 2.0, baseline_latency = 1.8 -> latency_mult = 1.111 <= 2.0 ok.
    # hard_cap_violations = 0 (40 <= 100).
    # p3_eff = 27 / (40 - 20) = 1.35 > combined(0.27) AND >= 0.8*depth(0.56).
    # p3 first_gold_rank_mean = 18 > 5 -> selector problem remains.
    checks.append(_check("synth_status_pass",
        report.get("status")
        == "bea_v1_p3_constrained_retrieval_policy_pass"))
    sgr = report.get("stop_go_records", [{}])[0] if report.get(
        "stop_go_records") else {}
    checks.append(_check("synth_stop_go_pass",
        sgr.get("stop_go_decision")
        == "bea_v1_p3_constrained_retrieval_policy_pass"))
    checks.append(_check("synth_newly_reachable_27",
        sgr.get("newly_reachable_count") == 27))

    # --- G17: Arm reach records (3 arms) ---
    arr_rows = report.get("arm_reach_records", [])
    checks.append(_check("arr_count_3", len(arr_rows) == 3))
    arr_arms = {r.get("arm_name") for r in arr_rows}
    for arm in POLICY_ARMS:
        checks.append(_check(f"arr_has_{arm}", arm in arr_arms))

    # --- G18: Arm cost records (3 arms x 2 axes + 1 hard cap = 7) ---
    acr_rows = report.get("arm_cost_records", [])
    checks.append(_check("acr_count_7", len(acr_rows) == 7))
    # Pool mult for baseline is 1.0 (baseline / baseline).
    baseline_pool_row = [r for r in acr_rows
                         if r.get("arm_name") == "current_bea_candidate_pool_replay"
                         and r.get("cost_axis") == "pool_size_multiplier"]
    checks.append(_check("acr_baseline_pool_mult_1",
        bool(baseline_pool_row)
        and baseline_pool_row[0].get("value") == 1.0))
    # P3 hard cap violation count axis present.
    hard_cap_rows = [r for r in acr_rows
                     if r.get("cost_axis") == "hard_cap_violation_count"]
    checks.append(_check("acr_has_hard_cap_axis", len(hard_cap_rows) == 1))
    checks.append(_check("acr_hard_cap_violations_0",
        hard_cap_rows[0].get("value") == 0.0
        if hard_cap_rows else False))

    # --- G19: Policy action records ---
    par_rows = report.get("policy_action_records", [])
    par_actions = {r.get("policy_action") for r in par_rows}
    checks.append(_check("par_has_extra_depth_triggered",
        "extra_depth_triggered" in par_actions))
    checks.append(_check("par_has_baseline_only",
        "baseline_only" in par_actions))

    # --- G20: Policy stop reason records ---
    psr_rows = report.get("policy_stop_reason_records", [])
    psr_reasons = {r.get("stop_reason") for r in psr_rows}
    checks.append(_check("psr_has_extra_depth_round_executed",
        "extra_depth_round_executed" in psr_reasons))
    checks.append(_check("psr_has_hard_candidate_cap_reached",
        "hard_candidate_cap_reached" in psr_reasons))

    # --- G21: Efficiency records ---
    efr_rows = report.get("efficiency_records", [])
    checks.append(_check("efr_count_2", len(efr_rows) == 2))
    efr_p3 = [r for r in efr_rows
              if "p3_constrained_depth_policy" in r.get("efficiency_axis", "")]
    checks.append(_check("efr_has_p3", len(efr_p3) == 1))
    checks.append(_check("efr_p3_better_than_combined",
        efr_p3[0].get("value") > efr_p3[0].get("p2_combined_efficiency")
        if efr_p3 else False))

    # --- G22: Denominator records ---
    dnr_rows = report.get("denominator_records", [])
    checks.append(_check("dnr_nonempty", len(dnr_rows) > 0))
    total_denom = sum(r.get("denominator_record_count", 0) for r in dnr_rows)
    checks.append(_check("dnr_total_119", total_denom == 119))

    # --- G23: Status decision logic ---
    status_no_replay = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=False,
        replay_artifact_validated=False,
        denominator_count=0,
        retrieval_policy_executed=False,
        pool_cost_exceeded=False,
        latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False,
        depth_reference_reach_drift=False,
        stop_go_decision="no_go_p3_replay_mismatch",
    )
    checks.append(_check("decide_status_no_replay",
        status_no_replay == "no_go_p3_replay_mismatch"))
    status_blocking = _decide_status(
        audit_match=True, blocking_failure_count=1,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_policy_executed=True,
        pool_cost_exceeded=False,
        latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False,
        depth_reference_reach_drift=False,
        stop_go_decision="bea_v1_p3_constrained_retrieval_policy_pass",
    )
    checks.append(_check("decide_status_blocking",
        status_blocking == "fail_schema_contract"))
    status_cost = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_policy_executed=True,
        pool_cost_exceeded=True,
        latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False,
        depth_reference_reach_drift=False,
        stop_go_decision="no_go_p3_cost_exceeded",
    )
    checks.append(_check("decide_status_cost",
        status_cost == "no_go_p3_cost_exceeded"))
    status_reach = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_policy_executed=True,
        pool_cost_exceeded=False,
        latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False,
        depth_reference_reach_drift=False,
        stop_go_decision="no_go_p3_reach_not_preserved",
    )
    checks.append(_check("decide_status_reach",
        status_reach == "no_go_p3_reach_not_preserved"))
    status_degenerate = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_policy_executed=True,
        pool_cost_exceeded=False,
        latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=False,
        depth_reference_reach_drift=False,
        stop_go_decision="no_go_p3_policy_degenerate",
    )
    checks.append(_check("decide_status_degenerate",
        status_degenerate == "no_go_p3_policy_degenerate"))
    status_drift = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        replay_artifact_validated=True,
        denominator_count=119,
        retrieval_policy_executed=True,
        pool_cost_exceeded=False,
        latency_cost_exceeded=False,
        hard_cap_violation_count=0,
        baseline_reach_drift=True,
        depth_reference_reach_drift=False,
        stop_go_decision="bea_v1_p3_constrained_retrieval_policy_pass",
    )
    checks.append(_check("decide_status_baseline_drift",
        status_drift == "no_go_p3_replay_mismatch"))

    # --- G24: Unavailable report ---
    unavail = _build_unavailable_report(
        "network_required_but_disabled", self_test_passed=True,
        openlocus_binary_source="self_test", network_mode="self_test",
    )
    checks.append(_check("unavail_status",
        unavail["status"] == "unavailable_with_reason"))
    checks.append(_check("unavail_scan_clean", not _scan_v1_p3(unavail)))
    for table in required_tables:
        if table in ("gate_records", "private_manifest_records",
                     "failure_category_count_records", "source_run_records",
                     "stop_go_records"):
            checks.append(_check(f"unavail_table_{table}_is_list",
                isinstance(unavail.get(table), list)))
        else:
            checks.append(_check(f"unavail_table_{table}_empty",
                unavail.get(table) == []))

    # --- G25: No-go when reach not preserved ---
    # baseline=32, p3_available=35 -> p3_newly=3 < 20 AND < 0.75*27=20.25.
    arm_results_low = _build_synthetic_policy_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=35)
    report_low = _build_policy_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results_low,
        retrieval_policy_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
    )
    # p3_newly = 35 - 32 = 3 < 20 -> no_go_p3_reach_not_preserved.
    checks.append(_check("low_reach_status_not_preserved",
        report_low.get("status") == "no_go_p3_reach_not_preserved"))
    checks.append(_check("low_reach_stop_go_not_preserved",
        report_low["stop_go_records"][0]["stop_go_decision"]
        == "no_go_p3_reach_not_preserved"))

    # --- G26: No-go when cost exceeded ---
    # pool=200 -> pool_mult = 10 > 4 -> cost exceeded.
    arm_results_cost = _build_synthetic_policy_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=59)
    # Override p3 pool to exceed.
    for rr in arm_results_cost["p3_constrained_depth_policy"]:
        rr.candidate_pool_size = 200
    report_cost = _build_policy_report(
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
        aggregate_runtime_seconds=0.5,
    )
    checks.append(_check("cost_exceeded_status",
        report_cost.get("status") == "no_go_p3_cost_exceeded"))

    # --- G27: No-go when hard cap violations ---
    # p3 pool = 150 > 100 hard cap -> hard_cap_violation_count = 119.
    arm_results_hardcap = _build_synthetic_policy_results(
        denominator_count=119, baseline_available=32,
        depth_available=59, p3_available=59)
    for rr in arm_results_hardcap["p3_constrained_depth_policy"]:
        rr.candidate_pool_size = 150  # > 100 hard cap
    report_hardcap = _build_policy_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=denominator2,
        arm_results=arm_results_hardcap,
        retrieval_policy_executed=True,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
    )
    checks.append(_check("hardcap_status_cost_exceeded",
        report_hardcap.get("status") == "no_go_p3_cost_exceeded"))
    checks.append(_check("hardcap_violation_count_119",
        report_hardcap["stop_go_records"][0]["hard_cap_violation_count"]
        == 119))

    # --- G28: No-go when denominator mismatch ---
    report_mismatch = _build_policy_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd1_committed_manifest_hash="a" * 64,
        pt=pt2, rav=rav2, denominator=[],  # empty denominator
        arm_results={arm: [] for arm in POLICY_ARMS},
        retrieval_policy_executed=False,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
    )
    checks.append(_check("mismatch_status_no_go",
        report_mismatch.get("status") == "no_go_p3_replay_mismatch"))

    # --- G29: Reach bucket + rank band records ---
    rbr_rows = report.get("reach_bucket_records", [])
    checks.append(_check("rbr_records_present", len(rbr_rows) > 0))
    # 3 arms x 6 buckets = 18 rows.
    checks.append(_check("rbr_count_18", len(rbr_rows) == 18))
    rkr_rows = report.get("rank_band_records", [])
    checks.append(_check("rkr_records_present", len(rkr_rows) > 0))
    # 3 arms x 6 bands = 18 rows.
    checks.append(_check("rkr_count_18", len(rkr_rows) == 18))

    # --- G30: Private policy manifest ---
    with tempfile.TemporaryDirectory(prefix="v1p3_manifest_st_") as sd:
        priv = Path(sd) / "policy.jsonl"
        _append_private_jsonl(priv, {"row": 1})
        _append_private_jsonl(priv, {"row": 2})
        pm = _private_file_manifest(
            priv,
            manifest_name="bea_v1_p3_private_policy_manifest",
            schema_version="bea_v1_p3_private_policy.v1",
        )
        checks.append(_check("private_policy_manifest_count_2",
            pm.get("record_count") == 2))
        checks.append(_check("private_policy_manifest_path_not_serialized",
            pm.get("path_publicly_serialized") is False))

    # --- G31: Config hash ---
    ch = _config_hash()
    checks.append(_check("config_hash_64_hex",
        len(ch) == 64 and all(c in "0123456789abcdef" for c in ch)))
    checks.append(_check("config_hash_stable",
        _config_hash() == ch))

    # --- G32: No-provider-calls binding ---
    checks.append(_check("no_provider_calls_field",
        report.get("provider_calls_made") is False))
    checks.append(_check("unavail_no_provider_calls",
        unavail.get("provider_calls_made") is False))

    # --- G33: License fields ---
    for field, expected in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{field}",
            report.get(field) == expected))

    # --- G34: Framing is_constrained_retrieval_policy_smoke ---
    checks.append(_check("framing_is_policy_smoke",
        report.get("framing", {}).get(
            "is_constrained_retrieval_policy_smoke") is True))
    checks.append(_check("framing_not_reach_smoke",
        report.get("framing", {}).get(
            "is_candidate_availability_reach_smoke") is False))
    checks.append(_check("framing_not_v04_repair",
        report.get("framing", {}).get("is_v04_repair") is False))
    checks.append(_check("framing_not_latency_in_relevance",
        report.get("framing", {}).get("is_latency_in_relevance") is False))

    # --- G35: failure_category_count_records covers all audit categories ---
    fccr_cats = {r.get("failure_category")
                 for r in report.get("failure_category_count_records", [])}
    for cat in FAILURE_CATEGORIES_AUDIT:
        checks.append(_check(f"fccr_has_{cat}", cat in fccr_cats))

    # --- G36: cost_safety_records ---
    csr_rows = report.get("cost_safety_records", [])
    checks.append(_check("csr_count_2", len(csr_rows) == 2))
    csr_axes = {r.get("cost_safety_axis") for r in csr_rows}
    checks.append(_check("csr_has_pool_mult",
        "max_pool_size_multiplier" in csr_axes))
    checks.append(_check("csr_has_latency_mult",
        "max_latency_multiplier" in csr_axes))

    # --- G37: CLI surface ---
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
                "--policy-thresholds"):
        checks.append(_check(f"cli_no_{opt}", opt not in option_strings))

    # --- G38: Drift gates fire on baseline/depth drift ---
    # baseline reach = 10 (way below 32, drift > 3).
    arm_results_drift = _build_synthetic_policy_results(
        denominator_count=119, baseline_available=10,
        depth_available=59, p3_available=59)
    report_drift = _build_policy_report(
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
        aggregate_runtime_seconds=0.5,
    )
    checks.append(_check("drift_status_replay_mismatch",
        report_drift.get("status") == "no_go_p3_replay_mismatch"))

    # --- G39: P3 preserves selector problem (first-gold rank > budget) ---
    p3_arr = [r for r in report.get("arm_reach_records", [])
              if r.get("arm_name") == "p3_constrained_depth_policy"]
    checks.append(_check("p3_arr_present", len(p3_arr) == 1))
    if p3_arr:
        checks.append(_check("p3_first_gold_rank_mean_above_budget",
            p3_arr[0].get("first_gold_file_rank_mean") > FIXED_BUDGET))

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
        description="BEA-v1-P3 Constrained Retrieval Policy Smoke")
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
                    help="Path to the OpenLocus binary (for retrieval policy).")
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
        _enforce_v1_p3_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    network_mode = "local_explicit" if enable_network else "disabled_opt_in"

    if not enable_network:
        # Default no-network: honest no_go_p3_replay_mismatch (no fake pass).
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
        _enforce_v1_p3_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real "
              "BEA-v1-P3 constrained retrieval policy smoke.")
        return

    try:
        report = _run_policy_smoke(
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
    if report.get("query_anchors_used_in_p3_arm") is not False:
        report["status"] = "fail_schema_contract"

    _enforce_v1_p3_no_forbidden(report)
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
