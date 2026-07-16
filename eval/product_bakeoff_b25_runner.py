#!/usr/bin/env python3
"""B2.5 admitted-machine runner around the frozen B2.1 engine."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b21_runner as b21r
import product_bakeoff_b24_runner as b24r
import product_bakeoff_b25_corpus as b25c
import product_bakeoff_b25_query_gate as b25q
import product_bakeoff_b25_runtime_qualification as b25rq
from product_bakeoff_b25_protocol import b25_source_bundle_digest


B25_RUNNER_VERSION = "product_bakeoff_b25_runner.v1"
B25_PRIVATE_RUNNER_ADMISSION_SCHEMA = (
    "product_bakeoff_b25_private_runner_admission.v1"
)
B25_PRIVATE_LAUNCH_RELEASE_SCHEMA = (
    "product_bakeoff_b25_private_launch_release.v1"
)


class B25RunError(RuntimeError):
    """Fail-closed B2.5 launch/execution error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _git_head(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    head = completed.stdout.strip()
    if completed.returncode != 0 or len(head) != 40:
        raise B25RunError("current source checkpoint could not be verified")
    return head


def _write_private_runner_admission(path: Path, value: Mapping[str, Any]) -> None:
    payload = dict(value)
    payload["admission_digest"] = _prefixed_digest("b25admit_", payload)
    b2c.write_json(path, payload)


def _wait_for_launch_release(
    path: Path,
    *,
    readiness_checkpoint: str,
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    expected = {
        "schema_version": B25_PRIVATE_LAUNCH_RELEASE_SCHEMA,
        "release": True,
        "readiness_checkpoint": readiness_checkpoint,
        "tournament_attempt_number": 1,
    }
    deadline = time.monotonic() + timeout_seconds
    while True:
        if os.path.lexists(path):
            if path.is_symlink() or not path.is_file():
                raise B25RunError("private launch release is missing or unsafe")
            try:
                raw = b2c.load_json(path)
            except Exception as exc:  # noqa: BLE001 - type-only boundary
                raise B25RunError(
                    "private launch release is unreadable: " + type(exc).__name__
                ) from exc
            if raw != expected:
                raise B25RunError("private launch release has non-closed shape")
            return raw
        if time.monotonic() >= deadline:
            raise B25RunError("private launch release was not received")
        time.sleep(0.1)


def run_full_matrix(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_qualification_report_path: Path,
    runtime_qualification_private_receipt_path: Path,
    qualification_private_receipt_path: Path,
    readiness_report_path: Path,
    runs_dir: Path,
    cli_path: Path,
    keep_worktrees: bool = False,
) -> b21r.B21RunResult:
    forbidden = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
        "product_bakeoff_b21_scorer",
        "product_bakeoff_b24_scorer",
        "product_bakeoff_b25_scorer",
    }
    if forbidden & set(sys.modules):
        raise B25RunError("B2.5 RUN import boundary already contaminated")
    private_root = Path(private_root)
    runs_dir = Path(runs_dir)
    repo_root = Path(__file__).resolve().parents[1]
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    query_path = private_root / "b25_private_query_compatibility.json"
    binding_path = private_root / "b25_private_holdout_binding.json"
    freeze_path = private_root / "b25_private_freeze_receipt.json"
    authorization_path = private_root / "b25_private_launch_authorization.json"
    admission_path = private_root / "b25_private_runner_admission.json"
    launch_release_path = private_root / "b25_private_launch_release.json"
    admission_scratch = private_root / "b25_private_admission_scratch"
    freeze = b2c.load_json(freeze_path)
    binding = b2c.load_json(binding_path)
    authorization = b2c.load_json(authorization_path)
    readiness = b2c.load_json(readiness_report_path)
    query_report = b2c.load_json(query_path)
    runtime_public = b2c.load_json(runtime_qualification_report_path)
    runtime_private = b2c.load_json(runtime_qualification_private_receipt_path)
    if _git_head(repo_root) != authorization.get("readiness_checkpoint"):
        raise B25RunError("checkout is not the authorized readiness checkpoint")
    if b25_source_bundle_digest() != freeze.get("source_bundle_digest"):
        raise B25RunError("B2.5 source bundle drifted after freeze")
    repo_lock = b2c.load_json(repo_path)
    task_manifest = b2c.load_json(task_path)
    oracle_manifest = b2c.load_json(oracle_path)
    b25q.validate_report_binding(
        query_report,
        repo_lock_digest=repo_lock["repo_lock_digest"],
        task_manifest_digest=task_manifest["task_manifest_digest"],
        oracle_manifest_digest=oracle_manifest["oracle_manifest_digest"],
    )
    if query_report["query_gate_digest"] != binding.get("query_gate_digest"):
        raise B25RunError("B2.5 query compatibility binding drifted")
    if b2c.file_sha256(query_path) != binding.get("query_gate_file_sha256"):
        raise B25RunError("B2.5 query compatibility bytes drifted")
    if b25rq.validate_public_report(runtime_public) or b25rq.validate_private_receipt(
        runtime_private
    ):
        raise B25RunError("B2.5 runtime qualification drifted")
    if runtime_public["qualification_digest"] != binding.get(
        "runtime_qualification_digest"
    ):
        raise B25RunError("B2.5 public runtime qualification binding drifted")
    if runtime_private["private_receipt_digest"] != binding.get(
        "runtime_qualification_private_receipt_digest"
    ):
        raise B25RunError("B2.5 private runtime qualification binding drifted")
    freeze_kwargs = {
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": oracle_manifest["oracle_manifest_digest"],
        "holdout_binding_digest_value": binding["holdout_binding_digest"],
        "query_gate_digest_value": query_report["query_gate_digest"],
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_qualification_private_receipt_digest": runtime_private[
            "private_receipt_digest"
        ],
        "repo_lock_path": repo_path,
        "task_manifest_path": task_path,
        "oracle_manifest_path": oracle_path,
        "holdout_binding_path": binding_path,
        "query_report_path": query_path,
        "candidate_plan_path": candidate_plan_path,
        "historical_repo_lock_paths": historical_repo_lock_paths,
        "exclusion_registry_path": exclusion_registry_path,
        "runtime_qualification_report_path": runtime_qualification_report_path,
        "runtime_qualification_private_receipt_path": (
            runtime_qualification_private_receipt_path
        ),
        "cli_path": cli_path,
    }
    b25c.validate_freeze_receipt(freeze, **freeze_kwargs)
    b25c.validate_launch_authorization(
        authorization,
        freeze_receipt=freeze,
        freeze_receipt_path=freeze_path,
        readiness_report=readiness,
        readiness_report_path=readiness_report_path,
        readiness_checkpoint=authorization["readiness_checkpoint"],
        readiness_ci_run_id=authorization["readiness_ci_run_id"],
        readiness_ci_conclusion=authorization["readiness_ci_conclusion"],
    )
    for path, label in (
        (admission_path, "runner admission"),
        (launch_release_path, "launch release"),
        (admission_scratch, "admission scratch"),
    ):
        if os.path.lexists(path):
            raise B25RunError(f"B2.5 private {label} must be absent before launch")
    if os.path.lexists(runs_dir):
        unsafe_or_nonempty = (
            runs_dir.is_symlink()
            or not runs_dir.is_dir()
            or any(runs_dir.iterdir())
        )
        if unsafe_or_nonempty:
            raise B25RunError("B2.5 runs directory must be absent or empty")
    b25rq.validate_runtime_binding(
        public_report_path=runtime_qualification_report_path,
        private_receipt_path=runtime_qualification_private_receipt_path,
        cli_path=cli_path,
        qualification_private_receipt_path=qualification_private_receipt_path,
        scratch_root=admission_scratch,
    )
    try:
        admission_scratch.rmdir()
    except OSError as exc:
        raise B25RunError("B2.5 private admission scratch was not empty") from exc
    _write_private_runner_admission(
        admission_path,
        {
            "schema_version": B25_PRIVATE_RUNNER_ADMISSION_SCHEMA,
            "runner_version": B25_RUNNER_VERSION,
            "runtime_qualification_digest": runtime_public["qualification_digest"],
            "runtime_qualification_private_receipt_digest": runtime_private[
                "private_receipt_digest"
            ],
            "query_gate_digest": query_report["query_gate_digest"],
            "query_gate_bound_without_oracle_import": True,
            "stable_profile_match": True,
            "current_profile_gate_passed": True,
            "exact_profile_values_recorded_publicly": False,
            "admission_digest": "",
        },
    )
    _wait_for_launch_release(
        launch_release_path,
        readiness_checkpoint=authorization["readiness_checkpoint"],
    )
    runs_dir.mkdir(parents=True, exist_ok=True)

    def receipt_validator(raw: Any, **_: Any) -> Mapping[str, Any]:
        if raw != freeze:
            raise B25RunError("B2.1 engine received a different B2.5 freeze receipt")
        return b25c.validate_freeze_receipt(raw, **freeze_kwargs)

    os.environ["OPENLOCUS_CLI"] = str(Path(cli_path).resolve(strict=True))
    with b24r._longrun_runtime_override(receipt_validator):
        result = b21r.run_full_matrix(
            repo_lock_path=repo_path,
            task_manifest_path=task_path,
            oracle_manifest_path=oracle_path,
            holdout_binding_path=binding_path,
            excluded_repo_lock_path=historical_repo_lock_paths["b2"],
            preflight_exclusion_path=exclusion_registry_path,
            freeze_receipt_path=freeze_path,
            expected_freeze_digest=freeze["freeze_receipt_digest"],
            runs_dir=runs_dir,
            keep_worktrees=keep_worktrees,
        )
    return result


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    forbidden = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
        "product_bakeoff_b21_scorer",
        "product_bakeoff_b24_scorer",
        "product_bakeoff_b25_scorer",
    }
    checks.append(("run_import_boundary_clean", not (forbidden & set(sys.modules))))

    def validator(raw: Any, **_: Any) -> Mapping[str, Any]:
        return raw

    before_validator = b21r.validate_freeze_receipt
    before_adapters = b21r.B2_ADAPTERS
    with b24r._longrun_runtime_override(validator):
        checks.append(("receipt_validator_overridden", b21r.validate_freeze_receipt is validator))
        checks.append(("adapter_registry_longrun", b21r.B2_ADAPTERS is b24r.B24_ADAPTERS))
    checks.append(("receipt_validator_restored", b21r.validate_freeze_receipt is before_validator))
    checks.append(("adapter_registry_restored", b21r.B2_ADAPTERS is before_adapters))
    with tempfile.TemporaryDirectory(prefix="openlocus-b25-release-") as temporary:
        release = Path(temporary) / "release.json"
        expected = {
            "schema_version": B25_PRIVATE_LAUNCH_RELEASE_SCHEMA,
            "release": True,
            "readiness_checkpoint": "a" * 40,
            "tournament_attempt_number": 1,
        }
        b2c.write_json(release, expected)
        checks.append(
            (
                "launch_release_roundtrip",
                _wait_for_launch_release(
                    release, readiness_checkpoint="a" * 40, timeout_seconds=0.0
                )
                == expected,
            )
        )
    checks.append(("runner_schema_b25", B25_PRIVATE_RUNNER_ADMISSION_SCHEMA.startswith("product_bakeoff_b25_")))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="openlocus-b25-release-fault-") as temporary:
        release = Path(temporary) / "release.json"
        b2c.write_json(
            release,
            {
                "schema_version": B25_PRIVATE_LAUNCH_RELEASE_SCHEMA,
                "release": False,
                "readiness_checkpoint": "a" * 40,
                "tournament_attempt_number": 1,
            },
        )
        try:
            _wait_for_launch_release(
                release, readiness_checkpoint="a" * 40, timeout_seconds=0.0
            )
            malformed_rejected = False
        except B25RunError:
            malformed_rejected = True
        checks.append(("malformed_release_rejected", malformed_rejected))
    with tempfile.TemporaryDirectory(prefix="openlocus-b25-release-missing-") as temporary:
        try:
            _wait_for_launch_release(
                Path(temporary) / "missing.json",
                readiness_checkpoint="a" * 40,
                timeout_seconds=0.0,
            )
            missing_rejected = False
        except B25RunError:
            missing_rejected = True
        checks.append(("missing_release_rejected", missing_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B25RunError",
    "B25_RUNNER_VERSION",
    "B25_PRIVATE_RUNNER_ADMISSION_SCHEMA",
    "B25_PRIVATE_LAUNCH_RELEASE_SCHEMA",
    "run_full_matrix",
    "run_self_test",
    "run_fault_test",
]
