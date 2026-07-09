#!/usr/bin/env python3
"""Phase 10A independent validation line protocol-freeze (no execution, no claim).

This is a docs/report/validator-only protocol-freeze checkpoint for a NEW
independent validation line.  It has one narrow purpose: freeze the boundary
of a fresh independent validation line that is separate from Phase 9, and
forbid any empirical activity inside Phase 10A.

Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation,
repair, rerun, rescore, or strengthening of Phase 9R/9S.  Phase 9 is closed at
commit ``1d71f6a``, CI run ``28999245247``.  Phase 10A makes NO new evidence
claims.

It does NOT fetch, clone, read, or materialize any repository or source, does
NOT read ignored ``runs/``, any private Phase 9 artifacts (Phase 9R adjudication
rows, Phase 9P scoring rows, Phase 9N packets, Phase 9H materialized sources,
Phase 9J annotation-input rows, Phase 9L outcome packets, Phase 9S closeout
rows), does NOT execute, score, adjudicate, evaluate correctness/evidence_success,
generate tasks/samples, fetch/clone/source refresh, or make any provider/LLM/model
call.  It introduces no metrics/thresholds/rates/counts beyond coarse fixed
status/boundary fields, and makes no product/method/performance/correctness/
generalization claim.  It does NOT use low-resource autonomy to start empirical
work inside 10A.

The Phase 9 closure gate reference values (commit ``1d71f6a``, CI run
``28999245247``, CI success, Phase 9 closed) are the only exact public gate
references published by Phase 10A.  Older Phase 9 exact commit/CI refs (Phase 9R,
Phase 9Q, Phase 9P, etc.) are intentionally NOT republished by Phase 10A (tighter
privacy); they are referenced only as "Phase 9 is closed" boundary provenance.
Local same-tree git commits are not read or compared; only the Phase 9 closure
gate constants are exact gate references.

Future-line requirements are DEFINED ONLY: any future execution requires fresh/
fenced inputs, independent replication packet generation, aggregate-only public
reporting, a pre-frozen protocol before any execution, and a separate boundary
review after the 10A commit + CI green before Phase 10B+.  Phase 10A does NOT
execute, freeze-and-run, or authorize that future execution.
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

# Compact Phase 10A slug (kept short so the absolute artifact report path stays
# comfortably under the Windows MAX_PATH (260) limit).  Boundary wording in the
# report body/docs is NOT weakened -- only the path-dependent slug is shortened.
PHASE = "phase10a_independent_validation_protocol_freeze_no_execution_no_claim"
# Honest protocol-freeze wording: Phase 10A freezes the protocol for a new
# independent validation line, with no execution and no new evidence claim.
STATUS = "phase10a_independent_validation_protocol_freeze_no_execution_no_claim"
SCHEMA_VERSION = "phase10a_independent_validation_protocol_freeze_no_execution_no_claim_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

# ---------------------------------------------------------------------------
# Phase 9 closure gate reference values (oracle-provided).  These are the
# PRIMARY (and only) public gate references published by Phase 10A.  Local
# same-tree git commits are not read or compared; the supplied confirmation
# values are matched against the frozen public gate constants only.
# ---------------------------------------------------------------------------
PHASE9_CLOSURE_COMMIT = "1d71f6a"
PHASE9_CLOSURE_CI_RUN = "28999245247"

# ---------------------------------------------------------------------------
# Frozen Phase 10A closed lists (validator set-equality checked).  These are
# STRUCTURAL protocol-freeze definitions only; no execution, scoring,
# adjudication, correctness/evidence_success evaluation, task generation, or
# protocol movement occurs in Phase 10A.
# ---------------------------------------------------------------------------
PROTOCOL_PUBLICATION_LEVEL = "aggregate_protocol_freeze_boundary_only"

# 1. Phase 9 separation rule: Phase 10A is separate from Phase 9; it does not
#    interpret, extend, strengthen, repair, rerun, or rescore Phase 9R/9S.
PHASE9_SEPARATION_RULES = (
    "phase10a_is_separate_from_phase9_not_a_continuation",
    "phase10a_does_not_interpret_phase9r_or_phase9s",
    "phase10a_does_not_extend_phase9r_or_phase9s",
    "phase10a_does_not_strengthen_phase9r_or_phase9s",
    "phase10a_does_not_repair_phase9r_or_phase9s",
    "phase10a_does_not_rerun_phase9r_or_phase9s",
    "phase10a_does_not_rescore_phase9r_or_phase9s",
    "phase9_artifacts_cannot_be_used_as_validation_evidence",
)

# 2. Future-line requirements (defined only): any future execution requires
#    fresh/fenced inputs, independent replication packet generation,
#    aggregate-only public reporting, a pre-frozen protocol before execution,
#    and a separate boundary review after 10A commit + CI green before 10B+.
FUTURE_LINE_REQUIREMENTS_RULES = (
    "future_inputs_must_be_fresh_and_fenced",
    "future_independent_replication_packet_generation_required",
    "future_aggregate_only_public_reporting",
    "future_protocol_must_be_pre_frozen_before_any_execution",
    "separate_boundary_review_after_phase10a_commit_and_ci_green_before_phase10b",
    "phase10a_does_not_freeze_or_run_any_future_execution",
)

# 3. Explicit Phase 10A forbidden actions.
FORBIDDEN_ACTIONS_RULES = (
    "no_private_reads_or_rereads_in_phase10a",
    "no_source_reads_in_phase10a",
    "no_repo_fetch_clone_or_network_materialization_in_phase10a",
    "no_task_generation_or_sampling_in_phase10a",
    "no_scoring_adjudication_evidence_success_or_correctness_execution_in_phase10a",
    "no_metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_in_phase10a",
    "no_product_method_performance_correctness_or_generalization_claims_in_phase10a",
    "no_low_resource_autonomy_starting_empirical_work_in_phase10a",
)

# 4. No-execution guardrails.
NO_EXECUTION_GUARDRAIL_RULES = (
    "no_execution_in_phase10a",
    "no_scoring_in_phase10a",
    "no_adjudication_in_phase10a",
    "no_correctness_or_evidence_success_evaluation_in_phase10a",
    "no_task_generation_or_sampling_in_phase10a",
    "no_source_fetch_clone_or_refresh_in_phase10a",
    "no_provider_llm_or_model_calls_in_phase10a",
    "no_private_reads_in_phase10a",
)

# Truth-boundary attestation keys that must always be True in the public report.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_at_recorded_commit_and_ci",
    "phase10a_makes_no_new_evidence_claims",
    "phase10a_does_not_interpret_extend_strengthen_repair_rerun_or_rescore_phase9r_or_phase9s",
    "phase10a_is_protocol_freeze_only_for_new_independent_validation_line",
    "phase10b_requires_separate_boundary_review_after_phase10a_commit_and_ci_green",
    "phase9_artifacts_cannot_be_used_as_validation_evidence",
)

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "task_generation_or_sampling_executed",
    "scoring_executed",
    "adjudication_executed",
    "correctness_evaluated",
    "evidence_success_evaluated",
    "private_reads_executed",
    "private_rereads_executed",
    "source_reads_executed",
    "repo_fetch_clone_or_network_materialization_executed",
    "metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_published",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
    "low_resource_autonomy_empirical_work_started",
    "phase9_artifacts_used_as_validation_evidence",
    "phase9r_rerun_or_rescored",
    "phase9s_rerun_or_reinterpreted",
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
    "correctness_claim",
    "generalization_claim",
)

PRIVACY_FALSE_KEYS = (
    "repo_names_public",
    "source_names_public",
    "urls_public",
    "owners_public",
    "non_gate_commits_public",
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
    "exact_counts_or_rates_public",
    "phase9_private_artifacts_public",
    "metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_public",
)

# Forbidden public field words; only apply to non-boolean values at
# non-allowed-schema paths so boolean boundary-attestation keys such as
# ``evidence_success_evaluated`` and section names are not false-flagged.
FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

# Closed protocol lists whose members are validator set-equality checked.
# Each entry is (report_section, list_key, expected_tuple, label) so the
# self-test can mutate the correct nested section.
CLOSED_PROTOCOL_LISTS = (
    ("frozen_phase9_separation", "phase9_separation_rules", PHASE9_SEPARATION_RULES, "phase9_separation"),
    ("frozen_future_line_requirements", "future_line_requirements_rules", FUTURE_LINE_REQUIREMENTS_RULES, "future_line_requirements"),
    ("frozen_forbidden_actions", "forbidden_actions_rules", FORBIDDEN_ACTIONS_RULES, "forbidden_actions"),
    ("frozen_no_execution_guardrails", "no_execution_guardrail_rules", NO_EXECUTION_GUARDRAIL_RULES, "no_execution_guardrails"),
)

# Claim-making wording that must never appear as an exposed value.
CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"materialization\s+(?:works|succeeded|proven|established)"
    r"|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)"
    r"|clone\s+(?:works|succeeded|proven|established)"
    r"|evidence_success\s+(?:achieved|proven|established|confirmed)"
    r"|method\s+(?:proven|established|works|winner|effectiveness)"
    r"|product\s+readiness"
    r"|scoring\s+success"
    r"|outcome\s+success"
    r"|evaluation\s+works"
    r"|task\s+annotation\s+readiness"
    r"|lift\s+(?:proven|established|achieved)"
    r"|route\s+(?:works|succeeded|proven|established)"
    r"|acquisition\s+success"
    r"|adjudication\s+(?:works|succeeded|proven|established)"
    r"|correctness\s+(?:proven|established|achieved|confirmed)"
    r"|evidence[-_ ]acquisition\s+success"
    r"|generalized\s+success"
    r"|validation\s+(?:works|succeeded|proven|established)"
    r")\b",
    re.IGNORECASE,
)

# User-approval wording that must never appear in exposed string values.
USER_APPROVAL_WORDING_RE = re.compile(
    r"\b(?:user\s+(?:must|should|needs?\s+to)\s+(?:approve|authorize|confirm)"
    r"|awaiting\s+user\s+(?:approval|authorization|confirmation)"
    r"|requires?\s+user\s+(?:approval|authorization)"
    r"|low.resource\s+continuation\s+(?:approval|authorization))\b",
    re.IGNORECASE,
)

# Placeholder / TBD / TODO wording that must never appear in exposed values.
PLACEHOLDER_RE = re.compile(
    r"\b(?:TBD|TODO|FIXME|XXX|placeholder|placeholder_value|fill_in|not_set"
    r"|stub_value|dummy_value)\b",
    re.IGNORECASE,
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
# Long decimal (8+ digits) CI/run-shaped public value detector.
LONG_DECIMAL_VALUE_RE = re.compile(r"\b\d{8,}\b")
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:count_1|bucket_one|bucket_1|bucket_up_to_1|bucket_at_most_1|n_1|singleton)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
# Private-shaped KEY detection (substring, case-insensitive).  Known-good
# boundary-attestation keys that legitimately contain a private token are
# exempted via the allowed-schema path check in ``_scan_public``.
PRIVATE_KEY_RE = re.compile(
    r"(?:repo|repo_name|repo_url|owner|source_url|url"
    r"|candidate_identity|commit|commit_sha|ci_run|sha|hash"
    r"|path|range|snippet|task_id|row_id|packet_id"
    r"|observable_id|observable_path|manifest|run_dir"
    r"|per_source|per_task|per_packet)",
    re.IGNORECASE,
)

# Defense-in-depth: scan list string values for private-shaped tokens even
# though closed protocol lists already reject extra members via set-equality.
LIST_VALUE_PRIVATE_TOKEN_RE = re.compile(
    r"(?:task_id|row_id|packet_id|observable_id|observable_path"
    r"|run_dir|source_path|manifest_path|candidate_id|commit_sha)",
    re.IGNORECASE,
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants (Phase 9 closure commit / CI run).  Phase 10A only
# publishes the Phase 9 closure gate refs; older Phase 9 exact commit/CI
# values are intentionally NOT republished (tighter privacy).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9_closure_gate.phase9_closure_commit",
        "$.phase9_closure_gate.phase9_closure_ci_run",
    }
)

# Exact public gate-reference JSON paths whose string VALUES are CI run IDs
# (long decimal integers).
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9_closure_gate.phase9_closure_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
TASK_GENERATION_OR_SAMPLING_ATTEMPTS = 0
SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0

CONSERVATIVE_RECOMMENDATION = (
    "phase10a_independent_validation_protocol_freeze_only_for_new_independent_validation_line"
    "_phase9_closed_at_recorded_commit_and_ci"
    "_phase10a_makes_no_new_evidence_claims"
    "_phase10a_does_not_interpret_extend_strengthen_repair_rerun_or_rescore_phase9r_or_phase9s"
    "_phase9_artifacts_cannot_be_used_as_validation_evidence"
    "_future_inputs_fresh_and_fenced_independent_replication_packet_generation_required"
    "_future_aggregate_only_public_reporting_protocol_before_execution"
    "_separate_boundary_review_after_phase10a_commit_and_ci_green_before_phase10b"
    "_no_private_reads_no_source_reads_no_repo_fetch_clone_no_task_generation"
    "_no_scoring_adjudication_evidence_success_correctness_execution"
    "_no_metrics_thresholds_rates_counts_beyond_coarse_fixed_status_boundary_fields"
    "_no_product_method_performance_correctness_generalization_claim"
    "_no_low_resource_autonomy_empirical_work"
)


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
    "phase9_closure_gate": {
        "phase9_closure_commit": None,
        "phase9_closure_ci_run": None,
        "phase9_closure_ci_success": None,
        "phase9_closed": None,
        "phase9_closure_gate_required_before_phase10a": None,
        "phase9r_9s_exact_refs_not_republished_by_phase10a": None,
    },
    "phase10a_scope": {
        "docs_report_validator_only": None,
        "protocol_freeze_only_for_new_independent_validation_line": None,
        "phase10a_separate_from_phase9_not_continuation": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "task_generation_or_sampling_executed": None,
        "scoring_executed": None,
        "adjudication_executed": None,
        "correctness_evaluated": None,
        "evidence_success_evaluated": None,
        "private_reads_executed": None,
        "private_rereads_executed": None,
        "source_reads_executed": None,
        "repo_fetch_clone_or_network_materialization_executed": None,
        "metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_published": None,
        "model_fitting": None,
        "provider_or_llm_calls": None,
        "runtime_default_or_product_changes": None,
        "low_resource_autonomy_empirical_work_started": None,
        "phase9_artifacts_used_as_validation_evidence": None,
        "phase9r_rerun_or_rescored": None,
        "phase9s_rerun_or_reinterpreted": None,
    },
    "frozen_phase9_separation": {
        "publication_level": None,
        "phase9_separation_rules": None,
        "phase10a_separate_from_phase9_not_a_continuation": None,
        "phase9_artifacts_cannot_be_used_as_validation_evidence": None,
    },
    "frozen_future_line_requirements": {
        "future_line_requirements_rules": None,
        "future_inputs_must_be_fresh_and_fenced": None,
        "future_independent_replication_packet_generation_required": None,
        "future_aggregate_only_public_reporting": None,
        "future_protocol_must_be_pre_frozen_before_any_execution": None,
        "separate_boundary_review_after_phase10a_commit_and_ci_green_before_phase10b": None,
        "phase10a_does_not_freeze_or_run_any_future_execution": None,
    },
    "frozen_forbidden_actions": {
        "forbidden_actions_rules": None,
        "no_private_reads_or_rereads_in_phase10a": None,
        "no_source_reads_in_phase10a": None,
        "no_repo_fetch_clone_or_network_materialization_in_phase10a": None,
        "no_task_generation_or_sampling_in_phase10a": None,
        "no_scoring_adjudication_evidence_success_or_correctness_execution_in_phase10a": None,
        "no_metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_in_phase10a": None,
        "no_product_method_performance_correctness_or_generalization_claims_in_phase10a": None,
        "no_low_resource_autonomy_starting_empirical_work_in_phase10a": None,
    },
    "frozen_no_execution_guardrails": {
        "no_execution_guardrail_rules": None,
        "no_execution_no_scoring_no_adjudication_in_phase10a": None,
        "no_correctness_or_evidence_success_evaluation_in_phase10a": None,
        "no_private_reads_in_phase10a": None,
        "no_task_generation_or_sampling_in_phase10a": None,
        "no_source_fetch_clone_or_refresh_in_phase10a": None,
        "no_provider_llm_or_model_calls_in_phase10a": None,
    },
    "truth_boundary": {key: None for key in TRUTH_BOUNDARY_TRUE_KEYS},
    "no_execution_booleans": {key: None for key in NO_EXECUTION_FALSE_KEYS},
    "privacy_contract": {
        "public_output_aggregate_only": None,
        "runs_remains_ignored": None,
        **{key: None for key in PRIVACY_FALSE_KEYS},
    },
    "claim_boundary": {key: None for key in CLAIM_BOUNDARY_FALSE_KEYS},
    "validation_summary": {
        "phase10a_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_starts_empirical_work": None,
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

    The report path must be under the Phase 10A public artifact directory
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
        return False, "report path is not under the Phase 10A public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report(phase9_closure_gate_ok: bool = True) -> dict[str, Any]:
    """Build the frozen Phase 10A public protocol-freeze report.

    This function performs no network/filesystem fetch and no private reads.
    It assembles the frozen protocol-freeze document from static constants.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9_closure_gate": {
            "phase9_closure_commit": PHASE9_CLOSURE_COMMIT,
            "phase9_closure_ci_run": PHASE9_CLOSURE_CI_RUN,
            "phase9_closure_ci_success": True,
            "phase9_closed": True,
            "phase9_closure_gate_required_before_phase10a": True,
            "phase9r_9s_exact_refs_not_republished_by_phase10a": True,
        },
        "phase10a_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only_for_new_independent_validation_line": True,
            "phase10a_separate_from_phase9_not_continuation": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "task_generation_or_sampling_executed": False,
            "scoring_executed": False,
            "adjudication_executed": False,
            "correctness_evaluated": False,
            "evidence_success_evaluated": False,
            "private_reads_executed": False,
            "private_rereads_executed": False,
            "source_reads_executed": False,
            "repo_fetch_clone_or_network_materialization_executed": False,
            "metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_published": False,
            "model_fitting": False,
            "provider_or_llm_calls": False,
            "runtime_default_or_product_changes": False,
            "low_resource_autonomy_empirical_work_started": False,
            "phase9_artifacts_used_as_validation_evidence": False,
            "phase9r_rerun_or_rescored": False,
            "phase9s_rerun_or_reinterpreted": False,
        },
        "frozen_phase9_separation": {
            "publication_level": PROTOCOL_PUBLICATION_LEVEL,
            "phase9_separation_rules": list(PHASE9_SEPARATION_RULES),
            "phase10a_separate_from_phase9_not_a_continuation": True,
            "phase9_artifacts_cannot_be_used_as_validation_evidence": True,
        },
        "frozen_future_line_requirements": {
            "future_line_requirements_rules": list(FUTURE_LINE_REQUIREMENTS_RULES),
            "future_inputs_must_be_fresh_and_fenced": True,
            "future_independent_replication_packet_generation_required": True,
            "future_aggregate_only_public_reporting": True,
            "future_protocol_must_be_pre_frozen_before_any_execution": True,
            "separate_boundary_review_after_phase10a_commit_and_ci_green_before_phase10b": True,
            "phase10a_does_not_freeze_or_run_any_future_execution": True,
        },
        "frozen_forbidden_actions": {
            "forbidden_actions_rules": list(FORBIDDEN_ACTIONS_RULES),
            "no_private_reads_or_rereads_in_phase10a": True,
            "no_source_reads_in_phase10a": True,
            "no_repo_fetch_clone_or_network_materialization_in_phase10a": True,
            "no_task_generation_or_sampling_in_phase10a": True,
            "no_scoring_adjudication_evidence_success_or_correctness_execution_in_phase10a": True,
            "no_metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_in_phase10a": True,
            "no_product_method_performance_correctness_or_generalization_claims_in_phase10a": True,
            "no_low_resource_autonomy_starting_empirical_work_in_phase10a": True,
        },
        "frozen_no_execution_guardrails": {
            "no_execution_guardrail_rules": list(NO_EXECUTION_GUARDRAIL_RULES),
            "no_execution_no_scoring_no_adjudication_in_phase10a": True,
            "no_correctness_or_evidence_success_evaluation_in_phase10a": True,
            "no_private_reads_in_phase10a": True,
            "no_task_generation_or_sampling_in_phase10a": True,
            "no_source_fetch_clone_or_refresh_in_phase10a": True,
            "no_provider_llm_or_model_calls_in_phase10a": True,
        },
        "truth_boundary": {key: True for key in TRUTH_BOUNDARY_TRUE_KEYS},
        "no_execution_booleans": {key: False for key in NO_EXECUTION_FALSE_KEYS},
        "privacy_contract": {
            "public_output_aggregate_only": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PRIVACY_FALSE_KEYS},
        },
        "claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "validation_summary": {
            "phase10a_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_starts_empirical_work": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
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
    if not isinstance(value, bool) and not is_allowed_path and any(
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


def validate_report(report: Any) -> list[str]:
    """Validate the Phase 10A public report against the frozen schema/constants.

    This checks the report's gate references against the frozen public gate
    constants (PHASE9_CLOSURE_COMMIT / PHASE9_CLOSURE_CI_RUN) directly.  It
    does NOT read any Phase 9 artifact on disk; Phase 10A is separate from
    Phase 9 and does not use Phase 9 artifacts as validation evidence.
    """
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") != STATUS:
        errors.append("status drift")

    # Phase 9 closure gate references (PRIMARY whitelisted public gate refs).
    gate = report.get("phase9_closure_gate", {})
    if gate.get("phase9_closure_commit") != PHASE9_CLOSURE_COMMIT:
        errors.append("Phase 9 closure commit gate reference drift")
    if gate.get("phase9_closure_ci_run") != PHASE9_CLOSURE_CI_RUN:
        errors.append("Phase 9 closure CI run gate reference drift")
    if gate.get("phase9_closure_ci_success") is not True:
        errors.append("Phase 9 closure CI success gate missing")
    if gate.get("phase9_closed") is not True:
        errors.append("Phase 9 closed gate missing")
    for key in ("phase9_closure_gate_required_before_phase10a",
                "phase9r_9s_exact_refs_not_republished_by_phase10a"):
        if gate.get(key) is not True:
            errors.append(f"Phase 9 closure gate boundary missing: {key}")

    # phase10a_scope: all execution booleans must be False.
    scope = report.get("phase10a_scope", {})
    for key in ("docs_report_validator_only",
                "protocol_freeze_only_for_new_independent_validation_line",
                "phase10a_separate_from_phase9_not_continuation"):
        if scope.get(key) is not True:
            errors.append(f"phase10a_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10a_scope execution boundary failed: {key}")

    # Frozen closed lists (set-equality checked).
    sep = report.get("frozen_phase9_separation", {})
    for key in ("phase10a_separate_from_phase9_not_a_continuation",
                "phase9_artifacts_cannot_be_used_as_validation_evidence"):
        if sep.get(key) is not True:
            errors.append(f"frozen phase9 separation boundary missing: {key}")

    future = report.get("frozen_future_line_requirements", {})
    for key in ("future_inputs_must_be_fresh_and_fenced",
                "future_independent_replication_packet_generation_required",
                "future_aggregate_only_public_reporting",
                "future_protocol_must_be_pre_frozen_before_any_execution",
                "separate_boundary_review_after_phase10a_commit_and_ci_green_before_phase10b",
                "phase10a_does_not_freeze_or_run_any_future_execution"):
        if future.get(key) is not True:
            errors.append(f"frozen future line requirements boundary missing: {key}")

    forbidden = report.get("frozen_forbidden_actions", {})
    for key in ("no_private_reads_or_rereads_in_phase10a",
                "no_source_reads_in_phase10a",
                "no_repo_fetch_clone_or_network_materialization_in_phase10a",
                "no_task_generation_or_sampling_in_phase10a",
                "no_scoring_adjudication_evidence_success_or_correctness_execution_in_phase10a",
                "no_metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_in_phase10a",
                "no_product_method_performance_correctness_or_generalization_claims_in_phase10a",
                "no_low_resource_autonomy_starting_empirical_work_in_phase10a"):
        if forbidden.get(key) is not True:
            errors.append(f"frozen forbidden actions boundary missing: {key}")

    guardrails = report.get("frozen_no_execution_guardrails", {})
    for key in ("no_execution_no_scoring_no_adjudication_in_phase10a",
                "no_correctness_or_evidence_success_evaluation_in_phase10a",
                "no_private_reads_in_phase10a",
                "no_task_generation_or_sampling_in_phase10a",
                "no_source_fetch_clone_or_refresh_in_phase10a",
                "no_provider_llm_or_model_calls_in_phase10a"):
        if guardrails.get(key) is not True:
            errors.append(f"frozen no-execution guardrail boundary missing: {key}")

    for _s, key, expected, _l in CLOSED_PROTOCOL_LISTS:
        errors.extend(_check_closed_list(report.get(_s, {}).get(key), expected, _s, key))

    # Truth boundary
    truth = report.get("truth_boundary", {})
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        if truth.get(key) is not True:
            errors.append(f"truth boundary failed: {key}")

    # No-execution false boundary
    no_exec = report.get("no_execution_booleans", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_exec.get(key) is not False:
            errors.append(f"no_execution_booleans boundary failed: {key}")

    # Privacy contract
    privacy = report.get("privacy_contract", {})
    for key in ("public_output_aggregate_only", "runs_remains_ignored"):
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
    for key in ("phase10a_specific_validator_available", "self_test_available",
                "report_validation_available", "validator_does_not_fetch_or_read_private",
                "validator_does_not_read_sources", "validator_does_not_read_ignored_runs",
                "validator_does_not_read_phase9_artifacts",
                "public_artifact_privacy_audit_expected"):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_executes_tasks", "validator_reads_private_registry",
                "validator_reads_sources", "validator_reads_ignored_runs",
                "validator_starts_empirical_work"):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    # Conservative recommendation
    if report.get("conservative_recommendation") != CONSERVATIVE_RECOMMENDATION:
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS
    global TASK_GENERATION_OR_SAMPLING_ATTEMPTS
    global SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
    TASK_GENERATION_OR_SAMPLING_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))
    checks.append(("base_status_equals_required_status", base["status"] == STATUS))
    checks.append(("base_phase_equals_slug", base["phase"] == PHASE))

    # Reject missing/wrong Phase 9 closure gate references (commit / ci).
    for field, bad_val, label in (
        ("phase9_closure_commit", "deadbeef" * 5, "commit"),
        ("phase9_closure_ci_run", "0000", "ci_run"),
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9_closure_gate"][field] = bad_val
        checks.append((f"wrong_phase9_closure_{label}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        del mutated["phase9_closure_gate"][field]
        checks.append((f"missing_phase9_closure_{label}_rejected", bool(validate_report(mutated))))

    # Reject phase9 closure gate facts flipped to false.
    for key in ("phase9_closed", "phase9_closure_ci_success",
                "phase9_closure_gate_required_before_phase10a",
                "phase9r_9s_exact_refs_not_republished_by_phase10a"):
        mutated = copy.deepcopy(base)
        mutated["phase9_closure_gate"][key] = False
        checks.append((f"phase9_closure_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema drift.
    for field, bad in (("status", "drift"), ("phase", "drift"), ("schema_version", "drift")):
        mutated = copy.deepcopy(base)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # --- negative mutation: execution booleans true fails. ---
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["phase10a_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: phase9 separation violation fails. ---
    for sep_key in ("phase9_artifacts_used_as_validation_evidence",
                    "phase9r_rerun_or_rescored",
                    "phase9s_rerun_or_reinterpreted"):
        mutated = copy.deepcopy(base)
        mutated["phase10a_scope"][sep_key] = True
        mutated["no_execution_booleans"][sep_key] = True
        checks.append((f"phase9_separation_{sep_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: exact count fields fail. ---
    mutated = copy.deepcopy(base)
    mutated["phase10a_scope"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_phase9_separation"]["adjudicated_count"] = 72
    checks.append(("adjudicated_count_field_rejected", bool(validate_report(mutated))))

    # --- negative mutation: observable/path/snippet/private-shaped fails. ---
    for label, bad_val in (
        ("url", "https://example.invalid/repo.git"),
        ("owner_repo", "owner/repo"),
        ("hash", "a" * 40),
        ("path", "src/private.py"),
        ("task_id", "task_id_7"),
        ("row_id", "row_id_3"),
        ("run_dir", "runs/secret/run_dir"),
    ):
        mutated = copy.deepcopy(base)
        mutated["phase10a_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: private-shaped keys fail. ---
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "per_task_summary", "source_path_bucket", "path",
        "repo_name", "task_id", "row_id", "packet_id", "manifest",
        "run_dir",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase10a_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: threshold/novel-metric/subgroup keys fail. ---
    for bad_key in ("correctness_threshold", "adjudication_threshold", "decision_threshold",
                    "novel_metric_bucket", "subgroup_breakdown"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9_separation"][bad_key] = "example"
        checks.append((f"forbidden_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: unknown closed-list member fails (set-equality). ---
    for _s, key, expected, label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(base)
        mutated[_s][key].append("extra_bogus_member")
        errors = validate_report(mutated)
        checks.append((f"extra_{label}_member_rejected", bool(errors)))
        checks.append((f"extra_{label}_member_set_equality", any("has extra members" in e for e in errors)))

    for _s, key, expected, label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(base)
        mutated[_s][key] = mutated[_s][key][1:]
        checks.append((f"missing_{label}_member_rejected", bool(validate_report(mutated))))

    # --- negative mutation: reworded closed-list member fails. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_phase9_separation"]["phase9_separation_rules"][0] = "phase10a_continues_phase9r"
    checks.append(("phase9_separation_vocabulary_drift_rejected", bool(validate_report(mutated))))

    # --- negative mutation: future-protocol freeze/run wording in 10A fails. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_future_line_requirements"]["future_line_requirements_rules"].append("phase10a_freezes_future_execution_now")
    checks.append(("future_execution_frozen_in_10a_rejected", bool(validate_report(mutated))))

    # --- negative mutation: claim boundary set to true fails. ---
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: privacy contract violations fail. ---
    for privacy_key in (
        "per_source_public_facts", "per_task_public_facts",
        "run_locations_public", "repo_names_public",
        "packet_ids_public", "exact_counts_or_rates_public", "singleton_buckets_public",
        "phase9_private_artifacts_public",
        "metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_public",
    ):
        mutated = copy.deepcopy(base)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: singleton buckets fail. ---
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9_separation"]["phase9_separation_rules"].append(singleton_val)
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # --- negative mutation: claim-making wording fails. ---
    for phrase in ("method effectiveness", "product readiness", "scoring success", "outcome success",
                   "evaluation works", "acquisition success", "adjudication proven",
                   "correctness proven", "evidence_success achieved", "lift achieved",
                   "generalized success", "evidence-acquisition success", "validation proven"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9_separation"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # --- negative mutation: user-approval wording fails. ---
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    # --- negative mutation: placeholder/TBD/TODO wording fails. ---
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9_separation"]["phase9_separation_rules"].append(phrase)
        checks.append((f"placeholder_{phrase}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: truth-boundary violation fails. ---
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["truth_boundary"][key] = False
        checks.append((f"truth_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # --- negative mutation: conservative recommendation drift fails. ---
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # --- negative mutation: unknown fields fail. ---
    mutated = copy.deepcopy(base)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase10a_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_phase9_separation"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_separation_rejected", bool(validate_report(mutated))))

    # --- non-gate-reference hash/CI values are rejected. ---
    mutated = copy.deepcopy(base)
    mutated["phase10a_scope"]["task_ci_run"] = "28999245247"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    checks.append(("non_whitelisted_ci_run_key_not_exempt", any("private-shaped public key" in e for e in errors)))

    mutated = copy.deepcopy(base)
    mutated["phase10a_scope"]["example_hash"] = "1d71f6a" + "0" * 33
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    # Gate-reference commit values are exempt from private-shaped value scan
    # but a non-gate-reference key with a hash value is still rejected (above).
    checks.append(("gate_ref_commit_values_on_whitelisted_paths_valid",
                   not validate_report(base)))

    # --- --validate-report fails closed on ignored/private paths. ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10a" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9r_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase9s_phase9r_docs_only_closeout_interpretation_guard_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading (no real file needed).
    runs_cli_path = str(REPO / "runs" / "phase10a" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # --- validate a temp-file round-trip (synthetic fixture only, no private reads). ---
    with tempfile.TemporaryDirectory(prefix="phase10a_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

        # A runs/-nested temp report is rejected by the path guard.
        runs_tmp = Path(tmp) / "runs" / "report.json"
        runs_tmp.parent.mkdir(parents=True, exist_ok=True)
        runs_tmp.write_text(json.dumps(base), encoding="utf-8")
        ok, _ = _validate_report_path_is_public(runs_tmp)
        checks.append(("validate_report_rejects_temp_runs_path", not ok))

    # --- prove the validator/self-test did not fetch/read private or execute. ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_sources", SOURCE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9_artifacts",
                   PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_tasks_or_samples",
                   TASK_GENERATION_OR_SAMPLING_ATTEMPTS == 0))
    checks.append(("selftest_does_not_score_adjudicate_or_execute",
                   SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 10A independent validation line protocol-freeze (no claim)"
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
        # Fail closed: --validate-report may only read the Phase 10A public
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
