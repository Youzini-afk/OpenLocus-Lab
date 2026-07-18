#!/usr/bin/env python3
"""Aggregate-only proof for the complete offline B4 control plane."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b4_control as b4c  # noqa: E402
import product_bakeoff_b4_execution_adapter as b4adapter  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402
import product_bakeoff_b4_runtime_qualification as b4rq  # noqa: E402
import product_bakeoff_b4_source as b4src  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b4_control_integration"
    / "product_bakeoff_b4_control_integration.json"
)
PARENT_ENGINE_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b4_engine_integration"
    / "product_bakeoff_b4_engine_integration.json"
)
B4_CONTROL_REPORT_SCHEMA = "product_bakeoff_b4_control_integration.v1"
B4_CONTROL_STATUS = (
    "product_bakeoff_b4_offline_control_plane_complete_"
    "server_required_next_for_exact_linux_qualification"
)
B4_PARENT_ENGINE_DIGEST = (
    "b4engine_4428645a9aeee22032da3b6268bead4c3abc872bbcac8fd1d08fb3da155e2f0f"
)


class B4ControlIntegrationError(ValueError):
    """Fail-closed B4 control integration error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(report: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(report))
    payload.pop("integration_digest", None)
    return "b4control_" + hashlib.sha256(_canonical(payload)).hexdigest()


