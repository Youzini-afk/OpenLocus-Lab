#!/usr/bin/env python3
"""Phase 9I materialized inventory to task annotation protocol freeze.

This is a docs/report/validator-only protocol freeze.  It freezes the future
protocol for converting the Phase 9H private materialized source inventory
into future task annotation / outcome-acquisition inputs.  It does NOT fetch,
clone, read, or materialize any repository or source, does NOT read ignored
``runs/`` or private candidate pools/registries/manifests or the Phase 9H
private materialized inventory, does NOT generate task annotations (labels),
outcomes, gold rows, evidence_success, or scoring/evaluation rows, and makes
no method/product/performance/model/provider/training/runtime/default/scoring/
outcome/evidence-success claim.

It records that Phase 9H is source-materialization readiness only and is NOT
proof that any annotation, outcome, evidence_success, scoring, or evaluation
works.  Phase 9H did not generate task annotations, outcomes, gold rows,
evidence_success, or scoring rows; it produced only private materialized
inventory rows under ignored ``runs/``.  Phase 9I does not read that private
inventory.  Future annotation execution requires a separate Phase 9J boundary
and explicit private Phase 9H inventory read confirmation.

The Phase 9H public gate reference values (remote commit
``d997caab5487e66c544f657645d70c97f3b780e2``, CI run ``28976655118``) are the
only public gate references published by Phase 9I.  Phase 9G is carried as
inherited provenance only and its exact remote commit/CI run values are
intentionally NOT published in the Phase 9I report/docs (bucketed inherited
provenance) to keep tighter privacy; only the Phase 9H full commit SHA and CI
run are public gate references.  Local same-tree git commits are not read or
compared; the supplied confirmation values are matched against the frozen
public gate constants only.
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

PHASE = (
    "phase9i_materialized_inventory_to_task_annotation_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
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

# Phase 9G inherited provenance (carried forward from Phase 9H).  The exact
# Phase 9G remote commit/CI run values are intentionally NOT published in the
# Phase 9I report/docs; Phase 9G is carried as bucketed inherited provenance
# only (tighter privacy).  Only the Phase 9H full commit SHA / CI run are
# public gate references.
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

PHASE9H_DOCS = (
    REPO / "docs" / "en" / "interventional-evidence-acquisition-phase9h-candidate-source-pool-public-source-network-fetch-materialization-no-scoring-no-claim.md",
    REPO / "docs" / "zh" / "interventional-evidence-acquisition-phase9h-candidate-source-pool-public-source-network-fetch-materialization-no-scoring-no-claim.md",
)

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "task_annotation_generated",
    "private_phase9h_materialized_inventory_read",
    "private_candidate_pool_read",
    "private_registry_read",
    "ignored_runs_read",
    "annotations_generated",
    "outcomes_generated",
    "gold_rows_generated",
    "evidence_success_evaluated",
    "scoring_executed",
    "evaluation_rows_generated",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
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

# Forbidden public field words; only apply to non-boolean values so boolean
# boundary attestation keys such as ``scoring_executed`` or
# ``evidence_success_claim`` are not false-flagged.
FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

# Future allowed annotation types (frozen vocabulary; neutral word
# "annotation" is used rather than "labels" wherever possible).
ALLOWED_FUTURE_ANNOTATION_TYPES = (
    "task_eligibility_annotation",
    "evidence_localization_requirement",
    "expected_evidence_form",
    "outcome_acquisition_preconditions",
    "adjudication_rules",
    "rejection_or_replacement_rules_before_scoring",
)

# Future Phase 9J execution gate conditions that must be present in the report.
FUTURE_PHASE9J_GATE_RULES = (
    "phase9i_commit_and_ci_green_required_before_phase9j",
    "phase9h_commit_and_ci_confirmation_required",
    "phase9i_protocol_freeze_confirmation_required",
    "phase9h_private_materialized_inventory_read_confirmation_required",
    "ignored_runs_workspace_confirmation_required",
    "private_output_only_confirmation_required",
    "no_scoring_or_evidence_success_confirmation_required",
    "no_provider_llm_model_default_runtime_change_confirmation_required",
    "aggregate_public_report_only_confirmation_required",
    "phase9j_may_read_phase9h_private_inventory_only_after_phase9i_commit_and_ci_green",
    "phase9j_remains_no_scoring_no_evidence_success_until_a_separate_frozen_boundary",
)

# Future annotation protocol rules (frozen).
FUTURE_ANNOTATION_RULES = (
    "convert_private_phase9h_materialized_inventory_to_future_task_annotation_inputs_only",
    "task_eligibility_annotation_only_under_explicit_future_confirmation",
    "evidence_localization_requirement_only_for_file_localizable_code_tasks",
    "expected_evidence_form_must_match_phase9h_inventory_shape",
    "outcome_acquisition_preconditions_must_be_set_before_any_outcome_acquisition",
    "adjudication_rules_must_be_frozen_before_any_annotation_execution",
    "rejection_or_replacement_rules_before_scoring_only",
    "no_annotation_execution_in_phase9i",
    "no_outcomes_or_gold_rows_or_evidence_success_or_scoring_rows_in_phase9i",
    "no_provider_or_llm_or_model_or_default_or_runtime_change_in_phase9i",
    "private_phase9h_inventory_read_only_after_phase9i_commit_and_ci_green_and_explicit_confirmation",
    "future_annotation_execution_requires_separate_phase9j_boundary",
    "aggregate_public_report_only_no_private_inventory_or_annotation_details",
    "no_singleton_public_buckets",
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

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:count_1|bucket_one|bucket_1|bucket_up_to_1|bucket_at_most_1|n_1|singleton)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
# Private-shaped KEY detection.  Matches any key that contains a private
# token (substring, case-insensitive) so containing/suffixed forms such as
# ``per_source_bucket``, ``per_task_summary``, ``source_path_bucket``,
# ``repo_commit``, ``private_source_commit`` and ``task_ci_run`` are rejected.
# Known-good boundary-attestation keys that legitimately contain a private
# token in their name (e.g. ``per_source_public_facts``, ``commits_public``,
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

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants (full commit SHA / CI run ID).  This is an exact path
# whitelist, NOT a suffix match, so arbitrary keys ending in ``_commit`` or
# ``_ci_run`` are NOT exempt.  Only the Phase 9H full commit SHA and CI run
# are public gate references; Phase 9G exact commit/CI are intentionally not
# published (bucketed inherited provenance).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9h_gate_references.phase9h_commit",
        "$.phase9h_gate_references.phase9h_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS = 0


def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


# Strict allowed-key schema for the public report.  Leaf values are ``None``
# (their type/content are checked separately in ``validate_report``); a nested
# dict declares the only keys permitted at that object level.  This is used by
# ``_check_allowed_keys`` (rejects any unexpected top-level or nested field)
# and by ``_scan_public`` (exempts known-good boundary-attestation key paths
# from the private-KEY shape scan so legitimate boundary keys such as
# ``per_source_public_facts`` or ``commits_public`` are not false-flagged).
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
        "phase9h_gate_required_before_phase9i": None,
    },
    "phase9i_scope": {
        "docs_report_validator_only": None,
        "protocol_freeze_only": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "task_annotation_generated": None,
        "private_phase9h_materialized_inventory_read": None,
        "private_candidate_pool_read": None,
        "private_registry_read": None,
        "ignored_runs_read": None,
        "annotations_generated": None,
        "outcomes_generated": None,
        "gold_rows_generated": None,
        "evidence_success_evaluated": None,
        "scoring_executed": None,
        "evaluation_rows_generated": None,
        "model_fitting": None,
        "provider_or_llm_calls": None,
        "runtime_default_or_product_changes": None,
        "future_execution_requires_phase9i_commit_and_ci_green": None,
    },
    "future_annotation_protocol": {
        "publication_level": None,
        "allowed_annotation_types": None,
        "annotation_neutral_word_used": None,
        "inherited_phase9h_aggregate_caps": {
            "target_inventory_bucket": None,
            "hard_cap_bucket": None,
            "per_source_cap_bucket": None,
            "minimum_distinct_sources_bucket": None,
        },
        "future_private_input_output_locations": None,
        "annotation_rules": None,
        "future_phase9j_gate_conditions": None,
        "future_annotation_execution_requires_separate_phase9j_boundary": None,
        "future_annotation_execution_requires_explicit_private_phase9h_inventory_read_confirmation": None,
    },
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

    The report path must be under the Phase 9I public artifact directory
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
        return False, "report path is not under the Phase 9I public artifact directory"
    return True, ""


def build_public_report() -> dict[str, Any]:
    """Build the frozen Phase 9I public protocol report.

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
            "phase9h_gate_required_before_phase9i": True,
        },
        "phase9i_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "task_annotation_generated": False,
            "private_phase9h_materialized_inventory_read": False,
            "private_candidate_pool_read": False,
            "private_registry_read": False,
            "ignored_runs_read": False,
            "annotations_generated": False,
            "outcomes_generated": False,
            "gold_rows_generated": False,
            "evidence_success_evaluated": False,
            "scoring_executed": False,
            "evaluation_rows_generated": False,
            "model_fitting": False,
            "provider_or_llm_calls": False,
            "runtime_default_or_product_changes": False,
            "future_execution_requires_phase9i_commit_and_ci_green": True,
        },
        "future_annotation_protocol": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "allowed_annotation_types": list(ALLOWED_FUTURE_ANNOTATION_TYPES),
            "annotation_neutral_word_used": "annotation_not_labels",
            "inherited_phase9h_aggregate_caps": {
                "target_inventory_bucket": "bucket_48_to_72",
                "hard_cap_bucket": "bucket_up_to_96",
                "per_source_cap_bucket": "bucket_up_to_8",
                "minimum_distinct_sources_bucket": "bucket_at_least_8",
            },
            "future_private_input_output_locations": "ignored runs/ only, not read in phase9i",
            "annotation_rules": list(FUTURE_ANNOTATION_RULES),
            "future_phase9j_gate_conditions": list(FUTURE_PHASE9J_GATE_RULES),
            "future_annotation_execution_requires_separate_phase9j_boundary": True,
            "future_annotation_execution_requires_explicit_private_phase9h_inventory_read_confirmation": True,
        },
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
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": (
            "future_annotation_execution_requires_separate_phase9j_boundary"
            "_and_explicit_private_phase9h_inventory_read_confirmation"
        ),
    }


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
    # gold) only apply to non-boolean values: boolean attestation keys such as
    # ``scoring_executed`` or ``evidence_success_claim`` are boundary checks
    # that must be ``false``, not exposed scoring data.
    if not isinstance(value, bool) and any(
        word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS
    ):
        errors.append(f"forbidden public field word at {path}")
    # Private-shaped KEY detection.  Known-good boundary-attestation keys that
    # legitimately contain a private token (e.g. ``per_source_public_facts``,
    # ``commits_public``, ``manifest_locations_public``) are at allowed-schema
    # paths and are exempted here; gate-reference commit/CI keys are allowed
    # paths too.  Containing/suffixed private forms not in the schema (e.g.
    # ``per_source_bucket``, ``repo_commit``, ``task_ci_run``) are rejected.
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
        # Gate-reference commit/CI values are expected public gate constants;
        # they are exempt from the private-shaped value scan only.
        if not is_gate_ref:
            if PRIVATE_SHAPED_VALUE_RE.search(value):
                errors.append(f"private-shaped public value at {path}")
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
    # values are intentionally NOT published (bucketed inherited provenance);
    # only their existence as bucketed inherited provenance is validated.
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
    if gate9h.get("phase9h_gate_required_before_phase9i") is not True:
        errors.append("Phase 9H gate-required boundary missing")

    # Phase 9I scope
    scope = report.get("phase9i_scope", {})
    for key in ("docs_report_validator_only", "protocol_freeze_only"):
        if scope.get(key) is not True:
            errors.append(f"phase9i scope missing: {key}")
    for key in (
        "public_fetch_clone_executed",
        "source_materialization_executed",
        "task_annotation_generated",
        "private_phase9h_materialized_inventory_read",
        "private_candidate_pool_read",
        "private_registry_read",
        "ignored_runs_read",
        "annotations_generated",
        "outcomes_generated",
        "gold_rows_generated",
        "evidence_success_evaluated",
        "scoring_executed",
        "evaluation_rows_generated",
        "model_fitting",
        "provider_or_llm_calls",
        "runtime_default_or_product_changes",
    ):
        if scope.get(key) is not False:
            errors.append(f"phase9i execution boundary failed: {key}")
    if scope.get("future_execution_requires_phase9i_commit_and_ci_green") is not True:
        errors.append("phase9i future execution commit+CI-green boundary missing")

    # Future annotation protocol
    future = report.get("future_annotation_protocol", {})
    if future.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("future annotation protocol publication level drift")
    if future.get("annotation_neutral_word_used") != "annotation_not_labels":
        errors.append("future annotation protocol neutral-word boundary missing")
    allowed_types = future.get("allowed_annotation_types")
    if not isinstance(allowed_types, list):
        errors.append("allowed annotation types missing")
    else:
        required_types = set(ALLOWED_FUTURE_ANNOTATION_TYPES)
        present_types = set(allowed_types)
        missing_types = required_types - present_types
        if missing_types:
            errors.append(
                "allowed annotation types missing: " + ", ".join(sorted(missing_types))
            )
    caps = future.get("inherited_phase9h_aggregate_caps", {})
    expected_caps = {
        "target_inventory_bucket": "bucket_48_to_72",
        "hard_cap_bucket": "bucket_up_to_96",
        "per_source_cap_bucket": "bucket_up_to_8",
        "minimum_distinct_sources_bucket": "bucket_at_least_8",
    }
    for cap_key, expected in expected_caps.items():
        if caps.get(cap_key) != expected:
            errors.append(f"inherited phase9h aggregate cap drift: {cap_key}")
    if future.get("future_private_input_output_locations") != "ignored runs/ only, not read in phase9i":
        errors.append("future private input/output locations drift")
    rules = future.get("annotation_rules")
    if not isinstance(rules, list) or not rules:
        errors.append("future annotation rules missing")
    else:
        required_rules = set(FUTURE_ANNOTATION_RULES)
        present_rules = set(rules)
        missing_rules = required_rules - present_rules
        if missing_rules:
            errors.append(
                "future annotation rules missing: " + ", ".join(sorted(missing_rules))
            )
    gate_conditions = future.get("future_phase9j_gate_conditions")
    if not isinstance(gate_conditions, list) or not gate_conditions:
        errors.append("future phase9j gate conditions missing")
    else:
        required_gates = set(FUTURE_PHASE9J_GATE_RULES)
        present_gates = set(gate_conditions)
        missing_gates = required_gates - present_gates
        if missing_gates:
            errors.append(
                "future phase9j gate conditions missing: " + ", ".join(sorted(missing_gates))
            )
    if future.get("future_annotation_execution_requires_separate_phase9j_boundary") is not True:
        errors.append("future annotation execution phase9j boundary missing")
    if future.get("future_annotation_execution_requires_explicit_private_phase9h_inventory_read_confirmation") is not True:
        errors.append("future annotation execution private inventory read confirmation missing")

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
        "future_annotation_execution_requires_separate_phase9j_boundary"
        "_and_explicit_private_phase9h_inventory_read_confirmation"
    ):
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS, PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_INVENTORY_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))
    checks.append(("base_status_equals_phase", base["status"] == STATUS))

    # Reject missing Phase 9H gate references.
    mutated = copy.deepcopy(base)
    del mutated["phase9h_gate_references"]["phase9h_commit"]
    checks.append(("missing_phase9h_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    del mutated["phase9h_gate_references"]["phase9h_ci_run"]
    checks.append(("missing_phase9h_ci_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_status"] = "drift"
    checks.append(("phase9h_status_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_ci_success"] = False
    checks.append(("phase9h_ci_success_false_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_source_materialization_readiness_only"] = False
    checks.append(("phase9h_readiness_only_false_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_not_proof_annotation_or_outcome_or_evidence_success_works"] = False
    checks.append(("phase9h_not_proof_false_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_did_not_generate_annotations_or_outcomes_or_gold_rows_or_evidence_success_or_scoring_rows"] = False
    checks.append(("phase9h_no_generation_false_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_private_materialized_inventory_under_ignored_runs_only"] = False
    checks.append(("phase9h_private_inventory_boundary_false_rejected", bool(validate_report(mutated))))

    # Reject wrong Phase 9H commit / CI values.
    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_commit"] = "deadbeef" * 5
    checks.append(("wrong_phase9h_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9h_gate_references"]["phase9h_ci_run"] = "0000"
    checks.append(("wrong_phase9h_ci_rejected", bool(validate_report(mutated))))

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

    mutated = copy.deepcopy(base)
    mutated["phase9g_inherited_provenance"]["phase9g_status"] = "drift"
    checks.append(("phase9g_status_drift_rejected", bool(validate_report(mutated))))

    # Reject missing Phase 9F inherited provenance.
    mutated = copy.deepcopy(base)
    mutated["phase9f_inherited_provenance"]["phase9f_status"] = "drift"
    checks.append(("phase9f_status_drift_rejected", bool(validate_report(mutated))))

    # Reject execution booleans set to true.
    for exec_key in (
        "public_fetch_clone_executed",
        "source_materialization_executed",
        "task_annotation_generated",
        "private_phase9h_materialized_inventory_read",
        "annotations_generated",
        "outcomes_generated",
        "gold_rows_generated",
        "evidence_success_evaluated",
        "scoring_executed",
        "evaluation_rows_generated",
        "model_fitting",
        "provider_or_llm_calls",
        "runtime_default_or_product_changes",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9i_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject private_phase9h_materialized_inventory_read=true specifically.
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["private_phase9h_materialized_inventory_read"] = True
    mutated["no_execution_booleans"]["private_phase9h_materialized_inventory_read"] = True
    checks.append(("private_phase9h_inventory_read_rejected", bool(validate_report(mutated))))

    # Reject ignored_runs_read=true.
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["ignored_runs_read"] = True
    mutated["no_execution_booleans"]["ignored_runs_read"] = True
    checks.append(("ignored_runs_read_rejected", bool(validate_report(mutated))))

    # Reject forbidden public field words in non-boolean values.
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(base)
        mutated["phase9i_scope"][bad_key] = "exposed_value"
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    # Reject claim boundary set to true.
    for claim_key in (
        "provider_claim",
        "model_claim",
        "runtime_claim",
        "default_claim",
        "product_claim",
        "performance_claim",
        "method_claim",
        "training_claim",
        "scoring_claim",
        "outcome_claim",
        "evidence_success_claim",
    ):
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject privacy contract violations.
    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["per_source_public_facts"] = True
    checks.append(("per_source_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["per_task_public_facts"] = True
    checks.append(("per_task_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["run_locations_public"] = True
    checks.append(("run_locations_public_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["repo_names_public"] = True
    checks.append(("repo_names_public_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["example_bucket"] = "count_1"
    checks.append(("count_1_singleton_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["example_bucket"] = "bucket_one"
    checks.append(("bucket_one_singleton_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["example_bucket"] = "singleton"
    checks.append(("singleton_wording_rejected", bool(validate_report(mutated))))

    # Reject exact count fields.
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["candidate_count"] = 72
    checks.append(("candidate_count_field_rejected", bool(validate_report(mutated))))

    # Reject private-shaped values (URL / path / hash / owner/repo).
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["example_value"] = "https://example.invalid/repo.git"
    checks.append(("url_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["example_value"] = "owner/repo"
    checks.append(("owner_repo_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["example_value"] = "a" * 40
    checks.append(("hash_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["example_value"] = "src/private.py"
    checks.append(("path_private_shaped_value_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["path"] = "src/private.py"
    checks.append(("private_shaped_key_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["repo_name"] = "hidden"
    checks.append(("private_shaped_key_repo_name_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["task_id"] = "hidden"
    checks.append(("private_shaped_key_task_id_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["row_id"] = "hidden"
    checks.append(("private_shaped_key_row_id_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["manifest"] = "hidden"
    checks.append(("private_shaped_key_manifest_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["run_dir"] = "hidden"
    checks.append(("private_shaped_key_run_dir_rejected", bool(validate_report(mutated))))

    # Reject claim-making wording in exposed string values.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "materialization works and is proven"
    checks.append(("claim_wording_materialization_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["example_note"] = "annotation works"
    checks.append(("claim_wording_annotation_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["example_note"] = "evidence_success achieved"
    checks.append(("claim_wording_evidence_success_rejected", bool(validate_report(mutated))))

    # Reject future execution without phase9i commit+CI green.
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["future_execution_requires_phase9i_commit_and_ci_green"] = False
    checks.append(("future_execution_without_commit_ci_rejected", bool(validate_report(mutated))))

    # Reject a missing required future annotation rule.
    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["annotation_rules"] = [
        r for r in base["future_annotation_protocol"]["annotation_rules"]
        if r != "no_annotation_execution_in_phase9i"
    ]
    checks.append(("missing_required_annotation_rule_rejected", bool(validate_report(mutated))))

    # Reject a missing required allowed annotation type.
    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["allowed_annotation_types"] = [
        t for t in base["future_annotation_protocol"]["allowed_annotation_types"]
        if t != "task_eligibility_annotation"
    ]
    checks.append(("missing_required_annotation_type_rejected", bool(validate_report(mutated))))

    # Reject a missing required future phase9j gate condition.
    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["future_phase9j_gate_conditions"] = [
        g for g in base["future_annotation_protocol"]["future_phase9j_gate_conditions"]
        if g != "phase9i_commit_and_ci_green_required_before_phase9j"
    ]
    checks.append(("missing_required_phase9j_gate_condition_rejected", bool(validate_report(mutated))))

    # Reject inherited cap drift.
    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["inherited_phase9h_aggregate_caps"]["target_inventory_bucket"] = "bucket_wrong"
    checks.append(("inherited_cap_drift_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Gate-reference commit values are exempt from private-shaped value scan
    # but a non-gate-reference key with a hash value is still rejected.
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["example_hash"] = "d997caab5487e66c544f657645d70c97f3b780e2"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    # Validate a temp-file round-trip.
    with tempfile.TemporaryDirectory(prefix="phase9i_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- Issue #3: strict allowed-key checking rejects unknown fields. ---
    mutated = copy.deepcopy(base)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_annotation_protocol"]["inherited_phase9h_aggregate_caps"]["unexpected_cap"] = "x"
    checks.append(("unknown_nested_field_caps_rejected", bool(validate_report(mutated))))

    # --- Issue #4: containing/suffixed private-shaped keys are rejected. ---
    for bad_key in (
        "private_source_commit",
        "repo_commit",
        "task_ci_run",
        "per_source_bucket",
        "per_task_summary",
        "source_path_bucket",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9i_scope"][bad_key] = "example"
        checks.append((
            f"private_key_{bad_key}_rejected",
            bool(validate_report(mutated)),
        ))
        # Direct regex assertion isolating the private-key detector itself.
        checks.append((
            f"private_key_regex_{bad_key}",
            bool(PRIVATE_KEY_RE.search(bad_key)),
        ))

    # --- Issue #5: extended singleton bucket forms are rejected.  Appended to
    # a list of strings so the singleton scanner is the only error that fires
    # (no missing-rule error, no allowed-key error on list elements). ---
    for singleton_val in ("bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1"):
        mutated = copy.deepcopy(base)
        mutated["future_annotation_protocol"]["annotation_rules"].append(singleton_val)
        checks.append((
            f"singleton_{singleton_val}_rejected",
            bool(validate_report(mutated)),
        ))
        checks.append((
            f"singleton_regex_{singleton_val}",
            bool(SINGLETON_BUCKET_RE.search(singleton_val)),
        ))

    # Existing singleton forms remain rejected (regression guard).
    for singleton_val in ("count_1", "bucket_one", "singleton"):
        mutated = copy.deepcopy(base)
        mutated["future_annotation_protocol"]["annotation_rules"].append(singleton_val)
        checks.append((
            f"singleton_existing_{singleton_val}_rejected",
            bool(validate_report(mutated)),
        ))

    # --- Issue #6: forbidden claim phrases are rejected.  Appended to a list
    # of strings so the claim scanner is the only error that fires. ---
    forbidden_claim_phrases = (
        "method effectiveness",
        "product readiness",
        "scoring success",
        "outcome success",
        "evaluation works",
        "task annotation readiness",
    )
    for phrase in forbidden_claim_phrases:
        mutated = copy.deepcopy(base)
        mutated["future_annotation_protocol"]["annotation_rules"].append(phrase)
        checks.append((
            f"claim_phrase_{phrase.replace(' ', '_')}_rejected",
            bool(validate_report(mutated)),
        ))
        checks.append((
            f"claim_phrase_regex_{phrase.replace(' ', '_')}",
            bool(CLAIM_WORDING_RE.search(phrase)),
        ))

    # --- Issue #2: gate-reference exemption is an exact path whitelist; a
    # key that merely ends in ``_commit`` / ``_ci_run`` outside the exact
    # gate-reference path is NOT exempt and its hash/CI value is rejected. ---
    mutated = copy.deepcopy(base)
    mutated["phase9i_scope"]["task_ci_run"] = "28976655118"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    checks.append((
        "non_whitelisted_ci_run_key_not_exempt",
        any("private-shaped public key" in e for e in errors),
    ))

    # --- Issue #7: --validate-report fails closed on ignored/private paths. ---
    ok, reason = _validate_report_path_is_public(REPO / "runs" / "phase9i" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, reason = _validate_report_path_is_public(REPO / "runs" / "phase9i_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, reason = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, reason = _validate_report_path_is_public(REPO / "artifacts" / "other_phase" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, reason = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading (no real file needed).
    runs_cli_path = str(REPO / "runs" / "phase9i" / "report.json")
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

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9I materialized inventory to task annotation protocol freeze"
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
        # Fail closed: --validate-report may only read the Phase 9I public
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
