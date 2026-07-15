#!/usr/bin/env python3
"""B2.4 qualified-machine runner envelope around the frozen B2.1 engine."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

import product_bakeoff_b1_adapters as b1a
from product_bakeoff_contract import (
    AdapterHooks,
    AdapterRequest,
    AdapterResult,
    validate_descriptor_hooks,
)
import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_adapters as b2a
import product_bakeoff_b2_runner as b2r
import product_bakeoff_b21_runner as b21r
import product_bakeoff_b23_runner_qualification as b23q
import product_bakeoff_b24_corpus as b24c
from product_bakeoff_b24_protocol import (
    B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
    B24_PARENT_B23_QUALIFICATION_DIGEST,
    B24_REQUEST_TIMEOUT_SECONDS,
    b24_source_bundle_digest,
    b24_spec_digest,
)


B24_RUNNER_VERSION = "product_bakeoff_b24_runner.v1"
B24_PRIVATE_RUNNER_ADMISSION_SCHEMA = (
    "product_bakeoff_b24_private_runner_admission.v1"
)
_FROZEN_MAKE_B2_REQUEST = b2r.make_b2_request
_FROZEN_ADAPTER_COMMAND_TIMEOUT = b1a._CLI_TIMEOUT
_FROZEN_B21_RECEIPT_VALIDATOR = b21r.validate_freeze_receipt
_FROZEN_B21_ADAPTERS = b21r.B2_ADAPTERS


class B24RunError(RuntimeError):
    """Fail-closed B2.4 launch/execution error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _make_b24_longrun_request(**kwargs: Any) -> Any:
    request = _FROZEN_MAKE_B2_REQUEST(**kwargs)
    run_spec = dataclasses.replace(
        request.run_spec,
        timeout_seconds=B24_REQUEST_TIMEOUT_SECONDS,
    ).validate()
    return dataclasses.replace(request, run_spec=run_spec).validate()


def _apply_child_command_timeout() -> None:
    b1a._CLI_TIMEOUT = B24_ADAPTER_COMMAND_TIMEOUT_SECONDS


def b24_prepare(request: AdapterRequest, isolated_root: Path) -> None:
    _apply_child_command_timeout()
    b1a._b1_prepare(request, isolated_root)


def b24_s0_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    _apply_child_command_timeout()
    return b2a.s0_query(request, isolated_root)


def b24_s1_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    _apply_child_command_timeout()
    return b2a.s1_query(request, isolated_root)


def b24_s2_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    _apply_child_command_timeout()
    return b2a.s2_query(request, isolated_root)


def b24_s3_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    _apply_child_command_timeout()
    return b2a.s3_query(request, isolated_root)


def b24_s4_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    _apply_child_command_timeout()
    return b2a.s4_query(request, isolated_root)


def b24_s5_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    _apply_child_command_timeout()
    return b2a.s5_query(request, isolated_root)


def b24_s0_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=b24_prepare, index=None, query=b24_s0_query).validate()


def b24_s1_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=b24_prepare, index=None, query=b24_s1_query).validate()


def b24_s2_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=b24_prepare, index=None, query=b24_s2_query).validate()


def b24_s3_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=b24_prepare, index=None, query=b24_s3_query).validate()


def b24_s4_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=b24_prepare, index=None, query=b24_s4_query).validate()


def b24_s5_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=b24_prepare, index=None, query=b24_s5_query).validate()


B24_ADAPTERS = tuple(
    (adapter_id, descriptor_factory, hook_factory)
    for (adapter_id, descriptor_factory, _), hook_factory in zip(
        b2a.B2_ADAPTERS,
        (
            b24_s0_hooks,
            b24_s1_hooks,
            b24_s2_hooks,
            b24_s3_hooks,
            b24_s4_hooks,
            b24_s5_hooks,
        ),
    )
)


def _spawn_timeout_probe(connection: Any) -> None:
    _apply_child_command_timeout()
    connection.send(b1a._CLI_TIMEOUT)
    connection.close()


