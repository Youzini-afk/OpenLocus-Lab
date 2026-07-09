#!/usr/bin/env python3
"""Phase 10C input-construction execution (no scoring, no claim).

This is the EXECUTION checkpoint for the NEW independent Phase 10 validation
line.  Phase 10C is allowed to execute ONLY input construction/materialization
under the frozen Phase 10B rules (commit ``19abcdd8f09e190c323a28fab8e3e0401d504236``,
CI run ``29004189917`` success, status
``phase10b_fresh_fenced_input_construction_protocol_freeze
_no_execution_no_materialization_no_claim``).  The frozen Phase 10B protocol
closed lists and caps are imported directly from the committed Phase 10B
protocol-freeze module so Phase 10C applies EXACTLY the frozen protocol (no
re-declaration, no vocabulary drift, no cap/eligibility/ordering edits after
observation).

Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation,
repair, rerun, rescore, or strengthening of Phase 9R/9S.  Phase 9 is closed.
Phase 10C does NOT read Phase 9 private artifacts, labels, outcomes, source
filters, priors, or sampling inputs as evidence/filter/labels/source prior, and
the clean-room operator does not use memory of Phase 9 private material.

ALLOWED in Phase 10C (under explicit confirmation flags only):
  * public-source discovery from eligible public metadata/channels only;
  * fetch/clone/materialize public sources into ignored ``runs/`` only;
  * apply the frozen Phase 10B source eligibility before use;
  * enforce freshness/fencing before packet generation (no Phase 9 inputs);
  * deterministic ordering/selection only (no randomness, stable channel order,
    predeclared sort keys, replacement only for availability/eligibility before
    packet construction);
  * respect frozen structural caps (candidate inspection cap total 48, per-channel
    cap 16, accepted source target cap 12, accepted source minimum cap 8);
  * generate independent replication/input packets under ignored ``runs/``;
  * generate private registries/manifests/materialization records/packets under
    ignored ``runs/``;
  * publish only aggregate/bucket-only public report and boundary docs.

FORBIDDEN in Phase 10C:
  * no Phase 9 private artifacts/labels/outcomes/source filters/priors/sampling
    inputs as evidence/filter/labels/source prior;
  * no changing the Phase 10B protocol after seeing discovery/materialization
    results;
  * no scoring, adjudication, correctness evaluation, evidence_success
    evaluation, pass/fail, precision/recall, outcome metrics, or gold labels;
  * no provider/LLM/model calls;
  * no runtime/default/product changes;
  * no model fitting/training;
  * no product/method/performance/correctness/evidence-success/generalization/
    validation claims;
  * no public source-specific disclosure (repo names, URLs, owners, commits,
    paths, snippets, line ranges, packet IDs, run dirs, per-source/per-task facts,
    singleton buckets).

Stop/repair conditions: fewer than the frozen minimum eligible accepted sources
after deterministic inspection/caps => produce a repair/no-claim checkpoint, do
NOT tune/pad.  Any need to alter eligibility/order/caps/replacement/packet
schema/privacy rules => stop/repair.  Any Phase 9 contamination/suspected
reliance => stop/repair.  Network/auth/private-host/redirect/license/default-
branch/currentness ambiguity unresolved under frozen rules => skip or stop per
protocol; do not change rules.

The dry self-test and report validation do NOT fetch/clone, read ignored
``runs/``, read private/source artifacts, score, adjudicate, or make any
provider/LLM/model call.  Execution (network fetch/materialization) is behind
explicit confirmation flags only.  Phase 10C makes NO evidence/method/product/
correctness/validation/evidence-success claim.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Import the frozen Phase 10B protocol constants directly from the committed
# protocol-freeze module so Phase 10C applies EXACTLY the frozen protocol
# (no re-declaration, no vocabulary/cap/ordering drift).  The import itself
# performs no execution, no fetch, no private read; it only loads constants.
try:  # namespace-package form (repo root on sys.path)
    from eval.interventional_evidence_acquisition_phase10b_input_protocol_freeze import (  # noqa: E402
        SOURCE_ELIGIBILITY_RULES,
        FRESHNESS_FENCING_RULES,
        INDEPENDENCE_FROM_PHASE9_RULES,
        DETERMINISTIC_ORDERING_SELECTION_RULES,
        CHANNEL_ORDER,
        DETERMINISTIC_SORT_KEYS,
        CAPS_AND_ABORT_LIMITS_RULES,
        FROZEN_CAPS,
        FROZEN_ABORT_LIMITS,
        PRIVATE_PUBLIC_ARTIFACT_SPLIT_RULES,
        REPLICATION_PACKET_SCHEMA_RULES,
        PRIVACY_SCANNER_RULES,
    )
except Exception:  # pragma: no cover - direct-module form (eval/ on sys.path)
    from interventional_evidence_acquisition_phase10b_input_protocol_freeze import (  # type: ignore[no-redef]  # noqa: E402
        SOURCE_ELIGIBILITY_RULES,
        FRESHNESS_FENCING_RULES,
        INDEPENDENCE_FROM_PHASE9_RULES,
        DETERMINISTIC_ORDERING_SELECTION_RULES,
        CHANNEL_ORDER,
        DETERMINISTIC_SORT_KEYS,
        CAPS_AND_ABORT_LIMITS_RULES,
        FROZEN_CAPS,
        FROZEN_ABORT_LIMITS,
        PRIVATE_PUBLIC_ARTIFACT_SPLIT_RULES,
        REPLICATION_PACKET_SCHEMA_RULES,
        PRIVACY_SCANNER_RULES,
    )


PHASE = "phase10c_input_construction_execution_no_scoring_no_claim"
SCHEMA_VERSION = (
    "phase10c_input_construction_execution_no_scoring_no_claim_report_v1"
)
STATUS_EXECUTED = "phase10c_input_construction_executed_no_scoring_no_claim"
STATUS_REPAIR = "phase10c_input_construction_repair_no_claim"
VALID_STATUSES = (STATUS_EXECUTED, STATUS_REPAIR)

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)
DEFAULT_PRIVATE_RUN_DIR = (
    REPO / "runs" / "phase10c_input_construction_execution"
)

# Frozen gate references (the only exact public gate references published by
# Phase 10C).  Phase 10A and Phase 9 closure are carried as inherited
# bucket/status only; older Phase 9 exact commit/CI refs are intentionally NOT
# republished by Phase 10C (tighter privacy).  Local same-tree git commits are
# not read or compared; supplied confirmation values are matched against the
# frozen public gate constants only.
PHASE10B_COMMIT = "19abcdd8f09e190c323a28fab8e3e0401d504236"
PHASE10B_CI_RUN = "29004189917"
PHASE10B_STATUS = (
    "phase10b_fresh_fenced_input_construction_protocol_freeze"
    "_no_execution_no_materialization_no_claim"
)

# Frozen structural caps (imported from Phase 10B; mirrored here only as a
# closed-schema convenience label, NOT redeclared -- the validator set-equality
# checks the imported tuple against the report).
CANDIDATE_INSPECTION_CAP_TOTAL = int(FROZEN_CAPS["candidate_inspection_cap_total"])
CANDIDATE_INSPECTION_CAP_PER_CHANNEL = int(FROZEN_CAPS["candidate_inspection_cap_per_channel"])
ACCEPTED_SOURCE_TARGET_CAP = int(FROZEN_CAPS["accepted_source_target_cap"])
ACCEPTED_SOURCE_MINIMUM_CAP = int(FROZEN_CAPS["accepted_source_minimum_cap"])

PROTOCOL_PUBLICATION_LEVEL = "aggregate_input_construction_execution_boundary_only"

# Truth-boundary attestation keys that must always be True.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_inherited",
    "phase10a_gate_inherited",
    "phase10b_gate_passed_at_recorded_commit_and_ci",
    "phase10c_applies_frozen_phase10b_protocol_exactly_no_drift",
    "phase10c_is_separate_from_phase9_not_continuation",
    "phase10c_does_not_reuse_phase9_artifacts_as_evidence",
    "phase10c_makes_no_scoring_adjudication_correctness_evidence_success_claim",
    "phase10c_does_not_make_provider_llm_model_runtime_default_product_claims",
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
    "validation_claim",
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
    "source_urls_public",
    "candidate_repo_names_public",
)

FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

# Closed protocol lists whose members are validator set-equality checked against
# the imported frozen Phase 10B tuples (proves no drift).  Each entry is
# (report_section, list_key, expected_tuple, label).
CLOSED_PROTOCOL_LISTS = (
    ("frozen_source_eligibility", "source_eligibility_rules", SOURCE_ELIGIBILITY_RULES, "source_eligibility"),
    ("frozen_freshness_fencing", "freshness_fencing_rules", FRESHNESS_FENCING_RULES, "freshness_fencing"),
    ("frozen_independence_from_phase9", "independence_from_phase9_rules", INDEPENDENCE_FROM_PHASE9_RULES, "independence_from_phase9"),
    ("frozen_deterministic_ordering_selection", "deterministic_ordering_selection_rules", DETERMINISTIC_ORDERING_SELECTION_RULES, "deterministic_ordering_selection"),
    ("frozen_deterministic_ordering_selection", "channel_order", CHANNEL_ORDER, "channel_order"),
    ("frozen_deterministic_ordering_selection", "deterministic_sort_keys", DETERMINISTIC_SORT_KEYS, "deterministic_sort_keys"),
    ("frozen_caps_and_abort_limits", "caps_and_abort_limits_rules", CAPS_AND_ABORT_LIMITS_RULES, "caps_and_abort_limits_rules"),
    ("frozen_caps_and_abort_limits", "abort_limits", FROZEN_ABORT_LIMITS, "abort_limits"),
    ("frozen_private_public_artifact_split", "private_public_artifact_split_rules", PRIVATE_PUBLIC_ARTIFACT_SPLIT_RULES, "private_public_artifact_split"),
    ("frozen_replication_packet_schema", "replication_packet_schema_rules", REPLICATION_PACKET_SCHEMA_RULES, "replication_packet_schema"),
    ("frozen_privacy_scanner", "privacy_scanner_rules", PRIVACY_SCANNER_RULES, "privacy_scanner"),
)

# ---------------------------------------------------------------------------
# Privacy scan regexes (mirror Phase 10B scanner, with Phase 10C gate paths)
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
    r"|candidate_identity|commit|commit_sha|ci_run|sha|hash"
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
# public gate constants (Phase 10B commit / CI run).  These are the only
# exact public gate references published by Phase 10C.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase10b_gate.phase10b_commit",
        "$.phase10b_gate.phase10b_ci_run",
    }
)
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase10b_gate.phase10b_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read/
# execute/score.  Execution increments these ONLY under explicit confirmation
# flags; the self-test and report validation never do.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_DISCOVERY_ATTEMPTS = 0
MATERIALIZATION_ATTEMPTS = 0
PACKET_GENERATION_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0


CONSERVATIVE_RECOMMENDATION = (
    "phase10c_input_construction_execution_only_under_frozen_phase10b_protocol"
    "_phase9_closed_inherited_phase10a_gate_inherited"
    "_phase10b_gate_passed_at_recorded_commit_and_ci"
    "_phase10c_applies_frozen_phase10b_protocol_exactly_no_drift"
    "_phase10c_is_separate_from_phase9_not_continuation"
    "_phase10c_does_not_reuse_phase9_artifacts_as_evidence"
    "_source_eligibility_freshness_fencing_independence_from_phase9_frozen"
    "_deterministic_ordering_selection_no_randomness_stable_channel_order"
    "_caps_frozen_as_structural_protocol_limits_not_success_metrics"
    "_private_material_and_packets_under_ignored_runs_only"
    "_public_output_aggregate_bucket_only_no_source_specific_disclosure"
    "_no_scoring_adjudication_correctness_evidence_success_provider_model"
    "_no_runtime_default_product_method_performance_correctness_claim"
    "_repair_no_claim_below_frozen_minimum_no_tuning_no_padding"
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
    """Fail-closed: private output must stay under the ignored runs/ root."""
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if resolved != runs_root and runs_root not in resolved.parents:
        raise ValueError("private output must stay under ignored runs/")
    if not _runs_is_ignored():
        raise ValueError("runs/ must remain ignored before private output is allowed")
    return resolved


def _is_gate_reference_value_path(path: str) -> bool:
    return path in GATE_REF_EXEMPT_PATHS


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--validate-report``.

    The report path must be under the Phase 10C public artifact directory
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
        return False, "report path is not under the Phase 10C public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Bucket helpers (aggregate/bucket-only; no exact counts)
# ---------------------------------------------------------------------------

def _bucket_accepted_sources(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < ACCEPTED_SOURCE_MINIMUM_CAP:
        return "bucket_nonzero_below_minimum"
    if value < ACCEPTED_SOURCE_TARGET_CAP:
        return "bucket_at_least_minimum_below_target"
    return "bucket_target_met_or_above"


def _bucket_quantity(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < ACCEPTED_SOURCE_MINIMUM_CAP:
        return "bucket_nonzero_below_minimum"
    if value < ACCEPTED_SOURCE_TARGET_CAP:
        return "bucket_at_least_minimum_below_target"
    return "bucket_target_met_or_above"


def _bucket_repair_reason(reason: str) -> str:
    if not reason:
        return "bucket_none"
    if reason == "no_eligible_channel_registry":
        return "bucket_no_eligible_channel_registry"
    if reason == "below_minimum_after_caps":
        return "bucket_below_minimum_after_caps"
    if reason == "network_auth_or_redirect_ambiguity":
        return "bucket_network_auth_redirect_ambiguity"
    if reason == "license_or_default_branch_ambiguity":
        return "bucket_license_or_default_branch_ambiguity"
    if reason == "phase9_contamination_suspected":
        return "bucket_phase9_contamination_suspected"
    if reason == "not_executed":
        return "bucket_not_executed"
    if reason == "confirmations_missing":
        return "bucket_confirmations_missing"
    return "bucket_other_repair_no_claim"


# ---------------------------------------------------------------------------
# Strict allowed-key schema for the public report
# ---------------------------------------------------------------------------

ALLOWED_REPORT_KEYS: dict[str, Any] = {
    "schema_version": None,
    "phase": None,
    "status": None,
    "phase10b_gate": {
        "phase10b_commit": None,
        "phase10b_ci_run": None,
        "phase10b_ci_success": None,
        "phase10b_status": None,
        "phase10b_gate_required_before_phase10c": None,
        "phase10b_protocol_freeze_only": None,
    },
    "inherited_gates": {
        "phase10a_gate_inherited": None,
        "phase9_closure_inherited": None,
        "older_phase9_exact_refs_not_republished_by_phase10c": None,
    },
    "phase10c_scope": {
        "input_construction_execution_only": None,
        "separate_from_phase9_not_continuation": None,
        "frozen_phase10b_protocol_applied_exactly": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "frozen_source_eligibility": {
        "source_eligibility_rules": None,
        "source_eligibility_decided_before_any_use": None,
        "source_eligibility_drift_is_hard_stop": None,
    },
    "frozen_freshness_fencing": {
        "freshness_fencing_rules": None,
        "freshness_verified_before_packet_generation": None,
        "fencing_violation_is_hard_stop": None,
    },
    "frozen_independence_from_phase9": {
        "independence_from_phase9_rules": None,
        "phase9_artifacts_cannot_be_used_as_validation_evidence": None,
        "clean_room_operator_must_not_use_memory_of_phase9_private_material": None,
    },
    "frozen_deterministic_ordering_selection": {
        "deterministic_ordering_selection_rules": None,
        "channel_order": None,
        "deterministic_sort_keys": None,
        "predeclared_seed_label": None,
        "seed_semantics": None,
        "randomness_policy": None,
    },
    "frozen_caps_and_abort_limits": {
        "caps_and_abort_limits_rules": None,
        "caps": {
            "candidate_inspection_cap_total": None,
            "accepted_source_target_cap": None,
            "accepted_source_minimum_cap": None,
            "candidate_inspection_cap_per_channel": None,
        },
        "abort_limits": None,
        "caps_are_structural_protocol_limits_not_success_metrics": None,
    },
    "frozen_private_public_artifact_split": {
        "private_public_artifact_split_rules": None,
        "public_output_aggregate_or_boundary_only": None,
        "private_material_under_ignored_runs_only": None,
        "no_singleton_buckets": None,
    },
    "frozen_replication_packet_schema": {
        "replication_packet_schema_rules": None,
        "packet_schema_independently_generated_in_phase10c": None,
    },
    "frozen_privacy_scanner": {
        "privacy_scanner_rules": None,
        "gate_exact_values_allowed_only_at_exact_gate_paths": None,
        "reject_exact_count_fields": True and None,
    },
    "execution_summary": {
        "publication_level": None,
        "source_discovery_executed": None,
        "fetch_clone_materialization_executed": None,
        "packet_generation_executed": None,
        "discovery_bucket": None,
        "materialization_bucket": None,
        "accepted_source_bucket": None,
        "packet_generation_bucket": None,
        "caps_respected": None,
        "deterministic_ordering_applied": None,
        "replacement_before_packet_generation_only": None,
        "no_randomness": None,
        "repair_reason_bucket": None,
    },
    "confirmation_summary": {
        "phase10b_commit_confirmed": None,
        "phase10b_ci_confirmed": None,
        "phase10b_status_confirmed": None,
        "phase10b_protocol_freeze_confirmed": None,
        "public_source_fetch_confirmed": None,
        "private_output_confirmed": None,
        "ignored_runs_workspace_confirmed": None,
        "aggregate_public_report_only_confirmed": None,
        "no_scoring_adjudication_correctness_evidence_success_confirmed": None,
        "no_provider_llm_model_runtime_default_product_confirmed": None,
        "no_phase9_artifacts_as_evidence_confirmed": None,
        "frozen_phase10b_protocol_applied_exactly_confirmed": None,
        "all_required_confirmations_present": None,
        "dry_self_test_and_report_validation_read_private_runs": None,
        "dry_self_test_and_report_validation_fetch_or_clone": None,
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
        "phase10c_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_generate_packets": None,
        "validator_does_not_score_adjudicate_or_evaluate": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_generates_packets": None,
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


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report(
    aggregate: dict[str, Any] | None = None,
    confirmations: dict[str, bool] | None = None,
    repair_reason: str = "",
    executed: bool = False,
) -> dict[str, Any]:
    """Build the frozen Phase 10C aggregate/bucket-only public report.

    This performs no network/filesystem fetch and no private reads.  It
    assembles the report from the frozen protocol constants and the supplied
    aggregate bucket inputs.  No exact source counts are published; only
    buckets and structural caps.
    """
    agg = aggregate or {}
    confirmations = confirmations or {}
    all_confirmations = all(confirmations.values()) and len(confirmations) == len(CONFIRMATION_KEYS)

    discovered = int(agg.get("discovered_candidates", 0))
    materialized = int(agg.get("materialized_sources", 0))
    accepted = int(agg.get("accepted_sources", 0))
    packets = int(agg.get("packets_generated", 0))

    caps_respected = bool(agg.get("caps_respected", True))
    deterministic = bool(agg.get("deterministic_ordering_applied", True))

    source_discovery_executed = bool(executed and agg.get("discovery_attempted", False))
    fetch_clone_executed = bool(
        executed and agg.get("materialization_attempted", False) and discovered > 0
    )
    packet_generation_executed = bool(
        executed and agg.get("packet_generation_attempted", False) and accepted >= ACCEPTED_SOURCE_MINIMUM_CAP
    )

    # Honest status: executed (no scoring/no claim) only when the frozen
    # minimum eligible accepted sources is met; otherwise repair/no-claim.
    if executed and all_confirmations and caps_respected and deterministic:
        if accepted >= ACCEPTED_SOURCE_MINIMUM_CAP and accepted > 0:
            status = STATUS_EXECUTED
        else:
            status = STATUS_REPAIR
            if not repair_reason:
                repair_reason = "below_minimum_after_caps"
    else:
        status = STATUS_REPAIR
        if not repair_reason:
            repair_reason = "not_executed" if not executed else "confirmations_missing"

    discovery_bucket = _bucket_quantity(discovered)
    materialization_bucket = _bucket_quantity(materialized)
    accepted_bucket = _bucket_accepted_sources(accepted)
    packet_bucket = _bucket_quantity(packets)

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase10b_gate": {
            "phase10b_commit": PHASE10B_COMMIT,
            "phase10b_ci_run": PHASE10B_CI_RUN,
            "phase10b_ci_success": True,
            "phase10b_status": PHASE10B_STATUS,
            "phase10b_gate_required_before_phase10c": True,
            "phase10b_protocol_freeze_only": True,
        },
        "inherited_gates": {
            "phase10a_gate_inherited": True,
            "phase9_closure_inherited": True,
            "older_phase9_exact_refs_not_republished_by_phase10c": True,
        },
        "phase10c_scope": {
            "input_construction_execution_only": True,
            "separate_from_phase9_not_continuation": True,
            "frozen_phase10b_protocol_applied_exactly": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "frozen_source_eligibility": {
            "source_eligibility_rules": list(SOURCE_ELIGIBILITY_RULES),
            "source_eligibility_decided_before_any_use": True,
            "source_eligibility_drift_is_hard_stop": True,
        },
        "frozen_freshness_fencing": {
            "freshness_fencing_rules": list(FRESHNESS_FENCING_RULES),
            "freshness_verified_before_packet_generation": True,
            "fencing_violation_is_hard_stop": True,
        },
        "frozen_independence_from_phase9": {
            "independence_from_phase9_rules": list(INDEPENDENCE_FROM_PHASE9_RULES),
            "phase9_artifacts_cannot_be_used_as_validation_evidence": True,
            "clean_room_operator_must_not_use_memory_of_phase9_private_material": True,
        },
        "frozen_deterministic_ordering_selection": {
            "deterministic_ordering_selection_rules": list(DETERMINISTIC_ORDERING_SELECTION_RULES),
            "channel_order": list(CHANNEL_ORDER),
            "deterministic_sort_keys": list(DETERMINISTIC_SORT_KEYS),
            "predeclared_seed_label": "phase10b_fresh_fenced_public_seed_v1",
            "seed_semantics": "version_label_only_randomness_forbidden",
            "randomness_policy": "forbidden_no_random_shuffle_no_posthoc_resampling",
        },
        "frozen_caps_and_abort_limits": {
            "caps_and_abort_limits_rules": list(CAPS_AND_ABORT_LIMITS_RULES),
            "caps": dict(FROZEN_CAPS),
            "abort_limits": list(FROZEN_ABORT_LIMITS),
            "caps_are_structural_protocol_limits_not_success_metrics": True,
        },
        "frozen_private_public_artifact_split": {
            "private_public_artifact_split_rules": list(PRIVATE_PUBLIC_ARTIFACT_SPLIT_RULES),
            "public_output_aggregate_or_boundary_only": True,
            "private_material_under_ignored_runs_only": True,
            "no_singleton_buckets": True,
        },
        "frozen_replication_packet_schema": {
            "replication_packet_schema_rules": list(REPLICATION_PACKET_SCHEMA_RULES),
            "packet_schema_independently_generated_in_phase10c": True,
        },
        "frozen_privacy_scanner": {
            "privacy_scanner_rules": list(PRIVACY_SCANNER_RULES),
            "gate_exact_values_allowed_only_at_exact_gate_paths": True,
            "reject_exact_count_fields": True,
        },
        "execution_summary": {
            "publication_level": PROTOCOL_PUBLICATION_LEVEL,
            "source_discovery_executed": source_discovery_executed,
            "fetch_clone_materialization_executed": fetch_clone_executed,
            "packet_generation_executed": packet_generation_executed,
            "discovery_bucket": discovery_bucket,
            "materialization_bucket": materialization_bucket,
            "accepted_source_bucket": accepted_bucket,
            "packet_generation_bucket": packet_bucket,
            "caps_respected": caps_respected,
            "deterministic_ordering_applied": deterministic,
            "replacement_before_packet_generation_only": True,
            "no_randomness": True,
            "repair_reason_bucket": _bucket_repair_reason(repair_reason),
        },
        "confirmation_summary": {
            "phase10b_commit_confirmed": confirmations.get("phase10b_commit_confirmed") is True,
            "phase10b_ci_confirmed": confirmations.get("phase10b_ci_confirmed") is True,
            "phase10b_status_confirmed": confirmations.get("phase10b_status_confirmed") is True,
            "phase10b_protocol_freeze_confirmed": confirmations.get("phase10b_protocol_freeze_confirmed") is True,
            "public_source_fetch_confirmed": confirmations.get("public_source_fetch_confirmed") is True,
            "private_output_confirmed": confirmations.get("private_output_confirmed") is True,
            "ignored_runs_workspace_confirmed": confirmations.get("ignored_runs_workspace_confirmed") is True,
            "aggregate_public_report_only_confirmed": confirmations.get("aggregate_public_report_only_confirmed") is True,
            "no_scoring_adjudication_correctness_evidence_success_confirmed": confirmations.get("no_scoring_adjudication_correctness_evidence_success_confirmed") is True,
            "no_provider_llm_model_runtime_default_product_confirmed": confirmations.get("no_provider_llm_model_runtime_default_product_confirmed") is True,
            "no_phase9_artifacts_as_evidence_confirmed": confirmations.get("no_phase9_artifacts_as_evidence_confirmed") is True,
            "frozen_phase10b_protocol_applied_exactly_confirmed": confirmations.get("frozen_phase10b_protocol_applied_exactly_confirmed") is True,
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
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
            "phase10c_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_generate_packets": True,
            "validator_does_not_score_adjudicate_or_evaluate": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_generates_packets": False,
            "validator_scores_or_adjudicates": False,
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
    """Validate the Phase 10C public report against the frozen schema/constants.

    This does NOT read any Phase 9/10A/10B artifact on disk, does NOT fetch/
    clone, and does NOT read ignored ``runs/``.  It checks the report's gate
    references against the frozen public gate constants directly and the
    imported Phase 10B protocol closed lists via set-equality (proves no drift).
    """
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") not in VALID_STATUSES:
        errors.append("status drift")

    # Status/bucket consistency per frozen protocol: the executed status
    # requires a minimum-source (nonzero) accepted bucket with packet
    # generation and fetch/clone materialization executed and no repair
    # reason; repair status is required for bucket_zero, below-minimum,
    # a repair reason, or no packet generation.
    exec_summary = report.get("execution_summary", {})
    if isinstance(exec_summary, dict):
        _status = report.get("status")
        _accepted_bucket = exec_summary.get("accepted_source_bucket")
        _fetch_executed = exec_summary.get("fetch_clone_materialization_executed")
        _packet_executed = exec_summary.get("packet_generation_executed")
        _repair_bucket = exec_summary.get("repair_reason_bucket")
        if _status == STATUS_EXECUTED:
            if _accepted_bucket in ("bucket_zero", "bucket_nonzero_below_minimum"):
                errors.append(
                    "executed status requires minimum-source accepted bucket "
                    "(bucket_zero/below_minimum inconsistent with executed)"
                )
            if _packet_executed is not True:
                errors.append("executed status requires packet_generation_executed")
            if _fetch_executed is not True:
                errors.append("executed status requires fetch_clone_materialization_executed")
            if _repair_bucket != "bucket_none":
                errors.append("executed status requires no repair reason bucket")

    gate = report.get("phase10b_gate", {})
    if gate.get("phase10b_commit") != PHASE10B_COMMIT:
        errors.append("Phase 10B commit gate reference drift")
    if gate.get("phase10b_ci_run") != PHASE10B_CI_RUN:
        errors.append("Phase 10B CI run gate reference drift")
    if gate.get("phase10b_ci_success") is not True:
        errors.append("Phase 10B CI success gate missing")
    if gate.get("phase10b_status") != PHASE10B_STATUS:
        errors.append("Phase 10B status gate reference drift")
    for key in ("phase10b_gate_required_before_phase10c", "phase10b_protocol_freeze_only"):
        if gate.get(key) is not True:
            errors.append(f"Phase 10B gate boundary missing: {key}")

    inh = report.get("inherited_gates", {})
    for key in ("phase10a_gate_inherited", "phase9_closure_inherited",
                "older_phase9_exact_refs_not_republished_by_phase10c"):
        if inh.get(key) is not True:
            errors.append(f"inherited gates boundary missing: {key}")

    scope = report.get("phase10c_scope", {})
    for key in ("input_construction_execution_only",
                "separate_from_phase9_not_continuation",
                "frozen_phase10b_protocol_applied_exactly"):
        if scope.get(key) is not True:
            errors.append(f"phase10c_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10c_scope execution boundary failed: {key}")

    se = report.get("frozen_source_eligibility", {})
    for key in ("source_eligibility_decided_before_any_use",
                "source_eligibility_drift_is_hard_stop"):
        if se.get(key) is not True:
            errors.append(f"frozen source eligibility boundary missing: {key}")

    ff = report.get("frozen_freshness_fencing", {})
    for key in ("freshness_verified_before_packet_generation",
                "fencing_violation_is_hard_stop"):
        if ff.get(key) is not True:
            errors.append(f"frozen freshness fencing boundary missing: {key}")

    ind = report.get("frozen_independence_from_phase9", {})
    for key in ("phase9_artifacts_cannot_be_used_as_validation_evidence",
                "clean_room_operator_must_not_use_memory_of_phase9_private_material"):
        if ind.get(key) is not True:
            errors.append(f"frozen independence from phase9 boundary missing: {key}")

    dos = report.get("frozen_deterministic_ordering_selection", {})
    if dos.get("predeclared_seed_label") != "phase10b_fresh_fenced_public_seed_v1":
        errors.append("seed label drift")
    if dos.get("seed_semantics") != "version_label_only_randomness_forbidden":
        errors.append("seed semantics drift")
    if dos.get("randomness_policy") != "forbidden_no_random_shuffle_no_posthoc_resampling":
        errors.append("randomness policy drift")
    if dos.get("channel_order") != list(CHANNEL_ORDER):
        errors.append("channel order drift")
    if dos.get("deterministic_sort_keys") != list(DETERMINISTIC_SORT_KEYS):
        errors.append("deterministic sort keys order drift")

    caps = report.get("frozen_caps_and_abort_limits", {})
    if caps.get("caps") != dict(FROZEN_CAPS):
        errors.append("frozen caps drift")
    if caps.get("caps_are_structural_protocol_limits_not_success_metrics") is not True:
        errors.append("caps structural boundary missing")

    pps = report.get("frozen_private_public_artifact_split", {})
    for key in ("public_output_aggregate_or_boundary_only",
                "private_material_under_ignored_runs_only", "no_singleton_buckets"):
        if pps.get(key) is not True:
            errors.append(f"frozen private public artifact split boundary missing: {key}")

    rps = report.get("frozen_replication_packet_schema", {})
    if rps.get("packet_schema_independently_generated_in_phase10c") is not True:
        errors.append("frozen replication packet schema boundary missing")

    ps = report.get("frozen_privacy_scanner", {})
    for key in ("gate_exact_values_allowed_only_at_exact_gate_paths",
                "reject_exact_count_fields"):
        if ps.get(key) is not True:
            errors.append(f"frozen privacy scanner boundary missing: {key}")

    for _s, key, expected, _l in CLOSED_PROTOCOL_LISTS:
        errors.extend(_check_closed_list(report.get(_s, {}).get(key), expected, _s, key))

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
    for key in ("phase10c_specific_validator_available", "self_test_available",
                "report_validation_available", "validator_does_not_fetch_or_read_private",
                "validator_does_not_read_sources", "validator_does_not_read_ignored_runs",
                "validator_does_not_read_phase9_artifacts",
                "validator_does_not_discover_sources",
                "validator_does_not_materialize_sources",
                "validator_does_not_generate_packets",
                "validator_does_not_score_adjudicate_or_evaluate",
                "public_artifact_privacy_audit_expected"):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_executes_tasks", "validator_reads_private_registry",
                "validator_reads_sources", "validator_reads_ignored_runs",
                "validator_starts_empirical_work", "validator_discovers_sources",
                "validator_materializes_sources", "validator_generates_packets",
                "validator_scores_or_adjudicates"):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    if report.get("conservative_recommendation") != CONSERVATIVE_RECOMMENDATION:
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Confirmation keys (used by CLI + self-test)
# ---------------------------------------------------------------------------

CONFIRMATION_KEYS = (
    "phase10b_commit_confirmed",
    "phase10b_ci_confirmed",
    "phase10b_status_confirmed",
    "phase10b_protocol_freeze_confirmed",
    "public_source_fetch_confirmed",
    "private_output_confirmed",
    "ignored_runs_workspace_confirmed",
    "aggregate_public_report_only_confirmed",
    "no_scoring_adjudication_correctness_evidence_success_confirmed",
    "no_provider_llm_model_runtime_default_product_confirmed",
    "no_phase9_artifacts_as_evidence_confirmed",
    "frozen_phase10b_protocol_applied_exactly_confirmed",
)


def _confirmations_from_args(args: argparse.Namespace) -> dict[str, bool]:
    gate_ok = (
        getattr(args, "confirm_phase10b_commit", None) == PHASE10B_COMMIT
        and getattr(args, "confirm_phase10b_ci", None) == PHASE10B_CI_RUN
        and getattr(args, "confirm_phase10b_status", None) == PHASE10B_STATUS
    )
    return {
        "phase10b_commit_confirmed": getattr(args, "confirm_phase10b_commit", None) == PHASE10B_COMMIT,
        "phase10b_ci_confirmed": getattr(args, "confirm_phase10b_ci", None) == PHASE10B_CI_RUN,
        "phase10b_status_confirmed": getattr(args, "confirm_phase10b_status", None) == PHASE10B_STATUS,
        "phase10b_protocol_freeze_confirmed": bool(getattr(args, "confirm_phase10b_protocol_freeze", False)),
        "public_source_fetch_confirmed": bool(getattr(args, "confirm_public_source_fetch", False)),
        "private_output_confirmed": bool(getattr(args, "confirm_private_output", False)),
        "ignored_runs_workspace_confirmed": bool(getattr(args, "confirm_ignored_runs_workspace", False)),
        "aggregate_public_report_only_confirmed": bool(getattr(args, "confirm_aggregate_public_report_only", False)),
        "no_scoring_adjudication_correctness_evidence_success_confirmed": bool(
            getattr(args, "confirm_no_scoring_adjudication_correctness_evidence_success", False)
        ),
        "no_provider_llm_model_runtime_default_product_confirmed": bool(
            getattr(args, "confirm_no_provider_llm_model_runtime_default_product", False)
        ),
        "no_phase9_artifacts_as_evidence_confirmed": bool(
            getattr(args, "confirm_no_phase9_artifacts_as_evidence", False)
        ),
        "frozen_phase10b_protocol_applied_exactly_confirmed": bool(
            getattr(args, "confirm_frozen_phase10b_protocol_applied_exactly", False)
        ),
    }


# ---------------------------------------------------------------------------
# Execution pipeline (input construction / materialization under frozen rules)
#
# Discovery reads an optional PRIVATE channel registry under ignored runs/ only
# (operator-populated from eligible public metadata/channels).  Phase 10C does
# NOT read any Phase 9 private artifact.  When no eligible channel registry is
# present, discovery yields zero candidates -> honest repair/no-claim (no
# tuning/padding).  Materialization (git clone) is attempted only behind the
# explicit confirmation flags; the self-test never calls it.
# ---------------------------------------------------------------------------

_CHANNEL_REGISTRY_RELPATH = "channels/channel_registry.json"


def _locate_private_channel_registry(private_run_dir: Path) -> Path | None:
    """Locate an optional private channel registry under ignored runs/ only.

    Returns the registry path if it exists AND is under the ignored runs/ root,
    else None.  This is the ONLY runs/ read performed during execution; it is
    a channel-registry read (public metadata), never a Phase 9 artifact read.
    """
    global PRIVATE_RUNS_READ_ATTEMPTS
    PRIVATE_RUNS_READ_ATTEMPTS += 1
    try:
        candidate = (private_run_dir / _CHANNEL_REGISTRY_RELPATH).resolve()
    except (OSError, RuntimeError):
        return None
    runs_root = (REPO / "runs").resolve()
    if candidate != runs_root and runs_root not in candidate.parents:
        return None
    if not candidate.exists():
        return None
    return candidate


def _read_candidates_from_registry(registry_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read candidate source descriptors from a private channel registry.

    The registry is operator-populated from eligible public metadata/channels.
    Each candidate descriptor carries only the fields needed for deterministic
    ordering + eligibility; source identities stay private under ignored runs/.
    Returns (candidates, errors).  No network fetch here.
    """
    global PRIVATE_RUNS_READ_ATTEMPTS
    PRIVATE_RUNS_READ_ATTEMPTS += 1
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"channel registry unreadable: {exc}"]
    if not isinstance(data, dict):
        return [], ["channel registry must be object"]
    candidates_raw = data.get("candidates")
    if not isinstance(candidates_raw, list):
        return [], ["channel registry candidates missing"]
    candidates: list[dict[str, Any]] = []
    for entry in candidates_raw:
        if not isinstance(entry, dict):
            continue
        candidates.append(entry)
    return candidates, []


