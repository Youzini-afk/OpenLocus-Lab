#!/usr/bin/env python3
"""P63 Cross-Run Slice Collector / Matrix Runner v0.

P63 is a deterministic, offline, no-provider, no-live-LLM, aggregate-only
orchestrator that collects already-downloaded local per-run artifact directories,
validates they contain only the allowlisted aggregate report JSON files, builds a
P62 slice manifest, runs P62 -> P57 -> P61 offline, and emits a sanitized
aggregate actionability report.

P63 NEVER:
  - fetches artifacts from a network,
  - reads source files, tasks, candidates, prompts, responses, traces,
  - exposes run/repo/dataset/directory identity,
  - authorizes provider spend or constructs prompts.

P63 ONLY accepts local directories:
  - `--slice-root-dir PATH` (repeatable; immediate children are slice dirs)
  - `--slice-dir PATH` (repeatable; exact slice dir)

All other inputs (provider/model/api/base-url/prompt/repo-lock/source-root/candidate
args) are explicitly rejected in v0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "p63-cross-run-slice-collector-v0"
GENERATED_BY = "p63_cross_run_slice_collector"
STAGE = "P63 Cross-Run Slice Collector / Matrix Runner v0"

DEFAULT_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_cross_run_slice_collector_report.json")
DEFAULT_DOC = Path("docs/en/p63-cross-run-slice-collector.md")
DEFAULT_MANIFEST_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_internal_slice_manifest.json")
DEFAULT_P57_INPUT_MATRIX_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_p57_input_matrix.json")
DEFAULT_P62_REPORT_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_p62_handoff_report.json")
DEFAULT_P62_DOC_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_p62_handoff_report.md")
DEFAULT_P57_REPORT_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_p57_matrix_report.json")
DEFAULT_P57_DOC_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_p57_matrix_report.md")
DEFAULT_P61_REPORT_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_p61_pre_spend_report.json")
DEFAULT_P61_DOC_OUT = Path("artifacts/p63_cross_run_slice_collector/p63_p61_pre_spend_report.md")

# Exact allowlist of per-slice filenames. No other files, subdirs, symlinks,
# hidden files, logs, JSONL, prompts, provider configs, or source files are allowed.
ALLOWED_SLICE_FILENAMES = {
    "p46_candidate_reach_cost_map_report.json",
    "p47_request_more_context_report.json",
    "p48_diagnostic_policy_simulator_report.json",
    "p49_contrastive_candidate_pack_scaffold_report.json",
    "p50_fixed_suite_validation_report.json",
    "p52_metadata_local_verifier_scaffold_report.json",
    "p52a_source_materialization_prerequisite_report.json",
    "p52b_source_backed_local_verifier_feature_matrix_report.json",
    "p52c_local_verifier_scoring_simulator_report.json",
    "p51_llm_span_narrow_2_diagnostic_report.json",
    "p51b_llm_opt_in_contract_report.json",
    "p57_generalization_gate_report.json",
    "p58_source_backed_verifier_calibration_report.json",
    "p59_contrastive_pack_coverage_counterfactual_report.json",
    "p60_rmc_policy_v2_report.json",
    "p61_pre_spend_gate_report.json",
}

# Required files for a slice to be accepted by P63 v0.
REQUIRED_SLICE_FILENAMES = {
    "p46_candidate_reach_cost_map_report.json",
    "p47_request_more_context_report.json",
    "p48_diagnostic_policy_simulator_report.json",
    "p49_contrastive_candidate_pack_scaffold_report.json",
    "p50_fixed_suite_validation_report.json",
    "p52_metadata_local_verifier_scaffold_report.json",
    "p52a_source_materialization_prerequisite_report.json",
    "p52b_source_backed_local_verifier_feature_matrix_report.json",
    "p52c_local_verifier_scoring_simulator_report.json",
    "p51b_llm_opt_in_contract_report.json",
    "p57_generalization_gate_report.json",
    "p58_source_backed_verifier_calibration_report.json",
    "p59_contrastive_pack_coverage_counterfactual_report.json",
    "p60_rmc_policy_v2_report.json",
}

OPTIONAL_SLICE_FILENAMES = {
    "p51_llm_span_narrow_2_diagnostic_report.json",
    "p61_pre_spend_gate_report.json",
}

# Map from phase/filename to the public phase name (for safety counters only).
FILENAME_TO_PHASE = {
    "p46_candidate_reach_cost_map_report.json": "p46",
    "p47_request_more_context_report.json": "p47",
    "p48_diagnostic_policy_simulator_report.json": "p48",
    "p49_contrastive_candidate_pack_scaffold_report.json": "p49",
    "p50_fixed_suite_validation_report.json": "p50",
    "p52_metadata_local_verifier_scaffold_report.json": "p52",
    "p52a_source_materialization_prerequisite_report.json": "p52a",
    "p52b_source_backed_local_verifier_feature_matrix_report.json": "p52b",
    "p52c_local_verifier_scoring_simulator_report.json": "p52c",
    "p51_llm_span_narrow_2_diagnostic_report.json": "p51",
    "p51b_llm_opt_in_contract_report.json": "p51b",
    "p57_generalization_gate_report.json": "p57",
    "p58_source_backed_verifier_calibration_report.json": "p58",
    "p59_contrastive_pack_coverage_counterfactual_report.json": "p59",
    "p60_rmc_policy_v2_report.json": "p60",
    "p61_pre_spend_gate_report.json": "p61",
}

ALLOWED_STATUS = {
    "self_test_only",
    "blocked_safety",
    "no_inputs",
    "invalid_input_artifacts",
    "insufficient_matrix_inputs",
    "matrix_not_actionable",
    "matrix_actionable_precondition_only",
    "orchestration_failed",
}

# Exact forbidden public keys. Required safety flag names that also appear in this
# set are explicitly allowed in P63_ALLOWED_KEYS.
FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "candidate_id",
    "repo_id",
    "dataset",
    "path",
    "paths",
    "slice_dir",
    "slice_dirs",
    "artifact_path",
    "artifact_paths",
    "directory",
    "directories",
    "run_id",
    "workflow_run_id",
    "github_run_id",
    "job_id",
    "source_root",
    "corpus_root",
    "repo_lock",
    "repo_lock_path",
    "start_line",
    "end_line",
    "span",
    "content_sha",
    "digest",
    "hash",
    "fingerprint",
    "signature",
    "slice_digest",
    "slice_signature",
    "gold",
    "gold_spans",
    "private_label",
    "private_labels",
    "label",
    "labels",
    "query",
    "raw_query",
    "snippet",
    "source_text",
    "raw_source",
    "prompt",
    "response",
    "output",
    "raw_output",
    "provider",
    "model",
    "base_url",
    "api_key",
    "api_token",
    "provider_key",
    "endpoint",
    "tasks",
    "records",
    "per_task",
    "per_task_results",
    "per_candidate",
    "per_candidate_results",
    "per_slice_rows",
    "decision_records",
    "candidate_pool",
    "raw_candidates",
    "pack_items",
    "evidence",
    "Evidence",
    "winner",
    "best_policy",
    "recommended_policy",
    "promotable_policy",
    "default_policy",
    "promotion_decision",
    "default_decision",
    "admission_decision",
    "request_payload",
    "request_envelope",
    "raw_request_envelope",
    "raw_request_envelopes",
}

# Keys that are intentionally public in the P63 report.
P63_ALLOWED_KEYS = {
    # schema
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    "not_quality_evidence",
    "precondition_report_only",
    "matrix_actionability_only",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "aggregate_only_public_artifact",
    "provider_spend_authorized",
    "micro_run_not_authorized",
    "workflow_dispatch_required_for_live_run",
    "remote_calls_by_p63",
    "llm_calls_by_p63",
    "remote_requests_by_p63",
    "provider_config_read_by_p63",
    "prompt_construction_by_p63",
    "source_reads_attempted_by_p63",
    "gold_used_by_p63",
    "private_labels_loaded_by_p63",
    "raw_text_stored",
    "raw_source_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_query_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
    "elapsed_ms",
    # summary blocks
    "input_validation_summary",
    "p62_handoff_summary",
    "p57_matrix_summary",
    "p61_pre_spend_summary",
    "final_actionability",
    "warnings",
    "blockers",
    "conclusion",
    "validation",
    # input_validation_summary
    "input_directory_count",
    "readable_directory_count",
    "accepted_slice_directory_count",
    "rejected_slice_directory_count",
    "empty_directory_count",
    "non_allowlisted_artifact_directory_count",
    "missing_required_aggregate_report_directory_count",
    "invalid_json_report_directory_count",
    "self_test_directory_count",
    "unsafe_upstream_report_directory_count",
    # p62_handoff_summary
    "p62_manifest_written",
    "p62_manifest_entry_count",
    "p62_status",
    "p62_eligible_distinct_slice_count",
    "p62_content_distinct_input_count",
    "p62_duplicate_input_count",
    "p62_exact_duplicate_inputs_rejected_count",
    "p62_p57_input_matrix_written",
    "p62_p57_input_matrix_entry_count",
    # p57_matrix_summary
    "p57_run_attempted",
    "p57_status",
    "p57_readiness_status",
    "p57_required_slice_count_met",
    "p57_included_generalization_slice_count",
    "p57_upstream_safety_blocker_count",
    # p61_pre_spend_summary
    "p61_run_attempted",
    "p61_status",
    "p61_decision",
    "p61_decision_is_authorization",
    "p61_provider_spend_authorized",
    "p61_requires_separate_human_or_workflow_dispatch",
    "representative_internal_slice",
    # final_actionability
    "multi_slice_matrix_actionable",
    "actionability_status",
    "actionability_is_authorization",
    "requires_separate_human_or_workflow_dispatch",
    "blocker_count",
    "warning_count",
    # validation
    "forbidden_key_scan_ok",
    "self_test_assertions_passed",
    # generic
    "count",
    "rate",
    "value",
    "bucket",
    "availability",
    "true",
    "false",
}

RAW_FLAGS = [
    "raw_text_stored",
    "raw_source_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_query_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _eval_dir() -> Path:
    return Path(__file__).resolve().parent


def _run_subprocess(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a Python subprocess without shell, network, or provider access."""
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    return result.returncode, result.stdout, result.stderr


