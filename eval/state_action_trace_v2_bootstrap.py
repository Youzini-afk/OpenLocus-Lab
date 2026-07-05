#!/usr/bin/env python3
"""TraceV2-A product-workflow state-action trace bootstrap.

Converts/audits existing ignored product-workflow private traces into strict
``openlocus.state_action_trace.v2`` rows. This is data prep only: no retrieval,
search, read, citation validation, candidate generation, source scan, provider,
network, CI, training, runtime/default change, or kernel hardening is executed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import frk_product_workflow_bounded_retrieval_repair_prototype as repair_proto
import frk_product_workflow_failure_decomposition as decomp
import frk_product_workflow_specific_retrieval_repair_design as design
import frk_product_workflow_trace_benchmark as benchmark
import rpm_trace_schema as phase1_schema


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_tracev2_a_product_workflow_trace_bootstrap"
ROW_SCHEMA_VERSION = "openlocus.state_action_trace.v2"
REPORT_SCHEMA_VERSION = "state_action_trace_v2_bootstrap_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "state_action_trace_v2_bootstrap" / "state_action_trace_v2_bootstrap_report.json"

PRIVATE_PREFIX = "state_action_trace_v2_bootstrap_private_"
PRIVATE_ROW_FILENAME = "state_action_trace_v2_rows.jsonl"

STATUS_HAAE = "tracev2_a_bootstrap_complete_haae_a2_replay_authorized"
STATUS_FRK_P2 = "tracev2_a_bootstrap_complete_frk_p2_capture_expansion_authorized"
STATUS_REPAIR = "tracev2_a_bootstrap_incomplete_targeted_trace_repair_only"
STATUS_NO_GO = "tracev2_a_bootstrap_no_go_private_trace_unusable"

AUTH_HAAE = "haae_a2_offline_action_replay_smoke_over_existing_v2_rows"
AUTH_FRK_P2 = "frk_p2_workflow_v2_task_state_capture_expansion"
AUTH_REPAIR = "targeted_tracev2_bootstrap_repair_or_minimal_trace_capture_only"
AUTH_NONE = "none_private_trace_unusable"

REQUIRED_GROUPS = (
    "schema_version",
    "trace_id",
    "episode_id",
    "step_index",
    "task",
    "state",
    "action",
    "behavior_policy",
    "observation",
    "evidence_linkage",
    "outcome",
    "privacy_execution",
    "source_lock",
)

ACTION_TYPES = {"retrieve_candidates", "read_next", "validate_now", "stop", "expand_depth", "abstain"}
TARGET_QUESTIONS = {"stop?", "validate_now?", "read_next?", "expand_depth?", "not_applicable"}
OLD_ACTION_MAP = {
    "bounded_retrieval": "expand_depth",
    "read_current_source": "read_next",
    "validate_evidence": "validate_now",
    "workflow_step": "stop",
    "abstain": "abstain",
}
UNKNOWN_VALUES = {"unknown", "not_observable_from_source_trace", "not_applicable", "not_available"}
COUNT_BUCKETS = {"count_0", "count_1", "count_2_to_5", "count_3_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"}
STATUS_SET = {STATUS_HAAE, STATUS_FRK_P2, STATUS_REPAIR, STATUS_NO_GO}

REQUIRED_NESTED_KEYS: dict[str, Any] = {
    "task": {"task_family", "task_split", "language_bucket", "repo_bucket", "query_type", "budget_class"},
    "state": {
        "candidate_pool": {"candidate_count_bucket", "unique_file_count_bucket", "top1_source", "top1_role_guess", "wrong_file_risk_bucket", "first_file_miss_proxy", "rank_miss_proxy"},
        "rankpack": {"pack_arm", "pack_size_bucket", "dedup_applied", "diversity_bucket", "read_budget_pressure_bucket"},
        "evidence_state": {"primary_evidence_count_bucket", "support_evidence_count_bucket", "evidencecore_valid_so_far", "currentness_fail_seen", "citation_fail_seen"},
        "budget_state": {"remaining_reads_bucket", "remaining_validations_bucket", "remaining_token_budget_bucket", "latency_budget_bucket"},
        "uncertainty_state": {"intent_uncertainty_bucket", "file_uncertainty_bucket", "span_uncertainty_bucket", "support_need_bucket"},
    },
    "action": {"action_type", "action_scope", "action_cost_class", "target_question", "source_action_type_bucket", "predeclared_action_bool"},
    "behavior_policy": {"policy_name_private_bucket", "policy_mode", "action_probability_marker", "label_blind_features_only"},
    "observation": {
        "post_action_status": None,
        "evidence_delta_bucket": None,
        "cost_observed": {"read_count_bucket", "validate_count_bucket", "token_bucket", "latency_bucket"},
        "failure_bucket": None,
        "mechanism_bucket": None,
        "observation_after_action_bool": None,
    },
    "evidence_linkage": {"evidencecore_linked", "currentness_verified", "content_sha_present", "path_range_valid", "citation_valid", "materialization_bucket", "candidate_state_separate_bool"},
    "outcome": {
        "label_timing_isolated": None,
        "downstream_proxy": {"correct_file_before_first_edit_bucket", "wrong_file_edit_bucket", "solve_bucket", "tests_pass_bucket"},
        "outcome_bucket": None,
        "label_source_bucket": None,
        "label_available_bool": None,
    },
}

FORBIDDEN = {
    "rpm_d2_training",
    "training_claim",
    "model_scaling",
    "runtime_default_claim",
    "default_claim",
    "provider_claim",
    "network_claim",
    "ci_claim",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "new_retrieval_prototype",
    "retrieval_execution",
    "search_execution",
    "read_execution",
    "citations_validate_execution",
    "broad_source_scan",
    "candidate_generation",
    "task_expansion",
    "kernel_hardening",
    "raw_publication",
    "private_trace_publication",
    "frk_j",
    "frk_b_c_resurrection",
    "frk_i_revival",
    "haae_sg",
    "haae_t",
    "ldi_b_easy_continuation",
    "bounded_repair_route_revival",
}

SOURCE_REPORTS = {
    "benchmark": benchmark.DEFAULT_REPORT,
    "failure_decomposition": decomp.DEFAULT_REPORT,
    "repair_design": design.DEFAULT_REPORT,
    "repair_prototype": repair_proto.DEFAULT_REPORT,
    "rpm_trace_schema": phase1_schema.DEFAULT_REPORT,
}


class TraceV2Error(Exception):
    pass


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


def coverage_bucket(present: int, total: int) -> str:
    if total <= 0 or present <= 0:
        return "coverage_none"
    rate = present / total
    if rate >= 0.95:
        return "coverage_high"
    if rate >= 0.75:
        return "coverage_medium"
    return "coverage_low"


def private_ref(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"private_ref_{prefix}_{digest}"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TraceV2Error(f"missing public source report: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise TraceV2Error(f"malformed public source report: {path.name}") from exc
    if not isinstance(value, dict):
        raise TraceV2Error(f"public source report is not object: {path.name}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TraceV2Error("private JSONL file is missing") from exc
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceV2Error(f"malformed JSONL at private line {line_no}") from exc
        if not isinstance(value, dict):
            raise TraceV2Error(f"private JSONL line {line_no} is not an object")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def latest_root(prefix: str, filename: str) -> Path | None:
    runs = REPO / "runs"
    roots = [path for path in runs.glob(f"{prefix}*") if path.is_dir() and (path / filename).exists()]
    if not roots:
        return None
    return sorted(roots, key=lambda path: (path.stat().st_mtime, path.name))[-1]


def load_allowed_private_inputs(confirm_private_input: bool) -> tuple[list[tuple[str, dict[str, Any]]], dict[str, Any]]:
    if not confirm_private_input:
        raise TraceV2Error("--confirm-private-input is required before reading private Phase-5/Phase-8 product-workflow traces")
    sources = [
        ("phase5_product_workflow", "frk_product_workflow_private_", "frk_product_workflow_state_action_rows.jsonl", "frk_product_workflow_private_expected_labels.jsonl"),
        ("phase8_bounded_repair", "frk_product_workflow_bounded_repair_private_", "frk_product_workflow_bounded_repair_state_action_rows.jsonl", "frk_product_workflow_bounded_repair_private_expected_labels.jsonl"),
    ]
    loaded: list[tuple[str, dict[str, Any]]] = []
    manifest: dict[str, Any] = {"private_input_confirmation": "confirmed", "allowed_private_roots_considered_bucket": bucket_count(len(sources)), "source_manifests": []}
    for source_name, prefix, trace_file, label_file in sources:
        root = latest_root(prefix, trace_file)
        if root is None:
            manifest["source_manifests"].append({"source": source_name, "present": False, "row_count": 0, "label_count": 0})
            continue
        rows = read_jsonl(root / trace_file)
        if not rows:
            raise TraceV2Error(f"private {source_name} trace JSONL is empty")
        errors = phase1_schema.validate_trace_rows(rows)
        if errors:
            raise TraceV2Error(f"private {source_name} trace rows failed Phase-1 schema validation: " + "; ".join(errors[:5]))
        labels = read_jsonl(root / label_file) if (root / label_file).exists() else []
        if labels and not all(item.get("label_timing") == "after_action" for item in labels):
            raise TraceV2Error(f"private {source_name} labels must be after-action labels")
        for row in rows:
            loaded.append((source_name, row))
        manifest["source_manifests"].append({"source": source_name, "present": True, "row_count": len(rows), "label_count": len(labels)})
    if not loaded:
        raise TraceV2Error("no allowed private product-workflow trace rows found")
    manifest["source_count_bucket"] = bucket_count(sum(1 for item in manifest["source_manifests"] if item["present"]))
    manifest["input_row_count"] = len(loaded)
    manifest["input_episode_count"] = len({row["trace_identity"]["trace_id"] for _source, row in loaded})
    return loaded, manifest


def old_bool(value: Any, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def old_str(group: dict[str, Any], key: str, default: str = "unknown") -> str:
    value = group.get(key)
    return value if isinstance(value, str) and value else default


def bool_bucket(value: bool | None, unknown: bool = False) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown" if unknown else "not_observable_from_source_trace"


def mechanism_from_old(action_type: str, obs: dict[str, Any], ev: dict[str, Any]) -> str:
    failure = old_str(obs, "failure_bucket", "none")
    link = old_str(ev, "evidencecore_link_status", "unknown")
    if failure == "missing_source":
        return "no_hit"
    if failure == "validation_failed":
        return "validation_failure"
    if link in {"stale_rejected", "unsafe_rejected"}:
        return "currentness_failure"
    if action_type == "bounded_retrieval":
        return "rankpack_or_candidate_pool"
    return "not_observable_from_source_trace"


def convert_row(source_name: str, old: dict[str, Any]) -> dict[str, Any]:
    ident = old.get("trace_identity", {}) if isinstance(old.get("trace_identity"), dict) else {}
    task = old.get("task_state", {}) if isinstance(old.get("task_state"), dict) else {}
    state = old.get("state_features", {}) if isinstance(old.get("state_features"), dict) else {}
    action = old.get("action", {}) if isinstance(old.get("action"), dict) else {}
    policy = old.get("policy_learning_support", {}) if isinstance(old.get("policy_learning_support"), dict) else {}
    obs = old.get("observation_result", {}) if isinstance(old.get("observation_result"), dict) else {}
    ev = old.get("evidencecore_linkage", {}) if isinstance(old.get("evidencecore_linkage"), dict) else {}
    out = old.get("outcome_label", {}) if isinstance(old.get("outcome_label"), dict) else {}
    priv = old.get("privacy_execution", {}) if isinstance(old.get("privacy_execution"), dict) else {}
    lock = old.get("stop_go_source_locks_readback", {}) if isinstance(old.get("stop_go_source_locks_readback"), dict) else {}
    old_action = old_str(action, "action_type", "unknown")
    converted_action = OLD_ACTION_MAP.get(old_action, "abstain")
    candidate_count = old_str(state, "candidate_count_bucket", "unknown")
    evidence_coverage = old_str(state, "evidence_coverage_bucket", "unknown")
    read_pressure = "high" if candidate_count in {"count_2_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"} and old_action in {"read_current_source", "validate_evidence", "workflow_step"} else "unknown"
    currentness_status = old_str(ev, "currentness_verification_status", "unknown")
    evidence_link_status = old_str(ev, "evidencecore_link_status", "unknown")
    label_timing = old_str(out, "label_timing", "not_available")
    trace_id = old_str(ident, "trace_id", private_ref("missing_trace", source_name, str(ident.get("created_order_index", "unknown"))))
    step_index = ident.get("episode_step_index")
    step_int = step_index if isinstance(step_index, int) else 0
    return {
        "schema_version": ROW_SCHEMA_VERSION,
        "trace_id": trace_id,
        "episode_id": trace_id,
        "step_index": step_int,
        "task": {
            "task_family": "not_observable_from_source_trace",
            "task_split": "existing_private_trace_bootstrap",
            "language_bucket": "not_observable_from_source_trace",
            "repo_bucket": old_str(state, "repo_size_bucket", "unknown"),
            "query_type": old_str(state, "query_shape_bucket", "unknown"),
            "budget_class": old_str(action, "retrieval_budget_bucket", "unknown"),
        },
        "state": {
            "candidate_pool": {
                "candidate_count_bucket": candidate_count,
                "unique_file_count_bucket": "not_observable_from_source_trace",
                "top1_source": "not_observable_from_source_trace",
                "top1_role_guess": "not_observable_from_source_trace",
                "wrong_file_risk_bucket": "not_observable_from_source_trace",
                "first_file_miss_proxy": "not_observable_from_source_trace",
                "rank_miss_proxy": "not_observable_from_source_trace",
            },
            "rankpack": {
                "pack_arm": "not_observable_from_source_trace",
                "pack_size_bucket": candidate_count,
                "dedup_applied": "not_observable_from_source_trace",
                "diversity_bucket": "not_observable_from_source_trace",
                "read_budget_pressure_bucket": read_pressure,
            },
            "evidence_state": {
                "primary_evidence_count_bucket": "count_1" if evidence_coverage in {"coverage_medium", "coverage_high"} else "unknown",
                "support_evidence_count_bucket": "not_observable_from_source_trace",
                "evidencecore_valid_so_far": "not_checked",
                "currentness_fail_seen": "not_checked",
                "citation_fail_seen": "not_checked",
            },
            "budget_state": {
                "remaining_reads_bucket": "not_observable_from_source_trace",
                "remaining_validations_bucket": "not_observable_from_source_trace",
                "remaining_token_budget_bucket": "not_observable_from_source_trace",
                "latency_budget_bucket": old_str(obs, "latency_bucket", "unknown"),
            },
            "uncertainty_state": {
                "intent_uncertainty_bucket": old_str(state, "ambiguity_bucket", "unknown"),
                "file_uncertainty_bucket": "not_observable_from_source_trace",
                "span_uncertainty_bucket": "not_observable_from_source_trace",
                "support_need_bucket": "not_observable_from_source_trace",
            },
        },
        "action": {
            "action_type": converted_action,
            "action_scope": old_str(action, "action_scope_bucket", "unknown"),
            "action_cost_class": old_str(action, "retrieval_budget_bucket", "unknown"),
            "target_question": {"expand_depth": "expand_depth?", "read_next": "read_next?", "validate_now": "validate_now?", "stop": "stop?", "abstain": "stop?"}.get(converted_action, "not_applicable"),
            "source_action_type_bucket": old_action if old_action in OLD_ACTION_MAP else "unknown",
            "predeclared_action_bool": True,
        },
        "behavior_policy": {
            "policy_name_private_bucket": "phase5_or_phase8_logged_policy",
            "policy_mode": old_str(policy, "behavior_policy_kind", "unknown"),
            "action_probability_marker": old_str(policy, "action_probability_bucket", "unknown"),
            "label_blind_features_only": old_bool(state.get("features_label_blind_bool"), True),
        },
        "observation": {
            "post_action_status": old_str(obs, "observation_status", "unknown"),
            "evidence_delta_bucket": old_str(obs, "evidence_delta_bucket", "unknown"),
            "cost_observed": {
                "read_count_bucket": "count_1" if old_action == "read_current_source" else "count_0",
                "validate_count_bucket": "count_1" if old_action == "validate_evidence" else "count_0",
                "token_bucket": "not_observable_from_source_trace",
                "latency_bucket": old_str(obs, "latency_bucket", "unknown"),
            },
            "failure_bucket": old_str(obs, "failure_bucket", "unknown"),
            "mechanism_bucket": mechanism_from_old(old_action, obs, ev),
            "observation_after_action_bool": old_bool(obs.get("observation_after_action_bool"), True),
        },
        "evidence_linkage": {
            "evidencecore_linked": bool_bucket(evidence_link_status == "linked_current"),
            "currentness_verified": bool_bucket(currentness_status == "verified_current"),
            "content_sha_present": "not_observable_from_source_trace",
            "path_range_valid": bool_bucket(old_bool(ev.get("path_range_hash_private_only_bool")), unknown=True),
            "citation_valid": bool_bucket(evidence_link_status == "linked_current"),
            "materialization_bucket": old_str(ev, "materialization_status", "unknown"),
            "candidate_state_separate_bool": True,
        },
        "outcome": {
            "label_timing_isolated": bool_bucket(label_timing in {"after_action", "after_episode", "offline_eval_only"}),
            "downstream_proxy": {
                "correct_file_before_first_edit_bucket": "not_observable_from_source_trace",
                "wrong_file_edit_bucket": "not_observable_from_source_trace",
                "solve_bucket": old_str(out, "outcome_bucket", "not_evaluated"),
                "tests_pass_bucket": "not_observable_from_source_trace",
            },
            "outcome_bucket": old_str(out, "outcome_bucket", "not_evaluated"),
            "label_source_bucket": old_str(out, "label_source", "none"),
            "label_available_bool": old_bool(out.get("label_available_bool")),
        },
        "privacy_execution": {
            "private_trace_bool": True,
            "public_report_level": "aggregate_only",
            "raw_publication_bool": False,
            "private_values_public_bool": False,
            "provider_or_model_calls_executed": False,
            "network_access": old_str(priv, "network_access", "no_network"),
            "ci_execution": old_str(priv, "ci_execution", "local_manual_only"),
            "retrieval_search_read_validate_executed_in_bootstrap": False,
            "candidate_generation_executed": False,
            "source_scan_executed": False,
            "training_or_model_fitting_executed": False,
            "runtime_default_changed": False,
        },
        "source_lock": {
            "bootstrap_source": source_name,
            "source_lock_readback_status": old_str(lock, "source_lock_readback_status", "unknown"),
            "source_trace_schema_version": old_str(ident, "schema_version", "unknown"),
            "conversion_policy": "lossless_bucketized_where_observable_unknown_elsewhere",
            "overauthorization_bool": False,
        },
    }


def validate_v2_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, int]] = set()
    by_episode: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {idx} is not object")
            continue
        extra = set(row) - set(REQUIRED_GROUPS)
        missing = set(REQUIRED_GROUPS) - set(row)
        if extra:
            errors.append(f"row {idx} unknown top-level keys: {sorted(extra)}")
        if missing:
            errors.append(f"row {idx} missing required groups: {sorted(missing)}")
        if row.get("schema_version") != ROW_SCHEMA_VERSION:
            errors.append(f"row {idx} bad schema_version")
        trace_id = row.get("trace_id")
        episode_id = row.get("episode_id")
        step_index = row.get("step_index")
        if not isinstance(trace_id, str) or not trace_id:
            errors.append(f"row {idx} bad trace_id")
        if not isinstance(episode_id, str) or not episode_id:
            errors.append(f"row {idx} bad episode_id")
        if not isinstance(step_index, int) or step_index < 0:
            errors.append(f"row {idx} bad step_index")
        else:
            key = (str(episode_id), step_index)
            if key in seen:
                errors.append(f"row {idx} duplicate episode step")
            seen.add(key)
            by_episode[str(episode_id)].append(step_index)
        for group in ("task", "state", "action", "behavior_policy", "observation", "evidence_linkage", "outcome", "privacy_execution", "source_lock"):
            if not isinstance(row.get(group), dict):
                errors.append(f"row {idx} group {group} is not object")
        task_group = row.get("task", {}) if isinstance(row.get("task"), dict) else {}
        state = row.get("state", {}) if isinstance(row.get("state"), dict) else {}
        action = row.get("action", {}) if isinstance(row.get("action"), dict) else {}
        behavior = row.get("behavior_policy", {}) if isinstance(row.get("behavior_policy"), dict) else {}
        observation = row.get("observation", {}) if isinstance(row.get("observation"), dict) else {}
        ev = row.get("evidence_linkage", {}) if isinstance(row.get("evidence_linkage"), dict) else {}
        outcome = row.get("outcome", {}) if isinstance(row.get("outcome"), dict) else {}
        priv = row.get("privacy_execution", {}) if isinstance(row.get("privacy_execution"), dict) else {}
        for group_name, schema_spec in REQUIRED_NESTED_KEYS.items():
            group_value = row.get(group_name, {})
            if not isinstance(group_value, dict):
                continue
            if isinstance(schema_spec, set):
                missing_group_keys = schema_spec - set(group_value)
                extra_group_keys = set(group_value) - schema_spec
                if missing_group_keys:
                    errors.append(f"row {idx} missing keys in {group_name}: {sorted(missing_group_keys)}")
                if extra_group_keys:
                    errors.append(f"row {idx} unknown keys in {group_name}: {sorted(extra_group_keys)}")
                continue
            for key, subkeys in schema_spec.items():
                if key not in group_value:
                    errors.append(f"row {idx} missing nested key {group_name}.{key}")
                    continue
                if isinstance(subkeys, set):
                    nested = group_value.get(key)
                    if not isinstance(nested, dict):
                        errors.append(f"row {idx} nested subgroup {group_name}.{key} is not object")
                    else:
                        missing_nested = subkeys - set(nested)
                        extra_nested = set(nested) - subkeys
                        if missing_nested:
                            errors.append(f"row {idx} missing nested keys {group_name}.{key}: {sorted(missing_nested)}")
                        if extra_nested:
                            errors.append(f"row {idx} unknown nested keys {group_name}.{key}: {sorted(extra_nested)}")
            allowed = set(schema_spec)
            extra_group = set(group_value) - allowed
            if extra_group:
                errors.append(f"row {idx} unknown keys in {group_name}: {sorted(extra_group)}")
        if action.get("action_type") not in ACTION_TYPES:
            errors.append(f"row {idx} bad action enum")
        if action.get("target_question") not in TARGET_QUESTIONS:
            errors.append(f"row {idx} bad target question")
        if action.get("predeclared_action_bool") is not True:
            errors.append(f"row {idx} action not predeclared")
        if behavior.get("label_blind_features_only") is not True:
            errors.append(f"row {idx} behavior policy not label blind")
        if outcome.get("label_timing_isolated") != "true":
            errors.append(f"row {idx} label-before-action or label leakage")
        forbidden_label_keys = {"label", "gold", "expected", "outcome", "outcome_bucket", "success_bucket", "failure_bucket", "solve_bucket", "tests_pass_bucket"}
        state_action_keys = set(state) | set(action) | set(task_group)
        state_action_text = json.dumps({"state": state, "action": action}, sort_keys=True)
        if (forbidden_label_keys & state_action_keys) or re.search(r"gold|expected|outcome_bucket|success_bucket|failure_bucket", state_action_text):
            errors.append(f"row {idx} label/gold leaked into state/action")
        evidence_state = state.get("evidence_state", {}) if isinstance(state.get("evidence_state"), dict) else {}
        if evidence_state.get("evidencecore_valid_so_far") != "not_checked" or evidence_state.get("currentness_fail_seen") != "not_checked" or evidence_state.get("citation_fail_seen") != "not_checked":
            errors.append(f"row {idx} post-action currentness leaked into pre-action state")
        uncertainty = state.get("uncertainty_state", {}) if isinstance(state.get("uncertainty_state"), dict) else {}
        if uncertainty.get("file_uncertainty_bucket") not in UNKNOWN_VALUES or uncertainty.get("span_uncertainty_bucket") not in UNKNOWN_VALUES or uncertainty.get("support_need_bucket") not in UNKNOWN_VALUES:
            errors.append(f"row {idx} invented non-observable uncertainty field")
        forbidden_state_keys = {"evidence_path", "path", "range", "content_sha", "hash", "snippet", "evidence_linkage", "candidate_evidencecore"}
        if forbidden_state_keys & set(state) or any(forbidden_state_keys & set(value) for value in state.values() if isinstance(value, dict)):
            errors.append(f"row {idx} EvidenceCore linkage conflated with candidate state")
        if ev.get("candidate_state_separate_bool") is not True:
            errors.append(f"row {idx} EvidenceCore linkage not separate from candidate state")
        if observation.get("observation_after_action_bool") is not True:
            errors.append(f"row {idx} observation is not after action")
        for flag in ("retrieval_search_read_validate_executed_in_bootstrap", "candidate_generation_executed", "source_scan_executed", "training_or_model_fitting_executed", "runtime_default_changed", "raw_publication_bool", "private_values_public_bool", "provider_or_model_calls_executed"):
            if priv.get(flag) is not False:
                errors.append(f"row {idx} forbidden execution/privacy flag set: {flag}")
        if priv.get("network_access") != "no_network" or priv.get("ci_execution") != "local_manual_only":
            errors.append(f"row {idx} provider/network/CI drift")
    for episode, steps in by_episode.items():
        if sorted(steps) != list(range(min(steps), max(steps) + 1)) or steps != sorted(steps):
            errors.append(f"episode {episode} duplicate/non-monotonic step sequence")
    return errors


def source_readbacks() -> dict[str, Any]:
    reports = {name: read_json(path) for name, path in SOURCE_REPORTS.items()}
    return {
        "benchmark_status": reports["benchmark"].get("status"),
        "failure_decomposition_status": reports["failure_decomposition"].get("status"),
        "repair_design_status": reports["repair_design"].get("status"),
        "repair_prototype_status": reports["repair_prototype"].get("status"),
        "repair_prototype_delta_vs_best": reports["repair_prototype"].get("arm_comparison", {}).get("delta_prototype_vs_best_fixed_baseline"),
        "repair_prototype_privacy_gate": reports["repair_prototype"].get("validation_summary", {}).get("privacy_leak_scan"),
        "rpm_trace_schema_status": reports["rpm_trace_schema"].get("status"),
        "runtime_public_report_readback_only": True,
    }


def source_readbacks_ok(readbacks: dict[str, Any]) -> bool:
    return (
        readbacks.get("benchmark_status") == benchmark.STATUS_NO_LIFT
        and readbacks.get("failure_decomposition_status") == decomp.STATUS_RETRIEVAL_REPAIR
        and readbacks.get("repair_design_status") == design.STATUS_CONCRETE
        and readbacks.get("repair_prototype_status") == repair_proto.STATUS_NO_LIFT
        and readbacks.get("repair_prototype_delta_vs_best") == "negative_delta"
        and readbacks.get("repair_prototype_privacy_gate") == "passed"
        and isinstance(readbacks.get("rpm_trace_schema_status"), str)
        and readbacks.get("runtime_public_report_readback_only") is True
    )


CRITICAL_FIELDS: dict[str, tuple[str, ...]] = {
    "task": ("task_family", "task_split", "language_bucket", "repo_bucket", "query_type", "budget_class"),
    "state.candidate_pool": ("candidate_count_bucket", "unique_file_count_bucket", "top1_source", "top1_role_guess", "wrong_file_risk_bucket", "first_file_miss_proxy", "rank_miss_proxy"),
    "state.rankpack": ("pack_arm", "pack_size_bucket", "dedup_applied", "diversity_bucket", "read_budget_pressure_bucket"),
    "state.evidence_state": ("primary_evidence_count_bucket", "support_evidence_count_bucket", "evidencecore_valid_so_far", "currentness_fail_seen", "citation_fail_seen"),
    "state.budget_state": ("remaining_reads_bucket", "remaining_validations_bucket", "remaining_token_budget_bucket", "latency_budget_bucket"),
    "state.uncertainty_state": ("intent_uncertainty_bucket", "file_uncertainty_bucket", "span_uncertainty_bucket", "support_need_bucket"),
    "action": ("action_type", "action_scope", "action_cost_class", "target_question", "source_action_type_bucket", "predeclared_action_bool"),
    "behavior_policy": ("policy_name_private_bucket", "policy_mode", "action_probability_marker", "label_blind_features_only"),
    "observation": ("post_action_status", "evidence_delta_bucket", "failure_bucket", "mechanism_bucket", "observation_after_action_bool"),
    "observation.cost_observed": ("read_count_bucket", "validate_count_bucket", "token_bucket", "latency_bucket"),
    "evidence_linkage": ("evidencecore_linked", "currentness_verified", "content_sha_present", "path_range_valid", "citation_valid", "materialization_bucket", "candidate_state_separate_bool"),
    "outcome": ("label_timing_isolated", "outcome_bucket", "label_source_bucket", "label_available_bool"),
    "outcome.downstream_proxy": ("correct_file_before_first_edit_bucket", "wrong_file_edit_bucket", "solve_bucket", "tests_pass_bucket"),
}


def nested_get(row: dict[str, Any], dotted_group: str) -> dict[str, Any]:
    value: Any = row
    for part in dotted_group.split("."):
        value = value.get(part, {}) if isinstance(value, dict) else {}
    return value if isinstance(value, dict) else {}


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_v2_rows(rows)
    row_count = len(rows)
    episode_count = len({row.get("episode_id") for row in rows if isinstance(row.get("episode_id"), str)})
    actions = Counter(row.get("action", {}).get("action_type", "unknown") for row in rows if isinstance(row.get("action"), dict))
    groups_present = {group: 0 for group in REQUIRED_GROUPS}
    unknowns = Counter()
    critical_present = 0
    critical_total = 0
    for row in rows:
        for group in REQUIRED_GROUPS:
            if group in row and row.get(group) not in (None, ""):
                groups_present[group] += 1
        for group, fields in CRITICAL_FIELDS.items():
            data = nested_get(row, group)
            for field in fields:
                critical_total += 1
                value = data.get(field)
                if value in UNKNOWN_VALUES or value in (None, ""):
                    unknowns[f"{group}.{field}"] += 1
                else:
                    critical_present += 1
    critical_rate = critical_present / critical_total if critical_total else 0.0
    target_questions = {row.get("action", {}).get("target_question") for row in rows if isinstance(row.get("action"), dict)}
    observable_task_families = {
        row.get("task", {}).get("task_family")
        for row in rows
        if isinstance(row.get("task"), dict) and row.get("task", {}).get("task_family") not in UNKNOWN_VALUES
    }
    family_bucket = bucket_count(len(observable_task_families))
    critical_sufficient = critical_rate >= 0.90 and sum(unknowns.values()) == 0
    gap_dominant = not critical_sufficient
    return {
        "schema_errors": errors,
        "private_row_count": row_count,
        "private_episode_count": episode_count,
        "action_types": sorted(action for action in actions if action != "unknown"),
        "action_coverage_buckets": {action: bucket_count(count) for action, count in sorted(actions.items())},
        "task_family_coverage_bucket": family_bucket,
        "conversion_coverage_by_group": {group: coverage_bucket(count, row_count) for group, count in groups_present.items()},
        "critical_field_coverage_bucket": coverage_bucket(critical_present, critical_total),
        "critical_field_coverage_sufficient": critical_sufficient,
        "unknown_missingness_bucket": bucket_count(sum(unknowns.values())),
        "unknown_missingness_by_group": {group: bucket_count(sum(count for key, count in unknowns.items() if key.startswith(group + "."))) for group in CRITICAL_FIELDS},
        "label_after_action_isolation": "passed" if not any("label" in err for err in errors) else "failed",
        "currentness_leakage_scan": "passed" if not any("currentness" in err for err in errors) else "failed",
        "replayable_targets": sorted(target for target in target_questions if target in {"stop?", "validate_now?", "read_next?", "expand_depth?"}),
        "coverage_gaps_dominate": gap_dominant,
    }


def choose_status(audit: dict[str, Any], source_ok: bool, private_ok: bool) -> tuple[str, str, str]:
    schema_ok = not audit.get("schema_errors")
    privacy_ok = private_ok
    enough = (
        audit.get("private_row_count", 0) >= 50
        and audit.get("private_episode_count", 0) >= 20
        and len(audit.get("action_types", [])) >= 3
        and audit.get("task_family_coverage_bucket") == "count_3_to_5"
        and audit.get("critical_field_coverage_sufficient") is True
        and audit.get("label_after_action_isolation") == "passed"
        and audit.get("currentness_leakage_scan") == "passed"
        and bool(audit.get("replayable_targets"))
        and audit.get("coverage_gaps_dominate") is not True
    )
    if not source_ok or not schema_ok or not privacy_ok:
        return STATUS_REPAIR, AUTH_REPAIR, "targeted_tracev2_bootstrap_repair_or_minimal_trace_capture_only"
    if enough:
        return STATUS_HAAE, AUTH_HAAE, "haae_a2_replay_over_existing_v2_rows_only"
    if audit.get("private_row_count", 0) > 0:
        return STATUS_FRK_P2, AUTH_FRK_P2, "frk_p2_capture_expansion_for_tracev2_coverage_gaps_only"
    return STATUS_NO_GO, AUTH_NONE, "no_go_private_trace_unusable"


def build_report(rows: list[dict[str, Any]], manifest: dict[str, Any], default_unavailable: bool = False) -> dict[str, Any]:
    readbacks = source_readbacks()
    audit = audit_rows(rows)
    status, auth, decision = choose_status(audit, source_readbacks_ok(readbacks), not default_unavailable)
    if default_unavailable:
        status, auth, decision = STATUS_NO_GO, AUTH_NONE, "no_go_missing_explicit_private_confirmations"
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "source_checkpoints_readbacks": readbacks,
        "execution_attestations": {
            "bootstrap_conversion_only": True,
            "public_reports_read_only": True,
            "existing_private_phase5_phase8_inputs_only": True,
            "retrieval_search_read_validate_executed": False,
            "new_candidates_generated": False,
            "source_scan_executed": False,
            "task_expansion_executed": False,
            "provider_or_model_calls_executed": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "training_or_model_fitting_executed": False,
            "rpm_d2_or_model_scaling_executed": False,
            "runtime_default_changed": False,
            "kernel_hardening_executed": False,
        },
        "private_io_buckets": {
            "private_input_confirmation": "not_confirmed" if default_unavailable else manifest.get("private_input_confirmation", "confirmed"),
            "private_output_confirmation": "not_confirmed" if default_unavailable else manifest.get("private_output_confirmation", "confirmed"),
            "allowed_private_source_count_bucket": manifest.get("source_count_bucket", "count_0"),
            "private_input_row_count_bucket": bucket_count(int(manifest.get("input_row_count", 0))),
            "private_input_episode_count_bucket": bucket_count(int(manifest.get("input_episode_count", 0))),
            "private_output_row_count_bucket": bucket_count(audit["private_row_count"]),
            "private_output_episode_count_bucket": bucket_count(audit["private_episode_count"]),
        },
        "tracev2_validation": {
            "v2_schema_validation": "passed" if not audit["schema_errors"] else "failed",
            "schema_error_bucket": bucket_count(len(audit["schema_errors"])),
            "label_after_action_isolation": audit["label_after_action_isolation"],
            "currentness_leakage_scan": audit["currentness_leakage_scan"],
            "evidence_linkage_separate_from_candidate_state": "passed" if not any("EvidenceCore" in err for err in audit["schema_errors"]) else "failed",
        },
        "coverage_audit": {
            "conversion_coverage_by_group": audit["conversion_coverage_by_group"],
            "critical_field_coverage_bucket": audit["critical_field_coverage_bucket"],
            "critical_field_coverage_sufficient": audit["critical_field_coverage_sufficient"],
            "unknown_missingness_bucket": audit["unknown_missingness_bucket"],
            "unknown_missingness_by_group": audit["unknown_missingness_by_group"],
            "action_coverage_buckets": audit["action_coverage_buckets"],
            "task_family_coverage_bucket": audit["task_family_coverage_bucket"],
            "replayable_target_bucket": bucket_count(len(audit["replayable_targets"])),
            "coverage_gaps_dominate": audit["coverage_gaps_dominate"],
        },
        "privacy_contract": {
            "publication_level": "aggregate_only",
            "raw_paths_public": False,
            "queries_public": False,
            "snippets_public": False,
            "ranges_public": False,
            "hashes_or_content_sha_public": False,
            "private_refs_public": False,
            "raw_task_ids_public": False,
            "raw_rows_public": False,
            "exact_labels_public": False,
            "per_task_outcomes_public": False,
            "private_trace_paths_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": decision,
            "authorized_next_phase": auth,
            "explicitly_forbidden": sorted(FORBIDDEN),
            "haae_a2_replay_authorized": auth == AUTH_HAAE,
            "frk_p2_capture_expansion_authorized": auth == AUTH_FRK_P2,
            "targeted_trace_repair_authorized": auth == AUTH_REPAIR,
            "rpm_d2_training_authorized": False,
            "model_scaling_authorized": False,
            "runtime_or_default_authorized": False,
            "new_retrieval_prototype_authorized": False,
            "broad_frk_repair_or_kernel_hardening_authorized": False,
            "provider_network_ci_authorized": False,
            "method_scale_winner_default_claims_allowed": False,
            "raw_private_trace_publication_authorized": False,
            "closed_route_revival_authorized": False,
        },
        "validation_summary": {"privacy_scan": "pending", "self_test_mutation_coverage": "available", "public_report_level": "aggregate_only"},
    }


REPORT_KEYS = {"schema_version", "phase", "status", "source_checkpoints_readbacks", "execution_attestations", "private_io_buckets", "tracev2_validation", "coverage_audit", "privacy_contract", "stop_go", "validation_summary"}
EXEC_KEYS = {"bootstrap_conversion_only", "public_reports_read_only", "existing_private_phase5_phase8_inputs_only", "retrieval_search_read_validate_executed", "new_candidates_generated", "source_scan_executed", "task_expansion_executed", "provider_or_model_calls_executed", "network_access", "ci_execution", "training_or_model_fitting_executed", "rpm_d2_or_model_scaling_executed", "runtime_default_changed", "kernel_hardening_executed"}
PRIVACY_KEYS = {"publication_level", "raw_paths_public", "queries_public", "snippets_public", "ranges_public", "hashes_or_content_sha_public", "private_refs_public", "raw_task_ids_public", "raw_rows_public", "exact_labels_public", "per_task_outcomes_public", "private_trace_paths_public", "raw_publication"}
STOP_KEYS = {"decision", "authorized_next_phase", "explicitly_forbidden", "haae_a2_replay_authorized", "frk_p2_capture_expansion_authorized", "targeted_trace_repair_authorized", "rpm_d2_training_authorized", "model_scaling_authorized", "runtime_or_default_authorized", "new_retrieval_prototype_authorized", "broad_frk_repair_or_kernel_hardening_authorized", "provider_network_ci_authorized", "method_scale_winner_default_claims_allowed", "raw_private_trace_publication_authorized", "closed_route_revival_authorized"}
AUTH_BY_STATUS = {STATUS_HAAE: AUTH_HAAE, STATUS_FRK_P2: AUTH_FRK_P2, STATUS_REPAIR: AUTH_REPAIR, STATUS_NO_GO: AUTH_NONE}


def all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(all_strings(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(all_strings(item))
        return out
    return []


def leak_errors(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    path_re = re.compile(r"(/workspace/|runs/|\.jsonl\b|\b(?:crates|eval|docs|scripts|artifacts)/[^\s]+|:[0-9]+-[0-9]+)")
    task_re = re.compile(r"\bwf[0-9]{2}\b")
    hash_re = re.compile(r"\b[a-f0-9]{32,}\b", re.I)
    for text in all_strings(report):
        if path_re.search(text):
            errors.append("public path/query/range leak")
        if task_re.search(text):
            errors.append("raw task id or per-task outcome leak")
        if hash_re.search(text) or "content_sha" in text:
            errors.append("hash/content_sha leak")
        if "private_ref_" in text:
            errors.append("private_ref leak")
        if text.strip().startswith("{") and "schema_version" in text:
            errors.append("raw row publication leak")
        if "snippet" in text.lower() and not text.endswith("_public"):
            errors.append("snippet leak")
    return errors


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(report) != REPORT_KEYS:
        errors.append("unknown or missing top-level report key")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("schema_version drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    status_value = report.get("status")
    status = status_value if isinstance(status_value, str) else ""
    if status not in STATUS_SET:
        errors.append("unknown status")
    src = report.get("source_checkpoints_readbacks", {})
    if not isinstance(src, dict) or not source_readbacks_ok(src):
        errors.append("source readback mismatch")
    exe = report.get("execution_attestations", {})
    if not isinstance(exe, dict) or set(exe) != EXEC_KEYS:
        errors.append("execution attestation key drift")
    for key in ("bootstrap_conversion_only", "public_reports_read_only", "existing_private_phase5_phase8_inputs_only"):
        if exe.get(key) is not True:
            errors.append(f"execution {key} must be true")
    for key in ("retrieval_search_read_validate_executed", "new_candidates_generated", "source_scan_executed", "task_expansion_executed", "provider_or_model_calls_executed", "training_or_model_fitting_executed", "rpm_d2_or_model_scaling_executed", "runtime_default_changed", "kernel_hardening_executed"):
        if exe.get(key) is not False:
            errors.append(f"forbidden execution flag set: {key}")
    if exe.get("network_access") != "no_network" or exe.get("ci_execution") != "local_manual_only":
        errors.append("provider/network/CI flag drift")
    pio = report.get("private_io_buckets", {})
    for key in ("allowed_private_source_count_bucket", "private_input_row_count_bucket", "private_input_episode_count_bucket", "private_output_row_count_bucket", "private_output_episode_count_bucket"):
        if pio.get(key) not in COUNT_BUCKETS:
            errors.append(f"bad private IO bucket {key}")
    val = report.get("tracev2_validation", {})
    if val.get("v2_schema_validation") != "passed" and status == STATUS_FRK_P2:
        errors.append("FRK-P2 authorization requires schema pass")
    if val.get("label_after_action_isolation") != "passed" or val.get("currentness_leakage_scan") != "passed" or val.get("evidence_linkage_separate_from_candidate_state") != "passed":
        errors.append("trace isolation/currentness/evidence separation failed")
    cov = report.get("coverage_audit", {})
    if status == STATUS_HAAE and (
        cov.get("critical_field_coverage_sufficient") is not True
        or cov.get("replayable_target_bucket") == "count_0"
        or cov.get("task_family_coverage_bucket") != "count_3_to_5"
        or cov.get("coverage_gaps_dominate") is True
    ):
        errors.append("HAAE-A2 authorization with insufficient critical coverage")
    if status == STATUS_FRK_P2 and cov.get("coverage_gaps_dominate") is not True:
        errors.append("FRK-P2 authorization without dominant coverage gaps")
    priv = report.get("privacy_contract", {})
    if not isinstance(priv, dict) or set(priv) != PRIVACY_KEYS:
        errors.append("privacy contract key drift")
    if priv.get("publication_level") != "aggregate_only":
        errors.append("publication level drift")
    for key in PRIVACY_KEYS - {"publication_level"}:
        if priv.get(key) is not False:
            errors.append(f"privacy flag set: {key}")
    stop = report.get("stop_go", {})
    if not isinstance(stop, dict) or set(stop) != STOP_KEYS:
        errors.append("stop/go key drift")
    if stop.get("authorized_next_phase") != AUTH_BY_STATUS.get(status):
        errors.append("authorized next phase inconsistent with status")
    if set(stop.get("explicitly_forbidden", [])) != FORBIDDEN:
        errors.append("forbidden set drift")
    if stop.get("haae_a2_replay_authorized") is not (stop.get("authorized_next_phase") == AUTH_HAAE):
        errors.append("HAAE-A2 flag inconsistency")
    if stop.get("frk_p2_capture_expansion_authorized") is not (stop.get("authorized_next_phase") == AUTH_FRK_P2):
        errors.append("FRK-P2 flag inconsistency")
    for key in ("rpm_d2_training_authorized", "model_scaling_authorized", "runtime_or_default_authorized", "new_retrieval_prototype_authorized", "broad_frk_repair_or_kernel_hardening_authorized", "provider_network_ci_authorized", "method_scale_winner_default_claims_allowed", "raw_private_trace_publication_authorized", "closed_route_revival_authorized"):
        if stop.get(key) is not False:
            errors.append(f"overauthorization flag set: {key}")
    vs = report.get("validation_summary", {})
    if vs.get("privacy_scan") != "passed" or vs.get("public_report_level") != "aggregate_only" or vs.get("self_test_mutation_coverage") != "available":
        errors.append("validation summary drift")
    errors.extend(leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_scan"] = "passed" if not leak_errors(final) else "failed"
    errors = validate_report(final)
    if errors:
        raise TraceV2Error("public report validation failed: " + "; ".join(errors[:12]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_bootstrap(confirm_private_input: bool, confirm_private_output: bool) -> dict[str, Any]:
    if not confirm_private_output:
        raise TraceV2Error("--confirm-private-output is required before writing private TraceV2 rows")
    loaded, manifest = load_allowed_private_inputs(confirm_private_input)
    rows = [convert_row(source, row) for source, row in loaded]
    errors = validate_v2_rows(rows)
    if errors:
        raise TraceV2Error("converted TraceV2 rows failed validation: " + "; ".join(errors[:8]))
    root = REPO / "runs" / f"{PRIVATE_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    write_jsonl(root / PRIVATE_ROW_FILENAME, rows)
    manifest = dict(manifest)
    manifest["private_output_confirmation"] = "confirmed"
    manifest["private_output_row_count"] = len(rows)
    manifest["private_output_episode_count"] = len({row["episode_id"] for row in rows})
    return build_report(rows, manifest)


def default_report() -> dict[str, Any]:
    return build_report([], {"private_input_confirmation": "not_confirmed", "private_output_confirmation": "not_confirmed"}, default_unavailable=True)


def fixture_row() -> dict[str, Any]:
    task = benchmark.TASKS[0]
    old = benchmark.build_row(task=task, arm="openlocus_hybrid_retrieve", action_type="bounded_retrieval", step_index=0, order_index=0, observation_status="observed", result_bucket="evidence_added", evidence_delta_bucket="delta_2_to_5", latency_bucket="lt_1s", failure_bucket="none", outcome_bucket="partial_bucket")
    return convert_row("phase5_product_workflow", old)


def fixture_rows(row_count: int = 60, episodes: int = 20) -> list[dict[str, Any]]:
    base = fixture_row()
    rows: list[dict[str, Any]] = []
    actions = ["expand_depth", "read_next", "validate_now", "stop"]
    for ep in range(episodes):
        for step in range(max(1, row_count // episodes)):
            row = copy.deepcopy(base)
            row["trace_id"] = private_ref("tracev2", str(ep))
            row["episode_id"] = row["trace_id"]
            row["step_index"] = step
            row["action"]["action_type"] = actions[step % len(actions)]
            row["action"]["target_question"] = {"expand_depth": "expand_depth?", "read_next": "read_next?", "validate_now": "validate_now?", "stop": "stop?"}[row["action"]["action_type"]]
            rows.append(row)
    return rows[:row_count]


def fixture_source_readbacks() -> dict[str, Any]:
    return {
        "benchmark_status": benchmark.STATUS_NO_LIFT,
        "failure_decomposition_status": decomp.STATUS_RETRIEVAL_REPAIR,
        "repair_design_status": design.STATUS_CONCRETE,
        "repair_prototype_status": repair_proto.STATUS_NO_LIFT,
        "repair_prototype_delta_vs_best": "negative_delta",
        "repair_prototype_privacy_gate": "passed",
        "rpm_trace_schema_status": "complete_schema_closure_only",
        "runtime_public_report_readback_only": True,
    }


def fixture_report() -> dict[str, Any]:
    rows = fixture_rows()
    manifest = {"private_input_confirmation": "confirmed", "private_output_confirmation": "confirmed", "source_count_bucket": "count_2_to_5", "input_row_count": len(rows), "input_episode_count": 20}
    report = build_report(rows, manifest)
    report["source_checkpoints_readbacks"] = fixture_source_readbacks()
    report["validation_summary"]["privacy_scan"] = "passed"
    # Real converted fixture still has legacy coverage gaps, so FRK-P2 is valid.
    report["status"] = STATUS_FRK_P2
    report["stop_go"]["authorized_next_phase"] = AUTH_FRK_P2
    report["stop_go"]["decision"] = "frk_p2_capture_expansion_for_tracev2_coverage_gaps_only"
    report["stop_go"]["haae_a2_replay_authorized"] = False
    report["stop_go"]["frk_p2_capture_expansion_authorized"] = True
    return report


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    def check(name: str, ok: bool) -> None:
        checks.append((name, ok))
    check("valid_v2_fixture", not validate_v2_rows(fixture_rows()))
    valid_report = fixture_report()
    check("valid_report_fixture", not validate_report(valid_report))
    check("unknown_critical_coverage_drives_frk_p2", valid_report["coverage_audit"]["critical_field_coverage_sufficient"] is False and valid_report["coverage_audit"]["coverage_gaps_dominate"] is True and valid_report["status"] == STATUS_FRK_P2)
    try:
        load_allowed_private_inputs(False)
        check("missing_private_input_confirmation_rejected", False)
    except TraceV2Error:
        check("missing_private_input_confirmation_rejected", True)
    try:
        run_bootstrap(True, False)
        check("missing_private_output_confirmation_rejected", False)
    except TraceV2Error:
        check("missing_private_output_confirmation_rejected", True)
    tmp = REPO / "artifacts" / "state_action_trace_v2_bootstrap" / "selftest_bad.jsonl"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp.write_text("{bad}\n", encoding="utf-8")
        try:
            read_jsonl(tmp)
            check("malformed_private_jsonl_rejected", False)
        except TraceV2Error:
            check("malformed_private_jsonl_rejected", True)
    finally:
        if tmp.exists():
            tmp.unlink()
    row_mutations: list[tuple[str, list[str], Any]] = [
        ("unknown_v2_top_level_key_rejected", ["unexpected"], True),
        ("missing_required_v2_group_rejected", ["task"], None),
        ("bad_action_enum_rejected", ["action", "action_type"], "bad"),
        ("duplicate_non_monotonic_step_rejected", ["duplicate_step"], True),
        ("missing_nested_state_subgroup_rejected", ["state", "candidate_pool"], None),
        ("unknown_nested_key_rejected", ["state", "candidate_pool", "unexpected"], "unknown"),
        ("nested_key_drift_rejected", ["action", "scope_bucket"], "scope_single_file"),
        ("label_before_action_rejected", ["outcome", "label_timing_isolated"], "false"),
        ("label_gold_in_state_action_rejected", ["state", "candidate_pool", "gold_label"], "success_bucket"),
        ("post_action_currentness_in_state_rejected", ["state", "evidence_state", "currentness_fail_seen"], "true"),
        ("invented_nonobservable_field_rejected", ["state", "uncertainty_state", "file_uncertainty_bucket"], "observed_file"),
        ("evidencecore_conflated_with_candidate_state_rejected", ["state", "candidate_pool", "content_sha"], "unknown"),
    ]
    for name, path, value in row_mutations:
        rows = fixture_rows(row_count=4, episodes=1)
        if path == ["task"]:
            rows[0].pop("task", None)
        elif path == ["duplicate_step"]:
            rows[1]["step_index"] = rows[0]["step_index"]
        elif value is None:
            target = rows[0]
            for key in path[:-1]:
                target = target[key]
            target.pop(path[-1], None)
        else:
            target = rows[0]
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        check(name, bool(validate_v2_rows(rows)))
    report_mutations: list[tuple[str, list[str], Any]] = [
        ("public_path_leak_rejected", ["source_checkpoints_readbacks", "rpm_trace_schema_status"], "/workspace/OpenLocus/OpenLocus-Lab/runs/x.jsonl"),
        ("public_query_leak_rejected", ["source_checkpoints_readbacks", "rpm_trace_schema_status"], "crates/openlocus-cli/src/lib.rs:1-2"),
        ("public_snippet_leak_rejected", ["source_checkpoints_readbacks", "rpm_trace_schema_status"], "snippet: fn main"),
        ("public_hash_content_sha_leak_rejected", ["source_checkpoints_readbacks", "rpm_trace_schema_status"], "a" * 64),
        ("public_private_ref_leak_rejected", ["source_checkpoints_readbacks", "rpm_trace_schema_status"], "private_ref_trace_abc"),
        ("raw_row_publication_rejected", ["source_checkpoints_readbacks", "rpm_trace_schema_status"], '{"schema_version":"openlocus.state_action_trace.v2"}'),
        ("exact_task_outcome_publication_rejected", ["source_checkpoints_readbacks", "rpm_trace_schema_status"], "wf02 success"),
        ("retrieval_read_validate_flag_rejected", ["execution_attestations", "retrieval_search_read_validate_executed"], True),
        ("candidate_generation_flag_rejected", ["execution_attestations", "new_candidates_generated"], True),
        ("source_scan_flag_rejected", ["execution_attestations", "source_scan_executed"], True),
        ("provider_flag_rejected", ["execution_attestations", "provider_or_model_calls_executed"], True),
        ("network_flag_rejected", ["execution_attestations", "network_access"], "network_allowed"),
        ("ci_flag_rejected", ["execution_attestations", "ci_execution"], "ci"),
        ("training_model_scaling_flag_rejected", ["execution_attestations", "training_or_model_fitting_executed"], True),
        ("runtime_default_flag_rejected", ["execution_attestations", "runtime_default_changed"], True),
        ("d2_authorization_rejected", ["stop_go", "rpm_d2_training_authorized"], True),
        ("haae_a2_authorization_insufficient_coverage_rejected", ["stop_go", "haae_a2_replay_authorized"], True),
        ("frk_p2_authorization_without_coverage_gaps_rejected", ["coverage_audit", "coverage_gaps_dominate"], False),
        ("frk_p2_authorization_schema_fail_rejected", ["tracev2_validation", "v2_schema_validation"], "failed"),
        ("unknown_report_key_rejected", ["unexpected"], True),
    ]
    for name, path, value in report_mutations:
        mutated = copy.deepcopy(valid_report)
        target = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        check(name, bool(validate_report(mutated)))
    haae_bad_family = copy.deepcopy(valid_report)
    haae_bad_family["status"] = STATUS_HAAE
    haae_bad_family["coverage_audit"]["critical_field_coverage_sufficient"] = True
    haae_bad_family["coverage_audit"]["coverage_gaps_dominate"] = False
    haae_bad_family["coverage_audit"]["task_family_coverage_bucket"] = "count_0"
    haae_bad_family["stop_go"]["authorized_next_phase"] = AUTH_HAAE
    haae_bad_family["stop_go"]["decision"] = "haae_a2_replay_over_existing_v2_rows_only"
    haae_bad_family["stop_go"]["haae_a2_replay_authorized"] = True
    haae_bad_family["stop_go"]["frk_p2_capture_expansion_authorized"] = False
    check("haae_a2_authorization_without_task_family_coverage_rejected", bool(validate_report(haae_bad_family)))
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_passed": len(checks) - len(failed), "checks_total": len(checks), "failed_checks": failed}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run-bootstrap", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            result = run_self_test()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.run_bootstrap:
            report = run_bootstrap(args.confirm_private_input, args.confirm_private_output)
            write_report(report)
            print(json.dumps({"public_report": str(DEFAULT_REPORT), "status": report["status"], "authorized_next_phase": report["stop_go"]["authorized_next_phase"]}, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = read_json(args.validate_report)
            errors = validate_report(report)
            if errors:
                raise TraceV2Error("public report validation failed: " + "; ".join(errors[:12]))
            print(f"Validation passed: {args.validate_report}")
            return 0
        report = default_report()
        write_report(report)
        print(json.dumps({"public_report": str(DEFAULT_REPORT), "status": report["status"], "mode": "default_unavailable_no_private_confirmations"}, indent=2, sort_keys=True))
        return 0
    except TraceV2Error as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
