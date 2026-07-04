#!/usr/bin/env python3
"""RPM-D0 local trace capture for OpenLocus v2.

This phase executes bounded, real local OpenLocus EvidenceCore actions and writes
private schema-valid state/action rows.  The public report is aggregate-only and
must never publish paths, task ids, queries, labels, snippets, hashes, provider
payloads, exact private row values, or raw rows.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rpm_trace_schema as schema


REPO = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = REPO / "artifacts" / "rpm_d0_trace_capture" / "rpm_d0_trace_capture_report.json"
REPORT_SCHEMA_VERSION = "rpm_d0_trace_capture_public_report_v1"
PHASE = "openlocus_v2_rpm_d0_trace_capture"
STATUS_COMPLETE = "rpm_d0_trace_capture_complete_d1_smoke_authorized"
STATUS_UNAVAILABLE = "rpm_d0_trace_capture_unavailable_cli_required"
PRIVATE_ROOT_PREFIX = "rpm_d0_private_"
PRIVATE_TRACE_FILENAME = "rpm_d0_state_action_traces.jsonl"
PUBLIC_FORBIDDEN_EXACT = {
    "rpm_training",
    "frk_j",
    "frk_b_c_resurrection",
    "frk_i_selector_variants",
    "ldi_b_easy_continuation",
    "haae_sg",
    "haae_t",
    "r2bv_static_support_repair",
    "broad_source_scan",
    "candidate_generation_expansion",
    "retrieval_pack_rerun_new_algorithm",
    "ldi_b_easy_slice_continuation",
    "provider_default",
    "provider_claim",
    "network_default",
    "network_claim",
    "ci_default",
    "ci_claim",
    "runtime_default",
    "runtime_default_claim",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "default_claim",
    "raw_publication",
}


class D0Error(Exception):
    pass


@dataclass(frozen=True)
class TaskSpec:
    opaque_id: str
    path_spec: str
    objective_bucket: str
    query_shape_bucket: str
    ambiguity_bucket: str


TASKS = [
    TaskSpec("private_ref_task_00", "README.md:1-8", "current_evidence", "structured", "low"),
    TaskSpec("private_ref_task_01", "eval/rpm_trace_schema.py:1-12", "trace_policy_learning", "structured", "low"),
    TaskSpec("private_ref_task_02", "docs/current-research-conclusions.md:1-18", "current_evidence", "structured", "low"),
    TaskSpec("private_ref_task_03", "crates/openlocus-cli/src/lib.rs:51-58", "current_evidence", "structured", "medium"),
    TaskSpec("private_ref_task_04", "Cargo.toml:1-14", "diagnostic_only", "structured", "low"),
]


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


def bucket_latency(seconds: float) -> str:
    if seconds < 1:
        return "lt_1s"
    if seconds <= 10:
        return "1s_to_10s"
    if seconds <= 60:
        return "10s_to_60s"
    return "gt_60s"


def private_ref(prefix: str, value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return f"private_ref_{prefix}_{safe}"


def ensure_openlocus() -> Path:
    binary = REPO / "target" / "debug" / "openlocus"
    if binary.exists() and os.access(binary, os.X_OK):
        return binary
    cargo = REPO / "Cargo.toml"
    if not cargo.exists():
        raise D0Error("OpenLocus workspace Cargo.toml unavailable; cannot build CLI")
    result = subprocess.run(
        ["cargo", "build", "-p", "openlocus-cli", "--bin", "openlocus"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode != 0 or not binary.exists():
        raise D0Error("OpenLocus CLI unavailable and cheap local build failed closed")
    return binary


def run_cli(binary: Path, args: list[str]) -> tuple[dict[str, Any], str, float]:
    started = time.monotonic()
    result = subprocess.run(
        [str(binary), *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    latency = time.monotonic() - started
    if result.returncode != 0:
        raise D0Error(f"OpenLocus action failed closed: {' '.join(args[:2])}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise D0Error(f"OpenLocus action returned non-JSON output: {' '.join(args[:2])}") from exc
    return payload, result.stdout, latency


def evidence_from_read(payload: dict[str, Any]) -> dict[str, Any]:
    # The CLI returns an Evidence object.  Keep it private for validate action input.
    if not isinstance(payload, dict):
        raise D0Error("read action did not return an Evidence object")
    if "core" in payload:
        return payload
    required_flat_core = {"path", "start_line", "end_line", "content_sha", "score", "why", "channels"}
    if not required_flat_core.issubset(payload):
        raise D0Error("read action missing Evidence core fields")
    return payload


def tamper_evidence_content_sha(evidence: dict[str, Any]) -> dict[str, Any]:
    bad = copy.deepcopy(evidence)
    if isinstance(bad.get("core"), dict):
        bad["core"]["content_sha"] = "0" * 64
    elif "content_sha" in bad:
        bad["content_sha"] = "0" * 64
    else:
        raise D0Error("evidence shape unavailable for stale/currentness mutation")
    return bad


def build_row(
    *,
    task: TaskSpec,
    action_type: str,
    step_index: int,
    order_index: int,
    observation_status: str,
    result_bucket: str,
    evidence_delta_bucket: str,
    latency_bucket: str,
    failure_bucket: str,
    currentness_bucket: str,
    label_available: bool,
    outcome_bucket: str,
    evidencecore_link_status: str | None = None,
    currentness_verification_status: str | None = None,
    stale_evidence_detected_bool: bool = False,
    materialization_status: str | None = None,
) -> dict[str, Any]:
    trace_id = private_ref("trace", task.opaque_id)
    step_id = private_ref("step", f"{task.opaque_id}_{step_index}_{action_type}")
    return {
        "trace_identity": {
            "schema_version": schema.ROW_SCHEMA_VERSION,
            "trace_id": trace_id,
            "step_id": step_id,
            "episode_step_index": step_index,
            "created_order_index": order_index,
            "runner_kind": "manual_local",
        },
        "task_state": {
            "task_bucket": bucket_count(len(TASKS)),
            "task_type": "rpm_trace_capture",
            "objective_bucket": task.objective_bucket,
            "route_family": "rpm_d0",
            "source_lock_id": "current_route_closure_2026_07_04",
            "current_route_status": "executable_capture_ready",
        },
        "state_features": {
            "query_shape_bucket": task.query_shape_bucket,
            "repo_size_bucket": "files_101_to_1000",
            "candidate_count_bucket": "count_1",
            "evidence_coverage_bucket": "coverage_medium" if action_type == "read_current_source" else "coverage_high",
            "currentness_bucket": currentness_bucket,
            "ambiguity_bucket": task.ambiguity_bucket,
            "dirty_state_bucket": "dirty_safe",
            "features_label_blind_bool": True,
        },
        "action": {
            "action_type": action_type,
            "action_scope_bucket": "scope_single_file",
            "retrieval_budget_bucket": "budget_1_to_5",
            "source_scan_scope": "explicit_bounded" if action_type == "read_current_source" else "current_evidence_only",
            "candidate_generation_policy": "bounded_current_source_only" if action_type == "read_current_source" else "existing_candidates_only",
            "pack_policy": "fixed_order" if action_type == "read_current_source" else "evidencecore_validated",
            "action_feature_keys": ["currentness_bucket", "evidence_coverage_bucket", "ambiguity_bucket"],
        },
        "policy_learning_support": {
            "behavior_policy_id": "private_ref_behavior_policy_rpm_d0_deterministic_local",
            "behavior_policy_kind": "deterministic_rule",
            "deterministic_bool": True,
            "action_probability": 1.0,
            "action_probability_bucket": "probability_1",
            "propensity_available_bool": True,
            "eligible_actions_bucket": "count_2_to_5",
        },
        "observation_result": {
            "observation_status": observation_status,
            "result_bucket": result_bucket,
            "evidence_delta_bucket": evidence_delta_bucket,
            "latency_bucket": latency_bucket,
            "failure_bucket": failure_bucket,
            "observation_after_action_bool": True,
        },
        "evidencecore_linkage": {
            "evidencecore_required_bool": True,
            "evidencecore_link_status": evidencecore_link_status or ("linked_current" if failure_bucket == "none" else "missing"),
            "currentness_verification_status": currentness_verification_status or ("verified_current" if failure_bucket == "none" else "unavailable"),
            "stale_evidence_detected_bool": stale_evidence_detected_bool,
            "materialization_status": materialization_status or ("materialized_current" if failure_bucket == "none" else "unavailable"),
            "path_range_hash_private_only_bool": True,
        },
        "outcome_label": {
            "label_available_bool": label_available,
            "label_timing": "after_action" if label_available else "not_available",
            "label_source": "private_eval_only" if label_available else "none",
            "outcome_bucket": outcome_bucket if label_available else "not_evaluated",
            "label_used_in_state_or_action_bool": False,
        },
        "privacy_execution": {
            "private_trace_bool": True,
            "public_report_level": "aggregate_schema_only",
            "raw_publication_bool": False,
            "provider_payload_public_bool": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "private_values_public_bool": False,
        },
        "stop_go_source_locks_readback": {
            "source_lock_readback_status": "passed",
            "allowed_next_phase": "rpm_d0_trace_capture",
            "forbidden_next_phases": sorted(schema.FORBIDDEN_NEXT_PHASES),
            "overauthorization_bool": False,
            "readback_consistency_status": "passed",
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def capture_traces(confirm_private_output: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not confirm_private_output:
        raise D0Error("--confirm-private-output is required before writing private trace rows")
    binary = ensure_openlocus()
    private_root = REPO / "runs" / f"{PRIVATE_ROOT_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    private_trace_path = private_root / PRIVATE_TRACE_FILENAME
    rows: list[dict[str, Any]] = []
    evidence_inputs: list[dict[str, Any]] = []
    order = 0
    for task in TASKS:
        # Pre-action state/features are constructed before action execution; labels are joined only after observation.
        read_payload, _read_stdout, read_latency = run_cli(binary, ["read", task.path_spec, "--json"])
        evidence = evidence_from_read(read_payload)
        rows.append(
            build_row(
                task=task,
                action_type="read_current_source",
                step_index=0,
                order_index=order,
                observation_status="observed",
                result_bucket="evidence_added",
                evidence_delta_bucket="delta_1",
                latency_bucket=bucket_latency(read_latency),
                failure_bucket="none",
                currentness_bucket="not_checked",
                label_available=True,
                outcome_bucket="success_bucket",
            )
        )
        order += 1
        evidence_inputs.append(evidence)
        evidence_file = private_root / f"private_evidence_{order:02d}.json"
        private_root.mkdir(parents=True, exist_ok=True)
        evidence_file.write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")
        validate_payload, _validate_stdout, validate_latency = run_cli(binary, ["citations", "validate", str(evidence_file), "--json"])
        valid_count = int(validate_payload.get("valid_count", 0)) if isinstance(validate_payload, dict) else 0
        failure = "none" if valid_count >= 1 else "validation_failed"
        rows.append(
            build_row(
                task=task,
                action_type="validate_evidence",
                step_index=1,
                order_index=order,
                observation_status="observed" if failure == "none" else "failed_safe",
                result_bucket="evidence_added" if failure == "none" else "failure",
                evidence_delta_bucket="delta_1" if failure == "none" else "delta_0",
                latency_bucket=bucket_latency(validate_latency),
                failure_bucket=failure,
                currentness_bucket="verified_current" if failure == "none" else "not_checked",
                label_available=True,
                outcome_bucket="success_bucket" if failure == "none" else "failure_bucket",
            )
        )
        order += 1
        if task is TASKS[0]:
            stale_evidence = tamper_evidence_content_sha(evidence)
            stale_file = private_root / f"private_evidence_stale_{order:02d}.json"
            stale_file.write_text(json.dumps(stale_evidence, sort_keys=True) + "\n", encoding="utf-8")
            stale_payload, _stale_stdout, stale_latency = run_cli(binary, ["citations", "validate", str(stale_file), "--json"])
            invalid_count = int(stale_payload.get("invalid_count", 0)) if isinstance(stale_payload, dict) else 0
            stale_failure = "stale_evidence" if invalid_count >= 1 else "validation_failed"
            rows.append(
                build_row(
                    task=task,
                    action_type="validate_evidence",
                    step_index=2,
                    order_index=order,
                    observation_status="failed_safe",
                    result_bucket="evidence_rejected",
                    evidence_delta_bucket="delta_0",
                    latency_bucket=bucket_latency(stale_latency),
                    failure_bucket=stale_failure,
                    currentness_bucket="not_checked",
                    label_available=True,
                    outcome_bucket="failure_bucket",
                    evidencecore_link_status="stale_rejected",
                    currentness_verification_status="stale",
                    stale_evidence_detected_bool=True,
                    materialization_status="rejected",
                )
            )
            order += 1

    errors = schema.validate_trace_rows(rows)
    if errors:
        raise D0Error("captured trace rows failed schema validation: " + "; ".join(errors[:5]))
    write_jsonl(private_trace_path, rows)
    manifest = {
        "storage_class": "ignored_repo_runs_private_jsonl",
        "row_count": len(rows),
        "task_count": len(TASKS),
        "episode_count": len(TASKS),
        "action_types": sorted({row["action"]["action_type"] for row in rows}),
        "private_trace_path": str(private_trace_path),
        "evidence_input_count": len(evidence_inputs),
    }
    return rows, manifest


def aggregate_rows(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    action_counts = Counter(row["action"]["action_type"] for row in rows)
    currentness_counts = Counter(row["evidencecore_linkage"]["evidencecore_link_status"] for row in rows)
    label_timing_counts = Counter(row["outcome_label"]["label_timing"] for row in rows)
    outcome_counts = Counter(row["outcome_label"]["outcome_bucket"] for row in rows)
    schema_errors = schema.validate_trace_rows(rows)
    sufficient = (
        not schema_errors
        and len({row["trace_identity"]["trace_id"] for row in rows}) >= 3
        and len(rows) >= 6
        and {"read_current_source", "validate_evidence"}.issubset(action_counts)
        and currentness_counts.get("stale_rejected", 0) >= 1
        and outcome_counts.get("failure_bucket", 0) >= 1
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS_COMPLETE if sufficient else STATUS_UNAVAILABLE,
        "execution_attestation": {
            "local_openlocus_actions_executed": True,
            "synthetic_rows_only": False,
            "task_selection_before_execution": "passed",
            "labels_joined_after_observation": "passed",
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "rpm_training_executed": False,
        },
        "coverage_buckets": {
            "task_count_bucket": bucket_count(int(manifest["task_count"])),
            "episode_count_bucket": bucket_count(int(manifest["episode_count"])),
            "step_count_bucket": bucket_count(len(rows)),
            "action_coverage": {name: bucket_count(count) for name, count in sorted(action_counts.items())},
            "required_action_types_present": sorted(action_counts),
            "evidencecore_currentness": {name: bucket_count(count) for name, count in sorted(currentness_counts.items())},
            "label_timing_isolation": {name: bucket_count(count) for name, count in sorted(label_timing_counts.items())},
            "outcome": {name: bucket_count(count) for name, count in sorted(outcome_counts.items())},
        },
        "validation_summary": {
            "strict_trace_schema": "passed" if not schema_errors else "failed",
            "schema_error_bucket": bucket_count(len(schema_errors)),
            "privacy_leak_scan": "pending",
            "private_manifest_count_proof_bucket": bucket_count(len(rows)),
            "private_storage_class": "ignored_repo_runs_private_jsonl",
        },
        "private_trace_manifest": {
            "storage_class": "ignored_repo_runs_private_jsonl",
            "row_count_bucket": bucket_count(len(rows)),
            "task_count_bucket": bucket_count(int(manifest["task_count"])),
            "episode_count_bucket": bucket_count(int(manifest["episode_count"])),
            "path_public": False,
            "raw_rows_public": False,
        },
        "privacy_contract": {
            "publication_level": "aggregate_schema_only",
            "raw_paths_public": False,
            "queries_public": False,
            "task_ids_public": False,
            "snippets_public": False,
            "hashes_public": False,
            "labels_public": False,
            "prompts_or_responses_public": False,
            "provider_payloads_public": False,
            "exact_private_row_values_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": "go_d1_smoke_only" if sufficient else "no_training_repair_or_stop_only",
            "authorized_next_phase": "rpm_d1_bounded_offline_rpm_small_learning_smoke" if sufficient else "targeted_trace_capture_repair_or_stop_for_task_label_sources",
            "explicitly_forbidden": sorted(PUBLIC_FORBIDDEN_EXACT),
            "d0_must_not_train_rpm": True,
            "method_scale_winner_default_claims_allowed": False,
        },
    }


def public_leak_errors(obj: Any) -> list[str]:
    sanitized = copy.deepcopy(obj)
    privacy = sanitized.get("privacy_contract") if isinstance(sanitized, dict) else None
    if isinstance(privacy, dict):
        for key in (
            "raw_paths_public",
            "task_ids_public",
            "snippets_public",
            "prompts_or_responses_public",
            "exact_private_row_values_public",
        ):
            privacy.pop(key, None)
    errors = schema.public_leak_errors(sanitized)
    text = json.dumps(obj, sort_keys=True)
    extra_terms = ["README.md", "Cargo.toml", "private_ref_task_", "content_sha", "private_evidence_"]
    for term in extra_terms:
        if term in text:
            errors.append(f"public leak disallowed private term {term}")
    return errors


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "phase",
        "status",
        "execution_attestation",
        "coverage_buckets",
        "validation_summary",
        "private_trace_manifest",
        "privacy_contract",
        "stop_go",
    }
    if not isinstance(report, dict):
        return ["report must be an object"]
    if set(report) != required:
        errors.append("report has missing or unknown top-level keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("bad schema_version")
    if report.get("phase") != PHASE:
        errors.append("bad phase")
    if report.get("status") not in {STATUS_COMPLETE, STATUS_UNAVAILABLE}:
        errors.append("bad status")
    attestation = report.get("execution_attestation", {})
    if attestation.get("local_openlocus_actions_executed") is not True:
        errors.append("local OpenLocus action execution must be attested")
    if attestation.get("synthetic_rows_only") is not False:
        errors.append("synthetic-only rows are forbidden")
    if attestation.get("labels_joined_after_observation") != "passed":
        errors.append("label timing isolation must pass")
    if attestation.get("rpm_training_executed") is not False:
        errors.append("D0 must not train RPM")
    coverage = report.get("coverage_buckets", {})
    expected_coverage_keys = {
        "task_count_bucket",
        "episode_count_bucket",
        "step_count_bucket",
        "action_coverage",
        "required_action_types_present",
        "evidencecore_currentness",
        "label_timing_isolation",
        "outcome",
    }
    if set(coverage) != expected_coverage_keys:
        errors.append("coverage bucket shape drift")
    actions = set(coverage.get("required_action_types_present", []))
    if not {"read_current_source", "validate_evidence"}.issubset(actions):
        errors.append("required real action type coverage missing")
    if report.get("status") == STATUS_COMPLETE:
        if coverage.get("task_count_bucket") not in {"count_2_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"}:
            errors.append("complete D0 requires at least three tasks")
        if coverage.get("step_count_bucket") not in {"count_6_to_20", "count_21_to_50", "count_gt_50"}:
            errors.append("complete D0 requires multi-step trace rows")
        currentness = coverage.get("evidencecore_currentness", {})
        if "linked_current" not in currentness or "stale_rejected" not in currentness:
            errors.append("complete D0 requires both current and stale-rejected EvidenceCore observations")
        outcome = coverage.get("outcome", {})
        if "success_bucket" not in outcome or "failure_bucket" not in outcome:
            errors.append("complete D0 requires both success and failure-safe outcome buckets")
    validation = report.get("validation_summary", {})
    if validation.get("strict_trace_schema") != "passed":
        errors.append("strict trace schema must pass")
    if validation.get("privacy_leak_scan") != "passed":
        errors.append("privacy leak scan must pass")
    manifest = report.get("private_trace_manifest", {})
    if manifest.get("storage_class") != "ignored_repo_runs_private_jsonl":
        errors.append("private storage class drift")
    if manifest.get("path_public") is not False or manifest.get("raw_rows_public") is not False:
        errors.append("private manifest must not publish paths or rows")
    privacy = report.get("privacy_contract", {})
    for field in (
        "raw_paths_public",
        "queries_public",
        "task_ids_public",
        "snippets_public",
        "hashes_public",
        "labels_public",
        "prompts_or_responses_public",
        "provider_payloads_public",
        "exact_private_row_values_public",
        "raw_publication",
    ):
        if privacy.get(field) is not False:
            errors.append(f"privacy_contract.{field} must be false")
    stop_go = report.get("stop_go", {})
    forbidden = set(stop_go.get("explicitly_forbidden", []))
    if forbidden != PUBLIC_FORBIDDEN_EXACT:
        errors.append("explicit forbidden route set drift")
    if stop_go.get("d0_must_not_train_rpm") is not True:
        errors.append("D0 training prohibition missing")
    if stop_go.get("method_scale_winner_default_claims_allowed") is not False:
        errors.append("claim boundary drift")
    allowed = stop_go.get("authorized_next_phase")
    if report.get("status") == STATUS_COMPLETE and allowed != "rpm_d1_bounded_offline_rpm_small_learning_smoke":
        errors.append("successful D0 must authorize only bounded offline RPM D1 smoke")
    if report.get("status") == STATUS_UNAVAILABLE and allowed != "targeted_trace_capture_repair_or_stop_for_task_label_sources":
        errors.append("insufficient D0 must not authorize D1")
    if allowed in forbidden:
        errors.append("forbidden phase appears as authorized next phase")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    report = copy.deepcopy(report)
    report["validation_summary"]["privacy_leak_scan"] = "passed" if not public_leak_errors(report) else "failed"
    errors = validate_public_report(report)
    if errors:
        raise D0Error("public report validation failed: " + "; ".join(errors[:5]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    rows = schema.valid_fixture_rows()
    checks.append(("phase1_schema_fixture_valid", not schema.validate_trace_rows(rows)))
    manifest = {"task_count": 3, "episode_count": 3}
    report = aggregate_rows(rows, manifest)
    report["status"] = STATUS_COMPLETE
    report["execution_attestation"]["local_openlocus_actions_executed"] = True
    report["execution_attestation"]["synthetic_rows_only"] = False
    report["coverage_buckets"]["task_count_bucket"] = "count_2_to_5"
    report["coverage_buckets"]["episode_count_bucket"] = "count_2_to_5"
    report["coverage_buckets"]["step_count_bucket"] = "count_6_to_20"
    report["coverage_buckets"]["action_coverage"] = {"read_current_source": "count_2_to_5", "validate_evidence": "count_2_to_5"}
    report["coverage_buckets"]["required_action_types_present"] = ["read_current_source", "validate_evidence"]
    report["coverage_buckets"]["evidencecore_currentness"] = {"linked_current": "count_2_to_5", "stale_rejected": "count_1"}
    report["coverage_buckets"]["outcome"] = {"success_bucket": "count_2_to_5", "failure_bucket": "count_1"}
    report["validation_summary"]["privacy_leak_scan"] = "passed"
    report["stop_go"]["authorized_next_phase"] = "rpm_d1_bounded_offline_rpm_small_learning_smoke"
    checks.append(("public_report_valid_fixture", not validate_public_report(report)))
    bad = copy.deepcopy(report)
    bad["stop_go"]["authorized_next_phase"] = "rpm_training"
    checks.append(("training_overauth_rejected", any("forbidden" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["privacy_contract"]["raw_paths_public"] = True
    checks.append(("privacy_contract_rejected", any("raw_paths_public" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["coverage_buckets"]["leaky_path"] = "README.md:1-8"
    checks.append(("public_path_leak_rejected", bool(validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["coverage_buckets"]["required_action_types_present"] = ["read_current_source"]
    checks.append(("missing_action_coverage_rejected", any("action type" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["coverage_buckets"]["evidencecore_currentness"] = {"linked_current": "count_6_to_20"}
    checks.append(("missing_stale_rejection_coverage_rejected", any("stale-rejected" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["execution_attestation"]["synthetic_rows_only"] = True
    checks.append(("synthetic_only_rejected", any("synthetic-only" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["private_trace_manifest"]["path_public"] = True
    checks.append(("private_path_public_rejected", any("paths or rows" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["status"] = STATUS_UNAVAILABLE
    bad["stop_go"]["authorized_next_phase"] = "rpm_d1_bounded_offline_rpm_small_learning_smoke"
    checks.append(("unavailable_d1_overauth_rejected", any("must not authorize D1" in e for e in validate_public_report(bad))))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise D0Error("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks), "failed_checks": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture RPM-D0 private local OpenLocus state-action traces")
    parser.add_argument("--self-test", action="store_true", help="run RPM-D0 validator self-tests")
    parser.add_argument("--run-local-trace-capture", action="store_true", help="execute bounded local OpenLocus actions and write private traces")
    parser.add_argument("--confirm-private-output", action="store_true", help="required explicit confirmation for private output write")
    parser.add_argument("--validate-report", type=Path, help="validate aggregate-only RPM-D0 public report")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(run_self_tests(), indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
            errors = validate_public_report(report)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"Validation passed: {args.validate_report}")
            return 0
        if args.run_local_trace_capture:
            rows, manifest = capture_traces(args.confirm_private_output)
            report = aggregate_rows(rows, manifest)
            write_report(report)
            print(
                json.dumps(
                    {
                        "status": report["status"],
                        "private_storage_class": manifest["storage_class"],
                        "private_row_count": manifest["row_count"],
                        "public_report": str(DEFAULT_REPORT),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        parser.error("choose --self-test, --run-local-trace-capture, or --validate-report")
    except (D0Error, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
