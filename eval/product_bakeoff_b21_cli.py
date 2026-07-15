#!/usr/bin/env python3
"""Command-line entry point for B2.1 prepare, freeze, RUN, and scoring."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def _print_result(label: str, value: Any) -> None:
    print(label + ": " + json.dumps(value, sort_keys=True), flush=True)


def _run_module_tests(function_name: str) -> int:
    modules = (
        "product_bakeoff_b21_corpus",
        "product_bakeoff_b21_runner",
        "product_bakeoff_b21_scorer",
    )
    passed = True
    total = 0
    successful = 0
    failures: dict[str, list[str]] = {}
    for module_name in modules:
        module = importlib.import_module(module_name)
        result = getattr(module, function_name)()
        _print_result(module_name, result)
        total += int(result["checks_total"])
        successful += int(result["checks_passed"])
        if not result["passed"]:
            passed = False
            failures[module_name] = list(result["failed"])
    _print_result(
        "b21_test_summary",
        {
            "passed": passed,
            "checks_total": total,
            "checks_passed": successful,
            "failures": failures,
        },
    )
    return 0 if passed else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenLocus B2.1 own-parent tournament")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--full-run", action="store_true")
    mode.add_argument("--validate-public-result", metavar="PATH")
    parser.add_argument("--candidate-plan", type=Path)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--excluded-repo-lock", type=Path)
    parser.add_argument("--preflight-exclusions", type=Path)
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--freeze-digest")
    parser.add_argument("--openlocus", type=Path)
    parser.add_argument("--public-out", type=Path)
    parser.add_argument("--keep-worktrees", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return _run_module_tests("run_self_test")
    if args.fault_test:
        return _run_module_tests("run_fault_test")

    if args.openlocus is not None:
        binary = args.openlocus.resolve(strict=True)
        os.environ["OPENLOCUS_CLI"] = str(binary)

    if args.prepare:
        if (
            args.candidate_plan is None
            or args.private_root is None
            or args.excluded_repo_lock is None
            or args.preflight_exclusions is None
        ):
            raise SystemExit(
                "--prepare requires --candidate-plan, --private-root, --excluded-repo-lock, and --preflight-exclusions"
            )
        corpus = importlib.import_module("product_bakeoff_b21_corpus")
        result = corpus.prepare_fresh_holdout(
            candidate_plan_path=args.candidate_plan,
            private_root=args.private_root,
            excluded_repo_lock_path=args.excluded_repo_lock,
            preflight_exclusion_path=args.preflight_exclusions,
        )
        _print_result(
            "b21_prepare",
            {
                key: result[key]
                for key in (
                    "author_version",
                    "repo_lock_digest",
                    "task_manifest_digest",
                    "oracle_manifest_digest",
                    "holdout_binding_digest",
                    "repo_count",
                    "task_count",
                )
            },
        )
        return 0

    if args.freeze:
        if (
            args.private_root is None
            or args.excluded_repo_lock is None
            or args.preflight_exclusions is None
        ):
            raise SystemExit(
                "--freeze requires --private-root, --excluded-repo-lock, and --preflight-exclusions"
            )
        if args.openlocus is None:
            adapters = importlib.import_module("product_bakeoff_b1_adapters")
            cli_path = adapters._find_cli()
        else:
            cli_path = str(args.openlocus.resolve(strict=True))
        corpus = importlib.import_module("product_bakeoff_b21_corpus")
        result = corpus.freeze_fresh_holdout(
            private_root=args.private_root,
            excluded_repo_lock_path=args.excluded_repo_lock,
            preflight_exclusion_path=args.preflight_exclusions,
            cli_path=cli_path,
        )
        _print_result(
            "b21_freeze",
            {
                "freeze_receipt_digest": result["freeze_receipt_digest"],
                "source_bundle_digest": result["source_bundle_digest"],
                "runtime_bundle_digest": result["runtime_bundle_digest"],
            },
        )
        return 0

    if args.full_run:
        if (
            args.private_root is None
            or args.excluded_repo_lock is None
            or args.preflight_exclusions is None
            or args.runs_dir is None
            or not args.freeze_digest
        ):
            raise SystemExit(
                "--full-run requires --private-root, --excluded-repo-lock, --preflight-exclusions, --runs-dir, and --freeze-digest"
            )
        forbidden = {
            "product_bakeoff_b2_author",
            "product_bakeoff_b2_oracle",
            "product_bakeoff_b2_scorer",
            "product_bakeoff_b21_scorer",
        }
        if forbidden & set(sys.modules):
            raise SystemExit("B2.1 RUN import boundary already contaminated")
        runner = importlib.import_module("product_bakeoff_b21_runner")
        result = runner.run_full_matrix(
            repo_lock_path=args.private_root / "b2_private_repo_lock.json",
            task_manifest_path=args.private_root / "b2_private_task_manifest.json",
            oracle_manifest_path=args.private_root / "b2_private_oracle_manifest.json",
            holdout_binding_path=args.private_root / "b21_private_holdout_binding.json",
            excluded_repo_lock_path=args.excluded_repo_lock,
            preflight_exclusion_path=args.preflight_exclusions,
            freeze_receipt_path=args.private_root / "b21_private_freeze_receipt.json",
            expected_freeze_digest=args.freeze_digest,
            runs_dir=args.runs_dir,
            keep_worktrees=args.keep_worktrees,
        )
        gate = result.gate_result
        _print_result(
            "b21_run_gates",
            {
                "passed": bool(gate and gate.passed),
                "logical_record_count": result.logical_record_count,
                "normal_record_count": len(result.records),
                "terminal_support_record_count": len(result.terminal_support_cells),
                "failures": dict(gate.failures) if gate else {"missing": "gate result"},
            },
        )
        if gate is None or not gate.passed:
            return 1
        scorer = importlib.import_module("product_bakeoff_b21_scorer")
        arm_results, decision, public = scorer.score_b21(
            result=result,
            oracle_manifest_path=args.private_root / "b2_private_oracle_manifest.json",
        )
        private_score = {
            "schema_version": "product_bakeoff_b21_private_score_summary.v1",
            "decision": decision,
            "arm_summaries": [scorer._arm_public(row) for row in arm_results],
            "public_result_digest": public["result_digest"],
        }
        b2c = importlib.import_module("product_bakeoff_b2_corpus")
        b2c.write_json(
            args.runs_dir / "private" / "b21_private_score_summary.json",
            private_score,
        )
        if args.public_out is not None:
            scorer.write_public_result(args.public_out, public)
        _print_result(
            "b21_score",
            {
                "verdict": decision["verdict"],
                "phase_c_internal_shortlist": decision["phase_c_internal_shortlist"],
                "result_digest": public["result_digest"],
                "public_result_written": args.public_out is not None,
            },
        )
        return 0

    if args.validate_public_result:
        scorer = importlib.import_module("product_bakeoff_b21_scorer")
        path = Path(args.validate_public_result)
        report = json.loads(path.read_text(encoding="utf-8"))
        errors = scorer.validate_public_result(report)
        _print_result(
            "b21_public_validation",
            {"passed": not errors, "errors": errors},
        )
        return 0 if not errors else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
