#!/usr/bin/env python3
"""Preregister the fresh B3 product tournament design.

B3 is a future experiment.  It does not reopen, retry, score, rank, or
reinterpret B2.5.  This public module contains no private holdout material and
grants no execution authority.

The design repairs three issues before any new treatment output exists:

* the repository is the dependence/generalization cluster, so 48 tasks are not
  described as 48 independent repositories;
* six Williams sequences balance both arm position and first-order predecessor
  effects instead of relying only on cyclic position balance; and
* the repeatability gate and scorer share one complete-plan canonicalizer that
  retains target cardinality because it controls same-arm support routing.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2  # noqa: E402
import product_bakeoff_b21_protocol as b21  # noqa: E402
import product_bakeoff_b3_repeatability as b3r  # noqa: E402
import product_bakeoff_terminal_archive as archive  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_protocol"
    / "product_bakeoff_b3_protocol_report.json"
)

B25_FAILURE_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b25"
    / "product_bakeoff_b25_failed_closed_aggregate.json"
)
DETERMINISM_REPAIR_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_determinism_repair"
    / "product_bakeoff_postcloseout_determinism_repair.json"
)
DETERMINISM_SCALE_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_determinism_linux_scale"
    / "product_bakeoff_postcloseout_determinism_linux_scale.json"
)

B3_SCHEMA_VERSION = "product_bakeoff_b3_protocol.v1"
B3_REPORT_SCHEMA_VERSION = "product_bakeoff_b3_protocol_report.v1"
B3_PHASE = "product_bakeoff_b3_fresh_cluster_aware_williams_tournament_protocol"
B3_STATUS = (
    "product_bakeoff_b3_protocol_frozen_no_runtime_no_holdout_"
    "no_execution_no_result"
)
B3_CLAIM_LEVEL = "future_preregistered_design_and_synthetic_selftest_only"
B3_DATE = "2026-07-17"

B3_PARENT_B25_FAILURE_SHA256 = (
    "8901b1cfaf7f47f12671e26e7976d1795747ee763128a31f43a75508113e1834"
)
B3_PARENT_B25_FAILURE_DIGEST = (
    "b25failure_012f59fc4d7d717b4f1d4f0da5513430637d4a6cc6eaf8a326a35adc339302fd"
)
B3_PARENT_DETERMINISM_REPAIR_SHA256 = (
    "bfce93f09664f75e4700978a9acbf10f4e8a995155b7426e765699994fca4949"
)
B3_PARENT_DETERMINISM_REPAIR_DIGEST = (
    "detrepair_b05b51b37631baa5e7d744be511e3368e4e56bab4f37a0a3cfb8748b853cedeb"
)
B3_PARENT_DETERMINISM_SCALE_SHA256 = (
    "830a2e2f727d8668d0af5fca8e513323319349edc93d77022c77a9b080070bf3"
)
B3_PARENT_DETERMINISM_SCALE_DIGEST = (
    "detlinux_b82d0262881b5f2623b866e3f9ea504e68cc591b1c23ac43c20349816af7bcfc"
)

B3_PARENT_B2_SPEC_DIGEST = "b2spec_358b77c924fbe3f1"
B3_PARENT_B2_TASK_SLOT_DIGEST = (
    "b2slots_a92720057d2f931e1f84c2b3d49af5a4e2efe08661d7c49e375e8835a80149ff"
)
B3_PARENT_B21_SPEC_DIGEST = "b21spec_3d656619189a7531"
B3_PARENT_B21_SCHEDULE_DIGEST = (
    "b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3"
)

B3_SOURCE_BUNDLE_PATHS = (
    "Cargo.lock",
    "crates/openlocus-cli/src/bakeoff_query.rs",
    "crates/openlocus-cli/src/lib.rs",
    "crates/openlocus-ast/src/symbol.rs",
    "crates/openlocus-context/src/plan.rs",
    "crates/openlocus-graph/src/graph.rs",
    "crates/openlocus-index/src/persistent.rs",
    "crates/openlocus-retrieval/src/bm25_search.rs",
    "crates/openlocus-retrieval/src/regex_search.rs",
    "crates/openlocus-retrieval/src/rrf.rs",
    "crates/openlocus-retrieval/src/symbol_search.rs",
    "eval/product_bakeoff_contract.py",
    "eval/product_bakeoff_b2_protocol.py",
    "eval/product_bakeoff_b2_runner.py",
    "eval/product_bakeoff_b2_scorer.py",
    "eval/product_bakeoff_b21_protocol.py",
    "eval/product_bakeoff_b21_runner.py",
    "eval/product_bakeoff_b21_scorer.py",
    "eval/product_bakeoff_b3_repeatability.py",
    "eval/product_bakeoff_b3_protocol.py",
    "eval/product_bakeoff_terminal_archive.py",
    ".github/workflows/product-bakeoff-b3-protocol.yml",
)

B3_RANDOMIZATION_SEED = "openlocus-b3-20260717-williams6-splitplot-v1"
B3_RANDOMIZATION_POLICY = (
    "seeded_repo_order_plus_williams6_position_and_first_order_balance_v1"
)
B3_SEQUENCE_COEFFICIENTS = {
    "language": 2,
    "size_band": 1,
    "role": 1,
    "repetition": 2,
}

B3_HOLDOUT_RULES = {
    "repository_snapshot_count": b2.B2_REPO_SLOT_COUNT,
    "logical_task_count": b2.B2_TASK_COUNT,
    "tasks_per_repository_snapshot": b2.B2_TASKS_PER_REPO_SLOT,
    "language_count": len(b2.B2_LANGUAGES),
    "size_band_count": len(b2.B2_SIZE_BANDS),
    "task_roles_per_repository": len(b2.B2_TASK_ROLES),
    "historical_repository_frame_labels": ["b2", "b21", "b24", "b25"],
    "historical_repository_count": 48,
    "all_repository_slugs_absent_from_all_historical_frames": True,
    "all_repository_identity_commit_pairs_absent_from_all_historical_frames": True,
    "all_real_preflight_runtime_and_scale_repositories_excluded": True,
    "all_synthetic_qualification_sources_excluded": True,
    "all_task_query_and_oracle_rows_new": True,
    "all_b25_treatment_output_reuse_forbidden": True,
    "b25_private_holdout_and_launch_authorization_reuse_forbidden": True,
    "task_and_oracle_authoring_complete_before_any_treatment_output": True,
    "candidate_failover_complete_before_private_freeze": True,
    "no_task_add_drop_replace_after_private_freeze": True,
    "no_query_or_oracle_edit_after_private_freeze": True,
    "private_holdout_identity_or_digest_public": False,
}

B3_EXPERIMENTAL_DESIGN = {
    "design_type": (
        "complete_within_task_six_treatment_blocks_with_repository_cluster_"
        "and_split_plot_runtime_lifecycle"
    ),
    "treatment_application_unit": "logical_task_within_repository_snapshot",
    "primary_quality_analysis_unit": "logical_task",
    "logical_task_count": b2.B2_TASK_COUNT,
    "repository_dependence_cluster": "frozen_repository_snapshot",
    "repository_cluster_count": b2.B2_REPO_SLOT_COUNT,
    "tasks_per_repository_cluster": b2.B2_TASKS_PER_REPO_SLOT,
    "forty_eight_tasks_are_not_claimed_as_independent_repositories": True,
    "repository_snapshots_are_stratified_fixed_frame_not_random_population_sample": True,
    "complete_six_treatment_block_within_every_task": True,
    "same_task_receives_all_treatments": True,
    "cache_and_repetition_are_technical_repeated_measures": True,
    "technical_repetition_count": len(b2.B2_REPETITIONS),
    "one_cold_plus_three_warm_observations_per_task_treatment": True,
    "repository_treatment_repetition_index_is_split_plot_whole_plot": True,
    "quality_scored_once_per_task_after_repeatability_gate": True,
    "resource_observations_remain_repeated_measurements": True,
    "primary_claim_scope": "fixed_frozen_frame_product_decision",
    "population_hypothesis_claim": False,
    "unadjusted_task_independence_p_values_forbidden": True,
    "interim_quality_looks": 0,
    "adaptive_arm_elimination_forbidden": True,
    "single_final_quality_analysis_only": True,
    "tie_policy": copy.deepcopy(b2.B2_TIE_POLICY),
}

B3_ANALYSIS_RULES = {
    "quality_metrics_and_thresholds_inherited_from_b2": True,
    "same_arm_own_parent_lineage_inherited_from_b21": True,
    "paired_task_level_quality_comparison": True,
    "repository_cluster_sensitivity_is_descriptive_only": True,
    "technical_repetitions_do_not_increase_quality_sample_size": True,
    "quality_and_resource_ranks_reported_separately": True,
    "exact_equal_quality_vectors_share_competition_rank": True,
    "exact_equal_resource_vectors_share_competition_rank": True,
    "forced_unique_winner": False,
    "decision_equivalent_arms_may_all_advance": True,
    "no_opaque_single_composite_score": True,
    "no_post_output_metric_threshold_weight_or_order_change": True,
}

B3_REPEATABILITY_BINDING = {
    "policy_version": b3r.B3_REPEATABILITY_POLICY_VERSION,
    "policy_digest": b3r.repeatability_policy_digest(),
    "gate_entry_point": "product_bakeoff_b3_repeatability.repeatability_gate",
    "scorer_entry_point": (
        "product_bakeoff_b3_repeatability.canonicalize_for_scoring"
    ),
    "shared_internal_canonicalization_core": True,
    "complete_expected_group_set_required": True,
    "exact_repetition_and_cache_signatures_required": True,
    "target_cardinality_class_retained_for_support_routing": True,
    "diagnostic_hash_drift_recorded_privately_but_not_quality_gate_failure": True,
    "source_currentness_scoreability_lineage_fairness_provider_are_separate_gates": True,
}

B3_EXECUTION_BOUNDARY = {
    "private_launch_release_alone_consumes_attempt": False,
    "attempt_boundary": "first_durable_treatment_observation",
    "pre_boundary_zero_output_recovery_allowed": True,
    "pre_boundary_recovery_requires_audited_zero_treatment_record_or_output": True,
    "pre_boundary_recovery_requires_no_operator_visible_treatment_payload": True,
    "pre_boundary_recovery_requires_unchanged_frozen_holdout_and_protocol": True,
    "pre_boundary_recovery_discards_and_recreates_all_working_state": True,
    "pre_boundary_runner_replacement_requires_new_public_qualification_and_readiness": True,
    "maximum_attempts_with_any_durable_treatment_observation": 1,
    "post_boundary_complete_restart_allowed": False,
    "post_boundary_resume_after_process_or_machine_loss_allowed": False,
    "post_boundary_selective_cell_retry_allowed": False,
    "missing_cell_imputation_allowed": False,
    "completed_cell_recomputation_allowed": False,
    "post_boundary_failure_closes_without_result": True,
    "intermediate_quality_resource_or_ranking_metrics_visible": False,
}

B3_HARD_GATES = {
    "terminal_b25_closeout_lock_valid": True,
    "determinism_repair_and_linux_scale_locks_valid": True,
    "fresh_private_holdout_and_oracle_frozen_before_execution": True,
    "exact_runtime_and_source_bundle_qualified_before_authoring": True,
    "complete_frozen_execution_schedule": True,
    "all_normal_and_terminal_records_valid_and_scoreable": True,
    "source_currentness_and_workspace_strictness": True,
    "exact_split_plot_lifecycle": True,
    "shared_score_and_routing_repeatability_policy": True,
    "same_arm_own_parent_lineage": True,
    "cross_arm_static_fairness": True,
    "provider_network_call_count_zero": True,
    "scorer_and_oracle_unloaded_until_all_pre_score_gates_pass": True,
}

B3_PUBLICATION_POLICY = {
    "publication_level": "aggregate_only",
    "protocol_schedule_and_policy_digests_public": True,
    "private_holdout_manifest_or_freeze_digest_public": False,
    "repository_candidate_task_query_or_oracle_identity_public": False,
    "source_location_range_excerpt_or_raw_output_public": False,
    "per_task_per_repository_or_per_cell_empirical_detail_public": False,
    "intermediate_arm_quality_resource_or_ranking_metric_public": False,
    "private_runner_identity_endpoint_or_working_location_public": False,
    "provider_payload_secret_or_credential_public": False,
    "final_arm_aggregate_public_only_after_all_gates": True,
}

B3_IMPLEMENTATION_READINESS = {
    "protocol_module_implemented": True,
    "shared_repeatability_module_implemented": True,
    "synthetic_schedule_and_fault_tests_implemented": True,
    "b3_runner_integrated": False,
    "b3_scorer_integrated": False,
    "public_synthetic_runtime_qualification_complete": False,
    "exact_linux_runtime_qualified": False,
    "private_holdout_authored": False,
    "private_holdout_frozen": False,
    "public_readiness_committed_and_ci_green": False,
    "private_launch_authorization_created": False,
    "future_tournament_execution_authorized": False,
    "treatment_output_exists": False,
    "tournament_result_exists": False,
}

B3_NEXT_ACTION = (
    "Keep the server off while implementing the B3 runner/scorer integration "
    "and public synthetic qualification locally. After those sources and "
    "fault tests are frozen and CI-green, qualify the exact Linux runtime, "
    "then author a fresh private holdout. Do not reuse any B2.5 treatment "
    "output, private holdout, or launch authorization."
)


class B3ProtocolError(ValueError):
    """Fail-closed error for the public B3 preregistration."""


@dataclass(frozen=True)
class B3ScheduleRow:
    slot_id: str
    repo_slot: str
    repetition: int
    cache_state: str
    task_position: int
    sequence_index: int
    arm_order: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "repo_slot": self.repo_slot,
            "repetition": self.repetition,
            "cache_state": self.cache_state,
            "task_position": self.task_position,
            "sequence_index": self.sequence_index,
            "arm_order": list(self.arm_order),
        }


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _prefixed_digest(prefix: str, value: Any, *, length: int | None = None) -> str:
    digest = hashlib.sha256(_canonical(value)).hexdigest()
    return prefix + (digest if length is None else digest[:length])


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B3ProtocolError("parent public artifact must be an object")
    return value


def _rotate(values: Sequence[str], offset: int) -> tuple[str, ...]:
    items = tuple(values)
    if not items:
        return ()
    point = offset % len(items)
    return items[point:] + items[:point]


def _seeded_order(values: Iterable[str], label: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            values,
            key=lambda value: hashlib.sha256(
                f"{B3_RANDOMIZATION_SEED}:{label}:{value}".encode("utf-8")
            ).hexdigest(),
        )
    )


def build_williams_index_sequences(
    treatment_count: int = len(b2.B2_ADAPTER_IDS),
) -> tuple[tuple[int, ...], ...]:
    if treatment_count < 2 or treatment_count % 2:
        raise B3ProtocolError("Williams design requires an even treatment count")
    base = [0]
    for offset in range(1, treatment_count):
        if offset % 2:
            base.append((offset + 1) // 2)
        else:
            base.append(treatment_count - offset // 2)
    return tuple(
        tuple((value + row) % treatment_count for value in base)
        for row in range(treatment_count)
    )


B3_WILLIAMS_INDEX_SEQUENCES = build_williams_index_sequences()


def validate_williams_index_sequences(
    sequences: Sequence[Sequence[int]] = B3_WILLIAMS_INDEX_SEQUENCES,
) -> list[str]:
    errors: list[str] = []
    treatment_count = len(b2.B2_ADAPTER_IDS)
    if len(sequences) != treatment_count:
        errors.append("Williams sequence count drifted")
    expected = set(range(treatment_count))
    for index, sequence in enumerate(sequences):
        if len(sequence) != treatment_count or set(sequence) != expected:
            errors.append(f"Williams row {index} is not a permutation")
    position_counts: Counter[tuple[int, int]] = Counter()
    predecessor_counts: Counter[tuple[int, int]] = Counter()
    for sequence in sequences:
        for position, treatment in enumerate(sequence):
            position_counts[(treatment, position)] += 1
        predecessor_counts.update(zip(sequence, sequence[1:]))
    for treatment in expected:
        for position in expected:
            if position_counts[(treatment, position)] != 1:
                errors.append("Williams position balance drifted")
    for first in expected:
        for second in expected:
            observed = predecessor_counts[(first, second)]
            expected_count = 0 if first == second else 1
            if observed != expected_count:
                errors.append("Williams first-order carryover balance drifted")
    return sorted(set(errors))


def build_execution_schedule(
    slots: Sequence[b2.B2TaskSlot] | None = None,
) -> tuple[B3ScheduleRow, ...]:
    task_slots = tuple(slots or b2.build_task_slots())
    by_repo_role: dict[str, dict[str, b2.B2TaskSlot]] = defaultdict(dict)
    for slot in task_slots:
        by_repo_role[slot.repo_slot][slot.role] = slot

    stable_repo_slots = tuple(sorted(by_repo_role))
    stable_repo_index = {
        repo_slot: index for index, repo_slot in enumerate(stable_repo_slots)
    }
    language_index = {value: index for index, value in enumerate(b2.B2_LANGUAGES)}
    size_index = {value: index for index, value in enumerate(b2.B2_SIZE_BANDS)}
    role_index = {value: index for index, value in enumerate(b2.B2_TASK_ROLES)}
    base_arm_order = _seeded_order(b2.B2_ADAPTER_IDS, "base-arm-order")
    rows: list[B3ScheduleRow] = []

    for repetition in b2.B2_REPETITIONS:
        repo_order = _seeded_order(
            stable_repo_slots, f"repo-order-repetition-{repetition}"
        )
        for repo_slot in repo_order:
            repo_index = stable_repo_index[repo_slot]
            cold_role_index = (repo_index + repetition - 1) % len(b2.B2_TASK_ROLES)
            role_order = _rotate(b2.B2_TASK_ROLES, cold_role_index)
            for task_position, role in enumerate(role_order, start=1):
                slot = by_repo_role[repo_slot][role]
                sequence_index = (
                    B3_SEQUENCE_COEFFICIENTS["language"]
                    * language_index[slot.language]
                    + B3_SEQUENCE_COEFFICIENTS["size_band"]
                    * size_index[slot.size_band]
                    + B3_SEQUENCE_COEFFICIENTS["role"] * role_index[slot.role]
                    + B3_SEQUENCE_COEFFICIENTS["repetition"] * (repetition - 1)
                ) % len(B3_WILLIAMS_INDEX_SEQUENCES)
                arm_order = tuple(
                    base_arm_order[index]
                    for index in B3_WILLIAMS_INDEX_SEQUENCES[sequence_index]
                )
                rows.append(
                    B3ScheduleRow(
                        slot_id=slot.slot_id,
                        repo_slot=repo_slot,
                        repetition=repetition,
                        cache_state="cold" if task_position == 1 else "warm",
                        task_position=task_position,
                        sequence_index=sequence_index,
                        arm_order=arm_order,
                    )
                )
    return tuple(rows)


def validate_execution_schedule(
    rows: Sequence[B3ScheduleRow],
    slots: Sequence[b2.B2TaskSlot] | None = None,
) -> list[str]:
    errors: list[str] = []
    task_slots = tuple(slots or b2.build_task_slots())
    if b2.validate_task_slots(task_slots):
        errors.append("inherited task-slot frame is invalid")
    if validate_williams_index_sequences():
        errors.append("Williams sequence basis is invalid")
    slot_by_id = {slot.slot_id: slot for slot in task_slots}
    expected_rows = b2.B2_TASK_COUNT * len(b2.B2_REPETITIONS)
    if len(rows) != expected_rows:
        errors.append(f"schedule row count must be {expected_rows}")
    keys = [(row.slot_id, row.repetition) for row in rows]
    if len(set(keys)) != len(keys):
        errors.append("schedule slot/repetition keys must be unique")

    per_slot_cache: dict[str, Counter[str]] = defaultdict(Counter)
    per_repo_rep_cache: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    sequence_counts: Counter[int] = Counter()
    sequence_by_rep: Counter[tuple[int, int]] = Counter()
    sequence_by_language: Counter[tuple[str, int]] = Counter()
    sequence_by_size: Counter[tuple[str, int]] = Counter()
    sequence_by_role: Counter[tuple[str, int]] = Counter()
    position_counts: Counter[tuple[str, int]] = Counter()
    position_by_rep: Counter[tuple[int, str, int]] = Counter()
    position_by_size: Counter[tuple[str, str, int]] = Counter()
    position_by_role: Counter[tuple[str, str, int]] = Counter()
    predecessor_counts: Counter[tuple[str, str]] = Counter()
    predecessor_by_rep: Counter[tuple[int, str, str]] = Counter()
    predecessor_by_size: Counter[tuple[str, str, str]] = Counter()
    predecessor_by_role: Counter[tuple[str, str, str]] = Counter()
    record_count = 0

    for row in rows:
        slot = slot_by_id.get(row.slot_id)
        if slot is None:
            errors.append(f"unknown scheduled slot: {row.slot_id}")
            continue
        if row.repo_slot != slot.repo_slot:
            errors.append(f"repo slot mismatch: {row.slot_id}")
        if row.repetition not in b2.B2_REPETITIONS:
            errors.append(f"invalid repetition: {row.repetition}")
        if row.cache_state not in {"cold", "warm"}:
            errors.append(f"invalid cache state: {row.cache_state}")
        if row.task_position not in {1, 2, 3, 4}:
            errors.append(f"invalid task position: {row.task_position}")
        if (row.cache_state == "cold") != (row.task_position == 1):
            errors.append(f"cold/task-position mismatch: {row.slot_id}")
        if row.sequence_index not in range(len(B3_WILLIAMS_INDEX_SEQUENCES)):
            errors.append(f"invalid Williams sequence: {row.slot_id}")
        if (
            len(row.arm_order) != len(b2.B2_ADAPTER_IDS)
            or set(row.arm_order) != set(b2.B2_ADAPTER_IDS)
        ):
            errors.append(f"arm order is not an exact permutation: {row.slot_id}")
        per_slot_cache[row.slot_id][row.cache_state] += 1
        per_repo_rep_cache[(row.repo_slot, row.repetition)][row.cache_state] += 1
        sequence_counts[row.sequence_index] += 1
        sequence_by_rep[(row.repetition, row.sequence_index)] += 1
        sequence_by_language[(slot.language, row.sequence_index)] += 1
        sequence_by_size[(slot.size_band, row.sequence_index)] += 1
        sequence_by_role[(slot.role, row.sequence_index)] += 1
        for position, adapter_id in enumerate(row.arm_order, start=1):
            position_counts[(adapter_id, position)] += 1
            position_by_rep[(row.repetition, adapter_id, position)] += 1
            position_by_size[(slot.size_band, adapter_id, position)] += 1
            position_by_role[(slot.role, adapter_id, position)] += 1
        for first, second in zip(row.arm_order, row.arm_order[1:]):
            predecessor_counts[(first, second)] += 1
            predecessor_by_rep[(row.repetition, first, second)] += 1
            predecessor_by_size[(slot.size_band, first, second)] += 1
            predecessor_by_role[(slot.role, first, second)] += 1
        record_count += len(b2.B2_ADAPTER_IDS) * (
            2 if slot.interaction_mode == "two_step" else 1
        )

    for slot in task_slots:
        if per_slot_cache[slot.slot_id] != Counter({"cold": 1, "warm": 3}):
            errors.append(f"cold/warm rotation drift: {slot.slot_id}")
    for repo_slot in sorted({slot.repo_slot for slot in task_slots}):
        for repetition in b2.B2_REPETITIONS:
            if per_repo_rep_cache[(repo_slot, repetition)] != Counter(
                {"cold": 1, "warm": 3}
            ):
                errors.append(f"repo split-plot cache drift: {repo_slot}/{repetition}")

    sequence_count = len(B3_WILLIAMS_INDEX_SEQUENCES)
    for sequence_index in range(sequence_count):
        if sequence_counts[sequence_index] != expected_rows // sequence_count:
            errors.append(f"global Williams sequence imbalance: {sequence_index}")
        for repetition in b2.B2_REPETITIONS:
            if sequence_by_rep[(repetition, sequence_index)] != 8:
                errors.append(
                    f"per-repetition Williams imbalance: {repetition}/{sequence_index}"
                )
        for size_band in b2.B2_SIZE_BANDS:
            if sequence_by_size[(size_band, sequence_index)] != 8:
                errors.append(
                    f"size Williams imbalance: {size_band}/{sequence_index}"
                )
        for role in b2.B2_TASK_ROLES:
            if sequence_by_role[(role, sequence_index)] != 8:
                errors.append(f"role Williams imbalance: {role}/{sequence_index}")
    for language in b2.B2_LANGUAGES:
        values = [
            sequence_by_language[(language, sequence_index)]
            for sequence_index in range(sequence_count)
        ]
        if min(values) < 10 or max(values) > 12:
            errors.append(f"language Williams imbalance: {language}")

    global_position_expected = expected_rows // len(b2.B2_ADAPTER_IDS)
    for adapter_id in b2.B2_ADAPTER_IDS:
        for position in range(1, len(b2.B2_ADAPTER_IDS) + 1):
            if position_counts[(adapter_id, position)] != global_position_expected:
                errors.append(f"global arm-position imbalance: {adapter_id}/{position}")
            for repetition in b2.B2_REPETITIONS:
                if position_by_rep[(repetition, adapter_id, position)] != 8:
                    errors.append(
                        f"repetition arm-position imbalance: "
                        f"{repetition}/{adapter_id}/{position}"
                    )
            for size_band in b2.B2_SIZE_BANDS:
                if position_by_size[(size_band, adapter_id, position)] != 8:
                    errors.append(
                        f"size arm-position imbalance: "
                        f"{size_band}/{adapter_id}/{position}"
                    )
            for role in b2.B2_TASK_ROLES:
                if position_by_role[(role, adapter_id, position)] != 8:
                    errors.append(
                        f"role arm-position imbalance: {role}/{adapter_id}/{position}"
                    )

    predecessor_global_expected = expected_rows // len(b2.B2_ADAPTER_IDS)
    for first in b2.B2_ADAPTER_IDS:
        for second in b2.B2_ADAPTER_IDS:
            expected = 0 if first == second else predecessor_global_expected
            if predecessor_counts[(first, second)] != expected:
                errors.append(f"global predecessor imbalance: {first}/{second}")
            for repetition in b2.B2_REPETITIONS:
                per_rep_expected = 0 if first == second else 8
                if predecessor_by_rep[(repetition, first, second)] != per_rep_expected:
                    errors.append(
                        f"repetition predecessor imbalance: {repetition}/{first}/{second}"
                    )
            for size_band in b2.B2_SIZE_BANDS:
                per_size_expected = 0 if first == second else 8
                if predecessor_by_size[(size_band, first, second)] != per_size_expected:
                    errors.append(
                        f"size predecessor imbalance: {size_band}/{first}/{second}"
                    )
            for role in b2.B2_TASK_ROLES:
                per_role_expected = 0 if first == second else 8
                if predecessor_by_role[(role, first, second)] != per_role_expected:
                    errors.append(
                        f"role predecessor imbalance: {role}/{first}/{second}"
                    )

    if record_count != b2.B2_TOTAL_RECORDS:
        errors.append(f"schedule record count must be {b2.B2_TOTAL_RECORDS}")
    return sorted(set(errors))


def execution_schedule_digest(
    rows: Sequence[B3ScheduleRow] | None = None,
) -> str:
    schedule = tuple(rows or build_execution_schedule())
    return _prefixed_digest("b3sched_", [row.to_dict() for row in schedule])


def build_expected_observation_plan(
    rows: Sequence[B3ScheduleRow] | None = None,
    slots: Sequence[b2.B2TaskSlot] | None = None,
) -> dict[b3r.GroupKey, tuple[b3r.ObservationSignature, ...]]:
    task_slots = tuple(slots or b2.build_task_slots())
    schedule = tuple(rows or build_execution_schedule(task_slots))
    slot_by_id = {slot.slot_id: slot for slot in task_slots}
    groups: dict[b3r.GroupKey, list[b3r.ObservationSignature]] = defaultdict(list)
    for row in schedule:
        slot = slot_by_id[row.slot_id]
        for adapter_id in row.arm_order:
            groups[(adapter_id, row.slot_id, "context")].append(
                (row.repetition, row.cache_state)
            )
            if slot.interaction_mode == "two_step":
                groups[(adapter_id, row.slot_id, "support")].append(
                    (row.repetition, row.cache_state)
                )
    return {key: tuple(sorted(values)) for key, values in sorted(groups.items())}


def expected_observation_plan_digest() -> str:
    rows = [
        {
            "adapter_id": key[0],
            "slot_id": key[1],
            "operation": key[2],
            "observations": [list(value) for value in values],
        }
        for key, values in build_expected_observation_plan().items()
    ]
    return _prefixed_digest("b3repeatplan_", rows)


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in B3_SOURCE_BUNDLE_PATHS:
        if rel in seen:
            raise B3ProtocolError(f"duplicate B3 source bundle entry: {rel}")
        seen.add(rel)
        source = root / rel
        if source.is_symlink() or not source.is_file():
            raise B3ProtocolError(f"missing or unsafe B3 source bundle file: {rel}")
        resolved = source.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise B3ProtocolError("B3 source bundle escapes repository") from exc
        raw = source.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "source": rel,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def source_bundle_digest(repo_root: Path | None = None) -> str:
    return _prefixed_digest("b3src_", _normalized_source_rows(repo_root))


def validate_parent_locks(repo_root: Path | None = None) -> list[str]:
    root = (repo_root or REPO).resolve()
    errors: list[str] = []
    try:
        if archive.validate_archive("b25"):
            errors.append("B2.5 terminal archive validation failed")
    except Exception as exc:  # noqa: BLE001 - public type-only failure
        errors.append(f"B2.5 terminal archive unreadable: {type(exc).__name__}")

    locks = (
        (
            root / B25_FAILURE_PATH.relative_to(REPO),
            B3_PARENT_B25_FAILURE_SHA256,
            "product_bakeoff_b25_failed_closed_aggregate.v1",
            "product_bakeoff_b25_execution_failed_closed_no_result",
            "failure_aggregate_digest",
            B3_PARENT_B25_FAILURE_DIGEST,
        ),
        (
            root / DETERMINISM_REPAIR_PATH.relative_to(REPO),
            B3_PARENT_DETERMINISM_REPAIR_SHA256,
            "product_bakeoff_postcloseout_determinism_repair.v1",
            "product_bakeoff_postcloseout_determinism_repair_complete_no_b25_result_change",
            "repair_digest",
            B3_PARENT_DETERMINISM_REPAIR_DIGEST,
        ),
        (
            root / DETERMINISM_SCALE_PATH.relative_to(REPO),
            B3_PARENT_DETERMINISM_SCALE_SHA256,
            "product_bakeoff_postcloseout_determinism_linux_scale.v1",
            "product_bakeoff_postcloseout_determinism_linux_scale_complete_no_tournament_authorization",
            "scale_digest",
            B3_PARENT_DETERMINISM_SCALE_DIGEST,
        ),
    )
    for artifact, sha256, schema, status, digest_key, digest in locks:
        try:
            if artifact.is_symlink() or not artifact.is_file():
                errors.append(f"missing parent public artifact: {artifact.name}")
                continue
            if _file_sha256(artifact) != sha256:
                errors.append(f"parent artifact bytes drifted: {artifact.name}")
                continue
            value = _load_json(artifact)
            if value.get("schema_version") != schema:
                errors.append(f"parent artifact schema drifted: {artifact.name}")
            if value.get("status") != status:
                errors.append(f"parent artifact status drifted: {artifact.name}")
            if value.get(digest_key) != digest:
                errors.append(f"parent artifact digest drifted: {artifact.name}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"parent artifact unreadable: {type(exc).__name__}")

    inherited = (
        ("B2 spec", b2.b2_spec_digest(), B3_PARENT_B2_SPEC_DIGEST),
        ("B2 task slots", b2.task_slot_digest(), B3_PARENT_B2_TASK_SLOT_DIGEST),
        ("B2.1 spec", b21.b21_spec_digest(), B3_PARENT_B21_SPEC_DIGEST),
        (
            "B2.1 schedule",
            b21.b21_execution_schedule_digest(),
            B3_PARENT_B21_SCHEDULE_DIGEST,
        ),
    )
    for name, actual, expected in inherited:
        if actual != expected:
            errors.append(f"inherited {name} drifted")
    return sorted(set(errors))


def spec_payload() -> dict[str, Any]:
    schedule = build_execution_schedule()
    schedule_errors = validate_execution_schedule(schedule)
    plan = build_expected_observation_plan(schedule)
    plan_errors = b3r.validate_expected_observation_plan(plan)
    if schedule_errors or plan_errors:
        raise B3ProtocolError(
            "invalid B3 design: " + "; ".join(schedule_errors + plan_errors)
        )
    return {
        "schema_version": B3_SCHEMA_VERSION,
        "parent_locks": {
            "b25_failure_sha256": B3_PARENT_B25_FAILURE_SHA256,
            "b25_failure_digest": B3_PARENT_B25_FAILURE_DIGEST,
            "determinism_repair_sha256": B3_PARENT_DETERMINISM_REPAIR_SHA256,
            "determinism_repair_digest": B3_PARENT_DETERMINISM_REPAIR_DIGEST,
            "determinism_scale_sha256": B3_PARENT_DETERMINISM_SCALE_SHA256,
            "determinism_scale_digest": B3_PARENT_DETERMINISM_SCALE_DIGEST,
            "b2_spec_digest": B3_PARENT_B2_SPEC_DIGEST,
            "b2_task_slot_digest": B3_PARENT_B2_TASK_SLOT_DIGEST,
            "b21_spec_digest": B3_PARENT_B21_SPEC_DIGEST,
        },
        "holdout_rules": copy.deepcopy(B3_HOLDOUT_RULES),
        "experimental_design": copy.deepcopy(B3_EXPERIMENTAL_DESIGN),
        "analysis_rules": copy.deepcopy(B3_ANALYSIS_RULES),
        "randomization": {
            "seed": B3_RANDOMIZATION_SEED,
            "policy": B3_RANDOMIZATION_POLICY,
            "sequence_coefficients_mod_6": copy.deepcopy(
                B3_SEQUENCE_COEFFICIENTS
            ),
            "williams_sequence_count": len(B3_WILLIAMS_INDEX_SEQUENCES),
            "position_balance_exact_overall_repetition_size_and_role": True,
            "first_order_predecessor_balance_exact_overall_repetition_size_and_role": True,
            "language_sequence_count_range": [10, 12],
            "schedule_row_count": len(schedule),
            "schedule_digest": execution_schedule_digest(schedule),
            "expected_logical_group_count": len(plan),
            "expected_observation_count": sum(len(values) for values in plan.values()),
            "expected_observation_plan_digest": expected_observation_plan_digest(),
        },
        "repeatability_binding": copy.deepcopy(B3_REPEATABILITY_BINDING),
        "repeatability_policy": b3r.repeatability_policy_payload(),
        "execution_boundary": copy.deepcopy(B3_EXECUTION_BOUNDARY),
        "hard_gates": copy.deepcopy(B3_HARD_GATES),
        "publication_policy": copy.deepcopy(B3_PUBLICATION_POLICY),
    }


def spec_digest() -> str:
    return _prefixed_digest("b3spec_", spec_payload(), length=16)


def _build_report_without_digest() -> dict[str, Any]:
    payload = spec_payload()
    return {
        "schema_version": B3_REPORT_SCHEMA_VERSION,
        "phase": B3_PHASE,
        "date": B3_DATE,
        "status": B3_STATUS,
        "claim_level": B3_CLAIM_LEVEL,
        "parent_locks": payload["parent_locks"],
        "design_corrections": {
            "b25_closeout_remains_terminal_failed_closed_no_result": True,
            "b25_matrix_restarted_resumed_scored_or_ranked": False,
            "b25_private_holdout_or_launch_authorization_reused": False,
            "forty_eight_tasks_no_longer_described_as_forty_eight_independent_repositories": True,
            "repository_cluster_count_explicitly_frozen_at_twelve": True,
            "arm_position_and_first_order_predecessor_effects_both_balanced": True,
            "target_cardinality_retained_because_it_controls_support_routing": True,
            "missing_whole_groups_and_duplicate_repetitions_fail_closed": True,
            "gate_and_scorer_share_one_repeatability_core": True,
            "pre_output_zero_output_recovery_separated_from_post_output_retry": True,
        },
        "holdout_rules": payload["holdout_rules"],
        "experimental_design": payload["experimental_design"],
        "analysis_rules": payload["analysis_rules"],
        "randomization": payload["randomization"],
        "repeatability_binding": payload["repeatability_binding"],
        "repeatability_policy": payload["repeatability_policy"],
        "execution_boundary": payload["execution_boundary"],
        "hard_gates": payload["hard_gates"],
        "publication_policy": payload["publication_policy"],
        "implementation_readiness": copy.deepcopy(B3_IMPLEMENTATION_READINESS),
        "source_bundle_digest": source_bundle_digest(),
        "spec_digest": spec_digest(),
        "next_authorized_action": B3_NEXT_ACTION,
    }


def build_report() -> dict[str, Any]:
    parent_errors = validate_parent_locks()
    if parent_errors:
        raise B3ProtocolError("parent lock validation failed: " + "; ".join(parent_errors))
    report = _build_report_without_digest()
    report["protocol_digest"] = _prefixed_digest("b3protocol_", report)
    return report


def _diff(expected: Any, actual: Any, path: str = "report") -> list[str]:
    if type(expected) is not type(actual):
        return [f"{path}: type drift"]
    if isinstance(expected, dict):
        errors: list[str] = []
        expected_keys = set(expected)
        actual_keys = set(actual)
        if expected_keys != actual_keys:
            errors.append(
                f"{path}: key drift missing={sorted(expected_keys - actual_keys)} "
                f"extra={sorted(actual_keys - expected_keys)}"
            )
        for key in sorted(expected_keys & actual_keys):
            errors.extend(_diff(expected[key], actual[key], f"{path}.{key}"))
        return errors
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"{path}: list length drift"]
        errors: list[str] = []
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            errors.extend(_diff(expected_item, actual_item, f"{path}[{index}]"))
        return errors
    if expected != actual:
        return [f"{path}: value drift"]
    return []


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 protocol report must be an object"]
    errors = list(b2.scan_public_report(report))
    try:
        expected = build_report()
    except (B3ProtocolError, OSError, ValueError) as exc:
        errors.append(f"cannot rebuild B3 protocol report: {type(exc).__name__}")
        return sorted(set(errors))
    errors.extend(_diff(expected, report))
    digest_input = copy.deepcopy(report)
    actual_digest = digest_input.pop("protocol_digest", None)
    if actual_digest != _prefixed_digest("b3protocol_", digest_input):
        errors.append("B3 protocol digest mismatch")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    slots = b2.build_task_slots()
    schedule = build_execution_schedule(slots)
    plan = build_expected_observation_plan(schedule, slots)
    report = build_report()
    repeatability_self = b3r.run_self_test()
    repeatability_fault = b3r.run_fault_test()
    checks = [
        not validate_parent_locks(),
        not b2.validate_task_slots(slots),
        not validate_williams_index_sequences(),
        not validate_execution_schedule(schedule, slots),
        not b3r.validate_expected_observation_plan(plan),
        len(schedule) == 192,
        len(plan) == 360,
        sum(len(values) for values in plan.values()) == 1440,
        report["experimental_design"]["repository_cluster_count"] == 12,
        report["experimental_design"][
            "forty_eight_tasks_are_not_claimed_as_independent_repositories"
        ],
        report["analysis_rules"][
            "exact_equal_quality_vectors_share_competition_rank"
        ],
        report["execution_boundary"]["private_launch_release_alone_consumes_attempt"]
        is False,
        report["execution_boundary"]["attempt_boundary"]
        == "first_durable_treatment_observation",
        report["repeatability_binding"][
            "target_cardinality_class_retained_for_support_routing"
        ],
        report["implementation_readiness"]["future_tournament_execution_authorized"]
        is False,
        not validate_report(report),
        repeatability_self["passed"],
        repeatability_fault["passed"],
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "schedule_rows": len(schedule),
        "logical_groups": len(plan),
        "logical_observations": sum(len(values) for values in plan.values()),
    }


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[tuple[str, bool]] = []

    def rejected(name: str, mutator: Any) -> None:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append((name, bool(validate_report(value))))

    rejected(
        "b25_reopened",
        lambda value: value["design_corrections"].__setitem__(
            "b25_matrix_restarted_resumed_scored_or_ranked", True
        ),
    )
    rejected(
        "parent_lock_drift",
        lambda value: value["parent_locks"].__setitem__(
            "b25_failure_digest", "b25failure_" + "0" * 64
        ),
    )
    rejected(
        "task_independence_claim",
        lambda value: value["experimental_design"].__setitem__(
            "forty_eight_tasks_are_not_claimed_as_independent_repositories", False
        ),
    )
    rejected(
        "carryover_unbalanced",
        lambda value: value["randomization"].__setitem__(
            "first_order_predecessor_balance_exact_overall_repetition_size_and_role",
            False,
        ),
    )
    rejected(
        "target_cardinality_removed",
        lambda value: value["repeatability_binding"].__setitem__(
            "target_cardinality_class_retained_for_support_routing", False
        ),
    )
    rejected(
        "launch_release_consumes_attempt",
        lambda value: value["execution_boundary"].__setitem__(
            "private_launch_release_alone_consumes_attempt", True
        ),
    )
    rejected(
        "post_output_retry",
        lambda value: value["execution_boundary"].__setitem__(
            "post_boundary_selective_cell_retry_allowed", True
        ),
    )
    rejected(
        "private_detail_public",
        lambda value: value["publication_policy"].__setitem__(
            "private_holdout_manifest_or_freeze_digest_public", True
        ),
    )
    rejected(
        "execution_overauthorized",
        lambda value: value["implementation_readiness"].__setitem__(
            "future_tournament_execution_authorized", True
        ),
    )
    rejected(
        "digest_drift",
        lambda value: value.__setitem__("protocol_digest", "b3protocol_" + "0" * 64),
    )
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit("fault-test failed: " + ", ".join(failed))
    return {
        "passed": True,
        "faults_rejected": len(checks),
        "faults_total": len(checks),
    }


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise B3ProtocolError("refusing to write invalid B3 report")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B3 future tournament protocol")
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
    "B3_SCHEMA_VERSION",
    "B3_REPORT_SCHEMA_VERSION",
    "B3_HOLDOUT_RULES",
    "B3_EXPERIMENTAL_DESIGN",
    "B3_ANALYSIS_RULES",
    "B3_REPEATABILITY_BINDING",
    "B3_EXECUTION_BOUNDARY",
    "B3_HARD_GATES",
    "B3_PUBLICATION_POLICY",
    "B3_IMPLEMENTATION_READINESS",
    "B3ScheduleRow",
    "build_williams_index_sequences",
    "validate_williams_index_sequences",
    "build_execution_schedule",
    "validate_execution_schedule",
    "execution_schedule_digest",
    "build_expected_observation_plan",
    "expected_observation_plan_digest",
    "source_bundle_digest",
    "validate_parent_locks",
    "spec_payload",
    "spec_digest",
    "build_report",
    "validate_report",
    "run_self_test",
    "run_fault_test",
]
