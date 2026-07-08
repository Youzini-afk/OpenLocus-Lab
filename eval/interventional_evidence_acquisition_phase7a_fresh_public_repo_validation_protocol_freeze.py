#!/usr/bin/env python3
"""Phase 7A fresh public-repo validation protocol freeze validator.

Design-only helper for the public Phase 7A protocol report. It validates the
aggregate/no-claim protocol shape only; it does not read private rows, ignored
runs, source files, repositories, manifests, or network resources.
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
PHASE = "phase7a_fresh_public_repo_validation_protocol_freeze"
STATUS = "phase7a_protocol_freeze_no_execution_no_claim"
SCHEMA_VERSION = "phase7a_fresh_public_repo_validation_protocol_freeze_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
LABELS = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
PHASE7B_STATUSES = (
    "stop_no_claim",
    "repair_fresh_validation_contract_no_claim",
    "fresh_public_repo_validation_positive_no_claim",
)
FORBIDDEN_CLAIM_WORD_RE = re.compile(
    r"\b(winner|lift|selected strategy|selected method|product|default|runtime|deployment|training|beat|beats)\b",
    re.IGNORECASE,
)
PRIVATE_VALUE_RE = re.compile(
    r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-f0-9]{32,}\b|\b\d+\s*-\s*\d+\b",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(
    r"(repo_url|repo_name|owner|commit|sha|path|range|hash|snippet|task_id|row_id|manifest|run_dir|per_repo|per_task|per_fold)",
    re.IGNORECASE,
)
ALLOWED_PRIVATE_FLAG_KEYS = {
    "repo_names_urls_owners_public",
    "exact_commits_public",
    "exact_paths_ranges_hashes_snippets_public",
    "task_ids_or_row_ids_public",
    "manifests_or_run_dirs_public",
    "per_repo_per_task_per_fold_public",
    "repo_url_name_owner_overlap_private_check",
    "pinned_commit_overlap_private_check",
    "task_identity_overlap_private_check",
    "exact_file_reference_overlap_private_check",
    "too_close_file_family_private_check",
    "full_panel_per_task",
    "max_tasks_per_repo",
}


def build_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "execution_boundary": {
            "design_only": True,
            "repo_fetch_or_clone_executed": False,
            "task_generation_executed": False,
            "canary_executed": False,
            "source_reads_executed": False,
            "private_rows_read": False,
            "runs_directory_read": False,
            "model_fit_or_training_executed": False,
            "provider_network_llm_used": False,
            "runtime_or_release_setting_changed": False,
            "new_retrieval_family_added": False,
        },
        "phase7b_frozen_protocol": {
            "freshness_rule": "fresh_public_repos_and_tasks_not_used_in_phase5b",
            "repo_target_min": 8,
            "repo_target_max": 12,
            "repo_hard_max": 16,
            "task_target_min": 80,
            "task_target_max": 120,
            "task_hard_max": 150,
            "max_tasks_per_repo": 20,
            "same_seven_labels_exact": list(LABELS),
            "full_panel_per_task": True,
            "possible_statuses_exact": list(PHASE7B_STATUSES),
            "replacement_rule": {
                "pre_outcome_invalidity_only": True,
                "allowed_reasons": [
                    "clone_failure",
                    "pinned_commit_unavailable",
                    "insufficient_eligible_files",
                    "evidencecore_materialization_impossible_before_scoring",
                ],
                "replacement_after_outcome_observation_allowed": False,
            },
            "private_overlap_rejection_rule": {
                "repo_url_name_owner_overlap_private_check": True,
                "pinned_commit_overlap_private_check": True,
                "task_identity_overlap_private_check": True,
                "exact_file_reference_overlap_private_check": True,
                "too_close_file_family_private_check": True,
                "public_overlap_detail_level": "boolean_or_bucket_only",
            },
            "evidencecore_rule": {
                "candidate_found_alone_is_evidence": False,
                "success_requires_current_source_read": True,
                "success_requires_materialization": True,
                "success_requires_content_digest": True,
                "success_requires_currentness_reread": True,
                "success_requires_span_match": True,
                "success_requires_task_tie": True,
                "stop_abstain_success_required_bucket": "bucket_zero",
            },
            "positive_status_meaning": "nonzero_aggregate_evidencecore_valid_local_evidence_acquisition_under_frozen_actions_with_privacy_and_controls_held_no_claim",
        },
        "future_public_report_contract": {
            "publication_level": "aggregate_only",
            "count_buckets_included": True,
            "label_coverage_buckets_included": True,
            "evidence_success_buckets_included": True,
            "best_fixed_local_or_acquisition_baseline_bucket_included": True,
            "privacy_summary_included": True,
            "evidencecore_validation_included": True,
            "singleton_buckets_public": False,
            "repo_names_urls_owners_public": False,
            "exact_commits_public": False,
            "exact_paths_ranges_hashes_snippets_public": False,
            "task_ids_or_row_ids_public": False,
            "manifests_or_run_dirs_public": False,
            "per_repo_per_task_per_fold_public": False,
            "claim_wording_public": False,
        },
        "claim_boundary": {
            "method_comparison_claim": False,
            "performance_increase_claim": False,
            "chosen_strategy_claim": False,
            "release_readiness_claim": False,
            "deployment_claim": False,
            "model_training_claim": False,
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "private_inputs_accessed_by_validator": False,
        },
        "next_authorized_action": "phase7b_runner_may_be_written_after_phase7a_is_committed_ci_green_and_phase7b_boundary_is_explicitly_invoked_under_existing_low_resource_no_claim_constraints",
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    lowered_key = key.lower()
    if PRIVATE_KEY_RE.search(lowered_key) and key not in ALLOWED_PRIVATE_FLAG_KEYS:
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            errors.extend(_scan_public(child, f"{path}.{child_key}" if path != "$" else f"$.{child_key}", str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_scan_public(child, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if "count_1" in value:
            errors.append(f"singleton bucket at {path}")
        if FORBIDDEN_CLAIM_WORD_RE.search(value):
            errors.append(f"forbidden claim wording at {path}")
        if PRIVATE_VALUE_RE.search(value):
            errors.append(f"private-shaped value at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE or report.get("status") != STATUS:
        errors.append("identity/status drift")
    boundary = report.get("execution_boundary", {})
    if boundary.get("design_only") is not True:
        errors.append("design-only boundary missing")
    for key in (
        "repo_fetch_or_clone_executed", "task_generation_executed", "canary_executed",
        "source_reads_executed", "private_rows_read", "runs_directory_read",
        "model_fit_or_training_executed", "provider_network_llm_used",
        "runtime_or_release_setting_changed", "new_retrieval_family_added",
    ):
        if boundary.get(key) is not False:
            errors.append(f"forbidden Phase 7A operation: {key}")
    protocol = report.get("phase7b_frozen_protocol", {})
    required_caps = {
        "repo_target_min": 8,
        "repo_target_max": 12,
        "repo_hard_max": 16,
        "task_target_min": 80,
        "task_target_max": 120,
        "task_hard_max": 150,
        "max_tasks_per_repo": 20,
    }
    for key, expected in required_caps.items():
        if protocol.get(key) != expected:
            errors.append(f"cap drift: {key}")
    if tuple(protocol.get("same_seven_labels_exact", [])) != LABELS:
        errors.append("seven-label drift")
    if tuple(protocol.get("possible_statuses_exact", [])) != PHASE7B_STATUSES:
        errors.append("Phase 7B status set drift")
    replacement = protocol.get("replacement_rule", {})
    if replacement.get("pre_outcome_invalidity_only") is not True or replacement.get("replacement_after_outcome_observation_allowed") is not False:
        errors.append("replacement rule drift")
    overlap = protocol.get("private_overlap_rejection_rule", {})
    for key in (
        "repo_url_name_owner_overlap_private_check", "pinned_commit_overlap_private_check",
        "task_identity_overlap_private_check", "exact_file_reference_overlap_private_check",
        "too_close_file_family_private_check",
    ):
        if overlap.get(key) is not True:
            errors.append(f"overlap rule missing: {key}")
    evidence = protocol.get("evidencecore_rule", {})
    if evidence.get("candidate_found_alone_is_evidence") is not False:
        errors.append("candidate-found evidence boundary drift")
    for key in (
        "success_requires_current_source_read", "success_requires_materialization",
        "success_requires_content_digest", "success_requires_currentness_reread",
        "success_requires_span_match", "success_requires_task_tie",
    ):
        if evidence.get(key) is not True:
            errors.append(f"EvidenceCore rule missing: {key}")
    if evidence.get("stop_abstain_success_required_bucket") != "bucket_zero":
        errors.append("stop/abstain control rule drift")
    public_contract = report.get("future_public_report_contract", {})
    for key in (
        "singleton_buckets_public", "repo_names_urls_owners_public", "exact_commits_public",
        "exact_paths_ranges_hashes_snippets_public", "task_ids_or_row_ids_public",
        "manifests_or_run_dirs_public", "per_repo_per_task_per_fold_public", "claim_wording_public",
    ):
        if public_contract.get(key) is not False:
            errors.append(f"future public privacy/claim boundary failed: {key}")
    for key in ("count_buckets_included", "label_coverage_buckets_included", "evidence_success_buckets_included", "best_fixed_local_or_acquisition_baseline_bucket_included", "privacy_summary_included", "evidencecore_validation_included"):
        if public_contract.get(key) is not True:
            errors.append(f"future public aggregate field missing: {key}")
    claim_boundary = report.get("claim_boundary", {})
    for key, value in claim_boundary.items():
        if value is not False:
            errors.append(f"claim boundary failed: {key}")
    next_action = report.get("next_authorized_action", "")
    if "phase7a_is_committed_ci_green" not in next_action or "phase7b_boundary_is_explicitly_invoked" not in next_action:
        errors.append("next action must require Phase 7A CI-green and explicit Phase 7B boundary invocation")
    if "separately_authorized" in next_action or "separate_explicit_decision" in next_action:
        errors.append("next action must not over-require separate user authorization")
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
    mutated["future_public_report_contract"]["singleton_buckets_public"] = "count_1"
    checks.append(("singleton_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(base)
    mutated["phase7b_frozen_protocol"]["same_seven_labels_exact"] = list(LABELS[:-1])
    checks.append(("label_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(base)
    mutated["phase7b_frozen_protocol"].pop("task_hard_max")
    checks.append(("missing_cap_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(base)
    mutated["phase7b_frozen_protocol"]["possible_statuses_exact"] = ["stop_no_claim"]
    checks.append(("status_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["method_comparison_claim"] = True
    checks.append(("claim_flag_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(base)
    mutated["phase7b_frozen_protocol"]["positive_status_meaning"] = "winner"
    checks.append(("claim_word_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(base)
    mutated["future_public_report_contract"]["example_repo_url"] = "https://example.invalid/repo"
    checks.append(("private_shaped_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(base)
    mutated["next_authorized_action"] = "stop_until_phase7b_runner_is_separately_authorized_under_this_fresh_validation_protocol"
    checks.append(("over_required_next_action_rejected", bool(validate_report(mutated))))
    with tempfile.TemporaryDirectory(prefix="phase7a_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("temp_fixture_valid", not validate_report(loaded)))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7A protocol-freeze report validator")
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
