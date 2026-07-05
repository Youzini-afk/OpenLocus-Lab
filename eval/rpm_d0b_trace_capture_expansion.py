#!/usr/bin/env python3
"""RPM-D0B trace capture expansion for OpenLocus v2.

This executable phase expands the private RPM trace set after RPM-D1 found the
original D0 rows insufficiently diverse. It executes only fixed, predeclared,
bounded local OpenLocus CLI actions; writes private JSONL rows only under
ignored runs storage after explicit confirmation; validates every row with the
Phase 1 schema; and publishes an aggregate-only public report.
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
DEFAULT_REPORT = REPO / "artifacts" / "rpm_d0b_trace_capture_expansion" / "rpm_d0b_trace_capture_expansion_report.json"
REPORT_SCHEMA_VERSION = "rpm_d0b_trace_capture_expansion_public_report_v1"
PHASE = "openlocus_v2_rpm_d0b_trace_capture_expansion"
STATUS_COMPLETE = "rpm_d0b_trace_capture_expansion_complete_d1_rerun_authorized"
STATUS_REPAIR = "rpm_d0b_trace_capture_expansion_incomplete_targeted_repair_only"
PRIVATE_ROOT_PREFIX = "rpm_d0b_private_"
PRIVATE_TRACE_FILENAME = "rpm_d0b_state_action_traces.jsonl"

AUTHORIZED_D1_RERUN = "rpm_d1_bounded_offline_rpm_small_learning_smoke_rerun"
AUTHORIZED_REPAIR = "targeted_d0b_repair_only"
REQUIRED_ACTION_TYPES = {"bounded_retrieval", "read_current_source", "validate_evidence"}
PUBLIC_FORBIDDEN_EXACT = {
    "rpm_training",
    "d2_model_scaling",
    "rpm_d2_model_scaling",
    "runtime_default",
    "runtime_default_claim",
    "provider_default",
    "provider_claim",
    "network_default",
    "network_claim",
    "ci_default",
    "ci_claim",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "default_claim",
    "raw_publication",
    "broad_source_scan",
    "candidate_generation_expansion",
    "retrieval_pack_rerun_new_algorithm",
    "frk_j",
    "frk_b_c_resurrection",
    "frk_i_selector_variants",
    "ldi_b_easy_continuation",
    "haae_sg",
    "haae_t",
    "r2bv_static_support_repair",
}


class D0BError(Exception):
    pass


@dataclass(frozen=True)
class EpisodeSpec:
    opaque_id: str
    path_spec: str
    retrieval_command: tuple[str, str]
    retrieval_expectation: str
    validation_mode: str
    objective_bucket: str
    query_shape_bucket: str
    ambiguity_bucket: str


# Fixed bounded tasks/actions. Labels, outcomes, and currentness results are not
# known to row features until after each action returns.
EPISODES = [
    EpisodeSpec("episode_00", "README.md:1-8", ("text", "EvidenceCore"), "hit", "current", "current_evidence", "short", "low"),
    EpisodeSpec("episode_01", "eval/rpm_trace_schema.py:1-12", ("text", "ROW_SCHEMA_VERSION"), "hit", "current", "trace_policy_learning", "structured", "low"),
    EpisodeSpec("episode_02", "docs/current-research-conclusions.md:1-18", ("text", "RPM-D1"), "hit", "current", "trace_policy_learning", "short", "medium"),
    EpisodeSpec("episode_03", "crates/openlocus-cli/src/lib.rs:1-20", ("regex", "openlocus"), "hit", "current", "current_evidence", "structured", "medium"),
    EpisodeSpec("episode_04", "Cargo.toml:1-14", ("text", "workspace"), "hit", "current", "diagnostic_only", "short", "low"),
    EpisodeSpec("episode_05", "docs/en/research-summary.md:1-16", ("text", "OpenLocus"), "hit", "current", "trace_policy_learning", "short", "low"),
    # Negative/control rows intentionally reuse ordinary pre-action buckets.  The
    # failure mechanism must live in post-action observation/linkage, not in an
    # easy query-shape or ambiguity shortcut.
    EpisodeSpec("episode_06", "docs/zh/research-summary.md:1-16", ("text", "private_ref_d0b_nohit_alpha_000"), "no_hit", "stale", "trace_policy_learning", "short", "low"),
    EpisodeSpec("episode_07", "docs/en/research-log.md:1-12", ("text", "private_ref_d0b_nohit_beta_111"), "no_hit", "stale", "current_evidence", "structured", "medium"),
    EpisodeSpec("episode_08", "docs/zh/research-log.md:1-12", ("text", "private_ref_d0b_nohit_gamma_222"), "no_hit", "stale", "trace_policy_learning", "short", "low"),
    EpisodeSpec("episode_09", "docs/en/openlocus-v2-rpm-d0-trace-capture.md:1-16", ("regex", "private_ref_d0b_nohit_delta_333"), "no_hit", "stale", "diagnostic_only", "structured", "medium"),
    EpisodeSpec("episode_10", "docs/zh/openlocus-v2-rpm-d0-trace-capture.md:1-16", ("text", "private_ref_d0b_nohit_epsilon_444"), "no_hit", "stale", "current_evidence", "short", "low"),
    EpisodeSpec("episode_11", "docs/en/openlocus-v2-rpm-d1-learning-smoke.md:1-16", ("regex", "private_ref_d0b_nohit_zeta_555"), "no_hit", "stale", "trace_policy_learning", "structured", "medium"),
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
    if not (REPO / "Cargo.toml").exists():
        raise D0BError("OpenLocus workspace Cargo.toml unavailable; cannot build CLI")
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
        raise D0BError("OpenLocus CLI unavailable and cheap local build failed closed")
    return binary


def run_cli(binary: Path, args: list[str], *, fail_safe: bool = False) -> tuple[Any | None, int, float]:
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
        if fail_safe:
            return None, result.returncode, latency
        raise D0BError(f"OpenLocus action failed closed: {' '.join(args[:2])}")
    try:
        return json.loads(result.stdout), result.returncode, latency
    except json.JSONDecodeError as exc:
        if fail_safe:
            return None, result.returncode, latency
        raise D0BError(f"OpenLocus action returned non-JSON output: {' '.join(args[:2])}") from exc


def evidence_from_read(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise D0BError("read action did not return an Evidence object")
    if "core" in payload:
        return payload
    required_flat_core = {"path", "start_line", "end_line", "content_sha", "score", "why", "channels"}
    if not required_flat_core.issubset(payload):
        raise D0BError("read action missing Evidence core fields")
    return payload


def tamper_evidence_content_sha(evidence: dict[str, Any]) -> dict[str, Any]:
    bad = copy.deepcopy(evidence)
    if isinstance(bad.get("core"), dict):
        bad["core"]["content_sha"] = "0" * 64
    elif "content_sha" in bad:
        bad["content_sha"] = "0" * 64
    else:
        raise D0BError("evidence shape unavailable for stale/currentness mutation")
    return bad


def search_hit_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("results", "evidence", "items", "hits"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


def evidence_linkage(*, required: bool, stale: bool = False, unsafe: bool = False) -> dict[str, Any]:
    if not required:
        return {
            "evidencecore_required_bool": False,
            "evidencecore_link_status": "not_required",
            "currentness_verification_status": "not_required",
            "stale_evidence_detected_bool": False,
            "materialization_status": "not_required",
            "path_range_hash_private_only_bool": True,
        }
    if stale:
        return {
            "evidencecore_required_bool": True,
            "evidencecore_link_status": "stale_rejected",
            "currentness_verification_status": "stale",
            "stale_evidence_detected_bool": True,
            "materialization_status": "rejected",
            "path_range_hash_private_only_bool": True,
        }
    if unsafe:
        return {
            "evidencecore_required_bool": True,
            "evidencecore_link_status": "unsafe_rejected",
            "currentness_verification_status": "unsafe",
            "stale_evidence_detected_bool": True,
            "materialization_status": "rejected",
            "path_range_hash_private_only_bool": True,
        }
    return {
        "evidencecore_required_bool": True,
        "evidencecore_link_status": "linked_current",
        "currentness_verification_status": "verified_current",
        "stale_evidence_detected_bool": False,
        "materialization_status": "materialized_current",
        "path_range_hash_private_only_bool": True,
    }


def build_row(
    *,
    episode: EpisodeSpec,
    action_type: str,
    step_index: int,
    order_index: int,
    observation_status: str,
    result_bucket: str,
    evidence_delta_bucket: str,
    latency_bucket: str,
    failure_bucket: str,
    pre_action_currentness_bucket: str,
    label_available: bool,
    outcome_bucket: str,
    evidencecore_required: bool = True,
    stale_evidence: bool = False,
) -> dict[str, Any]:
    trace_id = private_ref("trace", episode.opaque_id)
    step_id = private_ref("step", f"{episode.opaque_id}_{step_index}_{action_type}")
    if action_type == "bounded_retrieval":
        action_scope = "scope_small_bounded"
        source_scan_scope = "explicit_bounded"
        candidate_policy = "bounded_current_source_only"
        pack_policy = "fixed_order"
        candidate_count = "count_0"
        coverage = "coverage_none"
    elif action_type == "read_current_source":
        action_scope = "scope_single_file"
        source_scan_scope = "explicit_bounded"
        candidate_policy = "bounded_current_source_only"
        pack_policy = "fixed_order"
        candidate_count = "count_1"
        coverage = "coverage_low"
    else:
        action_scope = "scope_single_file"
        source_scan_scope = "current_evidence_only"
        candidate_policy = "existing_candidates_only"
        pack_policy = "evidencecore_validated"
        candidate_count = "count_1"
        coverage = "coverage_medium"

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
            "task_bucket": bucket_count(len(EPISODES)),
            "task_type": "rpm_trace_capture",
            "objective_bucket": episode.objective_bucket,
            "route_family": "rpm_d0",
            "source_lock_id": "current_route_closure_2026_07_04",
            "current_route_status": "executable_capture_ready",
        },
        "state_features": {
            "query_shape_bucket": episode.query_shape_bucket,
            "repo_size_bucket": "files_101_to_1000",
            "candidate_count_bucket": candidate_count,
            "evidence_coverage_bucket": coverage,
            "currentness_bucket": pre_action_currentness_bucket,
            "ambiguity_bucket": episode.ambiguity_bucket,
            "dirty_state_bucket": "dirty_safe",
            "features_label_blind_bool": True,
        },
        "action": {
            "action_type": action_type,
            "action_scope_bucket": action_scope,
            "retrieval_budget_bucket": "budget_1_to_5",
            "source_scan_scope": source_scan_scope,
            "candidate_generation_policy": candidate_policy,
            "pack_policy": pack_policy,
            "action_feature_keys": ["currentness_bucket", "evidence_coverage_bucket", "ambiguity_bucket"],
        },
        "policy_learning_support": {
            "behavior_policy_id": "private_ref_behavior_policy_rpm_d0b_deterministic_local",
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
        "evidencecore_linkage": evidence_linkage(required=evidencecore_required, stale=stale_evidence),
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


def capture_traces(confirm_private_output: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not confirm_private_output:
        raise D0BError("--confirm-private-output is required before writing private trace rows")
    if len(EPISODES) != 12:
        raise D0BError("D0B task predeclaration drift: expected exactly 12 episodes")
    binary = ensure_openlocus()
    private_root = REPO / "runs" / f"{PRIVATE_ROOT_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    private_trace_path = private_root / PRIVATE_TRACE_FILENAME
    rows: list[dict[str, Any]] = []
    evidence_inputs = 0
    cli_action_counts: Counter[str] = Counter()
    order = 0

    for episode in EPISODES:
        search_kind, search_value = episode.retrieval_command
        retrieval_payload, retrieval_rc, retrieval_latency = run_cli(
            binary,
            ["search", search_kind, search_value, "--json"],
            fail_safe=True,
        )
        cli_action_counts["bounded_retrieval"] += 1
        hits = search_hit_count(retrieval_payload) if retrieval_rc == 0 else 0
        retrieval_success = retrieval_rc == 0 and hits > 0 and episode.retrieval_expectation == "hit"
        retrieval_failure = "none" if retrieval_success else "missing_source"
        rows.append(
            build_row(
                episode=episode,
                action_type="bounded_retrieval",
                step_index=0,
                order_index=order,
                observation_status="observed" if retrieval_success else "failed_safe",
                result_bucket="evidence_added" if retrieval_success else "no_change",
                evidence_delta_bucket="delta_1" if retrieval_success else "delta_0",
                latency_bucket=bucket_latency(retrieval_latency),
                failure_bucket=retrieval_failure,
                pre_action_currentness_bucket="not_checked",
                label_available=True,
                outcome_bucket="success_bucket" if retrieval_success else "failure_bucket",
                evidencecore_required=retrieval_success,
            )
        )
        order += 1

        read_payload, _read_rc, read_latency = run_cli(binary, ["read", episode.path_spec, "--json"])
        cli_action_counts["read_current_source"] += 1
        evidence = evidence_from_read(read_payload)
        rows.append(
            build_row(
                episode=episode,
                action_type="read_current_source",
                step_index=1,
                order_index=order,
                observation_status="observed",
                result_bucket="evidence_added",
                evidence_delta_bucket="delta_1",
                latency_bucket=bucket_latency(read_latency),
                failure_bucket="none",
                pre_action_currentness_bucket="not_checked",
                label_available=True,
                outcome_bucket="success_bucket",
                evidencecore_required=True,
            )
        )
        order += 1

        private_root.mkdir(parents=True, exist_ok=True)
        evidence_to_validate = tamper_evidence_content_sha(evidence) if episode.validation_mode == "stale" else evidence
        evidence_file = private_root / f"private_evidence_{order:02d}.json"
        evidence_file.write_text(json.dumps(evidence_to_validate, sort_keys=True) + "\n", encoding="utf-8")
        evidence_inputs += 1
        validate_payload, _validate_rc, validate_latency = run_cli(binary, ["citations", "validate", str(evidence_file), "--json"])
        cli_action_counts["validate_evidence"] += 1
        valid_count = int(validate_payload.get("valid_count", 0)) if isinstance(validate_payload, dict) else 0
        invalid_count = int(validate_payload.get("invalid_count", 0)) if isinstance(validate_payload, dict) else 0
        validate_success = episode.validation_mode == "current" and valid_count >= 1
        stale_rejected = episode.validation_mode == "stale" and invalid_count >= 1
        rows.append(
            build_row(
                episode=episode,
                action_type="validate_evidence",
                step_index=2,
                order_index=order,
                observation_status="observed" if validate_success else "failed_safe",
                result_bucket="evidence_added" if validate_success else "evidence_rejected",
                evidence_delta_bucket="delta_1" if validate_success else "delta_0",
                latency_bucket=bucket_latency(validate_latency),
                failure_bucket="none" if validate_success else ("stale_evidence" if stale_rejected else "validation_failed"),
                pre_action_currentness_bucket="not_checked",
                label_available=True,
                outcome_bucket="success_bucket" if validate_success else "failure_bucket",
                evidencecore_required=True,
                stale_evidence=not validate_success,
            )
        )
        order += 1

    errors = schema.validate_trace_rows(rows)
    if errors:
        raise D0BError("captured trace rows failed schema validation: " + "; ".join(errors[:5]))
    write_jsonl(private_trace_path, rows)
    manifest = {
        "storage_class": "ignored_repo_runs_private_jsonl",
        "row_count": len(rows),
        "episode_count": len({row["trace_identity"]["trace_id"] for row in rows}),
        "task_count": len(EPISODES),
        "action_types": sorted({row["action"]["action_type"] for row in rows}),
        "private_trace_path": str(private_trace_path),
        "evidence_input_count": evidence_inputs,
        "cli_action_counts": dict(cli_action_counts),
    }
    return rows, manifest


def diversity_gates(rows: list[dict[str, Any]]) -> dict[str, bool]:
    action_types = {row["action"]["action_type"] for row in rows}
    episodes = {row["trace_identity"]["trace_id"] for row in rows}
    outcome_counts = Counter(row["outcome_label"]["outcome_bucket"] for row in rows)
    currentness_counts = Counter(row["evidencecore_linkage"]["evidencecore_link_status"] for row in rows)
    state_currentness = Counter(row["state_features"]["currentness_bucket"] for row in rows)
    schema_errors = schema.validate_trace_rows(rows)
    return {
        "strict_phase1_schema_passed": not schema_errors,
        "row_count_ge_30": len(rows) >= 30,
        "episode_count_ge_10": len(episodes) >= 10,
        "action_type_count_ge_3": len(action_types) >= 3,
        "required_action_types_present": REQUIRED_ACTION_TYPES.issubset(action_types),
        "success_bucket_rows_ge_5": outcome_counts.get("success_bucket", 0) >= 5,
        "failure_bucket_rows_ge_5": outcome_counts.get("failure_bucket", 0) >= 5,
        "stale_currentness_negative_controls_present": currentness_counts.get("stale_rejected", 0) >= 1 and state_currentness.get("not_checked", 0) >= 1,
        "retrieval_failure_safe_rows_present": any(row["action"]["action_type"] == "bounded_retrieval" and row["outcome_label"]["outcome_bucket"] == "failure_bucket" for row in rows),
        "labels_after_action_only": all(row["outcome_label"]["label_timing"] == "after_action" and row["outcome_label"]["label_used_in_state_or_action_bool"] is False for row in rows),
    }


def aggregate_rows(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    action_counts = Counter(row["action"]["action_type"] for row in rows)
    outcome_counts = Counter(row["outcome_label"]["outcome_bucket"] for row in rows)
    observation_counts = Counter(row["observation_result"]["observation_status"] for row in rows)
    failure_counts = Counter(row["observation_result"]["failure_bucket"] for row in rows)
    link_counts = Counter(row["evidencecore_linkage"]["evidencecore_link_status"] for row in rows)
    currentness_counts = Counter(row["state_features"]["currentness_bucket"] for row in rows)
    label_timing_counts = Counter(row["outcome_label"]["label_timing"] for row in rows)
    schema_errors = schema.validate_trace_rows(rows)
    gates = diversity_gates(rows)
    sufficient = all(gates.values())
    authorized = AUTHORIZED_D1_RERUN if sufficient else AUTHORIZED_REPAIR
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": STATUS_COMPLETE if sufficient else STATUS_REPAIR,
        "execution_attestation": {
            "local_openlocus_actions_executed": True,
            "real_cli_actions_only": True,
            "synthetic_rows_only": False,
            "fixed_bounded_tasks_predeclared": True,
            "labels_joined_after_action": True,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "rpm_training_executed": False,
            "d1_rerun_executed_by_d0b": False,
        },
        "aggregate_buckets": {
            "row_count_bucket": bucket_count(len(rows)),
            "episode_count_bucket": bucket_count(int(manifest["episode_count"])),
            "action_type_count_bucket": bucket_count(len(action_counts)),
            "action_coverage": {name: bucket_count(count) for name, count in sorted(action_counts.items())},
            "required_action_types_present": sorted(action_counts),
            "outcome": {name: bucket_count(count) for name, count in sorted(outcome_counts.items())},
            "observation_status": {name: bucket_count(count) for name, count in sorted(observation_counts.items())},
            "failure": {name: bucket_count(count) for name, count in sorted(failure_counts.items())},
            "evidencecore_linkage_currentness": {name: bucket_count(count) for name, count in sorted(link_counts.items())},
            "pre_action_currentness": {name: bucket_count(count) for name, count in sorted(currentness_counts.items())},
            "label_timing_isolation": {name: bucket_count(count) for name, count in sorted(label_timing_counts.items())},
        },
        "validation_summary": {
            "strict_trace_schema": "passed" if not schema_errors else "failed",
            "schema_error_bucket": bucket_count(len(schema_errors)),
            "privacy_leak_scan": "pending",
            "private_manifest_count_proof_bucket": bucket_count(len(rows)),
            "private_storage_class": "ignored_repo_runs_private_jsonl",
        },
        "diversity_gates": {
            "gate_results": gates,
            "diversity_status": "passed" if sufficient else "targeted_repair_required",
            "target_shape": "episodes_12_rows_36_action_types_3_aggregate_only",
        },
        "private_trace_manifest": {
            "storage_class": "ignored_repo_runs_private_jsonl",
            "row_count_bucket": bucket_count(len(rows)),
            "episode_count_bucket": bucket_count(int(manifest["episode_count"])),
            "action_type_count_bucket": bucket_count(len(action_counts)),
            "path_public": False,
            "raw_rows_public": False,
            "private_refs_public": False,
        },
        "privacy_contract": {
            "publication_level": "aggregate_schema_only",
            "raw_paths_public": False,
            "queries_public": False,
            "patterns_public": False,
            "task_ids_public": False,
            "snippets_public": False,
            "hashes_public": False,
            "labels_public": False,
            "prompts_or_responses_public": False,
            "provider_payloads_public": False,
            "private_trace_path_public": False,
            "evidence_filenames_public": False,
            "exact_private_row_values_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": "go_d1_rerun_only" if sufficient else "no_go_targeted_d0b_repair_only",
            "authorized_next_phase": authorized,
            "explicitly_forbidden": sorted(PUBLIC_FORBIDDEN_EXACT),
            "d2_or_model_scaling_authorized": False,
            "runtime_or_default_authorized": False,
            "training_or_provider_or_network_or_ci_authorized": False,
            "method_scale_winner_default_claims_allowed": False,
            "raw_or_broad_source_scan_or_candidate_expansion_authorized": False,
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
            "private_trace_path_public",
            "evidence_filenames_public",
        ):
            privacy.pop(key, None)
    errors = schema.public_leak_errors(sanitized)
    text = json.dumps(obj, sort_keys=True)
    extra_terms = [
        "README.md",
        "Cargo.toml",
        "private_ref_",
        "content_sha",
        "rpm_d0b_private_",
        "rpm_d0b_state_action_traces.jsonl",
        "EvidenceCore",
        "ROW_SCHEMA_VERSION",
    ]
    for term in extra_terms:
        if term in text:
            errors.append(f"public leak disallowed private term {term}")
    return errors


REPORT_TOP_LEVEL_KEYS = {
    "schema_version",
    "phase",
    "status",
    "execution_attestation",
    "aggregate_buckets",
    "validation_summary",
    "diversity_gates",
    "private_trace_manifest",
    "privacy_contract",
    "stop_go",
}


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    if set(report) != REPORT_TOP_LEVEL_KEYS:
        errors.append("report has missing or unknown top-level keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("bad schema_version")
    if report.get("phase") != PHASE:
        errors.append("bad phase")
    if report.get("status") not in {STATUS_COMPLETE, STATUS_REPAIR}:
        errors.append("bad status")
    attestation = report.get("execution_attestation", {})
    for field in ("local_openlocus_actions_executed", "real_cli_actions_only", "fixed_bounded_tasks_predeclared", "labels_joined_after_action"):
        if attestation.get(field) is not True:
            errors.append(f"execution_attestation.{field} must be true")
    if attestation.get("synthetic_rows_only") is not False or attestation.get("rpm_training_executed") is not False:
        errors.append("D0B must execute real trace capture without RPM training")
    if attestation.get("network_access") != "no_network" or attestation.get("ci_execution") != "local_manual_only":
        errors.append("D0B execution must remain local/no-network/non-CI")
    aggregate = report.get("aggregate_buckets", {})
    expected_aggregate = {
        "row_count_bucket",
        "episode_count_bucket",
        "action_type_count_bucket",
        "action_coverage",
        "required_action_types_present",
        "outcome",
        "observation_status",
        "failure",
        "evidencecore_linkage_currentness",
        "pre_action_currentness",
        "label_timing_isolation",
    }
    if set(aggregate) != expected_aggregate:
        errors.append("aggregate bucket shape drift")
    actions = set(aggregate.get("required_action_types_present", []))
    if not REQUIRED_ACTION_TYPES.issubset(actions):
        errors.append("required D0B action coverage missing")
    if aggregate.get("pre_action_currentness") != {"not_checked": "count_21_to_50"}:
        errors.append("pre-action currentness must not contain post-action validation results")
    if report.get("status") == STATUS_COMPLETE:
        if aggregate.get("row_count_bucket") != "count_21_to_50":
            errors.append("complete D0B report requires row_count_bucket count_21_to_50")
        if aggregate.get("episode_count_bucket") != "count_6_to_20":
            errors.append("complete D0B report requires episode_count_bucket count_6_to_20")
        for action in REQUIRED_ACTION_TYPES:
            if aggregate.get("action_coverage", {}).get(action) != "count_6_to_20":
                errors.append(f"complete D0B report requires action coverage for {action}")
        if aggregate.get("outcome", {}).get("success_bucket") not in {"count_6_to_20", "count_21_to_50", "count_gt_50"}:
            errors.append("complete D0B report requires success_bucket coverage")
        if aggregate.get("outcome", {}).get("failure_bucket") not in {"count_6_to_20", "count_21_to_50", "count_gt_50"}:
            errors.append("complete D0B report requires failure_bucket coverage")
        if aggregate.get("evidencecore_linkage_currentness", {}).get("stale_rejected") != "count_6_to_20":
            errors.append("complete D0B report requires stale_rejected currentness controls")
    validation = report.get("validation_summary", {})
    if validation.get("strict_trace_schema") != "passed" or validation.get("schema_error_bucket") != "count_0":
        errors.append("strict trace schema must pass")
    if validation.get("privacy_leak_scan") != "passed":
        errors.append("privacy leak scan must pass")
    gates = report.get("diversity_gates", {}).get("gate_results", {})
    required_gates = {
        "strict_phase1_schema_passed",
        "row_count_ge_30",
        "episode_count_ge_10",
        "action_type_count_ge_3",
        "required_action_types_present",
        "success_bucket_rows_ge_5",
        "failure_bucket_rows_ge_5",
        "stale_currentness_negative_controls_present",
        "retrieval_failure_safe_rows_present",
        "labels_after_action_only",
    }
    if set(gates) != required_gates or not all(isinstance(gates.get(key), bool) for key in required_gates):
        errors.append("diversity gate readback shape drift")
    sufficient = all(gates.get(key) is True for key in required_gates)
    if report.get("status") == STATUS_COMPLETE and not sufficient:
        errors.append("complete status requires all D0B gates passed")
    if report.get("status") == STATUS_REPAIR and sufficient:
        errors.append("repair status inconsistent with passed gates")
    manifest = report.get("private_trace_manifest", {})
    if manifest.get("storage_class") != "ignored_repo_runs_private_jsonl":
        errors.append("private storage class drift")
    for field in ("path_public", "raw_rows_public", "private_refs_public"):
        if manifest.get(field) is not False:
            errors.append(f"private_trace_manifest.{field} must be false")
    privacy = report.get("privacy_contract", {})
    for field in (
        "raw_paths_public",
        "queries_public",
        "patterns_public",
        "task_ids_public",
        "snippets_public",
        "hashes_public",
        "labels_public",
        "prompts_or_responses_public",
        "provider_payloads_public",
        "private_trace_path_public",
        "evidence_filenames_public",
        "exact_private_row_values_public",
        "raw_publication",
    ):
        if privacy.get(field) is not False:
            errors.append(f"privacy_contract.{field} must be false")
    stop_go = report.get("stop_go", {})
    forbidden = set(stop_go.get("explicitly_forbidden", []))
    if forbidden != PUBLIC_FORBIDDEN_EXACT:
        errors.append("explicit forbidden route set drift")
    allowed = stop_go.get("authorized_next_phase")
    expected_allowed = AUTHORIZED_D1_RERUN if report.get("status") == STATUS_COMPLETE else AUTHORIZED_REPAIR
    if allowed != expected_allowed:
        errors.append("authorized next phase drift")
    if allowed in forbidden:
        errors.append("forbidden phase appears as authorized next phase")
    for field in (
        "d2_or_model_scaling_authorized",
        "runtime_or_default_authorized",
        "training_or_provider_or_network_or_ci_authorized",
        "method_scale_winner_default_claims_allowed",
        "raw_or_broad_source_scan_or_candidate_expansion_authorized",
    ):
        if stop_go.get(field) is not False:
            errors.append(f"stop_go.{field} must be false")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    report = copy.deepcopy(report)
    report["validation_summary"]["privacy_leak_scan"] = "passed" if not public_leak_errors(report) else "failed"
    errors = validate_public_report(report)
    if errors:
        raise D0BError("public report validation failed: " + "; ".join(errors[:6]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    rows = schema.valid_fixture_rows()
    checks.append(("phase1_schema_fixture_valid", not schema.validate_trace_rows(rows)))
    d0b_rows: list[dict[str, Any]] = []
    order = 0
    for episode in EPISODES[:10]:
        d0b_rows.append(build_row(episode=episode, action_type="bounded_retrieval", step_index=0, order_index=order, observation_status="observed", result_bucket="evidence_added", evidence_delta_bucket="delta_1", latency_bucket="lt_1s", failure_bucket="none", pre_action_currentness_bucket="not_checked", label_available=True, outcome_bucket="success_bucket", evidencecore_required=True))
        order += 1
        d0b_rows.append(build_row(episode=episode, action_type="read_current_source", step_index=1, order_index=order, observation_status="observed", result_bucket="evidence_added", evidence_delta_bucket="delta_1", latency_bucket="lt_1s", failure_bucket="none", pre_action_currentness_bucket="not_checked", label_available=True, outcome_bucket="success_bucket", evidencecore_required=True))
        order += 1
        stale = episode.opaque_id.endswith(("6", "7", "8", "9"))
        d0b_rows.append(build_row(episode=episode, action_type="validate_evidence", step_index=2, order_index=order, observation_status="failed_safe" if stale else "observed", result_bucket="evidence_rejected" if stale else "evidence_added", evidence_delta_bucket="delta_0" if stale else "delta_1", latency_bucket="lt_1s", failure_bucket="stale_evidence" if stale else "none", pre_action_currentness_bucket="not_checked", label_available=True, outcome_bucket="failure_bucket" if stale else "success_bucket", evidencecore_required=True, stale_evidence=stale))
        order += 1
    for episode in EPISODES[10:12]:
        d0b_rows.append(build_row(episode=episode, action_type="bounded_retrieval", step_index=0, order_index=order, observation_status="failed_safe", result_bucket="no_change", evidence_delta_bucket="delta_0", latency_bucket="lt_1s", failure_bucket="missing_source", pre_action_currentness_bucket="not_checked", label_available=True, outcome_bucket="failure_bucket", evidencecore_required=False))
        order += 1
        d0b_rows.append(build_row(episode=episode, action_type="read_current_source", step_index=1, order_index=order, observation_status="observed", result_bucket="evidence_added", evidence_delta_bucket="delta_1", latency_bucket="lt_1s", failure_bucket="none", pre_action_currentness_bucket="not_checked", label_available=True, outcome_bucket="success_bucket", evidencecore_required=True))
        order += 1
        d0b_rows.append(build_row(episode=episode, action_type="validate_evidence", step_index=2, order_index=order, observation_status="failed_safe", result_bucket="evidence_rejected", evidence_delta_bucket="delta_0", latency_bucket="lt_1s", failure_bucket="stale_evidence", pre_action_currentness_bucket="not_checked", label_available=True, outcome_bucket="failure_bucket", evidencecore_required=True, stale_evidence=True))
        order += 1
    manifest = {"episode_count": 12}
    report = aggregate_rows(d0b_rows, manifest)
    report["validation_summary"]["privacy_leak_scan"] = "passed"
    checks.append(("d0b_fixture_rows_schema_valid", not schema.validate_trace_rows(d0b_rows)))
    checks.append(("d0b_fixture_gates_pass", all(diversity_gates(d0b_rows).values())))
    checks.append(("public_report_valid_fixture", not validate_public_report(report)))
    bad_rows = copy.deepcopy(d0b_rows)
    del bad_rows[0]["state_features"]["query_shape_bucket"]
    checks.append(("missing_required_trace_field_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(d0b_rows)
    bad_rows[0]["action"]["action_type"] = "rpm_training"
    checks.append(("bad_action_enum_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(d0b_rows)
    bad_rows[1]["trace_identity"]["step_id"] = bad_rows[0]["trace_identity"]["step_id"]
    checks.append(("duplicate_step_id_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(d0b_rows)
    bad_rows[1]["trace_identity"]["episode_step_index"] = 0
    checks.append(("non_monotonic_step_order_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(d0b_rows)
    bad_rows[0]["outcome_label"]["label_timing"] = "offline_eval_only"
    bad_rows[0]["outcome_label"]["label_used_in_state_or_action_bool"] = True
    checks.append(("label_timing_or_usage_leak_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(d0b_rows)
    bad_rows[0]["state_features"]["currentness_bucket"] = "stale_rejected"
    checks.append(("post_action_currentness_feature_rejected", bool(schema.validate_trace_rows(bad_rows)) or any("pre-action" in e for e in validate_public_report({**report, "aggregate_buckets": {**report["aggregate_buckets"], "pre_action_currentness": {"stale_rejected": "count_1"}}}))))
    try:
        capture_traces(False)
        checks.append(("private_output_confirmation_required", False))
    except D0BError as exc:
        checks.append(("private_output_confirmation_required", "confirm-private-output" in str(exc)))
    bad = copy.deepcopy(report)
    bad["stop_go"]["authorized_next_phase"] = "rpm_training"
    checks.append(("training_overauth_rejected", any("authorized" in e or "forbidden" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["debug_private_ref"] = "private_ref_trace_leak"
    checks.append(("private_ref_leak_rejected", bool(validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["diversity_gates"]["gate_results"]["row_count_ge_30"] = False
    checks.append(("failed_gate_complete_status_rejected", any("complete status" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["row_count_bucket"] = "count_6_to_20"
    checks.append(("fewer_than_30_rows_rejected", any("row_count_bucket" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["episode_count_bucket"] = "count_2_to_5"
    checks.append(("fewer_than_10_episodes_rejected", any("episode_count_bucket" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["required_action_types_present"] = ["read_current_source", "validate_evidence"]
    checks.append(("missing_bounded_retrieval_rejected", any("action coverage" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["action_coverage"]["validate_evidence"] = "count_2_to_5"
    checks.append(("fewer_than_required_action_rows_rejected", any("action coverage" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["outcome"]["success_bucket"] = "count_2_to_5"
    checks.append(("fewer_than_5_success_rows_rejected", any("success_bucket" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["outcome"]["failure_bucket"] = "count_2_to_5"
    checks.append(("fewer_than_5_failure_rows_rejected", any("failure_bucket" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["evidencecore_linkage_currentness"].pop("stale_rejected", None)
    checks.append(("missing_stale_negative_control_rejected", any("stale_rejected" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["privacy_contract"]["private_trace_path_public"] = True
    checks.append(("private_trace_path_public_rejected", any("private_trace_path_public" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["privacy_contract"]["queries_public"] = True
    checks.append(("public_query_pattern_leak_rejected", any("queries_public" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["privacy_contract"]["hashes_public"] = True
    checks.append(("public_hash_leak_rejected", any("hashes_public" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["stop_go"]["d2_or_model_scaling_authorized"] = True
    checks.append(("d2_overauthorization_rejected", any("d2_or_model_scaling" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["stop_go"]["training_or_provider_or_network_or_ci_authorized"] = True
    checks.append(("training_provider_overauthorization_rejected", any("training_or_provider" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["pre_action_currentness"] = {"verified_current": "count_21_to_50"}
    checks.append(("pre_action_currentness_leak_rejected", any("pre-action currentness" in e for e in validate_public_report(bad))))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise D0BError("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks), "failed_checks": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture expanded RPM-D0B private local OpenLocus state-action traces")
    parser.add_argument("--self-test", action="store_true", help="run RPM-D0B validator self-tests")
    parser.add_argument("--run-local-trace-capture", action="store_true", help="execute bounded local OpenLocus actions and write private D0B traces")
    parser.add_argument("--confirm-private-output", action="store_true", help="required explicit confirmation for private output write")
    parser.add_argument("--validate-report", type=Path, help="validate aggregate-only RPM-D0B public report")
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
                        "private_episode_count": manifest["episode_count"],
                        "public_report": str(DEFAULT_REPORT),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        parser.error("choose --self-test, --run-local-trace-capture, or --validate-report")
    except (D0BError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
