#!/usr/bin/env python3
"""Phase 10E candidate-source-registry construction protocol freeze (no execution, no claim).

This is a docs/report/validator-only PROTOCOL-FREEZE checkpoint.  Phase 10E
defines ONLY how a compliant candidate source registry MAY be constructed or
provided in a LATER, separately reviewed phase.  Phase 10E itself does NOT
construct, fetch, clone, read, select, filter, materialize, populate, or
execute any registry or source candidate now.

Phase 10E is authorized by Phase 10D (commit ``acaa189``, CI run ``29016304662``
green), which closed Phase 10C as repair/no-claim and authorized ONLY the next
possible phase: Phase 10E candidate-source-registry construction protocol
freeze, not construction/execution.

Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation,
repair, rerun, rescore, or strengthening of Phase 9R/9S.  Phase 9 is closed.

Anti-adaptation rule: the Phase 10E protocol is frozen as a PROSPECTIVE
construction/provision rule.  It is NOT tuned to repair the observed Phase 10C
``bucket_zero`` / ``bucket_no_eligible_channel_registry`` outcome.  Phase 10C is
mentioned ONLY as a gate/provenance fact and as a failure mode to guard against
in a future execution phase, NOT as optimization feedback.  Candidate source
eligibility, ordering, replacement, exclusion, and audit rules are deterministic
and predeclared.  No rule is justified by "because 10C found zero accepted
sources" unless framed as a general compliance/audit requirement.  No new
threshold/fallback/channel exception is introduced to avoid
``bucket_no_eligible_channel_registry``.  Future execution must use the frozen
10E protocol as written, with no post-hoc selection after seeing source
availability.

Phase 10E performs NO execution and makes NO empirical, validation,
correctness, scoring, product, method, performance, or generalization claims.
It does NOT construct/edit/select/filter/provide/materialize/populate a
candidate source registry, does NOT fetch/clone/read/scrape/inspect/sample
source repositories/materials, does NOT rerun Phase 10C materialization or
modify the frozen Phase 10B protocol, does NOT score/adjudicate/evaluate
correctness/compute evidence_success/generate metrics/create validation
evidence, does NOT add thresholds/fallbacks/exceptions/channel-specific rescue
paths, does NOT treat ``bucket_zero`` as partial success, does NOT use Phase 9
artifacts as validation evidence, does NOT change runtime/default behavior, and
does NOT make user-approval wording a protocol dependency.

This module performs no network/filesystem fetch, no private reads, no source
reads, no ignored-``runs/`` reads, no Phase 9/10A/10B/10C/10D private artifact
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

PHASE = "phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim"
SCHEMA_VERSION = (
    "phase10e_candidate_source_registry_protocol_freeze"
    "_no_execution_no_claim_report_v1"
)
STATUS = (
    "phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim"
)

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# ---------------------------------------------------------------------------
# Frozen gate references.  Phase 10E publishes exact commit/CI references only
# for the immediate Phase 10D gate that authorized this protocol freeze.  Older
# Phase 9 / 10A / 10B / 10C / hygiene checkpoints are carried forward only as
# status/bucket/scope provenance, not as exact commit/CI identifiers.
# ---------------------------------------------------------------------------
PHASE9_STATUS = "closed"
PHASE10A_STATUS = "phase10a_independent_validation_protocol_freeze_no_execution_no_claim"
PHASE10B_STATUS = (
    "phase10b_fresh_fenced_input_construction_protocol_freeze"
    "_no_execution_no_materialization_no_claim"
)
PHASE10C_STATUS = "phase10c_input_construction_repair_no_claim"
PHASE10C_ACCEPTED_SOURCE_BUCKET = "bucket_zero"
PHASE10C_REPAIR_REASON_BUCKET = "bucket_no_eligible_channel_registry"

# Separate CI hygiene commit (CI infrastructure only, NOT empirical evidence).
HYGIENE_CI_SUCCESS = True
HYGIENE_SCOPE = (
    "ci_infrastructure_only_no_eval_protocol_report_docs_results_change"
)
HYGIENE_WORKFLOW_FILE = ".github/workflows/empirical-research.yml"
HYGIENE_CHANGE_DESCRIPTION = (
    "b16a_b16b_f1_timeouts_15_to_30_minutes_only"
)

# Phase 10D closeout/guard gate (authorizes Phase 10E protocol freeze only).
PHASE10D_COMMIT = "acaa189"
PHASE10D_CI_RUN = "29016304662"
PHASE10D_STATUS = "phase10d_10c_repair_closeout_guard_no_claim"

PROTOCOL_PUBLICATION_LEVEL = (
    "aggregate_candidate_source_registry_construction_protocol_freeze_boundary_only"
)

# ---------------------------------------------------------------------------
# Frozen Phase 10E candidate-source-registry construction/provision protocol.
# These are STRUCTURAL protocol-freeze definitions only; no execution, no
# registry construction, no source reads, no fetch/clone, no scoring,
# adjudication, correctness/evidence_success evaluation, or materialization
# occurs in Phase 10E.
# ---------------------------------------------------------------------------

# 1. Allowed future registry schema fields (what a compliant future candidate
#    source registry is allowed to contain at the registry/manifest level).
ALLOWED_REGISTRY_SCHEMA_FIELDS = (
    "registry_provenance",
    "registry_construction_route",
    "registry_source_channel_classes",
    "registry_deterministic_order_rule",
    "registry_minimum_eligible_sources",
    "registry_caps",
    "registry_no_phase9_private_reuse",
    "registry_operator_clean_room_attestation",
    "registry_construction_audit_log",
    "registry_exclusion_audit_log",
    "registry_replacement_audit_log",
    "registry_aggregate_only_public_projection",
)

# 2. Allowed future registry provenance fields (provenance/auditability).
ALLOWED_REGISTRY_PROVENANCE_FIELDS = (
    "registry_construction_route",
    "registry_source_channel_classes",
    "registry_deterministic_order_rule",
    "registry_no_phase9_private_reuse",
    "registry_operator_clean_room_attestation",
)

# 3. Allowed future per-candidate descriptor fields (eligibility fields).
ALLOWED_CANDIDATE_DESCRIPTOR_FIELDS = (
    "normalized_public_project_identity",
    "default_branch_name",
    "public_metadata_stable_rank",
    "channel_local_index",
    "license_precheck",
    "access_precheck",
    "default_branch_precheck",
    "currentness_precheck",
    "content_integrity_precheck",
)

# 4. Allowed future registry eligibility fields (subset of candidate descriptor
#    fields used for deterministic eligibility decisions).
ALLOWED_REGISTRY_ELIGIBILITY_FIELDS = (
    "license_precheck",
    "access_precheck",
    "default_branch_precheck",
    "currentness_precheck",
    "content_integrity_precheck",
)

# 5. Predeclared deterministic exclusion reason codes (closed set).
PREDECLARED_EXCLUSION_REASONS = (
    "license_precheck_failed",
    "access_precheck_failed",
    "default_branch_precheck_failed",
    "currentness_precheck_failed",
    "content_integrity_precheck_failed",
    "candidate_below_minimum_eligibility",
    "candidate_duplicate_identity",
    "candidate_not_from_allowed_channel_class",
)

# 6. Predeclared auditability requirements for a future registry.
PREDECLARED_AUDITABILITY_REQUIREMENTS = (
    "registry_construction_audit_log_required",
    "registry_exclusion_audit_log_required",
    "registry_replacement_audit_log_required",
    "registry_deterministic_order_verified",
    "registry_no_phase9_private_reuse_verified",
    "registry_aggregate_only_public_projection_verified",
)

# 7. Allowed future construction/provision routes (defined only, NOT executed).
ALLOWED_FUTURE_CONSTRUCTION_ROUTES = (
    "neutral_public_acquisition_channels_only",
    "operator_provided_external_registry",
)

# 8. Hard stops: conditions that immediately halt future construction.
HARD_STOPS = (
    "nonzero_phase9_private_reuse_stops_construction",
    "adaptive_tuning_to_observed_outcome_stops_construction",
    "post_hoc_selection_after_source_availability_stops_construction",
    "nonzero_randomness_in_ordering_or_selection_stops_construction",
    "registry_construction_after_observation_stops_construction",
    "treatment_of_zero_accepted_as_partial_success_stops_construction",
)

# 9. Replacement rules (predeclared, deterministic, before labels/outcomes/scoring).
REPLACEMENT_RULES = (
    "replacement_before_labels_outcomes_scoring_only",
    "replacement_only_from_frozen_eligibility_pool",
    "replacement_not_based_on_observed_outcome",
    "replacement_deterministic_no_randomness",
)

# 10. Non-adaptive ordering rules (deterministic, predeclared, no randomness).
NON_ADAPTIVE_ORDERING_RULES = (
    "frozen_channel_order_then_frozen_public_metadata_sort_keys",
    "no_random_shuffle",
    "no_post_hoc_reordering_after_observation",
    "deterministic_sort_keys_predeclared",
)

# 11. Validation checks for a future execution phase (defined only, NOT run).
FUTURE_EXECUTION_VALIDATION_CHECKS = (
    "registry_schema_fields_valid",
    "registry_provenance_fields_complete",
    "registry_eligibility_fields_present",
    "registry_exclusion_reasons_in_predeclared_set",
    "registry_audit_log_complete",
    "registry_deterministic_order_verified",
    "registry_minimum_eligible_sources_met_or_repair",
    "registry_no_phase9_private_reuse_verified",
    "registry_aggregate_only_public_projection_verified",
)

# 12. Aggregate-only public reporting rules (privacy boundary for future output).
AGGREGATE_ONLY_PUBLIC_REPORTING_RULES = (
    "registry_contents_not_public",
    "registry_candidate_details_not_public",
    "only_aggregate_buckets_public",
    "exclusion_reasons_aggregate_only",
    "no_per_source_per_task_public_facts",
)

# 13. Anti-adaptation rules (the protocol is prospective, not tuned to 10C).
ANTI_ADAPTATION_RULES = (
    "protocol_is_prospective_not_tuned_to_observed_outcome",
    "observed_zero_outcome_referenced_only_as_gate_and_failure_mode",
    "eligibility_ordering_replacement_exclusion_audit_deterministic_and_predeclared",
    "no_rule_justified_by_observed_zero_unless_general_compliance_audit",
    "no_threshold_fallback_or_channel_exception_for_observed_repair_reason",
    "future_execution_uses_frozen_protocol_no_post_hoc_selection",
)

# Closed protocol lists whose members are validator set-equality checked.
# Each entry is (report_section, list_key, expected_tuple, label).
CLOSED_PROTOCOL_LISTS = (
    (
        "phase10e_protocol_freeze",
        "allowed_registry_schema_fields",
        ALLOWED_REGISTRY_SCHEMA_FIELDS,
        "allowed_registry_schema_fields",
    ),
    (
        "phase10e_protocol_freeze",
        "allowed_registry_provenance_fields",
        ALLOWED_REGISTRY_PROVENANCE_FIELDS,
        "allowed_registry_provenance_fields",
    ),
    (
        "phase10e_protocol_freeze",
        "allowed_candidate_descriptor_fields",
        ALLOWED_CANDIDATE_DESCRIPTOR_FIELDS,
        "allowed_candidate_descriptor_fields",
    ),
    (
        "phase10e_protocol_freeze",
        "allowed_registry_eligibility_fields",
        ALLOWED_REGISTRY_ELIGIBILITY_FIELDS,
        "allowed_registry_eligibility_fields",
    ),
    (
        "phase10e_protocol_freeze",
        "predeclared_exclusion_reasons",
        PREDECLARED_EXCLUSION_REASONS,
        "predeclared_exclusion_reasons",
    ),
    (
        "phase10e_protocol_freeze",
        "predeclared_auditability_requirements",
        PREDECLARED_AUDITABILITY_REQUIREMENTS,
        "predeclared_auditability_requirements",
    ),
    (
        "phase10e_protocol_freeze",
        "allowed_future_construction_routes",
        ALLOWED_FUTURE_CONSTRUCTION_ROUTES,
        "allowed_future_construction_routes",
    ),
    (
        "phase10e_protocol_freeze",
        "hard_stops",
        HARD_STOPS,
        "hard_stops",
    ),
    (
        "phase10e_protocol_freeze",
        "replacement_rules",
        REPLACEMENT_RULES,
        "replacement_rules",
    ),
    (
        "phase10e_protocol_freeze",
        "non_adaptive_ordering_rules",
        NON_ADAPTIVE_ORDERING_RULES,
        "non_adaptive_ordering_rules",
    ),
    (
        "phase10e_protocol_freeze",
        "future_execution_validation_checks",
        FUTURE_EXECUTION_VALIDATION_CHECKS,
        "future_execution_validation_checks",
    ),
    (
        "phase10e_protocol_freeze",
        "aggregate_only_public_reporting_rules",
        AGGREGATE_ONLY_PUBLIC_REPORTING_RULES,
        "aggregate_only_public_reporting_rules",
    ),
    (
        "anti_adaptation_rules",
        "anti_adaptation_rules_list",
        ANTI_ADAPTATION_RULES,
        "anti_adaptation_rules",
    ),
)

# ---------------------------------------------------------------------------
# Truth-boundary attestation keys that must always be True.
# ---------------------------------------------------------------------------
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_inherited",
    "phase10a_gate_inherited",
    "phase10b_gate_inherited",
    "phase10c_executed_frozen_10b_route_once",
    "phase10c_result_repair_no_claim_zero_accepted_sources",
    "phase10c_produced_no_validation_evidence",
    "phase10d_gate_inherited_closeout_guard_authorized_10e",
    "phase10e_is_protocol_freeze_only_for_future_registry_construction",
    "phase10e_does_not_construct_or_supply_candidate_registry",
    "phase10e_does_not_change_frozen_phase10b_protocol",
    "phase10e_is_separate_from_phase9_not_continuation",
    "phase10e_makes_no_new_evidence_claims",
    "phase10e_protocol_is_prospective_not_tuned_to_10c_zero_outcome",
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
    "candidate_registry_materialized",
    "candidate_registry_populated",
    "source_material_fetched_or_cloned",
    "source_material_read",
    "source_material_scraped_or_sampled",
    "materialization_rerun",
    "thresholds_added",
    "fallbacks_added",
    "exceptions_added",
    "channel_specific_rescue_paths_added",
    "bucket_zero_treated_as_partial_success",
    "protocol_tuned_to_10c_zero_outcome",
    "post_hoc_selection_after_source_availability",
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
    "phase10e_confirms_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "registry_construction_succeeded_claim",
    "registry_provision_succeeded_claim",
    "empirical_claim",
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
    "phase10d_private_artifacts_public",
    "source_urls_public",
    "candidate_repo_names_public",
    "candidate_identities_public",
    "candidate_registry_contents_public",
    "registry_manifest_locations_public",
    "registry_construction_audit_log_public",
    "registry_exclusion_audit_log_public",
)

FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
)

CONSERVATIVE_RECOMMENDATION = (
    "phase10e_candidate_source_registry_construction_protocol_freeze_only"
    "_phase9_closed_inherited"
    "_phase10a_gate_inherited"
    "_phase10b_gate_inherited"
    "_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources"
    "_phase10d_closeout_guard_gate_inherited_authorized_10e_protocol_freeze_only"
    "_phase10e_is_protocol_freeze_only_for_future_registry_construction"
    "_phase10e_does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry"
    "_phase10e_does_not_fetch_clone_read_scrape_inspect_or_sample_source_material"
    "_phase10e_does_not_rerun_10c_materialization_or_change_frozen_10b_protocol"
    "_phase10e_does_not_score_adjudicate_or_run_correctness_evidence_success"
    "_phase10e_does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths"
    "_phase10e_does_not_treat_bucket_zero_as_partial_success"
    "_phase10e_protocol_is_prospective_not_tuned_to_10c_zero_outcome"
    "_phase10e_10c_referenced_only_as_gate_and_failure_mode_not_optimization_feedback"
    "_candidate_eligibility_ordering_replacement_exclusion_audit_deterministic_and_predeclared"
    "_no_threshold_fallback_or_channel_exception_for_observed_repair_reason"
    "_future_execution_uses_frozen_10e_protocol_no_post_hoc_selection_after_source_availability"
    "_hygiene_commit_is_ci_infrastructure_only_not_empirical_evidence"
    "_future_registry_construction_or_provision_or_execution_requires_separate_phase_after_10e_commit_and_ci_green"
    "_boundary_review_after_phase10e_commit_and_ci_green"
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
    r"|phase\s*10d\s+confirms"
    r"|phase\s*10e\s+confirms"
    r"|registry\s+construction\s+(?:works|succeeded|proven|established)"
    r"|registry\s+provision\s+(?:works|succeeded|proven|established)"
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
# published by Phase 10E.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10c_accepted_source_bucket",
        "$.gate_facts.phase10c_repair_reason_bucket",
        "$.gate_facts.hygiene_workflow_file",
        "$.gate_facts.phase10d_commit",
        "$.gate_facts.phase10d_ci_run",
    }
)
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10d_ci_run",
    }
)
# Short provenance commit prefixes (not full SHAs) are permitted only at the
# gate-facts commit paths above.
SHORT_COMMIT_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10d_commit",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read/
# execute/score/construct.  Phase 10E has no execution path at all; these
# stay zero.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_DISCOVERY_ATTEMPTS = 0
MATERIALIZATION_ATTEMPTS = 0
PACKET_GENERATION_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS = 0
SOURCE_MATERIAL_READ_ATTEMPTS = 0
SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS = 0
CANDIDATE_REGISTRY_POPULATION_ATTEMPTS = 0
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

    The report path must be under the Phase 10E public artifact directory
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
        return False, "report path is not under the Phase 10E public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Strict allowed-key schema for the public report
# ---------------------------------------------------------------------------

def _protocol_freeze_allowed() -> dict[str, Any]:
    """Build the allowed-schema dict for the protocol-freeze section.

    Each frozen list is represented as a dict with:
      - ``<list_key>``: None  (the list itself)
      - one boolean ``True`` entry per rule (attestation)
    """
    section: dict[str, Any] = {}
    for _section_name, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = None
        for rule in expected_tuple:
            section[rule] = None
    return section


ALLOWED_REPORT_KEYS: dict[str, Any] = {
    "schema_version": None,
    "phase": None,
    "status": None,
    "publication_level": None,
    "gate_facts": {
        "phase9_status": None,
        "phase10a_status": None,
        "phase10b_status": None,
        "phase10c_status": None,
        "phase10c_accepted_source_bucket": None,
        "phase10c_repair_reason_bucket": None,
        "hygiene_ci_success": None,
        "hygiene_scope": None,
        "hygiene_workflow_file": None,
        "hygiene_change_description": None,
        "hygiene_is_ci_infrastructure_only_not_empirical_evidence": None,
        "phase10d_commit": None,
        "phase10d_ci_run": None,
        "phase10d_status": None,
        "phase10d_authorized_10e_protocol_freeze_only": None,
        "only_phase10d_gate_constants_are_exact_references": None,
        "local_same_tree_git_commits_not_read_or_compared": None,
        "older_phase9_10a_10b_10c_hygiene_exact_refs_not_republished_by_phase10e": None,
    },
    "phase10e_scope": {
        "protocol_freeze_only_for_future_registry_construction": None,
        "separate_from_phase9_not_continuation": None,
        "authorized_by_phase10d_closeout_guard": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "phase10e_protocol_freeze": _protocol_freeze_allowed(),
    "anti_adaptation_rules": {
        "anti_adaptation_rules_list": None,
        **{key: None for key in ANTI_ADAPTATION_RULES},
    },
    "phase10e_boundary": {
        "performs_no_execution": None,
        "makes_no_new_evidence_claims": None,
        "does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry": None,
        "does_not_fetch_clone_read_scrape_inspect_or_sample_source_material": None,
        "does_not_rerun_10c_materialization": None,
        "does_not_change_frozen_phase10b_protocol": None,
        "does_not_score_adjudicate_or_run_correctness_evidence_success": None,
        "does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths": None,
        "does_not_treat_bucket_zero_as_partial_success": None,
        "protocol_is_prospective_not_tuned_to_10c_zero_outcome": None,
        "future_registry_construction_or_execution_requires_separate_phase_after_10e_commit_and_ci_green": None,
        "boundary_review_required_after_phase10e_commit_and_ci_green": None,
        "no_user_approval_wording_as_protocol_dependency": None,
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
        "phase10e_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_read_phase10c_artifacts": None,
        "validator_does_not_read_phase10d_artifacts": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_generate_packets": None,
        "validator_does_not_scrape_or_sample_sources": None,
        "validator_does_not_construct_candidate_registry": None,
        "validator_does_not_populate_candidate_registry": None,
        "validator_does_not_score_adjudicate_or_evaluate": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_generates_packets": None,
        "validator_scrapes_or_samples_sources": None,
        "validator_constructs_candidate_registry": None,
        "validator_populates_candidate_registry": None,
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
    """Build the Phase 10E protocol-freeze public report.

    This performs no network/filesystem fetch, no private reads, no source
    reads, no ignored-``runs/`` reads, and no scoring.  It assembles the
    report from the frozen gate constants and frozen protocol definitions
    only.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "publication_level": PROTOCOL_PUBLICATION_LEVEL,
        "gate_facts": {
            "phase9_status": PHASE9_STATUS,
            "phase10a_status": PHASE10A_STATUS,
            "phase10b_status": PHASE10B_STATUS,
            "phase10c_status": PHASE10C_STATUS,
            "phase10c_accepted_source_bucket": PHASE10C_ACCEPTED_SOURCE_BUCKET,
            "phase10c_repair_reason_bucket": PHASE10C_REPAIR_REASON_BUCKET,
            "hygiene_ci_success": HYGIENE_CI_SUCCESS,
            "hygiene_scope": HYGIENE_SCOPE,
            "hygiene_workflow_file": HYGIENE_WORKFLOW_FILE,
            "hygiene_change_description": HYGIENE_CHANGE_DESCRIPTION,
            "hygiene_is_ci_infrastructure_only_not_empirical_evidence": True,
            "phase10d_commit": PHASE10D_COMMIT,
            "phase10d_ci_run": PHASE10D_CI_RUN,
            "phase10d_status": PHASE10D_STATUS,
            "phase10d_authorized_10e_protocol_freeze_only": True,
            "only_phase10d_gate_constants_are_exact_references": True,
            "local_same_tree_git_commits_not_read_or_compared": True,
            "older_phase9_10a_10b_10c_hygiene_exact_refs_not_republished_by_phase10e": True,
        },
        "phase10e_scope": {
            "protocol_freeze_only_for_future_registry_construction": True,
            "separate_from_phase9_not_continuation": True,
            "authorized_by_phase10d_closeout_guard": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "phase10e_protocol_freeze": _build_protocol_freeze_section(),
        "anti_adaptation_rules": {
            "anti_adaptation_rules_list": list(ANTI_ADAPTATION_RULES),
            **{key: True for key in ANTI_ADAPTATION_RULES},
        },
        "phase10e_boundary": {
            "performs_no_execution": True,
            "makes_no_new_evidence_claims": True,
            "does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry": True,
            "does_not_fetch_clone_read_scrape_inspect_or_sample_source_material": True,
            "does_not_rerun_10c_materialization": True,
            "does_not_change_frozen_phase10b_protocol": True,
            "does_not_score_adjudicate_or_run_correctness_evidence_success": True,
            "does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths": True,
            "does_not_treat_bucket_zero_as_partial_success": True,
            "protocol_is_prospective_not_tuned_to_10c_zero_outcome": True,
            "future_registry_construction_or_execution_requires_separate_phase_after_10e_commit_and_ci_green": True,
            "boundary_review_required_after_phase10e_commit_and_ci_green": True,
            "no_user_approval_wording_as_protocol_dependency": True,
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
            "phase10e_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_read_phase10c_artifacts": True,
            "validator_does_not_read_phase10d_artifacts": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_generate_packets": True,
            "validator_does_not_scrape_or_sample_sources": True,
            "validator_does_not_construct_candidate_registry": True,
            "validator_does_not_populate_candidate_registry": True,
            "validator_does_not_score_adjudicate_or_evaluate": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_generates_packets": False,
            "validator_scrapes_or_samples_sources": False,
            "validator_constructs_candidate_registry": False,
            "validator_populates_candidate_registry": False,
            "validator_scores_or_adjudicates": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }
    return report


def _build_protocol_freeze_section() -> dict[str, Any]:
    """Build the phase10e_protocol_freeze section with frozen lists + booleans."""
    section: dict[str, Any] = {}
    for _section_name, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = list(expected_tuple)
        for rule in expected_tuple:
            section[rule] = True
    return section


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_report(report: Any) -> list[str]:
    """Validate the Phase 10E public report against the frozen schema/constants.

    This does NOT read any Phase 9/10A/10B/10C/10D artifact on disk, does NOT
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
    if gate.get("phase9_status") != PHASE9_STATUS:
        errors.append("Phase 9 status gate fact drift")
    if gate.get("phase10a_status") != PHASE10A_STATUS:
        errors.append("Phase 10A status gate fact drift")
    if gate.get("phase10b_status") != PHASE10B_STATUS:
        errors.append("Phase 10B status gate fact drift")
    if gate.get("phase10c_status") != PHASE10C_STATUS:
        errors.append("Phase 10C status gate fact drift")
    if gate.get("phase10c_accepted_source_bucket") != PHASE10C_ACCEPTED_SOURCE_BUCKET:
        errors.append("Phase 10C accepted source bucket gate fact drift")
    if gate.get("phase10c_repair_reason_bucket") != PHASE10C_REPAIR_REASON_BUCKET:
        errors.append("Phase 10C repair reason bucket gate fact drift")
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
    if gate.get("phase10d_commit") != PHASE10D_COMMIT:
        errors.append("Phase 10D commit gate reference drift")
    if gate.get("phase10d_ci_run") != PHASE10D_CI_RUN:
        errors.append("Phase 10D CI run gate reference drift")
    if gate.get("phase10d_status") != PHASE10D_STATUS:
        errors.append("Phase 10D status gate reference drift")
    if gate.get("phase10d_authorized_10e_protocol_freeze_only") is not True:
        errors.append("Phase 10D 10E authorization boundary missing")
    if gate.get("only_phase10d_gate_constants_are_exact_references") is not True:
        errors.append("Phase 10D-only exact references boundary missing")
    if gate.get("local_same_tree_git_commits_not_read_or_compared") is not True:
        errors.append("local git commits not read boundary missing")
    if gate.get("older_phase9_10a_10b_10c_hygiene_exact_refs_not_republished_by_phase10e") is not True:
        errors.append("older exact refs not republished boundary missing")

    scope = report.get("phase10e_scope", {})
    for key in (
        "protocol_freeze_only_for_future_registry_construction",
        "separate_from_phase9_not_continuation",
        "authorized_by_phase10d_closeout_guard",
    ):
        if scope.get(key) is not True:
            errors.append(f"phase10e_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10e_scope execution boundary failed: {key}")

    # Protocol-freeze closed-list set-equality checks.
    protocol = report.get("phase10e_protocol_freeze", {})
    for _section, list_key, expected_tuple, label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        actual = protocol.get(list_key)
        if not isinstance(actual, list):
            errors.append(f"protocol freeze list missing: {list_key}")
            continue
        if set(actual) != set(expected_tuple):
            errors.append(f"protocol freeze list drift: {label}")
            continue
        if len(actual) != len(set(actual)):
            errors.append(f"protocol freeze list duplicates: {label}")
        for rule in expected_tuple:
            if protocol.get(rule) is not True:
                errors.append(f"protocol freeze attestation missing: {rule}")

    # Anti-adaptation closed-list set-equality check.
    anti = report.get("anti_adaptation_rules", {})
    anti_list = anti.get("anti_adaptation_rules_list")
    if not isinstance(anti_list, list):
        errors.append("anti_adaptation_rules_list missing")
    else:
        if set(anti_list) != set(ANTI_ADAPTATION_RULES):
            errors.append("anti_adaptation_rules_list drift")
        elif len(anti_list) != len(set(anti_list)):
            errors.append("anti_adaptation_rules_list duplicates")
    for rule in ANTI_ADAPTATION_RULES:
        if anti.get(rule) is not True:
            errors.append(f"anti_adaptation attestation missing: {rule}")

    boundary = report.get("phase10e_boundary", {})
    for key in (
        "performs_no_execution",
        "makes_no_new_evidence_claims",
        "does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry",
        "does_not_fetch_clone_read_scrape_inspect_or_sample_source_material",
        "does_not_rerun_10c_materialization",
        "does_not_change_frozen_phase10b_protocol",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths",
        "does_not_treat_bucket_zero_as_partial_success",
        "protocol_is_prospective_not_tuned_to_10c_zero_outcome",
        "future_registry_construction_or_execution_requires_separate_phase_after_10e_commit_and_ci_green",
        "boundary_review_required_after_phase10e_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        if boundary.get(key) is not True:
            errors.append(f"phase10e_boundary missing: {key}")

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
    for key in (
        "phase10e_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_sources",
        "validator_does_not_read_ignored_runs",
        "validator_does_not_read_phase9_artifacts",
        "validator_does_not_read_phase10c_artifacts",
        "validator_does_not_read_phase10d_artifacts",
        "validator_does_not_discover_sources",
        "validator_does_not_materialize_sources",
        "validator_does_not_generate_packets",
        "validator_does_not_scrape_or_sample_sources",
        "validator_does_not_construct_candidate_registry",
        "validator_does_not_populate_candidate_registry",
        "validator_does_not_score_adjudicate_or_evaluate",
        "public_artifact_privacy_audit_expected",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in (
        "validator_executes_tasks",
        "validator_reads_private_registry",
        "validator_reads_sources",
        "validator_reads_ignored_runs",
        "validator_starts_empirical_work",
        "validator_discovers_sources",
        "validator_materializes_sources",
        "validator_generates_packets",
        "validator_scrapes_or_samples_sources",
        "validator_constructs_candidate_registry",
        "validator_populates_candidate_registry",
        "validator_scores_or_adjudicates",
    ):
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
    global PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS
    global SOURCE_MATERIAL_READ_ATTEMPTS, SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS
    global CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS, CANDIDATE_REGISTRY_POPULATION_ATTEMPTS
    global SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS, PROVIDER_OR_MODEL_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_DISCOVERY_ATTEMPTS = 0
    MATERIALIZATION_ATTEMPTS = 0
    PACKET_GENERATION_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
    CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS = 0
    CANDIDATE_REGISTRY_POPULATION_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    # Baseline report validates.
    dry = build_public_report()
    checks.append(("report_valid", not validate_report(dry)))
    checks.append(("phase_equals_slug", dry["phase"] == PHASE))
    checks.append(("status_is_protocol_freeze_no_claim", dry["status"] == STATUS))
    checks.append(("publication_level_boundary", dry["publication_level"] == PROTOCOL_PUBLICATION_LEVEL))

    # Gate facts enforced.  Only the immediate Phase 10D gate publishes exact
    # commit/CI identifiers; older checkpoints are status/bucket/scope only.
    checks.append(("phase9_status_gate", dry["gate_facts"]["phase9_status"] == PHASE9_STATUS))
    checks.append(("phase10c_status_gate", dry["gate_facts"]["phase10c_status"] == PHASE10C_STATUS))
    checks.append(("phase10c_accepted_bucket_zero", dry["gate_facts"]["phase10c_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10c_repair_bucket", dry["gate_facts"]["phase10c_repair_reason_bucket"] == "bucket_no_eligible_channel_registry"))
    checks.append(("phase10a_status_gate", dry["gate_facts"]["phase10a_status"] == PHASE10A_STATUS))
    checks.append(("phase10b_status_gate", dry["gate_facts"]["phase10b_status"] == PHASE10B_STATUS))
    checks.append(("hygiene_ci_success", dry["gate_facts"]["hygiene_ci_success"] is True))
    checks.append(("hygiene_ci_infrastructure_only", dry["gate_facts"]["hygiene_is_ci_infrastructure_only_not_empirical_evidence"] is True))
    checks.append(("phase10d_commit_gate", dry["gate_facts"]["phase10d_commit"] == PHASE10D_COMMIT))
    checks.append(("phase10d_ci_gate", dry["gate_facts"]["phase10d_ci_run"] == PHASE10D_CI_RUN))
    checks.append(("phase10d_status_gate", dry["gate_facts"]["phase10d_status"] == PHASE10D_STATUS))
    checks.append(("phase10d_authorized_10e", dry["gate_facts"]["phase10d_authorized_10e_protocol_freeze_only"] is True))

    # Protocol-freeze closed lists are set-equality checked.
    proto = dry["phase10e_protocol_freeze"]
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        actual = proto.get(list_key)
        checks.append((f"protocol_list_{list_key}_present", isinstance(actual, list)))
        if isinstance(actual, list):
            checks.append((f"protocol_list_{list_key}_set_eq", set(actual) == set(expected_tuple)))
            checks.append((f"protocol_list_{list_key}_no_dup", len(actual) == len(set(actual))))
        for rule in expected_tuple:
            checks.append((f"protocol_attest_{rule}", proto.get(rule) is True))

    # Anti-adaptation closed list.
    anti = dry["anti_adaptation_rules"]
    checks.append(("anti_adaptation_list_present", isinstance(anti.get("anti_adaptation_rules_list"), list)))
    if isinstance(anti.get("anti_adaptation_rules_list"), list):
        checks.append(("anti_adaptation_list_set_eq", set(anti["anti_adaptation_rules_list"]) == set(ANTI_ADAPTATION_RULES)))
    for rule in ANTI_ADAPTATION_RULES:
        checks.append((f"anti_adaptation_attest_{rule}", anti.get(rule) is True))

    # 10E boundary enforces protocol-freeze / no registry / no execution.
    boundary = dry["phase10e_boundary"]
    for key in (
        "performs_no_execution",
        "makes_no_new_evidence_claims",
        "does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry",
        "does_not_fetch_clone_read_scrape_inspect_or_sample_source_material",
        "does_not_rerun_10c_materialization",
        "does_not_change_frozen_phase10b_protocol",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths",
        "does_not_treat_bucket_zero_as_partial_success",
        "protocol_is_prospective_not_tuned_to_10c_zero_outcome",
        "future_registry_construction_or_execution_requires_separate_phase_after_10e_commit_and_ci_green",
        "boundary_review_required_after_phase10e_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        checks.append((f"phase10e_boundary_{key}", boundary[key] is True))

    # Reject missing/wrong gate facts.
    for field, bad_val, label in (
        ("phase9_status", "open", "phase9_status"),
        ("phase10a_status", "drift", "phase10a_status"),
        ("phase10b_status", "drift", "phase10b_status"),
        ("phase10c_status", "drift", "phase10c_status"),
        ("phase10c_accepted_source_bucket", "bucket_nonzero", "phase10c_bucket"),
        ("phase10c_repair_reason_bucket", "drift", "phase10c_repair"),
        ("hygiene_scope", "drift", "hygiene_scope"),
        ("phase10d_commit", "deadbeef", "phase10d_commit"),
        ("phase10d_ci_run", "0000", "phase10d_ci"),
        ("phase10d_status", "drift", "phase10d_status"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["gate_facts"][field] = bad_val
        checks.append((f"wrong_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        del mutated["gate_facts"][field]
        checks.append((f"missing_{label}_rejected", bool(validate_report(mutated))))

    # Reject 10D authorization flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["phase10d_authorized_10e_protocol_freeze_only"] = False
    checks.append(("phase10d_authorization_false_rejected", bool(validate_report(mutated))))

    # Reject phase10e_scope boundary facts flipped to false.
    for key in (
        "protocol_freeze_only_for_future_registry_construction",
        "separate_from_phase9_not_continuation",
        "authorized_by_phase10d_closeout_guard",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10e_scope"][key] = False
        checks.append((f"phase10e_scope_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject execution booleans true (forbidden in Phase 10E).
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["phase10e_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject 10E boundary facts flipped to false.
    for key in (
        "performs_no_execution",
        "makes_no_new_evidence_claims",
        "does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry",
        "does_not_fetch_clone_read_scrape_inspect_or_sample_source_material",
        "does_not_rerun_10c_materialization",
        "does_not_change_frozen_phase10b_protocol",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths",
        "does_not_treat_bucket_zero_as_partial_success",
        "protocol_is_prospective_not_tuned_to_10c_zero_outcome",
        "future_registry_construction_or_execution_requires_separate_phase_after_10e_commit_and_ci_green",
        "boundary_review_required_after_phase10e_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10e_boundary"][key] = False
        checks.append((f"phase10e_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject anti-adaptation rules flipped to false.
    for key in ANTI_ADAPTATION_RULES:
        mutated = copy.deepcopy(dry)
        mutated["anti_adaptation_rules"][key] = False
        checks.append((f"anti_adaptation_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject anti-adaptation list drift (extra rule added).
    mutated = copy.deepcopy(dry)
    mutated["anti_adaptation_rules"]["anti_adaptation_rules_list"] = list(ANTI_ADAPTATION_RULES) + ["extra_rule"]
    checks.append(("anti_adaptation_list_extra_rejected", bool(validate_report(mutated))))
    # Reject anti-adaptation list drift (rule removed).
    mutated = copy.deepcopy(dry)
    mutated["anti_adaptation_rules"]["anti_adaptation_rules_list"] = list(ANTI_ADAPTATION_RULES)[:-1]
    checks.append(("anti_adaptation_list_missing_rejected", bool(validate_report(mutated))))

    # Reject protocol-freeze list drift (extra member).
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        mutated = copy.deepcopy(dry)
        mutated["phase10e_protocol_freeze"][list_key] = list(expected_tuple) + ["extra_member"]
        checks.append((f"protocol_list_{list_key}_extra_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        mutated["phase10e_protocol_freeze"][list_key] = list(expected_tuple)[:-1]
        checks.append((f"protocol_list_{list_key}_missing_rejected", bool(validate_report(mutated))))

    # Reject protocol-freeze attestation flipped to false.
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        for rule in expected_tuple:
            mutated = copy.deepcopy(dry)
            mutated["phase10e_protocol_freeze"][rule] = False
            checks.append((f"protocol_attest_{rule}_false_rejected", bool(validate_report(mutated))))

    # Reject treating bucket_zero as partial success.
    mutated = copy.deepcopy(dry)
    mutated["phase10e_boundary"]["does_not_treat_bucket_zero_as_partial_success"] = False
    checks.append(("bucket_zero_partial_success_rejected", bool(validate_report(mutated))))

    # Reject protocol tuned to 10C zero outcome.
    mutated = copy.deepcopy(dry)
    mutated["phase10e_boundary"]["protocol_is_prospective_not_tuned_to_10c_zero_outcome"] = False
    checks.append(("protocol_tuned_to_10c_rejected", bool(validate_report(mutated))))

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
        mutated["phase10e_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "source_path_bucket", "path", "repo_name", "task_id", "row_id",
        "packet_id", "manifest", "run_dir", "candidate_identity",
        "hash_value", "snippet_value",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10e_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(dry)
        mutated["phase10e_scope"]["example_bucket"] = singleton_val
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # Reject forbidden success wording (must NOT appear anywhere).
    for phrase in ("validated", "evidence_success achieved", "correctness evidence",
                   "materialization succeeded", "independent validation passed",
                   "OpenLocus works", "Phase 10 confirms", "Phase 10C confirms",
                   "Phase 10D confirms", "Phase 10E confirms",
                   "method proven", "product readiness", "scoring success",
                   "outcome success", "evaluation works", "acquisition success",
                   "adjudication proven", "correctness proven", "lift achieved",
                   "generalized success", "evidence-acquisition success", "validation proven",
                   "registry construction succeeded", "registry provision proven"):
        mutated = copy.deepcopy(dry)
        mutated["phase10e_scope"]["example_note"] = phrase
        checks.append((f"forbidden_success_wording_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # Reject user-approval wording.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10e_scope"]["example_note"] = "user must approve before proceeding"
    checks.append(("user_approval_wording_scope_rejected", bool(validate_report(mutated))))

    # Reject placeholder wording.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(dry)
        mutated["phase10e_scope"]["example_note"] = phrase
        checks.append((f"placeholder_{phrase}_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema/publication_level drift.
    for field, bad in (("status", "drift"), ("phase", "drift"),
                       ("schema_version", "drift"),
                       ("publication_level", "drift")):
        mutated = copy.deepcopy(dry)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # Reject unknown fields.
    mutated = copy.deepcopy(dry)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10e_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_gate_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10e_protocol_freeze"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(mutated))))

    # Reject non-gate hash/CI values (gate values only allowed at exact paths).
    mutated = copy.deepcopy(dry)
    mutated["phase10e_scope"]["task_ci_run"] = "29016304662"
    checks.append(("non_whitelisted_ci_run_value_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10e_scope"]["example_hash"] = "acaa189d32d8d3cc699008dbd1f1159895f826ad"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))
    checks.append(("gate_ref_values_on_whitelisted_paths_valid", not validate_report(dry)))

    # Reject hygiene facts that imply hygiene is empirical evidence.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["hygiene_is_ci_infrastructure_only_not_empirical_evidence"] = False
    checks.append(("hygiene_as_evidence_rejected", bool(validate_report(mutated))))

    # Reject converting 10C zero accepted into partial success.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["phase10c_accepted_source_bucket"] = "bucket_nonzero_below_minimum"
    checks.append(("phase10c_nonzero_accepted_rejected", bool(validate_report(mutated))))

    # Path guard tests.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10e" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10c" / "report.json")
    checks.append(("validate_report_rejects_runs_phase10c_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10d_10c_repair_closeout_guard_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10e" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Temp-file round-trip (synthetic fixture only; no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10e_selftest_") as tmp:
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
    checks.append(("selftest_does_not_read_phase10d_artifacts", PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_material", SOURCE_MATERIAL_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_scrape_or_sample_sources", SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_construct_candidate_registry", CANDIDATE_REGISTRY_CONSTRUCTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_populate_candidate_registry", CANDIDATE_REGISTRY_POPULATION_ATTEMPTS == 0))
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
        description="Phase 10E candidate-source-registry construction protocol freeze (docs/report/validator-only, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true",
                        help="write the protocol-freeze report (no private output, no fetch)")
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
