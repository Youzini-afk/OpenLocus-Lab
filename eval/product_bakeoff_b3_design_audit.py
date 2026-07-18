#!/usr/bin/env python3
"""Public post-result audit of the B3 decision and replication design.

The audit does not reopen, rescore, rerank, or otherwise reinterpret the frozen
B3 attempt.  It uses only the already-published aggregate result and the frozen
public decision code to identify why the experiment did not answer the intended
product-selection question strongly enough for a default change.
"""

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
import product_bakeoff_b3_publication as b3pub  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
RESULT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_result"
    / "product_bakeoff_b3_result.json"
)
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_design_audit"
    / "product_bakeoff_b3_design_audit.json"
)

SCHEMA_VERSION = "product_bakeoff_b3_design_audit.v1"
STATUS = "product_bakeoff_b3_decision_and_replication_design_audited_result_frozen"
CLAIM_LEVEL = "public_posthoc_design_audit_no_b3_reclassification_no_promotion"
DATE = "2026-07-18"

EXPECTED_RESULT_FILE_SHA256 = (
    "a4cb5414b5486e166aae783ce508e55e24e92e181fa73ac232185254be5d8e25"
)
EXPECTED_RESULT_DIGEST = (
    "b3result_25ef345fa4b312ab9292ffe47fdb4ee26d0009d7ca3e46c867fcf245f8f82a00"
)

SOURCE_BUNDLE_PATHS = (
    "eval/product_bakeoff_b2_protocol.py",
    "eval/product_bakeoff_b3_publication.py",
    "eval/product_bakeoff_b3_design_audit.py",
    "artifacts/product_bakeoff_b3_result/product_bakeoff_b3_result.json",
)

COMMON_ABSOLUTE_FAILURES = (
    "ambiguous_status_success_below_floor",
    "answerable_target_success_below_floor",
    "language_stratum_below_floor",
    "one_shot_success_below_floor",
    "overall_task_success_below_floor",
    "role_stratum_below_floor",
    "size_stratum_below_floor",
)


