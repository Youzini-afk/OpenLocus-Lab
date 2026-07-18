#!/usr/bin/env python3
"""Cluster-aware B4 analysis, ranking, Pareto, and deployment-gate engine."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import NormalDist
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402
import product_bakeoff_b4_runner as b4r  # noqa: E402


B4_SCORER_VERSION = "product_bakeoff_b4_scorer.v1"
B4_PRIVATE_ANALYSIS_SCHEMA = "product_bakeoff_b4_private_analysis.v1"
B4_PRIVATE_ANALYSIS_STATUS = "product_bakeoff_b4_complete_comparative_analysis_private"
B4_PARENT_PROTOCOL_DIGEST = (
    "b4protocol_cf983176938c83c415b44bfb50b64baa866bebac9e1567e85a119f5073683cc1"
)


class B4ScoreError(ValueError):
    """Fail-closed B4 analysis error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop("analysis_digest", None)
    return "b4analysis_" + hashlib.sha256(_canonical(payload)).hexdigest()


def _student_t_critical(level: float, df: int) -> float:
    if not 0.0 < level < 1.0 or df <= 0:
        raise B4ScoreError("invalid B4 confidence interval request")
    z = NormalDist().inv_cdf(1.0 - (1.0 - level) / 2.0)
    first = (z**3 + z) / (4.0 * df)
    second = (5.0 * z**5 + 16.0 * z**3 + 3.0 * z) / (96.0 * df**2)
    return z + first + second


def _mean_and_interval(values: Sequence[float], level: float) -> tuple[float, float, float]:
    if len(values) < 2:
        raise B4ScoreError("B4 interval requires at least two clusters")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    if variance == 0.0:
        return mean, mean, mean
    standard_error = math.sqrt(variance / len(values))
    half = _student_t_critical(level, len(values) - 1) * standard_error
    return mean, mean - half, mean + half


def _scaled_effect(
    cluster_values: Sequence[float],
    *,
    scale: int,
    clamp: tuple[int, int] | None = None,
) -> dict[str, Any]:
    mean, low95, high95 = _mean_and_interval(cluster_values, 0.95)
    _, low_sim, high_sim = _mean_and_interval(
        cluster_values, b4p.POWER_SIMULTANEOUS_CI_LEVEL_PPM / 1_000_000
    )

    def convert(value: float) -> int:
        result = int(round(value * scale))
        if clamp is not None:
            result = max(clamp[0], min(clamp[1], result))
        return result

    return {
        "estimate_ppm": convert(mean),
        "estimation_95ci_ppm": [convert(low95), convert(high95)],
        "simultaneous_97_5ci_ppm": [convert(low_sim), convert(high_sim)],
        "repository_cluster_count": len(cluster_values),
    }


def _log_ratio_interval_ppm(log_ratios: Sequence[float]) -> dict[str, Any]:
    mean, low, high = _mean_and_interval(log_ratios, 0.95)

    def ratio(value: float) -> int:
        return int(round(math.exp(value) * 1_000_000))

    return {
        "geometric_mean_ratio_ppm": ratio(mean),
        "upper_95ci_ppm": ratio(high),
        "lower_95ci_ppm": ratio(low),
        "repository_cluster_count": len(log_ratios),
    }


def _nearest_rank_p95(values: Sequence[int]) -> int:
    if not values:
        raise B4ScoreError("B4 P95 input is empty")
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _wilson_upper_ppm(successes: int, total: int, *, level: float) -> int:
    if not 0 <= successes <= total or total <= 0:
        raise B4ScoreError("invalid B4 Wilson-bound input")
    z = NormalDist().inv_cdf(level)
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return min(1_000_000, int(math.ceil((center + half) * 1_000_000)))


def _competition_ranks(
    arm_rows: Mapping[str, Mapping[str, Any]],
    key: Callable[[Mapping[str, Any]], tuple[Any, ...]],
) -> dict[str, int]:
    ordered = sorted(arm_rows, key=lambda arm_id: (key(arm_rows[arm_id]), arm_id))
    ranks: dict[str, int] = {}
    previous_key: tuple[Any, ...] | None = None
    previous_rank = 0
    for index, arm_id in enumerate(ordered, start=1):
        current = key(arm_rows[arm_id])
        if previous_key is None or current != previous_key:
            previous_rank = index
            previous_key = current
        ranks[arm_id] = previous_rank
    return ranks


