#!/usr/bin/env python3
"""BEA-v1-P1: FD1 Actionability and Oracle Ceiling Audit (Public Records-Only).

BEA-v1-P1 is the **first phase of BEA v1 Hierarchical Actionable Evidence
Acquisition**. It is *not* BEA v0.4 repair, not a selector / acquisition
phase, not FD2-B / FD2-C, not P4 / P5, not v0.31 / v0.32 tuning, not
B16-K, and not a re-run of FD2-A1.

Binding context:

* FD2-A1 result checkpoint ``b2aabf5``: FD2-A failed because the
  ``latency_category_non_actionable_or_dominating`` bucket dominated
  38/38 regressed records while candidate availability was not limiting.
* The user explicitly switched mainline to BEA v1 Hierarchical
  Actionable Evidence Acquisition. BEA-v1-P1 is the actionability audit
  that must run before any v1-A coverage-preserving selector work.
* BEA-v1-P1 audits the **full FD1 239-record frame** (not the FD2-A1
  38-record frame). It is an empirical audit over the committed FD1
  public aggregate, not a schema-only artifact.

Goal
----

Map each of the 12 FD1 failure categories to the BEA v1 action layer that
can causally affect it, and compute honest oracle ceilings where the
committed FD1 public aggregate permits. Action layers (6):

1. ``candidate_availability_retrieval``
2. ``file_selector``
3. ``span_refiner``
4. ``setwise_packer_redundancy``
5. ``stopping_scheduler``
6. ``non_actionable_accounting``

Each ``(failure_category, action_layer)`` cell is one of:

* ``direct_actionable`` — layer is the primary fix point
* ``indirect_actionable`` — layer can partially address the category
* ``not_actionable_by_layer`` — layer cannot causally affect the category
* ``candidate_unavailable`` — category carries no candidate-level labels
  (FD1 ``unavailable_no_support_label``); ceiling cannot be evaluated
* ``ceiling_unavailable_insufficient_trace`` — category trace is
  insufficient (FD1 ``unavailable_missing_trace``); ceiling cannot be
  evaluated

Oracle ceilings (honest, never inferred from aggregate latency):

* ``file_selector`` — **required**, and **requires FD1 private
  decomposition replay** to authorize v1-A. The FD1 public aggregate
  alone only yields an upper bound (denominator = records where
  ``gold_file_absent==1``); it cannot bound the recoverable loss from
  below because candidate-pool overlap is not in the public aggregate.
  BEA-v1-P1 therefore parses the deterministic FD1 private decomposition
  JSONL (regenerated under ``/tmp`` by ``bea_fd1_failure_decomposition``
  with ``--private-decomposition-dir``) to compute a real lower bound:
  for each ``gold_file_absent`` record, if ANY baseline arm selected a
  correct file (``baseline_value`` for ``file_recall@10`` > 0), that
  record is recoverable (the gold file was in the candidate pool).
  ``ceiling_class =
  computed_private_lower_bound_and_public_upper_bound``;
  ``ceiling_basis = fd1_private_decomposition_replay``. If no private
  JSONL is supplied, status is ``no_go_ceiling_unavailable`` and
  ``stop_go_decision = needs_fd1_private_replay_before_v1_a`` — the
  public aggregate upper bound is explicitly insufficient to authorize
  v1-A.
* ``span_refiner`` — computed only if candidate/gold span overlap fields
  exist; otherwise explicit ``unavailable_ceiling_records`` row. FD1 has
  no per-record span-overlap fields → unavailable.
* ``setwise_packer_redundancy`` (redundancy / marginal utility) —
  computed only if duplicate/file grouping fields exist. FD1 marks
  ``redundant_same_file_candidates`` as ``unavailable_missing_trace`` →
  unavailable.
* ``stopping_scheduler`` — computed only if ordered-prefix
  utility/latency exists. FD1 has aggregate latency loss per category
  but no ordered-prefix trace → unavailable. The plan forbids inferring
  stopping ceilings from aggregate latency.

Binding invariants
-----------------

* claim_level = ``bea_v1_p1_actionability_audit_only``
* status: ``bea_v1_p1_actionability_audit_pass`` |
  ``no_go_no_file_selector_ceiling`` |
  ``no_go_retrieval_availability_limit`` |
  ``no_go_span_or_stopping_dominates`` |
  ``no_go_ceiling_unavailable`` |
  ``unavailable_with_reason`` | ``fail_forbidden_scan`` |
  ``fail_schema_contract``
* mode = ``bea_v1_p1_actionability_audit``; phase = ``BEA-v1-P1``

* Eval-local only. The committed FD1 public aggregate is a read-only
  input. The committed FD2-A1 artifact is read-only binding context.
  BEA-v1-P1 does NOT rerun FD1, does NOT rerun FD2-A1, does NOT execute
  any selector / retrieval / provider call, and does NOT modify any
  committed artifact.
* No v0.4 role proxies, no weight tuning, no new records, no heldout
  validation, no per-repo tuning, no gold/private labels during
  selection, no provider/LLM calls.
* Public artifact is aggregate-only and records-only. No public record
  IDs, paths, queries, snippets, spans, candidate keys, selected order,
  private trace paths, or private row payloads.

Network / CI policy (binding)
----------------------------

* Default no-network self-test passes without HuggingFace/GitHub and
  without the committed FD1 / FD2-A1 artifacts or any private JSONL
  (self-test uses a synthetic FD1 aggregate and synthetic private rows).
* Default no-network / no-private-JSONL artifact is truthfully
  ``no_go_ceiling_unavailable`` with
  ``stop_go_decision = needs_fd1_private_replay_before_v1_a``
  (no fake pass). To authorize v1-A, the audit must be run with a
  regenerated FD1 private decomposition JSONL produced by
  ``bea_fd1_failure_decomposition --enable-external-benchmark-network
  --private-decomposition-dir <tmp>``.
* CI is a separate explicit workflow_dispatch job; it must NOT run on
  PR/push by default, must use no provider secrets/vars/model env, and
  must upload only the aggregate report. The CI workflow regenerates
  the FD1 private decomposition under ``$RUNNER_TEMP`` before running
  the audit; the private JSONL is NEVER uploaded.

Run::

    python3 -m py_compile eval/bea_v1_p1_actionability_audit.py
    python3 eval/bea_v1_p1_actionability_audit.py --self-test
    python3 eval/bea_v1_p1_actionability_audit.py \\
        --out artifacts/bea_v1_p1_actionability_audit/\\
bea_v1_p1_actionability_audit_report.json

To authorize v1-A, the audit must be run with a regenerated FD1 private
decomposition JSONL::

    python3 eval/bea_fd1_failure_decomposition.py \\
        --enable-external-benchmark-network \\
        --private-decomposition-dir /tmp/fd1_private \\
        --out /tmp/fd1_replay_report.json
    python3 eval/bea_v1_p1_actionability_audit.py \\
        --fd1-private-decomposition-jsonl /tmp/fd1_private/bea_fd1.decomposition.jsonl \\
        --out artifacts/bea_v1_p1_actionability_audit/bea_v1_p1_actionability_audit_report.json

Without ``--fd1-private-decomposition-jsonl`` the default artifact is
honestly ``no_go_ceiling_unavailable`` with
``stop_go_decision = needs_fd1_private_replay_before_v1_a`` (NOT a fake
pass).
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

# Reuse the FD1 evaluator (scanner composition, schema constants,
# category enum, no-support / missing-trace category sets) and the c5a
# helpers (now_iso / write_json / check). BEA-v1-P1 does NOT import any
# BEA-v0.4-P1/P2/P3 module, does NOT import FD2-A / FD2-A1 evaluators
# (FD2-A1 result is read-only binding context only via committed
# artifact), and does NOT use role proxies.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import bea_fd1_failure_decomposition as bea_fd1  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402

# --- Schema / claim constants ---
SCHEMA_VERSION = "bea_v1_p1_actionability_audit.v1"
GENERATED_BY = "eval/bea_v1_p1_actionability_audit.py"
CLAIM_LEVEL = "bea_v1_p1_actionability_audit_only"
MODE = "bea_v1_p1_actionability_audit"
PHASE = "BEA-v1-P1"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_p1_actionability_audit/"
    "bea_v1_p1_actionability_audit_report.json"
)
DEFAULT_FD1_ARTIFACT = bea_fd1.DEFAULT_OUT
DEFAULT_FD2A1_ARTIFACT = Path(
    "artifacts/bea_fd2a1_failure_attribution/"
    "bea_fd2a1_failure_attribution_replay_report.json"
)

# --- FD1 source binding context (read-only) ---
# FD1 manual CI run committed the 239-record decomposition artifact.
FD1_SOURCE_CI_RUN_ID = "28011901294"
FD1_SOURCE_LOCAL_CHECKPOINT = "29c5a1a"
FD1_SOURCE_STATUS = "bea_fd1_decomposition_pass"
FD1_SOURCE_SCHEMA_VERSION = bea_fd1.SCHEMA_VERSION
# FD2-A1 result checkpoint is the immediate predecessor of BEA-v1-P1.
FD2A1_RESULT_CHECKPOINT = "b2aabf5"
FD2A1_RESULT_STATUS = "bea_fd2a1_attribution_replay_pass"
FD2A1_SOURCE_SCHEMA_VERSION = "bea_fd2a1_failure_attribution_replay.v1"

# Fixed budget / methods inherited from FD1 (audit does not change them).
FIXED_BUDGET = bea_fd1.FIXED_BUDGET
FIXED_METHODS = tuple(bea_fd1.FIXED_METHODS.split(","))

# FD1 frame expectations (binding).
EXPECTED_RECORDS_DECOMPOSED = bea_fd1.EXPECTED_DECOMPOSED_RECORDS  # 239
EXPECTED_PRIVATE_DECOMP_ROWS = bea_fd1.EXPECTED_PRIVATE_DECOMP_ROWS  # 86040

# --- Action layers (6) ---
ACTION_LAYERS = (
    "candidate_availability_retrieval",
    "file_selector",
    "span_refiner",
    "setwise_packer_redundancy",
    "stopping_scheduler",
    "non_actionable_accounting",
)

# --- Cell classes (5) ---
CELL_CLASSES = (
    "direct_actionable",
    "indirect_actionable",
    "not_actionable_by_layer",
    "candidate_unavailable",
    "ceiling_unavailable_insufficient_trace",
)

# FD1 categories (12) — imported from bea_fd1.
FAILURE_CATEGORIES: tuple[str, ...] = bea_fd1.FAILURE_CATEGORIES

# Categories whose FD1 availability is "unavailable_no_support_label" —
# the candidate-level support/target labels needed to evaluate
# actionability are not present in FD1. All cells in these rows are
# ``candidate_unavailable``.
CANDIDATE_UNAVAILABLE_CATEGORIES = frozenset(
    bea_fd1.UNAVAILABLE_NO_SUPPORT_CATEGORIES
)
# Categories whose FD1 availability is "unavailable_missing_trace" —
# the per-record trace needed to compute a ceiling is missing in FD1.
# All cells in these rows are ``ceiling_unavailable_insufficient_trace``.
# We extend the FD1 frozenset with ``redundant_same_file_candidates``
# because the FD1 evaluator marks that category as
# ``unavailable_missing_trace`` in its published availability_records
# (see ``_classify_from_private_rows`` in bea_fd1), even though the
# frozenset constant in bea_fd1 only lists ``risk_penalty_removed_gold``.
CEILING_UNAVAILABLE_CATEGORIES = frozenset(
    bea_fd1.UNAVAILABLE_MISSING_TRACE_CATEGORIES
    | {"redundant_same_file_candidates"}
)

# Available categories (actionability matrix mapping applies).
AVAILABLE_CATEGORIES = tuple(
    c for c in FAILURE_CATEGORIES
    if c not in CANDIDATE_UNAVAILABLE_CATEGORIES
    and c not in CEILING_UNAVAILABLE_CATEGORIES
)

# --- Actionability matrix (category, layer) -> cell_class ---
# Built only for AVAILABLE categories. For unavailable categories the
# row is filled uniformly with candidate_unavailable or
# ceiling_unavailable_insufficient_trace (see _build_actionability_matrix).
ACTIONABILITY_MATRIX: dict[tuple[str, str], str] = {
    # gold_file_absent: gold file absent from selected set.
    ("gold_file_absent", "candidate_availability_retrieval"):
        "candidate_unavailable",  # gold absent == retrieval layer cannot
        # recover; this cell marks the retrieval-limit case.
    ("gold_file_absent", "file_selector"):
        "direct_actionable",  # selector chose wrong files; if gold is
        # in the candidate pool, a perfect selector recovers it.
    ("gold_file_absent", "span_refiner"):
        "not_actionable_by_layer",  # file absent → span layer cannot help
    ("gold_file_absent", "setwise_packer_redundancy"):
        "not_actionable_by_layer",
    ("gold_file_absent", "stopping_scheduler"):
        "not_actionable_by_layer",
    ("gold_file_absent", "non_actionable_accounting"):
        "indirect_actionable",

    # gold_span_absent: file hit, span==0 (gold span not present).
    ("gold_span_absent", "candidate_availability_retrieval"):
        "not_actionable_by_layer",
    ("gold_span_absent", "file_selector"):
        "indirect_actionable",
    ("gold_span_absent", "span_refiner"):
        "direct_actionable",  # span layer can pick correct span
    ("gold_span_absent", "setwise_packer_redundancy"):
        "not_actionable_by_layer",
    ("gold_span_absent", "stopping_scheduler"):
        "not_actionable_by_layer",
    ("gold_span_absent", "non_actionable_accounting"):
        "indirect_actionable",

    # correct_file_wrong_span: file hit, span==0 (selected wrong span).
    ("correct_file_wrong_span", "candidate_availability_retrieval"):
        "not_actionable_by_layer",
    ("correct_file_wrong_span", "file_selector"):
        "indirect_actionable",
    ("correct_file_wrong_span", "span_refiner"):
        "direct_actionable",
    ("correct_file_wrong_span", "setwise_packer_redundancy"):
        "not_actionable_by_layer",
    ("correct_file_wrong_span", "stopping_scheduler"):
        "not_actionable_by_layer",
    ("correct_file_wrong_span", "non_actionable_accounting"):
        "indirect_actionable",

    # redundant_same_file_candidates: trace unavailable in FD1 — row is
    # ceiling_unavailable_insufficient_trace (handled in matrix builder).

    # too_many_anchor_slots: anchor selection over-allocated.
    ("too_many_anchor_slots", "candidate_availability_retrieval"):
        "not_actionable_by_layer",
    ("too_many_anchor_slots", "file_selector"):
        "indirect_actionable",
    ("too_many_anchor_slots", "span_refiner"):
        "direct_actionable",  # anchor selection lives in span layer
    ("too_many_anchor_slots", "setwise_packer_redundancy"):
        "indirect_actionable",
    ("too_many_anchor_slots", "stopping_scheduler"):
        "not_actionable_by_layer",
    ("too_many_anchor_slots", "non_actionable_accounting"):
        "indirect_actionable",

    # missing_support_candidate: no support candidate in pool — row is
    # candidate_unavailable (handled in matrix builder).

    # support_selected_without_target: row is candidate_unavailable.

    # target_selected_without_support: row is candidate_unavailable.

    # risk_penalty_removed_gold: trace unavailable in FD1 — row is
    # ceiling_unavailable_insufficient_trace (handled in builder).

    # early_stop_too_early: stop fired too early relative to baseline.
    ("early_stop_too_early", "candidate_availability_retrieval"):
        "not_actionable_by_layer",
    ("early_stop_too_early", "file_selector"):
        "not_actionable_by_layer",
    ("early_stop_too_early", "span_refiner"):
        "not_actionable_by_layer",
    ("early_stop_too_early", "setwise_packer_redundancy"):
        "indirect_actionable",
    ("early_stop_too_early", "stopping_scheduler"):
        "direct_actionable",  # stopping layer controls early stop
    ("early_stop_too_early", "non_actionable_accounting"):
        "indirect_actionable",

    # budget_spent_on_low_marginal_gain: full budget spent, no quality
    # gain over baseline.
    ("budget_spent_on_low_marginal_gain", "candidate_availability_retrieval"):
        "not_actionable_by_layer",
    ("budget_spent_on_low_marginal_gain", "file_selector"):
        "indirect_actionable",
    ("budget_spent_on_low_marginal_gain", "span_refiner"):
        "not_actionable_by_layer",
    ("budget_spent_on_low_marginal_gain", "setwise_packer_redundancy"):
        "direct_actionable",  # marginal-utility packing controls budget
    ("budget_spent_on_low_marginal_gain", "stopping_scheduler"):
        "indirect_actionable",  # stopping can cap budget
    ("budget_spent_on_low_marginal_gain", "non_actionable_accounting"):
        "indirect_actionable",

    # latency_without_quality_gain: v0.3 latency > baseline and quality
    # delta <= 0 — non-actionable by candidate-level proxy during
    # selection (this is the FD2-A1-dominating bucket).
    ("latency_without_quality_gain", "candidate_availability_retrieval"):
        "not_actionable_by_layer",
    ("latency_without_quality_gain", "file_selector"):
        "indirect_actionable",  # selector can choose less-latency files
    ("latency_without_quality_gain", "span_refiner"):
        "not_actionable_by_layer",
    ("latency_without_quality_gain", "setwise_packer_redundancy"):
        "indirect_actionable",
    ("latency_without_quality_gain", "stopping_scheduler"):
        "indirect_actionable",
    ("latency_without_quality_gain", "non_actionable_accounting"):
        "direct_actionable",  # latency category is not actionable by
        # candidate-level proxy during selection — it must be accounted
        # for separately, not folded into selection loss.
}

# --- Oracle ceiling names ---
CEILING_NAMES = (
    "file_selector",
    "span_refiner",
    "setwise_packer_redundancy",
    "stopping_scheduler",
)
# Required ceiling: must be attempted (status No-Go if unavailable).
REQUIRED_CEILING = "file_selector"

# --- Stop / go thresholds (binding; mirror plan stop rules) ---
# File-selector actionable loss mass must be material to proceed to v1-A.
GO_FILE_SELECTOR_UPSIDE_RATE_MIN = 0.05  # >=5% upper-bound recoverable
# Retrieval availability must not dominate the recoverable ceiling.
NO_GO_RETRIEVAL_AVAILABILITY_RATE = 0.50  # if >50% of gold_file_absent
# cells are retrieval-limited (candidate_unavailable in the matrix),
# the audit No-Gos to retrieval layer.
# Span / stopping dominance: if span_refiner or stopping_scheduler
# actionable categories (direct_actionable) hold > SPAN_OR_STOPPING_DOMINANCE_RATE
# of available loss mass AND no file-selector ceiling was computed,
# status is no_go_span_or_stopping_dominates.
SPAN_OR_STOPPING_DOMINANCE_RATE = 0.50

# --- Statuses enum (binding) ---
STATUSES = (
    "bea_v1_p1_actionability_audit_pass",
    "no_go_no_file_selector_ceiling",
    "no_go_retrieval_availability_limit",
    "no_go_span_or_stopping_dominates",
    "no_go_ceiling_unavailable",
    "unavailable_with_reason",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
ALLOWED_REAL_RUN_STATUSES = frozenset({
    "bea_v1_p1_actionability_audit_pass",
    "no_go_no_file_selector_ceiling",
    "no_go_retrieval_availability_limit",
    "no_go_span_or_stopping_dominates",
    "no_go_ceiling_unavailable",
})

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
    "fd1_artifact_read": False,
    "fd2a1_artifact_read": False,
    "fd1_artifact_modified": False,
    "fd2a1_artifact_modified": False,
    "bea_v1_p1_audit_performed": False,
    "bea_v1_p1_actionability_matrix_built": False,
    "bea_v1_p1_oracle_ceiling_attempted": False,
    "fd1_private_decomposition_parsed": False,
    "fd1_private_decomposition_lower_bound_computed": False,
    # The v1 audit EVALUATOR itself never runs retrieval / selector /
    # replay / provider calls. The CI workflow may regenerate the FD1
    # private decomposition under temp storage before invoking the
    # evaluator; that is tracked by the explicit replay flags below,
    # NOT by this flag. Renamed from the ambiguous
    # ``bea_v1_p1_no_replay_executed`` after @oracle second No-Go.
    "bea_v1_p1_audit_evaluator_no_replay_executed": True,
    "bea_v1_p1_audit_evaluator_no_selector_executed": True,
    "bea_v1_p1_audit_evaluator_no_retrieval_executed": True,
    "bea_v1_p1_audit_evaluator_no_provider_calls": True,
    "bea_v1_p1_audit_evaluator_no_weight_tuning": True,
    "bea_v1_p1_audit_evaluator_no_role_proxy": True,
    # Explicit FD1 private decomposition replay provenance flags. For
    # the local default / no-private artifact these are all false
    # except supplied=false. For the real workflow report, supplied and
    # validated are true; workflow-executed is true when a validated
    # replay artifact is present.
    "fd1_private_decomposition_replay_supplied": False,
    "fd1_private_decomposition_replay_validated": False,
    "fd1_private_decomposition_replay_executed_by_workflow": False,
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
    "algorithm_changed_during_bea_v1_p1": False,
    "weights_tuned_during_bea_v1_p1": False,
    "v04_full_matrix_claimed": False,
    "v03_tuned_during_bea_v1_p1": False,
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
    "new_records_added_during_bea_v1_p1": False,
    "heldout_validation_claimed": False,
}

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_actionability_audit",
}

# Audit-level failure categories (NOT the FD1 categories).
FAILURE_CATEGORIES_AUDIT = (
    "fd1_artifact_missing", "fd1_artifact_parse_failed",
    "fd1_schema_version_mismatch", "fd1_status_mismatch",
    "fd1_records_decomposed_mismatch", "fd1_private_manifest_mismatch",
    "fd1_availability_table_missing", "fd1_category_summary_missing",
    "fd2a1_artifact_missing", "fd2a1_artifact_parse_failed",
    "fd2a1_status_mismatch",
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
    "scanner_self_test_failed", "forbidden_leak_blocked",
    "duplicate_record_key_blocked",
    "unexpected_exception",
)
BLOCKING_FAILURE_CATEGORIES = (
    "forbidden_leak_blocked", "unexpected_exception",
    "fd1_artifact_missing", "fd1_artifact_parse_failed",
)

# ---------------------------------------------------------------------------
# Scanner (strict, fail-closed). Composes the FD1 scanner; adds
# BEA-v1-P1-specific audit-private rejections.
# ---------------------------------------------------------------------------

# BEA-v1-P1 forbidden extra top-level keys (audit-private / per-record /
# claim / dynamic-dict mirrors / forbidden scope). Inherits the full
# FD1 forbidden-key discipline via ``bea_fd1._scan_fd1``.
V1_P1_FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        # private trace paths / dirs (BEA-v1-P1 must not serialize them)
        "private_trace_dir", "trace_dir", "private_score_dir",
        "private_audit_dir", "audit_trace_path",
        "private_decomposition_dir",
        "private_decomposition_path", "private_decomposition_file",
        # per-record audit detail (aggregate counts only)
        "per_record_buckets", "per_record_attribution",
        "record_bucket_assignment", "record_attribution_detail",
        "record_bucket_list", "attribution_records",
        "per_record_regressions", "record_regressions",
        "per_record_actionability", "per_record_matrix",
        # private / per-record candidate / query / path / span / snippet
        "candidate_paths", "candidate_keys", "query_text", "queries",
        "gold_paths", "gold_lines", "gold_spans", "gold_content",
        "snippets", "selected_paths", "selected_order",
        "private_record_ids", "record_ids", "private_record_id",
        "benchmark_row_id", "phase_run_id", "run_id",
        "task_id", "row_id", "needle_id", "instance_id",
        # objective-config / weights / raw trace payloads (audit-private)
        "objective_config_payload", "fd1_category_weights_payload",
        "weight_derivation_payload", "frozen_weights_payload",
        "raw_score_row", "raw_decision_row",
        "raw_feature_row", "raw_decomposition_row",
        # FD1 / FD2-A1 source artifact paths (private; only hash/schema)
        "fd1_source_artifact_path", "fd2a1_source_artifact_path",
        "fd2a_source_artifact_path",
        # claim / promotion (BEA-v1-P1 is audit only)
        "recommended_default", "recommended_method", "preferred_method",
        "default_method", "policy_decision", "decision", "ranking",
        "rank", "winner", "leaderboard", "promotion", "calibration",
        "method_winner", "best_method",
        # self-test details (counts only)
        "self_test_checks", "self_test_details", "self_test_list",
        "checks", "check_list",
        # dynamic dict mirrors (forbidden as top-level; records-only)
        "hard_gates", "failure_category_counts",
        "actionability_matrix_counts", "oracle_ceiling_counts",
        "candidate_availability_counts", "unavailable_ceiling_counts",
        "redundancy_tradeoff_counts", "stop_go_counts",
        # forbidden scope flags (BEA-v1-P1 is NOT these)
        "is_v04_repair", "is_fd2_b", "is_fd2_c", "is_p4", "is_p5",
        "is_v031_tuning", "is_v032_tuning", "is_b16k",
        "is_selector_phase", "is_acquisition_phase",
        "role_proxy", "role_proxy_assignment", "target_proxy",
        "support_proxy", "target_anchor", "target_support_pair",
        "role_proxy_used", "target_support_proxy_used",
    }
)

# Container keys whose record rows may legitimately carry a key that is
# forbidden as a top-level field (records-only discipline).
V1_P1_CONTAINER_KEYS = frozenset({
    "source_run_records", "failure_category_records",
    "actionability_matrix_records", "oracle_ceiling_records",
    "candidate_availability_records", "unavailable_ceiling_records",
    "redundancy_tradeoff_records", "stop_go_records",
    "gate_records", "private_manifest_records",
    "failure_category_count_records", "framing",
    # FD1-inherited containers (when echoing read-only FD1 records)
    "availability_records", "category_summary_records",
    "bucket_category_records", "candidate_source_category_records",
})


def _is_v1_p1_schema_key_container(path: str) -> bool:
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in V1_P1_CONTAINER_KEYS


def _scan_v1_p1_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_container = _is_v1_p1_schema_key_container(sub_path)
                if (key_str in V1_P1_FORBIDDEN_EXTRA_KEYS
                        and not is_container):
                    violations.append({
                        "category": "forbidden_v1_p1_extra_key",
                        "path": sub_path,
                    })
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


# BEA-v1-P1-specific safe VALUE path last-key segments. These keys MAY
# hold long policy strings or 64-char hex artifact hashes without
# triggering the primitive long_string / hex_digest_value checks.
V1_P1_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
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
        "treatment_arm", "baseline_arm",
        "fd1_overlap_policy", "fd1_source_overlap_policy",
        "excluded_prior_windows_policy",
    }
)


def _v1_p1_safe_value_path(path: str) -> bool:
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in V1_P1_SAFE_VALUE_PATH_LAST_KEYS


def _scan_v1_p1(obj: Any) -> list[dict[str, Any]]:
    # Compose with the FD1 scanner (which composes BEA-5/BEA-3), then
    # add BEA-v1-P1-specific rejections. Filter primitive false
    # positives for BEA-v1-P1-safe value paths (policy strings,
    # artifact hashes, reason strings).
    violations = bea_fd1._scan_fd1(obj)
    violations.extend(_scan_v1_p1_forbidden_keys(obj))
    filtered: list[dict[str, Any]] = []
    for v in violations:
        cat = v.get("category")
        if cat in ("long_string", "hex_digest_value",
                   "forbidden_field_name_value",
                   # Reason strings (ceiling_reason, tradeoff_reason,
                   # stop_go_reason) legitimately mention ratios like
                   # "X of Y" or scope phrases like "FD2-A1" that
                   # the primitive repo_slug_value check flags as
                   # false positives. Exempt safe value paths.
                   "repo_slug_value",
                   "line_range_value") and _v1_p1_safe_value_path(
                v.get("path", "")):
            continue
        filtered.append(v)
    return filtered


def _v1_p1_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_v1_p1(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_v1_p1_no_forbidden(obj: Any) -> None:
    scan = _v1_p1_forbidden_scan_summary(obj)
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


# --- Natural keys for BEA-v1-P1 public record tables ---


def _srr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["source_phase"], rec["source_ci_run_id"])


def _fcr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["failure_category"],)


def _amr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["failure_category"], rec["action_layer"])


def _ocr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["ceiling_name"],)


def _car_natural_key(rec: dict[str, Any]) -> tuple:
    return (
        rec["source_phase"], rec["benchmark"], rec["failure_category"],
    )


def _ucr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["ceiling_name"],)


def _rtr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["tradeoff_axis"],)


def _sgr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["stop_go_decision"],)


def _gr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["gate"],)


def _pmr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["manifest_name"],)


def _fccr_natural_key(rec: dict[str, Any]) -> tuple:
    return (rec["failure_category"],)


# ---------------------------------------------------------------------------
# Committed FD1 / FD2-A1 artifact loaders (read-only)
# ---------------------------------------------------------------------------


def _load_committed_artifact(
    artifact_path: Path,
) -> tuple[dict[str, Any], str, str, str]:
    """Load a committed public artifact (read-only).

    Returns ``(artifact, schema_version, artifact_hash, status)``.
    On failure returns ``({}, "", "", reason)``; the caller fail-closes
    to ``unavailable_with_reason``.
    """
    if not artifact_path.exists() or not artifact_path.is_file():
        return {}, "", "", "artifact_missing"
    try:
        with artifact_path.open("r", encoding="utf-8") as f:
            artifact = json.load(f)
    except Exception:
        return {}, "", "", "artifact_parse_failed"
    try:
        h = hashlib.sha256()
        with artifact_path.open("rb") as fb:
            for chunk in iter(lambda: fb.read(65536), b""):
                h.update(chunk)
        artifact_hash = h.hexdigest()
    except Exception:
        artifact_hash = ""
    schema_ver = str(artifact.get("schema_version", "") or "")
    return artifact, schema_ver, artifact_hash, "pass"


# ---------------------------------------------------------------------------
# FD1 replay artifact validator (fail-closed; @oracle second No-Go repair)
# ---------------------------------------------------------------------------


class Fd1ReplayArtifactValidation:
    """Container for FD1 replay-artifact validation results.

    The CI workflow regenerates the FD1 private decomposition under
    ``$RUNNER_TEMP`` and writes both the public replay report
    (``fd1_replay_report.json``) and the private JSONL
    (``bea_fd1.decomposition.jsonl``). The audit evaluator must
    validate the replay report BEFORE trusting the private JSONL, so
    that a stale / mismatched / partial replay cannot authorize v1-A.

    Only aggregate validation fields are exposed; no private JSONL path
    or content hash is serialized.
    """

    def __init__(self) -> None:
        self.supplied: bool = False
        self.parsed: bool = False
        self.validated: bool = False
        self.replay_status: str = ""
        self.replay_schema_version: str = ""
        self.replay_records_decomposed: int = 0
        self.replay_manifest_record_count: int = 0
        self.replay_manifest_records_written: bool = False
        self.replay_manifest_path_publicly_serialized: bool = True
        self.replay_manifest_schema_version: str = ""
        self.replay_manifest_hash: str = ""
        self.committed_manifest_hash: str = ""
        self.manifest_hash_match: bool = False
        self.replay_forbidden_scan_pass: bool = False
        self.failure_category: str = ""


def _validate_fd1_replay_artifact(
    replay_artifact_path: Path | None,
    committed_fd1_manifest_hash: str,
) -> Fd1ReplayArtifactValidation:
    """Validate the FD1 replay report (``fd1_replay_report.json``).

    Returns a :class:`Fd1ReplayArtifactValidation`. The caller fail-
    closes to ``no_go_ceiling_unavailable`` if the replay artifact is
    missing / unparseable / status-mismatched / count-mismatched /
    manifest-hash-mismatched / forbidden-scan-failed.

    Required replay-artifact fields (per @oracle second No-Go):
      * ``schema_version == "bea_fd1_failure_decomposition.v1"``
      * ``status == "bea_fd1_decomposition_pass"``
      * ``records_decomposed == 239``
      * ``private_decomposition_manifest.schema_version
        == "bea_fd1_private_decomposition.v1"``
      * ``private_decomposition_manifest.record_count == 86040``
      * ``private_decomposition_manifest.records_written == true``
      * ``private_decomposition_manifest.path_publicly_serialized == false``
      * ``private_decomposition_manifest.manifest_hash`` matches the
        committed FD1 artifact manifest hash
      * ``forbidden_scan.status == "pass"``
    """
    v = Fd1ReplayArtifactValidation()
    v.committed_manifest_hash = str(committed_fd1_manifest_hash or "")
    if replay_artifact_path is None:
        return v
    v.supplied = True
    if not replay_artifact_path.exists() or not replay_artifact_path.is_file():
        v.failure_category = "fd1_replay_artifact_missing"
        return v
    try:
        with replay_artifact_path.open("r", encoding="utf-8") as f:
            artifact = json.load(f)
    except Exception:
        v.failure_category = "fd1_replay_artifact_parse_failed"
        return v
    if not isinstance(artifact, dict):
        v.failure_category = "fd1_replay_artifact_parse_failed"
        return v
    v.parsed = True
    v.replay_schema_version = str(artifact.get("schema_version", "") or "")
    if v.replay_schema_version != "bea_fd1_failure_decomposition.v1":
        v.failure_category = "fd1_replay_artifact_schema_mismatch"
        return v
    v.replay_status = str(artifact.get("status", "") or "")
    if v.replay_status != "bea_fd1_decomposition_pass":
        v.failure_category = "fd1_replay_artifact_status_mismatch"
        return v
    try:
        v.replay_records_decomposed = int(
            artifact.get("records_decomposed", 0) or 0)
    except (TypeError, ValueError):
        v.replay_records_decomposed = 0
    if v.replay_records_decomposed != EXPECTED_RECORDS_DECOMPOSED:
        v.failure_category = "fd1_replay_artifact_records_mismatch"
        return v
    manifest = artifact.get("private_decomposition_manifest", {})
    if not isinstance(manifest, dict):
        v.failure_category = "fd1_replay_artifact_manifest_mismatch"
        return v
    v.replay_manifest_schema_version = str(
        manifest.get("schema_version", "") or "")
    v.replay_manifest_record_count = int(
        manifest.get("record_count", 0) or 0)
    v.replay_manifest_records_written = bool(
        manifest.get("records_written", False))
    v.replay_manifest_path_publicly_serialized = bool(
        manifest.get("path_publicly_serialized", True))
    v.replay_manifest_hash = str(manifest.get("manifest_hash", "") or "")
    # Manifest schema + count + records_written + path flag.
    if (v.replay_manifest_schema_version
            != bea_fd1.PRIVATE_DECOMP_SCHEMA_VERSION
            or v.replay_manifest_record_count != EXPECTED_PRIVATE_DECOMP_ROWS
            or not v.replay_manifest_records_written
            or v.replay_manifest_path_publicly_serialized is not False):
        v.failure_category = "fd1_replay_artifact_manifest_mismatch"
        return v
    # Manifest hash must match the committed FD1 artifact manifest hash
    # (the manifest hash is a schema-content hash, NOT a private JSONL
    # content hash — it identifies the private decomposition schema).
    v.manifest_hash_match = bool(
        v.replay_manifest_hash and v.committed_manifest_hash
        and v.replay_manifest_hash == v.committed_manifest_hash)
    if not v.manifest_hash_match:
        v.failure_category = "fd1_replay_artifact_manifest_hash_mismatch"
        return v
    # forbidden_scan must pass.
    scan = artifact.get("forbidden_scan", {})
    v.replay_forbidden_scan_pass = (
        isinstance(scan, dict)
        and scan.get("status") == "pass"
    )
    if not v.replay_forbidden_scan_pass:
        v.failure_category = "fd1_replay_artifact_forbidden_scan_failed"
        return v
    v.validated = True
    return v


# ---------------------------------------------------------------------------
# Actionability matrix builder
# ---------------------------------------------------------------------------


def _cell_class_for(category: str, layer: str) -> str:
    """Return the cell class for one (category, layer) pair.

    For unavailable categories (no support label / missing trace), the
    whole row is uniform; for available categories the lookup uses the
    ``ACTIONABILITY_MATRIX`` table. Falls back to
    ``not_actionable_by_layer`` if the mapping is missing (defensive).
    """
    if category in CANDIDATE_UNAVAILABLE_CATEGORIES:
        return "candidate_unavailable"
    if category in CEILING_UNAVAILABLE_CATEGORIES:
        return "ceiling_unavailable_insufficient_trace"
    return ACTIONABILITY_MATRIX.get((category, layer), "not_actionable_by_layer")


def _build_actionability_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category in FAILURE_CATEGORIES:
        for layer in ACTION_LAYERS:
            cell_class = _cell_class_for(category, layer)
            rows.append({
                "failure_category": category,
                "action_layer": layer,
                "cell_class": cell_class,
                "is_direct_actionable": cell_class == "direct_actionable",
                "is_indirect_actionable": cell_class == "indirect_actionable",
                "is_candidate_unavailable":
                    cell_class == "candidate_unavailable",
                "is_ceiling_unavailable":
                    cell_class == "ceiling_unavailable_insufficient_trace",
            })
    rows.sort(key=lambda r: (r["failure_category"], r["action_layer"]))
    return rows


# ---------------------------------------------------------------------------
# FD1 aggregate extraction (read-only)
# ---------------------------------------------------------------------------


def _fd1_availability_records(
    fd1_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = fd1_artifact.get("availability_records", [])
    return rows if isinstance(rows, list) else []


def _fd1_category_summary_records(
    fd1_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = fd1_artifact.get("category_summary_records", [])
    return rows if isinstance(rows, list) else []


def _fd1_source_run_records(
    fd1_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = fd1_artifact.get("source_run_records", [])
    return rows if isinstance(rows, list) else []


def _fd1_private_decomposition_manifest(
    fd1_artifact: dict[str, Any],
) -> dict[str, Any]:
    m = fd1_artifact.get("private_decomposition_manifest", {})
    return m if isinstance(m, dict) else {}


def _fd1_records_decomposed(fd1_artifact: dict[str, Any]) -> int:
    try:
        return int(fd1_artifact.get("records_decomposed", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _fd1_status(fd1_artifact: dict[str, Any]) -> str:
    return str(fd1_artifact.get("status", "") or "")


def _fd1_schema_version(fd1_artifact: dict[str, Any]) -> str:
    return str(fd1_artifact.get("schema_version", "") or "")


# Aggregate category counts per source_phase / benchmark.
# Derived from FD1 ``category_summary_records``: each row has
# (source_phase, benchmark, category, category_availability, record_count).
# For each (source_phase, benchmark, category) we sum record_count across
# availability buckets to get the total affected record count.

def _aggregate_failure_category_counts(
    fd1_artifact: dict[str, Any],
) -> dict[tuple[str, str, str], int]:
    """Return ``{(source_phase, benchmark, category): affected_count}``.

    Summed across availability buckets. Only categories with
    ``record_count > 0`` contribute (FD1 only writes a row when a
    category affected at least one record for that source_phase/benchmark).
    """
    out: dict[tuple[str, str, str], int] = {}
    for row in _fd1_category_summary_records(fd1_artifact):
        if not isinstance(row, dict):
            continue
        try:
            sp = str(row["source_phase"])
            bm = str(row["benchmark"])
            cat = str(row["category"])
            cnt = int(row.get("record_count", 0) or 0)
        except (KeyError, TypeError, ValueError):
            continue
        key = (sp, bm, cat)
        out[key] = out.get(key, 0) + cnt
    return out


def _total_records_per_source_phase(
    fd1_artifact: dict[str, Any],
) -> dict[str, int]:
    """Return ``{source_phase: total_successful_records}`` from FD1
    source_run_records."""
    out: dict[str, int] = {}
    for row in _fd1_source_run_records(fd1_artifact):
        if not isinstance(row, dict):
            continue
        try:
            sp = str(row["source_phase"])
            cnt = int(row.get("replayed_successful_records", 0) or 0)
        except (KeyError, TypeError, ValueError):
            continue
        out[sp] = out.get(sp, 0) + cnt
    return out


# ---------------------------------------------------------------------------
# FD1 private decomposition parser (in-memory; never serialized)
# ---------------------------------------------------------------------------


class ParsedPrivateDecomposition:
    """Container for parsed FD1 private decomposition rows.

    All per-record fields (``private_record_id``, candidate values, etc.)
    are kept in-memory only; the public artifact never serializes them.
    Only aggregate counts and rates derived from this object are
    published.
    """

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.parse_failures: int = 0
        self.row_count: int = 0
        self.group_count: int = 0
        # Computed file-selector ceiling fields.
        self.gold_file_absent_denominator: int = 0
        self.recoverable_lower_bound: int = 0
        self.unrecoverable_candidate_unavailable: int = 0
        self.retrieval_availability_rate: float = 0.0
        self.file_selector_lower_bound_rate: float = 0.0
        self.computed: bool = False
        # Whether a JSONL path was supplied (regardless of parse success).
        self.path_supplied: bool = False
        self.file_existed: bool = False


def _parse_private_decomposition_jsonl(
    path: Path | None,
) -> ParsedPrivateDecomposition:
    """Parse the FD1 private decomposition JSONL at ``path``.

    Returns a :class:`ParsedPrivateDecomposition`. If ``path`` is None
    or the file does not exist, returns an empty container with
    ``path_supplied``/``file_existed`` set appropriately; the caller
    decides whether to fail-closed (status ``no_go_ceiling_unavailable``)
    or proceed.

    Private row schema (from ``bea_fd1_failure_decomposition``):
    ``phase_run_id, source_phase, benchmark, private_record_id,
    policy_arm, category, baseline_arm, treatment_arm, metric,
    treatment_value, baseline_value, loss, delta,
    category_availability, latency_ms, cost_usd, tokens,
    provider_calls``.

    Only ``private_record_id``, ``metric``, ``treatment_value``,
    ``baseline_value``, and ``baseline_arm`` are read for the
    file-selector lower bound; nothing else is retained.
    """
    pt = ParsedPrivateDecomposition()
    if path is None:
        return pt
    pt.path_supplied = True
    if not path.exists() or not path.is_file():
        return pt
    pt.file_existed = True
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    pt.parse_failures += 1
                    continue
                if not isinstance(obj, dict):
                    pt.parse_failures += 1
                    continue
                pt.rows.append(obj)
    except OSError:
        pt.parse_failures += 1
    pt.row_count = len(pt.rows)
    # Group rows by private_record_id (in-memory; never serialized).
    by_record: set[str] = set()
    for row in pt.rows:
        rid = str(row.get("private_record_id", "") or "")
        if rid:
            by_record.add(rid)
    pt.group_count = len(by_record)
    return pt


def _compute_file_selector_lower_bound(
    pt: ParsedPrivateDecomposition,
) -> None:
    """Compute the file-selector oracle ceiling lower bound from the
    parsed FD1 private decomposition rows.

    For each record (grouped by ``private_record_id``):

    * v0.3 ``file_recall@10`` = ``treatment_value`` for metric
      ``file_recall@10`` (the treatment arm is always
      ``bea_v0_3_anchor_span_latency`` in FD1, so ``treatment_value``
      is the v0.3 value; identical across all baseline rows for the
      same record/metric).
    * v0.3 ``success_rate`` = ``treatment_value`` for metric
      ``success_rate``.
    * ``gold_file_absent`` denominator: v0.3 file_recall@10 == 0 AND
      success_rate == 0 (matches FD1's
      ``_classify_from_private_rows`` rule).
    * For denominator records: if ANY baseline arm row for
      ``file_recall@10`` has ``baseline_value`` > 0.0 → the record is
      recoverable (another same-pool/same-frame arm selected a correct
      file; the gold file was in the candidate pool). This is a LOWER
      BOUND on recoverability — it does NOT prove that every
      denominator record's gold was in the pool, only that at least
      this many were.

    Sets ``pt.computed = True`` and populates the computed fields.
    """
    if not pt.rows:
        return
    # Index treatment_value by (private_record_id, metric) — only the
    # metrics we need. Collect baseline_value per record for
    # file_recall@10 (one value per baseline_arm row).
    treatment_lookup: dict[tuple[str, str], float] = {}
    baseline_file_recall: dict[str, list[float]] = {}
    all_rids: set[str] = set()
    for row in pt.rows:
        rid = str(row.get("private_record_id", "") or "")
        if not rid:
            continue
        all_rids.add(rid)
        metric = str(row.get("metric", "") or "")
        try:
            t_val = float(row.get("treatment_value", 0.0) or 0.0)
            b_val = float(row.get("baseline_value", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if metric == "file_recall@10":
            # treatment_value is v0.3 file_recall (same for all 5
            # baselines × 12 categories = 60 rows for this record/metric).
            treatment_lookup.setdefault((rid, "file_recall@10"), t_val)
            baseline_file_recall.setdefault(rid, []).append(b_val)
        elif metric == "success_rate":
            treatment_lookup.setdefault((rid, "success_rate"), t_val)

    denominator = 0
    lower_bound = 0
    for rid in all_rids:
        file_recall = treatment_lookup.get((rid, "file_recall@10"), 0.0)
        success = treatment_lookup.get((rid, "success_rate"), 0.0)
        if file_recall == 0.0 and success == 0.0:
            denominator += 1
            baseline_vals = baseline_file_recall.get(rid, [])
            if any(v > 0.0 for v in baseline_vals):
                lower_bound += 1

    pt.gold_file_absent_denominator = denominator
    pt.recoverable_lower_bound = lower_bound
    pt.unrecoverable_candidate_unavailable = denominator - lower_bound
    if denominator > 0:
        pt.retrieval_availability_rate = (
            pt.unrecoverable_candidate_unavailable / denominator
        )
    if pt.group_count > 0:
        pt.file_selector_lower_bound_rate = lower_bound / pt.group_count
    pt.computed = True


# ---------------------------------------------------------------------------
# Public record builders (records-only; no dynamic dict mirrors)
# ---------------------------------------------------------------------------


def _source_run_records(
    *, fd1_schema_version: str, fd1_source_artifact_hash: str,
    fd1_status: str, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    fd1_committed_manifest_hash: str,
    fd2a1_schema_version: str, fd2a1_source_artifact_hash: str,
    fd2a1_status: str,
    audit_match: bool, audit_mismatch_reason: str,
    fd1_private_decomposition_supplied: bool = False,
    fd1_private_decomposition_parsed: bool = False,
    fd1_private_decomposition_row_count: int = 0,
    fd1_private_decomposition_group_count: int = 0,
    fd1_private_decomposition_lower_bound: int = 0,
    fd1_private_decomposition_denominator: int = 0,
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
) -> list[dict[str, Any]]:
    """One source_run_records row describing the FD1 audit source.

    The BEA-v1-P1 audit evaluator reads the committed FD1 artifact
    (read-only) and does NOT itself rerun FD1. The CI workflow may
    regenerate the FD1 private decomposition under temp storage before
    invoking the evaluator; that is tracked by the explicit replay
    provenance fields below. The ``source_phase`` is ``BEA-FD1`` (the
    audit's source phase) and ``source_ci_run_id`` is the FD1 manual
    CI run.

    The ``fd1_private_decomposition_*`` and ``replay_artifact_*`` fields
    are aggregate-only counts/validation flags (no record IDs, no
    private JSONL paths, no private JSONL content hashes). The
    ``replay_artifact_manifest_hash`` is the FD1 private decomposition
    SCHEMA manifest hash (a schema-content hash), NOT a private JSONL
    content hash, and must match the committed FD1 artifact's manifest
    hash. These fields are required to authorize v1-A.
    """
    del fd1_committed_manifest_hash  # recorded via manifest_hash_match
    return [{
        "source_phase": "BEA-FD1",
        "source_ci_run_id": FD1_SOURCE_CI_RUN_ID,
        "source_checkpoint": FD2A1_RESULT_CHECKPOINT,  # binding predecessor
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
        "fd2a1_source_schema_version": fd2a1_schema_version,
        "fd2a1_source_artifact_hash": fd2a1_source_artifact_hash,
        "fd2a1_result_checkpoint": FD2A1_RESULT_CHECKPOINT,
        "fd2a1_result_status": fd2a1_status or FD2A1_RESULT_STATUS,
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
        # FD1 replay artifact validation (fail-closed; @oracle second
        # No-Go). These fields are aggregate-only; no private JSONL
        # path or content hash is serialized.
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
            "fd1_committed_aggregate_counts_and_validated_private_replay"
            if fd1_private_decomposition_parsed and replay_artifact_validated
            else ("fd1_committed_aggregate_counts_and_unvalidated_private_replay"
                  if fd1_private_decomposition_parsed
                  else "fd1_committed_aggregate_counts_only_no_private_replay"),
    }]


def _failure_category_records(
    fd1_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    """12 rows: one per FD1 failure category, with aggregate affected
    counts across all source_phase / benchmark buckets (summed) and the
    FD1 availability class."""
    agg = _aggregate_failure_category_counts(fd1_artifact)
    # Per-source-phase totals for rate computation.
    sp_totals = _total_records_per_source_phase(fd1_artifact)
    total_records = sum(sp_totals.values()) or 1
    rows: list[dict[str, Any]] = []
    for category in FAILURE_CATEGORIES:
        affected = sum(
            cnt for (sp, bm, cat), cnt in agg.items() if cat == category
        )
        if category in CANDIDATE_UNAVAILABLE_CATEGORIES:
            availability = "unavailable_no_support_label"
        elif category in CEILING_UNAVAILABLE_CATEGORIES:
            availability = "unavailable_missing_trace"
        else:
            availability = "available"
        rows.append({
            "failure_category": category,
            "category_availability": availability,
            "affected_record_count": int(affected),
            "rate_of_records_decomposed": round(affected / total_records, 6),
        })
    rows.sort(key=lambda r: r["failure_category"])
    return rows


def _actionability_matrix_records() -> list[dict[str, Any]]:
    return _build_actionability_matrix()


def _candidate_availability_records(
    fd1_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    """Records-only: per (source_phase, benchmark, failure_category)
    counts of records where ``gold_file_absent`` (the file-selector
    ceiling denominator) or ``correct_file_wrong_span`` (span-refiner
    denominator) or other availability-driven categories fired.

    Sourced from FD1 ``availability_records`` (counts of records for
    which the category was *evaluable* per source_phase/benchmark, NOT
    affected counts). The ceiling denominator per category is the
    affected count from ``category_summary_records``; this table
    publishes the per-(source_phase, benchmark, failure_category)
    availability contribution so the public artifact remains
    records-only and reproducible.
    """
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    # Use FD1 availability_records: (source_phase, benchmark, category,
    # category_availability, record_count). For each (sp, bm, category)
    # we take the maximum record_count across availability buckets
    # (since availability_records lists the count of records for which
    # the category was evaluable). The "affected" count comes from
    # category_summary_records and is captured in failure_category_records.
    per_key: dict[tuple[str, str, str], int] = {}
    for row in _fd1_availability_records(fd1_artifact):
        if not isinstance(row, dict):
            continue
        try:
            sp = str(row["source_phase"])
            bm = str(row["benchmark"])
            cat = str(row["category"])
            cnt = int(row.get("record_count", 0) or 0)
        except (KeyError, TypeError, ValueError):
            continue
        key = (sp, bm, cat)
        per_key[key] = max(per_key.get(key, 0), cnt)
    # Only publish categories that bear on a ceiling denominator
    # (gold_file_absent, correct_file_wrong_span, gold_span_absent,
    # too_many_anchor_slots, early_stop_too_early,
    # budget_spent_on_low_marginal_gain, latency_without_quality_gain).
    # Unavailable categories are NOT included here (they have no
    # candidate-level denominator and are documented in
    # unavailable_ceiling_records instead).
    ceiling_relevant = {
        "gold_file_absent", "correct_file_wrong_span", "gold_span_absent",
        "too_many_anchor_slots", "early_stop_too_early",
        "budget_spent_on_low_marginal_gain", "latency_without_quality_gain",
    }
    for (sp, bm, cat), cnt in sorted(per_key.items()):
        if cat not in ceiling_relevant:
            continue
        if (sp, bm, cat) in seen:
            continue
        seen.add((sp, bm, cat))
        rows.append({
            "source_phase": sp,
            "benchmark": bm,
            "failure_category": cat,
            "evaluable_record_count": cnt,
        })
    rows.sort(key=lambda r: (r["source_phase"], r["benchmark"],
                              r["failure_category"]))
    return rows


def _oracle_ceiling_records(
    fd1_artifact: dict[str, Any],
    file_selector_denominator: int,
    file_selector_upper_bound: int,
    total_records: int,
    pt: ParsedPrivateDecomposition | None,
) -> list[dict[str, Any]]:
    """Honest oracle ceilings.

    * ``file_selector`` — REQUIRED. Two regimes:
      - If a parsed FD1 private decomposition is supplied and valid,
        publish a real lower bound
        (``ceiling_class =
        computed_private_lower_bound_and_public_upper_bound``;
        ``ceiling_basis = fd1_private_decomposition_replay``). The
        lower bound = count of denominator records where ANY baseline
        arm selected a correct file (gold was in the candidate pool).
      - Otherwise: omit the row entirely. The public aggregate upper
        bound alone is explicitly insufficient to authorize v1-A; the
        audit's status falls to ``no_go_ceiling_unavailable`` and the
        row is published in ``unavailable_ceiling_records`` instead.
    * ``span_refiner`` — unavailable (no per-record candidate/gold span
      overlap in FD1 public aggregate). Published in
      ``unavailable_ceiling_records`` instead.
    * ``setwise_packer_redundancy`` — unavailable
      (``redundant_same_file_candidates`` is ``unavailable_missing_trace``
      in FD1). Omitted; published in unavailable_ceiling_records.
    * ``stopping_scheduler`` — unavailable (no ordered-prefix
      utility/latency in FD1 public aggregate; plan forbids inferring
      stopping ceiling from aggregate latency). Omitted; published in
      unavailable_ceiling_records.
    """
    del fd1_artifact  # unused (denominators precomputed by caller)
    rows: list[dict[str, Any]] = []
    if pt is None or not pt.computed or file_selector_denominator <= 0:
        return rows
    upper_rate = file_selector_upper_bound / max(total_records, 1)
    lower_rate = pt.file_selector_lower_bound_rate
    rows.append({
        "ceiling_name": "file_selector",
        "ceiling_class":
            "computed_private_lower_bound_and_public_upper_bound",
        "denominator": int(file_selector_denominator),
        "recoverable_count_upper_bound":
            int(file_selector_upper_bound),
        "recoverable_count_lower_bound":
            int(pt.recoverable_lower_bound),
        "recoverable_rate_upper_bound": round(upper_rate, 6),
        "recoverable_rate_lower_bound": round(lower_rate, 6),
        "unrecoverable_candidate_unavailable_count":
            int(pt.unrecoverable_candidate_unavailable),
        "retrieval_availability_rate":
            round(pt.retrieval_availability_rate, 6),
        "ceiling_basis": "fd1_private_decomposition_replay",
        "ceiling_reason":
            "lower_bound_count_records_where_any_baseline_arm_selected_"
            "correct_file_for_file_recall_at_10; lower_bound_is_lower_"
            "bound_only_does_not_prove_full_candidate_pool_availability;"
            " upper_bound_assumes_gold_in_pool_when_gold_file_absent",
    })
    return rows


def _unavailable_ceiling_records(
    *, file_selector_unavailable: bool = False,
    file_selector_unavailable_reason: str = "",
) -> list[dict[str, Any]]:
    """Explicit unavailable rows for ceilings that cannot be computed
    from the committed FD1 public aggregate (or, for file_selector,
    when no FD1 private decomposition JSONL was supplied).
    """
    rows: list[dict[str, Any]] = []
    if file_selector_unavailable:
        rows.append({
            "ceiling_name": "file_selector",
            "ceiling_class": "unavailable",
            "ceiling_basis": "fd1_public_aggregate_records_only",
            "ceiling_reason": file_selector_unavailable_reason or (
                "fd1_private_decomposition_replay_required_for_lower_"
                "bound; public_aggregate_upper_bound_only_is_insufficient_"
                "to_authorize_v1_a"
            ),
        })
    rows.extend([
        {
            "ceiling_name": "span_refiner",
            "ceiling_class": "unavailable",
            "ceiling_basis": "fd1_public_aggregate_records_only",
            "ceiling_reason":
                "candidate_or_gold_span_overlap_fields_absent_in_fd1_"
                "public_aggregate; correct_file_wrong_span aggregate "
                "count exists but per-record span overlap with gold "
                "span does not",
        },
        {
            "ceiling_name": "setwise_packer_redundancy",
            "ceiling_class": "unavailable",
            "ceiling_basis": "fd1_public_aggregate_records_only",
            "ceiling_reason":
                "redundant_same_file_candidates_marked_unavailable_"
                "missing_trace_in_fd1; duplicate_or_file_grouping_fields_"
                "absent_in_public_aggregate",
        },
        {
            "ceiling_name": "stopping_scheduler",
            "ceiling_class": "unavailable",
            "ceiling_basis": "fd1_public_aggregate_records_only",
            "ceiling_reason":
                "ordered_prefix_quality_or_latency_absent_in_fd1_public_"
                "aggregate; plan_forbids_inferring_stopping_ceiling_"
                "from_aggregate_latency_loss",
        },
    ])
    rows.sort(key=lambda r: r["ceiling_name"])
    return rows


def _redundancy_tradeoff_records(
    fd1_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    """Redundancy / marginal-utility tradeoff axis records.

    Honest: FD1 marks ``redundant_same_file_candidates`` and
    ``risk_penalty_removed_gold`` as ``unavailable_missing_trace``, so
    the redundancy tradeoff cannot be quantified from the public
    aggregate. We publish one explicit unavailable row per tradeoff axis
    rather than fabricating a number.
    """
    del fd1_artifact  # trace unavailable; no computation
    rows = [
        {
            "tradeoff_axis":
                "marginal_utility_per_added_candidate",
            "tradeoff_class": "unavailable",
            "tradeoff_basis":
                "fd1_public_aggregate_records_only",
            "tradeoff_reason":
                "redundant_same_file_candidates_unavailable_missing_trace;"
                " per-candidate marginal utility not in public aggregate",
        },
        {
            "tradeoff_axis":
                "duplicate_same_file_suppression_cost",
            "tradeoff_class": "unavailable",
            "tradeoff_basis":
                "fd1_public_aggregate_records_only",
            "tradeoff_reason":
                "duplicate_or_file_grouping_fields_absent_in_fd1_public_"
                "aggregate; FD2-A1 rerun showed redundancy_overcorrection "
                "in 4 of 38 regressed records but that is the bounded "
                "FD2-A1 frame, not the full FD1 239-record frame",
        },
    ]
    rows.sort(key=lambda r: r["tradeoff_axis"])
    return rows


def _stop_go_records(
    *, file_selector_ceiling_computed: bool,
    fd1_private_decomposition_parsed: bool,
    file_selector_lower_bound: int | None,
    file_selector_lower_bound_rate: float,
    file_selector_upper_bound_rate: float,
    retrieval_availability_rate: float,
    span_or_stopping_dominance_rate: float,
    span_or_stopping_dominates: bool,
    ceiling_unavailable_count: int,
) -> list[dict[str, Any]]:
    """One stop/go row describing the v1-A coverage-preserving selector
    stop/go decision and its reason.

    Per the plan (updated after @oracle No-Go): the file-selector
    ceiling is required AND must be computed from the FD1 private
    decomposition replay (not the public aggregate upper bound alone).
    The lower bound rate (not the upper bound rate) drives the
    materiality test, and retrieval_availability_rate is the share of
    denominator records whose gold was NOT in the candidate pool (per
    the private replay).
    """
    # ``ceiling_unavailable_count`` is recorded for transparency; the
    # decision below does NOT branch on it (only file_selector ceiling
    # + private decomposition drive the v1-A decision).
    _ = int(ceiling_unavailable_count)
    if not fd1_private_decomposition_parsed:
        decision = "needs_fd1_private_replay_before_v1_a"
        reason = (
            "fd1_private_decomposition_replay_required; "
            "public_aggregate_upper_bound_only_is_insufficient_to_"
            "authorize_v1_a_coverage_preserving_selector"
        )
    elif not file_selector_ceiling_computed:
        decision = "no_go_no_file_selector_ceiling"
        reason = (
            "file_selector_oracle_ceiling_unavailable; cannot evaluate "
            "v1-A coverage-preserving selector upside"
        )
    elif file_selector_lower_bound is None:
        decision = "needs_fd1_private_replay_before_v1_a"
        reason = (
            "file_selector_lower_bound_null; fd1_private_decomposition_"
            "replay_required_to_compute_recoverable_lower_bound"
        )
    elif retrieval_availability_rate > NO_GO_RETRIEVAL_AVAILABILITY_RATE:
        decision = "no_go_retrieval_availability_limit"
        reason = (
            "retrieval_availability_dominates_recoverable_ceiling; "
            "v1-A selector cannot recover records whose gold file is "
            "absent from the candidate pool"
        )
    elif span_or_stopping_dominates:
        decision = "no_go_span_or_stopping_dominates"
        reason = (
            "span_refiner_or_stopping_scheduler_actionable_loss_dominates;"
            " v1-A file selector is not the highest-ceiling layer"
        )
    elif file_selector_lower_bound_rate < GO_FILE_SELECTOR_UPSIDE_RATE_MIN:
        decision = "no_go_no_file_selector_ceiling"
        reason = (
            "file_selector_lower_bound_upside_below_material_threshold; "
            "v1-A coverage-preserving selector has no material recoverable "
            "loss mass"
        )
    else:
        decision = "go_v1_a_coverage_preserving_selector"
        reason = (
            "file_selector_lower_bound_recoverable_loss_mass_is_material; "
            "candidate_availability_not_dominant_per_private_replay; "
            "span_or_stopping_does_not_dominate_recoverable_ceiling; "
            "runtime_clean_coverage_preserving_selector_plausible"
        )
    return [{
        "stop_go_decision": decision,
        "stop_go_reason": reason,
        "fd1_private_decomposition_parsed":
            bool(fd1_private_decomposition_parsed),
        "file_selector_ceiling_computed":
            bool(file_selector_ceiling_computed),
        "file_selector_lower_bound":
            None if file_selector_lower_bound is None
            else int(file_selector_lower_bound),
        "file_selector_lower_bound_rate":
            round(file_selector_lower_bound_rate, 6),
        "file_selector_upper_bound_rate":
            round(file_selector_upper_bound_rate, 6),
        "retrieval_availability_rate":
            round(retrieval_availability_rate, 6),
        "span_or_stopping_dominance_rate":
            round(span_or_stopping_dominance_rate, 6),
        "span_or_stopping_dominates": bool(span_or_stopping_dominates),
        "ceiling_unavailable_count": int(ceiling_unavailable_count),
        "go_threshold_file_selector_upside_rate_min":
            GO_FILE_SELECTOR_UPSIDE_RATE_MIN,
        "no_go_threshold_retrieval_availability_rate":
            NO_GO_RETRIEVAL_AVAILABILITY_RATE,
        "no_go_threshold_span_or_stopping_dominance_rate":
            SPAN_OR_STOPPING_DOMINANCE_RATE,
    }]


def _gate_records(
    *, fd1_records_decomposed: int,
    fd1_private_manifest_record_count: int,
    audit_match: bool,
    actionability_categories_covered: int,
    file_selector_ceiling_computed: bool,
    fd1_private_decomposition_parsed: bool,
    fd1_private_decomposition_row_count: int,
    fd1_private_decomposition_group_count: int,
    span_or_stopping_computed_or_unavailable: bool,
    forbidden_scan_pass: bool,
    retrieval_availability_dominates: bool,
    span_or_stopping_dominates: bool,
    ceiling_unavailable_count: int,
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
        _g("audit_match", 1.0 if audit_match else 0.0, "boolean", 1.0,
           audit_match),
        _g("actionability_categories_covered",
           float(actionability_categories_covered), "==",
           float(len(FAILURE_CATEGORIES)),
           actionability_categories_covered == len(FAILURE_CATEGORIES)),
        _g("file_selector_ceiling_computed",
           1.0 if file_selector_ceiling_computed else 0.0, "boolean", 1.0,
           file_selector_ceiling_computed),
        _g("fd1_private_decomposition_parsed",
           1.0 if fd1_private_decomposition_parsed else 0.0,
           "boolean", 1.0, fd1_private_decomposition_parsed),
        _g("fd1_private_decomposition_row_count",
           float(fd1_private_decomposition_row_count), "==",
           float(EXPECTED_PRIVATE_DECOMP_ROWS),
           fd1_private_decomposition_row_count == EXPECTED_PRIVATE_DECOMP_ROWS),
        _g("fd1_private_decomposition_group_count",
           float(fd1_private_decomposition_group_count), "==",
           float(EXPECTED_RECORDS_DECOMPOSED),
           fd1_private_decomposition_group_count == EXPECTED_RECORDS_DECOMPOSED),
        _g("span_or_stopping_computed_or_unavailable",
           1.0 if span_or_stopping_computed_or_unavailable else 0.0,
           "boolean", 1.0, span_or_stopping_computed_or_unavailable),
        _g("forbidden_scan_pass", 1.0 if forbidden_scan_pass else 0.0,
           "boolean", 1.0, forbidden_scan_pass),
        _g("retrieval_availability_dominates",
           1.0 if retrieval_availability_dominates else 0.0,
           "boolean_false", 0.0, not retrieval_availability_dominates),
        _g("span_or_stopping_dominates",
           1.0 if span_or_stopping_dominates else 0.0,
           "boolean_false", 0.0, not span_or_stopping_dominates),
        _g("ceiling_unavailable_count",
           float(ceiling_unavailable_count), "<=",
           float(len(CEILING_NAMES) - 1),  # at most 3 of 4 unavailable
           ceiling_unavailable_count <= len(CEILING_NAMES) - 1),
        _g("blocking_failure_count", float(blocking_failure_count), "==",
           0.0, blocking_failure_count == 0),
    ]


def _private_manifest_records(
    fd1_artifact: dict[str, Any], storage_class: str,
) -> list[dict[str, Any]]:
    """Echo the FD1 private_decomposition_manifest as a single
    private_manifest_records row (read-only; counts and hashes only)."""
    m = _fd1_private_decomposition_manifest(fd1_artifact)
    return [{
        "manifest_name": "fd1_private_decomposition_manifest",
        "records_written": bool(m.get("records_written", False)),
        "record_count": int(m.get("record_count", 0) or 0),
        "schema_version": str(m.get("schema_version", "") or ""),
        "manifest_hash": str(m.get("manifest_hash", "") or ""),
        "storage_class": storage_class,
        "path_publicly_serialized": False,
    }]


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
    file_selector_ceiling_computed: bool,
    retrieval_availability_dominates: bool,
    span_or_stopping_dominates: bool,
    ceiling_unavailable_count: int,
    file_selector_lower_bound_rate: float,
) -> str:
    if blocking_failure_count > 0:
        return "fail_schema_contract"
    if not audit_match:
        return "unavailable_with_reason"
    # Audit matched: real-run status decision (plan stop rules).
    # File-selector ceiling requires FD1 private decomposition replay
    # to compute a real lower bound. Without it the audit honestly
    # No-Gos to no_go_ceiling_unavailable (NOT a fake pass).
    if not fd1_private_decomposition_parsed:
        return "no_go_ceiling_unavailable"
    if not file_selector_ceiling_computed:
        return "no_go_no_file_selector_ceiling"
    if retrieval_availability_dominates:
        return "no_go_retrieval_availability_limit"
    if span_or_stopping_dominates:
        return "no_go_span_or_stopping_dominates"
    if ceiling_unavailable_count >= len(CEILING_NAMES):
        # All 4 ceilings unavailable (file-selector required, so this
        # branch is unreachable in practice; kept for completeness).
        return "no_go_ceiling_unavailable"
    if file_selector_lower_bound_rate < GO_FILE_SELECTOR_UPSIDE_RATE_MIN:
        return "no_go_no_file_selector_ceiling"
    return "bea_v1_p1_actionability_audit_pass"


# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


def _build_unavailable_report(
    failure_reason_category: str, *, self_test_passed: bool,
    self_test_checks_total: int = 0,
    self_test_checks_passed: int | None = None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact_read: bool = False,
    fd1_source_schema_version: str = "",
    fd1_source_artifact_hash: str = "",
    fd2a1_artifact_read: bool = False,
    fd2a1_source_schema_version: str = "",
    fd2a1_source_artifact_hash: str = "",
    audit_match: bool = False,
    audit_mismatch_reason: str = "",
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
    safe_true["fd1_artifact_read"] = bool(fd1_artifact_read)
    safe_true["fd2a1_artifact_read"] = bool(fd2a1_artifact_read)

    source_runs = _source_run_records(
        fd1_schema_version=fd1_source_schema_version,
        fd1_source_artifact_hash=fd1_source_artifact_hash,
        fd1_status="",
        fd1_records_decomposed=0,
        fd1_private_manifest_record_count=0,
        fd1_committed_manifest_hash="",
        fd2a1_schema_version=fd2a1_source_schema_version,
        fd2a1_source_artifact_hash=fd2a1_source_artifact_hash,
        fd2a1_status="",
        audit_match=audit_match,
        audit_mismatch_reason=audit_mismatch_reason,
    )

    # Unavailable artifact: publish empty record tables (the matrix /
    # ceilings are computed from the FD1 aggregate; without it the
    # artifact is honestly empty). The actionability_matrix_records is
    # always populated from the static mapping (it does not depend on
    # the FD1 aggregate), so the 12x6 = 72 row matrix is always
    # present even when the artifact is unavailable.
    matrix = _actionability_matrix_records()
    unavailable_ceilings = _unavailable_ceiling_records()

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
        "action_layers": list(ACTION_LAYERS),
        "failure_categories": list(FAILURE_CATEGORIES),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "records_decomposed": 0,
        "private_manifest_record_count": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_count_records": _failure_category_count_records(fcc),
        "source_run_records": source_runs,
        "failure_category_records": [],
        "actionability_matrix_records": matrix,
        "oracle_ceiling_records": [],
        "candidate_availability_records": [],
        "unavailable_ceiling_records": unavailable_ceilings,
        "redundancy_tradeoff_records": [],
        "stop_go_records": [],
        "gate_records": _gate_records(
            fd1_records_decomposed=0,
            fd1_private_manifest_record_count=0,
            audit_match=audit_match,
            actionability_categories_covered=len({r["failure_category"]
                                                  for r in matrix}),
            file_selector_ceiling_computed=False,
            fd1_private_decomposition_parsed=False,
            fd1_private_decomposition_row_count=0,
            fd1_private_decomposition_group_count=0,
            span_or_stopping_computed_or_unavailable=True,
            forbidden_scan_pass=True,
            retrieval_availability_dominates=False,
            span_or_stopping_dominates=False,
            ceiling_unavailable_count=len(unavailable_ceilings),
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
            "signal_strength": "bea_v1_p1_actionability_audit_unavailable",
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
            "is_failure_attribution_only": False,
            "is_actionability_audit_only": True,
        },
    }
    scan = _v1_p1_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_audit_report(
    *, self_test_passed: bool, self_test_checks_total: int,
    self_test_checks_passed: int | None,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact: dict[str, Any],
    fd1_source_schema_version: str, fd1_source_artifact_hash: str,
    fd2a1_source_schema_version: str, fd2a1_source_artifact_hash: str,
    fd2a1_status: str,
    audit_match: bool, audit_mismatch_reason: str,
    failure_category_counts: dict[str, int],
    aggregate_runtime_seconds: float,
    pt: ParsedPrivateDecomposition | None,
    rav: Fd1ReplayArtifactValidation | None,
) -> dict[str, Any]:
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    fd1_status = _fd1_status(fd1_artifact)
    fd1_records_decomposed = _fd1_records_decomposed(fd1_artifact)
    fd1_manifest = _fd1_private_decomposition_manifest(fd1_artifact)
    fd1_manifest_count = int(fd1_manifest.get("record_count", 0) or 0)

    # Aggregate tables.
    failure_category_records = _failure_category_records(fd1_artifact)
    actionability_matrix = _actionability_matrix_records()
    candidate_availability = _candidate_availability_records(fd1_artifact)
    redundancy_tradeoff = _redundancy_tradeoff_records(fd1_artifact)
    unavailable_ceilings = _unavailable_ceiling_records()

    # File-selector ceiling denominator: records where gold_file_absent==1,
    # summed across all source_phase/benchmark buckets.
    agg = _aggregate_failure_category_counts(fd1_artifact)
    file_selector_denominator = sum(
        cnt for (sp, bm, cat), cnt in agg.items()
        if cat == "gold_file_absent"
    )
    sp_totals = _total_records_per_source_phase(fd1_artifact)
    total_records = sum(sp_totals.values()) or 1

    # File-selector oracle ceiling: computed upper bound. The recoverable
    # count upper bound equals the denominator (a perfect selector that
    # picks gold whenever it is in the candidate pool could recover at
    # most this many records). The lower bound (gold actually in pool)
    # is unavailable from the FD1 public aggregate.
    file_selector_upper_bound = file_selector_denominator
    file_selector_upper_bound_rate = (
        file_selector_upper_bound / total_records if total_records > 0 else 0.0
    )
    # file_selector_ceiling_computed is True only when a real lower bound
    # was derived from the FD1 private decomposition replay AND the
    # replay artifact was validated (fail-closed: @oracle second No-Go).
    # Without the private JSONL, the upper bound alone is insufficient
    # and the audit honestly No-Gos to no_go_ceiling_unavailable. If the
    # private JSONL was supplied but the replay artifact is missing /
    # invalid / mismatched, the audit also No-Gos (NOT a fake pass).
    fd1_private_decomposition_parsed = (
        pt is not None and pt.computed
        and pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS
        and pt.group_count == EXPECTED_RECORDS_DECOMPOSED
    )
    # Replay-artifact gating: if a private JSONL was supplied, the
    # replay artifact must be supplied AND validated. Otherwise the
    # lower bound is not trustworthy.
    replay_artifact_validated_for_pt = (
        rav is not None and rav.validated
    )
    if pt is not None and pt.path_supplied and not replay_artifact_validated_for_pt:
        # Private JSONL supplied but replay artifact missing/invalid/
        # mismatched → record the failure category and force parsed=False.
        if rav is not None and rav.failure_category:
            fcc[rav.failure_category] = max(
                fcc.get(rav.failure_category, 0), 1)
        fd1_private_decomposition_parsed = False
    if pt is not None and fd1_private_decomposition_parsed:
        file_selector_lower_bound: int | None = pt.recoverable_lower_bound
        file_selector_lower_bound_rate: float = pt.file_selector_lower_bound_rate
        retrieval_availability_rate = pt.retrieval_availability_rate
    else:
        file_selector_lower_bound = None
        file_selector_lower_bound_rate = 0.0
        retrieval_availability_rate = 0.0
    file_selector_ceiling_computed = (
        fd1_private_decomposition_parsed
        and replay_artifact_validated_for_pt
        and file_selector_denominator > 0
        and file_selector_lower_bound is not None
    )

    oracle_ceilings = _oracle_ceiling_records(
        fd1_artifact, file_selector_denominator,
        file_selector_upper_bound, total_records, pt,
    )

    # Stop/go decision inputs:
    # retrieval_availability_rate is the share of gold_file_absent
    # denominator records whose gold file was NOT in the candidate pool
    # (i.e. no baseline arm selected a correct file). Computed only
    # when a private decomposition replay was parsed; otherwise 0.0 and
    # the stop_go decision will be needs_fd1_private_replay_before_v1_a.
    # (retrieval_availability_rate assigned above.)

    # Span / stopping dominance rate: rate of records whose failure
    # category is direct_actionable on span_refiner OR
    # stopping_scheduler layer (categories: correct_file_wrong_span,
    # gold_span_absent, too_many_anchor_slots on span_refiner;
    # early_stop_too_early on stopping_scheduler). Computed from FD1
    # aggregate.
    span_direct_categories = {
        "correct_file_wrong_span", "gold_span_absent", "too_many_anchor_slots",
    }
    stopping_direct_categories = {"early_stop_too_early"}
    span_or_stopping_affected = sum(
        cnt for (sp, bm, cat), cnt in agg.items()
        if cat in span_direct_categories or cat in stopping_direct_categories
    )
    span_or_stopping_dominance_rate = (
        span_or_stopping_affected / total_records if total_records > 0 else 0.0
    )
    # Span/stopping dominates if its affected rate exceeds the
    # file-selector lower bound rate (i.e. span/stopping loss mass
    # exceeds the recoverable file-selector ceiling). Only evaluated
    # when a real lower bound was computed.
    span_or_stopping_dominates = (
        fd1_private_decomposition_parsed
        and file_selector_ceiling_computed
        and span_or_stopping_dominance_rate > 0.0
        and span_or_stopping_dominance_rate > file_selector_lower_bound_rate
        and span_or_stopping_dominance_rate
        >= SPAN_OR_STOPPING_DOMINANCE_RATE
    )

    retrieval_availability_dominates = (
        retrieval_availability_rate > NO_GO_RETRIEVAL_AVAILABILITY_RATE
    )
    # When no private decomposition was parsed, file_selector is
    # unavailable and we publish an explicit unavailable row for it
    # (alongside the always-unavailable span/refiner/redundancy/stop).
    if file_selector_ceiling_computed:
        unavailable_ceilings = _unavailable_ceiling_records()
    else:
        unavailable_ceilings = _unavailable_ceiling_records(
            file_selector_unavailable=True,
            file_selector_unavailable_reason=(
                "fd1_private_decomposition_replay_required_for_lower_"
                "bound; public_aggregate_upper_bound_only_is_insufficient_"
                "to_authorize_v1_a"
            ),
        )
    ceiling_unavailable_count = len(unavailable_ceilings)

    stop_go = _stop_go_records(
        file_selector_ceiling_computed=file_selector_ceiling_computed,
        fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
        file_selector_lower_bound=file_selector_lower_bound,
        file_selector_lower_bound_rate=file_selector_lower_bound_rate,
        file_selector_upper_bound_rate=file_selector_upper_bound_rate,
        retrieval_availability_rate=retrieval_availability_rate,
        span_or_stopping_dominance_rate=span_or_stopping_dominance_rate,
        span_or_stopping_dominates=span_or_stopping_dominates,
        ceiling_unavailable_count=ceiling_unavailable_count,
    )

    actionability_categories_covered = len({
        r["failure_category"] for r in actionability_matrix
    })

    gates = _gate_records(
        fd1_records_decomposed=fd1_records_decomposed,
        fd1_private_manifest_record_count=fd1_manifest_count,
        audit_match=audit_match,
        actionability_categories_covered=actionability_categories_covered,
        file_selector_ceiling_computed=file_selector_ceiling_computed,
        fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
        fd1_private_decomposition_row_count=(
            pt.row_count if pt is not None else 0),
        fd1_private_decomposition_group_count=(
            pt.group_count if pt is not None else 0),
        span_or_stopping_computed_or_unavailable=True,  # always: either
        # computed (file_selector) or explicit unavailable rows exist
        forbidden_scan_pass=True,  # validated below; will flip on failure
        retrieval_availability_dominates=retrieval_availability_dominates,
        span_or_stopping_dominates=span_or_stopping_dominates,
        ceiling_unavailable_count=ceiling_unavailable_count,
        blocking_failure_count=_blocking_failure_count(fcc),
    )

    blocking_failure_count = _blocking_failure_count(fcc)

    status = _decide_status(
        audit_match=audit_match,
        blocking_failure_count=blocking_failure_count,
        fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
        file_selector_ceiling_computed=file_selector_ceiling_computed,
        retrieval_availability_dominates=retrieval_availability_dominates,
        span_or_stopping_dominates=span_or_stopping_dominates,
        ceiling_unavailable_count=ceiling_unavailable_count,
        file_selector_lower_bound_rate=file_selector_lower_bound_rate,
    )

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["fd1_artifact_read"] = True
    safe_true["fd2a1_artifact_read"] = bool(fd2a1_source_artifact_hash)
    safe_true["bea_v1_p1_audit_performed"] = audit_match
    safe_true["bea_v1_p1_actionability_matrix_built"] = True
    safe_true["bea_v1_p1_oracle_ceiling_attempted"] = True
    safe_true["fd1_private_decomposition_parsed"] = (
        bool(fd1_private_decomposition_parsed))
    safe_true["fd1_private_decomposition_lower_bound_computed"] = (
        bool(file_selector_ceiling_computed))
    # Replay provenance flags (explicit; @oracle second No-Go).
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
        fd1_committed_manifest_hash=str(
            fd1_manifest.get("manifest_hash", "") or ""),
        fd2a1_schema_version=fd2a1_source_schema_version,
        fd2a1_source_artifact_hash=fd2a1_source_artifact_hash,
        fd2a1_status=fd2a1_status,
        audit_match=audit_match,
        audit_mismatch_reason=audit_mismatch_reason,
        fd1_private_decomposition_supplied=(
            pt.path_supplied if pt is not None else False),
        fd1_private_decomposition_parsed=fd1_private_decomposition_parsed,
        fd1_private_decomposition_row_count=(
            pt.row_count if pt is not None else 0),
        fd1_private_decomposition_group_count=(
            pt.group_count if pt is not None else 0),
        fd1_private_decomposition_lower_bound=(
            file_selector_lower_bound if file_selector_lower_bound is not None
            else 0),
        fd1_private_decomposition_denominator=(
            pt.gold_file_absent_denominator if pt is not None else 0),
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
        "action_layers": list(ACTION_LAYERS),
        "failure_categories": list(FAILURE_CATEGORIES),
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "source_sampling_protocol": "bea_fd1_failure_decomposition.v1",
        "records_decomposed": fd1_records_decomposed,
        "private_manifest_record_count": fd1_manifest_count,
        "failure_reason_category": "",
        "failure_category_count_records": _failure_category_count_records(fcc),
        "source_run_records": source_runs,
        "failure_category_records": failure_category_records,
        "actionability_matrix_records": actionability_matrix,
        "oracle_ceiling_records": oracle_ceilings,
        "candidate_availability_records": candidate_availability,
        "unavailable_ceiling_records": unavailable_ceilings,
        "redundancy_tradeoff_records": redundancy_tradeoff,
        "stop_go_records": stop_go,
        "gate_records": gates,
        "private_manifest_records": _private_manifest_records(
            fd1_artifact, "fd1_committed_artifact",
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
            "signal_strength": "bea_v1_p1_actionability_audit_aggregate_only",
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
            "is_failure_attribution_only": False,
            "is_actionability_audit_only": True,
        },
    }
    scan = _v1_p1_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


# ---------------------------------------------------------------------------
# Real audit runner (read committed FD1 + FD2-A1 artifacts + optional
# FD1 private decomposition JSONL; no replay by this evaluator itself,
# but the CI workflow regenerates the private JSONL before running the
# audit so the file-selector lower bound can be computed).
# ---------------------------------------------------------------------------


def _run_audit(
    *, self_test_passed: bool, self_test_checks_total: int,
    openlocus_binary_source: str, network_mode: str,
    fd1_artifact_path: Path, fd2a1_artifact_path: Path,
    fd1_private_decomposition_jsonl: Path | None = None,
    fd1_replay_artifact: Path | None = None,
) -> dict[str, Any]:
    """Read the committed FD1 public aggregate and FD2-A1 binding
    context, optionally parse the regenerated FD1 private decomposition
    JSONL and validate the FD1 replay artifact, build the actionability
    matrix and oracle ceilings, and return the audit report. The audit
    evaluator itself never replays and never calls a provider; the CI
    workflow regenerates the private JSONL under ``$RUNNER_TEMP`` and
    writes the replay report (``fd1_replay_report.json``) before
    invoking the audit.

    Without ``fd1_private_decomposition_jsonl`` (or if the file is
    missing / unparseable / count-mismatched, OR the
    ``fd1_replay_artifact`` is missing / invalid / mismatched when a
    private JSONL was supplied), the file-selector oracle ceiling
    lower bound is unavailable and the audit honestly No-Gos to
    ``no_go_ceiling_unavailable`` with
    ``stop_go_decision = needs_fd1_private_replay_before_v1_a``.
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
    start = time.perf_counter()

    fd1_artifact, fd1_schema, fd1_hash, fd1_status = (
        _load_committed_artifact(fd1_artifact_path)
    )
    if fd1_status != "pass":
        fcc["fd1_artifact_missing" if fd1_status == "artifact_missing"
            else "fd1_artifact_parse_failed"] = 1
        return _build_unavailable_report(
            fd1_status, self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            failure_category_counts=fcc,
        )

    fd2a1_artifact, fd2a1_schema, fd2a1_hash, fd2a1_load_status = (
        _load_committed_artifact(fd2a1_artifact_path)
    )
    fd2a1_status = ""
    fd2a1_artifact_read = False
    if fd2a1_load_status == "pass":
        fd2a1_status = str(fd2a1_artifact.get("status", "") or "")
        fd2a1_artifact_read = True
        if fd2a1_status != FD2A1_RESULT_STATUS:
            # FD2-A1 status is binding context only; a mismatch is
            # recorded but does not block the audit (the audit's
            # denominator is the FD1 frame, not FD2-A1).
            fcc["fd2a1_status_mismatch"] = 1
    else:
        fcc["fd2a1_artifact_missing"
            if fd2a1_load_status == "artifact_missing"
            else "fd2a1_artifact_parse_failed"] = 1

    # Verify FD1 schema / status / counts (binding).
    audit_mismatch_reasons: list[str] = []
    if fd1_schema != FD1_SOURCE_SCHEMA_VERSION:
        fcc["fd1_schema_version_mismatch"] = 1
        audit_mismatch_reasons.append(
            f"fd1_schema_mismatch:{fd1_schema}")
    fd1_artifact_status = _fd1_status(fd1_artifact)
    if fd1_artifact_status != FD1_SOURCE_STATUS:
        fcc["fd1_status_mismatch"] = 1
        audit_mismatch_reasons.append(
            f"fd1_status_mismatch:{fd1_artifact_status}")
    if _fd1_records_decomposed(fd1_artifact) != EXPECTED_RECORDS_DECOMPOSED:
        fcc["fd1_records_decomposed_mismatch"] = 1
        audit_mismatch_reasons.append(
            f"records_decomposed_mismatch:"
            f"{_fd1_records_decomposed(fd1_artifact)}_vs_"
            f"{EXPECTED_RECORDS_DECOMPOSED}")
    fd1_manifest = _fd1_private_decomposition_manifest(fd1_artifact)
    fd1_manifest_count = int(fd1_manifest.get("record_count", 0) or 0)
    if fd1_manifest_count != EXPECTED_PRIVATE_DECOMP_ROWS:
        fcc["fd1_private_manifest_mismatch"] = 1
        audit_mismatch_reasons.append(
            f"private_manifest_count_mismatch:{fd1_manifest_count}_vs_"
            f"{EXPECTED_PRIVATE_DECOMP_ROWS}")
    if not _fd1_availability_records(fd1_artifact):
        fcc["fd1_availability_table_missing"] = 1
        audit_mismatch_reasons.append("availability_records_empty")
    if not _fd1_category_summary_records(fd1_artifact):
        fcc["fd1_category_summary_missing"] = 1
        audit_mismatch_reasons.append("category_summary_records_empty")

    audit_match = not audit_mismatch_reasons
    audit_mismatch_reason = ";".join(audit_mismatch_reasons)

    # Parse the optional FD1 private decomposition JSONL. Without it
    # (or if parse / count fails), the file-selector lower bound is
    # unavailable and the audit honestly No-Gos to
    # no_go_ceiling_unavailable. Parse failures and count mismatches
    # are recorded in the failure_category_counts.
    pt = _parse_private_decomposition_jsonl(
        fd1_private_decomposition_jsonl)
    if pt.path_supplied and not pt.file_existed:
        fcc["fd1_private_decomposition_missing"] = 1
    if pt.parse_failures > 0:
        fcc["fd1_private_decomposition_parse_failed"] = pt.parse_failures
    if pt.path_supplied and pt.file_existed and pt.parse_failures == 0:
        if pt.row_count != EXPECTED_PRIVATE_DECOMP_ROWS:
            fcc["fd1_private_decomposition_count_mismatch"] = 1
        if pt.group_count != EXPECTED_RECORDS_DECOMPOSED:
            fcc["fd1_private_decomposition_group_mismatch"] = 1

    # Validate the optional FD1 replay artifact (fail-closed;
    # @oracle second No-Go). When a private JSONL was supplied, the
    # replay artifact MUST be supplied and validated. The manifest hash
    # of the replay artifact must match the committed FD1 artifact
    # manifest hash (schema-content hash, NOT a private JSONL content
    # hash).
    committed_manifest_hash = str(
        fd1_manifest.get("manifest_hash", "") or "")
    rav = _validate_fd1_replay_artifact(
        fd1_replay_artifact, committed_manifest_hash)
    if rav.supplied and rav.failure_category:
        fcc[rav.failure_category] = max(
            fcc.get(rav.failure_category, 0), 1)

    # Compute the file-selector lower bound (no-op if rows are empty
    # or counts mismatched; the _build_audit_report re-checks
    # row_count / group_count AND replay artifact validation before
    # trusting pt.computed).
    _compute_file_selector_lower_bound(pt)

    aggregate_runtime_seconds = time.perf_counter() - start

    return _build_audit_report(
        self_test_passed=self_test_passed,
        self_test_checks_total=self_test_checks_total,
        self_test_checks_passed=None,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        fd1_artifact=fd1_artifact,
        fd1_source_schema_version=fd1_schema,
        fd1_source_artifact_hash=fd1_hash,
        fd2a1_source_schema_version=fd2a1_schema,
        fd2a1_source_artifact_hash=fd2a1_hash,
        fd2a1_status=fd2a1_status,
        audit_match=audit_match,
        audit_mismatch_reason=audit_mismatch_reason,
        failure_category_counts=fcc,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
        pt=pt,
        rav=rav,
    )


# ---------------------------------------------------------------------------
# Synthetic FD1 artifact (self-test only)
# ---------------------------------------------------------------------------


def _build_synthetic_fd1_artifact() -> dict[str, Any]:
    """Synthetic FD1 public aggregate for self-test.

    Mirrors the committed FD1 artifact's public shape exactly:
    source_run_records (2: BEA-4 120 / BEA-5 119), 12-category enum,
    availability_records (48), category_summary_records (16), private
    decomposition manifest (86040). Never written to any committed
    artifact; in-memory only.
    """
    sr = [
        {"source_phase": "BEA-4", "source_ci_run_id": "27957586271",
         "replayed_successful_records": 120, "records_attempted_total": 120,
         "contextbench_successful": 80, "repoqa_successful": 40},
        {"source_phase": "BEA-5", "source_ci_run_id": "28003522632",
         "replayed_successful_records": 119, "records_attempted_total": 186,
         "contextbench_successful": 82, "repoqa_successful": 37},
    ]
    # availability_records: 12 categories x 4 (sp, bm) buckets = 48.
    av: list[dict[str, Any]] = []
    # category_summary_records: only available categories with affected>0.
    cs: list[dict[str, Any]] = []
    # Synthetic affected counts (mirror the committed FD1 ratios roughly
    # but are NOT the real CI numbers — self-test only).
    synth_affected = {
        "BEA-4": {
            "contextbench": {
                "gold_file_absent": 62, "correct_file_wrong_span": 11,
                "budget_spent_on_low_marginal_gain": 38,
                "latency_without_quality_gain": 80,
                "gold_span_absent": 0, "too_many_anchor_slots": 0,
                "early_stop_too_early": 0,
            },
            "repoqa": {
                "gold_file_absent": 17, "correct_file_wrong_span": 14,
                "budget_spent_on_low_marginal_gain": 39,
                "latency_without_quality_gain": 40,
                "gold_span_absent": 0, "too_many_anchor_slots": 0,
                "early_stop_too_early": 0,
            },
        },
        "BEA-5": {
            "contextbench": {
                "gold_file_absent": 24, "correct_file_wrong_span": 23,
                "budget_spent_on_low_marginal_gain": 82,
                "latency_without_quality_gain": 82,
                "gold_span_absent": 0, "too_many_anchor_slots": 0,
                "early_stop_too_early": 0,
            },
            "repoqa": {
                "gold_file_absent": 16, "correct_file_wrong_span": 13,
                "budget_spent_on_low_marginal_gain": 37,
                "latency_without_quality_gain": 37,
                "gold_span_absent": 0, "too_many_anchor_slots": 0,
                "early_stop_too_early": 0,
            },
        },
    }
    # Per-(sp, bm) total records.
    sp_bm_totals = {
        ("BEA-4", "contextbench"): 80, ("BEA-4", "repoqa"): 40,
        ("BEA-5", "contextbench"): 82, ("BEA-5", "repoqa"): 37,
    }
    for category in FAILURE_CATEGORIES:
        if category in CANDIDATE_UNAVAILABLE_CATEGORIES:
            availability = "unavailable_no_support_label"
        elif category in CEILING_UNAVAILABLE_CATEGORIES:
            availability = "unavailable_missing_trace"
        else:
            availability = "available"
        for (sp, bm), total in sp_bm_totals.items():
            av.append({
                "source_phase": sp, "benchmark": bm,
                "category": category,
                "category_availability": availability,
                "record_count": total,
            })
            affected = synth_affected.get(sp, {}).get(bm, {}).get(category, 0)
            if affected > 0:
                cs.append({
                    "source_phase": sp, "benchmark": bm,
                    "category": category,
                    "category_availability": availability,
                    "record_count": affected,
                })
    return {
        "schema_version": FD1_SOURCE_SCHEMA_VERSION,
        "status": FD1_SOURCE_STATUS,
        "records_decomposed": EXPECTED_RECORDS_DECOMPOSED,
        "source_run_records": sr,
        "availability_records": av,
        "category_summary_records": cs,
        "private_decomposition_manifest": {
            "records_written": True,
            "record_count": EXPECTED_PRIVATE_DECOMP_ROWS,
            "schema_version": bea_fd1.PRIVATE_DECOMP_SCHEMA_VERSION,
            "manifest_hash": "a" * 64,
            "storage_class": "tmp_private",
            "path_publicly_serialized": False,
        },
    }


def _build_synthetic_fd2a1_artifact() -> dict[str, Any]:
    """Synthetic FD2-A1 binding-context artifact (self-test only)."""
    return {
        "schema_version": FD2A1_SOURCE_SCHEMA_VERSION,
        "status": FD2A1_RESULT_STATUS,
        "records_attributed": 38,
    }


def _build_synthetic_fd1_replay_artifact(
    path: Path | None = None,
    *,
    manifest_hash: str = "a" * 64,
    status: str = "bea_fd1_decomposition_pass",
    records_decomposed: int = EXPECTED_RECORDS_DECOMPOSED,
    manifest_record_count: int = EXPECTED_PRIVATE_DECOMP_ROWS,
    manifest_records_written: bool = True,
    manifest_path_publicly_serialized: bool = False,
    forbidden_scan_pass: bool = True,
) -> dict[str, Any]:
    """Synthetic FD1 replay report for self-test (mirrors the public
    shape of ``bea_fd1_failure_decomposition``'s output). If ``path``
    is supplied, also writes the JSON to disk so the validator can
    load it."""
    art = {
        "schema_version": "bea_fd1_failure_decomposition.v1",
        "status": status,
        "records_decomposed": records_decomposed,
        "private_decomposition_manifest": {
            "records_written": manifest_records_written,
            "record_count": manifest_record_count,
            "schema_version": bea_fd1.PRIVATE_DECOMP_SCHEMA_VERSION,
            "manifest_hash": manifest_hash,
            "storage_class": "tmp_private",
            "path_publicly_serialized": manifest_path_publicly_serialized,
        },
        "forbidden_scan": {
            "status": "pass" if forbidden_scan_pass else "fail",
            "violations_count": 0,
            "categories": {},
        },
    }
    if path is not None:
        path.write_text(json.dumps(art), encoding="utf-8")
    return art


def _build_synthetic_private_decomposition_jsonl(
    path: Path,
    *,
    gold_file_absent_count: int = 119,
    recoverable_lower_bound: int = 100,
) -> int:
    """Write a synthetic FD1 private decomposition JSONL to ``path``
    for self-test.

    Mirrors the FD1 private row schema exactly: each row has
    ``phase_run_id, source_phase, benchmark, private_record_id,
    policy_arm, category, baseline_arm, treatment_arm, metric,
    treatment_value, baseline_value, loss, delta,
    category_availability``. 239 records × 5 baselines × 12 categories
    × 6 metrics = 86040 rows (matches EXPECTED_PRIVATE_DECOMP_ROWS).

    The first ``gold_file_absent_count`` records are constructed so
    that v0.3 file_recall@10 == 0 and success_rate == 0 (gold file
    absent). Of those, the first ``recoverable_lower_bound`` records
    have at least one baseline arm with baseline_value > 0 for
    file_recall@10 (recoverable lower bound); the remaining
    ``gold_file_absent_count - recoverable_lower_bound`` records have
    all baselines at 0 (unrecoverable / candidate unavailable).

    Returns the number of rows written (86040).
    """
    arms_v03 = "bea_v0_3_anchor_span_latency"
    baselines = (
        "bea_v0_2_diversity_risk", "bea_v0", "bm25_prefix_same_budget",
        "agreement_only_same_budget", "rrf_same_budget",
    )
    categories = FAILURE_CATEGORIES
    metrics = (
        "file_recall@10", "mrr", "span_f0.5@10", "success_rate",
        "quality_per_latency", "latency_seconds",
    )
    rows_written = 0
    with path.open("w", encoding="utf-8") as fh:
        for rid_idx in range(EXPECTED_RECORDS_DECOMPOSED):
            rid = f"synth-record-{rid_idx:04d}"
            sp = "BEA-4" if rid_idx < 120 else "BEA-5"
            bm = "contextbench" if rid_idx % 2 == 0 else "repoqa"
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
                                # v0.3 selected no gold file: file_recall
                                # and success are 0; other quality
                                # metrics also 0.
                                t_val = 0.0
                                # Baselines: for recoverable records,
                                # the FIRST baseline (bea_v0_2) finds
                                # the gold file (file_recall > 0);
                                # other baselines do not. For
                                # non-recoverable records, no baseline
                                # finds gold.
                                if (metric == "file_recall@10"
                                        and is_recoverable
                                        and baseline == baselines[0]):
                                    b_val = 1.0
                                else:
                                    b_val = 0.0
                            else:
                                # Not gold-absent: v0.3 found the file.
                                t_val = 1.0 if metric in (
                                    "file_recall@10", "success_rate",
                                    "mrr") else 0.5
                                b_val = 0.5
                        loss = max(0.0, b_val - t_val) if metric != "latency_seconds" else max(0.0, t_val - b_val)
                        delta = t_val - b_val
                        row = {
                            "phase_run_id": "v1p1-self-test",
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


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic FD1 aggregate)
# ---------------------------------------------------------------------------


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []

    # --- G1: Identity ---
    checks.append(_check("schema_version_value",
        SCHEMA_VERSION == "bea_v1_p1_actionability_audit.v1"))
    checks.append(_check("claim_level_value",
        CLAIM_LEVEL == "bea_v1_p1_actionability_audit_only"))
    checks.append(_check("mode_value", MODE == "bea_v1_p1_actionability_audit"))
    checks.append(_check("phase_value", PHASE == "BEA-v1-P1"))
    checks.append(_check("generated_by_value",
        GENERATED_BY == "eval/bea_v1_p1_actionability_audit.py"))

    # --- G2: Safe true / false flags ---
    for flag in ("aggregate_only_public_artifact", "diagnostic_only",
                 "bea_v1_p1_audit_evaluator_no_replay_executed",
                 "bea_v1_p1_audit_evaluator_no_selector_executed",
                 "bea_v1_p1_audit_evaluator_no_retrieval_executed",
                 "bea_v1_p1_audit_evaluator_no_provider_calls",
                 "bea_v1_p1_audit_evaluator_no_weight_tuning",
                 "bea_v1_p1_audit_evaluator_no_role_proxy"):
        checks.append(_check(f"safe_true_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is True))
    # Replay provenance flags default to false (local no-private default).
    for flag in ("fd1_private_decomposition_replay_supplied",
                 "fd1_private_decomposition_replay_validated",
                 "fd1_private_decomposition_replay_executed_by_workflow"):
        checks.append(_check(f"safe_false_{flag}",
            SAFE_TRUE_FLAGS.get(flag) is False))
    for flag in ("role_proxy_assigned",
                 "posthoc_threshold_search",
                 "weights_tuned_during_bea_v1_p1",
                 "algorithm_changed_during_bea_v1_p1",
                 "v04_full_matrix_claimed",
                 "v1_a_selector_executed",
                 "v1_a_coverage_preserving_selector_promoted",
                 "fd2b_executed", "fd2c_executed",
                 "p4_executed", "p5_executed",
                 "v031_tuning_executed", "v032_tuning_executed",
                 "b16k_executed",
                 "default_should_change", "promotion_ready",
                 "heldout_validation_claimed",
                 "provider_calls_made", "remote_provider_calls_made"):
        checks.append(_check(f"false_{flag}",
            DEFAULT_FALSE_FLAGS.get(flag) is False))
    # No role_proxy_used / target_support_proxy_used public fields.
    checks.append(_check("no_role_proxy_used_field",
        "role_proxy_used" not in SAFE_TRUE_FLAGS))
    checks.append(_check("no_target_support_proxy_used_field",
        "target_support_proxy_used" not in SAFE_TRUE_FLAGS))

    # --- G3: Action layers (6) and cell classes (5) ---
    checks.append(_check("action_layers_count_6", len(ACTION_LAYERS) == 6))
    for layer in ACTION_LAYERS:
        checks.append(_check(f"action_layer_present_{layer}",
            layer in ACTION_LAYERS))
    checks.append(_check("cell_classes_count_5", len(CELL_CLASSES) == 5))
    for cc in CELL_CLASSES:
        checks.append(_check(f"cell_class_present_{cc}", cc in CELL_CLASSES))

    # --- G4: FD1 categories (12) and unavailable sets ---
    checks.append(_check("failure_categories_count_12",
        len(FAILURE_CATEGORIES) == 12))
    for cat in FAILURE_CATEGORIES:
        checks.append(_check(f"failure_category_present_{cat}",
            cat in FAILURE_CATEGORIES))
    checks.append(_check("candidate_unavailable_count_3",
        len(CANDIDATE_UNAVAILABLE_CATEGORIES) == 3))
    for cat in CANDIDATE_UNAVAILABLE_CATEGORIES:
        checks.append(_check(f"candidate_unavailable_{cat}",
            cat in CANDIDATE_UNAVAILABLE_CATEGORIES))
    checks.append(_check("ceiling_unavailable_count_2",
        len(CEILING_UNAVAILABLE_CATEGORIES) == 2))
    for cat in CEILING_UNAVAILABLE_CATEGORIES:
        checks.append(_check(f"ceiling_unavailable_{cat}",
            cat in CEILING_UNAVAILABLE_CATEGORIES))
    # 12 = 7 available + 3 candidate_unavailable + 2 ceiling_unavailable.
    checks.append(_check("available_categories_count_7",
        len(AVAILABLE_CATEGORIES) == 7))

    # --- G5: Actionability matrix completeness ---
    matrix = _actionability_matrix_records()
    checks.append(_check("matrix_rows_72", len(matrix) == 72))
    matrix_keys = {(r["failure_category"], r["action_layer"]) for r in matrix}
    for cat in FAILURE_CATEGORIES:
        for layer in ACTION_LAYERS:
            checks.append(_check(f"matrix_has_{cat}_{layer}",
                (cat, layer) in matrix_keys))
    # candidate_unavailable categories: all 6 cells candidate_unavailable.
    for cat in CANDIDATE_UNAVAILABLE_CATEGORIES:
        for layer in ACTION_LAYERS:
            cell = next(r for r in matrix
                        if r["failure_category"] == cat
                        and r["action_layer"] == layer)
            checks.append(_check(f"matrix_{cat}_{layer}_candidate_unavailable",
                cell["cell_class"] == "candidate_unavailable"))
    # ceiling_unavailable categories: all 6 cells ceiling_unavailable.
    for cat in CEILING_UNAVAILABLE_CATEGORIES:
        for layer in ACTION_LAYERS:
            cell = next(r for r in matrix
                        if r["failure_category"] == cat
                        and r["action_layer"] == layer)
            checks.append(_check(
                f"matrix_{cat}_{layer}_ceiling_unavailable",
                cell["cell_class"] == "ceiling_unavailable_insufficient_trace"))
    # Each available category must have at least one direct_actionable cell.
    for cat in AVAILABLE_CATEGORIES:
        direct_count = sum(1 for r in matrix
                           if r["failure_category"] == cat
                           and r["cell_class"] == "direct_actionable")
        checks.append(_check(f"matrix_{cat}_has_direct_actionable",
            direct_count >= 1))
    # gold_file_absent: file_selector cell is direct_actionable.
    gold_fs = next(r for r in matrix
                   if r["failure_category"] == "gold_file_absent"
                   and r["action_layer"] == "file_selector")
    checks.append(_check("matrix_gold_file_absent_file_selector_direct",
        gold_fs["cell_class"] == "direct_actionable"))
    # latency_without_quality_gain: non_actionable_accounting is direct.
    lat_na = next(r for r in matrix
                  if r["failure_category"] == "latency_without_quality_gain"
                  and r["action_layer"] == "non_actionable_accounting")
    checks.append(_check("matrix_latency_non_actionable_direct",
        lat_na["cell_class"] == "direct_actionable"))
    # early_stop_too_early: stopping_scheduler is direct.
    es_ts = next(r for r in matrix
                 if r["failure_category"] == "early_stop_too_early"
                 and r["action_layer"] == "stopping_scheduler")
    checks.append(_check("matrix_early_stop_stopping_direct",
        es_ts["cell_class"] == "direct_actionable"))

    # --- G6: Statuses enum ---
    for status in STATUSES:
        checks.append(_check(f"status_enum_{status}", isinstance(status, str)))
    checks.append(_check("statuses_count_8", len(STATUSES) == 8))
    checks.append(_check("allowed_real_run_statuses_count_5",
        len(ALLOWED_REAL_RUN_STATUSES) == 5))
    for s in ALLOWED_REAL_RUN_STATUSES:
        checks.append(_check(f"allowed_status_{s}", s in STATUSES))

    # --- G7: Forbidden scanner ---
    safe_sample = {
        "schema_version": SCHEMA_VERSION,
        "status": "bea_v1_p1_actionability_audit_pass",
        "actionability_matrix_records": [
            {"failure_category": "gold_file_absent",
             "action_layer": "file_selector",
             "cell_class": "direct_actionable",
             "is_direct_actionable": True,
             "is_indirect_actionable": False,
             "is_candidate_unavailable": False,
             "is_ceiling_unavailable": False},
        ],
        "oracle_ceiling_records": [
            {"ceiling_name": "file_selector",
             "ceiling_class": "computed_upper_bound_only",
             "denominator": 119,
             "recoverable_count_upper_bound": 119,
             "recoverable_count_lower_bound": None,
             "recoverable_rate_upper_bound": 0.4979,
             "recoverable_rate_lower_bound": None,
             "ceiling_basis": "fd1_public_aggregate_records_only",
             "ceiling_reason": "candidate_pool_overlap_unavailable"},
        ],
        "private_manifest_records": [{
            "manifest_name": "fd1_private_decomposition_manifest",
            "records_written": True, "record_count": 86040,
            "schema_version": bea_fd1.PRIVATE_DECOMP_SCHEMA_VERSION,
            "manifest_hash": "a" * 64,
            "storage_class": "fd1_committed_artifact",
            "path_publicly_serialized": False,
        }],
        "framing": {"signal_strength":
            "bea_v1_p1_actionability_audit_aggregate_only"},
        "fd1_source_artifact_hash": "b" * 64,
        "fd2a1_source_artifact_hash": "c" * 64,
        "fd2a1_result_checkpoint": FD2A1_RESULT_CHECKPOINT,
    }
    checks.append(_check("scanner_allows_safe", not _scan_v1_p1(safe_sample)))
    # Forbidden leaks.
    for fk in ("private_trace_dir", "per_record_buckets",
               "per_record_attribution", "per_record_matrix",
               "objective_config_payload", "fd1_category_weights_payload",
               "candidate_paths", "candidate_keys", "query_text",
               "gold_paths", "gold_lines", "gold_spans", "snippets",
               "selected_order", "private_record_ids", "private_record_id",
               "raw_score_row", "raw_decision_row",
               "weight_derivation_payload",
               "fd1_source_artifact_path", "fd2a1_source_artifact_path",
               "fd2a_source_artifact_path",
               "winner", "calibration", "method_winner",
               "recommended_default", "ranking", "decision",
               "hard_gates", "failure_category_counts",
               "actionability_matrix_counts", "oracle_ceiling_counts",
               "self_test_checks", "checks",
               "role_proxy", "role_proxy_assignment",
               "is_v04_repair", "is_fd2_b", "is_fd2_c",
               "is_p4", "is_p5", "is_v031_tuning", "is_v032_tuning",
               "is_b16k", "is_selector_phase", "is_acquisition_phase",
               "phase_run_id", "run_id", "benchmark_row_id",
               "private_decomposition_path", "private_decomposition_file"):
        leaked = dict(safe_sample)
        leaked[fk] = "leak"
        checks.append(_check(f"scanner_rejects_{fk}", bool(_scan_v1_p1(leaked))))

    # --- G8: Fail-closed enforcement ---
    try:
        _enforce_v1_p1_no_forbidden(safe_sample)
        checks.append(_check("fail_closed_clean", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean", False))
    for lk in ("private_trace_dir", "per_record_buckets",
               "gold_paths", "winner", "hard_gates",
               "self_test_checks", "fd1_source_artifact_path",
               "fd2a1_source_artifact_path",
               "is_v04_repair", "is_fd2_b"):
        leaked = dict(safe_sample)
        leaked[lk] = "leak"
        try:
            _enforce_v1_p1_no_forbidden(leaked)
            checks.append(_check(f"fail_closed_{lk}", False))
        except SystemExit:
            checks.append(_check(f"fail_closed_{lk}", True))

    # --- G9: Synthetic FD1 artifact ---
    fd1_art = _build_synthetic_fd1_artifact()
    checks.append(_check("synth_fd1_schema",
        fd1_art["schema_version"] == FD1_SOURCE_SCHEMA_VERSION))
    checks.append(_check("synth_fd1_status",
        fd1_art["status"] == FD1_SOURCE_STATUS))
    checks.append(_check("synth_fd1_records_decomposed",
        fd1_art["records_decomposed"] == EXPECTED_RECORDS_DECOMPOSED))
    checks.append(_check("synth_fd1_manifest_count",
        fd1_art["private_decomposition_manifest"]["record_count"]
        == EXPECTED_PRIVATE_DECOMP_ROWS))
    checks.append(_check("synth_fd1_availability_48",
        len(fd1_art["availability_records"]) == 48))
    checks.append(_check("synth_fd1_source_runs_2",
        len(fd1_art["source_run_records"]) == 2))
    # Synthetic FD1 counts: 80 + 40 + 82 + 37 = 239 total.
    sp_totals = _total_records_per_source_phase(fd1_art)
    checks.append(_check("synth_sp_totals_239",
        sum(sp_totals.values()) == EXPECTED_RECORDS_DECOMPOSED))

    # --- G10: Build audit report (synthetic, audit_match=True) ---
    # Write a synthetic FD1 private decomposition JSONL with 86040 rows
    # (239 records × 5 baselines × 12 categories × 6 metrics). 119
    # records are gold_file_absent; 100 of those are recoverable (one
    # baseline found the gold file) → lower bound = 100.
    synth_private_jsonl = Path(tempfile.mkdtemp(prefix="v1p1_pt_")) / "bea_fd1.decomposition.jsonl"
    synth_rows_written = _build_synthetic_private_decomposition_jsonl(
        synth_private_jsonl, gold_file_absent_count=119,
        recoverable_lower_bound=100,
    )
    checks.append(_check("synth_private_rows_86040",
        synth_rows_written == EXPECTED_PRIVATE_DECOMP_ROWS))
    synth_pt = _parse_private_decomposition_jsonl(synth_private_jsonl)
    checks.append(_check("synth_pt_path_supplied",
        synth_pt.path_supplied is True))
    checks.append(_check("synth_pt_file_existed",
        synth_pt.file_existed is True))
    checks.append(_check("synth_pt_row_count_86040",
        synth_pt.row_count == EXPECTED_PRIVATE_DECOMP_ROWS))
    checks.append(_check("synth_pt_group_count_239",
        synth_pt.group_count == EXPECTED_RECORDS_DECOMPOSED))
    checks.append(_check("synth_pt_parse_failures_0",
        synth_pt.parse_failures == 0))
    _compute_file_selector_lower_bound(synth_pt)
    checks.append(_check("synth_pt_computed", synth_pt.computed is True))
    checks.append(_check("synth_pt_denominator_119",
        synth_pt.gold_file_absent_denominator == 119))
    checks.append(_check("synth_pt_lower_bound_100",
        synth_pt.recoverable_lower_bound == 100))
    checks.append(_check("synth_pt_unrecoverable_19",
        synth_pt.unrecoverable_candidate_unavailable == 19))
    checks.append(_check("synth_pt_retrieval_rate",
        abs(synth_pt.retrieval_availability_rate - (19.0 / 119.0)) < 1e-6))
    checks.append(_check("synth_pt_lower_bound_rate",
        abs(synth_pt.file_selector_lower_bound_rate - (100.0 / 239.0))
        < 1e-6))

    report = _build_audit_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd2a1_source_schema_version=FD2A1_SOURCE_SCHEMA_VERSION,
        fd2a1_source_artifact_hash="c" * 64,
        fd2a1_status=FD2A1_RESULT_STATUS,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
        pt=synth_pt,
        rav=_validate_fd1_replay_artifact(
            None, "a" * 64),  # not supplied → not validated; but
            # synth_pt.path_supplied is True so this should force
            # fd1_private_decomposition_parsed=False. We patch below.
    )
    # The above call uses rav=None-supplied (not validated) which would
    # force the private decomposition to be untrusted. For the self-test
    # we need a VALIDATED rav to exercise the pass path. Build a real
    # synthetic replay artifact on disk and validate it.
    synth_replay_path = Path(tempfile.mkdtemp(prefix="v1p1_rav_")) / "fd1_replay_report.json"
    _build_synthetic_fd1_replay_artifact(synth_replay_path)
    synth_rav = _validate_fd1_replay_artifact(synth_replay_path, "a" * 64)
    checks.append(_check("synth_rav_supplied", synth_rav.supplied is True))
    checks.append(_check("synth_rav_parsed", synth_rav.parsed is True))
    checks.append(_check("synth_rav_validated", synth_rav.validated is True))
    checks.append(_check("synth_rav_manifest_hash_match",
        synth_rav.manifest_hash_match is True))
    checks.append(_check("synth_rav_forbidden_scan_pass",
        synth_rav.replay_forbidden_scan_pass is True))
    checks.append(_check("synth_rav_no_failure_category",
        synth_rav.failure_category == ""))
    # Rebuild report with validated rav.
    report = _build_audit_report(
        self_test_passed=True, self_test_checks_total=0,
        self_test_checks_passed=None,
        openlocus_binary_source="self_test", network_mode="self_test",
        fd1_artifact=fd1_art,
        fd1_source_schema_version=FD1_SOURCE_SCHEMA_VERSION,
        fd1_source_artifact_hash="b" * 64,
        fd2a1_source_schema_version=FD2A1_SOURCE_SCHEMA_VERSION,
        fd2a1_source_artifact_hash="c" * 64,
        fd2a1_status=FD2A1_RESULT_STATUS,
        audit_match=True, audit_mismatch_reason="",
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES_AUDIT},
        aggregate_runtime_seconds=0.5,
        pt=synth_pt,
        rav=synth_rav,
    )
    # Records-only shape: every required table is a list.
    required_tables = (
        "source_run_records", "failure_category_records",
        "actionability_matrix_records", "oracle_ceiling_records",
        "candidate_availability_records", "unavailable_ceiling_records",
        "redundancy_tradeoff_records", "stop_go_records",
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
    for ff in ("private_trace_dir", "per_record_buckets",
               "objective_config_payload", "candidate_paths",
               "gold_paths", "selected_order", "winner", "calibration",
               "hard_gates", "failure_category_counts",
               "actionability_matrix_counts", "oracle_ceiling_counts",
               "self_test_checks",
               "fd1_source_artifact_path", "fd2a1_source_artifact_path",
               "role_proxy_used", "target_support_proxy_used",
               "is_v04_repair", "is_fd2_b", "is_fd2_c",
               "is_p4", "is_p5", "is_v031_tuning", "is_b16k"):
        checks.append(_check(f"no_top_level_{ff}", ff not in report))
    # Self-scan clean.
    checks.append(_check("self_scan_clean", not _scan_v1_p1(report)))

    # --- G11: Records-only natural-key uniqueness ---
    checks.append(_check("srr_unique", not _check_unique_records(
        report.get("source_run_records", []), _srr_natural_key,
        "source_run_records")))
    checks.append(_check("fcr_unique", not _check_unique_records(
        report.get("failure_category_records", []), _fcr_natural_key,
        "failure_category_records")))
    checks.append(_check("amr_unique", not _check_unique_records(
        report.get("actionability_matrix_records", []), _amr_natural_key,
        "actionability_matrix_records")))
    checks.append(_check("ocr_unique", not _check_unique_records(
        report.get("oracle_ceiling_records", []), _ocr_natural_key,
        "oracle_ceiling_records")))
    checks.append(_check("car_unique", not _check_unique_records(
        report.get("candidate_availability_records", []), _car_natural_key,
        "candidate_availability_records")))
    checks.append(_check("ucr_unique", not _check_unique_records(
        report.get("unavailable_ceiling_records", []), _ucr_natural_key,
        "unavailable_ceiling_records")))
    checks.append(_check("rtr_unique", not _check_unique_records(
        report.get("redundancy_tradeoff_records", []), _rtr_natural_key,
        "redundancy_tradeoff_records")))
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

    # --- G12: All 12 FD1 categories in actionability_matrix_records ---
    amr_cats = {r["failure_category"]
                for r in report.get("actionability_matrix_records", [])}
    for cat in FAILURE_CATEGORIES:
        checks.append(_check(f"amr_has_{cat}", cat in amr_cats))
    # Matrix has 72 rows (12 x 6).
    checks.append(_check("amr_rows_72",
        len(report.get("actionability_matrix_records", [])) == 72))

    # --- G13: File-selector oracle ceiling computed (synthetic) ---
    # With synthetic private decomposition (lower bound = 100), the
    # ceiling class is now computed_private_lower_bound_and_public_upper_bound
    # and the lower bound is published.
    ocr_rows = report.get("oracle_ceiling_records", [])
    fs_rows = [r for r in ocr_rows if r["ceiling_name"] == "file_selector"]
    checks.append(_check("oracle_ceiling_file_selector_computed",
        len(fs_rows) == 1))
    if fs_rows:
        fs = fs_rows[0]
        checks.append(_check("fs_ceiling_class_private_lower_and_upper",
            fs["ceiling_class"]
            == "computed_private_lower_bound_and_public_upper_bound"))
        checks.append(_check("fs_ceiling_basis",
            fs["ceiling_basis"] == "fd1_private_decomposition_replay"))
        checks.append(_check("fs_denominator_positive",
            fs["denominator"] > 0))
        checks.append(_check("fs_upper_bound_eq_denominator",
            fs["recoverable_count_upper_bound"] == fs["denominator"]))
        checks.append(_check("fs_lower_bound_100",
            fs["recoverable_count_lower_bound"] == 100))
        checks.append(_check("fs_rate_positive",
            fs["recoverable_rate_upper_bound"] > 0.0))
        checks.append(_check("fs_lower_bound_rate_positive",
            fs["recoverable_rate_lower_bound"] > 0.0))
        checks.append(_check("fs_unrecoverable_19",
            fs["unrecoverable_candidate_unavailable_count"] == 19))
        checks.append(_check("fs_retrieval_rate_0_16",
            abs(fs["retrieval_availability_rate"] - (19.0 / 119.0)) < 1e-6))
    # Synthetic affected gold_file_absent = 62+17+24+16 = 119.
    fcr_rows = report.get("failure_category_records", [])
    gfa = next((r for r in fcr_rows
                if r["failure_category"] == "gold_file_absent"), {})
    checks.append(_check("synth_gold_file_absent_119",
        gfa.get("affected_record_count") == 119))

    # --- G14: Unavailable ceiling records (3: span/refiner/redundancy/stop) ---
    ucr_rows = report.get("unavailable_ceiling_records", [])
    ucr_names = {r["ceiling_name"] for r in ucr_rows}
    for name in ("span_refiner", "setwise_packer_redundancy",
                 "stopping_scheduler"):
        checks.append(_check(f"unavailable_has_{name}", name in ucr_names))
    checks.append(_check("unavailable_count_3", len(ucr_rows) == 3))
    for r in ucr_rows:
        checks.append(_check("ucr_class_unavailable",
            r["ceiling_class"] == "unavailable"))
        checks.append(_check("ucr_basis",
            r["ceiling_basis"] == "fd1_public_aggregate_records_only"))

    # --- G15: Stop/go records ---
    sgr_rows = report.get("stop_go_records", [])
    checks.append(_check("sgr_count_1", len(sgr_rows) == 1))
    if sgr_rows:
        sgr = sgr_rows[0]
        for field in ("stop_go_decision", "stop_go_reason",
                      "fd1_private_decomposition_parsed",
                      "file_selector_ceiling_computed",
                      "file_selector_lower_bound",
                      "file_selector_lower_bound_rate",
                      "file_selector_upper_bound_rate",
                      "retrieval_availability_rate",
                      "span_or_stopping_dominance_rate",
                      "span_or_stopping_dominates",
                      "ceiling_unavailable_count"):
            checks.append(_check(f"sgr_has_{field}", field in sgr)
                          if False else _check(f"sgr_has_{field}",
                                               field in sgr))
        # Synthetic: file_selector ceiling computed with lower_bound=100
        # (100/239 = 0.418 > 0.05) and retrieval_availability 19/119.
        checks.append(_check("sgr_fs_ceiling_computed",
            sgr["file_selector_ceiling_computed"] is True))
        checks.append(_check("sgr_fs_lower_bound_positive",
            sgr["file_selector_lower_bound"] == 100))
        checks.append(_check("sgr_fs_lower_bound_rate_positive",
            sgr["file_selector_lower_bound_rate"] > 0.0))
        # Synthetic 100/239 = 0.418 > 0.05; retrieval 19/119 = 0.160 < 0.50
        # → go.
        checks.append(_check("sgr_decision_go",
            sgr["stop_go_decision"] == "go_v1_a_coverage_preserving_selector"))

    # --- G16: Gate records ---
    gr_rows = report.get("gate_records", [])
    gate_names = {r.get("gate") for r in gr_rows if isinstance(r, dict)}
    for gate in ("fd1_records_decomposed",
                 "fd1_private_manifest_record_count",
                 "audit_match", "actionability_categories_covered",
                 "file_selector_ceiling_computed",
                 "span_or_stopping_computed_or_unavailable",
                 "forbidden_scan_pass",
                 "retrieval_availability_dominates",
                 "span_or_stopping_dominates",
                 "ceiling_unavailable_count",
                 "blocking_failure_count"):
        checks.append(_check(f"gate_has_{gate}", gate in gate_names))
    # Synthetic audit_match=True → audit_match gate passes.
    audit_match_gate = next((r for r in gr_rows
                            if r.get("gate") == "audit_match"), {})
    checks.append(_check("audit_match_gate_passed",
        audit_match_gate.get("passed") is True))
    fs_gate = next((r for r in gr_rows
                   if r.get("gate") == "fd1_records_decomposed"), {})
    checks.append(_check("fd1_records_decomposed_gate_passed",
        fs_gate.get("passed") is True))
    pm_gate = next((r for r in gr_rows
                   if r.get("gate") == "fd1_private_manifest_record_count"), {})
    checks.append(_check("fd1_private_manifest_gate_passed",
        pm_gate.get("passed") is True))

    # --- G17: Private manifest records ---
    pmr_rows = report.get("private_manifest_records", [])
    checks.append(_check("pmr_count_1", len(pmr_rows) == 1))
    if pmr_rows:
        pmr = pmr_rows[0]
        checks.append(_check("pmr_records_written_true",
            pmr.get("records_written") is True))
        checks.append(_check("pmr_record_count_86040",
            pmr.get("record_count") == EXPECTED_PRIVATE_DECOMP_ROWS))
        checks.append(_check("pmr_path_not_serialized",
            pmr.get("path_publicly_serialized") is False))
        checks.append(_check("pmr_hash_64",
            len(pmr.get("manifest_hash", "")) == 64))

    # --- G18: Status decision logic ---
    # With synthetic private decomposition (119 gold_file_absent, 100
    # recoverable → lower bound rate = 100/239 = 0.418 > 0.05; retrieval
    # availability = 19/119 = 0.160 < 0.50; span/stopping does not
    # dominate) → status pass.
    checks.append(_check("synth_status_pass",
        report.get("status") == "bea_v1_p1_actionability_audit_pass"))
    # No private decomposition parsed → no_go_ceiling_unavailable.
    status_no_pt = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=False,
        file_selector_ceiling_computed=False,
        retrieval_availability_dominates=False,
        span_or_stopping_dominates=False,
        ceiling_unavailable_count=4,
        file_selector_lower_bound_rate=0.0,
    )
    checks.append(_check("decide_status_no_private",
        status_no_pt == "no_go_ceiling_unavailable"))
    # Private parsed but file_selector ceiling not computed →
    # no_go_no_file_selector_ceiling.
    status_no_fs = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        file_selector_ceiling_computed=False,
        retrieval_availability_dominates=False,
        span_or_stopping_dominates=False,
        ceiling_unavailable_count=3,
        file_selector_lower_bound_rate=0.0,
    )
    checks.append(_check("decide_status_no_fs",
        status_no_fs == "no_go_no_file_selector_ceiling"))
    status_retrieval = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        file_selector_ceiling_computed=True,
        retrieval_availability_dominates=True,
        span_or_stopping_dominates=False,
        ceiling_unavailable_count=3,
        file_selector_lower_bound_rate=0.5,
    )
    checks.append(_check("decide_status_retrieval",
        status_retrieval == "no_go_retrieval_availability_limit"))
    status_span = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        file_selector_ceiling_computed=True,
        retrieval_availability_dominates=False,
        span_or_stopping_dominates=True,
        ceiling_unavailable_count=3,
        file_selector_lower_bound_rate=0.1,
    )
    checks.append(_check("decide_status_span",
        status_span == "no_go_span_or_stopping_dominates"))
    # Lower bound rate below material threshold → no_go_no_file_selector_ceiling.
    status_low_upside = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        file_selector_ceiling_computed=True,
        retrieval_availability_dominates=False,
        span_or_stopping_dominates=False,
        ceiling_unavailable_count=3,
        file_selector_lower_bound_rate=0.01,
    )
    checks.append(_check("decide_status_low_upside",
        status_low_upside == "no_go_no_file_selector_ceiling"))
    status_pass = _decide_status(
        audit_match=True, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        file_selector_ceiling_computed=True,
        retrieval_availability_dominates=False,
        span_or_stopping_dominates=False,
        ceiling_unavailable_count=3,
        file_selector_lower_bound_rate=0.5,
    )
    checks.append(_check("decide_status_pass",
        status_pass == "bea_v1_p1_actionability_audit_pass"))
    status_blocking = _decide_status(
        audit_match=True, blocking_failure_count=1,
        fd1_private_decomposition_parsed=True,
        file_selector_ceiling_computed=True,
        retrieval_availability_dominates=False,
        span_or_stopping_dominates=False,
        ceiling_unavailable_count=0,
        file_selector_lower_bound_rate=0.5,
    )
    checks.append(_check("decide_status_blocking",
        status_blocking == "fail_schema_contract"))
    status_no_match = _decide_status(
        audit_match=False, blocking_failure_count=0,
        fd1_private_decomposition_parsed=True,
        file_selector_ceiling_computed=True,
        retrieval_availability_dominates=False,
        span_or_stopping_dominates=False,
        ceiling_unavailable_count=0,
        file_selector_lower_bound_rate=0.5,
    )
    checks.append(_check("decide_status_no_match",
        status_no_match == "unavailable_with_reason"))

    # --- G19: Unavailable report ---
    unavail = _build_unavailable_report(
        "fd1_artifact_missing", self_test_passed=True,
        openlocus_binary_source="self_test", network_mode="self_test",
    )
    checks.append(_check("unavail_status",
        unavail["status"] == "unavailable_with_reason"))
    checks.append(_check("unavail_scan_clean", not _scan_v1_p1(unavail)))
    for table in required_tables:
        if table == "actionability_matrix_records":
            # Matrix is always populated (static mapping).
            checks.append(_check(f"unavail_table_{table}_nonempty",
                len(unavail.get(table, [])) > 0))
        elif table in ("unavailable_ceiling_records",):
            # Unavailable ceilings always populated.
            checks.append(_check(f"unavail_table_{table}_nonempty",
                len(unavail.get(table, [])) > 0))
        elif table in ("gate_records", "private_manifest_records",
                       "failure_category_count_records",
                       "source_run_records"):
            checks.append(_check(f"unavail_table_{table}_is_list",
                isinstance(unavail.get(table), list)))
            checks.append(_check(f"unavail_table_{table}_nonempty",
                len(unavail.get(table, [])) > 0))
        else:
            checks.append(_check(f"unavail_table_{table}_empty",
                unavail.get(table) == []))
    # Unavailable report still has 72-row matrix (static mapping).
    checks.append(_check("unavail_matrix_72",
        len(unavail.get("actionability_matrix_records", [])) == 72))
    # Unavailable report still has 3 unavailable ceilings.
    checks.append(_check("unavail_unavailable_ceilings_3",
        len(unavail.get("unavailable_ceiling_records", [])) == 3))

    # --- G20: CLI surface ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for opt in ("--self-test", "--out", "--fd1-artifact",
                "--fd2a1-artifact", "--fd1-private-decomposition-jsonl",
                "--fd1-replay-artifact",
                "--enable-external-benchmark-network"):
        checks.append(_check(f"cli_has_{opt}", opt in option_strings))
    # Must NOT have --budget / --methods / --openlocus (audit reads,
    # never changes; the CI workflow regenerates the private JSONL
    # separately before invoking the audit).
    for opt in ("--budget", "--methods", "--openlocus",
                "--private-trace-dir", "--private-decomposition-dir"):
        checks.append(_check(f"cli_no_{opt}", opt not in option_strings))

    # --- G21: Go/No-Go constants ---
    checks.append(_check("go_fs_upside_min_005",
        GO_FILE_SELECTOR_UPSIDE_RATE_MIN == 0.05))
    checks.append(_check("no_go_retrieval_rate_050",
        NO_GO_RETRIEVAL_AVAILABILITY_RATE == 0.50))
    checks.append(_check("no_go_span_stopping_rate_050",
        SPAN_OR_STOPPING_DOMINANCE_RATE == 0.50))

    # --- G22: Source binding context ---
    checks.append(_check("fd1_source_ci_run_id",
        FD1_SOURCE_CI_RUN_ID == "28011901294"))
    checks.append(_check("fd1_source_local_checkpoint",
        FD1_SOURCE_LOCAL_CHECKPOINT == "29c5a1a"))
    checks.append(_check("fd1_source_status",
        FD1_SOURCE_STATUS == "bea_fd1_decomposition_pass"))
    checks.append(_check("fd1_source_schema_version",
        FD1_SOURCE_SCHEMA_VERSION == "bea_fd1_failure_decomposition.v1"))
    checks.append(_check("fd2a1_result_checkpoint",
        FD2A1_RESULT_CHECKPOINT == "b2aabf5"))
    checks.append(_check("fd2a1_result_status",
        FD2A1_RESULT_STATUS == "bea_fd2a1_attribution_replay_pass"))
    checks.append(_check("fd2a1_source_schema_version",
        FD2A1_SOURCE_SCHEMA_VERSION
        == "bea_fd2a1_failure_attribution_replay.v1"))

    # --- G23: FD1 inheritance invariants ---
    checks.append(_check("inherits_fd1_failure_categories",
        tuple(FAILURE_CATEGORIES) == bea_fd1.FAILURE_CATEGORIES))
    checks.append(_check("inherits_fd1_unavailable_sets",
        CANDIDATE_UNAVAILABLE_CATEGORIES
        == frozenset(bea_fd1.UNAVAILABLE_NO_SUPPORT_CATEGORIES)
        and CEILING_UNAVAILABLE_CATEGORIES
        == frozenset(bea_fd1.UNAVAILABLE_MISSING_TRACE_CATEGORIES)
        | {"redundant_same_file_candidates"}))
    checks.append(_check("inherits_fd1_budget_methods",
        FIXED_BUDGET == bea_fd1.FIXED_BUDGET == 5
        and FIXED_METHODS == ("bm25", "regex", "symbol")))
    checks.append(_check("inherits_fd1_expected_records",
        EXPECTED_RECORDS_DECOMPOSED == 239
        and EXPECTED_PRIVATE_DECOMP_ROWS == 86040))
    checks.append(_check("fd1_default_out_matches",
        str(DEFAULT_FD1_ARTIFACT) == str(bea_fd1.DEFAULT_OUT)))

    # --- G24: Scanner composes FD1 scanner ---
    # BEA-v1-P1 forbidden extra keys must include v1-P1-specific additions
    # AND inherit FD1's forbidden keys (via bea_fd1._scan_fd1).
    checks.append(_check("v1_p1_inherits_fd1_scanner",
        "decomposition_path" in bea_fd1.FD1_FORBIDDEN_KEYS))
    checks.append(_check("v1_p1_extra_keys_has_private_trace_dir",
        "private_trace_dir" in V1_P1_FORBIDDEN_EXTRA_KEYS))
    checks.append(_check("v1_p1_extra_keys_has_per_record_matrix",
        "per_record_matrix" in V1_P1_FORBIDDEN_EXTRA_KEYS))
    checks.append(_check("v1_p1_extra_keys_has_fd2a1_path",
        "fd2a1_source_artifact_path" in V1_P1_FORBIDDEN_EXTRA_KEYS))
    checks.append(_check("v1_p1_extra_keys_has_is_v04_repair",
        "is_v04_repair" in V1_P1_FORBIDDEN_EXTRA_KEYS))

    # --- G25: Audit runner with synthetic FD1 artifact + private JSONL ---
    with tempfile.TemporaryDirectory(prefix="v1p1_st_") as sd:
        td = Path(sd)
        fd1_path = td / "fd1.json"
        fd1_path.write_text(json.dumps(fd1_art), encoding="utf-8")
        fd2a1_path = td / "fd2a1.json"
        fd2a1_path.write_text(json.dumps(_build_synthetic_fd2a1_artifact()),
                              encoding="utf-8")
        # Write synthetic private decomposition JSONL (86040 rows).
        priv_jsonl = td / "bea_fd1.decomposition.jsonl"
        _build_synthetic_private_decomposition_jsonl(priv_jsonl)
        # Write synthetic FD1 replay report (validated; manifest_hash
        # matches the synthetic FD1 artifact's "a"*64).
        replay_path = td / "fd1_replay_report.json"
        _build_synthetic_fd1_replay_artifact(replay_path)
        audit_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("run_audit_status_pass",
            audit_report["status"] == "bea_v1_p1_actionability_audit_pass"))
        checks.append(_check("run_audit_audit_match",
            audit_report["source_run_records"][0]["replay_protocol_match"]
            is True))
        checks.append(_check("run_audit_records_decomposed_239",
            audit_report["records_decomposed"] == 239))
        checks.append(_check("run_audit_manifest_count_86040",
            audit_report["private_manifest_record_count"] == 86040))
        checks.append(_check("run_audit_matrix_72",
            len(audit_report["actionability_matrix_records"]) == 72))
        checks.append(_check("run_audit_private_parsed",
            audit_report.get("fd1_private_decomposition_parsed") is True))
        checks.append(_check("run_audit_lower_bound_computed",
            audit_report.get(
                "fd1_private_decomposition_lower_bound_computed") is True))
        checks.append(_check("run_audit_replay_supplied",
            audit_report.get(
                "fd1_private_decomposition_replay_supplied") is True))
        checks.append(_check("run_audit_replay_validated",
            audit_report.get(
                "fd1_private_decomposition_replay_validated") is True))
        checks.append(_check("run_audit_replay_executed_by_workflow",
            audit_report.get(
                "fd1_private_decomposition_replay_executed_by_workflow")
            is True))
        checks.append(_check("run_audit_srr_replay_validated",
            audit_report["source_run_records"][0][
                "replay_artifact_validated"] is True))
        checks.append(_check("run_audit_srr_manifest_hash_match",
            audit_report["source_run_records"][0][
                "replay_artifact_manifest_hash_match"] is True))
        checks.append(_check("run_audit_unavailable_ceilings_3",
            len(audit_report["unavailable_ceiling_records"]) == 3))
        checks.append(_check("run_audit_self_scan_clean",
            not _scan_v1_p1(audit_report)))

        # --- G25b: Audit runner with NO private JSONL → no_go_ceiling_unavailable
        # and stop_go needs_fd1_private_replay_before_v1_a (NOT pass).
        no_priv_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=None,
        )
        checks.append(_check("no_priv_status_no_go_ceiling_unavailable",
            no_priv_report["status"] == "no_go_ceiling_unavailable"))
        checks.append(_check("no_priv_stop_go_needs_replay",
            no_priv_report["stop_go_records"][0]["stop_go_decision"]
            == "needs_fd1_private_replay_before_v1_a"))
        checks.append(_check("no_priv_private_parsed_false",
            no_priv_report.get("fd1_private_decomposition_parsed")
            is False))
        checks.append(_check("no_priv_oracle_ceilings_empty",
            no_priv_report.get("oracle_ceiling_records") == []))
        checks.append(_check("no_priv_unavailable_ceilings_4",
            len(no_priv_report.get("unavailable_ceiling_records", []))
            == 4))
        checks.append(_check("no_priv_self_scan_clean",
            not _scan_v1_p1(no_priv_report)))

        # --- G25c: Audit runner with private JSONL pointing to a
        # missing file → no_go_ceiling_unavailable (fail-closed).
        missing_priv_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=td / "missing_private.jsonl",
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("missing_priv_status_no_go",
            missing_priv_report["status"] == "no_go_ceiling_unavailable"))
        checks.append(_check("missing_priv_failure_category",
            any(r["failure_category"]
                == "fd1_private_decomposition_missing"
                and r["count"] == 1
                for r in missing_priv_report[
                    "failure_category_count_records"])))

        # --- G25d: Audit runner with private JSONL with bad row count
        # (10 instead of 86040) → no_go_ceiling_unavailable.
        bad_priv = td / "bad_private.jsonl"
        with bad_priv.open("w", encoding="utf-8") as fh:
            for i in range(10):
                fh.write(json.dumps({
                    "phase_run_id": "x", "source_phase": "BEA-4",
                    "benchmark": "contextbench",
                    "private_record_id": f"r{i}",
                    "policy_arm": "bea_v0_3_anchor_span_latency",
                    "category": "gold_file_absent",
                    "baseline_arm": "bea_v0",
                    "treatment_arm": "bea_v0_3_anchor_span_latency",
                    "metric": "file_recall@10",
                    "treatment_value": 0.0, "baseline_value": 0.0,
                    "loss": 0.0, "delta": 0.0,
                    "category_availability": "available",
                    "latency_ms": 0, "cost_usd": 0.0,
                    "tokens": 0, "provider_calls": 0,
                }) + "\n")
        bad_priv_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=bad_priv,
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("bad_priv_status_no_go",
            bad_priv_report["status"] == "no_go_ceiling_unavailable"))
        checks.append(_check("bad_priv_count_mismatch",
            any(r["failure_category"]
                == "fd1_private_decomposition_count_mismatch"
                and r["count"] == 1
                for r in bad_priv_report[
                    "failure_category_count_records"])))

        # --- G25e: Audit runner with private JSONL where ALL
        # gold_file_absent records are unrecoverable (lower bound = 0)
        # → retrieval availability dominates (50/50 = 1.0 > 0.50),
        # so status is no_go_retrieval_availability_limit (the gold
        # file was in the pool for 0 of 50 denominator records →
        # retrieval layer is the bottleneck, not the file selector).
        zero_lb_priv = td / "zero_lb_private.jsonl"
        _build_synthetic_private_decomposition_jsonl(
            zero_lb_priv, gold_file_absent_count=50,
            recoverable_lower_bound=0,
        )
        zero_lb_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=zero_lb_priv,
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("zero_lb_status_no_go_retrieval",
            zero_lb_report["status"]
            == "no_go_retrieval_availability_limit"))
        checks.append(_check("zero_lb_stop_go_no_go_retrieval",
            zero_lb_report["stop_go_records"][0]["stop_go_decision"]
            == "no_go_retrieval_availability_limit"))

        # --- G25f: Audit runner with private JSONL where lower bound
        # is positive but below the materiality threshold (lower_bound
        # = 5 / 239 = 0.021 < 0.05) and retrieval_availability does
        # NOT dominate (5/10 = 0.5, not > 0.50) →
        # no_go_no_file_selector_ceiling.
        low_lb_priv = td / "low_lb_private.jsonl"
        _build_synthetic_private_decomposition_jsonl(
            low_lb_priv, gold_file_absent_count=10,
            recoverable_lower_bound=5,
        )
        low_lb_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=low_lb_priv,
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("low_lb_status_no_go_no_fs",
            low_lb_report["status"] == "no_go_no_file_selector_ceiling"))
        checks.append(_check("low_lb_stop_go_no_go_no_fs",
            low_lb_report["stop_go_records"][0]["stop_go_decision"]
            == "no_go_no_file_selector_ceiling"))

        # --- G25g: Audit runner with private JSONL supplied but NO
        # replay artifact → no_go_ceiling_unavailable (fail-closed;
        # @oracle second No-Go). The private JSONL must not be trusted
        # without a validated replay artifact.
        no_rav_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=None,
        )
        checks.append(_check("no_rav_status_no_go",
            no_rav_report["status"] == "no_go_ceiling_unavailable"))
        checks.append(_check("no_rav_private_parsed_false",
            no_rav_report.get("fd1_private_decomposition_parsed")
            is False))
        checks.append(_check("no_rav_replay_supplied_false",
            no_rav_report.get(
                "fd1_private_decomposition_replay_supplied") is False))
        checks.append(_check("no_rav_replay_validated_false",
            no_rav_report.get(
                "fd1_private_decomposition_replay_validated") is False))
        checks.append(_check("no_rav_stop_go_needs_replay",
            no_rav_report["stop_go_records"][0]["stop_go_decision"]
            == "needs_fd1_private_replay_before_v1_a"))
        checks.append(_check("no_rav_self_scan_clean",
            not _scan_v1_p1(no_rav_report)))

        # --- G25h: Audit runner with private JSONL + missing replay
        # artifact file → no_go_ceiling_unavailable with the
        # fd1_replay_artifact_missing failure category.
        missing_rav_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=td / "missing_replay.json",
        )
        checks.append(_check("missing_rav_status_no_go",
            missing_rav_report["status"] == "no_go_ceiling_unavailable"))
        checks.append(_check("missing_rav_failure_category",
            any(r["failure_category"]
                == "fd1_replay_artifact_missing"
                and r["count"] == 1
                for r in missing_rav_report[
                    "failure_category_count_records"])))

        # --- G25i: Audit runner with private JSONL + replay artifact
        # with mismatched manifest hash → no_go_ceiling_unavailable
        # with fd1_replay_artifact_manifest_hash_mismatch.
        bad_hash_replay = td / "bad_hash_replay.json"
        _build_synthetic_fd1_replay_artifact(
            bad_hash_replay, manifest_hash="b" * 64)  # wrong hash
        bad_hash_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=bad_hash_replay,
        )
        checks.append(_check("bad_hash_status_no_go",
            bad_hash_report["status"] == "no_go_ceiling_unavailable"))
        checks.append(_check("bad_hash_failure_category",
            any(r["failure_category"]
                == "fd1_replay_artifact_manifest_hash_mismatch"
                and r["count"] == 1
                for r in bad_hash_report[
                    "failure_category_count_records"])))

        # --- G25j: Audit runner with private JSONL + replay artifact
        # with wrong status → no_go_ceiling_unavailable with
        # fd1_replay_artifact_status_mismatch.
        bad_status_replay = td / "bad_status_replay.json"
        _build_synthetic_fd1_replay_artifact(
            bad_status_replay, status="partial")
        bad_status_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path, fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=bad_status_replay,
        )
        checks.append(_check("bad_status_status_no_go",
            bad_status_report["status"] == "no_go_ceiling_unavailable"))
        checks.append(_check("bad_status_failure_category",
            any(r["failure_category"]
                == "fd1_replay_artifact_status_mismatch"
                and r["count"] == 1
                for r in bad_status_report[
                    "failure_category_count_records"])))

        # --- G26: Audit runner with missing FD1 artifact ---
        missing_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=td / "missing.json",
            fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("missing_fd1_status_unavailable",
            missing_report["status"] == "unavailable_with_reason"))
        checks.append(_check("missing_fd1_failure_reason",
            missing_report["failure_reason_category"] == "artifact_missing"))
        checks.append(_check("missing_fd1_failure_category_count",
            missing_report["failure_category_count_records"][
                next(i for i, r in enumerate(
                    missing_report["failure_category_count_records"])
                    if r["failure_category"] == "fd1_artifact_missing")
            ]["count"] == 1))

        # --- G27: Audit runner with mismatched FD1 counts ---
        bad_fd1 = dict(fd1_art)
        bad_fd1["records_decomposed"] = 100  # not 239
        bad_fd1["private_decomposition_manifest"] = dict(
            bad_fd1["private_decomposition_manifest"])
        bad_fd1["private_decomposition_manifest"]["record_count"] = 100
        bad_fd1_path = td / "bad_fd1.json"
        bad_fd1_path.write_text(json.dumps(bad_fd1), encoding="utf-8")
        bad_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=bad_fd1_path,
            fd2a1_artifact_path=fd2a1_path,
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("mismatch_fd1_status_unavailable",
            bad_report["status"] == "unavailable_with_reason"))
        checks.append(_check("mismatch_fd1_audit_match_false",
            bad_report["source_run_records"][0]["replay_protocol_match"]
            is False))
        checks.append(_check("mismatch_fd1_records_decomposed_mismatch",
            bad_report["failure_category_count_records"][
                next(i for i, r in enumerate(
                    bad_report["failure_category_count_records"])
                    if r["failure_category"] == "fd1_records_decomposed_mismatch")
            ]["count"] == 1))
        checks.append(_check("mismatch_fd1_manifest_mismatch",
            bad_report["failure_category_count_records"][
                next(i for i, r in enumerate(
                    bad_report["failure_category_count_records"])
                    if r["failure_category"] == "fd1_private_manifest_mismatch")
            ]["count"] == 1))

        # --- G28: Audit runner with missing FD2-A1 artifact ---
        # FD2-A1 is binding context; missing it does not block the
        # audit (audit_match is driven by FD1 only). With the private
        # JSONL supplied, the audit can still compute the lower bound
        # and pass.
        no_fd2a1_report = _run_audit(
            self_test_passed=True, self_test_checks_total=0,
            openlocus_binary_source="self_test", network_mode="self_test",
            fd1_artifact_path=fd1_path,
            fd2a1_artifact_path=td / "missing_fd2a1.json",
            fd1_private_decomposition_jsonl=priv_jsonl,
            fd1_replay_artifact=replay_path,
        )
        checks.append(_check("missing_fd2a1_status_pass",
            no_fd2a1_report["status"]
            == "bea_v1_p1_actionability_audit_pass"))
        checks.append(_check("missing_fd2a1_failure_category",
            any(r["failure_category"] == "fd2a1_artifact_missing"
                and r["count"] == 1
                for r in no_fd2a1_report["failure_category_count_records"])))

    # --- G29: License fields ---
    for field, expected in LICENSE_FIELDS.items():
        checks.append(_check(f"license_{field}",
            report.get(field) == expected))

    # --- G30: Framing is_actionability_audit_only ---
    checks.append(_check("framing_is_actionability_audit_only",
        report.get("framing", {}).get("is_actionability_audit_only") is True))
    checks.append(_check("framing_not_v04_repair",
        report.get("framing", {}).get("is_v04_repair") is False))
    checks.append(_check("framing_not_fd2_b",
        report.get("framing", {}).get("is_fd2_b") is False))
    checks.append(_check("framing_not_failure_attribution_only",
        report.get("framing", {}).get("is_failure_attribution_only") is False))

    # --- G31: Aggregate runtime present ---
    checks.append(_check("has_runtime",
        "aggregate_runtime_seconds" in report))
    checks.append(_check("unavail_no_runtime",
        "aggregate_runtime_seconds" not in unavail))

    # --- G32: failure_category_count_records covers all audit categories ---
    fccr_cats = {r.get("failure_category")
                 for r in report.get("failure_category_count_records", [])}
    for cat in FAILURE_CATEGORIES_AUDIT:
        checks.append(_check(f"fccr_has_{cat}", cat in fccr_cats))

    # --- G33: Provider calls zero (binding) ---
    checks.append(_check("no_provider_calls_field",
        report.get("provider_calls_made") is False))
    checks.append(_check("unavail_no_provider_calls",
        unavail.get("provider_calls_made") is False))

    # --- G34: Candidate availability records ---
    car_rows = report.get("candidate_availability_records", [])
    checks.append(_check("car_records_present", len(car_rows) >= 1))
    # Only ceiling-relevant categories published (not unavailable categories).
    car_cats = {r["failure_category"] for r in car_rows}
    for cat in CANDIDATE_UNAVAILABLE_CATEGORIES:
        checks.append(_check(f"car_excludes_{cat}", cat not in car_cats))
    for cat in CEILING_UNAVAILABLE_CATEGORIES:
        checks.append(_check(f"car_excludes_{cat}", cat not in car_cats))

    # --- G35: Redundancy tradeoff records (unavailable) ---
    rtr_rows = report.get("redundancy_tradeoff_records", [])
    checks.append(_check("rtr_records_present", len(rtr_rows) >= 1))
    for r in rtr_rows:
        checks.append(_check("rtr_class_unavailable",
            r["tradeoff_class"] == "unavailable"))

    # --- G36: BEA-v1-P1 NOT a selector / acquisition phase ---
    # No --budget / --methods / --openlocus CLI inputs.
    # No v1_a_selector_executed flag set true.
    checks.append(_check("v1_a_selector_not_executed",
        report.get("v1_a_selector_executed") is False))
    checks.append(_check("v1_a_selector_not_promoted",
        report.get("v1_a_coverage_preserving_selector_promoted") is False))

    # --- G37: source_run_records fields ---
    srr = report.get("source_run_records", [{}])[0] if report.get(
        "source_run_records") else {}
    for field in ("source_phase", "source_ci_run_id", "source_checkpoint",
                  "source_local_checkpoint", "source_status",
                  "source_artifact_status", "source_sampling_protocol",
                  "expected_records_decomposed",
                  "audited_records_decomposed",
                  "expected_private_manifest_record_count",
                  "audited_private_manifest_record_count",
                  "fd1_source_schema_version",
                  "fd1_source_artifact_hash",
                  "fd2a1_source_schema_version",
                  "fd2a1_source_artifact_hash",
                  "fd2a1_result_checkpoint",
                  "fd2a1_result_status",
                  "replay_protocol_match", "replay_mismatch_reason"):
        checks.append(_check(f"srr_has_{field}", field in srr))
    checks.append(_check("srr_no_artifact_path",
        "fd1_source_artifact_path" not in srr
        and "fd2a1_source_artifact_path" not in srr))

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
        description="BEA-v1-P1 FD1 Actionability and Oracle Ceiling Audit"
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1_ARTIFACT)
    ap.add_argument("--fd2a1-artifact", type=Path,
                    default=DEFAULT_FD2A1_ARTIFACT)
    ap.add_argument(
        "--fd1-private-decomposition-jsonl", type=Path, default=None,
        help="Path to a regenerated FD1 private decomposition JSONL "
        "(bea_fd1.decomposition.jsonl) produced by "
        "bea_fd1_failure_decomposition --private-decomposition-dir. "
        "Required to compute the file-selector oracle ceiling lower "
        "bound and authorize v1-A. Without it the audit honestly "
        "No-Gos to no_go_ceiling_unavailable.",
    )
    ap.add_argument(
        "--fd1-replay-artifact", type=Path, default=None,
        help="Path to the regenerated FD1 replay report "
        "(fd1_replay_report.json) produced by "
        "bea_fd1_failure_decomposition --out. Required when "
        "--fd1-private-decomposition-jsonl is supplied: the audit "
        "validates the replay report (schema/status/counts/manifest-hash/"
        "forbidden_scan) BEFORE trusting the private JSONL. If the "
        "replay artifact is missing/invalid/mismatched, the audit No-Gos "
        "to no_go_ceiling_unavailable (NOT a fake pass). No private "
        "JSONL path or content hash is serialized.",
    )
    ap.add_argument("--enable-external-benchmark-network",
                    action="store_true")
    # NOTE: NO --budget / --methods / --openlocus (audit reads committed
    # artifacts + an externally-regenerated private JSONL and replay
    # report; the audit evaluator itself never replays, never selects,
    # never calls a provider).
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
    fd2a1_artifact_path = (args.fd2a1_artifact
                           if args.fd2a1_artifact is not None
                           else DEFAULT_FD2A1_ARTIFACT)
    fd1_private_jsonl = args.fd1_private_decomposition_jsonl
    fd1_replay_artifact_path = args.fd1_replay_artifact
    enable_network = bool(args.enable_external_benchmark_network)

    checks, self_test_passed = run_self_test_checks()
    self_test_checks_total = len(checks)
    if not self_test_passed:
        print("error: self-test failed; refusing to write artifact",
              file=sys.stderr)
        sys.exit(1)

    # The BEA-v1-P1 audit EVALUATOR reads the committed FD1 artifact
    # (in-repo; no network needed). The --enable-external-benchmark-network
    # flag is accepted for CI-workflow symmetry but does not change
    # behavior: the audit evaluator itself never makes network calls,
    # never replays, never executes a selector, and never calls a
    # provider. The CI workflow regenerates the FD1 private decomposition
    # JSONL AND the FD1 replay report separately before invoking the
    # audit, and passes both via --fd1-private-decomposition-jsonl and
    # --fd1-replay-artifact.
    del enable_network  # accepted for CI symmetry; no behavioral effect

    openlocus_binary_source = "not_required"
    network_mode = "no_network_audit_only"

    try:
        report = _run_audit(
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            fd1_artifact_path=fd1_artifact_path,
            fd2a1_artifact_path=fd2a1_artifact_path,
            fd1_private_decomposition_jsonl=fd1_private_jsonl,
            fd1_replay_artifact=fd1_replay_artifact_path,
        )
    except Exception:
        fcc = {c: 0 for c in FAILURE_CATEGORIES_AUDIT}
        fcc["unexpected_exception"] = 1
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=self_test_passed,
            self_test_checks_total=self_test_checks_total,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            failure_category_counts=fcc,
        )

    if report.get("provider_calls_made") is not False:
        report["status"] = "fail_schema_contract"

    _enforce_v1_p1_no_forbidden(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, report)
    sgr = report.get("stop_go_records", [{}])[0] if report.get(
        "stop_go_records") else {}
    print(f"wrote artifact (forbidden_scan="
          f"{report['forbidden_scan']['status']}, "
          f"status={report['status']}, phase={report['phase']}, "
          f"records_decomposed={report.get('records_decomposed', 0)}, "
          f"private_manifest_record_count="
          f"{report.get('private_manifest_record_count', 0)}, "
          f"stop_go_decision={sgr.get('stop_go_decision', '')})")


if __name__ == "__main__":
    main()
