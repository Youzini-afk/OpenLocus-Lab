#!/usr/bin/env python3
"""Phase 9M outcome-observable acquisition route protocol freeze.

This is a docs/report/validator-only protocol freeze.  It freezes ONE explicit
authorized outcome-observable acquisition route for a future Phase 9N before
any outcome observable is visible.  It does NOT fetch, clone, read, or
materialize any repository or source, does NOT read ignored ``runs/`` or
private candidate pools/registries/manifests, the Phase 9H private materialized
sources, the Phase 9J private annotation-input rows/manifests, or the Phase 9L
private outcome-acquisition packets/manifests, does NOT execute the frozen route
or any extraction/acquisition method, does NOT acquire outcome observables, and
does NOT score, adjudicate, or generate gold/benchmark labels, evidence_success,
result labels, annotation-truth, or scoring/evaluation rows.  It makes no
method/product/performance/model/provider/training/runtime/default/scoring/
outcome/evidence-success/annotation-truth/adjudication/correctness claim.

It includes the Phase 9L closeout statement inside 9M: Phase 9J annotation-input
rows alone cannot expose outcome observables (they are routing/precondition
metadata only, not benchmark truth); Phase 9L all-unavailable packets are
acquisition-state records, not failures/successes/performance evidence; no
scoring denominator exists.  Phase 9M is therefore a NEW authorized route
freeze only.

The Phase 9L and Phase 9K public gate reference values (remote commits and CI
runs) are the only public gate references published by Phase 9M.  Phase 9H,
Phase 9I, Phase 9J, Phase 9G, and Phase 9F are carried as bucketed inherited
provenance only and their exact remote commit/CI run values are intentionally
NOT published in the Phase 9M report/docs (tighter privacy).  Local same-tree
git commits are not read or compared; the supplied confirmation values are
matched against the frozen public gate constants only.

Truth-boundary is explicit: the frozen route is a protocol, not an executed
acquisition; authorized input != outcome observable; extraction procedure !=
acquired outcome; observable definition != gold evidence; route fallback rule !=
trying routes until one works; denominator rule != a scoring denominator.
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

# Compact Phase 9M slug (kept short so the absolute artifact report path stays
# comfortably under the Windows MAX_PATH (260) limit).  Boundary wording in the
# report body/docs is NOT weakened -- only the path-dependent slug is shortened.
PHASE = "phase9m_outcome_route_protocol_freeze_no_claim"
# Honest freeze wording: the outcome-observable acquisition ROUTE PROTOCOL is
# frozen (no execution, no scoring, no adjudication, no claim).  Not
# "success"/"validated"/"acquired"/"benchmark" (forbidden wording); "freeze"
# honestly reflects that only the route protocol is frozen, with no execution
# of the route and no outcome/scoring/adjudication/evidence_success.
STATUS = (
    "phase9m_outcome_observable_acquisition_route_protocol_freeze"
    "_no_execution_no_scoring_no_adjudication_no_claim"
)
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

# ---------------------------------------------------------------------------
# Phase 9L public gate reference values (oracle-provided).  Local same-tree
# git commits are not read or compared; the supplied confirmation values are
# matched against the frozen public gate constants only.
PHASE9L_STATUS = (
    "phase9l_outcome_acquisition_executed_unavailable_only"
    "_no_scoring_no_adjudication_no_claim"
)
PHASE9L_COMMIT = "c815a77d4dea3b77efe5dae0abe06006045294e9"
PHASE9L_CI_RUN = "28983185765"

# Phase 9K public gate reference values (oracle-provided).
PHASE9K_STATUS = "phase9k_outcome_scoring_protocol_freeze_no_claim"
PHASE9K_COMMIT = "233a16e6672b05b87b09be5b920f8fc9dd72e274"
PHASE9K_CI_RUN = "28981994749"

# Phase 9H/9I/9J inherited provenance (carried forward, bucketed only).  The
# exact Phase 9H/9I/9J remote commit/CI run values are intentionally NOT
# published in the Phase 9M report/docs; they are carried as bucketed inherited
# provenance only (tighter privacy).  Only the Phase 9L and Phase 9K full
# commit SHAs / CI runs are public gate references.
PHASE9H_STATUS = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_readiness_no_scoring_no_claim"
)
PHASE9I_STATUS = (
    "phase9i_materialized_inventory_to_task_annotation_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9J_STATUS = "phase9j_annotation_input_rows_generated_no_scoring_no_claim"

# Phase 9G/9F inherited provenance (carried forward, bucketed only).
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

# ---------------------------------------------------------------------------
# Frozen outcome-observable acquisition route (single fixed deterministic
# route, no fallback, no retry, no LLM/provider).  These closed lists are
# validator-checked for set-equality (no missing/extra members) and for
# private-shaped tokens in list values.
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

# Frozen no-p-hacking guardrails.
NO_P_HACKING_GUARDRAIL_RULES = (
    "no_private_or_source_inspection_during_phase9m",
    "no_tuning_definitions_after_observables_visible",
    "no_denominator_or_inclusion_changes_after_acquisition",
    "no_subgroup_changes_after_acquisition",
    "single_route_order_and_failure_transitions_frozen_now_no_drift",
    "no_trying_routes_until_one_works_unless_pre_frozen",
)

# Frozen privacy rules.
PRIVACY_RULES = (
    "public_aggregate_or_bucketed_only",
    "no_repo_source_url_owner_commit_beyond_whitelisted_phase9l_phase9k_gate_refs",
    "no_path_snippet_row_task_manifest_run_locations_public",
    "no_per_source_or_per_task_facts_public",
    "no_singleton_buckets_public",
)

# Frozen denominator rules.
DENOMINATOR_RULES = (
    "acquired_outcomes_may_become_future_denominator_only_under_later_frozen_scoring_phase",
    "unavailable_outcomes_outside_scoring_or_adjudication_denominators"
    "_unless_pre_frozen_missingness_analysis_reports_aggregate_acquisition_availability",
    "never_count_unavailable_as_failure_or_success_or_partial_or_evidence_success",
    "no_scoring_denominator_exists_in_phase9m",
)

# Frozen future sequence rules.
FUTURE_SEQUENCE_RULES = (
    "phase9m_freeze_only",
    "phase9n_execute_frozen_route_only_private_outputs_under_ignored_runs"
    "_aggregate_public_availability_report_only",
    "phase9o_scoring_protocol_or_denominator_freeze_only_if_nonzero_valid_acquired_outcomes_exist",
    "phase9p_plus_scoring_or_adjudication_under_separate_frozen_boundaries",
    "no_scoring_or_adjudication_execution_in_phase9m",
)

# Truth-boundary attestation keys that must always be True in the public report.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "frozen_route_is_protocol_not_executed_acquisition",
    "authorized_input_is_not_outcome_observable",
    "extraction_procedure_is_not_acquired_outcome",
    "observable_definition_is_not_gold_evidence",
    "route_fallback_rule_is_not_trying_routes_until_one_works",
    "denominator_rule_is_not_a_scoring_denominator",
)

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "outcome_route_executed",
    "outcome_observables_acquired",
    "outcome_acquisition_method_executed",
    "task_annotation_generated",
    "private_phase9h_materialized_sources_read",
    "private_phase9j_annotation_input_rows_read",
    "private_phase9l_outcome_packets_read",
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
    "result_labels_generated",
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
    "outcome_observables_public",
    "outcome_packets_public",
)

# Forbidden public field words; only apply to non-boolean values at
# non-allowed-schema paths so boolean boundary attestation keys such as
# ``scoring_executed`` and section names such as ``frozen_denominator_rule``
# (which are at allowed-schema paths) are not false-flagged.
FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

# Closed protocol lists whose members are validator set-equality checked.
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

# Claim-making wording that must never appear as an exposed value.
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
    r"|route\s+(?:works|succeeded|proven|established)"
    r"|acquisition\s+success"
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
    r"|path|range|snippet|task_id|row_id"
    r"|manifest|run_dir|per_source|per_task)",
    re.IGNORECASE,
)

# Defense-in-depth: scan list string values for private-shaped tokens even
# though closed protocol lists already reject extra members via set-equality.
LIST_VALUE_PRIVATE_TOKEN_RE = re.compile(
    r"(?:task_id|row_id|run_dir|source_path"
    r"|manifest_path|candidate_id|commit_sha)",
    re.IGNORECASE,
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants (full commit SHA / CI run ID).  Only the Phase 9L and
# Phase 9K commit/CI paths are exempt from the private-shaped value scan.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9l_gate_references.phase9l_commit",
        "$.phase9l_gate_references.phase9l_ci_run",
        "$.phase9k_gate_references.phase9k_commit",
        "$.phase9k_gate_references.phase9k_ci_run",
    }
)

# Exact public gate-reference JSON paths whose string VALUES are CI run IDs
# (long decimal integers).  Only the Phase 9L and Phase 9K CI run paths are
# exempt from the long-decimal value scan.
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9l_gate_references.phase9l_ci_run",
        "$.phase9k_gate_references.phase9k_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0


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
    "phase9h_inherited_provenance": {
        "phase9h_status": None,
        "phase9h_ci_success": None,
        "phase9h_source_materialization_readiness_only": None,
        "phase9h_remote_provenance_bucketed": None,
        "phase9h_carried_as_inherited_provenance_only": None,
    },
    "phase9i_inherited_provenance": {
        "phase9i_status": None,
        "phase9i_ci_success": None,
        "phase9i_protocol_freeze": None,
        "phase9i_remote_provenance_bucketed": None,
        "phase9i_carried_as_inherited_provenance_only": None,
    },
    "phase9j_inherited_provenance": {
        "phase9j_status": None,
        "phase9j_ci_success": None,
        "phase9j_annotation_input_rows_generated": None,
        "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": None,
        "phase9j_remote_provenance_bucketed": None,
        "phase9j_carried_as_inherited_provenance_only": None,
    },
    "phase9k_gate_references": {
        "phase9k_commit": None,
        "phase9k_ci_run": None,
        "phase9k_ci_success": None,
        "phase9k_status": None,
        "phase9k_protocol_freeze": None,
        "phase9k_outcome_acquisition_protocol_frozen": None,
        "phase9k_did_not_acquire_outcomes_or_score_or_adjudicate_or_generate_gold_rows": None,
        "phase9k_not_proof_outcome_or_scoring_or_evidence_success_works": None,
        "phase9k_gate_required_before_phase9m": None,
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
        "phase9l_did_not_score_or_adjudicate_or_generate_gold_rows": None,
        "phase9l_not_proof_outcome_or_scoring_or_evidence_success_works": None,
        "phase9l_gate_required_before_phase9m": None,
    },
    "phase9l_closeout_statement": {
        "phase9j_rows_alone_cannot_expose_outcome_observables": None,
        "phase9l_all_unavailable_packets_are_acquisition_state_records_not_failures_or_successes_or_performance_evidence": None,
        "phase9l_no_scoring_denominator_exists": None,
        "phase9l_outcome_acquisition_packets_are_acquisition_state_only_not_scoring_not_adjudication_not_evidence_success": None,
    },
    "phase9m_scope": {
        "docs_report_validator_only": None,
        "protocol_freeze_only": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "outcome_route_executed": None,
        "outcome_observables_acquired": None,
        "outcome_acquisition_method_executed": None,
        "task_annotation_generated": None,
        "private_phase9h_materialized_sources_read": None,
        "private_phase9j_annotation_input_rows_read": None,
        "private_phase9l_outcome_packets_read": None,
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
        "result_labels_generated": None,
        "model_fitting": None,
        "provider_or_llm_calls": None,
        "runtime_default_or_product_changes": None,
        "network_fetch_or_clone_or_source_refresh_executed": None,
        "future_execution_requires_phase9m_commit_and_ci_green": None,
    },
    "frozen_outcome_observable_acquisition_route": {
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
        "future_phase9n_boundary": None,
        "inherited_phase9h_aggregate_caps": {
            "target_inventory_bucket": None,
            "hard_cap_bucket": None,
            "per_source_cap_bucket": None,
            "minimum_distinct_sources_bucket": None,
        },
    },
    "frozen_no_p_hacking_guardrails": {
        "guardrail_rules": None,
        "no_private_or_source_inspection_during_phase9m": None,
        "no_tuning_definitions_after_observables_visible": None,
        "no_denominator_or_inclusion_changes_after_acquisition": None,
        "no_subgroup_changes_after_acquisition": None,
        "single_route_order_and_failure_transitions_frozen_now": None,
    },
    "frozen_privacy": {
        "privacy_rules": None,
        "public_aggregate_or_bucketed_only": None,
        "no_repo_source_url_owner_commit_beyond_whitelisted_phase_gates": None,
        "no_path_snippet_row_task_manifest_run_locations": None,
        "no_per_source_or_per_task_facts": None,
        "no_singleton_buckets": None,
    },
    "frozen_denominator_rule": {
        "denominator_rules": None,
        "acquired_outcomes_may_become_future_denominator_only_under_later_frozen_scoring_phase": None,
        "unavailable_outcomes_outside_scoring_or_adjudication_denominators_unless_pre_frozen_missingness_analysis_reports_aggregate_acquisition_availability": None,
        "never_count_unavailable_as_failure_or_success_or_partial_or_evidence_success": None,
    },
    "frozen_future_sequence": {
        "sequence_rules": None,
        "phase9m_freeze_only": None,
        "phase9n_execute_frozen_route_only_private_outputs_under_ignored_runs_aggregate_public_availability_report_only": None,
        "phase9o_scoring_protocol_or_denominator_freeze_only_if_nonzero_valid_acquired_outcomes_exist": None,
        "phase9p_plus_scoring_or_adjudication_under_separate_frozen_boundaries": None,
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
        "validator_does_not_read_phase9h_materialized_sources": None,
        "validator_does_not_read_phase9j_annotation_input_rows": None,
        "validator_does_not_read_phase9l_outcome_packets": None,
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

    The report path must be under the Phase 9M public artifact directory
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
        return False, "report path is not under the Phase 9M public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report() -> dict[str, Any]:
    """Build the frozen Phase 9M public protocol report.

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
            "phase9g_remote_provenance_bucketed": True,
            "phase9g_carried_as_inherited_provenance_only": True,
        },
        "phase9h_inherited_provenance": {
            "phase9h_status": PHASE9H_STATUS,
            "phase9h_ci_success": True,
            "phase9h_source_materialization_readiness_only": True,
            "phase9h_remote_provenance_bucketed": True,
            "phase9h_carried_as_inherited_provenance_only": True,
        },
        "phase9i_inherited_provenance": {
            "phase9i_status": PHASE9I_STATUS,
            "phase9i_ci_success": True,
            "phase9i_protocol_freeze": True,
            "phase9i_remote_provenance_bucketed": True,
            "phase9i_carried_as_inherited_provenance_only": True,
        },
        "phase9j_inherited_provenance": {
            "phase9j_status": PHASE9J_STATUS,
            "phase9j_ci_success": True,
            "phase9j_annotation_input_rows_generated": True,
            "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth": True,
            "phase9j_remote_provenance_bucketed": True,
            "phase9j_carried_as_inherited_provenance_only": True,
        },
        "phase9k_gate_references": {
            "phase9k_commit": PHASE9K_COMMIT,
            "phase9k_ci_run": PHASE9K_CI_RUN,
            "phase9k_ci_success": True,
            "phase9k_status": PHASE9K_STATUS,
            "phase9k_protocol_freeze": True,
            "phase9k_outcome_acquisition_protocol_frozen": True,
            "phase9k_did_not_acquire_outcomes_or_score_or_adjudicate_or_generate_gold_rows": True,
            "phase9k_not_proof_outcome_or_scoring_or_evidence_success_works": True,
            "phase9k_gate_required_before_phase9m": True,
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
            "phase9l_did_not_score_or_adjudicate_or_generate_gold_rows": True,
            "phase9l_not_proof_outcome_or_scoring_or_evidence_success_works": True,
            "phase9l_gate_required_before_phase9m": True,
        },
        "phase9l_closeout_statement": {
            "phase9j_rows_alone_cannot_expose_outcome_observables": True,
            "phase9l_all_unavailable_packets_are_acquisition_state_records_not_failures_or_successes_or_performance_evidence": True,
            "phase9l_no_scoring_denominator_exists": True,
            "phase9l_outcome_acquisition_packets_are_acquisition_state_only_not_scoring_not_adjudication_not_evidence_success": True,
        },
        "phase9m_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "outcome_route_executed": False,
            "outcome_observables_acquired": False,
            "outcome_acquisition_method_executed": False,
            "task_annotation_generated": False,
            "private_phase9h_materialized_sources_read": False,
            "private_phase9j_annotation_input_rows_read": False,
            "private_phase9l_outcome_packets_read": False,
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
            "result_labels_generated": False,
            "model_fitting": False,
            "provider_or_llm_calls": False,
            "runtime_default_or_product_changes": False,
            "network_fetch_or_clone_or_source_refresh_executed": False,
            "future_execution_requires_phase9m_commit_and_ci_green": True,
        },
        "frozen_outcome_observable_acquisition_route": {
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
            "future_phase9n_boundary": True,
            "inherited_phase9h_aggregate_caps": {
                "target_inventory_bucket": "bucket_48_to_72",
                "hard_cap_bucket": "bucket_up_to_96",
                "per_source_cap_bucket": "bucket_up_to_8",
                "minimum_distinct_sources_bucket": "bucket_at_least_8",
            },
        },
        "frozen_no_p_hacking_guardrails": {
            "guardrail_rules": list(NO_P_HACKING_GUARDRAIL_RULES),
            "no_private_or_source_inspection_during_phase9m": True,
            "no_tuning_definitions_after_observables_visible": True,
            "no_denominator_or_inclusion_changes_after_acquisition": True,
            "no_subgroup_changes_after_acquisition": True,
            "single_route_order_and_failure_transitions_frozen_now": True,
        },
        "frozen_privacy": {
            "privacy_rules": list(PRIVACY_RULES),
            "public_aggregate_or_bucketed_only": True,
            "no_repo_source_url_owner_commit_beyond_whitelisted_phase_gates": True,
            "no_path_snippet_row_task_manifest_run_locations": True,
            "no_per_source_or_per_task_facts": True,
            "no_singleton_buckets": True,
        },
        "frozen_denominator_rule": {
            "denominator_rules": list(DENOMINATOR_RULES),
            "acquired_outcomes_may_become_future_denominator_only_under_later_frozen_scoring_phase": True,
            "unavailable_outcomes_outside_scoring_or_adjudication_denominators_unless_pre_frozen_missingness_analysis_reports_aggregate_acquisition_availability": True,
            "never_count_unavailable_as_failure_or_success_or_partial_or_evidence_success": True,
        },
        "frozen_future_sequence": {
            "sequence_rules": list(FUTURE_SEQUENCE_RULES),
            "phase9m_freeze_only": True,
            "phase9n_execute_frozen_route_only_private_outputs_under_ignored_runs_aggregate_public_availability_report_only": True,
            "phase9o_scoring_protocol_or_denominator_freeze_only_if_nonzero_valid_acquired_outcomes_exist": True,
            "phase9p_plus_scoring_or_adjudication_under_separate_frozen_boundaries": True,
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
            "validator_does_not_read_phase9h_materialized_sources": True,
            "validator_does_not_read_phase9j_annotation_input_rows": True,
            "validator_does_not_read_phase9l_outcome_packets": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": (
            "phase9m_freezes_outcome_observable_acquisition_route_protocol_only"
            "_no_execution_no_scoring_no_adjudication_no_claim"
            "_phase9n_may_execute_frozen_route_only_under_separate_boundary"
            "_no_method_product_claim"
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

    # Phase 9G inherited provenance
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

    # Phase 9H inherited provenance (bucketed only).
    prov9h = report.get("phase9h_inherited_provenance", {})
    if prov9h.get("phase9h_status") != PHASE9H_STATUS:
        errors.append("Phase 9H inherited status drift")
    if prov9h.get("phase9h_ci_success") is not True:
        errors.append("Phase 9H inherited CI success missing")
    if prov9h.get("phase9h_source_materialization_readiness_only") is not True:
        errors.append("Phase 9H inherited readiness-only boundary missing")
    if prov9h.get("phase9h_remote_provenance_bucketed") is not True:
        errors.append("Phase 9H inherited remote provenance must be bucketed")
    if prov9h.get("phase9h_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9H inherited provenance-only boundary missing")

    # Phase 9I inherited provenance (bucketed only).
    prov9i = report.get("phase9i_inherited_provenance", {})
    if prov9i.get("phase9i_status") != PHASE9I_STATUS:
        errors.append("Phase 9I inherited status drift")
    if prov9i.get("phase9i_ci_success") is not True:
        errors.append("Phase 9I inherited CI success missing")
    if prov9i.get("phase9i_protocol_freeze") is not True:
        errors.append("Phase 9I inherited protocol freeze missing")
    if prov9i.get("phase9i_remote_provenance_bucketed") is not True:
        errors.append("Phase 9I inherited remote provenance must be bucketed")
    if prov9i.get("phase9i_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9I inherited provenance-only boundary missing")

    # Phase 9J inherited provenance (bucketed only).
    prov9j = report.get("phase9j_inherited_provenance", {})
    if prov9j.get("phase9j_status") != PHASE9J_STATUS:
        errors.append("Phase 9J inherited status drift")
    if prov9j.get("phase9j_ci_success") is not True:
        errors.append("Phase 9J inherited CI success missing")
    if prov9j.get("phase9j_annotation_input_rows_generated") is not True:
        errors.append("Phase 9J inherited annotation-input rows generated missing")
    if prov9j.get("phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth") is not True:
        errors.append("Phase 9J inherited routing-precondition-only boundary missing")
    if prov9j.get("phase9j_remote_provenance_bucketed") is not True:
        errors.append("Phase 9J inherited remote provenance must be bucketed")
    if prov9j.get("phase9j_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9J inherited provenance-only boundary missing")

    # Phase 9K gate references (whitelisted public gate refs).
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
    if gate9k.get("phase9k_did_not_acquire_outcomes_or_score_or_adjudicate_or_generate_gold_rows") is not True:
        errors.append("Phase 9K no-generation boundary missing")
    if gate9k.get("phase9k_not_proof_outcome_or_scoring_or_evidence_success_works") is not True:
        errors.append("Phase 9K not-proof boundary missing")
    if gate9k.get("phase9k_gate_required_before_phase9m") is not True:
        errors.append("Phase 9K gate-required boundary missing")

    # Phase 9L gate references (whitelisted public gate refs).
    gate9l = report.get("phase9l_gate_references", {})
    if gate9l.get("phase9l_commit") != PHASE9L_COMMIT:
        errors.append("Phase 9L commit gate reference drift")
    if gate9l.get("phase9l_ci_run") != PHASE9L_CI_RUN:
        errors.append("Phase 9L CI run gate reference drift")
    if gate9l.get("phase9l_ci_success") is not True:
        errors.append("Phase 9L CI success gate missing")
    if gate9l.get("phase9l_status") != PHASE9L_STATUS:
        errors.append("Phase 9L status gate reference drift")
    if gate9l.get("phase9l_outcome_acquisition_protocol_frozen") is not True:
        errors.append("Phase 9L outcome-acquisition protocol frozen boundary missing")
    if gate9l.get("phase9l_all_unavailable_only_under_phase9k_missing_outcome_rule") is not True:
        errors.append("Phase 9L all-unavailable boundary missing")
    if gate9l.get("phase9l_outcome_packets_are_acquisition_state_only_not_scoring_not_adjudication") is not True:
        errors.append("Phase 9L acquisition-state-only boundary missing")
    if gate9l.get("phase9l_no_scoring_denominator_exists") is not True:
        errors.append("Phase 9L no-scoring-denominator boundary missing")
    if gate9l.get("phase9l_did_not_score_or_adjudicate_or_generate_gold_rows") is not True:
        errors.append("Phase 9L no-generation boundary missing")
    if gate9l.get("phase9l_not_proof_outcome_or_scoring_or_evidence_success_works") is not True:
        errors.append("Phase 9L not-proof boundary missing")
    if gate9l.get("phase9l_gate_required_before_phase9m") is not True:
        errors.append("Phase 9L gate-required boundary missing")

    # Phase 9L closeout statement (inside 9M).
    closeout = report.get("phase9l_closeout_statement", {})
    if closeout.get("phase9j_rows_alone_cannot_expose_outcome_observables") is not True:
        errors.append("Phase 9L closeout: phase9j-rows-alone boundary missing")
    if closeout.get("phase9l_all_unavailable_packets_are_acquisition_state_records_not_failures_or_successes_or_performance_evidence") is not True:
        errors.append("Phase 9L closeout: all-unavailable acquisition-state-only boundary missing")
    if closeout.get("phase9l_no_scoring_denominator_exists") is not True:
        errors.append("Phase 9L closeout: no-scoring-denominator boundary missing")
    if closeout.get("phase9l_outcome_acquisition_packets_are_acquisition_state_only_not_scoring_not_adjudication_not_evidence_success") is not True:
        errors.append("Phase 9L closeout: acquisition-state-only-not-evidence-success boundary missing")

    # Phase 9M scope
    scope = report.get("phase9m_scope", {})
    for key in ("docs_report_validator_only", "protocol_freeze_only"):
        if scope.get(key) is not True:
            errors.append(f"phase9m scope missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase9m execution boundary failed: {key}")
    if scope.get("future_execution_requires_phase9m_commit_and_ci_green") is not True:
        errors.append("phase9m future execution commit+CI-green boundary missing")

    # Frozen outcome-observable acquisition route
    route = report.get("frozen_outcome_observable_acquisition_route", {})
    if route.get("publication_level") != ROUTE_PUBLICATION_LEVEL:
        errors.append("route publication level drift")
    if route.get("route_form") != ROUTE_FORM:
        errors.append("route form drift")
    for key, expected in CLOSED_ROUTE_LISTS:
        errors.extend(_check_closed_list(route.get(key), expected, "frozen_outcome_observable_acquisition_route", key))
    if route.get("no_trying_routes_until_one_works_unless_pre_frozen") is not True:
        errors.append("route no-trying-routes boundary missing")
    if route.get("no_llm_no_provider_frozen") is not True:
        errors.append("route no-llm-no-provider boundary missing")
    if route.get("future_phase9n_boundary") is not True:
        errors.append("route future phase9n boundary missing")
    caps = route.get("inherited_phase9h_aggregate_caps", {})
    expected_caps = {
        "target_inventory_bucket": "bucket_48_to_72",
        "hard_cap_bucket": "bucket_up_to_96",
        "per_source_cap_bucket": "bucket_up_to_8",
        "minimum_distinct_sources_bucket": "bucket_at_least_8",
    }
    for cap_key, expected in expected_caps.items():
        if caps.get(cap_key) != expected:
            errors.append(f"inherited phase9h aggregate cap drift: {cap_key}")

    # Frozen no-p-hacking guardrails
    guard = report.get("frozen_no_p_hacking_guardrails", {})
    errors.extend(_check_closed_list(guard.get("guardrail_rules"), NO_P_HACKING_GUARDRAIL_RULES, "frozen_no_p_hacking_guardrails", "guardrail_rules"))
    for key in (
        "no_private_or_source_inspection_during_phase9m",
        "no_tuning_definitions_after_observables_visible",
        "no_denominator_or_inclusion_changes_after_acquisition",
        "no_subgroup_changes_after_acquisition",
        "single_route_order_and_failure_transitions_frozen_now",
    ):
        if guard.get(key) is not True:
            errors.append(f"no-p-hacking guardrail missing: {key}")

    # Frozen privacy
    priv = report.get("frozen_privacy", {})
    errors.extend(_check_closed_list(priv.get("privacy_rules"), PRIVACY_RULES, "frozen_privacy", "privacy_rules"))
    for key in (
        "public_aggregate_or_bucketed_only",
        "no_repo_source_url_owner_commit_beyond_whitelisted_phase_gates",
        "no_path_snippet_row_task_manifest_run_locations",
        "no_per_source_or_per_task_facts",
        "no_singleton_buckets",
    ):
        if priv.get(key) is not True:
            errors.append(f"frozen privacy rule missing: {key}")

    # Frozen denominator rule
    denom = report.get("frozen_denominator_rule", {})
    errors.extend(_check_closed_list(denom.get("denominator_rules"), DENOMINATOR_RULES, "frozen_denominator_rule", "denominator_rules"))
    for key in (
        "acquired_outcomes_may_become_future_denominator_only_under_later_frozen_scoring_phase",
        "unavailable_outcomes_outside_scoring_or_adjudication_denominators_unless_pre_frozen_missingness_analysis_reports_aggregate_acquisition_availability",
        "never_count_unavailable_as_failure_or_success_or_partial_or_evidence_success",
    ):
        if denom.get(key) is not True:
            errors.append(f"frozen denominator rule missing: {key}")

    # Frozen future sequence
    seq = report.get("frozen_future_sequence", {})
    errors.extend(_check_closed_list(seq.get("sequence_rules"), FUTURE_SEQUENCE_RULES, "frozen_future_sequence", "sequence_rules"))
    for key in (
        "phase9m_freeze_only",
        "phase9n_execute_frozen_route_only_private_outputs_under_ignored_runs_aggregate_public_availability_report_only",
        "phase9o_scoring_protocol_or_denominator_freeze_only_if_nonzero_valid_acquired_outcomes_exist",
        "phase9p_plus_scoring_or_adjudication_under_separate_frozen_boundaries",
    ):
        if seq.get(key) is not True:
            errors.append(f"frozen future sequence rule missing: {key}")

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
        "validator_does_not_read_phase9h_materialized_sources",
        "validator_does_not_read_phase9j_annotation_input_rows",
        "validator_does_not_read_phase9l_outcome_packets",
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
        "phase9m_freezes_outcome_observable_acquisition_route_protocol_only"
        "_no_execution_no_scoring_no_adjudication_no_claim"
        "_phase9n_may_execute_frozen_route_only_under_separate_boundary"
        "_no_method_product_claim"
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
    global PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    global PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))
    checks.append(("base_status_equals_required_status", base["status"] == STATUS))
    checks.append(("base_phase_equals_slug", base["phase"] == PHASE))

    # Reject missing/wrong Phase 9L and Phase 9K gate references.
    for gate_section, commit_key, ci_key, status_key, commit_val, ci_val, status_val in (
        ("phase9l_gate_references", "phase9l_commit", "phase9l_ci_run", "phase9l_status", PHASE9L_COMMIT, PHASE9L_CI_RUN, PHASE9L_STATUS),
        ("phase9k_gate_references", "phase9k_commit", "phase9k_ci_run", "phase9k_status", PHASE9K_COMMIT, PHASE9K_CI_RUN, PHASE9K_STATUS),
    ):
        mutated = copy.deepcopy(base)
        del mutated[gate_section][commit_key]
        checks.append((f"missing_{commit_key}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        del mutated[gate_section][ci_key]
        checks.append((f"missing_{ci_key}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        mutated[gate_section][commit_key] = "deadbeef" * 5
        checks.append((f"wrong_{commit_key}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        mutated[gate_section][ci_key] = "0000"
        checks.append((f"wrong_{ci_key}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        mutated[gate_section][status_key] = "drift"
        checks.append((f"wrong_{status_key}_rejected", bool(validate_report(mutated))))

    # Reject re-introduction of an exact Phase 9H/9I/9J commit/CI field
    # (the exact Phase 9H/9I/9J remote commit/CI run values are intentionally
    # NOT published; bucketed inherited provenance only).
    for prov_section, commit_key in (
        ("phase9h_inherited_provenance", "phase9h_commit"),
        ("phase9i_inherited_provenance", "phase9i_commit"),
        ("phase9j_inherited_provenance", "phase9j_commit"),
    ):
        mutated = copy.deepcopy(base)
        mutated[prov_section][commit_key] = "d997caab5487e66c544f657645d70c97f3b780e2"
        checks.append((f"{prov_section}_{commit_key}_field_rejected", bool(validate_report(mutated))))

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

    # Reject Phase 9L closeout statement violation.
    mutated = copy.deepcopy(base)
    mutated["phase9l_closeout_statement"]["phase9j_rows_alone_cannot_expose_outcome_observables"] = False
    checks.append(("closeout_phase9j_rows_boundary_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9l_closeout_statement"]["phase9l_no_scoring_denominator_exists"] = False
    checks.append(("closeout_no_denominator_boundary_rejected", bool(validate_report(mutated))))

    # Reject execution booleans set to true (execution/private-read/source-read/
    # network/provider/LLM/scoring/adjudication/evidence_success/gold/result
    # labels all rejected).
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["phase9m_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Targeted: private reads rejected.
    for private_read_key in (
        "private_phase9h_materialized_sources_read",
        "private_phase9j_annotation_input_rows_read",
        "private_phase9l_outcome_packets_read",
        "ignored_runs_read",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9m_scope"][private_read_key] = True
        mutated["no_execution_booleans"][private_read_key] = True
        checks.append((f"{private_read_key}_rejected", bool(validate_report(mutated))))

    # Targeted: route execution / acquisition / scoring / adjudication rejected.
    for exec_key in (
        "outcome_route_executed",
        "outcome_observables_acquired",
        "outcome_acquisition_method_executed",
        "scoring_executed",
        "adjudication_executed",
        "evidence_success_evaluated",
        "gold_rows_generated",
        "result_labels_generated",
        "provider_or_llm_calls",
        "network_fetch_or_clone_or_source_refresh_executed",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9m_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_rejected", bool(validate_report(mutated))))

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
        "outcome_observables_public",
        "outcome_packets_public",
    ):
        mutated = copy.deepcopy(base)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(base)
        mutated["frozen_outcome_observable_acquisition_route"]["stop_rule"].append(singleton_val)
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((
            f"singleton_regex_{singleton_val}",
            bool(SINGLETON_BUCKET_RE.search(singleton_val)),
        ))

    # Reject exact count fields.
    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["candidate_count"] = 72
    checks.append(("candidate_count_field_rejected", bool(validate_report(mutated))))

    # Reject private-shaped values (URL / path / hash / owner/repo).
    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["example_value"] = "https://example.invalid/repo.git"
    checks.append(("url_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["example_value"] = "owner/repo"
    checks.append(("owner_repo_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["example_value"] = "a" * 40
    checks.append(("hash_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["example_value"] = "src/private.py"
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
        mutated["phase9m_scope"][bad_key] = "example"
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
    mutated["conservative_recommendation"] = "route works and is proven"
    checks.append(("claim_wording_route_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["observable_definition"].append("evidence_success achieved")
    checks.append(("claim_wording_evidence_success_rejected", bool(validate_report(mutated))))

    for phrase in (
        "method effectiveness",
        "product readiness",
        "scoring success",
        "outcome success",
        "evaluation works",
        "acquisition success",
        "route proven",
    ):
        mutated = copy.deepcopy(base)
        mutated["frozen_outcome_observable_acquisition_route"]["stop_rule"].append(phrase)
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
    mutated["frozen_future_sequence"]["sequence_rules"].append("user must approve continuation")
    checks.append(("user_must_approve_wording_rejected", bool(validate_report(mutated))))

    # Reject placeholder/TBD/TODO wording in exposed string values.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(base)
        mutated["frozen_outcome_observable_acquisition_route"]["stop_rule"].append(phrase)
        checks.append((
            f"placeholder_{phrase}_rejected",
            bool(validate_report(mutated)),
        ))
        checks.append((
            f"placeholder_regex_{phrase}",
            bool(PLACEHOLDER_RE.search(phrase)),
        ))

    # Reject future execution without phase9m commit+CI green.
    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["future_execution_requires_phase9m_commit_and_ci_green"] = False
    checks.append(("future_execution_without_commit_ci_rejected", bool(validate_report(mutated))))

    # Reject a missing required route field (route vocabulary drift / missing
    # required route fields).
    mutated = copy.deepcopy(base)
    del mutated["frozen_outcome_observable_acquisition_route"]["observable_definition"]
    checks.append(("missing_route_field_rejected", bool(validate_report(mutated))))

    # Reject route vocabulary drift: a member value is reworded (set-equality).
    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["route_form"] = "drifted_route_form"
    checks.append(("route_form_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["extraction_procedure"][0] = (
        "llm_based_extraction_from_phase9h_materialized_sources_only"
    )
    checks.append(("route_extraction_procedure_vocabulary_drift_rejected", bool(validate_report(mutated))))

    # Reject EXTRA members in closed route lists (set-equality, route
    # vocabulary drift).  The task_id extra also fires the private-token scan.
    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["observable_definition"].append("task_id")
    errors = validate_report(mutated)
    checks.append(("extra_route_member_task_id_rejected", bool(errors)))
    checks.append((
        "extra_route_member_task_id_set_equality",
        any("has extra members" in e for e in errors),
    ))
    checks.append((
        "extra_route_member_task_id_private_token_scan",
        any("private-shaped list value" in e for e in errors),
    ))

    # Reject a missing required route list member.
    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["replacement_rule_if_invalid"] = [
        r for r in base["frozen_outcome_observable_acquisition_route"]["replacement_rule_if_invalid"]
        if r != "invalid_outcome_rejected_before_any_scoring_with_replacement_only"
    ]
    checks.append(("missing_required_route_rule_rejected", bool(validate_report(mutated))))

    # Reject an extra guardrail / privacy / denominator / sequence rule.
    for section, key, expected, label in (
        ("frozen_no_p_hacking_guardrails", "guardrail_rules", NO_P_HACKING_GUARDRAIL_RULES, "guardrail"),
        ("frozen_privacy", "privacy_rules", PRIVACY_RULES, "privacy"),
        ("frozen_denominator_rule", "denominator_rules", DENOMINATOR_RULES, "denominator"),
        ("frozen_future_sequence", "sequence_rules", FUTURE_SEQUENCE_RULES, "sequence"),
    ):
        mutated = copy.deepcopy(base)
        mutated[section][key].append("extra_bogus_rule")
        errors = validate_report(mutated)
        checks.append((f"extra_{label}_rule_rejected", bool(errors)))
        checks.append((
            f"extra_{label}_rule_set_equality",
            any("has extra members" in e for e in errors),
        ))

    # Reject a missing required guardrail / privacy / denominator / sequence rule.
    for section, key, expected, label, first_member in (
        ("frozen_no_p_hacking_guardrails", "guardrail_rules", NO_P_HACKING_GUARDRAIL_RULES, "guardrail", NO_P_HACKING_GUARDRAIL_RULES[0]),
        ("frozen_privacy", "privacy_rules", PRIVACY_RULES, "privacy", PRIVACY_RULES[0]),
        ("frozen_denominator_rule", "denominator_rules", DENOMINATOR_RULES, "denominator", DENOMINATOR_RULES[0]),
        ("frozen_future_sequence", "sequence_rules", FUTURE_SEQUENCE_RULES, "sequence", FUTURE_SEQUENCE_RULES[0]),
    ):
        mutated = copy.deepcopy(base)
        mutated[section][key] = [r for r in base[section][key] if r != first_member]
        checks.append((f"missing_required_{label}_rule_rejected", bool(validate_report(mutated))))

    # Reject inherited cap drift.
    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["inherited_phase9h_aggregate_caps"]["target_inventory_bucket"] = "bucket_wrong"
    checks.append(("inherited_cap_drift_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Reject truth-boundary violation.
    mutated = copy.deepcopy(base)
    mutated["truth_boundary"]["frozen_route_is_protocol_not_executed_acquisition"] = False
    checks.append(("truth_boundary_route_protocol_rejected", bool(validate_report(mutated))))

    # Reject no-llm-no-provider boundary flipped to false.
    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["no_llm_no_provider_frozen"] = False
    checks.append(("no_llm_no_provider_boundary_rejected", bool(validate_report(mutated))))
    # Reject no-trying-routes boundary flipped to false.
    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["no_trying_routes_until_one_works_unless_pre_frozen"] = False
    checks.append(("no_trying_routes_boundary_rejected", bool(validate_report(mutated))))

    # Non-whitelisted CI run key/value is rejected (the exact gate-reference
    # path exemption does not cover keys outside the schema).
    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["task_ci_run"] = "28983185765"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    checks.append((
        "non_whitelisted_ci_run_key_not_exempt",
        any("private-shaped public key" in e for e in errors),
    ))

    # Gate-reference commit values are exempt from private-shaped value scan
    # but a non-gate-reference key with a hash value is still rejected.
    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["example_hash"] = "c815a77d4dea3b77efe5dae0abe06006045294e9"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    # Validate a temp-file round-trip.
    with tempfile.TemporaryDirectory(prefix="phase9m_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- strict allowed-key checking rejects unknown fields. ---
    mutated = copy.deepcopy(base)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9m_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_route_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_outcome_observable_acquisition_route"]["inherited_phase9h_aggregate_caps"]["unexpected_cap"] = "x"
    checks.append(("unknown_nested_field_caps_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9l_closeout_statement"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_closeout_rejected", bool(validate_report(mutated))))

    # --- --validate-report fails closed on ignored/private paths. ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9m" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9m_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "other_phase" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading (no real file needed).
    runs_cli_path = str(REPO / "runs" / "phase9m" / "report.json")
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
        "selftest_does_not_read_phase9h_materialized_sources",
        PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS == 0,
    ))
    checks.append((
        "selftest_does_not_read_phase9j_annotation_input_rows",
        PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS == 0,
    ))
    checks.append((
        "selftest_does_not_read_phase9l_outcome_packets",
        PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS == 0,
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
        description="Phase 9M outcome-observable acquisition route protocol freeze"
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
        # Fail closed: --validate-report may only read the Phase 9M public
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
