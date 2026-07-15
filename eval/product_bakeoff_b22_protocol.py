#!/usr/bin/env python3
"""Freeze the B2.2 strong-runner qualification and execution protocol.

B2.2 is a new confirmatory experiment after B2.1 failed closed twice at the
same timeout boundary on an underpowered local machine.  This phase does not
author a holdout and does not execute any treatment arm.  It freezes a public,
synthetic, sustained runner qualification that must pass on the same ephemeral
self-hosted runner before any future private B2.2 input is read.
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
import product_bakeoff_b21_protocol as b21  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b22_protocol"
    / "product_bakeoff_b22_protocol_report.json"
)
B21_FAILURE_REL = (
    "artifacts/product_bakeoff_b21/"
    "product_bakeoff_b21_failed_closed_aggregate.json"
)

B22_SCHEMA_VERSION = "product_bakeoff_b22_protocol.v1"
B22_REPORT_SCHEMA_VERSION = "product_bakeoff_b22_protocol_report.v1"
B22_PHASE = "product_bakeoff_b22_self_hosted_runner_qualification_protocol"
B22_STATUS = "product_bakeoff_b22_runner_protocol_ready_no_runner_no_holdout_no_result"
B22_CLAIM_LEVEL = "execution_environment_design_only"

B22_PARENT_B21_CLOSEOUT_CHECKPOINT = (
    "492ff403c1fd3b970239a7f5c43396454639a7ac"
)
B22_PARENT_B21_SPEC_DIGEST = "b21spec_3d656619189a7531"
B22_PARENT_B21_SOURCE_BUNDLE_DIGEST = (
    "b21src_76cd7f44a8c25d1d6b46493414b1753f4e72e72298d437f2bf3a8a01211d341d"
)
B22_PARENT_B21_FRAME_DIGEST = (
    "b21frame_b27001da8dcecb1552596f887fd4af93a319a95f7ce9ef60eb7f11d720d5c5d9"
)
B22_PARENT_B21_SCHEDULE_DIGEST = (
    "b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3"
)
B22_PARENT_B21_PROTOCOL_REPORT_DIGEST = (
    "b21protocol_385333bd86ba0a553229caf0797ceb2ef1acd18f05cae8f9a4edcff16ba5c2e1"
)
B22_PARENT_B21_FAILURE_AGGREGATE_SHA256 = (
    "9ff9fd904c3df21f1c137a0e436ebf550c650af315e9f2aae65bdb67205bcfd9"
)

B22_SOURCE_BUNDLE_PATHS = (
    "eval/product_bakeoff_b22_protocol.py",
    "eval/product_bakeoff_b22_runner_qualification.py",
    ".github/workflows/product-bakeoff-b22-runner.yml",
)

GIB = 1024**3
MIB = 1024**2

B22_RUNNER_CLASS = {
    "required_os": "windows",
    "required_architecture": "x64",
    "minimum_logical_cpu_count": 16,
    "minimum_total_memory_bytes": 64 * GIB,
    "minimum_available_memory_bytes_at_start": 40 * GIB,
    "minimum_free_local_scratch_bytes_at_start": 200 * GIB,
    "scratch_volume_must_be_fixed_local": True,
    "scratch_must_be_outside_checkout": True,
    "runner_must_be_dedicated_and_idle": True,
    "custom_runner_label": "openlocus-b22-private",
    "ephemeral_one_job_runner_required": True,
    "same_runner_for_qualification_and_future_tournament": True,
}

B22_IO_QUALIFICATION = {
    "file_bytes": 512 * MIB,
    "minimum_sequential_write_bytes_per_second": 150 * MIB,
    "minimum_sequential_read_bytes_per_second": 150 * MIB,
    "fsync_before_write_timing_stops": True,
    "content_hash_verified_after_read": True,
}

B22_STRESS_QUALIFICATION = {
    "source_kind": "deterministic_public_synthetic_typescript",
    "source_file_count": 10_000,
    "source_visible_bytes": 72 * MIB,
    "size_band": "xlarge",
    "consecutive_group_count": 3,
    "tasks_per_group": 4,
    "arm_count": len(b2.B2_ADAPTER_IDS),
    "logical_records_per_group": 30,
    "logical_record_count": 90,
    "same_split_plot_copy_index_query_lifecycle_as_tournament": True,
    "same_frozen_arm_rotation_as_tournament": True,
    "same_phase_timeout_seconds": 30,
    "all_normal_records_must_be_accepted": True,
    "timeout_count_must_equal_zero": True,
    "provider_network_call_count_must_equal_zero": True,
    "terminal_support_count_must_equal_zero": True,
    "maximum_wall_clock_seconds": 45 * 60,
    "qualification_runs_before_private_input_read": True,
}

B22_EXECUTION_ENVIRONMENT = {
    "public_repository_self_hosted_risk_acknowledged": True,
    "workflow_trigger": "manual_workflow_dispatch_only",
    "pull_request_or_push_may_not_start_private_job": True,
    "protected_environment": "b22-private-execution",
    "required_human_approval_before_self_hosted_job": True,
    "runner_registration": "ephemeral",
    "runner_destroyed_or_wiped_after_job": True,
    "checkout_credentials_persisted": False,
    "workflow_token_permissions": "contents_read_only",
    "third_party_actions_pinned_to_full_commit": True,
    "actions_cache_for_private_job_forbidden": True,
    "private_inputs_preprovisioned_outside_checkout": True,
    "private_paths_or_exact_hardware_profile_in_logs_forbidden": True,
    "only_validated_aggregate_artifact_may_leave_runner": True,
    "runner_logs_forwarded_to_restricted_external_storage": True,
}

B22_EXPERIMENTAL_DESIGN = {
    "experimental_unit": "logical_task",
    "independent_unit_count": 48,
    "repository_is_nested_cluster": True,
    "cache_and_repetition_are_technical_repeated_measures": True,
    "runner_machine_is_fixed_nuisance_block": True,
    "all_six_treatments_run_on_one_machine": True,
    "multi_runner_group_or_arm_sharding_forbidden": True,
    "randomized_complete_task_blocks_inherited": True,
    "repository_split_plot_lifecycle_inherited": True,
    "interim_quality_looks": 0,
    "single_final_analysis_only": True,
}

B22_HOLDOUT_RULES = {
    "future_repository_count": 12,
    "future_logical_task_count": 48,
    "all_repository_slugs_absent_from_b2_and_b21_frames": True,
    "all_qualification_and_real_preflight_repositories_excluded": True,
    "all_task_query_and_oracle_rows_new": True,
    "b2_or_b21_empirical_cells_must_not_be_reused": True,
    "future_holdout_may_be_authored_only_after_runner_qualification_passes": True,
}

B22_RETRY_POLICY = {
    "runner_qualification_may_be_repeated_before_private_input_read": True,
    "runner_qualification_results_are_not_treatment_outputs": True,
    "future_tournament_attempt_count": 1,
    "complete_restart_after_any_future_arm_output_allowed": False,
    "selective_cell_retry_allowed": False,
    "missing_cell_imputation_allowed": False,
    "infrastructure_failure_closes_future_tournament_without_result": True,
}

B22_PUBLICATION_POLICY = {
    **dict(b21.B21_PUBLICATION_POLICY),
    "exact_runner_hardware_profile_public": False,
    "runner_name_or_machine_identifier_public": False,
    "private_runner_scratch_location_public": False,
    "synthetic_qualification_aggregate_public": True,
    "qualification_failure_code_public": True,
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any, *, length: int | None = None) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return prefix + (digest[:length] if length is not None else digest)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_parent_b21_closeout(repo_root: Path | None = None) -> list[str]:
    root = (repo_root or REPO).resolve()
    path = root / B21_FAILURE_REL
    if path.is_symlink() or not path.is_file():
        return ["parent B2.1 failure aggregate missing or unsafe"]
    if file_sha256(path) != B22_PARENT_B21_FAILURE_AGGREGATE_SHA256:
        return ["parent B2.1 failure aggregate bytes drifted"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - type-only fail-closed message
        return [f"parent B2.1 failure aggregate unreadable: {type(exc).__name__}"]
    checks = {
        "status": "product_bakeoff_b21_execution_failed_closed_no_result",
        "claim_level": (
            "repeated_infrastructure_invalid_incomplete_matrix_no_tournament_result"
        ),
    }
    errors = [
        f"parent B2.1 {key} drifted"
        for key, expected in checks.items()
        if value.get(key) != expected
    ]
    execution = value.get("execution") or {}
    if execution.get("tournament_scoring_executed") is not False:
        errors.append("parent B2.1 scoring state drifted")
    if execution.get("public_tournament_result_exists") is not False:
        errors.append("parent B2.1 result state drifted")
    if execution.get("complete_restart_attempt_count") != 2:
        errors.append("parent B2.1 restart count drifted")
    return sorted(set(errors))


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    for rel in B22_SOURCE_BUNDLE_PATHS:
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"missing or unsafe B2.2 source file: {rel}")
        resolved = path.resolve()
        resolved.relative_to(root)
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "path": rel,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def b22_source_bundle_digest(repo_root: Path | None = None) -> str:
    return _prefixed_digest(
        "b22src_",
        {
            "parent_b21_source_bundle_digest": B22_PARENT_B21_SOURCE_BUNDLE_DIGEST,
            "overlay_source_rows": _normalized_source_rows(repo_root),
        },
    )


def b22_spec_payload() -> dict[str, Any]:
    return {
        "schema_version": B22_SCHEMA_VERSION,
        "parent_b21": {
            "closeout_checkpoint": B22_PARENT_B21_CLOSEOUT_CHECKPOINT,
            "spec_digest": B22_PARENT_B21_SPEC_DIGEST,
            "source_bundle_digest": B22_PARENT_B21_SOURCE_BUNDLE_DIGEST,
            "holdout_frame_digest": B22_PARENT_B21_FRAME_DIGEST,
            "execution_schedule_digest": B22_PARENT_B21_SCHEDULE_DIGEST,
            "protocol_report_digest": B22_PARENT_B21_PROTOCOL_REPORT_DIGEST,
            "failure_aggregate_sha256": B22_PARENT_B21_FAILURE_AGGREGATE_SHA256,
        },
        "runner_class": copy.deepcopy(B22_RUNNER_CLASS),
        "io_qualification": copy.deepcopy(B22_IO_QUALIFICATION),
        "stress_qualification": copy.deepcopy(B22_STRESS_QUALIFICATION),
        "execution_environment": copy.deepcopy(B22_EXECUTION_ENVIRONMENT),
        "experimental_design": copy.deepcopy(B22_EXPERIMENTAL_DESIGN),
        "holdout_rules": copy.deepcopy(B22_HOLDOUT_RULES),
        "retry_policy": copy.deepcopy(B22_RETRY_POLICY),
        "publication_policy": copy.deepcopy(B22_PUBLICATION_POLICY),
    }


def b22_spec_digest() -> str:
    return _prefixed_digest("b22spec_", b22_spec_payload(), length=16)


def _build_report_without_digest() -> dict[str, Any]:
    return {
        "schema_version": B22_REPORT_SCHEMA_VERSION,
        "phase": B22_PHASE,
        "status": B22_STATUS,
        "claim_level": B22_CLAIM_LEVEL,
        "date": "2026-07-15",
        "parent_b21_lock": b22_spec_payload()["parent_b21"],
        "experimental_design": copy.deepcopy(B22_EXPERIMENTAL_DESIGN),
        "runner_class": copy.deepcopy(B22_RUNNER_CLASS),
        "io_qualification": copy.deepcopy(B22_IO_QUALIFICATION),
        "stress_qualification": copy.deepcopy(B22_STRESS_QUALIFICATION),
        "execution_environment": copy.deepcopy(B22_EXECUTION_ENVIRONMENT),
        "future_holdout": copy.deepcopy(B22_HOLDOUT_RULES),
        "retry_policy": copy.deepcopy(B22_RETRY_POLICY),
        "privacy_publication": copy.deepcopy(B22_PUBLICATION_POLICY),
        "source_locks": {
            "b22_spec_digest": b22_spec_digest(),
            "b22_source_bundle_digest": b22_source_bundle_digest(),
            "line_endings_normalized_for_cross_platform_digest": True,
        },
        "implementation_readiness": {
            "runner_profile_gate_implemented": True,
            "io_gate_implemented": True,
            "synthetic_three_group_stress_gate_implemented": True,
            "public_aggregate_validator_implemented": True,
            "manual_self_hosted_workflow_implemented": True,
            "actual_strong_runner_registered": False,
            "runner_qualification_executed": False,
            "future_private_holdout_materialized": False,
            "future_tournament_execution_authorized": False,
        },
        "next_authorized_action": (
            "provision one dedicated ephemeral Windows x64 self-hosted runner, "
            "configure protected-environment approval and restricted log retention, "
            "then run only the public synthetic runner qualification; do not author "
            "or read a B2.2 private holdout until that qualification is green"
        ),
    }


def build_report() -> dict[str, Any]:
    report = _build_report_without_digest()
    report["protocol_digest"] = _prefixed_digest("b22protocol_", report)
    return report


def _diff(expected: Any, actual: Any, path: str = "report") -> list[str]:
    if type(expected) is not type(actual):
        return [f"{path}: type drift"]
    if isinstance(expected, dict):
        errors = [f"{path}: key drift"] if set(expected) != set(actual) else []
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
        return ["report must be an object"]
    errors = list(b2.scan_public_report(report))
    errors.extend(validate_parent_b21_closeout())
    errors.extend(_diff(build_report(), report))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = [
        ("parent_b21_closeout_valid", not validate_parent_b21_closeout()),
        ("spec_digest", b22_spec_digest().startswith("b22spec_")),
        ("source_digest", b22_source_bundle_digest().startswith("b22src_")),
        ("report_valid", not validate_report(report)),
        ("logical_n_48", B22_EXPERIMENTAL_DESIGN["independent_unit_count"] == 48),
        ("machine_fixed_block", B22_EXPERIMENTAL_DESIGN["runner_machine_is_fixed_nuisance_block"]),
        ("multi_runner_sharding_forbidden", B22_EXPERIMENTAL_DESIGN["multi_runner_group_or_arm_sharding_forbidden"]),
        ("stress_three_groups", B22_STRESS_QUALIFICATION["consecutive_group_count"] == 3),
        ("stress_records_90", B22_STRESS_QUALIFICATION["logical_record_count"] == 90),
        ("qualification_before_private_read", B22_STRESS_QUALIFICATION["qualification_runs_before_private_input_read"]),
        ("ephemeral_runner", B22_RUNNER_CLASS["ephemeral_one_job_runner_required"]),
        ("single_future_attempt", B22_RETRY_POLICY["future_tournament_attempt_count"] == 1),
        ("no_future_restart", not B22_RETRY_POLICY["complete_restart_after_any_future_arm_output_allowed"]),
        ("no_holdout_yet", not report["implementation_readiness"]["future_private_holdout_materialized"]),
        ("no_execution_authority", not report["implementation_readiness"]["future_tournament_execution_authorized"]),
    ]
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {
        "status": "passed",
        "checks_passed": len(checks),
        "checks_total": len(checks),
    }


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[tuple[str, bool]] = []

    def rejected(name: str, mutator: Any) -> None:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append((name, bool(validate_report(value))))

    rejected("unknown_key", lambda value: value.__setitem__("extra", True))
    rejected("status_drift", lambda value: value.__setitem__("status", "drift"))
    rejected("parent_result_drift", lambda value: value["parent_b21_lock"].__setitem__("failure_aggregate_sha256", "0" * 64))
    rejected("weak_cpu", lambda value: value["runner_class"].__setitem__("minimum_logical_cpu_count", 1))
    rejected("weak_memory", lambda value: value["runner_class"].__setitem__("minimum_total_memory_bytes", GIB))
    rejected("private_before_qualification", lambda value: value["stress_qualification"].__setitem__("qualification_runs_before_private_input_read", False))
    rejected("sharding_enabled", lambda value: value["experimental_design"].__setitem__("multi_runner_group_or_arm_sharding_forbidden", False))
    rejected("restart_enabled", lambda value: value["retry_policy"].__setitem__("complete_restart_after_any_future_arm_output_allowed", True))
    rejected("interim_look", lambda value: value["experimental_design"].__setitem__("interim_quality_looks", 1))
    rejected("private_profile_public", lambda value: value["privacy_publication"].__setitem__("exact_runner_hardware_profile_public", True))
    rejected("execution_overauthorized", lambda value: value["implementation_readiness"].__setitem__("future_tournament_execution_authorized", True))
    rejected("digest_drift", lambda value: value.__setitem__("protocol_digest", "b22protocol_" + "0" * 64))
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit("fault-test failed: " + ", ".join(failed))
    return {
        "status": "passed",
        "faults_rejected": len(checks),
        "faults_total": len(checks),
    }


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise SystemExit("refusing to write invalid B2.2 report: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.2 strong-runner protocol")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--write-report", action="store_true")
    mode.add_argument("--validate-report", type=Path)
    mode.add_argument("--check-drift", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    if args.fault_test:
        print(json.dumps(run_fault_test(), sort_keys=True))
        return 0
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
    "B22_RUNNER_CLASS",
    "B22_IO_QUALIFICATION",
    "B22_STRESS_QUALIFICATION",
    "B22_EXECUTION_ENVIRONMENT",
    "B22_EXPERIMENTAL_DESIGN",
    "B22_HOLDOUT_RULES",
    "B22_RETRY_POLICY",
    "B22_PUBLICATION_POLICY",
    "b22_spec_digest",
    "b22_source_bundle_digest",
    "build_report",
    "validate_report",
]
