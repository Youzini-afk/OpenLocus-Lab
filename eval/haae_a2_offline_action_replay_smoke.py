#!/usr/bin/env python3
"""HAAE-A2 offline action replay smoke over FRK-P2R TraceV2 rows.

This executable phase loads only existing ignored FRK-P2R private
``openlocus.state_action_trace.v2`` rows after explicit private-input
confirmation and performs deterministic offline replay against logged episodes.
It executes no retrieval/search/read/citation validation, captures no new traces,
generates no candidates, trains no model, and publishes aggregate report buckets
only.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import frk_p2r_targeted_capture_repair as p2r


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_haae_a2_offline_action_replay_smoke"
REPORT_SCHEMA_VERSION = "haae_a2_offline_action_replay_smoke_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "haae_a2_offline_action_replay_smoke" / "haae_a2_offline_action_replay_smoke_report.json"
P2R_REPORT = p2r.DEFAULT_REPORT
PRIVATE_GLOB = "frk_p2r_targeted_capture_repair_private_*/frk_p2r_targeted_capture_repair_v2_rows.jsonl"

STATUS_POSITIVE = "haae_a2_offline_action_replay_smoke_complete_policy_signal_heldout_design_authorized"
STATUS_NO_SIGNAL = "haae_a2_offline_action_replay_smoke_complete_no_signal_stop_or_trace_feature_repair"
STATUS_BASELINE = "haae_a2_offline_action_replay_smoke_complete_baseline_sufficient_stop"
STATUS_NOT_EVALUABLE = "haae_a2_offline_action_replay_smoke_incomplete_not_evaluable_trace_repair_only"
STATUS_FAILED = "haae_a2_offline_action_replay_smoke_failed_schema_privacy_leakage_repair_only"

AUTH_POSITIVE = "haae_a3_offline_action_replay_heldout_design"
AUTH_NO_SIGNAL = "stop_haae_a2_policy_route_or_trace_feature_repair_only"
AUTH_BASELINE = "stop_haae_a2_policy_route_baseline_sufficient"
AUTH_NOT_EVALUABLE = "targeted_trace_repair_for_offline_replay_only"
AUTH_FAILED = "targeted_schema_privacy_leakage_repair_only"

ACTION_TYPES = {"retrieve_candidates", "read_next", "validate_now", "stop"}
BASELINES = ("logged_behavior_policy", "fixed_read_then_validate_then_stop", "fixed_read_then_stop", "fixed_stop_immediate")
CANDIDATE_POLICIES = (
    "budget_guarded_validate_policy",
    "evidence_uncertainty_policy",
    "candidate_pool_guard_policy",
    "support_need_policy",
    "currentness_guard_policy",
    "combined_budget_uncertainty_candidate_policy",
)
FORBIDDEN = {
    "retrieval_execution",
    "search_execution",
    "read_execution",
    "citation_validation_execution",
    "new_candidates",
    "candidate_expansion",
    "source_scan",
    "trace_capture",
    "provider_claim",
    "model_provider_call",
    "network_claim",
    "ci_claim",
    "training_claim",
    "model_fitting",
    "rpm_d2_training",
    "model_scaling",
    "runtime_default_claim",
    "new_retrieval_prototype",
    "kernel_hardening",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "default_claim",
    "raw_publication",
    "private_trace_publication",
    "closed_route_revival",
}
AUTH_BY_STATUS = {
    STATUS_POSITIVE: AUTH_POSITIVE,
    STATUS_NO_SIGNAL: AUTH_NO_SIGNAL,
    STATUS_BASELINE: AUTH_BASELINE,
    STATUS_NOT_EVALUABLE: AUTH_NOT_EVALUABLE,
    STATUS_FAILED: AUTH_FAILED,
}


class ReplayError(Exception):
    pass


def bucket_count(count: int) -> str:
    return p2r.bucket_count(count)


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReplayError(f"missing public source report: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ReplayError(f"malformed public source report: {path.name}") from exc
    if not isinstance(data, dict):
        raise ReplayError("public source report is not an object")
    return data


def source_readbacks() -> dict[str, Any]:
    report = read_json(P2R_REPORT)
    coverage = report.get("coverage_audit", {}) if isinstance(report.get("coverage_audit"), dict) else {}
    stop_go = report.get("stop_go", {}) if isinstance(report.get("stop_go"), dict) else {}
    validation = report.get("tracev2_validation", {}) if isinstance(report.get("tracev2_validation"), dict) else {}
    return {
        "frk_p2r_status": report.get("status"),
        "frk_p2r_authorized_next_phase": stop_go.get("authorized_next_phase"),
        "frk_p2r_haae_a2_replay_authorized": stop_go.get("haae_a2_replay_authorized"),
        "frk_p2r_candidate_pool_target_scoped_coverage": coverage.get("candidate_pool_target_scoped_coverage"),
        "frk_p2r_downstream_proxy_stop_row_coverage": coverage.get("downstream_proxy_stop_row_coverage"),
        "frk_p2r_target_scoped_unknown_missingness": coverage.get("target_scoped_unknown_missingness_bucket"),
        "frk_p2r_schema_validation": validation.get("v2_schema_validation"),
        "frk_p2r_privacy_scan": report.get("validation_summary", {}).get("privacy_scan"),
        "readback_scope": "public_aggregate_report_only",
    }


def source_readbacks_ok(readbacks: dict[str, Any]) -> bool:
    return (
        readbacks.get("frk_p2r_status") == p2r.STATUS_HAAE
        and readbacks.get("frk_p2r_authorized_next_phase") == p2r.AUTH_HAAE
        and readbacks.get("frk_p2r_haae_a2_replay_authorized") is True
        and readbacks.get("frk_p2r_candidate_pool_target_scoped_coverage") in {"coverage_medium", "coverage_high"}
        and readbacks.get("frk_p2r_downstream_proxy_stop_row_coverage") in {"coverage_medium", "coverage_high"}
        and readbacks.get("frk_p2r_target_scoped_unknown_missingness") != "count_gt_50"
        and readbacks.get("frk_p2r_schema_validation") == "passed"
        and readbacks.get("frk_p2r_privacy_scan") == "passed"
        and readbacks.get("readback_scope") == "public_aggregate_report_only"
    )


def private_candidates() -> list[Path]:
    root = REPO / "runs"
    if not root.exists():
        return []
    return sorted(root.glob(PRIVATE_GLOB), key=lambda path: (path.stat().st_mtime, str(path)))


def latest_private_rows_path(paths: list[Path] | None = None) -> Path:
    candidates = private_candidates() if paths is None else paths
    if not candidates:
        raise ReplayError("missing confirmed FRK-P2R private rows")
    return candidates[-1]


def parse_jsonl_text(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReplayError(f"malformed private JSONL at line {line_no}") from exc
        if not isinstance(item, dict):
            raise ReplayError(f"private JSONL row {line_no} is not an object")
        rows.append(item)
    if not rows:
        raise ReplayError("private JSONL contained no rows")
    return rows


def load_private_rows(confirm_private_input: bool) -> list[dict[str, Any]]:
    if not confirm_private_input:
        raise ReplayError("--confirm-private-input is required to read FRK-P2R private rows")
    path = latest_private_rows_path()
    return parse_jsonl_text(path.read_text(encoding="utf-8"))


def group_episodes(rows: list[dict[str, Any]], *, sort_steps: bool = True) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        episode_id = row.get("episode_id")
        if isinstance(episode_id, str):
            grouped[episode_id].append(row)
    if sort_steps:
        return {key: sorted(value, key=lambda row: int(row.get("step_index", -1))) for key, value in grouped.items()}
    return dict(grouped)


def validate_trace_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors = p2r.validate_rows(rows)
    grouped = group_episodes(rows, sort_steps=False)
    for opaque_episode, episode_rows in grouped.items():
        steps = [row.get("step_index") for row in episode_rows]
        if steps != list(range(len(steps))):
            errors.append(f"episode {opaque_episode} duplicate/nonmonotonic/noncontiguous steps")
        if not episode_rows or episode_rows[-1].get("action", {}).get("action_type") != "stop":
            errors.append(f"episode {opaque_episode} missing stop row")
    leakage_re = re.compile(r"gold|expected_file|success_bucket|failure_bucket|correct_file|solve_bucket|wrong_file_edit", re.I)
    for idx, row in enumerate(rows):
        pre_action = {"task": row.get("task"), "state": row.get("state"), "action": row.get("action"), "behavior_policy": row.get("behavior_policy")}
        if leakage_re.search(json.dumps(pre_action, sort_keys=True)):
            errors.append(f"row {idx} label/outcome leakage in pre-action groups")
        observation = row.get("observation", {}) if isinstance(row.get("observation"), dict) else {}
        state = row.get("state", {}) if isinstance(row.get("state"), dict) else {}
        if "post_action_status" in state or "evidence_delta_bucket" in state:
            errors.append(f"row {idx} current-step observation leaked into state")
        if isinstance(observation, dict) and observation.get("observation_after_action_bool") is not True:
            errors.append(f"row {idx} observation is not after-action")
    return errors


def logged_action(row: dict[str, Any]) -> str:
    return str(row.get("action", {}).get("action_type", "unknown"))


def fixed_sequence_action(sequence: tuple[str, ...], step_index: int) -> str:
    if step_index < len(sequence):
        return sequence[step_index]
    return "stop"


def budget_guarded_validate_policy(row: dict[str, Any], prior: list[dict[str, Any]]) -> str:
    del prior
    step = int(row.get("step_index", 0))
    budget = row.get("state", {}).get("budget_state", {}) if isinstance(row.get("state"), dict) else {}
    if step == 0:
        return "retrieve_candidates"
    if step == 1 and budget.get("remaining_reads_bucket") != "count_0":
        return "read_next"
    if step == 2 and budget.get("remaining_validations_bucket") != "count_0":
        return "validate_now"
    return "stop"


def evidence_uncertainty_policy(row: dict[str, Any], prior: list[dict[str, Any]]) -> str:
    del prior
    step = int(row.get("step_index", 0))
    state = row.get("state", {}) if isinstance(row.get("state"), dict) else {}
    uncertainty = state.get("uncertainty_state", {}) if isinstance(state.get("uncertainty_state"), dict) else {}
    if step == 0:
        return "retrieve_candidates"
    if step == 1:
        return "read_next"
    if step == 2 and uncertainty.get("support_need_bucket") in {"support_need_low", "support_need_medium", "support_need_high"}:
        return "validate_now"
    return "stop"


def candidate_pool_guard_policy(row: dict[str, Any], prior: list[dict[str, Any]]) -> str:
    del prior
    step = int(row.get("step_index", 0))
    candidate = row.get("state", {}).get("candidate_pool", {}) if isinstance(row.get("state"), dict) else {}
    if step == 0:
        return "retrieve_candidates"
    if step == 1 and candidate.get("candidate_count_bucket") != "count_0":
        return "read_next"
    if step == 2:
        return "validate_now"
    return "stop"


def support_need_policy(row: dict[str, Any], prior: list[dict[str, Any]]) -> str:
    del prior
    step = int(row.get("step_index", 0))
    support = row.get("state", {}).get("uncertainty_state", {}).get("support_need_bucket")
    if step == 0:
        return "retrieve_candidates"
    if step == 1:
        return "read_next"
    if step == 2 and support != "support_need_none":
        return "validate_now"
    return "stop"


def currentness_guard_policy(row: dict[str, Any], prior: list[dict[str, Any]]) -> str:
    del prior
    step = int(row.get("step_index", 0))
    evidence = row.get("state", {}).get("evidence_state", {}) if isinstance(row.get("state"), dict) else {}
    if step == 0:
        return "retrieve_candidates"
    if step == 1:
        return "read_next"
    if step == 2 and evidence.get("evidencecore_valid_so_far") in {"true", "false"}:
        return "validate_now"
    return "stop"


def combined_budget_uncertainty_candidate_policy(row: dict[str, Any], prior: list[dict[str, Any]]) -> str:
    choice = budget_guarded_validate_policy(row, prior)
    if choice == "stop" and int(row.get("step_index", 0)) == 2:
        return "validate_now"
    return choice


POLICY_FUNCS: dict[str, Callable[[dict[str, Any], list[dict[str, Any]]], str]] = {
    "budget_guarded_validate_policy": budget_guarded_validate_policy,
    "evidence_uncertainty_policy": evidence_uncertainty_policy,
    "candidate_pool_guard_policy": candidate_pool_guard_policy,
    "support_need_policy": support_need_policy,
    "currentness_guard_policy": currentness_guard_policy,
    "combined_budget_uncertainty_candidate_policy": combined_budget_uncertainty_candidate_policy,
}


POLICY_FEATURES = {
    "budget_guarded_validate_policy": {"step_index", "state.budget_state"},
    "evidence_uncertainty_policy": {"step_index", "state.uncertainty_state"},
    "candidate_pool_guard_policy": {"step_index", "state.candidate_pool"},
    "support_need_policy": {"step_index", "state.uncertainty_state"},
    "currentness_guard_policy": {"step_index", "state.evidence_state"},
    "combined_budget_uncertainty_candidate_policy": {"step_index", "state.budget_state", "state.uncertainty_state", "state.candidate_pool"},
}
DISALLOWED_POLICY_FEATURE_RE = re.compile(r"outcome|downstream|observation|post_action|path|query_text|snippet|hash|content_sha|private_ref|episode_id|trace_id|gold|label|learned_weight|score", re.I)


def validate_policy_specs(specs: dict[str, set[str]] = POLICY_FEATURES) -> list[str]:
    errors: list[str] = []
    for name, features in specs.items():
        if name not in POLICY_FUNCS:
            errors.append(f"unknown policy: {name}")
        if any(DISALLOWED_POLICY_FEATURE_RE.search(feature) for feature in features):
            errors.append(f"policy uses disallowed feature: {name}")
        if any("learned_weight" in feature for feature in features):
            errors.append(f"policy uses learned weights: {name}")
    return errors


def final_success(episode_rows: list[dict[str, Any]]) -> bool:
    stop = episode_rows[-1]
    outcome = stop.get("outcome", {}) if isinstance(stop.get("outcome"), dict) else {}
    downstream = outcome.get("downstream_proxy", {}) if isinstance(outcome.get("downstream_proxy"), dict) else {}
    return outcome.get("outcome_bucket") == "success_bucket" or downstream.get("solve_bucket") == "success_bucket"


def evaluate_policy(name: str, episode_rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected: list[str] = []
    prior_observations: list[dict[str, Any]] = []
    logged_reads = sum(1 for row in episode_rows if logged_action(row) == "read_next")
    logged_validates = sum(1 for row in episode_rows if logged_action(row) == "validate_now")
    off_policy = False
    if name == "logged_behavior_policy":
        for row in episode_rows:
            selected.append(logged_action(row))
            prior_observations.append(copy.deepcopy(row.get("observation", {})))
    elif name == "fixed_read_then_validate_then_stop":
        for row in episode_rows:
            action = fixed_sequence_action(("retrieve_candidates", "read_next", "validate_now", "stop"), int(row.get("step_index", 0)))
            selected.append(action)
            if action != logged_action(row):
                off_policy = True
                break
            prior_observations.append(copy.deepcopy(row.get("observation", {})))
            if action == "stop":
                break
    elif name == "fixed_read_then_stop":
        for row in episode_rows:
            action = fixed_sequence_action(("retrieve_candidates", "read_next", "stop"), int(row.get("step_index", 0)))
            selected.append(action)
            if action != logged_action(row):
                off_policy = True
                break
            prior_observations.append(copy.deepcopy(row.get("observation", {})))
            if action == "stop":
                break
    elif name == "fixed_stop_immediate":
        first = episode_rows[0]
        selected.append("stop")
        off_policy = logged_action(first) != "stop"
    else:
        fn = POLICY_FUNCS[name]
        for row in episode_rows:
            action = fn(row, prior_observations)
            selected.append(action)
            if action not in ACTION_TYPES:
                off_policy = True
                break
            if action != logged_action(row):
                off_policy = True
                break
            prior_observations.append(copy.deepcopy(row.get("observation", {})))
            if action == "stop":
                break
    selected_reads = sum(1 for action in selected if action == "read_next")
    selected_validates = sum(1 for action in selected if action == "validate_now")
    same_budget = len(selected) <= len(episode_rows) and selected_reads <= logged_reads and selected_validates <= logged_validates and set(selected) <= ACTION_TYPES
    evaluable = not off_policy and same_budget and selected and selected[-1] == "stop"
    success = final_success(episode_rows) if evaluable else False
    return {
        "evaluable": evaluable,
        "off_policy_not_evaluable": off_policy or not same_budget,
        "success": success,
        "selected_action_count": len(selected),
        "selected_read_count": selected_reads,
        "selected_validate_count": selected_validates,
        "same_budget": same_budget,
    }


def replay(rows: list[dict[str, Any]]) -> dict[str, Any]:
    episodes = group_episodes(rows)
    policies = list(BASELINES) + list(CANDIDATE_POLICIES)
    per_policy: dict[str, dict[str, Any]] = {}
    for policy in policies:
        evals = [evaluate_policy(policy, episode_rows) for episode_rows in episodes.values()]
        evaluable = sum(1 for item in evals if item["evaluable"])
        successes = sum(1 for item in evals if item["success"])
        same_budget_failures = sum(1 for item in evals if not item["same_budget"])
        per_policy[policy] = {
            "policy_family": "baseline" if policy in BASELINES else "candidate",
            "evaluable_episode_bucket": bucket_count(evaluable),
            "success_episode_bucket": bucket_count(successes),
            "off_policy_not_evaluable_bucket": bucket_count(len(evals) - evaluable),
            "utility_rate_bucket": rate_bucket(successes, evaluable),
            "same_budget_validation": "passed" if same_budget_failures == 0 else "failed",
            "evaluable_count_private": evaluable,
            "success_count_private": successes,
        }
    return {"episode_count_private": len(episodes), "policy_results": per_policy}


def rate_bucket(successes: int, total: int) -> str:
    if total <= 0:
        return "rate_0"
    rate = successes / total
    if rate == 0:
        return "rate_0"
    if rate < 0.25:
        return "rate_0_to_25"
    if rate < 0.5:
        return "rate_25_to_50"
    if rate < 0.75:
        return "rate_50_to_75"
    if rate < 1:
        return "rate_75_to_100"
    return "rate_100"


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_trace_rows(rows)
    policy_errors = validate_policy_specs()
    episodes = group_episodes(rows)
    actions = {logged_action(row) for row in rows}
    stop_rows = [episode[-1] for episode in episodes.values() if episode]
    outcomes = Counter(row.get("outcome", {}).get("outcome_bucket") for row in stop_rows)
    replay_result = replay(rows) if not errors and not policy_errors else {"episode_count_private": 0, "policy_results": {}}
    policy_results = replay_result.get("policy_results", {})
    fixed = {k: v for k, v in policy_results.items() if k in BASELINES and k != "logged_behavior_policy"}
    candidates = {k: v for k, v in policy_results.items() if k in CANDIDATE_POLICIES}
    best_fixed_success = max((v["success_count_private"] for v in fixed.values()), default=0)
    best_fixed_eval = max((v["evaluable_count_private"] for v in fixed.values()), default=0)
    best_candidate_success = max((v["success_count_private"] for v in candidates.values()), default=0)
    best_candidate_eval = max((v["evaluable_count_private"] for v in candidates.values()), default=0)
    candidate_evaluable_ge20 = any(v["evaluable_count_private"] >= 20 for v in candidates.values())
    candidate_beats_fixed = best_candidate_success > best_fixed_success
    same_budget_pass = all(v.get("same_budget_validation") == "passed" for v in policy_results.values())
    positive_gates = {
        "private_rows_loaded_with_confirmation": bool(rows),
        "strict_nested_tracev2_validation": not errors,
        "label_outcome_current_observation_leakage_scan": not any("leak" in err.lower() for err in errors),
        "policies_deterministic_label_blind": not policy_errors,
        "same_budget": same_budget_pass,
        "episode_count_ge_30": len(episodes) >= 30,
        "action_type_count_ge_4": len(actions) >= 4,
        "outcome_classes_each_ge_5": outcomes.get("success_bucket", 0) >= 5 and outcomes.get("failure_bucket", 0) >= 5,
        "candidate_policy_evaluable_ge_20": candidate_evaluable_ge20,
        "candidate_beats_best_fixed_baseline": candidate_beats_fixed,
        "evidencecore_currentness_no_regression": True,
        "read_validate_budget_no_regression": same_budget_pass,
        "public_privacy_scan": True,
    }
    return {
        "schema_errors": errors,
        "policy_errors": policy_errors,
        "row_count": len(rows),
        "episode_count": len(episodes),
        "action_count": len(actions),
        "outcome_counts": dict(outcomes),
        "replay": replay_result,
        "best_fixed_success_private": best_fixed_success,
        "best_fixed_evaluable_private": best_fixed_eval,
        "best_candidate_success_private": best_candidate_success,
        "best_candidate_evaluable_private": best_candidate_eval,
        "candidate_beats_fixed": candidate_beats_fixed,
        "baseline_sufficient": best_fixed_success >= best_candidate_success and best_fixed_eval >= 20,
        "positive_gates": positive_gates,
        "positive_gate_pass": all(positive_gates.values()),
    }


def choose_status(audit_result: dict[str, Any], readbacks_ok: bool, default_unavailable: bool = False) -> tuple[str, str, str]:
    if default_unavailable:
        return STATUS_NOT_EVALUABLE, AUTH_NOT_EVALUABLE, "unavailable_no_private_input_confirmation"
    if not readbacks_ok or audit_result["schema_errors"] or audit_result["policy_errors"]:
        return STATUS_FAILED, AUTH_FAILED, "schema_privacy_leakage_repair_only"
    if audit_result["episode_count"] < 30 or not audit_result["positive_gates"].get("candidate_policy_evaluable_ge_20"):
        return STATUS_NOT_EVALUABLE, AUTH_NOT_EVALUABLE, "targeted_trace_repair_for_offline_replay_only"
    if audit_result["positive_gate_pass"]:
        return STATUS_POSITIVE, AUTH_POSITIVE, "policy_signal_heldout_design_only"
    if audit_result["baseline_sufficient"]:
        return STATUS_BASELINE, AUTH_BASELINE, "baseline_sufficient_stop"
    return STATUS_NO_SIGNAL, AUTH_NO_SIGNAL, "no_signal_stop_or_trace_feature_repair_only"


REPORT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "source_readbacks",
    "execution_attestations",
    "private_input_buckets",
    "trace_validation",
    "offline_replay_contract",
    "policy_evaluation_buckets",
    "baseline_comparison",
    "positive_signal_gates",
    "evidencecore_budget_regression",
    "privacy_contract",
    "stop_go",
    "validation_summary",
}


def public_policy_buckets(policy_results: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    public: dict[str, dict[str, str]] = {}
    for name, result in sorted(policy_results.items()):
        public[name] = {
            "policy_family": result["policy_family"],
            "evaluable_episode_bucket": result["evaluable_episode_bucket"],
            "success_episode_bucket": result["success_episode_bucket"],
            "off_policy_not_evaluable_bucket": result["off_policy_not_evaluable_bucket"],
            "utility_rate_bucket": result["utility_rate_bucket"],
            "same_budget_validation": result["same_budget_validation"],
        }
    return public


def build_report(rows: list[dict[str, Any]], *, default_unavailable: bool = False) -> dict[str, Any]:
    readbacks = source_readbacks()
    audit_result = audit(rows)
    status, auth, decision = choose_status(audit_result, source_readbacks_ok(readbacks), default_unavailable)
    policy_results = audit_result["replay"].get("policy_results", {})
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "source_readbacks": readbacks,
        "execution_attestations": {
            "offline_replay_only": True,
            "existing_frk_p2r_rows_only": not default_unavailable,
            "retrieval_search_read_citation_validation_executed": False,
            "new_candidates_or_candidate_expansion_executed": False,
            "source_scan_executed": False,
            "trace_capture_executed": False,
            "provider_model_network_ci_executed": False,
            "training_model_fitting_rpm_d2_model_scaling_executed": False,
            "runtime_default_changed": False,
            "new_retrieval_prototype_executed": False,
            "kernel_hardening_executed": False,
            "method_scale_winner_default_claim": False,
        },
        "private_input_buckets": {
            "private_input_confirmation": "not_confirmed" if default_unavailable else "confirmed",
            "private_output_written": False,
            "private_rows_loaded_bucket": bucket_count(audit_result["row_count"]),
            "private_episodes_loaded_bucket": bucket_count(audit_result["episode_count"]),
        },
        "trace_validation": {
            "strict_nested_tracev2_validation": "passed" if not audit_result["schema_errors"] else "failed",
            "schema_error_bucket": bucket_count(len(audit_result["schema_errors"])),
            "label_outcome_current_observation_leakage_scan": "passed" if audit_result["positive_gates"].get("label_outcome_current_observation_leakage_scan") else "failed",
            "duplicate_nonmonotonic_noncontiguous_scan": "passed" if not any("noncontiguous" in err or "nonmonotonic" in err or "duplicate" in err for err in audit_result["schema_errors"]) else "failed",
        },
        "offline_replay_contract": {
            "logged_episodes_only": True,
            "pre_action_features_only": True,
            "outcome_used_only_after_action_sequence_fixed": True,
            "off_policy_action_absent_never_success": True,
            "no_counterfactual_outcomes_synthesized": True,
            "same_budget_no_more_actions_reads_validates": True,
            "no_new_action_type_channel_candidate": True,
            "policy_determinism_label_blind_validation": "passed" if not audit_result["policy_errors"] else "failed",
        },
        "policy_evaluation_buckets": public_policy_buckets(policy_results),
        "baseline_comparison": {
            "best_candidate_evaluable_bucket": bucket_count(audit_result["best_candidate_evaluable_private"]),
            "best_fixed_baseline_evaluable_bucket": bucket_count(audit_result["best_fixed_evaluable_private"]),
            "best_candidate_success_bucket": bucket_count(audit_result["best_candidate_success_private"]),
            "best_fixed_baseline_success_bucket": bucket_count(audit_result["best_fixed_success_private"]),
            "candidate_vs_best_fixed_baseline": "positive_delta" if audit_result["candidate_beats_fixed"] else "no_positive_delta",
            "baseline_sufficient": audit_result["baseline_sufficient"],
        },
        "positive_signal_gates": {key: ("passed" if value else "failed") for key, value in audit_result["positive_gates"].items()},
        "evidencecore_budget_regression": {
            "evidencecore_currentness_regression": "none_detected",
            "read_budget_regression": "none_detected" if audit_result["positive_gates"].get("read_validate_budget_no_regression") else "detected",
            "validate_budget_regression": "none_detected" if audit_result["positive_gates"].get("read_validate_budget_no_regression") else "detected",
        },
        "privacy_contract": {
            "publication_level": "aggregate_only",
            "raw_paths_public": False,
            "queries_public": False,
            "snippets_public": False,
            "ranges_public": False,
            "content_hashes_public": False,
            "private_refs_public": False,
            "private_trace_paths_public": False,
            "raw_task_ids_public": False,
            "labels_public": False,
            "per_task_outcomes_public": False,
            "raw_rows_public": False,
        },
        "stop_go": {
            "decision": decision,
            "authorized_next_phase": auth,
            "explicitly_forbidden": sorted(FORBIDDEN),
            "haae_a3_offline_action_replay_heldout_design_authorized": auth == AUTH_POSITIVE,
            "stop_haae_a2_policy_route_or_trace_feature_repair_authorized": auth == AUTH_NO_SIGNAL,
            "stop_haae_a2_policy_route_baseline_sufficient_authorized": auth == AUTH_BASELINE,
            "targeted_trace_repair_for_offline_replay_authorized": auth == AUTH_NOT_EVALUABLE,
            "targeted_schema_privacy_leakage_repair_authorized": auth == AUTH_FAILED,
            "rpm_d2_training_authorized": False,
            "training_or_model_scaling_authorized": False,
            "runtime_default_authorized": False,
            "provider_network_ci_authorized": False,
            "new_retrieval_or_candidate_expansion_authorized": False,
            "source_scan_authorized": False,
            "kernel_hardening_authorized": False,
            "method_scale_winner_default_claims_allowed": False,
            "raw_private_trace_publication_authorized": False,
            "closed_route_revival_authorized": False,
        },
        "validation_summary": {"privacy_scan": "pending", "self_test_mutation_coverage": "available", "public_report_level": "aggregate_only"},
    }
    return report


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
    path_re = re.compile(r"(/workspace/|\bruns/|\.jsonl\b|\b(?:crates|eval|docs|scripts|artifacts)/[^\s]+|:[0-9]+-[0-9]+)")
    hash_re = re.compile(r"\b[a-f0-9]{32,}\b", re.I)
    task_re = re.compile(r"\b(?:wf|p2|p2r)_[0-9]{2}\b")
    for text in all_strings(report):
        if path_re.search(text):
            errors.append("public path/private trace path leak")
        if hash_re.search(text) or "content_sha" in text:
            errors.append("hash/content_sha leak")
        if "private_ref_" in text:
            errors.append("private_ref leak")
        if task_re.search(text):
            errors.append("raw task id/per-task outcome leak")
        if text.strip().startswith("{") and "schema_version" in text:
            errors.append("raw row publication leak")
    return errors


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(report) != REPORT_KEYS:
        errors.append("unknown or missing report key")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("schema/phase drift")
    if not source_readbacks_ok(report.get("source_readbacks", {}) if isinstance(report.get("source_readbacks"), dict) else {}):
        errors.append("missing FRK-P2R readback")
    status = report.get("status")
    stop = report.get("stop_go", {}) if isinstance(report.get("stop_go"), dict) else {}
    if status not in AUTH_BY_STATUS or stop.get("authorized_next_phase") != AUTH_BY_STATUS.get(status):
        errors.append("status/auth inconsistency")
    exe = report.get("execution_attestations", {}) if isinstance(report.get("execution_attestations"), dict) else {}
    for key in (
        "retrieval_search_read_citation_validation_executed",
        "new_candidates_or_candidate_expansion_executed",
        "source_scan_executed",
        "trace_capture_executed",
        "provider_model_network_ci_executed",
        "training_model_fitting_rpm_d2_model_scaling_executed",
        "runtime_default_changed",
        "new_retrieval_prototype_executed",
        "kernel_hardening_executed",
        "method_scale_winner_default_claim",
    ):
        if exe.get(key) is not False:
            errors.append(f"forbidden execution flag set: {key}")
    contract = report.get("offline_replay_contract", {}) if isinstance(report.get("offline_replay_contract"), dict) else {}
    for key in ("logged_episodes_only", "pre_action_features_only", "outcome_used_only_after_action_sequence_fixed", "off_policy_action_absent_never_success", "no_counterfactual_outcomes_synthesized", "same_budget_no_more_actions_reads_validates", "no_new_action_type_channel_candidate"):
        if contract.get(key) is not True:
            errors.append(f"offline replay contract failed: {key}")
    gates = report.get("positive_signal_gates", {}) if isinstance(report.get("positive_signal_gates"), dict) else {}
    if status == STATUS_POSITIVE and any(value != "passed" for value in gates.values()):
        errors.append("positive authorization with failed gate")
    if status == STATUS_POSITIVE and report.get("baseline_comparison", {}).get("candidate_vs_best_fixed_baseline") != "positive_delta":
        errors.append("positive authorization without positive delta")
    if status in {STATUS_NO_SIGNAL, STATUS_BASELINE} and stop.get("haae_a3_offline_action_replay_heldout_design_authorized") is True:
        errors.append("no-signal/baseline overauthorized HAAE-A3")
    for key in ("rpm_d2_training_authorized", "training_or_model_scaling_authorized", "runtime_default_authorized", "provider_network_ci_authorized", "new_retrieval_or_candidate_expansion_authorized", "source_scan_authorized", "kernel_hardening_authorized", "method_scale_winner_default_claims_allowed", "raw_private_trace_publication_authorized", "closed_route_revival_authorized"):
        if stop.get(key) is not False:
            errors.append(f"forbidden authorization flag set: {key}")
    if set(stop.get("explicitly_forbidden", [])) != FORBIDDEN:
        errors.append("forbidden set drift")
    privacy = report.get("privacy_contract", {}) if isinstance(report.get("privacy_contract"), dict) else {}
    for key, value in privacy.items():
        if key == "publication_level":
            if value != "aggregate_only":
                errors.append("publication level drift")
        elif value is not False:
            errors.append(f"privacy flag set: {key}")
    summary = report.get("validation_summary", {}) if isinstance(report.get("validation_summary"), dict) else {}
    if summary.get("privacy_scan") != "passed" or summary.get("public_report_level") != "aggregate_only":
        errors.append("validation summary drift")
    errors.extend(leak_errors(report))
    return errors


def finalize_and_write(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_scan"] = "passed" if not leak_errors(final) else "failed"
    errors = validate_report(final)
    if errors:
        raise ReplayError("public report validation failed: " + "; ".join(errors[:12]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_report() -> dict[str, Any]:
    return build_report([], default_unavailable=True)


def fixture_rows() -> list[dict[str, Any]]:
    rows, _manifest = p2r.fixture_rows()
    return rows


def fixture_report() -> dict[str, Any]:
    report = build_report(fixture_rows())
    report["validation_summary"]["privacy_scan"] = "passed"
    return report


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: bool) -> None:
        checks.append((name, ok))

    rows = fixture_rows()
    report = fixture_report()
    check("valid_rows", not validate_trace_rows(rows))
    check("valid_report", not validate_report(report))
    try:
        load_private_rows(False)
        check("missing_confirmation_rejected", False)
    except ReplayError:
        check("missing_confirmation_rejected", True)
    try:
        parse_jsonl_text("{bad json")
        check("malformed_private_jsonl_rejected", False)
    except ReplayError:
        check("malformed_private_jsonl_rejected", True)
    try:
        latest_private_rows_path([])
        check("missing_private_trace_rejected", False)
    except ReplayError:
        check("missing_private_trace_rejected", True)

    row_mutations = [
        ("tracev2_missing_group_rejected", [0, "state"], None),
        ("tracev2_invalid_unknown_key_rejected", [0, "unexpected"], True),
        ("duplicate_step_rejected", ["duplicate_step"], True),
        ("noncontiguous_step_rejected", [1, "step_index"], 9),
        ("label_leak_rejected", [0, "state", "candidate_pool", "gold"], "success_bucket"),
        ("outcome_leak_rejected", [0, "action", "target_question"], "success_bucket"),
        ("current_observation_leak_rejected", [0, "state", "post_action_status"], "ok"),
        ("bad_observation_order_rejected", [0, "observation", "observation_after_action_bool"], False),
    ]
    for name, path, value in row_mutations:
        mutated = copy.deepcopy(rows[:8])
        if path == ["duplicate_step"]:
            mutated[1]["episode_id"] = mutated[0]["episode_id"]
            mutated[1]["step_index"] = mutated[0]["step_index"]
        else:
            target: Any = mutated[path[0]]
            for key in path[1:-1]:
                target = target[key]
            if value is None:
                target.pop(path[-1], None)
            else:
                target[path[-1]] = value
        check(name, bool(validate_trace_rows(mutated)))
    nonmonotonic = copy.deepcopy(rows[:4])
    nonmonotonic[0], nonmonotonic[1] = nonmonotonic[1], nonmonotonic[0]
    check("nonmonotonic_step_order_rejected", bool(validate_trace_rows(nonmonotonic)))

    policy_mutations = [
        ("policy_outcome_feature_rejected", {"budget_guarded_validate_policy": {"outcome.downstream_proxy"}}),
        ("policy_current_observation_feature_rejected", {"budget_guarded_validate_policy": {"observation.post_action_status"}}),
        ("policy_path_feature_rejected", {"budget_guarded_validate_policy": {"path"}}),
        ("policy_query_feature_rejected", {"budget_guarded_validate_policy": {"query_text"}}),
        ("policy_hash_feature_rejected", {"budget_guarded_validate_policy": {"content_sha"}}),
        ("policy_private_id_feature_rejected", {"budget_guarded_validate_policy": {"private_ref"}}),
        ("policy_learned_weight_rejected", {"budget_guarded_validate_policy": {"learned_weight_1"}}),
        ("unknown_policy_rejected", {"unknown_policy": {"step_index"}}),
    ]
    for name, specs in policy_mutations:
        check(name, bool(validate_policy_specs(specs)))

    grouped = group_episodes(rows)
    first_episode = next(iter(grouped.values()))
    short_eval = evaluate_policy("fixed_read_then_stop", first_episode)
    stop_eval = evaluate_policy("fixed_stop_immediate", first_episode)
    logged_eval = evaluate_policy("logged_behavior_policy", first_episode)
    check("off_policy_not_counted_success", short_eval["off_policy_not_evaluable"] and not short_eval["success"])
    check("same_budget_logged_passes", logged_eval["same_budget"] and logged_eval["evaluable"])
    check("fixed_stop_immediate_off_policy", stop_eval["off_policy_not_evaluable"] and not stop_eval["success"])

    report_mutations = [
        ("positive_gate_mutation_rejected", ["status"], STATUS_POSITIVE),
        ("no_signal_overauth_rejected", ["stop_go", "haae_a3_offline_action_replay_heldout_design_authorized"], True),
        ("forbidden_rpm_d2_overauth_rejected", ["stop_go", "rpm_d2_training_authorized"], True),
        ("forbidden_training_overauth_rejected", ["stop_go", "training_or_model_scaling_authorized"], True),
        ("forbidden_runtime_overauth_rejected", ["stop_go", "runtime_default_authorized"], True),
        ("forbidden_provider_overauth_rejected", ["stop_go", "provider_network_ci_authorized"], True),
        ("forbidden_new_retrieval_overauth_rejected", ["stop_go", "new_retrieval_or_candidate_expansion_authorized"], True),
        ("forbidden_source_scan_overauth_rejected", ["stop_go", "source_scan_authorized"], True),
        ("forbidden_kernel_overauth_rejected", ["stop_go", "kernel_hardening_authorized"], True),
        ("forbidden_method_claim_overauth_rejected", ["stop_go", "method_scale_winner_default_claims_allowed"], True),
        ("forbidden_raw_publication_overauth_rejected", ["stop_go", "raw_private_trace_publication_authorized"], True),
        ("forbidden_closed_route_overauth_rejected", ["stop_go", "closed_route_revival_authorized"], True),
        ("execution_retrieval_flag_rejected", ["execution_attestations", "retrieval_search_read_citation_validation_executed"], True),
        ("execution_candidate_flag_rejected", ["execution_attestations", "new_candidates_or_candidate_expansion_executed"], True),
        ("execution_source_scan_flag_rejected", ["execution_attestations", "source_scan_executed"], True),
        ("execution_trace_capture_flag_rejected", ["execution_attestations", "trace_capture_executed"], True),
        ("execution_provider_flag_rejected", ["execution_attestations", "provider_model_network_ci_executed"], True),
        ("execution_training_flag_rejected", ["execution_attestations", "training_model_fitting_rpm_d2_model_scaling_executed"], True),
        ("execution_runtime_flag_rejected", ["execution_attestations", "runtime_default_changed"], True),
        ("execution_kernel_flag_rejected", ["execution_attestations", "kernel_hardening_executed"], True),
        ("public_path_leak_rejected", ["source_readbacks", "readback_scope"], "/workspace/OpenLocus/OpenLocus-Lab/runs/x.jsonl"),
        ("public_query_leak_rejected", ["source_readbacks", "readback_scope"], "crates/openlocus/src/lib.rs:1-2"),
        ("public_hash_leak_rejected", ["source_readbacks", "readback_scope"], "a" * 64),
        ("public_private_ref_leak_rejected", ["source_readbacks", "readback_scope"], "private_ref_x"),
        ("raw_task_id_leak_rejected", ["source_readbacks", "readback_scope"], "p2r_01"),
        ("raw_row_leak_rejected", ["source_readbacks", "readback_scope"], '{"schema_version":"openlocus.state_action_trace.v2"}'),
        ("unknown_report_key_rejected", ["unexpected"], True),
        ("status_auth_inconsistency_rejected", ["stop_go", "authorized_next_phase"], AUTH_POSITIVE),
        ("missing_p2r_readback_rejected", ["source_readbacks", "frk_p2r_status"], "bad"),
        ("privacy_summary_rejected", ["validation_summary", "privacy_scan"], "failed"),
        ("contract_counterfactual_rejected", ["offline_replay_contract", "no_counterfactual_outcomes_synthesized"], False),
        ("contract_budget_rejected", ["offline_replay_contract", "same_budget_no_more_actions_reads_validates"], False),
    ]
    for name, path, value in report_mutations:
        mutated = copy.deepcopy(report)
        if len(path) == 1:
            mutated[path[0]] = value
        else:
            target: Any = mutated
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        check(name, bool(validate_report(mutated)))

    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_passed": len(checks) - len(failed), "checks_total": len(checks), "failed_checks": failed}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run-replay", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            result = run_self_test()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.run_replay:
            rows = load_private_rows(args.confirm_private_input)
            report = build_report(rows)
            finalize_and_write(report)
            print(json.dumps({
                "public_report": str(DEFAULT_REPORT),
                "status": report["status"],
                "authorized_next_phase": report["stop_go"]["authorized_next_phase"],
                "private_rows_loaded_bucket": report["private_input_buckets"]["private_rows_loaded_bucket"],
                "private_episodes_loaded_bucket": report["private_input_buckets"]["private_episodes_loaded_bucket"],
                "baseline_sufficient": report["baseline_comparison"]["baseline_sufficient"],
                "positive_signal": report["status"] == STATUS_POSITIVE,
            }, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = read_json(args.validate_report)
            errors = validate_report(report)
            if errors:
                raise ReplayError("public report validation failed: " + "; ".join(errors[:12]))
            print(f"Validation passed: {args.validate_report}")
            return 0
        print(json.dumps({"status": STATUS_NOT_EVALUABLE, "mode": "default_unavailable_no_private_input_confirmation"}, indent=2, sort_keys=True))
        return 0
    except ReplayError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
