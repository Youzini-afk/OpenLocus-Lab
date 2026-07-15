#!/usr/bin/env python3
"""B2.4 scorer wrapper and aggregate-only public result boundary."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_protocol as b2p
import product_bakeoff_b2_scorer as b2s
import product_bakeoff_b21_protocol as b21p
import product_bakeoff_b21_scorer as b21s
from product_bakeoff_b21_runner import B21RunResult
from product_bakeoff_b24_protocol import (
    B24_PARENT_B23_QUALIFICATION_DIGEST,
    B24_PARENT_B23_QUALIFICATION_SHA256,
    B24_REPORT_SCHEMA_VERSION,
    b24_execution_schedule_digest,
    b24_holdout_frame_digest,
    b24_source_bundle_digest,
    b24_spec_digest,
)


B24_SCORER_VERSION = "product_bakeoff_b24_scorer.v1"
B24_RESULT_SCHEMA = "product_bakeoff_b24_tournament_result.v1"
B24_RESULT_STATUS = "product_bakeoff_b24_internal_tournament_complete_aggregate_only"
B24_RESULT_CLAIM = "internal_product_decision_evidence_for_phase_c_no_public_default_claim"


class B24ScoreError(ValueError):
    """Fail-closed B2.4 scoring/publication error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_result_report(report: Any, *, private_tokens: Sequence[str] = ()) -> list[str]:
    errors = list(b21s.scan_result_report(report, private_tokens=private_tokens))
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "b24_private_",
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "launch_authorization_digest",
    ):
        if token in raw:
            errors.append(f"private B2.4 token forbidden in public result: {token}")
    return sorted(set(errors))