def _outcome_map(
    result: b4r.B4RunResult,
) -> dict[tuple[int, int, str], b4r.B4TaskOutcome]:
    return {
        (row.panel_index, row.task_index, row.arm_id): row
        for row in result.outcomes
    }


def _cluster_differences(
    rows: Mapping[tuple[int, int, str], b4r.B4TaskOutcome],
    candidate: str,
    metric: Callable[[b4r.B4TaskOutcome], float],
) -> list[float]:
    values: list[float] = []
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        for repository_index in range(1, b4p.B4_REPOSITORIES_PER_PANEL + 1):
            task_values: list[float] = []
            first_task = (repository_index - 1) * b4p.B4_TASKS_PER_REPOSITORY + 1
            for task_index in range(first_task, first_task + b4p.B4_TASKS_PER_REPOSITORY):
                candidate_row = rows[(panel_index, task_index, candidate)]
                baseline_row = rows[(panel_index, task_index, b4p.B4_BASELINE_ARM)]
                task_values.append(metric(candidate_row) - metric(baseline_row))
            values.append(sum(task_values) / len(task_values))
    return values


def _utility(row: b4r.B4TaskOutcome) -> tuple[int, int, int, int]:
    return (
        int(row.task_success),
        int(not row.harmful_evidence),
        int(row.status_or_target_success),
        row.context_f05_ppm,
    )


def _utility_value(row: b4r.B4TaskOutcome, baseline: b4r.B4TaskOutcome) -> float:
    left = _utility(row)
    right = _utility(baseline)
    return 1.0 if left > right else (-1.0 if left < right else 0.0)


def _cluster_utility_net_wins(
    rows: Mapping[tuple[int, int, str], b4r.B4TaskOutcome], candidate: str
) -> list[float]:
    values: list[float] = []
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        for repository_index in range(1, b4p.B4_REPOSITORIES_PER_PANEL + 1):
            task_values: list[float] = []
            first_task = (repository_index - 1) * b4p.B4_TASKS_PER_REPOSITORY + 1
            for task_index in range(first_task, first_task + b4p.B4_TASKS_PER_REPOSITORY):
                candidate_row = rows[(panel_index, task_index, candidate)]
                baseline_row = rows[(panel_index, task_index, b4p.B4_BASELINE_ARM)]
                task_values.append(_utility_value(candidate_row, baseline_row))
            values.append(sum(task_values) / len(task_values))
    return values


def _panel_directions(
    rows: Mapping[tuple[int, int, str], b4r.B4TaskOutcome], candidate: str
) -> dict[str, int]:
    counts = Counter()
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        differences = [
            int(rows[(panel_index, task_index, candidate)].task_success)
            - int(rows[(panel_index, task_index, b4p.B4_BASELINE_ARM)].task_success)
            for task_index in range(1, b4p.B4_TASKS_PER_PANEL + 1)
        ]
        mean = sum(differences) / len(differences)
        counts["positive" if mean > 0 else ("negative" if mean < 0 else "zero")] += 1
    return {
        "positive": counts["positive"],
        "zero": counts["zero"],
        "negative": counts["negative"],
        "panel_count": b4p.B4_PANEL_COUNT,
    }