@contextlib.contextmanager
def _longrun_runtime_override(
    receipt_validator: Callable[..., Mapping[str, Any]],
) -> Iterator[None]:
    if b2r.make_b2_request is not _FROZEN_MAKE_B2_REQUEST:
        raise B24RunError("B2 request factory is already overridden")
    if b1a._CLI_TIMEOUT != _FROZEN_ADAPTER_COMMAND_TIMEOUT:
        raise B24RunError("adapter command timeout was changed before B2.4 launch")
    if b21r.validate_freeze_receipt is not _FROZEN_B21_RECEIPT_VALIDATOR:
        raise B24RunError("B2.1 receipt validator is already overridden")
    if b21r.B2_ADAPTERS is not _FROZEN_B21_ADAPTERS:
        raise B24RunError("B2.1 adapter registry is already overridden")
    if not B24_ADAPTER_COMMAND_TIMEOUT_SECONDS < B24_REQUEST_TIMEOUT_SECONDS:
        raise B24RunError("B2.4 nested timeout contract is invalid")
    b2r.make_b2_request = _make_b24_longrun_request
    b1a._CLI_TIMEOUT = B24_ADAPTER_COMMAND_TIMEOUT_SECONDS
    b21r.validate_freeze_receipt = receipt_validator
    b21r.B2_ADAPTERS = B24_ADAPTERS
    try:
        yield
    finally:
        b21r.B2_ADAPTERS = _FROZEN_B21_ADAPTERS
        b21r.validate_freeze_receipt = _FROZEN_B21_RECEIPT_VALIDATOR
        b1a._CLI_TIMEOUT = _FROZEN_ADAPTER_COMMAND_TIMEOUT
        b2r.make_b2_request = _FROZEN_MAKE_B2_REQUEST


def qualification_private_receipt_digest(receipt: Mapping[str, Any]) -> str:
    payload = dict(receipt)
    payload.pop("private_receipt_digest", None)
    return _prefixed_digest("b23qpriv_", payload)


def validate_qualification_private_receipt(raw: Any) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "qualification_version",
        "b23_spec_digest",
        "b23_source_bundle_digest",
        "profile_before",
        "profile_after",
        "profile_recheck_error",
        "stable_profile_changes",
        "profile_failure_codes",
        "io",
        "stress",
        "public_qualification_digest",
        "private_receipt_digest",
    }
    if not isinstance(raw, dict) or set(raw) != expected_keys:
        raise B24RunError("private B2.3 qualification receipt has non-closed shape")
    if raw["schema_version"] != b23q.B23_PRIVATE_SCHEMA:
        raise B24RunError("private B2.3 qualification schema mismatch")
    if raw["qualification_version"] != b23q.B23_QUALIFICATION_VERSION:
        raise B24RunError("private B2.3 qualification version mismatch")
    if raw["b23_spec_digest"] != b23q.b23_spec_digest():
        raise B24RunError("private B2.3 qualification spec binding mismatch")
    if raw["b23_source_bundle_digest"] != b23q.b23_source_bundle_digest():
        raise B24RunError("private B2.3 qualification source binding mismatch")
    if raw["public_qualification_digest"] != B24_PARENT_B23_QUALIFICATION_DIGEST:
        raise B24RunError("private/public B2.3 qualification binding mismatch")
    if raw["private_receipt_digest"] != qualification_private_receipt_digest(raw):
        raise B24RunError("private B2.3 qualification receipt digest mismatch")
    if not isinstance(raw["profile_before"], dict) or not isinstance(
        raw["profile_after"], dict
    ):
        raise B24RunError("private B2.3 qualification profiles are missing")
    if raw["profile_recheck_error"] is not None:
        raise B24RunError("private B2.3 qualification profile recheck failed")
    if raw["stable_profile_changes"] != [] or raw["profile_failure_codes"] != []:
        raise B24RunError("private B2.3 qualification profile did not remain stable")
    return raw


def _admit_qualified_machine(
    *,
    qualification_private_receipt_path: Path,
    repo_root: Path,
    scratch_root: Path,
    cli_path: Path,
) -> dict[str, Any]:
    receipt = validate_qualification_private_receipt(
        b2c.load_json(qualification_private_receipt_path)
    )
    current = b23q.collect_runner_profile(
        repo_root=repo_root,
        scratch_root=scratch_root,
        cli_path=cli_path,
    )
    if b23q.validate_runner_profile(current):
        raise B24RunError("qualified runner profile admission failed")
    if b23q.stable_runner_profile_changes(receipt["profile_after"], current):
        raise B24RunError("current runner does not match the qualified machine profile")
    return {
        "schema_version": B24_PRIVATE_RUNNER_ADMISSION_SCHEMA,
        "runner_version": B24_RUNNER_VERSION,
        "qualification_private_receipt_digest": receipt["private_receipt_digest"],
        "public_qualification_digest": receipt["public_qualification_digest"],
        "stable_profile_match": True,
        "current_profile_gate_passed": True,
        "exact_profile_values_recorded_publicly": False,
        "admission_digest": "",
    }


