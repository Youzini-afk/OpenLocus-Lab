#!/usr/bin/env python3
"""Aggregate-only failed-closed publication for the terminal B2.5 attempt.

This module is post-terminal publication tooling.  It does not read private
manifests, execution rows, treatment output, oracle data, or score data.  The
formal runner already froze the exact private failure evidence outside the
checkout; this file only validates the closed public facts permitted by the
B2.5 publication boundary.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
import product_bakeoff_terminal_archive as archive


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = (
    REPO_ROOT
    / "artifacts"
    / "product_bakeoff_b25_readiness"
    / "product_bakeoff_b25_holdout_readiness.json"
)
PROTOCOL_REPORT_PATH = (
    REPO_ROOT
    / "artifacts"
    / "product_bakeoff_b25_protocol"
    / "product_bakeoff_b25_protocol_report.json"
)

B25_FAILURE_SCHEMA = "product_bakeoff_b25_failed_closed_aggregate.v1"
B25_FAILURE_STATUS = "product_bakeoff_b25_execution_failed_closed_no_result"
B25_FAILURE_PHASE = "product_bakeoff_b25_fresh_tokenizer_qualified_holdout_tournament"
B25_FAILURE_DATE = "2026-07-17"
B25_FAILURE_CLAIM = (
    "complete_matrix_comparability_gate_failure_pre_score_no_tournament_result"
)
B25_FAILURE_CATEGORY = "complete_matrix_comparability_gate_failure"
B25_READINESS_CHECKPOINT = "7523d9673afff867f69d8a87338b8d651952dd96"
B25_READINESS_CI_RUN_ID = 29500666349
B25_READINESS_CI_CONCLUSION = "success"

B25_FAILURE_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "candidate_plan_or_failover_public": False,
    "exact_failed_gate_or_private_detail_public": False,
    "exact_runner_profile_or_location_public": False,
    "intermediate_arm_quality_resource_or_ranking_metric_public": False,
    "per_arm_or_task_output_public": False,
    "private_evidence_digest_public": False,
    "private_manifest_freeze_launch_or_run_digest_public": False,
    "repository_identity_public": False,
    "source_location_range_or_excerpt_public": False,
    "task_text_query_oracle_public": False,
}

B25_FAILURE_ANTI_ADAPTATION = {
    "failed_attempt_may_be_restarted_resumed_or_retried": False,
    "failed_complete_matrix_may_be_scored_or_ranked": False,
    "failed_or_losing_cells_may_be_selectively_rerun": False,
    "frozen_comparability_gate_may_be_changed_for_b25": False,
    "missing_or_rejected_values_may_be_imputed": False,
    "same_b25_launch_authorization_may_be_reused": False,
    "second_b25_launch_may_be_performed": False,
    "task_query_or_oracle_may_be_edited": False,
}

B25_FAILURE_NEXT_ACTION = (
    "Close B2.5 as failed_closed_no_result. Do not relaunch, resume, repair, "
    "score, rank, or reuse the B2.5 matrix or launch authorization. Any later "
    "product tournament must be separately preregistered with a fresh holdout "
    "and must freeze its comparability policy before any treatment output."
)


class B25FailureCloseoutError(ValueError):
    """Fail-closed error for the public B2.5 terminal closeout."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("failure_aggregate_digest", None)
    return "b25failure_" + hashlib.sha256(_canonical(payload)).hexdigest()


def _load_public_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    archive_errors = archive.validate_archive("b25_parents")
    if archive_errors:
        raise B25FailureCloseoutError("B2.5 terminal parent archive is invalid")
    readiness = b2c.load_json(READINESS_PATH)
    protocol = b2c.load_json(PROTOCOL_REPORT_PATH)
    return readiness, protocol


