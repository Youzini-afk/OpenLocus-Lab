#!/usr/bin/env python3
"""BEA-FD2-A: Direct FD1-Objective Setwise Acquisition Smoke (Public Records-Only).

BEA-FD2-A is the direct algorithmic follow-on after BEA-v0.4-P3 stopped the
role-proxy line. It answers exactly one question:

    Can a setwise selector that directly optimizes frozen FD1 failure-loss
    reduction beat frozen BEA v0.3 on the same bounded external smoke frame,
    without target/support proxies and without quality regression?

This is NOT P4/P5, NOT a full v0.4 matrix, NOT a v0.31/v0.32 weight tweak,
and NOT fresh disjoint validation. It is one bounded algorithm-change smoke
on the same P1/P2/P3 success-quota frame.

Prior-phase binding context: P1 target_proxy_available_rate=0.0 (support
degenerate); P2 support collapsed to 0.0 and selections barely changed;
P3 restored support availability but selections/quality could not hold. FD2-A
pivots away from role proxies entirely. It reads the committed FD1 aggregate
artifact (``category_metric_loss_records`` only) as read-only input, derives
frozen category weights BEFORE evaluation, and uses those weights to score
marginal setwise additions by runtime-clean proxies for FD1 loss reduction.
No role-proxy assignment is used in the treatment; ``role_proxy_used=false``
and ``target_support_proxy_used=false`` are binding invariants that are
self-tested.

Fixed arms (5): bm25_prefix_same_budget, rrf_same_budget,
bea_v0_3_anchor_span_latency, fd1_coverage_only_same_budget (relevance +
coverage/diversity, no FD1 weights), fd1_loss_weighted_setwise_same_budget
(treatment: adds frozen FD1 category weights for file reach, span precision,
novelty/diminishing returns, latency/cost, duplicate penalty). Budget 5;
methods bm25,regex,symbol; candidate pool bm25/regex/symbol + derived RRF.

Weights are frozen before evaluation from committed FD1 aggregate loss
records; no per-record gold labels, no private decomposition rows during
selection, no post-hoc threshold search.

Claim boundary (binding):
* claim_level = bea_fd2a_direct_fd1_objective_setwise_smoke_only
* status: bea_fd2a_direct_fd1_objective_pass | partial_fd1_objective_signal |
  no_go_no_selection_change | no_go_no_fd1_loss_reduction |
  no_go_objective_ablation_only | no_go_quality_regression |
  unavailable_with_reason | fail_forbidden_scan | fail_schema_contract
* mode = bea_fd2a_direct_fd1_objective_setwise_smoke; phase = BEA-FD2-A

Required invariants (binding):
* Eval-local only. No runtime/default/EvidenceCore changes. Does NOT modify
  the FD1 artifact or any prior BEA result files; FD1 aggregate artifact is
  read-only input (category_metric_loss_records only, never private rows).
* No v0.31/v0.32 weight tuning, no dense/graph/QuIVer/provider scope, no
  post-hoc threshold search, no per-repo tuning, no gold/private labels, no
  provider/LLM calls, no role-proxy assignment in the FD2-A treatment.
* Budget fixed at 5. Methods fixed to bm25,regex,symbol.
* Private per-record score / decision / FD1-objective-feature /
  post-hoc-decomposition rows under /tmp only; plus a private objective-config
  JSON (single object, frozen FD1 weights + source artifact hash). Public
  artifact aggregate-only, records-only, fixed enum tables. No public paths.
  No dynamic hard_gates or failure_category_counts dict mirrors (records-only
  tables only).

Network / CI policy (binding):
* Default no-network self-test passes without HuggingFace/GitHub and without
  the committed FD1 artifact (self-test uses synthetic FD1 loss records).
* Real smoke requires public network access AND the committed FD1 artifact.
  CI is a separate explicit workflow_dispatch job with
  enable_external_benchmark_network=true; must NOT run on PR/push by default,
  must use no provider secrets/vars/model env, and must upload only the
  aggregate report. Private JSONL/JSON files are NEVER uploaded.

Run::
    python3 -m py_compile eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py
    python3 eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py --self-test
    python3 eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py \\
        --enable-external-benchmark-network \\
        --fd1-artifact artifacts/bea_fd1_failure_decomposition/\\
bea_fd1_failure_decomposition_report.json \\
        --out artifacts/bea_fd2a_direct_fd1_objective/\\
bea_fd2a_direct_fd1_objective_setwise_smoke_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

# Reuse BEA-3/5 helpers (frozen v0.3 policy + v0.2 controls + scanners),
# BEA-0/1/2 helpers (candidate collection, dedupe, controls, priority), the
# heldout fetchers (BEA-5), the benchmark adapters (c5a/c5d), and the FD1
# evaluator (category enum + scanner composition). FD2-A does NOT import any
# BEA-v0.4-P1/P2/P3 module: the FD2-A treatment does not use role-proxy
# assignment.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea5_frozen_policy_robustness as bea5  # noqa: E402
import bea3_anchor_span_latency as bea3  # noqa: E402
import bea2_policy_v02 as bea2  # noqa: E402
import bea1_mechanism_ablation as bea1  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402
import bea_fd1_failure_decomposition as bea_fd1  # noqa: E402

# --- Schema / claim constants ---
SCHEMA_VERSION = "bea_fd2a_direct_fd1_objective_setwise_smoke.v1"
GENERATED_BY = "eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py"
CLAIM_LEVEL = "bea_fd2a_direct_fd1_objective_setwise_smoke_only"
MODE = "bea_fd2a_direct_fd1_objective_setwise_smoke"
PHASE = "BEA-FD2-A"

DEFAULT_OUT = Path(
    "artifacts/bea_fd2a_direct_fd1_objective/"
    "bea_fd2a_direct_fd1_objective_setwise_smoke_report.json"
)
DEFAULT_FD1_ARTIFACT = Path(
    "artifacts/bea_fd1_failure_decomposition/"
    "bea_fd1_failure_decomposition_report.json"
)

PRIVATE_SCORE_SCHEMA_VERSION = "bea_fd2a_private_score.v1"
PRIVATE_DECISION_SCHEMA_VERSION = "bea_fd2a_private_decision.v1"
PRIVATE_FD1_OBJECTIVE_FEATURE_SCHEMA_VERSION = "bea_fd2a_private_fd1_objective_feature.v1"
PRIVATE_POSTHOC_DECOMPOSITION_SCHEMA_VERSION = "bea_fd2a_private_posthoc_decomposition.v1"
PRIVATE_OBJECTIVE_CONFIG_SCHEMA_VERSION = "bea_fd2a_private_objective_config.v1"

FIXED_BUDGET = 5
FIXED_METHODS = "bm25,regex,symbol"
ALLOWED_METHODS = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

SAMPLING_MODE = "success_quota"
SAMPLING_PROTOCOL_VERSION = "bea_fd2a_direct_fd1_objective_smoke.v1"
SAMPLING_FRAME_POLICY = (
    "full_available_python_excluding_bea2_bea3_bea4_mandatory_windows; "
    "bea5_overlap_disclosed_not_excluded; bea_v04_p1_overlap_disclosed; "
    "bea_v04_p2_overlap_disclosed; bea_v04_p3_overlap_disclosed; "
    "bea_fd2a_reuses_p1_p2_p3_success_quota_frame"
)
EXCLUDED_PRIOR_WINDOWS_POLICY = (
    "mandatory_bea2_bea3_bea4; bea5_overlap_disclosed_not_excluded; "
    "bea_v04_p1_overlap_disclosed_not_excluded; "
    "bea_v04_p2_overlap_disclosed_not_excluded; "
    "bea_v04_p3_overlap_disclosed_not_excluded; bea0_bea1_best_effort_or_disclosed"
)
BEA5_OVERLAP_POLICY = (
    "not_excluded; disclosed; BEA-5 used success-quota over the same full "
    "available Python frame and did not consume the entire frame, so overlap "
    "with BEA-5 evaluated records is possible. This is FD2-A smoke evidence, "
    "not fresh disjoint validation."
)
BEA_V04_P1_OVERLAP_POLICY = (
    "not_excluded; disclosed; FD2-A reuses the P1 frame; P1+FD2-A overlap "
    "possible. Not fresh disjoint validation."
)
BEA_V04_P2_OVERLAP_POLICY = (
    "not_excluded; disclosed; FD2-A reuses the P2 frame; P2+FD2-A overlap "
    "possible. Not fresh disjoint validation."
)
BEA_V04_P3_OVERLAP_POLICY = (
    "not_excluded; disclosed; FD2-A reuses the P3 frame (the role-proxy line "
    "P3 stopped); P3+FD2-A overlap possible. FD2-A does NOT use role proxies. "
    "Not fresh disjoint validation."
)
FD1_OVERLAP_POLICY = (
    "fd1_artifact_read_only_input; FD2-A reads ONLY the public aggregate "
    "category_metric_loss_records from the committed FD1 artifact to derive "
    "frozen category weights before evaluation. No private decomposition rows, "
    "gold labels, or per-record data are read. The FD1 artifact is NOT modified."
)

TARGET_SUCCESSFUL_RECORDS = 38
MIN_CONTEXTBENCH_SUCCESSFUL = 20
MIN_REPOQA_SUCCESSFUL = 10
RAW_ATTEMPT_CAP_CONTEXTBENCH = 480
RAW_ATTEMPT_CAP_REPOQA = 240
CI_MIN_RECORDS_SUCCESSFUL = 30

CONTEXTBENCH_MANDATORY_EXCLUDED_WINDOWS = (
    (40, 60),   # BEA-2
    (60, 80),   # BEA-3
    (80, 160),  # BEA-4
)
REPOQA_MANDATORY_EXCLUDED_WINDOWS = (
    (20, 30),   # BEA-2
    (30, 40),   # BEA-3
    (40, 80),   # BEA-4
)

BUDGET_DEFAULT = 5
BUDGET_HARD_CAP = 20

# Required arms (5; no role-proxy arms, no seeded random, no v0.2/v0 controls,
# no dense/graph/QuIVer/provider arms).
ARM_BM25_PREFIX = "bm25_prefix_same_budget"
ARM_RRF_SAME_BUDGET = "rrf_same_budget"
ARM_BEA_V0_3 = "bea_v0_3_anchor_span_latency"
ARM_FD1_COVERAGE_ONLY = "fd1_coverage_only_same_budget"
ARM_FD1_LOSS_WEIGHTED = "fd1_loss_weighted_setwise_same_budget"

FIXED_ARMS = (
    ARM_BM25_PREFIX,
    ARM_RRF_SAME_BUDGET,
    ARM_BEA_V0_3,
    ARM_FD1_COVERAGE_ONLY,
    ARM_FD1_LOSS_WEIGHTED,
)

TREATMENT_ARM = ARM_FD1_LOSS_WEIGHTED
COVERAGE_ONLY_ARM = ARM_FD1_COVERAGE_ONLY
QUALITY_BASELINE_ARM = ARM_BEA_V0_3
DELTA_BASELINE_ARM = ARM_BEA_V0_3

ARM_METRIC_ALLOWLIST = (
    "file_recall@10", "mrr", "span_f0.5@10", "success_rate",
    "candidate_count_read", "evidence_budget_used", "action_steps",
    "latency_seconds", "quality_per_candidate", "quality_per_latency",
)
PRIMARY_METRICS = ("file_recall@10", "mrr", "span_f0.5@10", "success_rate")

# FD1 plan categories (5). Four are derivable from FD1 aggregate loss
# records; redundant_same_file_candidates is unavailable_missing_trace in FD1
# and uses a fixed default weight (not derived from outcomes).
FD1_PLAN_CATEGORIES = (
    "gold_file_absent",
    "correct_file_wrong_span",
    "budget_spent_on_low_marginal_gain",
    "latency_without_quality_gain",
    "redundant_same_file_candidates",
)
FD1_DERIVABLE_CATEGORIES = frozenset({
    "gold_file_absent", "correct_file_wrong_span",
    "budget_spent_on_low_marginal_gain", "latency_without_quality_gain",
})
# Fixed default weight for the FD1 category unavailable_missing_trace in FD1.
FD1_FIXED_DUPLICATE_WEIGHT = 0.10

# FD1-objective components (5). Each maps to one FD1 plan category weight.
FD1_OBJECTIVE_COMPONENTS = (
    "file_reach",                    # <- gold_file_absent weight
    "span_precision",                # <- correct_file_wrong_span weight
    "novelty_diminishing_returns",   # <- budget_spent_on_low_marginal_gain
    "latency_cost",                  # <- latency_without_quality_gain (penalty)
    "duplicate_penalty",             # <- redundant_same_file_candidates (penalty)
)
FD1_CATEGORY_TO_COMPONENT = {
    "gold_file_absent": "file_reach",
    "correct_file_wrong_span": "span_precision",
    "budget_spent_on_low_marginal_gain": "novelty_diminishing_returns",
    "latency_without_quality_gain": "latency_cost",
    "redundant_same_file_candidates": "duplicate_penalty",
}
FD1_PENALTY_COMPONENTS = frozenset({"latency_cost", "duplicate_penalty"})

# Hard gates (FD2-A direct FD1-objective setwise smoke).
GATE_SETWISE_DIFF_VS_V03 = 0.25
GATE_SETWISE_DIFF_VS_COVERAGE = 0.15
GATE_QUALITY_MARGIN_FILE_RECALL = 0.03
GATE_QUALITY_MARGIN_MRR = 0.05
GATE_QUALITY_MARGIN_SPAN = 0.02
GATE_LATENCY_RATIO = 1.15

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "bea_v03_policy_executed": False,
    "fd2a_policy_executed": False,
    "coverage_only_policy_executed": False,
    "role_proxy_used": False,
    "target_support_proxy_used": False,
    "setwise_selection_performed": False,
    "bounded_smoke_frame_read": False,
    "private_score_records_written": False,
    "private_decision_records_written": False,
    "private_fd1_objective_feature_records_written": False,
    "private_posthoc_decomposition_records_written": False,
    "private_objective_config_written": False,
    "fd1_artifact_read": False,
    "fd1_weights_derived": False,
    "fd1_artifact_modified": False,
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
    "algorithm_changed_during_bea_fd2a": False,
    "weights_tuned_during_bea_fd2a": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_fd2a": False,
    "fd1_artifact_modified": False,
    "role_proxy_assigned": False,
    "posthoc_threshold_search": False,
    "private_decomposition_used_for_selection": False,
    "gold_labels_used_for_selection": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_smoke",
}

FAILURE_CATEGORIES = (
    "contextbench_fetch_failed", "contextbench_no_python_rows",
    "contextbench_label_parse_failed", "repoqa_asset_download_failed",
    "repoqa_asset_decompress_failed", "repoqa_asset_parse_failed",
    "repoqa_no_python_needles", "repoqa_needle_parse_failed",
    "heldout_offset_exceeds_available", "repo_clone_failed",
    "repo_checkout_failed", "materialization_failed", "retrieval_failed",
    "scoring_unavailable", "rrf_required_but_missing", "fd1_artifact_missing",
    "fd1_loss_records_missing", "score_failed", "private_score_write_failed",
    "private_decision_write_failed",
    "private_fd1_objective_feature_write_failed",
    "private_posthoc_decomposition_write_failed",
    "private_objective_config_write_failed",
    "record_excluded_from_paired_denominator", "row_limit_capped",
    "needle_limit_capped", "quota_reached_stop", "scanner_self_test_failed",
    "forbidden_leak_blocked", "duplicate_record_key_blocked",
    "unexpected_exception",
)
BLOCKING_FAILURE_CATEGORIES = (
    "private_score_write_failed", "private_decision_write_failed",
    "private_fd1_objective_feature_write_failed",
    "private_posthoc_decomposition_write_failed",
    "private_objective_config_write_failed", "forbidden_leak_blocked",
    "unexpected_exception",
)

# --- Scanner (strict, fail-closed). Composes FD1 scanner; adds role-proxy /
# per-record / FD1-private / dynamic-dict rejections. ---
FD2A_FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        # role-proxy fields (FD2-A does NOT use role proxies).
        "role_proxy", "role_proxy_assignment", "target_proxy",
        "support_proxy", "target_proxy_score", "support_proxy_score",
        "target_anchor", "target_support_pair",
        "per_record_role_labels", "p1_role_assignment",
        "p2_role_assignment", "p3_role_assignment",
        "fd2a_role_assignment", "role_proxy_summary",
        "role_proxy_bucket_counts", "role_proxy_available_rate",
        "target_proxy_available_rate", "support_proxy_available_rate",
        # per-record / private
        "private_record_id", "private_record_hash",
        "private_score_path", "score_path", "private_score_file",
        "private_decision_path", "decision_path", "private_decision_file",
        "private_decision_id", "decision_id",
        "private_fd1_objective_feature_path", "fd1_objective_feature_path",
        "private_fd1_objective_feature_file", "fd1_objective_feature_id",
        "private_posthoc_decomposition_path", "posthoc_decomposition_path",
        "private_posthoc_decomposition_file", "posthoc_decomposition_id",
        "private_objective_config_path", "objective_config_path",
        "action_order", "priority_components", "priority_score",
        "selected_decisions", "budget_trace", "stop_reason",
        "candidate_features", "anchor_eligibility", "anchor_slots",
        "early_stop_reason", "score_outcome", "action_trace",
        "action_steps_trace", "budget_state", "budget_states",
        "accepted_candidates", "final_candidates", "candidate_list",
        "candidates", "per_record_metrics", "runtime_query_features",
        "query_feature_summary", "query_features",
        "fd1_objective_features", "posthoc_decomposition",
        "objective_config", "objective_config_components",
        "fd1_objective_components_per_candidate",
        # FD1 private decomposition
        "decomposition_path", "private_decomposition_path",
        "private_decomposition_file", "decomposition_record_id",
        "per_record_decomposition", "decomposition_rows",
        "gold_paths", "gold_lines", "gold_spans", "gold_content",
        # identifiers
        "benchmark_row_id", "benchmark_record_id", "benchmark_label",
        "phase_run_id", "run_id", "task_id", "row_id", "needle_id",
        "instance_id", "provider_name", "model_name", "model_family",
        "provider_payload", "private_bucket", "route_bucket", "task_bucket",
        # claims
        "calibration", "method_winner", "best_method",
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion",
        # self-test details
        "self_test_checks", "self_test_details", "self_test_list",
        "checks", "check_list",
        # dynamic dict mirrors (forbidden as top-level; records-only tables)
        "hard_gates", "failure_category_counts",
        # FD1 source artifact path (private; only hash/schema serialized)
        "fd1_source_artifact_path",
    }
)
_FD2A_CONTAINER_KEYS = frozenset({
    "failure_category_count_records", "hard_gate_records", "arm_metric_records",
    "arm_delta_records", "win_tie_loss_records",
    "fd1_category_loss_records", "fd1_category_rate_records",
    "fd1_objective_component_records", "ablation_delta_records",
    "setwise_behavior_records", "source_run_records",
    "benchmark_attempt_records", "manifests", "framing",
})


def _is_fd2a_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in _FD2A_CONTAINER_KEYS


def _scan_fd2a_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_fd2a_schema_key_container(sub_path)
                if (key_str in FD2A_FORBIDDEN_EXTRA_KEYS and not is_container):
                    violations.append({
                        "category": "forbidden_fd2a_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_fd2a(obj: Any) -> list[dict[str, Any]]:
    # Compose with the FD1 scanner (which composes with BEA-5/BEA-3) so FD2-A
    # inherits the full prior forbidden-key discipline, then adds its own
    # role-proxy / per-record / FD1-private / dynamic-dict rejections. FD2-A
    # also filters primitive (c5a) false positives for its own legitimate
    # safe value paths (overlap policy strings, FD1 source artifact hash),
    # mirroring how BEA-0 filters with _bea0_safe_value_path.
    violations = bea_fd1._scan_fd1(obj)
    violations.extend(_scan_fd2a_forbidden_keys(obj))
    filtered: list[dict[str, Any]] = []
    for v in violations:
        cat = v.get("category")
        if cat in ("long_string", "hex_digest_value",
                   "forbidden_field_name_value") and _fd2a_safe_value_path(
                v.get("path", "")):
            continue
        filtered.append(v)
    return filtered


# FD2-A-specific safe VALUE path last-key segments. These keys MAY hold long
# policy strings or the FD1 source artifact hash (64-char hex) without
# triggering the primitive long_string / hex_digest_value checks. This
# mirrors BEA0_SAFE_VALUE_PATH_LAST_KEYS.
FD2A_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    {
        "bea5_overlap_policy",
        "bea_v04_p1_overlap_policy",
        "bea_v04_p2_overlap_policy",
        "bea_v04_p3_overlap_policy",
        "fd1_overlap_policy",
        "sampling_frame_policy",
        "excluded_prior_windows_policy",
        "fd1_source_artifact_hash",
        "fd1_source_schema_version",
        "manifest_hash",
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
        "treatment_arm",
        "coverage_only_arm",
        "quality_baseline_arm",
        "delta_baseline_arm",
        "failure_reason_category",
        "signal_strength",
        "storage_class",
        "openlocus_binary_source",
        "network_mode",
        "source_sampling_protocol",
        "sampling_protocol_version",
        "source_artifact_status",
        "source_phase",
        "replay_mismatch_reason",
    }
)


def _fd2a_safe_value_path(path: str) -> bool:
    """Check if a JSON path is an FD2-A-specific safe value path."""
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in FD2A_SAFE_VALUE_PATH_LAST_KEYS


def _fd2a_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_fd2a(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_fd2a_no_forbidden(obj: Any) -> None:
    scan = _fd2a_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


# --- Helpers ---


def _now_iso() -> str:
    return c5a._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    c5a._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5a._check(name, ok)


def _validate_row_offset(offset: int) -> int:
    if not isinstance(offset, int) or offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_needle_offset(offset: int) -> int:
    if not isinstance(offset, int) or offset < 0:
        raise SystemExit("invalid arguments")
    return offset


def _validate_row_limit(limit: int) -> int:
    if not isinstance(limit, int) or limit < 1:
        raise SystemExit("invalid arguments")
    if limit > RAW_ATTEMPT_CAP_CONTEXTBENCH:
        raise SystemExit("invalid arguments")
    return limit


def _validate_needle_limit(limit: int) -> int:
    if not isinstance(limit, int) or limit < 1:
        raise SystemExit("invalid arguments")
    if limit > RAW_ATTEMPT_CAP_REPOQA:
        raise SystemExit("invalid arguments")
    return limit


def _validate_budget(budget: int) -> int:
    if not isinstance(budget, int) or budget < 1:
        raise SystemExit("invalid arguments")
    if budget > BUDGET_HARD_CAP:
        raise SystemExit("invalid arguments")
    return budget


def _validate_methods(methods: str) -> tuple[str, ...]:
    return bea0._validate_methods(methods)


def _validate_fixed_protocol(
    *, contextbench_row_offset: int, contextbench_row_limit: int,
    repoqa_needle_offset: int, repoqa_needle_limit: int, budget: int,
    methods: tuple[str, ...],
) -> None:
    if contextbench_row_offset != 0:
        raise SystemExit("invalid arguments")
    if contextbench_row_limit != RAW_ATTEMPT_CAP_CONTEXTBENCH:
        raise SystemExit("invalid arguments")
    if repoqa_needle_offset != 0:
        raise SystemExit("invalid arguments")
    if repoqa_needle_limit != RAW_ATTEMPT_CAP_REPOQA:
        raise SystemExit("invalid arguments")
    if budget != FIXED_BUDGET:
        raise SystemExit("invalid arguments")
    if tuple(methods) != tuple(ALLOWED_METHODS):
        raise SystemExit("invalid arguments")


# --- Natural-key uniqueness validators ---


def _check_unique_records(
    records: list[dict[str, Any]], key_fn: Any, table_name: str,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if not records:
        return failures
    seen: dict[tuple, int] = {}
    for idx, rec in enumerate(records):
        try:
            key = key_fn(rec)
        except (KeyError, TypeError):
            failures.append({
                "table": table_name, "index": idx,
                "reason": "missing_natural_key",
            })
            continue
        if key in seen:
            failures.append({
                "table": table_name, "index": idx,
                "reason": "duplicate_natural_key",
            })
        else:
            seen[key] = idx
    return failures


def _amr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["arm"], rec["metric"])


def _adr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["baseline_arm"], rec["treatment_arm"], rec["metric"])


def _wtl_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["baseline_arm"], rec["treatment_arm"], rec["metric"])


def _fclr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["policy_arm"], rec["fd1_category"])


def _fcrr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["policy_arm"], rec["fd1_category"])


def _focr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["component"],)


def _abdr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["component"], rec["baseline_arm"], rec["treatment_arm"])


def _sbr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["behavior_field"],)


def _srr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["source_ci_run_id"])


def _man_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["manifest_name"],)


# --- Private manifest writers (5 private files: 4 JSONL + 1 JSON) ---


def _resolve_private_dir(explicit: str | None) -> tuple[Path, str]:
    return bea0._resolve_private_score_dir(explicit)


def _private_score_manifest_hash() -> str:
    schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "policy_arm", "runtime_query_feature_summary",
            "candidate_features", "fd1_objective_components_summary",
            "priority_components", "selected_decisions",
            "action_order", "budget_trace", "anchor_slots",
            "early_stop_reason", "stop_reason", "score_outcome",
            "role_proxy_summary", "latency_ms", "cost_usd", "tokens",
            "provider_calls", "failure_reason",
        ],
    }
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _private_decision_manifest_hash() -> str:
    schema = {
        "schema_version": PRIVATE_DECISION_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "policy_arm", "decision_step", "decision_action",
            "priority_score", "priority_components",
            "fd1_objective_score", "fd1_objective_components",
            "candidate_method", "candidate_rank", "agreement",
            "is_new_file", "is_new_dir", "span_extent",
            "span_proxy_bucket", "decision_reason",
        ],
    }
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _private_fd1_objective_feature_manifest_hash() -> str:
    schema = {
        "schema_version": PRIVATE_FD1_OBJECTIVE_FEATURE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "candidate_key", "policy_arm", "file_reach", "span_precision",
            "novelty_diminishing_returns", "latency_cost",
            "duplicate_penalty", "fd1_objective", "is_new_file",
            "is_new_dir", "agreement", "span_tightness", "rank",
            "feature_reason",
        ],
    }
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _private_posthoc_decomposition_manifest_hash() -> str:
    schema = {
        "schema_version": PRIVATE_POSTHOC_DECOMPOSITION_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "policy_arm", "fd1_category", "category_count",
            "category_availability", "loss", "delta_vs_v03",
            "latency_ms", "cost_usd", "tokens", "provider_calls",
        ],
    }
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _private_objective_config_manifest_hash() -> str:
    schema = {
        "schema_version": PRIVATE_OBJECTIVE_CONFIG_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "fd1_source_artifact_hash",
            "fd1_source_schema_version", "fd1_category_weights",
            "weight_derivation", "total_loss_sum_used", "derived_at",
        ],
    }
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _failure_category_count_records(fcc: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"failure_category": str(k), "count": int(v)}
        for k, v in sorted(fcc.items())
    ]


def _blocking_failure_count(fcc: dict[str, int]) -> int:
    return sum(int(fcc.get(cat, 0)) for cat in BLOCKING_FAILURE_CATEGORIES)


def _write_private_row(path: Path, row: dict[str, Any]) -> None:
    bea0._write_private_score_row(path, row)


def _write_private_objective_config(path: Path, config: dict[str, Any]) -> None:
    """Write the private objective-config JSON (single object, not JSONL)."""
    c5a._write_json(path, config)


# --- FD1 weight derivation (frozen before evaluation from FD1 aggregate loss
# records; read-only input; no private rows / gold labels) ---


def _load_fd1_loss_records(
    fd1_artifact_path: Path,
) -> tuple[list[dict[str, Any]], str, str, str]:
    """Load ONLY the public aggregate ``category_metric_loss_records`` from
    the committed FD1 artifact.

    Returns ``(loss_records, fd1_source_schema_version,
    fd1_source_artifact_hash, status)``. The artifact hash is a SHA-256 of
    the canonical artifact file bytes. Read-only: the FD1 artifact is NEVER
    modified. On failure returns ``([], schema_or_empty, hash_or_empty,
    reason)``; the caller fail-closes.
    """
    if not fd1_artifact_path.exists() or not fd1_artifact_path.is_file():
        return [], "", "", "fd1_artifact_missing"
    try:
        with fd1_artifact_path.open("r", encoding="utf-8") as f:
            artifact = json.load(f)
    except Exception:
        return [], "", "", "fd1_artifact_parse_failed"
    try:
        h = hashlib.sha256()
        with fd1_artifact_path.open("rb") as fb:
            for chunk in iter(lambda: fb.read(65536), b""):
                h.update(chunk)
        artifact_hash = h.hexdigest()
    except Exception:
        artifact_hash = ""
    loss_records = artifact.get("category_metric_loss_records", [])
    if not isinstance(loss_records, list):
        return [], str(artifact.get("schema_version", "")), artifact_hash, "fd1_loss_records_missing"
    schema_ver = str(artifact.get("schema_version", "") or "")
    if not loss_records:
        return [], schema_ver, artifact_hash, "fd1_loss_records_missing"
    return loss_records, schema_ver, artifact_hash, "pass"


def _derive_fd1_category_weights(
    loss_records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Derive frozen FD1 category weights from FD1 aggregate loss records.

    Reads ONLY the public aggregate ``category_metric_loss_records``
    (loss_sum per category, summed across source_phase / benchmark /
    baseline_arm / treatment_arm / metric). Normalizes the four derivable
    categories to sum to 1.0. The fifth category
    (redundant_same_file_candidates) is unavailable_missing_trace in FD1 and
    uses a fixed default weight. Returns ``{category: {"weight": float,
    "loss_sum": float, "derivation": str}}``. Frozen at derivation time; NOT
    tuned from FD2-A outcomes (no post-hoc threshold search).
    """
    loss_by_cat: dict[str, float] = {c: 0.0 for c in FD1_PLAN_CATEGORIES}
    for rec in loss_records:
        if not isinstance(rec, dict):
            continue
        cat = str(rec.get("category", "") or "")
        if cat not in FD1_DERIVABLE_CATEGORIES:
            continue
        try:
            loss_sum = float(rec.get("loss_sum", 0.0) or 0.0)
        except (TypeError, ValueError):
            loss_sum = 0.0
        loss_by_cat[cat] += loss_sum

    total = sum(loss_by_cat[c] for c in FD1_DERIVABLE_CATEGORIES)
    weights: dict[str, dict[str, Any]] = {}
    if total <= 0.0:
        # FD1 artifact present but all derivable loss_sums are zero. Use a
        # fixed uniform fallback so the treatment is still well-defined; this
        # is NOT tuning from outcomes (uniform is the maximum-entropy prior).
        uniform = 1.0 / float(len(FD1_DERIVABLE_CATEGORIES))
        for cat in FD1_DERIVABLE_CATEGORIES:
            weights[cat] = {
                "weight": round(uniform, 6), "loss_sum": 0.0,
                "derivation": "uniform_fallback_no_fd1_loss",
            }
    else:
        for cat in FD1_DERIVABLE_CATEGORIES:
            w = loss_by_cat[cat] / total
            weights[cat] = {
                "weight": round(w, 6),
                "loss_sum": round(loss_by_cat[cat], 6),
                "derivation": "loss_sum_normalized",
            }
    weights["redundant_same_file_candidates"] = {
        "weight": FD1_FIXED_DUPLICATE_WEIGHT,
        "loss_sum": 0.0,
        "derivation": "fixed_default_unavailable_in_fd1",
    }
    return weights


