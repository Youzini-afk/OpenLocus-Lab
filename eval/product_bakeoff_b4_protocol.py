#!/usr/bin/env python3
"""Preregister the B4 multi-panel independent replication protocol.

B4 treats the published B3 result as planning evidence only.  It does not
reopen, rescore, rerank, or count B3 as a confirmatory replication.  The design
reduces the six-arm screen to S0/S1/S4, replaces one fixed holdout with twelve
mutually disjoint panels, counts repositories rather than technical repeats as
the independent replication units, and always publishes relative effects,
uncertainty, ranks, and a Pareto frontier before deployment gates are applied.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import random
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from statistics import NormalDist
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2  # noqa: E402
import product_bakeoff_b3_design_audit as b3audit  # noqa: E402
import product_bakeoff_b3_publication as b3pub  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b4_protocol"
    / "product_bakeoff_b4_protocol_report.json"
)
B3_RESULT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_result"
    / "product_bakeoff_b3_result.json"
)
B3_AUDIT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_design_audit"
    / "product_bakeoff_b3_design_audit.json"
)

B4_SCHEMA_VERSION = "product_bakeoff_b4_protocol.v1"
B4_REPORT_SCHEMA_VERSION = "product_bakeoff_b4_protocol_report.v1"
B4_STATUS = (
    "product_bakeoff_b4_independent_replication_protocol_frozen_"
    "no_runtime_no_holdout_no_execution"
)
B4_CLAIM_LEVEL = "future_preregistered_multi_panel_replication_design_only"
B4_DATE = "2026-07-18"

B3_RESULT_FILE_SHA256 = (
    "a4cb5414b5486e166aae783ce508e55e24e92e181fa73ac232185254be5d8e25"
)
B3_RESULT_DIGEST = (
    "b3result_25ef345fa4b312ab9292ffe47fdb4ee26d0009d7ca3e46c867fcf245f8f82a00"
)
B3_AUDIT_FILE_SHA256 = (
    "d02943889ea1f39404cd054d97ab44cb55d569d2593c0f9bbec90bbad6ca6658"
)
B3_AUDIT_DIGEST = (
    "b3audit_94ab485305c1a3eea7e91250f8cb4c336e0309a390ff83e16b6eefaf8fe7e4e9"
)

B4_ARMS = (b2.S0_ADAPTER_ID, b2.S1_ADAPTER_ID, b2.S4_ADAPTER_ID)
B4_BASELINE_ARM = b2.S0_ADAPTER_ID
B4_CANDIDATE_ARMS = (b2.S1_ADAPTER_ID, b2.S4_ADAPTER_ID)
B4_PANEL_COUNT = 12
B4_REPOSITORIES_PER_PANEL = 12
B4_TASKS_PER_REPOSITORY = 4
B4_TASKS_PER_PANEL = B4_REPOSITORIES_PER_PANEL * B4_TASKS_PER_REPOSITORY
B4_REPOSITORY_CLUSTER_COUNT = B4_PANEL_COUNT * B4_REPOSITORIES_PER_PANEL
B4_LOGICAL_TASK_COUNT = B4_PANEL_COUNT * B4_TASKS_PER_PANEL
B4_REPOSITORY_ARM_LIFECYCLE_BLOCKS = 1
B4_COLD_TASKS_PER_REPOSITORY = 1
B4_WARM_TASKS_PER_REPOSITORY = (
    B4_TASKS_PER_REPOSITORY - B4_COLD_TASKS_PER_REPOSITORY
)
B4_GROUPS_PER_ARM_PANEL = 60
B4_LOGICAL_GROUP_COUNT = (
    B4_PANEL_COUNT * len(B4_ARMS) * B4_GROUPS_PER_ARM_PANEL
)
B4_LOGICAL_RECORD_COUNT = B4_LOGICAL_GROUP_COUNT
B4_INDEX_BUILD_COUNT = B4_REPOSITORY_CLUSTER_COUNT * len(B4_ARMS)

B4_RANDOMIZATION_SEED = (
    "openlocus-b4-20260718-three-arm-twelve-panel-single-lifecycle-v1"
)
B4_ARM_SEQUENCES = tuple(itertools.permutations(B4_ARMS))
B4_COLD_SEQUENCE_BASE_BY_ROLE = (
    (0, 1, 2),
    (3, 4, 5),
    (0, 2, 4),
    (1, 3, 5),
)

SOURCE_BUNDLE_PATHS = (
    "eval/product_bakeoff_b2_protocol.py",
    "eval/product_bakeoff_b3_publication.py",
    "eval/product_bakeoff_b3_design_audit.py",
    "eval/product_bakeoff_b4_protocol.py",
    "artifacts/product_bakeoff_b3_result/product_bakeoff_b3_result.json",
    "artifacts/product_bakeoff_b3_design_audit/product_bakeoff_b3_design_audit.json",
    ".github/workflows/product-bakeoff-b4-protocol.yml",
)

POWER_SIMULATIONS_PER_SCENARIO = 2_000
POWER_DISCORDANT_PROBABILITY_PPM = 500_000
POWER_EFFECT_PPM = (0, 60_000, 80_000, 100_000, 120_000, 140_000, 160_000)
POWER_REPOSITORY_ICC_PPM = (50_000, 150_000, 250_000)
POWER_PANEL_EFFECT_SD_PPM = (0, 40_000, 80_000)
POWER_PER_COMPARISON_ALPHA_PPM = 25_000
POWER_SIMULTANEOUS_CI_LEVEL_PPM = 975_000
POWER_FIXED_DESIGN_T_CRITICAL_PPM = 2_265_247
POWER_TARGET_EFFECT_PPM = 120_000
POWER_MINIMUM_MATERIAL_EFFECT_PPM = 60_000
POWER_MINIMUM_POSITIVE_PANELS = 8
POWER_SAMPLE_SIZE_PANEL_COUNTS = (8, 12, 16, 18)


class B4ProtocolError(ValueError):
    """Fail-closed B4 public protocol error."""


@dataclass(frozen=True)
class B4ScheduleRow:
    panel_index: int
    repository_index: int
    task_index: int
    task_role: str
    cache_state: str
    sequence_index: int
    arm_order: tuple[str, str, str]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _prefixed_digest(prefix: str, value: Mapping[str, Any], key: str) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def source_bundle_digest() -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_BUNDLE_PATHS:
        path = REPO / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return "b4bundle_" + digest.hexdigest()


def _validate_parent_locks() -> tuple[dict[str, Any], dict[str, Any]]:
    if _file_sha256(B3_RESULT_PATH) != B3_RESULT_FILE_SHA256:
        raise B4ProtocolError("B3 result file lock drifted")
    result = json.loads(B3_RESULT_PATH.read_text(encoding="utf-8"))
    if b3pub.validate_public_result(result):
        raise B4ProtocolError("B3 result validation failed")
    if result.get("result_digest") != B3_RESULT_DIGEST:
        raise B4ProtocolError("B3 result digest drifted")
    if _file_sha256(B3_AUDIT_PATH) != B3_AUDIT_FILE_SHA256:
        raise B4ProtocolError("B3 audit file lock drifted")
    audit = json.loads(B3_AUDIT_PATH.read_text(encoding="utf-8"))
    if b3audit.validate_report(audit):
        raise B4ProtocolError("B3 audit validation failed")
    if audit.get("audit_digest") != B3_AUDIT_DIGEST:
        raise B4ProtocolError("B3 audit digest drifted")
    return result, audit


def _task_metadata(panel_index: int, task_index: int) -> tuple[int, str, str]:
    repository_index = (task_index - 1) // B4_TASKS_PER_REPOSITORY + 1
    role_index = (task_index - 1) % B4_TASKS_PER_REPOSITORY
    task_role = b2.B2_TASK_ROLES[role_index]
    cold_role_index = (panel_index + repository_index - 2) % len(b2.B2_TASK_ROLES)
    cache_state = "cold" if role_index == cold_role_index else "warm"
    return repository_index, task_role, cache_state


def _task_order(panel_index: int, task_role: str, cache_state: str) -> list[int]:
    return sorted(
        (
            task_index
            for task_index in range(1, B4_TASKS_PER_PANEL + 1)
            if _task_metadata(panel_index, task_index)[1:] == (
                task_role,
                cache_state,
            )
        ),
        key=lambda task_index: hashlib.sha256(
            (
                f"{B4_RANDOMIZATION_SEED}|panel={panel_index}|"
                f"role={task_role}|cache={cache_state}|task={task_index}"
            ).encode()
        ).digest(),
    )


def _sequence_assignment(panel_index: int) -> dict[int, int]:
    assignment: dict[int, int] = {}
    sequence_count = len(B4_ARM_SEQUENCES)
    offset = hashlib.sha256(
        f"{B4_RANDOMIZATION_SEED}|panel={panel_index}|sequence-offset".encode()
    ).digest()[0] % sequence_count
    for role_index, task_role in enumerate(b2.B2_TASK_ROLES):
        cold_sequences = [
            (sequence_index + offset) % sequence_count
            for sequence_index in B4_COLD_SEQUENCE_BASE_BY_ROLE[role_index]
        ]
        cold_tasks = _task_order(panel_index, task_role, "cold")
        cold_sequences.sort(
            key=lambda sequence_index: hashlib.sha256(
                (
                    f"{B4_RANDOMIZATION_SEED}|panel={panel_index}|"
                    f"role={task_role}|cold-sequence={sequence_index}"
                ).encode()
            ).digest()
        )
        assignment.update(zip(cold_tasks, cold_sequences))

        remaining = Counter({sequence_index: 2 for sequence_index in range(sequence_count)})
        remaining.subtract(cold_sequences)
        warm_tokens = [
            (sequence_index, occurrence)
            for sequence_index in range(sequence_count)
            for occurrence in range(remaining[sequence_index])
        ]
        warm_tokens.sort(
            key=lambda token: hashlib.sha256(
                (
                    f"{B4_RANDOMIZATION_SEED}|panel={panel_index}|"
                    f"role={task_role}|warm-sequence={token[0]}|copy={token[1]}"
                ).encode()
            ).digest()
        )
        warm_tasks = _task_order(panel_index, task_role, "warm")
        assignment.update(
            (task_index, token[0])
            for task_index, token in zip(warm_tasks, warm_tokens)
        )
    return assignment


def build_schedule() -> list[B4ScheduleRow]:
    rows: list[B4ScheduleRow] = []
    for panel_index in range(1, B4_PANEL_COUNT + 1):
        sequence_by_task = _sequence_assignment(panel_index)
        for task_index in range(1, B4_TASKS_PER_PANEL + 1):
            repository_index, task_role, cache_state = _task_metadata(
                panel_index, task_index
            )
            sequence_index = sequence_by_task[task_index]
            rows.append(
                B4ScheduleRow(
                    panel_index=panel_index,
                    repository_index=repository_index,
                    task_index=task_index,
                    task_role=task_role,
                    cache_state=cache_state,
                    sequence_index=sequence_index,
                    arm_order=B4_ARM_SEQUENCES[sequence_index],
                )
            )
    return rows


def validate_schedule(rows: Sequence[B4ScheduleRow]) -> list[str]:
    errors: list[str] = []
    expected_rows = B4_PANEL_COUNT * B4_TASKS_PER_PANEL
    if len(rows) != expected_rows:
        errors.append("B4 schedule row count drifted")
    if len(set(rows)) != len(rows):
        errors.append("B4 schedule contains duplicate rows")
    keys = [(row.panel_index, row.task_index) for row in rows]
    if len(set(keys)) != len(keys):
        errors.append("B4 schedule contains duplicate panel/task keys")
    for panel_index in range(1, B4_PANEL_COUNT + 1):
        panel_rows = [row for row in rows if row.panel_index == panel_index]
        for repository_index in range(1, B4_REPOSITORIES_PER_PANEL + 1):
            repository_rows = [
                row
                for row in panel_rows
                if row.repository_index == repository_index
            ]
            if Counter(row.cache_state for row in repository_rows) != Counter(
                {"cold": B4_COLD_TASKS_PER_REPOSITORY, "warm": B4_WARM_TASKS_PER_REPOSITORY}
            ):
                errors.append(
                    f"B4 panel {panel_index} repository {repository_index} cache imbalance"
                )
        for task_role in b2.B2_TASK_ROLES:
            role_rows = [row for row in panel_rows if row.task_role == task_role]
            if Counter(row.cache_state for row in role_rows) != Counter(
                {"cold": 3, "warm": 9}
            ):
                errors.append(
                    f"B4 panel {panel_index} role {task_role} cache imbalance"
                )
            role_sequence_counts = Counter(row.sequence_index for row in role_rows)
            if set(role_sequence_counts) != set(range(len(B4_ARM_SEQUENCES))) or set(
                role_sequence_counts.values()
            ) != {2}:
                errors.append(
                    f"B4 panel {panel_index} role {task_role} sequence imbalance"
                )
        for cache_state, expected_sequence_count in (("cold", 2), ("warm", 6)):
            subset = [row for row in panel_rows if row.cache_state == cache_state]
            sequence_counts = Counter(row.sequence_index for row in subset)
            if set(sequence_counts) != set(range(len(B4_ARM_SEQUENCES))) or set(
                sequence_counts.values()
            ) != {expected_sequence_count}:
                errors.append(
                    f"B4 panel {panel_index} cache {cache_state} sequence imbalance"
                )
            for position in range(len(B4_ARMS)):
                counts = Counter(row.arm_order[position] for row in subset)
                if set(counts) != set(B4_ARMS) or len(set(counts.values())) != 1:
                    errors.append(
                        f"B4 panel {panel_index} cache {cache_state} position imbalance"
                    )
            predecessors = Counter(
                (row.arm_order[index], row.arm_order[index + 1])
                for row in subset
                for index in range(len(B4_ARMS) - 1)
            )
            expected_pairs = {
                (left, right) for left in B4_ARMS for right in B4_ARMS if left != right
            }
            if set(predecessors) != expected_pairs or len(
                set(predecessors.values())
            ) != 1:
                errors.append(
                    f"B4 panel {panel_index} cache {cache_state} predecessor imbalance"
                )
    return sorted(set(errors))


def schedule_digest() -> str:
    return "b4schedule_" + hashlib.sha256(
        _canonical([asdict(row) for row in build_schedule()])
    ).hexdigest()


def _scenario_seed(
    effect_ppm: int, icc_ppm: int, panel_effect_sd_ppm: int, panel_count: int
) -> int:
    payload = (
        f"{B4_RANDOMIZATION_SEED}|power|effect={effect_ppm}|icc={icc_ppm}|"
        f"panel_sd={panel_effect_sd_ppm}|panels={panel_count}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _wilson_interval_ppm(successes: int, total: int) -> tuple[int, int]:
    z = NormalDist().inv_cdf(0.975)
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    half = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4 * total * total)
        )
        / denominator
    )
    return (
        max(0, int(math.floor((center - half) * 1_000_000))),
        min(1_000_000, int(math.ceil((center + half) * 1_000_000))),
    )


def _student_t_critical(df: int) -> float:
    if df <= 0:
        raise B4ProtocolError("Student t degrees of freedom must be positive")
    z = NormalDist().inv_cdf(1.0 - POWER_PER_COMPARISON_ALPHA_PPM / 2_000_000)
    first = (z**3 + z) / (4.0 * df)
    second = (5.0 * z**5 + 16.0 * z**3 + 3.0 * z) / (96.0 * df**2)
    return z + first + second


def _positive_panel_threshold(panel_count: int) -> int:
    return math.ceil(panel_count * 2 / 3)


@lru_cache(maxsize=None)
def _simulate_power_scenario(
    effect_ppm: int,
    icc_ppm: int,
    panel_effect_sd_ppm: int,
    panel_count: int = B4_PANEL_COUNT,
) -> dict[str, Any]:
    effect = effect_ppm / 1_000_000
    icc = icc_ppm / 1_000_000
    panel_effect_sd = panel_effect_sd_ppm / 1_000_000
    discordance = POWER_DISCORDANT_PROBABILITY_PPM / 1_000_000
    rng = random.Random(
        _scenario_seed(effect_ppm, icc_ppm, panel_effect_sd_ppm, panel_count)
    )
    critical = _student_t_critical(
        panel_count * B4_REPOSITORIES_PER_PANEL - 1
    )
    aggregate_rejections = 0
    joint_quality_gate_passes = 0
    positive_panel_threshold = _positive_panel_threshold(panel_count)
    if panel_effect_sd and panel_count % 2:
        raise B4ProtocolError("panel heterogeneity sensitivity requires even panels")
    for _ in range(POWER_SIMULATIONS_PER_SCENARIO):
        cluster_means: list[float] = []
        panel_means: list[float] = []
        panel_shifts = (
            [panel_effect_sd] * (panel_count // 2)
            + [-panel_effect_sd] * (panel_count // 2)
            if panel_effect_sd
            else [0.0] * panel_count
        )
        rng.shuffle(panel_shifts)
        for panel_shift in panel_shifts:
            panel_effect = max(
                -discordance,
                min(discordance, effect + panel_shift),
            )
            requested_cluster_shift = math.sqrt(
                max(0.0, icc * (discordance - panel_effect * panel_effect))
            )
            cluster_shift = min(
                requested_cluster_shift,
                discordance - abs(panel_effect),
            )
            panel_clusters: list[float] = []
            for _cluster in range(B4_REPOSITORIES_PER_PANEL):
                signed_shift = (
                    cluster_shift if rng.random() < 0.5 else -cluster_shift
                )
                cluster_effect = panel_effect + signed_shift
                plus = (discordance + cluster_effect) / 2.0
                minus = (discordance - cluster_effect) / 2.0
                if plus < 0.0 or minus < 0.0 or plus + minus > 1.0:
                    raise B4ProtocolError("B4 power scenario probability is invalid")
                total = 0
                for _task in range(B4_TASKS_PER_REPOSITORY):
                    draw = rng.random()
                    if draw < plus:
                        total += 1
                    elif draw < plus + minus:
                        total -= 1
                cluster_mean = total / B4_TASKS_PER_REPOSITORY
                cluster_means.append(cluster_mean)
                panel_clusters.append(cluster_mean)
            panel_means.append(sum(panel_clusters) / len(panel_clusters))
        mean = sum(cluster_means) / len(cluster_means)
        variance = sum((value - mean) ** 2 for value in cluster_means) / (
            len(cluster_means) - 1
        )
        standard_error = math.sqrt(variance / len(cluster_means)) if variance else 0.0
        statistic = mean / standard_error if standard_error else 0.0
        aggregate_rejection = mean > 0.0 and statistic > critical
        if aggregate_rejection:
            aggregate_rejections += 1
        positive_panels = sum(panel_mean > 0.0 for panel_mean in panel_means)
        if (
            aggregate_rejection
            and mean >= POWER_MINIMUM_MATERIAL_EFFECT_PPM / 1_000_000
            and positive_panels >= positive_panel_threshold
        ):
            joint_quality_gate_passes += 1
    aggregate_low, aggregate_high = _wilson_interval_ppm(
        aggregate_rejections, POWER_SIMULATIONS_PER_SCENARIO
    )
    joint_low, joint_high = _wilson_interval_ppm(
        joint_quality_gate_passes, POWER_SIMULATIONS_PER_SCENARIO
    )
    return {
        "effect_ppm": effect_ppm,
        "repository_icc_ppm": icc_ppm,
        "panel_effect_sd_ppm": panel_effect_sd_ppm,
        "panel_count": panel_count,
        "repository_cluster_count": panel_count * B4_REPOSITORIES_PER_PANEL,
        "minimum_material_effect_ppm": POWER_MINIMUM_MATERIAL_EFFECT_PPM,
        "minimum_positive_panels": positive_panel_threshold,
        "aggregate_rejections": aggregate_rejections,
        "joint_quality_gate_passes": joint_quality_gate_passes,
        "simulations": POWER_SIMULATIONS_PER_SCENARIO,
        "estimated_aggregate_power_ppm": (
            aggregate_rejections * 1_000_000 // POWER_SIMULATIONS_PER_SCENARIO
        ),
        "aggregate_monte_carlo_95ci_ppm": [aggregate_low, aggregate_high],
        "estimated_joint_quality_gate_power_ppm": (
            joint_quality_gate_passes * 1_000_000
            // POWER_SIMULATIONS_PER_SCENARIO
        ),
        "joint_quality_gate_monte_carlo_95ci_ppm": [joint_low, joint_high],
    }


@lru_cache(maxsize=1)
def power_sensitivity() -> tuple[dict[str, Any], ...]:
    return tuple(
        dict(_simulate_power_scenario(effect_ppm, icc_ppm, panel_sd_ppm))
        for panel_sd_ppm in POWER_PANEL_EFFECT_SD_PPM
        for icc_ppm in POWER_REPOSITORY_ICC_PPM
        for effect_ppm in POWER_EFFECT_PPM
    )


@lru_cache(maxsize=1)
def sample_size_sensitivity() -> tuple[dict[str, Any], ...]:
    fixed_target_rows = [
        _simulate_power_scenario(
            POWER_TARGET_EFFECT_PPM,
            icc_ppm,
            panel_sd_ppm,
            B4_PANEL_COUNT,
        )
        for panel_sd_ppm in POWER_PANEL_EFFECT_SD_PPM
        for icc_ppm in POWER_REPOSITORY_ICC_PPM
    ]
    adverse = min(
        fixed_target_rows,
        key=lambda row: (
            row["estimated_joint_quality_gate_power_ppm"],
            -row["repository_icc_ppm"],
            -row["panel_effect_sd_ppm"],
        ),
    )
    return tuple(
        dict(
            _simulate_power_scenario(
                POWER_TARGET_EFFECT_PPM,
                adverse["repository_icc_ppm"],
                adverse["panel_effect_sd_ppm"],
                panel_count,
            )
        )
        for panel_count in POWER_SAMPLE_SIZE_PANEL_COUNTS
    )


def _sign_replication_tail_probability_ppm() -> int:
    numerator = sum(
        math.comb(B4_PANEL_COUNT, successes)
        for successes in range(POWER_MINIMUM_POSITIVE_PANELS, B4_PANEL_COUNT + 1)
    )
    return numerator * 1_000_000 // (2**B4_PANEL_COUNT)


B4_EXPERIMENTAL_DESIGN = {
    "design_type": "fixed_complete_within_task_three_arm_multi_panel_replication",
    "arm_ids": list(B4_ARMS),
    "baseline_arm": B4_BASELINE_ARM,
    "candidate_arms": list(B4_CANDIDATE_ARMS),
    "independent_panel_count": B4_PANEL_COUNT,
    "repositories_per_panel": B4_REPOSITORIES_PER_PANEL,
    "tasks_per_repository": B4_TASKS_PER_REPOSITORY,
    "languages_per_panel": list(b2.B2_LANGUAGES),
    "size_bands_per_panel": list(b2.B2_SIZE_BANDS),
    "task_roles_per_repository": list(b2.B2_TASK_ROLES),
    "each_panel_has_exact_language_by_size_repository_grid": True,
    "repository_cluster_count": B4_REPOSITORY_CLUSTER_COUNT,
    "logical_task_count": B4_LOGICAL_TASK_COUNT,
    "repository_arm_lifecycle_blocks": B4_REPOSITORY_ARM_LIFECYCLE_BLOCKS,
    "technical_repetition_count": 0,
    "formal_observations_per_task_arm_operation": 1,
    "index_build_count": B4_INDEX_BUILD_COUNT,
    "logical_group_count": B4_LOGICAL_GROUP_COUNT,
    "logical_record_count": B4_LOGICAL_RECORD_COUNT,
    "all_panels_repositories_tasks_queries_and_oracles_frozen_before_treatment": True,
    "all_panels_mutually_disjoint": True,
    "all_b2_through_b3_repository_frames_excluded": True,
    "b3_tasks_queries_oracles_and_treatment_output_reused": False,
    "b3_public_aggregate_used_for_planning_only": True,
    "repository_is_independent_replication_cluster": True,
    "tasks_are_nested_within_repository": True,
    "same_task_technical_pseudoreplication_eliminated": True,
    "single_repository_arm_lifecycle_has_one_cold_and_three_warm_tasks": True,
    "cold_task_role_balance_exact_within_every_panel": True,
    "same_task_receives_all_three_arms": True,
    "six_three_arm_sequences_balance_position_and_first_order_predecessor": True,
    "sequence_balance_exact_within_each_panel_and_cache_state": True,
    "sequence_balance_exact_within_each_panel_and_task_role": True,
    "authoring_acceptance_is_arm_agnostic_and_pre_treatment": True,
    "fixed_design_no_interim_quality_looks": True,
    "fixed_design_no_adaptive_panel_addition_or_arm_elimination": True,
}

B4_ANALYSIS_RULES = {
    "confirmatory_primary_relative_effect": "paired_task_success_difference",
    "key_secondary_relative_effects": [
        "paired_task_utility_net_win_rate",
        "paired_status_or_target_success_difference",
        "paired_context_f05_difference",
    ],
    "secondary_effects_are_estimation_and_ranking_not_extra_confirmatory_tests": True,
    "task_utility_order": [
        "task_success",
        "harmful_evidence_absence",
        "status_or_target_success",
        "context_f05",
    ],
    "task_utility_is_lexicographic_not_opaque_weighted_composite": True,
    "task_quality_is_scored_once_per_arm_without_repeat_vote_or_best_of_selection": True,
    "repository_cluster_level_uncertainty": True,
    "primary_effect_ci_method": "paired_repository_cluster_mean_t_interval",
    "inference_target": "mean_effect_over_the_twelve_frozen_panels",
    "no_universal_population_effect_claim": True,
    "two_candidate_comparisons_familywise_controlled": True,
    "multiplicity_method": "bonferroni_two_planned_candidate_vs_baseline_comparisons",
    "per_comparison_two_sided_alpha_ppm": POWER_PER_COMPARISON_ALPHA_PPM,
    "estimation_ci_level_ppm": 950_000,
    "confirmatory_simultaneous_ci_level_ppm": POWER_SIMULTANEOUS_CI_LEVEL_PPM,
    "paired_effect_point_estimates_and_both_ci_levels_always_published": True,
    "panel_direction_counts_always_published": True,
    "minimum_positive_panels_for_replication_gate": POWER_MINIMUM_POSITIVE_PANELS,
    "positive_panel_sign_tail_probability_ppm": _sign_replication_tail_probability_ppm(),
    "panel_direction_guard_is_heterogeneity_check_not_standalone_significance_test": True,
    "zero_panel_effect_is_not_counted_positive": True,
    "quality_competition_rank_key": [
        "task_success_rate_desc",
        "harmful_evidence_rate_asc",
        "status_or_target_success_rate_desc",
        "context_f05_mean_desc",
    ],
    "resource_competition_rank_key": [
        "warm_query_geometric_mean_us_asc",
        "peak_rss_p95_bytes_asc",
    ],
    "resource_ratio_ci_method": (
        "paired_repository_cluster_log_ratio_t_interval"
    ),
    "pareto_dimensions": [
        "task_success_rate_max",
        "harmful_evidence_rate_min",
        "warm_query_geometric_mean_us_min",
        "peak_rss_p95_bytes_min",
    ],
    "all_arms_ranked_before_deployment_gates": True,
    "baseline_ranked_symmetrically_with_candidates": True,
    "quality_and_resource_competition_ranks_always_published": True,
    "exact_ties_share_competition_rank": True,
    "pareto_frontier_always_published": True,
    "no_absolute_b2_quality_floor_veto": True,
    "no_empty_ranking_when_deployment_gates_fail": True,
    "no_forced_unique_winner": True,
}

B4_DEPLOYMENT_GATES = {
    b2.S1_ADAPTER_ID: {
        "track": "default_candidate",
        "minimum_task_success_effect_ppm": POWER_MINIMUM_MATERIAL_EFFECT_PPM,
        "aggregate_lower_simultaneous_97_5ci_must_exceed_zero": True,
        "minimum_positive_panels": POWER_MINIMUM_POSITIVE_PANELS,
        "warm_query_ratio_upper_95ci_ppm": 1_200_000,
        "peak_rss_ratio_upper_95ci_ppm": 1_150_000,
        "harmful_evidence_risk_difference_upper_simultaneous_97_5ci_ppm": 20_000,
    },
    b2.S4_ADAPTER_ID: {
        "track": "optional_high_recall_candidate",
        "minimum_task_success_effect_ppm": POWER_MINIMUM_MATERIAL_EFFECT_PPM,
        "aggregate_lower_simultaneous_97_5ci_must_exceed_zero": True,
        "minimum_positive_panels": POWER_MINIMUM_POSITIVE_PANELS,
        "warm_query_ratio_upper_95ci_ppm": 2_100_000,
        "peak_rss_ratio_upper_95ci_ppm": 1_250_000,
        "harmful_evidence_risk_difference_upper_simultaneous_97_5ci_ppm": 20_000,
    },
    "resource_bounds_are_operational_gates_not_superiority_claims": True,
    "deployment_gate_failure_does_not_delete_rank_or_effect_estimate": True,
    "promotion_requires_fresh_phase_c_validation": True,
}

B4_POWER_DESIGN = {
    "method": (
        "deterministic_monte_carlo_joint_quality_gate_cluster_panel_sensitivity"
    ),
    "simulation_model": (
        "paired_trinary_win_loss_tie_with_panel_and_repository_direction_shifts"
    ),
    "power_endpoint": "paired_task_success_difference",
    "paired_discordant_probability_sensitivity_ppm": (
        POWER_DISCORDANT_PROBABILITY_PPM
    ),
    "repository_icc_scenarios_ppm": list(POWER_REPOSITORY_ICC_PPM),
    "repository_icc_shift_is_symmetrically_feasibility_capped": True,
    "between_panel_effect_sd_scenarios_ppm": list(POWER_PANEL_EFFECT_SD_PPM),
    "panel_heterogeneity_is_mean_centered_with_balanced_positive_negative_shifts": True,
    "effect_scenarios_ppm": list(POWER_EFFECT_PPM),
    "simulations_per_scenario": POWER_SIMULATIONS_PER_SCENARIO,
    "per_comparison_alpha_ppm": POWER_PER_COMPARISON_ALPHA_PPM,
    "simultaneous_ci_level_ppm": POWER_SIMULTANEOUS_CI_LEVEL_PPM,
    "fixed_design_student_t_critical_ppm": POWER_FIXED_DESIGN_T_CRITICAL_PPM,
    "student_t_critical_method": "second_order_cornish_fisher_by_repository_df",
    "minimum_material_effect_ppm": POWER_MINIMUM_MATERIAL_EFFECT_PPM,
    "minimum_positive_panels": POWER_MINIMUM_POSITIVE_PANELS,
    "target_effect_ppm": POWER_TARGET_EFFECT_PPM,
    "joint_quality_power_includes_significance_materiality_and_panel_direction_guards": True,
    "resource_and_harm_gates_not_power_modeled_without_defensible_distributions": True,
    "sample_size_panel_sensitivity": list(POWER_SAMPLE_SIZE_PANEL_COUNTS),
    "twelve_panels_selected_as_cost_bounded_estimation_and_replication_design": True,
    "worst_case_eighteen_panel_option_not_selected_because_it_adds_50_percent_records": True,
    "sensitivity_not_guarantee": True,
    "raw_b3_pilot_effect_not_used_as_assumed_true_effect": True,
    "smaller_effects_are_estimated_but_not_claimed_well_powered": True,
    "gate_miss_never_erases_effect_estimates_ranks_or_pareto_result": True,
}

B4_RESOURCE_POLICY = {
    "authoring_mode": "serial_candidate_clone_materialize_freeze_cleanup",
    "formal_execution_mode": "bounded_streaming_repository_lanes",
    "failed_or_rejected_candidate_clone_deleted_before_replacement": True,
    "frozen_repository_source_stored_as_content_bound_compact_snapshot": True,
    "git_history_dependency_caches_and_build_outputs_not_persisted": True,
    "maximum_expanded_repositories_per_lane": 1,
    "parallel_lane_count_frozen_after_local_and_linux_qualification": True,
    "same_parallel_lane_count_and_affinity_for_every_arm": True,
    "no_adaptive_parallelism_after_treatment_begins": True,
    "scratch_admission_uses_measured_snapshot_and_runner_working_set": True,
    "no_arbitrary_fixed_free_disk_floor": True,
    "durable_results_append_before_scratch_cleanup": True,
    "gpu_required": False,
}

B4_PUBLICATION_POLICY = {
    "aggregate_only": True,
    "publish_panel_count_not_panel_repository_identity": True,
    "publish_effects_confidence_intervals_ranks_and_pareto_frontier": True,
    "publish_deployment_gate_outcomes_after_ranking": True,
    "publish_no_private_repository_task_query_oracle_identity": True,
    "publish_no_intermediate_panel_metrics_before_terminal_closeout": True,
    "no_result_shopping_or_post_output_rule_change": True,
    "failure_closeout_still_publishes_only_safe_aggregate_counts": True,
}

B4_IMPLEMENTATION_READINESS = {
    "protocol_frozen": True,
    "runner_implemented": False,
    "scorer_implemented": False,
    "runtime_qualified": False,
    "private_holdout_authored": False,
    "private_holdout_frozen": False,
    "public_readiness_published": False,
    "formal_execution_authorized": False,
    "treatment_output_exists": False,
}


def build_report() -> dict[str, Any]:
    result, audit = _validate_parent_locks()
    schedule = build_schedule()
    schedule_errors = validate_schedule(schedule)
    if schedule_errors:
        raise B4ProtocolError("B4 schedule invalid: " + "; ".join(schedule_errors))
    sensitivity = [dict(row) for row in power_sensitivity()]
    size_sensitivity = [dict(row) for row in sample_size_sensitivity()]
    target_rows = [
        row for row in sensitivity if row["effect_ppm"] == POWER_TARGET_EFFECT_PPM
    ]
    moderate_target_rows = [
        row
        for row in target_rows
        if row["repository_icc_ppm"] <= 150_000
        and row["panel_effect_sd_ppm"] <= 40_000
    ]
    selected_size_row = next(
        row for row in size_sensitivity if row["panel_count"] == B4_PANEL_COUNT
    )
    eighteen_panel_row = next(
        row for row in size_sensitivity if row["panel_count"] == 18
    )
    report: dict[str, Any] = {
        "schema_version": B4_REPORT_SCHEMA_VERSION,
        "protocol_schema_version": B4_SCHEMA_VERSION,
        "phase": "product_bakeoff_b4_multi_panel_independent_replication_protocol",
        "status": B4_STATUS,
        "claim_level": B4_CLAIM_LEVEL,
        "date": B4_DATE,
        "parent_locks": {
            "b3_result_schema": result["schema_version"],
            "b3_result_status": result["status"],
            "b3_result_digest": result["result_digest"],
            "b3_result_file_sha256": B3_RESULT_FILE_SHA256,
            "b3_design_audit_schema": audit["schema_version"],
            "b3_design_audit_status": audit["status"],
            "b3_design_audit_digest": audit["audit_digest"],
            "b3_design_audit_file_sha256": B3_AUDIT_FILE_SHA256,
            "b3_result_remains_frozen": True,
        },
        "experimental_design": copy.deepcopy(B4_EXPERIMENTAL_DESIGN),
        "randomization": {
            "seed": B4_RANDOMIZATION_SEED,
            "sequence_count": len(B4_ARM_SEQUENCES),
            "schedule_rows": len(schedule),
            "schedule_digest": schedule_digest(),
            "position_balance_exact_per_panel_and_cache_state": True,
            "first_order_predecessor_balance_exact_per_panel_and_cache_state": True,
            "sequence_balance_exact_per_panel_and_task_role": True,
            "one_cold_three_warm_tasks_per_repository": True,
            "cold_role_balance_exact_per_panel": True,
            "panel_task_order_seeded_before_treatment": True,
        },
        "analysis_rules": copy.deepcopy(B4_ANALYSIS_RULES),
        "deployment_gates": copy.deepcopy(B4_DEPLOYMENT_GATES),
        "power_design": copy.deepcopy(B4_POWER_DESIGN),
        "resource_policy": copy.deepcopy(B4_RESOURCE_POLICY),
        "power_sensitivity": sensitivity,
        "sample_size_sensitivity": size_sensitivity,
        "power_target_summary": {
            "effect_ppm": POWER_TARGET_EFFECT_PPM,
            "minimum_estimated_aggregate_power_ppm_across_nuisance_scenarios": min(
                row["estimated_aggregate_power_ppm"] for row in target_rows
            ),
            "maximum_estimated_aggregate_power_ppm_across_nuisance_scenarios": max(
                row["estimated_aggregate_power_ppm"] for row in target_rows
            ),
            "minimum_estimated_joint_quality_gate_power_ppm_across_nuisance_scenarios": min(
                row["estimated_joint_quality_gate_power_ppm"] for row in target_rows
            ),
            "maximum_estimated_joint_quality_gate_power_ppm_across_nuisance_scenarios": max(
                row["estimated_joint_quality_gate_power_ppm"] for row in target_rows
            ),
            "minimum_moderate_nuisance_joint_quality_gate_power_ppm": min(
                row["estimated_joint_quality_gate_power_ppm"]
                for row in moderate_target_rows
            ),
            "joint_quality_gate_scenarios_at_or_above_800000": sum(
                row["estimated_joint_quality_gate_power_ppm"] >= 800_000
                for row in target_rows
            ),
            "joint_quality_gate_scenario_count": len(target_rows),
            "no_universal_80_percent_power_claim": True,
            "interpretation": (
                "large_effect_confirmation_is_well_supported_in_moderate_"
                "nuisance_scenarios_but_worst_case_joint_power_is_reported_"
                "rather_than_hidden"
            ),
        },
        "sample_size_decision": {
            "selected_panel_count": B4_PANEL_COUNT,
            "selected_repository_cluster_count": B4_REPOSITORY_CLUSTER_COUNT,
            "selected_logical_record_count": B4_LOGICAL_RECORD_COUNT,
            "adverse_sensitivity_repository_icc_ppm": selected_size_row[
                "repository_icc_ppm"
            ],
            "adverse_sensitivity_panel_effect_sd_ppm": selected_size_row[
                "panel_effect_sd_ppm"
            ],
            "selected_worst_case_target_joint_quality_power_ppm": selected_size_row[
                "estimated_joint_quality_gate_power_ppm"
            ],
            "eighteen_panel_repository_cluster_count": 18
            * B4_REPOSITORIES_PER_PANEL,
            "eighteen_panel_logical_record_count": 18
            * len(B4_ARMS)
            * B4_GROUPS_PER_ARM_PANEL,
            "eighteen_panel_worst_case_target_joint_quality_power_ppm": eighteen_panel_row[
                "estimated_joint_quality_gate_power_ppm"
            ],
            "eighteen_panel_record_ratio_ppm": 1_500_000,
            "selection_reason": (
                "twelve_panels_preserve_independent_replication_and_always_"
                "publish_estimates_while_avoiding_a_50_percent_compute_increase_"
                "solely_to_cover_the_most_adverse_unidentified_nuisance_case"
            ),
        },
        "publication_policy": copy.deepcopy(B4_PUBLICATION_POLICY),
        "implementation_readiness": copy.deepcopy(B4_IMPLEMENTATION_READINESS),
        "source_bundle_digest": source_bundle_digest(),
        "next_authorized_action": (
            "implement_and_fault_test_b4_runner_scorer_publication_and_control_"
            "without_creating_private_holdout_or_treatment_output"
        ),
        "protocol_digest": "",
    }
    report["protocol_digest"] = _prefixed_digest(
        "b4protocol_", report, "protocol_digest"
    )
    return report


def _diff(expected: Any, actual: Any, path: str = "report") -> list[str]:
    if type(expected) is not type(actual):
        return [f"{path}: type drift"]
    if isinstance(expected, dict):
        errors: list[str] = []
        if set(expected) != set(actual):
            errors.append(f"{path}: key drift")
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
        return ["B4 protocol report must be an object"]
    errors = list(b2.scan_public_report(report))
    try:
        expected = build_report()
    except (B4ProtocolError, OSError, ValueError) as exc:
        errors.append(f"cannot rebuild B4 protocol report: {type(exc).__name__}")
        return sorted(set(errors))
    errors.extend(_diff(expected, report))
    if report.get("protocol_digest") != _prefixed_digest(
        "b4protocol_", report, "protocol_digest"
    ):
        errors.append("B4 protocol digest mismatch")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    schedule = build_schedule()
    report = build_report()
    zero_rows = [row for row in report["power_sensitivity"] if row["effect_ppm"] == 0]
    checks = [
        not validate_schedule(schedule),
        len(schedule) == B4_PANEL_COUNT * B4_TASKS_PER_PANEL,
        len(B4_ARM_SEQUENCES) == 6,
        report["experimental_design"]["independent_panel_count"] == 12,
        report["experimental_design"]["repository_cluster_count"] == 144,
        report["experimental_design"]["logical_task_count"] == 576,
        report["experimental_design"]["logical_record_count"] == 2160,
        report["experimental_design"]["index_build_count"] == 432,
        report["experimental_design"]["technical_repetition_count"] == 0,
        report["analysis_rules"]["minimum_positive_panels_for_replication_gate"]
        == 8,
        report["analysis_rules"]["positive_panel_sign_tail_probability_ppm"]
        == 193_847,
        report["analysis_rules"]["confirmatory_simultaneous_ci_level_ppm"]
        == 975_000,
        round(
            _student_t_critical(B4_REPOSITORY_CLUSTER_COUNT - 1) * 1_000_000
        )
        == POWER_FIXED_DESIGN_T_CRITICAL_PPM,
        report["analysis_rules"]["no_empty_ranking_when_deployment_gates_fail"],
        report["analysis_rules"]["baseline_ranked_symmetrically_with_candidates"],
        report["power_target_summary"]["no_universal_80_percent_power_claim"],
        report["resource_policy"]["no_arbitrary_fixed_free_disk_floor"],
        report["resource_policy"]["maximum_expanded_repositories_per_lane"] == 1,
        report["sample_size_decision"]["eighteen_panel_record_ratio_ppm"]
        == 1_500_000,
        report["sample_size_decision"][
            "selected_worst_case_target_joint_quality_power_ppm"
        ]
        == report["power_target_summary"][
            "minimum_estimated_joint_quality_gate_power_ppm_across_nuisance_scenarios"
        ],
        report["sample_size_decision"][
            "eighteen_panel_worst_case_target_joint_quality_power_ppm"
        ]
        > report["sample_size_decision"][
            "selected_worst_case_target_joint_quality_power_ppm"
        ],
        report["implementation_readiness"]["formal_execution_authorized"] is False,
        all(row["estimated_aggregate_power_ppm"] <= 35_000 for row in zero_rows),
        all(
            row["estimated_joint_quality_gate_power_ppm"] <= 25_000
            for row in zero_rows
        ),
        not validate_report(report),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "schedule_rows": len(schedule),
        "power_scenarios": len(report["power_sensitivity"]),
        "sample_size_scenarios": len(report["sample_size_sensitivity"]),
    }


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[bool] = []

    def reject(mutator: Any) -> None:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append(bool(validate_report(value)))

    reject(
        lambda value: value["experimental_design"].__setitem__(
            "same_task_technical_pseudoreplication_eliminated", False
        )
    )
    reject(
        lambda value: value["experimental_design"].__setitem__(
            "b3_tasks_queries_oracles_and_treatment_output_reused", True
        )
    )
    reject(
        lambda value: value["analysis_rules"].__setitem__(
            "all_arms_ranked_before_deployment_gates", False
        )
    )
    reject(
        lambda value: value["analysis_rules"].__setitem__(
            "no_empty_ranking_when_deployment_gates_fail", False
        )
    )
    reject(
        lambda value: value["analysis_rules"].__setitem__(
            "confirmatory_simultaneous_ci_level_ppm", 950_000
        )
    )
    reject(
        lambda value: value["deployment_gates"][b2.S1_ADAPTER_ID].__setitem__(
            "minimum_task_success_effect_ppm", POWER_TARGET_EFFECT_PPM
        )
    )
    reject(
        lambda value: value["resource_policy"].__setitem__(
            "no_arbitrary_fixed_free_disk_floor", False
        )
    )
    reject(
        lambda value: value["implementation_readiness"].__setitem__(
            "formal_execution_authorized", True
        )
    )
    reject(
        lambda value: value.__setitem__("protocol_digest", "b4protocol_" + "0" * 64)
    )
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise B4ProtocolError("refusing to write invalid B4 protocol report")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B4 independent replication protocol")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--write-report", action="store_true")
    mode.add_argument("--validate-report", type=Path)
    mode.add_argument("--check-drift", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, sort_keys=True))
        return 0 if report["passed"] else 1
    if args.fault_test:
        report = run_fault_test()
        print(json.dumps(report, sort_keys=True))
        return 0 if report["passed"] else 1
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
    "B4_SCHEMA_VERSION",
    "B4_REPORT_SCHEMA_VERSION",
    "B4_EXPERIMENTAL_DESIGN",
    "B4_ANALYSIS_RULES",
    "B4_DEPLOYMENT_GATES",
    "B4_POWER_DESIGN",
    "B4_RESOURCE_POLICY",
    "B4_PUBLICATION_POLICY",
    "B4_IMPLEMENTATION_READINESS",
    "B4ScheduleRow",
    "build_schedule",
    "validate_schedule",
    "schedule_digest",
    "power_sensitivity",
    "sample_size_sensitivity",
    "build_report",
    "validate_report",
    "run_self_test",
    "run_fault_test",
]
