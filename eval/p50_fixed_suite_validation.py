#!/usr/bin/env python3
"""P50 Fixed-Suite Validation / Anti-Overfit Gate.

P50 is a deterministic, SCORE-phase-only evaluation discipline phase.  It consumes
the same ephemeral P25-policy records (`p25-policy-records-ephemeral-v1`) that feed
P25, P30, P31, P33-B, P46 and P47, and produces a public aggregate health report
over a *frozen* suite.

Hard constraints:
* Evaluation discipline only — this is not a policy improvement phase.
* P48 is explicitly not implemented.
* No remote calls; `remote_calls_by_p50=0`.
* No EvidenceCore semantics change.
* No default promotion: `promotion_ready=false`, `default_should_change=false`,
  `evidencecore_semantics_changed=false`, `candidate_not_fact=true`.
* Public outputs are aggregate-only: no task IDs, candidate IDs, paths, spans,
  gold spans, private labels, route features, snippets, prompts, responses,
  provider URLs/keys, or repository identifiers treated as paths.
* Missing, unavailable, or fallback data is marked explicitly; never zero-filled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p25_bucket_policy as p25
import p46_candidate_reach_cost_map as p46
import p47_request_more_context as p47

SCHEMA_VERSION = "p50-fixed-suite-validation-v1"
GENERATED_BY = "eval/p50_fixed_suite_validation.py"

DEFAULT_OUT = Path("artifacts/p50_fixed_suite_validation/p50_fixed_suite_validation_report.json")
DEFAULT_DOC = Path("docs/en/p50-fixed-suite-validation.md")

KEY_STRATEGIES = [
    "candidate_baseline",
    "symbol_regex_union",
    "rrf_primary",
    "llm_span_narrow",
]

P50_SAFETY_FLAG_KEYS = set(p46.SAFETY_FLAG_KEYS) | set(p47.P47_SAFETY_FLAG_KEYS) | {
    "real_evaluation",
    "input_record_count",
    "repo_count",
    "suite_public_bucket_distribution",
    "suite_risk_tag_distribution",
    "candidate_pool_availability",
    "gold_span_availability",
    "p33b_subtype_availability",
    "outcome_availability",
    "fallback_outcome_rate",
    "missing_cost_field_rate",
    "suite_manifest_hash",
    "evaluator_config_hash",
    "evaluator_config",
    "suite_composition",
    "policy_route_comparison",
    "baseline_policy_delta",
    "p46_carry_forward",
    "p47_carry_forward",
    "p48_variant_availability",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "quality_gate_status",
    "quality_gate_reasons",
    "remote_calls_by_p50",
    "source_reads_attempted_by_p50",
    "score_phase_only_metrics",
    "aggregate_only_public_artifact",
    "span_geometry_only",
    "expanded_candidate_not_evidence",
    "labels_loaded_after_run",
    "delta_availability",
    "availability",
    "by_policy",
    "compared_policies",
    "key_strategy_outcome_cost",
    "action_distribution",
    "fallback_rates",
    "materialization_availability",
    "policy_routes",
    "route_summary",
    "status_reason",
    "not_quality_evidence",
}

FORBIDDEN_PUBLIC_KEYS = set(p46.FORBIDDEN_PUBLIC_KEYS) | {
    "task_id",
    "candidate_id",
    "path",
    "start_line",
    "end_line",
    "content_sha",
    "gold_spans",
    "label",
    "labels",
    "query",
    "prompt",
    "snippet",
    "response",
    "route_features",
    "source_text",
    "provider_key",
    "base_url",
    "api_key",
    "repo_id",
    "raw_candidates",
    "per_task",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stable_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _hash_bytes(data: bytes, *, alg: str = "sha256") -> str:
    if alg == "sha256":
        return hashlib.sha256(data).hexdigest()
    if alg == "blake2b":
        return hashlib.blake2b(data).hexdigest()
    raise ValueError(f"Unsupported hash algorithm: {alg}")


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _ratio(num: int, den: int) -> float | None:
    if den <= 0 or num < 0:
        return None
    return round(num / den, 6)


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P50_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _compute_suite_manifest_hash(tasks: list[dict[str, Any]], input_paths: list[Path]) -> dict[str, Any]:
    """Deterministic hash over private identifiers and public metadata; only the digest is published."""
    _ = input_paths
    private_components: list[dict[str, Any]] = []
    for t in tasks:
        private_components.append({
            "task_id": t.get("task_id"),
            "repo_id": t.get("repo_id"),
            "has_gold": t.get("has_gold"),
            "task_bucket": t.get("task_bucket"),
            "task_risk_tags": sorted(t.get("task_risk_tags", [])),
            "has_candidate_pool": t.get("has_candidate_pool"),
            "has_gold_spans": t.get("has_gold_spans"),
            "outcome_strategies_present": sorted(t.get("outcomes", {}).keys()),
            "pool_strategies_present": sorted(t.get("pools", {}).keys()),
        })
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "task_count": len(tasks),
        "input_source_count": len(input_paths),
        "private_task_manifest": private_components,
    }
    data = _stable_json(envelope)
    return {
        "algorithm": "sha256+blake2b",
        "sha256": _hash_bytes(data, alg="sha256"),
        "blake2b": _hash_bytes(data, alg="blake2b"),
        "published_note": "This hash covers private per-task identifiers and public metadata. Raw components are not published.",
    }


def _compute_evaluator_config_hash(
    *,
    k_values: list[int],
    reach_strategies: list[str],
    outcome_strategies: list[str],
    key_strategies: list[str],
    policies: list[str],
    variant_names: list[str],
    settings: dict[str, Any],
) -> dict[str, Any]:
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "k_values": k_values,
        "reach_strategies": reach_strategies,
        "outcome_strategies": outcome_strategies,
        "key_strategies": key_strategies,
        "policies": policies,
        "variant_names": variant_names,
        "settings": settings,
    }
    data = _stable_json(envelope)
    return {
        "algorithm": "sha256+blake2b",
        "sha256": _hash_bytes(data, alg="sha256"),
        "blake2b": _hash_bytes(data, alg="blake2b"),
        "published_note": "Hash of evaluator configuration. Raw configuration fields are listed only in aggregate summary form.",
    }


def _compute_suite_composition(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    task_count = len(tasks)
    if not tasks:
        return {
            "input_record_count": 0,
            "task_count": 0,
            "repo_count": 0,
            "positive_task_count": 0,
            "no_gold_task_count": 0,
            "public_bucket_distribution": {},
            "risk_tag_distribution": {},
            "candidate_pool_availability": "missing_candidate_pool",
            "gold_span_availability": "missing_gold_spans",
            "p33b_subtype_availability": "missing_subtype_data",
            "outcome_availability": "missing_outcomes",
            "fallback_outcome_rate": None,
            "missing_cost_field_rate": None,
        }

    repo_ids = {str(t.get("repo_id") or "unknown") for t in tasks}
    positive_count = sum(1 for t in tasks if t["has_gold"])
    no_gold_count = task_count - positive_count

    candidate_pool_availability = (
        "available" if all(t.get("has_candidate_pool") for t in tasks)
        else "partial" if any(t.get("has_candidate_pool") for t in tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available" if all(t.get("has_gold_spans") for t in tasks if t["has_gold"])
        else "partial" if any(t.get("has_gold_spans") for t in tasks if t["has_gold"])
        else "missing_gold_spans"
    )
    p33b_subtype_availability = "available" if any(t.get("subtypes") for t in tasks) else "missing_subtype_data"

    # Outcome availability across all tasks/strategies.
    total_outcome_slots = 0
    present_outcome_slots = 0
    cost_available_slots = 0
    for t in tasks:
        for strategy in p46.OUTCOME_STRATEGIES:
            total_outcome_slots += 1
            out = t.get("outcomes", {}).get(strategy, {})
            if out.get("outcome_present"):
                present_outcome_slots += 1
                if out.get("cost_available"):
                    cost_available_slots += 1

    outcome_availability = (
        "available" if present_outcome_slots == total_outcome_slots
        else "partial" if present_outcome_slots > 0
        else "missing_outcomes"
    )
    fallback_outcome_rate = _rate(total_outcome_slots - present_outcome_slots, total_outcome_slots)
    missing_cost_field_rate = _rate(total_outcome_slots - cost_available_slots, total_outcome_slots)

    bucket_dist: dict[str, int] = defaultdict(int)
    tag_dist: dict[str, int] = defaultdict(int)
    for t in tasks:
        bucket_dist[t.get("task_bucket", "unknown")] += 1
        for tag in t.get("task_risk_tags", []):
            tag_dist[tag] += 1

    return {
        "input_record_count": task_count,
        "task_count": task_count,
        "repo_count": len(repo_ids),
        "positive_task_count": positive_count,
        "no_gold_task_count": no_gold_count,
        "public_bucket_distribution": dict(sorted(bucket_dist.items())),
        "risk_tag_distribution": dict(sorted(tag_dist.items())),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "p33b_subtype_availability": p33b_subtype_availability,
        "outcome_availability": outcome_availability,
        "fallback_outcome_rate": fallback_outcome_rate,
        "missing_cost_field_rate": missing_cost_field_rate,
    }


def _key_strategy_outcome_cost(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    by_strategy: dict[str, Any] = {}
    for strategy in KEY_STRATEGIES:
        by_strategy[strategy] = p46._outcome_cost_block(tasks, strategy)
    return {"by_strategy": by_strategy}


def _policy_route_comparison(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    routes = p46.compute_policy_routes(tasks)
    route_summary: dict[str, Any] = {}
    for policy, block in routes.items():
        avail = block.get("availability")
        route_summary[policy] = {
            "availability": avail,
            "selected_task_count": block.get("selected_task_count", 0),
            "selected_with_outcome_count": block.get("selected_with_outcome_count", 0),
            "selected_missing_outcome_count": block.get("selected_missing_outcome_count", 0),
            "outcome_fallback_rate": block.get("outcome_fallback_rate"),
            "selected_with_cost_count": block.get("selected_with_cost_count", 0),
            "selected_missing_cost_count": block.get("selected_missing_cost_count", 0),
            "cost_fallback_rate": block.get("cost_fallback_rate"),
            "action_distribution": dict(sorted(block.get("action_counts", {}).items())),
        }
    return {"by_policy": route_summary, "compared_policies": list(routes.keys())}


def _baseline_policy_delta(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Delta of P25/P30 route policies vs raw strategy outcomes. Only computed when full cost is available."""
    routes = p46.compute_policy_routes(tasks)
    deltas: dict[str, Any] = {}
    compared: list[str] = []
    baseline_cost_present = sum(
        1
        for t in tasks
        if t.get("outcomes", {}).get("candidate_baseline", {}).get("cost_available")
    )
    baseline_cost_available = bool(tasks) and baseline_cost_present == len(tasks)
    for policy, block in routes.items():
        compared.append(policy)
        avail = block.get("availability")
        if avail != "available" or not baseline_cost_available:
            deltas[policy] = {
                "availability": "missing_or_partial_cost_fields",
                "reason": "Route policy or candidate_baseline span cost is not fully available; delta not computed.",
            }
            continue
        # Compare route-selected cost totals to the same strategies summed across all tasks.
        selected_added_gold = sum(
            info.get("added_gold_span") or 0
            for info in block.get("action_span_cost", {}).values()
            if info.get("added_gold_span") is not None
        )
        selected_added_false = sum(
            info.get("added_false_span") or 0
            for info in block.get("action_span_cost", {}).values()
            if info.get("added_false_span") is not None
        )

        baseline_added_gold = sum(
            (t["outcomes"].get("candidate_baseline", {}).get("added_gold_span") or 0)
            for t in tasks
            if t.get("outcomes", {}).get("candidate_baseline", {}).get("cost_available")
        )
        baseline_added_false = sum(
            (t["outcomes"].get("candidate_baseline", {}).get("added_false_span") or 0)
            for t in tasks
            if t.get("outcomes", {}).get("candidate_baseline", {}).get("cost_available")
        )

        deltas[policy] = {
            "availability": "available",
            "selected_added_gold_span": selected_added_gold,
            "selected_added_false_span": selected_added_false,
            "candidate_baseline_added_gold_span": baseline_added_gold,
            "candidate_baseline_added_false_span": baseline_added_false,
            "delta_added_gold_span": _as_int(selected_added_gold - baseline_added_gold),
            "delta_added_false_span": _as_int(selected_added_false - baseline_added_false),
            "delta_net_value_1x": _as_int((selected_added_gold - selected_added_false) - (baseline_added_gold - baseline_added_false)),
            "selection_rate_on_suite": _rate(block.get("selected_task_count", 0), len(tasks)) if tasks else None,
        }
    child_avails = [b.get("availability") for b in deltas.values()]
    if not routes:
        top_availability = "missing"
    elif child_avails and all(a == "available" for a in child_avails):
        top_availability = "available"
    elif child_avails and any(a == "available" for a in child_avails):
        top_availability = "partial"
    else:
        top_availability = "missing_or_partial_cost_fields"
    return {"by_policy": deltas, "compared_policies": compared, "availability": top_availability}


