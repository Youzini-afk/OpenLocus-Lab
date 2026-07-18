#!/usr/bin/env python3
"""Closed command surface for B4 qualification, freeze, launch, and closeout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(HERE))

import product_bakeoff_b2_corpus as b2c  # noqa: E402
import product_bakeoff_b4_control as b4c  # noqa: E402
import product_bakeoff_b4_execution_adapter as b4adapter  # noqa: E402
import product_bakeoff_b4_runtime_qualification as b4rq  # noqa: E402
import product_bakeoff_b4_source as b4src  # noqa: E402


def _print(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), sort_keys=True))


def _histories(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "b2": args.history_b2,
        "b21": args.history_b21,
        "b24": args.history_b24,
        "b25": args.history_b25,
        "b3": args.history_b3,
    }


def _add_histories(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--history-b2", type=Path, required=True)
    parser.add_argument("--history-b21", type=Path, required=True)
    parser.add_argument("--history-b24", type=Path, required=True)
    parser.add_argument("--history-b25", type=Path, required=True)
    parser.add_argument("--history-b3", type=Path, required=True)


def _add_runtime(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime-public", type=Path, required=True)
    parser.add_argument("--runtime-private", type=Path, required=True)
    parser.add_argument("--runtime-scratch", type=Path, required=True)
    parser.add_argument("--runtime-publication-checkpoint", required=True)
    parser.add_argument("--runtime-publication-ci-run-id", type=int, required=True)
    parser.add_argument(
        "--runtime-publication-ci-conclusion", choices=("success",), default="success"
    )
    parser.add_argument("--cli", type=Path, required=True)


def _add_frozen_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--candidate-catalog", type=Path, required=True)
    _add_histories(parser)
    parser.add_argument("--exclusion-registry", type=Path, required=True)
    _add_runtime(parser)


def _frozen_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "private_root": args.private_root,
        "candidate_catalog_path": args.candidate_catalog,
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
    qualify.add_argument("--source-ci-conclusion", choices=("success",), default="success")
    qualify.add_argument("--public-out", type=Path, required=True)
    qualify.add_argument("--private-out", type=Path, required=True)

    prepare = sub.add_parser("prepare-holdout")
    _add_frozen_inputs(prepare)
    prepare.add_argument("--authoring-cache-root", type=Path, action="append", default=[])

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
    authorize.add_argument("--readiness-ci-conclusion", choices=("success",), default="success")

    run = sub.add_parser("run")
    _add_frozen_inputs(run)
    run.add_argument("--readiness", type=Path, required=True)
    run.add_argument("--runs-dir", type=Path, required=True)
    run.add_argument("--public-out", type=Path, required=True)
    run.add_argument("--keep-worktrees", action="store_true")

    closeout = sub.add_parser("closeout-interrupted")
    closeout.add_argument("--private-root", type=Path, required=True)
    closeout.add_argument("--runs-dir", type=Path, required=True)
    closeout.add_argument("--public-out", type=Path, required=True)
    closeout.add_argument("--confirm-worker-stopped", action="store_true")

    reset = sub.add_parser("reset-preboundary")
    reset.add_argument("--private-root", type=Path, required=True)
    reset.add_argument("--runs-dir", type=Path, required=True)
    reset.add_argument("--public-out", type=Path, required=True)
    reset.add_argument("--confirm-worker-stopped", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("--private-root", type=Path, required=True)
    status.add_argument("--runs-dir", type=Path, required=True)
    status.add_argument("--public-out", type=Path, required=True)

    check = sub.add_parser("check-public")
    check.add_argument("path", type=Path)
    return parser.parse_args(argv)


def _module_tests(function_name: str) -> dict[str, Any]:
    modules = (b4src, b4rq, b4adapter, b4c)
    reports = {module.__name__: getattr(module, function_name)() for module in modules}
    return {"passed": all(row["passed"] for row in reports.values()), "reports": reports}


def _check_public(path: Path) -> list[str]:
    value = b2c.load_json(path)
    schema = value.get("schema_version") if isinstance(value, dict) else None
    if schema == b4rq.B4_RUNTIME_PUBLIC_SCHEMA:
        return b4rq.validate_public_report(value)
    if schema == b4c.B4_READINESS_SCHEMA:
        return b4c.validate_public_readiness(value)
    import product_bakeoff_b4_publication as publication

    if schema == publication.B4_RESULT_SCHEMA:
        return publication.validate_public_result(value)
    if schema == publication.B4_FAILURE_SCHEMA:
        return publication.validate_public_failure(value)
    return ["unknown B4 public artifact schema"]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command in {"self-test", "fault-test"}:
            report = _module_tests(
                "run_self_test" if args.command == "self-test" else "run_fault_test"
            )
            _print(report)
            return 0 if report["passed"] else 1
        if args.command == "qualify-runtime":
            public, private = b4rq.qualify_runtime(
                cli_path=args.cli,
                scratch_root=args.scratch,
                source_checkpoint=args.source_checkpoint,
                source_ci_run_id=args.source_ci_run_id,
                source_ci_conclusion=args.source_ci_conclusion,
            )
            b4rq.write_qualification_pair(
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
            report = b4c.prepare_holdout(
                **_frozen_kwargs(args),
                authoring_cache_roots=tuple(args.authoring_cache_root),
            )
            _print(report)
            return 0
        if args.command == "freeze-holdout":
            report = b4c.freeze_holdout(**_frozen_kwargs(args))
            _print(report)
            return 0
        if args.command == "build-readiness":
            report = b4c.build_public_readiness(
                **_frozen_kwargs(args), treatment_runs_dir=args.runs_dir
            )
            b4c.write_public_readiness(
                private_root=args.private_root,
                path=args.public_out,
                report=report,
            )
            _print(
                {
                    "status": "public_readiness_written",
                    "readiness_digest": report["readiness_digest"],
                    "treatment_output_count": 0,
                }
            )
            return 0
        if args.command == "authorize-launch":
            report = b4c.create_launch_authorization(
                private_root=args.private_root,
                readiness_report_path=args.readiness,
                readiness_checkpoint=args.readiness_checkpoint,
                readiness_ci_run_id=args.readiness_ci_run_id,
                readiness_ci_conclusion=args.readiness_ci_conclusion,
            )
            _print(report)
            return 0
        if args.command == "run":
            report = b4c.run_formal_replication(
                **_frozen_kwargs(args),
                readiness_report_path=args.readiness,
                runs_dir=args.runs_dir,
                public_closeout_path=args.public_out,
                keep_worktrees=args.keep_worktrees,
            )
            _print(report)
            return 0 if report["passed"] else 1
        if args.command == "closeout-interrupted":
            report = b4c.closeout_interrupted_failure(
                private_root=args.private_root,
                runs_dir=args.runs_dir,
                public_closeout_path=args.public_out,
                explicit_worker_stopped_confirmation=args.confirm_worker_stopped,
            )
            _print(report)
            return 1
        if args.command == "reset-preboundary":
            report = b4c.reset_preboundary_launch_state(
                private_root=args.private_root,
                runs_dir=args.runs_dir,
                public_closeout_path=args.public_out,
                explicit_worker_stopped_confirmation=args.confirm_worker_stopped,
            )
            _print(report)
            return 0
        if args.command == "status":
            _print(
                b4c.aggregate_status(
                    private_root=args.private_root,
                    runs_dir=args.runs_dir,
                    public_closeout_path=args.public_out,
                )
            )
            return 0
        if args.command == "check-public":
            errors = _check_public(args.path)
            _print({"passed": not errors, "errors": errors})
            return 0 if not errors else 1
    except Exception as exc:  # noqa: BLE001 - details remain in private log only
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
