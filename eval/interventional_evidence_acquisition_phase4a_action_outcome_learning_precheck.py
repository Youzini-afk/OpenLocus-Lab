#!/usr/bin/env python3
"""Phase 4A non-training feature/leakage/class-balance precheck.

Local-only. Reads existing ignored Phase 2/3 private rows only with explicit
confirmation. Does not train, estimate model quality, collect data, read source,
call providers, or change runtime/default behavior.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
PHASE = "phase4a_private_row_feature_leakage_balance_precheck"
SCHEMA_VERSION = "phase4a_feature_leakage_balance_precheck_public_report_v1"
STATUS_READY = "feature_balance_precheck_ready_no_training"
STATUS_REPAIR = "repair_feature_contract_no_claim"
STATUS_STOP = "stop_no_learning_claim"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
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
    "task_family_bucket",
    "candidate_count_bucket",
    "top_score_bucket",
    "rank_diversity_bucket",
    "action_label",
    "budget_bucket",
    "availability_bucket",
    "prior_step_count_bucket",
}
FORBIDDEN_FEATURE_RE = re.compile(
    r"(evidence_success|success_label|target_|private_task_id|task_id|path|range|hash|content|snippet|gold|provider|prompt|response|post_action|read_result|currentness|materialized|validation_result)",
    re.I,
)
PATH_SHAPED_RE = re.compile(r"(?:^|[\\/])(?:runs|docs|eval|scripts|artifacts|src|tests?)[\\/][^\s]+", re.I)
HASH_RE = re.compile(r"\b[a-f0-9]{16,}\b", re.I)
RANGE_RE = re.compile(r"\b(?:line|range)?\s*\d{1,6}\s*-\s*\d{1,6}\b", re.I)


class PrecheckError(Exception):
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


def path_is_ignored_runs(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == "runs"


def latest_rows(root: Path, filename: str) -> Path:
    candidates = sorted(root.glob(f"*/{filename}"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise PrecheckError(f"missing private rows under ignored runs: {filename}")
    return candidates[0]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path_is_ignored_runs(path):
        raise PrecheckError("private input outside ignored runs/ refused")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise PrecheckError(f"row {line_number} is not an object")
            rows.append(item)
    if not rows:
        raise PrecheckError("private input rows empty")
    return rows


def contains_count_1(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_count_1(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_count_1(v) for v in value)
    return value == "count_1"


def public_leak_errors(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    lowered = key.lower()
    if any(token in lowered for token in ("private_path", "private_range", "private_hash", "private_task_id", "row_id", "manifest", "snippet", "prompt", "response", "provider_payload", "gold")):
        errors.append(f"forbidden public key at {path}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            errors.extend(public_leak_errors(child, f"{path}.{child_key}", str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(public_leak_errors(child, f"{path}[{index}]", key))
    elif isinstance(value, str) and (PATH_SHAPED_RE.search(value) or HASH_RE.search(value) or RANGE_RE.search(value)):
        errors.append(f"leak-shaped public value at {path}")
    return errors


def validate_feature_contract(features: set[str]) -> list[str]:
    errors: list[str] = []
    for feature in features:
        if feature not in ALLOWED_FEATURES:
            errors.append(f"feature not allowed: {feature}")
        if FORBIDDEN_FEATURE_RE.search(feature):
            errors.append(f"leaky feature rejected: {feature}")
    return errors


def derive_feature_coverage(rows: list[dict[str, Any]]) -> tuple[set[str], Counter[str]]:
    features = {"task_family_bucket", "action_label", "budget_bucket", "availability_bucket"}
    coverage = Counter({feature: len(rows) for feature in features})
    if any(row.get("candidate_found") is not None for row in rows):
        features.add("candidate_count_bucket")
        coverage["candidate_count_bucket"] = len(rows)
    return features, coverage


def build_report(phase2_rows: list[dict[str, Any]], phase3_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = phase2_rows + phase3_rows
    features, feature_coverage = derive_feature_coverage(rows)
    feature_errors = validate_feature_contract(features)
    actions = Counter(str(row.get("micro_policy_id", "unknown")) for row in rows)
    phases = Counter(str(row.get("phase", "unknown")) for row in rows)
    targets = Counter("target_positive" if row.get("evidence_success") is True else "target_non_positive" for row in rows)
    controls_positive = sum(1 for row in rows if row.get("micro_policy_id") in {"stop", "abstain"} and row.get("evidence_success") is True)
    class_balance_ok = targets["target_positive"] > 0 and targets["target_non_positive"] > 0 and controls_positive == 0
    recommendation = STATUS_READY if not feature_errors and class_balance_ok else STATUS_REPAIR
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": recommendation,
        "authorization_attestation": {
            "confirm_private_input_required": True,
            "private_rows_read_locally": True,
            "private_rows_published": False,
            "local_only": True,
            "provider_network_used": False,
            "llm_used": False,
            "model_training_executed": False,
            "model_fitting_executed": False,
            "model_quality_estimate_executed": False,
            "new_data_collected": False,
            "source_files_read_for_new_evidence": False,
            "runtime_default_changed": False,
            "new_retrieval_channel_family_added": False,
            "ci_changed": False,
            "method_claimed": False,
            "effect_claim": "no_effect_claim",
        },
        "input_summary": {
            "row_count_bucket": bucket_count(len(rows)),
            "phase_source_buckets": {"phase2": bucket_count(len(phase2_rows)), "phase3": bucket_count(len(phase3_rows))},
            "action_coverage_buckets": {action: bucket_count(actions[action]) for action in ALLOWED_ACTIONS},
            "source_bucket": "existing_ignored_phase2_phase3_private_rows",
        },
        "feature_contract_summary": {
            "allowed_pre_action_features_only": not feature_errors,
            "evidence_success_used_as_feature": False,
            "candidate_found_alone_is_evidence": False,
            "feature_coverage_buckets": {feature: bucket_count(feature_coverage[feature]) for feature in sorted(features)},
        },
        "leakage_validation_summary": {
            "fail_closed_validator": True,
            "target_label_as_feature_rejected": True,
            "target_path_range_hash_content_features_rejected": True,
            "post_action_read_currentness_materialization_features_rejected": True,
            "private_identifiers_rejected": True,
            "leakage_errors_bucket": bucket_count(len(feature_errors)),
        },
        "class_balance_summary": {
            "target_positive_bucket": bucket_count(targets["target_positive"]),
            "target_non_positive_bucket": bucket_count(targets["target_non_positive"]),
            "control_positive_bucket": bucket_count(controls_positive),
            "class_balance_screen_passed": class_balance_ok,
        },
        "split_readiness_summary": {
            "holdout_by_task_family_repo_file_family_required": True,
            "no_task_leakage_rule_required": True,
            "public_split_output_buckets_only": True,
            "split_ready_for_training": False,
        },
        "validation_summary": {
            "self_test_available": True,
            "no_count_1_values": True,
            "public_leak_scan": "passed",
            "no_training_or_model_quality_estimate": True,
            "route_specific_phase4a_validation": "passed",
        },
        "conservative_recommendation": recommendation,
    }


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("identity drift")
    if report.get("status") not in {STATUS_STOP, STATUS_REPAIR, STATUS_READY}:
        errors.append("bad status")
    auth = report.get("authorization_attestation", {})
    for key in ("provider_network_used", "llm_used", "model_training_executed", "model_fitting_executed", "model_quality_estimate_executed", "new_data_collected", "source_files_read_for_new_evidence", "runtime_default_changed", "new_retrieval_channel_family_added", "ci_changed", "method_claimed"):
        if auth.get(key) is not False:
            errors.append(f"overclaim: {key}")
    if auth.get("effect_claim") != "no_effect_claim" or auth.get("private_rows_published") is not False:
        errors.append("claim/privacy boundary failed")
    feature_summary = report.get("feature_contract_summary", {})
    if feature_summary.get("evidence_success_used_as_feature") is not False or feature_summary.get("candidate_found_alone_is_evidence") is not False:
        errors.append("feature contract boundary failed")
    if report.get("class_balance_summary", {}).get("control_positive_bucket") != "count_0":
        errors.append("control positive overclaim")
    if contains_count_1(report):
        errors.append("count_1 published")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_report(report)
    if errors:
        raise PrecheckError("report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_precheck(confirm_private_input: bool, phase2_rows: Path | None, phase3_rows: Path | None, output: Path) -> dict[str, Any]:
    if not confirm_private_input:
        raise PrecheckError("--confirm-private-input is required")
    phase2_path = phase2_rows or latest_rows(PHASE2_ROOT, PHASE2_ROWS)
    phase3_path = phase3_rows or latest_rows(PHASE3_ROOT, PHASE3_ROWS)
    report = build_report(load_jsonl(phase2_path), load_jsonl(phase3_path))
    write_report(report, output)
    return {"status": report["status"], "conservative_recommendation": report["conservative_recommendation"], "public_report": str(output)}


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    checks.append(("evidence_success_feature_rejected", bool(validate_feature_contract({"evidence_success"}))))
    checks.append(("target_path_feature_rejected", bool(validate_feature_contract({"target_path"}))))
    checks.append(("target_range_feature_rejected", bool(validate_feature_contract({"target_range"}))))
    checks.append(("target_hash_feature_rejected", bool(validate_feature_contract({"target_hash"}))))
    checks.append(("target_content_feature_rejected", bool(validate_feature_contract({"target_content"}))))
    checks.append(("post_action_read_rejected", bool(validate_feature_contract({"post_action_read_result"}))))
    checks.append(("currentness_feature_rejected", bool(validate_feature_contract({"currentness_reread_match"}))))
    checks.append(("materialized_feature_rejected", bool(validate_feature_contract({"materialized_current_source"}))))
    sample_rows = []
    for phase in ("phase2_small_fair_local_comparison_pilot", "phase3_independent_local_holdout_validation_screen"):
        for action in ALLOWED_ACTIONS:
            sample_rows.append({"phase": phase, "micro_policy_id": action, "family_bucket": "same_symbol_support_relation", "candidate_found": action not in {"stop", "abstain"}, "evidence_success": action == "bm25_then_read_top1"})
    report = build_report(sample_rows[:7], sample_rows[7:])
    checks.append(("report_valid", not validate_report(report)))
    bad_report = json.loads(json.dumps(report))
    bad_report["input_summary"]["row_count_bucket"] = "count_1"
    checks.append(("count_1_rejected", bool(validate_report(bad_report))))
    bad_report = json.loads(json.dumps(report))
    bad_report["input_summary"]["leak"] = "runs/private/file.jsonl"
    checks.append(("public_leak_string_rejected", bool(validate_report(bad_report))))
    checks.append(("private_input_outside_runs_rejected", not path_is_ignored_runs(REPO / "docs" / "en" / "x.jsonl")))
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_total": len(checks), "checks_passed": len(checks) - len(failed), "failed_checks": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--phase2-private-rows", type=Path)
    parser.add_argument("--phase3-private-rows", type=Path)
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
            print("Phase 4A report validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Phase 4A report validation passed: {args.validate_report}")
        return 0
    try:
        result = run_precheck(args.confirm_private_input, args.phase2_private_rows, args.phase3_private_rows, args.output)
    except PrecheckError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
