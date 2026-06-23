#!/usr/bin/env python3
"""BEA-FD2-A1: Direct FD1 Objective Failure Attribution Replay (Public Records-Only).

BEA-FD2-A1 is a *failure-mechanism attribution replay* after the BEA-FD2-A
No-Go. It is NOT a new selector/acquisition phase, NOT FD2-B, NOT P4/P5,
and NOT v0.31/v0.32 tuning. It answers exactly one question:

    Why did direct aggregate-FD1-loss weighting select worse evidence sets
    on the same bounded FD2-A frame?

To answer it, FD2-A1 reruns FD2-A *deterministically* over the same fixed
38-record success-quota frame, with a private trace directory under ``/tmp``
so it can parse FD2-A private traces (score / decision / FD1-objective
feature / post-hoc decomposition / objective config). It does NOT change
FD2-A policy, weights, thresholds, arms, budget, methods, or frame. It then
attributes each FD2-A regression into aggregate mechanism buckets:

- ``gold_file_displacement``
- ``correct_file_rank_worsened``
- ``correct_file_span_worsened``
- ``redundancy_overcorrection``
- ``latency_category_non_actionable_or_dominating``
- ``aggregate_weight_category_collision``
- ``candidate_availability_limit``
- ``diffuse_or_unclassified``

Binding invariants
-----------------
* claim_level = ``bea_fd2a1_failure_attribution_replay_only``
* status: ``bea_fd2a1_attribution_replay_pass`` | ``no_go_mechanism_diffuse`` |
  ``no_go_candidate_availability_limit`` | ``no_go_replay_mismatch`` |
  ``unavailable_with_reason`` | ``fail_forbidden_scan`` | ``fail_schema_contract``
* mode = ``bea_fd2a1_failure_attribution_replay``; phase = ``BEA-FD2-A1``

* Eval-local only. Does NOT modify the FD2-A or FD1 artifacts or any prior
  BEA result files. The committed FD2-A public artifact and FD1 aggregate
  artifact are read-only inputs (replay-match context only). FD2-A policy /
  weights / thresholds are NOT changed; the rerun reuses
  ``bea_fd2a_direct_fd1_objective_setwise_smoke`` verbatim.
* No v0.31/v0.32 weight tuning, no new records/retrieval methods/arms, no
  heldout validation, no per-repo tuning, no gold/private labels during
  selection, no provider/LLM calls, no role-proxy assignment.
* Budget fixed at 5. Methods fixed to bm25,regex,symbol. 5 fixed arms.
* Private per-record traces under ``/tmp`` only; the public artifact is
  aggregate-only and records-only. No public record IDs, paths, queries,
  snippets, spans, candidate keys, selected order, objective-config
  payload, or private trace paths. Only counts, rates, hashes, schema
  names, and aggregate metrics.

Network / CI policy (binding)
-----------------------------
* Default no-network self-test passes without HuggingFace/GitHub and
  without the committed FD2-A / FD1 artifacts (self-test uses synthetic
  private traces).
* Real replay requires public network access AND the committed FD1
  artifact AND a built OpenLocus binary. CI is a separate explicit
  workflow_dispatch job with ``enable_external_benchmark_network=true``;
  it must NOT run on PR/push by default, must use no provider
  secrets/vars/model env, and must upload only the aggregate report.
  Private JSONL/JSON files are NEVER uploaded.

Run::

    python3 -m py_compile eval/bea_fd2a1_failure_attribution_replay.py
    python3 eval/bea_fd2a1_failure_attribution_replay.py --self-test
    python3 eval/bea_fd2a1_failure_attribution_replay.py \\
        --out artifacts/bea_fd2a1_failure_attribution/\\
bea_fd2a1_failure_attribution_replay_report.json
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

# Reuse the FD2-A evaluator verbatim (rerun + scanner composition), the
# BEA-0 helpers (private score dir resolution + row writer), and the
# c5a helpers (now_iso / write_json / check / openlocus binary). FD2-A1
# does NOT import any BEA-v0.4-P1/P2/P3 module and does NOT use role
# proxies.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea_fd2a_direct_fd1_objective_setwise_smoke as bea_fd2a  # noqa: E402
import bea0_budgeted_evidence_acquisition as bea0  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402

# --- Schema / claim constants ---
SCHEMA_VERSION = "bea_fd2a1_failure_attribution_replay.v1"
GENERATED_BY = "eval/bea_fd2a1_failure_attribution_replay.py"
CLAIM_LEVEL = "bea_fd2a1_failure_attribution_replay_only"
MODE = "bea_fd2a1_failure_attribution_replay"
PHASE = "BEA-FD2-A1"

DEFAULT_OUT = Path(
    "artifacts/bea_fd2a1_failure_attribution/"
    "bea_fd2a1_failure_attribution_replay_report.json"
)
DEFAULT_FD2A_ARTIFACT = Path(
    "artifacts/bea_fd2a_direct_fd1_objective/"
    "bea_fd2a_direct_fd1_objective_setwise_smoke_report.json"
)
DEFAULT_FD1_ARTIFACT = bea_fd2a.DEFAULT_FD1_ARTIFACT

# Expected private trace counts from the committed FD2-A run (CI 28025382422).
EXPECTED_RECORDS_SUCCESSFUL = 38
EXPECTED_PRIVATE_SCORE_COUNT = 190
EXPECTED_PRIVATE_DECISION_COUNT = 190
EXPECTED_PRIVATE_FD1_OBJECTIVE_FEATURE_COUNT = 190
EXPECTED_PRIVATE_POSTHOC_DECOMPOSITION_COUNT = 950
EXPECTED_PRIVATE_OBJECTIVE_CONFIG_COUNT = 1

EXPECTED_PRIVATE_TRACE_COUNTS = {
    "private_score_manifest": EXPECTED_PRIVATE_SCORE_COUNT,
    "private_decision_manifest": EXPECTED_PRIVATE_DECISION_COUNT,
    "private_fd1_objective_feature_manifest":
        EXPECTED_PRIVATE_FD1_OBJECTIVE_FEATURE_COUNT,
    "private_posthoc_decomposition_manifest":
        EXPECTED_PRIVATE_POSTHOC_DECOMPOSITION_COUNT,
    "private_objective_config_manifest":
        EXPECTED_PRIVATE_OBJECTIVE_CONFIG_COUNT,
}

# Replay-match tolerance (deterministic; no floating-point drift expected).
REPLAY_TOLERANCE = 1e-6

# Mechanism buckets (8). The first 7 are the actionable / specific buckets;
# ``diffuse_or_unclassified`` is the catch-all.
MECHANISM_BUCKETS = (
    "gold_file_displacement",
    "correct_file_rank_worsened",
    "correct_file_span_worsened",
    "redundancy_overcorrection",
    "latency_category_non_actionable_or_dominating",
    "aggregate_weight_category_collision",
    "candidate_availability_limit",
    "diffuse_or_unclassified",
)
ACTIONABLE_BUCKETS = frozenset({
    "gold_file_displacement", "correct_file_rank_worsened",
    "correct_file_span_worsened", "redundancy_overcorrection",
    "latency_category_non_actionable_or_dominating",
    "aggregate_weight_category_collision",
})
# Buckets whose dominance forces No-Go (per plan stop rules).
NO_GO_DOMINATING_BUCKETS = frozenset({
    "diffuse_or_unclassified", "candidate_availability_limit",
})

# Go threshold: >=60% of FD2-A regressions in one or two actionable buckets.
GO_ACTIONABLE_CONCENTRATION = 0.60
GO_TOP_BUCKETS = 2

# FD2-A source binding context (read-only).
FD2A_SOURCE_CHECKPOINT = "df82ddb"
FD2A_SOURCE_CI_RUN_ID = "28025382422"
FD2A_SOURCE_LOCAL_CHECKPOINT = "709b0cb"
FD2A_SOURCE_STATUS = "no_go_no_fd1_loss_reduction"
FD2A_SOURCE_SCHEMA_VERSION = bea_fd2a.SCHEMA_VERSION
FD2A_SOURCE_SAMPLING_PROTOCOL = bea_fd2a.SAMPLING_PROTOCOL_VERSION
FD2A_SOURCE_FIXED_ARMS = bea_fd2a.FIXED_ARMS
FD2A_SOURCE_BUDGET = bea_fd2a.FIXED_BUDGET
FD2A_SOURCE_METHODS = bea_fd2a.ALLOWED_METHODS
FD2A_SOURCE_TREATMENT_ARM = bea_fd2a.TREATMENT_ARM
FD2A_SOURCE_BASELINE_ARM = bea_fd2a.DELTA_BASELINE_ARM

# Private trace filenames (must match bea_fd2a._run_network_smoke).
PRIVATE_SCORE_FILENAME = "bea_fd2a.private.jsonl"
PRIVATE_DECISION_FILENAME = "bea_fd2a.decision.jsonl"
PRIVATE_FEAT_FILENAME = "bea_fd2a.fd1_objective_feature.jsonl"
PRIVATE_DECOMP_FILENAME = "bea_fd2a.posthoc_decomposition.jsonl"
PRIVATE_OBJCFG_FILENAME = "bea_fd2a.objective_config.json"

# Required keys per private trace row schema (from FD2-A manifest hashes).
SCORE_REQUIRED_KEYS = (
    "phase_run_id", "benchmark", "private_record_id", "policy_arm",
    "runtime_query_feature_summary", "stop_reason", "score_outcome",
)
DECISION_REQUIRED_KEYS = (
    "phase_run_id", "benchmark", "private_record_id", "policy_arm",
    "decision_step", "decision_action",
)
FEAT_REQUIRED_KEYS = (
    "phase_run_id", "benchmark", "private_record_id", "candidate_key",
    "policy_arm", "file_reach", "span_precision",
    "novelty_diminishing_returns", "latency_cost", "duplicate_penalty",
    "fd1_objective",
)
DECOMP_REQUIRED_KEYS = (
    "phase_run_id", "benchmark", "private_record_id", "policy_arm",
    "fd1_category", "category_count", "loss",
)
OBJCFG_REQUIRED_KEYS = (
    "phase_run_id", "fd1_source_artifact_hash", "fd1_source_schema_version",
    "fd1_category_weights",
)

# FD1 plan categories (5). Used for collision-pair attribution.
FD1_PLAN_CATEGORIES = bea_fd2a.FD1_PLAN_CATEGORIES
FD1_BINARY_CATEGORIES = (
    "gold_file_absent", "correct_file_wrong_span",
    "budget_spent_on_low_marginal_gain", "latency_without_quality_gain",
)

# Statuses enum (binding).
STATUSES = (
    "bea_fd2a1_attribution_replay_pass",
    "no_go_mechanism_diffuse",
    "no_go_candidate_availability_limit",
    "no_go_replay_mismatch",
    "unavailable_with_reason",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "bea_v03_policy_executed": False,
    "fd2a_policy_executed": False,
    "fd2a1_replay_executed": False,
    "fd2a1_private_traces_parsed": False,
    "fd2a1_attribution_performed": False,
    "fd1_artifact_read": False,
    "fd2a_artifact_read": False,
    "fd2a_source_artifact_modified": False,
    "fd1_artifact_modified": False,
    "bounded_smoke_frame_read": False,
    "private_score_records_read": False,
    "private_decision_records_read": False,
    "private_fd1_objective_feature_records_read": False,
    "private_posthoc_decomposition_records_read": False,
    "private_objective_config_read": False,
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
    "algorithm_changed_during_bea_fd2a1": False,
    "weights_tuned_during_bea_fd2a1": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_fd2a1": False,
    "fd2a_policy_changed_during_bea_fd2a1": False,
    "fd2a_weights_changed_during_bea_fd2a1": False,
    "fd2a_thresholds_changed_during_bea_fd2a1": False,
    "fd2a_artifact_modified": False,
    "fd1_artifact_modified": False,
    "role_proxy_assigned": False,
    "posthoc_threshold_search": False,
    "private_decomposition_used_for_selection": False,
    "gold_labels_used_for_selection": False,
    "new_records_added_during_bea_fd2a1": False,
    "heldout_validation_claimed": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_attribution_replay",
}

FAILURE_CATEGORIES = (
    "fd2a_artifact_missing", "fd2a_artifact_parse_failed",
    "fd2a_source_status_mismatch", "fd2a_replay_run_failed",
    "private_score_parse_failed", "private_decision_parse_failed",
    "private_fd1_objective_feature_parse_failed",
    "private_posthoc_decomposition_parse_failed",
    "private_objective_config_parse_failed",
    "private_trace_count_mismatch", "private_trace_dir_missing",
    "openlocus_binary_missing", "network_required_but_disabled",
    "attribution_failed", "scanner_self_test_failed",
    "forbidden_leak_blocked", "duplicate_record_key_blocked",
    "unexpected_exception",
)
BLOCKING_FAILURE_CATEGORIES = (
    "forbidden_leak_blocked", "unexpected_exception",
    "private_trace_dir_missing",
)

# --- Scanner (strict, fail-closed). Composes the FD2-A scanner; adds
# FD2-A1-specific per-record / private-trace / objective-config rejections. ---

# FD2-A1 already inherits the full FD2-A forbidden-key discipline via
# ``bea_fd2a._scan_fd2a`` (role-proxy, per-record, FD1-private, dynamic-dict,
# winner/calibration). FD2-A1 adds its own attribution-private rejections:
# any per-record bucket assignment, private trace path, or objective-config
# payload leak.
FD2A1_FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        # private trace paths / dirs (FD2-A1 must not serialize them)
        "private_trace_dir", "trace_dir", "private_score_dir",
        "private_trace_path", "score_trace_path", "decision_trace_path",
        "fd1_objective_feature_trace_path",
        "posthoc_decomposition_trace_path", "objective_config_path",
        "private_trace_file", "private_trace_files",
        # per-record attribution detail (aggregate counts only)
        "per_record_buckets", "per_record_attribution",
        "record_bucket_assignment", "record_attribution_detail",
        "record_bucket_list", "attribution_records",
        "per_record_regressions", "record_regressions",
        # objective-config payload (private)
        "objective_config_payload", "fd1_category_weights_payload",
        "weight_derivation_payload", "frozen_weights_payload",
        # per-record collision detail
        "per_record_collisions", "collision_pairs_per_record",
        # per-record counterfactual detail
        "per_record_counterfactual", "counterfactual_records",
        # raw trace rows / snippets
        "score_rows", "decision_rows", "feature_rows", "decomposition_rows",
        "objective_config_row", "raw_score_row", "raw_decision_row",
        "raw_feature_row", "raw_decomposition_row",
        # candidate / query / path / span / snippet
        "candidate_paths", "candidate_keys", "query_text", "queries",
        "gold_paths", "gold_lines", "gold_spans", "gold_content",
        "snippets", "selected_paths", "selected_order",
        "private_record_ids", "record_ids",
        # claim / promotion (FD2-A1 is attribution only)
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion", "calibration",
        "method_winner", "best_method",
        # self-test details
        "self_test_checks", "self_test_details", "self_test_list",
        "checks", "check_list",
        # dynamic dict mirrors (forbidden as top-level; records-only)
        "hard_gates", "failure_category_counts",
        "mechanism_bucket_counts", "mechanism_counts",
        "pairwise_deltas", "component_deltas", "counterfactual_counts",
        "category_collision_counts",
        # FD2-A / FD1 source artifact paths (private; only hash/schema)
        "fd2a_source_artifact_path", "fd1_source_artifact_path",
    }
)

# FD2-A1 container keys whose record rows may legitimately carry a key that
# is forbidden as a top-level field (records-only discipline).
FD2A1_CONTAINER_KEYS = frozenset({
    "source_run_records", "pairwise_outcome_delta_records",
    "mechanism_bucket_records", "component_delta_records",
    "counterfactual_availability_records", "category_collision_records",
    "gate_records", "private_manifest_records",
    "failure_category_count_records", "manifests", "framing",
})


def _is_fd2a1_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in FD2A1_CONTAINER_KEYS


def _scan_fd2a1_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_fd2a1_schema_key_container(sub_path)
                if (key_str in FD2A1_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_fd2a1_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


# FD2-A1-specific safe VALUE path last-key segments. These keys MAY hold
# long policy strings or 64-char hex artifact hashes without triggering the
# primitive long_string / hex_digest_value checks (mirrors FD2-A's
# FD2A_SAFE_VALUE_PATH_LAST_KEYS).
FD2A1_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version", "generated_by", "generated_at",
        "claim_level", "status", "mode", "phase",
        "treatment_arm", "baseline_arm", "delta_baseline_arm",
        "coverage_only_arm", "quality_baseline_arm",
        "failure_reason_category", "signal_strength",
        "storage_class", "openlocus_binary_source", "network_mode",
        "source_sampling_protocol", "sampling_protocol_version",
        "source_artifact_status", "source_phase", "source_status",
        "source_checkpoint", "source_ci_run_id",
        "source_local_checkpoint",
        "replay_mismatch_reason", "replay_match_basis",
        "mechanism_bucket", "counterfactual_bucket", "collision_pair",
        "gate", "threshold_relation", "manifest_name",
        "fd2a_source_schema_version", "fd2a_source_artifact_hash",
        "fd1_source_schema_version", "fd1_source_artifact_hash",
        "manifest_hash", "failure_category",
        "fd2a_overlap_policy", "fd1_overlap_policy",
        "sampling_frame_policy", "excluded_prior_windows_policy",
        "bea5_overlap_policy", "bea_v04_p1_overlap_policy",
        "bea_v04_p2_overlap_policy", "bea_v04_p3_overlap_policy",
    }
)


def _fd2a1_safe_value_path(path: str) -> bool:
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in FD2A1_SAFE_VALUE_PATH_LAST_KEYS


def _scan_fd2a1(obj: Any) -> list[dict[str, Any]]:
    # Compose with the FD2-A scanner (which composes FD1/BEA-5/BEA-3), then
    # add FD2-A1-specific rejections. Filter primitive false positives for
    # FD2-A1-safe value paths (policy strings, artifact hashes).
    violations = bea_fd2a._scan_fd2a(obj)
    violations.extend(_scan_fd2a1_forbidden_keys(obj))
    filtered: list[dict[str, Any]] = []
    for v in violations:
        cat = v.get("category")
        if cat in ("long_string", "hex_digest_value",
                   "forbidden_field_name_value") and _fd2a1_safe_value_path(
            v.get("path", "")):
            continue
        filtered.append(v)
    return filtered


def _fd2a1_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_fd2a1(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_fd2a1_no_forbidden(obj: Any) -> None:
    scan = _fd2a1_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")


# --- Helpers ---


def _now_iso() -> str:
    return c5a._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    c5a._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5a._check(name, ok)


def _resolve_private_trace_dir(explicit: str | None) -> tuple[Path, str]:
    """Resolve the private trace directory under ``/tmp`` (or runs/).

    Reuses BEA-0's private score dir resolution so the discipline is
    identical (tmp_private or ignored_private). The path is NEVER
    serialized in the public artifact.
    """
    return bea0._resolve_private_score_dir(explicit)


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


# --- Natural keys for FD2-A1 public record tables ---


def _srr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["source_ci_run_id"])


def _podr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["baseline_arm"], rec["treatment_arm"], rec["metric"])


def _mbr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["mechanism_bucket"],)


def _cdr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["component"], rec["baseline_arm"], rec["treatment_arm"])


def _car_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["counterfactual_bucket"],)


def _ccr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["collision_pair"],)


def _gr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["gate"],)


def _pmr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["manifest_name"],)


def _fcr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["failure_category"],)


# --- Committed FD2-A artifact loader (read-only; replay-match context) ---


def _load_committed_fd2a_artifact(
    fd2a_artifact_path: Path,
) -> tuple[dict[str, Any], str, str, str]:
    """Load the committed FD2-A public artifact (read-only).

    Returns ``(artifact, fd2a_source_schema_version,
    fd2a_source_artifact_hash, status)``. On failure returns
    ``({}, "", "", reason)``; the caller fail-closes to
    ``unavailable_with_reason``.
    """
    if not fd2a_artifact_path.exists() or not fd2a_artifact_path.is_file():
        return {}, "", "", "fd2a_artifact_missing"
    try:
        with fd2a_artifact_path.open("r", encoding="utf-8") as f:
            artifact = json.load(f)
    except Exception:
        return {}, "", "", "fd2a_artifact_parse_failed"
    try:
        h = hashlib.sha256()
        with fd2a_artifact_path.open("rb") as fb:
            for chunk in iter(lambda: fb.read(65536), b""):
                h.update(chunk)
        artifact_hash = h.hexdigest()
    except Exception:
        artifact_hash = ""
    schema_ver = str(artifact.get("schema_version", "") or "")
    return artifact, schema_ver, artifact_hash, "pass"


def _committed_source_run_records(
    fd2a_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = fd2a_artifact.get("source_run_records", [])
    return rows if isinstance(rows, list) else []


def _committed_arm_delta_records(
    fd2a_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = fd2a_artifact.get("arm_delta_records", [])
    return rows if isinstance(rows, list) else []


def _committed_ablation_delta_records(
    fd2a_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = fd2a_artifact.get("ablation_delta_records", [])
    return rows if isinstance(rows, list) else []


def _committed_manifests(
    fd2a_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = fd2a_artifact.get("manifests", [])
    return rows if isinstance(rows, list) else []


# --- Private trace parser (5 files; counts parse failures) ---


def _parse_jsonl(
    path: Path, required_keys: tuple[str, ...],
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    parse_failures = 0
    if not path.exists() or not path.is_file():
        return rows, 0
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    parse_failures += 1
                    continue
                if not isinstance(obj, dict):
                    parse_failures += 1
                    continue
                missing = [k for k in required_keys if k not in obj]
                if missing:
                    parse_failures += 1
                    continue
                rows.append(obj)
    except OSError:
        parse_failures += 1
    return rows, parse_failures


def _parse_json_object(
    path: Path, required_keys: tuple[str, ...],
) -> tuple[dict[str, Any] | None, int]:
    if not path.exists() or not path.is_file():
        return None, 0
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError):
        return None, 1
    if not isinstance(obj, dict):
        return None, 1
    missing = [k for k in required_keys if k not in obj]
    if missing:
        return None, 1
    return obj, 0


class ParsedTraces:
    """Container for parsed FD2-A private traces (in-memory only)."""

    def __init__(self) -> None:
        self.score_rows: list[dict[str, Any]] = []
        self.decision_rows: list[dict[str, Any]] = []
        self.feat_rows: list[dict[str, Any]] = []
        self.decomp_rows: list[dict[str, Any]] = []
        self.objective_config: dict[str, Any] | None = None
        self.score_parse_failures = 0
        self.decision_parse_failures = 0
        self.feat_parse_failures = 0
        self.decomp_parse_failures = 0
        self.objcfg_parse_failures = 0
        self.trace_dir_existed = False

    @property
    def total_parse_failures(self) -> int:
        return (self.score_parse_failures + self.decision_parse_failures
                + self.feat_parse_failures + self.decomp_parse_failures
                + self.objcfg_parse_failures)

    @property
    def score_count(self) -> int:
        return len(self.score_rows)

    @property
    def decision_count(self) -> int:
        return len(self.decision_rows)

    @property
    def feat_count(self) -> int:
        return len(self.feat_rows)

    @property
    def decomp_count(self) -> int:
        return len(self.decomp_rows)

    @property
    def objcfg_count(self) -> int:
        return 1 if self.objective_config is not None else 0


def _parse_private_traces(trace_dir: Path) -> ParsedTraces:
    pt = ParsedTraces()
    pt.trace_dir_existed = trace_dir.exists() and trace_dir.is_dir()
    score_path = trace_dir / PRIVATE_SCORE_FILENAME
    decision_path = trace_dir / PRIVATE_DECISION_FILENAME
    feat_path = trace_dir / PRIVATE_FEAT_FILENAME
    decomp_path = trace_dir / PRIVATE_DECOMP_FILENAME
    objcfg_path = trace_dir / PRIVATE_OBJCFG_FILENAME
    pt.score_rows, pt.score_parse_failures = _parse_jsonl(
        score_path, SCORE_REQUIRED_KEYS)
    pt.decision_rows, pt.decision_parse_failures = _parse_jsonl(
        decision_path, DECISION_REQUIRED_KEYS)
    pt.feat_rows, pt.feat_parse_failures = _parse_jsonl(
        feat_path, FEAT_REQUIRED_KEYS)
    pt.decomp_rows, pt.decomp_parse_failures = _parse_jsonl(
        decomp_path, DECOMP_REQUIRED_KEYS)
    pt.objective_config, pt.objcfg_parse_failures = _parse_json_object(
        objcfg_path, OBJCFG_REQUIRED_KEYS)
    return pt


# --- Per-record attribution (private; only aggregate counts published) ---


def _index_decomp_rows(
    decomp_rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    """Index: (private_record_id, policy_arm) -> {fd1_category -> row}.

    Private keys (never serialized). Used only for in-memory attribution.
    """
    idx: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in decomp_rows:
        rid = str(row.get("private_record_id", "") or "")
        arm = str(row.get("policy_arm", "") or "")
        cat = str(row.get("fd1_category", "") or "")
        if not rid or not arm or not cat:
            continue
        idx.setdefault((rid, arm), {})[cat] = row
    return idx


def _index_score_rows(
    score_rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Index: (private_record_id, policy_arm) -> score row."""
    idx: dict[tuple[str, str], dict[str, Any]] = {}
    for row in score_rows:
        rid = str(row.get("private_record_id", "") or "")
        arm = str(row.get("policy_arm", "") or "")
        if not rid or not arm:
            continue
        idx[(rid, arm)] = row
    return idx


