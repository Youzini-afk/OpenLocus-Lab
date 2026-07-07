#!/usr/bin/env python3
"""Hard-source dry-run/preflight for interventional evidence acquisition.

This script is local-only and aggregate-only. It does not write private rows,
does not call provider/network services, does not train models, does not change
runtime/default behavior, and does not make a method-winner claim.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
PHASE = "interventional_evidence_acquisition_phase1_hard_source_preflight"
REPORT_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1_hard_source_preflight_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
STATUS = "phase1_hard_source_preflight_no_private_rows"
NEXT_ACTION = "stop/request explicit decision before any confirmed private pilot"

FAMILY_BUCKETS = (
    "same_symbol_support_relation",
    "operation_ambiguity",
    "boundary_condition",
    "helper_dependency_choice",
    "config_or_test_mismatch",
    "distractor_file",
    "nearby_wrong_function",
    "cross_file_symbol",
)
ALLOWED_ACTIONS = (
    "retrieve_bm25",
    "retrieve_symbol_regex",
    "read_top1",
    "read_next_unique_file",
    "read_related_test",
    "stop",
    "abstain",
)
LOCAL_READ_OR_RETRIEVE_ACTIONS = tuple(action for action in ALLOWED_ACTIONS if action not in {"stop", "abstain"})
EVIDENCE_SUCCESS_ACTIONS = ("read_top1", "read_next_unique_file", "read_related_test")
REPORT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "authorization_attestation",
    "source_summary",
    "action_summary",
    "structural_availability",
    "candidate_ambiguity",
    "baseline_non_saturation",
    "evidencecore_summary",
    "privacy_summary",
    "validation_summary",
    "next_authorized_action",
}
PRIVATE_DETAIL_KEYS = {
    "task_id",
    "task_ids",
    "path",
    "paths",
    "exact_path",
    "exact_paths",
    "symbol",
    "symbols",
    "query",
    "queries",
    "range",
    "ranges",
    "snippet",
    "snippets",
    "hash",
    "hashes",
    "private_ref",
    "private_refs",
    "raw_task_detail",
    "raw_task_details",
}
PATH_SHAPED_RE = re.compile(r"(?:^|[\\/])(?:src|tests?|eval|docs|artifacts|runs)[\\/][^\s]+", re.I)
RANGE_SHAPED_RE = re.compile(r"\b(?:line|lines|range)?\s*\d{1,6}\s*-\s*\d{1,6}\b", re.I)
HASH_SHAPED_RE = re.compile(r"\b[a-f0-9]{16,}\b", re.I)


class PreflightError(Exception):
    pass


@dataclass(frozen=True)
class HardTaskShape:
    private_id: str
    family_bucket: str
    private_path: str
    private_symbol: str
    private_query: str
    private_range: str
    candidate_count: int
    unique_file_candidates: int
    symbol_candidates: int
    has_related_test: bool
    materialized_actions: tuple[str, ...]
    successful_actions: tuple[str, ...]


def bucket_count(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count == 1:
        return "count_1"
    if count <= 5:
        return "count_2_to_5"
    if count <= 20:
        return "count_6_to_20"
    if count <= 50:
        return "count_21_to_50"
    return "count_gt_50"


def bucket_rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "rate_unavailable"
    rate = numerator / denominator
    if rate == 0:
        return "rate_0"
    if rate < 0.25:
        return "rate_0_to_25"
    if rate < 0.50:
        return "rate_25_to_50"
    if rate < 0.75:
        return "rate_50_to_75"
    if rate < 1.0:
        return "rate_75_to_100"
    return "rate_1"


def build_hard_task_source() -> list[HardTaskShape]:
    tasks: list[HardTaskShape] = []
    for family_index, family in enumerate(FAMILY_BUCKETS):
        for variant in range(4):
            has_related_test = family in {"boundary_condition", "config_or_test_mismatch"} or (family == "cross_file_symbol" and variant == 0)
            candidate_count = 3 + ((family_index + variant) % 3)
            unique_file_candidates = 2 + ((family_index + variant) % 2)
            symbol_candidates = 1 + ((family_index + variant) % 3)
            successful_actions = _successful_actions_for_family(family, variant)
            tasks.append(
                HardTaskShape(
                    private_id=f"hard-private-{family_index:02d}-{variant:02d}",
                    family_bucket=family,
                    private_path=f"private/local/{family_index:02d}/{variant:02d}.py",
                    private_symbol=f"PrivateSymbol{family_index}_{variant}",
                    private_query=f"private query {family} variant {variant}",
                    private_range=f"{10 + variant}-{14 + variant}",
                    candidate_count=candidate_count,
                    unique_file_candidates=unique_file_candidates,
                    symbol_candidates=symbol_candidates,
                    has_related_test=has_related_test,
                    materialized_actions=("read_top1", "read_next_unique_file") + (("read_related_test",) if has_related_test else ()),
                    successful_actions=successful_actions,
                )
            )
    return tasks


def _successful_actions_for_family(family: str, variant: int) -> tuple[str, ...]:
    if family == "same_symbol_support_relation":
        return ("retrieve_symbol_regex", "read_next_unique_file") if variant % 2 == 0 else ("retrieve_symbol_regex",)
    if family == "operation_ambiguity":
        return ("retrieve_bm25",) if variant == 0 else ("read_next_unique_file",)
    if family == "boundary_condition":
        return ("read_related_test", "read_top1") if variant < 2 else ("read_related_test",)
    if family == "helper_dependency_choice":
        return ("retrieve_symbol_regex", "read_next_unique_file") if variant != 3 else ("read_next_unique_file",)
    if family == "config_or_test_mismatch":
        return ("read_related_test",)
    if family == "distractor_file":
        return ("read_next_unique_file",) if variant < 3 else ("abstain",)
    if family == "nearby_wrong_function":
        return ("retrieve_symbol_regex",) if variant != 1 else ("read_next_unique_file",)
    if family == "cross_file_symbol":
        return ("read_next_unique_file", "retrieve_symbol_regex") if variant < 2 else ("retrieve_symbol_regex",)
    raise PreflightError(f"unknown family bucket: {family}")


def action_available(task: HardTaskShape, action: str) -> bool:
    if action in {"stop", "abstain"}:
        return True
    if action == "retrieve_bm25":
        return task.candidate_count > 0
    if action == "retrieve_symbol_regex":
        return task.symbol_candidates > 0
    if action == "read_top1":
        return task.candidate_count > 0
    if action == "read_next_unique_file":
        return task.unique_file_candidates > 1
    if action == "read_related_test":
        return task.has_related_test
    return False


def action_materializes(task: HardTaskShape, action: str) -> bool:
    return action in task.materialized_actions and action_available(task, action)


def action_success(task: HardTaskShape, action: str) -> bool:
    return action in EVIDENCE_SUCCESS_ACTIONS and action in task.successful_actions and action_materializes(task, action)


def family_balance_ok(tasks: list[HardTaskShape]) -> bool:
    counts = Counter(task.family_bucket for task in tasks)
    return len(tasks) == 32 and set(counts) == set(FAMILY_BUCKETS) and set(counts.values()) == {4}


def structural_counts(tasks: list[HardTaskShape]) -> dict[str, int]:
    return {action: sum(1 for task in tasks if action_available(task, action)) for action in ALLOWED_ACTIONS}


def success_counts(tasks: list[HardTaskShape]) -> dict[str, int]:
    return {action: sum(1 for task in tasks if action_success(task, action)) for action in ALLOWED_ACTIONS}


def materialization_counts(tasks: list[HardTaskShape]) -> dict[str, int]:
    return {action: sum(1 for task in tasks if action_materializes(task, action)) for action in ALLOWED_ACTIONS}


def candidate_found_counts(tasks: list[HardTaskShape]) -> dict[str, int]:
    return {
        "retrieve_bm25": sum(1 for task in tasks if task.candidate_count > 0),
        "retrieve_symbol_regex": sum(1 for task in tasks if task.symbol_candidates > 0),
        "read_top1": sum(1 for task in tasks if task.candidate_count > 0),
        "read_next_unique_file": sum(1 for task in tasks if task.unique_file_candidates > 1),
        "read_related_test": sum(1 for task in tasks if task.has_related_test),
        "stop": 0,
        "abstain": 0,
    }


def build_report(tasks: list[HardTaskShape] | None = None) -> dict[str, Any]:
    tasks = tasks or build_hard_task_source()
    if not family_balance_ok(tasks):
        raise PreflightError("hard source must contain 32 balanced local task shapes")
    family_counts = Counter(task.family_bucket for task in tasks)
    availability = structural_counts(tasks)
    successes = success_counts(tasks)
    materialized = materialization_counts(tasks)
    candidates = candidate_found_counts(tasks)
    candidate_buckets = Counter(bucket_count(task.candidate_count) for task in tasks)
    unique_file_buckets = Counter(bucket_count(task.unique_file_candidates) for task in tasks)
    ambiguous_count = sum(1 for task in tasks if task.candidate_count >= 3 and task.unique_file_candidates > 1)
    materialized_not_success = sum(
        1
        for task in tasks
        for action in LOCAL_READ_OR_RETRIEVE_ACTIONS
        if action_materializes(task, action) and not action_success(task, action)
    )
    best_action, best_successes = max(
        ((action, successes[action]) for action in EVIDENCE_SUCCESS_ACTIONS),
        key=lambda item: (item[1], item[0]),
    )
    saturation = best_successes >= int(len(tasks) * 0.85)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "authorization_attestation": {
            "dry_run_preflight_only": True,
            "private_rows_written": False,
            "provider_network_authorized": False,
            "provider_network_used": False,
            "training_authorized": False,
            "model_training_executed": False,
            "runtime_default_change_authorized": False,
            "runtime_default_changed": False,
            "new_retrieval_channel_family_added": False,
            "method_winner_claimed": False,
            "local_existing_capabilities_only": True,
        },
        "source_summary": {
            "source_kind": "synthetic_local_hard_task_shapes",
            "shape_count_bucket": bucket_count(len(tasks)),
            "family_bucket_count": bucket_count(len(family_counts)),
            "family_balance_ok": True,
            "family_shape_count_buckets": {family: bucket_count(family_counts[family]) for family in FAMILY_BUCKETS},
        },
        "action_summary": {
            "allowed_action_count_bucket": bucket_count(len(ALLOWED_ACTIONS)),
            "local_action_families_only": True,
            "provider_or_network_action_count_bucket": "count_0",
            "confirmed_row_count_bucket": "count_0",
        },
        "structural_availability": {
            action: {
                "eligible_shape_count_bucket": bucket_count(availability[action]),
                "sampled_confirmed_row_count_bucket": "count_0",
                "structural_status": "eligible" if availability[action] > 0 else "structurally_unavailable",
            }
            for action in ALLOWED_ACTIONS
        },
        "candidate_ambiguity": {
            "ambiguous_shape_count_bucket": bucket_count(ambiguous_count),
            "candidate_count_buckets": {name: bucket_count(count) for name, count in sorted(candidate_buckets.items())},
            "unique_file_candidate_buckets": {name: bucket_count(count) for name, count in sorted(unique_file_buckets.items())},
            "distractor_family_present": family_counts["distractor_file"] > 0,
            "nearby_wrong_function_family_present": family_counts["nearby_wrong_function"] > 0,
        },
        "baseline_non_saturation": {
            "best_fixed_action_bucket": "local_read_or_retrieve_action",
            "best_fixed_action_success_rate_bucket": bucket_rate(best_successes, len(tasks)),
            "best_fixed_action_saturation_detected": saturation,
            "best_fixed_action_saturation_no_go": saturation,
            "candidate_source_meaningful_for_private_pilot": not saturation,
            "signal_claim": "no_signal_claim",
            "method_winner_claimed": False,
        },
        "evidencecore_summary": {
            "current_source_required_for_counted_evidence": True,
            "candidate_found_count_buckets": {action: bucket_count(candidates[action]) for action in ALLOWED_ACTIONS},
            "materialized_action_count_buckets": {action: bucket_count(materialized[action]) for action in ALLOWED_ACTIONS},
            "evidence_success_count_buckets": {action: bucket_count(successes[action]) for action in ALLOWED_ACTIONS},
            "materialized_not_success_count_bucket": bucket_count(materialized_not_success),
            "success_is_not_mere_materialization": materialized_not_success > 0,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_written": False,
            "private_task_details_public": False,
            "task_ids_public": False,
            "paths_public": False,
            "symbols_public": False,
            "queries_public": False,
            "ranges_public": False,
            "snippets_public": False,
            "hashes_public": False,
            "provider_payloads_public": False,
        },
        "validation_summary": {
            "route_specific_public_report_validation": "passed",
            "self_test_available": True,
            "public_artifact_privacy_audit_expected": "manual_local_only_not_ci_gate",
        },
        "next_authorized_action": NEXT_ACTION,
    }
    errors = validate_report(report)
    if errors:
        raise PreflightError("generated invalid report: " + "; ".join(errors[:8]))
    return report


def public_leak_errors(value: Any, parent: str = "$", *, key_name: str = "") -> list[str]:
    errors: list[str] = []
    if key_name.lower() in PRIVATE_DETAIL_KEYS:
        errors.append(f"private detail key public at {parent}")
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{parent}.{key}" if parent != "$" else f"$.{key}"
            errors.extend(public_leak_errors(child, child_path, key_name=str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(public_leak_errors(child, f"{parent}[{index}]"))
    elif isinstance(value, str):
        if PATH_SHAPED_RE.search(value) or HASH_SHAPED_RE.search(value) or RANGE_SHAPED_RE.search(value):
            errors.append(f"private detail shaped value public at {parent}")
    return errors


def _check_bool(report: dict[str, Any], path: tuple[str, ...], expected: bool, errors: list[str]) -> None:
    value: Any = report
    for part in path:
        value = value.get(part) if isinstance(value, dict) else None
    if value is not expected:
        errors.append("bad boolean: " + ".".join(path))


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be an object"]
    errors: list[str] = []
    if set(report) != REPORT_KEYS:
        errors.append("report top-level shape drift")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("bad schema version")
    if report.get("phase") != PHASE:
        errors.append("bad phase")
    if report.get("status") != STATUS:
        errors.append("bad status")
    auth = report.get("authorization_attestation", {})
    for key in (
        "private_rows_written",
        "provider_network_authorized",
        "provider_network_used",
        "training_authorized",
        "model_training_executed",
        "runtime_default_change_authorized",
        "runtime_default_changed",
        "new_retrieval_channel_family_added",
        "method_winner_claimed",
    ):
        if auth.get(key) is not False:
            errors.append(f"authorization overclaim: {key}")
    for key in ("dry_run_preflight_only", "local_existing_capabilities_only"):
        if auth.get(key) is not True:
            errors.append(f"missing local/preflight attestation: {key}")
    source = report.get("source_summary", {})
    if source.get("shape_count_bucket") != "count_21_to_50" or source.get("family_bucket_count") != "count_6_to_20" or source.get("family_balance_ok") is not True:
        errors.append("hard source balance failed")
    family_counts = source.get("family_shape_count_buckets", {})
    if set(family_counts) != set(FAMILY_BUCKETS) or any(value != "count_2_to_5" for value in family_counts.values()):
        errors.append("family count bucket drift")
    structural = report.get("structural_availability", {})
    if set(structural) != set(ALLOWED_ACTIONS):
        errors.append("structural availability action drift")
    else:
        for action, item in structural.items():
            if set(item) != {"eligible_shape_count_bucket", "sampled_confirmed_row_count_bucket", "structural_status"}:
                errors.append(f"structural availability shape drift: {action}")
            if item.get("sampled_confirmed_row_count_bucket") != "count_0":
                errors.append(f"confirmed rows sampled in preflight: {action}")
        if structural.get("read_related_test", {}).get("eligible_shape_count_bucket") == "count_0":
            errors.append("read_related_test unavailable in hard source")
    ambiguity = report.get("candidate_ambiguity", {})
    if ambiguity.get("ambiguous_shape_count_bucket") in {None, "count_0"}:
        errors.append("candidate ambiguity absent")
    if ambiguity.get("distractor_family_present") is not True or ambiguity.get("nearby_wrong_function_family_present") is not True:
        errors.append("hard distractor families absent")
    baseline = report.get("baseline_non_saturation", {})
    if baseline.get("best_fixed_action_saturation_detected") is not False or baseline.get("best_fixed_action_saturation_no_go") is not False:
        errors.append("best fixed action saturation no-go")
    if baseline.get("candidate_source_meaningful_for_private_pilot") is not True:
        errors.append("candidate source not meaningful")
    if baseline.get("signal_claim") != "no_signal_claim" or baseline.get("method_winner_claimed") is not False:
        errors.append("method-winner or signal overclaim")
    evidence = report.get("evidencecore_summary", {})
    if evidence.get("current_source_required_for_counted_evidence") is not True:
        errors.append("EvidenceCore currentness requirement missing")
    if evidence.get("success_is_not_mere_materialization") is not True or evidence.get("materialized_not_success_count_bucket") == "count_0":
        errors.append("success/materialization distinction missing")
    candidate_buckets = evidence.get("candidate_found_count_buckets", {})
    materialized_buckets = evidence.get("materialized_action_count_buckets", {})
    evidence_success_buckets = evidence.get("evidence_success_count_buckets", {})
    if set(candidate_buckets) != set(ALLOWED_ACTIONS) or set(materialized_buckets) != set(ALLOWED_ACTIONS) or set(evidence_success_buckets) != set(ALLOWED_ACTIONS):
        errors.append("EvidenceCore action bucket shape drift")
    else:
        for action in ALLOWED_ACTIONS:
            if materialized_buckets[action] == "count_0" and evidence_success_buckets[action] != "count_0":
                errors.append(f"evidence success without materialization: {action}")
        for action in ("retrieve_bm25", "retrieve_symbol_regex"):
            if candidate_buckets[action] == "count_0":
                errors.append(f"retrieval candidate_found absent: {action}")
            if evidence_success_buckets[action] != "count_0":
                errors.append(f"retrieval-only action counted as evidence success: {action}")
    privacy = report.get("privacy_summary", {})
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("publication level drift")
    for key in (
        "private_rows_written",
        "private_task_details_public",
        "task_ids_public",
        "paths_public",
        "symbols_public",
        "queries_public",
        "ranges_public",
        "snippets_public",
        "hashes_public",
        "provider_payloads_public",
    ):
        if privacy.get(key) is not False:
            errors.append(f"privacy boundary failure: {key}")
    action_summary = report.get("action_summary", {})
    if action_summary.get("provider_or_network_action_count_bucket") != "count_0" or action_summary.get("confirmed_row_count_bucket") != "count_0":
        errors.append("action summary overclaim")
    _check_bool(report, ("action_summary", "local_action_families_only"), True, errors)
    if report.get("next_authorized_action") != NEXT_ACTION:
        errors.append("next authorized action drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_report(report)
    if errors:
        raise PreflightError("public report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_report_file(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load report: {exc}"]
    return validate_report(report)


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    tasks = build_hard_task_source()
    report = build_report(tasks)
    checks.append(("task_family_balance", family_balance_ok(tasks)))
    checks.append(("read_related_test_available", structural_counts(tasks)["read_related_test"] > 0))
    checks.append(("success_not_mere_materialization", report["evidencecore_summary"]["success_is_not_mere_materialization"] is True))
    evidence = report["evidencecore_summary"]
    checks.append(("retrieval_candidate_found_not_evidence_success", evidence["candidate_found_count_buckets"]["retrieve_bm25"] != "count_0" and evidence["candidate_found_count_buckets"]["retrieve_symbol_regex"] != "count_0" and evidence["evidence_success_count_buckets"]["retrieve_bm25"] == "count_0" and evidence["evidence_success_count_buckets"]["retrieve_symbol_regex"] == "count_0"))
    checks.append(("no_evidence_success_without_materialization", all(evidence["materialized_action_count_buckets"][action] != "count_0" or evidence["evidence_success_count_buckets"][action] == "count_0" for action in ALLOWED_ACTIONS)))
    checks.append(("clean_report_valid", not validate_report(report)))
    bad_report = copy.deepcopy(report)
    bad_report["source_summary"]["leaky_value_bucket"] = "src/private/example.py"
    checks.append(("privacy_leak_rejected", bool(validate_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["authorization_attestation"]["provider_network_authorized"] = True
    checks.append(("provider_overclaim_rejected", bool(validate_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["authorization_attestation"]["training_authorized"] = True
    checks.append(("training_overclaim_rejected", bool(validate_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["baseline_non_saturation"]["method_winner_claimed"] = True
    checks.append(("method_winner_overclaim_rejected", bool(validate_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["baseline_non_saturation"]["best_fixed_action_saturation_detected"] = True
    bad_report["baseline_non_saturation"]["best_fixed_action_saturation_no_go"] = True
    bad_report["baseline_non_saturation"]["candidate_source_meaningful_for_private_pilot"] = False
    checks.append(("best_fixed_action_saturation_no_go", bool(validate_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["structural_availability"]["read_related_test"]["eligible_shape_count_bucket"] = "count_0"
    checks.append(("read_related_test_unavailability_rejected", bool(validate_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["evidencecore_summary"]["evidence_success_count_buckets"]["retrieve_bm25"] = "count_1"
    checks.append(("retrieval_evidence_success_rejected", bool(validate_report(bad_report))))
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_total": len(checks), "checks_passed": len(checks) - len(failed), "failed_checks": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run synthetic self-tests")
    parser.add_argument("--dry-run", action="store_true", help="write aggregate-only dry-run report")
    parser.add_argument("--validate-report", type=Path, help="validate an existing aggregate report")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT, help="dry-run report output path")
    args = parser.parse_args(argv)

    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "passed" else 1
    if args.validate_report:
        errors = validate_report_file(args.validate_report)
        if errors:
            print("Validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.dry_run:
        report = build_report()
        write_report(report, args.output)
        print(json.dumps({"status": report["status"], "private_rows_written": False, "public_report": str(args.output)}, indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