def _p46_carry_forward(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    reach_cost = p46.compute_reach_cost_map(tasks)
    materialization = p46.compute_materialization_diagnostics(tasks)
    cb5 = (
        reach_cost.get("by_strategy", {})
        .get("candidate_baseline", {})
        .get("by_k", {})
        .get(5, {})
    )
    materialization_availability = materialization.get("materialization_availability", "missing")
    materialization_overall = materialization.get("overall", {})
    measured_materialization = materialization_availability == "available"
    return {
        "reach_cost_map": {
            "availability": "available" if reach_cost.get("reach_metrics_available") else "missing",
            "strategy_availability": reach_cost.get("strategy_availability", {}),
            "reach_metrics_available": reach_cost.get("reach_metrics_available", False),
            "candidate_baseline_k5_gold_file_reach_denominator": cb5.get("gold_file_reach", {}).get("denominator"),
        },
        "materialization_availability": materialization_availability,
        "materialization_overall": {
            "availability": materialization_availability,
            "candidates_seen": materialization_overall.get("candidates_seen", 0),
            "materialized_valid": materialization_overall.get("materialized_valid") if measured_materialization else None,
            "materialization_rate": materialization_overall.get("materialization_rate") if measured_materialization else None,
            "unavailable_reason": None if measured_materialization else materialization_availability,
        },
        "p46_schema_version": p46.SCHEMA_VERSION,
    }


def _p47_carry_forward(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    variant_map = p47.compute_variant_map(
        tasks,
        small_window=3,
        medium_window=10,
        medium_max_width=50,
    )
    gap_breakdown = p47.compute_gap_type_breakdown(
        tasks,
        small_window=3,
        medium_window=10,
    )
    hypothetical = p47.compute_hypothetical_upper_bound(
        tasks,
        small_window=3,
        k=5,
    )
    return {
        "variant_map": {
            "availability": "available" if variant_map.get("variant_metrics_available") else "missing",
            "strategy_availability": variant_map.get("strategy_availability", {}),
            "variant_metrics_available": variant_map.get("variant_metrics_available", False),
        },
        "gap_type_breakdown": {
            "availability": "available" if gap_breakdown.get("gap_breakdown_available") else "missing",
            "strategy_availability": gap_breakdown.get("strategy_availability", {}),
            "gap_breakdown_available": gap_breakdown.get("gap_breakdown_available", False),
        },
        "hypothetical_upper_bound": {
            "availability": "available" if hypothetical["by_strategy"] else "missing",
            "k": hypothetical.get("k"),
        },
        "span_geometry_only": True,
        "expanded_candidate_not_evidence": True,
        "p47_schema_version": p47.SCHEMA_VERSION,
    }


def _compute_quality_gate_status(
    tasks: list[dict[str, Any]],
    suite_composition: dict[str, Any],
    policy_route_comparison: dict[str, Any],
    self_test: bool,
    status: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    def fail(reason: str) -> None:
        reasons.append(reason)

    if self_test:
        fail("self_test_only")
    if status != "ok":
        fail(f"status={status}")
    if suite_composition["task_count"] < 6:
        fail(f"task_count={suite_composition['task_count']} < 6")
    if suite_composition["repo_count"] < 2:
        fail(f"repo_count={suite_composition['repo_count']} < 2")
    if suite_composition["positive_task_count"] <= 0:
        fail("positive_task_count <= 0")
    if suite_composition["no_gold_task_count"] <= 0:
        fail("no_gold_task_count <= 0")
    if suite_composition["candidate_pool_availability"] == "missing_candidate_pool":
        fail("candidate_pool_availability=missing")
    if suite_composition["gold_span_availability"] == "missing_gold_spans":
        fail("gold_span_availability=missing")

    # Compared route policies must have zero selected_action/outcome/cost fallback.
    for policy, block in policy_route_comparison.get("by_policy", {}).items():
        ofr = block.get("outcome_fallback_rate")
        cfr = block.get("cost_fallback_rate")
        if not (isinstance(ofr, (int, float)) and ofr in {0, 0.0} and isinstance(cfr, (int, float)) and cfr in {0, 0.0}):
            fail(f"{policy} has non-zero outcome/cost fallback")

    if reasons:
        return {"quality_gate_status": "insufficient_fixed_suite", "quality_gate_reasons": reasons}
    return {"quality_gate_status": "pass", "quality_gate_reasons": []}


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p50") != 0:
        errors.append("remote_calls_by_p50 must be 0")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "source_reads_attempted_by_p50": False,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    for forbidden in ("tasks", "records", "per_task_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    if report.get("p48_variant_availability") != "not_implemented":
        errors.append("p48_variant_availability must be 'not_implemented'")

    errors.extend(_reject_forbidden_keys(report))
    return errors


def build_report(
    tasks: list[dict[str, Any]],
    input_paths: list[Path],
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    insufficient_paths: list[str] | None,
) -> dict[str, Any]:
    suite_composition = _compute_suite_composition(tasks)
    policy_route_comparison = _policy_route_comparison(tasks)
    baseline_delta = _baseline_policy_delta(tasks)
    key_outcome_cost = _key_strategy_outcome_cost(tasks)
    p46_carry = _p46_carry_forward(tasks)
    p47_carry = _p47_carry_forward(tasks)

    quality_gate = _compute_quality_gate_status(
        tasks,
        suite_composition,
        policy_route_comparison,
        self_test,
        status,
    )

    manifest_hash = _compute_suite_manifest_hash(tasks, input_paths)
    config_hash = _compute_evaluator_config_hash(
        k_values=list(p46.K_VALUES),
        reach_strategies=list(p46.REACH_STRATEGIES),
        outcome_strategies=list(p46.OUTCOME_STRATEGIES),
        key_strategies=list(KEY_STRATEGIES),
        policies=["bucket_routed_v0", "admission_v3_h4b"],
        variant_names=list(p47.VARIANTS),
        settings={"score_phase_only": True, "aggregate_only": True, "source_reads": False, "remote_calls": False},
    )

    p31_h1_handoff_detected = bool(
        tasks and any(t.get("has_candidate_pool") and t.get("has_gold_spans") for t in tasks)
    )
    p33b_handoff_detected = bool(tasks and any(t.get("subtypes") for t in tasks))

    conclusion_lines: list[str] = []
    if quality_gate["quality_gate_status"] == "pass":
        conclusion_lines.append(
            f"P50 fixed-suite anti-overfit gate passed for {suite_composition['task_count']} tasks across {suite_composition['repo_count']} repos."
        )
    else:
        conclusion_lines.append(
            f"P50 fixed-suite anti-overfit gate is `{quality_gate['quality_gate_status']}`; this is a scaffold/health report."
        )
        conclusion_lines.extend(quality_gate["quality_gate_reasons"])

    conclusion_lines.extend([
        "P50 is an evaluation discipline phase, not a policy improvement phase.",
        "P48 is explicitly not implemented; no policy promotion is inferred from candidate/span-geometry signals.",
        f"Suite manifest hash (sha256): `{manifest_hash['sha256']}`.",
        f"Evaluator config hash (sha256): `{config_hash['sha256']}`.",
        f"Candidate pool availability: `{suite_composition['candidate_pool_availability']}`; gold span availability: `{suite_composition['gold_span_availability']}`.",
        "All outputs are aggregate-only; no per-task rows, task IDs, candidate IDs, paths, gold spans, private labels, snippets, prompts, responses, or provider keys are published.",
    ])

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P50 Fixed-Suite Validation / Anti-Overfit Gate",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": len(input_paths),
        "insufficient_input_source_count": len(insufficient_paths or []),
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "remote_calls_by_p50": 0,
        "source_reads_attempted_by_p50": False,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "labels_loaded_after_run": bool(any(t["has_gold"] for t in tasks)),
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "elapsed_ms": elapsed_ms,
        "suite_manifest_hash": manifest_hash,
        "evaluator_config_hash": config_hash,
        "suite_composition": suite_composition,
        "policy_route_comparison": policy_route_comparison,
        "baseline_policy_delta": baseline_delta,
        "key_strategy_outcome_cost": key_outcome_cost,
        "p46_carry_forward": p46_carry,
        "p47_carry_forward": p47_carry,
        "p48_variant_availability": "not_implemented",
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": sum(1 for t in tasks if t.get("has_candidate_pool") and t.get("has_gold_spans")),
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": sum(1 for t in tasks if t.get("subtypes")),
        "quality_gate_status": quality_gate["quality_gate_status"],
        "quality_gate_reasons": quality_gate["quality_gate_reasons"],
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P50 public report validation failed: {errors}")
    return report


def _fmt_rate(x: Any) -> str:
    r = x.get("rate") if isinstance(x, dict) else None
    return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"


def _fmt_int(x: Any) -> str:
    return str(x) if isinstance(x, int) else "n/a"


def _fmt_scalar(x: Any) -> str:
    return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P50 Fixed-Suite Validation / Anti-Overfit Gate\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Quality gate: `{report['quality_gate_status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P50: {report['remote_calls_by_p50']}",
        f"- Source reads by P50: {report['source_reads_attempted_by_p50']}",
        f"- Tasks: {report['suite_composition']['task_count']} positive={report['suite_composition']['positive_task_count']} no_gold={report['suite_composition']['no_gold_task_count']} repos={report['suite_composition']['repo_count']}",
        "",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P50 validates that an evaluation suite is healthy and fixed enough to serve as an anti-overfit gate. ",
        "It is a deterministic, SCORE-phase-only discipline phase, not a policy improvement phase.",
        "",
        "## Methodology\n",
        "- Loads `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Computes hashes over the suite manifest and evaluator configuration; publishes only the digests.",
        "- Reports aggregate suite composition, availability, and fallback rates.",
        "- Compares the aggregate span cost of `bucket_routed_v0` and `admission_v3_h4b` route policies.",
        "- Carries forward P46 reach/cost/materialization and P47 span-geometry diagnostics with explicit not-evidence flags.",
        "- P48 is marked `not_implemented`; no admission policy is promoted from geometry signals.",
        "",
        "## Suite composition\n",
        f"- Input records: {report['suite_composition']['input_record_count']}",
        f"- Tasks: {report['suite_composition']['task_count']}",
        f"- Repositories: {report['suite_composition']['repo_count']} (count only; no repo IDs are published)",
        f"- Positive / no-gold tasks: {report['suite_composition']['positive_task_count']} / {report['suite_composition']['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['suite_composition']['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['suite_composition']['gold_span_availability']}`",
        f"- P33-B subtype availability: `{report['suite_composition']['p33b_subtype_availability']}`",
        f"- Outcome availability: `{report['suite_composition']['outcome_availability']}`",
        f"- Fallback outcome rate: {_fmt_rate(report['suite_composition']['fallback_outcome_rate'])}",
        f"- Missing cost-field rate: {_fmt_rate(report['suite_composition']['missing_cost_field_rate'])}",
        "",
        "## Hashes\n",
        f"- Suite manifest sha256: `{report['suite_manifest_hash']['sha256']}`",
        f"- Evaluator config sha256: `{report['evaluator_config_hash']['sha256']}`",
        f"- Note: {report['suite_manifest_hash']['published_note']}",
        "",
    ])

    lines.append("## Public bucket distribution\n")
    lines.append("| Bucket | Count |")
    lines.append("|---|---:|")
    for bucket, count in sorted(report["suite_composition"]["public_bucket_distribution"].items()):
        lines.append(f"| {bucket} | {count} |")
    lines.append("")

    lines.append("## Risk tag distribution\n")
    lines.append("| Tag | Count |")
    lines.append("|---|---:|")
    for tag, count in sorted(report["suite_composition"]["risk_tag_distribution"].items()):
        lines.append(f"| {tag} | {count} |")
    lines.append("")

    lines.append("## Policy route comparison\n")
    lines.append("| Policy | Selected | OutcomeFallback | CostFallback | Actions |")
    lines.append("|---|---:|---:|---:|---:|")
    for policy, block in sorted(report["policy_route_comparison"]["by_policy"].items()):
        actions = block.get("action_distribution", {})
        action_str = ", ".join(f"{a}={c}" for a, c in sorted(actions.items())) if actions else "n/a"
        lines.append(
            f"| {policy} | {block.get('selected_task_count', 0)} | {_fmt_rate(block.get('outcome_fallback_rate'))} | "
            f"{_fmt_rate(block.get('cost_fallback_rate'))} | {action_str} |"
        )
    lines.append("")

    lines.append("## Key-strategy outcome cost\n")
    lines.append("| Strategy | Availability | Tasks | + | no_gold | OutcomeMissing | CostMissing | added_gold | added_false | net_1x |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in KEY_STRATEGIES:
        b = report["key_strategy_outcome_cost"]["by_strategy"].get(strategy, {})
        lines.append(
            f"| {strategy} | {b.get('availability')} | {b.get('task_count', 0)} | {b.get('positive_task_count', 0)} | "
            f"{b.get('no_gold_task_count', 0)} | {b.get('outcome_missing_count', 0)} | {b.get('cost_missing_count', 0)} | "
            f"{_fmt_int(b.get('added_gold_span'))} | {_fmt_int(b.get('added_false_span'))} | {_fmt_int(b.get('net_span_value_1x'))} |"
        )
    lines.append("")

    lines.append("## Baseline/policy delta\n")
    if report["baseline_policy_delta"].get("availability") != "available":
        lines.append(f"Availability: `{report['baseline_policy_delta']['availability']}` — delta not computed.\n")
    else:
        lines.append("| Policy | Delta added_gold | Delta added_false | Delta net_1x | Selection rate |")
        lines.append("|---|---:|---:|---:|---:|")
        for policy, block in sorted(report["baseline_policy_delta"]["by_policy"].items()):
            lines.append(
                f"| {policy} | {_fmt_int(block.get('delta_added_gold_span'))} | "
                f"{_fmt_int(block.get('delta_added_false_span'))} | {_fmt_int(block.get('delta_net_value_1x'))} | {_fmt_rate(block.get('selection_rate_on_suite'))} |"
            )
        lines.append("")

    lines.append("## P46 carry-forward (aggregate only)\n")
    p46c = report["p46_carry_forward"]
    lines.append(
        f"- Reach/cost map availability: `{p46c['reach_cost_map']['availability']}`; "
        f"materialization availability: `{p46c['materialization_availability']}`"
    )
    lines.append(
        f"- Materialization overall: seen={p46c['materialization_overall']['candidates_seen']}, "
        f"valid={p46c['materialization_overall']['materialized_valid']}, "
        f"rate={_fmt_rate(p46c['materialization_overall']['materialization_rate'])}, "
        f"unavailable_reason={p46c['materialization_overall']['unavailable_reason']}"
    )
    lines.append("")

    lines.append("## P47 carry-forward (aggregate only)\n")
    p47c = report["p47_carry_forward"]
    lines.append(
        f"- Variant map availability: `{p47c['variant_map']['availability']}`; "
        f"gap breakdown availability: `{p47c['gap_type_breakdown']['availability']}`; "
        f"hypothetical upper bound availability: `{p47c['hypothetical_upper_bound']['availability']}`"
    )
    lines.append(f"- span_geometry_only: `{p47c['span_geometry_only']}`")
    lines.append(f"- expanded_candidate_not_evidence: `{p47c['expanded_candidate_not_evidence']}`")
    lines.append("")

    lines.append("## P48 status\n")
    lines.append(f"- `p48_variant_availability='{report['p48_variant_availability']}'`")
    lines.append("- P48 admission-policy improvement is intentionally not implemented before P50 gating is established.")
    lines.append("")

    lines.append("## Quality gate\n")
    lines.append(f"- Status: `{report['quality_gate_status']}`")
    if report["quality_gate_reasons"]:
        lines.append("- Reasons:")
        for r in report["quality_gate_reasons"]:
            lines.append(f"  - {r}")
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.extend([
        "- No remote model calls were made during P50 evaluation.",
        "- No source files were read by P50.",
        "- This report contains only aggregate counts/rates; no per-task rows are published.",
        "- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, repo IDs, or provider keys are stored.",
        "- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`.",
        "- `remote_calls_by_p50=0`, `source_reads_attempted_by_p50=false`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P50 Fixed-Suite Validation / Anti-Overfit Gate")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_records = p46.make_self_test_records()
    elif args.input:
        input_paths = list(args.input)
        raw_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_paths: list[str] = []
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P50 fixed-suite validation.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P50 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_task_detail"
            reason = marker_reasons[marker]
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (p46.normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P50 normalization."

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        normalized_tasks,
        input_paths,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        insufficient_paths=insufficient_paths,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P50 report written to {args.out}")
    print(f"P50 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
