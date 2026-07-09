#!/usr/bin/env python3
"""Phase 10P0 offline registry operator package protocol freeze (no package generation, no Phase 10 validation, no claim).

Phase 10P0 freezes the protocol for an operator-prepared offline registry-input
package.  This phase does not generate package contents and does not perform
Phase 10 validation.

Phase 10P0 is a PROTOCOL-FREEZE-ONLY checkpoint.  It is docs/report/validator
only; it performs NO execution, NO package generation, NO source selection,
NO fetch/clone/download, and NO Phase 10H intake validation.  Phase 10P0:

  * freezes the protocol/specification for an operator-prepared offline
    registry-input package: package directory layout, manifest schema, required
    metadata fields, checksum/hash algorithm, audit-log format, privacy
    redaction rules, provenance fields, source acquisition rules,
    inclusion/exclusion criteria, immutability/freeze rules, operator workflow,
    and anti-tuning guardrails;
  * commits the provenance language for later generated packages: "operator-
    prepared package, produced by the current agent/operator preparation line
    under the frozen Phase 10P0 protocol; external to the Phase 10 validation
    pipeline, but not independent external-human generated";
  * states that package generation remains for a LATER Phase 10P1 (into an
    ignored/private path) and that Phase 10H intake validation remains a LATER,
    separately authorized phase; and
  * states that no package contents are generated or selected in Phase 10P0.

Phase 10P0 is FORBIDDEN from: generating a package; selecting concrete repos
or sources; cloning/downloading/fetching/scraping candidate sources; creating
manifests containing real repo URLs, owner identities, or concrete sample
contents; running Phase 10H intake validation; scoring, materialization,
correctness/evidence_success evaluation, or benchmark interpretation; tuning
the protocol based on Phase 10C/10F zero outcomes; claiming the package is
independent external-human generated; claiming validation success, recovery,
or evidence improvement; reading ignored ``runs/`` private data; using the
forbidden provenance wording ("fully external", "independent external
package", "third-party generated", "unbiased external validation", "evidence
success", "correctness recovered"); and modifying/weakening/reinterpreting or
extending Phase 10G or any earlier frozen Phase 10 protocol.

Phase 10P0 makes NO validation/product/method/correctness/evidence-success
claim; it records ONLY the frozen operator-package protocol specification and
the committed provenance language.  It does NOT generate package contents,
does NOT select concrete sources, does NOT fetch/clone/read/scrape/inspect/
sample/download source material, does NOT materialize source contents, does
NOT create manifests containing real repo URLs/identities/concrete sample
contents, does NOT run Phase 10H intake validation, does NOT score/adjudicate/
evaluate correctness/evidence_success, does NOT tune the protocol based on
Phase 10C/10F zero outcomes, and does NOT claim the package is independent
external-human generated.

Anti-tuning rule: Phase 10P0 is prospective.  It is NOT tuned to repair the
observed Phase 10C ``bucket_zero`` / ``bucket_no_eligible_channel_registry``
outcome or the Phase 10F ``bucket_zero`` /
``bucket_no_compliant_registry_input_under_frozen_10e_protocol`` outcome.
Phase 10C and Phase 10F are referenced ONLY as gate/provenance facts and
failure modes, NOT as optimization feedback.  No rule is justified by
"because 10C/10F found zero" unless framed as a general compliance/audit
requirement.  No new threshold/fallback/channel exception is introduced to
avoid the observed zero outcome.  Future package generation (Phase 10P1) must
use the frozen 10P0 protocol as written, with no post-hoc selection after
seeing source availability.

Required wording for this phase: "Phase 10P0 freezes the protocol for an
operator-prepared offline registry-input package. This phase does not
generate package contents and does not perform Phase 10 validation."

Required wording for later generated packages: "operator-prepared package,
produced by the current agent/operator preparation line under the frozen
Phase 10P0 protocol; external to the Phase 10 validation pipeline, but not
independent external-human generated."

This module performs no network/filesystem fetch, no source read, no private
ignored-``runs/`` read, no Phase 9/10A/10B/10C/10D/10E/10F/10G private artifact
read, no package generation, no source selection, no Phase 10H intake
validation, and no scoring/adjudication/correctness/evidence_success
computation.  The dry self-test and report validation use synthetic dict
fixtures only; the protocol-spec schema checks are exercised on synthetic
dicts only and do NOT read, fetch, or generate any real package.
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

# Import the frozen Phase 10G external registry-input protocol-freeze status
# constant directly from the committed Phase 10G protocol-freeze module so
# Phase 10P0 references EXACTLY the frozen upstream gate (no re-declaration,
# no drift).  The import itself performs no execution, no fetch, no private
# read; it only loads frozen constants.
try:  # namespace-package form (repo root on sys.path)
    from eval.interventional_evidence_acquisition_phase10g_external_registry_input_protocol_freeze import (  # noqa: E402
        STATUS as PHASE10G_STATUS_CONST,
        PHASE as PHASE10G_PHASE_CONST,
    )
except Exception:  # pragma: no cover - direct-module form (eval/ on sys.path)
    from interventional_evidence_acquisition_phase10g_external_registry_input_protocol_freeze import (  # type: ignore[no-redef]  # noqa: E402
        STATUS as PHASE10G_STATUS_CONST,
        PHASE as PHASE10G_PHASE_CONST,
    )


PHASE = (
    "phase10p0_operator_package_protocol_freeze"
    "_no_package_generation_no_phase10_validation_no_claim"
)
SCHEMA_VERSION = (
    "phase10p0_operator_package_protocol_freeze"
    "_no_package_generation_no_phase10_validation_no_claim_report_v1"
)
STATUS = PHASE
PUBLICATION_LEVEL = (
    "aggregate_operator_package_protocol_freeze_boundary_only"
)

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# Required wording constants (frozen, committed).
PHASE10P0_REQUIRED_WORDING = (
    "Phase 10P0 freezes the protocol for an operator-prepared offline "
    "registry-input package. This phase does not generate package contents "
    "and does not perform Phase 10 validation."
)
FUTURE_PACKAGE_PROVENANCE_WORDING = (
    "operator-prepared package, produced by the current agent/operator "
    "preparation line under the frozen Phase 10P0 protocol; external to the "
    "Phase 10 validation pipeline, but not independent external-human "
    "generated"
)

# ---------------------------------------------------------------------------
# Frozen gate references.  Phase 10P0 publishes the exact commit identifier
# only for the immediate Phase 10G gate.  Older Phase 9 / 10A / 10B / 10C /
# 10D / 10E / 10F checkpoints are carried forward only as status/bucket/scope
# provenance, not as exact commit/CI identifiers.  Local same-tree git commits
# are not read or compared.
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
PHASE10E_STATUS = "phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim"
PHASE10F_STATUS = "phase10f_candidate_source_registry_construction_repair_no_claim"
PHASE10F_ACCEPTED_SOURCE_BUCKET = "bucket_zero"
PHASE10F_REPAIR_REASON_BUCKET = "bucket_no_compliant_registry_input_under_frozen_10e_protocol"

# Phase 10G gate (the immediate gate frozen-on by Phase 10P0).  The Phase 10G
# commit is the only exact public gate reference published by Phase 10P0.
PHASE10G_COMMIT = "c9c85aaf8e1811068acb8cf8265ddb2f4097f126"
PHASE10G_CI_GREEN = True
PHASE10G_STATUS = PHASE10G_STATUS_CONST  # frozen, imported (no drift)
PHASE10G_PHASE = PHASE10G_PHASE_CONST  # frozen, imported (no drift)

# Phase 10P0 is authorized by oracle as operator-package protocol freeze ONLY,
# gated on Phase 10G commit + CI green.
PHASE10P0_ORACLE_AUTHORIZATION = (
    "phase10p0_authorized_by_oracle_operator_package_protocol_freeze_only"
)

# Boundary buckets for this checkpoint.
NO_PACKAGE_GENERATED_BUCKET = "bucket_no_package_contents_generated_or_selected_in_phase10p0"
NO_PHASE10_VALIDATION_BUCKET = "bucket_no_phase10_validation_performed_in_phase10p0"
PROTOCOL_FREEZE_ONLY_BUCKET = "bucket_phase10p0_protocol_freeze_only"
PACKAGE_GENERATION_FOR_PHASE10P1_BUCKET = (
    "bucket_package_generation_for_phase10p1_into_ignored_private_path"
)
PHASE10H_INTAKE_FOR_LATER_BUCKET = (
    "bucket_phase10h_intake_validation_for_later_separately_authorized_phase"
)

# ---------------------------------------------------------------------------
# Frozen Phase 10P0 operator-package protocol specification.
# These are STRUCTURAL protocol-freeze definitions only; no execution, no
# package generation, no source selection, no fetch/clone, no scoring/
# adjudication/correctness/evidence_success evaluation, no Phase 10H intake
# validation occurs in Phase 10P0.
# ---------------------------------------------------------------------------

# 1. Package directory layout (closed list).  A future operator-prepared
#    package under the frozen 10P0 protocol MUST contain EXACTLY these
#    top-level paths (closed list; the validator enforces set-equality and
#    rejects missing/extra future paths).  No package is generated in 10P0;
#    the layout is defined only.
PACKAGE_DIRECTORY_LAYOUT_FIELDS = (
    "manifest_json",
    "sources_directory",
    "audit_log_directory",
    "checksums_sha256_file",
    "provenance_json",
    "package_readme_md",
)

# 2. Manifest schema required metadata fields (closed list).  The manifest
#    of a future operator-prepared package MUST contain EXACTLY these fields.
MANIFEST_SCHEMA_REQUIRED_FIELDS = (
    "package_protocol_version",
    "package_prepared_by",
    "package_preparation_line",
    "source_count_bucket",
    "checksum_algorithm",
    "immutable_freeze_timestamp",
    "audit_log_format",
    "privacy_redaction_applied",
)

# 3. Checksum/hash algorithm (closed list — single frozen algorithm).
CHECKSUM_HASH_ALGORITHM = (
    "sha256",
)

# 4. Audit-log format required entry fields (closed list).
AUDIT_LOG_FORMAT_FIELDS = (
    "entry_type",
    "entry_timestamp",
    "entry_actor",
    "entry_action",
    "entry_subject_bucket",
)

# 5. Privacy redaction rules (closed list).
PRIVACY_REDACTION_RULES = (
    "redact_repo_urls",
    "redact_owner_identities",
    "redact_concrete_source_contents",
    "publish_aggregate_buckets_only",
    "confine_contents_to_ignored_private_path",
)

# 6. Provenance fields (closed list).
PROVENANCE_FIELDS = (
    "provenance_statement",
    "provenance_preparation_line",
    "provenance_externality",
    "provenance_not_independent_external_human_generated",
)

# 7. Source acquisition rules (closed list).
SOURCE_ACQUISITION_RULES = (
    "operator_acquires_sources_offline",
    "no_project_side_fetch_clone_scrape",
    "sources_must_be_locally_available_before_package_sealed",
    "acquisition_method_declared_by_operator",
)

# 8. Inclusion/exclusion criteria (closed list).
INCLUSION_EXCLUSION_CRITERIA = (
    "include_only_license_permitted_sources",
    "exclude_sources_requiring_forbidden_fetch",
    "exclude_sources_with_unresolved_license",
    "deterministic_source_ordering_no_randomness",
)

# 9. Immutability/freeze rules (closed list).
IMMUTABILITY_FREEZE_RULES = (
    "package_immutable_after_seal",
    "checksums_frozen_at_seal_time",
    "no_post_seal_modification",
    "protocol_version_pinned_to_phase10p0",
)

# 10. Operator workflow steps (closed list).
OPERATOR_WORKFLOW_STEPS = (
    "operator_prepares_package_offline",
    "operator_seals_package_with_checksums",
    "operator_declares_provenance",
    "package_written_to_ignored_private_path",
)

# 11. Anti-tuning guardrails (closed list).
ANTI_TUNING_GUARDRAILS = (
    "protocol_not_tuned_to_phase10c_or_10f_zero_outcomes",
    "no_threshold_padding_for_zero_outcomes",
    "no_fallback_to_invent_sources",
    "protocol_prospective_not_reactive",
    "future_execution_uses_frozen_protocol_no_post_hoc_selection",
)

# 12. Future package generation validation checks (defined only, NOT executed).
#     These are the prospective checks a LATER Phase 10P1 MAY run when
#     generating a package under the frozen 10P0 protocol, and a LATER Phase
#     10H MAY run when intake-validating a generated package.  Phase 10P0
#     defines them only; it does NOT run them, does NOT generate a package,
#     and does NOT intake-validate a package.
FUTURE_PACKAGE_VALIDATION_CHECKS = (
    "package_layout_check_only",
    "manifest_schema_check_only",
    "checksum_algorithm_check_only",
    "audit_log_format_check_only",
    "privacy_redaction_check_only",
    "provenance_wording_check_only",
)

# Closed protocol lists whose members are validator set-equality checked.
# Each entry is (report_section, list_key, expected_tuple, label).
CLOSED_PROTOCOL_LISTS = (
    (
        "phase10p0_protocol_freeze",
        "package_directory_layout_fields",
        PACKAGE_DIRECTORY_LAYOUT_FIELDS,
        "package_directory_layout_fields",
    ),
    (
        "phase10p0_protocol_freeze",
        "manifest_schema_required_fields",
        MANIFEST_SCHEMA_REQUIRED_FIELDS,
        "manifest_schema_required_fields",
    ),
    (
        "phase10p0_protocol_freeze",
        "checksum_hash_algorithm",
        CHECKSUM_HASH_ALGORITHM,
        "checksum_hash_algorithm",
    ),
    (
        "phase10p0_protocol_freeze",
        "audit_log_format_fields",
        AUDIT_LOG_FORMAT_FIELDS,
        "audit_log_format_fields",
    ),
    (
        "phase10p0_protocol_freeze",
        "privacy_redaction_rules",
        PRIVACY_REDACTION_RULES,
        "privacy_redaction_rules",
    ),
    (
        "phase10p0_protocol_freeze",
        "provenance_fields",
        PROVENANCE_FIELDS,
        "provenance_fields",
    ),
    (
        "phase10p0_protocol_freeze",
        "source_acquisition_rules",
        SOURCE_ACQUISITION_RULES,
        "source_acquisition_rules",
    ),
    (
        "phase10p0_protocol_freeze",
        "inclusion_exclusion_criteria",
        INCLUSION_EXCLUSION_CRITERIA,
        "inclusion_exclusion_criteria",
    ),
    (
        "phase10p0_protocol_freeze",
        "immutability_freeze_rules",
        IMMUTABILITY_FREEZE_RULES,
        "immutability_freeze_rules",
    ),
    (
        "phase10p0_protocol_freeze",
        "operator_workflow_steps",
        OPERATOR_WORKFLOW_STEPS,
        "operator_workflow_steps",
    ),
    (
        "phase10p0_protocol_freeze",
        "anti_tuning_guardrails",
        ANTI_TUNING_GUARDRAILS,
        "anti_tuning_guardrails",
    ),
    (
        "phase10p0_protocol_freeze",
        "future_package_validation_checks",
        FUTURE_PACKAGE_VALIDATION_CHECKS,
        "future_package_validation_checks",
    ),
)

# Inherited frozen Phase 10G status (mirrored for continuity; the validator
# checks it against the imported constant to prove no drift from 10G).
INHERITED_PHASE10G_STATUS = PHASE10G_STATUS_CONST
INHERITED_PHASE10G_PHASE = PHASE10G_PHASE_CONST

CONSERVATIVE_RECOMMENDATION = (
    "phase10p0_operator_package_protocol_freeze_only"
    "_phase9_closed_inherited"
    "_phase10a_gate_inherited"
    "_phase10b_gate_inherited"
    "_phase10c_executed_repair_no_claim_zero_accepted_sources_inherited"
    "_phase10d_closeout_guard_gate_inherited"
    "_phase10e_protocol_freeze_gate_inherited"
    "_phase10f_registry_construction_execution_gate_inherited_repair_no_claim"
    "_phase10g_external_registry_input_protocol_freeze_gate_inherited_ci_green"
    "_phase10p0_authorized_by_oracle_operator_package_protocol_freeze_only"
    "_phase10p0_is_protocol_specification_only_not_package_generation"
    "_phase10p0_is_not_phase10_validation"
    "_phase10p0_does_not_generate_package_contents"
    "_phase10p0_does_not_select_concrete_repos_or_sources"
    "_phase10p0_does_not_fetch_clone_download_scrape_or_inspect_candidate_sources"
    "_phase10p0_does_not_create_manifests_with_real_repo_urls_or_identities"
    "_phase10p0_does_not_run_phase10h_intake_validation"
    "_phase10p0_does_not_score_adjudicate_or_evaluate_correctness_evidence_success"
    "_phase10p0_does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes"
    "_phase10p0_does_not_claim_package_is_independent_external_human_generated"
    "_phase10p0_does_not_claim_validation_success_recovery_or_evidence_improvement"
    "_phase10p0_does_not_use_forbidden_provenance_wording"
    "_phase10p0_does_not_modify_weaken_reinterpret_or_extend_phase10g"
    "_phase10p0_protocol_is_prospective_not_tuned_to_observed_outcome"
    "_no_package_contents_generated_or_selected_in_phase10p0"
    "_no_phase10_validation_performed_in_phase10p0"
    "_protocol_freeze_only"
    "_package_generation_for_phase10p1_into_ignored_private_path"
    "_phase10h_intake_validation_for_later_separately_authorized_phase"
    "_future_package_provenance_is_operator_prepared_not_independent_external_human_generated"
    "_boundary_review_after_phase10p0_commit_and_ci_green"
    "_no_user_approval_wording_no_method_product_correctness_evidence_success_claim"
)

# ---------------------------------------------------------------------------
# Truth-boundary attestation keys that must always be True.
# ---------------------------------------------------------------------------
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_inherited",
    "phase10a_gate_inherited",
    "phase10b_gate_inherited",
    "phase10c_executed_repair_no_claim_zero_accepted_sources_inherited",
    "phase10d_closeout_guard_gate_inherited",
    "phase10e_protocol_freeze_gate_inherited",
    "phase10f_registry_construction_execution_gate_inherited",
    "phase10g_external_registry_input_protocol_freeze_gate_inherited",
    "phase10g_ci_green_inherited",
    "phase10p0_applies_frozen_phase10g_gate_exactly_no_drift",
    "phase10p0_is_operator_package_protocol_freeze_only",
    "phase10p0_is_separate_from_phase9_not_continuation",
    "phase10p0_is_separate_from_phase10g_not_reinterpretation",
    "phase10p0_makes_no_new_evidence_claims",
    "phase10p0_protocol_is_prospective_not_tuned_to_observed_outcome",
    "phase10p0_no_package_contents_generated_or_selected",
    "phase10p0_no_phase10_validation_performed",
    "phase10p0_no_concrete_repos_or_sources_selected",
    "phase10p0_no_fetch_clone_download_scrape_or_inspect_of_candidate_sources",
    "phase10p0_no_manifests_with_real_repo_urls_or_identities",
    "phase10p0_no_phase10h_intake_validation",
    "phase10p0_required_wording_committed",
    "phase10p0_future_package_provenance_wording_committed",
    "phase10p0_future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
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
    "phase10g_protocol_modified_or_reinterpreted_or_extended",
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
    "package_contents_generated",
    "package_generation_executed",
    "concrete_repos_or_sources_selected",
    "manifests_with_real_repo_urls_or_identities_created",
    "task_generation_executed",
    "packet_generation_executed",
    "downstream_pipeline_executed",
    "phase10h_intake_validation_executed",
    "thresholds_added",
    "fallbacks_added",
    "exceptions_added",
    "fallback_channels_added",
    "implicit_eligibility_expansion",
    "best_effort_source_invention",
    "protocol_tuned_to_observed_outcome",
    "post_hoc_selection_after_source_availability",
    "package_claimed_independent_external_human_generated",
    "validation_success_claimed",
    "validation_recovery_claimed",
    "evidence_improvement_claimed",
    "correctness_recovered_claimed",
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
    "phase10g_confirms_claim",
    "phase10p0_confirms_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "package_generated_claim",
    "package_validated_claim",
    "package_independent_external_human_generated_claim",
    "validation_success_claim",
    "validation_recovery_claim",
    "evidence_improvement_claim",
    "correctness_recovered_claim",
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
    "phase10g_private_artifacts_public",
    "source_urls_public",
    "candidate_repo_names_public",
    "candidate_identities_public",
    "package_contents_public",
    "package_checksums_public",
    "package_provenance_public",
    "concrete_source_contents_public",
    "real_repo_urls_in_manifests_public",
    "owner_identities_in_manifests_public",
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

# Forbidden provenance wording that MUST NOT appear in any public output.
FORBIDDEN_PROVENANCE_WORDING_RE = re.compile(
    r"\b(?:"
    r"fully\s+external"
    r"|independent\s+external\s+package"
    r"|third-party\s+generated"
    r"|third\s+party\s+generated"
    r"|unbiased\s+external\s+validation"
    r"|evidence\s+success"
    r"|correctness\s+recovered"
    r")\b",
    re.IGNORECASE,
)

CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"package\s+generation\s+(?:works|succeeded|proven|established)"
    r"|package\s+(?:generated|validated|succeeded|proven|established)"
    r"|evidence_success\s+(?:achieved|proven|established|confirmed)"
    r"|method\s+(?:proven|established|works|winner|effectiveness)"
    r"|product\s+readiness"
    r"|scoring\s+success"
    r"|outcome\s+success"
    r"|evaluation\s+works"
    r"|lift\s+(?:proven|established|achieved)"
    r"|adjudication\s+(?:works|succeeded|proven|established)"
    r"|correctness\s+(?:proven|established|achieved|confirmed|recovered)"
    r"|generalized\s+success"
    r"|validation\s+(?:works|succeeded|proven|established|recovered)"
    r"|independent\s+validation\s+passed"
    r"|openlocus\s+works"
    r"|phase\s*10\s+confirms"
    r"|phase\s*10g\s+confirms"
    r"|phase\s*10p0\s+confirms"
    r"|validation\s+success"
    r"|validation\s+recovery"
    r"|evidence\s+improvement"
    r"|validated\b"
    r")\b",
    re.IGNORECASE,
)

USER_APPROVAL_WORDING_RE = re.compile(
    r"\b(?:user\s+(?:must|should|needs?\s+to)\s+(?:approve|authorize|confirm)"
    r"|awaiting\s+user\s+(?:approval|authorization|confirmation)"
    r"|requires?\s+user\s+(?:approval|authorization))\b",
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
    r"|per_source|per_task|per_packet|package_content"
    r"|package_checksum|real_repo_url|owner_identity)",
    re.IGNORECASE,
)

LIST_VALUE_PRIVATE_TOKEN_RE = re.compile(
    r"(?:task_id|row_id|packet_id|observable_id|observable_path"
    r"|run_dir|source_path|manifest_path|candidate_id|commit_sha"
    r"|package_content|real_repo_url|owner_identity)",
    re.IGNORECASE,
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants.  These are the only exact public gate references
# published by Phase 10P0 (immediate Phase 10G gate commit only, plus the
# inherited Phase 10C/10F bucket constants).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10c_accepted_source_bucket",
        "$.gate_facts.phase10c_repair_reason_bucket",
        "$.gate_facts.phase10f_accepted_source_bucket",
        "$.gate_facts.phase10f_repair_reason_bucket",
        "$.gate_facts.phase10g_commit",
    }
)

# Required-wording JSON paths whose string values are frozen oracle-mandated
# wording that legitimately contains slash-bearing tokens (e.g. "agent/
# operator") and is NOT a private repo/owner identity.  These are exempt
# from the private-shaped-value scanner only.
REQUIRED_WORDING_EXEMPT_PATHS = frozenset(
    {
        "$.required_wording",
        "$.future_package_provenance_wording",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read/
# execute/score/generate/select/inspect.  Phase 10P0's protocol-freeze path
# generates and selects nothing; these stay zero.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_DISCOVERY_ATTEMPTS = 0
SOURCE_INSPECTION_ATTEMPTS = 0
MATERIALIZATION_ATTEMPTS = 0
PACKAGE_GENERATION_ATTEMPTS = 0
PACKET_GENERATION_ATTEMPTS = 0
TASK_GENERATION_ATTEMPTS = 0
DOWNSTREAM_PIPELINE_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10G_ARTIFACT_READ_ATTEMPTS = 0
SOURCE_MATERIAL_READ_ATTEMPTS = 0
SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS = 0
PUBLIC_REGISTRY_INSPECTION_ATTEMPTS = 0
CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS = 0
CONCRETE_REPO_OR_SOURCE_SELECTION_ATTEMPTS = 0
MANIFEST_WITH_REAL_REPO_URLS_OR_IDENTITIES_ATTEMPTS = 0
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


def _is_required_wording_value_path(path: str) -> bool:
    return path in REQUIRED_WORDING_EXEMPT_PATHS


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--validate-report``.

    The report path must be under the Phase 10P0 public artifact directory
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
        return False, "report path is not under the Phase 10P0 public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Protocol-spec schema enforcement (pure dict checks).
# These check ONLY whether a dict has exactly the closed field set.  They do
# NOT read files, fetch, generate, or select any real package.  The self-test
# exercises them on synthetic dicts only.
# ---------------------------------------------------------------------------

def _check_closed_field_set(pkg: Any, expected: tuple[str, ...], label: str) -> list[str]:
    """Check a dict against a frozen closed field set.

    Returns errors for any missing or extra fields.  This is a PURE schema
    check only; it does NOT read, fetch, generate, or select a real package.
    """
    errors: list[str] = []
    if not isinstance(pkg, dict):
        return [f"{label} requires an object"]
    expected_set = set(expected)
    actual = {str(key) for key in pkg.keys()}
    for missing in sorted(expected_set - actual):
        errors.append(f"{label} field missing: {missing}")
    for extra in sorted(actual - expected_set):
        errors.append(f"{label} field extra: {extra}")
    return errors


def check_package_directory_layout_schema(pkg: Any) -> list[str]:
    """Check a dict against the frozen package directory layout (closed list)."""
    return _check_closed_field_set(pkg, PACKAGE_DIRECTORY_LAYOUT_FIELDS, "package directory layout")


def check_manifest_schema(pkg: Any) -> list[str]:
    """Check a dict against the frozen manifest schema (closed list)."""
    return _check_closed_field_set(pkg, MANIFEST_SCHEMA_REQUIRED_FIELDS, "manifest schema")


def check_audit_log_format_schema(pkg: Any) -> list[str]:
    """Check a dict against the frozen audit-log format (closed list)."""
    return _check_closed_field_set(pkg, AUDIT_LOG_FORMAT_FIELDS, "audit log format")


def check_provenance_fields_schema(pkg: Any) -> list[str]:
    """Check a dict against the frozen provenance fields (closed list)."""
    return _check_closed_field_set(pkg, PROVENANCE_FIELDS, "provenance fields")


# ---------------------------------------------------------------------------
# Strict allowed-key schema for the public report
# ---------------------------------------------------------------------------

def _protocol_freeze_allowed() -> dict[str, Any]:
    """Build the allowed-schema dict for the protocol-freeze section."""
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
    "required_wording": None,
    "future_package_provenance_wording": None,
    "gate_facts": {
        "phase9_status": None,
        "phase10a_status": None,
        "phase10b_status": None,
        "phase10c_status": None,
        "phase10c_accepted_source_bucket": None,
        "phase10c_repair_reason_bucket": None,
        "phase10d_status": None,
        "phase10e_status": None,
        "phase10f_status": None,
        "phase10f_accepted_source_bucket": None,
        "phase10f_repair_reason_bucket": None,
        "phase10g_commit": None,
        "phase10g_ci_green": None,
        "phase10g_status": None,
        "phase10g_phase": None,
        PHASE10P0_ORACLE_AUTHORIZATION: None,
        "only_phase10g_gate_constants_are_exact_references": None,
        "local_same_tree_git_commits_not_read_or_compared": None,
        "older_phase9_10a_10b_10c_10d_10e_10f_hygiene_exact_refs_not_republished_by_phase10p0": None,
    },
    "phase10p0_scope": {
        "operator_package_protocol_freeze_only": None,
        "freezes_protocol_specification_not_package_generation": None,
        "commits_provenance_language_for_future_packages": None,
        "applies_frozen_phase10g_gate_exactly_no_drift": None,
        "separate_from_phase9_not_continuation": None,
        "separate_from_phase10g_not_reinterpretation": None,
        "authorized_by_phase10g_gate_and_oracle": None,
        "no_package_contents_generated_or_selected_in_phase10p0": None,
        "no_phase10_validation_performed_in_phase10p0": None,
        "package_generation_for_phase10p1_into_ignored_private_path": None,
        "phase10h_intake_validation_for_later_separately_authorized_phase": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "phase10p0_protocol_freeze": _protocol_freeze_allowed(),
    "inherited_frozen_phase10g_gate": {
        "phase10g_status": None,
        "phase10g_phase": None,
        "phase10g_imported_exactly_no_drift": None,
    },
    "phase10p0_boundary": {
        "operator_package_protocol_freeze_only": None,
        "does_not_generate_package_contents": None,
        "does_not_select_concrete_repos_or_sources": None,
        "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources": None,
        "does_not_create_manifests_with_real_repo_urls_or_identities": None,
        "does_not_run_phase10h_intake_validation": None,
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success": None,
        "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes": None,
        "does_not_claim_package_is_independent_external_human_generated": None,
        "does_not_claim_validation_success_recovery_or_evidence_improvement": None,
        "does_not_use_forbidden_provenance_wording": None,
        "does_not_modify_weaken_reinterpret_or_extend_phase10g": None,
        "no_package_contents_generated_or_selected_in_phase10p0": None,
        "no_phase10_validation_performed_in_phase10p0": None,
        "no_concrete_repos_or_sources_selected": None,
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources": None,
        "no_manifests_with_real_repo_urls_or_identities": None,
        "no_phase10h_intake_validation": None,
        "protocol_is_prospective_not_tuned_to_observed_outcome": None,
        "package_generation_for_phase10p1_into_ignored_private_path": None,
        "phase10h_intake_validation_for_later_separately_authorized_phase": None,
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated": None,
        "boundary_review_required_after_phase10p0_commit_and_ci_green": None,
        "no_user_approval_wording_as_protocol_dependency": None,
    },
    "protocol_freeze_summary": {
        "package_directory_layout_enforced_as_exact_closed_list": None,
        "manifest_schema_enforced_as_exact_closed_list": None,
        "checksum_hash_algorithm_enforced_as_exact_closed_list": None,
        "audit_log_format_enforced_as_exact_closed_list": None,
        "privacy_redaction_rules_enforced_as_exact_closed_list": None,
        "provenance_fields_enforced_as_exact_closed_list": None,
        "source_acquisition_rules_enforced_as_exact_closed_list": None,
        "inclusion_exclusion_criteria_enforced_as_exact_closed_list": None,
        "immutability_freeze_rules_enforced_as_exact_closed_list": None,
        "operator_workflow_steps_enforced_as_exact_closed_list": None,
        "anti_tuning_guardrails_enforced_as_exact_closed_list": None,
        "future_package_validation_checks_defined_only_not_executed": None,
        "no_package_contents_generated_or_selected": None,
        "no_phase10_validation_performed": None,
        "protocol_freeze_only_bucket": None,
        "no_package_generated_bucket": None,
        "no_phase10_validation_bucket": None,
        "package_generation_for_phase10p1_bucket": None,
        "phase10h_intake_for_later_bucket": None,
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
        "phase10p0_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "protocol_spec_schema_checks_available": None,
        "validator_enforces_protocol_lists_as_exact_closed_lists": None,
        "validator_rejects_forbidden_provenance_wording": None,
        "validator_rejects_package_generation_fields": None,
        "validator_rejects_unknown_keys": None,
        "validator_rejects_concrete_repo_like_identities": None,
        "validator_rejects_over_published_old_phase_refs": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_read_phase10c_artifacts": None,
        "validator_does_not_read_phase10d_artifacts": None,
        "validator_does_not_read_phase10e_artifacts": None,
        "validator_does_not_read_phase10f_artifacts": None,
        "validator_does_not_read_phase10g_artifacts": None,
        "validator_does_not_inspect_sources": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_generate_package": None,
        "validator_does_not_select_concrete_repos_or_sources": None,
        "validator_does_not_create_manifests_with_real_repo_urls": None,
        "validator_does_not_run_phase10h_intake_validation": None,
        "validator_does_not_generate_packets": None,
        "validator_does_not_generate_tasks": None,
        "validator_does_not_execute_downstream_pipeline": None,
        "validator_does_not_scrape_or_sample_or_download_sources": None,
        "validator_does_not_score_adjudicate_or_evaluate": None,
        "validator_does_not_modify_or_extend_phase10g": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_inspects_sources": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_generates_package": None,
        "validator_selects_concrete_repos_or_sources": None,
        "validator_creates_manifests_with_real_repo_urls": None,
        "validator_runs_phase10h_intake_validation": None,
        "validator_generates_packets": None,
        "validator_generates_tasks": None,
        "validator_executes_downstream_pipeline": None,
        "validator_scrapes_or_samples_or_downloads_sources": None,
        "validator_scores_or_adjudicates": None,
        "validator_modifies_or_extends_phase10g": None,
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
    is_required_wording = _is_required_wording_value_path(path)
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
        if FORBIDDEN_PROVENANCE_WORDING_RE.search(value):
            errors.append(f"forbidden provenance wording at {path}")
        if not is_gate_ref and not is_required_wording:
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
    """Build the phase10p0_protocol_freeze section with frozen lists + booleans."""
    section: dict[str, Any] = {}
    for _section_name, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = list(expected_tuple)
        for rule in expected_tuple:
            section[rule] = True
    return section


def build_public_report() -> dict[str, Any]:
    """Build the Phase 10P0 operator-package protocol-freeze report.

    This performs no network/filesystem fetch, no source read, no private
    ignored-``runs/`` read, no Phase 9/10A/10B/10C/10D/10E/10F/10G private
    artifact read, no package generation, no source selection, no Phase 10H
    intake validation, and no scoring/adjudication/correctness/evidence_success
    computation.  It assembles the report from the frozen gate constants and
    the 10P0 protocol specification definitions only.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "publication_level": PUBLICATION_LEVEL,
        "required_wording": PHASE10P0_REQUIRED_WORDING,
        "future_package_provenance_wording": FUTURE_PACKAGE_PROVENANCE_WORDING,
        "gate_facts": {
            "phase9_status": PHASE9_STATUS,
            "phase10a_status": PHASE10A_STATUS,
            "phase10b_status": PHASE10B_STATUS,
            "phase10c_status": PHASE10C_STATUS,
            "phase10c_accepted_source_bucket": PHASE10C_ACCEPTED_SOURCE_BUCKET,
            "phase10c_repair_reason_bucket": PHASE10C_REPAIR_REASON_BUCKET,
            "phase10d_status": PHASE10D_STATUS,
            "phase10e_status": PHASE10E_STATUS,
            "phase10f_status": PHASE10F_STATUS,
            "phase10f_accepted_source_bucket": PHASE10F_ACCEPTED_SOURCE_BUCKET,
            "phase10f_repair_reason_bucket": PHASE10F_REPAIR_REASON_BUCKET,
            "phase10g_commit": PHASE10G_COMMIT,
            "phase10g_ci_green": PHASE10G_CI_GREEN,
            "phase10g_status": PHASE10G_STATUS,
            "phase10g_phase": PHASE10G_PHASE,
            PHASE10P0_ORACLE_AUTHORIZATION: True,
            "only_phase10g_gate_constants_are_exact_references": True,
            "local_same_tree_git_commits_not_read_or_compared": True,
            "older_phase9_10a_10b_10c_10d_10e_10f_hygiene_exact_refs_not_republished_by_phase10p0": True,
        },
        "phase10p0_scope": {
            "operator_package_protocol_freeze_only": True,
            "freezes_protocol_specification_not_package_generation": True,
            "commits_provenance_language_for_future_packages": True,
            "applies_frozen_phase10g_gate_exactly_no_drift": True,
            "separate_from_phase9_not_continuation": True,
            "separate_from_phase10g_not_reinterpretation": True,
            "authorized_by_phase10g_gate_and_oracle": True,
            "no_package_contents_generated_or_selected_in_phase10p0": True,
            "no_phase10_validation_performed_in_phase10p0": True,
            "package_generation_for_phase10p1_into_ignored_private_path": True,
            "phase10h_intake_validation_for_later_separately_authorized_phase": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "phase10p0_protocol_freeze": _build_protocol_freeze_section(),
        "inherited_frozen_phase10g_gate": {
            "phase10g_status": INHERITED_PHASE10G_STATUS,
            "phase10g_phase": INHERITED_PHASE10G_PHASE,
            "phase10g_imported_exactly_no_drift": True,
        },
        "phase10p0_boundary": {
            "operator_package_protocol_freeze_only": True,
            "does_not_generate_package_contents": True,
            "does_not_select_concrete_repos_or_sources": True,
            "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources": True,
            "does_not_create_manifests_with_real_repo_urls_or_identities": True,
            "does_not_run_phase10h_intake_validation": True,
            "does_not_score_adjudicate_or_evaluate_correctness_evidence_success": True,
            "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes": True,
            "does_not_claim_package_is_independent_external_human_generated": True,
            "does_not_claim_validation_success_recovery_or_evidence_improvement": True,
            "does_not_use_forbidden_provenance_wording": True,
            "does_not_modify_weaken_reinterpret_or_extend_phase10g": True,
            "no_package_contents_generated_or_selected_in_phase10p0": True,
            "no_phase10_validation_performed_in_phase10p0": True,
            "no_concrete_repos_or_sources_selected": True,
            "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources": True,
            "no_manifests_with_real_repo_urls_or_identities": True,
            "no_phase10h_intake_validation": True,
            "protocol_is_prospective_not_tuned_to_observed_outcome": True,
            "package_generation_for_phase10p1_into_ignored_private_path": True,
            "phase10h_intake_validation_for_later_separately_authorized_phase": True,
            "future_package_provenance_is_operator_prepared_not_independent_external_human_generated": True,
            "boundary_review_required_after_phase10p0_commit_and_ci_green": True,
            "no_user_approval_wording_as_protocol_dependency": True,
        },
        "protocol_freeze_summary": {
            "package_directory_layout_enforced_as_exact_closed_list": True,
            "manifest_schema_enforced_as_exact_closed_list": True,
            "checksum_hash_algorithm_enforced_as_exact_closed_list": True,
            "audit_log_format_enforced_as_exact_closed_list": True,
            "privacy_redaction_rules_enforced_as_exact_closed_list": True,
            "provenance_fields_enforced_as_exact_closed_list": True,
            "source_acquisition_rules_enforced_as_exact_closed_list": True,
            "inclusion_exclusion_criteria_enforced_as_exact_closed_list": True,
            "immutability_freeze_rules_enforced_as_exact_closed_list": True,
            "operator_workflow_steps_enforced_as_exact_closed_list": True,
            "anti_tuning_guardrails_enforced_as_exact_closed_list": True,
            "future_package_validation_checks_defined_only_not_executed": True,
            "no_package_contents_generated_or_selected": True,
            "no_phase10_validation_performed": True,
            "protocol_freeze_only_bucket": PROTOCOL_FREEZE_ONLY_BUCKET,
            "no_package_generated_bucket": NO_PACKAGE_GENERATED_BUCKET,
            "no_phase10_validation_bucket": NO_PHASE10_VALIDATION_BUCKET,
            "package_generation_for_phase10p1_bucket": PACKAGE_GENERATION_FOR_PHASE10P1_BUCKET,
            "phase10h_intake_for_later_bucket": PHASE10H_INTAKE_FOR_LATER_BUCKET,
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
            "phase10p0_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "protocol_spec_schema_checks_available": True,
            "validator_enforces_protocol_lists_as_exact_closed_lists": True,
            "validator_rejects_forbidden_provenance_wording": True,
            "validator_rejects_package_generation_fields": True,
            "validator_rejects_unknown_keys": True,
            "validator_rejects_concrete_repo_like_identities": True,
            "validator_rejects_over_published_old_phase_refs": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_read_phase10c_artifacts": True,
            "validator_does_not_read_phase10d_artifacts": True,
            "validator_does_not_read_phase10e_artifacts": True,
            "validator_does_not_read_phase10f_artifacts": True,
            "validator_does_not_read_phase10g_artifacts": True,
            "validator_does_not_inspect_sources": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_generate_package": True,
            "validator_does_not_select_concrete_repos_or_sources": True,
            "validator_does_not_create_manifests_with_real_repo_urls": True,
            "validator_does_not_run_phase10h_intake_validation": True,
            "validator_does_not_generate_packets": True,
            "validator_does_not_generate_tasks": True,
            "validator_does_not_execute_downstream_pipeline": True,
            "validator_does_not_scrape_or_sample_or_download_sources": True,
            "validator_does_not_score_adjudicate_or_evaluate": True,
            "validator_does_not_modify_or_extend_phase10g": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_inspects_sources": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_generates_package": False,
            "validator_selects_concrete_repos_or_sources": False,
            "validator_creates_manifests_with_real_repo_urls": False,
            "validator_runs_phase10h_intake_validation": False,
            "validator_generates_packets": False,
            "validator_generates_tasks": False,
            "validator_executes_downstream_pipeline": False,
            "validator_scrapes_or_samples_or_downloads_sources": False,
            "validator_scores_or_adjudicates": False,
            "validator_modifies_or_extends_phase10g": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }
    return report


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_report(report: Any) -> list[str]:
    """Validate the Phase 10P0 public report against the frozen schema/constants.

    This does NOT read any Phase 9/10A/10B/10C/10D/10E/10F/10G artifact on
    disk, does NOT fetch/clone, does NOT read ignored ``runs/``, does NOT
    inspect sources, does NOT generate a package, does NOT select concrete
    sources, does NOT run Phase 10H intake validation, and does NOT score.  It
    checks the report's gate references against the frozen public gate
    constants directly, and applies the closed 10P0 protocol lists with
    set-equality against the frozen constants.
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
    if report.get("required_wording") != PHASE10P0_REQUIRED_WORDING:
        errors.append("required wording drift")
    if report.get("future_package_provenance_wording") != FUTURE_PACKAGE_PROVENANCE_WORDING:
        errors.append("future package provenance wording drift")

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
        errors.append("Phase 10E status gate fact drift")
    if gate.get("phase10f_status") != PHASE10F_STATUS:
        errors.append("Phase 10F status gate fact drift")
    if gate.get("phase10f_accepted_source_bucket") != PHASE10F_ACCEPTED_SOURCE_BUCKET:
        errors.append("Phase 10F accepted source bucket gate fact drift")
    if gate.get("phase10f_repair_reason_bucket") != PHASE10F_REPAIR_REASON_BUCKET:
        errors.append("Phase 10F repair reason bucket gate fact drift")
    if gate.get("phase10g_commit") != PHASE10G_COMMIT:
        errors.append("Phase 10G commit gate reference drift")
    if gate.get("phase10g_ci_green") is not True:
        errors.append("Phase 10G CI green gate missing")
    if gate.get("phase10g_status") != PHASE10G_STATUS:
        errors.append("Phase 10G status gate reference drift")
    if gate.get("phase10g_phase") != PHASE10G_PHASE:
        errors.append("Phase 10G phase gate reference drift")
    if gate.get(PHASE10P0_ORACLE_AUTHORIZATION) is not True:
        errors.append("Phase 10P0 oracle authorization boundary missing")
    if gate.get("only_phase10g_gate_constants_are_exact_references") is not True:
        errors.append("Phase 10G-only exact references boundary missing")
    if gate.get("local_same_tree_git_commits_not_read_or_compared") is not True:
        errors.append("local git commits not read boundary missing")
    if gate.get("older_phase9_10a_10b_10c_10d_10e_10f_hygiene_exact_refs_not_republished_by_phase10p0") is not True:
        errors.append("older exact refs not republished boundary missing")

    scope = report.get("phase10p0_scope", {})
    for key in (
        "operator_package_protocol_freeze_only",
        "freezes_protocol_specification_not_package_generation",
        "commits_provenance_language_for_future_packages",
        "applies_frozen_phase10g_gate_exactly_no_drift",
        "separate_from_phase9_not_continuation",
        "separate_from_phase10g_not_reinterpretation",
        "authorized_by_phase10g_gate_and_oracle",
        "no_package_contents_generated_or_selected_in_phase10p0",
        "no_phase10_validation_performed_in_phase10p0",
        "package_generation_for_phase10p1_into_ignored_private_path",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
    ):
        if scope.get(key) is not True:
            errors.append(f"phase10p0_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10p0_scope execution boundary failed: {key}")

    # Phase 10P0 protocol-freeze closed-list set-equality checks.
    protocol = report.get("phase10p0_protocol_freeze", {})
    for _section, list_key, expected_tuple, label in CLOSED_PROTOCOL_LISTS:
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

    # Inherited frozen Phase 10G gate drift check.
    inherited = report.get("inherited_frozen_phase10g_gate", {})
    if inherited.get("phase10g_status") != INHERITED_PHASE10G_STATUS:
        errors.append("inherited 10G status drift")
    if inherited.get("phase10g_phase") != INHERITED_PHASE10G_PHASE:
        errors.append("inherited 10G phase drift")
    if inherited.get("phase10g_imported_exactly_no_drift") is not True:
        errors.append("inherited 10G no-drift attestation missing")

    boundary = report.get("phase10p0_boundary", {})
    for key in (
        "operator_package_protocol_freeze_only",
        "does_not_generate_package_contents",
        "does_not_select_concrete_repos_or_sources",
        "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources",
        "does_not_create_manifests_with_real_repo_urls_or_identities",
        "does_not_run_phase10h_intake_validation",
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success",
        "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes",
        "does_not_claim_package_is_independent_external_human_generated",
        "does_not_claim_validation_success_recovery_or_evidence_improvement",
        "does_not_use_forbidden_provenance_wording",
        "does_not_modify_weaken_reinterpret_or_extend_phase10g",
        "no_package_contents_generated_or_selected_in_phase10p0",
        "no_phase10_validation_performed_in_phase10p0",
        "no_concrete_repos_or_sources_selected",
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources",
        "no_manifests_with_real_repo_urls_or_identities",
        "no_phase10h_intake_validation",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "package_generation_for_phase10p1_into_ignored_private_path",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
        "boundary_review_required_after_phase10p0_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        if boundary.get(key) is not True:
            errors.append(f"phase10p0_boundary missing: {key}")

    # Protocol-freeze summary enforcement.
    proto_sum = report.get("protocol_freeze_summary", {})
    for key in (
        "package_directory_layout_enforced_as_exact_closed_list",
        "manifest_schema_enforced_as_exact_closed_list",
        "checksum_hash_algorithm_enforced_as_exact_closed_list",
        "audit_log_format_enforced_as_exact_closed_list",
        "privacy_redaction_rules_enforced_as_exact_closed_list",
        "provenance_fields_enforced_as_exact_closed_list",
        "source_acquisition_rules_enforced_as_exact_closed_list",
        "inclusion_exclusion_criteria_enforced_as_exact_closed_list",
        "immutability_freeze_rules_enforced_as_exact_closed_list",
        "operator_workflow_steps_enforced_as_exact_closed_list",
        "anti_tuning_guardrails_enforced_as_exact_closed_list",
        "future_package_validation_checks_defined_only_not_executed",
        "no_package_contents_generated_or_selected",
        "no_phase10_validation_performed",
    ):
        if proto_sum.get(key) is not True:
            errors.append(f"protocol_freeze_summary missing: {key}")
    if proto_sum.get("protocol_freeze_only_bucket") != PROTOCOL_FREEZE_ONLY_BUCKET:
        errors.append("protocol_freeze_only_bucket drift")
    if proto_sum.get("no_package_generated_bucket") != NO_PACKAGE_GENERATED_BUCKET:
        errors.append("no_package_generated_bucket drift")
    if proto_sum.get("no_phase10_validation_bucket") != NO_PHASE10_VALIDATION_BUCKET:
        errors.append("no_phase10_validation_bucket drift")
    if proto_sum.get("package_generation_for_phase10p1_bucket") != PACKAGE_GENERATION_FOR_PHASE10P1_BUCKET:
        errors.append("package_generation_for_phase10p1_bucket drift")
    if proto_sum.get("phase10h_intake_for_later_bucket") != PHASE10H_INTAKE_FOR_LATER_BUCKET:
        errors.append("phase10h_intake_for_later_bucket drift")

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
        "phase10p0_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "protocol_spec_schema_checks_available",
        "validator_enforces_protocol_lists_as_exact_closed_lists",
        "validator_rejects_forbidden_provenance_wording",
        "validator_rejects_package_generation_fields",
        "validator_rejects_unknown_keys",
        "validator_rejects_concrete_repo_like_identities",
        "validator_rejects_over_published_old_phase_refs",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_sources",
        "validator_does_not_read_ignored_runs",
        "validator_does_not_read_phase9_artifacts",
        "validator_does_not_read_phase10c_artifacts",
        "validator_does_not_read_phase10d_artifacts",
        "validator_does_not_read_phase10e_artifacts",
        "validator_does_not_read_phase10f_artifacts",
        "validator_does_not_read_phase10g_artifacts",
        "validator_does_not_inspect_sources",
        "validator_does_not_discover_sources",
        "validator_does_not_materialize_sources",
        "validator_does_not_generate_package",
        "validator_does_not_select_concrete_repos_or_sources",
        "validator_does_not_create_manifests_with_real_repo_urls",
        "validator_does_not_run_phase10h_intake_validation",
        "validator_does_not_generate_packets",
        "validator_does_not_generate_tasks",
        "validator_does_not_execute_downstream_pipeline",
        "validator_does_not_scrape_or_sample_or_download_sources",
        "validator_does_not_score_adjudicate_or_evaluate",
        "validator_does_not_modify_or_extend_phase10g",
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
        "validator_starts_empirical_work",
        "validator_discovers_sources",
        "validator_materializes_sources",
        "validator_generates_package",
        "validator_selects_concrete_repos_or_sources",
        "validator_creates_manifests_with_real_repo_urls",
        "validator_runs_phase10h_intake_validation",
        "validator_generates_packets",
        "validator_generates_tasks",
        "validator_executes_downstream_pipeline",
        "validator_scrapes_or_samples_or_downloads_sources",
        "validator_scores_or_adjudicates",
        "validator_modifies_or_extends_phase10g",
    ):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    if report.get("conservative_recommendation") != CONSERVATIVE_RECOMMENDATION:
        errors.append("conservative recommendation drift")

    errors.extend(_check_allowed_keys(report, ALLOWED_REPORT_KEYS))
    errors.extend(_scan_public(report, allowed_paths=_allowed_leaf_paths()))
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Self-test (synthetic fixtures only; no network/private/scoring/generation)
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_DISCOVERY_ATTEMPTS, SOURCE_INSPECTION_ATTEMPTS
    global MATERIALIZATION_ATTEMPTS, PACKAGE_GENERATION_ATTEMPTS, PACKET_GENERATION_ATTEMPTS
    global TASK_GENERATION_ATTEMPTS, DOWNSTREAM_PIPELINE_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS
    global PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS
    global PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10G_ARTIFACT_READ_ATTEMPTS
    global SOURCE_MATERIAL_READ_ATTEMPTS, SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS
    global SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS, PUBLIC_REGISTRY_INSPECTION_ATTEMPTS
    global CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS
    global CONCRETE_REPO_OR_SOURCE_SELECTION_ATTEMPTS
    global MANIFEST_WITH_REAL_REPO_URLS_OR_IDENTITIES_ATTEMPTS
    global PACKAGE_INTAKE_VALIDATION_ATTEMPTS
    global SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS, PROVIDER_OR_MODEL_CALL_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_DISCOVERY_ATTEMPTS = 0
    SOURCE_INSPECTION_ATTEMPTS = 0
    MATERIALIZATION_ATTEMPTS = 0
    PACKAGE_GENERATION_ATTEMPTS = 0
    PACKET_GENERATION_ATTEMPTS = 0
    TASK_GENERATION_ATTEMPTS = 0
    DOWNSTREAM_PIPELINE_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS = 0
    PRIVATE_PHASE10G_ARTIFACT_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
    SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS = 0
    PUBLIC_REGISTRY_INSPECTION_ATTEMPTS = 0
    CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS = 0
    CONCRETE_REPO_OR_SOURCE_SELECTION_ATTEMPTS = 0
    MANIFEST_WITH_REAL_REPO_URLS_OR_IDENTITIES_ATTEMPTS = 0
    PACKAGE_INTAKE_VALIDATION_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    # Baseline protocol-freeze report validates.
    dry = build_public_report()
    checks.append(("report_valid", not validate_report(dry)))
    checks.append(("phase_equals_slug", dry["phase"] == PHASE))
    checks.append(("status_is_no_generation_no_validation_no_claim", dry["status"] == STATUS))
    checks.append(("publication_level_boundary", dry["publication_level"] == PUBLICATION_LEVEL))
    checks.append(("required_wording_committed", dry["required_wording"] == PHASE10P0_REQUIRED_WORDING))
    checks.append(("future_package_provenance_wording_committed", dry["future_package_provenance_wording"] == FUTURE_PACKAGE_PROVENANCE_WORDING))

    # Gate facts enforced.  Only the immediate Phase 10G gate publishes exact
    # commit identifier; older checkpoints are status/bucket/scope only.
    checks.append(("phase9_status_gate", dry["gate_facts"]["phase9_status"] == PHASE9_STATUS))
    checks.append(("phase10a_status_gate", dry["gate_facts"]["phase10a_status"] == PHASE10A_STATUS))
    checks.append(("phase10b_status_gate", dry["gate_facts"]["phase10b_status"] == PHASE10B_STATUS))
    checks.append(("phase10c_status_gate", dry["gate_facts"]["phase10c_status"] == PHASE10C_STATUS))
    checks.append(("phase10c_accepted_bucket_zero", dry["gate_facts"]["phase10c_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10c_repair_bucket", dry["gate_facts"]["phase10c_repair_reason_bucket"] == "bucket_no_eligible_channel_registry"))
    checks.append(("phase10d_status_gate", dry["gate_facts"]["phase10d_status"] == PHASE10D_STATUS))
    checks.append(("phase10e_status_gate", dry["gate_facts"]["phase10e_status"] == PHASE10E_STATUS))
    checks.append(("phase10f_status_gate", dry["gate_facts"]["phase10f_status"] == PHASE10F_STATUS))
    checks.append(("phase10f_accepted_bucket_zero", dry["gate_facts"]["phase10f_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10f_repair_bucket", dry["gate_facts"]["phase10f_repair_reason_bucket"] == "bucket_no_compliant_registry_input_under_frozen_10e_protocol"))
    checks.append(("phase10g_commit_gate", dry["gate_facts"]["phase10g_commit"] == PHASE10G_COMMIT))
    checks.append(("phase10g_ci_green_gate", dry["gate_facts"]["phase10g_ci_green"] is True))
    checks.append(("phase10g_status_gate", dry["gate_facts"]["phase10g_status"] == PHASE10G_STATUS))
    checks.append(("phase10g_phase_gate", dry["gate_facts"]["phase10g_phase"] == PHASE10G_PHASE))
    checks.append(("phase10p0_oracle_authorization", dry["gate_facts"][PHASE10P0_ORACLE_AUTHORIZATION] is True))
    checks.append(("only_phase10g_refs", dry["gate_facts"]["only_phase10g_gate_constants_are_exact_references"] is True))

    # Inherited 10G gate drift check.
    inh = dry["inherited_frozen_phase10g_gate"]
    checks.append(("inherited_10g_status_no_drift", inh["phase10g_status"] == INHERITED_PHASE10G_STATUS))
    checks.append(("inherited_10g_phase_no_drift", inh["phase10g_phase"] == INHERITED_PHASE10G_PHASE))
    checks.append(("inherited_10g_imported_exactly", inh["phase10g_imported_exactly_no_drift"] is True))

    # Protocol-freeze summary enforces no package / no validation.
    proto_sum = dry["protocol_freeze_summary"]
    for key in (
        "package_directory_layout_enforced_as_exact_closed_list",
        "manifest_schema_enforced_as_exact_closed_list",
        "checksum_hash_algorithm_enforced_as_exact_closed_list",
        "audit_log_format_enforced_as_exact_closed_list",
        "privacy_redaction_rules_enforced_as_exact_closed_list",
        "provenance_fields_enforced_as_exact_closed_list",
        "source_acquisition_rules_enforced_as_exact_closed_list",
        "inclusion_exclusion_criteria_enforced_as_exact_closed_list",
        "immutability_freeze_rules_enforced_as_exact_closed_list",
        "operator_workflow_steps_enforced_as_exact_closed_list",
        "anti_tuning_guardrails_enforced_as_exact_closed_list",
        "future_package_validation_checks_defined_only_not_executed",
        "no_package_contents_generated_or_selected",
        "no_phase10_validation_performed",
    ):
        checks.append((f"proto_summary_{key}", proto_sum[key] is True))
    checks.append(("proto_summary_protocol_freeze_only_bucket", proto_sum["protocol_freeze_only_bucket"] == PROTOCOL_FREEZE_ONLY_BUCKET))
    checks.append(("proto_summary_no_package_generated_bucket", proto_sum["no_package_generated_bucket"] == NO_PACKAGE_GENERATED_BUCKET))
    checks.append(("proto_summary_no_phase10_validation_bucket", proto_sum["no_phase10_validation_bucket"] == NO_PHASE10_VALIDATION_BUCKET))
    checks.append(("proto_summary_package_generation_bucket", proto_sum["package_generation_for_phase10p1_bucket"] == PACKAGE_GENERATION_FOR_PHASE10P1_BUCKET))
    checks.append(("proto_summary_phase10h_intake_bucket", proto_sum["phase10h_intake_for_later_bucket"] == PHASE10H_INTAKE_FOR_LATER_BUCKET))

    # Phase 10P0 protocol-freeze closed lists are set-equality checked.
    proto = dry["phase10p0_protocol_freeze"]
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        actual = proto.get(list_key)
        checks.append((f"protocol_list_{list_key}_present", isinstance(actual, list)))
        if isinstance(actual, list):
            checks.append((f"protocol_list_{list_key}_set_eq", set(actual) == set(expected_tuple)))
            checks.append((f"protocol_list_{list_key}_no_dup", len(actual) == len(set(actual))))
        for rule in expected_tuple:
            checks.append((f"protocol_attest_{rule}", proto.get(rule) is True))

    # 10P0 boundary enforces protocol-freeze / no forbidden ops.
    boundary = dry["phase10p0_boundary"]
    for key in (
        "operator_package_protocol_freeze_only",
        "does_not_generate_package_contents",
        "does_not_select_concrete_repos_or_sources",
        "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources",
        "does_not_create_manifests_with_real_repo_urls_or_identities",
        "does_not_run_phase10h_intake_validation",
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success",
        "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes",
        "does_not_claim_package_is_independent_external_human_generated",
        "does_not_claim_validation_success_recovery_or_evidence_improvement",
        "does_not_use_forbidden_provenance_wording",
        "does_not_modify_weaken_reinterpret_or_extend_phase10g",
        "no_package_contents_generated_or_selected_in_phase10p0",
        "no_phase10_validation_performed_in_phase10p0",
        "no_concrete_repos_or_sources_selected",
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources",
        "no_manifests_with_real_repo_urls_or_identities",
        "no_phase10h_intake_validation",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "package_generation_for_phase10p1_into_ignored_private_path",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
        "boundary_review_required_after_phase10p0_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        checks.append((f"phase10p0_boundary_{key}", boundary[key] is True))

    # Protocol-spec schema enforcement (synthetic fixtures only; no real
    # package read/fetched/generated/selected).
    valid_layout = {field: "synthetic_value" for field in PACKAGE_DIRECTORY_LAYOUT_FIELDS}
    checks.append(("layout_schema_valid_pkg_passes", not check_package_directory_layout_schema(valid_layout)))
    missing_layout = {field: "synthetic_value" for field in PACKAGE_DIRECTORY_LAYOUT_FIELDS if field != "checksums_sha256_file"}
    checks.append(("layout_schema_missing_field_rejected", bool(check_package_directory_layout_schema(missing_layout))))
    extra_layout = dict(valid_layout)
    extra_layout["extra_future_field"] = "synthetic_value"
    checks.append(("layout_schema_extra_field_rejected", bool(check_package_directory_layout_schema(extra_layout))))
    checks.append(("layout_schema_non_object_rejected", bool(check_package_directory_layout_schema("not_a_dict"))))
    checks.append(("layout_schema_empty_rejected", bool(check_package_directory_layout_schema({}))))

    valid_manifest = {field: "synthetic_value" for field in MANIFEST_SCHEMA_REQUIRED_FIELDS}
    checks.append(("manifest_schema_valid_pkg_passes", not check_manifest_schema(valid_manifest)))
    missing_manifest = {field: "synthetic_value" for field in MANIFEST_SCHEMA_REQUIRED_FIELDS if field != "checksum_algorithm"}
    checks.append(("manifest_schema_missing_field_rejected", bool(check_manifest_schema(missing_manifest))))
    extra_manifest = dict(valid_manifest)
    extra_manifest["extra_future_field"] = "synthetic_value"
    checks.append(("manifest_schema_extra_field_rejected", bool(check_manifest_schema(extra_manifest))))

    valid_audit = {field: "synthetic_value" for field in AUDIT_LOG_FORMAT_FIELDS}
    checks.append(("audit_log_schema_valid_pkg_passes", not check_audit_log_format_schema(valid_audit)))
    missing_audit = {field: "synthetic_value" for field in AUDIT_LOG_FORMAT_FIELDS if field != "entry_actor"}
    checks.append(("audit_log_schema_missing_field_rejected", bool(check_audit_log_format_schema(missing_audit))))

    valid_prov = {field: "synthetic_value" for field in PROVENANCE_FIELDS}
    checks.append(("provenance_schema_valid_pkg_passes", not check_provenance_fields_schema(valid_prov)))
    missing_prov = {field: "synthetic_value" for field in PROVENANCE_FIELDS if field != "provenance_statement"}
    checks.append(("provenance_schema_missing_field_rejected", bool(check_provenance_fields_schema(missing_prov))))

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
        ("phase10f_status", "drift", "phase10f_status"),
        ("phase10f_accepted_source_bucket", "bucket_nonzero", "phase10f_bucket"),
        ("phase10f_repair_reason_bucket", "drift", "phase10f_repair"),
        ("phase10g_commit", "deadbeef", "phase10g_commit"),
        ("phase10g_status", "drift", "phase10g_status"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["gate_facts"][field] = bad_val
        checks.append((f"wrong_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        del mutated["gate_facts"][field]
        checks.append((f"missing_{label}_rejected", bool(validate_report(mutated))))

    # Reject 10G CI green flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["phase10g_ci_green"] = False
    checks.append(("phase10g_ci_green_false_rejected", bool(validate_report(mutated))))

    # Reject 10P0 oracle authorization flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"][PHASE10P0_ORACLE_AUTHORIZATION] = False
    checks.append(("phase10p0_oracle_authorization_false_rejected", bool(validate_report(mutated))))

    # Reject phase10p0_scope boundary facts flipped to false.
    for key in (
        "operator_package_protocol_freeze_only",
        "freezes_protocol_specification_not_package_generation",
        "commits_provenance_language_for_future_packages",
        "applies_frozen_phase10g_gate_exactly_no_drift",
        "separate_from_phase9_not_continuation",
        "separate_from_phase10g_not_reinterpretation",
        "authorized_by_phase10g_gate_and_oracle",
        "no_package_contents_generated_or_selected_in_phase10p0",
        "no_phase10_validation_performed_in_phase10p0",
        "package_generation_for_phase10p1_into_ignored_private_path",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10p0_scope"][key] = False
        checks.append((f"phase10p0_scope_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject execution booleans true (forbidden in Phase 10P0).
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["phase10p0_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject 10P0 boundary facts flipped to false.
    for key in (
        "operator_package_protocol_freeze_only",
        "does_not_generate_package_contents",
        "does_not_select_concrete_repos_or_sources",
        "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources",
        "does_not_create_manifests_with_real_repo_urls_or_identities",
        "does_not_run_phase10h_intake_validation",
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success",
        "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes",
        "does_not_claim_package_is_independent_external_human_generated",
        "does_not_claim_validation_success_recovery_or_evidence_improvement",
        "does_not_use_forbidden_provenance_wording",
        "does_not_modify_weaken_reinterpret_or_extend_phase10g",
        "no_package_contents_generated_or_selected_in_phase10p0",
        "no_phase10_validation_performed_in_phase10p0",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "package_generation_for_phase10p1_into_ignored_private_path",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
        "boundary_review_required_after_phase10p0_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10p0_boundary"][key] = False
        checks.append((f"phase10p0_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject protocol-freeze summary facts flipped to false / bucket drift.
    for key in (
        "package_directory_layout_enforced_as_exact_closed_list",
        "manifest_schema_enforced_as_exact_closed_list",
        "checksum_hash_algorithm_enforced_as_exact_closed_list",
        "audit_log_format_enforced_as_exact_closed_list",
        "privacy_redaction_rules_enforced_as_exact_closed_list",
        "provenance_fields_enforced_as_exact_closed_list",
        "source_acquisition_rules_enforced_as_exact_closed_list",
        "inclusion_exclusion_criteria_enforced_as_exact_closed_list",
        "immutability_freeze_rules_enforced_as_exact_closed_list",
        "operator_workflow_steps_enforced_as_exact_closed_list",
        "anti_tuning_guardrails_enforced_as_exact_closed_list",
        "future_package_validation_checks_defined_only_not_executed",
        "no_package_contents_generated_or_selected",
        "no_phase10_validation_performed",
    ):
        mutated = copy.deepcopy(dry)
        mutated["protocol_freeze_summary"][key] = False
        checks.append((f"proto_summary_{key}_false_rejected", bool(validate_report(mutated))))
    for bucket_key, bad in (
        ("protocol_freeze_only_bucket", "bucket_drift"),
        ("no_package_generated_bucket", "bucket_drift"),
        ("no_phase10_validation_bucket", "bucket_drift"),
        ("package_generation_for_phase10p1_bucket", "bucket_drift"),
        ("phase10h_intake_for_later_bucket", "bucket_drift"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["protocol_freeze_summary"][bucket_key] = bad
        checks.append((f"proto_summary_{bucket_key}_drift_rejected", bool(validate_report(mutated))))

    # Reject claim that a package was generated / validated (must stay false).
    for claim_key in ("package_generated_claim", "package_validated_claim",
                      "package_independent_external_human_generated_claim",
                      "validation_success_claim", "validation_recovery_claim",
                      "evidence_improvement_claim", "correctness_recovered_claim"):
        mutated = copy.deepcopy(dry)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject protocol-freeze list drift (extra member / member removed).
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(dry)
        mutated["phase10p0_protocol_freeze"][list_key] = list(expected_tuple) + ["extra_member"]
        checks.append((f"protocol_list_{list_key}_extra_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        mutated["phase10p0_protocol_freeze"][list_key] = list(expected_tuple)[:-1]
        checks.append((f"protocol_list_{list_key}_missing_rejected", bool(validate_report(mutated))))

    # Reject protocol-freeze attestation flipped to false.
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        for rule in expected_tuple:
            mutated = copy.deepcopy(dry)
            mutated["phase10p0_protocol_freeze"][rule] = False
            checks.append((f"protocol_attest_{rule}_false_rejected", bool(validate_report(mutated))))

    # Reject inherited 10G gate drift.
    mutated = copy.deepcopy(dry)
    mutated["inherited_frozen_phase10g_gate"]["phase10g_status"] = "drift"
    checks.append(("inherited_10g_status_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["inherited_frozen_phase10g_gate"]["phase10g_phase"] = "drift"
    checks.append(("inherited_10g_phase_drift_rejected", bool(validate_report(mutated))))

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
        "hash_value", "snippet_value", "package_content", "real_repo_url",
        "owner_identity",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10p0_scope"][bad_key] = "example"
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

    # Reject forbidden provenance wording (must NOT appear anywhere).
    for phrase in ("fully external", "independent external package",
                   "third-party generated", "third party generated",
                   "unbiased external validation", "evidence success",
                   "correctness recovered"):
        scan_errors = _scan_public(
            phrase,
            path="$.conservative_recommendation",
            key="conservative_recommendation",
            allowed_paths=allowed_leaf_paths,
        )
        checks.append((f"forbidden_provenance_{phrase.replace(' ', '_').replace('-', '_')}_scanner_rejected",
                       bool(scan_errors)))
        # Also test in a report field directly.
        mutated = copy.deepcopy(dry)
        mutated["conservative_recommendation"] = phrase
        checks.append((f"forbidden_provenance_{phrase.replace(' ', '_').replace('-', '_')}_report_rejected",
                       bool(validate_report(mutated))))

    # Reject forbidden success/claim wording (must NOT appear anywhere).
    for phrase in ("validated", "evidence_success achieved",
                   "correctness evidence", "package generated",
                   "package validated", "package succeeded",
                   "independent validation passed", "OpenLocus works",
                   "Phase 10 confirms", "Phase 10G confirms",
                   "Phase 10P0 confirms", "method proven",
                   "product readiness", "scoring success",
                   "outcome success", "evaluation works",
                   "correctness proven", "correctness recovered",
                   "validation success", "validation recovery",
                   "evidence improvement", "generalized success"):
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

    # Reject required wording drift.
    mutated = copy.deepcopy(dry)
    mutated["required_wording"] = "wrong wording"
    checks.append(("required_wording_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["future_package_provenance_wording"] = "wrong provenance"
    checks.append(("future_package_provenance_wording_drift_rejected", bool(validate_report(mutated))))

    # Reject status/phase/schema/publication_level drift.
    for field, bad in (("status", "drift"), ("phase", "drift"),
                       ("schema_version", "drift"),
                       ("publication_level", "drift")):
        mutated = copy.deepcopy(dry)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # Reject unknown fields (closed-schema enforcement).
    mutated = copy.deepcopy(dry)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10p0_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_gate_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10p0_protocol_freeze"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["protocol_freeze_summary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_proto_summary_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10p0_boundary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_boundary_rejected", bool(validate_report(mutated))))

    # Reject package generation/execution fields appearing in the report.
    for bad_field in ("package_contents_generated", "package_generation_executed",
                      "concrete_repos_or_sources_selected", "phase10h_intake_validation_executed",
                      "scoring_executed", "materialization_executed"):
        mutated = copy.deepcopy(dry)
        mutated["phase10p0_scope"][bad_field] = True
        checks.append((f"package_generation_field_{bad_field}_rejected", bool(validate_report(mutated))))

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

    # Reject flipping the "only Phase 10G gate constants are exact references".
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["only_phase10g_gate_constants_are_exact_references"] = False
    checks.append(("only_phase10g_refs_false_rejected", bool(validate_report(mutated))))

    # Reject modifying/extending 10G in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_modifies_or_extends_phase10g"] = True
    checks.append(("validator_modifies_phase10g_rejected", bool(validate_report(mutated))))

    # Reject generating a package in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_generates_package"] = True
    checks.append(("validator_generates_package_rejected", bool(validate_report(mutated))))

    # Reject selecting concrete repos in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_selects_concrete_repos_or_sources"] = True
    checks.append(("validator_selects_concrete_repos_rejected", bool(validate_report(mutated))))

    # Reject running Phase 10H intake validation in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_runs_phase10h_intake_validation"] = True
    checks.append(("validator_runs_phase10h_intake_rejected", bool(validate_report(mutated))))

    # Path guard tests.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10p0" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10g" / "report.json")
    checks.append(("validate_report_rejects_runs_phase10g_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10g_external_registry_input_protocol_freeze_no_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10p0" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Temp-file round-trip (synthetic fixture only; no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10p0_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(dry), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))
        runs_tmp = Path(tmp) / "runs" / "report.json"
        runs_tmp.parent.mkdir(parents=True, exist_ok=True)
        runs_tmp.write_text(json.dumps(dry), encoding="utf-8")
        ok, _ = _validate_report_path_is_public(runs_tmp)
        checks.append(("validate_report_rejects_temp_runs_path", not ok))

    # Prove the self-test did not fetch/read/private/execute/score/generate/
    # select/inspect/generate-tasks/generate-packets/run-downstream/
    # intake-validate.
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_discover_sources", SOURCE_DISCOVERY_ATTEMPTS == 0))
    checks.append(("selftest_does_not_inspect_sources", SOURCE_INSPECTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_materialize", MATERIALIZATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_package", PACKAGE_GENERATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_packets", PACKET_GENERATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_generate_tasks", TASK_GENERATION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_run_downstream_pipeline", DOWNSTREAM_PIPELINE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase9_artifacts", PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10c_artifacts", PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10d_artifacts", PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10e_artifacts", PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10f_artifacts", PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10g_artifacts", PRIVATE_PHASE10G_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_material", SOURCE_MATERIAL_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_scrape_or_sample_sources", SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_download_sources", SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS == 0))
    checks.append(("selftest_does_not_inspect_public_registries", PUBLIC_REGISTRY_INSPECTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_infer_candidates_from_prior_sources", CANDIDATE_INFERENCE_FROM_PRIOR_SOURCES_ATTEMPTS == 0))
    checks.append(("selftest_does_not_select_concrete_repos_or_sources", CONCRETE_REPO_OR_SOURCE_SELECTION_ATTEMPTS == 0))
    checks.append(("selftest_does_not_create_manifests_with_real_repo_urls", MANIFEST_WITH_REAL_REPO_URLS_OR_IDENTITIES_ATTEMPTS == 0))
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
        description="Phase 10P0 offline registry operator package protocol freeze (no package generation, no Phase 10 validation, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true",
                        help="write the operator-package protocol-freeze report (no private output, no fetch, no generation)")
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
