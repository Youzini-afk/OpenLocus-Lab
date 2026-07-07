#!/usr/bin/env python3
"""Hard-source dry-run/preflight for interventional evidence acquisition.

This script is local-only and aggregate-only. It does not write private rows,
does not call provider/network services, does not train models, does not change
runtime/default behavior, and does not make a method-winner claim.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
PHASE = "interventional_evidence_acquisition_phase1_hard_source_preflight"
REPORT_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1_hard_source_preflight_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
AGGREGATE_SCREEN_PHASE = "interventional_evidence_acquisition_phase1_hard_source_private_row_aggregate_screen"
AGGREGATE_SCREEN_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1_hard_source_private_row_aggregate_screen_v1"
AGGREGATE_SCREEN_STATUS = "phase1_hard_source_private_row_aggregate_screen_no_claim"
DEFAULT_AGGREGATE_SCREEN_REPORT = REPO / "artifacts" / AGGREGATE_SCREEN_PHASE / f"{AGGREGATE_SCREEN_PHASE}_report.json"
PHASE1B_PHASE = "interventional_evidence_acquisition_phase1b_micro_policy_tiny_collection"
PHASE1B_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1b_micro_policy_tiny_collection_public_report_v1"
PHASE1B_STATUS = "phase1b_micro_policy_tiny_collection_synthetic_preflight_no_real_evidencecore_no_claim"
DEFAULT_PHASE1B_REPORT = REPO / "artifacts" / PHASE1B_PHASE / f"{PHASE1B_PHASE}_report.json"
PHASE1B_PRIVATE_RUN_ROOT = REPO / "runs" / PHASE1B_PHASE
PHASE1C_PHASE = "interventional_evidence_acquisition_phase1c_tiny_real_current_source_pilot"
PHASE1C_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1c_tiny_real_current_source_pilot_public_report_v1"
PHASE1C_STATUS = "phase1c_tiny_real_current_source_pilot_evidencecore_feasibility_no_claim"
DEFAULT_PHASE1C_REPORT = REPO / "artifacts" / PHASE1C_PHASE / f"{PHASE1C_PHASE}_report.json"
PHASE1C_PRIVATE_RUN_ROOT = REPO / "runs" / PHASE1C_PHASE
PHASE1D_PHASE = "interventional_evidence_acquisition_phase1d_real_source_coverage_robustness"
PHASE1D_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1d_real_source_coverage_robustness_public_report_v1"
PHASE1D_STATUS = "phase1d_real_source_coverage_robustness_no_claim"
DEFAULT_PHASE1D_REPORT = REPO / "artifacts" / PHASE1D_PHASE / f"{PHASE1D_PHASE}_report.json"
PHASE1D_PRIVATE_RUN_ROOT = REPO / "runs" / PHASE1D_PHASE
PHASE1E_PHASE = "phase1e_cross_phase_private_row_diagnostic_screen"
PHASE1E_SCHEMA_VERSION = "phase1e_cross_phase_private_row_diagnostic_screen_public_report_v1"
PHASE1E_STATUS = "phase1e_cross_phase_private_row_diagnostic_no_claim"
DEFAULT_PHASE1E_REPORT = REPO / "artifacts" / PHASE1E_PHASE / f"{PHASE1E_PHASE}_report.json"
STATUS_PREFLIGHT = "phase1_hard_source_preflight_no_private_rows"
STATUS_COMPLETE = "phase1_hard_source_private_pilot_complete_no_claim"
NEXT_ACTION = "stop/request explicit decision before any follow-up experiment"
PRIVATE_RUN_ROOT = REPO / "runs" / "interventional_evidence_acquisition_phase1_hard_source_pilot"
PRIVATE_ROWS_FILENAME = "hard_source_private_rows.jsonl"
PRIVATE_MANIFEST_FILENAME = "hard_source_private_manifest.json"
FIXED_SEED = 20260707

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
AGGREGATE_SCREEN_KEYS = {
    "schema_version",
    "phase",
    "status",
    "authorization_attestation",
    "coverage_summary",
    "action_outcome_summary",
    "baseline_screen",
    "evidencecore_summary",
    "privacy_summary",
    "validation_summary",
    "conservative_recommendation",
}
PHASE1B_MICRO_POLICIES = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
PHASE1B_ACQUISITION_POLICIES = PHASE1B_MICRO_POLICIES[:5]
PHASE1B_REPORT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "authorization_attestation",
    "source_summary",
    "coverage_summary",
    "policy_outcome_summary",
    "baseline_screen",
    "evidencecore_summary",
    "privacy_summary",
    "validation_summary",
    "conservative_recommendation",
}
PHASE1C_REPORT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "authorization_attestation",
    "source_summary",
    "coverage_summary",
    "policy_outcome_summary",
    "evidencecore_summary",
    "privacy_summary",
    "validation_summary",
    "conservative_recommendation",
}
PHASE1D_REPORT_KEYS = PHASE1C_REPORT_KEYS
PHASE1E_REPORT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "input_summary",
    "authorization_attestation",
    "evidencecore_consistency_summary",
    "failure_mode_buckets",
    "policy_label_coverage_buckets",
    "phase_comparison_buckets",
    "privacy_summary",
    "validation_summary",
    "conservative_recommendation",
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


def bucket_private_screen_count(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count <= 5:
        return "count_1_to_5"
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


def eligible_actions(task: HardTaskShape) -> tuple[str, ...]:
    return tuple(action for action in ALLOWED_ACTIONS if action_available(task, action))


def action_candidate_found(task: HardTaskShape, action: str) -> bool:
    if action in {"stop", "abstain"}:
        return False
    return action_available(task, action)


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


def build_private_rows(tasks: list[HardTaskShape]) -> list[dict[str, Any]]:
    rng = random.Random(FIXED_SEED)
    shuffled_tasks = list(tasks)
    rng.shuffle(shuffled_tasks)
    rows: list[dict[str, Any]] = []
    used_task_ids: set[str] = set()
    coverage_actions = list(ALLOWED_ACTIONS)
    rng.shuffle(coverage_actions)

    for action in coverage_actions:
        candidates = [task for task in shuffled_tasks if task.private_id not in used_task_ids and action in eligible_actions(task)]
        if not candidates:
            continue
        task = rng.choice(candidates)
        used_task_ids.add(task.private_id)
        rows.append(build_private_row(task, action, len(rows), "fixed_seed_coverage_block_then_uniform_eligible"))

    for task in shuffled_tasks:
        if task.private_id in used_task_ids:
            continue
        choices = list(eligible_actions(task))
        action = rng.choice(choices)
        rows.append(build_private_row(task, action, len(rows), "fixed_seed_uniform_over_task_eligible_actions"))
    rows.sort(key=lambda row: int(row["row_index"]))
    return rows


def build_private_row(task: HardTaskShape, action: str, row_index: int, policy: str) -> dict[str, Any]:
    actions = eligible_actions(task)
    materialized = action_materializes(task, action)
    evidence_success = action_success(task, action)
    return {
        "schema_version": "interventional_evidence_acquisition_phase1_hard_source_private_row_v1",
        "row_index": row_index,
        "task_private_id": task.private_id,
        "family_bucket": task.family_bucket,
        "private_path": task.private_path,
        "private_symbol": task.private_symbol,
        "private_query": task.private_query,
        "private_range": task.private_range,
        "action": action,
        "eligible_actions": list(actions),
        "assignment_policy_private": policy,
        "propensity": 1.0 / len(actions),
        "candidate_found": action_candidate_found(task, action),
        "materialized_current_source": materialized,
        "evidence_success": evidence_success,
        "evidencecore": {
            "candidate_is_fact": evidence_success,
            "counted_evidence_requires_current_source": True,
            "retrieval_only_not_evidence_success": action.startswith("retrieve_") and not evidence_success,
        },
        "privacy": {
            "private_row": True,
            "public_artifact_allowed": False,
        },
    }


def private_row_semantic_errors(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows):
        evidence_success = row.get("evidence_success") is True
        candidate_is_fact = row.get("evidencecore", {}).get("candidate_is_fact") is True
        if candidate_is_fact != evidence_success:
            errors.append(f"candidate_is_fact/evidence_success mismatch at private row {index}")
    return errors


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_private_outputs(rows: list[dict[str, Any]], private_root: Path = PRIVATE_RUN_ROOT) -> dict[str, Any]:
    semantic_errors = private_row_semantic_errors(rows)
    if semantic_errors:
        raise PreflightError("private row semantic validation failed: " + "; ".join(semantic_errors[:8]))
    run_dir = private_root / time.strftime("%Y%m%d-%H%M%S")
    row_path = run_dir / PRIVATE_ROWS_FILENAME
    manifest_path = run_dir / PRIVATE_MANIFEST_FILENAME
    write_jsonl(row_path, rows)
    manifest = {
        "schema_version": "interventional_evidence_acquisition_phase1_hard_source_private_manifest_v1",
        "storage_class": "ignored_runs_private",
        "row_count": len(rows),
        "private_rows_path": str(row_path),
        "private_manifest_path": str(manifest_path),
        "public_report_must_not_include_private_paths": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def run_capture(*, confirm_private_output: bool, dry_run: bool, output: Path, private_root: Path = PRIVATE_RUN_ROOT) -> dict[str, Any]:
    tasks = build_hard_task_source()
    rows = build_private_rows(tasks) if confirm_private_output and not dry_run else []
    manifest: dict[str, Any] | None = None
    if confirm_private_output and not dry_run:
        manifest = write_private_outputs(rows, private_root)
    report = build_report(tasks, rows, confirmed=bool(manifest))
    write_report(report, output)
    return {
        "status": report["status"],
        "private_rows_written": bool(manifest),
        "public_report": str(output),
        "private_rows_location": "runs/interventional_evidence_acquisition_phase1_hard_source_pilot/.../hard_source_private_rows.jsonl" if manifest else "none",
        "_private_manifest": manifest,
    }


def find_latest_private_rows_path(private_root: Path = PRIVATE_RUN_ROOT) -> Path:
    candidates = sorted(private_root.glob(f"*/{PRIVATE_ROWS_FILENAME}"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise PreflightError("no hard-source private rows found under ignored runs/")
    return candidates[0]


def load_private_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise PreflightError(f"invalid private row json at line {line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise PreflightError(f"private row line {line_number} is not an object")
            rows.append(row)
    if not rows:
        raise PreflightError("private row file is empty")
    semantic_errors = private_row_semantic_errors(rows)
    if semantic_errors:
        raise PreflightError("private row semantic validation failed: " + "; ".join(semantic_errors[:8]))
    return rows


def _row_bool(row: dict[str, Any], key: str) -> bool:
    return row.get(key) is True


def contains_singleton_bucket(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_singleton_bucket(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_singleton_bucket(child) for child in value)
    return value == "count_1"


def build_aggregate_screen(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_actions = Counter(str(row.get("action", "")) for row in rows)
    row_families = Counter(str(row.get("family_bucket", "")) for row in rows)
    candidate_found = Counter(str(row.get("action", "")) for row in rows if _row_bool(row, "candidate_found"))
    materialized = Counter(str(row.get("action", "")) for row in rows if _row_bool(row, "materialized_current_source"))
    evidence_success = Counter(str(row.get("action", "")) for row in rows if _row_bool(row, "evidence_success"))
    materialized_not_success = sum(1 for row in rows if _row_bool(row, "materialized_current_source") and not _row_bool(row, "evidence_success"))
    missing_action_coverage = sum(1 for action in ALLOWED_ACTIONS if row_actions[action] == 0)
    missing_family_coverage = sum(1 for family in FAMILY_BUCKETS if row_families[family] == 0)
    best_fixed_success = max((evidence_success[action] for action in EVIDENCE_SUCCESS_ACTIONS), default=0)
    randomized_success = sum(evidence_success.values())
    recommendation = "maybe_expand_with_new_explicit_decision" if missing_action_coverage == 0 and missing_family_coverage == 0 and randomized_success > 0 else "redesign_before_expansion"
    report = {
        "schema_version": AGGREGATE_SCREEN_SCHEMA_VERSION,
        "phase": AGGREGATE_SCREEN_PHASE,
        "status": AGGREGATE_SCREEN_STATUS,
        "authorization_attestation": {
            "private_rows_read_locally": True,
            "private_rows_published": False,
            "provider_network_authorized": False,
            "provider_network_used": False,
            "training_authorized": False,
            "model_training_executed": False,
            "runtime_default_change_authorized": False,
            "runtime_default_changed": False,
            "new_retrieval_channel_family_added": False,
            "method_winner_claimed": False,
            "signal_claim": "no_signal_claim",
            "diagnostic_screen_only": True,
        },
        "coverage_summary": {
            "row_count_bucket": bucket_private_screen_count(len(rows)),
            "action_coverage_buckets": {action: bucket_private_screen_count(row_actions[action]) for action in ALLOWED_ACTIONS},
            "family_coverage_buckets": {family: bucket_private_screen_count(row_families[family]) for family in FAMILY_BUCKETS},
            "missing_action_coverage_bucket": bucket_private_screen_count(missing_action_coverage),
            "missing_family_coverage_bucket": bucket_private_screen_count(missing_family_coverage),
        },
        "action_outcome_summary": {
            "candidate_found_buckets": {action: bucket_private_screen_count(candidate_found[action]) for action in ALLOWED_ACTIONS},
            "materialized_buckets": {action: bucket_private_screen_count(materialized[action]) for action in ALLOWED_ACTIONS},
            "evidence_success_buckets": {action: bucket_private_screen_count(evidence_success[action]) for action in ALLOWED_ACTIONS},
            "materialized_but_not_success_bucket": bucket_private_screen_count(materialized_not_success),
        },
        "baseline_screen": {
            "best_fixed_local_action_success_rate_bucket": bucket_rate(best_fixed_success, len(rows)),
            "randomized_policy_evidence_success_rate_bucket": bucket_rate(randomized_success, len(rows)),
            "method_winner_claimed": False,
            "signal_claim": "no_signal_claim",
        },
        "evidencecore_summary": {
            "current_source_required_for_counted_evidence": True,
            "candidate_is_not_fact_without_evidence_success": True,
            "retrieval_only_evidence_success_bucket": bucket_private_screen_count(evidence_success["retrieve_bm25"] + evidence_success["retrieve_symbol_regex"]),
            "evidence_success_implies_materialization": True,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_read_locally": True,
            "private_rows_published": False,
            "raw_rows_public": False,
            "private_paths_public": False,
            "private_symbols_public": False,
            "private_queries_public": False,
            "private_ranges_public": False,
            "private_hashes_public": False,
            "private_run_paths_public": False,
            "provider_payloads_public": False,
        },
        "validation_summary": {
            "route_specific_public_screen_validation": "passed",
            "self_test_available": True,
        },
        "conservative_recommendation": recommendation,
    }
    errors = validate_aggregate_screen(report)
    if errors:
        raise PreflightError("generated invalid aggregate screen: " + "; ".join(errors[:8]))
    return report


def validate_private_rows_for_aggregate(rows: list[dict[str, Any]]) -> list[str]:
    errors = private_row_semantic_errors(rows)
    for index, row in enumerate(rows):
        action = str(row.get("action", ""))
        if action not in ALLOWED_ACTIONS:
            errors.append(f"unknown action at private row {index}")
        if str(row.get("family_bucket", "")) not in FAMILY_BUCKETS:
            errors.append(f"unknown family bucket at private row {index}")
        if _row_bool(row, "evidence_success") and not _row_bool(row, "materialized_current_source"):
            errors.append(f"evidence success without materialization at private row {index}")
        if action.startswith("retrieve_") and _row_bool(row, "evidence_success"):
            errors.append(f"retrieval-only evidence success at private row {index}")
    return errors


def validate_aggregate_screen(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["aggregate screen must be an object"]
    errors: list[str] = []
    if set(report) != AGGREGATE_SCREEN_KEYS:
        errors.append("aggregate screen top-level shape drift")
    if report.get("schema_version") != AGGREGATE_SCREEN_SCHEMA_VERSION:
        errors.append("bad aggregate screen schema version")
    if report.get("phase") != AGGREGATE_SCREEN_PHASE:
        errors.append("bad aggregate screen phase")
    if report.get("status") != AGGREGATE_SCREEN_STATUS:
        errors.append("bad aggregate screen status")
    auth = report.get("authorization_attestation", {})
    if auth.get("private_rows_read_locally") is not True or auth.get("private_rows_published") is not False:
        errors.append("private row read/publish attestation failed")
    for key in ("provider_network_authorized", "provider_network_used", "training_authorized", "model_training_executed", "runtime_default_change_authorized", "runtime_default_changed", "new_retrieval_channel_family_added", "method_winner_claimed"):
        if auth.get(key) is not False:
            errors.append(f"aggregate screen overclaim: {key}")
    if auth.get("signal_claim") != "no_signal_claim" or auth.get("diagnostic_screen_only") is not True:
        errors.append("aggregate screen claim boundary failed")
    coverage = report.get("coverage_summary", {})
    if set(coverage.get("action_coverage_buckets", {})) != set(ALLOWED_ACTIONS) or set(coverage.get("family_coverage_buckets", {})) != set(FAMILY_BUCKETS):
        errors.append("aggregate coverage shape drift")
    outcomes = report.get("action_outcome_summary", {})
    for key in ("candidate_found_buckets", "materialized_buckets", "evidence_success_buckets"):
        if set(outcomes.get(key, {})) != set(ALLOWED_ACTIONS):
            errors.append(f"aggregate outcome shape drift: {key}")
    success = outcomes.get("evidence_success_buckets", {})
    materialized = outcomes.get("materialized_buckets", {})
    if success.get("retrieve_bm25") != "count_0" or success.get("retrieve_symbol_regex") != "count_0":
        errors.append("retrieval-only action counted as evidence success")
    for action in ALLOWED_ACTIONS:
        if materialized.get(action) == "count_0" and success.get(action) != "count_0":
            errors.append(f"aggregate evidence success without materialization: {action}")
    baseline = report.get("baseline_screen", {})
    if baseline.get("method_winner_claimed") is not False or baseline.get("signal_claim") != "no_signal_claim":
        errors.append("aggregate baseline overclaim")
    evidence = report.get("evidencecore_summary", {})
    if evidence.get("current_source_required_for_counted_evidence") is not True or evidence.get("candidate_is_not_fact_without_evidence_success") is not True:
        errors.append("aggregate EvidenceCore boundary failed")
    if evidence.get("retrieval_only_evidence_success_bucket") != "count_0" or evidence.get("evidence_success_implies_materialization") is not True:
        errors.append("aggregate EvidenceCore success/materialization failed")
    privacy = report.get("privacy_summary", {})
    if privacy.get("publication_level") != "aggregate_only" or privacy.get("private_rows_read_locally") is not True or privacy.get("private_rows_published") is not False:
        errors.append("aggregate privacy level failed")
    for key in ("raw_rows_public", "private_paths_public", "private_symbols_public", "private_queries_public", "private_ranges_public", "private_hashes_public", "private_run_paths_public", "provider_payloads_public"):
        if privacy.get(key) is not False:
            errors.append(f"aggregate privacy boundary failed: {key}")
    if report.get("conservative_recommendation") not in {"stop_no_expansion", "redesign_before_expansion", "maybe_expand_with_new_explicit_decision"}:
        errors.append("bad conservative recommendation")
    errors.extend(public_leak_errors(report))
    return errors


def validate_aggregate_screen_file(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load aggregate screen: {exc}"]
    return validate_aggregate_screen(report)


def write_aggregate_screen(report: dict[str, Any], output: Path) -> None:
    errors = validate_aggregate_screen(report)
    if errors:
        raise PreflightError("aggregate screen validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_aggregate_private_rows(private_rows_path: Path | None, output: Path) -> dict[str, Any]:
    source_path = private_rows_path or find_latest_private_rows_path()
    rows = load_private_rows(source_path)
    row_errors = validate_private_rows_for_aggregate(rows)
    if row_errors:
        raise PreflightError("private row aggregate validation failed: " + "; ".join(row_errors[:8]))
    report = build_aggregate_screen(rows)
    write_aggregate_screen(report, output)
    return {
        "status": report["status"],
        "conservative_recommendation": report["conservative_recommendation"],
        "private_rows_read_locally": True,
        "private_rows_published": False,
        "public_report": str(output),
    }


def phase1b_tasks() -> list[HardTaskShape]:
    return build_hard_task_source()[:32]


def phase1b_policy_eligible(task: HardTaskShape, policy: str) -> bool:
    if policy in {"stop", "abstain"}:
        return True
    if policy == "read_related_test_when_available":
        return task.has_related_test
    return policy in PHASE1B_ACQUISITION_POLICIES


def phase1b_subactions(policy: str) -> tuple[str, ...]:
    if policy == "bm25_then_read_top1":
        return ("retrieve_bm25", "read_top1")
    if policy == "bm25_then_read_next_unique_file":
        return ("retrieve_bm25", "read_next_unique_file")
    if policy == "symbol_regex_then_read_top1":
        return ("retrieve_symbol_regex", "read_top1")
    if policy == "symbol_regex_then_read_next_unique_file":
        return ("retrieve_symbol_regex", "read_next_unique_file")
    if policy == "read_related_test_when_available":
        return ("read_related_test",)
    return (policy,)


def phase1b_policy_observation(task: HardTaskShape, policy: str) -> dict[str, Any]:
    subactions = phase1b_subactions(policy)
    candidate_found = any(action_candidate_found(task, action) for action in subactions)
    materialized = any(action_materializes(task, action) for action in subactions)
    synthetic_success = any(action_success(task, action) for action in subactions if action in EVIDENCE_SUCCESS_ACTIONS)
    if not materialized and policy not in {"stop", "abstain"}:
        reason = "no_current_source_materialized"
    elif materialized and not synthetic_success:
        reason = "materialized_but_not_acceptable_label"
    elif synthetic_success:
        reason = "synthetic_success_label_with_materialization"
    else:
        reason = "control_no_acquisition"
    return {
        "candidate_found": candidate_found,
        "read_attempted": any(action.startswith("read_") for action in subactions),
        "materialized_current_source": materialized,
        "synthetic_success": synthetic_success,
        "failure_safe_reason_bucket": reason,
        "subactions": subactions,
    }


def build_phase1b_private_rows(tasks: list[HardTaskShape] | None = None) -> list[dict[str, Any]]:
    tasks = tasks or phase1b_tasks()
    rows: list[dict[str, Any]] = []
    row_index = 0
    for task in tasks:
        eligible = [policy for policy in PHASE1B_MICRO_POLICIES if phase1b_policy_eligible(task, policy)]
        for policy in PHASE1B_ACQUISITION_POLICIES:
            if not phase1b_policy_eligible(task, policy):
                continue
            observation = phase1b_policy_observation(task, policy)
            rows.append(build_phase1b_private_row(task, policy, eligible, observation, row_index, "deterministic_full_panel_acquisition"))
            row_index += 1
    for policy in ("stop", "abstain"):
        for task in tasks[:8]:
            eligible = [candidate for candidate in PHASE1B_MICRO_POLICIES if phase1b_policy_eligible(task, candidate)]
            observation = phase1b_policy_observation(task, policy)
            rows.append(build_phase1b_private_row(task, policy, eligible, observation, row_index, "sparse_control_panel"))
            row_index += 1
    if len(rows) > 176:
        raise PreflightError("Phase 1B private row cap exceeded")
    return rows


def build_phase1b_private_row(task: HardTaskShape, policy: str, eligible: list[str], observation: dict[str, Any], row_index: int, assignment_mode: str) -> dict[str, Any]:
    synthetic_success = observation["synthetic_success"] is True
    return {
        "schema_version": "interventional_evidence_acquisition_phase1b_micro_policy_private_row_v1",
        "phase": PHASE1B_PHASE,
        "row_index": row_index,
        "private_task_id": task.private_id,
        "family_bucket": task.family_bucket,
        "micro_policy_id": policy,
        "micro_policy_version": "v1",
        "assignment_mode": assignment_mode,
        "eligible_micro_policies": eligible,
        "pre_policy_state_buckets": {
            "candidate_count_bucket": bucket_count(task.candidate_count),
            "unique_file_candidate_bucket": bucket_count(task.unique_file_candidates),
            "related_test_available": task.has_related_test,
        },
        "primitive_subaction_trace_labels": list(observation["subactions"]),
        "private_exact_refs": {
            "private_path": task.private_path,
            "private_symbol": task.private_symbol,
            "private_query": task.private_query,
            "private_range": task.private_range,
        },
        "candidate_found": observation["candidate_found"],
        "read_attempted": observation["read_attempted"],
        "materialized_current_source": observation["materialized_current_source"],
        "real_current_source_materialization": False,
        "synthetic_success": synthetic_success,
        "failure_safe_reason_bucket": observation["failure_safe_reason_bucket"],
        "evidencecore": {
            "candidate_is_fact": False,
            "counted_evidence_requires_current_source": True,
            "synthetic_materialization_only": True,
            "real_evidence_success": False,
        },
        "privacy": {
            "private_row": True,
            "public_artifact_allowed": False,
            "provider_network_used": False,
            "model_training_executed": False,
        },
    }


def validate_phase1b_private_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not rows or len(rows) > 176:
        errors.append("Phase 1B row count outside allowed range")
    for index, row in enumerate(rows):
        policy = str(row.get("micro_policy_id", ""))
        if policy not in PHASE1B_MICRO_POLICIES:
            errors.append(f"unknown Phase 1B policy at row {index}")
        if policy in {"retrieve_bm25", "retrieve_symbol_regex"}:
            errors.append(f"standalone retrieval policy at row {index}")
        if str(row.get("family_bucket", "")) not in FAMILY_BUCKETS:
            errors.append(f"unknown Phase 1B family at row {index}")
        if row.get("privacy", {}).get("provider_network_used") is not False or row.get("privacy", {}).get("model_training_executed") is not False:
            errors.append(f"provider/training boundary failure at row {index}")
        if row.get("real_current_source_materialization") is not False:
            errors.append(f"unexpected real current-source materialization at row {index}")
        if "evidence_success" in row:
            errors.append(f"unqualified Phase 1B evidence_success field at row {index}")
        synthetic_success = row.get("synthetic_success") is True
        materialized = row.get("materialized_current_source") is True
        if synthetic_success and not materialized:
            errors.append(f"Phase 1B synthetic success without materialization at row {index}")
        if row.get("evidencecore", {}).get("candidate_is_fact") is not False:
            errors.append(f"Phase 1B synthetic row claims candidate_is_fact at row {index}")
        if row.get("evidencecore", {}).get("real_evidence_success") is not False:
            errors.append(f"Phase 1B synthetic row claims real evidence success at row {index}")
        subactions = set(row.get("primitive_subaction_trace_labels", []))
        if subactions <= {"retrieve_bm25", "retrieve_symbol_regex"} and synthetic_success:
            errors.append(f"Phase 1B retrieval-only synthetic success at row {index}")
    return errors


def write_phase1b_private_outputs(rows: list[dict[str, Any]], private_root: Path = PHASE1B_PRIVATE_RUN_ROOT) -> dict[str, Any]:
    errors = validate_phase1b_private_rows(rows)
    if errors:
        raise PreflightError("Phase 1B private row validation failed: " + "; ".join(errors[:8]))
    run_dir = private_root / time.strftime("%Y%m%d-%H%M%S")
    row_path = run_dir / "phase1b_micro_policy_private_rows.jsonl"
    manifest_path = run_dir / "phase1b_micro_policy_private_manifest.json"
    write_jsonl(row_path, rows)
    manifest = {
        "schema_version": "interventional_evidence_acquisition_phase1b_micro_policy_private_manifest_v1",
        "storage_class": "ignored_runs_private",
        "row_count_bucket": bucket_count(len(rows)),
        "private_rows_path": str(row_path),
        "private_manifest_path": str(manifest_path),
        "public_report_must_not_include_private_paths": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def build_phase1b_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_phase1b_private_rows(rows)
    if errors:
        raise PreflightError("Phase 1B report input invalid: " + "; ".join(errors[:8]))
    policies = Counter(str(row["micro_policy_id"]) for row in rows)
    families = Counter(str(row["family_bucket"]) for row in rows)
    candidate_found = Counter(str(row["micro_policy_id"]) for row in rows if row.get("candidate_found") is True)
    read_attempted = Counter(str(row["micro_policy_id"]) for row in rows if row.get("read_attempted") is True)
    materialized = Counter(str(row["micro_policy_id"]) for row in rows if row.get("materialized_current_source") is True)
    synthetic_success = Counter(str(row["micro_policy_id"]) for row in rows if row.get("synthetic_success") is True)
    materialized_not_synthetic_success = sum(1 for row in rows if row.get("materialized_current_source") is True and row.get("synthetic_success") is not True)
    best_micro = max((synthetic_success[policy] for policy in PHASE1B_ACQUISITION_POLICIES), default=0)
    controls = synthetic_success["stop"] + synthetic_success["abstain"]
    missing_policy = sum(1 for policy in PHASE1B_MICRO_POLICIES if policies[policy] == 0)
    missing_family = sum(1 for family in FAMILY_BUCKETS if families[family] == 0)
    recommendation = "maybe_expand_with_new_explicit_decision" if missing_policy == 0 and missing_family == 0 and best_micro > controls else "redesign_before_expansion"
    report = {
        "schema_version": PHASE1B_SCHEMA_VERSION,
        "phase": PHASE1B_PHASE,
        "status": PHASE1B_STATUS,
        "authorization_attestation": {
            "local_only": True,
            "private_rows_written": True,
            "private_rows_published": False,
            "provider_network_authorized": False,
            "provider_network_used": False,
            "training_authorized": False,
            "model_training_executed": False,
            "runtime_default_change_authorized": False,
            "runtime_default_changed": False,
            "new_retrieval_channel_family_added": False,
            "method_winner_claimed": False,
            "signal_claim": "no_signal_claim",
        },
        "source_summary": {
            "source_kind": "synthetic_local_hard_task_shapes",
            "task_count_bucket": bucket_count(len({row["private_task_id"] for row in rows})),
            "real_current_source_materialization_performed": False,
            "evidencecore_status": "synthetic_materialization_preflight_no_real_current_source_reads",
        },
        "coverage_summary": {
            "row_count_bucket": bucket_count(len(rows)),
            "family_coverage_buckets": {family: bucket_count(families[family]) for family in FAMILY_BUCKETS},
            "policy_coverage_buckets": {policy: bucket_count(policies[policy]) for policy in PHASE1B_MICRO_POLICIES},
            "missing_policy_coverage_bucket": bucket_count(missing_policy),
            "missing_family_coverage_bucket": bucket_count(missing_family),
        },
        "policy_outcome_summary": {
            "candidate_found_buckets": {policy: bucket_count(candidate_found[policy]) for policy in PHASE1B_MICRO_POLICIES},
            "read_attempted_buckets": {policy: bucket_count(read_attempted[policy]) for policy in PHASE1B_MICRO_POLICIES},
            "materialized_buckets": {policy: bucket_count(materialized[policy]) for policy in PHASE1B_MICRO_POLICIES},
            "synthetic_success_buckets": {policy: bucket_count(synthetic_success[policy]) for policy in PHASE1B_MICRO_POLICIES},
            "materialized_but_not_synthetic_success_bucket": bucket_count(materialized_not_synthetic_success),
        },
        "baseline_screen": {
            "best_fixed_micro_policy_synthetic_success_rate_bucket": bucket_rate(best_micro, len(rows)),
            "stop_abstain_control_success_bucket": bucket_count(controls),
            "primitive_phase1_comparison": "retrieval_only_success_not_applicable",
            "method_winner_claimed": False,
            "signal_claim": "no_signal_claim",
        },
        "evidencecore_summary": {
            "real_evidence_success_bucket": "not_applicable",
            "synthetic_success_requires_materialization": True,
            "retrieval_only_synthetic_success_bucket": "not_applicable",
            "real_current_source_materialization_performed": False,
            "synthetic_materialization_only": True,
            "candidate_is_fact_bucket": "count_0",
            "candidate_is_not_fact_without_real_evidence": True,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_written": True,
            "private_rows_published": False,
            "raw_rows_public": False,
            "private_task_ids_public": False,
            "private_paths_public": False,
            "private_symbols_public": False,
            "private_queries_public": False,
            "private_ranges_public": False,
            "private_hashes_public": False,
            "private_run_paths_public": False,
            "provider_payloads_public": False,
        },
        "validation_summary": {
            "route_specific_phase1b_validation": "passed",
            "singleton_private_count_buckets_avoided": True,
            "self_test_available": True,
        },
        "conservative_recommendation": recommendation,
    }
    report_errors = validate_phase1b_report(report)
    if report_errors:
        raise PreflightError("generated invalid Phase 1B report: " + "; ".join(report_errors[:8]))
    return report


def validate_phase1b_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["Phase 1B report must be an object"]
    errors: list[str] = []
    if set(report) != PHASE1B_REPORT_KEYS:
        errors.append("Phase 1B report top-level shape drift")
    if report.get("schema_version") != PHASE1B_SCHEMA_VERSION or report.get("phase") != PHASE1B_PHASE or report.get("status") != PHASE1B_STATUS:
        errors.append("Phase 1B identity/status drift")
    auth = report.get("authorization_attestation", {})
    if auth.get("local_only") is not True or auth.get("private_rows_written") is not True or auth.get("private_rows_published") is not False:
        errors.append("Phase 1B authorization/private row attestation failed")
    for key in ("provider_network_authorized", "provider_network_used", "training_authorized", "model_training_executed", "runtime_default_change_authorized", "runtime_default_changed", "new_retrieval_channel_family_added", "method_winner_claimed"):
        if auth.get(key) is not False:
            errors.append(f"Phase 1B overclaim: {key}")
    if auth.get("signal_claim") != "no_signal_claim":
        errors.append("Phase 1B signal claim overclaim")
    source = report.get("source_summary", {})
    if source.get("real_current_source_materialization_performed") is not False or source.get("evidencecore_status") != "synthetic_materialization_preflight_no_real_current_source_reads":
        errors.append("Phase 1B real EvidenceCore status overclaim")
    coverage = report.get("coverage_summary", {})
    if set(coverage.get("policy_coverage_buckets", {})) != set(PHASE1B_MICRO_POLICIES) or set(coverage.get("family_coverage_buckets", {})) != set(FAMILY_BUCKETS):
        errors.append("Phase 1B coverage shape drift")
    outcomes = report.get("policy_outcome_summary", {})
    if "evidence_success_buckets" in outcomes:
        errors.append("Phase 1B unqualified evidence_success_buckets published")
    for key in ("candidate_found_buckets", "read_attempted_buckets", "materialized_buckets", "synthetic_success_buckets"):
        if set(outcomes.get(key, {})) != set(PHASE1B_MICRO_POLICIES):
            errors.append(f"Phase 1B outcome shape drift: {key}")
        if "count_1" in set(outcomes.get(key, {}).values()):
            errors.append(f"Phase 1B singleton private count bucket published: {key}")
    success = outcomes.get("synthetic_success_buckets", {})
    materialized = outcomes.get("materialized_buckets", {})
    for policy in PHASE1B_MICRO_POLICIES:
        if materialized.get(policy) == "count_0" and success.get(policy) != "count_0":
            errors.append(f"Phase 1B synthetic success without materialization: {policy}")
    if success.get("stop") != "count_0" or success.get("abstain") != "count_0":
        errors.append("Phase 1B control synthetic success overclaim")
    baseline = report.get("baseline_screen", {})
    if "best_fixed_micro_policy_success_rate_bucket" in baseline:
        errors.append("Phase 1B unqualified best fixed success bucket published")
    if baseline.get("method_winner_claimed") is not False or baseline.get("signal_claim") != "no_signal_claim":
        errors.append("Phase 1B baseline overclaim")
    evidence = report.get("evidencecore_summary", {})
    if "success_requires_materialization" in evidence or "retrieval_only_success_bucket" in evidence or "candidate_is_not_fact_without_evidence_success" in evidence:
        errors.append("Phase 1B unqualified EvidenceCore success/fact terminology published")
    if evidence.get("real_evidence_success_bucket") != "not_applicable" or evidence.get("candidate_is_fact_bucket") != "count_0":
        errors.append("Phase 1B real EvidenceCore success/fact overclaim")
    if evidence.get("synthetic_success_requires_materialization") is not True or evidence.get("retrieval_only_synthetic_success_bucket") != "not_applicable":
        errors.append("Phase 1B synthetic success boundary failed")
    if evidence.get("real_current_source_materialization_performed") is not False or evidence.get("synthetic_materialization_only") is not True:
        errors.append("Phase 1B synthetic/real materialization boundary failed")
    privacy = report.get("privacy_summary", {})
    if privacy.get("publication_level") != "aggregate_only" or privacy.get("private_rows_published") is not False:
        errors.append("Phase 1B privacy level failed")
    for key in ("raw_rows_public", "private_task_ids_public", "private_paths_public", "private_symbols_public", "private_queries_public", "private_ranges_public", "private_hashes_public", "private_run_paths_public", "provider_payloads_public"):
        if privacy.get(key) is not False:
            errors.append(f"Phase 1B privacy boundary failed: {key}")
    if report.get("validation_summary", {}).get("singleton_private_count_buckets_avoided") is not True:
        errors.append("Phase 1B singleton bucket guard missing")
    if contains_singleton_bucket(report):
        errors.append("Phase 1B singleton private count bucket published")
    if report.get("conservative_recommendation") not in {"stop_no_expansion", "redesign_before_expansion", "maybe_expand_with_new_explicit_decision"}:
        errors.append("Phase 1B recommendation drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_phase1b_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_phase1b_report(report)
    if errors:
        raise PreflightError("Phase 1B report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_phase1b_report_file(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load Phase 1B report: {exc}"]
    return validate_phase1b_report(report)


def run_phase1b_micro_policy(*, confirm_private_output: bool, output: Path, private_root: Path = PHASE1B_PRIVATE_RUN_ROOT) -> dict[str, Any]:
    if not confirm_private_output:
        raise PreflightError("Phase 1B private output requires --confirm-private-output")
    rows = build_phase1b_private_rows()
    manifest = write_phase1b_private_outputs(rows, private_root)
    report = build_phase1b_report(rows)
    write_phase1b_report(report, output)
    return {
        "status": report["status"],
        "conservative_recommendation": report["conservative_recommendation"],
        "real_current_source_materialization_performed": False,
        "private_rows_location": "runs/interventional_evidence_acquisition_phase1b_micro_policy_tiny_collection/.../phase1b_micro_policy_private_rows.jsonl",
        "public_report": str(output),
        "_private_manifest": manifest,
    }


def load_phase1c_private_manifest(path: Path, *, max_tasks: int = 8) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"cannot load Phase 1C private manifest: {exc}") from exc
    tasks = raw.get("tasks") if isinstance(raw, dict) else raw
    if not isinstance(tasks, list):
        raise PreflightError("Phase 1C private manifest must be a task list or an object with tasks")
    normalized: list[dict[str, Any]] = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise PreflightError(f"Phase 1C manifest task {index} is not an object")
        normalized.append(
            {
                "private_task_id": str(task.get("private_task_id", f"private-task-{index}")),
                "family_bucket": str(task["family_bucket"]),
                "private_path": str(task["private_path"]),
                "start_line": int(task["start_line"]),
                "end_line": int(task["end_line"]),
                "has_related_test": bool(task.get("has_related_test", False)),
            }
        )
    if not normalized or len(normalized) > max_tasks:
        raise PreflightError(f"private manifest must contain 1-{max_tasks} tasks")
    return normalized


def write_phase1c_manifest_template(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    template = {
        "schema_version": "interventional_evidence_acquisition_phase1c_private_manifest_template_v1",
        "note": "Replace placeholder values locally under ignored runs/. Do not commit real paths, ranges, task text, or labels.",
        "tasks": [],
    }
    output.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_phase1c_local_example_manifest(output: Path) -> None:
    candidates: list[Path] = []
    for pattern in ("docs/en/*.md", "docs/zh/*.md", "eval/*.py", "scripts/*.py"):
        candidates.extend(sorted(REPO.glob(pattern)))
    tasks: list[dict[str, Any]] = []
    for path in candidates:
        if len(tasks) >= 8:
            break
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue
        if line_count < 2:
            continue
        tasks.append(
            {
                "private_task_id": f"phase1c-local-private-{len(tasks):02d}",
                "family_bucket": FAMILY_BUCKETS[len(tasks)],
                "private_path": path.relative_to(REPO).as_posix(),
                "start_line": 1,
                "end_line": min(8, line_count),
                "has_related_test": False,
            }
        )
    if len(tasks) != 8:
        raise PreflightError("could not build 8 local Phase 1C manifest tasks")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": "interventional_evidence_acquisition_phase1c_private_manifest_v1",
                "storage_class": "ignored_runs_private",
                "tasks": tasks,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def read_current_range(private_path: str, start_line: int, end_line: int, *, base_dir: Path = REPO) -> dict[str, Any]:
    base = base_dir.resolve()
    path = (base / private_path).resolve()
    if not str(path).startswith(str(base)):
        raise PreflightError("Phase 1C path escapes repository")
    lines = path.read_text(encoding="utf-8").splitlines()
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        raise PreflightError("Phase 1C line range unavailable")
    content = "\n".join(lines[start_line - 1 : end_line]) + "\n"
    content_bytes = content.encode("utf-8")
    digest = hashlib.sha256(content_bytes).hexdigest()
    reread = path.read_text(encoding="utf-8").splitlines()
    reread_content = "\n".join(reread[start_line - 1 : end_line]) + "\n"
    return {
        "private_path": private_path,
        "private_range": f"{start_line}-{end_line}",
        "content_text": content,
        "content_byte_length": len(content_bytes),
        "content_sha256": digest,
        "currentness_reread_match": reread_content == content,
        "range_content_match": hashlib.sha256(reread_content.encode("utf-8")).hexdigest() == digest,
    }


def phase1c_policy_observation(task: dict[str, Any], policy: str, *, base_dir: Path = REPO) -> dict[str, Any]:
    candidate_found = policy not in {"stop", "abstain"}
    materializing_policy = policy in PHASE1B_ACQUISITION_POLICIES and (policy != "read_related_test_when_available" or task["has_related_test"])
    materialization: dict[str, Any] | None = read_current_range(task["private_path"], int(task["start_line"]), int(task["end_line"]), base_dir=base_dir) if materializing_policy else None
    evidence_success = bool(materialization and materialization["currentness_reread_match"] and materialization["range_content_match"] and materialization["content_byte_length"] > 0)
    return {
        "candidate_found": candidate_found,
        "read_attempted": materializing_policy,
        "materialized_current_source": materialization is not None,
        "evidence_success": evidence_success,
        "failure_safe_reason_bucket": "real_current_source_materialized" if evidence_success else ("control_no_acquisition" if policy in {"stop", "abstain"} else "not_eligible_or_no_materialization"),
        "materialization": materialization,
    }


def build_phase1c_private_rows(tasks: list[dict[str, Any]], *, base_dir: Path = REPO, max_rows: int = 56) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    row_index = 0
    for task in tasks:
        eligible = [policy for policy in PHASE1B_MICRO_POLICIES if policy != "read_related_test_when_available" or task["has_related_test"]]
        for policy in PHASE1B_MICRO_POLICIES:
            observation = phase1c_policy_observation(task, policy, base_dir=base_dir)
            materialization = observation["materialization"] or {}
            rows.append({
                "schema_version": "interventional_evidence_acquisition_phase1c_real_source_private_row_v1",
                "phase": PHASE1C_PHASE,
                "row_index": row_index,
                "private_task_id": task["private_task_id"],
                "family_bucket": task["family_bucket"],
                "micro_policy_id": policy,
                "micro_policy_version": "v1",
                "assignment_mode": "deterministic_full_panel_all_policies",
                "eligible_micro_policies": eligible,
                "candidate_found": observation["candidate_found"],
                "read_attempted": observation["read_attempted"],
                "materialized_current_source": observation["materialized_current_source"],
                "evidence_success": observation["evidence_success"],
                "failure_safe_reason_bucket": observation["failure_safe_reason_bucket"],
                "private_exact_refs": materialization,
                "evidencecore": {
                    "candidate_is_fact": observation["evidence_success"],
                    "counted_evidence_requires_current_source": True,
                    "content_sha256_present": bool(materialization.get("content_sha256")),
                    "currentness_reread_match": bool(materialization.get("currentness_reread_match")),
                    "range_content_match": bool(materialization.get("range_content_match")),
                },
                "privacy": {"private_row": True, "public_artifact_allowed": False, "provider_network_used": False, "model_training_executed": False},
            })
            row_index += 1
    if len(rows) > max_rows:
        raise PreflightError(f"real-source private row cap exceeded: {max_rows}")
    return rows


def validate_phase1c_private_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not rows or len(rows) > 56:
        errors.append("Phase 1C row count outside allowed range")
    for index, row in enumerate(rows):
        policy = str(row.get("micro_policy_id", ""))
        if policy not in PHASE1B_MICRO_POLICIES:
            errors.append(f"unknown Phase 1C policy at row {index}")
        if row.get("privacy", {}).get("provider_network_used") is not False or row.get("privacy", {}).get("model_training_executed") is not False:
            errors.append(f"Phase 1C provider/training boundary failure at row {index}")
        evidence_success = row.get("evidence_success") is True
        materialized = row.get("materialized_current_source") is True
        refs = row.get("private_exact_refs", {})
        if policy in {"stop", "abstain"} and evidence_success:
            errors.append(f"Phase 1C control policy succeeded at row {index}")
        if evidence_success and (not materialized or not refs.get("content_sha256") or refs.get("currentness_reread_match") is not True or refs.get("range_content_match") is not True or not refs.get("content_text")):
            errors.append(f"Phase 1C success without complete EvidenceCore materialization at row {index}")
        if row.get("evidencecore", {}).get("candidate_is_fact") is not evidence_success:
            errors.append(f"Phase 1C candidate_is_fact mismatch at row {index}")
    return errors


def build_phase1c_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_phase1c_private_rows(rows)
    if errors:
        raise PreflightError("Phase 1C report input invalid: " + "; ".join(errors[:8]))
    policies = Counter(str(row["micro_policy_id"]) for row in rows)
    families = Counter(str(row["family_bucket"]) for row in rows)
    candidate_found = Counter(str(row["micro_policy_id"]) for row in rows if row.get("candidate_found") is True)
    materialized = Counter(str(row["micro_policy_id"]) for row in rows if row.get("materialized_current_source") is True)
    evidence_success = Counter(str(row["micro_policy_id"]) for row in rows if row.get("evidence_success") is True)
    materialized_not_success = sum(1 for row in rows if row.get("materialized_current_source") is True and row.get("evidence_success") is not True)
    recommendation = "maybe_expand_with_new_explicit_decision" if sum(evidence_success.values()) > 0 else "stop_no_claim"
    report = {
        "schema_version": PHASE1C_SCHEMA_VERSION,
        "phase": PHASE1C_PHASE,
        "status": PHASE1C_STATUS,
        "authorization_attestation": {"local_only": True, "private_rows_written": True, "private_rows_published": False, "provider_network_authorized": False, "provider_network_used": False, "training_authorized": False, "model_training_executed": False, "runtime_default_change_authorized": False, "runtime_default_changed": False, "new_retrieval_channel_family_added": False, "method_winner_claimed": False, "signal_claim": "no_signal_claim"},
        "source_summary": {"source_kind": "real_current_repository_files", "task_count_bucket": bucket_private_screen_count(len({row["private_task_id"] for row in rows})), "real_current_source_materialization_performed": True},
        "coverage_summary": {"row_count_bucket": bucket_private_screen_count(len(rows)), "family_coverage_buckets": {family: bucket_private_screen_count(families[family]) for family in FAMILY_BUCKETS}, "policy_coverage_buckets": {policy: bucket_private_screen_count(policies[policy]) for policy in PHASE1B_MICRO_POLICIES}},
        "policy_outcome_summary": {"candidate_found_buckets": {policy: bucket_private_screen_count(candidate_found[policy]) for policy in PHASE1B_MICRO_POLICIES}, "materialized_buckets": {policy: bucket_private_screen_count(materialized[policy]) for policy in PHASE1B_MICRO_POLICIES}, "evidence_success_buckets": {policy: bucket_private_screen_count(evidence_success[policy]) for policy in PHASE1B_MICRO_POLICIES}, "materialized_but_not_success_bucket": bucket_private_screen_count(materialized_not_success)},
        "evidencecore_summary": {"success_requires_materialization_hash_currentness": True, "candidate_found_is_not_evidence": True, "control_success_bucket": bucket_private_screen_count(evidence_success["stop"] + evidence_success["abstain"]), "content_hash_recorded_private_only": True, "real_current_source_materialization_performed": True},
        "privacy_summary": {"publication_level": "aggregate_only", "private_rows_written": True, "private_rows_published": False, "raw_rows_public": False, "private_task_ids_public": False, "private_paths_public": False, "private_ranges_public": False, "private_hashes_public": False, "private_snippets_public": False, "private_run_paths_public": False, "provider_payloads_public": False},
        "validation_summary": {"route_specific_phase1c_validation": "passed", "singleton_private_count_buckets_avoided": True, "self_test_available": True},
        "conservative_recommendation": recommendation,
    }
    report_errors = validate_phase1c_report(report)
    if report_errors:
        raise PreflightError("generated invalid Phase 1C report: " + "; ".join(report_errors[:8]))
    return report


def validate_phase1c_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["Phase 1C report must be an object"]
    errors: list[str] = []
    if set(report) != PHASE1C_REPORT_KEYS:
        errors.append("Phase 1C report top-level shape drift")
    if report.get("schema_version") != PHASE1C_SCHEMA_VERSION or report.get("phase") != PHASE1C_PHASE or report.get("status") != PHASE1C_STATUS:
        errors.append("Phase 1C identity/status drift")
    auth = report.get("authorization_attestation", {})
    for key in ("provider_network_authorized", "provider_network_used", "training_authorized", "model_training_executed", "runtime_default_change_authorized", "runtime_default_changed", "new_retrieval_channel_family_added", "method_winner_claimed"):
        if auth.get(key) is not False:
            errors.append(f"Phase 1C overclaim: {key}")
    if auth.get("local_only") is not True or auth.get("private_rows_published") is not False or auth.get("signal_claim") != "no_signal_claim":
        errors.append("Phase 1C authorization boundary failed")
    if report.get("source_summary", {}).get("real_current_source_materialization_performed") is not True:
        errors.append("Phase 1C real materialization missing")
    coverage = report.get("coverage_summary", {})
    outcomes = report.get("policy_outcome_summary", {})
    if set(coverage.get("policy_coverage_buckets", {})) != set(PHASE1B_MICRO_POLICIES) or set(outcomes.get("evidence_success_buckets", {})) != set(PHASE1B_MICRO_POLICIES):
        errors.append("Phase 1C policy shape drift")
    if outcomes.get("evidence_success_buckets", {}).get("stop") != "count_0" or outcomes.get("evidence_success_buckets", {}).get("abstain") != "count_0":
        errors.append("Phase 1C control success overclaim")
    evidence = report.get("evidencecore_summary", {})
    if evidence.get("success_requires_materialization_hash_currentness") is not True or evidence.get("candidate_found_is_not_evidence") is not True or evidence.get("control_success_bucket") != "count_0":
        errors.append("Phase 1C EvidenceCore boundary failed")
    privacy = report.get("privacy_summary", {})
    for key in ("raw_rows_public", "private_task_ids_public", "private_paths_public", "private_ranges_public", "private_hashes_public", "private_snippets_public", "private_run_paths_public", "provider_payloads_public"):
        if privacy.get(key) is not False:
            errors.append(f"Phase 1C privacy boundary failed: {key}")
    if contains_singleton_bucket(report):
        errors.append("Phase 1C singleton private count bucket published")
    if report.get("conservative_recommendation") not in {"maybe_expand_with_new_explicit_decision", "stop_no_claim"}:
        errors.append("Phase 1C recommendation drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_phase1c_test_manifest(base_dir: Path, output: Path) -> None:
    files: list[Path] = []
    for index in range(8):
        path = base_dir / f"phase1c_source_{index}.txt"
        path.write_text(f"phase1c local source {index}\nline two\nline three\n", encoding="utf-8")
        files.append(path)
    manifest = {
        "schema_version": "interventional_evidence_acquisition_phase1c_private_manifest_v1",
        "tasks": [
            {
                "private_task_id": f"temp-private-{index}",
                "family_bucket": FAMILY_BUCKETS[index],
                "private_path": path.name,
                "start_line": 1,
                "end_line": 2,
                "has_related_test": False,
            }
            for index, path in enumerate(files)
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_phase1c_private_outputs(rows: list[dict[str, Any]], private_root: Path = PHASE1C_PRIVATE_RUN_ROOT) -> dict[str, Any]:
    errors = validate_phase1c_private_rows(rows)
    if errors:
        raise PreflightError("Phase 1C private row validation failed: " + "; ".join(errors[:8]))
    run_dir = private_root / time.strftime("%Y%m%d-%H%M%S")
    row_path = run_dir / "phase1c_real_source_private_rows.jsonl"
    manifest_path = run_dir / "phase1c_real_source_private_manifest.json"
    write_jsonl(row_path, rows)
    manifest = {"schema_version": "interventional_evidence_acquisition_phase1c_private_manifest_v1", "storage_class": "ignored_runs_private", "row_count_bucket": bucket_private_screen_count(len(rows)), "private_rows_path": str(row_path), "public_report_must_not_include_private_paths": True}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def write_phase1c_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_phase1c_report(report)
    if errors:
        raise PreflightError("Phase 1C report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_phase1c_report_file(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load Phase 1C report: {exc}"]
    return validate_phase1c_report(report)


def run_phase1c_real_source(*, confirm_private_output: bool, output: Path, private_manifest: Path | None, private_root: Path = PHASE1C_PRIVATE_RUN_ROOT, base_dir: Path = REPO) -> dict[str, Any]:
    if not confirm_private_output:
        raise PreflightError("Phase 1C private output requires --confirm-private-output")
    if private_manifest is None:
        raise PreflightError("Phase 1C requires --phase1c-private-manifest pointing to ignored local task manifest")
    tasks = load_phase1c_private_manifest(private_manifest)
    rows = build_phase1c_private_rows(tasks, base_dir=base_dir)
    manifest = write_phase1c_private_outputs(rows, private_root)
    report = build_phase1c_report(rows)
    write_phase1c_report(report, output)
    return {"status": report["status"], "conservative_recommendation": report["conservative_recommendation"], "private_rows_location": "runs/interventional_evidence_acquisition_phase1c_tiny_real_current_source_pilot/.../phase1c_real_source_private_rows.jsonl", "public_report": str(output), "_private_manifest": manifest}


def write_phase1d_local_example_manifest(output: Path) -> None:
    candidates: list[Path] = []
    for pattern in ("docs/en/*.md", "docs/zh/*.md", "eval/*.py", "scripts/*.py", "artifacts/**/*.json"):
        candidates.extend(sorted(REPO.glob(pattern)))
    tasks: list[dict[str, Any]] = []
    for path in candidates:
        if len(tasks) >= 16:
            break
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue
        if line_count < 2:
            continue
        tasks.append(
            {
                "private_task_id": f"phase1d-local-private-{len(tasks):02d}",
                "family_bucket": FAMILY_BUCKETS[len(tasks) % len(FAMILY_BUCKETS)],
                "private_path": path.relative_to(REPO).as_posix(),
                "start_line": 1,
                "end_line": min(8, line_count),
                "has_related_test": False,
            }
        )
    if len(tasks) != 16:
        raise PreflightError("could not build 16 local Phase 1D manifest tasks")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema_version": "interventional_evidence_acquisition_phase1d_private_manifest_v1", "storage_class": "ignored_runs_private", "tasks": tasks}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_phase1d_private_rows(tasks: list[dict[str, Any]], *, base_dir: Path = REPO) -> list[dict[str, Any]]:
    if not tasks or len(tasks) > 16:
        raise PreflightError("Phase 1D private manifest must contain 1-16 tasks")
    rows = build_phase1c_private_rows(tasks, base_dir=base_dir, max_rows=112)
    for row in rows:
        row["phase"] = PHASE1D_PHASE
        row["schema_version"] = "interventional_evidence_acquisition_phase1d_real_source_private_row_v1"
    if len(rows) > 112:
        raise PreflightError("Phase 1D private row cap exceeded")
    return rows


def validate_phase1d_private_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors = []
    original_phases = [row.get("phase") for row in rows]
    try:
        for row in rows:
            row["phase"] = PHASE1C_PHASE
        errors.extend(error for error in validate_phase1c_private_rows(rows) if error != "Phase 1C row count outside allowed range")
    finally:
        for row, phase in zip(rows, original_phases):
            row["phase"] = phase
    if len(rows) > 112:
        errors.append("Phase 1D row count exceeds cap")
    return errors


def build_real_source_report(rows: list[dict[str, Any]], *, phase: str, schema_version: str, status: str, recommendation_values: set[str]) -> dict[str, Any]:
    policies = Counter(str(row["micro_policy_id"]) for row in rows)
    families = Counter(str(row["family_bucket"]) for row in rows)
    candidate_found = Counter(str(row["micro_policy_id"]) for row in rows if row.get("candidate_found") is True)
    materialized = Counter(str(row["micro_policy_id"]) for row in rows if row.get("materialized_current_source") is True)
    evidence_success = Counter(str(row["micro_policy_id"]) for row in rows if row.get("evidence_success") is True)
    materialized_not_success = sum(1 for row in rows if row.get("materialized_current_source") is True and row.get("evidence_success") is not True)
    recommendation = "maybe_expand_with_new_explicit_decision" if sum(evidence_success.values()) > 0 else sorted(recommendation_values - {"maybe_expand_with_new_explicit_decision"})[0]
    return {
        "schema_version": schema_version,
        "phase": phase,
        "status": status,
        "authorization_attestation": {"local_only": True, "private_rows_written": True, "private_rows_published": False, "provider_network_authorized": False, "provider_network_used": False, "training_authorized": False, "model_training_executed": False, "runtime_default_change_authorized": False, "runtime_default_changed": False, "new_retrieval_channel_family_added": False, "method_winner_claimed": False, "signal_claim": "no_signal_claim"},
        "source_summary": {"real_current_source_materialization_performed": True, "source_kind": "real_current_repository_files", "task_count_bucket": bucket_private_screen_count(len({row["private_task_id"] for row in rows}))},
        "coverage_summary": {"family_coverage_buckets": {family: bucket_private_screen_count(families[family]) for family in FAMILY_BUCKETS}, "policy_coverage_buckets": {policy: bucket_private_screen_count(policies[policy]) for policy in PHASE1B_MICRO_POLICIES}, "row_count_bucket": bucket_private_screen_count(len(rows))},
        "policy_outcome_summary": {"candidate_found_buckets": {policy: bucket_private_screen_count(candidate_found[policy]) for policy in PHASE1B_MICRO_POLICIES}, "evidence_success_buckets": {policy: bucket_private_screen_count(evidence_success[policy]) for policy in PHASE1B_MICRO_POLICIES}, "materialized_buckets": {policy: bucket_private_screen_count(materialized[policy]) for policy in PHASE1B_MICRO_POLICIES}, "materialized_but_not_success_bucket": bucket_private_screen_count(materialized_not_success)},
        "evidencecore_summary": {"candidate_found_is_not_evidence": True, "content_hash_recorded_private_only": True, "control_success_bucket": bucket_private_screen_count(evidence_success["stop"] + evidence_success["abstain"]), "real_current_source_materialization_performed": True, "success_requires_materialization_hash_currentness": True},
        "privacy_summary": {"private_hashes_public": False, "private_paths_public": False, "private_ranges_public": False, "private_rows_published": False, "private_rows_written": True, "private_run_paths_public": False, "private_snippets_public": False, "private_task_ids_public": False, "provider_payloads_public": False, "publication_level": "aggregate_only", "raw_rows_public": False},
        "validation_summary": {"route_specific_phase_validation": "passed", "self_test_available": True, "singleton_private_count_buckets_avoided": True},
        "conservative_recommendation": recommendation,
    }


def build_phase1d_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_phase1d_private_rows(rows)
    if errors:
        raise PreflightError("Phase 1D report input invalid: " + "; ".join(errors[:8]))
    report = build_real_source_report(rows, phase=PHASE1D_PHASE, schema_version=PHASE1D_SCHEMA_VERSION, status=PHASE1D_STATUS, recommendation_values={"maybe_expand_with_new_explicit_decision", "stop_repair_no_claim"})
    report_errors = validate_phase1d_report(report)
    if report_errors:
        raise PreflightError("generated invalid Phase 1D report: " + "; ".join(report_errors[:8]))
    return report


def validate_phase1d_report(report: Any) -> list[str]:
    errors = validate_phase1c_report({**report, "schema_version": PHASE1C_SCHEMA_VERSION, "phase": PHASE1C_PHASE, "status": PHASE1C_STATUS} if isinstance(report, dict) else report)
    if not isinstance(report, dict):
        return errors
    if set(report) != PHASE1D_REPORT_KEYS:
        errors.append("Phase 1D report top-level shape drift")
    if report.get("schema_version") != PHASE1D_SCHEMA_VERSION or report.get("phase") != PHASE1D_PHASE or report.get("status") != PHASE1D_STATUS:
        errors.append("Phase 1D identity/status drift")
    if report.get("conservative_recommendation") not in {"maybe_expand_with_new_explicit_decision", "stop_repair_no_claim"}:
        errors.append("Phase 1D recommendation drift")
    return errors


def write_phase1d_private_outputs(rows: list[dict[str, Any]], private_root: Path = PHASE1D_PRIVATE_RUN_ROOT) -> dict[str, Any]:
    errors = validate_phase1d_private_rows(rows)
    if errors:
        raise PreflightError("Phase 1D private row validation failed: " + "; ".join(errors[:8]))
    run_dir = private_root / time.strftime("%Y%m%d-%H%M%S")
    row_path = run_dir / "phase1d_real_source_private_rows.jsonl"
    manifest_path = run_dir / "phase1d_real_source_private_manifest.json"
    write_jsonl(row_path, rows)
    manifest = {"schema_version": "interventional_evidence_acquisition_phase1d_private_manifest_v1", "storage_class": "ignored_runs_private", "row_count_bucket": bucket_private_screen_count(len(rows)), "private_rows_path": str(row_path), "public_report_must_not_include_private_paths": True}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def write_phase1d_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_phase1d_report(report)
    if errors:
        raise PreflightError("Phase 1D report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_phase1d_report_file(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load Phase 1D report: {exc}"]
    return validate_phase1d_report(report)


def run_phase1d_real_source(*, confirm_private_output: bool, output: Path, private_manifest: Path | None, private_root: Path = PHASE1D_PRIVATE_RUN_ROOT, base_dir: Path = REPO) -> dict[str, Any]:
    if not confirm_private_output:
        raise PreflightError("Phase 1D private output requires --confirm-private-output")
    if private_manifest is None:
        raise PreflightError("Phase 1D requires --phase1d-private-manifest pointing to ignored local task manifest")
    tasks = load_phase1c_private_manifest(private_manifest, max_tasks=16)
    rows = build_phase1d_private_rows(tasks, base_dir=base_dir)
    manifest = write_phase1d_private_outputs(rows, private_root)
    report = build_phase1d_report(rows)
    write_phase1d_report(report, output)
    return {"status": report["status"], "conservative_recommendation": report["conservative_recommendation"], "private_rows_location": "runs/interventional_evidence_acquisition_phase1d_real_source_coverage_robustness/.../phase1d_real_source_private_rows.jsonl", "public_report": str(output), "_private_manifest": manifest}


def path_is_ignored_runs(path: Path) -> bool:
    try:
        resolved = path.resolve()
        relative = resolved.relative_to(REPO.resolve())
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] == "runs"


def find_latest_rows(private_root: Path, filename: str) -> Path:
    candidates = sorted(private_root.glob(f"*/{filename}"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise PreflightError("private rows not found under ignored runs/")
    return candidates[0]


def load_private_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path_is_ignored_runs(path):
        raise PreflightError("private row input must be under ignored runs/")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PreflightError(f"invalid private row JSONL at line {line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise PreflightError(f"private row line {line_number} is not an object")
            rows.append(row)
    if not rows:
        raise PreflightError("private row input is empty")
    return rows


def validate_phase1e_input_rows(phase1c_rows: list[dict[str, Any]], phase1d_rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(phase1c_rows) + len(phase1d_rows) > 168:
        errors.append("Phase 1E combined row cap exceeded")
    errors.extend(validate_phase1c_private_rows(phase1c_rows))
    errors.extend(validate_phase1d_private_rows(phase1d_rows))
    for index, row in enumerate(phase1c_rows + phase1d_rows):
        policy = str(row.get("micro_policy_id", ""))
        if policy not in PHASE1B_MICRO_POLICIES:
            errors.append(f"Phase 1E unknown policy at row {index}")
        if row.get("evidence_success") is True:
            refs = row.get("private_exact_refs", {})
            if row.get("materialized_current_source") is not True or not refs.get("content_sha256") or refs.get("currentness_reread_match") is not True or refs.get("range_content_match") is not True:
                errors.append(f"Phase 1E success without complete EvidenceCore materialization at row {index}")
        if policy in {"stop", "abstain"} and row.get("evidence_success") is True:
            errors.append(f"Phase 1E control success at row {index}")
    return errors


def build_phase1e_report(phase1c_rows: list[dict[str, Any]], phase1d_rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_phase1e_input_rows(phase1c_rows, phase1d_rows)
    if errors:
        raise PreflightError("Phase 1E input validation failed: " + "; ".join(errors[:8]))
    rows = phase1c_rows + phase1d_rows
    phase_counts = {"phase1c": len(phase1c_rows), "phase1d": len(phase1d_rows)}
    policies = Counter(str(row["micro_policy_id"]) for row in rows)
    failures = Counter(str(row.get("failure_safe_reason_bucket", "unknown")) for row in rows if row.get("evidence_success") is not True)
    success_by_phase = {
        "phase1c": sum(1 for row in phase1c_rows if row.get("evidence_success") is True),
        "phase1d": sum(1 for row in phase1d_rows if row.get("evidence_success") is True),
    }
    controls_success = sum(1 for row in rows if row.get("micro_policy_id") in {"stop", "abstain"} and row.get("evidence_success") is True)
    recommendation = "maybe_design_claim_or_larger_pilot_with_explicit_decision" if sum(success_by_phase.values()) > 0 else "stop_summarize_no_claim"
    report = {
        "schema_version": PHASE1E_SCHEMA_VERSION,
        "phase": PHASE1E_PHASE,
        "status": PHASE1E_STATUS,
        "input_summary": {
            "phase_coverage_buckets": {phase: bucket_private_screen_count(count) for phase, count in phase_counts.items()},
            "row_count_bucket": bucket_private_screen_count(len(rows)),
            "task_count_bucket": bucket_private_screen_count(len({row["private_task_id"] for row in rows})),
            "source_kind_bucket": "real_current_repository_files",
        },
        "authorization_attestation": {"local_only": True, "private_rows_read_locally": True, "private_rows_published": False, "provider_network_authorized": False, "provider_network_used": False, "llm_used": False, "training_authorized": False, "model_training_executed": False, "runtime_default_change_authorized": False, "runtime_default_changed": False, "new_retrieval_channel_family_added": False, "method_winner_claimed": False, "signal_lift_claim": "no_signal_claim"},
        "evidencecore_consistency_summary": {"success_requires_materialization_hash_currentness_range_match": True, "candidate_found_is_not_evidence": True, "controls_success_bucket": bucket_private_screen_count(controls_success)},
        "failure_mode_buckets": {key: bucket_private_screen_count(failures[key]) for key in sorted(failures)},
        "policy_label_coverage_buckets": {policy: bucket_private_screen_count(policies[policy]) for policy in PHASE1B_MICRO_POLICIES},
        "phase_comparison_buckets": {phase: {"row_count_bucket": bucket_private_screen_count(phase_counts[phase]), "evidence_success_bucket": bucket_private_screen_count(success_by_phase[phase])} for phase in ("phase1c", "phase1d")},
        "privacy_summary": {"publication_level": "aggregate_only", "private_rows_read_locally": True, "private_rows_published": False, "raw_rows_public": False, "private_task_ids_public": False, "private_paths_public": False, "private_ranges_public": False, "private_hashes_public": False, "private_snippets_public": False, "private_run_paths_public": False, "private_manifest_paths_public": False, "provider_payloads_public": False},
        "validation_summary": {"route_specific_phase1e_validation": "passed", "combined_row_cap_bucket": "lte_168", "singleton_private_count_buckets_avoided": True, "self_test_available": True},
        "conservative_recommendation": recommendation,
    }
    report_errors = validate_phase1e_report(report)
    if report_errors:
        raise PreflightError("generated invalid Phase 1E report: " + "; ".join(report_errors[:8]))
    return report


def validate_phase1e_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["Phase 1E report must be an object"]
    errors: list[str] = []
    if set(report) != PHASE1E_REPORT_KEYS:
        errors.append("Phase 1E report top-level shape drift")
    if report.get("schema_version") != PHASE1E_SCHEMA_VERSION or report.get("phase") != PHASE1E_PHASE or report.get("status") != PHASE1E_STATUS:
        errors.append("Phase 1E identity/status drift")
    auth = report.get("authorization_attestation", {})
    for key in ("provider_network_authorized", "provider_network_used", "llm_used", "training_authorized", "model_training_executed", "runtime_default_change_authorized", "runtime_default_changed", "new_retrieval_channel_family_added", "method_winner_claimed"):
        if auth.get(key) is not False:
            errors.append(f"Phase 1E overclaim: {key}")
    if auth.get("local_only") is not True or auth.get("private_rows_published") is not False or auth.get("signal_lift_claim") != "no_signal_claim":
        errors.append("Phase 1E authorization boundary failed")
    if set(report.get("policy_label_coverage_buckets", {})) != set(PHASE1B_MICRO_POLICIES):
        errors.append("Phase 1E policy coverage shape drift")
    evidence = report.get("evidencecore_consistency_summary", {})
    if evidence.get("success_requires_materialization_hash_currentness_range_match") is not True or evidence.get("candidate_found_is_not_evidence") is not True or evidence.get("controls_success_bucket") != "count_0":
        errors.append("Phase 1E EvidenceCore consistency failed")
    privacy = report.get("privacy_summary", {})
    for key in ("raw_rows_public", "private_task_ids_public", "private_paths_public", "private_ranges_public", "private_hashes_public", "private_snippets_public", "private_run_paths_public", "private_manifest_paths_public", "provider_payloads_public"):
        if privacy.get(key) is not False:
            errors.append(f"Phase 1E privacy boundary failed: {key}")
    if contains_singleton_bucket(report):
        errors.append("Phase 1E singleton private count bucket published")
    if report.get("conservative_recommendation") not in {"stop_summarize_no_claim", "maybe_design_claim_or_larger_pilot_with_explicit_decision"}:
        errors.append("Phase 1E recommendation drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_phase1e_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_phase1e_report(report)
    if errors:
        raise PreflightError("Phase 1E report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_phase1e_report_file(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load Phase 1E report: {exc}"]
    return validate_phase1e_report(report)


def run_phase1e_diagnostic(*, confirm_private_input: bool, phase1c_private_rows: Path | None, phase1d_private_rows: Path | None, output: Path) -> dict[str, Any]:
    if not confirm_private_input:
        raise PreflightError("Phase 1E requires --confirm-private-input")
    phase1c_path = phase1c_private_rows or find_latest_rows(PHASE1C_PRIVATE_RUN_ROOT, "phase1c_real_source_private_rows.jsonl")
    phase1d_path = phase1d_private_rows or find_latest_rows(PHASE1D_PRIVATE_RUN_ROOT, "phase1d_real_source_private_rows.jsonl")
    rows_c = load_private_jsonl_rows(phase1c_path)
    rows_d = load_private_jsonl_rows(phase1d_path)
    report = build_phase1e_report(rows_c, rows_d)
    write_phase1e_report(report, output)
    return {"status": report["status"], "conservative_recommendation": report["conservative_recommendation"], "private_rows_read_locally": True, "private_rows_published": False, "public_report": str(output)}


def build_report(tasks: list[HardTaskShape] | None = None, rows: list[dict[str, Any]] | None = None, *, confirmed: bool = False) -> dict[str, Any]:
    tasks = tasks or build_hard_task_source()
    rows = rows or []
    if not family_balance_ok(tasks):
        raise PreflightError("hard source must contain 32 balanced local task shapes")
    family_counts = Counter(task.family_bucket for task in tasks)
    availability = structural_counts(tasks)
    successes = success_counts(tasks)
    materialized = materialization_counts(tasks)
    candidates = candidate_found_counts(tasks)
    row_actions = Counter(str(row["action"]) for row in rows)
    row_families = Counter(str(row["family_bucket"]) for row in rows)
    row_candidate_found = Counter(str(row["action"]) for row in rows if row.get("candidate_found") is True)
    row_materialized = Counter(str(row["action"]) for row in rows if row.get("materialized_current_source") is True)
    row_successes = Counter(str(row["action"]) for row in rows if row.get("evidence_success") is True)
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
        "status": STATUS_COMPLETE if confirmed else STATUS_PREFLIGHT,
        "authorization_attestation": {
            "dry_run_preflight_only": not confirmed,
            "private_rows_written": confirmed,
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
            "confirmed_row_count_bucket": bucket_count(len(rows)) if confirmed else "count_0",
            "confirmed_action_coverage_buckets": {action: bucket_count(row_actions[action]) for action in ALLOWED_ACTIONS},
            "confirmed_family_coverage_buckets": {family: bucket_count(row_families[family]) for family in FAMILY_BUCKETS},
        },
        "structural_availability": {
            action: {
                "eligible_shape_count_bucket": bucket_count(availability[action]),
                "sampled_confirmed_row_count_bucket": bucket_count(row_actions[action]) if confirmed else "count_0",
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
            "randomized_policy_evidence_success_rate_bucket": bucket_rate(sum(row_successes.values()), len(rows)) if confirmed else "rate_unavailable",
            "signal_claim": "no_signal_claim",
            "method_winner_claimed": False,
        },
        "evidencecore_summary": {
            "current_source_required_for_counted_evidence": True,
            "candidate_found_count_buckets": {action: bucket_count(candidates[action]) for action in ALLOWED_ACTIONS},
            "materialized_action_count_buckets": {action: bucket_count(materialized[action]) for action in ALLOWED_ACTIONS},
            "evidence_success_count_buckets": {action: bucket_count(successes[action]) for action in ALLOWED_ACTIONS},
            "randomized_candidate_found_count_buckets": {action: bucket_count(row_candidate_found[action]) for action in ALLOWED_ACTIONS},
            "randomized_materialized_count_buckets": {action: bucket_count(row_materialized[action]) for action in ALLOWED_ACTIONS},
            "randomized_evidence_success_count_buckets": {action: bucket_count(row_successes[action]) for action in ALLOWED_ACTIONS},
            "materialized_not_success_count_bucket": bucket_count(materialized_not_success),
            "success_is_not_mere_materialization": materialized_not_success > 0,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_written": confirmed,
            "private_storage_class": "ignored_runs_private" if confirmed else "none",
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
    status = report.get("status")
    confirmed = status == STATUS_COMPLETE
    if status not in {STATUS_PREFLIGHT, STATUS_COMPLETE}:
        errors.append("bad status")
    auth = report.get("authorization_attestation", {})
    if auth.get("private_rows_written") is not confirmed:
        errors.append("private row write status mismatch")
    if auth.get("dry_run_preflight_only") is not (not confirmed):
        errors.append("dry-run status mismatch")
    for key in (
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
    for key in ("local_existing_capabilities_only",):
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
            if not confirmed and item.get("sampled_confirmed_row_count_bucket") != "count_0":
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
    if privacy.get("private_rows_written") is not confirmed:
        errors.append("privacy private row status mismatch")
    if confirmed and privacy.get("private_storage_class") != "ignored_runs_private":
        errors.append("private storage class missing")
    if not confirmed and privacy.get("private_storage_class") != "none":
        errors.append("dry-run private storage class drift")
    for key in (
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
    if action_summary.get("provider_or_network_action_count_bucket") != "count_0":
        errors.append("action summary overclaim")
    if (not confirmed and action_summary.get("confirmed_row_count_bucket") != "count_0") or (confirmed and action_summary.get("confirmed_row_count_bucket") == "count_0"):
        errors.append("confirmed row count mismatch")
    if set(action_summary.get("confirmed_action_coverage_buckets", {})) != set(ALLOWED_ACTIONS):
        errors.append("confirmed action coverage shape drift")
    elif confirmed and any(value == "count_0" for value in action_summary["confirmed_action_coverage_buckets"].values()):
        errors.append("confirmed action coverage missing")
    if set(action_summary.get("confirmed_family_coverage_buckets", {})) != set(FAMILY_BUCKETS):
        errors.append("confirmed family coverage shape drift")
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
    rows = build_private_rows(tasks)
    confirmed_report = build_report(tasks, rows, confirmed=True)
    checks.append(("private_row_candidate_is_fact_matches_evidence_success", not private_row_semantic_errors(rows)))
    checks.append(("private_rows_valid_for_aggregate", not validate_private_rows_for_aggregate(rows)))
    checks.append(("confirmed_report_valid", not validate_report(confirmed_report)))
    checks.append(("confirmed_all_actions_covered", all(value != "count_0" for value in confirmed_report["action_summary"]["confirmed_action_coverage_buckets"].values())))
    checks.append(("confirmed_retrieval_success_zero", confirmed_report["evidencecore_summary"]["randomized_evidence_success_count_buckets"]["retrieve_bm25"] == "count_0" and confirmed_report["evidencecore_summary"]["randomized_evidence_success_count_buckets"]["retrieve_symbol_regex"] == "count_0"))
    with tempfile.TemporaryDirectory() as temp_dir:
        dry_output = Path(temp_dir) / "dry_report.json"
        dry_result = run_capture(confirm_private_output=False, dry_run=True, output=dry_output, private_root=Path(temp_dir) / "runs")
        checks.append(("dry_run_writes_no_private_rows", dry_result["private_rows_written"] is False and not (Path(temp_dir) / "runs").exists()))
        confirmed_output = Path(temp_dir) / "confirmed_report.json"
        confirmed_result = run_capture(confirm_private_output=True, dry_run=False, output=confirmed_output, private_root=Path(temp_dir) / "runs")
        manifest = confirmed_result.get("_private_manifest") or {}
        checks.append(("confirm_flag_required_for_private_rows", confirmed_result["private_rows_written"] is True and Path(manifest.get("private_rows_path", "")).is_file()))
        loaded_confirmed = json.loads(confirmed_output.read_text(encoding="utf-8"))
        checks.append(("confirmed_manifest_path_not_public", not public_leak_errors(loaded_confirmed) and "private_rows_path" not in json.dumps(loaded_confirmed)))
        aggregate_output = Path(temp_dir) / "aggregate_screen.json"
        aggregate_result = run_aggregate_private_rows(Path(manifest["private_rows_path"]), aggregate_output)
        aggregate_report = json.loads(aggregate_output.read_text(encoding="utf-8"))
        checks.append(("aggregate_private_rows_generates_screen", aggregate_result["status"] == AGGREGATE_SCREEN_STATUS and aggregate_report["privacy_summary"]["private_rows_published"] is False))
        checks.append(("aggregate_screen_valid", not validate_aggregate_screen(aggregate_report)))
        phase1b_output = Path(temp_dir) / "phase1b_report.json"
        phase1b_result = run_phase1b_micro_policy(confirm_private_output=True, output=phase1b_output, private_root=Path(temp_dir) / "phase1b_runs")
        phase1b_report = json.loads(phase1b_output.read_text(encoding="utf-8"))
        checks.append(("phase1b_generates_report", phase1b_result["status"] == PHASE1B_STATUS and phase1b_report["privacy_summary"]["private_rows_published"] is False))
        checks.append(("phase1b_report_valid", not validate_phase1b_report(phase1b_report)))
        checks.append(("phase1b_private_rows_written_under_temp_runs", Path((phase1b_result.get("_private_manifest") or {}).get("private_rows_path", "")).is_file()))
        phase1c_output = Path(temp_dir) / "phase1c_report.json"
        phase1c_manifest = Path(temp_dir) / "phase1c_manifest.json"
        write_phase1c_test_manifest(Path(temp_dir), phase1c_manifest)
        phase1c_result = run_phase1c_real_source(confirm_private_output=True, output=phase1c_output, private_manifest=phase1c_manifest, private_root=Path(temp_dir) / "phase1c_runs", base_dir=Path(temp_dir))
        phase1c_report = json.loads(phase1c_output.read_text(encoding="utf-8"))
        checks.append(("phase1c_generates_report", phase1c_result["status"] == PHASE1C_STATUS and phase1c_report["privacy_summary"]["private_rows_published"] is False))
        checks.append(("phase1c_report_valid", not validate_phase1c_report(phase1c_report)))
        checks.append(("phase1c_private_rows_written_under_temp_runs", Path((phase1c_result.get("_private_manifest") or {}).get("private_rows_path", "")).is_file()))
        phase1d_output = Path(temp_dir) / "phase1d_report.json"
        phase1d_manifest = Path(temp_dir) / "phase1d_manifest.json"
        write_phase1c_test_manifest(Path(temp_dir), phase1d_manifest)
        phase1d_result = run_phase1d_real_source(confirm_private_output=True, output=phase1d_output, private_manifest=phase1d_manifest, private_root=Path(temp_dir) / "phase1d_runs", base_dir=Path(temp_dir))
        phase1d_report = json.loads(phase1d_output.read_text(encoding="utf-8"))
        checks.append(("phase1d_generates_report", phase1d_result["status"] == PHASE1D_STATUS and phase1d_report["privacy_summary"]["private_rows_published"] is False))
        checks.append(("phase1d_report_valid", not validate_phase1d_report(phase1d_report)))
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
    bad_rows = copy.deepcopy(rows)
    false_success_row = next(row for row in bad_rows if row["evidence_success"] is False)
    false_success_row["evidencecore"]["candidate_is_fact"] = True
    checks.append(("private_row_candidate_fact_without_success_rejected", bool(private_row_semantic_errors(bad_rows))))
    bad_rows = copy.deepcopy(rows)
    retrieval_row = next(row for row in bad_rows if str(row["action"]).startswith("retrieve_"))
    retrieval_row["evidence_success"] = True
    retrieval_row["materialized_current_source"] = False
    retrieval_row["evidencecore"]["candidate_is_fact"] = True
    checks.append(("aggregate_retrieval_success_row_rejected", bool(validate_private_rows_for_aggregate(bad_rows))))
    bad_screen = build_aggregate_screen(rows)
    bad_screen["authorization_attestation"]["method_winner_claimed"] = True
    checks.append(("aggregate_overclaim_rejected", bool(validate_aggregate_screen(bad_screen))))
    bad_screen = build_aggregate_screen(rows)
    bad_screen["privacy_summary"]["private_run_paths_public"] = True
    checks.append(("aggregate_privacy_overclaim_rejected", bool(validate_aggregate_screen(bad_screen))))
    phase1b_rows = build_phase1b_private_rows(tasks)
    phase1b_report = build_phase1b_report(phase1b_rows)
    checks.append(("phase1b_private_rows_valid", not validate_phase1b_private_rows(phase1b_rows)))
    checks.append(("phase1b_no_singleton_public_buckets", not contains_singleton_bucket(phase1b_report)))
    checks.append(("phase1b_private_rows_no_candidate_fact", all(row["evidencecore"]["candidate_is_fact"] is False and row["evidencecore"]["real_evidence_success"] is False for row in phase1b_rows)))
    checks.append(("phase1b_public_uses_synthetic_terms", "evidence_success_buckets" not in phase1b_report["policy_outcome_summary"] and "synthetic_success_buckets" in phase1b_report["policy_outcome_summary"] and "best_fixed_micro_policy_success_rate_bucket" not in phase1b_report["baseline_screen"]))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["authorization_attestation"]["provider_network_used"] = True
    checks.append(("phase1b_provider_overclaim_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["authorization_attestation"]["model_training_executed"] = True
    checks.append(("phase1b_training_overclaim_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["authorization_attestation"]["runtime_default_changed"] = True
    checks.append(("phase1b_runtime_overclaim_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["policy_outcome_summary"]["synthetic_success_buckets"]["stop"] = "count_2_to_5"
    checks.append(("phase1b_control_synthetic_success_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["policy_outcome_summary"]["synthetic_success_buckets"]["bm25_then_read_top1"] = "count_1"
    checks.append(("phase1b_singleton_bucket_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["coverage_summary"]["missing_policy_coverage_bucket"] = "count_1"
    checks.append(("phase1b_global_singleton_bucket_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["policy_outcome_summary"]["evidence_success_buckets"] = bad_phase1b_report["policy_outcome_summary"].pop("synthetic_success_buckets")
    checks.append(("phase1b_unqualified_success_bucket_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_report = copy.deepcopy(phase1b_report)
    bad_phase1b_report["baseline_screen"]["best_fixed_micro_policy_success_rate_bucket"] = bad_phase1b_report["baseline_screen"].pop("best_fixed_micro_policy_synthetic_success_rate_bucket")
    checks.append(("phase1b_unqualified_baseline_success_rejected", bool(validate_phase1b_report(bad_phase1b_report))))
    bad_phase1b_rows = copy.deepcopy(phase1b_rows)
    bad_phase1b_rows[0]["synthetic_success"] = True
    bad_phase1b_rows[0]["materialized_current_source"] = False
    checks.append(("phase1b_synthetic_success_without_materialization_rejected", bool(validate_phase1b_private_rows(bad_phase1b_rows))))
    bad_phase1b_rows = copy.deepcopy(phase1b_rows)
    bad_phase1b_rows[0]["evidencecore"]["candidate_is_fact"] = True
    checks.append(("phase1b_candidate_fact_rejected", bool(validate_phase1b_private_rows(bad_phase1b_rows))))
    bad_phase1b_rows = copy.deepcopy(phase1b_rows)
    bad_phase1b_rows[0]["evidence_success"] = True
    checks.append(("phase1b_unqualified_private_evidence_success_rejected", bool(validate_phase1b_private_rows(bad_phase1b_rows))))
    with tempfile.TemporaryDirectory() as temp_dir:
        phase1c_manifest = Path(temp_dir) / "phase1c_manifest.json"
        write_phase1c_test_manifest(Path(temp_dir), phase1c_manifest)
        phase1c_rows = build_phase1c_private_rows(load_phase1c_private_manifest(phase1c_manifest), base_dir=Path(temp_dir))
    phase1c_report = build_phase1c_report(phase1c_rows)
    checks.append(("phase1c_private_rows_valid", not validate_phase1c_private_rows(phase1c_rows)))
    checks.append(("phase1c_row_cap", len(phase1c_rows) <= 56))
    checks.append(("phase1c_no_singleton_public_buckets", not contains_singleton_bucket(phase1c_report)))
    checks.append(("phase1c_success_requires_hash_currentness", all((row["evidence_success"] is not True) or (row["materialized_current_source"] is True and row["private_exact_refs"].get("content_sha256") and row["private_exact_refs"].get("currentness_reread_match") is True and row["private_exact_refs"].get("range_content_match") is True) for row in phase1c_rows)))
    checks.append(("phase1c_controls_do_not_succeed", all(row["evidence_success"] is False for row in phase1c_rows if row["micro_policy_id"] in {"stop", "abstain"})))
    bad_phase1c_rows = copy.deepcopy(phase1c_rows)
    bad_phase1c_rows[0]["evidence_success"] = True
    bad_phase1c_rows[0]["materialized_current_source"] = False
    checks.append(("phase1c_success_without_materialization_rejected", bool(validate_phase1c_private_rows(bad_phase1c_rows))))
    bad_phase1c_report = copy.deepcopy(phase1c_report)
    bad_phase1c_report["coverage_summary"]["row_count_bucket"] = "count_1"
    checks.append(("phase1c_singleton_bucket_rejected", bool(validate_phase1c_report(bad_phase1c_report))))
    bad_phase1c_report = copy.deepcopy(phase1c_report)
    bad_phase1c_report["privacy_summary"]["private_paths_public"] = True
    checks.append(("phase1c_privacy_flag_rejected", bool(validate_phase1c_report(bad_phase1c_report))))
    bad_phase1c_report = copy.deepcopy(phase1c_report)
    bad_phase1c_report["source_summary"]["leaky_value_bucket"] = "docs/en/private.md"
    checks.append(("phase1c_public_path_leak_rejected", bool(validate_phase1c_report(bad_phase1c_report))))
    with tempfile.TemporaryDirectory() as temp_dir:
        phase1d_manifest = Path(temp_dir) / "phase1d_manifest.json"
        write_phase1c_test_manifest(Path(temp_dir), phase1d_manifest)
        phase1d_rows = build_phase1d_private_rows(load_phase1c_private_manifest(phase1d_manifest, max_tasks=16), base_dir=Path(temp_dir))
    phase1d_report = build_phase1d_report(phase1d_rows)
    checks.append(("phase1d_private_rows_valid", not validate_phase1d_private_rows(phase1d_rows)))
    checks.append(("phase1d_row_cap", len(phase1d_rows) <= 112))
    checks.append(("phase1d_no_singleton_public_buckets", not contains_singleton_bucket(phase1d_report)))
    checks.append(("phase1d_controls_do_not_succeed", all(row["evidence_success"] is False for row in phase1d_rows if row["micro_policy_id"] in {"stop", "abstain"})))
    bad_phase1d_report = copy.deepcopy(phase1d_report)
    bad_phase1d_report["coverage_summary"]["row_count_bucket"] = "count_1"
    checks.append(("phase1d_singleton_bucket_rejected", bool(validate_phase1d_report(bad_phase1d_report))))
    bad_phase1d_report = copy.deepcopy(phase1d_report)
    bad_phase1d_report["privacy_summary"]["private_paths_public"] = True
    checks.append(("phase1d_privacy_flag_rejected", bool(validate_phase1d_report(bad_phase1d_report))))
    phase1e_report = build_phase1e_report(phase1c_rows, phase1d_rows)
    checks.append(("phase1e_report_valid", not validate_phase1e_report(phase1e_report)))
    checks.append(("phase1e_no_singleton_public_buckets", not contains_singleton_bucket(phase1e_report)))
    checks.append(("phase1e_combined_row_cap", len(phase1c_rows) + len(phase1d_rows) <= 168))
    checks.append(("phase1e_controls_do_not_succeed", phase1e_report["evidencecore_consistency_summary"]["controls_success_bucket"] == "count_0"))
    bad_phase1e_report = copy.deepcopy(phase1e_report)
    bad_phase1e_report["input_summary"]["row_count_bucket"] = "count_1"
    checks.append(("phase1e_singleton_bucket_rejected", bool(validate_phase1e_report(bad_phase1e_report))))
    bad_phase1e_report = copy.deepcopy(phase1e_report)
    bad_phase1e_report["privacy_summary"]["private_run_paths_public"] = True
    checks.append(("phase1e_privacy_flag_rejected", bool(validate_phase1e_report(bad_phase1e_report))))
    bad_phase1e_report = copy.deepcopy(phase1e_report)
    bad_phase1e_report["input_summary"]["leaky_value_bucket"] = "runs/private/path.jsonl"
    checks.append(("phase1e_public_run_path_leak_rejected", bool(validate_phase1e_report(bad_phase1e_report))))
    bad_phase1e_rows = copy.deepcopy(phase1c_rows)
    bad_phase1e_rows[0]["evidence_success"] = True
    bad_phase1e_rows[0]["materialized_current_source"] = False
    checks.append(("phase1e_success_without_materialization_rejected", bool(validate_phase1e_input_rows(bad_phase1e_rows, phase1d_rows))))
    bad_report = copy.deepcopy(confirmed_report)
    bad_report["action_summary"]["confirmed_action_coverage_buckets"]["stop"] = "count_0"
    checks.append(("confirmed_missing_action_coverage_rejected", bool(validate_report(bad_report))))
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_total": len(checks), "checks_passed": len(checks) - len(failed), "failed_checks": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run synthetic self-tests")
    parser.add_argument("--dry-run", action="store_true", help="write aggregate-only dry-run report")
    parser.add_argument("--confirm-private-output", action="store_true", help="write ignored private rows under runs/ and aggregate-only public report")
    parser.add_argument("--aggregate-private-rows", action="store_true", help="read ignored private rows locally and write aggregate-only outcome screen")
    parser.add_argument("--run-phase1b-micro-policy", action="store_true", help="run Phase 1B tiny local micro-policy collection; requires --confirm-private-output")
    parser.add_argument("--run-phase1c-real-source", action="store_true", help="run Phase 1C tiny real current-source feasibility pilot; requires --confirm-private-output")
    parser.add_argument("--run-phase1d-real-source", action="store_true", help="run Phase 1D real-source coverage robustness pilot; requires --confirm-private-output")
    parser.add_argument("--run-phase1e-diagnostic", action="store_true", help="read existing Phase 1C/1D private rows and write aggregate-only diagnostic")
    parser.add_argument("--confirm-private-input", action="store_true", help="allow Phase 1E to read ignored private row inputs")
    parser.add_argument("--write-phase1c-manifest-template", type=Path, help="write an empty private manifest template; keep real filled manifests under ignored runs/")
    parser.add_argument("--write-phase1c-local-example-manifest", type=Path, help="write a local filled private manifest under ignored runs/; do not commit it")
    parser.add_argument("--write-phase1d-local-example-manifest", type=Path, help="write a local filled Phase 1D private manifest under ignored runs/; do not commit it")
    parser.add_argument("--private-rows-path", type=Path, help="local ignored private rows JSONL path for aggregate screen; never published")
    parser.add_argument("--phase1c-private-manifest", type=Path, help="ignored local Phase 1C private manifest with real task paths/ranges")
    parser.add_argument("--phase1d-private-manifest", type=Path, help="ignored local Phase 1D private manifest with real task paths/ranges")
    parser.add_argument("--phase1c-private-rows", type=Path, help="ignored Phase 1C private rows JSONL for Phase 1E")
    parser.add_argument("--phase1d-private-rows", type=Path, help="ignored Phase 1D private rows JSONL for Phase 1E")
    parser.add_argument("--validate-report", type=Path, help="validate an existing aggregate report")
    parser.add_argument("--validate-aggregate-screen", type=Path, help="validate an existing aggregate-only private row outcome screen")
    parser.add_argument("--validate-phase1b-report", type=Path, help="validate an existing Phase 1B public report")
    parser.add_argument("--validate-phase1c-report", type=Path, help="validate an existing Phase 1C public report")
    parser.add_argument("--validate-phase1d-report", type=Path, help="validate an existing Phase 1D public report")
    parser.add_argument("--validate-phase1e-report", type=Path, help="validate an existing Phase 1E public report")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT, help="dry-run report output path")
    parser.add_argument("--aggregate-output", type=Path, default=DEFAULT_AGGREGATE_SCREEN_REPORT, help="aggregate screen output path")
    parser.add_argument("--phase1b-output", type=Path, default=DEFAULT_PHASE1B_REPORT, help="Phase 1B public report output path")
    parser.add_argument("--phase1c-output", type=Path, default=DEFAULT_PHASE1C_REPORT, help="Phase 1C public report output path")
    parser.add_argument("--phase1d-output", type=Path, default=DEFAULT_PHASE1D_REPORT, help="Phase 1D public report output path")
    parser.add_argument("--phase1e-output", type=Path, default=DEFAULT_PHASE1E_REPORT, help="Phase 1E public report output path")
    args = parser.parse_args(argv)

    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "passed" else 1
    if args.write_phase1c_manifest_template:
        write_phase1c_manifest_template(args.write_phase1c_manifest_template)
        print(json.dumps({"status": "phase1c_private_manifest_template_written", "path": str(args.write_phase1c_manifest_template)}, indent=2, sort_keys=True))
        return 0
    if args.write_phase1c_local_example_manifest:
        write_phase1c_local_example_manifest(args.write_phase1c_local_example_manifest)
        print(json.dumps({"status": "phase1c_local_private_manifest_written", "path": str(args.write_phase1c_local_example_manifest)}, indent=2, sort_keys=True))
        return 0
    if args.write_phase1d_local_example_manifest:
        write_phase1d_local_example_manifest(args.write_phase1d_local_example_manifest)
        print(json.dumps({"status": "phase1d_local_private_manifest_written", "path": str(args.write_phase1d_local_example_manifest)}, indent=2, sort_keys=True))
        return 0
    if args.validate_report:
        errors = validate_report_file(args.validate_report)
        if errors:
            print("Validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.validate_aggregate_screen:
        errors = validate_aggregate_screen_file(args.validate_aggregate_screen)
        if errors:
            print("Aggregate screen validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Aggregate screen validation passed: {args.validate_aggregate_screen}")
        return 0
    if args.validate_phase1b_report:
        errors = validate_phase1b_report_file(args.validate_phase1b_report)
        if errors:
            print("Phase 1B report validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Phase 1B report validation passed: {args.validate_phase1b_report}")
        return 0
    if args.validate_phase1c_report:
        errors = validate_phase1c_report_file(args.validate_phase1c_report)
        if errors:
            print("Phase 1C report validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Phase 1C report validation passed: {args.validate_phase1c_report}")
        return 0
    if args.validate_phase1d_report:
        errors = validate_phase1d_report_file(args.validate_phase1d_report)
        if errors:
            print("Phase 1D report validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Phase 1D report validation passed: {args.validate_phase1d_report}")
        return 0
    if args.validate_phase1e_report:
        errors = validate_phase1e_report_file(args.validate_phase1e_report)
        if errors:
            print("Phase 1E report validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Phase 1E report validation passed: {args.validate_phase1e_report}")
        return 0
    if args.run_phase1e_diagnostic:
        try:
            result = run_phase1e_diagnostic(confirm_private_input=args.confirm_private_input, phase1c_private_rows=args.phase1c_private_rows, phase1d_private_rows=args.phase1d_private_rows, output=args.phase1e_output)
        except PreflightError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.run_phase1d_real_source:
        try:
            result = run_phase1d_real_source(confirm_private_output=args.confirm_private_output, output=args.phase1d_output, private_manifest=args.phase1d_private_manifest)
        except PreflightError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        result.pop("_private_manifest", None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.run_phase1c_real_source:
        try:
            result = run_phase1c_real_source(confirm_private_output=args.confirm_private_output, output=args.phase1c_output, private_manifest=args.phase1c_private_manifest)
        except PreflightError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        result.pop("_private_manifest", None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.run_phase1b_micro_policy:
        try:
            result = run_phase1b_micro_policy(confirm_private_output=args.confirm_private_output, output=args.phase1b_output)
        except PreflightError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        result.pop("_private_manifest", None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.dry_run or args.confirm_private_output:
        result = run_capture(confirm_private_output=args.confirm_private_output, dry_run=args.dry_run, output=args.output)
        result.pop("_private_manifest", None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.aggregate_private_rows:
        result = run_aggregate_private_rows(args.private_rows_path, args.aggregate_output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