def _index_feat_rows_by_record(
    feat_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index: private_record_id -> list of fd1_objective_feature rows
    (treatment arm only, since only the treatment arm writes feature rows)."""
    idx: dict[str, list[dict[str, Any]]] = {}
    for row in feat_rows:
        rid = str(row.get("private_record_id", "") or "")
        if not rid:
            continue
        idx.setdefault(rid, []).append(row)
    return idx


def _cat_count(post: dict[str, dict[str, Any]], cat: str) -> int:
    """Read a category count from an indexed post-hoc decomposition arm.

    The FD2-A private post-hoc decomposition row stores the count under
    ``category_count`` (NOT ``count``); ``count`` is only the in-memory
    key returned by ``bea_fd2a._classify_fd1_categories``. This helper
    reads either field defensively.
    """
    row = post.get(cat, {})
    if not isinstance(row, dict):
        return 0
    val = row.get("category_count", row.get("count", 0))
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _record_regressed(
    v03_post: dict[str, dict[str, Any]],
    fd1lw_post: dict[str, dict[str, Any]],
) -> bool:
    """A record regressed if any binary FD1 category count worsened
    (fd1lw > v03)."""
    for cat in FD1_BINARY_CATEGORIES:
        v = _cat_count(v03_post, cat)
        t = _cat_count(fd1lw_post, cat)
        if t > v:
            return True
    return False


def _attribute_record_buckets(
    v03_post: dict[str, dict[str, Any]],
    fd1lw_post: dict[str, dict[str, Any]],
    fd1lw_score_summary: dict[str, Any],
    fd1lw_features: list[dict[str, Any]],
) -> set[str]:
    """Attribute one record's FD2-A regression into mechanism buckets.

    Returns the set of buckets the record falls into. A record may fall
    into multiple buckets. ``diffuse_or_unclassified`` is added only when
    the record regressed but no actionable bucket matched (or the record
    did not regress at all, in which case there is no actionable
    mechanism to attribute).
    """
    buckets: set[str] = set()
    regressed = _record_regressed(v03_post, fd1lw_post)

    v03_gold = _cat_count(v03_post, "gold_file_absent")
    fd1lw_gold = _cat_count(fd1lw_post, "gold_file_absent")
    v03_span = _cat_count(v03_post, "correct_file_wrong_span")
    fd1lw_span = _cat_count(fd1lw_post, "correct_file_wrong_span")
    v03_budget = _cat_count(v03_post, "budget_spent_on_low_marginal_gain")
    fd1lw_budget = _cat_count(fd1lw_post, "budget_spent_on_low_marginal_gain")
    v03_lat = _cat_count(v03_post, "latency_without_quality_gain")
    fd1lw_lat = _cat_count(fd1lw_post, "latency_without_quality_gain")
    v03_dup = _cat_count(v03_post, "redundant_same_file_candidates")
    fd1lw_dup = _cat_count(fd1lw_post, "redundant_same_file_candidates")

    budget = int(fd1lw_score_summary.get("budget", FD2A_SOURCE_BUDGET) or FD2A_SOURCE_BUDGET)
    deduped_count = int(fd1lw_score_summary.get("deduped_candidate_count", 0) or 0)

    if regressed:
        # 1. gold_file_displacement: v03 kept gold, fd1lw lost it.
        if v03_gold == 0 and fd1lw_gold == 1:
            buckets.add("gold_file_displacement")

        # 2/3. correct file retained in both arms.
        if v03_gold == 0 and fd1lw_gold == 0:
            # 2. correct_file_span_worsened: fd1lw lost correct span.
            if v03_span == 0 and fd1lw_span == 1:
                buckets.add("correct_file_span_worsened")
            # 3. correct_file_rank_worsened: fd1lw spent full budget with no
            # MRR gain vs v03 (budget_spent_on_low_marginal_gain worsened).
            if v03_budget == 0 and fd1lw_budget == 1:
                buckets.add("correct_file_rank_worsened")

        # 4. redundancy_overcorrection: v03 had duplicates, fd1lw suppressed
        # them, but fd1lw still regressed (overcorrected dedup hurt).
        if v03_dup > 0 and fd1lw_dup == 0:
            buckets.add("redundancy_overcorrection")

        # 5. latency_category_non_actionable_or_dominating: fd1lw latency
        # worsened, or the latency_cost component dominates the objective.
        if fd1lw_lat == 1 and v03_lat == 0:
            buckets.add("latency_category_non_actionable_or_dominating")
        if fd1lw_features:
            n = len(fd1lw_features)
            mean_latency_cost = sum(
                float(f.get("latency_cost", 0.0) or 0.0)
                for f in fd1lw_features
            ) / n
            mean_file_reach = sum(
                float(f.get("file_reach", 0.0) or 0.0)
                for f in fd1lw_features
            ) / n
            mean_span_precision = sum(
                float(f.get("span_precision", 0.0) or 0.0)
                for f in fd1lw_features
            ) / n
            if (mean_latency_cost > mean_file_reach
                    or mean_latency_cost > mean_span_precision):
                buckets.add("latency_category_non_actionable_or_dominating")

        # 6. aggregate_weight_category_collision: opposite movements across
        # FD1 binary categories (some improve, some worsen).
        improvements: list[str] = []
        worsenings: list[str] = []
        for cat in FD1_BINARY_CATEGORIES:
            v = _cat_count(v03_post, cat)
            t = _cat_count(fd1lw_post, cat)
            if t < v:
                improvements.append(cat)
            elif t > v:
                worsenings.append(cat)
        if improvements and worsenings:
            buckets.add("aggregate_weight_category_collision")

    # 7. candidate_availability_limit: deduped pool below 2*budget.
    # Applies whether or not the record regressed; a small pool is a
    # structural availability limit.
    if 0 < deduped_count < 2 * budget:
        buckets.add("candidate_availability_limit")

    # 8. diffuse_or_unclassified: regressed but no actionable bucket matched,
    # OR did not regress (no actionable mechanism to attribute).
    if not (buckets & ACTIONABLE_BUCKETS):
        buckets.add("diffuse_or_unclassified")

    return buckets


def _collision_pairs_for_record(
    v03_post: dict[str, dict[str, Any]],
    fd1lw_post: dict[str, dict[str, Any]],
) -> list[str]:
    """Return sorted collision pairs (cat_a vs cat_b) where one category
    improved and another worsened. The pair label is
    ``"<improved_cat>__vs__<worsened_cat>"`` (sorted for determinism)."""
    improvements: list[str] = []
    worsenings: list[str] = []
    for cat in FD1_BINARY_CATEGORIES:
        v = _cat_count(v03_post, cat)
        t = _cat_count(fd1lw_post, cat)
        if t < v:
            improvements.append(cat)
        elif t > v:
            worsenings.append(cat)
    pairs: list[str] = []
    for imp in improvements:
        for wor in worsenings:
            a, b = sorted((imp, wor))
            pairs.append(f"{a}__vs__{b}")
    return sorted(set(pairs))


def _counterfactual_buckets_for_record(
    v03_post: dict[str, dict[str, Any]],
    fd1lw_post: dict[str, dict[str, Any]],
    fd1lw_score_summary: dict[str, Any],
    budget: int,
) -> set[str]:
    """Return counterfactual availability buckets for one record."""
    cfs: set[str] = set()
    deduped_count = int(fd1lw_score_summary.get("deduped_candidate_count", 0) or 0)
    if deduped_count > budget:
        cfs.add("better_candidates_in_pool_above_budget")
    if deduped_count > 2 * budget:
        cfs.add("better_candidates_in_pool_above_2x_budget")
    v03_gold = _cat_count(v03_post, "gold_file_absent")
    fd1lw_gold = _cat_count(fd1lw_post, "gold_file_absent")
    if v03_gold == 0 and fd1lw_gold == 1:
        cfs.add("v03_selected_correct_file_fd1lw_did_not")
    v03_dup = _cat_count(v03_post, "redundant_same_file_candidates")
    fd1lw_dup = _cat_count(fd1lw_post, "redundant_same_file_candidates")
    if v03_dup > 0:
        cfs.add("v03_retained_duplicates_fd1lw_suppressed")
    return cfs


# --- Public record builders (records-only; no dynamic dict mirrors) ---


def _source_run_records(
    *, records_successful: int, records_attempted_total: int,
    records_excluded: int, contextbench_successful: int,
    repoqa_successful: int,
    private_score_count: int, private_decision_count: int,
    private_feat_count: int, private_decomp_count: int,
    private_objcfg_count: int,
    fd2a_source_schema_version: str, fd2a_source_artifact_hash: str,
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
    replay_protocol_match: bool, replay_mismatch_reason: str,
    committed_status: str,
) -> list[dict[str, Any]]:
    return [{
        "source_phase": FD2A_SOURCE_SCHEMA_VERSION.rsplit(".", 1)[0]
        if FD2A_SOURCE_SCHEMA_VERSION else "BEA-FD2-A",
        "source_ci_run_id": FD2A_SOURCE_CI_RUN_ID,
        "source_checkpoint": FD2A_SOURCE_CHECKPOINT,
        "source_local_checkpoint": FD2A_SOURCE_LOCAL_CHECKPOINT,
        "source_status": committed_status,
        "source_artifact_status": "replay_match" if replay_protocol_match
        else "replay_mismatch",
        "source_sampling_protocol": FD2A_SOURCE_SAMPLING_PROTOCOL,
        "expected_successful_records": EXPECTED_RECORDS_SUCCESSFUL,
        "replayed_successful_records": records_successful,
        "expected_private_score_count": EXPECTED_PRIVATE_SCORE_COUNT,
        "replayed_private_score_count": private_score_count,
        "expected_private_decision_count": EXPECTED_PRIVATE_DECISION_COUNT,
        "replayed_private_decision_count": private_decision_count,
        "expected_private_fd1_objective_feature_count":
            EXPECTED_PRIVATE_FD1_OBJECTIVE_FEATURE_COUNT,
        "replayed_private_fd1_objective_feature_count": private_feat_count,
        "expected_private_posthoc_decomposition_count":
            EXPECTED_PRIVATE_POSTHOC_DECOMPOSITION_COUNT,
        "replayed_private_posthoc_decomposition_count": private_decomp_count,
        "expected_private_objective_config_count":
            EXPECTED_PRIVATE_OBJECTIVE_CONFIG_COUNT,
        "replayed_private_objective_config_count": private_objcfg_count,
        "fd2a_source_schema_version": fd2a_source_schema_version,
        "fd2a_source_artifact_hash": fd2a_source_artifact_hash,
        "fd1_source_schema_version": fd1_source_schema_version,
        "fd1_source_artifact_hash": fd1_source_artifact_hash,
        "records_attempted_total": int(records_attempted_total),
        "records_excluded": int(records_excluded),
        "contextbench_successful": int(contextbench_successful),
        "repoqa_successful": int(repoqa_successful),
        "replay_protocol_match": bool(replay_protocol_match),
        "replay_mismatch_reason": replay_mismatch_reason,
        "replay_match_basis": "private_trace_counts_and_status_class",
    }]


def _pairwise_outcome_delta_records(
    committed_arm_deltas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Repackage the committed FD2-A public arm_delta_records (read-only)
    into FD2-A1 pairwise_outcome_delta_records. Records-only; natural key
    (baseline_arm, treatment_arm, metric)."""
    records: list[dict[str, Any]] = []
    for d in committed_arm_deltas:
        if not isinstance(d, dict):
            continue
        try:
            records.append({
                "baseline_arm": str(d["baseline_arm"]),
                "treatment_arm": str(d["treatment_arm"]),
                "metric": str(d["metric"]),
                "delta": round(float(d.get("delta", 0.0)), 6),
                "record_count": EXPECTED_RECORDS_SUCCESSFUL,
            })
        except (KeyError, TypeError, ValueError):
            continue
    records.sort(key=lambda r: (r["baseline_arm"], r["treatment_arm"], r["metric"]))
    return records


def _component_delta_records(
    committed_ablation_deltas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Repackage the committed FD2-A public ablation_delta_records
    (read-only) into FD2-A1 component_delta_records. Records-only."""
    records: list[dict[str, Any]] = []
    for d in committed_ablation_deltas:
        if not isinstance(d, dict):
            continue
        try:
            records.append({
                "component": str(d["component"]),
                "baseline_arm": str(d["baseline_arm"]),
                "treatment_arm": str(d["treatment_arm"]),
                "delta": round(float(d.get("delta", 0.0)), 6),
                "record_count": EXPECTED_RECORDS_SUCCESSFUL,
            })
        except (KeyError, TypeError, ValueError):
            continue
    records.sort(key=lambda r: (r["component"], r["baseline_arm"], r["treatment_arm"]))
    return records


def _mechanism_bucket_records(
    bucket_counts: dict[str, int], records_attributed: int,
    records_regressed: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    denom = records_attributed if records_attributed > 0 else 1
    reg_denom = records_regressed if records_regressed > 0 else 1
    for bucket in MECHANISM_BUCKETS:
        count = int(bucket_counts.get(bucket, 0))
        records.append({
            "mechanism_bucket": bucket,
            "record_count": count,
            "rate_of_attributed": round(count / denom, 6),
            "rate_of_regressed": round(count / reg_denom, 6) if records_regressed > 0 else 0.0,
            "is_actionable": bucket in ACTIONABLE_BUCKETS,
            "is_no_go_dominating": bucket in NO_GO_DOMINATING_BUCKETS,
        })
    records.sort(key=lambda r: r["mechanism_bucket"])
    return records


def _counterfactual_availability_records(
    cf_counts: dict[str, int], records_attributed: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    denom = records_attributed if records_attributed > 0 else 1
    for bucket in sorted(cf_counts.keys()):
        count = int(cf_counts.get(bucket, 0))
        records.append({
            "counterfactual_bucket": bucket,
            "record_count": count,
            "rate_of_attributed": round(count / denom, 6),
        })
    records.sort(key=lambda r: r["counterfactual_bucket"])
    return records


def _category_collision_records(
    collision_counts: dict[str, int], records_attributed: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    denom = records_attributed if records_attributed > 0 else 1
    for pair in sorted(collision_counts.keys()):
        count = int(collision_counts.get(pair, 0))
        records.append({
            "collision_pair": pair,
            "record_count": count,
            "rate_of_attributed": round(count / denom, 6),
        })
    records.sort(key=lambda r: r["collision_pair"])
    return records


def _gate_records(
    *, records_attributed: int, records_regressed: int,
    records_successful: int,
    private_score_count: int, private_decision_count: int,
    private_feat_count: int, private_decomp_count: int,
    private_objcfg_count: int,
    total_parse_failures: int, replay_protocol_match: bool,
    forbidden_scan_pass: bool,
    actionable_concentration: float,
    top_actionable_buckets: list[str],
    candidate_availability_dominates: bool,
    diffuse_dominates: bool,
) -> list[dict[str, Any]]:
    def _g(gate: str, value: float, relation: str, threshold: float,
           passed: bool) -> dict[str, Any]:
        return {
            "gate": gate, "value": round(float(value), 6),
            "threshold_relation": relation,
            "threshold_value": round(float(threshold), 6),
            "passed": bool(passed),
        }

    rows = [
        _g("records_attributed", float(records_attributed), "==",
           float(EXPECTED_RECORDS_SUCCESSFUL),
           records_attributed == EXPECTED_RECORDS_SUCCESSFUL),
        _g("records_successful", float(records_successful), "==",
           float(EXPECTED_RECORDS_SUCCESSFUL),
           records_successful == EXPECTED_RECORDS_SUCCESSFUL),
        _g("records_regressed", float(records_regressed), ">", 0.0,
           records_regressed > 0),
        _g("private_score_count", float(private_score_count), "==",
           float(EXPECTED_PRIVATE_SCORE_COUNT),
           private_score_count == EXPECTED_PRIVATE_SCORE_COUNT),
        _g("private_decision_count", float(private_decision_count), "==",
           float(EXPECTED_PRIVATE_DECISION_COUNT),
           private_decision_count == EXPECTED_PRIVATE_DECISION_COUNT),
        _g("private_fd1_objective_feature_count", float(private_feat_count),
           "==", float(EXPECTED_PRIVATE_FD1_OBJECTIVE_FEATURE_COUNT),
           private_feat_count == EXPECTED_PRIVATE_FD1_OBJECTIVE_FEATURE_COUNT),
        _g("private_posthoc_decomposition_count", float(private_decomp_count),
           "==", float(EXPECTED_PRIVATE_POSTHOC_DECOMPOSITION_COUNT),
           private_decomp_count == EXPECTED_PRIVATE_POSTHOC_DECOMPOSITION_COUNT),
        _g("private_objective_config_count", float(private_objcfg_count), "==",
           float(EXPECTED_PRIVATE_OBJECTIVE_CONFIG_COUNT),
           private_objcfg_count == EXPECTED_PRIVATE_OBJECTIVE_CONFIG_COUNT),
        _g("parse_failure_count", float(total_parse_failures), "==", 0.0,
           total_parse_failures == 0),
        _g("replay_protocol_match", 1.0 if replay_protocol_match else 0.0,
           "boolean", 1.0, replay_protocol_match),
        _g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0,
           "boolean", 1.0, forbidden_scan_pass),
        _g("actionable_concentration", float(actionable_concentration), ">=",
           float(GO_ACTIONABLE_CONCENTRATION),
           actionable_concentration >= GO_ACTIONABLE_CONCENTRATION),
        _g("candidate_availability_dominates",
           1.0 if candidate_availability_dominates else 0.0,
           "boolean_false", 0.0, not candidate_availability_dominates),
        _g("diffuse_dominates", 1.0 if diffuse_dominates else 0.0,
           "boolean_false", 0.0, not diffuse_dominates),
    ]
    # The top-1 and top-2 actionable bucket *names* are NOT serialized as
    # gate record labels (the inherited scanner forbids the ``label`` key
    # and the public artifact must remain records-only / aggregate). The
    # actionable concentration is already captured by the
    # ``actionable_concentration`` gate above, and the per-bucket counts
    # are published via ``mechanism_bucket_records`` (sort by record_count
    # to recover the ranking).
    return rows


def _private_manifest_records(
    pt: ParsedTraces, storage_class: str,
) -> list[dict[str, Any]]:
    """Reuse the FD2-A manifest hashes (schema is identical, since FD2-A1
    reruns FD2-A verbatim and parses the same private trace schemas)."""
    rows = [
        ("private_score_manifest", pt.score_count > 0, pt.score_count,
         bea_fd2a.PRIVATE_SCORE_SCHEMA_VERSION,
         bea_fd2a._private_score_manifest_hash()),
        ("private_decision_manifest", pt.decision_count > 0, pt.decision_count,
         bea_fd2a.PRIVATE_DECISION_SCHEMA_VERSION,
         bea_fd2a._private_decision_manifest_hash()),
        ("private_fd1_objective_feature_manifest",
         pt.feat_count > 0, pt.feat_count,
         bea_fd2a.PRIVATE_FD1_OBJECTIVE_FEATURE_SCHEMA_VERSION,
         bea_fd2a._private_fd1_objective_feature_manifest_hash()),
        ("private_posthoc_decomposition_manifest",
         pt.decomp_count > 0, pt.decomp_count,
         bea_fd2a.PRIVATE_POSTHOC_DECOMPOSITION_SCHEMA_VERSION,
         bea_fd2a._private_posthoc_decomposition_manifest_hash()),
        ("private_objective_config_manifest",
         pt.objective_config is not None, pt.objcfg_count,
         bea_fd2a.PRIVATE_OBJECTIVE_CONFIG_SCHEMA_VERSION,
         bea_fd2a._private_objective_config_manifest_hash()),
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


def _failure_category_count_records(
    fcc: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {"failure_category": str(k), "count": int(v)}
        for k, v in sorted(fcc.items())
    ]


def _blocking_failure_count(fcc: dict[str, int]) -> int:
    return sum(int(fcc.get(cat, 0)) for cat in BLOCKING_FAILURE_CATEGORIES)


# --- Status decision ---


def _decide_status(
    *, records_successful: int, records_attributed: int,
    replay_protocol_match: bool, total_parse_failures: int,
    forbidden_scan_pass: bool, blocking_failure_count: int,
    actionable_concentration: float, records_regressed: int,
    candidate_availability_dominates: bool, diffuse_dominates: bool,
) -> str:
    if not forbidden_scan_pass:
        return "fail_forbidden_scan"
    if blocking_failure_count > 0:
        return "fail_schema_contract"
    if not replay_protocol_match or records_successful != EXPECTED_RECORDS_SUCCESSFUL:
        return "no_go_replay_mismatch"
    if total_parse_failures > 0:
        return "fail_schema_contract"
    if records_attributed != EXPECTED_RECORDS_SUCCESSFUL:
        return "no_go_replay_mismatch"
    if records_successful == 0:
        return "unavailable_with_reason"
    # Go/No-Go decision based on actionable concentration among regressing
    # records (plan stop rules).
    if candidate_availability_dominates:
        return "no_go_candidate_availability_limit"
    if diffuse_dominates or records_regressed == 0:
        return "no_go_mechanism_diffuse"
    if actionable_concentration >= GO_ACTIONABLE_CONCENTRATION:
        return "bea_fd2a1_attribution_replay_pass"
    return "no_go_mechanism_diffuse"


# --- Public report builders ---


def _build_unavailable_report(
    failure_reason_category: str, *, self_test_passed: bool,
    self_test_checks_total: int = 0,
    self_test_checks_passed: int | None = None,
    openlocus_binary_source: str, network_mode: str,
    private_trace_storage_class: str = "tmp_private",
    fd2a_artifact_read: bool = False,
    fd2a_source_schema_version: str = "",
    fd2a_source_artifact_hash: str = "",
    fd1_source_schema_version: str = "",
    fd1_source_artifact_hash: str = "",
    records_attempted_total: int = 0, records_successful: int = 0,
    records_attributed: int = 0,
    committed_status: str = "",
    replay_protocol_match: bool = False,
    replay_mismatch_reason: str = "",
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
    safe_true["fd2a_artifact_read"] = bool(fd2a_artifact_read)
    safe_true["fd1_artifact_read"] = bool(fd2a_artifact_read) and bool(fd1_source_artifact_hash)

    private_manifest_records = _private_manifest_records(
        ParsedTraces(), private_trace_storage_class,
    )
    source_run_records = _source_run_records(
        records_successful=records_successful,
        records_attempted_total=records_attempted_total,
        records_excluded=0, contextbench_successful=0, repoqa_successful=0,
        private_score_count=0, private_decision_count=0,
        private_feat_count=0, private_decomp_count=0,
        private_objcfg_count=0,
        fd2a_source_schema_version=fd2a_source_schema_version,
        fd2a_source_artifact_hash=fd2a_source_artifact_hash,
        fd1_source_schema_version=fd1_source_schema_version,
        fd1_source_artifact_hash=fd1_source_artifact_hash,
        replay_protocol_match=replay_protocol_match,
        replay_mismatch_reason=replay_mismatch_reason,
        committed_status=committed_status,
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": "unavailable_with_reason",
        "mode": MODE,
        "phase": PHASE,
        "budget": FD2A_SOURCE_BUDGET,
        "methods": list(FD2A_SOURCE_METHODS),
        "fixed_arms": list(FD2A_SOURCE_FIXED_ARMS),
        "treatment_arm": FD2A_SOURCE_TREATMENT_ARM,
        "delta_baseline_arm": FD2A_SOURCE_BASELINE_ARM,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": FD2A_SOURCE_SAMPLING_PROTOCOL,
        "sampling_protocol_version": FD2A_SOURCE_SAMPLING_PROTOCOL,
        "target_successful_records": EXPECTED_RECORDS_SUCCESSFUL,
        "records_attempted_total": int(records_attempted_total),
        "records_successful": records_successful,
        "records_attributed": records_attributed,
        "records_regressed": 0,
        "actionable_concentration": 0.0,
        "failure_reason_category": failure_reason_category,
        "failure_category_count_records": _failure_category_count_records(fcc),
        "source_run_records": source_run_records,
        "pairwise_outcome_delta_records": [],
        "mechanism_bucket_records": _mechanism_bucket_records({}, 0, 0),
        "component_delta_records": [],
        "counterfactual_availability_records": [],
        "category_collision_records": [],
        "gate_records": _gate_records(
            records_attributed=0, records_regressed=0,
            records_successful=0, private_score_count=0,
            private_decision_count=0, private_feat_count=0,
            private_decomp_count=0, private_objcfg_count=0,
            total_parse_failures=0,
            replay_protocol_match=replay_protocol_match,
            forbidden_scan_pass=True,
            actionable_concentration=0.0,
            top_actionable_buckets=[],
            candidate_availability_dominates=False,
            diffuse_dominates=True,
        ),
        "private_manifest_records": private_manifest_records,
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
            "heldout_validation_claimed": False,
            "signal_strength": "bea_fd2a1_attribution_replay_unavailable",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
            "is_fd2_b": False,
            "is_failure_attribution_only": True,
        },
    }
    scan = _fd2a1_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_attribution_report(
    *, self_test_passed: bool, self_test_checks_total: int,
    self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    private_trace_storage_class: str,
    pt: ParsedTraces,
    fd2a_artifact: dict[str, Any],
    fd2a_source_schema_version: str, fd2a_source_artifact_hash: str,
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
    records_successful: int, records_attempted_total: int,
    records_excluded: int, contextbench_successful: int,
    repoqa_successful: int,
    committed_status: str,
    aggregate_runtime_seconds: float,
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    # Index private traces (in-memory only; never serialized).
    decomp_idx = _index_decomp_rows(pt.decomp_rows)
    score_idx = _index_score_rows(pt.score_rows)
    feat_idx = _index_feat_rows_by_record(pt.feat_rows)

    # Collect the set of private_record_ids that have BOTH v03 and fd1lw
    # post-hoc decomposition rows (the paired denominator).
    paired_rids: list[str] = sorted({
        rid for (rid, arm) in decomp_idx
        if arm == FD2A_SOURCE_BASELINE_ARM
        and (rid, FD2A_SOURCE_TREATMENT_ARM) in decomp_idx
    })
    records_attributed = len(paired_rids)

    # Per-record attribution.
    bucket_counts: dict[str, int] = {b: 0 for b in MECHANISM_BUCKETS}
    cf_counts: dict[str, int] = {}
    collision_counts: dict[str, int] = {}
    records_regressed = 0
    for rid in paired_rids:
        v03_post = decomp_idx.get((rid, FD2A_SOURCE_BASELINE_ARM), {})
        fd1lw_post = decomp_idx.get((rid, FD2A_SOURCE_TREATMENT_ARM), {})
        fd1lw_score = score_idx.get((rid, FD2A_SOURCE_TREATMENT_ARM), {})
        fd1lw_summary = fd1lw_score.get("runtime_query_feature_summary", {})
        if not isinstance(fd1lw_summary, dict):
            fd1lw_summary = {}
        fd1lw_features = feat_idx.get(rid, [])
        regressed = _record_regressed(v03_post, fd1lw_post)
        if regressed:
            records_regressed += 1
        buckets = _attribute_record_buckets(
            v03_post, fd1lw_post, fd1lw_summary, fd1lw_features,
        )
        for b in buckets:
            bucket_counts[b] = bucket_counts.get(b, 0) + 1
        for cf in _counterfactual_buckets_for_record(
            v03_post, fd1lw_post, fd1lw_summary, FD2A_SOURCE_BUDGET,
        ):
            cf_counts[cf] = cf_counts.get(cf, 0) + 1
        for pair in _collision_pairs_for_record(v03_post, fd1lw_post):
            collision_counts[pair] = collision_counts.get(pair, 0) + 1

    # Actionable concentration: fraction of regressing records that fall
    # into the top-1 or top-2 actionable buckets.
    actionable_counts = {
        b: bucket_counts.get(b, 0) for b in ACTIONABLE_BUCKETS
    }
    sorted_actionable = sorted(
        actionable_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top_actionable = [b for b, c in sorted_actionable if c > 0]
    top_actionable_buckets = top_actionable[:GO_TOP_BUCKETS]
    if records_regressed > 0:
        top_sum = sum(actionable_counts.get(b, 0)
                      for b in top_actionable_buckets)
        actionable_concentration = top_sum / records_regressed
    else:
        actionable_concentration = 0.0

    # No-Go dominating buckets: a No-Go dominating bucket holds the
    # plurality of regressing records.
    candidate_av_count = bucket_counts.get("candidate_availability_limit", 0)
    diffuse_count = bucket_counts.get("diffuse_or_unclassified", 0)
    candidate_availability_dominates = (
        records_regressed > 0
        and candidate_av_count > 0
        and candidate_av_count >= max(
            bucket_counts.get(b, 0) for b in ACTIONABLE_BUCKETS
        )
    )
    diffuse_dominates = (
        records_regressed > 0
        and diffuse_count > 0
        and diffuse_count >= max(
            bucket_counts.get(b, 0) for b in ACTIONABLE_BUCKETS
        )
    )

    # Replay match: private trace counts must equal expected, AND the
    # committed FD2-A public outcome must be the No-Go class, AND the
    # parsed records_attributed must equal committed records_successful.
    committed_src = _committed_source_run_records(fd2a_artifact)
    committed_records_successful = (
        int(committed_src[0].get("replayed_successful_records", 0))
        if committed_src else 0
    )
    expected_from_committed = {
        "private_score_manifest": int(committed_src[0].get(
            "expected_private_score_count", 0)) if committed_src else 0,
        "private_decision_manifest": int(committed_src[0].get(
            "expected_private_decision_count", 0)) if committed_src else 0,
        "private_fd1_objective_feature_manifest": int(committed_src[0].get(
            "expected_private_fd1_objective_feature_count", 0)) if committed_src else 0,
        "private_posthoc_decomposition_manifest": int(committed_src[0].get(
            "expected_private_posthoc_decomposition_count", 0)) if committed_src else 0,
        "private_objective_config_manifest": int(committed_src[0].get(
            "expected_private_objective_config_count", 0)) if committed_src else 0,
    }
    parsed_counts = {
        "private_score_manifest": pt.score_count,
        "private_decision_manifest": pt.decision_count,
        "private_fd1_objective_feature_manifest": pt.feat_count,
        "private_posthoc_decomposition_manifest": pt.decomp_count,
        "private_objective_config_manifest": pt.objcfg_count,
    }
    counts_match_expected = all(
        parsed_counts[k] == EXPECTED_PRIVATE_TRACE_COUNTS[k]
        for k in EXPECTED_PRIVATE_TRACE_COUNTS
    )
    counts_match_committed = all(
        parsed_counts[k] == expected_from_committed[k]
        for k in expected_from_committed
        if expected_from_committed[k] > 0
    )
    committed_status_is_no_go = committed_status in (
        "no_go_no_fd1_loss_reduction", "no_go_no_selection_change",
        "no_go_objective_ablation_only", "no_go_quality_regression",
    )
    replay_protocol_match = (
        counts_match_expected
        and counts_match_committed
        and committed_status_is_no_go
        and records_successful == EXPECTED_RECORDS_SUCCESSFUL
        and records_successful == committed_records_successful
        and records_attributed == EXPECTED_RECORDS_SUCCESSFUL
        and pt.total_parse_failures == 0
    )
    if not replay_protocol_match:
        reasons = []
        if not counts_match_expected:
            reasons.append("private_trace_count_mismatch_vs_expected")
        if not counts_match_committed:
            reasons.append("private_trace_count_mismatch_vs_committed")
        if not committed_status_is_no_go:
            reasons.append(f"committed_status_not_no_go:{committed_status}")
        if records_successful != EXPECTED_RECORDS_SUCCESSFUL:
            reasons.append(f"records_successful_mismatch:{records_successful}")
        if records_attributed != EXPECTED_RECORDS_SUCCESSFUL:
            reasons.append(f"records_attributed_mismatch:{records_attributed}")
        if pt.total_parse_failures > 0:
            reasons.append(f"parse_failures:{pt.total_parse_failures}")
        replay_mismatch_reason = ";".join(reasons)
    else:
        replay_mismatch_reason = ""

    forbidden_scan_summary = _fd2a1_forbidden_scan_summary  # alias
    # Build the public report.
    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["fd2a1_replay_executed"] = True
    safe_true["fd2a1_private_traces_parsed"] = pt.total_parse_failures == 0
    safe_true["fd2a1_attribution_performed"] = records_attributed > 0
    safe_true["fd2a_policy_executed"] = records_successful > 0
    safe_true["bea_v03_policy_executed"] = records_successful > 0
    safe_true["fd2a_artifact_read"] = True
    safe_true["fd1_artifact_read"] = bool(fd1_source_artifact_hash)
    safe_true["external_benchmark_rows_read"] = records_successful > 0
    safe_true["bounded_smoke_frame_read"] = records_successful > 0
    safe_true["private_score_records_read"] = pt.score_count > 0
    safe_true["private_decision_records_read"] = pt.decision_count > 0
    safe_true["private_fd1_objective_feature_records_read"] = pt.feat_count > 0
    safe_true["private_posthoc_decomposition_records_read"] = pt.decomp_count > 0
    safe_true["private_objective_config_read"] = pt.objective_config is not None

    blocking_failure_count = _blocking_failure_count(fcc)

    status = _decide_status(
        records_successful=records_successful,
        records_attributed=records_attributed,
        replay_protocol_match=replay_protocol_match,
        total_parse_failures=pt.total_parse_failures,
        forbidden_scan_pass=True,  # validated below; will flip on failure
        blocking_failure_count=blocking_failure_count,
        actionable_concentration=actionable_concentration,
        records_regressed=records_regressed,
        candidate_availability_dominates=candidate_availability_dominates,
        diffuse_dominates=diffuse_dominates,
    )

    pairwise_deltas = _pairwise_outcome_delta_records(
        _committed_arm_delta_records(fd2a_artifact))
    component_deltas = _component_delta_records(
        _committed_ablation_delta_records(fd2a_artifact))
    mech_buckets = _mechanism_bucket_records(
        bucket_counts, records_attributed, records_regressed)
    cf_records = _counterfactual_availability_records(
        cf_counts, records_attributed)
    coll_records = _category_collision_records(
        collision_counts, records_attributed)
    private_manifests = _private_manifest_records(
        pt, private_trace_storage_class)
    source_runs = _source_run_records(
        records_successful=records_successful,
        records_attempted_total=records_attempted_total,
        records_excluded=records_excluded,
        contextbench_successful=contextbench_successful,
        repoqa_successful=repoqa_successful,
        private_score_count=pt.score_count,
        private_decision_count=pt.decision_count,
        private_feat_count=pt.feat_count,
        private_decomp_count=pt.decomp_count,
        private_objcfg_count=pt.objcfg_count,
        fd2a_source_schema_version=fd2a_source_schema_version,
        fd2a_source_artifact_hash=fd2a_source_artifact_hash,
        fd1_source_schema_version=fd1_source_schema_version,
        fd1_source_artifact_hash=fd1_source_artifact_hash,
        replay_protocol_match=replay_protocol_match,
        replay_mismatch_reason=replay_mismatch_reason,
        committed_status=committed_status,
    )
    gates = _gate_records(
        records_attributed=records_attributed,
        records_regressed=records_regressed,
        records_successful=records_successful,
        private_score_count=pt.score_count,
        private_decision_count=pt.decision_count,
        private_feat_count=pt.feat_count,
        private_decomp_count=pt.decomp_count,
        private_objcfg_count=pt.objcfg_count,
        total_parse_failures=pt.total_parse_failures,
        replay_protocol_match=replay_protocol_match,
        forbidden_scan_pass=True,
        actionable_concentration=actionable_concentration,
        top_actionable_buckets=top_actionable_buckets,
        candidate_availability_dominates=candidate_availability_dominates,
        diffuse_dominates=diffuse_dominates,
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "budget": FD2A_SOURCE_BUDGET,
        "methods": list(FD2A_SOURCE_METHODS),
        "fixed_arms": list(FD2A_SOURCE_FIXED_ARMS),
        "treatment_arm": FD2A_SOURCE_TREATMENT_ARM,
        "delta_baseline_arm": FD2A_SOURCE_BASELINE_ARM,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": FD2A_SOURCE_SAMPLING_PROTOCOL,
        "sampling_protocol_version": FD2A_SOURCE_SAMPLING_PROTOCOL,
        "target_successful_records": EXPECTED_RECORDS_SUCCESSFUL,
        "records_attempted_total": int(records_attempted_total),
        "records_successful": records_successful,
        "records_attributed": records_attributed,
        "records_regressed": records_regressed,
        "actionable_concentration": round(actionable_concentration, 6),
        "failure_reason_category": "",
        "failure_category_count_records": _failure_category_count_records(fcc),
        "source_run_records": source_runs,
        "pairwise_outcome_delta_records": pairwise_deltas,
        "mechanism_bucket_records": mech_buckets,
        "component_delta_records": component_deltas,
        "counterfactual_availability_records": cf_records,
        "category_collision_records": coll_records,
        "gate_records": gates,
        "private_manifest_records": private_manifests,
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
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
            "heldout_validation_claimed": False,
            "signal_strength": "bea_fd2a1_attribution_replay_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
            "is_fd2_b": False,
            "is_failure_attribution_only": True,
        },
    }
    scan = forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# --- Real replay runner (network + openlocus + committed FD1 artifact) ---


def _run_real_replay(
    *, openlocus_bin: str, openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, self_test_checks_total: int,
    private_trace_dir: Path, private_trace_storage_class: str,
    fd1_artifact_path: Path, fd2a_artifact_path: Path,
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    """Rerun FD2-A deterministically (verbatim) with a private trace dir
    under ``/tmp``, then parse the resulting private traces and attribute.

    Reuses ``bea_fd2a._run_network_smoke`` so the FD2-A policy / weights /
    thresholds / arms / budget / methods / frame are unchanged. The FD2-A
    pass report is used for replay-match context only.
    """
    fcc = failure_category_counts
    replay_start = time.perf_counter()

    fd2a_artifact, fd2a_schema, fd2a_hash, fd2a_status = (
        _load_committed_fd2a_artifact(fd2a_artifact_path)
    )
    if fd2a_status != "pass":
        fcc["fd2a_artifact_missing" if fd2a_status == "fd2a_artifact_missing"
            else "fd2a_artifact_parse_failed"] = 1
        return _build_unavailable_report(
            fd2a_status, self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_trace_storage_class=private_trace_storage_class,
            failure_category_counts=fcc,
        )
    committed_status = str(fd2a_artifact.get("status", "") or "")

    phase_run_id = f"bea-fd2a1-{int(time.time())}"
    fd2a_report: dict[str, Any]
    try:
        fd2a_report = bea_fd2a._run_network_smoke(
            contextbench_row_offset=0,
            contextbench_row_limit=bea_fd2a.RAW_ATTEMPT_CAP_CONTEXTBENCH,
            repoqa_needle_offset=0,
            repoqa_needle_limit=bea_fd2a.RAW_ATTEMPT_CAP_REPOQA,
            budget=FD2A_SOURCE_BUDGET, openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            private_score_dir=private_trace_dir,
            private_score_storage_class=private_trace_storage_class,
            phase_run_id=phase_run_id,
            fd1_artifact_path=fd1_artifact_path,
        )
    except Exception:
        fcc["fd2a_replay_run_failed"] = fcc.get("fd2a_replay_run_failed", 0) + 1
        fcc["unexpected_exception"] = fcc.get("unexpected_exception", 0) + 1
        return _build_unavailable_report(
            "fd2a_replay_run_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_trace_storage_class=private_trace_storage_class,
            fd2a_artifact_read=True,
            fd2a_source_schema_version=fd2a_schema,
            fd2a_source_artifact_hash=fd2a_hash,
            committed_status=committed_status,
            failure_category_counts=fcc,
        )

    if fd2a_report.get("provider_calls") != 0:
        fcc["fd2a_replay_run_failed"] = 1
        return _build_unavailable_report(
            "fd2a_replay_run_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_trace_storage_class=private_trace_storage_class,
            fd2a_artifact_read=True,
            fd2a_source_schema_version=fd2a_schema,
            fd2a_source_artifact_hash=fd2a_hash,
            committed_status=committed_status,
            failure_category_counts=fcc,
        )

    # Parse the private traces written by the FD2-A rerun.
    pt = _parse_private_traces(private_trace_dir)
    if not pt.trace_dir_existed:
        fcc["private_trace_dir_missing"] = 1
    if pt.score_parse_failures > 0:
        fcc["private_score_parse_failed"] = pt.score_parse_failures
    if pt.decision_parse_failures > 0:
        fcc["private_decision_parse_failed"] = pt.decision_parse_failures
    if pt.feat_parse_failures > 0:
        fcc["private_fd1_objective_feature_parse_failed"] = pt.feat_parse_failures
    if pt.decomp_parse_failures > 0:
        fcc["private_posthoc_decomposition_parse_failed"] = pt.decomp_parse_failures
    if pt.objcfg_parse_failures > 0:
        fcc["private_objective_config_parse_failed"] = pt.objcfg_parse_failures

    # FD1 source schema/hash from the private objective-config (more
    # precise than the committed FD2-A artifact, since the rerun re-derived
    # weights from the FD1 artifact at rerun time).
    fd1_schema = ""
    fd1_hash = ""
    if pt.objective_config is not None:
        fd1_schema = str(pt.objective_config.get(
            "fd1_source_schema_version", "") or "")
        fd1_hash = str(pt.objective_config.get(
            "fd1_source_artifact_hash", "") or "")
    if not fd1_schema or not fd1_hash:
        committed_src = _committed_source_run_records(fd2a_artifact)
        if committed_src:
            fd1_schema = str(committed_src[0].get(
                "fd1_source_schema_version", "") or "")
            fd1_hash = str(committed_src[0].get(
                "fd1_source_artifact_hash", "") or "")

    aggregate_runtime_seconds = time.perf_counter() - replay_start

    return _build_attribution_report(
        self_test_passed=self_test_passed,
        self_test_checks_total=self_test_checks_total,
        self_test_checks_passed=None,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        private_trace_storage_class=private_trace_storage_class,
        pt=pt, fd2a_artifact=fd2a_artifact,
        fd2a_source_schema_version=fd2a_schema,
        fd2a_source_artifact_hash=fd2a_hash,
        fd1_source_schema_version=fd1_schema,
        fd1_source_artifact_hash=fd1_hash,
        records_successful=int(fd2a_report.get("records_successful", 0)),
        records_attempted_total=int(fd2a_report.get("records_attempted_total", 0)),
        records_excluded=int(fd2a_report.get("records_excluded", 0)),
        contextbench_successful=int(fd2a_report.get("contextbench_successful", 0)),
        repoqa_successful=int(fd2a_report.get("repoqa_successful", 0)),
        committed_status=committed_status,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        failure_category_counts=fcc,
    )


# --- Self-test (no network; synthetic private traces) ---


def _build_synthetic_private_traces(
    trace_dir: Path,
) -> tuple[ParsedTraces, int]:
    """Write synthetic FD2-A private traces to ``trace_dir`` for self-test.

    Returns ``(parsed, records_successful)``. The synthetic traces mirror
    the FD2-A private trace schemas exactly (one record, 5 arms, 5
    categories per arm = 25 decomposition rows, 5 score rows, 5 decision
    rows, 5 feature rows, 1 objective config). Never written to any
    committed artifact.
    """
    phase_run_id = "fd2a1-self-test"
    rid = "synthetic-0"
    arms = list(FD2A_SOURCE_FIXED_ARMS)
    # Score rows: 5 (one per arm).
    for arm in arms:
        row = {
            "schema_version": bea_fd2a.PRIVATE_SCORE_SCHEMA_VERSION,
            "phase_run_id": phase_run_id,
            "benchmark": "contextbench",
            "private_record_id": rid,
            "policy_arm": arm,
            "runtime_query_feature_summary": {
                "benchmark": "contextbench",
                "method_count": 3,
                "methods": list(FD2A_SOURCE_METHODS),
                "candidate_count_total": 12,
                "candidate_count_per_method": {m: 4 for m in FIELDS_METHODS},
                "rrf_candidate_count": 8,
                "budget": FD2A_SOURCE_BUDGET,
                "same_budget_k": 5,
                "deduped_candidate_count": 8,
                "fd1lw_accepted_count": 5,
                "coverage_accepted_count": 5,
                "v03_accepted_count": 5,
                "shared_retrieval_latency_seconds": 0.05,
                "query_length_chars": 40,
                "query_word_count": 7,
            },
            "candidate_features": [],
            "fd1_objective_components_summary": {
                "component_means": {c: 0.5 for c in bea_fd2a.FD1_OBJECTIVE_COMPONENTS},
                "mean_fd1_objective": 0.3,
                "selected_feature_count": 5,
            },
            "priority_components": [],
            "selected_decisions": [],
            "action_order": [],
            "budget_trace": [],
            "anchor_slots": 0,
            "early_stop_reason": "",
            "stop_reason": "budget_exhausted",
            "score_outcome": arm,
            "role_proxy_summary": ({"role_proxy_used": False,
                                    "target_support_proxy_used": False}
                                   if arm == FD2A_SOURCE_TREATMENT_ARM else {}),
            "latency_ms": 50, "cost_usd": 0.0, "tokens": 0,
            "provider_calls": 0, "failure_reason": None,
        }
        bea_fd2a._write_private_row(trace_dir / PRIVATE_SCORE_FILENAME, row)

    # Decision rows: 5 (treatment arm only, budget=5).
    for step in range(5):
        row = {
            "schema_version": bea_fd2a.PRIVATE_DECISION_SCHEMA_VERSION,
            "phase_run_id": phase_run_id,
            "benchmark": "contextbench",
            "private_record_id": rid,
            "policy_arm": FD2A_SOURCE_TREATMENT_ARM,
            "decision_step": step,
            "decision_action": "accept_candidate",
            "priority_score": 0.5 - step * 0.05,
            "priority_components": {"relevance": 0.5},
            "fd1_objective_score": 0.4 - step * 0.04,
            "fd1_objective_components": {c: 0.5 for c in bea_fd2a.FD1_OBJECTIVE_COMPONENTS},
            "candidate_method": "bm25",
            "candidate_rank": step,
            "agreement": 1,
            "is_new_file": step == 0,
            "is_new_dir": step == 0,
            "span_extent": 10,
            "span_proxy_bucket": "tight",
            "decision_reason": "budget_exhausted",
        }
        bea_fd2a._write_private_row(trace_dir / PRIVATE_DECISION_FILENAME, row)

    # FD1-objective feature rows: 5 (treatment arm selected candidates).
    for i in range(5):
        row = {
            "schema_version": bea_fd2a.PRIVATE_FD1_OBJECTIVE_FEATURE_SCHEMA_VERSION,
            "phase_run_id": phase_run_id,
            "benchmark": "contextbench",
            "private_record_id": rid,
            "candidate_key": f"cand-{i}",
            "policy_arm": FD2A_SOURCE_TREATMENT_ARM,
            "file_reach": 0.7,
            "span_precision": 0.8,
            "novelty_diminishing_returns": 0.6,
            "latency_cost": 0.4,
            "duplicate_penalty": 0.0,
            "fd1_objective": 0.35,
            "is_new_file": i == 0,
            "is_new_dir": i == 0,
            "agreement": 1,
            "span_tightness": 0.7,
            "rank": i,
            "feature_reason": "synthetic",
        }
        bea_fd2a._write_private_row(trace_dir / PRIVATE_FEAT_FILENAME, row)

    # Post-hoc decomposition rows: 5 arms x 5 categories = 25.
    # Synthetic v03: gold present, no span issue, budget WAS wasted,
    # no latency waste, 2 duplicates.
    # Synthetic fd1lw (treatment): gold DISPLACED (regression!), span n/a,
    # budget IMPROVED (no longer wasted), latency WORSENED, 0 duplicates.
    # This produces a collision: gold_file_absent worsened (0->1) while
    # budget_spent_on_low_marginal_gain improved (1->0), so the
    # aggregate_weight_category_collision bucket and a collision pair
    # (budget_spent_on_low_marginal_gain__vs__gold_file_absent) fire.
    for arm in arms:
        is_treat = (arm == FD2A_SOURCE_TREATMENT_ARM)
        is_v03 = (arm == FD2A_SOURCE_BASELINE_ARM)
        cats = {
            "gold_file_absent": (1 if is_treat else 0),
            "correct_file_wrong_span": 0,
            "budget_spent_on_low_marginal_gain": (0 if is_treat else 1),
            "latency_without_quality_gain": (1 if is_treat else 0),
            "redundant_same_file_candidates": (0 if is_treat else 2),
        }
        for cat, count in cats.items():
            row = {
                "schema_version": bea_fd2a.PRIVATE_POSTHOC_DECOMPOSITION_SCHEMA_VERSION,
                "phase_run_id": phase_run_id,
                "benchmark": "contextbench",
                "private_record_id": rid,
                "policy_arm": arm,
                "fd1_category": cat,
                "category_count": count,
                "category_availability": "available",
                "loss": float(count),
                "delta_vs_v03": (float(count) - (2.0 if is_v03 and cat == "redundant_same_file_candidates" else (1.0 if is_v03 and cat == "budget_spent_on_low_marginal_gain" else 0.0))),
                "latency_ms": 50, "cost_usd": 0.0, "tokens": 0,
                "provider_calls": 0,
            }
            bea_fd2a._write_private_row(trace_dir / PRIVATE_DECOMP_FILENAME, row)

    # Objective config: 1.
    objcfg = {
        "schema_version": bea_fd2a.PRIVATE_OBJECTIVE_CONFIG_SCHEMA_VERSION,
        "phase_run_id": phase_run_id,
        "fd1_source_artifact_hash": "a" * 64,
        "fd1_source_schema_version": "bea_fd1_failure_decomposition.v1",
        "fd1_category_weights": {c: 0.2 for c in FD1_PLAN_CATEGORIES},
        "weight_derivation": {c: "loss_sum_normalized" for c in FD1_PLAN_CATEGORIES},
        "total_loss_sum_used": 10.0,
        "derived_at": _now_iso(),
    }
    bea_fd2a._write_private_objective_config(
        trace_dir / PRIVATE_OBJCFG_FILENAME, objcfg)

    pt = _parse_private_traces(trace_dir)
    return pt, 1


# Placeholder constant referenced inside _build_synthetic_private_traces
# for method listing (kept inline to avoid an unused-module-level import).
FIELDS_METHODS = list(FD2A_SOURCE_METHODS)


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    # --- G1: Identity ---
    checks.append(_check("schema_version_value", SCHEMA_VERSION == "bea_fd2a1_failure_attribution_replay.v1"))
    checks.append(_check("claim_level_value", CLAIM_LEVEL == "bea_fd2a1_failure_attribution_replay_only"))
    checks.append(_check("mode_value", MODE == "bea_fd2a1_failure_attribution_replay"))
    checks.append(_check("phase_value", PHASE == "BEA-FD2-A1"))
    checks.append(_check("generated_by_value", GENERATED_BY == "eval/bea_fd2a1_failure_attribution_replay.py"))

    # --- G2: Safe true / false flags ---
    for flag in ("aggregate_only_public_artifact", "diagnostic_only"):
        checks.append(_check(f"safe_true_{flag}", SAFE_TRUE_FLAGS.get(flag) is True))
    for flag in ("role_proxy_assigned", "posthoc_threshold_search",
                 "weights_tuned_during_bea_fd2a1",
                 "fd2a_policy_changed_during_bea_fd2a1",
                 "fd2a_weights_changed_during_bea_fd2a1",
                 "fd2a_thresholds_changed_during_bea_fd2a1",
                 "algorithm_changed_during_bea_fd2a1",
                 "new_records_added_during_bea_fd2a1",
                 "heldout_validation_claimed",
                 "v04_full_matrix_claimed",
                 "default_should_change", "promotion_ready"):
        checks.append(_check(f"false_{flag}", DEFAULT_FALSE_FLAGS.get(flag) is False))
    # role_proxy_used / target_support_proxy_used inherited from FD2-A scanner
    # discipline; FD2-A1 must not introduce them as public fields.
    checks.append(_check("no_role_proxy_used_field", "role_proxy_used" not in SAFE_TRUE_FLAGS))
    checks.append(_check("no_target_support_proxy_used_field",
                         "target_support_proxy_used" not in SAFE_TRUE_FLAGS))

    # --- G3: Mechanism buckets (8) ---
    checks.append(_check("mechanism_buckets_count_8", len(MECHANISM_BUCKETS) == 8))
    for b in MECHANISM_BUCKETS:
        checks.append(_check(f"mechanism_bucket_present_{b}", b in MECHANISM_BUCKETS))
    checks.append(_check("actionable_buckets_count_6", len(ACTIONABLE_BUCKETS) == 6))
    checks.append(_check("no_go_dominating_buckets_count_2",
                         len(NO_GO_DOMINATING_BUCKETS) == 2))
    checks.append(_check("diffuse_is_not_actionable",
                         "diffuse_or_unclassified" not in ACTIONABLE_BUCKETS))
    checks.append(_check("candidate_availability_not_actionable",
                         "candidate_availability_limit" not in ACTIONABLE_BUCKETS))

    # --- G4: Expected private trace counts ---
    checks.append(_check("expected_records_38", EXPECTED_RECORDS_SUCCESSFUL == 38))
    checks.append(_check("expected_score_190", EXPECTED_PRIVATE_SCORE_COUNT == 190))
    checks.append(_check("expected_decision_190", EXPECTED_PRIVATE_DECISION_COUNT == 190))
    checks.append(_check("expected_feat_190",
                         EXPECTED_PRIVATE_FD1_OBJECTIVE_FEATURE_COUNT == 190))
    checks.append(_check("expected_decomp_950",
                         EXPECTED_PRIVATE_POSTHOC_DECOMPOSITION_COUNT == 950))
    checks.append(_check("expected_objcfg_1",
                         EXPECTED_PRIVATE_OBJECTIVE_CONFIG_COUNT == 1))
    checks.append(_check("expected_trace_counts_table_5",
                         len(EXPECTED_PRIVATE_TRACE_COUNTS) == 5))
    checks.append(_check("decomp_count_is_5_arms_x_5_cats_x_38",
                         EXPECTED_PRIVATE_POSTHOC_DECOMPOSITION_COUNT
                         == 5 * 5 * 38))

    # --- G5: Statuses enum ---
    for status in STATUSES:
        checks.append(_check(f"status_enum_{status}", isinstance(status, str)))
    checks.append(_check("statuses_count_7", len(STATUSES) == 7))

    # --- G6: Synthetic private trace parser ---
    with tempfile.TemporaryDirectory(prefix="fd2a1_st_") as sd:
        td = Path(sd)
        pt, records_successful = _build_synthetic_private_traces(td)
        checks.append(_check("synth_records_successful_1", records_successful == 1))
        checks.append(_check("parse_score_5", pt.score_count == 5))
        checks.append(_check("parse_decision_5", pt.decision_count == 5))
        checks.append(_check("parse_feat_5", pt.feat_count == 5))
        checks.append(_check("parse_decomp_25", pt.decomp_count == 25))
        checks.append(_check("parse_objcfg_1", pt.objcfg_count == 1))
        checks.append(_check("parse_failures_zero", pt.total_parse_failures == 0))
        checks.append(_check("trace_dir_existed", pt.trace_dir_existed is True))

        # --- G7: Parser failure handling ---
        # Corrupt one line in each file and confirm parse failures counted.
        bad_score = td / "bad.private.jsonl"
        bad_score.write_text('{"valid": 1}\n{not json}\n', encoding="utf-8")
        rows, fails = _parse_jsonl(bad_score, SCORE_REQUIRED_KEYS)
        # Line 1: valid JSON but missing required keys -> 1 failure.
        # Line 2: invalid JSON -> 1 failure. Total = 2.
        checks.append(_check("parse_fail_missing_keys_counted", fails == 2))
        checks.append(_check("parse_fail_missing_keys_rows", len(rows) == 0))
        bad_json = td / "bad2.private.jsonl"
        bad_json.write_text('{"phase_run_id":"x"}\nnot json at all\n{"phase_run_id":"y","benchmark":"b","private_record_id":"r","policy_arm":"a","runtime_query_feature_summary":{},"stop_reason":"s","score_outcome":"o"}\n', encoding="utf-8")
        rows2, fails2 = _parse_jsonl(bad_json, SCORE_REQUIRED_KEYS)
        # Line 1: missing required keys -> fail. Line 2: invalid -> fail.
        # Line 3: all keys present -> row. Total fails = 2.
        checks.append(_check("parse_fail_mixed_count", fails2 == 2))
        checks.append(_check("parse_fail_mixed_rows", len(rows2) == 1))
        # Missing file: zero rows, zero failures.
        rows3, fails3 = _parse_jsonl(td / "missing.jsonl", SCORE_REQUIRED_KEYS)
        checks.append(_check("parse_missing_file_rows", rows3 == []))
        checks.append(_check("parse_missing_file_failures", fails3 == 0))

        # --- G8: Objective-config JSON parser ---
        obj_path = td / "obj.json"
        obj_path.write_text('{"phase_run_id":"x","fd1_source_artifact_hash":"h","fd1_source_schema_version":"v","fd1_category_weights":{}}', encoding="utf-8")
        obj, ofails = _parse_json_object(obj_path, OBJCFG_REQUIRED_KEYS)
        checks.append(_check("objcfg_parse_ok", obj is not None and ofails == 0))
        bad_obj_path = td / "bad_obj.json"
        bad_obj_path.write_text('{"phase_run_id":"x"}', encoding="utf-8")
        obj2, ofails2 = _parse_json_object(bad_obj_path, OBJCFG_REQUIRED_KEYS)
        checks.append(_check("objcfg_parse_missing_keys", obj2 is None and ofails2 == 1))
        bad_json_path = td / "bad_json_obj.json"
        bad_json_path.write_text('not json', encoding="utf-8")
        obj3, ofails3 = _parse_json_object(bad_json_path, OBJCFG_REQUIRED_KEYS)
        checks.append(_check("objcfg_parse_bad_json", obj3 is None and ofails3 == 1))

        # --- G9: Manifest count expectations (synthetic) ---
        checks.append(_check("synth_manifest_score_5", pt.score_count == 5))
        checks.append(_check("synth_manifest_decision_5", pt.decision_count == 5))
        checks.append(_check("synth_manifest_feat_5", pt.feat_count == 5))
        checks.append(_check("synth_manifest_decomp_25", pt.decomp_count == 25))
        checks.append(_check("synth_manifest_objcfg_1", pt.objcfg_count == 1))

        # --- G10: Mechanism bucket aggregation ---
        decomp_idx = _index_decomp_rows(pt.decomp_rows)
        score_idx = _index_score_rows(pt.score_rows)
        feat_idx = _index_feat_rows_by_record(pt.feat_rows)
        paired_rids = sorted({
            rid for (rid, arm) in decomp_idx
            if arm == FD2A_SOURCE_BASELINE_ARM
            and (rid, FD2A_SOURCE_TREATMENT_ARM) in decomp_idx
        })
        checks.append(_check("paired_rids_1", len(paired_rids) == 1))
        bucket_counts: dict[str, int] = {b: 0 for b in MECHANISM_BUCKETS}
        records_regressed = 0
        for rid in paired_rids:
            v03_post = decomp_idx.get((rid, FD2A_SOURCE_BASELINE_ARM), {})
            fd1lw_post = decomp_idx.get((rid, FD2A_SOURCE_TREATMENT_ARM), {})
            fd1lw_score = score_idx.get((rid, FD2A_SOURCE_TREATMENT_ARM), {})
            fd1lw_summary = fd1lw_score.get("runtime_query_feature_summary", {})
            if not isinstance(fd1lw_summary, dict):
                fd1lw_summary = {}
            fd1lw_features = feat_idx.get(rid, [])
            if _record_regressed(v03_post, fd1lw_post):
                records_regressed += 1
            buckets = _attribute_record_buckets(
                v03_post, fd1lw_post, fd1lw_summary, fd1lw_features,
            )
            for b in buckets:
                bucket_counts[b] = bucket_counts.get(b, 0) + 1
        checks.append(_check("synth_records_regressed_1", records_regressed == 1))
        # Synthetic record: gold displaced (v03 gold present, fd1lw absent)
        # → gold_file_displacement bucket must fire.
        checks.append(_check("synth_gold_file_displacement",
                             bucket_counts.get("gold_file_displacement", 0) >= 1))
        # v03 had duplicates, fd1lw suppressed them → redundancy_overcorrection.
        checks.append(_check("synth_redundancy_overcorrection",
                             bucket_counts.get("redundancy_overcorrection", 0) >= 1))
        # fd1lw latency worsened → latency_category bucket.
        checks.append(_check("synth_latency_category",
                             bucket_counts.get("latency_category_non_actionable_or_dominating", 0) >= 1))
        # budget improved (1->0) while gold worsened (0->1) and latency
        # worsened (0->1) → collision bucket fires.
        checks.append(_check("synth_collision_fires",
                             bucket_counts.get("aggregate_weight_category_collision", 0) >= 1))
        # deduped=8, 2*budget=10 → 8<10 → candidate_availability_limit fires.
        checks.append(_check("synth_candidate_availability_limit",
                             bucket_counts.get("candidate_availability_limit", 0) >= 1))
        # At least one actionable bucket fired → not diffuse.
        checks.append(_check("synth_not_diffuse",
                             bucket_counts.get("diffuse_or_unclassified", 0) == 0))

        # --- G11: Collision pair detection ---
        # Synthetic record: budget improved, gold+latency worsened →
        # collision pairs (budget vs gold) and (budget vs latency).
        pairs = _collision_pairs_for_record(
            decomp_idx.get((paired_rids[0], FD2A_SOURCE_BASELINE_ARM), {}),
            decomp_idx.get((paired_rids[0], FD2A_SOURCE_TREATMENT_ARM), {}),
        )
        checks.append(_check("synth_collision_pairs_present", len(pairs) >= 1))
        checks.append(_check("synth_collision_pair_budget_vs_gold",
                             "budget_spent_on_low_marginal_gain__vs__gold_file_absent" in pairs))
        # Construct a synthetic all-worsened scenario: NO collision pairs
        # should fire (no improvements).
        v03_clean = {c: {"category_count": 0} for c in FD1_BINARY_CATEGORIES}
        fd1lw_all_worse = {
            "gold_file_absent": {"category_count": 1},
            "correct_file_wrong_span": {"category_count": 1},
            "budget_spent_on_low_marginal_gain": {"category_count": 1},
            "latency_without_quality_gain": {"category_count": 1},
        }
        pairs_all_worse = _collision_pairs_for_record(v03_clean, fd1lw_all_worse)
        checks.append(_check("synth_no_collision_pairs_all_worsen",
                             pairs_all_worse == []))

        # --- G12: Counterfactual buckets ---
        cf = _counterfactual_buckets_for_record(
            decomp_idx.get((paired_rids[0], FD2A_SOURCE_BASELINE_ARM), {}),
            decomp_idx.get((paired_rids[0], FD2A_SOURCE_TREATMENT_ARM), {}),
            {"deduped_candidate_count": 8}, FD2A_SOURCE_BUDGET,
        )
        # deduped=8, budget=5 → 8>5 → better_candidates_in_pool_above_budget.
        checks.append(_check("synth_cf_better_candidates_in_pool",
                             "better_candidates_in_pool_above_budget" in cf))
        # 8 is NOT > 2*5=10 → no 2x bucket.
        checks.append(_check("synth_cf_no_2x_bucket",
                             "better_candidates_in_pool_above_2x_budget" not in cf))
        # v03 had gold, fd1lw lost it → v03_selected_correct_file.
        checks.append(_check("synth_cf_v03_correct_file",
                             "v03_selected_correct_file_fd1lw_did_not" in cf))
        # v03 had duplicates → v03_retained_duplicates.
        checks.append(_check("synth_cf_v03_retained_duplicates",
                             "v03_retained_duplicates_fd1lw_suppressed" in cf))

        # --- G13: Forbidden scanner ---
        # Safe sample: aggregate-only, records-only.
        safe_sample = {
            "schema_version": SCHEMA_VERSION,
            "status": "no_go_mechanism_diffuse",
            "mechanism_bucket_records": [
                {"mechanism_bucket": "gold_file_displacement",
                 "record_count": 3, "rate_of_attributed": 0.078947,
                 "rate_of_regressed": 0.25, "is_actionable": True,
                 "is_no_go_dominating": False},
            ],
            "manifests": [{"manifest_name": "private_score_manifest",
                           "records_written": True, "record_count": 190,
                           "schema_version": bea_fd2a.PRIVATE_SCORE_SCHEMA_VERSION,
                           "manifest_hash": "a" * 64,
                           "storage_class": "tmp_private",
                           "path_publicly_serialized": False}],
            "framing": {"signal_strength": "bea_fd2a1_attribution_replay_aggregate_only"},
            "fd2a_source_artifact_hash": "b" * 64,
            "fd1_source_artifact_hash": "c" * 64,
        }
        checks.append(_check("scanner_allows_safe", not _scan_fd2a1(safe_sample)))
        # Forbidden leaks.
        for fk in ("private_trace_dir", "private_score_dir",
                   "per_record_buckets", "per_record_attribution",
                   "objective_config_payload", "fd1_category_weights_payload",
                   "candidate_paths", "candidate_keys", "query_text",
                   "gold_paths", "gold_lines", "snippets",
                   "selected_order", "private_record_ids",
                   "raw_score_row", "raw_decision_row",
                   "weight_derivation_payload",
                   "per_record_collisions", "per_record_counterfactual",
                   "fd2a_source_artifact_path", "fd1_source_artifact_path",
                   "winner", "calibration", "method_winner",
                   "recommended_default", "ranking", "decision",
                   "hard_gates", "failure_category_counts",
                   "mechanism_bucket_counts", "self_test_checks",
                   "checks", "role_proxy", "role_proxy_assignment"):
            leaked = dict(safe_sample)
            leaked[fk] = "leak"
            checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_fd2a1(leaked))))

        # --- G14: Fail-closed enforcement ---
        try:
            _enforce_fd2a1_no_forbidden(safe_sample)
            checks.append(_check("fail_closed_clean", True))
        except SystemExit:
            checks.append(_check("fail_closed_clean", False))
        for lk in ("private_trace_dir", "per_record_buckets",
                   "gold_paths", "winner", "hard_gates",
                   "self_test_checks", "fd2a_source_artifact_path"):
            leaked = dict(safe_sample)
            leaked[lk] = "leak"
            try:
                _enforce_fd2a1_no_forbidden(leaked)
                checks.append(_check(f"fail_closed_{lk}", False))
            except SystemExit:
                checks.append(_check(f"fail_closed_{lk}", True))

        # --- G15: Public records-only shape (build a synthetic report) ---
        # Use a minimal committed FD2-A artifact shape for the report builder.
        synth_fd2a_artifact = {
            "schema_version": bea_fd2a.SCHEMA_VERSION,
            "status": "no_go_no_fd1_loss_reduction",
            "source_run_records": [{
                "source_phase": "BEA-FD2-A",
                "source_ci_run_id": FD2A_SOURCE_CI_RUN_ID,
                "replayed_successful_records": 1,
                "expected_private_score_count": 5,
                "expected_private_decision_count": 5,
                "expected_private_fd1_objective_feature_count": 5,
                "expected_private_posthoc_decomposition_count": 25,
                "expected_private_objective_config_count": 1,
                "fd1_source_schema_version": "bea_fd1_failure_decomposition.v1",
                "fd1_source_artifact_hash": "a" * 64,
            }],
            "arm_delta_records": [
                {"baseline_arm": FD2A_SOURCE_BASELINE_ARM,
                 "treatment_arm": FD2A_SOURCE_TREATMENT_ARM,
                 "metric": "file_recall@10", "delta": -0.078947},
                {"baseline_arm": FD2A_SOURCE_BASELINE_ARM,
                 "treatment_arm": FD2A_SOURCE_TREATMENT_ARM,
                 "metric": "mrr", "delta": -0.053509},
            ],
            "ablation_delta_records": [
                {"component": "budget_used",
                 "baseline_arm": bea_fd2a.COVERAGE_ONLY_ARM,
                 "treatment_arm": FD2A_SOURCE_TREATMENT_ARM,
                 "delta": 0.0},
                {"component": "duplicate_file_count",
                 "baseline_arm": bea_fd2a.COVERAGE_ONLY_ARM,
                 "treatment_arm": FD2A_SOURCE_TREATMENT_ARM,
                 "delta": -0.026316},
            ],
            "manifests": [],
        }
        report = _build_attribution_report(
            self_test_passed=True, self_test_checks_total=0,
            self_test_checks_passed=None,
            openlocus_binary_source="self_test", network_mode="self_test",
            private_trace_storage_class="tmp_private",
            pt=pt, fd2a_artifact=synth_fd2a_artifact,
            fd2a_source_schema_version=bea_fd2a.SCHEMA_VERSION,
            fd2a_source_artifact_hash="b" * 64,
            fd1_source_schema_version="bea_fd1_failure_decomposition.v1",
            fd1_source_artifact_hash="a" * 64,
            records_successful=1, records_attempted_total=1,
            records_excluded=0, contextbench_successful=1,
            repoqa_successful=0,
            committed_status="no_go_no_fd1_loss_reduction",
            aggregate_runtime_seconds=0.5,
            failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        )
        # Records-only shape: every required table is a list.
        for table in ("source_run_records", "pairwise_outcome_delta_records",
                      "mechanism_bucket_records", "component_delta_records",
                      "counterfactual_availability_records",
                      "category_collision_records", "gate_records",
                      "private_manifest_records",
                      "failure_category_count_records"):
            checks.append(_check(f"table_{table}_is_list",
                                 isinstance(report.get(table), list)))
            checks.append(_check(f"table_{table}_nonempty",
                                 len(report.get(table, [])) > 0))
        # framing + forbidden_scan present.
        checks.append(_check("framing_present", isinstance(report.get("framing"), dict)))
        checks.append(_check("forbidden_scan_present",
                             isinstance(report.get("forbidden_scan"), dict)))
        checks.append(_check("forbidden_scan_pass",
                             report.get("forbidden_scan", {}).get("status") == "pass"))
        # No forbidden top-level fields.
        for ff in ("private_trace_dir", "per_record_buckets",
                   "objective_config_payload", "candidate_paths",
                   "gold_paths", "selected_order", "winner", "calibration",
                   "hard_gates", "failure_category_counts",
                   "mechanism_bucket_counts", "self_test_checks",
                   "fd2a_source_artifact_path", "fd1_source_artifact_path",
                   "role_proxy_used", "target_support_proxy_used"):
            checks.append(_check(f"no_top_level_{ff}", ff not in report))
        # Self-scan clean.
        checks.append(_check("self_scan_clean", not _scan_fd2a1(report)))

        # --- G16: Records-only natural-key uniqueness ---
        checks.append(_check("srr_unique", not _check_unique_records(
            report.get("source_run_records", []), _srr_natural_key, "source_run_records")))
        checks.append(_check("podr_unique", not _check_unique_records(
            report.get("pairwise_outcome_delta_records", []), _podr_natural_key,
            "pairwise_outcome_delta_records")))
        checks.append(_check("mbr_unique", not _check_unique_records(
            report.get("mechanism_bucket_records", []), _mbr_natural_key,
            "mechanism_bucket_records")))
        checks.append(_check("cdr_unique", not _check_unique_records(
            report.get("component_delta_records", []), _cdr_natural_key,
            "component_delta_records")))
        checks.append(_check("car_unique", not _check_unique_records(
            report.get("counterfactual_availability_records", []), _car_natural_key,
            "counterfactual_availability_records")))
        checks.append(_check("ccr_unique", not _check_unique_records(
            report.get("category_collision_records", []), _ccr_natural_key,
            "category_collision_records")))
        checks.append(_check("gr_unique", not _check_unique_records(
            report.get("gate_records", []), _gr_natural_key, "gate_records")))
        checks.append(_check("pmr_unique", not _check_unique_records(
            report.get("private_manifest_records", []), _pmr_natural_key,
            "private_manifest_records")))
        checks.append(_check("fcr_unique", not _check_unique_records(
            report.get("failure_category_count_records", []), _fcr_natural_key,
            "failure_category_count_records")))

        # --- G17: Mechanism bucket records fields ---
        mbr_rows = report.get("mechanism_bucket_records", [])
        mbr_buckets = {r.get("mechanism_bucket") for r in mbr_rows}
        for b in MECHANISM_BUCKETS:
            checks.append(_check(f"mbr_has_{b}", b in mbr_buckets))
        for r in mbr_rows:
            for field in ("mechanism_bucket", "record_count",
                          "rate_of_attributed", "rate_of_regressed",
                          "is_actionable", "is_no_go_dominating"):
                checks.append(_check(f"mbr_field_{field}",
                                     any(field in rr for rr in mbr_rows)))

        # --- G18: Gate records present ---
        gr_rows = report.get("gate_records", [])
        gate_names = {r.get("gate") for r in gr_rows if isinstance(r, dict)}
        for gate in ("records_attributed", "records_successful",
                     "records_regressed", "private_score_count",
                     "private_decision_count",
                     "private_fd1_objective_feature_count",
                     "private_posthoc_decomposition_count",
                     "private_objective_config_count",
                     "parse_failure_count", "replay_protocol_match",
                     "forbidden_scan_pass", "actionable_concentration",
                     "candidate_availability_dominates", "diffuse_dominates"):
            checks.append(_check(f"gate_has_{gate}", gate in gate_names))
        # Top actionable bucket labels must NOT be serialized as gate rows
        # (the inherited scanner forbids the ``label`` key; the bucket
        # ranking is published via mechanism_bucket_records instead).
        checks.append(_check("gate_no_top_actionable_bucket_label_rows",
                             not any(isinstance(g, str) and g.startswith("top_actionable_bucket_")
                                     for g in gate_names)))

        # --- G19: Private manifest records (5) ---
        pmr_rows = report.get("private_manifest_records", [])
        pmr_names = {r.get("manifest_name") for r in pmr_rows}
        for name in ("private_score_manifest", "private_decision_manifest",
                     "private_fd1_objective_feature_manifest",
                     "private_posthoc_decomposition_manifest",
                     "private_objective_config_manifest"):
            checks.append(_check(f"pmr_has_{name}", name in pmr_names))
        for r in pmr_rows:
            checks.append(_check("pmr_path_not_serialized",
                                 r.get("path_publicly_serialized") is False))
            checks.append(_check("pmr_hash_64",
                                 len(r.get("manifest_hash", "")) == 64))

        # --- G20: Status decision logic ---
        # Synthetic report has 1 record, gold displaced → actionable
        # concentration = 1.0 (1 regressed, 1 in gold_file_displacement).
        # But records_successful=1 != EXPECTED_RECORDS_SUCCESSFUL=38 →
        # replay_protocol_match=False → status=no_go_replay_mismatch.
        checks.append(_check("synth_status_replay_mismatch",
                             report.get("status") == "no_go_replay_mismatch"))
        # Force a "match" scenario by monkey-patching expected counts via a
        # direct _decide_status call.
        status_match = _decide_status(
            records_successful=38, records_attributed=38,
            replay_protocol_match=True, total_parse_failures=0,
            forbidden_scan_pass=True, blocking_failure_count=0,
            actionable_concentration=0.7, records_regressed=10,
            candidate_availability_dominates=False,
            diffuse_dominates=False,
        )
        checks.append(_check("decide_status_pass",
                             status_match == "bea_fd2a1_attribution_replay_pass"))
        status_diffuse = _decide_status(
            records_successful=38, records_attributed=38,
            replay_protocol_match=True, total_parse_failures=0,
            forbidden_scan_pass=True, blocking_failure_count=0,
            actionable_concentration=0.3, records_regressed=10,
            candidate_availability_dominates=False,
            diffuse_dominates=True,
        )
        checks.append(_check("decide_status_diffuse",
                             status_diffuse == "no_go_mechanism_diffuse"))
        status_cand = _decide_status(
            records_successful=38, records_attributed=38,
            replay_protocol_match=True, total_parse_failures=0,
            forbidden_scan_pass=True, blocking_failure_count=0,
            actionable_concentration=0.3, records_regressed=10,
            candidate_availability_dominates=True,
            diffuse_dominates=False,
        )
        checks.append(_check("decide_status_candidate_availability",
                             status_cand == "no_go_candidate_availability_limit"))
        status_mismatch = _decide_status(
            records_successful=30, records_attributed=38,
            replay_protocol_match=False, total_parse_failures=0,
            forbidden_scan_pass=True, blocking_failure_count=0,
            actionable_concentration=0.9, records_regressed=10,
            candidate_availability_dominates=False,
            diffuse_dominates=False,
        )
        checks.append(_check("decide_status_replay_mismatch",
                             status_mismatch == "no_go_replay_mismatch"))
        status_forbidden = _decide_status(
            records_successful=38, records_attributed=38,
            replay_protocol_match=True, total_parse_failures=0,
            forbidden_scan_pass=False, blocking_failure_count=0,
            actionable_concentration=0.9, records_regressed=10,
            candidate_availability_dominates=False,
            diffuse_dominates=False,
        )
        checks.append(_check("decide_status_forbidden_scan",
                             status_forbidden == "fail_forbidden_scan"))
        status_parse = _decide_status(
            records_successful=38, records_attributed=38,
            replay_protocol_match=True, total_parse_failures=3,
            forbidden_scan_pass=True, blocking_failure_count=0,
            actionable_concentration=0.9, records_regressed=10,
            candidate_availability_dominates=False,
            diffuse_dominates=False,
        )
        checks.append(_check("decide_status_parse_failures",
                             status_parse == "fail_schema_contract"))

        # --- G21: Unavailable report ---
        unavail = _build_unavailable_report(
            "network_required_but_disabled", self_test_passed=True,
            openlocus_binary_source="self_test", network_mode="self_test",
        )
        checks.append(_check("unavail_status", unavail["status"] == "unavailable_with_reason"))
        checks.append(_check("unavail_scan_clean", not _scan_fd2a1(unavail)))
        for table in ("source_run_records", "pairwise_outcome_delta_records",
                      "mechanism_bucket_records", "component_delta_records",
                      "counterfactual_availability_records",
                      "category_collision_records", "gate_records",
                      "private_manifest_records",
                      "failure_category_count_records"):
            checks.append(_check(f"unavail_table_{table}_is_list",
                                 isinstance(unavail.get(table), list)))
        # Unavailable report has records_attributed=0.
        checks.append(_check("unavail_records_attributed_0",
                             unavail.get("records_attributed") == 0))
        # Unavailable report has all mechanism buckets present (with 0 counts).
        mbr_unavail = {r.get("mechanism_bucket") for r in unavail.get("mechanism_bucket_records", [])}
        for b in MECHANISM_BUCKETS:
            checks.append(_check(f"unavail_mbr_has_{b}", b in mbr_unavail))

        # --- G22: Private manifest records in unavailable report ---
        pmr_unavail = unavail.get("private_manifest_records", [])
        checks.append(_check("unavail_pmr_count_5", len(pmr_unavail) == 5))
        for r in pmr_unavail:
            checks.append(_check("unavail_pmr_records_written_false",
                                 r.get("records_written") is False))
            checks.append(_check("unavail_pmr_record_count_0",
                                 r.get("record_count") == 0))

        # --- G23: CLI surface ---
        parser = build_parser()
        option_strings: set[str] = set()
        for action in parser._actions:
            for opt in action.option_strings:
                option_strings.add(opt)
        for opt in ("--self-test", "--out", "--fd2a-artifact", "--fd1-artifact",
                    "--openlocus", "--private-trace-dir",
                    "--enable-external-benchmark-network"):
            checks.append(_check(f"cli_has_{opt}", opt in option_strings))

        # --- G24: Go/No-Go constants ---
        checks.append(_check("go_concentration_060",
                             GO_ACTIONABLE_CONCENTRATION == 0.60))
        checks.append(_check("go_top_buckets_2", GO_TOP_BUCKETS == 2))

        # --- G25: Source binding context ---
        checks.append(_check("fd2a_source_checkpoint", FD2A_SOURCE_CHECKPOINT == "df82ddb"))
        checks.append(_check("fd2a_source_ci_run_id", FD2A_SOURCE_CI_RUN_ID == "28025382422"))
        checks.append(_check("fd2a_source_local_checkpoint",
                             FD2A_SOURCE_LOCAL_CHECKPOINT == "709b0cb"))
        checks.append(_check("fd2a_source_status_no_go",
                             FD2A_SOURCE_STATUS == "no_go_no_fd1_loss_reduction"))

        # --- G26: FD2-A policy unchanged invariants ---
        checks.append(_check("fd2a_budget_unchanged",
                             FD2A_SOURCE_BUDGET == bea_fd2a.FIXED_BUDGET == 5))
        checks.append(_check("fd2a_methods_unchanged",
                             tuple(FD2A_SOURCE_METHODS) == bea_fd2a.ALLOWED_METHODS))
        checks.append(_check("fd2a_arms_unchanged",
                             tuple(FD2A_SOURCE_FIXED_ARMS) == bea_fd2a.FIXED_ARMS))
        checks.append(_check("fd2a_treatment_arm_unchanged",
                             FD2A_SOURCE_TREATMENT_ARM == bea_fd2a.TREATMENT_ARM))
        checks.append(_check("fd2a_baseline_arm_unchanged",
                             FD2A_SOURCE_BASELINE_ARM == bea_fd2a.DELTA_BASELINE_ARM))
        checks.append(_check("fd2a_gate_constants_unchanged",
                             bea_fd2a.GATE_SETWISE_DIFF_VS_V03 == 0.25
                             and bea_fd2a.GATE_SETWISE_DIFF_VS_COVERAGE == 0.15
                             and bea_fd2a.GATE_QUALITY_MARGIN_FILE_RECALL == 0.03))

        # --- G27: Parser required keys cover manifest schema ---
        checks.append(_check("score_required_has_7",
                             len(SCORE_REQUIRED_KEYS) == 7))
        checks.append(_check("decision_required_has_6",
                             len(DECISION_REQUIRED_KEYS) == 6))
        checks.append(_check("feat_required_has_11",
                             len(FEAT_REQUIRED_KEYS) == 11))
        checks.append(_check("decomp_required_has_7",
                             len(DECOMP_REQUIRED_KEYS) == 7))
        checks.append(_check("objcfg_required_has_4",
                             len(OBJCFG_REQUIRED_KEYS) == 4))

        # --- G28: FD2-A1 composes FD2-A scanner ---
        # FD2-A1 forbidden extra keys must include FD2-A1-specific additions
        # AND inherit FD2-A's forbidden keys (via bea_fd2a._scan_fd2a).
        checks.append(_check("fd2a1_inherits_fd2a_scanner",
                             "private_score_path" in bea_fd2a.FD2A_FORBIDDEN_EXTRA_KEYS))
        checks.append(_check("fd2a1_extra_keys_has_private_trace_dir",
                             "private_trace_dir" in FD2A1_FORBIDDEN_EXTRA_KEYS))
        checks.append(_check("fd2a1_extra_keys_has_per_record_buckets",
                             "per_record_buckets" in FD2A1_FORBIDDEN_EXTRA_KEYS))

        # --- G29: record_regressed detection ---
        v03_clean = {c: {"count": 0} for c in FD1_BINARY_CATEGORIES}
        fd1lw_clean = {c: {"count": 0} for c in FD1_BINARY_CATEGORIES}
        checks.append(_check("no_regression_when_clean",
                             _record_regressed(v03_clean, fd1lw_clean) is False))
        fd1lw_worse = dict(fd1lw_clean)
        fd1lw_worse["gold_file_absent"] = {"count": 1}
        checks.append(_check("regression_when_gold_displaced",
                             _record_regressed(v03_clean, fd1lw_worse) is True))
        # Improvement only (fd1lw better) → not a regression.
        fd1lw_better = {c: {"count": 0} for c in FD1_BINARY_CATEGORIES}
        v03_worse = {c: {"count": 0} for c in FD1_BINARY_CATEGORIES}
        v03_worse["gold_file_absent"] = {"count": 1}
        checks.append(_check("no_regression_when_fd1lw_better",
                             _record_regressed(v03_worse, fd1lw_better) is False))

        # --- G30: Provider calls zero ---
        checks.append(_check("no_provider_calls_field",
                             "provider_calls" not in report
                             or report.get("provider_calls_made") is False))
        checks.append(_check("unavail_no_provider_calls",
                             unavail.get("provider_calls_made") is False))

        # --- G31: License fields ---
        for field, expected in LICENSE_FIELDS.items():
            checks.append(_check(f"license_{field}",
                                 report.get(field) == expected))

        # --- G32: Forbidden scanner category names ---
        # Inject a forbidden key and confirm the violation category is
        # fd2a1-specific (or inherited from FD2-A).
        leaked = {"private_trace_dir": "leak"}
        scan_v = _scan_fd2a1(leaked)
        checks.append(_check("scanner_category_fd2a1",
                             any(v.get("category") == "forbidden_fd2a1_extra_key"
                                 for v in scan_v)))
        leaked2 = {"role_proxy": "leak"}
        scan_v2 = _scan_fd2a1(leaked2)
        checks.append(_check("scanner_inherits_fd2a_role_proxy",
                             bool(scan_v2)))

        # --- G33: Aggregation runtime present ---
        checks.append(_check("has_runtime", "aggregate_runtime_seconds" in report))
        checks.append(_check("unavail_no_runtime",
                             "aggregate_runtime_seconds" not in unavail))

        # --- G34: failure_category_count_records covers all categories ---
        fcr_rows = report.get("failure_category_count_records", [])
        fcr_cats = {r.get("failure_category") for r in fcr_rows}
        for cat in FAILURE_CATEGORIES:
            checks.append(_check(f"fcr_has_{cat}", cat in fcr_cats))

        # --- G35: framing is_failure_attribution_only ---
        checks.append(_check("framing_is_failure_attribution_only",
                             report.get("framing", {}).get("is_failure_attribution_only") is True))
        checks.append(_check("framing_not_fd2b",
                             report.get("framing", {}).get("is_fd2_b") is False))

        # --- G36: Build unavailable when committed FD2-A artifact missing ---
        unavail2 = _build_unavailable_report(
            "fd2a_artifact_missing", self_test_passed=True,
            openlocus_binary_source="self_test", network_mode="self_test",
        )
        checks.append(_check("unavail_artifact_missing_status",
                             unavail2["status"] == "unavailable_with_reason"))
        checks.append(_check("unavail_artifact_missing_reason",
                             unavail2.get("failure_reason_category") == "fd2a_artifact_missing"))

        # --- G37: Mechanism bucket aggregation sum >= records_attributed ---
        # (records can be in multiple buckets, so sum >= records_attributed).
        total_bucket_assignments = sum(r.get("record_count", 0) for r in mbr_rows)
        checks.append(_check("bucket_assignments_gte_attributed",
                             total_bucket_assignments >= 1))

        # --- G38: counterfactual_availability + category_collision tables ---
        car_rows = report.get("counterfactual_availability_records", [])
        ccr_rows = report.get("category_collision_records", [])
        checks.append(_check("car_records_present", len(car_rows) >= 1))
        # Synthetic record has all categories worsened (no collision pairs).
        checks.append(_check("ccr_records_may_be_empty_for_synthetic",
                             isinstance(ccr_rows, list)))

        # --- G39: source_run_records fields ---
        srr = report.get("source_run_records", [{}])[0] if report.get("source_run_records") else {}
        for field in ("source_phase", "source_ci_run_id", "source_checkpoint",
                      "source_status", "expected_successful_records",
                      "replayed_successful_records",
                      "expected_private_score_count",
                      "replayed_private_score_count",
                      "fd2a_source_schema_version",
                      "fd2a_source_artifact_hash",
                      "fd1_source_schema_version",
                      "fd1_source_artifact_hash",
                      "replay_protocol_match", "replay_mismatch_reason"):
            checks.append(_check(f"srr_has_{field}", field in srr))
        checks.append(_check("srr_no_artifact_path",
                             "fd2a_source_artifact_path" not in srr
                             and "fd1_source_artifact_path" not in srr))

        # --- G40: Pairwise outcome delta records repackaged ---
        podr_rows = report.get("pairwise_outcome_delta_records", [])
        checks.append(_check("podr_count_2", len(podr_rows) == 2))
        for r in podr_rows:
            for field in ("baseline_arm", "treatment_arm", "metric",
                          "delta", "record_count"):
                checks.append(_check(f"podr_has_{field}", field in r))

        # --- G41: Component delta records repackaged ---
        cdr_rows = report.get("component_delta_records", [])
        checks.append(_check("cdr_count_2", len(cdr_rows) == 2))
        for r in cdr_rows:
            for field in ("component", "baseline_arm", "treatment_arm",
                          "delta", "record_count"):
                checks.append(_check(f"cdr_has_{field}", field in r))

        # --- G42: No-Go status when records_regressed is 0 ---
        status_zero = _decide_status(
            records_successful=38, records_attributed=38,
            replay_protocol_match=True, total_parse_failures=0,
            forbidden_scan_pass=True, blocking_failure_count=0,
            actionable_concentration=0.0, records_regressed=0,
            candidate_availability_dominates=False,
            diffuse_dominates=False,
        )
        checks.append(_check("decide_status_zero_regressed_diffuse",
                             status_zero == "no_go_mechanism_diffuse"))

    all_passed = all(c["passed"] for c in checks if c is not None)
    return checks, all_passed


# --- CLI ---


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description="BEA-FD2-A1 Direct FD1 Objective Failure Attribution Replay"
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd2a-artifact", type=Path, default=DEFAULT_FD2A_ARTIFACT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--openlocus", default=None)
    ap.add_argument("--private-trace-dir", default=None)
    ap.add_argument("--enable-external-benchmark-network", action="store_true")
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
        print(f"self_test_passed={passed} ({passed_count}/{len(checks)} checks)")
        sys.exit(0 if passed else 1)

    out_path = args.out if args.out is not None else DEFAULT_OUT
    fd2a_artifact_path = (args.fd2a_artifact if args.fd2a_artifact is not None
                          else DEFAULT_FD2A_ARTIFACT)
    fd1_artifact_path = (args.fd1_artifact if args.fd1_artifact is not None
                         else DEFAULT_FD1_ARTIFACT)
    enable_network = bool(args.enable_external_benchmark_network)

    checks, self_test_passed = run_self_test_checks()
    self_test_checks_total = len(checks)
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact", file=sys.stderr)
        sys.exit(1)

    # Default no-network path: truthfully unavailable.
    if not enable_network:
        report = _build_unavailable_report(
            "network_required_but_disabled", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source="missing", network_mode="disabled_opt_in",
        )
        # Read the committed FD2-A public artifact for replay-match context
        # (read-only; status / schema / hash only). This is allowed even
        # with no network because the artifact is committed in-repo.
        fd2a_artifact, fd2a_schema, fd2a_hash, fd2a_status = (
            _load_committed_fd2a_artifact(fd2a_artifact_path)
        )
        if fd2a_status == "pass":
            report = _build_unavailable_report(
                "network_required_but_disabled",
                self_test_passed=self_test_passed,
                self_test_checks_total=self_test_checks_total,
                openlocus_binary_source="missing", network_mode="disabled_opt_in",
                fd2a_artifact_read=True,
                fd2a_source_schema_version=fd2a_schema,
                fd2a_source_artifact_hash=fd2a_hash,
                committed_status=str(fd2a_artifact.get("status", "") or ""),
                replay_protocol_match=False,
                replay_mismatch_reason="no_private_traces_default_no_network",
            )
        _enforce_fd2a1_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real FD2-A1 replay.")
        return

    # Real replay path: requires openlocus binary + committed FD1 artifact.
    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(args.openlocus)
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "openlocus_binary_missing", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source, network_mode="local_explicit",
        )
        _enforce_fd2a1_no_forbidden(report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    private_trace_dir, private_trace_storage_class = _resolve_private_trace_dir(
        args.private_trace_dir
    )
    network_mode = "local_explicit"
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    try:
        report = _run_real_replay(
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            private_trace_dir=private_trace_dir,
            private_trace_storage_class=private_trace_storage_class,
            fd1_artifact_path=fd1_artifact_path,
            fd2a_artifact_path=fd2a_artifact_path,
            failure_category_counts=fcc,
        )
    except Exception:
        fcc["unexpected_exception"] = fcc.get("unexpected_exception", 0) + 1
        report = _build_unavailable_report(
            "unexpected_exception", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source, network_mode=network_mode,
            private_trace_storage_class=private_trace_storage_class,
            failure_category_counts=fcc,
        )

    if report.get("provider_calls_made") is not False:
        report["status"] = "fail_schema_contract"

    _enforce_fd2a1_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"records_attributed={report.get('records_attributed', 0)}, "
          f"records_regressed={report.get('records_regressed', 0)})")


if __name__ == "__main__":
    main()