def _build_objective_config(
    *, phase_run_id: str, loss_records: list[dict[str, Any]],
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
) -> dict[str, Any]:
    """Build the private objective-config JSON object (frozen weights)."""
    weights = _derive_fd1_category_weights(loss_records)
    category_weights = {
        cat: float(weights[cat]["weight"]) for cat in FD1_PLAN_CATEGORIES
    }
    total_loss_sum = sum(
        float(weights[cat]["loss_sum"]) for cat in FD1_PLAN_CATEGORIES
    )
    return {
        "schema_version": PRIVATE_OBJECTIVE_CONFIG_SCHEMA_VERSION,
        "phase_run_id": phase_run_id,
        "fd1_source_artifact_hash": fd1_source_artifact_hash,
        "fd1_source_schema_version": fd1_source_schema_version,
        "fd1_category_weights": category_weights,
        "weight_derivation": {
            cat: weights[cat]["derivation"] for cat in FD1_PLAN_CATEGORIES
        },
        "total_loss_sum_used": round(total_loss_sum, 6),
        "derived_at": _now_iso(),
    }


# --- FD1-objective feature computation (per candidate, runtime-clean) ---


def _rank_of(entry: dict[str, Any]) -> int:
    rank = entry.get("first_rank", entry.get("rank", 0))
    try:
        return int(rank) if rank is not None else 0
    except (TypeError, ValueError):
        return 0


def _compute_fd1_objective_components(
    entry: dict[str, Any], query_toks: set[str],
    accepted_paths: set[str], accepted_dirs: set[str],
    accepted_methods: set[str], step: int, budget: int,
) -> dict[str, float]:
    """Compute the 5 runtime-clean FD1-objective components for one candidate.

    Each component is in [0, 1]. latency_cost and duplicate_penalty are
    penalties (higher = worse); the caller subtracts them. No gold labels,
    no private decomposition rows, no role proxies.
    """
    path = str(entry.get("path", "") or "")
    dir_part = bea2._path_dir(path)
    is_new_file = bool(path) and (path not in accepted_paths)
    is_new_dir = bool(dir_part) and (dir_part not in accepted_dirs)

    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods) if methods else set()
    method_set_total = (len(accepted_methods | methods) or 1)
    agreement_norm = min(len(methods) / max(method_set_total, 1), 1.0)

    path_toks = bea2._path_tokens(path)
    overlap = bea2._token_overlap(query_toks, path_toks) if path_toks else 0.0
    file_reach = round(min(
        (0.4 if is_new_file else 0.0) + 0.3 * agreement_norm + 0.3 * overlap,
        1.0,
    ), 6)

    span_tight = bea3._span_tightness(entry)
    exactness = 1.0 if len(methods) >= 2 else 0.5
    span_precision = round(min(span_tight * 0.6 + exactness * 0.4, 1.0), 6)

    novelty_raw = 1.0 if (is_new_file or is_new_dir) else 0.0
    diminish = max(0.0, 1.0 - (float(step) / float(max(budget, 1))))
    novelty_diminishing_returns = round(novelty_raw * diminish, 6)

    rank = _rank_of(entry)
    latency_cost = round(min(max(rank, 0), 10) / 10.0, 6)

    duplicate_penalty = 0.0 if is_new_file else 1.0

    return {
        "file_reach": file_reach,
        "span_precision": span_precision,
        "novelty_diminishing_returns": novelty_diminishing_returns,
        "latency_cost": latency_cost,
        "duplicate_penalty": duplicate_penalty,
    }


def _compute_fd1_objective(
    components: dict[str, float],
    fd1_weights: dict[str, float],
) -> float:
    """Combine the 5 components with the frozen FD1 category weights.

    Reward components (file_reach, span_precision, novelty) are added;
    penalty components (latency_cost, duplicate_penalty) are subtracted.
    """
    obj = 0.0
    for cat, comp in FD1_CATEGORY_TO_COMPONENT.items():
        w = float(fd1_weights.get(cat, 0.0))
        c = float(components.get(comp, 0.0))
        if comp in FD1_PENALTY_COMPONENTS:
            obj -= w * c
        else:
            obj += w * c
    return round(obj, 6)


# --- FD1 coverage-only setwise policy (relevance + coverage/diversity, no
# FD1 weights) and FD1 loss-weighted setwise treatment (adds frozen weights) ---


def _empty_mechanism_summary(arm_label: str) -> dict[str, Any]:
    return {
        "arm_label": arm_label,
        "role_proxy_used": False,
        "target_support_proxy_used": False,
        "setwise_used": False,
        "budget_used": 0,
        "stop_reason": "",
        "fd1_weights_used": False,
    }


def _fd1_coverage_only_setwise_policy(
    candidates: list[dict[str, Any]], query: str, budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Any]]:
    """fd1_coverage_only_same_budget arm.

    Greedy setwise under budget 5 using the v0.2 base priority (agreement +
    bm25_norm + diversity + query/path overlap - risk - duplication). This is
    the relevance + coverage/diversity signal WITHOUT FD1 weights. It is the
    ablation baseline for the FD1 loss-weighted treatment.
    """
    mechanism_summary = _empty_mechanism_summary("coverage_only")
    if not candidates or budget <= 0:
        return [], [], [
            {"step": 0, "budget_remaining": 0, "accepted_so_far": 0}
        ], "no_candidates_or_zero_budget", mechanism_summary

    deduped = bea1._dedup_candidates(candidates)
    if not deduped:
        return [], [], [
            {"step": 0, "budget_remaining": budget, "accepted_so_far": 0}
        ], "no_deduped_candidates", mechanism_summary

    query_toks = bea2._query_tokens(query)
    method_set: set[str] = set()
    for entry in deduped:
        m = entry.get("methods", set())
        if isinstance(m, set):
            method_set |= m
        elif isinstance(m, (list, tuple)):
            method_set |= set(m)

    accepted: list[dict[str, Any]] = []
    accepted_paths: set[str] = set()
    accepted_dirs: set[str] = set()
    accepted_spans: set[tuple[str, int, int]] = set()
    action_order: list[dict[str, Any]] = []
    budget_trace: list[dict[str, Any]] = []
    stop_reason = "candidates_exhausted"
    remaining = list(deduped)

    for step in range(budget):
        if not remaining:
            stop_reason = "candidates_exhausted"
            break
        scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]] = []
        for idx, entry in enumerate(remaining):
            prio = bea2._compute_priority(
                entry, query_toks, accepted_paths, accepted_dirs,
                accepted_spans, method_set,
            )
            scored.append((prio["priority_score"], entry.get("stable_index", idx), entry, prio))
        scored.sort(key=lambda t: (-t[0], t[1]))
        best_prio, _si, best_entry, best_components = scored[0]
        budget_remaining = budget - len(accepted)
        budget_trace.append({
            "step": step, "budget_remaining": budget_remaining,
            "accepted_so_far": len(accepted),
            "candidate_count_remaining": len(remaining),
        })
        if len(accepted) >= budget:
            stop_reason = "budget_exhausted"
            action_order.append({
                "step": step, "action": "stop_budget_exhausted",
                "priority_score": best_prio,
                "priority_components": best_components["priority_components"],
            })
            break
        path = best_entry["path"]
        dir_part = bea2._path_dir(path)
        span_key = (path, best_entry["start_line"], best_entry["end_line"])
        accepted.append({
            "path": path,
            "start_line": best_entry["start_line"],
            "end_line": best_entry["end_line"],
            "content_sha": best_entry.get("content_sha", ""),
        })
        accepted_paths.add(path)
        if dir_part:
            accepted_dirs.add(dir_part)
        accepted_spans.add(span_key)
        action_order.append({
            "step": step, "action": "accept_candidate",
            "priority_score": best_prio,
            "priority_components": best_components["priority_components"],
            "candidate_method": best_entry.get("first_method", ""),
            "candidate_rank": best_entry.get("first_rank", 0),
            "is_new_file": best_components["is_new_file"],
            "is_new_dir": best_components["is_new_dir"],
            "span_extent": bea3._span_extent(best_entry),
            "span_proxy_bucket": bea3._span_proxy_bucket(bea3._span_extent(best_entry)),
        })
        remaining = [e for e in remaining if (e["path"], e["start_line"], e["end_line"]) != span_key]

    if len(accepted) >= budget and stop_reason not in ("candidates_exhausted",):
        stop_reason = "budget_exhausted"
    elif not remaining and stop_reason != "budget_exhausted":
        stop_reason = "candidates_exhausted"

    mechanism_summary["setwise_used"] = True
    mechanism_summary["budget_used"] = len(accepted)
    mechanism_summary["stop_reason"] = stop_reason
    return accepted, action_order, budget_trace, stop_reason, mechanism_summary


