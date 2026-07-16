#!/usr/bin/env python3
"""Command-line entry point for B2.5 qualification, freeze, and tournament."""

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
    if (
        args.excluded_b2_repo_lock is None
        or args.excluded_b21_repo_lock is None
        or args.excluded_b24_repo_lock is None
    ):
        raise SystemExit(
            "B2.5 requires --excluded-b2-repo-lock, --excluded-b21-repo-lock, and --excluded-b24-repo-lock"
        )
    return {
        "b2": args.excluded_b2_repo_lock,
        "b21": args.excluded_b21_repo_lock,
        "b24": args.excluded_b24_repo_lock,
    }


def _run_module_tests(function_name: str) -> int:
    modules = (
        "product_bakeoff_b25_query_gate",
        "product_bakeoff_b25_runtime_qualification",
        "product_bakeoff_b25_corpus",
        "product_bakeoff_b25_runner",
        "product_bakeoff_b25_readiness",
        "product_bakeoff_b25_scorer",
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
        "b25_test_summary",
        {
            "passed": passed,
            "checks_total": total,
            "checks_passed": successful,
            "failures": failures,
        },
    )
    return 0 if passed else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenLocus B2.5 tokenizer-qualified holdout tournament"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--qualify-runtime", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--build-readiness", action="store_true")
    mode.add_argument("--authorize-launch", action="store_true")
    mode.add_argument("--full-run", action="store_true")
    mode.add_argument("--validate-runtime-qualification", type=Path)
    mode.add_argument("--validate-public-readiness", type=Path)
    mode.add_argument("--validate-public-result", type=Path)
    parser.add_argument("--candidate-plan", type=Path)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--excluded-b2-repo-lock", type=Path)
    parser.add_argument("--excluded-b21-repo-lock", type=Path)
    parser.add_argument("--excluded-b24-repo-lock", type=Path)
    parser.add_argument("--repository-exclusions", type=Path)
    parser.add_argument("--qualification-private-receipt", type=Path)
    parser.add_argument("--runtime-qualification-report", type=Path)
    parser.add_argument("--runtime-qualification-private-receipt", type=Path)
    parser.add_argument("--runtime-qualification-public-out", type=Path)
    parser.add_argument("--runtime-qualification-private-out", type=Path)
    parser.add_argument("--runtime-qualification-scratch", type=Path)
    parser.add_argument("--runtime-admission-scratch", type=Path)
    parser.add_argument("--protocol-checkpoint")
    parser.add_argument("--protocol-ci-run-id", type=int)
    parser.add_argument("--protocol-ci-conclusion")
    parser.add_argument("--runtime-qualification-checkpoint")
    parser.add_argument("--runtime-qualification-ci-run-id", type=int)
    parser.add_argument("--runtime-qualification-ci-conclusion")
    parser.add_argument("--readiness-report", type=Path)
    parser.add_argument("--readiness-out", type=Path)
    parser.add_argument("--readiness-checkpoint")
    parser.add_argument("--readiness-ci-run-id", type=int)
    parser.add_argument("--readiness-ci-conclusion")
    parser.add_argument("--treatment-runs-dir", type=Path)
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--openlocus", type=Path)
    parser.add_argument("--public-out", type=Path)
    parser.add_argument("--keep-worktrees", action="store_true")
    return parser.parse_args(argv)


