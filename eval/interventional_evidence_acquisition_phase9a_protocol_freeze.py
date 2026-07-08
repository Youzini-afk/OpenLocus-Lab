#!/usr/bin/env python3
"""Phase 9A clean-room candidate-source protocol-freeze report helper.

This helper is deliberately protocol/report-only. It writes or validates one
public aggregate JSON report and uses only constants embedded in this file. It
does not read private inputs, ignored run storage, manifests, candidate pools,
source material, provider outputs, or network resources.
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
PHASE = "phase9a_protocol_freeze_no_execution_no_claim"
STATUS = "phase9a_protocol_freeze_no_execution_no_claim"
SCHEMA_VERSION = "phase9a_protocol_freeze_no_execution_no_claim_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

FORBIDDEN_OPERATION_KEYS = (
    "private_reads",
    "ignored_runs_reads",
    "manifest_reads",
    "phase8b_private_registry_or_pool_reads",
    "phase8b_accepted_or_rejected_repo_inspection",
    "repo_fetch_or_clone",
    "source_reads",
    "task_generation",
    "candidate_registry_population",
    "candidate_pool_construction",
    "data_collection",
    "row_or_outcome_scoring",
    "labels_generated",
    "evidence_success_evaluation",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
    "direct_phase9_execution",
    "phase8b_accepted_repo_count_repair",
)

CLAIM_BOUNDARY_KEYS = (
    "method_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "model_claim",
    "scoring_claim",
    "outcome_claim",
    "evidence_success_claim",
    "runtime_claim",
    "default_claim",
)

PUBLIC_PRIVACY_KEYS = (
    "repo_names_public",
    "repo_urls_public",
    "owners_public",
    "commits_or_hashes_public",
    "paths_public",
    "snippets_public",
    "task_ids_public",
    "row_ids_public",
    "manifest_paths_public",
    "run_dirs_public",
    "singleton_buckets_public",
    "per_repo_or_per_task_facts_public",
)

CHANNEL_ORDER = (
    "public_language_registry_top_projects_index",
    "public_ecosystem_topic_index",
    "public_package_metadata_dependents_index",
)

DETERMINISTIC_SORT_KEYS = (
    "normalized_public_project_identity_ascending",
    "public_metadata_stable_rank_ascending",
    "default_branch_name_ascending",
    "channel_local_index_ascending",
)

ELIGIBILITY_CRITERIA = (
    "publicly_accessible_without_authentication",
    "source_archive_materializable_before_scoring",
    "declared_or_publicly_auditable_license_present",
    "default_branch_or_equivalent_revision_resolvable",
    "in_scope_language_or_file_mix_detectable_from_public_metadata",
    "not_private_prior_phase_or_manual_named_seed_material",
)

EXCLUSION_CRITERIA = (
    "requires_authentication_or_private_access",
    "cannot_materialize_source_archive_before_scoring",
    "license_absent_or_not_publicly_auditable",
    "identity_collides_with_earlier_clean_room_candidate",
    "fork_or_mirror_duplicate_of_already_accepted_identity",
    "would_require_public_reporting_of_exact_identifiers",
)

REPLACEMENT_ALGORITHM = (
    "replace_unavailable_or_ineligible_source_with_next_uninspected_item_from_same_frozen_channel_stream",
    "if_channel_stream_exhausted_continue_round_robin_to_next_channel_in_frozen_channel_order",
    "replacement_must_happen_before_any_scoring_labels_or_outcomes",
    "replacement_must_not_use_performance_outcome_evidence_success_or_phase8b_private_feedback",
)

FROZEN_QUOTAS = {
    "accepted_source_target": 12,
    "accepted_source_minimum_for_audit_pass": 8,
    "candidate_inspection_cap_total": 48,
    "candidate_inspection_cap_per_channel": 16,
    "initial_channel_quota_each": 16,
}

CLAIM_WORD_RE = re.compile(
    r"\b(winner|lift|performance gain|method selected|selected method|product ready|"
    r"default change|runtime change|provider expansion|training result|model fit|"
    r"scoring result|outcome result|evidence success|route works)\b",
    re.IGNORECASE,
)
PRIVATE_VALUE_RE = re.compile(r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-fA-F0-9]{32,}\b")
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9])")
PRIVATE_KEY_RE = re.compile(
    r"(repo_url|repo_name|owner|commit|sha|path|hash|snippet|task_id|row_id|manifest|run_dir|per_repo|per_task|registry|pool)",
    re.IGNORECASE,
)

ALLOWED_PRIVATE_SHAPED_KEYS = {
    *FORBIDDEN_OPERATION_KEYS,
    *PUBLIC_PRIVACY_KEYS,
    "availability_first_gate",
    "candidate_registry_population",
    "candidate_pool_construction",
    "candidate_source_universe",
    "phase8b_private_material_policy",
    "neutral_acquisition_channels",
    "identity_normalization_before_inspection",
    "private_material_reuse_allowed",
    "privacy_contract",
    "future_phase9b_boundary",
    "commits_or_hashes_public",
    "per_repo_or_per_task_facts_public",
    "phase9a_does_not_read_phase8b_registry",
    "reuse_of_phase8b_private_candidates_near_misses_rejects_manifests_logs_provenance_forbidden",
    "future_phase9b_source_list_generated_without_phase8b_private_pool_or_manifest_reads",
    "prior_private_candidates_near_misses_rejects_manifests_logs_provenance_reuse_allowed",
    "public_registry_lists_allowed",
    "candidate_registry_public",
    "per_source_or_per_task_public_details_allowed",
    "private_or_per_repo_details_used",
    "concrete_freeze",
    "channel_order",
    "deterministic_sort_keys",
    "eligibility_criteria",
    "exclusion_criteria",
    "replacement_algorithm",
    "quota_numbers",
    "randomness_policy",
    "source_channels",
    "public_metadata_fields_used_for_ordering",
    "public_project_identity",
    "candidate_inspection_cap_per_channel",
    "candidate_inspection_cap_total",
}


def build_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "public_scope": {
            "docs_report_only": True,
            "protocol_freeze_only": True,
            "uses_only_public_aggregate_phase8b_phase8c_motivation": True,
            "not_continuation_or_repair_of_phase8b": True,
            "future_execution_authorized": False,
        },
        "motivation_public_aggregate_only": {
            "phase8c_ci_status_public_aggregate": "success",
            "phase8b_scoring_eligibility": "not_eligible_under_frozen_cap",
            "phase8b_accepted_repo_target_met": False,
            "private_or_per_repo_details_used": False,
        },
        "forbidden_operations": {key: False for key in FORBIDDEN_OPERATION_KEYS},
        "clean_room_protocol": {
            "candidate_source_universe": {
                "future_phase9b_source_list_generated_without_phase8b_private_pool_or_manifest_reads": True,
                "phase8b_private_material_reuse_allowed": False,
                "prior_private_candidates_near_misses_rejects_manifests_logs_provenance_reuse_allowed": False,
                "clean_room_operator_must_not_use_memory_of_private_phase8b_material": True,
            },
            "neutral_acquisition_channels": {
                "public_registry_lists_allowed": True,
                "public_topic_or_ecosystem_indexes_allowed": True,
                "public_package_or_project_metadata_allowed": True,
                "manual_named_seed_repositories_allowed": False,
                "private_or_prior_phase_candidate_sources_allowed": False,
                "channel_order": list(CHANNEL_ORDER),
            },
            "ordering_quota_replacement_rules": {
                "predeclared_seed_label": "phase9a_clean_room_public_seed_v1",
                "seed_semantics": "version_label_only_randomness_forbidden",
                "randomness_policy": "forbidden_no_random_shuffle_no_posthoc_resampling",
                "stable_channel_then_stable_public_metadata_order": True,
                "deterministic_sort_keys": list(DETERMINISTIC_SORT_KEYS),
                "quota_balance_before_inspection": True,
                "quota_numbers": dict(FROZEN_QUOTAS),
                "replacement_before_scoring_only": True,
                "replacement_reasons_limited_to_availability_or_eligibility": True,
                "replacement_algorithm": list(REPLACEMENT_ALGORITHM),
                "performance_based_replacement_allowed": False,
            },
            "identity_normalization_before_inspection": {
                "normalize_public_project_identity_before_source_inspection": True,
                "deduplicate_before_inspection": True,
                "fork_or_mirror_equivalence_checked_before_inspection_where_publicly_available": True,
                "identity_checks_use_public_metadata_only": True,
                "public_metadata_fields_used_for_ordering": list(DETERMINISTIC_SORT_KEYS),
            },
            "eligibility_filter_before_inspection": {
                "eligibility_criteria": list(ELIGIBILITY_CRITERIA),
                "exclusion_criteria": list(EXCLUSION_CRITERIA),
                "eligibility_decided_before_scoring": True,
                "eligibility_drift_is_hard_stop": True,
            },
            "availability_first_gate": {
                "availability_checked_before_scoring": True,
                "license_access_and_materialization_precheck_before_scoring": True,
                "unavailable_sources_replaced_before_scoring": True,
                "availability_gate_is_not_outcome_scoring": True,
            },
            "anti_laundering_rule": {
                "phase9a_does_not_read_phase8b_registry": True,
                "excludes_all_phase8b_private_material_rather_than_claiming_checked_safe_reuse": True,
                "reuse_of_phase8b_private_candidates_near_misses_rejects_manifests_logs_provenance_forbidden": True,
            },
            "privacy_contract": {
                "public_output_aggregate_only": True,
                "candidate_registry_public": False,
                "per_source_or_per_task_public_details_allowed": False,
                "private_or_exact_identifiers_public": False,
            },
            "hard_stops": {
                "phase8b_private_material_read_attempt": True,
                "identity_normalization_not_completed_before_inspection": True,
                "availability_gate_not_completed_before_scoring": True,
                "quota_or_ordering_rule_drift": True,
                "channel_order_or_sort_key_drift": True,
                "eligibility_or_replacement_algorithm_drift": True,
                "public_report_would_require_private_or_exact_identifiers": True,
                "any_scoring_before_later_audit_passes": True,
            },
        },
        "future_phase9b_boundary": {
            "may_only_construct_and_audit_under_frozen_protocol": True,
            "candidate_population_allowed_only_in_future_phase9b": True,
            "scoring_forbidden_until_later_audit_passes": True,
            "phase9a_direct_execution_authorized": False,
        },
        "public_privacy_contract": {
            "publication_level": "aggregate_protocol_only",
            **{key: False for key in PUBLIC_PRIVACY_KEYS},
        },
        "claim_boundary": {key: False for key in CLAIM_BOUNDARY_KEYS},
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "private_inputs_accessed_by_validator": False,
        },
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    if key and PRIVATE_KEY_RE.search(key) and key not in ALLOWED_PRIVATE_SHAPED_KEYS:
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(_scan_public(child_value, child_path, str(child_key)))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            errors.extend(_scan_public(child_value, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if CLAIM_WORD_RE.search(value):
            errors.append(f"forbidden claim wording at {path}")
        if PRIVATE_VALUE_RE.search(value):
            errors.append(f"private-shaped value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE or report.get("status") != STATUS:
        errors.append("identity/status drift")

    scope = report.get("public_scope", {})
    for key in (
        "docs_report_only",
        "protocol_freeze_only",
        "uses_only_public_aggregate_phase8b_phase8c_motivation",
        "not_continuation_or_repair_of_phase8b",
    ):
        if scope.get(key) is not True:
            errors.append(f"public scope missing: {key}")
    if scope.get("future_execution_authorized") is not False:
        errors.append("Phase 9A must not authorize execution")

    motivation = report.get("motivation_public_aggregate_only", {})
    if motivation.get("phase8b_scoring_eligibility") != "not_eligible_under_frozen_cap":
        errors.append("Phase 8B eligibility motivation must remain public aggregate no-eligibility")
    if motivation.get("phase8b_accepted_repo_target_met") is not False:
        errors.append("Phase 8B accepted target miss must remain aggregate false")
    if motivation.get("private_or_per_repo_details_used") is not False:
        errors.append("motivation must not use private or per-repo details")

    forbidden = report.get("forbidden_operations", {})
    for key in FORBIDDEN_OPERATION_KEYS:
        if forbidden.get(key) is not False:
            errors.append(f"forbidden operation flag not false: {key}")

    protocol = report.get("clean_room_protocol", {})
    universe = protocol.get("candidate_source_universe", {})
    for key in (
        "future_phase9b_source_list_generated_without_phase8b_private_pool_or_manifest_reads",
        "clean_room_operator_must_not_use_memory_of_private_phase8b_material",
    ):
        if universe.get(key) is not True:
            errors.append(f"clean-room source universe missing: {key}")
    for key in (
        "phase8b_private_material_reuse_allowed",
        "prior_private_candidates_near_misses_rejects_manifests_logs_provenance_reuse_allowed",
    ):
        if universe.get(key) is not False:
            errors.append(f"private material reuse must be excluded: {key}")

    channels = protocol.get("neutral_acquisition_channels", {})
    for key in (
        "public_registry_lists_allowed",
        "public_topic_or_ecosystem_indexes_allowed",
        "public_package_or_project_metadata_allowed",
    ):
        if channels.get(key) is not True:
            errors.append(f"neutral channel missing: {key}")
    for key in ("manual_named_seed_repositories_allowed", "private_or_prior_phase_candidate_sources_allowed"):
        if channels.get(key) is not False:
            errors.append(f"non-neutral channel must be forbidden: {key}")
    if channels.get("channel_order") != list(CHANNEL_ORDER):
        errors.append("concrete channel order drift")

    ordering = protocol.get("ordering_quota_replacement_rules", {})
    for key in (
        "stable_channel_then_stable_public_metadata_order",
        "quota_balance_before_inspection",
        "replacement_before_scoring_only",
        "replacement_reasons_limited_to_availability_or_eligibility",
    ):
        if ordering.get(key) is not True:
            errors.append(f"ordering/quota/replacement rule missing: {key}")
    if ordering.get("performance_based_replacement_allowed") is not False:
        errors.append("performance-based replacement must be forbidden")
    if ordering.get("predeclared_seed_label") != "phase9a_clean_room_public_seed_v1":
        errors.append("seed label drift")
    if ordering.get("seed_semantics") != "version_label_only_randomness_forbidden":
        errors.append("seed semantics drift")
    if ordering.get("randomness_policy") != "forbidden_no_random_shuffle_no_posthoc_resampling":
        errors.append("randomness policy drift")
    if ordering.get("deterministic_sort_keys") != list(DETERMINISTIC_SORT_KEYS):
        errors.append("deterministic sort keys drift")
    if ordering.get("quota_numbers") != dict(FROZEN_QUOTAS):
        errors.append("frozen quota numbers drift")
    if ordering.get("replacement_algorithm") != list(REPLACEMENT_ALGORITHM):
        errors.append("replacement algorithm drift")

    identity = protocol.get("identity_normalization_before_inspection", {})
    for key in (
        "normalize_public_project_identity_before_source_inspection",
        "deduplicate_before_inspection",
        "fork_or_mirror_equivalence_checked_before_inspection_where_publicly_available",
        "identity_checks_use_public_metadata_only",
    ):
        if identity.get(key) is not True:
            errors.append(f"identity normalization rule missing: {key}")
    if identity.get("public_metadata_fields_used_for_ordering") != list(DETERMINISTIC_SORT_KEYS):
        errors.append("identity/order public metadata fields drift")

    eligibility = protocol.get("eligibility_filter_before_inspection", {})
    if eligibility.get("eligibility_criteria") != list(ELIGIBILITY_CRITERIA):
        errors.append("eligibility criteria drift")
    if eligibility.get("exclusion_criteria") != list(EXCLUSION_CRITERIA):
        errors.append("exclusion criteria drift")
    if eligibility.get("eligibility_decided_before_scoring") is not True:
        errors.append("eligibility must be decided before scoring")
    if eligibility.get("eligibility_drift_is_hard_stop") is not True:
        errors.append("eligibility drift must be a hard stop")

    availability = protocol.get("availability_first_gate", {})
    for key in (
        "availability_checked_before_scoring",
        "license_access_and_materialization_precheck_before_scoring",
        "unavailable_sources_replaced_before_scoring",
        "availability_gate_is_not_outcome_scoring",
    ):
        if availability.get(key) is not True:
            errors.append(f"availability-first gate missing: {key}")

    anti_laundering = protocol.get("anti_laundering_rule", {})
    for key in (
        "phase9a_does_not_read_phase8b_registry",
        "excludes_all_phase8b_private_material_rather_than_claiming_checked_safe_reuse",
        "reuse_of_phase8b_private_candidates_near_misses_rejects_manifests_logs_provenance_forbidden",
    ):
        if anti_laundering.get(key) is not True:
            errors.append(f"anti-laundering rule missing: {key}")

    privacy = protocol.get("privacy_contract", {})
    if privacy.get("public_output_aggregate_only") is not True:
        errors.append("privacy contract must be aggregate-only")
    for key in (
        "candidate_registry_public",
        "per_source_or_per_task_public_details_allowed",
        "private_or_exact_identifiers_public",
    ):
        if privacy.get(key) is not False:
            errors.append(f"privacy contract must forbid: {key}")

    hard_stops = protocol.get("hard_stops", {})
    for key in (
        "phase8b_private_material_read_attempt",
        "identity_normalization_not_completed_before_inspection",
        "availability_gate_not_completed_before_scoring",
        "quota_or_ordering_rule_drift",
        "channel_order_or_sort_key_drift",
        "eligibility_or_replacement_algorithm_drift",
        "public_report_would_require_private_or_exact_identifiers",
        "any_scoring_before_later_audit_passes",
    ):
        if hard_stops.get(key) is not True:
            errors.append(f"hard stop missing: {key}")

    future = report.get("future_phase9b_boundary", {})
    for key in (
        "may_only_construct_and_audit_under_frozen_protocol",
        "candidate_population_allowed_only_in_future_phase9b",
        "scoring_forbidden_until_later_audit_passes",
    ):
        if future.get(key) is not True:
            errors.append(f"future Phase 9B boundary missing: {key}")
    if future.get("phase9a_direct_execution_authorized") is not False:
        errors.append("Phase 9A direct execution must stay unauthorized")

    public_privacy = report.get("public_privacy_contract", {})
    if public_privacy.get("publication_level") != "aggregate_protocol_only":
        errors.append("public report must be aggregate protocol only")
    for key in PUBLIC_PRIVACY_KEYS:
        if public_privacy.get(key) is not False:
            errors.append(f"public privacy boundary failed: {key}")

    for key, value in report.get("claim_boundary", {}).items():
        if value is not False:
            errors.append(f"claim boundary failed: {key}")

    errors.extend(_scan_public(report))
    return sorted(set(errors))


def write_report(output: Path = DEFAULT_REPORT) -> None:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise SystemExit("generated report invalid: " + "; ".join(errors[:12]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    base = build_report()
    checks.append(("base_report_valid", not validate_report(base)))

    for flag in FORBIDDEN_OPERATION_KEYS:
        mutated = copy.deepcopy(base)
        mutated["forbidden_operations"][flag] = True
        checks.append((f"forbidden_flag_rejected_{flag}", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_scope"]["not_continuation_or_repair_of_phase8b"] = False
    checks.append(("phase8b_continuation_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["candidate_source_universe"]["phase8b_private_material_reuse_allowed"] = True
    checks.append(("phase8b_private_reuse_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["anti_laundering_rule"]["phase9a_does_not_read_phase8b_registry"] = False
    checks.append(("anti_laundering_read_boundary_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["availability_first_gate"]["availability_checked_before_scoring"] = False
    checks.append(("availability_first_gate_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["neutral_acquisition_channels"]["channel_order"] = list(reversed(CHANNEL_ORDER))
    checks.append(("channel_order_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["ordering_quota_replacement_rules"]["deterministic_sort_keys"] = ["posthoc_metric_descending"]
    checks.append(("sort_key_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["ordering_quota_replacement_rules"]["quota_numbers"]["candidate_inspection_cap_total"] = 96
    checks.append(("quota_number_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["ordering_quota_replacement_rules"]["randomness_policy"] = "random_shuffle_allowed"
    checks.append(("randomness_policy_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["ordering_quota_replacement_rules"]["replacement_algorithm"] = ["choose_replacement_after_reviewing_results"]
    checks.append(("replacement_algorithm_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["clean_room_protocol"]["eligibility_filter_before_inspection"]["eligibility_criteria"] = ["looks_good_after_manual_review"]
    checks.append(("eligibility_criteria_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_phase9b_boundary"]["scoring_forbidden_until_later_audit_passes"] = False
    checks.append(("future_scoring_boundary_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_privacy_contract"]["repo_urls_public"] = True
    checks.append(("public_identifier_boundary_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_privacy_contract"]["example_bucket"] = "count_1"
    checks.append(("singleton_bucket_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_privacy_contract"]["example_value"] = "C:/private/repo/file.py"
    checks.append(("private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["method_claim"] = True
    checks.append(("claim_flag_rejected", bool(validate_report(mutated))))

    with tempfile.TemporaryDirectory(prefix="phase9a_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("temp_fixture_valid", not validate_report(loaded)))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 9A clean-room protocol-freeze report validator")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.write_report:
        write_report(args.output)
        print(str(args.output))
        return 0
    if args.validate_report:
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    parser.error("choose --self-test, --validate-report, or --write-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
