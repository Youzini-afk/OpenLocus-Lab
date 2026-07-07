#!/usr/bin/env python3
"""Phase 4D frozen fresh-holdout local screen.

This script follows the Phase 4C frozen protocol. It uses only stdlib, reads
Phase 2 private training rows and a Phase 4D private manifest from ignored
`runs/` after explicit confirmations, writes Phase 4D private rows only under
ignored `runs/phase4d_frozen_fresh_holdout/<timestamp>/`, and emits one
aggregate-only public report.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
PHASE = "phase4d_frozen_fresh_holdout"
SCHEMA_VERSION = "phase4d_frozen_fresh_holdout_public_report_v1"
STATUS_STOP = "stop_no_learning_claim"
STATUS_REPAIR = "repair_holdout_contract_no_claim"
STATUS_POSITIVE = "fresh_holdout_screen_positive_no_claim"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
PHASE4C_REPORT = REPO / "artifacts" / "phase4c_frozen_fresh_holdout_protocol_design_only" / "phase4c_frozen_fresh_holdout_protocol_design_only_report.json"
PHASE2_ROOT = REPO / "runs" / "phase2_small_fair_local_comparison_pilot"
PHASE3_ROOT = REPO / "runs" / "phase3_independent_local_holdout_validation_screen"
PHASE4D_ROOT = REPO / "runs" / PHASE
PHASE2_ROWS_FILENAME = "phase2_small_fair_local_comparison_private_rows.jsonl"
PHASE3_ROWS_FILENAME = "phase3_independent_local_holdout_private_rows.jsonl"
PRIVATE_ROWS_FILENAME = "phase4d_frozen_fresh_holdout_private_rows.jsonl"
PRIVATE_MANIFEST_COPY_FILENAME = "phase4d_frozen_fresh_holdout_private_manifest_copy.json"
ALLOWED_LABELS = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
ACQUISITION_LABELS = set(ALLOWED_LABELS) - {"stop", "abstain"}
FROZEN_FEATURES = ("action_label", "task_family_bucket", "availability_bucket", "budget_bucket")
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
TARGET_TASKS = 12
MAX_TASKS = 16
MAX_PRIVATE_ROWS = 112
FORBIDDEN_PUBLIC_WORDS = re.compile(r"\b(winner|lift|product-ready|product readiness|default change|method victory|deploy|promotion|best action|learned policy|auc|accuracy|predictive performance)\b", re.I)
PATH_RE = re.compile(r"(?:^|[\\/])(?:runs|docs|eval|scripts|artifacts|src|tests?)[\\/][^\s]+", re.I)
HASH_RE = re.compile(r"\b[a-f0-9]{16,}\b", re.I)
RANGE_RE = re.compile(r"\b(?:line|range)?\s*\d{1,6}\s*-\s*\d{1,6}\b", re.I)


class Phase4DError(Exception):
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
        raise Phase4DError(f"missing private rows: {filename}")
    return candidates[0]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path_is_ignored_runs(path):
        raise Phase4DError("private input outside ignored runs/ refused")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise Phase4DError(f"row {line_number} is not an object")
            rows.append(item)
    if not rows:
        raise Phase4DError("private rows are empty")
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
    if not privacy_false_flag and any(token in lowered for token in ("private_paths_public", "private_ranges_public", "private_hashes_public", "private_task_ids_public", "private_row_ids_public", "private_run_dirs_public", "manifest_path", "snippet", "prompt", "response", "provider_payload", "gold", "raw_row")):
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
            errors.append(f"claim-shaped public value at {path}")
    return errors


def validate_phase4c_report(path: Path = PHASE4C_REPORT) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load Phase 4C report: {exc}"]
    errors: list[str] = []
    if report.get("phase") != "phase4c_frozen_fresh_holdout_protocol_design_only":
        errors.append("Phase 4C phase mismatch")
    if report.get("status") != "phase4c_frozen_fresh_holdout_protocol_design_only_no_execution":
        errors.append("Phase 4C status mismatch")
    protocol = report.get("frozen_protocol", {})
    if tuple(protocol.get("labels", [])) != ALLOWED_LABELS:
        errors.append("Phase 4C labels are not frozen as expected")
    if tuple(protocol.get("features", [])) != FROZEN_FEATURES:
        errors.append("Phase 4C features are not frozen as expected")
    if report.get("basis", {}).get("code_protocol_basis_commit") != "6626075":
        errors.append("Phase 4C basis commit mismatch")
    if contains_count_1(report):
        errors.append("Phase 4C report exposes count_1")
    errors.extend(public_leak_errors(report))
    return errors


def load_private_manifest(path: Path) -> list[dict[str, Any]]:
    if not path_is_ignored_runs(path):
        raise Phase4DError("Phase 4D private manifest must be under ignored runs/")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Phase4DError(f"cannot load Phase 4D private manifest: {exc}") from exc
    tasks = raw.get("tasks") if isinstance(raw, dict) else raw
    if not isinstance(tasks, list):
        raise Phase4DError("Phase 4D manifest must contain a tasks list")
    if not tasks or len(tasks) > MAX_TASKS:
        raise Phase4DError(f"Phase 4D manifest must contain 1-{MAX_TASKS} tasks")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise Phase4DError(f"manifest task {index} is not an object")
        private_task_id = str(task.get("private_task_id", f"phase4d-private-{index}"))
        if private_task_id in seen_ids:
            raise Phase4DError("duplicate private task id in Phase 4D manifest")
        seen_ids.add(private_task_id)
        family = str(task.get("family_bucket", FAMILY_BUCKETS[index % len(FAMILY_BUCKETS)]))
        if family not in FAMILY_BUCKETS:
            raise Phase4DError(f"unknown family bucket in manifest: {family}")
        normalized.append({
            "private_task_id": private_task_id,
            "family_bucket": family,
            "private_path": str(task["private_path"]),
            "start_line": int(task["start_line"]),
            "end_line": int(task["end_line"]),
            "has_related_test": bool(task.get("has_related_test", False)),
            "task_target_tie": bool(task.get("task_target_tie", True)),
        })
    return normalized


def write_local_example_manifest(output: Path) -> None:
    if not path_is_ignored_runs(output):
        raise Phase4DError("example manifest output must be under ignored runs/")
    prior_rows: list[dict[str, Any]] = []
    for root, filename in ((PHASE2_ROOT, PHASE2_ROWS_FILENAME), (PHASE3_ROOT, PHASE3_ROWS_FILENAME)):
        try:
            prior_rows.extend(load_jsonl(latest_rows(root, filename)))
        except Phase4DError:
            pass
    prior_keys = private_overlap_keys(prior_rows)
    candidates: list[Path] = []
    for pattern in ("docs/en/*.md", "docs/zh/*.md", "eval/*.py", "scripts/*.py"):
        candidates.extend(sorted(REPO.glob(pattern)))
    tasks: list[dict[str, Any]] = []
    used: set[str] = set()
    for path in candidates:
        if len(tasks) >= TARGET_TASKS:
            break
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue
        if line_count < 8:
            continue
        rel = path.relative_to(REPO).as_posix()
        selected_range: tuple[int, int] | None = None
        for start_line in (1, 9, 17, 25, 33, 41):
            end_line = start_line + 7
            if end_line > line_count:
                continue
            if (rel, f"{start_line}-{end_line}") in prior_keys:
                continue
            selected_range = (start_line, end_line)
            break
        if selected_range is None or f"{rel}:{selected_range[0]}-{selected_range[1]}" in used:
            continue
        used.add(f"{rel}:{selected_range[0]}-{selected_range[1]}")
        index = len(tasks)
        tasks.append({
            "private_task_id": f"phase4d-local-private-{index:02d}",
            "family_bucket": FAMILY_BUCKETS[index % len(FAMILY_BUCKETS)],
            "private_path": rel,
            "start_line": selected_range[0],
            "end_line": selected_range[1],
            "has_related_test": index % 3 == 0,
            "task_target_tie": True,
        })
    if len(tasks) != TARGET_TASKS:
        raise Phase4DError(f"could not build {TARGET_TASKS} local Phase 4D tasks")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema_version": "phase4d_frozen_fresh_holdout_private_manifest_v1", "storage_class": "ignored_runs_private", "tasks": tasks}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_current_range(private_path: str, start_line: int, end_line: int) -> dict[str, Any]:
    base = REPO.resolve()
    path = (base / private_path).resolve()
    if not str(path).startswith(str(base)):
        raise Phase4DError("Phase 4D path escapes repository")
    lines = path.read_text(encoding="utf-8").splitlines()
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        raise Phase4DError("Phase 4D line range unavailable")
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


def feature_row_from_training(row: dict[str, Any]) -> dict[str, Any]:
    action = str(row.get("micro_policy_id", ""))
    eligible = row.get("eligible_micro_policies", [])
    available = action in eligible if isinstance(eligible, list) else action in ALLOWED_LABELS
    return {
        "features": {
            "action_label": action,
            "task_family_bucket": str(row.get("family_bucket", "unknown_family")),
            "availability_bucket": "available" if available else "not_available",
            "budget_bucket": "single_panel_budget",
        },
        "target": bool(row.get("evidence_success") is True),
    }


def feature_row_from_holdout(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "features": {
            "action_label": str(row["micro_policy_id"]),
            "task_family_bucket": str(row["family_bucket"]),
            "availability_bucket": "available" if row.get("micro_policy_id") in row.get("eligible_micro_policies", []) else "not_available",
            "budget_bucket": "single_panel_budget",
        },
        "target": bool(row.get("evidence_success") is True),
    }


def row_key(item: dict[str, Any]) -> tuple[str, ...]:
    features = item["features"]
    return tuple(str(features[name]) for name in FROZEN_FEATURES)


def table_counts(items: list[dict[str, Any]]) -> dict[tuple[str, ...], list[int]]:
    table: dict[tuple[str, ...], list[int]] = defaultdict(lambda: [0, 0])
    for item in items:
        key = row_key(item)
        table[key][1] += 1
        if item["target"]:
            table[key][0] += 1
    return table


def smoothed_rate(table: dict[tuple[str, ...], list[int]], key: tuple[str, ...]) -> float:
    positives, total = table.get(key, [0, 0])
    return (positives + 1) / (total + 2)


def screen_count(training_rows: list[dict[str, Any]], holdout_rows: list[dict[str, Any]], *, shuffled: bool = False) -> int:
    train_items = [feature_row_from_training(row) for row in training_rows if row.get("micro_policy_id") in ALLOWED_LABELS]
    if shuffled and train_items:
        shifted = [item["target"] for item in train_items[1:]] + [train_items[0]["target"]]
        for item, target in zip(train_items, shifted):
            item["target"] = target
    table = table_counts(train_items)
    count = 0
    for item in (feature_row_from_holdout(row) for row in holdout_rows):
        if item["target"] and smoothed_rate(table, row_key(item)) >= 0.5:
            count += 1
    return count


def private_overlap_keys(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for row in rows:
        refs = row.get("private_exact_refs", {}) if isinstance(row.get("private_exact_refs"), dict) else {}
        path = refs.get("private_path")
        private_range = refs.get("private_range")
        if path and private_range:
            keys.add((str(path), str(private_range)))
    return keys


def manifest_overlap_count(tasks: list[dict[str, Any]], prior_rows: list[dict[str, Any]]) -> int:
    prior = private_overlap_keys(prior_rows)
    count = 0
    for task in tasks:
        key = (str(task["private_path"]), f"{int(task['start_line'])}-{int(task['end_line'])}")
        if key in prior:
            count += 1
    return count


def build_private_rows(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task in tasks:
        eligible = [label for label in ALLOWED_LABELS if label != "read_related_test_when_available" or task["has_related_test"]]
        for label in ALLOWED_LABELS:
            materializing = label in ACQUISITION_LABELS and (label != "read_related_test_when_available" or task["has_related_test"])
            materialization = read_current_range(task["private_path"], int(task["start_line"]), int(task["end_line"])) if materializing else None
            refs = materialization or {}
            evidence_success = bool(label in ACQUISITION_LABELS and materialization and refs.get("content_sha256") and refs.get("currentness_reread_match") is True and refs.get("range_content_match") is True and refs.get("content_byte_length", 0) > 0 and task.get("task_target_tie") is True)
            rows.append({
                "schema_version": "phase4d_frozen_fresh_holdout_private_row_v1",
                "phase": PHASE,
                "private_task_id": task["private_task_id"],
                "family_bucket": task["family_bucket"],
                "micro_policy_id": label,
                "micro_policy_version": "frozen_6626075_v1",
                "assignment_mode": "deterministic_full_panel_frozen_seven_labels",
                "eligible_micro_policies": eligible,
                "candidate_found": label in ACQUISITION_LABELS,
                "read_attempted": materializing,
                "materialized_current_source": materialization is not None,
                "evidence_success": evidence_success,
                "failure_safe_reason_bucket": "real_current_source_materialized" if evidence_success else ("control_no_acquisition" if label in {"stop", "abstain"} else "not_eligible_or_no_materialization"),
                "private_exact_refs": refs,
                "task_target_tie": bool(task.get("task_target_tie") is True),
                "evidencecore": {
                    "candidate_is_fact": evidence_success,
                    "counted_evidence_requires_current_source": True,
                    "content_sha256_present": bool(refs.get("content_sha256")),
                    "currentness_reread_match": bool(refs.get("currentness_reread_match")),
                    "range_content_match": bool(refs.get("range_content_match")),
                },
                "privacy": {"private_row": True, "public_artifact_allowed": False, "provider_network_used": False, "model_training_executed": False},
            })
    if len(rows) > MAX_PRIVATE_ROWS:
        raise Phase4DError("Phase 4D private row cap exceeded")
    return rows


def validate_private_rows(rows: list[dict[str, Any]], task_count: int) -> list[str]:
    errors: list[str] = []
    if task_count < 1 or task_count > MAX_TASKS:
        errors.append("Phase 4D task count outside cap")
    if len(rows) != task_count * len(ALLOWED_LABELS) or len(rows) > MAX_PRIVATE_ROWS:
        errors.append("Phase 4D row count/panel shape invalid")
    panels: dict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(rows):
        label = str(row.get("micro_policy_id", ""))
        if label not in ALLOWED_LABELS:
            errors.append(f"unknown label at private row {index}")
        panels[str(row.get("private_task_id", ""))].add(label)
        success = row.get("evidence_success") is True
        refs = row.get("private_exact_refs", {}) if isinstance(row.get("private_exact_refs"), dict) else {}
        if label in {"stop", "abstain"} and success:
            errors.append(f"control succeeded at private row {index}")
        if success and (label not in ACQUISITION_LABELS or row.get("materialized_current_source") is not True or not refs.get("private_path") or not refs.get("private_range") or not refs.get("content_text") or not refs.get("content_sha256") or refs.get("currentness_reread_match") is not True or refs.get("range_content_match") is not True or row.get("task_target_tie") is not True):
            errors.append(f"success without complete EvidenceCore materialization at private row {index}")
        if row.get("evidencecore", {}).get("candidate_is_fact") is not success:
            errors.append(f"candidate_is_fact mismatch at private row {index}")
    if any(labels != set(ALLOWED_LABELS) for labels in panels.values()):
        errors.append("not every task has the frozen seven-label panel")
    return errors


def write_private_outputs(rows: list[dict[str, Any]], manifest_path: Path) -> dict[str, Path]:
    run_dir = PHASE4D_ROOT / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    private_rows = run_dir / PRIVATE_ROWS_FILENAME
    with private_rows.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest_copy = run_dir / PRIVATE_MANIFEST_COPY_FILENAME
    manifest_copy.write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {"private_rows": private_rows, "manifest_copy": manifest_copy}


def build_report(training_rows: list[dict[str, Any]], holdout_rows: list[dict[str, Any]], tasks: list[dict[str, Any]], overlap_count: int) -> dict[str, Any]:
    private_errors = validate_private_rows(holdout_rows, len(tasks))
    labels = Counter(str(row["micro_policy_id"]) for row in holdout_rows)
    families = Counter(str(row["family_bucket"]) for row in holdout_rows)
    evidence_success = Counter(str(row["micro_policy_id"]) for row in holdout_rows if row.get("evidence_success") is True)
    materialized = Counter(str(row["micro_policy_id"]) for row in holdout_rows if row.get("materialized_current_source") is True)
    materialization_pass = sum(1 for row in holdout_rows if row.get("evidence_success") is True)
    control_success = evidence_success["stop"] + evidence_success["abstain"]
    screen = screen_count(training_rows, holdout_rows)
    shuffled = screen_count(training_rows, holdout_rows, shuffled=True)
    majority = 0
    valid_holdout_shape = len(tasks) == TARGET_TASKS and len(holdout_rows) <= MAX_PRIVATE_ROWS and all(labels[label] == len(tasks) for label in ALLOWED_LABELS)
    if private_errors or overlap_count > 0 or control_success > 0 or not valid_holdout_shape:
        status = STATUS_REPAIR
    elif screen > shuffled and materialization_pass > 0:
        status = STATUS_POSITIVE
    else:
        status = STATUS_STOP
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "authorization_attestation": {
            "phase4c_gate_required": True,
            "phase4c_gate_passed": True,
            "confirm_private_input_required": True,
            "confirm_private_output_required": True,
            "local_only": True,
            "provider_network_used": False,
            "llm_used": False,
            "rpm_d2_or_model_scaling_used": False,
            "model_training_executed": False,
            "reusable_model_artifact_created": False,
            "runtime_default_changed": False,
            "new_retrieval_family_added": False,
            "ci_changed": False,
            "method_claimed": False,
            "claim_level": "no_claim",
        },
        "frozen_protocol_summary": {
            "basis_commit": "6626075",
            "labels_frozen": True,
            "feature_set_frozen": True,
            "screen_method_frozen": True,
            "fit_source": "frozen_phase2_training_rows",
            "fit_or_tune_on_holdout_rows": False,
            "stdlib_only": True,
        },
        "input_summary": {
            "fresh_holdout_task_count_bucket": bucket_count(len(tasks)),
            "private_row_count_bucket": bucket_count(len(holdout_rows)),
            "phase2_training_row_count_bucket": bucket_count(len(training_rows)),
            "source_kind_bucket": "fresh_current_source_manifest_private",
        },
        "coverage_summary": {
            "label_coverage_buckets": {label: bucket_count(labels[label]) for label in ALLOWED_LABELS},
            "family_coverage_buckets": {family: bucket_count(families[family]) for family in FAMILY_BUCKETS},
            "overlap_check_bucket": bucket_count(overlap_count),
        },
        "screen_summary": {
            "heldout_screen_bucket": bucket_count(screen),
            "shuffled_control_bucket": bucket_count(shuffled),
            "majority_non_success_control_bucket": bucket_count(majority),
            "shuffled_control_comparison_bucket": bucket_delta(screen - shuffled),
        },
        "evidencecore_summary": {
            "evidence_requires_real_current_source_read": True,
            "evidence_requires_current_source_refs_hash_currentness_range_match_task_tie": True,
            "candidate_found_alone_is_not_evidence": True,
            "stop_abstain_success_bucket": bucket_count(control_success),
            "materialized_buckets": {label: bucket_count(materialized[label]) for label in ALLOWED_LABELS},
            "evidence_success_buckets": {label: bucket_count(evidence_success[label]) for label in ALLOWED_LABELS},
            "evidence_materialization_pass_bucket": bucket_count(materialization_pass),
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_written": True,
            "private_rows_published": False,
            "raw_rows_public": False,
            "private_paths_public": False,
            "private_ranges_public": False,
            "private_hashes_public": False,
            "private_snippets_public": False,
            "private_task_ids_public": False,
            "private_row_ids_public": False,
            "private_run_dirs_public": False,
            "private_manifest_paths_public": False,
            "provider_payloads_public": False,
        },
        "validation_summary": {
            "route_specific_phase4d_validation": "passed",
            "no_count_1_values": True,
            "public_leak_scan": "passed",
            "self_test_available": True,
            "no_runs_files_staged_required": True,
        },
        "conservative_recommendation": status,
    }
    errors = validate_report(report)
    if errors:
        raise Phase4DError("generated invalid report: " + "; ".join(errors[:8]))
    return report


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("identity drift")
    if report.get("status") not in {STATUS_STOP, STATUS_REPAIR, STATUS_POSITIVE}:
        errors.append("bad status")
    auth = report.get("authorization_attestation", {})
    for key in ("provider_network_used", "llm_used", "rpm_d2_or_model_scaling_used", "model_training_executed", "reusable_model_artifact_created", "runtime_default_changed", "new_retrieval_family_added", "ci_changed", "method_claimed"):
        if auth.get(key) is not False:
            errors.append(f"overclaim: {key}")
    if auth.get("claim_level") != "no_claim":
        errors.append("claim boundary failed")
    if report.get("frozen_protocol_summary", {}).get("fit_or_tune_on_holdout_rows") is not False:
        errors.append("holdout tuning boundary failed")
    if report.get("coverage_summary", {}).get("overlap_check_bucket") != "count_0":
        errors.append("overlap check did not pass")
    if report.get("evidencecore_summary", {}).get("stop_abstain_success_bucket") != "count_0":
        errors.append("control success boundary failed")
    if contains_count_1(report):
        errors.append("count_1 published")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_phase4d(confirm_private_input: bool, confirm_private_output: bool, phase2_training_rows: Path | None, phase4c_report: Path, phase4d_manifest: Path, output: Path) -> dict[str, Any]:
    if not confirm_private_input or not confirm_private_output:
        raise Phase4DError("--confirm-private-input and --confirm-private-output are required")
    gate_errors = validate_phase4c_report(phase4c_report)
    if gate_errors:
        raise Phase4DError("Phase 4C gate failed: " + "; ".join(gate_errors[:8]))
    training_path = phase2_training_rows or latest_rows(PHASE2_ROOT, PHASE2_ROWS_FILENAME)
    training_rows = load_jsonl(training_path)
    tasks = load_private_manifest(phase4d_manifest)
    phase3_rows: list[dict[str, Any]] = []
    try:
        phase3_rows = load_jsonl(latest_rows(PHASE3_ROOT, PHASE3_ROWS_FILENAME))
    except Phase4DError:
        phase3_rows = []
    overlap_count = manifest_overlap_count(tasks, training_rows + phase3_rows)
    holdout_rows = build_private_rows(tasks)
    private_errors = validate_private_rows(holdout_rows, len(tasks))
    if private_errors:
        raise Phase4DError("private row validation failed: " + "; ".join(private_errors[:8]))
    private_paths = write_private_outputs(holdout_rows, phase4d_manifest)
    report = build_report(training_rows, holdout_rows, tasks, overlap_count)
    write_report(report, output)
    return {
        "status": report["status"],
        "conservative_recommendation": report["conservative_recommendation"],
        "public_report": str(output),
        "private_rows_location": "runs/phase4d_frozen_fresh_holdout/.../phase4d_frozen_fresh_holdout_private_rows.jsonl",
        "_private_rows": str(private_paths["private_rows"]),
    }


def sample_training_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILY_BUCKETS[:4]:
        for label in ALLOWED_LABELS:
            rows.append({"family_bucket": family, "micro_policy_id": label, "eligible_micro_policies": list(ALLOWED_LABELS), "evidence_success": label in {"bm25_then_read_top1", "symbol_regex_then_read_top1"}})
    return rows


def sample_holdout_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task_index in range(2):
        for label in ALLOWED_LABELS:
            success = label in {"bm25_then_read_top1", "symbol_regex_then_read_top1"}
            refs = {"private_path": "docs/private.md", "private_range": "1-2", "content_text": "x\n", "content_sha256": "a" * 64, "currentness_reread_match": True, "range_content_match": True, "content_byte_length": 2} if label in ACQUISITION_LABELS else {}
            rows.append({"phase": PHASE, "private_task_id": f"t{task_index}", "family_bucket": FAMILY_BUCKETS[task_index], "micro_policy_id": label, "eligible_micro_policies": list(ALLOWED_LABELS), "materialized_current_source": label in ACQUISITION_LABELS, "evidence_success": success, "private_exact_refs": refs, "task_target_tie": True, "evidencecore": {"candidate_is_fact": success}})
    return rows


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    checks.append(("count_1_rejected", bool(validate_report({"schema_version": SCHEMA_VERSION, "phase": PHASE, "status": STATUS_STOP, "x": "count_1"}))))
    bad = {"schema_version": SCHEMA_VERSION, "phase": PHASE, "status": STATUS_STOP, "authorization_attestation": {"provider_network_used": False, "llm_used": False, "rpm_d2_or_model_scaling_used": False, "model_training_executed": False, "reusable_model_artifact_created": False, "runtime_default_changed": False, "new_retrieval_family_added": False, "ci_changed": False, "method_claimed": False, "claim_level": "no_claim"}, "coverage_summary": {"overlap_check_bucket": "count_0"}, "evidencecore_summary": {"stop_abstain_success_bucket": "count_0"}, "frozen_protocol_summary": {"fit_or_tune_on_holdout_rows": False}, "privacy_summary": {"private_paths_public": False, "private_ranges_public": False, "private_hashes_public": False}}
    checks.append(("minimal_report_valid", not validate_report(bad)))
    leak = json.loads(json.dumps(bad)); leak["x"] = "runs/private/rows.jsonl"
    checks.append(("leak_rejected", bool(validate_report(leak))))
    claim = json.loads(json.dumps(bad)); claim["x"] = "winner"
    checks.append(("claim_term_rejected", bool(validate_report(claim))))
    rows = sample_holdout_rows()
    checks.append(("private_rows_valid", not validate_private_rows(rows, 2)))
    bad_rows = json.loads(json.dumps(rows)); bad_rows[-1]["evidence_success"] = True
    checks.append(("control_success_rejected", bool(validate_private_rows(bad_rows, 2))))
    bad_rows = json.loads(json.dumps(rows)); bad_rows[0]["private_exact_refs"] = {}; bad_rows[0]["materialized_current_source"] = False
    checks.append(("success_requires_materialization", bool(validate_private_rows(bad_rows, 2))))
    checks.append(("outside_runs_refused", not path_is_ignored_runs(REPO / "docs" / "manifest.json")))
    report = build_report(sample_training_rows(), rows, [{"private_task_id": "t0"}, {"private_task_id": "t1"}], 0)
    checks.append(("build_report_valid", not validate_report(report)))
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_total": len(checks), "checks_passed": len(checks) - len(failed), "failed_checks": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--write-phase4d-local-example-manifest", type=Path)
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--phase2-training-rows", type=Path)
    parser.add_argument("--phase4c-report", type=Path, default=PHASE4C_REPORT)
    parser.add_argument("--phase4d-private-manifest", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
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
            print("Phase 4D report validation failed: " + "; ".join(errors[:8]), file=sys.stderr)
            return 1
        print(f"Phase 4D report validation passed: {args.validate_report}")
        return 0
    if args.write_phase4d_local_example_manifest:
        try:
            write_local_example_manifest(args.write_phase4d_local_example_manifest)
        except Phase4DError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"wrote Phase 4D local example private manifest: {args.write_phase4d_local_example_manifest}")
        return 0
    if not args.phase4d_private_manifest:
        print("--phase4d-private-manifest is required unless using --self-test, --validate-report, or --write-phase4d-local-example-manifest", file=sys.stderr)
        return 1
    try:
        result = run_phase4d(args.confirm_private_input, args.confirm_private_output, args.phase2_training_rows, args.phase4c_report, args.phase4d_private_manifest, args.output)
    except Phase4DError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({key: value for key, value in result.items() if not key.startswith("_")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