def _parent_engine() -> dict[str, Any]:
    value = json.loads(PARENT_ENGINE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B4ControlIntegrationError("B4 engine parent must be an object")
    if value.get("schema_version") != "product_bakeoff_b4_engine_integration.v1":
        raise B4ControlIntegrationError("B4 engine parent schema drifted")
    if value.get("status") != (
        "product_bakeoff_b4_analysis_publication_engine_complete_"
        "no_runtime_no_holdout_no_execution"
    ):
        raise B4ControlIntegrationError("B4 engine parent status drifted")
    if value.get("integration_digest") != B4_PARENT_ENGINE_DIGEST:
        raise B4ControlIntegrationError("B4 engine parent digest drifted")
    return value


def _module_reports(function_name: str) -> dict[str, dict[str, Any]]:
    modules = (b4src, b4rq, b4adapter, b4c)
    return {module.__name__: getattr(module, function_name)() for module in modules}


def build_report() -> dict[str, Any]:
    parent = _parent_engine()
    self_reports = _module_reports("run_self_test")
    fault_reports = _module_reports("run_fault_test")
    if not all(
        report["passed"] for report in (*self_reports.values(), *fault_reports.values())
    ):
        raise B4ControlIntegrationError("B4 control module tests failed")
    report: dict[str, Any] = {
        "schema_version": B4_CONTROL_REPORT_SCHEMA,
        "phase": "product_bakeoff_b4_offline_control_plane_integration",
        "status": B4_CONTROL_STATUS,
        "claim_level": "engineering_and_synthetic_fault_tests_only_no_private_input",
        "date": "2026-07-18",
        "parent_engine": {
            "integration_digest": parent["integration_digest"],
            "canonical_sha256": hashlib.sha256(_canonical(parent)).hexdigest(),
            "closed_matrix_analysis_and_publication_integrated": True,
        },
        "protocol_binding": {
            "protocol_digest": b4c.B4_PROTOCOL_DIGEST,
            "panel_count": b4p.B4_PANEL_COUNT,
            "repository_count": b4p.B4_REPOSITORY_CLUSTER_COUNT,
            "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
            "logical_record_count": b4p.B4_LOGICAL_RECORD_COUNT,
            "attempt_boundary": "first_durable_treatment_observation",
            "launch_release_alone_consumes_attempt": False,
        },
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "implemented_surfaces": {
            "three_arm_single_lifecycle_b21_engine_override": True,
            "historical_binding_restored_after_every_panel": True,
            "fresh_child_process_per_panel_preserves_run_score_import_fence": True,
            "identity_free_raw_to_closed_outcome_projection": True,
            "exclusive_atomic_durable_panel_outcome_write": True,
            "twelve_panel_shared_candidate_catalog_with_deterministic_cursors": True,
            "per_slot_authoring_checkpoints_and_deterministic_resume": True,
            "completed_panel_plan_cursor_query_and_binding_replay": True,
            "failed_candidate_clone_cleanup_without_selected_source_deletion": True,
            "five_historical_frames_and_prior_panels_excluded": True,
            "all_twelve_panels_mutually_disjoint_before_treatment": True,
            "exact_source_runtime_manifest_and_oracle_freeze": True,
            "calculated_serial_working_set_resource_gate": True,
            "arbitrary_fixed_disk_floor_removed": True,
            "aggregate_readiness_publication": True,
            "private_readiness_bytes_bound_to_exact_global_freeze": True,
            "green_readiness_ci_bound_private_launch_authorization": True,
            "disconnect_safe_worker_admission_and_launch_release": True,
            "exact_cli_path_bound_into_historical_runner_environment": True,
            "zero_observation_pre_release_admission_reset": True,
            "first_durable_raw_observation_boundary_with_crash_reconciliation": True,
            "aggregate_only_status_monitoring": True,
            "failure_progress_uses_exact_durable_observation_inventory": True,
            "aggregate_success_and_failed_closeout": True,
        },
        "synthetic_validation": {
            "module_count": len(self_reports),
            "self_test_check_count": sum(row["checks_total"] for row in self_reports.values()),
            "fault_test_check_count": sum(row["checks_total"] for row in fault_reports.values()),
            "panel_schedule_count": b4p.B4_PANEL_COUNT,
            "panel_logical_record_count": b4adapter.B4_PANEL_LOGICAL_RECORD_COUNT,
            "full_task_outcome_count": 1_728,
            "scorer_import_absent_from_raw_child_import_surface": True,
            "launch_release_without_observation_does_not_cross_boundary": True,
            "persisted_observation_without_receipt_is_reconciled": True,
            "duplicate_and_nonfinite_private_json_rejected": True,
            "post_exception_historical_runtime_bindings_restored": True,
            "released_or_observed_launch_cannot_be_reset": True,
            "private_tokens_rejected_from_public_readiness": True,
        },
        "resource_policy": {
            "minimum_free_scratch_bytes": b4rq.B4_SCRATCH_CAPACITY_POLICY[
                "minimum_free_local_scratch_bytes_at_start"
            ],
            "calculated_from_three_arm_serial_peak_working_set": True,
            "frozen_source_bytes_already_accounted_by_current_free_space": True,
            "arbitrary_fixed_disk_floor": False,
            "gpu_required": False,
        },
        "implementation_readiness": {
            "offline_control_source_complete": True,
            "raw_repository_execution_adapter_complete": True,
            "public_synthetic_runtime_qualification_tooling_complete": True,
            "exact_linux_runtime_qualified": False,
            "private_candidate_catalog_frozen": False,
            "private_holdout_authored_or_frozen": False,
            "public_readiness_committed_and_ci_green": False,
            "private_launch_authorization_created": False,
            "attempt_boundary_crossed": False,
            "treatment_output_exists": False,
            "empirical_b4_result_exists": False,
            "formal_execution_authorized": False,
        },
        "publication_limits": copy.deepcopy(b4c.B4_PUBLICATION_LIMITS),
        "next_authorized_action": (
            "Start the Linux compute server only now: build the frozen CLI at this "
            "exact checkpoint, run aggregate-only runtime qualification, commit it and "
            "wait for green CI, then author and freeze the twelve private panels."
        ),
        "integration_digest": "",
    }
    report["integration_digest"] = _digest(report)
    return report


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B4 control integration report must be an object"]
    try:
        expected = build_report()
    except Exception as exc:  # noqa: BLE001 - public type-only error
        return [f"B4 control integration could not be rebuilt: {type(exc).__name__}"]
    errors: list[str] = []
    if report != expected:
        errors.append("B4 control integration report drifted")
    if report.get("integration_digest") != _digest(report):
        errors.append("B4 control integration digest mismatch")
    errors.extend(b2p.scan_public_report(report))
    raw = json.dumps(report, sort_keys=True).casefold()
    for token in (
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "private_receipt_digest",
        "launch_authorization_digest",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "clone_root",
    ):
        if token in raw:
            errors.append("B4 control integration contains a private token")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = {
        "report_valid": not validate_report(report),
        "server_is_next": "Start the Linux compute server only now"
        in report["next_authorized_action"],
        "attempt_not_crossed": report["implementation_readiness"][
            "attempt_boundary_crossed"
        ]
        is False,
        "small_calculated_disk_gate": report["resource_policy"][
            "minimum_free_scratch_bytes"
        ]
        < 8 * 1024**3,
        "no_arbitrary_disk_floor": report["resource_policy"][
            "arbitrary_fixed_disk_floor"
        ]
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
    drifted["implemented_surfaces"]["arbitrary_fixed_disk_floor_removed"] = False
    leaked = copy.deepcopy(report)
    leaked["next_authorized_action"] += " freeze_receipt_digest"
    checks = {
        "resource_policy_drift_rejected": bool(validate_report(drifted)),
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
    if validate_report(report):
        raise B4ControlIntegrationError("refusing to write invalid B4 control report")
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
        errors = validate_report(json.loads(args.check_drift.read_text(encoding="utf-8")))
        report = {"passed": not errors, "errors": errors}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