def _require_authoring_common(args: argparse.Namespace) -> Mapping[str, Any]:
    required = (
        args.candidate_plan,
        args.private_root,
        args.repository_exclusions,
        args.runtime_qualification_report,
        args.runtime_qualification_private_receipt,
        args.qualification_private_receipt,
        args.runtime_admission_scratch,
        args.runtime_qualification_checkpoint,
        args.runtime_qualification_ci_run_id,
        args.runtime_qualification_ci_conclusion,
        args.openlocus,
    )
    if any(value is None for value in required):
        raise SystemExit(
            "mode requires candidate/private/exclusion inputs, all runtime qualification bindings, B2.3 private receipt, admission scratch, publication CI metadata, and --openlocus"
        )
    return {
        "candidate_plan_path": args.candidate_plan,
        "private_root": args.private_root,
        "historical_repo_lock_paths": _historical_paths(args),
        "exclusion_registry_path": args.repository_exclusions,
        "runtime_qualification_report_path": args.runtime_qualification_report,
        "runtime_qualification_private_receipt_path": (
            args.runtime_qualification_private_receipt
        ),
        "qualification_private_receipt_path": args.qualification_private_receipt,
        "runtime_admission_scratch_root": args.runtime_admission_scratch,
        "runtime_qualification_checkpoint": args.runtime_qualification_checkpoint,
        "runtime_qualification_ci_run_id": args.runtime_qualification_ci_run_id,
        "runtime_qualification_ci_conclusion": (
            args.runtime_qualification_ci_conclusion
        ),
        "cli_path": args.openlocus,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return _run_module_tests("run_self_test")
    if args.fault_test:
        return _run_module_tests("run_fault_test")
    if args.validate_runtime_qualification:
        module = importlib.import_module("product_bakeoff_b25_runtime_qualification")
        report = json.loads(args.validate_runtime_qualification.read_text(encoding="utf-8"))
        errors = module.validate_public_report(report)
        _print_result("b25_runtime_qualification_validation", {"passed": not errors, "errors": errors})
        return 0 if not errors else 1
    if args.validate_public_readiness:
        module = importlib.import_module("product_bakeoff_b25_readiness")
        report = json.loads(args.validate_public_readiness.read_text(encoding="utf-8"))
        errors = module.validate_public_readiness(report)
        _print_result("b25_readiness_validation", {"passed": not errors, "errors": errors})
        return 0 if not errors else 1
    if args.validate_public_result:
        module = importlib.import_module("product_bakeoff_b25_scorer")
        report = json.loads(args.validate_public_result.read_text(encoding="utf-8"))
        errors = module.validate_public_result(report)
        _print_result("b25_result_validation", {"passed": not errors, "errors": errors})
        return 0 if not errors else 1

    if args.openlocus is not None:
        binary = args.openlocus.resolve(strict=True)
        os.environ["OPENLOCUS_CLI"] = str(binary)

    if args.qualify_runtime:
        required = (
            args.openlocus,
            args.qualification_private_receipt,
            args.runtime_qualification_scratch,
            args.runtime_qualification_public_out,
            args.runtime_qualification_private_out,
            args.protocol_checkpoint,
            args.protocol_ci_run_id,
            args.protocol_ci_conclusion,
        )
        if any(value is None for value in required):
            raise SystemExit(
                "--qualify-runtime requires --openlocus, B2.3 private receipt, scratch, public/private outputs, and protocol checkpoint CI metadata"
            )
        module = importlib.import_module("product_bakeoff_b25_runtime_qualification")
        public, private = module.qualify_runtime(
            cli_path=args.openlocus,
            qualification_private_receipt_path=args.qualification_private_receipt,
            scratch_root=args.runtime_qualification_scratch,
            protocol_checkpoint=args.protocol_checkpoint,
            protocol_ci_run_id=args.protocol_ci_run_id,
            protocol_ci_conclusion=args.protocol_ci_conclusion,
        )
        module.write_qualification_pair(
            public_path=args.runtime_qualification_public_out,
            private_path=args.runtime_qualification_private_out,
            public_report=public,
            private_receipt=private,
        )
        _print_result(
            "b25_runtime_qualification",
            {
                "qualified": True,
                "case_count": public["synthetic_matrix"]["case_count"],
                "passed_case_count": public["synthetic_matrix"]["passed_case_count"],
                "qualification_digest": public["qualification_digest"],
                "private_values_printed": False,
                "private_holdout_read": False,
                "tournament_execution_authorized": False,
            },
        )
        return 0

    if args.prepare:
        corpus = importlib.import_module("product_bakeoff_b25_corpus")
        result = corpus.prepare_fresh_holdout(**_require_authoring_common(args))
        _print_result(
            "b25_prepare",
            {
                "prepared": True,
                "repository_count": result["repo_count"],
                "logical_task_count": result["task_count"],
                "query_compatibility_gate_passed": True,
                "private_values_printed": False,
            },
        )
        return 0

    if args.freeze:
        corpus = importlib.import_module("product_bakeoff_b25_corpus")
        corpus.freeze_fresh_holdout(**_require_authoring_common(args))
        _print_result(
            "b25_freeze",
            {
                "frozen": True,
                "runtime_bound": True,
                "query_gate_bound": True,
                "private_digests_printed": False,
                "tournament_execution_authorized": False,
            },
        )
        return 0

    if args.build_readiness:
        if args.treatment_runs_dir is None or args.readiness_out is None:
            raise SystemExit("--build-readiness requires treatment runs dir and readiness output")
        readiness = importlib.import_module("product_bakeoff_b25_readiness")
        common = dict(_require_authoring_common(args))
        preauthoring_checkpoint = common.pop("runtime_qualification_checkpoint")
        preauthoring_ci_run_id = common.pop("runtime_qualification_ci_run_id")
        preauthoring_ci_conclusion = common.pop("runtime_qualification_ci_conclusion")
        report = readiness.build_public_readiness(
            **common,
            treatment_runs_dir=args.treatment_runs_dir,
            preauthoring_checkpoint=preauthoring_checkpoint,
            preauthoring_ci_run_id=preauthoring_ci_run_id,
            preauthoring_ci_conclusion=preauthoring_ci_conclusion,
        )
        readiness.write_public(args.readiness_out, report)
        _print_result(
            "b25_readiness",
            {
                "written": True,
                "repository_count": report["private_holdout"]["repository_count"],
                "logical_task_count": report["private_holdout"]["logical_task_count"],
                "query_compatibility_gate_passed": report["decision"]["query_compatibility_gate_passed"],
                "treatment_output_count": report["execution_state"]["treatment_output_count"],
                "readiness_digest": report["readiness_digest"],
            },
        )
        return 0

    if args.authorize_launch:
        if (
            args.private_root is None
            or args.readiness_report is None
            or not args.readiness_checkpoint
            or args.readiness_ci_run_id is None
            or not args.readiness_ci_conclusion
        ):
            raise SystemExit(
                "--authorize-launch requires private root, readiness report, checkpoint, CI run id, and success conclusion"
            )
        corpus = importlib.import_module("product_bakeoff_b25_corpus")
        corpus.create_launch_authorization(
            private_root=args.private_root,
            readiness_report_path=args.readiness_report,
            readiness_checkpoint=args.readiness_checkpoint,
            readiness_ci_run_id=args.readiness_ci_run_id,
            readiness_ci_conclusion=args.readiness_ci_conclusion,
        )
        _print_result(
            "b25_launch_authorization",
            {"authorized": True, "attempt_number": 1, "private_digest_printed": False},
        )
        return 0

    if args.full_run:
        required = (
            args.candidate_plan,
            args.private_root,
            args.repository_exclusions,
            args.runtime_qualification_report,
            args.runtime_qualification_private_receipt,
            args.qualification_private_receipt,
            args.readiness_report,
            args.runs_dir,
            args.openlocus,
        )
        if any(value is None for value in required):
            raise SystemExit("--full-run is missing a required frozen input")
        historical = _historical_paths(args)
        forbidden = {
            "product_bakeoff_b2_author",
            "product_bakeoff_b2_oracle",
            "product_bakeoff_b2_scorer",
            "product_bakeoff_b21_scorer",
            "product_bakeoff_b24_scorer",
            "product_bakeoff_b25_scorer",
        }
        if forbidden & set(sys.modules):
            raise SystemExit("B2.5 RUN import boundary already contaminated")
        runner = importlib.import_module("product_bakeoff_b25_runner")
        result = runner.run_full_matrix(
            private_root=args.private_root,
            candidate_plan_path=args.candidate_plan,
            historical_repo_lock_paths=historical,
            exclusion_registry_path=args.repository_exclusions,
            runtime_qualification_report_path=args.runtime_qualification_report,
            runtime_qualification_private_receipt_path=(
                args.runtime_qualification_private_receipt
            ),
            qualification_private_receipt_path=args.qualification_private_receipt,
            readiness_report_path=args.readiness_report,
            runs_dir=args.runs_dir,
            cli_path=args.openlocus,
            keep_worktrees=args.keep_worktrees,
        )
        gate = result.gate_result
        _print_result(
            "b25_run_gates",
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
        scorer = importlib.import_module("product_bakeoff_b25_scorer")
        b2c = importlib.import_module("product_bakeoff_b2_corpus")
        readiness_report = b2c.load_json(args.readiness_report)
        launch_authorization = b2c.load_json(
            args.private_root / "b25_private_launch_authorization.json"
        )
        arm_results, decision, public = scorer.score_b25(
            result=result,
            oracle_manifest_path=args.private_root / "b2_private_oracle_manifest.json",
            readiness_report=readiness_report,
            readiness_report_path=args.readiness_report,
            launch_authorization=launch_authorization,
        )
        private_score = {
            "schema_version": "product_bakeoff_b25_private_score_summary.v1",
            "decision": decision,
            "arm_summaries": [scorer.b21s._arm_public(row) for row in arm_results],
            "public_result_digest": public["result_digest"],
        }
        b2c.write_json(args.runs_dir / "private" / "b25_private_score_summary.json", private_score)
        if args.public_out is not None:
            scorer.write_public_result(args.public_out, public)
        _print_result(
            "b25_score",
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
