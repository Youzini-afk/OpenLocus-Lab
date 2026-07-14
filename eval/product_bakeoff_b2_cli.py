#!/usr/bin/env python3
"""Command-line entry point for B2 authoring, freeze, RUN, and scoring."""

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
        "product_bakeoff_b2_corpus",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_adapters",
        "product_bakeoff_b2_runner",
        "product_bakeoff_b2_scorer",
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
        "b2_test_summary",
        {
            "passed": passed,
            "checks_total": total,
            "checks_passed": successful,
            "failures": failures,
        },
    )
    return 0 if passed else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenLocus B2 private tournament")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--full-run", action="store_true")
    mode.add_argument("--validate-public-result", metavar="PATH")
    parser.add_argument("--candidate-plan", type=Path)
    parser.add_argument("--private-root", type=Path)
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
        if args.candidate_plan is None or args.private_root is None:
            raise SystemExit("--prepare requires --candidate-plan and --private-root")
        author = importlib.import_module("product_bakeoff_b2_author")
        result = author.prepare_private_manifests(
            candidate_plan=args.candidate_plan,
            private_root=args.private_root,
        )
        _print_result(
            "b2_prepare",
            {
                key: result[key]
                for key in (
                    "author_version", "repo_lock_digest", "task_manifest_digest",
                    "oracle_manifest_digest", "repo_count", "task_count",
                )
            },
        )
        return 0

    if args.freeze:
        if args.private_root is None:
            raise SystemExit("--freeze requires --private-root")
        if args.openlocus is None:
            adapters = importlib.import_module("product_bakeoff_b1_adapters")
            cli_path = adapters._find_cli()
        else:
            cli_path = str(args.openlocus.resolve(strict=True))
        author = importlib.import_module("product_bakeoff_b2_author")
        result = author.freeze_private_manifests(
            private_root=args.private_root,
            cli_path=cli_path,
        )
        _print_result(
            "b2_freeze",
            {
                "freeze_receipt_digest": result["freeze_receipt_digest"],
                "source_bundle_digest": result["source_bundle_digest"],
                "runtime_bundle_digest": result["runtime_bundle_digest"],
            },
        )
        return 0

    if args.full_run:
        if args.private_root is None or args.runs_dir is None or not args.freeze_digest:
            raise SystemExit(
                "--full-run requires --private-root, --runs-dir, and --freeze-digest"
            )
        # RUN import boundary: author/oracle/scorer must still be absent.
        forbidden = {
            "product_bakeoff_b2_author",
            "product_bakeoff_b2_oracle",
            "product_bakeoff_b2_scorer",
        }
        if forbidden & set(sys.modules):
            raise SystemExit("RUN phase import boundary already contaminated")
        runner = importlib.import_module("product_bakeoff_b2_runner")
        result = runner.run_full_matrix(
            repo_lock_path=args.private_root / "b2_private_repo_lock.json",
            task_manifest_path=args.private_root / "b2_private_task_manifest.json",
            oracle_manifest_path=args.private_root / "b2_private_oracle_manifest.json",
            freeze_receipt_path=args.private_root / "b2_private_freeze_receipt.json",
            expected_freeze_digest=args.freeze_digest,
            runs_dir=args.runs_dir,
            keep_worktrees=args.keep_worktrees,
        )
        gate = result.gate_result
        _print_result(
            "b2_run_gates",
            {
                "passed": bool(gate and gate.passed),
                "record_count": len(result.records),
                "failures": dict(gate.failures) if gate else {"missing": "gate result"},
            },
        )
        if gate is None or not gate.passed:
            return 1
        scorer = importlib.import_module("product_bakeoff_b2_scorer")
        summaries, decision, public = scorer.score_b2(
            result=result,
            oracle_manifest_path=args.private_root / "b2_private_oracle_manifest.json",
        )
        private_score = {
            "schema_version": "product_bakeoff_b2_private_score_summary.v1",
            "decision": decision,
            "arm_summaries": [scorer._summary_dict(summary) for summary in summaries],
            "public_result_digest": public["result_digest"],
        }
        corpus = importlib.import_module("product_bakeoff_b2_corpus")
        corpus.write_json(args.runs_dir / "private" / "b2_private_score_summary.json", private_score)
        if args.public_out is not None:
            scorer.write_public_result(args.public_out, public)
        _print_result(
            "b2_score",
            {
                "verdict": decision["verdict"],
                "phase_c_internal_shortlist": decision["phase_c_internal_shortlist"],
                "result_digest": public["result_digest"],
                "public_result_written": args.public_out is not None,
            },
        )
        return 0

    if args.validate_public_result:
        scorer = importlib.import_module("product_bakeoff_b2_scorer")
        path = Path(args.validate_public_result)
        report = json.loads(path.read_text(encoding="utf-8"))
        errors = scorer.scan_result_report(report)
        if errors:
            _print_result("b2_public_validation", {"passed": False, "errors": errors})
            return 1
        digest = report.get("result_digest")
        payload = dict(report)
        payload.pop("result_digest", None)
        expected = "b2result_" + __import__("hashlib").sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        passed = digest == expected
        _print_result("b2_public_validation", {"passed": passed})
        return 0 if passed else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
