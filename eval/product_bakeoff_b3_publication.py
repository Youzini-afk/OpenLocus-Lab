#!/usr/bin/env python3
"""Aggregate-only success and fail-closed publication boundaries for B3."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_protocol as b2p
import product_bakeoff_b2_scorer as b2s
import product_bakeoff_b3_protocol as b3p
import product_bakeoff_b3_readiness as b3ready
import product_bakeoff_b3_repeatability as b3repeat
import product_bakeoff_b3_source as b3src


REPO = Path(__file__).resolve().parents[1]
B3_RESULT_SCHEMA = "product_bakeoff_b3_tournament_result.v1"
B3_RESULT_STATUS = "product_bakeoff_b3_tournament_complete_aggregate_only"
B3_FAILURE_SCHEMA = "product_bakeoff_b3_failed_closed_aggregate.v1"
B3_FAILURE_STATUS = "product_bakeoff_b3_execution_failed_closed_no_result"
B3_RESULT_CLAIM = "fixed_frozen_frame_internal_product_decision_evidence"
B3_FAILURE_CLASSES = frozenset(
    {
        "worker_or_machine_terminated",
        "matrix_execution_failed",
        "pre_score_gate_failed",
        "scoring_or_publication_failed",
        "incomplete_matrix_after_worker_exit",
    }
)
B3_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "repository_task_query_oracle_identity_public": False,
    "source_location_range_excerpt_or_raw_output_public": False,
    "per_task_per_repository_or_per_cell_detail_public": False,
    "intermediate_arm_quality_resource_or_ranking_metric_public": False,
    "private_freeze_runtime_or_launch_digest_public": False,
    "exact_runner_profile_or_location_public": False,
}


class B3PublicationError(ValueError):
    """Fail-closed B3 public artifact error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _result_digest(prefix: str, report: Mapping[str, Any], key: str) -> str:
    payload = copy.deepcopy(dict(report))
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _protocol_block() -> dict[str, Any]:
    return {
        "b3_spec_digest": b3p.spec_digest(),
        "b3_execution_schedule_digest": b3p.execution_schedule_digest(),
        "b3_expected_observation_plan_digest": b3p.expected_observation_plan_digest(),
        "b3_repeatability_policy_digest": b3repeat.repeatability_policy_digest(),
        "b3_control_source_bundle_digest": b3src.control_source_bundle_digest(),
        "attempt_boundary": "first_durable_treatment_observation",
        "launch_release_alone_consumes_attempt": False,
        "maximum_attempts_with_durable_observation": 1,
    }


def _string_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, Mapping):
        for child in value.values():
            values.extend(_string_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(_string_values(child))
    elif isinstance(value, str):
        values.append(value)
    return values


def _scan_public(
    report: Any,
    *,
    private_exact_tokens: Sequence[str] = (),
    private_substring_tokens: Sequence[str] = (),
) -> list[str]:
    errors = list(b2s.scan_result_report(report))
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "b3_private_",
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "runtime_private_receipt_digest",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "query_gate_digest",
        "launch_authorization_digest",
        "clone_root",
    ):
        if token in raw:
            errors.append(f"private B3 token forbidden in public artifact: {token}")
    string_values = [value.casefold() for value in _string_values(report)]
    exact = {token.casefold() for token in private_exact_tokens if token}
    substrings = {
        token.casefold() for token in private_substring_tokens if len(token) >= 4
    }
    if any(value in exact for value in string_values):
        errors.append("private B3 exact value leaked into public artifact")
    if any(token in value for value in string_values for token in substrings):
        errors.append("private B3 identity value leaked into public artifact")
    return sorted(set(errors))


def _private_result_tokens(result: Any) -> tuple[list[str], list[str]]:
    exact: list[str] = []
    substrings: list[str] = []
    if result.repo_lock:
        for repo in result.repo_lock["repos"]:
            substrings.extend(
                (
                    repo["source"]["repo"],
                    repo["source"]["clone_root"],
                    repo["commit"],
                )
            )
    for task in result.tasks:
        exact.append(task.query)
        substrings.append(task.task_slug)
    return exact, substrings


