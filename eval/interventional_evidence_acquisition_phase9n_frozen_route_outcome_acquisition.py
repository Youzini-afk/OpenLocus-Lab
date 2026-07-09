#!/usr/bin/env python3
"""Phase 9N frozen-route outcome-observable acquisition (availability only).

This runner has one narrow purpose: under explicit confirmations and the frozen
Phase 9M outcome-observable acquisition route protocol, execute the SINGLE frozen
route only.  It reads the Phase 9H private materialized sources (the actual
source content) under ignored ``runs/`` only, reads the Phase 9J private
annotation-input rows under ignored ``runs/`` only (as routing/precondition
metadata only, NOT benchmark truth), performs deterministic manual extraction
from the Phase 9H materialized sources only (no LLM, no provider, no model
inference or judgment), and publishes only an aggregate/bucketed public
availability report.

It does NOT do scoring, adjudication, gold labels, benchmark labels,
evidence_success, correctness, precision/recall, pass/fail, result labels,
provider/LLM/model/network/fetch/clone/source refresh, model fitting/training,
runtime/default/product changes, or method/product/performance/provider/model
claims.  It does NOT read Phase 9L private outcome packets.  It does NOT use
Phase 9J annotation-input rows as benchmark truth (routing/precondition
metadata only).

Outcome-observable packets record only the outcome acquisition state
(acquired/unavailable/invalid) plus the source-grounded evidence-form
confirmation (file_path_and_line_range_only, no snippet stored).  They do NOT
compute scores, correctness, pass/fail, evidence_success, precision/recall,
benchmark results, gold answers, adjudicated answers, or method success.  The
acquisition state is recorded honestly: acquired only when the materialized
source file exists, is readable, and the line range is valid within the file;
unavailable when the source is absent/unreadable or does not contain the
observable; invalid when the observable is malformed, not source-grounded,
ambiguous, or exceeds the whitelisted evidence form.

The closed route vocabulary (authorized private inputs, extraction procedure,
observable definition, invalid/unavailable criteria, replacement rule, stop
rule, route-order/fallback rule) is set-equality validated against the frozen
Phase 9M public report's closed lists.  There is exactly ONE fixed route; no
fallback, no retry, no trying-routes-until-one-works, no route-order drift.

The Phase 9M public gate reference values (remote commit and CI run) are the
only primary public gate references published by Phase 9N.  Phase 9L and Phase
9K gate references are carried forward from the Phase 9M public report
(secondary, whitelisted).  Local same-tree git commits are not read or compared;
the supplied confirmation values are matched against the frozen public gate
constants only.

Outcome acquisition is not scoring, not adjudication, not evidence_success, not
method success, not benchmark success, not product readiness.  Unavailable and
invalid outcomes are NOT counted as failure, success, or partial.  No scoring
denominator exists in Phase 9N.
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

# Compact Phase 9N slug (kept short so the absolute artifact report path stays
# comfortably under the Windows MAX_PATH (260) limit).  Boundary wording in the
# report body/docs is NOT weakened -- only the path-dependent slug is shortened.
PHASE = "phase9n_frozen_route_outcome_acquisition_no_scoring_no_claim"
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

# ---------------------------------------------------------------------------
# Status shapes (availability-only).
# ---------------------------------------------------------------------------
# Executed: the frozen route ran and acquired nonzero valid outcome
# observables.
STATUS_EXECUTED_VALID = (
    "phase9n_frozen_route_executed_valid_acquired_nonzero_aggregate_availability"
    "_no_scoring_no_adjudication_no_claim"
)
# Executed: the frozen route ran but acquired zero (all unavailable only).
STATUS_EXECUTED_ZERO_UNAVAILABLE = (
    "phase9n_frozen_route_executed_acquired_zero_unavailable_only"
    "_aggregate_availability_no_scoring_no_adjudication_no_claim"
)
# Executed: the frozen route ran but acquired zero (all invalid only).
STATUS_EXECUTED_ZERO_INVALID = (
    "phase9n_frozen_route_executed_acquired_zero_invalid_only"
    "_aggregate_availability_no_scoring_no_adjudication_no_claim"
)
# Executed: the frozen route ran but acquired zero (invalid and unavailable).
STATUS_EXECUTED_ZERO_INVALID_AND_UNAVAILABLE = (
    "phase9n_frozen_route_executed_acquired_zero_invalid_and_unavailable"
    "_aggregate_availability_no_scoring_no_adjudication_no_claim"
)
STATUS_REPAIR = "phase9n_frozen_route_repair_no_claim"
STATUS_GATE_MISSING = "phase9n_blocked_phase9m_gate_missing_or_not_green_no_claim"
STATUS_ORDER_AMBIGUITY = (
    "phase9n_blocked_deterministic_ordering_ambiguity_no_execution_no_claim"
)
ALLOWED_STATUSES = {
    STATUS_EXECUTED_VALID,
    STATUS_EXECUTED_ZERO_UNAVAILABLE,
    STATUS_EXECUTED_ZERO_INVALID,
    STATUS_EXECUTED_ZERO_INVALID_AND_UNAVAILABLE,
    STATUS_REPAIR,
    STATUS_GATE_MISSING,
    STATUS_ORDER_AMBIGUITY,
}
# The set of statuses that represent actual frozen-route execution.
EXECUTED_STATUSES = {
    STATUS_EXECUTED_VALID,
    STATUS_EXECUTED_ZERO_UNAVAILABLE,
    STATUS_EXECUTED_ZERO_INVALID,
    STATUS_EXECUTED_ZERO_INVALID_AND_UNAVAILABLE,
}

# ---------------------------------------------------------------------------
# Phase 9M public gate reference values (oracle-provided).  These are the
# PRIMARY gate references for Phase 9N.  Local same-tree git commits are not
# read or compared; the supplied confirmation values are matched against the
# frozen public gate constants only.
# ---------------------------------------------------------------------------
PHASE9M_PHASE = "phase9m_outcome_route_protocol_freeze_no_claim"
PHASE9M_STATUS = (
    "phase9m_outcome_observable_acquisition_route_protocol_freeze"
    "_no_execution_no_scoring_no_adjudication_no_claim"
)
PHASE9M_COMMIT = "0b0356b43d98edad0a3483132bdfae12ed520bb9"
PHASE9M_CI_RUN = "28983935272"
PHASE9M_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE9M_PHASE / f"{PHASE9M_PHASE}_report.json"
)

# Phase 9L and Phase 9K gate references (carried forward from the Phase 9M
# public report; secondary whitelisted gate references).
PHASE9L_STATUS = (
    "phase9l_outcome_acquisition_executed_unavailable_only"
    "_no_scoring_no_adjudication_no_claim"
)
PHASE9L_COMMIT = "c815a77d4dea3b77efe5dae0abe06006045294e9"
PHASE9L_CI_RUN = "28983185765"

PHASE9K_STATUS = "phase9k_outcome_scoring_protocol_freeze_no_claim"
PHASE9K_COMMIT = "233a16e6672b05b87b09be5b920f8fc9dd72e274"
PHASE9K_CI_RUN = "28981994749"

# Phase 9H/9I/9J inherited provenance (carried forward, bucketed only).  The
# exact Phase 9H/9I/9J remote commit/CI run values are intentionally NOT
# published in the Phase 9N report/docs (tighter privacy).
PHASE9H_STATUS = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_readiness_no_scoring_no_claim"
)
PHASE9I_STATUS = (
    "phase9i_materialized_inventory_to_task_annotation_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9J_STATUS = "phase9j_annotation_input_rows_generated_no_scoring_no_claim"
PHASE9G_STATUS = (
    "phase9g_candidate_source_pool_network_fetch_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9F_STATUS = "phase9f_public_source_fetch_clone_materialization_repair_no_claim"

# Inherited aggregate caps/buckets from Phase 9H (frozen, aggregate-only).
TARGET_INVENTORY_MIN = 48
TARGET_INVENTORY_MAX = 72
HARD_INVENTORY_CAP = 96
PER_SOURCE_CAP = 8
MIN_DISTINCT_SOURCES = 8

# Expected private Phase 9H materialized sources location (under ignored
# runs/ only).  Phase 9N reads the materialization rows + the actual source
# files in the workspace.
PHASE9H_PRIVATE_RUN_DIR = (
    REPO / "runs"
    / "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_no_scoring_no_claim" / "current"
)
PHASE9H_PRIVATE_MANIFEST = (
    PHASE9H_PRIVATE_RUN_DIR / "private_phase9h_materialization_manifest.json"
)
PHASE9H_PRIVATE_ROWS = (
    PHASE9H_PRIVATE_RUN_DIR / "private_phase9h_materialization_rows.json"
)
PHASE9H_PRIVATE_WORKSPACE = (
    PHASE9H_PRIVATE_RUN_DIR / "private_materialized_sources_workspace"
)

# Expected private Phase 9J annotation-input location (under ignored runs/ only).
PHASE9J_PHASE = "phase9j_annotation_input_execution_no_scoring_no_claim"
PHASE9J_PRIVATE_RUN_DIR = REPO / "runs" / PHASE9J_PHASE / "current"
PHASE9J_PRIVATE_MANIFEST = (
    PHASE9J_PRIVATE_RUN_DIR / "private_phase9j_annotation_input_manifest.json"
)
PHASE9J_PRIVATE_ROWS = (
    PHASE9J_PRIVATE_RUN_DIR / "private_phase9j_annotation_input_rows.json"
)

# ---------------------------------------------------------------------------
# Frozen outcome-observable acquisition route (from Phase 9M).  These closed
# lists are validator-checked for set-equality against the Phase 9M public
# report's frozen lists AND for private-shaped tokens in list values.
# ---------------------------------------------------------------------------
ROUTE_PUBLICATION_LEVEL = "aggregate_bucketed_protocol_only"
ROUTE_FORM = "single_fixed_route_no_fallback_no_retry"

AUTHORIZED_PRIVATE_INPUTS = (
    "phase9h_materialized_sources_authorized_to_be_read_in_phase9n_only",
    "phase9j_annotation_input_rows_authorized_to_be_read_in_phase9n"
    "_as_routing_precondition_metadata_only_not_benchmark_truth",
)

AUTHORIZED_DERIVED_ARTIFACTS = (
    "evidence_acquisition_method_outputs_authorized_to_be_generated_and_read"
    "_in_phase9n_under_ignored_runs_only",
    "outcome_observable_packets_authorized_to_be_generated_in_phase9n"
    "_under_ignored_runs_only",
    "no_public_derived_artifacts_except_aggregate_availability_buckets",
)

EXTRACTION_PROCEDURE = (
    "deterministic_manual_extraction_from_phase9h_materialized_sources_only",
    "no_llm_no_provider_calls_in_phase9n",
    "no_model_inference_or_judgment_in_outcome_observable_acquisition",
)

OBSERVABLE_DEFINITION = (
    "outcome_observable_is_directly_readable_source_grounded_fact"
    "_from_authorized_materialized_source_only",
    "outcome_observable_answers_the_phase9j_outcome_acquisition_precondition"
    "_not_an_inference",
    "outcome_observable_must_match_the_phase9j_expected_evidence_form",
)

INVALID_CRITERIA = (
    "acquired_observable_malformed_or_not_source_grounded_is_invalid",
    "acquired_observable_ambiguous_or_self_contradictory_is_invalid",
    "acquired_observable_exceeds_whitelisted_evidence_form_is_invalid",
)

UNAVAILABLE_CRITERIA = (
    "materialized_source_absent_or_not_readable_is_unavailable",
    "materialized_source_does_not_contain_outcome_observable_is_unavailable",
    "outcome_observable_cannot_be_acquired_from_authorized_reads_alone_is_unavailable",
)

REPLACEMENT_RULE_IF_INVALID = (
    "invalid_outcome_rejected_before_any_scoring_with_replacement_only",
    "replacement_uses_next_deterministic_source_or_task_candidate"
    "_no_retry_no_fallback_route",
    "replacement_uses_no_performance_evidence_model_or_downstream_feedback",
)

STOP_RULE = (
    "stop_per_task_when_outcome_observable_acquired_and_valid"
    "_or_single_route_attempt_exhausted",
    "stop_per_source_at_inherited_phase9h_per_source_cap_bucket",
    "no_retry_no_fallback_route_after_unavailable_or_invalid",
)

ROUTE_ORDER_AND_FALLBACK_RULE = (
    "single_fixed_route_deterministic_manual_extraction_no_route_order_drift",
    "no_trying_routes_until_one_works",
    "failure_transition_record_unavailable_or_invalid_and_stop_no_fallback_route",
)

# Closed protocol lists whose members are validator set-equality checked
# against the Phase 9M public report's frozen lists.
CLOSED_ROUTE_LISTS = (
    ("authorized_private_inputs", AUTHORIZED_PRIVATE_INPUTS),
    ("authorized_derived_artifacts", AUTHORIZED_DERIVED_ARTIFACTS),
    ("extraction_procedure", EXTRACTION_PROCEDURE),
    ("observable_definition", OBSERVABLE_DEFINITION),
    ("invalid_criteria", INVALID_CRITERIA),
    ("unavailable_criteria", UNAVAILABLE_CRITERIA),
    ("replacement_rule_if_invalid", REPLACEMENT_RULE_IF_INVALID),
    ("stop_rule", STOP_RULE),
    ("route_order_and_fallback_rule", ROUTE_ORDER_AND_FALLBACK_RULE),
)

# The expected evidence form (from Phase 9J rows).  The outcome observable is a
# file_path_and_line_range confirmation: the materialized source file exists at
# the candidate path, is readable, and the line range is valid within the file.
# No snippet is stored.
EXPECTED_EVIDENCE_FORM = "file_path_and_line_range_only_no_snippet_stored"

# Outcome-observable acquisition states.
OUTCOME_ACQUISITION_STATES = ("acquired", "unavailable", "invalid")

# Frozen outcome-observable packet required fields (routing/precondition
# metadata + acquisition state only, NOT benchmark truth, NOT scoring).
OUTCOME_PACKET_REQUIRED_FIELDS: dict[str, type] = {
    "private_annotation_input_ref": str,
    "source_order_index_private": int,
    "candidate_order_index_private": int,
    "task_eligibility_routing_precondition_only": str,
    "evidence_localization_requirement": str,
    "expected_evidence_form": str,
    "outcome_acquisition_precondition": str,
    "annotation_input_metadata_reference": str,
    "outcome_acquisition_state": str,
    "outcome_observable_acquired": bool,
    "replacement_needed": bool,
    "evidence_form_confirmed_source_grounded": bool,
    "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": bool,
}

# Forbidden tokens in outcome-packet field names (defense in depth; the strict
# allowed-field check already rejects any unknown field).
FORBIDDEN_OUTCOME_PACKET_TOKENS = (
    "score_value", "correctness", "pass_fail", "pass_or_fail",
    "evidence_success_value", "precision", "recall",
    "benchmark_result", "gold_answer", "adjudicated_answer",
    "method_success", "ground_truth", "truth_label",
    "expected_answer", "expected_output", "expected_result",
    "result_label", "result_truth",
)

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "scoring_executed",
    "adjudication_executed",
    "gold_labels_generated",
    "benchmark_labels_generated",
    "evidence_success_evaluated",
    "correctness_evaluated",
    "precision_recall_computed",
    "result_labels_generated",
    "model_fitting_executed",
    "provider_or_llm_calls_executed",
    "runtime_default_or_product_changes_executed",
    "network_fetch_or_clone_or_source_refresh_executed",
    "annotation_truth_generated",
    "adjudicated_answer_generated",
    "phase9l_outcome_packets_read",
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
    "adjudication_claim",
    "correctness_claim",
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
    "outcome_packets_public",
    "outcome_observables_public",
)

# Forbidden public field words; only apply to non-boolean values so boolean
# boundary attestation keys are not false-flagged.
FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
    "correctness",
    "precision",
    "recall",
    "benchmark",
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants (full commit SHA / CI run ID).  Phase 9M is the
# primary gate; Phase 9L and Phase 9K are secondary (carried from 9M).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9m_gate_references.phase9m_commit",
        "$.phase9m_gate_references.phase9m_ci_run",
        "$.phase9l_gate_references.phase9l_commit",
        "$.phase9l_gate_references.phase9l_ci_run",
        "$.phase9k_gate_references.phase9k_commit",
        "$.phase9k_gate_references.phase9k_ci_run",
    }
)

DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9m_gate_references.phase9m_ci_run",
        "$.phase9l_gate_references.phase9l_ci_run",
        "$.phase9k_gate_references.phase9k_ci_run",
    }
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
LONG_DECIMAL_VALUE_RE = re.compile(r"\b\d{8,}\b")
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:count_1|bucket_one|bucket_1|bucket_up_to_1|bucket_at_most_1|n_1|singleton)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(
    r"(?:repo|repo_name|repo_url|owner|source_url|url"
    r"|candidate_identity|commit|commit_sha|ci_run|sha|hash"
    r"|path|range|snippet|task_id|row_id"
    r"|manifest|run_dir|per_source|per_task)",
    re.IGNORECASE,
)
LIST_VALUE_PRIVATE_TOKEN_RE = re.compile(
    r"(?:task_id|row_id|run_dir|source_path"
    r"|manifest_path|candidate_id|commit_sha)",
    re.IGNORECASE,
)
CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"materialization\s+(?:works|succeeded|proven|established)"
    r"|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)"
    r"|clone\s+(?:works|succeeded|proven|established)"
    r"|annotation\s+(?:works|succeeded|proven|established)"
    r"|outcome\s+acquisition\s+(?:works|succeeded|proven|established)"
    r"|frozen\s+route\s+(?:works|succeeded|proven|established)"
    r"|evidence_success\s+(?:achieved|proven|established|confirmed)"
    r"|method\s+(?:proven|established|works|winner|effectiveness)"
    r"|product\s+readiness"
    r"|scoring\s+success"
    r"|outcome\s+success"
    r"|adjudication\s+success"
    r"|evaluation\s+works"
    r"|task\s+annotation\s+readiness"
    r"|lift\s+(?:proven|established|achieved)"
    r"|route\s+(?:works|succeeded|proven|established)"
    r"|acquisition\s+success"
    r")\b",
    re.IGNORECASE,
)
USER_APPROVAL_WORDING_RE = re.compile(
    r"\b(?:user\s+(?:must|should|needs?\s+to)\s+(?:approve|authorize|confirm)"
    r"|awaiting\s+user\s+(?:approval|authorization|confirmation)"
    r"|requires?\s+user\s+(?:approval|authorization)"
    r"|low.resource\s+continuation\s+(?:approval|authorization))\b",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(
    r"\b(?:TBD|TODO|FIXME|XXX|placeholder|placeholder_value|fill_in|not_set"
    r"|stub_value|dummy_value)\b",
    re.IGNORECASE,
)
# Forbidden standalone status wording (word-boundary matched so underscore-joined
# boundary negations like ``no_gold`` are NOT flagged).
FORBIDDEN_STATUS_WORDING_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:validated|benchmark|gold|correctness)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_FILE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
NETWORK_CALL_ATTEMPTS = 0


# ---------------------------------------------------------------------------
# Ignored-runs / privacy helpers
# ---------------------------------------------------------------------------

def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def _assert_under_ignored_runs(path: Path) -> Path:
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if resolved != runs_root and runs_root not in resolved.parents:
        raise ValueError("private output must stay under ignored runs/")
    if not _runs_is_ignored():
        raise ValueError("runs/ must remain ignored before private output is allowed")
    return resolved


# ---------------------------------------------------------------------------
# Bucket helpers
# ---------------------------------------------------------------------------

def _bucket_availability(value: int) -> str:
    """Bucket an availability count into privacy-safe buckets only.

    Zero -> ``bucket_zero``; nonzero -> ``bucket_nonzero_redacted`` (no exact
    count, no singleton, no per-source/per-task fact).
    """
    if value <= 0:
        return "bucket_zero"
    return "bucket_nonzero_redacted"


# ---------------------------------------------------------------------------
# Phase 9M gate validation (reads tracked public report only)
# ---------------------------------------------------------------------------

def _phase9m_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9M public gate.  Reads the tracked public report only."""
    errors: list[str] = []
    if report is None:
        if not PHASE9M_PUBLIC_REPORT.exists():
            return ["Phase 9M public report missing"]
        report = json.loads(PHASE9M_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9M public report must be object"]
    if report.get("status") != PHASE9M_STATUS:
        errors.append("Phase 9M public report status drift")
    if report.get("schema_version") != f"{PHASE9M_PHASE}_report_v1":
        errors.append("Phase 9M public report schema drift")
    route = report.get("frozen_outcome_observable_acquisition_route", {})
    if route.get("future_phase9n_boundary") is not True:
        errors.append("Phase 9M future_phase9n_boundary gate missing")
    if route.get("no_llm_no_provider_frozen") is not True:
        errors.append("Phase 9M no_llm_no_provider_frozen gate missing")
    if route.get("no_trying_routes_until_one_works_unless_pre_frozen") is not True:
        errors.append("Phase 9M no_trying_routes gate missing")
    # Verify the closed route lists in the 9M report match the frozen constants.
    for key, expected in CLOSED_ROUTE_LISTS:
        report_list = route.get(key)
        if not isinstance(report_list, list):
            errors.append(f"Phase 9M frozen route list missing: {key}")
            continue
        if set(report_list) != set(expected):
            errors.append(f"Phase 9M frozen route list drift: {key}")
    if supplied_commit is not None and supplied_commit != PHASE9M_COMMIT:
        errors.append("supplied Phase 9M commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9M_CI_RUN:
        errors.append("supplied Phase 9M CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9M_STATUS:
        errors.append("supplied Phase 9M status does not match public gate reference")
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Phase 9H private materialized-sources reading (under ignored runs/ only)
# ---------------------------------------------------------------------------

def _find_phase9h_private_materialization() -> tuple[Path, Path, Path] | None:
    """Locate the Phase 9H private manifest + rows + workspace under ignored runs/."""
    global PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS
    PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = PHASE9H_PRIVATE_MANIFEST.resolve()
    rows_resolved = PHASE9H_PRIVATE_ROWS.resolve()
    workspace_resolved = PHASE9H_PRIVATE_WORKSPACE.resolve()
    if runs_root not in manifest_resolved.parents:
        return None
    if runs_root not in rows_resolved.parents:
        return None
    if runs_root not in workspace_resolved.parents:
        return None
    if not manifest_resolved.exists() or not rows_resolved.exists():
        return None
    if not workspace_resolved.exists():
        return None
    return manifest_resolved, rows_resolved, workspace_resolved


def _validate_phase9h_row_shape(row: Any, index: int) -> list[str]:
    """Validate a single Phase 9H private materialization row shape."""
    errors: list[str] = []
    if not isinstance(row, dict):
        errors.append(f"Phase 9H row {index} not object")
        return errors
    required: dict[str, type] = {
        "candidate_order_index_private": int,
        "source_order_index_private": int,
        "private_candidate_id": str,
        "private_source_file_path": str,
        "private_source_sha256": str,
        "source_snippet_stored": bool,
        "public_access_check_passed": bool,
        "task_type": str,
    }
    for field, expected_type in required.items():
        if field not in row:
            errors.append(f"Phase 9H row {index} missing field: {field}")
        elif not isinstance(row[field], expected_type):
            errors.append(f"Phase 9H row {index} field {field} wrong type")
    lr = row.get("private_line_range")
    if not isinstance(lr, dict):
        errors.append(f"Phase 9H row {index} missing private_line_range")
    else:
        if not isinstance(lr.get("start"), int) or not isinstance(lr.get("end"), int):
            errors.append(f"Phase 9H row {index} line_range start/end must be int")
        elif lr["start"] < 1 or lr["end"] < lr["start"]:
            errors.append(f"Phase 9H row {index} line_range invalid")
    if row.get("source_snippet_stored") is not False:
        errors.append(f"Phase 9H row {index} source_snippet_stored must be false")
    return errors


def _read_phase9h_private_materialization(
    manifest_path: Path, rows_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Read the Phase 9H private manifest + rows under ignored runs/ only."""
    global PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS
    PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = manifest_path.resolve()
    rows_resolved = rows_path.resolve()
    if runs_root not in manifest_resolved.parents or runs_root not in rows_resolved.parents:
        return {}, [], ["Phase 9H private materialization must be under ignored runs/"]
    try:
        manifest = json.loads(manifest_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9H private manifest unreadable"]
    try:
        rows = json.loads(rows_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9H private rows unreadable"]
    if not isinstance(rows, list):
        return {}, [], ["Phase 9H private rows must be a list"]
    row_errors: list[str] = []
    valid_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        row_errs = _validate_phase9h_row_shape(row, index)
        row_errors.extend(row_errs)
        if not row_errs:
            valid_rows.append(row)
    return manifest, valid_rows, row_errors


# ---------------------------------------------------------------------------
# Phase 9J private annotation-input reading (under ignored runs/ only)
# ---------------------------------------------------------------------------

def _find_phase9j_private_annotation_input() -> tuple[Path, Path] | None:
    """Locate the Phase 9J private manifest + rows under ignored runs/ only."""
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = PHASE9J_PRIVATE_MANIFEST.resolve()
    rows_resolved = PHASE9J_PRIVATE_ROWS.resolve()
    if runs_root not in manifest_resolved.parents:
        return None
    if runs_root not in rows_resolved.parents:
        return None
    if not manifest_resolved.exists() or not rows_resolved.exists():
        return None
    return manifest_resolved, rows_resolved


def _validate_phase9j_manifest_shape(manifest: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["Phase 9J manifest must be object"]
    if manifest.get("phase") != PHASE9J_PHASE:
        errors.append("Phase 9J manifest phase drift")
    if manifest.get(
        "annotation_input_rows_are_routing_precondition_only_not_benchmark_truth"
    ) is not True:
        errors.append("Phase 9J manifest routing-precondition-only boundary missing")
    rows = manifest.get("annotation_input_rows_private")
    if not isinstance(rows, list):
        errors.append("Phase 9J manifest missing annotation_input_rows_private list")
    aggregate = manifest.get("aggregate_private_totals")
    if not isinstance(aggregate, dict):
        errors.append("Phase 9J manifest missing aggregate_private_totals")
    return errors


def _validate_phase9j_row_shape(row: Any, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(row, dict):
        errors.append(f"Phase 9J row {index} not object")
        return errors
    required: dict[str, type] = {
        "private_candidate_ref": str,
        "source_order_index_private": int,
        "candidate_order_index_private": int,
        "task_eligibility_input": str,
        "evidence_localization_requirement": str,
        "expected_evidence_form": str,
        "outcome_acquisition_preconditions": str,
        "adjudication_rules": str,
        "rejection_or_replacement_rules_before_scoring": str,
        "annotation_input_is_routing_precondition_only_not_benchmark_truth": bool,
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": bool,
    }
    for field, expected_type in required.items():
        if field not in row:
            errors.append(f"Phase 9J row {index} missing field: {field}")
        elif not isinstance(row[field], expected_type):
            errors.append(f"Phase 9J row {index} field {field} wrong type")
    if row.get(
        "annotation_input_is_routing_precondition_only_not_benchmark_truth"
    ) is not True:
        errors.append(f"Phase 9J row {index} routing-precondition-only boundary failed")
    if row.get(
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels"
    ) is not True:
        errors.append(f"Phase 9J row {index} no-outcomes/gold/scoring boundary failed")
    return errors


def _read_phase9j_private_annotation_input(
    manifest_path: Path, rows_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Read the Phase 9J private manifest + rows under ignored runs/ only."""
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = manifest_path.resolve()
    rows_resolved = rows_path.resolve()
    if runs_root not in manifest_resolved.parents or runs_root not in rows_resolved.parents:
        return {}, [], ["Phase 9J private annotation-input must be under ignored runs/"]
    try:
        manifest = json.loads(manifest_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9J private manifest unreadable"]
    try:
        rows = json.loads(rows_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9J private rows unreadable"]
    manifest_errors = _validate_phase9j_manifest_shape(manifest)
    if manifest_errors:
        return {}, [], manifest_errors
    if not isinstance(rows, list):
        return {}, [], ["Phase 9J private rows must be a list"]
    row_errors: list[str] = []
    valid_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        row_errs = _validate_phase9j_row_shape(row, index)
        row_errors.extend(row_errs)
        if not row_errs:
            valid_rows.append(row)
    return manifest, valid_rows, row_errors


# ---------------------------------------------------------------------------
# Deterministic manual extraction (the frozen route)
# ---------------------------------------------------------------------------

def _read_materialized_source_file(
    workspace: Path, source_order_index: int, relative_path: str
) -> tuple[str | None, int, str]:
    """Read a single materialized source file deterministically.

    Returns (content, line_count, read_error).  ``content`` is None if the
    file is absent or unreadable.  No snippet is stored; only line_count is
    used for line-range validation.  This is deterministic manual extraction
    only -- no LLM, no provider, no model inference or judgment.
    """
    global SOURCE_FILE_READ_ATTEMPTS
    SOURCE_FILE_READ_ATTEMPTS += 1
    # Deterministic path construction: workspace / private_source_N / relative
    source_dir = workspace / f"private_source_{source_order_index}"
    full_path = (source_dir / relative_path).resolve()
    # Fail-closed: the resolved path must stay under the workspace.
    try:
        full_path.relative_to(source_dir.resolve())
    except (ValueError, OSError):
        return None, 0, "source_path_escapes_workspace"
    if not full_path.exists():
        return None, 0, "source_file_absent"
    if not full_path.is_file():
        return None, 0, "source_path_not_a_file"
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, 0, "source_file_unreadable"
    line_count = len(content.splitlines())
    return content, line_count, ""


def _acquire_outcome_observable(
    h_row: dict[str, Any], j_row: dict[str, Any], workspace: Path
) -> dict[str, Any]:
    """Acquire a single outcome observable via deterministic manual extraction.

    The expected evidence form is ``file_path_and_line_range_only_no_snippet_stored``.
    The outcome observable is a directly-readable source-grounded fact: the
    materialized source file exists at the candidate's path, is readable, and
    the line range [start, end] is valid within the file's line count.  No
    snippet is stored.

    Acquisition states:
    - ``acquired``: file exists, readable, line range valid, evidence form
      matches.  outcome_observable_acquired = True.
    - ``unavailable``: file absent/unreadable (source absent or not readable)
      OR file does not contain the observable (line range exceeds file line
      count).  outcome_observable_acquired = False.
    - ``invalid``: observable malformed, not source-grounded, ambiguous, or
      exceeds the whitelisted evidence form.  outcome_observable_acquired =
      False; replacement_needed = True (next deterministic candidate only).
    """
    source_order = int(h_row["source_order_index_private"])
    candidate_order = int(h_row["candidate_order_index_private"])
    relative_path = str(h_row["private_source_file_path"])
    line_range = h_row["private_line_range"]
    start = int(line_range["start"])
    end = int(line_range["end"])

    # Validate the expected evidence form matches the frozen form.
    if j_row.get("expected_evidence_form") != EXPECTED_EVIDENCE_FORM:
        # The annotation-input row's expected evidence form does not match the
        # frozen form.  This is invalid (exceeds whitelisted evidence form).
        return {
            "private_annotation_input_ref": j_row["private_candidate_ref"],
            "source_order_index_private": source_order,
            "candidate_order_index_private": candidate_order,
            "task_eligibility_routing_precondition_only": j_row[
                "task_eligibility_input"
            ],
            "evidence_localization_requirement": j_row[
                "evidence_localization_requirement"
            ],
            "expected_evidence_form": j_row["expected_evidence_form"],
            "outcome_acquisition_precondition": j_row[
                "outcome_acquisition_preconditions"
            ],
            "annotation_input_metadata_reference": (
                "phase9j_annotation_input_row_routing_precondition_only"
                "_not_benchmark_truth"
            ),
            "outcome_acquisition_state": "invalid",
            "outcome_observable_acquired": False,
            "replacement_needed": True,
            "evidence_form_confirmed_source_grounded": False,
            "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
        }

    content, line_count, read_error = _read_materialized_source_file(
        workspace, source_order, relative_path
    )

    if read_error == "source_file_absent" or read_error == "source_path_not_a_file":
        # materialized_source_absent_or_not_readable_is_unavailable
        state = "unavailable"
        acquired = False
        replacement = False
        grounded = False
    elif read_error == "source_file_unreadable" or read_error == "source_path_escapes_workspace":
        # materialized_source_absent_or_not_readable_is_unavailable
        state = "unavailable"
        acquired = False
        replacement = False
        grounded = False
    elif read_error:
        # Unknown read error: unavailable (not acquired from authorized reads)
        state = "unavailable"
        acquired = False
        replacement = False
        grounded = False
    else:
        # File exists and is readable.  Validate the line range.
        if start < 1 or end < start:
            # Malformed line range: invalid (acquired_observable_malformed_is_invalid)
            state = "invalid"
            acquired = False
            replacement = True
            grounded = False
        elif end > line_count:
            # materialized_source_does_not_contain_outcome_observable_is_unavailable
            state = "unavailable"
            acquired = False
            replacement = False
            grounded = False
        else:
            # File exists, readable, line range valid, evidence form matches.
            # The outcome observable is acquired (source-grounded fact).
            state = "acquired"
            acquired = True
            replacement = False
            grounded = True

    return {
        "private_annotation_input_ref": j_row["private_candidate_ref"],
        "source_order_index_private": source_order,
        "candidate_order_index_private": candidate_order,
        "task_eligibility_routing_precondition_only": j_row[
            "task_eligibility_input"
        ],
        "evidence_localization_requirement": j_row[
            "evidence_localization_requirement"
        ],
        "expected_evidence_form": j_row["expected_evidence_form"],
        "outcome_acquisition_precondition": j_row[
            "outcome_acquisition_preconditions"
        ],
        "annotation_input_metadata_reference": (
            "phase9j_annotation_input_row_routing_precondition_only"
            "_not_benchmark_truth"
        ),
        "outcome_acquisition_state": state,
        "outcome_observable_acquired": acquired,
        "replacement_needed": replacement,
        "evidence_form_confirmed_source_grounded": grounded,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
    }


def _validate_outcome_packet(row: Any, index: int) -> list[str]:
    """Validate a single outcome-observable packet against the frozen schema."""
    errors: list[str] = []
    if not isinstance(row, dict):
        errors.append(f"outcome packet {index} not object")
        return errors
    allowed = set(OUTCOME_PACKET_REQUIRED_FIELDS.keys())
    actual = set(str(k) for k in row.keys())
    for extra in sorted(actual - allowed):
        errors.append(f"outcome packet {index} unexpected field: {extra}")
        for token in FORBIDDEN_OUTCOME_PACKET_TOKENS:
            if token in extra.lower():
                errors.append(
                    f"outcome packet {index} forbidden token '{token}' in field: {extra}"
                )
    for field, expected_type in OUTCOME_PACKET_REQUIRED_FIELDS.items():
        if field not in row:
            errors.append(f"outcome packet {index} missing field: {field}")
        elif not isinstance(row[field], expected_type):
            errors.append(f"outcome packet {index} field {field} wrong type")
    if row.get("outcome_acquisition_state") not in OUTCOME_ACQUISITION_STATES:
        errors.append(f"outcome packet {index} invalid outcome_acquisition_state")
    if row.get("outcome_acquisition_state") == "invalid":
        if row.get("replacement_needed") is not True:
            errors.append(
                f"outcome packet {index} invalid state requires replacement_needed True"
            )
    if row.get("outcome_acquisition_state") == "acquired":
        if row.get("outcome_observable_acquired") is not True:
            errors.append(
                f"outcome packet {index} acquired state requires observable acquired True"
            )
        if row.get("evidence_form_confirmed_source_grounded") is not True:
            errors.append(
                f"outcome packet {index} acquired state requires source-grounded True"
            )
    if row.get(
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels"
    ) is not True:
        errors.append(
            f"outcome packet {index} no-scoring/adjudication/evidence_success boundary failed"
        )
    return errors


def _execute_frozen_route(
    h_rows: list[dict[str, Any]],
    j_rows: list[dict[str, Any]],
    workspace: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Execute the single frozen route over the deterministic candidate order.

    Candidates are processed in ``candidate_order_index_private`` order
    (ascending).  Each Phase 9H row is matched to its Phase 9J annotation-input
    row by ``candidate_order_index_private``.  There is exactly ONE route; no
    fallback, no retry, no trying-routes-until-one-works.
    """
    packets: list[dict[str, Any]] = []
    errors: list[str] = []
    # Deterministic ordering: sort by candidate_order_index_private.
    h_sorted = sorted(h_rows, key=lambda r: int(r["candidate_order_index_private"]))
    j_by_order = {
        int(r["candidate_order_index_private"]): r for r in j_rows
    }
    for h_row in h_sorted:
        cand_idx = int(h_row["candidate_order_index_private"])
        j_row = j_by_order.get(cand_idx)
        if j_row is None:
            # Deterministic ordering ambiguity: a 9H row has no matching 9J row.
            # This is an ordering/input ambiguity detected BEFORE outcome
            # inspection.  Block and require a separate no-execution protocol
            # freeze (no in-place tie-breaker).
            errors.append(
                f"deterministic_ordering_ambiguity: phase9h candidate {cand_idx} "
                f"has no matching phase9j annotation-input row"
            )
            continue
        # Verify the candidate references match across 9H and 9J.
        h_cand_id = h_row.get("private_candidate_id", "")
        j_cand_ref = j_row.get("private_candidate_ref", "")
        if h_cand_id != j_cand_ref:
            errors.append(
                f"deterministic_ordering_ambiguity: phase9h candidate {cand_idx} "
                f"reference mismatch"
            )
            continue
        packet = _acquire_outcome_observable(h_row, j_row, workspace)
        packets.append(packet)
        errors.extend(_validate_outcome_packet(packet, cand_idx))
    return packets, errors


def _compute_outcome_aggregate(packets: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate outcome-acquisition totals (private, under runs/ only)."""
    attempted = len(packets)
    acquired = sum(
        1 for p in packets if p.get("outcome_acquisition_state") == "acquired"
    )
    unavailable = sum(
        1 for p in packets if p.get("outcome_acquisition_state") == "unavailable"
    )
    invalid = sum(
        1 for p in packets if p.get("outcome_acquisition_state") == "invalid"
    )
    replacement_needed = sum(
        1 for p in packets if p.get("replacement_needed") is True
    )
    distinct_sources = len(
        {p["source_order_index_private"] for p in packets}
    ) if packets else 0
    return {
        "outcome_packets_total": attempted,
        "acquired_valid_total": acquired,
        "unavailable_total": unavailable,
        "invalid_rejected_total": invalid,
        "replacement_needed_total": replacement_needed,
        "distinct_sources_with_outcome_packets": distinct_sources,
        "hard_cap_respected": attempted <= HARD_INVENTORY_CAP,
        "per_source_cap_respected": all(
            c <= PER_SOURCE_CAP
            for c in (
                {}
                if not packets
                else (
                    lambda d: d
                )({s: sum(1 for p in packets if p["source_order_index_private"] == s) for s in {p["source_order_index_private"] for p in packets}}).values()
            )
        ),
        "target_bucket_met": TARGET_INVENTORY_MIN <= attempted <= TARGET_INVENTORY_MAX,
        "diversity_minimum_met": distinct_sources >= MIN_DISTINCT_SOURCES,
    }


def _build_private_manifest(
    outcome_packets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the private outcome-acquisition manifest (under ignored runs/ only)."""
    aggregate = _compute_outcome_aggregate(outcome_packets)
    by_source: dict[int, int] = {}
    for packet in outcome_packets:
        idx = packet["source_order_index_private"]
        by_source[idx] = by_source.get(idx, 0) + 1
    source_summaries: list[dict[str, Any]] = []
    for source_idx, count in sorted(by_source.items()):
        source_summaries.append({
            "source_order_index_private": source_idx,
            "private_outcome_packets": count,
        })
    return {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication": True,
        "frozen_route_executed_single_fixed_route_no_fallback_no_retry": True,
        "outcome_acquisition_packets_private": outcome_packets,
        "source_private_summaries": source_summaries,
        "aggregate_private_totals": aggregate,
        "annotation_input_metadata_remains_routing_precondition_not_benchmark_truth": True,
        "phase9j_rows_used_as_benchmark_truth": False,
        "phase9l_outcome_packets_read": False,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
        "provider_or_llm_calls_executed": False,
        "model_fitting_executed": False,
        "network_fetch_or_clone_or_source_refresh_executed": False,
    }


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def _determine_status(
    attempted: int,
    acquired: int,
    unavailable: int,
    invalid: int,
    gate_ok: bool,
    all_confirmations: bool,
    caps_ok: bool,
    schema_ok: bool,
    ordering_ambiguity: bool,
) -> str:
    if ordering_ambiguity:
        return STATUS_ORDER_AMBIGUITY
    if not gate_ok:
        return STATUS_GATE_MISSING
    if not all_confirmations or not caps_ok or not schema_ok:
        return STATUS_REPAIR
    if attempted <= 0:
        return STATUS_REPAIR
    if acquired > 0:
        return STATUS_EXECUTED_VALID
    if invalid > 0 and unavailable > 0:
        return STATUS_EXECUTED_ZERO_INVALID_AND_UNAVAILABLE
    if invalid > 0:
        return STATUS_EXECUTED_ZERO_INVALID
    if unavailable > 0:
        return STATUS_EXECUTED_ZERO_UNAVAILABLE
    return STATUS_REPAIR


def build_public_report(
    outcome_aggregate: dict[str, Any],
    phase9m_gate_ok: bool,
    confirmations: dict[str, bool],
    private_phase9h_sources_read: bool,
    private_phase9j_annotation_input_read: bool,
    outcome_packet_errors: list[str] | None = None,
    ordering_ambiguity: bool = False,
) -> dict[str, Any]:
    """Build the aggregate-only public Phase 9N report."""
    attempted = int(outcome_aggregate.get("outcome_packets_total", 0))
    acquired = int(outcome_aggregate.get("acquired_valid_total", 0))
    unavailable = int(outcome_aggregate.get("unavailable_total", 0))
    invalid = int(outcome_aggregate.get("invalid_rejected_total", 0))
    replacement_needed = int(outcome_aggregate.get("replacement_needed_total", 0))
    distinct_sources = int(
        outcome_aggregate.get("distinct_sources_with_outcome_packets", 0)
    )
    caps_ok = (
        outcome_aggregate.get("hard_cap_respected") is True
        and outcome_aggregate.get("per_source_cap_respected") is True
    )
    schema_ok = not outcome_packet_errors
    all_confirmations = all(confirmations.values()) and len(confirmations) == 16

    status = _determine_status(
        attempted, acquired, unavailable, invalid,
        phase9m_gate_ok, all_confirmations, caps_ok, schema_ok,
        ordering_ambiguity,
    )

    route_executed = status in EXECUTED_STATUSES and attempted > 0
    acquired_nonzero = acquired > 0
    # Phase 9O gate: scoring protocol may be considered only if acquired_valid
    # bucket is nonzero; scoring/adjudication remain false.
    phase9o_scoring_may_be_considered = acquired_nonzero and route_executed

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9m_gate_references": {
            "phase9m_commit": PHASE9M_COMMIT,
            "phase9m_ci_run": PHASE9M_CI_RUN,
            "phase9m_ci_success": True,
            "phase9m_status": PHASE9M_STATUS,
            "phase9m_protocol_freeze": True,
            "phase9m_outcome_observable_acquisition_route_frozen": True,
            "phase9m_did_not_execute_route_or_acquire_outcomes_or_score_or_adjudicate": True,
            "phase9m_not_proof_outcome_or_scoring_or_evidence_success_works": True,
            "phase9m_gate_required_before_phase9n": True,
            "phase9m_public_report_validated": phase9m_gate_ok,
        },
        "phase9l_gate_references": {
            "phase9l_commit": PHASE9L_COMMIT,
            "phase9l_ci_run": PHASE9L_CI_RUN,
            "phase9l_ci_success": True,
            "phase9l_status": PHASE9L_STATUS,
            "phase9l_outcome_acquisition_protocol_frozen": True,
            "phase9l_all_unavailable_only_under_phase9k_missing_outcome_rule": True,
            "phase9l_outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication": True,
            "phase9l_no_scoring_denominator_exists": True,
            "phase9l_not_proof_outcome_or_scoring_or_evidence_success_works": True,
            "phase9l_gate_required_before_phase9m": True,
        },
        "phase9k_gate_references": {
            "phase9k_commit": PHASE9K_COMMIT,
            "phase9k_ci_run": PHASE9K_CI_RUN,
            "phase9k_ci_success": True,
            "phase9k_status": PHASE9K_STATUS,
            "phase9k_protocol_freeze": True,
            "phase9k_outcome_acquisition_protocol_frozen": True,
            "phase9k_not_proof_outcome_or_scoring_or_evidence_success_works": True,
            "phase9k_did_not_acquire_outcomes_or_score_or_adjudicate_or_generate_gold_rows": True,
            "phase9k_gate_required_before_phase9m": True,
        },
        "inherited_provenance_bucketed": {
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_carried_as_inherited_provenance_only": True,
            "phase9g_status": PHASE9G_STATUS,
            "phase9g_carried_as_inherited_provenance_only": True,
            "phase9h_status": PHASE9H_STATUS,
            "phase9h_carried_as_inherited_provenance_only": True,
            "phase9i_status": PHASE9I_STATUS,
            "phase9i_carried_as_inherited_provenance_only": True,
            "phase9j_status": PHASE9J_STATUS,
            "phase9j_carried_as_inherited_provenance_only": True,
            "exact_remote_commit_ci_values_intentionally_not_published": True,
        },
        "confirmation_summary": {
            "phase9m_commit_confirmed": confirmations.get("phase9m_commit_confirmed") is True,
            "phase9m_ci_confirmed": confirmations.get("phase9m_ci_confirmed") is True,
            "phase9m_status_confirmed": confirmations.get("phase9m_status_confirmed") is True,
            "phase9m_protocol_freeze_confirmed": confirmations.get("phase9m_protocol_freeze_confirmed") is True,
            "read_phase9h_private_materialized_sources_confirmed": confirmations.get("read_phase9h_private_materialized_sources_confirmed") is True,
            "read_phase9j_private_annotation_input_rows_confirmed": confirmations.get("read_phase9j_private_annotation_input_rows_confirmed") is True,
            "ignored_runs_workspace_confirmed": confirmations.get("ignored_runs_workspace_confirmed") is True,
            "private_output_only_confirmed": confirmations.get("private_output_only_confirmed") is True,
            "aggregate_public_report_only_confirmed": confirmations.get("aggregate_public_report_only_confirmed") is True,
            "no_scoring_or_evidence_success_until_separate_boundary_confirmed": confirmations.get("no_scoring_or_evidence_success_until_separate_boundary_confirmed") is True,
            "no_provider_llm_model_default_runtime_product_change_confirmed": confirmations.get("no_provider_llm_model_default_runtime_product_change_confirmed") is True,
            "no_network_fetch_clone_source_refresh_confirmed": confirmations.get("no_network_fetch_clone_source_refresh_confirmed") is True,
            "phase9j_rows_not_benchmark_truth_confirmed": confirmations.get("phase9j_rows_not_benchmark_truth_confirmed") is True,
            "phase9l_outcome_packets_not_read_confirmed": confirmations.get("phase9l_outcome_packets_not_read_confirmed") is True,
            "single_fixed_route_no_fallback_no_retry_confirmed": confirmations.get("single_fixed_route_no_fallback_no_retry_confirmed") is True,
            "deterministic_manual_extraction_only_confirmed": confirmations.get("deterministic_manual_extraction_only_confirmed") is True,
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
        },
        "execution_booleans": {
            "route_executed": route_executed,
            "private_phase9h_materialized_sources_read": private_phase9h_sources_read and route_executed,
            "private_phase9j_annotation_input_rows_read": private_phase9j_annotation_input_read and route_executed,
            "phase9j_rows_used_as_benchmark_truth": False,
            "phase9l_outcome_packets_read": False,
            "provider_or_llm_calls": False,
            "model_fitting": False,
            "scoring_executed": False,
            "adjudication_executed": False,
            "gold_labels_generated": False,
            "benchmark_labels_generated": False,
            "evidence_success_evaluated": False,
            "correctness_evaluated": False,
            "precision_recall_computed": False,
            "result_labels_generated": False,
            "runtime_default_or_product_changes": False,
            "network_fetch_or_clone_or_source_refresh_executed": False,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "annotation_truth_generated": False,
        },
        "availability_buckets": {
            "publication_level": "aggregate_bucketed_availability_only",
            "attempted_bucket": _bucket_availability(attempted),
            "acquired_valid_bucket": _bucket_availability(acquired),
            "unavailable_bucket": _bucket_availability(unavailable),
            "invalid_rejected_bucket": _bucket_availability(invalid),
            "replacement_needed_bucket": _bucket_availability(replacement_needed),
            "distinct_sources_bucket": _bucket_availability(distinct_sources),
            "outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication": True,
            "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
            "annotation_input_metadata_remains_routing_precondition_not_benchmark_truth": True,
            "private_output_under_ignored_runs_only": True,
            "outcome_packets_generated_under_ignored_runs_only": route_executed,
            "frozen_route_vocabulary_matches_phase9m": True,
            "inherited_phase9h_aggregate_caps_respected": caps_ok,
            "outcome_packet_schema_validation_passed": schema_ok,
            "inherited_phase9h_aggregate_caps": {
                "target_inventory_bucket": "bucket_48_to_72",
                "hard_cap_bucket": "bucket_up_to_96",
                "per_source_cap_bucket": "bucket_up_to_8",
                "minimum_distinct_sources_bucket": "bucket_at_least_8",
            },
        },
        "phase9o_gate": {
            "scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero": phase9o_scoring_may_be_considered,
            "scoring_executed": False,
            "adjudication_executed": False,
            "no_scoring_denominator_exists_in_phase9n": True,
            "phase9o_requires_separate_frozen_boundary": True,
        },
        "frozen_route_attestation": {
            "publication_level": ROUTE_PUBLICATION_LEVEL,
            "route_form": ROUTE_FORM,
            "authorized_private_inputs": list(AUTHORIZED_PRIVATE_INPUTS),
            "authorized_derived_artifacts": list(AUTHORIZED_DERIVED_ARTIFACTS),
            "extraction_procedure": list(EXTRACTION_PROCEDURE),
            "observable_definition": list(OBSERVABLE_DEFINITION),
            "invalid_criteria": list(INVALID_CRITERIA),
            "unavailable_criteria": list(UNAVAILABLE_CRITERIA),
            "replacement_rule_if_invalid": list(REPLACEMENT_RULE_IF_INVALID),
            "stop_rule": list(STOP_RULE),
            "route_order_and_fallback_rule": list(ROUTE_ORDER_AND_FALLBACK_RULE),
            "no_trying_routes_until_one_works_unless_pre_frozen": True,
            "no_llm_no_provider_frozen": True,
            "single_fixed_route_no_fallback_no_retry": True,
            "deterministic_manual_extraction_only": True,
        },
        "privacy_summary": {
            "public_output_aggregate_only": True,
            "private_outputs_under_ignored_runs_only": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PRIVACY_FALSE_KEYS},
        },
        "no_claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "forbidden_execution_boundary": {
            key: False for key in NO_EXECUTION_FALSE_KEYS
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "public_artifact_privacy_audit_expected": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_does_not_read_phase9l_outcome_packets": True,
        },
        "conservative_recommendation": (
            "phase9n_executes_frozen_route_availability_only"
            "_acquisition_state_not_scoring_not_adjudication_not_evidence_success"
            "_future_scoring_and_adjudication_require_separate_frozen_boundary"
            "_no_method_product_claim"
        ),
    }


# ---------------------------------------------------------------------------
# Strict allowed-key schema + privacy scan + validation
# ---------------------------------------------------------------------------

def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


ALLOWED_REPORT_KEYS: dict[str, Any] = {
    "schema_version": None,
    "phase": None,
    "status": None,
    "phase9m_gate_references": {
        "phase9m_commit": None,
        "phase9m_ci_run": None,
        "phase9m_ci_success": None,
        "phase9m_status": None,
        "phase9m_protocol_freeze": None,
        "phase9m_outcome_observable_acquisition_route_frozen": None,
        "phase9m_did_not_execute_route_or_acquire_outcomes_or_score_or_adjudicate": None,
        "phase9m_not_proof_outcome_or_scoring_or_evidence_success_works": None,
        "phase9m_gate_required_before_phase9n": None,
        "phase9m_public_report_validated": None,
    },
    "phase9l_gate_references": {
        "phase9l_commit": None,
        "phase9l_ci_run": None,
        "phase9l_ci_success": None,
        "phase9l_status": None,
        "phase9l_outcome_acquisition_protocol_frozen": None,
        "phase9l_all_unavailable_only_under_phase9k_missing_outcome_rule": None,
        "phase9l_outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication": None,
        "phase9l_no_scoring_denominator_exists": None,
        "phase9l_not_proof_outcome_or_scoring_or_evidence_success_works": None,
        "phase9l_gate_required_before_phase9m": None,
    },
    "phase9k_gate_references": {
        "phase9k_commit": None,
        "phase9k_ci_run": None,
        "phase9k_ci_success": None,
        "phase9k_status": None,
        "phase9k_protocol_freeze": None,
        "phase9k_outcome_acquisition_protocol_frozen": None,
        "phase9k_not_proof_outcome_or_scoring_or_evidence_success_works": None,
        "phase9k_did_not_acquire_outcomes_or_score_or_adjudicate_or_generate_gold_rows": None,
        "phase9k_gate_required_before_phase9m": None,
    },
    "inherited_provenance_bucketed": {
        "phase9f_status": None,
        "phase9f_carried_as_inherited_provenance_only": None,
        "phase9g_status": None,
        "phase9g_carried_as_inherited_provenance_only": None,
        "phase9h_status": None,
        "phase9h_carried_as_inherited_provenance_only": None,
        "phase9i_status": None,
        "phase9i_carried_as_inherited_provenance_only": None,
        "phase9j_status": None,
        "phase9j_carried_as_inherited_provenance_only": None,
        "exact_remote_commit_ci_values_intentionally_not_published": None,
    },
    "confirmation_summary": {
        "phase9m_commit_confirmed": None,
        "phase9m_ci_confirmed": None,
        "phase9m_status_confirmed": None,
        "phase9m_protocol_freeze_confirmed": None,
        "read_phase9h_private_materialized_sources_confirmed": None,
        "read_phase9j_private_annotation_input_rows_confirmed": None,
        "ignored_runs_workspace_confirmed": None,
        "private_output_only_confirmed": None,
        "aggregate_public_report_only_confirmed": None,
        "no_scoring_or_evidence_success_until_separate_boundary_confirmed": None,
        "no_provider_llm_model_default_runtime_product_change_confirmed": None,
        "no_network_fetch_clone_source_refresh_confirmed": None,
        "phase9j_rows_not_benchmark_truth_confirmed": None,
        "phase9l_outcome_packets_not_read_confirmed": None,
        "single_fixed_route_no_fallback_no_retry_confirmed": None,
        "deterministic_manual_extraction_only_confirmed": None,
        "all_required_confirmations_present": None,
        "dry_self_test_and_report_validation_read_private_runs": None,
        "dry_self_test_and_report_validation_fetch_or_clone": None,
    },
    "execution_booleans": {
        "route_executed": None,
        "private_phase9h_materialized_sources_read": None,
        "private_phase9j_annotation_input_rows_read": None,
        "phase9j_rows_used_as_benchmark_truth": None,
        "phase9l_outcome_packets_read": None,
        "provider_or_llm_calls": None,
        "model_fitting": None,
        "scoring_executed": None,
        "adjudication_executed": None,
        "gold_labels_generated": None,
        "benchmark_labels_generated": None,
        "evidence_success_evaluated": None,
        "correctness_evaluated": None,
        "precision_recall_computed": None,
        "result_labels_generated": None,
        "runtime_default_or_product_changes": None,
        "network_fetch_or_clone_or_source_refresh_executed": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "annotation_truth_generated": None,
    },
    "availability_buckets": {
        "publication_level": None,
        "attempted_bucket": None,
        "acquired_valid_bucket": None,
        "unavailable_bucket": None,
        "invalid_rejected_bucket": None,
        "replacement_needed_bucket": None,
        "distinct_sources_bucket": None,
        "outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication": None,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": None,
        "annotation_input_metadata_remains_routing_precondition_not_benchmark_truth": None,
        "private_output_under_ignored_runs_only": None,
        "outcome_packets_generated_under_ignored_runs_only": None,
        "frozen_route_vocabulary_matches_phase9m": None,
        "inherited_phase9h_aggregate_caps_respected": None,
        "outcome_packet_schema_validation_passed": None,
        "inherited_phase9h_aggregate_caps": {
            "target_inventory_bucket": None,
            "hard_cap_bucket": None,
            "per_source_cap_bucket": None,
            "minimum_distinct_sources_bucket": None,
        },
    },
    "phase9o_gate": {
        "scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero": None,
        "scoring_executed": None,
        "adjudication_executed": None,
        "no_scoring_denominator_exists_in_phase9n": None,
        "phase9o_requires_separate_frozen_boundary": None,
    },
    "frozen_route_attestation": {
        "publication_level": None,
        "route_form": None,
        "authorized_private_inputs": None,
        "authorized_derived_artifacts": None,
        "extraction_procedure": None,
        "observable_definition": None,
        "invalid_criteria": None,
        "unavailable_criteria": None,
        "replacement_rule_if_invalid": None,
        "stop_rule": None,
        "route_order_and_fallback_rule": None,
        "no_trying_routes_until_one_works_unless_pre_frozen": None,
        "no_llm_no_provider_frozen": None,
        "single_fixed_route_no_fallback_no_retry": None,
        "deterministic_manual_extraction_only": None,
    },
    "privacy_summary": {
        "public_output_aggregate_only": None,
        "private_outputs_under_ignored_runs_only": None,
        "runs_remains_ignored": None,
        **{key: None for key in PRIVACY_FALSE_KEYS},
    },
    "no_claim_boundary": {key: None for key in CLAIM_BOUNDARY_FALSE_KEYS},
    "forbidden_execution_boundary": {key: None for key in NO_EXECUTION_FALSE_KEYS},
    "validation_summary": {
        "route_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "public_artifact_privacy_audit_expected": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_does_not_read_phase9l_outcome_packets": None,
    },
    "conservative_recommendation": None,
}


def _allowed_leaf_paths() -> set[str]:
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


def _check_closed_list(report_list: Any, expected: tuple[str, ...], section: str, key: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(report_list, list):
        errors.append(f"{section}.{key} missing")
        return errors
    expected_set = set(expected)
    present_set = set(report_list)
    missing = expected_set - present_set
    if missing:
        errors.append(f"{section}.{key} missing members: " + ", ".join(sorted(missing)))
    extra = present_set - expected_set
    if extra:
        errors.append(f"{section}.{key} has extra members: " + ", ".join(sorted(extra)))
    return errors


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
    if not isinstance(value, bool) and any(
        word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS
    ):
        errors.append(f"forbidden public field word at {path}")
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
            if isinstance(child_value, str) and LIST_VALUE_PRIVATE_TOKEN_RE.search(child_value):
                errors.append(f"private-shaped list value at {child_path}")
    elif isinstance(value, str):
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
        if PLACEHOLDER_RE.search(value):
            errors.append(f"placeholder wording at {path}")
        if FORBIDDEN_STATUS_WORDING_RE.search(value):
            errors.append(f"forbidden status wording at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") not in ALLOWED_STATUSES:
        errors.append("unknown status")

    # Phase 9M gate references (whitelisted public gate refs).
    gate9m = report.get("phase9m_gate_references", {})
    if gate9m.get("phase9m_commit") != PHASE9M_COMMIT:
        errors.append("Phase 9M commit gate reference drift")
    if gate9m.get("phase9m_ci_run") != PHASE9M_CI_RUN:
        errors.append("Phase 9M CI run gate reference drift")
    if gate9m.get("phase9m_ci_success") is not True:
        errors.append("Phase 9M CI success gate missing")
    if gate9m.get("phase9m_status") != PHASE9M_STATUS:
        errors.append("Phase 9M status gate reference drift")
    if gate9m.get("phase9m_protocol_freeze") is not True:
        errors.append("Phase 9M protocol freeze gate missing")
    if gate9m.get("phase9m_outcome_observable_acquisition_route_frozen") is not True:
        errors.append("Phase 9M route frozen boundary missing")
    if gate9m.get("phase9m_did_not_execute_route_or_acquire_outcomes_or_score_or_adjudicate") is not True:
        errors.append("Phase 9M no-execution boundary missing")
    if gate9m.get("phase9m_not_proof_outcome_or_scoring_or_evidence_success_works") is not True:
        errors.append("Phase 9M not-proof boundary missing")
    if gate9m.get("phase9m_gate_required_before_phase9n") is not True:
        errors.append("Phase 9M gate-required boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        if gate9m.get("phase9m_public_report_validated") is not True:
            errors.append("Phase 9M public report validated gate missing")

    # Phase 9L gate references (secondary, from 9M).
    gate9l = report.get("phase9l_gate_references", {})
    if gate9l.get("phase9l_commit") != PHASE9L_COMMIT:
        errors.append("Phase 9L commit gate reference drift")
    if gate9l.get("phase9l_ci_run") != PHASE9L_CI_RUN:
        errors.append("Phase 9L CI run gate reference drift")
    if gate9l.get("phase9l_ci_success") is not True:
        errors.append("Phase 9L CI success gate missing")
    if gate9l.get("phase9l_status") != PHASE9L_STATUS:
        errors.append("Phase 9L status gate reference drift")

    # Phase 9K gate references (secondary, from 9M).
    gate9k = report.get("phase9k_gate_references", {})
    if gate9k.get("phase9k_commit") != PHASE9K_COMMIT:
        errors.append("Phase 9K commit gate reference drift")
    if gate9k.get("phase9k_ci_run") != PHASE9K_CI_RUN:
        errors.append("Phase 9K CI run gate reference drift")
    if gate9k.get("phase9k_ci_success") is not True:
        errors.append("Phase 9K CI success gate missing")
    if gate9k.get("phase9k_status") != PHASE9K_STATUS:
        errors.append("Phase 9K status gate reference drift")

    # Inherited provenance (bucketed only).
    prov = report.get("inherited_provenance_bucketed", {})
    if prov.get("phase9f_status") != PHASE9F_STATUS:
        errors.append("Phase 9F inherited status drift")
    if prov.get("phase9g_status") != PHASE9G_STATUS:
        errors.append("Phase 9G inherited status drift")
    if prov.get("phase9h_status") != PHASE9H_STATUS:
        errors.append("Phase 9H inherited status drift")
    if prov.get("phase9i_status") != PHASE9I_STATUS:
        errors.append("Phase 9I inherited status drift")
    if prov.get("phase9j_status") != PHASE9J_STATUS:
        errors.append("Phase 9J inherited status drift")

    # Execution booleans.
    execs = report.get("execution_booleans", {})
    if execs.get("route_executed") is not True:
        if report.get("status") in EXECUTED_STATUSES:
            errors.append("executed status requires route_executed True")
    for key in (
        "phase9j_rows_used_as_benchmark_truth",
        "phase9l_outcome_packets_read",
        "provider_or_llm_calls",
        "model_fitting",
        "scoring_executed",
        "adjudication_executed",
        "gold_labels_generated",
        "benchmark_labels_generated",
        "evidence_success_evaluated",
        "correctness_evaluated",
        "precision_recall_computed",
        "result_labels_generated",
        "runtime_default_or_product_changes",
        "network_fetch_or_clone_or_source_refresh_executed",
        "public_fetch_clone_executed",
        "source_materialization_executed",
        "annotation_truth_generated",
    ):
        if execs.get(key) is not False:
            errors.append(f"execution boundary failed: {key}")

    # Availability buckets.
    buckets = report.get("availability_buckets", {})
    for key in (
        "attempted_bucket",
        "acquired_valid_bucket",
        "unavailable_bucket",
        "invalid_rejected_bucket",
        "replacement_needed_bucket",
        "distinct_sources_bucket",
    ):
        val = buckets.get(key)
        if val not in ("bucket_zero", "bucket_nonzero_redacted"):
            errors.append(f"availability bucket must be bucket_zero or bucket_nonzero_redacted: {key}")

    # Status / bucket consistency.
    status = report.get("status")
    if status == STATUS_EXECUTED_VALID:
        if buckets.get("acquired_valid_bucket") != "bucket_nonzero_redacted":
            errors.append("executed_valid requires acquired_valid_bucket nonzero")
        if buckets.get("attempted_bucket") != "bucket_nonzero_redacted":
            errors.append("executed_valid requires attempted_bucket nonzero")
        if buckets.get("unavailable_bucket") != "bucket_zero":
            errors.append("executed_valid requires unavailable_bucket zero")
        if buckets.get("invalid_rejected_bucket") != "bucket_zero":
            errors.append("executed_valid requires invalid_rejected_bucket zero")
        if buckets.get("replacement_needed_bucket") != "bucket_zero":
            errors.append("executed_valid requires replacement_needed_bucket zero")
    elif status == STATUS_EXECUTED_ZERO_UNAVAILABLE:
        if buckets.get("acquired_valid_bucket") != "bucket_zero":
            errors.append("executed_zero_unavailable requires acquired_valid_bucket zero")
        if buckets.get("unavailable_bucket") != "bucket_nonzero_redacted":
            errors.append("executed_zero_unavailable requires unavailable_bucket nonzero")
        if buckets.get("invalid_rejected_bucket") != "bucket_zero":
            errors.append("executed_zero_unavailable requires invalid_rejected_bucket zero")
        if buckets.get("replacement_needed_bucket") != "bucket_zero":
            errors.append("executed_zero_unavailable requires replacement_needed_bucket zero")
    elif status == STATUS_EXECUTED_ZERO_INVALID:
        if buckets.get("acquired_valid_bucket") != "bucket_zero":
            errors.append("executed_zero_invalid requires acquired_valid_bucket zero")
        if buckets.get("invalid_rejected_bucket") != "bucket_nonzero_redacted":
            errors.append("executed_zero_invalid requires invalid_rejected_bucket nonzero")
        if buckets.get("unavailable_bucket") != "bucket_zero":
            errors.append("executed_zero_invalid requires unavailable_bucket zero")
    elif status == STATUS_EXECUTED_ZERO_INVALID_AND_UNAVAILABLE:
        if buckets.get("acquired_valid_bucket") != "bucket_zero":
            errors.append("executed_zero_invalid_and_unavailable requires acquired_valid_bucket zero")
        if buckets.get("invalid_rejected_bucket") != "bucket_nonzero_redacted":
            errors.append("executed_zero_invalid_and_unavailable requires invalid_rejected_bucket nonzero")
        if buckets.get("unavailable_bucket") != "bucket_nonzero_redacted":
            errors.append("executed_zero_invalid_and_unavailable requires unavailable_bucket nonzero")

    # Phase 9O gate.
    gate9o = report.get("phase9o_gate", {})
    if gate9o.get("scoring_executed") is not False:
        errors.append("phase9o scoring_executed must be false")
    if gate9o.get("adjudication_executed") is not False:
        errors.append("phase9o adjudication_executed must be false")
    if gate9o.get("no_scoring_denominator_exists_in_phase9n") is not True:
        errors.append("phase9o no_scoring_denominator boundary missing")
    if gate9o.get("phase9o_requires_separate_frozen_boundary") is not True:
        errors.append("phase9o separate-boundary boundary missing")
    # Phase 9O gate consistency: the scoring-protocol gate must be True only
    # when BOTH the acquired_valid bucket is nonzero AND the route executed
    # with nonzero valid outcomes (STATUS_EXECUTED_VALID).  Reject both wrong
    # directions: acquired bucket zero but gate true, and nonzero
    # valid/executed status but gate false.  scoring_executed,
    # adjudication_executed, and no_scoring_denominator remain invariant
    # (checked above) and are NOT part of this gate-consistency tie.
    gate9o_may_consider = gate9o.get(
        "scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero"
    )
    acquired_bucket_val = buckets.get("acquired_valid_bucket")
    expected_gate9o_may_consider = (
        status == STATUS_EXECUTED_VALID
        and acquired_bucket_val == "bucket_nonzero_redacted"
    )
    if gate9o_may_consider is not expected_gate9o_may_consider:
        errors.append(
            "phase9o scoring gate inconsistent with status/acquired_valid_bucket"
        )

    # Frozen route attestation (closed-list set-equality vs Phase 9M).
    route = report.get("frozen_route_attestation", {})
    if route.get("publication_level") != ROUTE_PUBLICATION_LEVEL:
        errors.append("route publication level drift")
    if route.get("route_form") != ROUTE_FORM:
        errors.append("route form drift")
    for key, expected in CLOSED_ROUTE_LISTS:
        errors.extend(_check_closed_list(route.get(key), expected, "frozen_route_attestation", key))
    if route.get("no_trying_routes_until_one_works_unless_pre_frozen") is not True:
        errors.append("route no-trying-routes boundary missing")
    if route.get("no_llm_no_provider_frozen") is not True:
        errors.append("route no-llm-no-provider boundary missing")
    if route.get("single_fixed_route_no_fallback_no_retry") is not True:
        errors.append("route single-fixed-route boundary missing")
    if route.get("deterministic_manual_extraction_only") is not True:
        errors.append("route deterministic-manual-extraction boundary missing")

    # Privacy summary.
    privacy = report.get("privacy_summary", {})
    for key in (
        "public_output_aggregate_only",
        "private_outputs_under_ignored_runs_only",
        "runs_remains_ignored",
    ):
        if privacy.get(key) is not True:
            errors.append(f"privacy summary missing: {key}")
    for key in PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"public privacy boundary failed: {key}")

    # Validation summary.
    validation = report.get("validation_summary", {})
    for key in (
        "route_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "public_artifact_privacy_audit_expected",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_phase9l_outcome_packets",
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

    # No-claim boundary.
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("no_claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    # Forbidden execution boundary.
    for key in NO_EXECUTION_FALSE_KEYS:
        if report.get("forbidden_execution_boundary", {}).get(key) is not False:
            errors.append(f"forbidden execution boundary failed: {key}")

    # Conservative recommendation.
    if report.get("conservative_recommendation") != (
        "phase9n_executes_frozen_route_availability_only"
        "_acquisition_state_not_scoring_not_adjudication_not_evidence_success"
        "_future_scoring_and_adjudication_require_separate_frozen_boundary"
        "_no_method_product_claim"
    ):
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--validate-report``."""
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
        return False, "report path is not under the Phase 9N public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------

def _all_confirmations_dict(
    confirm_phase9m_commit: str | None,
    confirm_phase9m_ci: str | None,
    confirm_phase9m_status: str | None,
    confirm_phase9m_protocol_freeze: bool,
    confirm_read_phase9h_private_materialized_sources: bool,
    confirm_read_phase9j_private_annotation_input_rows: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_no_scoring_or_evidence_success_until_separate_boundary: bool,
    confirm_no_provider_llm_model_default_runtime_product_change: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
    confirm_phase9j_rows_not_benchmark_truth: bool,
    confirm_phase9l_outcome_packets_not_read: bool,
    confirm_single_fixed_route_no_fallback_no_retry: bool,
    confirm_deterministic_manual_extraction_only: bool,
) -> dict[str, bool]:
    return {
        "phase9m_commit_confirmed": confirm_phase9m_commit == PHASE9M_COMMIT,
        "phase9m_ci_confirmed": confirm_phase9m_ci == PHASE9M_CI_RUN,
        "phase9m_status_confirmed": confirm_phase9m_status == PHASE9M_STATUS,
        "phase9m_protocol_freeze_confirmed": confirm_phase9m_protocol_freeze is True,
        "read_phase9h_private_materialized_sources_confirmed": confirm_read_phase9h_private_materialized_sources is True,
        "read_phase9j_private_annotation_input_rows_confirmed": confirm_read_phase9j_private_annotation_input_rows is True,
        "ignored_runs_workspace_confirmed": confirm_ignored_runs_workspace is True,
        "private_output_only_confirmed": confirm_private_output_only is True,
        "aggregate_public_report_only_confirmed": confirm_aggregate_public_report_only is True,
        "no_scoring_or_evidence_success_until_separate_boundary_confirmed": confirm_no_scoring_or_evidence_success_until_separate_boundary is True,
        "no_provider_llm_model_default_runtime_product_change_confirmed": confirm_no_provider_llm_model_default_runtime_product_change is True,
        "no_network_fetch_clone_source_refresh_confirmed": confirm_no_network_fetch_clone_source_refresh is True,
        "phase9j_rows_not_benchmark_truth_confirmed": confirm_phase9j_rows_not_benchmark_truth is True,
        "phase9l_outcome_packets_not_read_confirmed": confirm_phase9l_outcome_packets_not_read is True,
        "single_fixed_route_no_fallback_no_retry_confirmed": confirm_single_fixed_route_no_fallback_no_retry is True,
        "deterministic_manual_extraction_only_confirmed": confirm_deterministic_manual_extraction_only is True,
    }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _empty_aggregate() -> dict[str, Any]:
    return {
        "outcome_packets_total": 0,
        "acquired_valid_total": 0,
        "unavailable_total": 0,
        "invalid_rejected_total": 0,
        "replacement_needed_total": 0,
        "distinct_sources_with_outcome_packets": 0,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
    }


def execute_phase9n(
    private_run_dir: Path,
    public_report: Path,
    confirm_phase9m_commit: str | None,
    confirm_phase9m_ci: str | None,
    confirm_phase9m_status: str | None,
    confirm_phase9m_protocol_freeze: bool,
    confirm_read_phase9h_private_materialized_sources: bool,
    confirm_read_phase9j_private_annotation_input_rows: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_no_scoring_or_evidence_success_until_separate_boundary: bool,
    confirm_no_provider_llm_model_default_runtime_product_change: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
    confirm_phase9j_rows_not_benchmark_truth: bool,
    confirm_phase9l_outcome_packets_not_read: bool,
    confirm_single_fixed_route_no_fallback_no_retry: bool,
    confirm_deterministic_manual_extraction_only: bool,
) -> dict[str, Any]:
    confirmations = _all_confirmations_dict(
        confirm_phase9m_commit, confirm_phase9m_ci, confirm_phase9m_status,
        confirm_phase9m_protocol_freeze,
        confirm_read_phase9h_private_materialized_sources,
        confirm_read_phase9j_private_annotation_input_rows,
        confirm_ignored_runs_workspace,
        confirm_private_output_only,
        confirm_aggregate_public_report_only,
        confirm_no_scoring_or_evidence_success_until_separate_boundary,
        confirm_no_provider_llm_model_default_runtime_product_change,
        confirm_no_network_fetch_clone_source_refresh,
        confirm_phase9j_rows_not_benchmark_truth,
        confirm_phase9l_outcome_packets_not_read,
        confirm_single_fixed_route_no_fallback_no_retry,
        confirm_deterministic_manual_extraction_only,
    )
    missing = [name for name, ok in confirmations.items() if not ok]
    if missing:
        raise ValueError("missing required confirmation(s): " + ", ".join(missing))

    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    public_report.parent.mkdir(parents=True, exist_ok=True)

    # Validate Phase 9M gate (read tracked public report only).
    phase9m_errors = _phase9m_gate_errors(
        supplied_commit=confirm_phase9m_commit,
        supplied_ci=confirm_phase9m_ci,
        supplied_status=confirm_phase9m_status,
    )
    phase9m_gate_ok = not phase9m_errors

    if not phase9m_gate_ok:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9m_gate_ok, confirmations,
            private_phase9h_sources_read=False,
            private_phase9j_annotation_input_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated gate-missing report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9n_gate_missing_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9m_gate_missing_or_not_green",
                "phase9m_gate_errors_private": phase9m_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["availability_buckets"]["attempted_bucket"],
            "public_acquired_valid_bucket": report["availability_buckets"]["acquired_valid_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Locate and read the Phase 9H private materialized sources.
    h_loc = _find_phase9h_private_materialization()
    if h_loc is None:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9m_gate_ok, confirmations,
            private_phase9h_sources_read=False,
            private_phase9j_annotation_input_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated no-materialization report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9n_no_materialization_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9h_private_materialization_missing_or_not_under_ignored_runs",
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["availability_buckets"]["attempted_bucket"],
            "public_acquired_valid_bucket": report["availability_buckets"]["acquired_valid_bucket"],
            "private_output_under_ignored_runs": True,
        }

    h_manifest_path, h_rows_path, workspace = h_loc
    _, h_rows, h_read_errors = _read_phase9h_private_materialization(
        h_manifest_path, h_rows_path
    )

    # Locate and read the Phase 9J private annotation-input.
    j_loc = _find_phase9j_private_annotation_input()
    if j_loc is None:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9m_gate_ok, confirmations,
            private_phase9h_sources_read=False,
            private_phase9j_annotation_input_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated no-annotation-input report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9n_no_annotation_input_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9j_private_annotation_input_missing_or_not_under_ignored_runs",
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["availability_buckets"]["attempted_bucket"],
            "public_acquired_valid_bucket": report["availability_buckets"]["acquired_valid_bucket"],
            "private_output_under_ignored_runs": True,
        }

    j_manifest_path, j_rows_path = j_loc
    _, j_rows, j_read_errors = _read_phase9j_private_annotation_input(
        j_manifest_path, j_rows_path
    )

    if h_read_errors or not h_rows or j_read_errors or not j_rows:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9m_gate_ok, confirmations,
            private_phase9h_sources_read=bool(h_rows),
            private_phase9j_annotation_input_read=bool(j_rows),
            outcome_packet_errors=h_read_errors or j_read_errors or ["no_valid_input_rows"],
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated input-shape-invalid report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9n_input_shape_invalid_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9h_or_phase9j_input_shape_invalid_or_empty",
                "phase9h_read_errors_private": h_read_errors,
                "phase9j_read_errors_private": j_read_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["availability_buckets"]["attempted_bucket"],
            "public_acquired_valid_bucket": report["availability_buckets"]["acquired_valid_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Execute the single frozen route (deterministic manual extraction).
    outcome_packets, route_errors = _execute_frozen_route(h_rows, j_rows, workspace)

    # Check for deterministic ordering ambiguity (detected BEFORE outcome
    # inspection in _execute_frozen_route, but if any ambiguity errors
    # appeared, block with no-execution status).
    ordering_ambiguity = any("deterministic_ordering_ambiguity" in e for e in route_errors)

    if ordering_ambiguity:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9m_gate_ok, confirmations,
            private_phase9h_sources_read=True,
            private_phase9j_annotation_input_read=True,
            outcome_packet_errors=route_errors,
            ordering_ambiguity=True,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated ordering-ambiguity report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9n_ordering_ambiguity_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "deterministic_ordering_ambiguity_before_outcome_inspection",
                "ordering_ambiguity_errors_private": [
                    e for e in route_errors if "deterministic_ordering_ambiguity" in e
                ],
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["availability_buckets"]["attempted_bucket"],
            "public_acquired_valid_bucket": report["availability_buckets"]["acquired_valid_bucket"],
            "private_output_under_ignored_runs": True,
        }

    if route_errors:
        aggregate = _compute_outcome_aggregate(outcome_packets) if outcome_packets else _empty_aggregate()
        report = build_public_report(
            aggregate, phase9m_gate_ok, confirmations,
            private_phase9h_sources_read=True,
            private_phase9j_annotation_input_read=True,
            outcome_packet_errors=route_errors,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated outcome-packet-invalid report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9n_outcome_packet_invalid_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "outcome_packet_schema_violation",
                "outcome_packet_errors_private": route_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["availability_buckets"]["attempted_bucket"],
            "public_acquired_valid_bucket": report["availability_buckets"]["acquired_valid_bucket"],
            "private_output_under_ignored_runs": True,
        }

    private_manifest = _build_private_manifest(outcome_packets)
    aggregate = private_manifest["aggregate_private_totals"]

    report = build_public_report(
        aggregate, phase9m_gate_ok, confirmations,
        private_phase9h_sources_read=True,
        private_phase9j_annotation_input_read=True,
    )
    errors = validate_report(report)
    if errors:
        raise ValueError(
            "generated public report invalid: " + "; ".join(errors[:12])
        )

    private_run_dir.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_phase9n_outcome_acquisition_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (private_run_dir / "private_phase9n_outcome_acquisition_packets.json").write_text(
        json.dumps(outcome_packets, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    public_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": report["status"],
        "public_report": str(public_report),
        "public_attempted_bucket": report["availability_buckets"]["attempted_bucket"],
        "public_acquired_valid_bucket": report["availability_buckets"]["acquired_valid_bucket"],
        "public_unavailable_bucket": report["availability_buckets"]["unavailable_bucket"],
        "public_invalid_rejected_bucket": report["availability_buckets"]["invalid_rejected_bucket"],
        "private_output_under_ignored_runs": True,
    }


# ---------------------------------------------------------------------------
# Synthetic fixtures for self-test
# ---------------------------------------------------------------------------

def _synthetic_phase9h_row(index: int, source_index: int = 0) -> dict[str, Any]:
    return {
        "candidate_order_index_private": index,
        "source_order_index_private": source_index,
        "private_candidate_id": f"synthetic_h_ref_{index}",
        "private_source_file_path": f"file_{index}.py",
        "private_source_sha256": f"hash_{index}",
        "private_line_range": {"start": 1, "end": 10},
        "source_snippet_stored": False,
        "public_access_check_passed": True,
        "replacement_policy_private": "next_deterministic_candidate",
        "currentness_reread_available_private": True,
        "license_access_default_branch_checks_passed": True,
        "task_type": "evidence_finding_file_localizable_code_task",
    }


def _synthetic_phase9j_row(index: int, source_index: int = 0) -> dict[str, Any]:
    return {
        "private_candidate_ref": f"synthetic_h_ref_{index}",
        "source_order_index_private": source_index,
        "candidate_order_index_private": index,
        "task_eligibility_input": (
            "eligible_for_future_annotation_acquisition"
            "_routing_precondition_only_not_benchmark_truth"
        ),
        "evidence_localization_requirement": "file_localized_code_evidence_required",
        "expected_evidence_form": EXPECTED_EVIDENCE_FORM,
        "outcome_acquisition_preconditions": (
            "future_separate_boundary_required_no_outcomes_in_phase9j"
        ),
        "adjudication_rules": "frozen_in_phase9i_protocol_not_executed_in_phase9j",
        "rejection_or_replacement_rules_before_scoring": "next_deterministic_candidate",
        "annotation_input_is_routing_precondition_only_not_benchmark_truth": True,
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": True,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_FILE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    global PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS, NETWORK_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_FILE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    NETWORK_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    full_confirmations = _all_confirmations_dict(
        PHASE9M_COMMIT, PHASE9M_CI_RUN, PHASE9M_STATUS, True,
        True, True, True, True, True, True, True, True, True, True, True, True,
    )

    # --- valid executed report (acquired nonzero) ---
    # NOTE: synthetic counts (12/5) are deliberately unrelated to the
    # private Phase 9N internals (never 49 or 8) so the tracked validator /
    # self-test source cannot leak the real acquired counts.
    valid_aggregate = {
        "outcome_packets_total": 12,
        "acquired_valid_total": 12,
        "unavailable_total": 0,
        "invalid_rejected_total": 0,
        "replacement_needed_total": 0,
        "distinct_sources_with_outcome_packets": 5,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
    }
    valid_report = build_public_report(
        valid_aggregate, True, full_confirmations,
        private_phase9h_sources_read=True,
        private_phase9j_annotation_input_read=True,
    )
    checks.append(("valid_executed_report_passes", not validate_report(valid_report)))
    checks.append(("valid_report_is_executed_valid_status", valid_report["status"] == STATUS_EXECUTED_VALID))
    checks.append(("valid_report_route_executed_true", valid_report["execution_booleans"]["route_executed"] is True))
    checks.append(("valid_report_phase9h_read_true", valid_report["execution_booleans"]["private_phase9h_materialized_sources_read"] is True))
    checks.append(("valid_report_phase9j_read_true", valid_report["execution_booleans"]["private_phase9j_annotation_input_rows_read"] is True))
    checks.append(("valid_report_phase9j_not_truth", valid_report["execution_booleans"]["phase9j_rows_used_as_benchmark_truth"] is False))
    checks.append(("valid_report_phase9l_not_read", valid_report["execution_booleans"]["phase9l_outcome_packets_read"] is False))
    checks.append(("valid_report_acquired_nonzero_bucket", valid_report["availability_buckets"]["acquired_valid_bucket"] == "bucket_nonzero_redacted"))
    checks.append(("valid_report_unavailable_zero_bucket", valid_report["availability_buckets"]["unavailable_bucket"] == "bucket_zero"))
    checks.append(("valid_report_invalid_zero_bucket", valid_report["availability_buckets"]["invalid_rejected_bucket"] == "bucket_zero"))
    checks.append(("valid_report_replacement_zero_bucket", valid_report["availability_buckets"]["replacement_needed_bucket"] == "bucket_zero"))
    checks.append(("valid_report_phase9o_may_consider", valid_report["phase9o_gate"]["scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero"] is True))
    checks.append(("valid_report_phase9o_scoring_false", valid_report["phase9o_gate"]["scoring_executed"] is False))

    # --- executed zero unavailable report ---
    unavail_aggregate = {
        "outcome_packets_total": 12,
        "acquired_valid_total": 0,
        "unavailable_total": 12,
        "invalid_rejected_total": 0,
        "replacement_needed_total": 0,
        "distinct_sources_with_outcome_packets": 5,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
    }
    unavail_report = build_public_report(
        unavail_aggregate, True, full_confirmations,
        private_phase9h_sources_read=True,
        private_phase9j_annotation_input_read=True,
    )
    checks.append(("unavail_report_passes", not validate_report(unavail_report)))
    checks.append(("unavail_report_is_zero_unavailable_status", unavail_report["status"] == STATUS_EXECUTED_ZERO_UNAVAILABLE))
    checks.append(("unavail_report_acquired_zero", unavail_report["availability_buckets"]["acquired_valid_bucket"] == "bucket_zero"))
    checks.append(("unavail_report_unavailable_nonzero", unavail_report["availability_buckets"]["unavailable_bucket"] == "bucket_nonzero_redacted"))
    checks.append(("unavail_report_phase9o_not_considered", unavail_report["phase9o_gate"]["scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero"] is False))

    # --- Phase 9O gate consistency: gate mutated both wrong ways rejected ---
    # Wrong way 1: gate False on an executed_valid report (acquired nonzero).
    mutated = copy.deepcopy(valid_report)
    mutated["phase9o_gate"]["scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero"] = False
    checks.append(("phase9o_gate_false_but_executed_valid_rejected", bool(validate_report(mutated))))

    # Wrong way 2: gate True on a zero-acquired report (acquired bucket zero).
    mutated = copy.deepcopy(unavail_report)
    mutated["phase9o_gate"]["scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero"] = True
    checks.append(("phase9o_gate_true_but_acquired_zero_rejected", bool(validate_report(mutated))))

    # Wrong way 3: gate True on a non-executed-valid status even when the bucket
    # is nonzero.  Phase 9O can only be considered after the exact executed-valid
    # status, not merely any report carrying a nonzero acquired bucket.
    mutated = copy.deepcopy(valid_report)
    mutated["status"] = STATUS_REPAIR
    checks.append(("phase9o_gate_true_but_status_not_executed_valid_rejected", bool(validate_report(mutated))))

    # --- executed zero invalid report ---
    invalid_aggregate = {
        "outcome_packets_total": 12,
        "acquired_valid_total": 0,
        "unavailable_total": 0,
        "invalid_rejected_total": 12,
        "replacement_needed_total": 12,
        "distinct_sources_with_outcome_packets": 5,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
    }
    invalid_report = build_public_report(
        invalid_aggregate, True, full_confirmations,
        private_phase9h_sources_read=True,
        private_phase9j_annotation_input_read=True,
    )
    checks.append(("invalid_report_passes", not validate_report(invalid_report)))
    checks.append(("invalid_report_is_zero_invalid_status", invalid_report["status"] == STATUS_EXECUTED_ZERO_INVALID))
    checks.append(("invalid_report_invalid_nonzero", invalid_report["availability_buckets"]["invalid_rejected_bucket"] == "bucket_nonzero_redacted"))

    # --- gate-missing report ---
    gate_missing_report = build_public_report(
        _empty_aggregate(), False, full_confirmations,
        private_phase9h_sources_read=False,
        private_phase9j_annotation_input_read=False,
    )
    checks.append(("gate_missing_report_passes", not validate_report(gate_missing_report)))
    checks.append(("gate_missing_report_is_gate_missing_status", gate_missing_report["status"] == STATUS_GATE_MISSING))

    # --- repair report (zero attempted) ---
    repair_report = build_public_report(
        _empty_aggregate(), True, full_confirmations,
        private_phase9h_sources_read=False,
        private_phase9j_annotation_input_read=False,
    )
    checks.append(("repair_report_passes", not validate_report(repair_report)))
    checks.append(("repair_report_is_repair_status", repair_report["status"] == STATUS_REPAIR))

    # --- Oracle must-fix: executed_valid with acquired zero rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["availability_buckets"]["acquired_valid_bucket"] = "bucket_zero"
    checks.append(("executed_valid_acquired_zero_rejected", bool(validate_report(mutated))))

    # --- executed_valid with unavailable nonzero rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["availability_buckets"]["unavailable_bucket"] = "bucket_nonzero_redacted"
    checks.append(("executed_valid_unavailable_nonzero_rejected", bool(validate_report(mutated))))

    # --- executed_valid with invalid nonzero rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["availability_buckets"]["invalid_rejected_bucket"] = "bucket_nonzero_redacted"
    checks.append(("executed_valid_invalid_nonzero_rejected", bool(validate_report(mutated))))

    # --- nonzero bucket as exact singleton rejected ---
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "singleton"):
        mutated = copy.deepcopy(valid_report)
        mutated["availability_buckets"]["acquired_valid_bucket"] = singleton_val
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))

    # --- Phase 9M gate drift rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["phase9m_gate_references"]["phase9m_commit"] = "deadbeef" * 5
    checks.append(("wrong_phase9m_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    mutated["phase9m_gate_references"]["phase9m_ci_run"] = "0000"
    checks.append(("wrong_phase9m_ci_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    mutated["phase9m_gate_references"]["phase9m_status"] = "drift"
    checks.append(("wrong_phase9m_status_rejected", bool(validate_report(mutated))))

    # --- missing confirmation blocks execution ---
    confirmation_labels = (
        ("missing_confirm_phase9m_commit", dict(confirm_phase9m_commit=None)),
        ("missing_confirm_phase9m_ci", dict(confirm_phase9m_ci=None)),
        ("missing_confirm_phase9m_status", dict(confirm_phase9m_status=None)),
        ("missing_confirm_phase9m_protocol_freeze", dict(confirm_phase9m_protocol_freeze=False)),
        ("missing_confirm_read_phase9h_sources", dict(confirm_read_phase9h_private_materialized_sources=False)),
        ("missing_confirm_read_phase9j_rows", dict(confirm_read_phase9j_private_annotation_input_rows=False)),
        ("missing_confirm_ignored_runs_workspace", dict(confirm_ignored_runs_workspace=False)),
        ("missing_confirm_private_output_only", dict(confirm_private_output_only=False)),
        ("missing_confirm_aggregate_public_report_only", dict(confirm_aggregate_public_report_only=False)),
        ("missing_confirm_no_scoring_evidence_success", dict(confirm_no_scoring_or_evidence_success_until_separate_boundary=False)),
        ("missing_confirm_no_provider_llm_model", dict(confirm_no_provider_llm_model_default_runtime_product_change=False)),
        ("missing_confirm_no_network_fetch_clone", dict(confirm_no_network_fetch_clone_source_refresh=False)),
        ("missing_confirm_phase9j_not_truth", dict(confirm_phase9j_rows_not_benchmark_truth=False)),
        ("missing_confirm_phase9l_not_read", dict(confirm_phase9l_outcome_packets_not_read=False)),
        ("missing_confirm_single_fixed_route", dict(confirm_single_fixed_route_no_fallback_no_retry=False)),
        ("missing_confirm_deterministic_extraction", dict(confirm_deterministic_manual_extraction_only=False)),
    )
    for label, overrides in confirmation_labels:
        kwargs = dict(
            confirm_phase9m_commit=PHASE9M_COMMIT,
            confirm_phase9m_ci=PHASE9M_CI_RUN,
            confirm_phase9m_status=PHASE9M_STATUS,
            confirm_phase9m_protocol_freeze=True,
            confirm_read_phase9h_private_materialized_sources=True,
            confirm_read_phase9j_private_annotation_input_rows=True,
            confirm_ignored_runs_workspace=True,
            confirm_private_output_only=True,
            confirm_aggregate_public_report_only=True,
            confirm_no_scoring_or_evidence_success_until_separate_boundary=True,
            confirm_no_provider_llm_model_default_runtime_product_change=True,
            confirm_no_network_fetch_clone_source_refresh=True,
            confirm_phase9j_rows_not_benchmark_truth=True,
            confirm_phase9l_outcome_packets_not_read=True,
            confirm_single_fixed_route_no_fallback_no_retry=True,
            confirm_deterministic_manual_extraction_only=True,
        )
        kwargs.update(overrides)
        try:
            execute_phase9n(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, **kwargs)
            checks.append((f"{label}_rejected", False))
        except ValueError as exc:
            checks.append((f"{label}_rejected", "missing required confirmation" in str(exc)))

    # --- tracked/private path rejected ---
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_tracked_output")
        checks.append(("tracked_output_path_rejected", False))
    except ValueError as exc:
        checks.append(("tracked_output_path_rejected", "runs" in str(exc)))

    # --- Phase 9H row shape validation ---
    valid_h_row = _synthetic_phase9h_row(0)
    checks.append(("valid_phase9h_row_shape_passes", not _validate_phase9h_row_shape(valid_h_row, 0)))
    bad_h_row = {"private_candidate_id": "abc"}
    checks.append(("invalid_phase9h_row_shape_rejected", bool(_validate_phase9h_row_shape(bad_h_row, 0))))

    # --- Phase 9J row shape validation ---
    valid_j_row = _synthetic_phase9j_row(0)
    checks.append(("valid_phase9j_row_shape_passes", not _validate_phase9j_row_shape(valid_j_row, 0)))
    bad_j_row = {"private_candidate_ref": "abc"}
    checks.append(("invalid_phase9j_row_shape_rejected", bool(_validate_phase9j_row_shape(bad_j_row, 0))))

    # --- outcome packet with forbidden scoring field rejected ---
    h_row = _synthetic_phase9h_row(0)
    j_row = _synthetic_phase9j_row(0)
    with tempfile.TemporaryDirectory(prefix="phase9n_selftest_") as tmp:
        ws = Path(tmp)
        src_dir = ws / "private_source_0"
        src_dir.mkdir(parents=True)
        (src_dir / "file_0.py").write_text("\n".join(f"line {i}" for i in range(20)) + "\n", encoding="utf-8")
        packet = _acquire_outcome_observable(h_row, j_row, ws)
        checks.append(("valid_acquired_packet_passes", not _validate_outcome_packet(packet, 0)))
        checks.append(("acquired_packet_state_acquired", packet["outcome_acquisition_state"] == "acquired"))
        checks.append(("acquired_packet_observable_acquired", packet["outcome_observable_acquired"] is True))
        checks.append(("acquired_packet_source_grounded", packet["evidence_form_confirmed_source_grounded"] is True))
        checks.append(("acquired_packet_replacement_false", packet["replacement_needed"] is False))

        # --- unavailable: file absent ---
        h_absent = dict(h_row, private_source_file_path="nonexistent.py")
        packet_absent = _acquire_outcome_observable(h_absent, j_row, ws)
        checks.append(("absent_packet_unavailable", packet_absent["outcome_acquisition_state"] == "unavailable"))
        checks.append(("absent_packet_not_acquired", packet_absent["outcome_observable_acquired"] is False))
        checks.append(("absent_packet_passes_validation", not _validate_outcome_packet(packet_absent, 0)))

        # --- unavailable: line range exceeds file ---
        h_overflow = dict(h_row, private_line_range={"start": 1, "end": 100})
        packet_overflow = _acquire_outcome_observable(h_overflow, j_row, ws)
        checks.append(("overflow_packet_unavailable", packet_overflow["outcome_acquisition_state"] == "unavailable"))
        checks.append(("overflow_packet_passes_validation", not _validate_outcome_packet(packet_overflow, 0)))

        # --- invalid: wrong evidence form ---
        j_wrong_form = dict(j_row, expected_evidence_form="snippet_stored_wrong_form")
        packet_invalid = _acquire_outcome_observable(h_row, j_wrong_form, ws)
        checks.append(("wrong_form_packet_invalid", packet_invalid["outcome_acquisition_state"] == "invalid"))
        checks.append(("wrong_form_packet_replacement_needed", packet_invalid["replacement_needed"] is True))
        checks.append(("wrong_form_packet_passes_validation", not _validate_outcome_packet(packet_invalid, 0)))

        # --- invalid: malformed line range ---
        h_malformed = dict(h_row, private_line_range={"start": 5, "end": 2})
        packet_malformed = _acquire_outcome_observable(h_malformed, j_row, ws)
        checks.append(("malformed_range_packet_invalid", packet_malformed["outcome_acquisition_state"] == "invalid"))
        checks.append(("malformed_range_packet_replacement_needed", packet_malformed["replacement_needed"] is True))

        # --- provider/LLM sentinel: an outcome packet with a scoring field rejected ---
        bad_packet = dict(packet)
        bad_packet["score_value"] = 42
        checks.append(("packet_scoring_field_rejected", bool(_validate_outcome_packet(bad_packet, 0))))
        bad_packet2 = dict(packet)
        bad_packet2["gold_answer"] = "hidden"
        checks.append(("packet_gold_field_rejected", bool(_validate_outcome_packet(bad_packet2, 0))))

        # --- invalid-only blocks 9O ---
        invalid_only_aggregate = _compute_outcome_aggregate([packet_invalid, dict(packet_invalid, candidate_order_index_private=1)])
        invalid_only_report = build_public_report(
            invalid_only_aggregate, True, full_confirmations,
            private_phase9h_sources_read=True,
            private_phase9j_annotation_input_read=True,
        )
        checks.append(("invalid_only_report_passes", not validate_report(invalid_only_report)))
        checks.append(("invalid_only_blocks_9o", invalid_only_report["phase9o_gate"]["scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero"] is False))

        # --- full route execution with multiple acquired ---
        # Synthetic row/source counts (6) are deliberately unrelated to the
        # private Phase 9N internals (never 49 or 8).
        h_rows = [_synthetic_phase9h_row(i, i % 6) for i in range(6)]
        j_rows_multi = [_synthetic_phase9j_row(i, i % 6) for i in range(6)]
        for i in range(6):
            sd = ws / f"private_source_{i % 6}"
            sd.mkdir(parents=True, exist_ok=True)
            (sd / f"file_{i}.py").write_text("\n".join(f"line {j}" for j in range(20)) + "\n", encoding="utf-8")
        packets, route_errs = _execute_frozen_route(h_rows, j_rows_multi, ws)
        checks.append(("route_execution_no_errors", not route_errs))
        checks.append(("route_execution_count_matches", len(packets) == 6))
        checks.append(("route_execution_all_acquired", all(p["outcome_acquisition_state"] == "acquired" for p in packets)))

    # --- strict schema: unknown fields rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    mutated["availability_buckets"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_rejected", bool(validate_report(mutated))))

    # --- private-shaped public values rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["availability_buckets"]["example_value"] = "https://example.invalid/repo.git"
    checks.append(("url_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    mutated["availability_buckets"]["example_value"] = "owner/repo"
    checks.append(("owner_repo_private_shaped_value_rejected", bool(validate_report(mutated))))

    # --- privacy boundary violations rejected ---
    for privacy_key in ("per_source_public_facts", "per_task_public_facts", "outcome_packets_public", "outcome_observables_public"):
        mutated = copy.deepcopy(valid_report)
        mutated["privacy_summary"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # --- private-shaped keys rejected ---
    for bad_key in ("private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket", "per_task_summary", "source_path_bucket"):
        mutated = copy.deepcopy(valid_report)
        mutated["availability_buckets"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- forbidden execution boundary true rejected ---
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(valid_report)
        mutated["forbidden_execution_boundary"][exec_key] = True
        checks.append((f"{exec_key}_true_rejected", bool(validate_report(mutated))))

    # --- claim boundary true rejected ---
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(valid_report)
        mutated["no_claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- forbidden claim phrases rejected ---
    for phrase in ("method effectiveness", "product readiness", "scoring success", "outcome success", "frozen route works", "acquisition success", "route proven"):
        mutated = copy.deepcopy(valid_report)
        mutated["availability_buckets"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_')}_rejected", bool(validate_report(mutated))))

    # --- forbidden standalone status wording rejected ---
    for bad_word in ("validated", "benchmark", "gold", "correctness"):
        mutated = copy.deepcopy(valid_report)
        mutated["availability_buckets"]["example_note"] = f"this is {bad_word} here"
        checks.append((f"forbidden_status_wording_{bad_word}_rejected", bool(validate_report(mutated))))

    # --- exact count field rejected ---
    # Synthetic count (12) is deliberately unrelated to private internals.
    mutated = copy.deepcopy(valid_report)
    mutated["availability_buckets"]["count"] = 12
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    # --- route vocabulary drift rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["frozen_route_attestation"]["extraction_procedure"][0] = "llm_based_extraction"
    checks.append(("route_vocabulary_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    mutated["frozen_route_attestation"]["observable_definition"].append("extra_member")
    checks.append(("route_extra_member_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    del mutated["frozen_route_attestation"]["stop_rule"]
    checks.append(("route_missing_list_rejected", bool(validate_report(mutated))))

    # --- status/phase/schema drift rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["status"] = "drift"
    checks.append(("status_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    mutated["phase"] = "drift"
    checks.append(("phase_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(valid_report)
    mutated["schema_version"] = "drift"
    checks.append(("schema_drift_rejected", bool(validate_report(mutated))))

    # --- conservative recommendation drift rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["conservative_recommendation"] = "wrong"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # --- validate-report path fail-closed ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9n" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "other_phase" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase9n" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # --- temp-file round-trip validation ---
    with tempfile.TemporaryDirectory(prefix="phase9n_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(valid_report), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- gate-reference CI run values on whitelisted paths valid ---
    checks.append(("gate_ci_run_values_on_whitelisted_paths_valid", not validate_report(valid_report)))

    # --- self-test does not fetch/read private ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9l_packets", PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_make_network_calls", NETWORK_CALL_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9N frozen-route outcome-observable acquisition (availability only)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--confirm-phase9m-commit")
    parser.add_argument("--confirm-phase9m-ci")
    parser.add_argument("--confirm-phase9m-status")
    parser.add_argument("--confirm-phase9m-protocol-freeze", action="store_true")
    parser.add_argument("--confirm-read-phase9h-private-materialized-sources", action="store_true")
    parser.add_argument("--confirm-read-phase9j-private-annotation-input-rows", action="store_true")
    parser.add_argument("--confirm-ignored-runs-workspace", action="store_true")
    parser.add_argument("--confirm-private-output-only", action="store_true")
    parser.add_argument("--confirm-aggregate-public-report-only", action="store_true")
    parser.add_argument("--confirm-no-scoring-or-evidence-success-until-separate-boundary", action="store_true")
    parser.add_argument("--confirm-no-provider-llm-model-default-runtime-product-change", action="store_true")
    parser.add_argument("--confirm-no-network-fetch-clone-source-refresh", action="store_true")
    parser.add_argument("--confirm-phase9j-rows-not-benchmark-truth", action="store_true")
    parser.add_argument("--confirm-phase9l-outcome-packets-not-read", action="store_true")
    parser.add_argument("--confirm-single-fixed-route-no-fallback-no-retry", action="store_true")
    parser.add_argument("--confirm-deterministic-manual-extraction-only", action="store_true")
    parser.add_argument("--private-run-dir", type=Path, default=DEFAULT_PRIVATE_RUN_DIR)
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.validate_report:
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
        result = execute_phase9n(
            args.private_run_dir,
            args.output,
            args.confirm_phase9m_commit,
            args.confirm_phase9m_ci,
            args.confirm_phase9m_status,
            args.confirm_phase9m_protocol_freeze,
            args.confirm_read_phase9h_private_materialized_sources,
            args.confirm_read_phase9j_private_annotation_input_rows,
            args.confirm_ignored_runs_workspace,
            args.confirm_private_output_only,
            args.confirm_aggregate_public_report_only,
            args.confirm_no_scoring_or_evidence_success_until_separate_boundary,
            args.confirm_no_provider_llm_model_default_runtime_product_change,
            args.confirm_no_network_fetch_clone_source_refresh,
            args.confirm_phase9j_rows_not_benchmark_truth,
            args.confirm_phase9l_outcome_packets_not_read,
            args.confirm_single_fixed_route_no_fallback_no_retry,
            args.confirm_deterministic_manual_extraction_only,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