def _arm_summary(
    result: b4r.B4RunResult, arm_id: str
) -> dict[str, Any]:
    arm_rows = [row for row in result.outcomes if row.arm_id == arm_id]
    warm = [row.query_us for row in arm_rows if row.cache_state == "warm"]
    if len(warm) != b4p.B4_PANEL_COUNT * 36:
        raise B4ScoreError("B4 warm-query count drifted")
    repo_peak: list[int] = []
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        for repository_index in range(1, b4p.B4_REPOSITORIES_PER_PANEL + 1):
            values = [
                row.peak_rss_bytes
                for row in arm_rows
                if row.panel_index == panel_index
                and row.repository_index == repository_index
            ]
            if len(values) != b4p.B4_TASKS_PER_REPOSITORY:
                raise B4ScoreError("B4 repository/arm resource cardinality drifted")
            repo_peak.append(max(values))
    count = len(arm_rows)
    return {
        "arm_id": arm_id,
        "task_count": count,
        "task_success_count": sum(row.task_success for row in arm_rows),
        "task_success_rate_ppm": sum(row.task_success for row in arm_rows)
        * 1_000_000
        // count,
        "harmful_evidence_task_count": sum(row.harmful_evidence for row in arm_rows),
        "harmful_evidence_rate_ppm": sum(row.harmful_evidence for row in arm_rows)
        * 1_000_000
        // count,
        "status_or_target_success_count": sum(
            row.status_or_target_success for row in arm_rows
        ),
        "status_or_target_success_rate_ppm": sum(
            row.status_or_target_success for row in arm_rows
        )
        * 1_000_000
        // count,
        "context_f05_mean_ppm": sum(row.context_f05_ppm for row in arm_rows)
        // count,
        "warm_query_geometric_mean_us": int(
            round(math.exp(sum(math.log(value) for value in warm) / len(warm)))
        ),
        "peak_rss_p95_bytes": _nearest_rank_p95(repo_peak),
    }


def _resource_ratios(
    result: b4r.B4RunResult, candidate: str
) -> dict[str, Any]:
    by_key = _outcome_map(result)
    warm_log_ratios: list[float] = []
    rss_log_ratios: list[float] = []
    schedule = {(row.panel_index, row.task_index): row for row in b4p.build_schedule()}
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        for repository_index in range(1, b4p.B4_REPOSITORIES_PER_PANEL + 1):
            first_task = (repository_index - 1) * b4p.B4_TASKS_PER_REPOSITORY + 1
            task_indexes = range(first_task, first_task + b4p.B4_TASKS_PER_REPOSITORY)
            warm_tasks = [
                task_index
                for task_index in task_indexes
                if schedule[(panel_index, task_index)].cache_state == "warm"
            ]
            if len(warm_tasks) != 3:
                raise B4ScoreError("B4 paired warm-query cardinality drifted")
            candidate_log = sum(
                math.log(by_key[(panel_index, task_index, candidate)].query_us)
                for task_index in warm_tasks
            ) / len(warm_tasks)
            baseline_log = sum(
                math.log(
                    by_key[(panel_index, task_index, b4p.B4_BASELINE_ARM)].query_us
                )
                for task_index in warm_tasks
            ) / len(warm_tasks)
            warm_log_ratios.append(candidate_log - baseline_log)
            candidate_rss = max(
                by_key[(panel_index, task_index, candidate)].peak_rss_bytes
                for task_index in task_indexes
            )
            baseline_rss = max(
                by_key[
                    (panel_index, task_index, b4p.B4_BASELINE_ARM)
                ].peak_rss_bytes
                for task_index in range(
                    first_task, first_task + b4p.B4_TASKS_PER_REPOSITORY
                )
            )
            rss_log_ratios.append(math.log(candidate_rss / baseline_rss))
    return {
        "warm_query_ratio": _log_ratio_interval_ppm(warm_log_ratios),
        "peak_rss_ratio": _log_ratio_interval_ppm(rss_log_ratios),
    }


