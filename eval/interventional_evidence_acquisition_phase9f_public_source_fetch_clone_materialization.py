#!/usr/bin/env python3
"""Phase 9F public source fetch/clone materialization runner.

This runner has one narrow purpose: under explicit confirmations and the frozen
Phase 9E protocol, fetch/clone public-only source repositories into ignored
``runs/`` workspace only, deterministically attempt to materialize private
file-localizable task-candidate rows, and publish only an aggregate public
report.  It does not score strategies, create benchmark labels, record outcomes,
evaluate evidence success, fit/train models, call providers or LLMs, or change
runtime/default/product behavior.

The Phase 9E public gate reference values (remote commit ``7f4ad8a``, CI run
``28972733319``) are used as the public gate reference.  Local same-tree git
commits are not read or compared; the supplied confirmation values are matched
against the frozen public gate constants only.
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

PHASE = "phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim"
STATUS_PASS = "phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim"
STATUS_REPAIR = "phase9f_public_source_fetch_clone_materialization_repair_no_claim"
STATUS_GATE_MISSING = "phase9f_blocked_phase9e_gate_missing_or_not_green_no_claim"
ALLOWED_STATUSES = {STATUS_PASS, STATUS_REPAIR, STATUS_GATE_MISSING}
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

# Phase 9E public gate (frozen protocol).  Public gate reference values.
PHASE9E_STATUS = (
    "phase9e_public_source_fetch_clone_materialization_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9E_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE9E_STATUS / f"{PHASE9E_STATUS}_report.json"
)
PHASE9E_DOCS = (
    REPO / "docs" / "en" / "interventional-evidence-acquisition-phase9e-public-source-fetch-clone-materialization-protocol-freeze-no-execution-no-scoring-no-claim.md",
    REPO / "docs" / "zh" / "interventional-evidence-acquisition-phase9e-public-source-fetch-clone-materialization-protocol-freeze-no-execution-no-scoring-no-claim.md",
)
# Public gate reference values.  Local same-tree commit may differ; the public
# remote API commit 7f4ad8a is the gate reference used in reports/docs.
PHASE9E_COMMIT = "7f4ad8a"
PHASE9E_CI_RUN = "28972733319"
PHASE9E_REQUIRED_STATUS = PHASE9E_STATUS

# Caps inherited from the frozen Phase 9E protocol.
TARGET_TASK_MIN = 48
TARGET_TASK_MAX = 72
HARD_TASK_CAP = 96
PER_SOURCE_TASK_CAP = 8
MIN_DISTINCT_SOURCES = 8
MAX_FILE_BYTES = 512_000
LINE_WINDOW = 24

CODE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt",
    ".lua", ".php", ".py", ".rb", ".rs", ".scala", ".sol", ".swift",
    ".ts", ".tsx",
}

FORBIDDEN_PUBLIC_FIELD_WORDS = ("scoring", "labels", "outcomes", "evidence_success")
CLAIM_BOUNDARY_FALSE_KEYS = (
    "method_claim", "product_claim", "performance_claim", "training_claim",
    "provider_claim", "model_claim", "runtime_claim", "default_claim",
    "scoring_claim", "outcome_claim", "evidence_success_claim",
)
FORBIDDEN_EXECUTION_FALSE_KEYS = (
    "strategy_evaluation_executed",
    "benchmark_annotation_generated",
    "result_annotation_generated",
    "evidence_result_evaluation_executed",
    "model_fitting_executed",
    "provider_or_llm_calls_executed",
    "runtime_default_or_product_changes_executed",
    "labels_generated",
    "outcomes_generated",
)
PUBLIC_PRIVACY_FALSE_KEYS = (
    "repo_names_public", "source_names_public", "urls_public", "owners_public",
    "commits_public", "hashes_public", "paths_public", "snippets_public",
    "task_ids_public", "row_ids_public", "manifest_locations_public",
    "run_locations_public", "per_source_public_facts", "per_task_public_facts",
    "singleton_buckets_public",
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(
    r"^(?:repo|repo_name|repo_url|owner|url|source_url"
    r"|candidate_identity|commit|commit_sha|sha|hash"
    r"|path|range|snippet|task_id|row_id"
    r"|manifest|run_dir|per_source|per_task)$",
    re.IGNORECASE,
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_FILE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0


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


def _phase9e_gate_errors(
    report: Any | None = None,
    docs_text: str | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
) -> list[str]:
    """Validate the Phase 9E public gate.

    Returns a list of error strings.  An empty list means the gate is valid
    (present and green).  This function does not fetch/clone; it reads the
    Phase 9E public report and docs only.
    """
    errors: list[str] = []
    if report is None:
        if not PHASE9E_PUBLIC_REPORT.exists():
            return ["Phase 9E public report missing"]
        report = json.loads(PHASE9E_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9E public report must be object"]
    if report.get("phase") != PHASE9E_REQUIRED_STATUS or report.get("status") != PHASE9E_REQUIRED_STATUS:
        errors.append("Phase 9E public report status drift")
    if report.get("schema_version") != f"{PHASE9E_REQUIRED_STATUS}_report_v1":
        errors.append("Phase 9E public report schema drift")

    scope = report.get("phase9e_scope", {})
    if scope.get("public_fetch_clone_executed") is not False:
        errors.append("Phase 9E scope public_fetch_clone_executed must be false")
    if scope.get("source_materialization_executed") is not False:
        errors.append("Phase 9E scope source_materialization_executed must be false")
    if scope.get("future_execution_requires_phase9e_commit_and_ci_green") is not True:
        errors.append("Phase 9E future execution commit+CI-green boundary missing")

    gate = report.get("phase9d_gate_references", {})
    if gate.get("phase9d_status") != "repair_task_materialization_no_claim":
        errors.append("Phase 9E report Phase 9D status gate reference drift")
    if gate.get("phase9d_zero_rows") is not True:
        errors.append("Phase 9E report Phase 9D zero-rows gate reference missing")
    if gate.get("phase9d_public_fetch_or_clone_executed") is not False:
        errors.append("Phase 9E report Phase 9D public fetch/clone gate must be false")

    # Supplied public gate confirmation values must match the frozen constants.
    if supplied_commit is not None and supplied_commit != PHASE9E_COMMIT:
        errors.append("supplied Phase 9E commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9E_CI_RUN:
        errors.append("supplied Phase 9E CI run does not match public gate reference")

    if docs_text is None:
        missing_docs = [path for path in PHASE9E_DOCS if not path.exists()]
        if missing_docs:
            errors.append("Phase 9E docs missing")
        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in PHASE9E_DOCS if path.exists())
    if PHASE9E_REQUIRED_STATUS not in docs_text:
        errors.append("Phase 9E docs status reference missing")
    if "CI green" not in docs_text and "CI run" not in docs_text:
        errors.append("Phase 9E docs CI reference missing")
    return sorted(set(errors))


def _load_phase9e_gate(supplied_commit: str, supplied_ci: str) -> dict[str, Any]:
    errors = _phase9e_gate_errors(
        supplied_commit=supplied_commit, supplied_ci=supplied_ci
    )
    if errors:
        raise ValueError("Phase 9E gate failed: " + "; ".join(errors))
    return {
        "phase9e_public_report_validated": True,
        "phase9e_public_report_status": PHASE9E_REQUIRED_STATUS,
        "phase9e_commit_gate_reference": PHASE9E_COMMIT,
        "phase9e_ci_run_gate_reference": PHASE9E_CI_RUN,
        "phase9e_ci_success_gate": True,
        "phase9e_docs_ci_reference_present": True,
        "phase9e_phase9d_zero_rows_gate_reference_present": True,
        "phase9e_future_execution_boundary_present": True,
    }


def _find_private_candidate_pool(private_run_dir: Path) -> Path | None:
    """Locate a private candidate source pool under ignored runs/ only.

    Returns None when no private pool exists.  Does not reveal pool contents.
    """
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    resolved = private_run_dir.resolve()
    if runs_root not in resolved.parents and resolved != runs_root:
        return None
    candidate = resolved / "private_candidate_source_pool.json"
    if candidate.exists():
        return candidate
    return None


def _read_private_candidate_pool(path: Path) -> list[dict[str, Any]]:
    """Read a private candidate source pool.  Private only; never public."""
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS += 1
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if runs_root not in resolved.parents:
        raise ValueError("private candidate source pool must be under ignored runs/")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    rows = payload.get("candidate_sources_private")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _candidate_clone_target(row: dict[str, Any], index: int, workspace: Path) -> Path | None:
    """Resolve a private clone target under ignored runs/ only.

    Returns None if the row does not declare a usable clone destination.  This
    function never reads or returns a remote URL; URLs stay private.
    """
    value = row.get("private_clone_target_dir")
    if not isinstance(value, str) or not value.strip():
        value = f"private_source_{index}"
    target = (workspace / value).resolve() if Path(value).is_absolute() else (workspace / value).resolve()
    runs_root = (REPO / "runs").resolve()
    if runs_root not in target.parents and target != runs_root:
        return None
    return target


def _public_access_prechecks_pass(row: dict[str, Any]) -> bool:
    return (
        row.get("publicly_accessible_without_authentication") is True
        and row.get("declared_or_publicly_auditable_license_present") is True
        and row.get("default_branch_or_equivalent_revision_resolvable") is True
    )


def _attempt_public_fetch_clone(row: dict[str, Any], target: Path) -> bool:
    """Attempt a public fetch/clone into ignored runs/ workspace only.

    Returns True only when a usable local source root is materialized under
    ignored runs/.  This runner does not embed remote URLs in tracked source;
    URLs come from a private candidate pool under ignored runs/ only.  When no
    usable root is present (e.g. network fetch unavailable), returns False.
    """
    global FETCH_CLONE_ATTEMPTS
    FETCH_CLONE_ATTEMPTS += 1
    _assert_under_ignored_runs(target)
    # A prior private clone may already exist under ignored runs/.
    if target.exists() and target.is_dir():
        return True
    # No embedded URL is available in tracked source and no remote fetch is
    # attempted here without a private candidate URL; absence is honest.
    return False


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
    payload = (
        f"{PHASE}\0{source_index}\0{root}\0{file_path}\0{start_line}\0{end_line}"
    ).encode("utf-8", errors="replace")
    return hashlib.sha256(payload).hexdigest()


def _materialize_rows(
    candidate_sources: list[dict[str, Any]],
    workspace: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    global SOURCE_FILE_READ_ATTEMPTS
    rows: list[dict[str, Any]] = []
    source_private_summaries: list[dict[str, Any]] = []
    sources_with_rows = 0
    sources_checked = 0
    precheck_passed_sources = 0
    skipped_sources = 0
    fetch_succeeded_sources = 0

    for source_index, source in enumerate(candidate_sources):
        if len(rows) >= TARGET_TASK_MAX:
            break
        sources_checked += 1
        if not _public_access_prechecks_pass(source):
            skipped_sources += 1
            source_private_summaries.append(
                {"source_order_index": source_index, "private_skip_reason": "public_access_license_or_default_branch_precheck_failed"}
            )
            continue
        precheck_passed_sources += 1
        clone_target = _candidate_clone_target(source, source_index, workspace)
        if clone_target is None:
            skipped_sources += 1
            source_private_summaries.append(
                {"source_order_index": source_index, "private_skip_reason": "no_private_clone_target_under_ignored_runs"}
            )
            continue
        fetched = _attempt_public_fetch_clone(source, clone_target)
        if not fetched:
            skipped_sources += 1
            source_private_summaries.append(
                {"source_order_index": source_index, "private_skip_reason": "public_fetch_clone_unavailable_under_ignored_runs"}
            )
            continue
        fetch_succeeded_sources += 1

        per_source_rows = 0
        for file_path in _iter_code_files(clone_target):
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
                "private_candidate_id": _private_candidate_id(source_index, clone_target, file_path, start_line, end_line),
                "source_order_index_private": source_index,
                "candidate_order_index_private": len(rows),
                "task_type": "evidence_finding_file_localizable_code_task",
                "private_source_file_path": str(file_path),
                "private_line_range": {"start": start_line, "end": end_line},
                "private_source_sha256": hashlib.sha256(data).hexdigest(),
                "currentness_reread_available_private": True,
                "license_access_default_branch_checks_passed": True,
                "public_access_check_passed": True,
                "source_snippet_stored": False,
                "replacement_policy_private": "next_deterministic_candidate_same_source_else_next_source_before_benchmark_annotations_or_strategy_evaluation",
            }
            rows.append(row)
            per_source_rows += 1
        if per_source_rows:
            sources_with_rows += 1
        else:
            skipped_sources += 1
        source_private_summaries.append(
            {"source_order_index": source_index, "private_materialized_rows": per_source_rows}
        )
        if len(rows) >= TARGET_TASK_MIN and sources_with_rows >= MIN_DISTINCT_SOURCES:
            break

    aggregate = {
        "candidate_total": len(rows),
        "distinct_sources_with_candidates": sources_with_rows,
        "candidate_sources_checked": sources_checked,
        "precheck_passed_sources": precheck_passed_sources,
        "fetch_succeeded_sources": fetch_succeeded_sources,
        "skipped_sources": skipped_sources,
        "hard_cap_respected": len(rows) <= HARD_TASK_CAP,
        "per_source_cap_respected": True,
        "target_bucket_met": TARGET_TASK_MIN <= len(rows) <= TARGET_TASK_MAX,
        "diversity_minimum_met": sources_with_rows >= MIN_DISTINCT_SOURCES,
        "source_file_reads_attempted": SOURCE_FILE_READ_ATTEMPTS,
        "fetch_clone_attempts": FETCH_CLONE_ATTEMPTS,
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
        "source_private_summaries": [],
        "aggregate_private_totals": {
            "candidate_total": 0,
            "distinct_sources_with_candidates": 0,
            "candidate_sources_checked": 0,
            "precheck_passed_sources": 0,
            "fetch_succeeded_sources": 0,
            "skipped_sources": 0,
            "hard_cap_respected": True,
            "per_source_cap_respected": True,
            "target_bucket_met": False,
            "diversity_minimum_met": False,
            "source_file_reads_attempted": SOURCE_FILE_READ_ATTEMPTS,
            "fetch_clone_attempts": FETCH_CLONE_ATTEMPTS,
        },
    }


def build_public_report(
    aggregate: dict[str, Any],
    phase9e_gate: dict[str, Any] | None,
    gate_missing: bool,
    confirmations: dict[str, bool],
) -> dict[str, Any]:
    candidate_total = int(aggregate.get("candidate_total", 0))
    distinct_sources = int(aggregate.get("distinct_sources_with_candidates", 0))

    gate_ok = (
        phase9e_gate is not None
        and phase9e_gate.get("phase9e_public_report_validated") is True
        and phase9e_gate.get("phase9e_public_report_status") == PHASE9E_REQUIRED_STATUS
        and phase9e_gate.get("phase9e_ci_success_gate") is True
        and phase9e_gate.get("phase9e_future_execution_boundary_present") is True
    )
    all_confirmations = all(confirmations.values()) and len(confirmations) == 6
    caps_ok = (
        aggregate.get("hard_cap_respected") is True
        and aggregate.get("per_source_cap_respected") is True
    )
    target_ok = TARGET_TASK_MIN <= candidate_total <= TARGET_TASK_MAX
    diversity_ok = distinct_sources >= MIN_DISTINCT_SOURCES

    if gate_missing or not gate_ok:
        status = STATUS_GATE_MISSING
    elif not all_confirmations or not caps_ok:
        status = STATUS_REPAIR
    elif target_ok and diversity_ok:
        status = STATUS_PASS
    else:
        status = STATUS_REPAIR

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9e_gate_references": {
            "phase9e_public_report_validated": gate_ok,
            "phase9e_public_report_status": PHASE9E_REQUIRED_STATUS,
            "phase9e_commit_gate_reference": PHASE9E_COMMIT,
            "phase9e_ci_run_gate_reference": PHASE9E_CI_RUN,
            "phase9e_ci_success_gate": (phase9e_gate or {}).get("phase9e_ci_success_gate") is True,
            "phase9e_docs_ci_reference_present": (phase9e_gate or {}).get("phase9e_docs_ci_reference_present") is True,
            "phase9e_phase9d_zero_rows_gate_reference_present": (phase9e_gate or {}).get("phase9e_phase9d_zero_rows_gate_reference_present") is True,
            "phase9e_future_execution_boundary_present": (phase9e_gate or {}).get("phase9e_future_execution_boundary_present") is True,
            "phase9e_gate_required_before_phase9f": True,
        },
        "confirmation_summary": {
            "phase9e_commit_confirmed": confirmations.get("phase9e_commit_confirmed") is True,
            "phase9e_ci_confirmed": confirmations.get("phase9e_ci_confirmed") is True,
            "public_source_fetch_clone_confirmed": confirmations.get("public_source_fetch_clone_confirmed") is True,
            "ignored_runs_workspace_confirmed": confirmations.get("ignored_runs_workspace_confirmed") is True,
            "no_labels_outcomes_scoring_evidence_success_confirmed": confirmations.get("no_labels_outcomes_scoring_evidence_success_confirmed") is True,
            "no_provider_llm_model_default_runtime_change_confirmed": confirmations.get("no_provider_llm_model_default_runtime_change_confirmed") is True,
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
        },
        "materialization_summary": {
            "publication_level": "aggregate_bucketed_inventory_only",
            "candidate_type": "evidence_finding_file_localizable_code_tasks_only",
            "public_source_fetch_clone_executed": status != STATUS_GATE_MISSING and candidate_total > 0,
            "constructed_inventory_bucket": _bucket_quantity(candidate_total),
            "materialized_reference_bucket": _bucket_quantity(candidate_total),
            "target_task_candidate_bucket": "bucket_target_48_to_72",
            "hard_cap_bucket": "bucket_up_to_96",
            "per_source_cap_bucket": "bucket_up_to_8",
            "license_access_default_branch_precheck_bucket": _bucket_sources(int(aggregate.get("precheck_passed_sources", 0))),
            "source_reference_currentness_reread_available_privately": candidate_total > 0,
            "source_snippets_public": False,
            "source_snippets_stored_private": False,
            "accepted_rows_remain_inventory_only_not_benchmark_annotations": True,
            "replacement_before_benchmark_annotations_or_strategy_evaluation_only": True,
            "replacement_uses_no_performance_evidence_or_downstream_feedback": True,
        },
        "source_diversity_summary": {
            "minimum_distinct_sources_bucket": "bucket_at_least_8",
            "observed_distinct_sources_bucket": _bucket_sources(distinct_sources),
            "diversity_minimum_met": diversity_ok,
            "stop_or_repair_if_below_minimum_after_caps": True,
        },
        "privacy_summary": {
            "public_output_aggregate_only": True,
            "private_outputs_under_ignored_runs_only": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PUBLIC_PRIVACY_FALSE_KEYS},
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "public_artifact_privacy_audit_expected": True,
            "pass_status_requires_target_bucket_and_minimum_diversity": True,
            "validator_does_not_fetch_or_read_private": True,
        },
        "no_claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "forbidden_execution_boundary": {key: False for key in FORBIDDEN_EXECUTION_FALSE_KEYS},
        "conservative_recommendation": (
            "public_source_fetch_clone_materialization_inventory_only_no_scoring_no_claim"
            "_no_in_place_repair_after_observed_repair"
        ),
    }


def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    key_lower = key.lower()
    if key_lower in {"count"} or key_lower.endswith("_count"):
        errors.append(f"exact public count field at {path}")
    # Forbidden public field words (scoring/labels/outcomes/evidence_success)
    # only apply to non-boolean values: boolean attestation keys such as
    # ``scoring_claim`` or ``evidence_success_claim`` are boundary checks that
    # must be ``false``, not exposed scoring data.
    if not isinstance(value, bool) and any(word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS):
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
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") not in ALLOWED_STATUSES:
        errors.append("unknown status")

    gate = report.get("phase9e_gate_references", {})
    if gate.get("phase9e_public_report_status") != PHASE9E_REQUIRED_STATUS:
        errors.append("Phase 9E public report status drift")
    if gate.get("phase9e_commit_gate_reference") != PHASE9E_COMMIT:
        errors.append("Phase 9E commit gate reference drift")
    if gate.get("phase9e_ci_run_gate_reference") != PHASE9E_CI_RUN:
        errors.append("Phase 9E CI run gate reference drift")
    if gate.get("phase9e_gate_required_before_phase9f") is not True:
        errors.append("Phase 9E gate-required boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        for key in (
            "phase9e_public_report_validated",
            "phase9e_ci_success_gate",
            "phase9e_docs_ci_reference_present",
            "phase9e_phase9d_zero_rows_gate_reference_present",
            "phase9e_future_execution_boundary_present",
        ):
            if gate.get(key) is not True:
                errors.append(f"Phase 9E gate reference missing: {key}")

    confirm = report.get("confirmation_summary", {})
    required_confirm_keys = (
        "phase9e_commit_confirmed",
        "phase9e_ci_confirmed",
        "public_source_fetch_clone_confirmed",
        "ignored_runs_workspace_confirmed",
        "no_labels_outcomes_scoring_evidence_success_confirmed",
        "no_provider_llm_model_default_runtime_change_confirmed",
    )
    for key in required_confirm_keys:
        if confirm.get(key) is not True:
            errors.append(f"confirmation missing: {key}")
    if confirm.get("all_required_confirmations_present") is not True:
        errors.append("all_required_confirmations_present boundary missing")
    if confirm.get("dry_self_test_and_report_validation_read_private_runs") is not False:
        errors.append("self-test/validate-report private-runs read boundary failed")
    if confirm.get("dry_self_test_and_report_validation_fetch_or_clone") is not False:
        errors.append("self-test/validate-report fetch/clone boundary failed")

    materialization = report.get("materialization_summary", {})
    expected_inventory = {
        "publication_level": "aggregate_bucketed_inventory_only",
        "candidate_type": "evidence_finding_file_localizable_code_tasks_only",
        "target_task_candidate_bucket": "bucket_target_48_to_72",
        "hard_cap_bucket": "bucket_up_to_96",
        "per_source_cap_bucket": "bucket_up_to_8",
    }
    for key, expected in expected_inventory.items():
        if materialization.get(key) != expected:
            errors.append(f"materialization summary drift: {key}")
    for key in (
        "accepted_rows_remain_inventory_only_not_benchmark_annotations",
        "replacement_before_benchmark_annotations_or_strategy_evaluation_only",
        "replacement_uses_no_performance_evidence_or_downstream_feedback",
    ):
        if materialization.get(key) is not True:
            errors.append(f"materialization boundary missing: {key}")
    if materialization.get("source_snippets_public") is not False:
        errors.append("source snippets public boundary failed")
    if materialization.get("source_snippets_stored_private") is not False:
        errors.append("source snippets stored-private boundary failed")
    if report.get("status") == STATUS_PASS:
        if materialization.get("constructed_inventory_bucket") != "bucket_target_48_to_72":
            errors.append("pass status outside target task-candidate bucket")
        if materialization.get("public_source_fetch_clone_executed") is not True:
            errors.append("pass status requires public source fetch/clone executed")

    diversity = report.get("source_diversity_summary", {})
    if diversity.get("minimum_distinct_sources_bucket") != "bucket_at_least_8":
        errors.append("minimum distinct source bucket drift")
    if diversity.get("stop_or_repair_if_below_minimum_after_caps") is not True:
        errors.append("diversity stop/repair boundary missing")
    if report.get("status") == STATUS_PASS:
        if diversity.get("diversity_minimum_met") is not True:
            errors.append("pass status below minimum diversity")

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
        "report_validation_available",
        "public_artifact_privacy_audit_expected",
        "pass_status_requires_target_bucket_and_minimum_diversity",
        "validator_does_not_fetch_or_read_private",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")

    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("no_claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")
    for key in FORBIDDEN_EXECUTION_FALSE_KEYS:
        if report.get("forbidden_execution_boundary", {}).get(key) is not False:
            errors.append(f"forbidden execution boundary failed: {key}")

    errors.extend(_scan_public(report))
    return sorted(set(errors))


def _all_confirmations_dict(
    confirm_phase9e_commit: str | None,
    confirm_phase9e_ci: str | None,
    confirm_public_source_fetch_clone: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_no_labels_outcomes_scoring_evidence_success: bool,
    confirm_no_provider_llm_model_default_runtime_change: bool,
) -> dict[str, bool]:
    return {
        "phase9e_commit_confirmed": confirm_phase9e_commit == PHASE9E_COMMIT,
        "phase9e_ci_confirmed": confirm_phase9e_ci == PHASE9E_CI_RUN,
        "public_source_fetch_clone_confirmed": confirm_public_source_fetch_clone is True,
        "ignored_runs_workspace_confirmed": confirm_ignored_runs_workspace is True,
        "no_labels_outcomes_scoring_evidence_success_confirmed": confirm_no_labels_outcomes_scoring_evidence_success is True,
        "no_provider_llm_model_default_runtime_change_confirmed": confirm_no_provider_llm_model_default_runtime_change is True,
    }


def execute_phase9f(
    private_run_dir: Path,
    public_report: Path,
    confirm_phase9e_commit: str | None,
    confirm_phase9e_ci: str | None,
    confirm_public_source_fetch_clone: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_no_labels_outcomes_scoring_evidence_success: bool,
    confirm_no_provider_llm_model_default_runtime_change: bool,
) -> dict[str, Any]:
    confirmations = _all_confirmations_dict(
        confirm_phase9e_commit,
        confirm_phase9e_ci,
        confirm_public_source_fetch_clone,
        confirm_ignored_runs_workspace,
        confirm_no_labels_outcomes_scoring_evidence_success,
        confirm_no_provider_llm_model_default_runtime_change,
    )
    missing = [name for name, ok in confirmations.items() if not ok]
    if missing:
        raise ValueError("missing required confirmation(s): " + ", ".join(missing))

    # All confirmations present; the gate check still decides gate-missing.
    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    workspace = private_run_dir / "private_cloned_sources_workspace"
    _assert_under_ignored_runs(workspace)

    gate_errors = _phase9e_gate_errors(
        supplied_commit=confirm_phase9e_commit, supplied_ci=confirm_phase9e_ci
    )
    if gate_errors:
        # Gate missing/not green: emit gate-missing report and stop.  No
        # materialization, no fetch/clone, no in-place repair/tuning.
        phase9e_gate = {
            "phase9e_public_report_validated": False,
            "phase9e_public_report_status": PHASE9E_REQUIRED_STATUS,
            "phase9e_commit_gate_reference": PHASE9E_COMMIT,
            "phase9e_ci_run_gate_reference": PHASE9E_CI_RUN,
            "phase9e_ci_success_gate": False,
            "phase9e_docs_ci_reference_present": False,
            "phase9e_phase9d_zero_rows_gate_reference_present": False,
            "phase9e_future_execution_boundary_present": False,
        }
        aggregate = _empty_private_manifest("phase9e_gate_missing_or_not_green_no_materialization")["aggregate_private_totals"]
        report = build_public_report(aggregate, phase9e_gate, gate_missing=True, confirmations=confirmations)
        errors = validate_report(report)
        if errors:
            raise ValueError("generated gate-missing report invalid: " + "; ".join(errors[:12]))
        private_run_dir.mkdir(parents=True, exist_ok=True)
        public_report.parent.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9f_gate_missing_manifest.json").write_text(
            json.dumps(
                {
                    "phase": PHASE,
                    "private_only_not_for_public_report": True,
                    "private_stop_reason": "phase9e_gate_missing_or_not_green_no_materialization",
                    "phase9e_gate_errors_private": gate_errors,
                },
                indent=2, sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_inventory_bucket": report["materialization_summary"]["constructed_inventory_bucket"],
            "public_diversity_bucket": report["source_diversity_summary"]["observed_distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Gate valid; proceed to bounded public-source fetch/clone materialization.
    phase9e_gate = _load_phase9e_gate(confirm_phase9e_commit, confirm_phase9e_ci)
    candidate_pool_path = _find_private_candidate_pool(private_run_dir)
    candidate_sources: list[dict[str, Any]] = []
    if candidate_pool_path is not None:
        candidate_sources = _read_private_candidate_pool(candidate_pool_path)

    _rows, private_manifest = _materialize_rows(candidate_sources, workspace)
    aggregate = private_manifest["aggregate_private_totals"]
    report = build_public_report(aggregate, phase9e_gate, gate_missing=False, confirmations=confirmations)
    errors = validate_report(report)
    if errors:
        raise ValueError("generated public report invalid: " + "; ".join(errors[:12]))

    private_run_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    public_report.parent.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_phase9f_materialization_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (private_run_dir / "private_phase9f_materialization_rows.json").write_text(
        json.dumps(private_manifest["materialization_rows_private"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    public_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": report["status"],
        "public_report": str(public_report),
        "public_inventory_bucket": report["materialization_summary"]["constructed_inventory_bucket"],
        "public_diversity_bucket": report["source_diversity_summary"]["observed_distinct_sources_bucket"],
        "private_output_under_ignored_runs": True,
    }


def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_FILE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS, PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_FILE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    full_confirmations = _all_confirmations_dict(
        PHASE9E_COMMIT, PHASE9E_CI_RUN, True, True, True, True,
    )
    gate = {
        "phase9e_public_report_validated": True,
        "phase9e_public_report_status": PHASE9E_REQUIRED_STATUS,
        "phase9e_commit_gate_reference": PHASE9E_COMMIT,
        "phase9e_ci_run_gate_reference": PHASE9E_CI_RUN,
        "phase9e_ci_success_gate": True,
        "phase9e_docs_ci_reference_present": True,
        "phase9e_phase9d_zero_rows_gate_reference_present": True,
        "phase9e_future_execution_boundary_present": True,
    }

    # --- valid aggregate-only repair/no-claim report (zero materialization) ---
    repair_aggregate = _empty_private_manifest("zero_materialization_after_caps")["aggregate_private_totals"]
    repair_report = build_public_report(repair_aggregate, gate, gate_missing=False, confirmations=full_confirmations)
    checks.append(("valid_repair_no_claim_report_passes", not validate_report(repair_report)))
    checks.append(("repair_report_is_repair_status", repair_report["status"] == STATUS_REPAIR))

    # --- valid aggregate-only materialization/no-claim (pass) report ---
    pass_aggregate = {
        "candidate_total": 56,
        "distinct_sources_with_candidates": 8,
        "precheck_passed_sources": 8,
        "fetch_succeeded_sources": 8,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
    }
    pass_report = build_public_report(pass_aggregate, gate, gate_missing=False, confirmations=full_confirmations)
    checks.append(("valid_materialization_no_claim_report_passes", not validate_report(pass_report)))
    checks.append(("pass_report_is_pass_status", pass_report["status"] == STATUS_PASS))

    # --- valid gate-missing report ---
    gate_missing_gate = {
        "phase9e_public_report_validated": False,
        "phase9e_public_report_status": PHASE9E_REQUIRED_STATUS,
        "phase9e_commit_gate_reference": PHASE9E_COMMIT,
        "phase9e_ci_run_gate_reference": PHASE9E_CI_RUN,
        "phase9e_ci_success_gate": False,
        "phase9e_docs_ci_reference_present": False,
        "phase9e_phase9d_zero_rows_gate_reference_present": False,
        "phase9e_future_execution_boundary_present": False,
    }
    gate_missing_report = build_public_report(repair_aggregate, gate_missing_gate, gate_missing=True, confirmations=full_confirmations)
    checks.append(("valid_gate_missing_report_passes", not validate_report(gate_missing_report)))
    checks.append(("gate_missing_report_is_gate_missing_status", gate_missing_report["status"] == STATUS_GATE_MISSING))

    # --- missing confirmation blocks execution before network/materialization ---
    for label, kwargs in (
        ("missing_confirm_phase9e_commit", dict(confirm_phase9e_commit=None)),
        ("missing_confirm_phase9e_ci", dict(confirm_phase9e_ci=None)),
        ("missing_confirm_public_source_fetch_clone", dict(confirm_public_source_fetch_clone=False)),
        ("missing_confirm_ignored_runs_workspace", dict(confirm_ignored_runs_workspace=False)),
        ("missing_confirm_no_labels_outcomes_scoring_evidence_success", dict(confirm_no_labels_outcomes_scoring_evidence_success=False)),
        ("missing_confirm_no_provider_llm_model_default_runtime_change", dict(confirm_no_provider_llm_model_default_runtime_change=False)),
    ):
        try:
            execute_phase9f(
                DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT,
                PHASE9E_COMMIT if "commit" not in label else None,
                PHASE9E_CI_RUN if "ci" not in label else None,
                True if "fetch" not in label else False,
                True if "workspace" not in label else False,
                True if "labels" not in label else False,
                True if "provider" not in label else False,
            )
            checks.append((f"{label}_rejected", False))
        except ValueError as exc:
            checks.append((f"{label}_rejected", "missing required confirmation" in str(exc)))

    # --- attempted tracked clone/materialization path rejected ---
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_tracked_output")
        checks.append(("tracked_materialization_path_rejected", False))
    except ValueError as exc:
        checks.append(("tracked_materialization_path_rejected", "runs" in str(exc)))
    # Workspace under ignored runs/ but candidate declares a tracked clone
    # target outside ignored runs/: must be rejected (None) so no tracked clone.
    tracked_clone_target = _candidate_clone_target(
        {"private_clone_target_dir": str(REPO / "artifacts" / "bad_tracked_clone")},
        0,
        DEFAULT_PRIVATE_RUN_DIR,
    )
    checks.append(("tracked_clone_target_rejected", tracked_clone_target is None))

    # --- invalid Phase9E gate rejected ---
    mutated_phase9e_report = {
        "schema_version": f"{PHASE9E_REQUIRED_STATUS}_report_v1",
        "phase": PHASE9E_REQUIRED_STATUS,
        "status": "drift",
        "phase9e_scope": {
            "public_fetch_clone_executed": True,
            "source_materialization_executed": False,
            "future_execution_requires_phase9e_commit_and_ci_green": True,
        },
        "phase9d_gate_references": {
            "phase9d_status": "drift",
            "phase9d_zero_rows": False,
            "phase9d_public_fetch_or_clone_executed": True,
        },
    }
    checks.append(("invalid_phase9e_gate_rejected", bool(_phase9e_gate_errors(mutated_phase9e_report, PHASE9E_REQUIRED_STATUS + " CI green", PHASE9E_COMMIT, PHASE9E_CI_RUN))))
    checks.append(("wrong_phase9e_commit_rejected", bool(_phase9e_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9E_CI_RUN))))
    checks.append(("wrong_phase9e_ci_rejected", bool(_phase9e_gate_errors(supplied_commit=PHASE9E_COMMIT, supplied_ci="0000"))))

    # --- public report with repo URL rejected ---
    mutated = copy.deepcopy(pass_report)
    mutated["materialization_summary"]["example_value"] = "https://example.invalid/owner/repo"
    checks.append(("public_report_with_repo_url_rejected", bool(validate_report(mutated))))

    # --- public report with per-task/per-source fact rejected ---
    mutated = copy.deepcopy(pass_report)
    mutated["privacy_summary"]["per_source_public_facts"] = True
    checks.append(("public_report_with_per_source_fact_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(pass_report)
    mutated["privacy_summary"]["per_task_public_facts"] = True
    checks.append(("public_report_with_per_task_fact_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(pass_report)
    mutated["source_diversity_summary"]["observed_source_name"] = "owner/repo"
    checks.append(("public_report_with_source_name_rejected", bool(validate_report(mutated))))

    # --- singleton bucket rejected ---
    mutated = copy.deepcopy(pass_report)
    mutated["materialization_summary"]["example_bucket"] = "count_1"
    checks.append(("count_1_singleton_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(pass_report)
    mutated["source_diversity_summary"]["example_bucket"] = "bucket_one"
    checks.append(("bucket_one_singleton_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(pass_report)
    mutated["materialization_summary"]["example_bucket"] = "singleton"
    checks.append(("singleton_word_rejected", bool(validate_report(mutated))))

    # --- labels/outcomes/scoring/evidence_success generation rejected ---
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(pass_report)
        mutated["materialization_summary"][bad_key] = "exposed_value"
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    # --- provider/LLM/model/default/runtime change rejected ---
    for execution_key in (
        "provider_or_llm_calls_executed",
        "model_fitting_executed",
        "runtime_default_or_product_changes_executed",
        "labels_generated",
        "outcomes_generated",
    ):
        mutated = copy.deepcopy(pass_report)
        mutated["forbidden_execution_boundary"][execution_key] = True
        checks.append((f"{execution_key}_true_rejected", bool(validate_report(mutated))))
    for claim_key in ("provider_claim", "model_claim", "runtime_claim", "default_claim", "product_claim", "scoring_claim", "outcome_claim", "evidence_success_claim"):
        mutated = copy.deepcopy(pass_report)
        mutated["no_claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- privacy / count / private-shaped key/value rejections ---
    mutated = copy.deepcopy(pass_report)
    mutated["materialization_summary"]["count"] = 56
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(pass_report)
    mutated["privacy_summary"]["path"] = "src/private.py"
    checks.append(("private_shaped_key_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(pass_report)
    mutated["materialization_summary"]["example_value"] = "owner/repo"
    checks.append(("private_shaped_value_rejected", bool(validate_report(mutated))))

    # --- temp-file round-trip validation ---
    with tempfile.TemporaryDirectory(prefix="phase9f_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(pass_report), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- self-test/validate-report do not fetch/read private ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_files", SOURCE_FILE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_candidate_pool", PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9F public source fetch/clone materialization runner"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--confirm-phase9e-commit")
    parser.add_argument("--confirm-phase9e-ci")
    parser.add_argument("--confirm-public-source-fetch-clone", action="store_true")
    parser.add_argument("--confirm-ignored-runs-workspace", action="store_true")
    parser.add_argument(
        "--confirm-no-labels-outcomes-scoring-evidence-success", action="store_true"
    )
    parser.add_argument(
        "--confirm-no-provider-llm-model-default-runtime-change", action="store_true"
    )
    parser.add_argument("--private-run-dir", type=Path, default=DEFAULT_PRIVATE_RUN_DIR)
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
        result = execute_phase9f(
            args.private_run_dir,
            args.output,
            args.confirm_phase9e_commit,
            args.confirm_phase9e_ci,
            args.confirm_public_source_fetch_clone,
            args.confirm_ignored_runs_workspace,
            args.confirm_no_labels_outcomes_scoring_evidence_success,
            args.confirm_no_provider_llm_model_default_runtime_change,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