def _fd1_loss_weighted_setwise_policy(
    candidates: list[dict[str, Any]], query: str, budget: int,
    fd1_weights: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Any], list[dict[str, Any]]]:
    """fd1_loss_weighted_setwise_same_budget treatment arm.

    Greedy setwise under budget 5. Score = coverage-only base priority
    (relevance + coverage/diversity) + FD1 loss-weighted objective
    (file reach, span precision, novelty/diminishing returns, latency/cost
    penalty, duplicate penalty). The FD1 weights are frozen before
    evaluation; no role-proxy assignment; no gold/private labels.
    Returns (accepted, action_order, budget_trace, stop_reason,
    mechanism_summary, objective_features) where objective_features is the
    per-candidate FD1-objective feature log (private).
    """
    mechanism_summary = _empty_mechanism_summary("fd1_loss_weighted")
    mechanism_summary["fd1_weights_used"] = bool(fd1_weights)
    objective_features: list[dict[str, Any]] = []
    if not candidates or budget <= 0:
        return [], [], [
            {"step": 0, "budget_remaining": 0, "accepted_so_far": 0}
        ], "no_candidates_or_zero_budget", mechanism_summary, objective_features

    deduped = bea1._dedup_candidates(candidates)
    if not deduped:
        return [], [], [
            {"step": 0, "budget_remaining": budget, "accepted_so_far": 0}
        ], "no_deduped_candidates", mechanism_summary, objective_features

    query_toks = bea2._query_tokens(query)
    method_set: set[str] = set()
    for entry in deduped:
        m = entry.get("methods", set())
        if isinstance(m, set):
            method_set |= m
        elif isinstance(m, (list, tuple)):
            method_set |= set(m)

    accepted: list[dict[str, Any]] = []
    accepted_paths: set[str] = set()
    accepted_dirs: set[str] = set()
    accepted_spans: set[tuple[str, int, int]] = set()
    accepted_methods: set[str] = set()
    action_order: list[dict[str, Any]] = []
    budget_trace: list[dict[str, Any]] = []
    stop_reason = "candidates_exhausted"
    remaining = list(deduped)

    for step in range(budget):
        if not remaining:
            stop_reason = "candidates_exhausted"
            break
        scored: list[tuple[float, int, dict[str, Any], dict[str, Any], dict[str, float], float]] = []
        for idx, entry in enumerate(remaining):
            base = bea2._compute_priority(
                entry, query_toks, accepted_paths, accepted_dirs,
                accepted_spans, method_set,
            )
            comps = _compute_fd1_objective_components(
                entry, query_toks, accepted_paths, accepted_dirs,
                accepted_methods, step, budget,
            )
            obj = _compute_fd1_objective(comps, fd1_weights)
            priority = round(float(base["priority_score"]) + obj, 6)
            scored.append((priority, entry.get("stable_index", idx), entry, base, comps, obj))
        scored.sort(key=lambda t: (-t[0], t[1]))
        best_priority, _si, best_entry, best_base, best_comps, best_obj = scored[0]

        budget_remaining = budget - len(accepted)
        budget_trace.append({
            "step": step, "budget_remaining": budget_remaining,
            "accepted_so_far": len(accepted),
            "candidate_count_remaining": len(remaining),
        })
        if len(accepted) >= budget:
            stop_reason = "budget_exhausted"
            action_order.append({
                "step": step, "action": "stop_budget_exhausted",
                "priority_score": best_priority,
                "priority_components": best_base["priority_components"],
                "fd1_objective_score": best_obj,
                "fd1_objective_components": best_comps,
            })
            break
        path = best_entry["path"]
        dir_part = bea2._path_dir(path)
        span_key = (path, best_entry["start_line"], best_entry["end_line"])
        accepted.append({
            "path": path,
            "start_line": best_entry["start_line"],
            "end_line": best_entry["end_line"],
            "content_sha": best_entry.get("content_sha", ""),
        })
        accepted_paths.add(path)
        if dir_part:
            accepted_dirs.add(dir_part)
        accepted_spans.add(span_key)
        bm = best_entry.get("methods", set())
        if isinstance(bm, set):
            accepted_methods |= bm
        elif isinstance(bm, (list, tuple)):
            accepted_methods |= set(bm)
        action_order.append({
            "step": step, "action": "accept_candidate",
            "priority_score": best_priority,
            "priority_components": best_base["priority_components"],
            "fd1_objective_score": best_obj,
            "fd1_objective_components": best_comps,
            "candidate_method": best_entry.get("first_method", ""),
            "candidate_rank": best_entry.get("first_rank", 0),
            "is_new_file": best_base["is_new_file"],
            "is_new_dir": best_base["is_new_dir"],
            "span_extent": bea3._span_extent(best_entry),
            "span_proxy_bucket": bea3._span_proxy_bucket(bea3._span_extent(best_entry)),
        })
        objective_features.append({
            "candidate_key": f"{path}:{best_entry['start_line']}:{best_entry['end_line']}",
            "policy_arm": ARM_FD1_LOSS_WEIGHTED,
            "file_reach": best_comps["file_reach"],
            "span_precision": best_comps["span_precision"],
            "novelty_diminishing_returns": best_comps["novelty_diminishing_returns"],
            "latency_cost": best_comps["latency_cost"],
            "duplicate_penalty": best_comps["duplicate_penalty"],
            "fd1_objective": best_obj,
            "is_new_file": best_base["is_new_file"],
            "is_new_dir": best_base["is_new_dir"],
            "span_tightness": bea3._span_tightness(best_entry),
            "rank": _rank_of(best_entry),
            "feature_reason": "selected_candidate",
        })
        remaining = [e for e in remaining if (e["path"], e["start_line"], e["end_line"]) != span_key]

    if len(accepted) >= budget and stop_reason not in ("candidates_exhausted",):
        stop_reason = "budget_exhausted"
    elif not remaining and stop_reason != "budget_exhausted":
        stop_reason = "candidates_exhausted"

    mechanism_summary["setwise_used"] = True
    mechanism_summary["budget_used"] = len(accepted)
    mechanism_summary["stop_reason"] = stop_reason
    return accepted, action_order, budget_trace, stop_reason, mechanism_summary, objective_features


# --- Per-arm metrics + setwise behavior + FD1 category classification ---


def _arm_metrics_for_record(
    arm_id: str, accepted_evidence: list[dict[str, Any]],
    gold_record: dict[str, Any], task_id: str,
    candidate_count_read: int, evidence_budget_used: int,
    action_steps: int, latency_seconds: float,
) -> dict[str, Any]:
    return bea3._arm_metrics_for_record(
        arm_id, accepted_evidence, gold_record, task_id,
        candidate_count_read, evidence_budget_used, action_steps,
        latency_seconds,
    )


def _accepted_file_duplicates(accepted: list[dict[str, Any]]) -> int:
    if not accepted:
        return 0
    paths = [e.get("path", "") for e in accepted if isinstance(e, dict)]
    counts: dict[str, int] = {}
    for p in paths:
        counts[p] = counts.get(p, 0) + 1
    return sum(max(0, c - 1) for c in counts.values())


def _accepted_source_diversity(
    accepted: list[dict[str, Any]], all_candidates: list[dict[str, Any]],
) -> int:
    if not accepted:
        return 0
    accepted_keys = set()
    for e in accepted:
        if isinstance(e, dict):
            accepted_keys.add((e.get("path", ""), e.get("start_line", 0), e.get("end_line", 0)))
    methods: set[str] = set()
    for c in all_candidates:
        if not isinstance(c, dict):
            continue
        key = (c.get("path", ""), c.get("start_line", 0), c.get("end_line", 0))
        if key in accepted_keys:
            m = c.get("method", "")
            if isinstance(m, str) and m:
                methods.add(m)
    return len(methods)


def _selection_differs(
    a_accepted: list[dict[str, Any]], b_accepted: list[dict[str, Any]],
) -> bool:
    a_keys = {(e.get("path", ""), e.get("start_line", 0), e.get("end_line", 0)) for e in a_accepted if isinstance(e, dict)}
    b_keys = {(e.get("path", ""), e.get("start_line", 0), e.get("end_line", 0)) for e in b_accepted if isinstance(e, dict)}
    return a_keys != b_keys


def _classify_fd1_categories(
    metrics: dict[str, Any], budget_used: int,
    latency_seconds: float, baseline_metrics: dict[str, Any],
    baseline_latency: float, duplicate_file_count: int,
) -> dict[str, dict[str, Any]]:
    """Classify one arm's outcome into the 5 FD1 plan categories (post-hoc).

    Post-hoc only: used for public fd1_category_loss_records /
    fd1_category_rate_records tables and the private post-hoc decomposition
    JSONL. NEVER used during selection.
    """
    file_recall = float(metrics.get("file_recall@10", 0.0) or 0.0)
    span_f = float(metrics.get("span_f0.5@10", 0.0) or 0.0)
    success = float(metrics.get("success_rate", 0.0) or 0.0)
    mrr = float(metrics.get("mrr", 0.0) or 0.0)
    b_mrr = float(baseline_metrics.get("mrr", 0.0) or 0.0)

    cats: dict[str, dict[str, Any]] = {}
    if file_recall == 0 and success == 0:
        cats["gold_file_absent"] = {"count": 1, "availability": "available"}
    else:
        cats["gold_file_absent"] = {"count": 0, "availability": "available"}

    if file_recall > 0 and span_f == 0:
        cats["correct_file_wrong_span"] = {"count": 1, "availability": "available"}
    else:
        cats["correct_file_wrong_span"] = {"count": 0, "availability": "available"}

    if budget_used >= FIXED_BUDGET and mrr <= b_mrr:
        cats["budget_spent_on_low_marginal_gain"] = {"count": 1, "availability": "available"}
    else:
        cats["budget_spent_on_low_marginal_gain"] = {"count": 0, "availability": "available"}

    if latency_seconds > baseline_latency and (mrr - b_mrr) <= 0:
        cats["latency_without_quality_gain"] = {"count": 1, "availability": "available"}
    else:
        cats["latency_without_quality_gain"] = {"count": 0, "availability": "available"}

    cats["redundant_same_file_candidates"] = {
        "count": int(max(0, duplicate_file_count)),
        "availability": "available",
    }
    return cats


# --- Heldout fetchers (reuse BEA-5) ---


