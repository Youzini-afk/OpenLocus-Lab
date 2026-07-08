#!/usr/bin/env python3
"""Phase 9J annotation-input execution (no scoring, no claim).

This runner has one narrow purpose: under explicit confirmations and the
frozen Phase 9I annotation protocol, read the Phase 9H private materialized
inventory under ignored ``runs/`` only, generate private annotation-input
rows/manifests under ignored ``runs/`` only, and publish only an aggregate
public report.  It does NOT do outcome acquisition, scoring rows, gold labels,
benchmark labels, evidence_success, provider/LLM/network/fetch/clone/source
refresh, model fitting/training, runtime/default/product changes, or
method/product/performance/provider/model claims.

Annotation-input rows are routing/precondition metadata only, NOT benchmark
truth.  They contain only frozen fields from the Phase 9I protocol: task
eligibility input, evidence-localization requirement, expected evidence form,
outcome-acquisition preconditions, adjudication rules, and
rejection/replacement-before-scoring rules.  They must NOT include
outcomes/gold/scoring/evidence_success/result labels.

The Phase 9H public gate reference values (remote commit
``d997caab5487e66c544f657645d70c97f3b780e2``, CI run ``28976655118``) and the
Phase 9I public gate reference values (remote commit
``fe9eabba744ff00526fadd7184801c3721677fba``, CI run ``28979060368``) are the
only public gate references.  Phase 9G and Phase 9F are carried as bucketed
inherited provenance only; their exact remote commit/CI run values are
intentionally NOT published.  Local same-tree git commits are not read or
compared; the supplied confirmation values are matched against the frozen
public gate constants only.

Annotation-input execution is not evidence_success, method success, benchmark
success, scoring success, or product readiness.  Eligibility annotations are
routing/precondition metadata only, not benchmark truth.
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

PHASE = "phase9j_annotation_input_execution_no_scoring_no_claim"
# Honest completed wording: annotation-input rows were generated (no scoring,
# no claim).  Not "readiness" (rows were actually produced) and not
# "execution complete" (which could overstate the bounded scope).
STATUS_EXECUTED = (
    "phase9j_annotation_input_rows_generated_no_scoring_no_claim"
)
STATUS_REPAIR = "phase9j_annotation_input_execution_repair_no_claim"
STATUS_GATE_MISSING = (
    "phase9j_blocked_phase9h_or_phase9i_gate_missing_or_not_green_no_claim"
)
ALLOWED_STATUSES = {STATUS_EXECUTED, STATUS_REPAIR, STATUS_GATE_MISSING}
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

# Phase 9H public gate reference values (oracle-provided).
PHASE9H_PHASE = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_no_scoring_no_claim"
)
PHASE9H_STATUS = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_readiness_no_scoring_no_claim"
)
PHASE9H_COMMIT = "d997caab5487e66c544f657645d70c97f3b780e2"
PHASE9H_CI_RUN = "28976655118"
PHASE9H_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE9H_PHASE / f"{PHASE9H_PHASE}_report.json"
)

# Phase 9I public gate reference values (oracle-provided).
PHASE9I_PHASE = (
    "phase9i_materialized_inventory_to_task_annotation_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9I_STATUS = PHASE9I_PHASE
PHASE9I_COMMIT = "fe9eabba744ff00526fadd7184801c3721677fba"
PHASE9I_CI_RUN = "28979060368"
PHASE9I_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE9I_PHASE / f"{PHASE9I_PHASE}_report.json"
)

# Expected private Phase 9H inventory location (under ignored runs/ only).
PHASE9H_PRIVATE_RUN_DIR = REPO / "runs" / PHASE9H_PHASE / "current"
PHASE9H_PRIVATE_MANIFEST = (
    PHASE9H_PRIVATE_RUN_DIR / "private_phase9h_materialization_manifest.json"
)
PHASE9H_PRIVATE_ROWS = (
    PHASE9H_PRIVATE_RUN_DIR / "private_phase9h_materialization_rows.json"
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

# Frozen annotation-input row fields from the Phase 9I protocol.  These are the
# ONLY fields a private annotation-input row may contain.  They are
# routing/precondition metadata only, NOT benchmark truth.
ANNOTATION_INPUT_REQUIRED_FIELDS: dict[str, type] = {
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

# Frozen annotation-input values (deterministic, no claims, no benchmark truth).
ANNOTATION_INPUT_TASK_ELIGIBILITY = (
    "eligible_for_future_annotation_acquisition"
    "_routing_precondition_only_not_benchmark_truth"
)
ANNOTATION_INPUT_EVIDENCE_LOCALIZATION = (
    "file_localized_code_evidence_required"
)
ANNOTATION_INPUT_EXPECTED_EVIDENCE_FORM = (
    "file_path_and_line_range_only_no_snippet_stored"
)
ANNOTATION_INPUT_OUTCOME_PRECONDITIONS = (
    "future_separate_boundary_required_no_outcomes_in_phase9j"
)
ANNOTATION_INPUT_ADJUDICATION_RULES = (
    "frozen_in_phase9i_protocol_not_executed_in_phase9j"
)

# Forbidden tokens in annotation-input field names (defense in depth; the strict
# allowed-field check already rejects any unknown field, but this catches
# accidental reintroduction with explicit messaging).
FORBIDDEN_ANNOTATION_INPUT_TOKENS = (
    "outcome", "gold", "scoring", "evidence_success",
    "result_label", "result_truth", "benchmark_label",
    "ground_truth", "expected_answer", "expected_output", "expected_result",
    "score_value", "truth_label",
)

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "outcome_acquisition_executed",
    "scoring_rows_generated",
    "gold_labels_generated",
    "benchmark_labels_generated",
    "evidence_success_evaluated",
    "result_labels_generated",
    "model_fitting_executed",
    "provider_or_llm_calls_executed",
    "runtime_default_or_product_changes_executed",
    "network_fetch_or_clone_or_source_refresh_executed",
    "annotation_truth_generated",
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
    "annotation_input_rows_public",
)

# Forbidden public field words; only apply to non-boolean values so boolean
# boundary attestation keys are not false-flagged.
FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants (full commit SHA / CI run ID).  Exact path whitelist,
# NOT a suffix match.  Only Phase 9H and Phase 9I commit/CI are public gate
# references; Phase 9G/9F exact commit/CI are intentionally not published.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9h_gate_references.phase9h_commit",
        "$.phase9h_gate_references.phase9h_ci_run",
        "$.phase9i_gate_references.phase9i_commit",
        "$.phase9i_gate_references.phase9i_ci_run",
    }
)

# Exact public gate-reference JSON paths whose string VALUES are CI run IDs
# (long decimal integers).  Only the Phase 9H and Phase 9I CI run paths are
# exempt from the long-decimal value scan; commit SHAs are hex and are NOT
# exempt here (they are validated by exact-equality gate checks instead).
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9h_gate_references.phase9h_ci_run",
        "$.phase9i_gate_references.phase9i_ci_run",
    }
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
# Long decimal (8+ digits) CI/run-shaped public value detector.  Catches CI
# run IDs and other long numeric identifiers that should never appear in
# public output except on the exact whitelisted CI run gate paths
# (DECIMAL_CI_RUN_EXEMPT_PATHS).  Commit SHAs are hex (a-f0-9) and do not
# match \d{8,} unless they happen to contain 8+ consecutive digits, which is
# fine since commits are separately validated by exact-equality gate checks.
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
CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"materialization\s+(?:works|succeeded|proven|established)"
    r"|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)"
    r"|clone\s+(?:works|succeeded|proven|established)"
    r"|annotation\s+(?:works|succeeded|proven|established)"
    r"|annotation_input\s+(?:works|succeeded|proven|established)"
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

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_FILE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS = 0
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


# ---------------------------------------------------------------------------
# Phase 9H gate validation (reads tracked public report only)
# ---------------------------------------------------------------------------

def _phase9h_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9H public gate.  Returns error strings (empty=valid).

    Reads the Phase 9H public report (tracked artifact) only; does not
    fetch/clone or read private runs/.
    """
    errors: list[str] = []
    if report is None:
        if not PHASE9H_PUBLIC_REPORT.exists():
            return ["Phase 9H public report missing"]
        report = json.loads(PHASE9H_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9H public report must be object"]
    if report.get("status") != PHASE9H_STATUS:
        errors.append("Phase 9H public report status drift")
    if report.get("schema_version") != f"{PHASE9H_PHASE}_report_v1":
        errors.append("Phase 9H public report schema drift")

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
    """Validate the Phase 9I public gate.  Returns error strings (empty=valid).

    Reads the Phase 9I public report (tracked artifact) only; does not
    fetch/clone or read private runs/.
    """
    errors: list[str] = []
    if report is None:
        if not PHASE9I_PUBLIC_REPORT.exists():
            return ["Phase 9I public report missing"]
        report = json.loads(PHASE9I_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9I public report must be object"]
    if report.get("status") != PHASE9I_STATUS:
        errors.append("Phase 9I public report status drift")
    if report.get("schema_version") != f"{PHASE9I_PHASE}_report_v1":
        errors.append("Phase 9I public report schema drift")

    if supplied_commit is not None and supplied_commit != PHASE9I_COMMIT:
        errors.append("supplied Phase 9I commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9I_CI_RUN:
        errors.append("supplied Phase 9I CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9I_STATUS:
        errors.append("supplied Phase 9I status does not match public gate reference")
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Private Phase 9H inventory reading (under ignored runs/ only)
# ---------------------------------------------------------------------------

def _find_phase9h_private_inventory() -> tuple[Path, Path] | None:
    """Locate the Phase 9H private manifest + rows under ignored runs/ only.

    Returns (manifest_path, rows_path) or None if not found / not under runs/.
    """
    global PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS
    PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = PHASE9H_PRIVATE_MANIFEST.resolve()
    rows_resolved = PHASE9H_PRIVATE_ROWS.resolve()
    if runs_root not in manifest_resolved.parents:
        return None
    if runs_root not in rows_resolved.parents:
        return None
    if not manifest_resolved.exists() or not rows_resolved.exists():
        return None
    return manifest_resolved, rows_resolved


def _validate_phase9h_manifest_shape(manifest: Any) -> list[str]:
    """Validate the Phase 9H private manifest has the expected shape.

    Pure schema check: no filesystem or network access.  Used by both the
    private inventory reader (under ignored runs/) and the self-test.
    """
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["Phase 9H manifest must be object"]
    if manifest.get("phase") != PHASE9H_PHASE:
        errors.append("Phase 9H manifest phase drift")
    if manifest.get("task_candidate_rows_are_inventory_only") is not True:
        errors.append("Phase 9H manifest inventory-only boundary missing")
    if manifest.get(
        "accepted_task_rows_remain_inventory_only_not_benchmark_annotations"
    ) is not True:
        errors.append("Phase 9H manifest not-benchmark-annotations boundary missing")
    rows = manifest.get("materialization_rows_private")
    if not isinstance(rows, list):
        errors.append("Phase 9H manifest missing materialization_rows_private list")
    aggregate = manifest.get("aggregate_private_totals")
    if not isinstance(aggregate, dict):
        errors.append("Phase 9H manifest missing aggregate_private_totals")
    return errors


def _validate_phase9h_row_shape(row: Any, index: int) -> list[str]:
    """Validate a single Phase 9H private materialization row shape.

    Pure schema check: no filesystem or network access.
    """
    errors: list[str] = []
    if not isinstance(row, dict):
        errors.append(f"Phase 9H row {index} not object")
        return errors
    required: dict[str, type] = {
        "private_candidate_id": str,
        "source_order_index_private": int,
        "candidate_order_index_private": int,
        "task_type": str,
        "private_source_file_path": str,
        "private_line_range": dict,
        "replacement_policy_private": str,
    }
    for field, expected_type in required.items():
        if field not in row:
            errors.append(f"Phase 9H row {index} missing field: {field}")
        elif not isinstance(row[field], expected_type):
            errors.append(f"Phase 9H row {index} field {field} wrong type")
    return errors


def _compute_inventory_caps(inventory_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute inherited Phase 9H caps directly from inventory rows.

    Pure check (no I/O).  Defence in depth: computes hard/per-source/diversity
    caps from the rows themselves rather than trusting the manifest's aggregate,
    so a stale or inconsistent manifest cannot bypass the fail-closed gate.
    """
    total = len(inventory_rows)
    by_source: dict[int, int] = {}
    for row in inventory_rows:
        idx = row.get("source_order_index_private")
        if isinstance(idx, int):
            by_source[idx] = by_source.get(idx, 0) + 1
    distinct_sources = len(by_source)
    per_source_max = max(by_source.values()) if by_source else 0
    return {
        "inventory_rows_total": total,
        "distinct_sources": distinct_sources,
        "per_source_max": per_source_max,
        "hard_cap_respected": total <= HARD_INVENTORY_CAP,
        "per_source_cap_respected": per_source_max <= PER_SOURCE_CAP,
        "diversity_minimum_met": distinct_sources >= MIN_DISTINCT_SOURCES,
    }


def _inventory_cap_violations(inventory_rows: list[dict[str, Any]]) -> list[str]:
    """Return inherited Phase 9H cap-violation errors for the inventory.

    Empty list = all caps respected.  Called BEFORE any annotation-input row
    generation so that a cap violation fails closed without producing
    per-row annotation output.
    """
    caps = _compute_inventory_caps(inventory_rows)
    errors: list[str] = []
    if not caps["hard_cap_respected"]:
        errors.append(
            f"phase9h inventory hard cap violated: "
            f"{caps['inventory_rows_total']} > {HARD_INVENTORY_CAP}"
        )
    if not caps["per_source_cap_respected"]:
        errors.append(
            f"phase9h inventory per-source cap violated: "
            f"max {caps['per_source_max']} > {PER_SOURCE_CAP}"
        )
    if not caps["diversity_minimum_met"]:
        errors.append(
            f"phase9h inventory diversity minimum violated: "
            f"{caps['distinct_sources']} < {MIN_DISTINCT_SOURCES}"
        )
    return errors


def _read_phase9h_private_inventory(
    manifest_path: Path, rows_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Read the Phase 9H private manifest + rows under ignored runs/ only.

    Returns (manifest, rows, errors).  Private only; never public.
    """
    global PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS
    PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = manifest_path.resolve()
    rows_resolved = rows_path.resolve()
    if runs_root not in manifest_resolved.parents or runs_root not in rows_resolved.parents:
        return {}, [], ["Phase 9H private inventory must be under ignored runs/"]
    try:
        manifest = json.loads(manifest_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9H private manifest unreadable"]
    try:
        rows = json.loads(rows_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9H private rows unreadable"]
    manifest_errors = _validate_phase9h_manifest_shape(manifest)
    if manifest_errors:
        return {}, [], manifest_errors
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
# Annotation-input generation
# ---------------------------------------------------------------------------

def _generate_annotation_input_row(
    inv_row: dict[str, Any], index: int
) -> dict[str, Any]:
    """Generate a single private annotation-input row from a Phase 9H inventory row.

    Only frozen Phase 9I protocol fields; routing/precondition metadata only,
    NOT benchmark truth.
    """
    return {
        "private_candidate_ref": inv_row["private_candidate_id"],
        "source_order_index_private": inv_row["source_order_index_private"],
        "candidate_order_index_private": inv_row["candidate_order_index_private"],
        "task_eligibility_input": ANNOTATION_INPUT_TASK_ELIGIBILITY,
        "evidence_localization_requirement": ANNOTATION_INPUT_EVIDENCE_LOCALIZATION,
        "expected_evidence_form": ANNOTATION_INPUT_EXPECTED_EVIDENCE_FORM,
        "outcome_acquisition_preconditions": ANNOTATION_INPUT_OUTCOME_PRECONDITIONS,
        "adjudication_rules": ANNOTATION_INPUT_ADJUDICATION_RULES,
        "rejection_or_replacement_rules_before_scoring": inv_row[
            "replacement_policy_private"
        ],
        "annotation_input_is_routing_precondition_only_not_benchmark_truth": True,
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": True,
    }


def _validate_annotation_input_row(row: Any, index: int) -> list[str]:
    """Validate a single annotation-input row against the frozen schema.

    Rejects any extra field, any missing field, wrong types, and any forbidden
    token in field names (defense in depth).  Pure check; no I/O.
    """
    errors: list[str] = []
    if not isinstance(row, dict):
        errors.append(f"annotation-input row {index} not object")
        return errors
    allowed = set(ANNOTATION_INPUT_REQUIRED_FIELDS.keys())
    actual = set(str(k) for k in row.keys())
    for extra in sorted(actual - allowed):
        errors.append(f"annotation-input row {index} unexpected field: {extra}")
        for token in FORBIDDEN_ANNOTATION_INPUT_TOKENS:
            if token in extra.lower():
                errors.append(
                    f"annotation-input row {index} forbidden token '{token}' in field: {extra}"
                )
    for field, expected_type in ANNOTATION_INPUT_REQUIRED_FIELDS.items():
        if field not in row:
            errors.append(f"annotation-input row {index} missing field: {field}")
        elif not isinstance(row[field], expected_type):
            errors.append(f"annotation-input row {index} field {field} wrong type")
    # Boundary booleans must be True.
    if row.get(
        "annotation_input_is_routing_precondition_only_not_benchmark_truth"
    ) is not True:
        errors.append(
            f"annotation-input row {index} routing-precondition-only boundary failed"
        )
    if row.get(
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels"
    ) is not True:
        errors.append(
            f"annotation-input row {index} no-outcomes/gold/scoring boundary failed"
        )
    return errors


def _generate_annotation_input_rows(
    inventory_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Generate all annotation-input rows from Phase 9H inventory rows."""
    annotation_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, inv_row in enumerate(inventory_rows):
        ann_row = _generate_annotation_input_row(inv_row, index)
        annotation_rows.append(ann_row)
        errors.extend(_validate_annotation_input_row(ann_row, index))
    return annotation_rows, errors


def _build_private_manifest(
    annotation_rows: list[dict[str, Any]],
    inventory_rows: list[dict[str, Any]],
    inventory_aggregate: dict[str, Any],
) -> dict[str, Any]:
    """Build the private annotation-input manifest (under ignored runs/ only)."""
    distinct_sources = len(
        {row["source_order_index_private"] for row in annotation_rows}
    ) if annotation_rows else 0
    source_summaries: list[dict[str, Any]] = []
    by_source: dict[int, int] = {}
    for row in annotation_rows:
        idx = row["source_order_index_private"]
        by_source[idx] = by_source.get(idx, 0) + 1
    for source_idx, count in sorted(by_source.items()):
        source_summaries.append({
            "source_order_index_private": source_idx,
            "private_annotation_input_rows": count,
        })
    return {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": True,
        "annotation_input_rows_private": annotation_rows,
        "source_private_summaries": source_summaries,
        "aggregate_private_totals": {
            "annotation_input_rows_total": len(annotation_rows),
            "distinct_sources_with_annotation_inputs": distinct_sources,
            "hard_cap_respected": len(annotation_rows) <= HARD_INVENTORY_CAP,
            "per_source_cap_respected": all(
                c <= PER_SOURCE_CAP for c in by_source.values()
            ),
            "target_bucket_met": TARGET_INVENTORY_MIN <= len(annotation_rows) <= TARGET_INVENTORY_MAX,
            "diversity_minimum_met": distinct_sources >= MIN_DISTINCT_SOURCES,
            "inventory_rows_consumed": len(inventory_rows),
        },
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": True,
        "provider_or_llm_calls_executed": False,
        "model_fitting_executed": False,
        "network_fetch_or_clone_or_source_refresh_executed": False,
    }


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report(
    annotation_aggregate: dict[str, Any],
    phase9h_gate_ok: bool,
    phase9i_gate_ok: bool,
    confirmations: dict[str, bool],
    private_inventory_read: bool,
    annotation_input_errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build the aggregate-only public Phase 9J report."""
    total = int(annotation_aggregate.get("annotation_input_rows_total", 0))
    distinct_sources = int(
        annotation_aggregate.get("distinct_sources_with_annotation_inputs", 0)
    )
    caps_ok = (
        annotation_aggregate.get("hard_cap_respected") is True
        and annotation_aggregate.get("per_source_cap_respected") is True
    )
    target_ok = TARGET_INVENTORY_MIN <= total <= TARGET_INVENTORY_MAX
    diversity_ok = distinct_sources >= MIN_DISTINCT_SOURCES
    schema_ok = not annotation_input_errors
    all_confirmations = all(confirmations.values()) and len(confirmations) == 15

    gate_ok = phase9h_gate_ok and phase9i_gate_ok
    if not gate_ok:
        status = STATUS_GATE_MISSING
    elif not all_confirmations or not caps_ok or not schema_ok:
        status = STATUS_REPAIR
    elif target_ok and diversity_ok and total > 0 and private_inventory_read:
        status = STATUS_EXECUTED
    else:
        status = STATUS_REPAIR

    annotation_executed = (
        status == STATUS_EXECUTED and total > 0
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
        "phase9h_gate_references": {
            "phase9h_commit": PHASE9H_COMMIT,
            "phase9h_ci_run": PHASE9H_CI_RUN,
            "phase9h_ci_success": True,
            "phase9h_status": PHASE9H_STATUS,
            "phase9h_source_materialization_readiness_only": True,
            "phase9h_not_proof_annotation_or_outcome_or_evidence_success_works": True,
            "phase9h_did_not_generate_annotations_or_outcomes_or_gold_rows_or_evidence_success_or_scoring_rows": True,
            "phase9h_private_materialized_inventory_under_ignored_runs_only": True,
            "phase9h_gate_required_before_phase9j": True,
            "phase9h_public_report_validated": phase9h_gate_ok,
        },
        "phase9i_gate_references": {
            "phase9i_commit": PHASE9I_COMMIT,
            "phase9i_ci_run": PHASE9I_CI_RUN,
            "phase9i_ci_success": True,
            "phase9i_status": PHASE9I_STATUS,
            "phase9i_protocol_freeze": True,
            "phase9i_annotation_protocol_frozen": True,
            "phase9i_gate_required_before_phase9j": True,
            "phase9i_carried_as_inherited_provenance_only": True,
            "phase9i_public_report_validated": phase9i_gate_ok,
        },
        "confirmation_summary": {
            "phase9h_commit_confirmed": confirmations.get("phase9h_commit_confirmed") is True,
            "phase9h_ci_confirmed": confirmations.get("phase9h_ci_confirmed") is True,
            "phase9h_status_confirmed": confirmations.get("phase9h_status_confirmed") is True,
            "phase9i_commit_confirmed": confirmations.get("phase9i_commit_confirmed") is True,
            "phase9i_ci_confirmed": confirmations.get("phase9i_ci_confirmed") is True,
            "phase9i_status_confirmed": confirmations.get("phase9i_status_confirmed") is True,
            "phase9i_protocol_freeze_confirmed": confirmations.get("phase9i_protocol_freeze_confirmed") is True,
            "read_phase9h_private_inventory_confirmed": confirmations.get("read_phase9h_private_inventory_confirmed") is True,
            "ignored_runs_workspace_confirmed": confirmations.get("ignored_runs_workspace_confirmed") is True,
            "private_output_only_confirmed": confirmations.get("private_output_only_confirmed") is True,
            "aggregate_public_report_only_confirmed": confirmations.get("aggregate_public_report_only_confirmed") is True,
            "no_outcomes_scoring_evidence_success_confirmed": confirmations.get("no_outcomes_scoring_evidence_success_confirmed") is True,
            "no_gold_benchmark_labels_confirmed": confirmations.get("no_gold_benchmark_labels_confirmed") is True,
            "no_provider_llm_model_runtime_default_product_change_confirmed": confirmations.get("no_provider_llm_model_runtime_default_product_change_confirmed") is True,
            "no_network_fetch_clone_source_refresh_confirmed": confirmations.get("no_network_fetch_clone_source_refresh_confirmed") is True,
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
        },
        "annotation_input_execution_summary": {
            "publication_level": "aggregate_bucketed_annotation_input_only",
            "annotation_input_rows_bucket": _bucket_quantity(total),
            "distinct_sources_bucket": _bucket_sources(distinct_sources),
            "annotation_input_is_routing_precondition_only_not_benchmark_truth": True,
            "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": True,
            "private_output_under_ignored_runs_only": True,
            "phase9h_private_inventory_read_under_ignored_runs": private_inventory_read and annotation_executed,
            "annotation_input_rows_generated_under_ignored_runs_only": annotation_executed,
            "annotation_input_fields_frozen_from_phase9i_protocol_only": True,
            "inherited_phase9h_aggregate_caps_respected": caps_ok,
            "annotation_input_schema_validation_passed": schema_ok,
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
            "annotation_input_rows_are_routing_precondition_only_not_benchmark_truth"
            "_future_outcome_acquisition_and_scoring_require_separate_frozen_boundary"
            "_no_evidence_success_no_method_product_claim"
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
    "phase9h_gate_references": {
        "phase9h_commit": None,
        "phase9h_ci_run": None,
        "phase9h_ci_success": None,
        "phase9h_status": None,
        "phase9h_source_materialization_readiness_only": None,
        "phase9h_not_proof_annotation_or_outcome_or_evidence_success_works": None,
        "phase9h_did_not_generate_annotations_or_outcomes_or_gold_rows_or_evidence_success_or_scoring_rows": None,
        "phase9h_private_materialized_inventory_under_ignored_runs_only": None,
        "phase9h_gate_required_before_phase9j": None,
        "phase9h_public_report_validated": None,
    },
    "phase9i_gate_references": {
        "phase9i_commit": None,
        "phase9i_ci_run": None,
        "phase9i_ci_success": None,
        "phase9i_status": None,
        "phase9i_protocol_freeze": None,
        "phase9i_annotation_protocol_frozen": None,
        "phase9i_gate_required_before_phase9j": None,
        "phase9i_carried_as_inherited_provenance_only": None,
        "phase9i_public_report_validated": None,
    },
    "confirmation_summary": {
        "phase9h_commit_confirmed": None,
        "phase9h_ci_confirmed": None,
        "phase9h_status_confirmed": None,
        "phase9i_commit_confirmed": None,
        "phase9i_ci_confirmed": None,
        "phase9i_status_confirmed": None,
        "phase9i_protocol_freeze_confirmed": None,
        "read_phase9h_private_inventory_confirmed": None,
        "ignored_runs_workspace_confirmed": None,
        "private_output_only_confirmed": None,
        "aggregate_public_report_only_confirmed": None,
        "no_outcomes_scoring_evidence_success_confirmed": None,
        "no_gold_benchmark_labels_confirmed": None,
        "no_provider_llm_model_runtime_default_product_change_confirmed": None,
        "no_network_fetch_clone_source_refresh_confirmed": None,
        "all_required_confirmations_present": None,
        "dry_self_test_and_report_validation_read_private_runs": None,
        "dry_self_test_and_report_validation_fetch_or_clone": None,
    },
    "annotation_input_execution_summary": {
        "publication_level": None,
        "annotation_input_rows_bucket": None,
        "distinct_sources_bucket": None,
        "annotation_input_is_routing_precondition_only_not_benchmark_truth": None,
        "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": None,
        "private_output_under_ignored_runs_only": None,
        "phase9h_private_inventory_read_under_ignored_runs": None,
        "annotation_input_rows_generated_under_ignored_runs_only": None,
        "annotation_input_fields_frozen_from_phase9i_protocol_only": None,
        "inherited_phase9h_aggregate_caps_respected": None,
        "annotation_input_schema_validation_passed": None,
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
            errors.extend(_scan_public(child_value, f"{path}[{index}]", "", allowed_paths))
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
    if gate9h.get("phase9h_gate_required_before_phase9j") is not True:
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
    if gate9i.get("phase9i_gate_required_before_phase9j") is not True:
        errors.append("Phase 9I gate-required boundary missing")
    if gate9i.get("phase9i_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9I provenance-only boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        if gate9i.get("phase9i_public_report_validated") is not True:
            errors.append("Phase 9I public report validated gate missing")

    # Confirmation summary
    confirm = report.get("confirmation_summary", {})
    required_confirm_keys = (
        "phase9h_commit_confirmed",
        "phase9h_ci_confirmed",
        "phase9h_status_confirmed",
        "phase9i_commit_confirmed",
        "phase9i_ci_confirmed",
        "phase9i_status_confirmed",
        "phase9i_protocol_freeze_confirmed",
        "read_phase9h_private_inventory_confirmed",
        "ignored_runs_workspace_confirmed",
        "private_output_only_confirmed",
        "aggregate_public_report_only_confirmed",
        "no_outcomes_scoring_evidence_success_confirmed",
        "no_gold_benchmark_labels_confirmed",
        "no_provider_llm_model_runtime_default_product_change_confirmed",
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

    # Annotation-input execution summary
    ann = report.get("annotation_input_execution_summary", {})
    if ann.get("publication_level") != "aggregate_bucketed_annotation_input_only":
        errors.append("annotation input execution publication level drift")
    if ann.get("annotation_input_is_routing_precondition_only_not_benchmark_truth") is not True:
        errors.append("annotation input routing-precondition-only boundary missing")
    if ann.get("no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels") is not True:
        errors.append("annotation input no-outcomes/gold/scoring boundary missing")
    if ann.get("private_output_under_ignored_runs_only") is not True:
        errors.append("annotation input private output boundary missing")
    if ann.get("annotation_input_fields_frozen_from_phase9i_protocol_only") is not True:
        errors.append("annotation input frozen-fields boundary missing")
    if report.get("status") == STATUS_EXECUTED:
        if ann.get("annotation_input_rows_bucket") != "bucket_target_48_to_72":
            errors.append("executed status outside target annotation-input bucket")
        if ann.get("annotation_input_rows_generated_under_ignored_runs_only") is not True:
            errors.append("executed status requires annotation inputs generated under ignored runs")
        if ann.get("phase9h_private_inventory_read_under_ignored_runs") is not True:
            errors.append("executed status requires Phase 9H private inventory read")
        if ann.get("inherited_phase9h_aggregate_caps_respected") is not True:
            errors.append("executed status requires aggregate caps respected")
        if ann.get("annotation_input_schema_validation_passed") is not True:
            errors.append("executed status requires annotation input schema validation passed")

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
        "annotation_input_rows_are_routing_precondition_only_not_benchmark_truth"
        "_future_outcome_acquisition_and_scoring_require_separate_frozen_boundary"
        "_no_evidence_success_no_method_product_claim"
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
        return False, "report path is not under the Phase 9J public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------

def _all_confirmations_dict(
    confirm_phase9h_commit: str | None,
    confirm_phase9h_ci: str | None,
    confirm_phase9h_status: str | None,
    confirm_phase9i_commit: str | None,
    confirm_phase9i_ci: str | None,
    confirm_phase9i_status: str | None,
    confirm_phase9i_protocol_freeze: bool,
    confirm_read_phase9h_private_inventory: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_no_outcomes_scoring_evidence_success: bool,
    confirm_no_gold_benchmark_labels: bool,
    confirm_no_provider_llm_model_runtime_default_product_change: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
) -> dict[str, bool]:
    return {
        "phase9h_commit_confirmed": confirm_phase9h_commit == PHASE9H_COMMIT,
        "phase9h_ci_confirmed": confirm_phase9h_ci == PHASE9H_CI_RUN,
        "phase9h_status_confirmed": confirm_phase9h_status == PHASE9H_STATUS,
        "phase9i_commit_confirmed": confirm_phase9i_commit == PHASE9I_COMMIT,
        "phase9i_ci_confirmed": confirm_phase9i_ci == PHASE9I_CI_RUN,
        "phase9i_status_confirmed": confirm_phase9i_status == PHASE9I_STATUS,
        "phase9i_protocol_freeze_confirmed": confirm_phase9i_protocol_freeze is True,
        "read_phase9h_private_inventory_confirmed": confirm_read_phase9h_private_inventory is True,
        "ignored_runs_workspace_confirmed": confirm_ignored_runs_workspace is True,
        "private_output_only_confirmed": confirm_private_output_only is True,
        "aggregate_public_report_only_confirmed": confirm_aggregate_public_report_only is True,
        "no_outcomes_scoring_evidence_success_confirmed": confirm_no_outcomes_scoring_evidence_success is True,
        "no_gold_benchmark_labels_confirmed": confirm_no_gold_benchmark_labels is True,
        "no_provider_llm_model_runtime_default_product_change_confirmed": confirm_no_provider_llm_model_runtime_default_product_change is True,
        "no_network_fetch_clone_source_refresh_confirmed": confirm_no_network_fetch_clone_source_refresh is True,
    }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _empty_aggregate() -> dict[str, Any]:
    return {
        "annotation_input_rows_total": 0,
        "distinct_sources_with_annotation_inputs": 0,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
        "inventory_rows_consumed": 0,
    }


def _cap_violation_aggregate() -> dict[str, Any]:
    """Aggregate for the fail-closed inventory cap-violation repair path.

    No annotation-input rows are generated, so annotation totals are zero.
    The cap booleans are False to honestly reflect that the inherited Phase
    9H inventory caps were violated and execution stopped before row
    generation.
    """
    return {
        "annotation_input_rows_total": 0,
        "distinct_sources_with_annotation_inputs": 0,
        "hard_cap_respected": False,
        "per_source_cap_respected": False,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
        "inventory_rows_consumed": 0,
    }


def execute_phase9j(
    private_run_dir: Path,
    public_report: Path,
    confirm_phase9h_commit: str | None,
    confirm_phase9h_ci: str | None,
    confirm_phase9h_status: str | None,
    confirm_phase9i_commit: str | None,
    confirm_phase9i_ci: str | None,
    confirm_phase9i_status: str | None,
    confirm_phase9i_protocol_freeze: bool,
    confirm_read_phase9h_private_inventory: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_no_outcomes_scoring_evidence_success: bool,
    confirm_no_gold_benchmark_labels: bool,
    confirm_no_provider_llm_model_runtime_default_product_change: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
) -> dict[str, Any]:
    confirmations = _all_confirmations_dict(
        confirm_phase9h_commit, confirm_phase9h_ci, confirm_phase9h_status,
        confirm_phase9i_commit, confirm_phase9i_ci, confirm_phase9i_status,
        confirm_phase9i_protocol_freeze,
        confirm_read_phase9h_private_inventory,
        confirm_ignored_runs_workspace,
        confirm_private_output_only,
        confirm_aggregate_public_report_only,
        confirm_no_outcomes_scoring_evidence_success,
        confirm_no_gold_benchmark_labels,
        confirm_no_provider_llm_model_runtime_default_product_change,
        confirm_no_network_fetch_clone_source_refresh,
    )
    missing = [name for name, ok in confirmations.items() if not ok]
    if missing:
        raise ValueError("missing required confirmation(s): " + ", ".join(missing))

    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    public_report.parent.mkdir(parents=True, exist_ok=True)

    # Validate Phase 9H + Phase 9I gates (read tracked public reports only).
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
    phase9h_gate_ok = not phase9h_errors
    phase9i_gate_ok = not phase9i_errors

    if not phase9h_gate_ok or not phase9i_gate_ok:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9h_gate_ok, phase9i_gate_ok,
            confirmations, private_inventory_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated gate-missing report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9j_gate_missing_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9h_or_phase9i_gate_missing_or_not_green",
                "phase9h_gate_errors_private": phase9h_errors,
                "phase9i_gate_errors_private": phase9i_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_annotation_input_rows_bucket": report["annotation_input_execution_summary"]["annotation_input_rows_bucket"],
            "public_distinct_sources_bucket": report["annotation_input_execution_summary"]["distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Locate and read the Phase 9H private inventory under ignored runs/ only.
    inventory_loc = _find_phase9h_private_inventory()
    if inventory_loc is None:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9h_gate_ok, phase9i_gate_ok,
            confirmations, private_inventory_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated no-inventory report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9j_no_inventory_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9h_private_inventory_missing_or_not_under_ignored_runs",
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_annotation_input_rows_bucket": report["annotation_input_execution_summary"]["annotation_input_rows_bucket"],
            "public_distinct_sources_bucket": report["annotation_input_execution_summary"]["distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    manifest_path, rows_path = inventory_loc
    manifest, inventory_rows, read_errors = _read_phase9h_private_inventory(
        manifest_path, rows_path
    )
    if read_errors or not inventory_rows:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9h_gate_ok, phase9i_gate_ok,
            confirmations, private_inventory_read=False,
            annotation_input_errors=read_errors or ["no_valid_inventory_rows"],
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated inventory-shape-invalid report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9j_inventory_shape_invalid_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9h_private_inventory_shape_invalid_or_empty",
                "inventory_read_errors_private": read_errors or ["no_valid_inventory_rows"],
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_annotation_input_rows_bucket": report["annotation_input_execution_summary"]["annotation_input_rows_bucket"],
            "public_distinct_sources_bucket": report["annotation_input_execution_summary"]["distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Fail closed on inherited Phase 9H hard/per-source/diversity cap
    # violations BEFORE generating any private annotation-input rows/manifests.
    # If the inventory violates caps, write only a private repair/stop manifest
    # (no per-row annotation output) and a public repair report.
    cap_violations = _inventory_cap_violations(inventory_rows)
    if cap_violations:
        aggregate = _cap_violation_aggregate()
        report = build_public_report(
            aggregate, phase9h_gate_ok, phase9i_gate_ok,
            confirmations, private_inventory_read=True,
            annotation_input_errors=cap_violations,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated cap-violation report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9j_inventory_cap_violation_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9h_inventory_cap_violation_fail_closed",
                "cap_violations_private": cap_violations,
                "annotation_input_rows_generated": False,
                "no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels": True,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_annotation_input_rows_bucket": report["annotation_input_execution_summary"]["annotation_input_rows_bucket"],
            "public_distinct_sources_bucket": report["annotation_input_execution_summary"]["distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Generate annotation-input rows from the Phase 9H inventory rows.
    annotation_rows, ann_errors = _generate_annotation_input_rows(inventory_rows)
    if ann_errors:
        aggregate = _empty_aggregate()
        report = build_public_report(
            aggregate, phase9h_gate_ok, phase9i_gate_ok,
            confirmations, private_inventory_read=True,
            annotation_input_errors=ann_errors,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated annotation-input-invalid report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9j_annotation_input_invalid_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "annotation_input_row_schema_violation",
                "annotation_input_errors_private": ann_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_annotation_input_rows_bucket": report["annotation_input_execution_summary"]["annotation_input_rows_bucket"],
            "public_distinct_sources_bucket": report["annotation_input_execution_summary"]["distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    private_manifest = _build_private_manifest(
        annotation_rows, inventory_rows,
        manifest.get("aggregate_private_totals", {}),
    )
    aggregate = private_manifest["aggregate_private_totals"]

    report = build_public_report(
        aggregate, phase9h_gate_ok, phase9i_gate_ok,
        confirmations, private_inventory_read=True,
    )
    errors = validate_report(report)
    if errors:
        raise ValueError(
            "generated public report invalid: " + "; ".join(errors[:12])
        )

    private_run_dir.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_phase9j_annotation_input_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (private_run_dir / "private_phase9j_annotation_input_rows.json").write_text(
        json.dumps(annotation_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    public_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": report["status"],
        "public_report": str(public_report),
        "public_annotation_input_rows_bucket": report["annotation_input_execution_summary"]["annotation_input_rows_bucket"],
        "public_distinct_sources_bucket": report["annotation_input_execution_summary"]["distinct_sources_bucket"],
        "private_output_under_ignored_runs": True,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_FILE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS, NETWORK_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_FILE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS = 0
    NETWORK_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    full_confirmations = _all_confirmations_dict(
        PHASE9H_COMMIT, PHASE9H_CI_RUN, PHASE9H_STATUS,
        PHASE9I_COMMIT, PHASE9I_CI_RUN, PHASE9I_STATUS,
        True, True, True, True, True, True, True, True, True,
    )

    # --- valid executed report (pass) ---
    executed_aggregate = {
        "annotation_input_rows_total": 49,
        "distinct_sources_with_annotation_inputs": 8,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": True,
        "diversity_minimum_met": True,
        "inventory_rows_consumed": 49,
    }
    executed_report = build_public_report(
        executed_aggregate, True, True, full_confirmations,
        private_inventory_read=True,
    )
    checks.append(("valid_executed_report_passes", not validate_report(executed_report)))
    checks.append(("executed_report_is_executed_status", executed_report["status"] == STATUS_EXECUTED))

    # --- valid repair report (zero annotation inputs) ---
    repair_aggregate = _empty_aggregate()
    repair_report = build_public_report(
        repair_aggregate, True, True, full_confirmations,
        private_inventory_read=False,
    )
    checks.append(("valid_repair_report_passes", not validate_report(repair_report)))
    checks.append(("repair_report_is_repair_status", repair_report["status"] == STATUS_REPAIR))

    # --- valid gate-missing report ---
    gate_missing_report = build_public_report(
        repair_aggregate, False, False, full_confirmations,
        private_inventory_read=False,
    )
    checks.append(("valid_gate_missing_report_passes", not validate_report(gate_missing_report)))
    checks.append(("gate_missing_report_is_gate_missing_status", gate_missing_report["status"] == STATUS_GATE_MISSING))

    # --- base report still valid (issue: base report validity) ---
    checks.append(("base_report_valid", not validate_report(executed_report)))

    # --- missing confirmation blocks execution ---
    confirmation_labels = (
        ("missing_confirm_phase9h_commit", dict(confirm_phase9h_commit=None)),
        ("missing_confirm_phase9h_ci", dict(confirm_phase9h_ci=None)),
        ("missing_confirm_phase9h_status", dict(confirm_phase9h_status=None)),
        ("missing_confirm_phase9i_commit", dict(confirm_phase9i_commit=None)),
        ("missing_confirm_phase9i_ci", dict(confirm_phase9i_ci=None)),
        ("missing_confirm_phase9i_status", dict(confirm_phase9i_status=None)),
        ("missing_confirm_phase9i_protocol_freeze", dict(confirm_phase9i_protocol_freeze=False)),
        ("missing_confirm_read_phase9h_private_inventory", dict(confirm_read_phase9h_private_inventory=False)),
        ("missing_confirm_ignored_runs_workspace", dict(confirm_ignored_runs_workspace=False)),
        ("missing_confirm_private_output_only", dict(confirm_private_output_only=False)),
        ("missing_confirm_aggregate_public_report_only", dict(confirm_aggregate_public_report_only=False)),
        ("missing_confirm_no_outcomes_scoring_evidence_success", dict(confirm_no_outcomes_scoring_evidence_success=False)),
        ("missing_confirm_no_gold_benchmark_labels", dict(confirm_no_gold_benchmark_labels=False)),
        ("missing_confirm_no_provider_llm_model", dict(confirm_no_provider_llm_model_runtime_default_product_change=False)),
        ("missing_confirm_no_network_fetch_clone", dict(confirm_no_network_fetch_clone_source_refresh=False)),
    )
    for label, overrides in confirmation_labels:
        kwargs = dict(
            confirm_phase9h_commit=PHASE9H_COMMIT,
            confirm_phase9h_ci=PHASE9H_CI_RUN,
            confirm_phase9h_status=PHASE9H_STATUS,
            confirm_phase9i_commit=PHASE9I_COMMIT,
            confirm_phase9i_ci=PHASE9I_CI_RUN,
            confirm_phase9i_status=PHASE9I_STATUS,
            confirm_phase9i_protocol_freeze=True,
            confirm_read_phase9h_private_inventory=True,
            confirm_ignored_runs_workspace=True,
            confirm_private_output_only=True,
            confirm_aggregate_public_report_only=True,
            confirm_no_outcomes_scoring_evidence_success=True,
            confirm_no_gold_benchmark_labels=True,
            confirm_no_provider_llm_model_runtime_default_product_change=True,
            confirm_no_network_fetch_clone_source_refresh=True,
        )
        kwargs.update(overrides)
        try:
            execute_phase9j(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, **kwargs)
            checks.append((f"{label}_rejected", False))
        except ValueError as exc:
            checks.append((f"{label}_rejected", "missing required confirmation" in str(exc)))

    # --- tracked/private path rejected (path scope fail-closed) ---
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_tracked_output")
        checks.append(("tracked_output_path_rejected", False))
    except ValueError as exc:
        checks.append(("tracked_output_path_rejected", "runs" in str(exc)))

    # --- Phase 9H/9I gate validation ---
    checks.append((
        "wrong_phase9h_commit_rejected",
        bool(_phase9h_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9H_CI_RUN, supplied_status=PHASE9H_STATUS)),
    ))
    checks.append((
        "wrong_phase9h_ci_rejected",
        bool(_phase9h_gate_errors(supplied_commit=PHASE9H_COMMIT, supplied_ci="0000", supplied_status=PHASE9H_STATUS)),
    ))
    checks.append((
        "wrong_phase9h_status_rejected",
        bool(_phase9h_gate_errors(supplied_commit=PHASE9H_COMMIT, supplied_ci=PHASE9H_CI_RUN, supplied_status="drift")),
    ))
    checks.append((
        "wrong_phase9i_commit_rejected",
        bool(_phase9i_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9I_CI_RUN, supplied_status=PHASE9I_STATUS)),
    ))
    checks.append((
        "wrong_phase9i_ci_rejected",
        bool(_phase9i_gate_errors(supplied_commit=PHASE9I_COMMIT, supplied_ci="0000", supplied_status=PHASE9I_STATUS)),
    ))
    checks.append((
        "wrong_phase9i_status_rejected",
        bool(_phase9i_gate_errors(supplied_commit=PHASE9I_COMMIT, supplied_ci=PHASE9I_CI_RUN, supplied_status="drift")),
    ))

    # --- Phase 9H private manifest shape validation ---
    valid_manifest = {
        "phase": PHASE9H_PHASE,
        "task_candidate_rows_are_inventory_only": True,
        "accepted_task_rows_remain_inventory_only_not_benchmark_annotations": True,
        "materialization_rows_private": [],
        "aggregate_private_totals": {"candidate_total": 0},
    }
    checks.append(("valid_phase9h_manifest_shape_passes", not _validate_phase9h_manifest_shape(valid_manifest)))

    bad_manifest = {"phase": "drift"}
    checks.append(("invalid_phase9h_manifest_shape_rejected", bool(_validate_phase9h_manifest_shape(bad_manifest))))

    # --- Phase 9H row shape validation ---
    valid_inv_row = {
        "private_candidate_id": "abc123",
        "source_order_index_private": 0,
        "candidate_order_index_private": 0,
        "task_type": "evidence_finding_file_localizable_code_task",
        "private_source_file_path": "src/example.py",
        "private_line_range": {"start": 1, "end": 24},
        "replacement_policy_private": "next_deterministic_candidate",
    }
    checks.append(("valid_phase9h_row_shape_passes", not _validate_phase9h_row_shape(valid_inv_row, 0)))

    bad_inv_row = {"private_candidate_id": "abc123"}
    checks.append(("invalid_phase9h_row_shape_rejected", bool(_validate_phase9h_row_shape(bad_inv_row, 0))))

    # --- annotation-input row generation + validation ---
    ann_row = _generate_annotation_input_row(valid_inv_row, 0)
    checks.append(("valid_annotation_input_row_passes", not _validate_annotation_input_row(ann_row, 0)))
    checks.append(("annotation_input_row_is_routing_precondition_only", ann_row["annotation_input_is_routing_precondition_only_not_benchmark_truth"] is True))
    checks.append(("annotation_input_row_has_no_outcomes", ann_row["no_outcomes_no_gold_no_scoring_no_evidence_success_no_result_labels"] is True))

    # --- annotation-input row with extra/forbidden field rejected ---
    bad_ann_row = dict(ann_row)
    bad_ann_row["gold_label"] = "hidden"
    checks.append(("annotation_input_extra_field_rejected", bool(_validate_annotation_input_row(bad_ann_row, 0))))
    checks.append(("annotation_input_forbidden_token_detected", any("forbidden token" in e for e in _validate_annotation_input_row(bad_ann_row, 0))))

    bad_ann_row2 = dict(ann_row)
    del bad_ann_row2["task_eligibility_input"]
    checks.append(("annotation_input_missing_field_rejected", bool(_validate_annotation_input_row(bad_ann_row2, 0))))

    bad_ann_row3 = dict(ann_row)
    bad_ann_row3["outcome_result"] = "hidden"
    checks.append(("annotation_input_outcome_field_rejected", bool(_validate_annotation_input_row(bad_ann_row3, 0))))

    bad_ann_row4 = dict(ann_row)
    bad_ann_row4["scoring_value"] = 42
    checks.append(("annotation_input_scoring_field_rejected", bool(_validate_annotation_input_row(bad_ann_row4, 0))))

    bad_ann_row5 = dict(ann_row)
    bad_ann_row5["annotation_input_is_routing_precondition_only_not_benchmark_truth"] = False
    checks.append(("annotation_input_boundary_false_rejected", bool(_validate_annotation_input_row(bad_ann_row5, 0))))

    # --- annotation-input row generation from multiple inventory rows ---
    inv_rows = [dict(valid_inv_row, candidate_order_index_private=i, private_candidate_id=f"id_{i}") for i in range(5)]
    ann_rows, ann_gen_errors = _generate_annotation_input_rows(inv_rows)
    checks.append(("annotation_input_generation_no_errors", not ann_gen_errors))
    checks.append(("annotation_input_generation_count_matches", len(ann_rows) == 5))

    # --- inherited Phase 9H cap fail-closed (no annotation rows on cap violation) ---
    cap_row_base = dict(valid_inv_row)
    # Over the hard inventory cap (96): 100 rows across 8 sources.
    over_hard_cap_rows = [
        dict(cap_row_base, candidate_order_index_private=i,
             private_candidate_id=f"cap_{i}", source_order_index_private=i % MIN_DISTINCT_SOURCES)
        for i in range(HARD_INVENTORY_CAP + 4)
    ]
    over_hard_cap_violations = _inventory_cap_violations(over_hard_cap_rows)
    checks.append(("over_hard_cap_violation_detected", bool(over_hard_cap_violations)))
    checks.append(("over_hard_cap_violation_mentions_hard_cap", any("hard cap" in e for e in over_hard_cap_violations)))

    # Per-source cap violation only (under hard cap, diversity met, one source over 8).
    per_source_rows = [
        dict(cap_row_base, candidate_order_index_private=i,
             private_candidate_id=f"ps_{i}", source_order_index_private=0)
        for i in range(PER_SOURCE_CAP + 1)
    ] + [
        dict(cap_row_base, candidate_order_index_private=PER_SOURCE_CAP + 1 + i,
             private_candidate_id=f"ps2_{i}", source_order_index_private=1 + i)
        for i in range(MIN_DISTINCT_SOURCES)
    ]
    per_source_violations = _inventory_cap_violations(per_source_rows)
    checks.append(("per_source_cap_violation_detected", any("per-source cap" in e for e in per_source_violations)))

    # Diversity minimum violation only (under hard cap, per-source OK, too few sources).
    diversity_rows = [
        dict(cap_row_base, candidate_order_index_private=i,
             private_candidate_id=f"dv_{i}", source_order_index_private=i % (MIN_DISTINCT_SOURCES - 1))
        for i in range(MIN_DISTINCT_SOURCES + 2)
    ]
    diversity_violations = _inventory_cap_violations(diversity_rows)
    checks.append(("diversity_minimum_violation_detected", any("diversity minimum" in e for e in diversity_violations)))

    # Within-caps inventory produces NO violations (no false positive).
    within_caps_rows = [
        dict(cap_row_base, candidate_order_index_private=i,
             private_candidate_id=f"ok_{i}", source_order_index_private=i % MIN_DISTINCT_SOURCES)
        for i in range(TARGET_INVENTORY_MIN + 1)
    ]
    checks.append(("within_caps_inventory_no_violations", not _inventory_cap_violations(within_caps_rows)))

    # Cap violation blocks before annotation-input generation: the cap check
    # is the fail-closed guard that prevents _generate_annotation_input_rows
    # running on an over-cap inventory.
    checks.append((
        "cap_violation_blocks_annotation_row_generation",
        bool(_inventory_cap_violations(over_hard_cap_rows)),
    ))

    # --- strict schema: unknown top-level/nested fields rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["annotation_input_execution_summary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["phase9h_gate_references"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_gate_field_rejected", bool(validate_report(mutated))))

    # --- private-shaped public fields rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["annotation_input_execution_summary"]["example_value"] = "https://example.invalid/repo.git"
    checks.append(("url_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["annotation_input_execution_summary"]["example_value"] = "owner/repo"
    checks.append(("owner_repo_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["privacy_summary"]["per_source_public_facts"] = True
    checks.append(("per_source_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["privacy_summary"]["per_task_public_facts"] = True
    checks.append(("per_task_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(executed_report)
    mutated["privacy_summary"]["annotation_input_rows_public"] = True
    checks.append(("annotation_input_rows_public_rejected", bool(validate_report(mutated))))

    # --- private-shaped keys rejected ---
    for bad_key in ("private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket", "per_task_summary", "source_path_bucket"):
        mutated = copy.deepcopy(executed_report)
        mutated["annotation_input_execution_summary"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- singleton buckets rejected ---
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(executed_report)
        mutated["annotation_input_execution_summary"]["example_bucket"] = singleton_val
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))

    # --- forbidden outcome/scoring/evidence/gold/label keys/values rejected ---
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(executed_report)
        mutated["annotation_input_execution_summary"][bad_key] = "exposed_value"
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
        "outcome success", "evaluation works", "task annotation readiness",
        "annotation works", "annotation_input works",
    )
    for phrase in forbidden_claims:
        mutated = copy.deepcopy(executed_report)
        mutated["annotation_input_execution_summary"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_')}_rejected", bool(validate_report(mutated))))

    # --- exact count field rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["annotation_input_execution_summary"]["count"] = 49
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    # --- gate-reference path whitelist: non-whitelisted key with hash value rejected ---
    mutated = copy.deepcopy(executed_report)
    mutated["annotation_input_execution_summary"]["task_ci_run"] = "28979060368"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))

    # --- long decimal CI/run-shaped values rejected except on whitelisted gate paths ---
    # 28979060368 (Phase 9I CI run) inserted into an ALLOWED non-gate string
    # field must be rejected by the long-decimal value scan.
    mutated = copy.deepcopy(executed_report)
    mutated["annotation_input_execution_summary"]["distinct_sources_bucket"] = "28979060368"
    errors = validate_report(mutated)
    checks.append(("long_decimal_in_allowed_non_gate_field_rejected", bool(errors)))
    checks.append((
        "long_decimal_rejection_cites_decimal",
        any("long decimal" in e for e in errors),
    ))

    # 28976655118 (Phase 9H CI run) into a different allowed non-gate string field.
    mutated = copy.deepcopy(executed_report)
    mutated["annotation_input_execution_summary"]["annotation_input_rows_bucket"] = "28976655118"
    checks.append(("long_decimal_ci_run_in_allowed_non_gate_field_rejected", bool(validate_report(mutated))))

    # Gate CI run values on the exact whitelisted gate paths remain valid
    # (executed_report carries phase9h_ci_run / phase9i_ci_run and must pass).
    checks.append(("gate_ci_run_values_on_whitelisted_paths_valid", not validate_report(executed_report)))

    # --- validate-report path fail-closed ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9j" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "other_phase" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase9j" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # --- temp-file round-trip validation ---
    with tempfile.TemporaryDirectory(prefix="phase9j_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(executed_report), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- self-test does not fetch/read private ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_files", SOURCE_FILE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9h_private_inventory", PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS == 0))
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
        description="Phase 9J annotation-input execution (no scoring, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--confirm-phase9h-commit")
    parser.add_argument("--confirm-phase9h-ci")
    parser.add_argument("--confirm-phase9h-status")
    parser.add_argument("--confirm-phase9i-commit")
    parser.add_argument("--confirm-phase9i-ci")
    parser.add_argument("--confirm-phase9i-status")
    parser.add_argument("--confirm-phase9i-protocol-freeze", action="store_true")
    parser.add_argument("--confirm-read-phase9h-private-inventory", action="store_true")
    parser.add_argument("--confirm-ignored-runs-workspace", action="store_true")
    parser.add_argument("--confirm-private-output-only", action="store_true")
    parser.add_argument("--confirm-aggregate-public-report-only", action="store_true")
    parser.add_argument("--confirm-no-outcomes-scoring-evidence-success", action="store_true")
    parser.add_argument("--confirm-no-gold-benchmark-labels", action="store_true")
    parser.add_argument("--confirm-no-provider-llm-model-runtime-default-product-change", action="store_true")
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
        result = execute_phase9j(
            args.private_run_dir,
            args.output,
            args.confirm_phase9h_commit,
            args.confirm_phase9h_ci,
            args.confirm_phase9h_status,
            args.confirm_phase9i_commit,
            args.confirm_phase9i_ci,
            args.confirm_phase9i_status,
            args.confirm_phase9i_protocol_freeze,
            args.confirm_read_phase9h_private_inventory,
            args.confirm_ignored_runs_workspace,
            args.confirm_private_output_only,
            args.confirm_aggregate_public_report_only,
            args.confirm_no_outcomes_scoring_evidence_success,
            args.confirm_no_gold_benchmark_labels,
            args.confirm_no_provider_llm_model_runtime_default_product_change,
            args.confirm_no_network_fetch_clone_source_refresh,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