def _comparison(
    result: b4r.B4RunResult,
    candidate: str,
) -> dict[str, Any]:
    rows = _outcome_map(result)
    task_success = _scaled_effect(
        _cluster_differences(rows, candidate, lambda row: float(row.task_success)),
        scale=1_000_000,
        clamp=(-1_000_000, 1_000_000),
    )
    utility = _scaled_effect(
        _cluster_utility_net_wins(rows, candidate),
        scale=1_000_000,
        clamp=(-1_000_000, 1_000_000),
    )
    status = _scaled_effect(
        _cluster_differences(
            rows, candidate, lambda row: float(row.status_or_target_success)
        ),
        scale=1_000_000,
        clamp=(-1_000_000, 1_000_000),
    )
    context = _scaled_effect(
        _cluster_differences(
            rows, candidate, lambda row: float(row.context_f05_ppm)
        ),
        scale=1,
        clamp=(-1_000_000, 1_000_000),
    )
    harmful = _scaled_effect(
        _cluster_differences(
            rows, candidate, lambda row: float(row.harmful_evidence)
        ),
        scale=1_000_000,
        clamp=(-1_000_000, 1_000_000),
    )
    extra_harm_count = sum(
        rows[(panel_index, task_index, candidate)].harmful_evidence
        and not rows[
            (panel_index, task_index, b4p.B4_BASELINE_ARM)
        ].harmful_evidence
        for panel_index in range(1, b4p.B4_PANEL_COUNT + 1)
        for task_index in range(1, b4p.B4_TASKS_PER_PANEL + 1)
    )
    avoided_harm_count = sum(
        not rows[(panel_index, task_index, candidate)].harmful_evidence
        and rows[
            (panel_index, task_index, b4p.B4_BASELINE_ARM)
        ].harmful_evidence
        for panel_index in range(1, b4p.B4_PANEL_COUNT + 1)
        for task_index in range(1, b4p.B4_TASKS_PER_PANEL + 1)
    )
    harmful["candidate_only_harm_task_count"] = extra_harm_count
    harmful["baseline_only_harm_task_count"] = avoided_harm_count
    harmful["conservative_extra_harm_upper_simultaneous_97_5ci_ppm"] = (
        _wilson_upper_ppm(
            extra_harm_count,
            b4p.B4_LOGICAL_TASK_COUNT,
            level=1.0 - b4p.POWER_PER_COMPARISON_ALPHA_PPM / 2_000_000,
        )
    )
    panel_directions = _panel_directions(rows, candidate)
    resources = _resource_ratios(result, candidate)
    gate = b4p.B4_DEPLOYMENT_GATES[candidate]
    failures: list[str] = []
    if task_success["estimate_ppm"] < gate["minimum_task_success_effect_ppm"]:
        failures.append("task_success_effect_below_material_minimum")
    if task_success["simultaneous_97_5ci_ppm"][0] <= 0:
        failures.append("task_success_simultaneous_lower_not_positive")
    if panel_directions["positive"] < gate["minimum_positive_panels"]:
        failures.append("positive_panel_count_below_minimum")
    if harmful[
        "conservative_extra_harm_upper_simultaneous_97_5ci_ppm"
    ] > gate[
        "harmful_evidence_risk_difference_upper_simultaneous_97_5ci_ppm"
    ]:
        failures.append("harmful_evidence_noninferiority_failed")
    if resources["warm_query_ratio"]["upper_95ci_ppm"] > gate[
        "warm_query_ratio_upper_95ci_ppm"
    ]:
        failures.append("warm_query_ratio_upper_ci_above_limit")
    if resources["peak_rss_ratio"]["upper_95ci_ppm"] > gate[
        "peak_rss_ratio_upper_95ci_ppm"
    ]:
        failures.append("peak_rss_ratio_upper_ci_above_limit")
    return {
        "candidate_arm": candidate,
        "baseline_arm": b4p.B4_BASELINE_ARM,
        "track": gate["track"],
        "task_success_effect": task_success,
        "task_utility_net_win_rate": utility,
        "status_or_target_success_effect": status,
        "context_f05_effect": context,
        "harmful_evidence_risk_difference": harmful,
        "panel_directions": panel_directions,
        "resource_ratios": resources,
        "deployment_eligible": not failures,
        "deployment_failure_reasons": sorted(failures),
    }


def _pareto_frontier(arm_rows: Mapping[str, Mapping[str, Any]]) -> list[str]:
    def dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        comparisons = (
            left["task_success_rate_ppm"] >= right["task_success_rate_ppm"],
            left["harmful_evidence_rate_ppm"] <= right["harmful_evidence_rate_ppm"],
            left["warm_query_geometric_mean_us"]
            <= right["warm_query_geometric_mean_us"],
            left["peak_rss_p95_bytes"] <= right["peak_rss_p95_bytes"],
        )
        strict = (
            left["task_success_rate_ppm"] > right["task_success_rate_ppm"]
            or left["harmful_evidence_rate_ppm"] < right["harmful_evidence_rate_ppm"]
            or left["warm_query_geometric_mean_us"]
            < right["warm_query_geometric_mean_us"]
            or left["peak_rss_p95_bytes"] < right["peak_rss_p95_bytes"]
        )
        return all(comparisons) and strict

    return sorted(
        arm_id
        for arm_id, row in arm_rows.items()
        if not any(
            other_id != arm_id and dominates(other, row)
            for other_id, other in arm_rows.items()
        )
    )


