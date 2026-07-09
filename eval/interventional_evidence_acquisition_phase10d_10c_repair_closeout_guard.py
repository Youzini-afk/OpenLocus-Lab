#!/usr/bin/env python3
"""Phase 10D 10C repair closeout guard (docs/report/validator-only, no claim).

This is the DOCS-ONLY CLOSEOUT / BOUNDARY GUARD for Phase 10C.  Phase 10C
executed the frozen Phase 10B input-construction/materialization route once
(research commit ``0be627d``) and produced a repair/no-claim checkpoint: the
accepted-source bucket was zero and no compliant candidate source registry was
available.  Phase 10D closes 10C: it states the 10C result is a valid execution
of the frozen 10B route but produced zero accepted sources and no validation
evidence.

Phase 10D itself performs NO execution and makes NO new evidence claims.  It
does NOT construct/edit/select/filter/supply a candidate source registry, does
NOT fetch/clone/read source material, does NOT rerun materialization, does NOT
change the frozen Phase 10B protocol, does NOT score/adjudicate/run
correctness/evidence_success, and does NOT add thresholds/fallbacks/exceptions.

Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation,
repair, rerun, rescore, or strengthening of Phase 9R/9S.  Phase 9 is closed.

This module performs no network/filesystem fetch, no private reads, no source
reads, no ignored-``runs/`` reads, no Phase 9/10A/10B/10C private artifact
reads, and no scoring/adjudication/correctness/evidence_success computation.
The dry self-test and report validation use synthetic tempfile fixtures only.
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
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

PHASE = "phase10d_10c_repair_closeout_guard_no_claim"
SCHEMA_VERSION = (
    "phase10d_10c_repair_closeout_guard_no_claim_report_v1"
)
STATUS = "phase10d_10c_repair_closeout_guard_no_claim"

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# Frozen gate references (the only exact public gate references published by
# Phase 10D).  Local same-tree git commits are not read or compared; supplied
# confirmation values are matched against the frozen public gate constants
# only.
PHASE9_CLOSED_COMMIT = "1d71f6a"
PHASE10A_COMMIT = "67e8d984601d82a2a97992bb83fda06b09e06be0"
PHASE10A_CI_RUN = "29002587099"
PHASE10A_STATUS = "phase10a_independent_validation_protocol_freeze_no_execution_no_claim"
PHASE10B_COMMIT = "19abcdd8f09e190c323a28fab8e3e0401d504236"
PHASE10B_CI_RUN = "29004189917"
PHASE10B_STATUS = (
    "phase10b_fresh_fenced_input_construction_protocol_freeze"
    "_no_execution_no_materialization_no_claim"
)
PHASE10C_RESEARCH_COMMIT = "0be627d"
PHASE10C_STATUS = "phase10c_input_construction_repair_no_claim"
PHASE10C_ACCEPTED_SOURCE_BUCKET = "bucket_zero"
PHASE10C_REPAIR_REASON_BUCKET = "bucket_no_eligible_channel_registry"

# Separate CI hygiene commit (CI infrastructure only, NOT empirical evidence).
HYGIENE_COMMIT = "dad6049"
HYGIENE_CI_RUN = "29015062502"
HYGIENE_CI_SUCCESS = True
HYGIENE_SCOPE = (
    "ci_infrastructure_only_no_eval_protocol_report_docs_results_change"
)
HYGIENE_WORKFLOW_FILE = ".github/workflows/empirical-research.yml"
HYGIENE_CHANGE_DESCRIPTION = (
    "b16a_b16b_f1_timeouts_15_to_30_minutes_only"
)

PROTOCOL_PUBLICATION_LEVEL = "aggregate_10c_repair_closeout_guard_boundary_only"

# Truth-boundary attestation keys that must always be True.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_inherited",
    "phase10a_gate_inherited",
    "phase10b_gate_inherited",
    "phase10c_executed_frozen_10b_route_once",
    "phase10c_result_repair_no_claim_zero_accepted_sources",
    "phase10c_produced_no_validation_evidence",
    "phase10d_is_docs_only_closeout_no_claim",
    "phase10d_makes_no_new_evidence_claims",
    "phase10d_does_not_construct_or_supply_candidate_registry",
    "phase10d_does_not_change_frozen_phase10b_protocol",
    "phase10d_is_separate_from_phase9_not_continuation",
)

# Boundary attestation keys that must always be False.
NO_EXECUTION_FALSE_KEYS = (
    "scoring_executed",
    "adjudication_executed",
    "correctness_evaluated",
    "evidence_success_evaluated",
    "provider_calls_executed",
    "model_fitting",
    "runtime_default_or_product_changes",
    "phase9_artifacts_read_or_reused",
    "phase9_labels_or_outcomes_reused_as_input",
    "phase9_source_filters_or_priors_reused",
    "phase9_sampling_inputs_reused",
    "clean_room_operator_used_phase9_private_material_memory",
    "protocol_edited_after_observation",
    "caps_changed_after_observation",
    "eligibility_changed_after_observation",
    "randomness_used",
    "padding_or_tuning_below_minimum",
    "candidate_registry_constructed",
    "candidate_registry_edited",
    "candidate_registry_selected",
    "candidate_registry_filtered",
    "candidate_registry_supplied",
    "source_material_fetched_or_cloned",
    "source_material_read",
    "materialization_rerun",
    "thresholds_added",
    "fallbacks_added",
    "exceptions_added",
)

CLAIM_BOUNDARY_FALSE_KEYS = (
    "method_claim",
    "model_claim",
    "runtime_claim",
    "default_claim",
    "scoring_claim",
    "outcome_claim",
    "evidence_success_claim",
    "correctness_claim",
    "generalization_claim",
    "validation_claim",
    "materialization_succeeded_claim",
    "independent_validation_passed_claim",
    "openlocus_works_claim",
    "phase10_confirms_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
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
    "phase10a_private_artifacts_public",
    "phase10b_private_artifacts_public",
    "phase10c_private_artifacts_public",
    "source_urls_public",
    "candidate_repo_names_public",
    "candidate_registry_contents_public",
)

FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

CONSERVATIVE_RECOMMENDATION = (
    "phase10d_10c_repair_closeout_guard_docs_only_no_claim"
    "_phase9_closed_inherited_phase10a_gate_inherited"
    "_phase10b_gate_inherited_phase10c_executed_frozen_10b_route_once"
    "_phase10c_result_repair_no_claim_zero_accepted_sources_no_validation_evidence"
    "_phase10d_is_docs_only_closeout_no_new_evidence_claims"
    "_phase10d_does_not_construct_edit_select_filter_or_supply_candidate_registry"
    "_phase10d_does_not_fetch_clone_read_source_material_or_rerun_materialization"
    "_phase10d_does_not_change_frozen_phase10b_protocol"
    "_phase10d_does_not_score_adjudicate_or_run_correctness_evidence_success"
    "_phase10d_does_not_add_thresholds_fallbacks_or_exceptions"
    "_hygiene_commit_is_ci_infrastructure_only_not_empirical_evidence"
    "_next_possible_phase_is_phase10e_candidate_source_registry_construction"
    "_protocol_freeze_only_not_registry_construction_or_execution"
    "_boundary_review_after_phase10d_commit_and_ci_green"
    "_no_user_approval_wording_no_method_product_correctness_evidence_success_claim"
)

# ---------------------------------------------------------------------------
# Privacy scan regexes
# ---------------------------------------------------------------------------

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
    r"|independent\s+validation\s+passed"
    r"|openlocus\s+works"
    r"|phase\s*10\s+confirms"
    r"|phase\s*10c\s+confirms"
    r"|validated\b"
    r"|materialization\s+succeeded"
    r"|correctness\s+evidence"
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
    r"|candidate_identity|commit_sha|sha|hash"
    r"|path|range|snippet|task_id|row_id|packet_id"
    r"|observable_id|observable_path|manifest|run_dir"
    r"|per_source|per_task|per_packet)",
    re.IGNORECASE,
)
LIST_VALUE_PRIVATE_TOKEN_RE = re.compile(
    r"(?:task_id|row_id|packet_id|observable_id|observable_path"
    r"|run_dir|source_path|manifest_path|candidate_id|commit_sha)",
    re.IGNORECASE,
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants.  These are the only exact public gate references
# published by Phase 10D.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10a_commit",
        "$.gate_facts.phase10a_ci_run",
        "$.gate_facts.phase10b_commit",
        "$.gate_facts.phase10b_ci_run",
        "$.gate_facts.phase10c_research_commit",
        "$.gate_facts.hygiene_commit",
        "$.gate_facts.hygiene_ci_run",
        "$.gate_facts.hygiene_workflow_file",
    }
)
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10a_ci_run",
        "$.gate_facts.phase10b_ci_run",
        "$.gate_facts.hygiene_ci_run",
    }
)
# Short provenance commit prefixes (not full SHAs) are permitted only at the
# gate-facts commit paths above.
SHORT_COMMIT_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase9_closed_commit",
        "$.gate_facts.phase10a_commit",
        "$.gate_facts.phase10b_commit",
        "$.gate_facts.phase10c_research_commit",
        "$.gate_facts.hygiene_commit",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read/
# execute/score.  Phase 10D has no execution path at all; these stay zero.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_DISCOVERY_ATTEMPTS = 0
MATERIALIZATION_ATTEMPTS = 0
PACKET_GENERATION_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
SOURCE_MATERIAL_READ_ATTEMPTS = 0
CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS = 0
SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0


# ---------------------------------------------------------------------------
# Ignored-runs / privacy helpers
# ---------------------------------------------------------------------------

def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--validate-report``.

    The report path must be under the Phase 10D public artifact directory
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
        return False, "report path is not under the Phase 10D public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Strict allowed-key schema for the public report
# ---------------------------------------------------------------------------

ALLOWED_REPORT_KEYS: dict[str, Any] = {
    "schema_version": None,
    "phase": None,
    "status": None,
    "publication_level": None,
    "gate_facts": {
        "phase9_closed_commit": None,
        "phase10a_commit": None,
        "phase10a_ci_run": None,
        "phase10a_status": None,
        "phase10b_commit": None,
        "phase10b_ci_run": None,
        "phase10b_status": None,
        "phase10c_research_commit": None,
        "phase10c_status": None,
        "phase10c_accepted_source_bucket": None,
        "phase10c_repair_reason_bucket": None,
        "hygiene_commit": None,
        "hygiene_ci_run": None,
        "hygiene_ci_success": None,
        "hygiene_scope": None,
        "hygiene_workflow_file": None,
        "hygiene_change_description": None,
        "hygiene_is_ci_infrastructure_only_not_empirical_evidence": None,
        "gate_constants_are_exact_references_only": None,
        "local_same_tree_git_commits_not_read_or_compared": None,
        "older_phase9_exact_refs_not_republished_by_phase10d": None,
    },
    "phase10d_scope": {
        "docs_only_closeout_no_claim": None,
        "separate_from_phase9_not_continuation": None,
        "closes_phase10c_repair_no_claim": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "phase10c_result_summary": {
        "phase10c_executed_frozen_10b_route_once": None,
        "phase10c_result_repair_no_claim": None,
        "phase10c_accepted_source_bucket_zero": None,
        "phase10c_no_compliant_candidate_source_registry_available": None,
        "phase10c_produced_no_validation_evidence": None,
        "phase10c_did_not_score_adjudicate_or_run_correctness_evidence_success": None,
        "phase10c_oracle_blockers_repaired_without_changing_frozen_10b_protocol": None,
        "phase10c_zero_accepted_is_not_partial_success": None,
    },
    "phase10d_boundary": {
        "performs_no_execution": None,
        "makes_no_new_evidence_claims": None,
        "does_not_construct_edit_select_filter_or_supply_candidate_registry": None,
        "does_not_fetch_clone_or_read_source_material": None,
        "does_not_rerun_materialization": None,
        "does_not_change_frozen_phase10b_protocol": None,
        "does_not_score_adjudicate_or_run_correctness_evidence_success": None,
        "does_not_add_thresholds_fallbacks_or_exceptions": None,
        "next_possible_phase_is_phase10e_candidate_registry_construction_protocol_freeze": None,
        "next_phase_is_protocol_freeze_only_not_registry_construction_or_execution": None,
        "boundary_review_required_after_phase10d_commit_and_ci_green": None,
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
        "phase10d_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_read_phase10c_artifacts": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_generate_packets": None,
        "validator_does_not_construct_candidate_registry": None,
        "validator_does_not_score_adjudicate_or_evaluate": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_generates_packets": None,
        "validator_constructs_candidate_registry": None,
        "validator_scores_or_adjudicates": None,
        "public_artifact_privacy_audit_expected": None,
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
    is_short_commit_exempt = path in SHORT_COMMIT_EXEMPT_PATHS
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
        if not is_gate_ref and not is_short_commit_exempt:
            if PRIVATE_SHAPED_VALUE_RE.search(value):
                errors.append(f"private-shaped public value at {path}")
        if path not in DECIMAL_CI_RUN_EXEMPT_PATHS and not is_short_commit_exempt:
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


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report() -> dict[str, Any]:
    """Build the Phase 10D docs-only closeout guard public report.

    This performs no network/filesystem fetch, no private reads, no source
    reads, no ignored-``runs/`` reads, and no scoring.  It assembles the
    report from the frozen gate constants only.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "publication_level": PROTOCOL_PUBLICATION_LEVEL,
        "gate_facts": {
            "phase9_closed_commit": PHASE9_CLOSED_COMMIT,
            "phase10a_commit": PHASE10A_COMMIT,
            "phase10a_ci_run": PHASE10A_CI_RUN,
            "phase10a_status": PHASE10A_STATUS,
            "phase10b_commit": PHASE10B_COMMIT,
            "phase10b_ci_run": PHASE10B_CI_RUN,
            "phase10b_status": PHASE10B_STATUS,
            "phase10c_research_commit": PHASE10C_RESEARCH_COMMIT,
            "phase10c_status": PHASE10C_STATUS,
            "phase10c_accepted_source_bucket": PHASE10C_ACCEPTED_SOURCE_BUCKET,
            "phase10c_repair_reason_bucket": PHASE10C_REPAIR_REASON_BUCKET,
            "hygiene_commit": HYGIENE_COMMIT,
            "hygiene_ci_run": HYGIENE_CI_RUN,
            "hygiene_ci_success": HYGIENE_CI_SUCCESS,
            "hygiene_scope": HYGIENE_SCOPE,
            "hygiene_workflow_file": HYGIENE_WORKFLOW_FILE,
            "hygiene_change_description": HYGIENE_CHANGE_DESCRIPTION,
            "hygiene_is_ci_infrastructure_only_not_empirical_evidence": True,
            "gate_constants_are_exact_references_only": True,
            "local_same_tree_git_commits_not_read_or_compared": True,
            "older_phase9_exact_refs_not_republished_by_phase10d": True,
        },
        "phase10d_scope": {
            "docs_only_closeout_no_claim": True,
            "separate_from_phase9_not_continuation": True,
            "closes_phase10c_repair_no_claim": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "phase10c_result_summary": {
            "phase10c_executed_frozen_10b_route_once": True,
            "phase10c_result_repair_no_claim": True,
            "phase10c_accepted_source_bucket_zero": True,
            "phase10c_no_compliant_candidate_source_registry_available": True,
            "phase10c_produced_no_validation_evidence": True,
            "phase10c_did_not_score_adjudicate_or_run_correctness_evidence_success": True,
            "phase10c_oracle_blockers_repaired_without_changing_frozen_10b_protocol": True,
            "phase10c_zero_accepted_is_not_partial_success": True,
        },
        "phase10d_boundary": {
            "performs_no_execution": True,
            "makes_no_new_evidence_claims": True,
            "does_not_construct_edit_select_filter_or_supply_candidate_registry": True,
            "does_not_fetch_clone_or_read_source_material": True,
            "does_not_rerun_materialization": True,
            "does_not_change_frozen_phase10b_protocol": True,
            "does_not_score_adjudicate_or_run_correctness_evidence_success": True,
            "does_not_add_thresholds_fallbacks_or_exceptions": True,
            "next_possible_phase_is_phase10e_candidate_registry_construction_protocol_freeze": True,
            "next_phase_is_protocol_freeze_only_not_registry_construction_or_execution": True,
            "boundary_review_required_after_phase10d_commit_and_ci_green": True,
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
            "phase10d_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_read_phase10c_artifacts": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_generate_packets": True,
            "validator_does_not_construct_candidate_registry": True,
            "validator_does_not_score_adjudicate_or_evaluate": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_generates_packets": False,
            "validator_constructs_candidate_registry": False,
            "validator_scores_or_adjudicates": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_report(report: Any) -> list[str]:
    """Validate the Phase 10D public report against the frozen schema/constants.

    This does NOT read any Phase 9/10A/10B/10C artifact on disk, does NOT
    fetch/clone, does NOT read ignored ``runs/``, and does NOT score.  It
    checks the report's gate references against the frozen public gate
    constants directly.
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
    if report.get("publication_level") != PROTOCOL_PUBLICATION_LEVEL:
        errors.append("publication level drift")

    gate = report.get("gate_facts", {})
    if gate.get("phase9_closed_commit") != PHASE9_CLOSED_COMMIT:
        errors.append("Phase 9 closed commit gate reference drift")
    if gate.get("phase10a_commit") != PHASE10A_COMMIT:
        errors.append("Phase 10A commit gate reference drift")
    if gate.get("phase10a_ci_run") != PHASE10A_CI_RUN:
        errors.append("Phase 10A CI run gate reference drift")
    if gate.get("phase10a_status") != PHASE10A_STATUS:
        errors.append("Phase 10A status gate reference drift")
    if gate.get("phase10b_commit") != PHASE10B_COMMIT:
        errors.append("Phase 10B commit gate reference drift")
    if gate.get("phase10b_ci_run") != PHASE10B_CI_RUN:
        errors.append("Phase 10B CI run gate reference drift")
    if gate.get("phase10b_status") != PHASE10B_STATUS:
        errors.append("Phase 10B status gate reference drift")
    if gate.get("phase10c_research_commit") != PHASE10C_RESEARCH_COMMIT:
        errors.append("Phase 10C research commit gate reference drift")
    if gate.get("phase10c_status") != PHASE10C_STATUS:
        errors.append("Phase 10C status gate reference drift")
    if gate.get("phase10c_accepted_source_bucket") != PHASE10C_ACCEPTED_SOURCE_BUCKET:
        errors.append("Phase 10C accepted source bucket gate fact drift")
    if gate.get("phase10c_repair_reason_bucket") != PHASE10C_REPAIR_REASON_BUCKET:
        errors.append("Phase 10C repair reason bucket gate fact drift")
    if gate.get("hygiene_commit") != HYGIENE_COMMIT:
        errors.append("hygiene commit gate reference drift")
    if gate.get("hygiene_ci_run") != HYGIENE_CI_RUN:
        errors.append("hygiene CI run gate reference drift")
    if gate.get("hygiene_ci_success") is not True:
        errors.append("hygiene CI success gate missing")
    if gate.get("hygiene_scope") != HYGIENE_SCOPE:
        errors.append("hygiene scope gate fact drift")
    if gate.get("hygiene_workflow_file") != HYGIENE_WORKFLOW_FILE:
        errors.append("hygiene workflow file gate fact drift")
    if gate.get("hygiene_change_description") != HYGIENE_CHANGE_DESCRIPTION:
        errors.append("hygiene change description gate fact drift")
    if gate.get("hygiene_is_ci_infrastructure_only_not_empirical_evidence") is not True:
        errors.append("hygiene CI infrastructure boundary missing")
    if gate.get("gate_constants_are_exact_references_only") is not True:
        errors.append("gate constants exact references boundary missing")
    if gate.get("local_same_tree_git_commits_not_read_or_compared") is not True:
        errors.append("local git commits not read boundary missing")
    if gate.get("older_phase9_exact_refs_not_republished_by_phase10d") is not True:
        errors.append("older phase9 refs not republished boundary missing")

    scope = report.get("phase10d_scope", {})
    for key in ("docs_only_closeout_no_claim",
                "separate_from_phase9_not_continuation",
                "closes_phase10c_repair_no_claim"):
        if scope.get(key) is not True:
            errors.append(f"phase10d_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10d_scope execution boundary failed: {key}")

    csum = report.get("phase10c_result_summary", {})
    for key in (
        "phase10c_executed_frozen_10b_route_once",
        "phase10c_result_repair_no_claim",
        "phase10c_accepted_source_bucket_zero",
        "phase10c_no_compliant_candidate_source_registry_available",
        "phase10c_produced_no_validation_evidence",
        "phase10c_did_not_score_adjudicate_or_run_correctness_evidence_success",
        "phase10c_oracle_blockers_repaired_without_changing_frozen_10b_protocol",
        "phase10c_zero_accepted_is_not_partial_success",
    ):
        if csum.get(key) is not True:
            errors.append(f"phase10c_result_summary boundary missing: {key}")

    boundary = report.get("phase10d_boundary", {})
    for key in (
        "performs_no_execution",
        "makes_no_new_evidence_claims",
        "does_not_construct_edit_select_filter_or_supply_candidate_registry",
        "does_not_fetch_clone_or_read_source_material",
        "does_not_rerun_materialization",
        "does_not_change_frozen_phase10b_protocol",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_add_thresholds_fallbacks_or_exceptions",
        "next_possible_phase_is_phase10e_candidate_registry_construction_protocol_freeze",
        "next_phase_is_protocol_freeze_only_not_registry_construction_or_execution",
        "boundary_review_required_after_phase10d_commit_and_ci_green",
    ):
        if boundary.get(key) is not True:
            errors.append(f"phase10d_boundary missing: {key}")

    truth = report.get("truth_boundary", {})
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        if truth.get(key) is not True:
            errors.append(f"truth boundary failed: {key}")

    no_exec = report.get("no_execution_booleans", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_exec.get(key) is not False:
            errors.append(f"no_execution_booleans boundary failed: {key}")

    privacy = report.get("privacy_contract", {})
    for key in ("public_output_aggregate_only", "runs_remains_ignored"):
        if privacy.get(key) is not True:
            errors.append(f"privacy contract missing: {key}")
    for key in PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"privacy contract boundary failed: {key}")

    claims = report.get("claim_boundary", {})
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if claims.get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    validation = report.get("validation_summary", {})
    for key in ("phase10d_specific_validator_available", "self_test_available",
                "report_validation_available", "validator_does_not_fetch_or_read_private",
                "validator_does_not_read_sources", "validator_does_not_read_ignored_runs",
                "validator_does_not_read_phase9_artifacts",
                "validator_does_not_read_phase10c_artifacts",
                "validator_does_not_discover_sources",
                "validator_does_not_materialize_sources",
                "validator_does_not_generate_packets",
                "validator_does_not_construct_candidate_registry",
                "validator_does_not_score_adjudicate_or_evaluate",
                "public_artifact_privacy_audit_expected"):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_executes_tasks", "validator_reads_private_registry",
                "validator_reads_sources", "validator_reads_ignored_runs",
                "validator_starts_empirical_work", "validator_discovers_sources",
                "validator_materializes_sources", "validator_generates_packets",
                "validator_constructs_candidate_registry",
                "validator_scores_or_adjudicates"):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    if report.get("conservative_recommendation") != CONSERVATIVE_RECOMMENDATION:
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Self-test (synthetic fixtures only; no network/private/scoring)
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_DISCOVERY_ATTEMPTS, MATERIALIZATION_ATTEMPTS
    global PACKET_GENERATION_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS
    global SOURCE_MATERIAL_READ_ATTEMPTS, CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS
    global SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS, PROVIDER_OR_MODEL_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_DISCOVERY_ATTEMPTS = 0
    MATERIALIZATION_ATTEMPTS = 0
    PACKET_GENERATION_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_READ_ATTEMPTS = 0
    CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    # Baseline report validates.
    dry = build_public_report()
    checks.append(("report_valid", not validate_report(dry)))
    checks.append(("phase_equals_slug", dry["phase"] == PHASE))
    checks.append(("status_is_docs_only_closeout_no_claim", dry["status"] == STATUS))
    checks.append(("publication_level_boundary", dry["publication_level"] == PROTOCOL_PUBLICATION_LEVEL))

    # Gate facts enforced.
    checks.append(("phase9_closed_gate", dry["gate_facts"]["phase9_closed_commit"] == PHASE9_CLOSED_COMMIT))
    checks.append(("phase10a_commit_gate", dry["gate_facts"]["phase10a_commit"] == PHASE10A_COMMIT))
    checks.append(("phase10a_ci_gate", dry["gate_facts"]["phase10a_ci_run"] == PHASE10A_CI_RUN))
    checks.append(("phase10b_commit_gate", dry["gate_facts"]["phase10b_commit"] == PHASE10B_COMMIT))
    checks.append(("phase10b_ci_gate", dry["gate_facts"]["phase10b_ci_run"] == PHASE10B_CI_RUN))
    checks.append(("phase10c_research_commit_gate", dry["gate_facts"]["phase10c_research_commit"] == PHASE10C_RESEARCH_COMMIT))
    checks.append(("phase10c_status_gate", dry["gate_facts"]["phase10c_status"] == PHASE10C_STATUS))
    checks.append(("phase10c_accepted_bucket_zero", dry["gate_facts"]["phase10c_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10c_repair_bucket", dry["gate_facts"]["phase10c_repair_reason_bucket"] == "bucket_no_eligible_channel_registry"))
    checks.append(("hygiene_commit_gate", dry["gate_facts"]["hygiene_commit"] == HYGIENE_COMMIT))
    checks.append(("hygiene_ci_gate", dry["gate_facts"]["hygiene_ci_run"] == HYGIENE_CI_RUN))
    checks.append(("hygiene_ci_success", dry["gate_facts"]["hygiene_ci_success"] is True))
    checks.append(("hygiene_ci_infrastructure_only", dry["gate_facts"]["hygiene_is_ci_infrastructure_only_not_empirical_evidence"] is True))

    # 10C result summary enforces zero accepted / no validation evidence / no scoring.
    csum = dry["phase10c_result_summary"]
    checks.append(("phase10c_executed_frozen_route_once", csum["phase10c_executed_frozen_10b_route_once"] is True))
    checks.append(("phase10c_repair_no_claim", csum["phase10c_result_repair_no_claim"] is True))
    checks.append(("phase10c_zero_accepted", csum["phase10c_accepted_source_bucket_zero"] is True))
    checks.append(("phase10c_no_registry", csum["phase10c_no_compliant_candidate_source_registry_available"] is True))
    checks.append(("phase10c_no_validation_evidence", csum["phase10c_produced_no_validation_evidence"] is True))
    checks.append(("phase10c_no_scoring", csum["phase10c_did_not_score_adjudicate_or_run_correctness_evidence_success"] is True))
    checks.append(("phase10c_oracle_repaired_no_protocol_change", csum["phase10c_oracle_blockers_repaired_without_changing_frozen_10b_protocol"] is True))
    checks.append(("phase10c_zero_not_partial_success", csum["phase10c_zero_accepted_is_not_partial_success"] is True))

    # 10D boundary enforces docs-only / no registry / no execution / next phase 10E.
    boundary = dry["phase10d_boundary"]
    checks.append(("phase10d_no_execution", boundary["performs_no_execution"] is True))
    checks.append(("phase10d_no_new_claims", boundary["makes_no_new_evidence_claims"] is True))
    checks.append(("phase10d_no_registry_construction", boundary["does_not_construct_edit_select_filter_or_supply_candidate_registry"] is True))
    checks.append(("phase10d_no_fetch_clone_read", boundary["does_not_fetch_clone_or_read_source_material"] is True))
    checks.append(("phase10d_no_materialization_rerun", boundary["does_not_rerun_materialization"] is True))
    checks.append(("phase10d_no_protocol_change", boundary["does_not_change_frozen_phase10b_protocol"] is True))
    checks.append(("phase10d_no_scoring", boundary["does_not_score_adjudicate_or_run_correctness_evidence_success"] is True))
    checks.append(("phase10d_no_thresholds_fallbacks_exceptions", boundary["does_not_add_thresholds_fallbacks_or_exceptions"] is True))
    checks.append(("phase10d_next_phase_10e_freeze", boundary["next_possible_phase_is_phase10e_candidate_registry_construction_protocol_freeze"] is True))
    checks.append(("phase10d_next_phase_freeze_only", boundary["next_phase_is_protocol_freeze_only_not_registry_construction_or_execution"] is True))
    checks.append(("phase10d_boundary_review_required", boundary["boundary_review_required_after_phase10d_commit_and_ci_green"] is True))

    # Reject missing/wrong gate references.
    for field, bad_val, label in (
        ("phase10a_commit", "deadbeef", "phase10a_commit"),
        ("phase10a_ci_run", "0000", "phase10a_ci"),
        ("phase10b_commit", "deadbeef", "phase10b_commit"),
        ("phase10b_ci_run", "0000", "phase10b_ci"),
        ("phase10c_research_commit", "deadbeef", "phase10c_commit"),
        ("phase10c_status", "drift", "phase10c_status"),
        ("hygiene_commit", "deadbeef", "hygiene_commit"),
        ("hygiene_ci_run", "0000", "hygiene_ci"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["gate_facts"][field] = bad_val
        checks.append((f"wrong_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        del mutated["gate_facts"][field]
        checks.append((f"missing_{label}_rejected", bool(validate_report(mutated))))

    # Reject 10C result-summary facts flipped to false.
    for key in (
        "phase10c_executed_frozen_10b_route_once",
        "phase10c_result_repair_no_claim",
        "phase10c_accepted_source_bucket_zero",
        "phase10c_no_compliant_candidate_source_registry_available",
        "phase10c_produced_no_validation_evidence",
        "phase10c_did_not_score_adjudicate_or_run_correctness_evidence_success",
        "phase10c_oracle_blockers_repaired_without_changing_frozen_10b_protocol",
        "phase10c_zero_accepted_is_not_partial_success",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10c_result_summary"][key] = False
        checks.append((f"phase10c_summary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject converting 10C zero accepted into nonzero/partial success.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["phase10c_accepted_source_bucket"] = "bucket_nonzero_below_minimum"
    checks.append(("phase10c_nonzero_accepted_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10c_result_summary"]["phase10c_zero_accepted_is_not_partial_success"] = False
    checks.append(("phase10c_partial_success_claim_rejected", bool(validate_report(mutated))))

    # Reject 10D boundary facts flipped to false.
    for key in (
        "performs_no_execution",
        "makes_no_new_evidence_claims",
        "does_not_construct_edit_select_filter_or_supply_candidate_registry",
        "does_not_fetch_clone_or_read_source_material",
        "does_not_rerun_materialization",
        "does_not_change_frozen_phase10b_protocol",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_add_thresholds_fallbacks_or_exceptions",
        "next_possible_phase_is_phase10e_candidate_registry_construction_protocol_freeze",
        "next_phase_is_protocol_freeze_only_not_registry_construction_or_execution",
        "boundary_review_required_after_phase10d_commit_and_ci_green",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10d_boundary"][key] = False
        checks.append((f"phase10d_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema/publication_level drift.
    for field, bad in (("status", "drift"), ("phase", "drift"),
                       ("schema_version", "drift"),
                       ("publication_level", "drift")):
        mutated = copy.deepcopy(dry)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # Reject execution booleans true (forbidden in Phase 10D).
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["phase10d_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject truth-boundary violation.
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["truth_boundary"][key] = False
        checks.append((f"truth_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject claim boundary true.
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject privacy contract violations.
    for privacy_key in PRIVACY_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # Reject private-shaped values.
    for label, bad_val in (
        ("url", "https://example.invalid/repo.git"),
        ("owner_repo", "owner/repo"),
        ("full_hash", "a" * 40),
        ("path", "src/private.py"),
        ("task_id", "task_id_7"),
        ("run_dir", "runs/secret/run_dir"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10d_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "source_path_bucket", "path", "repo_name", "task_id", "row_id",
        "packet_id", "manifest", "run_dir", "candidate_identity",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10d_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(dry)
        mutated["phase10d_scope"]["example_bucket"] = singleton_val
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # Reject forbidden success wording (must NOT appear anywhere).
    for phrase in ("validated", "evidence_success achieved", "correctness evidence",
                   "materialization succeeded", "independent validation passed",
                   "OpenLocus works", "Phase 10 confirms", "Phase 10C confirms",
                   "method proven", "product readiness", "scoring success",
                   "outcome success", "evaluation works", "acquisition success",
                   "adjudication proven", "correctness proven", "lift achieved",
                   "generalized success", "evidence-acquisition success", "validation proven"):
        mutated = copy.deepcopy(dry)
        mutated["phase10d_scope"]["example_note"] = phrase
        checks.append((f"forbidden_success_wording_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # Reject user-approval wording.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    # Reject placeholder wording.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(dry)
        mutated["phase10d_scope"]["example_note"] = phrase
        checks.append((f"placeholder_{phrase}_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Reject unknown fields.
    mutated = copy.deepcopy(dry)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10d_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_gate_rejected", bool(validate_report(mutated))))

    # Reject non-gate hash/CI values (gate values only allowed at exact paths).
    mutated = copy.deepcopy(dry)
    mutated["phase10d_scope"]["task_ci_run"] = "29004189917"
    checks.append(("non_whitelisted_ci_run_value_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10d_scope"]["example_hash"] = "19abcdd8f09e190c323a28fab8e3e0401d504236"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))
    checks.append(("gate_ref_values_on_whitelisted_paths_valid", not validate_report(dry)))

    # Reject hygiene facts that imply hygiene is empirical evidence.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["hygiene_is_ci_infrastructure_only_not_empirical_evidence"] = False
    checks.append(("hygiene_as_evidence_rejected", bool(validate_report(mutated))))

    # Path guard tests.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10d" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10c" / "report.json")
    checks.append(("validate_report_rejects_runs_phase10c_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10c_input_construction_execution_no_scoring_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10d" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Temp-file round-trip (synthetic fixture only; no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10d_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(dry), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))
        runs_tmp = Path(tmp) / "runs" / "report.json"
        runs_tmp.parent.mkdir(parents=True, exist_ok=True)
        runs_tmp.write_text(json.dumps(dry), encoding="utf-8")
        ok, _ = _validate_report_path_is_public(runs_tmp)
        checks.append(("validate_report_rejects_temp_runs_path", not ok))

    # Prove the self-test did not fetch/read/private/execute/score/construct.
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_discover_sources", SOURCE_DISCOVERY_ATTEMPTS == 0))
    checks.append(("selftest_does_not_materialize", MATERIALIZATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_packets", PACKET_GENERATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9_artifacts", PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10c_artifacts", PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_material", SOURCE_MATERIAL_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_construct_candidate_registry", CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_score_adjudicate_or_execute", SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_call_provider_or_model", PROVIDER_OR_MODEL_CALL_ATTEMPTS == 0))

    failed = [name for name, ok_flag in checks if not ok_flag]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 10D 10C repair closeout guard (docs/report/validator-only, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true",
                        help="write the docs-only closeout guard report (no private output, no fetch)")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
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
