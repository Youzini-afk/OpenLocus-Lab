#!/usr/bin/env python3
"""Public aggregate proof for the complete offline B3 control plane."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b3_corpus as b3c
import product_bakeoff_b3_execution as b3e
import product_bakeoff_b3_protocol as b3p
import product_bakeoff_b3_publication as b3pub
import product_bakeoff_b3_readiness as b3ready
import product_bakeoff_b3_runtime_qualification as b3rq
import product_bakeoff_b3_source as b3src


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_control_integration"
    / "product_bakeoff_b3_control_integration.json"
)
PARENT_ENGINE_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_engine_integration"
    / "product_bakeoff_b3_engine_integration.json"
)
B3_CONTROL_REPORT_SCHEMA = "product_bakeoff_b3_control_integration.v1"
B3_CONTROL_STATUS = (
    "product_bakeoff_b3_offline_control_plane_complete_"
    "server_required_next_for_exact_linux_qualification"
)


class B3ControlIntegrationError(ValueError):
    """Fail-closed B3 control integration error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(report: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(report))
    payload.pop("integration_digest", None)
    return "b3control_" + hashlib.sha256(_canonical(payload)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B3ControlIntegrationError("public parent artifact must be an object")
    return value


def _module_reports(function_name: str) -> dict[str, dict[str, Any]]:
    modules = (b3src, b3rq, b3c, b3ready, b3pub, b3e)
    return {module.__name__: getattr(module, function_name)() for module in modules}


def _parent_engine() -> dict[str, Any]:
    value = _load_json(PARENT_ENGINE_PATH)
    if value.get("schema_version") != "product_bakeoff_b3_engine_integration.v1":
        raise B3ControlIntegrationError("B3 engine parent schema drifted")
    if value.get("status") != (
        "product_bakeoff_b3_runner_scorer_integration_complete_"
        "no_runtime_no_holdout_no_execution_no_result"
    ):
        raise B3ControlIntegrationError("B3 engine parent status drifted")
    if value.get("integration_digest") != (
        "b3engine_a61e54a2fe426f00ac081345ce379300b4cf8c59bdbcc43eca99f9f104579535"
    ):
        raise B3ControlIntegrationError("B3 engine parent digest drifted")
    return value


def build_report() -> dict[str, Any]:
    parent = _parent_engine()
    self_reports = _module_reports("run_self_test")
    fault_reports = _module_reports("run_fault_test")
    if not all(report["passed"] for report in (*self_reports.values(), *fault_reports.values())):
        raise B3ControlIntegrationError("B3 control module tests failed")
    report: dict[str, Any] = {
        "schema_version": B3_CONTROL_REPORT_SCHEMA,
        "phase": "product_bakeoff_b3_offline_control_plane_integration",
        "status": B3_CONTROL_STATUS,
        "claim_level": "engineering_and_synthetic_fault_tests_only_no_private_input",
        "date": "2026-07-18",
        "parent_engine": {
            "integration_digest": parent["integration_digest"],
            "canonical_sha256": hashlib.sha256(_canonical(parent)).hexdigest(),
            "runner_and_scorer_integrated": True,
        },
        "protocol_binding": {
            "b3_spec_digest": b3p.spec_digest(),
            "b3_execution_schedule_digest": b3p.execution_schedule_digest(),
            "b3_expected_observation_plan_digest": b3p.expected_observation_plan_digest(),
            "attempt_boundary": "first_durable_treatment_observation",
            "launch_release_alone_consumes_attempt": False,
        },
        "control_source_bundle_digest": b3src.control_source_bundle_digest(),
        "implemented_surfaces": {
            "freshness_against_b2_b21_b24_b25_frames": True,
            "exact_current_linux_profile_and_cli_private_freeze": True,
            "historical_machine_identity_dependency_removed": True,
            "aggregate_runtime_qualification_publication": True,
            "private_holdout_authoring_binding_and_freeze": True,
            "per_slot_authoring_checkpoints_and_deterministic_resume": True,
            "verified_prior_clone_cache_without_slot_reselection": True,
            "serial_peak_working_set_scratch_capacity_policy": True,
            "aggregate_readiness_publication": True,
            "green_readiness_ci_bound_private_launch_authorization": True,
            "disconnect_safe_worker_admission_and_release": True,
            "first_persisted_normal_or_terminal_observation_receipt": True,
            "crash_window_observation_without_receipt_reconciliation": True,
            "post_boundary_restart_resume_retry_recompute_forbidden": True,
            "aggregate_success_publication": True,
            "aggregate_failure_closeout_without_arm_metrics": True,
            "preboundary_zero_observation_recovery_audit_no_auto_delete": True,
        },
        "synthetic_validation": {
            "module_count": len(self_reports),
            "self_test_check_count": sum(
                report["checks_total"] for report in self_reports.values()
            ),
            "fault_test_check_count": sum(
                report["checks_total"] for report in fault_reports.values()
            ),
            "launch_release_without_observation_does_not_cross_boundary": True,
            "persisted_observation_without_receipt_crosses_boundary": True,
            "boundary_receipt_without_observation_rejected": True,
            "b25_repository_reuse_rejected": True,
            "author_checkpoint_candidate_plan_drift_rejected": True,
            "invalid_cache_reclone_preserves_candidate_order": True,
            "legacy_300_gib_scratch_floor_not_inherited_by_b3": True,
            "public_failure_contains_no_arm_quality_resource_or_rank_metrics": True,
        },
        "implementation_readiness": {
            "offline_control_source_complete": True,
            "public_synthetic_runtime_qualification_tooling_complete": True,
            "exact_linux_runtime_qualified": False,
            "private_holdout_authored_or_frozen": False,
            "public_readiness_committed_and_ci_green": False,
            "private_launch_authorization_created": False,
            "attempt_boundary_crossed": False,
            "treatment_output_exists": False,
            "tournament_result_exists": False,
            "future_tournament_execution_authorized": False,
        },
        "historical_boundary": {
            "b25_closeout_remains_failed_closed_no_result": True,
            "b25_run_restarted_resumed_scored_ranked_or_reinterpreted": False,
            "b25_private_holdout_output_or_authorization_reused": False,
        },
        "publication_limits": copy.deepcopy(b3p.B3_PUBLICATION_POLICY),
        "next_authorized_action": (
            "Start the Linux server only now: build the frozen CLI at this exact "
            "checkpoint, run the public synthetic runtime qualification, privately "
            "freeze the exact admitted profile, then commit only the aggregate report "
            "and wait for green CI before any private holdout authoring."
        ),
        "integration_digest": "",
    }
    report["integration_digest"] = _digest(report)
    return report


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 control integration report must be an object"]
    try:
        expected = build_report()
    except Exception as exc:  # noqa: BLE001 - public type-only error
        return [f"B3 control integration could not be rebuilt: {type(exc).__name__}"]
    errors: list[str] = []
    if report != expected:
        errors.append("B3 control integration report drifted")
    if report.get("integration_digest") != _digest(report):
        errors.append("B3 control integration digest mismatch")
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "b3_private_",
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "launch_authorization_digest",
        "clone_root",
    ):
        if token in raw:
            errors.append(f"private B3 token is public: {token}")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = {
        "report_valid": not validate_report(report),
        "source_digest_bound": report["control_source_bundle_digest"]
        == b3src.control_source_bundle_digest(),
        "server_is_next": "Start the Linux server only now" in report["next_authorized_action"],
        "attempt_not_crossed": report["implementation_readiness"]["attempt_boundary_crossed"]
        is False,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    report = build_report()
    drifted = copy.deepcopy(report)
    drifted["implemented_surfaces"]["crash_window_observation_without_receipt_reconciliation"] = False
    leaked = copy.deepcopy(report)
    leaked["next_authorized_action"] += " b3_private_freeze_receipt.json"
    checks = {
        "boundary_reconciliation_drift_rejected": bool(validate_report(drifted)),
        "private_token_rejected": bool(validate_report(leaked)),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--fault-test", action="store_true")
    group.add_argument("--write", action="store_true")
    group.add_argument("--check-drift", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        report = run_self_test()
    elif args.fault_test:
        report = run_fault_test()
    elif args.write:
        path = write_report()
        report = {"passed": True, "path": str(path)}
    else:
        errors = validate_report(_load_json(args.check_drift))
        report = {"passed": not errors, "errors": errors}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
