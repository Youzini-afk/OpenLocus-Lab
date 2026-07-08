#!/usr/bin/env python3
"""Phase 9C task-construction/materialization protocol-freeze helper.

This helper is deliberately docs/report/validator-only. It writes or validates
one public aggregate JSON report and uses only constants embedded in this file.
It does not read ignored ``runs/`` storage, Phase 9B private registries, source
archives, source files, manifests, task rows, labels, outcomes, providers, or
network resources.
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

PHASE = "phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim"
STATUS = "phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim"
SCHEMA_VERSION = f"{PHASE}_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

PHASE9B_COMMIT = "cfb25cd"
PHASE9B_CI_RUN = "28967621378"
PHASE9B_STATUS = "phase9b_clean_room_source_construction_audit_no_scoring_no_claim"

NO_EXECUTION_FALSE_KEYS = (
    "task_generation_executed",
    "source_materialization_executed",
    "labels_generated",
    "outcomes_generated",
    "scoring_executed",
    "evidence_success_evaluated",
    "model_fitting",
    "provider_or_llm_calls",
    "runtime_default_or_product_changes",
    "private_registry_read",
)

CLAIM_BOUNDARY_FALSE_KEYS = (
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

PUBLIC_PRIVACY_FALSE_KEYS = (
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
    "manifests_public",
    "run_dirs_public",
    "per_source_public_facts",
    "per_task_public_facts",
    "singleton_buckets_public",
)

TASK_CONSTRUCTION_RULES = (
    "future_phase9d_uses_phase9b_private_registry_order_without_phase9c_registry_read",
    "deterministic_source_order_no_random_shuffle",
    "target_task_candidate_bucket_conservative_48_to_72",
    "hard_cap_bucket_up_to_96",
    "per_source_task_cap_bucket_up_to_8",
    "minimum_distinct_sources_bucket_at_least_8",
    "current_source_materialization_only_in_later_execution_not_phase9c",
    "source_path_range_hash_currentness_available_privately_before_later_task_acceptance",
    "task_types_limited_to_evidence_finding_file_localizable_code_tasks",
    "provider_llm_tasks_forbidden",
    "phase8b_phase7_phase5_private_material_task_derivation_forbidden",
    "no_unit_public_per_source_or_per_task_reporting",
)

MATERIALIZATION_PRECHECKS = (
    "future_private_source_archive_materialized_under_ignored_runs_only",
    "currentness_hash_reread_before_any_task_row_acceptance",
    "license_access_default_branch_checks_preserved",
    "exact_paths_ranges_hashes_snippets_private",
)

ELIGIBILITY_REPLACEMENT_RULES = (
    "reject_task_requiring_private_access",
    "reject_task_requiring_exact_public_identity_disclosure",
    "reject_unavailable_source",
    "reject_ambiguous_path_or_range",
    "reject_missing_license_currentness_or_hash_check",
    "reject_task_leaking_per_task_details",
    "replace_with_next_deterministic_candidate_from_same_source",
    "if_source_exhausted_continue_to_next_source_in_frozen_order",
    "replacement_before_labels_outcomes_scoring_only",
    "replacement_cannot_use_performance_or_evidence_success_feedback",
)

HARD_STOP_KEYS = (
    "status_drift",
    "missing_phase9b_gate_refs",
    "any_execution_boolean_true",
    "private_registry_read_true",
    "scoring_labels_outcomes_or_evidence_success_true",
    "provider_model_runtime_default_or_product_claim_true",
    "public_private_shaped_value_or_key",
    "singleton_bucket_or_count_one",
    "exact_count_field",
    "missing_phase9d_later_boundary_statement",
    "fewer_than_minimum_source_task_diversity_after_caps",
    "private_leak_or_singleton_public_bucket_need",
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]|(?:^|\s)/[A-Za-z0-9_.-]+/|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9])", re.IGNORECASE)
FORBIDDEN_PUBLIC_KEY_RE = re.compile(
    r"^(?:repo_name|repo_url|owner|source_url|source_name|candidate_identity|commit_sha|sha|hash|path|range|snippet|task_id|row_id|manifest|run_dir|per_source_fact|per_task_fact)$",
    re.IGNORECASE,
)

ALLOWED_PRIVATE_SHAPED_KEYS = {
    "phase9b_commit",
    "phase9b_ci_run",
    "phase9b_status",
    "phase9b_gate_references",
    "private_registry_read",
    "future_phase9d_may_reference_phase9b_private_accepted_source_registry",
    "phase9c_private_registry_read",
    "private_future_manifests_only_under_ignored_runs",
    *PUBLIC_PRIVACY_FALSE_KEYS,
}


def build_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "phase9b_gate_references": {
            "phase9b_commit": PHASE9B_COMMIT,
            "phase9b_ci_run": PHASE9B_CI_RUN,
            "phase9b_status": PHASE9B_STATUS,
            "phase9b_ci_success": True,
            "phase9b_gate_required_before_phase9c": True,
        },
        "phase9c_scope": {
            "docs_report_validator_only": True,
            "protocol_freeze_only": True,
            "future_phase9d_may_reference_phase9b_private_accepted_source_registry": True,
            "phase9c_private_registry_read": False,
            "task_construction_or_materialization_authorized_in_phase9c": False,
            "phase9d_execution_requires_later_boundary_after_phase9c_commit_and_ci_green": True,
        },
        "no_execution_booleans": {key: False for key in NO_EXECUTION_FALSE_KEYS},
        "future_protocol_summary": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "task_candidate_target_bucket": "bucket_conservative_48_to_72",
            "task_candidate_hard_cap_bucket": "bucket_up_to_96",
            "per_source_task_cap_bucket": "bucket_up_to_8",
            "minimum_distinct_sources_bucket": "bucket_at_least_8",
            "task_construction_rules": list(TASK_CONSTRUCTION_RULES),
            "materialization_prechecks": list(MATERIALIZATION_PRECHECKS),
            "eligibility_and_replacement_rules": list(ELIGIBILITY_REPLACEMENT_RULES),
            "phase9d_execution_caps_and_stops": {
                "phase9c_scoring_labels_outcomes_forbidden": True,
                "future_phase9d_may_only_construct_and_materialize_task_candidates": True,
                "future_strategy_scoring_requires_another_frozen_boundary": True,
                "stop_if_source_or_task_diversity_below_minimum_after_caps": True,
                "stop_on_private_leak_or_singleton_public_bucket_need": True,
            },
        },
        "public_privacy_contract": {
            "public_output_aggregate_only": True,
            "private_future_manifests_only_under_ignored_runs": True,
            "no_repo_source_names_urls_owners_commits_hashes_paths_snippets_task_ids_row_ids_manifests_run_dirs_per_source_or_per_task_facts_public": True,
            **{key: False for key in PUBLIC_PRIVACY_FALSE_KEYS},
        },
        "hard_stop_matrix": {key: True for key in HARD_STOP_KEYS},
        "claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "report_generation_available": True,
            "report_validation_available": True,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_executes_tasks": False,
        },
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    if key == "count":
        errors.append(f"exact count field at {path}")
    if key and FORBIDDEN_PUBLIC_KEY_RE.search(key) and key not in ALLOWED_PRIVATE_SHAPED_KEYS:
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
            errors.append(f"private-shaped value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE or report.get("status") != STATUS:
        errors.append("status drift")

    gate = report.get("phase9b_gate_references", {})
    if gate.get("phase9b_commit") != PHASE9B_COMMIT or gate.get("phase9b_ci_run") != PHASE9B_CI_RUN or gate.get("phase9b_status") != PHASE9B_STATUS:
        errors.append("missing Phase 9B gate refs")
    if gate.get("phase9b_ci_success") is not True or gate.get("phase9b_gate_required_before_phase9c") is not True:
        errors.append("Phase 9B gate success requirement missing")

    scope = report.get("phase9c_scope", {})
    for key in ("docs_report_validator_only", "protocol_freeze_only", "phase9d_execution_requires_later_boundary_after_phase9c_commit_and_ci_green"):
        if scope.get(key) is not True:
            errors.append(f"Phase 9C scope missing: {key}")
    if scope.get("phase9c_private_registry_read") is not False:
        errors.append("private registry read must be false")
    if scope.get("task_construction_or_materialization_authorized_in_phase9c") is not False:
        errors.append("Phase 9C must not authorize task construction/materialization")

    no_execution = report.get("no_execution_booleans", {})
    for key in NO_EXECUTION_FALSE_KEYS:
        if no_execution.get(key) is not False:
            errors.append(f"execution boolean must be false: {key}")
    if no_execution.get("private_registry_read") is not False:
        errors.append("private registry read true")
    for key in ("scoring_executed", "labels_generated", "outcomes_generated", "evidence_success_evaluated"):
        if no_execution.get(key) is not False:
            errors.append(f"scoring/label/outcome boundary failed: {key}")
    for key in ("provider_or_llm_calls", "model_fitting", "runtime_default_or_product_changes"):
        if no_execution.get(key) is not False:
            errors.append(f"provider/model/runtime/default/product boundary failed: {key}")

    summary = report.get("future_protocol_summary", {})
    if summary.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("future protocol summary must be aggregate bucketed only")
    expected_buckets = {
        "task_candidate_target_bucket": "bucket_conservative_48_to_72",
        "task_candidate_hard_cap_bucket": "bucket_up_to_96",
        "per_source_task_cap_bucket": "bucket_up_to_8",
        "minimum_distinct_sources_bucket": "bucket_at_least_8",
    }
    for key, expected in expected_buckets.items():
        if summary.get(key) != expected:
            errors.append(f"bucketed cap drift: {key}")
    if summary.get("task_construction_rules") != list(TASK_CONSTRUCTION_RULES):
        errors.append("task construction rule drift")
    if summary.get("materialization_prechecks") != list(MATERIALIZATION_PRECHECKS):
        errors.append("materialization precheck drift")
    if summary.get("eligibility_and_replacement_rules") != list(ELIGIBILITY_REPLACEMENT_RULES):
        errors.append("eligibility/replacement rule drift")
    phase9d = summary.get("phase9d_execution_caps_and_stops", {})
    for key in (
        "phase9c_scoring_labels_outcomes_forbidden",
        "future_phase9d_may_only_construct_and_materialize_task_candidates",
        "future_strategy_scoring_requires_another_frozen_boundary",
        "stop_if_source_or_task_diversity_below_minimum_after_caps",
        "stop_on_private_leak_or_singleton_public_bucket_need",
    ):
        if phase9d.get(key) is not True:
            errors.append(f"Phase 9D hard-stop boundary missing: {key}")

    privacy = report.get("public_privacy_contract", {})
    for key in (
        "public_output_aggregate_only",
        "private_future_manifests_only_under_ignored_runs",
        "no_repo_source_names_urls_owners_commits_hashes_paths_snippets_task_ids_row_ids_manifests_run_dirs_per_source_or_per_task_facts_public",
    ):
        if privacy.get(key) is not True:
            errors.append(f"public privacy contract missing: {key}")
    for key in PUBLIC_PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"public privacy boundary failed: {key}")

    hard_stops = report.get("hard_stop_matrix", {})
    for key in HARD_STOP_KEYS:
        if hard_stops.get(key) is not True:
            errors.append(f"hard stop missing: {key}")

    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    validation = report.get("validation_summary", {})
    for key in ("route_specific_validator_available", "self_test_available", "report_generation_available", "report_validation_available"):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in ("validator_reads_private_registry", "validator_reads_sources", "validator_executes_tasks"):
        if validation.get(key) is not False:
            errors.append(f"validator forbidden behavior: {key}")

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

    mutated = copy.deepcopy(base)
    mutated["status"] = "phase9c_status_drift"
    checks.append(("status_drift_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9b_gate_references"]["phase9b_commit"] = "wrong"
    checks.append(("phase9b_gate_ref_rejected", bool(validate_report(mutated))))

    for flag in NO_EXECUTION_FALSE_KEYS:
        mutated = copy.deepcopy(base)
        mutated["no_execution_booleans"][flag] = True
        checks.append((f"execution_boolean_rejected_{flag}", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["provider_claim"] = True
    checks.append(("provider_claim_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["model_claim"] = True
    checks.append(("model_claim_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["runtime_claim"] = True
    checks.append(("runtime_claim_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["default_claim"] = True
    checks.append(("default_claim_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["product_claim"] = True
    checks.append(("product_claim_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_privacy_contract"]["path"] = "src/private.py"
    checks.append(("private_shaped_key_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_privacy_contract"]["example_value"] = "C:/private/source/file.py"
    checks.append(("private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_protocol_summary"]["example_bucket"] = "count_1"
    checks.append(("singleton_bucket_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["future_protocol_summary"]["count"] = 2
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase9c_scope"]["phase9d_execution_requires_later_boundary_after_phase9c_commit_and_ci_green"] = False
    checks.append(("missing_phase9d_boundary_rejected", bool(validate_report(mutated))))

    with tempfile.TemporaryDirectory(prefix="phase9c_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("temp_fixture_valid", not validate_report(loaded)))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 9C task-construction/materialization protocol-freeze report validator")
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