def _deterministic_sort_key(candidate: dict[str, Any], channel_index: int) -> tuple[Any, ...]:
    """Predeclared deterministic sort key (no randomness).

    Per the frozen Phase 10B rule ``stable_channel_then_stable_public_
    metadata_order`` the frozen channel order (CHANNEL_ORDER) is applied
    FIRST, then the predeclared public metadata sort keys
    (DETERMINISTIC_SORT_KEYS):
      channel_local_index_ascending (frozen CHANNEL_ORDER position),
      normalized_public_project_identity_ascending,
      public_metadata_stable_rank_ascending,
      default_branch_name_ascending.
    Missing fields sort last via stable defaults.
    """
    identity = str(candidate.get("normalized_public_project_identity", "") or "")
    rank = candidate.get("public_metadata_stable_rank")
    try:
        rank_val: Any = int(rank) if rank is not None else 10 ** 9
    except (TypeError, ValueError):
        rank_val = 10 ** 9
    branch = str(candidate.get("default_branch_name", "") or "")
    # Channel order first, then predeclared public metadata sort keys.
    return (channel_index, identity, rank_val, branch)


def _apply_source_eligibility(candidate: dict[str, Any]) -> tuple[bool, str]:
    """Apply the frozen Phase 10B source eligibility before any use.

    Returns (eligible, skip_reason).  Eligibility is decided from the
    candidate's public metadata fields ONLY; no Phase 9 artifact is consulted.
    Ambiguity unresolved under frozen rules => skip (not pad).
    """
    if candidate.get("publicly_accessible_without_authentication") is not True:
        return False, "not_public_no_auth"
    if candidate.get("source_archive_materializable") is not True:
        return False, "not_materializable"
    license_auditable = candidate.get("license_publicly_auditable")
    if license_auditable is not True:
        return False, "license_not_auditable"
    default_branch = candidate.get("default_branch_resolvable")
    if default_branch is not True:
        return False, "default_branch_ambiguous"
    lang_mix = candidate.get("in_scope_language_mix_detectable")
    if lang_mix is not True:
        return False, "language_mix_undetectable"
    if candidate.get("is_phase9_artifact_or_derived") is True:
        return False, "phase9_artifact_or_derived"
    if candidate.get("is_private_prior_or_manual_seed") is True:
        return False, "private_prior_or_manual_seed"
    # Freshness/fencing: candidate must be declared explicitly fresh (not
    # from Phase 9).  Missing or ambiguous freshness must fail-closed
    # (skip/repair), not accept -- only an explicit True passes.
    if candidate.get("fresh_not_from_phase9") is not True:
        return False, "freshness_ambiguous_or_missing"
    return True, ""


