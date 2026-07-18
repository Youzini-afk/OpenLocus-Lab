#!/usr/bin/env python3
"""Aggregate-only B4 success publication and failed-closeout schemas."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402
import product_bakeoff_b4_runner as b4r  # noqa: E402
import product_bakeoff_b4_scorer as b4s  # noqa: E402


B4_RESULT_SCHEMA = "product_bakeoff_b4_replication_result.v1"
B4_RESULT_STATUS = "product_bakeoff_b4_replication_complete_aggregate_only"
B4_RESULT_CLAIM = "comparative_evidence_over_twelve_frozen_panels"
B4_FAILURE_SCHEMA = "product_bakeoff_b4_failed_closeout.v1"
B4_FAILURE_STATUS = "product_bakeoff_b4_execution_failed_closed_aggregate_only"
B4_PARENT_PROTOCOL_DIGEST = b4s.B4_PARENT_PROTOCOL_DIGEST

B4_FAILURE_CLASSES = frozenset(
    {
        "preboundary_admission_failure",
        "postboundary_worker_failure",
        "postboundary_integrity_failure",
        "postboundary_resource_failure",
    }
)

B4_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "repository_task_query_oracle_identity_public": False,
    "source_location_range_excerpt_or_raw_output_public": False,
    "private_analysis_or_freeze_digest_public": False,
    "intermediate_panel_metric_public": False,
    "provider_payload_secret_or_credential_public": False,
    "effects_ranks_pareto_and_gate_outcomes_always_public_on_success": True,
}

B4_RESULT_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "claim_level",
        "protocol_digest",
        "inference_target",
        "matrix",
        "arms",
        "comparisons",
        "quality_competition_ranks",
        "resource_competition_ranks",
        "pareto_frontier",
        "phase_c_shortlist",
        "decision_status",
        "ranking_published_even_when_gates_fail",
        "promotion_requires_fresh_phase_c_validation",
        "publication_limits",
        "result_digest",
    }
)
B4_FAILURE_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "claim_level",
        "protocol_digest",
        "failure_class",
        "attempt_boundary_crossed",
        "completed_group_count",
        "logical_record_count",
        "retry_resume_or_recompute_authorized",
        "quality_resource_rank_or_candidate_metric_public",
        "publication_limits",
        "failure_digest",
    }
)


class B4PublicationError(ValueError):
    """Fail-closed B4 public artifact error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Mapping[str, Any], key: str) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _arm_map(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    arms = report.get("arms")
    if not isinstance(arms, list):
        raise B4PublicationError("B4 public arms must be a list")
    result: dict[str, Mapping[str, Any]] = {}
    for row in arms:
        if not isinstance(row, Mapping) or not isinstance(row.get("arm_id"), str):
            raise B4PublicationError("B4 public arm row malformed")
        if row["arm_id"] in result:
            raise B4PublicationError("B4 public arm duplicated")
        result[row["arm_id"]] = row
    return result


def _comparison_map(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    comparisons = report.get("comparisons")
    if not isinstance(comparisons, list):
        raise B4PublicationError("B4 public comparisons must be a list")
    result: dict[str, Mapping[str, Any]] = {}
    for row in comparisons:
        if not isinstance(row, Mapping) or not isinstance(
            row.get("candidate_arm"), str
        ):
            raise B4PublicationError("B4 public comparison row malformed")
        if row["candidate_arm"] in result:
            raise B4PublicationError("B4 public comparison duplicated")
        result[row["candidate_arm"]] = row
    return result


def _gate_failures(row: Mapping[str, Any]) -> list[str]:
    candidate = row["candidate_arm"]
    gate = b4p.B4_DEPLOYMENT_GATES[candidate]
    failures: list[str] = []
    task = row["task_success_effect"]
    harmful = row["harmful_evidence_risk_difference"]
    directions = row["panel_directions"]
    resources = row["resource_ratios"]
    if task["estimate_ppm"] < gate["minimum_task_success_effect_ppm"]:
        failures.append("task_success_effect_below_material_minimum")
    if task["simultaneous_97_5ci_ppm"][0] <= 0:
        failures.append("task_success_simultaneous_lower_not_positive")
    if directions["positive"] < gate["minimum_positive_panels"]:
        failures.append("positive_panel_count_below_minimum")
    if harmful[
        "conservative_extra_harm_upper_simultaneous_97_5ci_ppm"
    ] > gate["harmful_evidence_risk_difference_upper_simultaneous_97_5ci_ppm"]:
        failures.append("harmful_evidence_noninferiority_failed")
    if resources["warm_query_ratio"]["upper_95ci_ppm"] > gate[
        "warm_query_ratio_upper_95ci_ppm"
    ]:
        failures.append("warm_query_ratio_upper_ci_above_limit")
    if resources["peak_rss_ratio"]["upper_95ci_ppm"] > gate[
        "peak_rss_ratio_upper_95ci_ppm"
    ]:
        failures.append("peak_rss_ratio_upper_ci_above_limit")
    return sorted(failures)


def build_public_result(analysis: Mapping[str, Any]) -> dict[str, Any]:
    errors = b4s.validate_analysis(analysis)
    if errors:
        raise B4PublicationError("cannot publish invalid B4 analysis")
    report: dict[str, Any] = {
        "schema_version": B4_RESULT_SCHEMA,
        "status": B4_RESULT_STATUS,
        "claim_level": B4_RESULT_CLAIM,
        "protocol_digest": B4_PARENT_PROTOCOL_DIGEST,
        "inference_target": "mean_effect_over_the_twelve_frozen_panels",
        "matrix": copy.deepcopy(analysis["matrix"]),
        "arms": copy.deepcopy(analysis["arms"]),
        "comparisons": copy.deepcopy(analysis["comparisons"]),
        "quality_competition_ranks": copy.deepcopy(
            analysis["quality_competition_ranks"]
        ),
        "resource_competition_ranks": copy.deepcopy(
            analysis["resource_competition_ranks"]
        ),
        "pareto_frontier": copy.deepcopy(analysis["pareto_frontier"]),
        "phase_c_shortlist": copy.deepcopy(analysis["phase_c_shortlist"]),
        "decision_status": analysis["decision_status"],
        "ranking_published_even_when_gates_fail": True,
        "promotion_requires_fresh_phase_c_validation": True,
        "publication_limits": copy.deepcopy(B4_PUBLICATION_LIMITS),
        "result_digest": "",
    }
    report["result_digest"] = _digest("b4result_", report, "result_digest")
    validation = validate_public_result(report)
    if validation:
        raise B4PublicationError(
            "refusing to publish invalid B4 result: " + "; ".join(validation[:8])
        )
    return report


def validate_public_result(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B4 public result must be an object"]
    errors = list(b2.scan_public_report(report))
    if set(report) != B4_RESULT_KEYS:
        errors.append("B4 public result top-level key set drifted")
    if report.get("schema_version") != B4_RESULT_SCHEMA:
        errors.append("B4 public result schema drifted")
    if report.get("status") != B4_RESULT_STATUS:
        errors.append("B4 public result status drifted")
    if report.get("claim_level") != B4_RESULT_CLAIM:
        errors.append("B4 public result claim drifted")
    if report.get("protocol_digest") != B4_PARENT_PROTOCOL_DIGEST:
        errors.append("B4 public result protocol lock drifted")
    if report.get("result_digest") != _digest("b4result_", report, "result_digest"):
        errors.append("B4 public result digest mismatch")
    matrix = report.get("matrix")
    expected_matrix = {
        "panel_count": b4p.B4_PANEL_COUNT,
        "repository_cluster_count": b4p.B4_REPOSITORY_CLUSTER_COUNT,
        "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
        "task_outcome_count": b4r.B4_TASK_OUTCOME_COUNT,
        "logical_group_count": b4p.B4_LOGICAL_GROUP_COUNT,
        "logical_record_count": b4p.B4_LOGICAL_RECORD_COUNT,
        "index_build_count": b4p.B4_INDEX_BUILD_COUNT,
        "provider_network_call_count": 0,
        "all_pre_score_gates_passed": True,
    }
    if matrix != expected_matrix:
        errors.append("B4 public result matrix drifted")
    try:
        arms = _arm_map(report)
    except B4PublicationError as exc:
        errors.append(str(exc))
        arms = {}
    if set(arms) != set(b4p.B4_ARMS):
        errors.append("B4 public arm set drifted")
    if arms:
        try:
            expected_quality = b4s._competition_ranks(
                arms,
                lambda row: (
                    -row["task_success_rate_ppm"],
                    row["harmful_evidence_rate_ppm"],
                    -row["status_or_target_success_rate_ppm"],
                    -row["context_f05_mean_ppm"],
                ),
            )
            expected_resource = b4s._competition_ranks(
                arms,
                lambda row: (
                    row["warm_query_geometric_mean_us"],
                    row["peak_rss_p95_bytes"],
                ),
            )
            expected_pareto = b4s._pareto_frontier(arms)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"B4 public arm aggregates malformed: {type(exc).__name__}")
        else:
            if report.get("quality_competition_ranks") != expected_quality:
                errors.append("B4 public quality ranks drifted")
            if report.get("resource_competition_ranks") != expected_resource:
                errors.append("B4 public resource ranks drifted")
            if report.get("pareto_frontier") != expected_pareto:
                errors.append("B4 public Pareto frontier drifted")
    try:
        comparisons = _comparison_map(report)
    except B4PublicationError as exc:
        errors.append(str(exc))
        comparisons = {}
    if set(comparisons) != set(b4p.B4_CANDIDATE_ARMS):
        errors.append("B4 public comparison set drifted")
    else:
        for candidate, row in comparisons.items():
            try:
                expected_failures = _gate_failures(row)
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(
                    f"B4 public comparison malformed: {candidate}/{type(exc).__name__}"
                )
                continue
            if row.get("deployment_failure_reasons") != expected_failures:
                errors.append(f"B4 public gate failures drifted: {candidate}")
            if row.get("deployment_eligible") is not (not expected_failures):
                errors.append(f"B4 public gate eligibility drifted: {candidate}")
        shortlist = sorted(
            candidate
            for candidate, row in comparisons.items()
            if row.get("deployment_eligible") is True
        )
        if report.get("phase_c_shortlist") != shortlist:
            errors.append("B4 public Phase C shortlist drifted")
        expected_status = (
            "phase_c_shortlist_available"
            if shortlist
            else "comparative_result_complete_no_deployment_eligible_candidate"
        )
        if report.get("decision_status") != expected_status:
            errors.append("B4 public decision status drifted")
    if report.get("ranking_published_even_when_gates_fail") is not True:
        errors.append("B4 public ranking permanence flag drifted")
    if report.get("promotion_requires_fresh_phase_c_validation") is not True:
        errors.append("B4 public Phase C boundary drifted")
    if report.get("publication_limits") != B4_PUBLICATION_LIMITS:
        errors.append("B4 public publication limits drifted")
    return sorted(set(errors))


def build_public_failure(
    *,
    failure_class: str,
    attempt_boundary_crossed: bool,
    completed_group_count: int,
    logical_record_count: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": B4_FAILURE_SCHEMA,
        "status": B4_FAILURE_STATUS,
        "claim_level": "aggregate_failed_closeout_no_comparative_result",
        "protocol_digest": B4_PARENT_PROTOCOL_DIGEST,
        "failure_class": failure_class,
        "attempt_boundary_crossed": attempt_boundary_crossed,
        "completed_group_count": completed_group_count,
        "logical_record_count": logical_record_count,
        "retry_resume_or_recompute_authorized": False,
        "quality_resource_rank_or_candidate_metric_public": False,
        "publication_limits": copy.deepcopy(B4_PUBLICATION_LIMITS),
        "failure_digest": "",
    }
    report["failure_digest"] = _digest("b4failure_", report, "failure_digest")
    errors = validate_public_failure(report)
    if errors:
        raise B4PublicationError(
            "refusing to publish invalid B4 failure: " + "; ".join(errors[:8])
        )
    return report


def validate_public_failure(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B4 public failure must be an object"]
    errors = list(b2.scan_public_report(report))
    if set(report) != B4_FAILURE_KEYS:
        errors.append("B4 public failure top-level key set drifted")
    if report.get("schema_version") != B4_FAILURE_SCHEMA:
        errors.append("B4 public failure schema drifted")
    if report.get("status") != B4_FAILURE_STATUS:
        errors.append("B4 public failure status drifted")
    if report.get("protocol_digest") != B4_PARENT_PROTOCOL_DIGEST:
        errors.append("B4 public failure protocol lock drifted")
    if report.get("failure_class") not in B4_FAILURE_CLASSES:
        errors.append("B4 public failure class invalid")
    if type(report.get("attempt_boundary_crossed")) is not bool:
        errors.append("B4 public failure boundary flag invalid")
    for key, maximum in (
        ("completed_group_count", b4p.B4_LOGICAL_GROUP_COUNT),
        ("logical_record_count", b4p.B4_LOGICAL_RECORD_COUNT),
    ):
        value = report.get(key)
        if type(value) is not int or not 0 <= value <= maximum:
            errors.append(f"B4 public failure {key} invalid")
    if report.get("attempt_boundary_crossed") is False and (
        report.get("completed_group_count") != 0
        or report.get("logical_record_count") != 0
    ):
        errors.append("B4 pre-boundary failure contains treatment counts")
    failure_class = report.get("failure_class")
    boundary = report.get("attempt_boundary_crossed")
    if failure_class == "preboundary_admission_failure" and boundary is not False:
        errors.append("B4 pre-boundary failure class crossed boundary")
    if isinstance(failure_class, str) and failure_class.startswith("postboundary_"):
        if boundary is not True:
            errors.append("B4 post-boundary failure class lacks boundary")
    if report.get("completed_group_count") != report.get("logical_record_count"):
        errors.append("B4 failure group/record progress diverged")
    if report.get("retry_resume_or_recompute_authorized") is not False:
        errors.append("B4 public failure retry boundary drifted")
    if report.get("quality_resource_rank_or_candidate_metric_public") is not False:
        errors.append("B4 public failure leaks result metrics")
    if report.get("publication_limits") != B4_PUBLICATION_LIMITS:
        errors.append("B4 public failure publication limits drifted")
    if report.get("failure_digest") != _digest(
        "b4failure_", report, "failure_digest"
    ):
        errors.append("B4 public failure digest mismatch")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    analysis = b4s.score_b4(b4r.synthetic_run_result())
    result = build_public_result(analysis)
    tie = build_public_result(b4s.score_b4(b4r.synthetic_run_result(tie=True)))
    failure = build_public_failure(
        failure_class="postboundary_worker_failure",
        attempt_boundary_crossed=True,
        completed_group_count=120,
        logical_record_count=120,
    )
    checks = [
        not validate_public_result(result),
        not validate_public_result(tie),
        not validate_public_failure(failure),
        set(result["quality_competition_ranks"]) == set(b4p.B4_ARMS),
        set(result["resource_competition_ranks"]) == set(b4p.B4_ARMS),
        len(result["comparisons"]) == 2,
        set(tie["quality_competition_ranks"].values()) == {1},
        tie["phase_c_shortlist"] == [],
        bool(tie["pareto_frontier"]),
        "analysis_digest" not in result,
        "repository_slug" not in json.dumps(result, sort_keys=True),
        failure["retry_resume_or_recompute_authorized"] is False,
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "success_arm_count": len(result["arms"]),
        "success_comparison_count": len(result["comparisons"]),
    }


def run_fault_test() -> dict[str, Any]:
    base = build_public_result(b4s.score_b4(b4r.synthetic_run_result()))
    checks: list[bool] = []

    def reject(mutator: Any) -> None:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append(bool(validate_public_result(value)))

    reject(lambda value: value.__setitem__("quality_competition_ranks", {}))
    reject(lambda value: value.__setitem__("comparisons", value["comparisons"][:-1]))
    reject(lambda value: value.__setitem__("phase_c_shortlist", []))
    reject(lambda value: value.__setitem__("result_digest", "b4result_" + "0" * 64))
    reject(lambda value: value.__setitem__("query", "private"))

    failure = build_public_failure(
        failure_class="preboundary_admission_failure",
        attempt_boundary_crossed=False,
        completed_group_count=0,
        logical_record_count=0,
    )
    bad_failure = copy.deepcopy(failure)
    bad_failure["completed_group_count"] = 1
    checks.append(bool(validate_public_failure(bad_failure)))
    bad_failure = copy.deepcopy(failure)
    bad_failure["retry_resume_or_recompute_authorized"] = True
    checks.append(bool(validate_public_failure(bad_failure)))
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B4 aggregate publication")
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
    "B4_RESULT_SCHEMA",
    "B4_RESULT_STATUS",
    "B4_FAILURE_SCHEMA",
    "B4_FAILURE_STATUS",
    "B4_PUBLICATION_LIMITS",
    "B4PublicationError",
    "build_public_result",
    "validate_public_result",
    "build_public_failure",
    "validate_public_failure",
    "run_self_test",
    "run_fault_test",
]
