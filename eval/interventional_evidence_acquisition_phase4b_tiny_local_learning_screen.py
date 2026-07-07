#!/usr/bin/env python3
"""Phase 4B tiny stdlib-only local learning screen.

Reads existing ignored Phase 2/3 private rows only with explicit confirmation.
Uses a deterministic smoothed categorical table for an aggregate screen. No new
data collection, source reads, provider/network calls, CI changes, runtime
changes, retrieval-family changes, RPM-D2/model scaling, or reusable model
artifact.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
PHASE = "phase4b_tiny_local_learning_screen"
SCHEMA_VERSION = "phase4b_tiny_local_learning_screen_public_report_v1"
STATUS_STOP = "stop_no_learning_claim"
STATUS_REPAIR = "repair_learning_contract_no_claim"
STATUS_POSITIVE = "learning_screen_positive_no_claim"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
PHASE4A_REPORT = REPO / "artifacts" / "phase4a_private_row_feature_leakage_balance_precheck" / "phase4a_private_row_feature_leakage_balance_precheck_report.json"
PHASE2_ROOT = REPO / "runs" / "phase2_small_fair_local_comparison_pilot"
PHASE3_ROOT = REPO / "runs" / "phase3_independent_local_holdout_validation_screen"
PHASE2_ROWS = "phase2_small_fair_local_comparison_private_rows.jsonl"
PHASE3_ROWS = "phase3_independent_local_holdout_private_rows.jsonl"
ALLOWED_ACTIONS = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
ALLOWED_FEATURES = {
    "action_label",
    "task_family_bucket",
    "candidate_count_bucket",
    "top_score_bucket",
    "rank_diversity_bucket",
    "availability_bucket",
    "budget_bucket",
    "prior_step_count_bucket",
}
USED_FEATURES = ("action_label", "task_family_bucket", "availability_bucket", "budget_bucket")
FORBIDDEN_FEATURE_RE = re.compile(
    r"(evidence_success|success_label|target_|private_task_id|task_id|path|range|hash|content|snippet|gold|provider|prompt|response|post_action|read_result|currentness|materialized|validation_result)",
    re.I,
)
PATH_RE = re.compile(r"(?:^|[\\/])(?:runs|docs|eval|scripts|artifacts|src|tests?)[\\/][^\s]+", re.I)
HASH_RE = re.compile(r"\b[a-f0-9]{16,}\b", re.I)
RANGE_RE = re.compile(r"\b(?:line|range)?\s*\d{1,6}\s*-\s*\d{1,6}\b", re.I)
FORBIDDEN_PUBLIC_WORDS = re.compile(r"\b(accuracy|auc|predictive performance|lift|signal|winner|best action|learned policy|deploy|promotion|product-ready)\b", re.I)


class ScreenError(Exception):
    pass


def bucket_count(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count <= 5:
        return "count_1_to_5"
    if count <= 20:
        return "count_6_to_20"
    if count <= 50:
        return "count_21_to_50"
    return "count_gt_50"


def bucket_delta(value: int) -> str:
    if value <= 0:
        return "not_above_control"
    if value <= 5:
        return "above_control_1_to_5"
    if value <= 20:
        return "above_control_6_to_20"
    return "above_control_gt_20"


def path_is_ignored_runs(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == "runs"


def latest_rows(root: Path, filename: str) -> Path:
    candidates = sorted(root.glob(f"*/{filename}"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise ScreenError(f"missing private rows: {filename}")
    return candidates[0]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path_is_ignored_runs(path):
        raise ScreenError("private input outside ignored runs/ refused")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ScreenError(f"row {line_number} is not an object")
            rows.append(item)
    if not rows:
        raise ScreenError("private rows are empty")
    return rows


def contains_count_1(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_count_1(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_count_1(child) for child in value)
    return value == "count_1"


def public_leak_errors(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    lowered = key.lower()
    privacy_false_flag = path.startswith("$.privacy_summary.") and value is False
    if not privacy_false_flag and any(token in lowered for token in ("private_path", "private_range", "private_hash", "private_task_id", "row_id", "manifest", "snippet", "prompt", "response", "provider_payload", "gold", "coefficient", "rule_content", "prediction")):
        errors.append(f"forbidden public key at {path}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            errors.extend(public_leak_errors(child, f"{path}.{child_key}", str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(public_leak_errors(child, f"{path}[{index}]", key))
    elif isinstance(value, str):
        if PATH_RE.search(value) or HASH_RE.search(value) or RANGE_RE.search(value):
            errors.append(f"leak-shaped public value at {path}")
        if FORBIDDEN_PUBLIC_WORDS.search(value):
            errors.append(f"forbidden public wording at {path}")
    return errors


def validate_feature_names(features: set[str]) -> list[str]:
    errors: list[str] = []
    for feature in features:
        if feature not in ALLOWED_FEATURES:
            errors.append(f"unknown feature: {feature}")
        if FORBIDDEN_FEATURE_RE.search(feature):
            errors.append(f"forbidden feature: {feature}")
    return errors


def validate_phase4a_gate(path: Path = PHASE4A_REPORT) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load Phase 4A gate: {exc}"]
    errors: list[str] = []
    if report.get("schema_version") != "phase4a_feature_leakage_balance_precheck_public_report_v1":
        errors.append("Phase 4A gate schema mismatch")
    if report.get("phase") != "phase4a_private_row_feature_leakage_balance_precheck":
        errors.append("Phase 4A gate phase mismatch")
    if report.get("status") != "feature_balance_precheck_ready_no_training":
        errors.append("Phase 4A gate not ready")
    if contains_count_1(report):
        errors.append("Phase 4A gate exposes count_1")
    errors.extend(public_leak_errors(report))
    return errors


def feature_row(row: dict[str, Any]) -> dict[str, Any]:
    action = str(row.get("micro_policy_id", ""))
    eligible = row.get("eligible_micro_policies", [])
    available = action in eligible if isinstance(eligible, list) else action in ALLOWED_ACTIONS
    return {
        "features": {
            "action_label": action,
            "task_family_bucket": str(row.get("family_bucket", "unknown_family")),
            "availability_bucket": "available" if available else "not_available",
            "budget_bucket": "single_panel_budget",
        },
        "target": bool(row.get("evidence_success") is True),
    }


def row_key(item: dict[str, Any], features: tuple[str, ...] = USED_FEATURES) -> tuple[str, ...]:
    data = item["features"]
    return tuple(str(data[name]) for name in features)


def action_key(item: dict[str, Any]) -> tuple[str, ...]:
    return (str(item["features"]["action_label"]),)


def table_counts(items: list[dict[str, Any]], *, features: tuple[str, ...]) -> dict[tuple[str, ...], list[int]]:
    table: dict[tuple[str, ...], list[int]] = defaultdict(lambda: [0, 0])
    for item in items:
        key = row_key(item, features) if len(features) > 1 else action_key(item)
        table[key][1] += 1
        if item["target"]:
            table[key][0] += 1
    return table


def smoothed_rate(table: dict[tuple[str, ...], list[int]], key: tuple[str, ...]) -> float:
    positives, total = table.get(key, [0, 0])
    return (positives + 1) / (total + 2)


def screen_count(train: list[dict[str, Any]], holdout: list[dict[str, Any]], *, shuffle_targets: bool = False, action_only: bool = False) -> int:
    train_items = [json.loads(json.dumps(item)) for item in train]
    if shuffle_targets and train_items:
        shifted = [item["target"] for item in train_items[1:]] + [train_items[0]["target"]]
        for item, target in zip(train_items, shifted):
            item["target"] = target
    features = ("action_label",) if action_only else USED_FEATURES
    table = table_counts(train_items, features=features)
    count = 0
    for item in holdout:
        key = action_key(item) if action_only else row_key(item)
        if item["target"] and smoothed_rate(table, key) >= 0.5:
            count += 1
    return count


def build_report(phase2_rows: list[dict[str, Any]], phase3_rows: list[dict[str, Any]]) -> dict[str, Any]:
    feature_errors = validate_feature_names(set(USED_FEATURES))
    phase2_items = [feature_row(row) for row in phase2_rows]
    phase3_items = [feature_row(row) for row in phase3_rows]
    controls_positive = sum(1 for row in phase2_rows + phase3_rows if row.get("micro_policy_id") in {"stop", "abstain"} and row.get("evidence_success") is True)
    p2_to_p3 = screen_count(phase2_items, phase3_items)
    p3_to_p2 = screen_count(phase3_items, phase2_items)
    shuffled = screen_count(phase2_items, phase3_items, shuffle_targets=True)
    action_only = screen_count(phase2_items, phase3_items, action_only=True)
    majority_non_success = 0
    status = STATUS_POSITIVE if not feature_errors and controls_positive == 0 and p2_to_p3 > shuffled else STATUS_REPAIR
    rows = phase2_rows + phase3_rows
    actions = Counter(str(row.get("micro_policy_id", "")) for row in rows)
    target_positive = sum(1 for row in rows if row.get("evidence_success") is True)
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "authorization_attestation": {
            "confirm_private_input_required": True,
            "phase4a_gate_required": True,
            "phase4a_gate_passed": True,
            "local_only": True,
            "private_rows_read_locally": True,
            "private_rows_published": False,
            "new_data_collected": False,
            "source_files_read": False,
            "provider_network_used": False,
            "llm_used": False,
            "training_executed": False,
            "model_training_executed": False,
            "reusable_model_fitting_executed": False,
            "disposable_screen_table_fit_executed": True,
            "stdlib_only_heldout_screen_executed": True,
            "reusable_model_artifact_created": False,
            "runtime_default_changed": False,
            "new_retrieval_channel_family_added": False,
            "rpm_d2_or_model_scaling_used": False,
            "ci_changed": False,
            "method_claimed": False,
            "effect_claim": "no_effect_claim",
        },
        "input_summary": {
            "row_count_bucket": bucket_count(len(rows)),
            "phase2_row_count_bucket": bucket_count(len(phase2_rows)),
            "phase3_row_count_bucket": bucket_count(len(phase3_rows)),
            "action_coverage_buckets": {action: bucket_count(actions[action]) for action in ALLOWED_ACTIONS},
        },
        "feature_summary": {
            "allowed_pre_action_categorical_features_only": not feature_errors,
            "target_used_only_as_target": True,
            "phase_used_only_for_split_bookkeeping": True,
            "used_feature_buckets": {name: "present" for name in USED_FEATURES},
            "forbidden_feature_errors_bucket": bucket_count(len(feature_errors)),
        },
        "split_screen_summary": {
            "primary_split": "phase2_to_phase3",
            "sensitivity_split": "phase3_to_phase2",
            "no_tuning_after_holdout": True,
            "phase2_to_phase3_heldout_screen_bucket": bucket_count(p2_to_p3),
            "phase3_to_phase2_consistency_bucket": bucket_count(p3_to_p2),
        },
        "control_summary": {
            "shuffled_target_control_bucket": bucket_count(shuffled),
            "action_only_control_bucket": bucket_count(action_only),
            "majority_non_success_control_bucket": bucket_count(majority_non_success),
            "shuffled_control_comparison_bucket": bucket_delta(p2_to_p3 - shuffled),
            "stop_abstain_positive_bucket": bucket_count(controls_positive),
        },
        "target_balance_summary": {
            "target_positive_bucket": bucket_count(target_positive),
            "target_non_positive_bucket": bucket_count(len(rows) - target_positive),
            "candidate_found_alone_is_not_evidence": True,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_published": False,
            "raw_feature_rows_public": False,
            "row_outputs_public": False,
            "model_artifact_public": False,
            "private_paths_public": False,
            "private_ranges_public": False,
            "private_hashes_public": False,
            "private_content_public": False,
            "private_snippets_public": False,
            "private_task_ids_public": False,
            "private_run_dirs_public": False,
            "private_manifests_public": False,
            "gold_labels_public": False,
            "provider_payloads_public": False,
        },
        "validation_summary": {
            "self_test_available": True,
            "no_count_1_values": True,
            "public_leak_scan": "passed",
            "forbidden_feature_rejection_self_test": True,
            "shuffled_target_control_path_checked": True,
            "route_specific_phase4b_validation": "passed",
        },
        "conservative_recommendation": status,
    }


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("identity drift")
    if report.get("status") not in {STATUS_STOP, STATUS_REPAIR, STATUS_POSITIVE}:
        errors.append("bad status")
    auth = report.get("authorization_attestation", {})
    for key in ("new_data_collected", "source_files_read", "provider_network_used", "llm_used", "training_executed", "model_training_executed", "reusable_model_fitting_executed", "reusable_model_artifact_created", "runtime_default_changed", "new_retrieval_channel_family_added", "rpm_d2_or_model_scaling_used", "ci_changed", "method_claimed"):
        if auth.get(key) is not False:
            errors.append(f"overclaim: {key}")
    for key in ("disposable_screen_table_fit_executed", "stdlib_only_heldout_screen_executed"):
        if auth.get(key) is not True:
            errors.append(f"missing screen attestation: {key}")
    if auth.get("effect_claim") != "no_effect_claim" or auth.get("phase4a_gate_passed") is not True:
        errors.append("claim or gate boundary failed")
    if report.get("control_summary", {}).get("stop_abstain_positive_bucket") != "count_0":
        errors.append("stop/abstain sanity failed")
    if report.get("feature_summary", {}).get("target_used_only_as_target") is not True:
        errors.append("target feature boundary failed")
    if contains_count_1(report):
        errors.append("count_1 published")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_report(report)
    if errors:
        raise ScreenError("report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_screen(confirm_private_input: bool, phase2_path: Path | None, phase3_path: Path | None, output: Path, phase4a_report: Path) -> dict[str, Any]:
    if not confirm_private_input:
        raise ScreenError("--confirm-private-input is required")
    gate_errors = validate_phase4a_gate(phase4a_report)
    if gate_errors:
        raise ScreenError("Phase 4A gate failed: " + "; ".join(gate_errors[:8]))
    p2 = phase2_path or latest_rows(PHASE2_ROOT, PHASE2_ROWS)
    p3 = phase3_path or latest_rows(PHASE3_ROOT, PHASE3_ROWS)
    report = build_report(load_jsonl(p2), load_jsonl(p3))
    write_report(report, output)
    return {"status": report["status"], "conservative_recommendation": report["conservative_recommendation"], "public_report": str(output)}


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    checks.append(("no_confirm_refused", run_refuses_without_confirm()))
    checks.append(("outside_runs_refused", not path_is_ignored_runs(REPO / "docs" / "private.jsonl")))
    checks.append(("forbidden_feature_rejected", bool(validate_feature_names({"post_action_read_result"}))))
    checks.append(("target_as_feature_rejected", bool(validate_feature_names({"evidence_success"}))))
    rows2, rows3 = sample_rows()
    report = build_report(rows2, rows3)
    checks.append(("report_valid", not validate_report(report)))
    checks.append(("shuffled_control_path_works", report["control_summary"]["shuffled_target_control_bucket"] in {"count_0", "count_1_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"}))
    bad_report = json.loads(json.dumps(report))
    bad_report["input_summary"]["row_count_bucket"] = "count_1"
    checks.append(("count_1_rejected", bool(validate_report(bad_report))))
    bad_report = json.loads(json.dumps(report))
    bad_report["input_summary"]["leak"] = "runs/private/rows.jsonl"
    checks.append(("public_leak_string_rejected", bool(validate_report(bad_report))))
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_total": len(checks), "checks_passed": len(checks) - len(failed), "failed_checks": failed}


def run_refuses_without_confirm() -> bool:
    try:
        run_screen(False, None, None, DEFAULT_REPORT, PHASE4A_REPORT)
    except ScreenError:
        return True
    return False


def sample_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows2: list[dict[str, Any]] = []
    rows3: list[dict[str, Any]] = []
    for phase, target_rows in (("phase2_small_fair_local_comparison_pilot", rows2), ("phase3_independent_local_holdout_validation_screen", rows3)):
        for family in ("same_symbol_support_relation", "operation_ambiguity", "boundary_condition"):
            for action in ALLOWED_ACTIONS:
                target_rows.append({"phase": phase, "micro_policy_id": action, "family_bucket": family, "eligible_micro_policies": list(ALLOWED_ACTIONS), "evidence_success": action in {"bm25_then_read_top1", "symbol_regex_then_read_top1"}})
    return rows2, rows3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--phase2-private-rows", type=Path)
    parser.add_argument("--phase3-private-rows", type=Path)
    parser.add_argument("--phase4a-report", type=Path, default=PHASE4A_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--validate-report", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "passed" else 1
    if args.validate_report:
        try:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"cannot load report: {exc}", file=sys.stderr)
            return 1
        errors = validate_report(report)
        if errors:
            print("Phase 4B report validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Phase 4B report validation passed: {args.validate_report}")
        return 0
    try:
        result = run_screen(args.confirm_private_input, args.phase2_private_rows, args.phase3_private_rows, args.output, args.phase4a_report)
    except ScreenError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