def build_public_result(
    *,
    result: B21RunResult,
    inherited_public: Mapping[str, Any],
    readiness_report: Mapping[str, Any],
    readiness_report_path: Path,
    launch_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    inherited_errors = b21s.validate_public_result(dict(inherited_public))
    if inherited_errors:
        raise B24ScoreError(
            "inherited B2.1 aggregate failed validation: " + "; ".join(inherited_errors)
        )
    if readiness_report.get("readiness_digest") != launch_authorization.get(
        "readiness_report_digest"
    ):
        raise B24ScoreError("readiness report differs from launch authorization")
    if _file_sha256(readiness_report_path) != launch_authorization.get(
        "readiness_report_file_sha256"
    ):
        raise B24ScoreError("readiness report bytes differ from launch authorization")
    report: dict[str, Any] = {
        "schema_version": B24_RESULT_SCHEMA,
        "phase": "product_bakeoff_b24_fresh_holdout_qualified_linux_tournament",
        "status": B24_RESULT_STATUS,
        "claim_level": B24_RESULT_CLAIM,
        "aggregate_only": True,
        "product_default_changed": False,
        "public_winner_declared": False,
        "phase_c_validation_required": True,
        "protocol": {
            "protocol_schema_version": B24_REPORT_SCHEMA_VERSION,
            "spec_digest": b24_spec_digest(),
            "source_bundle_digest": b24_source_bundle_digest(),
            "holdout_frame_digest": b24_holdout_frame_digest(),
            "execution_schedule_digest": b24_execution_schedule_digest(),
            "inherited_b21_engine": {
                "spec_digest": b21p.b21_spec_digest(),
                "source_bundle_digest": b21p.b21_source_bundle_digest(),
                "holdout_frame_digest": b21p.b21_task_frame_digest(),
                "execution_schedule_digest": b21p.b21_execution_schedule_digest(),
            },
        },
        "runner_qualification": {
            "qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
            "qualification_file_sha256": B24_PARENT_B23_QUALIFICATION_SHA256,
            "same_qualified_machine_admitted_before_execution": True,
            "exact_runner_profile_public": False,
        },
        "readiness_gate": {
            "readiness_digest": readiness_report["readiness_digest"],
            "readiness_file_sha256": _file_sha256(readiness_report_path),
            "readiness_checkpoint": launch_authorization["readiness_checkpoint"],
            "readiness_ci_run_id": launch_authorization["readiness_ci_run_id"],
            "readiness_ci_conclusion": launch_authorization["readiness_ci_conclusion"],
        },
        "freeze_verification": {
            "fresh_against_b2_and_b21_repository_task_oracle_frames": True,
            "runtime_and_longrun_timeouts_frozen_before_execution": True,
            "freeze_receipt_validated_before_execution": True,
            "private_launch_authorization_validated_before_execution": True,
            "private_freeze_and_launch_digests_public": False,
        },
        "matrix": dict(inherited_public["matrix"]),
        "resource_percentile_rule": inherited_public["resource_percentile_rule"],
        "arms": list(inherited_public["arms"]),
        "tournament_decision": dict(inherited_public["tournament_decision"]),
        "publication_limits": {
            "repo_level_results_public": False,
            "task_level_results_public": False,
            "task_text_query_oracle_public": False,
            "per_cell_resources_public": False,
            "private_freeze_and_launch_digests_public": False,
            "per_task_parent_divergence_public": False,
            "exact_runner_profile_or_location_public": False,
        },
        "result_digest": "",
    }
    report["result_digest"] = "b24result_" + hashlib.sha256(
        _canonical({key: value for key, value in report.items() if key != "result_digest"}).encode(
            "utf-8"
        )
    ).hexdigest()
    errors = scan_result_report(report, private_tokens=b2s._private_tokens(result))
    if errors:
        raise B24ScoreError("public B2.4 result privacy scan failed: " + "; ".join(errors))
    return report


def _as_inherited_b21_report(report: Mapping[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": b21s.B21_RESULT_SCHEMA,
        "phase": "product_bakeoff_b21_own_parent_holdout_tournament",
        "status": b21s.B21_RESULT_STATUS,
        "claim_level": b21s.B21_RESULT_CLAIM,
        "aggregate_only": True,
        "product_default_changed": False,
        "public_winner_declared": False,
        "phase_c_validation_required": True,
        "protocol": {
            "protocol_schema_version": b21p.B21_REPORT_SCHEMA_VERSION,
            "spec_digest": b21p.b21_spec_digest(),
            "source_bundle_digest": b21p.b21_source_bundle_digest(),
            "holdout_frame_digest": b21p.b21_task_frame_digest(),
            "execution_schedule_digest": b21p.b21_execution_schedule_digest(),
        },
        "freeze_verification": {
            "fresh_holdout_repository_task_oracle_and_runtime_frozen": True,
            "freeze_receipt_validated_before_execution": True,
            "private_freeze_digests_public": False,
        },
        "matrix": dict(report.get("matrix") or {}),
        "resource_percentile_rule": report.get("resource_percentile_rule"),
        "arms": list(report.get("arms") or []),
        "tournament_decision": dict(report.get("tournament_decision") or {}),
        "publication_limits": {
            "repo_level_results_public": False,
            "task_level_results_public": False,
            "task_text_public": False,
            "oracle_rows_public": False,
            "per_cell_resources_public": False,
            "private_freeze_digests_public": False,
            "per_task_parent_divergence_public": False,
        },
    }
    value["result_digest"] = "b21result_" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return value


def validate_public_result(report: Any) -> list[str]:
    errors = scan_result_report(report)
    if not isinstance(report, dict):
        return sorted(set([*errors, "public B2.4 result must be an object"]))
    expected_keys = {
        "schema_version",
        "phase",
        "status",
        "claim_level",
        "aggregate_only",
        "product_default_changed",
        "public_winner_declared",
        "phase_c_validation_required",
        "protocol",
        "runner_qualification",
        "readiness_gate",
        "freeze_verification",
        "matrix",
        "resource_percentile_rule",
        "arms",
        "tournament_decision",
        "publication_limits",
        "result_digest",
    }
    if set(report) != expected_keys:
        errors.append("public B2.4 result top-level shape drift")
    if report.get("schema_version") != B24_RESULT_SCHEMA:
        errors.append("public B2.4 result schema mismatch")
    if report.get("status") != B24_RESULT_STATUS:
        errors.append("public B2.4 result status mismatch")
    if report.get("aggregate_only") is not True:
        errors.append("public B2.4 result must be aggregate-only")
    protocol = report.get("protocol") or {}
    expected_protocol = {
        "protocol_schema_version": B24_REPORT_SCHEMA_VERSION,
        "spec_digest": b24_spec_digest(),
        "source_bundle_digest": b24_source_bundle_digest(),
        "holdout_frame_digest": b24_holdout_frame_digest(),
        "execution_schedule_digest": b24_execution_schedule_digest(),
        "inherited_b21_engine": {
            "spec_digest": b21p.b21_spec_digest(),
            "source_bundle_digest": b21p.b21_source_bundle_digest(),
            "holdout_frame_digest": b21p.b21_task_frame_digest(),
            "execution_schedule_digest": b21p.b21_execution_schedule_digest(),
        },
    }
    if protocol != expected_protocol:
        errors.append("public B2.4 protocol binding mismatch")
    qualification = report.get("runner_qualification") or {}
    expected_qualification = {
        "qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
        "qualification_file_sha256": B24_PARENT_B23_QUALIFICATION_SHA256,
        "same_qualified_machine_admitted_before_execution": True,
        "exact_runner_profile_public": False,
    }
    if qualification != expected_qualification:
        errors.append("public B2.4 runner qualification binding mismatch")
    readiness = report.get("readiness_gate") or {}
    if readiness.get("readiness_ci_conclusion") != "success":
        errors.append("public B2.4 readiness CI did not succeed")
    if not isinstance(readiness.get("readiness_ci_run_id"), int) or readiness.get(
        "readiness_ci_run_id", 0
    ) <= 0:
        errors.append("public B2.4 readiness CI run id malformed")
    if not isinstance(readiness.get("readiness_digest"), str) or not str(
        readiness.get("readiness_digest")
    ).startswith("b24ready_"):
        errors.append("public B2.4 readiness digest malformed")
    inherited_errors = b21s.validate_public_result(_as_inherited_b21_report(report))
    errors.extend(f"inherited engine: {error}" for error in inherited_errors)
    payload = dict(report)
    observed = payload.pop("result_digest", None)
    expected = "b24result_" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    if observed != expected:
        errors.append("public B2.4 result digest mismatch")
    return sorted(set(errors))


def score_b24(
    *,
    result: B21RunResult,
    oracle_manifest_path: Path,
    readiness_report: Mapping[str, Any],
    readiness_report_path: Path,
    launch_authorization: Mapping[str, Any],
) -> tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]:
    arm_results, decision, inherited_public = b21s.score_b21(
        result=result,
        oracle_manifest_path=oracle_manifest_path,
    )
    public = build_public_result(
        result=result,
        inherited_public=inherited_public,
        readiness_report=readiness_report,
        readiness_report_path=readiness_report_path,
        launch_authorization=launch_authorization,
    )
    errors = validate_public_result(public)
    if errors:
        raise B24ScoreError("generated B2.4 public result invalid: " + "; ".join(errors))
    return arm_results, decision, public


def write_public_result(path: Path, report: Mapping[str, Any]) -> Path:
    errors = validate_public_result(dict(report))
    if errors:
        raise B24ScoreError("refusing to write invalid B2.4 public result")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B24ScoreError("public B2.4 result output already exists")
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
        temporary.chmod(0o600)
        if os.path.lexists(target):
            raise B24ScoreError("public B2.4 result appeared concurrently")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def run_self_test() -> dict[str, Any]:
    inherited = b21s.run_self_test()
    checks = [
        ("inherited_scorer_self_test", inherited["passed"]),
        ("shared_competition_rank", b2p.B2_TIE_POLICY["exact_equal_quality_vector"] == "shared_competition_rank"),
        ("six_arms", len(b2p.B2_ADAPTER_IDS) == 6),
        ("empty_report_rejected", bool(validate_public_result({}))),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    inherited = b21s.run_fault_test()
    checks = [
        ("inherited_scorer_fault_test", inherited["passed"]),
        ("private_token_rejected", bool(scan_result_report({"x": "b24_private_secret"}))),
        ("missing_matrix_rejected", bool(validate_public_result({"schema_version": B24_RESULT_SCHEMA}))),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B24ScoreError",
    "B24_RESULT_SCHEMA",
    "build_public_result",
    "validate_public_result",
    "score_b24",
    "write_public_result",
    "run_self_test",
    "run_fault_test",
]
