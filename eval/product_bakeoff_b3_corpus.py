#!/usr/bin/env python3
"""Fresh B3 holdout admission, freeze, and launch authorization.

All repository, task, query, oracle, runner-profile, and private digest material
remains outside the checkout.  Public artifacts are admitted only through a
tracked-checkpoint plus green-CI gate.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
import product_bakeoff_b24_corpus as b24c
import product_bakeoff_b25_query_gate as b25q
import product_bakeoff_b3_protocol as b3p
import product_bakeoff_b3_repeatability as b3repeat
import product_bakeoff_b3_runtime_qualification as b3rq
import product_bakeoff_b3_source as b3src
from product_bakeoff_b24_protocol import (
    B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
    B24_REQUEST_TIMEOUT_SECONDS,
)


REPO = Path(__file__).resolve().parents[1]

B3_CORPUS_VERSION = "product_bakeoff_b3_corpus.v1"
B3_CANDIDATE_PLAN_SCHEMA = "product_bakeoff_b2_private_candidate_plan.v1"
B3_HOLDOUT_BINDING_SCHEMA = "product_bakeoff_b3_private_holdout_binding.v1"
B3_FREEZE_RECEIPT_SCHEMA = "product_bakeoff_b3_private_freeze_receipt.v1"
B3_LAUNCH_AUTHORIZATION_SCHEMA = (
    "product_bakeoff_b3_private_launch_authorization.v1"
)
B3_AUTHOR_CHECKPOINT_SCHEMA = "product_bakeoff_b3_author_slot_checkpoint.v1"
B3_AUTHOR_COMPLETE_SCHEMA = "product_bakeoff_b3_author_complete.v1"
B3_HISTORICAL_FRAME_LABELS = ("b2", "b21", "b24", "b25")


class B3CorpusError(ValueError):
    """Fail-closed B3 private corpus/freeze error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value)).hexdigest()


def _repo_slug(value: Any) -> str:
    if not isinstance(value, str) or value.count("/") != 1:
        raise B3CorpusError("repository slug is missing or malformed")
    owner, repo = value.split("/", 1)
    pattern = r"[A-Za-z0-9_.-]+"
    if not re.fullmatch(pattern, owner) or not re.fullmatch(pattern, repo):
        raise B3CorpusError("repository slug is missing or malformed")
    return value.casefold()


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
        raise B3CorpusError("current source checkpoint could not be verified")
    return value


