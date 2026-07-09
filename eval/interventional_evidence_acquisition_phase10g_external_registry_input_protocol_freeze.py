#!/usr/bin/env python3
"""Phase 10G external registry-input protocol freeze + Phase 10F closeout (no execution, no claim).

Phase 10G is a DOCS-ONLY CLOSEOUT + EXTERNAL-INPUT PROTOCOL-FREEZE checkpoint.
It is docs/report/validator only; it performs NO execution.  Phase 10G:

  * closes Phase 10F cleanly as repair/no-claim under the frozen Phase 10E
    candidate-source-registry construction/provision protocol (Phase 10F
    commit ``969f8acde65a27ab3b512db269150d814483d49c``, CI run ``29022117575``
    green, status ``phase10f_candidate_source_registry_construction_repair_no_claim``);
  * adds/clarifies guard language: no compliant registry source exists and no
    fallback path is authorized;
  * defines -- as metadata/specification only -- what a future compliant
    operator-provided external registry-input package MUST contain (the
    future external-input package contract); and
  * states that execution remains blocked until a compliant external package
    matching this contract exists.

Phase 10G is FORBIDDEN from: direct fetch, clone, scrape, download, browsing,
source read, public registry inspection; candidate discovery, source
materialization, task generation, scoring, adjudication, correctness/
evidence_success evaluation, or outcomes; constructing a registry from public
information; inferring candidates from memory, docs, URLs, package indexes,
GitHub, search, or prior non-compliant sources; treating the absent external
package as permission to create one; reading ignored ``runs/`` private data;
constructing or validating a registry manifest in 10G; and constructing or
intake-validating an external-input package in 10G.

Phase 10G makes NO validation/product/method/correctness/evidence-success
claim; it records ONLY Phase 10F closeout status and a future external-input
package contract (metadata/specification only).  It does NOT score/adjudicate/
evaluate correctness/evidence_success, does NOT fetch/clone/read/scrape/inspect/
sample/download source material, does NOT materialize source contents, does NOT
generate tasks/packets or execute any downstream pipeline, does NOT modify/
reinterpret/extend the frozen 10E protocol, does NOT add thresholds/fallbacks/
exceptions/fallback channels, does NOT treat the absent external package as
partial success or as permission to create one, does NOT use Phase 9 artifacts
as validation evidence, does NOT change runtime/default behavior, and does NOT
make user-approval wording a protocol dependency.

Anti-adaptation rule: Phase 10G is prospective.  It is NOT tuned to repair the
observed Phase 10C ``bucket_zero`` / ``bucket_no_eligible_channel_registry``
outcome or the Phase 10F ``bucket_zero`` /
``bucket_no_compliant_registry_input_under_frozen_10e_protocol`` outcome.  The
frozen Phase 10E protocol is applied EXACTLY (the frozen closed lists are
imported directly from the committed Phase 10E protocol-freeze module; no
re-declaration, no drift, no post-hoc edit after seeing registry/package
availability).  Phase 10C and Phase 10F are referenced ONLY as gate/provenance
facts and failure modes, NOT as optimization feedback.  No rule is justified by
"because 10F found no compliant registry" unless framed as a general
compliance/audit requirement.  No new threshold/fallback/channel exception is
introduced to avoid the observed repair reason.  Future execution must use the
frozen 10E protocol and the 10G external-input contract as written, with no
post-hoc selection after seeing source/package availability, and no fallback
path is authorized.

This module performs no network/filesystem fetch, no source read, no private
ignored-``runs/`` read, no Phase 9/10A/10B/10C/10D/10E/10F private artifact
read, no scoring/adjudication/correctness/evidence_success computation, no
registry-manifest construction or validation, and no external-input package
intake validation.  The dry self-test and report validation use synthetic
tempfile fixtures only; the future-package-contract schema check is exercised
on synthetic dicts only and does NOT read, fetch, or intake-validate any real
package.
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

# Import the frozen Phase 10E candidate-source-registry construction/provision
# protocol constants directly from the committed Phase 10E protocol-freeze
# module so Phase 10G references EXACTLY the frozen protocol (no re-declaration,
# no vocabulary/ordering/eligibility drift).  The import itself performs no
# execution, no fetch, no private read; it only loads frozen constants.  The
# Phase 10F status constant is imported from the committed Phase 10F execution
# module so 10G carries the exact 10F status with no drift.
try:  # namespace-package form (repo root on sys.path)
    from eval.interventional_evidence_acquisition_phase10e_candidate_source_registry_protocol_freeze import (  # noqa: E402
        CLOSED_PROTOCOL_LISTS as PHASE10E_CLOSED_PROTOCOL_LISTS,
        ANTI_ADAPTATION_RULES as PHASE10E_ANTI_ADAPTATION_RULES,
        STATUS as PHASE10E_STATUS_CONST,
    )
    from eval.interventional_evidence_acquisition_phase10f_registry_construction_execution import (  # noqa: E402
        STATUS as PHASE10F_STATUS_CONST,
    )
except Exception:  # pragma: no cover - direct-module form (eval/ on sys.path)
    from interventional_evidence_acquisition_phase10e_candidate_source_registry_protocol_freeze import (  # type: ignore[no-redef]  # noqa: E402
        CLOSED_PROTOCOL_LISTS as PHASE10E_CLOSED_PROTOCOL_LISTS,
        ANTI_ADAPTATION_RULES as PHASE10E_ANTI_ADAPTATION_RULES,
        STATUS as PHASE10E_STATUS_CONST,
    )
    from interventional_evidence_acquisition_phase10f_registry_construction_execution import (  # type: ignore[no-redef]  # noqa: E402
        STATUS as PHASE10F_STATUS_CONST,
    )


PHASE = "phase10g_external_registry_input_protocol_freeze_no_execution_no_claim"
SCHEMA_VERSION = "phase10g_external_registry_input_protocol_freeze_no_execution_no_claim_report_v1"
STATUS = (
    "phase10g_external_registry_input_protocol_freeze_no_execution_no_claim"
)
PUBLICATION_LEVEL = (
    "aggregate_external_registry_input_protocol_freeze_and_phase10f_closeout_boundary_only"
)

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# ---------------------------------------------------------------------------
# Frozen gate references.  Phase 10G publishes exact commit/CI identifiers only
# for the immediate Phase 10F gate that it closes.  Older Phase 9 / 10A / 10B /
# 10C / 10D / 10E / hygiene checkpoints are carried forward only as
# status/bucket/scope provenance, not as exact commit/CI identifiers.  Local
# same-tree git commits are not read or compared.
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
PHASE10D_STATUS = "phase10d_10c_repair_closeout_guard_no_claim"
PHASE10E_STATUS = PHASE10E_STATUS_CONST  # frozen, imported (no drift)

# Phase 10F gate (the immediate gate closed by Phase 10G).  These are the only
# exact public gate references published by Phase 10G.
PHASE10F_COMMIT = "969f8acde65a27ab3b512db269150d814483d49c"
PHASE10F_CI_RUN = "29022117575"
PHASE10F_CI_SUCCESS = True
PHASE10F_STATUS = PHASE10F_STATUS_CONST  # frozen, imported (no drift)
PHASE10F_REPAIR_NO_CLAIM = True
PHASE10F_NO_COMPLIANT_REGISTRY_MANIFEST_CONSTRUCTED_OR_PROVIDED = True
PHASE10F_NO_COMPLIANT_REGISTRY_INPUT_OR_SOURCE_EXISTS = True
PHASE10F_NO_FALLBACK_AUTHORIZED = True

# Phase 10G is authorized by oracle as docs-only closeout + external-input
# protocol freeze ONLY, gated on Phase 10F commit + CI green.
PHASE10G_ORACLE_AUTHORIZATION = (
    "phase10g_authorized_by_oracle_docs_only_closeout_and_external_registry_input_protocol_freeze_only"
)

# Repair/no-claim closeout buckets for this checkpoint.
CLOSEOUT_BUCKET = "bucket_phase10f_closed_repair_no_claim_under_frozen_10e_protocol"
NO_COMPLIANT_REGISTRY_SOURCE_BUCKET = "bucket_no_compliant_registry_source_exists"
NO_FALLBACK_BUCKET = "bucket_no_fallback_path_authorized"
EXECUTION_BLOCKED_BUCKET = (
    "bucket_execution_blocked_until_compliant_external_package_matching_10g_contract_exists"
)

# ---------------------------------------------------------------------------
# Frozen Phase 10G external registry-input protocol freeze.
# These are STRUCTURAL protocol-freeze definitions only; no execution, no
# package construction, no package intake validation, no registry construction,
# no source reads, no fetch/clone, no scoring/adjudication/correctness/
# evidence_success evaluation, or materialization occurs in Phase 10G.
# ---------------------------------------------------------------------------

# 1. Future operator-provided external registry-input package contract
#    (metadata/specification only).  A future compliant operator-provided
#    external registry-input package MUST contain EXACTLY these fields (closed
#    list; the validator enforces set-equality and rejects missing/extra future
#    fields).  No package matching this contract exists in Phase 10G; the
#    contract is defined only.
FUTURE_EXTERNAL_INPUT_PACKAGE_CONTRACT_FIELDS = (
    "operator_assertion_package_externally_provided",
    "registry_manifest_file",
    "provenance_statement",
    "license_usage_permissions",
    "immutable_checksums",
    "operator_declared_acquisition_method",
    "explicit_no_project_side_fetch_clone_scrape_source_discovery",
    "offline_local_availability_for_later_bounded_validation",
)

# 2. Future package intake validation checks (defined only, NOT executed).
#    These are the prospective checks a LATER Phase 10H MAY run if and only if
#    an operator provides a complete offline registry-input package matching the
#    10G contract.  Phase 10G defines them only; it does NOT run them, does NOT
#    read a package, and does NOT claim a package exists or was checked.
FUTURE_PACKAGE_INTAKE_VALIDATION_CHECKS = (
    "package_presence_check_only",
    "declared_provenance_check_only",
    "schema_check_only",
    "checksums_check_only",
    "permissions_check_only",
)

# 3. Anti-adaptation rules (the protocol is prospective, not tuned to 10C/10F).
ANTI_ADAPTATION_RULES = (
    "protocol_is_prospective_not_tuned_to_observed_outcome",
    "observed_zero_outcome_referenced_only_as_gate_and_failure_mode",
    "no_rule_justified_by_observed_zero_unless_general_compliance_audit",
    "no_threshold_fallback_or_channel_exception_for_observed_repair_reason",
    "future_execution_uses_frozen_protocol_no_post_hoc_selection",
    "absent_external_package_not_treated_as_permission_to_create_one",
    "no_fallback_path_authorized_for_absent_external_package",
    "execution_remains_blocked_until_compliant_external_package_matches_contract",
)

# Closed protocol lists whose members are validator set-equality checked.
# Each entry is (report_section, list_key, expected_tuple, label).
CLOSED_PROTOCOL_LISTS = (
    (
        "phase10g_protocol_freeze",
        "future_external_input_package_contract_fields",
        FUTURE_EXTERNAL_INPUT_PACKAGE_CONTRACT_FIELDS,
        "future_external_input_package_contract_fields",
    ),
    (
        "phase10g_protocol_freeze",
        "future_package_intake_validation_checks",
        FUTURE_PACKAGE_INTAKE_VALIDATION_CHECKS,
        "future_package_intake_validation_checks",
    ),
    (
        "anti_adaptation_rules",
        "anti_adaptation_rules_list",
        ANTI_ADAPTATION_RULES,
        "anti_adaptation_rules",
    ),
)

# Inherited frozen Phase 10E closed lists (mirrored for continuity; the
# validator set-equality checks them against the imported constants to prove
# no drift from 10E).  These are structural definitions only; Phase 10G does
# not fetch/clone/read/materialize/score to populate any registry.
INHERITED_PHASE10E_CLOSED_PROTOCOL_LISTS = PHASE10E_CLOSED_PROTOCOL_LISTS
INHERITED_PHASE10E_ANTI_ADAPTATION_RULES = PHASE10E_ANTI_ADAPTATION_RULES

CONSERVATIVE_RECOMMENDATION = (
    "phase10g_external_registry_input_protocol_freeze_and_phase10f_closeout_only"
    "_phase9_closed_inherited"
    "_phase10a_gate_inherited"
    "_phase10b_gate_inherited"
    "_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources"
    "_phase10d_closeout_guard_gate_inherited"
    "_phase10e_protocol_freeze_gate_inherited"
    "_phase10f_registry_construction_execution_gate_inherited_ci_green_closed_as_repair_no_claim_under_frozen_10e_protocol"
    "_phase10g_authorized_by_oracle_docs_only_closeout_and_external_registry_input_protocol_freeze_only"
    "_phase10g_applies_frozen_phase10e_protocol_exactly_no_drift"
    "_phase10g_is_docs_only_closeout_and_external_input_protocol_freeze_only_not_execution"
    "_phase10g_is_not_validation_product_method_correctness_evidence_success"
    "_phase10g_does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material"
    "_phase10g_does_not_materialize_source_contents"
    "_phase10g_does_not_generate_tasks_or_packets_or_execute_downstream_pipeline"
    "_phase10g_does_not_score_adjudicate_or_run_correctness_evidence_success"
    "_phase10g_does_not_construct_or_validate_a_registry_manifest"
    "_phase10g_does_not_construct_or_intake_validate_an_external_input_package"
    "_phase10g_does_not_authorize_a_fallback_path"
    "_phase10g_does_not_treat_absent_external_package_as_permission_to_create_one"
    "_phase10g_does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f"
    "_phase10g_protocol_is_prospective_not_tuned_to_observed_outcome"
    "_phase10g_closes_phase10f_as_repair_no_claim_under_frozen_10e_protocol"
    "_no_compliant_registry_source_exists_under_frozen_10e_protocol"
    "_no_fallback_path_authorized"
    "_execution_remains_blocked_until_compliant_external_package_matching_10g_contract_exists"
    "_no_registry_manifest_constructed_or_validated_in_phase10g"
    "_no_external_input_package_constructed_or_intake_validated_in_phase10g"
    "_future_package_contract_is_metadata_specification_only_no_package_exists"
    "_future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract"
    "_phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes"
    "_boundary_review_after_phase10g_commit_and_ci_green"
    "_no_user_approval_wording_no_method_product_correctness_evidence_success_claim"
)

# ---------------------------------------------------------------------------
# Truth-boundary attestation keys that must always be True.
# ---------------------------------------------------------------------------
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_inherited",
    "phase10a_gate_inherited",
    "phase10b_gate_inherited",
    "phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources",
    "phase10d_closeout_guard_gate_inherited",
    "phase10e_protocol_freeze_gate_inherited",
    "phase10f_registry_construction_execution_gate_inherited",
    "phase10f_closed_repair_no_claim_under_frozen_10e_protocol",
    "phase10f_no_compliant_registry_manifest_constructed_or_provided",
    "phase10f_no_compliant_registry_input_or_source_exists",
    "phase10f_no_fallback_authorized",
    "phase10g_applies_frozen_phase10e_protocol_exactly_no_drift",
    "phase10g_is_docs_only_closeout_and_external_input_protocol_freeze_only",
    "phase10g_is_separate_from_phase9_not_continuation",
    "phase10g_makes_no_new_evidence_claims",
    "phase10g_protocol_is_prospective_not_tuned_to_observed_outcome",
    "phase10g_no_compliant_registry_source_exists",
    "phase10g_no_fallback_path_authorized",
    "phase10g_execution_remains_blocked_until_compliant_external_package_matches_contract",
    "phase10g_no_registry_manifest_constructed_or_validated",
    "phase10g_no_external_input_package_constructed_or_intake_validated",
)

# Boundary attestation keys that must always be False (forbidden operations).
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
    "source_material_fetched_or_cloned",
    "source_material_read",
    "source_material_scraped_or_sampled",
    "source_material_inspected",
    "source_material_downloaded",
    "materialization_executed",
    "task_generation_executed",
    "packet_generation_executed",
    "downstream_pipeline_executed",
    "thresholds_added",
    "fallbacks_added",
    "exceptions_added",
    "fallback_channels_added",
    "implicit_eligibility_expansion",
    "best_effort_registry_invention",
    "phase10e_protocol_modified_or_reinterpreted_or_extended",
    "phase10f_closed_repair_reinterpreted_or_extended",
    "candidate_registry_populated",
    "candidate_registry_materialized",
    "registry_manifest_constructed_or_validated",
    "external_input_package_constructed_or_intake_validated",
    "public_registry_inspection_executed",
    "candidate_inference_from_memory_docs_urls_indexes_search_or_prior_sources",
    "absent_external_package_treated_as_permission_to_create_one",
    "bucket_zero_treated_as_partial_success",
    "protocol_tuned_to_observed_outcome",
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
    "phase10f_confirms_claim",
    "phase10g_confirms_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "registry_construction_succeeded_claim",
    "registry_provision_succeeded_claim",
    "external_package_exists_claim",
    "external_package_validated_claim",
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
    "phase10e_private_artifacts_public",
    "phase10f_private_artifacts_public",
    "source_urls_public",
    "candidate_repo_names_public",
    "candidate_identities_public",
    "candidate_registry_contents_public",
    "registry_manifest_locations_public",
    "registry_construction_audit_log_public",
    "registry_exclusion_audit_log_public",
    "external_package_contents_public",
    "external_package_checksums_public",
    "external_package_provenance_public",
)

FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
    "gold",
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
    r"|phase\s*10f\s+confirms"
    r"|phase\s*10g\s+confirms"
    r"|registry\s+construction\s+(?:works|succeeded|proven|established)"
    r"|registry\s+provision\s+(?:works|succeeded|proven|established)"
    r"|external\s+package\s+(?:exists|validated|succeeded|proven|established)"
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
# published by Phase 10G (immediate Phase 10F gate only, plus the inherited
# Phase 10C bucket constants).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10c_accepted_source_bucket",
        "$.gate_facts.phase10c_repair_reason_bucket",
        "$.gate_facts.phase10f_commit",
        "$.gate_facts.phase10f_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read/
# execute/score/construct/materialize/intake-validate.  Phase 10G's
# docs-only/protocol-freeze path constructs and validates nothing; these
# stay zero.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_DISCOVERY_ATTEMPTS = 0
SOURCE_INSPECTION_ATTEMPTS = 0
MATERIALIZATION_ATTEMPTS = 0
PACKET_GENERATION_ATTEMPTS = 0
TASK_GENERATION_ATTEMPTS = 0
DOWNSTREAM_PIPELINE_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS = 0
SOURCE_MATERIAL_READ_ATTEMPTS = 0
SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS = 0
PUBLIC_REGISTRY_INSPECTION_ATTEMPTS = 0
CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS = 0
CANDIDATE_REGISTRY_POPULATION_ATTEMPTS = 0
REGISTRY_MANIFEST_CONSTRUCTION_OR_VALIDATION_ATTEMPTS = 0
EXTERNAL_INPUT_PACKAGE_CONSTRUCTION_OR_INTAKE_VALIDATION_ATTEMPTS = 0
PACKAGE_INTAKE_VALIDATION_ATTEMPTS = 0
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

    The report path must be under the Phase 10G public artifact directory
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
        return False, "report path is not under the Phase 10G public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Future external-input package contract schema enforcement (pure dict check).
# This checks ONLY whether a dict has exactly the closed contract field set.
# It does NOT read files, fetch, score, or intake-validate any real package.
# The self-test exercises it on synthetic dicts only.
# ---------------------------------------------------------------------------

def check_future_package_contract_schema(pkg: Any) -> list[str]:
    """Check a dict against the frozen future external-input package contract.

    Returns errors for any missing or extra fields.  This is a PURE schema
    check only; it does NOT read, fetch, score, or intake-validate a real
    package, and it does NOT assert that any package exists.  It is the
    metadata/specification enforcement for the future operator-provided
    external registry-input package contract.
    """
    errors: list[str] = []
    if not isinstance(pkg, dict):
        return ["future package contract check requires an object"]
    expected = set(FUTURE_EXTERNAL_INPUT_PACKAGE_CONTRACT_FIELDS)
    actual = {str(key) for key in pkg.keys()}
    for missing in sorted(expected - actual):
        errors.append(f"future package contract field missing: {missing}")
    for extra in sorted(actual - expected):
        errors.append(f"future package contract field extra: {extra}")
    return errors


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


def _inherited_phase10e_protocol_allowed() -> dict[str, Any]:
    """Build the allowed-schema dict for the inherited frozen 10E protocol."""
    section: dict[str, Any] = {}
    for _section_name, list_key, expected_tuple, _label in INHERITED_PHASE10E_CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = None
        for rule in expected_tuple:
            section[rule] = None
    return section


def _inherited_phase10e_anti_adaptation_allowed() -> dict[str, Any]:
    section: dict[str, Any] = {"anti_adaptation_rules_list": None}
    for rule in INHERITED_PHASE10E_ANTI_ADAPTATION_RULES:
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
        "phase10d_status": None,
        "phase10e_status": None,
        "phase10e_protocol_freeze_only_for_future_registry_construction": None,
        "phase10f_commit": None,
        "phase10f_ci_run": None,
        "phase10f_ci_success": None,
        "phase10f_status": None,
        "phase10f_repair_no_claim": None,
        "phase10f_no_compliant_registry_manifest_constructed_or_provided": None,
        "phase10f_no_compliant_registry_input_or_source_exists": None,
        "phase10f_no_fallback_authorized": None,
        PHASE10G_ORACLE_AUTHORIZATION: None,
        "only_phase10f_gate_constants_are_exact_references": None,
        "local_same_tree_git_commits_not_read_or_compared": None,
        "older_phase9_10a_10b_10c_10d_10e_hygiene_exact_refs_not_republished_by_phase10g": None,
    },
    "phase10g_scope": {
        "docs_only_closeout_and_external_input_protocol_freeze_only": None,
        "closes_phase10f_as_repair_no_claim_under_frozen_10e_protocol": None,
        "defines_future_external_input_package_contract_metadata_specification_only": None,
        "applies_frozen_phase10e_protocol_exactly_no_drift": None,
        "separate_from_phase9_not_continuation": None,
        "authorized_by_phase10f_gate_and_oracle": None,
        "no_compliant_registry_source_exists": None,
        "no_fallback_path_authorized": None,
        "execution_remains_blocked_until_compliant_external_package_matches_contract": None,
        "no_registry_manifest_constructed_or_validated_in_phase10g": None,
        "no_external_input_package_constructed_or_intake_validated_in_phase10g": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "phase10g_protocol_freeze": _protocol_freeze_allowed(),
    "inherited_frozen_phase10e_protocol": _inherited_phase10e_protocol_allowed(),
    "inherited_frozen_phase10e_anti_adaptation_rules": _inherited_phase10e_anti_adaptation_allowed(),
    "anti_adaptation_rules": {
        "anti_adaptation_rules_list": None,
        **{key: None for key in ANTI_ADAPTATION_RULES},
    },
    "phase10g_boundary": {
        "docs_only_closeout_plus_external_input_protocol_freeze": None,
        "closes_phase10f_repair_no_claim_under_frozen_10e_protocol": None,
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material": None,
        "does_not_materialize_source_contents": None,
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline": None,
        "does_not_score_adjudicate_or_run_correctness_evidence_success": None,
        "does_not_construct_or_validate_a_registry_manifest": None,
        "does_not_construct_or_intake_validate_an_external_input_package": None,
        "does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f": None,
        "does_not_authorize_a_fallback_path": None,
        "does_not_treat_absent_external_package_as_permission_to_create_one": None,
        "does_not_inspect_public_registries": None,
        "does_not_infer_candidates_from_memory_docs_urls_indexes_search_or_prior_sources": None,
        "no_compliant_registry_source_exists": None,
        "no_fallback_path_authorized": None,
        "execution_remains_blocked_until_compliant_external_package_matches_contract": None,
        "future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract": None,
        "phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes": None,
        "protocol_is_prospective_not_tuned_to_observed_outcome": None,
        "boundary_review_required_after_phase10g_commit_and_ci_green": None,
        "no_user_approval_wording_as_protocol_dependency": None,
    },
    "phase10f_closeout_summary": {
        "phase10f_closed_as_repair_no_claim": None,
        "phase10f_closeout_bucket": None,
        "phase10f_no_compliant_registry_manifest_constructed_or_provided": None,
        "phase10f_no_compliant_registry_input_or_source_exists": None,
        "phase10f_no_fallback_authorized": None,
        "phase10f_repair_no_claim_under_frozen_10e_protocol": None,
    },
    "external_input_protocol_freeze_summary": {
        "future_external_input_package_contract_is_metadata_specification_only": None,
        "future_package_contract_enforced_as_exact_closed_list": None,
        "future_package_intake_validation_checks_defined_only_not_executed": None,
        "no_external_input_package_exists_or_was_intake_validated": None,
        "no_registry_manifest_constructed_or_validated": None,
        "no_compliant_registry_source_exists": None,
        "no_fallback_path_authorized": None,
        "execution_blocked_bucket": None,
        "no_compliant_registry_source_bucket": None,
        "no_fallback_bucket": None,
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
        "phase10g_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "future_package_contract_schema_check_available": None,
        "validator_enforces_future_package_contract_as_exact_closed_list": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_read_phase10c_artifacts": None,
        "validator_does_not_read_phase10d_artifacts": None,
        "validator_does_not_read_phase10e_artifacts": None,
        "validator_does_not_read_phase10f_artifacts": None,
        "validator_does_not_inspect_sources": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_generate_packets": None,
        "validator_does_not_generate_tasks": None,
        "validator_does_not_execute_downstream_pipeline": None,
        "validator_does_not_scrape_or_sample_or_download_sources": None,
        "validator_does_not_inspect_public_registries": None,
        "validator_does_not_infer_candidates_from_prior_sources": None,
        "validator_does_not_populate_candidate_registry": None,
        "validator_does_not_construct_or_validate_registry_manifest": None,
        "validator_does_not_construct_or_intake_validate_external_package": None,
        "validator_does_not_score_adjudicate_or_evaluate": None,
        "validator_does_not_modify_or_extend_phase10e_or_phase10f": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_inspects_sources": None,
        "validator_inspects_public_registries": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_generates_packets": None,
        "validator_generates_tasks": None,
        "validator_executes_downstream_pipeline": None,
        "validator_scrapes_or_samples_or_downloads_sources": None,
        "validator_infers_candidates_from_prior_sources": None,
        "validator_populates_candidate_registry": None,
        "validator_constructs_or_validates_registry_manifest": None,
        "validator_constructs_or_intake_validates_external_package": None,
        "validator_scores_or_adjudicates": None,
        "validator_modifies_or_extends_phase10e_or_phase10f": None,
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

def _build_protocol_freeze_section() -> dict[str, Any]:
    """Build the phase10g_protocol_freeze section with frozen lists + booleans."""
    section: dict[str, Any] = {}
    for _section_name, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = list(expected_tuple)
        for rule in expected_tuple:
            section[rule] = True
    return section


def _build_inherited_phase10e_protocol_section() -> dict[str, Any]:
    """Build the inherited_frozen_phase10e_protocol section (frozen 10E lists)."""
    section: dict[str, Any] = {}
    for _section_name, list_key, expected_tuple, _label in INHERITED_PHASE10E_CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = list(expected_tuple)
        for rule in expected_tuple:
            section[rule] = True
    return section


def build_public_report() -> dict[str, Any]:
    """Build the Phase 10G external-input protocol-freeze + 10F closeout report.

    This performs no network/filesystem fetch, no source read, no private
    ignored-``runs/`` read, no Phase 9/10A/10B/10C/10D/10E/10F private artifact
    read, no scoring, no registry-manifest construction/validation, and no
    external-input package intake validation.  It assembles the report from
    the frozen gate constants and the imported frozen Phase 10E protocol
    definitions and the 10G external-input contract definitions only.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "publication_level": PUBLICATION_LEVEL,
        "gate_facts": {
            "phase9_status": PHASE9_STATUS,
            "phase10a_status": PHASE10A_STATUS,
            "phase10b_status": PHASE10B_STATUS,
            "phase10c_status": PHASE10C_STATUS,
            "phase10c_accepted_source_bucket": PHASE10C_ACCEPTED_SOURCE_BUCKET,
            "phase10c_repair_reason_bucket": PHASE10C_REPAIR_REASON_BUCKET,
            "phase10d_status": PHASE10D_STATUS,
            "phase10e_status": PHASE10E_STATUS,
            "phase10e_protocol_freeze_only_for_future_registry_construction": True,
            "phase10f_commit": PHASE10F_COMMIT,
            "phase10f_ci_run": PHASE10F_CI_RUN,
            "phase10f_ci_success": PHASE10F_CI_SUCCESS,
            "phase10f_status": PHASE10F_STATUS,
            "phase10f_repair_no_claim": PHASE10F_REPAIR_NO_CLAIM,
            "phase10f_no_compliant_registry_manifest_constructed_or_provided": (
                PHASE10F_NO_COMPLIANT_REGISTRY_MANIFEST_CONSTRUCTED_OR_PROVIDED
            ),
            "phase10f_no_compliant_registry_input_or_source_exists": (
                PHASE10F_NO_COMPLIANT_REGISTRY_INPUT_OR_SOURCE_EXISTS
            ),
            "phase10f_no_fallback_authorized": PHASE10F_NO_FALLBACK_AUTHORIZED,
            PHASE10G_ORACLE_AUTHORIZATION: True,
            "only_phase10f_gate_constants_are_exact_references": True,
            "local_same_tree_git_commits_not_read_or_compared": True,
            "older_phase9_10a_10b_10c_10d_10e_hygiene_exact_refs_not_republished_by_phase10g": True,
        },
        "phase10g_scope": {
            "docs_only_closeout_and_external_input_protocol_freeze_only": True,
            "closes_phase10f_as_repair_no_claim_under_frozen_10e_protocol": True,
            "defines_future_external_input_package_contract_metadata_specification_only": True,
            "applies_frozen_phase10e_protocol_exactly_no_drift": True,
            "separate_from_phase9_not_continuation": True,
            "authorized_by_phase10f_gate_and_oracle": True,
            "no_compliant_registry_source_exists": True,
            "no_fallback_path_authorized": True,
            "execution_remains_blocked_until_compliant_external_package_matches_contract": True,
            "no_registry_manifest_constructed_or_validated_in_phase10g": True,
            "no_external_input_package_constructed_or_intake_validated_in_phase10g": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "phase10g_protocol_freeze": _build_protocol_freeze_section(),
        "inherited_frozen_phase10e_protocol": _build_inherited_phase10e_protocol_section(),
        "inherited_frozen_phase10e_anti_adaptation_rules": {
            "anti_adaptation_rules_list": list(INHERITED_PHASE10E_ANTI_ADAPTATION_RULES),
            **{key: True for key in INHERITED_PHASE10E_ANTI_ADAPTATION_RULES},
        },
        "anti_adaptation_rules": {
            "anti_adaptation_rules_list": list(ANTI_ADAPTATION_RULES),
            **{key: True for key in ANTI_ADAPTATION_RULES},
        },
        "phase10g_boundary": {
            "docs_only_closeout_plus_external_input_protocol_freeze": True,
            "closes_phase10f_repair_no_claim_under_frozen_10e_protocol": True,
            "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material": True,
            "does_not_materialize_source_contents": True,
            "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline": True,
            "does_not_score_adjudicate_or_run_correctness_evidence_success": True,
            "does_not_construct_or_validate_a_registry_manifest": True,
            "does_not_construct_or_intake_validate_an_external_input_package": True,
            "does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f": True,
            "does_not_authorize_a_fallback_path": True,
            "does_not_treat_absent_external_package_as_permission_to_create_one": True,
            "does_not_inspect_public_registries": True,
            "does_not_infer_candidates_from_memory_docs_urls_indexes_search_or_prior_sources": True,
            "no_compliant_registry_source_exists": True,
            "no_fallback_path_authorized": True,
            "execution_remains_blocked_until_compliant_external_package_matches_contract": True,
            "future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract": True,
            "phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes": True,
            "protocol_is_prospective_not_tuned_to_observed_outcome": True,
            "boundary_review_required_after_phase10g_commit_and_ci_green": True,
            "no_user_approval_wording_as_protocol_dependency": True,
        },
        "phase10f_closeout_summary": {
            "phase10f_closed_as_repair_no_claim": True,
            "phase10f_closeout_bucket": CLOSEOUT_BUCKET,
            "phase10f_no_compliant_registry_manifest_constructed_or_provided": (
                PHASE10F_NO_COMPLIANT_REGISTRY_MANIFEST_CONSTRUCTED_OR_PROVIDED
            ),
            "phase10f_no_compliant_registry_input_or_source_exists": (
                PHASE10F_NO_COMPLIANT_REGISTRY_INPUT_OR_SOURCE_EXISTS
            ),
            "phase10f_no_fallback_authorized": PHASE10F_NO_FALLBACK_AUTHORIZED,
            "phase10f_repair_no_claim_under_frozen_10e_protocol": True,
        },
        "external_input_protocol_freeze_summary": {
            "future_external_input_package_contract_is_metadata_specification_only": True,
            "future_package_contract_enforced_as_exact_closed_list": True,
            "future_package_intake_validation_checks_defined_only_not_executed": True,
            "no_external_input_package_exists_or_was_intake_validated": True,
            "no_registry_manifest_constructed_or_validated": True,
            "no_compliant_registry_source_exists": True,
            "no_fallback_path_authorized": True,
            "execution_blocked_bucket": EXECUTION_BLOCKED_BUCKET,
            "no_compliant_registry_source_bucket": NO_COMPLIANT_REGISTRY_SOURCE_BUCKET,
            "no_fallback_bucket": NO_FALLBACK_BUCKET,
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
            "phase10g_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "future_package_contract_schema_check_available": True,
            "validator_enforces_future_package_contract_as_exact_closed_list": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_read_phase10c_artifacts": True,
            "validator_does_not_read_phase10d_artifacts": True,
            "validator_does_not_read_phase10e_artifacts": True,
            "validator_does_not_read_phase10f_artifacts": True,
            "validator_does_not_inspect_sources": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_generate_packets": True,
            "validator_does_not_generate_tasks": True,
            "validator_does_not_execute_downstream_pipeline": True,
            "validator_does_not_scrape_or_sample_or_download_sources": True,
            "validator_does_not_inspect_public_registries": True,
            "validator_does_not_infer_candidates_from_prior_sources": True,
            "validator_does_not_populate_candidate_registry": True,
            "validator_does_not_construct_or_validate_registry_manifest": True,
            "validator_does_not_construct_or_intake_validate_external_package": True,
            "validator_does_not_score_adjudicate_or_evaluate": True,
            "validator_does_not_modify_or_extend_phase10e_or_phase10f": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_inspects_sources": False,
            "validator_inspects_public_registries": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_generates_packets": False,
            "validator_generates_tasks": False,
            "validator_executes_downstream_pipeline": False,
            "validator_scrapes_or_samples_or_downloads_sources": False,
            "validator_infers_candidates_from_prior_sources": False,
            "validator_populates_candidate_registry": False,
            "validator_constructs_or_validates_registry_manifest": False,
            "validator_constructs_or_intake_validates_external_package": False,
            "validator_scores_or_adjudicates": False,
            "validator_modifies_or_extends_phase10e_or_phase10f": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }
    return report


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_report(report: Any) -> list[str]:
    """Validate the Phase 10G public report against the frozen schema/constants.

    This does NOT read any Phase 9/10A/10B/10C/10D/10E/10F artifact on disk,
    does NOT fetch/clone, does NOT read ignored ``runs/``, does NOT inspect
    public registries, does NOT score, does NOT construct or validate a
    registry manifest, and does NOT construct or intake-validate an external
    package.  It checks the report's gate references against the frozen public
    gate constants directly, and applies the closed 10G protocol lists and the
    inherited frozen 10E lists with set-equality against the imported constants.
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
    if report.get("publication_level") != PUBLICATION_LEVEL:
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
    if gate.get("phase10d_status") != PHASE10D_STATUS:
        errors.append("Phase 10D status gate fact drift")
    if gate.get("phase10e_status") != PHASE10E_STATUS:
        errors.append("Phase 10E status gate reference drift")
    if gate.get("phase10e_protocol_freeze_only_for_future_registry_construction") is not True:
        errors.append("Phase 10E protocol-freeze-only boundary missing")
    if gate.get("phase10f_commit") != PHASE10F_COMMIT:
        errors.append("Phase 10F commit gate reference drift")
    if gate.get("phase10f_ci_run") != PHASE10F_CI_RUN:
        errors.append("Phase 10F CI run gate reference drift")
    if gate.get("phase10f_ci_success") is not True:
        errors.append("Phase 10F CI success gate missing")
    if gate.get("phase10f_status") != PHASE10F_STATUS:
        errors.append("Phase 10F status gate reference drift")
    if gate.get("phase10f_repair_no_claim") is not True:
        errors.append("Phase 10F repair/no-claim gate missing")
    if gate.get("phase10f_no_compliant_registry_manifest_constructed_or_provided") is not True:
        errors.append("Phase 10F no compliant manifest gate missing")
    if gate.get("phase10f_no_compliant_registry_input_or_source_exists") is not True:
        errors.append("Phase 10F no compliant input/source gate missing")
    if gate.get("phase10f_no_fallback_authorized") is not True:
        errors.append("Phase 10F no fallback gate missing")
    if gate.get(PHASE10G_ORACLE_AUTHORIZATION) is not True:
        errors.append("Phase 10G oracle authorization boundary missing")
    if gate.get("only_phase10f_gate_constants_are_exact_references") is not True:
        errors.append("Phase 10F-only exact references boundary missing")
    if gate.get("local_same_tree_git_commits_not_read_or_compared") is not True:
        errors.append("local git commits not read boundary missing")
    if gate.get("older_phase9_10a_10b_10c_10d_10e_hygiene_exact_refs_not_republished_by_phase10g") is not True:
        errors.append("older exact refs not republished boundary missing")

    scope = report.get("phase10g_scope", {})
    for key in (
        "docs_only_closeout_and_external_input_protocol_freeze_only",
        "closes_phase10f_as_repair_no_claim_under_frozen_10e_protocol",
        "defines_future_external_input_package_contract_metadata_specification_only",
        "applies_frozen_phase10e_protocol_exactly_no_drift",
        "separate_from_phase9_not_continuation",
        "authorized_by_phase10f_gate_and_oracle",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
        "execution_remains_blocked_until_compliant_external_package_matches_contract",
        "no_registry_manifest_constructed_or_validated_in_phase10g",
        "no_external_input_package_constructed_or_intake_validated_in_phase10g",
    ):
        if scope.get(key) is not True:
            errors.append(f"phase10g_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10g_scope execution boundary failed: {key}")

    # Phase 10G protocol-freeze closed-list set-equality checks.
    protocol = report.get("phase10g_protocol_freeze", {})
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

    # Inherited frozen Phase 10E protocol closed-list set-equality checks
    # (proves no drift from 10E).
    inherited = report.get("inherited_frozen_phase10e_protocol", {})
    for _section, list_key, expected_tuple, label in INHERITED_PHASE10E_CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        actual = inherited.get(list_key)
        if not isinstance(actual, list):
            errors.append(f"inherited 10E protocol list missing: {list_key}")
            continue
        if set(actual) != set(expected_tuple):
            errors.append(f"inherited 10E protocol list drift: {label}")
            continue
        if len(actual) != len(set(actual)):
            errors.append(f"inherited 10E protocol list duplicates: {label}")
        for rule in expected_tuple:
            if inherited.get(rule) is not True:
                errors.append(f"inherited 10E protocol attestation missing: {rule}")

    inherited_anti = report.get("inherited_frozen_phase10e_anti_adaptation_rules", {})
    inherited_anti_list = inherited_anti.get("anti_adaptation_rules_list")
    if not isinstance(inherited_anti_list, list):
        errors.append("inherited 10E anti_adaptation_rules_list missing")
    else:
        if set(inherited_anti_list) != set(INHERITED_PHASE10E_ANTI_ADAPTATION_RULES):
            errors.append("inherited 10E anti_adaptation_rules_list drift")
        elif len(inherited_anti_list) != len(set(inherited_anti_list)):
            errors.append("inherited 10E anti_adaptation_rules_list duplicates")
    for rule in INHERITED_PHASE10E_ANTI_ADAPTATION_RULES:
        if inherited_anti.get(rule) is not True:
            errors.append(f"inherited 10E anti_adaptation attestation missing: {rule}")

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

    boundary = report.get("phase10g_boundary", {})
    for key in (
        "docs_only_closeout_plus_external_input_protocol_freeze",
        "closes_phase10f_repair_no_claim_under_frozen_10e_protocol",
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material",
        "does_not_materialize_source_contents",
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_construct_or_validate_a_registry_manifest",
        "does_not_construct_or_intake_validate_an_external_input_package",
        "does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f",
        "does_not_authorize_a_fallback_path",
        "does_not_treat_absent_external_package_as_permission_to_create_one",
        "does_not_inspect_public_registries",
        "does_not_infer_candidates_from_memory_docs_urls_indexes_search_or_prior_sources",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
        "execution_remains_blocked_until_compliant_external_package_matches_contract",
        "future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract",
        "phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "boundary_review_required_after_phase10g_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        if boundary.get(key) is not True:
            errors.append(f"phase10g_boundary missing: {key}")

    # Phase 10F closeout summary: enforce repair/no-claim closeout.
    closeout = report.get("phase10f_closeout_summary", {})
    if closeout.get("phase10f_closed_as_repair_no_claim") is not True:
        errors.append("phase10f_closed_as_repair_no_claim missing")
    if closeout.get("phase10f_closeout_bucket") != CLOSEOUT_BUCKET:
        errors.append("phase10f_closeout_bucket drift")
    if closeout.get("phase10f_no_compliant_registry_manifest_constructed_or_provided") is not True:
        errors.append("phase10f no compliant manifest closeout missing")
    if closeout.get("phase10f_no_compliant_registry_input_or_source_exists") is not True:
        errors.append("phase10f no compliant input/source closeout missing")
    if closeout.get("phase10f_no_fallback_authorized") is not True:
        errors.append("phase10f no fallback closeout missing")
    if closeout.get("phase10f_repair_no_claim_under_frozen_10e_protocol") is not True:
        errors.append("phase10f repair/no-claim under frozen 10E closeout missing")

    # External-input protocol-freeze summary: enforce no package exists /
    # validated and no registry construction.
    ext = report.get("external_input_protocol_freeze_summary", {})
    for key in (
        "future_external_input_package_contract_is_metadata_specification_only",
        "future_package_contract_enforced_as_exact_closed_list",
        "future_package_intake_validation_checks_defined_only_not_executed",
        "no_external_input_package_exists_or_was_intake_validated",
        "no_registry_manifest_constructed_or_validated",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
    ):
        if ext.get(key) is not True:
            errors.append(f"external_input_protocol_freeze_summary missing: {key}")
    if ext.get("execution_blocked_bucket") != EXECUTION_BLOCKED_BUCKET:
        errors.append("execution_blocked_bucket drift")
    if ext.get("no_compliant_registry_source_bucket") != NO_COMPLIANT_REGISTRY_SOURCE_BUCKET:
        errors.append("no_compliant_registry_source_bucket drift")
    if ext.get("no_fallback_bucket") != NO_FALLBACK_BUCKET:
        errors.append("no_fallback_bucket drift")

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
        "phase10g_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "future_package_contract_schema_check_available",
        "validator_enforces_future_package_contract_as_exact_closed_list",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_sources",
        "validator_does_not_read_ignored_runs",
        "validator_does_not_read_phase9_artifacts",
        "validator_does_not_read_phase10c_artifacts",
        "validator_does_not_read_phase10d_artifacts",
        "validator_does_not_read_phase10e_artifacts",
        "validator_does_not_read_phase10f_artifacts",
        "validator_does_not_inspect_sources",
        "validator_does_not_discover_sources",
        "validator_does_not_materialize_sources",
        "validator_does_not_generate_packets",
        "validator_does_not_generate_tasks",
        "validator_does_not_execute_downstream_pipeline",
        "validator_does_not_scrape_or_sample_or_download_sources",
        "validator_does_not_inspect_public_registries",
        "validator_does_not_infer_candidates_from_prior_sources",
        "validator_does_not_populate_candidate_registry",
        "validator_does_not_construct_or_validate_registry_manifest",
        "validator_does_not_construct_or_intake_validate_external_package",
        "validator_does_not_score_adjudicate_or_evaluate",
        "validator_does_not_modify_or_extend_phase10e_or_phase10f",
        "public_artifact_privacy_audit_expected",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in (
        "validator_executes_tasks",
        "validator_reads_private_registry",
        "validator_reads_sources",
        "validator_reads_ignored_runs",
        "validator_inspects_sources",
        "validator_inspects_public_registries",
        "validator_starts_empirical_work",
        "validator_discovers_sources",
        "validator_materializes_sources",
        "validator_generates_packets",
        "validator_generates_tasks",
        "validator_executes_downstream_pipeline",
        "validator_scrapes_or_samples_or_downloads_sources",
        "validator_infers_candidates_from_prior_sources",
        "validator_populates_candidate_registry",
        "validator_constructs_or_validates_registry_manifest",
        "validator_constructs_or_intake_validates_external_package",
        "validator_scores_or_adjudicates",
        "validator_modifies_or_extends_phase10e_or_phase10f",
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
    global FETCH_CLONE_ATTEMPTS, SOURCE_DISCOVERY_ATTEMPTS, SOURCE_INSPECTION_ATTEMPTS
    global MATERIALIZATION_ATTEMPTS, PACKET_GENERATION_ATTEMPTS, TASK_GENERATION_ATTEMPTS
    global DOWNSTREAM_PIPELINE_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS
    global PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS
    global PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS
    global SOURCE_MATERIAL_READ_ATTEMPTS, SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS
    global SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS, PUBLIC_REGISTRY_INSPECTION_ATTEMPTS
    global CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS
    global CANDIDATE_REGISTRY_POPULATION_ATTEMPTS
    global REGISTRY_MANIFEST_CONSTRUCTION_OR_VALIDATION_ATTEMPTS
    global EXTERNAL_INPUT_PACKAGE_CONSTRUCTION_OR_INTAKE_VALIDATION_ATTEMPTS
    global PACKAGE_INTAKE_VALIDATION_ATTEMPTS
    global SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS, PROVIDER_OR_MODEL_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_DISCOVERY_ATTEMPTS = 0
    SOURCE_INSPECTION_ATTEMPTS = 0
    MATERIALIZATION_ATTEMPTS = 0
    PACKET_GENERATION_ATTEMPTS = 0
    TASK_GENERATION_ATTEMPTS = 0
    DOWNSTREAM_PIPELINE_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
    SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS = 0
    PUBLIC_REGISTRY_INSPECTION_ATTEMPTS = 0
    CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS = 0
    CANDIDATE_REGISTRY_POPULATION_ATTEMPTS = 0
    REGISTRY_MANIFEST_CONSTRUCTION_OR_VALIDATION_ATTEMPTS = 0
    EXTERNAL_INPUT_PACKAGE_CONSTRUCTION_OR_INTAKE_VALIDATION_ATTEMPTS = 0
    PACKAGE_INTAKE_VALIDATION_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    # Baseline docs/protocol-freeze report validates.
    dry = build_public_report()
    checks.append(("report_valid", not validate_report(dry)))
    checks.append(("phase_equals_slug", dry["phase"] == PHASE))
    checks.append(("status_is_no_execution_no_claim", dry["status"] == STATUS))
    checks.append(("publication_level_boundary", dry["publication_level"] == PUBLICATION_LEVEL))

    # Gate facts enforced.  Only the immediate Phase 10F gate publishes exact
    # commit/CI identifiers; older checkpoints are status/bucket/scope only.
    checks.append(("phase9_status_gate", dry["gate_facts"]["phase9_status"] == PHASE9_STATUS))
    checks.append(("phase10a_status_gate", dry["gate_facts"]["phase10a_status"] == PHASE10A_STATUS))
    checks.append(("phase10b_status_gate", dry["gate_facts"]["phase10b_status"] == PHASE10B_STATUS))
    checks.append(("phase10c_status_gate", dry["gate_facts"]["phase10c_status"] == PHASE10C_STATUS))
    checks.append(("phase10c_accepted_bucket_zero", dry["gate_facts"]["phase10c_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10c_repair_bucket", dry["gate_facts"]["phase10c_repair_reason_bucket"] == "bucket_no_eligible_channel_registry"))
    checks.append(("phase10d_status_gate", dry["gate_facts"]["phase10d_status"] == PHASE10D_STATUS))
    checks.append(("phase10e_status_gate", dry["gate_facts"]["phase10e_status"] == PHASE10E_STATUS))
    checks.append(("phase10e_protocol_freeze_only", dry["gate_facts"]["phase10e_protocol_freeze_only_for_future_registry_construction"] is True))
    checks.append(("phase10f_commit_gate", dry["gate_facts"]["phase10f_commit"] == PHASE10F_COMMIT))
    checks.append(("phase10f_ci_gate", dry["gate_facts"]["phase10f_ci_run"] == PHASE10F_CI_RUN))
    checks.append(("phase10f_ci_success_gate", dry["gate_facts"]["phase10f_ci_success"] is True))
    checks.append(("phase10f_status_gate", dry["gate_facts"]["phase10f_status"] == PHASE10F_STATUS))
    checks.append(("phase10f_repair_no_claim_gate", dry["gate_facts"]["phase10f_repair_no_claim"] is True))
    checks.append(("phase10f_no_manifest_gate", dry["gate_facts"]["phase10f_no_compliant_registry_manifest_constructed_or_provided"] is True))
    checks.append(("phase10f_no_input_source_gate", dry["gate_facts"]["phase10f_no_compliant_registry_input_or_source_exists"] is True))
    checks.append(("phase10f_no_fallback_gate", dry["gate_facts"]["phase10f_no_fallback_authorized"] is True))
    checks.append(("phase10g_oracle_authorization", dry["gate_facts"][PHASE10G_ORACLE_AUTHORIZATION] is True))
    checks.append(("only_phase10f_refs", dry["gate_facts"]["only_phase10f_gate_constants_are_exact_references"] is True))

    # 10F closeout summary enforces repair/no-claim closeout.
    closeout = dry["phase10f_closeout_summary"]
    checks.append(("phase10f_closed_repair_no_claim", closeout["phase10f_closed_as_repair_no_claim"] is True))
    checks.append(("phase10f_closeout_bucket", closeout["phase10f_closeout_bucket"] == CLOSEOUT_BUCKET))
    checks.append(("phase10f_closeout_no_manifest", closeout["phase10f_no_compliant_registry_manifest_constructed_or_provided"] is True))
    checks.append(("phase10f_closeout_no_input", closeout["phase10f_no_compliant_registry_input_or_source_exists"] is True))
    checks.append(("phase10f_closeout_no_fallback", closeout["phase10f_no_fallback_authorized"] is True))
    checks.append(("phase10f_closeout_repair_under_10e", closeout["phase10f_repair_no_claim_under_frozen_10e_protocol"] is True))

    # External-input protocol-freeze summary enforces no package / no registry.
    ext = dry["external_input_protocol_freeze_summary"]
    for key in (
        "future_external_input_package_contract_is_metadata_specification_only",
        "future_package_contract_enforced_as_exact_closed_list",
        "future_package_intake_validation_checks_defined_only_not_executed",
        "no_external_input_package_exists_or_was_intake_validated",
        "no_registry_manifest_constructed_or_validated",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
    ):
        checks.append((f"ext_summary_{key}", ext[key] is True))
    checks.append(("ext_execution_blocked_bucket", ext["execution_blocked_bucket"] == EXECUTION_BLOCKED_BUCKET))
    checks.append(("ext_no_registry_source_bucket", ext["no_compliant_registry_source_bucket"] == NO_COMPLIANT_REGISTRY_SOURCE_BUCKET))
    checks.append(("ext_no_fallback_bucket", ext["no_fallback_bucket"] == NO_FALLBACK_BUCKET))

    # Phase 10G protocol-freeze closed lists are set-equality checked.
    proto = dry["phase10g_protocol_freeze"]
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

    # Inherited frozen 10E protocol closed lists set-equality (no drift).
    inherited = dry["inherited_frozen_phase10e_protocol"]
    for _section, list_key, expected_tuple, _label in INHERITED_PHASE10E_CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        actual = inherited.get(list_key)
        checks.append((f"inherited_10e_list_{list_key}_present", isinstance(actual, list)))
        if isinstance(actual, list):
            checks.append((f"inherited_10e_list_{list_key}_set_eq", set(actual) == set(expected_tuple)))
            checks.append((f"inherited_10e_list_{list_key}_no_dup", len(actual) == len(set(actual))))
        for rule in expected_tuple:
            checks.append((f"inherited_10e_attest_{rule}", inherited.get(rule) is True))

    # Inherited 10E anti-adaptation closed list.
    inh_anti = dry["inherited_frozen_phase10e_anti_adaptation_rules"]
    checks.append(("inherited_10e_anti_list_present", isinstance(inh_anti.get("anti_adaptation_rules_list"), list)))
    if isinstance(inh_anti.get("anti_adaptation_rules_list"), list):
        checks.append(("inherited_10e_anti_list_set_eq", set(inh_anti["anti_adaptation_rules_list"]) == set(INHERITED_PHASE10E_ANTI_ADAPTATION_RULES)))
    for rule in INHERITED_PHASE10E_ANTI_ADAPTATION_RULES:
        checks.append((f"inherited_10e_anti_attest_{rule}", inh_anti.get(rule) is True))

    # 10G anti-adaptation closed list.
    anti = dry["anti_adaptation_rules"]
    checks.append(("anti_adaptation_list_present", isinstance(anti.get("anti_adaptation_rules_list"), list)))
    if isinstance(anti.get("anti_adaptation_rules_list"), list):
        checks.append(("anti_adaptation_list_set_eq", set(anti["anti_adaptation_rules_list"]) == set(ANTI_ADAPTATION_RULES)))
    for rule in ANTI_ADAPTATION_RULES:
        checks.append((f"anti_adaptation_attest_{rule}", anti.get(rule) is True))

    # 10G boundary enforces docs-only/protocol-freeze / no forbidden ops.
    boundary = dry["phase10g_boundary"]
    for key in (
        "docs_only_closeout_plus_external_input_protocol_freeze",
        "closes_phase10f_repair_no_claim_under_frozen_10e_protocol",
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material",
        "does_not_materialize_source_contents",
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_construct_or_validate_a_registry_manifest",
        "does_not_construct_or_intake_validate_an_external_input_package",
        "does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f",
        "does_not_authorize_a_fallback_path",
        "does_not_treat_absent_external_package_as_permission_to_create_one",
        "does_not_inspect_public_registries",
        "does_not_infer_candidates_from_memory_docs_urls_indexes_search_or_prior_sources",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
        "execution_remains_blocked_until_compliant_external_package_matches_contract",
        "future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract",
        "phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "boundary_review_required_after_phase10g_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        checks.append((f"phase10g_boundary_{key}", boundary[key] is True))

    # Future external-input package contract schema enforcement (synthetic
    # fixtures only; no real package read/fetched/intake-validated).
    valid_pkg = {field: "synthetic_value" for field in FUTURE_EXTERNAL_INPUT_PACKAGE_CONTRACT_FIELDS}
    checks.append(("future_package_contract_valid_pkg_passes", not check_future_package_contract_schema(valid_pkg)))
    missing_pkg = {field: "synthetic_value" for field in FUTURE_EXTERNAL_INPUT_PACKAGE_CONTRACT_FIELDS if field != "immutable_checksums"}
    checks.append(("future_package_contract_missing_field_rejected", bool(check_future_package_contract_schema(missing_pkg))))
    extra_pkg = dict(valid_pkg)
    extra_pkg["extra_future_field"] = "synthetic_value"
    checks.append(("future_package_contract_extra_field_rejected", bool(check_future_package_contract_schema(extra_pkg))))
    checks.append(("future_package_contract_non_object_rejected", bool(check_future_package_contract_schema("not_a_dict"))))
    # Empty package rejected (all fields missing).
    checks.append(("future_package_contract_empty_rejected", bool(check_future_package_contract_schema({}))))
    # Contract field count matches required fields.
    checks.append(("future_package_contract_field_count", len(FUTURE_EXTERNAL_INPUT_PACKAGE_CONTRACT_FIELDS) == 8))

    # Reject missing/wrong gate facts.
    for field, bad_val, label in (
        ("phase9_status", "open", "phase9_status"),
        ("phase10a_status", "drift", "phase10a_status"),
        ("phase10b_status", "drift", "phase10b_status"),
        ("phase10c_status", "drift", "phase10c_status"),
        ("phase10c_accepted_source_bucket", "bucket_nonzero", "phase10c_bucket"),
        ("phase10c_repair_reason_bucket", "drift", "phase10c_repair"),
        ("phase10d_status", "drift", "phase10d_status"),
        ("phase10e_status", "drift", "phase10e_status"),
        ("phase10f_commit", "deadbeef", "phase10f_commit"),
        ("phase10f_ci_run", "0000", "phase10f_ci"),
        ("phase10f_status", "drift", "phase10f_status"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["gate_facts"][field] = bad_val
        checks.append((f"wrong_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        del mutated["gate_facts"][field]
        checks.append((f"missing_{label}_rejected", bool(validate_report(mutated))))

    # Reject 10F CI success flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["phase10f_ci_success"] = False
    checks.append(("phase10f_ci_success_false_rejected", bool(validate_report(mutated))))

    # Reject 10F repair/no-claim gate flipped to false.
    for gate_key in (
        "phase10f_repair_no_claim",
        "phase10f_no_compliant_registry_manifest_constructed_or_provided",
        "phase10f_no_compliant_registry_input_or_source_exists",
        "phase10f_no_fallback_authorized",
    ):
        mutated = copy.deepcopy(dry)
        mutated["gate_facts"][gate_key] = False
        checks.append((f"phase10f_{gate_key}_false_rejected", bool(validate_report(mutated))))

    # Reject 10G oracle authorization flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"][PHASE10G_ORACLE_AUTHORIZATION] = False
    checks.append(("phase10g_oracle_authorization_false_rejected", bool(validate_report(mutated))))

    # Reject phase10g_scope boundary facts flipped to false.
    for key in (
        "docs_only_closeout_and_external_input_protocol_freeze_only",
        "closes_phase10f_as_repair_no_claim_under_frozen_10e_protocol",
        "defines_future_external_input_package_contract_metadata_specification_only",
        "applies_frozen_phase10e_protocol_exactly_no_drift",
        "separate_from_phase9_not_continuation",
        "authorized_by_phase10f_gate_and_oracle",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
        "execution_remains_blocked_until_compliant_external_package_matches_contract",
        "no_registry_manifest_constructed_or_validated_in_phase10g",
        "no_external_input_package_constructed_or_intake_validated_in_phase10g",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10g_scope"][key] = False
        checks.append((f"phase10g_scope_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject execution booleans true (forbidden in Phase 10G).
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["phase10g_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject 10G boundary facts flipped to false.
    for key in (
        "docs_only_closeout_plus_external_input_protocol_freeze",
        "closes_phase10f_repair_no_claim_under_frozen_10e_protocol",
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material",
        "does_not_materialize_source_contents",
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_construct_or_validate_a_registry_manifest",
        "does_not_construct_or_intake_validate_an_external_input_package",
        "does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f",
        "does_not_authorize_a_fallback_path",
        "does_not_treat_absent_external_package_as_permission_to_create_one",
        "does_not_inspect_public_registries",
        "does_not_infer_candidates_from_memory_docs_urls_indexes_search_or_prior_sources",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
        "execution_remains_blocked_until_compliant_external_package_matches_contract",
        "future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract",
        "phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "boundary_review_required_after_phase10g_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10g_boundary"][key] = False
        checks.append((f"phase10g_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject 10F closeout summary facts flipped to false.
    for key in (
        "phase10f_closed_as_repair_no_claim",
        "phase10f_no_compliant_registry_manifest_constructed_or_provided",
        "phase10f_no_compliant_registry_input_or_source_exists",
        "phase10f_no_fallback_authorized",
        "phase10f_repair_no_claim_under_frozen_10e_protocol",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10f_closeout_summary"][key] = False
        checks.append((f"phase10f_closeout_{key}_false_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10f_closeout_summary"]["phase10f_closeout_bucket"] = "bucket_drift"
    checks.append(("phase10f_closeout_bucket_drift_rejected", bool(validate_report(mutated))))

    # Reject external-input summary facts flipped to false / bucket drift.
    for key in (
        "future_external_input_package_contract_is_metadata_specification_only",
        "future_package_contract_enforced_as_exact_closed_list",
        "future_package_intake_validation_checks_defined_only_not_executed",
        "no_external_input_package_exists_or_was_intake_validated",
        "no_registry_manifest_constructed_or_validated",
        "no_compliant_registry_source_exists",
        "no_fallback_path_authorized",
    ):
        mutated = copy.deepcopy(dry)
        mutated["external_input_protocol_freeze_summary"][key] = False
        checks.append((f"ext_summary_{key}_false_rejected", bool(validate_report(mutated))))
    for bucket_key, bad in (
        ("execution_blocked_bucket", "bucket_drift"),
        ("no_compliant_registry_source_bucket", "bucket_drift"),
        ("no_fallback_bucket", "bucket_drift"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["external_input_protocol_freeze_summary"][bucket_key] = bad
        checks.append((f"ext_summary_{bucket_key}_drift_rejected", bool(validate_report(mutated))))

    # Reject claim that a package exists / was validated (must stay false).
    for claim_key in ("external_package_exists_claim", "external_package_validated_claim"):
        mutated = copy.deepcopy(dry)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject anti-adaptation rules flipped to false.
    for key in ANTI_ADAPTATION_RULES:
        mutated = copy.deepcopy(dry)
        mutated["anti_adaptation_rules"][key] = False
        checks.append((f"anti_adaptation_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject anti-adaptation list drift (extra rule added / rule removed).
    mutated = copy.deepcopy(dry)
    mutated["anti_adaptation_rules"]["anti_adaptation_rules_list"] = list(ANTI_ADAPTATION_RULES) + ["extra_rule"]
    checks.append(("anti_adaptation_list_extra_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["anti_adaptation_rules"]["anti_adaptation_rules_list"] = list(ANTI_ADAPTATION_RULES)[:-1]
    checks.append(("anti_adaptation_list_missing_rejected", bool(validate_report(mutated))))

    # Reject 10G protocol-freeze list drift (extra member / member removed).
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        mutated = copy.deepcopy(dry)
        mutated["phase10g_protocol_freeze"][list_key] = list(expected_tuple) + ["extra_member"]
        checks.append((f"protocol_list_{list_key}_extra_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        mutated["phase10g_protocol_freeze"][list_key] = list(expected_tuple)[:-1]
        checks.append((f"protocol_list_{list_key}_missing_rejected", bool(validate_report(mutated))))

    # Reject protocol-freeze attestation flipped to false.
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        for rule in expected_tuple:
            mutated = copy.deepcopy(dry)
            mutated["phase10g_protocol_freeze"][rule] = False
            checks.append((f"protocol_attest_{rule}_false_rejected", bool(validate_report(mutated))))

    # Reject inherited 10E protocol list drift.
    for _section, list_key, expected_tuple, _label in INHERITED_PHASE10E_CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        mutated = copy.deepcopy(dry)
        mutated["inherited_frozen_phase10e_protocol"][list_key] = list(expected_tuple) + ["extra_member"]
        checks.append((f"inherited_10e_list_{list_key}_extra_rejected", bool(validate_report(mutated))))

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

    # Reject private-shaped values.  Test the public value scanner directly on
    # an allowed leaf path so these checks cannot pass merely because an
    # injected unknown report key was rejected first.
    allowed_leaf_paths = _allowed_leaf_paths()
    for label, bad_val in (
        ("url", "https://example.invalid/repo.git"),
        ("owner_repo", "owner/repo"),
        ("full_hash", "a" * 40),
        ("path", "src/private.py"),
        ("task_id", "owner/task_id_7"),
        ("run_dir", "runs/secret/run_dir"),
    ):
        scan_errors = _scan_public(
            bad_val,
            path="$.conservative_recommendation",
            key="conservative_recommendation",
            allowed_paths=allowed_leaf_paths,
        )
        checks.append((f"private_shaped_{label}_scanner_rejected", bool(scan_errors)))

    # Reject private-shaped keys.
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "source_path_bucket", "path", "repo_name", "task_id", "row_id",
        "packet_id", "manifest", "run_dir", "candidate_identity",
        "hash_value", "snippet_value",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10g_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        scan_errors = _scan_public(
            singleton_val,
            path="$.conservative_recommendation",
            key="conservative_recommendation",
            allowed_paths=allowed_leaf_paths,
        )
        checks.append((f"singleton_{singleton_val}_scanner_rejected", bool(scan_errors)))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # Reject forbidden success/claim wording (must NOT appear anywhere).
    for phrase in ("validated", "evidence_success achieved", "correctness evidence",
                   "materialization succeeded", "independent validation passed",
                   "OpenLocus works", "Phase 10 confirms", "Phase 10C confirms",
                   "Phase 10D confirms", "Phase 10E confirms", "Phase 10F confirms",
                   "Phase 10G confirms", "method proven", "product readiness",
                   "scoring success", "outcome success", "evaluation works",
                   "acquisition success", "adjudication proven", "correctness proven",
                   "lift achieved", "generalized success", "evidence-acquisition success",
                   "validation proven", "registry construction succeeded",
                   "registry provision proven", "external package exists",
                   "external package validated", "external package succeeded"):
        mutated = copy.deepcopy(dry)
        mutated["conservative_recommendation"] = phrase
        checks.append((f"forbidden_success_wording_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # Reject user-approval wording.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))
    scan_errors = _scan_public(
        "user must approve before proceeding",
        path="$.conservative_recommendation",
        key="conservative_recommendation",
        allowed_paths=allowed_leaf_paths,
    )
    checks.append(("user_approval_wording_scanner_rejected", bool(scan_errors)))

    # Reject placeholder wording.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        scan_errors = _scan_public(
            phrase,
            path="$.conservative_recommendation",
            key="conservative_recommendation",
            allowed_paths=allowed_leaf_paths,
        )
        checks.append((f"placeholder_{phrase}_scanner_rejected", bool(scan_errors)))

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
    mutated["phase10g_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_gate_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10g_protocol_freeze"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10f_closeout_summary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_closeout_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["external_input_protocol_freeze_summary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_ext_summary_rejected", bool(validate_report(mutated))))

    # Reject non-gate hash/CI values (gate values only allowed at exact paths).
    scan_errors = _scan_public(
        "29999999999",
        path="$.conservative_recommendation",
        key="conservative_recommendation",
        allowed_paths=allowed_leaf_paths,
    )
    checks.append(("non_whitelisted_ci_run_value_scanner_rejected", bool(scan_errors)))
    scan_errors = _scan_public(
        "0123456789abcdef0123456789abcdef01234567",
        path="$.conservative_recommendation",
        key="conservative_recommendation",
        allowed_paths=allowed_leaf_paths,
    )
    checks.append(("non_gate_ref_hash_value_scanner_rejected", bool(scan_errors)))
    checks.append(("gate_ref_values_on_whitelisted_paths_valid", not validate_report(dry)))

    # Reject flipping the "only Phase 10F gate constants are exact references".
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["only_phase10f_gate_constants_are_exact_references"] = False
    checks.append(("only_phase10f_refs_false_rejected", bool(validate_report(mutated))))

    # Reject modifying/extending 10E/10F in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_modifies_or_extends_phase10e_or_phase10f"] = True
    checks.append(("validator_modifies_phase10e_or_10f_rejected", bool(validate_report(mutated))))

    # Reject constructing/validating a registry manifest in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_constructs_or_validates_registry_manifest"] = True
    checks.append(("validator_constructs_registry_manifest_rejected", bool(validate_report(mutated))))

    # Reject intake-validating an external package in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_constructs_or_intake_validates_external_package"] = True
    checks.append(("validator_intake_validates_external_package_rejected", bool(validate_report(mutated))))

    # Path guard tests.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10g" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10f" / "report.json")
    checks.append(("validate_report_rejects_runs_phase10f_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10f_registry_construction_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10g" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Temp-file round-trip (synthetic fixture only; no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10g_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(dry), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))
        runs_tmp = Path(tmp) / "runs" / "report.json"
        runs_tmp.parent.mkdir(parents=True, exist_ok=True)
        runs_tmp.write_text(json.dumps(dry), encoding="utf-8")
        ok, _ = _validate_report_path_is_public(runs_tmp)
        checks.append(("validate_report_rejects_temp_runs_path", not ok))

    # Prove the self-test did not fetch/read/private/execute/score/construct/
    # materialize/inspect/generate-tasks/generate-packets/run-downstream/
    # intake-validate/inspect-public-registry/infer-candidates.
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_discover_sources", SOURCE_DISCOVERY_ATTEMPTS == 0))
    checks.append(("selftest_does_not_inspect_sources", SOURCE_INSPECTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_materialize", MATERIALIZATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_packets", PACKET_GENERATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_tasks", TASK_GENERATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_run_downstream_pipeline", DOWNSTREAM_PIPELINE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9_artifacts", PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10c_artifacts", PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10d_artifacts", PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10e_artifacts", PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10f_artifacts", PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_material", SOURCE_MATERIAL_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_scrape_or_sample_sources", SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_download_sources", SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS == 0))
    checks.append(("selftest_does_not_inspect_public_registries", PUBLIC_REGISTRY_INSPECTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_infer_candidates_from_prior_sources", CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS == 0))
    checks.append(("selftest_does_not_populate_candidate_registry", CANDIDATE_REGISTRY_POPULATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_construct_or_validate_registry_manifest", REGISTRY_MANIFEST_CONSTRUCTION_OR_VALIDATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_construct_or_intake_validate_external_package", EXTERNAL_INPUT_PACKAGE_CONSTRUCTION_OR_INTAKE_VALIDATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_intake_validate_package", PACKAGE_INTAKE_VALIDATION_ATTEMPTS == 0))
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
        description="Phase 10G external registry-input protocol freeze + Phase 10F closeout (no execution, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true",
                        help="write the external-input protocol-freeze + 10F closeout report (no private output, no fetch)")
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