def _materialize_source(candidate: dict[str, Any], clone_target: Path) -> tuple[bool, str]:
    """Attempt a public fetch/clone into ignored runs/ workspace only.

    Behind explicit confirmation flags only.  Uses unauthenticated public
    transport only; no credentials, no auth prompts, no private host, no local
    fallback.  On any network/auth/redirect/license/default-branch ambiguity
    unresolved under frozen rules, returns (False, reason) and skips (no pad).
    """
    global FETCH_CLONE_ATTEMPTS, MATERIALIZATION_ATTEMPTS
    FETCH_CLONE_ATTEMPTS += 1
    MATERIALIZATION_ATTEMPTS += 1
    try:
        _assert_under_ignored_runs(clone_target)
    except ValueError as exc:
        return False, f"clone_target_not_under_runs: {exc}"
    clone_url = candidate.get("public_clone_url")
    if not isinstance(clone_url, str) or not clone_url:
        # No public clone URL resolved from the channel registry -> skip under
        # frozen rules (no local fallback, no private host, no auth prompt).
        return False, "no_public_clone_url_resolved"
    # Network ambiguity fail-closed: only unauthenticated public https/git
    # transports are permitted.  Anything else is skipped, not padded.
    lowered = clone_url.lower()
    if not (lowered.startswith("https://") or lowered.startswith("git://")):
        return False, "transport_not_public_https_or_git"
    if "@" in lowered.split("://", 1)[-1]:
        return False, "auth_credential_in_url_rejected"
    try:
        clone_target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"workspace_unavailable: {exc}"
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(clone_target)],
            cwd=str(REPO),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"fetch_clone_unavailable: {exc}"
    if proc.returncode != 0:
        return False, "fetch_clone_returned_nonzero"
    if not clone_target.exists():
        return False, "materialization_target_missing_after_clone"
    return True, ""


