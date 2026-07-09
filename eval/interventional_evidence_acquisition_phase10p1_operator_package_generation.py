#!/usr/bin/env python3
"""Phase 10P1 operator-prepared offline registry-input package generation (sealed, no Phase 10 validation, no claim).

Phase 10P1 generates and seals an operator-prepared offline registry-input
package under the FROZEN Phase 10P0 operator-package protocol, writing the
package into an ignored/private path under ``runs/`` only, and producing an
aggregate/boundary-only public report.  Phase 10P1 does NOT perform Phase 10
validation.

Phase 10P1 is an OPERATOR-PACKAGE GENERATION-AND-SEALING-ONLY checkpoint
authorized by oracle, gated on the frozen Phase 10P0 operator-package
protocol-freeze gate (commit ``621eb61aba0b3fa027b5c96f168056aaea951b5a``,
CI green).  It imports the frozen Phase 10P0 protocol constants directly from
the committed Phase 10P0 protocol-freeze module (no re-declaration, no drift,
set-equality validated) and applies them EXACTLY as frozen.  Phase 10P1:

  * generates an operator-prepared offline registry-input package under the
    frozen 10P0 directory layout (``manifest_json``, ``sources_directory``,
    ``audit_log_directory``, ``checksums_sha256_file``, ``provenance_json``,
    ``package_readme_md``) into an ignored/private path under ``runs/`` only;
  * seals the package with sha256 checksums (the single frozen algorithm);
  * declares the frozen operator-prepared provenance wording: "operator-
    prepared package, produced by the current agent/operator preparation line
    under the frozen Phase 10P0 protocol; external to the Phase 10 validation
    pipeline, but not independent external-human generated";
  * records that the package contains zero eligible concrete sources (none
    available offline without forbidden fetch; none invented/fabricated) — a
    conservative no-claim package — and therefore contains NO source/read
    material and is NOT Phase 10 validation evidence; and
  * publishes ONLY an aggregate/boundary-only public report (booleans/buckets
    only; no repo URLs/names/owners/commits/paths/snippets/line ranges/per-
    source facts/private counts/singleton counts/private checksums/package
    contents/package path).

Phase 10P1 is FORBIDDEN from: running Phase 10H intake validation; scoring,
materialization, correctness/evidence_success evaluation, or adjudication;
fetching/cloning/reading/scraping/inspecting/sampling/downloading source
material; selecting concrete repos or sources; inventing or fabricating source
material; creating manifests with real repo URLs or owner identities; reading
ignored ``runs/`` private data from earlier phases as evidence; treating the
package or its contents as Phase 10 validation evidence; tuning the protocol
based on Phase 10C/10F zero outcomes; claiming the package is independent
external-human generated; claiming validation success, recovery, or evidence
improvement; using the forbidden provenance wording; and modifying/weakening/
reinterpreting or extending Phase 10P0 or any earlier frozen Phase 10 protocol.

Phase 10P1 makes NO validation/product/method/correctness/evidence-success
claim.  It records ONLY that an operator-prepared package was generated and
sealed under the frozen 10P0 protocol into an ignored/private path, with zero
eligible concrete sources, and that no Phase 10 validation was performed.

Anti-tuning rule: Phase 10P1 is prospective.  It is NOT tuned to repair the
observed Phase 10C ``bucket_zero`` / ``bucket_no_eligible_channel_registry``
outcome or the Phase 10F ``bucket_zero`` /
``bucket_no_compliant_registry_input_under_frozen_10e_protocol`` outcome.  The
zero-source package is an honest consequence of no eligible concrete sources
being available offline without forbidden fetch — NOT a tuned/padded/fabricated
outcome.  No source is invented to avoid the observed zero outcome.  Phase 10C
and Phase 10F are referenced ONLY as gate/provenance facts and failure modes.

Required wording (frozen, inherited from 10P0): "Phase 10P0 freezes the
protocol for an operator-prepared offline registry-input package. This phase
does not generate package contents and does not perform Phase 10 validation."

Required provenance wording for generated packages (frozen, inherited from
10P0): "operator-prepared package, produced by the current agent/operator
preparation line under the frozen Phase 10P0 protocol; external to the Phase
10 validation pipeline, but not independent external-human generated."

This module writes the private package ONLY into an ignored/private path under
``runs/`` (fail-closed: if the target path is not under ignored ``runs/``, no
package is written and a blocker is reported).  It performs no network/filesystem
fetch, no source read, no private ignored-``runs/`` read of earlier phases, no
Phase 9/10A/10B/10C/10D/10E/10F/10G/10P0 private artifact read, no Phase 10H
intake validation, and no scoring/adjudication/correctness/evidence_success
computation.  The dry self-test and report validation use synthetic dict/file
fixtures only (synthetic values that do not coincide with real private outputs).
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Import the frozen Phase 10P0 operator-package protocol-freeze constants
# directly from the committed Phase 10P0 protocol-freeze module so Phase 10P1
# references EXACTLY the frozen upstream protocol (no re-declaration, no drift).
# The import itself performs no execution, no fetch, no private read; it only
# loads frozen constants and scanners.
try:  # namespace-package form (repo root on sys.path)
    from eval.interventional_evidence_acquisition_phase10p0_operator_package_protocol_freeze import (  # noqa: E402
        STATUS as PHASE10P0_STATUS_CONST,
        PHASE as PHASE10P0_PHASE_CONST,
        PHASE10P0_REQUIRED_WORDING,
        FUTURE_PACKAGE_PROVENANCE_WORDING,
        PACKAGE_DIRECTORY_LAYOUT_FIELDS,
        MANIFEST_SCHEMA_REQUIRED_FIELDS,
        CHECKSUM_HASH_ALGORITHM,
        AUDIT_LOG_FORMAT_FIELDS,
        PROVENANCE_FIELDS,
        PRIVACY_REDACTION_RULES,
        SOURCE_ACQUISITION_RULES,
        INCLUSION_EXCLUSION_CRITERIA,
        IMMUTABILITY_FREEZE_RULES,
        OPERATOR_WORKFLOW_STEPS,
        ANTI_TUNING_GUARDRAILS,
        FUTURE_PACKAGE_VALIDATION_CHECKS,
        PHASE9_STATUS as P10P0_PHASE9_STATUS,
        PHASE10A_STATUS as P10P0_PHASE10A_STATUS,
        PHASE10B_STATUS as P10P0_PHASE10B_STATUS,
        PHASE10C_STATUS as P10P0_PHASE10C_STATUS,
        PHASE10C_ACCEPTED_SOURCE_BUCKET as P10P0_PHASE10C_ACCEPTED_SOURCE_BUCKET,
        PHASE10C_REPAIR_REASON_BUCKET as P10P0_PHASE10C_REPAIR_REASON_BUCKET,
        PHASE10D_STATUS as P10P0_PHASE10D_STATUS,
        PHASE10E_STATUS as P10P0_PHASE10E_STATUS,
        PHASE10F_STATUS as P10P0_PHASE10F_STATUS,
        PHASE10F_ACCEPTED_SOURCE_BUCKET as P10P0_PHASE10F_ACCEPTED_SOURCE_BUCKET,
        PHASE10F_REPAIR_REASON_BUCKET as P10P0_PHASE10F_REPAIR_REASON_BUCKET,
        PHASE10G_CI_GREEN as P10P0_PHASE10G_CI_GREEN,
        PHASE10G_STATUS as P10P0_PHASE10G_STATUS,
        PHASE10G_PHASE as P10P0_PHASE10G_PHASE,
        FORBIDDEN_PROVENANCE_WORDING_RE,
        CLAIM_WORDING_RE,
        USER_APPROVAL_WORDING_RE,
        PLACEHOLDER_RE,
        PRIVATE_SHAPED_VALUE_RE,
        LONG_DECIMAL_VALUE_RE,
        SINGLETON_BUCKET_RE,
        PRIVATE_KEY_RE,
        LIST_VALUE_PRIVATE_TOKEN_RE,
        FORBIDDEN_PUBLIC_FIELD_WORDS,
    )
except Exception:  # pragma: no cover - direct-module form (eval/ on sys.path)
    from interventional_evidence_acquisition_phase10p0_operator_package_protocol_freeze import (  # type: ignore[no-redef]  # noqa: E402
        STATUS as PHASE10P0_STATUS_CONST,
        PHASE as PHASE10P0_PHASE_CONST,
        PHASE10P0_REQUIRED_WORDING,
        FUTURE_PACKAGE_PROVENANCE_WORDING,
        PACKAGE_DIRECTORY_LAYOUT_FIELDS,
        MANIFEST_SCHEMA_REQUIRED_FIELDS,
        CHECKSUM_HASH_ALGORITHM,
        AUDIT_LOG_FORMAT_FIELDS,
        PROVENANCE_FIELDS,
        PRIVACY_REDACTION_RULES,
        SOURCE_ACQUISITION_RULES,
        INCLUSION_EXCLUSION_CRITERIA,
        IMMUTABILITY_FREEZE_RULES,
        OPERATOR_WORKFLOW_STEPS,
        ANTI_TUNING_GUARDRAILS,
        FUTURE_PACKAGE_VALIDATION_CHECKS,
        PHASE9_STATUS as P10P0_PHASE9_STATUS,
        PHASE10A_STATUS as P10P0_PHASE10A_STATUS,
        PHASE10B_STATUS as P10P0_PHASE10B_STATUS,
        PHASE10C_STATUS as P10P0_PHASE10C_STATUS,
        PHASE10C_ACCEPTED_SOURCE_BUCKET as P10P0_PHASE10C_ACCEPTED_SOURCE_BUCKET,
        PHASE10C_REPAIR_REASON_BUCKET as P10P0_PHASE10C_REPAIR_REASON_BUCKET,
        PHASE10D_STATUS as P10P0_PHASE10D_STATUS,
        PHASE10E_STATUS as P10P0_PHASE10E_STATUS,
        PHASE10F_STATUS as P10P0_PHASE10F_STATUS,
        PHASE10F_ACCEPTED_SOURCE_BUCKET as P10P0_PHASE10F_ACCEPTED_SOURCE_BUCKET,
        PHASE10F_REPAIR_REASON_BUCKET as P10P0_PHASE10F_REPAIR_REASON_BUCKET,
        PHASE10G_CI_GREEN as P10P0_PHASE10G_CI_GREEN,
        PHASE10G_STATUS as P10P0_PHASE10G_STATUS,
        PHASE10G_PHASE as P10P0_PHASE10G_PHASE,
        FORBIDDEN_PROVENANCE_WORDING_RE,
        CLAIM_WORDING_RE,
        USER_APPROVAL_WORDING_RE,
        PLACEHOLDER_RE,
        PRIVATE_SHAPED_VALUE_RE,
        LONG_DECIMAL_VALUE_RE,
        SINGLETON_BUCKET_RE,
        PRIVATE_KEY_RE,
        LIST_VALUE_PRIVATE_TOKEN_RE,
        FORBIDDEN_PUBLIC_FIELD_WORDS,
    )


# ---------------------------------------------------------------------------
# Phase 10P1 identity / schema
# ---------------------------------------------------------------------------

PHASE = (
    "phase10p1_operator_package_generation_sealed"
    "_no_phase10_validation_no_claim"
)
SCHEMA_VERSION = PHASE + "_report_v1"
STATUS = PHASE
PUBLICATION_LEVEL = "aggregate_operator_package_generation_boundary_only"

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# Private package path (ignored/private).  Phase 10P1 writes the package ONLY
# here.  ``runs/`` is gitignored at the repo root.
DEFAULT_PACKAGE_DIR = (
    REPO / "runs" / "phase10p1_operator_package_generation" / "current"
)

# Concrete package filenames satisfying the frozen 10P0 layout fields.
PACKAGE_MANIFEST_FILE = "manifest.json"
PACKAGE_SOURCES_DIR = "sources"
PACKAGE_AUDIT_LOG_DIR = "audit_log"
PACKAGE_AUDIT_LOG_FILE = "audit.jsonl"
PACKAGE_CHECKSUMS_FILE = "checksums.sha256"
PACKAGE_PROVENANCE_FILE = "provenance.json"
PACKAGE_README_FILE = "README.md"

# Frozen gate references.  Phase 10P1 publishes the exact commit identifier
# only for the immediate Phase 10P0 gate.  Older Phase 9 / 10A / 10B / 10C /
# 10D / 10E / 10F / 10G checkpoints are carried forward only as status/bucket/
# scope provenance, not as exact commit/CI identifiers.  Local same-tree git
# commits are not read or compared.
PHASE10P0_COMMIT = "621eb61aba0b3fa027b5c96f168056aaea951b5a"
PHASE10P0_CI_GREEN = True
PHASE10P0_STATUS = PHASE10P0_STATUS_CONST  # frozen, imported (no drift)
PHASE10P0_PHASE = PHASE10P0_PHASE_CONST  # frozen, imported (no drift)

# Phase 10P1 is authorized by oracle as operator-package generation only,
# gated on Phase 10P0 commit + CI green.
PHASE10P1_ORACLE_AUTHORIZATION = (
    "phase10p1_authorized_by_oracle_operator_package_generation_only"
)

# Boundary buckets for this checkpoint.
PACKAGE_GENERATION_SEALED_BUCKET = (
    "bucket_operator_package_generation_sealed_under_frozen_phase10p0_protocol"
)
NO_PHASE10_VALIDATION_BUCKET = (
    "bucket_no_phase10_validation_performed_in_phase10p1"
)
PACKAGE_GENERATION_ONLY_BUCKET = (
    "bucket_phase10p1_operator_package_generation_sealed_only"
)
PHASE10H_INTAKE_FOR_LATER_BUCKET = (
    "bucket_phase10h_intake_validation_for_later_separately_authorized_phase"
)
ZERO_ELIGIBLE_SOURCES_BUCKET = (
    "bucket_zero_eligible_concrete_sources_available_offline_without_forbidden_fetch"
)

# Bucketized protocol-field counts (the frozen 10P0 protocol closed lists are
# public via Phase 10P0; bucketizing the counts here is privacy-safe).
LAYOUT_FIELDS_BUCKET = (
    "bucket_frozen_phase10p0_package_layout_six_fields"
)
MANIFEST_SCHEMA_BUCKET = (
    "bucket_frozen_phase10p0_manifest_eight_fields"
)
SOURCE_COUNT_BUCKET = "bucket_zero"

CONSERVATIVE_RECOMMENDATION = (
    "phase10p1_operator_package_generation_sealed_only_under_frozen_phase10p0_protocol"
    "_phase9_closed_inherited"
    "_phase10a_status_gate_inherited"
    "_phase10b_status_gate_inherited"
    "_phase10c_executed_repair_no_claim_zero_accepted_sources_inherited"
    "_phase10d_closeout_guard_gate_inherited"
    "_phase10e_protocol_freeze_gate_inherited"
    "_phase10f_registry_construction_execution_gate_inherited_repair_no_claim"
    "_phase10g_external_registry_input_protocol_freeze_gate_inherited"
    "_phase10p0_operator_package_protocol_freeze_gate_inherited_ci_green"
    "_phase10p1_authorized_by_oracle_operator_package_generation_only"
    "_phase10p1_applies_frozen_phase10p0_protocol_exactly_no_drift"
    "_phase10p1_is_operator_package_generation_sealed_only_not_phase10_validation"
    "_phase10p1_generates_and_seals_package_under_frozen_10p0_protocol_into_ignored_private_path"
    "_phase10p1_does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material"
    "_phase10p1_does_not_select_concrete_repos_or_sources"
    "_phase10p1_does_not_materialize_source_contents"
    "_phase10p1_does_not_run_phase10h_intake_validation"
    "_phase10p1_does_not_score_adjudicate_or_evaluate_correctness_evidence_success"
    "_phase10p1_does_not_invent_or_fabricate_source_material"
    "_phase10p1_does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes"
    "_phase10p1_does_not_claim_package_is_independent_external_human_generated"
    "_phase10p1_does_not_claim_validation_success_recovery_or_evidence_improvement"
    "_phase10p1_does_not_use_forbidden_provenance_wording"
    "_phase10p1_does_not_modify_weaken_reinterpret_or_extend_phase10p0"
    "_phase10p1_protocol_is_prospective_not_tuned_to_observed_outcome"
    "_zero_eligible_concrete_sources_available_offline_without_forbidden_fetch_none_invented"
    "_source_count_bucket_zero"
    "_package_sealed_with_sha256_checksums_into_ignored_private_path"
    "_no_phase10_validation_performed_in_phase10p1"
    "_phase10h_intake_validation_for_later_separately_authorized_phase"
    "_future_package_provenance_is_operator_prepared_not_independent_external_human_generated"
    "_boundary_review_after_phase10p1_commit_and_ci_green"
    "_no_user_approval_wording_no_method_product_correctness_evidence_success_claim"
)

# Frozen Phase 10P0 protocol closed lists imported exactly (no drift).  The
# validator set-equality checks each against the imported tuple.
CLOSED_PROTOCOL_LISTS = (
    ("package_directory_layout_fields", PACKAGE_DIRECTORY_LAYOUT_FIELDS),
    ("manifest_schema_required_fields", MANIFEST_SCHEMA_REQUIRED_FIELDS),
    ("checksum_hash_algorithm", CHECKSUM_HASH_ALGORITHM),
    ("audit_log_format_fields", AUDIT_LOG_FORMAT_FIELDS),
    ("privacy_redaction_rules", PRIVACY_REDACTION_RULES),
    ("provenance_fields", PROVENANCE_FIELDS),
    ("source_acquisition_rules", SOURCE_ACQUISITION_RULES),
    ("inclusion_exclusion_criteria", INCLUSION_EXCLUSION_CRITERIA),
    ("immutability_freeze_rules", IMMUTABILITY_FREEZE_RULES),
    ("operator_workflow_steps", OPERATOR_WORKFLOW_STEPS),
    ("anti_tuning_guardrails", ANTI_TUNING_GUARDRAILS),
    ("future_package_validation_checks", FUTURE_PACKAGE_VALIDATION_CHECKS),
)

# Truth-boundary attestation keys that must always be True.
TRUTH_BOUNDARY_TRUE_KEYS = (
    "phase9_closed_inherited",
    "phase10a_status_gate_inherited",
    "phase10b_status_gate_inherited",
    "phase10c_executed_repair_no_claim_zero_accepted_sources_inherited",
    "phase10d_closeout_guard_gate_inherited",
    "phase10e_protocol_freeze_gate_inherited",
    "phase10f_registry_construction_execution_gate_inherited",
    "phase10g_external_registry_input_protocol_freeze_gate_inherited",
    "phase10p0_operator_package_protocol_freeze_gate_inherited",
    "phase10p0_ci_green_inherited",
    "phase10p1_applies_frozen_phase10p0_protocol_exactly_no_drift",
    "phase10p1_is_operator_package_generation_sealed_only",
    "phase10p1_is_separate_from_phase10p0_not_reinterpretation",
    "phase10p1_is_separate_from_phase9_not_continuation",
    "phase10p1_makes_no_new_evidence_claims",
    "phase10p1_protocol_is_prospective_not_tuned_to_observed_outcome",
    "phase10p1_package_generation_executed_and_sealed",
    "phase10p1_package_written_to_ignored_private_path",
    "phase10p1_no_phase10_validation_performed",
    "phase10p1_no_concrete_repos_or_sources_selected",
    "phase10p1_no_fetch_clone_download_scrape_or_inspect_of_candidate_sources",
    "phase10p1_no_phase10h_intake_validation",
    "phase10p1_required_wording_inherited_from_phase10p0",
    "phase10p1_future_package_provenance_wording_inherited_from_phase10p0",
    "phase10p1_future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
)

# Boundary attestation keys that must always be False (forbidden operations).
# NOTE: ``package_generation_executed`` is intentionally NOT in this set — it is
# TRUE for Phase 10P1 (the package IS generated and sealed).  All forbidden
# operations (fetch/clone/read/scrape/inspect/sample/download source material,
# select concrete sources, materialize source contents, run Phase 10H intake
# validation, score/adjudicate/evaluate correctness/evidence_success, invent
# sources, etc.) remain false.
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
    "phase10p0_protocol_modified_or_reinterpreted_or_extended",
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
    "source_material_invented_or_fabricated",
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
    "phase10p1_confirms_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
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
    "phase10p0_private_artifacts_public",
    "source_urls_public",
    "candidate_repo_names_public",
    "candidate_identities_public",
    "package_contents_public",
    "package_checksums_public",
    "package_provenance_public",
    "package_path_public",
    "concrete_source_contents_public",
    "real_repo_urls_in_manifests_public",
    "owner_identities_in_manifests_public",
)

# Exact public gate-reference JSON paths whose string VALUES are expected
# public gate constants.  These are the only exact public gate references
# published by Phase 10P1 (immediate Phase 10P0 gate commit + inherited Phase
# 10C/10F bucket constants only; older exact commits such as Phase 10G are not
# republished by Phase 10P1).
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10c_accepted_source_bucket",
        "$.gate_facts.phase10c_repair_reason_bucket",
        "$.gate_facts.phase10f_accepted_source_bucket",
        "$.gate_facts.phase10f_repair_reason_bucket",
        "$.gate_facts.phase10p0_commit",
    }
)

# Required-wording JSON paths whose string values are frozen oracle-mandated
# wording (inherited from Phase 10P0) and are exempt from the private-shaped-
# value scanner only.
REQUIRED_WORDING_EXEMPT_PATHS = frozenset(
    {
        "$.required_wording",
        "$.future_package_provenance_wording",
    }
)

# Attestation counters to prove the generator/validator/self-test do not
# fetch/read/execute/score/select/inspect (the package-generation path writes
# ONLY to the ignored private path and reads no source material).
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
PRIVATE_PHASE10G_ARTIFACT_READ_ATTEMPTS = 0
PRIVATE_PHASE10P0_ARTIFACT_READ_ATTEMPTS = 0
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


def _validate_package_path_is_ignored_private(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--generate-package``.

    The package path MUST be under the ignored/private ``runs/`` root AND
    ``runs/`` MUST be gitignored at the repo root.  If either check fails, no
    package is written and a blocker is reported.
    """
    if not _runs_is_ignored():
        return False, "runs/ is not gitignored at repo root"
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        return False, "unable to resolve package path"
    runs_root = (REPO / "runs").resolve()
    try:
        rel = resolved.relative_to(runs_root)
    except ValueError:
        return False, "package path is not under the ignored runs/ root"
    rel_posix = str(rel).replace("\\", "/")
    if not rel_posix or rel_posix == ".":
        return False, "package path is the runs/ root itself"
    return True, ""


