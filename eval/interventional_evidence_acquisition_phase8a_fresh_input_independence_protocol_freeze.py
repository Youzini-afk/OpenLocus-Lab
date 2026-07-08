#!/usr/bin/env python3
"""Phase 8A fresh-input independence protocol freeze report writer/validator.

Docs/report-only helper for the public Phase 8A protocol report. It validates
only the aggregate no-claim protocol shape. It does not read private inputs,
ignored runs, manifests, repositories, source files, task material, candidates,
rows, outcomes, or network resources; it only writes or validates the public
JSON report supplied by the caller.
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
PHASE = "phase8a_fresh_input_independence_protocol_freeze"
STATUS = "phase8a_protocol_freeze_no_execution_no_claim"
SCHEMA_VERSION = "phase8a_fresh_input_independence_protocol_freeze_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"

PRIOR_PHASES = ("phase5b", "phase7b", "phase7c", "phase7e")

CLAIM_WORD_RE = re.compile(
    r"\b(signal|winner|lift|selected method|method selected|selected strategy|product|default|runtime|deployment|provider|training|data[- ]usage|route works|beat|beats)\b",
    re.IGNORECASE,
)
INDEPENDENCE_ACHIEVED_RE = re.compile(
    r"\b(independence (?:achieved|passed|validated|repaired)|independent inputs achieved|freshness passed)\b",
    re.IGNORECASE,
)
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:bucket_nonzero_lt_two|count_1(?!_to_))(?![A-Za-z0-9])")
PRIVATE_VALUE_RE = re.compile(r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-fA-F0-9]{32,}\b|\b\d+\s*-\s*\d+\b")
PRIVATE_KEY_RE = re.compile(
    r"(repo_url|repo_name|owner|commit|sha|path|range|hash|snippet|task_id|row_id|manifest|run_dir|per_repo|per_task|candidate|registry|clone_origin|source_repo)",
    re.IGNORECASE,
)

ALLOWED_PRIVATE_SHAPED_KEYS = {
    "private_input_reads_executed",
    "ignored_runs_reads_executed",
    "manifest_reads_executed",
    "public_repo_fetch_or_clone_executed",
    "source_reads_executed",
    "task_generation_executed",
    "candidate_registry_population_executed",
    "row_outcome_scoring_executed",
    "model_training_provider_llm_runtime_default_product_method_claims_executed",
    "candidate_source_registry_under_ignored_runs_in_phase8b_only",
    "candidate_registry_public",
    "repo_names_urls_owners_public",
    "commits_shas_public",
    "paths_ranges_hashes_snippets_public",
    "task_ids_row_ids_public",
    "manifest_paths_public",
    "run_dirs_public",
    "per_repo_per_task_details_public",
    "normalized_url_forms_required",
    "owner_name_required",
    "fork_source_repo_required_if_detectable",
    "commit_sha_required",
    "clone_origin_required",
    "exact_paths_ranges_hashes_required",
    "task_ids_required",
    "max_candidate_repos_inspected",
    "target_accepted_repo_min",
    "target_accepted_repo_max",
    "future_task_hard_max_if_separately_allowed",
    "allowed_unavailable_sha",
}

FALSE_OPERATION_KEYS = (
    "private_input_reads_executed",
    "ignored_runs_reads_executed",
    "manifest_reads_executed",
    "public_repo_fetch_or_clone_executed",
    "source_reads_executed",
    "task_generation_executed",
    "candidate_registry_population_executed",
    "row_outcome_scoring_executed",
    "model_fit_or_training_executed",
    "provider_network_llm_used",
    "runtime_setting_changed",
    "default_setting_changed",
    "product_or_method_claim_made",
)


def build_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "public_scope": {
            "docs_report_only": True,
            "aggregate_protocol_report_only": True,
            "future_contract_only": True,
            "independence_achieved": False,
            "independence_passed": False,
            "independence_validated": False,
            "independence_repaired": False,
            "phase7e_repair_loop_forbidden": True,
        },
        "forbidden_operations": {key: False for key in FALSE_OPERATION_KEYS},
        "phase8b_contract": {
            "input_construction_audit_first_not_scoring": True,
            "candidate_source_registry_under_ignored_runs_in_phase8b_only": True,
            "candidate_registry_public": False,
            "explicit_prior_phase_exclusion_required": {phase: True for phase in PRIOR_PHASES},
            "strict_comparable_identity_required": {
                "normalized_url_forms_required": True,
                "owner_name_required": True,
                "fork_source_repo_required_if_detectable": True,
                "commit_sha_required": True,
                "clone_origin_required": True,
                "package_module_identity_required_where_available": True,
                "exact_paths_ranges_hashes_required": True,
                "task_ids_required": True,
                "file_family_closeness_required_if_privately_detectable": True,
            },
            "attempt_budget": {
                "max_independent_construction_attempts": 2,
                "max_candidate_repos_inspected": 16,
                "target_accepted_repo_min": 8,
                "target_accepted_repo_max": 12,
                "future_task_hard_max_if_separately_allowed": 150,
                "unbounded_attempts_allowed": False,
            },
            "replacement_policy": {
                "only_before_outcome_scoring": True,
                "allowed_clone_failure": True,
                "allowed_unavailable_sha": True,
                "allowed_insufficient_eligible_files": True,
                "allowed_failed_independence_or_materialization_precheck": True,
                "after_evidence_outcomes_allowed": False,
                "performance_based_replacement_allowed": False,
            },
            "hard_stops": {
                "overlap_nonzero": True,
                "comparable_identity_cannot_be_established": True,
                "accepted_task_count_cannot_be_reached_without_loosening_freshness": True,
                "public_report_would_need_exact_private_details": True,
                "any_scoring_before_input_independence_audit_passes": True,
            },
        },
        "public_reporting_contract": {
            "publication_level": "aggregate_bucket_only",
            "singleton_buckets_public": False,
            "repo_names_urls_owners_public": False,
            "commits_shas_public": False,
            "paths_ranges_hashes_snippets_public": False,
            "task_ids_row_ids_public": False,
            "manifest_paths_public": False,
            "run_dirs_public": False,
            "per_repo_per_task_details_public": False,
            "private_details_public": False,
        },
        "claim_boundary": {
            "signal_claim": False,
            "winner_claim": False,
            "lift_claim": False,
            "method_selected_claim": False,
            "product_claim": False,
            "default_claim": False,
            "runtime_claim": False,
            "provider_claim": False,
            "training_claim": False,
            "data_usage_claim": False,
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "private_inputs_accessed_by_validator": False,
        },
        "next_authorized_action": "phase8b_may_only_construct_and_audit_inputs_first_no_scoring_until_input_independence_audit_passes_no_phase7e_repair_loop",
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
        if INDEPENDENCE_ACHIEVED_RE.search(value):
            errors.append(f"independence-achieved wording at {path}")
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
    for key in ("docs_report_only", "aggregate_protocol_report_only", "future_contract_only", "phase7e_repair_loop_forbidden"):
        if scope.get(key) is not True:
            errors.append(f"public scope missing: {key}")
    for key in ("independence_achieved", "independence_passed", "independence_validated", "independence_repaired"):
        if scope.get(key) is not False:
            errors.append(f"independence status drift: {key}")

    forbidden = report.get("forbidden_operations", {})
    for key in FALSE_OPERATION_KEYS:
        if forbidden.get(key) is not False:
            errors.append(f"forbidden Phase 8A operation flag not false: {key}")

    contract = report.get("phase8b_contract", {})
    if contract.get("input_construction_audit_first_not_scoring") is not True:
        errors.append("Phase 8B must audit input construction before scoring")
    if contract.get("candidate_source_registry_under_ignored_runs_in_phase8b_only") is not True or contract.get("candidate_registry_public") is not False:
        errors.append("candidate registry boundary missing")
    exclusions = contract.get("explicit_prior_phase_exclusion_required", {})
    for phase in PRIOR_PHASES:
        if exclusions.get(phase) is not True:
            errors.append(f"missing explicit prior phase exclusion: {phase}")

    identity = contract.get("strict_comparable_identity_required", {})
    for key in (
        "normalized_url_forms_required",
        "owner_name_required",
        "fork_source_repo_required_if_detectable",
        "commit_sha_required",
        "clone_origin_required",
        "package_module_identity_required_where_available",
        "exact_paths_ranges_hashes_required",
        "task_ids_required",
        "file_family_closeness_required_if_privately_detectable",
    ):
        if identity.get(key) is not True:
            errors.append(f"strict comparable identity requirement missing: {key}")

    budget = contract.get("attempt_budget", {})
    if budget.get("max_independent_construction_attempts") != 2:
        errors.append("attempt budget must be max 2")
    if budget.get("max_candidate_repos_inspected") != 16:
        errors.append("candidate repo inspection cap must be 16")
    if budget.get("target_accepted_repo_min") != 8 or budget.get("target_accepted_repo_max") != 12:
        errors.append("accepted repo target must be 8 to 12")
    if budget.get("future_task_hard_max_if_separately_allowed") != 150:
        errors.append("future task hard max must remain 150 if scoring is separately allowed")
    if budget.get("unbounded_attempts_allowed") is not False:
        errors.append("unbounded attempts must be forbidden")

    replacement = contract.get("replacement_policy", {})
    for key in (
        "only_before_outcome_scoring",
        "allowed_clone_failure",
        "allowed_unavailable_sha",
        "allowed_insufficient_eligible_files",
        "allowed_failed_independence_or_materialization_precheck",
    ):
        if replacement.get(key) is not True:
            errors.append(f"replacement policy missing: {key}")
    if replacement.get("after_evidence_outcomes_allowed") is not False or replacement.get("performance_based_replacement_allowed") is not False:
        errors.append("post-outcome/performance replacement must be forbidden")

    hard_stops = contract.get("hard_stops", {})
    for key in (
        "overlap_nonzero",
        "comparable_identity_cannot_be_established",
        "accepted_task_count_cannot_be_reached_without_loosening_freshness",
        "public_report_would_need_exact_private_details",
        "any_scoring_before_input_independence_audit_passes",
    ):
        if hard_stops.get(key) is not True:
            errors.append(f"hard stop missing: {key}")

    public_contract = report.get("public_reporting_contract", {})
    if public_contract.get("publication_level") != "aggregate_bucket_only":
        errors.append("aggregate-only publication level missing")
    for key in (
        "singleton_buckets_public",
        "repo_names_urls_owners_public",
        "commits_shas_public",
        "paths_ranges_hashes_snippets_public",
        "task_ids_row_ids_public",
        "manifest_paths_public",
        "run_dirs_public",
        "per_repo_per_task_details_public",
        "private_details_public",
    ):
        if public_contract.get(key) is not False:
            errors.append(f"public privacy boundary failed: {key}")

    for key, value in report.get("claim_boundary", {}).items():
        if value is not False:
            errors.append(f"claim boundary failed: {key}")

    next_action = str(report.get("next_authorized_action", ""))
    if "construct_and_audit_inputs_first" not in next_action or "no_scoring_until_input_independence_audit_passes" not in next_action:
        errors.append("next action must forbid scoring before input independence audit")
    if "no_phase7e_repair_loop" not in next_action:
        errors.append("next action must forbid another Phase 7E repair loop")

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

    for flag in ("private_input_reads_executed", "ignored_runs_reads_executed", "manifest_reads_executed", "public_repo_fetch_or_clone_executed", "source_reads_executed", "task_generation_executed", "candidate_registry_population_executed", "row_outcome_scoring_executed", "provider_network_llm_used"):
        mutated = copy.deepcopy(base)
        mutated["forbidden_operations"][flag] = True
        checks.append((f"forbidden_flag_rejected_{flag}", bool(validate_report(mutated))))

    for key in ("independence_achieved", "independence_passed", "independence_validated", "independence_repaired"):
        mutated = copy.deepcopy(base)
        mutated["public_scope"][key] = True
        checks.append((f"independence_status_rejected_{key}", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["next_authorized_action"] = "independence achieved; scoring may proceed"
    checks.append(("independence_achieved_wording_rejected", bool(validate_report(mutated))))

    for phase in PRIOR_PHASES:
        mutated = copy.deepcopy(base)
        mutated["phase8b_contract"]["explicit_prior_phase_exclusion_required"].pop(phase)
        checks.append((f"missing_prior_exclusion_rejected_{phase}", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase8b_contract"]["strict_comparable_identity_required"]["normalized_url_forms_required"] = False
    checks.append(("missing_strict_comparable_identity_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase8b_contract"]["attempt_budget"]["max_independent_construction_attempts"] = 3
    checks.append(("too_high_attempt_budget_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase8b_contract"]["attempt_budget"]["unbounded_attempts_allowed"] = True
    checks.append(("unbounded_attempts_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["phase8b_contract"]["hard_stops"]["overlap_nonzero"] = False
    checks.append(("missing_overlap_hard_stop_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_reporting_contract"]["example_bucket"] = "count_1"
    checks.append(("singleton_bucket_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_reporting_contract"]["example_value"] = "C:/private/repo/file.py"
    checks.append(("private_shaped_public_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["public_reporting_contract"]["example"] = "winner"
    checks.append(("claim_word_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["claim_boundary"]["signal_claim"] = True
    checks.append(("claim_flag_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["next_authorized_action"] = "phase8b_may_score_now"
    checks.append(("next_action_scoring_before_audit_rejected", bool(validate_report(mutated))))

    with tempfile.TemporaryDirectory(prefix="phase8a_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("temp_fixture_valid", not validate_report(loaded)))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 8A fresh-input independence protocol-freeze report validator")
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