def _generate_packet(accepted_source: dict[str, Any], packet_dir: Path, ordinal: int) -> tuple[bool, str]:
    """Generate an independent replication/input packet under ignored runs/ only.

    The packet contains public source identity + fenced acquisition metadata
    only (no Phase 9 artifacts, no private rows/observables).  No scoring,
    adjudication, correctness, or evidence_success.  Source-specific details
    stay private under ignored runs/.
    """
    global PACKET_GENERATION_ATTEMPTS
    PACKET_GENERATION_ATTEMPTS += 1
    try:
        _assert_under_ignored_runs(packet_dir)
    except ValueError as exc:
        return False, f"packet_dir_not_under_runs: {exc}"
    try:
        packet_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"packet_workspace_unavailable: {exc}"
    packet = {
        "schema": "phase10c_independent_replication_packet_v1",
        "ordinal": ordinal,
        "fresh_not_from_phase9": True,
        "fenced_from_phase9_private_artifacts": True,
        "acquisition_metadata_only": True,
        "no_phase9_artifacts": True,
        "no_private_rows_or_observables": True,
        "source_identity_private_under_ignored_runs": True,
    }
    packet_path = packet_dir / f"packet_{ordinal:04d}.json"
    try:
        packet_path.write_text(json.dumps(packet, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return False, f"packet_write_unavailable: {exc}"
    return True, ""


def _write_private_records(
    private_run_dir: Path,
    candidates: list[dict[str, Any]],
    accepted: list[dict[str, Any]],
    materialization_records: list[dict[str, Any]],
    packet_records: list[dict[str, Any]],
) -> list[str]:
    """Write private registries/manifests/materialization records under runs/."""
    errors: list[str] = []
    try:
        root = _assert_under_ignored_runs(private_run_dir)
        root.mkdir(parents=True, exist_ok=True)
        registry = {
            "schema": "phase10c_private_source_registry_v1",
            "fresh_not_from_phase9": True,
            "fenced_from_phase9_private_artifacts": True,
            "candidate_descriptors": candidates,
            "accepted_descriptors": accepted,
            "materialization_records": materialization_records,
            "packet_records": packet_records,
        }
        (root / "private_source_registry.json").write_text(
            json.dumps(registry, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        errors.append(f"private_records_write_failed: {exc}")
    return errors


def run_execution(args: argparse.Namespace) -> dict[str, Any]:
    """Run the Phase 10C input-construction execution pipeline.

    Returns an aggregate dict (private counts only; the public report builder
    converts these to buckets).  Requires all confirmation flags; fails closed
    otherwise without any fetch/clone/private write.
    """
    global SOURCE_DISCOVERY_ATTEMPTS
    confirmations = _confirmations_from_args(args)
    all_confirmed = all(confirmations.values()) and len(confirmations) == len(CONFIRMATION_KEYS)
    if not all_confirmed:
        return {
            "executed": False,
            "discovered_candidates": 0,
            "materialized_sources": 0,
            "accepted_sources": 0,
            "packets_generated": 0,
            "caps_respected": True,
            "deterministic_ordering_applied": True,
            "discovery_attempted": False,
            "materialization_attempted": False,
            "packet_generation_attempted": False,
            "repair_reason": "confirmations_missing",
        }
    if not _runs_is_ignored():
        return {
            "executed": False,
            "discovered_candidates": 0,
            "materialized_sources": 0,
            "accepted_sources": 0,
            "packets_generated": 0,
            "caps_respected": True,
            "deterministic_ordering_applied": True,
            "discovery_attempted": False,
            "materialization_attempted": False,
            "packet_generation_attempted": False,
            "repair_reason": "confirmations_missing",
        }

    private_run_dir = Path(args.private_run_dir)
    try:
        _assert_under_ignored_runs(private_run_dir)
    except ValueError as exc:
        return {
            "executed": False,
            "discovered_candidates": 0,
            "materialized_sources": 0,
            "accepted_sources": 0,
            "packets_generated": 0,
            "caps_respected": True,
            "deterministic_ordering_applied": True,
            "discovery_attempted": False,
            "materialization_attempted": False,
            "packet_generation_attempted": False,
            "repair_reason": "confirmations_missing",
        }

    # 1. Discover candidates from the eligible private channel registry under
    #    ignored runs/ only (operator-populated from public metadata/channels).
    #    Phase 10C does NOT read any Phase 9 private artifact here.
    SOURCE_DISCOVERY_ATTEMPTS += 1
    registry_path = _locate_private_channel_registry(private_run_dir)
    if registry_path is None:
        # No eligible channel registry present -> zero candidates -> honest
        # repair/no-claim (no tuning, no padding, no protocol change).
        _write_private_records(private_run_dir, [], [], [], [])
        return {
            "executed": True,
            "discovered_candidates": 0,
            "materialized_sources": 0,
            "accepted_sources": 0,
            "packets_generated": 0,
            "caps_respected": True,
            "deterministic_ordering_applied": True,
            "discovery_attempted": True,
            "materialization_attempted": True,
            "packet_generation_attempted": False,
            "repair_reason": "no_eligible_channel_registry",
        }

    candidates, reg_errors = _read_candidates_from_registry(registry_path)
    if reg_errors:
        _write_private_records(private_run_dir, [], [], [], [])
        return {
            "executed": True,
            "discovered_candidates": 0,
            "materialized_sources": 0,
            "accepted_sources": 0,
            "packets_generated": 0,
            "caps_respected": True,
            "deterministic_ordering_applied": True,
            "discovery_attempted": True,
            "materialization_attempted": True,
            "packet_generation_attempted": False,
            "repair_reason": "no_eligible_channel_registry",
        }

    # 2. Deterministic ordering: stable channel order (CHANNEL_ORDER) then
    #    predeclared sort keys (DETERMINISTIC_SORT_KEYS).  No randomness.
    def _channel_index(cand: dict[str, Any]) -> int:
        ch = str(cand.get("channel", "") or "")
        for idx, name in enumerate(CHANNEL_ORDER):
            if ch == name:
                return idx
        return len(CHANNEL_ORDER)

    ordered = sorted(
        candidates,
        key=lambda c: _deterministic_sort_key(c, _channel_index(c)),
    )

    # 3. Apply caps (inspection cap total 48, per-channel cap 16) + eligibility.
    inspected: list[dict[str, Any]] = []
    per_channel_counts: dict[str, int] = {}
    accepted: list[dict[str, Any]] = []
    materialization_records: list[dict[str, Any]] = []
    caps_respected = True
    for cand in ordered:
        if len(inspected) >= CANDIDATE_INSPECTION_CAP_TOTAL:
            caps_respected = caps_respected and True
            break
        ch = str(cand.get("channel", "") or "")
        if per_channel_counts.get(ch, 0) >= CANDIDATE_INSPECTION_CAP_PER_CHANNEL:
            continue
        per_channel_counts[ch] = per_channel_counts.get(ch, 0) + 1
        inspected.append(cand)
        eligible, skip_reason = _apply_source_eligibility(cand)
        if not eligible:
            continue
        if len(accepted) >= ACCEPTED_SOURCE_TARGET_CAP:
            break
        # 4. Materialize (fetch/clone) into ignored runs/ only.
        ordinal = len(accepted)
        clone_target = private_run_dir / "materialized" / f"src_{ordinal:04d}"
        ok, reason = _materialize_source(cand, clone_target)
        materialization_records.append({
            "ordinal": ordinal,
            "materialized": ok,
            "reason": reason,
        })
        if not ok:
            continue
        accepted.append(cand)

    # 5. Packet generation: only when minimum cap met (else repair/no-claim,
    #    no padding/tuning).  Replacement before packet generation only.
    packet_records: list[dict[str, Any]] = []
    packet_generation_attempted = False
    repair_reason = ""
    if len(accepted) >= ACCEPTED_SOURCE_MINIMUM_CAP and accepted:
        packet_generation_attempted = True
        for idx, src in enumerate(accepted):
            packet_dir = private_run_dir / "packets"
            ok, reason = _generate_packet(src, packet_dir, idx)
            packet_records.append({"ordinal": idx, "generated": ok, "reason": reason})
    else:
        repair_reason = "below_minimum_after_caps"

    _write_private_records(private_run_dir, inspected, accepted, materialization_records, packet_records)

    return {
        "executed": True,
        "discovered_candidates": len(candidates),
        "materialized_sources": sum(1 for r in materialization_records if r.get("materialized")),
        "accepted_sources": len(accepted),
        "packets_generated": sum(1 for r in packet_records if r.get("generated")),
        "caps_respected": caps_respected,
        "deterministic_ordering_applied": True,
        "discovery_attempted": True,
        "materialization_attempted": True,
        "packet_generation_attempted": packet_generation_attempted,
        "repair_reason": repair_reason,
    }


# ---------------------------------------------------------------------------
# Self-test (synthetic fixtures only; no network/private/scoring)
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_DISCOVERY_ATTEMPTS, MATERIALIZATION_ATTEMPTS
    global PACKET_GENERATION_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS
    global SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS, PROVIDER_OR_MODEL_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_DISCOVERY_ATTEMPTS = 0
    MATERIALIZATION_ATTEMPTS = 0
    PACKET_GENERATION_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    # Dry (no-execution) report: all execution booleans false, repair status.
    dry = build_public_report()
    checks.append(("dry_report_valid", not validate_report(dry)))
    checks.append(("dry_status_is_repair", dry["status"] == STATUS_REPAIR))
    checks.append(("dry_phase_equals_slug", dry["phase"] == PHASE))
    checks.append(("dry_discovery_not_executed", dry["execution_summary"]["source_discovery_executed"] is False))
    checks.append(("dry_packet_generation_not_executed", dry["execution_summary"]["packet_generation_executed"] is False))
    checks.append(("dry_repair_reason_bucket_not_executed", dry["execution_summary"]["repair_reason_bucket"] == "bucket_not_executed"))

    # Executed report with all confirmations but zero accepted sources -> repair.
    all_conf = {key: True for key in CONFIRMATION_KEYS}
    exec_zero = build_public_report(
        aggregate={"discovered_candidates": 0, "accepted_sources": 0,
                   "materialized_sources": 0, "packets_generated": 0,
                   "discovery_attempted": True, "materialization_attempted": True,
                   "packet_generation_attempted": False,
                   "caps_respected": True, "deterministic_ordering_applied": True},
        confirmations=all_conf,
        repair_reason="no_eligible_channel_registry",
        executed=True,
    )
    checks.append(("executed_zero_valid", not validate_report(exec_zero)))
    checks.append(("executed_zero_status_repair", exec_zero["status"] == STATUS_REPAIR))
    checks.append(("executed_zero_discovery_executed", exec_zero["execution_summary"]["source_discovery_executed"] is True))
    checks.append(("executed_zero_accepted_bucket_zero", exec_zero["execution_summary"]["accepted_source_bucket"] == "bucket_zero"))
    checks.append(("executed_zero_repair_bucket", exec_zero["execution_summary"]["repair_reason_bucket"] == "bucket_no_eligible_channel_registry"))

    # Executed report meeting the minimum -> executed status (no scoring/no claim).
    exec_ok = build_public_report(
        aggregate={"discovered_candidates": 12, "accepted_sources": ACCEPTED_SOURCE_MINIMUM_CAP,
                   "materialized_sources": ACCEPTED_SOURCE_MINIMUM_CAP,
                   "packets_generated": ACCEPTED_SOURCE_MINIMUM_CAP,
                   "discovery_attempted": True, "materialization_attempted": True,
                   "packet_generation_attempted": True,
                   "caps_respected": True, "deterministic_ordering_applied": True},
        confirmations=all_conf,
        executed=True,
    )
    checks.append(("executed_min_valid", not validate_report(exec_ok)))
    checks.append(("executed_min_status_executed", exec_ok["status"] == STATUS_EXECUTED))
    checks.append(("executed_min_packet_generation_executed", exec_ok["execution_summary"]["packet_generation_executed"] is True))
    checks.append(("executed_min_accepted_bucket_minimum", exec_ok["execution_summary"]["accepted_source_bucket"] == "bucket_at_least_minimum_below_target"))
    checks.append(("executed_min_repair_bucket_none", exec_ok["execution_summary"]["repair_reason_bucket"] == "bucket_none"))

    # Status/bucket consistency: executed status is inconsistent with
    # bucket_zero / no packet generation / no materialization / a repair
    # reason and must be rejected; repair status with bucket_zero is the
    # honest accepted outcome.
    inconsistent = copy.deepcopy(exec_zero)
    inconsistent["status"] = STATUS_EXECUTED
    inconsistent_errors = validate_report(inconsistent)
    checks.append(("executed_status_with_bucket_zero_rejected", bool(inconsistent_errors)))
    checks.append(("executed_status_with_bucket_zero_consistency_error",
                   any("executed status requires" in e for e in inconsistent_errors)))
    checks.append(("repair_status_with_bucket_zero_accepted", not validate_report(exec_zero)))
    # Executed status with a below-minimum (but nonzero) bucket is also rejected.
    below_min = copy.deepcopy(exec_ok)
    below_min["execution_summary"]["accepted_source_bucket"] = "bucket_nonzero_below_minimum"
    checks.append(("executed_status_with_below_minimum_bucket_rejected", bool(validate_report(below_min))))

    # Reject missing/wrong Phase 10B gate references.
    for field, bad_val, label in (
        ("phase10b_commit", "deadbeef" * 5, "commit"),
        ("phase10b_ci_run", "0000", "ci_run"),
        ("phase10b_status", "drift", "status"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10b_gate"][field] = bad_val
        checks.append((f"wrong_phase10b_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        del mutated["phase10b_gate"][field]
        checks.append((f"missing_phase10b_{label}_rejected", bool(validate_report(mutated))))

    # Reject gate facts flipped to false.
    for key in ("phase10b_ci_success", "phase10b_gate_required_before_phase10c",
                "phase10b_protocol_freeze_only"):
        mutated = copy.deepcopy(dry)
        mutated["phase10b_gate"][key] = False
        checks.append((f"phase10b_gate_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject inherited-gate facts flipped to false.
    for key in ("phase10a_gate_inherited", "phase9_closure_inherited",
                "older_phase9_exact_refs_not_republished_by_phase10c"):
        mutated = copy.deepcopy(dry)
        mutated["inherited_gates"][key] = False
        checks.append((f"inherited_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema drift.
    for field, bad in (("status", "drift"), ("phase", "drift"), ("schema_version", "drift")):
        mutated = copy.deepcopy(dry)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # Reject execution booleans true (forbidden in Phase 10C).
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["phase10c_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject exact count fields.
    mutated = copy.deepcopy(dry)
    mutated["execution_summary"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    # Reject private-shaped values.
    for label, bad_val in (
        ("url", "https://example.invalid/repo.git"),
        ("owner_repo", "owner/repo"),
        ("hash", "a" * 40),
        ("path", "src/private.py"),
        ("task_id", "task_id_7"),
        ("run_dir", "runs/secret/run_dir"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10c_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "source_path_bucket", "path", "repo_name", "task_id", "row_id",
        "packet_id", "manifest", "run_dir",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10c_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject threshold/novel-metric/subgroup keys.
    for bad_key in ("correctness_threshold", "adjudication_threshold", "decision_threshold",
                    "novel_metric_bucket", "subgroup_breakdown"):
        mutated = copy.deepcopy(dry)
        mutated["frozen_source_eligibility"][bad_key] = "example"
        checks.append((f"forbidden_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject unknown closed-list members (set-equality) for every imported list.
    for _s, key, expected, label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(dry)
        mutated[_s][key].append("extra_bogus_member")
        errors = validate_report(mutated)
        checks.append((f"extra_{label}_member_rejected", bool(errors)))
        checks.append((f"extra_{label}_member_set_equality", any("has extra members" in e for e in errors)))
    for _s, key, expected, label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(dry)
        mutated[_s][key] = mutated[_s][key][1:]
        checks.append((f"missing_{label}_member_rejected", bool(validate_report(mutated))))

    # Reject reworded closed-list member (vocabulary drift).
    mutated = copy.deepcopy(dry)
    mutated["frozen_source_eligibility"]["source_eligibility_rules"][0] = "looks_good_after_review"
    checks.append(("source_eligibility_vocabulary_drift_rejected", bool(validate_report(mutated))))

    # Reject caps drift.
    mutated = copy.deepcopy(dry)
    mutated["frozen_caps_and_abort_limits"]["caps"]["candidate_inspection_cap_total"] = 96
    checks.append(("caps_drift_rejected", bool(validate_report(mutated))))

    # Reject seed label / channel order / sort keys drift.
    mutated = copy.deepcopy(dry)
    mutated["frozen_deterministic_ordering_selection"]["predeclared_seed_label"] = "wrong_seed"
    checks.append(("seed_label_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["frozen_deterministic_ordering_selection"]["channel_order"] = list(reversed(CHANNEL_ORDER))
    checks.append(("channel_order_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["frozen_deterministic_ordering_selection"]["deterministic_sort_keys"] = list(reversed(DETERMINISTIC_SORT_KEYS))
    checks.append(("sort_keys_drift_rejected", bool(validate_report(mutated))))

    # Reject claim boundary true.
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject privacy contract violations.
    for privacy_key in (
        "per_source_public_facts", "per_task_public_facts",
        "run_locations_public", "repo_names_public",
        "packet_ids_public", "exact_counts_or_rates_public", "singleton_buckets_public",
        "phase9_private_artifacts_public", "phase10a_private_artifacts_public",
        "phase10b_private_artifacts_public", "source_urls_public", "candidate_repo_names_public",
    ):
        mutated = copy.deepcopy(dry)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(dry)
        mutated["frozen_source_eligibility"]["source_eligibility_rules"].append(singleton_val)
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # Reject claim-making wording.
    for phrase in ("method effectiveness", "product readiness", "scoring success", "outcome success",
                   "evaluation works", "acquisition success", "adjudication proven",
                   "correctness proven", "evidence_success achieved", "lift achieved",
                   "generalized success", "evidence-acquisition success", "validation proven"):
        mutated = copy.deepcopy(dry)
        mutated["frozen_source_eligibility"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # Reject user-approval wording.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    # Reject placeholder wording.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(dry)
        mutated["frozen_source_eligibility"]["source_eligibility_rules"].append(phrase)
        checks.append((f"placeholder_{phrase}_rejected", bool(validate_report(mutated))))

    # Reject truth-boundary violation.
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["truth_boundary"][key] = False
        checks.append((f"truth_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Reject unknown fields.
    mutated = copy.deepcopy(dry)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10c_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["frozen_source_eligibility"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_eligibility_rejected", bool(validate_report(mutated))))

    # Reject non-gate hash/CI values.
    mutated = copy.deepcopy(dry)
    mutated["phase10c_scope"]["task_ci_run"] = "29004189917"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    mutated = copy.deepcopy(dry)
    mutated["phase10c_scope"]["example_hash"] = "19abcdd8f09e190c323a28fab8e3e0401d504236"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))
    checks.append(("gate_ref_commit_values_on_whitelisted_paths_valid", not validate_report(dry)))

    # Path guard tests.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10c" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9r_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10c" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Eligibility helper: synthetic candidate fixtures (no network/private).
    good_cand = {
        "publicly_accessible_without_authentication": True,
        "source_archive_materializable": True,
        "license_publicly_auditable": True,
        "default_branch_resolvable": True,
        "in_scope_language_mix_detectable": True,
        "is_phase9_artifact_or_derived": False,
        "is_private_prior_or_manual_seed": False,
        "fresh_not_from_phase9": True,
    }
    checks.append(("eligibility_accepts_synthetic_eligible", _apply_source_eligibility(good_cand)[0]))
    for bad_field in ("publicly_accessible_without_authentication", "source_archive_materializable",
                      "license_publicly_auditable", "default_branch_resolvable",
                      "in_scope_language_mix_detectable"):
        bad_cand = dict(good_cand)
        bad_cand[bad_field] = False
        ok_elig, _ = _apply_source_eligibility(bad_cand)
        checks.append((f"eligibility_rejects_{bad_field}_false", not ok_elig))
    phase9_cand = dict(good_cand)
    phase9_cand["is_phase9_artifact_or_derived"] = True
    checks.append(("eligibility_rejects_phase9_derived", not _apply_source_eligibility(phase9_cand)[0]))
    notfresh_cand = dict(good_cand)
    notfresh_cand["fresh_not_from_phase9"] = False
    checks.append(("eligibility_rejects_not_fresh", not _apply_source_eligibility(notfresh_cand)[0]))
    # Missing/ambiguous freshness must fail-closed (skip), not accept.
    missing_fresh_cand = dict(good_cand)
    del missing_fresh_cand["fresh_not_from_phase9"]
    checks.append(("eligibility_rejects_missing_freshness", not _apply_source_eligibility(missing_fresh_cand)[0]))
    ambiguous_fresh_cand = dict(good_cand)
    ambiguous_fresh_cand["fresh_not_from_phase9"] = None
    checks.append(("eligibility_rejects_ambiguous_freshness_null", not _apply_source_eligibility(ambiguous_fresh_cand)[0]))
    stringy_fresh_cand = dict(good_cand)
    stringy_fresh_cand["fresh_not_from_phase9"] = "true"
    checks.append(("eligibility_rejects_ambiguous_freshness_string", not _apply_source_eligibility(stringy_fresh_cand)[0]))

    # Deterministic sort key is stable / no randomness.
    cands = [
        {"normalized_public_project_identity": "b", "public_metadata_stable_rank": 2, "default_branch_name": "main", "channel": "public_registry_lists"},
        {"normalized_public_project_identity": "a", "public_metadata_stable_rank": 1, "default_branch_name": "main", "channel": "public_registry_lists"},
    ]
    ordered_cands = sorted(cands, key=lambda c: _deterministic_sort_key(c, 0))
    checks.append(("deterministic_sort_stable", ordered_cands[0]["normalized_public_project_identity"] == "a"))

    # Channel order must be applied FIRST per frozen Phase 10B rule
    # stable_channel_then_stable_public_metadata_order.  A candidate from
    # an earlier channel (index 0) must precede a candidate from a later
    # channel (index 2) even when the later-channel candidate has an
    # earlier public metadata identity.  This would fail if channel_index
    # were applied last instead of first.
    cand_early_channel_late_identity = {
        "normalized_public_project_identity": "z",
        "public_metadata_stable_rank": 9,
        "default_branch_name": "main",
    }
    cand_late_channel_early_identity = {
        "normalized_public_project_identity": "a",
        "public_metadata_stable_rank": 1,
        "default_branch_name": "main",
    }
    ordered_chan = sorted(
        [cand_late_channel_early_identity, cand_early_channel_late_identity],
        key=lambda c: _deterministic_sort_key(
            c, 2 if c is cand_late_channel_early_identity else 0),
    )
    checks.append((
        "channel_order_applied_before_metadata_sort_keys",
        ordered_chan[0] is cand_early_channel_late_identity,
    ))

    # Temp-file round-trip (synthetic fixture only; no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10c_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(dry), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))
        runs_tmp = Path(tmp) / "runs" / "report.json"
        runs_tmp.parent.mkdir(parents=True, exist_ok=True)
        runs_tmp.write_text(json.dumps(dry), encoding="utf-8")
        ok, _ = _validate_report_path_is_public(runs_tmp)
        checks.append(("validate_report_rejects_temp_runs_path", not ok))

    # Prove the self-test did not fetch/read/private/execute/score.
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_discover_sources", SOURCE_DISCOVERY_ATTEMPTS == 0))
    checks.append(("selftest_does_not_materialize", MATERIALIZATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_packets", PACKET_GENERATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9_artifacts", PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_score_adjudicate_or_execute", SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_call_provider_or_model", PROVIDER_OR_MODEL_CALL_ATTEMPTS == 0))

    # Confirmation-key set matches the schema expectations.
    checks.append(("confirmation_keys_count_matches", len(CONFIRMATION_KEYS) == 12))

    failed = [name for name, ok_flag in checks if not ok_flag]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 10C input-construction execution (no scoring, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true",
                        help="write a dry no-execution repair report (no private output, no fetch)")
    parser.add_argument("--execute", action="store_true",
                        help="execute the input-construction pipeline under explicit confirmations")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--private-run-dir", type=Path, default=DEFAULT_PRIVATE_RUN_DIR)
    parser.add_argument("--confirm-phase10b-commit")
    parser.add_argument("--confirm-phase10b-ci")
    parser.add_argument("--confirm-phase10b-status")
    parser.add_argument("--confirm-phase10b-protocol-freeze", action="store_true")
    parser.add_argument("--confirm-public-source-fetch", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--confirm-ignored-runs-workspace", action="store_true")
    parser.add_argument("--confirm-aggregate-public-report-only", action="store_true")
    parser.add_argument("--confirm-no-scoring-adjudication-correctness-evidence-success", action="store_true")
    parser.add_argument("--confirm-no-provider-llm-model-runtime-default-product", action="store_true")
    parser.add_argument("--confirm-no-phase9-artifacts-as-evidence", action="store_true")
    parser.add_argument("--confirm-frozen-phase10b-protocol-applied-exactly", action="store_true")
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
    if args.execute:
        confirmations = _confirmations_from_args(args)
        all_confirmed = all(confirmations.values()) and len(confirmations) == len(CONFIRMATION_KEYS)
        if not all_confirmed:
            print("ERROR: --execute requires all --confirm-* flags and matching Phase 10B gate values",
                  file=sys.stderr)
            return 1
        if not _runs_is_ignored():
            print("ERROR: runs/ must remain ignored before execution", file=sys.stderr)
            return 1
        aggregate = run_execution(args)
        report = build_public_report(
            aggregate=aggregate,
            confirmations=confirmations,
            repair_reason=aggregate.get("repair_reason", ""),
            executed=bool(aggregate.get("executed", False)),
        )
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "status": report["status"],
            "public_report": str(args.output),
            "private_output_root": str(Path(args.private_run_dir).resolve()),
            "source_discovery_executed": report["execution_summary"]["source_discovery_executed"],
            "accepted_source_bucket": report["execution_summary"]["accepted_source_bucket"],
            "repair_reason_bucket": report["execution_summary"]["repair_reason_bucket"],
        }, indent=2, sort_keys=True))
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
    parser.error("choose --self-test, --write-report, --execute, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
