#!/usr/bin/env python3
"""Phase 9Q adjudication/correctness/evidence_success protocol freeze.

This is a docs/report/validator-only protocol freeze.  It freezes the
adjudication eligibility rules, correctness/evidence_success definitions,
adjudication input boundary, inclusion/exclusion rules, privacy/publication
boundary, and future Phase 9R execution gate *structurally* (not
numerically) before any adjudication, correctness, or evidence_success is
executed.

It does NOT fetch, clone, read, or materialize any repository or source, does
NOT read ignored ``runs/``, the Phase 9P private scoring rows, the Phase 9N
private outcome-observable packets, the Phase 9H private materialized sources,
the Phase 9J private annotation-input rows/manifests, the Phase 9L private
outcome-acquisition packets/manifests, private candidate pools/registries/
manifests, does NOT execute any adjudication method or correctness/evidence_
success computation, does NOT compute any precision/recall/pass/fail, and does
NOT adjudicate or generate gold/benchmark/result/annotation-truth labels,
correctness, evidence_success, or evaluation rows.  It makes no
method/product/performance/model/provider/training/runtime/default/scoring/
outcome/evidence-success/annotation-truth/adjudication/correctness claim.

The Phase 9P public gate reference values (remote commit and CI run), the
Phase 9P public status, and the Phase 9P public bucket facts
(``denominator_bucket``, ``scored_bucket``, ``adjudicated_bucket``,
``correctness_bucket``) are the only public gate references published by Phase
9Q.  Phase 9O, Phase 9N, Phase 9M, Phase 9L, Phase 9K, Phase 9H, Phase 9I,
Phase 9J, Phase 9G, and Phase 9F are carried as bucketed inherited provenance
only and their exact remote commit/CI run values are intentionally NOT
published in the Phase 9Q report/docs (tighter privacy).  Local same-tree git
commits are not read or compared; the supplied confirmation values are matched
against the frozen public gate constants only.

Truth-boundary is explicit: the adjudication eligibility rule is a protocol,
not adjudicated truth; the correctness/evidence_success definitions are future
definitions, not executed correctness/evidence_success; the adjudication input
boundary is frozen, not executed; the Phase 9P scored bucket is scoring
availability, not adjudication success; the frozen protocol is not executed
adjudication or correctness.
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

# Compact Phase 9Q slug (kept short so the absolute artifact report path stays
# comfortably under the Windows MAX_PATH (260) limit).  Boundary wording in
# the report body/docs is NOT weakened -- only the path-dependent slug is
# shortened.
PHASE = "phase9q_adjudication_correctness_protocol_freeze_no_execution_no_claim"
# Honest freeze wording: the adjudication/correctness/evidence_success
# PROTOCOL is frozen (no execution, no private read, no adjudication, no
# correctness, no evidence_success, no claim).  Not "success"/"validated"/
# "scored"/"adjudicated"/"correct"/"benchmark" (forbidden wording); "freeze"
# honestly reflects that only the protocol is frozen, with no execution of
# adjudication/correctness/evidence_success.
STATUS = (
    "phase9q_adjudication_correctness_protocol_freeze"
    "_no_execution_no_private_read_no_adjudication_no_correctness"
    "_no_evidence_success_no_claim"
)
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

# ---------------------------------------------------------------------------
# Phase 9P public gate reference values (oracle-provided).  These are the
# PRIMARY and ONLY public gate references published by Phase 9Q.  Local
# same-tree git commits are not read or compared; the supplied confirmation
# values are matched against the frozen public gate constants only.
# ---------------------------------------------------------------------------
PHASE9P_STATUS = (
    "phase9p_frozen_scoring_executed_denominator_nonzero_scored_nonzero"
    "_adjudication_not_executed_separate_frozen_boundary_required"
    "_no_evidence_success_no_claim"
)
PHASE9P_COMMIT = "511a765135bd53c724fb593db0c9ea5ebb38a500"
PHASE9P_CI_RUN = "28987083201"
# Phase 9P public bucket facts (aggregate bucket only, no exact count).
PHASE9P_DENOMINATOR_BUCKET = "bucket_nonzero_redacted"
PHASE9P_SCORED_BUCKET = "bucket_nonzero_redacted"
PHASE9P_ADJUDICATED_BUCKET = "bucket_zero"
PHASE9P_CORRECTNESS_BUCKET = "bucket_zero"

# Phase 9O inherited provenance (carried forward, bucketed only).  The exact
# Phase 9O remote commit/CI run values are intentionally NOT published in the
# Phase 9Q report/docs (tighter privacy); only the Phase 9P full commit SHA /
# CI run are public gate references.
PHASE9O_STATUS = (
    "phase9o_scoring_denominator_adjudication_protocol_freeze"
    "_no_execution_no_private_read_no_scoring_no_claim"
)
# Phase 9N inherited provenance (bucketed only).
PHASE9N_STATUS = (
    "phase9n_frozen_route_executed_valid_acquired_nonzero_aggregate_availability"
    "_no_scoring_no_adjudication_no_claim"
)
# Phase 9M/9L/9K inherited provenance (carried forward, bucketed only).
PHASE9M_STATUS = (
    "phase9m_outcome_observable_acquisition_route_protocol_freeze"
    "_no_execution_no_scoring_no_adjudication_no_claim"
)
PHASE9L_STATUS = (
    "phase9l_outcome_acquisition_executed_unavailable_only"
    "_no_scoring_no_adjudication_no_claim"
)
PHASE9K_STATUS = "phase9k_outcome_scoring_protocol_freeze_no_claim"

# Phase 9H/9I/9J/9G/9F inherited provenance (carried forward, bucketed only).
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

# ---------------------------------------------------------------------------
# Frozen adjudication/correctness/evidence_success protocol (closed lists,
# validator set-equality checked).  These are STRUCTURAL protocol definitions
# only; no adjudication, correctness, or evidence_success is executed in
# Phase 9Q.
# ---------------------------------------------------------------------------
PROTOCOL_PUBLICATION_LEVEL = "aggregate_bucketed_protocol_only"

# 1. Adjudication eligibility rule: future Phase 9R adjudication may consider
#    only the private set of Phase 9P scored rows that at Phase 9R execution
#    time satisfy these pre-frozen predicates.
ADJUDICATION_ELIGIBILITY_PREDICATES = (
    "row_scored_in_phase9p_under_frozen_phase9o_protocol",
    "row_denominator_bucket_nonzero",
    "row_scored_bucket_nonzero",
    "row_packet_acquisition_state_is_acquired",
    "row_packet_validity_state_is_valid",
    "row_outcome_observable_packet_present",
    "row_not_unavailable",
    "row_not_invalid",
    "row_not_excluded_before_scoring",
    "row_not_outside_frozen_route",
    "row_not_outside_cap",
    "row_not_outside_order_constraints",
    "row_schema_validates",
)

# 2. Correctness/evidence_success definitions: future definitions only (not
#    executed).  No precision/recall/pass/fail, no gold/benchmark/result/
#    annotation-truth labels, no provider/LLM/model.
CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS = (
    "correctness_is_deterministic_comparison_not_llm_not_provider_not_model",
    "correctness_is_source_grounded_against_frozen_outcome_observable_packet_only",
    "correctness_uses_no_phase9j_rows_as_truth",
    "correctness_uses_no_phase9l_unavailable_packets",
    "evidence_success_is_aggregate_correctness_bucket_only_not_executed",
    "no_precision_recall_pass_fail_in_phase9q",
    "no_gold_benchmark_result_annotation_truth_labels_in_phase9q",
    "correctness_and_evidence_success_are_future_definitions_not_executed",
)

# 3. Adjudication input boundary: what inputs future adjudication may/may not
#    read.  Frozen, not executed in Phase 9Q.
ADJUDICATION_INPUT_BOUNDARY_RULES = (
    "adjudication_input_is_frozen_outcome_observable_packet_only",
    "adjudication_reads_no_phase9h_materialized_sources",
    "adjudication_reads_no_phase9j_annotation_input_rows_as_truth",
    "adjudication_reads_no_phase9l_unavailable_packets",
    "adjudication_reads_no_phase9p_private_scoring_rows_as_truth",
    "adjudication_uses_no_provider_llm_model",
    "adjudication_input_boundary_frozen_not_executed_in_phase9q",
)

# 4. Inclusion/exclusion rule: include only scored acquired valid packets for
#    future adjudication; exclude unavailable, invalid, excluded,
#    out-of-route/cap/order before adjudication.
INCLUSION_EXCLUSION_RULES = (
    "include_only_scored_acquired_valid_packets_for_future_adjudication",
    "exclude_unavailable_packets_from_adjudication",
    "exclude_invalid_packets_from_adjudication",
    "exclude_excluded_packets_from_adjudication",
    "exclude_out_of_route_packets_from_adjudication",
    "exclude_out_of_cap_packets_from_adjudication",
    "exclude_out_of_order_packets_from_adjudication",
    "no_adjudication_execution_in_phase9q",
)

# 5. Privacy/publication boundary: public only buckets, no exact
#    counts/observables/paths/snippets/source/task/row/packet IDs/run
#    locations.
PRIVACY_PUBLICATION_RULES = (
    "public_aggregate_or_bucketed_only",
    "no_exact_counts_or_rates_public",
    "no_repo_source_url_owner_commit_beyond_whitelisted_phase9p_gate_refs",
    "no_paths_snippets_line_ranges_rows_tasks_packets_public",
    "no_manifest_or_run_locations_public",
    "no_per_source_or_per_task_or_per_packet_facts_public",
    "no_singleton_buckets_public",
    "no_phase9p_private_scoring_rows_read_in_phase9q",
    "no_phase9n_private_packets_read_in_phase9q",
    "no_phase9l_private_packets_read_in_phase9q",
    "no_ignored_runs_read_in_phase9q",
)

# 6. Future Phase 9R gate: may execute adjudication/correctness only after
#    9Q committed/CI green, only frozen rules, private outputs ignored, public
#    aggregate buckets only.
FUTURE_PHASE9R_GATE_RULES = (
    "phase9q_commit_and_ci_green_required_before_phase9r",
    "phase9p_gate_confirmed_denominator_nonzero_scored_nonzero_required",
    "phase9q_protocol_freeze_confirmation_required",
    "only_frozen_rules_may_execute_in_phase9r",
    "private_outputs_ignored_in_phase9r_public_aggregate_buckets_only",
    "no_adjudication_or_correctness_execution_in_phase9q",
    "no_provider_llm_model_in_phase9r_adjudication",
    "no_phase9j_as_truth_in_phase9r",
    "no_phase9l_unavailable_packets_adjudicable_in_phase9r",
    "no_user_approval_wording_future_gate_requires_phase9q_commit_ci_green_and_explicit_confirmations_boundary",
)

# Frozen no-p-hacking guardrails.
NO_P_HACKING_GUARDRAIL_RULES = (
    "no_private_or_source_inspection_during_phase9q",
    "no_tuning_definitions_after_outcomes_visible",
    "no_adjudication_or_correctness_changes_after_scoring",
    "no_subgroup_changes_after_scoring",
    "no_metric_threshold_tuning_after_outcome_visibility",
    "correctness_and_evidence_success_definitions_frozen_now_future_definitions_not_executed",
)

# Truth-boundary attestation keys that must always be True in the public report.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "adjudication_eligibility_rule_is_not_adjudicated_truth",
    "correctness_definition_is_not_executed_correctness",
    "evidence_success_definition_is_not_executed_evidence_success",
    "adjudication_input_boundary_is_frozen_not_executed",
    "phase9p_scored_bucket_is_scoring_availability_not_adjudication_success",
    "frozen_protocol_is_not_executed_adjudication_or_correctness",
)

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "outcome_route_executed",
    "outcomes_acquired",
    "task_annotation_generated",
    "private_phase9h_materialized_sources_read",
    "private_phase9j_annotation_input_rows_read",
    "private_phase9l_outcome_packets_read",
    "private_phase9n_packets_read",
    "private_phase9p_scoring_rows_read",
    "private_candidate_pool_read",
    "private_registry_read",
    "ignored_runs_read",
    "annotations_generated",
    "gold_rows_generated",
    "benchmark_labels_generated",
    "evidence_success_evaluated",
    "scoring_executed",
    "adjudication_executed",
    "denominator_computed",
    "correctness_evaluated",
    "evaluation_rows_generated",
    "result_labels_generated",
    "annotation_truth_generated",
    "phase9j_rows_used_as_benchmark_truth",
    "phase9l_packets_scoreable",
    "phase9p_scoring_rows_used_as_adjudication_truth",
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
    "packet_ids_public",
    "manifest_locations_public",
    "run_locations_public",
    "per_source_public_facts",
    "per_task_public_facts",
    "per_packet_public_facts",
    "singleton_buckets_public",
    "outcome_observables_public",
    "outcome_packets_public",
    "phase9p_scoring_rows_public",
    "phase9n_packets_public",
)

# Forbidden public field words; only apply to non-boolean values at
# non-allowed-schema paths so boolean boundary attestation keys such as
# ``adjudication_executed`` and section names such as
# ``frozen_adjudication_eligibility`` (which are at allowed-schema paths)
# are not false-flagged.
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
    ("frozen_adjudication_eligibility", "adjudication_eligibility_predicates", ADJUDICATION_ELIGIBILITY_PREDICATES, "adjudication_predicates"),
    ("frozen_correctness_evidence_success_definitions", "correctness_evidence_success_definitions", CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS, "correctness_definitions"),
    ("frozen_adjudication_input_boundary", "adjudication_input_boundary_rules", ADJUDICATION_INPUT_BOUNDARY_RULES, "adjudication_input"),
    ("frozen_inclusion_exclusion", "inclusion_exclusion_rules", INCLUSION_EXCLUSION_RULES, "inclusion_exclusion"),
    ("frozen_privacy_publication", "privacy_publication_rules", PRIVACY_PUBLICATION_RULES, "privacy"),
    ("frozen_future_phase9r_gate", "future_phase9r_gate_rules", FUTURE_PHASE9R_GATE_RULES, "future_phase9r_gate"),
    ("frozen_no_p_hacking_guardrails", "guardrail_rules", NO_P_HACKING_GUARDRAIL_RULES, "guardrail"),
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
    r"|adjudication\s+(?:works|succeeded|proven|established)"
    r"|denominator\s+(?:proven|established|achieved)"
    r"|correctness\s+(?:proven|established|achieved|confirmed)"
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
# public gate constants (full commit SHA / CI run ID).  Only the Phase 9P
# commit/CI paths are exempt from the private-shaped value scan.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9p_gate_references.phase9p_commit",
        "$.phase9p_gate_references.phase9p_ci_run",
    }
)

# Exact public gate-reference JSON paths whose string VALUES are CI run IDs
# (long decimal integers).  Only the Phase 9P CI run path is exempt from the
# long-decimal value scan.
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9p_gate_references.phase9p_ci_run",
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
PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS = 0


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
    "phase9p_gate_references": {
        "phase9p_commit": None,
        "phase9p_ci_run": None,
        "phase9p_ci_success": None,
        "phase9p_status": None,
        "phase9p_denominator_bucket": None,
        "phase9p_scored_bucket": None,
        "phase9p_adjudicated_bucket": None,
        "phase9p_correctness_bucket": None,
        "phase9p_adjudication_not_executed": None,
        "phase9p_correctness_not_computed": None,
        "phase9p_evidence_success_not_computed": None,
        "phase9p_requires_separate_frozen_boundary_after_scoring": None,
        "phase9p_phase9q_gate_true": None,
        "phase9p_phase9q_may_be_considered_only_if_denominator_and_scored_buckets_nonzero": None,
        "phase9p_no_adjudication_no_correctness_no_evidence_success_in_phase9p": None,
        "phase9p_not_proof_adjudication_or_correctness_or_evidence_success": None,
        "phase9p_gate_required_before_phase9q": True,
    },
    "phase9o_inherited_provenance": {
        "phase9o_status": None,
        "phase9o_ci_success": None,
        "phase9o_protocol_freeze": None,
        "phase9o_remote_provenance_bucketed": None,
        "phase9o_carried_as_inherited_provenance_only": None,
    },
    "phase9n_inherited_provenance": {
        "phase9n_status": None,
        "phase9n_ci_success": None,
        "phase9n_acquired_valid_bucket": None,
        "phase9n_remote_provenance_bucketed": None,
        "phase9n_carried_as_inherited_provenance_only": None,
    },
    "phase9m_inherited_provenance": {
        "phase9m_status": None,
        "phase9m_ci_success": None,
        "phase9m_protocol_freeze": None,
        "phase9m_remote_provenance_bucketed": None,
        "phase9m_carried_as_inherited_provenance_only": None,
    },
    "phase9l_inherited_provenance": {
        "phase9l_status": None,
        "phase9l_ci_success": None,
        "phase9l_outcome_acquisition_protocol_frozen": None,
        "phase9l_remote_provenance_bucketed": None,
        "phase9l_carried_as_inherited_provenance_only": None,
    },
    "phase9k_inherited_provenance": {
        "phase9k_status": None,
        "phase9k_ci_success": None,
        "phase9k_protocol_freeze": None,
        "phase9k_remote_provenance_bucketed": None,
        "phase9k_carried_as_inherited_provenance_only": None,
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
    "phase9g_inherited_provenance": {
        "phase9g_status": None,
        "phase9g_ci_success": None,
        "phase9g_protocol_freeze": None,
        "phase9g_remote_provenance_bucketed": None,
        "phase9g_carried_as_inherited_provenance_only": None,
    },
    "phase9f_inherited_provenance": {
        "phase9f_status": None,
        "phase9f_repair_no_claim": None,
        "phase9f_zero_buckets": None,
        "phase9f_public_fetch_or_clone_executed": None,
        "phase9f_carried_as_inherited_provenance_only": None,
    },
    "phase9q_scope": {
        "docs_report_validator_only": None,
        "protocol_freeze_only": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "outcome_route_executed": None,
        "outcomes_acquired": None,
        "task_annotation_generated": None,
        "private_phase9h_materialized_sources_read": None,
        "private_phase9j_annotation_input_rows_read": None,
        "private_phase9l_outcome_packets_read": None,
        "private_phase9n_packets_read": None,
        "private_phase9p_scoring_rows_read": None,
        "private_candidate_pool_read": None,
        "private_registry_read": None,
        "ignored_runs_read": None,
        "annotations_generated": None,
        "gold_rows_generated": None,
        "benchmark_labels_generated": None,
        "evidence_success_evaluated": None,
        "scoring_executed": None,
        "adjudication_executed": None,
        "denominator_computed": None,
        "correctness_evaluated": None,
        "evaluation_rows_generated": None,
        "result_labels_generated": None,
        "annotation_truth_generated": None,
        "phase9j_rows_used_as_benchmark_truth": None,
        "phase9l_packets_scoreable": None,
        "phase9p_scoring_rows_used_as_adjudication_truth": None,
        "model_fitting": None,
        "provider_or_llm_calls": None,
        "runtime_default_or_product_changes": None,
        "network_fetch_or_clone_or_source_refresh_executed": None,
        "future_execution_requires_phase9q_commit_and_ci_green": None,
    },
    "frozen_adjudication_eligibility": {
        "publication_level": None,
        "adjudication_eligibility_predicates": None,
        "adjudication_eligible_only_if_scored_in_phase9p_under_frozen_protocol": None,
        "no_adjudication_executed_in_phase9q": None,
        "adjudication_eligibility_rule_is_not_adjudicated_truth": None,
    },
    "frozen_correctness_evidence_success_definitions": {
        "correctness_evidence_success_definitions": None,
        "definitions_are_future_definitions_not_executed": None,
        "correctness_is_deterministic_source_grounded_no_llm_no_provider_no_model": None,
        "no_precision_recall_pass_fail": None,
        "no_gold_benchmark_result_annotation_truth_labels": None,
        "evidence_success_is_aggregate_correctness_bucket_only_not_executed": None,
    },
    "frozen_adjudication_input_boundary": {
        "adjudication_input_boundary_rules": None,
        "adjudication_input_is_frozen_outcome_observable_packet_only": None,
        "adjudication_reads_no_phase9p_private_scoring_rows_as_truth": None,
        "adjudication_uses_no_provider_llm_model": None,
        "no_adjudication_input_read_in_phase9q": None,
    },
    "frozen_inclusion_exclusion": {
        "inclusion_exclusion_rules": None,
        "include_only_scored_acquired_valid_packets_for_future_adjudication": None,
        "exclude_unavailable_invalid_excluded_out_of_route_cap_order_before_adjudication": None,
    },
    "frozen_privacy_publication": {
        "privacy_publication_rules": None,
        "public_aggregate_or_bucketed_only": None,
        "no_exact_counts_rates_observables_paths_snippets_ids_run_locations": None,
        "no_phase9p_private_scoring_rows_read_in_phase9q": None,
        "no_phase9n_private_packets_read_in_phase9q": None,
        "no_singleton_buckets": None,
    },
    "frozen_future_phase9r_gate": {
        "future_phase9r_gate_rules": None,
        "phase9r_may_execute_adjudication_correctness_only_after_phase9q_commit_and_ci_green": None,
        "phase9r_uses_only_frozen_rules": None,
        "phase9r_private_outputs_ignored_public_aggregate_buckets_only": None,
        "no_adjudication_or_correctness_execution_in_phase9q": None,
    },
    "frozen_no_p_hacking_guardrails": {
        "guardrail_rules": None,
        "no_private_or_source_inspection_during_phase9q": None,
        "no_tuning_definitions_after_outcomes_visible": None,
        "no_adjudication_or_correctness_changes_after_scoring": None,
        "no_subgroup_changes_after_scoring": None,
        "no_metric_threshold_tuning_after_outcome_visibility": None,
        "correctness_and_evidence_success_definitions_frozen_now": None,
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
        "protocol_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_phase9h_materialized_sources": None,
        "validator_does_not_read_phase9j_annotation_input_rows": None,
        "validator_does_not_read_phase9l_outcome_packets": None,
        "validator_does_not_read_phase9n_outcome_packets": None,
        "validator_does_not_read_phase9p_scoring_rows": None,
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

    The report path must be under the Phase 9Q public artifact directory
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
        return False, "report path is not under the Phase 9Q public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report() -> dict[str, Any]:
    """Build the frozen Phase 9Q public protocol report.

    This function performs no network/filesystem fetch or private reads.  It
    assembles the frozen protocol document from static constants.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9p_gate_references": {
            "phase9p_commit": PHASE9P_COMMIT,
            "phase9p_ci_run": PHASE9P_CI_RUN,
            "phase9p_ci_success": True,
            "phase9p_status": PHASE9P_STATUS,
            "phase9p_denominator_bucket": PHASE9P_DENOMINATOR_BUCKET,
            "phase9p_scored_bucket": PHASE9P_SCORED_BUCKET,
            "phase9p_adjudicated_bucket": PHASE9P_ADJUDICATED_BUCKET,
            "phase9p_correctness_bucket": PHASE9P_CORRECTNESS_BUCKET,
            "phase9p_adjudication_not_executed": True,
            "phase9p_correctness_not_computed": True,
            "phase9p_evidence_success_not_computed": True,
            "phase9p_requires_separate_frozen_boundary_after_scoring": True,
            "phase9p_phase9q_gate_true": True,
            "phase9p_phase9q_may_be_considered_only_if_denominator_and_scored_buckets_nonzero": True,
            "phase9p_no_adjudication_no_correctness_no_evidence_success_in_phase9p": True,
            "phase9p_not_proof_adjudication_or_correctness_or_evidence_success": True,
            "phase9p_gate_required_before_phase9q": True,
        },
        "phase9o_inherited_provenance": {
            "phase9o_status": PHASE9O_STATUS,
            "phase9o_ci_success": True,
            "phase9o_protocol_freeze": True,
            "phase9o_remote_provenance_bucketed": True,
            "phase9o_carried_as_inherited_provenance_only": True,
        },
        "phase9n_inherited_provenance": {
            "phase9n_status": PHASE9N_STATUS,
            "phase9n_ci_success": True,
            "phase9n_acquired_valid_bucket": "bucket_nonzero_redacted",
            "phase9n_remote_provenance_bucketed": True,
            "phase9n_carried_as_inherited_provenance_only": True,
        },
        "phase9m_inherited_provenance": {
            "phase9m_status": PHASE9M_STATUS,
            "phase9m_ci_success": True,
            "phase9m_protocol_freeze": True,
            "phase9m_remote_provenance_bucketed": True,
            "phase9m_carried_as_inherited_provenance_only": True,
        },
        "phase9l_inherited_provenance": {
            "phase9l_status": PHASE9L_STATUS,
            "phase9l_ci_success": True,
            "phase9l_outcome_acquisition_protocol_frozen": True,
            "phase9l_remote_provenance_bucketed": True,
            "phase9l_carried_as_inherited_provenance_only": True,
        },
        "phase9k_inherited_provenance": {
            "phase9k_status": PHASE9K_STATUS,
            "phase9k_ci_success": True,
            "phase9k_protocol_freeze": True,
            "phase9k_remote_provenance_bucketed": True,
            "phase9k_carried_as_inherited_provenance_only": True,
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
        "phase9g_inherited_provenance": {
            "phase9g_status": PHASE9G_STATUS,
            "phase9g_ci_success": True,
            "phase9g_protocol_freeze": True,
            "phase9g_remote_provenance_bucketed": True,
            "phase9g_carried_as_inherited_provenance_only": True,
        },
        "phase9f_inherited_provenance": {
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_repair_no_claim": True,
            "phase9f_zero_buckets": True,
            "phase9f_public_fetch_or_clone_executed": False,
            "phase9f_carried_as_inherited_provenance_only": True,
        },
        "phase9q_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "outcome_route_executed": False,
            "outcomes_acquired": False,
            "task_annotation_generated": False,
            "private_phase9h_materialized_sources_read": False,
            "private_phase9j_annotation_input_rows_read": False,
            "private_phase9l_outcome_packets_read": False,
            "private_phase9n_packets_read": False,
            "private_phase9p_scoring_rows_read": False,
            "private_candidate_pool_read": False,
            "private_registry_read": False,
            "ignored_runs_read": False,
            "annotations_generated": False,
            "gold_rows_generated": False,
            "benchmark_labels_generated": False,
            "evidence_success_evaluated": False,
            "scoring_executed": False,
            "adjudication_executed": False,
            "denominator_computed": False,
            "correctness_evaluated": False,
            "evaluation_rows_generated": False,
            "result_labels_generated": False,
            "annotation_truth_generated": False,
            "phase9j_rows_used_as_benchmark_truth": False,
            "phase9l_packets_scoreable": False,
            "phase9p_scoring_rows_used_as_adjudication_truth": False,
            "model_fitting": False,
            "provider_or_llm_calls": False,
            "runtime_default_or_product_changes": False,
            "network_fetch_or_clone_or_source_refresh_executed": False,
            "future_execution_requires_phase9q_commit_and_ci_green": True,
        },
        "frozen_adjudication_eligibility": {
            "publication_level": PROTOCOL_PUBLICATION_LEVEL,
            "adjudication_eligibility_predicates": list(ADJUDICATION_ELIGIBILITY_PREDICATES),
            "adjudication_eligible_only_if_scored_in_phase9p_under_frozen_protocol": True,
            "no_adjudication_executed_in_phase9q": True,
            "adjudication_eligibility_rule_is_not_adjudicated_truth": True,
        },
        "frozen_correctness_evidence_success_definitions": {
            "correctness_evidence_success_definitions": list(CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS),
            "definitions_are_future_definitions_not_executed": True,
            "correctness_is_deterministic_source_grounded_no_llm_no_provider_no_model": True,
            "no_precision_recall_pass_fail": True,
            "no_gold_benchmark_result_annotation_truth_labels": True,
            "evidence_success_is_aggregate_correctness_bucket_only_not_executed": True,
        },
        "frozen_adjudication_input_boundary": {
            "adjudication_input_boundary_rules": list(ADJUDICATION_INPUT_BOUNDARY_RULES),
            "adjudication_input_is_frozen_outcome_observable_packet_only": True,
            "adjudication_reads_no_phase9p_private_scoring_rows_as_truth": True,
            "adjudication_uses_no_provider_llm_model": True,
            "no_adjudication_input_read_in_phase9q": True,
        },
        "frozen_inclusion_exclusion": {
            "inclusion_exclusion_rules": list(INCLUSION_EXCLUSION_RULES),
            "include_only_scored_acquired_valid_packets_for_future_adjudication": True,
            "exclude_unavailable_invalid_excluded_out_of_route_cap_order_before_adjudication": True,
        },
        "frozen_privacy_publication": {
            "privacy_publication_rules": list(PRIVACY_PUBLICATION_RULES),
            "public_aggregate_or_bucketed_only": True,
            "no_exact_counts_rates_observables_paths_snippets_ids_run_locations": True,
            "no_phase9p_private_scoring_rows_read_in_phase9q": True,
            "no_phase9n_private_packets_read_in_phase9q": True,
            "no_singleton_buckets": True,
        },
        "frozen_future_phase9r_gate": {
            "future_phase9r_gate_rules": list(FUTURE_PHASE9R_GATE_RULES),
            "phase9r_may_execute_adjudication_correctness_only_after_phase9q_commit_and_ci_green": True,
            "phase9r_uses_only_frozen_rules": True,
            "phase9r_private_outputs_ignored_public_aggregate_buckets_only": True,
            "no_adjudication_or_correctness_execution_in_phase9q": True,
        },
        "frozen_no_p_hacking_guardrails": {
            "guardrail_rules": list(NO_P_HACKING_GUARDRAIL_RULES),
            "no_private_or_source_inspection_during_phase9q": True,
            "no_tuning_definitions_after_outcomes_visible": True,
            "no_adjudication_or_correctness_changes_after_scoring": True,
            "no_subgroup_changes_after_scoring": True,
            "no_metric_threshold_tuning_after_outcome_visibility": True,
            "correctness_and_evidence_success_definitions_frozen_now": True,
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
            "protocol_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_phase9h_materialized_sources": True,
            "validator_does_not_read_phase9j_annotation_input_rows": True,
            "validator_does_not_read_phase9l_outcome_packets": True,
            "validator_does_not_read_phase9n_outcome_packets": True,
            "validator_does_not_read_phase9p_scoring_rows": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": (
            "phase9q_freezes_adjudication_correctness_evidence_success_protocol_only"
            "_after_phase9p_scoring_no_execution_no_private_read"
            "_no_phase9p_private_scoring_rows_no_adjudication_no_correctness"
            "_no_evidence_success_no_method_product_claim"
            "_future_execution_requires_separate_frozen_boundary"
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

    # Phase 9P gate references (PRIMARY whitelisted public gate refs).
    gate9p = report.get("phase9p_gate_references", {})
    if gate9p.get("phase9p_commit") != PHASE9P_COMMIT:
        errors.append("Phase 9P commit gate reference drift")
    if gate9p.get("phase9p_ci_run") != PHASE9P_CI_RUN:
        errors.append("Phase 9P CI run gate reference drift")
    if gate9p.get("phase9p_ci_success") is not True:
        errors.append("Phase 9P CI success gate missing")
    if gate9p.get("phase9p_status") != PHASE9P_STATUS:
        errors.append("Phase 9P status gate reference drift")
    if gate9p.get("phase9p_denominator_bucket") != PHASE9P_DENOMINATOR_BUCKET:
        errors.append("Phase 9P denominator_bucket public fact drift")
    if gate9p.get("phase9p_scored_bucket") != PHASE9P_SCORED_BUCKET:
        errors.append("Phase 9P scored_bucket public fact drift")
    if gate9p.get("phase9p_adjudicated_bucket") != PHASE9P_ADJUDICATED_BUCKET:
        errors.append("Phase 9P adjudicated_bucket public fact drift")
    if gate9p.get("phase9p_correctness_bucket") != PHASE9P_CORRECTNESS_BUCKET:
        errors.append("Phase 9P correctness_bucket public fact drift")
    if gate9p.get("phase9p_adjudication_not_executed") is not True:
        errors.append("Phase 9P adjudication not executed boundary missing")
    if gate9p.get("phase9p_correctness_not_computed") is not True:
        errors.append("Phase 9P correctness not computed boundary missing")
    if gate9p.get("phase9p_evidence_success_not_computed") is not True:
        errors.append("Phase 9P evidence_success not computed boundary missing")
    if gate9p.get("phase9p_requires_separate_frozen_boundary_after_scoring") is not True:
        errors.append("Phase 9P requires separate frozen boundary missing")
    if gate9p.get("phase9p_phase9q_gate_true") is not True:
        errors.append("Phase 9P phase9q gate true missing")
    if gate9p.get("phase9p_phase9q_may_be_considered_only_if_denominator_and_scored_buckets_nonzero") is not True:
        errors.append("Phase 9P phase9q may be considered boundary missing")
    if gate9p.get("phase9p_no_adjudication_no_correctness_no_evidence_success_in_phase9p") is not True:
        errors.append("Phase 9P no-adjudication-no-correctness boundary missing")
    if gate9p.get("phase9p_not_proof_adjudication_or_correctness_or_evidence_success") is not True:
        errors.append("Phase 9P not-proof boundary missing")
    if gate9p.get("phase9p_gate_required_before_phase9q") is not True:
        errors.append("Phase 9P gate-required boundary missing")

    # Phase 9O inherited provenance (bucketed only).
    prov9o = report.get("phase9o_inherited_provenance", {})
    if prov9o.get("phase9o_status") != PHASE9O_STATUS:
        errors.append("Phase 9O inherited status drift")
    if prov9o.get("phase9o_ci_success") is not True:
        errors.append("Phase 9O inherited CI success missing")
    if prov9o.get("phase9o_protocol_freeze") is not True:
        errors.append("Phase 9O inherited protocol freeze missing")
    if prov9o.get("phase9o_remote_provenance_bucketed") is not True:
        errors.append("Phase 9O inherited remote provenance must be bucketed")
    if prov9o.get("phase9o_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9O inherited provenance-only boundary missing")

    # Phase 9N inherited provenance (bucketed only).
    prov9n = report.get("phase9n_inherited_provenance", {})
    if prov9n.get("phase9n_status") != PHASE9N_STATUS:
        errors.append("Phase 9N inherited status drift")
    if prov9n.get("phase9n_ci_success") is not True:
        errors.append("Phase 9N inherited CI success missing")
    if prov9n.get("phase9n_acquired_valid_bucket") != "bucket_nonzero_redacted":
        errors.append("Phase 9N inherited acquired_valid_bucket drift")
    if prov9n.get("phase9n_remote_provenance_bucketed") is not True:
        errors.append("Phase 9N inherited remote provenance must be bucketed")
    if prov9n.get("phase9n_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9N inherited provenance-only boundary missing")

    # Phase 9M inherited provenance (bucketed only).
    prov9m = report.get("phase9m_inherited_provenance", {})
    if prov9m.get("phase9m_status") != PHASE9M_STATUS:
        errors.append("Phase 9M inherited status drift")
    if prov9m.get("phase9m_ci_success") is not True:
        errors.append("Phase 9M inherited CI success missing")
    if prov9m.get("phase9m_protocol_freeze") is not True:
        errors.append("Phase 9M inherited protocol freeze missing")
    if prov9m.get("phase9m_remote_provenance_bucketed") is not True:
        errors.append("Phase 9M inherited remote provenance must be bucketed")
    if prov9m.get("phase9m_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9M inherited provenance-only boundary missing")

    # Phase 9L inherited provenance (bucketed only).
    prov9l = report.get("phase9l_inherited_provenance", {})
    if prov9l.get("phase9l_status") != PHASE9L_STATUS:
        errors.append("Phase 9L inherited status drift")
    if prov9l.get("phase9l_ci_success") is not True:
        errors.append("Phase 9L inherited CI success missing")
    if prov9l.get("phase9l_outcome_acquisition_protocol_frozen") is not True:
        errors.append("Phase 9L inherited outcome-acquisition protocol frozen missing")
    if prov9l.get("phase9l_remote_provenance_bucketed") is not True:
        errors.append("Phase 9L inherited remote provenance must be bucketed")
    if prov9l.get("phase9l_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9L inherited provenance-only boundary missing")

    # Phase 9K inherited provenance (bucketed only).
    prov9k = report.get("phase9k_inherited_provenance", {})
    if prov9k.get("phase9k_status") != PHASE9K_STATUS:
        errors.append("Phase 9K inherited status drift")
    if prov9k.get("phase9k_ci_success") is not True:
        errors.append("Phase 9K inherited CI success missing")
    if prov9k.get("phase9k_protocol_freeze") is not True:
        errors.append("Phase 9K inherited protocol freeze missing")
    if prov9k.get("phase9k_remote_provenance_bucketed") is not True:
        errors.append("Phase 9K inherited remote provenance must be bucketed")
    if prov9k.get("phase9k_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9K inherited provenance-only boundary missing")

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

    # Phase 9G inherited provenance (bucketed only).
    prov9g = report.get("phase9g_inherited_provenance", {})
    if prov9g.get("phase9g_status") != PHASE9G_STATUS:
        errors.append("Phase 9G inherited status drift")
    if prov9g.get("phase9g_ci_success") is not True:
        errors.append("Phase 9G inherited CI success missing")
    if prov9g.get("phase9g_protocol_freeze") is not True:
        errors.append("Phase 9G inherited protocol freeze missing")
    if prov9g.get("phase9g_remote_provenance_bucketed") is not True:
        errors.append("Phase 9G inherited remote provenance must be bucketed")
    if prov9g.get("phase9g_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9G inherited provenance-only boundary missing")

    # Phase 9F inherited provenance (bucketed only).
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

    # Phase 9Q scope
    scope = report.get("phase9q_scope", {})
    for key in ("docs_report_validator_only", "protocol_freeze_only"):
        if scope.get(key) is not True:
            errors.append(f"phase9q scope missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase9q execution boundary failed: {key}")
    if scope.get("future_execution_requires_phase9q_commit_and_ci_green") is not True:
        errors.append("phase9q future execution commit+CI-green boundary missing")

    # Frozen adjudication eligibility
    elig = report.get("frozen_adjudication_eligibility", {})
    if elig.get("publication_level") != PROTOCOL_PUBLICATION_LEVEL:
        errors.append("adjudication eligibility publication level drift")
    errors.extend(_check_closed_list(
        elig.get("adjudication_eligibility_predicates"),
        ADJUDICATION_ELIGIBILITY_PREDICATES,
        "frozen_adjudication_eligibility",
        "adjudication_eligibility_predicates",
    ))
    for key in (
        "adjudication_eligible_only_if_scored_in_phase9p_under_frozen_protocol",
        "no_adjudication_executed_in_phase9q",
        "adjudication_eligibility_rule_is_not_adjudicated_truth",
    ):
        if elig.get(key) is not True:
            errors.append(f"frozen adjudication eligibility boundary missing: {key}")

    # Frozen correctness/evidence_success definitions
    defs = report.get("frozen_correctness_evidence_success_definitions", {})
    errors.extend(_check_closed_list(
        defs.get("correctness_evidence_success_definitions"),
        CORRECTNESS_EVIDENCE_SUCCESS_DEFINITIONS,
        "frozen_correctness_evidence_success_definitions",
        "correctness_evidence_success_definitions",
    ))
    for key in (
        "definitions_are_future_definitions_not_executed",
        "correctness_is_deterministic_source_grounded_no_llm_no_provider_no_model",
        "no_precision_recall_pass_fail",
        "no_gold_benchmark_result_annotation_truth_labels",
        "evidence_success_is_aggregate_correctness_bucket_only_not_executed",
    ):
        if defs.get(key) is not True:
            errors.append(f"frozen correctness/evidence_success definitions boundary missing: {key}")

    # Frozen adjudication input boundary
    inp = report.get("frozen_adjudication_input_boundary", {})
    errors.extend(_check_closed_list(
        inp.get("adjudication_input_boundary_rules"),
        ADJUDICATION_INPUT_BOUNDARY_RULES,
        "frozen_adjudication_input_boundary",
        "adjudication_input_boundary_rules",
    ))
    for key in (
        "adjudication_input_is_frozen_outcome_observable_packet_only",
        "adjudication_reads_no_phase9p_private_scoring_rows_as_truth",
        "adjudication_uses_no_provider_llm_model",
        "no_adjudication_input_read_in_phase9q",
    ):
        if inp.get(key) is not True:
            errors.append(f"frozen adjudication input boundary missing: {key}")

    # Frozen inclusion/exclusion
    incl = report.get("frozen_inclusion_exclusion", {})
    errors.extend(_check_closed_list(
        incl.get("inclusion_exclusion_rules"),
        INCLUSION_EXCLUSION_RULES,
        "frozen_inclusion_exclusion",
        "inclusion_exclusion_rules",
    ))
    for key in (
        "include_only_scored_acquired_valid_packets_for_future_adjudication",
        "exclude_unavailable_invalid_excluded_out_of_route_cap_order_before_adjudication",
    ):
        if incl.get(key) is not True:
            errors.append(f"frozen inclusion/exclusion boundary missing: {key}")

    # Frozen privacy/publication
    priv = report.get("frozen_privacy_publication", {})
    errors.extend(_check_closed_list(
        priv.get("privacy_publication_rules"),
        PRIVACY_PUBLICATION_RULES,
        "frozen_privacy_publication",
        "privacy_publication_rules",
    ))
    for key in (
        "public_aggregate_or_bucketed_only",
        "no_exact_counts_rates_observables_paths_snippets_ids_run_locations",
        "no_phase9p_private_scoring_rows_read_in_phase9q",
        "no_phase9n_private_packets_read_in_phase9q",
        "no_singleton_buckets",
    ):
        if priv.get(key) is not True:
            errors.append(f"frozen privacy/publication boundary missing: {key}")

    # Frozen future Phase 9R gate
    gate9r = report.get("frozen_future_phase9r_gate", {})
    errors.extend(_check_closed_list(
        gate9r.get("future_phase9r_gate_rules"),
        FUTURE_PHASE9R_GATE_RULES,
        "frozen_future_phase9r_gate",
        "future_phase9r_gate_rules",
    ))
    for key in (
        "phase9r_may_execute_adjudication_correctness_only_after_phase9q_commit_and_ci_green",
        "phase9r_uses_only_frozen_rules",
        "phase9r_private_outputs_ignored_public_aggregate_buckets_only",
        "no_adjudication_or_correctness_execution_in_phase9q",
    ):
        if gate9r.get(key) is not True:
            errors.append(f"frozen future phase9r gate boundary missing: {key}")

    # Frozen no-p-hacking guardrails
    guard = report.get("frozen_no_p_hacking_guardrails", {})
    errors.extend(_check_closed_list(
        guard.get("guardrail_rules"),
        NO_P_HACKING_GUARDRAIL_RULES,
        "frozen_no_p_hacking_guardrails",
        "guardrail_rules",
    ))
    for key in (
        "no_private_or_source_inspection_during_phase9q",
        "no_tuning_definitions_after_outcomes_visible",
        "no_adjudication_or_correctness_changes_after_scoring",
        "no_subgroup_changes_after_scoring",
        "no_metric_threshold_tuning_after_outcome_visibility",
        "correctness_and_evidence_success_definitions_frozen_now",
    ):
        if guard.get(key) is not True:
            errors.append(f"no-p-hacking guardrail missing: {key}")

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
        "protocol_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_phase9h_materialized_sources",
        "validator_does_not_read_phase9j_annotation_input_rows",
        "validator_does_not_read_phase9l_outcome_packets",
        "validator_does_not_read_phase9n_outcome_packets",
        "validator_does_not_read_phase9p_scoring_rows",
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
        "phase9q_freezes_adjudication_correctness_evidence_success_protocol_only"
        "_after_phase9p_scoring_no_execution_no_private_read"
        "_no_phase9p_private_scoring_rows_no_adjudication_no_correctness"
        "_no_evidence_success_no_method_product_claim"
        "_future_execution_requires_separate_frozen_boundary"
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
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    global PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))
    checks.append(("base_status_equals_required_status", base["status"] == STATUS))
    checks.append(("base_phase_equals_slug", base["phase"] == PHASE))

    # Reject missing/wrong Phase 9P gate references (commit / ci / status /
    # bucket facts).
    for field, bad_val, label in (
        ("phase9p_commit", "deadbeef" * 5, "commit"),
        ("phase9p_ci_run", "0000", "ci_run"),
        ("phase9p_status", "drift", "status"),
        ("phase9p_denominator_bucket", "bucket_wrong", "denominator_bucket"),
        ("phase9p_scored_bucket", "bucket_wrong", "scored_bucket"),
        ("phase9p_adjudicated_bucket", "bucket_wrong", "adjudicated_bucket"),
        ("phase9p_correctness_bucket", "bucket_wrong", "correctness_bucket"),
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9p_gate_references"][field] = bad_val
        checks.append((f"wrong_phase9p_{label}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        del mutated["phase9p_gate_references"][field]
        checks.append((f"missing_phase9p_{label}_rejected", bool(validate_report(mutated))))

    # Reject phase9p gate facts flipped to false.
    for key in (
        "phase9p_adjudication_not_executed",
        "phase9p_correctness_not_computed",
        "phase9p_evidence_success_not_computed",
        "phase9p_requires_separate_frozen_boundary_after_scoring",
        "phase9p_phase9q_gate_true",
        "phase9p_phase9q_may_be_considered_only_if_denominator_and_scored_buckets_nonzero",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9p_gate_references"][key] = False
        checks.append((f"phase9p_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject re-introduction of an exact Phase 9O/9N/9M/9L/9K commit/CI field
    # (the exact remote commit/CI run values are intentionally NOT published;
    # bucketed inherited provenance only).
    for prov_section, commit_key in (
        ("phase9o_inherited_provenance", "phase9o_commit"),
        ("phase9n_inherited_provenance", "phase9n_commit"),
        ("phase9m_inherited_provenance", "phase9m_commit"),
        ("phase9l_inherited_provenance", "phase9l_commit"),
        ("phase9k_inherited_provenance", "phase9k_commit"),
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

    # --- negative mutation: execution booleans true fails. ---
    for exec_key in (
        "scoring_executed",
        "adjudication_executed",
        "correctness_evaluated",
        "evidence_success_evaluated",
        "denominator_computed",
        "gold_rows_generated",
        "benchmark_labels_generated",
        "result_labels_generated",
        "annotation_truth_generated",
        "provider_or_llm_calls",
        "network_fetch_or_clone_or_source_refresh_executed",
        "outcomes_acquired",
        "outcome_route_executed",
        "model_fitting",
        "runtime_default_or_product_changes",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9q_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: ignored_runs_read / private reads true fails. ---
    for private_read_key in (
        "private_phase9h_materialized_sources_read",
        "private_phase9j_annotation_input_rows_read",
        "private_phase9l_outcome_packets_read",
        "private_phase9n_packets_read",
        "private_phase9p_scoring_rows_read",
        "ignored_runs_read",
        "private_candidate_pool_read",
        "private_registry_read",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9q_scope"][private_read_key] = True
        mutated["no_execution_booleans"][private_read_key] = True
        checks.append((f"{private_read_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: 9J-as-truth fails. ---
    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["phase9j_rows_used_as_benchmark_truth"] = True
    mutated["no_execution_booleans"]["phase9j_rows_used_as_benchmark_truth"] = True
    checks.append(("phase9j_as_truth_rejected", bool(validate_report(mutated))))

    # --- negative mutation: Phase9L packets scoreable fails. ---
    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["phase9l_packets_scoreable"] = True
    mutated["no_execution_booleans"]["phase9l_packets_scoreable"] = True
    checks.append(("phase9l_packets_scoreable_rejected", bool(validate_report(mutated))))

    # --- negative mutation: Phase9P scoring rows as adjudication truth fails. ---
    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["phase9p_scoring_rows_used_as_adjudication_truth"] = True
    mutated["no_execution_booleans"]["phase9p_scoring_rows_used_as_adjudication_truth"] = True
    checks.append(("phase9p_scoring_rows_as_truth_rejected", bool(validate_report(mutated))))

    # --- negative mutation: exact count fields fail. ---
    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_adjudication_eligibility"]["adjudicated_count"] = 72
    checks.append(("adjudicated_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_correctness_evidence_success_definitions"]["correctness_count"] = 10
    checks.append(("correctness_count_field_rejected", bool(validate_report(mutated))))

    # --- negative mutation: observable/path/snippet/private-shaped fails. ---
    for label, bad_val in (
        ("url", "https://example.invalid/repo.git"),
        ("owner_repo", "owner/repo"),
        ("hash", "a" * 40),
        ("path", "src/private.py"),
        ("observable_id", "observable_id_42"),
        ("packet_id", "packet_id_99"),
        ("task_id", "task_id_7"),
        ("row_id", "row_id_3"),
        ("run_dir", "runs/secret/run_dir"),
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9q_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: unknown definition fails (set-equality). ---
    mutated = copy.deepcopy(base)
    mutated["frozen_correctness_evidence_success_definitions"]["correctness_evidence_success_definitions"].append("unknown_definition_bucket")
    errors = validate_report(mutated)
    checks.append(("unknown_definition_rejected", bool(errors)))
    checks.append((
        "unknown_definition_set_equality",
        any("has extra members" in e for e in errors),
    ))

    # --- negative mutation: 9P scoring rows as truth inside input boundary. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_adjudication_input_boundary"]["adjudication_input_boundary_rules"].append("phase9p_scoring_rows_used_as_truth")
    errors = validate_report(mutated)
    checks.append(("input_9p_as_truth_member_rejected", bool(errors)))
    checks.append((
        "input_9p_as_truth_set_equality",
        any("has extra members" in e for e in errors),
    ))

    # --- negative mutation: LLM/provider in adjudication input boundary. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_adjudication_input_boundary"]["adjudication_input_boundary_rules"].append("llm_provider_based_adjudication")
    checks.append(("input_llm_member_rejected", bool(validate_report(mutated))))

    # --- negative mutation: flip adjudication input boundary no-llm. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_adjudication_input_boundary"]["adjudication_uses_no_provider_llm_model"] = False
    checks.append(("input_no_llm_boundary_false_rejected", bool(validate_report(mutated))))

    # --- negative mutation: flip no-phase9p-scoring-rows-as-truth boundary. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_adjudication_input_boundary"]["adjudication_reads_no_phase9p_private_scoring_rows_as_truth"] = False
    checks.append(("no_phase9p_as_truth_boundary_false_rejected", bool(validate_report(mutated))))

    # --- negative mutation: precision/recall in correctness definitions. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_correctness_evidence_success_definitions"]["correctness_evidence_success_definitions"].append("precision_recall_computed")
    checks.append(("precision_recall_member_rejected", bool(validate_report(mutated))))

    # --- negative mutation: flip no-precision-recall boundary. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_correctness_evidence_success_definitions"]["no_precision_recall_pass_fail"] = False
    checks.append(("no_precision_recall_boundary_false_rejected", bool(validate_report(mutated))))

    # --- negative mutation: gold labels in correctness definitions. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_correctness_evidence_success_definitions"]["correctness_evidence_success_definitions"].append("gold_labels_generated")
    checks.append(("gold_labels_member_rejected", bool(validate_report(mutated))))

    # Reject claim boundary set to true.
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject privacy contract violations.
    for privacy_key in (
        "per_source_public_facts",
        "per_task_public_facts",
        "per_packet_public_facts",
        "run_locations_public",
        "repo_names_public",
        "outcome_observables_public",
        "outcome_packets_public",
        "phase9p_scoring_rows_public",
        "phase9n_packets_public",
        "packet_ids_public",
    ):
        mutated = copy.deepcopy(base)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1", "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(base)
        mutated["frozen_inclusion_exclusion"]["inclusion_exclusion_rules"].append(singleton_val)
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((
            f"singleton_regex_{singleton_val}",
            bool(SINGLETON_BUCKET_RE.search(singleton_val)),
        ))

    # Reject private-shaped keys (defense-in-depth beyond allowed-schema check).
    for bad_key in (
        "private_source_commit",
        "repo_commit",
        "task_ci_run",
        "per_source_bucket",
        "per_task_summary",
        "per_packet_summary",
        "source_path_bucket",
        "path",
        "repo_name",
        "task_id",
        "row_id",
        "packet_id",
        "observable_id",
        "manifest",
        "run_dir",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9q_scope"][bad_key] = "example"
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
    mutated["conservative_recommendation"] = "adjudication works and is proven"
    checks.append(("claim_wording_adjudication_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_correctness_evidence_success_definitions"]["correctness_evidence_success_definitions"].append("correctness proven")
    checks.append(("claim_wording_correctness_proven_rejected", bool(validate_report(mutated))))

    for phrase in (
        "method effectiveness",
        "product readiness",
        "scoring success",
        "outcome success",
        "evaluation works",
        "acquisition success",
        "adjudication proven",
        "correctness proven",
        "evidence_success achieved",
        "lift achieved",
    ):
        mutated = copy.deepcopy(base)
        mutated["frozen_privacy_publication"]["privacy_publication_rules"].append(phrase)
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
    mutated["frozen_future_phase9r_gate"]["future_phase9r_gate_rules"].append("user must approve continuation")
    checks.append(("user_must_approve_wording_rejected", bool(validate_report(mutated))))

    # Reject placeholder/TBD/TODO wording in exposed string values.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(base)
        mutated["frozen_adjudication_eligibility"]["adjudication_eligibility_predicates"].append(phrase)
        checks.append((
            f"placeholder_{phrase}_rejected",
            bool(validate_report(mutated)),
        ))
        checks.append((
            f"placeholder_regex_{phrase}",
            bool(PLACEHOLDER_RE.search(phrase)),
        ))

    # Reject future execution without phase9q commit+CI green.
    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["future_execution_requires_phase9q_commit_and_ci_green"] = False
    checks.append(("future_execution_without_commit_ci_rejected", bool(validate_report(mutated))))

    # Reject a missing required closed-list member (vocabulary drift).
    mutated = copy.deepcopy(base)
    mutated["frozen_adjudication_eligibility"]["adjudication_eligibility_predicates"] = [
        p for p in base["frozen_adjudication_eligibility"]["adjudication_eligibility_predicates"]
        if p != ADJUDICATION_ELIGIBILITY_PREDICATES[0]
    ]
    checks.append(("missing_required_adjudication_predicate_rejected", bool(validate_report(mutated))))

    # Reject EXTRA members in every closed protocol list (set-equality).
    for section, key, expected, label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(base)
        mutated[section][key].append("extra_bogus_member")
        errors = validate_report(mutated)
        checks.append((f"extra_{label}_member_rejected", bool(errors)))
        checks.append((
            f"extra_{label}_member_set_equality",
            any("has extra members" in e for e in errors),
        ))

    # Reject a reworded closed-list member (set-equality catches vocabulary drift).
    mutated = copy.deepcopy(base)
    mutated["frozen_correctness_evidence_success_definitions"]["correctness_evidence_success_definitions"][0] = "correctness_count_exact"
    checks.append(("correctness_definition_vocabulary_drift_rejected", bool(validate_report(mutated))))

    # Reject conservative recommendation drift.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))

    # Reject truth-boundary violation.
    mutated = copy.deepcopy(base)
    mutated["truth_boundary"]["adjudication_eligibility_rule_is_not_adjudicated_truth"] = False
    checks.append(("truth_boundary_adjudication_not_truth_rejected", bool(validate_report(mutated))))

    # Non-whitelisted CI run key/value is rejected.
    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["task_ci_run"] = "28987083201"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    checks.append((
        "non_whitelisted_ci_run_key_not_exempt",
        any("private-shaped public key" in e for e in errors),
    ))

    # Gate-reference commit values are exempt from private-shaped value scan
    # but a non-gate-reference key with a hash value is still rejected.
    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["example_hash"] = "511a765135bd53c724fb593db0c9ea5ebb38a500"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    # Validate a temp-file round-trip (synthetic fixture only, no private reads).
    with tempfile.TemporaryDirectory(prefix="phase9q_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- strict allowed-key checking rejects unknown fields. ---
    mutated = copy.deepcopy(base)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9q_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_adjudication_eligibility"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_eligibility_rejected", bool(validate_report(mutated))))

    # --- --validate-report fails closed on ignored/private paths. ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9q" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9q_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "artifacts" / "phase9p_frozen_scoring_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading (no real file needed).
    runs_cli_path = str(REPO / "runs" / "phase9q" / "report.json")
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
    checks.append((
        "selftest_does_not_read_phase9n_outcome_packets",
        PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS == 0,
    ))
    checks.append((
        "selftest_does_not_read_phase9p_scoring_rows",
        PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS == 0,
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
        description="Phase 9Q adjudication/correctness/evidence_success protocol freeze"
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
        # Fail closed: --validate-report may only read the Phase 9Q public
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