def _write_private_runner_admission(path: Path, value: Mapping[str, Any]) -> None:
    payload = dict(value)
    payload["admission_digest"] = _prefixed_digest("b24admit_", payload)
    b2c.write_json(path, payload)


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
        raise B24RunError("current source checkpoint could not be verified")
    return head


def run_full_matrix(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    qualification_report_path: Path,
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
    }
    if forbidden & set(sys.modules):
        raise B24RunError("B2.4 RUN import boundary already contaminated")
    private_root = Path(private_root)
    runs_dir = Path(runs_dir)
    repo_root = Path(__file__).resolve().parents[1]
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    binding_path = private_root / "b24_private_holdout_binding.json"
    freeze_path = private_root / "b24_private_freeze_receipt.json"
    authorization_path = private_root / "b24_private_launch_authorization.json"
    freeze = b2c.load_json(freeze_path)
    binding = b2c.load_json(binding_path)
    authorization = b2c.load_json(authorization_path)
    readiness = b2c.load_json(readiness_report_path)
    if _git_head(repo_root) != authorization.get("readiness_checkpoint"):
        raise B24RunError("checkout is not the authorized readiness checkpoint")
    if b24_source_bundle_digest() != freeze.get("source_bundle_digest"):
        raise B24RunError("B2.4 source bundle drifted after freeze")
    repo_lock = b2c.load_json(repo_path)
    task_manifest = b2c.load_json(task_path)
    oracle_manifest = b2c.load_json(oracle_path)
    freeze_kwargs = {
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": oracle_manifest["oracle_manifest_digest"],
        "holdout_binding_digest_value": binding["holdout_binding_digest"],
        "repo_lock_path": repo_path,
        "task_manifest_path": task_path,
        "oracle_manifest_path": oracle_path,
        "holdout_binding_path": binding_path,
        "candidate_plan_path": candidate_plan_path,
        "historical_repo_lock_paths": historical_repo_lock_paths,
        "exclusion_registry_path": exclusion_registry_path,
        "qualification_report_path": qualification_report_path,
        "cli_path": cli_path,
    }
    b24c.validate_freeze_receipt(freeze, **freeze_kwargs)
    b24c.validate_launch_authorization(
        authorization,
        freeze_receipt=freeze,
        freeze_receipt_path=freeze_path,
        readiness_report=readiness,
        readiness_report_path=readiness_report_path,
        readiness_checkpoint=authorization["readiness_checkpoint"],
        readiness_ci_run_id=authorization["readiness_ci_run_id"],
        readiness_ci_conclusion=authorization["readiness_ci_conclusion"],
    )
    if runs_dir.exists() and any(runs_dir.iterdir()):
        raise B24RunError("B2.4 runs directory must be absent or empty")
    runs_dir.mkdir(parents=True, exist_ok=True)
    admission = _admit_qualified_machine(
        qualification_private_receipt_path=qualification_private_receipt_path,
        repo_root=repo_root,
        scratch_root=runs_dir,
        cli_path=cli_path,
    )
    _write_private_runner_admission(
        private_root / "b24_private_runner_admission.json",
        admission,
    )

    def receipt_validator(raw: Any, **_: Any) -> Mapping[str, Any]:
        if raw != freeze:
            raise B24RunError("B2.1 engine received a different B2.4 freeze receipt")
        return b24c.validate_freeze_receipt(raw, **freeze_kwargs)

    os.environ["OPENLOCUS_CLI"] = str(cli_path.resolve(strict=True))
    with _longrun_runtime_override(receipt_validator):
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

    def validator(raw: Any, **_: Any) -> Mapping[str, Any]:
        return raw

    before_make = b2r.make_b2_request
    before_timeout = b1a._CLI_TIMEOUT
    before_validator = b21r.validate_freeze_receipt
    before_adapters = b21r.B2_ADAPTERS
    with _longrun_runtime_override(validator):
        checks.append(("request_factory_overridden", b2r.make_b2_request is _make_b24_longrun_request))
        checks.append(("adapter_timeout_570", b1a._CLI_TIMEOUT == 570.0))
        checks.append(("receipt_validator_overridden", b21r.validate_freeze_receipt is validator))
        checks.append(("adapter_registry_overridden", b21r.B2_ADAPTERS is B24_ADAPTERS))
    checks.extend(
        [
            ("request_factory_restored", b2r.make_b2_request is before_make),
            ("adapter_timeout_restored", b1a._CLI_TIMEOUT == before_timeout),
            ("receipt_validator_restored", b21r.validate_freeze_receipt is before_validator),
            ("adapter_registry_restored", b21r.B2_ADAPTERS is before_adapters),
            ("nested_timeout", B24_ADAPTER_COMMAND_TIMEOUT_SECONDS < B24_REQUEST_TIMEOUT_SECONDS),
        ]
    )
    ctx = multiprocessing.get_context("spawn")
    receive, send = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_spawn_timeout_probe, args=(send,))
    process.start()
    send.close()
    spawned_timeout = receive.recv() if receive.poll(15) else None
    process.join(15)
    if process.is_alive():
        process.terminate()
        process.join(5)
    receive.close()
    checks.append(("spawned_child_timeout_570", process.exitcode == 0 and spawned_timeout == 570.0))
    checks.append(
        (
            "wrapped_adapter_contracts_valid",
            all(
                validate_descriptor_hooks(descriptor_factory(), hook_factory())
                for _, descriptor_factory, hook_factory in B24_ADAPTERS
            ),
        )
    )
    synthetic = {
        "schema_version": b23q.B23_PRIVATE_SCHEMA,
        "qualification_version": b23q.B23_QUALIFICATION_VERSION,
        "b23_spec_digest": b23q.b23_spec_digest(),
        "b23_source_bundle_digest": b23q.b23_source_bundle_digest(),
        "profile_before": {},
        "profile_after": {},
        "profile_recheck_error": None,
        "stable_profile_changes": [],
        "profile_failure_codes": [],
        "io": {},
        "stress": {},
        "public_qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
        "private_receipt_digest": "",
    }
    synthetic["private_receipt_digest"] = qualification_private_receipt_digest(synthetic)
    checks.append(("private_receipt_roundtrip", validate_qualification_private_receipt(synthetic) == synthetic))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    synthetic = {
        "schema_version": b23q.B23_PRIVATE_SCHEMA,
        "qualification_version": b23q.B23_QUALIFICATION_VERSION,
        "b23_spec_digest": b23q.b23_spec_digest(),
        "b23_source_bundle_digest": b23q.b23_source_bundle_digest(),
        "profile_before": {},
        "profile_after": {},
        "profile_recheck_error": None,
        "stable_profile_changes": [],
        "profile_failure_codes": [],
        "io": {},
        "stress": {},
        "public_qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
        "private_receipt_digest": "",
    }
    synthetic["private_receipt_digest"] = qualification_private_receipt_digest(synthetic)
    bad = dict(synthetic)
    bad["stable_profile_changes"] = ["cpu_quota_count"]
    try:
        validate_qualification_private_receipt(bad)
        changed_profile_rejected = False
    except B24RunError:
        changed_profile_rejected = True
    checks.append(("changed_private_profile_rejected", changed_profile_rejected))
    bad = dict(synthetic)
    bad["private_receipt_digest"] = "b23qpriv_" + "0" * 64
    try:
        validate_qualification_private_receipt(bad)
        bad_digest_rejected = False
    except B24RunError:
        bad_digest_rejected = True
    checks.append(("private_receipt_digest_rejected", bad_digest_rejected))
    original = b1a._CLI_TIMEOUT
    b1a._CLI_TIMEOUT = original + 1
    try:
        try:
            with _longrun_runtime_override(lambda raw, **_: raw):
                pass
            preoverride_rejected = False
        except B24RunError:
            preoverride_rejected = True
    finally:
        b1a._CLI_TIMEOUT = original
    checks.append(("preexisting_timeout_override_rejected", preoverride_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B24RunError",
    "B24_RUNNER_VERSION",
    "validate_qualification_private_receipt",
    "run_full_matrix",
    "run_self_test",
    "run_fault_test",
]
