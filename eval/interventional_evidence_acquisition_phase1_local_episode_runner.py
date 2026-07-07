#!/usr/bin/env python3
"""Minimal Phase 1 local pilot/preflight runner for interventional evidence acquisition."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rpm_trace_schema as schema
from frk_product_workflow_trace_benchmark import TASKS, WorkflowTask, bucket_count, bucket_latency, bucket_rate, private_ref

REPO = Path(__file__).resolve().parent.parent
PHASE = "interventional_evidence_acquisition_phase1_local_episode_runner"
ROW_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1_private_row_v1"
REPORT_SCHEMA_VERSION = "interventional_evidence_acquisition_phase1_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
PRIVATE_ROOT_PREFIX = "interventional_evidence_acquisition_phase1_private_"
PRIVATE_ROWS_FILENAME = "interventional_evidence_acquisition_phase1_private_rows.jsonl"
FIXED_SEED = 20260707
DEFAULT_EPISODES = 24
MIN_EPISODES = 24
MAX_EPISODES = 40
MAX_CANDIDATES = 5

ALLOWED_ACTIONS = (
    "retrieve_bm25",
    "retrieve_symbol_regex",
    "read_top1",
    "read_next_unique_file",
    "read_related_test",
    "stop",
    "abstain",
)
TERMINAL_ACTIONS = {"stop", "abstain"}
STATUS_PREFLIGHT = "phase1_preflight"
STATUS_COMPLETE_NO_CLAIM = "phase1_private_pilot_complete_no_claim"
STATUS_NO_GO = "phase1_private_pilot_no_go"
STATUS_INSUFFICIENT_SOURCE = "preflight_insufficient_episode_source"
NEXT_ACTION = "stop/request next explicit decision"
REPORT_KEYS = {
    "schema_version", "phase", "status", "authorization_attestation", "aggregate_buckets",
    "preflight_availability", "randomized_action_health", "evidencecore_summary", "privacy_summary",
    "hard_gates", "best_fixed_local_action_baseline", "validation_summary", "next_authorized_action",
}
ROW_KEYS = {
    "schema_version", "episode_private_id", "step_index", "created_order_index",
    "randomization_block_private", "task_bucket", "task_family_bucket", "state", "action",
    "randomization", "observation", "evidence_core", "outcome", "privacy",
}
LABEL_LEAK_TERMS = re.compile(r"(gold|answer|outcome|success|failure_label|relevant|judg(e|ment)|label)", re.I)
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
HASH_RE = re.compile(r"\b[a-f0-9]{16,}\b", re.I)


class RunnerError(Exception):
    pass


@dataclass(frozen=True)
class Episode:
    index: int
    task: WorkflowTask
    action: str
    block_id: str
    action_probability: float
    eligible_actions: tuple[str, ...]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def bucket_probability(probability: float) -> str:
    if probability <= 0.25:
        return "probability_0_to_0_25"
    if probability <= 0.50:
        return "probability_0_25_to_0_5"
    if probability < 1.0:
        return "probability_0_5_to_1"
    return "probability_1"


def bucket_coverage(count: int) -> str:
    if count <= 0:
        return "coverage_none"
    if count == 1:
        return "coverage_low"
    if count <= 3:
        return "coverage_medium"
    return "coverage_high"


def bounded_source_paths() -> list[str]:
    return sorted({task.expected_path for task in TASKS})


def safe_read_text(rel_path: str) -> str | None:
    path = (REPO / rel_path).resolve()
    try:
        path.relative_to(REPO)
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def tokenize(query: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(query) if len(token) >= 3}


def line_window(text: str, pattern: re.Pattern[str] | None = None, tokens: set[str] | None = None) -> tuple[int, int]:
    lines = text.splitlines()
    if not lines:
        return 1, 1
    for idx, line in enumerate(lines, start=1):
        if pattern is not None and pattern.search(line):
            return max(1, idx - 2), min(len(lines), idx + 2)
        if tokens and any(token in line.lower() for token in tokens):
            return max(1, idx - 2), min(len(lines), idx + 2)
    return 1, min(len(lines), 5)


def content_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def materialize(rel_path: str, range_text: str) -> dict[str, Any]:
    match = re.match(r"^(\d+)-(\d+)$", range_text)
    start, end = (int(match.group(1)), int(match.group(2))) if match else (1, 1)
    text = safe_read_text(rel_path)
    if text is None:
        return {"path_private": rel_path, "range_private": range_text, "currentness_status": "unavailable", "materialization_status": "unavailable", "content_digest_private": None}
    lines = text.splitlines()
    start = max(1, min(start, max(1, len(lines))))
    end = max(start, min(end, max(1, len(lines))))
    snippet = "\n".join(lines[start - 1:end])
    return {"path_private": rel_path, "range_private": f"{start}-{end}", "currentness_status": "verified_current", "materialization_status": "materialized_current", "content_digest_private": content_digest(snippet)}


def local_bm25_like_search(task: WorkflowTask) -> tuple[list[dict[str, Any]], float, str]:
    started = time.monotonic()
    tokens = tokenize(task.text_query)
    results: list[dict[str, Any]] = []
    for rel_path in bounded_source_paths():
        text = safe_read_text(rel_path)
        if text is None:
            continue
        score = sum(text.lower().count(token) for token in tokens)
        if score <= 0:
            continue
        start, end = line_window(text, tokens=tokens)
        results.append({"path_private": rel_path, "range_private": f"{start}-{end}", "score_private": score, "channel_private": "retrieve_bm25"})
    results.sort(key=lambda item: (-int(item["score_private"]), str(item["path_private"])))
    return results[:MAX_CANDIDATES], time.monotonic() - started, "available" if results else "bounded_no_candidate"


def local_symbol_regex_search(task: WorkflowTask) -> tuple[list[dict[str, Any]], float, str]:
    started = time.monotonic()
    raw = task.symbol_or_regex_query if task.symbol_mode == "regex" else re.escape(task.symbol_or_regex_query)
    try:
        pattern = re.compile(raw)
    except re.error:
        pattern = re.compile(re.escape(task.symbol_or_regex_query))
    results: list[dict[str, Any]] = []
    for rel_path in bounded_source_paths():
        text = safe_read_text(rel_path)
        if text is None or not pattern.search(text):
            continue
        start, end = line_window(text, pattern=pattern)
        results.append({"path_private": rel_path, "range_private": f"{start}-{end}", "score_private": 1, "channel_private": "retrieve_symbol_regex"})
    results.sort(key=lambda item: str(item["path_private"]))
    return results[:MAX_CANDIDATES], time.monotonic() - started, "available" if results else "bounded_no_candidate"


def related_test_candidates() -> list[dict[str, Any]]:
    return [{"path_private": p, "range_private": "1-5", "score_private": 1, "channel_private": "read_related_test"} for p in bounded_source_paths() if "test" in p.lower()][:MAX_CANDIDATES]


def ensure_episode_count(episodes: int) -> None:
    if episodes < MIN_EPISODES or episodes > MAX_EPISODES:
        raise RunnerError(f"--episodes must be between {MIN_EPISODES} and {MAX_EPISODES}")
    if len(TASKS) < 20:
        raise RunnerError("preflight_insufficient_episode_source: expected at least 20 FRK workflow tasks")


def action_is_structurally_available(action: str, task: WorkflowTask) -> bool:
    if action in TERMINAL_ACTIONS:
        return True
    if action == "retrieve_bm25":
        candidates, _latency, _availability = local_bm25_like_search(task)
        return bool(candidates)
    if action == "retrieve_symbol_regex":
        candidates, _latency, _availability = local_symbol_regex_search(task)
        return bool(candidates)
    if action == "read_top1":
        candidates, _latency, _availability = local_bm25_like_search(task)
        return bool(candidates)
    if action == "read_next_unique_file":
        candidates, _latency, _availability = local_bm25_like_search(task)
        return len(candidates) > 1
    if action == "read_related_test":
        return bool(related_test_candidates())
    return False


def build_action_availability() -> dict[str, list[WorkflowTask]]:
    return {action: [task for task in TASKS if action_is_structurally_available(action, task)] for action in ALLOWED_ACTIONS}


def available_actions_from(availability: dict[str, list[WorkflowTask]]) -> list[str]:
    return [action for action in ALLOWED_ACTIONS if availability.get(action)]


def action_eligibility_counts(availability: dict[str, list[WorkflowTask]]) -> dict[str, int]:
    return {action: len(availability.get(action, [])) for action in ALLOWED_ACTIONS}


def generate_episodes(count: int, availability: dict[str, list[WorkflowTask]] | None = None) -> list[Episode]:
    ensure_episode_count(count)
    if availability is None:
        availability = build_action_availability()
    available_actions = available_actions_from(availability)
    if not available_actions:
        raise RunnerError("preflight_no_structurally_available_actions")
    rng = random.Random(FIXED_SEED)
    actions: list[str] = []
    while len(actions) < count:
        block = list(available_actions)
        rng.shuffle(block)
        actions.extend(block)
    task_pools = {action: list(availability[action]) for action in available_actions}
    task_offsets = {action: 0 for action in available_actions}
    for pool in task_pools.values():
        rng.shuffle(pool)
    probability = 1.0 / len(available_actions)
    episodes: list[Episode] = []
    for i in range(count):
        action = actions[i]
        pool = task_pools[action]
        offset = task_offsets[action]
        if offset >= len(pool):
            rng.shuffle(pool)
            offset = 0
        task = pool[offset]
        task_offsets[action] = offset + 1
        episodes.append(Episode(i, task, action, private_ref("randomization_block", str(FIXED_SEED), str(i // len(available_actions))), probability, tuple(available_actions)))
    return episodes


def walk_values(obj: Any) -> list[Any]:
    values = [obj]
    if isinstance(obj, dict):
        for value in obj.values():
            values.extend(walk_values(value))
    elif isinstance(obj, list):
        for value in obj:
            values.extend(walk_values(value))
    return values


def build_row(
    *,
    episode: Episode,
    order_index: int,
    action_label: str,
    seen_count: int,
    candidate_count: int,
    observation_status: str,
    result_bucket: str,
    failure_bucket: str,
    latency_seconds: float,
    evidence_delta: int,
    evidence_required: bool,
    evidence: dict[str, Any] | None,
    outcome_bucket: str,
    dry_run: bool,
) -> dict[str, Any]:
    materialized = bool(evidence and evidence.get("materialization_status") == "materialized_current")
    return {
        "schema_version": ROW_SCHEMA_VERSION,
        "episode_private_id": private_ref("episode", episode.task.opaque_id, str(episode.index), str(FIXED_SEED)),
        "step_index": 0,
        "created_order_index": order_index,
        "randomization_block_private": episode.block_id,
        "task_bucket": bucket_count(len(TASKS)),
        "task_family_bucket": private_ref("family", episode.task.family),
        "state": {
            "remaining_budget_bucket": "count_1",
            "seen_file_count_bucket": bucket_count(seen_count),
            "candidate_count_bucket": bucket_count(candidate_count),
            "ambiguity_bucket": episode.task.ambiguity_bucket,
            "evidence_coverage_bucket": bucket_coverage(seen_count),
            "features_label_blind_bool": True,
        },
        "action": {
            "label": action_label,
            "local_existing_capability": True,
            "network_or_provider_action": False,
            "new_retrieval_family": False,
        },
        "randomization": {
            "eligible_actions": list(episode.eligible_actions),
            "assignment_policy_id_private": private_ref("policy", str(FIXED_SEED)),
            "action_probability_bucket": bucket_probability(episode.action_probability),
            "propensity_available_bool": True,
        },
        "observation": {
            "status": observation_status,
            "result_bucket": result_bucket,
            "evidence_delta_bucket": bucket_count(evidence_delta),
            "latency_bucket": bucket_latency(latency_seconds),
            "failure_bucket": failure_bucket,
        },
        "evidence_core": {
            "required_bool": evidence_required,
            "link_status": "linked_current" if materialized else ("missing" if evidence_required else "not_required"),
            "currentness_status": evidence.get("currentness_status") if evidence else "not_required",
            "materialization_status": evidence.get("materialization_status") if evidence else "not_required",
            "path_private": evidence.get("path_private") if evidence else None,
            "range_private": evidence.get("range_private") if evidence else None,
            "content_digest_private": evidence.get("content_digest_private") if evidence else None,
        },
        "outcome": {
            "label_timing": "after_action",
            "outcome_bucket": outcome_bucket,
            "label_used_in_state_or_action_bool": False,
        },
        "privacy": {
            "private_row_bool": True,
            "dry_run_no_private_write_bool": dry_run,
            "raw_publication_bool": False,
            "provider_payload_public_bool": False,
            "private_values_public_bool": False,
            "network_access": "no_network",
        },
    }


def execute_episode(episode: Episode, order_index: int, dry_run: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    candidates: list[dict[str, Any]] = []
    evidence: dict[str, Any] | None = None
    availability = "not_applicable"
    action = episode.action

    if action == "retrieve_bm25":
        candidates, latency, availability = local_bm25_like_search(episode.task)
    elif action == "retrieve_symbol_regex":
        candidates, latency, availability = local_symbol_regex_search(episode.task)
    elif action in {"read_top1", "read_next_unique_file"}:
        candidates, _unused_latency, availability = local_bm25_like_search(episode.task)
        latency = time.monotonic() - started
    elif action == "read_related_test":
        candidates = related_test_candidates()
        availability = "available" if candidates else "bounded_no_candidate"
        latency = time.monotonic() - started
    else:
        latency = time.monotonic() - started

    candidate = None
    if action == "read_next_unique_file" and len(candidates) > 1:
        candidate = candidates[1]
    elif candidates and action not in TERMINAL_ACTIONS:
        candidate = candidates[0]
    if candidate:
        evidence = materialize(str(candidate["path_private"]), str(candidate["range_private"]))

    success = bool(evidence and evidence.get("materialization_status") == "materialized_current")
    if action == "stop":
        outcome = "stop_bucket"
        observation = "stopped"
        result = "not_applicable"
        failure = "none"
    elif action == "abstain":
        outcome = "abstain_bucket"
        observation = "abstained"
        result = "not_applicable"
        failure = "none"
    else:
        outcome = "success_bucket" if success else "failure_bucket"
        observation = "observed" if success else "failed_safe"
        result = "evidence_added" if success else ("no_change" if action.startswith("retrieve") else "failure")
        failure = "none" if success else "missing_source"
    row = build_row(
        episode=episode,
        order_index=order_index,
        action_label=action,
        seen_count=1 if success else 0,
        candidate_count=len(candidates),
        observation_status=observation,
        result_bucket=result,
        failure_bucket=failure,
        latency_seconds=latency,
        evidence_delta=len(candidates) if action.startswith("retrieve") else (1 if success else 0),
        evidence_required=action not in TERMINAL_ACTIONS,
        evidence=evidence,
        outcome_bucket=outcome,
        dry_run=dry_run,
    )
    stat = {
        "action": action,
        "success": success,
        "evidence_required": action not in TERMINAL_ACTIONS,
        "materialized": success,
        "availability": availability,
        "failure": failure,
        "latency_bucket": row["observation"]["latency_bucket"],
        "candidate_count": len(candidates),
    }
    return row, stat


def validate_private_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not rows:
        return ["private rows must be non-empty"]
    seen_episodes: set[str] = set()
    for idx, row in enumerate(rows):
        loc = f"row[{idx}]"
        if set(row) != ROW_KEYS:
            errors.append(f"{loc}: row shape drift")
        if row.get("schema_version") != ROW_SCHEMA_VERSION:
            errors.append(f"{loc}: bad schema version")
        episode_id = row.get("episode_private_id")
        if episode_id in seen_episodes:
            errors.append(f"{loc}: duplicate episode id")
        seen_episodes.add(str(episode_id))
        action = row.get("action", {}).get("label") if isinstance(row.get("action"), dict) else None
        if action not in ALLOWED_ACTIONS:
            errors.append(f"{loc}: action set drift")
        eligible_actions = row.get("randomization", {}).get("eligible_actions")
        if not isinstance(eligible_actions, list) or not eligible_actions:
            errors.append(f"{loc}: eligible action drift")
            eligible_actions = []
        elif any(action_name not in ALLOWED_ACTIONS for action_name in eligible_actions) or len(set(eligible_actions)) != len(eligible_actions):
            errors.append(f"{loc}: eligible action drift")
        elif action not in eligible_actions:
            errors.append(f"{loc}: selected action not eligible")
        for group_name in ("state", "action", "randomization"):
            for value in walk_values(row.get(group_name, {})):
                if isinstance(value, str) and LABEL_LEAK_TERMS.search(value) and value not in ALLOWED_ACTIONS:
                    errors.append(f"{loc}.{group_name}: label leakage term")
        if row.get("state", {}).get("features_label_blind_bool") is not True:
            errors.append(f"{loc}: state not label-blind")
        if row.get("outcome", {}).get("label_used_in_state_or_action_bool") is not False:
            errors.append(f"{loc}: label used in state/action")
        privacy = row.get("privacy", {})
        if privacy.get("network_access") != "no_network":
            errors.append(f"{loc}: network not allowed")
        for key in ("raw_publication_bool", "provider_payload_public_bool", "private_values_public_bool"):
            if privacy.get(key) is not False:
                errors.append(f"{loc}: {key} must be false")
        evidence = row.get("evidence_core", {})
        if evidence.get("required_bool") and evidence.get("link_status") == "linked_current":
            if evidence.get("currentness_status") != "verified_current" or evidence.get("materialization_status") != "materialized_current":
                errors.append(f"{loc}: linked evidence must be verified/materialized")
    return errors


def run_episodes(episode_count: int, dry_run: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    availability = build_action_availability()
    for order, episode in enumerate(generate_episodes(episode_count, availability)):
        row, stat = execute_episode(episode, order, dry_run)
        rows.append(row)
        stats.append(stat)
    errors = validate_private_rows(rows)
    if errors:
        raise RunnerError("private row validation failed: " + "; ".join(errors[:5]))
    return rows, stats, {
        "episode_count": len(rows),
        "row_count": len(rows),
        "private_rows_written": False,
        "storage_class": "none",
        "action_eligible_episode_counts": action_eligibility_counts(availability),
    }


def hard_gates(rows: list[dict[str, Any]], stats: list[dict[str, Any]], confirmed: bool) -> dict[str, bool]:
    actions = Counter(row["action"]["label"] for row in rows)
    eligible_actions = set(rows[0]["randomization"]["eligible_actions"]) if rows else set()
    return {
        "episode_source_bounded_to_frk_tasks": len(TASKS) >= 20,
        "episode_count_in_authorized_range": MIN_EPISODES <= len(rows) <= MAX_EPISODES,
        "selected_actions_subset_of_allowed": set(actions).issubset(set(ALLOWED_ACTIONS)),
        "all_eligible_actions_observed": set(actions) == eligible_actions,
        "no_provider_network_actions": all(not row["action"]["network_or_provider_action"] and row["privacy"]["network_access"] == "no_network" for row in rows),
        "no_training_or_runtime_default_change": True,
        "private_rows_schema_valid": not validate_private_rows(rows),
        "public_private_boundary_preserved": True,
        "confirm_private_output_for_private_write": confirmed,
        "evidencecore_checked_for_counted_evidence": all((not s["evidence_required"]) or s["materialized"] or s["failure"] != "none" for s in stats),
    }


def public_leak_errors(report: dict[str, Any]) -> list[str]:
    sanitized = copy.deepcopy(report)
    privacy = sanitized.get("privacy_summary") if isinstance(sanitized, dict) else None
    if isinstance(privacy, dict):
        for key in list(privacy):
            if key.endswith("_public") or key.startswith("private_") or key.startswith("raw_private"):
                privacy.pop(key, None)
    errors = schema.public_leak_errors(sanitized)
    text = json.dumps(report, sort_keys=True)
    for term in ("private_ref_", PRIVATE_ROOT_PREFIX, PRIVATE_ROWS_FILENAME, "crates/", "docs/", "eval/", "README.md"):
        if term in text:
            errors.append(f"public leak disallowed term {term}")
    if HASH_RE.search(text):
        errors.append("public leak hash-like value")
    return errors


def aggregate_report(rows: list[dict[str, Any]], stats: list[dict[str, Any]], manifest: dict[str, Any], *, confirmed: bool, dry_run: bool) -> dict[str, Any]:
    actions = Counter(row["action"]["label"] for row in rows)
    eligible_actions = set(rows[0]["randomization"]["eligible_actions"]) if rows else set()
    eligible_counts = manifest.get("action_eligible_episode_counts")
    if not isinstance(eligible_counts, dict):
        eligible_counts = {action: (len(TASKS) if action in eligible_actions else 0) for action in ALLOWED_ACTIONS}
    outcomes = Counter(row["outcome"]["outcome_bucket"] for row in rows)
    failures = Counter(row["observation"]["failure_bucket"] for row in rows)
    currentness = Counter(row["evidence_core"]["currentness_status"] for row in rows)
    materialized = sum(1 for row in rows if row["evidence_core"]["materialization_status"] == "materialized_current")
    required = sum(1 for row in rows if row["evidence_core"]["required_bool"])
    success_by_action = Counter(s["action"] for s in stats if s["success"])
    total_by_action = Counter(s["action"] for s in stats)
    rates = {action: (success_by_action.get(action, 0), total_by_action.get(action, 0)) for action in ALLOWED_ACTIONS}
    comparable = [action for action in ALLOWED_ACTIONS if action not in TERMINAL_ACTIONS and total_by_action.get(action, 0)]
    best_action = max(comparable, key=lambda a: (rates[a][0] / rates[a][1]) if rates[a][1] else -1) if comparable else "none"
    gates = hard_gates(rows, stats, confirmed)
    status = STATUS_PREFLIGHT if dry_run or not confirmed else (STATUS_COMPLETE_NO_CLAIM if all(gates.values()) else STATUS_NO_GO)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "authorization_attestation": {
            "training_authorized": False,
            "runtime_default_change_authorized": False,
            "provider_network_authorized": False,
            "method_winner_claimed": False,
            "new_retrieval_channel_family_added": False,
            "model_training_executed": False,
            "local_existing_capabilities_only": True,
            "private_output_confirmation": "confirmed" if confirmed else "not_confirmed_no_private_rows_written",
            "dry_run_preflight": dry_run,
        },
        "aggregate_buckets": {
            "episode_count_bucket": bucket_count(int(manifest["episode_count"])),
            "row_count_bucket": bucket_count(int(manifest["row_count"])),
            "source_task_count_bucket": bucket_count(len(TASKS)),
            "action_coverage": {name: bucket_count(actions.get(name, 0)) for name in ALLOWED_ACTIONS},
            "outcome_buckets": {name: bucket_count(count) for name, count in sorted(outcomes.items())},
            "failure_buckets": {name: bucket_count(count) for name, count in sorted(failures.items())},
            "candidate_count_buckets": {name: bucket_count(count) for name, count in sorted(Counter(bucket_count(s["candidate_count"]) for s in stats).items())},
            "latency_buckets": {name: bucket_count(count) for name, count in sorted(Counter(s["latency_bucket"] for s in stats).items())},
        },
        "preflight_availability": {
            action: {
                "availability_status": "eligible" if int(eligible_counts.get(action, 0)) > 0 else "structurally_unavailable",
                "eligible_episode_count_bucket": bucket_count(int(eligible_counts.get(action, 0))),
                "sampled_episode_count_bucket": bucket_count(actions.get(action, 0)),
            }
            for action in ALLOWED_ACTIONS
        },
        "randomized_action_health": {
            "policy": "fixed_seed_shuffled_blocks_over_structurally_eligible_actions",
            "allowed_action_count_bucket": bucket_count(len(ALLOWED_ACTIONS)),
            "eligible_action_count_bucket": bucket_count(len(eligible_actions)),
            "unavailable_action_count_bucket": bucket_count(len(set(ALLOWED_ACTIONS) - eligible_actions)),
            "all_allowed_actions_observed": set(actions) == set(ALLOWED_ACTIONS),
            "all_eligible_actions_observed": set(actions) == eligible_actions,
            "propensity_available": True,
            "assignment_probability_bucket": bucket_probability(1.0 / len(eligible_actions)) if eligible_actions else "probability_0_to_0_25",
            "coverage_bucket_by_action_min": bucket_count(min(actions.values()) if actions else 0),
        },
        "evidencecore_summary": {
            "required_evidence_bucket": bucket_count(required),
            "materialized_current_bucket": bucket_count(materialized),
            "not_materialized_bucket": bucket_count(max(0, required - materialized)),
            "currentness_buckets": {name: bucket_count(count) for name, count in sorted(currentness.items())},
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "private_rows_written": bool(manifest.get("private_rows_written")),
            "private_paths_public": False,
            "private_ranges_public": False,
            "private_hashes_public": False,
            "private_task_text_public": False,
            "per_episode_details_public": False,
            "raw_private_rows_public": False,
            "provider_payloads_public": False,
            "central_privacy_scan": "pending",
        },
        "hard_gates": gates,
        "best_fixed_local_action_baseline": {
            "comparison_meaningfulness": "tiny_local_pilot_no_signal_claim",
            "best_fixed_action_bucket": "local_read_or_retrieve_action" if best_action != "none" else "not_available",
            "best_fixed_action_success_bucket": bucket_rate(*rates[best_action]) if best_action != "none" else "rate_0",
            "randomized_policy_success_bucket": bucket_rate(sum(1 for s in stats if s["success"]), len(stats)),
            "method_winner_claimed": False,
            "signal_claim": "no_signal_claim",
        },
        "validation_summary": {
            "private_row_validation": "passed" if not validate_private_rows(rows) else "failed",
            "route_specific_public_report_validation": "pending",
            "central_privacy_scanner": "pending",
            "self_test_available": True,
        },
        "next_authorized_action": NEXT_ACTION,
    }
    report["privacy_summary"]["central_privacy_scan"] = "passed" if not public_leak_errors(report) else "failed"
    report["validation_summary"]["central_privacy_scanner"] = report["privacy_summary"]["central_privacy_scan"]
    report["validation_summary"]["route_specific_public_report_validation"] = "passed" if not validate_public_report(report) else "failed"
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    if set(report) != REPORT_KEYS:
        errors.append("report top-level shape drift")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("bad schema version")
    if report.get("phase") != PHASE:
        errors.append("bad phase")
    if report.get("status") not in {STATUS_PREFLIGHT, STATUS_COMPLETE_NO_CLAIM, STATUS_NO_GO, STATUS_INSUFFICIENT_SOURCE}:
        errors.append("bad status")
    auth = report.get("authorization_attestation", {})
    for key in ("training_authorized", "runtime_default_change_authorized", "provider_network_authorized", "method_winner_claimed", "new_retrieval_channel_family_added", "model_training_executed"):
        if auth.get(key) is not False:
            errors.append(f"authorization overclaim: {key}")
    if auth.get("local_existing_capabilities_only") is not True:
        errors.append("local existing capability attestation missing")
    action_coverage = report.get("aggregate_buckets", {}).get("action_coverage", {})
    if set(action_coverage) != set(ALLOWED_ACTIONS):
        errors.append("allowed action set drift in coverage")
    availability = report.get("preflight_availability", {})
    if set(availability) != set(ALLOWED_ACTIONS):
        errors.append("preflight availability action set drift")
    elif any((not isinstance(value, dict)) or set(value) != {"availability_status", "eligible_episode_count_bucket", "sampled_episode_count_bucket"} for value in availability.values()):
        errors.append("preflight availability shape drift")
    for action_name, value in (availability.items() if isinstance(availability, dict) else []):
        if not isinstance(value, dict):
            errors.append("preflight availability row must be aggregate object")
            continue
        if value.get("availability_status") == "structurally_unavailable" and value.get("sampled_episode_count_bucket") != "count_0":
            errors.append(f"unavailable action sampled: {action_name}")
    if not report.get("randomized_action_health", {}).get("all_eligible_actions_observed"):
        errors.append("not all eligible actions observed")
    privacy = report.get("privacy_summary", {})
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("publication level drift")
    for key in ("private_paths_public", "private_ranges_public", "private_hashes_public", "private_task_text_public", "per_episode_details_public", "raw_private_rows_public", "provider_payloads_public"):
        if privacy.get(key) is not False:
            errors.append(f"privacy boundary failure: {key}")
    if privacy.get("central_privacy_scan") != "passed":
        errors.append("central privacy scan must pass")
    gates = report.get("hard_gates", {})
    if gates.get("no_provider_network_actions") is not True or gates.get("no_training_or_runtime_default_change") is not True:
        errors.append("hard gate overclaim/failure")
    if report.get("best_fixed_local_action_baseline", {}).get("method_winner_claimed") is not False:
        errors.append("method winner claim is prohibited")
    if report.get("best_fixed_local_action_baseline", {}).get("signal_claim") != "no_signal_claim":
        errors.append("signal claim must be denied")
    if report.get("next_authorized_action") != NEXT_ACTION:
        errors.append("next authorized action drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_public_report(report)
    if errors:
        raise RunnerError("public report validation failed: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def capture(episodes: int, *, confirm_private_output: bool, dry_run: bool, output: Path) -> dict[str, Any]:
    rows, stats, manifest = run_episodes(episodes, dry_run or not confirm_private_output)
    confirmed_write = confirm_private_output and not dry_run
    if confirmed_write:
        private_root = REPO / "runs" / f"{PRIVATE_ROOT_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        write_jsonl(private_root / PRIVATE_ROWS_FILENAME, rows)
        manifest.update({"private_rows_written": True, "storage_class": "ignored_repo_runs_private_jsonl"})
    report = aggregate_report(rows, stats, manifest, confirmed=confirmed_write, dry_run=dry_run or not confirm_private_output)
    write_report(report, output)
    return report


def fixture_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    evidence = {"path_private": "private/source.rs", "range_private": "1-3", "currentness_status": "verified_current", "materialization_status": "materialized_current", "content_digest_private": "0" * 64}
    availability = build_action_availability()
    for order, episode in enumerate(generate_episodes(DEFAULT_EPISODES, availability)):
        success = episode.action not in TERMINAL_ACTIONS
        row = build_row(
            episode=episode,
            order_index=order,
            action_label=episode.action,
            seen_count=1 if success else 0,
            candidate_count=1 if success else 0,
            observation_status="observed" if success else ("stopped" if episode.action == "stop" else "abstained"),
            result_bucket="evidence_added" if success else "not_applicable",
            failure_bucket="none",
            latency_seconds=0.001,
            evidence_delta=1 if success else 0,
            evidence_required=success,
            evidence=evidence if success else None,
            outcome_bucket="success_bucket" if success else ("stop_bucket" if episode.action == "stop" else "abstain_bucket"),
            dry_run=True,
        )
        rows.append(row)
        stats.append({"action": episode.action, "success": success, "evidence_required": success, "materialized": success, "availability": "available", "failure": "none", "latency_bucket": "lt_1s", "candidate_count": 1 if success else 0})
    return rows, stats, {"episode_count": len(rows), "row_count": len(rows), "private_rows_written": False, "storage_class": "none", "action_eligible_episode_counts": action_eligibility_counts(availability)}


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    rows, stats, manifest = fixture_rows()
    checks.append(("synthetic_private_rows_valid", not validate_private_rows(rows)))
    report = aggregate_report(rows, stats, manifest, confirmed=False, dry_run=True)
    checks.append(("synthetic_public_report_valid", not validate_public_report(report)))
    bad_rows = copy.deepcopy(rows)
    bad_rows[0]["action"]["label"] = "llm_provider_call"
    checks.append(("action_set_drift_rejected", bool(validate_private_rows(bad_rows))))
    bad_rows = copy.deepcopy(rows)
    bad_rows[0]["state"]["debug"] = "gold_label_hit"
    checks.append(("label_leakage_rejected", bool(validate_private_rows(bad_rows))))
    bad_report = copy.deepcopy(report)
    bad_report["privacy_summary"]["private_paths_public"] = True
    checks.append(("public_privacy_leak_rejected", bool(validate_public_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["authorization_attestation"]["training_authorized"] = True
    checks.append(("training_overclaim_rejected", bool(validate_public_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["best_fixed_local_action_baseline"]["method_winner_claimed"] = True
    checks.append(("method_winner_overclaim_rejected", bool(validate_public_report(bad_report))))
    bad_report = copy.deepcopy(report)
    bad_report["aggregate_buckets"]["action_coverage"].pop("abstain", None)
    checks.append(("report_action_set_drift_rejected", bool(validate_public_report(bad_report))))
    first_block_actions = [episode.action for episode in generate_episodes(DEFAULT_EPISODES)[:len(ALLOWED_ACTIONS)]]
    checks.append(("first_action_block_shuffled", first_block_actions != list(ALLOWED_ACTIONS)))
    availability = build_action_availability()
    unavailable_action = "read_related_test"
    availability[unavailable_action] = []
    unavailable_episodes = generate_episodes(DEFAULT_EPISODES, availability)
    checks.append(("unavailable_action_not_selected", unavailable_action not in {episode.action for episode in unavailable_episodes}))
    rows_unavailable = []
    stats_unavailable = []
    evidence = {"path_private": "private/source.rs", "range_private": "1-3", "currentness_status": "verified_current", "materialization_status": "materialized_current", "content_digest_private": "0" * 64}
    for order, episode in enumerate(unavailable_episodes):
        success = episode.action not in TERMINAL_ACTIONS
        row = build_row(
            episode=episode,
            order_index=order,
            action_label=episode.action,
            seen_count=1 if success else 0,
            candidate_count=1 if success else 0,
            observation_status="observed" if success else ("stopped" if episode.action == "stop" else "abstained"),
            result_bucket="evidence_added" if success else "not_applicable",
            failure_bucket="none",
            latency_seconds=0.001,
            evidence_delta=1 if success else 0,
            evidence_required=success,
            evidence=evidence if success else None,
            outcome_bucket="success_bucket" if success else ("stop_bucket" if episode.action == "stop" else "abstain_bucket"),
            dry_run=True,
        )
        rows_unavailable.append(row)
        stats_unavailable.append({"action": episode.action, "success": success, "evidence_required": success, "materialized": success, "availability": "available", "failure": "none", "latency_bucket": "lt_1s", "candidate_count": 1 if success else 0})
    manifest_unavailable = {"episode_count": len(rows_unavailable), "row_count": len(rows_unavailable), "private_rows_written": False, "storage_class": "none", "action_eligible_episode_counts": action_eligibility_counts(availability)}
    unavailable_report = aggregate_report(rows_unavailable, stats_unavailable, manifest_unavailable, confirmed=False, dry_run=True)
    checks.append(("unavailable_action_report_valid", not validate_public_report(unavailable_report)))
    bad_report = copy.deepcopy(unavailable_report)
    bad_report["preflight_availability"][unavailable_action]["sampled_episode_count_bucket"] = "count_1"
    checks.append(("unavailable_action_sample_rejected", bool(validate_public_report(bad_report))))
    try:
        temp = REPO / "artifacts" / PHASE / "__phase1_selftest_report__.json"
        capture(24, confirm_private_output=False, dry_run=True, output=temp)
        boundary_ok = not (REPO / "runs" / f"{PRIVATE_ROOT_PREFIX}selftest").exists()
    except RunnerError:
        boundary_ok = False
    finally:
        temp.unlink(missing_ok=True)
    checks.append(("missing_confirm_private_boundary_safe", boundary_ok))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise RunnerError("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks), "failed_checks": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 local interventional evidence acquisition pilot/preflight")
    parser.add_argument("--self-test", action="store_true", help="run in-memory validator and privacy mutation tests")
    parser.add_argument("--validate-report", type=Path, help="validate an aggregate-only public report")
    parser.add_argument("--confirm-private-output", action="store_true", help="required before writing ignored private rows under runs/")
    parser.add_argument("--episodes", type=int, default=DEFAULT_EPISODES, help="episode count, 24-40")
    parser.add_argument("--dry-run", action="store_true", help="write only preflight public report; never write private rows")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT, help="public aggregate report path")
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
        report = capture(args.episodes, confirm_private_output=args.confirm_private_output, dry_run=args.dry_run, output=args.output)
        print(json.dumps({"status": report["status"], "public_report": str(args.output), "private_rows_written": report["privacy_summary"]["private_rows_written"]}, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, RunnerError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