def _paths_overlap(left: Path, right: Path) -> bool:
    left = left.resolve(strict=False)
    right = right.resolve(strict=False)
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def _require_regular_file(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise B3CorpusError(f"B3 {label} is missing or unsafe")
    return path


def _write_private_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B3CorpusError(f"private B3 output already exists: {path.name}")
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
            raise B3CorpusError("private B3 output appeared concurrently")
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


def _write_private_json_replace(path: Path, value: Mapping[str, Any]) -> None:
    """Durably replace a derived private JSON file with canonical bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if target.is_symlink():
        raise B3CorpusError(f"private B3 output is an unsafe link: {path.name}")
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


def validate_private_layout(private_root: Path, runtime_scratch: Path) -> None:
    if _paths_overlap(private_root, REPO):
        raise B3CorpusError("B3 private root must remain outside the checkout")
    if _paths_overlap(private_root, runtime_scratch):
        raise B3CorpusError("runtime scratch must remain separate from private root")


def validate_publication_gate(
    *,
    artifact_path: Path,
    checkpoint: str,
    ci_run_id: int,
    ci_conclusion: str,
    require_current_head: bool,
) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", checkpoint):
        raise B3CorpusError("publication checkpoint must be a full commit SHA")
    if not isinstance(ci_run_id, int) or ci_run_id <= 0:
        raise B3CorpusError("publication CI run id must be positive")
    if ci_conclusion != "success":
        raise B3CorpusError("publication CI must conclude success")
    if require_current_head and _git_head() != checkpoint:
        raise B3CorpusError("checkout is not the publication checkpoint")
    _require_regular_file(Path(artifact_path), "public artifact")
    artifact = Path(artifact_path).resolve(strict=True)
    try:
        relative = artifact.relative_to(REPO.resolve(strict=True)).as_posix()
    except ValueError as exc:
        raise B3CorpusError("public artifact must be tracked inside checkout") from exc
    completed = subprocess.run(
        ["git", "show", f"{checkpoint}:{relative}"],
        cwd=REPO,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise B3CorpusError("public artifact is absent from publication checkpoint")
    frozen_raw = completed.stdout.replace(b"\r\n", b"\n")
    current_raw = artifact.read_bytes().replace(b"\r\n", b"\n")
    if frozen_raw != current_raw:
        raise B3CorpusError("public artifact differs from publication checkpoint")


def historical_repository_sets(
    historical_repo_locks: Mapping[str, Mapping[str, Any]],
) -> tuple[set[str], set[tuple[str, str]], dict[str, str]]:
    if set(historical_repo_locks) != set(B3_HISTORICAL_FRAME_LABELS):
        raise B3CorpusError("historical lock labels must be b2, b21, b24, and b25")
    slugs: set[str] = set()
    identities: set[tuple[str, str]] = set()
    digests: dict[str, str] = {}
    for label in B3_HISTORICAL_FRAME_LABELS:
        validated = b2c.validate_repo_lock(
            dict(historical_repo_locks[label]), require_sources=False
        )
        frame_slugs = {_repo_slug(row["source"]["repo"]) for row in validated["repos"]}
        frame_identities = {
            (_repo_slug(row["source"]["repo"]), row["commit"])
            for row in validated["repos"]
        }
        if len(frame_slugs) != 12 or len(frame_identities) != 12:
            raise B3CorpusError(f"historical {label} frame is not exactly 12 identities")
        if slugs & frame_slugs or identities & frame_identities:
            raise B3CorpusError("historical B3 frames overlap")
        slugs.update(frame_slugs)
        identities.update(frame_identities)
        digests[label] = validated["repo_lock_digest"]
    if len(slugs) != 48 or len(identities) != 48:
        raise B3CorpusError("historical B3 union is not 48 distinct repositories")
    return slugs, identities, digests


def validate_exclusion_registry(raw: Any) -> dict[str, Any]:
    try:
        return b24c.validate_exclusion_registry(raw)
    except b24c.B24CorpusError as exc:
        raise B3CorpusError(str(exc)) from exc


def exclusion_repository_slugs(registry: Mapping[str, Any]) -> set[str]:
    validated = validate_exclusion_registry(dict(registry))
    return {_repo_slug(row["repo"]) for row in validated["repositories"]}


def validate_fresh_candidate_plan(
    candidate_plan: Any,
    *,
    historical_repo_locks: Mapping[str, Mapping[str, Any]],
    exclusion_registry: Mapping[str, Any],
) -> tuple[str, ...]:
    if not isinstance(candidate_plan, dict) or set(candidate_plan) != {
        "schema_version",
        "slots",
    }:
        raise B3CorpusError("candidate plan has non-closed shape")
    if candidate_plan["schema_version"] != B3_CANDIDATE_PLAN_SCHEMA:
        raise B3CorpusError("candidate plan schema mismatch")
    slots = candidate_plan["slots"]
    if not isinstance(slots, list) or len(slots) != 12:
        raise B3CorpusError("candidate plan must contain exactly 12 slots")
    historical_slugs, _, _ = historical_repository_sets(historical_repo_locks)
    excluded_slugs = exclusion_repository_slugs(exclusion_registry)
    expected_slots = {slot.repo_slot for slot in b2p.build_task_slots()}
    seen_slots: set[str] = set()
    candidates: list[str] = []
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"repo_slot", "candidates"}:
            raise B3CorpusError("candidate slot has non-closed shape")
        repo_slot = slot["repo_slot"]
        if repo_slot not in expected_slots or repo_slot in seen_slots:
            raise B3CorpusError("candidate slot is unknown or duplicated")
        seen_slots.add(repo_slot)
        rows = slot["candidates"]
        if not isinstance(rows, list) or len(rows) < 2:
            raise B3CorpusError("each B3 slot requires at least two candidates")
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"repo", "expected_license"}:
                raise B3CorpusError("candidate row has non-closed shape")
            slug = _repo_slug(row["repo"])
            if not isinstance(row["expected_license"], str) or not row[
                "expected_license"
            ].strip():
                raise B3CorpusError("candidate expected license is missing")
            if slug in historical_slugs:
                raise B3CorpusError("historical repository reused in B3 candidate plan")
            if slug in excluded_slugs:
                raise B3CorpusError("excluded repository reused in B3 candidate plan")
            candidates.append(slug)
    if seen_slots != expected_slots:
        raise B3CorpusError("candidate plan slot coverage is incomplete")
    if len(candidates) != len(set(candidates)):
        raise B3CorpusError("candidate repositories repeat across B3 slots")
    return tuple(candidates)


def _slot_candidate_digest(slot: Mapping[str, Any]) -> str:
    return _digest(
        "b3slotplan_",
        {
            "repo_slot": slot["repo_slot"],
            "candidates": list(slot["candidates"]),
        },
    )


def _author_checkpoint_digest(checkpoint: Mapping[str, Any]) -> str:
    payload = dict(checkpoint)
    payload.pop("checkpoint_digest", None)
    return _digest("b3authorcp_", payload)


def _draft_to_dict(draft: Any) -> dict[str, Any]:
    return {
        "slot_id": draft.slot_id,
        "repo_slot": draft.repo_slot,
        "language": draft.language,
        "size_band": draft.size_band,
        "role": draft.role,
        "task_family": draft.task_family,
        "interaction_mode": draft.interaction_mode,
        "oracle_kind": draft.oracle_kind,
        "query": draft.query,
        "positives": [span.to_dict() for span in draft.positives],
        "negatives": [span.to_dict() for span in draft.negatives],
        "support": [relation.to_dict() for relation in draft.support],
    }


def _draft_from_dict(author: Any, raw: Any) -> Any:
    expected = {
        "slot_id",
        "repo_slot",
        "language",
        "size_band",
        "role",
        "task_family",
        "interaction_mode",
        "oracle_kind",
        "query",
        "positives",
        "negatives",
        "support",
    }
    if not isinstance(raw, dict) or set(raw) != expected:
        raise B3CorpusError("B3 author checkpoint draft shape drifted")
    try:
        return author.TaskDraft(
            slot_id=raw["slot_id"],
            repo_slot=raw["repo_slot"],
            language=raw["language"],
            size_band=raw["size_band"],
            role=raw["role"],
            task_family=raw["task_family"],
            interaction_mode=raw["interaction_mode"],
            oracle_kind=raw["oracle_kind"],
            query=raw["query"],
            positives=tuple(author.B2Span.from_dict(row) for row in raw["positives"]),
            negatives=tuple(author.B2Span.from_dict(row) for row in raw["negatives"]),
            support=tuple(
                author.B2SupportRelation.from_dict(row) for row in raw["support"]
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise B3CorpusError("B3 author checkpoint draft is invalid") from exc


def _build_author_checkpoint(
    *,
    author: Any,
    slot: Mapping[str, Any],
    authored: Any,
) -> dict[str, Any]:
    source = authored.repo_row.get("source") or {}
    selected_repo = source.get("repo")
    selected = [
        index
        for index, candidate in enumerate(slot["candidates"], start=1)
        if candidate["repo"] == selected_repo
    ]
    if len(selected) != 1:
        raise B3CorpusError("B3 authored repository is absent from its frozen slot")
    checkpoint: dict[str, Any] = {
        "schema_version": B3_AUTHOR_CHECKPOINT_SCHEMA,
        "repo_slot": slot["repo_slot"],
        "slot_candidate_digest": _slot_candidate_digest(slot),
        "selected_candidate_index": selected[0],
        "repo_row": authored.repo_row,
        "drafts": [_draft_to_dict(draft) for draft in authored.drafts],
        "checkpoint_digest": "",
    }
    checkpoint["checkpoint_digest"] = _author_checkpoint_digest(checkpoint)
    return checkpoint


def _validate_author_checkpoint(
    *,
    author: Any,
    raw: Any,
    slot: Mapping[str, Any],
) -> Any:
    expected = {
        "schema_version",
        "repo_slot",
        "slot_candidate_digest",
        "selected_candidate_index",
        "repo_row",
        "drafts",
        "checkpoint_digest",
    }
    if not isinstance(raw, dict) or set(raw) != expected:
        raise B3CorpusError("B3 author checkpoint shape drifted")
    if raw["schema_version"] != B3_AUTHOR_CHECKPOINT_SCHEMA:
        raise B3CorpusError("B3 author checkpoint schema drifted")
    if raw["repo_slot"] != slot["repo_slot"]:
        raise B3CorpusError("B3 author checkpoint slot drifted")
    if raw["slot_candidate_digest"] != _slot_candidate_digest(slot):
        raise B3CorpusError("B3 author checkpoint candidate plan drifted")
    if raw["checkpoint_digest"] != _author_checkpoint_digest(raw):
        raise B3CorpusError("B3 author checkpoint digest drifted")
    selected = raw["selected_candidate_index"]
    if not isinstance(selected, int) or isinstance(selected, bool):
        raise B3CorpusError("B3 author checkpoint selected candidate is invalid")
    if not 1 <= selected <= len(slot["candidates"]):
        raise B3CorpusError("B3 author checkpoint selected candidate is out of range")
    repo_row = raw["repo_row"]
    if not isinstance(repo_row, dict) or repo_row.get("repo_slot") != slot["repo_slot"]:
        raise B3CorpusError("B3 author checkpoint repository row drifted")
    source = repo_row.get("source") or {}
    candidate = slot["candidates"][selected - 1]
    if source.get("repo") != candidate["repo"]:
        raise B3CorpusError("B3 author checkpoint repository identity drifted")
    if (repo_row.get("license") or {}).get("expected") != candidate[
        "expected_license"
    ]:
        raise B3CorpusError("B3 author checkpoint license binding drifted")
    clone_root = Path(str(source.get("clone_root", "")))
    if (
        clone_root.is_symlink()
        or not clone_root.is_dir()
        or _paths_overlap(clone_root, REPO)
    ):
        raise B3CorpusError("B3 author checkpoint clone root is unsafe")
    try:
        if b2c.git_commit(clone_root) != repo_row.get("commit"):
            raise B3CorpusError("B3 author checkpoint commit drifted")
        b2c.require_git_worktree_clean(clone_root)
        drafts = tuple(_draft_from_dict(author, row) for row in raw["drafts"])
    except b2c.B2CorpusError as exc:
        raise B3CorpusError("B3 author checkpoint source drifted") from exc
    if len(drafts) != 4 or any(draft.repo_slot != slot["repo_slot"] for draft in drafts):
        raise B3CorpusError("B3 author checkpoint task count drifted")
    return author.AuthoredRepo(repo_row=repo_row, drafts=drafts)


def _normalize_cache_clone_roots(
    roots: Sequence[Path], *, private_root: Path
) -> tuple[Path, ...]:
    normalized: list[Path] = []
    for supplied in roots:
        root = Path(supplied)
        candidate = root / "clones" if (root / "clones").is_dir() else root
        if (
            candidate.is_symlink()
            or not candidate.is_dir()
            or _paths_overlap(candidate, REPO)
            or _paths_overlap(candidate, private_root)
        ):
            raise B3CorpusError("B3 authoring cache root is missing or unsafe")
        resolved = candidate.resolve(strict=True)
        if resolved not in normalized:
            normalized.append(resolved)
    return tuple(normalized)


def _prepare_checkpointed_manifests(
    *,
    author: Any,
    slots: Sequence[Mapping[str, Any]],
    private_root: Path,
    cache_clone_roots: Sequence[Path],
) -> dict[str, Any]:
    private_root.mkdir(parents=True, exist_ok=True)
    clone_root = private_root / "clones"
    checkpoints = private_root / "authoring_checkpoints"
    clone_root.mkdir(exist_ok=True)
    checkpoints.mkdir(exist_ok=True)
    authored: list[Any] = []
    resumed = 0
    for slot in slots:
        checkpoint_path = checkpoints / f"{slot['repo_slot']}.json"
        if checkpoint_path.is_file() and not checkpoint_path.is_symlink():
            authored.append(
                _validate_author_checkpoint(
                    author=author,
                    raw=b2c.load_json(checkpoint_path),
                    slot=slot,
                )
            )
            resumed += 1
            continue
        if os.path.lexists(checkpoint_path):
            raise B3CorpusError("B3 author checkpoint path is unsafe")
        prepared = author._prepare_one_repo(
            repo_slot=slot["repo_slot"],
            candidates=slot["candidates"],
            clone_root=clone_root,
            cache_clone_roots=cache_clone_roots,
        )
        checkpoint = _build_author_checkpoint(
            author=author,
            slot=slot,
            authored=prepared,
        )
        _write_private_json_exclusive(checkpoint_path, checkpoint)
        authored.append(prepared)
    repo_lock, task_manifest, oracle_manifest = author._build_manifest_payloads(authored)
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    _write_private_json_replace(repo_path, repo_lock)
    _write_private_json_replace(task_path, task_manifest)
    _write_private_json_replace(oracle_path, oracle_manifest)
    complete = {
        "schema_version": B3_AUTHOR_COMPLETE_SCHEMA,
        "checkpoint_count": len(slots),
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": oracle_manifest["oracle_manifest_digest"],
        "authoring_complete_digest": "",
    }
    complete["authoring_complete_digest"] = _digest("b3author_", complete)
    complete_path = private_root / "b3_private_authoring_complete.json"
    if complete_path.is_file() and not complete_path.is_symlink():
        if b2c.load_json(complete_path) != complete:
            raise B3CorpusError("B3 author completion receipt drifted")
    else:
        _write_private_json_exclusive(complete_path, complete)
    return {
        "author_version": author.B2_AUTHOR_VERSION,
        "repo_lock_path": str(repo_path.resolve()),
        "task_manifest_path": str(task_path.resolve()),
        "oracle_manifest_path": str(oracle_path.resolve()),
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": oracle_manifest["oracle_manifest_digest"],
        "repo_count": len(repo_lock["repos"]),
        "task_count": len(task_manifest["tasks"]),
        "checkpoint_count": len(slots),
        "resumed_checkpoint_count": resumed,
    }


def holdout_binding_digest(binding: Mapping[str, Any]) -> str:
    payload = dict(binding)
    payload.pop("holdout_binding_digest", None)
    return _digest("b3holdout_", payload)


def build_holdout_binding(
    *,
    new_repo_lock: Mapping[str, Any],
    new_task_manifest: Mapping[str, Any],
    new_oracle_manifest: Mapping[str, Any],
    query_report: Mapping[str, Any],
    query_report_path: Path,
    candidate_plan: Mapping[str, Any],
    candidate_plan_path: Path,
    historical_repo_locks: Mapping[str, Mapping[str, Any]],
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry: Mapping[str, Any],
    exclusion_registry_path: Path,
    runtime_public: Mapping[str, Any],
    runtime_public_path: Path,
    runtime_private: Mapping[str, Any],
    runtime_private_path: Path,
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
) -> dict[str, Any]:
    candidates = set(
        validate_fresh_candidate_plan(
            candidate_plan,
            historical_repo_locks=historical_repo_locks,
            exclusion_registry=exclusion_registry,
        )
    )
    new_lock = b2c.validate_repo_lock(dict(new_repo_lock), require_sources=True)
    tasks = b2c.validate_task_manifest(
        dict(new_task_manifest), repo_lock_digest=new_lock["repo_lock_digest"]
    )
    oracle = importlib.import_module("product_bakeoff_b2_oracle")
    oracle.validate_oracle_manifest(
        dict(new_oracle_manifest),
        tasks=tasks,
        repo_lock=new_lock,
        task_manifest_digest=new_task_manifest["task_manifest_digest"],
    )
    query = b25q.validate_report_binding(
        query_report,
        repo_lock_digest=new_lock["repo_lock_digest"],
        task_manifest_digest=new_task_manifest["task_manifest_digest"],
        oracle_manifest_digest=new_oracle_manifest["oracle_manifest_digest"],
    )
    if b3rq.validate_public_report(runtime_public) or b3rq.validate_private_receipt(
        runtime_private
    ):
        raise B3CorpusError("B3 runtime qualification inputs are invalid")
    if runtime_private["public_qualification_digest"] != runtime_public[
        "qualification_digest"
    ]:
        raise B3CorpusError("B3 runtime public/private binding mismatch")
    historical_slugs, historical_identities, historical_digests = (
        historical_repository_sets(historical_repo_locks)
    )
    if set(historical_repo_lock_paths) != set(B3_HISTORICAL_FRAME_LABELS):
        raise B3CorpusError("historical repository lock paths are incomplete")
    excluded_slugs = exclusion_repository_slugs(exclusion_registry)
    selected_slugs: set[str] = set()
    selected_identities: set[tuple[str, str]] = set()
    for row in new_lock["repos"]:
        slug = _repo_slug(row["source"]["repo"])
        identity = (slug, row["commit"])
        if slug not in candidates:
            raise B3CorpusError("selected repository is absent from candidate plan")
        if slug in historical_slugs or identity in historical_identities:
            raise B3CorpusError("selected B3 repository overlaps historical frame")
        if slug in excluded_slugs:
            raise B3CorpusError("selected B3 repository overlaps exclusion registry")
        selected_slugs.add(slug)
        selected_identities.add(identity)
    if len(selected_slugs) != 12 or len(selected_identities) != 12:
        raise B3CorpusError("selected B3 frame is not 12 distinct identities")
    binding: dict[str, Any] = {
        "schema_version": B3_HOLDOUT_BINDING_SCHEMA,
        "corpus_version": B3_CORPUS_VERSION,
        "b3_spec_digest": b3p.spec_digest(),
        "b3_execution_schedule_digest": b3p.execution_schedule_digest(),
        "b3_repeatability_policy_digest": b3repeat.repeatability_policy_digest(),
        "control_source_bundle_digest": b3src.control_source_bundle_digest(),
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_private_receipt_digest": runtime_private["private_receipt_digest"],
        "runtime_public_file_sha256": b2c.file_sha256(runtime_public_path),
        "runtime_private_file_sha256": b2c.file_sha256(runtime_private_path),
        "runtime_publication_checkpoint": runtime_publication_checkpoint,
        "runtime_publication_ci_run_id": runtime_publication_ci_run_id,
        "runtime_publication_ci_conclusion": runtime_publication_ci_conclusion,
        "new_repo_lock_digest": new_lock["repo_lock_digest"],
        "new_task_manifest_digest": new_task_manifest["task_manifest_digest"],
        "new_oracle_manifest_digest": new_oracle_manifest["oracle_manifest_digest"],
        "query_gate_digest": query["query_gate_digest"],
        "query_gate_file_sha256": b2c.file_sha256(query_report_path),
        "candidate_plan_file_sha256": b2c.file_sha256(candidate_plan_path),
        "historical_repo_lock_digests": {
            label: historical_digests[label] for label in B3_HISTORICAL_FRAME_LABELS
        },
        "historical_repo_lock_file_sha256": {
            label: b2c.file_sha256(historical_repo_lock_paths[label])
            for label in B3_HISTORICAL_FRAME_LABELS
        },
        "exclusion_registry_file_sha256": b2c.file_sha256(exclusion_registry_path),
        "historical_repository_count": len(historical_slugs),
        "excluded_repository_count": len(excluded_slugs),
        "excluded_synthetic_source_count": len(exclusion_registry["synthetic_sources"]),
        "new_repository_count": len(selected_slugs),
        "new_task_count": len(tasks),
        "selected_candidate_membership_count": len(selected_slugs),
        "historical_repository_slug_overlap_count": 0,
        "historical_repository_identity_overlap_count": 0,
        "exclusion_registry_overlap_count": 0,
        "all_queries_tokenizable": True,
        "all_positive_spans_compatible": True,
        "b25_private_holdout_or_output_reused": False,
        "holdout_binding_digest": "",
    }
    binding["holdout_binding_digest"] = holdout_binding_digest(binding)
    return binding


def validate_holdout_binding(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_holdout_binding(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B3CorpusError("B3 holdout binding drifted from private inputs")
    return raw


def prepare_fresh_holdout(
    *,
    candidate_plan_path: Path,
    private_root: Path,
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
    private_root = Path(private_root)
    validate_private_layout(private_root, runtime_scratch)
    allowed_private_entries = {
        "clones",
        "authoring_checkpoints",
        "b2_private_repo_lock.json",
        "b2_private_task_manifest.json",
        "b2_private_oracle_manifest.json",
        "b3_private_authoring_complete.json",
        "b3_private_query_compatibility.json",
        "b3_private_holdout_binding.json",
    }
    if private_root.exists():
        if private_root.is_symlink() or not private_root.is_dir():
            raise B3CorpusError("B3 private root is missing or unsafe")
        unexpected = {path.name for path in private_root.iterdir()} - allowed_private_entries
        if unexpected:
            raise B3CorpusError("B3 private root contains unexpected authoring state")
    validate_publication_gate(
        artifact_path=runtime_public_path,
        checkpoint=runtime_publication_checkpoint,
        ci_run_id=runtime_publication_ci_run_id,
        ci_conclusion=runtime_publication_ci_conclusion,
        require_current_head=True,
    )
    runtime_public, runtime_private = b3rq.validate_runtime_binding(
        public_report_path=runtime_public_path,
        private_receipt_path=runtime_private_path,
        cli_path=cli_path,
        scratch_root=runtime_scratch,
    )
    try:
        Path(runtime_scratch).rmdir()
    except OSError as exc:
        raise B3CorpusError("B3 authoring runtime scratch was not empty") from exc
    _require_regular_file(candidate_plan_path, "candidate plan")
    _require_regular_file(exclusion_registry_path, "exclusion registry")
    if set(historical_repo_lock_paths) != set(B3_HISTORICAL_FRAME_LABELS):
        raise B3CorpusError("historical repository lock paths are incomplete")
    for label, path in historical_repo_lock_paths.items():
        _require_regular_file(path, f"historical {label} repository lock")
    candidate_plan = b2c.load_json(candidate_plan_path)
    historical_locks = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in B3_HISTORICAL_FRAME_LABELS
    }
    registry = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    validate_fresh_candidate_plan(
        candidate_plan,
        historical_repo_locks=historical_locks,
        exclusion_registry=registry,
    )
    author = importlib.import_module("product_bakeoff_b2_author")
    if getattr(author, "B2_CANDIDATE_PLAN_SCHEMA", None) != B3_CANDIDATE_PLAN_SCHEMA:
        raise B3CorpusError("candidate plan schema drifted from frozen author")
    slots = author._validate_candidate_plan(candidate_plan)
    cache_clone_roots = _normalize_cache_clone_roots(
        authoring_cache_roots,
        private_root=private_root,
    )
    result = _prepare_checkpointed_manifests(
        author=author,
        slots=slots,
        private_root=private_root,
        cache_clone_roots=cache_clone_roots,
    )
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    query_path = private_root / "b3_private_query_compatibility.json"
    binding_path = private_root / "b3_private_holdout_binding.json"
    query_report = b25q.build_query_compatibility_report(
        repo_lock=b2c.load_json(repo_path),
        task_manifest=b2c.load_json(task_path),
        oracle_manifest=b2c.load_json(oracle_path),
    )
    if query_path.is_file() and not query_path.is_symlink():
        if b2c.load_json(query_path) != query_report:
            raise B3CorpusError("B3 private query compatibility report drifted")
    else:
        b25q.write_private_report(query_path, query_report)
    binding = build_holdout_binding(
        new_repo_lock=b2c.load_json(repo_path),
        new_task_manifest=b2c.load_json(task_path),
        new_oracle_manifest=b2c.load_json(oracle_path),
        query_report=query_report,
        query_report_path=query_path,
        candidate_plan=candidate_plan,
        candidate_plan_path=candidate_plan_path,
        historical_repo_locks=historical_locks,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry=registry,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public=runtime_public,
        runtime_public_path=runtime_public_path,
        runtime_private=runtime_private,
        runtime_private_path=runtime_private_path,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
    )
    if binding_path.is_file() and not binding_path.is_symlink():
        if b2c.load_json(binding_path) != binding:
            raise B3CorpusError("B3 private holdout binding drifted")
    else:
        _write_private_json_exclusive(binding_path, binding)
    return {
        **result,
        "repo_count": 12,
        "task_count": 48,
        "query_gate_passed": True,
        "holdout_binding_path": str(binding_path.resolve()),
    }


def runtime_bundle_digest(
    cli_path: Path,
    *,
    runtime_qualification_digest: str,
    runtime_private_receipt_digest: str,
) -> str:
    cli = Path(cli_path).resolve(strict=True)
    if cli.is_symlink() or not cli.is_file():
        raise B3CorpusError("OpenLocus CLI path is missing or unsafe")
    return _digest(
        "b3run_",
        {
            "control_source_bundle_digest": b3src.control_source_bundle_digest(),
            "cli_bytes": cli.stat().st_size,
            "cli_sha256": b2c.file_sha256(cli),
            "runtime_qualification_digest": runtime_qualification_digest,
            "runtime_private_receipt_digest": runtime_private_receipt_digest,
            "execution_schedule_digest": b3p.execution_schedule_digest(),
            "repeatability_policy_digest": b3repeat.repeatability_policy_digest(),
            "request_timeout_seconds": B24_REQUEST_TIMEOUT_SECONDS,
            "adapter_command_timeout_seconds": B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
        },
    )


def build_freeze_receipt(
    *,
    repo_lock_digest: str,
    task_manifest_digest: str,
    oracle_manifest_digest: str,
    holdout_binding_digest_value: str,
    query_gate_digest_value: str,
    runtime_qualification_digest: str,
    runtime_private_receipt_digest: str,
    repo_lock_path: Path,
    task_manifest_path: Path,
    oracle_manifest_path: Path,
    holdout_binding_path: Path,
    query_report_path: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    cli_path: Path,
) -> dict[str, Any]:
    if set(historical_repo_lock_paths) != set(B3_HISTORICAL_FRAME_LABELS):
        raise B3CorpusError("historical repository lock paths are incomplete")
    receipt: dict[str, Any] = {
        "schema_version": B3_FREEZE_RECEIPT_SCHEMA,
        "b3_spec_digest": b3p.spec_digest(),
        "b3_execution_schedule_digest": b3p.execution_schedule_digest(),
        "b21_execution_schedule_digest": b3p.execution_schedule_digest(),
        "b3_expected_observation_plan_digest": b3p.expected_observation_plan_digest(),
        "b3_repeatability_policy_digest": b3repeat.repeatability_policy_digest(),
        "control_source_bundle_digest": b3src.control_source_bundle_digest(),
        "runtime_qualification_digest": runtime_qualification_digest,
        "runtime_private_receipt_digest": runtime_private_receipt_digest,
        "repo_lock_digest": repo_lock_digest,
        "task_manifest_digest": task_manifest_digest,
        "oracle_manifest_digest": oracle_manifest_digest,
        "holdout_binding_digest": holdout_binding_digest_value,
        "query_gate_digest": query_gate_digest_value,
        "repo_lock_file_sha256": b2c.file_sha256(repo_lock_path),
        "task_manifest_file_sha256": b2c.file_sha256(task_manifest_path),
        "oracle_manifest_file_sha256": b2c.file_sha256(oracle_manifest_path),
        "holdout_binding_file_sha256": b2c.file_sha256(holdout_binding_path),
        "query_gate_file_sha256": b2c.file_sha256(query_report_path),
        "candidate_plan_file_sha256": b2c.file_sha256(candidate_plan_path),
        "historical_repo_lock_file_sha256": {
            label: b2c.file_sha256(historical_repo_lock_paths[label])
            for label in B3_HISTORICAL_FRAME_LABELS
        },
        "exclusion_registry_file_sha256": b2c.file_sha256(exclusion_registry_path),
        "runtime_public_file_sha256": b2c.file_sha256(runtime_public_path),
        "runtime_private_file_sha256": b2c.file_sha256(runtime_private_path),
        "request_timeout_seconds": B24_REQUEST_TIMEOUT_SECONDS,
        "adapter_command_timeout_seconds": B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
        "runtime_bundle_digest": runtime_bundle_digest(
            cli_path,
            runtime_qualification_digest=runtime_qualification_digest,
            runtime_private_receipt_digest=runtime_private_receipt_digest,
        ),
        "historical_repository_count": 48,
        "new_repository_count": 12,
        "new_task_count": 48,
        "treatment_output_exists_at_freeze": False,
        "freeze_receipt_digest": "",
    }
    receipt["freeze_receipt_digest"] = _digest("b3freeze_", receipt)
    return receipt


def validate_freeze_receipt(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_freeze_receipt(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B3CorpusError("B3 freeze receipt drifted from locked inputs/runtime")
    return raw


def _private_paths(private_root: Path) -> dict[str, Path]:
    return {
        "repo": private_root / "b2_private_repo_lock.json",
        "task": private_root / "b2_private_task_manifest.json",
        "oracle": private_root / "b2_private_oracle_manifest.json",
        "query": private_root / "b3_private_query_compatibility.json",
        "binding": private_root / "b3_private_holdout_binding.json",
        "freeze": private_root / "b3_private_freeze_receipt.json",
        "authorization": private_root / "b3_private_launch_authorization.json",
    }


def _freeze_kwargs(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_public_path: Path,
    runtime_private_path: Path,
    cli_path: Path,
    runtime_public: Mapping[str, Any],
    runtime_private: Mapping[str, Any],
) -> dict[str, Any]:
    paths = _private_paths(private_root)
    for path, label in (
        (paths["repo"], "private repository lock"),
        (paths["task"], "private task manifest"),
        (paths["oracle"], "private oracle manifest"),
        (paths["query"], "private query report"),
        (paths["binding"], "private holdout binding"),
        (candidate_plan_path, "candidate plan"),
        (exclusion_registry_path, "exclusion registry"),
        (runtime_public_path, "runtime public report"),
        (runtime_private_path, "runtime private receipt"),
        (cli_path, "OpenLocus CLI"),
    ):
        _require_regular_file(Path(path), label)
    for label, path in historical_repo_lock_paths.items():
        _require_regular_file(Path(path), f"historical {label} repository lock")
    repo = b2c.load_json(paths["repo"])
    task = b2c.load_json(paths["task"])
    oracle = b2c.load_json(paths["oracle"])
    query = b2c.load_json(paths["query"])
    binding = b2c.load_json(paths["binding"])
    return {
        "repo_lock_digest": repo["repo_lock_digest"],
        "task_manifest_digest": task["task_manifest_digest"],
        "oracle_manifest_digest": oracle["oracle_manifest_digest"],
        "holdout_binding_digest_value": binding["holdout_binding_digest"],
        "query_gate_digest_value": query["query_gate_digest"],
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_private_receipt_digest": runtime_private["private_receipt_digest"],
        "repo_lock_path": paths["repo"],
        "task_manifest_path": paths["task"],
        "oracle_manifest_path": paths["oracle"],
        "holdout_binding_path": paths["binding"],
        "query_report_path": paths["query"],
        "candidate_plan_path": candidate_plan_path,
        "historical_repo_lock_paths": historical_repo_lock_paths,
        "exclusion_registry_path": exclusion_registry_path,
        "runtime_public_path": runtime_public_path,
        "runtime_private_path": runtime_private_path,
        "cli_path": cli_path,
    }


def _validate_authored_state(
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
    cli_path: Path,
) -> dict[str, Any]:
    private_root = Path(private_root)
    validate_private_layout(private_root, runtime_scratch)
    validate_publication_gate(
        artifact_path=runtime_public_path,
        checkpoint=runtime_publication_checkpoint,
        ci_run_id=runtime_publication_ci_run_id,
        ci_conclusion=runtime_publication_ci_conclusion,
        require_current_head=True,
    )
    runtime_public, runtime_private = b3rq.validate_runtime_binding(
        public_report_path=runtime_public_path,
        private_receipt_path=runtime_private_path,
        cli_path=cli_path,
        scratch_root=runtime_scratch,
    )
    try:
        Path(runtime_scratch).rmdir()
    except OSError as exc:
        raise B3CorpusError("B3 freeze validation scratch was not empty") from exc
    kwargs = _freeze_kwargs(
        private_root=private_root,
        candidate_plan_path=candidate_plan_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        cli_path=cli_path,
        runtime_public=runtime_public,
        runtime_private=runtime_private,
    )
    paths = _private_paths(private_root)
    repo = b2c.load_json(paths["repo"])
    task = b2c.load_json(paths["task"])
    oracle = b2c.load_json(paths["oracle"])
    query = b2c.load_json(paths["query"])
    binding = b2c.load_json(paths["binding"])
    candidate = b2c.load_json(candidate_plan_path)
    histories = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in B3_HISTORICAL_FRAME_LABELS
    }
    registry = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    recomputed_query = b25q.build_query_compatibility_report(
        repo_lock=repo, task_manifest=task, oracle_manifest=oracle
    )
    if recomputed_query != query:
        raise B3CorpusError("B3 query compatibility drifted")
    validate_holdout_binding(
        binding,
        new_repo_lock=repo,
        new_task_manifest=task,
        new_oracle_manifest=oracle,
        query_report=query,
        query_report_path=paths["query"],
        candidate_plan=candidate,
        candidate_plan_path=candidate_plan_path,
        historical_repo_locks=histories,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry=registry,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public=runtime_public,
        runtime_public_path=runtime_public_path,
        runtime_private=runtime_private,
        runtime_private_path=runtime_private_path,
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
    )
    return {
        "paths": paths,
        "repo_lock": repo,
        "task_manifest": task,
        "oracle_manifest": oracle,
        "query_report": query,
        "binding": binding,
        "runtime_public": runtime_public,
        "runtime_private": runtime_private,
        "freeze_kwargs": kwargs,
    }


def validate_frozen_state(
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
    cli_path: Path,
) -> dict[str, Any]:
    state = _validate_authored_state(
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
    freeze = validate_freeze_receipt(
        b2c.load_json(state["paths"]["freeze"]), **state["freeze_kwargs"]
    )
    return {**state, "freeze": freeze}


def validate_run_admission_state(
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
    cli_path: Path,
) -> dict[str, Any]:
    """Validate frozen bytes at RUN admission without importing author/oracle/scorer."""

    private_root = Path(private_root)
    if _paths_overlap(private_root, REPO) or _paths_overlap(runtime_scratch, REPO):
        raise B3CorpusError("B3 RUN private paths must remain outside checkout")
    validate_publication_gate(
        artifact_path=runtime_public_path,
        checkpoint=runtime_publication_checkpoint,
        ci_run_id=runtime_publication_ci_run_id,
        ci_conclusion=runtime_publication_ci_conclusion,
        require_current_head=False,
    )
    runtime_public, runtime_private = b3rq.validate_runtime_binding(
        public_report_path=runtime_public_path,
        private_receipt_path=runtime_private_path,
        cli_path=cli_path,
        scratch_root=runtime_scratch,
    )
    try:
        Path(runtime_scratch).rmdir()
    except OSError as exc:
        raise B3CorpusError("B3 RUN admission scratch was not empty") from exc
    freeze_kwargs = _freeze_kwargs(
        private_root=private_root,
        candidate_plan_path=candidate_plan_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_public_path=runtime_public_path,
        runtime_private_path=runtime_private_path,
        cli_path=cli_path,
        runtime_public=runtime_public,
        runtime_private=runtime_private,
    )
    paths = _private_paths(private_root)
    repo = b2c.load_json(paths["repo"])
    task = b2c.load_json(paths["task"])
    oracle = b2c.load_json(paths["oracle"])
    query = b2c.load_json(paths["query"])
    binding = b2c.load_json(paths["binding"])
    b25q.validate_report_binding(
        query,
        repo_lock_digest=repo["repo_lock_digest"],
        task_manifest_digest=task["task_manifest_digest"],
        oracle_manifest_digest=oracle["oracle_manifest_digest"],
    )
    if binding.get("schema_version") != B3_HOLDOUT_BINDING_SCHEMA:
        raise B3CorpusError("B3 RUN holdout binding schema drifted")
    if binding.get("holdout_binding_digest") != holdout_binding_digest(binding):
        raise B3CorpusError("B3 RUN holdout binding digest drifted")
    exact_binding = {
        "b3_spec_digest": b3p.spec_digest(),
        "b3_execution_schedule_digest": b3p.execution_schedule_digest(),
        "b3_repeatability_policy_digest": b3repeat.repeatability_policy_digest(),
        "control_source_bundle_digest": b3src.control_source_bundle_digest(),
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_private_receipt_digest": runtime_private["private_receipt_digest"],
        "new_repo_lock_digest": repo["repo_lock_digest"],
        "new_task_manifest_digest": task["task_manifest_digest"],
        "new_oracle_manifest_digest": oracle["oracle_manifest_digest"],
        "query_gate_digest": query["query_gate_digest"],
        "historical_repository_count": 48,
        "new_repository_count": 12,
        "new_task_count": 48,
        "historical_repository_slug_overlap_count": 0,
        "historical_repository_identity_overlap_count": 0,
        "exclusion_registry_overlap_count": 0,
        "b25_private_holdout_or_output_reused": False,
    }
    for key, expected in exact_binding.items():
        if binding.get(key) != expected:
            raise B3CorpusError(f"B3 RUN holdout binding field drifted: {key}")
    file_bindings = {
        "query_gate_file_sha256": b2c.file_sha256(paths["query"]),
        "candidate_plan_file_sha256": b2c.file_sha256(candidate_plan_path),
        "exclusion_registry_file_sha256": b2c.file_sha256(exclusion_registry_path),
        "runtime_public_file_sha256": b2c.file_sha256(runtime_public_path),
        "runtime_private_file_sha256": b2c.file_sha256(runtime_private_path),
    }
    for key, expected in file_bindings.items():
        if binding.get(key) != expected:
            raise B3CorpusError(f"B3 RUN private file binding drifted: {key}")
    expected_history_hashes = {
        label: b2c.file_sha256(historical_repo_lock_paths[label])
        for label in B3_HISTORICAL_FRAME_LABELS
    }
    if binding.get("historical_repo_lock_file_sha256") != expected_history_hashes:
        raise B3CorpusError("B3 RUN historical lock bytes drifted")
    freeze = validate_freeze_receipt(b2c.load_json(paths["freeze"]), **freeze_kwargs)
    return {
        "paths": paths,
        "repo_lock": repo,
        "task_manifest": task,
        "oracle_manifest": oracle,
        "query_report": query,
        "binding": binding,
        "freeze": freeze,
        "runtime_public": runtime_public,
        "runtime_private": runtime_private,
        "freeze_kwargs": freeze_kwargs,
    }


def freeze_fresh_holdout(**kwargs: Any) -> dict[str, Any]:
    private_root = Path(kwargs["private_root"])
    paths = _private_paths(private_root)
    if os.path.lexists(paths["freeze"]):
        raise B3CorpusError("B3 freeze receipt already exists")
    state = _validate_authored_state(**kwargs)
    receipt = build_freeze_receipt(**state["freeze_kwargs"])
    _write_private_json_exclusive(paths["freeze"], receipt)
    validate_freeze_receipt(
        b2c.load_json(paths["freeze"]), **state["freeze_kwargs"]
    )
    return {**receipt, "freeze_receipt_path": str(paths["freeze"].resolve())}


def launch_authorization_digest(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("launch_authorization_digest", None)
    return _digest("b3launch_", payload)


def build_launch_authorization(
    *,
    freeze_receipt: Mapping[str, Any],
    freeze_receipt_path: Path,
    readiness_report: Mapping[str, Any],
    readiness_report_path: Path,
    readiness_checkpoint: str,
    readiness_ci_run_id: int,
    readiness_ci_conclusion: str,
) -> dict[str, Any]:
    readiness = importlib.import_module("product_bakeoff_b3_readiness")
    if readiness.validate_public_readiness(dict(readiness_report)):
        raise B3CorpusError("B3 public readiness report is invalid")
    validate_publication_gate(
        artifact_path=readiness_report_path,
        checkpoint=readiness_checkpoint,
        ci_run_id=readiness_ci_run_id,
        ci_conclusion=readiness_ci_conclusion,
        require_current_head=True,
    )
    decision = readiness_report["decision"]
    if decision["private_holdout_frozen"] is not True:
        raise B3CorpusError("B3 readiness did not freeze the holdout")
    if decision["treatment_output_exists"] is not False:
        raise B3CorpusError("B3 readiness already contains treatment output")
    authorization: dict[str, Any] = {
        "schema_version": B3_LAUNCH_AUTHORIZATION_SCHEMA,
        "b3_spec_digest": b3p.spec_digest(),
        "control_source_bundle_digest": freeze_receipt[
            "control_source_bundle_digest"
        ],
        "runtime_bundle_digest": freeze_receipt["runtime_bundle_digest"],
        "runtime_qualification_digest": freeze_receipt[
            "runtime_qualification_digest"
        ],
        "freeze_receipt_digest": freeze_receipt["freeze_receipt_digest"],
        "freeze_receipt_file_sha256": b2c.file_sha256(freeze_receipt_path),
        "readiness_report_digest": readiness_report["readiness_digest"],
        "readiness_report_file_sha256": b2c.file_sha256(readiness_report_path),
        "readiness_checkpoint": readiness_checkpoint,
        "readiness_ci_run_id": readiness_ci_run_id,
        "readiness_ci_conclusion": readiness_ci_conclusion,
        "tournament_attempt_number": 1,
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
        raise B3CorpusError("B3 launch authorization drifted")
    return raw


def create_launch_authorization(
    *,
    private_root: Path,
    readiness_report_path: Path,
    readiness_checkpoint: str,
    readiness_ci_run_id: int,
    readiness_ci_conclusion: str,
) -> dict[str, Any]:
    paths = _private_paths(Path(private_root))
    if os.path.lexists(paths["authorization"]):
        raise B3CorpusError("B3 launch authorization already exists")
    _require_regular_file(paths["freeze"], "private freeze receipt")
    _require_regular_file(readiness_report_path, "public readiness report")
    freeze = b2c.load_json(paths["freeze"])
    readiness = b2c.load_json(readiness_report_path)
    authorization = build_launch_authorization(
        freeze_receipt=freeze,
        freeze_receipt_path=paths["freeze"],
        readiness_report=readiness,
        readiness_report_path=readiness_report_path,
        readiness_checkpoint=readiness_checkpoint,
        readiness_ci_run_id=readiness_ci_run_id,
        readiness_ci_conclusion=readiness_ci_conclusion,
    )
    _write_private_json_exclusive(paths["authorization"], authorization)
    return {
        **authorization,
        "launch_authorization_path": str(paths["authorization"].resolve()),
    }


def _synthetic_locks() -> dict[str, dict[str, Any]]:
    return {
        "b2": b24c._synthetic_lock("b2old"),
        "b21": b24c._synthetic_lock("b21old"),
        "b24": b24c._synthetic_lock("b24old"),
        "b25": b24c._synthetic_lock("b25old"),
    }


def _synthetic_registry() -> dict[str, Any]:
    return b24c._synthetic_registry()


def _synthetic_candidate_plan(first_slug: str | None = None) -> dict[str, Any]:
    slots = []
    for index, repo_slot in enumerate(sorted({row.repo_slot for row in b2p.build_task_slots()})):
        candidates = [
            {
                "repo": first_slug if index == 0 and offset == 0 and first_slug else f"new{index:02d}/repo{offset}",
                "expected_license": "MIT",
            }
            for offset in range(2)
        ]
        slots.append({"repo_slot": repo_slot, "candidates": candidates})
    return {"schema_version": B3_CANDIDATE_PLAN_SCHEMA, "slots": slots}


def run_self_test() -> dict[str, Any]:
    histories = _synthetic_locks()
    registry = _synthetic_registry()
    slugs, identities, _ = historical_repository_sets(histories)
    candidates = validate_fresh_candidate_plan(
        _synthetic_candidate_plan(),
        historical_repo_locks=histories,
        exclusion_registry=registry,
    )
    checks = {
        "four_historical_frames": len(histories) == 4,
        "historical_slug_count_48": len(slugs) == 48,
        "historical_identity_count_48": len(identities) == 48,
        "candidate_count_24": len(candidates) == 24,
        "candidate_unique": len(candidates) == len(set(candidates)),
        "boundary_policy_bound": b3p.B3_EXECUTION_BOUNDARY["attempt_boundary"]
        == "first_durable_treatment_observation",
    }
    with tempfile.TemporaryDirectory(prefix="openlocus-b3-freeze-") as temporary:
        root = Path(temporary)
        files: list[Path] = []
        for index in range(13):
            path = root / f"f{index}.json"
            path.write_text("{}\n", encoding="utf-8")
            files.append(path)
        cli = root / "openlocus.bin"
        cli.write_bytes(b"b3-test-runtime")
        freeze_kwargs = {
            "repo_lock_digest": "b2repos_" + "1" * 64,
            "task_manifest_digest": "b2tasks_" + "2" * 64,
            "oracle_manifest_digest": "b2oracles_" + "3" * 64,
            "holdout_binding_digest_value": "b3holdout_" + "4" * 64,
            "query_gate_digest_value": "b25query_" + "5" * 64,
            "runtime_qualification_digest": "b3qual_" + "6" * 64,
            "runtime_private_receipt_digest": "b3qpriv_" + "7" * 64,
            "repo_lock_path": files[0],
            "task_manifest_path": files[1],
            "oracle_manifest_path": files[2],
            "holdout_binding_path": files[3],
            "query_report_path": files[4],
            "candidate_plan_path": files[5],
            "historical_repo_lock_paths": {
                "b2": files[6],
                "b21": files[7],
                "b24": files[8],
                "b25": files[9],
            },
            "exclusion_registry_path": files[10],
            "runtime_public_path": files[11],
            "runtime_private_path": files[12],
            "cli_path": cli,
        }
        freeze = build_freeze_receipt(**freeze_kwargs)
        checks["freeze_roundtrip"] = (
            validate_freeze_receipt(freeze, **freeze_kwargs) == freeze
        )
        checks["runtime_bundle_bound"] = freeze["runtime_bundle_digest"].startswith(
            "b3run_"
        )
        readiness = importlib.import_module("product_bakeoff_b3_readiness")
        readiness_report = readiness._build_report(
            runtime_publication_checkpoint="a" * 40,
            runtime_publication_ci_run_id=1,
            runtime_publication_ci_conclusion="success",
            runtime_qualification_digest="b3qual_" + "6" * 64,
            runtime_public_file_sha256="8" * 64,
            historical_repository_count=48,
            excluded_repository_count=2,
            excluded_synthetic_source_count=2,
            query_gate=readiness._synthetic_query_gate(),
            observed_margins=readiness._frozen_margins(),
        )
        freeze_path = root / "freeze.json"
        readiness_path = root / "readiness.json"
        b2c.write_json(freeze_path, freeze)
        b2c.write_json(readiness_path, readiness_report)
        original_gate = globals()["validate_publication_gate"]
        globals()["validate_publication_gate"] = lambda **_: None
        try:
            authorization_kwargs = {
                "freeze_receipt": freeze,
                "freeze_receipt_path": freeze_path,
                "readiness_report": readiness_report,
                "readiness_report_path": readiness_path,
                "readiness_checkpoint": "b" * 40,
                "readiness_ci_run_id": 2,
                "readiness_ci_conclusion": "success",
            }
            authorization = build_launch_authorization(**authorization_kwargs)
            checks["launch_authorization_roundtrip"] = (
                validate_launch_authorization(authorization, **authorization_kwargs)
                == authorization
            )
            checks["launch_release_not_boundary"] = (
                authorization["launch_release_alone_consumes_attempt"] is False
            )
        finally:
            globals()["validate_publication_gate"] = original_gate
        author = importlib.import_module("product_bakeoff_b2_author")
        cache_root = root / "candidate-cache"
        cache_repo = author._candidate_destination(
            cache_root,
            repo_slot="b2_repo_python_small",
            candidate_index=1,
            repo_slug="example/checkpoint-cache",
        )
        cache_repo.mkdir(parents=True)
        author._synthetic_python_repo(cache_repo)
        (cache_repo / "LICENSE").write_text(
            "Permission is hereby granted, free of charge, to any person obtaining a copy.\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=cache_repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "b3-checkpoint@example.invalid"],
            cwd=cache_repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "B3 Checkpoint Test"],
            cwd=cache_repo,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=cache_repo, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "checkpoint fixture"],
            cwd=cache_repo,
            check=True,
        )
        checkpoint_slot = {
            "repo_slot": "b2_repo_python_small",
            "candidates": [
                {"repo": "example/checkpoint-cache", "expected_license": "MIT"},
                {"repo": "example/checkpoint-fallback", "expected_license": "MIT"},
            ],
        }
        checkpoint_authored = author._author_existing_candidate(
            repo_slot=checkpoint_slot["repo_slot"],
            candidate=checkpoint_slot["candidates"][0],
            root=cache_repo,
        )
        original_clone = author.clone_public_repo
        author.clone_public_repo = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("verified cache unexpectedly recloned")
        )
        try:
            cached_authored = author._prepare_one_repo(
                repo_slot=checkpoint_slot["repo_slot"],
                candidates=checkpoint_slot["candidates"],
                clone_root=root / "unused-clone-root",
                cache_clone_roots=(cache_root,),
            )
        finally:
            author.clone_public_repo = original_clone
        checks["verified_cache_avoids_reclone"] = (
            cached_authored == checkpoint_authored
        )
        fresh_repo = root / "fresh-candidate"
        subprocess.run(
            ["git", "clone", "-q", str(cache_repo), str(fresh_repo)],
            check=True,
        )
        cache_tracked = cache_repo / "pkg" / "alpha.py"
        cache_tracked_original = cache_tracked.read_bytes()
        cache_tracked.write_bytes(cache_tracked_original + b"# cache drift\n")
        fresh_clone_calls = 0

        def fake_clone(_repo: str, _destination: Path) -> Path:
            nonlocal fresh_clone_calls
            fresh_clone_calls += 1
            return fresh_repo

        original_clone = author.clone_public_repo
        author.clone_public_repo = fake_clone
        try:
            fallback_authored = author._prepare_one_repo(
                repo_slot=checkpoint_slot["repo_slot"],
                candidates=checkpoint_slot["candidates"],
                clone_root=root / "fresh-clone-root",
                cache_clone_roots=(cache_root,),
            )
        finally:
            author.clone_public_repo = original_clone
            cache_tracked.write_bytes(cache_tracked_original)
        checks["invalid_cache_falls_back_without_reselection"] = (
            fresh_clone_calls == 1
            and Path(fallback_authored.repo_row["source"]["clone_root"])
            == fresh_repo.resolve()
            and fallback_authored.repo_row["source"]["repo"]
            == checkpoint_slot["candidates"][0]["repo"]
        )
        checkpoint = _build_author_checkpoint(
            author=author,
            slot=checkpoint_slot,
            authored=checkpoint_authored,
        )
        resumed = _validate_author_checkpoint(
            author=author,
            raw=checkpoint,
            slot=checkpoint_slot,
        )
        checks["slot_checkpoint_roundtrip"] = (
            resumed.repo_row == checkpoint_authored.repo_row
            and resumed.drafts == checkpoint_authored.drafts
        )
        checks["slot_checkpoint_plan_local"] = checkpoint[
            "slot_candidate_digest"
        ] == _slot_candidate_digest(checkpoint_slot)
        original_prepare = author._prepare_one_repo
        original_build = author._build_manifest_payloads
        author_calls = 0

        def fake_prepare(**_kwargs: Any) -> Any:
            nonlocal author_calls
            author_calls += 1
            return checkpoint_authored

        def fake_build(_authored: Sequence[Any]) -> tuple[dict[str, Any], ...]:
            return (
                {
                    "repos": [checkpoint_authored.repo_row],
                    "repo_lock_digest": "b2repos_" + "1" * 64,
                },
                {
                    "tasks": [{"slot_id": "checkpoint-task"}],
                    "task_manifest_digest": "b2tasks_" + "2" * 64,
                },
                {"oracle_manifest_digest": "b2oracles_" + "3" * 64},
            )

        resume_root = root / "checkpoint-resume"
        try:
            author._prepare_one_repo = fake_prepare
            author._build_manifest_payloads = fake_build
            first_pass = _prepare_checkpointed_manifests(
                author=author,
                slots=(checkpoint_slot,),
                private_root=resume_root,
                cache_clone_roots=(cache_root,),
            )
            author._prepare_one_repo = lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("completed slot was authored twice")
            )
            second_pass = _prepare_checkpointed_manifests(
                author=author,
                slots=(checkpoint_slot,),
                private_root=resume_root,
                cache_clone_roots=(cache_root,),
            )
        finally:
            author._prepare_one_repo = original_prepare
            author._build_manifest_payloads = original_build
        checks["checkpoint_resume_skips_completed_slot"] = (
            author_calls == 1
            and first_pass["resumed_checkpoint_count"] == 0
            and second_pass["resumed_checkpoint_count"] == 1
            and first_pass["repo_lock_digest"] == second_pass["repo_lock_digest"]
        )
        drift_file = cache_repo / "pkg" / "alpha.py"
        drift_original = drift_file.read_bytes()
        drift_file.write_bytes(drift_original + b"# checkpoint drift\n")
        try:
            _validate_author_checkpoint(
                author=author,
                raw=checkpoint,
                slot=checkpoint_slot,
            )
            checks["checkpoint_source_drift_rejected"] = False
        except B3CorpusError:
            checks["checkpoint_source_drift_rejected"] = True
        finally:
            drift_file.write_bytes(drift_original)
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    histories = _synthetic_locks()
    registry = _synthetic_registry()
    historical_slug = histories["b25"]["repos"][0]["source"]["repo"]
    cases: dict[str, bool] = {}
    try:
        validate_fresh_candidate_plan(
            _synthetic_candidate_plan(historical_slug),
            historical_repo_locks=histories,
            exclusion_registry=registry,
        )
        cases["b25_reuse_rejected"] = False
    except B3CorpusError:
        cases["b25_reuse_rejected"] = True
    overlapping = dict(histories)
    overlapping["b25"] = histories["b24"]
    try:
        historical_repository_sets(overlapping)
        cases["historical_overlap_rejected"] = False
    except B3CorpusError:
        cases["historical_overlap_rejected"] = True
    missing = dict(histories)
    missing.pop("b25")
    try:
        historical_repository_sets(missing)
        cases["missing_history_rejected"] = False
    except B3CorpusError:
        cases["missing_history_rejected"] = True
    synthetic_slot = _synthetic_candidate_plan()["slots"][0]
    synthetic_checkpoint = {
        "schema_version": B3_AUTHOR_CHECKPOINT_SCHEMA,
        "repo_slot": synthetic_slot["repo_slot"],
        "slot_candidate_digest": "b3slotplan_" + "0" * 64,
        "selected_candidate_index": 1,
        "repo_row": {},
        "drafts": [],
        "checkpoint_digest": "b3authorcp_" + "0" * 64,
    }
    try:
        _validate_author_checkpoint(
            author=importlib.import_module("product_bakeoff_b2_author"),
            raw=synthetic_checkpoint,
            slot=synthetic_slot,
        )
        cases["checkpoint_plan_drift_rejected"] = False
    except B3CorpusError:
        cases["checkpoint_plan_drift_rejected"] = True
    failed = sorted(name for name, passed in cases.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(cases),
        "checks_passed": len(cases) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B3CorpusError",
    "B3_HISTORICAL_FRAME_LABELS",
    "build_freeze_receipt",
    "build_launch_authorization",
    "create_launch_authorization",
    "freeze_fresh_holdout",
    "historical_repository_sets",
    "prepare_fresh_holdout",
    "validate_fresh_candidate_plan",
    "validate_freeze_receipt",
    "validate_frozen_state",
    "validate_launch_authorization",
    "validate_run_admission_state",
]