def score_b4(result: b4r.B4RunResult) -> dict[str, Any]:
    try:
        b4r.require_valid_run_result(result)
    except b4r.B4RunError as exc:
        raise B4ScoreError("B4 scorer rejected run matrix") from exc
    arm_rows = {arm_id: _arm_summary(result, arm_id) for arm_id in b4p.B4_ARMS}
    quality_ranks = _competition_ranks(
        arm_rows,
        lambda row: (
            -row["task_success_rate_ppm"],
            row["harmful_evidence_rate_ppm"],
            -row["status_or_target_success_rate_ppm"],
            -row["context_f05_mean_ppm"],
        ),
    )
    resource_ranks = _competition_ranks(
        arm_rows,
        lambda row: (
            row["warm_query_geometric_mean_us"],
            row["peak_rss_p95_bytes"],
        ),
    )
    comparisons = {
        candidate: _comparison(result, candidate)
        for candidate in b4p.B4_CANDIDATE_ARMS
    }
    shortlist = sorted(
        candidate
        for candidate, row in comparisons.items()
        if row["deployment_eligible"]
    )
    analysis: dict[str, Any] = {
        "schema_version": B4_PRIVATE_ANALYSIS_SCHEMA,
        "status": B4_PRIVATE_ANALYSIS_STATUS,
        "scorer_version": B4_SCORER_VERSION,
        "protocol_digest": B4_PARENT_PROTOCOL_DIGEST,
        "matrix": {
            "panel_count": b4p.B4_PANEL_COUNT,
            "repository_cluster_count": b4p.B4_REPOSITORY_CLUSTER_COUNT,
            "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
            "task_outcome_count": len(result.outcomes),
            "logical_group_count": result.logical_group_count,
            "logical_record_count": result.logical_record_count,
            "index_build_count": result.index_build_count,
            "provider_network_call_count": result.provider_network_call_count,
            "all_pre_score_gates_passed": True,
        },
        "arms": [arm_rows[arm_id] for arm_id in b4p.B4_ARMS],
        "comparisons": [comparisons[arm_id] for arm_id in b4p.B4_CANDIDATE_ARMS],
        "quality_competition_ranks": quality_ranks,
        "resource_competition_ranks": resource_ranks,
        "pareto_frontier": _pareto_frontier(arm_rows),
        "phase_c_shortlist": shortlist,
        "decision_status": (
            "phase_c_shortlist_available"
            if shortlist
            else "comparative_result_complete_no_deployment_eligible_candidate"
        ),
        "ranking_published_even_when_gates_fail": True,
        "private_detail_public": False,
        "analysis_digest": "",
    }
    analysis["analysis_digest"] = _digest(analysis)
    return analysis


