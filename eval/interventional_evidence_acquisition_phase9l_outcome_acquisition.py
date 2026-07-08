#!/usr/bin/env python3
"""Phase 9L outcome acquisition (no scoring, no adjudication, no claim).

This runner has one narrow purpose: under explicit confirmations and the frozen
Phase 9K outcome-acquisition protocol, read the Phase 9J private annotation-
input rows under ignored ``runs/`` only, acquire outcome-acquisition packets
under ignored ``runs/`` only, and publish only an aggregate/bucketed public
report.  It does NOT do scoring, adjudication, gold labels, benchmark labels,
evidence_success, precision/recall, correctness, pass/fail, result labels,
provider/LLM/network/fetch/clone/source refresh, model fitting/training,
runtime/default/product changes, or method/product/performance/provider/model
claims.

Outcome-acquisition packets record only the outcome acquisition state
(acquired/unavailable/invalid) plus validation-state/readiness buckets.  They
do NOT compute scores, correctness, pass/fail, evidence_success, precision/
recall, benchmark results, gold answers, adjudicated answers, or method
success.  Annotation-input metadata remains routing/precondition metadata only,
NOT benchmark truth.

Within this boundary the only authorized private read is the Phase 9J private
annotation-input rows (routing/precondition metadata only).  The Phase 9H
private materialized inventory/sources are NOT authorized to be read here, and
no provider/LLM/evidence-acquisition method execution is authorized.  The
Phase 9K frozen rule ``missing_outcome_handled_as_unavailable_not_as_failure_
or_success`` is therefore applied: an outcome observable that cannot be
acquired from authorized reads alone is recorded as ``unavailable``, not as
failure or success.  This applies the frozen Phase 9K handling rule; it does
NOT invent a new material rule.

The Phase 9K, Phase 9H, Phase 9I, and Phase 9J public gate reference values
(remote commits and CI runs) are the only public gate references published by
Phase 9L.  Phase 9G and Phase 9F are carried as inherited provenance only and
their exact remote commit/CI run values are intentionally NOT published in the
Phase 9L report/docs (bucketed inherited provenance).  Local same-tree git
commits are not read or compared; the supplied confirmation values are matched
against the frozen public gate constants only.

Outcome acquisition is not scoring, not adjudication, not evidence_success, not
method success, not benchmark success, not product readiness.  Eligibility
annotations remain routing/precondition metadata only, not benchmark truth.
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

# Compact Phase 9L slug (kept short so the absolute artifact report path stays
# comfortably under the Windows MAX_PATH (260) limit).  Boundary wording in the
# report body/docs is NOT weakened — only the path-dependent slug is shortened.
PHASE = "phase9l_outcome_acquisition_no_scoring_no_claim"
# Honest completed wording: outcome-acquisition packets were generated as
# unavailable-only (no scoring, no adjudication, no claim).  Not
# "success"/"validated"/"benchmark" (forbidden wording); "executed_unavailable_only"
# honestly reflects that acquisition packets were produced under the Phase 9K
# missing-outcome rule (all packets unavailable, none acquired) without
# overstating to outcome/scoring/evidence_success.  The unavailable-only
# invariant is also validator-enforced (see validate_report STATUS_EXECUTED),
# so a mutated executed report claiming nonzero acquired outcomes, an
# unavailable/invalid mismatch, replacement drift, or readiness drift is
# rejected.
STATUS_EXECUTED = (
    "phase9l_outcome_acquisition_executed_unavailable_only"
    "_no_scoring_no_adjudication_no_claim"
)
STATUS_REPAIR = "phase9l_outcome_acquisition_repair_no_claim"
STATUS_GATE_MISSING = (
    "phase9l_blocked_phase9k_or_phase9h_or_phase9i_or_phase9j"
    "_gate_missing_or_not_green_no_claim"
)
ALLOWED_STATUSES = {STATUS_EXECUTED, STATUS_REPAIR, STATUS_GATE_MISSING}
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

# ---------------------------------------------------------------------------
# Phase 9K public gate reference values (oracle-provided).
# ---------------------------------------------------------------------------
PHASE9K_PHASE = "phase9k_outcome_scoring_protocol_freeze_no_claim"
PHASE9K_STATUS = PHASE9K_PHASE
PHASE9K_COMMIT = "233a16e6672b05b87b09be5b920f8fc9dd72e274"
PHASE9K_CI_RUN = "28981994749"
PHASE9K_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE9K_PHASE / f"{PHASE9K_PHASE}_report.json"
)

# Phase 9H public gate reference values (oracle-provided).
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
PHASE9J_PHASE = "phase9j_annotation_input_execution_no_scoring_no_claim"
PHASE9J_STATUS = "phase9j_annotation_input_rows_generated_no_scoring_no_claim"
PHASE9J_COMMIT = "25140f4017acf139012fe917fd920ddba9839cc3"
PHASE9J_CI_RUN = "28980705743"

# Expected private Phase 9J annotation-input location (under ignored runs/ only).
PHASE9J_PRIVATE_RUN_DIR = REPO / "runs" / PHASE9J_PHASE / "current"
PHASE9J_PRIVATE_MANIFEST = (
    PHASE9J_PRIVATE_RUN_DIR / "private_phase9j_annotation_input_manifest.json"
)
PHASE9J_PRIVATE_ROWS = (
    PHASE9J_PRIVATE_RUN_DIR / "private_phase9j_annotation_input_rows.json"
)

# Phase 9G/9F inherited provenance (bucketed only; exact commit/CI NOT published).
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

# Frozen Phase 9K outcome-acquisition packet required fields (routing/
# precondition metadata only, NOT benchmark truth).  These are the only
# routing/precondition fields a private outcome-acquisition packet may carry
# forward from the Phase 9J annotation-input row.
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
    "outcome_acquisition_readiness_bucket": str,
    "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": bool,
}

# Frozen outcome-acquisition states (from Phase 9K protocol).
OUTCOME_ACQUISITION_STATES = ("acquired", "unavailable", "invalid")

# The outcome observable cannot be acquired from authorized reads alone within
# this boundary (Phase 9J annotation-input rows are routing/precondition
# metadata only; Phase 9H materialized sources and evidence-acquisition method
# execution are NOT authorized here).  The Phase 9K frozen rule
# ``missing_outcome_handled_as_unavailable_not_as_failure_or_success`` is
# applied: the outcome acquisition state is recorded as ``unavailable``.
OUTCOME_ACQUISITION_STATE_UNAVAILABLE = "unavailable"
OUTCOME_OBSERVABLE_ACQUIRED_DEFAULT = False
REPLACEMENT_NEEDED_DEFAULT = False
OUTCOME_ACQUISITION_READINESS_BUCKET = (
    "bucket_outcome_observable_unavailable_within_boundary"
)

# Forbidden tokens in outcome-packet field names (defense in depth; the strict
# allowed-field check already rejects any unknown field, but this catches
# accidental reintroduction with explicit messaging).  Boundary boolean field
# names that legitimately contain these tokens (e.g.
# ``no_scoring_no_adjudication_...``) are in the allowed schema and are never
# scanned here — only UNKNOWN/extra fields are checked.
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
# boundary attestation keys (e.g. ``scoring_executed``) and boundary-boolean
# keys that legitimately contain these tokens (e.g.
# ``no_scoring_no_adjudication_...``) are not false-flagged.
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
# public gate constants (full commit SHA / CI run ID).  Exact path whitelist,
# NOT a suffix match.  Only Phase 9K, Phase 9H, Phase 9I, and Phase 9J
# commit/CI are public gate references; Phase 9G/9F exact commit/CI are
# intentionally not published.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9k_gate_references.phase9k_commit",
        "$.phase9k_gate_references.phase9k_ci_run",
        "$.phase9h_gate_references.phase9h_commit",
        "$.phase9h_gate_references.phase9h_ci_run",
        "$.phase9i_gate_references.phase9i_commit",
        "$.phase9i_gate_references.phase9i_ci_run",
        "$.phase9j_gate_references.phase9j_commit",
        "$.phase9j_gate_references.phase9j_ci_run",
    }
)

# Exact public gate-reference JSON paths whose string VALUES are CI run IDs
# (long decimal integers).
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9k_gate_references.phase9k_ci_run",
        "$.phase9h_gate_references.phase9h_ci_run",
        "$.phase9i_gate_references.phase9i_ci_run",
        "$.phase9j_gate_references.phase9j_ci_run",
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
    r"|manifest_path|candidate_id|commit_sha|outcome_observable)",
    re.IGNORECASE,
)
CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"materialization\s+(?:works|succeeded|proven|established)"
    r"|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)"
    r"|clone\s+(?:works|succeeded|proven|established)"
    r"|annotation\s+(?:works|succeeded|proven|established)"
    r"|annotation_input\s+(?:works|succeeded|proven|established)"
    r"|outcome\s+acquisition\s+(?:works|succeeded|proven|established)"
    r"|evidence_success\s+(?:achieved|proven|established|confirmed)"
    r"|method\s+(?:proven|established|works|winner|effectiveness)"
    r"|product\s+readiness"
    r"|scoring\s+success"
    r"|outcome\s+success"
    r"|adjudication\s+success"
    r"|evaluation\s+works"
    r"|task\s+annotation\s+readiness"
    r"|lift\s+(?:proven|established|achieved)"
    r")\b",
    re.IGNORECASE,
)

# Forbidden standalone status wording that must never appear as an exposed
# non-gate string value.  Word-boundary matched so underscore-joined boundary
# negations (e.g. ``no_gold``, ``no_scoring``) are NOT flagged (the leading
# underscore is a word character, so there is no word boundary before the
# token).
FORBIDDEN_STATUS_WORDING_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:success|validated|benchmark|gold|correctness)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_FILE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
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

def _bucket_quantity(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < MIN_DISTINCT_SOURCES:
        return "bucket_nonzero_below_minimum"
    if value < TARGET_INVENTORY_MIN:
        return "bucket_at_least_minimum_below_target"
    if value <= TARGET_INVENTORY_MAX:
        return "bucket_target_48_to_72"
    if value <= HARD_INVENTORY_CAP:
        return "bucket_above_target_within_hard_cap"
    return "bucket_over_hard_cap"


def _bucket_sources(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < MIN_DISTINCT_SOURCES:
        return "bucket_nonzero_below_minimum"
    if value <= 12:
        return "bucket_minimum_met_low"
    if value <= 24:
        return "bucket_minimum_met_mid"
    return "bucket_minimum_met_high"


def _bucket_outcome_state_counts(
    attempted: int, acquired: int, unavailable: int, invalid: int
) -> dict[str, str]:
    """Bucket the outcome-acquisition state counts (aggregate only)."""
    return {
        "attempted_bucket": _bucket_quantity(attempted),
        "acquired_bucket": _bucket_quantity(acquired),
        "unavailable_bucket": _bucket_quantity(unavailable),
        "invalid_bucket": _bucket_quantity(invalid),
        "replacement_needed_bucket": _bucket_quantity(invalid),
        "readiness_bucket": OUTCOME_ACQUISITION_READINESS_BUCKET,
    }


# ---------------------------------------------------------------------------
# Phase 9K / 9H / 9I / 9J gate validation (reads tracked public reports only)
# ---------------------------------------------------------------------------

def _phase9k_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9K public gate.  Reads the tracked public report only."""
    errors: list[str] = []
    if report is None:
        if not PHASE9K_PUBLIC_REPORT.exists():
            return ["Phase 9K public report missing"]
        report = json.loads(PHASE9K_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9K public report must be object"]
    if report.get("status") != PHASE9K_STATUS:
        errors.append("Phase 9K public report status drift")
    if report.get("schema_version") != f"{PHASE9K_PHASE}_report_v1":
        errors.append("Phase 9K public report schema drift")
    if supplied_commit is not None and supplied_commit != PHASE9K_COMMIT:
        errors.append("supplied Phase 9K commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9K_CI_RUN:
        errors.append("supplied Phase 9K CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9K_STATUS:
        errors.append("supplied Phase 9K status does not match public gate reference")
    return sorted(set(errors))


def _phase9h_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9H public gate.  Reads the tracked public report only."""
    errors: list[str] = []
    if report is None:
        public_report = (
            REPO / "artifacts"
            / "phase9h_candidate_source_pool_public_source_network_fetch"
            "_materialization_no_scoring_no_claim"
            / "phase9h_candidate_source_pool_public_source_network_fetch"
            "_materialization_no_scoring_no_claim_report.json"
        )
        if not public_report.exists():
            return ["Phase 9H public report missing"]
        report = json.loads(public_report.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9H public report must be object"]
    if report.get("status") != PHASE9H_STATUS:
        errors.append("Phase 9H public report status drift")
    if supplied_commit is not None and supplied_commit != PHASE9H_COMMIT:
        errors.append("supplied Phase 9H commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9H_CI_RUN:
        errors.append("supplied Phase 9H CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9H_STATUS:
        errors.append("supplied Phase 9H status does not match public gate reference")
    return sorted(set(errors))


def _phase9i_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9I public gate.  Reads the tracked public report only."""
    errors: list[str] = []
    if report is None:
        public_report = (
            REPO / "artifacts"
            / "phase9i_materialized_inventory_to_task_annotation_protocol_freeze"
            "_no_execution_no_scoring_no_claim"
            / "phase9i_materialized_inventory_to_task_annotation_protocol_freeze"
            "_no_execution_no_scoring_no_claim_report.json"
        )
        if not public_report.exists():
            return ["Phase 9I public report missing"]
        report = json.loads(public_report.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9I public report must be object"]
    if report.get("status") != PHASE9I_STATUS:
        errors.append("Phase 9I public report status drift")
    if supplied_commit is not None and supplied_commit != PHASE9I_COMMIT:
        errors.append("supplied Phase 9I commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9I_CI_RUN:
        errors.append("supplied Phase 9I CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9I_STATUS:
        errors.append("supplied Phase 9I status does not match public gate reference")
    return sorted(set(errors))


def _phase9j_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9J public gate.  Reads the tracked public report only."""
    errors: list[str] = []
    if report is None:
        public_report = (
            REPO / "artifacts" / PHASE9J_PHASE / f"{PHASE9J_PHASE}_report.json"
        )
        if not public_report.exists():
            return ["Phase 9J public report missing"]
        report = json.loads(public_report.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9J public report must be object"]
    if report.get("status") != PHASE9J_STATUS:
        errors.append("Phase 9J public report status drift")
    if report.get("schema_version") != f"{PHASE9J_PHASE}_report_v1":
        errors.append("Phase 9J public report schema drift")
    if supplied_commit is not None and supplied_commit != PHASE9J_COMMIT:
        errors.append("supplied Phase 9J commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9J_CI_RUN:
        errors.append("supplied Phase 9J CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9J_STATUS:
        errors.append("supplied Phase 9J status does not match public gate reference")
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Phase 9J private annotation-input reading (under ignored runs/ only)
# ---------------------------------------------------------------------------

def _find_phase9j_private_annotation_input() -> tuple[Path, Path] | None:
    """Locate the Phase 9J private manifest + rows under ignored runs/ only.

    Returns (manifest_path, rows_path) or None if not found / not under runs/.
    """
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
    """Validate the Phase 9J private manifest has the expected shape.

    Pure schema check: no filesystem or network access.
    """
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
    """Validate a single Phase 9J private annotation-input row shape.

    Pure schema check: no filesystem or network access.
    """
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
    """Read the Phase 9J private manifest + rows under ignored runs/ only.

    Returns (manifest, rows, errors).  Private only; never public.
    """
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
# Outcome-acquisition packet generation
# ---------------------------------------------------------------------------

def _generate_outcome_packet(ann_row: dict[str, Any], index: int) -> dict[str, Any]:
    """Generate a single private outcome-acquisition packet from a Phase 9J
    annotation-input row.

    Only frozen Phase 9K protocol fields + outcome acquisition state.  Routing/
    precondition metadata only, NOT benchmark truth.  The outcome acquisition
    state is ``unavailable`` because the outcome observable cannot be acquired
    from authorized reads alone within this boundary (Phase 9K frozen rule:
    missing outcome = unavailable, not failure or success).
    """
    return {
        "private_annotation_input_ref": ann_row["private_candidate_ref"],
        "source_order_index_private": ann_row["source_order_index_private"],
        "candidate_order_index_private": ann_row["candidate_order_index_private"],
        "task_eligibility_routing_precondition_only": ann_row[
            "task_eligibility_input"
        ],
        "evidence_localization_requirement": ann_row[
            "evidence_localization_requirement"
        ],
        "expected_evidence_form": ann_row["expected_evidence_form"],
        "outcome_acquisition_precondition": ann_row[
            "outcome_acquisition_preconditions"
        ],
        "annotation_input_metadata_reference": (
            "phase9j_annotation_input_row_routing_precondition_only"
            "_not_benchmark_truth"
        ),
        "outcome_acquisition_state": OUTCOME_ACQUISITION_STATE_UNAVAILABLE,
        "outcome_observable_acquired": OUTCOME_OBSERVABLE_ACQUIRED_DEFAULT,
        "replacement_needed": REPLACEMENT_NEEDED_DEFAULT,
        "outcome_acquisition_readiness_bucket": OUTCOME_ACQUISITION_READINESS_BUCKET,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
    }


def _validate_outcome_packet(row: Any, index: int) -> list[str]:
    """Validate a single outcome-acquisition packet against the frozen schema.

    Rejects any extra field, any missing field, wrong types, invalid
    acquisition state, and any forbidden token in field names (defense in
    depth).  Pure check; no I/O.
    """
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
    # When state is invalid, replacement_needed must be True (Phase 9K frozen
    # rule: invalid outcome rejected before scoring with replacement only).
    if row.get("outcome_acquisition_state") == "invalid":
        if row.get("replacement_needed") is not True:
            errors.append(
                f"outcome packet {index} invalid state requires replacement_needed True"
            )
    # Boundary boolean must be True.
    if row.get(
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels"
    ) is not True:
        errors.append(
            f"outcome packet {index} no-scoring/adjudication/evidence_success boundary failed"
        )
    return errors


def _generate_outcome_packets(
    annotation_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Generate all outcome-acquisition packets from Phase 9J annotation-input rows."""
    packets: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, ann_row in enumerate(annotation_rows):
        packet = _generate_outcome_packet(ann_row, index)
        packets.append(packet)
        errors.extend(_validate_outcome_packet(packet, index))
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
        "acquired_total": acquired,
        "unavailable_total": unavailable,
        "invalid_total": invalid,
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
    annotation_aggregate: dict[str, Any],
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
        "outcome_acquisition_packets_private": outcome_packets,
        "source_private_summaries": source_summaries,
        "aggregate_private_totals": aggregate,
        "annotation_input_metadata_remains_routing_precondition_not_benchmark_truth": True,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
        "provider_or_llm_calls_executed": False,
        "model_fitting_executed": False,
        "network_fetch_or_clone_or_source_refresh_executed": False,
    }


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report(
    outcome_aggregate: dict[str, Any],
    phase9k_gate_ok: bool,
    phase9h_gate_ok: bool,
    phase9i_gate_ok: bool,
    phase9j_gate_ok: bool,
    confirmations: dict[str, bool],
    private_annotation_input_read: bool,
    outcome_packet_errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build the aggregate-only public Phase 9L report."""
    attempted = int(outcome_aggregate.get("outcome_packets_total", 0))
    acquired = int(outcome_aggregate.get("acquired_total", 0))
    unavailable = int(outcome_aggregate.get("unavailable_total", 0))
    invalid = int(outcome_aggregate.get("invalid_total", 0))
    replacement_needed = int(outcome_aggregate.get("replacement_needed_total", 0))
    distinct_sources = int(
        outcome_aggregate.get("distinct_sources_with_outcome_packets", 0)
    )
    caps_ok = (
        outcome_aggregate.get("hard_cap_respected") is True
        and outcome_aggregate.get("per_source_cap_respected") is True
    )
    target_ok = TARGET_INVENTORY_MIN <= attempted <= TARGET_INVENTORY_MAX
    diversity_ok = distinct_sources >= MIN_DISTINCT_SOURCES
    schema_ok = not outcome_packet_errors
    all_confirmations = all(confirmations.values()) and len(confirmations) == 20

    gate_ok = (
        phase9k_gate_ok and phase9h_gate_ok
        and phase9i_gate_ok and phase9j_gate_ok
    )
    if not gate_ok:
        status = STATUS_GATE_MISSING
    elif not all_confirmations or not caps_ok or not schema_ok:
        status = STATUS_REPAIR
    elif (
        target_ok and diversity_ok and attempted > 0
        and private_annotation_input_read
    ):
        status = STATUS_EXECUTED
    else:
        status = STATUS_REPAIR

    acquisition_executed = (
        status == STATUS_EXECUTED and attempted > 0
    )
    state_buckets = _bucket_outcome_state_counts(
        attempted, acquired, unavailable, invalid
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9f_inherited_provenance": {
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_repair_no_claim": True,
            "phase9f_zero_buckets": True,
            "phase9f_public_fetch_or_clone_executed": False,
            "phase9f_carried_as_inherited_provenance_only": True,
            "phase9f_remote_provenance_bucketed": True,
        },
        "phase9g_inherited_provenance": {
            "phase9g_ci_success": True,
            "phase9g_status": PHASE9G_STATUS,
            "phase9g_protocol_freeze": True,
            "phase9g_remote_provenance_bucketed": True,
            "phase9g_carried_as_inherited_provenance_only": True,
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
            "phase9k_gate_required_before_phase9l": True,
            "phase9k_public_report_validated": phase9k_gate_ok,
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
            "phase9h_gate_required_before_phase9l": True,
            "phase9h_public_report_validated": phase9h_gate_ok,
        },
        "phase9i_gate_references": {
            "phase9i_commit": PHASE9I_COMMIT,
            "phase9i_ci_run": PHASE9I_CI_RUN,
            "phase9i_ci_success": True,
            "phase9i_status": PHASE9I_STATUS,
            "phase9i_protocol_freeze": True,
            "phase9i_annotation_protocol_frozen": True,
            "phase9i_gate_required_before_phase9l": True,
            "phase9i_carried_as_inherited_provenance_only": True,
            "phase9i_public_report_validated": phase9i_gate_ok,
        },
        "phase9j_gate_references": {
            "phase9j_commit": PHASE9J_COMMIT,
            "phase9j_ci_run": PHASE9J_CI_RUN,
            "phase9j_ci_success": True,
            "phase9j_status": PHASE9J_STATUS,
            "phase9j_annotation_input_rows_generated": True,
            "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": True,
            "phase9j_gate_required_before_phase9l": True,
            "phase9j_carried_as_inherited_provenance_only": True,
            "phase9j_public_report_validated": phase9j_gate_ok,
        },
        "confirmation_summary": {
            "phase9k_commit_confirmed": confirmations.get("phase9k_commit_confirmed") is True,
            "phase9k_ci_confirmed": confirmations.get("phase9k_ci_confirmed") is True,
            "phase9k_status_confirmed": confirmations.get("phase9k_status_confirmed") is True,
            "phase9k_protocol_freeze_confirmed": confirmations.get("phase9k_protocol_freeze_confirmed") is True,
            "phase9h_commit_confirmed": confirmations.get("phase9h_commit_confirmed") is True,
            "phase9h_ci_confirmed": confirmations.get("phase9h_ci_confirmed") is True,
            "phase9h_status_confirmed": confirmations.get("phase9h_status_confirmed") is True,
            "phase9i_commit_confirmed": confirmations.get("phase9i_commit_confirmed") is True,
            "phase9i_ci_confirmed": confirmations.get("phase9i_ci_confirmed") is True,
            "phase9i_status_confirmed": confirmations.get("phase9i_status_confirmed") is True,
            "phase9j_commit_confirmed": confirmations.get("phase9j_commit_confirmed") is True,
            "phase9j_ci_confirmed": confirmations.get("phase9j_ci_confirmed") is True,
            "phase9j_status_confirmed": confirmations.get("phase9j_status_confirmed") is True,
            "read_phase9j_private_annotation_input_rows_confirmed": confirmations.get("read_phase9j_private_annotation_input_rows_confirmed") is True,
            "ignored_runs_workspace_confirmed": confirmations.get("ignored_runs_workspace_confirmed") is True,
            "private_output_only_confirmed": confirmations.get("private_output_only_confirmed") is True,
            "aggregate_public_report_only_confirmed": confirmations.get("aggregate_public_report_only_confirmed") is True,
            "no_scoring_or_evidence_success_until_separate_boundary_confirmed": confirmations.get("no_scoring_or_evidence_success_until_separate_boundary_confirmed") is True,
            "no_provider_llm_model_default_runtime_product_change_confirmed": confirmations.get("no_provider_llm_model_default_runtime_product_change_confirmed") is True,
            "no_network_fetch_clone_source_refresh_confirmed": confirmations.get("no_network_fetch_clone_source_refresh_confirmed") is True,
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
        },
        "outcome_acquisition_execution_summary": {
            "publication_level": "aggregate_bucketed_outcome_acquisition_only",
            "outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication": True,
            "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
            "annotation_input_metadata_remains_routing_precondition_not_benchmark_truth": True,
            "private_output_under_ignored_runs_only": True,
            "phase9j_private_annotation_input_read_under_ignored_runs": private_annotation_input_read and acquisition_executed,
            "outcome_packets_generated_under_ignored_runs_only": acquisition_executed,
            "outcome_acquisition_fields_frozen_from_phase9k_protocol_only": True,
            "inherited_phase9h_aggregate_caps_respected": caps_ok,
            "outcome_packet_schema_validation_passed": schema_ok,
            "attempted_bucket": state_buckets["attempted_bucket"],
            "acquired_bucket": state_buckets["acquired_bucket"],
            "unavailable_bucket": state_buckets["unavailable_bucket"],
            "invalid_bucket": state_buckets["invalid_bucket"],
            "replacement_needed_bucket": state_buckets["replacement_needed_bucket"],
            "readiness_bucket": state_buckets["readiness_bucket"],
            "distinct_sources_bucket": _bucket_sources(distinct_sources),
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
        },
        "conservative_recommendation": (
            "outcome_acquisition_packets_are_acquisition_state_only"
            "_not_scoring_not_adjudication_not_evidence_success"
            "_future_scoring_and_adjudication_require_separate_frozen_boundary"
            "_no_method_product_claim"
        ),
    }


# ---------------------------------------------------------------------------
# Public report privacy scan + validation
# ---------------------------------------------------------------------------

def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


# Strict allowed-key schema for the public report.
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
        "phase9f_remote_provenance_bucketed": None,
    },
    "phase9g_inherited_provenance": {
        "phase9g_ci_success": None,
        "phase9g_status": None,
        "phase9g_protocol_freeze": None,
        "phase9g_remote_provenance_bucketed": None,
        "phase9g_carried_as_inherited_provenance_only": None,
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
        "phase9k_gate_required_before_phase9l": None,
        "phase9k_public_report_validated": None,
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
        "phase9h_gate_required_before_phase9l": None,
        "phase9h_public_report_validated": None,
    },
    "phase9i_gate_references": {
        "phase9i_commit": None,
        "phase9i_ci_run": None,
        "phase9i_ci_success": None,
        "phase9i_status": None,
        "phase9i_protocol_freeze": None,
        "phase9i_annotation_protocol_frozen": None,
        "phase9i_gate_required_before_phase9l": None,
        "phase9i_carried_as_inherited_provenance_only": None,
        "phase9i_public_report_validated": None,
    },
    "phase9j_gate_references": {
        "phase9j_commit": None,
        "phase9j_ci_run": None,
        "phase9j_ci_success": None,
        "phase9j_status": None,
        "phase9j_annotation_input_rows_generated": None,
        "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": None,
        "phase9j_gate_required_before_phase9l": None,
        "phase9j_carried_as_inherited_provenance_only": None,
        "phase9j_public_report_validated": None,
    },
    "confirmation_summary": {
        "phase9k_commit_confirmed": None,
        "phase9k_ci_confirmed": None,
        "phase9k_status_confirmed": None,
        "phase9k_protocol_freeze_confirmed": None,
        "phase9h_commit_confirmed": None,
        "phase9h_ci_confirmed": None,
        "phase9h_status_confirmed": None,
        "phase9i_commit_confirmed": None,
        "phase9i_ci_confirmed": None,
        "phase9i_status_confirmed": None,
        "phase9j_commit_confirmed": None,
        "phase9j_ci_confirmed": None,
        "phase9j_status_confirmed": None,
        "read_phase9j_private_annotation_input_rows_confirmed": None,
        "ignored_runs_workspace_confirmed": None,
        "private_output_only_confirmed": None,
        "aggregate_public_report_only_confirmed": None,
        "no_scoring_or_evidence_success_until_separate_boundary_confirmed": None,
        "no_provider_llm_model_default_runtime_product_change_confirmed": None,
        "no_network_fetch_clone_source_refresh_confirmed": None,
        "all_required_confirmations_present": None,
        "dry_self_test_and_report_validation_read_private_runs": None,
        "dry_self_test_and_report_validation_fetch_or_clone": None,
    },
    "outcome_acquisition_execution_summary": {
        "publication_level": None,
        "outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication": None,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": None,
        "annotation_input_metadata_remains_routing_precondition_not_benchmark_truth": None,
        "private_output_under_ignored_runs_only": None,
        "phase9j_private_annotation_input_read_under_ignored_runs": None,
        "outcome_packets_generated_under_ignored_runs_only": None,
        "outcome_acquisition_fields_frozen_from_phase9k_protocol_only": None,
        "inherited_phase9h_aggregate_caps_respected": None,
        "outcome_packet_schema_validation_passed": None,
        "attempted_bucket": None,
        "acquired_bucket": None,
        "unavailable_bucket": None,
        "invalid_bucket": None,
        "replacement_needed_bucket": None,
        "readiness_bucket": None,
        "distinct_sources_bucket": None,
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

    # Phase 9F inherited provenance (bucketed only)
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
    if prov9f.get("phase9f_remote_provenance_bucketed") is not True:
        errors.append("Phase 9F inherited remote provenance must be bucketed")

    # Phase 9G inherited provenance (bucketed only)
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

    # Phase 9K gate references
    gate9k = report.get("phase9k_gate_references", {})
    if gate9k.get("phase9k_commit") != PHASE9K_COMMIT:
        errors.append("Phase 9K commit gate reference drift")
    if gate9k.get("phase9k_ci_run") != PHASE9K_CI_RUN:
        errors.append("Phase 9K CI run gate reference drift")
    if gate9k.get("phase9k_ci_success") is not True:
        errors.append("Phase 9K CI success gate missing")
    if gate9k.get("phase9k_status") != PHASE9K_STATUS:
        errors.append("Phase 9K status gate reference drift")
    if gate9k.get("phase9k_protocol_freeze") is not True:
        errors.append("Phase 9K protocol freeze gate missing")
    if gate9k.get("phase9k_outcome_acquisition_protocol_frozen") is not True:
        errors.append("Phase 9K outcome-acquisition protocol frozen boundary missing")
    if gate9k.get("phase9k_not_proof_outcome_or_scoring_or_evidence_success_works") is not True:
        errors.append("Phase 9K not-proof boundary missing")
    if gate9k.get("phase9k_did_not_acquire_outcomes_or_score_or_adjudicate_or_generate_gold_rows") is not True:
        errors.append("Phase 9K no-generation boundary missing")
    if gate9k.get("phase9k_gate_required_before_phase9l") is not True:
        errors.append("Phase 9K gate-required boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        if gate9k.get("phase9k_public_report_validated") is not True:
            errors.append("Phase 9K public report validated gate missing")

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
    if gate9h.get("phase9h_gate_required_before_phase9l") is not True:
        errors.append("Phase 9H gate-required boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        if gate9h.get("phase9h_public_report_validated") is not True:
            errors.append("Phase 9H public report validated gate missing")

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
    if gate9i.get("phase9i_gate_required_before_phase9l") is not True:
        errors.append("Phase 9I gate-required boundary missing")
    if gate9i.get("phase9i_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9I provenance-only boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        if gate9i.get("phase9i_public_report_validated") is not True:
            errors.append("Phase 9I public report validated gate missing")

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
    if gate9j.get("phase9j_gate_required_before_phase9l") is not True:
        errors.append("Phase 9J gate-required boundary missing")
    if gate9j.get("phase9j_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9J provenance-only boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        if gate9j.get("phase9j_public_report_validated") is not True:
            errors.append("Phase 9J public report validated gate missing")

    # Confirmation summary
    confirm = report.get("confirmation_summary", {})
    required_confirm_keys = (
        "phase9k_commit_confirmed",
        "phase9k_ci_confirmed",
        "phase9k_status_confirmed",
        "phase9k_protocol_freeze_confirmed",
        "phase9h_commit_confirmed",
        "phase9h_ci_confirmed",
        "phase9h_status_confirmed",
        "phase9i_commit_confirmed",
        "phase9i_ci_confirmed",
        "phase9i_status_confirmed",
        "phase9j_commit_confirmed",
        "phase9j_ci_confirmed",
        "phase9j_status_confirmed",
        "read_phase9j_private_annotation_input_rows_confirmed",
        "ignored_runs_workspace_confirmed",
        "private_output_only_confirmed",
        "aggregate_public_report_only_confirmed",
        "no_scoring_or_evidence_success_until_separate_boundary_confirmed",
        "no_provider_llm_model_default_runtime_product_change_confirmed",
        "no_network_fetch_clone_source_refresh_confirmed",
    )
    for key in required_confirm_keys:
        if confirm.get(key) is not True:
            errors.append(f"confirmation missing: {key}")
    if confirm.get("all_required_confirmations_present") is not True:
        errors.append("all_required_confirmations_present boundary missing")
    if confirm.get("dry_self_test_and_report_validation_read_private_runs") is not False:
        errors.append("self-test/validate-report private-runs read boundary failed")
    if confirm.get("dry_self_test_and_report_validation_fetch_or_clone") is not False:
        errors.append("self-test/validate-report fetch/clone boundary failed")

    # Outcome-acquisition execution summary
    oae = report.get("outcome_acquisition_execution_summary", {})
    if oae.get("publication_level") != "aggregate_bucketed_outcome_acquisition_only":
        errors.append("outcome acquisition execution publication level drift")
    if oae.get("outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication") is not True:
        errors.append("outcome acquisition state-only boundary missing")
    if oae.get("no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels") is not True:
        errors.append("outcome acquisition no-scoring/adjudication boundary missing")
    if oae.get("annotation_input_metadata_remains_routing_precondition_not_benchmark_truth") is not True:
        errors.append("outcome acquisition routing-precondition boundary missing")
    if oae.get("private_output_under_ignored_runs_only") is not True:
        errors.append("outcome acquisition private output boundary missing")
    if oae.get("outcome_acquisition_fields_frozen_from_phase9k_protocol_only") is not True:
        errors.append("outcome acquisition frozen-fields boundary missing")
    if report.get("status") == STATUS_EXECUTED:
        if oae.get("attempted_bucket") != "bucket_target_48_to_72":
            errors.append("executed status outside target attempted bucket")
        if oae.get("outcome_packets_generated_under_ignored_runs_only") is not True:
            errors.append("executed status requires outcome packets generated under ignored runs")
        if oae.get("phase9j_private_annotation_input_read_under_ignored_runs") is not True:
            errors.append("executed status requires Phase 9J private annotation input read")
        if oae.get("inherited_phase9h_aggregate_caps_respected") is not True:
            errors.append("executed status requires aggregate caps respected")
        if oae.get("outcome_packet_schema_validation_passed") is not True:
            errors.append("executed status requires outcome packet schema validation passed")
        # Oracle must-fix: an executed Phase 9L public report MUST be
        # unavailable-only and validator-enforced (non-optional).  Under this
        # boundary authorized reads cannot acquire outcome observables (Phase
        # 9J annotation-input rows are routing/precondition metadata only;
        # Phase 9H materialized sources and evidence-acquisition method
        # execution are NOT authorized here), so every generated packet is
        # unavailable under the Phase 9K frozen rule
        # ``missing_outcome_handled_as_unavailable_not_as_failure_or_success``.
        # A mutated report claiming nonzero acquired outcomes, an
        # unavailable/invalid mismatch, replacement drift, or readiness drift
        # MUST be rejected.
        if oae.get("acquired_bucket") != "bucket_zero":
            errors.append(
                "executed status requires acquired_bucket bucket_zero "
                "(unavailable-only; no outcome observable acquired)"
            )
        if oae.get("unavailable_bucket") != "bucket_target_48_to_72":
            errors.append(
                "executed status requires unavailable_bucket bucket_target_48_to_72 "
                "(unavailable-only; all packets unavailable)"
            )
        if oae.get("invalid_bucket") != "bucket_zero":
            errors.append(
                "executed status requires invalid_bucket bucket_zero "
                "(unavailable-only; no invalid packets)"
            )
        if oae.get("replacement_needed_bucket") != "bucket_zero":
            errors.append(
                "executed status requires replacement_needed_bucket bucket_zero "
                "(unavailable-only; no replacement needed)"
            )
        if oae.get("readiness_bucket") != OUTCOME_ACQUISITION_READINESS_BUCKET:
            errors.append(
                "executed status requires readiness_bucket "
                "bucket_outcome_observable_unavailable_within_boundary "
                "(unavailable-only; readiness drift rejected)"
            )

    # Privacy summary
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

    # Validation summary
    validation = report.get("validation_summary", {})
    for key in (
        "route_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "public_artifact_privacy_audit_expected",
        "validator_does_not_fetch_or_read_private",
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

    # No-claim boundary
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("no_claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    # Forbidden execution boundary
    for key in NO_EXECUTION_FALSE_KEYS:
        if report.get("forbidden_execution_boundary", {}).get(key) is not False:
            errors.append(f"forbidden execution boundary failed: {key}")

    # Conservative recommendation
    if report.get("conservative_recommendation") != (
        "outcome_acquisition_packets_are_acquisition_state_only"
        "_not_scoring_not_adjudication_not_evidence_success"
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
        return False, "report path is not under the Phase 9L public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------

def _all_confirmations_dict(
    confirm_phase9k_commit: str | None,
    confirm_phase9k_ci: str | None,
    confirm_phase9k_status: str | None,
    confirm_phase9k_protocol_freeze: bool,
    confirm_phase9h_commit: str | None,
    confirm_phase9h_ci: str | None,
    confirm_phase9h_status: str | None,
    confirm_phase9i_commit: str | None,
    confirm_phase9i_ci: str | None,
    confirm_phase9i_status: str | None,
    confirm_phase9j_commit: str | None,
    confirm_phase9j_ci: str | None,
    confirm_phase9j_status: str | None,
    confirm_read_phase9j_private_annotation_input_rows: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_no_scoring_or_evidence_success_until_separate_boundary: bool,
    confirm_no_provider_llm_model_default_runtime_product_change: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
) -> dict[str, bool]:
    return {
        "phase9k_commit_confirmed": confirm_phase9k_commit == PHASE9K_COMMIT,
        "phase9k_ci_confirmed": confirm_phase9k_ci == PHASE9K_CI_RUN,
        "phase9k_status_confirmed": confirm_phase9k_status == PHASE9K_STATUS,
        "phase9k_protocol_freeze_confirmed": confirm_phase9k_protocol_freeze is True,
        "phase9h_commit_confirmed": confirm_phase9h_commit == PHASE9H_COMMIT,
        "phase9h_ci_confirmed": confirm_phase9h_ci == PHASE9H_CI_RUN,
        "phase9h_status_confirmed": confirm_phase9h_status == PHASE9H_STATUS,
        "phase9i_commit_confirmed": confirm_phase9i_commit == PHASE9I_COMMIT,
        "phase9i_ci_confirmed": confirm_phase9i_ci == PHASE9I_CI_RUN,
        "phase9i_status_confirmed": confirm_phase9i_status == PHASE9I_STATUS,
        "phase9j_commit_confirmed": confirm_phase9j_commit == PHASE9J_COMMIT,
        "phase9j_ci_confirmed": confirm_phase9j_ci == PHASE9J_CI_RUN,
        "phase9j_status_confirmed": confirm_phase9j_status == PHASE9J_STATUS,
        "read_phase9j_private_annotation_input_rows_confirmed": confirm_read_phase9j_private_annotation_input_rows is True,
        "ignored_runs_workspace_confirmed": confirm_ignored_runs_workspace is True,
        "private_output_only_confirmed": confirm_private_output_only is True,
        "aggregate_public_report_only_confirmed": confirm_aggregate_public_report_only is True,
        "no_scoring_or_evidence_success_until_separate_boundary_confirmed": confirm_no_scoring_or_evidence_success_until_separate_boundary is True,
        "no_provider_llm_model_default_runtime_product_change_confirmed": confirm_no_provider_llm_model_default_runtime_product_change is True,
        "no_network_fetch_clone_source_refresh_confirmed": confirm_no_network_fetch_clone_source_refresh is True,
    }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _empty_aggregate() -> dict[str, Any]:
    return {
        "outcome_packets_total": 0,
        "acquired_total": 0,
        "unavailable_total": 0,
        "invalid_total": 0,
        "replacement_needed_total": 0,
        "distinct_sources_with_outcome_packets": 0,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
    }


def execute_phase9l(
    private_run_dir: Path,
    public_report: Path,
    confirm_phase9k_commit: str | None,
    confirm_phase9k_ci: str | None,
    confirm_phase9k_status: str | None,
    confirm_phase9k_protocol_freeze: bool,
    confirm_phase9h_commit: str | None,
    confirm_phase9h_ci: str | None,
    confirm_phase9h_status: str | None,
    confirm_phase9i_commit: str | None,
    confirm_phase9i_ci: str | None,
    confirm_phase9i_status: str | None,
    confirm_phase9j_commit: str | None,
    confirm_phase9j_ci: str | None,
    confirm_phase9j_status: str | None,
    confirm_read_phase9j_private_annotation_input_rows: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_no_scoring_or_evidence_success_until_separate_boundary: bool,
    confirm_no_provider_llm_model_default_runtime_product_change: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
) -> dict[str, Any]:
    confirmations = _all_confirmations_dict(
        confirm_phase9k_commit, confirm_phase9k_ci, confirm_phase9k_status,
        confirm_phase9k_protocol_freeze,
        confirm_phase9h_commit, confirm_phase9h_ci, confirm_phase9h_status,
        confirm_phase9i_commit, confirm_phase9i_ci, confirm_phase9i_status,
        confirm_phase9j_commit, confirm_phase9j_ci, confirm_phase9j_status,
        confirm_read_phase9j_private_annotation_input_rows,
        confirm_ignored_runs_workspace,
        confirm_private_output_only,
        confirm_aggregate_public_report_only,
        confirm_no_scoring_or_evidence_success_until_separate_boundary,
        confirm_no_provider_llm_model_default_runtime_product_change,
        confirm_no_network_fetch_clone_source_refresh,
    )
    missing = [name for name, ok in confirmations.items() if not ok]
    if missing:
        raise ValueError("missing required confirmation(s): " + ", ".join(missing))

    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    public_report.parent.mkdir(parents=True, exist_ok=True)

    # Validate Phase 9K + 9H + 9I + 9J gates (read tracked public reports only).
    phase9k_errors = _phase9k_gate_errors(
        supplied_commit=confirm_phase9k_commit,
        supplied_ci=confirm_phase9k_ci,
        supplied_status=confirm_phase9k_status,
    )
    phase9h_errors = _phase9h_gate_errors(
        supplied_commit=confirm_phase9h_commit,
        supplied_ci=confirm_phase9h_ci,
        supplied_status=confirm_phase9h_status,
    )
    phase9i_errors = _phase9i_gate_errors(
        supplied_commit=confirm_phase9i_commit,
        supplied_ci=confirm_phase9i_ci,
        supplied_status=confirm_phase9i_status,
    )
    phase9j_errors = _phase9j_gate_errors(
        supplied_commit=confirm_phase9j_commit,
        supplied_ci=confirm_phase9j_ci,
        supplied_status=confirm_phase9j_status,
    )
    phase9k_gate_ok = not phase9k_errors
    phase9h_gate_ok = not phase9h_errors
    phase9i_gate_ok = not phase9i_errors
    phase9j_gate_ok = not phase9j_errors

    if not (phase9k_gate_ok and phase9h_gate_ok and phase9i_gate_ok and phase9j_gate_ok):
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9k_gate_ok, phase9h_gate_ok, phase9i_gate_ok,
            phase9j_gate_ok, confirmations, private_annotation_input_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated gate-missing report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9l_gate_missing_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9k_or_phase9h_or_phase9i_or_phase9j_gate_missing_or_not_green",
                "phase9k_gate_errors_private": phase9k_errors,
                "phase9h_gate_errors_private": phase9h_errors,
                "phase9i_gate_errors_private": phase9i_errors,
                "phase9j_gate_errors_private": phase9j_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["outcome_acquisition_execution_summary"]["attempted_bucket"],
            "public_unavailable_bucket": report["outcome_acquisition_execution_summary"]["unavailable_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Locate and read the Phase 9J private annotation-input under ignored runs/.
    annotation_loc = _find_phase9j_private_annotation_input()
    if annotation_loc is None:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9k_gate_ok, phase9h_gate_ok, phase9i_gate_ok,
            phase9j_gate_ok, confirmations, private_annotation_input_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated no-annotation-input report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9l_no_annotation_input_manifest.json").write_text(
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
            "public_attempted_bucket": report["outcome_acquisition_execution_summary"]["attempted_bucket"],
            "public_unavailable_bucket": report["outcome_acquisition_execution_summary"]["unavailable_bucket"],
            "private_output_under_ignored_runs": True,
        }

    manifest_path, rows_path = annotation_loc
    manifest, annotation_rows, read_errors = _read_phase9j_private_annotation_input(
        manifest_path, rows_path
    )
    if read_errors or not annotation_rows:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9k_gate_ok, phase9h_gate_ok, phase9i_gate_ok,
            phase9j_gate_ok, confirmations, private_annotation_input_read=False,
            outcome_packet_errors=read_errors or ["no_valid_annotation_input_rows"],
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated annotation-input-shape-invalid report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9l_annotation_input_shape_invalid_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9j_private_annotation_input_shape_invalid_or_empty",
                "annotation_input_read_errors_private": read_errors or ["no_valid_annotation_input_rows"],
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["outcome_acquisition_execution_summary"]["attempted_bucket"],
            "public_unavailable_bucket": report["outcome_acquisition_execution_summary"]["unavailable_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Generate outcome-acquisition packets from the Phase 9J annotation-input
    # rows.  The outcome acquisition state is ``unavailable`` for every row
    # because the outcome observable cannot be acquired from authorized reads
    # alone within this boundary (Phase 9K frozen rule: missing outcome =
    # unavailable, not failure or success).
    outcome_packets, packet_errors = _generate_outcome_packets(annotation_rows)
    if packet_errors:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9k_gate_ok, phase9h_gate_ok, phase9i_gate_ok,
            phase9j_gate_ok, confirmations, private_annotation_input_read=True,
            outcome_packet_errors=packet_errors,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated outcome-packet-invalid report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9l_outcome_packet_invalid_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "outcome_packet_schema_violation",
                "outcome_packet_errors_private": packet_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_attempted_bucket": report["outcome_acquisition_execution_summary"]["attempted_bucket"],
            "public_unavailable_bucket": report["outcome_acquisition_execution_summary"]["unavailable_bucket"],
            "private_output_under_ignored_runs": True,
        }

    private_manifest = _build_private_manifest(
        outcome_packets, manifest.get("aggregate_private_totals", {}),
    )
    aggregate = private_manifest["aggregate_private_totals"]

    report = build_public_report(
        aggregate, phase9k_gate_ok, phase9h_gate_ok, phase9i_gate_ok,
        phase9j_gate_ok, confirmations, private_annotation_input_read=True,
    )
    errors = validate_report(report)
    if errors:
        raise ValueError(
            "generated public report invalid: " + "; ".join(errors[:12])
        )

    private_run_dir.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_phase9l_outcome_acquisition_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (private_run_dir / "private_phase9l_outcome_acquisition_packets.json").write_text(
        json.dumps(outcome_packets, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    public_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": report["status"],
        "public_report": str(public_report),
        "public_attempted_bucket": report["outcome_acquisition_execution_summary"]["attempted_bucket"],
        "public_unavailable_bucket": report["outcome_acquisition_execution_summary"]["unavailable_bucket"],
        "private_output_under_ignored_runs": True,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _synthetic_annotation_input_row(index: int) -> dict[str, Any]:
    """Build a synthetic Phase 9J annotation-input row for self-test fixtures."""
    return {
        "private_candidate_ref": f"synthetic_ref_{index}",
        "source_order_index_private": index % MIN_DISTINCT_SOURCES,
        "candidate_order_index_private": index,
        "task_eligibility_input": (
            "eligible_for_future_annotation_acquisition"
            "_routing_precondition_only_not_benchmark_truth"
        ),
        "evidence_localization_requirement": "file_localized_code_evidence_required",
        "expected_evidence_form": "file_path_and_line_range_only_no_snippet_stored",
        "outcome_acquisition_preconditions": (
            "future_separate_boundary_required_no_outcomes_in_phase9j"
        ),
        "adjudication_rules": "frozen_in_phase9i_protocol_not_executed_in_phase9j",
        "rejection_or_replacement_rules_before_scoring": "next_deterministic_candidate",
        "annotation_input_is_routing_precondition_only_not_benchmark_truth": True,
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": True,
    }


def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_FILE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS, NETWORK_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_FILE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    NETWORK_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    full_confirmations = _all_confirmations_dict(
        PHASE9K_COMMIT, PHASE9K_CI_RUN, PHASE9K_STATUS, True,
        PHASE9H_COMMIT, PHASE9H_CI_RUN, PHASE9H_STATUS,
        PHASE9I_COMMIT, PHASE9I_CI_RUN, PHASE9I_STATUS,
        PHASE9J_COMMIT, PHASE9J_CI_RUN, PHASE9J_STATUS,
        True, True, True, True, True, True, True,
    )

    # --- valid executed report (pass) ---
    executed_aggregate = {
        "outcome_packets_total": 49,
        "acquired_total": 0,
        "unavailable_total": 49,
        "invalid_total": 0,
        "replacement_needed_total": 0,
        "distinct_sources_with_outcome_packets": 8,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": True,
        "diversity_minimum_met": True,
    }
    executed_report = build_public_report(
        executed_aggregate, True, True, True, True, full_confirmations,
        private_annotation_input_read=True,
    )
    checks.append(("valid_executed_report_passes", not validate_report(executed_report)))
    checks.append(("executed_report_is_executed_status", executed_report["status"] == STATUS_EXECUTED))

    # --- valid repair report (zero outcome packets) ---
    repair_aggregate = _empty_aggregate()
    repair_report = build_public_report(
        repair_aggregate, True, True, True, True, full_confirmations,
        private_annotation_input_read=False,
    )
    checks.append(("valid_repair_report_passes", not validate_report(repair_report)))
    checks.append(("repair_report_is_repair_status", repair_report["status"] == STATUS_REPAIR))

    # --- valid gate-missing report ---
    gate_missing_report = build_public_report(
        repair_aggregate, False, False, False, False, full_confirmations,
        private_annotation_input_read=False,
    )
    checks.append(("valid_gate_missing_report_passes", not validate_report(gate_missing_report)))
    checks.append(("gate_missing_report_is_gate_missing_status", gate_missing_report["status"] == STATUS_GATE_MISSING))

    # --- base report still valid ---
    checks.append(("base_report_valid", not validate_report(executed_report)))

    # --- Oracle must-fix: executed report with nonzero acquired bucket rejected ---
    # A mutated otherwise-valid executed public report claiming nonzero acquired
    # outcomes MUST fail validation (unavailable-only is non-optional).
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["acquired_bucket"] = "bucket_target_48_to_72"
    checks.append(("executed_nonzero_acquired_bucket_rejected", bool(validate_report(mutated))))

    # --- executed report with unavailable bucket mismatch rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["unavailable_bucket"] = "bucket_zero"
    checks.append(("executed_unavailable_bucket_mismatch_rejected", bool(validate_report(mutated))))

    # --- executed report with nonzero invalid bucket rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["invalid_bucket"] = "bucket_target_48_to_72"
    checks.append(("executed_nonzero_invalid_bucket_rejected", bool(validate_report(mutated))))

    # --- executed report with nonzero replacement_needed bucket rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["replacement_needed_bucket"] = "bucket_target_48_to_72"
    checks.append(("executed_nonzero_replacement_needed_bucket_rejected", bool(validate_report(mutated))))

    # --- executed report with readiness bucket drift rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["readiness_bucket"] = (
        "bucket_outcome_observable_acquired_within_boundary"
    )
    checks.append(("executed_readiness_bucket_drift_rejected", bool(validate_report(mutated))))

    # --- executed report with acquired+unavailable both nonzero rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["acquired_bucket"] = "bucket_nonzero_below_minimum"
    mutated["outcome_acquisition_execution_summary"]["unavailable_bucket"] = "bucket_at_least_minimum_below_target"
    checks.append(("executed_acquired_and_unavailable_mismatch_rejected", bool(validate_report(mutated))))

    # --- executed report with acquired bucket nonzero and unavailable zero rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["acquired_bucket"] = "bucket_target_48_to_72"
    mutated["outcome_acquisition_execution_summary"]["unavailable_bucket"] = "bucket_zero"
    checks.append(("executed_acquired_nonzero_unavailable_zero_rejected", bool(validate_report(mutated))))

    # --- missing confirmation blocks execution ---
    confirmation_labels = (
        ("missing_confirm_phase9k_commit", dict(confirm_phase9k_commit=None)),
        ("missing_confirm_phase9k_ci", dict(confirm_phase9k_ci=None)),
        ("missing_confirm_phase9k_status", dict(confirm_phase9k_status=None)),
        ("missing_confirm_phase9k_protocol_freeze", dict(confirm_phase9k_protocol_freeze=False)),
        ("missing_confirm_phase9h_commit", dict(confirm_phase9h_commit=None)),
        ("missing_confirm_phase9h_ci", dict(confirm_phase9h_ci=None)),
        ("missing_confirm_phase9h_status", dict(confirm_phase9h_status=None)),
        ("missing_confirm_phase9i_commit", dict(confirm_phase9i_commit=None)),
        ("missing_confirm_phase9i_ci", dict(confirm_phase9i_ci=None)),
        ("missing_confirm_phase9i_status", dict(confirm_phase9i_status=None)),
        ("missing_confirm_phase9j_commit", dict(confirm_phase9j_commit=None)),
        ("missing_confirm_phase9j_ci", dict(confirm_phase9j_ci=None)),
        ("missing_confirm_phase9j_status", dict(confirm_phase9j_status=None)),
        ("missing_confirm_read_phase9j_annotation_input", dict(confirm_read_phase9j_private_annotation_input_rows=False)),
        ("missing_confirm_ignored_runs_workspace", dict(confirm_ignored_runs_workspace=False)),
        ("missing_confirm_private_output_only", dict(confirm_private_output_only=False)),
        ("missing_confirm_aggregate_public_report_only", dict(confirm_aggregate_public_report_only=False)),
        ("missing_confirm_no_scoring_evidence_success", dict(confirm_no_scoring_or_evidence_success_until_separate_boundary=False)),
        ("missing_confirm_no_provider_llm_model", dict(confirm_no_provider_llm_model_default_runtime_product_change=False)),
        ("missing_confirm_no_network_fetch_clone", dict(confirm_no_network_fetch_clone_source_refresh=False)),
    )
    for label, overrides in confirmation_labels:
        kwargs = dict(
            confirm_phase9k_commit=PHASE9K_COMMIT,
            confirm_phase9k_ci=PHASE9K_CI_RUN,
            confirm_phase9k_status=PHASE9K_STATUS,
            confirm_phase9k_protocol_freeze=True,
            confirm_phase9h_commit=PHASE9H_COMMIT,
            confirm_phase9h_ci=PHASE9H_CI_RUN,
            confirm_phase9h_status=PHASE9H_STATUS,
            confirm_phase9i_commit=PHASE9I_COMMIT,
            confirm_phase9i_ci=PHASE9I_CI_RUN,
            confirm_phase9i_status=PHASE9I_STATUS,
            confirm_phase9j_commit=PHASE9J_COMMIT,
            confirm_phase9j_ci=PHASE9J_CI_RUN,
            confirm_phase9j_status=PHASE9J_STATUS,
            confirm_read_phase9j_private_annotation_input_rows=True,
            confirm_ignored_runs_workspace=True,
            confirm_private_output_only=True,
            confirm_aggregate_public_report_only=True,
            confirm_no_scoring_or_evidence_success_until_separate_boundary=True,
            confirm_no_provider_llm_model_default_runtime_product_change=True,
            confirm_no_network_fetch_clone_source_refresh=True,
        )
        kwargs.update(overrides)
        try:
            execute_phase9l(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, **kwargs)
            checks.append((f"{label}_rejected", False))
        except ValueError as exc:
            checks.append((f"{label}_rejected", "missing required confirmation" in str(exc)))

    # --- tracked/private path rejected (path scope fail-closed) ---
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_tracked_output")
        checks.append(("tracked_output_path_rejected", False))
    except ValueError as exc:
        checks.append(("tracked_output_path_rejected", "runs" in str(exc)))

    # --- Phase 9K/9H/9I/9J gate validation ---
    checks.append((
        "wrong_phase9k_commit_rejected",
        bool(_phase9k_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9K_CI_RUN, supplied_status=PHASE9K_STATUS)),
    ))
    checks.append((
        "wrong_phase9k_ci_rejected",
        bool(_phase9k_gate_errors(supplied_commit=PHASE9K_COMMIT, supplied_ci="0000", supplied_status=PHASE9K_STATUS)),
    ))
    checks.append((
        "wrong_phase9k_status_rejected",
        bool(_phase9k_gate_errors(supplied_commit=PHASE9K_COMMIT, supplied_ci=PHASE9K_CI_RUN, supplied_status="drift")),
    ))
    checks.append((
        "wrong_phase9h_commit_rejected",
        bool(_phase9h_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9H_CI_RUN, supplied_status=PHASE9H_STATUS)),
    ))
    checks.append((
        "wrong_phase9i_commit_rejected",
        bool(_phase9i_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9I_CI_RUN, supplied_status=PHASE9I_STATUS)),
    ))
    checks.append((
        "wrong_phase9j_commit_rejected",
        bool(_phase9j_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9J_CI_RUN, supplied_status=PHASE9J_STATUS)),
    ))

    # --- Phase 9J private manifest shape validation ---
    valid_phase9j_manifest = {
        "phase": PHASE9J_PHASE,
        "annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": True,
        "annotation_input_rows_private": [],
        "aggregate_private_totals": {"annotation_input_rows_total": 0},
    }
    checks.append(("valid_phase9j_manifest_shape_passes", not _validate_phase9j_manifest_shape(valid_phase9j_manifest)))
    bad_phase9j_manifest = {"phase": "drift"}
    checks.append(("invalid_phase9j_manifest_shape_rejected", bool(_validate_phase9j_manifest_shape(bad_phase9j_manifest))))

    # --- Phase 9J annotation-input row shape validation ---
    valid_ann_row = _synthetic_annotation_input_row(0)
    checks.append(("valid_phase9j_row_shape_passes", not _validate_phase9j_row_shape(valid_ann_row, 0)))
    bad_ann_input_row = {"private_candidate_ref": "abc123"}
    checks.append(("invalid_phase9j_row_shape_rejected", bool(_validate_phase9j_row_shape(bad_ann_input_row, 0))))

    # --- outcome-acquisition packet generation + validation ---
    packet = _generate_outcome_packet(valid_ann_row, 0)
    checks.append(("valid_outcome_packet_passes", not _validate_outcome_packet(packet, 0)))
    checks.append((
        "outcome_packet_is_acquisition_state_only",
        packet["outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication"]
        if "outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication" in packet
        else packet["no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels"] is True
    ))
    checks.append(("outcome_packet_state_is_unavailable", packet["outcome_acquisition_state"] == "unavailable"))
    checks.append(("outcome_packet_observable_not_acquired", packet["outcome_observable_acquired"] is False))
    checks.append(("outcome_packet_replacement_not_needed", packet["replacement_needed"] is False))

    # --- outcome packet with extra/forbidden field rejected ---
    bad_packet = dict(packet)
    bad_packet["gold_answer"] = "hidden"
    checks.append(("outcome_packet_extra_field_rejected", bool(_validate_outcome_packet(bad_packet, 0))))

    bad_packet2 = dict(packet)
    del bad_packet2["outcome_acquisition_state"]
    checks.append(("outcome_packet_missing_field_rejected", bool(_validate_outcome_packet(bad_packet2, 0))))

    bad_packet3 = dict(packet)
    bad_packet3["score_value"] = 42
    checks.append(("outcome_packet_scoring_field_rejected", bool(_validate_outcome_packet(bad_packet3, 0))))

    bad_packet4 = dict(packet)
    bad_packet4["correctness"] = True
    checks.append(("outcome_packet_correctness_field_rejected", bool(_validate_outcome_packet(bad_packet4, 0))))

    bad_packet5 = dict(packet)
    bad_packet5["no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels"] = False
    checks.append(("outcome_packet_boundary_false_rejected", bool(_validate_outcome_packet(bad_packet5, 0))))

    # --- outcome packet invalid state requires replacement_needed ---
    invalid_packet = dict(packet)
    invalid_packet["outcome_acquisition_state"] = "invalid"
    invalid_packet["replacement_needed"] = False
    checks.append(("invalid_state_without_replacement_rejected", bool(_validate_outcome_packet(invalid_packet, 0))))
    invalid_packet2 = dict(packet)
    invalid_packet2["outcome_acquisition_state"] = "invalid"
    invalid_packet2["replacement_needed"] = True
    checks.append(("invalid_state_with_replacement_passes", not _validate_outcome_packet(invalid_packet2, 0)))

    # --- outcome packet with bad acquisition state rejected ---
    bad_state_packet = dict(packet)
    bad_state_packet["outcome_acquisition_state"] = "scored"
    checks.append(("bad_acquisition_state_rejected", bool(_validate_outcome_packet(bad_state_packet, 0))))

    # --- outcome packet generation from multiple annotation-input rows ---
    ann_rows = [_synthetic_annotation_input_row(i) for i in range(5)]
    packets, gen_errors = _generate_outcome_packets(ann_rows)
    checks.append(("outcome_packet_generation_no_errors", not gen_errors))
    checks.append(("outcome_packet_generation_count_matches", len(packets) == 5))
    checks.append(("all_generated_packets_unavailable", all(p["outcome_acquisition_state"] == "unavailable" for p in packets)))

    # --- strict schema: unknown top-level/nested fields rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["phase9k_gate_references"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_gate_field_rejected", bool(validate_report(mutated))))

    # --- private-shaped public fields rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["example_value"] = "https://example.invalid/repo.git"
    checks.append(("url_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["example_value"] = "owner/repo"
    checks.append(("owner_repo_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["privacy_summary"]["per_source_public_facts"] = True
    checks.append(("per_source_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["privacy_summary"]["per_task_public_facts"] = True
    checks.append(("per_task_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["privacy_summary"]["outcome_packets_public"] = True
    checks.append(("outcome_packets_public_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["privacy_summary"]["outcome_observables_public"] = True
    checks.append(("outcome_observables_public_rejected", bool(validate_report(mutated))))

    # --- private-shaped keys rejected ---
    for bad_key in ("private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket", "per_task_summary", "source_path_bucket"):
        mutated = copy.deepcopy(executed_report)
        mutated["outcome_acquisition_execution_summary"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- singleton buckets rejected ---
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(executed_report)
        mutated["outcome_acquisition_execution_summary"]["example_bucket"] = singleton_val
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))

    # --- forbidden outcome/scoring/evidence/gold/correctness keys rejected ---
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(executed_report)
        mutated["outcome_acquisition_execution_summary"][bad_key] = "exposed_value"
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    # --- forbidden execution boundary true rejected ---
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(executed_report)
        mutated["forbidden_execution_boundary"][exec_key] = True
        checks.append((f"{exec_key}_true_rejected", bool(validate_report(mutated))))

    # --- claim boundary true rejected ---
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(executed_report)
        mutated["no_claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- forbidden claim phrases rejected ---
    forbidden_claims = (
        "method effectiveness", "product readiness", "scoring success",
        "outcome success", "adjudication success", "evaluation works",
        "task annotation readiness", "outcome acquisition works",
        "outcome acquisition succeeded",
    )
    for phrase in forbidden_claims:
        mutated = copy.deepcopy(executed_report)
        mutated["outcome_acquisition_execution_summary"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_')}_rejected", bool(validate_report(mutated))))

    # --- forbidden standalone status wording rejected (success/validated/benchmark/gold/correctness) ---
    for bad_word in ("success", "validated", "benchmark", "gold", "correctness"):
        mutated = copy.deepcopy(executed_report)
        mutated["outcome_acquisition_execution_summary"]["example_note"] = f"this is {bad_word} here"
        checks.append((f"forbidden_status_wording_{bad_word}_rejected", bool(validate_report(mutated))))

    # --- exact count field rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["count"] = 49
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    # --- gate-reference path whitelist: non-whitelisted key with ci-run value rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["task_ci_run"] = "28981994749"
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(validate_report(mutated))))

    # --- long decimal CI/run-shaped values rejected except on whitelisted gate paths ---
    mutated = copy.deepcopy(executed_report)
    mutated["outcome_acquisition_execution_summary"]["acquired_bucket"] = "28981994749"
    errors = validate_report(mutated)
    checks.append(("long_decimal_in_allowed_non_gate_field_rejected", bool(errors)))
    checks.append((
        "long_decimal_rejection_cites_decimal",
        any("long decimal" in e for e in errors),
    ))

    # Gate CI run values on the exact whitelisted gate paths remain valid.
    checks.append(("gate_ci_run_values_on_whitelisted_paths_valid", not validate_report(executed_report)))

    # --- validate-report path fail-closed ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9l" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "other_phase" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase9l" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # --- temp-file round-trip validation ---
    with tempfile.TemporaryDirectory(prefix="phase9l_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(executed_report), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- self-test does not fetch/read private ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_files", SOURCE_FILE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9j_private_annotation_input", PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS == 0))
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
        description="Phase 9L outcome acquisition (no scoring, no adjudication, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--confirm-phase9k-commit")
    parser.add_argument("--confirm-phase9k-ci")
    parser.add_argument("--confirm-phase9k-status")
    parser.add_argument("--confirm-phase9k-protocol-freeze", action="store_true")
    parser.add_argument("--confirm-phase9h-commit")
    parser.add_argument("--confirm-phase9h-ci")
    parser.add_argument("--confirm-phase9h-status")
    parser.add_argument("--confirm-phase9i-commit")
    parser.add_argument("--confirm-phase9i-ci")
    parser.add_argument("--confirm-phase9i-status")
    parser.add_argument("--confirm-phase9j-commit")
    parser.add_argument("--confirm-phase9j-ci")
    parser.add_argument("--confirm-phase9j-status")
    parser.add_argument("--confirm-read-phase9j-private-annotation-input-rows", action="store_true")
    parser.add_argument("--confirm-ignored-runs-workspace", action="store_true")
    parser.add_argument("--confirm-private-output-only", action="store_true")
    parser.add_argument("--confirm-aggregate-public-report-only", action="store_true")
    parser.add_argument("--confirm-no-scoring-or-evidence-success-until-separate-boundary", action="store_true")
    parser.add_argument("--confirm-no-provider-llm-model-default-runtime-product-change", action="store_true")
    parser.add_argument("--confirm-no-network-fetch-clone-source-refresh", action="store_true")
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
        result = execute_phase9l(
            args.private_run_dir,
            args.output,
            args.confirm_phase9k_commit,
            args.confirm_phase9k_ci,
            args.confirm_phase9k_status,
            args.confirm_phase9k_protocol_freeze,
            args.confirm_phase9h_commit,
            args.confirm_phase9h_ci,
            args.confirm_phase9h_status,
            args.confirm_phase9i_commit,
            args.confirm_phase9i_ci,
            args.confirm_phase9i_status,
            args.confirm_phase9j_commit,
            args.confirm_phase9j_ci,
            args.confirm_phase9j_status,
            args.confirm_read_phase9j_private_annotation_input_rows,
            args.confirm_ignored_runs_workspace,
            args.confirm_private_output_only,
            args.confirm_aggregate_public_report_only,
            args.confirm_no_scoring_or_evidence_success_until_separate_boundary,
            args.confirm_no_provider_llm_model_default_runtime_product_change,
            args.confirm_no_network_fetch_clone_source_refresh,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
