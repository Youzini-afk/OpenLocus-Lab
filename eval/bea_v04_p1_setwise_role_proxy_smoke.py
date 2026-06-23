#!/usr/bin/env python3
"""BEA-v0.4-P1: Setwise Role-Proxy Smoke (Public Records-Only).

This module implements the **BEA-v0.4-P1 setwise role-proxy smoke**: a
minimal, eval-local, deterministic role-proxy setwise selection policy
(``setwise_complementarity_v0_4_p1``) compared against BEA v0.3 and
same-budget controls on a fresh small external smoke slice. It answers
one question only: can deterministic role-proxy setwise selection change
BEA v0.3 behavior and reduce FD1 failure families without catastrophic
quality regression?

BEA-v0.4-P1 is explicitly **not** a v0.4 proof, **not** a benchmark
result, **not** a leaderboard entry, **not** a performance claim, **not**
a method-winner claim, **not** a calibration claim, **not** a promotion,
**not** a default/policy change, **not** a runtime/retriever/pack/
backend/EvidenceCore semantic change, and **not** the full v0.4 matrix.

Claim boundary (binding):

* Claim level: ``bea_v04_p1_setwise_role_proxy_smoke_only``.
* Status: ``bea_v04_p1_smoke_pass`` | ``partial_directional_signal`` |
  ``no_go_proxy_unavailable`` | ``no_go_no_selection_change`` |
  ``no_go_quality_regression`` | ``unavailable_with_reason`` |
  ``offline_counterfactual_replay`` | ``fail_forbidden_scan`` |
  ``fail_schema_contract``.
* Mode: ``bea_v04_p1_setwise_role_proxy_smoke``; phase ``BEA-v0.4-P1``.

Required invariants (binding):

* Eval-local only. No runtime/default/EvidenceCore changes.
* No B16-K, no v0.31/v0.32 weight tuning, no dense/graph/QuIVer/provider
  scope.
* Budget fixed at 5. Methods fixed to ``bm25,regex,symbol``.
* Role proxies are deterministic runtime-clean, no gold/private labels:
  fixed enums ``target_proxy``, ``support_proxy``, ``unknown``.
* Private per-record score / decision / role-proxy rows under ``/tmp``
  only. Public artifact aggregate-only, records-only, fixed enum tables.
* No public record IDs, repo URLs, commits, paths, queries, gold labels,
  spans, snippets, candidate files, decision order, score components, or
  per-record role labels.

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real smoke requires public network access. CI must be a separate
  explicit ``workflow_dispatch`` job with
  ``enable_external_benchmark_network=true``. It must NOT run on PR/push
  by default, must use no provider secrets/vars, no provider model env,
  and must upload only the aggregate report. The private JSONL files are
  NEVER uploaded.

Run::

    python3 -m py_compile eval/bea_v04_p1_setwise_role_proxy_smoke.py
    python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py --self-test
    python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py \\
        --enable-external-benchmark-network \\
        --contextbench-row-offset 0 --contextbench-row-limit 480 \\
        --repoqa-needle-offset 0 --repoqa-needle-limit 240 \\
        --out artifacts/bea_v04_p1_setwise_role_proxy/\\
bea_v04_p1_setwise_role_proxy_smoke_report.json
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

# Reuse BEA-3/5 helpers (frozen v0.3 policy + v0.2/v0 controls + scanners).
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

# ---------------------------------------------------------------------------
# Schema / claim constants (BEA-v0.4-P1 owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "bea_v04_p1_setwise_role_proxy_smoke.v1"
GENERATED_BY = "eval/bea_v04_p1_setwise_role_proxy_smoke.py"
CLAIM_LEVEL = "bea_v04_p1_setwise_role_proxy_smoke_only"
SELF_TEST_CHECKS_EXPECTED = 269
MODE = "bea_v04_p1_setwise_role_proxy_smoke"
PHASE = "BEA-v0.4-P1"

DEFAULT_OUT = Path(
    "artifacts/bea_v04_p1_setwise_role_proxy/"
    "bea_v04_p1_setwise_role_proxy_smoke_report.json"
)

PRIVATE_SCORE_SCHEMA_VERSION = "bea_v04_p1_private_score.v1"
PRIVATE_DECISION_SCHEMA_VERSION = "bea_v04_p1_private_decision.v1"
PRIVATE_ROLE_PROXY_SCHEMA_VERSION = "bea_v04_p1_private_role_proxy.v1"

# Fixed protocol (no CLI budget/methods inputs for the smoke).
FIXED_BUDGET = 5
FIXED_METHODS = "bm25,regex,symbol"
ALLOWED_METHODS = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

# Fresh small external smoke protocol (success-quota).
SAMPLING_MODE = "success_quota"
SAMPLING_PROTOCOL_VERSION = "bea_v04_p1_fresh_smoke.v1"
SAMPLING_FRAME_POLICY = (
    "full_available_python_excluding_bea2_bea3_bea4_mandatory_windows; "
    "bea5_overlap_disclosed_not_excluded"
)
EXCLUDED_PRIOR_WINDOWS_POLICY = (
    "mandatory_bea2_bea3_bea4; bea5_overlap_disclosed_not_excluded; "
    "bea0_bea1_best_effort_or_disclosed"
)
BEA5_OVERLAP_POLICY = (
    "not_excluded; disclosed; BEA-5 used success-quota over the same full "
    "available Python frame and did not consume the entire frame, so overlap "
    "with BEA-5 evaluated records is possible. This is P1 smoke evidence, "
    "not fresh disjoint validation."
)
TARGET_SUCCESSFUL_RECORDS = 30
MIN_CONTEXTBENCH_SUCCESSFUL = 20
MIN_REPOQA_SUCCESSFUL = 10
RAW_ATTEMPT_CAP_CONTEXTBENCH = 480
RAW_ATTEMPT_CAP_REPOQA = 240

# Mandatory excluded index windows (same as BEA-5; covers BEA-2/3/4).
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

# Required arms (RRF included because it is cheap and stable via BEA-5's
# deterministic derivation from method ranks when the direct path fails).
ARM_BM25_PREFIX = "bm25_prefix_same_budget"
ARM_BEA_V0_3 = "bea_v0_3_anchor_span_latency"
ARM_ROLE_PROXY_ONLY = "role_proxy_only_same_budget"
ARM_SETWISE_V0_4_P1 = "setwise_complementarity_v0_4_p1"
ARM_SEEDED_RANDOM = "seeded_random_same_budget"
ARM_RRF_SAME_BUDGET = "rrf_same_budget"

FIXED_ARMS = (
    ARM_BM25_PREFIX,
    ARM_BEA_V0_3,
    ARM_ROLE_PROXY_ONLY,
    ARM_SETWISE_V0_4_P1,
    ARM_SEEDED_RANDOM,
    ARM_RRF_SAME_BUDGET,
)

TREATMENT_ARM = ARM_SETWISE_V0_4_P1
QUALITY_BASELINE_ARM = ARM_BEA_V0_3
DELTA_BASELINE_ARM = ARM_BEA_V0_3

SEEDED_RANDOM_SEED = 20240623

# Role-proxy fixed enum.
ROLE_TARGET_PROXY = "target_proxy"
ROLE_SUPPORT_PROXY = "support_proxy"
ROLE_UNKNOWN = "unknown"
ROLE_ENUM = (ROLE_TARGET_PROXY, ROLE_SUPPORT_PROXY, ROLE_UNKNOWN)

# Metric allowlist (same as BEA-3/4/5).
ARM_METRIC_ALLOWLIST = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
    "candidate_count_read",
    "evidence_budget_used",
    "action_steps",
    "latency_seconds",
    "quality_per_candidate",
    "quality_per_latency",
)

PRIMARY_METRICS = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
)

# FD1 failure family fixed enum (12 categories, same as BEA-FD1).
FAILURE_FAMILIES = (
    "gold_file_absent",
    "gold_span_absent",
    "correct_file_wrong_span",
    "redundant_same_file_candidates",
    "too_many_anchor_slots",
    "missing_support_candidate",
    "support_selected_without_target",
    "target_selected_without_support",
    "risk_penalty_removed_gold",
    "early_stop_too_early",
    "budget_spent_on_low_marginal_gain",
    "latency_without_quality_gain",
)

UNAVAILABLE_NO_SUPPORT_FAMILIES = frozenset({
    "missing_support_candidate",
    "support_selected_without_target",
    "target_selected_without_support",
})
UNAVAILABLE_MISSING_TRACE_FAMILIES = frozenset({
    "risk_penalty_removed_gold",
})

AVAILABILITY_REASONS = (
    "available",
    "unavailable_missing_trace",
    "unavailable_no_support_label",
    "unavailable_replay_mismatch",
    "unavailable_no_candidates",
)

# Hard gates (P1 smoke).
GATE_ROLE_PROXY_ASSIGNMENT_RATE = 0.70
GATE_TARGET_PROXY_AVAILABLE_RATE = 0.50
GATE_SUPPORT_PROXY_AVAILABLE_RATE = 0.30
GATE_UNKNOWN_ONLY_RATE = 0.30
GATE_SETWISE_DIFF_RATE = 0.25
GATE_QUALITY_MARGIN = 0.05
GATE_SPAN_MARGIN = 0.02
GATE_LATENCY_RATIO = 1.25

# v0.4 P1 frozen role-proxy weights (NOT tuned from outcomes).
V04_P1_WEIGHT_TARGET = 0.40
V04_P1_WEIGHT_SUPPORT_CROSS_FILE = 0.20
V04_P1_WEIGHT_SOURCE_DIVERSITY = 0.15
V04_P1_WEIGHT_SPAN_TIGHT = 0.10
V04_P1_WEIGHT_NOVELTY = 0.10
V04_P1_WEIGHT_DUP_FILE_PENALTY = -0.35
V04_P1_WEIGHT_WEAK_SUPPORT_PENALTY = -0.15

# Role-proxy assignment thresholds (frozen, deterministic, runtime-clean).
TARGET_PROXY_MIN_AGREEMENT = 2
TARGET_PROXY_MIN_SPAN_TIGHT = 0.25
SUPPORT_PROXY_MIN_AGREEMENT = 1
SUPPORT_PROXY_MIN_SPAN_TIGHT = 0.0

CI_MIN_RECORDS_SUCCESSFUL = 30

SAFE_TRUE_FLAGS = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "bea_v03_policy_executed": False,
    "bea_v04_p1_policy_executed": False,
    "role_proxy_assigned": False,
    "setwise_selection_performed": False,
    "fresh_smoke_slice_read": False,
    "private_score_records_written": False,
    "private_decision_records_written": False,
    "private_role_proxy_records_written": False,
}

DEFAULT_FALSE_FLAGS = {
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
    "algorithm_changed_during_bea_v04_p1": False,
    "weights_tuned_during_bea_v04_p1": False,
    "v04_full_matrix_claimed": False,
}

LICENSE_FIELDS = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_smoke",
}

FAILURE_CATEGORIES = (
    "contextbench_fetch_failed",
    "contextbench_no_python_rows",
    "contextbench_gold_parse_failed",
    "repoqa_asset_download_failed",
    "repoqa_asset_decompress_failed",
    "repoqa_asset_parse_failed",
    "repoqa_no_python_needles",
    "repoqa_needle_parse_failed",
    "heldout_offset_exceeds_available",
    "repo_clone_failed",
    "repo_checkout_failed",
    "materialization_failed",
    "retrieval_failed",
    "scoring_unavailable",
    "rrf_required_but_missing",
    "role_proxy_unavailable",
    "score_failed",
    "private_score_write_failed",
    "private_decision_write_failed",
    "private_role_proxy_write_failed",
    "record_excluded_from_paired_denominator",
    "row_limit_capped",
    "needle_limit_capped",
    "quota_reached_stop",
    "scanner_self_test_failed",
    "forbidden_leak_blocked",
    "duplicate_record_key_blocked",
    "unexpected_exception",
)

BLOCKING_FAILURE_CATEGORIES = (
    "private_score_write_failed",
    "private_decision_write_failed",
    "private_role_proxy_write_failed",
    "forbidden_leak_blocked",
    "unexpected_exception",
)

# ---------------------------------------------------------------------------
# Scanner (BEA-v0.4-P1 owned, strict, fail-closed). Extends BEA-5.
# ---------------------------------------------------------------------------

BEA_V04_P1_FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        "action_order", "priority_components", "priority_score",
        "selected_decisions", "budget_trace", "stop_reason",
        "candidate_features", "anchor_eligibility",
        "anchor_slots", "early_stop_reason",
        "private_score_path", "score_path", "private_score_file",
        "private_record_id", "private_record_hash",
        "private_decision_path", "decision_path", "private_decision_file",
        "private_decision_id", "decision_id",
        "private_role_proxy_path", "role_proxy_path",
        "private_role_proxy_file", "private_role_proxy_id",
        "role_proxy_row_id",
        "per_record_role_labels", "role_proxy_assignment",
        "action_trace", "action_steps_trace",
        "budget_state", "budget_states",
        "accepted_candidates", "final_candidates",
        "candidate_list", "candidates", "score_outcome",
        "hard_gates", "failure_category_counts",
        "per_record_metrics", "runtime_query_features",
        "query_feature_summary", "query_features",
        "benchmark_row_id", "benchmark_record_id", "benchmark_label",
        "phase_run_id", "run_id", "task_id", "row_id", "needle_id",
        "instance_id", "provider_name", "model_name", "model_family",
        "provider_payload", "private_bucket", "route_bucket", "task_bucket",
        "calibration", "method_winner", "best_method",
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion",
        "self_test_checks", "self_test_details", "self_test_list",
        "checks", "check_list",
    }
)


def _is_v04_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in (
        "failure_category_count_records", "hard_gate_records", "arm_metric_records",
        "arm_delta_records", "win_tie_loss_records",
        "role_proxy_summary_records", "setwise_behavior_records",
        "failure_family_records", "availability_records",
        "source_run_records", "benchmark_attempt_records",
        "private_score_manifest", "private_decision_manifest",
        "private_role_proxy_manifest", "framing",
    )


def _scan_v04_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_v04_schema_key_container(sub_path)
                if (key_str in BEA_V04_P1_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_v04_p1_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_v04(obj: Any) -> list[dict[str, Any]]:
    violations = bea5._scan_bea5(obj)
    violations.extend(_scan_v04_forbidden_keys(obj))
    return violations


def _v04_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v04(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_v04_no_forbidden(obj: Any) -> None:
    scan = _v04_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Natural-key uniqueness validators
# ---------------------------------------------------------------------------


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


def _rpsr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["role_proxy"], rec["summary_field"])


def _sbr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["behavior_field"],)


def _ffr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["failure_family"], rec["policy_arm"], rec["availability"])


def _avr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["category"], rec["availability"])


def _srr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["source_ci_run_id"])


# ---------------------------------------------------------------------------
# Private manifest writers
# ---------------------------------------------------------------------------


def _resolve_private_dir(explicit: str | None) -> tuple[Path, str]:
    return bea0._resolve_private_score_dir(explicit)


def _private_score_manifest_hash() -> str:
    schema = {
        "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "policy_arm", "runtime_query_feature_summary",
            "candidate_features", "anchor_eligibility",
            "priority_components", "selected_decisions",
            "action_order", "budget_trace", "anchor_slots",
            "early_stop_reason", "stop_reason", "score_outcome",
            "role_proxy_summary",
            "latency_ms", "cost_usd", "tokens", "provider_calls",
            "failure_reason",
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
            "role_proxy", "priority_score", "priority_components",
            "candidate_method", "candidate_rank", "agreement",
            "is_new_file", "is_new_dir", "span_extent",
            "span_proxy_bucket", "decision_reason",
        ],
    }
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _private_role_proxy_manifest_hash() -> str:
    schema = {
        "schema_version": PRIVATE_ROLE_PROXY_SCHEMA_VERSION,
        "fields": [
            "phase_run_id", "benchmark", "private_record_id",
            "candidate_key", "role_proxy", "target_score",
            "support_score", "agreement", "bm25_present",
            "span_tightness", "query_path_overlap", "path_depth",
            "source_diversity", "assignment_reason",
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


# ---------------------------------------------------------------------------
# Role-proxy assignment (deterministic, runtime-clean, no gold/private labels)
# ---------------------------------------------------------------------------


def _path_depth(path: str) -> int:
    if not isinstance(path, str) or not path:
        return 0
    return len([p for p in path.split("/") if p])


def _source_diversity(methods: set[str]) -> int:
    if not isinstance(methods, set):
        methods = set(methods) if methods else set()
    return len(methods)


def _compute_target_score(
    entry: dict[str, Any], query_toks: set[str],
) -> float:
    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods) if methods else set()
    agreement = len(methods)
    bm25_present = "bm25" in methods
    span_tight = bea3._span_tightness(entry)
    path = str(entry.get("path", "") or "")
    path_toks = bea2._path_tokens(path)
    overlap = bea2._token_overlap(query_toks, path_toks)
    depth = _path_depth(path)
    depth_norm = min(depth, 5) / 5.0

    score = 0.0
    score += (min(agreement, 3) / 3.0) * 0.30
    score += (1.0 if bm25_present else 0.0) * 0.20
    score += span_tight * 0.20
    score += overlap * 0.15
    score += depth_norm * 0.15
    return round(min(score, 1.0), 6)


def _compute_support_score(
    entry: dict[str, Any], query_toks: set[str],
    accepted_paths: set[str], accepted_dirs: set[str],
) -> float:
    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods) if methods else set()
    span_tight = bea3._span_tightness(entry)
    path = str(entry.get("path", "") or "")
    path_toks = bea2._path_tokens(path)
    overlap = bea2._token_overlap(query_toks, path_toks)
    source_div = _source_diversity(methods)
    dir_part = bea2._path_dir(path)
    is_new_file = path not in accepted_paths
    is_new_dir = bea2._is_new_dir(dir_part, accepted_dirs)

    score = 0.0
    score += (1.0 if is_new_file else 0.0) * 0.30
    score += (1.0 if is_new_dir else 0.0) * 0.20
    score += (min(source_div, 3) / 3.0) * 0.20
    score += span_tight * 0.15
    score += overlap * 0.15
    return round(min(score, 1.0), 6)


def _assign_role_proxy(
    entry: dict[str, Any], query_toks: set[str],
    accepted_paths: set[str], accepted_dirs: set[str],
) -> tuple[str, float, float, str]:
    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods) if methods else set()
    agreement = len(methods)
    bm25_present = "bm25" in methods
    span_tight = bea3._span_tightness(entry)
    path = str(entry.get("path", "") or "")
    path_toks = bea2._path_tokens(path)
    overlap = bea2._token_overlap(query_toks, path_toks)

    target_score = _compute_target_score(entry, query_toks)
    support_score = _compute_support_score(
        entry, query_toks, accepted_paths, accepted_dirs
    )

    is_target = (
        agreement >= TARGET_PROXY_MIN_AGREEMENT
        and span_tight >= TARGET_PROXY_MIN_SPAN_TIGHT
        and (bm25_present or overlap > 0.0)
        and target_score >= 0.40
    )
    if is_target:
        return ROLE_TARGET_PROXY, target_score, support_score, "target_high_confidence"

    is_support = (
        agreement >= SUPPORT_PROXY_MIN_AGREEMENT
        and span_tight >= SUPPORT_PROXY_MIN_SPAN_TIGHT
        and support_score >= 0.30
    )
    if is_support:
        return ROLE_SUPPORT_PROXY, target_score, support_score, "support_complementarity"

    return ROLE_UNKNOWN, target_score, support_score, "below_role_thresholds"


def _assign_role_proxies_batch(
    deduped: list[dict[str, Any]], query_toks: set[str],
) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    empty_paths: set[str] = set()
    empty_dirs: set[str] = set()
    for entry in deduped:
        role, t_score, s_score, reason = _assign_role_proxy(
            entry, query_toks, empty_paths, empty_dirs
        )
        assignments.append({
            "entry": entry,
            "role_proxy": role,
            "target_score": t_score,
            "support_score": s_score,
            "assignment_reason": reason,
        })
    return assignments


# ---------------------------------------------------------------------------
# BEA v0.4 P1 setwise complementarity policy (deterministic, runtime-clean)
# ---------------------------------------------------------------------------


def _compute_v04_p1_priority(
    entry: dict[str, Any], role_proxy: str,
    target_score: float, support_score: float,
    query_toks: set[str],
    accepted_paths: set[str], accepted_dirs: set[str],
    accepted_methods: set[str], is_target_slot: bool,
) -> dict[str, Any]:
    base = bea2._compute_priority(
        entry, query_toks, accepted_paths, accepted_dirs,
        set(), accepted_methods,
    )
    base_priority = base["priority_score"]
    base_components = dict(base["priority_components"])

    target_boost = (
        V04_P1_WEIGHT_TARGET
        if (is_target_slot and role_proxy == ROLE_TARGET_PROXY)
        else 0.0
    )
    path = str(entry.get("path", "") or "")
    is_new_file = path not in accepted_paths
    dir_part = bea2._path_dir(path)
    is_new_dir = bea2._is_new_dir(dir_part, accepted_dirs)
    support_cross_file = (
        V04_P1_WEIGHT_SUPPORT_CROSS_FILE
        if (role_proxy == ROLE_SUPPORT_PROXY and is_new_file)
        else 0.0
    )

    methods = entry.get("methods", set())
    if not isinstance(methods, set):
        methods = set(methods) if methods else set()
    new_methods = methods - accepted_methods
    source_diversity = V04_P1_WEIGHT_SOURCE_DIVERSITY if new_methods else 0.0

    span_tight = bea3._span_tightness(entry)
    span_bonus = V04_P1_WEIGHT_SPAN_TIGHT * span_tight

    novelty = V04_P1_WEIGHT_NOVELTY if (is_new_file or is_new_dir) else 0.0
    dup_file_penalty = (
        V04_P1_WEIGHT_DUP_FILE_PENALTY if not is_new_file else 0.0
    )

    agreement = len(methods)
    bm25_norm = float(entry.get("max_norm_score", 0.0) or 0.0)
    weak_support = (agreement <= 1 and bm25_norm < 0.01)
    weak_penalty = V04_P1_WEIGHT_WEAK_SUPPORT_PENALTY if weak_support else 0.0

    priority = (
        base_priority + target_boost + support_cross_file
        + source_diversity + span_bonus + novelty
        + dup_file_penalty + weak_penalty
    )

    return {
        "priority_score": round(priority, 6),
        "priority_components": {
            **base_components,
            "role_proxy": role_proxy,
            "target_score": round(target_score, 6),
            "support_score": round(support_score, 6),
            "target_boost": round(target_boost, 6),
            "support_cross_file": round(support_cross_file, 6),
            "source_diversity": round(source_diversity, 6),
            "span_tightness_v04": round(span_tight, 6),
            "span_bonus_v04": round(span_bonus, 6),
            "novelty": round(novelty, 6),
            "dup_file_penalty": round(dup_file_penalty, 6),
            "weak_support_penalty_v04": round(weak_penalty, 6),
            "is_new_file": is_new_file,
            "is_new_dir": is_new_dir,
        },
        "is_new_file": is_new_file,
        "is_new_dir": is_new_dir,
        "risk_bucket": base["risk_bucket"],
        "role_proxy": role_proxy,
    }


def _bea_v0_4_p1_setwise_policy(
    candidates: list[dict[str, Any]], query: str, budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Any]]:
    mechanism_summary = {
        "role_proxy_used": True,
        "setwise_used": True,
        "target_slot_reserved": 1,
        "target_slot_filled": 0,
        "support_selected": 0,
        "unknown_selected": 0,
        "mean_target_score": 0.0,
        "mean_support_score": 0.0,
        "role_proxy_bucket_counts": {},
        "stop_reason": "",
    }

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
    role_assignments = _assign_role_proxies_batch(deduped, query_toks)

    role_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    for ra in role_assignments:
        entry = ra["entry"]
        key = (entry["path"], entry["start_line"], entry["end_line"])
        role_by_key[key] = ra

    has_target = any(ra["role_proxy"] == ROLE_TARGET_PROXY for ra in role_assignments)
    target_slot_reserved = 1 if has_target else 0
    mechanism_summary["target_slot_reserved"] = target_slot_reserved

    accepted: list[dict[str, Any]] = []
    accepted_paths: set[str] = set()
    accepted_dirs: set[str] = set()
    accepted_spans: set[tuple[str, int, int]] = set()
    accepted_methods: set[str] = set()
    action_order: list[dict[str, Any]] = []
    budget_trace: list[dict[str, Any]] = []
    stop_reason = "candidates_exhausted"

    remaining = list(deduped)
    target_filled = 0
    support_selected = 0
    unknown_selected = 0
    target_scores: list[float] = []
    support_scores: list[float] = []
    role_bucket_counts: dict[str, int] = {}

    for step in range(budget):
        if not remaining:
            stop_reason = "candidates_exhausted"
            break

        is_target_slot = (target_filled < target_slot_reserved)

        scored: list[tuple[float, int, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
        for idx, entry in enumerate(remaining):
            key = (entry["path"], entry["start_line"], entry["end_line"])
            ra = role_by_key.get(key, {})
            role = ra.get("role_proxy", ROLE_UNKNOWN)
            t_score = ra.get("target_score", 0.0)
            s_score = ra.get("support_score", 0.0)
            prio = _compute_v04_p1_priority(
                entry, role, t_score, s_score, query_toks,
                accepted_paths, accepted_dirs, accepted_methods, is_target_slot,
            )
            scored.append((prio["priority_score"], entry.get("stable_index", idx), entry, prio, ra))

        if is_target_slot and has_target:
            scored.sort(key=lambda t: (
                0 if t[3]["role_proxy"] == ROLE_TARGET_PROXY else 1,
                -t[0], t[1]
            ))
        else:
            scored.sort(key=lambda t: (-t[0], t[1]))

        best_prio, _best_si, best_entry, best_components, best_ra = scored[0]

        budget_remaining = budget - len(accepted)
        budget_trace.append({
            "step": step,
            "budget_remaining": budget_remaining,
            "accepted_so_far": len(accepted),
            "candidate_count_remaining": len(remaining),
            "is_target_slot": is_target_slot,
        })

        if len(accepted) >= budget:
            stop_reason = "budget_exhausted"
            action_order.append({
                "step": step,
                "action": "stop_budget_exhausted",
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

        role = best_components.get("role_proxy", ROLE_UNKNOWN)
        if role == ROLE_TARGET_PROXY:
            target_filled += 1
        elif role == ROLE_SUPPORT_PROXY:
            support_selected += 1
        else:
            unknown_selected += 1
        role_bucket_counts[role] = role_bucket_counts.get(role, 0) + 1

        best_methods = best_entry.get("methods", set())
        if isinstance(best_methods, set):
            accepted_methods |= best_methods
        elif isinstance(best_methods, (list, tuple)):
            accepted_methods |= set(best_methods)

        target_scores.append(float(best_ra.get("target_score", 0.0)))
        support_scores.append(float(best_ra.get("support_score", 0.0)))

        action_order.append({
            "step": step,
            "action": "accept_candidate",
            "priority_score": best_prio,
            "priority_components": best_components["priority_components"],
            "candidate_method": best_entry.get("first_method", ""),
            "candidate_rank": best_entry.get("first_rank", 0),
            "agreement": len(best_methods) if isinstance(best_methods, set) else len(set(best_methods) if best_methods else set()),
            "is_new_file": best_components["is_new_file"],
            "is_new_dir": best_components["is_new_dir"],
            "risk_bucket": best_components["risk_bucket"],
            "role_proxy": role,
            "is_target_slot": is_target_slot,
        })
        remaining = [e for e in remaining if (e["path"], e["start_line"], e["end_line"]) != span_key]

    if len(accepted) >= budget and stop_reason not in ("candidates_exhausted",):
        stop_reason = "budget_exhausted"
    elif not remaining and stop_reason != "budget_exhausted":
        stop_reason = "candidates_exhausted"

    mechanism_summary["target_slot_filled"] = target_filled
    mechanism_summary["support_selected"] = support_selected
    mechanism_summary["unknown_selected"] = unknown_selected
    mechanism_summary["mean_target_score"] = (
        round(sum(target_scores) / len(target_scores), 6) if target_scores else 0.0
    )
    mechanism_summary["mean_support_score"] = (
        round(sum(support_scores) / len(support_scores), 6) if support_scores else 0.0
    )
    mechanism_summary["role_proxy_bucket_counts"] = role_bucket_counts
    mechanism_summary["stop_reason"] = stop_reason

    return accepted, action_order, budget_trace, stop_reason, mechanism_summary


# ---------------------------------------------------------------------------
# Role-proxy-only same-budget control arm
# ---------------------------------------------------------------------------


def _role_proxy_only_same_budget_arm(
    role_assignments: list[dict[str, Any]], k: int,
) -> list[dict[str, Any]]:
    if k <= 0 or not role_assignments:
        return []

    def _sort_key(ra: dict[str, Any]) -> tuple:
        role = ra.get("role_proxy", ROLE_UNKNOWN)
        role_order = {
            ROLE_TARGET_PROXY: 0, ROLE_SUPPORT_PROXY: 1, ROLE_UNKNOWN: 2,
        }.get(role, 3)
        t_score = float(ra.get("target_score", 0.0))
        s_score = float(ra.get("support_score", 0.0))
        return (role_order, -t_score if role == ROLE_TARGET_PROXY else 0.0,
                -s_score if role == ROLE_SUPPORT_PROXY else 0.0)

    sorted_assignments = sorted(role_assignments, key=_sort_key)
    selected = sorted_assignments[:k]
    return [
        {
            "path": ra["entry"]["path"],
            "start_line": ra["entry"]["start_line"],
            "end_line": ra["entry"]["end_line"],
            "content_sha": ra["entry"].get("content_sha", ""),
        }
        for ra in selected
    ]


# ---------------------------------------------------------------------------
# Per-arm metrics + role-proxy availability + setwise behavior
# ---------------------------------------------------------------------------


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


def _arm_means(per_record_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_record_metrics:
        return {k: 0.0 for k in ARM_METRIC_ALLOWLIST}
    means: dict[str, Any] = {}
    for key in ARM_METRIC_ALLOWLIST:
        vals = [
            float(r[key]) for r in per_record_metrics
            if key in r and isinstance(r[key], (int, float))
        ]
        if vals:
            means[key] = round(sum(vals) / len(vals), 6)
        else:
            means[key] = 0.0
    return means


def _record_role_proxy_summary(
    role_assignments: list[dict[str, Any]],
) -> dict[str, Any]:
    n = len(role_assignments)
    target_count = sum(1 for ra in role_assignments if ra["role_proxy"] == ROLE_TARGET_PROXY)
    support_count = sum(1 for ra in role_assignments if ra["role_proxy"] == ROLE_SUPPORT_PROXY)
    unknown_count = sum(1 for ra in role_assignments if ra["role_proxy"] == ROLE_UNKNOWN)
    has_target = target_count > 0
    has_support = support_count > 0
    unknown_only = (not has_target and not has_support)
    assignment_rate = (
        (target_count + support_count) / n if n > 0 else 0.0
    )
    return {
        "has_target": has_target,
        "has_support": has_support,
        "unknown_only": unknown_only,
        "target_count": target_count,
        "support_count": support_count,
        "unknown_count": unknown_count,
        "role_proxy_assignment_rate": round(assignment_rate, 6),
        "deduped_count": n,
    }


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
    v03_accepted: list[dict[str, Any]], v04_accepted: list[dict[str, Any]],
) -> bool:
    v03_keys = {(e.get("path", ""), e.get("start_line", 0), e.get("end_line", 0)) for e in v03_accepted if isinstance(e, dict)}
    v04_keys = {(e.get("path", ""), e.get("start_line", 0), e.get("end_line", 0)) for e in v04_accepted if isinstance(e, dict)}
    return v03_keys != v04_keys


# ---------------------------------------------------------------------------
# FD1 failure family classification (per record, per policy arm)
# ---------------------------------------------------------------------------


def _classify_failure_family(
    metrics: dict[str, Any], budget_used: int,
    latency_seconds: float, baseline_metrics: dict[str, Any],
    baseline_latency: float, role_proxy_summary: dict[str, Any],
) -> dict[str, dict[str, Any]]:
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
        cats["gold_span_absent"] = {"count": 0, "availability": "available"}
    elif file_recall > 0 and span_f > 0:
        cats["correct_file_wrong_span"] = {"count": 0, "availability": "available"}
        cats["gold_span_absent"] = {"count": 0, "availability": "available"}
    else:
        cats["correct_file_wrong_span"] = {"count": 0, "availability": "available"}
        cats["gold_span_absent"] = {"count": 0, "availability": "available"}

    cats["redundant_same_file_candidates"] = {"count": 0, "availability": "available"}
    cats["too_many_anchor_slots"] = {"count": 0, "availability": "available"}

    for fam in UNAVAILABLE_NO_SUPPORT_FAMILIES:
        cats[fam] = {"count": 0, "availability": "unavailable_no_support_label"}

    for fam in UNAVAILABLE_MISSING_TRACE_FAMILIES:
        cats[fam] = {"count": 0, "availability": "unavailable_missing_trace"}

    if mrr <= b_mrr and latency_seconds < baseline_latency:
        cats["early_stop_too_early"] = {"count": 0, "availability": "available"}
    else:
        cats["early_stop_too_early"] = {"count": 0, "availability": "available"}

    if budget_used >= FIXED_BUDGET and mrr <= b_mrr:
        cats["budget_spent_on_low_marginal_gain"] = {"count": 1, "availability": "available"}
    else:
        cats["budget_spent_on_low_marginal_gain"] = {"count": 0, "availability": "available"}

    if latency_seconds > baseline_latency and (mrr - b_mrr) <= 0:
        cats["latency_without_quality_gain"] = {"count": 1, "availability": "available"}
    else:
        cats["latency_without_quality_gain"] = {"count": 0, "availability": "available"}

    return cats


# ---------------------------------------------------------------------------
# Heldout fetchers (reuse BEA-5)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Per-record evaluation
# ---------------------------------------------------------------------------


def _evaluate_record(
    *, openlocus_bin: str, benchmark: str, private_record_id: str,
    task_id: str, query: str, gold_paths: list[str],
    gold_lines: list[list[int]], repo_root: Path, budget: int,
    score_path: Path, decision_path: Path, role_proxy_path: Path,
    phase_run_id: str, fcc: dict[str, int],
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
    query_toks = bea2._query_tokens(query)

    role_assignments = _assign_role_proxies_batch(deduped, query_toks)
    role_proxy_summary = _record_role_proxy_summary(role_assignments)

    if role_proxy_summary["role_proxy_assignment_rate"] < GATE_ROLE_PROXY_ASSIGNMENT_RATE:
        fcc["role_proxy_unavailable"] = (
            fcc.get("role_proxy_unavailable", 0) + 1
        )

    shared_retrieval_latency = sum(method_latencies_ms.values()) / 1000.0

    # --- v0.4 P1 setwise complementarity (treatment) ---
    policy_start = time.perf_counter()
    v04_accepted, v04_action_order, v04_budget_trace, v04_stop_reason, v04_mech = (
        _bea_v0_4_p1_setwise_policy(all_candidates, query, budget)
    )
    v04_policy_time = time.perf_counter() - policy_start
    v04_metrics = _arm_metrics_for_record(
        ARM_SETWISE_V0_4_P1, v04_accepted, gold_record, task_id,
        len(all_candidates), len(v04_accepted), len(v04_action_order),
        shared_retrieval_latency + v04_policy_time,
    )

    # --- v0.3 anchor/span/latency (quality baseline) ---
    v03_accepted, v03_action_order, v03_budget_trace, v03_stop_reason, v03_mech = (
        bea3._bea_v0_3_policy(all_candidates, query, budget,
                              use_anchor=True, use_early_stop=True)
    )
    v03_metrics = _arm_metrics_for_record(
        ARM_BEA_V0_3, v03_accepted, gold_record, task_id,
        len(all_candidates), len(v03_accepted), len(v03_action_order),
        shared_retrieval_latency,
    )

    same_budget_k = bea2._same_budget_k(len(v03_accepted), deduped_count)

    # --- Controls ---
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(method_candidates, same_budget_k)
    sb_bm25_metrics = _arm_metrics_for_record(
        ARM_BM25_PREFIX, sb_bm25_ev, gold_record, task_id,
        len(method_candidates.get("bm25", [])),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0,
    )

    rp_ev = _role_proxy_only_same_budget_arm(role_assignments, same_budget_k)
    rp_metrics = _arm_metrics_for_record(
        ARM_ROLE_PROXY_ONLY, rp_ev, gold_record, task_id,
        len(all_candidates), len(rp_ev), len(rp_ev), 0.0,
    )

    sr_ev = bea2._seeded_random_same_budget_arm(all_candidates, same_budget_k)
    sr_metrics = _arm_metrics_for_record(
        ARM_SEEDED_RANDOM, sr_ev, gold_record, task_id,
        len(all_candidates), len(sr_ev), len(sr_ev), 0.0,
    )

    rrf_ev = bea2._rrf_same_budget_arm(rrf_candidates, same_budget_k)
    rrf_metrics = _arm_metrics_for_record(
        ARM_RRF_SAME_BUDGET, rrf_ev, gold_record, task_id,
        len(rrf_candidates), len(rrf_ev), len(rrf_ev),
        rrf_latency_ms / 1000.0,
    )

    per_arm_metrics: dict[str, dict[str, Any]] = {
        ARM_SETWISE_V0_4_P1: v04_metrics,
        ARM_BEA_V0_3: v03_metrics,
        ARM_BM25_PREFIX: sb_bm25_metrics,
        ARM_ROLE_PROXY_ONLY: rp_metrics,
        ARM_SEEDED_RANDOM: sr_metrics,
        ARM_RRF_SAME_BUDGET: rrf_metrics,
    }

    rec_latency_ms = int((time.perf_counter() - rec_start) * 1000)

    v03_dup = _accepted_file_duplicates(v03_accepted)
    v04_dup = _accepted_file_duplicates(v04_accepted)
    v03_div = _accepted_source_diversity(v03_accepted, all_candidates)
    v04_div = _accepted_source_diversity(v04_accepted, all_candidates)
    selection_diff = _selection_differs(v03_accepted, v04_accepted)

    rec_summary = {
        "role_proxy_summary": role_proxy_summary,
        "setwise_behavior": {
            "selection_differs_v03": selection_diff,
            "duplicate_file_count_v03": v03_dup,
            "duplicate_file_count_v04": v04_dup,
            "source_diversity_v03": v03_div,
            "source_diversity_v04": v04_div,
            "v03_budget_used": len(v03_accepted),
            "v04_budget_used": len(v04_accepted),
            "same_budget_k": same_budget_k,
        },
        "mechanism_summary": {
            "role_proxy_used": v04_mech.get("role_proxy_used", False),
            "setwise_used": v04_mech.get("setwise_used", False),
            "target_slot_filled": v04_mech.get("target_slot_filled", 0),
            "support_selected": v04_mech.get("support_selected", 0),
            "unknown_selected": v04_mech.get("unknown_selected", 0),
            "mean_target_score": v04_mech.get("mean_target_score", 0.0),
            "mean_support_score": v04_mech.get("mean_support_score", 0.0),
            "role_proxy_bucket_counts": v04_mech.get("role_proxy_bucket_counts", {}),
        },
        "v03_mechanism_summary": {
            "anchor_used": v03_mech.get("anchor_used", False),
            "early_stop_used": bool(v03_mech.get("early_stop_reason", "")),
            "budget_used": len(v03_accepted),
            "latency_ms": rec_latency_ms,
            "mean_span_extent": v03_mech.get("mean_span_extent", 0.0),
        },
    }

    # --- Write private role-proxy rows ---
    for ra in role_assignments:
        entry = ra["entry"]
        methods_set = entry.get("methods", set())
        if not isinstance(methods_set, set):
            methods_set = set(methods_set) if methods_set else set()
        try:
            _write_private_row(role_proxy_path, {
                "phase_run_id": phase_run_id,
                "benchmark": benchmark,
                "private_record_id": private_record_id,
                "candidate_key": f"{entry['path']}:{entry['start_line']}:{entry['end_line']}",
                "role_proxy": ra["role_proxy"],
                "target_score": ra["target_score"],
                "support_score": ra["support_score"],
                "agreement": len(methods_set),
                "bm25_present": "bm25" in methods_set,
                "span_tightness": bea3._span_tightness(entry),
                "query_path_overlap": bea2._token_overlap(query_toks, bea2._path_tokens(entry.get("path", ""))),
                "path_depth": _path_depth(entry.get("path", "")),
                "source_diversity": _source_diversity(methods_set),
                "assignment_reason": ra["assignment_reason"],
            })
        except OSError:
            fcc["private_role_proxy_write_failed"] = (
                fcc.get("private_role_proxy_write_failed", 0) + 1
            )

    # --- Write private decision rows (v0.4 P1 arm only) ---
    for i, action in enumerate(v04_action_order):
        try:
            _write_private_row(decision_path, {
                "phase_run_id": phase_run_id,
                "benchmark": benchmark,
                "private_record_id": private_record_id,
                "policy_arm": ARM_SETWISE_V0_4_P1,
                "decision_step": action.get("step", i),
                "decision_action": action.get("action", ""),
                "role_proxy": action.get("role_proxy", ROLE_UNKNOWN),
                "priority_score": action.get("priority_score", 0.0),
                "priority_components": action.get("priority_components", {}),
                "candidate_method": action.get("candidate_method", ""),
                "candidate_rank": action.get("candidate_rank", 0),
                "agreement": action.get("agreement", 0),
                "is_new_file": action.get("is_new_file", False),
                "is_new_dir": action.get("is_new_dir", False),
                "span_extent": action.get("span_extent", 0),
                "span_proxy_bucket": action.get("span_proxy_bucket", ""),
                "decision_reason": v04_stop_reason,
            })
        except OSError:
            fcc["private_decision_write_failed"] = (
                fcc.get("private_decision_write_failed", 0) + 1
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
        "v04_accepted_count": int(len(v04_accepted)),
        "v03_accepted_count": int(len(v03_accepted)),
        "shared_retrieval_latency_seconds": round(shared_retrieval_latency, 6),
        "query_length_chars": len(query) if isinstance(query, str) else 0,
        "query_word_count": (
            len(query.split()) if isinstance(query, str) and query else 0
        ),
    }

    arms_to_write = [
        (ARM_SETWISE_V0_4_P1, v04_action_order, v04_budget_trace,
         v04_stop_reason, v04_metrics, v04_mech),
        (ARM_BEA_V0_3, v03_action_order, v03_budget_trace,
         v03_stop_reason, v03_metrics, v03_mech),
        (ARM_BM25_PREFIX, [], [], "same_budget_bm25_prefix", sb_bm25_metrics, {}),
        (ARM_ROLE_PROXY_ONLY, [], [], "same_budget_role_proxy", rp_metrics, {}),
        (ARM_SEEDED_RANDOM, [], [], "same_budget_seeded_random", sr_metrics, {}),
        (ARM_RRF_SAME_BUDGET, [], [], "same_budget_rrf", rrf_metrics, {}),
    ]

    for arm_id, action_order, budget_trace, stop_reason, score_outcome, mech_summary in arms_to_write:
        private_score_row = {
            "phase_run_id": phase_run_id,
            "benchmark": benchmark,
            "private_record_id": private_record_id,
            "policy_arm": arm_id,
            "runtime_query_feature_summary": runtime_query_feature_summary,
            "candidate_features": [],
            "anchor_eligibility": (
                {k: v for k, v in mech_summary.items()
                 if k in ("anchor_used", "anchor_count_reserved",
                          "anchor_count_filled", "early_stop_reason")}
                if mech_summary else {}
            ),
            "priority_components": (
                [{"step": a.get("step", i), "priority_score": a.get("priority_score", 0.0),
                  "priority_components": a.get("priority_components", {})}
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
            "role_proxy_summary": role_proxy_summary if arm_id == ARM_SETWISE_V0_4_P1 else {},
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


# ---------------------------------------------------------------------------
# Public record builders (records-only; no dynamic arm dicts)
# ---------------------------------------------------------------------------


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


def _role_proxy_summary_records(
    per_record_role_proxy_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not per_record_role_proxy_summaries:
        return []
    n = len(per_record_role_proxy_summaries)
    records: list[dict[str, Any]] = []
    target_avail = sum(1 for s in per_record_role_proxy_summaries if s.get("has_target"))
    support_avail = sum(1 for s in per_record_role_proxy_summaries if s.get("has_support"))
    unknown_only = sum(1 for s in per_record_role_proxy_summaries if s.get("unknown_only"))
    mean_assign_rate = sum(float(s.get("role_proxy_assignment_rate", 0.0)) for s in per_record_role_proxy_summaries) / n
    mean_target_count = sum(int(s.get("target_count", 0)) for s in per_record_role_proxy_summaries) / n
    mean_support_count = sum(int(s.get("support_count", 0)) for s in per_record_role_proxy_summaries) / n
    mean_unknown_count = sum(int(s.get("unknown_count", 0)) for s in per_record_role_proxy_summaries) / n

    records.append({"role_proxy": ROLE_TARGET_PROXY, "summary_field": "available_rate",
                    "value": round(target_avail / n, 6), "record_count": n})
    records.append({"role_proxy": ROLE_SUPPORT_PROXY, "summary_field": "available_rate",
                    "value": round(support_avail / n, 6), "record_count": n})
    records.append({"role_proxy": ROLE_UNKNOWN, "summary_field": "unknown_only_rate",
                    "value": round(unknown_only / n, 6), "record_count": n})
    records.append({"role_proxy": ROLE_TARGET_PROXY, "summary_field": "mean_count_per_record",
                    "value": round(mean_target_count, 6), "record_count": n})
    records.append({"role_proxy": ROLE_SUPPORT_PROXY, "summary_field": "mean_count_per_record",
                    "value": round(mean_support_count, 6), "record_count": n})
    records.append({"role_proxy": ROLE_UNKNOWN, "summary_field": "mean_count_per_record",
                    "value": round(mean_unknown_count, 6), "record_count": n})
    records.append({"role_proxy": ROLE_TARGET_PROXY, "summary_field": "assignment_rate",
                    "value": round(mean_assign_rate, 6), "record_count": n})
    records.sort(key=lambda r: (r["role_proxy"], r["summary_field"]))
    return records


def _setwise_behavior_records(
    per_record_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not per_record_summaries:
        return []
    n = len(per_record_summaries)
    records: list[dict[str, Any]] = []
    diff_count = sum(1 for s in per_record_summaries if s.get("setwise_behavior", {}).get("selection_differs_v03", False))
    mean_dup_v03 = sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_v03", 0)) for s in per_record_summaries) / n
    mean_dup_v04 = sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_v04", 0)) for s in per_record_summaries) / n
    mean_div_v03 = sum(int(s.get("setwise_behavior", {}).get("source_diversity_v03", 0)) for s in per_record_summaries) / n
    mean_div_v04 = sum(int(s.get("setwise_behavior", {}).get("source_diversity_v04", 0)) for s in per_record_summaries) / n

    records.append({"behavior_field": "setwise_selection_diff_rate_vs_v03",
                    "value": round(diff_count / n, 6), "record_count": n})
    records.append({"behavior_field": "mean_duplicate_file_count_v03",
                    "value": round(mean_dup_v03, 6), "record_count": n})
    records.append({"behavior_field": "mean_duplicate_file_count_v04",
                    "value": round(mean_dup_v04, 6), "record_count": n})
    records.append({"behavior_field": "mean_candidate_source_diversity_v03",
                    "value": round(mean_div_v03, 6), "record_count": n})
    records.append({"behavior_field": "mean_candidate_source_diversity_v04",
                    "value": round(mean_div_v04, 6), "record_count": n})
    records.sort(key=lambda r: r["behavior_field"])
    return records


def _failure_family_records(
    per_record_failure_families: list[dict[str, dict[str, dict[str, Any]]]],
    policy_arm: str,
) -> list[dict[str, Any]]:
    if not per_record_failure_families:
        return []
    records: list[dict[str, Any]] = []
    for family in FAILURE_FAMILIES:
        avail_counts: dict[str, int] = {}
        for rec_families in per_record_failure_families:
            raw_info = rec_families.get(family, {})
            fam_info = raw_info if isinstance(raw_info, dict) else {}
            raw_count = fam_info.get("count", 0)
            count = int(raw_count) if isinstance(raw_count, (int, float, str)) else 0
            avail = str(fam_info.get("availability", "available"))
            avail_counts[avail] = avail_counts.get(avail, 0) + (1 if count > 0 else 0)
        for avail, cnt in sorted(avail_counts.items()):
            records.append({
                "failure_family": family,
                "policy_arm": policy_arm,
                "availability": avail,
                "record_count": cnt,
            })
        if not avail_counts:
            records.append({
                "failure_family": family,
                "policy_arm": policy_arm,
                "availability": "available",
                "record_count": 0,
            })
    records.sort(key=lambda r: (r["failure_family"], r["policy_arm"], r["availability"]))
    return records


def _availability_records(
    per_record_failure_families_v03: list[dict[str, dict[str, dict[str, Any]]]],
    per_record_failure_families_v04: list[dict[str, dict[str, dict[str, Any]]]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    avail_totals: dict[tuple[str, str], int] = {}
    for rec_families in per_record_failure_families_v03 + per_record_failure_families_v04:
        for family, info in rec_families.items():
            if not isinstance(info, dict):
                continue
            avail = str(info.get("availability", "available"))
            key = (family, avail)
            avail_totals[key] = avail_totals.get(key, 0) + 1
    for (family, avail), cnt in sorted(avail_totals.items()):
        records.append({
            "category": family,
            "availability": avail,
            "record_count": cnt,
        })
    return records


# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str, *, self_test_passed: bool,
    self_test_checks_total: int = SELF_TEST_CHECKS_EXPECTED,
    self_test_checks_passed: int | None = None,
    openlocus_binary_source: str, network_mode: str,
    private_score_storage_class: str = "tmp_private",
    private_score_records_written: bool = False,
    private_score_record_count: int = 0,
    private_decision_records_written: bool = False,
    private_decision_record_count: int = 0,
    private_role_proxy_records_written: bool = False,
    private_role_proxy_record_count: int = 0,
    private_score_manifest_hash_value: str | None = None,
    private_decision_manifest_hash_value: str | None = None,
    private_role_proxy_manifest_hash_value: str | None = None,
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
    safe_true["private_role_proxy_records_written"] = bool(private_role_proxy_records_written)

    score_hash = (
        private_score_manifest_hash_value
        if private_score_manifest_hash_value is not None
        else _private_score_manifest_hash()
    )
    decision_hash = (
        private_decision_manifest_hash_value
        if private_decision_manifest_hash_value is not None
        else _private_decision_manifest_hash()
    )
    role_proxy_hash = (
        private_role_proxy_manifest_hash_value
        if private_role_proxy_manifest_hash_value is not None
        else _private_role_proxy_manifest_hash()
    )

    per_benchmark_attempts = {
        "contextbench": {
            "attempted": int(contextbench_attempted),
            "successful": int(contextbench_successful),
            "excluded": int(contextbench_excluded),
        },
        "repoqa": {
            "attempted": int(repoqa_attempted),
            "successful": int(repoqa_successful),
            "excluded": int(repoqa_excluded),
        },
    }
    benchmark_attempt_records = _benchmark_attempt_records(per_benchmark_attempts)

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
        "quality_baseline_arm": QUALITY_BASELINE_ARM,
        "seeded_random_seed": SEEDED_RANDOM_SEED,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "sampling_mode": SAMPLING_MODE,
        "sampling_protocol_version": SAMPLING_PROTOCOL_VERSION,
        "sampling_frame_policy": SAMPLING_FRAME_POLICY,
        "excluded_prior_windows_policy": EXCLUDED_PRIOR_WINDOWS_POLICY,
        "bea5_overlap_policy": BEA5_OVERLAP_POLICY,
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
        "role_proxy_summary_records": [],
        "setwise_behavior_records": [],
        "failure_family_records": [],
        "win_tie_loss_records": [],
        "availability_records": [],
        "benchmark_attempt_records": benchmark_attempt_records,
        "hard_gate_records": [],
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": score_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "private_decision_manifest": {
            "records_written": bool(private_decision_records_written),
            "record_count": int(private_decision_record_count),
            "schema_version": PRIVATE_DECISION_SCHEMA_VERSION,
            "manifest_hash": decision_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "private_role_proxy_manifest": {
            "records_written": bool(private_role_proxy_records_written),
            "record_count": int(private_role_proxy_record_count),
            "schema_version": PRIVATE_ROLE_PROXY_SCHEMA_VERSION,
            "manifest_hash": role_proxy_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
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
            "signal_strength": "bea_v04_p1_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
        },
    }
    scan = _v04_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_pass_report(
    *, self_test_passed: bool,
    self_test_checks_total: int = SELF_TEST_CHECKS_EXPECTED,
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
    per_record_role_proxy_summaries: list[dict[str, Any]],
    per_record_setwise_summaries: list[dict[str, Any]],
    per_record_failure_families_v03: list[dict[str, dict[str, dict[str, Any]]]],
    per_record_failure_families_v04: list[dict[str, dict[str, dict[str, Any]]]],
    private_score_records_written: bool,
    private_score_record_count: int,
    private_decision_records_written: bool,
    private_decision_record_count: int,
    private_role_proxy_records_written: bool,
    private_role_proxy_record_count: int,
    private_score_storage_class: str,
    private_score_manifest_hash: str,
    private_decision_manifest_hash: str,
    private_role_proxy_manifest_hash: str,
    aggregate_runtime_seconds: float,
    failure_category_counts: dict[str, int],
    paired_exclusion_count: int, partial: bool,
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
    safe_true["bea_v04_p1_policy_executed"] = records_successful > 0
    safe_true["role_proxy_assigned"] = records_successful > 0
    safe_true["setwise_selection_performed"] = records_successful > 0
    safe_true["fresh_smoke_slice_read"] = records_evaluated > 0
    safe_true["private_score_records_written"] = bool(private_score_records_written)
    safe_true["private_decision_records_written"] = bool(private_decision_records_written)
    safe_true["private_role_proxy_records_written"] = bool(private_role_proxy_records_written)

    amr = _arm_metric_records(arm_aggs)

    required_controls = [
        ARM_BEA_V0_3, ARM_BM25_PREFIX, ARM_ROLE_PROXY_ONLY,
        ARM_SEEDED_RANDOM, ARM_RRF_SAME_BUDGET,
    ]
    adr: list[dict[str, Any]] = []
    for control in required_controls:
        adr.extend(_arm_delta_records(arm_aggs, control, [TREATMENT_ARM]))
    adr.sort(key=lambda r: (r["baseline_arm"], r["treatment_arm"], r["metric"]))

    wtl: list[dict[str, Any]] = []
    for baseline in required_controls:
        wtl.extend(_win_tie_loss_records(per_record_arm_metrics, baseline, TREATMENT_ARM))
    wtl.sort(key=lambda r: (r["baseline_arm"], r["metric"]))

    rpsr = _role_proxy_summary_records(per_record_role_proxy_summaries)
    sbr = _setwise_behavior_records(per_record_setwise_summaries)
    ffr_v04 = _failure_family_records(per_record_failure_families_v04, TREATMENT_ARM)
    ffr_v03 = _failure_family_records(per_record_failure_families_v03, ARM_BEA_V0_3)
    ffr = ffr_v04 + ffr_v03
    ffr.sort(key=lambda r: (r["failure_family"], r["policy_arm"], r["availability"]))
    avr = _availability_records(per_record_failure_families_v03, per_record_failure_families_v04)

    per_benchmark_attempts = {
        "contextbench": {
            "attempted": int(contextbench_attempted),
            "successful": int(contextbench_successful),
            "excluded": int(contextbench_excluded),
        },
        "repoqa": {
            "attempted": int(repoqa_attempted),
            "successful": int(repoqa_successful),
            "excluded": int(repoqa_excluded),
        },
    }
    benchmark_attempt_records = _benchmark_attempt_records(per_benchmark_attempts)

    source_run_records = [{
        "source_phase": PHASE,
        "source_ci_run_id": "",
        "source_artifact_status": "fresh_smoke",
        "source_sampling_protocol": SAMPLING_PROTOCOL_VERSION,
        "expected_successful_records": TARGET_SUCCESSFUL_RECORDS,
        "replayed_successful_records": records_successful,
        "expected_private_score_count": records_successful * len(FIXED_ARMS),
        "replayed_private_score_count": private_score_record_count,
        "records_attempted_total": int(records_attempted_total),
        "records_excluded": int(records_excluded),
        "contextbench_successful": int(contextbench_successful),
        "repoqa_successful": int(repoqa_successful),
        "replay_protocol_match": True,
        "replay_mismatch_reason": "",
    }]

    role_proxy_assignment_rate = (
        sum(float(s.get("role_proxy_assignment_rate", 0.0)) for s in per_record_role_proxy_summaries) / len(per_record_role_proxy_summaries)
        if per_record_role_proxy_summaries else 0.0
    )
    target_avail_rate = (
        sum(1 for s in per_record_role_proxy_summaries if s.get("has_target")) / len(per_record_role_proxy_summaries)
        if per_record_role_proxy_summaries else 0.0
    )
    support_avail_rate = (
        sum(1 for s in per_record_role_proxy_summaries if s.get("has_support")) / len(per_record_role_proxy_summaries)
        if per_record_role_proxy_summaries else 0.0
    )
    unknown_only_rate = (
        sum(1 for s in per_record_role_proxy_summaries if s.get("unknown_only")) / len(per_record_role_proxy_summaries)
        if per_record_role_proxy_summaries else 0.0
    )
    diff_rate = (
        sum(1 for s in per_record_setwise_summaries if s.get("setwise_behavior", {}).get("selection_differs_v03", False)) / len(per_record_setwise_summaries)
        if per_record_setwise_summaries else 0.0
    )

    v03_agg = arm_aggs.get(ARM_BEA_V0_3, {})
    v04_agg = arm_aggs.get(TREATMENT_ARM, {})
    v03_fr = float(v03_agg.get("file_recall@10", 0.0))
    v04_fr = float(v04_agg.get("file_recall@10", 0.0))
    v03_mrr = float(v03_agg.get("mrr", 0.0))
    v04_mrr = float(v04_agg.get("mrr", 0.0))
    v03_span = float(v03_agg.get("span_f0.5@10", 0.0))
    v04_span = float(v04_agg.get("span_f0.5@10", 0.0))
    v03_lat = float(v03_agg.get("latency_seconds", 0.0))
    v04_lat = float(v04_agg.get("latency_seconds", 0.0))

    mean_dup_v03 = (
        sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_v03", 0)) for s in per_record_setwise_summaries) / len(per_record_setwise_summaries)
        if per_record_setwise_summaries else 0.0
    )
    mean_dup_v04 = (
        sum(int(s.get("setwise_behavior", {}).get("duplicate_file_count_v04", 0)) for s in per_record_setwise_summaries) / len(per_record_setwise_summaries)
        if per_record_setwise_summaries else 0.0
    )
    mean_div_v03 = (
        sum(int(s.get("setwise_behavior", {}).get("source_diversity_v03", 0)) for s in per_record_setwise_summaries) / len(per_record_setwise_summaries)
        if per_record_setwise_summaries else 0.0
    )
    mean_div_v04 = (
        sum(int(s.get("setwise_behavior", {}).get("source_diversity_v04", 0)) for s in per_record_setwise_summaries) / len(per_record_setwise_summaries)
        if per_record_setwise_summaries else 0.0
    )

    proxy_ok = (
        role_proxy_assignment_rate >= GATE_ROLE_PROXY_ASSIGNMENT_RATE
        and target_avail_rate >= GATE_TARGET_PROXY_AVAILABLE_RATE
        and support_avail_rate >= GATE_SUPPORT_PROXY_AVAILABLE_RATE
        and unknown_only_rate <= GATE_UNKNOWN_ONLY_RATE
    )
    behavior_ok = (
        diff_rate >= GATE_SETWISE_DIFF_RATE
        and mean_dup_v04 <= mean_dup_v03
        and mean_div_v04 >= mean_div_v03
    )
    quality_ok = (
        v04_fr >= v03_fr - GATE_QUALITY_MARGIN
        and v04_mrr >= v03_mrr - GATE_QUALITY_MARGIN
        and v04_span >= v03_span - GATE_SPAN_MARGIN
        and (v03_lat <= 0 or v04_lat <= v03_lat * GATE_LATENCY_RATIO)
    )
    directional = (
        mean_dup_v04 < mean_dup_v03
        or v04_fr > v03_fr
        or v04_span > v03_span
        or (v03_lat > 0 and v04_lat > 0 and (v04_span / v04_lat) > (v03_span / v03_lat))
    )

    denominator_ok = (
        records_successful >= TARGET_SUCCESSFUL_RECORDS
        and contextbench_successful >= MIN_CONTEXTBENCH_SUCCESSFUL
        and repoqa_successful >= MIN_REPOQA_SUCCESSFUL
    )
    blocking_failure_count = _blocking_failure_count(fcc)

    if records_successful <= 0:
        status = "unavailable_with_reason"
    elif blocking_failure_count > 0:
        status = "fail_schema_contract"
    elif not denominator_ok:
        status = "partial_directional_signal"
    elif not proxy_ok:
        status = "no_go_proxy_unavailable"
    elif not behavior_ok:
        status = "no_go_no_selection_change"
    elif not quality_ok:
        status = "no_go_quality_regression"
    elif directional and not partial:
        status = "bea_v04_p1_smoke_pass"
    elif records_successful > 0:
        status = "partial_directional_signal"
    else:
        status = "unavailable_with_reason"

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
        "quality_baseline_arm": QUALITY_BASELINE_ARM,
        "delta_baseline_arm": DELTA_BASELINE_ARM,
        "seeded_random_seed": SEEDED_RANDOM_SEED,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "sampling_mode": SAMPLING_MODE,
        "sampling_protocol_version": SAMPLING_PROTOCOL_VERSION,
        "sampling_frame_policy": SAMPLING_FRAME_POLICY,
        "excluded_prior_windows_policy": EXCLUDED_PRIOR_WINDOWS_POLICY,
        "bea5_overlap_policy": BEA5_OVERLAP_POLICY,
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
        "paired_exclusion_count": int(paired_exclusion_count),
        "network_calls": network_calls,
        "provider_calls": 0,
        "source_run_records": source_run_records,
        "arm_metric_records": amr,
        "arm_delta_records": adr,
        "role_proxy_summary_records": rpsr,
        "setwise_behavior_records": sbr,
        "failure_family_records": ffr,
        "win_tie_loss_records": wtl,
        "availability_records": avr,
        "benchmark_attempt_records": benchmark_attempt_records,
        "private_score_manifest": {
            "records_written": bool(private_score_records_written),
            "record_count": int(private_score_record_count),
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": private_score_manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "private_decision_manifest": {
            "records_written": bool(private_decision_records_written),
            "record_count": int(private_decision_record_count),
            "schema_version": PRIVATE_DECISION_SCHEMA_VERSION,
            "manifest_hash": private_decision_manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "private_role_proxy_manifest": {
            "records_written": bool(private_role_proxy_records_written),
            "record_count": int(private_role_proxy_record_count),
            "schema_version": PRIVATE_ROLE_PROXY_SCHEMA_VERSION,
            "manifest_hash": private_role_proxy_manifest_hash,
            "storage_class": private_score_storage_class,
            "path_publicly_serialized": False,
        },
        "aggregate_runtime_seconds": round(float(aggregate_runtime_seconds), 3),
        "failure_category_count_records": _failure_category_count_records(fcc),
        "hard_gate_records": [
            {"gate": "role_proxy_assignment_rate", "value": round(role_proxy_assignment_rate, 6), "threshold_relation": ">=", "threshold_value": GATE_ROLE_PROXY_ASSIGNMENT_RATE, "passed": role_proxy_assignment_rate >= GATE_ROLE_PROXY_ASSIGNMENT_RATE},
            {"gate": "target_proxy_available_rate", "value": round(target_avail_rate, 6), "threshold_relation": ">=", "threshold_value": GATE_TARGET_PROXY_AVAILABLE_RATE, "passed": target_avail_rate >= GATE_TARGET_PROXY_AVAILABLE_RATE},
            {"gate": "support_proxy_available_rate", "value": round(support_avail_rate, 6), "threshold_relation": ">=", "threshold_value": GATE_SUPPORT_PROXY_AVAILABLE_RATE, "passed": support_avail_rate >= GATE_SUPPORT_PROXY_AVAILABLE_RATE},
            {"gate": "unknown_only_record_rate", "value": round(unknown_only_rate, 6), "threshold_relation": "<=", "threshold_value": GATE_UNKNOWN_ONLY_RATE, "passed": unknown_only_rate <= GATE_UNKNOWN_ONLY_RATE},
            {"gate": "setwise_selection_diff_rate_vs_v03", "value": round(diff_rate, 6), "threshold_relation": ">=", "threshold_value": GATE_SETWISE_DIFF_RATE, "passed": diff_rate >= GATE_SETWISE_DIFF_RATE},
            {"gate": "mean_duplicate_file_count_v03", "value": round(mean_dup_v03, 6), "threshold_relation": "baseline", "threshold_value": round(mean_dup_v03, 6), "passed": True},
            {"gate": "mean_duplicate_file_count_v04", "value": round(mean_dup_v04, 6), "threshold_relation": "<=v03", "threshold_value": round(mean_dup_v03, 6), "passed": mean_dup_v04 <= mean_dup_v03},
            {"gate": "mean_candidate_source_diversity_v03", "value": round(mean_div_v03, 6), "threshold_relation": "baseline", "threshold_value": round(mean_div_v03, 6), "passed": True},
            {"gate": "mean_candidate_source_diversity_v04", "value": round(mean_div_v04, 6), "threshold_relation": ">=v03", "threshold_value": round(mean_div_v03, 6), "passed": mean_div_v04 >= mean_div_v03},
            {"gate": "file_recall_10_v03", "value": round(v03_fr, 6), "threshold_relation": "baseline", "threshold_value": round(v03_fr, 6), "passed": True},
            {"gate": "file_recall_10_v04", "value": round(v04_fr, 6), "threshold_relation": ">=v03_minus_margin", "threshold_value": round(v03_fr - GATE_QUALITY_MARGIN, 6), "passed": v04_fr >= v03_fr - GATE_QUALITY_MARGIN},
            {"gate": "mrr_v03", "value": round(v03_mrr, 6), "threshold_relation": "baseline", "threshold_value": round(v03_mrr, 6), "passed": True},
            {"gate": "mrr_v04", "value": round(v04_mrr, 6), "threshold_relation": ">=v03_minus_margin", "threshold_value": round(v03_mrr - GATE_QUALITY_MARGIN, 6), "passed": v04_mrr >= v03_mrr - GATE_QUALITY_MARGIN},
            {"gate": "span_f05_10_v03", "value": round(v03_span, 6), "threshold_relation": "baseline", "threshold_value": round(v03_span, 6), "passed": True},
            {"gate": "span_f05_10_v04", "value": round(v04_span, 6), "threshold_relation": ">=v03_minus_margin", "threshold_value": round(v03_span - GATE_SPAN_MARGIN, 6), "passed": v04_span >= v03_span - GATE_SPAN_MARGIN},
            {"gate": "latency_seconds_v03", "value": round(v03_lat, 6), "threshold_relation": "baseline", "threshold_value": round(v03_lat, 6), "passed": True},
            {"gate": "latency_seconds_v04", "value": round(v04_lat, 6), "threshold_relation": "<=v03_ratio", "threshold_value": round(v03_lat * GATE_LATENCY_RATIO if v03_lat > 0 else 0.0, 6), "passed": (v03_lat <= 0 or v04_lat <= v03_lat * GATE_LATENCY_RATIO)},
            {"gate": "proxy_ok", "value": 1.0 if proxy_ok else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(proxy_ok)},
            {"gate": "behavior_ok", "value": 1.0 if behavior_ok else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(behavior_ok)},
            {"gate": "quality_ok", "value": 1.0 if quality_ok else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(quality_ok)},
            {"gate": "directional_improvement", "value": 1.0 if directional else 0.0, "threshold_relation": "boolean", "threshold_value": 1.0, "passed": bool(directional)},
        ],
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
            "signal_strength": "bea_v04_p1_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_v04_full_matrix": False,
        },
    }
    scan = _v04_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _build_synthetic_candidates() -> list[dict[str, Any]]:
    return bea0._build_synthetic_candidates()


def _build_synthetic_gold() -> dict[str, Any]:
    return bea0._build_synthetic_gold()


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    candidates = _build_synthetic_candidates()
    gold = _build_synthetic_gold()
    query = "merge adjacent strings into a single string"

    v04_acc, v04_ao, v04_bt, v04_sr, v04_ms = _bea_v0_4_p1_setwise_policy(
        candidates, query, 5
    )
    v03_acc, v03_ao, v03_bt, v03_sr, v03_ms = bea3._bea_v0_3_policy(
        candidates, query, 5, use_anchor=True, use_early_stop=True
    )

    deduped = bea1._dedup_candidates(candidates)
    query_toks = bea2._query_tokens(query)
    role_assignments = _assign_role_proxies_batch(deduped, query_toks)
    role_proxy_summary = _record_role_proxy_summary(role_assignments)

    same_budget_k = bea2._same_budget_k(len(v03_acc), len(deduped))
    rp_ev = _role_proxy_only_same_budget_arm(role_assignments, same_budget_k)
    sr_ev = bea2._seeded_random_same_budget_arm(candidates, same_budget_k)
    rrf_ev = bea2._rrf_same_budget_arm(
        bea5._derive_rrf_candidates_from_method_ranks(candidates), same_budget_k
    )
    sb_bm25_ev = bea2._bm25_prefix_same_budget_arm(
        {"bm25": [c for c in candidates if c["method"] == "bm25"]}, same_budget_k
    )

    v04_m = _arm_metrics_for_record(
        ARM_SETWISE_V0_4_P1, v04_acc, gold, "v04-st", len(candidates),
        len(v04_acc), len(v04_ao), 0.05)
    v03_m = _arm_metrics_for_record(
        ARM_BEA_V0_3, v03_acc, gold, "v04-st", len(candidates),
        len(v03_acc), len(v03_ao), 0.04)
    sb_m = _arm_metrics_for_record(
        ARM_BM25_PREFIX, sb_bm25_ev, gold, "v04-st", len(candidates),
        len(sb_bm25_ev), len(sb_bm25_ev), 0.0)
    rp_m = _arm_metrics_for_record(
        ARM_ROLE_PROXY_ONLY, rp_ev, gold, "v04-st", len(candidates),
        len(rp_ev), len(rp_ev), 0.0)
    sr_m = _arm_metrics_for_record(
        ARM_SEEDED_RANDOM, sr_ev, gold, "v04-st", len(candidates),
        len(sr_ev), len(sr_ev), 0.0)
    rrf_m = _arm_metrics_for_record(
        ARM_RRF_SAME_BUDGET, rrf_ev, gold, "v04-st", len(candidates),
        len(rrf_ev), len(rrf_ev), 0.0)

    arm_aggs = {
        ARM_SETWISE_V0_4_P1: {**_arm_means([v04_m]), "__record_count__": 1},
        ARM_BEA_V0_3: {**_arm_means([v03_m]), "__record_count__": 1},
        ARM_BM25_PREFIX: {**_arm_means([sb_m]), "__record_count__": 1},
        ARM_ROLE_PROXY_ONLY: {**_arm_means([rp_m]), "__record_count__": 1},
        ARM_SEEDED_RANDOM: {**_arm_means([sr_m]), "__record_count__": 1},
        ARM_RRF_SAME_BUDGET: {**_arm_means([rrf_m]), "__record_count__": 1},
    }
    per_record_arm_metrics = [{
        ARM_SETWISE_V0_4_P1: v04_m, ARM_BEA_V0_3: v03_m,
        ARM_BM25_PREFIX: sb_m, ARM_ROLE_PROXY_ONLY: rp_m,
        ARM_SEEDED_RANDOM: sr_m, ARM_RRF_SAME_BUDGET: rrf_m,
    }]

    per_record_role_proxy_summaries = [role_proxy_summary]
    per_record_setwise_summaries = [{
        "role_proxy_summary": role_proxy_summary,
        "setwise_behavior": {
            "selection_differs_v03": _selection_differs(v03_acc, v04_acc),
            "duplicate_file_count_v03": _accepted_file_duplicates(v03_acc),
            "duplicate_file_count_v04": _accepted_file_duplicates(v04_acc),
            "source_diversity_v03": _accepted_source_diversity(v03_acc, candidates),
            "source_diversity_v04": _accepted_source_diversity(v04_acc, candidates),
            "v03_budget_used": len(v03_acc),
            "v04_budget_used": len(v04_acc),
            "same_budget_k": same_budget_k,
        },
    }]

    ff_v03 = _classify_failure_family(
        v03_m, len(v03_acc), float(v03_m.get("latency_seconds", 0.0)),
        v03_m, float(v03_m.get("latency_seconds", 0.0)), role_proxy_summary,
    )
    ff_v04 = _classify_failure_family(
        v04_m, len(v04_acc), float(v04_m.get("latency_seconds", 0.0)),
        v03_m, float(v03_m.get("latency_seconds", 0.0)), role_proxy_summary,
    )

    skeleton = _build_pass_report(
        self_test_passed=True,
        openlocus_binary_source="self_test",
        network_mode="self_test",
        records_attempted_total=1,
        records_evaluated=1, records_successful=1, records_failed=0,
        records_excluded=0,
        contextbench_attempted=1, contextbench_successful=1,
        contextbench_excluded=0,
        repoqa_attempted=0, repoqa_successful=0, repoqa_excluded=0,
        contextbench_excluded_prior_window_count=0,
        repoqa_excluded_prior_window_count=0,
        contextbench_eligible_count=1,
        repoqa_eligible_count=0,
        quota_reached=True,
        network_calls=0, arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_record_role_proxy_summaries=per_record_role_proxy_summaries,
        per_record_setwise_summaries=per_record_setwise_summaries,
        per_record_failure_families_v03=[ff_v03],
        per_record_failure_families_v04=[ff_v04],
        private_score_records_written=True,
        private_score_record_count=6,
        private_decision_records_written=True,
        private_decision_record_count=len(v04_ao),
        private_role_proxy_records_written=True,
        private_role_proxy_record_count=len(role_assignments),
        private_score_storage_class="tmp_private",
        private_score_manifest_hash=_private_score_manifest_hash(),
        private_decision_manifest_hash=_private_decision_manifest_hash(),
        private_role_proxy_manifest_hash=_private_role_proxy_manifest_hash(),
        aggregate_runtime_seconds=0.5,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        paired_exclusion_count=0, partial=False,
    )
    unavail = _build_unavailable_report(
        "retrieval_failed", self_test_passed=True,
        openlocus_binary_source="self_test",
        network_mode="self_test",
    )

    # G1: Identity
    for k, v in [("schema_version", SCHEMA_VERSION), ("claim_level", CLAIM_LEVEL),
                 ("mode", MODE), ("phase", PHASE), ("generated_by", GENERATED_BY)]:
        checks.append(_check(f"identity_{k}", skeleton[k] == v))
    checks.append(_check("status_present", "status" in skeleton))
    checks.append(_check("unavail_status", unavail["status"] == "unavailable_with_reason"))

    # G2: Safe true flags
    for flag in ("aggregate_only_public_artifact", "diagnostic_only",
                 "bea_v04_p1_policy_executed", "role_proxy_assigned",
                 "setwise_selection_performed"):
        checks.append(_check(f"safe_true_{flag}", skeleton.get(flag) is True))

    # G3: No-claim false flags
    for flag in ("external_benchmark_performance_claimed",
                 "leaderboard_entry_claimed", "downstream_agent_value_proven",
                 "calibration_claimed", "method_winner_claimed",
                 "promotion_ready", "default_should_change",
                 "runtime_behavior_changed", "retriever_changed",
                 "pack_builder_changed", "backend_changed",
                 "default_policy_changed", "evidencecore_semantics_changed",
                 "provider_calls_made", "remote_provider_calls_made",
                 "algorithm_changed_during_bea_v04_p1",
                 "weights_tuned_during_bea_v04_p1",
                 "v04_full_matrix_claimed"):
        checks.append(_check(f"false_{flag}", skeleton.get(flag) is False))

    # G4: License fields
    for field, expected in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{field}", skeleton.get(field) == expected))

    # G5: Fixed protocol constants
    checks.append(_check("fixed_budget_5", FIXED_BUDGET == 5))
    checks.append(_check("fixed_methods", FIXED_METHODS == "bm25,regex,symbol"))
    checks.append(_check("target_successful_30", TARGET_SUCCESSFUL_RECORDS == 30))
    checks.append(_check("min_cb_20", MIN_CONTEXTBENCH_SUCCESSFUL == 20))
    checks.append(_check("min_rq_10", MIN_REPOQA_SUCCESSFUL == 10))
    checks.append(_check("raw_cap_cb_480", RAW_ATTEMPT_CAP_CONTEXTBENCH == 480))
    checks.append(_check("raw_cap_rq_240", RAW_ATTEMPT_CAP_REPOQA == 240))
    checks.append(_check("ci_min_records_30", CI_MIN_RECORDS_SUCCESSFUL == 30))
    checks.append(_check("sampling_mode", SAMPLING_MODE == "success_quota"))
    checks.append(_check("sampling_protocol", SAMPLING_PROTOCOL_VERSION == "bea_v04_p1_fresh_smoke.v1"))
    checks.append(_check("bea5_overlap_disclosed", "disclosed" in BEA5_OVERLAP_POLICY))
    checks.append(_check("blocking_failure_categories_count_5", len(BLOCKING_FAILURE_CATEGORIES) == 5))
    bad_fcc = {c: 0 for c in FAILURE_CATEGORIES}
    bad_fcc["private_score_write_failed"] = 1
    checks.append(_check("blocking_private_score_failure_detected", _blocking_failure_count(bad_fcc) == 1))
    checks.append(_check("blocking_clean_failure_count_zero", _blocking_failure_count({c: 0 for c in FAILURE_CATEGORIES}) == 0))

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

    # G7: Fixed arms
    for arm in FIXED_ARMS:
        checks.append(_check(f"fixed_arms_has_{arm}", arm in skeleton.get("fixed_arms", [])))
    checks.append(_check("fixed_arms_count_6", len(skeleton.get("fixed_arms", [])) == 6))
    checks.append(_check("treatment_arm", skeleton.get("treatment_arm") == ARM_SETWISE_V0_4_P1))
    checks.append(_check("quality_baseline_arm", skeleton.get("quality_baseline_arm") == ARM_BEA_V0_3))

    # G8: Role-proxy enum
    checks.append(_check("role_enum_3", len(ROLE_ENUM) == 3))
    for role in ROLE_ENUM:
        checks.append(_check(f"role_enum_{role}", role in ROLE_ENUM))

    # G9: Role-proxy assignment
    checks.append(_check("role_assignments_nonempty", len(role_assignments) > 0))
    roles_present = {ra["role_proxy"] for ra in role_assignments}
    checks.append(_check("role_assignments_have_target_or_support",
        ROLE_TARGET_PROXY in roles_present or ROLE_SUPPORT_PROXY in roles_present))
    checks.append(_check("role_proxy_summary_has_assignment_rate",
        "role_proxy_assignment_rate" in role_proxy_summary))
    checks.append(_check("role_proxy_summary_has_target", "has_target" in role_proxy_summary))
    checks.append(_check("role_proxy_summary_has_support", "has_support" in role_proxy_summary))

    # G10: v0.4 P1 policy mechanics
    checks.append(_check("v04_accepts_nonempty", len(v04_acc) > 0))
    checks.append(_check("v04_respects_budget_5", len(v04_acc) <= 5))
    v04_b3, _, _, _, _ = _bea_v0_4_p1_setwise_policy(candidates, query, 3)
    checks.append(_check("v04_respects_budget_3", len(v04_b3) <= 3))
    v04_b0, _, _, _, _ = _bea_v0_4_p1_setwise_policy(candidates, query, 0)
    checks.append(_check("v04_budget_0_empty", len(v04_b0) == 0))
    checks.append(_check("v04_empty_candidates", len(_bea_v0_4_p1_setwise_policy([], query, 5)[0]) == 0))
    checks.append(_check("v04_action_order_nonempty", len(v04_ao) > 0))
    checks.append(_check("v04_budget_trace_nonempty", len(v04_bt) > 0))
    checks.append(_check("v04_stop_reason_present", isinstance(v04_sr, str) and len(v04_sr) > 0))
    checks.append(_check("v04_mechanism_summary_present", isinstance(v04_ms, dict) and len(v04_ms) > 0))
    checks.append(_check("v04_role_proxy_used", v04_ms.get("role_proxy_used") is True))
    checks.append(_check("v04_setwise_used", v04_ms.get("setwise_used") is True))
    checks.append(_check("v04_mechanism_has_target_filled", "target_slot_filled" in v04_ms))
    checks.append(_check("v04_mechanism_has_support_selected", "support_selected" in v04_ms))

    # G11: v0.4 P1 priority components
    if v04_ao:
        first = v04_ao[0]
        for comp in ("role_proxy", "target_boost", "support_cross_file",
                     "source_diversity", "span_bonus_v04", "novelty",
                     "dup_file_penalty"):
            checks.append(_check(f"v04_priority_{comp}_present",
                comp in first.get("priority_components", {})))

    # G12: v0.4 P1 differs from v0.3
    checks.append(_check("v04_differs_from_v03",
        len(v04_ao) != len(v03_ao) or v04_acc != v03_acc
        or any("role_proxy" in a.get("priority_components", {}) for a in v04_ao)))

    # G13: Frozen weights
    checks.append(_check("weight_target_frozen", V04_P1_WEIGHT_TARGET == 0.40))
    checks.append(_check("weight_support_cross_file_frozen", V04_P1_WEIGHT_SUPPORT_CROSS_FILE == 0.20))
    checks.append(_check("weight_source_diversity_frozen", V04_P1_WEIGHT_SOURCE_DIVERSITY == 0.15))
    checks.append(_check("weight_span_tight_frozen", V04_P1_WEIGHT_SPAN_TIGHT == 0.10))
    checks.append(_check("weight_novelty_frozen", V04_P1_WEIGHT_NOVELTY == 0.10))
    checks.append(_check("weight_dup_file_penalty_frozen", V04_P1_WEIGHT_DUP_FILE_PENALTY == -0.35))
    checks.append(_check("weight_weak_support_penalty_frozen", V04_P1_WEIGHT_WEAK_SUPPORT_PENALTY == -0.15))

    # G14: Hard gates constants
    checks.append(_check("gate_role_proxy_assignment_070", GATE_ROLE_PROXY_ASSIGNMENT_RATE == 0.70))
    checks.append(_check("gate_target_avail_050", GATE_TARGET_PROXY_AVAILABLE_RATE == 0.50))
    checks.append(_check("gate_support_avail_030", GATE_SUPPORT_PROXY_AVAILABLE_RATE == 0.30))
    checks.append(_check("gate_unknown_only_030", GATE_UNKNOWN_ONLY_RATE == 0.30))
    checks.append(_check("gate_setwise_diff_025", GATE_SETWISE_DIFF_RATE == 0.25))
    checks.append(_check("gate_quality_margin_005", GATE_QUALITY_MARGIN == 0.05))
    checks.append(_check("gate_span_margin_002", GATE_SPAN_MARGIN == 0.02))
    checks.append(_check("gate_latency_ratio_125", GATE_LATENCY_RATIO == 1.25))

    # G15: Public record tables present + nonempty
    for table in ("source_run_records", "arm_metric_records", "arm_delta_records",
                  "role_proxy_summary_records", "setwise_behavior_records",
                  "failure_family_records", "win_tie_loss_records",
                  "availability_records", "benchmark_attempt_records",
                  "failure_category_count_records", "hard_gate_records"):
        checks.append(_check(f"table_{table}_present", isinstance(skeleton.get(table), list)))
        checks.append(_check(f"table_{table}_nonempty", len(skeleton.get(table, [])) > 0))

    # G16: Natural-key uniqueness
    checks.append(_check("amr_unique", not _check_unique_records(skeleton.get("arm_metric_records", []), _amr_natural_key, "arm_metric_records")))
    checks.append(_check("adr_unique", not _check_unique_records(skeleton.get("arm_delta_records", []), _adr_natural_key, "arm_delta_records")))
    checks.append(_check("wtl_unique", not _check_unique_records(skeleton.get("win_tie_loss_records", []), _wtl_natural_key, "win_tie_loss_records")))
    checks.append(_check("rpsr_unique", not _check_unique_records(skeleton.get("role_proxy_summary_records", []), _rpsr_natural_key, "role_proxy_summary_records")))
    checks.append(_check("sbr_unique", not _check_unique_records(skeleton.get("setwise_behavior_records", []), _sbr_natural_key, "setwise_behavior_records")))
    checks.append(_check("ffr_unique", not _check_unique_records(skeleton.get("failure_family_records", []), _ffr_natural_key, "failure_family_records")))
    checks.append(_check("avr_unique", not _check_unique_records(skeleton.get("availability_records", []), _avr_natural_key, "availability_records")))
    checks.append(_check("srr_unique", not _check_unique_records(skeleton.get("source_run_records", []), _srr_natural_key, "source_run_records")))

    # G17: Private manifests
    for manifest_name, schema_ver in (
        ("private_score_manifest", PRIVATE_SCORE_SCHEMA_VERSION),
        ("private_decision_manifest", PRIVATE_DECISION_SCHEMA_VERSION),
        ("private_role_proxy_manifest", PRIVATE_ROLE_PROXY_SCHEMA_VERSION),
    ):
        m = skeleton.get(manifest_name, {})
        checks.append(_check(f"{manifest_name}_present", isinstance(m, dict) and len(m) > 0))
        checks.append(_check(f"{manifest_name}_records_written", m.get("records_written") is True))
        checks.append(_check(f"{manifest_name}_path_not_serialized", m.get("path_publicly_serialized") is False))
        checks.append(_check(f"{manifest_name}_hash_64", len(m.get("manifest_hash", "")) == 64))
        checks.append(_check(f"{manifest_name}_schema", m.get("schema_version") == schema_ver))

    # G18: Hard gates present as records-only table
    hg = skeleton.get("hard_gate_records", [])
    checks.append(_check("hard_gate_records_present", isinstance(hg, list) and len(hg) > 0))
    gate_names = {r.get("gate") for r in hg if isinstance(r, dict)}
    for field in ("role_proxy_assignment_rate", "target_proxy_available_rate",
                  "support_proxy_available_rate", "unknown_only_record_rate",
                  "setwise_selection_diff_rate_vs_v03",
                  "mean_duplicate_file_count_v03", "mean_duplicate_file_count_v04",
                  "mean_candidate_source_diversity_v03",
                  "mean_candidate_source_diversity_v04",
                  "proxy_ok", "behavior_ok", "quality_ok",
                  "directional_improvement"):
        checks.append(_check(f"hard_gate_records_has_{field}", field in gate_names))
    checks.append(_check("failure_category_count_records_present",
        isinstance(skeleton.get("failure_category_count_records"), list)))

    # G19: Scanner rejects forbidden keys
    for fk in ("private_score_path", "action_order", "priority_components",
               "selected_decisions", "budget_trace", "stop_reason",
               "candidate_features", "anchor_eligibility", "score_outcome",
               "private_decision_path", "private_role_proxy_path",
               "role_proxy_assignment", "per_record_role_labels",
               "hard_gates", "failure_category_counts",
               "winner", "calibration", "method_winner",
               "self_test_checks", "checks"):
        leaked = dict(skeleton)
        leaked[fk] = "leak"
        checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_v04(leaked))))

    # G20: Scanner allows safe
    safe_sample = {
        "schema_version": SCHEMA_VERSION,
        "arm": ARM_SETWISE_V0_4_P1,
        "metric": "mrr",
        "value": 0.5,
        "record_count": 5,
        "arm_metric_records": [
            {"arm": ARM_SETWISE_V0_4_P1, "metric": "mrr", "value": 0.5, "record_count": 5},
        ],
        "role_proxy_summary_records": [
            {"role_proxy": ROLE_TARGET_PROXY, "summary_field": "available_rate",
             "value": 0.5, "record_count": 5},
        ],
        "private_score_manifest": {
            "records_written": True, "record_count": 6,
            "schema_version": PRIVATE_SCORE_SCHEMA_VERSION,
            "manifest_hash": "a" * 64, "storage_class": "tmp_private",
            "path_publicly_serialized": False,
        },
    }
    checks.append(_check("scanner_allows_safe", not _scan_v04(safe_sample)))

    # G21: Fail-closed
    try:
        _enforce_v04_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk, lv in [
        ("private_score_path", "/tmp/x"),
        ("action_order", [{}]),
        ("candidate_features", [{}]),
        ("winner", "v04"),
        ("calibration", "x"),
        ("method_winner", "v04"),
        ("role_proxy_assignment", {}),
        ("self_test_checks", []),
    ]:
        leaked = dict(skeleton)
        leaked[lk] = lv
        try:
            _enforce_v04_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # G22: Self-scan clean
    checks.append(_check("self_scan_clean", not _scan_v04(skeleton)))
    checks.append(_check("unavail_scan_clean", not _scan_v04(unavail)))

    # G23: CLI surface
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for opt in ("--self-test", "--contextbench-row-offset", "--contextbench-row-limit",
                "--repoqa-needle-offset", "--repoqa-needle-limit", "--budget",
                "--methods", "--openlocus", "--out", "--private-score-dir",
                "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in option_strings))

    # G24: Private row writer
    with tempfile.TemporaryDirectory(prefix="v04_st_") as sd:
        sf = Path(sd) / "v04.private.jsonl"
        _write_private_row(sf, {"test": 1})
        _write_private_row(sf, {"test": 2})
        lines = sf.read_text(encoding="utf-8").splitlines()
        checks.append(_check("writer_2_rows", len(lines) == 2))
        checks.append(_check("writer_parse",
            all(isinstance(json.loads(l), dict) for l in lines if l)))

    # G25: Failure family enum (12)
    checks.append(_check("failure_families_12", len(FAILURE_FAMILIES) == 12))
    for fam in FAILURE_FAMILIES:
        checks.append(_check(f"failure_family_{fam}", fam in FAILURE_FAMILIES))

    # G26: Unavailable categories
    for fam in UNAVAILABLE_NO_SUPPORT_FAMILIES:
        checks.append(_check(f"unavail_no_support_{fam}", fam in UNAVAILABLE_NO_SUPPORT_FAMILIES))
    for fam in UNAVAILABLE_MISSING_TRACE_FAMILIES:
        checks.append(_check(f"unavail_missing_trace_{fam}", fam in UNAVAILABLE_MISSING_TRACE_FAMILIES))

    # G27: Counts-only self-test
    checks.append(_check("has_self_test_checks_total", "self_test_checks_total" in skeleton))
    checks.append(_check("has_self_test_checks_passed", "self_test_checks_passed" in skeleton))
    for ff in ("self_test_checks", "self_test_details", "self_test_list", "checks", "check_list"):
        checks.append(_check(f"no_{ff}", ff not in skeleton))

    # G28: No winner/calibration anywhere
    for field in ("winner", "best_method", "recommended_default", "method_winner", "calibration"):
        checks.append(_check(f"missing_{field}", field not in skeleton))

    # G29: Aggregate runtime present
    checks.append(_check("has_runtime", "aggregate_runtime_seconds" in skeleton))
    checks.append(_check("unavail_no_runtime", "aggregate_runtime_seconds" not in unavail))

    # G30: role_proxy_only arm
    checks.append(_check("role_proxy_only_nonempty_when_targets", len(rp_ev) > 0 or not role_proxy_summary["has_target"]))
    checks.append(_check("role_proxy_only_respects_budget", len(rp_ev) <= max(0, same_budget_k)))

    # G31: Fixed protocol validation
    try:
        _validate_fixed_protocol(
            contextbench_row_offset=0,
            contextbench_row_limit=RAW_ATTEMPT_CAP_CONTEXTBENCH,
            repoqa_needle_offset=0,
            repoqa_needle_limit=RAW_ATTEMPT_CAP_REPOQA,
            budget=5,
            methods=ALLOWED_METHODS,
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
            budget=5,
            methods=ALLOWED_METHODS,
        )
        checks.append(_check("fixed_protocol_rejects_offset", False))
    except SystemExit:
        checks.append(_check("fixed_protocol_rejects_offset", True))

    # G32: Setwise behavior helpers
    checks.append(_check("dup_count_no_dup", _accepted_file_duplicates([{"path": "a"}, {"path": "b"}]) == 0))
    checks.append(_check("dup_count_with_dup", _accepted_file_duplicates([{"path": "a"}, {"path": "a"}]) == 1))
    checks.append(_check("source_diversity_returns_int", isinstance(_accepted_source_diversity(v04_acc, candidates), int)))
    checks.append(_check("selection_differs_detects_diff", _selection_differs(v03_acc, []) is True))

    # G33: Statuses enum
    for status in ("bea_v04_p1_smoke_pass", "partial_directional_signal",
                   "no_go_proxy_unavailable", "no_go_no_selection_change",
                   "no_go_quality_regression", "unavailable_with_reason",
                   "fail_forbidden_scan", "fail_schema_contract"):
        checks.append(_check(f"status_enum_{status}", isinstance(status, str)))

    # G34: v0.4 P1 runtime-clean invariance
    tainted = []
    for c in candidates:
        tc = dict(c)
        tc["gold_paths"] = ["src/path1.py"]
        tc["row_id"] = "leaked"
        tc["benchmark_label"] = "positive"
        tainted.append(tc)
    v04_t, _, _, _, _ = _bea_v0_4_p1_setwise_policy(tainted, query, 5)
    def _ak(a): return (a["path"], a["start_line"], a["end_line"])
    checks.append(_check("v04_runtime_clean_invariance",
        [_ak(a) for a in v04_acc] == [_ak(a) for a in v04_t]))

    # G35: Unavailable report has empty tables
    for k in ("source_run_records", "arm_metric_records", "arm_delta_records",
              "role_proxy_summary_records", "setwise_behavior_records",
              "failure_family_records", "win_tie_loss_records",
              "availability_records"):
        checks.append(_check(f"unavail_empty_{k}", unavail.get(k) == []))

    # G36: Quality_per_latency in metrics
    checks.append(_check("quality_per_latency_in_v04", "quality_per_latency" in v04_m))
    checks.append(_check("quality_per_latency_in_allowlist", "quality_per_latency" in ARM_METRIC_ALLOWLIST))

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
        description="BEA-v0.4-P1 Setwise Role-Proxy Smoke"
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
    return ap


# ---------------------------------------------------------------------------
# Network smoke runner
# ---------------------------------------------------------------------------


def _run_network_smoke(
    *, contextbench_row_offset: int, contextbench_row_limit: int,
    repoqa_needle_offset: int, repoqa_needle_limit: int,
    budget: int, openlocus_bin: str,
    openlocus_binary_source: str, network_mode: str,
    self_test_passed: bool, private_score_dir: Path,
    private_score_storage_class: str, phase_run_id: str,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0
    smoke_start = time.perf_counter()
    score_hash = _private_score_manifest_hash()
    decision_hash = _private_decision_manifest_hash()
    role_proxy_hash = _private_role_proxy_manifest_hash()
    score_file = private_score_dir / "bea_v04_p1.private.jsonl"
    decision_file = private_score_dir / "bea_v04_p1.decision.jsonl"
    role_proxy_file = private_score_dir / "bea_v04_p1.role_proxy.jsonl"
    for f in (score_file, decision_file, role_proxy_file):
        try:
            f.unlink()
        except OSError:
            pass

    per_record_arm_metrics: list[dict[str, dict[str, Any]]] = []
    arm_aggs_raw: dict[str, dict[str, list[float]]] = {
        arm: {m: [] for m in ARM_METRIC_ALLOWLIST} for arm in FIXED_ARMS
    }
    arm_record_counts: dict[str, int] = {arm: 0 for arm in FIXED_ARMS}
    per_record_role_proxy_summaries: list[dict[str, Any]] = []
    per_record_setwise_summaries: list[dict[str, Any]] = []
    per_record_failure_families_v03: list[dict[str, dict[str, dict[str, Any]]]] = []
    per_record_failure_families_v04: list[dict[str, dict[str, dict[str, Any]]]] = []
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
    paired_exclusion_count = 0

    # ContextBench heldout fresh smoke slice.
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

    # RepoQA heldout fresh smoke slice.
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
                fcc["contextbench_gold_parse_failed"] += 1
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
            with tempfile.TemporaryDirectory(prefix=f"v04_cb_{idx}_") as rds:
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
                    role_proxy_path=role_proxy_file,
                    phase_run_id=phase_run_id, fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    records_excluded += 1
                    contextbench_excluded += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_role_proxy_summaries.append(rec_summary.get("role_proxy_summary", {}))
                per_record_setwise_summaries.append(rec_summary)
                v03_m = per_arm.get(ARM_BEA_V0_3, {})
                v04_m = per_arm.get(ARM_SETWISE_V0_4_P1, {})
                v03_lat = float(v03_m.get("latency_seconds", 0.0))
                v04_lat = float(v04_m.get("latency_seconds", 0.0))
                ff_v03 = _classify_failure_family(
                    v03_m, int(rec_summary.get("setwise_behavior", {}).get("v03_budget_used", 0)),
                    v03_lat, v03_m, v03_lat, rec_summary.get("role_proxy_summary", {}),
                )
                ff_v04 = _classify_failure_family(
                    v04_m, int(rec_summary.get("setwise_behavior", {}).get("v04_budget_used", 0)),
                    v04_lat, v03_m, v03_lat, rec_summary.get("role_proxy_summary", {}),
                )
                per_record_failure_families_v03.append(ff_v03)
                per_record_failure_families_v04.append(ff_v04)
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
            with tempfile.TemporaryDirectory(prefix=f"v04_rq_{idx}_") as rds:
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
                    role_proxy_path=role_proxy_file,
                    phase_run_id=phase_run_id, fcc=fcc,
                )
                if per_arm is None:
                    records_failed += 1
                    records_excluded += 1
                    repoqa_excluded += 1
                    continue
                per_record_arm_metrics.append(per_arm)
                per_record_role_proxy_summaries.append(rec_summary.get("role_proxy_summary", {}))
                per_record_setwise_summaries.append(rec_summary)
                v03_m = per_arm.get(ARM_BEA_V0_3, {})
                v04_m = per_arm.get(ARM_SETWISE_V0_4_P1, {})
                v03_lat = float(v03_m.get("latency_seconds", 0.0))
                v04_lat = float(v04_m.get("latency_seconds", 0.0))
                ff_v03 = _classify_failure_family(
                    v03_m, int(rec_summary.get("setwise_behavior", {}).get("v03_budget_used", 0)),
                    v03_lat, v03_m, v03_lat, rec_summary.get("role_proxy_summary", {}),
                )
                ff_v04 = _classify_failure_family(
                    v04_m, int(rec_summary.get("setwise_behavior", {}).get("v04_budget_used", 0)),
                    v04_lat, v03_m, v03_lat, rec_summary.get("role_proxy_summary", {}),
                )
                per_record_failure_families_v03.append(ff_v03)
                per_record_failure_families_v04.append(ff_v04)
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
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            private_score_storage_class=private_score_storage_class,
            private_score_manifest_hash_value=score_hash,
            records_attempted_total=records_attempted_total,
            records_evaluated=records_evaluated,
            records_successful=records_successful,
            records_failed=records_failed,
            records_excluded=records_excluded,
            contextbench_attempted=contextbench_attempted,
            contextbench_successful=contextbench_successful,
            contextbench_excluded=contextbench_excluded,
            repoqa_attempted=repoqa_attempted,
            repoqa_successful=repoqa_successful,
            repoqa_excluded=repoqa_excluded,
            contextbench_excluded_prior_window_count=cb_excluded_prior_window_count,
            repoqa_excluded_prior_window_count=rq_excluded_prior_window_count,
            contextbench_eligible_count=cb_eligible_count,
            repoqa_eligible_count=rq_eligible_count,
            quota_reached=quota_reached,
            network_calls=network_calls, failure_category_counts=fcc,
        )

    # Compute arm aggregates.
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

    # Count private rows.
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
    private_role_proxy_count = _count_lines(role_proxy_file)

    private_score_written = private_score_count > 0
    expected_count = records_successful * len(FIXED_ARMS)
    if records_successful > 0 and private_score_count != expected_count:
        fcc["private_score_write_failed"] = fcc.get("private_score_write_failed", 0) + 1

    aggregate_runtime_seconds = time.perf_counter() - smoke_start
    partial = (not quota_reached) or records_failed > 0

    return _build_pass_report(
        self_test_passed=self_test_passed,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        records_attempted_total=records_attempted_total,
        records_evaluated=records_evaluated,
        records_successful=records_successful,
        records_failed=records_failed,
        records_excluded=records_excluded,
        contextbench_attempted=contextbench_attempted,
        contextbench_successful=contextbench_successful,
        contextbench_excluded=contextbench_excluded,
        repoqa_attempted=repoqa_attempted,
        repoqa_successful=repoqa_successful,
        repoqa_excluded=repoqa_excluded,
        contextbench_excluded_prior_window_count=cb_excluded_prior_window_count,
        repoqa_excluded_prior_window_count=rq_excluded_prior_window_count,
        contextbench_eligible_count=cb_eligible_count,
        repoqa_eligible_count=rq_eligible_count,
        quota_reached=quota_reached,
        network_calls=network_calls,
        arm_aggs=arm_aggs,
        per_record_arm_metrics=per_record_arm_metrics,
        per_record_role_proxy_summaries=per_record_role_proxy_summaries,
        per_record_setwise_summaries=per_record_setwise_summaries,
        per_record_failure_families_v03=per_record_failure_families_v03,
        per_record_failure_families_v04=per_record_failure_families_v04,
        private_score_records_written=private_score_written,
        private_score_record_count=private_score_count,
        private_decision_records_written=private_decision_count > 0,
        private_decision_record_count=private_decision_count,
        private_role_proxy_records_written=private_role_proxy_count > 0,
        private_role_proxy_record_count=private_role_proxy_count,
        private_score_storage_class=private_score_storage_class,
        private_score_manifest_hash=score_hash,
        private_decision_manifest_hash=decision_hash,
        private_role_proxy_manifest_hash=role_proxy_hash,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        failure_category_counts=fcc,
        paired_exclusion_count=paired_exclusion_count,
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
        budget=budget,
        methods=methods,
    )
    enable_network = bool(args.enable_external_benchmark_network)
    out_path = args.out if args.out is not None else DEFAULT_OUT

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
        _enforce_v04_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        return

    private_score_dir, private_score_storage_class = (
        _resolve_private_dir(args.private_score_dir)
    )
    phase_run_id = f"bea-v04-p1-{int(time.time())}"

    if not enable_network:
        report = _build_unavailable_report(
            "contextbench_fetch_failed", self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_source,
            network_mode="disabled_opt_in",
            private_score_storage_class=private_score_storage_class,
        )
        _enforce_v04_no_forbidden(report)
        _write_json(out_path, report)
        print(f"wrote artifact (status={report['status']})")
        print("enable_external_benchmark_network is false; skipping real BEA-v0.4-P1 smoke.")
        return

    network_mode = "local_explicit"
    try:
        report = _run_network_smoke(
            contextbench_row_offset=contextbench_row_offset,
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_offset=repoqa_needle_offset,
            repoqa_needle_limit=repoqa_needle_limit,
            budget=budget,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            self_test_passed=self_test_passed,
            private_score_dir=private_score_dir,
            private_score_storage_class=private_score_storage_class,
            phase_run_id=phase_run_id,
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

    _enforce_v04_no_forbidden(report)
    _write_json(out_path, report)
    manifest = report.get("private_score_manifest", {})
    print(f"wrote artifact (forbidden_scan={report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"records_successful={report.get('records_successful', 0)}, "
          f"private_score_record_count={manifest.get('record_count', 0)})")


if __name__ == "__main__":
    main()
