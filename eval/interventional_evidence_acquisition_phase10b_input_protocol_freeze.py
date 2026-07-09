#!/usr/bin/env python3
"""Phase 10B fresh/fenced input-construction protocol freeze (no execution, no claim).

This is a docs/report/validator-only protocol-freeze checkpoint for fresh/fenced
input construction for the NEW independent Phase 10 validation line.  Phase 10 is
separate from Phase 9; it is not a continuation, reinterpretation, repair, rerun,
rescore, or strengthening of Phase 9R/9S.  Phase 9 is closed at commit ``1d71f6a``,
CI run ``28999245247``.  Phase 10A is committed at ``67e8d984601d82a2a97992bb83fda06b09e06be0``,
CI run ``29002587099`` success.  Phase 10B makes NO new evidence claims.

Phase 10B does NOT execute, discover, fetch, clone, sample, generate real
packets/tasks, score, adjudicate, evaluate correctness/evidence_success, or read
private/source artifacts.  It defines the future input-construction protocol
(source eligibility, freshness/fencing, independence-from-Phase-9, deterministic
ordering/selection rules, caps/abort limits, private/public artifact split,
replication packet schema, privacy scanner rules, and future 10C handoff gates)
WITHOUT instantiating any of them.

The Phase 9 closure gate and Phase 10A gate reference values are the only exact
public gate references published by Phase 10B.  Older Phase 9 exact commit/CI refs
are intentionally NOT republished by Phase 10B (tighter privacy).  Local same-tree
git commits are not read or compared; only the gate constants are exact references.

Future 10C requires 10B commit + CI green + separate boundary review before any
discovery/fetch/materialization.  Phase 10B does NOT authorize Phase 10C execution.
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

PHASE = "phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim"
STATUS = (
    "phase10b_fresh_fenced_input_construction_protocol_freeze"
    "_no_execution_no_materialization_no_claim"
)
SCHEMA_VERSION = "phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

# ---------------------------------------------------------------------------
# Gate reference values (oracle-provided).  These are the only exact public
# gate references published by Phase 10B.  Local same-tree git commits are
# not read or compared; the supplied confirmation values are matched against
# the frozen public gate constants only.
# ---------------------------------------------------------------------------
PHASE9_CLOSURE_COMMIT = "1d71f6a"
PHASE9_CLOSURE_CI_RUN = "28999245247"

PHASE10A_COMMIT = "67e8d984601d82a2a97992bb83fda06b09e06be0"
PHASE10A_CI_RUN = "29002587099"
PHASE10A_STATUS = "phase10a_independent_validation_protocol_freeze_no_execution_no_claim"

# ---------------------------------------------------------------------------
# Frozen Phase 10B closed lists (validator set-equality checked).
# ---------------------------------------------------------------------------

PROTOCOL_PUBLICATION_LEVEL = "aggregate_input_construction_protocol_freeze_boundary_only"

# 1. Source eligibility rules.
SOURCE_ELIGIBILITY_RULES = (
    "publicly_accessible_without_authentication",
    "source_archive_materializable_before_use",
    "declared_or_publicly_auditable_license_present",
    "default_branch_or_equivalent_revision_resolvable",
    "in_scope_language_or_file_mix_detectable_from_public_metadata",
    "not_phase9_artifact_or_phase9_derived_material",
    "not_private_prior_phase_or_manual_named_seed_material",
)

# 2. Freshness/fencing definition.
FRESHNESS_FENCING_RULES = (
    "inputs_must_be_fresh_not_reused_from_phase9",
    "inputs_must_be_fenced_from_phase9_private_artifacts",
    "fencing_requires_independent_replication_packet_generation",
    "no_phase9_priors_sources_labels_outcomes_as_input",
    "freshness_verified_before_any_sampling_or_packet_generation",
    "fencing_violation_is_hard_stop",
)

# 3. Independence-from-Phase-9 checks.
INDEPENDENCE_FROM_PHASE9_RULES = (
    "phase9_artifacts_cannot_be_used_as_validation_evidence",
    "phase9_source_filters_or_priors_cannot_be_reused",
    "phase9_labels_or_outcomes_cannot_be_reused_as_inputs",
    "phase9_sampling_inputs_cannot_be_reused",
    "clean_room_operator_must_not_use_memory_of_phase9_private_material",
    "independent_replication_packet_generation_required",
)

# 4. Deterministic ordering/selection rules (no actual draw in 10B).
DETERMINISTIC_ORDERING_SELECTION_RULES = (
    "predeclared_seed_label_version_only_randomness_forbidden",
    "stable_channel_then_stable_public_metadata_order",
    "deterministic_sort_keys_predeclared",
    "replacement_before_sampling_only",
    "replacement_reasons_limited_to_availability_or_eligibility",
    "performance_based_replacement_forbidden",
    "no_actual_sampling_draw_in_phase10b",
)

CHANNEL_ORDER = (
    "public_registry_lists",
    "public_ecosystem_topic_indexes",
    "public_package_or_project_metadata",
)

DETERMINISTIC_SORT_KEYS = (
    "normalized_public_project_identity_ascending",
    "public_metadata_stable_rank_ascending",
    "default_branch_name_ascending",
    "channel_local_index_ascending",
)

# 5. Caps and abort limits (structural protocol limits, NOT success metrics).
CAPS_AND_ABORT_LIMITS_RULES = (
    "caps_are_structural_protocol_limits_not_success_metrics",
    "caps_are_coarse_fixed_boundary_fields_not_measured_counts",
    "abort_on_quota_or_ordering_drift",
    "abort_on_eligibility_drift",
    "abort_on_fencing_violation",
    "abort_on_phase9_contamination",
    "abort_on_privacy_violation",
)

FROZEN_CAPS = {
    "candidate_inspection_cap_total": 48,
    "accepted_source_target_cap": 12,
    "accepted_source_minimum_cap": 8,
    "candidate_inspection_cap_per_channel": 16,
}

FROZEN_ABORT_LIMITS = (
    "abort_on_quota_or_ordering_drift",
    "abort_on_eligibility_drift",
    "abort_on_fencing_violation",
    "abort_on_phase9_contamination",
    "abort_on_privacy_violation",
)

# 6. Private/public artifact split.
PRIVATE_PUBLIC_ARTIFACT_SPLIT_RULES = (
    "public_output_aggregate_or_boundary_only",
    "private_material_under_ignored_runs_only",
    "no_repo_source_url_owner_commit_beyond_whitelisted_gate_refs",
    "no_paths_snippets_line_ranges_or_identifier_or_run_location_facts",
    "no_per_source_per_task_or_per_packet_facts",
    "no_singleton_buckets",
    "no_phase9_or_phase10a_private_artifacts_published",
)

# 7. Independent replication packet schema (schema definition only, no packets).
REPLICATION_PACKET_SCHEMA_RULES = (
    "packet_schema_definition_only_no_packets_generated_in_phase10b",
    "packet_must_contain_public_source_identity_only",
    "packet_must_contain_fenced_acquisition_metadata_only",
    "packet_must_not_contain_phase9_artifacts",
    "packet_must_not_contain_private_rows_or_observables",
    "packet_must_be_independently_generated_in_future_phase10c",
    "packet_schema_must_support_aggregate_only_public_reporting",
)

# 8. Privacy scanner rules.
PRIVACY_SCANNER_RULES = (
    "reject_private_shaped_keys_and_values",
    "reject_singleton_buckets",
    "reject_claim_wording",
    "reject_placeholder_wording",
    "reject_user_approval_wording",
    "reject_exact_count_fields",
    "reject_long_unapproved_numeric_run_ids",
    "gate_exact_values_allowed_only_at_exact_gate_paths",
)

# 9. Future 10C handoff gates.
FUTURE_10C_HANDOFF_GATES = (
    "phase10b_commit_required",
    "phase10b_ci_green_required",
    "separate_boundary_review_after_phase10b_commit_and_ci_green_before_phase10c",
    "explicit_execution_and_materialization_boundary_required_before_phase10c",
    "phase10b_does_not_authorize_phase10c_execution",
)

# 10. Explicit Phase 10B forbidden actions.
FORBIDDEN_ACTIONS_RULES = (
    "no_private_reads_or_rereads_in_phase10b",
    "no_ignored_runs_reads_in_phase10b",
    "no_phase9_artifact_reads_or_reuse_in_phase10b",
    "no_public_source_discovery_in_phase10b",
    "no_repo_source_fetch_clone_refresh_checkout_api_query_or_scrape_in_phase10b",
    "no_source_code_reads_from_candidate_validation_targets_in_phase10b",
    "no_task_generation_or_sampling_draw_in_phase10b",
    "no_real_packet_generation_in_phase10b",
    "no_scoring_adjudication_correctness_or_evidence_success_in_phase10b",
    "no_provider_llm_or_model_calls_in_phase10b",
    "no_metrics_thresholds_rates_or_counts_beyond_coarse_fixed_status_boundary_fields_in_phase10b",
    "no_claims_about_validation_method_product_correctness_or_generalization_in_phase10b",
)

# 11. No-execution guardrails.
NO_EXECUTION_GUARDRAIL_RULES = (
    "no_execution_in_phase10b",
    "no_discovery_in_phase10b",
    "no_fetch_clone_or_materialization_in_phase10b",
    "no_source_reads_in_phase10b",
    "no_task_generation_or_sampling_in_phase10b",
    "no_packet_generation_in_phase10b",
    "no_scoring_adjudication_or_correctness_evaluation_in_phase10b",
    "no_provider_llm_or_model_calls_in_phase10b",
    "no_private_reads_in_phase10b",
)

# Truth-boundary attestation keys that must always be True.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_at_recorded_commit_and_ci",
    "phase10a_gate_passed_at_recorded_commit_and_ci",
    "phase10b_makes_no_evidence_method_product_performance_correctness_or_generalization_claims",
    "phase10b_does_not_execute_discover_fetch_clone_sample_or_materialize",
    "phase10b_does_not_read_private_or_source_artifacts",
    "phase10b_does_not_reuse_phase9_artifacts_as_validation_evidence",
    "phase10c_requires_separate_boundary_review_after_phase10b_commit_and_ci_green",
)

# Boundary attestation keys that must always be False.
NO_EXECUTION_FALSE_KEYS = (
    "private_reads_executed",
    "private_rereads_executed",
    "ignored_runs_read_executed",
    "phase9_artifacts_read_or_reused",
    "phase9r_rerun_or_rescored",
    "phase9s_rerun_or_reinterpreted",
    "source_discovery_executed",
    "fetch_clone_materialization_executed",
    "source_code_reads_executed",
    "tasks_generated",
    "sampling_draw_executed",
    "packets_generated",
    "scoring_executed",
    "adjudication_executed",
    "correctness_evaluated",
    "evidence_success_evaluated",
    "provider_calls_executed",
    "claims_made",
    "model_fitting",
    "runtime_default_or_product_changes",
    "low_resource_autonomy_empirical_work_started",
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

# Closed protocol lists whose members are validator set-equality checked.
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
    ("frozen_future_10c_handoff_gates", "future_10c_handoff_gates", FUTURE_10C_HANDOFF_GATES, "future_10c_handoff_gates"),
    ("frozen_forbidden_actions", "forbidden_actions_rules", FORBIDDEN_ACTIONS_RULES, "forbidden_actions"),
    ("frozen_no_execution_guardrails", "no_execution_guardrail_rules", NO_EXECUTION_GUARDRAIL_RULES, "no_execution_guardrails"),
)

# Privacy scan regexes.
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
# public gate constants.  Phase 10B only publishes the Phase 9 closure and
# Phase 10A gate refs; older Phase 9 exact commit/CI values are intentionally
# NOT republished (tighter privacy).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9_closure_gate.phase9_closure_commit",
        "$.phase9_closure_gate.phase9_closure_ci_run",
        "$.phase10a_gate.phase10a_commit",
        "$.phase10a_gate.phase10a_ci_run",
    }
)

DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9_closure_gate.phase9_closure_ci_run",
        "$.phase10a_gate.phase10a_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read/execute.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10A_ARTIFACT_READ_ATTEMPTS = 0
SOURCE_DISCOVERY_ATTEMPTS = 0
MATERIALIZATION_ATTEMPTS = 0
TASK_GENERATION_OR_SAMPLING_ATTEMPTS = 0
PACKET_GENERATION_ATTEMPTS = 0
SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0

CONSERVATIVE_RECOMMENDATION = (
    "phase10b_fresh_fenced_input_construction_protocol_freeze_only_for_new_independent_validation_line"
    "_phase9_closed_at_recorded_commit_and_ci"
    "_phase10a_gate_passed_at_recorded_commit_and_ci"
    "_phase10b_makes_no_evidence_method_product_performance_correctness_or_generalization_claims"
    "_phase10b_does_not_execute_discover_fetch_clone_sample_or_materialize"
    "_phase10b_does_not_read_private_or_source_artifacts"
    "_phase10b_does_not_reuse_phase9_artifacts_as_validation_evidence"
    "_future_input_construction_requires_fresh_fenced_inputs_independent_from_phase9"
    "_source_eligibility_freshness_fencing_and_deterministic_ordering_rules_frozen"
    "_caps_and_abort_limits_frozen_as_structural_protocol_limits_not_success_metrics"
    "_replication_packet_schema_defined_only_no_packets_generated_in_phase10b"
    "_private_public_artifact_split_frozen_aggregate_only_public_reporting"
    "_privacy_scanner_rules_frozen"
    "_phase10c_requires_separate_boundary_review_after_phase10b_commit_and_ci_green"
    "_no_private_reads_no_source_reads_no_discovery_no_fetch_clone"
    "_no_task_generation_no_sampling_draw_no_packet_generation"
    "_no_scoring_adjudication_correctness_or_evidence_success_evaluation"
    "_no_metrics_thresholds_rates_counts_beyond_coarse_fixed_status_boundary_fields"
    "_no_product_method_performance_correctness_generalization_claim"
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
        "phase9_closure_gate_required_before_phase10b": None,
        "phase9r_9s_exact_refs_not_republished_by_phase10b": None,
    },
    "phase10a_gate": {
        "phase10a_commit": None,
        "phase10a_ci_run": None,
        "phase10a_ci_success": None,
        "phase10a_status": None,
        "phase10a_gate_required_before_phase10b": None,
        "phase10a_protocol_freeze_only": None,
    },
    "phase10b_scope": {
        "docs_report_validator_only": None,
        "input_construction_protocol_freeze_only": None,
        "phase10b_separate_from_phase9_not_continuation": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "frozen_source_eligibility": {
        "source_eligibility_rules": None,
        "publication_level": None,
        "source_eligibility_decided_before_any_use": None,
        "source_eligibility_drift_is_hard_stop": None,
    },
    "frozen_freshness_fencing": {
        "freshness_fencing_rules": None,
        "freshness_verified_before_any_sampling_or_packet_generation": None,
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
        "no_actual_sampling_draw_in_phase10b": None,
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
        "packet_schema_definition_only_no_packets_generated_in_phase10b": None,
        "packet_must_be_independently_generated_in_future_phase10c": None,
    },
    "frozen_privacy_scanner": {
        "privacy_scanner_rules": None,
        "gate_exact_values_allowed_only_at_exact_gate_paths": None,
        "reject_exact_count_fields": True and None,
    },
    "frozen_future_10c_handoff_gates": {
        "future_10c_handoff_gates": None,
        "separate_boundary_review_after_phase10b_commit_and_ci_green_before_phase10c": None,
        "phase10b_does_not_authorize_phase10c_execution": None,
    },
    "frozen_forbidden_actions": {
        "forbidden_actions_rules": None,
        "no_public_source_discovery_in_phase10b": None,
        "no_repo_source_fetch_clone_or_materialization_in_phase10b": None,
        "no_task_generation_or_sampling_draw_in_phase10b": None,
        "no_real_packet_generation_in_phase10b": None,
    },
    "frozen_no_execution_guardrails": {
        "no_execution_guardrail_rules": None,
        "no_execution_no_discovery_no_materialization_in_phase10b": None,
        "no_private_reads_in_phase10b": None,
        "no_source_reads_in_phase10b": None,
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
        "phase10b_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_read_phase10a_private_artifacts": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_generate_tasks": None,
        "validator_does_not_generate_packets": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_generates_tasks": None,
        "validator_generates_packets": None,
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


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
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
        return False, "report path is not under the Phase 10B public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9_closure_gate": {
            "phase9_closure_commit": PHASE9_CLOSURE_COMMIT,
            "phase9_closure_ci_run": PHASE9_CLOSURE_CI_RUN,
            "phase9_closure_ci_success": True,
            "phase9_closed": True,
            "phase9_closure_gate_required_before_phase10b": True,
            "phase9r_9s_exact_refs_not_republished_by_phase10b": True,
        },
        "phase10a_gate": {
            "phase10a_commit": PHASE10A_COMMIT,
            "phase10a_ci_run": PHASE10A_CI_RUN,
            "phase10a_ci_success": True,
            "phase10a_status": PHASE10A_STATUS,
            "phase10a_gate_required_before_phase10b": True,
            "phase10a_protocol_freeze_only": True,
        },
        "phase10b_scope": {
            "docs_report_validator_only": True,
            "input_construction_protocol_freeze_only": True,
            "phase10b_separate_from_phase9_not_continuation": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "frozen_source_eligibility": {
            "source_eligibility_rules": list(SOURCE_ELIGIBILITY_RULES),
            "publication_level": PROTOCOL_PUBLICATION_LEVEL,
            "source_eligibility_decided_before_any_use": True,
            "source_eligibility_drift_is_hard_stop": True,
        },
        "frozen_freshness_fencing": {
            "freshness_fencing_rules": list(FRESHNESS_FENCING_RULES),
            "freshness_verified_before_any_sampling_or_packet_generation": True,
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
            "no_actual_sampling_draw_in_phase10b": True,
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
            "packet_schema_definition_only_no_packets_generated_in_phase10b": True,
            "packet_must_be_independently_generated_in_future_phase10c": True,
        },
        "frozen_privacy_scanner": {
            "privacy_scanner_rules": list(PRIVACY_SCANNER_RULES),
            "gate_exact_values_allowed_only_at_exact_gate_paths": True,
            "reject_exact_count_fields": True,
        },
        "frozen_future_10c_handoff_gates": {
            "future_10c_handoff_gates": list(FUTURE_10C_HANDOFF_GATES),
            "separate_boundary_review_after_phase10b_commit_and_ci_green_before_phase10c": True,
            "phase10b_does_not_authorize_phase10c_execution": True,
        },
        "frozen_forbidden_actions": {
            "forbidden_actions_rules": list(FORBIDDEN_ACTIONS_RULES),
            "no_public_source_discovery_in_phase10b": True,
            "no_repo_source_fetch_clone_or_materialization_in_phase10b": True,
            "no_task_generation_or_sampling_draw_in_phase10b": True,
            "no_real_packet_generation_in_phase10b": True,
        },
        "frozen_no_execution_guardrails": {
            "no_execution_guardrail_rules": list(NO_EXECUTION_GUARDRAIL_RULES),
            "no_execution_no_discovery_no_materialization_in_phase10b": True,
            "no_private_reads_in_phase10b": True,
            "no_source_reads_in_phase10b": True,
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
            "phase10b_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_read_phase10a_private_artifacts": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_generate_tasks": True,
            "validator_does_not_generate_packets": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_generates_tasks": False,
            "validator_generates_packets": False,
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
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") != STATUS:
        errors.append("status drift")

    gate9 = report.get("phase9_closure_gate", {})
    if gate9.get("phase9_closure_commit") != PHASE9_CLOSURE_COMMIT:
        errors.append("Phase 9 closure commit gate reference drift")
    if gate9.get("phase9_closure_ci_run") != PHASE9_CLOSURE_CI_RUN:
        errors.append("Phase 9 closure CI run gate reference drift")
    if gate9.get("phase9_closure_ci_success") is not True:
        errors.append("Phase 9 closure CI success gate missing")
    if gate9.get("phase9_closed") is not True:
        errors.append("Phase 9 closed gate missing")
    for key in ("phase9_closure_gate_required_before_phase10b",
                "phase9r_9s_exact_refs_not_republished_by_phase10b"):
        if gate9.get(key) is not True:
            errors.append(f"Phase 9 closure gate boundary missing: {key}")

    gate10a = report.get("phase10a_gate", {})
    if gate10a.get("phase10a_commit") != PHASE10A_COMMIT:
        errors.append("Phase 10A commit gate reference drift")
    if gate10a.get("phase10a_ci_run") != PHASE10A_CI_RUN:
        errors.append("Phase 10A CI run gate reference drift")
    if gate10a.get("phase10a_ci_success") is not True:
        errors.append("Phase 10A CI success gate missing")
    if gate10a.get("phase10a_status") != PHASE10A_STATUS:
        errors.append("Phase 10A status gate reference drift")
    for key in ("phase10a_gate_required_before_phase10b", "phase10a_protocol_freeze_only"):
        if gate10a.get(key) is not True:
            errors.append(f"Phase 10A gate boundary missing: {key}")

    scope = report.get("phase10b_scope", {})
    for key in ("docs_report_validator_only",
                "input_construction_protocol_freeze_only",
                "phase10b_separate_from_phase9_not_continuation"):
        if scope.get(key) is not True:
            errors.append(f"phase10b_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10b_scope execution boundary failed: {key}")

    sep = report.get("frozen_source_eligibility", {})
    for key in ("source_eligibility_decided_before_any_use",
                "source_eligibility_drift_is_hard_stop"):
        if sep.get(key) is not True:
            errors.append(f"frozen source eligibility boundary missing: {key}")

    ff = report.get("frozen_freshness_fencing", {})
    for key in ("freshness_verified_before_any_sampling_or_packet_generation",
                "fencing_violation_is_hard_stop"):
        if ff.get(key) is not True:
            errors.append(f"frozen freshness fencing boundary missing: {key}")

    ind = report.get("frozen_independence_from_phase9", {})
    for key in ("phase9_artifacts_cannot_be_used_as_validation_evidence",
                "clean_room_operator_must_not_use_memory_of_phase9_private_material"):
        if ind.get(key) is not True:
            errors.append(f"frozen independence from phase9 boundary missing: {key}")

    dos = report.get("frozen_deterministic_ordering_selection", {})
    for key in ("no_actual_sampling_draw_in_phase10b",):
        if dos.get(key) is not True:
            errors.append(f"frozen deterministic ordering boundary missing: {key}")
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
    for key in ("packet_schema_definition_only_no_packets_generated_in_phase10b",
                "packet_must_be_independently_generated_in_future_phase10c"):
        if rps.get(key) is not True:
            errors.append(f"frozen replication packet schema boundary missing: {key}")

    ps = report.get("frozen_privacy_scanner", {})
    for key in ("gate_exact_values_allowed_only_at_exact_gate_paths",
                "reject_exact_count_fields"):
        if ps.get(key) is not True:
            errors.append(f"frozen privacy scanner boundary missing: {key}")

    fc = report.get("frozen_future_10c_handoff_gates", {})
    for key in ("separate_boundary_review_after_phase10b_commit_and_ci_green_before_phase10c",
                "phase10b_does_not_authorize_phase10c_execution"):
        if fc.get(key) is not True:
            errors.append(f"frozen future 10c handoff boundary missing: {key}")

    fa = report.get("frozen_forbidden_actions", {})
    for key in ("no_public_source_discovery_in_phase10b",
                "no_repo_source_fetch_clone_or_materialization_in_phase10b",
                "no_task_generation_or_sampling_draw_in_phase10b",
                "no_real_packet_generation_in_phase10b"):
        if fa.get(key) is not True:
            errors.append(f"frozen forbidden actions boundary missing: {key}")

    ng = report.get("frozen_no_execution_guardrails", {})
    for key in ("no_execution_no_discovery_no_materialization_in_phase10b",
                "no_private_reads_in_phase10b", "no_source_reads_in_phase10b"):
        if ng.get(key) is not True:
            errors.append(f"frozen no-execution guardrail boundary missing: {key}")

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
    for key in ("phase10b_specific_validator_available", "self_test_available",
                "report_validation_available", "validator_does_not_fetch_or_read_private",
                "validator_does_not_read_sources", "validator_does_not_read_ignored_runs",
                "validator_does_not_read_phase9_artifacts",
                "validator_does_not_read_phase10a_private_artifacts",
                "validator_does_not_discover_sources",
                "validator_does_not_materialize_sources",
                "validator_does_not_generate_tasks",
                "validator_does_not_generate_packets",
                "public_artifact_privacy_audit_expected"):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_executes_tasks", "validator_reads_private_registry",
                "validator_reads_sources", "validator_reads_ignored_runs",
                "validator_starts_empirical_work", "validator_discovers_sources",
                "validator_materializes_sources", "validator_generates_tasks",
                "validator_generates_packets"):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

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
    global PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10A_ARTIFACT_READ_ATTEMPTS
    global SOURCE_DISCOVERY_ATTEMPTS, MATERIALIZATION_ATTEMPTS
    global TASK_GENERATION_OR_SAMPLING_ATTEMPTS, PACKET_GENERATION_ATTEMPTS
    global SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10A_ARTIFACT_READ_ATTEMPTS = 0
    SOURCE_DISCOVERY_ATTEMPTS = 0
    MATERIALIZATION_ATTEMPTS = 0
    TASK_GENERATION_OR_SAMPLING_ATTEMPTS = 0
    PACKET_GENERATION_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))
    checks.append(("base_status_equals_required_status", base["status"] == STATUS))
    checks.append(("base_phase_equals_slug", base["phase"] == PHASE))

    # Reject missing/wrong Phase 9 closure gate references.
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

    # Reject missing/wrong Phase 10A gate references.
    for field, bad_val, label in (
        ("phase10a_commit", "deadbeef" * 5, "commit"),
        ("phase10a_ci_run", "0000", "ci_run"),
        ("phase10a_status", "drift", "status"),
    ):
        mutated = copy.deepcopy(base)
        mutated["phase10a_gate"][field] = bad_val
        checks.append((f"wrong_phase10a_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(base)
        del mutated["phase10a_gate"][field]
        checks.append((f"missing_phase10a_{label}_rejected", bool(validate_report(mutated))))

    # Reject gate facts flipped to false.
    for key in ("phase9_closed", "phase9_closure_ci_success",
                "phase9_closure_gate_required_before_phase10b",
                "phase9r_9s_exact_refs_not_republished_by_phase10b",
                "phase10a_ci_success", "phase10a_gate_required_before_phase10b",
                "phase10a_protocol_freeze_only"):
        section = "phase9_closure_gate" if key.startswith("phase9_") or key == "phase9_closed" else "phase10a_gate"
        mutated = copy.deepcopy(base)
        mutated[section][key] = False
        checks.append((f"{section}_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema drift.
    for field, bad in (("status", "drift"), ("phase", "drift"), ("schema_version", "drift")):
        mutated = copy.deepcopy(base)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # Reject execution booleans true.
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["phase10b_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject exact count fields.
    mutated = copy.deepcopy(base)
    mutated["phase10b_scope"]["count"] = 48
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
        mutated = copy.deepcopy(base)
        mutated["phase10b_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "source_path_bucket", "path", "repo_name", "task_id", "row_id",
        "packet_id", "manifest", "run_dir",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase10b_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject forbidden keys.
    for bad_key in ("correctness_threshold", "adjudication_threshold", "decision_threshold",
                    "novel_metric_bucket", "subgroup_breakdown"):
        mutated = copy.deepcopy(base)
        mutated["frozen_source_eligibility"][bad_key] = "example"
        checks.append((f"forbidden_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject unknown closed-list members (set-equality).
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

    # Reject reworded closed-list member.
    mutated = copy.deepcopy(base)
    mutated["frozen_source_eligibility"]["source_eligibility_rules"][0] = "looks_good_after_review"
    checks.append(("source_eligibility_vocabulary_drift_rejected", bool(validate_report(mutated))))

    # Reject future execution freeze/run wording in 10B.
    mutated = copy.deepcopy(base)
    mutated["frozen_future_10c_handoff_gates"]["future_10c_handoff_gates"].append("phase10b_authorizes_phase10c_execution_now")
    checks.append(("future_execution_authorized_in_10b_rejected", bool(validate_report(mutated))))

    # Reject caps drift.
    mutated = copy.deepcopy(base)
    mutated["frozen_caps_and_abort_limits"]["caps"]["candidate_inspection_cap_total"] = 96
    checks.append(("caps_drift_rejected", bool(validate_report(mutated))))

    # Reject seed label drift.
    mutated = copy.deepcopy(base)
    mutated["frozen_deterministic_ordering_selection"]["predeclared_seed_label"] = "wrong_seed"
    checks.append(("seed_label_drift_rejected", bool(validate_report(mutated))))

    # Reject channel order drift.
    mutated = copy.deepcopy(base)
    mutated["frozen_deterministic_ordering_selection"]["channel_order"] = list(reversed(CHANNEL_ORDER))
    checks.append(("channel_order_drift_rejected", bool(validate_report(mutated))))

    # Reject claim boundary true.
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject privacy contract violations.
    for privacy_key in (
        "per_source_public_facts", "per_task_public_facts",
        "run_locations_public", "repo_names_public",
        "packet_ids_public", "exact_counts_or_rates_public", "singleton_buckets_public",
        "phase9_private_artifacts_public", "phase10a_private_artifacts_public",
        "source_urls_public", "candidate_repo_names_public",
    ):
        mutated = copy.deepcopy(base)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(base)
        mutated["frozen_source_eligibility"]["source_eligibility_rules"].append(singleton_val)
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # Reject claim-making wording.
    for phrase in ("method effectiveness", "product readiness", "scoring success", "outcome success",
                   "evaluation works", "acquisition success", "adjudication proven",
                   "correctness proven", "evidence_success achieved", "lift achieved",
                   "generalized success", "evidence-acquisition success", "validation proven"):
        mutated = copy.deepcopy(base)
        mutated["frozen_source_eligibility"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # Reject user-approval wording.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    # Reject placeholder wording.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(base)
        mutated["frozen_source_eligibility"]["source_eligibility_rules"].append(phrase)
        checks.append((f"placeholder_{phrase}_rejected", bool(validate_report(mutated))))

    # Reject truth-boundary violation.
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["truth_boundary"][key] = False
        checks.append((f"truth_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Reject unknown fields.
    mutated = copy.deepcopy(base)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase10b_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_source_eligibility"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_eligibility_rejected", bool(validate_report(mutated))))

    # Reject non-gate hash/CI values.
    mutated = copy.deepcopy(base)
    mutated["phase10b_scope"]["task_ci_run"] = "29002587099"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    checks.append(("non_whitelisted_ci_run_key_not_exempt", any("private-shaped public key" in e for e in errors)))

    mutated = copy.deepcopy(base)
    mutated["phase10b_scope"]["example_hash"] = "67e8d984601d82a2a97992bb83fda06b09e06be0"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    checks.append(("gate_ref_commit_values_on_whitelisted_paths_valid",
                   not validate_report(base)))

    # Path guard tests.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10b" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9r_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10a_independent_validation_protocol_freeze_no_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10b" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Temp-file round-trip (synthetic fixture only, no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10b_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

        runs_tmp = Path(tmp) / "runs" / "report.json"
        runs_tmp.parent.mkdir(parents=True, exist_ok=True)
        runs_tmp.write_text(json.dumps(base), encoding="utf-8")
        ok, _ = _validate_report_path_is_public(runs_tmp)
        checks.append(("validate_report_rejects_temp_runs_path", not ok))

    # Prove the validator/self-test did not fetch/read/private/execute.
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_sources", SOURCE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9_artifacts",
                   PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10a_artifacts",
                   PRIVATE_PHASE10A_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_discover_sources", SOURCE_DISCOVERY_ATTEMPTS == 0))
    checks.append(("selftest_does_not_materialize", MATERIALIZATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_tasks_or_samples",
                   TASK_GENERATION_OR_SAMPLING_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_packets", PACKET_GENERATION_ATTEMPTS == 0))
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
        description="Phase 10B fresh/fenced input-construction protocol freeze (no claim)"
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
