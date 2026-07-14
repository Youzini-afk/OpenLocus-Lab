#!/usr/bin/env python3
"""Freeze the B2 internal product-decision tournament protocol.

This module is design-only.  It creates no empirical tasks, reads no private
oracle rows, runs no adapter, and makes no tournament/default/winner claim.

The experimental unit is one logical task.  All six S0-S5 stacks are measured
on every task, so task is the complete comparison block.  Cache/repetition
measurements are technical repeated measures and never increase the task-level
sample size above 48.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from product_bakeoff_b1_spec import (  # noqa: E402
    B1_ADAPTER_IDS,
    B1_SOURCE_BUNDLE_PATHS,
    S0_ADAPTER_ID,
    S1_ADAPTER_ID,
    S2_ADAPTER_ID,
    S3_ADAPTER_ID,
    S4_ADAPTER_ID,
    S5_ADAPTER_ID,
)


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b2_protocol"
    / "product_bakeoff_b2_protocol_report.json"
)

B2_SCHEMA_VERSION = "product_bakeoff_b2_protocol.v1"
B2_REPORT_SCHEMA_VERSION = "product_bakeoff_b2_protocol_report.v1"
B2_PHASE = "product_bakeoff_b2_internal_product_decision_tournament_protocol"
B2_STATUS = "product_bakeoff_b2_protocol_frozen_no_execution_no_result"
B2_CLAIM_LEVEL = "design_only_no_tournament_result"

# B2 is allowed to start only from the formally closed B1 bundle.
B2_PARENT_B1_SOURCE_CHECKPOINT = "0b6f2e13b1dbc679eb1f827c28a8abd5403dcd58"
B2_PARENT_B1_CLOSEOUT_CHECKPOINT = "617b452cf24ac7294b49133caf18ee8f279e1dfe"
B2_PARENT_B1_SPEC_VERSION = "product_bakeoff_b1.v2.4"
B2_PARENT_B1_SPEC_DIGEST = "b1spec_6058c3e732d077f5"
B2_PARENT_B1_FIXTURE_DIGEST = "b1fix_b012d3da68d75522"
B2_PARENT_B1_SOURCE_BUNDLE_DIGEST = (
    "b1src_fa5b30ca188d08a491206e13acfe3faa9a5070a68be2222ba349392101b136d2"
)
B2_PARENT_B1_RUNTIME_BUNDLE_DIGEST = (
    "b1run_01c1fdcfe6d77f3d1f8101f66a90191a1f4a620d43e39a139b686149e0b2a896"
)
B2_PARENT_B1_AGGREGATE_REL = (
    "artifacts/product_bakeoff_b1/"
    "product_bakeoff_b1_mechanics_screen_aggregate.json"
)

# The committed B2 design source is added to the complete B1 source surface.
B2_SOURCE_BUNDLE_PATHS = tuple(B1_SOURCE_BUNDLE_PATHS) + (
    "eval/ci_clone_and_lock_repo.py",
    "eval/product_bakeoff_b2_corpus.py",
    "eval/product_bakeoff_b2_oracle.py",
    "eval/product_bakeoff_b2_author.py",
    "eval/product_bakeoff_b2_adapters.py",
    "eval/product_bakeoff_b2_runner.py",
    "eval/product_bakeoff_b2_scorer.py",
    "eval/product_bakeoff_b2_cli.py",
    "eval/product_bakeoff_b2_protocol.py",
    ".github/workflows/retrieval-benchmark.yml",
)

# ---------------------------------------------------------------------------
# Frozen task frame
# ---------------------------------------------------------------------------

B2_LANGUAGES = ("rust", "python", "typescript")
B2_SIZE_BANDS = ("small", "medium", "large", "xlarge")
B2_SIZE_BAND_VISIBLE_BYTES = {
    "small": (256 * 1024, 4 * 1024 * 1024),
    "medium": (4 * 1024 * 1024, 16 * 1024 * 1024),
    "large": (16 * 1024 * 1024, 64 * 1024 * 1024),
    "xlarge": (64 * 1024 * 1024, 256 * 1024 * 1024 + 1),
}
B2_VISIBLE_FILE_COUNT_RANGE = (32, 50_000)
B2_TASK_ROLES = ("direct", "relational", "workflow", "restraint")

B2_DIRECT_FAMILIES = ("symbol_lookup", "definition_find", "error_text")
B2_RELATIONAL_FAMILIES = (
    "caller_trace",
    "type_resolution",
    "cross_file_dependency",
)
B2_WORKFLOW_FAMILIES = (
    "refactor_target_find",
    "configuration_discovery",
    "test_discovery",
)
B2_RESTRAINT_FAMILIES = ("ambiguous_target", "no_answer")
B2_TASK_FAMILIES = (
    *B2_DIRECT_FAMILIES,
    *B2_RELATIONAL_FAMILIES,
    *B2_WORKFLOW_FAMILIES,
    *B2_RESTRAINT_FAMILIES,
)

B2_LITERAL_ELIGIBLE_FAMILIES = frozenset(
    {"error_text", "configuration_discovery", "test_discovery"}
)
B2_SYMBOL_ELIGIBLE_FAMILIES = frozenset(
    {
        "symbol_lookup",
        "definition_find",
        "type_resolution",
        "refactor_target_find",
    }
)
B2_GRAPH_ELIGIBLE_FAMILIES = frozenset(
    {
        "caller_trace",
        "cross_file_dependency",
        "configuration_discovery",
        "test_discovery",
    }
)
B2_SUPPORT_ELIGIBLE_FAMILIES = frozenset(B2_RELATIONAL_FAMILIES)
B2_ORACLE_KINDS = ("deterministic", "multi_target", "abstain")

B2_REPO_SLOT_COUNT = len(B2_LANGUAGES) * len(B2_SIZE_BANDS)  # 12
B2_TASKS_PER_REPO_SLOT = len(B2_TASK_ROLES)  # 4
B2_TASK_COUNT = B2_REPO_SLOT_COUNT * B2_TASKS_PER_REPO_SLOT  # 48
B2_ONE_SHOT_TASK_COUNT = 36
B2_TWO_STEP_TASK_COUNT = 12
B2_ANSWERABLE_TASK_COUNT = 42
B2_AMBIGUOUS_TASK_COUNT = 6
B2_NO_ANSWER_TASK_COUNT = 6

# Four repetitions make the four task roles rotate through the one cold slot
# exactly once per repository.  One repository/arm/repetition index build is
# shared by the four task measurements; this is a constrained split-plot
# lifecycle, not four independent index builds.
B2_REPETITIONS = (1, 2, 3, 4)
B2_COLD_OBSERVATIONS_PER_TASK = 1
B2_WARM_OBSERVATIONS_PER_TASK = 3
B2_RANDOMIZATION_SEED = "openlocus-b2-20260714-rcbd-splitplot-v1"
B2_RANDOMIZATION_POLICY = (
    "seeded_repo_order_plus_orthogonal_cyclic_arm_position_balance_v1"
)
B2_LIFECYCLE_POLICY = "repo_block_split_plot_rotating_cold_task_v1"
# rotation = 2*language + 1*size + 1*role + 2*repetition (mod 6).
# This makes arm positions exact within every size, task role, and repetition
# stratum; language strata (64 rows each) are arithmetically unable to split
# perfectly into six positions and are held to the minimal 10..12 range.
B2_ARM_ROTATION_COEFFICIENTS = {
    "language": 2,
    "size_band": 1,
    "role": 1,
    "repetition": 2,
}

B2_ADAPTER_IDS = tuple(B1_ADAPTER_IDS)
B2_ADAPTER_COUNT = len(B2_ADAPTER_IDS)
B2_ONE_SHOT_RECORDS = (
    B2_ONE_SHOT_TASK_COUNT * len(B2_REPETITIONS) * B2_ADAPTER_COUNT
)  # 36 * 4 * 6 = 864
B2_TWO_STEP_RECORDS = (
    B2_TWO_STEP_TASK_COUNT * len(B2_REPETITIONS) * B2_ADAPTER_COUNT * 2
)  # 12 * 4 * 6 * 2 = 576
B2_TOTAL_RECORDS = B2_ONE_SHOT_RECORDS + B2_TWO_STEP_RECORDS  # 1440
B2_RECORDS_PER_ARM = B2_TOTAL_RECORDS // B2_ADAPTER_COUNT  # 240
B2_INDEX_BUILD_COUNT = B2_REPO_SLOT_COUNT * len(B2_REPETITIONS) * B2_ADAPTER_COUNT

# ---------------------------------------------------------------------------
# Frozen metrics and decision gates
# ---------------------------------------------------------------------------

B2_FIXED_POINT_SCALE = 1_000_000
B2_SUBSET_DENOMINATORS = {
    "literal": 12,
    "symbol": 16,
    "graph": 16,
    "support": 12,
}

B2_METRIC_DEFINITIONS = {
    "task_success_count": (
        "count of the 48 logical tasks whose frozen status/target and, when "
        "applicable, support requirements all pass"
    ),
    "answerable_target_success_count": (
        "count of the 42 answerable tasks with at least one oracle-valid "
        "primary target under the frozen task-kind rule"
    ),
    "ambiguous_status_success_count": (
        "count of six ambiguous tasks returning uncertain with multi-target "
        "coverage and no oracle-negative target"
    ),
    "no_answer_status_success_count": (
        "count of six no-answer tasks returning no_evidence with no selected "
        "candidate/evidence/target/support"
    ),
    "support_success_count": (
        "count of 12 two-step tasks with a correct bound parent target and at "
        "least one oracle-valid bounded support relation"
    ),
    "one_shot_success_count": (
        "count of 36 one-shot tasks meeting the frozen status and target rule"
    ),
    "component_subset_success_counts": (
        "target/status success counts within the predeclared literal, symbol, "
        "graph, and support subsets; support subset success equals support success"
    ),
    "context_f05_sum_ppm": (
        "sum over 42 answerable tasks of span F0.5 stored as integer "
        "millionths; rank uses the sum, never a rounded mean"
    ),
    "harmful_evidence_task_count": (
        "count of answerable tasks whose selected evidence overlaps a frozen "
        "oracle-negative span"
    ),
    "warm_query_p95_us": (
        "parent-observed warm query-to-pack p95 in integer microseconds over "
        "technical repetitions"
    ),
    "peak_rss_p95_bytes": (
        "parent-observed p95 peak resident bytes over attempted stages"
    ),
    "cold_index_p95_us": (
        "parent-observed p95 cold prepare/index duration in integer microseconds"
    ),
    "index_state_p95_bytes": (
        "p95 sealed persistent-state bytes after cold build"
    ),
}

B2_TASK_ADMISSION_RULES = {
    "one_frozen_repo_snapshot_per_language_size_stratum": True,
    "repo_snapshot_count": B2_REPO_SLOT_COUNT,
    "immutable_commit_and_visible_tree_manifest_required": True,
    "license_or_usage_permission_required": True,
    "resolved_source_root_must_be_real_directory_not_link_or_reparse": True,
    "visible_tree_must_match_frozen_manifest_before_and_after_execution": True,
    "actual_repo_identity_kept_private_until_aggregate_release": True,
    "task_text_and_oracle_rows_kept_private": True,
    "task_authored_before_any_arm_output": True,
    "adapter_output_must_not_be_used_to_create_or_edit_task_oracle": True,
    "query_must_not_contain_source_path_line_number_or_repo_identity": True,
    "deterministic_oracle_exact_positive_span_count": 1,
    "multi_target_oracle_min_distinct_positive_span_count": 2,
    "abstain_oracle_positive_span_count": 0,
    "two_step_oracle_min_support_relation_count": 1,
    "min_distinct_negative_spans_per_task": 2,
    "positive_negative_spans_must_be_disjoint": True,
    "all_oracle_spans_must_validate_against_frozen_current_source": True,
    "no_task_replacement_or_exclusion_after_manifest_freeze": True,
}

B2_SCORING_RULES = {
    "line_atom": "canonical_relative_path_plus_one_indexed_line",
    "duplicate_selected_line_atoms_deduplicated_before_scoring": True,
    "deterministic_target_success": (
        "selected_primary_target_intersects_the_single_positive_target_span_"
        "and_intersects_no_negative_span"
    ),
    "multi_target_success": (
        "status_uncertain_and_at_least_two_distinct_positive_target_spans_"
        "covered_and_no_selected_target_intersects_a_negative_span"
    ),
    "abstain_success": (
        "status_no_evidence_and_zero_candidates_evidence_targets_and_support"
    ),
    "two_step_support_success": (
        "context_target_success_and_parent_lineage_valid_and_at_least_one_"
        "selected_support_span_matches_a_frozen_target_relation_span"
    ),
    "two_step_step_order": "all_six_context_steps_in_frozen_arm_order_then_all_six_support_steps_in_same_order",
    "two_step_parent_normalization": (
        "all_six_context_targets_must_share_one_path_and_a_nonempty_line_range_"
        "intersection;_the_exact_intersection_is_the_common_parent_for_all_"
        "six_support_requests;_otherwise_the_run_fails_closed"
    ),
    "logical_task_success_partition": (
        "task_success_count_equals_one_shot_success_count_plus_support_success_count"
    ),
    "component_subset_success": (
        "target_or_status_success_inside_the_frozen_component_eligible_subset;_"
        "for_support_the_value_is_support_success_count"
    ),
    "context_precision": "positive_selected_line_atoms_divided_by_selected_line_atoms",
    "context_recall": "positive_selected_line_atoms_divided_by_positive_oracle_line_atoms",
    "context_f05": "1.25_times_precision_times_recall_divided_by_0.25_times_precision_plus_recall",
    "context_empty_answerable_value": 0,
    "fixed_point_conversion": "floor_exact_rational_times_1000000",
    "context_sum_denominator_tasks": B2_ANSWERABLE_TASK_COUNT,
    "harmful_evidence_task": "any_selected_line_atom_intersects_any_frozen_negative_span",
    "no_answer_tasks_excluded_from_context_f05_sum": True,
    "quality_scored_once_per_logical_task_after_exact_cache_repetition_semantic_equality": True,
    "resource_percentile_rule": "nearest_rank_ceiling_p95",
    "warm_query_population": "all_warm_context_and_support_records_query_plus_materialize_plus_render",
    "peak_rss_population": "all_attempted_validated_records_parent_observed_direct_worker_peak_rss",
    "cold_index_population": "one_cold_context_prepare_per_repository_arm_repetition",
    "index_state_population": "sealed_persistent_index_bytes_after_each_cold_context_build",
}

B2_QUALITY_FLOORS = {
    "task_success_count": 34,
    "one_shot_success_count": 30,
    "answerable_target_success_count": 34,
    "ambiguous_status_success_count": 5,
    "no_answer_status_success_count": 5,
    "default_track_support_success_count": 9,
    "default_track_task_success_count": 36,
    "max_harmful_evidence_task_count": 4,
    "language_success_floor_each_of_16": 11,
    "size_success_floor_each_of_12": 8,
    "role_success_floor_each_of_12": 8,
}

B2_BASELINE_NONINFERIORITY = {
    "max_task_success_loss": 1,
    "max_target_success_loss": 1,
    "max_context_f05_average_loss_ppm": 10_000,
    "max_harmful_evidence_extra_tasks": 1,
}

B2_BASELINE_RESOURCE_CEILINGS = {
    "warm_query_ratio_ppm": 2_000_000,
    "warm_query_additive_us": 250_000,
    "peak_rss_ratio_ppm": 2_000_000,
    "peak_rss_additive_bytes": 256 * 1024 * 1024,
    "cold_index_ratio_ppm": 1_500_000,
    "cold_index_additive_us": 5_000_000,
    "index_state_ratio_ppm": 1_100_000,
    "index_state_additive_bytes": 64 * 1024 * 1024,
}

B2_COMPONENT_RULES = (
    {
        "rule_id": "literal_earns_inclusion",
        "child": S1_ADAPTER_ID,
        "parent": S0_ADAPTER_ID,
        "subset": "literal",
        "minimum_success_gain": 1,
        "alternative_context_mean_gain_ppm": 10_000,
        "allow_context_alternative": True,
        "regression_metric": "task_success_count",
        "max_overall_task_loss": 1,
        "max_harmful_evidence_extra_tasks": 1,
        "max_warm_query_ratio_ppm": 1_200_000,
        "max_peak_rss_ratio_ppm": 1_150_000,
    },
    {
        "rule_id": "symbol_earns_inclusion",
        "child": S2_ADAPTER_ID,
        "parent": S1_ADAPTER_ID,
        "subset": "symbol",
        "minimum_success_gain": 1,
        "alternative_context_mean_gain_ppm": 10_000,
        "allow_context_alternative": True,
        "regression_metric": "task_success_count",
        "max_overall_task_loss": 1,
        "max_harmful_evidence_extra_tasks": 1,
        "max_warm_query_ratio_ppm": 1_200_000,
        "max_peak_rss_ratio_ppm": 1_150_000,
    },
    {
        "rule_id": "graph_earns_inclusion_over_s2",
        "child": S3_ADAPTER_ID,
        "parent": S2_ADAPTER_ID,
        "subset": "graph",
        "minimum_success_gain": 2,
        "alternative_context_mean_gain_ppm": 20_000,
        "allow_context_alternative": True,
        "regression_metric": "task_success_count",
        "max_overall_task_loss": 1,
        "max_harmful_evidence_extra_tasks": 1,
        "max_warm_query_ratio_ppm": 1_300_000,
        "max_peak_rss_ratio_ppm": 1_200_000,
    },
    {
        "rule_id": "support_earns_inclusion_over_s2",
        "child": S4_ADAPTER_ID,
        "parent": S2_ADAPTER_ID,
        "subset": "support",
        "minimum_success_gain": 3,
        "alternative_context_mean_gain_ppm": 10_000,
        "allow_context_alternative": False,
        "regression_metric": "one_shot_success_count",
        "max_overall_task_loss": 1,
        "max_harmful_evidence_extra_tasks": 1,
        "max_warm_query_ratio_ppm": 1_350_000,
        "max_peak_rss_ratio_ppm": 1_250_000,
    },
    {
        "rule_id": "support_earns_inclusion_over_s3",
        "child": S5_ADAPTER_ID,
        "parent": S3_ADAPTER_ID,
        "subset": "support",
        "minimum_success_gain": 3,
        "alternative_context_mean_gain_ppm": 10_000,
        "allow_context_alternative": False,
        "regression_metric": "one_shot_success_count",
        "max_overall_task_loss": 1,
        "max_harmful_evidence_extra_tasks": 1,
        "max_warm_query_ratio_ppm": 1_350_000,
        "max_peak_rss_ratio_ppm": 1_250_000,
    },
    {
        "rule_id": "graph_earns_inclusion_over_s4",
        "child": S5_ADAPTER_ID,
        "parent": S4_ADAPTER_ID,
        "subset": "graph",
        "minimum_success_gain": 2,
        "alternative_context_mean_gain_ppm": 20_000,
        "allow_context_alternative": True,
        "regression_metric": "task_success_count",
        "max_overall_task_loss": 1,
        "max_harmful_evidence_extra_tasks": 1,
        "max_warm_query_ratio_ppm": 1_300_000,
        "max_peak_rss_ratio_ppm": 1_200_000,
    },
)

B2_REQUIRED_COMPONENT_RULES = {
    S1_ADAPTER_ID: ("literal_earns_inclusion",),
    S2_ADAPTER_ID: (
        "literal_earns_inclusion",
        "symbol_earns_inclusion",
    ),
    S3_ADAPTER_ID: (
        "literal_earns_inclusion",
        "symbol_earns_inclusion",
        "graph_earns_inclusion_over_s2",
    ),
    S4_ADAPTER_ID: (
        "literal_earns_inclusion",
        "symbol_earns_inclusion",
        "support_earns_inclusion_over_s2",
    ),
    S5_ADAPTER_ID: (
        "literal_earns_inclusion",
        "symbol_earns_inclusion",
        "graph_earns_inclusion_over_s2",
        "support_earns_inclusion_over_s3",
        "graph_earns_inclusion_over_s4",
    ),
}

B2_DEFAULT_TRACK_ARMS = (S4_ADAPTER_ID, S5_ADAPTER_ID)
B2_OPTIONAL_TRACK_ARMS = (S1_ADAPTER_ID, S2_ADAPTER_ID, S3_ADAPTER_ID)
B2_BASELINE_CONTROL_ARM = S0_ADAPTER_ID

B2_DECISION_EQUIVALENCE = {
    "max_task_success_loss": 1,
    "max_target_success_loss": 1,
    "max_status_success_loss": 1,
    "max_support_success_loss": 1,
    "max_context_f05_average_loss_ppm": 10_000,
    "max_harmful_evidence_extra_tasks": 1,
    "max_warm_query_ratio_ppm": 1_200_000,
    "max_warm_query_additive_us": 100_000,
    "max_peak_rss_ratio_ppm": 1_150_000,
    "max_peak_rss_additive_bytes": 64 * 1024 * 1024,
}

B2_TIE_POLICY = {
    "quality_values": "unrounded_integer_counts_and_fixed_point_sums_only",
    "exact_equal_quality_vector": "shared_competition_rank",
    "exact_equal_resource_vector": "shared_competition_rank",
    "competition_rank_example": [1, 1, 3],
    "forced_unique_winner": False,
    "decision_equivalent_arms_may_all_advance": True,
    "maximum_finalist_count": None,
}

B2_FORBIDDEN_ADAPTATIONS = (
    "no_task_add_drop_replace_after_any_arm_output",
    "no_oracle_or_query_edit_after_any_arm_output",
    "no_metric_threshold_weight_or_order_change_after_any_arm_output",
    "no_arm_specific_budget_timeout_or_visibility",
    "no_interim_arm_elimination_or_early_winner_call",
    "no_selective_rerun_of_only_failed_or_losing_cells",
    "no_imputation_for_missing_or_rejected_cells",
    "no_provider_network_or_model_calls",
    "no_public_per_task_or_per_repo_empirical_detail",
)

B2_PUBLICATION_POLICY = {
    "publication_level": "aggregate_only",
    "minimum_public_stratum_denominator": 12,
    "arm_level_aggregate_metrics_public": True,
    "predeclared_language_size_role_aggregates_public": True,
    "repo_level_results_public": False,
    "task_level_results_public": False,
    "task_text_or_query_public": False,
    "candidate_path_range_excerpt_hash_public": False,
    "private_manifest_or_freeze_digest_public": False,
    "oracle_or_label_rows_public": False,
    "resource_samples_or_timings_per_cell_public": False,
    "private_run_paths_public": False,
    "provider_payloads_or_secrets_public": False,
}

B2_HARD_GATES = {
    "parent_b1_closeout_lock_matches": True,
    "private_task_manifest_frozen_before_execution": True,
    "private_oracle_manifest_frozen_before_execution": True,
    "source_and_runtime_bundle_locked_before_execution": True,
    "complete_1440_record_matrix": True,
    "all_records_accepted": True,
    "all_current_source_citations_valid": True,
    "source_immutable": True,
    "cold_warm_and_repetition_quality_semantics_equal": True,
    "all_resource_samples_complete": True,
    "provider_network_call_count_zero": True,
    "privacy_canary_absent_from_public_surface": True,
    "scorer_and_oracle_unloaded_until_pre_score_gates_pass": True,
    "no_post_hoc_task_or_rule_change": True,
}


@dataclass(frozen=True)
class B2TaskSlot:
    slot_id: str
    repo_slot: str
    language: str
    size_band: str
    role: str
    task_family: str
    interaction_mode: str
    oracle_kind: str
    literal_eligible: bool
    symbol_eligible: bool
    graph_eligible: bool
    support_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "repo_slot": self.repo_slot,
            "language": self.language,
            "size_band": self.size_band,
            "role": self.role,
            "task_family": self.task_family,
            "interaction_mode": self.interaction_mode,
            "oracle_kind": self.oracle_kind,
            "literal_eligible": self.literal_eligible,
            "symbol_eligible": self.symbol_eligible,
            "graph_eligible": self.graph_eligible,
            "support_eligible": self.support_eligible,
        }


@dataclass(frozen=True)
class B2ScheduleRow:
    slot_id: str
    repo_slot: str
    repetition: int
    cache_state: str
    task_position: int
    arm_order: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "repo_slot": self.repo_slot,
            "repetition": self.repetition,
            "cache_state": self.cache_state,
            "task_position": self.task_position,
            "arm_order": list(self.arm_order),
        }


@dataclass(frozen=True)
class B2ArmSummary:
    adapter_id: str
    record_count: int
    accepted_count: int
    rejected_count: int
    resource_complete_count: int
    matrix_complete: bool
    safety_gates_passed: bool
    determinism_confirmed: bool
    source_immutable: bool
    provider_network_call_count: int
    invalid_citation_count: int
    timeout_count: int
    task_success_count: int
    answerable_target_success_count: int
    ambiguous_status_success_count: int
    no_answer_status_success_count: int
    support_success_count: int
    one_shot_success_count: int
    context_f05_sum_ppm: int
    harmful_evidence_task_count: int
    language_success_counts: tuple[tuple[str, int], ...]
    size_success_counts: tuple[tuple[str, int], ...]
    role_success_counts: tuple[tuple[str, int], ...]
    subset_success_counts: tuple[tuple[str, int], ...]
    subset_context_f05_sum_ppm: tuple[tuple[str, int], ...]
    warm_query_p95_us: int
    peak_rss_p95_bytes: int
    cold_index_p95_us: int
    index_state_p95_bytes: int

    def language_counts(self) -> dict[str, int]:
        return dict(self.language_success_counts)

    def size_counts(self) -> dict[str, int]:
        return dict(self.size_success_counts)

    def role_counts(self) -> dict[str, int]:
        return dict(self.role_success_counts)

    def subset_counts(self) -> dict[str, int]:
        return dict(self.subset_success_counts)

    def subset_context(self) -> dict[str, int]:
        return dict(self.subset_context_f05_sum_ppm)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any, *, length: int | None = None) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    if length is not None:
        digest = digest[:length]
    return prefix + digest


def _seeded_order(values: Iterable[str], label: str) -> tuple[str, ...]:
    def key(value: str) -> tuple[str, str]:
        material = f"{B2_RANDOMIZATION_SEED}|{label}|{value}".encode("utf-8")
        return hashlib.sha256(material).hexdigest(), value

    return tuple(sorted(values, key=key))


def _rotate(values: Sequence[str], offset: int) -> tuple[str, ...]:
    if not values:
        return ()
    n = offset % len(values)
    return tuple(values[n:]) + tuple(values[:n])


def build_task_slots() -> tuple[B2TaskSlot, ...]:
    slots: list[B2TaskSlot] = []
    for size_index, size_band in enumerate(B2_SIZE_BANDS):
        for language_index, language in enumerate(B2_LANGUAGES):
            repo_slot = f"b2_repo_{language}_{size_band}"
            family_by_role = {
                "direct": B2_DIRECT_FAMILIES[(language_index + size_index) % 3],
                "relational": B2_RELATIONAL_FAMILIES[
                    (language_index + 2 * size_index) % 3
                ],
                "workflow": B2_WORKFLOW_FAMILIES[
                    (2 * language_index + size_index) % 3
                ],
                "restraint": B2_RESTRAINT_FAMILIES[
                    (language_index + size_index) % 2
                ],
            }
            for role in B2_TASK_ROLES:
                task_family = family_by_role[role]
                if task_family == "no_answer":
                    oracle_kind = "abstain"
                elif task_family == "ambiguous_target":
                    oracle_kind = "multi_target"
                else:
                    oracle_kind = "deterministic"
                interaction_mode = "two_step" if role == "relational" else "one_shot"
                slots.append(
                    B2TaskSlot(
                        slot_id=f"b2_slot_{len(slots) + 1:02d}",
                        repo_slot=repo_slot,
                        language=language,
                        size_band=size_band,
                        role=role,
                        task_family=task_family,
                        interaction_mode=interaction_mode,
                        oracle_kind=oracle_kind,
                        literal_eligible=task_family in B2_LITERAL_ELIGIBLE_FAMILIES,
                        symbol_eligible=task_family in B2_SYMBOL_ELIGIBLE_FAMILIES,
                        graph_eligible=task_family in B2_GRAPH_ELIGIBLE_FAMILIES,
                        support_eligible=task_family in B2_SUPPORT_ELIGIBLE_FAMILIES,
                    )
                )
    return tuple(slots)


def validate_task_slots(slots: Sequence[B2TaskSlot]) -> list[str]:
    errors: list[str] = []
    if len(slots) != B2_TASK_COUNT:
        errors.append(f"task slot count must be {B2_TASK_COUNT}")
    if len({slot.slot_id for slot in slots}) != len(slots):
        errors.append("task slot ids must be unique")
    if len({slot.repo_slot for slot in slots}) != B2_REPO_SLOT_COUNT:
        errors.append(f"repo slot count must be {B2_REPO_SLOT_COUNT}")
    for slot in slots:
        if slot.language not in B2_LANGUAGES:
            errors.append(f"unknown language: {slot.language}")
        if slot.size_band not in B2_SIZE_BANDS:
            errors.append(f"unknown size band: {slot.size_band}")
        if slot.role not in B2_TASK_ROLES:
            errors.append(f"unknown role: {slot.role}")
        if slot.task_family not in B2_TASK_FAMILIES:
            errors.append(f"unknown task family: {slot.task_family}")
        if slot.interaction_mode not in {"one_shot", "two_step"}:
            errors.append(f"unknown interaction mode: {slot.interaction_mode}")
        if slot.oracle_kind not in B2_ORACLE_KINDS:
            errors.append(f"unknown oracle kind: {slot.oracle_kind}")
        if slot.support_eligible != (slot.role == "relational"):
            errors.append(f"support eligibility drift: {slot.slot_id}")
        if slot.interaction_mode == "two_step" and not slot.support_eligible:
            errors.append(f"two-step task lacks support eligibility: {slot.slot_id}")
        if slot.task_family == "no_answer" and slot.oracle_kind != "abstain":
            errors.append(f"no-answer oracle drift: {slot.slot_id}")
        if slot.task_family == "ambiguous_target" and slot.oracle_kind != "multi_target":
            errors.append(f"ambiguous oracle drift: {slot.slot_id}")

    language_counts = Counter(slot.language for slot in slots)
    size_counts = Counter(slot.size_band for slot in slots)
    role_counts = Counter(slot.role for slot in slots)
    family_counts = Counter(slot.task_family for slot in slots)
    interaction_counts = Counter(slot.interaction_mode for slot in slots)
    oracle_counts = Counter(slot.oracle_kind for slot in slots)
    repo_counts = Counter(slot.repo_slot for slot in slots)

    if language_counts != Counter({language: 16 for language in B2_LANGUAGES}):
        errors.append("language margins must be 16/16/16")
    if size_counts != Counter({size: 12 for size in B2_SIZE_BANDS}):
        errors.append("size margins must be 12 each")
    if role_counts != Counter({role: 12 for role in B2_TASK_ROLES}):
        errors.append("role margins must be 12 each")
    if any(count != B2_TASKS_PER_REPO_SLOT for count in repo_counts.values()):
        errors.append("each repository slot must contain four tasks")
    expected_family_counts = Counter(
        {
            **{
                family: 4
                for family in (
                    *B2_DIRECT_FAMILIES,
                    *B2_RELATIONAL_FAMILIES,
                    *B2_WORKFLOW_FAMILIES,
                )
            },
            "ambiguous_target": 6,
            "no_answer": 6,
        }
    )
    if family_counts != expected_family_counts:
        errors.append("task family margins drifted")
    if interaction_counts != Counter(
        {"one_shot": B2_ONE_SHOT_TASK_COUNT, "two_step": B2_TWO_STEP_TASK_COUNT}
    ):
        errors.append("interaction margins drifted")
    if oracle_counts != Counter(
        {
            "deterministic": 36,
            "multi_target": B2_AMBIGUOUS_TASK_COUNT,
            "abstain": B2_NO_ANSWER_TASK_COUNT,
        }
    ):
        errors.append("oracle-kind margins drifted")

    eligibility_expected = {
        "literal": B2_SUBSET_DENOMINATORS["literal"],
        "symbol": B2_SUBSET_DENOMINATORS["symbol"],
        "graph": B2_SUBSET_DENOMINATORS["graph"],
        "support": B2_SUBSET_DENOMINATORS["support"],
    }
    eligibility_actual = {
        "literal": sum(slot.literal_eligible for slot in slots),
        "symbol": sum(slot.symbol_eligible for slot in slots),
        "graph": sum(slot.graph_eligible for slot in slots),
        "support": sum(slot.support_eligible for slot in slots),
    }
    if eligibility_actual != eligibility_expected:
        errors.append("component-eligibility margins drifted")
    return sorted(set(errors))


def task_slot_digest(slots: Sequence[B2TaskSlot] | None = None) -> str:
    rows = [slot.to_dict() for slot in (slots or build_task_slots())]
    return _prefixed_digest("b2slots_", rows)


def build_execution_schedule(
    slots: Sequence[B2TaskSlot] | None = None,
) -> tuple[B2ScheduleRow, ...]:
    task_slots = tuple(slots or build_task_slots())
    by_repo_role: dict[str, dict[str, B2TaskSlot]] = defaultdict(dict)
    for slot in task_slots:
        by_repo_role[slot.repo_slot][slot.role] = slot

    stable_repo_slots = tuple(sorted(by_repo_role))
    stable_repo_index = {repo_slot: index for index, repo_slot in enumerate(stable_repo_slots)}
    language_index = {value: index for index, value in enumerate(B2_LANGUAGES)}
    size_index = {value: index for index, value in enumerate(B2_SIZE_BANDS)}
    role_index = {value: index for index, value in enumerate(B2_TASK_ROLES)}
    base_arm_order = _seeded_order(B2_ADAPTER_IDS, "base-arm-order")
    rows: list[B2ScheduleRow] = []

    for repetition in B2_REPETITIONS:
        repo_order = _seeded_order(stable_repo_slots, f"repo-order-repetition-{repetition}")
        for repo_slot in repo_order:
            repo_index = stable_repo_index[repo_slot]
            cold_role_index = (repo_index + repetition - 1) % len(B2_TASK_ROLES)
            role_order = _rotate(B2_TASK_ROLES, cold_role_index)
            for task_position, role in enumerate(role_order, start=1):
                slot = by_repo_role[repo_slot][role]
                rotation = (
                    B2_ARM_ROTATION_COEFFICIENTS["language"]
                    * language_index[slot.language]
                    + B2_ARM_ROTATION_COEFFICIENTS["size_band"]
                    * size_index[slot.size_band]
                    + B2_ARM_ROTATION_COEFFICIENTS["role"]
                    * role_index[slot.role]
                    + B2_ARM_ROTATION_COEFFICIENTS["repetition"]
                    * (repetition - 1)
                ) % len(B2_ADAPTER_IDS)
                rows.append(
                    B2ScheduleRow(
                        slot_id=slot.slot_id,
                        repo_slot=repo_slot,
                        repetition=repetition,
                        cache_state="cold" if task_position == 1 else "warm",
                        task_position=task_position,
                        arm_order=_rotate(base_arm_order, rotation),
                    )
                )
    return tuple(rows)


def validate_execution_schedule(
    rows: Sequence[B2ScheduleRow],
    slots: Sequence[B2TaskSlot] | None = None,
) -> list[str]:
    errors: list[str] = []
    task_slots = tuple(slots or build_task_slots())
    slot_by_id = {slot.slot_id: slot for slot in task_slots}
    expected_rows = B2_TASK_COUNT * len(B2_REPETITIONS)
    if len(rows) != expected_rows:
        errors.append(f"schedule row count must be {expected_rows}")
    keys = [(row.slot_id, row.repetition) for row in rows]
    if len(set(keys)) != len(keys):
        errors.append("schedule slot/repetition keys must be unique")

    per_slot_cache: dict[str, Counter[str]] = defaultdict(Counter)
    per_repo_rep_cache: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    arm_position_counts: Counter[tuple[str, int]] = Counter()
    arm_position_counts_by_rep: Counter[tuple[int, str, int]] = Counter()
    arm_position_counts_by_language: Counter[tuple[str, str, int]] = Counter()
    arm_position_counts_by_size: Counter[tuple[str, str, int]] = Counter()
    arm_position_counts_by_role: Counter[tuple[str, str, int]] = Counter()
    record_count = 0

    for row in rows:
        if row.slot_id not in slot_by_id:
            errors.append(f"unknown scheduled slot: {row.slot_id}")
            continue
        slot = slot_by_id[row.slot_id]
        if row.repo_slot != slot.repo_slot:
            errors.append(f"repo slot mismatch: {row.slot_id}")
        if row.repetition not in B2_REPETITIONS:
            errors.append(f"invalid repetition: {row.repetition}")
        if row.cache_state not in {"cold", "warm"}:
            errors.append(f"invalid cache state: {row.cache_state}")
        if row.task_position not in {1, 2, 3, 4}:
            errors.append(f"invalid task position: {row.task_position}")
        if row.cache_state == "cold" and row.task_position != 1:
            errors.append(f"cold task must be first: {row.slot_id}")
        if row.cache_state == "warm" and row.task_position == 1:
            errors.append(f"first task must be cold: {row.slot_id}")
        if set(row.arm_order) != set(B2_ADAPTER_IDS) or len(row.arm_order) != B2_ADAPTER_COUNT:
            errors.append(f"arm order is not an exact permutation: {row.slot_id}")
        per_slot_cache[row.slot_id][row.cache_state] += 1
        per_repo_rep_cache[(row.repo_slot, row.repetition)][row.cache_state] += 1
        for position, adapter_id in enumerate(row.arm_order, start=1):
            arm_position_counts[(adapter_id, position)] += 1
            arm_position_counts_by_rep[(row.repetition, adapter_id, position)] += 1
            arm_position_counts_by_language[(slot.language, adapter_id, position)] += 1
            arm_position_counts_by_size[(slot.size_band, adapter_id, position)] += 1
            arm_position_counts_by_role[(slot.role, adapter_id, position)] += 1
        record_count += B2_ADAPTER_COUNT * (2 if slot.interaction_mode == "two_step" else 1)

    for slot in task_slots:
        counts = per_slot_cache[slot.slot_id]
        if counts != Counter(
            {
                "cold": B2_COLD_OBSERVATIONS_PER_TASK,
                "warm": B2_WARM_OBSERVATIONS_PER_TASK,
            }
        ):
            errors.append(f"cold/warm rotation drift: {slot.slot_id}")
    for repo_slot in sorted({slot.repo_slot for slot in task_slots}):
        for repetition in B2_REPETITIONS:
            if per_repo_rep_cache[(repo_slot, repetition)] != Counter({"cold": 1, "warm": 3}):
                errors.append(f"repo split-plot cache drift: {repo_slot}/{repetition}")

    expected_position_count = len(rows) // B2_ADAPTER_COUNT
    expected_position_count_per_rep = (B2_TASK_COUNT // B2_ADAPTER_COUNT)
    for adapter_id in B2_ADAPTER_IDS:
        for position in range(1, B2_ADAPTER_COUNT + 1):
            if arm_position_counts[(adapter_id, position)] != expected_position_count:
                errors.append(f"global arm-position imbalance: {adapter_id}/{position}")
            for repetition in B2_REPETITIONS:
                if (
                    arm_position_counts_by_rep[(repetition, adapter_id, position)]
                    != expected_position_count_per_rep
                ):
                    errors.append(
                        f"per-repetition arm-position imbalance: "
                        f"{repetition}/{adapter_id}/{position}"
                    )
            for size_band in B2_SIZE_BANDS:
                if arm_position_counts_by_size[(size_band, adapter_id, position)] != 8:
                    errors.append(
                        f"size arm-position imbalance: {size_band}/{adapter_id}/{position}"
                    )
            for role in B2_TASK_ROLES:
                if arm_position_counts_by_role[(role, adapter_id, position)] != 8:
                    errors.append(
                        f"role arm-position imbalance: {role}/{adapter_id}/{position}"
                    )
        for language in B2_LANGUAGES:
            language_position_values = [
                arm_position_counts_by_language[(language, adapter_id, position)]
                for position in range(1, B2_ADAPTER_COUNT + 1)
            ]
            if min(language_position_values) < 10 or max(language_position_values) > 12:
                errors.append(f"language arm-position imbalance: {language}/{adapter_id}")
    if record_count != B2_TOTAL_RECORDS:
        errors.append(f"schedule record count must be {B2_TOTAL_RECORDS}")
    return sorted(set(errors))


def execution_schedule_digest(
    rows: Sequence[B2ScheduleRow] | None = None,
) -> str:
    schedule = rows or build_execution_schedule()
    return _prefixed_digest("b2sched_", [row.to_dict() for row in schedule])


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in B2_SOURCE_BUNDLE_PATHS:
        if rel in seen:
            raise RuntimeError(f"duplicate B2 source bundle path: {rel}")
        seen.add(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"missing or unsafe B2 source bundle file: {rel}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"B2 source bundle path escapes repo: {rel}") from exc
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "path": rel,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def b2_source_bundle_digest(repo_root: Path | None = None) -> str:
    return _prefixed_digest("b2src_", _normalized_source_rows(repo_root))


def b2_spec_digest() -> str:
    payload = {
        "schema_version": B2_SCHEMA_VERSION,
        "parent_b1": {
            "source_checkpoint": B2_PARENT_B1_SOURCE_CHECKPOINT,
            "closeout_checkpoint": B2_PARENT_B1_CLOSEOUT_CHECKPOINT,
            "spec_version": B2_PARENT_B1_SPEC_VERSION,
            "spec_digest": B2_PARENT_B1_SPEC_DIGEST,
            "fixture_digest": B2_PARENT_B1_FIXTURE_DIGEST,
            "source_bundle_digest": B2_PARENT_B1_SOURCE_BUNDLE_DIGEST,
            "runtime_bundle_digest": B2_PARENT_B1_RUNTIME_BUNDLE_DIGEST,
        },
        "task_slots": [slot.to_dict() for slot in build_task_slots()],
        "size_band_visible_bytes": B2_SIZE_BAND_VISIBLE_BYTES,
        "visible_file_count_range": B2_VISIBLE_FILE_COUNT_RANGE,
        "repetitions": B2_REPETITIONS,
        "randomization_seed": B2_RANDOMIZATION_SEED,
        "randomization_policy": B2_RANDOMIZATION_POLICY,
        "arm_rotation_coefficients": B2_ARM_ROTATION_COEFFICIENTS,
        "lifecycle_policy": B2_LIFECYCLE_POLICY,
        "records": {
            "one_shot": B2_ONE_SHOT_RECORDS,
            "two_step": B2_TWO_STEP_RECORDS,
            "total": B2_TOTAL_RECORDS,
            "per_arm": B2_RECORDS_PER_ARM,
            "index_builds": B2_INDEX_BUILD_COUNT,
        },
        "metrics": B2_METRIC_DEFINITIONS,
        "task_admission_rules": B2_TASK_ADMISSION_RULES,
        "scoring_rules": B2_SCORING_RULES,
        "quality_floors": B2_QUALITY_FLOORS,
        "baseline_noninferiority": B2_BASELINE_NONINFERIORITY,
        "baseline_resource_ceilings": B2_BASELINE_RESOURCE_CEILINGS,
        "component_rules": B2_COMPONENT_RULES,
        "required_component_rules": B2_REQUIRED_COMPONENT_RULES,
        "decision_equivalence": B2_DECISION_EQUIVALENCE,
        "tie_policy": B2_TIE_POLICY,
        "hard_gates": B2_HARD_GATES,
        "forbidden_adaptations": B2_FORBIDDEN_ADAPTATIONS,
        "publication_policy": B2_PUBLICATION_POLICY,
    }
    return _prefixed_digest("b2spec_", payload, length=16)


def _validate_mapping_counts(
    name: str,
    pairs: tuple[tuple[str, int], ...],
    expected_keys: Sequence[str],
    capacities: Mapping[str, int],
    expected_sum: int | None = None,
) -> list[str]:
    errors: list[str] = []
    if len(pairs) != len(expected_keys) or len(dict(pairs)) != len(pairs):
        errors.append(f"{name} must have unique exact keys")
        return errors
    mapping = dict(pairs)
    if set(mapping) != set(expected_keys):
        errors.append(f"{name} key set mismatch")
        return errors
    for key, value in mapping.items():
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{name}.{key} must be integer")
        elif value < 0 or value > capacities[key]:
            errors.append(f"{name}.{key} outside 0..{capacities[key]}")
    if expected_sum is not None and sum(mapping.values()) != expected_sum:
        errors.append(f"{name} must sum to {expected_sum}")
    return errors


def validate_arm_summary(summary: B2ArmSummary) -> list[str]:
    errors: list[str] = []
    if summary.adapter_id not in B2_ADAPTER_IDS:
        errors.append("unknown adapter id")
    boolean_fields = (
        "matrix_complete",
        "safety_gates_passed",
        "determinism_confirmed",
        "source_immutable",
    )
    for field_name in boolean_fields:
        if not isinstance(getattr(summary, field_name), bool):
            errors.append(f"{field_name} must be boolean")

    integer_fields = (
        "record_count",
        "accepted_count",
        "rejected_count",
        "resource_complete_count",
        "provider_network_call_count",
        "invalid_citation_count",
        "timeout_count",
        "task_success_count",
        "answerable_target_success_count",
        "ambiguous_status_success_count",
        "no_answer_status_success_count",
        "support_success_count",
        "one_shot_success_count",
        "context_f05_sum_ppm",
        "harmful_evidence_task_count",
        "warm_query_p95_us",
        "peak_rss_p95_bytes",
        "cold_index_p95_us",
        "index_state_p95_bytes",
    )
    for field_name in integer_fields:
        value = getattr(summary, field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{field_name} must be a nonnegative integer")

    bounds = {
        "record_count": B2_RECORDS_PER_ARM,
        "accepted_count": B2_RECORDS_PER_ARM,
        "rejected_count": B2_RECORDS_PER_ARM,
        "resource_complete_count": B2_RECORDS_PER_ARM,
        "task_success_count": B2_TASK_COUNT,
        "answerable_target_success_count": B2_ANSWERABLE_TASK_COUNT,
        "ambiguous_status_success_count": B2_AMBIGUOUS_TASK_COUNT,
        "no_answer_status_success_count": B2_NO_ANSWER_TASK_COUNT,
        "support_success_count": B2_TWO_STEP_TASK_COUNT,
        "one_shot_success_count": B2_ONE_SHOT_TASK_COUNT,
        "context_f05_sum_ppm": B2_ANSWERABLE_TASK_COUNT * B2_FIXED_POINT_SCALE,
        "harmful_evidence_task_count": B2_ANSWERABLE_TASK_COUNT,
    }
    for field_name, upper in bounds.items():
        value = getattr(summary, field_name)
        if isinstance(value, int) and not isinstance(value, bool) and value > upper:
            errors.append(f"{field_name} exceeds {upper}")

    if summary.accepted_count + summary.rejected_count != summary.record_count:
        errors.append("accepted/rejected counts do not reconcile")
    if summary.task_success_count > (
        summary.answerable_target_success_count + summary.no_answer_status_success_count
    ):
        errors.append("task success exceeds possible target/no-answer successes")
    if summary.task_success_count != (
        summary.one_shot_success_count + summary.support_success_count
    ):
        errors.append("task success must equal one-shot plus support success")

    errors.extend(
        _validate_mapping_counts(
            "language_success_counts",
            summary.language_success_counts,
            B2_LANGUAGES,
            {language: 16 for language in B2_LANGUAGES},
            summary.task_success_count,
        )
    )
    if summary.subset_counts().get("support") != summary.support_success_count:
        errors.append("support subset success must equal support success count")
    errors.extend(
        _validate_mapping_counts(
            "size_success_counts",
            summary.size_success_counts,
            B2_SIZE_BANDS,
            {size: 12 for size in B2_SIZE_BANDS},
            summary.task_success_count,
        )
    )
    errors.extend(
        _validate_mapping_counts(
            "role_success_counts",
            summary.role_success_counts,
            B2_TASK_ROLES,
            {role: 12 for role in B2_TASK_ROLES},
            summary.task_success_count,
        )
    )
    errors.extend(
        _validate_mapping_counts(
            "subset_success_counts",
            summary.subset_success_counts,
            tuple(B2_SUBSET_DENOMINATORS),
            B2_SUBSET_DENOMINATORS,
        )
    )
    context_capacities = {
        key: denominator * B2_FIXED_POINT_SCALE
        for key, denominator in B2_SUBSET_DENOMINATORS.items()
    }
    errors.extend(
        _validate_mapping_counts(
            "subset_context_f05_sum_ppm",
            summary.subset_context_f05_sum_ppm,
            tuple(B2_SUBSET_DENOMINATORS),
            context_capacities,
        )
    )
    return sorted(set(errors))


def _ratio_or_additive_ok(
    child: int,
    parent: int,
    ratio_ppm: int,
    additive: int = 0,
) -> bool:
    if parent <= 0:
        return False
    ratio_limit = (parent * ratio_ppm) // B2_FIXED_POINT_SCALE
    return child <= max(ratio_limit, parent + additive)


def _integrity_reasons(summary: B2ArmSummary) -> list[str]:
    reasons: list[str] = []
    if summary.record_count != B2_RECORDS_PER_ARM:
        reasons.append("record_count_incomplete")
    if summary.accepted_count != B2_RECORDS_PER_ARM or summary.rejected_count != 0:
        reasons.append("records_not_all_accepted")
    if summary.resource_complete_count != B2_RECORDS_PER_ARM:
        reasons.append("resource_samples_incomplete")
    if not summary.matrix_complete:
        reasons.append("matrix_incomplete")
    if not summary.safety_gates_passed:
        reasons.append("safety_gates_failed")
    if not summary.determinism_confirmed:
        reasons.append("quality_semantics_not_deterministic")
    if not summary.source_immutable:
        reasons.append("source_mutated")
    if summary.provider_network_call_count != 0:
        reasons.append("provider_network_calls_nonzero")
    if summary.invalid_citation_count != 0:
        reasons.append("invalid_citations_nonzero")
    if summary.timeout_count != 0:
        reasons.append("timeouts_nonzero")
    return reasons


def _candidate_gate_reasons(
    summary: B2ArmSummary,
    baseline: B2ArmSummary,
) -> list[str]:
    reasons = _integrity_reasons(summary)
    floors = B2_QUALITY_FLOORS
    if summary.task_success_count < floors["task_success_count"]:
        reasons.append("overall_task_success_below_floor")
    if summary.one_shot_success_count < floors["one_shot_success_count"]:
        reasons.append("one_shot_success_below_floor")
    if summary.answerable_target_success_count < floors["answerable_target_success_count"]:
        reasons.append("answerable_target_success_below_floor")
    if summary.ambiguous_status_success_count < floors["ambiguous_status_success_count"]:
        reasons.append("ambiguous_status_success_below_floor")
    if summary.no_answer_status_success_count < floors["no_answer_status_success_count"]:
        reasons.append("no_answer_status_success_below_floor")
    if summary.harmful_evidence_task_count > floors["max_harmful_evidence_task_count"]:
        reasons.append("harmful_evidence_above_ceiling")
    if min(summary.language_counts().values()) < floors["language_success_floor_each_of_16"]:
        reasons.append("language_stratum_below_floor")
    if min(summary.size_counts().values()) < floors["size_success_floor_each_of_12"]:
        reasons.append("size_stratum_below_floor")
    if min(summary.role_counts().values()) < floors["role_success_floor_each_of_12"]:
        reasons.append("role_stratum_below_floor")

    noninferiority = B2_BASELINE_NONINFERIORITY
    if summary.task_success_count < (
        baseline.task_success_count - noninferiority["max_task_success_loss"]
    ):
        reasons.append("task_success_inferior_to_s0")
    if summary.answerable_target_success_count < (
        baseline.answerable_target_success_count
        - noninferiority["max_target_success_loss"]
    ):
        reasons.append("target_success_inferior_to_s0")
    context_loss_limit = (
        B2_ANSWERABLE_TASK_COUNT
        * noninferiority["max_context_f05_average_loss_ppm"]
    )
    if summary.context_f05_sum_ppm < baseline.context_f05_sum_ppm - context_loss_limit:
        reasons.append("context_quality_inferior_to_s0")
    if summary.harmful_evidence_task_count > (
        baseline.harmful_evidence_task_count
        + noninferiority["max_harmful_evidence_extra_tasks"]
    ):
        reasons.append("harmful_evidence_worse_than_s0")

    resource = B2_BASELINE_RESOURCE_CEILINGS
    if not _ratio_or_additive_ok(
        summary.warm_query_p95_us,
        baseline.warm_query_p95_us,
        resource["warm_query_ratio_ppm"],
        resource["warm_query_additive_us"],
    ):
        reasons.append("warm_query_cost_above_s0_ceiling")
    if not _ratio_or_additive_ok(
        summary.peak_rss_p95_bytes,
        baseline.peak_rss_p95_bytes,
        resource["peak_rss_ratio_ppm"],
        resource["peak_rss_additive_bytes"],
    ):
        reasons.append("rss_cost_above_s0_ceiling")
    if not _ratio_or_additive_ok(
        summary.cold_index_p95_us,
        baseline.cold_index_p95_us,
        resource["cold_index_ratio_ppm"],
        resource["cold_index_additive_us"],
    ):
        reasons.append("cold_index_cost_above_s0_ceiling")
    if not _ratio_or_additive_ok(
        summary.index_state_p95_bytes,
        baseline.index_state_p95_bytes,
        resource["index_state_ratio_ppm"],
        resource["index_state_additive_bytes"],
    ):
        reasons.append("index_state_cost_above_s0_ceiling")
    return sorted(set(reasons))


def evaluate_component_rules(
    summaries: Mapping[str, B2ArmSummary],
) -> dict[str, dict[str, Any]]:
    outcomes: dict[str, dict[str, Any]] = {}
    for rule in B2_COMPONENT_RULES:
        child = summaries[rule["child"]]
        parent = summaries[rule["parent"]]
        subset = str(rule["subset"])
        denominator = B2_SUBSET_DENOMINATORS[subset]
        success_gain = child.subset_counts()[subset] - parent.subset_counts()[subset]
        context_gain = (
            child.subset_context()[subset] - parent.subset_context()[subset]
        )
        minimum_context_gain = (
            denominator * int(rule["alternative_context_mean_gain_ppm"])
        )
        quality_earned = (
            success_gain >= int(rule["minimum_success_gain"])
            or (
                bool(rule["allow_context_alternative"])
                and context_gain >= minimum_context_gain
            )
        )
        regression_metric = str(rule["regression_metric"])
        child_regression_value = int(getattr(child, regression_metric))
        parent_regression_value = int(getattr(parent, regression_metric))
        no_primary_regression = child_regression_value >= (
            parent_regression_value - int(rule["max_overall_task_loss"])
        )
        no_harm_regression = child.harmful_evidence_task_count <= (
            parent.harmful_evidence_task_count
            + int(rule["max_harmful_evidence_extra_tasks"])
        )
        latency_ok = _ratio_or_additive_ok(
            child.warm_query_p95_us,
            parent.warm_query_p95_us,
            int(rule["max_warm_query_ratio_ppm"]),
        )
        rss_ok = _ratio_or_additive_ok(
            child.peak_rss_p95_bytes,
            parent.peak_rss_p95_bytes,
            int(rule["max_peak_rss_ratio_ppm"]),
        )
        passed = all(
            (quality_earned, no_primary_regression, no_harm_regression, latency_ok, rss_ok)
        )
        outcomes[str(rule["rule_id"])] = {
            "passed": passed,
            "success_gain": success_gain,
            "context_f05_sum_gain_ppm": context_gain,
            "quality_earned": quality_earned,
            "regression_metric": regression_metric,
            "no_primary_regression": no_primary_regression,
            "no_harm_regression": no_harm_regression,
            "latency_ok": latency_ok,
            "rss_ok": rss_ok,
        }
    return outcomes


def quality_vector(summary: B2ArmSummary) -> tuple[int, ...]:
    return (
        summary.task_success_count,
        summary.answerable_target_success_count,
        summary.ambiguous_status_success_count + summary.no_answer_status_success_count,
        summary.support_success_count,
        summary.context_f05_sum_ppm,
        -summary.harmful_evidence_task_count,
    )


def competition_ranks(
    summaries: Iterable[B2ArmSummary],
) -> dict[str, int]:
    ordered = sorted(
        summaries,
        key=lambda summary: (quality_vector(summary), summary.adapter_id),
        reverse=True,
    )
    ranks: dict[str, int] = {}
    previous_vector: tuple[int, ...] | None = None
    current_rank = 0
    for position, summary in enumerate(ordered, start=1):
        vector = quality_vector(summary)
        if previous_vector is None or vector != previous_vector:
            current_rank = position
            previous_vector = vector
        ranks[summary.adapter_id] = current_rank
    return ranks


def resource_vector(summary: B2ArmSummary) -> tuple[int, ...]:
    return (
        summary.warm_query_p95_us,
        summary.peak_rss_p95_bytes,
        summary.cold_index_p95_us,
        summary.index_state_p95_bytes,
    )


def resource_competition_ranks(
    summaries: Iterable[B2ArmSummary],
) -> dict[str, int]:
    ordered = sorted(
        summaries,
        key=lambda summary: (resource_vector(summary), summary.adapter_id),
    )
    ranks: dict[str, int] = {}
    previous_vector: tuple[int, ...] | None = None
    current_rank = 0
    for position, summary in enumerate(ordered, start=1):
        vector = resource_vector(summary)
        if previous_vector is None or vector != previous_vector:
            current_rank = position
            previous_vector = vector
        ranks[summary.adapter_id] = current_rank
    return ranks


def decision_equivalent(candidate: B2ArmSummary, best: B2ArmSummary) -> bool:
    margin = B2_DECISION_EQUIVALENCE
    if candidate.task_success_count < best.task_success_count - margin["max_task_success_loss"]:
        return False
    if candidate.answerable_target_success_count < (
        best.answerable_target_success_count - margin["max_target_success_loss"]
    ):
        return False
    candidate_status = (
        candidate.ambiguous_status_success_count + candidate.no_answer_status_success_count
    )
    best_status = best.ambiguous_status_success_count + best.no_answer_status_success_count
    if candidate_status < best_status - margin["max_status_success_loss"]:
        return False
    if candidate.support_success_count < (
        best.support_success_count - margin["max_support_success_loss"]
    ):
        return False
    context_loss_limit = (
        B2_ANSWERABLE_TASK_COUNT * margin["max_context_f05_average_loss_ppm"]
    )
    if candidate.context_f05_sum_ppm < best.context_f05_sum_ppm - context_loss_limit:
        return False
    if candidate.harmful_evidence_task_count > (
        best.harmful_evidence_task_count + margin["max_harmful_evidence_extra_tasks"]
    ):
        return False
    if not _ratio_or_additive_ok(
        candidate.warm_query_p95_us,
        best.warm_query_p95_us,
        margin["max_warm_query_ratio_ppm"],
        margin["max_warm_query_additive_us"],
    ):
        return False
    if not _ratio_or_additive_ok(
        candidate.peak_rss_p95_bytes,
        best.peak_rss_p95_bytes,
        margin["max_peak_rss_ratio_ppm"],
        margin["max_peak_rss_additive_bytes"],
    ):
        return False
    return True


def evaluate_tournament(
    summaries: Sequence[B2ArmSummary],
) -> dict[str, Any]:
    if len(summaries) != B2_ADAPTER_COUNT:
        raise ValueError(f"expected {B2_ADAPTER_COUNT} arm summaries")
    by_id = {summary.adapter_id: summary for summary in summaries}
    if set(by_id) != set(B2_ADAPTER_IDS) or len(by_id) != len(summaries):
        raise ValueError("arm summaries must contain each S0-S5 adapter exactly once")
    validation_errors = {
        adapter_id: validate_arm_summary(summary)
        for adapter_id, summary in by_id.items()
    }
    if any(validation_errors.values()):
        raise ValueError("invalid arm summary: " + _canonical(validation_errors))

    baseline = by_id[B2_BASELINE_CONTROL_ARM]
    baseline_reasons = _integrity_reasons(baseline)
    if baseline_reasons:
        return {
            "verdict": "invalid_tournament_baseline_failed",
            "baseline_control": B2_BASELINE_CONTROL_ARM,
            "baseline_failure_reasons": baseline_reasons,
            "component_rule_outcomes": {},
            "candidate_failure_reasons": {},
            "quality_ranks": {},
            "resource_ranks": {},
            "default_track_eligible": [],
            "optional_track_eligible": [],
            "phase_c_internal_shortlist": [],
        }

    component_outcomes = evaluate_component_rules(by_id)
    candidate_failure_reasons: dict[str, list[str]] = {}
    eligible: list[B2ArmSummary] = []
    for adapter_id in (*B2_OPTIONAL_TRACK_ARMS, *B2_DEFAULT_TRACK_ARMS):
        summary = by_id[adapter_id]
        reasons = _candidate_gate_reasons(summary, baseline)
        for rule_id in B2_REQUIRED_COMPONENT_RULES[adapter_id]:
            if not component_outcomes[rule_id]["passed"]:
                reasons.append(f"component_rule_failed:{rule_id}")
        if adapter_id in B2_DEFAULT_TRACK_ARMS and summary.support_success_count < (
            B2_QUALITY_FLOORS["default_track_support_success_count"]
        ):
            reasons.append("default_track_support_below_floor")
        if adapter_id in B2_DEFAULT_TRACK_ARMS and summary.task_success_count < (
            B2_QUALITY_FLOORS["default_track_task_success_count"]
        ):
            reasons.append("default_track_task_success_below_floor")
        reasons = sorted(set(reasons))
        candidate_failure_reasons[adapter_id] = reasons
        if not reasons:
            eligible.append(summary)

    ranks = competition_ranks(eligible)
    resource_ranks = resource_competition_ranks(eligible)
    default_eligible = sorted(
        summary.adapter_id
        for summary in eligible
        if summary.adapter_id in B2_DEFAULT_TRACK_ARMS
    )
    optional_eligible = sorted(
        summary.adapter_id
        for summary in eligible
        if summary.adapter_id in B2_OPTIONAL_TRACK_ARMS
    )

    comparison_pool = (
        [by_id[adapter_id] for adapter_id in default_eligible]
        if default_eligible
        else [by_id[adapter_id] for adapter_id in optional_eligible]
    )
    shortlist: list[str] = []
    if comparison_pool:
        best = max(comparison_pool, key=lambda summary: quality_vector(summary))
        shortlist = sorted(
            summary.adapter_id
            for summary in comparison_pool
            if decision_equivalent(summary, best)
        )

    if not shortlist:
        verdict = "no_internal_finalist"
    elif len(shortlist) == 1:
        verdict = "single_internal_finalist_for_phase_c"
    else:
        verdict = "multiple_decision_equivalent_internal_finalists_for_phase_c"
    return {
        "verdict": verdict,
        "baseline_control": B2_BASELINE_CONTROL_ARM,
        "baseline_failure_reasons": [],
        "component_rule_outcomes": component_outcomes,
        "candidate_failure_reasons": candidate_failure_reasons,
        "quality_ranks": dict(sorted(ranks.items())),
        "resource_ranks": dict(sorted(resource_ranks.items())),
        "default_track_eligible": default_eligible,
        "optional_track_eligible": optional_eligible,
        "phase_c_internal_shortlist": shortlist,
    }


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _build_report_without_protocol_digest() -> dict[str, Any]:
    slots = build_task_slots()
    schedule = build_execution_schedule(slots)
    slot_errors = validate_task_slots(slots)
    schedule_errors = validate_execution_schedule(schedule, slots)
    if slot_errors or schedule_errors:
        raise RuntimeError(
            "internal B2 design invalid: " + _canonical(slot_errors + schedule_errors)
        )
    return {
        "schema_version": B2_REPORT_SCHEMA_VERSION,
        "phase": B2_PHASE,
        "status": B2_STATUS,
        "claim_level": B2_CLAIM_LEVEL,
        "parent_b1_lock": {
            "source_checkpoint": B2_PARENT_B1_SOURCE_CHECKPOINT,
            "closeout_checkpoint": B2_PARENT_B1_CLOSEOUT_CHECKPOINT,
            "spec_version": B2_PARENT_B1_SPEC_VERSION,
            "spec_digest": B2_PARENT_B1_SPEC_DIGEST,
            "fixture_digest": B2_PARENT_B1_FIXTURE_DIGEST,
            "source_bundle_digest": B2_PARENT_B1_SOURCE_BUNDLE_DIGEST,
            "runtime_bundle_digest": B2_PARENT_B1_RUNTIME_BUNDLE_DIGEST,
            "public_aggregate": B2_PARENT_B1_AGGREGATE_REL,
            "mechanics_pass_required": True,
        },
        "execution_boundary": {
            "design_only": True,
            "empirical_task_materialization_executed": False,
            "private_oracle_rows_read": False,
            "adapter_execution_executed": False,
            "tournament_scoring_executed": False,
            "winner_or_default_selected": False,
            "provider_or_network_calls_executed": False,
        },
        "experimental_design": {
            "design_type": "randomized_complete_task_blocks_with_repo_split_plot_lifecycle",
            "experimental_unit": "logical_task",
            "independent_unit_count": B2_TASK_COUNT,
            "treatments": list(B2_ADAPTER_IDS),
            "complete_block": "every_task_receives_all_six_stacks",
            "repository_is_nested_cluster": True,
            "cache_and_repetition_are_technical_repeated_measures": True,
            "technical_measurements_do_not_increase_independent_n": True,
            "analysis_unit": "paired_task_level_outcomes_with_repository_cluster_respected",
            "interim_looks": 0,
            "single_final_analysis_only": True,
        },
        "task_frame": {
            "task_slot_count": B2_TASK_COUNT,
            "repo_slot_count": B2_REPO_SLOT_COUNT,
            "tasks_per_repo_slot": B2_TASKS_PER_REPO_SLOT,
            "languages": list(B2_LANGUAGES),
            "language_counts": _counter_dict(slot.language for slot in slots),
            "size_bands": list(B2_SIZE_BANDS),
            "size_band_visible_bytes_half_open": {
                key: list(value) for key, value in B2_SIZE_BAND_VISIBLE_BYTES.items()
            },
            "visible_file_count_range_inclusive": list(B2_VISIBLE_FILE_COUNT_RANGE),
            "size_counts": _counter_dict(slot.size_band for slot in slots),
            "role_counts": _counter_dict(slot.role for slot in slots),
            "task_family_counts": _counter_dict(slot.task_family for slot in slots),
            "oracle_kind_counts": _counter_dict(slot.oracle_kind for slot in slots),
            "interaction_counts": _counter_dict(slot.interaction_mode for slot in slots),
            "component_eligible_counts": {
                "literal": sum(slot.literal_eligible for slot in slots),
                "symbol": sum(slot.symbol_eligible for slot in slots),
                "graph": sum(slot.graph_eligible for slot in slots),
                "support": sum(slot.support_eligible for slot in slots),
            },
            "task_slot_digest": task_slot_digest(slots),
            "actual_repo_identity_and_task_text_private_until_aggregate_release": True,
            "task_and_oracle_manifests_frozen_before_any_arm_output": True,
            "admission_rules": dict(B2_TASK_ADMISSION_RULES),
        },
        "lifecycle_matrix": {
            "repetitions": list(B2_REPETITIONS),
            "cold_observations_per_task": B2_COLD_OBSERVATIONS_PER_TASK,
            "warm_observations_per_task": B2_WARM_OBSERVATIONS_PER_TASK,
            "one_cold_plus_three_warm_per_task": True,
            "one_index_build_per_repo_arm_repetition": True,
            "index_build_count": B2_INDEX_BUILD_COUNT,
            "one_shot_records": B2_ONE_SHOT_RECORDS,
            "two_step_records": B2_TWO_STEP_RECORDS,
            "total_records": B2_TOTAL_RECORDS,
            "records_per_arm": B2_RECORDS_PER_ARM,
            "two_step_order": ["context", "support"],
            "lifecycle_policy": B2_LIFECYCLE_POLICY,
        },
        "randomization": {
            "seed": B2_RANDOMIZATION_SEED,
            "policy": B2_RANDOMIZATION_POLICY,
            "arm_rotation_coefficients_mod_6": dict(B2_ARM_ROTATION_COEFFICIENTS),
            "schedule_digest": execution_schedule_digest(schedule),
            "schedule_row_count": len(schedule),
            "each_task_cold_once_warm_three_times": True,
            "each_repo_repetition_has_one_cold_three_warm_tasks": True,
            "each_arm_appears_equally_in_each_execution_position": True,
            "arm_position_count_each_overall": len(schedule) // B2_ADAPTER_COUNT,
            "arm_position_count_each_per_repetition": B2_TASK_COUNT // B2_ADAPTER_COUNT,
            "arm_positions_exactly_balanced_within_each_size_role_and_repetition": True,
            "language_arm_position_count_range_inclusive": [10, 12],
            "arm_order_is_constrained_randomization_not_adaptive": True,
        },
        "metric_contract": {
            "fixed_point_scale": B2_FIXED_POINT_SCALE,
            "metric_definitions": dict(B2_METRIC_DEFINITIONS),
            "scoring_rules": dict(B2_SCORING_RULES),
            "subset_denominators": dict(B2_SUBSET_DENOMINATORS),
            "quality_semantics_must_match_across_cache_and_repetitions": True,
            "resource_samples_are_repeated_measurements_not_independent_tasks": True,
            "no_opaque_single_composite_score": True,
            "quality_and_resource_ranks_reported_separately": True,
        },
        "hard_gates": dict(B2_HARD_GATES),
        "promotion_contract": {
            "baseline_control_arm": B2_BASELINE_CONTROL_ARM,
            "baseline_retained_for_phase_c_and_d_even_if_not_promoted": True,
            "quality_floors": dict(B2_QUALITY_FLOORS),
            "baseline_noninferiority": dict(B2_BASELINE_NONINFERIORITY),
            "baseline_resource_ceilings": dict(B2_BASELINE_RESOURCE_CEILINGS),
            "component_rules": [dict(rule) for rule in B2_COMPONENT_RULES],
            "required_component_rules": {
                key: list(value) for key, value in B2_REQUIRED_COMPONENT_RULES.items()
            },
            "default_track_arms": list(B2_DEFAULT_TRACK_ARMS),
            "optional_track_arms": list(B2_OPTIONAL_TRACK_ARMS),
            "decision_equivalence": dict(B2_DECISION_EQUIVALENCE),
            "phase_c_shortlist_prefers_default_track_when_any_default_arm_passes": True,
            "no_arm_automatically_promoted": True,
            "zero_one_or_multiple_finalists_are_valid_outcomes": True,
        },
        "tie_policy": dict(B2_TIE_POLICY),
        "privacy_publication": dict(B2_PUBLICATION_POLICY),
        "forbidden_adaptations": list(B2_FORBIDDEN_ADAPTATIONS),
        "source_locks": {
            "b2_spec_digest": b2_spec_digest(),
            "b2_source_bundle_digest": b2_source_bundle_digest(),
            "line_endings_normalized_for_cross_platform_source_digest": True,
            "runtime_bundle_must_be_single_and_frozen_before_execution": True,
            "mixed_runtime_bundles_in_one_tournament_forbidden": True,
        },
        "implementation_readiness": {
            "private_repository_admission_implemented": True,
            "offline_task_and_oracle_authoring_implemented": True,
            "all_six_b1_adapter_wrappers_implemented": True,
            "split_plot_runner_implemented": True,
            "isolated_scorer_and_aggregate_publication_implemented": True,
            "single_cli_for_self_fault_prepare_freeze_run_and_validate": True,
            "real_repository_preflight_required_before_freeze": True,
            "full_tournament_execution_is_not_part_of_this_protocol_report": True,
        },
        "next_authorized_action": (
            "freeze the prepared private repository/task/oracle manifests and one "
            "runtime bundle, confirm protocol/self/fault/privacy/bundle preflight, then "
            "run the complete matrix locally under ignored runs without interim looks"
        ),
    }


def build_report() -> dict[str, Any]:
    report = _build_report_without_protocol_digest()
    report["protocol_digest"] = _prefixed_digest("b2protocol_", report)
    return report


_PRIVATE_KEYS = {
    "task_id",
    "query",
    "path",
    "range",
    "excerpt",
    "snippet",
    "content_hash",
    "source_hash",
    "label",
    "oracle_row",
    "run_dir",
    "provider_payload",
    "api_key",
}
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|^/home/|^/tmp/|^/Users/|^/var/)")
_CANARY_RE = re.compile(r"canary_[0-9a-f]{32}")
_SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{10,}|github_pat_|AKIA[0-9A-Z]{16})"
)


def scan_public_report(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text in _PRIVATE_KEYS:
                errors.append(f"private key forbidden: {child_path}")
            errors.extend(scan_public_report(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_public_report(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if _ABSOLUTE_PATH_RE.search(value):
            errors.append(f"absolute path forbidden: {path}")
        if _CANARY_RE.search(value):
            errors.append(f"private canary forbidden: {path}")
        if _SECRET_RE.search(value):
            errors.append(f"secret-shaped value forbidden: {path}")
        if ".env.local" in lowered or "runs/" in lowered or "runs\\" in lowered:
            errors.append(f"private path marker forbidden: {path}")
    return sorted(set(errors))


def _diff_values(expected: Any, actual: Any, path: str = "$") -> list[str]:
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
            errors.extend(_diff_values(expected[key], actual[key], f"{path}.{key}"))
        return errors
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"{path}: list length drift"]
        errors: list[str] = []
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            errors.extend(_diff_values(expected_item, actual_item, f"{path}[{index}]"))
        return errors
    if expected != actual:
        return [f"{path}: value drift"]
    return []


def validate_parent_b1_public_aggregate() -> list[str]:
    path = REPO / B2_PARENT_B1_AGGREGATE_REL
    if path.is_symlink() or not path.is_file():
        return ["parent B1 public aggregate missing or unsafe"]
    try:
        aggregate = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail closed with type only
        return [f"parent B1 aggregate unreadable: {type(exc).__name__}"]
    expected = {
        "mechanics_pass": True,
        "total_records": 504,
        "accepted_count": 504,
        "rejected_count": 0,
        "all_six_stacks_passing": True,
        "zero_provider_network_calls": True,
        "fixture_digest": B2_PARENT_B1_FIXTURE_DIGEST,
        "spec_digest": B2_PARENT_B1_SPEC_DIGEST,
        "source_bundle_digest": B2_PARENT_B1_SOURCE_BUNDLE_DIGEST,
        "runtime_bundle_digest": B2_PARENT_B1_RUNTIME_BUNDLE_DIGEST,
    }
    errors = []
    for key, value in expected.items():
        if aggregate.get(key) != value:
            errors.append(f"parent B1 aggregate drift: {key}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be an object"]
    errors = scan_public_report(report)
    errors.extend(validate_parent_b1_public_aggregate())
    expected = build_report()
    errors.extend(_diff_values(expected, report))
    return sorted(set(errors))


def _balanced_partition(
    total: int,
    labels: Sequence[str],
    capacity: int,
) -> tuple[tuple[str, int], ...]:
    values = {label: total // len(labels) for label in labels}
    for label in labels[: total % len(labels)]:
        values[label] += 1
    if any(value > capacity for value in values.values()):
        raise ValueError("synthetic partition exceeds capacity")
    return tuple((label, values[label]) for label in labels)


def _synthetic_summary(adapter_id: str) -> B2ArmSummary:
    position = B2_ADAPTER_IDS.index(adapter_id)
    task_success = (30, 34, 35, 36, 45, 46)[position]
    target_success = (34, 35, 36, 38, 40, 41)[position]
    support_success = (0, 0, 0, 0, 10, 11)[position]
    one_shot_success = (30, 34, 35, 36, 35, 35)[position]
    context_average = (650_000, 670_000, 690_000, 715_000, 720_000, 725_000)[position]
    harmful = (4, 4, 3, 3, 2, 2)[position]
    subset_success_table = {
        S0_ADAPTER_ID: (6, 10, 8, 0),
        S1_ADAPTER_ID: (7, 10, 8, 0),
        S2_ADAPTER_ID: (7, 11, 8, 0),
        S3_ADAPTER_ID: (7, 11, 10, 0),
        S4_ADAPTER_ID: (7, 11, 10, 10),
        S5_ADAPTER_ID: (7, 11, 12, 11),
    }
    subset_success = subset_success_table[adapter_id]
    subset_context = tuple(
        (key, B2_SUBSET_DENOMINATORS[key] * context_average)
        for key in B2_SUBSET_DENOMINATORS
    )
    warm_us = (1_000_000, 1_100_000, 1_150_000, 1_350_000, 1_300_000, 1_550_000)[position]
    rss_mib = (100, 110, 112, 130, 125, 145)[position]
    cold_us = (5_000_000, 5_100_000, 5_200_000, 5_500_000, 5_350_000, 5_700_000)[position]
    index_mib = (80, 80, 80, 81, 80, 81)[position]
    return B2ArmSummary(
        adapter_id=adapter_id,
        record_count=B2_RECORDS_PER_ARM,
        accepted_count=B2_RECORDS_PER_ARM,
        rejected_count=0,
        resource_complete_count=B2_RECORDS_PER_ARM,
        matrix_complete=True,
        safety_gates_passed=True,
        determinism_confirmed=True,
        source_immutable=True,
        provider_network_call_count=0,
        invalid_citation_count=0,
        timeout_count=0,
        task_success_count=task_success,
        answerable_target_success_count=target_success,
        ambiguous_status_success_count=5,
        no_answer_status_success_count=5,
        support_success_count=support_success,
        one_shot_success_count=one_shot_success,
        context_f05_sum_ppm=B2_ANSWERABLE_TASK_COUNT * context_average,
        harmful_evidence_task_count=harmful,
        language_success_counts=_balanced_partition(task_success, B2_LANGUAGES, 16),
        size_success_counts=_balanced_partition(task_success, B2_SIZE_BANDS, 12),
        role_success_counts=_balanced_partition(task_success, B2_TASK_ROLES, 12),
        subset_success_counts=tuple(
            (key, value) for key, value in zip(B2_SUBSET_DENOMINATORS, subset_success)
        ),
        subset_context_f05_sum_ppm=subset_context,
        warm_query_p95_us=warm_us,
        peak_rss_p95_bytes=rss_mib * 1024 * 1024,
        cold_index_p95_us=cold_us,
        index_state_p95_bytes=index_mib * 1024 * 1024,
    )


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    slots = build_task_slots()
    schedule = build_execution_schedule(slots)
    checks.append(("task_frame_valid", not validate_task_slots(slots)))
    checks.append(("schedule_valid", not validate_execution_schedule(schedule, slots)))
    checks.append(("task_count_48", len(slots) == 48))
    checks.append(("record_count_1440", B2_TOTAL_RECORDS == 1440))
    checks.append(("index_build_count_288", B2_INDEX_BUILD_COUNT == 288))
    checks.append(("base_report_valid", not validate_report(build_report())))
    checks.append(("parent_b1_public_lock_valid", not validate_parent_b1_public_aggregate()))

    summaries = [_synthetic_summary(adapter_id) for adapter_id in B2_ADAPTER_IDS]
    checks.append(
        (
            "synthetic_summaries_valid",
            all(not validate_arm_summary(summary) for summary in summaries),
        )
    )
    decision = evaluate_tournament(summaries)
    checks.append(
        (
            "multiple_equivalent_default_finalists_allowed",
            decision["verdict"]
            == "multiple_decision_equivalent_internal_finalists_for_phase_c"
            and decision["phase_c_internal_shortlist"]
            == sorted([S4_ADAPTER_ID, S5_ADAPTER_ID]),
        )
    )
    checks.append(("s0_retained_only_as_control", decision["baseline_control"] == S0_ADAPTER_ID))
    checks.append(
        (
            "resource_rank_is_separate_and_nonempty",
            decision["resource_ranks"].get(S1_ADAPTER_ID) == 1
            and set(decision["resource_ranks"])
            == set((*B2_OPTIONAL_TRACK_ARMS, *B2_DEFAULT_TRACK_ARMS)),
        )
    )

    tie_s4 = _synthetic_summary(S4_ADAPTER_ID)
    s5_original = _synthetic_summary(S5_ADAPTER_ID)
    tie_s5 = replace(
        s5_original,
        task_success_count=tie_s4.task_success_count,
        answerable_target_success_count=tie_s4.answerable_target_success_count,
        ambiguous_status_success_count=tie_s4.ambiguous_status_success_count,
        no_answer_status_success_count=tie_s4.no_answer_status_success_count,
        support_success_count=tie_s4.support_success_count,
        context_f05_sum_ppm=tie_s4.context_f05_sum_ppm,
        harmful_evidence_task_count=tie_s4.harmful_evidence_task_count,
        language_success_counts=tie_s4.language_success_counts,
        size_success_counts=tie_s4.size_success_counts,
        role_success_counts=tie_s4.role_success_counts,
    )
    s3 = _synthetic_summary(S3_ADAPTER_ID)
    ranks = competition_ranks([tie_s4, tie_s5, s3])
    checks.append(
        (
            "exact_ties_use_competition_rank_1_1_3",
            ranks[S4_ADAPTER_ID] == 1
            and ranks[S5_ADAPTER_ID] == 1
            and ranks[S3_ADAPTER_ID] == 3,
        )
    )

    graph_broken = replace(
        _synthetic_summary(S5_ADAPTER_ID),
        subset_success_counts=(
            ("literal", 7),
            ("symbol", 11),
            ("graph", 10),
            ("support", 11),
        ),
        subset_context_f05_sum_ppm=_synthetic_summary(S4_ADAPTER_ID).subset_context_f05_sum_ppm,
    )
    broken_summaries = [
        graph_broken if summary.adapter_id == S5_ADAPTER_ID else summary
        for summary in summaries
    ]
    broken_decision = evaluate_tournament(broken_summaries)
    checks.append(
        (
            "graph_without_incremental_value_not_promoted",
            S5_ADAPTER_ID not in broken_decision["default_track_eligible"],
        )
    )

    support_child = _synthetic_summary(S4_ADAPTER_ID)
    support_counts = dict(support_child.subset_success_counts)
    support_counts["support"] = 2
    support_context = dict(support_child.subset_context_f05_sum_ppm)
    support_context["support"] = B2_SUBSET_DENOMINATORS["support"] * B2_FIXED_POINT_SCALE
    support_child = replace(
        support_child,
        subset_success_counts=tuple(
            (key, support_counts[key]) for key in B2_SUBSET_DENOMINATORS
        ),
        subset_context_f05_sum_ppm=tuple(
            (key, support_context[key]) for key in B2_SUBSET_DENOMINATORS
        ),
    )
    support_rule_summaries = {
        summary.adapter_id: summary for summary in summaries
    }
    support_rule_summaries[S4_ADAPTER_ID] = support_child
    checks.append(
        (
            "support_cannot_earn_by_context_without_support_gain",
            evaluate_component_rules(support_rule_summaries)[
                "support_earns_inclusion_over_s2"
            ]["passed"]
            is False,
        )
    )

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {
        "status": "passed",
        "checks_passed": len(checks),
        "checks_total": len(checks),
        "task_slots": len(slots),
        "schedule_rows": len(schedule),
        "records": B2_TOTAL_RECORDS,
    }


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[tuple[str, bool]] = []

    def rejected(name: str, mutator: Any) -> None:
        mutated = copy.deepcopy(base)
        mutator(mutated)
        checks.append((name, bool(validate_report(mutated))))

    rejected("schema_drift_rejected", lambda report: report.__setitem__("schema_version", "drift"))
    rejected("unknown_top_key_rejected", lambda report: report.__setitem__("extra", True))
    rejected(
        "parent_bundle_drift_rejected",
        lambda report: report["parent_b1_lock"].__setitem__("source_bundle_digest", "drift"),
    )
    rejected(
        "execution_overauthorization_rejected",
        lambda report: report["execution_boundary"].__setitem__(
            "adapter_execution_executed", True
        ),
    )
    rejected(
        "task_count_drift_rejected",
        lambda report: report["task_frame"].__setitem__("task_slot_count", 47),
    )
    rejected(
        "task_family_margin_drift_rejected",
        lambda report: report["task_frame"]["task_family_counts"].__setitem__(
            "no_answer", 5
        ),
    )
    rejected(
        "task_admission_drift_rejected",
        lambda report: report["task_frame"]["admission_rules"].__setitem__(
            "task_authored_before_any_arm_output", False
        ),
    )
    rejected(
        "schedule_digest_drift_rejected",
        lambda report: report["randomization"].__setitem__("schedule_digest", "drift"),
    )
    rejected(
        "seed_drift_rejected",
        lambda report: report["randomization"].__setitem__("seed", "different"),
    )
    rejected(
        "rotation_balance_drift_rejected",
        lambda report: report["randomization"]["arm_rotation_coefficients_mod_6"].__setitem__(
            "language", 1
        ),
    )
    rejected(
        "matrix_count_drift_rejected",
        lambda report: report["lifecycle_matrix"].__setitem__("total_records", 1439),
    )
    rejected(
        "quality_floor_drift_rejected",
        lambda report: report["promotion_contract"]["quality_floors"].__setitem__(
            "task_success_count", 35
        ),
    )
    rejected(
        "scoring_rounding_drift_rejected",
        lambda report: report["metric_contract"]["scoring_rules"].__setitem__(
            "fixed_point_conversion", "round_to_nearest"
        ),
    )
    rejected(
        "component_rule_drift_rejected",
        lambda report: report["promotion_contract"]["component_rules"][2].__setitem__(
            "minimum_success_gain", 1
        ),
    )
    rejected(
        "forced_unique_winner_rejected",
        lambda report: report["tie_policy"].__setitem__("forced_unique_winner", True),
    )
    rejected(
        "privacy_task_detail_rejected",
        lambda report: report["privacy_publication"].__setitem__(
            "task_level_results_public", True
        ),
    )
    rejected(
        "private_path_rejected",
        lambda report: report.__setitem__("note", "runs/private-b2"),
    )
    rejected(
        "protocol_digest_drift_rejected",
        lambda report: report.__setitem__("protocol_digest", "b2protocol_drift"),
    )

    bad_summary = replace(_synthetic_summary(S4_ADAPTER_ID), rejected_count=1)
    checks.append(
        (
            "arm_summary_reconciliation_fault_rejected",
            bool(validate_arm_summary(bad_summary)),
        )
    )

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("fault-test failed: " + ", ".join(failed))
    return {
        "status": "passed",
        "faults_rejected": len(checks),
        "faults_total": len(checks),
    }


def write_report(output: Path = REPORT_PATH) -> None:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise SystemExit("generated report invalid: " + "; ".join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_drift(path: Path) -> list[str]:
    try:
        observed = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail closed with exception type only
        return [f"report unreadable: {type(exc).__name__}"]
    return _diff_values(build_report(), observed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze and validate the OpenLocus B2 tournament protocol"
    )
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
        write_report(args.output)
        print(str(args.output))
        return 0
    if args.validate_report:
        try:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - fail closed with type only
            print(f"ERROR: unreadable report: {type(exc).__name__}", file=sys.stderr)
            return 1
        errors = validate_report(report)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    drift = check_drift(args.check_drift)
    if drift:
        for error in drift:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Drift check passed: {args.check_drift}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
