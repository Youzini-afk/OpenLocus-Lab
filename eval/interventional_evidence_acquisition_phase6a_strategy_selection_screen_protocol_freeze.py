#!/usr/bin/env python3
"""Phase 6A strategy-selection screen protocol freeze validator.

Design-only helper: validates the public Phase 6A report shape. It does not read
private rows, read source, create tasks/repos, fit models, or execute a screen.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO / "artifacts" / "phase6a_strategy_selection_screen_protocol_freeze" / "phase6a_strategy_selection_screen_protocol_freeze_report.json"
SCHEMA_VERSION = "phase6a_strategy_selection_screen_protocol_freeze_report_v1"
PHASE = "interventional_evidence_acquisition_phase6a_strategy_selection_screen_protocol_freeze"
STATUS = "phase6a_strategy_selection_screen_protocol_freeze_no_claim"
LABELS = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
FORBIDDEN_PUBLIC_WORDS = (
    "winner",
    "lift",
    "product",
    "default",
    "runtime",
    "training",
    "selected method",
)
PRIVATE_KEY_RE = re.compile(r"(task_id|path|range|hash|snippet|run_dir|manifest|row)", re.IGNORECASE)
PRIVATE_VALUE_RE = re.compile(r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-f0-9]{32,}\b|\b\d+\s*-\s*\d+\b", re.IGNORECASE)


def build_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "execution_boundary": {
            "design_only": True,
            "private_rows_read": False,
            "source_reads_executed": False,
            "new_tasks_or_repos_created": False,
            "model_fit_executed": False,
            "screen_execution_executed": False,
            "ci_or_workflow_added": False,
        },
        "phase6b_frozen_screen_design": {
            "input_source": "existing_ignored_phase5b_rows_only_after_explicit_future_confirmation",
            "screen_scale": "tiny_repo_heldout_screen",
            "same_seven_labels_exact": list(LABELS),
            "split_rule": "repo_heldout_no_repo_overlap_between_fit_and_check_slices",
            "feature_rule": "pre_action_aggregate_or_action_only_fields_no_task_target_material",
            "stdlib_only": True,
            "baselines_exact": [
                "action_only_table",
                "shuffled_repo_heldout_control",
                "fixed_label_controls",
            ],
        },
        "hard_stop_conditions": {
            "phase6a_private_read_would_stop": True,
            "phase6a_source_read_would_stop": True,
            "phase6a_new_task_or_repo_creation_would_stop": True,
            "phase6a_model_fit_would_stop": True,
            "phase6a_execution_would_stop": True,
            "phase6b_repo_overlap_between_slices_would_stop": True,
            "phase6b_uses_non_frozen_labels_would_stop": True,
            "phase6b_public_private_leak_or_singleton_bucket_would_stop": True,
            "phase6b_stop_or_abstain_success_nonzero_would_stop": True,
            "phase6b_post_outcome_tuning_would_stop": True,
            "phase6b_new_provider_or_remote_call_would_stop": True,
        },
        "public_report_contract": {
            "publication_level": "aggregate_only",
            "raw_private_rows_public": False,
            "raw_task_ids_public": False,
            "paths_public": False,
            "ranges_public": False,
            "hashes_public": False,
            "snippets_public": False,
            "run_dirs_public": False,
            "manifests_public": False,
            "singleton_buckets_public": False,
            "per_repo_or_per_task_details_public": False,
            "claim_level": "no_claim_protocol_freeze_only",
        },
        "authorization_denials": {
            "provider_or_remote_call_authorized": False,
            "model_fit_authorized": False,
            "release_setting_change_authorized": False,
            "route_promotion_authorized": False,
            "new_retrieval_family_authorized": False,
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "private_inputs_accessed_by_validator": False,
        },
        "next_authorized_action": "phase6b_runner_may_be_written_only_after_phase6a_is_green_and_phase6b_boundary_is_explicitly_invoked_under_low_resource_no_claim_constraints",
    }


def _scan_public(value: Any, parent: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    if PRIVATE_KEY_RE.search(key) and key not in {
        "private_rows_read",
        "raw_private_rows_public",
        "raw_task_ids_public",
        "paths_public",
        "ranges_public",
        "hashes_public",
        "snippets_public",
        "run_dirs_public",
        "manifests_public",
        "phase6b_public_private_leak_or_singleton_bucket_would_stop",
    }:
        errors.append(f"private-shaped key at {parent}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            errors.extend(_scan_public(child, f"{parent}.{child_key}" if parent != "$" else f"$.{child_key}", str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_scan_public(child, f"{parent}[{index}]", ""))
    elif isinstance(value, str):
        lowered = value.lower()
        for word in FORBIDDEN_PUBLIC_WORDS:
            if word in lowered:
                errors.append(f"forbidden claim word at {parent}: {word}")
        if "count_1" in lowered or PRIVATE_VALUE_RE.search(value):
            errors.append(f"private-shaped or singleton value at {parent}")
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
    for key in ("private_rows_read", "source_reads_executed", "new_tasks_or_repos_created", "model_fit_executed", "screen_execution_executed", "ci_or_workflow_added"):
        if boundary.get(key) is not False:
            errors.append(f"Phase 6A execution boundary failed: {key}")
    design = report.get("phase6b_frozen_screen_design", {})
    if tuple(design.get("same_seven_labels_exact", [])) != LABELS:
        errors.append("seven-label freeze drift")
    if design.get("stdlib_only") is not True:
        errors.append("stdlib-only design missing")
    if set(design.get("baselines_exact", [])) != {"action_only_table", "shuffled_repo_heldout_control", "fixed_label_controls"}:
        errors.append("baseline design drift")
    privacy = report.get("public_report_contract", {})
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("aggregate-only contract missing")
    for key in ("raw_private_rows_public", "raw_task_ids_public", "paths_public", "ranges_public", "hashes_public", "snippets_public", "run_dirs_public", "manifests_public", "singleton_buckets_public", "per_repo_or_per_task_details_public"):
        if privacy.get(key) is not False:
            errors.append(f"privacy contract failed: {key}")
    auth = report.get("authorization_denials", {})
    for key in ("provider_or_remote_call_authorized", "model_fit_authorized", "release_setting_change_authorized", "route_promotion_authorized", "new_retrieval_family_authorized"):
        if auth.get(key) is not False:
            errors.append(f"authorization denial failed: {key}")
    hard_stop = report.get("hard_stop_conditions")
    if not isinstance(hard_stop, dict):
        errors.append("hard_stop_conditions must be an object")
    else:
        for key, value in hard_stop.items():
            if not str(key).endswith("_would_stop"):
                errors.append(f"hard-stop key must be conditional: {key}")
            if value is not True:
                errors.append(f"hard-stop condition must be true: {key}")
    next_action = report.get("next_authorized_action", "")
    if "phase6a_is_green" not in next_action or "phase6b_boundary_is_explicitly_invoked" not in next_action:
        errors.append("next_authorized_action must require green Phase 6A and explicit Phase 6B boundary invocation")
    if "separate_explicit_decision" in next_action:
        errors.append("next_authorized_action must not over-require separate user decision")
    errors.extend(_scan_public(report))
    return sorted(set(errors))


def write_report(output: Path = REPORT_PATH) -> None:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise SystemExit("generated report invalid: " + "; ".join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks: list[tuple[str, bool]] = []
    checks.append(("base_report_valid", not validate_report(report)))
    mutated = copy.deepcopy(report)
    mutated["execution_boundary"]["private_rows_read"] = True
    checks.append(("private_read_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(report)
    mutated["phase6b_frozen_screen_design"]["same_seven_labels_exact"] = list(LABELS[:-1])
    checks.append(("label_drift_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(report)
    mutated["public_report_contract"]["paths_public"] = True
    checks.append(("privacy_flag_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(report)
    mutated["public_report_contract"]["claim_level"] = "winner"
    checks.append(("claim_word_rejected", bool(validate_report(mutated))))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate/generate Phase 6A protocol-freeze report")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
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
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
