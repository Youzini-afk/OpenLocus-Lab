#!/usr/bin/env python3
"""Freeze the B2.3 constrained-Linux long-run execution protocol.

B2.3 preserves the unexecuted B2.2 strong-runner checkpoint and adapts only the
execution environment to a dedicated, quota-limited Linux container.  This
phase does not author a holdout, read private B2.3 input, or execute a treatment
arm.  A public synthetic qualification must pass before any future private
input is materialized.
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
    / "product_bakeoff_b23_protocol"
    / "product_bakeoff_b23_protocol_report.json"
)
B22_REPORT_REL = (
    "artifacts/product_bakeoff_b22_protocol/"
    "product_bakeoff_b22_protocol_report.json"
)

B23_SCHEMA_VERSION = "product_bakeoff_b23_protocol.v1"
B23_REPORT_SCHEMA_VERSION = "product_bakeoff_b23_protocol_report.v1"
B23_PHASE = "product_bakeoff_b23_constrained_linux_longrun_protocol"
B23_STATUS = (
    "product_bakeoff_b23_linux_longrun_protocol_ready_"
    "no_runner_qualification_no_holdout_no_result"
)
B23_CLAIM_LEVEL = "execution_environment_design_only"

B23_PARENT_B22_CHECKPOINT = (
    "9acfc997c3971f7b6501b05311044887e43c4736"
)
B23_PARENT_B22_SPEC_DIGEST = "b22spec_adf15e2598e9f7c4"
B23_PARENT_B22_SOURCE_BUNDLE_DIGEST = (
    "b22src_05d40bb6c20414aa8ec0972d087e53750d0af635f0a57857ceddd864b4b1ea47"
)
B23_PARENT_B22_PROTOCOL_REPORT_DIGEST = (
    "b22protocol_a84b309cf327a81325eb38451682beb8077cd93e2e9a49b3befc65fc4219e425"
)
B23_PARENT_B22_REPORT_NORMALIZED_SHA256 = (
    "15daa2914518e715c49f3686537ee135040f8361690a6f4983b5763e3e1695c1"
)

B23_SOURCE_BUNDLE_PATHS = (
    "eval/product_bakeoff_b23_protocol.py",
    "eval/product_bakeoff_b23_runner_qualification.py",
    "scripts/product_bakeoff_b23_linux_bootstrap.sh",
    ".github/workflows/product-bakeoff-b23-linux.yml",
)

GIB = 1024**3
MIB = 1024**2

B23_RUNNER_CLASS = {
    "required_os": "linux",
    "required_architecture": "x64",
    "minimum_effective_cpu_quota_count": 8,
    "minimum_cgroup_memory_limit_bytes": 32 * GIB,
    "minimum_cgroup_available_memory_bytes_at_start": 24 * GIB,
    "minimum_free_local_scratch_bytes_at_start": 300 * GIB,
    "finite_cgroup_cpu_and_memory_limits_required": True,
    "active_swap_must_equal_zero": True,
    "maximum_idle_cgroup_cpu_millicores": 250,
    "minimum_open_file_soft_limit": 65_535,
    "minimum_python_major": 3,
    "minimum_python_minor": 10,
    "required_rustc_version_prefix": "rustc 1.95.0 ",
    "required_cargo_version_prefix": "cargo 1.95.0 ",
    "scratch_volume_must_be_nonrotational_local_block_storage": True,
    "scratch_must_be_outside_checkout": True,
    "runner_must_be_dedicated_and_idle": True,
    "profile_revalidated_after_sustained_qualification": True,
    "stable_profile_fields_must_not_change_during_qualification": True,
    "custom_runner_label": "openlocus-b23-private",
    "qualification_runner_registration_must_be_ephemeral_one_job": True,
    "same_machine_instance_for_qualification_and_future_tournament": True,
    "provider_physical_host_exclusivity_not_claimed": True,
}

B23_IO_QUALIFICATION = {
    "file_bytes": 512 * MIB,
    "minimum_sequential_write_bytes_per_second": 150 * MIB,
    "minimum_sequential_read_bytes_per_second": 150 * MIB,
    "fsync_before_write_timing_stops": True,
    "content_hash_verified_after_read": True,
}

B23_STRESS_QUALIFICATION = {
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
    "same_phase_timeout_seconds": 600,
    "all_normal_records_must_be_accepted": True,
    "timeout_count_must_equal_zero": True,
    "provider_network_call_count_must_equal_zero": True,
    "terminal_support_count_must_equal_zero": True,
    "maximum_wall_clock_seconds": 6 * 60 * 60,
    "qualification_runs_before_private_input_read": True,
    "complete_six_arm_rotation_within_each_task_block": True,
}

B23_EXECUTION_ENVIRONMENT = {
    "public_repository_self_hosted_risk_acknowledged": True,
    "workflow_trigger": "manual_workflow_dispatch_only",
    "pull_request_or_push_may_not_start_private_job": True,
    "protected_environment": "b23-private-execution",
    "required_human_approval_before_self_hosted_job": True,
    "qualification_runner_registration": "ephemeral_one_job",
    "qualification_runner_registration_removed_after_job": True,
    "machine_stays_offline_from_github_between_qualification_and_tournament": True,
    "machine_destroyed_or_wiped_after_final_b23_use": True,
    "checkout_credentials_persisted": False,
    "workflow_token_permissions": "contents_read_only",
    "third_party_actions_pinned_to_full_commit": True,
    "actions_cache_for_private_job_forbidden": True,
    "private_inputs_preprovisioned_outside_checkout": True,
    "private_paths_or_exact_hardware_profile_in_logs_forbidden": True,
    "only_validated_aggregate_artifact_may_leave_runner": True,
    "runner_logs_forwarded_to_restricted_external_storage": True,
    "future_tournament_runs_as_standalone_process_not_github_actions": True,
}

B23_EXPERIMENTAL_DESIGN = {
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
    "provider_host_contention_is_uncontrolled_nuisance": True,
    "complete_arm_rotation_balances_time_drift_within_task_block": True,
    "performance_claim_scope": "within_this_qualified_machine_only",
    "cross_machine_performance_generalization_forbidden": True,
}

B23_HOLDOUT_RULES = {
    "future_repository_count": 12,
    "future_logical_task_count": 48,
    "all_repository_slugs_absent_from_b2_and_b21_frames": True,
    "all_qualification_and_real_preflight_repositories_excluded": True,
    "all_task_query_and_oracle_rows_new": True,
    "b2_or_b21_empirical_cells_must_not_be_reused": True,
    "future_holdout_may_be_authored_only_after_runner_qualification_passes": True,
    "all_b22_and_b23_qualification_sources_excluded": True,
}

B23_RETRY_POLICY = {
    "runner_qualification_may_be_repeated_before_private_input_read": True,
    "runner_qualification_results_are_not_treatment_outputs": True,
    "future_tournament_attempt_count": 1,
    "complete_restart_after_any_future_arm_output_allowed": False,
    "selective_cell_retry_allowed": False,
    "missing_cell_imputation_allowed": False,
    "infrastructure_failure_closes_future_tournament_without_result": True,
    "resume_after_future_process_or_machine_restart_allowed": False,
}

B23_LONGRUN_EXECUTION = {
    "launcher": "standalone_single_process_under_screen_or_nohup",
    "github_actions_job_used_for_future_tournament": False,
    "minimum_open_file_soft_limit": 65_535,
    "checkout_build_and_scratch_live_on_data_volume": True,
    "ssh_disconnect_must_not_terminate_process": True,
    "private_health_heartbeat_contains_no_outcome_or_arm_metric": True,
    "intermediate_public_artifacts_forbidden": True,
    "completed_cells_may_not_be_recomputed": True,
    "process_or_machine_restart_after_arm_output_closes_without_result": True,
}

B23_PUBLICATION_POLICY = {
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


def normalized_text_file_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def validate_parent_b22_checkpoint(repo_root: Path | None = None) -> list[str]:
    root = (repo_root or REPO).resolve()
    path = root / B22_REPORT_REL
    if path.is_symlink() or not path.is_file():
        return ["parent B2.2 protocol report missing or unsafe"]
    if (
        normalized_text_file_sha256(path)
        != B23_PARENT_B22_REPORT_NORMALIZED_SHA256
    ):
        return ["parent B2.2 protocol report bytes drifted"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - type-only fail-closed message
        return [f"parent B2.2 protocol report unreadable: {type(exc).__name__}"]
    checks = {
        "status": "product_bakeoff_b22_runner_protocol_ready_no_runner_no_holdout_no_result",
        "claim_level": "execution_environment_design_only",
        "protocol_digest": B23_PARENT_B22_PROTOCOL_REPORT_DIGEST,
    }
    errors = [
        f"parent B2.2 {key} drifted"
        for key, expected in checks.items()
        if value.get(key) != expected
    ]
    locks = value.get("source_locks") or {}
    if locks.get("b22_spec_digest") != B23_PARENT_B22_SPEC_DIGEST:
        errors.append("parent B2.2 spec digest drifted")
    if locks.get("b22_source_bundle_digest") != B23_PARENT_B22_SOURCE_BUNDLE_DIGEST:
        errors.append("parent B2.2 source digest drifted")
    readiness = value.get("implementation_readiness") or {}
    if readiness.get("runner_qualification_executed") is not False:
        errors.append("parent B2.2 qualification state drifted")
    if readiness.get("future_private_holdout_materialized") is not False:
        errors.append("parent B2.2 holdout state drifted")
    return sorted(set(errors))


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    for rel in B23_SOURCE_BUNDLE_PATHS:
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"missing or unsafe B2.3 source file: {rel}")
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


def b23_source_bundle_digest(repo_root: Path | None = None) -> str:
    return _prefixed_digest(
        "b23src_",
        {
            "parent_b22_source_bundle_digest": B23_PARENT_B22_SOURCE_BUNDLE_DIGEST,
            "overlay_source_rows": _normalized_source_rows(repo_root),
        },
    )


def b23_spec_payload() -> dict[str, Any]:
    return {
        "schema_version": B23_SCHEMA_VERSION,
        "parent_b22": {
            "checkpoint": B23_PARENT_B22_CHECKPOINT,
            "spec_digest": B23_PARENT_B22_SPEC_DIGEST,
            "source_bundle_digest": B23_PARENT_B22_SOURCE_BUNDLE_DIGEST,
            "protocol_report_digest": B23_PARENT_B22_PROTOCOL_REPORT_DIGEST,
            "protocol_report_normalized_sha256": (
                B23_PARENT_B22_REPORT_NORMALIZED_SHA256
            ),
        },
        "runner_class": copy.deepcopy(B23_RUNNER_CLASS),
        "io_qualification": copy.deepcopy(B23_IO_QUALIFICATION),
        "stress_qualification": copy.deepcopy(B23_STRESS_QUALIFICATION),
        "execution_environment": copy.deepcopy(B23_EXECUTION_ENVIRONMENT),
        "experimental_design": copy.deepcopy(B23_EXPERIMENTAL_DESIGN),
        "holdout_rules": copy.deepcopy(B23_HOLDOUT_RULES),
        "retry_policy": copy.deepcopy(B23_RETRY_POLICY),
        "longrun_execution": copy.deepcopy(B23_LONGRUN_EXECUTION),
        "publication_policy": copy.deepcopy(B23_PUBLICATION_POLICY),
    }


def b23_spec_digest() -> str:
    return _prefixed_digest("b23spec_", b23_spec_payload(), length=16)


def _build_report_without_digest() -> dict[str, Any]:
    return {
        "schema_version": B23_REPORT_SCHEMA_VERSION,
        "phase": B23_PHASE,
        "status": B23_STATUS,
        "claim_level": B23_CLAIM_LEVEL,
        "date": "2026-07-15",
        "parent_b22_lock": b23_spec_payload()["parent_b22"],
        "experimental_design": copy.deepcopy(B23_EXPERIMENTAL_DESIGN),
        "runner_class": copy.deepcopy(B23_RUNNER_CLASS),
        "io_qualification": copy.deepcopy(B23_IO_QUALIFICATION),
        "stress_qualification": copy.deepcopy(B23_STRESS_QUALIFICATION),
        "execution_environment": copy.deepcopy(B23_EXECUTION_ENVIRONMENT),
        "future_holdout": copy.deepcopy(B23_HOLDOUT_RULES),
        "retry_policy": copy.deepcopy(B23_RETRY_POLICY),
        "longrun_execution": copy.deepcopy(B23_LONGRUN_EXECUTION),
        "privacy_publication": copy.deepcopy(B23_PUBLICATION_POLICY),
        "source_locks": {
            "b23_spec_digest": b23_spec_digest(),
            "b23_source_bundle_digest": b23_source_bundle_digest(),
            "line_endings_normalized_for_cross_platform_digest": True,
        },
        "implementation_readiness": {
            "runner_profile_gate_implemented": True,
            "io_gate_implemented": True,
            "synthetic_three_group_stress_gate_implemented": True,
            "public_aggregate_validator_implemented": True,
            "linux_cgroup_v1_and_v2_detection_implemented": True,
            "standalone_longrun_contract_implemented": True,
            "manual_self_hosted_qualification_workflow_implemented": True,
            "actual_constrained_linux_runner_registered": False,
            "runner_qualification_executed": False,
            "future_private_holdout_materialized": False,
            "future_tournament_execution_authorized": False,
        },
        "next_authorized_action": (
            "start the inspected dedicated quota-limited Linux container, bootstrap "
            "the pinned Rust toolchain on its data volume, configure one ephemeral "
            "qualification runner registration, then run only the public synthetic "
            "qualification; do not author "
            "or read a B2.3 private holdout until that qualification is green"
        ),
    }


def build_report() -> dict[str, Any]:
    report = _build_report_without_digest()
    report["protocol_digest"] = _prefixed_digest("b23protocol_", report)
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
    errors.extend(validate_parent_b22_checkpoint())
    errors.extend(_diff(build_report(), report))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = [
        ("parent_b22_checkpoint_valid", not validate_parent_b22_checkpoint()),
        ("spec_digest", b23_spec_digest().startswith("b23spec_")),
        ("source_digest", b23_source_bundle_digest().startswith("b23src_")),
        ("report_valid", not validate_report(report)),
        ("logical_n_48", B23_EXPERIMENTAL_DESIGN["independent_unit_count"] == 48),
        ("machine_fixed_block", B23_EXPERIMENTAL_DESIGN["runner_machine_is_fixed_nuisance_block"]),
        ("multi_runner_sharding_forbidden", B23_EXPERIMENTAL_DESIGN["multi_runner_group_or_arm_sharding_forbidden"]),
        ("stress_three_groups", B23_STRESS_QUALIFICATION["consecutive_group_count"] == 3),
        ("stress_records_90", B23_STRESS_QUALIFICATION["logical_record_count"] == 90),
        ("qualification_before_private_read", B23_STRESS_QUALIFICATION["qualification_runs_before_private_input_read"]),
        ("linux_runner", B23_RUNNER_CLASS["required_os"] == "linux"),
        ("finite_cgroup_limits", B23_RUNNER_CLASS["finite_cgroup_cpu_and_memory_limits_required"]),
        (
            "profile_revalidated_after_stress",
            B23_RUNNER_CLASS["profile_revalidated_after_sustained_qualification"],
        ),
        (
            "stable_profile_drift_forbidden",
            B23_RUNNER_CLASS[
                "stable_profile_fields_must_not_change_during_qualification"
            ],
        ),
        ("long_phase_timeout", B23_STRESS_QUALIFICATION["same_phase_timeout_seconds"] == 600),
        ("standalone_future_run", not B23_LONGRUN_EXECUTION["github_actions_job_used_for_future_tournament"]),
        ("single_future_attempt", B23_RETRY_POLICY["future_tournament_attempt_count"] == 1),
        ("no_future_restart", not B23_RETRY_POLICY["complete_restart_after_any_future_arm_output_allowed"]),
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
    rejected("parent_result_drift", lambda value: value["parent_b22_lock"].__setitem__("protocol_report_normalized_sha256", "0" * 64))
    rejected("weak_cpu", lambda value: value["runner_class"].__setitem__("minimum_effective_cpu_quota_count", 1))
    rejected("weak_memory", lambda value: value["runner_class"].__setitem__("minimum_cgroup_memory_limit_bytes", GIB))
    rejected("private_before_qualification", lambda value: value["stress_qualification"].__setitem__("qualification_runs_before_private_input_read", False))
    rejected("sharding_enabled", lambda value: value["experimental_design"].__setitem__("multi_runner_group_or_arm_sharding_forbidden", False))
    rejected("restart_enabled", lambda value: value["retry_policy"].__setitem__("complete_restart_after_any_future_arm_output_allowed", True))
    rejected("interim_look", lambda value: value["experimental_design"].__setitem__("interim_quality_looks", 1))
    rejected("private_profile_public", lambda value: value["privacy_publication"].__setitem__("exact_runner_hardware_profile_public", True))
    rejected("execution_overauthorized", lambda value: value["implementation_readiness"].__setitem__("future_tournament_execution_authorized", True))
    rejected("digest_drift", lambda value: value.__setitem__("protocol_digest", "b23protocol_" + "0" * 64))
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
        raise SystemExit("refusing to write invalid B2.3 report: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.3 constrained-Linux long-run protocol")
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
    "B23_RUNNER_CLASS",
    "B23_IO_QUALIFICATION",
    "B23_STRESS_QUALIFICATION",
    "B23_EXECUTION_ENVIRONMENT",
    "B23_EXPERIMENTAL_DESIGN",
    "B23_HOLDOUT_RULES",
    "B23_RETRY_POLICY",
    "B23_LONGRUN_EXECUTION",
    "B23_PUBLICATION_POLICY",
    "b23_spec_digest",
    "b23_source_bundle_digest",
    "build_report",
    "validate_report",
]