def _is_path_or_secret_value(value: Any, prefix: str = "") -> list[str]:
    """Detect values that look like paths, URLs, or provider secrets."""
    violations: list[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            violations.extend(_is_path_or_secret_value(val, prefix + str(key) + "."))
    elif isinstance(value, list):
        for idx, val in enumerate(value):
            violations.extend(_is_path_or_secret_value(val, prefix + str(idx) + "."))
    elif isinstance(value, str):
        text = value.strip()
        if len(text) > 1:
            if text.startswith("/") or text.startswith("\\"):
                violations.append(prefix + " looks like an absolute path")
            elif "://" in text:
                violations.append(prefix + " looks like a URL")
            elif re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
                violations.append(prefix + " looks like an API key")
            elif re.fullmatch(r"[0-9a-fA-F]{32,}", text):
                violations.append(prefix + " looks like a hex digest")
            elif re.search(r"(?i)(api_key|api_token|base_url|provider_key|endpoint|authorization\s*[:=])", text):
                violations.append(prefix + " looks like a provider secret pattern")
            elif re.search(r"[/\\]", text) and (text.count("/") > 1 or text.count("\\") > 1):
                violations.append(prefix + " looks like a relative path")
    return violations


def _is_upstream_private_value(value: Any, prefix: str = "") -> list[str]:
    """Detect clear private values in upstream aggregate reports.

    Upstream aggregate reports may legitimately contain hash-policy fields or
    stage-name text with slashes (for example "P52A/P52B"). P63 must reject
    obvious private values (absolute paths, URLs, API keys/provider secrets)
    while allowing existing sanitized aggregate diagnostics to be consumed.
    P63's own public report still uses the stricter value scanner.
    """
    violations: list[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            violations.extend(_is_upstream_private_value(val, prefix + str(key) + "."))
    elif isinstance(value, list):
        for idx, val in enumerate(value):
            violations.extend(_is_upstream_private_value(val, prefix + str(idx) + "."))
    elif isinstance(value, str):
        text = value.strip()
        if len(text) > 1:
            if text.startswith("/") or text.startswith("\\"):
                violations.append(prefix + " looks like an absolute path")
            elif "://" in text:
                violations.append(prefix + " looks like a URL")
            elif re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
                violations.append(prefix + " looks like an API key")
            elif re.search(r"(?i)(api_key|api_token|base_url|provider_key|endpoint|authorization\s*[:=])", text):
                violations.append(prefix + " looks like a provider secret pattern")
    return violations


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P63_ALLOWED_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _is_regular_file(path: Path) -> bool:
    """Accept only real files (no symlinks, no dirs, no devices)."""
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def _check_report_safety(data: dict[str, Any]) -> tuple[bool, str]:
    """Lightweight aggregate-only safety check. Returns (safe, reason)."""
    if not isinstance(data, dict):
        return False, "report_not_object"

    # P63 accepts only aggregate public reports. Even allowlisted filenames must
    # not contain private/per-row structures or leak identifiers/paths/providers.
    if _reject_forbidden_keys(data) or _is_upstream_private_value(data):
        return False, "aggregate_contract_violation"

    if data.get("self_test") is True:
        return False, "self_test_report"
    if data.get("status") == "self_test_only":
        return False, "self_test_status"

    # Common promotion/default/quality gates.
    for flag, expected in [
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("candidate_not_fact", True),
        ("aggregate_only_public_artifact", True),
    ]:
        if data.get(flag) is not expected:
            return False, f"{flag}_unexpected"

    # Remote/LLM/prompt/provider counters must be zero/false.
    for key in data:
        if re.fullmatch(r"remote_calls_by_[a-z0-9]+", key):
            if data[key] != 0:
                return False, f"{key}_nonzero"
        if re.fullmatch(r"llm_calls_by_[a-z0-9]+", key):
            if data[key] != 0:
                return False, f"{key}_nonzero"
        if re.fullmatch(r"remote_requests_by_[a-z0-9]+", key):
            if data[key] != 0:
                return False, f"{key}_nonzero"
        if re.fullmatch(r"prompt_construction_by_[a-z0-9]+", key):
            if data[key] is not False:
                return False, f"{key}_true"
        if re.fullmatch(r"provider_config_read_by_[a-z0-9]+", key):
            if data[key] is not False:
                return False, f"{key}_true"
        if re.fullmatch(r"source_reads_attempted_by_[a-z0-9]+", key):
            if data[key] is True:
                bounded_key = key.replace("attempted", "bounded")
                if data.get(bounded_key) is not True:
                    return False, f"{key}_unbounded"

    # Raw/private flags must be false.
    for flag in RAW_FLAGS:
        if data.get(flag) is True:
            return False, f"{flag}_true"

    return True, ""


def _validate_slice_dir(slice_dir: Path) -> dict[str, Any]:
    """Validate a slice directory and return a result dict."""
    result: dict[str, Any] = {
        "path": str(slice_dir),  # internal only
        "readable": False,
        "rejected": False,
        "reason": None,
        "files": set(),
    }
    try:
        if slice_dir.is_symlink():
            result["rejected"] = True
            result["reason"] = "non_allowlisted"
            return result
        if not slice_dir.is_dir():
            result["rejected"] = True
            result["reason"] = "not_directory"
            return result
        result["readable"] = True
        entries = list(os.scandir(slice_dir))
    except OSError:
        result["rejected"] = True
        result["reason"] = "unreadable"
        return result

    if not entries:
        result["rejected"] = True
        result["reason"] = "empty"
        return result

    filenames: set[str] = set()
    for entry in entries:
        name = entry.name
        # Hidden files, symlinks, directories, and non-JSON files are rejected.
        if name.startswith("."):
            result["rejected"] = True
            result["reason"] = "non_allowlisted"
            return result
        if entry.is_symlink():
            result["rejected"] = True
            result["reason"] = "non_allowlisted"
            return result
        if entry.is_dir(follow_symlinks=False):
            result["rejected"] = True
            result["reason"] = "non_allowlisted"
            return result
        if not name.endswith(".json"):
            result["rejected"] = True
            result["reason"] = "non_allowlisted"
            return result
        if name not in ALLOWED_SLICE_FILENAMES:
            result["rejected"] = True
            result["reason"] = "non_allowlisted"
            return result
        filenames.add(name)

    result["files"] = filenames

    # Missing required reports.
    missing = REQUIRED_SLICE_FILENAMES - filenames
    if missing:
        result["rejected"] = True
        result["reason"] = "missing_required"
        return result

    # Validate JSON and safety of each file.
    for name in filenames:
        file_path = slice_dir / name
        try:
            data = _read_json(file_path)
        except Exception:
            result["rejected"] = True
            result["reason"] = "invalid_json"
            return result

        safe, reason = _check_report_safety(data)
        if not safe:
            result["rejected"] = True
            if reason == "self_test_report" or reason == "self_test_status":
                result["reason"] = "self_test"
            else:
                result["reason"] = "unsafe_upstream"
            return result

    result["accepted"] = True
    return result


def _collect_slice_dirs(args: argparse.Namespace) -> list[Path]:
    dirs: set[Path] = set()
    for d in (args.slice_dir or []):
        # Preserve symlink identity so validation can reject it.
        dirs.add(d)
    for root in (args.slice_root_dir or []):
        # Preserve symlink identity; do not traverse symlink roots.
        if root.is_symlink():
            continue
        if root.is_dir():
            try:
                for entry in os.scandir(root):
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                        dirs.add(Path(entry.path))
            except OSError:
                pass
    return sorted(dirs)


def _run_p62(
    manifest_path: Path,
    matrix_out: Path,
    report_out: Path,
    doc_out: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Run P62 via subprocess. Return its public report or a stub on failure."""
    script = _eval_dir() / "p62_generalization_matrix_aggregator.py"
    args = [
        sys.executable,
        str(script),
        "--slice-manifest",
        str(manifest_path),
        "--p57-input-matrix-out",
        str(matrix_out),
        "--out",
        str(report_out),
        "--doc",
        str(doc_out),
    ]
    rc, stdout, stderr = _run_subprocess(args, cwd=repo_root)
    if rc != 0:
        raise RuntimeError(f"P62 subprocess failed: rc={rc} stdout={stdout} stderr={stderr}")
    return _read_json(report_out)


def _run_p57(
    matrix_path: Path,
    report_out: Path,
    doc_out: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Run P57 via subprocess. Return its public report or a stub on failure."""
    script = _eval_dir() / "p57_generalization_gate.py"
    args = [
        sys.executable,
        str(script),
        "--input-matrix",
        str(matrix_path),
        "--out",
        str(report_out),
        "--doc",
        str(doc_out),
    ]
    rc, stdout, stderr = _run_subprocess(args, cwd=repo_root)
    if rc != 0:
        raise RuntimeError(f"P57 subprocess failed: rc={rc} stdout={stdout} stderr={stderr}")
    return _read_json(report_out)


def _run_p61(
    p57_report: Path,
    representative_slice_dir: Path,
    report_out: Path,
    doc_out: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Run P61 via subprocess on a representative accepted slice."""
    script = _eval_dir() / "p61_pre_spend_gate.py"
    args = [
        sys.executable,
        str(script),
        "--p57-report",
        str(p57_report),
        "--p58-report",
        str(representative_slice_dir / "p58_source_backed_verifier_calibration_report.json"),
        "--p59-report",
        str(representative_slice_dir / "p59_contrastive_pack_coverage_counterfactual_report.json"),
        "--p60-report",
        str(representative_slice_dir / "p60_rmc_policy_v2_report.json"),
        "--p51b-report",
        str(representative_slice_dir / "p51b_llm_opt_in_contract_report.json"),
        "--p52c-report",
        str(representative_slice_dir / "p52c_local_verifier_scoring_simulator_report.json"),
        "--out",
        str(report_out),
        "--doc",
        str(doc_out),
    ]
    rc, stdout, stderr = _run_subprocess(args, cwd=repo_root)
    if rc != 0:
        raise RuntimeError(f"P61 subprocess failed: rc={rc} stdout={stdout} stderr={stderr}")
    return _read_json(report_out)


def _build_p63_report(
    *,
    self_test: bool,
    validation_results: list[dict[str, Any]],
    accepted_slice_dirs: list[Path],
    p62_report: dict[str, Any] | None,
    p57_report: dict[str, Any] | None,
    p61_report: dict[str, Any] | None,
    p61_run_attempted: bool,
    p57_run_attempted: bool,
    p62_manifest_written: bool,
    p62_manifest_entry_count: int,
    p62_matrix_written: bool,
    p62_matrix_entry_count: int,
    elapsed_ms: int,
    repo_root: Path,
    orchestration_error: str | None,
) -> dict[str, Any]:
    """Build the sanitized public P63 report."""

    input_directory_count = len(validation_results)
    readable_directory_count = sum(1 for r in validation_results if r["readable"])
    empty_directory_count = sum(1 for r in validation_results if r.get("reason") == "empty")
    non_allowlisted_count = sum(1 for r in validation_results if r.get("reason") == "non_allowlisted")
    invalid_json_count = sum(1 for r in validation_results if r.get("reason") == "invalid_json")
    missing_required_count = sum(1 for r in validation_results if r.get("reason") == "missing_required")
    self_test_count = sum(1 for r in validation_results if r.get("reason") == "self_test")
    unsafe_count = sum(1 for r in validation_results if r.get("reason") == "unsafe_upstream")
    rejected_count = sum(1 for r in validation_results if r.get("rejected"))
    accepted_count = input_directory_count - rejected_count

    p62_status = (p62_report or {}).get("status")
    p62_input_summary = (p62_report or {}).get("input_summary") or {}
    p62_contract = (p62_report or {}).get("p57_consumption_contract") or {}
    p62_eligible_distinct_slice_count = p62_input_summary.get("eligible_distinct_slice_count", 0)
    p62_content_distinct_input_count = p62_input_summary.get("content_distinct_input_count", 0)
    p62_duplicate_input_count = p62_input_summary.get("duplicate_input_count", 0)
    p62_exact_duplicate_inputs_rejected_count = p62_input_summary.get("exact_duplicate_inputs_rejected_count", 0)
    p62_matrix_entry_count = p62_contract.get("p57_input_matrix_entry_count", 0)

    p57_status = (p57_report or {}).get("status")
    p57_generalization_matrix = (p57_report or {}).get("generalization_matrix") or {}
    p57_input_summary = (p57_report or {}).get("input_summary") or {}
    p57_upstream_safety_gate = (p57_report or {}).get("upstream_safety_gate") or {}
    p57_readiness_status = p57_generalization_matrix.get("readiness_status")
    p57_required_slice_count = p57_generalization_matrix.get("required_slice_count", 4)
    p57_included_slice_count = p57_input_summary.get("included_generalization_slice_count", 0)
    p57_required_met = (
        isinstance(p57_included_slice_count, int)
        and p57_included_slice_count >= p57_required_slice_count
    )
    p57_safety_blocker_count = p57_upstream_safety_gate.get("blocker_count", 0)

    p61_status = (p61_report or {}).get("status")
    p61_readiness = (p61_report or {}).get("readiness_decision") or {}
    p61_decision = p61_readiness.get("decision")

    blockers: list[str] = []
    warnings: list[str] = []

    if input_directory_count == 0:
        blockers.append("no_input_directories_provided")
    if rejected_count > 0:
        warnings.append(f"rejected_slice_directory_count={rejected_count}")
    if non_allowlisted_count > 0:
        blockers.append(f"non_allowlisted_artifact_directory_count={non_allowlisted_count}")
    if invalid_json_count > 0:
        blockers.append(f"invalid_json_report_directory_count={invalid_json_count}")
    if missing_required_count > 0:
        blockers.append(f"missing_required_aggregate_report_directory_count={missing_required_count}")
    if self_test_count > 0:
        blockers.append(f"self_test_directory_count={self_test_count}")
    if unsafe_count > 0:
        blockers.append(f"unsafe_upstream_report_directory_count={unsafe_count}")
    if accepted_count < 4:
        blockers.append(f"accepted_slice_directory_count={accepted_count} < required 4")

    p62_runnable = p62_report is not None and p62_status in {
        "diagnostic_matrix_complete",
        "diagnostic_matrix_unstable",
    }
    p57_runnable = p57_run_attempted and p57_report is not None and p57_status in {
        "diagnostic_matrix_complete",
        "diagnostic_matrix_unstable",
    }

    if not p62_runnable:
        blockers.append("p62_matrix_not_runnable")
    if p57_run_attempted and not p57_runnable:
        blockers.append("p57_matrix_not_runnable")
    if orchestration_error:
        blockers.append("orchestration_failed")

    multi_slice_matrix_actionable = (
        p62_runnable
        and p57_runnable
        and p57_required_met
        and p57_safety_blocker_count == 0
    )

    if self_test:
        status = "self_test_only"
    elif orchestration_error:
        status = "orchestration_failed"
    elif input_directory_count == 0:
        status = "no_inputs"
    elif rejected_count == input_directory_count:
        # All inputs rejected. Prefer invalid_input_artifacts if any non-allowlisted.
        if non_allowlisted_count > 0 or invalid_json_count > 0:
            status = "invalid_input_artifacts"
        elif missing_required_count > 0:
            status = "invalid_input_artifacts"
        elif unsafe_count > 0:
            status = "blocked_safety"
        elif self_test_count > 0:
            status = "invalid_input_artifacts"
        else:
            status = "no_inputs"
    elif accepted_count < 4 or p62_eligible_distinct_slice_count < 4:
        status = "insufficient_matrix_inputs"
    elif not multi_slice_matrix_actionable:
        status = "matrix_not_actionable"
    else:
        status = "matrix_actionable_precondition_only"

    status_reason = "; ".join(blockers) if blockers else "aggregate cross-run slice collector evaluation complete"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": status_reason,
        "self_test": self_test,
        "not_quality_evidence": True,
        "precondition_report_only": True,
        "matrix_actionability_only": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
        "provider_spend_authorized": False,
        "micro_run_not_authorized": True,
        "workflow_dispatch_required_for_live_run": True,
        "remote_calls_by_p63": 0,
        "llm_calls_by_p63": 0,
        "remote_requests_by_p63": 0,
        "provider_config_read_by_p63": False,
        "prompt_construction_by_p63": False,
        "source_reads_attempted_by_p63": False,
        "gold_used_by_p63": False,
        "private_labels_loaded_by_p63": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_query_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "private_labels_committed": False,
        "elapsed_ms": elapsed_ms,
        "input_validation_summary": {
            "input_directory_count": input_directory_count,
            "readable_directory_count": readable_directory_count,
            "accepted_slice_directory_count": accepted_count,
            "rejected_slice_directory_count": rejected_count,
            "empty_directory_count": empty_directory_count,
            "non_allowlisted_artifact_directory_count": non_allowlisted_count,
            "missing_required_aggregate_report_directory_count": missing_required_count,
            "invalid_json_report_directory_count": invalid_json_count,
            "self_test_directory_count": self_test_count,
            "unsafe_upstream_report_directory_count": unsafe_count,
        },
        "p62_handoff_summary": {
            "p62_manifest_written": p62_manifest_written,
            "p62_manifest_entry_count": p62_manifest_entry_count,
            "p62_status": p62_status,
            "p62_eligible_distinct_slice_count": p62_eligible_distinct_slice_count,
            "p62_content_distinct_input_count": p62_content_distinct_input_count,
            "p62_duplicate_input_count": p62_duplicate_input_count,
            "p62_exact_duplicate_inputs_rejected_count": p62_exact_duplicate_inputs_rejected_count,
            "p62_p57_input_matrix_written": p62_matrix_written,
            "p62_p57_input_matrix_entry_count": p62_matrix_entry_count,
        },
        "p57_matrix_summary": {
            "p57_run_attempted": p57_run_attempted,
            "p57_status": p57_status,
            "p57_readiness_status": p57_readiness_status,
            "p57_required_slice_count_met": p57_required_met,
            "p57_included_generalization_slice_count": p57_included_slice_count,
            "p57_upstream_safety_blocker_count": p57_safety_blocker_count,
        },
        "p61_pre_spend_summary": {
            "p61_run_attempted": p61_run_attempted,
            "p61_status": p61_status,
            "p61_decision": p61_decision,
            "p61_decision_is_authorization": False,
            "p61_provider_spend_authorized": False,
            "p61_requires_separate_human_or_workflow_dispatch": True,
            "representative_internal_slice": p61_run_attempted,
        },
        "final_actionability": {
            "multi_slice_matrix_actionable": multi_slice_matrix_actionable,
            "actionability_status": (
                "matrix_actionable_precondition_only"
                if multi_slice_matrix_actionable
                else "matrix_not_actionable"
            ),
            "actionability_is_authorization": False,
            "provider_spend_authorized": False,
            "requires_separate_human_or_workflow_dispatch": True,
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        "warnings": warnings,
        "blockers": blockers,
        "conclusion": [
            "P63 Cross-Run Slice Collector / Matrix Runner v0 is a deterministic, offline, aggregate-only orchestrator.",
            "P63 does not fetch artifacts from a network, call providers, construct prompts, read source files, or expose run, repo, dataset, or directory identity.",
            "P63 validates only local directories and allowlisted aggregate JSON report filenames, then delegates to P62, P57, and P61 offline.",
            "P63 output is not quality evidence, not a promotion or default gate, not live-readiness evidence, and not provider spend authorization.",
            "A multi-slice aggregate-only matrix is actionable as a precondition-only offline diagnostic; any future live provider run requires separate human or workflow_dispatch authorization.",
        ],
        "validation": {
            "forbidden_key_scan_ok": True,
            "self_test_assertions_passed": self_test,
        },
    }

    if self_test:
        report["conclusion"].append(
            "This self-test exercised no-input, insufficient-input, duplicate-collapse, non-allowlisted-file, symlink or subdir, missing-report, and self-test or unsafe-slice rejection paths in memory with synthetic aggregate reports."
        )

    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        errors.append("generated_by mismatch")
    if report.get("stage") != STAGE:
        errors.append("stage mismatch")
    if report.get("status") not in ALLOWED_STATUS:
        errors.append(f"status must be one of {ALLOWED_STATUS}")
    if report.get("self_test") and report.get("status") != "self_test_only":
        errors.append("self_test must set status=self_test_only")
    if report.get("status") == "self_test_only" and report.get("self_test") is not True:
        errors.append("status self_test_only requires self_test=true")

    # Required safety flags.
    expected_true = {
        "not_quality_evidence",
        "precondition_report_only",
        "matrix_actionability_only",
        "candidate_not_fact",
        "aggregate_only_public_artifact",
        "micro_run_not_authorized",
        "workflow_dispatch_required_for_live_run",
    }
    expected_false = {
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "provider_spend_authorized",
        "prompt_construction_by_p63",
        "source_reads_attempted_by_p63",
        "gold_used_by_p63",
        "private_labels_loaded_by_p63",
        "provider_config_read_by_p63",
    }
    for flag in expected_true:
        if report.get(flag) is not True:
            errors.append(f"{flag} must be true")
    for flag in expected_false:
        if report.get(flag) is not False:
            errors.append(f"{flag} must be false")

    for flag in ["remote_calls_by_p63", "llm_calls_by_p63", "remote_requests_by_p63"]:
        if report.get(flag) != 0:
            errors.append(f"{flag} must be 0")

    for flag in RAW_FLAGS:
        if report.get(flag) is not False:
            errors.append(f"{flag} must be false")

    # Required summary blocks.
    for block in [
        "input_validation_summary",
        "p62_handoff_summary",
        "p57_matrix_summary",
        "p61_pre_spend_summary",
        "final_actionability",
        "warnings",
        "blockers",
        "validation",
    ]:
        if block not in report:
            errors.append(f"missing required block: {block}")

    # P63-specific authorization flags.
    p61_summary = report.get("p61_pre_spend_summary") or {}
    if p61_summary.get("p61_decision_is_authorization") is not False:
        errors.append("p61_decision_is_authorization must be false")
    if p61_summary.get("p61_provider_spend_authorized") is not False:
        errors.append("p61_provider_spend_authorized must be false")
    if p61_summary.get("p61_requires_separate_human_or_workflow_dispatch") is not True:
        errors.append("p61_requires_separate_human_or_workflow_dispatch must be true")

    final = report.get("final_actionability") or {}
    if final.get("actionability_is_authorization") is not False:
        errors.append("actionability_is_authorization must be false")
    if final.get("provider_spend_authorized") is not False:
        errors.append("final_actionability.provider_spend_authorized must be false")
    if final.get("requires_separate_human_or_workflow_dispatch") is not True:
        errors.append("final_actionability.requires_separate_human_or_workflow_dispatch must be true")

    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_is_path_or_secret_value(report))

    # Forbidden claims in text fields.
    forbidden_claims = [
        "generalization proven",
        "dataset diversity proven",
        "repo diversity proven",
        "four distinct repos",
        "multi-repo evidence",
        "quality evidence",
        "promotion ready",
        "default should change",
        "live-readiness proven",
        "P51-C authorized",
        "provider spend authorized",
        "safe to spend",
        "safe to run live LLM",
        "research-quality finding",
    ]
    text_fields: list[str] = []
    for field in ("status_reason", "conclusion", "warnings", "blockers"):
        val = report.get(field)
        if isinstance(val, str):
            text_fields.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    text_fields.append(item)
    for text in text_fields:
        lower = text.lower()
        for claim in forbidden_claims:
            # Allow explicit negation.
            negated = f"not {claim}"
            if claim in lower and negated not in lower:
                errors.append(f"forbidden claim in text: {claim}")

    # Avoid CI secret regex patterns like "authorization:".
    for text in text_fields:
        if re.search(r"(?i)authorization\s*[:=]", text):
            errors.append("text field contains forbidden authorization pattern")

    return errors


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P63: {report['remote_calls_by_p63']}",
        f"- LLM calls by P63: {report['llm_calls_by_p63']}",
        f"- Provider config read by P63: {report['provider_config_read_by_p63']}",
        f"- Prompt construction by P63: {report['prompt_construction_by_p63']}",
        f"- Source reads attempted by P63: {report['source_reads_attempted_by_p63']}",
        "",
    ])

    lines.extend([
        "## Purpose",
        "",
        "P63 Cross-Run Slice Collector / Matrix Runner v0 is a deterministic, offline, no-provider, no-live-LLM, aggregate-only orchestrator.",
        "It collects already-downloaded local per-run artifact directories, validates that they contain only allowlisted aggregate report JSON files, builds a P62 slice manifest, and runs P62 -> P57 -> P61 offline.",
        "P63 is **not** a fetcher, **not** quality evidence, **not** provider spend authorization, and **not** repo or dataset diversity proof.",
        "",
        "## Methodology",
        "",
        "- Accept only local directories via `--slice-root-dir PATH` and `--slice-dir PATH`.",
        "- Reject any directory containing non-allowlisted files, subdirectories, symlinks, hidden files, logs, JSONL, prompts, responses, provider configs, source files, or non-JSON files.",
        "- Require each accepted slice to contain all 14 required aggregate JSON reports (P46/P47/P48/P49/P50/P52/P52A/P52B/P52C/P51B/P57/P58/P59/P60). P51 and P61 are optional.",
        "- Build a P62 slice manifest and run `p62_generalization_matrix_aggregator.py` to produce a P57-compatible input matrix.",
        "- If the matrix is valid, run `p57_generalization_gate.py` to check multi-slice generalization readiness.",
        "- If a representative accepted slice exists, run `p61_pre_spend_gate.py` to report pre-spend preconditions, but never authorize spend.",
        "- Emit only aggregate counts and status enums; never expose run, repo, dataset, or directory identity.",
        "",
        "## Safety notes",
        "",
        "- P63 makes no network, remote, LLM, or provider calls.",
        "- P63 does not fetch artifacts, construct prompts, read source files, tasks, candidates, labels, or ephemeral records.",
        "- P63 does not publish paths, repo IDs, dataset IDs, run IDs, task IDs, candidate IDs, spans, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.",
        "- P63 output is aggregate-only and explicitly not a promotion or default gate or live-readiness authorization.",
        "",
    ])

    inp = report["input_validation_summary"]
    lines.extend([
        "## Input validation summary",
        "",
        f"- Input directories: {inp['input_directory_count']}",
        f"- Readable directories: {inp['readable_directory_count']}",
        f"- Accepted slice directories: {inp['accepted_slice_directory_count']}",
        f"- Rejected slice directories: {inp['rejected_slice_directory_count']}",
        f"- Empty directories: {inp['empty_directory_count']}",
        f"- Non-allowlisted artifact directories: {inp['non_allowlisted_artifact_directory_count']}",
        f"- Missing required report directories: {inp['missing_required_aggregate_report_directory_count']}",
        f"- Invalid JSON report directories: {inp['invalid_json_report_directory_count']}",
        f"- Self-test directories: {inp['self_test_directory_count']}",
        f"- Unsafe upstream report directories: {inp['unsafe_upstream_report_directory_count']}",
        "",
    ])

    p62 = report["p62_handoff_summary"]
    lines.extend([
        "## P62 handoff summary",
        "",
        f"- P62 manifest written: {p62['p62_manifest_written']}",
        f"- P62 manifest entry count: {p62['p62_manifest_entry_count']}",
        f"- P62 status: `{p62['p62_status']}`",
        f"- P62 eligible distinct slice count: {p62['p62_eligible_distinct_slice_count']}",
        f"- P62 content distinct input count: {p62['p62_content_distinct_input_count']}",
        f"- P62 duplicate input count: {p62['p62_duplicate_input_count']}",
        f"- P62 exact duplicate inputs rejected: {p62['p62_exact_duplicate_inputs_rejected_count']}",
        f"- P62 P57 input matrix written: {p62['p62_p57_input_matrix_written']}",
        f"- P62 P57 input matrix entry count: {p62['p62_p57_input_matrix_entry_count']}",
        "",
    ])

    p57 = report["p57_matrix_summary"]
    lines.extend([
        "## P57 matrix summary",
        "",
        f"- P57 run attempted: {p57['p57_run_attempted']}",
        f"- P57 status: `{p57['p57_status']}`",
        f"- P57 readiness status: `{p57['p57_readiness_status']}`",
        f"- P57 required slice count met: {p57['p57_required_slice_count_met']}",
        f"- P57 included generalization slice count: {p57['p57_included_generalization_slice_count']}",
        f"- P57 upstream safety blocker count: {p57['p57_upstream_safety_blocker_count']}",
        "",
    ])

    p61 = report["p61_pre_spend_summary"]
    lines.extend([
        "## P61 pre-spend summary",
        "",
        f"- P61 run attempted: {p61['p61_run_attempted']}",
        f"- P61 status: `{p61['p61_status']}`",
        f"- P61 decision: `{p61['p61_decision']}`",
        f"- P61 decision is authorization flag: {p61['p61_decision_is_authorization']}",
        f"- P61 provider spend authorization flag: {p61['p61_provider_spend_authorized']}",
        f"- P61 requires separate human or workflow_dispatch: {p61['p61_requires_separate_human_or_workflow_dispatch']}",
        f"- Representative internal slice selected: {p61['representative_internal_slice']}",
        "",
    ])

    fa = report["final_actionability"]
    lines.extend([
        "## Final actionability",
        "",
        f"- Multi-slice matrix actionable: {fa['multi_slice_matrix_actionable']}",
        f"- Actionability status: `{fa['actionability_status']}`",
        f"- Actionability is authorization flag: {fa['actionability_is_authorization']}",
        f"- Provider spend authorization flag: {fa['provider_spend_authorized']}",
        f"- Requires separate human or workflow_dispatch: {fa['requires_separate_human_or_workflow_dispatch']}",
        f"- Blocker count: {fa['blocker_count']}",
        f"- Warning count: {fa['warning_count']}",
        "",
    ])

    lines.extend([
        "## Blockers",
        "",
    ])
    if report["blockers"]:
        for b in report["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend([
        "## Warnings",
        "",
    ])
    if report["warnings"]:
        for w in report["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend([
        "## Conclusion",
        "",
    ])
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test helpers
# ---------------------------------------------------------------------------

def _import_p62() -> Any:
    """Import P62 module from the eval directory for self-test helpers."""
    eval_dir = _eval_dir()
    if str(eval_dir) not in sys.path:
        sys.path.insert(0, str(eval_dir))
    import p62_generalization_matrix_aggregator as p62
    return p62


def _import_p61() -> Any:
    """Import P61 module from the eval directory for self-test helpers."""
    eval_dir = _eval_dir()
    if str(eval_dir) not in sys.path:
        sys.path.insert(0, str(eval_dir))
    import p61_pre_spend_gate as p61
    return p61


def _make_p57_upstream_report(phase: str) -> dict[str, Any]:
    """Generate a minimal safe P57 upstream aggregate report for self-test."""
    report: dict[str, Any] = {
        "schema_version": f"{phase}-aggregate-report-v0",
        "status": "ok",
        "self_test": False,
        "not_quality_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "task_count": 7,
        "positive_task_count": 5,
        "no_gold_task_count": 2,
    }
    remote_key = f"remote_calls_by_{phase}"
    llm_key = f"llm_calls_by_{phase}"
    prompt_key = f"prompt_construction_by_{phase}"
    source_reads_key = f"source_reads_attempted_by_{phase}"
    source_bounded_key = f"source_reads_bounded_by_{phase}"
    provider_config_key = f"provider_config_read_by_{phase}"
    report[remote_key] = 0
    report[llm_key] = 0
    report[prompt_key] = False
    report[provider_config_key] = False
    if phase in {"p52a", "p52b", "p52c"}:
        report[source_reads_key] = True
        report[source_bounded_key] = True
    else:
        report[source_reads_key] = False
    for flag in RAW_FLAGS:
        report[flag] = False
    # P51-B specific extra flags.
    if phase == "p51b":
        report["remote_requests_by_p51b"] = 0
        report["dry_run_payload_validation_only"] = True
        report["p51b_live_calls_disabled"] = True
    return report


def _make_p57_upstream_reports() -> dict[str, dict[str, Any]]:
    phases = [
        "p46", "p47", "p48", "p49", "p50",
        "p52", "p52a", "p52b", "p52c", "p51b",
    ]
    return {phase: _make_p57_upstream_report(phase) for phase in phases}


def _write_slice_dir(
    slice_dir: Path,
    seed: int,
    p62_mod: Any,
    unsafe: bool = False,
    self_test_report: bool = False,
) -> None:
    """Write a synthetic slice directory for self-test."""
    slice_dir.mkdir(parents=True, exist_ok=True)
    # P57 upstream reports (P51B needs task_count for P57 gate).
    upstream_reports = _make_p57_upstream_reports()
    for phase, report in upstream_reports.items():
        if self_test_report:
            report["self_test"] = True
            report["status"] = "self_test_only"
        if unsafe and phase == "p46":
            report["promotion_ready"] = True
        filename = {
            "p46": "p46_candidate_reach_cost_map_report.json",
            "p47": "p47_request_more_context_report.json",
            "p48": "p48_diagnostic_policy_simulator_report.json",
            "p49": "p49_contrastive_candidate_pack_scaffold_report.json",
            "p50": "p50_fixed_suite_validation_report.json",
            "p52": "p52_metadata_local_verifier_scaffold_report.json",
            "p52a": "p52a_source_materialization_prerequisite_report.json",
            "p52b": "p52b_source_backed_local_verifier_feature_matrix_report.json",
            "p52c": "p52c_local_verifier_scoring_simulator_report.json",
            "p51b": "p51b_llm_opt_in_contract_report.json",
        }[phase]
        _write_json(slice_dir / filename, report)

    # P57/P58/P59/P60/P51B reports via P62 helper. Merge P51B with upstream so P51B
    # keeps both P57-required task counts and P62/P61-required metrics.
    slice_data = p62_mod._make_eligible_slice(seed)
    for phase in ["p57", "p58", "p59", "p60", "p51b"]:
        report = slice_data[phase]
        if self_test_report:
            report["self_test"] = True
            report["status"] = "self_test_only"
        filename = {
            "p57": "p57_generalization_gate_report.json",
            "p58": "p58_source_backed_verifier_calibration_report.json",
            "p59": "p59_contrastive_pack_coverage_counterfactual_report.json",
            "p60": "p60_rmc_policy_v2_report.json",
            "p51b": "p51b_llm_opt_in_contract_report.json",
        }[phase]
        if phase == "p51b":
            merged = dict(upstream_reports["p51b"])
            merged.update(report)
            report = merged
        _write_json(slice_dir / filename, report)


def _run_p63_pipeline(
    slice_dirs: list[Path],
    output_paths: dict[str, Path],
    repo_root: Path,
    self_test: bool = False,
) -> dict[str, Any]:
    """Shared pipeline used by both main and self-test."""
    start = time.monotonic()
    validation_results = [_validate_slice_dir(d) for d in slice_dirs]
    accepted_slice_dirs = [d for d, r in zip(slice_dirs, validation_results) if not r.get("rejected")]

    p62_report: dict[str, Any] | None = None
    p57_report: dict[str, Any] | None = None
    p61_report: dict[str, Any] | None = None
    p62_manifest_written = False
    p62_manifest_entry_count = 0
    p62_matrix_written = False
    p62_matrix_entry_count = 0
    p57_run_attempted = False
    p57_current_report_available = False
    p61_run_attempted = False
    orchestration_error: str | None = None

    try:
        # Remove stale handoff outputs from prior runs at the same path. P61 must
        # never consume an old P57 report if this invocation does not create one.
        for key in [
            "p57_matrix_out",
            "p57_report_out",
            "p57_doc_out",
            "p61_report_out",
            "p61_doc_out",
        ]:
            try:
                output_paths[key].unlink()
            except FileNotFoundError:
                pass
        if accepted_slice_dirs:
            manifest_path = output_paths["manifest_out"]
            manifest = [{"slice_dir": str(d)} for d in accepted_slice_dirs]
            _write_json(manifest_path, manifest)
            p62_manifest_written = True
            p62_manifest_entry_count = len(manifest)

            p62_report = _run_p62(
                manifest_path,
                output_paths["p57_matrix_out"],
                output_paths["p62_report_out"],
                output_paths["p62_doc_out"],
                repo_root,
            )
            p62_matrix_written = bool(p62_report.get("p57_consumption_contract", {}).get("p57_input_matrix_written"))
            p62_matrix_entry_count = int(p62_report.get("p57_consumption_contract", {}).get("p57_input_matrix_entry_count", 0))

            if p62_matrix_written and p62_matrix_entry_count > 0:
                p57_run_attempted = True
                p57_report = _run_p57(
                    output_paths["p57_matrix_out"],
                    output_paths["p57_report_out"],
                    output_paths["p57_doc_out"],
                    repo_root,
                )
                p57_current_report_available = True

            if accepted_slice_dirs and p57_current_report_available:
                p61_run_attempted = True
                representative = sorted(accepted_slice_dirs, key=lambda p: str(p))[0]
                p61_report = _run_p61(
                    output_paths["p57_report_out"],
                    representative,
                    output_paths["p61_report_out"],
                    output_paths["p61_doc_out"],
                    repo_root,
                )
    except Exception as exc:
        orchestration_error = str(exc)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    report = _build_p63_report(
        self_test=self_test,
        validation_results=validation_results,
        accepted_slice_dirs=accepted_slice_dirs,
        p62_report=p62_report,
        p57_report=p57_report,
        p61_report=p61_report,
        p61_run_attempted=p61_run_attempted,
        p57_run_attempted=p57_run_attempted,
        p62_manifest_written=p62_manifest_written,
        p62_manifest_entry_count=p62_manifest_entry_count,
        p62_matrix_written=p62_matrix_written,
        p62_matrix_entry_count=p62_matrix_entry_count,
        elapsed_ms=elapsed_ms,
        repo_root=repo_root,
        orchestration_error=orchestration_error,
    )
    return report


def _run_self_test_assertions() -> None:
    """Exercise all P63 validation and orchestration paths in memory."""
    p62_mod = _import_p62()
    repo_root = _eval_dir().parent

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        def make_output_paths(prefix: str) -> dict[str, Path]:
            return {
                "manifest_out": out_dir / f"{prefix}_manifest.json",
                "p57_matrix_out": out_dir / f"{prefix}_matrix.json",
                "p62_report_out": out_dir / f"{prefix}_p62.json",
                "p62_doc_out": out_dir / f"{prefix}_p62.md",
                "p57_report_out": out_dir / f"{prefix}_p57.json",
                "p57_doc_out": out_dir / f"{prefix}_p57.md",
                "p61_report_out": out_dir / f"{prefix}_p61.json",
                "p61_doc_out": out_dir / f"{prefix}_p61.md",
            }

        # 1) No inputs.
        report = _run_p63_pipeline([], make_output_paths("no_inputs"), repo_root)
        assert report["status"] == "no_inputs", report["status"]

        # 2) Fewer than 4 accepted slices.
        slices_3 = [tmp_path / f"slice_3_{i}" for i in range(3)]
        for i, d in enumerate(slices_3):
            _write_slice_dir(d, i, p62_mod)
        report = _run_p63_pipeline(slices_3, make_output_paths("three"), repo_root)
        assert report["status"] == "insufficient_matrix_inputs", report["status"]
        assert report["p62_handoff_summary"]["p62_eligible_distinct_slice_count"] == 3

        # 3) 4 distinct accepted slices => matrix actionable precondition only.
        slices_4 = [tmp_path / f"slice_4_{i}" for i in range(4)]
        for i, d in enumerate(slices_4):
            _write_slice_dir(d, i, p62_mod)
        report = _run_p63_pipeline(slices_4, make_output_paths("four"), repo_root)
        assert report["status"] == "matrix_actionable_precondition_only", report["status"]
        assert report["p62_handoff_summary"]["p62_eligible_distinct_slice_count"] == 4
        assert report["p57_matrix_summary"]["p57_run_attempted"] is True
        assert report["p61_pre_spend_summary"]["p61_run_attempted"] is True
        assert report["p61_pre_spend_summary"]["p61_decision_is_authorization"] is False
        assert report["p61_pre_spend_summary"]["p61_provider_spend_authorized"] is False

        # 4) 4 duplicates collapse by P62.
        dup_slices = [tmp_path / f"dup_{i}" for i in range(4)]
        for d in dup_slices:
            _write_slice_dir(d, 0, p62_mod)
        report = _run_p63_pipeline(dup_slices, make_output_paths("dup"), repo_root)
        assert report["status"] == "insufficient_matrix_inputs", report["status"]
        assert report["p62_handoff_summary"]["p62_content_distinct_input_count"] == 1
        assert report["p62_handoff_summary"]["p62_duplicate_input_count"] == 3

        # 5) Non-allowlisted file.
        bad_dir = tmp_path / "bad_file"
        _write_slice_dir(bad_dir, 0, p62_mod)
        (bad_dir / "extra.log").write_text("log", encoding="utf-8")
        report = _run_p63_pipeline([bad_dir], make_output_paths("bad_file"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]
        assert report["input_validation_summary"]["non_allowlisted_artifact_directory_count"] == 1

        # 6) JSONL file.
        jsonl_dir = tmp_path / "jsonl_dir"
        _write_slice_dir(jsonl_dir, 0, p62_mod)
        (jsonl_dir / "trace.jsonl").write_text("{}", encoding="utf-8")
        report = _run_p63_pipeline([jsonl_dir], make_output_paths("jsonl"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]
        assert report["input_validation_summary"]["non_allowlisted_artifact_directory_count"] == 1

        # 7) Prompt/response envelope.
        prompt_dir = tmp_path / "prompt_dir"
        _write_slice_dir(prompt_dir, 0, p62_mod)
        (prompt_dir / "prompts.json").write_text(json.dumps({"prompt": "x"}), encoding="utf-8")
        report = _run_p63_pipeline([prompt_dir], make_output_paths("prompt"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]

        # 8) Subdirectory.
        subdir_dir = tmp_path / "subdir_dir"
        _write_slice_dir(subdir_dir, 0, p62_mod)
        (subdir_dir / "nested").mkdir()
        (subdir_dir / "nested" / "x.json").write_text("{}", encoding="utf-8")
        report = _run_p63_pipeline([subdir_dir], make_output_paths("subdir"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]

        # 9) Symlink.
        link_dir = tmp_path / "link_dir"
        _write_slice_dir(link_dir, 0, p62_mod)
        (link_dir / "link.json").symlink_to(link_dir / "p46_candidate_reach_cost_map_report.json")
        report = _run_p63_pipeline([link_dir], make_output_paths("link"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]

        # 9b) Symlinked slice directory passed explicitly must be rejected.
        real_slice_dir = tmp_path / "real_slice_dir"
        _write_slice_dir(real_slice_dir, 0, p62_mod)
        symlink_slice_dir = tmp_path / "symlink_slice_dir"
        symlink_slice_dir.symlink_to(real_slice_dir, target_is_directory=True)
        report = _run_p63_pipeline([symlink_slice_dir], make_output_paths("symlink_slice_dir"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]

        # 9c) Symlinked child under a root must not be collected.
        root_with_link = tmp_path / "root_with_link"
        root_with_link.mkdir()
        (root_with_link / "slice_link_child").symlink_to(real_slice_dir, target_is_directory=True)
        collected = _collect_slice_dirs(argparse.Namespace(slice_dir=[], slice_root_dir=[root_with_link]))
        assert collected == [], collected

        # 10) Missing required report.
        missing_dir = tmp_path / "missing_dir"
        _write_slice_dir(missing_dir, 0, p62_mod)
        (missing_dir / "p60_rmc_policy_v2_report.json").unlink()
        report = _run_p63_pipeline([missing_dir], make_output_paths("missing"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]
        assert report["input_validation_summary"]["missing_required_aggregate_report_directory_count"] == 1

        # 11) Invalid JSON.
        invalid_dir = tmp_path / "invalid_dir"
        _write_slice_dir(invalid_dir, 0, p62_mod)
        (invalid_dir / "p46_candidate_reach_cost_map_report.json").write_text("not json", encoding="utf-8")
        report = _run_p63_pipeline([invalid_dir], make_output_paths("invalid"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]
        assert report["input_validation_summary"]["invalid_json_report_directory_count"] == 1

        # 12) Self-test report.
        st_dir = tmp_path / "st_dir"
        _write_slice_dir(st_dir, 0, p62_mod, self_test_report=True)
        report = _run_p63_pipeline([st_dir], make_output_paths("st"), repo_root)
        assert report["status"] == "invalid_input_artifacts", report["status"]
        assert report["input_validation_summary"]["self_test_directory_count"] == 1

        # 13) Unsafe upstream report.
        unsafe_dir = tmp_path / "unsafe_dir"
        _write_slice_dir(unsafe_dir, 0, p62_mod, unsafe=True)
        report = _run_p63_pipeline([unsafe_dir], make_output_paths("unsafe"), repo_root)
        assert report["status"] in {"invalid_input_artifacts", "blocked_safety"}, report["status"]
        assert report["input_validation_summary"]["unsafe_upstream_report_directory_count"] == 1

        # 13b) Forbidden private keys inside an allowlisted report must be rejected.
        embedded_forbidden_dir = tmp_path / "embedded_forbidden_dir"
        _write_slice_dir(embedded_forbidden_dir, 0, p62_mod)
        target_report = embedded_forbidden_dir / "p60_rmc_policy_v2_report.json"
        data = _read_json(target_report)
        data["prompt"] = "do not persist"
        _write_json(target_report, data)
        report = _run_p63_pipeline([embedded_forbidden_dir], make_output_paths("embedded_forbidden"), repo_root)
        assert report["status"] in {"invalid_input_artifacts", "blocked_safety"}, report["status"]
        assert report["input_validation_summary"]["unsafe_upstream_report_directory_count"] == 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--slice-root-dir", type=Path, action="append", help="Parent of slice dirs (repeatable; immediate children only).")
    parser.add_argument("--slice-dir", type=Path, action="append", help="Exact slice directory (repeatable).")
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT, help="Internal P62 manifest JSON path.")
    parser.add_argument("--p57-input-matrix-out", type=Path, default=DEFAULT_P57_INPUT_MATRIX_OUT, help="Internal P57 input matrix JSON path.")
    parser.add_argument("--p62-report-out", type=Path, default=DEFAULT_P62_REPORT_OUT, help="Internal P62 report JSON path.")
    parser.add_argument("--p62-doc-out", type=Path, default=DEFAULT_P62_DOC_OUT, help="Internal P62 markdown path.")
    parser.add_argument("--p57-report-out", type=Path, default=DEFAULT_P57_REPORT_OUT, help="Internal P57 report JSON path.")
    parser.add_argument("--p57-doc-out", type=Path, default=DEFAULT_P57_DOC_OUT, help="Internal P57 markdown path.")
    parser.add_argument("--p61-report-out", type=Path, default=DEFAULT_P61_REPORT_OUT, help="Internal P61 report JSON path.")
    parser.add_argument("--p61-doc-out", type=Path, default=DEFAULT_P61_DOC_OUT, help="Internal P61 markdown path.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Public P63 report JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Public P63 markdown path.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = _eval_dir().parent

    if args.self_test:
        _run_self_test_assertions()
        slice_dirs: list[Path] = []
    else:
        slice_dirs = _collect_slice_dirs(args)

    output_paths = {
        "manifest_out": args.manifest_out,
        "p57_matrix_out": args.p57_input_matrix_out,
        "p62_report_out": args.p62_report_out,
        "p62_doc_out": args.p62_doc_out,
        "p57_report_out": args.p57_report_out,
        "p57_doc_out": args.p57_doc_out,
        "p61_report_out": args.p61_report_out,
        "p61_doc_out": args.p61_doc_out,
    }

    report = _run_p63_pipeline(
        slice_dirs,
        output_paths,
        repo_root,
        self_test=args.self_test,
    )

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P63 public report validation failed: {errors}")

    report["validation"]["forbidden_key_scan_ok"] = True
    if args.self_test:
        report["validation"]["self_test_assertions_passed"] = True

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P63 public report written to {args.out}")
    print(f"P63 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
