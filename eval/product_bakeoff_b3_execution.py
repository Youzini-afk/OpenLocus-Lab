#!/usr/bin/env python3
"""B3 launch admission, first-observation boundary, execution, and closeout."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import importlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterator, Mapping

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b21_runner as b21r
import product_bakeoff_b3_corpus as b3c
import product_bakeoff_b3_readiness as b3ready
import product_bakeoff_b3_runner as b3runner
import product_bakeoff_b3_source as b3src


REPO = Path(__file__).resolve().parents[1]
B3_EXECUTION_VERSION = "product_bakeoff_b3_execution.v1"
B3_RUNNER_ADMISSION_SCHEMA = "product_bakeoff_b3_private_runner_admission.v1"
B3_LAUNCH_RELEASE_SCHEMA = "product_bakeoff_b3_private_launch_release.v1"
B3_ATTEMPT_BOUNDARY_SCHEMA = "product_bakeoff_b3_private_attempt_boundary.v1"
B3_TERMINAL_STATE_SCHEMA = "product_bakeoff_b3_private_terminal_state.v1"

_FROZEN_APPEND_NORMAL = b21r._append_normal
_FROZEN_APPEND_TERMINAL = b21r._append_terminal


class B3ExecutionError(RuntimeError):
    """Fail-closed B3 execution error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Mapping[str, Any], key: str) -> str:
    payload = dict(value)
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _atomic_private_write(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B3ExecutionError(f"private B3 receipt already exists: {path.name}")
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        if os.path.lexists(target):
            raise B3ExecutionError("private B3 receipt appeared concurrently")
        os.replace(temporary, target)
        if os.name != "nt":
            directory_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def _fsync_persisted_observation(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise B3ExecutionError("persisted treatment observation is missing or unsafe")
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
    if os.name != "nt":
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


def _observation_inventory(runs_dir: Path) -> dict[str, int]:
    private = Path(runs_dir) / "private"
    counts = {"normal_entries": 0, "terminal_entries": 0, "regular_json": 0}
    for key, name in (("normal_entries", "cells"), ("terminal_entries", "terminal_support")):
        root = private / name
        if not os.path.lexists(root):
            continue
        if root.is_symlink() or not root.is_dir():
            counts[key] += 1
            continue
        for entry in root.iterdir():
            counts[key] += 1
            if entry.is_file() and not entry.is_symlink() and entry.suffix == ".json":
                counts["regular_json"] += 1
    counts["durable_entries"] = counts["normal_entries"] + counts["terminal_entries"]
    return counts


def _boundary_path(runs_dir: Path) -> Path:
    return Path(runs_dir) / "private" / "b3_private_attempt_boundary.json"


def _build_boundary_receipt(
    *,
    freeze_receipt_digest: str,
    launch_authorization_digest: str,
    observation_kind: str,
    durable_entry_count: int,
    recovered_after_receipt_gap: bool,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": B3_ATTEMPT_BOUNDARY_SCHEMA,
        "execution_version": B3_EXECUTION_VERSION,
        "attempt_boundary": "first_durable_treatment_observation",
        "attempt_boundary_crossed": True,
        "tournament_attempt_number": 1,
        "launch_release_alone_consumes_attempt": False,
        "freeze_receipt_digest": freeze_receipt_digest,
        "launch_authorization_digest": launch_authorization_digest,
        "observation_kind": observation_kind,
        "durable_entry_count_at_receipt": durable_entry_count,
        "recovered_after_receipt_gap": recovered_after_receipt_gap,
        "restart_resume_retry_or_recomputation_authorized": False,
        "attempt_boundary_receipt_digest": "",
    }
    receipt["attempt_boundary_receipt_digest"] = _digest(
        "b3attempt_", receipt, "attempt_boundary_receipt_digest"
    )
    return receipt


def validate_boundary_receipt(
    receipt: Any,
    *,
    freeze_receipt_digest: str | None = None,
    launch_authorization_digest: str | None = None,
) -> dict[str, Any]:
    if not isinstance(receipt, dict) or set(receipt) != {
        "schema_version",
        "execution_version",
        "attempt_boundary",
        "attempt_boundary_crossed",
        "tournament_attempt_number",
        "launch_release_alone_consumes_attempt",
        "freeze_receipt_digest",
        "launch_authorization_digest",
        "observation_kind",
        "durable_entry_count_at_receipt",
        "recovered_after_receipt_gap",
        "restart_resume_retry_or_recomputation_authorized",
        "attempt_boundary_receipt_digest",
    }:
        raise B3ExecutionError("B3 attempt boundary receipt has non-closed shape")
    exact = {
        "schema_version": B3_ATTEMPT_BOUNDARY_SCHEMA,
        "execution_version": B3_EXECUTION_VERSION,
        "attempt_boundary": "first_durable_treatment_observation",
        "attempt_boundary_crossed": True,
        "tournament_attempt_number": 1,
        "launch_release_alone_consumes_attempt": False,
        "restart_resume_retry_or_recomputation_authorized": False,
    }
    if any(receipt.get(key) != value for key, value in exact.items()):
        raise B3ExecutionError("B3 attempt boundary receipt policy drifted")
    if receipt.get("observation_kind") not in {
        "normal",
        "terminal_support",
        "reconciled_existing_private_observation",
    }:
        raise B3ExecutionError("B3 attempt boundary observation kind drifted")
    count = receipt.get("durable_entry_count_at_receipt")
    if not isinstance(count, int) or count < 1:
        raise B3ExecutionError("B3 attempt boundary durable entry count malformed")
    if not isinstance(receipt.get("recovered_after_receipt_gap"), bool):
        raise B3ExecutionError("B3 attempt boundary recovery flag malformed")
    if freeze_receipt_digest is not None and receipt.get(
        "freeze_receipt_digest"
    ) != freeze_receipt_digest:
        raise B3ExecutionError("B3 attempt boundary freeze binding drifted")
    if launch_authorization_digest is not None and receipt.get(
        "launch_authorization_digest"
    ) != launch_authorization_digest:
        raise B3ExecutionError("B3 attempt boundary launch binding drifted")
    if receipt.get("attempt_boundary_receipt_digest") != _digest(
        "b3attempt_", receipt, "attempt_boundary_receipt_digest"
    ):
        raise B3ExecutionError("B3 attempt boundary receipt digest mismatch")
    return receipt


def _record_boundary(
    *,
    runs_dir: Path,
    freeze_receipt_digest: str,
    launch_authorization_digest: str,
    observation_kind: str,
    recovered: bool,
) -> dict[str, Any]:
    path = _boundary_path(runs_dir)
    inventory = _observation_inventory(runs_dir)
    if inventory["durable_entries"] < 1:
        raise B3ExecutionError("attempt boundary cannot precede durable observation")
    if os.path.lexists(path):
        return validate_boundary_receipt(
            b2c.load_json(path),
            freeze_receipt_digest=freeze_receipt_digest,
            launch_authorization_digest=launch_authorization_digest,
        )
    receipt = _build_boundary_receipt(
        freeze_receipt_digest=freeze_receipt_digest,
        launch_authorization_digest=launch_authorization_digest,
        observation_kind=observation_kind,
        durable_entry_count=inventory["durable_entries"],
        recovered_after_receipt_gap=recovered,
    )
    _atomic_private_write(path, receipt)
    return receipt


def reconcile_attempt_boundary(
    *,
    runs_dir: Path,
    freeze_receipt_digest: str,
    launch_authorization_digest: str,
    write_recovery_receipt: bool,
) -> dict[str, Any]:
    inventory = _observation_inventory(runs_dir)
    path = _boundary_path(runs_dir)
    receipt: dict[str, Any] | None = None
    if os.path.lexists(path):
        if path.is_symlink() or not path.is_file():
            raise B3ExecutionError("B3 attempt boundary receipt is unsafe")
        receipt = validate_boundary_receipt(
            b2c.load_json(path),
            freeze_receipt_digest=freeze_receipt_digest,
            launch_authorization_digest=launch_authorization_digest,
        )
        if inventory["durable_entries"] < 1:
            raise B3ExecutionError("attempt receipt exists without durable observation")
    elif inventory["durable_entries"] > 0 and write_recovery_receipt:
        receipt = _record_boundary(
            runs_dir=runs_dir,
            freeze_receipt_digest=freeze_receipt_digest,
            launch_authorization_digest=launch_authorization_digest,
            observation_kind="reconciled_existing_private_observation",
            recovered=True,
        )
    return {
        **inventory,
        "attempt_boundary_crossed": receipt is not None
        or inventory["durable_entries"] > 0,
        "receipt_present": receipt is not None,
        "recovery_receipt_written": bool(
            receipt and receipt.get("recovered_after_receipt_gap")
        ),
    }


@contextlib.contextmanager
def attempt_boundary_observer(
    *,
    runs_dir: Path,
    freeze_receipt_digest: str,
    launch_authorization_digest: str,
) -> Iterator[None]:
    if b21r._append_normal is not _FROZEN_APPEND_NORMAL:
        raise B3ExecutionError("normal append hook was already overridden")
    if b21r._append_terminal is not _FROZEN_APPEND_TERMINAL:
        raise B3ExecutionError("terminal append hook was already overridden")

    def append_normal(result: Any, cell: Any, descriptor: Any, private_root: Path) -> None:
        _FROZEN_APPEND_NORMAL(result, cell, descriptor, private_root)
        persisted = (
            Path(private_root)
            / "cells"
            / f"{cell.request.adapter_id}__{cell.request.run_spec.request_id}.json"
        )
        _fsync_persisted_observation(persisted)
        _record_boundary(
            runs_dir=runs_dir,
            freeze_receipt_digest=freeze_receipt_digest,
            launch_authorization_digest=launch_authorization_digest,
            observation_kind="normal",
            recovered=False,
        )

    def append_terminal(result: Any, cell: Any, private_root: Path) -> None:
        _FROZEN_APPEND_TERMINAL(result, cell, private_root)
        persisted = (
            Path(private_root)
            / "terminal_support"
            / f"{cell.adapter_id}__{cell.run_cell_id}__r{cell.adapter_repetition}.json"
        )
        _fsync_persisted_observation(persisted)
        _record_boundary(
            runs_dir=runs_dir,
            freeze_receipt_digest=freeze_receipt_digest,
            launch_authorization_digest=launch_authorization_digest,
            observation_kind="terminal_support",
            recovered=False,
        )

    b21r._append_normal = append_normal
    b21r._append_terminal = append_terminal
    try:
        yield
    finally:
        b21r._append_terminal = _FROZEN_APPEND_TERMINAL
        b21r._append_normal = _FROZEN_APPEND_NORMAL


def _write_admission(path: Path, value: Mapping[str, Any]) -> None:
    receipt = dict(value)
    receipt["admission_digest"] = _digest("b3admit_", receipt, "admission_digest")
    _atomic_private_write(path, receipt)


def _wait_for_launch_release(
    path: Path,
    *,
    readiness_checkpoint: str,
    launch_authorization_digest: str,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    expected = {
        "schema_version": B3_LAUNCH_RELEASE_SCHEMA,
        "readiness_checkpoint": readiness_checkpoint,
        "launch_authorization_digest": launch_authorization_digest,
        "tournament_attempt_number": 1,
        "release": True,
        "launch_release_alone_consumes_attempt": False,
    }
    deadline = time.monotonic() + timeout_seconds
    while True:
        if os.path.lexists(path):
            if path.is_symlink() or not path.is_file():
                raise B3ExecutionError("B3 private launch release is unsafe")
            raw = b2c.load_json(path)
            if raw != expected:
                raise B3ExecutionError("B3 private launch release has non-closed shape")
            return raw
        if time.monotonic() >= deadline:
            raise B3ExecutionError("B3 private launch release was not received")
        time.sleep(0.1)


def _terminal_state_path(private_root: Path) -> Path:
    return Path(private_root) / "b3_private_terminal_state.json"


def _write_terminal_state(
    *,
    private_root: Path,
    state: str,
    boundary_crossed: bool,
    logical_record_count: int,
) -> None:
    path = _terminal_state_path(private_root)
    if os.path.lexists(path):
        return
    value: dict[str, Any] = {
        "schema_version": B3_TERMINAL_STATE_SCHEMA,
        "execution_version": B3_EXECUTION_VERSION,
        "state": state,
        "attempt_boundary_crossed": boundary_crossed,
        "logical_record_count": logical_record_count,
        "retry_authorized": False if boundary_crossed else None,
        "private_detail_public": False,
        "terminal_state_digest": "",
    }
    value["terminal_state_digest"] = _digest(
        "b3terminal_", value, "terminal_state_digest"
    )
    _atomic_private_write(path, value)


def _write_private_score(path: Path, arm_results: Any, decision: Mapping[str, Any]) -> None:
    payload: dict[str, Any] = {
        "schema_version": "product_bakeoff_b3_private_complete_score.v1",
        "arm_results": [dataclasses.asdict(row) for row in arm_results],
        "decision": dict(decision),
        "public": False,
        "private_score_digest": "",
    }
    payload["private_score_digest"] = _digest(
        "b3score_", payload, "private_score_digest"
    )
    _atomic_private_write(path, payload)


def audit_preboundary_recovery(runs_dir: Path) -> dict[str, Any]:
    inventory = _observation_inventory(runs_dir)
    receipt_exists = os.path.lexists(_boundary_path(runs_dir))
    return {
        "eligible_for_explicit_preboundary_recovery": inventory["durable_entries"] == 0
        and not receipt_exists,
        "attempt_boundary_crossed": inventory["durable_entries"] > 0 or receipt_exists,
        "durable_treatment_entry_count": inventory["durable_entries"],
        "automatic_deletion_performed": False,
        "new_runtime_qualification_and_readiness_required_if_runner_replaced": True,
    }


def _validate_public_closeout_target(path: Path) -> None:
    path = Path(path)
    if path.suffix != ".json":
        raise B3ExecutionError("B3 public closeout target must be JSON")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    try:
        parent.relative_to(REPO.resolve(strict=True))
    except ValueError as exc:
        raise B3ExecutionError("B3 public closeout target must stay in checkout") from exc
    target = parent / path.name
    if os.path.lexists(target):
        raise B3ExecutionError("B3 public closeout path must be new")
    descriptor, probe_raw = tempfile.mkstemp(
        prefix=".b3-public-closeout-probe.", suffix=".tmp", dir=parent
    )
    probe = Path(probe_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(b"{}\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if probe.exists():
            probe.unlink()


def _validate_private_run_paths(private_root: Path, runs_dir: Path) -> None:
    repo = REPO.resolve(strict=True)
    for path, label in ((Path(private_root), "private root"), (Path(runs_dir), "runs dir")):
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(repo)
        except ValueError:
            pass
        else:
            raise B3ExecutionError(f"B3 {label} must remain outside checkout")
        if os.path.lexists(path) and path.is_symlink():
            raise B3ExecutionError(f"B3 {label} must not be a symlink")


def run_full_tournament(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    runtime_scratch: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    readiness_report_path: Path,
    runs_dir: Path,
    public_closeout_path: Path,
    cli_path: Path,
    keep_worktrees: bool = False,
) -> Any:
    forbidden = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
        "product_bakeoff_b21_scorer",
        "product_bakeoff_b24_scorer",
        "product_bakeoff_b25_scorer",
        "product_bakeoff_b3_scorer",
        "product_bakeoff_b3_publication",
    }
    if forbidden & set(sys.modules):
        raise B3ExecutionError("B3 RUN process import boundary is contaminated")
    private_root = Path(private_root)
    runs_dir = Path(runs_dir)
    public_closeout_path = Path(public_closeout_path)
    _validate_private_run_paths(private_root, runs_dir)
    state = b3c.validate_run_admission_state(
        private_root=private_root,
        candidate_plan_path=candidate_plan_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        runtime_scratch=runtime_scratch,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        cli_path=cli_path,
    )
    paths = state["paths"]
    freeze = state["freeze"]
    readiness_report_path = Path(readiness_report_path)
    if readiness_report_path.is_symlink() or not readiness_report_path.is_file():
        raise B3ExecutionError("B3 readiness report is missing or unsafe")
    readiness = b2c.load_json(readiness_report_path)
    if b3ready.validate_public_readiness(readiness):
        raise B3ExecutionError("B3 readiness report is invalid at RUN admission")
    if paths["authorization"].is_symlink() or not paths["authorization"].is_file():
        raise B3ExecutionError("B3 private launch authorization is missing or unsafe")
    authorization = b2c.load_json(paths["authorization"])
    b3c.validate_launch_authorization(
        authorization,
        freeze_receipt=freeze,
        freeze_receipt_path=paths["freeze"],
        readiness_report=readiness,
        readiness_report_path=readiness_report_path,
        readiness_checkpoint=authorization["readiness_checkpoint"],
        readiness_ci_run_id=authorization["readiness_ci_run_id"],
        readiness_ci_conclusion=authorization["readiness_ci_conclusion"],
    )
    if b3src.control_source_bundle_digest() != freeze["control_source_bundle_digest"]:
        raise B3ExecutionError("B3 control source drifted at RUN admission")
    admission_path = private_root / "b3_private_runner_admission.json"
    release_path = private_root / "b3_private_launch_release.json"
    for path, label in ((admission_path, "runner admission"), (release_path, "launch release")):
        if os.path.lexists(path):
            raise B3ExecutionError(f"B3 private {label} must be absent before launch")
    boundary_state = reconcile_attempt_boundary(
        runs_dir=runs_dir,
        freeze_receipt_digest=freeze["freeze_receipt_digest"],
        launch_authorization_digest=authorization["launch_authorization_digest"],
        write_recovery_receipt=True,
    )
    if boundary_state["attempt_boundary_crossed"]:
        raise B3ExecutionError("B3 durable-observation attempt was already consumed")
    if os.path.lexists(runs_dir) and (
        runs_dir.is_symlink() or not runs_dir.is_dir() or any(runs_dir.iterdir())
    ):
        raise B3ExecutionError("B3 zero-observation working state requires explicit recovery")
    _validate_public_closeout_target(public_closeout_path)
    _write_admission(
        admission_path,
        {
            "schema_version": B3_RUNNER_ADMISSION_SCHEMA,
            "execution_version": B3_EXECUTION_VERSION,
            "control_source_bundle_digest": b3src.control_source_bundle_digest(),
            "runtime_qualification_digest": state["runtime_public"][
                "qualification_digest"
            ],
            "freeze_receipt_digest": freeze["freeze_receipt_digest"],
            "launch_authorization_digest": authorization[
                "launch_authorization_digest"
            ],
            "stable_profile_match": True,
            "current_profile_gate_passed": True,
            "zero_durable_treatment_observation_verified": True,
            "launch_release_consumes_attempt": False,
            "exact_profile_values_recorded_publicly": False,
            "admission_digest": "",
        },
    )
    launch_release = _wait_for_launch_release(
        release_path,
        readiness_checkpoint=authorization["readiness_checkpoint"],
        launch_authorization_digest=authorization["launch_authorization_digest"],
    )
    if b3c._git_head() != authorization["readiness_checkpoint"]:
        raise B3ExecutionError("checkout changed after B3 runner admission")
    if _observation_inventory(runs_dir)["durable_entries"] != 0:
        raise B3ExecutionError("treatment observation appeared before engine entry")
    os.environ["OPENLOCUS_CLI"] = str(Path(cli_path).resolve(strict=True))
    stage = "engine"
    try:
        def receipt_validator(raw: Any, **_: Any) -> Mapping[str, Any]:
            if raw != freeze:
                raise B3ExecutionError("B3 engine received a different freeze receipt")
            return b3c.validate_freeze_receipt(raw, **state["freeze_kwargs"])

        def revalidate_frozen_bytes() -> None:
            for path, label in (
                (paths["freeze"], "freeze receipt"),
                (paths["authorization"], "launch authorization"),
                (release_path, "launch release"),
            ):
                if path.is_symlink() or not path.is_file():
                    raise B3ExecutionError(f"B3 {label} became unsafe during execution")
            observed = b2c.load_json(paths["freeze"])
            if observed != freeze:
                raise B3ExecutionError("B3 freeze receipt changed during execution")
            b3c.validate_freeze_receipt(observed, **state["freeze_kwargs"])
            if b2c.load_json(paths["authorization"]) != authorization:
                raise B3ExecutionError("B3 launch authorization changed during execution")
            if b2c.load_json(release_path) != launch_release:
                raise B3ExecutionError("B3 launch release changed during execution")

        with attempt_boundary_observer(
            runs_dir=runs_dir,
            freeze_receipt_digest=freeze["freeze_receipt_digest"],
            launch_authorization_digest=authorization["launch_authorization_digest"],
        ):
            result = b3runner.run_full_matrix_engine(
                repo_lock_path=paths["repo"],
                task_manifest_path=paths["task"],
                oracle_manifest_path=paths["oracle"],
                holdout_binding_path=paths["binding"],
                excluded_repo_lock_path=historical_repo_lock_paths["b2"],
                preflight_exclusion_path=exclusion_registry_path,
                freeze_receipt_path=paths["freeze"],
                expected_freeze_digest=freeze["freeze_receipt_digest"],
                runs_dir=runs_dir,
                receipt_validator=receipt_validator,
                keep_worktrees=keep_worktrees,
            )
        boundary_state = reconcile_attempt_boundary(
            runs_dir=runs_dir,
            freeze_receipt_digest=freeze["freeze_receipt_digest"],
            launch_authorization_digest=authorization["launch_authorization_digest"],
            write_recovery_receipt=True,
        )
        if not boundary_state["attempt_boundary_crossed"]:
            raise B3ExecutionError("complete B3 engine returned without attempt boundary")
        stage = "pre_score"
        revalidate_frozen_bytes()
        if result.logical_record_count != 1440:
            raise B3ExecutionError("B3 engine returned an incomplete matrix")
        if result.gate_result is None or not result.gate_result.passed:
            raise B3ExecutionError("B3 pre-score gates failed")
        stage = "scoring"
        scorer = importlib.import_module("product_bakeoff_b3_scorer")
        arm_results, decision = scorer.score_b3(
            result=result, oracle_manifest_path=paths["oracle"]
        )
        _write_private_score(
            runs_dir / "private" / "b3_private_complete_score.json",
            arm_results,
            decision,
        )
        revalidate_frozen_bytes()
        publication = importlib.import_module("product_bakeoff_b3_publication")
        public = publication.build_public_result(
            result=result,
            arm_results=arm_results,
            decision=decision,
            readiness_report=readiness,
            readiness_report_path=readiness_report_path,
            launch_authorization=authorization,
        )
        publication.write_public(public_closeout_path, public)
        try:
            _write_terminal_state(
                private_root=private_root,
                state="complete_success_public_aggregate_written",
                boundary_crossed=True,
                logical_record_count=1440,
            )
        except B3ExecutionError:
            # The aggregate result is already durably written and validated.
            # A secondary private status receipt must not turn success into a
            # contradictory nonzero worker exit.
            pass
        return result
    except Exception:
        reconciled = reconcile_attempt_boundary(
            runs_dir=runs_dir,
            freeze_receipt_digest=freeze["freeze_receipt_digest"],
            launch_authorization_digest=authorization["launch_authorization_digest"],
            write_recovery_receipt=True,
        )
        if reconciled["attempt_boundary_crossed"]:
            logical = reconciled["regular_json"]
            _write_terminal_state(
                private_root=private_root,
                state="failed_after_attempt_boundary_no_retry",
                boundary_crossed=True,
                logical_record_count=logical,
            )
            if not os.path.lexists(public_closeout_path):
                publication = importlib.import_module("product_bakeoff_b3_publication")
                failure_class = {
                    "engine": "matrix_execution_failed",
                    "pre_score": "pre_score_gate_failed",
                    "scoring": "scoring_or_publication_failed",
                }[stage]
                failure = publication.build_public_failure(
                    failure_class=failure_class,
                    completed_group_count=min(48, logical // 30),
                    logical_record_count=min(1440, logical),
                    durable_treatment_artifact_count=reconciled["durable_entries"],
                )
                publication.write_public(public_closeout_path, failure)
        else:
            _write_terminal_state(
                private_root=private_root,
                state="preboundary_failure_zero_observation_recovery_audit_required",
                boundary_crossed=False,
                logical_record_count=0,
            )
        raise


def closeout_interrupted_failure(
    *,
    private_root: Path,
    runs_dir: Path,
    public_closeout_path: Path,
    worker_exit_code: int,
    worker_pid_identity_path: Path,
    explicit_worker_stopped_confirmation: bool,
) -> dict[str, Any]:
    _validate_public_closeout_target(public_closeout_path)
    _validate_private_run_paths(private_root, runs_dir)
    identity_state = _worker_identity_state(worker_pid_identity_path)
    if identity_state == "alive":
        raise B3ExecutionError("cannot close B3 while the admitted worker is alive")
    if identity_state in {"absent", "invalid"} and not explicit_worker_stopped_confirmation:
        raise B3ExecutionError("B3 worker stop requires explicit confirmation")
    freeze = b2c.load_json(Path(private_root) / "b3_private_freeze_receipt.json")
    authorization = b2c.load_json(
        Path(private_root) / "b3_private_launch_authorization.json"
    )
    state = reconcile_attempt_boundary(
        runs_dir=runs_dir,
        freeze_receipt_digest=freeze["freeze_receipt_digest"],
        launch_authorization_digest=authorization["launch_authorization_digest"],
        write_recovery_receipt=True,
    )
    if not state["attempt_boundary_crossed"]:
        raise B3ExecutionError("cannot publish B3 failure before attempt boundary")
    if os.path.lexists(public_closeout_path):
        raise B3ExecutionError("B3 public closeout already exists")
    logical = state["regular_json"]
    publication = importlib.import_module("product_bakeoff_b3_publication")
    failure = publication.build_public_failure(
        failure_class=(
            "worker_or_machine_terminated"
            if worker_exit_code != 0
            else "incomplete_matrix_after_worker_exit"
        ),
        completed_group_count=min(48, logical // 30),
        logical_record_count=min(1440, logical),
        durable_treatment_artifact_count=state["durable_entries"],
    )
    publication.write_public(public_closeout_path, failure)
    return failure


def _worker_identity_state(path: Path) -> str:
    path = Path(path)
    if not os.path.lexists(path):
        return "absent"
    if path.is_symlink() or not path.is_file():
        return "invalid"
    try:
        value = b2c.load_json(path)
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "pid",
            "boot_id",
            "process_start_ticks",
        }:
            return "invalid"
        if value["schema_version"] != (
            "product_bakeoff_b3_private_worker_pid_identity.v1"
        ):
            return "invalid"
        pid = int(value["pid"])
        start = int(value["process_start_ticks"])
        boot = Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii"
        ).strip()
        if boot != value["boot_id"]:
            return "not_alive"
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        fields = stat.rsplit(")", 1)[1].strip().split()
        return "alive" if int(fields[19]) == start else "not_alive"
    except (OSError, ValueError, IndexError, KeyError, b2c.B2CorpusError):
        return "invalid"


def run_self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="openlocus-b3-boundary-") as temporary:
        runs = Path(temporary) / "runs"
        cell = runs / "private" / "cells" / "s0__ctx.json"
        cell.parent.mkdir(parents=True)
        cell.write_text("{}\n", encoding="utf-8")
        before = reconcile_attempt_boundary(
            runs_dir=runs,
            freeze_receipt_digest="b3freeze_test",
            launch_authorization_digest="b3launch_test",
            write_recovery_receipt=False,
        )
        after = reconcile_attempt_boundary(
            runs_dir=runs,
            freeze_receipt_digest="b3freeze_test",
            launch_authorization_digest="b3launch_test",
            write_recovery_receipt=True,
        )
        receipt = b2c.load_json(_boundary_path(runs))
        validate_boundary_receipt(
            receipt,
            freeze_receipt_digest="b3freeze_test",
            launch_authorization_digest="b3launch_test",
        )
    original = (b21r._append_normal, b21r._append_terminal)
    with attempt_boundary_observer(
        runs_dir=Path(temporary) / "unused",
        freeze_receipt_digest="b3freeze_test",
        launch_authorization_digest="b3launch_test",
    ):
        patched = b21r._append_normal is not original[0] and b21r._append_terminal is not original[1]
    restored = (b21r._append_normal, b21r._append_terminal) == original
    checks = {
        "durable_observation_without_receipt_crosses_boundary": before[
            "attempt_boundary_crossed"
        ],
        "receipt_gap_reconciled": after["recovery_receipt_written"],
        "launch_release_not_required_for_boundary_reconciliation": True,
        "append_hooks_scoped": patched,
        "append_hooks_restored": restored,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="openlocus-b3-boundary-fault-") as temporary:
        runs = Path(temporary) / "runs"
        empty = reconcile_attempt_boundary(
            runs_dir=runs,
            freeze_receipt_digest="b3freeze_test",
            launch_authorization_digest="b3launch_test",
            write_recovery_receipt=True,
        )
        checks["release_or_empty_state_does_not_cross_boundary"] = not empty[
            "attempt_boundary_crossed"
        ]
        receipt_path = _boundary_path(runs)
        receipt_path.parent.mkdir(parents=True)
        receipt = _build_boundary_receipt(
            freeze_receipt_digest="b3freeze_test",
            launch_authorization_digest="b3launch_test",
            observation_kind="normal",
            durable_entry_count=1,
            recovered_after_receipt_gap=False,
        )
        b2c.write_json(receipt_path, receipt)
        try:
            reconcile_attempt_boundary(
                runs_dir=runs,
                freeze_receipt_digest="b3freeze_test",
                launch_authorization_digest="b3launch_test",
                write_recovery_receipt=False,
            )
            checks["receipt_without_observation_rejected"] = False
        except B3ExecutionError:
            checks["receipt_without_observation_rejected"] = True
        drift = dict(receipt)
        drift["launch_release_alone_consumes_attempt"] = True
        try:
            validate_boundary_receipt(drift)
            checks["release_as_boundary_rejected"] = False
        except B3ExecutionError:
            checks["release_as_boundary_rejected"] = True
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B3ExecutionError",
    "attempt_boundary_observer",
    "audit_preboundary_recovery",
    "closeout_interrupted_failure",
    "reconcile_attempt_boundary",
    "run_full_tournament",
    "validate_boundary_receipt",
]
