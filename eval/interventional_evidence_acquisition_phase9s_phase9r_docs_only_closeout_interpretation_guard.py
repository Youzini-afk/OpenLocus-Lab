#!/usr/bin/env python3
"""Phase 9S Phase 9R docs-only closeout / interpretation guard (no claim).

This is a docs/report/validator-only closeout and interpretation guard applied
after Phase 9R.  It has one narrow purpose: interpret Phase 9R narrowly -- only
"the Phase 9Q frozen adjudication/correctness/evidence_success protocol was
applied exactly once and produced bucketed nonzero aggregate protocol-
application buckets" -- and guard against any post-outcome protocol movement,
numerical/publication expansion, or generalized success claim.

It does NOT fetch, clone, read, or materialize any repository or source, does
NOT read ignored ``runs/``, the Phase 9R private adjudication rows, the Phase
9P private scoring rows, the Phase 9N private outcome-observable packets, the
Phase 9H private materialized sources, the Phase 9J private annotation-input
rows/manifests, or the Phase 9L private outcome-acquisition packets/manifests,
does NOT execute, score, adjudicate, recompute correctness/evidence_success,
change denominators/inclusion/exclusion, fetch/clone/source refresh, or make
any provider/LLM/model call.  It does NOT introduce any new metric/threshold/
subgroup/denominator/inclusion/exclusion/correctness/evidence_success rule and
does NOT repair based on Phase 9R results.

The Phase 9R public gate reference values (remote commit, CI run, status, and
the three nonzero public buckets ``adjudicated_bucket``/``correctness_bucket``/
``evidence_success_bucket`` = ``bucket_nonzero_redacted``) are the only exact
public gate references published by Phase 9S.  Phase 9Q and Phase 9P are
carried forward only as status/bucket inherited provenance; their full commit
SHAs and CI runs are intentionally NOT republished by Phase 9S.  Phase 9O
through Phase 9F are likewise carried as inherited provenance only and their
exact remote commit/CI run values are intentionally NOT published in the Phase
9S report/docs (tighter privacy).  Local same-tree git commits are not read or
compared; only the Phase 9R public gate constants are exact gate references.

Interpretation-boundary is explicit: Phase 9R is interpreted ONLY as protocol-
application results (the frozen Phase 9Q protocol applied exactly once and
produced bucketed nonzero aggregate protocol-application buckets); it is
explicitly NOT method success, product success, performance, provider/model
quality, runtime/default readiness, annotation truth, benchmark truth, scoring
quality, adjudication quality, or generalized evidence-acquisition success.

Future validation needs are DEFINED ONLY: any future strengthening requires a
separate independent validation line with a fresh pre-frozen protocol, fresh/
fenced inputs, independent replication packet generation, and execution only
after commit/CI-green confirmation.  Phase 9S does NOT freeze or run that future
protocol.
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

# Compact Phase 9S slug (kept short so the absolute artifact report path stays
# comfortably under the Windows MAX_PATH (260) limit).  Boundary wording in
# the report body/docs is NOT weakened -- only the path-dependent slug is
# shortened.
PHASE = "phase9s_phase9r_docs_only_closeout_interpretation_guard_no_claim"
# Honest closeout wording: Phase 9R is docs-only closed as an interpretation
# guard (no execution, no private read, no new metrics, no claim).  Not
# "success"/"validated"/"proven"/"established" (forbidden wording); "closeout"
# honestly reflects that only a docs/report/validator interpretation guard is
# applied, with no execution and no new metrics.
STATUS = (
    "phase9s_phase9r_docs_only_closeout_interpretation_guard"
    "_no_execution_no_private_read_no_new_metrics_no_claim"
)
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

# ---------------------------------------------------------------------------
# Phase 9R public gate reference values (oracle-provided).  These are the
# PRIMARY public gate references published by Phase 9S.  Local same-tree git
# commits are not read or compared; the supplied confirmation values are
# matched against the frozen public gate constants only.
# ---------------------------------------------------------------------------
PHASE9R_STATUS = (
    "phase9r_frozen_adjudication_correctness_evidence_success_executed"
    "_bucketed_aggregate_no_private_publication_no_claim"
)
PHASE9R_COMMIT = "304aff6fd52b80680f91bd077a2760e4a95edc5f"
PHASE9R_CI_RUN = "28989276491"
# Phase 9R public bucket facts (aggregate bucket only, no exact count).  These
# are the "bucketed nonzero aggregate protocol-application buckets" that Phase
# 9S interprets Phase 9R as having produced.
PHASE9R_ADJUDICATED_BUCKET = "bucket_nonzero_redacted"
PHASE9R_CORRECTNESS_BUCKET = "bucket_nonzero_redacted"
PHASE9R_EVIDENCE_SUCCESS_BUCKET = "bucket_nonzero_redacted"

PHASE9R_PUBLIC_REPORT = (
    REPO / "artifacts"
    / "phase9r_frozen_adjudication_correctness_evidence_success_execution_no_claim"
    / "phase9r_frozen_adjudication_correctness_evidence_success_execution_no_claim_report.json"
)

# Phase 9Q inherited provenance (status/boolean only; exact commit/CI is not
# republished by Phase 9S).
PHASE9Q_STATUS = (
    "phase9q_adjudication_correctness_protocol_freeze"
    "_no_execution_no_private_read_no_adjudication_no_correctness"
    "_no_evidence_success_no_claim"
)

# Phase 9P inherited provenance (status/buckets only; exact commit/CI is not
# republished by Phase 9S).
PHASE9P_STATUS = (
    "phase9p_frozen_scoring_executed_denominator_nonzero_scored_nonzero"
    "_adjudication_not_executed_separate_frozen_boundary_required"
    "_no_evidence_success_no_claim"
)
PHASE9P_DENOMINATOR_BUCKET = "bucket_nonzero_redacted"
PHASE9P_SCORED_BUCKET = "bucket_nonzero_redacted"
PHASE9P_ADJUDICATED_BUCKET = "bucket_zero"
PHASE9P_CORRECTNESS_BUCKET = "bucket_zero"

# Phase 9O through Phase 9F inherited provenance (carried forward, bucketed
# only).  The exact remote commit/CI run values are intentionally NOT
# published in the Phase 9S report/docs (tighter privacy).
PHASE9O_STATUS = (
    "phase9o_scoring_denominator_adjudication_protocol_freeze"
    "_no_execution_no_private_read_no_scoring_no_claim"
)
PHASE9N_STATUS = (
    "phase9n_frozen_route_executed_valid_acquired_nonzero_aggregate_availability"
    "_no_scoring_no_adjudication_no_claim"
)
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

# ---------------------------------------------------------------------------
# Frozen Phase 9S interpretation-guard closed lists (validator set-equality
# checked).  These are STRUCTURAL interpretation-guard definitions only; no
# execution, scoring, adjudication, correctness/evidence_success recomputation,
# denominator change, or protocol movement occurs in Phase 9S.
# ---------------------------------------------------------------------------
PROTOCOL_PUBLICATION_LEVEL = "aggregate_bucketed_protocol_application_results_only"

# 1. Phase 9R narrow interpretation rule: Phase 9R is interpreted ONLY as
#    protocol-application results (frozen Phase 9Q protocol applied exactly
#    once, bucketed nonzero aggregate protocol-application buckets).  It is
#    explicitly NOT any kind of generalized success.
PHASE9R_INTERPRETATION_RULES = (
    "phase9r_applied_phase9q_frozen_adjudication_correctness_evidence_success_protocol_exactly_once",
    "phase9r_produced_bucketed_nonzero_aggregate_protocol_application_buckets_only",
    "phase9r_interpretation_is_protocol_application_results_only_not_outcome_success",
    "phase9r_interpretation_is_not_method_success",
    "phase9r_interpretation_is_not_product_success",
    "phase9r_interpretation_is_not_performance_success",
    "phase9r_interpretation_is_not_provider_or_model_quality",
    "phase9r_interpretation_is_not_runtime_or_default_readiness",
    "phase9r_interpretation_is_not_annotation_truth",
    "phase9r_interpretation_is_not_benchmark_truth",
    "phase9r_interpretation_is_not_scoring_quality",
    "phase9r_interpretation_is_not_adjudication_quality",
    "phase9r_interpretation_is_not_generalized_evidence_acquisition_success",
)

# 2. No post-outcome protocol movement: no new metrics, thresholds, subgroups,
#    denominator/inclusion/exclusion edits, correctness/evidence_success
#    definition edits, or repair based on Phase 9R results.
NO_POST_OUTCOME_PROTOCOL_MOVEMENT_RULES = (
    "no_new_metrics_introduced_based_on_phase9r_results",
    "no_new_thresholds_introduced_based_on_phase9r_results",
    "no_new_subgroups_introduced_based_on_phase9r_results",
    "no_denominator_inclusion_or_exclusion_edits_based_on_phase9r_results",
    "no_correctness_or_evidence_success_definition_edits_based_on_phase9r_results",
    "no_repair_based_on_phase9r_results",
    "no_protocol_movement_after_phase9r_outcome_visibility",
)

# 3. Privacy/publication boundary: public only buckets; no exact counts/rates/
#    ids/observables/snippets/source/repo/path/run locations/per-task/per-
#    source/per-packet facts/singleton buckets; no Phase 9R private rows; no
#    ignored runs/ read in Phase 9S.
PRIVACY_PUBLICATION_RULES = (
    "public_aggregate_or_bucketed_only",
    "no_exact_counts_or_rates_public",
    "no_ids_observables_or_snippets_public",
    "no_source_repo_path_or_run_locations_public",
    "no_per_task_per_source_or_per_packet_facts_public",
    "no_singleton_buckets_public",
    "no_phase9r_private_adjudication_rows_read_in_phase9s",
    "no_phase9p_private_scoring_rows_read_in_phase9s",
    "no_phase9n_private_packets_read_in_phase9s",
    "no_phase9h_phase9j_or_phase9l_private_material_read_in_phase9s",
    "no_ignored_runs_read_in_phase9s",
)

# 4. Future validation needs are DEFINED ONLY: any future strengthening
#    requires a separate independent validation line with a fresh pre-frozen
#    protocol, fresh/fenced inputs, independent replication packet generation,
#    and execution only after commit/CI-green confirmation.  Phase 9S does NOT
#    freeze or run that future protocol.
FUTURE_VALIDATION_NEEDS_RULES = (
    "future_strengthening_requires_separate_independent_validation_line",
    "future_protocol_must_be_pre_frozen_before_any_execution",
    "future_inputs_must_be_fresh_and_fenced",
    "future_replication_packet_generation_must_be_independent",
    "future_execution_only_after_commit_and_ci_green_confirmation",
    "phase9s_does_not_freeze_or_run_any_future_protocol",
)

# Frozen no-p-hacking / no-execution guardrails.
NO_EXECUTION_GUARDRAIL_RULES = (
    "no_execution_in_phase9s",
    "no_scoring_in_phase9s",
    "no_adjudication_in_phase9s",
    "no_correctness_or_evidence_success_recomputation_in_phase9s",
    "no_denominator_changes_in_phase9s",
    "no_source_fetch_clone_or_refresh_in_phase9s",
    "no_provider_llm_or_model_calls_in_phase9s",
    "no_private_reads_in_phase9s",
    "no_protocol_edits_after_phase9r_outcome_visibility",
)

# Truth-boundary attestation keys that must always be True in the public report.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9r_interpreted_as_protocol_application_results_only",
    "phase9r_buckets_are_protocol_application_buckets_not_success_buckets",
    "phase9r_interpretation_is_not_generalized_success",
    "phase9s_closeout_is_docs_report_validator_only",
    "phase9s_does_not_recompute_or_repair_phase9r_results",
    "future_validation_requires_separate_independent_line_not_continuation_of_phase9r",
)

# Boundary attestation keys that must always be False in the public report.
NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "outcome_route_executed",
    "outcomes_acquired",
    "task_annotation_generated",
    "scoring_executed",
    "adjudication_executed",
    "correctness_evaluated",
    "evidence_success_evaluated",
    "correctness_or_evidence_success_recomputed",
    "denominator_computed",
    "denominator_changed",
    "inclusion_exclusion_edited",
    "private_phase9r_adjudication_rows_read",
    "private_phase9p_scoring_rows_read",
    "private_phase9n_packets_read",
    "private_phase9h_materialized_sources_read",
    "private_phase9j_annotation_input_rows_read",
    "private_phase9l_outcome_packets_read",
    "private_candidate_pool_read",
    "private_registry_read",
    "ignored_runs_read",
    "annotations_generated",
    "gold_rows_generated",
    "benchmark_labels_generated",
    "result_labels_generated",
    "annotation_truth_generated",
    "evaluation_rows_generated",
    "phase9j_rows_used_as_benchmark_truth",
    "phase9l_packets_scoreable",
    "phase9p_scoring_rows_used_as_adjudication_truth",
    "phase9r_rows_used_as_truth",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
    "network_fetch_or_clone_or_source_refresh_executed",
    "new_metrics_introduced",
    "new_thresholds_introduced",
    "new_subgroups_introduced",
    "protocol_edited_after_outcome_visibility",
    "repair_based_on_phase9r_results",
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
    "benchmark_truth_claim",
    "generalized_evidence_acquisition_success_claim",
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
    "phase9r_private_adjudication_rows_public",
    "phase9p_scoring_rows_public",
    "phase9n_packets_public",
    "phase9l_packets_public",
    "exact_counts_or_rates_public",
)

# Forbidden public field words; only apply to non-boolean values at
# non-allowed-schema paths so boolean boundary attestation keys such as
# ``adjudication_executed`` and section names such as
# ``frozen_phase9r_interpretation`` (which are at allowed-schema paths)
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
    ("frozen_phase9r_interpretation", "phase9r_interpretation_rules", PHASE9R_INTERPRETATION_RULES, "phase9r_interpretation"),
    ("frozen_no_post_outcome_protocol_movement", "no_post_outcome_protocol_movement_rules", NO_POST_OUTCOME_PROTOCOL_MOVEMENT_RULES, "no_protocol_movement"),
    ("frozen_privacy_publication", "privacy_publication_rules", PRIVACY_PUBLICATION_RULES, "privacy"),
    ("frozen_future_validation_needs", "future_validation_needs_rules", FUTURE_VALIDATION_NEEDS_RULES, "future_validation_needs"),
    ("frozen_no_execution_guardrails", "no_execution_guardrail_rules", NO_EXECUTION_GUARDRAIL_RULES, "no_execution_guardrails"),
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
    r"|evidence[-_ ]acquisition\s+success"
    r"|generalized\s+success"
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
# public gate constants (full commit SHA / CI run ID).  Phase 9S only publishes
# exact Phase 9R gate refs; older phases remain status/bucket provenance only.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.phase9r_gate_references.phase9r_commit",
        "$.phase9r_gate_references.phase9r_ci_run",
    }
)

# Exact public gate-reference JSON paths whose string VALUES are CI run IDs
# (long decimal integers).
DECIMAL_CI_RUN_EXEMPT_PATHS = frozenset(
    {
        "$.phase9r_gate_references.phase9r_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9R_ADJUDICATION_ROWS_READ_ATTEMPTS = 0
PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS = 0
PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0

CONSERVATIVE_RECOMMENDATION = (
    "phase9s_closes_phase9r_as_docs_only_interpretation_guard"
    "_phase9r_interpreted_as_protocol_application_results_only"
    "_bucketed_nonzero_aggregate_protocol_application_buckets_not_generalized_success"
    "_no_execution_no_private_read_no_new_metrics_no_repair"
    "_future_strengthening_requires_separate_independent_validation_line"
    "_no_method_product_performance_provider_model_runtime_default"
    "_scoring_outcome_evidence_success_annotation_truth_adjudication_correctness_claim"
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
    "phase9r_gate_references": {
        "phase9r_commit": None,
        "phase9r_ci_run": None,
        "phase9r_ci_success": None,
        "phase9r_status": None,
        "phase9r_adjudicated_bucket": None,
        "phase9r_correctness_bucket": None,
        "phase9r_evidence_success_bucket": None,
        "phase9r_protocol_applied_exactly_once": None,
        "phase9r_bucketed_nonzero_aggregate_protocol_application_buckets": None,
        "phase9r_gate_required_before_phase9s": None,
        "phase9r_public_report_validated": None,
    },
    "phase9q_inherited_provenance": {
        "phase9q_ci_success": None,
        "phase9q_status": None,
        "phase9q_protocol_freeze": None,
        "phase9q_did_not_execute_adjudication_or_correctness": None,
        "phase9q_carried_as_inherited_provenance_only": None,
    },
    "phase9p_inherited_provenance": {
        "phase9p_ci_success": None,
        "phase9p_status": None,
        "phase9p_denominator_bucket": None,
        "phase9p_scored_bucket": None,
        "phase9p_adjudicated_bucket": None,
        "phase9p_correctness_bucket": None,
        "phase9p_adjudication_not_executed": None,
        "phase9p_correctness_not_computed": None,
        "phase9p_evidence_success_not_computed": None,
        "phase9p_carried_as_inherited_provenance_only": None,
    },
    "inherited_provenance_bucketed": {
        "phase9o_status": None,
        "phase9o_carried_as_inherited_provenance_only": None,
        "phase9n_status": None,
        "phase9n_carried_as_inherited_provenance_only": None,
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
    "phase9s_scope": {
        "docs_report_validator_only": None,
        "closeout_interpretation_guard_only": None,
        "public_fetch_clone_executed": None,
        "source_materialization_executed": None,
        "outcome_route_executed": None,
        "outcomes_acquired": None,
        "task_annotation_generated": None,
        "scoring_executed": None,
        "adjudication_executed": None,
        "correctness_evaluated": None,
        "evidence_success_evaluated": None,
        "correctness_or_evidence_success_recomputed": None,
        "denominator_computed": None,
        "denominator_changed": None,
        "inclusion_exclusion_edited": None,
        "private_phase9r_adjudication_rows_read": None,
        "private_phase9p_scoring_rows_read": None,
        "private_phase9n_packets_read": None,
        "private_phase9h_materialized_sources_read": None,
        "private_phase9j_annotation_input_rows_read": None,
        "private_phase9l_outcome_packets_read": None,
        "private_candidate_pool_read": None,
        "private_registry_read": None,
        "ignored_runs_read": None,
        "annotations_generated": None,
        "gold_rows_generated": None,
        "benchmark_labels_generated": None,
        "result_labels_generated": None,
        "annotation_truth_generated": None,
        "evaluation_rows_generated": None,
        "phase9j_rows_used_as_benchmark_truth": None,
        "phase9l_packets_scoreable": None,
        "phase9p_scoring_rows_used_as_adjudication_truth": None,
        "phase9r_rows_used_as_truth": None,
        "model_fitting": None,
        "provider_or_llm_calls": None,
        "runtime_default_or_product_changes": None,
        "network_fetch_or_clone_or_source_refresh_executed": None,
        "new_metrics_introduced": None,
        "new_thresholds_introduced": None,
        "new_subgroups_introduced": None,
        "protocol_edited_after_outcome_visibility": None,
        "repair_based_on_phase9r_results": None,
    },
    "frozen_phase9r_interpretation": {
        "publication_level": None,
        "phase9r_interpretation_rules": None,
        "phase9r_applied_phase9q_frozen_protocol_exactly_once": None,
        "phase9r_produced_bucketed_nonzero_aggregate_protocol_application_buckets_only": None,
        "phase9r_interpretation_is_protocol_application_results_only_not_generalized_success": None,
    },
    "frozen_no_post_outcome_protocol_movement": {
        "no_post_outcome_protocol_movement_rules": None,
        "no_new_metrics_thresholds_subgroups_based_on_phase9r_results": None,
        "no_denominator_inclusion_exclusion_correctness_evidence_success_edits": None,
        "no_repair_based_on_phase9r_results": None,
    },
    "frozen_privacy_publication": {
        "privacy_publication_rules": None,
        "public_aggregate_or_bucketed_only": None,
        "no_exact_counts_rates_ids_observables_snippets_paths_run_locations": None,
        "no_phase9r_private_adjudication_rows_read_in_phase9s": None,
        "no_ignored_runs_read_in_phase9s": None,
        "no_singleton_buckets": None,
    },
    "frozen_future_validation_needs": {
        "future_validation_needs_rules": None,
        "future_strengthening_requires_separate_independent_validation_line": None,
        "future_protocol_must_be_pre_frozen_before_any_execution": None,
        "future_execution_only_after_commit_and_ci_green_confirmation": None,
        "phase9s_does_not_freeze_or_run_any_future_protocol": None,
    },
    "frozen_no_execution_guardrails": {
        "no_execution_guardrail_rules": None,
        "no_execution_no_scoring_no_adjudication_in_phase9s": None,
        "no_correctness_or_evidence_success_recomputation_in_phase9s": None,
        "no_private_reads_in_phase9s": None,
        "no_protocol_edits_after_phase9r_outcome_visibility": None,
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
        "phase9s_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_phase9r_adjudication_rows": None,
        "validator_does_not_read_phase9p_scoring_rows": None,
        "validator_does_not_read_phase9n_packets": None,
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

    The report path must be under the Phase 9S public artifact directory
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
        return False, "report path is not under the Phase 9S public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report(phase9r_gate_ok: bool = True) -> dict[str, Any]:
    """Build the frozen Phase 9S public closeout/interpretation-guard report.

    This function performs no network/filesystem fetch and no private reads.
    It assembles the frozen closeout document from static constants.  The
    Phase 9R public report is referenced as a public gate fact only when
    ``--validate-report`` is invoked against an already-written report; this
    builder itself does not read it.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9r_gate_references": {
            "phase9r_commit": PHASE9R_COMMIT,
            "phase9r_ci_run": PHASE9R_CI_RUN,
            "phase9r_ci_success": True,
            "phase9r_status": PHASE9R_STATUS,
            "phase9r_adjudicated_bucket": PHASE9R_ADJUDICATED_BUCKET,
            "phase9r_correctness_bucket": PHASE9R_CORRECTNESS_BUCKET,
            "phase9r_evidence_success_bucket": PHASE9R_EVIDENCE_SUCCESS_BUCKET,
            "phase9r_protocol_applied_exactly_once": True,
            "phase9r_bucketed_nonzero_aggregate_protocol_application_buckets": True,
            "phase9r_gate_required_before_phase9s": True,
            "phase9r_public_report_validated": phase9r_gate_ok,
        },
        "phase9q_inherited_provenance": {
            "phase9q_ci_success": True,
            "phase9q_status": PHASE9Q_STATUS,
            "phase9q_protocol_freeze": True,
            "phase9q_did_not_execute_adjudication_or_correctness": True,
            "phase9q_carried_as_inherited_provenance_only": True,
        },
        "phase9p_inherited_provenance": {
            "phase9p_ci_success": True,
            "phase9p_status": PHASE9P_STATUS,
            "phase9p_denominator_bucket": PHASE9P_DENOMINATOR_BUCKET,
            "phase9p_scored_bucket": PHASE9P_SCORED_BUCKET,
            "phase9p_adjudicated_bucket": PHASE9P_ADJUDICATED_BUCKET,
            "phase9p_correctness_bucket": PHASE9P_CORRECTNESS_BUCKET,
            "phase9p_adjudication_not_executed": True,
            "phase9p_correctness_not_computed": True,
            "phase9p_evidence_success_not_computed": True,
            "phase9p_carried_as_inherited_provenance_only": True,
        },
        "inherited_provenance_bucketed": {
            "phase9o_status": PHASE9O_STATUS,
            "phase9o_carried_as_inherited_provenance_only": True,
            "phase9n_status": PHASE9N_STATUS,
            "phase9n_carried_as_inherited_provenance_only": True,
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
        "phase9s_scope": {
            "docs_report_validator_only": True,
            "closeout_interpretation_guard_only": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "outcome_route_executed": False,
            "outcomes_acquired": False,
            "task_annotation_generated": False,
            "scoring_executed": False,
            "adjudication_executed": False,
            "correctness_evaluated": False,
            "evidence_success_evaluated": False,
            "correctness_or_evidence_success_recomputed": False,
            "denominator_computed": False,
            "denominator_changed": False,
            "inclusion_exclusion_edited": False,
            "private_phase9r_adjudication_rows_read": False,
            "private_phase9p_scoring_rows_read": False,
            "private_phase9n_packets_read": False,
            "private_phase9h_materialized_sources_read": False,
            "private_phase9j_annotation_input_rows_read": False,
            "private_phase9l_outcome_packets_read": False,
            "private_candidate_pool_read": False,
            "private_registry_read": False,
            "ignored_runs_read": False,
            "annotations_generated": False,
            "gold_rows_generated": False,
            "benchmark_labels_generated": False,
            "result_labels_generated": False,
            "annotation_truth_generated": False,
            "evaluation_rows_generated": False,
            "phase9j_rows_used_as_benchmark_truth": False,
            "phase9l_packets_scoreable": False,
            "phase9p_scoring_rows_used_as_adjudication_truth": False,
            "phase9r_rows_used_as_truth": False,
            "model_fitting": False,
            "provider_or_llm_calls": False,
            "runtime_default_or_product_changes": False,
            "network_fetch_or_clone_or_source_refresh_executed": False,
            "new_metrics_introduced": False,
            "new_thresholds_introduced": False,
            "new_subgroups_introduced": False,
            "protocol_edited_after_outcome_visibility": False,
            "repair_based_on_phase9r_results": False,
        },
        "frozen_phase9r_interpretation": {
            "publication_level": PROTOCOL_PUBLICATION_LEVEL,
            "phase9r_interpretation_rules": list(PHASE9R_INTERPRETATION_RULES),
            "phase9r_applied_phase9q_frozen_protocol_exactly_once": True,
            "phase9r_produced_bucketed_nonzero_aggregate_protocol_application_buckets_only": True,
            "phase9r_interpretation_is_protocol_application_results_only_not_generalized_success": True,
        },
        "frozen_no_post_outcome_protocol_movement": {
            "no_post_outcome_protocol_movement_rules": list(NO_POST_OUTCOME_PROTOCOL_MOVEMENT_RULES),
            "no_new_metrics_thresholds_subgroups_based_on_phase9r_results": True,
            "no_denominator_inclusion_exclusion_correctness_evidence_success_edits": True,
            "no_repair_based_on_phase9r_results": True,
        },
        "frozen_privacy_publication": {
            "privacy_publication_rules": list(PRIVACY_PUBLICATION_RULES),
            "public_aggregate_or_bucketed_only": True,
            "no_exact_counts_rates_ids_observables_snippets_paths_run_locations": True,
            "no_phase9r_private_adjudication_rows_read_in_phase9s": True,
            "no_ignored_runs_read_in_phase9s": True,
            "no_singleton_buckets": True,
        },
        "frozen_future_validation_needs": {
            "future_validation_needs_rules": list(FUTURE_VALIDATION_NEEDS_RULES),
            "future_strengthening_requires_separate_independent_validation_line": True,
            "future_protocol_must_be_pre_frozen_before_any_execution": True,
            "future_execution_only_after_commit_and_ci_green_confirmation": True,
            "phase9s_does_not_freeze_or_run_any_future_protocol": True,
        },
        "frozen_no_execution_guardrails": {
            "no_execution_guardrail_rules": list(NO_EXECUTION_GUARDRAIL_RULES),
            "no_execution_no_scoring_no_adjudication_in_phase9s": True,
            "no_correctness_or_evidence_success_recomputation_in_phase9s": True,
            "no_private_reads_in_phase9s": True,
            "no_protocol_edits_after_phase9r_outcome_visibility": True,
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
            "phase9s_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_phase9r_adjudication_rows": True,
            "validator_does_not_read_phase9p_scoring_rows": True,
            "validator_does_not_read_phase9n_packets": True,
            "validator_does_not_read_phase9h_materialized_sources": True,
            "validator_does_not_read_phase9j_annotation_input_rows": True,
            "validator_does_not_read_phase9l_outcome_packets": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
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


def _phase9r_gate_errors(
    report: Any | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
    supplied_status: str | None = None,
) -> list[str]:
    """Validate the Phase 9R public report gate facts.

    Reads ONLY the Phase 9R public artifact report under ``artifacts/`` (a
    public artifact, not a private read).  Confirms the Phase 9R commit/CI/
    status and the three nonzero public buckets match the frozen gate
    constants.  Does NOT read ignored ``runs/`` or any private adjudication
    rows.
    """
    errors: list[str] = []
    if report is None:
        if not PHASE9R_PUBLIC_REPORT.exists():
            return ["Phase 9R public report missing"]
        report = json.loads(PHASE9R_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9R public report must be object"]
    if report.get("status") != PHASE9R_STATUS:
        errors.append("Phase 9R public report status drift")
    if report.get("phase") != "phase9r_frozen_adjudication_correctness_evidence_success_execution_no_claim":
        errors.append("Phase 9R public report phase drift")
    buckets = report.get("adjudication_buckets", {})
    if buckets.get("adjudicated_bucket") != PHASE9R_ADJUDICATED_BUCKET:
        errors.append("Phase 9R public report adjudicated_bucket drift")
    if buckets.get("correctness_bucket") != PHASE9R_CORRECTNESS_BUCKET:
        errors.append("Phase 9R public report correctness_bucket drift")
    if buckets.get("evidence_success_bucket") != PHASE9R_EVIDENCE_SUCCESS_BUCKET:
        errors.append("Phase 9R public report evidence_success_bucket drift")
    for key in ("adjudication_executed_once", "correctness_evaluated_once",
                "evidence_success_is_aggregate_correctness_bucket_only"):
        if buckets.get(key) is not True:
            errors.append(f"Phase 9R public report bucket boundary missing: {key}")
    execs = report.get("execution_booleans", {})
    if execs.get("adjudication_executed") is not True:
        errors.append("Phase 9R public report adjudication_executed must be true")
    if execs.get("correctness_evaluated") is not True:
        errors.append("Phase 9R public report correctness_evaluated must be true")
    if execs.get("evidence_success_evaluated") is not True:
        errors.append("Phase 9R public report evidence_success_evaluated must be true")
    if execs.get("adjudication_repaired_after_private_reads") is not False:
        errors.append("Phase 9R public report adjudication_repaired_after_private_reads must be false")
    if supplied_commit is not None and supplied_commit != PHASE9R_COMMIT:
        errors.append("supplied Phase 9R commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9R_CI_RUN:
        errors.append("supplied Phase 9R CI run does not match public gate reference")
    if supplied_status is not None and supplied_status != PHASE9R_STATUS:
        errors.append("supplied Phase 9R status does not match public gate reference")
    return sorted(set(errors))


def validate_report(report: Any) -> list[str]:
    """Validate the Phase 9S public report against the frozen schema/constants.

    This checks the report's gate references against the frozen public gate
    constants (PHASE9R_COMMIT / PHASE9R_CI_RUN / PHASE9R_STATUS / the three
    nonzero buckets, etc.) directly.  It does NOT read the Phase 9R public
    report on disk; the on-disk cross-check against the Phase 9R public
    artifact report is performed separately by the ``--validate-report`` CLI
    path via ``_phase9r_gate_errors`` (which reads ONLY the Phase 9R public
    artifact report under ``artifacts/``, never ignored ``runs/`` or private
    adjudication rows).
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

    # Phase 9R gate references (PRIMARY whitelisted public gate refs).
    gate9r = report.get("phase9r_gate_references", {})
    if gate9r.get("phase9r_commit") != PHASE9R_COMMIT:
        errors.append("Phase 9R commit gate reference drift")
    if gate9r.get("phase9r_ci_run") != PHASE9R_CI_RUN:
        errors.append("Phase 9R CI run gate reference drift")
    if gate9r.get("phase9r_ci_success") is not True:
        errors.append("Phase 9R CI success gate missing")
    if gate9r.get("phase9r_status") != PHASE9R_STATUS:
        errors.append("Phase 9R status gate reference drift")
    if gate9r.get("phase9r_adjudicated_bucket") != PHASE9R_ADJUDICATED_BUCKET:
        errors.append("Phase 9R adjudicated_bucket public fact drift")
    if gate9r.get("phase9r_correctness_bucket") != PHASE9R_CORRECTNESS_BUCKET:
        errors.append("Phase 9R correctness_bucket public fact drift")
    if gate9r.get("phase9r_evidence_success_bucket") != PHASE9R_EVIDENCE_SUCCESS_BUCKET:
        errors.append("Phase 9R evidence_success_bucket public fact drift")
    for key in ("phase9r_protocol_applied_exactly_once",
                "phase9r_bucketed_nonzero_aggregate_protocol_application_buckets",
                "phase9r_gate_required_before_phase9s"):
        if gate9r.get(key) is not True:
            errors.append(f"Phase 9R gate boundary missing: {key}")

    # Phase 9Q inherited provenance (status/boolean only; no exact commit/CI).
    prov9q = report.get("phase9q_inherited_provenance", {})
    if prov9q.get("phase9q_ci_success") is not True:
        errors.append("Phase 9Q inherited CI success missing")
    if prov9q.get("phase9q_status") != PHASE9Q_STATUS:
        errors.append("Phase 9Q inherited status drift")
    if prov9q.get("phase9q_protocol_freeze") is not True:
        errors.append("Phase 9Q inherited protocol freeze missing")
    if prov9q.get("phase9q_did_not_execute_adjudication_or_correctness") is not True:
        errors.append("Phase 9Q inherited no-execution boundary missing")
    if prov9q.get("phase9q_carried_as_inherited_provenance_only") is not True:
        errors.append("Phase 9Q inherited provenance-only boundary missing")

    # Phase 9P inherited provenance (status/buckets only; no exact commit/CI).
    prov9p = report.get("phase9p_inherited_provenance", {})
    if prov9p.get("phase9p_ci_success") is not True:
        errors.append("Phase 9P inherited CI success missing")
    if prov9p.get("phase9p_status") != PHASE9P_STATUS:
        errors.append("Phase 9P inherited status drift")
    if prov9p.get("phase9p_denominator_bucket") != PHASE9P_DENOMINATOR_BUCKET:
        errors.append("Phase 9P inherited denominator_bucket drift")
    if prov9p.get("phase9p_scored_bucket") != PHASE9P_SCORED_BUCKET:
        errors.append("Phase 9P inherited scored_bucket drift")
    if prov9p.get("phase9p_adjudicated_bucket") != PHASE9P_ADJUDICATED_BUCKET:
        errors.append("Phase 9P inherited adjudicated_bucket drift")
    if prov9p.get("phase9p_correctness_bucket") != PHASE9P_CORRECTNESS_BUCKET:
        errors.append("Phase 9P inherited correctness_bucket drift")
    for key in ("phase9p_adjudication_not_executed", "phase9p_correctness_not_computed",
                "phase9p_evidence_success_not_computed",
                "phase9p_carried_as_inherited_provenance_only"):
        if prov9p.get(key) is not True:
            errors.append(f"Phase 9P inherited boundary missing: {key}")

    # Phase 9O-9F inherited provenance (bucketed only).
    prov = report.get("inherited_provenance_bucketed", {})
    for pk, es in (("phase9o_status", PHASE9O_STATUS), ("phase9n_status", PHASE9N_STATUS),
                    ("phase9m_status", PHASE9M_STATUS), ("phase9l_status", PHASE9L_STATUS),
                    ("phase9k_status", PHASE9K_STATUS), ("phase9h_status", PHASE9H_STATUS),
                    ("phase9i_status", PHASE9I_STATUS), ("phase9j_status", PHASE9J_STATUS),
                    ("phase9g_status", PHASE9G_STATUS), ("phase9f_status", PHASE9F_STATUS)):
        if prov.get(pk) != es:
            errors.append(f"inherited provenance {pk} drift")
    for key in ("phase9o_carried_as_inherited_provenance_only",
                "phase9n_carried_as_inherited_provenance_only",
                "phase9m_carried_as_inherited_provenance_only",
                "phase9l_carried_as_inherited_provenance_only",
                "phase9k_carried_as_inherited_provenance_only",
                "phase9h_carried_as_inherited_provenance_only",
                "phase9i_carried_as_inherited_provenance_only",
                "phase9j_carried_as_inherited_provenance_only",
                "phase9g_carried_as_inherited_provenance_only",
                "phase9f_carried_as_inherited_provenance_only",
                "phase9j_annotation_input_rows_are_routing_precondition_only_not_benchmark_truth",
                "exact_remote_commit_ci_values_intentionally_not_published"):
        if prov.get(key) is not True:
            errors.append(f"inherited provenance boundary missing: {key}")

    # phase9s_scope: all execution booleans must be False.
    scope = report.get("phase9s_scope", {})
    for key in ("docs_report_validator_only", "closeout_interpretation_guard_only"):
        if scope.get(key) is not True:
            errors.append(f"phase9s_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase9s_scope execution boundary failed: {key}")

    # Frozen closed lists (set-equality checked).
    proto = report.get("frozen_phase9r_interpretation", {})
    for key in ("phase9r_applied_phase9q_frozen_protocol_exactly_once",
                "phase9r_produced_bucketed_nonzero_aggregate_protocol_application_buckets_only",
                "phase9r_interpretation_is_protocol_application_results_only_not_generalized_success"):
        if proto.get(key) is not True:
            errors.append(f"frozen phase9r interpretation boundary missing: {key}")

    movement = report.get("frozen_no_post_outcome_protocol_movement", {})
    for key in ("no_new_metrics_thresholds_subgroups_based_on_phase9r_results",
                "no_denominator_inclusion_exclusion_correctness_evidence_success_edits",
                "no_repair_based_on_phase9r_results"):
        if movement.get(key) is not True:
            errors.append(f"frozen no-protocol-movement boundary missing: {key}")

    privacy_pub = report.get("frozen_privacy_publication", {})
    for key in ("public_aggregate_or_bucketed_only",
                "no_exact_counts_rates_ids_observables_snippets_paths_run_locations",
                "no_phase9r_private_adjudication_rows_read_in_phase9s",
                "no_ignored_runs_read_in_phase9s", "no_singleton_buckets"):
        if privacy_pub.get(key) is not True:
            errors.append(f"frozen privacy publication boundary missing: {key}")

    future = report.get("frozen_future_validation_needs", {})
    for key in ("future_strengthening_requires_separate_independent_validation_line",
                "future_protocol_must_be_pre_frozen_before_any_execution",
                "future_execution_only_after_commit_and_ci_green_confirmation",
                "phase9s_does_not_freeze_or_run_any_future_protocol"):
        if future.get(key) is not True:
            errors.append(f"frozen future validation needs boundary missing: {key}")

    guardrails = report.get("frozen_no_execution_guardrails", {})
    for key in ("no_execution_no_scoring_no_adjudication_in_phase9s",
                "no_correctness_or_evidence_success_recomputation_in_phase9s",
                "no_private_reads_in_phase9s",
                "no_protocol_edits_after_phase9r_outcome_visibility"):
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
    for key in ("phase9s_specific_validator_available", "self_test_available",
                "report_validation_available", "validator_does_not_fetch_or_read_private",
                "validator_does_not_read_phase9r_adjudication_rows",
                "validator_does_not_read_phase9p_scoring_rows",
                "validator_does_not_read_phase9n_packets",
                "validator_does_not_read_phase9h_materialized_sources",
                "validator_does_not_read_phase9j_annotation_input_rows",
                "validator_does_not_read_phase9l_outcome_packets",
                "public_artifact_privacy_audit_expected"):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_executes_tasks", "validator_reads_private_registry",
                "validator_reads_sources", "validator_reads_ignored_runs"):
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
    global PRIVATE_PHASE9R_ADJUDICATION_ROWS_READ_ATTEMPTS
    global PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS
    global PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS
    global PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS
    global PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS
    global PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9R_ADJUDICATION_ROWS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS = 0
    PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))
    checks.append(("base_status_equals_required_status", base["status"] == STATUS))
    checks.append(("base_phase_equals_slug", base["phase"] == PHASE))

    # Reject missing/wrong Phase 9R gate references (commit / ci / status /
    # bucket facts).
    for field, bad_val, label in (
        ("phase9r_commit", "deadbeef" * 5, "commit"),
        ("phase9r_ci_run", "0000", "ci_run"),
        ("phase9r_status", "drift", "status"),
        ("phase9r_adjudicated_bucket", "bucket_wrong", "adjudicated_bucket"),
        ("phase9r_correctness_bucket", "bucket_wrong", "correctness_bucket"),
        ("phase9r_evidence_success_bucket", "bucket_wrong", "evidence_success_bucket"),
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9r_gate_references"][field] = bad_val
        checks.append((f"wrong_phase9r_{label}_rejected", bool(validate_report(mutated))))

        mutated = copy.deepcopy(base)
        del mutated["phase9r_gate_references"][field]
        checks.append((f"missing_phase9r_{label}_rejected", bool(validate_report(mutated))))

    # Reject phase9r gate facts flipped to false.
    for key in ("phase9r_protocol_applied_exactly_once",
                "phase9r_bucketed_nonzero_aggregate_protocol_application_buckets",
                "phase9r_gate_required_before_phase9s"):
        mutated = copy.deepcopy(base)
        mutated["phase9r_gate_references"][key] = False
        checks.append((f"phase9r_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject phase9r bucket flipped to bucket_zero (would contradict "nonzero").
    for key in ("phase9r_adjudicated_bucket", "phase9r_correctness_bucket",
                "phase9r_evidence_success_bucket"):
        mutated = copy.deepcopy(base)
        mutated["phase9r_gate_references"][key] = "bucket_zero"
        checks.append((f"phase9r_{key}_zero_bucket_rejected", bool(validate_report(mutated))))

    # Reject re-introduction of an exact Phase 9O-9F commit/CI field (the
    # exact remote commit/CI run values are intentionally NOT published;
    # bucketed inherited provenance only).
    for prov_section, commit_key in (
        ("inherited_provenance_bucketed", "phase9o_commit"),
        ("inherited_provenance_bucketed", "phase9n_commit"),
        ("inherited_provenance_bucketed", "phase9m_commit"),
        ("inherited_provenance_bucketed", "phase9l_commit"),
        ("inherited_provenance_bucketed", "phase9k_commit"),
        ("inherited_provenance_bucketed", "phase9h_commit"),
        ("inherited_provenance_bucketed", "phase9i_commit"),
        ("inherited_provenance_bucketed", "phase9j_commit"),
    ):
        mutated = copy.deepcopy(base)
        mutated[prov_section][commit_key] = "d997caab5487e66c544f657645d70c97f3b780e2"
        checks.append((f"{prov_section}_{commit_key}_field_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema drift.
    for field, bad in (("status", "drift"), ("phase", "drift"), ("schema_version", "drift")):
        mutated = copy.deepcopy(base)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # --- negative mutation: execution booleans true fails. ---
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["phase9s_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: private reads true fails (incl. phase9r rows). ---
    for private_read_key in (
        "private_phase9r_adjudication_rows_read",
        "private_phase9p_scoring_rows_read",
        "private_phase9n_packets_read",
        "private_phase9h_materialized_sources_read",
        "private_phase9j_annotation_input_rows_read",
        "private_phase9l_outcome_packets_read",
        "ignored_runs_read",
        "private_candidate_pool_read",
        "private_registry_read",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9s_scope"][private_read_key] = True
        mutated["no_execution_booleans"][private_read_key] = True
        checks.append((f"{private_read_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: 9R-as-truth fails. ---
    mutated = copy.deepcopy(base)
    mutated["phase9s_scope"]["phase9r_rows_used_as_truth"] = True
    mutated["no_execution_booleans"]["phase9r_rows_used_as_truth"] = True
    checks.append(("phase9r_as_truth_rejected", bool(validate_report(mutated))))

    # --- negative mutation: protocol movement / repair fails. ---
    for key in ("new_metrics_introduced", "new_thresholds_introduced", "new_subgroups_introduced",
                "denominator_changed", "inclusion_exclusion_edited",
                "correctness_or_evidence_success_recomputed", "repair_based_on_phase9r_results",
                "protocol_edited_after_outcome_visibility"):
        mutated = copy.deepcopy(base)
        mutated["phase9s_scope"][key] = True
        mutated["no_execution_booleans"][key] = True
        checks.append((f"protocol_movement_{key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: exact count fields fail. ---
    mutated = copy.deepcopy(base)
    mutated["phase9s_scope"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_phase9r_interpretation"]["adjudicated_count"] = 72
    checks.append(("adjudicated_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_phase9r_interpretation"]["correctness_count"] = 10
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
        mutated["phase9s_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: private-shaped keys fail. ---
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "per_task_summary", "per_packet_summary", "source_path_bucket", "path",
        "repo_name", "task_id", "row_id", "packet_id", "observable_id", "manifest",
        "run_dir",
    ):
        mutated = copy.deepcopy(base)
        mutated["phase9s_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: threshold/novel-metric/subgroup keys fail. ---
    for bad_key in ("correctness_threshold", "adjudication_threshold", "decision_threshold",
                    "novel_metric_bucket", "subgroup_breakdown"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9r_interpretation"][bad_key] = "example"
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
    mutated["frozen_phase9r_interpretation"]["phase9r_interpretation_rules"][0] = "phase9r_method_success_proven"
    checks.append(("phase9r_interpretation_vocabulary_drift_rejected", bool(validate_report(mutated))))

    # --- negative mutation: future-protocol freeze/run wording in 9S fails. ---
    mutated = copy.deepcopy(base)
    mutated["frozen_future_validation_needs"]["future_validation_needs_rules"].append("phase9s_freezes_future_protocol_now")
    checks.append(("future_protocol_frozen_in_9s_rejected", bool(validate_report(mutated))))

    # --- negative mutation: claim boundary set to true fails. ---
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- negative mutation: privacy contract violations fail. ---
    for privacy_key in (
        "per_source_public_facts", "per_task_public_facts", "per_packet_public_facts",
        "run_locations_public", "repo_names_public", "outcome_observables_public",
        "outcome_packets_public", "phase9r_private_adjudication_rows_public",
        "phase9p_scoring_rows_public", "phase9n_packets_public", "phase9l_packets_public",
        "packet_ids_public", "exact_counts_or_rates_public", "singleton_buckets_public",
    ):
        mutated = copy.deepcopy(base)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # --- negative mutation: singleton buckets fail. ---
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9r_interpretation"]["phase9r_interpretation_rules"].append(singleton_val)
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # --- negative mutation: claim-making wording fails. ---
    for phrase in ("method effectiveness", "product readiness", "scoring success", "outcome success",
                   "evaluation works", "acquisition success", "adjudication proven",
                   "correctness proven", "evidence_success achieved", "lift achieved",
                   "generalized success", "evidence-acquisition success"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9r_interpretation"]["example_note"] = phrase
        checks.append((f"claim_phrase_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # --- negative mutation: user-approval wording fails. ---
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    # --- negative mutation: placeholder/TBD/TODO wording fails. ---
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(base)
        mutated["frozen_phase9r_interpretation"]["phase9r_interpretation_rules"].append(phrase)
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
    mutated["phase9s_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["frozen_phase9r_interpretation"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_interpretation_rejected", bool(validate_report(mutated))))

    # --- non-gate-reference hash/CI values are rejected. ---
    mutated = copy.deepcopy(base)
    mutated["phase9s_scope"]["task_ci_run"] = "28989276491"
    errors = validate_report(mutated)
    checks.append(("non_whitelisted_ci_run_key_value_rejected", bool(errors)))
    checks.append(("non_whitelisted_ci_run_key_not_exempt", any("private-shaped public key" in e for e in errors)))

    mutated = copy.deepcopy(base)
    mutated["phase9s_scope"]["example_hash"] = "304aff6fd52b80680f91bd077a2760e4a95edc5f"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))

    # Gate-reference commit values are exempt from private-shaped value scan
    # but a non-gate-reference key with a hash value is still rejected (above).
    checks.append(("gate_ref_commit_values_on_whitelisted_paths_valid",
                   not validate_report(base)))

    # --- Phase 9R public-report cross-check: a synthetic drifted 9R report
    #     is rejected (proves the gate constants are enforced against the 9R
    #     public report without reading any private adjudication rows). ---
    synthetic_9r_good = {
        "phase": "phase9r_frozen_adjudication_correctness_evidence_success_execution_no_claim",
        "status": PHASE9R_STATUS,
        "adjudication_buckets": {
            "adjudicated_bucket": PHASE9R_ADJUDICATED_BUCKET,
            "correctness_bucket": PHASE9R_CORRECTNESS_BUCKET,
            "evidence_success_bucket": PHASE9R_EVIDENCE_SUCCESS_BUCKET,
            "adjudication_executed_once": True,
            "correctness_evaluated_once": True,
            "evidence_success_is_aggregate_correctness_bucket_only": True,
        },
        "execution_booleans": {
            "adjudication_executed": True,
            "correctness_evaluated": True,
            "evidence_success_evaluated": True,
            "adjudication_repaired_after_private_reads": False,
        },
    }
    checks.append(("synthetic_9r_good_cross_check_passes",
                   not _phase9r_gate_errors(report=synthetic_9r_good)))

    for field, bad in (("status", "drift"),
                       ("adjudicated_bucket", "bucket_zero"),
                       ("correctness_bucket", "bucket_zero"),
                       ("evidence_success_bucket", "bucket_zero")):
        drifted = copy.deepcopy(synthetic_9r_good)
        if field in drifted["adjudication_buckets"]:
            drifted["adjudication_buckets"][field] = bad
        else:
            drifted[field] = bad
        checks.append((f"synthetic_9r_{field}_drift_rejected", bool(_phase9r_gate_errors(report=drifted))))

    drifted = copy.deepcopy(synthetic_9r_good)
    drifted["execution_booleans"]["adjudication_executed"] = False
    checks.append(("synthetic_9r_adjudication_not_executed_rejected", bool(_phase9r_gate_errors(report=drifted))))

    drifted = copy.deepcopy(synthetic_9r_good)
    drifted["execution_booleans"]["adjudication_repaired_after_private_reads"] = True
    checks.append(("synthetic_9r_repaired_after_private_reads_rejected", bool(_phase9r_gate_errors(report=drifted))))

    # Supplied confirmation mismatch is rejected.
    checks.append(("supplied_9r_commit_mismatch_rejected",
                   bool(_phase9r_gate_errors(report=synthetic_9r_good, supplied_commit="wrong"))))
    checks.append(("supplied_9r_ci_mismatch_rejected",
                   bool(_phase9r_gate_errors(report=synthetic_9r_good, supplied_ci="wrong"))))
    checks.append(("supplied_9r_status_mismatch_rejected",
                   bool(_phase9r_gate_errors(report=synthetic_9r_good, supplied_status="wrong"))))

    # --- --validate-report fails closed on ignored/private paths. ---
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9s" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase9r_private" / "inv.json")
    checks.append(("validate_report_rejects_runs_private_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase9r_frozen_adjudication_correctness_evidence_success_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects an ignored runs/ path before reading (no real file needed).
    runs_cli_path = str(REPO / "runs" / "phase9s" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # --- validate a temp-file round-trip (synthetic fixture only, no private reads). ---
    with tempfile.TemporaryDirectory(prefix="phase9s_selftest_") as tmp:
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

    # --- prove the validator/self-test did not fetch/read private. ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_sources", SOURCE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9r_adjudication_rows",
                   PRIVATE_PHASE9R_ADJUDICATION_ROWS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9p_scoring_rows",
                   PRIVATE_PHASE9P_SCORING_ROWS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9n_packets",
                   PRIVATE_PHASE9N_OUTCOME_PACKETS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9l_outcome_packets",
                   PRIVATE_PHASE9L_OUTCOME_PACKETS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9h_materialized_sources",
                   PRIVATE_PHASE9H_SOURCES_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9j_annotation_input_rows",
                   PRIVATE_PHASE9J_ANNOTATION_INPUT_READ_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9S Phase 9R docs-only closeout / interpretation guard (no claim)"
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
        # Fail closed: --validate-report may only read the Phase 9S public
        # artifact report, never ignored/private paths such as runs/ or paths
        # outside the public artifacts/ root.
        ok, reason = _validate_report_path_is_public(args.validate_report)
        if not ok:
            print(f"ERROR: {reason}: {args.validate_report}", file=sys.stderr)
            return 1
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        # Cross-check the frozen gate constants against the Phase 9R public
        # artifact report (a public artifact, NOT a private read).  This
        # confirms the Phase 9R commit/CI/status and the three nonzero public
        # buckets match without reading ignored runs/ or private adjudication
        # rows.
        errors.extend(_phase9r_gate_errors())
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.write_report:
        report = build_public_report()
        errors = validate_report(report)
        # Cross-check the frozen gate constants against the Phase 9R public
        # artifact report when writing (public artifact read, not private).
        errors.extend(_phase9r_gate_errors())
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