def _arm_public(row: Any) -> dict[str, Any]:
    errors = b2p.validate_arm_summary(row.summary)
    if errors:
        raise B3PublicationError("invalid B3 arm summary")
    value = b2s._summary_dict(row.summary)
    value["terminal_support_count"] = int(row.terminal_support_count)
    value["executed_adapter_record_count"] = int(row.executed_adapter_record_count)
    return value


def build_public_result(
    *,
    result: Any,
    arm_results: Sequence[Any],
    decision: Mapping[str, Any],
    readiness_report: Mapping[str, Any],
    readiness_report_path: Path,
    launch_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    readiness_errors = b3ready.validate_public_readiness(dict(readiness_report))
    if readiness_errors:
        raise B3PublicationError("B3 readiness report is invalid")
    readiness_sha = hashlib.sha256(Path(readiness_report_path).read_bytes()).hexdigest()
    if readiness_report["readiness_digest"] != launch_authorization.get(
        "readiness_report_digest"
    ) or readiness_sha != launch_authorization.get("readiness_report_file_sha256"):
        raise B3PublicationError("B3 readiness differs from launch authorization")
    if len(arm_results) != 6:
        raise B3PublicationError("B3 public result requires six arm aggregates")
    expected_decision = b2p.evaluate_tournament([row.summary for row in arm_results])
    if dict(decision) != expected_decision:
        raise B3PublicationError("B3 tournament decision drifted from arm aggregates")
    report: dict[str, Any] = {
        "schema_version": B3_RESULT_SCHEMA,
        "phase": "product_bakeoff_b3_fresh_cluster_aware_williams_tournament",
        "status": B3_RESULT_STATUS,
        "claim_level": B3_RESULT_CLAIM,
        "date": "2026-07-17",
        "aggregate_only": True,
        "product_default_changed": False,
        "public_unique_winner_required": False,
        "phase_c_validation_required": True,
        "protocol": _protocol_block(),
        "historical_closeout": {
            "b25_remains_failed_closed_no_result": True,
            "b25_private_holdout_output_or_authorization_reused": False,
        },
        "readiness_gate": {
            "readiness_digest": readiness_report["readiness_digest"],
            "readiness_file_sha256": readiness_sha,
            "readiness_checkpoint": launch_authorization["readiness_checkpoint"],
            "readiness_ci_run_id": launch_authorization["readiness_ci_run_id"],
            "readiness_ci_conclusion": launch_authorization[
                "readiness_ci_conclusion"
            ],
        },
        "attempt_boundary_gate": {
            "launch_release_issued": True,
            "first_durable_observation_recorded": True,
            "durable_observation_attempt_count": 1,
            "restart_resume_retry_or_recomputation_used": False,
        },
        "experimental_design": {
            "repository_cluster_count": 12,
            "logical_task_count": 48,
            "quality_analysis_unit": "logical_task",
            "technical_repetition_count": 4,
            "technical_repetitions_increase_quality_sample_size": False,
            "paired_task_level_quality_comparison": True,
            "repository_cluster_sensitivity_descriptive_only": True,
            "exact_ties_share_competition_rank": True,
            "forced_unique_winner": False,
        },
        "matrix": {
            "logical_task_count": 48,
            "logical_group_count": 360,
            "logical_record_count": int(result.logical_record_count),
            "expected_logical_record_count": 1440,
            "executed_adapter_record_count": len(result.records),
            "terminal_support_record_count": len(result.terminal_support_cells),
            "all_pre_score_gates_passed": bool(
                result.gate_result and result.gate_result.passed
            ),
            "provider_network_call_count": int(result.provider_network_call_count),
        },
        "resource_percentile_rule": (
            "nearest_rank_ceiling_p95;_terminal_support_excluded_from_query_latency_and_peak_rss"
        ),
        "arms": [
            _arm_public(row)
            for row in sorted(arm_results, key=lambda item: item.summary.adapter_id)
        ],
        "tournament_decision": dict(decision),
        "publication_limits": copy.deepcopy(B3_PUBLICATION_LIMITS),
        "result_digest": "",
    }
    report["result_digest"] = _result_digest("b3result_", report, "result_digest")
    private_exact, private_substrings = _private_result_tokens(result)
    errors = _scan_public(
        report,
        private_exact_tokens=private_exact,
        private_substring_tokens=private_substrings,
    )
    if errors:
        raise B3PublicationError("B3 public result privacy scan failed: " + "; ".join(errors))
    validation = validate_public_result(report)
    if validation:
        raise B3PublicationError("generated B3 public result is invalid")
    return report


def _summary_from_public(value: Mapping[str, Any]) -> b2p.B2ArmSummary:
    mapping_fields = {
        "language_success_counts",
        "size_success_counts",
        "role_success_counts",
        "subset_success_counts",
        "subset_context_f05_sum_ppm",
    }
    kwargs: dict[str, Any] = {}
    for field in b2p.B2ArmSummary.__dataclass_fields__:
        observed = value.get(field)
        kwargs[field] = (
            tuple(sorted(observed.items())) if field in mapping_fields and isinstance(observed, dict) else observed
        )
    return b2p.B2ArmSummary(**kwargs)


def validate_public_result(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 public result must be an object"]
    errors = _scan_public(report)
    expected_keys = {
        "schema_version",
        "phase",
        "status",
        "claim_level",
        "date",
        "aggregate_only",
        "product_default_changed",
        "public_unique_winner_required",
        "phase_c_validation_required",
        "protocol",
        "historical_closeout",
        "readiness_gate",
        "attempt_boundary_gate",
        "experimental_design",
        "matrix",
        "resource_percentile_rule",
        "arms",
        "tournament_decision",
        "publication_limits",
        "result_digest",
    }
    if set(report) != expected_keys:
        errors.append("B3 public result shape drifted")
    if report.get("schema_version") != B3_RESULT_SCHEMA:
        errors.append("B3 public result schema drifted")
    if report.get("status") != B3_RESULT_STATUS:
        errors.append("B3 public result status drifted")
    if report.get("claim_level") != B3_RESULT_CLAIM:
        errors.append("B3 public result claim drifted")
    for key, expected in (
        ("aggregate_only", True),
        ("product_default_changed", False),
        ("public_unique_winner_required", False),
        ("phase_c_validation_required", True),
    ):
        if report.get(key) is not expected:
            errors.append(f"B3 public result {key} drifted")
    if report.get("protocol") != _protocol_block():
        errors.append("B3 public result protocol drifted")
    if report.get("historical_closeout") != {
        "b25_remains_failed_closed_no_result": True,
        "b25_private_holdout_output_or_authorization_reused": False,
    }:
        errors.append("B3 public result historical closeout drifted")
    readiness = report.get("readiness_gate") or {}
    if set(readiness) != {
        "readiness_digest",
        "readiness_file_sha256",
        "readiness_checkpoint",
        "readiness_ci_run_id",
        "readiness_ci_conclusion",
    }:
        errors.append("B3 public result readiness gate shape drifted")
    if not str(readiness.get("readiness_digest", "")).startswith("b3ready_"):
        errors.append("B3 public result readiness digest malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", str(readiness.get("readiness_file_sha256", ""))):
        errors.append("B3 public result readiness file digest malformed")
    if not re.fullmatch(r"[0-9a-f]{40}", str(readiness.get("readiness_checkpoint", ""))):
        errors.append("B3 public result readiness checkpoint malformed")
    if not isinstance(readiness.get("readiness_ci_run_id"), int) or readiness.get(
        "readiness_ci_run_id", 0
    ) <= 0:
        errors.append("B3 public result readiness CI id malformed")
    if readiness.get("readiness_ci_conclusion") != "success":
        errors.append("B3 public result readiness CI failed")
    if report.get("attempt_boundary_gate") != {
        "launch_release_issued": True,
        "first_durable_observation_recorded": True,
        "durable_observation_attempt_count": 1,
        "restart_resume_retry_or_recomputation_used": False,
    }:
        errors.append("B3 public result attempt boundary drifted")
    if report.get("experimental_design") != {
        "repository_cluster_count": 12,
        "logical_task_count": 48,
        "quality_analysis_unit": "logical_task",
        "technical_repetition_count": 4,
        "technical_repetitions_increase_quality_sample_size": False,
        "paired_task_level_quality_comparison": True,
        "repository_cluster_sensitivity_descriptive_only": True,
        "exact_ties_share_competition_rank": True,
        "forced_unique_winner": False,
    }:
        errors.append("B3 public result experimental design drifted")
    matrix = report.get("matrix") or {}
    if matrix.get("logical_task_count") != 48 or matrix.get("logical_group_count") != 360:
        errors.append("B3 public result matrix task/group counts drifted")
    if matrix.get("logical_record_count") != 1440 or matrix.get(
        "expected_logical_record_count"
    ) != 1440:
        errors.append("B3 public result matrix incomplete")
    if not isinstance(matrix.get("executed_adapter_record_count"), int) or not isinstance(
        matrix.get("terminal_support_record_count"), int
    ) or matrix.get("executed_adapter_record_count", -1) + matrix.get(
        "terminal_support_record_count", -1
    ) != 1440:
        errors.append("B3 public result executed/terminal counts drifted")
    if matrix.get("all_pre_score_gates_passed") is not True:
        errors.append("B3 public result pre-score gates failed")
    if matrix.get("provider_network_call_count") != 0:
        errors.append("B3 public result provider network count nonzero")
    arms = report.get("arms")
    summaries: list[b2p.B2ArmSummary] = []
    if not isinstance(arms, list) or len(arms) != 6:
        errors.append("B3 public result must contain six arms")
    else:
        for arm in arms:
            if not isinstance(arm, dict) or set(arm) != {
                *b2p.B2ArmSummary.__dataclass_fields__,
                "terminal_support_count",
                "executed_adapter_record_count",
            }:
                errors.append("B3 public arm shape drifted")
                continue
            try:
                summary = _summary_from_public(arm)
            except (TypeError, ValueError):
                errors.append("B3 public arm could not be reconstructed")
                continue
            errors.extend(f"B3 public arm: {error}" for error in b2p.validate_arm_summary(summary))
            if arm["executed_adapter_record_count"] + arm["terminal_support_count"] != 240:
                errors.append("B3 public arm logical record count drifted")
            summaries.append(summary)
    if len(summaries) == 6:
        try:
            expected_decision = b2p.evaluate_tournament(summaries)
        except Exception as exc:  # noqa: BLE001 - public type only
            errors.append(f"B3 public decision reconstruction failed: {type(exc).__name__}")
        else:
            if report.get("tournament_decision") != expected_decision:
                errors.append("B3 public tournament decision drifted")
    if report.get("publication_limits") != B3_PUBLICATION_LIMITS:
        errors.append("B3 public result publication limits drifted")
    if report.get("result_digest") != _result_digest(
        "b3result_", report, "result_digest"
    ):
        errors.append("B3 public result digest mismatch")
    return sorted(set(errors))


def build_public_failure(
    *,
    failure_class: str,
    completed_group_count: int,
    logical_record_count: int,
    durable_treatment_artifact_count: int,
) -> dict[str, Any]:
    if failure_class not in B3_FAILURE_CLASSES:
        raise B3PublicationError("B3 public failure class is not closed")
    if not isinstance(completed_group_count, int) or not 0 <= completed_group_count <= 48:
        raise B3PublicationError("B3 completed group count malformed")
    if not isinstance(logical_record_count, int) or not 0 <= logical_record_count <= 1440:
        raise B3PublicationError("B3 failure logical record count malformed")
    if (
        not isinstance(durable_treatment_artifact_count, int)
        or durable_treatment_artifact_count < 1
        or logical_record_count > durable_treatment_artifact_count
    ):
        raise B3PublicationError("B3 failure durable artifact count malformed")
    report: dict[str, Any] = {
        "schema_version": B3_FAILURE_SCHEMA,
        "phase": "product_bakeoff_b3_fresh_cluster_aware_williams_tournament",
        "status": B3_FAILURE_STATUS,
        "claim_level": "aggregate_failure_closeout_only_no_tournament_result",
        "date": "2026-07-17",
        "protocol": _protocol_block(),
        "attempt_boundary_gate": {
            "first_durable_observation_recorded": True,
            "durable_observation_attempt_count": 1,
            "restart_resume_retry_or_recomputation_allowed": False,
        },
        "execution_aggregate": {
            "completed_group_count": completed_group_count,
            "logical_record_count": logical_record_count,
            "durable_treatment_artifact_count": durable_treatment_artifact_count,
            "expected_group_count": 48,
            "expected_logical_record_count": 1440,
            "failure_class": failure_class,
            "arm_quality_resource_or_rank_metrics_included": False,
        },
        "decision": {
            "failed_closed": True,
            "tournament_result_exists": False,
            "arm_scoring_or_ranking_publishable": False,
            "retry_authorized": False,
            "product_default_changed": False,
        },
        "publication_limits": copy.deepcopy(B3_PUBLICATION_LIMITS),
        "failure_aggregate_digest": "",
    }
    report["failure_aggregate_digest"] = _result_digest(
        "b3failure_", report, "failure_aggregate_digest"
    )
    errors = validate_public_failure(report)
    if errors:
        raise B3PublicationError("generated B3 failure closeout is invalid")
    return report


def validate_public_failure(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 public failure must be an object"]
    errors = _scan_public(report)
    if set(report) != {
        "schema_version",
        "phase",
        "status",
        "claim_level",
        "date",
        "protocol",
        "attempt_boundary_gate",
        "execution_aggregate",
        "decision",
        "publication_limits",
        "failure_aggregate_digest",
    }:
        errors.append("B3 public failure shape drifted")
    if report.get("schema_version") != B3_FAILURE_SCHEMA:
        errors.append("B3 public failure schema drifted")
    if report.get("status") != B3_FAILURE_STATUS:
        errors.append("B3 public failure status drifted")
    if report.get("protocol") != _protocol_block():
        errors.append("B3 public failure protocol drifted")
    if report.get("attempt_boundary_gate") != {
        "first_durable_observation_recorded": True,
        "durable_observation_attempt_count": 1,
        "restart_resume_retry_or_recomputation_allowed": False,
    }:
        errors.append("B3 public failure attempt boundary drifted")
    aggregate = report.get("execution_aggregate") or {}
    if set(aggregate) != {
        "completed_group_count",
        "logical_record_count",
        "durable_treatment_artifact_count",
        "expected_group_count",
        "expected_logical_record_count",
        "failure_class",
        "arm_quality_resource_or_rank_metrics_included",
    }:
        errors.append("B3 public failure execution aggregate shape drifted")
    groups = aggregate.get("completed_group_count")
    records = aggregate.get("logical_record_count")
    if not isinstance(groups, int) or not 0 <= groups <= 48:
        errors.append("B3 public failure completed groups malformed")
    durable = aggregate.get("durable_treatment_artifact_count")
    if not isinstance(records, int) or not 0 <= records <= 1440:
        errors.append("B3 public failure logical records malformed")
    if (
        not isinstance(durable, int)
        or durable < 1
        or (isinstance(records, int) and records > durable)
    ):
        errors.append("B3 public failure durable artifact count malformed")
    if aggregate.get("expected_group_count") != 48 or aggregate.get(
        "expected_logical_record_count"
    ) != 1440:
        errors.append("B3 public failure expected counts drifted")
    if aggregate.get("failure_class") not in B3_FAILURE_CLASSES:
        errors.append("B3 public failure class drifted")
    if aggregate.get("arm_quality_resource_or_rank_metrics_included") is not False:
        errors.append("B3 public failure contains intermediate metrics")
    if report.get("decision") != {
        "failed_closed": True,
        "tournament_result_exists": False,
        "arm_scoring_or_ranking_publishable": False,
        "retry_authorized": False,
        "product_default_changed": False,
    }:
        errors.append("B3 public failure decision drifted")
    if report.get("publication_limits") != B3_PUBLICATION_LIMITS:
        errors.append("B3 public failure publication limits drifted")
    if report.get("failure_aggregate_digest") != _result_digest(
        "b3failure_", report, "failure_aggregate_digest"
    ):
        errors.append("B3 public failure digest mismatch")
    raw = json.dumps(report, sort_keys=True).casefold()
    for token in ("arms", "tournament_decision", "quality_rank", "resource_rank"):
        if token in raw:
            errors.append(f"B3 public failure contains forbidden metric token: {token}")
    return sorted(set(errors))


def write_public(path: Path, report: Mapping[str, Any]) -> Path:
    value = dict(report)
    if validate_public_result(value) and validate_public_failure(value):
        raise B3PublicationError("refusing to write invalid B3 public closeout")
    try:
        path.resolve(strict=False).relative_to(REPO.resolve(strict=True))
    except ValueError as exc:
        raise B3PublicationError("B3 public closeout must be written inside checkout") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B3PublicationError("B3 public closeout already exists")
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        if os.name != "nt":
            directory_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def run_self_test() -> dict[str, Any]:
    failure = build_public_failure(
        failure_class="matrix_execution_failed",
        completed_group_count=3,
        logical_record_count=91,
        durable_treatment_artifact_count=91,
    )
    first = b2p._synthetic_summary(b2p.B2_ADAPTER_IDS[0])
    tied = dataclasses.replace(first, adapter_id=b2p.B2_ADAPTER_IDS[1])
    tie_ranks = b2p.competition_ranks([first, tied])
    readiness = b3ready._build_report(
        runtime_publication_checkpoint="a" * 40,
        runtime_publication_ci_run_id=1,
        runtime_publication_ci_conclusion="success",
        runtime_qualification_digest="b3qual_" + "b" * 64,
        runtime_public_file_sha256="c" * 64,
        historical_repository_count=48,
        excluded_repository_count=2,
        excluded_synthetic_source_count=2,
        query_gate=b3ready._synthetic_query_gate(),
        observed_margins=b3ready._frozen_margins(),
    )
    summaries = [b2p._synthetic_summary(adapter_id) for adapter_id in b2p.B2_ADAPTER_IDS]
    arms = [
        SimpleNamespace(
            summary=summary,
            terminal_support_count=0,
            executed_adapter_record_count=240,
        )
        for summary in summaries
    ]
    result = SimpleNamespace(
        logical_record_count=1440,
        records=[None] * 1440,
        terminal_support_cells=[],
        gate_result=SimpleNamespace(passed=True),
        provider_network_call_count=0,
        repo_lock=None,
        tasks=[SimpleNamespace(task_slug="private-task-123", query="status")],
    )
    with tempfile.TemporaryDirectory(prefix="openlocus-b3-publication-") as temporary:
        readiness_path = Path(temporary) / "readiness.json"
        readiness_path.write_text(
            json.dumps(readiness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        authorization = {
            "readiness_report_digest": readiness["readiness_digest"],
            "readiness_report_file_sha256": hashlib.sha256(
                readiness_path.read_bytes()
            ).hexdigest(),
            "readiness_checkpoint": "d" * 40,
            "readiness_ci_run_id": 2,
            "readiness_ci_conclusion": "success",
        }
        success = build_public_result(
            result=result,
            arm_results=arms,
            decision=b2p.evaluate_tournament(summaries),
            readiness_report=readiness,
            readiness_report_path=readiness_path,
            launch_authorization=authorization,
        )
    checks = {
        "failure_valid": not validate_public_failure(failure),
        "success_valid": not validate_public_result(success),
        "common_query_does_not_match_public_key_name": not _scan_public(
            success, private_exact_tokens=["status"]
        ),
        "failure_has_no_arms": "arms" not in failure,
        "failure_retry_forbidden": failure["decision"]["retry_authorized"] is False,
        "partial_durable_artifact_closeout_supported": not validate_public_failure(
            build_public_failure(
                failure_class="matrix_execution_failed",
                completed_group_count=0,
                logical_record_count=0,
                durable_treatment_artifact_count=1,
            )
        ),
        "tie_policy_permits_shared_rank": len(set(tie_ranks.values())) < len(tie_ranks),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    failure = build_public_failure(
        failure_class="matrix_execution_failed",
        completed_group_count=3,
        logical_record_count=91,
        durable_treatment_artifact_count=91,
    )
    leaked = copy.deepcopy(failure)
    leaked["execution_aggregate"]["quality_rank"] = 1
    zero = copy.deepcopy(failure)
    zero["execution_aggregate"]["durable_treatment_artifact_count"] = 0
    checks = {
        "metric_leak_rejected": bool(validate_public_failure(leaked)),
        "zero_durable_artifact_failure_rejected": bool(validate_public_failure(zero)),
        "exact_private_value_rejected": bool(
            _scan_public({"value": "status"}, private_exact_tokens=["status"])
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B3PublicationError",
    "build_public_failure",
    "build_public_result",
    "validate_public_failure",
    "validate_public_result",
    "write_public",
]
