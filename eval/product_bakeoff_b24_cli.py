#!/usr/bin/env python3
"""Command-line entry point for B2.4 authoring, freeze, readiness, and RUN."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


def _print_result(label: str, value: Any) -> None:
    print(label + ": " + json.dumps(value, sort_keys=True), flush=True)


def _historical_paths(args: argparse.Namespace) -> dict[str, Path]:
    if args.excluded_b2_repo_lock is None or args.excluded_b21_repo_lock is None:
        raise SystemExit("B2.4 requires both --excluded-b2-repo-lock and --excluded-b21-repo-lock")
    return {
        "b2": args.excluded_b2_repo_lock,
        "b21": args.excluded_b21_repo_lock,
    }


def _run_module_tests(function_name: str) -> int:
    modules = (
        "product_bakeoff_b24_corpus",
        "product_bakeoff_b24_runner",
        "product_bakeoff_b24_readiness",
        "product_bakeoff_b24_scorer",
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
        "b24_test_summary",
        {
            "passed": passed,
            "checks_total": total,
            "checks_passed": successful,
            "failures": failures,
        },
    )
    return 0 if passed else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenLocus B2.4 qualified holdout tournament")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--build-readiness", action="store_true")
    mode.add_argument("--authorize-launch", action="store_true")
    mode.add_argument("--full-run", action="store_true")
    mode.add_argument("--validate-public-readiness", type=Path)
    mode.add_argument("--validate-public-result", type=Path)
    parser.add_argument("--candidate-plan", type=Path)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--excluded-b2-repo-lock", type=Path)
    parser.add_argument("--excluded-b21-repo-lock", type=Path)
    parser.add_argument("--repository-exclusions", type=Path)
    parser.add_argument("--qualification-report", type=Path)
    parser.add_argument("--qualification-private-receipt", type=Path)
    parser.add_argument("--readiness-report", type=Path)
    parser.add_argument("--readiness-out", type=Path)
    parser.add_argument("--protocol-checkpoint")
    parser.add_argument("--protocol-ci-run-id", type=int)
    parser.add_argument("--protocol-ci-conclusion")
    parser.add_argument("--readiness-checkpoint")
    parser.add_argument("--readiness-ci-run-id", type=int)
    parser.add_argument("--readiness-ci-conclusion")
    parser.add_argument("--treatment-runs-dir", type=Path)
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--openlocus", type=Path)
    parser.add_argument("--public-out", type=Path)
    parser.add_argument("--keep-worktrees", action="store_true")
    return parser.parse_args(argv)


def _require_common_private(args: argparse.Namespace) -> Mapping[str, Any]:
    if (
        args.candidate_plan is None
        or args.private_root is None
        or args.repository_exclusions is None
        or args.qualification_report is None
    ):
        raise SystemExit(
            "mode requires --candidate-plan, --private-root, --repository-exclusions, and --qualification-report"
        )
    return {
        "candidate_plan_path": args.candidate_plan,
        "private_root": args.private_root,
        "historical_repo_lock_paths": _historical_paths(args),
        "exclusion_registry_path": args.repository_exclusions,
        "qualification_report_path": args.qualification_report,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return _run_module_tests("run_self_test")
    if args.fault_test:
        return _run_module_tests("run_fault_test")
    if args.validate_public_readiness:
        readiness = importlib.import_module("product_bakeoff_b24_readiness")
        report = json.loads(args.validate_public_readiness.read_text(encoding="utf-8"))
        errors = readiness.validate_public_readiness(report)
        _print_result("b24_readiness_validation", {"passed": not errors, "errors": errors})
        return 0 if not errors else 1
    if args.validate_public_result:
        scorer = importlib.import_module("product_bakeoff_b24_scorer")
        report = json.loads(args.validate_public_result.read_text(encoding="utf-8"))
        errors = scorer.validate_public_result(report)
        _print_result("b24_result_validation", {"passed": not errors, "errors": errors})
        return 0 if not errors else 1

    common = _require_common_private(args)
    if args.openlocus is not None:
        binary = args.openlocus.resolve(strict=True)
        os.environ["OPENLOCUS_CLI"] = str(binary)

    if args.prepare:
        corpus = importlib.import_module("product_bakeoff_b24_corpus")
        result = corpus.prepare_fresh_holdout(**common)
        _print_result(
            "b24_prepare",
            {
                "prepared": True,
                "repository_count": result["repo_count"],
                "logical_task_count": result["task_count"],
                "private_values_printed": False,
            },
        )
        return 0

    if args.freeze:
        if args.openlocus is None:
            raise SystemExit("--freeze requires --openlocus")
        corpus = importlib.import_module("product_bakeoff_b24_corpus")
        corpus.freeze_fresh_holdout(**common, cli_path=args.openlocus)
        _print_result(
            "b24_freeze",
            {
                "frozen": True,
                "runtime_bound": True,
                "private_digests_printed": False,
                "tournament_execution_authorized": False,
            },
        )
        return 0

    if args.build_readiness:
        if (
            args.openlocus is None
            or args.treatment_runs_dir is None
            or args.readiness_out is None
            or not args.protocol_checkpoint
            or args.protocol_ci_run_id is None
            or not args.protocol_ci_conclusion
        ):
            raise SystemExit(
                "--build-readiness requires --openlocus, --treatment-runs-dir, --readiness-out, --protocol-checkpoint, --protocol-ci-run-id, and --protocol-ci-conclusion"
            )
        readiness = importlib.import_module("product_bakeoff_b24_readiness")
        report = readiness.build_public_readiness(
            **common,
            cli_path=args.openlocus,
            treatment_runs_dir=args.treatment_runs_dir,
            protocol_checkpoint=args.protocol_checkpoint,
            protocol_ci_run_id=args.protocol_ci_run_id,
            protocol_ci_conclusion=args.protocol_ci_conclusion,
        )
        readiness.write_public(args.readiness_out, report)
        _print_result(
            "b24_readiness",
            {
                "written": True,
                "repository_count": report["private_holdout"]["repository_count"],
                "logical_task_count": report["private_holdout"]["logical_task_count"],
                "treatment_output_count": report["execution_state"]["treatment_output_count"],
                "readiness_digest": report["readiness_digest"],
            },
        )
        return 0

    if args.authorize_launch:
        if (
            args.readiness_report is None
            or not args.readiness_checkpoint
            or args.readiness_ci_run_id is None
            or not args.readiness_ci_conclusion
        ):
            raise SystemExit(
                "--authorize-launch requires --readiness-report, --readiness-checkpoint, --readiness-ci-run-id, and --readiness-ci-conclusion"
            )
        corpus = importlib.import_module("product_bakeoff_b24_corpus")
        corpus.create_launch_authorization(
            private_root=args.private_root,
            readiness_report_path=args.readiness_report,
            readiness_checkpoint=args.readiness_checkpoint,
            readiness_ci_run_id=args.readiness_ci_run_id,
            readiness_ci_conclusion=args.readiness_ci_conclusion,
        )
        _print_result(
            "b24_launch_authorization",
            {
                "authorized": True,
                "attempt_number": 1,
                "private_digest_printed": False,
            },
        )
        return 0

    if args.full_run:
        if (
            args.openlocus is None
            or args.qualification_private_receipt is None
            or args.readiness_report is None
            or args.runs_dir is None
        ):
            raise SystemExit(
                "--full-run requires --openlocus, --qualification-private-receipt, --readiness-report, and --runs-dir"
            )
        forbidden = {
            "product_bakeoff_b2_author",
            "product_bakeoff_b2_oracle",
            "product_bakeoff_b2_scorer",
            "product_bakeoff_b21_scorer",
            "product_bakeoff_b24_scorer",
        }
        if forbidden & set(sys.modules):
            raise SystemExit("B2.4 RUN import boundary already contaminated")
        runner = importlib.import_module("product_bakeoff_b24_runner")
        result = runner.run_full_matrix(
            **common,
            qualification_private_receipt_path=args.qualification_private_receipt,
            readiness_report_path=args.readiness_report,
            runs_dir=args.runs_dir,
            cli_path=args.openlocus,
            keep_worktrees=args.keep_worktrees,
        )
        gate = result.gate_result
        _print_result(
            "b24_run_gates",
            {
                "passed": bool(gate and gate.passed),
                "logical_record_count": result.logical_record_count,
                "normal_record_count": len(result.records),
                "terminal_support_record_count": len(result.terminal_support_cells),
                "failure_gate_count": len(gate.failures) if gate else 1,
                "private_failure_details_printed": False,
            },
        )
        if gate is None or not gate.passed:
            return 1
        scorer = importlib.import_module("product_bakeoff_b24_scorer")
        b2c = importlib.import_module("product_bakeoff_b2_corpus")
        readiness_report = b2c.load_json(args.readiness_report)
        launch_authorization = b2c.load_json(
            args.private_root / "b24_private_launch_authorization.json"
        )
        arm_results, decision, public = scorer.score_b24(
            result=result,
            oracle_manifest_path=args.private_root / "b2_private_oracle_manifest.json",
            readiness_report=readiness_report,
            readiness_report_path=args.readiness_report,
            launch_authorization=launch_authorization,
        )
        private_score = {
            "schema_version": "product_bakeoff_b24_private_score_summary.v1",
            "decision": decision,
            "arm_summaries": [scorer.b21s._arm_public(row) for row in arm_results],
            "public_result_digest": public["result_digest"],
        }
        b2c.write_json(
            args.runs_dir / "private" / "b24_private_score_summary.json",
            private_score,
        )
        if args.public_out is not None:
            scorer.write_public_result(args.public_out, public)
        _print_result(
            "b24_score",
            {
                "verdict": decision["verdict"],
                "phase_c_internal_shortlist": decision["phase_c_internal_shortlist"],
                "result_digest": public["result_digest"],
                "public_result_written": args.public_out is not None,
            },
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
