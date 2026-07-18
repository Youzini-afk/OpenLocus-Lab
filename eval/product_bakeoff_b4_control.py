#!/usr/bin/env python3
"""Offline B4 corpus, freeze, readiness, launch, and execution control.

This module deliberately imports no author, oracle, or scorer at module load.
Authoring and scoring are phase-local lazy imports, while every raw panel runs
in a fresh child process through ``product_bakeoff_b4_execution_adapter``.
"""

from __future__ import annotations

import contextlib
import copy
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_corpus as b2c  # noqa: E402
import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b25_query_gate as b25q  # noqa: E402
import product_bakeoff_b3_corpus as b3c  # noqa: E402
import product_bakeoff_b4_execution_adapter as b4adapter  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402
import product_bakeoff_b4_runtime_qualification as b4rq  # noqa: E402
import product_bakeoff_b4_source as b4src  # noqa: E402
from product_bakeoff_b24_protocol import (  # noqa: E402
    B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
    B24_REQUEST_TIMEOUT_SECONDS,
)


REPO = Path(__file__).resolve().parents[1]
B4_CONTROL_VERSION = "product_bakeoff_b4_control.v1"
B4_CANDIDATE_CATALOG_SCHEMA = "product_bakeoff_b4_private_candidate_catalog.v1"
B4_EXCLUSION_REGISTRY_SCHEMA = "product_bakeoff_b4_private_exclusions.v1"
B4_AUTHOR_STATE_SCHEMA = "product_bakeoff_b4_private_author_state.v1"
B4_PANEL_BINDING_SCHEMA = "product_bakeoff_b4_private_panel_binding.v1"
B4_GLOBAL_BINDING_SCHEMA = "product_bakeoff_b4_private_holdout_binding.v1"
B4_HISTORY_BINDING_SCHEMA = "product_bakeoff_b4_private_history_binding.v1"
B4_PANEL_FREEZE_SCHEMA = "product_bakeoff_b4_private_panel_freeze.v1"
B4_GLOBAL_FREEZE_SCHEMA = "product_bakeoff_b4_private_holdout_freeze.v1"
B4_READINESS_SCHEMA = "product_bakeoff_b4_holdout_readiness.v1"
B4_READINESS_BINDING_SCHEMA = "product_bakeoff_b4_private_readiness_binding.v1"
B4_READINESS_STATUS = (
    "product_bakeoff_b4_twelve_panel_holdout_frozen_runtime_qualified_"
    "zero_treatment_output_launch_not_yet_authorized"
)
B4_LAUNCH_AUTHORIZATION_SCHEMA = "product_bakeoff_b4_private_launch_authorization.v1"
B4_LAUNCH_RELEASE_SCHEMA = "product_bakeoff_b4_private_launch_release.v1"
B4_RUNNER_ADMISSION_SCHEMA = "product_bakeoff_b4_private_runner_admission.v1"
B4_ATTEMPT_BOUNDARY_SCHEMA = "product_bakeoff_b4_private_attempt_boundary.v1"
B4_TERMINAL_STATE_SCHEMA = "product_bakeoff_b4_private_terminal_state.v1"
B4_PROTOCOL_DIGEST = (
    "b4protocol_cf983176938c83c415b44bfb50b64baa866bebac9e1567e85a119f5073683cc1"
)
B4_HISTORY_LABELS = ("b2", "b21", "b24", "b25", "b3")
B4_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "private_holdout_or_freeze_digest_public": False,
    "repository_candidate_task_query_or_oracle_identity_public": False,
    "source_location_range_excerpt_or_raw_output_public": False,
    "per_panel_per_repository_or_per_task_empirical_detail_public": False,
    "private_runner_identity_endpoint_or_working_location_public": False,
    "intermediate_quality_resource_or_rank_metric_public": False,
    "provider_payload_secret_or_credential_public": False,
}


