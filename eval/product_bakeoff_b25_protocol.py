#!/usr/bin/env python3
"""Preregister the B2.5 fresh, tokenizer-qualified product tournament.

B2.5 is a new confirmatory envelope.  It does not reopen B2.4 and cannot
reuse its incomplete output or exposed holdout.  It preserves the frozen
B2.1 execution/scoring design, excludes the B2, B2.1, and B2.4 repository
frames, adds a source-only query/token compatibility gate, and requires the
repaired production binary to pass a synthetic qualification on the admitted
Linux machine before any new private authoring.

This public module reads no private input and authorizes no tournament run.
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
import product_bakeoff_b24_protocol as b24  # noqa: E402
from product_bakeoff_b25_query_gate import B25_ANALYZER_CONTRACT  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b25_protocol"
    / "product_bakeoff_b25_protocol_report.json"
)
B24_FAILURE_REL = (
    "artifacts/product_bakeoff_b24/"
    "product_bakeoff_b24_failed_closed_aggregate.json"
)
B24_REPAIR_REL = (
    "artifacts/product_bakeoff_b24_repair/"
    "product_bakeoff_b24_bm25_tokenizer_repair.json"
)

B25_SCHEMA_VERSION = "product_bakeoff_b25_protocol.v1"
B25_REPORT_SCHEMA_VERSION = "product_bakeoff_b25_protocol_report.v1"
B25_PHASE = "product_bakeoff_b25_fresh_tokenizer_qualified_linux_tournament_protocol"
B25_STATUS = (
    "product_bakeoff_b25_protocol_ready_runtime_qualification_pending_"
    "no_private_holdout_no_tournament_no_result"
)
B25_CLAIM_LEVEL = "separately_preregistered_design_only_no_tournament_result"

B25_PARENT_B24_FAILURE_SHA256 = (
    "3ad6df3173c41b068c5b5d4f2b736ffbcd314d0da48cec52632a2ceb18a9cdd7"
)
B25_PARENT_B24_FAILURE_DIGEST = (
    "b24failure_a41d6e150a5e5c2752cfb455b0ca5dd1df35687b9489d82e5a888362dc4c4b83"
)
B25_PARENT_B24_SPEC_DIGEST = "b24spec_52eefc930fac34f5"
B25_PARENT_B24_SOURCE_BUNDLE_DIGEST = (
    "b24src_301e5a211de015d86e2607e68d12f69afaf4474fa5f62fdd68d1c0a58f6c634f"
)
B25_PARENT_B24_FRAME_DIGEST = (
    "b24frame_429a87368330b5c33c8c30a771fd5f62c2f445d9408598bf25cbf0d0fad64d07"
)
B25_PARENT_B24_SCHEDULE_DIGEST = (
    "b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3"
)
B25_PARENT_B24_READINESS_CHECKPOINT = "20d279a39eda578ba4027fbaec3da6b6065279a1"
B25_PARENT_B24_READINESS_CI_RUN_ID = 29453549335

B25_PARENT_B24_REPAIR_SHA256 = (
    "709c94cee11dec685e10f5079599f006e968ab72e99c7478dd501e2b8cf07862"
)
B25_PARENT_B24_REPAIR_DIGEST = (
    "b24repair_2a4e664f19e8c72de3f6f4b09f4476f5313c01b547bbb141cb5c26a394473136"
)
B25_PARENT_B24_REPAIR_SOURCE_CHECKPOINT = (
    "665fd51bba0eae52ade8d5f3c37069217de38916"
)
B25_PARENT_B24_REPAIR_CI_RUN_ID = 29457607093
B25_PARENT_B24_CLOSEOUT_CHECKPOINT = "5e69913a8bed7c68bd379fe8bb18600c556891d8"
B25_PARENT_B24_CLOSEOUT_CI_RUN_ID = 29455988022

B25_PARENT_B23_QUALIFICATION_DIGEST = b24.B24_PARENT_B23_QUALIFICATION_DIGEST
B25_PARENT_B23_QUALIFICATION_SHA256 = b24.B24_PARENT_B23_QUALIFICATION_SHA256

B25_SOURCE_BUNDLE_PATHS = (
    "crates/openlocus-index/src/persistent.rs",
    "crates/openlocus-cli/tests/bakeoff_query_leading_underscore.rs",
    "eval/product_bakeoff_b25_protocol.py",
    "eval/product_bakeoff_b25_query_gate.py",
    "eval/product_bakeoff_b25_runtime_qualification.py",
    "eval/product_bakeoff_b25_corpus.py",
    "eval/product_bakeoff_b25_runner.py",
    "eval/product_bakeoff_b25_scorer.py",
    "eval/product_bakeoff_b25_readiness.py",
    "eval/product_bakeoff_b25_cli.py",
    "scripts/product_bakeoff_b25_linux_longrun.sh",
    ".github/workflows/product-bakeoff-b25-holdout.yml",
)

B25_REQUEST_TIMEOUT_SECONDS = 600.0
B25_ADAPTER_COMMAND_TIMEOUT_SECONDS = 570.0

B25_HOLDOUT_RULES = {
    "repository_snapshot_count": b2.B2_REPO_SLOT_COUNT,
    "logical_task_count": b2.B2_TASK_COUNT,
    "language_count": len(b2.B2_LANGUAGES),
    "size_band_count": len(b2.B2_SIZE_BANDS),
    "task_roles_per_repository": len(b2.B2_TASK_ROLES),
    "historical_repository_frame_labels": ["b2", "b21", "b24"],
    "historical_repository_count": 36,
    "all_repository_slugs_absent_from_b2_b21_and_b24_frames": True,
    "all_repository_identity_commit_pairs_absent_from_b2_b21_and_b24_frames": True,
    "all_real_preflight_and_qualification_repositories_excluded": True,
    "all_synthetic_qualification_sources_excluded": True,
    "all_task_query_and_oracle_rows_new": True,
    "b2_b21_and_b24_empirical_cells_must_not_be_reused": True,
    "b24_incomplete_output_must_not_be_reused": True,
    "b24_private_holdout_must_not_be_reused": True,
    "b2_task_authoring_rules_inherited_without_output_driven_change": True,
    "candidate_plan_slot_count": b2.B2_REPO_SLOT_COUNT,
    "minimum_candidates_per_slot": 2,
    "candidate_order_and_license_expectations_frozen_before_authoring": True,
    "candidate_failover_must_finish_before_any_treatment_output": True,
    "runtime_qualification_must_pass_before_private_authoring": True,
    "query_compatibility_gate_runs_at_authoring_and_freeze": True,
    "query_compatibility_bound_at_readiness_and_runner_admission": True,
    "final_holdout_tasks_not_executed_before_runtime_freeze": True,
    "private_holdout_digests_and_identities_never_public": True,
}

B25_QUERY_COMPATIBILITY = {
    "gate_version": "product_bakeoff_b25_query_compatibility.v1",
    "source_only": True,
    "retrieval_execution_forbidden": True,
    "adapter_execution_forbidden": True,
    "every_query_must_emit_at_least_one_production_token": True,
    "every_answerable_positive_span_must_contain_a_normalized_query_token": True,
    "no_answer_tasks_require_nonempty_tokens_but_have_no_positive_span": True,
    "analyzer_contract": copy.deepcopy(B25_ANALYZER_CONTRACT),
    "private_report_bound_at_authoring": True,
    "private_report_recomputed_at_freeze": True,
    "private_report_file_and_digest_bound_at_readiness": True,
    "private_report_file_and_digest_bound_at_runner_admission": True,
    "query_text_path_excerpt_or_private_digest_public": False,
}

B25_RUNTIME_QUALIFICATION = {
    "qualification_version": "product_bakeoff_b25_runtime_qualification.v1",
    "must_precede_private_authoring": True,
    "must_use_current_production_openlocus_binary": True,
    "must_run_on_b23_admitted_machine_instance": True,
    "synthetic_only_no_private_input": True,
    "synthetic_case_categories": [
        "ordinary_identifier",
        "leading_underscore_identifier",
        "punctuation_split_identifier",
        "one_character_identifier",
    ],
    "all_cases_require_current_evidence": True,
    "all_cases_require_zero_stale_hits_skipped": True,
    "all_cases_require_zero_invalid_hits_skipped": True,
    "provider_network_call_count_must_be_zero": True,
    "qualification_publication_requires_green_ci_before_authoring": True,
    "exact_query_source_profile_path_or_private_receipt_digest_public": False,
}

B25_EXPERIMENTAL_DESIGN = {
    "experimental_unit": "logical_task",
    "independent_unit_count": b2.B2_TASK_COUNT,
    "repository_is_nested_cluster": True,
    "cache_and_repetition_are_technical_repeated_measures": True,
    "complete_six_treatment_randomized_block_within_each_task": True,
    "repository_split_plot_lifecycle_inherited": True,
    "frozen_seeded_schedule_inherited": True,
    "execution_schedule_digest": B25_PARENT_B24_SCHEDULE_DIGEST,
    "runner_machine_is_fixed_nuisance_block": True,
    "all_six_treatments_run_on_one_qualified_machine": True,
    "multi_runner_group_or_arm_sharding_forbidden": True,
    "interim_quality_looks": 0,
    "adaptive_arm_elimination_forbidden": True,
    "single_final_analysis_only": True,
    "tie_policy": copy.deepcopy(b2.B2_TIE_POLICY),
}

B25_INHERITED_ENGINE = {
    "execution_engine": "product_bakeoff_b21_runner.v1",
    "scoring_engine": "product_bakeoff_b21_scorer.v1",
    "b24_failed_attempt_output_used": False,
    "same_arm_same_execution_own_parent_lineage_inherited": True,
    "parent_unavailable_terminal_policy_inherited": True,
    "quality_thresholds_and_resource_ceilings_inherited": True,
    "arm_definitions_inherited_without_change": True,
    "arm_count": len(b2.B2_ADAPTER_IDS),
    "logical_record_count": b2.B2_TOTAL_RECORDS,
    "index_build_count": b2.B2_INDEX_BUILD_COUNT,
    "request_timeout_seconds": B25_REQUEST_TIMEOUT_SECONDS,
    "adapter_command_timeout_seconds": B25_ADAPTER_COMMAND_TIMEOUT_SECONDS,
    "adapter_timeout_strictly_less_than_request_timeout": True,
    "timeout_override_applies_to_prepare_index_context_and_support": True,
    "timeout_values_frozen_before_private_authoring": True,
}

B25_RUNNER_BINDING = {
    "parent_runner_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
    "parent_runner_qualification_sha256": B25_PARENT_B23_QUALIFICATION_SHA256,
    "qualified_machine_instance_must_be_reused": True,
    "repaired_runtime_qualification_must_match_current_cli_bytes": True,
    "runner_profile_revalidated_before_runtime_qualification": True,
    "runner_profile_revalidated_immediately_before_tournament": True,
    "stable_runner_profile_must_match_private_b23_qualification_receipt": True,
    "minimum_open_file_soft_limit": 65_535,
    "zero_active_swap_required": True,
    "dedicated_idle_runner_required": True,
    "scratch_and_checkout_on_qualified_data_volume": True,
    "provider_physical_host_exclusivity_not_claimed": True,
    "performance_claim_scope": "within_this_qualified_machine_only",
    "cross_machine_performance_generalization_forbidden": True,
}

B25_EXECUTION_POLICY = {
    "launcher": "standalone_single_process_under_nohup_or_screen",
    "launcher_invokes_tracked_script_through_bash": True,
    "launcher_resolves_absolute_script_path_before_handoff": True,
    "launcher_success_requires_worker_entry_and_runner_admission": True,
    "worker_startup_handshake_ci_test_required": True,
    "github_actions_used_for_private_tournament": False,
    "public_protocol_and_runtime_qualification_must_be_ci_green_before_authoring": True,
    "private_holdout_preprovisioned_outside_checkout": True,
    "public_readiness_checkpoint_must_be_committed_and_ci_green_before_launch": True,
    "private_launch_authorization_receipt_required": True,
    "private_launch_release_required_after_runner_admission": True,
    "private_launch_release_binds_readiness_checkpoint_and_attempt_number": True,
    "tournament_attempt_boundary": "private_launch_release_after_runner_admission",
    "pid_receipt_or_launcher_acknowledgement_alone_consumes_attempt": False,
    "pre_admission_handoff_failure_with_zero_treatment_output_consumes_attempt": False,
    "future_tournament_attempt_count": 1,
    "complete_restart_after_any_treatment_output_allowed": False,
    "resume_after_process_or_machine_restart_allowed": False,
    "selective_cell_retry_allowed": False,
    "missing_cell_imputation_allowed": False,
    "completed_cells_may_not_be_recomputed": True,
    "task_query_oracle_timeout_or_rule_edit_after_output_forbidden": True,
    "infrastructure_failure_after_attempt_boundary_closes_without_result": True,
    "ssh_disconnect_must_not_terminate_process": True,
    "health_monitor_may_report_progress_counts_only": True,
    "intermediate_arm_or_quality_metrics_forbidden": True,
    "scoring_import_forbidden_until_all_pre_score_gates_pass": True,
}

B25_PUBLICATION_POLICY = {
    **dict(b24.B24_PUBLICATION_POLICY),
    "b24_failure_and_repair_aggregate_locks_public": True,
    "b2_b21_b24_or_b25_private_manifest_digest_public": False,
    "runtime_qualification_aggregate_counts_and_boolean_gates_public": True,
    "runtime_qualification_exact_query_source_profile_path_or_private_digest_public": False,
    "query_compatibility_counts_and_boolean_gates_public": True,
    "query_compatibility_private_report_digest_public": False,
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


def validate_parent_b24_failure(repo_root: Path | None = None) -> list[str]:
    root = (repo_root or REPO).resolve()
    path = root / B24_FAILURE_REL
    if path.is_symlink() or not path.is_file():
        return ["parent B2.4 failure aggregate missing or unsafe"]
    if file_sha256(path) != B25_PARENT_B24_FAILURE_SHA256:
        return ["parent B2.4 failure aggregate bytes drifted"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail-closed type only
        return [f"parent B2.4 failure aggregate unreadable: {type(exc).__name__}"]
    errors: list[str] = []
    if report.get("status") != "product_bakeoff_b24_execution_failed_closed_no_result":
        errors.append("parent B2.4 failure status drifted")
    if report.get("failure_aggregate_digest") != B25_PARENT_B24_FAILURE_DIGEST:
        errors.append("parent B2.4 failure digest drifted")
    protocol = report.get("protocol") or {}
    expected_protocol = {
        "spec_digest": B25_PARENT_B24_SPEC_DIGEST,
        "source_bundle_digest": B25_PARENT_B24_SOURCE_BUNDLE_DIGEST,
        "holdout_frame_digest": B25_PARENT_B24_FRAME_DIGEST,
        "execution_schedule_digest": B25_PARENT_B24_SCHEDULE_DIGEST,
    }
    for key, expected in expected_protocol.items():
        if protocol.get(key) != expected:
            errors.append(f"parent B2.4 {key} drifted")
    execution = report.get("execution") or {}
    if execution.get("formal_tournament_attempt_count") != 1:
        errors.append("parent B2.4 attempt count drifted")
    if execution.get("complete_matrix_gate_passed") is not False:
        errors.append("parent B2.4 complete-matrix state drifted")
    if execution.get("tournament_scoring_executed") is not False:
        errors.append("parent B2.4 scoring state drifted")
    if execution.get("public_tournament_result_exists") is not False:
        errors.append("parent B2.4 result state drifted")
    source_gate = report.get("source_gate") or {}
    if source_gate.get("readiness_checkpoint") != B25_PARENT_B24_READINESS_CHECKPOINT:
        errors.append("parent B2.4 readiness checkpoint drifted")
    if source_gate.get("ci_run_id") != B25_PARENT_B24_READINESS_CI_RUN_ID:
        errors.append("parent B2.4 readiness CI run drifted")
    return sorted(set(errors))


def validate_parent_b24_repair(repo_root: Path | None = None) -> list[str]:
    root = (repo_root or REPO).resolve()
    path = root / B24_REPAIR_REL
    if path.is_symlink() or not path.is_file():
        return ["parent B2.4 repair aggregate missing or unsafe"]
    if file_sha256(path) != B25_PARENT_B24_REPAIR_SHA256:
        return ["parent B2.4 repair aggregate bytes drifted"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"parent B2.4 repair aggregate unreadable: {type(exc).__name__}"]
    errors: list[str] = []
    expected_status = (
        "product_bakeoff_b24_postcloseout_bm25_tokenizer_repair_complete_"
        "b25_design_authorized"
    )
    if report.get("status") != expected_status:
        errors.append("parent B2.4 repair status drifted")
    if report.get("repair_digest") != B25_PARENT_B24_REPAIR_DIGEST:
        errors.append("parent B2.4 repair digest drifted")
    repair = report.get("repair") or {}
    expected_repair = {
        "source_checkpoint": B25_PARENT_B24_REPAIR_SOURCE_CHECKPOINT,
        "linux_ci_run_id": B25_PARENT_B24_REPAIR_CI_RUN_ID,
        "linux_ci_conclusion": "success",
        "content_field_actual_tantivy_tokenizer_reused": True,
        "legacy_handwritten_query_splitter_removed": True,
        "bakeoff_query_end_to_end_regression_passed": True,
        "b24_result_reopened": False,
    }
    for key, expected in expected_repair.items():
        if repair.get(key) != expected:
            errors.append(f"parent B2.4 repair {key} drifted")
    closeout = report.get("parent_closeout") or {}
    if closeout.get("checkpoint") != B25_PARENT_B24_CLOSEOUT_CHECKPOINT:
        errors.append("parent B2.4 closeout checkpoint drifted")
    if closeout.get("ci_run_id") != B25_PARENT_B24_CLOSEOUT_CI_RUN_ID:
        errors.append("parent B2.4 closeout CI run drifted")
    requirements = report.get("future_gate_requirements") or {}
    for key in (
        "fresh_holdout_required",
        "b24_private_repositories_must_be_excluded_from_next_holdout",
        "query_compatibility_bound_at_authoring_freeze_readiness_and_admission",
        "repaired_binary_must_pass_synthetic_runner_qualification",
        "separately_preregistered_tournament_required",
    ):
        if requirements.get(key) is not True:
            errors.append(f"parent B2.4 repair requirement {key} drifted")
    return sorted(set(errors))


def validate_parent_b23_qualification(repo_root: Path | None = None) -> list[str]:
    return b24.validate_parent_b23_qualification(repo_root)


def b25_holdout_frame_digest() -> str:
    return _prefixed_digest(
        "b25frame_",
        {
            "parent_task_slot_digest": b2.task_slot_digest(),
            "parent_b24_failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
            "parent_b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
            "holdout_rules": B25_HOLDOUT_RULES,
            "query_compatibility": B25_QUERY_COMPATIBILITY,
        },
    )


def b25_execution_schedule_digest() -> str:
    digest = b21.b21_execution_schedule_digest()
    if digest != B25_PARENT_B24_SCHEDULE_DIGEST:
        raise RuntimeError("inherited B2.1 execution schedule digest drifted")
    return digest


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in B25_SOURCE_BUNDLE_PATHS:
        if rel in seen:
            raise RuntimeError(f"duplicate B2.5 source bundle path: {rel}")
        seen.add(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"missing or unsafe B2.5 source bundle file: {rel}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"B2.5 source bundle path escapes repository: {rel}") from exc
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "path": rel,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def b25_source_bundle_digest(repo_root: Path | None = None) -> str:
    inherited = b24.b24_source_bundle_digest(repo_root)
    if inherited != B25_PARENT_B24_SOURCE_BUNDLE_DIGEST:
        raise RuntimeError("inherited B2.4 source bundle drifted")
    return _prefixed_digest(
        "b25src_",
        {
            "inherited_b24_source_bundle_digest": inherited,
            "parent_b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
            "overlay_source_rows": _normalized_source_rows(repo_root),
        },
    )


def b25_spec_payload() -> dict[str, Any]:
    return {
        "schema_version": B25_SCHEMA_VERSION,
        "parent_b24_failure": {
            "aggregate_sha256": B25_PARENT_B24_FAILURE_SHA256,
            "failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
            "spec_digest": B25_PARENT_B24_SPEC_DIGEST,
            "source_bundle_digest": B25_PARENT_B24_SOURCE_BUNDLE_DIGEST,
            "holdout_frame_digest": B25_PARENT_B24_FRAME_DIGEST,
            "execution_schedule_digest": B25_PARENT_B24_SCHEDULE_DIGEST,
        },
        "parent_b24_repair": {
            "aggregate_sha256": B25_PARENT_B24_REPAIR_SHA256,
            "repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
            "repair_source_checkpoint": B25_PARENT_B24_REPAIR_SOURCE_CHECKPOINT,
            "repair_ci_run_id": B25_PARENT_B24_REPAIR_CI_RUN_ID,
            "repair_ci_conclusion": "success",
        },
        "parent_b23_qualification": {
            "qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
            "aggregate_sha256": B25_PARENT_B23_QUALIFICATION_SHA256,
        },
        "holdout_rules": copy.deepcopy(B25_HOLDOUT_RULES),
        "query_compatibility": copy.deepcopy(B25_QUERY_COMPATIBILITY),
        "runtime_qualification": copy.deepcopy(B25_RUNTIME_QUALIFICATION),
        "experimental_design": copy.deepcopy(B25_EXPERIMENTAL_DESIGN),
        "inherited_engine": copy.deepcopy(B25_INHERITED_ENGINE),
        "runner_binding": copy.deepcopy(B25_RUNNER_BINDING),
        "execution_policy": copy.deepcopy(B25_EXECUTION_POLICY),
        "publication_policy": copy.deepcopy(B25_PUBLICATION_POLICY),
    }


def b25_spec_digest() -> str:
    return _prefixed_digest("b25spec_", b25_spec_payload(), length=16)


def _build_report_without_digest() -> dict[str, Any]:
    payload = b25_spec_payload()
    return {
        "schema_version": B25_REPORT_SCHEMA_VERSION,
        "phase": B25_PHASE,
        "status": B25_STATUS,
        "claim_level": B25_CLAIM_LEVEL,
        "date": "2026-07-16",
        "parent_b24_failure": payload["parent_b24_failure"],
        "parent_b24_repair": payload["parent_b24_repair"],
        "parent_b23_qualification": payload["parent_b23_qualification"],
        "holdout_rules": copy.deepcopy(B25_HOLDOUT_RULES),
        "query_compatibility": copy.deepcopy(B25_QUERY_COMPATIBILITY),
        "runtime_qualification": copy.deepcopy(B25_RUNTIME_QUALIFICATION),
        "experimental_design": copy.deepcopy(B25_EXPERIMENTAL_DESIGN),
        "inherited_engine": copy.deepcopy(B25_INHERITED_ENGINE),
        "runner_binding": copy.deepcopy(B25_RUNNER_BINDING),
        "execution_policy": copy.deepcopy(B25_EXECUTION_POLICY),
        "privacy_publication": copy.deepcopy(B25_PUBLICATION_POLICY),
        "source_locks": {
            "b25_spec_digest": b25_spec_digest(),
            "b25_source_bundle_digest": b25_source_bundle_digest(),
            "b25_holdout_frame_digest": b25_holdout_frame_digest(),
            "b25_execution_schedule_digest": b25_execution_schedule_digest(),
            "line_endings_normalized_for_cross_platform_digest": True,
        },
        "implementation_readiness": {
            "repaired_persistent_bm25_source_and_regression_bound": True,
            "triple_historical_frame_exclusion_implemented": True,
            "source_only_query_compatibility_gate_implemented": True,
            "synthetic_repaired_runtime_qualification_implemented": True,
            "private_holdout_binding_implemented": True,
            "runtime_freeze_receipt_implemented": True,
            "qualified_runner_launch_authorization_implemented": True,
            "aggregate_only_readiness_validator_implemented": True,
            "standalone_disconnect_safe_launcher_implemented": True,
            "runner_admission_launch_release_handshake_implemented": True,
            "runtime_qualification_completed": False,
            "private_holdout_materialized": False,
            "private_runtime_frozen": False,
            "treatment_output_exists": False,
            "future_tournament_execution_authorized": False,
        },
        "next_authorized_action": (
            "commit this B2.5 public protocol and implementation and obtain green "
            "CI; then run the synthetic repaired-runtime qualification on the "
            "B2.3-admitted Linux machine without private input, publish only its "
            "aggregate report, and obtain green CI before any fresh private "
            "holdout authoring"
        ),
    }


def build_report() -> dict[str, Any]:
    report = _build_report_without_digest()
    report["protocol_digest"] = _prefixed_digest("b25protocol_", report)
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
    errors.extend(validate_parent_b24_failure())
    errors.extend(validate_parent_b24_repair())
    errors.extend(validate_parent_b23_qualification())
    errors.extend(_diff(build_report(), report))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = [
        ("parent_b24_failure_valid", not validate_parent_b24_failure()),
        ("parent_b24_repair_valid", not validate_parent_b24_repair()),
        ("parent_b23_qualification_valid", not validate_parent_b23_qualification()),
        ("report_valid", not validate_report(report)),
        ("spec_digest", b25_spec_digest().startswith("b25spec_")),
        ("source_digest", b25_source_bundle_digest().startswith("b25src_")),
        ("frame_digest", b25_holdout_frame_digest().startswith("b25frame_")),
        ("historical_repo_count_36", B25_HOLDOUT_RULES["historical_repository_count"] == 36),
        ("logical_n_48", B25_EXPERIMENTAL_DESIGN["independent_unit_count"] == 48),
        ("record_count_1440", B25_INHERITED_ENGINE["logical_record_count"] == 1440),
        ("no_interim_looks", B25_EXPERIMENTAL_DESIGN["interim_quality_looks"] == 0),
        ("single_machine", B25_EXPERIMENTAL_DESIGN["all_six_treatments_run_on_one_qualified_machine"]),
        ("no_sharding", B25_EXPERIMENTAL_DESIGN["multi_runner_group_or_arm_sharding_forbidden"]),
        ("shared_ranks", B25_EXPERIMENTAL_DESIGN["tie_policy"]["exact_equal_quality_vector"] == "shared_competition_rank"),
        ("query_gate_source_only", B25_QUERY_COMPATIBILITY["source_only"]),
        ("runtime_qualification_precedes_authoring", B25_RUNTIME_QUALIFICATION["must_precede_private_authoring"]),
        ("request_timeout_600", B25_REQUEST_TIMEOUT_SECONDS == 600.0),
        ("adapter_timeout_570", B25_ADAPTER_COMMAND_TIMEOUT_SECONDS == 570.0),
        ("one_attempt", B25_EXECUTION_POLICY["future_tournament_attempt_count"] == 1),
        (
            "admission_release_attempt_boundary",
            B25_EXECUTION_POLICY["tournament_attempt_boundary"]
            == "private_launch_release_after_runner_admission",
        ),
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
    rejected("failure_drift", lambda value: value["parent_b24_failure"].__setitem__("failure_digest", "drift"))
    rejected("repair_drift", lambda value: value["parent_b24_repair"].__setitem__("repair_digest", "drift"))
    rejected("historical_reuse", lambda value: value["holdout_rules"].__setitem__("all_repository_slugs_absent_from_b2_b21_and_b24_frames", False))
    rejected("query_retrieval_enabled", lambda value: value["query_compatibility"].__setitem__("retrieval_execution_forbidden", False))
    rejected("runtime_qualification_after_authoring", lambda value: value["runtime_qualification"].__setitem__("must_precede_private_authoring", False))
    rejected("short_timeout", lambda value: value["inherited_engine"].__setitem__("adapter_command_timeout_seconds", 25.0))
    rejected("sharding_enabled", lambda value: value["experimental_design"].__setitem__("multi_runner_group_or_arm_sharding_forbidden", False))
    rejected("interim_look", lambda value: value["experimental_design"].__setitem__("interim_quality_looks", 1))
    rejected("restart_enabled", lambda value: value["execution_policy"].__setitem__("complete_restart_after_any_treatment_output_allowed", True))
    rejected("private_digest_public", lambda value: value["privacy_publication"].__setitem__("query_compatibility_private_report_digest_public", True))
    rejected("execution_overauthorized", lambda value: value["implementation_readiness"].__setitem__("future_tournament_execution_authorized", True))
    rejected("digest_drift", lambda value: value.__setitem__("protocol_digest", "b25protocol_" + "0" * 64))
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit("fault-test failed: " + ", ".join(failed))
    return {"status": "passed", "faults_rejected": len(checks), "faults_total": len(checks)}


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise SystemExit("refusing to write invalid B2.5 report: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.5 fresh tokenizer-qualified protocol")
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
    "B25_HOLDOUT_RULES",
    "B25_QUERY_COMPATIBILITY",
    "B25_RUNTIME_QUALIFICATION",
    "B25_EXPERIMENTAL_DESIGN",
    "B25_INHERITED_ENGINE",
    "B25_RUNNER_BINDING",
    "B25_EXECUTION_POLICY",
    "B25_PUBLICATION_POLICY",
    "B25_REQUEST_TIMEOUT_SECONDS",
    "B25_ADAPTER_COMMAND_TIMEOUT_SECONDS",
    "B25_PARENT_B24_FAILURE_DIGEST",
    "B25_PARENT_B24_REPAIR_DIGEST",
    "B25_PARENT_B23_QUALIFICATION_DIGEST",
    "B25_REPORT_SCHEMA_VERSION",
    "b25_holdout_frame_digest",
    "b25_execution_schedule_digest",
    "b25_source_bundle_digest",
    "b25_spec_digest",
    "build_report",
    "validate_report",
    "run_self_test",
    "run_fault_test",
]