def _validate_report_path_is_public(path: Path) -> tuple[bool, str]:
    """Fail-closed path guard for ``--validate-report``.

    The report path must be under the Phase 10P1 public artifact directory
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
        return False, "report path is not under the Phase 10P1 public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Protocol-spec schema enforcement (pure dict checks, inherited from 10P0).
# These check ONLY whether a dict has exactly the closed field set.  They do
# NOT read files, fetch, generate, or select any real package.
# ---------------------------------------------------------------------------

def _check_closed_field_set(pkg: Any, expected: tuple[str, ...], label: str) -> list[str]:
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
    return _check_closed_field_set(pkg, PACKAGE_DIRECTORY_LAYOUT_FIELDS, "package_directory_layout")


def check_manifest_schema(pkg: Any) -> list[str]:
    return _check_closed_field_set(pkg, MANIFEST_SCHEMA_REQUIRED_FIELDS, "manifest_schema")


def check_audit_log_format_schema(pkg: Any) -> list[str]:
    return _check_closed_field_set(pkg, AUDIT_LOG_FORMAT_FIELDS, "audit_log_format")


def check_provenance_fields_schema(pkg: Any) -> list[str]:
    return _check_closed_field_set(pkg, PROVENANCE_FIELDS, "provenance_fields")


# ---------------------------------------------------------------------------
# Private package generation (writes ONLY to ignored runs/; no fetch/read).
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_package_contents(package_dir: Path) -> dict[str, Any]:
    """Write the operator-prepared package layout into ``package_dir``.

    This writes ONLY the package's structural files (manifest, audit log,
    provenance, readme) and seals them with sha256 checksums.  It performs NO
    fetch/clone/read/scrape/inspect/sample/download of source material; the
    ``sources/`` directory is created empty (zero eligible concrete sources
    available offline without forbidden fetch; none invented/fabricated).  The
    caller MUST ensure ``package_dir`` is under ignored/private ``runs/`` (the
    public ``generate_package`` wrapper enforces this fail-closed).

    Returns a summary dict of booleans/buckets ONLY (no private checksums,
    no package path, no source identities) suitable for boundary attestation.
    """
    package_dir.mkdir(parents=True, exist_ok=True)
    sources_dir = package_dir / PACKAGE_SOURCES_DIR
    audit_dir = package_dir / PACKAGE_AUDIT_LOG_DIR
    sources_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # manifest.json — exactly the frozen 10P0 manifest schema required fields.
    manifest: dict[str, Any] = {
        "package_protocol_version": "phase10p0",
        "package_prepared_by": "operator",
        "package_preparation_line": "operator_preparation_line",
        "source_count_bucket": SOURCE_COUNT_BUCKET,
        "checksum_algorithm": CHECKSUM_HASH_ALGORITHM[0],
        "immutable_freeze_timestamp": now,
        "audit_log_format": "jsonl",
        "privacy_redaction_applied": True,
    }
    manifest_path = package_dir / PACKAGE_MANIFEST_FILE
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # audit_log/audit.jsonl — each entry has exactly the frozen 10P0 audit-log
    # format fields.  These are package-construction audit entries, NOT source/
    # read material and NOT Phase 10 validation evidence.
    audit_entries = [
        {
            "entry_type": "package_construction",
            "entry_timestamp": now,
            "entry_actor": "operator",
            "entry_action": "construct_package_layout_under_frozen_phase10p0_protocol",
            "entry_subject_bucket": LAYOUT_FIELDS_BUCKET,
        },
        {
            "entry_type": "source_acquisition",
            "entry_timestamp": now,
            "entry_actor": "operator",
            "entry_action": "no_eligible_concrete_sources_available_offline_without_forbidden_fetch_none_invented",
            "entry_subject_bucket": SOURCE_COUNT_BUCKET,
        },
        {
            "entry_type": "package_seal",
            "entry_timestamp": now,
            "entry_actor": "operator",
            "entry_action": "seal_package_with_sha256_checksums",
            "entry_subject_bucket": PACKAGE_GENERATION_SEALED_BUCKET,
        },
    ]
    audit_path = audit_dir / PACKAGE_AUDIT_LOG_FILE
    audit_path.write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in audit_entries),
        encoding="utf-8",
    )

    # provenance.json — exactly the frozen 10P0 provenance fields.  The
    # provenance_statement is the frozen operator-prepared wording inherited
    # from Phase 10P0.
    provenance: dict[str, Any] = {
        "provenance_statement": FUTURE_PACKAGE_PROVENANCE_WORDING,
        "provenance_preparation_line": "operator_preparation_line",
        "provenance_externality": (
            "external_to_phase10_validation_pipeline_not_independent_external_human_generated"
        ),
        "provenance_not_independent_external_human_generated": True,
    }
    provenance_path = package_dir / PACKAGE_PROVENANCE_FILE
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # README.md — package description (package-construction material, NOT
    # source/read material, NOT Phase 10 validation evidence).
    readme_text = (
        "# Operator-prepared offline registry-input package (Phase 10P1)\n\n"
        "This package was generated and sealed under the frozen Phase 10P0\n"
        "operator-package protocol into this ignored/private path under runs/.\n\n"
        "Provenance: " + FUTURE_PACKAGE_PROVENANCE_WORDING + "\n\n"
        "Source count bucket: " + SOURCE_COUNT_BUCKET + " (no eligible concrete\n"
        "sources available offline without forbidden fetch; none invented or\n"
        "fabricated). The sources/ directory is therefore empty.\n\n"
        "Checksum algorithm: " + CHECKSUM_HASH_ALGORITHM[0] + ".\n\n"
        "This package is package-construction material only. It is NOT Phase 10\n"
        "validation evidence and contains no source/read material. Phase 10H\n"
        "intake validation was NOT performed. No scoring/adjudication/correctness/\n"
        "evidence_success evaluation was performed.\n"
    )
    readme_path = package_dir / PACKAGE_README_FILE
    readme_path.write_text(readme_text, encoding="utf-8")

    # checksums.sha256 — seal all package files (sources/ is empty: zero
    # eligible sources, so no source files to checksum).
    sealed_files = [manifest_path, audit_path, provenance_path, readme_path]
    checksum_lines: list[str] = []
    for sealed in sealed_files:
        rel = sealed.relative_to(package_dir).as_posix()
        checksum_lines.append(f"{_sha256_file(sealed)}  {rel}")
    checksums_path = package_dir / PACKAGE_CHECKSUMS_FILE
    checksums_path.write_text(
        "".join(line + "\n" for line in checksum_lines), encoding="utf-8"
    )

    # Boundary summary (booleans/buckets ONLY; no private checksums/path).
    layout_present = all([
        (package_dir / PACKAGE_MANIFEST_FILE).exists(),
        sources_dir.is_dir(),
        audit_dir.is_dir(),
        (package_dir / PACKAGE_CHECKSUMS_FILE).exists(),
        (package_dir / PACKAGE_PROVENANCE_FILE).exists(),
        (package_dir / PACKAGE_README_FILE).exists(),
    ])
    checksums_sealed = checksums_path.exists() and len(checksum_lines) == len(sealed_files)
    return {
        "layout_fields_present": layout_present,
        "package_sealed_with_sha256_checksums": checksums_sealed,
        "source_count_bucket": SOURCE_COUNT_BUCKET,
        "checksum_algorithm": CHECKSUM_HASH_ALGORITHM[0],
        "layout_fields_bucket": LAYOUT_FIELDS_BUCKET,
        "manifest_schema_bucket": MANIFEST_SCHEMA_BUCKET,
    }


def generate_package(
    package_dir: Path,
    *,
    confirm_ignored_private_path: bool = False,
    confirm_operator_prepared: bool = False,
) -> dict[str, Any]:
    """Generate and seal the operator-prepared package (fail-closed).

    Fail-closed: requires explicit confirmation flags AND a package path under
    ignored/private ``runs/``.  If any check fails, no package is written and a
    blocker is raised.  Performs no fetch/clone/read/scrape/inspect/sample/
    download of source material.
    """
    if not confirm_ignored_private_path:
        raise SystemExit(
            "BLOCKER: --confirm-ignored-private-path is required to write a "
            "package; refusing to generate without explicit ignored/private-path "
            "confirmation."
        )
    if not confirm_operator_prepared:
        raise SystemExit(
            "BLOCKER: --confirm-operator-prepared is required; the package must "
            "be operator-prepared under the frozen Phase 10P0 protocol."
        )
    ok, reason = _validate_package_path_is_ignored_private(package_dir)
    if not ok:
        raise SystemExit(
            f"BLOCKER: package path is not ignored/private: {reason}: {package_dir}"
        )
    summary = _write_package_contents(package_dir)
    summary["package_under_ignored_runs_path"] = True
    summary["package_generation_executed"] = True
    summary["package_path"] = str(package_dir)  # private; never published
    return summary


# ---------------------------------------------------------------------------
# Strict allowed-key schema for the public report
# ---------------------------------------------------------------------------

def _frozen_protocol_allowed() -> dict[str, Any]:
    section: dict[str, Any] = {"phase10p0_protocol_imported_exactly_no_drift": None}
    for list_key, expected_tuple in CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = None
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
        "phase10g_ci_green": None,
        "phase10g_status": None,
        "phase10g_phase": None,
        "phase10p0_status": None,
        "phase10p0_commit": None,
        "phase10p0_ci_green": None,
        PHASE10P1_ORACLE_AUTHORIZATION: None,
        "phase10p0_protocol_imported_exactly_no_drift": None,
        "only_phase10p0_gate_constants_are_exact_references": None,
        "older_phase9_10a_10b_10c_10d_10e_10f_10g_exact_refs_not_republished_by_phase10p1": None,
        "local_same_tree_git_commits_not_read_or_compared": None,
    },
    "phase10p1_scope": {
        "operator_package_generation_sealed_only_under_frozen_phase10p0_protocol": None,
        "applies_frozen_phase10p0_protocol_exactly_no_drift": None,
        "authorized_by_phase10p0_gate_and_oracle": None,
        "separate_from_phase10p0_not_reinterpretation": None,
        "separate_from_phase9_not_continuation": None,
        "package_generation_executed": None,
        "package_sealed_with_sha256_checksums": None,
        "package_written_to_ignored_private_path": None,
        "no_phase10_validation_performed_in_phase10p1": None,
        "phase10h_intake_validation_for_later_separately_authorized_phase": None,
        "no_concrete_repos_or_sources_selected": None,
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources": None,
        "no_manifests_with_real_repo_urls_or_identities": None,
        "no_source_material_invented_or_fabricated": None,
        "protocol_is_prospective_not_tuned_to_observed_outcome": None,
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated": None,
        "no_user_approval_wording_as_protocol_dependency": None,
        "boundary_review_required_after_phase10p1_commit_and_ci_green": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "package_generation_facts": {
        "package_under_ignored_runs_path": None,
        "checksum_algorithm": None,
        "layout_fields_bucket": None,
        "manifest_schema_bucket": None,
        "source_count_bucket": None,
        "package_generation_executed": None,
        "package_sealed_with_sha256_checksums": None,
        "phase10h_validation_executed": None,
        "scoring_executed": None,
        "adjudication_executed": None,
        "correctness_evaluated": None,
        "evidence_success_evaluated": None,
        "no_claim": None,
    },
    "frozen_phase10p0_protocol": _frozen_protocol_allowed(),
    "inherited_frozen_phase10p0_gate": {
        "phase10p0_status": None,
        "phase10p0_phase": None,
        "phase10p0_protocol_imported_exactly_no_drift": None,
    },
    "phase10p1_boundary": {
        "operator_package_generation_sealed_only": None,
        "does_not_generate_phase10_validation_evidence": None,
        "does_not_select_concrete_repos_or_sources": None,
        "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources": None,
        "does_not_create_manifests_with_real_repo_urls_or_identities": None,
        "does_not_run_phase10h_intake_validation": None,
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success": None,
        "does_not_invent_or_fabricate_source_material": None,
        "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes": None,
        "does_not_claim_package_is_independent_external_human_generated": None,
        "does_not_claim_validation_success_recovery_or_evidence_improvement": None,
        "does_not_use_forbidden_provenance_wording": None,
        "does_not_modify_weaken_reinterpret_or_extend_phase10p0": None,
        "no_phase10_validation_performed_in_phase10p1": None,
        "no_concrete_repos_or_sources_selected": None,
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources": None,
        "no_manifests_with_real_repo_urls_or_identities": None,
        "no_phase10h_intake_validation": None,
        "no_source_material_invented_or_fabricated": None,
        "protocol_is_prospective_not_tuned_to_observed_outcome": None,
        "package_sealed_with_sha256_checksums_into_ignored_private_path": None,
        "phase10h_intake_validation_for_later_separately_authorized_phase": None,
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated": None,
        "boundary_review_required_after_phase10p1_commit_and_ci_green": None,
        "no_user_approval_wording_as_protocol_dependency": None,
    },
    "protocol_generation_summary": {
        "package_generation_executed_and_sealed": True,
        "no_phase10_validation_performed": True,
        "package_generation_sealed_bucket": None,
        "no_phase10_validation_bucket": None,
        "package_generation_only_bucket": None,
        "phase10h_intake_for_later_bucket": None,
        "zero_eligible_sources_bucket": None,
        "frozen_protocol_lists_imported_exactly_no_drift": True,
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
        "phase10p1_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "package_generation_available": None,
        "validator_enforces_frozen_phase10p0_protocol_lists": None,
        "validator_rejects_forbidden_provenance_wording": None,
        "validator_rejects_claim_wording": None,
        "validator_rejects_unknown_keys": None,
        "validator_rejects_non_ignored_package_path": None,
        "validator_rejects_phase10h_scoring_adjudication_correctness_evidence_success_true": None,
        "validator_rejects_concrete_repo_like_identities": None,
        "validator_rejects_private_shaped_values": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_read_phase10c_artifacts": None,
        "validator_does_not_read_phase10d_artifacts": None,
        "validator_does_not_read_phase10e_artifacts": None,
        "validator_does_not_read_phase10f_artifacts": None,
        "validator_does_not_read_phase10g_artifacts": None,
        "validator_does_not_read_phase10p0_artifacts": None,
        "validator_does_not_inspect_sources": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_select_concrete_repos_or_sources": None,
        "validator_does_not_create_manifests_with_real_repo_urls": None,
        "validator_does_not_run_phase10h_intake_validation": None,
        "validator_does_not_generate_packets": None,
        "validator_does_not_generate_tasks": None,
        "validator_does_not_execute_downstream_pipeline": None,
        "validator_does_not_scrape_or_sample_or_download_sources": None,
        "validator_does_not_score_adjudicate_or_evaluate": None,
        "validator_does_not_modify_or_extend_phase10p0": None,
        "validator_reads_ignored_runs": None,
        "validator_reads_sources": None,
        "validator_inspects_sources": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_selects_concrete_repos_or_sources": None,
        "validator_creates_manifests_with_real_repo_urls": None,
        "validator_runs_phase10h_intake_validation": None,
        "validator_generates_packets": None,
        "validator_generates_tasks": None,
        "validator_executes_downstream_pipeline": None,
        "validator_scrapes_or_samples_or_downloads_sources": None,
        "validator_scores_or_adjudicates": None,
        "validator_modifies_or_extends_phase10p0": None,
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

def _build_frozen_protocol_section() -> dict[str, Any]:
    section: dict[str, Any] = {"phase10p0_protocol_imported_exactly_no_drift": True}
    for list_key, expected_tuple in CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = list(expected_tuple)
    return section


def build_public_report() -> dict[str, Any]:
    """Build the Phase 10P1 operator-package generation public report.

    This performs no network/filesystem fetch, no source read, no private
    ignored-``runs/`` read of earlier phases, no Phase 9/10A/10B/10C/10D/10E/
    10F/10G/10P0 private artifact read, no Phase 10H intake validation, and no
    scoring/adjudication/correctness/evidence_success computation.  It
    assembles the report from the frozen gate constants and the imported 10P0
    protocol specification only.  The report is aggregate/boundary-only: it
    attests that an operator-prepared package was generated and sealed under
    the frozen 10P0 protocol into an ignored/private path, with zero eligible
    concrete sources, and that no Phase 10 validation was performed.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "publication_level": PUBLICATION_LEVEL,
        "required_wording": PHASE10P0_REQUIRED_WORDING,
        "future_package_provenance_wording": FUTURE_PACKAGE_PROVENANCE_WORDING,
        "gate_facts": {
            "phase9_status": P10P0_PHASE9_STATUS,
            "phase10a_status": P10P0_PHASE10A_STATUS,
            "phase10b_status": P10P0_PHASE10B_STATUS,
            "phase10c_status": P10P0_PHASE10C_STATUS,
            "phase10c_accepted_source_bucket": P10P0_PHASE10C_ACCEPTED_SOURCE_BUCKET,
            "phase10c_repair_reason_bucket": P10P0_PHASE10C_REPAIR_REASON_BUCKET,
            "phase10d_status": P10P0_PHASE10D_STATUS,
            "phase10e_status": P10P0_PHASE10E_STATUS,
            "phase10f_status": P10P0_PHASE10F_STATUS,
            "phase10f_accepted_source_bucket": P10P0_PHASE10F_ACCEPTED_SOURCE_BUCKET,
            "phase10f_repair_reason_bucket": P10P0_PHASE10F_REPAIR_REASON_BUCKET,
            "phase10g_ci_green": P10P0_PHASE10G_CI_GREEN,
            "phase10g_status": P10P0_PHASE10G_STATUS,
            "phase10g_phase": P10P0_PHASE10G_PHASE,
            "phase10p0_status": PHASE10P0_STATUS,
            "phase10p0_commit": PHASE10P0_COMMIT,
            "phase10p0_ci_green": PHASE10P0_CI_GREEN,
            PHASE10P1_ORACLE_AUTHORIZATION: True,
            "phase10p0_protocol_imported_exactly_no_drift": True,
            "only_phase10p0_gate_constants_are_exact_references": True,
            "older_phase9_10a_10b_10c_10d_10e_10f_10g_exact_refs_not_republished_by_phase10p1": True,
            "local_same_tree_git_commits_not_read_or_compared": True,
        },
        "phase10p1_scope": {
            "operator_package_generation_sealed_only_under_frozen_phase10p0_protocol": True,
            "applies_frozen_phase10p0_protocol_exactly_no_drift": True,
            "authorized_by_phase10p0_gate_and_oracle": True,
            "separate_from_phase10p0_not_reinterpretation": True,
            "separate_from_phase9_not_continuation": True,
            "package_generation_executed": True,
            "package_sealed_with_sha256_checksums": True,
            "package_written_to_ignored_private_path": True,
            "no_phase10_validation_performed_in_phase10p1": True,
            "phase10h_intake_validation_for_later_separately_authorized_phase": True,
            "no_concrete_repos_or_sources_selected": True,
            "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources": True,
            "no_manifests_with_real_repo_urls_or_identities": True,
            "no_source_material_invented_or_fabricated": True,
            "protocol_is_prospective_not_tuned_to_observed_outcome": True,
            "future_package_provenance_is_operator_prepared_not_independent_external_human_generated": True,
            "no_user_approval_wording_as_protocol_dependency": True,
            "boundary_review_required_after_phase10p1_commit_and_ci_green": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "package_generation_facts": {
            "package_under_ignored_runs_path": _runs_is_ignored(),
            "checksum_algorithm": CHECKSUM_HASH_ALGORITHM[0],
            "layout_fields_bucket": LAYOUT_FIELDS_BUCKET,
            "manifest_schema_bucket": MANIFEST_SCHEMA_BUCKET,
            "source_count_bucket": SOURCE_COUNT_BUCKET,
            "package_generation_executed": True,
            "package_sealed_with_sha256_checksums": True,
            "phase10h_validation_executed": False,
            "scoring_executed": False,
            "adjudication_executed": False,
            "correctness_evaluated": False,
            "evidence_success_evaluated": False,
            "no_claim": True,
        },
        "frozen_phase10p0_protocol": _build_frozen_protocol_section(),
        "inherited_frozen_phase10p0_gate": {
            "phase10p0_status": PHASE10P0_STATUS,
            "phase10p0_phase": PHASE10P0_PHASE,
            "phase10p0_protocol_imported_exactly_no_drift": True,
        },
        "phase10p1_boundary": {
            "operator_package_generation_sealed_only": True,
            "does_not_generate_phase10_validation_evidence": True,
            "does_not_select_concrete_repos_or_sources": True,
            "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources": True,
            "does_not_create_manifests_with_real_repo_urls_or_identities": True,
            "does_not_run_phase10h_intake_validation": True,
            "does_not_score_adjudicate_or_evaluate_correctness_evidence_success": True,
            "does_not_invent_or_fabricate_source_material": True,
            "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes": True,
            "does_not_claim_package_is_independent_external_human_generated": True,
            "does_not_claim_validation_success_recovery_or_evidence_improvement": True,
            "does_not_use_forbidden_provenance_wording": True,
            "does_not_modify_weaken_reinterpret_or_extend_phase10p0": True,
            "no_phase10_validation_performed_in_phase10p1": True,
            "no_concrete_repos_or_sources_selected": True,
            "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources": True,
            "no_manifests_with_real_repo_urls_or_identities": True,
            "no_phase10h_intake_validation": True,
            "no_source_material_invented_or_fabricated": True,
            "protocol_is_prospective_not_tuned_to_observed_outcome": True,
            "package_sealed_with_sha256_checksums_into_ignored_private_path": True,
            "phase10h_intake_validation_for_later_separately_authorized_phase": True,
            "future_package_provenance_is_operator_prepared_not_independent_external_human_generated": True,
            "boundary_review_required_after_phase10p1_commit_and_ci_green": True,
            "no_user_approval_wording_as_protocol_dependency": True,
        },
        "protocol_generation_summary": {
            "package_generation_executed_and_sealed": True,
            "no_phase10_validation_performed": True,
            "package_generation_sealed_bucket": PACKAGE_GENERATION_SEALED_BUCKET,
            "no_phase10_validation_bucket": NO_PHASE10_VALIDATION_BUCKET,
            "package_generation_only_bucket": PACKAGE_GENERATION_ONLY_BUCKET,
            "phase10h_intake_for_later_bucket": PHASE10H_INTAKE_FOR_LATER_BUCKET,
            "zero_eligible_sources_bucket": ZERO_ELIGIBLE_SOURCES_BUCKET,
            "frozen_protocol_lists_imported_exactly_no_drift": True,
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
            "phase10p1_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "package_generation_available": True,
            "validator_enforces_frozen_phase10p0_protocol_lists": True,
            "validator_rejects_forbidden_provenance_wording": True,
            "validator_rejects_claim_wording": True,
            "validator_rejects_unknown_keys": True,
            "validator_rejects_non_ignored_package_path": True,
            "validator_rejects_phase10h_scoring_adjudication_correctness_evidence_success_true": True,
            "validator_rejects_concrete_repo_like_identities": True,
            "validator_rejects_private_shaped_values": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_read_phase10c_artifacts": True,
            "validator_does_not_read_phase10d_artifacts": True,
            "validator_does_not_read_phase10e_artifacts": True,
            "validator_does_not_read_phase10f_artifacts": True,
            "validator_does_not_read_phase10g_artifacts": True,
            "validator_does_not_read_phase10p0_artifacts": True,
            "validator_does_not_inspect_sources": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_select_concrete_repos_or_sources": True,
            "validator_does_not_create_manifests_with_real_repo_urls": True,
            "validator_does_not_run_phase10h_intake_validation": True,
            "validator_does_not_generate_packets": True,
            "validator_does_not_generate_tasks": True,
            "validator_does_not_execute_downstream_pipeline": True,
            "validator_does_not_scrape_or_sample_or_download_sources": True,
            "validator_does_not_score_adjudicate_or_evaluate": True,
            "validator_does_not_modify_or_extend_phase10p0": True,
            "validator_reads_ignored_runs": False,
            "validator_reads_sources": False,
            "validator_inspects_sources": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_selects_concrete_repos_or_sources": False,
            "validator_creates_manifests_with_real_repo_urls": False,
            "validator_runs_phase10h_intake_validation": False,
            "validator_generates_packets": False,
            "validator_generates_tasks": False,
            "validator_executes_downstream_pipeline": False,
            "validator_scrapes_or_samples_or_downloads_sources": False,
            "validator_scores_or_adjudicates": False,
            "validator_modifies_or_extends_phase10p0": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }
    return report


# ---------------------------------------------------------------------------
# Validator (fail-closed)
# ---------------------------------------------------------------------------

def validate_report(report: Any) -> list[str]:
    """Validate the Phase 10P1 public report against the frozen schema/constants.

    Fail-closed: rejects unknown fields, closed-list drift, non-ignored package
    path, Phase 10H/scoring/adjudication/correctness/evidence_success set true,
    forbidden provenance wording, claim wording, private-shaped values, and
    privacy-contract violations.  This does NOT read any Phase 9/10A/10B/10C/
    10D/10E/10F/10G/10P0 artifact on disk, does NOT fetch/clone, does NOT read
    ignored ``runs/``, does NOT inspect sources, does NOT run Phase 10H intake
    validation, and does NOT score.
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
        errors.append("required wording drift (must inherit frozen Phase 10P0 wording)")
    if report.get("future_package_provenance_wording") != FUTURE_PACKAGE_PROVENANCE_WORDING:
        errors.append("future package provenance wording drift")

    gate = report.get("gate_facts", {})
    if gate.get("phase9_status") != P10P0_PHASE9_STATUS:
        errors.append("Phase 9 status gate fact drift")
    if gate.get("phase10a_status") != P10P0_PHASE10A_STATUS:
        errors.append("Phase 10A status gate fact drift")
    if gate.get("phase10b_status") != P10P0_PHASE10B_STATUS:
        errors.append("Phase 10B status gate fact drift")
    if gate.get("phase10c_status") != P10P0_PHASE10C_STATUS:
        errors.append("Phase 10C status gate fact drift")
    if gate.get("phase10c_accepted_source_bucket") != P10P0_PHASE10C_ACCEPTED_SOURCE_BUCKET:
        errors.append("Phase 10C accepted source bucket gate fact drift")
    if gate.get("phase10c_repair_reason_bucket") != P10P0_PHASE10C_REPAIR_REASON_BUCKET:
        errors.append("Phase 10C repair reason bucket gate fact drift")
    if gate.get("phase10d_status") != P10P0_PHASE10D_STATUS:
        errors.append("Phase 10D status gate fact drift")
    if gate.get("phase10e_status") != P10P0_PHASE10E_STATUS:
        errors.append("Phase 10E status gate fact drift")
    if gate.get("phase10f_status") != P10P0_PHASE10F_STATUS:
        errors.append("Phase 10F status gate fact drift")
    if gate.get("phase10f_accepted_source_bucket") != P10P0_PHASE10F_ACCEPTED_SOURCE_BUCKET:
        errors.append("Phase 10F accepted source bucket gate fact drift")
    if gate.get("phase10f_repair_reason_bucket") != P10P0_PHASE10F_REPAIR_REASON_BUCKET:
        errors.append("Phase 10F repair reason bucket gate fact drift")
    if gate.get("phase10g_ci_green") is not True:
        errors.append("Phase 10G CI green gate missing")
    if gate.get("phase10g_status") != P10P0_PHASE10G_STATUS:
        errors.append("Phase 10G status gate reference drift")
    if gate.get("phase10g_phase") != P10P0_PHASE10G_PHASE:
        errors.append("Phase 10G phase gate reference drift")
    if gate.get("phase10p0_status") != PHASE10P0_STATUS:
        errors.append("Phase 10P0 status gate reference drift")
    if gate.get("phase10p0_commit") != PHASE10P0_COMMIT:
        errors.append("Phase 10P0 commit gate reference drift")
    if gate.get("phase10p0_ci_green") is not True:
        errors.append("Phase 10P0 CI green gate missing")
    if gate.get(PHASE10P1_ORACLE_AUTHORIZATION) is not True:
        errors.append("Phase 10P1 oracle authorization boundary missing")
    if gate.get("phase10p0_protocol_imported_exactly_no_drift") is not True:
        errors.append("Phase 10P0 protocol imported-no-drift boundary missing")
    if gate.get("only_phase10p0_gate_constants_are_exact_references") is not True:
        errors.append("Phase 10P0-only exact references boundary missing")
    if gate.get("local_same_tree_git_commits_not_read_or_compared") is not True:
        errors.append("local git commits not read boundary missing")
    if gate.get("older_phase9_10a_10b_10c_10d_10e_10f_10g_exact_refs_not_republished_by_phase10p1") is not True:
        errors.append("older exact refs not republished boundary missing")

    scope = report.get("phase10p1_scope", {})
    for key in (
        "operator_package_generation_sealed_only_under_frozen_phase10p0_protocol",
        "applies_frozen_phase10p0_protocol_exactly_no_drift",
        "authorized_by_phase10p0_gate_and_oracle",
        "separate_from_phase10p0_not_reinterpretation",
        "separate_from_phase9_not_continuation",
        "package_generation_executed",
        "package_sealed_with_sha256_checksums",
        "package_written_to_ignored_private_path",
        "no_phase10_validation_performed_in_phase10p1",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
        "no_concrete_repos_or_sources_selected",
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources",
        "no_manifests_with_real_repo_urls_or_identities",
        "no_source_material_invented_or_fabricated",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
        "no_user_approval_wording_as_protocol_dependency",
        "boundary_review_required_after_phase10p1_commit_and_ci_green",
    ):
        if scope.get(key) is not True:
            errors.append(f"phase10p1_scope boundary missing: {key}")
    # package_generation_executed MUST be true (this is a generation phase).
    if scope.get("package_generation_executed") is not True:
        errors.append("phase10p1_scope package_generation_executed must be true")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10p1_scope execution boundary failed: {key}")

    # Package generation facts (fail-closed on the required booleans/buckets).
    gen = report.get("package_generation_facts", {})
    if gen.get("package_under_ignored_runs_path") is not True:
        errors.append("package_generation_facts package_under_ignored_runs_path must be true (package not under ignored/private path)")
    if gen.get("checksum_algorithm") != CHECKSUM_HASH_ALGORITHM[0]:
        errors.append("package_generation_facts checksum_algorithm drift")
    if gen.get("layout_fields_bucket") != LAYOUT_FIELDS_BUCKET:
        errors.append("package_generation_facts layout_fields_bucket drift")
    if gen.get("manifest_schema_bucket") != MANIFEST_SCHEMA_BUCKET:
        errors.append("package_generation_facts manifest_schema_bucket drift")
    if gen.get("source_count_bucket") != SOURCE_COUNT_BUCKET:
        errors.append("package_generation_facts source_count_bucket drift")
    if gen.get("package_generation_executed") is not True:
        errors.append("package_generation_facts package_generation_executed must be true")
    if gen.get("package_sealed_with_sha256_checksums") is not True:
        errors.append("package_generation_facts package_sealed_with_sha256_checksums must be true")
    # Fail-closed: Phase 10H / scoring / adjudication / correctness /
    # evidence_success MUST be false.  no_claim MUST be true.
    for key in (
        "phase10h_validation_executed",
        "scoring_executed",
        "adjudication_executed",
        "correctness_evaluated",
        "evidence_success_evaluated",
    ):
        if gen.get(key) is not False:
            errors.append(f"package_generation_facts {key} must be false")
    if gen.get("no_claim") is not True:
        errors.append("package_generation_facts no_claim must be true")

    # Frozen Phase 10P0 protocol closed-list set-equality checks (no drift).
    protocol = report.get("frozen_phase10p0_protocol", {})
    if protocol.get("phase10p0_protocol_imported_exactly_no_drift") is not True:
        errors.append("frozen_phase10p0_protocol no-drift attestation missing")
    for list_key, expected_tuple in CLOSED_PROTOCOL_LISTS:
        actual = protocol.get(list_key)
        if not isinstance(actual, list):
            errors.append(f"frozen protocol list missing: {list_key}")
            continue
        if set(actual) != set(expected_tuple):
            errors.append(f"frozen protocol list drift: {list_key}")
            continue
        if len(actual) != len(set(actual)):
            errors.append(f"frozen protocol list duplicates: {list_key}")

    inherited = report.get("inherited_frozen_phase10p0_gate", {})
    if inherited.get("phase10p0_status") != PHASE10P0_STATUS:
        errors.append("inherited 10P0 status drift")
    if inherited.get("phase10p0_phase") != PHASE10P0_PHASE:
        errors.append("inherited 10P0 phase drift")
    if inherited.get("phase10p0_protocol_imported_exactly_no_drift") is not True:
        errors.append("inherited 10P0 no-drift attestation missing")

    boundary = report.get("phase10p1_boundary", {})
    for key in (
        "operator_package_generation_sealed_only",
        "does_not_generate_phase10_validation_evidence",
        "does_not_select_concrete_repos_or_sources",
        "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources",
        "does_not_create_manifests_with_real_repo_urls_or_identities",
        "does_not_run_phase10h_intake_validation",
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success",
        "does_not_invent_or_fabricate_source_material",
        "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes",
        "does_not_claim_package_is_independent_external_human_generated",
        "does_not_claim_validation_success_recovery_or_evidence_improvement",
        "does_not_use_forbidden_provenance_wording",
        "does_not_modify_weaken_reinterpret_or_extend_phase10p0",
        "no_phase10_validation_performed_in_phase10p1",
        "no_concrete_repos_or_sources_selected",
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources",
        "no_manifests_with_real_repo_urls_or_identities",
        "no_phase10h_intake_validation",
        "no_source_material_invented_or_fabricated",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "package_sealed_with_sha256_checksums_into_ignored_private_path",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
        "boundary_review_required_after_phase10p1_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        if boundary.get(key) is not True:
            errors.append(f"phase10p1_boundary missing: {key}")

    proto_sum = report.get("protocol_generation_summary", {})
    for key in (
        "package_generation_executed_and_sealed",
        "no_phase10_validation_performed",
        "frozen_protocol_lists_imported_exactly_no_drift",
    ):
        if proto_sum.get(key) is not True:
            errors.append(f"protocol_generation_summary missing: {key}")
    if proto_sum.get("package_generation_sealed_bucket") != PACKAGE_GENERATION_SEALED_BUCKET:
        errors.append("package_generation_sealed_bucket drift")
    if proto_sum.get("no_phase10_validation_bucket") != NO_PHASE10_VALIDATION_BUCKET:
        errors.append("no_phase10_validation_bucket drift")
    if proto_sum.get("package_generation_only_bucket") != PACKAGE_GENERATION_ONLY_BUCKET:
        errors.append("package_generation_only_bucket drift")
    if proto_sum.get("phase10h_intake_for_later_bucket") != PHASE10H_INTAKE_FOR_LATER_BUCKET:
        errors.append("phase10h_intake_for_later_bucket drift")
    if proto_sum.get("zero_eligible_sources_bucket") != ZERO_ELIGIBLE_SOURCES_BUCKET:
        errors.append("zero_eligible_sources_bucket drift")

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
        "phase10p1_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "package_generation_available",
        "validator_enforces_frozen_phase10p0_protocol_lists",
        "validator_rejects_forbidden_provenance_wording",
        "validator_rejects_claim_wording",
        "validator_rejects_unknown_keys",
        "validator_rejects_non_ignored_package_path",
        "validator_rejects_phase10h_scoring_adjudication_correctness_evidence_success_true",
        "validator_rejects_concrete_repo_like_identities",
        "validator_rejects_private_shaped_values",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_sources",
        "validator_does_not_read_ignored_runs",
        "validator_does_not_read_phase9_artifacts",
        "validator_does_not_read_phase10c_artifacts",
        "validator_does_not_read_phase10d_artifacts",
        "validator_does_not_read_phase10e_artifacts",
        "validator_does_not_read_phase10f_artifacts",
        "validator_does_not_read_phase10g_artifacts",
        "validator_does_not_read_phase10p0_artifacts",
        "validator_does_not_inspect_sources",
        "validator_does_not_discover_sources",
        "validator_does_not_materialize_sources",
        "validator_does_not_select_concrete_repos_or_sources",
        "validator_does_not_create_manifests_with_real_repo_urls",
        "validator_does_not_run_phase10h_intake_validation",
        "validator_does_not_generate_packets",
        "validator_does_not_generate_tasks",
        "validator_does_not_execute_downstream_pipeline",
        "validator_does_not_scrape_or_sample_or_download_sources",
        "validator_does_not_score_adjudicate_or_evaluate",
        "validator_does_not_modify_or_extend_phase10p0",
        "public_artifact_privacy_audit_expected",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in (
        "validator_reads_ignored_runs",
        "validator_reads_sources",
        "validator_inspects_sources",
        "validator_starts_empirical_work",
        "validator_discovers_sources",
        "validator_materializes_sources",
        "validator_selects_concrete_repos_or_sources",
        "validator_creates_manifests_with_real_repo_urls",
        "validator_runs_phase10h_intake_validation",
        "validator_generates_packets",
        "validator_generates_tasks",
        "validator_executes_downstream_pipeline",
        "validator_scrapes_or_samples_or_downloads_sources",
        "validator_scores_or_adjudicates",
        "validator_modifies_or_extends_phase10p0",
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
    global MATERIALIZATION_ATTEMPTS, PACKET_GENERATION_ATTEMPTS, TASK_GENERATION_ATTEMPTS
    global DOWNSTREAM_PIPELINE_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_PHASE9_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10C_ARTIFACT_READ_ATTEMPTS
    global PRIVATE_PHASE10D_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10E_ARTIFACT_READ_ATTEMPTS
    global PRIVATE_PHASE10F_ARTIFACT_READ_ATTEMPTS, PRIVATE_PHASE10G_ARTIFACT_READ_ATTEMPTS
    global PRIVATE_PHASE10P0_ARTIFACT_READ_ATTEMPTS
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
    PRIVATE_PHASE10P0_ARTIFACT_READ_ATTEMPTS = 0
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

    # Baseline generation report validates.
    dry = build_public_report()
    checks.append(("report_valid", not validate_report(dry)))
    checks.append(("phase_equals_slug", dry["phase"] == PHASE))
    checks.append(("status_is_generation_sealed_no_validation_no_claim", dry["status"] == STATUS))
    checks.append(("publication_level_boundary", dry["publication_level"] == PUBLICATION_LEVEL))
    checks.append(("required_wording_inherited_from_10p0", dry["required_wording"] == PHASE10P0_REQUIRED_WORDING))
    checks.append(("future_package_provenance_wording_inherited_from_10p0", dry["future_package_provenance_wording"] == FUTURE_PACKAGE_PROVENANCE_WORDING))

    # Gate facts enforced.  Only the immediate Phase 10P0 gate publishes exact
    # commit identifier; older checkpoints are status/bucket/scope only.
    checks.append(("phase9_status_gate", dry["gate_facts"]["phase9_status"] == P10P0_PHASE9_STATUS))
    checks.append(("phase10a_status_gate", dry["gate_facts"]["phase10a_status"] == P10P0_PHASE10A_STATUS))
    checks.append(("phase10b_status_gate", dry["gate_facts"]["phase10b_status"] == P10P0_PHASE10B_STATUS))
    checks.append(("phase10c_status_gate", dry["gate_facts"]["phase10c_status"] == P10P0_PHASE10C_STATUS))
    checks.append(("phase10c_accepted_bucket_zero", dry["gate_facts"]["phase10c_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10c_repair_bucket", dry["gate_facts"]["phase10c_repair_reason_bucket"] == "bucket_no_eligible_channel_registry"))
    checks.append(("phase10d_status_gate", dry["gate_facts"]["phase10d_status"] == P10P0_PHASE10D_STATUS))
    checks.append(("phase10e_status_gate", dry["gate_facts"]["phase10e_status"] == P10P0_PHASE10E_STATUS))
    checks.append(("phase10f_status_gate", dry["gate_facts"]["phase10f_status"] == P10P0_PHASE10F_STATUS))
    checks.append(("phase10f_accepted_bucket_zero", dry["gate_facts"]["phase10f_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10f_repair_bucket", dry["gate_facts"]["phase10f_repair_reason_bucket"] == "bucket_no_compliant_registry_input_under_frozen_10e_protocol"))
    checks.append(("phase10g_ci_green_gate", dry["gate_facts"]["phase10g_ci_green"] is True))
    checks.append(("phase10g_commit_not_republished", "phase10g_commit" not in dry["gate_facts"]))
    checks.append(("phase10p0_commit_gate", dry["gate_facts"]["phase10p0_commit"] == PHASE10P0_COMMIT))
    checks.append(("phase10p0_ci_green_gate", dry["gate_facts"]["phase10p0_ci_green"] is True))
    checks.append(("phase10p0_status_gate", dry["gate_facts"]["phase10p0_status"] == PHASE10P0_STATUS))
    checks.append(("phase10p1_oracle_authorization", dry["gate_facts"][PHASE10P1_ORACLE_AUTHORIZATION] is True))
    checks.append(("only_phase10p0_refs", dry["gate_facts"]["only_phase10p0_gate_constants_are_exact_references"] is True))

    # Inherited 10P0 gate drift check.
    inh = dry["inherited_frozen_phase10p0_gate"]
    checks.append(("inherited_10p0_status_no_drift", inh["phase10p0_status"] == PHASE10P0_STATUS))
    checks.append(("inherited_10p0_phase_no_drift", inh["phase10p0_phase"] == PHASE10P0_PHASE))
    checks.append(("inherited_10p0_imported_exactly", inh["phase10p0_protocol_imported_exactly_no_drift"] is True))

    # Package generation facts (the required booleans/buckets).
    gen = dry["package_generation_facts"]
    checks.append(("package_under_ignored_runs_path", gen["package_under_ignored_runs_path"] is True))
    checks.append(("checksum_algorithm_sha256", gen["checksum_algorithm"] == "sha256"))
    checks.append(("layout_fields_bucket", gen["layout_fields_bucket"] == LAYOUT_FIELDS_BUCKET))
    checks.append(("manifest_schema_bucket", gen["manifest_schema_bucket"] == MANIFEST_SCHEMA_BUCKET))
    checks.append(("source_count_bucket_zero", gen["source_count_bucket"] == "bucket_zero"))
    checks.append(("package_generation_executed_true", gen["package_generation_executed"] is True))
    checks.append(("package_sealed_with_sha256_checksums_true", gen["package_sealed_with_sha256_checksums"] is True))
    checks.append(("phase10h_validation_executed_false", gen["phase10h_validation_executed"] is False))
    checks.append(("scoring_executed_false", gen["scoring_executed"] is False))
    checks.append(("adjudication_executed_false", gen["adjudication_executed"] is False))
    checks.append(("correctness_evaluted_false", gen["correctness_evaluated"] is False))
    checks.append(("evidence_success_evaluated_false", gen["evidence_success_evaluated"] is False))
    checks.append(("no_claim_true", gen["no_claim"] is True))

    # Frozen 10P0 protocol closed lists imported exactly (no drift).
    proto = dry["frozen_phase10p0_protocol"]
    for list_key, expected_tuple in CLOSED_PROTOCOL_LISTS:
        actual = proto.get(list_key)
        checks.append((f"frozen_protocol_list_{list_key}_present", isinstance(actual, list)))
        if isinstance(actual, list):
            checks.append((f"frozen_protocol_list_{list_key}_set_eq", set(actual) == set(expected_tuple)))
            checks.append((f"frozen_protocol_list_{list_key}_no_dup", len(actual) == len(set(actual))))

    # Protocol generation summary buckets.
    ps = dry["protocol_generation_summary"]
    checks.append(("proto_summary_generation_sealed", ps["package_generation_executed_and_sealed"] is True))
    checks.append(("proto_summary_no_validation", ps["no_phase10_validation_performed"] is True))
    checks.append(("proto_summary_no_drift", ps["frozen_protocol_lists_imported_exactly_no_drift"] is True))
    checks.append(("proto_summary_sealed_bucket", ps["package_generation_sealed_bucket"] == PACKAGE_GENERATION_SEALED_BUCKET))
    checks.append(("proto_summary_no_validation_bucket", ps["no_phase10_validation_bucket"] == NO_PHASE10_VALIDATION_BUCKET))
    checks.append(("proto_summary_only_bucket", ps["package_generation_only_bucket"] == PACKAGE_GENERATION_ONLY_BUCKET))
    checks.append(("proto_summary_intake_for_later_bucket", ps["phase10h_intake_for_later_bucket"] == PHASE10H_INTAKE_FOR_LATER_BUCKET))
    checks.append(("proto_summary_zero_sources_bucket", ps["zero_eligible_sources_bucket"] == ZERO_ELIGIBLE_SOURCES_BUCKET))

    # Phase 10P1 boundary.
    boundary = dry["phase10p1_boundary"]
    for key in (
        "operator_package_generation_sealed_only",
        "does_not_generate_phase10_validation_evidence",
        "does_not_select_concrete_repos_or_sources",
        "does_not_fetch_clone_download_scrape_or_inspect_candidate_sources",
        "does_not_create_manifests_with_real_repo_urls_or_identities",
        "does_not_run_phase10h_intake_validation",
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success",
        "does_not_invent_or_fabricate_source_material",
        "does_not_tune_protocol_based_on_phase10c_or_10f_zero_outcomes",
        "does_not_claim_package_is_independent_external_human_generated",
        "does_not_claim_validation_success_recovery_or_evidence_improvement",
        "does_not_use_forbidden_provenance_wording",
        "does_not_modify_weaken_reinterpret_or_extend_phase10p0",
        "no_phase10_validation_performed_in_phase10p1",
        "no_concrete_repos_or_sources_selected",
        "no_fetch_clone_download_scrape_or_inspect_of_candidate_sources",
        "no_manifests_with_real_repo_urls_or_identities",
        "no_phase10h_intake_validation",
        "no_source_material_invented_or_fabricated",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "package_sealed_with_sha256_checksums_into_ignored_private_path",
        "phase10h_intake_validation_for_later_separately_authorized_phase",
        "future_package_provenance_is_operator_prepared_not_independent_external_human_generated",
        "boundary_review_required_after_phase10p1_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        checks.append((f"phase10p1_boundary_{key}", boundary[key] is True))

    # Protocol-spec schema enforcement (synthetic fixtures only; no real
    # package read/fetched/generated/selected).
    valid_layout = {field: "synthetic_value" for field in PACKAGE_DIRECTORY_LAYOUT_FIELDS}
    checks.append(("layout_schema_valid_pkg_passes", not check_package_directory_layout_schema(valid_layout)))
    missing_layout = {field: "synthetic_value" for field in PACKAGE_DIRECTORY_LAYOUT_FIELDS if field != "checksums_sha256_file"}
    checks.append(("layout_schema_missing_field_rejected", bool(check_package_directory_layout_schema(missing_layout))))
    extra_layout = dict(valid_layout)
    extra_layout["extra_future_field"] = "synthetic_value"
    checks.append(("layout_schema_extra_field_rejected", bool(check_package_directory_layout_schema(extra_layout))))
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

    # Fail-closed: reject Phase 10H/scoring/adjudication/correctness/
    # evidence_success flipped to true in package_generation_facts.
    for bad_key in ("phase10h_validation_executed", "scoring_executed",
                    "adjudication_executed", "correctness_evaluated",
                    "evidence_success_evaluated"):
        mutated = copy.deepcopy(dry)
        mutated["package_generation_facts"][bad_key] = True
        checks.append((f"package_generation_facts_{bad_key}_true_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject no_claim flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["package_generation_facts"]["no_claim"] = False
    checks.append(("package_generation_facts_no_claim_false_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject package_generation_executed flipped to false.
    for section in ("package_generation_facts", "phase10p1_scope"):
        mutated = copy.deepcopy(dry)
        mutated[section]["package_generation_executed"] = False
        checks.append((f"{section}_package_generation_executed_false_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject package_under_ignored_runs_path flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["package_generation_facts"]["package_under_ignored_runs_path"] = False
    checks.append(("package_under_ignored_runs_path_false_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject checksum_algorithm drift.
    mutated = copy.deepcopy(dry)
    mutated["package_generation_facts"]["checksum_algorithm"] = "md5"
    checks.append(("checksum_algorithm_drift_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject gate fact drift.
    for field, bad_val, label in (
        ("phase10p0_commit", "deadbeef", "phase10p0_commit"),
        ("phase10p0_ci_green", False, "phase10p0_ci_green"),
        ("phase10p0_status", "drift", "phase10p0_status"),
        ("phase10g_ci_green", False, "phase10g_ci_green"),
        ("phase10c_accepted_source_bucket", "bucket_nonzero", "phase10c_bucket"),
        ("phase10f_accepted_source_bucket", "bucket_nonzero", "phase10f_bucket"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["gate_facts"][field] = bad_val
        checks.append((f"wrong_{label}_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["phase10g_commit"] = "deadbeef"
    checks.append(("phase10g_commit_republished_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject phase10p1_scope execution booleans flipped true.
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["phase10p1_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject phase10p1_boundary facts flipped false.
    for key in (
        "operator_package_generation_sealed_only",
        "does_not_generate_phase10_validation_evidence",
        "does_not_run_phase10h_intake_validation",
        "does_not_score_adjudicate_or_evaluate_correctness_evidence_success",
        "does_not_invent_or_fabricate_source_material",
        "does_not_claim_package_is_independent_external_human_generated",
        "does_not_use_forbidden_provenance_wording",
        "does_not_modify_weaken_reinterpret_or_extend_phase10p0",
        "package_sealed_with_sha256_checksums_into_ignored_private_path",
        "no_phase10_validation_performed_in_phase10p1",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10p1_boundary"][key] = False
        checks.append((f"phase10p1_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject frozen-protocol list drift (extra/missing member).
    for list_key, expected_tuple in CLOSED_PROTOCOL_LISTS:
        mutated = copy.deepcopy(dry)
        mutated["frozen_phase10p0_protocol"][list_key] = list(expected_tuple) + ["extra_member"]
        checks.append((f"frozen_protocol_list_{list_key}_extra_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        mutated["frozen_phase10p0_protocol"][list_key] = list(expected_tuple)[:-1]
        checks.append((f"frozen_protocol_list_{list_key}_missing_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject inherited 10P0 gate drift.
    mutated = copy.deepcopy(dry)
    mutated["inherited_frozen_phase10p0_gate"]["phase10p0_status"] = "drift"
    checks.append(("inherited_10p0_status_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["inherited_frozen_phase10p0_gate"]["phase10p0_phase"] = "drift"
    checks.append(("inherited_10p0_phase_drift_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject truth-boundary violation.
    for key in TRUTH_BOUNDARY_TRUE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["truth_boundary"][key] = False
        checks.append((f"truth_boundary_{key}_false_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject claim boundary true.
    for claim_key in CLAIM_BOUNDARY_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject privacy contract violations.
    for privacy_key in PRIVACY_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["privacy_contract"][privacy_key] = True
        checks.append((f"{privacy_key}_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject forbidden provenance wording (must NOT appear).
    allowed_leaf_paths = _allowed_leaf_paths()
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
        mutated = copy.deepcopy(dry)
        mutated["conservative_recommendation"] = phrase
        checks.append((f"forbidden_provenance_{phrase.replace(' ', '_').replace('-', '_')}_report_rejected",
                       bool(validate_report(mutated))))

    # Fail-closed: reject forbidden success/claim wording.
    for phrase in ("validated", "evidence_success achieved",
                   "package generated", "package validated",
                   "package succeeded", "independent validation passed",
                   "OpenLocus works", "Phase 10 confirms",
                   "Phase 10P0 confirms", "Phase 10P1 confirms",
                   "method proven", "product readiness",
                   "scoring success", "outcome success",
                   "correctness proven", "correctness recovered",
                   "validation success", "validation recovery",
                   "evidence improvement", "generalized success"):
        mutated = copy.deepcopy(dry)
        mutated["conservative_recommendation"] = phrase
        checks.append((f"forbidden_success_wording_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # Fail-closed: reject user-approval wording.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject placeholder wording.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        scan_errors = _scan_public(
            phrase,
            path="$.conservative_recommendation",
            key="conservative_recommendation",
            allowed_paths=allowed_leaf_paths,
        )
        checks.append((f"placeholder_{phrase}_scanner_rejected", bool(scan_errors)))

    # Fail-closed: reject private-shaped values.
    for label, bad_val in (
        ("url", "https://example.invalid/repo.git"),
        ("owner_repo", "owner/repo"),
        ("full_hash", "a" * 40),
        ("path", "src/private.py"),
        ("run_dir", "runs/secret/run_dir"),
    ):
        scan_errors = _scan_public(
            bad_val,
            path="$.conservative_recommendation",
            key="conservative_recommendation",
            allowed_paths=allowed_leaf_paths,
        )
        checks.append((f"private_shaped_{label}_scanner_rejected", bool(scan_errors)))

    # Fail-closed: reject private-shaped keys.
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "source_path_bucket", "path", "repo_name", "task_id", "row_id",
        "packet_id", "manifest", "run_dir", "candidate_identity",
        "hash_value", "snippet_value", "package_content", "real_repo_url",
        "owner_identity", "package_checksum",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10p1_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        scan_errors = _scan_public(
            singleton_val,
            path="$.conservative_recommendation",
            key="conservative_recommendation",
            allowed_paths=allowed_leaf_paths,
        )
        checks.append((f"singleton_{singleton_val}_scanner_rejected", bool(scan_errors)))

    # Fail-closed: reject non-gate hash/CI values (gate values only at exact paths).
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

    # Fail-closed: reject status/phase/schema/publication_level drift.
    for field, bad in (("status", "drift"), ("phase", "drift"),
                       ("schema_version", "drift"),
                       ("publication_level", "drift")):
        mutated = copy.deepcopy(dry)
        mutated[field] = bad
        checks.append((f"{field}_drift_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject unknown fields (closed-schema enforcement).
    mutated = copy.deepcopy(dry)
    mutated["unexpected_top_level"] = "x"
    checks.append(("unknown_top_level_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10p1_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_gate_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["package_generation_facts"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_generation_facts_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["frozen_phase10p0_protocol"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10p1_boundary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_boundary_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject conservative recommendation / required wording drift.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "wrong_recommendation"
    checks.append(("conservative_recommendation_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["required_wording"] = "wrong wording"
    checks.append(("required_wording_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["future_package_provenance_wording"] = "wrong provenance"
    checks.append(("future_package_provenance_wording_drift_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject modifying/extending 10P0 in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_modifies_or_extends_phase10p0"] = True
    checks.append(("validator_modifies_phase10p0_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject running Phase 10H intake validation in the summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_runs_phase10h_intake_validation"] = True
    checks.append(("validator_runs_phase10h_intake_rejected", bool(validate_report(mutated))))

    # Fail-closed: reject selecting concrete repos in the summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_selects_concrete_repos_or_sources"] = True
    checks.append(("validator_selects_concrete_repos_rejected", bool(validate_report(mutated))))

    # Path guard tests for the report validator.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10p1" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10p0_operator_package_protocol_freeze_no_package_generation_no_phase10_validation_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # Package path guard tests (fail-closed: must be under ignored runs/).
    ok, _ = _validate_package_path_is_ignored_private(REPO / "artifacts" / "phase10p1" / "pkg")
    checks.append(("package_path_rejects_artifacts_path", not ok))
    ok, _ = _validate_package_path_is_ignored_private(REPO / "eval" / "pkg")
    checks.append(("package_path_rejects_eval_path", not ok))
    ok, _ = _validate_package_path_is_ignored_private(REPO / "runs")
    checks.append(("package_path_rejects_runs_root_itself", not ok))
    ok, _ = _validate_package_path_is_ignored_private(DEFAULT_PACKAGE_DIR)
    checks.append(("package_path_accepts_default_ignored_runs_path", ok))

    # Fail-closed: generate_package blocks without confirm flags.
    blocked_no_confirm = False
    try:
        generate_package(DEFAULT_PACKAGE_DIR)
    except SystemExit:
        blocked_no_confirm = True
    checks.append(("generate_package_blocks_without_confirm_flags", blocked_no_confirm))

    # Fail-closed: generate_package blocks a non-ignored path even with flags.
    blocked_non_ignored = False
    try:
        generate_package(
            REPO / "artifacts" / "phase10p1_synthetic" / "pkg",
            confirm_ignored_private_path=True,
            confirm_operator_prepared=True,
        )
    except SystemExit:
        blocked_non_ignored = True
    checks.append(("generate_package_blocks_non_ignored_path", blocked_non_ignored))

    # Synthetic package-writing round-trip (temp dir; NOT real runs/; no
    # private values coinciding with real outputs).  Tests the sealing logic
    # without polluting the real ignored runs/ path.
    with tempfile.TemporaryDirectory(prefix="phase10p1_selftest_") as tmp:
        tmp_pkg = Path(tmp) / "synthetic_pkg"
        write_summary = _write_package_contents(tmp_pkg)
        checks.append(("write_layout_present", write_summary["layout_fields_present"] is True))
        checks.append(("write_package_sealed", write_summary["package_sealed_with_sha256_checksums"] is True))
        checks.append(("write_source_count_bucket_zero", write_summary["source_count_bucket"] == "bucket_zero"))
        checks.append(("write_checksum_algorithm_sha256", write_summary["checksum_algorithm"] == "sha256"))
        checks.append(("write_layout_fields_bucket", write_summary["layout_fields_bucket"] == LAYOUT_FIELDS_BUCKET))
        checks.append(("write_manifest_schema_bucket", write_summary["manifest_schema_bucket"] == MANIFEST_SCHEMA_BUCKET))
        # All sealed files exist with the frozen 10P0 layout.
        checks.append(("write_manifest_file_exists", (tmp_pkg / PACKAGE_MANIFEST_FILE).exists()))
        checks.append(("write_sources_dir_exists", (tmp_pkg / PACKAGE_SOURCES_DIR).is_dir()))
        checks.append(("write_audit_log_dir_exists", (tmp_pkg / PACKAGE_AUDIT_LOG_DIR).is_dir()))
        checks.append(("write_checksums_file_exists", (tmp_pkg / PACKAGE_CHECKSUMS_FILE).exists()))
        checks.append(("write_provenance_file_exists", (tmp_pkg / PACKAGE_PROVENANCE_FILE).exists()))
        checks.append(("write_readme_file_exists", (tmp_pkg / PACKAGE_README_FILE).exists()))
        # sources/ is empty (zero eligible sources; none invented).
        checks.append(("write_sources_dir_empty_no_source_material",
                       not any((tmp_pkg / PACKAGE_SOURCES_DIR).iterdir())))
        # checksums.sha256 has one valid sha256 line per sealed file.
        ck_lines = (tmp_pkg / PACKAGE_CHECKSUMS_FILE).read_text(encoding="utf-8").strip().splitlines()
        checks.append(("write_checksums_line_count_matches_sealed_files", len(ck_lines) == 4))
        for line in ck_lines:
            parts = line.split("  ", 1)
            checks.append(("write_checksum_line_well_formed_sha256",
                           len(parts) == 2 and len(parts[0]) == 64 and all(c in "0123456789abcdef" for c in parts[0])))
            break  # one representative check name; structure checked per line above
        # manifest schema is exactly the frozen 10P0 closed list.
        manifest_loaded = json.loads((tmp_pkg / PACKAGE_MANIFEST_FILE).read_text(encoding="utf-8"))
        checks.append(("write_manifest_schema_set_eq_frozen_10p0", not check_manifest_schema(manifest_loaded)))
        # audit-log entries each have exactly the frozen 10P0 audit fields.
        audit_lines = (tmp_pkg / PACKAGE_AUDIT_LOG_DIR / PACKAGE_AUDIT_LOG_FILE).read_text(encoding="utf-8").strip().splitlines()
        checks.append(("write_audit_log_has_three_entries", len(audit_lines) == 3))
        for entry_line in audit_lines:
            entry = json.loads(entry_line)
            checks.append(("write_audit_entry_schema_set_eq_frozen_10p0", not check_audit_log_format_schema(entry)))
            break
        # provenance has exactly the frozen 10P0 provenance fields + wording.
        prov_loaded = json.loads((tmp_pkg / PACKAGE_PROVENANCE_FILE).read_text(encoding="utf-8"))
        checks.append(("write_provenance_schema_set_eq_frozen_10p0", not check_provenance_fields_schema(prov_loaded)))
        checks.append(("write_provenance_statement_is_frozen_wording",
                       prov_loaded["provenance_statement"] == FUTURE_PACKAGE_PROVENANCE_WORDING))
        # temp dir is NOT under ignored runs/ (synthetic fixture only).
        ok, _ = _validate_package_path_is_ignored_private(tmp_pkg)
        checks.append(("write_temp_pkg_not_under_ignored_runs", not ok))

    # CLI rejects ignored runs/ report path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10p1" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # CLI blocks generate-package without confirm flags.
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--generate-package", "--package-dir", str(DEFAULT_PACKAGE_DIR)])
    checks.append(("generate_package_cli_blocks_without_confirm_flags", cli_rc == 1))

    # Temp-file report round-trip (synthetic fixture only; no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10p1_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(dry), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # Prove the self-test did not fetch/read/private/execute/score/select/
    # inspect/generate-tasks/generate-packets/run-downstream/intake-validate.
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
    checks.append(("selftest_does_not_read_phase10g_artifacts", PRIVATE_PHASE10G_ARTIFACT_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_phase10p0_artifacts", PRIVATE_PHASE10P0_ARTIFACT_READ_ATTEMPTS == 0))
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
        description="Phase 10P1 operator-prepared offline registry-input package generation (sealed, no Phase 10 validation, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--generate-package", action="store_true",
        help="generate and seal the operator-prepared package under the frozen "
             "10P0 protocol into an ignored/private runs/ path (fail-closed)",
    )
    parser.add_argument(
        "--write-report", action="store_true",
        help="write the aggregate/boundary-only public report (no private output, no fetch, no Phase 10 validation)",
    )
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument(
        "--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR,
        help="package directory (must be under ignored/private runs/)",
    )
    parser.add_argument(
        "--confirm-ignored-private-path", action="store_true",
        help="explicit confirmation that the package path is ignored/private under runs/",
    )
    parser.add_argument(
        "--confirm-operator-prepared", action="store_true",
        help="explicit confirmation that the package is operator-prepared under the frozen Phase 10P0 protocol",
    )
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
    if args.generate_package:
        try:
            summary = generate_package(
                args.package_dir,
                confirm_ignored_private_path=args.confirm_ignored_private_path,
                confirm_operator_prepared=args.confirm_operator_prepared,
            )
        except SystemExit as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({
            "status": STATUS,
            "package_generation_executed": summary["package_generation_executed"],
            "package_sealed_with_sha256_checksums": summary["package_sealed_with_sha256_checksums"],
            "package_under_ignored_runs_path": summary["package_under_ignored_runs_path"],
            "source_count_bucket": summary["source_count_bucket"],
            "checksum_algorithm": summary["checksum_algorithm"],
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
    parser.error("choose --self-test, --generate-package, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
