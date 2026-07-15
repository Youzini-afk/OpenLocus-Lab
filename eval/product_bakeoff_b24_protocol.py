#!/usr/bin/env python3
"""Freeze the B2.4 fresh-holdout and qualified long-run protocol.

B2.4 is a new confirmatory tournament envelope.  It inherits the B2.1
own-parent execution/scoring semantics, excludes both historical empirical
frames, binds execution to the passed B2.3 Linux runner qualification, and
bridges the old short command timeout to the B2.3 long-run limit.

This module is public design code only.  It does not accept a private input,
author a task, run an adapter, score an arm, or authorize tournament execution.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2  # noqa: E402
import product_bakeoff_b21_protocol as b21  # noqa: E402
import product_bakeoff_b23_protocol as b23  # noqa: E402
import product_bakeoff_b23_runner_qualification as b23q  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b24_protocol"
    / "product_bakeoff_b24_protocol_report.json"
)
B21_FAILURE_REL = (
    "artifacts/product_bakeoff_b21/"
    "product_bakeoff_b21_failed_closed_aggregate.json"
)
B23_QUALIFICATION_REL = (
    "artifacts/product_bakeoff_b23_runner_qualification/"
    "product_bakeoff_b23_runner_qualification.json"
)

B24_SCHEMA_VERSION = "product_bakeoff_b24_protocol.v1"
B24_REPORT_SCHEMA_VERSION = "product_bakeoff_b24_protocol_report.v1"
B24_PHASE = "product_bakeoff_b24_fresh_holdout_qualified_linux_tournament_protocol"
B24_STATUS = (
    "product_bakeoff_b24_protocol_ready_"
    "no_private_holdout_no_tournament_no_result"
)
B24_CLAIM_LEVEL = "holdout_authoring_and_execution_envelope_design_only"

B24_PARENT_B21_FAILURE_SHA256 = (
    "9ff9fd904c3df21f1c137a0e436ebf550c650af315e9f2aae65bdb67205bcfd9"
)
B24_PARENT_B21_FAILURE_DIGEST = (
    "b21failure_6feabc0f3ffa4efc396a5195417f15ff4e21527f753114f1854951ddc855b68c"
)
B24_PARENT_B21_SPEC_DIGEST = "b21spec_3d656619189a7531"
B24_PARENT_B21_SOURCE_BUNDLE_DIGEST = (
    "b21src_76cd7f44a8c25d1d6b46493414b1753f4e72e72298d437f2bf3a8a01211d341d"
)
B24_PARENT_B21_FRAME_DIGEST = (
    "b21frame_b27001da8dcecb1552596f887fd4af93a319a95f7ce9ef60eb7f11d720d5c5d9"
)
B24_PARENT_B21_SCHEDULE_DIGEST = (
    "b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3"
)

B24_PARENT_B23_QUALIFICATION_SOURCE_CHECKPOINT = (
    "13fbf5f3f4def0bb7663aa2895e72e2d7682e3da"
)
B24_PARENT_B23_QUALIFICATION_PUBLICATION_CHECKPOINT = (
    "b21acaf03b7faa19891c45e958fdc184ce29db9b"
)
B24_PARENT_B23_QUALIFICATION_SHA256 = (
    "b22229479ed3744321a4a6b09e454d06dc873f08d366069c738e6109c72a7e95"
)
B24_PARENT_B23_QUALIFICATION_DIGEST = (
    "b23qual_0ba839c5e02c96a7c8c879532ad354f19a6405cd6dd3f9885baa2ea3c1a499a1"
)
B24_PARENT_B23_SPEC_DIGEST = "b23spec_b9281d2e323f8103"
B24_PARENT_B23_SOURCE_BUNDLE_DIGEST = (
    "b23src_c674402a50183c6d3bb6eec0d855900dbfe7822929eb9656965077f9336057eb"
)

B24_SOURCE_BUNDLE_PATHS = (
    "eval/product_bakeoff_b24_protocol.py",
    "eval/product_bakeoff_b24_corpus.py",
    "eval/product_bakeoff_b24_runner.py",
    "eval/product_bakeoff_b24_scorer.py",
    "eval/product_bakeoff_b24_readiness.py",
    "eval/product_bakeoff_b24_cli.py",
    "scripts/product_bakeoff_b24_linux_longrun.sh",
    ".github/workflows/product-bakeoff-b24-holdout.yml",
)

B24_REQUEST_TIMEOUT_SECONDS = 600.0
B24_ADAPTER_COMMAND_TIMEOUT_SECONDS = 570.0

B24_HOLDOUT_RULES = {
    "repository_snapshot_count": b2.B2_REPO_SLOT_COUNT,
    "logical_task_count": b2.B2_TASK_COUNT,
    "language_count": len(b2.B2_LANGUAGES),
    "size_band_count": len(b2.B2_SIZE_BANDS),
    "task_roles_per_repository": len(b2.B2_TASK_ROLES),
    "all_repository_slugs_absent_from_b2_frame": True,
    "all_repository_slugs_absent_from_b21_frame": True,
    "all_repository_identity_commit_pairs_absent_from_b2_frame": True,
    "all_repository_identity_commit_pairs_absent_from_b21_frame": True,
    "all_real_preflight_and_qualification_repositories_excluded": True,
    "all_b22_and_b23_synthetic_qualification_sources_excluded": True,
    "all_task_query_and_oracle_rows_new": True,
    "b2_and_b21_empirical_cells_must_not_be_reused": True,
    "b2_and_b21_private_manifests_must_not_be_reused_as_new_inputs": True,
    "b2_task_authoring_rules_inherited_without_output_driven_change": True,
    "candidate_plan_slot_count": b2.B2_REPO_SLOT_COUNT,
    "minimum_candidates_per_slot": 2,
    "candidate_order_and_license_expectations_frozen_before_authoring": True,
    "candidate_failover_must_finish_before_any_treatment_output": True,
    "final_holdout_tasks_not_executed_before_runtime_freeze": True,
    "private_holdout_digests_and_identities_never_public": True,
}

B24_EXPERIMENTAL_DESIGN = {
    "experimental_unit": "logical_task",
    "independent_unit_count": b2.B2_TASK_COUNT,
    "repository_is_nested_cluster": True,
    "cache_and_repetition_are_technical_repeated_measures": True,
    "complete_six_treatment_randomized_block_within_each_task": True,
    "repository_split_plot_lifecycle_inherited": True,
    "frozen_seeded_schedule_inherited": True,
    "execution_schedule_digest": B24_PARENT_B21_SCHEDULE_DIGEST,
    "runner_machine_is_fixed_nuisance_block": True,
    "all_six_treatments_run_on_one_qualified_machine": True,
    "multi_runner_group_or_arm_sharding_forbidden": True,
    "interim_quality_looks": 0,
    "adaptive_arm_elimination_forbidden": True,
    "single_final_analysis_only": True,
    "tie_policy": copy.deepcopy(b2.B2_TIE_POLICY),
}

B24_INHERITED_ENGINE = {
    "execution_engine": "product_bakeoff_b21_runner.v1",
    "scoring_engine": "product_bakeoff_b21_scorer.v1",
    "same_arm_same_execution_own_parent_lineage_inherited": True,
    "parent_unavailable_terminal_policy_inherited": True,
    "quality_thresholds_and_resource_ceilings_inherited": True,
    "arm_definitions_inherited_without_change": True,
    "arm_count": len(b2.B2_ADAPTER_IDS),
    "logical_record_count": b2.B2_TOTAL_RECORDS,
    "index_build_count": b2.B2_INDEX_BUILD_COUNT,
    "request_timeout_seconds": B24_REQUEST_TIMEOUT_SECONDS,
    "adapter_command_timeout_seconds": B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
    "adapter_timeout_strictly_less_than_request_timeout": True,
    "old_25_second_adapter_command_timeout_not_reused": True,
    "timeout_override_applies_to_prepare_index_context_and_support": True,
    "timeout_values_frozen_before_private_authoring": True,
}

B24_RUNNER_BINDING = {
    "parent_runner_qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
    "parent_runner_qualification_sha256": B24_PARENT_B23_QUALIFICATION_SHA256,
    "qualified_machine_instance_must_be_reused": True,
    "runner_profile_revalidated_immediately_before_tournament": True,
    "stable_runner_profile_must_match_private_qualification_receipt": True,
    "minimum_open_file_soft_limit": 65_535,
    "zero_active_swap_required": True,
    "dedicated_idle_runner_required": True,
    "scratch_and_checkout_on_qualified_data_volume": True,
    "provider_physical_host_exclusivity_not_claimed": True,
    "performance_claim_scope": "within_this_qualified_machine_only",
    "cross_machine_performance_generalization_forbidden": True,
}

B24_EXECUTION_POLICY = {
    "launcher": "standalone_single_process_under_nohup_or_screen",
    "github_actions_used_for_private_tournament": False,
    "private_holdout_preprovisioned_outside_checkout": True,
    "public_readiness_checkpoint_must_be_committed_and_ci_green_before_launch": True,
    "private_launch_authorization_receipt_required": True,
    "future_tournament_attempt_count": 1,
    "complete_restart_after_any_treatment_output_allowed": False,
    "resume_after_process_or_machine_restart_allowed": False,
    "selective_cell_retry_allowed": False,
    "missing_cell_imputation_allowed": False,
    "completed_cells_may_not_be_recomputed": True,
    "task_query_oracle_timeout_or_rule_edit_after_output_forbidden": True,
    "infrastructure_failure_closes_without_result": True,
    "ssh_disconnect_must_not_terminate_process": True,
    "health_monitor_may_report_progress_counts_only": True,
    "intermediate_arm_or_quality_metrics_forbidden": True,
    "scoring_import_forbidden_until_all_pre_score_gates_pass": True,
}

B24_PUBLICATION_POLICY = {
    **dict(b21.B21_PUBLICATION_POLICY),
    "b2_b21_or_b24_private_manifest_digest_public": False,
    "candidate_plan_or_failover_identity_public": False,
    "repository_exclusion_registry_contents_public": False,
    "exact_runner_hardware_profile_public": False,
    "runner_name_machine_identifier_or_scratch_path_public": False,
    "holdout_readiness_counts_and_boolean_gates_public": True,
    "complete_tournament_arm_aggregate_public_only_after_all_gates": True,
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


def validate_parent_b21_failure(repo_root: Path | None = None) -> list[str]:
    root = (repo_root or REPO).resolve()
    path = root / B21_FAILURE_REL
    if path.is_symlink() or not path.is_file():
        return ["parent B2.1 failure aggregate missing or unsafe"]
    if file_sha256(path) != B24_PARENT_B21_FAILURE_SHA256:
        return ["parent B2.1 failure aggregate bytes drifted"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - type-only fail-closed message
        return [f"parent B2.1 failure aggregate unreadable: {type(exc).__name__}"]
    errors: list[str] = []
    if report.get("status") != "product_bakeoff_b21_execution_failed_closed_no_result":
        errors.append("parent B2.1 failure status drifted")
    if report.get("failure_aggregate_digest") != B24_PARENT_B21_FAILURE_DIGEST:
        errors.append("parent B2.1 failure digest drifted")
    protocol = report.get("protocol") or {}
    expected_protocol = {
        "spec_digest": B24_PARENT_B21_SPEC_DIGEST,
        "source_bundle_digest": B24_PARENT_B21_SOURCE_BUNDLE_DIGEST,
        "holdout_frame_digest": B24_PARENT_B21_FRAME_DIGEST,
        "execution_schedule_digest": B24_PARENT_B21_SCHEDULE_DIGEST,
    }
    for key, expected in expected_protocol.items():
        if protocol.get(key) != expected:
            errors.append(f"parent B2.1 {key} drifted")
    execution = report.get("execution") or {}
    if execution.get("complete_restart_attempt_count") != 2:
        errors.append("parent B2.1 attempt count drifted")
    if execution.get("tournament_scoring_executed") is not False:
        errors.append("parent B2.1 scoring state drifted")
    if execution.get("public_tournament_result_exists") is not False:
        errors.append("parent B2.1 result state drifted")
    return sorted(set(errors))


def validate_parent_b23_qualification(repo_root: Path | None = None) -> list[str]:
    root = (repo_root or REPO).resolve()
    path = root / B23_QUALIFICATION_REL
    if path.is_symlink() or not path.is_file():
        return ["parent B2.3 qualification aggregate missing or unsafe"]
    if file_sha256(path) != B24_PARENT_B23_QUALIFICATION_SHA256:
        return ["parent B2.3 qualification aggregate bytes drifted"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - type-only fail-closed message
        return [f"parent B2.3 qualification aggregate unreadable: {type(exc).__name__}"]
    errors = list(b23q.validate_public_report(report))
    if report.get("qualification_digest") != B24_PARENT_B23_QUALIFICATION_DIGEST:
        errors.append("parent B2.3 qualification digest drifted")
    if report.get("b23_spec_digest") != B24_PARENT_B23_SPEC_DIGEST:
        errors.append("parent B2.3 spec digest drifted")
    if report.get("b23_source_bundle_digest") != B24_PARENT_B23_SOURCE_BUNDLE_DIGEST:
        errors.append("parent B2.3 source digest drifted")
    decision = report.get("decision") or {}
    if decision.get("runner_qualified") is not True:
        errors.append("parent B2.3 runner is not qualified")
    if decision.get("future_holdout_authoring_authorized") is not True:
        errors.append("parent B2.3 holdout authoring is not authorized")
    if decision.get("future_tournament_execution_authorized") is not False:
        errors.append("parent B2.3 qualification overauthorizes tournament execution")
    privacy = report.get("privacy") or {}
    if privacy.get("private_input_read") is not False:
        errors.append("parent B2.3 qualification read private input")
    return sorted(set(errors))


def b24_holdout_frame_digest() -> str:
    return _prefixed_digest(
        "b24frame_",
        {
            "parent_task_slot_digest": b2.task_slot_digest(),
            "parent_b21_frame_digest": B24_PARENT_B21_FRAME_DIGEST,
            "holdout_rules": B24_HOLDOUT_RULES,
        },
    )


def b24_execution_schedule_digest() -> str:
    digest = b21.b21_execution_schedule_digest()
    if digest != B24_PARENT_B21_SCHEDULE_DIGEST:
        raise RuntimeError("inherited B2.1 execution schedule digest drifted")
    return digest


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in B24_SOURCE_BUNDLE_PATHS:
        if rel in seen:
            raise RuntimeError(f"duplicate B2.4 source bundle path: {rel}")
        seen.add(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"missing or unsafe B2.4 source bundle file: {rel}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"B2.4 source bundle path escapes repository: {rel}") from exc
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "path": rel,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def b24_source_bundle_digest(repo_root: Path | None = None) -> str:
    inherited = b21.b21_source_bundle_digest(repo_root)
    if inherited != B24_PARENT_B21_SOURCE_BUNDLE_DIGEST:
        raise RuntimeError("inherited B2.1 runtime source bundle drifted")
    return _prefixed_digest(
        "b24src_",
        {
            "inherited_b21_source_bundle_digest": inherited,
            "qualified_b23_source_bundle_digest": B24_PARENT_B23_SOURCE_BUNDLE_DIGEST,
            "overlay_source_rows": _normalized_source_rows(repo_root),
        },
    )


def b24_spec_payload() -> dict[str, Any]:
    return {
        "schema_version": B24_SCHEMA_VERSION,
        "parent_b21_failure": {
            "aggregate_sha256": B24_PARENT_B21_FAILURE_SHA256,
            "failure_digest": B24_PARENT_B21_FAILURE_DIGEST,
            "spec_digest": B24_PARENT_B21_SPEC_DIGEST,
            "source_bundle_digest": B24_PARENT_B21_SOURCE_BUNDLE_DIGEST,
            "holdout_frame_digest": B24_PARENT_B21_FRAME_DIGEST,
            "execution_schedule_digest": B24_PARENT_B21_SCHEDULE_DIGEST,
        },
        "parent_b23_qualification": {
            "qualification_source_checkpoint": (
                B24_PARENT_B23_QUALIFICATION_SOURCE_CHECKPOINT
            ),
            "qualification_publication_checkpoint": (
                B24_PARENT_B23_QUALIFICATION_PUBLICATION_CHECKPOINT
            ),
            "aggregate_sha256": B24_PARENT_B23_QUALIFICATION_SHA256,
            "qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
            "spec_digest": B24_PARENT_B23_SPEC_DIGEST,
            "source_bundle_digest": B24_PARENT_B23_SOURCE_BUNDLE_DIGEST,
        },
        "holdout_rules": copy.deepcopy(B24_HOLDOUT_RULES),
        "experimental_design": copy.deepcopy(B24_EXPERIMENTAL_DESIGN),
        "inherited_engine": copy.deepcopy(B24_INHERITED_ENGINE),
        "runner_binding": copy.deepcopy(B24_RUNNER_BINDING),
        "execution_policy": copy.deepcopy(B24_EXECUTION_POLICY),
        "publication_policy": copy.deepcopy(B24_PUBLICATION_POLICY),
    }


def b24_spec_digest() -> str:
    return _prefixed_digest("b24spec_", b24_spec_payload(), length=16)


def _build_report_without_digest() -> dict[str, Any]:
    return {
        "schema_version": B24_REPORT_SCHEMA_VERSION,
        "phase": B24_PHASE,
        "status": B24_STATUS,
        "claim_level": B24_CLAIM_LEVEL,
        "date": "2026-07-15",
        "parent_b21_failure": b24_spec_payload()["parent_b21_failure"],
        "parent_b23_qualification": b24_spec_payload()["parent_b23_qualification"],
        "holdout_rules": copy.deepcopy(B24_HOLDOUT_RULES),
        "experimental_design": copy.deepcopy(B24_EXPERIMENTAL_DESIGN),
        "inherited_engine": copy.deepcopy(B24_INHERITED_ENGINE),
        "runner_binding": copy.deepcopy(B24_RUNNER_BINDING),
        "execution_policy": copy.deepcopy(B24_EXECUTION_POLICY),
        "privacy_publication": copy.deepcopy(B24_PUBLICATION_POLICY),
        "source_locks": {
            "b24_spec_digest": b24_spec_digest(),
            "b24_source_bundle_digest": b24_source_bundle_digest(),
            "b24_holdout_frame_digest": b24_holdout_frame_digest(),
            "b24_execution_schedule_digest": b24_execution_schedule_digest(),
            "line_endings_normalized_for_cross_platform_digest": True,
        },
        "implementation_readiness": {
            "dual_historical_frame_exclusion_implemented": True,
            "candidate_plan_admission_implemented": True,
            "private_holdout_binding_implemented": True,
            "runtime_freeze_receipt_implemented": True,
            "qualified_runner_launch_authorization_implemented": True,
            "longrun_request_and_adapter_timeout_bridge_implemented": True,
            "aggregate_only_readiness_validator_implemented": True,
            "standalone_disconnect_safe_launcher_implemented": True,
            "private_holdout_materialized": False,
            "private_runtime_frozen": False,
            "treatment_output_exists": False,
            "future_tournament_execution_authorized": False,
        },
        "next_authorized_action": (
            "commit this public B2.4 protocol and obtain green public CI; only then "
            "freeze a private candidate plan, author a new 12-repository/48-task "
            "holdout on the already qualified machine, audit it against both "
            "historical frames and all exclusions, and freeze the exact runtime; "
            "do not execute any treatment arm"
        ),
    }


def build_report() -> dict[str, Any]:
    report = _build_report_without_digest()
    report["protocol_digest"] = _prefixed_digest("b24protocol_", report)
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
    errors.extend(validate_parent_b21_failure())
    errors.extend(validate_parent_b23_qualification())
    errors.extend(_diff(build_report(), report))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = [
        ("parent_b21_failure_valid", not validate_parent_b21_failure()),
        ("parent_b23_qualification_valid", not validate_parent_b23_qualification()),
        ("report_valid", not validate_report(report)),
        ("spec_digest", b24_spec_digest().startswith("b24spec_")),
        ("source_digest", b24_source_bundle_digest().startswith("b24src_")),
        ("frame_digest", b24_holdout_frame_digest().startswith("b24frame_")),
        ("repo_count_12", B24_HOLDOUT_RULES["repository_snapshot_count"] == 12),
        ("logical_n_48", B24_EXPERIMENTAL_DESIGN["independent_unit_count"] == 48),
        ("record_count_1440", B24_INHERITED_ENGINE["logical_record_count"] == 1440),
        ("no_interim_looks", B24_EXPERIMENTAL_DESIGN["interim_quality_looks"] == 0),
        ("single_machine", B24_EXPERIMENTAL_DESIGN["all_six_treatments_run_on_one_qualified_machine"]),
        ("no_sharding", B24_EXPERIMENTAL_DESIGN["multi_runner_group_or_arm_sharding_forbidden"]),
        ("shared_ranks", B24_EXPERIMENTAL_DESIGN["tie_policy"]["exact_equal_quality_vector"] == "shared_competition_rank"),
        ("request_timeout_600", B24_REQUEST_TIMEOUT_SECONDS == 600.0),
        ("adapter_timeout_570", B24_ADAPTER_COMMAND_TIMEOUT_SECONDS == 570.0),
        ("nested_timeout", B24_ADAPTER_COMMAND_TIMEOUT_SECONDS < B24_REQUEST_TIMEOUT_SECONDS),
        ("one_attempt", B24_EXECUTION_POLICY["future_tournament_attempt_count"] == 1),
        ("no_private_holdout", not report["implementation_readiness"]["private_holdout_materialized"]),
        ("no_treatment_output", not report["implementation_readiness"]["treatment_output_exists"]),
        ("no_execution_authority", not report["implementation_readiness"]["future_tournament_execution_authorized"]),
    ]
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[tuple[str, bool]] = []

    def rejected(name: str, mutator: Any) -> None:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append((name, bool(validate_report(value))))

    rejected("unknown_key", lambda value: value.__setitem__("extra", True))
    rejected("parent_failure_drift", lambda value: value["parent_b21_failure"].__setitem__("failure_digest", "drift"))
    rejected("qualification_drift", lambda value: value["parent_b23_qualification"].__setitem__("qualification_digest", "drift"))
    rejected("historical_reuse", lambda value: value["holdout_rules"].__setitem__("all_repository_slugs_absent_from_b21_frame", False))
    rejected("short_timeout", lambda value: value["inherited_engine"].__setitem__("adapter_command_timeout_seconds", 25.0))
    rejected("timeout_inversion", lambda value: value["inherited_engine"].__setitem__("adapter_command_timeout_seconds", 601.0))
    rejected("sharding_enabled", lambda value: value["experimental_design"].__setitem__("multi_runner_group_or_arm_sharding_forbidden", False))
    rejected("interim_look", lambda value: value["experimental_design"].__setitem__("interim_quality_looks", 1))
    rejected("restart_enabled", lambda value: value["execution_policy"].__setitem__("complete_restart_after_any_treatment_output_allowed", True))
    rejected("private_digest_public", lambda value: value["privacy_publication"].__setitem__("b2_b21_or_b24_private_manifest_digest_public", True))
    rejected("execution_overauthorized", lambda value: value["implementation_readiness"].__setitem__("future_tournament_execution_authorized", True))
    rejected("digest_drift", lambda value: value.__setitem__("protocol_digest", "b24protocol_" + "0" * 64))
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit("fault-test failed: " + ", ".join(failed))
    return {"status": "passed", "faults_rejected": len(checks), "faults_total": len(checks)}


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise SystemExit("refusing to write invalid B2.4 report: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.4 fresh qualified holdout protocol")
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
    "B24_HOLDOUT_RULES",
    "B24_EXPERIMENTAL_DESIGN",
    "B24_INHERITED_ENGINE",
    "B24_RUNNER_BINDING",
    "B24_EXECUTION_POLICY",
    "B24_PUBLICATION_POLICY",
    "B24_REQUEST_TIMEOUT_SECONDS",
    "B24_ADAPTER_COMMAND_TIMEOUT_SECONDS",
    "B24_PARENT_B23_QUALIFICATION_DIGEST",
    "B24_PARENT_B23_QUALIFICATION_SHA256",
    "b24_holdout_frame_digest",
    "b24_execution_schedule_digest",
    "b24_source_bundle_digest",
    "b24_spec_digest",
    "build_report",
    "validate_report",
]
