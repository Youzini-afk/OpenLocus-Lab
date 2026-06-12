#!/usr/bin/env python3
"""R50 CI Validate Report: fail CI unless all invariants hold.

Checks:
1. citation_validity for all implemented strategies == 1.0
2. Artifact private-field scan is clean
3. Run/Score separation flags are true
4. promotion_ready == false
5. Unavailable strategies are reason-only with no numeric quality metrics
6. default_should_change == false

Usage:
    python3 eval/ci_validate_report.py \\
        --report eval/ci_output/score/report.json \\
        --run-dir eval/ci_output/run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PRIVATE_FIELD_DENYLIST = [
    "source_category", "risk_public", "intent_guess", "risk_tags",
    "oracle_type", "expected_behavior", "gold_spans",
    "hard_distractors", "must_not_primary", "why_this_is_hard",
    "which_strategy_it_targets",
]

# Numeric quality metric keys that must NOT appear for unavailable strategies
QUALITY_METRIC_KEYS = [
    "FileRecall", "MRR", "SpanF0.5", "SpanPrecision", "SpanRecall",
    "token_waste", "primary_false_positive_rate", "abstain_rate",
    "hard_distractor_hit_rate", "no_gold_nonempty_rate",
    "must_not_primary_violation_rate", "success_rate",
    "FileRecall@1", "FileRecall@3", "FileRecall@5",
]


def validate_report(report: dict[str, Any], run_dir: Path) -> list[str]:
    """Validate CI report. Returns list of failure reasons (empty = pass)."""
    failures: list[str] = []

    # 1. citation_validity all implemented == 1.0
    citation_valid = report.get("citation_validity_all_implemented", False)
    if not citation_valid:
        failures.append("citation_validity_all_implemented is not true")
    # Also check per-strategy
    for strategy, metrics in report.get("strategies", {}).items():
        cv = metrics.get("citation_validity", 0.0)
        total = metrics.get("citation_total_count", 0)
        if total > 0 and cv < 1.0:
            failures.append(
                f"Strategy {strategy}: citation_validity={cv} < 1.0 "
                f"(valid={metrics.get('citation_valid_count')}, total={total})"
            )

    # 2. Artifact private-field scan is clean
    scan_summary = report.get("private_scan_summary", {})
    if not scan_summary.get("clean", False):
        violations = scan_summary.get("violations", "?")
        failures.append(
            f"Private field scan not clean: {violations} violations found"
        )

    # Also scan run artifacts
    run_scan_issues = _scan_run_dir_for_private_fields(Path(run_dir))
    if run_scan_issues:
        failures.extend(run_scan_issues)

    report_scan_issues: list[str] = []
    _scan_object_for_private_fields(report, "report", report_scan_issues)
    if report_scan_issues:
        failures.extend(report_scan_issues)

    # 3. Run/Score separation flags
    if not report.get("run_score_separation", False):
        failures.append("run_score_separation flag is not true")
    if report.get("labels_used_in_run_phase", True):
        failures.append("labels_used_in_run_phase should be false (run phase must not use labels)")

    # 4. promotion_ready == false
    if report.get("promotion_ready", True):
        failures.append("promotion_ready must be false")

    # 5. default_should_change == false
    if report.get("default_should_change", True):
        failures.append("default_should_change must be false")

    # 6. Unavailable strategies are reason-only with no numeric quality metrics
    for strat, info in report.get("unavailable_strategies", {}).items():
        if info.get("status") != "unavailable":
            failures.append(f"Unavailable strategy {strat}: status must be 'unavailable'")
        if not info.get("reason"):
            failures.append(f"Unavailable strategy {strat}: must have a reason")
        extra_keys = set(info) - {"status", "reason"}
        if extra_keys:
            failures.append(
                f"Unavailable strategy {strat}: reason-only status has extra keys {sorted(extra_keys)}"
            )
        if info.get("metrics") is not None:
            failures.append(
                f"Unavailable strategy {strat}: must not have metrics (got {info.get('metrics')})"
            )
        if info.get("quality_numbers") is not None:
            failures.append(
                f"Unavailable strategy {strat}: must not have quality_numbers "
                f"(got {info.get('quality_numbers')})"
            )
        # Check that no quality metric keys appear in the info dict
        for key in QUALITY_METRIC_KEYS:
            if key in info:
                failures.append(
                    f"Unavailable strategy {strat}: contains quality metric key '{key}'"
                )

    # Also check strategy_registry for unavailable entries
    for strat, entry in report.get("strategy_registry", {}).items():
        if entry.get("status") == "unavailable":
            extra_keys = set(entry) - {"status", "reason"}
            if extra_keys:
                failures.append(
                    f"Strategy registry: unavailable strategy {strat} has extra keys {sorted(extra_keys)}"
                )
            if entry.get("metrics_available", False):
                failures.append(
                    f"Strategy registry: unavailable strategy {strat} has metrics_available=true"
                )

    return failures


def _scan_object_for_private_fields(obj: Any, where: str, issues: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in PRIVATE_FIELD_DENYLIST:
                issues.append(f"CRITICAL: Private field '{key}' in {where}")
            _scan_object_for_private_fields(value, f"{where}.{key}", issues)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _scan_object_for_private_fields(item, f"{where}[{idx}]", issues)


def _scan_run_dir_for_private_fields(run_dir: Path) -> list[str]:
    """Scan run directory artifacts for private fields."""
    issues: list[str] = []
    if not run_dir.exists():
        return issues

    for jsonl_path in sorted(run_dir.rglob("*.jsonl")):
        try:
            text = jsonl_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            for field in PRIVATE_FIELD_DENYLIST:
                if field in obj:
                    issues.append(
                        f"CRITICAL: Private field '{field}' in {jsonl_path.name}:{line_no}"
                    )
            for e in obj.get("evidence", []):
                for field in PRIVATE_FIELD_DENYLIST:
                    if field in e:
                        issues.append(
                            f"CRITICAL: Private field '{field}' in evidence in {jsonl_path.name}:{line_no}"
                        )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="R50 CI Validate Report")
    parser.add_argument("--report", required=True, help="Score report JSON path")
    parser.add_argument("--run-dir", required=True, help="Run output directory for artifact scan")
    args = parser.parse_args()

    report_path = Path(args.report)
    run_dir = Path(args.run_dir)

    if not report_path.exists():
        print(f"ERROR: Report not found: {report_path}", file=sys.stderr)
        sys.exit(1)

    report = json.loads(report_path.read_text(encoding="utf-8"))

    failures = validate_report(report, run_dir)

    if failures:
        print("CI VALIDATION FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        sys.exit(1)
    else:
        print("CI VALIDATION PASSED")
        print(f"  citation_validity_all_implemented: {report.get('citation_validity_all_implemented')}")
        print(f"  promotion_ready: {report.get('promotion_ready')}")
        print(f"  default_should_change: {report.get('default_should_change')}")
        print(f"  run_score_separation: {report.get('run_score_separation')}")
        print(f"  private_scan_clean: {report.get('private_scan_summary', {}).get('clean')}")
        print(f"  strategies_validated: {len(report.get('strategies', {}))}")
        print(f"  unavailable_strategies: {list(report.get('unavailable_strategies', {}).keys())}")


if __name__ == "__main__":
    main()