def build_public_failure_closeout() -> dict[str, Any]:
    readiness, protocol = _load_public_parents()
    gate = readiness["preauthoring_publication_gate"]
    decision = readiness["decision"]
    execution_state = readiness["execution_state"]
    if not (
        decision["private_holdout_frozen"] is True
        and decision["query_compatibility_gate_passed"] is True
        and decision["future_tournament_execution_authorized"] is False
        and execution_state["treatment_output_count"] == 0
    ):
        raise B25FailureCloseoutError("B2.5 readiness boundary drifted")

    report: dict[str, Any] = {
        "schema_version": B25_FAILURE_SCHEMA,
        "phase": B25_FAILURE_PHASE,
        "date": B25_FAILURE_DATE,
        "status": B25_FAILURE_STATUS,
        "claim_level": B25_FAILURE_CLAIM,
        "source_gate": {
            "readiness_checkpoint": B25_READINESS_CHECKPOINT,
            "ci_run_id": B25_READINESS_CI_RUN_ID,
            "ci_conclusion": B25_READINESS_CI_CONCLUSION,
            "readiness_digest": readiness["readiness_digest"],
        },
        "protocol": {
            "spec_digest": gate["b25_spec_digest"],
            "source_bundle_digest": gate["b25_source_bundle_digest"],
            "holdout_frame_digest": gate["b25_holdout_frame_digest"],
            "execution_schedule_digest": gate["b25_execution_schedule_digest"],
            "protocol_report_digest": protocol["protocol_digest"],
        },
        "execution": {
            "private_holdout_and_runtime_frozen_before_execution": True,
            "formal_attempt_boundary_crossed": True,
            "formal_tournament_attempt_count": 1,
            "worker_entered": True,
            "runner_admitted": True,
            "launch_release_created": True,
            "expected_group_count": 48,
            "completed_group_count": 48,
            "expected_logical_record_count": 1440,
            "logical_record_count": 1440,
            "complete_matrix_gate_passed": True,
            "pre_score_gates_passed": False,
            "pre_score_failure_gate_count": 1,
            "provider_network_call_count": 0,
            "tournament_scoring_executed": False,
            "quality_or_resource_ranking_executed": False,
            "phase_c_shortlist_selected": False,
            "product_default_changed": False,
            "public_tournament_result_exists": False,
            "terminal_exit_code": 1,
        },
        "failure": {
            "category": B25_FAILURE_CATEGORY,
            "failed_closed": True,
            "complete_matrix_present": True,
            "complete_matrix_invalid_for_scoring": True,
            "comparability_gate_family_failed": True,
            "exact_failed_gate_public": False,
            "private_failure_evidence_frozen": True,
            "infrastructure_capacity_failure": False,
            "provider_or_model_failure": False,
            "description": (
                "All 48 groups and all 1,440 logical records completed, but one "
                "frozen pre-score comparability gate failed. The scorer remained "
                "unexecuted, so no arm score, rank, shortlist, product-default "
                "decision, or tournament result exists. The exact failed gate and "
                "its private evidence remain non-public. No restart, resume, "
                "selective rerun, gate change, or post-failure scoring is authorized."
            ),
        },
        "terminal_attempt_boundary": {
            "launch_authorization_attempt_number": 1,
            "restart_or_retry_authorized": False,
            "second_launch_performed": False,
            "terminal_exit_receipt_created": True,
            "complete_matrix_retained_private": True,
            "treatment_output_reused": False,
        },
        "anti_adaptation": copy.deepcopy(B25_FAILURE_ANTI_ADAPTATION),
        "publication_limits": copy.deepcopy(B25_FAILURE_PUBLICATION_LIMITS),
        "next_authorized_action": B25_FAILURE_NEXT_ACTION,
        "failure_aggregate_digest": "",
    }
    report["failure_aggregate_digest"] = _digest(report)
    return report


def validate_public_failure_closeout(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["public B2.5 failure closeout must be an object"]
    errors = list(b2p.scan_public_report(report))
    try:
        expected = build_public_failure_closeout()
    except (B25FailureCloseoutError, OSError, ValueError) as exc:
        errors.append(f"cannot rebuild public B2.5 failure closeout: {type(exc).__name__}")
        return sorted(set(errors))
    if report != expected:
        errors.append("public B2.5 failure closeout drifted from closed terminal facts")
    if report.get("failure_aggregate_digest") != _digest(report):
        errors.append("public B2.5 failure closeout digest mismatch")
    return sorted(set(errors))


def write_public(path: Path, report: Mapping[str, Any]) -> Path:
    if validate_public_failure_closeout(dict(report)):
        raise B25FailureCloseoutError("refusing to write invalid B2.5 failure closeout")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B25FailureCloseoutError("public B2.5 failure closeout already exists")
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
        if os.path.lexists(target):
            raise B25FailureCloseoutError(
                "public B2.5 failure closeout appeared concurrently"
            )
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def run_self_test() -> dict[str, Any]:
    first = build_public_failure_closeout()
    second = build_public_failure_closeout()
    checks = [
        ("deterministic", first == second),
        ("valid", not validate_public_failure_closeout(first)),
        ("complete_matrix", first["execution"]["logical_record_count"] == 1440),
        ("pre_score_failed", first["execution"]["pre_score_gates_passed"] is False),
        ("scoring_absent", first["execution"]["tournament_scoring_executed"] is False),
        ("result_absent", first["execution"]["public_tournament_result_exists"] is False),
        ("digest_stable", first["failure_aggregate_digest"] == _digest(first)),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    mutators: dict[str, Callable[[dict[str, Any]], None]] = {
        "status": lambda value: value.__setitem__("status", "complete"),
        "group_count": lambda value: value["execution"].__setitem__(
            "completed_group_count", 47
        ),
        "scoring": lambda value: value["execution"].__setitem__(
            "tournament_scoring_executed", True
        ),
        "failure_category": lambda value: value["failure"].__setitem__(
            "category", "winner_selected"
        ),
        "private_detail": lambda value: value["failure"].__setitem__(
            "exact_failed_gate_public", True
        ),
        "digest": lambda value: value.__setitem__(
            "failure_aggregate_digest", "b25failure_" + "0" * 64
        ),
    }
    checks: list[tuple[str, bool]] = []
    for name, mutate in mutators.items():
        value = build_public_failure_closeout()
        mutate(value)
        checks.append((name, bool(validate_public_failure_closeout(value))))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def _print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="B2.5 aggregate-only terminal failure closeout"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-public", type=Path)
    mode.add_argument("--validate-public", type=Path)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = run_self_test()
        _print(result)
        return 0 if result["passed"] else 1
    if args.fault_test:
        result = run_fault_test()
        _print(result)
        return 0 if result["passed"] else 1
    if args.validate_public:
        report = b2c.load_json(args.validate_public)
        errors = validate_public_failure_closeout(report)
        _print({"passed": not errors, "errors": errors})
        return 0 if not errors else 1
    report = build_public_failure_closeout()
    write_public(args.write_public, report)
    _print(
        {
            "written": True,
            "aggregate_only": True,
            "failed_closed": True,
            "private_details_printed": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B25_FAILURE_SCHEMA",
    "B25_FAILURE_STATUS",
    "B25_FAILURE_CATEGORY",
    "B25FailureCloseoutError",
    "build_public_failure_closeout",
    "validate_public_failure_closeout",
    "write_public",
    "run_self_test",
    "run_fault_test",
]
