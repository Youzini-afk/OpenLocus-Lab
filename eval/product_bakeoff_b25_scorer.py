#!/usr/bin/env python3
"""B2.5 scorer wrapper and aggregate-only public result boundary."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_protocol as b2p
import product_bakeoff_b2_scorer as b2s
import product_bakeoff_b21_protocol as b21p
import product_bakeoff_b21_scorer as b21s
from product_bakeoff_b21_runner import B21RunResult
from product_bakeoff_b25_protocol import (
    B25_PARENT_B23_QUALIFICATION_DIGEST,
    B25_PARENT_B24_FAILURE_DIGEST,
    B25_PARENT_B24_REPAIR_DIGEST,
    B25_REPORT_SCHEMA_VERSION,
    b25_execution_schedule_digest,
    b25_holdout_frame_digest,
    b25_source_bundle_digest,
    b25_spec_digest,
)


B25_SCORER_VERSION = "product_bakeoff_b25_scorer.v1"
B25_RESULT_SCHEMA = "product_bakeoff_b25_tournament_result.v1"
B25_RESULT_STATUS = "product_bakeoff_b25_internal_tournament_complete_aggregate_only"
B25_RESULT_CLAIM = "internal_product_decision_evidence_for_phase_c_no_public_default_claim"
B25_RESULT_PUBLICATION_LIMITS = {
    "repo_level_results_public": False,
    "task_level_results_public": False,
    "task_text_query_oracle_public": False,
    "per_cell_resources_public": False,
    "private_freeze_query_and_launch_digests_public": False,
    "per_task_parent_divergence_public": False,
    "exact_runner_profile_or_location_public": False,
}
B25_RESULT_FREEZE_VERIFICATION = {
    "fresh_against_b2_b21_and_b24_repository_task_oracle_frames": True,
    "runtime_query_gate_and_longrun_timeouts_frozen_before_execution": True,
    "freeze_receipt_validated_before_execution": True,
    "private_launch_authorization_validated_before_execution": True,
    "private_freeze_query_and_launch_digests_public": False,
}


class B25ScoreError(ValueError):
    """Fail-closed B2.5 scoring/publication error."""


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
        "b25_private_",
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "query_gate_digest",
        "b25query_",
        "launch_authorization_digest",
        "b25qpriv_",
    ):
        if token in raw:
            errors.append(f"private B2.5 token forbidden in public result: {token}")
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
        raise B25ScoreError("inherited B2.1 aggregate failed validation")
    if readiness_report.get("readiness_digest") != launch_authorization.get(
        "readiness_report_digest"
    ):
        raise B25ScoreError("readiness report differs from launch authorization")
    if _file_sha256(readiness_report_path) != launch_authorization.get(
        "readiness_report_file_sha256"
    ):
        raise B25ScoreError("readiness bytes differ from launch authorization")
    runner_gate = readiness_report["runner_qualification_gate"]
    query_gate = readiness_report["query_compatibility_gate"]
    report: dict[str, Any] = {
        "schema_version": B25_RESULT_SCHEMA,
        "phase": "product_bakeoff_b25_fresh_tokenizer_qualified_linux_tournament",
        "status": B25_RESULT_STATUS,
        "claim_level": B25_RESULT_CLAIM,
        "aggregate_only": True,
        "product_default_changed": False,
        "public_winner_declared": False,
        "phase_c_validation_required": True,
        "protocol": {
            "protocol_schema_version": B25_REPORT_SCHEMA_VERSION,
            "spec_digest": b25_spec_digest(),
            "source_bundle_digest": b25_source_bundle_digest(),
            "holdout_frame_digest": b25_holdout_frame_digest(),
            "execution_schedule_digest": b25_execution_schedule_digest(),
            "inherited_b21_engine": {
                "spec_digest": b21p.b21_spec_digest(),
                "source_bundle_digest": b21p.b21_source_bundle_digest(),
                "holdout_frame_digest": b21p.b21_task_frame_digest(),
                "execution_schedule_digest": b21p.b21_execution_schedule_digest(),
            },
        },
        "historical_closeout": {
            "b24_failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
            "b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
            "b24_result_reopened": False,
            "b24_incomplete_output_reused": False,
        },
        "runner_qualification": {
            "parent_b23_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
            "runtime_qualification_digest": runner_gate[
                "runtime_qualification_digest"
            ],
            "runtime_qualification_file_sha256": runner_gate[
                "runtime_qualification_file_sha256"
            ],
            "same_qualified_machine_admitted_before_execution": True,
            "exact_runner_profile_public": False,
        },
        "query_compatibility": {
            "task_count": query_gate["task_count"],
            "tokenizable_query_count": query_gate["tokenizable_query_count"],
            "positive_span_count": query_gate["positive_span_count"],
            "compatible_positive_span_count": query_gate[
                "compatible_positive_span_count"
            ],
            "source_only_gate_passed_before_execution": True,
            "private_query_path_or_gate_digest_public": False,
        },
        "readiness_gate": {
            "readiness_digest": readiness_report["readiness_digest"],
            "readiness_file_sha256": _file_sha256(readiness_report_path),
            "readiness_checkpoint": launch_authorization["readiness_checkpoint"],
            "readiness_ci_run_id": launch_authorization["readiness_ci_run_id"],
            "readiness_ci_conclusion": launch_authorization[
                "readiness_ci_conclusion"
            ],
        },
        "freeze_verification": dict(B25_RESULT_FREEZE_VERIFICATION),
        "matrix": dict(inherited_public["matrix"]),
        "resource_percentile_rule": inherited_public["resource_percentile_rule"],
        "arms": list(inherited_public["arms"]),
        "tournament_decision": dict(inherited_public["tournament_decision"]),
        "publication_limits": dict(B25_RESULT_PUBLICATION_LIMITS),
        "result_digest": "",
    }
    payload = {key: value for key, value in report.items() if key != "result_digest"}
    report["result_digest"] = "b25result_" + hashlib.sha256(
        _canonical(payload).encode("utf-8")
    ).hexdigest()
    errors = scan_result_report(report, private_tokens=b2s._private_tokens(result))
    if errors:
        raise B25ScoreError("public B2.5 result privacy scan failed: " + "; ".join(errors))
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
        return sorted(set([*errors, "public B2.5 result must be an object"]))
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
        "historical_closeout",
        "runner_qualification",
        "query_compatibility",
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
        errors.append("public B2.5 result top-level shape drift")
    if report.get("schema_version") != B25_RESULT_SCHEMA:
        errors.append("public B2.5 result schema mismatch")
    if report.get("status") != B25_RESULT_STATUS:
        errors.append("public B2.5 result status mismatch")
    if report.get("aggregate_only") is not True:
        errors.append("public B2.5 result must be aggregate-only")
    if report.get("phase") != "product_bakeoff_b25_fresh_tokenizer_qualified_linux_tournament":
        errors.append("public B2.5 result phase mismatch")
    if report.get("claim_level") != B25_RESULT_CLAIM:
        errors.append("public B2.5 result claim mismatch")
    for key, expected in (
        ("product_default_changed", False),
        ("public_winner_declared", False),
        ("phase_c_validation_required", True),
    ):
        if report.get(key) is not expected:
            errors.append(f"public B2.5 result {key} drifted")
    expected_protocol = {
        "protocol_schema_version": B25_REPORT_SCHEMA_VERSION,
        "spec_digest": b25_spec_digest(),
        "source_bundle_digest": b25_source_bundle_digest(),
        "holdout_frame_digest": b25_holdout_frame_digest(),
        "execution_schedule_digest": b25_execution_schedule_digest(),
        "inherited_b21_engine": {
            "spec_digest": b21p.b21_spec_digest(),
            "source_bundle_digest": b21p.b21_source_bundle_digest(),
            "holdout_frame_digest": b21p.b21_task_frame_digest(),
            "execution_schedule_digest": b21p.b21_execution_schedule_digest(),
        },
    }
    if report.get("protocol") != expected_protocol:
        errors.append("public B2.5 protocol binding mismatch")
    expected_history = {
        "b24_failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
        "b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
        "b24_result_reopened": False,
        "b24_incomplete_output_reused": False,
    }
    if report.get("historical_closeout") != expected_history:
        errors.append("public B2.5 historical closeout drifted")
    runner = report.get("runner_qualification") or {}
    if set(runner) != {
        "parent_b23_qualification_digest",
        "runtime_qualification_digest",
        "runtime_qualification_file_sha256",
        "same_qualified_machine_admitted_before_execution",
        "exact_runner_profile_public",
    }:
        errors.append("public B2.5 runner qualification shape drift")
    if runner.get("parent_b23_qualification_digest") != B25_PARENT_B23_QUALIFICATION_DIGEST:
        errors.append("public B2.5 parent runner qualification drifted")
    if not isinstance(runner.get("runtime_qualification_digest"), str) or not str(
        runner.get("runtime_qualification_digest")
    ).startswith("b25qual_"):
        errors.append("public B2.5 runtime qualification digest malformed")
    if runner.get("same_qualified_machine_admitted_before_execution") is not True:
        errors.append("public B2.5 same-machine admission drifted")
    if runner.get("exact_runner_profile_public") is not False:
        errors.append("public B2.5 runner profile publication drifted")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(runner.get("runtime_qualification_file_sha256", ""))
    ):
        errors.append("public B2.5 runtime qualification file digest malformed")
    query = report.get("query_compatibility") or {}
    if set(query) != {
        "task_count",
        "tokenizable_query_count",
        "positive_span_count",
        "compatible_positive_span_count",
        "source_only_gate_passed_before_execution",
        "private_query_path_or_gate_digest_public",
    }:
        errors.append("public B2.5 query compatibility shape drift")
    if query.get("task_count") != 48 or query.get("tokenizable_query_count") != 48:
        errors.append("public B2.5 query compatibility task counts drifted")
    positives = query.get("positive_span_count")
    if not isinstance(positives, int) or not 48 <= positives <= 60:
        errors.append("public B2.5 query positive span count malformed")
    if query.get("compatible_positive_span_count") != positives:
        errors.append("public B2.5 query compatibility counts drifted")
    if query.get("source_only_gate_passed_before_execution") is not True:
        errors.append("public B2.5 query compatibility gate drifted")
    if query.get("private_query_path_or_gate_digest_public") is not False:
        errors.append("public B2.5 private query publication drifted")
    readiness = report.get("readiness_gate") or {}
    if set(readiness) != {
        "readiness_digest",
        "readiness_file_sha256",
        "readiness_checkpoint",
        "readiness_ci_run_id",
        "readiness_ci_conclusion",
    }:
        errors.append("public B2.5 readiness gate shape drift")
    if readiness.get("readiness_ci_conclusion") != "success":
        errors.append("public B2.5 readiness CI did not succeed")
    if not isinstance(readiness.get("readiness_ci_run_id"), int) or readiness.get(
        "readiness_ci_run_id", 0
    ) <= 0:
        errors.append("public B2.5 readiness CI run id malformed")
    if not isinstance(readiness.get("readiness_digest"), str) or not str(
        readiness.get("readiness_digest")
    ).startswith("b25ready_"):
        errors.append("public B2.5 readiness digest malformed")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(readiness.get("readiness_file_sha256", ""))
    ):
        errors.append("public B2.5 readiness file digest malformed")
    if not re.fullmatch(
        r"[0-9a-f]{40}", str(readiness.get("readiness_checkpoint", ""))
    ):
        errors.append("public B2.5 readiness checkpoint malformed")
    if report.get("freeze_verification") != B25_RESULT_FREEZE_VERIFICATION:
        errors.append("public B2.5 freeze verification drifted")
    if report.get("publication_limits") != B25_RESULT_PUBLICATION_LIMITS:
        errors.append("public B2.5 publication limits drifted")
    errors.extend(
        f"inherited engine: {error}"
        for error in b21s.validate_public_result(_as_inherited_b21_report(report))
    )
    payload = dict(report)
    observed = payload.pop("result_digest", None)
    expected = "b25result_" + hashlib.sha256(
        _canonical(payload).encode("utf-8")
    ).hexdigest()
    if observed != expected:
        errors.append("public B2.5 result digest mismatch")
    return sorted(set(errors))


def score_b25(
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
        raise B25ScoreError("generated B2.5 public result invalid: " + "; ".join(errors))
    return arm_results, decision, public


def write_public_result(path: Path, report: Mapping[str, Any]) -> Path:
    if validate_public_result(dict(report)):
        raise B25ScoreError("refusing to write invalid B2.5 public result")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B25ScoreError("public B2.5 result output already exists")
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
            raise B25ScoreError("public B2.5 result appeared concurrently")
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
        ("private_token_rejected", bool(scan_result_report({"x": "b25_private_secret"}))),
        ("query_digest_rejected", bool(scan_result_report({"x": "b25query_secret"}))),
        ("missing_matrix_rejected", bool(validate_public_result({"schema_version": B25_RESULT_SCHEMA}))),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B25ScoreError",
    "B25_RESULT_SCHEMA",
    "build_public_result",
    "validate_public_result",
    "score_b25",
    "write_public_result",
    "run_self_test",
    "run_fault_test",
]
