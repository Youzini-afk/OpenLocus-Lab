#!/usr/bin/env python3
"""Phase 9K outcome-acquisition / scoring / adjudication protocol freeze.

This is a docs/report/validator-only protocol freeze.  It freezes the future
protocol for outcome acquisition, scoring, and adjudication that may follow the
Phase 9J annotation-input rows.  It does NOT fetch, clone, read, or materialize
any repository or source, does NOT read ignored ``runs/`` or private candidate
pools/registries/manifests or the Phase 9H private materialized inventory or
the Phase 9J private annotation-input rows/manifests, does NOT acquire
outcomes, does NOT score, does NOT adjudicate, does NOT generate gold labels,
benchmark labels, evidence_success, result labels, annotation-truth, or
scoring/evaluation rows, and makes no method/product/performance/model/provider/
training/runtime/default/scoring/outcome/evidence-success/annotation-truth
claim.

It records that Phase 9J annotation-input rows are routing/precondition
metadata only, NOT benchmark truth.  It records that Phase 9H is source-
materialization readiness only and is NOT proof that any annotation, outcome,
evidence_success, scoring, or evaluation works.  Phase 9K does not read any
private inventory or annotation-input rows.  Future outcome acquisition,
scoring, and adjudication each require a separate frozen boundary.

The Phase 9H, Phase 9I, and Phase 9J public gate reference values (remote
commits and CI runs) are the only public gate references published by Phase 9K.
Phase 9G and Phase 9F are carried as inherited provenance only and their exact
remote commit/CI run values are intentionally NOT published in the Phase 9K
report/docs (bucketed inherited provenance) to keep tighter privacy; only the
Phase 9H, Phase 9I, and Phase 9J full commit SHAs and CI runs are public gate
references.  Local same-tree git commits are not read or compared; the supplied
confirmation values are matched against the frozen public gate constants only.

Truth-boundary is explicit: annotation-input metadata remains routing/
precondition metadata; eligibility != correctness; expected evidence form !=
gold evidence; outcome precondition != outcome; adjudication rule !=
adjudicated truth.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

# Compact Phase 9K slug: the long descriptive status string was shortened to
# ``phase9k_outcome_scoring_protocol_freeze_no_claim`` so that the absolute
# artifact report path stays comfortably under the Windows MAX_PATH (260)
# limit.  Boundary wording in the report body/docs is NOT weakened — only the
# path-dependent slug is shortened.
PHASE = "phase9k_outcome_scoring_protocol_freeze_no_claim"
STATUS = PHASE
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# Phase 9H public gate reference values (oracle-provided).  Local same-tree
# git commits are not read or compared; the supplied confirmation values are
# matched against the frozen public gate constants only.
PHASE9H_STATUS = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_readiness_no_scoring_no_claim"
)
PHASE9H_COMMIT = "d997caab5487e66c544f657645d70c97f3b780e2"
PHASE9H_CI_RUN = "28976655118"

# Phase 9I public gate reference values (oracle-provided).
PHASE9I_STATUS = (
    "phase9i_materialized_inventory_to_task_annotation_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9I_COMMIT = "fe9eabba744ff00526fadd7184801c3721677fba"
PHASE9I_CI_RUN = "28979060368"

# Phase 9J public gate reference values (oracle-provided).
PHASE9J_STATUS = (
    "phase9j_annotation_input_rows_generated_no_scoring_no_claim"
)
PHASE9J_COMMIT = "25140f4017acf139012fe917fd920ddba9839cc3"
PHASE9J_CI_RUN = "28980705743"

# Phase 9G inherited provenance (carried forward).  The exact Phase 9G remote
# commit/CI run values are intentionally NOT published in the Phase 9K
# report/docs; Phase 9G is carried as bucketed inherited provenance only
# (tighter privacy).  Only the Phase 9H, Phase 9I, and Phase 9J full commit
# SHAs / CI runs are public gate references.
PHASE9G_STATUS = (
    "phase9g_candidate_source_pool_network_fetch_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9G_REMOTE_PROVENANCE_BUCKETED = True

# Phase 9F status (inherited provenance only, carried forward from Phase 9G).
PHASE9F_STATUS = "phase9f_public_source_fetch_clone_materialization_repair_no_claim"

# Inherited aggregate caps/buckets from Phase 9H (frozen, aggregate-only).
TARGET_INVENTORY_MIN = 48
TARGET_INVENTORY_MAX = 72
HARD_INVENTORY_CAP = 96
PER_SOURCE_CAP = 8
MIN_DISTINCT_SOURCES = 8

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "task_annotation_generated",
    "private_phase9h_materialized_inventory_read",
    "private_phase9j_annotation_input_rows_read",
    "private_candidate_pool_read",
    "private_registry_read",
    "ignored_runs_read",
    "annotations_generated",
    "outcomes_acquired",
    "gold_rows_generated",
    "evidence_success_evaluated",
    "scoring_executed",
    "adjudication_executed",
    "evaluation_rows_generated",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
    "network_fetch_or_clone_or_source_refresh_executed",
)

CLAIM_BOUNDARY_FALSE_KEYS = (
    "method_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "model_claim",
    "runtime_claim",
    "default_claim",
    "scoring_claim",
    "outcome_claim",
    "evidence_success_claim",
    "annotation_truth_claim",
)

PRIVACY_FALSE_KEYS = (
    "repo_names_public",
    "source_names_public",
    "urls_public",
    "owners_public",
    "commits_public",
    "hashes_public",
    "paths_public",
    "snippets_public",
    "task_ids_public",
    "row_ids_public",
    "manifest_locations_public",
    "run_locations_public",
    "per_source_public_facts",
    "per_task_public_facts",
    "singleton_buckets_public",
)

# Forbidden public field words; only apply to non-boolean values at
# non-allowed-schema paths so boolean boundary attestation keys such as
# ``scoring_executed`` and protocol-freeze section names such as
# ``future_scoring_protocol`` (which are at allowed-schema paths) are not
# false-flagged.
FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

# Frozen outcome-acquisition packet required fields (routing/precondition
# metadata only, NOT benchmark truth).
OUTCOME_PACKET_REQUIRED_FIELDS = (
    "task_eligibility_routing_precondition_only",
    "evidence_localization_requirement",
    "expected_evidence_form",
    "outcome_acquisition_precondition",
    "annotation_input_metadata_reference",
)

# Allowed public aggregate buckets for outcome-acquisition reporting.
ALLOWED_PUBLIC_AGGREGATE_BUCKETS = (
    "bucket_outcome_acquired_or_unavailable",
    "bucket_included_or_excluded",
    "bucket_adjudication_agreement_or_disagreement",
    "bucket_aggregate_pass_or_fail",
)

# Predeclared failure buckets for scoring protocol.
PREDECLARED_FAILURE_BUCKETS = (
    "bucket_outcome_unavailable_failure",
    "bucket_outcome_invalid_failure",
    "bucket_inclusion_failure",
    "bucket_metric_denominator_failure",
)

# Disagreement categories for adjudication protocol.
DISAGREEMENT_CATEGORIES = (
    "full_agreement",
    "partial_disagreement",
    "full_disagreement",
    "tie_requires_adjudication",
)

# Frozen future outcome-acquisition rules.
FUTURE_OUTCOME_ACQUISITION_RULES = (
    "outcome_acquisition_packet_schema_frozen_with_required_fields_only",
    "private_only_fields_stay_private_under_ignored_runs_only",
    "allowed_public_aggregate_buckets_only_no_exact_counts",
    "missing_outcome_handled_as_unavailable_not_as_failure_or_success",
    "invalid_outcome_rejected_before_scoring_with_replacement_only",
    "unavailable_outcome_recorded_in_aggregate_unavailability_bucket_only",
    "no_outcome_acquisition_execution_in_phase9k",
    "no_outcomes_or_gold_or_scoring_or_evidence_success_in_phase9k",
    "future_outcome_acquisition_requires_separate_phase9l_boundary",
    "aggregate_public_report_only_no_private_outcome_details",
    "annotation_input_metadata_remains_routing_precondition_not_benchmark_truth",
)

# Frozen future scoring rules.
FUTURE_SCORING_RULES = (
    "scoring_metrics_and_denominators_frozen_before_outcome_visibility",
    "inclusion_exclusion_rules_frozen_before_outcome_visibility",
    "failure_buckets_predeclared_aggregate_only",
    "no_threshold_or_metric_tuning_after_outcome_visibility",
    "no_posthoc_subgroup_mining_except_predeclared_aggregate_buckets",
    "no_scoring_execution_in_phase9k",
    "future_scoring_requires_separate_frozen_boundary_after_outcome_acquisition",
    "aggregate_public_report_only_no_private_scoring_details",
)

# Frozen future adjudication rules.
FUTURE_ADJUDICATION_RULES = (
    "adjudication_independence_required_raters_blind_to_each_other",
    "minimum_rater_count_at_least_three_if_human_annotations_used",
    "disagreement_categories_predeclared_before_adjudication",
    "tie_break_flow_predeclared_before_adjudication",
    "independent_outcomes_acquired_first_adjudication_second",
    "adjudication_rule_is_not_adjudicated_truth",
    "no_adjudication_execution_in_phase9k",
    "future_adjudication_requires_separate_frozen_boundary_after_scoring",
    "aggregate_public_report_only_no_private_adjudication_details",
)

# Future Phase 9L gate conditions (frozen).
FUTURE_PHASE9L_GATE_RULES = (
    "phase9k_commit_and_ci_green_required_before_phase9l",
    "phase9h_phase9i_phase9j_commit_and_ci_confirmation_required",
    "phase9k_protocol_freeze_confirmation_required",
    "read_phase9j_private_annotation_input_rows_confirmation_required",
    "ignored_runs_workspace_confirmation_required",
    "private_output_only_confirmation_required",
    "no_scoring_or_evidence_success_confirmation_required_until_separate_boundary",
    "no_provider_llm_model_default_runtime_change_confirmation_required",
    "aggregate_public_report_only_confirmation_required",
    "phase9l_may_read_phase9j_private_annotation_input_rows_only_after_phase9k_commit_and_ci_green",
    "consider_phase9l_outcome_acquisition_only_and_later_phase9m_scoring_adjudication_if_complexity_warrants",
    "no_user_approval_wording_future_gate_requires_phase9k_commit_ci_green_and_explicit_confirmations_boundary",
)

# Truth-boundary attestation keys that must always be True in the public report.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "annotation_input_metadata_is_routing_precondition_only",
    "eligibility_is_not_correctness",
    "expected_evidence_form_is_not_gold_evidence",
    "outcome_precondition_is_not_outcome",
    "adjudication_rule_is_not_adjudicated_truth",
)

# Claim-making wording that must never appear as an exposed value.  Targeted
# so legitimate boundary attestation keys such as ``*_validated`` booleans are
# not false-flagged.
CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"materialization\s+(?:works|succeeded|proven|established)"
    r"|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)"
    r"|clone\s+(?:works|succeeded|proven|established)"
    r"|annotation\s+(?:works|succeeded|proven|established)"
    r"|evidence_success\s+(?:achieved|proven|established|confirmed)"
    r"|method\s+(?:proven|established|works|winner|effectiveness)"
    r"|product\s+readiness"
    r"|scoring\s+success"
    r"|outcome\s+success"
    r"|evaluation\s+works"
    r"|task\s+annotation\s+readiness"
    r"|lift\s+(?:proven|established|achieved)"
    r")\b",
    re.IGNORECASE,
)

# User-approval wording that must never appear in next_action / conservative
# recommendation / rule strings.  The future gate must be phrased as requiring
# Phase 9K commit+CI green and explicit confirmations/boundary, NOT as
# requiring the user to separately approve low-resource continuation.
# Underscore-separated forms (e.g. ``no_user_approval``) use word characters
# between tokens and so do NOT match this regex (which requires whitespace
# ``\s+`` between ``user`` and the approval verb).
USER_APPROVAL_WORDING_RE = re.compile(
    r"\b(?:user\s+(?:must|should|needs?\s+to)\s+(?:approve|authorize|confirm)"
    r"|awaiting\s+user\s+(?:approval|authorization|confirmation)"
    r"|requires?\s+user\s+(?:approval|authorization)"
    r"|low.resource\s+continuation\s+(?:approval|authorization))\b",
    re.IGNORECASE,
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
# Long decimal (8+ digits) CI/run-shaped public value detector.  Catches CI
# run IDs and other long numeric identifiers that should never appear in
# public output except on the exact whitelisted CI run gate paths.
LONG_DECIMAL_VALUE_RE = re.compile(r"\b\d{8,}\b")
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:count_1|bucket_one|bucket_1|bucket_up_to_1|bucket_at_most_1|n_1|singleton)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
# Private-shaped KEY detection.  Matches any key that contains a private
# token (substring, case-insensitive).  Known-good boundary-attestation keys
# that legitimately contain a private token in their name (e.g.
# ``per_source_public_facts``, ``commits_public``,
# ``manifest_locations_public``) are exempted via the allowed-schema path
# check in ``_scan_public``; gate-reference commit/CI keys are exempted via
# ``GATE_REF_EXEMPT_PATHS``.
PRIVATE_KEY_RE = re.compile(
    r"(?:repo|repo_name|repo_url|owner|source_url|url"
    r"|candidate_identity|commit|commit_sha|ci_run|sha|hash"
    r"|path|range|snippet|task_id|row_id"
    r"|manifest|run_dir|per_source|per_task)",
    re.IGNORECASE,
)

# Private-shaped TOKEN scan for list string VALUES.  Unlike PRIVATE_KEY_RE
# (which scans object keys), this scans list string values that have no
# object key context.  Closed protocol lists already reject extra members
# via set-equality in ``validate_report``; this is a defense-in-depth scan
# that catches private-shaped tokens in ANY list string value: task_id,
# bucket_task_id, bucket_private_row_id_failure, private_run_dir,
# source_path, etc.  Tokens that also appear inside legitimate frozen
# protocol strings (e.g. ``commit`` in ``phase9k_commit_and_ci_green_...``)
# are intentionally excluded here to avoid false-flagging; those are
# validated by the set-equality checks on the closed protocol lists.
LIST_VALUE_PRIVATE_TOKEN_RE = re.compile(
    r"(?:task_id|row_id|run_dir|source_path"
    r"|manifest_path|candidate_id|commit_sha)",
    re.IGNORECASE,
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants (full commit SHA / CI run ID).  This is an exact path
# whitelist, NOT a suffix match, so arbitrary keys ending in ``_commit`` or
# ``_ci_run`` are NOT exempt.  Only the Phase 9H, Phase 9I, and Phase 9J full
# commit SHAs and CI runs are public gate references; Phase 9G/9F exact
# commit/CI are intentionally not published (bucketed inherited provenance).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9h_gate_references.phase9h_commit",
        "$.phase9h_gate_references.phase9h_ci_run",
        "$.phase9i_gate_references.phase9i_commit",
        "$.phase9i_gate_references.phase9i_ci_run",
        "$.phase9j_gate_references.phase9j_commit",
        "$.phase9j_gate_references.phase9j_ci_run",
    }
)

# Exact public gate-reference JSON paths whose string VALUES are CI run IDs
# (long decimal integers).  Only the Phase 9H, Phase 9I, and Phase 9J CI run
# paths are exempt from the long-decimal value scan; commit SHAs are hex and
# are NOT exempt here (they are validated by exact-equality gate checks
# instead).
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9h_gate_references.phase9h_ci_run",
        "$.phase9i_gate_references.phase9i_ci_run",
        "$.phase9j_gate_references.phase9j_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS = 0
PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0


def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


# ---------------------------------------------------------------------------
# Strict allowed-key schema for the public report
# ---------------------------------------------------------------------------

ALLOWED_REPORT_KEYS: dict[str, Any] = {
    "schema_version": None,
    "phase": None,
    "status": None,
    "phase9f_inherited_provenance": {
        "phase9f_status": None,
        "phase9f_repair_no_claim": None,
        "phase9f_zero_buckets": None,
        "phase9f_public_fetch_or_clone_executed": None,
        "phase9f_carried_as_inherited_provenance_only": None,
    },
    "phase9g_inherited_provenance": {
        "phase9g_ci_success": None,
        "phase9g_status": None,
        "phase9g_protocol_freeze": None,
        "phase9g_remote_provenance_bucketed": None,
        "phase9g_carried_as_inherited_provenance_only": None,
    },
    "phase9h_gate_references": {
        "phase9h_commit": None,
        "phase9h_ci_run": None,
        "phase9h_ci_success": None,
        "phase9h_status": None,
        "phase9h_source_materialization_readiness_only": None,
        "phase9h_not_proof_annotation_or_outcome_or_evidence_success_works": None,
        "phase9h_did_not_generate_annotations_or_outcomes_or_gold_rows_or_evidence_success_or_scoring_rows": None,
        "phase9h_private_materialized_inventory_under_ignored_runs_only": None,
        "phase9h_gate_required_before_phase9k": None,
    },
    "phase9i_gate_references": {
        "phase9i_commit": None,
        "phase9i_ci_run": None,
        "phase9i_ci_success": None,
        "phase9i_status": None,
        "phase9i_protocol_freeze": None,
        "phase9i_annotation_protocol_frozen": None,
        "phase9i_gate_required_before_phase9k": None,
        "phase9i_carried_as_inherited_provenance_only": None,
    },
    "phase9j_gate_references": {
        "phase9j_commit": None,
        "phase9j_ci_run": None,
        "phase9j_ci_success": None,
        "phase9j_status": None,
        "phase9j_annotation_input_rows_generated": None,
        "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": None,
        "phase9j_gate_required_before_phase9k": None,
        "phase9j_carried_as_inherited_provenance_only": None,
    },
    "phase9k_scope": {
        "docs_report_validator_only": None,
        "protocol_freeze_only": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "task_annotation_generated": None,
        "private_phase9h_materialized_inventory_read": None,
        "private_phase9j_annotation_input_rows_read": None,
        "private_candidate_pool_read": None,
        "private_registry_read": None,
        "ignored_runs_read": None,
        "annotations_generated": None,
        "outcomes_acquired": None,
        "gold_rows_generated": None,
        "evidence_success_evaluated": None,
        "scoring_executed": None,
        "adjudication_executed": None,
        "evaluation_rows_generated": None,
        "model_fitting": None,
        "provider_or_llm_calls": None,
        "runtime_default_or_product_changes": None,
        "network_fetch_or_clone_or_source_refresh_executed": None,
        "future_execution_requires_phase9k_commit_and_ci_green": None,
    },
    "future_outcome_acquisition_protocol": {
        "publication_level": None,
        "outcome_packet_schema": None,
        "outcome_packet_required_fields": None,
        "private_only_fields": None,
        "allowed_public_aggregate_buckets": None,
        "missing_invalid_unavailable_outcome_handling": None,
        "outcome_acquisition_rules": None,
        "inherited_phase9h_aggregate_caps": {
            "target_inventory_bucket": None,
            "hard_cap_bucket": None,
            "per_source_cap_bucket": None,
            "minimum_distinct_sources_bucket": None,
        },
        "future_private_input_output_locations": None,
        "future_phase9l_gate_conditions": None,
        "future_outcome_acquisition_requires_separate_phase9l_boundary": None,
        "future_outcome_acquisition_requires_explicit_phase9k_commit_and_ci_green": None,
    },
    "future_scoring_protocol": {
        "publication_level": None,
        "metrics_and_denominators": None,
        "inclusion_exclusion_rules": None,
        "failure_buckets": None,
        "no_threshold_or_metric_tuning_after_outcome_visibility": None,
        "no_posthoc_subgroup_mining_except_predeclared_aggregate_buckets": None,
        "scoring_rules": None,
        "future_scoring_requires_separate_frozen_boundary_after_outcome_acquisition": None,
    },
    "future_adjudication_protocol": {
        "publication_level": None,
        "independence_required": None,
        "minimum_rater_count_if_human_annotations_used": None,
        "disagreement_categories": None,
        "tie_break_flow": None,
        "timing_independent_outcomes_first_adjudication_second": None,
        "adjudication_rules": None,
        "future_adjudication_requires_separate_frozen_boundary_after_scoring": None,
    },
    "truth_boundary": {key: None for key in TRUTH_BOUNDARY_TRUE_KEYS},
    "no_execution_booleans": {key: None for key in NO_EXECUTION_FALSE_KEYS},
    "privacy_contract": {
        "public_output_aggregate_only": None,
        "private_future_manifests_only_under_ignored_runs": None,
        "runs_remains_ignored": None,
        **{key: None for key in PRIVACY_FALSE_KEYS},
    },
    "claim_boundary": {key: None for key in CLAIM_BOUNDARY_FALSE_KEYS},
    "validation_summary": {
        "route_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_private_candidate_pools": None,
        "validator_does_not_read_phase9h_private_materialized_inventory": None,
        "validator_does_not_read_phase9j_private_annotation_input_rows": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "public_artifact_privacy_audit_expected": None,
    },
    "conservative_recommendation": None,
}


def _allowed_leaf_paths() -> set[str]:
    """Return the set of every allowed JSON path in ``ALLOWED_REPORT_KEYS``."""
    paths: set[str] = set()

    def walk(allowed: Any, prefix: str = "$") -> None:
        if isinstance(allowed, dict):
            for key, value in allowed.items():
                child = f"$.{key}" if prefix == "$" else f"{prefix}.{key}"
                paths.add(child)
                walk(value, child)

    walk(ALLOWED_REPORT_KEYS)
    return paths


def _check_allowed_keys(value: Any, allowed: Any, path: str = "$") -> list[str]:
    """Recursively reject any field not present in ``ALLOWED_REPORT_KEYS``."""
    errors: list[str] = []
    if isinstance(allowed, dict):
        if not isinstance(value, dict):
            errors.append(f"expected object at {path}")
            return errors
        allowed_names = set(allowed.keys())
        actual_names = {str(key) for key in value.keys()}
        for extra in sorted(actual_names - allowed_names):
            if path == "$":
                errors.append(f"unexpected top-level field: {extra}")
            else:
                errors.append(f"unexpected field at {path}.{extra}")
        for key, child_value in value.items():
            name = str(key)
            if name in allowed:
                child_path = f"$.{name}" if path == "$" else f"{path}.{name}"
                errors.extend(_check_allowed_keys(child_value, allowed[name], child_path))
    return errors


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--validate-report``.

    The report path must be under the Phase 9K public artifact directory
    (``artifacts/<PHASE>/...``); ignored/private paths such as ``runs/`` and
    paths outside ``artifacts/`` are rejected before any file is read.
    """
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        return False, "unable to resolve report path"
    artifacts_root = (REPO / "artifacts").resolve()
    try:
        rel = resolved.relative_to(artifacts_root)
    except ValueError:
        return False, "report path is not under the public artifacts/ root"
    rel_posix = str(rel).replace("\\", "/")
    if rel_posix == "runs" or rel_posix.startswith("runs/"):
        return False, "report path is under ignored runs/ (private)"
    if "/runs/" in rel_posix:
        return False, "report path crosses ignored runs/ (private)"
    if not rel_posix.startswith(PHASE + "/"):
        return False, "report path is not under the Phase 9K public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report() -> dict[str, Any]:
    """Build the frozen Phase 9K public protocol report.

    This function performs no network/filesystem fetch or private reads.  It
    assembles the frozen protocol document from static constants.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9f_inherited_provenance": {
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_repair_no_claim": True,
            "phase9f_zero_buckets": True,
            "phase9f_public_fetch_or_clone_executed": False,
            "phase9f_carried_as_inherited_provenance_only": True,
        },
        "phase9g_inherited_provenance": {
            "phase9g_ci_success": True,
            "phase9g_status": PHASE9G_STATUS,
            "phase9g_protocol_freeze": True,
            "phase9g_remote_provenance_bucketed": PHASE9G_REMOTE_PROVENANCE_BUCKETED,
            "phase9g_carried_as_inherited_provenance_only": True,
        },
        "phase9h_gate_references": {
            "phase9h_commit": PHASE9H_COMMIT,
            "phase9h_ci_run": PHASE9H_CI_RUN,
            "phase9h_ci_success": True,
            "phase9h_status": PHASE9H_STATUS,
            "phase9h_source_materialization_readiness_only": True,
            "phase9h_not_proof_annotation_or_outcome_or_evidence_success_works": True,
            "phase9h_did_not_generate_annotations_or_outcomes_or_gold_rows_or_evidence_success_or_scoring_rows": True,
            "phase9h_private_materialized_inventory_under_ignored_runs_only": True,
            "phase9h_gate_required_before_phase9k": True,
        },
        "phase9i_gate_references": {
            "phase9i_commit": PHASE9I_COMMIT,
            "phase9i_ci_run": PHASE9I_CI_RUN,
            "phase9i_ci_success": True,
            "phase9i_status": PHASE9I_STATUS,
            "phase9i_protocol_freeze": True,
            "phase9i_annotation_protocol_frozen": True,
            "phase9i_gate_required_before_phase9k": True,
            "phase9i_carried_as_inherited_provenance_only": True,
        },
        "phase9j_gate_references": {
            "phase9j_commit": PHASE9J_COMMIT,
            "phase9j_ci_run": PHASE9J_CI_RUN,
            "phase9j_ci_success": True,
            "phase9j_status": PHASE9J_STATUS,
            "phase9j_annotation_input_rows_generated": True,
            "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": True,
            "phase9j_gate_required_before_phase9k": True,
            "phase9j_carried_as_inherited_provenance_only": True,
        },
        "phase9k_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "task_annotation_generated": False,
            "private_phase9h_materialized_inventory_read": False,
            "private_phase9j_annotation_input_rows_read": False,
            "private_candidate_pool_read": False,
            "private_registry_read": False,
            "ignored_runs_read": False,
            "annotations_generated": False,
            "outcomes_acquired": False,
            "gold_rows_generated": False,
            "evidence_success_evaluated": False,
            "scoring_executed": False,
            "adjudication_executed": False,
            "evaluation_rows_generated": False,
            "model_fitting": False,
            "provider_or_llm_calls": False,
            "runtime_default_or_product_changes": False,
            "network_fetch_or_clone_or_source_refresh_executed": False,
            "future_execution_requires_phase9k_commit_and_ci_green": True,
        },
        "future_outcome_acquisition_protocol": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "outcome_packet_schema": "frozen_required_fields_only",
            "outcome_packet_required_fields": list(OUTCOME_PACKET_REQUIRED_FIELDS),
            "private_only_fields": "private_fields_stay_under_ignored_runs_only",
            "allowed_public_aggregate_buckets": list(ALLOWED_PUBLIC_AGGREGATE_BUCKETS),
            "missing_invalid_unavailable_outcome_handling": "frozen_fail_closed_rules",
            "outcome_acquisition_rules": list(FUTURE_OUTCOME_ACQUISITION_RULES),
            "inherited_phase9h_aggregate_caps": {
                "target_inventory_bucket": "bucket_48_to_72",
                "hard_cap_bucket": "bucket_up_to_96",
                "per_source_cap_bucket": "bucket_up_to_8",
                "minimum_distinct_sources_bucket": "bucket_at_least_8",
            },
            "future_private_input_output_locations": "ignored runs/ only, not read in phase9k",
            "future_phase9l_gate_conditions": list(FUTURE_PHASE9L_GATE_RULES),
            "future_outcome_acquisition_requires_separate_phase9l_boundary": True,
            "future_outcome_acquisition_requires_explicit_phase9k_commit_and_ci_green": True,
        },
        "future_scoring_protocol": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "metrics_and_denominators": "frozen_before_outcome_visibility",
            "inclusion_exclusion_rules": "frozen_before_outcome_visibility",
            "failure_buckets": list(PREDECLARED_FAILURE_BUCKETS),
            "no_threshold_or_metric_tuning_after_outcome_visibility": True,
            "no_posthoc_subgroup_mining_except_predeclared_aggregate_buckets": True,
            "scoring_rules": list(FUTURE_SCORING_RULES),
            "future_scoring_requires_separate_frozen_boundary_after_outcome_acquisition": True,
        },
        "future_adjudication_protocol": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "independence_required": True,
            "minimum_rater_count_if_human_annotations_used": "minimum_at_least_three_independent_raters",
            "disagreement_categories": list(DISAGREEMENT_CATEGORIES),
            "tie_break_flow": "frozen_predeclared_before_adjudication",
            "timing_independent_outcomes_first_adjudication_second": True,
            "adjudication_rules": list(FUTURE_ADJUDICATION_RULES),
            "future_adjudication_requires_separate_frozen_boundary_after_scoring": True,
        },
        "truth_boundary": {key: True for key in TRUTH_BOUNDARY_TRUE_KEYS},
        "no_execution_booleans": {key: False for key in NO_EXECUTION_FALSE_KEYS},
        "privacy_contract": {
            "public_output_aggregate_only": True,
            "private_future_manifests_only_under_ignored_runs": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PRIVACY_FALSE_KEYS},
        },
        "claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_private_candidate_pools": True,
            "validator_does_not_read_phase9h_private_materialized_inventory": True,
            "validator_does_not_read_phase9j_private_annotation_input_rows": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": (
            "future_outcome_acquisition_scoring_adjudication_require_separate_frozen_boundary"
            "_phase9l_requires_phase9k_commit_ci_green_and_explicit_confirmations_boundary"
            "_no_user_approval_no_evidence_success_no_method_product_claim"
        ),
    }


# ---------------------------------------------------------------------------
# Public report privacy scan + validation
# ---------------------------------------------------------------------------

def _scan_public(
    value: Any,
    path: str = "$",
    key: str = "",
    allowed_paths: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    key_lower = key.lower()
    is_allowed_path = allowed_paths is not None and path in allowed_paths
    is_gate_ref = _is_gate_reference_value_path(path)
    if key_lower in {"count"} or key_lower.endswith("_count"):
        errors.append(f"exact public count field at {path}")
    # Forbidden public field words (scoring/labels/outcomes/evidence_success/
    # gold) only apply to non-boolean values at non-allowed-schema paths:
    # boolean attestation keys such as ``scoring_executed`` are boundary checks
    # that must be ``false``, and protocol-freeze section names such as
    # ``future_scoring_protocol`` are at allowed-schema paths.  Unknown keys
    # with forbidden words (not in the allowed schema) are still rejected.
    if not isinstance(value, bool) and not is_allowed_path and any(
        word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS
    ):
        errors.append(f"forbidden public field word at {path}")
    # Private-shaped KEY detection.  Known-good boundary-attestation keys that
    # legitimately contain a private token (e.g. ``per_source_public_facts``,
    # ``commits_public``, ``manifest_locations_public``) are at allowed-schema
    # paths and are exempted here; gate-reference commit/CI keys are allowed
    # paths too.
    if key and PRIVATE_KEY_RE.search(key) and not is_allowed_path:
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(
                _scan_public(child_value, child_path, str(child_key), allowed_paths)
            )
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            child_path = f"{path}[{index}]"
            errors.extend(_scan_public(child_value, child_path, "", allowed_paths))
            # Defense-in-depth: scan list string values for private-shaped
            # tokens even though they have no object key context.  Closed
            # protocol lists already reject extra members via set-equality
            # (see validate_report), but this catches private-shaped tokens
            # in ANY list string value: task_id, bucket_task_id,
            # bucket_private_row_id_failure, private_run_dir, source_path, etc.
            if isinstance(child_value, str) and LIST_VALUE_PRIVATE_TOKEN_RE.search(child_value):
                errors.append(f"private-shaped list value at {child_path}")
    elif isinstance(value, str):
        # Gate-reference commit/CI values are expected public gate constants;
        # they are exempt from the private-shaped value scan only.
        if not is_gate_ref:
            if PRIVATE_SHAPED_VALUE_RE.search(value):
                errors.append(f"private-shaped public value at {path}")
        if path not in DECIMAL_CI_RUN_EXEMPT_PATHS:
            if LONG_DECIMAL_VALUE_RE.search(value):
                errors.append(f"long decimal ci/run shaped public value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
        if CLAIM_WORDING_RE.search(value):
            errors.append(f"claim-making wording at {path}")
        if USER_APPROVAL_WORDING_RE.search(value):
            errors.append(f"user approval wording at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") != STATUS:
        errors.append("status drift")

    # Phase 9F inherited provenance
    prov9f = report.get("phase9f_inherited_provenance", {})
    if prov9f.get("phase9f_status") != PHASE9F_STATUS:
        errors.append("Phase 9F inherited status drift")
    if prov9f.get("phase9f_repair_no_claim") is not True:
        errors.append("Phase 9F inherited repair/no-claim missing")
    if prov9f.get("phase9f_zero_buckets") is not True:
        errors.append("Phase 9F inherited zero-buckets missing")
    if prov9f.get("phase9f_public_fetch_or_clone_executed") is not False:
        errors.append("Phase 9F inherited public fetch/clone must be false")
    if prov9f.get("phase9f_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9F inherited provenance-only boundary missing")

    # Phase 9G inherited provenance.  The exact Phase 9G remote commit/CI run
    # values are intentionally NOT published (bucketed inherited provenance).
    prov9g = report.get("phase9g_inherited_provenance", {})
    if prov9g.get("phase9g_ci_success") is not True:
        errors.append("Phase 9G inherited CI success missing")
    if prov9g.get("phase9g_status") != PHASE9G_STATUS:
        errors.append("Phase 9G inherited status drift")
    if prov9g.get("phase9g_protocol_freeze") is not True:
        errors.append("Phase 9G inherited protocol freeze missing")
    if prov9g.get("phase9g_remote_provenance_bucketed") is not True:
        errors.append("Phase 9G inherited remote provenance must be bucketed")
    if prov9g.get("phase9g_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9G inherited provenance-only boundary missing")

    # Phase 9H gate references
    gate9h = report.get("phase9h_gate_references", {})
    if gate9h.get("phase9h_commit") != PHASE9H_COMMIT:
        errors.append("Phase 9H commit gate reference drift")
    if gate9h.get("phase9h_ci_run") != PHASE9H_CI_RUN:
        errors.append("Phase 9H CI run gate reference drift")
    if gate9h.get("phase9h_ci_success") is not True:
        errors.append("Phase 9H CI success gate missing")
    if gate9h.get("phase9h_status") != PHASE9H_STATUS:
        errors.append("Phase 9H status gate reference drift")
    if gate9h.get("phase9h_source_materialization_readiness_only") is not True:
        errors.append("Phase 9H readiness-only boundary missing")
    if gate9h.get("phase9h_not_proof_annotation_or_outcome_or_evidence_success_works") is not True:
        errors.append("Phase 9H not-proof boundary missing")
    if gate9h.get("phase9h_did_not_generate_annotations_or_outcomes_or_gold_rows_or_evidence_success_or_scoring_rows") is not True:
        errors.append("Phase 9H no-generation boundary missing")
    if gate9h.get("phase9h_private_materialized_inventory_under_ignored_runs_only") is not True:
        errors.append("Phase 9H private inventory under ignored runs boundary missing")
    if gate9h.get("phase9h_gate_required_before_phase9k") is not True:
        errors.append("Phase 9H gate-required boundary missing")

    # Phase 9I gate references
    gate9i = report.get("phase9i_gate_references", {})
    if gate9i.get("phase9i_commit") != PHASE9I_COMMIT:
        errors.append("Phase 9I commit gate reference drift")
    if gate9i.get("phase9i_ci_run") != PHASE9I_CI_RUN:
        errors.append("Phase 9I CI run gate reference drift")
    if gate9i.get("phase9i_ci_success") is not True:
        errors.append("Phase 9I CI success gate missing")
    if gate9i.get("phase9i_status") != PHASE9I_STATUS:
        errors.append("Phase 9I status gate reference drift")
    if gate9i.get("phase9i_protocol_freeze") is not True:
        errors.append("Phase 9I protocol freeze gate missing")
    if gate9i.get("phase9i_annotation_protocol_frozen") is not True:
        errors.append("Phase 9I annotation protocol frozen boundary missing")
    if gate9i.get("phase9i_gate_required_before_phase9k") is not True:
        errors.append("Phase 9I gate-required boundary missing")
    if gate9i.get("phase9i_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9I provenance-only boundary missing")

    # Phase 9J gate references
    gate9j = report.get("phase9j_gate_references", {})
    if gate9j.get("phase9j_commit") != PHASE9J_COMMIT:
        errors.append("Phase 9J commit gate reference drift")
    if gate9j.get("phase9j_ci_run") != PHASE9J_CI_RUN:
        errors.append("Phase 9J CI run gate reference drift")
    if gate9j.get("phase9j_ci_success") is not True:
        errors.append("Phase 9J CI success gate missing")
    if gate9j.get("phase9j_status") != PHASE9J_STATUS:
        errors.append("Phase 9J status gate reference drift")
    if gate9j.get("phase9j_annotation_input_rows_generated") is not True:
        errors.append("Phase 9J annotation input rows generated boundary missing")
    if gate9j.get("phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth") is not True:
        errors.append("Phase 9J routing-precondition-only boundary missing")
    if gate9j.get("phase9j_gate_required_before_phase9k") is not True:
        errors.append("Phase 9J gate-required boundary missing")
    if gate9j.get("phase9j_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9J provenance-only boundary missing")

    # Phase 9K scope
    scope = report.get("phase9k_scope", {})
    for key in ("docs_report_validator_only", "protocol_freeze_only"):
        if scope.get(key) is not True:
            errors.append(f"phase9k scope missing: {key}")
    for key in (
        "public_fetch_clone_executed",
        "source_materialization_executed",
        "task_annotation_generated",
        "private_phase9h_materialized_inventory_read",
        "private_phase9j_annotation_input_rows_read",
        "private_candidate_pool_read",
        "private_registry_read",
        "ignored_runs_read",
        "annotations_generated",
        "outcomes_acquired",
        "gold_rows_generated",
        "evidence_success_evaluated",
        "scoring_executed",
        "adjudication_executed",
        "evaluation_rows_generated",
        "model_fitting",
        "provider_or_llm_calls",
        "runtime_default_or_product_changes",
        "network_fetch_or_clone_or_source_refresh_executed",
    ):
        if scope.get(key) is not False:
            errors.append(f"phase9k execution boundary failed: {key}")
    if scope.get("future_execution_requires_phase9k_commit_and_ci_green") is not True:
        errors.append("phase9k future execution commit+CI-green boundary missing")

    # Future outcome-acquisition protocol
    oa = report.get("future_outcome_acquisition_protocol", {})
    if oa.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("future outcome-acquisition protocol publication level drift")
    if oa.get("outcome_packet_schema") != "frozen_required_fields_only":
        errors.append("outcome packet schema drift")
    required_fields = oa.get("outcome_packet_required_fields")
    if not isinstance(required_fields, list):
        errors.append("outcome packet required fields missing")
    else:
        required_set = set(OUTCOME_PACKET_REQUIRED_FIELDS)
        present_set = set(required_fields)
        missing_fields = required_set - present_set
        if missing_fields:
            errors.append(
                "outcome packet required fields missing: " + ", ".join(sorted(missing_fields))
            )
        extra_fields = present_set - required_set
        if extra_fields:
            errors.append(
                "outcome packet required fields has extra members: " + ", ".join(sorted(extra_fields))
            )
    if oa.get("private_only_fields") != "private_fields_stay_under_ignored_runs_only":
        errors.append("outcome-acquisition private-only fields drift")
    allowed_buckets = oa.get("allowed_public_aggregate_buckets")
    if not isinstance(allowed_buckets, list):
        errors.append("allowed public aggregate buckets missing")
    else:
        required_buckets = set(ALLOWED_PUBLIC_AGGREGATE_BUCKETS)
        present_buckets = set(allowed_buckets)
        missing_buckets = required_buckets - present_buckets
        if missing_buckets:
            errors.append(
                "allowed public aggregate buckets missing: " + ", ".join(sorted(missing_buckets))
            )
        extra_buckets = present_buckets - required_buckets
        if extra_buckets:
            errors.append(
                "allowed public aggregate buckets has extra members: " + ", ".join(sorted(extra_buckets))
            )
    if oa.get("missing_invalid_unavailable_outcome_handling") != "frozen_fail_closed_rules":
        errors.append("outcome missing/invalid/unavailable handling drift")
    oa_rules = oa.get("outcome_acquisition_rules")
    if not isinstance(oa_rules, list) or not oa_rules:
        errors.append("future outcome-acquisition rules missing")
    else:
        required_rules = set(FUTURE_OUTCOME_ACQUISITION_RULES)
        present_rules = set(oa_rules)
        missing_rules = required_rules - present_rules
        if missing_rules:
            errors.append(
                "future outcome-acquisition rules missing: " + ", ".join(sorted(missing_rules))
            )
        extra_rules = present_rules - required_rules
        if extra_rules:
            errors.append(
                "future outcome-acquisition rules has extra members: " + ", ".join(sorted(extra_rules))
            )
    caps = oa.get("inherited_phase9h_aggregate_caps", {})
    expected_caps = {
        "target_inventory_bucket": "bucket_48_to_72",
        "hard_cap_bucket": "bucket_up_to_96",
        "per_source_cap_bucket": "bucket_up_to_8",
        "minimum_distinct_sources_bucket": "bucket_at_least_8",
    }
    for cap_key, expected in expected_caps.items():
        if caps.get(cap_key) != expected:
            errors.append(f"inherited phase9h aggregate cap drift: {cap_key}")
    if oa.get("future_private_input_output_locations") != "ignored runs/ only, not read in phase9k":
        errors.append("future private input/output locations drift")
    gate_conditions = oa.get("future_phase9l_gate_conditions")
    if not isinstance(gate_conditions, list) or not gate_conditions:
        errors.append("future phase9l gate conditions missing")
    else:
        required_gates = set(FUTURE_PHASE9L_GATE_RULES)
        present_gates = set(gate_conditions)
        missing_gates = required_gates - present_gates
        if missing_gates:
            errors.append(
                "future phase9l gate conditions missing: " + ", ".join(sorted(missing_gates))
            )
        extra_gates = present_gates - required_gates
        if extra_gates:
            errors.append(
                "future phase9l gate conditions has extra members: " + ", ".join(sorted(extra_gates))
            )
    if oa.get("future_outcome_acquisition_requires_separate_phase9l_boundary") is not True:
        errors.append("future outcome-acquisition phase9l boundary missing")
    if oa.get("future_outcome_acquisition_requires_explicit_phase9k_commit_and_ci_green") is not True:
        errors.append("future outcome-acquisition explicit phase9k commit+ci-green boundary missing")

    # Future scoring protocol
    sp = report.get("future_scoring_protocol", {})
    if sp.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("future scoring protocol publication level drift")
    if sp.get("metrics_and_denominators") != "frozen_before_outcome_visibility":
        errors.append("scoring metrics/denominators drift")
    if sp.get("inclusion_exclusion_rules") != "frozen_before_outcome_visibility":
        errors.append("scoring inclusion/exclusion rules drift")
    failure_buckets = sp.get("failure_buckets")
    if not isinstance(failure_buckets, list):
        errors.append("predeclared failure buckets missing")
    else:
        required_fb = set(PREDECLARED_FAILURE_BUCKETS)
        present_fb = set(failure_buckets)
        missing_fb = required_fb - present_fb
        if missing_fb:
            errors.append(
                "predeclared failure buckets missing: " + ", ".join(sorted(missing_fb))
            )
        extra_fb = present_fb - required_fb
        if extra_fb:
            errors.append(
                "predeclared failure buckets has extra members: " + ", ".join(sorted(extra_fb))
            )
    if sp.get("no_threshold_or_metric_tuning_after_outcome_visibility") is not True:
        errors.append("no-threshold/metric-tuning boundary missing")
    if sp.get("no_posthoc_subgroup_mining_except_predeclared_aggregate_buckets") is not True:
        errors.append("no-posthoc-subgroup-mining boundary missing")
    sp_rules = sp.get("scoring_rules")
    if not isinstance(sp_rules, list) or not sp_rules:
        errors.append("future scoring rules missing")
    else:
        required_rules = set(FUTURE_SCORING_RULES)
        present_rules = set(sp_rules)
        missing_rules = required_rules - present_rules
        if missing_rules:
            errors.append(
                "future scoring rules missing: " + ", ".join(sorted(missing_rules))
            )
        extra_rules = present_rules - required_rules
        if extra_rules:
            errors.append(
                "future scoring rules has extra members: " + ", ".join(sorted(extra_rules))
            )
    if sp.get("future_scoring_requires_separate_frozen_boundary_after_outcome_acquisition") is not True:
        errors.append("future scoring separate-boundary missing")

    # Future adjudication protocol
    ap = report.get("future_adjudication_protocol", {})
    if ap.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("future adjudication protocol publication level drift")
    if ap.get("independence_required") is not True:
        errors.append("adjudication independence boundary missing")
    if ap.get("minimum_rater_count_if_human_annotations_used") != "minimum_at_least_three_independent_raters":
        errors.append("minimum rater count boundary drift")
    disagreement = ap.get("disagreement_categories")
    if not isinstance(disagreement, list):
        errors.append("disagreement categories missing")
    else:
        required_dc = set(DISAGREEMENT_CATEGORIES)
        present_dc = set(disagreement)
        missing_dc = required_dc - present_dc
        if missing_dc:
            errors.append(
                "disagreement categories missing: " + ", ".join(sorted(missing_dc))
            )
        extra_dc = present_dc - required_dc
        if extra_dc:
            errors.append(
                "disagreement categories has extra members: " + ", ".join(sorted(extra_dc))
            )
    if ap.get("tie_break_flow") != "frozen_predeclared_before_adjudication":
        errors.append("tie-break flow drift")
    if ap.get("timing_independent_outcomes_first_adjudication_second") is not True:
        errors.append("timing independent-outcomes-first boundary missing")
    ap_rules = ap.get("adjudication_rules")
    if not isinstance(ap_rules, list) or not ap_rules:
        errors.append("future adjudication rules missing")
    else:
        required_rules = set(FUTURE_ADJUDICATION_RULES)
        present_rules = set(ap_rules)
        missing_rules = required_rules - present_rules
        if missing_rules:
            errors.append(
                "future adjudication rules missing: " + ", ".join(sorted(missing_rules))
            )
        extra_rules = present_rules - required_rules
        if extra_rules:
            errors.append(
                "future adjudication rules has extra members: " + ", ".join(sorted(extra_rules))
            )
    if ap.get("future_adjudication_requires_separate_frozen_boundary_after_scoring") is not True:
        errors.append("future adjudication separate-boundary missing")

    # Truth boundary
    truth = report.get("truth_boundary", {})
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        if truth.get(key) is not True:
            errors.append(f"truth boundary failed: {key}")

    # No-execution booleans
    no_exec = report.get("no_execution_booleans", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_exec.get(key) is not False:
            errors.append(f"no_execution boundary failed: {key}")

    # Privacy contract
    privacy = report.get("privacy_contract", {})
    for key in (
        "public_output_aggregate_only",
        "private_future_manifests_only_under_ignored_runs",
        "runs_remains_ignored",
    ):
        if privacy.get(key) is not True:
            errors.append(f"privacy contract missing: {key}")
    for key in PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"privacy contract boundary failed: {key}")

    # Claim boundary
    claims = report.get("claim_boundary", {})
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if claims.get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    # Validation summary
    validation = report.get("validation_summary", {})
    for key in (
        "route_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_private_candidate_pools",
        "validator_does_not_read_phase9h_private_materialized_inventory",
        "validator_does_not_read_phase9j_private_annotation_input_rows",
        "public_artifact_privacy_audit_expected",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in (
        "validator_executes_tasks",
        "validator_reads_private_registry",
        "validator_reads_sources",
        "validator_reads_ignored_runs",
    ):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    # Conservative recommendation
    if report.get("conservative_recommendation") != (
        "future_outcome_acquisition_scoring_adjudication_require_separate_frozen_boundary"
        "_phase9l_requires_phase9k_commit_ci_green_and_explicit_confirmations_boundary"
        "_no_user_approval_no_evidence_success_no_method_product_claim"
    ):
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS
    global PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))
    checks.append(("base_status_equals_phase", base["status"] == STATUS))

    # Reject missing Phase 9H/9I/9J gate references.
    for gate_section, commit_key, ci_key in (
        ("phase9h_gate_references", "phase9h_commit", "phase9h_ci_run"),
        ("phase9i_gate_references", "phase9i_commit", "phase9i_ci_run"),
        ("phase9j_gate_references", "phase9j_commit", "phase9j_ci_run"),
    ):
        mutated = copy.deepcopy(base)
        del mutated[gate_section][commit_key]
        checks.append((f"missing_{commit_key}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        del mutated[gate_section][ci_key]
        checks.append((f"missing_{ci_key}_rejected", bool(validate_report(mutated))))

    # Reject wrong Phase 9H/9I/9J commit / CI values.
    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_commit"] = "deadbeef" * 5
    checks.append(("wrong_phase9h_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_ci_run"] = "0000"
    checks.append(("wrong_phase9h_ci_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9i_gate_references"]["phase9i_commit"] = "deadbeef" * 5
    checks.append(("wrong_phase9i_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9i_gate_references"]["phase9i_ci_run"] = "0000"
    checks.append(("wrong_phase9i_ci_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9j_gate_references"]["phase9j_commit"] = "deadbeef" * 5
    checks.append(("wrong_phase9j_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9j_gate_references"]["phase9j_ci_run"] = "0000"
    checks.append(("wrong_phase9j_ci_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema drift.
    mutated = copy.deepcopy(base)
    mutated["status"] = "drift"
    checks.append(("status_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase"] = "drift"
    checks.append(("phase_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["schema_version"] = "drift"
    checks.append(("schema_drift_rejected", bool(validate_report(mutated))))

    # Reject re-introduction of an exact Phase 9G commit/CI field (the exact
    # Phase 9G remote commit/CI run values are intentionally NOT published).
    mutated = copy.deepcopy(base)
    mutated["phase9g_inherited_provenance"]["phase9g_commit"] = "130b6732"
    checks.append(("phase9g_commit_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9g_inherited_provenance"]["phase9g_ci_run"] = "28974306775"
    checks.append(("phase9g_ci_run_field_rejected", bool(validate_report(mutated))))

    # Reject bucketed-provenance flag flipped to False.
    mutated = copy.deepcopy(base)
    mutated["phase9g_inherited_provenance"]["phase9g_remote_provenance_bucketed"] = False
    checks.append(("phase9g_remote_provenance_bucketed_false_rejected", bool(validate_report(mutated))))

    # Reject missing Phase 9F inherited provenance.
    mutated = copy.deepcopy(base)
    mutated["phase9f_inherited_provenance"]["phase9f_status"] = "drift"
    checks.append(("phase9f_status_drift_rejected", bool(validate_report(mutated))))

    # Reject execution booleans set to true.
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["phase9k_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject private_phase9j_annotation_input_rows_read=true specifically.
    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["private_phase9j_annotation_input_rows_read"] = True
    mutated["no_execution_booleans"]["private_phase9j_annotation_input_rows_read"] = True
    checks.append(("private_phase9j_annotation_input_rows_read_rejected", bool(validate_report(mutated))))

    # Reject ignored_runs_read=true.
    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["ignored_runs_read"] = True
    mutated["no_execution_booleans"]["ignored_runs_read"] = True
    checks.append(("ignored_runs_read_rejected", bool(validate_report(mutated))))

    # Reject forbidden public field words in non-boolean values at
    # non-allowed-schema paths.
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(base)
        mutated["phase9k_scope"][bad_key] = "exposed_value"
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    # Reject claim boundary set to true.
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject privacy contract violations.
    for privacy_key in (
        "per_source_public_facts",
        "per_task_public_facts",
        "run_locations_public",
        "repo_names_public",
    ):
        mutated = copy.deepcopy(base)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(base)
        mutated["future_outcome_acquisition_protocol"]["outcome_acquisition_rules"].append(singleton_val)
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((
            f"singleton_regex_{singleton_val}",
            bool(SINGLETON_BUCKET_RE.search(singleton_val)),
        ))

    # Reject exact count fields.
    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["candidate_count"] = 72
    checks.append(("candidate_count_field_rejected", bool(validate_report(mutated))))

    # Reject private-shaped values (URL / path / hash / owner/repo).
    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["example_value"] = "https://example.invalid/repo.git"
    checks.append(("url_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["example_value"] = "owner/repo"
    checks.append(("owner_repo_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["example_value"] = "a" * 40
    checks.append(("hash_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["example_value"] = "src/private.py"
    checks.append(("path_private_shaped_value_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    for bad_key in (
        "private_source_commit",
        "repo_commit",
        "task_ci_run",
        "per_source_bucket",
        "per_task_summary",
        "source_path_bucket",
        "path",
        "repo_name",
        "task_id",
        "row_id",
        "manifest",
        "run_dir",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9k_scope"][bad_key] = "example"
        checks.append((
            f"private_key_{bad_key}_rejected",
            bool(validate_report(mutated)),
        ))
        checks.append((
            f"private_key_regex_{bad_key}",
            bool(PRIVATE_KEY_RE.search(bad_key)),
        ))

    # Reject claim-making wording in exposed string values.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "materialization works and is proven"
    checks.append(("claim_wording_materialization_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["example_note"] = "annotation works"
    checks.append(("claim_wording_annotation_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["example_note"] = "evidence_success achieved"
    checks.append(("claim_wording_evidence_success_rejected", bool(validate_report(mutated))))

    for phrase in (
        "method effectiveness",
        "product readiness",
        "scoring success",
        "outcome success",
        "evaluation works",
        "task annotation readiness",
    ):
        mutated = copy.deepcopy(base)
        mutated["future_outcome_acquisition_protocol"]["outcome_acquisition_rules"].append(phrase)
        checks.append((
            f"claim_phrase_{phrase.replace(' ', '_')}_rejected",
            bool(validate_report(mutated)),
        ))
        checks.append((
            f"claim_phrase_regex_{phrase.replace(' ', '_')}",
            bool(CLAIM_WORDING_RE.search(phrase)),
        ))

    # Reject user-approval wording in exposed string values.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["example_note"] = "user must approve continuation"
    checks.append(("user_must_approve_wording_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["example_note"] = "awaiting user confirmation"
    checks.append(("awaiting_user_confirmation_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["example_note"] = "low-resource continuation approval"
    checks.append(("low_resource_continuation_approval_rejected", bool(validate_report(mutated))))

    # Reject future execution without phase9k commit+CI green.
    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["future_execution_requires_phase9k_commit_and_ci_green"] = False
    checks.append(("future_execution_without_commit_ci_rejected", bool(validate_report(mutated))))

    # Reject a missing required future outcome-acquisition rule.
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["outcome_acquisition_rules"] = [
        r for r in base["future_outcome_acquisition_protocol"]["outcome_acquisition_rules"]
        if r != "no_outcome_acquisition_execution_in_phase9k"
    ]
    checks.append(("missing_required_outcome_acquisition_rule_rejected", bool(validate_report(mutated))))

    # Reject a missing required outcome packet required field.
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["outcome_packet_required_fields"] = [
        f for f in base["future_outcome_acquisition_protocol"]["outcome_packet_required_fields"]
        if f != "task_eligibility_routing_precondition_only"
    ]
    checks.append(("missing_required_outcome_packet_field_rejected", bool(validate_report(mutated))))

    # Reject a missing required future phase9l gate condition.
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["future_phase9l_gate_conditions"] = [
        g for g in base["future_outcome_acquisition_protocol"]["future_phase9l_gate_conditions"]
        if g != "phase9k_commit_and_ci_green_required_before_phase9l"
    ]
    checks.append(("missing_required_phase9l_gate_condition_rejected", bool(validate_report(mutated))))

    # Reject a missing required scoring rule.
    mutated = copy.deepcopy(base)
    mutated["future_scoring_protocol"]["scoring_rules"] = [
        r for r in base["future_scoring_protocol"]["scoring_rules"]
        if r != "no_threshold_or_metric_tuning_after_outcome_visibility"
    ]
    checks.append(("missing_required_scoring_rule_rejected", bool(validate_report(mutated))))

    # Reject a missing required adjudication rule.
    mutated = copy.deepcopy(base)
    mutated["future_adjudication_protocol"]["adjudication_rules"] = [
        r for r in base["future_adjudication_protocol"]["adjudication_rules"]
        if r != "adjudication_rule_is_not_adjudicated_truth"
    ]
    checks.append(("missing_required_adjudication_rule_rejected", bool(validate_report(mutated))))

    # --- Reject EXTRA members in closed protocol lists (set-equality). ---
    # These prove that appending an extra member to a closed protocol list
    # is rejected, not just missing members.  The three private-shaped
    # examples also prove the defense-in-depth list-value private-token scan
    # fires alongside the set-equality check.

    # Append task_id to outcome_packet_required_fields (extra + private).
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["outcome_packet_required_fields"].append("task_id")
    errors = validate_report(mutated)
    checks.append(("extra_outcome_packet_field_task_id_rejected", bool(errors)))
    checks.append((
        "extra_outcome_packet_field_task_id_set_equality",
        any("has extra members" in e for e in errors),
    ))
    checks.append((
        "extra_outcome_packet_field_task_id_private_token_scan",
        any("private-shaped list value" in e for e in errors),
    ))

    # Append bucket_task_id to allowed_public_aggregate_buckets (extra + private).
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["allowed_public_aggregate_buckets"].append("bucket_task_id")
    errors = validate_report(mutated)
    checks.append(("extra_aggregate_bucket_bucket_task_id_rejected", bool(errors)))
    checks.append((
        "extra_aggregate_bucket_bucket_task_id_set_equality",
        any("has extra members" in e for e in errors),
    ))
    checks.append((
        "extra_aggregate_bucket_bucket_task_id_private_token_scan",
        any("private-shaped list value" in e for e in errors),
    ))

    # Append bucket_private_row_id_failure to failure_buckets (extra + private).
    mutated = copy.deepcopy(base)
    mutated["future_scoring_protocol"]["failure_buckets"].append("bucket_private_row_id_failure")
    errors = validate_report(mutated)
    checks.append(("extra_failure_bucket_bucket_private_row_id_failure_rejected", bool(errors)))
    checks.append((
        "extra_failure_bucket_bucket_private_row_id_failure_set_equality",
        any("has extra members" in e for e in errors),
    ))
    checks.append((
        "extra_failure_bucket_bucket_private_row_id_failure_private_token_scan",
        any("private-shaped list value" in e for e in errors),
    ))

    # Reject an extra gate condition (set-equality only, no private token).
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["future_phase9l_gate_conditions"].append("extra_bogus_gate_condition")
    errors = validate_report(mutated)
    checks.append(("extra_phase9l_gate_condition_rejected", bool(errors)))
    checks.append((
        "extra_phase9l_gate_condition_set_equality",
        any("has extra members" in e for e in errors),
    ))

    # Reject an extra adjudication rule (set-equality only, no private token).
    mutated = copy.deepcopy(base)
    mutated["future_adjudication_protocol"]["adjudication_rules"].append("extra_bogus_adjudication_rule")
    errors = validate_report(mutated)
    checks.append(("extra_adjudication_rule_rejected", bool(errors)))
    checks.append((
        "extra_adjudication_rule_set_equality",
        any("has extra members" in e for e in errors),
    ))

    # Reject an extra scoring rule (set-equality only, no private token).
    mutated = copy.deepcopy(base)
    mutated["future_scoring_protocol"]["scoring_rules"].append("extra_bogus_scoring_rule")
    errors = validate_report(mutated)
    checks.append(("extra_scoring_rule_rejected", bool(errors)))
    checks.append((
        "extra_scoring_rule_set_equality",
        any("has extra members" in e for e in errors),
    ))

    # Reject an extra disagreement category (set-equality only, no private token).
    mutated = copy.deepcopy(base)
    mutated["future_adjudication_protocol"]["disagreement_categories"].append("extra_bogus_disagreement_category")
    errors = validate_report(mutated)
    checks.append(("extra_disagreement_category_rejected", bool(errors)))
    checks.append((
        "extra_disagreement_category_set_equality",
        any("has extra members" in e for e in errors),
    ))

    # Reject an extra outcome-acquisition rule (set-equality only, no private token).
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["outcome_acquisition_rules"].append("extra_bogus_outcome_acquisition_rule")
    errors = validate_report(mutated)
    checks.append(("extra_outcome_acquisition_rule_rejected", bool(errors)))
    checks.append((
        "extra_outcome_acquisition_rule_set_equality",
        any("has extra members" in e for e in errors),
    ))

    # Reject a private-shaped list value that is NOT a closed-list extra
    # member — appends private_run_dir to outcome_acquisition_rules and
    # confirms the private-token scan fires (this value is also an extra
    # member, but the private-token scan is the defense-in-depth signal).
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["outcome_acquisition_rules"].append("private_run_dir")
    errors = validate_report(mutated)
    checks.append(("private_list_value_private_run_dir_rejected", bool(errors)))
    checks.append((
        "private_list_value_private_run_dir_token_scan",
        any("private-shaped list value" in e for e in errors),
    ))

    # Reject source_path as a private-shaped list value.
    mutated = copy.deepcopy(base)
    mutated["future_scoring_protocol"]["scoring_rules"].append("source_path")
    errors = validate_report(mutated)
    checks.append(("private_list_value_source_path_rejected", bool(errors)))
    checks.append((
        "private_list_value_source_path_token_scan",
        any("private-shaped list value" in e for e in errors),
    ))

    # Reject inherited cap drift.
    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["inherited_phase9h_aggregate_caps"]["target_inventory_bucket"] = "bucket_wrong"
    checks.append(("inherited_cap_drift_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Reject truth-boundary violation.
    mutated = copy.deepcopy(base)
    mutated["truth_boundary"]["eligibility_is_not_correctness"] = False
    checks.append(("truth_boundary_eligibility_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["truth_boundary"]["adjudication_rule_is_not_adjudicated_truth"] = False
    checks.append(("truth_boundary_adjudication_rejected", bool(validate_report(mutated))))

    # Reject minimum-rater-count drift.
    mutated = copy.deepcopy(base)
    mutated["future_adjudication_protocol"]["minimum_rater_count_if_human_annotations_used"] = "drift"
    checks.append(("minimum_rater_count_drift_rejected", bool(validate_report(mutated))))

    # Gate-reference commit values are exempt from private-shaped value scan
    # but a non-gate-reference key with a hash value is still rejected.
    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["example_hash"] = "d997caab5487e66c544f657645d70c97f3b780e2"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    # Non-whitelisted CI run key/value is rejected (the exact gate-reference
    # path exemption does not cover keys outside the schema).
    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["task_ci_run"] = "28980705743"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    checks.append((
        "non_whitelisted_ci_run_key_not_exempt",
        any("private-shaped public key" in e for e in errors),
    ))

    # Validate a temp-file round-trip.
    with tempfile.TemporaryDirectory(prefix="phase9k_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- strict allowed-key checking rejects unknown fields. ---
    mutated = copy.deepcopy(base)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9k_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_outcome_protocol_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_scoring_protocol"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scoring_protocol_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_adjudication_protocol"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_adjudication_protocol_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_outcome_acquisition_protocol"]["inherited_phase9h_aggregate_caps"]["unexpected_cap"] = "x"
    checks.append(("unknown_nested_field_caps_rejected", bool(validate_report(mutated))))

    # --- --validate-report fails closed on ignored/private paths. ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9k" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9k_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "other_phase" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading (no real file needed).
    runs_cli_path = str(REPO / "runs" / "phase9k" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Prove the validator/self-test did not fetch/read private.
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_sources", SOURCE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append((
        "selftest_does_not_read_private_candidate_pools",
        PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS == 0,
    ))
    checks.append((
        "selftest_does_not_read_phase9h_private_materialized_inventory",
        PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS == 0,
    ))
    checks.append((
        "selftest_does_not_read_phase9j_private_annotation_input_rows",
        PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS == 0,
    ))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9K outcome-acquisition/scoring/adjudication protocol freeze"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.validate_report:
        # Fail closed: --validate-report may only read the Phase 9K public
        # artifact report, never ignored/private paths such as runs/ or paths
        # outside the public artifacts/ root.
        ok, reason = _validate_report_path_is_public(args.validate_report)
        if not ok:
            print(f"ERROR: {reason}: {args.validate_report}", file=sys.stderr)
            return 1
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.write_report:
        report = build_public_report()
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({"status": report["status"], "public_report": str(args.output)}, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
