#!/usr/bin/env python3
"""Phase 9D bounded task-candidate materialization helper.

This runner has one narrow purpose: under explicit confirmations, read the
ignored Phase 9B private accepted-source registry, deterministically attempt to
materialize private file-localizable task-candidate rows, and publish only an
aggregate public report.  It does not score strategies, create benchmark labels,
record outcomes, evaluate evidence success, fit/train models, call providers or
LLMs, or change runtime/default/product behavior.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

PHASE = "phase9d_task_candidate_materialization_no_scoring_no_claim"
STATUS_PASS = "phase9d_task_candidate_materialization_no_scoring_no_claim"
STATUS_REPAIR = "repair_task_materialization_no_claim"
STATUS_STOP = "stop_task_materialization_no_claim"
ALLOWED_STATUSES = {STATUS_PASS, STATUS_REPAIR, STATUS_STOP}
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

PHASE9C_STATUS = "phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim"
PHASE9C_PUBLIC_REPORT = REPO / "artifacts" / PHASE9C_STATUS / f"{PHASE9C_STATUS}_report.json"
PHASE9C_DOCS = (
    REPO / "docs" / "en" / "interventional-evidence-acquisition-phase9c-task-construction-materialization-protocol-freeze.md",
    REPO / "docs" / "zh" / "interventional-evidence-acquisition-phase9c-task-construction-materialization-protocol-freeze.md",
)
PHASE9B_PRIVATE_REGISTRY_GLOB = "phase9b_clean_room_source_construction_audit/**/private_candidate_registry.json"

TARGET_TASK_MIN = 48
TARGET_TASK_MAX = 72
HARD_TASK_CAP = 96
PER_SOURCE_TASK_CAP = 8
MIN_DISTINCT_SOURCES = 8
MAX_FILE_BYTES = 512_000
LINE_WINDOW = 24

CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".lua",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sol",
    ".swift",
    ".ts",
    ".tsx",
}

FORBIDDEN_PUBLIC_FIELD_WORDS = ("scoring", "labels", "outcomes", "evidence_success")
CLAIM_BOUNDARY_FALSE_KEYS = (
    "method_claim",
    "product_claim",
    "performance_claim",
    "training_claim",
    "provider_claim",
    "model_claim",
    "runtime_claim",
    "default_claim",
)
FORBIDDEN_EXECUTION_FALSE_KEYS = (
    "strategy_evaluation_executed",
    "benchmark_annotation_generated",
    "result_annotation_generated",
    "evidence_result_evaluation_executed",
    "model_fitting_executed",
    "provider_or_llm_calls_executed",
    "runtime_default_or_product_changes_executed",
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
    "manifest_locations_public",
    "run_locations_public",
    "unit_source_facts_public",
    "unit_task_facts_public",
    "singleton_buckets_public",
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]|(?:^|\s)/[A-Za-z0-9_.-]+/|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9])", re.IGNORECASE)
PRIVATE_KEY_RE = re.compile(
    r"^(?:repo|repo_name|repo_url|owner|url|source_url|candidate_identity|commit|commit_sha|sha|hash|path|range|snippet|task_id|row_id|manifest|run_dir|per_source|per_task)$",
    re.IGNORECASE,
)

PRIVATE_REGISTRY_READ_ATTEMPTS = 0
SOURCE_FILE_READ_ATTEMPTS = 0


def _bucket_quantity(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < MIN_DISTINCT_SOURCES:
        return "bucket_nonzero_below_minimum"
    if value < TARGET_TASK_MIN:
        return "bucket_at_least_minimum_below_target"
    if value <= TARGET_TASK_MAX:
        return "bucket_target_48_to_72"
    if value <= HARD_TASK_CAP:
        return "bucket_above_target_within_hard_cap"
    return "bucket_over_hard_cap"


def _bucket_sources(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < MIN_DISTINCT_SOURCES:
        return "bucket_nonzero_below_minimum"
    if value <= 12:
        return "bucket_minimum_met_low"
    if value <= 24:
        return "bucket_minimum_met_mid"
    return "bucket_minimum_met_high"


def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def _assert_under_ignored_runs(path: Path) -> Path:
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if resolved != runs_root and runs_root not in resolved.parents:
        raise ValueError("private output must stay under ignored runs/")
    if not _runs_is_ignored():
        raise ValueError("runs/ must remain ignored before private output is allowed")
    return resolved


def _phase9c_gate_errors(report: Any | None = None, docs_text: str | None = None) -> list[str]:
    errors: list[str] = []
    if report is None:
        if not PHASE9C_PUBLIC_REPORT.exists():
            return ["Phase 9C public report missing"]
        report = json.loads(PHASE9C_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9C public report must be object"]
    if report.get("phase") != PHASE9C_STATUS or report.get("status") != PHASE9C_STATUS:
        errors.append("Phase 9C public report status drift")
    if report.get("schema_version") != f"{PHASE9C_STATUS}_report_v1":
        errors.append("Phase 9C public report schema drift")
    phase9d_boundary = report.get("future_protocol_summary", {}).get("phase9d_execution_caps_and_stops", {})
    if phase9d_boundary.get("future_phase9d_may_only_construct_and_materialize_task_candidates") is not True:
        errors.append("Phase 9C does not authorize bounded Phase 9D materialization")
    if phase9d_boundary.get("future_strategy_scoring_requires_another_frozen_boundary") is not True:
        errors.append("Phase 9C later strategy boundary missing")
    if phase9d_boundary.get("stop_if_source_or_task_diversity_below_minimum_after_caps") is not True:
        errors.append("Phase 9C diversity stop missing")
    scope = report.get("phase9c_scope", {})
    if scope.get("phase9d_execution_requires_later_boundary_after_phase9c_commit_and_ci_green") is not True:
        errors.append("Phase 9C commit/CI-green boundary missing")
    gate = report.get("phase9b_gate_references", {})
    if not gate.get("phase9b_ci_run") or gate.get("phase9b_ci_success") is not True:
        errors.append("Phase 9C report CI reference missing")

    if docs_text is None:
        missing_docs = [path for path in PHASE9C_DOCS if not path.exists()]
        if missing_docs:
            errors.append("Phase 9C docs missing")
        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in PHASE9C_DOCS if path.exists())
    if PHASE9C_STATUS not in docs_text:
        errors.append("Phase 9C docs status reference missing")
    if "CI green" not in docs_text and "CI run" not in docs_text:
        errors.append("Phase 9C docs CI reference missing")
    return sorted(set(errors))


def _load_phase9c_gate() -> dict[str, Any]:
    errors = _phase9c_gate_errors()
    if errors:
        raise ValueError("Phase 9C gate failed: " + "; ".join(errors))
    return {
        "phase9c_public_report_validated": True,
        "phase9c_public_report_status": PHASE9C_STATUS,
        "phase9c_report_ci_reference_present": True,
        "phase9c_docs_ci_reference_present": True,
        "phase9c_bounded_materialization_boundary_present": True,
    }


def _find_latest_phase9b_private_registry() -> Path:
    runs_root = (REPO / "runs").resolve()
    candidates = sorted(runs_root.glob(PHASE9B_PRIVATE_REGISTRY_GLOB), key=lambda path: (path.stat().st_mtime, str(path)))
    if not candidates:
        raise FileNotFoundError("Phase 9B private registry not found under ignored runs/")
    return candidates[-1]


def _read_phase9b_private_registry(path: Path) -> dict[str, Any]:
    global PRIVATE_REGISTRY_READ_ATTEMPTS
    PRIVATE_REGISTRY_READ_ATTEMPTS += 1
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if runs_root not in resolved.parents:
        raise ValueError("Phase 9B private registry must be under ignored runs/")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Phase 9B private registry must be a JSON object")
    return payload


def _accepted_source_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = registry.get("accepted_private_registry")
    if not isinstance(rows, list):
        raise ValueError("Phase 9B private accepted-source registry missing")
    return [row for row in rows if isinstance(row, dict)]


def _candidate_source_roots(row: dict[str, Any]) -> list[Path]:
    roots: list[Path] = []
    for key in ("private_source_root", "source_root", "checkout_path", "local_source_dir", "materialized_source_dir"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = REPO / path
            if path.exists() and path.is_dir():
                roots.append(path.resolve())
    return sorted(set(roots), key=str)


def _prechecks_pass(row: dict[str, Any]) -> bool:
    return (
        row.get("publicly_accessible_without_authentication") is True
        and row.get("declared_or_publicly_auditable_license_present") is True
        and row.get("default_branch_or_equivalent_revision_resolvable") is True
    )


def _iter_code_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in CODE_SUFFIXES:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def _private_candidate_id(source_index: int, root: Path, file_path: Path, start_line: int, end_line: int) -> str:
    payload = f"{PHASE}\0{source_index}\0{root}\0{file_path}\0{start_line}\0{end_line}".encode("utf-8", errors="replace")
    return hashlib.sha256(payload).hexdigest()


def _materialize_rows(accepted_sources: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    global SOURCE_FILE_READ_ATTEMPTS
    rows: list[dict[str, Any]] = []
    source_private_summaries: list[dict[str, Any]] = []
    sources_with_rows = 0
    sources_checked = 0
    precheck_passed_sources = 0
    skipped_sources = 0

    for source_index, source in enumerate(accepted_sources):
        if len(rows) >= TARGET_TASK_MAX:
            break
        sources_checked += 1
        if not _prechecks_pass(source):
            skipped_sources += 1
            source_private_summaries.append({"source_order_index": source_index, "private_skip_reason": "license_access_or_default_branch_precheck_failed"})
            continue
        precheck_passed_sources += 1
        roots = _candidate_source_roots(source)
        if not roots:
            skipped_sources += 1
            source_private_summaries.append({"source_order_index": source_index, "private_skip_reason": "no_private_materialized_source_root_available"})
            continue

        per_source_rows = 0
        for root in roots:
            for file_path in _iter_code_files(root):
                if len(rows) >= TARGET_TASK_MAX or per_source_rows >= PER_SOURCE_TASK_CAP:
                    break
                try:
                    SOURCE_FILE_READ_ATTEMPTS += 1
                    data = file_path.read_bytes()
                except OSError:
                    continue
                if not data.strip():
                    continue
                text = data.decode("utf-8", errors="replace")
                line_total = max(1, text.count("\n") + (0 if text.endswith("\n") else 1))
                start_line = 1
                end_line = min(line_total, LINE_WINDOW)
                row = {
                    "private_candidate_id": _private_candidate_id(source_index, root, file_path, start_line, end_line),
                    "source_order_index_private": source_index,
                    "candidate_order_index_private": len(rows),
                    "task_type": "evidence_finding_file_localizable_code_task",
                    "private_source_file_path": str(file_path),
                    "private_line_range": {"start": start_line, "end": end_line},
                    "private_source_sha256": hashlib.sha256(data).hexdigest(),
                    "currentness_reread_available_private": True,
                    "license_access_default_branch_checks_passed": True,
                    "source_snippet_stored": False,
                    "replacement_policy_private": "next_deterministic_candidate_same_source_else_next_source_before_benchmark_annotations_or_strategy_evaluation",
                }
                rows.append(row)
                per_source_rows += 1
            if len(rows) >= TARGET_TASK_MAX or per_source_rows >= PER_SOURCE_TASK_CAP:
                break
        if per_source_rows:
            sources_with_rows += 1
        else:
            skipped_sources += 1
        source_private_summaries.append({"source_order_index": source_index, "private_materialized_rows": per_source_rows})
        if len(rows) >= TARGET_TASK_MIN and sources_with_rows >= MIN_DISTINCT_SOURCES:
            break

    aggregate = {
        "candidate_total": len(rows),
        "distinct_sources_with_candidates": sources_with_rows,
        "accepted_sources_checked": sources_checked,
        "precheck_passed_sources": precheck_passed_sources,
        "skipped_sources": skipped_sources,
        "hard_cap_respected": len(rows) <= HARD_TASK_CAP,
        "per_source_cap_respected": True,
        "target_bucket_met": TARGET_TASK_MIN <= len(rows) <= TARGET_TASK_MAX,
        "diversity_minimum_met": sources_with_rows >= MIN_DISTINCT_SOURCES,
        "source_file_reads_attempted": SOURCE_FILE_READ_ATTEMPTS,
    }
    private_manifest = {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "task_candidate_rows_are_inventory_only": True,
        "accepted_task_rows_remain_inventory_only_not_benchmark_annotations": True,
        "provider_or_llm_calls_executed": False,
        "model_fitting_executed": False,
        "source_snippets_stored": False,
        "materialization_rows_private": rows,
        "source_private_summaries": source_private_summaries,
        "aggregate_private_totals": aggregate,
    }
    return rows, private_manifest


def _empty_private_manifest(reason: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "task_candidate_rows_are_inventory_only": True,
        "private_stop_reason": reason,
        "materialization_rows_private": [],
        "aggregate_private_totals": {
            "candidate_total": 0,
            "distinct_sources_with_candidates": 0,
            "accepted_sources_checked": 0,
            "precheck_passed_sources": 0,
            "skipped_sources": 0,
            "hard_cap_respected": True,
            "per_source_cap_respected": True,
            "target_bucket_met": False,
            "diversity_minimum_met": False,
            "source_file_reads_attempted": SOURCE_FILE_READ_ATTEMPTS,
        },
    }


def build_public_report(
    aggregate: dict[str, Any],
    phase9c_gate: dict[str, Any],
    private_read_confirmed: bool,
    private_output_confirmed: bool,
) -> dict[str, Any]:
    candidate_total = int(aggregate.get("candidate_total", 0))
    distinct_sources = int(aggregate.get("distinct_sources_with_candidates", 0))
    gate_ok = all(
        phase9c_gate.get(key) is True
        for key in (
            "phase9c_public_report_validated",
            "phase9c_report_ci_reference_present",
            "phase9c_docs_ci_reference_present",
            "phase9c_bounded_materialization_boundary_present",
        )
    ) and phase9c_gate.get("phase9c_public_report_status") == PHASE9C_STATUS
    caps_ok = aggregate.get("hard_cap_respected") is True and aggregate.get("per_source_cap_respected") is True
    target_ok = TARGET_TASK_MIN <= candidate_total <= TARGET_TASK_MAX
    diversity_ok = distinct_sources >= MIN_DISTINCT_SOURCES
    auth_ok = private_read_confirmed is True and private_output_confirmed is True
    if not gate_ok or not caps_ok or not auth_ok:
        status = STATUS_STOP
    elif target_ok and diversity_ok:
        status = STATUS_PASS
    else:
        status = STATUS_REPAIR
    zero_materialization_repair = status == STATUS_REPAIR and candidate_total == 0 and distinct_sources == 0

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9c_gate_refs": {
            "phase9c_public_report_validated": gate_ok,
            "phase9c_public_report_status": PHASE9C_STATUS,
            "phase9c_report_ci_reference_present": phase9c_gate.get("phase9c_report_ci_reference_present") is True,
            "phase9c_docs_ci_reference_present": phase9c_gate.get("phase9c_docs_ci_reference_present") is True,
            "phase9c_bounded_materialization_boundary_present": phase9c_gate.get("phase9c_bounded_materialization_boundary_present") is True,
        },
        "private_read_authorization_attestation": {
            "phase9b_private_registry_read_confirmed": private_read_confirmed is True,
            "private_output_confirmed": private_output_confirmed is True,
            "dry_self_test_and_report_validation_read_private_registry": False,
            "dry_self_test_and_report_validation_read_source_repositories": False,
        },
        "task_candidate_inventory_summary": {
            "publication_level": "aggregate_bucketed_inventory_only",
            "candidate_type": "evidence_finding_file_localizable_code_tasks_only",
            "constructed_inventory_bucket": _bucket_quantity(candidate_total),
            "target_task_candidate_bucket": "bucket_target_48_to_72",
            "hard_cap_bucket": "bucket_up_to_96",
            "per_source_cap_bucket": "bucket_up_to_8",
            "accepted_rows_remain_inventory_only_not_benchmark_annotations": True,
            "replacement_before_benchmark_annotations_or_strategy_evaluation_only": True,
            "replacement_uses_no_performance_evidence_or_downstream_feedback": True,
        },
        "materialization_summary": {
            "private_materialization_rows_written": private_output_confirmed is True,
            "materialized_reference_bucket": _bucket_quantity(candidate_total),
            "license_access_default_branch_precheck_bucket": _bucket_sources(int(aggregate.get("precheck_passed_sources", 0))),
            "source_reference_currentness_reread_available_privately": candidate_total > 0,
            "source_snippets_public": False,
            "source_snippets_stored_private": False,
        },
        "repair_checkpoint_summary": {
            "phase9d_preserves_observed_repair_state": status == STATUS_REPAIR,
            "phase9d_preserves_zero_materialization_repair_checkpoint": zero_materialization_repair,
            "direct_private_source_root_materialization_bucket": _bucket_quantity(candidate_total),
            "public_repo_fetch_or_clone_executed": False,
            "in_place_public_fetch_repair_after_observed_repair_forbidden": True,
            "future_public_source_fetch_requires_separate_frozen_boundary": True,
            "materialization_failure_is_not_route_or_method_evidence": status == STATUS_REPAIR,
            "materialization_itself_is_not_result_evidence": True,
        },
        "diversity_summary": {
            "minimum_distinct_sources_bucket": "bucket_at_least_8",
            "observed_distinct_sources_bucket": _bucket_sources(distinct_sources),
            "diversity_minimum_met": diversity_ok,
            "stop_or_repair_if_below_minimum_after_caps": True,
        },
        "forbidden_execution_boundary": {key: False for key in FORBIDDEN_EXECUTION_FALSE_KEYS},
        "no_claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "privacy_summary": {
            "public_output_aggregate_only": True,
            "private_outputs_under_ignored_runs_only": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PUBLIC_PRIVACY_FALSE_KEYS},
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "public_artifact_privacy_audit_expected": True,
            "report_validation_available": True,
            "pass_status_requires_target_bucket_and_minimum_diversity": True,
        },
        "conservative_recommendation": "candidate_materialization_inventory_only_no_strategy_evaluation_until_separate_boundary",
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    key_lower = key.lower()
    if key_lower in {"count"} or key_lower.endswith("_count"):
        errors.append(f"exact public count field at {path}")
    if any(word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS):
        errors.append(f"forbidden public field word at {path}")
    if key and PRIVATE_KEY_RE.search(key):
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
            errors.append(f"private-shaped public value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("schema or phase drift")
    if report.get("status") not in ALLOWED_STATUSES:
        errors.append("unknown status")

    gate = report.get("phase9c_gate_refs", {})
    if gate.get("phase9c_public_report_validated") is not True:
        errors.append("Phase 9C public report gate missing")
    if gate.get("phase9c_public_report_status") != PHASE9C_STATUS:
        errors.append("Phase 9C status drift")
    for key in ("phase9c_report_ci_reference_present", "phase9c_docs_ci_reference_present", "phase9c_bounded_materialization_boundary_present"):
        if gate.get(key) is not True:
            errors.append(f"Phase 9C gate missing: {key}")

    auth = report.get("private_read_authorization_attestation", {})
    if auth.get("phase9b_private_registry_read_confirmed") is not True:
        errors.append("missing --confirm-phase9b-private-registry-read")
    if auth.get("private_output_confirmed") is not True:
        errors.append("missing --confirm-private-output")
    if auth.get("dry_self_test_and_report_validation_read_private_registry") is not False:
        errors.append("self-test/validate-report private registry read boundary failed")
    if auth.get("dry_self_test_and_report_validation_read_source_repositories") is not False:
        errors.append("self-test/validate-report source repository read boundary failed")

    inventory = report.get("task_candidate_inventory_summary", {})
    expected_inventory = {
        "publication_level": "aggregate_bucketed_inventory_only",
        "candidate_type": "evidence_finding_file_localizable_code_tasks_only",
        "target_task_candidate_bucket": "bucket_target_48_to_72",
        "hard_cap_bucket": "bucket_up_to_96",
        "per_source_cap_bucket": "bucket_up_to_8",
    }
    for key, expected in expected_inventory.items():
        if inventory.get(key) != expected:
            errors.append(f"inventory summary drift: {key}")
    for key in (
        "accepted_rows_remain_inventory_only_not_benchmark_annotations",
        "replacement_before_benchmark_annotations_or_strategy_evaluation_only",
        "replacement_uses_no_performance_evidence_or_downstream_feedback",
    ):
        if inventory.get(key) is not True:
            errors.append(f"inventory boundary missing: {key}")

    materialization = report.get("materialization_summary", {})
    if materialization.get("private_materialization_rows_written") is not True:
        errors.append("private materialization rows write attestation missing")
    if materialization.get("source_reference_currentness_reread_available_privately") not in {True, False}:
        errors.append("source reference currentness boolean missing")
    if materialization.get("source_snippets_public") is not False or materialization.get("source_snippets_stored_private") is not False:
        errors.append("source snippet boundary failed")

    repair_summary = report.get("repair_checkpoint_summary", {})
    if repair_summary.get("public_repo_fetch_or_clone_executed") is not False:
        errors.append("Phase 9D must not public-fetch/clone in this repair checkpoint")
    if repair_summary.get("in_place_public_fetch_repair_after_observed_repair_forbidden") is not True:
        errors.append("in-place public fetch repair boundary missing")
    if repair_summary.get("future_public_source_fetch_requires_separate_frozen_boundary") is not True:
        errors.append("future public source fetch boundary missing")
    if repair_summary.get("materialization_itself_is_not_result_evidence") is not True:
        errors.append("materialization/result-evidence boundary missing")
    if report.get("status") == STATUS_REPAIR:
        if repair_summary.get("phase9d_preserves_observed_repair_state") is not True:
            errors.append("repair status must preserve observed repair state")
        if inventory.get("constructed_inventory_bucket") == "bucket_zero" and materialization.get("materialized_reference_bucket") == "bucket_zero":
            if repair_summary.get("phase9d_preserves_zero_materialization_repair_checkpoint") is not True:
                errors.append("zero-materialization repair checkpoint must be explicit")

    diversity = report.get("diversity_summary", {})
    if diversity.get("minimum_distinct_sources_bucket") != "bucket_at_least_8":
        errors.append("minimum distinct source bucket drift")
    if diversity.get("stop_or_repair_if_below_minimum_after_caps") is not True:
        errors.append("diversity stop/repair boundary missing")
    if report.get("status") == STATUS_PASS:
        if inventory.get("constructed_inventory_bucket") != "bucket_target_48_to_72":
            errors.append("pass status outside target task-candidate bucket")
        if diversity.get("diversity_minimum_met") is not True:
            errors.append("pass status below minimum diversity")

    for key in FORBIDDEN_EXECUTION_FALSE_KEYS:
        if report.get("forbidden_execution_boundary", {}).get(key) is not False:
            errors.append(f"forbidden execution boundary failed: {key}")
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("no_claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    privacy = report.get("privacy_summary", {})
    for key in ("public_output_aggregate_only", "private_outputs_under_ignored_runs_only", "runs_remains_ignored"):
        if privacy.get(key) is not True:
            errors.append(f"privacy summary missing: {key}")
    for key in PUBLIC_PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"public privacy boundary failed: {key}")

    validation = report.get("validation_summary", {})
    for key in (
        "route_specific_validator_available",
        "self_test_available",
        "public_artifact_privacy_audit_expected",
        "report_validation_available",
        "pass_status_requires_target_bucket_and_minimum_diversity",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")

    errors.extend(_scan_public(report))
    return sorted(set(errors))


def execute_phase9d(
    private_run_dir: Path,
    public_report: Path,
    confirm_phase9b_private_registry_read: bool,
    confirm_private_output: bool,
) -> dict[str, Any]:
    if not confirm_phase9b_private_registry_read:
        raise ValueError("missing --confirm-phase9b-private-registry-read")
    if not confirm_private_output:
        raise ValueError("missing --confirm-private-output")
    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    phase9c_gate = _load_phase9c_gate()
    registry_path = _find_latest_phase9b_private_registry()
    registry = _read_phase9b_private_registry(registry_path)
    accepted_sources = _accepted_source_rows(registry)
    _rows, private_manifest = _materialize_rows(accepted_sources)
    aggregate = private_manifest["aggregate_private_totals"]
    report = build_public_report(aggregate, phase9c_gate, True, True)
    errors = validate_report(report)
    if errors:
        raise ValueError("generated public report invalid: " + "; ".join(errors[:12]))

    private_run_dir.mkdir(parents=True, exist_ok=True)
    public_report.parent.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_task_candidate_materialization_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (private_run_dir / "private_task_candidate_materialization_rows.json").write_text(
        json.dumps(private_manifest["materialization_rows_private"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    public_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": report["status"],
        "public_report": str(public_report),
        "public_inventory_bucket": report["task_candidate_inventory_summary"]["constructed_inventory_bucket"],
        "public_diversity_bucket": report["diversity_summary"]["observed_distinct_sources_bucket"],
        "private_output_under_ignored_runs": True,
    }


def run_self_test() -> dict[str, Any]:
    global PRIVATE_REGISTRY_READ_ATTEMPTS, SOURCE_FILE_READ_ATTEMPTS
    PRIVATE_REGISTRY_READ_ATTEMPTS = 0
    SOURCE_FILE_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []
    gate = {
        "phase9c_public_report_validated": True,
        "phase9c_public_report_status": PHASE9C_STATUS,
        "phase9c_report_ci_reference_present": True,
        "phase9c_docs_ci_reference_present": True,
        "phase9c_bounded_materialization_boundary_present": True,
    }
    aggregate = {
        "candidate_total": 56,
        "distinct_sources_with_candidates": 8,
        "precheck_passed_sources": 8,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
    }
    base = build_public_report(aggregate, gate, True, True)
    checks.append(("base_report_valid", not validate_report(base)))

    try:
        execute_phase9d(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, False, True)
        checks.append(("missing_phase9b_private_registry_read_confirm_rejected", False))
    except ValueError as exc:
        checks.append(("missing_phase9b_private_registry_read_confirm_rejected", "confirm-phase9b-private-registry-read" in str(exc)))
    try:
        execute_phase9d(DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT, True, False)
        checks.append(("missing_private_output_confirm_rejected", False))
    except ValueError as exc:
        checks.append(("missing_private_output_confirm_rejected", "confirm-private-output" in str(exc)))
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_private_output")
        checks.append(("private_output_outside_ignored_runs_rejected", False))
    except ValueError as exc:
        checks.append(("private_output_outside_ignored_runs_rejected", "runs" in str(exc)))

    phase9c_mutated = {
        "schema_version": f"{PHASE9C_STATUS}_report_v1",
        "phase": PHASE9C_STATUS,
        "status": "drift",
        "future_protocol_summary": {"phase9d_execution_caps_and_stops": {}},
        "phase9c_scope": {},
        "phase9b_gate_references": {},
    }
    checks.append(("phase9c_gate_drift_rejected", bool(_phase9c_gate_errors(phase9c_mutated, PHASE9C_STATUS + " CI green"))))

    for bad_key in ("scoring", "labels", "outcomes", "evidence_success"):
        mutated = copy.deepcopy(base)
        mutated["task_candidate_inventory_summary"][bad_key] = False
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["materialization_summary"]["materialization_as_evidence_success"] = True
    checks.append(("materialization_as_evidence_success_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["repair_checkpoint_summary"]["public_repo_fetch_or_clone_executed"] = True
    checks.append(("public_fetch_or_clone_in_phase9d_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["repair_checkpoint_summary"]["future_public_source_fetch_requires_separate_frozen_boundary"] = False
    checks.append(("missing_future_fetch_boundary_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["task_candidate_inventory_summary"]["example_bucket"] = "count_1"
    checks.append(("count_1_singleton_bucket_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["task_candidate_inventory_summary"]["example_bucket"] = "bucket_one"
    checks.append(("bucket_one_singleton_bucket_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["task_candidate_inventory_summary"]["count"] = 56
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_summary"]["path"] = "src/private.py"
    checks.append(("public_private_shaped_key_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["privacy_summary"]["example_value"] = "owner/repo"
    checks.append(("public_private_shaped_value_rejected", bool(validate_report(mutated))))

    mutated = copy.deepcopy(base)
    mutated["diversity_summary"]["diversity_minimum_met"] = False
    mutated["diversity_summary"]["observed_distinct_sources_bucket"] = "bucket_nonzero_below_minimum"
    checks.append(("diversity_below_minimum_rejected_for_pass", bool(validate_report(mutated))))

    for claim_key in ("provider_claim", "model_claim", "runtime_claim", "default_claim", "product_claim"):
        mutated = copy.deepcopy(base)
        mutated["no_claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    for execution_key in ("provider_or_llm_calls_executed", "model_fitting_executed", "runtime_default_or_product_changes_executed"):
        mutated = copy.deepcopy(base)
        mutated["forbidden_execution_boundary"][execution_key] = True
        checks.append((f"{execution_key}_true_rejected", bool(validate_report(mutated))))

    with tempfile.TemporaryDirectory(prefix="phase9d_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(base), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    checks.append(("selftest_and_validate_report_do_not_read_private_registry", PRIVATE_REGISTRY_READ_ATTEMPTS == 0))
    checks.append(("selftest_and_validate_report_do_not_read_source_repositories", SOURCE_FILE_READ_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 9D task-candidate materialization runner")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--confirm-phase9b-private-registry-read", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--private-run-dir", type=Path, default=DEFAULT_PRIVATE_RUN_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.validate_report:
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.write_report:
        result = execute_phase9d(
            args.private_run_dir,
            args.output,
            args.confirm_phase9b_private_registry_read,
            args.confirm_private_output,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
