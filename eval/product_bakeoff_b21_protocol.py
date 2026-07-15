#!/usr/bin/env python3
"""Freeze the B2.1 own-parent holdout tournament protocol.

B2.1 is a new confirmatory experiment after B2 failed closed.  It does not
repair, resume, or score the incomplete B2 matrix.  The task-authoring rules,
six treatment stacks, quality thresholds, split-plot lifecycle, and privacy
boundary are inherited.  The single design change is preregistered here:
each arm's support step is bound to that arm's own same-execution context
target.  Cross-arm target/path equality is neither required nor normalized.
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


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b21_protocol"
    / "product_bakeoff_b21_protocol_report.json"
)
B2_FAILURE_AGGREGATE_REL = (
    "artifacts/product_bakeoff_b2/"
    "product_bakeoff_b2_failed_closed_aggregate.json"
)
B2_PROTOCOL_REPORT_REL = (
    "artifacts/product_bakeoff_b2_protocol/"
    "product_bakeoff_b2_protocol_report.json"
)

B21_SCHEMA_VERSION = "product_bakeoff_b21_protocol.v1"
B21_REPORT_SCHEMA_VERSION = "product_bakeoff_b21_protocol_report.v1"
B21_PHASE = "product_bakeoff_b21_own_parent_holdout_tournament_protocol"
B21_STATUS = "product_bakeoff_b21_implementation_ready_preflight_passed_no_holdout_no_result"
B21_CLAIM_LEVEL = "implementation_ready_no_b21_tournament_result"

B21_PARENT_B2_SOURCE_CHECKPOINT = (
    "55e0ebaaaf6f25c5c7d5c13ffc6ee58825e7d915"
)
B21_PARENT_B2_CLOSEOUT_CHECKPOINT = (
    "07bfd116622bd0ed9a2bc654abec3bb98a7f38df"
)
B21_PARENT_B2_SPEC_DIGEST = "b2spec_358b77c924fbe3f1"
B21_PARENT_B2_SOURCE_BUNDLE_DIGEST = (
    "b2src_c129273f4078d484401e4e255a110b926a0cce7f513fe2f1455415f6309f2ea0"
)
B21_PARENT_B2_TASK_SLOT_DIGEST = (
    "b2slots_a92720057d2f931e1f84c2b3d49af5a4e2efe08661d7c49e375e8835a80149ff"
)
B21_PARENT_B2_SCHEDULE_DIGEST = (
    "b2sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3"
)
B21_PARENT_B2_PROTOCOL_REPORT_DIGEST = (
    "b2protocol_9057cbb85bb11f84377424a96ea2de55e7bff80314520b89b3c0c1e35340b679"
)
B21_PARENT_B2_FAILURE_AGGREGATE_SHA256 = (
    "6097e6ec903930fc0bdebd75ffc4c75a635bb9c0d1984d6d90050ebcdb79074b"
)

B21_SOURCE_BUNDLE_PATHS = tuple(b2.B2_SOURCE_BUNDLE_PATHS) + (
    "eval/product_bakeoff_b21_corpus.py",
    "eval/product_bakeoff_b21_runner.py",
    "eval/product_bakeoff_b21_scorer.py",
    "eval/product_bakeoff_b21_cli.py",
    "eval/product_bakeoff_b21_protocol.py",
    ".github/workflows/product-bakeoff-b21.yml",
)

B21_HOLDOUT_RULES = {
    "repository_snapshot_count": b2.B2_REPO_SLOT_COUNT,
    "logical_task_count": b2.B2_TASK_COUNT,
    "all_repository_slugs_absent_from_b2_frame": True,
    "all_repository_identity_commit_pairs_absent_from_b2_frame": True,
    "all_real_preflight_repository_slugs_absent_from_final_holdout": True,
    "all_task_query_and_oracle_rows_new": True,
    "b2_empirical_cells_must_not_be_reused": True,
    "b2_private_manifests_must_not_be_reused": True,
    "b2_task_authoring_rules_inherited_without_output_driven_change": True,
    "final_holdout_tasks_not_executed_before_runtime_freeze": True,
    "candidate_failover_must_finish_before_any_final_arm_output": True,
}

B21_LINEAGE_POLICY = {
    "policy": "same_arm_same_execution_own_parent_v1",
    "all_six_context_steps_execute_before_any_support_step": True,
    "support_steps_follow_the_same_frozen_arm_order": True,
    "support_parent_scope": "same_arm_same_task_same_repetition_same_episode",
    "support_parent_source": "accepted_same_execution_context_capture",
    "support_parent_must_be_current_source_valid": True,
    "support_parent_target_id_must_be_recomputed_by_parent": True,
    "cross_arm_parent_path_equality_required": False,
    "cross_arm_parent_range_equality_required": False,
    "cross_arm_parent_normalization_forbidden": True,
    "cross_arm_parent_substitution_forbidden": True,
    "target_divergence_is_a_treatment_mediator_not_a_gate_failure": True,
    "oracle_fixed_common_parent_not_used_in_main_tournament": True,
}

B21_PARENT_UNAVAILABLE_POLICY = {
    "policy": "validated_terminal_support_opportunity_v1",
    "eligible_only_after_accepted_context_outcome": True,
    "trigger": "accepted_context_does_not_supply_exactly_one_ready_primary_target",
    "logical_support_record_still_required": True,
    "adapter_support_query_executed": False,
    "terminal_outcome": "parent_unavailable",
    "terminal_counts_as_support_failure": True,
    "terminal_counts_as_task_failure": True,
    "terminal_is_not_an_infrastructure_failure": True,
    "terminal_resource_sample_parent_observed": True,
    "terminal_excluded_from_query_latency_percentile": True,
    "terminal_excluded_from_peak_rss_percentile": True,
    "terminal_count_reported_at_arm_aggregate": True,
    "rejected_timeout_or_malformed_context_still_fails_run_closed": True,
}

B21_FAIRNESS_POLICY = {
    "context_fingerprint_equal_across_arms": True,
    "support_static_envelope_equal_across_arms": True,
    "support_parent_fields_allowed_to_differ_as_treatment_output": True,
    "same_visible_source_bytes": True,
    "same_task_query_budget_timeout_and_cache_label": True,
    "same_split_plot_repository_state_lifecycle": True,
    "arm_specific_budget_or_visibility_forbidden": True,
}

B21_SCORING_OVERRIDES = {
    "two_step_context_target": (
        "score_each_arm_against_the_frozen_oracle_using_that_arms_own_context_target"
    ),
    "two_step_support": (
        "context_target_success_and_same_arm_parent_lineage_valid_and_at_least_one_"
        "selected_support_span_matches_a_frozen_relation"
    ),
    "parent_unavailable": "support_success_false_and_task_success_false",
    "target_divergence": "not_a_failure_gate_and_not_normalized",
    "quality_analysis_unit": "logical_task_after_four_technical_repetitions_agree",
    "resource_query_population": (
        "executed_adapter_queries_only;_terminal_support_opportunities_excluded"
    ),
    "resource_rss_population": (
        "executed_adapter_records_only;_terminal_parent_wrapper_rss_excluded"
    ),
    "terminal_support_count": "reported_separately_and_never_rewards_quality",
}

B21_HARD_GATES = {
    **dict(b2.B2_HARD_GATES),
    "parent_b2_failed_closed_lock_matches": True,
    "fresh_holdout_repository_frame": True,
    "fresh_holdout_task_and_oracle_rows": True,
    "complete_1440_logical_record_matrix": True,
    "normal_adapter_records_accepted_and_scoreable": True,
    "terminal_support_records_closed_and_valid": True,
    "same_arm_parent_lineage_valid": True,
    "cross_arm_parent_convergence_not_required": True,
}
B21_HARD_GATES.pop("complete_1440_record_matrix", None)

B21_FORBIDDEN_ADAPTATIONS = tuple(b2.B2_FORBIDDEN_ADAPTATIONS) + (
    "no_reuse_or_resume_of_incomplete_b2_cells",
    "no_repository_slug_overlap_with_b2_holdout",
    "no_post_output_switch_between_own_parent_and_common_parent",
    "no_cross_arm_parent_majority_vote_or_consensus_selection",
    "no_dropping_parent_unavailable_support_opportunities",
)

B21_PUBLICATION_POLICY = {
    **dict(b2.B2_PUBLICATION_POLICY),
    "b2_or_b21_private_manifest_digest_public": False,
    "parent_path_partition_or_per_task_divergence_public": False,
    "terminal_support_count_public_at_arm_aggregate": True,
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any, *, length: int | None = None) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    if length is not None:
        digest = digest[:length]
    return prefix + digest


def b21_task_frame_digest() -> str:
    return _prefixed_digest(
        "b21frame_",
        {
            "parent_task_slot_digest": b2.task_slot_digest(),
            "holdout_rules": B21_HOLDOUT_RULES,
        },
    )


def b21_execution_schedule_digest() -> str:
    return _prefixed_digest(
        "b21sched_",
        [row.to_dict() for row in b2.build_execution_schedule()],
    )


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in B21_SOURCE_BUNDLE_PATHS:
        if rel in seen:
            raise RuntimeError(f"duplicate B2.1 source bundle path: {rel}")
        seen.add(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"missing or unsafe B2.1 source bundle file: {rel}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"B2.1 source bundle path escapes repo: {rel}") from exc
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "path": rel,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def b21_source_bundle_digest(repo_root: Path | None = None) -> str:
    return _prefixed_digest("b21src_", _normalized_source_rows(repo_root))


def b21_spec_payload() -> dict[str, Any]:
    return {
        "schema_version": B21_SCHEMA_VERSION,
        "parent_b2": {
            "source_checkpoint": B21_PARENT_B2_SOURCE_CHECKPOINT,
            "closeout_checkpoint": B21_PARENT_B2_CLOSEOUT_CHECKPOINT,
            "spec_digest": B21_PARENT_B2_SPEC_DIGEST,
            "source_bundle_digest": B21_PARENT_B2_SOURCE_BUNDLE_DIGEST,
            "task_slot_digest": B21_PARENT_B2_TASK_SLOT_DIGEST,
            "schedule_digest": B21_PARENT_B2_SCHEDULE_DIGEST,
            "protocol_report_digest": B21_PARENT_B2_PROTOCOL_REPORT_DIGEST,
            "failure_aggregate_sha256": B21_PARENT_B2_FAILURE_AGGREGATE_SHA256,
        },
        "treatments": list(b2.B2_ADAPTER_IDS),
        "task_frame": {
            "parent_slot_digest": b2.task_slot_digest(),
            "b21_frame_digest": b21_task_frame_digest(),
            "holdout_rules": B21_HOLDOUT_RULES,
        },
        "experimental_unit": "logical_task",
        "independent_unit_count": b2.B2_TASK_COUNT,
        "repository_is_nested_cluster": True,
        "cache_and_repetition_are_technical_repeated_measures": True,
        "schedule_digest": b21_execution_schedule_digest(),
        "lineage_policy": B21_LINEAGE_POLICY,
        "parent_unavailable_policy": B21_PARENT_UNAVAILABLE_POLICY,
        "fairness_policy": B21_FAIRNESS_POLICY,
        "scoring_overrides": B21_SCORING_OVERRIDES,
        "quality_floors": b2.B2_QUALITY_FLOORS,
        "baseline_noninferiority": b2.B2_BASELINE_NONINFERIORITY,
        "baseline_resource_ceilings": b2.B2_BASELINE_RESOURCE_CEILINGS,
        "component_rules": b2.B2_COMPONENT_RULES,
        "required_component_rules": b2.B2_REQUIRED_COMPONENT_RULES,
        "decision_equivalence": b2.B2_DECISION_EQUIVALENCE,
        "tie_policy": b2.B2_TIE_POLICY,
        "hard_gates": B21_HARD_GATES,
        "forbidden_adaptations": B21_FORBIDDEN_ADAPTATIONS,
        "publication_policy": B21_PUBLICATION_POLICY,
    }


def b21_spec_digest() -> str:
    return _prefixed_digest("b21spec_", b21_spec_payload(), length=16)


def validate_parent_b2_closeout() -> list[str]:
    errors: list[str] = []
    failure_path = REPO / B2_FAILURE_AGGREGATE_REL
    if failure_path.is_symlink() or not failure_path.is_file():
        return ["parent B2 failed-closed aggregate missing or unsafe"]
    if hashlib.sha256(failure_path.read_bytes()).hexdigest() != B21_PARENT_B2_FAILURE_AGGREGATE_SHA256:
        errors.append("parent B2 failed-closed aggregate byte digest drift")
    try:
        failure = json.loads(failure_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail closed with type only
        return [f"parent B2 failed-closed aggregate unreadable: {type(exc).__name__}"]
    expected = {
        "status": "product_bakeoff_b2_execution_failed_closed_no_result",
        "source_checkpoint": B21_PARENT_B2_SOURCE_CHECKPOINT,
        "claim_level": "incomplete_matrix_no_tournament_result",
    }
    for key, value in expected.items():
        if failure.get(key) != value:
            errors.append(f"parent B2 closeout drift: {key}")
    execution = failure.get("execution", {})
    if execution.get("expected_complete_record_count") != b2.B2_TOTAL_RECORDS:
        errors.append("parent B2 expected matrix drift")
    if execution.get("complete_matrix_gate_passed") is not False:
        errors.append("parent B2 must remain incomplete")
    if execution.get("tournament_scoring_executed") is not False:
        errors.append("parent B2 must remain unscored")
    if execution.get("product_default_changed") is not False:
        errors.append("parent B2 must not change product default")

    protocol_path = REPO / B2_PROTOCOL_REPORT_REL
    if protocol_path.is_symlink() or not protocol_path.is_file():
        errors.append("parent B2 protocol report missing or unsafe")
    else:
        try:
            protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"parent B2 protocol unreadable: {type(exc).__name__}")
        else:
            errors.extend(f"parent B2 protocol: {item}" for item in b2.validate_report(protocol))
    return sorted(set(errors))


def _build_report_without_digest() -> dict[str, Any]:
    slots = b2.build_task_slots()
    schedule = b2.build_execution_schedule(slots)
    if b2.validate_task_slots(slots) or b2.validate_execution_schedule(schedule, slots):
        raise RuntimeError("inherited B2 task frame or schedule is invalid")
    b2_report = b2.build_report()
    metric_contract = copy.deepcopy(b2_report["metric_contract"])
    metric_contract["scoring_rules"].update(B21_SCORING_OVERRIDES)
    metric_contract["terminal_support_opportunities_are_quality_failures"] = True
    metric_contract["terminal_support_opportunities_excluded_from_query_p95"] = True
    metric_contract["terminal_support_opportunities_excluded_from_peak_rss_p95"] = True
    promotion = copy.deepcopy(b2_report["promotion_contract"])
    return {
        "schema_version": B21_REPORT_SCHEMA_VERSION,
        "phase": B21_PHASE,
        "status": B21_STATUS,
        "claim_level": B21_CLAIM_LEVEL,
        "parent_b2_lock": {
            "source_checkpoint": B21_PARENT_B2_SOURCE_CHECKPOINT,
            "closeout_checkpoint": B21_PARENT_B2_CLOSEOUT_CHECKPOINT,
            "spec_digest": B21_PARENT_B2_SPEC_DIGEST,
            "source_bundle_digest": B21_PARENT_B2_SOURCE_BUNDLE_DIGEST,
            "task_slot_digest": B21_PARENT_B2_TASK_SLOT_DIGEST,
            "schedule_digest": B21_PARENT_B2_SCHEDULE_DIGEST,
            "protocol_report_digest": B21_PARENT_B2_PROTOCOL_REPORT_DIGEST,
            "failed_closed_aggregate": B2_FAILURE_AGGREGATE_REL,
            "failed_closed_aggregate_sha256": B21_PARENT_B2_FAILURE_AGGREGATE_SHA256,
            "b2_result_reused": False,
        },
        "execution_boundary": {
            "design_only": False,
            "implementation_ready": True,
            "unused_repository_real_source_preflight_executed": True,
            "preflight_repository_identity_count": 2,
            "preflight_scenario_count": 3,
            "preflight_logical_record_count": 36,
            "preflight_normal_record_count": 30,
            "preflight_terminal_support_record_count": 6,
            "preflight_cross_path_divergence_observed_and_tolerated": True,
            "preflight_provider_or_network_call_count": 0,
            "holdout_repositories_materialized": False,
            "holdout_tasks_materialized": False,
            "final_holdout_adapter_execution_executed": False,
            "tournament_scoring_executed": False,
            "winner_or_default_selected": False,
            "provider_or_network_calls_executed": False,
        },
        "design_rationale": {
            "b2_stopping_condition": "cross_arm_parent_path_divergence",
            "b2_records_were_mechanically_valid": True,
            "b2_failure_was_not_used_to_rank_or_select_an_arm": True,
            "own_parent_policy_preserves_target_selection_as_part_of_treatment": True,
            "common_parent_policy_removed_only_in_new_holdout_experiment": True,
        },
        "experimental_design": {
            "design_type": "randomized_complete_task_blocks_with_repo_split_plot_lifecycle",
            "experimental_unit": "logical_task",
            "independent_unit_count": b2.B2_TASK_COUNT,
            "treatments": list(b2.B2_ADAPTER_IDS),
            "complete_block": "every_task_receives_all_six_stacks",
            "repository_is_nested_cluster": True,
            "cache_and_repetition_are_technical_repeated_measures": True,
            "technical_measurements_do_not_increase_independent_n": True,
            "interim_looks": 0,
            "single_final_analysis_only": True,
        },
        "holdout_frame": {
            "parent_task_authoring_spec_digest": B21_PARENT_B2_SPEC_DIGEST,
            "parent_task_slot_digest": b2.task_slot_digest(slots),
            "b21_holdout_frame_digest": b21_task_frame_digest(),
            "repository_slot_count": b2.B2_REPO_SLOT_COUNT,
            "logical_task_count": b2.B2_TASK_COUNT,
            "language_counts": b2_report["task_frame"]["language_counts"],
            "size_counts": b2_report["task_frame"]["size_counts"],
            "role_counts": b2_report["task_frame"]["role_counts"],
            "task_family_counts": b2_report["task_frame"]["task_family_counts"],
            "interaction_counts": b2_report["task_frame"]["interaction_counts"],
            "oracle_kind_counts": b2_report["task_frame"]["oracle_kind_counts"],
            "component_eligible_counts": b2_report["task_frame"]["component_eligible_counts"],
            "holdout_rules": dict(B21_HOLDOUT_RULES),
        },
        "lifecycle_matrix": {
            **copy.deepcopy(b2_report["lifecycle_matrix"]),
            "logical_record_count": b2.B2_TOTAL_RECORDS,
            "context_record_count": (
                b2.B2_ONE_SHOT_RECORDS
                + b2.B2_TWO_STEP_TASK_COUNT * len(b2.B2_ADAPTER_IDS) * len(b2.B2_REPETITIONS)
            ),
            "support_opportunity_count": (
                b2.B2_TWO_STEP_TASK_COUNT * len(b2.B2_ADAPTER_IDS) * len(b2.B2_REPETITIONS)
            ),
            "terminal_support_record_count_range_inclusive": [0, 288],
            "adapter_execution_record_count_range_inclusive": [1152, 1440],
        },
        "randomization": {
            **copy.deepcopy(b2_report["randomization"]),
            "b21_schedule_digest": b21_execution_schedule_digest(),
            "schedule_inherited_but_applied_to_a_fresh_holdout_frame": True,
        },
        "two_step_lineage": dict(B21_LINEAGE_POLICY),
        "parent_unavailable_terminal": dict(B21_PARENT_UNAVAILABLE_POLICY),
        "fairness": dict(B21_FAIRNESS_POLICY),
        "metric_contract": metric_contract,
        "hard_gates": dict(B21_HARD_GATES),
        "promotion_contract": promotion,
        "tie_policy": copy.deepcopy(b2_report["tie_policy"]),
        "privacy_publication": dict(B21_PUBLICATION_POLICY),
        "forbidden_adaptations": list(B21_FORBIDDEN_ADAPTATIONS),
        "source_locks": {
            "b21_spec_digest": b21_spec_digest(),
            "b21_source_bundle_digest": b21_source_bundle_digest(),
            "line_endings_normalized_for_cross_platform_source_digest": True,
            "runtime_bundle_must_be_single_and_frozen_before_execution": True,
            "mixed_runtime_bundles_in_one_tournament_forbidden": True,
        },
        "implementation_readiness": {
            "fresh_holdout_exclusion_overlay_implemented": True,
            "b2_and_preflight_repository_nonoverlap_enforced": True,
            "same_arm_own_parent_runner_implemented": True,
            "parent_unavailable_terminal_record_implemented": True,
            "logical_1440_cell_gate_implemented": True,
            "isolated_scorer_and_aggregate_publication_implemented": True,
            "public_result_privacy_and_digest_validator_implemented": True,
            "final_holdout_not_materialized": True,
        },
        "next_authorized_action": (
            "prepare a new 12-repository 48-task holdout frame excluding every B2 and "
            "real-preflight repository, audit only aggregate margins, then freeze the "
            "private manifests and one runtime bundle before any final holdout arm output"
        ),
    }


def build_report() -> dict[str, Any]:
    report = _build_report_without_digest()
    report["protocol_digest"] = _prefixed_digest("b21protocol_", report)
    return report


def _diff_values(expected: Any, actual: Any, path: str = "report") -> list[str]:
    if type(expected) is not type(actual):
        return [f"{path}: type drift"]
    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        errors = [f"{path}: key drift"] if expected_keys != actual_keys else []
        for key in sorted(expected_keys & actual_keys):
            errors.extend(_diff_values(expected[key], actual[key], f"{path}.{key}"))
        return errors
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"{path}: list length drift"]
        errors: list[str] = []
        for index, (left, right) in enumerate(zip(expected, actual)):
            errors.extend(_diff_values(left, right, f"{path}[{index}]"))
        return errors
    return [] if expected == actual else [f"{path}: value drift"]


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be an object"]
    errors = list(b2.scan_public_report(report))
    errors.extend(validate_parent_b2_closeout())
    errors.extend(_diff_values(build_report(), report))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    slots = b2.build_task_slots()
    schedule = b2.build_execution_schedule(slots)
    checks = [
        ("parent_b2_closeout_valid", not validate_parent_b2_closeout()),
        ("inherited_task_frame_valid", not b2.validate_task_slots(slots)),
        ("inherited_schedule_valid", not b2.validate_execution_schedule(schedule, slots)),
        ("independent_n_48", len(slots) == 48),
        ("logical_records_1440", b2.B2_TOTAL_RECORDS == 1440),
        ("index_builds_288", b2.B2_INDEX_BUILD_COUNT == 288),
        ("fresh_repo_slugs_required", B21_HOLDOUT_RULES["all_repository_slugs_absent_from_b2_frame"]),
        ("cross_arm_parent_equality_disabled", not B21_LINEAGE_POLICY["cross_arm_parent_path_equality_required"]),
        ("same_arm_parent_required", B21_LINEAGE_POLICY["support_parent_scope"] == "same_arm_same_task_same_repetition_same_episode"),
        ("terminal_support_is_quality_failure", B21_PARENT_UNAVAILABLE_POLICY["terminal_counts_as_task_failure"]),
        ("terminal_support_does_not_abort", B21_PARENT_UNAVAILABLE_POLICY["terminal_is_not_an_infrastructure_failure"]),
        ("no_interim_looks", _build_report_without_digest()["experimental_design"]["interim_looks"] == 0),
        ("base_report_valid", not validate_report(build_report())),
    ]
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {
        "status": "passed",
        "checks_passed": len(checks),
        "checks_total": len(checks),
        "task_slots": len(slots),
        "schedule_rows": len(schedule),
        "logical_records": b2.B2_TOTAL_RECORDS,
    }


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[tuple[str, bool]] = []

    def rejected(name: str, mutator: Any) -> None:
        mutated = copy.deepcopy(base)
        mutator(mutated)
        checks.append((name, bool(validate_report(mutated))))

    rejected("unknown_key_rejected", lambda report: report.__setitem__("extra", True))
    rejected("status_drift_rejected", lambda report: report.__setitem__("status", "drift"))
    rejected("parent_checkpoint_drift_rejected", lambda report: report["parent_b2_lock"].__setitem__("source_checkpoint", "drift"))
    rejected("b2_result_reuse_rejected", lambda report: report["parent_b2_lock"].__setitem__("b2_result_reused", True))
    rejected("repo_overlap_rejected", lambda report: report["holdout_frame"]["holdout_rules"].__setitem__("all_repository_slugs_absent_from_b2_frame", False))
    rejected("common_parent_rejected", lambda report: report["two_step_lineage"].__setitem__("cross_arm_parent_path_equality_required", True))
    rejected("cross_arm_substitution_rejected", lambda report: report["two_step_lineage"].__setitem__("cross_arm_parent_substitution_forbidden", False))
    rejected("terminal_drop_rejected", lambda report: report["parent_unavailable_terminal"].__setitem__("logical_support_record_still_required", False))
    rejected("terminal_success_rejected", lambda report: report["parent_unavailable_terminal"].__setitem__("terminal_counts_as_task_failure", False))
    rejected("matrix_drift_rejected", lambda report: report["lifecycle_matrix"].__setitem__("logical_record_count", 1439))
    rejected("interim_look_rejected", lambda report: report["experimental_design"].__setitem__("interim_looks", 1))
    rejected("private_digest_public_rejected", lambda report: report["privacy_publication"].__setitem__("private_manifest_or_freeze_digest_public", True))
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
        raise SystemExit("refusing to write invalid B2.1 report: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_report(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze the B2.1 own-parent protocol")
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
    report = load_report(path)
    errors = validate_report(report)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    label = "Drift check" if args.check_drift else "Validation"
    print(f"{label} passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B21_SCHEMA_VERSION",
    "B21_REPORT_SCHEMA_VERSION",
    "B21_SOURCE_BUNDLE_PATHS",
    "B21_HOLDOUT_RULES",
    "B21_LINEAGE_POLICY",
    "B21_PARENT_UNAVAILABLE_POLICY",
    "B21_FAIRNESS_POLICY",
    "B21_SCORING_OVERRIDES",
    "B21_HARD_GATES",
    "B21_FORBIDDEN_ADAPTATIONS",
    "B21_PUBLICATION_POLICY",
    "b21_task_frame_digest",
    "b21_execution_schedule_digest",
    "b21_source_bundle_digest",
    "b21_spec_digest",
    "validate_parent_b2_closeout",
    "build_report",
    "validate_report",
    "run_self_test",
    "run_fault_test",
]