class B3DesignAuditError(ValueError):
    """Fail-closed error for malformed or drifted public audit inputs."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _prefixed_digest(prefix: str, value: Mapping[str, Any], key: str) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_bundle_digest() -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_BUNDLE_PATHS:
        path = REPO / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return "b3auditbundle_" + digest.hexdigest()


def _load_result() -> dict[str, Any]:
    if _file_sha256(RESULT_PATH) != EXPECTED_RESULT_FILE_SHA256:
        raise B3DesignAuditError("B3 result file lock drifted")
    value = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    errors = b3pub.validate_public_result(value)
    if errors:
        raise B3DesignAuditError("B3 public result is invalid")
    if value.get("result_digest") != EXPECTED_RESULT_DIGEST:
        raise B3DesignAuditError("B3 result digest drifted")
    return value


def _minimum_mapping_value(arm: Mapping[str, Any], key: str) -> int:
    values = arm.get(key)
    if not isinstance(values, Mapping) or not values:
        raise B3DesignAuditError(f"B3 arm {key} is malformed")
    return min(int(value) for value in values.values())


def _candidate_floor_failures(arm: Mapping[str, Any]) -> list[str]:
    floors = b2.B2_QUALITY_FLOORS
    failures: list[str] = []
    if int(arm["task_success_count"]) < floors["task_success_count"]:
        failures.append("overall_task_success_below_floor")
    if int(arm["one_shot_success_count"]) < floors["one_shot_success_count"]:
        failures.append("one_shot_success_below_floor")
    if int(arm["answerable_target_success_count"]) < floors[
        "answerable_target_success_count"
    ]:
        failures.append("answerable_target_success_below_floor")
    if int(arm["ambiguous_status_success_count"]) < floors[
        "ambiguous_status_success_count"
    ]:
        failures.append("ambiguous_status_success_below_floor")
    if int(arm["no_answer_status_success_count"]) < floors[
        "no_answer_status_success_count"
    ]:
        failures.append("no_answer_status_success_below_floor")
    if _minimum_mapping_value(arm, "language_success_counts") < floors[
        "language_success_floor_each_of_16"
    ]:
        failures.append("language_stratum_below_floor")
    if _minimum_mapping_value(arm, "size_success_counts") < floors[
        "size_success_floor_each_of_12"
    ]:
        failures.append("size_stratum_below_floor")
    if _minimum_mapping_value(arm, "role_success_counts") < floors[
        "role_success_floor_each_of_12"
    ]:
        failures.append("role_stratum_below_floor")
    return sorted(failures)


def _ratio_ppm(child: int, parent: int) -> int:
    if parent <= 0:
        raise B3DesignAuditError("ratio parent must be positive")
    return (child * 1_000_000) // parent


def _planning_signal(
    candidate: Mapping[str, Any], baseline: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "task_success_delta": int(candidate["task_success_count"])
        - int(baseline["task_success_count"]),
        "one_shot_success_delta": int(candidate["one_shot_success_count"])
        - int(baseline["one_shot_success_count"]),
        "answerable_target_success_delta": int(
            candidate["answerable_target_success_count"]
        )
        - int(baseline["answerable_target_success_count"]),
        "context_f05_sum_delta_ppm": int(candidate["context_f05_sum_ppm"])
        - int(baseline["context_f05_sum_ppm"]),
        "warm_query_p95_ratio_ppm": _ratio_ppm(
            int(candidate["warm_query_p95_us"]),
            int(baseline["warm_query_p95_us"]),
        ),
        "peak_rss_p95_ratio_ppm": _ratio_ppm(
            int(candidate["peak_rss_p95_bytes"]),
            int(baseline["peak_rss_p95_bytes"]),
        ),
        "planning_only_not_confirmatory": True,
    }


def build_report() -> dict[str, Any]:
    result = _load_result()
    arms = {arm["adapter_id"]: arm for arm in result["arms"]}
    baseline = arms[b2.S0_ADAPTER_ID]
    candidate_ids = (*b2.B2_OPTIONAL_TRACK_ARMS, *b2.B2_DEFAULT_TRACK_ARMS)
    failure_map = result["tournament_decision"]["candidate_failure_reasons"]
    shared_failures = sorted(
        set.intersection(*(set(failure_map[adapter_id]) for adapter_id in candidate_ids))
    )

    absolute_floor_maxima = {
        "task_success_count": {
            "floor": b2.B2_QUALITY_FLOORS["task_success_count"],
            "observed_candidate_max": max(
                int(arms[adapter_id]["task_success_count"])
                for adapter_id in candidate_ids
            ),
            "baseline_observed": int(baseline["task_success_count"]),
        },
        "one_shot_success_count": {
            "floor": b2.B2_QUALITY_FLOORS["one_shot_success_count"],
            "observed_candidate_max": max(
                int(arms[adapter_id]["one_shot_success_count"])
                for adapter_id in candidate_ids
            ),
            "baseline_observed": int(baseline["one_shot_success_count"]),
        },
        "answerable_target_success_count": {
            "floor": b2.B2_QUALITY_FLOORS["answerable_target_success_count"],
            "observed_candidate_max": max(
                int(arms[adapter_id]["answerable_target_success_count"])
                for adapter_id in candidate_ids
            ),
            "baseline_observed": int(baseline["answerable_target_success_count"]),
        },
        "ambiguous_status_success_count": {
            "floor": b2.B2_QUALITY_FLOORS["ambiguous_status_success_count"],
            "observed_candidate_max": max(
                int(arms[adapter_id]["ambiguous_status_success_count"])
                for adapter_id in candidate_ids
            ),
            "baseline_observed": int(baseline["ambiguous_status_success_count"]),
        },
        "minimum_language_stratum": {
            "floor": b2.B2_QUALITY_FLOORS["language_success_floor_each_of_16"],
            "observed_candidate_max": max(
                _minimum_mapping_value(arms[adapter_id], "language_success_counts")
                for adapter_id in candidate_ids
            ),
            "baseline_observed": _minimum_mapping_value(
                baseline, "language_success_counts"
            ),
        },
        "minimum_size_stratum": {
            "floor": b2.B2_QUALITY_FLOORS["size_success_floor_each_of_12"],
            "observed_candidate_max": max(
                _minimum_mapping_value(arms[adapter_id], "size_success_counts")
                for adapter_id in candidate_ids
            ),
            "baseline_observed": _minimum_mapping_value(
                baseline, "size_success_counts"
            ),
        },
        "minimum_role_stratum": {
            "floor": b2.B2_QUALITY_FLOORS["role_success_floor_each_of_12"],
            "observed_candidate_max": max(
                _minimum_mapping_value(arms[adapter_id], "role_success_counts")
                for adapter_id in candidate_ids
            ),
            "baseline_observed": _minimum_mapping_value(
                baseline, "role_success_counts"
            ),
        },
    }

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase": "product_bakeoff_b3_post_result_design_validity_audit",
        "status": STATUS,
        "claim_level": CLAIM_LEVEL,
        "date": DATE,
        "aggregate_only": True,
        "parent_result": {
            "schema_version": result["schema_version"],
            "status": result["status"],
            "result_digest": result["result_digest"],
            "file_sha256": EXPECTED_RESULT_FILE_SHA256,
            "result_remains_frozen_and_authoritative": True,
        },
        "execution_validity": {
            "logical_task_count": result["matrix"]["logical_task_count"],
            "logical_group_count": result["matrix"]["logical_group_count"],
            "logical_record_count": result["matrix"]["logical_record_count"],
            "all_pre_score_gates_passed": result["matrix"][
                "all_pre_score_gates_passed"
            ],
            "provider_network_call_count": result["matrix"][
                "provider_network_call_count"
            ],
            "formal_execution_integrity_valid": True,
        },
        "decision_rule_audit": {
            "b2_absolute_quality_floors_reused_without_b3_panel_calibration": True,
            "candidate_eligibility_filter_applied_before_competition_ranking": True,
            "baseline_control_not_subject_to_candidate_absolute_quality_floors": True,
            "baseline_counterfactual_candidate_floor_failures": _candidate_floor_failures(
                baseline
            ),
            "shared_candidate_failure_reasons": shared_failures,
            "all_candidates_shared_the_seven_core_absolute_failures": shared_failures
            == list(COMMON_ABSOLUTE_FAILURES),
            "absolute_floor_maxima": absolute_floor_maxima,
            "quality_ranks_empty_because_no_candidate_reached_ranking": not bool(
                result["tournament_decision"]["quality_ranks"]
            ),
            "resource_ranks_empty_because_no_candidate_reached_ranking": not bool(
                result["tournament_decision"]["resource_ranks"]
            ),
            "tie_policy_implemented_but_not_reached": True,
            "decision_rule_answered_deployment_eligibility_but_not_relative_order": True,
            "product_selection_question_not_sufficiently_answered": True,
        },
        "replication_audit": {
            "formal_tournament_count": 1,
            "independent_holdout_panel_count": 1,
            "repository_cluster_count": result["experimental_design"][
                "repository_cluster_count"
            ],
            "logical_task_count": result["experimental_design"][
                "logical_task_count"
            ],
            "technical_repetition_count": result["experimental_design"][
                "technical_repetition_count"
            ],
            "technical_repetitions_are_not_independent_quality_samples": True,
            "logical_record_count_is_not_quality_sample_size": True,
            "quality_sample_size_is_48_tasks_nested_in_12_repository_clusters": True,
            "between_panel_variance_not_estimated": True,
            "population_generalization_not_supported": True,
        },
        "descriptive_planning_signals": {
            b2.S1_ADAPTER_ID: _planning_signal(arms[b2.S1_ADAPTER_ID], baseline),
            b2.S4_ADAPTER_ID: _planning_signal(arms[b2.S4_ADAPTER_ID], baseline),
            "b3_public_aggregates_may_inform_b4_planning_only": True,
            "b3_may_not_be_counted_as_b4_confirmatory_replication": True,
        },
        "corrective_route": {
            "next_protocol_label": "product_bakeoff_b4",
            "candidate_arms": [b2.S0_ADAPTER_ID, b2.S1_ADAPTER_ID, b2.S4_ADAPTER_ID],
            "independent_fresh_panels_required": True,
            "baseline_ranked_symmetrically_with_candidates": True,
            "relative_effect_estimates_and_uncertainty_always_published": True,
            "ranking_precedes_deployment_gates": True,
            "pareto_frontier_always_published": True,
            "exact_ties_share_competition_rank": True,
            "new_execution_authorized": False,
        },
        "closure": {
            "b3_rescored_reranked_or_recomputed": False,
            "b3_result_status_changed": False,
            "b3_product_default_changed": False,
            "private_b3_task_or_repository_identity_read_or_published": False,
            "private_b3_task_level_scores_reconstructed": False,
        },
        "source_bundle_digest": source_bundle_digest(),
        "audit_digest": "",
    }
    report["audit_digest"] = _prefixed_digest("b3audit_", report, "audit_digest")
    return report


def _diff(expected: Any, actual: Any, path: str = "report") -> list[str]:
    if type(expected) is not type(actual):
        return [f"{path}: type drift"]
    if isinstance(expected, dict):
        errors: list[str] = []
        if set(expected) != set(actual):
            errors.append(f"{path}: key drift")
        for key in sorted(set(expected) & set(actual)):
            errors.extend(_diff(expected[key], actual[key], f"{path}.{key}"))
        return errors
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"{path}: list length drift"]
        errors: list[str] = []
        for index, (left, right) in enumerate(zip(expected, actual)):
            errors.extend(_diff(left, right, f"{path}[{index}]"))
        return errors
    return [] if expected == actual else [f"{path}: value drift"]


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 design audit must be an object"]
    errors = list(b2.scan_public_report(report))
    try:
        expected = build_report()
    except (B3DesignAuditError, OSError, ValueError) as exc:
        errors.append(f"cannot rebuild B3 design audit: {type(exc).__name__}")
        return sorted(set(errors))
    errors.extend(_diff(expected, report))
    if report.get("audit_digest") != _prefixed_digest(
        "b3audit_", report, "audit_digest"
    ):
        errors.append("B3 design audit digest mismatch")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    maxima = report["decision_rule_audit"]["absolute_floor_maxima"]
    checks = [
        not validate_report(report),
        maxima["task_success_count"] == {
            "floor": 34,
            "observed_candidate_max": 29,
            "baseline_observed": 23,
        },
        maxima["one_shot_success_count"]["observed_candidate_max"] == 26,
        maxima["answerable_target_success_count"]["observed_candidate_max"] == 27,
        maxima["ambiguous_status_success_count"]["observed_candidate_max"] == 1,
        report["decision_rule_audit"][
            "all_candidates_shared_the_seven_core_absolute_failures"
        ],
        report["decision_rule_audit"]["tie_policy_implemented_but_not_reached"],
        report["replication_audit"]["independent_holdout_panel_count"] == 1,
        report["replication_audit"][
            "technical_repetitions_are_not_independent_quality_samples"
        ],
        report["closure"]["b3_rescored_reranked_or_recomputed"] is False,
        report["corrective_route"]["new_execution_authorized"] is False,
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[bool] = []

    def reject(mutator: Any) -> None:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append(bool(validate_report(value)))

    reject(
        lambda value: value["closure"].__setitem__(
            "b3_rescored_reranked_or_recomputed", True
        )
    )
    reject(
        lambda value: value["replication_audit"].__setitem__(
            "independent_holdout_panel_count", 4
        )
    )
    reject(
        lambda value: value["decision_rule_audit"].__setitem__(
            "candidate_eligibility_filter_applied_before_competition_ranking", False
        )
    )
    reject(
        lambda value: value["corrective_route"].__setitem__(
            "new_execution_authorized", True
        )
    )
    reject(lambda value: value.__setitem__("audit_digest", "b3audit_" + "0" * 64))
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise B3DesignAuditError("refusing to write invalid B3 design audit")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B3 public design-validity audit")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--write-report", action="store_true")
    mode.add_argument("--validate-report", type=Path)
    mode.add_argument("--check-drift", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, sort_keys=True))
        return 0 if report["passed"] else 1
    if args.fault_test:
        report = run_fault_test()
        print(json.dumps(report, sort_keys=True))
        return 0 if report["passed"] else 1
    if args.write_report:
        print(write_report(args.output))
        return 0
    path = args.validate_report or args.check_drift
    report = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_report(report)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(("Drift check" if args.check_drift else "Validation") + f" passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SCHEMA_VERSION",
    "STATUS",
    "build_report",
    "validate_report",
    "run_self_test",
    "run_fault_test",
]
