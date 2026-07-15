#!/usr/bin/env python3
"""B2.1 scorer and aggregate-only publication boundary."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
import product_bakeoff_b2_scorer as b2s
from product_bakeoff_b2_oracle import B2TaskOracle, validate_oracle_manifest
from product_bakeoff_b21_protocol import (
    B21_REPORT_SCHEMA_VERSION,
    b21_execution_schedule_digest,
    b21_source_bundle_digest,
    b21_spec_digest,
    b21_task_frame_digest,
)
from product_bakeoff_b21_runner import (
    B21RunResult,
    B21TerminalSupportCell,
)


B21_SCORER_VERSION = "product_bakeoff_b21_scorer.v1"
B21_RESULT_SCHEMA = "product_bakeoff_b21_tournament_result.v1"
B21_RESULT_STATUS = "product_bakeoff_b21_internal_tournament_complete_aggregate_only"
B21_RESULT_CLAIM = "internal_product_decision_evidence_for_phase_c_no_public_default_claim"


class B21ScoreError(ValueError):
    """Fail-closed B2.1 scoring/publication error."""


@dataclass(frozen=True)
class B21ArmResult:
    summary: b2p.B2ArmSummary
    terminal_support_count: int
    executed_adapter_record_count: int


def _canonical_normal_cells(
    result: B21RunResult,
) -> dict[tuple[str, str, str], Any]:
    grouped: dict[tuple[str, str, str], list[Any]] = {}
    for cell in result.cells:
        key = (
            cell.record.adapter_id,
            cell.record.run_cell_id,
            cell.record.operation,
        )
        grouped.setdefault(key, []).append(cell)
    canonical: dict[tuple[str, str, str], Any] = {}
    for key, cells in grouped.items():
        if len(cells) != len(b2p.B2_REPETITIONS):
            # A support operation may be represented entirely by terminal cells.
            if key[2] == "support":
                continue
            raise B21ScoreError(f"logical normal cell {key} has {len(cells)} observations")
        if len({cell.semantic_hash for cell in cells}) != 1:
            raise B21ScoreError(f"logical normal cell {key} is not deterministic")
        canonical[key] = min(cells, key=lambda cell: cell.record.adapter_repetition)
    return canonical


def _canonical_terminals(
    result: B21RunResult,
) -> dict[tuple[str, str], B21TerminalSupportCell]:
    grouped: dict[tuple[str, str], list[B21TerminalSupportCell]] = {}
    for cell in result.terminal_support_cells:
        grouped.setdefault((cell.adapter_id, cell.run_cell_id), []).append(cell)
    canonical: dict[tuple[str, str], B21TerminalSupportCell] = {}
    for key, cells in grouped.items():
        if len(cells) != len(b2p.B2_REPETITIONS):
            raise B21ScoreError(f"logical terminal support {key} has {len(cells)} observations")
        if len({cell.semantic_hash for cell in cells}) != 1:
            raise B21ScoreError(f"logical terminal support {key} is not deterministic")
        canonical[key] = min(cells, key=lambda cell: cell.adapter_repetition)
    return canonical


def _terminal_task_score(
    context_cell: Any,
    oracle: B2TaskOracle,
) -> b2s.TaskScore:
    target_success = b2s._context_target_success(context_cell, oracle)
    evidence_atoms = b2s._evidence_atoms(context_cell)
    positive_atoms = b2s._span_atoms(oracle.positive_spans)
    negative_atoms = b2s._span_atoms(oracle.negative_spans)
    context_score = (
        b2s.f05_ppm(evidence_atoms, positive_atoms)
        if oracle.oracle_kind != "abstain"
        else 0
    )
    harmful = bool(evidence_atoms & negative_atoms) if oracle.oracle_kind != "abstain" else False
    return b2s.TaskScore(
        target_or_status_success=target_success,
        support_success=False,
        task_success=False,
        context_f05_ppm=context_score,
        harmful_evidence=harmful,
    )


def _micros(seconds: float | None) -> int:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        raise B21ScoreError("resource timing is missing/non-finite")
    return int(seconds * 1_000_000)


def _query_to_pack_us(cell: Any) -> int:
    resource = cell.record.resource_sample
    if resource is None:
        raise B21ScoreError("normal resource sample missing")
    return sum(
        _micros(value)
        for value in (
            resource.query_seconds,
            resource.materialize_seconds,
            resource.render_seconds,
        )
        if value is not None
    )


def _build_arm_result(
    *,
    adapter_id: str,
    result: B21RunResult,
    tasks: Sequence[b2c.B2PublicTask],
    oracle_by_slug: Mapping[str, B2TaskOracle],
    normal: Mapping[tuple[str, str, str], Any],
    terminals: Mapping[tuple[str, str], B21TerminalSupportCell],
) -> B21ArmResult:
    slots = {slot.slot_id: slot for slot in b2p.build_task_slots()}
    scores: dict[str, b2s.TaskScore] = {}
    for task in tasks:
        context = normal[(adapter_id, task.task_slug, "context")]
        if task.interaction_mode == "one_shot":
            scores[task.task_slug] = b2s.score_task(
                task=task,
                oracle=oracle_by_slug[task.task_slug],
                context_cell=context,
                support_cell=None,
            )
            continue
        terminal = terminals.get((adapter_id, task.task_slug))
        support = normal.get((adapter_id, task.task_slug, "support"))
        if (terminal is None) == (support is None):
            raise B21ScoreError("two-step task must have exactly one support outcome kind")
        if terminal is not None:
            scores[task.task_slug] = _terminal_task_score(
                context,
                oracle_by_slug[task.task_slug],
            )
        else:
            scores[task.task_slug] = b2s.score_task(
                task=task,
                oracle=oracle_by_slug[task.task_slug],
                context_cell=context,
                support_cell=support,
            )

    normal_cells = [cell for cell in result.cells if cell.record.adapter_id == adapter_id]
    terminal_cells = [cell for cell in result.terminal_support_cells if cell.adapter_id == adapter_id]
    logical_count = len(normal_cells) + len(terminal_cells)
    if logical_count != b2p.B2_RECORDS_PER_ARM:
        raise B21ScoreError("arm logical record count is incomplete")
    warm_query = [
        _query_to_pack_us(cell)
        for cell in normal_cells
        if cell.record.cache_state == "warm"
    ]
    if not warm_query:
        raise B21ScoreError("arm executed warm-query population is empty")
    rss: list[int] = []
    for cell in normal_cells:
        resource = cell.record.resource_sample
        if resource is None or resource.rss_bytes is None:
            raise B21ScoreError("normal arm RSS sample missing")
        rss.append(resource.rss_bytes)
    if len(rss) != len(normal_cells):
        raise B21ScoreError("executed arm RSS population is incomplete")
    cold_context = [
        cell
        for cell in normal_cells
        if cell.record.cache_state == "cold" and cell.record.operation == "context"
    ]
    if len(cold_context) != 48:
        raise B21ScoreError("arm cold-index population must contain 48 observations")
    cold_index: list[int] = []
    index_state: list[int] = []
    for cell in cold_context:
        resource = cell.record.resource_sample
        if resource is None:
            raise B21ScoreError("cold context resource missing")
        cold_index.append(_micros(resource.setup_seconds))
        if cell.parent_receipt is None:
            raise B21ScoreError("cold context parent receipt missing")
        index_state.append(int(cell.parent_receipt["index_state_bytes"]))

    language_counts = {
        language: sum(
            scores[task.task_slug].task_success
            for task in tasks
            if task.language == language
        )
        for language in b2p.B2_LANGUAGES
    }
    size_counts = {
        size: sum(
            scores[task.task_slug].task_success
            for task in tasks
            if task.size_band == size
        )
        for size in b2p.B2_SIZE_BANDS
    }
    role_counts = {
        role: sum(
            scores[task.task_slug].task_success
            for task in tasks
            if task.role == role
        )
        for role in b2p.B2_TASK_ROLES
    }
    subset_success: dict[str, int] = {}
    subset_context: dict[str, int] = {}
    for subset in b2p.B2_SUBSET_DENOMINATORS:
        eligible = [
            task
            for task in tasks
            if getattr(slots[task.slot_id], f"{subset}_eligible")
        ]
        if len(eligible) != b2p.B2_SUBSET_DENOMINATORS[subset]:
            raise B21ScoreError(f"subset denominator drift for {subset}")
        if subset == "support":
            subset_success[subset] = sum(
                scores[task.task_slug].support_success for task in eligible
            )
        else:
            subset_success[subset] = sum(
                scores[task.task_slug].target_or_status_success for task in eligible
            )
        subset_context[subset] = sum(
            scores[task.task_slug].context_f05_ppm for task in eligible
        )

    normal_records = [cell.record for cell in normal_cells]
    normal_resource_complete = sum(
        record.resource_sample is not None
        and record.resource_sample.cpu_seconds is not None
        and record.resource_sample.rss_bytes is not None
        for record in normal_records
    )
    terminal_resource_complete = sum(
        cell.resource_sample.cpu_seconds is not None
        and cell.resource_sample.rss_bytes is not None
        for cell in terminal_cells
    )
    task_by_slug = {task.task_slug: task for task in tasks}
    summary = b2p.B2ArmSummary(
        adapter_id=adapter_id,
        record_count=logical_count,
        accepted_count=sum(record.status == "accepted" for record in normal_records)
        + len(terminal_cells),
        rejected_count=sum(record.status == "rejected" for record in normal_records),
        resource_complete_count=normal_resource_complete + terminal_resource_complete,
        matrix_complete=logical_count == b2p.B2_RECORDS_PER_ARM,
        safety_gates_passed=bool(result.gate_result and result.gate_result.passed),
        determinism_confirmed=True,
        source_immutable=not result.parent_receipt_failures,
        provider_network_call_count=sum(
            int(cell.parent_receipt["provider_network_call_count"])
            for cell in normal_cells
            if cell.parent_receipt is not None
        ),
        invalid_citation_count=0,
        timeout_count=sum(record.result_status == "timeout" for record in normal_records),
        task_success_count=sum(score.task_success for score in scores.values()),
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
        warm_query_p95_us=b2s.nearest_rank_p95(warm_query),
        peak_rss_p95_bytes=b2s.nearest_rank_p95(rss),
        cold_index_p95_us=b2s.nearest_rank_p95(cold_index),
        index_state_p95_bytes=b2s.nearest_rank_p95(index_state),
    )
    errors = b2p.validate_arm_summary(summary)
    if errors:
        raise B21ScoreError(f"arm summary invalid for {adapter_id}: {errors}")
    return B21ArmResult(
        summary=summary,
        terminal_support_count=len(terminal_cells),
        executed_adapter_record_count=len(normal_cells),
    )


def _arm_public(result: B21ArmResult) -> dict[str, Any]:
    payload = b2s._summary_dict(result.summary)
    payload["terminal_support_count"] = result.terminal_support_count
    payload["executed_adapter_record_count"] = result.executed_adapter_record_count
    return payload


def scan_result_report(report: Any, *, private_tokens: Sequence[str] = ()) -> list[str]:
    errors = list(b2s.scan_result_report(report, private_tokens=private_tokens))
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False)
    if "b21_private_" in raw.casefold():
        errors.append("private B2.1 identifier forbidden in public result")
    return sorted(set(errors))


def build_public_result(
    *,
    result: B21RunResult,
    arm_results: Sequence[B21ArmResult],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    if result.repo_lock is None or result.task_manifest is None or result.freeze_receipt is None:
        raise B21ScoreError("run result lacks frozen holdout bindings")
    report: dict[str, Any] = {
        "schema_version": B21_RESULT_SCHEMA,
        "phase": "product_bakeoff_b21_own_parent_holdout_tournament",
        "status": B21_RESULT_STATUS,
        "claim_level": B21_RESULT_CLAIM,
        "aggregate_only": True,
        "product_default_changed": False,
        "public_winner_declared": False,
        "phase_c_validation_required": True,
        "protocol": {
            "protocol_schema_version": B21_REPORT_SCHEMA_VERSION,
            "spec_digest": b21_spec_digest(),
            "source_bundle_digest": b21_source_bundle_digest(),
            "holdout_frame_digest": b21_task_frame_digest(),
            "execution_schedule_digest": b21_execution_schedule_digest(),
        },
        "freeze_verification": {
            "fresh_holdout_repository_task_oracle_and_runtime_frozen": True,
            "freeze_receipt_validated_before_execution": True,
            "private_freeze_digests_public": False,
        },
        "matrix": {
            "logical_task_count": b2p.B2_TASK_COUNT,
            "logical_record_count": result.logical_record_count,
            "expected_logical_record_count": b2p.B2_TOTAL_RECORDS,
            "executed_adapter_record_count": len(result.records),
            "terminal_support_record_count": len(result.terminal_support_cells),
            "all_pre_score_gates_passed": bool(result.gate_result and result.gate_result.passed),
            "provider_network_call_count": result.provider_network_call_count,
        },
        "resource_percentile_rule": (
            "nearest_rank_ceiling_p95;_terminal_support_excluded_from_query_latency_and_peak_rss"
        ),
        "arms": [
            _arm_public(row)
            for row in sorted(arm_results, key=lambda item: item.summary.adapter_id)
        ],
        "tournament_decision": dict(decision),
        "publication_limits": {
            "repo_level_results_public": False,
            "task_level_results_public": False,
            "task_text_public": False,
            "oracle_rows_public": False,
            "per_cell_resources_public": False,
            "private_freeze_digests_public": False,
            "per_task_parent_divergence_public": False,
        },
    }
    report["result_digest"] = "b21result_" + hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    errors = scan_result_report(report, private_tokens=b2s._private_tokens(result))
    if errors:
        raise B21ScoreError("public B2.1 result privacy scan failed: " + "; ".join(errors))
    return report


def validate_public_result(report: Any) -> list[str]:
    errors = scan_result_report(report)
    if not isinstance(report, dict):
        return sorted(set([*errors, "public result must be an object"]))
    expected_keys = {
        "schema_version",
        "phase",
        "status",
        "claim_level",
        "aggregate_only",
        "product_default_changed",
        "public_winner_declared",
        "phase_c_validation_required",
        "protocol",
        "freeze_verification",
        "matrix",
        "resource_percentile_rule",
        "arms",
        "tournament_decision",
        "publication_limits",
        "result_digest",
    }
    if set(report) != expected_keys:
        errors.append("public result top-level shape drift")
    if report.get("schema_version") != B21_RESULT_SCHEMA:
        errors.append("public result schema mismatch")
    if report.get("status") != B21_RESULT_STATUS:
        errors.append("public result status mismatch")
    if report.get("aggregate_only") is not True:
        errors.append("public result must be aggregate-only")
    protocol = report.get("protocol", {})
    expected_protocol = {
        "protocol_schema_version": B21_REPORT_SCHEMA_VERSION,
        "spec_digest": b21_spec_digest(),
        "source_bundle_digest": b21_source_bundle_digest(),
        "holdout_frame_digest": b21_task_frame_digest(),
        "execution_schedule_digest": b21_execution_schedule_digest(),
    }
    if protocol != expected_protocol:
        errors.append("public result protocol binding mismatch")
    matrix = report.get("matrix", {})
    logical = matrix.get("logical_record_count")
    normal = matrix.get("executed_adapter_record_count")
    terminal = matrix.get("terminal_support_record_count")
    if logical != b2p.B2_TOTAL_RECORDS:
        errors.append("public result logical matrix count mismatch")
    if not isinstance(normal, int) or not isinstance(terminal, int):
        errors.append("public result execution counts malformed")
    elif normal + terminal != b2p.B2_TOTAL_RECORDS or not 0 <= terminal <= 288:
        errors.append("public result normal/terminal counts do not reconcile")
    if matrix.get("all_pre_score_gates_passed") is not True:
        errors.append("public result pre-score gates did not pass")
    if matrix.get("provider_network_call_count") != 0:
        errors.append("public result provider/network count nonzero")
    arms = report.get("arms")
    if not isinstance(arms, list) or len(arms) != len(b2p.B2_ADAPTER_IDS):
        errors.append("public result must contain six arm aggregates")
    else:
        adapter_ids = [row.get("adapter_id") for row in arms if isinstance(row, dict)]
        if sorted(adapter_ids) != sorted(b2p.B2_ADAPTER_IDS):
            errors.append("public result arm identities drifted")
        arm_terminal_total = 0
        arm_executed_total = 0
        for row in arms:
            if not isinstance(row, dict):
                errors.append("public result arm row malformed")
                break
            arm_terminal = row.get("terminal_support_count")
            arm_executed = row.get("executed_adapter_record_count")
            if (
                not isinstance(arm_terminal, int)
                or not isinstance(arm_executed, int)
                or arm_terminal + arm_executed != b2p.B2_RECORDS_PER_ARM
                or not 0 <= arm_terminal <= 48
            ):
                errors.append("public result arm execution counts do not reconcile")
                break
            arm_terminal_total += arm_terminal
            arm_executed_total += arm_executed
        if isinstance(terminal, int) and arm_terminal_total != terminal:
            errors.append("public result terminal count differs from arm aggregates")
        if isinstance(normal, int) and arm_executed_total != normal:
            errors.append("public result executed count differs from arm aggregates")
    payload = dict(report)
    observed = payload.pop("result_digest", None)
    expected = "b21result_" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if observed != expected:
        errors.append("public result digest mismatch")
    return sorted(set(errors))


def _synthetic_public_result() -> dict[str, Any]:
    fake = B21RunResult(
        records=[None] * b2p.B2_TOTAL_RECORDS,
        gate_result=__import__("product_bakeoff_b2_runner").B2GateResult(passed=True),
        repo_lock={"repos": []},
        task_manifest={},
        freeze_receipt={},
    )
    arm_results = tuple(
        B21ArmResult(
            summary=b2p._synthetic_summary(adapter_id),
            terminal_support_count=0,
            executed_adapter_record_count=b2p.B2_RECORDS_PER_ARM,
        )
        for adapter_id in b2p.B2_ADAPTER_IDS
    )
    decision = b2p.evaluate_tournament([row.summary for row in arm_results])
    return build_public_result(
        result=fake,
        arm_results=arm_results,
        decision=decision,
    )


def score_b21(
    *,
    result: B21RunResult,
    oracle_manifest_path: Path,
) -> tuple[tuple[B21ArmResult, ...], dict[str, Any], dict[str, Any]]:
    if result.gate_result is None or not result.gate_result.passed:
        raise B21ScoreError("B2.1 scorer cannot run before all pre-score gates pass")
    if result.logical_record_count != b2p.B2_TOTAL_RECORDS:
        raise B21ScoreError("B2.1 scorer received an incomplete logical matrix")
    if result.repo_lock is None or result.task_manifest is None:
        raise B21ScoreError("B2.1 scorer lacks task/repository bindings")
    oracle_manifest = b2c.load_json(oracle_manifest_path)
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
        raise B21ScoreError("oracle manifest differs from pre-run freeze receipt")
    oracle_by_slug = {oracle.task_slug: oracle for oracle in oracles}
    normal = _canonical_normal_cells(result)
    terminals = _canonical_terminals(result)
    arm_results = tuple(
        _build_arm_result(
            adapter_id=adapter_id,
            result=result,
            tasks=result.tasks,
            oracle_by_slug=oracle_by_slug,
            normal=normal,
            terminals=terminals,
        )
        for adapter_id in b2p.B2_ADAPTER_IDS
    )
    decision = b2p.evaluate_tournament([row.summary for row in arm_results])
    public = build_public_result(
        result=result,
        arm_results=arm_results,
        decision=decision,
    )
    return arm_results, decision, public


def write_public_result(path: Path, report: Mapping[str, Any]) -> None:
    errors = validate_public_result(dict(report))
    if errors:
        raise B21ScoreError("refusing to write unsafe public B2.1 report: " + "; ".join(errors))
    b2c.write_json(path, report)


def run_self_test() -> dict[str, Any]:
    synthetic_public = _synthetic_public_result()
    checks = [
        ("perfect_f05_inherited", b2s.f05_ppm({("a", 1)}, {("a", 1)}) == b2p.B2_FIXED_POINT_SCALE),
        ("nearest_rank_inherited", b2s.nearest_rank_p95(list(range(1, 21))) == 19),
        ("public_rank_scan", not scan_result_report({"quality_ranks": {"s0": 1, "s1": 1, "s2": 3}})),
        ("public_protocol_digest_allowed", not scan_result_report({"source_bundle_digest": "b21src_public"})),
        ("synthetic_public_result_valid", not validate_public_result(synthetic_public)),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    synthetic_public = _synthetic_public_result()
    tampered = json.loads(json.dumps(synthetic_public))
    tampered["matrix"]["logical_record_count"] = 1439
    checks = [
        ("repo_url_rejected", bool(scan_result_report({"value": "https://github.com/a/b"}))),
        ("private_task_token_rejected", bool(scan_result_report({"value": "opaque-secret-query"}, private_tokens=["opaque-secret-query"]))),
        ("private_freeze_digest_rejected", bool(scan_result_report({"freeze_receipt_digest": "private"}))),
        ("private_b21_identifier_rejected", bool(scan_result_report({"value": "b21_private_holdout"}))),
        ("tampered_public_matrix_rejected", bool(validate_public_result(tampered))),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B21ScoreError",
    "B21ArmResult",
    "score_b21",
    "build_public_result",
    "scan_result_report",
    "validate_public_result",
    "write_public_result",
    "run_self_test",
    "run_fault_test",
]
