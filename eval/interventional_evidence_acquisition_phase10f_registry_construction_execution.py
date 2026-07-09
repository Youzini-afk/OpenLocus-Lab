#!/usr/bin/env python3
"""Phase 10F candidate-source-registry construction/provision execution (repair, no claim).

Phase 10F is the EXECUTION checkpoint that is allowed -- by oracle gate and by
the frozen Phase 10E candidate-source-registry construction/provision protocol --
to construct and/or provide a candidate-source registry *manifest only*, exactly
under the frozen Phase 10E rules.  Phase 10F is allowed to:

  * construct and/or provide a candidate-source-registry manifest only;
  * validate manifest eligibility/provisioning protocol against frozen 10E rules;
  * record registry-level metadata needed by 10E (source identifiers, declared
    provenance, availability bucket, compliance status);
  * store any private/non-public registry details under ignored ``runs/``;
  * publish only an aggregate/bucket-level public report.

Phase 10F is FORBIDDEN from fetching, cloning, scraping, downloading, or source
inspection; reading repository files or materializing source contents; task
generation, packet generation, repair execution, or downstream pipeline
execution beyond registry-level manifest allowed by 10E; scoring, adjudication,
correctness, evidence_success, or outcomes; modifying, weakening, reinterpreting,
or extending 10E after seeing registry availability; fallback channels, implicit
eligibility expansion, or best-effort registry invention.

Phase 10F STOPS as repair/no-claim when no compliant registry input/source
exists, when the available registry source cannot satisfy the frozen 10E
protocol, when constructing a compliant registry would require forbidden
fetch/clone/read/scrape/materialization/source inspection, when eligibility
depends on unavailable info without forbidden inspection, or when rule
relaxation would be needed.

Anti-adaptation rule: the frozen Phase 10E protocol is applied EXACTLY (the
frozen closed lists are imported directly from the committed Phase 10E
protocol-freeze module; no re-declaration, no drift, no post-hoc edit after
seeing registry availability).  Phase 10F is prospective, not tuned to the
observed Phase 10C ``bucket_zero`` / ``bucket_no_eligible_channel_registry``
outcome; 10C is referenced only as a gate/provenance fact and failure mode.

This executed run is repair/no-claim: no compliant candidate-source-registry
manifest was constructed or provided under the frozen Phase 10E protocol.  Every
allowed construction/provision route under frozen 10E requires either forbidden
fetch/clone/read/scrape/source-inspection (``neutral_public_acquisition_channels_only``)
or an operator-provided external-registry input that does not exist
(``operator_provided_external_registry``); best-effort registry invention is
forbidden.  Therefore the registry-manifest compliance bucket is ``bucket_zero``
and Phase 10F produces an honest repair/no-claim checkpoint (no tuning, no
padding, no protocol change, no fallback channel, no eligibility expansion).

Phase 10F makes NO validation/product/method/correctness/evidence-success claim;
it records ONLY registry-manifest construction/provision status.  It does NOT
score/adjudicate/evaluate correctness/evidence_success, does NOT fetch/clone/
read/scrape/inspect/sample/download source material, does NOT materialize source
contents, does NOT generate tasks/packets or execute any downstream pipeline,
does NOT modify/reinterpret/extend the frozen 10E protocol, does NOT add
thresholds/fallbacks/exceptions/channel rescue paths, does NOT treat
``bucket_zero`` as partial success, does NOT use Phase 9 artifacts as validation
evidence, does NOT change runtime/default behavior, and does NOT make
user-approval wording a protocol dependency.

This module performs no network/filesystem fetch, no source read, no private
ignored-``runs/`` read, no Phase 9/10A/10B/10C/10D/10E private artifact read, no
scoring/adjudication/correctness/evidence_success computation, and no task/packet
generation.  The dry self-test and report validation use synthetic tempfile
fixtures only.
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
# module so Phase 10F applies EXACTLY the frozen protocol (no re-declaration,
# no vocabulary/ordering/eligibility drift).  The import itself performs no
# execution, no fetch, no private read; it only loads frozen constants.
try:  # namespace-package form (repo root on sys.path)
    from eval.interventional_evidence_acquisition_phase10e_candidate_source_registry_protocol_freeze import (  # noqa: E402
        CLOSED_PROTOCOL_LISTS as PHASE10E_CLOSED_PROTOCOL_LISTS,
        ANTI_ADAPTATION_RULES as PHASE10E_ANTI_ADAPTATION_RULES,
        STATUS as PHASE10E_STATUS_CONST,
    )
except Exception:  # pragma: no cover - direct-module form (eval/ on sys.path)
    from interventional_evidence_acquisition_phase10e_candidate_source_registry_protocol_freeze import (  # type: ignore[no-redef]  # noqa: E402
        CLOSED_PROTOCOL_LISTS as PHASE10E_CLOSED_PROTOCOL_LISTS,
        ANTI_ADAPTATION_RULES as PHASE10E_ANTI_ADAPTATION_RULES,
        STATUS as PHASE10E_STATUS_CONST,
    )


PHASE = "phase10f_registry_construction_execution_no_claim"
SCHEMA_VERSION = "phase10f_registry_construction_execution_no_claim_report_v1"
STATUS = "phase10f_candidate_source_registry_construction_repair_no_claim"
PUBLICATION_LEVEL = (
    "aggregate_candidate_source_registry_construction_provision_execution_boundary_only"
)

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# ---------------------------------------------------------------------------
# Frozen gate references.  Phase 10F publishes exact commit/CI identifiers only
# for the immediate Phase 10E gate that froze the construction/provision
# protocol.  Older Phase 9 / 10A / 10B / 10C / 10D / hygiene checkpoints are
# carried forward only as status/bucket/scope provenance, not as exact
# commit/CI identifiers.
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

# Phase 10E protocol-freeze gate (the immediate gate for Phase 10F).  These are
# the only exact public gate references published by Phase 10F.
PHASE10E_COMMIT = "285543ba4006773a65b813f0a5fdeb7a840d7d3c"
PHASE10E_CI_RUN = "29018708378"
PHASE10E_CI_SUCCESS = True
PHASE10E_STATUS = PHASE10E_STATUS_CONST  # frozen, imported (no drift)

# Phase 10F is authorized by oracle as candidate-source-registry
# construction/provision ONLY, gated on Phase 10E commit + CI green.
PHASE10F_ORACLE_AUTHORIZATION = (
    "phase10f_authorized_by_oracle_candidate_source_registry_construction_provision_only"
)

# Repair/no-claim buckets for this executed run.
COMPLIANCE_BUCKET_ZERO = "bucket_zero"
COMPLIANCE_BUCKET_NONZERO = "bucket_nonzero_redacted"
REPAIR_REASON_BUCKET = (
    "bucket_no_compliant_registry_input_under_frozen_10e_protocol"
)

CONSERVATIVE_RECOMMENDATION = (
    "phase10f_candidate_source_registry_construction_or_provision_only_under_frozen_phase10e_protocol"
    "_phase9_closed_inherited"
    "_phase10a_gate_inherited"
    "_phase10b_gate_inherited"
    "_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources"
    "_phase10d_closeout_guard_gate_inherited"
    "_phase10e_protocol_freeze_gate_inherited_ci_green_authorized_phase10f_candidate_source_registry_construction_or_provision_only_by_oracle"
    "_phase10f_applies_frozen_phase10e_protocol_exactly_no_drift"
    "_phase10f_is_candidate_source_registry_construction_or_provision_only_not_validation_product_method_correctness_evidence_success"
    "_phase10f_does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material"
    "_phase10f_does_not_materialize_source_contents"
    "_phase10f_does_not_generate_tasks_or_packets_or_execute_downstream_pipeline"
    "_phase10f_does_not_score_adjudicate_or_run_correctness_evidence_success"
    "_phase10f_does_not_modify_weaken_reinterpret_or_extend_phase10e"
    "_phase10f_does_not_add_fallback_channels_or_implicit_eligibility_expansion_or_best_effort_registry_invention"
    "_phase10f_does_not_treat_zero_compliance_as_partial_success"
    "_phase10f_protocol_is_prospective_not_tuned_to_observed_outcome"
    "_phase10f_repair_no_claim_no_compliant_registry_manifest_constructed_or_provided_under_frozen_10e_protocol"
    "_constructing_compliant_registry_would_require_forbidden_fetch_clone_read_scrape_or_source_inspection"
    "_no_compliant_registry_input_or_operator_provided_external_registry_available_under_frozen_10e_protocol"
    "_private_registry_details_under_ignored_runs_only_none_materialized"
    "_future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green"
    "_boundary_review_after_phase10f_commit_and_ci_green"
    "_no_user_approval_wording_no_method_product_correctness_evidence_success_claim"
)

# ---------------------------------------------------------------------------
# Frozen Phase 10E protocol closed lists (imported; mirrored into the report
# and validator set-equality checked against the imported constants).  These
# are structural definitions only; Phase 10F does not fetch/clone/read/
# materialize/score to populate any registry.
# ---------------------------------------------------------------------------

CLOSED_PROTOCOL_LISTS = PHASE10E_CLOSED_PROTOCOL_LISTS
ANTI_ADAPTATION_RULES = PHASE10E_ANTI_ADAPTATION_RULES

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
    "phase10e_protocol_freeze_only_for_future_registry_construction",
    "phase10f_applies_frozen_phase10e_protocol_exactly_no_drift",
    "phase10f_is_candidate_source_registry_construction_or_provision_only",
    "phase10f_is_separate_from_phase9_not_continuation",
    "phase10f_makes_no_new_evidence_claims",
    "phase10f_protocol_is_prospective_not_tuned_to_observed_outcome",
    "phase10f_repair_no_claim_no_compliant_registry_manifest_constructed_or_provided_under_frozen_10e_protocol",
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
    "candidate_registry_populated",
    "candidate_registry_materialized",
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
    "phase10e_private_artifacts_public",
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
# published by Phase 10F.
GATE_REF_EXEMPT_PATHS = frozenset(
    {
        "$.gate_facts.phase10c_accepted_source_bucket",
        "$.gate_facts.phase10c_repair_reason_bucket",
        "$.gate_facts.phase10e_commit",
        "$.gate_facts.phase10e_ci_run",
    }
)

# Attestation counters to prove the validator/self-test do not fetch/read/
# execute/score/construct/materialize/generate.  Phase 10F's repair/no-claim
# path constructs nothing; these stay zero.
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
SOURCE_MATERIAL_READ_ATTEMPTS = 0
SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS = 0
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

    The report path must be under the Phase 10F public artifact directory
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
        return False, "report path is not under the Phase 10F public artifact directory"
    return True, ""


# ---------------------------------------------------------------------------
# Strict allowed-key schema for the public report
# ---------------------------------------------------------------------------

def _protocol_freeze_allowed() -> dict[str, Any]:
    """Build the allowed-schema dict for the frozen-10E-protocol section.

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
        "phase10d_status": None,
        "phase10e_commit": None,
        "phase10e_ci_run": None,
        "phase10e_ci_success": None,
        "phase10e_status": None,
        "phase10e_protocol_freeze_only_for_future_registry_construction": None,
        PHASE10F_ORACLE_AUTHORIZATION: None,
        "only_phase10e_gate_constants_are_exact_references": None,
        "local_same_tree_git_commits_not_read_or_compared": None,
        "older_phase9_10a_10b_10c_10d_hygiene_exact_refs_not_republished_by_phase10f": None,
    },
    "phase10f_scope": {
        "candidate_source_registry_construction_or_provision_only": None,
        "applies_frozen_phase10e_protocol_exactly_no_drift": None,
        "separate_from_phase9_not_continuation": None,
        "authorized_by_phase10e_protocol_freeze_gate_and_oracle": None,
        **{key: None for key in NO_EXECUTION_FALSE_KEYS},
    },
    "frozen_phase10e_protocol": _protocol_freeze_allowed(),
    "anti_adaptation_rules": {
        "anti_adaptation_rules_list": None,
        **{key: None for key in ANTI_ADAPTATION_RULES},
    },
    "phase10f_boundary": {
        "construction_or_provision_only_under_frozen_10e_protocol": None,
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material": None,
        "does_not_materialize_source_contents": None,
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline": None,
        "does_not_score_adjudicate_or_run_correctness_evidence_success": None,
        "does_not_modify_weaken_reinterpret_or_extend_phase10e": None,
        "does_not_add_fallback_channels_or_implicit_eligibility_expansion": None,
        "does_not_invent_best_effort_registry": None,
        "does_not_treat_zero_compliance_as_partial_success": None,
        "protocol_is_prospective_not_tuned_to_observed_outcome": None,
        "future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green": None,
        "boundary_review_required_after_phase10f_commit_and_ci_green": None,
        "no_user_approval_wording_as_protocol_dependency": None,
    },
    "registry_construction_summary": {
        "registry_manifest_construction_attempted": None,
        "compliant_registry_manifest_constructed": None,
        "compliant_registry_manifest_provided": None,
        "registry_manifest_compliance_bucket": None,
        "compliant_candidate_source_bucket": None,
        "repair_reason_bucket": None,
        "repair_no_claim": None,
        "private_registry_details_under_ignored_runs_only": None,
        "no_private_registry_manifest_materialized": None,
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
        "phase10f_specific_validator_available": None,
        "self_test_available": None,
        "report_validation_available": None,
        "validator_does_not_fetch_or_read_private": None,
        "validator_does_not_read_sources": None,
        "validator_does_not_read_ignored_runs": None,
        "validator_does_not_read_phase9_artifacts": None,
        "validator_does_not_read_phase10c_artifacts": None,
        "validator_does_not_read_phase10d_artifacts": None,
        "validator_does_not_read_phase10e_artifacts": None,
        "validator_does_not_inspect_sources": None,
        "validator_does_not_discover_sources": None,
        "validator_does_not_materialize_sources": None,
        "validator_does_not_generate_packets": None,
        "validator_does_not_generate_tasks": None,
        "validator_does_not_execute_downstream_pipeline": None,
        "validator_does_not_scrape_or_sample_or_download_sources": None,
        "validator_does_not_populate_candidate_registry": None,
        "validator_does_not_score_adjudicate_or_evaluate": None,
        "validator_does_not_modify_or_extend_phase10e": None,
        "validator_executes_tasks": None,
        "validator_reads_private_registry": None,
        "validator_reads_sources": None,
        "validator_reads_ignored_runs": None,
        "validator_inspects_sources": None,
        "validator_starts_empirical_work": None,
        "validator_discovers_sources": None,
        "validator_materializes_sources": None,
        "validator_generates_packets": None,
        "validator_generates_tasks": None,
        "validator_executes_downstream_pipeline": None,
        "validator_scrapes_or_samples_or_downloads_sources": None,
        "validator_populates_candidate_registry": None,
        "validator_scores_or_adjudicates": None,
        "validator_modifies_or_extends_phase10e": None,
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
    """Build the frozen_phase10e_protocol section with frozen lists + booleans."""
    section: dict[str, Any] = {}
    for _section_name, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key in section:
            continue
        section[list_key] = list(expected_tuple)
        for rule in expected_tuple:
            section[rule] = True
    return section


def build_public_report() -> dict[str, Any]:
    """Build the Phase 10F registry-construction/provision public report.

    This performs no network/filesystem fetch, no source read, no private
    ignored-``runs/`` read, no Phase 9/10A/10B/10C/10D/10E private artifact
    read, and no scoring.  It assembles the report from the frozen gate
    constants and the imported frozen Phase 10E protocol definitions only.
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
            "phase10e_commit": PHASE10E_COMMIT,
            "phase10e_ci_run": PHASE10E_CI_RUN,
            "phase10e_ci_success": PHASE10E_CI_SUCCESS,
            "phase10e_status": PHASE10E_STATUS,
            "phase10e_protocol_freeze_only_for_future_registry_construction": True,
            PHASE10F_ORACLE_AUTHORIZATION: True,
            "only_phase10e_gate_constants_are_exact_references": True,
            "local_same_tree_git_commits_not_read_or_compared": True,
            "older_phase9_10a_10b_10c_10d_hygiene_exact_refs_not_republished_by_phase10f": True,
        },
        "phase10f_scope": {
            "candidate_source_registry_construction_or_provision_only": True,
            "applies_frozen_phase10e_protocol_exactly_no_drift": True,
            "separate_from_phase9_not_continuation": True,
            "authorized_by_phase10e_protocol_freeze_gate_and_oracle": True,
            **{key: False for key in NO_EXECUTION_FALSE_KEYS},
        },
        "frozen_phase10e_protocol": _build_protocol_freeze_section(),
        "anti_adaptation_rules": {
            "anti_adaptation_rules_list": list(ANTI_ADAPTATION_RULES),
            **{key: True for key in ANTI_ADAPTATION_RULES},
        },
        "phase10f_boundary": {
            "construction_or_provision_only_under_frozen_10e_protocol": True,
            "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material": True,
            "does_not_materialize_source_contents": True,
            "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline": True,
            "does_not_score_adjudicate_or_run_correctness_evidence_success": True,
            "does_not_modify_weaken_reinterpret_or_extend_phase10e": True,
            "does_not_add_fallback_channels_or_implicit_eligibility_expansion": True,
            "does_not_invent_best_effort_registry": True,
            "does_not_treat_zero_compliance_as_partial_success": True,
            "protocol_is_prospective_not_tuned_to_observed_outcome": True,
            "future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green": True,
            "boundary_review_required_after_phase10f_commit_and_ci_green": True,
            "no_user_approval_wording_as_protocol_dependency": True,
        },
        "registry_construction_summary": {
            "registry_manifest_construction_attempted": False,
            "compliant_registry_manifest_constructed": False,
            "compliant_registry_manifest_provided": False,
            "registry_manifest_compliance_bucket": COMPLIANCE_BUCKET_ZERO,
            "compliant_candidate_source_bucket": COMPLIANCE_BUCKET_ZERO,
            "repair_reason_bucket": REPAIR_REASON_BUCKET,
            "repair_no_claim": True,
            "private_registry_details_under_ignored_runs_only": True,
            "no_private_registry_manifest_materialized": True,
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
            "phase10f_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_sources": True,
            "validator_does_not_read_ignored_runs": True,
            "validator_does_not_read_phase9_artifacts": True,
            "validator_does_not_read_phase10c_artifacts": True,
            "validator_does_not_read_phase10d_artifacts": True,
            "validator_does_not_read_phase10e_artifacts": True,
            "validator_does_not_inspect_sources": True,
            "validator_does_not_discover_sources": True,
            "validator_does_not_materialize_sources": True,
            "validator_does_not_generate_packets": True,
            "validator_does_not_generate_tasks": True,
            "validator_does_not_execute_downstream_pipeline": True,
            "validator_does_not_scrape_or_sample_or_download_sources": True,
            "validator_does_not_populate_candidate_registry": True,
            "validator_does_not_score_adjudicate_or_evaluate": True,
            "validator_does_not_modify_or_extend_phase10e": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "validator_inspects_sources": False,
            "validator_starts_empirical_work": False,
            "validator_discovers_sources": False,
            "validator_materializes_sources": False,
            "validator_generates_packets": False,
            "validator_generates_tasks": False,
            "validator_executes_downstream_pipeline": False,
            "validator_scrapes_or_samples_or_downloads_sources": False,
            "validator_populates_candidate_registry": False,
            "validator_scores_or_adjudicates": False,
            "validator_modifies_or_extends_phase10e": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": CONSERVATIVE_RECOMMENDATION,
    }
    return report


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_report(report: Any) -> list[str]:
    """Validate the Phase 10F public report against the frozen schema/constants.

    This does NOT read any Phase 9/10A/10B/10C/10D/10E artifact on disk, does
    NOT fetch/clone, does NOT read ignored ``runs/``, and does NOT score.  It
    checks the report's gate references against the frozen public gate
    constants directly, and applies the closed Phase 10E protocol lists with
    set-equality against the imported frozen constants.
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
    if gate.get("phase10e_commit") != PHASE10E_COMMIT:
        errors.append("Phase 10E commit gate reference drift")
    if gate.get("phase10e_ci_run") != PHASE10E_CI_RUN:
        errors.append("Phase 10E CI run gate reference drift")
    if gate.get("phase10e_ci_success") is not True:
        errors.append("Phase 10E CI success gate missing")
    if gate.get("phase10e_status") != PHASE10E_STATUS:
        errors.append("Phase 10E status gate reference drift")
    if gate.get("phase10e_protocol_freeze_only_for_future_registry_construction") is not True:
        errors.append("Phase 10E protocol-freeze-only boundary missing")
    if gate.get(PHASE10F_ORACLE_AUTHORIZATION) is not True:
        errors.append("Phase 10F oracle authorization boundary missing")
    if gate.get("only_phase10e_gate_constants_are_exact_references") is not True:
        errors.append("Phase 10E-only exact references boundary missing")
    if gate.get("local_same_tree_git_commits_not_read_or_compared") is not True:
        errors.append("local git commits not read boundary missing")
    if gate.get("older_phase9_10a_10b_10c_10d_hygiene_exact_refs_not_republished_by_phase10f") is not True:
        errors.append("older exact refs not republished boundary missing")

    scope = report.get("phase10f_scope", {})
    for key in (
        "candidate_source_registry_construction_or_provision_only",
        "applies_frozen_phase10e_protocol_exactly_no_drift",
        "separate_from_phase9_not_continuation",
        "authorized_by_phase10e_protocol_freeze_gate_and_oracle",
    ):
        if scope.get(key) is not True:
            errors.append(f"phase10f_scope boundary missing: {key}")
    for key in NO_EXECUTION_FALSE_KEYS:
        if scope.get(key) is not False:
            errors.append(f"phase10f_scope execution boundary failed: {key}")

    # Frozen Phase 10E protocol closed-list set-equality checks.
    protocol = report.get("frozen_phase10e_protocol", {})
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

    boundary = report.get("phase10f_boundary", {})
    for key in (
        "construction_or_provision_only_under_frozen_10e_protocol",
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material",
        "does_not_materialize_source_contents",
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_modify_weaken_reinterpret_or_extend_phase10e",
        "does_not_add_fallback_channels_or_implicit_eligibility_expansion",
        "does_not_invent_best_effort_registry",
        "does_not_treat_zero_compliance_as_partial_success",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green",
        "boundary_review_required_after_phase10f_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        if boundary.get(key) is not True:
            errors.append(f"phase10f_boundary missing: {key}")

    # Registry-construction summary: enforce repair/no-claim when the
    # compliance bucket is zero; block success wording unless the compliance
    # bucket is nonzero AND all allowed-only conditions hold.
    summary = report.get("registry_construction_summary", {})
    compliance_bucket = summary.get("registry_manifest_compliance_bucket")
    if compliance_bucket == COMPLIANCE_BUCKET_ZERO:
        if summary.get("repair_no_claim") is not True:
            errors.append("repair_no_claim missing for zero compliance bucket")
        if summary.get("compliant_registry_manifest_constructed") is not False:
            errors.append("compliant_registry_manifest_constructed must be false for zero compliance bucket")
        if summary.get("compliant_registry_manifest_provided") is not False:
            errors.append("compliant_registry_manifest_provided must be false for zero compliance bucket")
        if summary.get("registry_manifest_construction_attempted") is not False:
            errors.append("registry_manifest_construction_attempted must be false for zero compliance bucket")
        if summary.get("compliant_candidate_source_bucket") != COMPLIANCE_BUCKET_ZERO:
            errors.append("compliant_candidate_source_bucket must be bucket_zero for zero compliance bucket")
        if summary.get("repair_reason_bucket") != REPAIR_REASON_BUCKET:
            errors.append("repair_reason_bucket drift for zero compliance bucket")
        if summary.get("no_private_registry_manifest_materialized") is not True:
            errors.append("no_private_registry_manifest_materialized missing for zero compliance bucket")
        if report.get("status") != STATUS:
            errors.append("status must be repair/no-claim for zero compliance bucket")
    elif compliance_bucket == COMPLIANCE_BUCKET_NONZERO:
        # Success wording is allowed ONLY when the compliance bucket is nonzero
        # AND all allowed-only conditions hold.  This branch is never produced
        # by Phase 10F's repair/no-claim builder; it exists only so the
        # validator can reject inconsistent "success" reports.
        if summary.get("repair_no_claim") is not False:
            errors.append("repair_no_claim must be false for nonzero compliance bucket")
        if summary.get("compliant_registry_manifest_constructed") is not True:
            errors.append("compliant_registry_manifest_constructed must be true for nonzero compliance bucket")
        if summary.get("compliant_registry_manifest_provided") is not True:
            errors.append("compliant_registry_manifest_provided must be true for nonzero compliance bucket")
        if summary.get("compliant_candidate_source_bucket") != COMPLIANCE_BUCKET_NONZERO:
            errors.append("compliant_candidate_source_bucket must be bucket_nonzero_redacted for nonzero compliance bucket")
    else:
        errors.append("unknown registry_manifest_compliance_bucket")

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
        "phase10f_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_sources",
        "validator_does_not_read_ignored_runs",
        "validator_does_not_read_phase9_artifacts",
        "validator_does_not_read_phase10c_artifacts",
        "validator_does_not_read_phase10d_artifacts",
        "validator_does_not_read_phase10e_artifacts",
        "validator_does_not_inspect_sources",
        "validator_does_not_discover_sources",
        "validator_does_not_materialize_sources",
        "validator_does_not_generate_packets",
        "validator_does_not_generate_tasks",
        "validator_does_not_execute_downstream_pipeline",
        "validator_does_not_scrape_or_sample_or_download_sources",
        "validator_does_not_populate_candidate_registry",
        "validator_does_not_score_adjudicate_or_evaluate",
        "validator_does_not_modify_or_extend_phase10e",
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
        "validator_generates_packets",
        "validator_generates_tasks",
        "validator_executes_downstream_pipeline",
        "validator_scrapes_or_samples_or_downloads_sources",
        "validator_populates_candidate_registry",
        "validator_scores_or_adjudicates",
        "validator_modifies_or_extends_phase10e",
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
    global SOURCE_MATERIAL_READ_ATTEMPTS, SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS
    global SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS, CANDIDATE_REGISTRY_POPULATION_ATTEMPTS
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
    SOURCE_MATERIAL_READ_ATTEMPTS = 0
    SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS = 0
    SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS = 0
    CANDIDATE_REGISTRY_POPULATION_ATTEMPTS = 0
    SCORING_ADJUDICATION_OR_EXECUTION_ATTEMPTS = 0
    PROVIDER_OR_MODEL_CALL_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    # Baseline repair/no-claim report validates.
    dry = build_public_report()
    checks.append(("report_valid", not validate_report(dry)))
    checks.append(("phase_equals_slug", dry["phase"] == PHASE))
    checks.append(("status_is_repair_no_claim", dry["status"] == STATUS))
    checks.append(("publication_level_boundary", dry["publication_level"] == PUBLICATION_LEVEL))

    # Gate facts enforced.  Only the immediate Phase 10E gate publishes exact
    # commit/CI identifiers; older checkpoints are status/bucket/scope only.
    checks.append(("phase9_status_gate", dry["gate_facts"]["phase9_status"] == PHASE9_STATUS))
    checks.append(("phase10a_status_gate", dry["gate_facts"]["phase10a_status"] == PHASE10A_STATUS))
    checks.append(("phase10b_status_gate", dry["gate_facts"]["phase10b_status"] == PHASE10B_STATUS))
    checks.append(("phase10c_status_gate", dry["gate_facts"]["phase10c_status"] == PHASE10C_STATUS))
    checks.append(("phase10c_accepted_bucket_zero", dry["gate_facts"]["phase10c_accepted_source_bucket"] == "bucket_zero"))
    checks.append(("phase10c_repair_bucket", dry["gate_facts"]["phase10c_repair_reason_bucket"] == "bucket_no_eligible_channel_registry"))
    checks.append(("phase10d_status_gate", dry["gate_facts"]["phase10d_status"] == PHASE10D_STATUS))
    checks.append(("phase10e_commit_gate", dry["gate_facts"]["phase10e_commit"] == PHASE10E_COMMIT))
    checks.append(("phase10e_ci_gate", dry["gate_facts"]["phase10e_ci_run"] == PHASE10E_CI_RUN))
    checks.append(("phase10e_ci_success_gate", dry["gate_facts"]["phase10e_ci_success"] is True))
    checks.append(("phase10e_status_gate", dry["gate_facts"]["phase10e_status"] == PHASE10E_STATUS))
    checks.append(("phase10e_protocol_freeze_only", dry["gate_facts"]["phase10e_protocol_freeze_only_for_future_registry_construction"] is True))
    checks.append(("phase10f_oracle_authorization", dry["gate_facts"][PHASE10F_ORACLE_AUTHORIZATION] is True))

    # Registry-construction summary enforces repair/no-claim (zero bucket).
    summ = dry["registry_construction_summary"]
    checks.append(("compliance_bucket_zero", summ["registry_manifest_compliance_bucket"] == COMPLIANCE_BUCKET_ZERO))
    checks.append(("repair_no_claim_true", summ["repair_no_claim"] is True))
    checks.append(("construction_attempted_false", summ["registry_manifest_construction_attempted"] is False))
    checks.append(("compliant_constructed_false", summ["compliant_registry_manifest_constructed"] is False))
    checks.append(("compliant_provided_false", summ["compliant_registry_manifest_provided"] is False))
    checks.append(("candidate_source_bucket_zero", summ["compliant_candidate_source_bucket"] == COMPLIANCE_BUCKET_ZERO))
    checks.append(("repair_reason_bucket", summ["repair_reason_bucket"] == REPAIR_REASON_BUCKET))
    checks.append(("no_private_manifest_materialized", summ["no_private_registry_manifest_materialized"] is True))

    # Frozen Phase 10E protocol closed lists are set-equality checked against
    # the imported constants (proves no drift from 10E).
    proto = dry["frozen_phase10e_protocol"]
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

    # 10F boundary enforces construction/provision-only / no forbidden ops.
    boundary = dry["phase10f_boundary"]
    for key in (
        "construction_or_provision_only_under_frozen_10e_protocol",
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material",
        "does_not_materialize_source_contents",
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_modify_weaken_reinterpret_or_extend_phase10e",
        "does_not_add_fallback_channels_or_implicit_eligibility_expansion",
        "does_not_invent_best_effort_registry",
        "does_not_treat_zero_compliance_as_partial_success",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green",
        "boundary_review_required_after_phase10f_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        checks.append((f"phase10f_boundary_{key}", boundary[key] is True))

    # Reject missing/wrong gate facts.
    for field, bad_val, label in (
        ("phase9_status", "open", "phase9_status"),
        ("phase10a_status", "drift", "phase10a_status"),
        ("phase10b_status", "drift", "phase10b_status"),
        ("phase10c_status", "drift", "phase10c_status"),
        ("phase10c_accepted_source_bucket", "bucket_nonzero", "phase10c_bucket"),
        ("phase10c_repair_reason_bucket", "drift", "phase10c_repair"),
        ("phase10d_status", "drift", "phase10d_status"),
        ("phase10e_commit", "deadbeef", "phase10e_commit"),
        ("phase10e_ci_run", "0000", "phase10e_ci"),
        ("phase10e_status", "drift", "phase10e_status"),
    ):
        mutated = copy.deepcopy(dry)
        mutated["gate_facts"][field] = bad_val
        checks.append((f"wrong_{label}_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        del mutated["gate_facts"][field]
        checks.append((f"missing_{label}_rejected", bool(validate_report(mutated))))

    # Reject 10E CI success flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["phase10e_ci_success"] = False
    checks.append(("phase10e_ci_success_false_rejected", bool(validate_report(mutated))))

    # Reject 10F oracle authorization flipped to false.
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"][PHASE10F_ORACLE_AUTHORIZATION] = False
    checks.append(("phase10f_oracle_authorization_false_rejected", bool(validate_report(mutated))))

    # Reject phase10f_scope boundary facts flipped to false.
    for key in (
        "candidate_source_registry_construction_or_provision_only",
        "applies_frozen_phase10e_protocol_exactly_no_drift",
        "separate_from_phase9_not_continuation",
        "authorized_by_phase10e_protocol_freeze_gate_and_oracle",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10f_scope"][key] = False
        checks.append((f"phase10f_scope_{key}_false_rejected", bool(validate_report(mutated))))

    # Reject execution booleans true (forbidden in Phase 10F).
    for exec_key in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(dry)
        mutated["phase10f_scope"][exec_key] = True
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"execution_{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject 10F boundary facts flipped to false.
    for key in (
        "construction_or_provision_only_under_frozen_10e_protocol",
        "does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material",
        "does_not_materialize_source_contents",
        "does_not_generate_tasks_or_packets_or_execute_downstream_pipeline",
        "does_not_score_adjudicate_or_run_correctness_evidence_success",
        "does_not_modify_weaken_reinterpret_or_extend_phase10e",
        "does_not_add_fallback_channels_or_implicit_eligibility_expansion",
        "does_not_invent_best_effort_registry",
        "does_not_treat_zero_compliance_as_partial_success",
        "protocol_is_prospective_not_tuned_to_observed_outcome",
        "future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green",
        "boundary_review_required_after_phase10f_commit_and_ci_green",
        "no_user_approval_wording_as_protocol_dependency",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10f_boundary"][key] = False
        checks.append((f"phase10f_boundary_{key}_false_rejected", bool(validate_report(mutated))))

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

    # Reject frozen-10E-protocol list drift (extra member / member removed).
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        mutated = copy.deepcopy(dry)
        mutated["frozen_phase10e_protocol"][list_key] = list(expected_tuple) + ["extra_member"]
        checks.append((f"protocol_list_{list_key}_extra_rejected", bool(validate_report(mutated))))
        mutated = copy.deepcopy(dry)
        mutated["frozen_phase10e_protocol"][list_key] = list(expected_tuple)[:-1]
        checks.append((f"protocol_list_{list_key}_missing_rejected", bool(validate_report(mutated))))

    # Reject protocol-freeze attestation flipped to false.
    for _section, list_key, expected_tuple, _label in CLOSED_PROTOCOL_LISTS:
        if list_key.startswith("anti_adaptation"):
            continue
        for rule in expected_tuple:
            mutated = copy.deepcopy(dry)
            mutated["frozen_phase10e_protocol"][rule] = False
            checks.append((f"protocol_attest_{rule}_false_rejected", bool(validate_report(mutated))))

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

    # Repair enforcement: reject flipping repair_no_claim to false while the
    # compliance bucket stays zero (validator must enforce repair/no-claim).
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["repair_no_claim"] = False
    checks.append(("repair_no_claim_false_rejected", bool(validate_report(mutated))))

    # Repair enforcement: reject claiming a compliant manifest was constructed
    # while the compliance bucket stays zero (prevents success wording unless
    # compliance bucket is nonzero).
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["compliant_registry_manifest_constructed"] = True
    checks.append(("compliant_constructed_true_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["compliant_registry_manifest_provided"] = True
    checks.append(("compliant_provided_true_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["registry_manifest_construction_attempted"] = True
    checks.append(("construction_attempted_true_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["compliant_candidate_source_bucket"] = COMPLIANCE_BUCKET_NONZERO
    checks.append(("candidate_source_nonzero_rejected", bool(validate_report(mutated))))

    # Repair enforcement: nonzero compliance bucket without the matching
    # allowed-only success conditions must be rejected.
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["registry_manifest_compliance_bucket"] = COMPLIANCE_BUCKET_NONZERO
    checks.append(("nonzero_compliance_without_success_conditions_rejected", bool(validate_report(mutated))))

    # Unknown compliance bucket rejected.
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["registry_manifest_compliance_bucket"] = "bucket_unknown"
    checks.append(("unknown_compliance_bucket_rejected", bool(validate_report(mutated))))

    # Reject treating zero compliance as partial success.
    mutated = copy.deepcopy(dry)
    mutated["phase10f_boundary"]["does_not_treat_zero_compliance_as_partial_success"] = False
    checks.append(("zero_compliance_partial_success_rejected", bool(validate_report(mutated))))

    # Reject protocol tuned to observed outcome.
    mutated = copy.deepcopy(dry)
    mutated["phase10f_boundary"]["protocol_is_prospective_not_tuned_to_observed_outcome"] = False
    checks.append(("protocol_tuned_to_observed_rejected", bool(validate_report(mutated))))

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
        mutated["phase10f_scope"]["example_value"] = bad_val
        checks.append((f"private_shaped_{label}_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    for bad_key in (
        "private_source_commit", "repo_commit", "task_ci_run", "per_source_bucket",
        "source_path_bucket", "path", "repo_name", "task_id", "row_id",
        "packet_id", "manifest", "run_dir", "candidate_identity",
        "hash_value", "snippet_value",
    ):
        mutated = copy.deepcopy(dry)
        mutated["phase10f_scope"][bad_key] = "example"
        checks.append((f"private_key_{bad_key}_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    for singleton_val in ("count_1", "bucket_one", "bucket_1", "bucket_up_to_1",
                          "bucket_at_most_1", "n_1", "singleton"):
        mutated = copy.deepcopy(dry)
        mutated["phase10f_scope"]["example_bucket"] = singleton_val
        checks.append((f"singleton_{singleton_val}_rejected", bool(validate_report(mutated))))
        checks.append((f"singleton_regex_{singleton_val}", bool(SINGLETON_BUCKET_RE.search(singleton_val))))

    # Reject forbidden success wording (must NOT appear anywhere).
    for phrase in ("validated", "evidence_success achieved", "correctness evidence",
                   "materialization succeeded", "independent validation passed",
                   "OpenLocus works", "Phase 10 confirms", "Phase 10C confirms",
                   "Phase 10D confirms", "Phase 10E confirms", "Phase 10F confirms",
                   "method proven", "product readiness", "scoring success",
                   "outcome success", "evaluation works", "acquisition success",
                   "adjudication proven", "correctness proven", "lift achieved",
                   "generalized success", "evidence-acquisition success", "validation proven",
                   "registry construction succeeded", "registry provision proven"):
        mutated = copy.deepcopy(dry)
        mutated["phase10f_scope"]["example_note"] = phrase
        checks.append((f"forbidden_success_wording_{phrase.replace(' ', '_').replace('-', '_')}_rejected",
                       bool(validate_report(mutated))))

    # Reject user-approval wording.
    mutated = copy.deepcopy(dry)
    mutated["conservative_recommendation"] = "requires user approval to proceed"
    checks.append(("user_approval_wording_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10f_scope"]["example_note"] = "user must approve before proceeding"
    checks.append(("user_approval_wording_scope_rejected", bool(validate_report(mutated))))

    # Reject placeholder wording.
    for phrase in ("TBD", "TODO", "placeholder", "FIXME", "fill_in", "not_set"):
        mutated = copy.deepcopy(dry)
        mutated["phase10f_scope"]["example_note"] = phrase
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
    mutated["phase10f_scope"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_scope_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_gate_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["frozen_phase10e_protocol"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_protocol_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["registry_construction_summary"]["unexpected_nested"] = "x"
    checks.append(("unknown_nested_field_summary_rejected", bool(validate_report(mutated))))

    # Reject non-gate hash/CI values (gate values only allowed at exact paths).
    mutated = copy.deepcopy(dry)
    mutated["phase10f_scope"]["task_ci_run"] = "29999999999"
    checks.append(("non_whitelisted_ci_run_value_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(dry)
    mutated["phase10f_scope"]["example_hash"] = "0123456789abcdef0123456789abcdef01234567"
    checks.append(("non_gate_ref_hash_value_rejected", bool(validate_report(mutated))))
    checks.append(("gate_ref_values_on_whitelisted_paths_valid", not validate_report(dry)))

    # Reject flipping the "only Phase 10E gate constants are exact references".
    mutated = copy.deepcopy(dry)
    mutated["gate_facts"]["only_phase10e_gate_constants_are_exact_references"] = False
    checks.append(("only_phase10e_refs_false_rejected", bool(validate_report(mutated))))

    # Reject modifying/extending 10E in the validation summary.
    mutated = copy.deepcopy(dry)
    mutated["validation_summary"]["validator_modifies_or_extends_phase10e"] = True
    checks.append(("validator_modifies_phase10e_rejected", bool(validate_report(mutated))))

    # Path guard tests.
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10f" / "report.json")
    checks.append(("validate_report_rejects_runs_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "runs" / "phase10c" / "report.json")
    checks.append(("validate_report_rejects_runs_phase10c_path", not ok))
    ok, _ = _validate_report_path_is_public(REPO / "eval" / "report.json")
    checks.append(("validate_report_rejects_non_artifact_path", not ok))
    ok, _ = _validate_report_path_is_public(
        REPO / "artifacts" / "phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim" / "report.json")
    checks.append(("validate_report_rejects_other_phase_path", not ok))
    ok, _ = _validate_report_path_is_public(DEFAULT_PUBLIC_REPORT)
    checks.append(("validate_report_accepts_default_public_path", ok))

    # CLI rejects ignored runs/ path before reading.
    runs_cli_path = str(REPO / "runs" / "phase10f" / "report.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        cli_rc = main(["--validate-report", runs_cli_path])
    checks.append(("validate_report_cli_rejects_runs_path", cli_rc == 1))

    # Temp-file round-trip (synthetic fixture only; no private reads).
    with tempfile.TemporaryDirectory(prefix="phase10f_selftest_") as tmp:
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
    # materialize/inspect/generate-tasks/generate-packets/run-downstream.
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
    checks.append(("selftest_does_not_read_source_material", SOURCE_MATERIAL_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_scrape_or_sample_sources", SOURCE_MATERIAL_SCRAPE_OR_SAMPLE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_download_sources", SOURCE_MATERIAL_DOWNLOAD_ATTEMPTS == 0))
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
        description="Phase 10F candidate-source-registry construction/provision execution (repair, no claim)"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true",
                        help="write the registry-construction repair/no-claim report (no private output, no fetch)")
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