def validate_analysis(
    analysis: Any, *, result: b4r.B4RunResult | None = None
) -> list[str]:
    if not isinstance(analysis, dict):
        return ["B4 analysis must be an object"]
    errors: list[str] = []
    if analysis.get("analysis_digest") != _digest(analysis):
        errors.append("B4 analysis digest mismatch")
    if analysis.get("schema_version") != B4_PRIVATE_ANALYSIS_SCHEMA:
        errors.append("B4 analysis schema drifted")
    if analysis.get("status") != B4_PRIVATE_ANALYSIS_STATUS:
        errors.append("B4 analysis status drifted")
    if analysis.get("private_detail_public") is not False:
        errors.append("B4 analysis private-detail flag drifted")
    ranks = analysis.get("quality_competition_ranks")
    if not isinstance(ranks, dict) or set(ranks) != set(b4p.B4_ARMS):
        errors.append("B4 quality ranks incomplete")
    resource_ranks = analysis.get("resource_competition_ranks")
    if not isinstance(resource_ranks, dict) or set(resource_ranks) != set(b4p.B4_ARMS):
        errors.append("B4 resource ranks incomplete")
    if result is not None:
        try:
            expected = score_b4(result)
        except (B4ScoreError, ValueError, TypeError) as exc:
            errors.append(f"cannot rebuild B4 analysis: {type(exc).__name__}")
        else:
            if analysis != expected:
                errors.append("B4 analysis drifted from run result")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    result = b4r.synthetic_run_result()
    analysis = score_b4(result)
    comparisons = {row["candidate_arm"]: row for row in analysis["comparisons"]}
    tie = score_b4(b4r.synthetic_run_result(tie=True))
    checks = [
        not validate_analysis(analysis, result=result),
        comparisons[b2.S1_ADAPTER_ID]["deployment_eligible"],
        comparisons[b2.S4_ADAPTER_ID]["deployment_eligible"],
        comparisons[b2.S1_ADAPTER_ID]["panel_directions"]["positive"] == 12,
        comparisons[b2.S4_ADAPTER_ID]["panel_directions"]["positive"] == 12,
        analysis["quality_competition_ranks"]
        == {b2.S4_ADAPTER_ID: 1, b2.S1_ADAPTER_ID: 2, b4p.B4_BASELINE_ARM: 3},
        analysis["resource_competition_ranks"]
        == {b4p.B4_BASELINE_ARM: 1, b2.S1_ADAPTER_ID: 2, b2.S4_ADAPTER_ID: 3},
        set(analysis["pareto_frontier"]) == set(b4p.B4_ARMS),
        set(analysis["phase_c_shortlist"]) == set(b4p.B4_CANDIDATE_ARMS),
        set(tie["quality_competition_ranks"].values()) == {1},
        set(tie["resource_competition_ranks"].values()) == {1},
        set(tie["pareto_frontier"]) == set(b4p.B4_ARMS),
        tie["phase_c_shortlist"] == [],
        all(tie["quality_competition_ranks"].values()),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "arm_count": len(analysis["arms"]),
        "comparison_count": len(analysis["comparisons"]),
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[bool] = []
    invalid = b4r.synthetic_run_result()
    invalid = b4r.B4RunResult(
        **{**invalid.__dict__, "outcomes": invalid.outcomes[:-1]}
    )
    try:
        score_b4(invalid)
    except B4ScoreError:
        checks.append(True)
    else:
        checks.append(False)

    resource = score_b4(b4r.synthetic_run_result(s1_resource_regression=True))
    resource_s1 = next(
        row for row in resource["comparisons"] if row["candidate_arm"] == b2.S1_ADAPTER_ID
    )
    checks.extend(
        [
            not resource_s1["deployment_eligible"],
            "warm_query_ratio_upper_ci_above_limit"
            in resource_s1["deployment_failure_reasons"],
            bool(resource["quality_competition_ranks"]),
            bool(resource["resource_competition_ranks"]),
        ]
    )

    harmful = score_b4(b4r.synthetic_run_result(s1_harm_regression=True))
    harmful_s1 = next(
        row for row in harmful["comparisons"] if row["candidate_arm"] == b2.S1_ADAPTER_ID
    )
    checks.extend(
        [
            not harmful_s1["deployment_eligible"],
            "harmful_evidence_noninferiority_failed"
            in harmful_s1["deployment_failure_reasons"],
            bool(harmful["pareto_frontier"]),
        ]
    )

    mutated = copy.deepcopy(score_b4(b4r.synthetic_run_result()))
    mutated["analysis_digest"] = "b4analysis_" + "0" * 64
    checks.append(bool(validate_analysis(mutated)))
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B4 cluster-aware scorer")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    args = parser.parse_args(argv)
    report = run_self_test() if args.self_test else run_fault_test()
    _print(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B4_SCORER_VERSION",
    "B4_PRIVATE_ANALYSIS_SCHEMA",
    "B4_PRIVATE_ANALYSIS_STATUS",
    "B4ScoreError",
    "score_b4",
    "validate_analysis",
    "run_self_test",
    "run_fault_test",
]
