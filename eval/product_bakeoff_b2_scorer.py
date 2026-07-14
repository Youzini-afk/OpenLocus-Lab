#!/usr/bin/env python3
"""Scorer-only B2 task scoring, arm aggregation, and public result builder."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from product_bakeoff_contract import PackTarget, stable_target_id
from product_bakeoff_b2_corpus import B2PublicTask, load_json, write_json
from product_bakeoff_b2_oracle import (
    B2Span,
    B2TaskOracle,
    validate_oracle_manifest,
)
from product_bakeoff_b2_protocol import (
    B2_ADAPTER_IDS,
    B2_ANSWERABLE_TASK_COUNT,
    B2_FIXED_POINT_SCALE,
    B2_RECORDS_PER_ARM,
    B2_REPORT_SCHEMA_VERSION,
    B2_SUBSET_DENOMINATORS,
    B2_TASK_COUNT,
    B2_TOTAL_RECORDS,
    B2ArmSummary,
    b2_source_bundle_digest,
    b2_spec_digest,
    build_task_slots,
    evaluate_tournament,
    execution_schedule_digest,
    scan_public_report,
    task_slot_digest,
    validate_arm_summary,
)
from product_bakeoff_b2_runner import B2CellResult, B2RunResult


B2_SCORER_VERSION = "product_bakeoff_b2_scorer.v1"
B2_RESULT_SCHEMA = "product_bakeoff_b2_tournament_result.v1"
B2_RESULT_STATUS = "product_bakeoff_b2_internal_tournament_complete_aggregate_only"
B2_RESULT_CLAIM = "internal_product_decision_evidence_for_phase_c_no_public_default_claim"
PRIVATE_FREEZE_DIGEST_KEYS = frozenset(
    {
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "runtime_bundle_digest",
        "freeze_receipt_digest",
    }
)


class B2ScoreError(ValueError):
    """Fail-closed B2 scoring/publication error."""


@dataclass(frozen=True)
class TaskScore:
    target_or_status_success: bool
    support_success: bool
    task_success: bool
    context_f05_ppm: int
    harmful_evidence: bool


def _atoms(path: str, start: int, end: int) -> set[tuple[str, int]]:
    return {(path, line) for line in range(start, end + 1)}


def _span_atoms(spans: Sequence[B2Span]) -> set[tuple[str, int]]:
    atoms: set[tuple[str, int]] = set()
    for span in spans:
        atoms.update(span.atoms())
    return atoms


def f05_ppm(
    selected_atoms: set[tuple[str, int]], positive_atoms: set[tuple[str, int]]
) -> int:
    """Exact floor(F0.5 * 1e6) using 5*a/(g+4*s)."""
    if not selected_atoms or not positive_atoms:
        return 0
    overlap = len(selected_atoms & positive_atoms)
    if overlap == 0:
        return 0
    numerator = 5 * overlap * B2_FIXED_POINT_SCALE
    denominator = len(positive_atoms) + 4 * len(selected_atoms)
    return numerator // denominator


def nearest_rank_p95(values: Sequence[int]) -> int:
    if not values:
        raise B2ScoreError("p95 population is empty")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        raise B2ScoreError("p95 values must be nonnegative integers")
    ordered = sorted(values)
    rank = max(1, math.ceil(95 * len(ordered) / 100))
    return ordered[rank - 1]


def _target_atoms(cell: B2CellResult) -> set[tuple[str, int]]:
    output = cell.capture.output
    if output is None:
        raise B2ScoreError("score cell lacks accepted capture")
    atoms: set[tuple[str, int]] = set()
    for target in output.pack.targets:
        atoms.update(_atoms(target.path, target.start_line, target.end_line))
    return atoms


def _evidence_atoms(cell: B2CellResult) -> set[tuple[str, int]]:
    output = cell.capture.output
    if output is None:
        raise B2ScoreError("score cell lacks accepted capture")
    atoms: set[tuple[str, int]] = set()
    for evidence in output.evidence:
        atoms.update(_atoms(evidence.path, evidence.start_line, evidence.end_line))
    return atoms


def _context_target_success(cell: B2CellResult, oracle: B2TaskOracle) -> bool:
    output = cell.capture.output
    if output is None:
        return False
    target_atoms = _target_atoms(cell)
    positive_by_span = [set(span.atoms()) for span in oracle.positive_spans]
    negative_atoms = _span_atoms(oracle.negative_spans)
    if target_atoms & negative_atoms:
        return False
    if oracle.oracle_kind == "deterministic":
        return bool(positive_by_span and target_atoms & positive_by_span[0])
    if oracle.oracle_kind == "multi_target":
        covered = sum(bool(target_atoms & atoms) for atoms in positive_by_span)
        return output.pack.pack_status == "uncertain" and covered >= 2
    if oracle.oracle_kind == "abstain":
        return (
            output.pack.pack_status == "no_evidence"
            and not output.validated_candidates
            and not output.evidence
            and not output.pack.targets
            and not output.pack.support
        )
    raise B2ScoreError("unknown oracle kind")


def _support_success(
    context_cell: B2CellResult,
    support_cell: B2CellResult,
    oracle: B2TaskOracle,
    context_success: bool,
) -> bool:
    if not context_success or context_cell.capture.output is None or support_cell.capture.output is None:
        return False
    if len(context_cell.capture.output.pack.targets) != 1:
        return False
    expected_parent_id = support_cell.request.run_spec.bound_target_id
    if not expected_parent_id:
        return False
    support_pack = support_cell.capture.output.pack
    for selected in support_pack.support:
        selected_atoms = _atoms(selected.path, selected.start_line, selected.end_line)
        for expected in oracle.support_relations:
            if (
                selected.relation_kind == expected.relation_kind
                and selected.parent_target_id == expected_parent_id
                and selected_atoms & set(expected.support.atoms())
            ):
                return True
    return False


def score_task(
    *,
    task: B2PublicTask,
    oracle: B2TaskOracle,
    context_cell: B2CellResult,
    support_cell: B2CellResult | None,
) -> TaskScore:
    target_success = _context_target_success(context_cell, oracle)
    evidence_atoms = _evidence_atoms(context_cell)
    positive_atoms = _span_atoms(oracle.positive_spans)
    negative_atoms = _span_atoms(oracle.negative_spans)
    context_score = (
        f05_ppm(evidence_atoms, positive_atoms)
        if oracle.oracle_kind != "abstain"
        else 0
    )
    harmful = bool(evidence_atoms & negative_atoms) if oracle.oracle_kind != "abstain" else False
    if task.interaction_mode == "two_step":
        if support_cell is None:
            raise B2ScoreError("two-step task lacks support cell")
        support_success = _support_success(
            context_cell, support_cell, oracle, target_success
        )
        task_success = support_success
    else:
        support_success = False
        task_success = target_success
    return TaskScore(
        target_or_status_success=target_success,
        support_success=support_success,
        task_success=task_success,
        context_f05_ppm=context_score,
        harmful_evidence=harmful,
    )


def _canonical_cells(
    result: B2RunResult,
) -> dict[tuple[str, str, str], B2CellResult]:
    grouped: dict[tuple[str, str, str], list[B2CellResult]] = defaultdict(list)
    for cell in result.cells:
        grouped[(
            cell.record.adapter_id,
            cell.record.run_cell_id,
            cell.record.operation,
        )].append(cell)
    canonical: dict[tuple[str, str, str], B2CellResult] = {}
    for key, cells in grouped.items():
        if len(cells) != 4:
            raise B2ScoreError(f"logical score cell {key} has {len(cells)} observations")
        if len({cell.semantic_hash for cell in cells}) != 1:
            raise B2ScoreError(f"logical score cell {key} is not deterministic")
        canonical[key] = min(cells, key=lambda cell: cell.record.adapter_repetition)
    return canonical


def _micros(seconds: float | None) -> int:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        raise B2ScoreError("resource timing is missing/non-finite")
    return int(seconds * 1_000_000)


def _query_to_pack_us(cell: B2CellResult) -> int:
    resource = cell.record.resource_sample
    if resource is None:
        raise B2ScoreError("resource sample missing")
    return sum(
        _micros(value)
        for value in (
            resource.query_seconds,
            resource.materialize_seconds,
            resource.render_seconds,
        )
        if value is not None
    )


def _build_arm_summary(
    *,
    adapter_id: str,
    result: B2RunResult,
    tasks: Sequence[B2PublicTask],
    oracle_by_slug: Mapping[str, B2TaskOracle],
    canonical: Mapping[tuple[str, str, str], B2CellResult],
) -> B2ArmSummary:
    slots = {slot.slot_id: slot for slot in build_task_slots()}
    scores: dict[str, TaskScore] = {}
    for task in tasks:
        context = canonical[(adapter_id, task.task_slug, "context")]
        support = (
            canonical[(adapter_id, task.task_slug, "support")]
            if task.interaction_mode == "two_step"
            else None
        )
        scores[task.task_slug] = score_task(
            task=task,
            oracle=oracle_by_slug[task.task_slug],
            context_cell=context,
            support_cell=support,
        )

    arm_cells = [cell for cell in result.cells if cell.record.adapter_id == adapter_id]
    if len(arm_cells) != B2_RECORDS_PER_ARM:
        raise B2ScoreError("arm record count is incomplete")
    warm_query = [
        _query_to_pack_us(cell)
        for cell in arm_cells
        if cell.record.cache_state == "warm"
    ]
    rss = []
    for cell in arm_cells:
        resource = cell.record.resource_sample
        if resource is None or resource.rss_bytes is None:
            raise B2ScoreError("arm RSS sample missing")
        rss.append(resource.rss_bytes)
    cold_context = [
        cell for cell in arm_cells
        if cell.record.cache_state == "cold" and cell.record.operation == "context"
    ]
    cold_index = []
    index_state = []
    for cell in cold_context:
        resource = cell.record.resource_sample
        if resource is None:
            raise B2ScoreError("cold index resource sample missing")
        cold_index.append(_micros(resource.setup_seconds))
        if cell.parent_receipt is None:
            raise B2ScoreError("cold index receipt missing")
        index_state.append(int(cell.parent_receipt["index_state_bytes"]))
    if len(cold_context) != 48:
        raise B2ScoreError("arm cold-index population must contain 48 observations")

    task_by_slug = {task.task_slug: task for task in tasks}
    success_tasks = [slug for slug, score in scores.items() if score.task_success]
    language_counts = {
        language: sum(
            scores[task.task_slug].task_success
            for task in tasks if task.language == language
        )
        for language in ("rust", "python", "typescript")
    }
    size_counts = {
        size: sum(
            scores[task.task_slug].task_success
            for task in tasks if task.size_band == size
        )
        for size in ("small", "medium", "large", "xlarge")
    }
    role_counts = {
        role: sum(
            scores[task.task_slug].task_success
            for task in tasks if task.role == role
        )
        for role in ("direct", "relational", "workflow", "restraint")
    }
    subset_success: dict[str, int] = {}
    subset_context: dict[str, int] = {}
    for subset in B2_SUBSET_DENOMINATORS:
        eligible_tasks = [
            task for task in tasks
            if getattr(slots[task.slot_id], f"{subset}_eligible")
        ]
        if len(eligible_tasks) != B2_SUBSET_DENOMINATORS[subset]:
            raise B2ScoreError(f"subset denominator drift for {subset}")
        if subset == "support":
            subset_success[subset] = sum(
                scores[task.task_slug].support_success for task in eligible_tasks
            )
        else:
            subset_success[subset] = sum(
                scores[task.task_slug].target_or_status_success
                for task in eligible_tasks
            )
        subset_context[subset] = sum(
            scores[task.task_slug].context_f05_ppm for task in eligible_tasks
        )

    arm_records = [cell.record for cell in arm_cells]
    summary = B2ArmSummary(
        adapter_id=adapter_id,
        record_count=len(arm_records),
        accepted_count=sum(record.status == "accepted" for record in arm_records),
        rejected_count=sum(record.status == "rejected" for record in arm_records),
        resource_complete_count=sum(
            record.resource_sample is not None
            and record.resource_sample.cpu_seconds is not None
            and record.resource_sample.rss_bytes is not None
            for record in arm_records
        ),
        matrix_complete=len(arm_records) == B2_RECORDS_PER_ARM,
        safety_gates_passed=bool(result.gate_result and result.gate_result.passed),
        determinism_confirmed=True,
        source_immutable=not result.parent_receipt_failures,
        provider_network_call_count=sum(
            int(cell.parent_receipt["provider_network_call_count"])
            for cell in arm_cells if cell.parent_receipt is not None
        ),
        invalid_citation_count=0,
        timeout_count=sum(record.result_status == "timeout" for record in arm_records),
        task_success_count=len(success_tasks),
        answerable_target_success_count=sum(
            score.target_or_status_success
            for slug, score in scores.items()
            if oracle_by_slug[slug].oracle_kind != "abstain"
        ),
        ambiguous_status_success_count=sum(
            score.target_or_status_success
            for slug, score in scores.items()
            if oracle_by_slug[slug].oracle_kind == "multi_target"
        ),
        no_answer_status_success_count=sum(
            score.target_or_status_success
            for slug, score in scores.items()
            if oracle_by_slug[slug].oracle_kind == "abstain"
        ),
        support_success_count=sum(score.support_success for score in scores.values()),
        one_shot_success_count=sum(
            score.task_success
            for slug, score in scores.items()
            if task_by_slug[slug].interaction_mode == "one_shot"
        ),
        context_f05_sum_ppm=sum(
            score.context_f05_ppm
            for slug, score in scores.items()
            if oracle_by_slug[slug].oracle_kind != "abstain"
        ),
        harmful_evidence_task_count=sum(score.harmful_evidence for score in scores.values()),
        language_success_counts=tuple(sorted(language_counts.items())),
        size_success_counts=tuple(sorted(size_counts.items())),
        role_success_counts=tuple(sorted(role_counts.items())),
        subset_success_counts=tuple(sorted(subset_success.items())),
        subset_context_f05_sum_ppm=tuple(sorted(subset_context.items())),
        warm_query_p95_us=nearest_rank_p95(warm_query),
        peak_rss_p95_bytes=nearest_rank_p95(rss),
        cold_index_p95_us=nearest_rank_p95(cold_index),
        index_state_p95_bytes=nearest_rank_p95(index_state),
    )
    errors = validate_arm_summary(summary)
    if errors:
        raise B2ScoreError(f"arm summary invalid for {adapter_id}: {errors}")
    return summary


def _summary_dict(summary: B2ArmSummary) -> dict[str, Any]:
    return {
        "adapter_id": summary.adapter_id,
        "record_count": summary.record_count,
        "accepted_count": summary.accepted_count,
        "rejected_count": summary.rejected_count,
        "resource_complete_count": summary.resource_complete_count,
        "matrix_complete": summary.matrix_complete,
        "safety_gates_passed": summary.safety_gates_passed,
        "determinism_confirmed": summary.determinism_confirmed,
        "source_immutable": summary.source_immutable,
        "provider_network_call_count": summary.provider_network_call_count,
        "invalid_citation_count": summary.invalid_citation_count,
        "timeout_count": summary.timeout_count,
        "task_success_count": summary.task_success_count,
        "answerable_target_success_count": summary.answerable_target_success_count,
        "ambiguous_status_success_count": summary.ambiguous_status_success_count,
        "no_answer_status_success_count": summary.no_answer_status_success_count,
        "support_success_count": summary.support_success_count,
        "one_shot_success_count": summary.one_shot_success_count,
        "context_f05_sum_ppm": summary.context_f05_sum_ppm,
        "harmful_evidence_task_count": summary.harmful_evidence_task_count,
        "language_success_counts": dict(summary.language_success_counts),
        "size_success_counts": dict(summary.size_success_counts),
        "role_success_counts": dict(summary.role_success_counts),
        "subset_success_counts": dict(summary.subset_success_counts),
        "subset_context_f05_sum_ppm": dict(summary.subset_context_f05_sum_ppm),
        "warm_query_p95_us": summary.warm_query_p95_us,
        "peak_rss_p95_bytes": summary.peak_rss_p95_bytes,
        "cold_index_p95_us": summary.cold_index_p95_us,
        "index_state_p95_bytes": summary.index_state_p95_bytes,
    }


def _private_tokens(result: B2RunResult) -> list[str]:
    tokens: list[str] = []
    if result.repo_lock:
        for repo in result.repo_lock["repos"]:
            tokens.extend((repo["source"]["repo"], repo["source"]["clone_root"]))
    for task in result.tasks:
        tokens.extend((task.task_slug, task.query))
    return [token for token in tokens if token]


def scan_result_report(report: Any, *, private_tokens: Sequence[str] = ()) -> list[str]:
    errors = list(scan_public_report(report))

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            forbidden = PRIVATE_FREEZE_DIGEST_KEYS & set(value)
            if forbidden:
                errors.append("private freeze digest key forbidden in public B2 result")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(report)
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False)
    lowered = raw.casefold()
    if "github.com/" in lowered or "git@github.com" in lowered:
        errors.append("repository URL forbidden in public B2 result")
    for token in private_tokens:
        if len(token) >= 4 and token.casefold() in lowered:
            errors.append("private repository/task token leaked into public B2 result")
            break
    return sorted(set(errors))


def build_public_result(
    *,
    result: B2RunResult,
    summaries: Sequence[B2ArmSummary],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    if result.repo_lock is None or result.task_manifest is None or result.freeze_receipt is None:
        raise B2ScoreError("run result lacks frozen manifest bindings")
    report: dict[str, Any] = {
        "schema_version": B2_RESULT_SCHEMA,
        "phase": "product_bakeoff_b2_internal_product_decision_tournament",
        "status": B2_RESULT_STATUS,
        "claim_level": B2_RESULT_CLAIM,
        "aggregate_only": True,
        "product_default_changed": False,
        "public_winner_declared": False,
        "phase_c_validation_required": True,
        "protocol": {
            "protocol_schema_version": B2_REPORT_SCHEMA_VERSION,
            "spec_digest": b2_spec_digest(),
            "source_bundle_digest": b2_source_bundle_digest(),
            "task_slot_digest": task_slot_digest(),
            "execution_schedule_digest": execution_schedule_digest(),
        },
        "freeze_verification": {
            "repository_task_oracle_and_runtime_frozen": True,
            "freeze_receipt_validated_before_execution": True,
            "private_freeze_digests_public": False,
        },
        "matrix": {
            "logical_task_count": B2_TASK_COUNT,
            "validated_record_count": len(result.records),
            "expected_record_count": B2_TOTAL_RECORDS,
            "accepted_count": sum(record.status == "accepted" for record in result.records),
            "rejected_count": sum(record.status == "rejected" for record in result.records),
            "all_pre_score_gates_passed": bool(result.gate_result and result.gate_result.passed),
            "provider_network_call_count": result.provider_network_call_count,
        },
        "resource_percentile_rule": "nearest_rank_ceiling_p95_over_frozen_populations",
        "arms": [_summary_dict(summary) for summary in sorted(summaries, key=lambda row: row.adapter_id)],
        "tournament_decision": dict(decision),
        "publication_limits": {
            "repo_level_results_public": False,
            "task_level_results_public": False,
            "task_text_public": False,
            "oracle_rows_public": False,
            "per_cell_resources_public": False,
            "private_freeze_digests_public": False,
        },
    }
    report["result_digest"] = "b2result_" + hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    errors = scan_result_report(report, private_tokens=_private_tokens(result))
    if errors:
        raise B2ScoreError("public B2 result privacy scan failed: " + "; ".join(errors))
    return report


def score_b2(
    *, result: B2RunResult, oracle_manifest_path: Path
) -> tuple[tuple[B2ArmSummary, ...], dict[str, Any], dict[str, Any]]:
    if result.gate_result is None or not result.gate_result.passed:
        raise B2ScoreError("B2 scorer cannot run before all pre-score gates pass")
    if len(result.records) != B2_TOTAL_RECORDS or not result.repo_lock or not result.task_manifest:
        raise B2ScoreError("B2 scorer received an incomplete run")
    oracle_manifest = load_json(oracle_manifest_path)
    oracles = validate_oracle_manifest(
        oracle_manifest,
        tasks=result.tasks,
        repo_lock=result.repo_lock,
        task_manifest_digest=result.task_manifest["task_manifest_digest"],
    )
    if result.freeze_receipt is None or (
        oracle_manifest["oracle_manifest_digest"]
        != result.freeze_receipt["oracle_manifest_digest"]
    ):
        raise B2ScoreError("oracle manifest differs from pre-run freeze receipt")
    oracle_by_slug = {oracle.task_slug: oracle for oracle in oracles}
    canonical = _canonical_cells(result)
    summaries = tuple(
        _build_arm_summary(
            adapter_id=adapter_id,
            result=result,
            tasks=result.tasks,
            oracle_by_slug=oracle_by_slug,
            canonical=canonical,
        )
        for adapter_id in B2_ADAPTER_IDS
    )
    decision = evaluate_tournament(summaries)
    public = build_public_result(result=result, summaries=summaries, decision=decision)
    return summaries, decision, public


def write_public_result(path: Path, report: Mapping[str, Any]) -> None:
    errors = scan_result_report(report)
    if errors:
        raise B2ScoreError("refusing to write unsafe public report: " + "; ".join(errors))
    write_json(path, report)


def run_self_test() -> dict[str, Any]:
    checks = [
        ("perfect_f05", f05_ppm({("a", 1)}, {("a", 1)}) == B2_FIXED_POINT_SCALE),
        ("partial_f05", f05_ppm({("a", 1), ("a", 2)}, {("a", 1)}) == 5 * B2_FIXED_POINT_SCALE // 9),
        ("nearest_rank", nearest_rank_p95(list(range(1, 21))) == 19),
        ("competition_privacy_scan", not scan_result_report({"quality_ranks": {"s0": 1, "s1": 1, "s2": 3}})),
        ("public_protocol_digest_allowed", not scan_result_report({"source_bundle_digest": "b2src_public"})),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks = [
        ("repo_url_rejected", bool(scan_result_report({"value": "https://github.com/a/b"}))),
        ("private_task_token_rejected", bool(scan_result_report({"value": "opaque-secret-query"}, private_tokens=["opaque-secret-query"]))),
        ("private_freeze_digest_rejected", bool(scan_result_report({"repo_lock_digest": "private"}))),
    ]
    try:
        nearest_rank_p95([])
        empty_rejected = False
    except B2ScoreError:
        empty_rejected = True
    checks.append(("empty_percentile_rejected", empty_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B2ScoreError", "TaskScore", "f05_ppm", "nearest_rank_p95",
    "score_task", "score_b2", "build_public_result", "scan_result_report",
    "write_public_result", "run_self_test", "run_fault_test",
]