class B4ControlError(RuntimeError):
    """Fail-closed B4 control error; caller logs only the exception class."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Mapping[str, Any], key: str) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _normalized_file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _exact_int(value: Any) -> bool:
    return type(value) is int


def _git_head(repo_root: Path = REPO) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise B4ControlError("current git checkpoint is unavailable")
    return value


def _repo_relative(path: Path) -> str:
    resolved = Path(path).resolve(strict=True)
    try:
        relative = resolved.relative_to(REPO.resolve(strict=True))
    except ValueError as exc:
        raise B4ControlError("public artifact is outside the checkout") from exc
    return relative.as_posix()


def validate_publication_gate(
    *,
    artifact_path: Path,
    checkpoint: str,
    ci_run_id: int,
    ci_conclusion: str,
    require_current_head: bool,
) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", checkpoint):
        raise B4ControlError("publication checkpoint must be a full commit SHA")
    if not _exact_int(ci_run_id) or ci_run_id <= 0 or ci_conclusion != "success":
        raise B4ControlError("publication CI gate is not green")
    if require_current_head and _git_head() != checkpoint:
        raise B4ControlError("checkout is not the required publication checkpoint")
    path = Path(artifact_path)
    if path.is_symlink() or not path.is_file():
        raise B4ControlError("publication artifact is missing or unsafe")
    relative = _repo_relative(path)
    blob = subprocess.run(
        ["git", "show", f"{checkpoint}:{relative}"],
        cwd=REPO,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if blob.returncode != 0 or blob.stdout != path.read_bytes():
        raise B4ControlError("publication artifact is not exact at checkpoint")


def _safe_private_root(path: Path) -> Path:
    target = Path(path).resolve(strict=False)
    try:
        target.relative_to(REPO.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise B4ControlError("B4 private root must stay outside checkout")
    if os.path.lexists(target) and (target.is_symlink() or not target.is_dir()):
        raise B4ControlError("B4 private root is unsafe")
    target.mkdir(parents=True, exist_ok=True)
    return target.resolve(strict=True)


def _paths_overlap(left: Path, right: Path) -> bool:
    left = Path(left).resolve(strict=False)
    right = Path(right).resolve(strict=False)
    return left == right or left in right.parents or right in left.parents


def _write_json_exclusive(path: Path, value: Mapping[str, Any], *, mode: int = 0o600) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B4ControlError("B4 private output already exists")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        if os.path.lexists(target):
            raise B4ControlError("B4 private output appeared concurrently")
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


def _write_json_replace(path: Path, value: Mapping[str, Any], *, mode: int = 0o600) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target) and (target.is_symlink() or not target.is_file()):
        raise B4ControlError("B4 replace target is unsafe")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
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


def _write_json_exclusive_or_equal(
    path: Path, value: Mapping[str, Any], *, mode: int = 0o600
) -> Path:
    target = Path(path)
    if target.is_file() and not target.is_symlink():
        if b2c.load_json(target) != dict(value):
            raise B4ControlError("B4 resumable output drifted")
        return target
    if os.path.lexists(target):
        raise B4ControlError("B4 resumable output path is unsafe")
    return _write_json_exclusive(target, value, mode=mode)


def _write_public_exclusive(path: Path, value: Mapping[str, Any]) -> Path:
    target = Path(path).resolve(strict=False)
    try:
        target.relative_to(REPO.resolve(strict=True))
    except ValueError as exc:
        raise B4ControlError("B4 public output must stay inside checkout") from exc
    return _write_json_exclusive(target, value, mode=0o644)


def _repo_slug(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise B4ControlError("repository token is invalid")
    token = value.strip().removesuffix(".git")
    for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
        if token.startswith(prefix):
            token = token[len(prefix) :]
            break
    token = token.strip("/").casefold()
    if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", token):
        raise B4ControlError("repository token is not a closed owner/name slug")
    return token


def validate_exclusion_registry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "repositories",
        "synthetic_sources",
    }:
        raise B4ControlError("B4 exclusion registry has non-closed shape")
    if raw["schema_version"] != B4_EXCLUSION_REGISTRY_SCHEMA:
        raise B4ControlError("B4 exclusion registry schema drifted")
    repositories = raw["repositories"]
    synthetic = raw["synthetic_sources"]
    if not isinstance(repositories, list) or not isinstance(synthetic, list):
        raise B4ControlError("B4 exclusion registry rows must be lists")
    slugs: list[str] = []
    for row in repositories:
        if not isinstance(row, dict) or set(row) != {"repo", "reason"}:
            raise B4ControlError("B4 repository exclusion row has non-closed shape")
        slugs.append(_repo_slug(row["repo"]))
        if not isinstance(row["reason"], str) or not row["reason"].strip():
            raise B4ControlError("B4 repository exclusion reason is missing")
    if len(slugs) != len(set(slugs)):
        raise B4ControlError("B4 exclusion repository repeats")
    if any(not isinstance(value, str) or not value for value in synthetic):
        raise B4ControlError("B4 synthetic exclusion token is invalid")
    if len(synthetic) != len(set(synthetic)):
        raise B4ControlError("B4 synthetic exclusion token repeats")
    return raw


def exclusion_slugs(registry: Mapping[str, Any]) -> set[str]:
    validated = validate_exclusion_registry(dict(registry))
    return {_repo_slug(row["repo"]) for row in validated["repositories"]}


def historical_repository_sets(
    historical_repo_locks: Mapping[str, Mapping[str, Any]],
) -> tuple[set[str], set[tuple[str, str]], dict[str, str]]:
    if set(historical_repo_locks) != set(B4_HISTORY_LABELS):
        raise B4ControlError("B4 historical lock labels are incomplete")
    slugs: set[str] = set()
    identities: set[tuple[str, str]] = set()
    digests: dict[str, str] = {}
    for label in B4_HISTORY_LABELS:
        lock = b2c.validate_repo_lock(dict(historical_repo_locks[label]), require_sources=False)
        frame_slugs = {_repo_slug(row["source"]["repo"]) for row in lock["repos"]}
        frame_identities = {
            (_repo_slug(row["source"]["repo"]), row["commit"])
            for row in lock["repos"]
        }
        if len(frame_slugs) != 12 or len(frame_identities) != 12:
            raise B4ControlError("B4 historical frame cardinality drifted")
        if slugs & frame_slugs or identities & frame_identities:
            raise B4ControlError("B4 historical frames overlap")
        slugs.update(frame_slugs)
        identities.update(frame_identities)
        digests[label] = lock["repo_lock_digest"]
    if len(slugs) != 60 or len(identities) != 60:
        raise B4ControlError("B4 historical union is not 60 distinct repositories")
    return slugs, identities, digests


def validate_candidate_catalog(
    raw: Any,
    *,
    historical_slugs: set[str],
    excluded_slugs: set[str],
) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "slots"}:
        raise B4ControlError("B4 candidate catalog has non-closed shape")
    if raw["schema_version"] != B4_CANDIDATE_CATALOG_SCHEMA:
        raise B4ControlError("B4 candidate catalog schema drifted")
    slots = raw["slots"]
    if not isinstance(slots, list) or len(slots) != 12:
        raise B4ControlError("B4 candidate catalog must contain twelve slots")
    expected_slots = {slot.repo_slot for slot in b2p.build_task_slots()}
    seen_slots: set[str] = set()
    all_candidates: list[str] = []
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"repo_slot", "candidates"}:
            raise B4ControlError("B4 candidate catalog slot has non-closed shape")
        repo_slot = slot["repo_slot"]
        if repo_slot not in expected_slots or repo_slot in seen_slots:
            raise B4ControlError("B4 candidate catalog slot is unknown or duplicated")
        seen_slots.add(repo_slot)
        candidates = slot["candidates"]
        if not isinstance(candidates, list) or len(candidates) < b4p.B4_PANEL_COUNT:
            raise B4ControlError("B4 candidate catalog lacks one candidate per panel")
        for candidate in candidates:
            if not isinstance(candidate, dict) or set(candidate) != {
                "repo",
                "expected_license",
            }:
                raise B4ControlError("B4 candidate row has non-closed shape")
            slug = _repo_slug(candidate["repo"])
            if slug in historical_slugs or slug in excluded_slugs:
                raise B4ControlError("B4 candidate catalog overlaps an excluded frame")
            if not isinstance(candidate["expected_license"], str) or not candidate[
                "expected_license"
            ].strip():
                raise B4ControlError("B4 candidate expected license is missing")
            all_candidates.append(slug)
    if seen_slots != expected_slots:
        raise B4ControlError("B4 candidate catalog slot coverage is incomplete")
    if len(all_candidates) != len(set(all_candidates)):
        raise B4ControlError("B4 candidate catalog repeats a repository")
    return raw


def _catalog_by_slot(catalog: Mapping[str, Any]) -> dict[str, list[dict[str, str]]]:
    return {row["repo_slot"]: list(row["candidates"]) for row in catalog["slots"]}


def _initial_author_state(
    *, catalog_path: Path, history_paths: Mapping[str, Path], exclusion_path: Path
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "schema_version": B4_AUTHOR_STATE_SCHEMA,
        "catalog_file_sha256": _file_sha256(catalog_path),
        "history_file_sha256": {
            label: _file_sha256(history_paths[label]) for label in B4_HISTORY_LABELS
        },
        "exclusion_file_sha256": _file_sha256(exclusion_path),
        "next_candidate_index_by_slot": {
            slot.repo_slot: 0 for slot in b2p.build_task_slots()[::4]
        },
        "completed_panels": [],
        "selected_repository_count": 0,
        "author_state_digest": "",
    }
    state["author_state_digest"] = _digest("b4authorstate_", state, "author_state_digest")
    return state


def validate_author_state(
    state: Any,
    *,
    catalog_path: Path,
    history_paths: Mapping[str, Path],
    exclusion_path: Path,
) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise B4ControlError("B4 author state must be an object")
    expected_keys = set(_initial_author_state(
        catalog_path=catalog_path,
        history_paths=history_paths,
        exclusion_path=exclusion_path,
    ))
    if set(state) != expected_keys or state["schema_version"] != B4_AUTHOR_STATE_SCHEMA:
        raise B4ControlError("B4 author state shape drifted")
    if state["catalog_file_sha256"] != _file_sha256(catalog_path):
        raise B4ControlError("B4 author state catalog binding drifted")
    if state["history_file_sha256"] != {
        label: _file_sha256(history_paths[label]) for label in B4_HISTORY_LABELS
    }:
        raise B4ControlError("B4 author state history binding drifted")
    if state["exclusion_file_sha256"] != _file_sha256(exclusion_path):
        raise B4ControlError("B4 author state exclusion binding drifted")
    cursors = state["next_candidate_index_by_slot"]
    expected_slots = {slot.repo_slot for slot in b2p.build_task_slots()[::4]}
    if not isinstance(cursors, dict) or set(cursors) != expected_slots:
        raise B4ControlError("B4 author state cursor set drifted")
    if any(not _exact_int(value) or value < 0 for value in cursors.values()):
        raise B4ControlError("B4 author state cursor invalid")
    completed = state["completed_panels"]
    if not isinstance(completed, list) or completed != list(range(1, len(completed) + 1)):
        raise B4ControlError("B4 author state completed panels are not a prefix")
    if state["selected_repository_count"] != 12 * len(completed):
        raise B4ControlError("B4 author state repository count drifted")
    if state["author_state_digest"] != _digest(
        "b4authorstate_", state, "author_state_digest"
    ):
        raise B4ControlError("B4 author state digest mismatch")
    return state


def build_panel_candidate_plan(
    catalog: Mapping[str, Any], cursors: Mapping[str, int]
) -> dict[str, Any]:
    by_slot = _catalog_by_slot(catalog)
    slots: list[dict[str, Any]] = []
    for repo_slot in sorted(by_slot):
        cursor = cursors[repo_slot]
        remaining = by_slot[repo_slot][cursor:]
        if not remaining:
            raise B4ControlError("B4 candidate catalog was depleted before treatment")
        slots.append({"repo_slot": repo_slot, "candidates": remaining})
    return {
        "schema_version": "product_bakeoff_b2_private_candidate_plan.v1",
        "slots": slots,
    }


def _selected_by_slot(repo_lock: Mapping[str, Any]) -> dict[str, str]:
    validated = b2c.validate_repo_lock(dict(repo_lock), require_sources=True)
    selected = {
        row["repo_slot"]: _repo_slug(row["source"]["repo"])
        for row in validated["repos"]
    }
    if len(selected) != 12:
        raise B4ControlError("B4 selected panel is not twelve repositories")
    return selected


def _advance_cursors(
    *,
    catalog: Mapping[str, Any],
    cursors: Mapping[str, int],
    selected_by_slot: Mapping[str, str],
) -> dict[str, int]:
    by_slot = _catalog_by_slot(catalog)
    advanced: dict[str, int] = {}
    for repo_slot, cursor in cursors.items():
        candidates = [_repo_slug(row["repo"]) for row in by_slot[repo_slot]]
        selected = selected_by_slot[repo_slot]
        try:
            index = candidates.index(selected, cursor)
        except ValueError as exc:
            raise B4ControlError("B4 selected repository is absent from remaining catalog") from exc
        advanced[repo_slot] = index + 1
    return advanced


def _panel_root(private_root: Path, panel_index: int) -> Path:
    return Path(private_root) / "panels" / f"panel_{panel_index:02d}"


def _panel_paths(private_root: Path, panel_index: int) -> dict[str, Path]:
    root = _panel_root(private_root, panel_index)
    return {
        "root": root,
        "plan": root / "b4_private_panel_candidate_plan.json",
        "repo": root / "b2_private_repo_lock.json",
        "task": root / "b2_private_task_manifest.json",
        "oracle": root / "b2_private_oracle_manifest.json",
        "query": root / "b4_private_query_compatibility.json",
        "binding": root / "b4_private_panel_binding.json",
        "freeze": root / "b4_private_panel_freeze.json",
    }


def _cleanup_unselected_clones(panel_root: Path, repo_lock: Mapping[str, Any]) -> int:
    clone_root = Path(panel_root) / "clones"
    if not clone_root.exists():
        return 0
    if clone_root.is_symlink() or not clone_root.is_dir():
        raise B4ControlError("B4 panel clone root is unsafe")
    selected = {
        Path(row["source"]["clone_root"]).resolve(strict=True)
        for row in repo_lock["repos"]
    }
    removed = 0
    resolved_root = clone_root.resolve(strict=True)
    for child in clone_root.iterdir():
        resolved = child.resolve(strict=True)
        resolved.relative_to(resolved_root)
        if resolved in selected:
            continue
        if child.is_symlink() or not child.is_dir():
            raise B4ControlError("B4 candidate clone entry is unsafe")
        shutil.rmtree(resolved)
        removed += 1
    return removed


def panel_binding_digest(binding: Mapping[str, Any]) -> str:
    return _digest("b4panelbind_", binding, "holdout_binding_digest")


def build_panel_binding(
    *,
    panel_index: int,
    repo_lock: Mapping[str, Any],
    task_manifest: Mapping[str, Any],
    oracle_manifest: Mapping[str, Any],
    query_report: Mapping[str, Any],
    paths: Mapping[str, Path],
    catalog_path: Path,
    history_paths: Mapping[str, Path],
    exclusion_path: Path,
    runtime_public: Mapping[str, Any],
    runtime_private: Mapping[str, Any],
    runtime_public_path: Path,
    runtime_private_path: Path,
) -> dict[str, Any]:
    lock = b2c.validate_repo_lock(dict(repo_lock), require_sources=True)
    tasks = b2c.validate_task_manifest(
        dict(task_manifest), repo_lock_digest=lock["repo_lock_digest"]
    )
    expected_query_report = b25q.build_query_compatibility_report(
        repo_lock=lock,
        task_manifest=dict(task_manifest),
        oracle_manifest=dict(oracle_manifest),
    )
    if dict(query_report) != expected_query_report:
        raise B4ControlError("B4 panel query gate does not bind the frozen manifests")
    binding: dict[str, Any] = {
        "schema_version": B4_PANEL_BINDING_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "protocol_digest": B4_PROTOCOL_DIGEST,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "panel_index": panel_index,
        "panel_schedule_digest": b4adapter.panel_schedule_digest(panel_index),
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_private_receipt_digest": runtime_private["private_receipt_digest"],
        "runtime_bundle_digest": runtime_private["runtime_bundle_digest"],
        "runtime_public_file_sha256": _file_sha256(runtime_public_path),
        "runtime_private_file_sha256": _file_sha256(runtime_private_path),
        "candidate_catalog_file_sha256": _file_sha256(catalog_path),
        "panel_candidate_plan_file_sha256": _file_sha256(paths["plan"]),
        "history_file_sha256": {
            label: _file_sha256(history_paths[label]) for label in B4_HISTORY_LABELS
        },
        "exclusion_file_sha256": _file_sha256(exclusion_path),
        "repo_lock_digest": lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": oracle_manifest["oracle_manifest_digest"],
        "query_gate_digest": query_report["query_gate_digest"],
        "repo_lock_file_sha256": _file_sha256(paths["repo"]),
        "task_manifest_file_sha256": _file_sha256(paths["task"]),
        "oracle_manifest_file_sha256": _file_sha256(paths["oracle"]),
        "query_gate_file_sha256": _file_sha256(paths["query"]),
        "repository_count": len(lock["repos"]),
        "task_count": len(tasks),
        "selected_repository_identity_count": len(
            {
                (_repo_slug(row["source"]["repo"]), row["commit"])
                for row in lock["repos"]
            }
        ),
        "treatment_output_exists": False,
        "holdout_binding_digest": "",
    }
    binding["holdout_binding_digest"] = panel_binding_digest(binding)
    return binding


def _build_history_binding(
    *, history_paths: Mapping[str, Path], historical_locks: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    _, _, digests = historical_repository_sets(historical_locks)
    value: dict[str, Any] = {
        "schema_version": B4_HISTORY_BINDING_SCHEMA,
        "history_labels": list(B4_HISTORY_LABELS),
        "history_repo_lock_digests": digests,
        "history_file_sha256": {
            label: _file_sha256(history_paths[label]) for label in B4_HISTORY_LABELS
        },
        "historical_repository_count": 60,
        "history_binding_digest": "",
    }
    value["history_binding_digest"] = _digest(
        "b4history_", value, "history_binding_digest"
    )
    return value


def _load_runtime_for_authoring(
    *,
    runtime_public_path: Path,
    runtime_private_path: Path,
    runtime_scratch: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    cli_path: Path,
    require_current_head: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_publication_gate(
        artifact_path=runtime_public_path,
        checkpoint=runtime_publication_checkpoint,
        ci_run_id=runtime_publication_ci_run_id,
        ci_conclusion=runtime_publication_ci_conclusion,
        require_current_head=require_current_head,
    )
    public, private = b4rq.validate_runtime_binding(
        public_report_path=runtime_public_path,
        private_receipt_path=runtime_private_path,
        cli_path=cli_path,
        scratch_root=runtime_scratch,
    )
    try:
        Path(runtime_scratch).rmdir()
    except OSError as exc:
        raise B4ControlError("B4 runtime validation scratch was not empty") from exc
    return public, private


def prepare_holdout(
    *,
    private_root: Path,
    candidate_catalog_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    runtime_scratch: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    cli_path: Path,
    authoring_cache_roots: Sequence[Path] = (),
) -> dict[str, Any]:
    private_root = _safe_private_root(private_root)
    if _paths_overlap(private_root, runtime_scratch):
        raise B4ControlError("B4 private root overlaps runtime scratch")
    if set(historical_repo_lock_paths) != set(B4_HISTORY_LABELS):
        raise B4ControlError("B4 historical lock paths are incomplete")
    for path in (
        candidate_catalog_path,
        exclusion_registry_path,
        runtime_public_path,
        runtime_private_path,
        cli_path,
        *historical_repo_lock_paths.values(),
    ):
        if Path(path).is_symlink() or not Path(path).is_file():
            raise B4ControlError("B4 authoring input is missing or unsafe")
    runtime_public, runtime_private = _load_runtime_for_authoring(
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        runtime_scratch=runtime_scratch,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        cli_path=cli_path,
        require_current_head=True,
    )
    histories = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in B4_HISTORY_LABELS
    }
    historical_slugs, historical_identities, _ = historical_repository_sets(histories)
    exclusion = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    excluded = exclusion_slugs(exclusion)
    catalog = validate_candidate_catalog(
        b2c.load_json(candidate_catalog_path),
        historical_slugs=historical_slugs,
        excluded_slugs=excluded,
    )
    state_path = private_root / "b4_private_author_state.json"
    if state_path.is_file() and not state_path.is_symlink():
        state = validate_author_state(
            b2c.load_json(state_path),
            catalog_path=candidate_catalog_path,
            history_paths=historical_repo_lock_paths,
            exclusion_path=exclusion_registry_path,
        )
    elif os.path.lexists(state_path):
        raise B4ControlError("B4 author state path is unsafe")
    else:
        state = _initial_author_state(
            catalog_path=candidate_catalog_path,
            history_paths=historical_repo_lock_paths,
            exclusion_path=exclusion_registry_path,
        )
        _write_json_exclusive(state_path, state)

    author = __import__("importlib").import_module("product_bakeoff_b2_author")
    cache_clone_roots = b3c._normalize_cache_clone_roots(
        authoring_cache_roots,
        private_root=private_root,
    )
    selected_slugs = set(historical_slugs) | set(excluded)
    selected_identities = set(historical_identities)
    replayed_cursors = {
        slot.repo_slot: 0 for slot in b2p.build_task_slots()[::4]
    }
    for completed_panel in state["completed_panels"]:
        paths = _panel_paths(private_root, completed_panel)
        expected_plan = build_panel_candidate_plan(catalog, replayed_cursors)
        if b2c.load_json(paths["plan"]) != expected_plan:
            raise B4ControlError("B4 completed panel candidate plan drifted")
        lock = b2c.validate_repo_lock(
            b2c.load_json(paths["repo"]),
            require_sources=True,
        )
        task_manifest = b2c.load_json(paths["task"])
        oracle_manifest = b2c.load_json(paths["oracle"])
        query_report = b2c.load_json(paths["query"])
        binding = b2c.load_json(paths["binding"])
        expected_binding = build_panel_binding(
            panel_index=completed_panel,
            repo_lock=lock,
            task_manifest=task_manifest,
            oracle_manifest=oracle_manifest,
            query_report=query_report,
            paths=paths,
            catalog_path=candidate_catalog_path,
            history_paths=historical_repo_lock_paths,
            exclusion_path=exclusion_registry_path,
            runtime_public=runtime_public,
            runtime_private=runtime_private,
            runtime_public_path=runtime_public_path,
            runtime_private_path=runtime_private_path,
        )
        if binding != expected_binding:
            raise B4ControlError("B4 completed panel binding drifted")
        selected = _selected_by_slot(lock)
        replayed_cursors = _advance_cursors(
            catalog=catalog,
            cursors=replayed_cursors,
            selected_by_slot=selected,
        )
        panel_slugs = {
            _repo_slug(row["source"]["repo"]) for row in lock["repos"]
        }
        panel_identities = {
            (_repo_slug(row["source"]["repo"]), row["commit"])
            for row in lock["repos"]
        }
        if panel_slugs & selected_slugs or panel_identities & selected_identities:
            raise B4ControlError("B4 completed panels overlap a prior frame")
        selected_slugs.update(panel_slugs)
        selected_identities.update(panel_identities)
    if replayed_cursors != state["next_candidate_index_by_slot"]:
        raise B4ControlError("B4 author-state cursors do not replay from completed panels")

    resumed_checkpoints = 0
    removed_rejected_clones = 0
    for panel_index in range(len(state["completed_panels"]) + 1, b4p.B4_PANEL_COUNT + 1):
        paths = _panel_paths(private_root, panel_index)
        paths["root"].mkdir(parents=True, exist_ok=True)
        plan = build_panel_candidate_plan(
            catalog, state["next_candidate_index_by_slot"]
        )
        if paths["plan"].is_file() and not paths["plan"].is_symlink():
            if b2c.load_json(paths["plan"]) != plan:
                raise B4ControlError("B4 panel candidate plan drifted during resume")
        elif os.path.lexists(paths["plan"]):
            raise B4ControlError("B4 panel candidate plan path is unsafe")
        else:
            _write_json_exclusive(paths["plan"], plan)
        slots = author._validate_candidate_plan(plan)
        prepared = b3c._prepare_checkpointed_manifests(
            author=author,
            slots=slots,
            private_root=paths["root"],
            cache_clone_roots=cache_clone_roots,
        )
        resumed_checkpoints += prepared["resumed_checkpoint_count"]
        repo_lock = b2c.load_json(paths["repo"])
        task_manifest = b2c.load_json(paths["task"])
        oracle_manifest = b2c.load_json(paths["oracle"])
        query_report = b25q.build_query_compatibility_report(
            repo_lock=repo_lock,
            task_manifest=task_manifest,
            oracle_manifest=oracle_manifest,
        )
        if paths["query"].is_file() and not paths["query"].is_symlink():
            if b2c.load_json(paths["query"]) != query_report:
                raise B4ControlError("B4 panel query compatibility drifted")
        else:
            _write_json_exclusive(paths["query"], query_report)

        selected = _selected_by_slot(repo_lock)
        new_identities = {
            (_repo_slug(row["source"]["repo"]), row["commit"])
            for row in repo_lock["repos"]
        }
        if set(selected.values()) & selected_slugs or new_identities & selected_identities:
            raise B4ControlError("B4 panel overlaps a historical or completed panel")
        binding = build_panel_binding(
            panel_index=panel_index,
            repo_lock=repo_lock,
            task_manifest=task_manifest,
            oracle_manifest=oracle_manifest,
            query_report=query_report,
            paths=paths,
            catalog_path=candidate_catalog_path,
            history_paths=historical_repo_lock_paths,
            exclusion_path=exclusion_registry_path,
            runtime_public=runtime_public,
            runtime_private=runtime_private,
            runtime_public_path=runtime_public_path,
            runtime_private_path=runtime_private_path,
        )
        if paths["binding"].is_file() and not paths["binding"].is_symlink():
            if b2c.load_json(paths["binding"]) != binding:
                raise B4ControlError("B4 panel binding drifted during resume")
        else:
            _write_json_exclusive(paths["binding"], binding)
        removed_rejected_clones += _cleanup_unselected_clones(paths["root"], repo_lock)

        state = dict(state)
        state["next_candidate_index_by_slot"] = _advance_cursors(
            catalog=catalog,
            cursors=state["next_candidate_index_by_slot"],
            selected_by_slot=selected,
        )
        state["completed_panels"] = [*state["completed_panels"], panel_index]
        state["selected_repository_count"] = 12 * len(state["completed_panels"])
        state["author_state_digest"] = _digest(
            "b4authorstate_", state, "author_state_digest"
        )
        _write_json_replace(state_path, state)
        selected_slugs.update(selected.values())
        selected_identities.update(new_identities)

    return {
        "status": "private_b4_holdout_authored",
        "panel_count": len(state["completed_panels"]),
        "repository_count": state["selected_repository_count"],
        "logical_task_count": state["selected_repository_count"] * 4,
        "checkpoint_count": state["selected_repository_count"],
        "resumed_checkpoint_count": resumed_checkpoints,
        "removed_rejected_clone_count": removed_rejected_clones,
        "private_paths_or_digests_printed": False,
    }


def global_binding_digest(binding: Mapping[str, Any]) -> str:
    return _digest("b4holdout_", binding, "holdout_binding_digest")


def build_global_binding(
    *,
    private_root: Path,
    candidate_catalog_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public: Mapping[str, Any],
    runtime_private: Mapping[str, Any],
    runtime_public_path: Path,
    runtime_private_path: Path,
) -> dict[str, Any]:
    catalog = b2c.load_json(candidate_catalog_path)
    state = validate_author_state(
        b2c.load_json(Path(private_root) / "b4_private_author_state.json"),
        catalog_path=candidate_catalog_path,
        history_paths=historical_repo_lock_paths,
        exclusion_path=exclusion_registry_path,
    )
    if state["completed_panels"] != list(range(1, b4p.B4_PANEL_COUNT + 1)):
        raise B4ControlError("B4 global binding requires twelve completed panels")
    replayed_cursors = {
        slot.repo_slot: 0 for slot in b2p.build_task_slots()[::4]
    }
    panel_bindings: list[dict[str, Any]] = []
    slugs: set[str] = set()
    identities: set[tuple[str, str]] = set()
    total_visible_bytes = 0
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        paths = _panel_paths(private_root, panel_index)
        if b2c.load_json(paths["plan"]) != build_panel_candidate_plan(
            catalog, replayed_cursors
        ):
            raise B4ControlError("B4 panel candidate plan drifted before global binding")
        binding = b2c.load_json(paths["binding"])
        if not isinstance(binding, dict) or binding.get("schema_version") != B4_PANEL_BINDING_SCHEMA:
            raise B4ControlError("B4 panel binding is missing or malformed")
        if binding.get("panel_index") != panel_index:
            raise B4ControlError("B4 panel binding index drifted")
        if binding.get("holdout_binding_digest") != panel_binding_digest(binding):
            raise B4ControlError("B4 panel binding digest mismatch")
        if binding.get("control_source_bundle_digest") != b4src.control_source_bundle_digest():
            raise B4ControlError("B4 panel binding source drifted")
        if binding.get("runtime_bundle_digest") != runtime_private["runtime_bundle_digest"]:
            raise B4ControlError("B4 panel runtime binding drifted")
        lock = b2c.validate_repo_lock(b2c.load_json(paths["repo"]), require_sources=True)
        task_manifest = b2c.load_json(paths["task"])
        oracle_manifest = b2c.load_json(paths["oracle"])
        query_report = b2c.load_json(paths["query"])
        expected_panel_binding = build_panel_binding(
            panel_index=panel_index,
            repo_lock=lock,
            task_manifest=task_manifest,
            oracle_manifest=oracle_manifest,
            query_report=query_report,
            paths=paths,
            catalog_path=candidate_catalog_path,
            history_paths=historical_repo_lock_paths,
            exclusion_path=exclusion_registry_path,
            runtime_public=runtime_public,
            runtime_private=runtime_private,
            runtime_public_path=runtime_public_path,
            runtime_private_path=runtime_private_path,
        )
        if binding != expected_panel_binding:
            raise B4ControlError("B4 panel binding drifted from its frozen inputs")
        panel_slugs = {_repo_slug(row["source"]["repo"]) for row in lock["repos"]}
        panel_identities = {
            (_repo_slug(row["source"]["repo"]), row["commit"])
            for row in lock["repos"]
        }
        replayed_cursors = _advance_cursors(
            catalog=catalog,
            cursors=replayed_cursors,
            selected_by_slot=_selected_by_slot(lock),
        )
        if len(panel_slugs) != 12 or len(panel_identities) != 12:
            raise B4ControlError("B4 panel repository identities are incomplete")
        if slugs & panel_slugs or identities & panel_identities:
            raise B4ControlError("B4 panels overlap")
        slugs.update(panel_slugs)
        identities.update(panel_identities)
        total_visible_bytes += sum(row["visible"]["bytes"] for row in lock["repos"])
        panel_bindings.append(
            {
                "panel_index": panel_index,
                "panel_binding_digest": binding["holdout_binding_digest"],
                "panel_binding_file_sha256": _file_sha256(paths["binding"]),
                "repo_lock_file_sha256": _file_sha256(paths["repo"]),
                "task_manifest_file_sha256": _file_sha256(paths["task"]),
                "oracle_manifest_file_sha256": _file_sha256(paths["oracle"]),
                "query_gate_file_sha256": _file_sha256(paths["query"]),
            }
        )
    if replayed_cursors != state["next_candidate_index_by_slot"]:
        raise B4ControlError("B4 global binding author cursors failed deterministic replay")
    if len(slugs) != b4p.B4_REPOSITORY_CLUSTER_COUNT or len(identities) != len(slugs):
        raise B4ControlError("B4 global repository identity cardinality drifted")
    binding: dict[str, Any] = {
        "schema_version": B4_GLOBAL_BINDING_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "protocol_digest": B4_PROTOCOL_DIGEST,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_private_receipt_digest": runtime_private["private_receipt_digest"],
        "runtime_bundle_digest": runtime_private["runtime_bundle_digest"],
        "runtime_public_file_sha256": _file_sha256(runtime_public_path),
        "runtime_private_file_sha256": _file_sha256(runtime_private_path),
        "candidate_catalog_file_sha256": _file_sha256(candidate_catalog_path),
        "history_file_sha256": {
            label: _file_sha256(historical_repo_lock_paths[label])
            for label in B4_HISTORY_LABELS
        },
        "exclusion_file_sha256": _file_sha256(exclusion_registry_path),
        "panel_bindings": panel_bindings,
        "panel_count": b4p.B4_PANEL_COUNT,
        "repository_count": len(slugs),
        "repository_identity_count": len(identities),
        "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
        "total_visible_source_bytes": total_visible_bytes,
        "mutually_disjoint_panels": True,
        "treatment_output_exists": False,
        "holdout_binding_digest": "",
    }
    binding["holdout_binding_digest"] = global_binding_digest(binding)
    return binding


def panel_freeze_digest(receipt: Mapping[str, Any]) -> str:
    return _digest("b4panelfreeze_", receipt, "freeze_receipt_digest")


def build_panel_freeze_receipt(
    *,
    panel_index: int,
    repo_lock_digest: str,
    task_manifest_digest: str,
    oracle_manifest_digest: str,
    holdout_binding_digest_value: str,
    repo_lock_path: Path,
    task_manifest_path: Path,
    oracle_manifest_path: Path,
    holdout_binding_path: Path,
    excluded_repo_lock_path: Path,
    preflight_exclusion_path: Path,
    cli_path: Path,
) -> dict[str, Any]:
    binding = b2c.load_json(holdout_binding_path)
    global_binding_path = Path(holdout_binding_path).parents[2] / "b4_private_holdout_binding.json"
    global_binding = b2c.load_json(global_binding_path)
    if binding.get("holdout_binding_digest") != holdout_binding_digest_value:
        raise B4ControlError("B4 panel freeze binding digest drifted")
    if global_binding.get("holdout_binding_digest") != global_binding_digest(global_binding):
        raise B4ControlError("B4 global holdout binding is invalid")
    cli = Path(cli_path).resolve(strict=True)
    receipt: dict[str, Any] = {
        "schema_version": B4_PANEL_FREEZE_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "protocol_digest": B4_PROTOCOL_DIGEST,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "panel_index": panel_index,
        "panel_schedule_digest": b4adapter.panel_schedule_digest(panel_index),
        "b21_execution_schedule_digest": b4adapter.panel_schedule_digest(panel_index),
        "runtime_qualification_digest": binding["runtime_qualification_digest"],
        "runtime_private_receipt_digest": binding["runtime_private_receipt_digest"],
        "runtime_bundle_digest": binding["runtime_bundle_digest"],
        "repo_lock_digest": repo_lock_digest,
        "task_manifest_digest": task_manifest_digest,
        "oracle_manifest_digest": oracle_manifest_digest,
        "holdout_binding_digest": holdout_binding_digest_value,
        "global_holdout_binding_digest": global_binding["holdout_binding_digest"],
        "repo_lock_file_sha256": _file_sha256(repo_lock_path),
        "task_manifest_file_sha256": _file_sha256(task_manifest_path),
        "oracle_manifest_file_sha256": _file_sha256(oracle_manifest_path),
        "holdout_binding_file_sha256": _file_sha256(holdout_binding_path),
        "global_holdout_binding_file_sha256": _file_sha256(global_binding_path),
        "history_binding_file_sha256": _file_sha256(excluded_repo_lock_path),
        "exclusion_registry_file_sha256": _file_sha256(preflight_exclusion_path),
        "cli_bytes": cli.stat().st_size,
        "cli_sha256": _file_sha256(cli),
        "request_timeout_seconds": B24_REQUEST_TIMEOUT_SECONDS,
        "adapter_command_timeout_seconds": B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
        "repository_count": b4p.B4_REPOSITORIES_PER_PANEL,
        "task_count": b4p.B4_TASKS_PER_PANEL,
        "logical_record_count": b4adapter.B4_PANEL_LOGICAL_RECORD_COUNT,
        "index_build_count": b4adapter.B4_PANEL_INDEX_BUILD_COUNT,
        "treatment_output_exists_at_freeze": False,
        "freeze_receipt_digest": "",
    }
    receipt["freeze_receipt_digest"] = panel_freeze_digest(receipt)
    return receipt


def global_freeze_digest(receipt: Mapping[str, Any]) -> str:
    return _digest("b4freeze_", receipt, "freeze_receipt_digest")


def build_global_freeze_receipt(
    *,
    private_root: Path,
    global_binding: Mapping[str, Any],
    runtime_public: Mapping[str, Any],
    runtime_private: Mapping[str, Any],
) -> dict[str, Any]:
    panel_freezes: list[dict[str, Any]] = []
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        path = _panel_paths(private_root, panel_index)["freeze"]
        value = b2c.load_json(path)
        if value.get("freeze_receipt_digest") != panel_freeze_digest(value):
            raise B4ControlError("B4 panel freeze digest mismatch")
        panel_freezes.append(
            {
                "panel_index": panel_index,
                "panel_freeze_digest": value["freeze_receipt_digest"],
                "panel_freeze_file_sha256": _file_sha256(path),
            }
        )
    receipt: dict[str, Any] = {
        "schema_version": B4_GLOBAL_FREEZE_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "protocol_digest": B4_PROTOCOL_DIGEST,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_private_receipt_digest": runtime_private["private_receipt_digest"],
        "runtime_bundle_digest": runtime_private["runtime_bundle_digest"],
        "holdout_binding_digest": global_binding["holdout_binding_digest"],
        "panel_freezes": panel_freezes,
        "panel_count": b4p.B4_PANEL_COUNT,
        "repository_count": b4p.B4_REPOSITORY_CLUSTER_COUNT,
        "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
        "logical_record_count": b4p.B4_LOGICAL_RECORD_COUNT,
        "index_build_count": b4p.B4_INDEX_BUILD_COUNT,
        "treatment_output_exists_at_freeze": False,
        "freeze_receipt_digest": "",
    }
    receipt["freeze_receipt_digest"] = global_freeze_digest(receipt)
    return receipt


def _validate_global_freeze_files(private_root: Path, receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema_version") != B4_GLOBAL_FREEZE_SCHEMA:
        raise B4ControlError("B4 global freeze schema drifted")
    if receipt.get("freeze_receipt_digest") != global_freeze_digest(receipt):
        raise B4ControlError("B4 global freeze digest mismatch")
    if receipt.get("control_source_bundle_digest") != b4src.control_source_bundle_digest():
        raise B4ControlError("B4 global freeze source drifted")
    rows = receipt.get("panel_freezes")
    if not isinstance(rows, list) or len(rows) != b4p.B4_PANEL_COUNT:
        raise B4ControlError("B4 global freeze panel set is incomplete")
    for panel_index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or row.get("panel_index") != panel_index:
            raise B4ControlError("B4 global freeze panel order drifted")
        path = _panel_paths(private_root, panel_index)["freeze"]
        value = b2c.load_json(path)
        if row.get("panel_freeze_digest") != value.get("freeze_receipt_digest"):
            raise B4ControlError("B4 global freeze panel digest drifted")
        if row.get("panel_freeze_file_sha256") != _file_sha256(path):
            raise B4ControlError("B4 global freeze panel file drifted")


def validate_panel_freeze_receipt(
    raw: Any,
    *,
    panel_index: int,
    repo_lock_digest: str,
    task_manifest_digest: str,
    oracle_manifest_digest: str,
    holdout_binding_digest_value: str,
    repo_lock_path: Path,
    task_manifest_path: Path,
    oracle_manifest_path: Path,
    holdout_binding_path: Path,
    excluded_repo_lock_path: Path,
    preflight_exclusion_path: Path,
    cli_path: Path,
) -> dict[str, Any]:
    expected = build_panel_freeze_receipt(
        panel_index=panel_index,
        repo_lock_digest=repo_lock_digest,
        task_manifest_digest=task_manifest_digest,
        oracle_manifest_digest=oracle_manifest_digest,
        holdout_binding_digest_value=holdout_binding_digest_value,
        repo_lock_path=repo_lock_path,
        task_manifest_path=task_manifest_path,
        oracle_manifest_path=oracle_manifest_path,
        holdout_binding_path=holdout_binding_path,
        excluded_repo_lock_path=excluded_repo_lock_path,
        preflight_exclusion_path=preflight_exclusion_path,
        cli_path=cli_path,
    )
    if not isinstance(raw, dict) or raw != expected:
        raise B4ControlError("B4 panel freeze drifted from locked inputs")
    private_root = Path(holdout_binding_path).parents[2]
    global_freeze = b2c.load_json(private_root / "b4_private_holdout_freeze.json")
    _validate_global_freeze_files(private_root, global_freeze)
    row = global_freeze["panel_freezes"][panel_index - 1]
    if row["panel_freeze_digest"] != raw["freeze_receipt_digest"]:
        raise B4ControlError("B4 panel freeze is absent from global freeze")
    return raw


def freeze_holdout(
    *,
    private_root: Path,
    candidate_catalog_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    runtime_scratch: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    cli_path: Path,
) -> dict[str, Any]:
    private_root = _safe_private_root(private_root)
    global_binding_path = private_root / "b4_private_holdout_binding.json"
    global_freeze_path = private_root / "b4_private_holdout_freeze.json"
    history_binding_path = private_root / "b4_private_history_binding.json"
    for path in (global_binding_path, global_freeze_path, history_binding_path):
        if os.path.lexists(path):
            raise B4ControlError("B4 freeze output already exists")
    state = validate_author_state(
        b2c.load_json(private_root / "b4_private_author_state.json"),
        catalog_path=candidate_catalog_path,
        history_paths=historical_repo_lock_paths,
        exclusion_path=exclusion_registry_path,
    )
    if state["completed_panels"] != list(range(1, b4p.B4_PANEL_COUNT + 1)):
        raise B4ControlError("B4 authoring is not complete")
    runtime_public, runtime_private = _load_runtime_for_authoring(
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        runtime_scratch=runtime_scratch,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        cli_path=cli_path,
        require_current_head=True,
    )
    histories = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in B4_HISTORY_LABELS
    }
    historical_slugs, _, _ = historical_repository_sets(histories)
    exclusion = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    validate_candidate_catalog(
        b2c.load_json(candidate_catalog_path),
        historical_slugs=historical_slugs,
        excluded_slugs=exclusion_slugs(exclusion),
    )
    global_binding = build_global_binding(
        private_root=private_root,
        candidate_catalog_path=candidate_catalog_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public=runtime_public,
        runtime_private=runtime_private,
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
    )
    _write_json_exclusive_or_equal(global_binding_path, global_binding)
    history_binding = _build_history_binding(
        history_paths=historical_repo_lock_paths, historical_locks=histories
    )
    _write_json_exclusive_or_equal(history_binding_path, history_binding)

    panel_freeze_digests: list[str] = []
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        paths = _panel_paths(private_root, panel_index)
        binding = b2c.load_json(paths["binding"])
        receipt = build_panel_freeze_receipt(
            panel_index=panel_index,
            repo_lock_digest=binding["repo_lock_digest"],
            task_manifest_digest=binding["task_manifest_digest"],
            oracle_manifest_digest=binding["oracle_manifest_digest"],
            holdout_binding_digest_value=binding["holdout_binding_digest"],
            repo_lock_path=paths["repo"],
            task_manifest_path=paths["task"],
            oracle_manifest_path=paths["oracle"],
            holdout_binding_path=paths["binding"],
            excluded_repo_lock_path=history_binding_path,
            preflight_exclusion_path=exclusion_registry_path,
            cli_path=cli_path,
        )
        _write_json_exclusive_or_equal(paths["freeze"], receipt)
        panel_freeze_digests.append(receipt["freeze_receipt_digest"])
    global_freeze = build_global_freeze_receipt(
        private_root=private_root,
        global_binding=global_binding,
        runtime_public=runtime_public,
        runtime_private=runtime_private,
    )
    _write_json_exclusive_or_equal(global_freeze_path, global_freeze)
    _validate_global_freeze_files(private_root, global_freeze)
    return {
        "status": "private_b4_holdout_frozen",
        "panel_count": b4p.B4_PANEL_COUNT,
        "repository_count": b4p.B4_REPOSITORY_CLUSTER_COUNT,
        "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
        "panel_freeze_count": len(panel_freeze_digests),
        "treatment_output_count": 0,
        "private_paths_or_digests_printed": False,
    }


def _treatment_inventory(runs_dir: Path) -> dict[str, int]:
    root = Path(runs_dir)
    counts = {
        "normal_entries": 0,
        "terminal_entries": 0,
        "panel_outcome_reports": 0,
        "durable_entries": 0,
    }
    if not root.exists():
        return counts
    if root.is_symlink() or not root.is_dir():
        counts["durable_entries"] = 1
        return counts
    for panel_root in sorted((root / "panels").glob("panel_*")) if (root / "panels").is_dir() else ():
        private = panel_root / "private"
        for key, name in (("normal_entries", "cells"), ("terminal_entries", "terminal_support")):
            entries = private / name
            if entries.is_dir() and not entries.is_symlink():
                counts[key] += sum(
                    entry.is_file() and not entry.is_symlink() and entry.suffix == ".json"
                    for entry in entries.iterdir()
                )
            elif os.path.lexists(entries):
                counts[key] += 1
    outcomes = root / "private" / "panel_outcomes"
    if outcomes.is_dir() and not outcomes.is_symlink():
        counts["panel_outcome_reports"] = sum(
            entry.is_file() and not entry.is_symlink() and entry.suffix == ".json"
            for entry in outcomes.iterdir()
        )
    elif os.path.lexists(outcomes):
        counts["panel_outcome_reports"] = 1
    counts["durable_entries"] = counts["normal_entries"] + counts["terminal_entries"]
    return counts


def validate_frozen_holdout(
    *,
    private_root: Path,
    candidate_catalog_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    runtime_scratch: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    cli_path: Path,
    require_runtime_checkpoint_at_head: bool,
) -> dict[str, Any]:
    private_root = _safe_private_root(private_root)
    runtime_public, runtime_private = _load_runtime_for_authoring(
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        runtime_scratch=runtime_scratch,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        cli_path=cli_path,
        require_current_head=require_runtime_checkpoint_at_head,
    )
    histories = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in B4_HISTORY_LABELS
    }
    historical_slugs, _, _ = historical_repository_sets(histories)
    exclusion = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    validate_candidate_catalog(
        b2c.load_json(candidate_catalog_path),
        historical_slugs=historical_slugs,
        excluded_slugs=exclusion_slugs(exclusion),
    )
    state = validate_author_state(
        b2c.load_json(private_root / "b4_private_author_state.json"),
        catalog_path=candidate_catalog_path,
        history_paths=historical_repo_lock_paths,
        exclusion_path=exclusion_registry_path,
    )
    if state["completed_panels"] != list(range(1, b4p.B4_PANEL_COUNT + 1)):
        raise B4ControlError("B4 frozen author state is incomplete")
    global_binding_path = private_root / "b4_private_holdout_binding.json"
    global_binding = b2c.load_json(global_binding_path)
    expected_binding = build_global_binding(
        private_root=private_root,
        candidate_catalog_path=candidate_catalog_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public=runtime_public,
        runtime_private=runtime_private,
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
    )
    if global_binding != expected_binding:
        raise B4ControlError("B4 global holdout binding drifted")
    global_freeze = b2c.load_json(private_root / "b4_private_holdout_freeze.json")
    expected_freeze = build_global_freeze_receipt(
        private_root=private_root,
        global_binding=global_binding,
        runtime_public=runtime_public,
        runtime_private=runtime_private,
    )
    if global_freeze != expected_freeze:
        raise B4ControlError("B4 global holdout freeze drifted")
    _validate_global_freeze_files(private_root, global_freeze)
    history_binding_path = private_root / "b4_private_history_binding.json"
    expected_history = _build_history_binding(
        history_paths=historical_repo_lock_paths, historical_locks=histories
    )
    if b2c.load_json(history_binding_path) != expected_history:
        raise B4ControlError("B4 history binding drifted")
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        paths = _panel_paths(private_root, panel_index)
        binding = b2c.load_json(paths["binding"])
        freeze = b2c.load_json(paths["freeze"])
        validate_panel_freeze_receipt(
            freeze,
            panel_index=panel_index,
            repo_lock_digest=binding["repo_lock_digest"],
            task_manifest_digest=binding["task_manifest_digest"],
            oracle_manifest_digest=binding["oracle_manifest_digest"],
            holdout_binding_digest_value=binding["holdout_binding_digest"],
            repo_lock_path=paths["repo"],
            task_manifest_path=paths["task"],
            oracle_manifest_path=paths["oracle"],
            holdout_binding_path=paths["binding"],
            excluded_repo_lock_path=history_binding_path,
            preflight_exclusion_path=exclusion_registry_path,
            cli_path=cli_path,
        )
    return {
        "private_root": private_root,
        "runtime_public": runtime_public,
        "runtime_private": runtime_private,
        "global_binding": global_binding,
        "global_freeze": global_freeze,
        "history_binding_path": history_binding_path,
    }


def readiness_digest(report: Mapping[str, Any]) -> str:
    return _digest("b4ready_", report, "readiness_digest")


def _build_public_readiness(
    *,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    runtime_public: Mapping[str, Any],
    total_visible_source_bytes: int,
    excluded_repository_count: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": B4_READINESS_SCHEMA,
        "phase": "product_bakeoff_b4_twelve_panel_private_holdout_freeze",
        "status": B4_READINESS_STATUS,
        "claim_level": "private_holdout_readiness_only_no_replication_result",
        "date": "2026-07-18",
        "protocol_gate": {
            "protocol_digest": B4_PROTOCOL_DIGEST,
            "control_source_bundle_digest": b4src.control_source_bundle_digest(),
            "attempt_boundary": "first_durable_treatment_observation",
            "launch_release_alone_consumes_attempt": False,
            "completed_observation_recompute_forbidden": True,
        },
        "runner_gate": {
            "runtime_publication_checkpoint": runtime_publication_checkpoint,
            "runtime_publication_ci_run_id": runtime_publication_ci_run_id,
            "runtime_publication_ci_conclusion": runtime_publication_ci_conclusion,
            "runtime_qualification_digest": runtime_public["qualification_digest"],
            "calculated_minimum_free_scratch_bytes": b4rq.B4_SCRATCH_CAPACITY_POLICY[
                "minimum_free_local_scratch_bytes_at_start"
            ],
            "arbitrary_fixed_disk_floor_used": False,
            "serial_panel_and_repository_execution": True,
            "exact_runtime_profile_public": False,
        },
        "holdout_gate": {
            "panel_count": b4p.B4_PANEL_COUNT,
            "repository_count": b4p.B4_REPOSITORY_CLUSTER_COUNT,
            "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
            "logical_record_count": b4p.B4_LOGICAL_RECORD_COUNT,
            "index_build_count": b4p.B4_INDEX_BUILD_COUNT,
            "mutually_disjoint_panels": True,
            "all_historical_frames_excluded": True,
            "excluded_repository_count": excluded_repository_count,
            "total_visible_source_bytes": total_visible_source_bytes,
            "all_queries_tokenizable": True,
            "all_positive_spans_compatible": True,
            "source_only_no_retrieval_or_adapter_execution": True,
        },
        "execution_state": {
            "private_holdout_frozen": True,
            "treatment_output_exists": False,
            "launch_authorization_exists": False,
            "launch_release_exists": False,
            "attempt_boundary_crossed": False,
            "empirical_result_exists": False,
        },
        "decision": {
            "runtime_qualified": True,
            "private_holdout_frozen": True,
            "public_readiness_ci_required_before_launch": True,
            "formal_execution_authorized": False,
        },
        "publication_limits": copy.deepcopy(B4_PUBLICATION_LIMITS),
        "next_authorized_action": (
            "Commit this aggregate-only readiness report and obtain green public CI; "
            "then create one private launch authorization and start the disconnect-safe "
            "B4 worker exactly once."
        ),
        "readiness_digest": "",
    }
    report["readiness_digest"] = readiness_digest(report)
    return report


def validate_public_readiness(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B4 readiness must be an object"]
    expected_keys = {
        "schema_version",
        "phase",
        "status",
        "claim_level",
        "date",
        "protocol_gate",
        "runner_gate",
        "holdout_gate",
        "execution_state",
        "decision",
        "publication_limits",
        "next_authorized_action",
        "readiness_digest",
    }
    errors: list[str] = []
    if set(report) != expected_keys:
        return ["B4 readiness shape drifted"]
    if report["schema_version"] != B4_READINESS_SCHEMA or report["status"] != B4_READINESS_STATUS:
        errors.append("B4 readiness schema or status drifted")
    protocol = report["protocol_gate"]
    if protocol != {
        "protocol_digest": B4_PROTOCOL_DIGEST,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "attempt_boundary": "first_durable_treatment_observation",
        "launch_release_alone_consumes_attempt": False,
        "completed_observation_recompute_forbidden": True,
    }:
        errors.append("B4 readiness protocol gate drifted")
    runner = report["runner_gate"]
    if not isinstance(runner, dict) or set(runner) != {
        "runtime_publication_checkpoint",
        "runtime_publication_ci_run_id",
        "runtime_publication_ci_conclusion",
        "runtime_qualification_digest",
        "calculated_minimum_free_scratch_bytes",
        "arbitrary_fixed_disk_floor_used",
        "serial_panel_and_repository_execution",
        "exact_runtime_profile_public",
    }:
        errors.append("B4 readiness runner gate shape drifted")
    else:
        if not re.fullmatch(r"[0-9a-f]{40}", str(runner["runtime_publication_checkpoint"])):
            errors.append("B4 readiness runtime checkpoint malformed")
        if not _exact_int(runner["runtime_publication_ci_run_id"]) or runner[
            "runtime_publication_ci_run_id"
        ] <= 0:
            errors.append("B4 readiness runtime CI id invalid")
        if runner["runtime_publication_ci_conclusion"] != "success":
            errors.append("B4 readiness runtime CI is not green")
        if not str(runner["runtime_qualification_digest"]).startswith("b4qual_"):
            errors.append("B4 readiness runtime digest malformed")
        if runner["calculated_minimum_free_scratch_bytes"] != b4rq.B4_SCRATCH_CAPACITY_POLICY[
            "minimum_free_local_scratch_bytes_at_start"
        ]:
            errors.append("B4 readiness scratch calculation drifted")
        if runner["arbitrary_fixed_disk_floor_used"] is not False:
            errors.append("B4 readiness introduced an arbitrary disk floor")
        if runner["serial_panel_and_repository_execution"] is not True:
            errors.append("B4 readiness serial execution drifted")
        if runner["exact_runtime_profile_public"] is not False:
            errors.append("B4 readiness published exact runtime profile")
    holdout = report["holdout_gate"]
    if not isinstance(holdout, dict):
        errors.append("B4 readiness holdout gate invalid")
    else:
        expected_counts = {
            "panel_count": b4p.B4_PANEL_COUNT,
            "repository_count": b4p.B4_REPOSITORY_CLUSTER_COUNT,
            "logical_task_count": b4p.B4_LOGICAL_TASK_COUNT,
            "logical_record_count": b4p.B4_LOGICAL_RECORD_COUNT,
            "index_build_count": b4p.B4_INDEX_BUILD_COUNT,
        }
        for key, value in expected_counts.items():
            if holdout.get(key) != value:
                errors.append("B4 readiness holdout count drifted")
        for key in (
            "mutually_disjoint_panels",
            "all_historical_frames_excluded",
            "all_queries_tokenizable",
            "all_positive_spans_compatible",
            "source_only_no_retrieval_or_adapter_execution",
        ):
            if holdout.get(key) is not True:
                errors.append("B4 readiness holdout integrity drifted")
        for key in ("excluded_repository_count", "total_visible_source_bytes"):
            if not _exact_int(holdout.get(key)) or holdout[key] < 0:
                errors.append("B4 readiness holdout aggregate invalid")
    if report["execution_state"] != {
        "private_holdout_frozen": True,
        "treatment_output_exists": False,
        "launch_authorization_exists": False,
        "launch_release_exists": False,
        "attempt_boundary_crossed": False,
        "empirical_result_exists": False,
    }:
        errors.append("B4 readiness execution state drifted")
    if report["decision"] != {
        "runtime_qualified": True,
        "private_holdout_frozen": True,
        "public_readiness_ci_required_before_launch": True,
        "formal_execution_authorized": False,
    }:
        errors.append("B4 readiness decision drifted")
    if report["publication_limits"] != B4_PUBLICATION_LIMITS:
        errors.append("B4 readiness publication limits drifted")
    if report["readiness_digest"] != readiness_digest(report):
        errors.append("B4 readiness digest mismatch")
    errors.extend(b2p.scan_public_report(report))
    raw = json.dumps(report, sort_keys=True).casefold()
    for token in (
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "private_receipt_digest",
        "launch_authorization_digest",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
    ):
        if token in raw:
            errors.append("B4 readiness contains a private binding token")
    return sorted(set(errors))


def build_public_readiness(
    *,
    private_root: Path,
    candidate_catalog_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    runtime_scratch: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    cli_path: Path,
    treatment_runs_dir: Path,
) -> dict[str, Any]:
    state = validate_frozen_holdout(
        private_root=private_root,
        candidate_catalog_path=candidate_catalog_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        runtime_scratch=runtime_scratch,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        cli_path=cli_path,
        require_runtime_checkpoint_at_head=True,
    )
    inventory = _treatment_inventory(treatment_runs_dir)
    if inventory["durable_entries"] or inventory["panel_outcome_reports"]:
        raise B4ControlError("B4 treatment output exists before readiness")
    private_root = Path(state["private_root"])
    for path in (
        private_root / "b4_private_launch_authorization.json",
        private_root / "b4_private_launch_release.json",
    ):
        if os.path.lexists(path):
            raise B4ControlError("B4 launch state exists before readiness")
    exclusion = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    report = _build_public_readiness(
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        runtime_public=state["runtime_public"],
        total_visible_source_bytes=state["global_binding"]["total_visible_source_bytes"],
        excluded_repository_count=len(exclusion["repositories"]),
    )
    errors = validate_public_readiness(report)
    if errors:
        raise B4ControlError("generated B4 readiness is invalid")
    return report


def private_readiness_binding_digest(value: Mapping[str, Any]) -> str:
    return _digest("b4readybind_", value, "readiness_binding_digest")


def build_private_readiness_binding(
    *,
    global_freeze: Mapping[str, Any],
    global_freeze_path: Path,
    readiness_report: Mapping[str, Any],
    readiness_report_path: Path,
) -> dict[str, Any]:
    if validate_public_readiness(readiness_report):
        raise B4ControlError("B4 readiness is invalid for private binding")
    if global_freeze.get("schema_version") != B4_GLOBAL_FREEZE_SCHEMA:
        raise B4ControlError("B4 global freeze schema is invalid for readiness binding")
    if global_freeze.get("freeze_receipt_digest") != global_freeze_digest(global_freeze):
        raise B4ControlError("B4 global freeze digest is invalid for readiness binding")
    value: dict[str, Any] = {
        "schema_version": B4_READINESS_BINDING_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "protocol_digest": B4_PROTOCOL_DIGEST,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "readiness_digest": readiness_report["readiness_digest"],
        "readiness_file_sha256": _file_sha256(readiness_report_path),
        "global_freeze_digest": global_freeze["freeze_receipt_digest"],
        "global_freeze_file_sha256": _file_sha256(global_freeze_path),
        "holdout_binding_digest": global_freeze["holdout_binding_digest"],
        "runtime_bundle_digest": global_freeze["runtime_bundle_digest"],
        "treatment_output_exists": False,
        "readiness_binding_digest": "",
    }
    value["readiness_binding_digest"] = private_readiness_binding_digest(value)
    return value


def validate_private_readiness_binding(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_private_readiness_binding(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B4ControlError("B4 private readiness binding drifted")
    return raw


def write_public_readiness(
    *, private_root: Path, path: Path, report: Mapping[str, Any]
) -> Path:
    if validate_public_readiness(report):
        raise B4ControlError("refusing to write invalid B4 readiness")
    private_root = _safe_private_root(private_root)
    public_target = Path(path).resolve(strict=False)
    try:
        public_target.relative_to(REPO.resolve(strict=True))
    except ValueError as exc:
        raise B4ControlError("B4 public readiness must stay inside checkout") from exc
    target = _write_json_exclusive_or_equal(public_target, report, mode=0o644)
    freeze_path = private_root / "b4_private_holdout_freeze.json"
    if freeze_path.is_symlink() or not freeze_path.is_file():
        raise B4ControlError("B4 global freeze is missing or unsafe for readiness")
    freeze = b2c.load_json(freeze_path)
    _validate_global_freeze_files(private_root, freeze)
    binding = build_private_readiness_binding(
        global_freeze=freeze,
        global_freeze_path=freeze_path,
        readiness_report=report,
        readiness_report_path=target,
    )
    _write_json_exclusive_or_equal(
        private_root / "b4_private_readiness_binding.json", binding
    )
    return target


def launch_authorization_digest(value: Mapping[str, Any]) -> str:
    return _digest("b4launch_", value, "launch_authorization_digest")


def build_launch_authorization(
    *,
    global_freeze: Mapping[str, Any],
    global_freeze_path: Path,
    readiness_report: Mapping[str, Any],
    readiness_report_path: Path,
    readiness_binding: Mapping[str, Any],
    readiness_binding_path: Path,
    readiness_checkpoint: str,
    readiness_ci_run_id: int,
    readiness_ci_conclusion: str,
) -> dict[str, Any]:
    if validate_public_readiness(readiness_report):
        raise B4ControlError("B4 public readiness is invalid")
    validate_publication_gate(
        artifact_path=readiness_report_path,
        checkpoint=readiness_checkpoint,
        ci_run_id=readiness_ci_run_id,
        ci_conclusion=readiness_ci_conclusion,
        require_current_head=True,
    )
    if global_freeze.get("freeze_receipt_digest") != global_freeze_digest(global_freeze):
        raise B4ControlError("B4 global freeze is invalid for authorization")
    if (
        readiness_binding.get("schema_version") != B4_READINESS_BINDING_SCHEMA
        or readiness_binding.get("readiness_digest") != readiness_report["readiness_digest"]
        or readiness_binding.get("readiness_file_sha256")
        != _file_sha256(readiness_report_path)
        or readiness_binding.get("global_freeze_digest")
        != global_freeze["freeze_receipt_digest"]
        or readiness_binding.get("global_freeze_file_sha256")
        != _file_sha256(global_freeze_path)
        or readiness_binding.get("protocol_digest") != B4_PROTOCOL_DIGEST
        or readiness_binding.get("control_source_bundle_digest")
        != b4src.control_source_bundle_digest()
        or readiness_binding.get("holdout_binding_digest")
        != global_freeze["holdout_binding_digest"]
        or readiness_binding.get("runtime_bundle_digest")
        != global_freeze["runtime_bundle_digest"]
        or readiness_binding.get("treatment_output_exists") is not False
        or readiness_binding.get("readiness_binding_digest")
        != private_readiness_binding_digest(readiness_binding)
    ):
        raise B4ControlError("B4 private readiness binding is invalid for authorization")
    authorization: dict[str, Any] = {
        "schema_version": B4_LAUNCH_AUTHORIZATION_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "protocol_digest": B4_PROTOCOL_DIGEST,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "runtime_bundle_digest": global_freeze["runtime_bundle_digest"],
        "freeze_receipt_digest": global_freeze["freeze_receipt_digest"],
        "freeze_receipt_file_sha256": _file_sha256(global_freeze_path),
        "readiness_digest": readiness_report["readiness_digest"],
        "readiness_file_sha256": _file_sha256(readiness_report_path),
        "readiness_binding_digest": readiness_binding["readiness_binding_digest"],
        "readiness_binding_file_sha256": _file_sha256(readiness_binding_path),
        "readiness_checkpoint": readiness_checkpoint,
        "readiness_ci_run_id": readiness_ci_run_id,
        "readiness_ci_conclusion": readiness_ci_conclusion,
        "formal_attempt_number": 1,
        "attempt_boundary": "first_durable_treatment_observation",
        "launch_release_alone_consumes_attempt": False,
        "launch_authorization_digest": "",
    }
    authorization["launch_authorization_digest"] = launch_authorization_digest(
        authorization
    )
    return authorization


def validate_launch_authorization(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_launch_authorization(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B4ControlError("B4 launch authorization drifted")
    return raw


def create_launch_authorization(
    *,
    private_root: Path,
    readiness_report_path: Path,
    readiness_checkpoint: str,
    readiness_ci_run_id: int,
    readiness_ci_conclusion: str,
) -> dict[str, Any]:
    private_root = _safe_private_root(private_root)
    path = private_root / "b4_private_launch_authorization.json"
    for state_path in (
        private_root / "b4_private_launch_release.json",
        private_root / "b4_private_terminal_state.json",
    ):
        if os.path.lexists(state_path):
            raise B4ControlError("B4 launch state exists before authorization")
    freeze_path = private_root / "b4_private_holdout_freeze.json"
    binding_path = private_root / "b4_private_readiness_binding.json"
    for private_path in (freeze_path, binding_path):
        if private_path.is_symlink() or not private_path.is_file():
            raise B4ControlError("B4 authorization input is missing or unsafe")
    readiness = b2c.load_json(readiness_report_path)
    freeze = b2c.load_json(freeze_path)
    _validate_global_freeze_files(private_root, freeze)
    binding = validate_private_readiness_binding(
        b2c.load_json(binding_path),
        global_freeze=freeze,
        global_freeze_path=freeze_path,
        readiness_report=readiness,
        readiness_report_path=readiness_report_path,
    )
    authorization = build_launch_authorization(
        global_freeze=freeze,
        global_freeze_path=freeze_path,
        readiness_report=readiness,
        readiness_report_path=readiness_report_path,
        readiness_binding=binding,
        readiness_binding_path=binding_path,
        readiness_checkpoint=readiness_checkpoint,
        readiness_ci_run_id=readiness_ci_run_id,
        readiness_ci_conclusion=readiness_ci_conclusion,
    )
    _write_json_exclusive_or_equal(path, authorization)
    return {
        "status": "private_b4_launch_authorized",
        "attempt_boundary_crossed": False,
        "private_path_or_digest_printed": False,
    }


def boundary_receipt_digest(value: Mapping[str, Any]) -> str:
    return _digest("b4attempt_", value, "attempt_boundary_receipt_digest")


def _boundary_path(runs_dir: Path) -> Path:
    return Path(runs_dir) / "private" / "b4_private_attempt_boundary.json"


def _build_boundary_receipt(
    *,
    freeze_receipt_digest: str,
    launch_authorization_digest: str,
    durable_entry_count: int,
    recovered_after_receipt_gap: bool,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": B4_ATTEMPT_BOUNDARY_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "attempt_boundary": "first_durable_treatment_observation",
        "attempt_boundary_crossed": True,
        "formal_attempt_number": 1,
        "launch_release_alone_consumes_attempt": False,
        "freeze_receipt_digest": freeze_receipt_digest,
        "launch_authorization_digest": launch_authorization_digest,
        "durable_entry_count_at_receipt": durable_entry_count,
        "recovered_after_receipt_gap": recovered_after_receipt_gap,
        "completed_observation_recompute_authorized": False,
        "attempt_boundary_receipt_digest": "",
    }
    value["attempt_boundary_receipt_digest"] = boundary_receipt_digest(value)
    return value


def validate_boundary_receipt(
    raw: Any,
    *,
    freeze_receipt_digest: str | None = None,
    launch_authorization_digest: str | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "control_version",
        "attempt_boundary",
        "attempt_boundary_crossed",
        "formal_attempt_number",
        "launch_release_alone_consumes_attempt",
        "freeze_receipt_digest",
        "launch_authorization_digest",
        "durable_entry_count_at_receipt",
        "recovered_after_receipt_gap",
        "completed_observation_recompute_authorized",
        "attempt_boundary_receipt_digest",
    }:
        raise B4ControlError("B4 attempt boundary receipt shape drifted")
    if raw["schema_version"] != B4_ATTEMPT_BOUNDARY_SCHEMA:
        raise B4ControlError("B4 attempt boundary schema drifted")
    if raw["attempt_boundary"] != "first_durable_treatment_observation":
        raise B4ControlError("B4 attempt boundary definition drifted")
    if raw["attempt_boundary_crossed"] is not True:
        raise B4ControlError("B4 attempt boundary receipt is not crossed")
    if raw["formal_attempt_number"] != 1:
        raise B4ControlError("B4 formal attempt number drifted")
    if raw["launch_release_alone_consumes_attempt"] is not False:
        raise B4ControlError("B4 launch release incorrectly consumed attempt")
    if not _exact_int(raw["durable_entry_count_at_receipt"]) or raw[
        "durable_entry_count_at_receipt"
    ] < 1:
        raise B4ControlError("B4 attempt boundary lacks a durable observation")
    if type(raw["recovered_after_receipt_gap"]) is not bool:
        raise B4ControlError("B4 attempt boundary recovery flag invalid")
    if raw["completed_observation_recompute_authorized"] is not False:
        raise B4ControlError("B4 attempt boundary authorized recomputation")
    if freeze_receipt_digest is not None and raw["freeze_receipt_digest"] != freeze_receipt_digest:
        raise B4ControlError("B4 attempt boundary freeze binding drifted")
    if launch_authorization_digest is not None and raw[
        "launch_authorization_digest"
    ] != launch_authorization_digest:
        raise B4ControlError("B4 attempt boundary launch binding drifted")
    if raw["attempt_boundary_receipt_digest"] != boundary_receipt_digest(raw):
        raise B4ControlError("B4 attempt boundary receipt digest mismatch")
    return raw


def _first_durable_observation(runs_dir: Path) -> Path | None:
    panels_root = Path(runs_dir) / "panels"
    if not panels_root.is_dir() or panels_root.is_symlink():
        return None
    for panel in sorted(panels_root.glob("panel_*")):
        for name in ("cells", "terminal_support"):
            root = panel / "private" / name
            if not root.is_dir() or root.is_symlink():
                continue
            for entry in sorted(root.glob("*.json")):
                if entry.is_file() and not entry.is_symlink():
                    return entry
    return None


def _fsync_observation(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise B4ControlError("B4 durable observation is missing or unsafe")
    with path.open("r+b") as handle:
        os.fsync(handle.fileno())
    if os.name != "nt":
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


def reconcile_attempt_boundary(
    *,
    runs_dir: Path,
    freeze_receipt_digest: str,
    launch_authorization_digest: str,
) -> dict[str, Any] | None:
    path = _boundary_path(runs_dir)
    inventory = _treatment_inventory(runs_dir)
    if path.is_file() and not path.is_symlink():
        return validate_boundary_receipt(
            b2c.load_json(path),
            freeze_receipt_digest=freeze_receipt_digest,
            launch_authorization_digest=launch_authorization_digest,
        )
    if os.path.lexists(path):
        raise B4ControlError("B4 attempt boundary path is unsafe")
    if inventory["durable_entries"] == 0:
        return None
    observation = _first_durable_observation(runs_dir)
    if observation is None:
        raise B4ControlError("B4 durable inventory lacks a regular observation")
    _fsync_observation(observation)
    value = _build_boundary_receipt(
        freeze_receipt_digest=freeze_receipt_digest,
        launch_authorization_digest=launch_authorization_digest,
        durable_entry_count=inventory["durable_entries"],
        recovered_after_receipt_gap=True,
    )
    _write_json_exclusive(path, value)
    return value


@contextlib.contextmanager
def attempt_boundary_observer(
    *,
    runs_dir: Path,
    freeze_receipt_digest: str,
    launch_authorization_digest: str,
) -> Iterator[None]:
    stop = threading.Event()
    errors: list[BaseException] = []

    def observe() -> None:
        while not stop.wait(0.05):
            try:
                if _boundary_path(runs_dir).is_file():
                    return
                observation = _first_durable_observation(runs_dir)
                if observation is None:
                    continue
                _fsync_observation(observation)
                inventory = _treatment_inventory(runs_dir)
                value = _build_boundary_receipt(
                    freeze_receipt_digest=freeze_receipt_digest,
                    launch_authorization_digest=launch_authorization_digest,
                    durable_entry_count=inventory["durable_entries"],
                    recovered_after_receipt_gap=False,
                )
                _write_json_exclusive(_boundary_path(runs_dir), value)
                return
            except BaseException as exc:  # noqa: BLE001 - delivered to owner thread
                errors.append(exc)
                return

    thread = threading.Thread(target=observe, name="b4-attempt-boundary", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=10)
        if thread.is_alive():
            raise B4ControlError("B4 attempt-boundary observer did not stop")
        if errors:
            raise B4ControlError("B4 attempt-boundary observer failed") from errors[0]


def _wait_for_launch_release(
    *,
    release_path: Path,
    authorization: Mapping[str, Any],
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    expected = {
        "schema_version": B4_LAUNCH_RELEASE_SCHEMA,
        "formal_attempt_number": 1,
        "readiness_checkpoint": authorization["readiness_checkpoint"],
        "launch_authorization_digest": authorization["launch_authorization_digest"],
        "release": True,
        "launch_release_alone_consumes_attempt": False,
    }
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if release_path.is_file() and not release_path.is_symlink():
            value = b2c.load_json(release_path)
            if value != expected:
                raise B4ControlError("B4 private launch release is unsafe")
            return value
        if os.path.lexists(release_path):
            raise B4ControlError("B4 private launch release path is unsafe")
        time.sleep(0.1)
    raise B4ControlError("B4 private launch release was not received")


def _build_panel_envelopes(
    *,
    private_root: Path,
    runs_dir: Path,
    exclusion_registry_path: Path,
    cli_path: Path,
    keep_worktrees: bool,
) -> list[Path]:
    history_binding_path = private_root / "b4_private_history_binding.json"
    envelope_root = runs_dir / "private" / "panel_envelopes"
    outcome_root = runs_dir / "private" / "panel_outcomes"
    envelope_root.mkdir(parents=True, exist_ok=True)
    outcome_root.mkdir(parents=True, exist_ok=True)
    envelopes: list[Path] = []
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        paths = _panel_paths(private_root, panel_index)
        freeze = b2c.load_json(paths["freeze"])
        envelope = {
            "schema_version": b4adapter.B4_PANEL_ENVELOPE_SCHEMA,
            "panel_index": panel_index,
            "repo_lock_path": str(paths["repo"].resolve(strict=True)),
            "task_manifest_path": str(paths["task"].resolve(strict=True)),
            "oracle_manifest_path": str(paths["oracle"].resolve(strict=True)),
            "holdout_binding_path": str(paths["binding"].resolve(strict=True)),
            "excluded_repo_lock_path": str(history_binding_path.resolve(strict=True)),
            "preflight_exclusion_path": str(Path(exclusion_registry_path).resolve(strict=True)),
            "freeze_receipt_path": str(paths["freeze"].resolve(strict=True)),
            "expected_freeze_digest": freeze["freeze_receipt_digest"],
            "runs_dir": str((runs_dir / "panels" / f"panel_{panel_index:02d}").resolve(strict=False)),
            "outcome_path": str((outcome_root / f"panel_{panel_index:02d}.json").resolve(strict=False)),
            "keep_worktrees": keep_worktrees,
        }
        if b4adapter.validate_panel_envelope(envelope):
            raise B4ControlError("generated B4 panel envelope is invalid")
        path = envelope_root / f"panel_{panel_index:02d}.json"
        _write_json_exclusive(path, envelope)
        envelopes.append(path)
    return envelopes


def _write_terminal_state(
    *,
    private_root: Path,
    state: str,
    boundary_crossed: bool,
    completed_panel_count: int,
    public_output_exists: bool,
) -> None:
    value = {
        "schema_version": B4_TERMINAL_STATE_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "state": state,
        "attempt_boundary_crossed": boundary_crossed,
        "completed_panel_count": completed_panel_count,
        "public_output_exists": public_output_exists,
        "retry_authorized": False if boundary_crossed else None,
    }
    path = private_root / "b4_private_terminal_state.json"
    if path.is_file() and not path.is_symlink():
        if b2c.load_json(path) != value:
            raise B4ControlError("B4 terminal state drifted")
        return
    _write_json_exclusive(path, value)


def _write_public_closeout(path: Path, report: Mapping[str, Any]) -> Path:
    import product_bakeoff_b4_publication as publication  # noqa: PLC0415

    schema = report.get("schema_version")
    if schema == publication.B4_RESULT_SCHEMA:
        errors = publication.validate_public_result(report)
    elif schema == publication.B4_FAILURE_SCHEMA:
        errors = publication.validate_public_failure(report)
    else:
        errors = ["unknown B4 public closeout schema"]
    if errors:
        raise B4ControlError("refusing to write invalid B4 public closeout")
    return _write_public_exclusive(path, report)


def _classify_postboundary_failure(exc: BaseException) -> str:
    if isinstance(exc, OSError) and exc.errno in {errno.ENOSPC, errno.EDQUOT}:
        return "postboundary_resource_failure"
    if isinstance(exc, (B4ControlError, b4adapter.B4ExecutionAdapterError, ValueError, TypeError)):
        return "postboundary_integrity_failure"
    return "postboundary_worker_failure"


def run_formal_replication(
    *,
    private_root: Path,
    candidate_catalog_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    runtime_scratch: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    cli_path: Path,
    readiness_report_path: Path,
    runs_dir: Path,
    public_closeout_path: Path,
    keep_worktrees: bool = False,
) -> dict[str, Any]:
    private_root = _safe_private_root(private_root)
    state = validate_frozen_holdout(
        private_root=private_root,
        candidate_catalog_path=candidate_catalog_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        runtime_scratch=runtime_scratch,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        cli_path=cli_path,
        require_runtime_checkpoint_at_head=False,
    )
    readiness_path = Path(readiness_report_path)
    readiness = b2c.load_json(readiness_path)
    if validate_public_readiness(readiness):
        raise B4ControlError("B4 readiness is invalid at run admission")
    readiness_binding_path = private_root / "b4_private_readiness_binding.json"
    if readiness_binding_path.is_symlink() or not readiness_binding_path.is_file():
        raise B4ControlError("B4 private readiness binding is missing or unsafe")
    readiness_binding = validate_private_readiness_binding(
        b2c.load_json(readiness_binding_path),
        global_freeze=state["global_freeze"],
        global_freeze_path=private_root / "b4_private_holdout_freeze.json",
        readiness_report=readiness,
        readiness_report_path=readiness_path,
    )
    authorization_path = private_root / "b4_private_launch_authorization.json"
    if authorization_path.is_symlink() or not authorization_path.is_file():
        raise B4ControlError("B4 launch authorization is missing or unsafe")
    authorization = b2c.load_json(authorization_path)
    validate_launch_authorization(
        authorization,
        global_freeze=state["global_freeze"],
        global_freeze_path=private_root / "b4_private_holdout_freeze.json",
        readiness_report=readiness,
        readiness_report_path=readiness_path,
        readiness_binding=readiness_binding,
        readiness_binding_path=readiness_binding_path,
        readiness_checkpoint=authorization["readiness_checkpoint"],
        readiness_ci_run_id=authorization["readiness_ci_run_id"],
        readiness_ci_conclusion=authorization["readiness_ci_conclusion"],
    )
    if _git_head() != authorization["readiness_checkpoint"]:
        raise B4ControlError("checkout is not the authorized B4 readiness checkpoint")
    runs_dir = Path(runs_dir)
    if os.path.lexists(runs_dir) and (
        runs_dir.is_symlink() or not runs_dir.is_dir() or any(runs_dir.iterdir())
    ):
        raise B4ControlError("B4 formal runs directory must be absent or empty")
    runs_dir.mkdir(parents=True, exist_ok=True)
    public_closeout_path = Path(public_closeout_path)
    if os.path.lexists(public_closeout_path):
        raise B4ControlError("B4 public closeout already exists")
    release_path = private_root / "b4_private_launch_release.json"
    admission_path = private_root / "b4_private_runner_admission.json"
    boundary_path = _boundary_path(runs_dir)
    for path in (release_path, admission_path, boundary_path):
        if os.path.lexists(path):
            raise B4ControlError("B4 formal launch state already exists")
    envelopes = _build_panel_envelopes(
        private_root=private_root,
        runs_dir=runs_dir,
        exclusion_registry_path=exclusion_registry_path,
        cli_path=cli_path,
        keep_worktrees=keep_worktrees,
    )
    admission = {
        "schema_version": B4_RUNNER_ADMISSION_SCHEMA,
        "control_version": B4_CONTROL_VERSION,
        "runner_admitted": True,
        "zero_treatment_observations": True,
        "panel_envelope_count": len(envelopes),
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "runtime_qualification_digest": state["runtime_public"]["qualification_digest"],
        "freeze_receipt_digest": state["global_freeze"]["freeze_receipt_digest"],
        "launch_authorization_digest": authorization["launch_authorization_digest"],
        "launch_release_consumes_attempt": False,
    }
    _write_json_exclusive(admission_path, admission)
    if _treatment_inventory(runs_dir)["durable_entries"] != 0:
        raise B4ControlError("B4 treatment observation appeared before launch release")
    _wait_for_launch_release(
        release_path=release_path,
        authorization=authorization,
    )

    completed_panels = 0
    try:
        with attempt_boundary_observer(
            runs_dir=runs_dir,
            freeze_receipt_digest=state["global_freeze"]["freeze_receipt_digest"],
            launch_authorization_digest=authorization["launch_authorization_digest"],
        ):
            for panel_index, envelope_path in enumerate(envelopes, start=1):
                command = [
                    sys.executable,
                    str((REPO / "eval" / "product_bakeoff_b4_execution_adapter.py").resolve(strict=True)),
                    "--run-panel-envelope",
                    str(envelope_path.resolve(strict=True)),
                    "--confirm-private-input",
                    "--confirm-private-output",
                ]
                completed = subprocess.run(
                    command,
                    cwd=REPO,
                    check=False,
                )
                if completed.returncode != 0:
                    raise B4ControlError("B4 panel child exited nonzero")
                outcome_path = runs_dir / "private" / "panel_outcomes" / f"panel_{panel_index:02d}.json"
                report = b2c.load_json(outcome_path)
                if b4adapter.validate_panel_outcome_report(report):
                    raise B4ControlError("B4 completed panel outcome failed validation")
                completed_panels += 1
        boundary = reconcile_attempt_boundary(
            runs_dir=runs_dir,
            freeze_receipt_digest=state["global_freeze"]["freeze_receipt_digest"],
            launch_authorization_digest=authorization["launch_authorization_digest"],
        )
        if boundary is None:
            raise B4ControlError("B4 full matrix completed without an attempt boundary")
        panel_reports = [
            b2c.load_json(
                runs_dir / "private" / "panel_outcomes" / f"panel_{panel_index:02d}.json"
            )
            for panel_index in range(1, b4p.B4_PANEL_COUNT + 1)
        ]
        result = b4adapter.assemble_run_result(panel_reports)
        import product_bakeoff_b4_publication as publication  # noqa: PLC0415
        import product_bakeoff_b4_scorer as scorer  # noqa: PLC0415

        analysis = scorer.score_b4(result)
        private_analysis_path = runs_dir / "private" / "b4_private_analysis.json"
        _write_json_exclusive(private_analysis_path, analysis)
        public = publication.build_public_result(analysis)
        _write_public_closeout(public_closeout_path, public)
        _write_terminal_state(
            private_root=private_root,
            state="complete",
            boundary_crossed=True,
            completed_panel_count=completed_panels,
            public_output_exists=True,
        )
        return {
            "passed": True,
            "status": "complete_public_aggregate_written",
            "completed_panel_count": completed_panels,
            "completed_group_count": b4p.B4_LOGICAL_GROUP_COUNT,
            "logical_record_count": b4p.B4_LOGICAL_RECORD_COUNT,
            "private_metrics_printed": False,
        }
    except Exception as exc:
        # The public writer is atomic.  If replacement succeeded but a later
        # directory fsync or terminal-state write failed, never overwrite a
        # valid aggregate success with a contradictory failure closeout.
        import product_bakeoff_b4_publication as publication  # noqa: PLC0415

        if public_closeout_path.is_file() and not public_closeout_path.is_symlink():
            try:
                existing_public = b2c.load_json(public_closeout_path)
                existing_success = not publication.validate_public_result(
                    existing_public
                )
            except Exception:
                existing_success = False
            if existing_success:
                terminal_state_recorded = True
                try:
                    _write_terminal_state(
                        private_root=private_root,
                        state="complete",
                        boundary_crossed=True,
                        completed_panel_count=completed_panels,
                        public_output_exists=True,
                    )
                except Exception:
                    terminal_state_recorded = False
                return {
                    "passed": True,
                    "status": "complete_public_aggregate_written",
                    "completed_panel_count": completed_panels,
                    "completed_group_count": b4p.B4_LOGICAL_GROUP_COUNT,
                    "logical_record_count": b4p.B4_LOGICAL_RECORD_COUNT,
                    "terminal_state_recorded": terminal_state_recorded,
                    "private_metrics_printed": False,
                }
        boundary = reconcile_attempt_boundary(
            runs_dir=runs_dir,
            freeze_receipt_digest=state["global_freeze"]["freeze_receipt_digest"],
            launch_authorization_digest=authorization["launch_authorization_digest"],
        )
        crossed = boundary is not None
        inventory = _treatment_inventory(runs_dir)
        failure = publication.build_public_failure(
            failure_class=(
                _classify_postboundary_failure(exc)
                if crossed
                else "preboundary_admission_failure"
            ),
            attempt_boundary_crossed=crossed,
            completed_group_count=(
                inventory["durable_entries"] if crossed else 0
            ),
            logical_record_count=(
                inventory["durable_entries"] if crossed else 0
            ),
        )
        _write_public_closeout(public_closeout_path, failure)
        _write_terminal_state(
            private_root=private_root,
            state="failed_closed",
            boundary_crossed=crossed,
            completed_panel_count=completed_panels,
            public_output_exists=True,
        )
        return {
            "passed": False,
            "status": "failed_closed_public_aggregate_written",
            "attempt_boundary_crossed": crossed,
            "completed_panel_count": completed_panels,
            "error_class": type(exc).__name__,
            "private_detail_printed": False,
        }


def reset_preboundary_launch_state(
    *,
    private_root: Path,
    runs_dir: Path,
    public_closeout_path: Path,
    explicit_worker_stopped_confirmation: bool,
) -> dict[str, Any]:
    """Remove only zero-observation state created before launch release.

    This recovery is intentionally unavailable once a release, boundary,
    treatment observation, panel outcome, terminal state, or public closeout
    exists.  It permits retrying a failed admission without inventing a new
    formal attempt or deleting any treatment evidence.
    """

    if explicit_worker_stopped_confirmation is not True:
        raise B4ControlError("B4 pre-boundary reset requires stopped-worker confirmation")
    private_root = _safe_private_root(private_root)
    runs_root = Path(runs_dir).resolve(strict=False)
    public_path = Path(public_closeout_path)
    release_path = private_root / "b4_private_launch_release.json"
    boundary_path = _boundary_path(runs_root)
    terminal_path = private_root / "b4_private_terminal_state.json"
    admission_path = private_root / "b4_private_runner_admission.json"
    for path, label in (
        (release_path, "launch release"),
        (boundary_path, "attempt boundary"),
        (terminal_path, "terminal state"),
        (public_path, "public closeout"),
    ):
        if os.path.lexists(path):
            raise B4ControlError(f"B4 {label} exists; pre-boundary reset is forbidden")
    inventory = _treatment_inventory(runs_root)
    if inventory["durable_entries"] or inventory["panel_outcome_reports"]:
        raise B4ControlError("B4 treatment evidence exists; pre-boundary reset is forbidden")

    if admission_path.is_file() and not admission_path.is_symlink():
        admission = b2c.load_json(admission_path)
        if (
            not isinstance(admission, dict)
            or admission.get("schema_version") != B4_RUNNER_ADMISSION_SCHEMA
            or admission.get("runner_admitted") is not True
            or admission.get("zero_treatment_observations") is not True
            or admission.get("launch_release_consumes_attempt") is not False
        ):
            raise B4ControlError("B4 pre-boundary admission receipt is malformed")
    elif os.path.lexists(admission_path):
        raise B4ControlError("B4 pre-boundary admission path is unsafe")

    if os.path.lexists(runs_root):
        if runs_root.is_symlink() or not runs_root.is_dir():
            raise B4ControlError("B4 pre-boundary runs root is unsafe")
        resolved_runs = runs_root.resolve(strict=True)
        repo_root = REPO.resolve(strict=True)
        private_resolved = private_root.resolve(strict=True)
        anchor = Path(resolved_runs.anchor)
        if (
            resolved_runs == anchor
            or resolved_runs == repo_root
            or resolved_runs in repo_root.parents
            or resolved_runs == private_resolved
            or resolved_runs in private_resolved.parents
        ):
            raise B4ControlError("B4 pre-boundary runs root is too broad to remove")
        top_entries = {entry.name: entry for entry in resolved_runs.iterdir()}
        if set(top_entries) - {"private"}:
            raise B4ControlError("B4 pre-boundary runs root contains an unknown entry")
        private_runs = top_entries.get("private")
        if private_runs is not None:
            if private_runs.is_symlink() or not private_runs.is_dir():
                raise B4ControlError("B4 pre-boundary private runs directory is unsafe")
            private_entries = {entry.name: entry for entry in private_runs.iterdir()}
            if set(private_entries) - {"panel_envelopes", "panel_outcomes"}:
                raise B4ControlError("B4 pre-boundary private runs contain an unknown entry")
            envelopes = private_entries.get("panel_envelopes")
            if envelopes is not None:
                if envelopes.is_symlink() or not envelopes.is_dir():
                    raise B4ControlError("B4 pre-boundary envelope directory is unsafe")
                for entry in envelopes.iterdir():
                    if (
                        entry.is_symlink()
                        or not entry.is_file()
                        or not re.fullmatch(r"panel_\d{2}\.json", entry.name)
                    ):
                        raise B4ControlError("B4 pre-boundary envelope entry is unsafe")
            outcomes = private_entries.get("panel_outcomes")
            if outcomes is not None and (
                outcomes.is_symlink()
                or not outcomes.is_dir()
                or any(outcomes.iterdir())
            ):
                raise B4ControlError("B4 pre-boundary outcome directory is not empty")
        shutil.rmtree(resolved_runs)
    if admission_path.is_file() and not admission_path.is_symlink():
        admission_path.unlink()
    return {
        "status": "preboundary_launch_state_reset",
        "attempt_boundary_crossed": False,
        "treatment_observation_count": 0,
        "launch_release_exists": False,
        "private_path_or_digest_printed": False,
    }


def closeout_interrupted_failure(
    *,
    private_root: Path,
    runs_dir: Path,
    public_closeout_path: Path,
    explicit_worker_stopped_confirmation: bool,
) -> dict[str, Any]:
    if explicit_worker_stopped_confirmation is not True:
        raise B4ControlError("B4 interrupted closeout requires stopped-worker confirmation")
    private_root = _safe_private_root(private_root)
    freeze = b2c.load_json(private_root / "b4_private_holdout_freeze.json")
    authorization = b2c.load_json(private_root / "b4_private_launch_authorization.json")
    boundary = reconcile_attempt_boundary(
        runs_dir=runs_dir,
        freeze_receipt_digest=freeze["freeze_receipt_digest"],
        launch_authorization_digest=authorization["launch_authorization_digest"],
    )
    crossed = boundary is not None
    inventory = _treatment_inventory(runs_dir)
    completed_panels = inventory["panel_outcome_reports"]
    import product_bakeoff_b4_publication as publication  # noqa: PLC0415

    failure = publication.build_public_failure(
        failure_class=("postboundary_worker_failure" if crossed else "preboundary_admission_failure"),
        attempt_boundary_crossed=crossed,
        completed_group_count=(
            inventory["durable_entries"] if crossed else 0
        ),
        logical_record_count=(
            inventory["durable_entries"] if crossed else 0
        ),
    )
    _write_public_closeout(public_closeout_path, failure)
    _write_terminal_state(
        private_root=private_root,
        state="failed_closed",
        boundary_crossed=crossed,
        completed_panel_count=completed_panels,
        public_output_exists=True,
    )
    return {
        "passed": False,
        "status": "failed_closed_public_aggregate_written",
        "attempt_boundary_crossed": crossed,
        "completed_panel_count": completed_panels,
        "private_detail_printed": False,
    }


def aggregate_status(
    *, private_root: Path, runs_dir: Path, public_closeout_path: Path
) -> dict[str, Any]:
    inventory = _treatment_inventory(runs_dir)
    boundary = _boundary_path(runs_dir)
    release = Path(private_root) / "b4_private_launch_release.json"
    admission = Path(private_root) / "b4_private_runner_admission.json"
    return {
        "runner_admitted": admission.is_file() and not admission.is_symlink(),
        "launch_release_issued": release.is_file() and not release.is_symlink(),
        "attempt_boundary_crossed": (
            (boundary.is_file() and not boundary.is_symlink())
            or inventory["durable_entries"] > 0
        ),
        "completed_panel_count": inventory["panel_outcome_reports"],
        "completed_group_count": inventory["durable_entries"],
        "logical_record_count": inventory["durable_entries"],
        "public_output_exists": Path(public_closeout_path).is_file()
        and not Path(public_closeout_path).is_symlink(),
    }


def _synthetic_catalog() -> dict[str, Any]:
    slots = []
    for slot_index, slot in enumerate(b2p.build_task_slots()[::4], start=1):
        candidates = [
            {
                "repo": f"candidate{slot_index:02d}/repository{candidate_index:02d}",
                "expected_license": "MIT",
            }
            for candidate_index in range(1, b4p.B4_PANEL_COUNT + 1)
        ]
        slots.append({"repo_slot": slot.repo_slot, "candidates": candidates})
    return {"schema_version": B4_CANDIDATE_CATALOG_SCHEMA, "slots": slots}


def run_self_test() -> dict[str, Any]:
    catalog = _synthetic_catalog()
    validated = validate_candidate_catalog(
        catalog, historical_slugs=set(), excluded_slugs=set()
    )
    cursors = {slot.repo_slot: 0 for slot in b2p.build_task_slots()[::4]}
    plan = build_panel_candidate_plan(validated, cursors)
    selected = {
        row["repo_slot"]: _repo_slug(row["candidates"][0]["repo"])
        for row in plan["slots"]
    }
    advanced = _advance_cursors(
        catalog=validated, cursors=cursors, selected_by_slot=selected
    )
    readiness = _build_public_readiness(
        runtime_publication_checkpoint="a" * 40,
        runtime_publication_ci_run_id=1,
        runtime_publication_ci_conclusion="success",
        runtime_public={"qualification_digest": "b4qual_" + "b" * 64},
        total_visible_source_bytes=1,
        excluded_repository_count=0,
    )
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        runs = root / "runs"
        observation = runs / "panels" / "panel_01" / "private" / "cells" / "one.json"
        observation.parent.mkdir(parents=True)
        observation.write_text("{}\n", encoding="utf-8")
        boundary = reconcile_attempt_boundary(
            runs_dir=runs,
            freeze_receipt_digest="b4freeze_test",
            launch_authorization_digest="b4launch_test",
        )
        inventory = _treatment_inventory(runs)
        status = aggregate_status(
            private_root=root / "aggregate_private",
            runs_dir=runs,
            public_closeout_path=root / "aggregate_public.json",
        )

        reset_private = root / "reset_private"
        reset_runs = root / "reset_runs"
        envelopes = reset_runs / "private" / "panel_envelopes"
        outcomes = reset_runs / "private" / "panel_outcomes"
        envelopes.mkdir(parents=True)
        outcomes.mkdir(parents=True)
        (envelopes / "panel_01.json").write_text("{}\n", encoding="utf-8")
        reset_private.mkdir()
        _write_json_exclusive(
            reset_private / "b4_private_runner_admission.json",
            {
                "schema_version": B4_RUNNER_ADMISSION_SCHEMA,
                "runner_admitted": True,
                "zero_treatment_observations": True,
                "launch_release_consumes_attempt": False,
            },
        )
        reset_report = reset_preboundary_launch_state(
            private_root=reset_private,
            runs_dir=reset_runs,
            public_closeout_path=root / "reset_public.json",
            explicit_worker_stopped_confirmation=True,
        )

        cleanup_panel = root / "cleanup_panel"
        selected_clone = cleanup_panel / "clones" / "selected"
        rejected_clone = cleanup_panel / "clones" / "rejected"
        selected_clone.mkdir(parents=True)
        rejected_clone.mkdir()
        original_validate_repo_lock = b2c.validate_repo_lock
        b2c.validate_repo_lock = lambda raw, require_sources=False: raw
        try:
            removed_clone_count = _cleanup_unselected_clones(
                cleanup_panel,
                {
                    "repos": [
                        {"source": {"clone_root": str(selected_clone)}}
                    ]
                },
            )
        finally:
            b2c.validate_repo_lock = original_validate_repo_lock
        clone_cleanup_valid = (
            removed_clone_count == 1
            and selected_clone.is_dir()
            and not rejected_clone.exists()
        )
        resumable_path = root / "resumable.json"
        _write_json_exclusive_or_equal(resumable_path, {"value": 1})
        _write_json_exclusive_or_equal(resumable_path, {"value": 1})
        resumable_equal_reused = b2c.load_json(resumable_path) == {"value": 1}
        readiness_path = root / "readiness.json"
        _write_json_exclusive(readiness_path, readiness, mode=0o644)
        synthetic_freeze = {
            "schema_version": B4_GLOBAL_FREEZE_SCHEMA,
            "control_source_bundle_digest": b4src.control_source_bundle_digest(),
            "holdout_binding_digest": "b4holdout_synthetic",
            "runtime_bundle_digest": "b4run_synthetic",
            "freeze_receipt_digest": "",
        }
        synthetic_freeze["freeze_receipt_digest"] = global_freeze_digest(
            synthetic_freeze
        )
        freeze_path = root / "freeze.json"
        _write_json_exclusive(freeze_path, synthetic_freeze)
        readiness_binding = build_private_readiness_binding(
            global_freeze=synthetic_freeze,
            global_freeze_path=freeze_path,
            readiness_report=readiness,
            readiness_report_path=readiness_path,
        )
        readiness_binding_valid = validate_private_readiness_binding(
            readiness_binding,
            global_freeze=synthetic_freeze,
            global_freeze_path=freeze_path,
            readiness_report=readiness,
            readiness_report_path=readiness_path,
        ) is readiness_binding
        readiness_binding_path = root / "readiness_binding.json"
        _write_json_exclusive(readiness_binding_path, readiness_binding)
        original_publication_gate = validate_publication_gate
        globals()["validate_publication_gate"] = lambda **_: None
        try:
            authorization = build_launch_authorization(
                global_freeze=synthetic_freeze,
                global_freeze_path=freeze_path,
                readiness_report=readiness,
                readiness_report_path=readiness_path,
                readiness_binding=readiness_binding,
                readiness_binding_path=readiness_binding_path,
                readiness_checkpoint="a" * 40,
                readiness_ci_run_id=1,
                readiness_ci_conclusion="success",
            )
        finally:
            globals()["validate_publication_gate"] = original_publication_gate
        authorization_binds_readiness = (
            authorization["readiness_binding_digest"]
            == readiness_binding["readiness_binding_digest"]
            and authorization["freeze_receipt_digest"]
            == synthetic_freeze["freeze_receipt_digest"]
        )
    checks = {
        "catalog_valid": validated is catalog,
        "panel_plan_has_twelve_slots": len(plan["slots"]) == 12,
        "cursor_advanced_once": set(advanced.values()) == {1},
        "readiness_valid": not validate_public_readiness(readiness),
        "readiness_zero_treatment": readiness["execution_state"][
            "treatment_output_exists"
        ]
        is False,
        "readiness_no_arbitrary_disk_floor": readiness["runner_gate"][
            "arbitrary_fixed_disk_floor_used"
        ]
        is False,
        "boundary_reconciled": boundary is not None,
        "boundary_valid": boundary is not None
        and validate_boundary_receipt(
            boundary,
            freeze_receipt_digest="b4freeze_test",
            launch_authorization_digest="b4launch_test",
        )
        is boundary,
        "inventory_detected_one_observation": inventory["durable_entries"] == 1,
        "status_uses_exact_durable_progress": status["completed_group_count"] == 1
        and status["logical_record_count"] == 1
        and status["completed_panel_count"] == 0,
        "preboundary_reset_succeeded": reset_report["attempt_boundary_crossed"]
        is False,
        "preboundary_reset_removed_only_admission_state": not reset_runs.exists()
        and not (reset_private / "b4_private_runner_admission.json").exists(),
        "clone_cleanup_uses_frozen_clone_root": clone_cleanup_valid,
        "equal_freeze_receipt_is_resumable": resumable_equal_reused,
        "private_readiness_binding_valid": readiness_binding_valid,
        "launch_authorization_binds_private_readiness": authorization_binds_readiness,
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
    catalog = _synthetic_catalog()
    repeated = copy.deepcopy(catalog)
    repeated["slots"][1]["candidates"][0] = copy.deepcopy(
        repeated["slots"][0]["candidates"][0]
    )
    try:
        validate_candidate_catalog(repeated, historical_slugs=set(), excluded_slugs=set())
        checks["repeated_candidate_rejected"] = False
    except B4ControlError:
        checks["repeated_candidate_rejected"] = True
    historical = _repo_slug(catalog["slots"][0]["candidates"][0]["repo"])
    try:
        validate_candidate_catalog(
            catalog, historical_slugs={historical}, excluded_slugs=set()
        )
        checks["historical_candidate_rejected"] = False
    except B4ControlError:
        checks["historical_candidate_rejected"] = True
    depleted_cursors = {
        row["repo_slot"]: len(row["candidates"]) for row in catalog["slots"]
    }
    try:
        build_panel_candidate_plan(catalog, depleted_cursors)
        checks["catalog_depletion_rejected"] = False
    except B4ControlError:
        checks["catalog_depletion_rejected"] = True
    readiness = _build_public_readiness(
        runtime_publication_checkpoint="a" * 40,
        runtime_publication_ci_run_id=1,
        runtime_publication_ci_conclusion="success",
        runtime_public={"qualification_digest": "b4qual_" + "b" * 64},
        total_visible_source_bytes=1,
        excluded_repository_count=0,
    )
    drifted = copy.deepcopy(readiness)
    drifted["runner_gate"]["arbitrary_fixed_disk_floor_used"] = True
    checks["arbitrary_disk_floor_rejected"] = bool(validate_public_readiness(drifted))
    leaked = copy.deepcopy(readiness)
    leaked["next_authorized_action"] += " freeze_receipt_digest"
    checks["private_readiness_token_rejected"] = bool(validate_public_readiness(leaked))
    boundary = _build_boundary_receipt(
        freeze_receipt_digest="b4freeze_test",
        launch_authorization_digest="b4launch_test",
        durable_entry_count=1,
        recovered_after_receipt_gap=False,
    )
    bad_boundary = copy.deepcopy(boundary)
    bad_boundary["completed_observation_recompute_authorized"] = True
    try:
        validate_boundary_receipt(bad_boundary)
        checks["boundary_recompute_rejected"] = False
    except B4ControlError:
        checks["boundary_recompute_rejected"] = True
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        private = root / "private"
        private.mkdir()
        _write_json_exclusive(
            private / "b4_private_launch_release.json",
            {"release": True},
        )
        try:
            reset_preboundary_launch_state(
                private_root=private,
                runs_dir=root / "runs",
                public_closeout_path=root / "public.json",
                explicit_worker_stopped_confirmation=True,
            )
            checks["released_launch_reset_rejected"] = False
        except B4ControlError:
            checks["released_launch_reset_rejected"] = True

        evidence_private = root / "evidence_private"
        evidence_private.mkdir()
        evidence = (
            root
            / "evidence_runs"
            / "panels"
            / "panel_01"
            / "private"
            / "cells"
            / "one.json"
        )
        evidence.parent.mkdir(parents=True)
        evidence.write_text("{}\n", encoding="utf-8")
        try:
            reset_preboundary_launch_state(
                private_root=evidence_private,
                runs_dir=root / "evidence_runs",
                public_closeout_path=root / "evidence_public.json",
                explicit_worker_stopped_confirmation=True,
            )
            checks["observed_launch_reset_rejected"] = False
        except B4ControlError:
            checks["observed_launch_reset_rejected"] = True

        resumable = root / "resumable.json"
        _write_json_exclusive_or_equal(resumable, {"value": 1})
        try:
            _write_json_exclusive_or_equal(resumable, {"value": 2})
            checks["resumable_freeze_drift_rejected"] = False
        except B4ControlError:
            checks["resumable_freeze_drift_rejected"] = True

        readiness_path = root / "readiness.json"
        _write_json_exclusive(readiness_path, readiness, mode=0o644)
        synthetic_freeze = {
            "schema_version": B4_GLOBAL_FREEZE_SCHEMA,
            "control_source_bundle_digest": b4src.control_source_bundle_digest(),
            "holdout_binding_digest": "b4holdout_synthetic",
            "runtime_bundle_digest": "b4run_synthetic",
            "freeze_receipt_digest": "",
        }
        synthetic_freeze["freeze_receipt_digest"] = global_freeze_digest(
            synthetic_freeze
        )
        freeze_path = root / "freeze.json"
        _write_json_exclusive(freeze_path, synthetic_freeze)
        binding = build_private_readiness_binding(
            global_freeze=synthetic_freeze,
            global_freeze_path=freeze_path,
            readiness_report=readiness,
            readiness_report_path=readiness_path,
        )
        readiness_path.write_text("{}\n", encoding="utf-8")
        try:
            validate_private_readiness_binding(
                binding,
                global_freeze=synthetic_freeze,
                global_freeze_path=freeze_path,
                readiness_report=readiness,
                readiness_report_path=readiness_path,
            )
            checks["readiness_file_drift_rejected"] = False
        except B4ControlError:
            checks["readiness_file_drift_rejected"] = True
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B4_CONTROL_VERSION",
    "B4_CANDIDATE_CATALOG_SCHEMA",
    "B4_EXCLUSION_REGISTRY_SCHEMA",
    "B4_READINESS_SCHEMA",
    "B4_READINESS_BINDING_SCHEMA",
    "B4_LAUNCH_AUTHORIZATION_SCHEMA",
    "B4_LAUNCH_RELEASE_SCHEMA",
    "B4ControlError",
    "validate_publication_gate",
    "validate_exclusion_registry",
    "historical_repository_sets",
    "validate_candidate_catalog",
    "validate_author_state",
    "build_panel_candidate_plan",
    "prepare_holdout",
    "build_global_binding",
    "build_panel_freeze_receipt",
    "validate_panel_freeze_receipt",
    "freeze_holdout",
    "validate_frozen_holdout",
    "build_public_readiness",
    "validate_public_readiness",
    "build_private_readiness_binding",
    "validate_private_readiness_binding",
    "write_public_readiness",
    "build_launch_authorization",
    "validate_launch_authorization",
    "create_launch_authorization",
    "validate_boundary_receipt",
    "reconcile_attempt_boundary",
    "run_formal_replication",
    "reset_preboundary_launch_state",
    "closeout_interrupted_failure",
    "aggregate_status",
    "run_self_test",
    "run_fault_test",
]
