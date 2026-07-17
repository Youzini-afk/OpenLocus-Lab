#!/usr/bin/env python3
"""B3 scorer integration using the same canonicalizer as the runner gate.

The scorer deliberately bypasses the historical B2.1 exact-semantic-hash
canonicalizers.  It calls ``product_bakeoff_b3_repeatability`` directly, then
reuses only the frozen B2/B2.1 task scoring, arm aggregation, resource
percentiles, and tournament decision rules.

Public result publication is intentionally deferred to the later readiness and
launch phase.  This module can compute private arm aggregates only after every
pre-score gate passes; it does not authorize a run or create a result artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_corpus as b2c  # noqa: E402
import product_bakeoff_b2_protocol as b2p  # noqa: E402
from product_bakeoff_b2_oracle import validate_oracle_manifest  # noqa: E402
import product_bakeoff_b21_scorer as b21s  # noqa: E402
from product_bakeoff_b21_runner import B21RunResult, B21TerminalSupportCell  # noqa: E402
import product_bakeoff_b3_repeatability as b3r  # noqa: E402
import product_bakeoff_b3_runner as b3runner  # noqa: E402


B3_SCORER_VERSION = "product_bakeoff_b3_scorer.v1"
B3_PRIVATE_SCORE_SCHEMA = "product_bakeoff_b3_private_score.v1"


class B3ScoreError(ValueError):
    """Fail-closed B3 scoring integration error."""


@dataclass(frozen=True)
class B3CanonicalScoreCells:
    normal: Mapping[tuple[str, str, str], Any]
    terminals: Mapping[tuple[str, str], B21TerminalSupportCell]
    projection_hashes: Mapping[tuple[str, str, str], str]
    diagnostic_drift_group_count: int


def canonicalize_result_for_scoring(result: B21RunResult) -> B3CanonicalScoreCells:
    """Canonicalize all 360 logical groups through the shared B3 core."""

    try:
        expected_plan = b3runner.build_expected_observation_plan(result.tasks)
        canonical = b3r.canonicalize_for_scoring(
            result.cells,
            result.terminal_support_cells,
            expected_plan=expected_plan,
        )
    except (b3runner.B3RunError, b3r.B3RepeatabilityError, TypeError, ValueError) as exc:
        raise B3ScoreError(
            f"B3 scorer repeatability canonicalization failed: {type(exc).__name__}"
        ) from exc
    if canonical.logical_group_count != 360:
        raise B3ScoreError("B3 scorer logical group count is not 360")
    terminals: dict[tuple[str, str], B21TerminalSupportCell] = {}
    for (adapter_id, run_cell_id, operation), cell in canonical.terminal_cells.items():
        if operation != "support":
            raise B3ScoreError("B3 terminal canonical group is not support")
        key = (adapter_id, run_cell_id)
        if key in terminals:
            raise B3ScoreError("duplicate B3 terminal canonical group")
        terminals[key] = cell
    return B3CanonicalScoreCells(
        normal=dict(canonical.normal_cells),
        terminals=terminals,
        projection_hashes=dict(canonical.projection_hashes),
        diagnostic_drift_group_count=len(canonical.diagnostic_drift_groups),
    )


def score_b3(
    *,
    result: B21RunResult,
    oracle_manifest_path: Path,
) -> tuple[tuple[b21s.B21ArmResult, ...], dict[str, Any]]:
    """Compute private B3 arm aggregates after every pre-score gate passes."""

    if result.gate_result is None or not result.gate_result.passed:
        raise B3ScoreError("B3 scorer cannot run before all pre-score gates pass")
    if result.logical_record_count != b2p.B2_TOTAL_RECORDS:
        raise B3ScoreError("B3 scorer received an incomplete logical matrix")
    if result.repo_lock is None or result.task_manifest is None:
        raise B3ScoreError("B3 scorer lacks task/repository bindings")
    if result.freeze_receipt is None:
        raise B3ScoreError("B3 scorer lacks a validated freeze receipt")

    oracle_manifest = b2c.load_json(oracle_manifest_path)
    oracles = validate_oracle_manifest(
        oracle_manifest,
        tasks=result.tasks,
        repo_lock=result.repo_lock,
        task_manifest_digest=result.task_manifest["task_manifest_digest"],
    )
    if (
        oracle_manifest.get("oracle_manifest_digest")
        != result.freeze_receipt.get("oracle_manifest_digest")
    ):
        raise B3ScoreError("B3 oracle manifest differs from the pre-run freeze")
    oracle_by_slug = {oracle.task_slug: oracle for oracle in oracles}
    canonical = canonicalize_result_for_scoring(result)
    result.b3_diagnostic_drift_group_count = canonical.diagnostic_drift_group_count

    arm_results = tuple(
        b21s._build_arm_result(
            adapter_id=adapter_id,
            result=result,
            tasks=result.tasks,
            oracle_by_slug=oracle_by_slug,
            normal=canonical.normal,
            terminals=canonical.terminals,
        )
        for adapter_id in b2p.B2_ADAPTER_IDS
    )
    decision = b2p.evaluate_tournament([row.summary for row in arm_results])
    return arm_results, decision


def private_score_receipt(
    *,
    arm_results: tuple[b21s.B21ArmResult, ...],
    decision: Mapping[str, Any],
    diagnostic_drift_group_count: int,
) -> dict[str, Any]:
    """Build a private-only score receipt without task/repository identities."""

    return {
        "schema_version": B3_PRIVATE_SCORE_SCHEMA,
        "scorer_version": B3_SCORER_VERSION,
        "repeatability_policy_digest": b3r.repeatability_policy_digest(),
        "arm_count": len(arm_results),
        "logical_group_count": 360,
        "diagnostic_drift_group_count": diagnostic_drift_group_count,
        "decision_status": decision.get("status"),
        "public_result_created": False,
        "private_detail_public": False,
    }


def _poison_historical_exact_canonicalizers() -> tuple[Any, Any]:
    before = (b21s._canonical_normal_cells, b21s._canonical_terminals)

    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("historical exact-hash canonicalizer was called")

    b21s._canonical_normal_cells = forbidden
    b21s._canonical_terminals = forbidden
    return before


def _restore_historical_exact_canonicalizers(before: tuple[Any, Any]) -> None:
    b21s._canonical_normal_cells, b21s._canonical_terminals = before


def run_self_test() -> dict[str, Any]:
    inherited = b21s.run_self_test()
    result = b3runner._synthetic_result()
    before = _poison_historical_exact_canonicalizers()
    try:
        canonical = canonicalize_result_for_scoring(result)
    finally:
        _restore_historical_exact_canonicalizers(before)
    selected_repetitions = {
        cell.record.adapter_repetition for cell in canonical.normal.values()
    }
    checks = [
        inherited["passed"],
        len(canonical.normal) == 360,
        len(canonical.terminals) == 0,
        len(canonical.projection_hashes) == 360,
        canonical.diagnostic_drift_group_count == 360,
        selected_repetitions == {1},
        b21s._canonical_normal_cells is before[0],
        b21s._canonical_terminals is before[1],
    ]
    try:
        canonicalize_result_for_scoring(
            b3runner._synthetic_result(target_cardinality_drift=True)
        )
    except B3ScoreError:
        checks.append(True)
    else:
        checks.append(False)
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "historical_exact_hash_canonicalizers_called": False,
        "synthetic_logical_groups": len(canonical.projection_hashes),
    }


def run_fault_test() -> dict[str, Any]:
    inherited = b21s.run_fault_test()
    checks = [inherited["passed"]]

    result = b3runner._synthetic_result()
    result.cells.pop()
    try:
        canonicalize_result_for_scoring(result)
    except B3ScoreError:
        checks.append(True)
    else:
        checks.append(False)

    result = b3runner._synthetic_result()
    try:
        score_b3(result=result, oracle_manifest_path=Path("unused"))
    except B3ScoreError:
        checks.append(True)
    else:
        checks.append(False)

    before = (b21s._canonical_normal_cells, b21s._canonical_terminals)
    poisoned = _poison_historical_exact_canonicalizers()
    try:
        canonicalize_result_for_scoring(b3runner._synthetic_result())
        checks.append(True)
    except AssertionError:
        checks.append(False)
    finally:
        _restore_historical_exact_canonicalizers(poisoned)
    checks.append(
        b21s._canonical_normal_cells is before[0]
        and b21s._canonical_terminals is before[1]
    )
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(description="B3 shared-core scorer integration")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    args = parser.parse_args()
    result = run_self_test() if args.self_test else run_fault_test()
    _print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B3_SCORER_VERSION",
    "B3_PRIVATE_SCORE_SCHEMA",
    "B3ScoreError",
    "B3CanonicalScoreCells",
    "canonicalize_result_for_scoring",
    "score_b3",
    "private_score_receipt",
    "run_self_test",
    "run_fault_test",
]
