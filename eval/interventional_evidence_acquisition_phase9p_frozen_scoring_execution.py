#!/usr/bin/env python3
"""Phase 9P frozen scoring execution (bucketed aggregate only, no claim).

This runner has one narrow purpose: under explicit confirmations and the frozen
Phase 9O scoring/denominator/adjudication protocol, execute the frozen SCORING
protocol only.  It reads the Phase 9N private outcome-observable packets under
ignored ``runs/`` only (with explicit confirmation), applies the frozen Phase 9O
denominator-eligibility predicates, applies the frozen inclusion/exclusion
rules, and computes the frozen scoring-metric buckets (denominator_bucket,
scored_bucket, adjudicated_bucket, invalid_excluded_bucket,
unavailable_excluded_bucket, correctness_bucket) as bucketed aggregates only.

It does NOT execute adjudication: the frozen Phase 9O adjudication rule
``future_adjudication_requires_separate_frozen_boundary_after_scoring`` requires
a separate future frozen boundary after scoring, which does not exist in
Phase 9P.  Adjudication, correctness, evidence_success, gold/benchmark labels,
result labels, and annotation-truth remain not-executed.  It does NOT read the
Phase 9H private materialized sources, the Phase 9J private annotation-input
rows, or the Phase 9L private outcome packets.  It does NOT use Phase 9J rows as
benchmark truth (the Phase 9N packets carry only acquisition state + routing
precondition metadata, NOT benchmark truth).  It does NOT score Phase 9L
unavailable packets.

The frozen Phase 9O protocol closed lists (denominator eligibility predicates,
inclusion/exclusion rules, scoring metric definitions, adjudication rules,
missing/invalid/unavailable handling, privacy/publication, future Phase 9P gate,
no-p-hacking guardrails) are loaded directly from the committed Phase 9O
protocol-freeze module so Phase 9P applies EXACTLY the frozen protocol (no
re-declaration, no drift).  No new metrics, thresholds, or subgroups are
introduced; no protocol edits after outcome visibility; no denominator repair
after private reads.

Scoring here is the frozen bucketing of acquisition availability into aggregate
buckets only -- NOT correctness scoring, NOT evidence_success, NOT pass/fail,
NOT method/product/performance success.  Private scoring rows are written only
under ignored ``runs/``.  The public report publishes only bucketed aggregates:
no exact counts/rates, no ids/observables/snippets/paths/source identities/run
dirs/singleton buckets.

Truth-boundary is explicit: the denominator eligibility rule is applied, not
redefined; the scoring metric definitions are applied as bucketed aggregates, not
redefined as executed correctness metrics; the adjudication rule is not
adjudicated truth; missing/invalid/unavailable handling is not failure or
success; the Phase 9N acquired-valid bucket is availability, not scoring
success; the frozen protocol is applied, not redefined after outcome visibility.
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

# Compact Phase 9P slug (kept short so the absolute artifact report path stays
# comfortably under the Windows MAX_PATH (260) limit).  Boundary wording in the
# report body/docs is NOT weakened -- only the path-dependent slug is shortened.
PHASE = "phase9p_frozen_scoring_execution_no_claim"
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

# ---------------------------------------------------------------------------
# Status shapes.
# ---------------------------------------------------------------------------
# Executed: frozen scoring (bucketing) ran, denominator nonzero, scored
# nonzero; adjudication NOT executed (separate future frozen boundary required).
STATUS_EXECUTED = (
    "phase9p_frozen_scoring_executed_denominator_nonzero_scored_nonzero"
    "_adjudication_not_executed_separate_frozen_boundary_required"
    "_no_evidence_success_no_claim"
)
# Dry/no-private mode: no runs/ read, no scoring, no denominator, no claim.
STATUS_DRY = (
    "phase9p_dry_run_no_private_read_no_scoring_no_denominator_no_claim"
)
# Repair: gate missing/not green, packets unreadable, denominator zero, or
# scoring cannot be applied exactly as frozen.  Stop with no-claim.
STATUS_REPAIR = "phase9p_frozen_scoring_repair_no_claim"
STATUS_GATE_MISSING = (
    "phase9p_blocked_phase9o_or_phase9n_gate_missing_or_not_green_no_claim"
)
STATUS_DENOMINATOR_ZERO = (
    "phase9p_frozen_scoring_denominator_zero_no_scoring_applied_no_claim"
)
ALLOWED_STATUSES = {
    STATUS_EXECUTED,
    STATUS_DRY,
    STATUS_REPAIR,
    STATUS_GATE_MISSING,
    STATUS_DENOMINATOR_ZERO,
}
# Statuses that represent actual frozen-scoring execution.
EXECUTED_STATUSES = {STATUS_EXECUTED}

# ---------------------------------------------------------------------------
# Phase 9O public gate reference values (oracle-provided).  These are the
# PRIMARY gate references for Phase 9P.  Local same-tree git commits are not
# read or compared; the supplied confirmation values are matched against the
# frozen public gate constants only.
# ---------------------------------------------------------------------------
PHASE9O_COMMIT = "fa812361e1a121b7c3c8e6d2a540d4916975d090"
PHASE9O_CI_RUN = "28986131071"
PHASE9O_STATUS = (
    "phase9o_scoring_denominator_adjudication_protocol_freeze"
    "_no_execution_no_private_read_no_scoring_no_claim"
)
PHASE9O_PUBLIC_REPORT = (
    REPO / "artifacts"
    / "phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim"
    / "phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim_report.json"
)

# ---------------------------------------------------------------------------
# Phase 9N public gate reference values (oracle-provided; secondary, whitelisted
# from Phase 9O).  Nonzero acquired-valid bucket is the availability gate that
# permits Phase 9P scoring to be considered.
# ---------------------------------------------------------------------------
PHASE9N_COMMIT = "282a5037a106da55b6df67a33c42bb3ad7142836"
PHASE9N_CI_RUN = "28985320043"
PHASE9N_STATUS = (
    "phase9n_frozen_route_executed_valid_acquired_nonzero_aggregate_availability"
    "_no_scoring_no_adjudication_no_claim"
)
PHASE9N_ACQUIRED_VALID_BUCKET = "bucket_nonzero_redacted"

# Phase 9M/9L/9K/9H/9I/9J/9G/9F inherited provenance (carried forward, bucketed
# only).  The exact remote commit/CI run values are intentionally NOT published
# in the Phase 9P report/docs (tighter privacy); only the Phase 9O and Phase 9N
# full commit SHA / CI run are public gate references.
PHASE9M_STATUS = (
    "phase9m_outcome_observable_acquisition_route_protocol_freeze"
    "_no_execution_no_scoring_no_adjudication_no_claim"
)
PHASE9L_STATUS = (
    "phase9l_outcome_acquisition_executed_unavailable_only"
    "_no_scoring_no_adjudication_no_claim"
)
PHASE9K_STATUS = "phase9k_outcome_scoring_protocol_freeze_no_claim"
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

# Expected private Phase 9N outcome-observable packets location (under ignored
# runs/ only).  Phase 9P reads the acquisition-state packets only (no source
# content, no snippets, no observables -- only acquisition state + routing
# precondition metadata).
PHASE9N_PHASE = "phase9n_frozen_route_outcome_acquisition_no_scoring_no_claim"
PHASE9N_PRIVATE_RUN_DIR = REPO / "runs" / PHASE9N_PHASE / "current"
PHASE9N_PRIVATE_MANIFEST = (
    PHASE9N_PRIVATE_RUN_DIR / "private_phase9n_outcome_acquisition_manifest.json"
)
PHASE9N_PRIVATE_PACKETS = (
    PHASE9N_PRIVATE_RUN_DIR / "private_phase9n_outcome_acquisition_packets.json"
)

# Whitelisted expected evidence form (from Phase 9N/9J frozen route).  The
# denominator predicate ``packet_expected_evidence_form_matches_whitelist`` is
# satisfied only by this exact form.
EXPECTED_EVIDENCE_FORM_WHITELIST = (
    "file_path_and_line_range_only_no_snippet_stored",
)

# Phase 9N outcome-observable packet required fields (for the
# ``packet_schema_validates`` denominator predicate).  These mirror the frozen
# Phase 9N packet schema (acquisition state + routing precondition metadata
# only; no scoring/observables/snippets).
PHASE9N_PACKET_REQUIRED_FIELDS = (
    "private_annotation_input_ref",
    "source_order_index_private",
    "candidate_order_index_private",
    "task_eligibility_routing_precondition_only",
    "evidence_localization_requirement",
    "expected_evidence_form",
    "outcome_acquisition_precondition",
    "annotation_input_metadata_reference",
    "outcome_acquisition_state",
    "outcome_observable_acquired",
    "replacement_needed",
    "evidence_form_confirmed_source_grounded",
    "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels",
)

# Frozen scoring-metric bucket names (exactly the Phase 9O frozen
# SCORING_METRIC_DEFINITIONS bucket names, published as bucketed aggregates).
SCORING_BUCKET_NAMES = (
    "denominator_bucket",
    "scored_bucket",
    "adjudicated_bucket",
    "invalid_excluded_bucket",
    "unavailable_excluded_bucket",
    "correctness_bucket",
)

# Boundary attestation keys that must always be True in the public report.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "denominator_eligibility_rule_applied_not_redefined",
    "scoring_metric_definitions_applied_as_bucketed_aggregate_not_redefined",
    "adjudication_rule_is_not_adjudicated_truth",
    "missing_invalid_unavailable_handling_is_not_failure_or_success",
    "phase9n_acquired_valid_bucket_is_availability_not_scoring_success",
    "frozen_protocol_applied_not_redefined_after_outcome_visibility",
)

# Boundary attestation keys that must always be False in the public report.
# Phase 9P executes frozen scoring (bucketing) and reads Phase 9N packets under
# ignored runs/, so ``scoring_executed``, ``denominator_computed``,
# ``private_phase9n_packets_read`` and ``ignored_runs_read`` are intentionally
# NOT in this false-set (they are honest True execution attestations).  These
# are the FORBIDDEN actions that must remain False.
NO_EXECUTION_FALSE_KEYS = (
    "adjudication_executed",
    "correctness_evaluated",
    "evidence_success_evaluated",
    "gold_labels_generated",
    "benchmark_labels_generated",
    "result_labels_generated",
    "annotation_truth_generated",
    "phase9j_rows_used_as_benchmark_truth",
    "phase9l_packets_scoreable",
    "private_phase9l_outcome_packets_read",
    "private_phase9h_materialized_sources_read",
    "private_phase9j_annotation_input_rows_read",
    "private_candidate_pool_read",
    "private_registry_read",
    "provider_or_llm_calls",
    "model_fitting",
    "network_fetch_or_clone_or_source_refresh_executed",
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "runtime_default_or_product_changes",
    "new_metrics_introduced",
    "new_thresholds_introduced",
    "new_subgroups_introduced",
    "protocol_edited_after_outcome_visibility",
    "denominator_repaired_after_private_reads",
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
    "packet_ids_public",
    "manifest_locations_public",
    "run_locations_public",
    "per_source_public_facts",
    "per_task_public_facts",
    "per_packet_public_facts",
    "singleton_buckets_public",
    "outcome_observables_public",
    "outcome_packets_public",
    "phase9n_packets_public",
    "phase9l_packets_public",
    "exact_counts_or_rates_public",
)

# Forbidden public field words; only apply to non-boolean values at
# non-allowed-schema paths so boolean boundary attestation keys are not
# false-flagged.
FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

# Threshold key detector (no new thresholds introduced).
THRESHOLD_KEY_RE = re.compile(r"threshold", re.IGNORECASE)

# Closed protocol lists loaded EXACTLY from the committed Phase 9O freeze
# module (set-equality validated against the same source of truth).  Populated
# by ``_load_phase9o_freeze`` below.
DENOMINATOR_ELIGIBILITY_PREDICATES: tuple[str, ...] = ()
INCLUSION_EXCLUSION_RULES: tuple[str, ...] = ()
SCORING_METRIC_DEFINITIONS: tuple[str, ...] = ()
ADJUDICATION_RULES: tuple[str, ...] = ()
MISSING_INVALID_UNAVAILABLE_HANDLING_RULES: tuple[str, ...] = ()
PRIVACY_PUBLICATION_RULES: tuple[str, ...] = ()
FUTURE_PHASE9P_GATE_RULES: tuple[str, ...] = ()
NO_P_HACKING_GUARDRAIL_RULES: tuple[str, ...] = ()
TRUTH_BOUNDARY_TRUE_KEYS_9O: tuple[str, ...] = ()

# Inherited aggregate caps/buckets from Phase 9H (frozen, aggregate-only).
TARGET_INVENTORY_MIN = 48
TARGET_INVENTORY_MAX = 72
HARD_INVENTORY_CAP = 96
PER_SOURCE_CAP = 8
MIN_DISTINCT_SOURCES = 8

# Privacy/wording regexes (loaded from Phase 9O freeze to stay identical).
PRIVATE_SHAPED_VALUE_RE: re.Pattern[str] = re.compile(r"$.^")  # replaced after load
LONG_DECIMAL_VALUE_RE: re.Pattern[str] = re.compile(r"$.^")
SINGLETON_BUCKET_RE: re.Pattern[str] = re.compile(r"$.^")
CLAIM_WORDING_RE: re.Pattern[str] = re.compile(r"$.^")
USER_APPROVAL_WORDING_RE: re.Pattern[str] = re.compile(r"$.^")
PLACEHOLDER_RE: re.Pattern[str] = re.compile(r"$.^")
PRIVATE_KEY_RE: re.Pattern[str] = re.compile(r"$.^")
LIST_VALUE_PRIVATE_TOKEN_RE: re.Pattern[str] = re.compile(r"$.^")

# Closed protocol lists carried in the public report (section, key, label).
CLOSED_PROTOCOL_LISTS = (
    (
        "frozen_protocol_applied",
        "denominator_eligibility_predicates",
        DENOMINATOR_ELIGIBILITY_PREDICATES,
        "denominator_predicates",
    ),
    (
        "frozen_protocol_applied",
        "inclusion_exclusion_rules",
        INCLUSION_EXCLUSION_RULES,
        "inclusion_exclusion",
    ),
    (
        "frozen_protocol_applied",
        "scoring_metric_definitions",
        SCORING_METRIC_DEFINITIONS,
        "scoring_metrics",
    ),
    (
        "frozen_protocol_applied",
        "adjudication_rules",
        ADJUDICATION_RULES,
        "adjudication",
    ),
    (
        "frozen_protocol_applied",
        "missing_invalid_unavailable_handling_rules",
        MISSING_INVALID_UNAVAILABLE_HANDLING_RULES,
        "handling",
    ),
    (
        "frozen_protocol_applied",
        "privacy_publication_rules",
        PRIVACY_PUBLICATION_RULES,
        "privacy",
    ),
    (
        "frozen_protocol_applied",
        "future_phase9p_gate_rules",
        FUTURE_PHASE9P_GATE_RULES,
        "future_phase9p_gate",
    ),
    (
        "frozen_protocol_applied",
        "no_p_hacking_guardrail_rules",
        NO_P_HACKING_GUARDRAIL_RULES,
        "guardrail",
    ),
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants (full commit SHA / CI run ID).  Only the Phase 9O and
# Phase 9N commit/CI paths are exempt from the private-shaped/decimal value
# scans.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9o_gate_references.phase9o_commit",
        "$.phase9o_gate_references.phase9o_ci_run",
        "$.phase9n_gate_references.phase9n_commit",
        "$.phase9n_gate_references.phase9n_ci_run",
    }
)
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9o_gate_references.phase9o_ci_run",
        "$.phase9n_gate_references.phase9n_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read
# private beyond the explicitly-authorized Phase 9N packet read.
FETCH_CLONE_ATTEMPTS = 0
NETWORK_CALL_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0


# ---------------------------------------------------------------------------
# Load the committed Phase 9O protocol-freeze module (constants only) so Phase
# 9P applies EXACTLY the frozen protocol -- no re-declaration, no drift.
# ---------------------------------------------------------------------------

def _load_phase9o_freeze() -> Any:
    """Load the committed Phase 9O freeze module by path (no sys.path mutation).

    The Phase 9O module only defines constants and pure functions at module
    level (no fetch, no private reads, no execution on import).  Loading it
    does not read ``runs/`` or any private material.
    """
    import importlib.util

    path = (
        REPO / "eval"
        / "interventional_evidence_acquisition_phase9o_scoring_denominator_adjudication_protocol_freeze.py"
    )
    spec = importlib.util.spec_from_file_location("_phase9o_freeze_for_phase9p", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Phase 9O freeze module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PHASE9O_FREEZE = _load_phase9o_freeze()

# Bind the frozen closed lists and regexes directly from Phase 9O.
DENOMINATOR_ELIGIBILITY_PREDICATES = _PHASE9O_FREEZE.DENOMINATOR_ELIGIBILITY_PREDICATES
INCLUSION_EXCLUSION_RULES = _PHASE9O_FREEZE.INCLUSION_EXCLUSION_RULES
SCORING_METRIC_DEFINITIONS = _PHASE9O_FREEZE.SCORING_METRIC_DEFINITIONS
ADJUDICATION_RULES = _PHASE9O_FREEZE.ADJUDICATION_RULES
MISSING_INVALID_UNAVAILABLE_HANDLING_RULES = (
    _PHASE9O_FREEZE.MISSING_INVALID_UNAVAILABLE_HANDLING_RULES
)
PRIVACY_PUBLICATION_RULES = _PHASE9O_FREEZE.PRIVACY_PUBLICATION_RULES
FUTURE_PHASE9P_GATE_RULES = _PHASE9O_FREEZE.FUTURE_PHASE9P_GATE_RULES
NO_P_HACKING_GUARDRAIL_RULES = _PHASE9O_FREEZE.NO_P_HACKING_GUARDRAIL_RULES
TRUTH_BOUNDARY_TRUE_KEYS_9O = _PHASE9O_FREEZE.TRUTH_BOUNDARY_TRUE_KEYS

PRIVATE_SHAPED_VALUE_RE = _PHASE9O_FREEZE.PRIVATE_SHAPED_VALUE_RE
LONG_DECIMAL_VALUE_RE = _PHASE9O_FREEZE.LONG_DECIMAL_VALUE_RE
SINGLETON_BUCKET_RE = _PHASE9O_FREEZE.SINGLETON_BUCKET_RE
CLAIM_WORDING_RE = _PHASE9O_FREEZE.CLAIM_WORDING_RE
USER_APPROVAL_WORDING_RE = _PHASE9O_FREEZE.USER_APPROVAL_WORDING_RE
PLACEHOLDER_RE = _PHASE9O_FREEZE.PLACEHOLDER_RE
PRIVATE_KEY_RE = _PHASE9O_FREEZE.PRIVATE_KEY_RE
LIST_VALUE_PRIVATE_TOKEN_RE = _PHASE9O_FREEZE.LIST_VALUE_PRIVATE_TOKEN_RE

# Re-bind CLOSED_PROTOCOL_LISTS now that the tuples are populated.
CLOSED_PROTOCOL_LISTS = (
    (
        "frozen_protocol_applied",
        "denominator_eligibility_predicates",
        DENOMINATOR_ELIGIBILITY_PREDICATES,
        "denominator_predicates",
    ),
    (
        "frozen_protocol_applied",
        "inclusion_exclusion_rules",
        INCLUSION_EXCLUSION_RULES,
        "inclusion_exclusion",
    ),
    (
        "frozen_protocol_applied",
        "scoring_metric_definitions",
        SCORING_METRIC_DEFINITIONS,
        "scoring_metrics",
    ),
    (
        "frozen_protocol_applied",
        "adjudication_rules",
        ADJUDICATION_RULES,
        "adjudication",
    ),
    (
        "frozen_protocol_applied",
        "missing_invalid_unavailable_handling_rules",
        MISSING_INVALID_UNAVAILABLE_HANDLING_RULES,
        "handling",
    ),
    (
        "frozen_protocol_applied",
        "privacy_publication_rules",
        PRIVACY_PUBLICATION_RULES,
        "privacy",
    ),
    (
        "frozen_protocol_applied",
        "future_phase9p_gate_rules",
        FUTURE_PHASE9P_GATE_RULES,
        "future_phase9p_gate",
    ),
    (
        "frozen_protocol_applied",
        "no_p_hacking_guardrail_rules",
        NO_P_HACKING_GUARDRAIL_RULES,
        "guardrail",
    ),
)

CONSERVATIVE_RECOMMENDATION = (
    "phase9p_executes_frozen_scoring_bucketing_only"
    "_denominator_nonzero_adjudication_not_executed"
    "_requires_separate_frozen_boundary_after_scoring"
    "_no_evidence_success_no_correctness_no_method_product_claim"
)


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


def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


# ---------------------------------------------------------------------------
# Bucket helper
# ---------------------------------------------------------------------------

def _bucket(value: int) -> str:
    """Bucket a count into privacy-safe buckets only.

    Zero -> ``bucket_zero``; nonzero -> ``bucket_nonzero_redacted`` (no exact
    count, no singleton, no per-source/per-task fact).
    """
    if value <= 0:
        return "bucket_zero"
    return "bucket_nonzero_redacted"


# ---------------------------------------------------------------------------
# Phase 9O / Phase 9N gate validation (reads tracked public reports only)
# ---------------------------------------------------------------------------

def _phase9o_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9O public gate.  Reads the tracked public report only."""
    errors: list[str] = []
    if report is None:
        if not PHASE9O_PUBLIC_REPORT.exists():
            return ["Phase 9O public report missing"]
        report = json.loads(PHASE9O_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9O public report must be object"]
    if report.get("status") != PHASE9O_STATUS:
        errors.append("Phase 9O public report status drift")
    if report.get("schema_version") != (
        "phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim_report_v1"
    ):
        errors.append("Phase 9O public report schema drift")
    if report.get("phase") != (
        "phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim"
    ):
        errors.append("Phase 9O public report phase drift")
    # Phase 9O must attest no execution / no scoring.
    scope = report.get("phase9o_scope", {})
    for key in ("scoring_executed", "adjudication_executed", "denominator_computed"):
        if scope.get(key) is not False:
            errors.append(f"Phase 9O public report execution boundary failed: {key}")
    # Phase 9N gate references published by Phase 9O.
    gate9n = report.get("phase9n_gate_references", {})
    if gate9n.get("phase9n_commit") != PHASE9N_COMMIT:
        errors.append("Phase 9O report Phase 9N commit gate drift")
    if gate9n.get("phase9n_ci_run") != PHASE9N_CI_RUN:
        errors.append("Phase 9O report Phase 9N CI run gate drift")
    if gate9n.get("phase9n_status") != PHASE9N_STATUS:
        errors.append("Phase 9O report Phase 9N status gate drift")
    if gate9n.get("phase9n_acquired_valid_bucket") != PHASE9N_ACQUIRED_VALID_BUCKET:
        errors.append("Phase 9O report Phase 9N acquired_valid_bucket drift")
    if supplied_commit is not None and supplied_commit != PHASE9O_COMMIT:
        errors.append("supplied Phase 9O commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9O_CI_RUN:
        errors.append("supplied Phase 9O CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9O_STATUS:
        errors.append("supplied Phase 9O status does not match public gate reference")
    return sorted(set(errors))


def _phase9n_gate_errors(
    supplied_commit: str | None,
    supplied_ci: str | None,
    supplied_status: str | None,
    acquired_valid_bucket_nonzero: bool,
) -> list[str]:
    """Validate the Phase 9N public gate references (matched against constants)."""
    errors: list[str] = []
    if supplied_commit != PHASE9N_COMMIT:
        errors.append("supplied Phase 9N commit does not match public gate reference")
    if supplied_ci != PHASE9N_CI_RUN:
        errors.append("supplied Phase 9N CI run does not match public gate reference")
    if supplied_status != PHASE9N_STATUS:
        errors.append("supplied Phase 9N status does not match public gate reference")
    if acquired_valid_bucket_nonzero is not True:
        errors.append("Phase 9N acquired_valid_bucket must be nonzero to consider scoring")
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Phase 9N private outcome-observable packet reading (under ignored runs/ only)
# ---------------------------------------------------------------------------

def _find_phase9n_private_packets() -> tuple[Path, Path] | None:
    """Locate the Phase 9N private manifest + packets under ignored runs/ only."""
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = PHASE9N_PRIVATE_MANIFEST.resolve()
    packets_resolved = PHASE9N_PRIVATE_PACKETS.resolve()
    if runs_root not in manifest_resolved.parents:
        return None
    if runs_root not in packets_resolved.parents:
        return None
    if not manifest_resolved.exists() or not packets_resolved.exists():
        return None
    return manifest_resolved, packets_resolved


def _packet_schema_valid(packet: Any) -> bool:
    """``packet_schema_validates`` denominator predicate."""
    if not isinstance(packet, dict):
        return False
    for field in PHASE9N_PACKET_REQUIRED_FIELDS:
        if field not in packet:
            return False
    state = packet.get("outcome_acquisition_state")
    if state not in ("acquired", "unavailable", "invalid"):
        return False
    if not isinstance(packet.get("outcome_observable_acquired"), bool):
        return False
    if not isinstance(packet.get("replacement_needed"), bool):
        return False
    if not isinstance(packet.get("evidence_form_confirmed_source_grounded"), bool):
        return False
    if not isinstance(packet.get("candidate_order_index_private"), int):
        return False
    if not isinstance(packet.get("source_order_index_private"), int):
        return False
    if packet.get(
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels"
    ) is not True:
        return False
    return True


def _read_phase9n_private_packets(
    manifest_path: Path, packets_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Read the Phase 9N private manifest + packets under ignored runs/ only.

    The Phase 9N packets carry only acquisition state + routing precondition
    metadata (no snippets, no observables, no source content).  Reading them
    does not expose outcomes or source identities.
    """
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    manifest_resolved = manifest_path.resolve()
    packets_resolved = packets_path.resolve()
    if runs_root not in manifest_resolved.parents or runs_root not in packets_resolved.parents:
        return {}, [], ["Phase 9N private packets must be under ignored runs/"]
    try:
        manifest = json.loads(manifest_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9N private manifest unreadable"]
    try:
        packets = json.loads(packets_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, [], ["Phase 9N private packets unreadable"]
    if not isinstance(packets, list):
        return {}, [], ["Phase 9N private packets must be a list"]
    errors: list[str] = []
    valid_packets: list[dict[str, Any]] = []
    for index, packet in enumerate(packets):
        if not _packet_schema_valid(packet):
            errors.append(f"Phase 9N packet {index} schema invalid")
            continue
        valid_packets.append(packet)
    return manifest, valid_packets, errors


# ---------------------------------------------------------------------------
# Frozen scoring: apply Phase 9O denominator eligibility + inclusion/exclusion
# ---------------------------------------------------------------------------

def _apply_frozen_scoring(
    packets: list[dict[str, Any]],
    manifest_route_attested: bool,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    """Apply the frozen Phase 9O scoring protocol to the Phase 9N packets.

    Returns (private_scoring_rows, bucket_counts, errors).  The bucket_counts
    are the raw integer counts that are later bucketed into privacy-safe
    aggregate buckets for the public report.
    """
    scoring_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_candidates: set[int] = set()
    source_counts: dict[int, int] = {}
    eligible_total = 0
    included_total = 0
    invalid_excluded_total = 0
    unavailable_excluded_total = 0

    # Deterministic order: candidate_order_index_private ascending.
    ordered = sorted(
        packets, key=lambda p: int(p.get("candidate_order_index_private", -1))
    )
    total = len(ordered)

    for position, packet in enumerate(ordered):
        cand_idx = int(packet["candidate_order_index_private"])
        src_idx = int(packet["source_order_index_private"])
        source_counts[src_idx] = source_counts.get(src_idx, 0) + 1
        state = packet.get("outcome_acquisition_state")

        # Evaluate the frozen denominator-eligibility predicates (exact set
        # carried from Phase 9O).
        preds: dict[str, bool] = {
            "packet_generated_by_single_phase9m_frozen_route_during_phase9n_gated_run": bool(manifest_route_attested),
            "packet_acquisition_state_is_acquired": state == "acquired",
            "packet_validity_state_is_valid": state == "acquired",
            "packet_expected_evidence_form_matches_whitelist": (
                packet.get("expected_evidence_form") in EXPECTED_EVIDENCE_FORM_WHITELIST
            ),
            "packet_source_grounding_checks_pass": (
                packet.get("evidence_form_confirmed_source_grounded") is True
            ),
            "packet_schema_validates": _packet_schema_valid(packet),
            "packet_not_unavailable": state != "unavailable",
            "packet_not_invalid": state != "invalid",
            "packet_not_replacement_needed": packet.get("replacement_needed") is False,
            "packet_not_malformed": _packet_schema_valid(packet),
            "packet_not_duplicate": cand_idx not in seen_candidates,
            "packet_not_outside_route": bool(manifest_route_attested),
            "packet_not_outside_cap": (
                (position + 1) <= HARD_INVENTORY_CAP
                and source_counts[src_idx] <= PER_SOURCE_CAP
            ),
            "packet_not_outside_order_constraints": True,  # deterministic order
        }
        eligible = all(preds.values())
        if eligible:
            eligible_total += 1

        # Frozen inclusion/exclusion rules: include only eligible valid
        # acquired; exclude unavailable/invalid/replacement/schema-invalid/
        # duplicate/out-of-route/cap/order before scoring.
        if state == "unavailable":
            decision = "excluded_unavailable_before_scoring"
            unavailable_excluded_total += 1
        elif state == "invalid":
            decision = "excluded_invalid_before_scoring"
            invalid_excluded_total += 1
        elif packet.get("replacement_needed") is True:
            decision = "excluded_replacement_needed_before_scoring"
            invalid_excluded_total += 1
        elif not preds["packet_schema_validates"]:
            decision = "excluded_schema_invalid_before_scoring"
            invalid_excluded_total += 1
        elif not eligible:
            decision = "excluded_ineligible_before_scoring"
            invalid_excluded_total += 1
        else:
            decision = "included"
            included_total += 1

        seen_candidates.add(cand_idx)
        scoring_rows.append(
            {
                "candidate_order_index_private": cand_idx,
                "source_order_index_private": src_idx,
                "denominator_eligibility_predicates_evaluated_private": preds,
                "denominator_eligible_private": eligible,
                "inclusion_exclusion_decision_private": decision,
                "scored_private": decision == "included",
                "adjudicated_private": False,
                "correctness_evaluated_private": False,
                "evidence_success_evaluated_private": False,
                "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels_private": True,
            }
        )

    distinct_sources = len(source_counts)
    bucket_counts = {
        "denominator": eligible_total,
        "scored": included_total,
        "adjudicated": 0,  # adjudication NOT executed (separate boundary required)
        "invalid_excluded": invalid_excluded_total,
        "unavailable_excluded": unavailable_excluded_total,
        "correctness": 0,  # correctness NOT executed (tied to adjudication)
        "attempted": total,
        "distinct_sources": distinct_sources,
        "hard_cap_respected": total <= HARD_INVENTORY_CAP,
        "per_source_cap_respected": all(
            c <= PER_SOURCE_CAP for c in source_counts.values()
        ),
        "target_bucket_met": TARGET_INVENTORY_MIN <= total <= TARGET_INVENTORY_MAX,
        "diversity_minimum_met": distinct_sources >= MIN_DISTINCT_SOURCES,
    }
    return scoring_rows, bucket_counts, errors


def _build_private_manifest(
    scoring_rows: list[dict[str, Any]],
    bucket_counts: dict[str, int],
    manifest_route_attested: bool,
) -> dict[str, Any]:
    """Build the private scoring manifest (under ignored runs/ only)."""
    return {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "frozen_phase9o_protocol_applied_exactly": True,
        "frozen_phase9o_protocol_loaded_from_committed_module": True,
        "scoring_rows_are_bucketed_availability_only_not_correctness": True,
        "scoring_rows_private": scoring_rows,
        "aggregate_private_totals": bucket_counts,
        "manifest_route_attested_private": bool(manifest_route_attested),
        "adjudication_not_executed_requires_separate_frozen_boundary_after_scoring": True,
        "correctness_not_executed_tied_to_adjudication": True,
        "evidence_success_not_evaluated": True,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
        "phase9j_rows_used_as_benchmark_truth": False,
        "phase9l_packets_scoreable": False,
        "private_phase9l_outcome_packets_read": False,
        "private_phase9h_materialized_sources_read": False,
        "private_phase9j_annotation_input_rows_read": False,
        "provider_or_llm_calls_executed": False,
        "model_fitting_executed": False,
        "network_fetch_or_clone_or_source_refresh_executed": False,
    }


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def _determine_status(
    bucket_counts: dict[str, int],
    phase9o_gate_ok: bool,
    phase9n_gate_ok: bool,
    all_confirmations: bool,
    read_ok: bool,
    schema_ok: bool,
    dry: bool,
) -> str:
    if dry:
        return STATUS_DRY
    if not phase9o_gate_ok or not phase9n_gate_ok:
        return STATUS_GATE_MISSING
    if not all_confirmations or not read_ok or not schema_ok:
        return STATUS_REPAIR
    denominator = int(bucket_counts.get("denominator", 0))
    if denominator <= 0:
        return STATUS_DENOMINATOR_ZERO
    return STATUS_EXECUTED


def build_public_report(
    bucket_counts: dict[str, int],
    phase9o_gate_ok: bool,
    phase9n_gate_ok: bool,
    confirmations: dict[str, bool],
    private_phase9n_packets_read: bool,
    scoring_errors: list[str] | None = None,
    dry: bool = False,
) -> dict[str, Any]:
    """Build the aggregate-only public Phase 9P report."""
    executed = (not dry) and phase9o_gate_ok and phase9n_gate_ok
    all_confirmations = all(confirmations.values()) and len(confirmations) == len(_CONFIRMATION_KEYS)
    schema_ok = not scoring_errors
    status = _determine_status(
        bucket_counts, phase9o_gate_ok, phase9n_gate_ok,
        all_confirmations, private_phase9n_packets_read, schema_ok, dry,
    )
    is_executed = status == STATUS_EXECUTED

    scoring_executed = is_executed
    denominator_computed = is_executed
    ignored_runs_read = private_phase9n_packets_read and is_executed
    private_phase9n_read = private_phase9n_packets_read and is_executed

    caps_ok = (
        bool(bucket_counts.get("hard_cap_respected"))
        and bool(bucket_counts.get("per_source_cap_respected"))
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9o_gate_references": {
            "phase9o_commit": PHASE9O_COMMIT,
            "phase9o_ci_run": PHASE9O_CI_RUN,
            "phase9o_ci_success": True,
            "phase9o_status": PHASE9O_STATUS,
            "phase9o_protocol_freeze": True,
            "phase9o_did_not_execute_scoring_or_adjudication_in_phase9o": True,
            "phase9o_gate_required_before_phase9p": True,
            "phase9o_public_report_validated": phase9o_gate_ok,
        },
        "phase9n_gate_references": {
            "phase9n_commit": PHASE9N_COMMIT,
            "phase9n_ci_run": PHASE9N_CI_RUN,
            "phase9n_ci_success": True,
            "phase9n_status": PHASE9N_STATUS,
            "phase9n_acquired_valid_bucket": PHASE9N_ACQUIRED_VALID_BUCKET,
            "phase9n_acquired_valid_bucket_nonzero": True,
            "phase9n_scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero": True,
            "phase9n_gate_required_before_phase9p": True,
        },
        "inherited_provenance_bucketed": {
            "phase9m_status": PHASE9M_STATUS,
            "phase9m_carried_as_inherited_provenance_only": True,
            "phase9l_status": PHASE9L_STATUS,
            "phase9l_carried_as_inherited_provenance_only": True,
            "phase9k_status": PHASE9K_STATUS,
            "phase9k_carried_as_inherited_provenance_only": True,
            "phase9h_status": PHASE9H_STATUS,
            "phase9h_carried_as_inherited_provenance_only": True,
            "phase9i_status": PHASE9I_STATUS,
            "phase9i_carried_as_inherited_provenance_only": True,
            "phase9j_status": PHASE9J_STATUS,
            "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": True,
            "phase9j_carried_as_inherited_provenance_only": True,
            "phase9g_status": PHASE9G_STATUS,
            "phase9g_carried_as_inherited_provenance_only": True,
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_carried_as_inherited_provenance_only": True,
            "exact_remote_commit_ci_values_intentionally_not_published": True,
        },
        "frozen_protocol_applied": {
            "phase9o_protocol_loaded_from_committed_module": True,
            "protocol_applied_exactly_as_frozen_in_phase9o": True,
            "no_new_metrics_thresholds_or_subgroups": True,
            "no_protocol_edits_after_outcome_visibility": True,
            "no_denominator_repair_after_private_reads": True,
            "denominator_eligibility_predicates": list(DENOMINATOR_ELIGIBILITY_PREDICATES),
            "inclusion_exclusion_rules": list(INCLUSION_EXCLUSION_RULES),
            "scoring_metric_definitions": list(SCORING_METRIC_DEFINITIONS),
            "adjudication_rules": list(ADJUDICATION_RULES),
            "missing_invalid_unavailable_handling_rules": list(MISSING_INVALID_UNAVAILABLE_HANDLING_RULES),
            "privacy_publication_rules": list(PRIVACY_PUBLICATION_RULES),
            "future_phase9p_gate_rules": list(FUTURE_PHASE9P_GATE_RULES),
            "no_p_hacking_guardrail_rules": list(NO_P_HACKING_GUARDRAIL_RULES),
            "inherited_phase9h_aggregate_caps": {
                "target_inventory_bucket": "bucket_48_to_72",
                "hard_cap_bucket": "bucket_up_to_96",
                "per_source_cap_bucket": "bucket_up_to_8",
                "minimum_distinct_sources_bucket": "bucket_at_least_8",
            },
        },
        "confirmation_summary": {
            **{key: confirmations.get(key) is True for key in _CONFIRMATION_KEYS},
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
        },
        "execution_booleans": {
            "scoring_executed": scoring_executed,
            "denominator_computed": denominator_computed,
            "adjudication_executed": False,
            "correctness_evaluated": False,
            "evidence_success_evaluated": False,
            "gold_labels_generated": False,
            "benchmark_labels_generated": False,
            "result_labels_generated": False,
            "annotation_truth_generated": False,
            "private_phase9n_packets_read": private_phase9n_read,
            "ignored_runs_read": ignored_runs_read,
            "phase9j_rows_used_as_benchmark_truth": False,
            "phase9l_packets_scoreable": False,
            "private_phase9l_outcome_packets_read": False,
            "private_phase9h_materialized_sources_read": False,
            "private_phase9j_annotation_input_rows_read": False,
            "private_candidate_pool_read": False,
            "private_registry_read": False,
            "provider_or_llm_calls": False,
            "model_fitting": False,
            "network_fetch_or_clone_or_source_refresh_executed": False,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "runtime_default_or_product_changes": False,
            "new_metrics_introduced": False,
            "new_thresholds_introduced": False,
            "new_subgroups_introduced": False,
            "protocol_edited_after_outcome_visibility": False,
            "denominator_repaired_after_private_reads": False,
        },
        "scoring_buckets": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "denominator_bucket": _bucket(int(bucket_counts.get("denominator", 0))),
            "scored_bucket": _bucket(int(bucket_counts.get("scored", 0))),
            "adjudicated_bucket": _bucket(int(bucket_counts.get("adjudicated", 0))),
            "invalid_excluded_bucket": _bucket(int(bucket_counts.get("invalid_excluded", 0))),
            "unavailable_excluded_bucket": _bucket(int(bucket_counts.get("unavailable_excluded", 0))),
            "correctness_bucket": _bucket(int(bucket_counts.get("correctness", 0))),
            "scoring_metric_definitions_applied_as_bucketed_aggregate_only": True,
            "no_exact_counts_or_rates": True,
            "no_winner_effect_lift_language": True,
            "adjudication_not_executed_requires_separate_frozen_boundary_after_scoring": True,
            "correctness_not_executed_tied_to_adjudication": True,
            "private_scoring_rows_under_ignored_runs_only": True,
            "inherited_phase9h_aggregate_caps_respected": caps_ok,
        },
        "adjudication_boundary": {
            "adjudication_is_deterministic_not_llm_not_provider_not_model": True,
            "adjudication_against_frozen_outcome_observable_packet_only": True,
            "no_phase9j_as_truth": True,
            "no_phase9l_unavailable_packets_scoreable": True,
            "adjudication_not_executed_in_phase9p_requires_separate_frozen_boundary_after_scoring": True,
        },
        "truth_boundary": {key: True for key in TRUTH_BOUNDARY_TRUE_KEYS},
        "no_execution_false_boundary": {key: False for key in NO_EXECUTION_FALSE_KEYS},
        "privacy_summary": {
            "public_output_aggregate_only": True,
            "private_scoring_rows_under_ignored_runs_only": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PRIVACY_FALSE_KEYS},
        },
        "no_claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "validation_summary": {
            "phase9p_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "public_artifact_privacy_audit_expected": True,
            "validator_does_not_fetch_or_read_private_beyond_authorized_phase9n_packets": True,
            "validator_does_not_read_phase9l_outcome_packets": True,
            "validator_does_not_read_phase9h_materialized_sources": True,
            "validator_does_not_read_phase9j_annotation_input_rows": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------

_CONFIRMATION_KEYS = (
    "phase9o_commit_confirmed",
    "phase9o_ci_confirmed",
    "phase9o_status_confirmed",
    "phase9o_protocol_freeze_confirmed",
    "phase9n_commit_confirmed",
    "phase9n_ci_confirmed",
    "phase9n_status_confirmed",
    "phase9n_acquired_valid_bucket_nonzero_confirmed",
    "read_phase9n_private_outcome_observable_packets_confirmed",
    "ignored_runs_read_for_phase9n_packets_only_confirmed",
    "private_output_only_confirmed",
    "aggregate_public_report_only_confirmed",
    "apply_frozen_phase9o_protocol_exactly_confirmed",
    "no_new_metrics_thresholds_subgroups_confirmed",
    "no_protocol_edits_after_outcome_visibility_confirmed",
    "no_adjudication_execution_separate_boundary_required_confirmed",
    "no_provider_llm_model_adjudication_confirmed",
    "no_phase9j_as_truth_confirmed",
    "no_phase9l_unavailable_packets_scoreable_confirmed",
    "no_evidence_success_no_correctness_no_gold_confirmed",
    "no_runtime_default_product_method_performance_claim_confirmed",
    "no_network_fetch_clone_source_refresh_confirmed",
)


def _all_confirmations_dict(
    confirm_phase9o_commit: str | None,
    confirm_phase9o_ci: str | None,
    confirm_phase9o_status: str | None,
    confirm_phase9o_protocol_freeze: bool,
    confirm_phase9n_commit: str | None,
    confirm_phase9n_ci: str | None,
    confirm_phase9n_status: str | None,
    confirm_phase9n_acquired_valid_bucket_nonzero: bool,
    confirm_read_phase9n_private_outcome_observable_packets: bool,
    confirm_ignored_runs_read_for_phase9n_packets_only: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_apply_frozen_phase9o_protocol_exactly: bool,
    confirm_no_new_metrics_thresholds_subgroups: bool,
    confirm_no_protocol_edits_after_outcome_visibility: bool,
    confirm_no_adjudication_execution_separate_boundary_required: bool,
    confirm_no_provider_llm_model_adjudication: bool,
    confirm_no_phase9j_as_truth: bool,
    confirm_no_phase9l_unavailable_packets_scoreable: bool,
    confirm_no_evidence_success_no_correctness_no_gold: bool,
    confirm_no_runtime_default_product_method_performance_claim: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
) -> dict[str, bool]:
    return {
        "phase9o_commit_confirmed": confirm_phase9o_commit == PHASE9O_COMMIT,
        "phase9o_ci_confirmed": confirm_phase9o_ci == PHASE9O_CI_RUN,
        "phase9o_status_confirmed": confirm_phase9o_status == PHASE9O_STATUS,
        "phase9o_protocol_freeze_confirmed": confirm_phase9o_protocol_freeze is True,
        "phase9n_commit_confirmed": confirm_phase9n_commit == PHASE9N_COMMIT,
        "phase9n_ci_confirmed": confirm_phase9n_ci == PHASE9N_CI_RUN,
        "phase9n_status_confirmed": confirm_phase9n_status == PHASE9N_STATUS,
        "phase9n_acquired_valid_bucket_nonzero_confirmed": confirm_phase9n_acquired_valid_bucket_nonzero is True,
        "read_phase9n_private_outcome_observable_packets_confirmed": confirm_read_phase9n_private_outcome_observable_packets is True,
        "ignored_runs_read_for_phase9n_packets_only_confirmed": confirm_ignored_runs_read_for_phase9n_packets_only is True,
        "private_output_only_confirmed": confirm_private_output_only is True,
        "aggregate_public_report_only_confirmed": confirm_aggregate_public_report_only is True,
        "apply_frozen_phase9o_protocol_exactly_confirmed": confirm_apply_frozen_phase9o_protocol_exactly is True,
        "no_new_metrics_thresholds_subgroups_confirmed": confirm_no_new_metrics_thresholds_subgroups is True,
        "no_protocol_edits_after_outcome_visibility_confirmed": confirm_no_protocol_edits_after_outcome_visibility is True,
        "no_adjudication_execution_separate_boundary_required_confirmed": confirm_no_adjudication_execution_separate_boundary_required is True,
        "no_provider_llm_model_adjudication_confirmed": confirm_no_provider_llm_model_adjudication is True,
        "no_phase9j_as_truth_confirmed": confirm_no_phase9j_as_truth is True,
        "no_phase9l_unavailable_packets_scoreable_confirmed": confirm_no_phase9l_unavailable_packets_scoreable is True,
        "no_evidence_success_no_correctness_no_gold_confirmed": confirm_no_evidence_success_no_correctness_no_gold is True,
        "no_runtime_default_product_method_performance_claim_confirmed": confirm_no_runtime_default_product_method_performance_claim is True,
        "no_network_fetch_clone_source_refresh_confirmed": confirm_no_network_fetch_clone_source_refresh is True,
    }


# ---------------------------------------------------------------------------
# Strict allowed-key schema + privacy scan + validation
# ---------------------------------------------------------------------------

ALLOWED_REPORT_KEYS: dict[str, Any] = {
    "schema_version": None,
    "phase": None,
    "status": None,
    "phase9o_gate_references": {
        "phase9o_commit": None,
        "phase9o_ci_run": None,
        "phase9o_ci_success": None,
        "phase9o_status": None,
        "phase9o_protocol_freeze": None,
        "phase9o_did_not_execute_scoring_or_adjudication_in_phase9o": None,
        "phase9o_gate_required_before_phase9p": None,
        "phase9o_public_report_validated": None,
    },
    "phase9n_gate_references": {
        "phase9n_commit": None,
        "phase9n_ci_run": None,
        "phase9n_ci_success": None,
        "phase9n_status": None,
        "phase9n_acquired_valid_bucket": None,
        "phase9n_acquired_valid_bucket_nonzero": None,
        "phase9n_scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero": None,
        "phase9n_gate_required_before_phase9p": None,
    },
    "inherited_provenance_bucketed": {
        "phase9m_status": None,
        "phase9m_carried_as_inherited_provenance_only": None,
        "phase9l_status": None,
        "phase9l_carried_as_inherited_provenance_only": None,
        "phase9k_status": None,
        "phase9k_carried_as_inherited_provenance_only": None,
        "phase9h_status": None,
        "phase9h_carried_as_inherited_provenance_only": None,
        "phase9i_status": None,
        "phase9i_carried_as_inherited_provenance_only": None,
        "phase9j_status": None,
        "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": None,
        "phase9j_carried_as_inherited_provenance_only": None,
        "phase9g_status": None,
        "phase9g_carried_as_inherited_provenance_only": None,
        "phase9f_status": None,
        "phase9f_carried_as_inherited_provenance_only": None,
        "exact_remote_commit_ci_values_intentionally_not_published": None,
    },
    "frozen_protocol_applied": {
        "phase9o_protocol_loaded_from_committed_module": None,
        "protocol_applied_exactly_as_frozen_in_phase9o": None,
        "no_new_metrics_thresholds_or_subgroups": None,
        "no_protocol_edits_after_outcome_visibility": None,
        "no_denominator_repair_after_private_reads": None,
        "denominator_eligibility_predicates": None,
        "inclusion_exclusion_rules": None,
        "scoring_metric_definitions": None,
        "adjudication_rules": None,
        "missing_invalid_unavailable_handling_rules": None,
        "privacy_publication_rules": None,
        "future_phase9p_gate_rules": None,
        "no_p_hacking_guardrail_rules": None,
        "inherited_phase9h_aggregate_caps": {
            "target_inventory_bucket": None,
            "hard_cap_bucket": None,
            "per_source_cap_bucket": None,
            "minimum_distinct_sources_bucket": None,
        },
    },
    "confirmation_summary": {
        **{key: None for key in _CONFIRMATION_KEYS},
        "all_required_confirmations_present": None,
        "dry_self_test_and_report_validation_read_private_runs": None,
        "dry_self_test_and_report_validation_fetch_or_clone": None,
    },
    "execution_booleans": {
        "scoring_executed": None,
        "denominator_computed": None,
        "adjudication_executed": None,
        "correctness_evaluated": None,
        "evidence_success_evaluated": False,
        "gold_labels_generated": None,
        "benchmark_labels_generated": None,
        "result_labels_generated": None,
        "annotation_truth_generated": None,
        "private_phase9n_packets_read": None,
        "ignored_runs_read": None,
        "phase9j_rows_used_as_benchmark_truth": None,
        "phase9l_packets_scoreable": None,
        "private_phase9l_outcome_packets_read": None,
        "private_phase9h_materialized_sources_read": None,
        "private_phase9j_annotation_input_rows_read": None,
        "private_candidate_pool_read": None,
        "private_registry_read": None,
        "provider_or_llm_calls": None,
        "model_fitting": None,
        "network_fetch_or_clone_or_source_refresh_executed": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "runtime_default_or_product_changes": None,
        "new_metrics_introduced": None,
        "new_thresholds_introduced": None,
        "new_subgroups_introduced": None,
        "protocol_edited_after_outcome_visibility": None,
        "denominator_repaired_after_private_reads": None,
    },
    "scoring_buckets": {
        "publication_level": None,
        "denominator_bucket": None,
        "scored_bucket": None,
        "adjudicated_bucket": None,
        "invalid_excluded_bucket": None,
        "unavailable_excluded_bucket": None,
        "correctness_bucket": None,
        "scoring_metric_definitions_applied_as_bucketed_aggregate_only": None,
        "no_exact_counts_or_rates": None,
        "no_winner_effect_lift_language": None,
        "adjudication_not_executed_requires_separate_frozen_boundary_after_scoring": None,
        "correctness_not_executed_tied_to_adjudication": None,
        "private_scoring_rows_under_ignored_runs_only": None,
        "inherited_phase9h_aggregate_caps_respected": None,
    },
    "adjudication_boundary": {
        "adjudication_is_deterministic_not_llm_not_provider_not_model": None,
        "adjudication_against_frozen_outcome_observable_packet_only": None,
        "no_phase9j_as_truth": None,
        "no_phase9l_unavailable_packets_scoreable": None,
        "adjudication_not_executed_in_phase9p_requires_separate_frozen_boundary_after_scoring": None,
    },
    "truth_boundary": {key: None for key in TRUTH_BOUNDARY_TRUE_KEYS},
    "no_execution_false_boundary": {key: None for key in NO_EXECUTION_FALSE_KEYS},
    "privacy_summary": {
        "public_output_aggregate_only": None,
        "private_scoring_rows_under_ignored_runs_only": None,
        "runs_remains_ignored": None,
        **{key: None for key in PRIVACY_FALSE_KEYS},
    },
    "no_claim_boundary": {key: None for key in CLAIM_BOUNDARY_FALSE_KEYS},
    "validation_summary": {
        "phase9p_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "public_artifact_privacy_audit_expected": None,
        "validator_does_not_fetch_or_read_private_beyond_authorized_phase9n_packets": None,
        "validator_does_not_read_phase9l_outcome_packets": None,
        "validator_does_not_read_phase9h_materialized_sources": None,
        "validator_does_not_read_phase9j_annotation_input_rows": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
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
    if key_lower.endswith("_rate"):
        errors.append(f"exact public rate field at {path}")
    if not isinstance(value, bool) and not is_allowed_path and any(
        word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS
    ):
        errors.append(f"forbidden public field word at {path}")
    if key and THRESHOLD_KEY_RE.search(key) and not is_allowed_path:
        errors.append(f"threshold-shaped public key at {path}")
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

    # Phase 9O gate references (PRIMARY whitelisted public gate refs).
    gate9o = report.get("phase9o_gate_references", {})
    if gate9o.get("phase9o_commit") != PHASE9O_COMMIT:
        errors.append("Phase 9O commit gate reference drift")
    if gate9o.get("phase9o_ci_run") != PHASE9O_CI_RUN:
        errors.append("Phase 9O CI run gate reference drift")
    if gate9o.get("phase9o_ci_success") is not True:
        errors.append("Phase 9O CI success gate missing")
    if gate9o.get("phase9o_status") != PHASE9O_STATUS:
        errors.append("Phase 9O status gate reference drift")
    if gate9o.get("phase9o_protocol_freeze") is not True:
        errors.append("Phase 9O protocol freeze gate missing")
    if gate9o.get("phase9o_did_not_execute_scoring_or_adjudication_in_phase9o") is not True:
        errors.append("Phase 9O no-execution boundary missing")
    if gate9o.get("phase9o_gate_required_before_phase9p") is not True:
        errors.append("Phase 9O gate-required boundary missing")

    # Phase 9N gate references (secondary, whitelisted).
    gate9n = report.get("phase9n_gate_references", {})
    if gate9n.get("phase9n_commit") != PHASE9N_COMMIT:
        errors.append("Phase 9N commit gate reference drift")
    if gate9n.get("phase9n_ci_run") != PHASE9N_CI_RUN:
        errors.append("Phase 9N CI run gate reference drift")
    if gate9n.get("phase9n_ci_success") is not True:
        errors.append("Phase 9N CI success gate missing")
    if gate9n.get("phase9n_status") != PHASE9N_STATUS:
        errors.append("Phase 9N status gate reference drift")
    if gate9n.get("phase9n_acquired_valid_bucket") != PHASE9N_ACQUIRED_VALID_BUCKET:
        errors.append("Phase 9N acquired_valid_bucket public fact drift")
    if gate9n.get("phase9n_acquired_valid_bucket_nonzero") is not True:
        errors.append("Phase 9N acquired_valid_bucket_nonzero gate missing")
    if gate9n.get("phase9n_scoring_protocol_may_be_considered_only_if_acquired_valid_bucket_nonzero") is not True:
        errors.append("Phase 9N scoring-protocol-may-be-considered gate missing")
    if gate9n.get("phase9n_gate_required_before_phase9p") is not True:
        errors.append("Phase 9N gate-required boundary missing")

    # Inherited provenance (bucketed only).
    prov = report.get("inherited_provenance_bucketed", {})
    for phase_key, expected_status in (
        ("phase9m_status", PHASE9M_STATUS),
        ("phase9l_status", PHASE9L_STATUS),
        ("phase9k_status", PHASE9K_STATUS),
        ("phase9h_status", PHASE9H_STATUS),
        ("phase9i_status", PHASE9I_STATUS),
        ("phase9j_status", PHASE9J_STATUS),
        ("phase9g_status", PHASE9G_STATUS),
        ("phase9f_status", PHASE9F_STATUS),
    ):
        if prov.get(phase_key) != expected_status:
            errors.append(f"inherited provenance {phase_key} drift")

    # Frozen protocol applied (closed-list set-equality vs Phase 9O).
    proto = report.get("frozen_protocol_applied", {})
    for key in (
        "phase9o_protocol_loaded_from_committed_module",
        "protocol_applied_exactly_as_frozen_in_phase9o",
        "no_new_metrics_thresholds_or_subgroups",
        "no_protocol_edits_after_outcome_visibility",
        "no_denominator_repair_after_private_reads",
    ):
        if proto.get(key) is not True:
            errors.append(f"frozen protocol applied boundary missing: {key}")
    for _section, key, expected, _label in CLOSED_PROTOCOL_LISTS:
        errors.extend(_check_closed_list(proto.get(key), expected, "frozen_protocol_applied", key))
    caps = proto.get("inherited_phase9h_aggregate_caps", {})
    expected_caps = {
        "target_inventory_bucket": "bucket_48_to_72",
        "hard_cap_bucket": "bucket_up_to_96",
        "per_source_cap_bucket": "bucket_up_to_8",
        "minimum_distinct_sources_bucket": "bucket_at_least_8",
    }
    for cap_key, expected in expected_caps.items():
        if caps.get(cap_key) != expected:
            errors.append(f"inherited phase9h aggregate cap drift: {cap_key}")

    # Confirmation summary.
    conf = report.get("confirmation_summary", {})
    for key in _CONFIRMATION_KEYS:
        if conf.get(key) is not True:
            errors.append(f"confirmation missing or not true: {key}")

    # Execution booleans.
    execs = report.get("execution_booleans", {})
    status = report.get("status")
    if status == STATUS_EXECUTED:
        for key in ("scoring_executed", "denominator_computed"):
            if execs.get(key) is not True:
                errors.append(f"executed status requires {key} True")
        if execs.get("private_phase9n_packets_read") is not True:
            errors.append("executed status requires private_phase9n_packets_read True")
        if execs.get("ignored_runs_read") is not True:
            errors.append("executed status requires ignored_runs_read True")
    else:
        for key in ("scoring_executed", "denominator_computed", "private_phase9n_packets_read", "ignored_runs_read"):
            if execs.get(key) is True:
                errors.append(f"non-executed status must not set {key} True")
    # Forbidden execution boundaries (always False).
    for key in NO_EXECUTION_FALSE_KEYS:
        if execs.get(key) is not False:
            errors.append(f"forbidden execution boundary failed: {key}")

    # Scoring buckets.
    buckets = report.get("scoring_buckets", {})
    for key in SCORING_BUCKET_NAMES:
        val = buckets.get(key)
        if val not in ("bucket_zero", "bucket_nonzero_redacted"):
            errors.append(f"scoring bucket must be bucket_zero or bucket_nonzero_redacted: {key}")
    # Executed status: denominator and scored nonzero; adjudicated/correctness zero.
    if status == STATUS_EXECUTED:
        if buckets.get("denominator_bucket") != "bucket_nonzero_redacted":
            errors.append("executed status requires denominator_bucket nonzero")
        if buckets.get("scored_bucket") != "bucket_nonzero_redacted":
            errors.append("executed status requires scored_bucket nonzero")
        if buckets.get("adjudicated_bucket") != "bucket_zero":
            errors.append("executed status requires adjudicated_bucket zero (not executed)")
        if buckets.get("correctness_bucket") != "bucket_zero":
            errors.append("executed status requires correctness_bucket zero (not executed)")
    for key in (
        "scoring_metric_definitions_applied_as_bucketed_aggregate_only",
        "no_exact_counts_or_rates",
        "no_winner_effect_lift_language",
        "adjudication_not_executed_requires_separate_frozen_boundary_after_scoring",
        "correctness_not_executed_tied_to_adjudication",
        "private_scoring_rows_under_ignored_runs_only",
    ):
        if buckets.get(key) is not True:
            errors.append(f"scoring bucket boundary missing: {key}")

    # Adjudication boundary.
    adj = report.get("adjudication_boundary", {})
    for key in (
        "adjudication_is_deterministic_not_llm_not_provider_not_model",
        "adjudication_against_frozen_outcome_observable_packet_only",
        "no_phase9j_as_truth",
        "no_phase9l_unavailable_packets_scoreable",
        "adjudication_not_executed_in_phase9p_requires_separate_frozen_boundary_after_scoring",
    ):
        if adj.get(key) is not True:
            errors.append(f"adjudication boundary missing: {key}")

    # Truth boundary.
    truth = report.get("truth_boundary", {})
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        if truth.get(key) is not True:
            errors.append(f"truth boundary failed: {key}")

    # No-execution false boundary.
    no_exec = report.get("no_execution_false_boundary", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_exec.get(key) is not False:
            errors.append(f"no_execution_false boundary failed: {key}")

    # Privacy summary.
    privacy = report.get("privacy_summary", {})
    for key in (
        "public_output_aggregate_only",
        "private_scoring_rows_under_ignored_runs_only",
        "runs_remains_ignored",
    ):
        if privacy.get(key) is not True:
            errors.append(f"privacy summary missing: {key}")
    for key in PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"privacy contract boundary failed: {key}")

    # No-claim boundary.
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("no_claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    # Validation summary.
    validation = report.get("validation_summary", {})
    for key in (
        "phase9p_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "public_artifact_privacy_audit_expected",
        "validator_does_not_fetch_or_read_private_beyond_authorized_phase9n_packets",
        "validator_does_not_read_phase9l_outcome_packets",
        "validator_does_not_read_phase9h_materialized_sources",
        "validator_does_not_read_phase9j_annotation_input_rows",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in (
        "validator_executes_tasks",
        "validator_reads_private_registry",
        "validator_reads_sources",
    ):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    # Conservative recommendation.
    if report.get("conservative_recommendation") != CONSERVATIVE_RECOMMENDATION:
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--validate-report``.

    The report path must be under the Phase 9P public artifact directory
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
        return False, "report path is not under the Phase 9P public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _empty_bucket_counts() -> dict[str, int]:
    return {
        "denominator": 0,
        "scored": 0,
        "adjudicated": 0,
        "invalid_excluded": 0,
        "unavailable_excluded": 0,
        "correctness": 0,
        "attempted": 0,
        "distinct_sources": 0,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
    }


def execute_phase9p(
    private_run_dir: Path,
    public_report: Path,
    confirm_phase9o_commit: str | None,
    confirm_phase9o_ci: str | None,
    confirm_phase9o_status: str | None,
    confirm_phase9o_protocol_freeze: bool,
    confirm_phase9n_commit: str | None,
    confirm_phase9n_ci: str | None,
    confirm_phase9n_status: str | None,
    confirm_phase9n_acquired_valid_bucket_nonzero: bool,
    confirm_read_phase9n_private_outcome_observable_packets: bool,
    confirm_ignored_runs_read_for_phase9n_packets_only: bool,
    confirm_private_output_only: bool,
    confirm_aggregate_public_report_only: bool,
    confirm_apply_frozen_phase9o_protocol_exactly: bool,
    confirm_no_new_metrics_thresholds_subgroups: bool,
    confirm_no_protocol_edits_after_outcome_visibility: bool,
    confirm_no_adjudication_execution_separate_boundary_required: bool,
    confirm_no_provider_llm_model_adjudication: bool,
    confirm_no_phase9j_as_truth: bool,
    confirm_no_phase9l_unavailable_packets_scoreable: bool,
    confirm_no_evidence_success_no_correctness_no_gold: bool,
    confirm_no_runtime_default_product_method_performance_claim: bool,
    confirm_no_network_fetch_clone_source_refresh: bool,
    dry: bool = False,
) -> dict[str, Any]:
    confirmations = _all_confirmations_dict(
        confirm_phase9o_commit, confirm_phase9o_ci, confirm_phase9o_status,
        confirm_phase9o_protocol_freeze,
        confirm_phase9n_commit, confirm_phase9n_ci, confirm_phase9n_status,
        confirm_phase9n_acquired_valid_bucket_nonzero,
        confirm_read_phase9n_private_outcome_observable_packets,
        confirm_ignored_runs_read_for_phase9n_packets_only,
        confirm_private_output_only,
        confirm_aggregate_public_report_only,
        confirm_apply_frozen_phase9o_protocol_exactly,
        confirm_no_new_metrics_thresholds_subgroups,
        confirm_no_protocol_edits_after_outcome_visibility,
        confirm_no_adjudication_execution_separate_boundary_required,
        confirm_no_provider_llm_model_adjudication,
        confirm_no_phase9j_as_truth,
        confirm_no_phase9l_unavailable_packets_scoreable,
        confirm_no_evidence_success_no_correctness_no_gold,
        confirm_no_runtime_default_product_method_performance_claim,
        confirm_no_network_fetch_clone_source_refresh,
    )
    missing = [name for name, ok in confirmations.items() if not ok]
    if missing:
        raise ValueError("missing required confirmation(s): " + ", ".join(missing))

    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    public_report.parent.mkdir(parents=True, exist_ok=True)

    # Validate Phase 9O gate (read tracked public report only).
    phase9o_errors = _phase9o_gate_errors(
        supplied_commit=confirm_phase9o_commit,
        supplied_ci=confirm_phase9o_ci,
        supplied_status=confirm_phase9o_status,
    )
    phase9o_gate_ok = not phase9o_errors

    # Validate Phase 9N gate references (matched against constants).
    phase9n_errors = _phase9n_gate_errors(
        confirm_phase9n_commit, confirm_phase9n_ci, confirm_phase9n_status,
        confirm_phase9n_acquired_valid_bucket_nonzero,
    )
    phase9n_gate_ok = not phase9n_errors

    # Dry/no-private mode: no runs/ read, no scoring, no denominator.
    if dry:
        bucket_counts = _empty_bucket_counts()
        report = build_public_report(
            bucket_counts, phase9o_gate_ok, phase9n_gate_ok, confirmations,
            private_phase9n_packets_read=False, dry=True,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError("generated dry report invalid: " + "; ".join(errors[:12]))
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "private_output_under_ignored_runs": False,
            "dry_run": True,
        }

    if not phase9o_gate_ok or not phase9n_gate_ok:
        bucket_counts = _empty_bucket_counts()
        report = build_public_report(
            bucket_counts, phase9o_gate_ok, phase9n_gate_ok, confirmations,
            private_phase9n_packets_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError("generated gate-missing report invalid: " + "; ".join(errors[:12]))
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9p_gate_missing_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9o_or_phase9n_gate_missing_or_not_green",
                "phase9o_gate_errors_private": phase9o_errors,
                "phase9n_gate_errors_private": phase9n_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "private_output_under_ignored_runs": True,
        }

    # Locate and read the Phase 9N private outcome-observable packets.
    n_loc = _find_phase9n_private_packets()
    if n_loc is None:
        bucket_counts = _empty_bucket_counts()
        report = build_public_report(
            bucket_counts, phase9o_gate_ok, phase9n_gate_ok, confirmations,
            private_phase9n_packets_read=False,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError("generated no-packets report invalid: " + "; ".join(errors[:12]))
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9p_no_phase9n_packets_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9n_private_packets_missing_or_not_under_ignored_runs",
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "private_output_under_ignored_runs": True,
        }

    n_manifest_path, n_packets_path = n_loc
    n_manifest, n_packets, read_errors = _read_phase9n_private_packets(
        n_manifest_path, n_packets_path
    )

    if read_errors or not n_packets:
        bucket_counts = _empty_bucket_counts()
        report = build_public_report(
            bucket_counts, phase9o_gate_ok, phase9n_gate_ok, confirmations,
            private_phase9n_packets_read=bool(n_packets),
            scoring_errors=read_errors or ["no_valid_phase9n_packets"],
        )
        errors = validate_report(report)
        if errors:
            raise ValueError("generated packets-invalid report invalid: " + "; ".join(errors[:12]))
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9p_packets_invalid_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "phase9n_packets_schema_invalid_or_empty",
                "phase9n_read_errors_private": read_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "private_output_under_ignored_runs": True,
        }

    # Manifest route attestation (single frozen Phase 9M route during 9N run).
    manifest_route_attested = bool(
        n_manifest.get("frozen_route_executed_single_fixed_route_no_fallback_no_retry")
    ) if isinstance(n_manifest, dict) else False

    # Apply the frozen Phase 9O scoring protocol (denominator + inclusion/excl).
    scoring_rows, bucket_counts, scoring_errors = _apply_frozen_scoring(
        n_packets, manifest_route_attested
    )

    if scoring_errors:
        report = build_public_report(
            bucket_counts, phase9o_gate_ok, phase9n_gate_ok, confirmations,
            private_phase9n_packets_read=True, scoring_errors=scoring_errors,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError("generated scoring-error report invalid: " + "; ".join(errors[:12]))
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9p_scoring_error_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "scoring_could_not_be_applied_exactly_as_frozen",
                "scoring_errors_private": scoring_errors,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "private_output_under_ignored_runs": True,
        }

    # Failure behavior: denominator zero -> stop with repair/no-claim.
    if int(bucket_counts.get("denominator", 0)) <= 0:
        report = build_public_report(
            bucket_counts, phase9o_gate_ok, phase9n_gate_ok, confirmations,
            private_phase9n_packets_read=True,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError("generated denominator-zero report invalid: " + "; ".join(errors[:12]))
        private_run_dir.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9p_denominator_zero_manifest.json").write_text(
            json.dumps({
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "private_stop_reason": "denominator_zero_no_scoring_applied",
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "private_output_under_ignored_runs": True,
        }

    # Build the public report (bucketed aggregate only).
    report = build_public_report(
        bucket_counts, phase9o_gate_ok, phase9n_gate_ok, confirmations,
        private_phase9n_packets_read=True,
    )
    errors = validate_report(report)
    if errors:
        raise ValueError("generated public report invalid: " + "; ".join(errors[:12]))

    # Write private scoring manifest + rows under ignored runs/ only.
    private_manifest = _build_private_manifest(
        scoring_rows, bucket_counts, manifest_route_attested
    )
    private_run_dir.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_phase9p_scoring_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (private_run_dir / "private_phase9p_scoring_rows.json").write_text(
        json.dumps(scoring_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    public_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": report["status"],
        "public_report": str(public_report),
        "public_denominator_bucket": report["scoring_buckets"]["denominator_bucket"],
        "public_scored_bucket": report["scoring_buckets"]["scored_bucket"],
        "public_adjudicated_bucket": report["scoring_buckets"]["adjudicated_bucket"],
        "public_invalid_excluded_bucket": report["scoring_buckets"]["invalid_excluded_bucket"],
        "public_unavailable_excluded_bucket": report["scoring_buckets"]["unavailable_excluded_bucket"],
        "public_correctness_bucket": report["scoring_buckets"]["correctness_bucket"],
        "private_output_under_ignored_runs": True,
    }


# ---------------------------------------------------------------------------
# Synthetic fixtures for self-test
# ---------------------------------------------------------------------------

def _synthetic_phase9n_packet(index: int, source_index: int = 0, state: str = "acquired") -> dict[str, Any]:
    return {
        "private_annotation_input_ref": f"synthetic_ref_{index}",
        "source_order_index_private": source_index,
        "candidate_order_index_private": index,
        "task_eligibility_routing_precondition_only": (
            "eligible_for_future_annotation_acquisition"
            "_routing_precondition_only_not_benchmark_truth"
        ),
        "evidence_localization_requirement": "file_localized_code_evidence_required",
        "expected_evidence_form": EXPECTED_EVIDENCE_FORM_WHITELIST[0],
        "outcome_acquisition_precondition": "future_separate_boundary_required_no_outcomes_in_phase9j",
        "annotation_input_metadata_reference": (
            "phase9j_annotation_input_row_routing_precondition_only_not_benchmark_truth"
        ),
        "outcome_acquisition_state": state,
        "outcome_observable_acquired": state == "acquired",
        "replacement_needed": state == "invalid",
        "evidence_form_confirmed_source_grounded": state == "acquired",
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
    }


def _synthetic_manifest(route_attested: bool = True) -> dict[str, Any]:
    return {
        "frozen_route_executed_single_fixed_route_no_fallback_no_retry": route_attested,
        "no_scoring_no_adjudication_no_evidence_success_no_gold_no_result_labels": True,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, NETWORK_CALL_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    global PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS
    global PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    NETWORK_CALL_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    full_confirmations = _all_confirmations_dict(
        PHASE9O_COMMIT, PHASE9O_CI_RUN, PHASE9O_STATUS, True,
        PHASE9N_COMMIT, PHASE9N_CI_RUN, PHASE9N_STATUS, True,
        True, True, True, True, True, True, True, True, True, True, True, True, True, True,
    )

    # --- valid executed report (synthetic counts deliberately unrelated to
    # the private Phase 9P internals; never the real denominator/source). ---
    valid_counts = {
        "denominator": 12,
        "scored": 12,
        "adjudicated": 0,
        "invalid_excluded": 0,
        "unavailable_excluded": 0,
        "correctness": 0,
        "attempted": 12,
        "distinct_sources": 5,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "target_bucket_met": False,
        "diversity_minimum_met": False,
    }
    valid_report = build_public_report(
        valid_counts, True, True, full_confirmations,
        private_phase9n_packets_read=True,
    )
    checks.append(("valid_executed_report_passes", not validate_report(valid_report)))
    checks.append(("valid_report_is_executed_status", valid_report["status"] == STATUS_EXECUTED))
    checks.append(("valid_report_scoring_executed_true", valid_report["execution_booleans"]["scoring_executed"] is True))
    checks.append(("valid_report_denominator_computed_true", valid_report["execution_booleans"]["denominator_computed"] is True))
    checks.append(("valid_report_private_phase9n_read_true", valid_report["execution_booleans"]["private_phase9n_packets_read"] is True))
    checks.append(("valid_report_ignored_runs_read_true", valid_report["execution_booleans"]["ignored_runs_read"] is True))
    checks.append(("valid_report_adjudication_executed_false", valid_report["execution_booleans"]["adjudication_executed"] is False))
    checks.append(("valid_report_correctness_evaluated_false", valid_report["execution_booleans"]["correctness_evaluated"] is False))
    checks.append(("valid_report_evidence_success_evaluated_false", valid_report["execution_booleans"]["evidence_success_evaluated"] is False))
    checks.append(("valid_report_phase9j_not_truth", valid_report["execution_booleans"]["phase9j_rows_used_as_benchmark_truth"] is False))
    checks.append(("valid_report_phase9l_not_scoreable", valid_report["execution_booleans"]["phase9l_packets_scoreable"] is False))
    checks.append(("valid_report_denominator_nonzero_bucket", valid_report["scoring_buckets"]["denominator_bucket"] == "bucket_nonzero_redacted"))
    checks.append(("valid_report_scored_nonzero_bucket", valid_report["scoring_buckets"]["scored_bucket"] == "bucket_nonzero_redacted"))
    checks.append(("valid_report_adjudicated_zero_bucket", valid_report["scoring_buckets"]["adjudicated_bucket"] == "bucket_zero"))
    checks.append(("valid_report_correctness_zero_bucket", valid_report["scoring_buckets"]["correctness_bucket"] == "bucket_zero"))
    checks.append(("valid_report_invalid_excluded_zero_bucket", valid_report["scoring_buckets"]["invalid_excluded_bucket"] == "bucket_zero"))
    checks.append(("valid_report_unavailable_excluded_zero_bucket", valid_report["scoring_buckets"]["unavailable_excluded_bucket"] == "bucket_zero"))

    # --- dry-run report ---
    dry_report = build_public_report(
        _empty_bucket_counts(), True, True, full_confirmations,
        private_phase9n_packets_read=False, dry=True,
    )
    checks.append(("dry_report_passes", not validate_report(dry_report)))
    checks.append(("dry_report_is_dry_status", dry_report["status"] == STATUS_DRY))
    checks.append(("dry_report_scoring_executed_false", dry_report["execution_booleans"]["scoring_executed"] is False))
    checks.append(("dry_report_denominator_computed_false", dry_report["execution_booleans"]["denominator_computed"] is False))
    checks.append(("dry_report_private_phase9n_read_false", dry_report["execution_booleans"]["private_phase9n_packets_read"] is False))

    # --- gate-missing report ---
    gate_missing_report = build_public_report(
        _empty_bucket_counts(), False, False, full_confirmations,
        private_phase9n_packets_read=False,
    )
    checks.append(("gate_missing_report_passes", not validate_report(gate_missing_report)))
    checks.append(("gate_missing_report_is_gate_missing_status", gate_missing_report["status"] == STATUS_GATE_MISSING))

    # --- denominator-zero report ---
    zero_counts = dict(valid_counts, denominator=0, scored=0)
    zero_report = build_public_report(
        zero_counts, True, True, full_confirmations,
        private_phase9n_packets_read=True,
    )
    checks.append(("denominator_zero_report_passes", not validate_report(zero_report)))
    checks.append(("denominator_zero_report_is_denominator_zero_status", zero_report["status"] == STATUS_DENOMINATOR_ZERO))
    checks.append(("denominator_zero_report_scoring_executed_false", zero_report["execution_booleans"]["scoring_executed"] is False))

    # --- gate ref drift rejected (Phase 9O and Phase 9N commit/ci/status) ---
    for field, bad_val, label in (
        ("phase9o_commit", "deadbeef" * 5, "phase9o_commit"),
        ("phase9o_ci_run", "0000", "phase9o_ci"),
        ("phase9o_status", "drift", "phase9o_status"),
        ("phase9n_commit", "deadbeef" * 5, "phase9n_commit"),
        ("phase9n_ci_run", "0000", "phase9n_ci"),
        ("phase9n_status", "drift", "phase9n_status"),
        ("phase9n_acquired_valid_bucket", "bucket_wrong", "phase9n_acquired_valid_bucket"),
    ):
        section = "phase9o_gate_references" if label.startswith("phase9o") else "phase9n_gate_references"
        mutated = copy.deepcopy(valid_report)
        mutated[section][field] = bad_val
        checks.append((f"wrong_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(valid_report)
        del mutated[section][field]
        checks.append((f"missing_{label}_rejected", bool(validate_report(mutated))))

    # --- status/phase/schema drift rejected ---
    for field, bad in (("status", "drift"), ("phase", "drift"), ("schema_version", "drift")):
        mutated = copy.deepcopy(valid_report)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # --- forbidden execution boundary true rejected ---
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(valid_report)
        mutated["execution_booleans"][exec_key] = True
        mutated["no_execution_false_boundary"][exec_key] = True
        checks.append((f"forbidden_exec_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # --- scoring_executed true on non-executed status rejected ---
    for status_key in (STATUS_DRY, STATUS_GATE_MISSING, STATUS_DENOMINATOR_ZERO):
        mutated = copy.deepcopy(valid_report)
        mutated["status"] = status_key
        checks.append((f"{status_key}_with_scoring_true_rejected", bool(validate_report(mutated))))

    # --- claim boundary true rejected ---
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(valid_report)
        mutated["no_claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- privacy contract violations rejected ---
    for privacy_key in (
        "per_source_public_facts",
        "per_task_public_facts",
        "per_packet_public_facts",
        "run_locations_public",
        "repo_names_public",
        "outcome_observables_public",
        "outcome_packets_public",
        "phase9n_packets_public",
        "phase9l_packets_public",
        "packet_ids_public",
        "exact_counts_or_rates_public",
        "singleton_buckets_public",
    ):
        mutated = copy.deepcopy(valid_report)
        mutated["privacy_summary"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # --- singleton buckets rejected ---
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(valid_report)
        mutated["scoring_buckets"]["denominator_bucket"] = singleton_val
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # --- exact count / rate fields rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["scoring_buckets"]["count"] = 12
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(valid_report)
    mutated["scoring_buckets"]["denominator_count"] = 12
    checks.append(("denominator_count_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(valid_report)
    mutated["scoring_buckets"]["scored_rate"] = "rate_50pct"
    checks.append(("scored_rate_field_rejected", bool(validate_report(mutated))))

    # --- private-shaped public values rejected ---
    for label, bad_val in (
        ("url", "https://example.invalid/repo.git"),
        ("owner_repo", "owner/repo"),
        ("hash", "a" * 40),
        ("path", "src/private.py"),
        ("observable_id", "observable_id_42"),
        ("packet_id", "packet_id_99"),
        ("run_dir", "runs/secret/run_dir"),
    ):
        mutated = copy.deepcopy(valid_report)
        mutated["scoring_buckets"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # --- private-shaped keys rejected ---
    for bad_key in ("private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket", "per_task_summary", "per_packet_summary", "source_path_bucket", "path", "repo_name", "task_id", "row_id", "packet_id", "manifest", "run_dir"):
        mutated = copy.deepcopy(valid_report)
        mutated["scoring_buckets"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- threshold-shaped keys rejected (no new thresholds) ---
    for bad_key in ("score_threshold", "denominator_threshold", "decision_threshold"):
        mutated = copy.deepcopy(valid_report)
        mutated["scoring_buckets"][bad_key] = "example"
        checks.append((f"threshold_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- new metric field rejected (no new metrics; allowed-key schema) ---
    mutated = copy.deepcopy(valid_report)
    mutated["scoring_buckets"]["novel_metric_bucket"] = "bucket_nonzero_redacted"
    checks.append(("new_metric_field_rejected", bool(validate_report(mutated))))

    # --- subgroup field rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["scoring_buckets"]["subgroup_breakdown"] = "example"
    checks.append(("subgroup_field_rejected", bool(validate_report(mutated))))

    # --- claim-making wording rejected ---
    for phrase in ("method effectiveness", "product readiness", "scoring success", "outcome success", "evaluation works", "acquisition success", "adjudication proven", "denominator proven", "correctness proven", "lift achieved", "evidence_success achieved"):
        mutated = copy.deepcopy(valid_report)
        mutated["scoring_buckets"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_')}_rejected", bool(validate_report(mutated))))

    # --- user-approval wording rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    # --- placeholder wording rejected ---
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(valid_report)
        mutated["frozen_protocol_applied"]["denominator_eligibility_predicates"] = list(DENOMINATOR_ELIGIBILITY_PREDICATES) + [phrase]
        checks.append((f"placeholder_{phrase}_rejected", bool(validate_report(mutated))))

    # --- closed-list set-equality: extra member rejected in every list ---
    for _section, key, expected, label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(valid_report)
        mutated["frozen_protocol_applied"][key].append("extra_bogus_member")
        errors = validate_report(mutated)
        checks.append((f"extra_{label}_member_rejected", bool(errors)))
        checks.append((f"extra_{label}_member_set_equality", any("has extra members" in e for e in errors)))

    # --- closed-list set-equality: missing member rejected ---
    for _section, key, expected, label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(valid_report)
        mutated["frozen_protocol_applied"][key] = mutated["frozen_protocol_applied"][key][1:]
        checks.append((f"missing_{label}_member_rejected", bool(validate_report(mutated))))

    # --- closed-list vocabulary drift rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["frozen_protocol_applied"]["scoring_metric_definitions"][0] = "denominator_count_exact"
    checks.append(("scoring_metric_vocabulary_drift_rejected", bool(validate_report(mutated))))

    # --- adjudication boundary flip rejected ---
    for key in (
        "adjudication_is_deterministic_not_llm_not_provider_not_model",
        "no_phase9j_as_truth",
        "no_phase9l_unavailable_packets_scoreable",
        "adjudication_not_executed_in_phase9p_requires_separate_frozen_boundary_after_scoring",
    ):
        mutated = copy.deepcopy(valid_report)
        mutated["adjudication_boundary"][key] = False
        checks.append((f"adjudication_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # --- adjudication rules with 9J-as-truth / 9L-scoreable / LLM rejected ---
    for bad_member in ("phase9j_rows_used_as_truth", "phase9l_unavailable_packets_scoreable", "llm_provider_based_adjudication"):
        mutated = copy.deepcopy(valid_report)
        mutated["frozen_protocol_applied"]["adjudication_rules"].append(bad_member)
        checks.append((f"adjudication_rule_{bad_member}_rejected", bool(validate_report(mutated))))

    # --- evidence_success / correctness / adjudication true on executed rejected ---
    for exec_key in ("adjudication_executed", "correctness_evaluated", "evidence_success_evaluated"):
        mutated = copy.deepcopy(valid_report)
        mutated["execution_booleans"][exec_key] = True
        checks.append((f"executed_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # --- runtime/default/product/method/performance claim boundary ---
    for claim_key in ("runtime_claim", "default_claim", "product_claim", "method_claim", "performance_claim", "evidence_success_claim"):
        mutated = copy.deepcopy(valid_report)
        mutated["no_claim_boundary"][claim_key] = True
        checks.append((f"claim_{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- truth boundary flip rejected ---
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        mutated = copy.deepcopy(valid_report)
        mutated["truth_boundary"][key] = False
        checks.append((f"truth_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # --- inherited cap drift rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["frozen_protocol_applied"]["inherited_phase9h_aggregate_caps"]["target_inventory_bucket"] = "bucket_wrong"
    checks.append(("inherited_cap_drift_rejected", bool(validate_report(mutated))))

    # --- conservative recommendation drift rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["conservative_recommendation"] = "wrong"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # --- strict allowed-key schema: unknown fields rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(valid_report)
    mutated["scoring_buckets"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scoring_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(valid_report)
    mutated["frozen_protocol_applied"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(valid_report)
    mutated["frozen_protocol_applied"]["inherited_phase9h_aggregate_caps"]["unexpected_cap"] = "x"
    checks.append(("unknown_nested_field_caps_rejected", bool(validate_report(mutated))))

    # --- gate-reference values on whitelisted paths valid; non-gate hash rejected ---
    mutated = copy.deepcopy(valid_report)
    mutated["execution_booleans"]["example_hash"] = "282a5037a106da55b6df67a33c42bb3ad7142836"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    # --- validate-report path fail-closed ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9p" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9p_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase9p" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # --- frozen scoring application on synthetic fixtures ---
    # Acquired-only: all eligible, all included.
    pkts_acq = [_synthetic_phase9n_packet(i, i % 5) for i in range(12)]
    rows, counts, errs = _apply_frozen_scoring(pkts_acq, True)
    checks.append(("scoring_acquired_no_errors", not errs))
    checks.append(("scoring_acquired_denominator_12", counts["denominator"] == 12))
    checks.append(("scoring_acquired_scored_12", counts["scored"] == 12))
    checks.append(("scoring_acquired_invalid_excluded_0", counts["invalid_excluded"] == 0))
    checks.append(("scoring_acquired_unavailable_excluded_0", counts["unavailable_excluded"] == 0))
    checks.append(("scoring_acquired_adjudicated_0", counts["adjudicated"] == 0))
    checks.append(("scoring_acquired_correctness_0", counts["correctness"] == 0))

    # Unavailable packets excluded before scoring.
    pkts_unavail = [_synthetic_phase9n_packet(i, 0, state="unavailable") for i in range(6)]
    rows_u, counts_u, errs_u = _apply_frozen_scoring(pkts_unavail, True)
    checks.append(("scoring_unavailable_no_errors", not errs_u))
    checks.append(("scoring_unavailable_denominator_0", counts_u["denominator"] == 0))
    checks.append(("scoring_unavailable_scored_0", counts_u["scored"] == 0))
    checks.append(("scoring_unavailable_unavailable_excluded_6", counts_u["unavailable_excluded"] == 6))

    # Invalid packets excluded before scoring.
    pkts_inv = [_synthetic_phase9n_packet(i, 0, state="invalid") for i in range(6)]
    rows_i, counts_i, errs_i = _apply_frozen_scoring(pkts_inv, True)
    checks.append(("scoring_invalid_denominator_0", counts_i["denominator"] == 0))
    checks.append(("scoring_invalid_invalid_excluded_6", counts_i["invalid_excluded"] == 6))

    # Mixed: 8 acquired + 2 unavailable + 2 invalid.
    mixed = (
        [_synthetic_phase9n_packet(i, i % 4) for i in range(8)]
        + [_synthetic_phase9n_packet(8 + i, 0, state="unavailable") for i in range(2)]
        + [_synthetic_phase9n_packet(10 + i, 0, state="invalid") for i in range(2)]
    )
    rows_m, counts_m, errs_m = _apply_frozen_scoring(mixed, True)
    checks.append(("scoring_mixed_no_errors", not errs_m))
    checks.append(("scoring_mixed_denominator_8", counts_m["denominator"] == 8))
    checks.append(("scoring_mixed_scored_8", counts_m["scored"] == 8))
    checks.append(("scoring_mixed_unavailable_excluded_2", counts_m["unavailable_excluded"] == 2))
    checks.append(("scoring_mixed_invalid_excluded_2", counts_m["invalid_excluded"] == 2))

    # Route not attested: all packets fail route predicate -> denominator 0.
    rows_r, counts_r, _ = _apply_frozen_scoring(pkts_acq, False)
    checks.append(("scoring_route_not_attested_denominator_0", counts_r["denominator"] == 0))

    # Duplicate candidate index: second duplicate excluded as ineligible.
    dup_pkts = [_synthetic_phase9n_packet(0), _synthetic_phase9n_packet(0)]
    rows_d, counts_d, _ = _apply_frozen_scoring(dup_pkts, True)
    checks.append(("scoring_duplicate_denominator_1", counts_d["denominator"] == 1))
    checks.append(("scoring_duplicate_invalid_excluded_1", counts_d["invalid_excluded"] == 1))

    # --- missing confirmation blocks execution ---
    confirmation_labels = (
        ("missing_confirm_phase9o_commit", dict(confirm_phase9o_commit=None)),
        ("missing_confirm_phase9o_ci", dict(confirm_phase9o_ci=None)),
        ("missing_confirm_phase9o_status", dict(confirm_phase9o_status=None)),
        ("missing_confirm_phase9o_protocol_freeze", dict(confirm_phase9o_protocol_freeze=False)),
        ("missing_confirm_phase9n_commit", dict(confirm_phase9n_commit=None)),
        ("missing_confirm_phase9n_ci", dict(confirm_phase9n_ci=None)),
        ("missing_confirm_phase9n_status", dict(confirm_phase9n_status=None)),
        ("missing_confirm_phase9n_nonzero", dict(confirm_phase9n_acquired_valid_bucket_nonzero=False)),
        ("missing_confirm_read_phase9n_packets", dict(confirm_read_phase9n_private_outcome_observable_packets=False)),
        ("missing_confirm_ignored_runs", dict(confirm_ignored_runs_read_for_phase9n_packets_only=False)),
        ("missing_confirm_private_output_only", dict(confirm_private_output_only=False)),
        ("missing_confirm_aggregate_public", dict(confirm_aggregate_public_report_only=False)),
        ("missing_confirm_apply_frozen", dict(confirm_apply_frozen_phase9o_protocol_exactly=False)),
        ("missing_confirm_no_new_metrics", dict(confirm_no_new_metrics_thresholds_subgroups=False)),
        ("missing_confirm_no_protocol_edits", dict(confirm_no_protocol_edits_after_outcome_visibility=False)),
        ("missing_confirm_no_adjudication", dict(confirm_no_adjudication_execution_separate_boundary_required=False)),
        ("missing_confirm_no_provider_llm", dict(confirm_no_provider_llm_model_adjudication=False)),
        ("missing_confirm_no_phase9j_truth", dict(confirm_no_phase9j_as_truth=False)),
        ("missing_confirm_no_phase9l_scoreable", dict(confirm_no_phase9l_unavailable_packets_scoreable=False)),
        ("missing_confirm_no_evidence_success", dict(confirm_no_evidence_success_no_correctness_no_gold=False)),
        ("missing_confirm_no_runtime_claim", dict(confirm_no_runtime_default_product_method_performance_claim=False)),
        ("missing_confirm_no_network", dict(confirm_no_network_fetch_clone_source_refresh=False)),
    )
    base_kwargs = dict(
        confirm_phase9o_commit=PHASE9O_COMMIT,
        confirm_phase9o_ci=PHASE9O_CI_RUN,
        confirm_phase9o_status=PHASE9O_STATUS,
        confirm_phase9o_protocol_freeze=True,
        confirm_phase9n_commit=PHASE9N_COMMIT,
        confirm_phase9n_ci=PHASE9N_CI_RUN,
        confirm_phase9n_status=PHASE9N_STATUS,
        confirm_phase9n_acquired_valid_bucket_nonzero=True,
        confirm_read_phase9n_private_outcome_observable_packets=True,
        confirm_ignored_runs_read_for_phase9n_packets_only=True,
        confirm_private_output_only=True,
        confirm_aggregate_public_report_only=True,
        confirm_apply_frozen_phase9o_protocol_exactly=True,
        confirm_no_new_metrics_thresholds_subgroups=True,
        confirm_no_protocol_edits_after_outcome_visibility=True,
        confirm_no_adjudication_execution_separate_boundary_required=True,
        confirm_no_provider_llm_model_adjudication=True,
        confirm_no_phase9j_as_truth=True,
        confirm_no_phase9l_unavailable_packets_scoreable=True,
        confirm_no_evidence_success_no_correctness_no_gold=True,
        confirm_no_runtime_default_product_method_performance_claim=True,
        confirm_no_network_fetch_clone_source_refresh=True,
    )
    for label, overrides in confirmation_labels:
        kwargs = dict(base_kwargs)
        kwargs.update(overrides)
        try:
            execute_phase9p(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, **kwargs)
            checks.append((f"{label}_rejected", False))
        except ValueError as exc:
            checks.append((f"{label}_rejected", "missing required confirmation" in str(exc)))

    # --- tracked/private path rejected ---
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_tracked_output")
        checks.append(("tracked_output_path_rejected", False))
    except ValueError as exc:
        checks.append(("tracked_output_path_rejected", "runs" in str(exc)))

    # --- packet schema validation ---
    checks.append(("valid_packet_schema_passes", _packet_schema_valid(_synthetic_phase9n_packet(0))))
    bad_packet = {"outcome_acquisition_state": "acquired"}
    checks.append(("invalid_packet_schema_rejected", not _packet_schema_valid(bad_packet)))

    # --- temp-file round-trip validation ---
    with tempfile.TemporaryDirectory(prefix="phase9p_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(valid_report), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- gate-reference CI run values on whitelisted paths valid ---
    checks.append(("gate_ci_run_values_on_whitelisted_paths_valid", not validate_report(valid_report)))

    # --- frozen protocol lists loaded from Phase 9O module (exact match) ---
    checks.append(("denominator_predicates_loaded_from_phase9o", DENOMINATOR_ELIGIBILITY_PREDICATES is _PHASE9O_FREEZE.DENOMINATOR_ELIGIBILITY_PREDICATES))
    checks.append(("scoring_metrics_loaded_from_phase9o", SCORING_METRIC_DEFINITIONS is _PHASE9O_FREEZE.SCORING_METRIC_DEFINITIONS))
    checks.append(("adjudication_rules_loaded_from_phase9o", ADJUDICATION_RULES is _PHASE9O_FREEZE.ADJUDICATION_RULES))

    # --- self-test does not fetch/read private beyond authorized ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_make_network_calls", NETWORK_CALL_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs_directly", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9l_packets", PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9h_sources", PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9j_rows", PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9P frozen scoring execution (bucketed aggregate only, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--confirm-phase9o-commit")
    parser.add_argument("--confirm-phase9o-ci")
    parser.add_argument("--confirm-phase9o-status")
    parser.add_argument("--confirm-phase9o-protocol-freeze", action="store_true")
    parser.add_argument("--confirm-phase9n-commit")
    parser.add_argument("--confirm-phase9n-ci")
    parser.add_argument("--confirm-phase9n-status")
    parser.add_argument("--confirm-phase9n-acquired-valid-bucket-nonzero", action="store_true")
    parser.add_argument("--confirm-read-phase9n-private-outcome-observable-packets", action="store_true")
    parser.add_argument("--confirm-ignored-runs-read-for-phase9n-packets-only", action="store_true")
    parser.add_argument("--confirm-private-output-only", action="store_true")
    parser.add_argument("--confirm-aggregate-public-report-only", action="store_true")
    parser.add_argument("--confirm-apply-frozen-phase9o-protocol-exactly", action="store_true")
    parser.add_argument("--confirm-no-new-metrics-thresholds-subgroups", action="store_true")
    parser.add_argument("--confirm-no-protocol-edits-after-outcome-visibility", action="store_true")
    parser.add_argument("--confirm-no-adjudication-execution-separate-boundary-required", action="store_true")
    parser.add_argument("--confirm-no-provider-llm-model-adjudication", action="store_true")
    parser.add_argument("--confirm-no-phase9j-as-truth", action="store_true")
    parser.add_argument("--confirm-no-phase9l-unavailable-packets-scoreable", action="store_true")
    parser.add_argument("--confirm-no-evidence-success-no-correctness-no-gold", action="store_true")
    parser.add_argument("--confirm-no-runtime-default-product-method-performance-claim", action="store_true")
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
        result = execute_phase9p(
            args.private_run_dir,
            args.output,
            args.confirm_phase9o_commit,
            args.confirm_phase9o_ci,
            args.confirm_phase9o_status,
            args.confirm_phase9o_protocol_freeze,
            args.confirm_phase9n_commit,
            args.confirm_phase9n_ci,
            args.confirm_phase9n_status,
            args.confirm_phase9n_acquired_valid_bucket_nonzero,
            args.confirm_read_phase9n_private_outcome_observable_packets,
            args.confirm_ignored_runs_read_for_phase9n_packets_only,
            args.confirm_private_output_only,
            args.confirm_aggregate_public_report_only,
            args.confirm_apply_frozen_phase9o_protocol_exactly,
            args.confirm_no_new_metrics_thresholds_subgroups,
            args.confirm_no_protocol_edits_after_outcome_visibility,
            args.confirm_no_adjudication_execution_separate_boundary_required,
            args.confirm_no_provider_llm_model_adjudication,
            args.confirm_no_phase9j_as_truth,
            args.confirm_no_phase9l_unavailable_packets_scoreable,
            args.confirm_no_evidence_success_no_correctness_no_gold,
            args.confirm_no_runtime_default_product_method_performance_claim,
            args.confirm_no_network_fetch_clone_source_refresh,
            dry=args.dry_run,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
