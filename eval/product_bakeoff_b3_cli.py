#!/usr/bin/env python3
"""Closed command surface for B3 qualification, freeze, launch, and closeout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b3_corpus as b3c
import product_bakeoff_b3_execution as b3e
import product_bakeoff_b3_readiness as b3ready
import product_bakeoff_b3_runtime_qualification as b3rq
import product_bakeoff_b3_source as b3src


def _print(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), sort_keys=True))


def _histories(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "b2": args.history_b2,
        "b21": args.history_b21,
        "b24": args.history_b24,
        "b25": args.history_b25,
    }


def _add_history(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--history-b2", type=Path, required=True)
    parser.add_argument("--history-b21", type=Path, required=True)
    parser.add_argument("--history-b24", type=Path, required=True)
    parser.add_argument("--history-b25", type=Path, required=True)


def _add_runtime_publication(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime-public", type=Path, required=True)
    parser.add_argument("--runtime-private", type=Path, required=True)
    parser.add_argument("--runtime-scratch", type=Path, required=True)
    parser.add_argument("--runtime-publication-checkpoint", required=True)
    parser.add_argument("--runtime-publication-ci-run-id", type=int, required=True)
    parser.add_argument(
        "--runtime-publication-ci-conclusion", default="success", choices=("success",)
    )
    parser.add_argument("--cli", type=Path, required=True)


def _add_frozen_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--candidate-plan", type=Path, required=True)
    _add_history(parser)
    parser.add_argument("--exclusion-registry", type=Path, required=True)
    _add_runtime_publication(parser)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    sub.add_parser("fault-test")

    qualify = sub.add_parser("qualify-runtime")
    qualify.add_argument("--cli", type=Path, required=True)
    qualify.add_argument("--scratch", type=Path, required=True)
    qualify.add_argument("--source-checkpoint", required=True)
    qualify.add_argument("--source-ci-run-id", type=int, required=True)
    qualify.add_argument("--source-ci-conclusion", default="success", choices=("success",))
    qualify.add_argument("--public-out", type=Path, required=True)
    qualify.add_argument("--private-out", type=Path, required=True)

    prepare = sub.add_parser("prepare-holdout")
    _add_frozen_inputs(prepare)
    prepare.add_argument(
        "--authoring-cache-root",
        type=Path,
        action="append",
        default=[],
        help="Prior private authoring root or clones directory to revalidate as cache",
    )

    freeze = sub.add_parser("freeze-holdout")
    _add_frozen_inputs(freeze)

    readiness = sub.add_parser("build-readiness")
    _add_frozen_inputs(readiness)
    readiness.add_argument("--runs-dir", type=Path, required=True)
    readiness.add_argument("--public-out", type=Path, required=True)

    authorize = sub.add_parser("authorize-launch")
    authorize.add_argument("--private-root", type=Path, required=True)
    authorize.add_argument("--readiness", type=Path, required=True)
    authorize.add_argument("--readiness-checkpoint", required=True)
    authorize.add_argument("--readiness-ci-run-id", type=int, required=True)
    authorize.add_argument("--readiness-ci-conclusion", default="success", choices=("success",))

    run = sub.add_parser("run")
    _add_frozen_inputs(run)
    run.add_argument("--readiness", type=Path, required=True)
    run.add_argument("--runs-dir", type=Path, required=True)
    run.add_argument("--public-out", type=Path, required=True)
    run.add_argument("--keep-worktrees", action="store_true")

    interrupted = sub.add_parser("closeout-interrupted")
    interrupted.add_argument("--private-root", type=Path, required=True)
    interrupted.add_argument("--runs-dir", type=Path, required=True)
    interrupted.add_argument("--public-out", type=Path, required=True)
    interrupted.add_argument("--worker-exit-code", type=int, required=True)
    interrupted.add_argument("--worker-pid-identity", type=Path, required=True)
    interrupted.add_argument("--confirm-worker-stopped", action="store_true")

    audit = sub.add_parser("audit-preboundary")
    audit.add_argument("--runs-dir", type=Path, required=True)

    check = sub.add_parser("check-public")
    check.add_argument("path", type=Path)
    return parser.parse_args(argv)


def _run_module_tests(function_name: str) -> dict[str, Any]:
    import product_bakeoff_b3_publication as publication

    modules = (b3src, b3rq, b3c, b3ready, publication, b3e)
    reports = {module.__name__: getattr(module, function_name)() for module in modules}
    passed = all(report["passed"] for report in reports.values())
    return {"passed": passed, "reports": reports}


def _frozen_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "private_root": args.private_root,
        "candidate_plan_path": args.candidate_plan,
        "historical_repo_lock_paths": _histories(args),
        "exclusion_registry_path": args.exclusion_registry,
        "runtime_public_path": args.runtime_public,
        "runtime_private_path": args.runtime_private,
        "runtime_scratch": args.runtime_scratch,
        "runtime_publication_checkpoint": args.runtime_publication_checkpoint,
        "runtime_publication_ci_run_id": args.runtime_publication_ci_run_id,
        "runtime_publication_ci_conclusion": args.runtime_publication_ci_conclusion,
        "cli_path": args.cli,
    }


def _check_public(path: Path) -> list[str]:
    value = b2c.load_json(path)
    schema = value.get("schema_version") if isinstance(value, dict) else None
    if schema == b3rq.B3_RUNTIME_PUBLIC_SCHEMA:
        return b3rq.validate_public_report(value)
    if schema == b3ready.B3_READINESS_SCHEMA:
        return b3ready.validate_public_readiness(value)
    import product_bakeoff_b3_publication as publication

    if schema == publication.B3_RESULT_SCHEMA:
        return publication.validate_public_result(value)
    if schema == publication.B3_FAILURE_SCHEMA:
        return publication.validate_public_failure(value)
    return ["unknown B3 public artifact schema"]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "self-test":
            report = _run_module_tests("run_self_test")
            _print(report)
            return 0 if report["passed"] else 1
        if args.command == "fault-test":
            report = _run_module_tests("run_fault_test")
            _print(report)
            return 0 if report["passed"] else 1
        if args.command == "qualify-runtime":
            public, private = b3rq.qualify_runtime(
                cli_path=args.cli,
                scratch_root=args.scratch,
                source_checkpoint=args.source_checkpoint,
                source_ci_run_id=args.source_ci_run_id,
                source_ci_conclusion=args.source_ci_conclusion,
            )
            b3rq.write_qualification_pair(
                public_path=args.public_out,
                private_path=args.private_out,
                public_report=public,
                private_receipt=private,
            )
            _print(
                {
                    "status": "runtime_qualified_public_aggregate_written",
                    "qualification_digest": public["qualification_digest"],
                    "private_path_printed": False,
                }
            )
            return 0
        if args.command == "prepare-holdout":
            result = b3c.prepare_fresh_holdout(
                **_frozen_kwargs(args),
                authoring_cache_roots=tuple(args.authoring_cache_root),
            )
            _print(
                {
                    "status": "private_holdout_authored",
                    "repository_count": result["repo_count"],
                    "logical_task_count": result["task_count"],
                    "checkpoint_count": result["checkpoint_count"],
                    "resumed_checkpoint_count": result[
                        "resumed_checkpoint_count"
                    ],
                    "private_paths_or_digests_printed": False,
                }
            )
            return 0
        if args.command == "freeze-holdout":
            b3c.freeze_fresh_holdout(**_frozen_kwargs(args))
            _print(
                {
                    "status": "private_holdout_frozen",
                    "repository_count": 12,
                    "logical_task_count": 48,
                    "private_paths_or_digests_printed": False,
                }
            )
            return 0
        if args.command == "build-readiness":
            readiness = b3ready.build_public_readiness(
                **_frozen_kwargs(args), treatment_runs_dir=args.runs_dir
            )
            b3ready.write_public(args.public_out, readiness)
            _print(
                {
                    "status": "public_readiness_written",
                    "readiness_digest": readiness["readiness_digest"],
                    "treatment_output_count": 0,
                }
            )
            return 0
        if args.command == "authorize-launch":
            b3c.create_launch_authorization(
                private_root=args.private_root,
                readiness_report_path=args.readiness,
                readiness_checkpoint=args.readiness_checkpoint,
                readiness_ci_run_id=args.readiness_ci_run_id,
                readiness_ci_conclusion=args.readiness_ci_conclusion,
            )
            _print(
                {
                    "status": "private_launch_authorized",
                    "attempt_boundary_crossed": False,
                    "private_path_or_digest_printed": False,
                }
            )
            return 0
        if args.command == "run":
            result = b3e.run_full_tournament(
                **_frozen_kwargs(args),
                readiness_report_path=args.readiness,
                runs_dir=args.runs_dir,
                public_closeout_path=args.public_out,
                keep_worktrees=args.keep_worktrees,
            )
            _print(
                {
                    "status": "complete_public_aggregate_written",
                    "logical_record_count": result.logical_record_count,
                    "completed_group_count": 48,
                    "private_metrics_printed": False,
                }
            )
            return 0
        if args.command == "closeout-interrupted":
            report = b3e.closeout_interrupted_failure(
                private_root=args.private_root,
                runs_dir=args.runs_dir,
                public_closeout_path=args.public_out,
                worker_exit_code=args.worker_exit_code,
                worker_pid_identity_path=args.worker_pid_identity,
                explicit_worker_stopped_confirmation=args.confirm_worker_stopped,
            )
            _print(
                {
                    "status": report["status"],
                    "failure_aggregate_digest": report["failure_aggregate_digest"],
                    "private_metrics_printed": False,
                }
            )
            return 0
        if args.command == "audit-preboundary":
            _print(b3e.audit_preboundary_recovery(args.runs_dir))
            return 0
        if args.command == "check-public":
            errors = _check_public(args.path)
            _print({"passed": not errors, "errors": errors})
            return 0 if not errors else 1
    except Exception as exc:  # noqa: BLE001 - detail remains in private log only
        _print(
            {
                "status": "failed_closed",
                "error_class": type(exc).__name__,
                "private_detail_printed": False,
            }
        )
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
