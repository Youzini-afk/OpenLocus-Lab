#!/usr/bin/env python3
"""Phase 7D input-repair protocol freeze report writer/validator.

Docs/report-only helper for the public Phase 7D protocol report. It validates
only the aggregate no-claim protocol shape. It does not read private rows,
manifests, provenance, run directories, repositories, source files, or network
resources; it only writes or validates the public JSON report supplied by the
caller.
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
PHASE = "phase7d_input_repair_protocol_freeze"
STATUS = "phase7d_input_repair_protocol_freeze_no_execution_no_claim"
SCHEMA_VERSION = "phase7d_input_repair_protocol_freeze_report_v1"
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

PHASE7C_STATUSES = (
    "stop_formal_no_claim",
    "repair_formal_pipeline_no_claim",
    "phase7c_formal_fresh_public_repo_validation_passed_no_claim",
)

CLAIM_WORD_RE = re.compile(
    r"\b(winner|lift|selected method|selected strategy|product|default|runtime|deployment|training|route works|beat|beats)\b",
    re.IGNORECASE,
)
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:bucket_nonzero_lt_two|count_1(?!_to_))(?![A-Za-z0-9])")
PRIVATE_VALUE_RE = re.compile(r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-fA-F0-9]{32,}\b|\b\d+\s*-\s*\d+\b")
PRIVATE_KEY_RE = re.compile(
    r"(repo_url|repo_name|owner|commit|sha|path|range|hash|snippet|task_id|row_id|manifest|provenance|run_dir|per_repo|per_task|per_fold)",
    re.IGNORECASE,
)

ALLOWED_PRIVATE_SHAPED_KEYS = {
    "private_rows_read",
    "private_manifests_read",
    "private_provenance_read",
    "runs_directory_read",
    "row_generation_executed",
    "benchmark_rows_generated",
    "pre_row_generation_only",
    "repo_fetch_or_clone_executed",
    "public_repo_fetch_or_clone_executed",
    "source_repo_clone_or_fetch_executed",
    "outcome_rows_scored",
    "private_row_manifest_provenance_reads_public",
    "repo_names_urls_owners_public",
    "exact_commits_shas_public",
    "exact_paths_ranges_hashes_snippets_public",
    "task_ids_row_ids_public",
    "manifests_provenance_run_dirs_public",
    "per_repo_per_task_per_fold_public",
    "full_panel_per_task",
    "max_tasks_per_repo",
    "task_target_min",
    "task_target_max",
    "task_hard_max",
    "repo_target_min",
    "repo_target_max",
    "repo_hard_max",
    "phase7c_statuses_exact",
}

FALSE_OPERATION_KEYS = (
    "private_rows_read",
    "private_manifests_read",
    "private_provenance_read",
    "runs_directory_read",
    "public_repo_fetch_or_clone_executed",
    "source_repo_clone_or_fetch_executed",
    "source_reads_executed",
    "row_generation_executed",
    "benchmark_rows_generated",
    "outcome_scoring_executed",
    "outcome_rows_scored",
    "model_fit_or_training_executed",
    "training_executed",
    "provider_network_llm_used",
    "default_setting_changed",
    "runtime_setting_changed",
    "deployment_setting_changed",
    "replacement_logic_tuned_after_row_or_outcome_effects",
    "labels_changed",
    "caps_changed",
    "evidencecore_semantics_changed",
    "privacy_boundary_changed",
    "no_claim_posture_changed",
)


def build_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "public_scope": {
            "docs_report_only": True,
            "aggregate_protocol_report_only": True,
            "private_row_manifest_provenance_reads_public": False,
        },
        "forbidden_operations": {key: False for key in FALSE_OPERATION_KEYS},
        "input_repair_freeze": {
            "prior_overlap_as_input_ineligibility": True,
            "replacement_before_rows_and_outcomes_required": True,
            "pre_row_generation_only": True,
            "pre_outcome_scoring_only": True,
            "replacement_after_rows_or_outcomes_allowed": False,
            "selection_rule_deterministic_auditable": True,
            "selection_rule_not_performance_based": True,
            "selection_rule_frozen_before_effects": True,
            "selection_rule_summary": "stable_public_candidate_order_then_first_eligible_bucket_only",
        },
        "frozen_phase7a_7c_protocol": {
            "same_seven_labels_exact": list(LABELS),
            "repo_target_min": 8,
            "repo_target_max": 12,
            "repo_hard_max": 16,
            "task_target_min": 80,
            "task_target_max": 120,
            "task_hard_max": 150,
            "max_tasks_per_repo": 20,
            "full_panel_per_task": True,
            "phase7c_statuses_exact": list(PHASE7C_STATUSES),
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
            "privacy_boundary_frozen": True,
            "no_claim_posture_frozen": True,
        },
        "public_reporting_contract": {
            "publication_level": "aggregate_bucket_only",
            "replacement_reporting_level": "aggregate_bucket_only",
            "overlap_reporting_level": "aggregate_bucket_only",
            "singleton_buckets_public": False,
            "repo_names_urls_owners_public": False,
            "exact_commits_shas_public": False,
            "exact_paths_ranges_hashes_snippets_public": False,
            "task_ids_row_ids_public": False,
            "manifests_provenance_run_dirs_public": False,
            "per_repo_per_task_per_fold_public": False,
            "private_details_public": False,
            "claim_wording_public": False,
        },
        "claim_boundary": {
            "method_comparison_claim": False,
            "performance_increase_claim": False,
            "method_winner_claim": False,
            "product_claim": False,
            "default_claim": False,
            "runtime_claim": False,
            "deployment_claim": False,
            "training_claim": False,
            "provider_claim": False,
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "private_inputs_accessed_by_validator": False,
        },
        "next_authorized_action": "phase7e_may_execute_only_after_phase7d_committed_ci_green_and_phase7e_boundary_explicitly_invoked_under_low_resource_no_claim_constraints",
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    if key and PRIVATE_KEY_RE.search(key) and key not in ALLOWED_PRIVATE_SHAPED_KEYS:
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(_scan_public(child, child_path, str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_scan_public(child, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if CLAIM_WORD_RE.search(value):
            errors.append(f"forbidden claim wording at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket term at {path}")
        if PRIVATE_VALUE_RE.search(value):
            errors.append(f"private-shaped value at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE or report.get("status") != STATUS:
        errors.append("identity/status drift")

    scope = report.get("public_scope", {})
    if scope.get("docs_report_only") is not True or scope.get("aggregate_protocol_report_only") is not True:
        errors.append("docs/report-only scope missing")
    if scope.get("private_row_manifest_provenance_reads_public") is not False:
        errors.append("private read publication boundary failed")

    forbidden = report.get("forbidden_operations", {})
    for key in FALSE_OPERATION_KEYS:
        if forbidden.get(key) is not False:
            errors.append(f"forbidden Phase 7D flag not false: {key}")

    repair = report.get("input_repair_freeze", {})
    if repair.get("prior_overlap_as_input_ineligibility") is not True:
        errors.append("prior-overlap input ineligibility missing")
    if repair.get("replacement_before_rows_and_outcomes_required") is not True:
        errors.append("pre-row/pre-outcome replacement constraint missing")
    if repair.get("pre_row_generation_only") is not True or repair.get("pre_outcome_scoring_only") is not True:
        errors.append("replacement must be pre-row and pre-outcome")
    if repair.get("replacement_after_rows_or_outcomes_allowed") is not False:
        errors.append("post-row/outcome replacement must be forbidden")
    if repair.get("selection_rule_deterministic_auditable") is not True:
        errors.append("deterministic/auditable replacement rule missing")
    if repair.get("selection_rule_not_performance_based") is not True or repair.get("selection_rule_frozen_before_effects") is not True:
        errors.append("non-performance replacement freeze missing")

    frozen = report.get("frozen_phase7a_7c_protocol", {})
    if tuple(frozen.get("same_seven_labels_exact", [])) != LABELS:
        errors.append("seven-label drift")
    for key, expected in {
        "repo_target_min": 8,
        "repo_target_max": 12,
        "repo_hard_max": 16,
        "task_target_min": 80,
        "task_target_max": 120,
        "task_hard_max": 150,
        "max_tasks_per_repo": 20,
    }.items():
        if frozen.get(key) != expected:
            errors.append(f"cap drift: {key}")
    if frozen.get("full_panel_per_task") is not True:
        errors.append("full-panel task rule missing")
    if tuple(frozen.get("phase7c_statuses_exact", [])) != PHASE7C_STATUSES:
        errors.append("Phase 7C status drift")
    evidence = frozen.get("evidencecore_rule", {})
    if evidence.get("candidate_found_alone_is_evidence") is not False:
        errors.append("candidate-found evidence boundary drift")
    for key in (
        "success_requires_current_source_read",
        "success_requires_materialization",
        "success_requires_content_digest",
        "success_requires_currentness_reread",
        "success_requires_span_match",
        "success_requires_task_tie",
    ):
        if evidence.get(key) is not True:
            errors.append(f"EvidenceCore rule missing: {key}")
    if evidence.get("stop_abstain_success_required_bucket") != "bucket_zero":
        errors.append("stop/abstain control rule drift")
    if frozen.get("privacy_boundary_frozen") is not True or frozen.get("no_claim_posture_frozen") is not True:
        errors.append("privacy/no-claim freeze missing")

    public_contract = report.get("public_reporting_contract", {})
    if public_contract.get("replacement_reporting_level") != "aggregate_bucket_only" or public_contract.get("overlap_reporting_level") != "aggregate_bucket_only":
        errors.append("aggregate-only replacement/overlap reporting missing")
    for key in (
        "singleton_buckets_public",
        "repo_names_urls_owners_public",
        "exact_commits_shas_public",
        "exact_paths_ranges_hashes_snippets_public",
        "task_ids_row_ids_public",
        "manifests_provenance_run_dirs_public",
        "per_repo_per_task_per_fold_public",
        "private_details_public",
        "claim_wording_public",
    ):
        if public_contract.get(key) is not False:
            errors.append(f"public privacy/claim boundary failed: {key}")

    claim_boundary = report.get("claim_boundary", {})
    for key, value in claim_boundary.items():
        if value is not False:
            errors.append(f"claim boundary failed: {key}")

    next_action = report.get("next_authorized_action", "")
    if "phase7d_committed_ci_green" not in next_action or "phase7e_boundary_explicitly_invoked" not in next_action:
        errors.append("next action must require Phase 7D committed/CI-green and explicit Phase 7E boundary invocation")
    if "low_resource_no_claim_constraints" not in next_action:
        errors.append("next action must preserve low-resource/no-claim constraints")

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

    for flag in ("private_rows_read", "public_repo_fetch_or_clone_executed", "row_generation_executed", "outcome_scoring_executed", "training_executed", "default_setting_changed", "provider_network_llm_used"):
        mutated = copy.deepcopy(base)
        mutated["forbidden_operations"][flag] = True
        checks.append((f"forbidden_flag_rejected_{flag}", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["input_repair_freeze"]["prior_overlap_as_input_ineligibility"] = False
    checks.append(("missing_prior_overlap_ineligibility_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["input_repair_freeze"]["replacement_before_rows_and_outcomes_required"] = False
    checks.append(("missing_pre_row_pre_outcome_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["input_repair_freeze"]["selection_rule_not_performance_based"] = False
    checks.append(("missing_non_performance_rule_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_reporting_contract"]["overlap_reporting_level"] = "detailed"
    checks.append(("missing_aggregate_only_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_reporting_contract"]["example"] = "winner"
    checks.append(("claim_word_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_reporting_contract"]["example_bucket"] = "count_1"
    checks.append(("singleton_bucket_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["method_winner_claim"] = True
    checks.append(("claim_flag_rejected", bool(validate_report(mutated))))

    with tempfile.TemporaryDirectory(prefix="phase7d_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("temp_fixture_valid", not validate_report(loaded)))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7D input-repair protocol-freeze report validator")
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
