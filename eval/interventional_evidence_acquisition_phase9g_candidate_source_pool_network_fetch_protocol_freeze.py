#!/usr/bin/env python3
"""Phase 9G candidate source-pool network-fetch protocol freeze.

This is a docs/report/validator-only protocol freeze. It freezes the future
candidate-source-pool schema and the future Phase 9H network-fetch
implementation contract after the Phase 9F public-source fetch/clone
materialization repair/no-claim checkpoint. It does NOT fetch, clone, read, or
materialize any repository or source, does NOT read ignored ``runs/`` or
private candidate pools/registries/manifests, does NOT generate task rows,
labels, outcomes, scoring rows, or evidence_success, and makes no
method/product/performance/model/provider/training/runtime/default/scoring/
outcome/evidence-success claim.

It records that Phase 9F is repair/no-claim and is NOT proof that fetch/clone
or materialization works: Phase 9F observed zero buckets and
``public_source_fetch_clone_executed=false``.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

PHASE = (
    "phase9g_candidate_source_pool_network_fetch_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
STATUS = PHASE
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
)

# Phase 9F public gate reference values (oracle-provided).  Local same-tree git
# commits are not read or compared; the supplied confirmation values are
# matched against the frozen public gate constants only.
PHASE9F_STATUS = "phase9f_public_source_fetch_clone_materialization_repair_no_claim"
PHASE9F_COMMIT = "c091b742"
PHASE9F_CI_RUN = "28973602930"

PHASE9F_DOCS = (
    REPO / "docs" / "en" / "interventional-evidence-acquisition-phase9f-public-source-fetch-clone-materialization-no-scoring-no-claim.md",
    REPO / "docs" / "zh" / "interventional-evidence-acquisition-phase9f-public-source-fetch-clone-materialization-no-scoring-no-claim.md",
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
)

NO_EXECUTION_FALSE_KEYS = (
    "public_fetch_clone_executed",
    "source_materialization_executed",
    "task_generation_executed",
    "private_candidate_pool_read",
    "private_registry_read",
    "ignored_runs_read",
    "labels_generated",
    "outcomes_generated",
    "scoring_executed",
    "evidence_success_evaluated",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
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
)

FORBIDDEN_PUBLIC_FIELD_WORDS = (
    "scoring",
    "labels",
    "outcomes",
    "evidence_success",
)

# Claim-making wording that must never appear as an exposed value.  Targeted so
# legitimate boundary attestation keys such as ``*_validated`` booleans are not
# false-flagged.
CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"materialization\s+(?:works|succeeded|proven|established)"
    r"|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)"
    r"|clone\s+(?:works|succeeded|proven|established)"
    r"|evidence_success\s+(?:achieved|proven|established|confirmed)"
    r"|method\s+(?:proven|established|works|winner)"
    r"|lift\s+(?:proven|established|achieved)"
    r")\b",
    re.IGNORECASE,
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(
    r"^(?:repo|repo_name|repo_url|owner|url|source_url"
    r"|candidate_identity|commit|commit_sha|sha|hash"
    r"|path|range|snippet|task_id|row_id"
    r"|manifest|run_dir|per_source|per_task)$",
    re.IGNORECASE,
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0


def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def build_public_report() -> dict[str, Any]:
    """Build the frozen Phase 9G public protocol report.

    This function performs no network/filesystem fetch or private reads. It
    assembles the frozen protocol document from static constants.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9f_gate_references": {
            "phase9f_commit": PHASE9F_COMMIT,
            "phase9f_ci_run": PHASE9F_CI_RUN,
            "phase9f_ci_success": True,
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_repair_no_claim": True,
            "phase9f_zero_buckets": True,
            "phase9f_public_fetch_or_clone_executed": False,
            "phase9f_not_proof_fetch_or_clone_or_materialization_works": True,
            "phase9f_gate_required_before_phase9g": True,
        },
        "phase9g_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only": True,
            "public_fetch_clone_executed": False,
            "source_materialization_executed": False,
            "private_candidate_pool_read": False,
            "private_registry_read": False,
            "ignored_runs_read": False,
            "task_generation_executed": False,
            "future_execution_requires_phase9g_commit_and_ci_green": True,
        },
        "candidate_source_pool_schema": {
            "publication_level": "aggregate_bucketed_schema_only",
            "bounded_public_source_pool_only": True,
            "license_field": True,
            "access_field": True,
            "default_branch_field": True,
            "currentness_field": True,
            "deterministic_source_order_field": True,
            "retry_timeout_failure_bucket_fields": True,
            "clone_target_mapping_under_ignored_runs_only": True,
            "no_credentials_or_auth_prompt_fields": True,
            "no_private_host_fields": True,
            "no_local_fallback_fields": True,
            "no_repo_name_or_url_or_owner_or_commit_or_path_or_hash_fields": True,
        },
        "future_phase9h_network_fetch_contract": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "ignored_workspace": "runs/ only",
            "fetch_clone_rules": [
                "public_only_https_or_git_fetch_clone_under_explicit_confirmation_only",
                "fetch_clone_into_ignored_runs_workspace_only_not_into_tracked_artifacts",
                "no_credentials_or_auth_prompts_or_private_hosts_or_local_fallback",
                "deterministic_source_order_no_random_shuffle",
                "bounded_public_source_pool_only",
                "fail_closed_on_redirect_ambiguity",
                "fail_closed_on_auth_prompt",
                "fail_closed_on_private_host",
                "fail_closed_on_missing_license_access_or_default_branch",
                "fail_closed_on_hash_or_currentness_mismatch",
                "fail_closed_on_inaccessible_source",
                "retry_timeout_failure_buckets_aggregate_only",
                "clone_target_mapping_under_ignored_runs_only",
                "license_access_default_branch_currentness_fields_before_acceptance",
                "privacy_redaction_rules_aggregate_only",
                "aggregate_public_report_only_no_repo_names_urls_owners_commits_paths_snippets_hashes_row_ids_run_dirs_singleton_buckets",
                "task_candidate_target_bucket_conservative_48_to_72",
                "task_candidate_hard_cap_bucket_up_to_96",
                "per_source_task_cap_bucket_up_to_8",
                "minimum_distinct_sources_bucket_at_least_8",
                "stop_or_repair_if_zero_materialization_after_caps",
                "stop_or_repair_if_source_diversity_below_minimum_after_caps",
                "no_replacement_or_tuning_based_on_labels_outcomes_evidence_success_model_or_downstream_performance_feedback",
                "task_types_limited_to_evidence_finding_file_localizable_code_tasks",
                "provider_llm_tasks_forbidden",
                "no_unit_public_per_source_or_per_task_reporting",
                "no_hidden_github_api_substitute_unless_future_protocol_explicitly_allows_or_forbids",
            ],
            "license_access_default_branch_currentness_hash_checks": True,
            "deterministic_caps_preserved": True,
            "carry_forward_caps_preserved": True,
            "fail_closed_gates": True,
            "stop_on_zero_materialization_after_caps": True,
            "stop_on_diversity_below_minimum_after_caps": True,
            "no_replacement_tuning_on_labels_outcomes_evidence_success_model_downstream_feedback": True,
            "stop_on_privacy_leak_or_singleton_public_bucket": True,
            "future_strategy_scoring_requires_another_frozen_boundary": True,
        },
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
            "validator_does_not_read_private_candidate_pools": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
            "public_artifact_privacy_audit_expected": True,
        },
        "conservative_recommendation": (
            "freeze_future_phase9h_candidate_source_pool_network_fetch_protocol"
            "_no_execution_no_scoring_no_claim"
        ),
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    key_lower = key.lower()
    if key_lower in {"count"} or key_lower.endswith("_count"):
        errors.append(f"exact public count field at {path}")
    # Forbidden public field words (scoring/labels/outcomes/evidence_success)
    # only apply to non-boolean values: boolean attestation keys such as
    # ``scoring_executed`` or ``evidence_success_claim`` are boundary checks
    # that must be ``false``, not exposed scoring data.
    if not isinstance(value, bool) and any(word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS):
        errors.append(f"forbidden public field word at {path}")
    if key and PRIVATE_KEY_RE.search(key):
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(_scan_public(child_value, child_path, str(child_key)))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            errors.extend(_scan_public(child_value, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if PRIVATE_SHAPED_VALUE_RE.search(value):
            errors.append(f"private-shaped public value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
        if CLAIM_WORDING_RE.search(value):
            errors.append(f"claim-making wording at {path}")
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

    gate = report.get("phase9f_gate_references", {})
    if gate.get("phase9f_commit") != PHASE9F_COMMIT:
        errors.append("Phase 9F commit gate reference missing or drift")
    if gate.get("phase9f_ci_run") != PHASE9F_CI_RUN:
        errors.append("Phase 9F CI run gate reference missing or drift")
    if gate.get("phase9f_ci_success") is not True:
        errors.append("Phase 9F CI success gate missing")
    if gate.get("phase9f_status") != PHASE9F_STATUS:
        errors.append("Phase 9F status gate reference drift")
    if gate.get("phase9f_repair_no_claim") is not True:
        errors.append("Phase 9F repair/no-claim gate reference missing")
    if gate.get("phase9f_zero_buckets") is not True:
        errors.append("Phase 9F zero-buckets gate reference missing")
    if gate.get("phase9f_public_fetch_or_clone_executed") is not False:
        errors.append("Phase 9F public fetch/clone gate must be false")
    if gate.get("phase9f_not_proof_fetch_or_clone_or_materialization_works") is not True:
        errors.append("Phase 9F not-proof-fetch/clone/materialization gate missing")
    if gate.get("phase9f_gate_required_before_phase9g") is not True:
        errors.append("Phase 9F gate-required boundary missing")

    scope = report.get("phase9g_scope", {})
    for key in ("docs_report_validator_only", "protocol_freeze_only"):
        if scope.get(key) is not True:
            errors.append(f"phase9g scope missing: {key}")
    for key in (
        "public_fetch_clone_executed",
        "source_materialization_executed",
        "private_candidate_pool_read",
        "private_registry_read",
        "ignored_runs_read",
        "task_generation_executed",
    ):
        if scope.get(key) is not False:
            errors.append(f"phase9g execution boundary failed: {key}")
    if scope.get("future_execution_requires_phase9g_commit_and_ci_green") is not True:
        errors.append("phase9g future execution commit+CI-green boundary missing")

    schema = report.get("candidate_source_pool_schema", {})
    if schema.get("publication_level") != "aggregate_bucketed_schema_only":
        errors.append("candidate source pool schema publication level drift")
    for key in (
        "bounded_public_source_pool_only",
        "license_field",
        "access_field",
        "default_branch_field",
        "currentness_field",
        "deterministic_source_order_field",
        "retry_timeout_failure_bucket_fields",
        "clone_target_mapping_under_ignored_runs_only",
        "no_credentials_or_auth_prompt_fields",
        "no_private_host_fields",
        "no_local_fallback_fields",
        "no_repo_name_or_url_or_owner_or_commit_or_path_or_hash_fields",
    ):
        if schema.get(key) is not True:
            errors.append(f"candidate source pool schema missing: {key}")

    future = report.get("future_phase9h_network_fetch_contract", {})
    if future.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("future phase9h contract publication level drift")
    if future.get("ignored_workspace") != "runs/ only":
        errors.append("future phase9h contract ignored workspace drift")
    if future.get("license_access_default_branch_currentness_hash_checks") is not True:
        errors.append("future phase9h contract license/access/currentness/hash checks missing")
    if future.get("deterministic_caps_preserved") is not True:
        errors.append("future phase9h contract deterministic caps missing")
    if future.get("carry_forward_caps_preserved") is not True:
        errors.append("future phase9h contract carry-forward caps missing")
    if future.get("fail_closed_gates") is not True:
        errors.append("future phase9h contract fail-closed gates missing")
    if future.get("stop_on_zero_materialization_after_caps") is not True:
        errors.append("future phase9h contract stop-on-zero missing")
    if future.get("stop_on_diversity_below_minimum_after_caps") is not True:
        errors.append("future phase9h contract stop-on-diversity missing")
    if future.get("no_replacement_tuning_on_labels_outcomes_evidence_success_model_downstream_feedback") is not True:
        errors.append("future phase9h contract no-replacement-on-feedback missing")
    if future.get("stop_on_privacy_leak_or_singleton_public_bucket") is not True:
        errors.append("future phase9h contract stop-on-privacy/singleton missing")
    if future.get("future_strategy_scoring_requires_another_frozen_boundary") is not True:
        errors.append("future phase9h contract strategy-scoring boundary missing")
    rules = future.get("fetch_clone_rules")
    if not isinstance(rules, list) or not rules:
        errors.append("future phase9h contract fetch_clone_rules missing")
    else:
        required_rules = {
            "public_only_https_or_git_fetch_clone_under_explicit_confirmation_only",
            "fetch_clone_into_ignored_runs_workspace_only_not_into_tracked_artifacts",
            "no_credentials_or_auth_prompts_or_private_hosts_or_local_fallback",
            "deterministic_source_order_no_random_shuffle",
            "bounded_public_source_pool_only",
            "fail_closed_on_redirect_ambiguity",
            "fail_closed_on_auth_prompt",
            "fail_closed_on_private_host",
            "fail_closed_on_missing_license_access_or_default_branch",
            "fail_closed_on_hash_or_currentness_mismatch",
            "fail_closed_on_inaccessible_source",
            "retry_timeout_failure_buckets_aggregate_only",
            "clone_target_mapping_under_ignored_runs_only",
            "license_access_default_branch_currentness_fields_before_acceptance",
            "privacy_redaction_rules_aggregate_only",
            "aggregate_public_report_only_no_repo_names_urls_owners_commits_paths_snippets_hashes_row_ids_run_dirs_singleton_buckets",
            "task_candidate_target_bucket_conservative_48_to_72",
            "task_candidate_hard_cap_bucket_up_to_96",
            "per_source_task_cap_bucket_up_to_8",
            "minimum_distinct_sources_bucket_at_least_8",
            "stop_or_repair_if_zero_materialization_after_caps",
            "stop_or_repair_if_source_diversity_below_minimum_after_caps",
            "no_replacement_or_tuning_based_on_labels_outcomes_evidence_success_model_or_downstream_performance_feedback",
            "no_hidden_github_api_substitute_unless_future_protocol_explicitly_allows_or_forbids",
        }
        present = set(rules)
        missing_rules = required_rules - present
        if missing_rules:
            errors.append(
                "future phase9h contract missing rules: " + ", ".join(sorted(missing_rules))
            )

    no_exec = report.get("no_execution_booleans", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_exec.get(key) is not False:
            errors.append(f"no_execution boundary failed: {key}")

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

    claims = report.get("claim_boundary", {})
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if claims.get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    validation = report.get("validation_summary", {})
    for key in (
        "route_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_private_candidate_pools",
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

    errors.extend(_scan_public(report))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    base = build_public_report()
    checks.append(("base_report_valid", not validate_report(base)))

    # Reject missing Phase9F gate references.
    mutated = copy.deepcopy(base)
    del mutated["phase9f_gate_references"]["phase9f_commit"]
    checks.append(("missing_phase9f_commit_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    del mutated["phase9f_gate_references"]["phase9f_ci_run"]
    checks.append(("missing_phase9f_ci_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9f_gate_references"]["phase9f_status"] = "drift"
    checks.append(("phase9f_status_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9f_gate_references"]["phase9f_repair_no_claim"] = False
    checks.append(("phase9f_repair_no_claim_false_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9f_gate_references"]["phase9f_not_proof_fetch_or_clone_or_materialization_works"] = False
    checks.append(("phase9f_not_proof_false_rejected", bool(validate_report(mutated))))

    # Reject public_fetch_clone_executed=true.
    mutated = copy.deepcopy(base)
    mutated["phase9g_scope"]["public_fetch_clone_executed"] = True
    mutated["no_execution_booleans"]["public_fetch_clone_executed"] = True
    checks.append(("public_fetch_clone_executed_rejected", bool(validate_report(mutated))))

    # Reject source_materialization_executed=true.
    mutated = copy.deepcopy(base)
    mutated["phase9g_scope"]["source_materialization_executed"] = True
    mutated["no_execution_booleans"]["source_materialization_executed"] = True
    checks.append(("source_materialization_executed_rejected", bool(validate_report(mutated))))

    # Reject private candidate pool / private runs read=true.
    mutated = copy.deepcopy(base)
    mutated["phase9g_scope"]["private_candidate_pool_read"] = True
    mutated["no_execution_booleans"]["private_candidate_pool_read"] = True
    checks.append(("private_candidate_pool_read_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9g_scope"]["ignored_runs_read"] = True
    mutated["no_execution_booleans"]["ignored_runs_read"] = True
    checks.append(("private_runs_read_rejected", bool(validate_report(mutated))))

    # Reject task_generation_executed=true (implies materialization).
    mutated = copy.deepcopy(base)
    mutated["phase9g_scope"]["task_generation_executed"] = True
    mutated["no_execution_booleans"]["task_generation_executed"] = True
    checks.append(("task_generation_executed_rejected", bool(validate_report(mutated))))

    # Reject scoring / evidence_success / labels / outcomes exposed fields.
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(base)
        mutated["candidate_source_pool_schema"][bad_key] = "exposed_value"
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    # Reject scoring_executed / evidence_success_evaluated / labels_generated /
    # outcomes_generated set true (boundary booleans that must stay false).
    for exec_key in (
        "scoring_executed",
        "evidence_success_evaluated",
        "labels_generated",
        "outcomes_generated",
    ):
        mutated = copy.deepcopy(base)
        mutated["no_execution_booleans"][exec_key] = True
        checks.append((f"{exec_key}_true_rejected", bool(validate_report(mutated))))

    # Reject provider / model / default / runtime / product / performance claims.
    for claim_key in (
        "provider_claim",
        "model_claim",
        "runtime_claim",
        "default_claim",
        "product_claim",
        "performance_claim",
    ):
        mutated = copy.deepcopy(base)
        mutated["claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # Reject private / run / per-source / per-task public facts.
    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["per_source_public_facts"] = True
    checks.append(("per_source_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["per_task_public_facts"] = True
    checks.append(("per_task_public_facts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["run_locations_public"] = True
    checks.append(("run_locations_public_rejected", bool(validate_report(mutated))))

    # Reject singleton buckets.
    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["example_bucket"] = "count_1"
    checks.append(("count_1_singleton_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["example_bucket"] = "bucket_one"
    checks.append(("bucket_one_singleton_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_phase9h_network_fetch_contract"]["example_bucket"] = "singleton"
    checks.append(("singleton_wording_rejected", bool(validate_report(mutated))))

    # Reject exact count fields.
    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["count"] = 48
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    # Reject private-shaped values (URL / path / hash / owner/repo).
    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["example_value"] = "https://example.invalid/repo.git"
    checks.append(("url_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["example_value"] = "owner/repo"
    checks.append(("owner_repo_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["example_value"] = "a" * 40
    checks.append(("hash_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["example_value"] = "src/private.py"
    checks.append(("path_private_shaped_value_rejected", bool(validate_report(mutated))))

    # Reject private-shaped keys.
    mutated = copy.deepcopy(base)
    mutated["privacy_contract"]["path"] = "src/private.py"
    checks.append(("private_shaped_key_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["repo_name"] = "hidden"
    checks.append(("private_shaped_key_repo_name_rejected", bool(validate_report(mutated))))

    # Reject claim-making wording in exposed string values.
    mutated = copy.deepcopy(base)
    mutated["conservative_recommendation"] = "materialization works and is proven"
    checks.append(("claim_wording_materialization_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_phase9h_network_fetch_contract"]["example_note"] = "fetch/clone works"
    checks.append(("claim_wording_fetch_clone_works_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["candidate_source_pool_schema"]["example_note"] = "evidence_success achieved"
    checks.append(("claim_wording_evidence_success_rejected", bool(validate_report(mutated))))

    # Reject future execution without phase9g commit+CI green.
    mutated = copy.deepcopy(base)
    mutated["phase9g_scope"]["future_execution_requires_phase9g_commit_and_ci_green"] = False
    checks.append(("future_execution_without_commit_ci_rejected", bool(validate_report(mutated))))

    # Reject a missing required future-phase9h rule.
    mutated = copy.deepcopy(base)
    mutated["future_phase9h_network_fetch_contract"]["fetch_clone_rules"] = [
        r for r in base["future_phase9h_network_fetch_contract"]["fetch_clone_rules"]
        if r != "fail_closed_on_inaccessible_source"
    ]
    checks.append(("missing_required_rule_rejected", bool(validate_report(mutated))))

    # Validate a temp-file round-trip.
    with tempfile.TemporaryDirectory(prefix="phase9g_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # Prove the validator/self-test did not fetch/read private.
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_sources", SOURCE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append((
        "selftest_does_not_read_private_candidate_pools",
        PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS == 0,
    ))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9G candidate source-pool network-fetch protocol freeze"
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