def _fetch_heldout_contextbench_rows(
    row_offset: int, row_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    return bea5._fetch_heldout_contextbench_rows(row_offset, row_limit)


def _fetch_heldout_repoqa_needles(
    needle_offset: int, needle_limit: int,
) -> tuple[list[dict[str, Any]], str, int, dict[str, int]]:
    return bea5._fetch_heldout_repoqa_needles(needle_offset, needle_limit)


def _is_index_excluded(index: int, windows: tuple[tuple[int, int], ...]) -> bool:
    return bea5._is_index_excluded(index, windows)


def _benchmark_attempt_records(
    per_benchmark_attempts: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    return bea5._benchmark_attempt_records(per_benchmark_attempts)


# --- Per-record evaluation ---


def _evaluate_record(
    *, openlocus_bin: str, benchmark: str, private_record_id: str,
    task_id: str, query: str, gold_paths: list[str],
    gold_lines: list[list[int]], repo_root: Path, budget: int,
    score_path: Path, decision_path: Path,
    fd1_objective_feature_path: Path,
    posthoc_decomposition_path: Path,
    phase_run_id: str, fcc: dict[str, int],
    fd1_weights: dict[str, float],
) -> tuple[dict[str, Any] | None, dict[str, int], dict[str, Any]]:
    rec_start = time.perf_counter()
    failure_reason: str | None = None

    method_candidates: dict[str, list[dict[str, Any]]] = {}
    method_latencies_ms: dict[str, int] = {}
    all_candidates: list[dict[str, Any]] = []
    for method in ALLOWED_METHODS:
        cands, lat_ms, _err = bea0._collect_method_candidates(
            openlocus_bin, method, query, repo_root
        )
        method_candidates[method] = cands
        method_latencies_ms[method] = lat_ms
        if cands:
            all_candidates.extend(cands)

    channels = ",".join(ALLOWED_METHODS)
    rrf_candidates, rrf_latency_ms, _rrf_err = bea0._collect_rrf_candidates(
        openlocus_bin, query, repo_root, channels=channels
    )
    if not rrf_candidates and all_candidates:
        rrf_candidates = bea5._derive_rrf_candidates_from_method_ranks(all_candidates)
        rrf_latency_ms = 0
    if not rrf_candidates:
        fcc["rrf_required_but_missing"] = (
            fcc.get("rrf_required_but_missing", 0) + 1
        )
        failure_reason = "rrf_required_but_missing"

    if not all_candidates:
        failure_reason = "no_candidates_from_any_method"
        fcc["retrieval_failed"] = fcc.get("retrieval_failed", 0) + 1

    if failure_reason is not None:
        return None, fcc, {}

    gold_record = {
        "task_id": task_id, "gold_paths": gold_paths, "gold_lines": gold_lines,
    }

    deduped = bea1._dedup_candidates(all_candidates)
    deduped_count = len(deduped)
    shared_retrieval_latency = sum(method_latencies_ms.values()) / 1000.0

    # --- FD1 loss-weighted setwise (treatment) ---
    treatment_start = time.perf_counter()
    fd1lw_acc, fd1lw_ao, fd1lw_bt, fd1lw_sr, fd1lw_mech, fd1lw_features = (
        _fd1_loss_weighted_setwise_policy(all_candidates, query, budget, fd1_weights)
    )
    fd1lw_policy_time = time.perf_counter() - treatment_start
    fd1lw_metrics = _arm_metrics_for_record(
        ARM_FD1_LOSS_WEIGHTED, fd1lw_acc, gold_record, task_id,
        len(all_candidates), len(fd1lw_acc), len(fd1lw_ao),
        shared_retrieval_latency + fd1lw_policy_time,
    )

    # --- FD1 coverage-only same-budget (ablation) ---
    cov_start = time.perf_counter()
    cov_acc, cov_ao, cov_bt, cov_sr, cov_mech = (
        _fd1_coverage_only_setwise_policy(all_candidates, query, budget)
    )
    cov_policy_time = time.perf_counter() - cov_start
    cov_metrics = _arm_metrics_for_record(
        ARM_FD1_COVERAGE_ONLY, cov_acc, gold_record, task_id,
        len(all_candidates), len(cov_acc), len(cov_ao),
        shared_retrieval_latency + cov_policy_time,
    )

    # --- v0.3 anchor/span/latency (quality baseline) ---
    v03_acc, v03_ao, v03_bt, v03_sr, v03_mech = (
        bea3._bea_v0_3_policy(all_candidates, query, budget,
                              use_anchor=True, use_early_stop=True)
    )
    v03_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_3, v03_acc, gold_record, task_id,
        len(all_candidates), len(v03_acc), len(v03_ao),
        shared_retrieval_latency,
    )

    same_budget_k = bea2._same_budget_k(len(v03_acc), deduped_count)

    # --- Controls ---
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(method_candidates, same_budget_k)
    sb_bm25_metrics = _arm_metrics_for_record(
        ARM_BM25_PREFIX, sb_bm25_ev, gold_record, task_id,
        len(method_candidates.get("bm25", [])),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0,
    )

    rrf_ev = bea2._rrf_same_budget_arm(rrf_candidates, same_budget_k)
    rrf_metrics = _arm_metrics_for_record(
        ARM_RRF_SAME_BUDGET, rrf_ev, gold_record, task_id,
        len(rrf_candidates), len(rrf_ev), len(rrf_ev),
        rrf_latency_ms / 1000.0,
    )

    per_arm_metrics: dict[str, dict[str, Any]] = {
        ARM_FD1_LOSS_WEIGHTED: fd1lw_metrics,
        ARM_FD1_COVERAGE_ONLY: cov_metrics,
        ARM_BEA_V0_3: v03_metrics,
        ARM_BM25_PREFIX: sb_bm25_metrics,
        ARM_RRF_SAME_BUDGET: rrf_metrics,
    }

    rec_latency_ms = int((time.perf_counter() - rec_start) * 1000)

    v03_dup = _accepted_file_duplicates(v03_acc)
    cov_dup = _accepted_file_duplicates(cov_acc)
    fd1lw_dup = _accepted_file_duplicates(fd1lw_acc)
    v03_div = _accepted_source_diversity(v03_acc, all_candidates)
    cov_div = _accepted_source_diversity(cov_acc, all_candidates)
    fd1lw_div = _accepted_source_diversity(fd1lw_acc, all_candidates)
    selection_diff_v03 = _selection_differs(v03_acc, fd1lw_acc)
    selection_diff_cov = _selection_differs(cov_acc, fd1lw_acc)

    rec_summary = {
        "setwise_behavior": {
            "selection_differs_v03": selection_diff_v03,
            "selection_differs_coverage": selection_diff_cov,
            "duplicate_file_count_v03": v03_dup,
            "duplicate_file_count_coverage": cov_dup,
            "duplicate_file_count_fd1lw": fd1lw_dup,
            "source_diversity_v03": v03_div,
            "source_diversity_coverage": cov_div,
            "source_diversity_fd1lw": fd1lw_div,
            "v03_budget_used": len(v03_acc),
            "coverage_budget_used": len(cov_acc),
            "fd1lw_budget_used": len(fd1lw_acc),
            "same_budget_k": same_budget_k,
        },
        "mechanism_summary": {
            "role_proxy_used": fd1lw_mech.get("role_proxy_used", False),
            "target_support_proxy_used": fd1lw_mech.get("target_support_proxy_used", False),
            "setwise_used": fd1lw_mech.get("setwise_used", False),
            "budget_used": fd1lw_mech.get("budget_used", 0),
            "fd1_weights_used": fd1lw_mech.get("fd1_weights_used", False),
            "stop_reason": fd1lw_mech.get("stop_reason", ""),
        },
        "v03_mechanism_summary": {
            "anchor_used": v03_mech.get("anchor_used", False),
            "early_stop_used": bool(v03_mech.get("early_stop_reason", "")),
            "budget_used": len(v03_acc),
            "latency_ms": rec_latency_ms,
            "mean_span_extent": v03_mech.get("mean_span_extent", 0.0),
        },
        "fd1_objective_features": fd1lw_features,
    }

    # --- Write private FD1-objective-feature rows (per selected candidate) ---
    for feat in fd1lw_features:
        try:
            _write_private_row(fd1_objective_feature_path, {
                "phase_run_id": phase_run_id,
                "benchmark": benchmark,
                "private_record_id": private_record_id,
                "candidate_key": feat["candidate_key"],
                "policy_arm": feat["policy_arm"],
                "file_reach": feat["file_reach"],
                "span_precision": feat["span_precision"],
                "novelty_diminishing_returns": feat["novelty_diminishing_returns"],
                "latency_cost": feat["latency_cost"],
                "duplicate_penalty": feat["duplicate_penalty"],
                "fd1_objective": feat["fd1_objective"],
                "is_new_file": feat["is_new_file"],
                "is_new_dir": feat["is_new_dir"],
                "span_tightness": feat["span_tightness"],
                "rank": feat["rank"],
                "feature_reason": feat["feature_reason"],
            })
        except OSError:
            fcc["private_fd1_objective_feature_write_failed"] = (
                fcc.get("private_fd1_objective_feature_write_failed", 0) + 1
            )

    # --- Write private decision rows (treatment arm only) ---
    for i, action in enumerate(fd1lw_ao):
        try:
            _write_private_row(decision_path, {
                "phase_run_id": phase_run_id,
                "benchmark": benchmark,
                "private_record_id": private_record_id,
                "policy_arm": ARM_FD1_LOSS_WEIGHTED,
                "decision_step": action.get("step", i),
                "decision_action": action.get("action", ""),
                "priority_score": action.get("priority_score", 0.0),
                "priority_components": action.get("priority_components", {}),
                "fd1_objective_score": action.get("fd1_objective_score", 0.0),
                "fd1_objective_components": action.get("fd1_objective_components", {}),
                "candidate_method": action.get("candidate_method", ""),
                "candidate_rank": action.get("candidate_rank", 0),
                "is_new_file": action.get("is_new_file", False),
                "is_new_dir": action.get("is_new_dir", False),
                "span_extent": action.get("span_extent", 0),
                "span_proxy_bucket": action.get("span_proxy_bucket", ""),
                "decision_reason": fd1lw_sr,
            })
        except OSError:
            fcc["private_decision_write_failed"] = (
                fcc.get("private_decision_write_failed", 0) + 1
            )

    # --- Write private post-hoc decomposition rows (record x arm x category) ---
    v03_lat = float(v03_metrics.get("latency_seconds", 0.0))
    v03_cats = _classify_fd1_categories(
        v03_metrics, len(v03_acc), v03_lat, v03_metrics, v03_lat, v03_dup,
    )
    for arm_id, metrics in per_arm_metrics.items():
        accepted = (
            fd1lw_acc if arm_id == ARM_FD1_LOSS_WEIGHTED
            else cov_acc if arm_id == ARM_FD1_COVERAGE_ONLY
            else v03_acc if arm_id == ARM_BEA_V0_3
            else sb_bm25_ev if arm_id == ARM_BM25_PREFIX
            else rrf_ev
        )
        arm_dup = _accepted_file_duplicates(accepted)
        arm_lat = float(metrics.get("latency_seconds", 0.0))
        arm_budget = len(accepted)
        cats = _classify_fd1_categories(
            metrics, arm_budget, arm_lat, v03_metrics, v03_lat, arm_dup,
        )
        for cat in FD1_PLAN_CATEGORIES:
            info = cats.get(cat, {"count": 0, "availability": "available"})
            v03_count = int(v03_cats.get(cat, {}).get("count", 0))
            try:
                _write_private_row(posthoc_decomposition_path, {
                    "phase_run_id": phase_run_id,
                    "benchmark": benchmark,
                    "private_record_id": private_record_id,
                    "policy_arm": arm_id,
                    "fd1_category": cat,
                    "category_count": int(info.get("count", 0)),
                    "category_availability": str(info.get("availability", "available")),
                    "loss": float(info.get("count", 0)),
                    "delta_vs_v03": float(info.get("count", 0)) - float(v03_count),
                    "latency_ms": rec_latency_ms,
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "provider_calls": 0,
                })
            except OSError:
                fcc["private_posthoc_decomposition_write_failed"] = (
                    fcc.get("private_posthoc_decomposition_write_failed", 0) + 1
                )

    # --- Write private SCORE rows (one per policy arm) ---
    runtime_query_feature_summary = {
        "benchmark": benchmark,
        "method_count": len(ALLOWED_METHODS),
        "methods": list(ALLOWED_METHODS),
        "candidate_count_total": len(all_candidates),
        "candidate_count_per_method": {
            m: len(method_candidates.get(m, [])) for m in ALLOWED_METHODS
        },
        "rrf_candidate_count": len(rrf_candidates),
        "budget": int(budget),
        "same_budget_k": int(same_budget_k),
        "deduped_candidate_count": int(deduped_count),
        "fd1lw_accepted_count": int(len(fd1lw_acc)),
        "coverage_accepted_count": int(len(cov_acc)),
        "v03_accepted_count": int(len(v03_acc)),
        "shared_retrieval_latency_seconds": round(shared_retrieval_latency, 6),
        "query_length_chars": len(query) if isinstance(query, str) else 0,
        "query_word_count": (
            len(query.split()) if isinstance(query, str) and query else 0
        ),
    }

    arms_to_write = [
        (ARM_FD1_LOSS_WEIGHTED, fd1lw_ao, fd1lw_bt, fd1lw_sr, fd1lw_metrics, fd1lw_mech, fd1lw_features),
        (ARM_FD1_COVERAGE_ONLY, cov_ao, cov_bt, cov_sr, cov_metrics, cov_mech, []),
        (ARM_BEA_V0_3, v03_ao, v03_bt, v03_sr, v03_metrics, v03_mech, []),
        (ARM_BM25_PREFIX, [], [], "same_budget_bm25_prefix", sb_bm25_metrics, {}, []),
        (ARM_RRF_SAME_BUDGET, [], [], "same_budget_rrf", rrf_metrics, {}, []),
    ]

    for arm_id, action_order, budget_trace, stop_reason, score_outcome, mech_summary, feats in arms_to_write:
        fd1_obj_summary = {
            "component_means": {
                comp: round(
                    sum(float(f.get(comp, 0.0)) for f in feats) / len(feats), 6
                ) if feats else 0.0
                for comp in FD1_OBJECTIVE_COMPONENTS
            },
            "mean_fd1_objective": (
                round(sum(float(f.get("fd1_objective", 0.0)) for f in feats) / len(feats), 6)
                if feats else 0.0
            ),
            "selected_feature_count": len(feats),
        }
        private_score_row = {
            "phase_run_id": phase_run_id,
            "benchmark": benchmark,
            "private_record_id": private_record_id,
            "policy_arm": arm_id,
            "runtime_query_feature_summary": runtime_query_feature_summary,
            "candidate_features": [],
            "fd1_objective_components_summary": fd1_obj_summary,
            "priority_components": (
                [{"step": a.get("step", i), "priority_score": a.get("priority_score", 0.0),
                  "priority_components": a.get("priority_components", {}),
                  "fd1_objective_score": a.get("fd1_objective_score", 0.0)}
                 for i, a in enumerate(action_order) if a.get("action") == "accept_candidate"]
                if action_order else []
            ),
            "selected_decisions": [
                {"step": a.get("step", i), "action": a.get("action", ""),
                 "priority_score": a.get("priority_score", 0.0)}
                for i, a in enumerate(action_order)
            ] if action_order else [],
            "action_order": action_order,
            "budget_trace": budget_trace,
            "anchor_slots": mech_summary.get("anchor_count_filled", 0) if mech_summary else 0,
            "early_stop_reason": mech_summary.get("early_stop_reason", "") if mech_summary else "",
            "stop_reason": stop_reason,
            "score_outcome": score_outcome,
            "role_proxy_summary": ({"role_proxy_used": False, "target_support_proxy_used": False}
                                    if arm_id == ARM_FD1_LOSS_WEIGHTED else {}),
            "latency_ms": rec_latency_ms,
            "cost_usd": 0.0,
            "tokens": 0,
            "provider_calls": 0,
            "failure_reason": failure_reason,
        }
        try:
            _write_private_row(score_path, private_score_row)
        except OSError:
            fcc["private_score_write_failed"] = (
                fcc.get("private_score_write_failed", 0) + 1
            )
            return None, fcc, rec_summary

    return per_arm_metrics, fcc, rec_summary


# --- Public record builders (records-only; no dynamic dict mirrors) ---


def _arm_metric_records(
    arm_aggs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for arm_id in sorted(arm_aggs.keys()):
        agg = arm_aggs[arm_id]
        rc = int(agg.get("__record_count__", 0))
        for metric in ARM_METRIC_ALLOWLIST:
            value = agg.get(metric, 0.0)
            records.append({
                "arm": arm_id,
                "metric": metric,
                "value": float(value) if isinstance(value, (int, float)) else 0.0,
                "record_count": rc,
            })
    records.sort(key=lambda r: (r["arm"], r["metric"]))
    return records


def _arm_delta_records(
    arm_aggs: dict[str, dict[str, Any]], baseline_arm: str,
    treatment_arms: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if baseline_arm not in arm_aggs:
        return records
    for treatment in treatment_arms:
        if treatment not in arm_aggs:
            continue
        for metric in ARM_METRIC_ALLOWLIST:
            b = float(arm_aggs[baseline_arm].get(metric, 0.0))
            t = float(arm_aggs[treatment].get(metric, 0.0))
            records.append({
                "baseline_arm": baseline_arm,
                "treatment_arm": treatment,
                "metric": metric,
                "delta": round(t - b, 6),
            })
    records.sort(key=lambda r: (r["baseline_arm"], r["treatment_arm"], r["metric"]))
    return records


def _win_tie_loss_records(
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    baseline_arm: str, treatment_arm: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    paired: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for rec in per_record_arm_metrics:
        if baseline_arm in rec and treatment_arm in rec:
            paired.append((rec[baseline_arm], rec[treatment_arm]))
    record_count = len(paired)
    if record_count == 0:
        return records
    for metric in PRIMARY_METRICS:
        win = tie = loss = 0
        for b, t in paired:
            bv = b.get(metric, 0.0)
            tv = t.get(metric, 0.0)
            if not isinstance(bv, (int, float)) or not isinstance(tv, (int, float)):
                continue
            if tv > bv:
                win += 1
            elif tv < bv:
                loss += 1
            else:
                tie += 1
        records.append({
            "baseline_arm": baseline_arm,
            "treatment_arm": treatment_arm,
            "metric": metric,
            "win": win, "tie": tie, "loss": loss,
            "record_count": record_count,
        })
    records.sort(key=lambda r: (r["baseline_arm"], r["metric"]))
    return records


def _setwise_behavior_records(
    per_record_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not per_record_summaries:
        return []
    n = len(per_record_summaries)
    records: list[dict[str, Any]] = []
    sb = [s.get("setwise_behavior", {}) for s in per_record_summaries]
    diff_v03 = sum(1 for s in sb if s.get("selection_differs_v03", False))
    diff_cov = sum(1 for s in sb if s.get("selection_differs_coverage", False))
    mean_dup_v03 = sum(int(s.get("duplicate_file_count_v03", 0)) for s in sb) / n
    mean_dup_cov = sum(int(s.get("duplicate_file_count_coverage", 0)) for s in sb) / n
    mean_dup_fd1lw = sum(int(s.get("duplicate_file_count_fd1lw", 0)) for s in sb) / n
    mean_div_v03 = sum(int(s.get("source_diversity_v03", 0)) for s in sb) / n
    mean_div_cov = sum(int(s.get("source_diversity_coverage", 0)) for s in sb) / n
    mean_div_fd1lw = sum(int(s.get("source_diversity_fd1lw", 0)) for s in sb) / n

    records.append({"behavior_field": "setwise_selection_diff_rate_fd1lw_vs_v03",
                    "value": round(diff_v03 / n, 6), "record_count": n})
    records.append({"behavior_field": "setwise_selection_diff_rate_fd1lw_vs_coverage",
                    "value": round(diff_cov / n, 6), "record_count": n})
    records.append({"behavior_field": "mean_duplicate_file_count_v03",
                    "value": round(mean_dup_v03, 6), "record_count": n})
    records.append({"behavior_field": "mean_duplicate_file_count_coverage",
                    "value": round(mean_dup_cov, 6), "record_count": n})
    records.append({"behavior_field": "mean_duplicate_file_count_fd1lw",
                    "value": round(mean_dup_fd1lw, 6), "record_count": n})
    records.append({"behavior_field": "mean_candidate_source_diversity_v03",
                    "value": round(mean_div_v03, 6), "record_count": n})
    records.append({"behavior_field": "mean_candidate_source_diversity_coverage",
                    "value": round(mean_div_cov, 6), "record_count": n})
    records.append({"behavior_field": "mean_candidate_source_diversity_fd1lw",
                    "value": round(mean_div_fd1lw, 6), "record_count": n})
    records.sort(key=lambda r: r["behavior_field"])
    return records


def _fd1_category_loss_records(
    per_record_categories: dict[str, list[dict[str, dict[str, Any]]]],
    fd1_weights: dict[str, float],
) -> list[dict[str, Any]]:
    """Per (policy_arm, fd1_category): category_rate * frozen_weight + counts."""
    records: list[dict[str, Any]] = []
    for arm_id, rec_cats in per_record_categories.items():
        n = len(rec_cats) if rec_cats else 0
        if n == 0:
            continue
        for cat in FD1_PLAN_CATEGORIES:
            count = sum(
                int(rc.get(cat, {}).get("count", 0))
                for rc in rec_cats
                if isinstance(rc.get(cat, {}), dict)
            )
            rate = count / n
            w = float(fd1_weights.get(cat, 0.0))
            records.append({
                "policy_arm": arm_id,
                "fd1_category": cat,
                "category_rate": round(rate, 6),
                "weighted_loss": round(rate * w, 6),
                "frozen_weight": round(w, 6),
                "record_count": n,
            })
    records.sort(key=lambda r: (r["policy_arm"], r["fd1_category"]))
    return records


def _fd1_category_rate_records(
    per_record_categories: dict[str, list[dict[str, dict[str, Any]]]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for arm_id, rec_cats in per_record_categories.items():
        n = len(rec_cats) if rec_cats else 0
        if n == 0:
            continue
        for cat in FD1_PLAN_CATEGORIES:
            count = sum(
                int(rc.get(cat, {}).get("count", 0) if isinstance(rc.get(cat, {}), dict) else 0)
                for rc in rec_cats
            )
            rate = count / n
            records.append({
                "policy_arm": arm_id,
                "fd1_category": cat,
                "category_rate": round(rate, 6),
                "record_count": n,
            })
    records.sort(key=lambda r: (r["policy_arm"], r["fd1_category"]))
    return records


def _fd1_objective_component_records(
    per_record_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per component: mean across treatment-arm selected candidates."""
    if not per_record_summaries:
        return []
    n = len(per_record_summaries)
    records: list[dict[str, Any]] = []
    comp_sums: dict[str, float] = {c: 0.0 for c in FD1_OBJECTIVE_COMPONENTS}
    obj_sum = 0.0
    total_feats = 0
    for s in per_record_summaries:
        feats = s.get("fd1_objective_features", [])
        if not feats:
            continue
        for f in feats:
            for c in FD1_OBJECTIVE_COMPONENTS:
                comp_sums[c] += float(f.get(c, 0.0))
            obj_sum += float(f.get("fd1_objective", 0.0))
            total_feats += 1
    for c in FD1_OBJECTIVE_COMPONENTS:
        records.append({
            "component": c,
            "value": round(comp_sums[c] / total_feats, 6) if total_feats else 0.0,
            "record_count": n,
        })
    records.append({
        "component": "fd1_objective_mean",
        "value": round(obj_sum / total_feats, 6) if total_feats else 0.0,
        "record_count": n,
    })
    records.sort(key=lambda r: r["component"])
    return records


def _ablation_delta_records(
    per_record_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per (component, baseline_arm, treatment_arm): coverage-only vs FD1."""
    if not per_record_summaries:
        return []
    n = len(per_record_summaries)
    records: list[dict[str, Any]] = []
    cov_budget = sum(int(s.get("setwise_behavior", {}).get("coverage_budget_used", 0)) for s in per_record_summaries) / n
    fd1lw_budget = sum(int(s.get("setwise_behavior", {}).get("fd1lw_budget_used", 0)) for s in per_record_summaries) / n
    cov_dup = sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_coverage", 0)) for s in per_record_summaries) / n
    fd1lw_dup = sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_fd1lw", 0)) for s in per_record_summaries) / n
    cov_div = sum(int(s.get("setwise_behavior", {}).get("source_diversity_coverage", 0)) for s in per_record_summaries) / n
    fd1lw_div = sum(int(s.get("setwise_behavior", {}).get("source_diversity_fd1lw", 0)) for s in per_record_summaries) / n
    rows = [
        ("budget_used", COVERAGE_ONLY_ARM, TREATMENT_ARM, round(fd1lw_budget - cov_budget, 6)),
        ("duplicate_file_count", COVERAGE_ONLY_ARM, TREATMENT_ARM, round(fd1lw_dup - cov_dup, 6)),
        ("source_diversity", COVERAGE_ONLY_ARM, TREATMENT_ARM, round(fd1lw_div - cov_div, 6)),
    ]
    for comp, base, treat, delta in rows:
        records.append({
            "component": comp,
            "baseline_arm": base,
            "treatment_arm": treat,
            "delta": delta,
            "record_count": n,
        })
    records.sort(key=lambda r: (r["component"], r["baseline_arm"], r["treatment_arm"]))
    return records


def _manifest_records(
    *, score_written: bool, score_count: int,
    decision_written: bool, decision_count: int,
    fd1_objective_feature_written: bool, fd1_objective_feature_count: int,
    posthoc_decomposition_written: bool, posthoc_decomposition_count: int,
    objective_config_written: bool, objective_config_count: int,
    storage_class: str,
) -> list[dict[str, Any]]:
    rows = [
        ("private_score_manifest", score_written, score_count,
         PRIVATE_SCORE_SCHEMA_VERSION, _private_score_manifest_hash()),
        ("private_decision_manifest", decision_written, decision_count,
         PRIVATE_DECISION_SCHEMA_VERSION, _private_decision_manifest_hash()),
        ("private_fd1_objective_feature_manifest", fd1_objective_feature_written,
         fd1_objective_feature_count,
         PRIVATE_FD1_OBJECTIVE_FEATURE_SCHEMA_VERSION,
         _private_fd1_objective_feature_manifest_hash()),
        ("private_posthoc_decomposition_manifest", posthoc_decomposition_written,
         posthoc_decomposition_count,
         PRIVATE_POSTHOC_DECOMPOSITION_SCHEMA_VERSION,
         _private_posthoc_decomposition_manifest_hash()),
        ("private_objective_config_manifest", objective_config_written,
         objective_config_count,
         PRIVATE_OBJECTIVE_CONFIG_SCHEMA_VERSION,
         _private_objective_config_manifest_hash()),
    ]
    return [
        {
            "manifest_name": name,
            "records_written": bool(written),
            "record_count": int(count),
            "schema_version": schema,
            "manifest_hash": hsh,
            "storage_class": storage_class,
            "path_publicly_serialized": False,
        }
        for name, written, count, schema, hsh in rows
    ]


# --- Public report builders ---


def _build_unavailable_report(
    failure_reason_category: str, *, self_test_passed: bool,
    self_test_checks_total: int = 0,
    self_test_checks_passed: int | None = None,
    openlocus_binary_source: str, network_mode: str,
    private_score_storage_class: str = "tmp_private",
    private_score_records_written: bool = False,
    private_score_record_count: int = 0,
    private_decision_records_written: bool = False,
    private_decision_record_count: int = 0,
    private_fd1_objective_feature_records_written: bool = False,
    private_fd1_objective_feature_record_count: int = 0,
    private_posthoc_decomposition_records_written: bool = False,
    private_posthoc_decomposition_record_count: int = 0,
    private_objective_config_written: bool = False,
    private_score_manifest_hash_value: str | None = None,
    private_decision_manifest_hash_value: str | None = None,
    private_fd1_objective_feature_manifest_hash_value: str | None = None,
    private_posthoc_decomposition_manifest_hash_value: str | None = None,
    private_objective_config_manifest_hash_value: str | None = None,
    records_attempted_total: int = 0,
    records_evaluated: int = 0,
    records_successful: int = 0,
    records_failed: int = 0,
    records_excluded: int = 0,
    contextbench_attempted: int = 0,
    contextbench_successful: int = 0,
    contextbench_excluded: int = 0,
    repoqa_attempted: int = 0,
    repoqa_successful: int = 0,
    repoqa_excluded: int = 0,
    contextbench_excluded_prior_window_count: int = 0,
    repoqa_excluded_prior_window_count: int = 0,
    contextbench_eligible_count: int = 0,
    repoqa_eligible_count: int = 0,
    quota_reached: bool = False,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["private_score_records_written"] = bool(private_score_records_written)
    safe_true["private_decision_records_written"] = bool(private_decision_records_written)
    safe_true["private_fd1_objective_feature_records_written"] = bool(private_fd1_objective_feature_records_written)
    safe_true["private_posthoc_decomposition_records_written"] = bool(private_posthoc_decomposition_records_written)
    safe_true["private_objective_config_written"] = bool(private_objective_config_written)

    score_hash = private_score_manifest_hash_value if private_score_manifest_hash_value is not None else _private_score_manifest_hash()
    decision_hash = private_decision_manifest_hash_value if private_decision_manifest_hash_value is not None else _private_decision_manifest_hash()
    feat_hash = private_fd1_objective_feature_manifest_hash_value if private_fd1_objective_feature_manifest_hash_value is not None else _private_fd1_objective_feature_manifest_hash()
    decomp_hash = private_posthoc_decomposition_manifest_hash_value if private_posthoc_decomposition_manifest_hash_value is not None else _private_posthoc_decomposition_manifest_hash()
    objcfg_hash = private_objective_config_manifest_hash_value if private_objective_config_manifest_hash_value is not None else _private_objective_config_manifest_hash()

    per_benchmark_attempts = {
        "contextbench": {"attempted": int(contextbench_attempted), "successful": int(contextbench_successful), "excluded": int(contextbench_excluded)},
        "repoqa": {"attempted": int(repoqa_attempted), "successful": int(repoqa_successful), "excluded": int(repoqa_excluded)},
    }
    benchmark_attempt_records = _benchmark_attempt_records(per_benchmark_attempts)
    manifests = _manifest_records(
        score_written=bool(private_score_records_written), score_count=int(private_score_record_count),
        decision_written=bool(private_decision_records_written), decision_count=int(private_decision_record_count),
        fd1_objective_feature_written=bool(private_fd1_objective_feature_records_written),
        fd1_objective_feature_count=int(private_fd1_objective_feature_record_count),
        posthoc_decomposition_written=bool(private_posthoc_decomposition_records_written),
        posthoc_decomposition_count=int(private_posthoc_decomposition_record_count),
        objective_config_written=bool(private_objective_config_written),
        objective_config_count=1 if private_objective_config_written else 0,
        storage_class=private_score_storage_class,
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
        "methods": list(ALLOWED_METHODS),
        "fixed_arms": list(FIXED_ARMS),
        "treatment_arm": TREATMENT_ARM,
        "coverage_only_arm": COVERAGE_ONLY_ARM,
        "quality_baseline_arm": QUALITY_BASELINE_ARM,
        "delta_baseline_arm": DELTA_BASELINE_ARM,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "sampling_mode": SAMPLING_MODE,
        "sampling_protocol_version": SAMPLING_PROTOCOL_VERSION,
        "sampling_frame_policy": SAMPLING_FRAME_POLICY,
        "excluded_prior_windows_policy": EXCLUDED_PRIOR_WINDOWS_POLICY,
        "bea5_overlap_policy": BEA5_OVERLAP_POLICY,
        "bea_v04_p1_overlap_policy": BEA_V04_P1_OVERLAP_POLICY,
        "bea_v04_p2_overlap_policy": BEA_V04_P2_OVERLAP_POLICY,
        "bea_v04_p3_overlap_policy": BEA_V04_P3_OVERLAP_POLICY,
        "fd1_overlap_policy": FD1_OVERLAP_POLICY,
        "target_successful_records": TARGET_SUCCESSFUL_RECORDS,
        "raw_attempt_cap_contextbench": RAW_ATTEMPT_CAP_CONTEXTBENCH,
        "raw_attempt_cap_repoqa": RAW_ATTEMPT_CAP_REPOQA,
        "min_contextbench_successful": MIN_CONTEXTBENCH_SUCCESSFUL,
        "min_repoqa_successful": MIN_REPOQA_SUCCESSFUL,
        "contextbench_row_offset_requested": 0,
        "contextbench_row_limit_requested": RAW_ATTEMPT_CAP_CONTEXTBENCH,
        "repoqa_needle_offset_requested": 0,
        "repoqa_needle_limit_requested": RAW_ATTEMPT_CAP_REPOQA,
        "records_attempted_total": int(records_attempted_total),
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "records_excluded": int(records_excluded),
        "contextbench_attempted": int(contextbench_attempted),
        "contextbench_successful": int(contextbench_successful),
        "contextbench_excluded": int(contextbench_excluded),
        "repoqa_attempted": int(repoqa_attempted),
        "repoqa_successful": int(repoqa_successful),
        "repoqa_excluded": int(repoqa_excluded),
        "contextbench_excluded_prior_window_count": int(contextbench_excluded_prior_window_count),
        "repoqa_excluded_prior_window_count": int(repoqa_excluded_prior_window_count),
        "contextbench_eligible_count": int(contextbench_eligible_count),
        "repoqa_eligible_count": int(repoqa_eligible_count),
        "quota_reached": bool(quota_reached),
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_count_records": _failure_category_count_records(fcc),
        "source_run_records": [],
        "arm_metric_records": [],
        "arm_delta_records": [],
        "win_tie_loss_records": [],
        "fd1_category_loss_records": [],
        "fd1_category_rate_records": [],
        "fd1_objective_component_records": [],
        "ablation_delta_records": [],
        "setwise_behavior_records": [],
        "benchmark_attempt_records": benchmark_attempt_records,
        "hard_gate_records": [],
        "manifests": manifests,
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None and self_test_passed
            else (self_test_checks_passed or 0)
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_fd2a_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
        },
    }
    scan = _fd2a_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *, self_test_passed: bool,
    self_test_checks_total: int,
    self_test_checks_passed: int | None = None,
    openlocus_binary_source: str, network_mode: str,
    records_attempted_total: int, records_evaluated: int,
    records_successful: int, records_failed: int, records_excluded: int,
    contextbench_attempted: int, contextbench_successful: int,
    contextbench_excluded: int, repoqa_attempted: int,
    repoqa_successful: int, repoqa_excluded: int,
    contextbench_excluded_prior_window_count: int,
    repoqa_excluded_prior_window_count: int,
    contextbench_eligible_count: int, repoqa_eligible_count: int,
    quota_reached: bool, network_calls: int,
    arm_aggs: dict[str, dict[str, Any]],
    per_record_arm_metrics: list[dict[str, dict[str, Any]]],
    per_record_setwise_summaries: list[dict[str, Any]],
    per_record_categories: dict[str, list[dict[str, dict[str, Any]]]],
    fd1_weights: dict[str, float],
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
    private_score_records_written: bool,
    private_score_record_count: int,
    private_decision_records_written: bool,
    private_decision_record_count: int,
    private_fd1_objective_feature_records_written: bool,
    private_fd1_objective_feature_record_count: int,
    private_posthoc_decomposition_records_written: bool,
    private_posthoc_decomposition_record_count: int,
    private_objective_config_written: bool,
    private_score_storage_class: str,
    private_score_manifest_hash: str,
    private_decision_manifest_hash: str,
    private_fd1_objective_feature_manifest_hash: str,
    private_posthoc_decomposition_manifest_hash: str,
    private_objective_config_manifest_hash: str,
    aggregate_runtime_seconds: float,
    failure_category_counts: dict[str, int],
    partial: bool,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = records_evaluated > 0
    safe_true["openlocus_retrieval_executed"] = records_successful > 0
    safe_true["score_py_metrics_computed"] = bool(arm_aggs)
    safe_true["bea_v03_policy_executed"] = records_successful > 0
    safe_true["fd2a_policy_executed"] = records_successful > 0
    safe_true["coverage_only_policy_executed"] = records_successful > 0
    safe_true["setwise_selection_performed"] = records_successful > 0
    safe_true["bounded_smoke_frame_read"] = records_evaluated > 0
    safe_true["fd1_artifact_read"] = records_successful > 0
    safe_true["fd1_weights_derived"] = records_successful > 0
    safe_true["private_score_records_written"] = bool(private_score_records_written)
    safe_true["private_decision_records_written"] = bool(private_decision_records_written)
    safe_true["private_fd1_objective_feature_records_written"] = bool(private_fd1_objective_feature_records_written)
    safe_true["private_posthoc_decomposition_records_written"] = bool(private_posthoc_decomposition_records_written)
    safe_true["private_objective_config_written"] = bool(private_objective_config_written)

    amr = _arm_metric_records(arm_aggs)

    required_controls = [ARM_BEA_V0_3, ARM_FD1_COVERAGE_ONLY, ARM_BM25_PREFIX, ARM_RRF_SAME_BUDGET]
    adr: list[dict[str, Any]] = []
    for control in required_controls:
        adr.extend(_arm_delta_records(arm_aggs, control, [TREATMENT_ARM]))
    adr.sort(key=lambda r: (r["baseline_arm"], r["treatment_arm"], r["metric"]))

    wtl: list[dict[str, Any]] = []
    for baseline in required_controls:
        wtl.extend(_win_tie_loss_records(per_record_arm_metrics, baseline, TREATMENT_ARM))
    wtl.sort(key=lambda r: (r["baseline_arm"], r["metric"]))

    sbr = _setwise_behavior_records(per_record_setwise_summaries)
    fclr = _fd1_category_loss_records(per_record_categories, fd1_weights)
    fcrr = _fd1_category_rate_records(per_record_categories)
    focr = _fd1_objective_component_records(per_record_setwise_summaries)
    abdr = _ablation_delta_records(per_record_setwise_summaries)

    per_benchmark_attempts = {
        "contextbench": {"attempted": int(contextbench_attempted), "successful": int(contextbench_successful), "excluded": int(contextbench_excluded)},
        "repoqa": {"attempted": int(repoqa_attempted), "successful": int(repoqa_successful), "excluded": int(repoqa_excluded)},
    }
    benchmark_attempt_records = _benchmark_attempt_records(per_benchmark_attempts)

    manifests = _manifest_records(
        score_written=bool(private_score_records_written), score_count=int(private_score_record_count),
        decision_written=bool(private_decision_records_written), decision_count=int(private_decision_record_count),
        fd1_objective_feature_written=bool(private_fd1_objective_feature_records_written),
        fd1_objective_feature_count=int(private_fd1_objective_feature_record_count),
        posthoc_decomposition_written=bool(private_posthoc_decomposition_records_written),
        posthoc_decomposition_count=int(private_posthoc_decomposition_record_count),
        objective_config_written=bool(private_objective_config_written),
        objective_config_count=1 if private_objective_config_written else 0,
        storage_class=private_score_storage_class,
    )

    source_run_records = [{
        "source_phase": PHASE,
        "source_ci_run_id": "",
        "source_artifact_status": "fresh_smoke",
        "source_sampling_protocol": SAMPLING_PROTOCOL_VERSION,
        "expected_successful_records": TARGET_SUCCESSFUL_RECORDS,
        "replayed_successful_records": records_successful,
        "expected_private_score_count": records_successful * len(FIXED_ARMS),
        "replayed_private_score_count": private_score_record_count,
        "expected_private_decision_count": sum(
            int(s.get("mechanism_summary", {}).get("budget_used", 0))
            for s in per_record_setwise_summaries
        ),
        "replayed_private_decision_count": private_decision_record_count,
        "expected_private_fd1_objective_feature_count": sum(
            int(s.get("mechanism_summary", {}).get("budget_used", 0))
            for s in per_record_setwise_summaries
        ),
        "replayed_private_fd1_objective_feature_count": private_fd1_objective_feature_record_count,
        "expected_private_posthoc_decomposition_count": records_successful * len(FIXED_ARMS) * len(FD1_PLAN_CATEGORIES),
        "replayed_private_posthoc_decomposition_count": private_posthoc_decomposition_record_count,
        "expected_private_objective_config_count": 1,
        "replayed_private_objective_config_count": 1 if private_objective_config_written else 0,
        "fd1_source_schema_version": fd1_source_schema_version,
        "fd1_source_artifact_hash": fd1_source_artifact_hash,
        "records_attempted_total": int(records_attempted_total),
        "records_excluded": int(records_excluded),
        "contextbench_successful": int(contextbench_successful),
        "repoqa_successful": int(repoqa_successful),
        "replay_protocol_match": True,
        "replay_mismatch_reason": "",
    }]

    n = len(per_record_setwise_summaries) if per_record_setwise_summaries else 0
    diff_rate_v03 = (sum(1 for s in per_record_setwise_summaries if s.get("setwise_behavior", {}).get("selection_differs_v03", False)) / n) if n else 0.0
    diff_rate_cov = (sum(1 for s in per_record_setwise_summaries if s.get("setwise_behavior", {}).get("selection_differs_coverage", False)) / n) if n else 0.0
    mean_dup_v03 = (sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_v03", 0)) for s in per_record_setwise_summaries) / n) if n else 0.0
    mean_dup_fd1lw = (sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_fd1lw", 0)) for s in per_record_setwise_summaries) / n) if n else 0.0
    mean_div_v03 = (sum(int(s.get("setwise_behavior", {}).get("source_diversity_v03", 0)) for s in per_record_setwise_summaries) / n) if n else 0.0
    mean_div_fd1lw = (sum(int(s.get("setwise_behavior", {}).get("source_diversity_fd1lw", 0)) for s in per_record_setwise_summaries) / n) if n else 0.0

    v03_agg = arm_aggs.get(ARM_BEA_V0_3, {})
    fd1lw_agg = arm_aggs.get(TREATMENT_ARM, {})
    cov_agg = arm_aggs.get(COVERAGE_ONLY_ARM, {})
    v03_fr = float(v03_agg.get("file_recall@10", 0.0))
    fd1lw_fr = float(fd1lw_agg.get("file_recall@10", 0.0))
    v03_mrr = float(v03_agg.get("mrr", 0.0))
    fd1lw_mrr = float(fd1lw_agg.get("mrr", 0.0))
    v03_span = float(v03_agg.get("span_f0.5@10", 0.0))
    fd1lw_span = float(fd1lw_agg.get("span_f0.5@10", 0.0))
    v03_lat = float(v03_agg.get("latency_seconds", 0.0))
    fd1lw_lat = float(fd1lw_agg.get("latency_seconds", 0.0))

    def _composite_loss(arm_id: str) -> float:
        rec_cats = per_record_categories.get(arm_id, [])
        if not rec_cats:
            return 0.0
        nn = len(rec_cats)
        total = 0.0
        for cat in FD1_PLAN_CATEGORIES:
            count = sum(
                int(rc.get(cat, {}).get("count", 0) if isinstance(rc.get(cat, {}), dict) else 0)
                for rc in rec_cats
            )
            total += (count / nn) * float(fd1_weights.get(cat, 0.0))
        return total

    composite_v03 = _composite_loss(ARM_BEA_V0_3)
    composite_cov = _composite_loss(COVERAGE_ONLY_ARM)
    composite_fd1lw = _composite_loss(TREATMENT_ARM)

    def _cat_rate(arm_id: str, cat: str) -> float:
        rec_cats = per_record_categories.get(arm_id, [])
        if not rec_cats:
            return 0.0
        nn = len(rec_cats)
        count = sum(
            int(rc.get(cat, {}).get("count", 0) if isinstance(rc.get(cat, {}), dict) else 0)
            for rc in rec_cats
        )
        return count / nn

    dominant_improves = any(
        _cat_rate(TREATMENT_ARM, cat) < _cat_rate(ARM_BEA_V0_3, cat)
        for cat in FD1_PLAN_CATEGORIES
    )

    behavior_ok = (
        diff_rate_v03 >= GATE_SETWISE_DIFF_VS_V03
        and diff_rate_cov >= GATE_SETWISE_DIFF_VS_COVERAGE
        and mean_dup_fd1lw <= mean_dup_v03
        and mean_div_fd1lw >= mean_div_v03
    )
    fd1_loss_ok = (
        composite_fd1lw < composite_v03
        and composite_fd1lw < composite_cov
        and dominant_improves
    )
    quality_ok = (
        fd1lw_fr >= v03_fr - GATE_QUALITY_MARGIN_FILE_RECALL
        and fd1lw_mrr >= v03_mrr - GATE_QUALITY_MARGIN_MRR
        and fd1lw_span >= v03_span - GATE_QUALITY_MARGIN_SPAN
        and (v03_lat <= 0 or fd1lw_lat <= v03_lat * GATE_LATENCY_RATIO)
    )

    denominator_ok = (
        records_successful >= CI_MIN_RECORDS_SUCCESSFUL
        and contextbench_successful >= MIN_CONTEXTBENCH_SUCCESSFUL
        and repoqa_successful >= MIN_REPOQA_SUCCESSFUL
    )
    blocking_failure_count = _blocking_failure_count(fcc)

    if records_successful <= 0:
        status = "unavailable_with_reason"
    elif blocking_failure_count > 0:
        status = "fail_schema_contract"
    elif not denominator_ok:
        status = "partial_fd1_objective_signal"
    elif not behavior_ok:
        status = "no_go_no_selection_change"
    elif not fd1_loss_ok:
        if not dominant_improves:
            status = "no_go_objective_ablation_only"
        else:
            status = "no_go_no_fd1_loss_reduction"
    elif not quality_ok:
        status = "no_go_quality_regression"
    elif not partial:
        status = "bea_fd2a_direct_fd1_objective_pass"
    else:
        status = "partial_fd1_objective_signal"

    hard_gate_records = [
        {"gate": "records_successful", "value": float(records_successful), "threshold_relation": ">=", "threshold_value": float(CI_MIN_RECORDS_SUCCESSFUL), "passed": records_successful >= CI_MIN_RECORDS_SUCCESSFUL},
        {"gate": "contextbench_successful", "value": float(contextbench_successful), "threshold_relation": ">=", "threshold_value": float(MIN_CONTEXTBENCH_SUCCESSFUL), "passed": contextbench_successful >= MIN_CONTEXTBENCH_SUCCESSFUL},
        {"gate": "repoqa_successful", "value": float(repoqa_successful), "threshold_relation": ">=", "threshold_value": float(MIN_REPOQA_SUCCESSFUL), "passed": repoqa_successful >= MIN_REPOQA_SUCCESSFUL},
        {"gate": "budget_fixed_5", "value": float(FIXED_BUDGET), "threshold_relation": "==", "threshold_value": 5.0, "passed": FIXED_BUDGET == 5},
        {"gate": "role_proxy_used_false", "value": 0.0, "threshold_relation": "boolean_false", "threshold_value": 0.0, "passed": safe_true.get("role_proxy_used") is False},
        {"gate": "target_support_proxy_used_false", "value": 0.0, "threshold_relation": "boolean_false", "threshold_value": 0.0, "passed": safe_true.get("target_support_proxy_used") is False},
        {"gate": "selection_diff_rate_fd1lw_vs_v03", "value": round(diff_rate_v03, 6), "threshold_relation": ">=", "threshold_value": GATE_SETWISE_DIFF_VS_V03, "passed": diff_rate_v03 >= GATE_SETWISE_DIFF_VS_V03},
        {"gate": "selection_diff_rate_fd1lw_vs_coverage", "value": round(diff_rate_cov, 6), "threshold_relation": ">=", "threshold_value": GATE_SETWISE_DIFF_VS_COVERAGE, "passed": diff_rate_cov >= GATE_SETWISE_DIFF_VS_COVERAGE},
        {"gate": "mean_duplicate_file_count_v03", "value": round(mean_dup_v03, 6), "threshold_relation": "baseline", "threshold_value": round(mean_dup_v03, 6), "passed": True},
        {"gate": "mean_duplicate_file_count_fd1lw", "value": round(mean_dup_fd1lw, 6), "threshold_relation": "<=v03", "threshold_value": round(mean_dup_v03, 6), "passed": mean_dup_fd1lw <= mean_dup_v03},
        {"gate": "mean_candidate_source_diversity_v03", "value": round(mean_div_v03, 6), "threshold_relation": "baseline", "threshold_value": round(mean_div_v03, 6), "passed": True},
        {"gate": "mean_candidate_source_diversity_fd1lw", "value": round(mean_div_fd1lw, 6), "threshold_relation": ">=v03", "threshold_value": round(mean_div_v03, 6), "passed": mean_div_fd1lw >= mean_div_v03},
        {"gate": "composite_fd1_loss_v03", "value": round(composite_v03, 6), "threshold_relation": "baseline", "threshold_value": round(composite_v03, 6), "passed": True},
        {"gate": "composite_fd1_loss_fd1lw", "value": round(composite_fd1lw, 6), "threshold_relation": "<v03", "threshold_value": round(composite_v03, 6), "passed": composite_fd1lw < composite_v03},
        {"gate": "composite_fd1_loss_fd1lw_vs_coverage", "value": round(composite_fd1lw, 6), "threshold_relation": "<coverage", "threshold_value": round(composite_cov, 6), "passed": composite_fd1lw < composite_cov},
        {"gate": "dominant_category_improves", "value": 1.0 if dominant_improves else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(dominant_improves)},
        {"gate": "file_recall_10_v03", "value": round(v03_fr, 6), "threshold_relation": "baseline", "threshold_value": round(v03_fr, 6), "passed": True},
        {"gate": "file_recall_10_fd1lw", "value": round(fd1lw_fr, 6), "threshold_relation": ">=v03_minus_margin", "threshold_value": round(v03_fr - GATE_QUALITY_MARGIN_FILE_RECALL, 6), "passed": fd1lw_fr >= v03_fr - GATE_QUALITY_MARGIN_FILE_RECALL},
        {"gate": "mrr_v03", "value": round(v03_mrr, 6), "threshold_relation": "baseline", "threshold_value": round(v03_mrr, 6), "passed": True},
        {"gate": "mrr_fd1lw", "value": round(fd1lw_mrr, 6), "threshold_relation": ">=v03_minus_margin", "threshold_value": round(v03_mrr - GATE_QUALITY_MARGIN_MRR, 6), "passed": fd1lw_mrr >= v03_mrr - GATE_QUALITY_MARGIN_MRR},
        {"gate": "span_f05_10_v03", "value": round(v03_span, 6), "threshold_relation": "baseline", "threshold_value": round(v03_span, 6), "passed": True},
        {"gate": "span_f05_10_fd1lw", "value": round(fd1lw_span, 6), "threshold_relation": ">=v03_minus_margin", "threshold_value": round(v03_span - GATE_QUALITY_MARGIN_SPAN, 6), "passed": fd1lw_span >= v03_span - GATE_QUALITY_MARGIN_SPAN},
        {"gate": "latency_seconds_v03", "value": round(v03_lat, 6), "threshold_relation": "baseline", "threshold_value": round(v03_lat, 6), "passed": True},
        {"gate": "latency_seconds_fd1lw", "value": round(fd1lw_lat, 6), "threshold_relation": "<=v03_ratio", "threshold_value": round(v03_lat * GATE_LATENCY_RATIO if v03_lat > 0 else 0.0, 6), "passed": (v03_lat <= 0 or fd1lw_lat <= v03_lat * GATE_LATENCY_RATIO)},
        {"gate": "behavior_ok", "value": 1.0 if behavior_ok else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(behavior_ok)},
        {"gate": "fd1_loss_ok", "value": 1.0 if fd1_loss_ok else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(fd1_loss_ok)},
        {"gate": "quality_ok", "value": 1.0 if quality_ok else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(quality_ok)},
    ]

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "budget": FIXED_BUDGET,
        "methods": list(ALLOWED_METHODS),
        "fixed_arms": list(FIXED_ARMS),
        "treatment_arm": TREATMENT_ARM,
        "coverage_only_arm": COVERAGE_ONLY_ARM,
        "quality_baseline_arm": QUALITY_BASELINE_ARM,
        "delta_baseline_arm": DELTA_BASELINE_ARM,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "sampling_mode": SAMPLING_MODE,
        "sampling_protocol_version": SAMPLING_PROTOCOL_VERSION,
        "sampling_frame_policy": SAMPLING_FRAME_POLICY,
        "excluded_prior_windows_policy": EXCLUDED_PRIOR_WINDOWS_POLICY,
        "bea5_overlap_policy": BEA5_OVERLAP_POLICY,
        "bea_v04_p1_overlap_policy": BEA_V04_P1_OVERLAP_POLICY,
        "bea_v04_p2_overlap_policy": BEA_V04_P2_OVERLAP_POLICY,
        "bea_v04_p3_overlap_policy": BEA_V04_P3_OVERLAP_POLICY,
        "fd1_overlap_policy": FD1_OVERLAP_POLICY,
        "target_successful_records": TARGET_SUCCESSFUL_RECORDS,
        "raw_attempt_cap_contextbench": RAW_ATTEMPT_CAP_CONTEXTBENCH,
        "raw_attempt_cap_repoqa": RAW_ATTEMPT_CAP_REPOQA,
        "min_contextbench_successful": MIN_CONTEXTBENCH_SUCCESSFUL,
        "min_repoqa_successful": MIN_REPOQA_SUCCESSFUL,
        "contextbench_row_offset_requested": 0,
        "contextbench_row_limit_requested": RAW_ATTEMPT_CAP_CONTEXTBENCH,
        "repoqa_needle_offset_requested": 0,
        "repoqa_needle_limit_requested": RAW_ATTEMPT_CAP_REPOQA,
        "records_attempted_total": int(records_attempted_total),
        "records_evaluated": records_evaluated,
        "records_successful": records_successful,
        "records_failed": records_failed,
        "records_excluded": int(records_excluded),
        "contextbench_attempted": int(contextbench_attempted),
        "contextbench_successful": int(contextbench_successful),
        "contextbench_excluded": int(contextbench_excluded),
        "repoqa_attempted": int(repoqa_attempted),
        "repoqa_successful": int(repoqa_successful),
        "repoqa_excluded": int(repoqa_excluded),
        "contextbench_excluded_prior_window_count": int(contextbench_excluded_prior_window_count),
        "repoqa_excluded_prior_window_count": int(repoqa_excluded_prior_window_count),
        "contextbench_eligible_count": int(contextbench_eligible_count),
        "repoqa_eligible_count": int(repoqa_eligible_count),
        "quota_reached": bool(quota_reached),
        "network_calls": network_calls,
        "provider_calls": 0,
        "source_run_records": source_run_records,
        "arm_metric_records": amr,
        "arm_delta_records": adr,
        "win_tie_loss_records": wtl,
        "fd1_category_loss_records": fclr,
        "fd1_category_rate_records": fcrr,
        "fd1_objective_component_records": focr,
        "ablation_delta_records": abdr,
        "setwise_behavior_records": sbr,
        "benchmark_attempt_records": benchmark_attempt_records,
        "hard_gate_records": hard_gate_records,
        "manifests": manifests,
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "failure_category_count_records": _failure_category_count_records(fcc),
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": int(self_test_checks_total),
        "self_test_checks_passed": int(
            self_test_checks_total if self_test_checks_passed is None and self_test_passed
            else (self_test_checks_passed or 0)
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "calibration_claimed": False,
            "method_winner_claimed": False,
            "signal_strength": "bea_fd2a_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
        },
    }
    scan = _fd2a_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# --- Self-test (no network; synthetic data + synthetic FD1 loss records) ---


def _build_synthetic_fd1_loss_records() -> list[dict[str, Any]]:
    """Synthetic FD1 aggregate loss records for self-test only.

    Mirrors the shape of the committed FD1 artifact's
    ``category_metric_loss_records``. Never written to any artifact.
    """
    return [
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "gold_file_absent", "baseline_arm": "agreement_only_same_budget",
         "treatment_arm": "bea_v0_3_anchor_span_latency",
         "metric": "file_recall@10", "loss_sum": 5.0, "loss_mean": 0.1,
         "delta_mean": -0.1, "record_count": 50},
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "correct_file_wrong_span",
         "baseline_arm": "agreement_only_same_budget",
         "treatment_arm": "bea_v0_3_anchor_span_latency",
         "metric": "span_f0.5@10", "loss_sum": 3.0, "loss_mean": 0.06,
         "delta_mean": -0.06, "record_count": 50},
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "budget_spent_on_low_marginal_gain",
         "baseline_arm": "agreement_only_same_budget",
         "treatment_arm": "bea_v0_3_anchor_span_latency",
         "metric": "mrr", "loss_sum": 4.0, "loss_mean": 0.08,
         "delta_mean": -0.08, "record_count": 50},
        {"source_phase": "BEA-4", "benchmark": "contextbench",
         "category": "latency_without_quality_gain",
         "baseline_arm": "agreement_only_same_budget",
         "treatment_arm": "bea_v0_3_anchor_span_latency",
         "metric": "latency_seconds", "loss_sum": 6.0, "loss_mean": 0.12,
         "delta_mean": 0.12, "record_count": 50},
        {"source_phase": "BEA-5", "benchmark": "repoqa",
         "category": "gold_file_absent",
         "baseline_arm": "rrf_same_budget",
         "treatment_arm": "bea_v0_3_anchor_span_latency",
         "metric": "file_recall@10", "loss_sum": 2.0, "loss_mean": 0.05,
         "delta_mean": -0.05, "record_count": 40},
    ]


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    candidates = bea0._build_synthetic_candidates()
    gold = bea0._build_synthetic_gold()
    query = "merge adjacent strings into a single string"

    # Derive frozen FD1 weights from synthetic loss records.
    synth_loss_records = _build_synthetic_fd1_loss_records()
    fd1_weights_info = _derive_fd1_category_weights(synth_loss_records)
    fd1_weights = {cat: float(fd1_weights_info[cat]["weight"]) for cat in FD1_PLAN_CATEGORIES}

    # Run both FD2-A policies on synthetic candidates.
    fd1lw_acc, fd1lw_ao, fd1lw_bt, fd1lw_sr, fd1lw_mech, fd1lw_features = (
        _fd1_loss_weighted_setwise_policy(candidates, query, 5, fd1_weights)
    )
    cov_acc, cov_ao, cov_bt, cov_sr, cov_mech = (
        _fd1_coverage_only_setwise_policy(candidates, query, 5)
    )
    v03_acc, v03_ao, v03_bt, v03_sr, v03_mech = bea3._bea_v0_3_policy(
        candidates, query, 5, use_anchor=True, use_early_stop=True
    )

    deduped = bea1._dedup_candidates(candidates)
    same_budget_k = bea2._same_budget_k(len(v03_acc), len(deduped))
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(
        {"bm25": [c for c in candidates if c["method"] == "bm25"]}, same_budget_k
    )
    rrf_ev = bea2._rrf_same_budget_arm(
        bea5._derive_rrf_candidates_from_method_ranks(candidates), same_budget_k
    )

    fd1lw_m = _arm_metrics_for_record(ARM_FD1_LOSS_WEIGHTED, fd1lw_acc, gold, "fd2a-st", len(candidates), len(fd1lw_acc), len(fd1lw_ao), 0.05)
    cov_m = _arm_metrics_for_record(ARM_FD1_COVERAGE_ONLY, cov_acc, gold, "fd2a-st", len(candidates), len(cov_acc), len(cov_ao), 0.04)
    v03_m = _arm_metrics_for_record(ARM_BEA_V0_3, v03_acc, gold, "fd2a-st", len(candidates), len(v03_acc), len(v03_ao), 0.04)
    sb_m = _arm_metrics_for_record(ARM_BM25_PREFIX, sb_bm25_ev, gold, "fd2a-st", len(candidates), len(sb_bm25_ev), len(sb_bm25_ev), 0.0)
    rrf_m = _arm_metrics_for_record(ARM_RRF_SAME_BUDGET, rrf_ev, gold, "fd2a-st", len(candidates), len(rrf_ev), len(rrf_ev), 0.0)

    arm_aggs = {
        ARM_FD1_LOSS_WEIGHTED: {**{k: v for k, v in fd1lw_m.items() if k in ARM_METRIC_ALLOWLIST}, "__record_count__": 1},
        ARM_FD1_COVERAGE_ONLY: {**{k: v for k, v in cov_m.items() if k in ARM_METRIC_ALLOWLIST}, "__record_count__": 1},
        ARM_BEA_V0_3: {**{k: v for k, v in v03_m.items() if k in ARM_METRIC_ALLOWLIST}, "__record_count__": 1},
        ARM_BM25_PREFIX: {**{k: v for k, v in sb_m.items() if k in ARM_METRIC_ALLOWLIST}, "__record_count__": 1},
        ARM_RRF_SAME_BUDGET: {**{k: v for k, v in rrf_m.items() if k in ARM_METRIC_ALLOWLIST}, "__record_count__": 1},
    }
    per_record_arm_metrics = [{
        ARM_FD1_LOSS_WEIGHTED: fd1lw_m, ARM_FD1_COVERAGE_ONLY: cov_m,
        ARM_BEA_V0_3: v03_m, ARM_BM25_PREFIX: sb_m, ARM_RRF_SAME_BUDGET: rrf_m,
    }]
    per_record_setwise_summaries = [{
        "setwise_behavior": {
            "selection_differs_v03": _selection_differs(v03_acc, fd1lw_acc),
            "selection_differs_coverage": _selection_differs(cov_acc, fd1lw_acc),
            "duplicate_file_count_v03": _accepted_file_duplicates(v03_acc),
            "duplicate_file_count_coverage": _accepted_file_duplicates(cov_acc),
            "duplicate_file_count_fd1lw": _accepted_file_duplicates(fd1lw_acc),
            "source_diversity_v03": _accepted_source_diversity(v03_acc, candidates),
            "source_diversity_coverage": _accepted_source_diversity(cov_acc, candidates),
            "source_diversity_fd1lw": _accepted_source_diversity(fd1lw_acc, candidates),
            "v03_budget_used": len(v03_acc), "coverage_budget_used": len(cov_acc),
            "fd1lw_budget_used": len(fd1lw_acc), "same_budget_k": same_budget_k,
        },
        "mechanism_summary": {
            "role_proxy_used": fd1lw_mech.get("role_proxy_used", False),
            "target_support_proxy_used": fd1lw_mech.get("target_support_proxy_used", False),
            "setwise_used": fd1lw_mech.get("setwise_used", False),
            "budget_used": fd1lw_mech.get("budget_used", 0),
            "fd1_weights_used": fd1lw_mech.get("fd1_weights_used", False),
            "stop_reason": fd1lw_mech.get("stop_reason", ""),
        },
        "fd1_objective_features": fd1lw_features,
    }]
    # Post-hoc FD1 categories for each arm.
    v03_lat = float(v03_m.get("latency_seconds", 0.0))
    v03_cats = _classify_fd1_categories(v03_m, len(v03_acc), v03_lat, v03_m, v03_lat, _accepted_file_duplicates(v03_acc))
    per_record_categories: dict[str, list[dict[str, dict[str, Any]]]] = {
        ARM_BEA_V0_3: [v03_cats],
        ARM_FD1_COVERAGE_ONLY: [_classify_fd1_categories(cov_m, len(cov_acc), float(cov_m.get("latency_seconds", 0.0)), v03_m, v03_lat, _accepted_file_duplicates(cov_acc))],
        ARM_FD1_LOSS_WEIGHTED: [_classify_fd1_categories(fd1lw_m, len(fd1lw_acc), float(fd1lw_m.get("latency_seconds", 0.0)), v03_m, v03_lat, _accepted_file_duplicates(fd1lw_acc))],
        ARM_BM25_PREFIX: [_classify_fd1_categories(sb_m, len(sb_bm25_ev), 0.0, v03_m, v03_lat, _accepted_file_duplicates(sb_bm25_ev))],
        ARM_RRF_SAME_BUDGET: [_classify_fd1_categories(rrf_m, len(rrf_ev), 0.0, v03_m, v03_lat, _accepted_file_duplicates(rrf_ev))],
    }

    objective_config = _build_objective_config(
        phase_run_id="fd2a-self-test",
        loss_records=synth_loss_records,
        fd1_source_schema_version="bea_fd1_failure_decomposition.v1",
        fd1_source_artifact_hash="a" * 64,
    )

    skeleton = _build_pass_report(
        self_test_passed=True,
        self_test_checks_total=0,
        openlocus_binary_source="self_test",
        network_mode="self_test",
        records_attempted_total=1, records_evaluated=1, records_successful=1,
        records_failed=0, records_excluded=0,
        contextbench_attempted=1, contextbench_successful=1, contextbench_excluded=0,
        repoqa_attempted=0, repoqa_successful=0, repoqa_excluded=0,
        contextbench_excluded_prior_window_count=0,
        repoqa_excluded_prior_window_count=0,
        contextbench_eligible_count=1, repoqa_eligible_count=0,
        quota_reached=True, network_calls=0, arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_record_setwise_summaries=per_record_setwise_summaries,
        per_record_categories=per_record_categories,
        fd1_weights=fd1_weights,
        fd1_source_schema_version="bea_fd1_failure_decomposition.v1",
        fd1_source_artifact_hash="a" * 64,
        private_score_records_written=True, private_score_record_count=5,
        private_decision_records_written=True, private_decision_record_count=len(fd1lw_ao),
        private_fd1_objective_feature_records_written=True,
        private_fd1_objective_feature_record_count=len(fd1lw_features),
        private_posthoc_decomposition_records_written=True,
        private_posthoc_decomposition_record_count=5 * len(FD1_PLAN_CATEGORIES),
        private_objective_config_written=True,
        private_score_storage_class="tmp_private",
        private_score_manifest_hash=_private_score_manifest_hash(),
        private_decision_manifest_hash=_private_decision_manifest_hash(),
        private_fd1_objective_feature_manifest_hash=_private_fd1_objective_feature_manifest_hash(),
        private_posthoc_decomposition_manifest_hash=_private_posthoc_decomposition_manifest_hash(),
        private_objective_config_manifest_hash=_private_objective_config_manifest_hash(),
        aggregate_runtime_seconds=0.5,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        partial=False,
    )
    unavail = _build_unavailable_report(
        "retrieval_failed", self_test_passed=True,
        openlocus_binary_source="self_test", network_mode="self_test",
    )

    # G1: Identity
    for k, v in [("schema_version", SCHEMA_VERSION), ("claim_level", CLAIM_LEVEL),
                 ("mode", MODE), ("phase", PHASE), ("generated_by", GENERATED_BY)]:
        checks.append(_check(f"identity_{k}", skeleton[k] == v))
    checks.append(_check("status_present", "status" in skeleton))
    checks.append(_check("unavail_status", unavail["status"] == "unavailable_with_reason"))

    # G2: Safe true flags (role_proxy_used / target_support_proxy_used MUST be False)
    for flag in ("aggregate_only_public_artifact", "diagnostic_only",
                 "fd2a_policy_executed", "coverage_only_policy_executed",
                 "bea_v03_policy_executed", "setwise_selection_performed",
                 "fd1_artifact_read", "fd1_weights_derived"):
        checks.append(_check(f"safe_true_{flag}", skeleton.get(flag) is True))
    # Binding: role_proxy_used=false, target_support_proxy_used=false
    checks.append(_check("role_proxy_used_false", skeleton.get("role_proxy_used") is False))
    checks.append(_check("target_support_proxy_used_false", skeleton.get("target_support_proxy_used") is False))
    checks.append(_check("unavail_role_proxy_used_false", unavail.get("role_proxy_used") is False))
    checks.append(_check("unavail_target_support_proxy_used_false", unavail.get("target_support_proxy_used") is False))
    # Mechanism-level: treatment policy does not use role proxies.
    checks.append(_check("mech_role_proxy_used_false", fd1lw_mech.get("role_proxy_used") is False))
    checks.append(_check("mech_target_support_proxy_used_false", fd1lw_mech.get("target_support_proxy_used") is False))

    # G3: No-claim false flags
    for flag in ("external_benchmark_performance_claimed", "leaderboard_entry_claimed",
                 "downstream_agent_value_proven", "calibration_claimed",
                 "method_winner_claimed", "promotion_ready", "default_should_change",
                 "runtime_behavior_changed", "retriever_changed", "pack_builder_changed",
                 "backend_changed", "default_policy_changed", "evidencecore_semantics_changed",
                 "provider_calls_made", "remote_provider_calls_made",
                 "algorithm_changed_during_bea_fd2a", "weights_tuned_during_bea_fd2a",
                 "v04_full_matrix_claimed", "v03_tuned_during_bea_fd2a",
                 "fd1_artifact_modified", "role_proxy_assigned",
                 "posthoc_threshold_search", "private_decomposition_used_for_selection",
                 "gold_labels_used_for_selection"):
        checks.append(_check(f"false_{flag}", skeleton.get(flag) is False))

    # G4: License fields
    for field, expected in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{field}", skeleton.get(field) == expected))

    # G5: Fixed protocol constants
    checks.append(_check("fixed_budget_5", FIXED_BUDGET == 5))
    checks.append(_check("fixed_methods", FIXED_METHODS == "bm25,regex,symbol"))
    checks.append(_check("target_successful_38", TARGET_SUCCESSFUL_RECORDS == 38))
    checks.append(_check("min_cb_20", MIN_CONTEXTBENCH_SUCCESSFUL == 20))
    checks.append(_check("min_rq_10", MIN_REPOQA_SUCCESSFUL == 10))
    checks.append(_check("raw_cap_cb_480", RAW_ATTEMPT_CAP_CONTEXTBENCH == 480))
    checks.append(_check("raw_cap_rq_240", RAW_ATTEMPT_CAP_REPOQA == 240))
    checks.append(_check("ci_min_records_30", CI_MIN_RECORDS_SUCCESSFUL == 30))
    checks.append(_check("sampling_mode", SAMPLING_MODE == "success_quota"))
    checks.append(_check("bea5_overlap_disclosed", "disclosed" in BEA5_OVERLAP_POLICY))
    checks.append(_check("p1_overlap_disclosed", "disclosed" in BEA_V04_P1_OVERLAP_POLICY))
    checks.append(_check("p2_overlap_disclosed", "disclosed" in BEA_V04_P2_OVERLAP_POLICY))
    checks.append(_check("p3_overlap_disclosed", "disclosed" in BEA_V04_P3_OVERLAP_POLICY))
    checks.append(_check("fd1_overlap_read_only", "read_only" in FD1_OVERLAP_POLICY))
    checks.append(_check("blocking_categories_count_7", len(BLOCKING_FAILURE_CATEGORIES) == 7))

    # G6: Mandatory excluded windows
    checks.append(_check("cb_mandatory_windows_3", len(CONTEXTBENCH_MANDATORY_EXCLUDED_WINDOWS) == 3))
    checks.append(_check("rq_mandatory_windows_3", len(REPOQA_MANDATORY_EXCLUDED_WINDOWS) == 3))
    checks.append(_check("cb_excludes_40_to_160",
        _is_index_excluded(40, CONTEXTBENCH_MANDATORY_EXCLUDED_WINDOWS)
        and _is_index_excluded(159, CONTEXTBENCH_MANDATORY_EXCLUDED_WINDOWS)
        and not _is_index_excluded(160, CONTEXTBENCH_MANDATORY_EXCLUDED_WINDOWS)))
    checks.append(_check("rq_excludes_20_to_80",
        _is_index_excluded(20, REPOQA_MANDATORY_EXCLUDED_WINDOWS)
        and _is_index_excluded(79, REPOQA_MANDATORY_EXCLUDED_WINDOWS)
        and not _is_index_excluded(80, REPOQA_MANDATORY_EXCLUDED_WINDOWS)))

    # G7: Fixed arms (exactly 5; no role-proxy arms, no seeded random, no v0.2)
    checks.append(_check("fixed_arms_count_5", len(skeleton.get("fixed_arms", [])) == 5))
    for arm in FIXED_ARMS:
        checks.append(_check(f"fixed_arms_has_{arm}", arm in skeleton.get("fixed_arms", [])))
    for bad_arm in ("seeded_random_same_budget", "setwise_complementarity_v0_2",
                    "setwise_complementarity_v0_4_p1", "setwise_complementarity_v0_4_p2",
                    "setwise_complementarity_v0_4_p3_support_repair",
                    "support_complementarity_repair_only_same_budget",
                    "bea_v0_2_diversity_risk", "bea_v0",
                    "agreement_only_same_budget"):
        checks.append(_check(f"no_arm_{bad_arm}", bad_arm not in skeleton.get("fixed_arms", [])))
    checks.append(_check("treatment_arm", skeleton.get("treatment_arm") == ARM_FD1_LOSS_WEIGHTED))
    checks.append(_check("coverage_only_arm", skeleton.get("coverage_only_arm") == ARM_FD1_COVERAGE_ONLY))
    checks.append(_check("quality_baseline_arm", skeleton.get("quality_baseline_arm") == ARM_BEA_V0_3))
    checks.append(_check("has_fd1_coverage_only_arm", ARM_FD1_COVERAGE_ONLY in FIXED_ARMS))
    checks.append(_check("has_fd1_loss_weighted_arm", ARM_FD1_LOSS_WEIGHTED in FIXED_ARMS))

    # G8: FD1 weight derivation from synthetic loss records
    checks.append(_check("weights_5_categories", len(fd1_weights) == 5))
    for cat in FD1_PLAN_CATEGORIES:
        checks.append(_check(f"weight_present_{cat}", cat in fd1_weights))
    derivable_total = sum(fd1_weights[c] for c in FD1_DERIVABLE_CATEGORIES)
    checks.append(_check("derivable_weights_sum_to_1", abs(derivable_total - 1.0) < 1e-6))
    checks.append(_check("duplicate_weight_fixed_default",
        fd1_weights["redundant_same_file_candidates"] == FD1_FIXED_DUPLICATE_WEIGHT))
    # Synthetic loss_sums: gold_file_absent=7, correct_file_wrong_span=3,
    # budget_spent_on_low_marginal_gain=4, latency_without_quality_gain=6 => total=20.
    checks.append(_check("weight_gold_file_absent_0_35", abs(fd1_weights["gold_file_absent"] - 7.0 / 20.0) < 1e-6))
    checks.append(_check("weight_correct_file_wrong_span_0_15", abs(fd1_weights["correct_file_wrong_span"] - 3.0 / 20.0) < 1e-6))
    checks.append(_check("weight_budget_spent_0_20", abs(fd1_weights["budget_spent_on_low_marginal_gain"] - 4.0 / 20.0) < 1e-6))
    checks.append(_check("weight_latency_0_30", abs(fd1_weights["latency_without_quality_gain"] - 6.0 / 20.0) < 1e-6))
    # Uniform fallback when all loss_sums are zero.
    zero_weights = _derive_fd1_category_weights([])
    checks.append(_check("uniform_fallback_when_no_loss",
        all(zero_weights[c]["derivation"] == "uniform_fallback_no_fd1_loss" for c in FD1_DERIVABLE_CATEGORIES)))
    checks.append(_check("uniform_fallback_sum_1",
        abs(sum(zero_weights[c]["weight"] for c in FD1_DERIVABLE_CATEGORIES) - 1.0) < 1e-6))

    # G9: FD1-objective components
    checks.append(_check("components_count_5", len(FD1_OBJECTIVE_COMPONENTS) == 5))
    for comp in FD1_OBJECTIVE_COMPONENTS:
        checks.append(_check(f"component_{comp}_present", comp in FD1_OBJECTIVE_COMPONENTS))
    checks.append(_check("penalty_components_2", len(FD1_PENALTY_COMPONENTS) == 2))
    checks.append(_check("category_to_component_5", len(FD1_CATEGORY_TO_COMPONENT) == 5))

    # G10: FD1 loss-weighted policy mechanics
    checks.append(_check("fd1lw_accepts_nonempty", len(fd1lw_acc) > 0))
    checks.append(_check("fd1lw_respects_budget_5", len(fd1lw_acc) <= 5))
    fd1lw_b3, _, _, _, _, _ = _fd1_loss_weighted_setwise_policy(candidates, query, 3, fd1_weights)
    checks.append(_check("fd1lw_respects_budget_3", len(fd1lw_b3) <= 3))
    fd1lw_b0, _, _, _, _, _ = _fd1_loss_weighted_setwise_policy(candidates, query, 0, fd1_weights)
    checks.append(_check("fd1lw_budget_0_empty", len(fd1lw_b0) == 0))
    checks.append(_check("fd1lw_empty_candidates",
        len(_fd1_loss_weighted_setwise_policy([], query, 5, fd1_weights)[0]) == 0))
    checks.append(_check("fd1lw_action_order_nonempty", len(fd1lw_ao) > 0))
    checks.append(_check("fd1lw_budget_trace_nonempty", len(fd1lw_bt) > 0))
    checks.append(_check("fd1lw_stop_reason_present", isinstance(fd1lw_sr, str) and len(fd1lw_sr) > 0))
    checks.append(_check("fd1lw_mechanism_summary_present", isinstance(fd1lw_mech, dict) and len(fd1lw_mech) > 0))
    checks.append(_check("fd1lw_setwise_used", fd1lw_mech.get("setwise_used") is True))
    checks.append(_check("fd1lw_fd1_weights_used", fd1lw_mech.get("fd1_weights_used") is True))
    checks.append(_check("fd1lw_features_nonempty", len(fd1lw_features) > 0))

    # G11: Coverage-only policy mechanics
    checks.append(_check("cov_accepts_nonempty", len(cov_acc) > 0))
    checks.append(_check("cov_respects_budget_5", len(cov_acc) <= 5))
    checks.append(_check("cov_setwise_used", cov_mech.get("setwise_used") is True))
    checks.append(_check("cov_fd1_weights_not_used", cov_mech.get("fd1_weights_used") is False))
    checks.append(_check("cov_budget_0_empty",
        len(_fd1_coverage_only_setwise_policy([], query, 5)[0]) == 0))

    # G12: Coverage-only vs FD1 treatment are SEPARATE
    checks.append(_check("coverage_and_treatment_different_arms",
        COVERAGE_ONLY_ARM != TREATMENT_ARM))
    checks.append(_check("coverage_no_fd1_weights", cov_mech.get("fd1_weights_used") is False))
    checks.append(_check("treatment_has_fd1_weights", fd1lw_mech.get("fd1_weights_used") is True))
    # Coverage-only priority uses only v0.2 base; treatment adds FD1 objective.
    # They may select differently when the FD1 objective changes the ranking.
    checks.append(_check("coverage_mechanism_label", cov_mech.get("arm_label") == "coverage_only"))
    checks.append(_check("treatment_mechanism_label", fd1lw_mech.get("arm_label") == "fd1_loss_weighted"))

    # G13: FD1-objective component computation (runtime-clean)
    qt = bea2._query_tokens(query)
    entry = deduped[0] if deduped else {}
    comps = _compute_fd1_objective_components(
        entry, qt, set(), set(), set(), 0, 5,
    )
    for comp in FD1_OBJECTIVE_COMPONENTS:
        checks.append(_check(f"component_value_{comp}_present", comp in comps))
        checks.append(_check(f"component_value_{comp}_in_range",
            0.0 <= float(comps[comp]) <= 1.0))
    obj = _compute_fd1_objective(comps, fd1_weights)
    checks.append(_check("objective_is_number", isinstance(obj, (int, float))))

    # G14: Hard gates constants
    checks.append(_check("gate_diff_v03_025", GATE_SETWISE_DIFF_VS_V03 == 0.25))
    checks.append(_check("gate_diff_cov_015", GATE_SETWISE_DIFF_VS_COVERAGE == 0.15))
    checks.append(_check("gate_qm_fr_003", GATE_QUALITY_MARGIN_FILE_RECALL == 0.03))
    checks.append(_check("gate_qm_mrr_005", GATE_QUALITY_MARGIN_MRR == 0.05))
    checks.append(_check("gate_qm_span_002", GATE_QUALITY_MARGIN_SPAN == 0.02))
    checks.append(_check("gate_latency_ratio_115", GATE_LATENCY_RATIO == 1.15))

    # G15: Public record tables present + nonempty
    for table in ("source_run_records", "arm_metric_records", "arm_delta_records",
                  "win_tie_loss_records", "fd1_category_loss_records",
                  "fd1_category_rate_records", "fd1_objective_component_records",
                  "ablation_delta_records", "setwise_behavior_records",
                  "benchmark_attempt_records", "failure_category_count_records",
                  "hard_gate_records", "manifests"):
        checks.append(_check(f"table_{table}_present", isinstance(skeleton.get(table), list)))
        checks.append(_check(f"table_{table}_nonempty", len(skeleton.get(table, [])) > 0))

    # G16: Natural-key uniqueness
    checks.append(_check("amr_unique", not _check_unique_records(skeleton.get("arm_metric_records", []), _amr_natural_key, "arm_metric_records")))
    checks.append(_check("adr_unique", not _check_unique_records(skeleton.get("arm_delta_records", []), _adr_natural_key, "arm_delta_records")))
    checks.append(_check("wtl_unique", not _check_unique_records(skeleton.get("win_tie_loss_records", []), _wtl_natural_key, "win_tie_loss_records")))
    checks.append(_check("fclr_unique", not _check_unique_records(skeleton.get("fd1_category_loss_records", []), _fclr_natural_key, "fd1_category_loss_records")))
    checks.append(_check("fcrr_unique", not _check_unique_records(skeleton.get("fd1_category_rate_records", []), _fcrr_natural_key, "fd1_category_rate_records")))
    checks.append(_check("focr_unique", not _check_unique_records(skeleton.get("fd1_objective_component_records", []), _focr_natural_key, "fd1_objective_component_records")))
    checks.append(_check("abdr_unique", not _check_unique_records(skeleton.get("ablation_delta_records", []), _abdr_natural_key, "ablation_delta_records")))
    checks.append(_check("sbr_unique", not _check_unique_records(skeleton.get("setwise_behavior_records", []), _sbr_natural_key, "setwise_behavior_records")))
    checks.append(_check("srr_unique", not _check_unique_records(skeleton.get("source_run_records", []), _srr_natural_key, "source_run_records")))
    checks.append(_check("man_unique", not _check_unique_records(skeleton.get("manifests", []), _man_natural_key, "manifests")))
    checks.append(_check("hard_gate_unique", not _check_unique_records(skeleton.get("hard_gate_records", []), lambda r: (r["gate"],), "hard_gate_records")))
    checks.append(_check("fcc_unique", not _check_unique_records(skeleton.get("failure_category_count_records", []), lambda r: (r["failure_category"],), "failure_category_count_records")))

    # G17: Private manifests (5) in manifests table; NOT top-level
    manifest_by_name = {r.get("manifest_name"): r for r in skeleton.get("manifests", [])}
    for manifest_name, schema_ver in (
        ("private_score_manifest", PRIVATE_SCORE_SCHEMA_VERSION),
        ("private_decision_manifest", PRIVATE_DECISION_SCHEMA_VERSION),
        ("private_fd1_objective_feature_manifest", PRIVATE_FD1_OBJECTIVE_FEATURE_SCHEMA_VERSION),
        ("private_posthoc_decomposition_manifest", PRIVATE_POSTHOC_DECOMPOSITION_SCHEMA_VERSION),
        ("private_objective_config_manifest", PRIVATE_OBJECTIVE_CONFIG_SCHEMA_VERSION),
    ):
        m = manifest_by_name.get(manifest_name, {})
        checks.append(_check(f"{manifest_name}_present_in_table", isinstance(m, dict) and len(m) > 0))
        checks.append(_check(f"{manifest_name}_not_top_level", manifest_name not in skeleton))
        checks.append(_check(f"{manifest_name}_path_not_serialized", m.get("path_publicly_serialized") is False))
        checks.append(_check(f"{manifest_name}_hash_64", len(m.get("manifest_hash", "")) == 64))
        checks.append(_check(f"{manifest_name}_schema", m.get("schema_version") == schema_ver))
    # No top-level manifest dict mirrors (P3 discipline).
    for forbidden_top in ("private_score_manifest", "private_decision_manifest",
                          "private_fd1_objective_feature_manifest",
                          "private_posthoc_decomposition_manifest",
                          "private_objective_config_manifest"):
        checks.append(_check(f"no_top_level_{forbidden_top}", forbidden_top not in skeleton))

    # G18: Hard gates present as records-only table (NOT a dict)
    hg = skeleton.get("hard_gate_records", [])
    checks.append(_check("hard_gate_records_list", isinstance(hg, list) and len(hg) > 0))
    gate_names = {r.get("gate") for r in hg if isinstance(r, dict)}
    for field in ("records_successful", "contextbench_successful", "repoqa_successful",
                  "budget_fixed_5", "role_proxy_used_false",
                  "target_support_proxy_used_false",
                  "selection_diff_rate_fd1lw_vs_v03",
                  "selection_diff_rate_fd1lw_vs_coverage",
                  "mean_duplicate_file_count_fd1lw",
                  "mean_candidate_source_diversity_fd1lw",
                  "composite_fd1_loss_fd1lw", "dominant_category_improves",
                  "file_recall_10_fd1lw", "mrr_fd1lw", "span_f05_10_fd1lw",
                  "latency_seconds_fd1lw", "behavior_ok", "fd1_loss_ok", "quality_ok"):
        checks.append(_check(f"hard_gate_records_has_{field}", field in gate_names))

    # G19: Scanner rejects forbidden keys (role-proxy, per-record, private, dynamic)
    for fk in ("private_score_path", "action_order", "priority_components",
               "selected_decisions", "budget_trace", "stop_reason",
               "candidate_features", "score_outcome", "private_record_id",
               "role_proxy", "role_proxy_assignment", "target_proxy",
               "support_proxy", "target_anchor", "per_record_role_labels",
               "fd2a_role_assignment", "role_proxy_summary",
               "private_fd1_objective_feature_path",
               "private_posthoc_decomposition_path",
               "private_objective_config_path",
               "gold_paths", "gold_lines",
               "hard_gates", "failure_category_counts",
               "winner", "calibration", "method_winner",
               "self_test_checks", "checks", "fd1_source_artifact_path",
               "fd1_objective_features", "posthoc_decomposition",
               "objective_config", "phase_run_id", "run_id"):
        leaked = dict(skeleton)
        leaked[fk] = "leak"
        checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_fd2a(leaked))))

    # G20: Scanner allows safe
    safe_sample = {
        "schema_version": SCHEMA_VERSION,
        "arm": ARM_FD1_LOSS_WEIGHTED,
        "metric": "mrr",
        "value": 0.5,
        "record_count": 5,
        "manifests": [{"manifest_name": "private_score_manifest",
                       "records_written": True, "record_count": 5,
                       "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
                       "manifest_hash": "a" * 64, "storage_class": "tmp_private",
                       "path_publicly_serialized": False}],
    }
    checks.append(_check("scanner_allows_safe", not _scan_fd2a(safe_sample)))

    # G21: Fail-closed
    try:
        _enforce_fd2a_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk in ("private_score_path", "action_order", "role_proxy",
               "gold_paths", "winner", "hard_gates", "failure_category_counts",
               "self_test_checks", "fd1_source_artifact_path"):
        leaked = dict(skeleton)
        leaked[lk] = "leak"
        try:
            _enforce_fd2a_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # G22: Self-scan clean
    checks.append(_check("self_scan_clean", not _scan_fd2a(skeleton)))
    checks.append(_check("unavail_scan_clean", not _scan_fd2a(unavail)))

    # G23: CLI surface
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for opt in ("--self-test", "--contextbench-row-offset", "--contextbench-row-limit",
                "--repoqa-needle-offset", "--repoqa-needle-limit", "--budget",
                "--methods", "--openlocus", "--out", "--private-score-dir",
                "--enable-external-benchmark-network", "--fd1-artifact"):
        checks.append(_check(f"cli_has_{opt}", opt in option_strings))

    # G24: Private row writer
    with tempfile.TemporaryDirectory(prefix="fd2a_st_") as sd:
        sf = Path(sd) / "fd2a.private.jsonl"
        _write_private_row(sf, {"test": 1})
        _write_private_row(sf, {"test": 2})
        lines = sf.read_text(encoding="utf-8").splitlines()
        checks.append(_check("writer_2_rows", len(lines) == 2))
        checks.append(_check("writer_parse",
            all(isinstance(json.loads(l), dict) for l in lines if l)))
        # objective-config JSON writer
        cfg_path = Path(sd) / "fd2a.objective_config.json"
        _write_private_objective_config(cfg_path, objective_config)
        loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
        checks.append(_check("objective_config_written", isinstance(loaded, dict)))
        checks.append(_check("objective_config_has_weights",
            "fd1_category_weights" in loaded and len(loaded["fd1_category_weights"]) == 5))
        checks.append(_check("objective_config_no_path",
            "fd1_source_artifact_path" not in loaded))
        checks.append(_check("objective_config_has_hash",
            len(loaded.get("fd1_source_artifact_hash", "")) == 64))

    # G25: FD1 plan categories (5)
    checks.append(_check("fd1_plan_categories_5", len(FD1_PLAN_CATEGORIES) == 5))
    for cat in FD1_PLAN_CATEGORIES:
        checks.append(_check(f"fd1_category_{cat}", cat in FD1_PLAN_CATEGORIES))

    # G26: Counts-only self-test (no detail lists)
    checks.append(_check("has_self_test_checks_total", "self_test_checks_total" in skeleton))
    checks.append(_check("has_self_test_checks_passed", "self_test_checks_passed" in skeleton))
    for ff in ("self_test_checks", "self_test_details", "self_test_list", "checks", "check_list"):
        checks.append(_check(f"no_{ff}", ff not in skeleton))

    # G27: No winner/calibration anywhere
    for field in ("winner", "best_method", "recommended_default", "method_winner", "calibration"):
        checks.append(_check(f"missing_{field}", field not in skeleton))

    # G28: Aggregate runtime present
    checks.append(_check("has_runtime", "aggregate_runtime_seconds" in skeleton))
    checks.append(_check("unavail_no_runtime", "aggregate_runtime_seconds" not in unavail))

    # G29: Fixed protocol validation
    try:
        _validate_fixed_protocol(
            contextbench_row_offset=0,
            contextbench_row_limit=RAW_ATTEMPT_CAP_CONTEXTBENCH,
            repoqa_needle_offset=0,
            repoqa_needle_limit=RAW_ATTEMPT_CAP_REPOQA,
            budget=5, methods=ALLOWED_METHODS,
        )
        checks.append(_check("fixed_protocol_accepts_exact", True))
    except SystemExit:
        checks.append(_check("fixed_protocol_accepts_exact", False))
    try:
        _validate_fixed_protocol(
            contextbench_row_offset=80,
            contextbench_row_limit=RAW_ATTEMPT_CAP_CONTEXTBENCH,
            repoqa_needle_offset=0,
            repoqa_needle_limit=RAW_ATTEMPT_CAP_REPOQA,
            budget=5, methods=ALLOWED_METHODS,
        )
        checks.append(_check("fixed_protocol_rejects_offset", False))
    except SystemExit:
        checks.append(_check("fixed_protocol_rejects_offset", True))

    # G30: Setwise behavior helpers
    checks.append(_check("dup_count_no_dup", _accepted_file_duplicates([{"path": "a"}, {"path": "b"}]) == 0))
    checks.append(_check("dup_count_with_dup", _accepted_file_duplicates([{"path": "a"}, {"path": "a"}]) == 1))
    checks.append(_check("selection_differs_detects_diff", _selection_differs(v03_acc, []) is True))

    # G31: Statuses enum
    for status in ("bea_fd2a_direct_fd1_objective_pass", "partial_fd1_objective_signal",
                   "no_go_no_selection_change", "no_go_no_fd1_loss_reduction",
                   "no_go_objective_ablation_only", "no_go_quality_regression",
                   "unavailable_with_reason", "fail_forbidden_scan", "fail_schema_contract"):
        checks.append(_check(f"status_enum_{status}", isinstance(status, str)))

    # G32: FD2-A runtime-clean invariance (tainted candidates with gold/row_id
    # produce identical selections).
    tainted = []
    for c in candidates:
        tc = dict(c)
        tc["gold_paths"] = ["src/path1.py"]
        tc["row_id"] = "leaked"
        tc["benchmark_label"] = "positive"
        tainted.append(tc)
    fd1lw_t, _, _, _, _, _ = _fd1_loss_weighted_setwise_policy(tainted, query, 5, fd1_weights)

    def _ak(a): return (a["path"], a["start_line"], a["end_line"])
    checks.append(_check("fd2a_runtime_clean_invariance",
        [_ak(a) for a in fd1lw_acc] == [_ak(a) for a in fd1lw_t]))

    # G33: Unavailable report has empty tables
    for k in ("source_run_records", "arm_metric_records", "arm_delta_records",
              "win_tie_loss_records", "fd1_category_loss_records",
              "fd1_category_rate_records", "fd1_objective_component_records",
              "ablation_delta_records", "setwise_behavior_records", "hard_gate_records"):
        checks.append(_check(f"unavail_empty_{k}", unavail.get(k) == []))

    # G34: No dynamic hard_gates / failure_category_counts dicts
    checks.append(_check("no_hard_gates_dict", "hard_gates" not in skeleton))
    checks.append(_check("no_failure_category_counts_dict", "failure_category_counts" not in skeleton))
    checks.append(_check("no_hard_gates_dict_unavail", "hard_gates" not in unavail))
    checks.append(_check("no_failure_category_counts_dict_unavail", "failure_category_counts" not in unavail))

    # G35: FD1 category loss / rate records fields
    fclr_fields = {r.get("fd1_category") for r in skeleton.get("fd1_category_loss_records", [])}
    for cat in FD1_PLAN_CATEGORIES:
        checks.append(_check(f"fclr_has_{cat}", cat in fclr_fields))
    fcrr_fields = {r.get("fd1_category") for r in skeleton.get("fd1_category_rate_records", [])}
    for cat in FD1_PLAN_CATEGORIES:
        checks.append(_check(f"fcrr_has_{cat}", cat in fcrr_fields))

    # G36: FD1 objective component records fields
    focr_fields = {r.get("component") for r in skeleton.get("fd1_objective_component_records", [])}
    for comp in FD1_OBJECTIVE_COMPONENTS:
        checks.append(_check(f"focr_has_{comp}", comp in focr_fields))
    checks.append(_check("focr_has_fd1_objective_mean", "fd1_objective_mean" in focr_fields))

    # G37: Ablation delta records fields
    abdr_fields = {(r.get("component"), r.get("baseline_arm"), r.get("treatment_arm"))
                   for r in skeleton.get("ablation_delta_records", [])}
    for comp in ("budget_used", "duplicate_file_count", "source_diversity"):
        checks.append(_check(f"abdr_has_{comp}",
            (comp, COVERAGE_ONLY_ARM, TREATMENT_ARM) in abdr_fields))

    # G38: provider_calls = 0
    checks.append(_check("provider_calls_zero", skeleton.get("provider_calls") == 0))
    checks.append(_check("unavail_provider_calls_zero", unavail.get("provider_calls") == 0))

    all_passed = all(c["passed"] for c in checks if c is not None)
    return checks, all_passed


# --- CLI ---


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description="BEA-FD2-A Direct FD1-Objective Setwise Acquisition Smoke"
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--contextbench-row-offset", type=int, default=0)
    ap.add_argument("--contextbench-row-limit", type=int,
                    default=RAW_ATTEMPT_CAP_CONTEXTBENCH)
    ap.add_argument("--repoqa-needle-offset", type=int, default=0)
    ap.add_argument("--repoqa-needle-limit", type=int,
                    default=RAW_ATTEMPT_CAP_REPOQA)
    ap.add_argument("--budget", type=int, default=FIXED_BUDGET)
    ap.add_argument("--methods", default=DEFAULT_METHODS)
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--private-score-dir", default=None)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    return ap


# --- Network smoke runner ---


def _run_network_smoke(
    *, contextbench_row_offset: int, contextbench_row_limit: int,
    repoqa_needle_offset: int, repoqa_needle_limit: int,
    budget: int, openlocus_bin: str,
    openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    private_score_dir: Path,
    private_score_storage_class: str, phase_run_id: str,
    fd1_artifact_path: Path,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    smoke_start = time.perf_counter()

    # Derive frozen FD1 weights BEFORE evaluation from the committed FD1
    # artifact (read-only; category_metric_loss_records only).
    loss_records, fd1_schema, fd1_hash, fd1_status = _load_fd1_loss_records(
        fd1_artifact_path
    )
    if fd1_status != "pass" or not loss_records:
        fcc["fd1_artifact_missing" if fd1_status == "fd1_artifact_missing"
            else "fd1_loss_records_missing"] = 1
        return _build_unavailable_report(
            fd1_status, self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
            records_attempted_total=0, failure_category_counts=fcc,
        )
    fd1_weights_info = _derive_fd1_category_weights(loss_records)
    fd1_weights = {cat: float(fd1_weights_info[cat]["weight"]) for cat in FD1_PLAN_CATEGORIES}

    # Write private objective-config JSON (frozen weights + source hash).
    score_hash = _private_score_manifest_hash()
    decision_hash = _private_decision_manifest_hash()
    feat_hash = _private_fd1_objective_feature_manifest_hash()
    decomp_hash = _private_posthoc_decomposition_manifest_hash()
    objcfg_hash = _private_objective_config_manifest_hash()
    score_file = private_score_dir / "bea_fd2a.private.jsonl"
    decision_file = private_score_dir / "bea_fd2a.decision.jsonl"
    feat_file = private_score_dir / "bea_fd2a.fd1_objective_feature.jsonl"
    decomp_file = private_score_dir / "bea_fd2a.posthoc_decomposition.jsonl"
    objcfg_file = private_score_dir / "bea_fd2a.objective_config.json"
    for f in (score_file, decision_file, feat_file, decomp_file, objcfg_file):
        try:
            f.unlink()
        except OSError:
            pass
    objective_config = _build_objective_config(
        phase_run_id=phase_run_id, loss_records=loss_records,
        fd1_source_schema_version=fd1_schema,
        fd1_source_artifact_hash=fd1_hash,
    )
    try:
        _write_private_objective_config(objcfg_file, objective_config)
    except OSError:
        fcc["private_objective_config_write_failed"] = (
            fcc.get("private_objective_config_write_failed", 0) + 1
        )

    per_record_arm_metrics: list[dict[str, dict[str, Any]]] = []
    arm_aggs_raw: dict[str, dict[str, list[float]]] = {
        arm: {m: [] for m in ARM_METRIC_ALLOWLIST} for arm in FIXED_ARMS
    }
    arm_record_counts: dict[str, int] = {arm: 0 for arm in FIXED_ARMS}
    per_record_setwise_summaries: list[dict[str, Any]] = []
    per_record_categories: dict[str, list[dict[str, dict[str, Any]]]] = {
        arm: [] for arm in FIXED_ARMS
    }
    records_attempted_total = 0
    records_evaluated = 0
    records_successful = 0
    records_failed = 0
    records_excluded = 0
    contextbench_attempted = 0
    contextbench_successful = 0
    contextbench_excluded = 0
    repoqa_attempted = 0
    repoqa_successful = 0
    repoqa_excluded = 0
    quota_reached = False

    cb_rows, cb_status, cb_nc, cb_fcc = _fetch_heldout_contextbench_rows(
        0, RAW_ATTEMPT_CAP_CONTEXTBENCH
    )
    network_calls += cb_nc
    for k, v in cb_fcc.items():
        if k in fcc:
            fcc[k] += v
    cb_eligible_rows: list[tuple[int, dict[str, Any]]] = []
    cb_excluded_prior_window_count = 0
    if cb_status == "pass" and cb_rows:
        for idx, row in enumerate(cb_rows):
            if _is_index_excluded(idx, CONTEXTBENCH_MANDATORY_EXCLUDED_WINDOWS):
                cb_excluded_prior_window_count += 1
                continue
            cb_eligible_rows.append((idx, row))
    cb_eligible_count = len(cb_eligible_rows)

    rq_needles, rq_status, rq_nc, rq_fcc = _fetch_heldout_repoqa_needles(
        0, RAW_ATTEMPT_CAP_REPOQA
    )
    network_calls += rq_nc
    for k, v in rq_fcc.items():
        if k in fcc:
            fcc[k] += v
    rq_eligible_needles: list[tuple[int, dict[str, Any]]] = []
    rq_excluded_prior_window_count = 0
    if rq_status == "pass" and rq_needles:
        for idx, needle in enumerate(rq_needles):
            if _is_index_excluded(idx, REPOQA_MANDATORY_EXCLUDED_WINDOWS):
                rq_excluded_prior_window_count += 1
                continue
            rq_eligible_needles.append((idx, needle))
    rq_eligible_count = len(rq_eligible_needles)

    cb_ptr = 0
    rq_ptr = 0
    cb_done = (cb_status != "pass" or not cb_eligible_rows)
    rq_done = (rq_status != "pass" or not rq_eligible_needles)

    def _quota_satisfied() -> bool:
        return (records_successful >= TARGET_SUCCESSFUL_RECORDS
                and contextbench_successful >= MIN_CONTEXTBENCH_SUCCESSFUL
                and repoqa_successful >= MIN_REPOQA_SUCCESSFUL)

    while not (cb_done and rq_done):
        if _quota_satisfied():
            quota_reached = True
            fcc["quota_reached_stop"] = fcc.get("quota_reached_stop", 0) + 1
            break

        if not cb_done and cb_ptr < len(cb_eligible_rows):
            idx, row = cb_eligible_rows[cb_ptr]
            cb_ptr += 1
            if cb_ptr >= len(cb_eligible_rows):
                cb_done = True
            records_attempted_total += 1
            contextbench_attempted += 1
            records_evaluated += 1
            gold_paths, gold_lines, gc_status = c5a._parse_gold_context(
                row.get("gold_context")
            )
            if gc_status != "pass":
                fcc["contextbench_label_parse_failed"] += 1
                records_failed += 1
                records_excluded += 1
                contextbench_excluded += 1
                continue
            query = c5a._sanitize_query(
                row.get("problem_statement", ""), "first_paragraph"
            )
            if not query:
                fcc["contextbench_no_python_rows"] += 1
                records_failed += 1
                records_excluded += 1
                contextbench_excluded += 1
                continue
            repo_url = row.get("repo_url", "")
            base_commit = row.get("base_commit", "")
            if not isinstance(repo_url, str) or not isinstance(base_commit, str) or not repo_url or not base_commit:
                fcc["contextbench_no_python_rows"] += 1
                records_failed += 1
                records_excluded += 1
                contextbench_excluded += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"fd2a_cb_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(repo_url, base_commit, rwd)
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    fcc["materialization_failed"] = fcc.get("materialization_failed", 0) + 1
                    records_failed += 1
                    records_excluded += 1
                    contextbench_excluded += 1
                    continue
                repo_root = rwd / "repo"
                per_arm, fcc, rec_summary = _evaluate_record(
                    openlocus_bin=openlocus_bin, benchmark="contextbench",
                    private_record_id=f"contextbench-{idx}",
                    task_id=f"cb_row_{idx}", query=query,
                    gold_paths=gold_paths, gold_lines=gold_lines,
                    repo_root=repo_root, budget=budget,
                    score_path=score_file, decision_path=decision_file,
                    fd1_objective_feature_path=feat_file,
                    posthoc_decomposition_path=decomp_file,
                    phase_run_id=phase_run_id, fcc=fcc,
                    fd1_weights=fd1_weights,
                )
                if per_arm is None:
                    records_failed += 1
                    records_excluded += 1
                    contextbench_excluded += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_setwise_summaries.append(rec_summary)
                v03_m = per_arm.get(ARM_BEA_V0_3, {})
                fd1lw_m = per_arm.get(TREATMENT_ARM, {})
                v03_lat = float(v03_m.get("latency_seconds", 0.0))
                v03_dup = _accepted_file_duplicates(
                    [e for e in [{"path": p} for p in []] for e in []]  # placeholder; real dup below
                )
                v03_acc_count = int(rec_summary.get("setwise_behavior", {}).get("v03_budget_used", 0))
                v03_cats = _classify_fd1_categories(v03_m, v03_acc_count, v03_lat, v03_m, v03_lat, int(rec_summary.get("setwise_behavior", {}).get("duplicate_file_count_v03", 0)))
                for arm_id in FIXED_ARMS:
                    arm_m = per_arm.get(arm_id, {})
                    arm_dup = int(rec_summary.get("setwise_behavior", {}).get(
                        "duplicate_file_count_fd1lw" if arm_id == TREATMENT_ARM
                        else "duplicate_file_count_coverage" if arm_id == COVERAGE_ONLY_ARM
                        else "duplicate_file_count_v03" if arm_id == ARM_BEA_V0_3
                        else "duplicate_file_count_v03", 0))
                    arm_budget = int(rec_summary.get("setwise_behavior", {}).get(
                        "fd1lw_budget_used" if arm_id == TREATMENT_ARM
                        else "coverage_budget_used" if arm_id == COVERAGE_ONLY_ARM
                        else "v03_budget_used" if arm_id == ARM_BEA_V0_3
                        else "v03_budget_used", 0))
                    arm_lat = float(arm_m.get("latency_seconds", 0.0))
                    cats = _classify_fd1_categories(arm_m, arm_budget, arm_lat, v03_m, v03_lat, arm_dup)
                    per_record_categories[arm_id].append(cats)
                for arm_id, metrics in per_arm.items():
                    arm_record_counts[arm_id] = arm_record_counts.get(arm_id, 0) + 1
                    for m in ARM_METRIC_ALLOWLIST:
                        if m in metrics:
                            arm_aggs_raw[arm_id][m].append(float(metrics[m]))
                records_successful += 1
                contextbench_successful += 1

        if _quota_satisfied():
            quota_reached = True
            fcc["quota_reached_stop"] = fcc.get("quota_reached_stop", 0) + 1
            break

        if not rq_done and rq_ptr < len(rq_eligible_needles):
            idx, needle = rq_eligible_needles[rq_ptr]
            rq_ptr += 1
            if rq_ptr >= len(rq_eligible_needles):
                rq_done = True
            records_attempted_total += 1
            repoqa_attempted += 1
            records_evaluated += 1
            query = c5d._sanitize_needle_description(
                needle.get("needle_description", "")
            )
            if not query:
                fcc["repoqa_needle_parse_failed"] += 1
                records_failed += 1
                records_excluded += 1
                repoqa_excluded += 1
                continue
            repo_url = needle.get("repo_url", "")
            commit_sha = needle.get("commit_sha", "")
            needle_path = needle.get("needle_path", "")
            start_line = needle.get("needle_start_line", 0)
            end_line = needle.get("needle_end_line", 0)
            if (not isinstance(repo_url, str) or not repo_url
                or not isinstance(commit_sha, str) or not commit_sha
                or not isinstance(needle_path, str) or not needle_path):
                fcc["repoqa_needle_parse_failed"] += 1
                records_failed += 1
                records_excluded += 1
                repoqa_excluded += 1
                continue
            with tempfile.TemporaryDirectory(prefix=f"fd2a_rq_{idx}_") as rds:
                rwd = Path(rds)
                clone_ok, _, clone_fcc = c5d._clone_and_checkout(repo_url, commit_sha, rwd)
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    fcc["materialization_failed"] = fcc.get("materialization_failed", 0) + 1
                    records_failed += 1
                    records_excluded += 1
                    repoqa_excluded += 1
                    continue
                repo_root = rwd / "repo"
                per_arm, fcc, rec_summary = _evaluate_record(
                    openlocus_bin=openlocus_bin, benchmark="repoqa",
                    private_record_id=f"repoqa-{idx}",
                    task_id=f"rq_needle_{idx}", query=query,
                    gold_paths=[needle_path],
                    gold_lines=[[start_line, end_line]],
                    repo_root=repo_root, budget=budget,
                    score_path=score_file, decision_path=decision_file,
                    fd1_objective_feature_path=feat_file,
                    posthoc_decomposition_path=decomp_file,
                    phase_run_id=phase_run_id, fcc=fcc,
                    fd1_weights=fd1_weights,
                )
                if per_arm is None:
                    records_failed += 1
                    records_excluded += 1
                    repoqa_excluded += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_setwise_summaries.append(rec_summary)
                v03_m = per_arm.get(ARM_BEA_V0_3, {})
                v03_lat = float(v03_m.get("latency_seconds", 0.0))
                v03_acc_count = int(rec_summary.get("setwise_behavior", {}).get("v03_budget_used", 0))
                v03_cats = _classify_fd1_categories(v03_m, v03_acc_count, v03_lat, v03_m, v03_lat, int(rec_summary.get("setwise_behavior", {}).get("duplicate_file_count_v03", 0)))
                for arm_id in FIXED_ARMS:
                    arm_m = per_arm.get(arm_id, {})
                    arm_dup = int(rec_summary.get("setwise_behavior", {}).get(
                        "duplicate_file_count_fd1lw" if arm_id == TREATMENT_ARM
                        else "duplicate_file_count_coverage" if arm_id == COVERAGE_ONLY_ARM
                        else "duplicate_file_count_v03" if arm_id == ARM_BEA_V0_3
                        else "duplicate_file_count_v03", 0))
                    arm_budget = int(rec_summary.get("setwise_behavior", {}).get(
                        "fd1lw_budget_used" if arm_id == TREATMENT_ARM
                        else "coverage_budget_used" if arm_id == COVERAGE_ONLY_ARM
                        else "v03_budget_used" if arm_id == ARM_BEA_V0_3
                        else "v03_budget_used", 0))
                    arm_lat = float(arm_m.get("latency_seconds", 0.0))
                    cats = _classify_fd1_categories(arm_m, arm_budget, arm_lat, v03_m, v03_lat, arm_dup)
                    per_record_categories[arm_id].append(cats)
                for arm_id, metrics in per_arm.items():
                    arm_record_counts[arm_id] = arm_record_counts.get(arm_id, 0) + 1
                    for m in ARM_METRIC_ALLOWLIST:
                        if m in metrics:
                            arm_aggs_raw[arm_id][m].append(float(metrics[m]))
                records_successful += 1
                repoqa_successful += 1

        if cb_done and rq_done:
            break

    if not per_record_arm_metrics:
        return _build_unavailable_report(
            "retrieval_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash_value=score_hash,
            private_decision_manifest_hash_value=decision_hash,
            private_fd1_objective_feature_manifest_hash_value=feat_hash,
            private_posthoc_decomposition_manifest_hash_value=decomp_hash,
            private_objective_config_manifest_hash_value=objcfg_hash,
            records_attempted_total=records_attempted_total,
            records_evaluated=records_evaluated, records_successful=records_successful,
            records_failed=records_failed, records_excluded=records_excluded,
            contextbench_attempted=contextbench_attempted,
            contextbench_successful=contextbench_successful,
            contextbench_excluded=contextbench_excluded,
            repoqa_attempted=repoqa_attempted, repoqa_successful=repoqa_successful,
            repoqa_excluded=repoqa_excluded,
            contextbench_excluded_prior_window_count=cb_excluded_prior_window_count,
            repoqa_excluded_prior_window_count=rq_excluded_prior_window_count,
            contextbench_eligible_count=cb_eligible_count,
            repoqa_eligible_count=rq_eligible_count,
            quota_reached=quota_reached, network_calls=network_calls,
            private_objective_config_written=True,
            failure_category_counts=fcc,
        )

    arm_aggs: dict[str, dict[str, Any]] = {}
    for arm_id in FIXED_ARMS:
        agg: dict[str, Any] = {}
        for m in ARM_METRIC_ALLOWLIST:
            vals = arm_aggs_raw[arm_id].get(m, [])
            if vals:
                agg[m] = round(sum(vals) / len(vals), 6)
            else:
                agg[m] = 0.0
        agg["__record_count__"] = arm_record_counts.get(arm_id, 0)
        arm_aggs[arm_id] = agg

    def _count_lines(p: Path) -> int:
        try:
            if p.exists():
                with p.open("r", encoding="utf-8") as fh:
                    return sum(1 for line in fh if line.strip())
        except OSError:
            pass
        return 0

    private_score_count = _count_lines(score_file)
    private_decision_count = _count_lines(decision_file)
    private_feat_count = _count_lines(feat_file)
    private_decomp_count = _count_lines(decomp_file)
    private_objcfg_count = 1 if objcfg_file.exists() else 0

    expected_score = records_successful * len(FIXED_ARMS)
    expected_decision = sum(
        int(s.get("mechanism_summary", {}).get("budget_used", 0))
        for s in per_record_setwise_summaries
    )
    expected_feat = expected_decision
    expected_decomp = records_successful * len(FIXED_ARMS) * len(FD1_PLAN_CATEGORIES)
    if records_successful > 0 and private_score_count != expected_score:
        fcc["private_score_write_failed"] = fcc.get("private_score_write_failed", 0) + 1
    if records_successful > 0 and private_decision_count != expected_decision:
        fcc["private_decision_write_failed"] = fcc.get("private_decision_write_failed", 0) + 1
    if records_successful > 0 and private_feat_count != expected_feat:
        fcc["private_fd1_objective_feature_write_failed"] = (
            fcc.get("private_fd1_objective_feature_write_failed", 0) + 1
        )
    if records_successful > 0 and private_decomp_count != expected_decomp:
        fcc["private_posthoc_decomposition_write_failed"] = (
            fcc.get("private_posthoc_decomposition_write_failed", 0) + 1
        )
    if records_successful > 0 and private_objcfg_count != 1:
        fcc["private_objective_config_write_failed"] = (
            fcc.get("private_objective_config_write_failed", 0) + 1
        )

    aggregate_runtime_seconds = time.perf_counter() - smoke_start
    partial = (not quota_reached) or records_failed > 0

    return _build_pass_report(
        self_test_passed=self_test_passed,
        self_test_checks_total=self_test_checks_total,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        records_attempted_total=records_attempted_total,
        records_evaluated=records_evaluated, records_successful=records_successful,
        records_failed=records_failed, records_excluded=records_excluded,
        contextbench_attempted=contextbench_attempted,
        contextbench_successful=contextbench_successful,
        contextbench_excluded=contextbench_excluded,
        repoqa_attempted=repoqa_attempted, repoqa_successful=repoqa_successful,
        repoqa_excluded=repoqa_excluded,
        contextbench_excluded_prior_window_count=cb_excluded_prior_window_count,
        repoqa_excluded_prior_window_count=rq_excluded_prior_window_count,
        contextbench_eligible_count=cb_eligible_count,
        repoqa_eligible_count=rq_eligible_count,
        quota_reached=quota_reached, network_calls=network_calls,
        arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_record_setwise_summaries=per_record_setwise_summaries,
        per_record_categories=per_record_categories,
        fd1_weights=fd1_weights,
        fd1_source_schema_version=fd1_schema,
        fd1_source_artifact_hash=fd1_hash,
        private_score_records_written=private_score_count > 0,
        private_score_record_count=private_score_count,
        private_decision_records_written=private_decision_count > 0,
        private_decision_record_count=private_decision_count,
        private_fd1_objective_feature_records_written=private_feat_count > 0,
        private_fd1_objective_feature_record_count=private_feat_count,
        private_posthoc_decomposition_records_written=private_decomp_count > 0,
        private_posthoc_decomposition_record_count=private_decomp_count,
        private_objective_config_written=private_objcfg_count > 0,
        private_score_storage_class=private_score_storage_class,
        private_score_manifest_hash=score_hash,
        private_decision_manifest_hash=decision_hash,
        private_fd1_objective_feature_manifest_hash=feat_hash,
        private_posthoc_decomposition_manifest_hash=decomp_hash,
        private_objective_config_manifest_hash=objcfg_hash,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        failure_category_counts=fcc,
        partial=partial,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            tag = "PASS" if c["passed"] else "FAIL"
            print(f"[{tag}] {c['check']}")
        passed_count = sum(1 for c in checks if c["passed"])
        print(f"self_test_passed={passed} ({passed_count}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    contextbench_row_offset = _validate_row_offset(args.contextbench_row_offset)
    contextbench_row_limit = _validate_row_limit(args.contextbench_row_limit)
    repoqa_needle_offset = _validate_needle_offset(args.repoqa_needle_offset)
    repoqa_needle_limit = _validate_needle_limit(args.repoqa_needle_limit)
    budget = _validate_budget(args.budget)
    methods = _validate_methods(args.methods)
    _validate_fixed_protocol(
        contextbench_row_offset=contextbench_row_offset,
        contextbench_row_limit=contextbench_row_limit,
        repoqa_needle_offset=repoqa_needle_offset,
        repoqa_needle_limit=repoqa_needle_limit,
        budget=budget, methods=methods,
    )
    enable_network = bool(args.enable_external_benchmark_network)
    out_path = args.out if args.out is not None else DEFAULT_OUT
    fd1_artifact_path = args.fd1_artifact if args.fd1_artifact is not None else DEFAULT_FD1_ARTIFACT

    checks, self_test_passed = run_self_test_checks()
    self_test_checks_total = len(checks)
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        sys.exit(1)

    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(args.openlocus)
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "retrieval_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_fd2a_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    private_score_dir, private_score_storage_class = (
        _resolve_private_dir(args.private_score_dir)
    )
    phase_run_id = f"bea-fd2a-{int(time.time())}"

    if not enable_network:
        report = _build_unavailable_report(
            "contextbench_fetch_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode="disabled_opt_in",
            private_score_storage_class=private_score_storage_class,
        )
        _enforce_fd2a_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real BEA-FD2-A smoke.")
        return

    network_mode = "local_explicit"
    try:
        report = _run_network_smoke(
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            budget=budget, openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            private_score_dir=private_score_dir,
            private_score_storage_class=private_score_storage_class,
            phase_run_id=phase_run_id,
            fd1_artifact_path=fd1_artifact_path,
        )
    except Exception:
        report = _build_unavailable_report(
            "unexpected_exception", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
        )

    if report.get("provider_calls") != 0:
        report["status"] = "fail_schema_contract"

    _enforce_fd2a_no_forbidden(report)
    _write_json(out_path, report)
    manifests = {r.get("manifest_name"): r for r in report.get("manifests", [])}
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"records_successful={report.get('records_successful', 0)}, "
          f"private_score_record_count={manifests.get('private_score_manifest', {}).get('record_count', 0)})")


if __name__ == "__main__":
    main()
