#!/usr/bin/env python3
"""B2.1 fresh-holdout admission overlay and runtime freeze binding.

The repository scanner, offline task author, task/oracle schemas, and visible
source mirror remain the frozen B2 implementation.  This overlay adds the
B2.1-only requirements: every candidate repository slug must be absent from
the B2 frame, the selected repo/task/oracle manifests must be new, and one
freeze receipt must bind those private inputs to the B2.1 protocol/runtime.

This module does not import the author or oracle at module load so the RUN
phase can validate a receipt without contaminating scorer isolation.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
from product_bakeoff_b21_protocol import (
    B21_PARENT_B2_SPEC_DIGEST,
    b21_execution_schedule_digest,
    b21_source_bundle_digest,
    b21_spec_digest,
    b21_task_frame_digest,
)


B21_CORPUS_VERSION = "product_bakeoff_b21_corpus.v1"
B21_HOLDOUT_BINDING_SCHEMA = "product_bakeoff_b21_private_holdout_binding.v1"
B21_FREEZE_RECEIPT_SCHEMA = "product_bakeoff_b21_private_freeze_receipt.v1"
B21_PREFLIGHT_EXCLUSION_SCHEMA = "product_bakeoff_b21_preflight_exclusions.v1"


class B21CorpusError(ValueError):
    """Fail-closed B2.1 holdout/freeze error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _repo_slug(value: Any) -> str:
    if not isinstance(value, str) or not value or "/" not in value:
        raise B21CorpusError("repository slug is missing or malformed")
    return value.casefold()


def excluded_repository_sets(
    excluded_repo_lock: Mapping[str, Any],
) -> tuple[set[str], set[tuple[str, str]]]:
    validated = b2c.validate_repo_lock(dict(excluded_repo_lock), require_sources=False)
    slugs: set[str] = set()
    identities: set[tuple[str, str]] = set()
    for row in validated["repos"]:
        slug = _repo_slug(row["source"]["repo"])
        slugs.add(slug)
        identities.add((slug, row["commit"]))
    if len(slugs) != 12 or len(identities) != 12:
        raise B21CorpusError("excluded B2 frame is not an exact 12-repository identity set")
    return slugs, identities


def validate_fresh_candidate_plan(
    candidate_plan: Any,
    *,
    excluded_repo_lock: Mapping[str, Any],
    preflight_excluded_slugs: Sequence[str] = (),
) -> tuple[str, ...]:
    if not isinstance(candidate_plan, dict) or set(candidate_plan) != {
        "schema_version",
        "slots",
    }:
        raise B21CorpusError("candidate plan has non-closed shape")
    if candidate_plan["schema_version"] != "product_bakeoff_b2_candidate_plan.v1":
        raise B21CorpusError("candidate plan schema mismatch")
    if not isinstance(candidate_plan["slots"], list) or len(candidate_plan["slots"]) != 12:
        raise B21CorpusError("candidate plan must contain exactly 12 slot rows")
    excluded_slugs, _ = excluded_repository_sets(excluded_repo_lock)
    preflight_slugs = {_repo_slug(slug) for slug in preflight_excluded_slugs}
    seen_slots: set[str] = set()
    candidates: list[str] = []
    for slot in candidate_plan["slots"]:
        if not isinstance(slot, dict) or set(slot) != {"repo_slot", "candidates"}:
            raise B21CorpusError("candidate slot has non-closed shape")
        repo_slot = slot["repo_slot"]
        if not isinstance(repo_slot, str) or repo_slot in seen_slots:
            raise B21CorpusError("candidate slot is missing or duplicated")
        seen_slots.add(repo_slot)
        if not isinstance(slot["candidates"], list) or not slot["candidates"]:
            raise B21CorpusError("candidate slot has no candidates")
        for candidate in slot["candidates"]:
            if not isinstance(candidate, dict) or set(candidate) != {
                "repo",
                "expected_license",
            }:
                raise B21CorpusError("candidate row has non-closed shape")
            slug = _repo_slug(candidate["repo"])
            if slug in excluded_slugs:
                raise B21CorpusError("B2 repository slug reused in B2.1 candidate plan")
            if slug in preflight_slugs:
                raise B21CorpusError("real-preflight repository reused in final B2.1 candidate plan")
            candidates.append(slug)
    if len(seen_slots) != 12:
        raise B21CorpusError("candidate plan slot coverage is incomplete")
    if len(set(candidates)) != len(candidates):
        raise B21CorpusError("candidate repositories must not repeat across B2.1 slots")
    return tuple(candidates)


def load_preflight_exclusions(path: Path) -> tuple[str, ...]:
    raw = b2c.load_json(path)
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "repos"}:
        raise B21CorpusError("preflight exclusion file has non-closed shape")
    if raw["schema_version"] != B21_PREFLIGHT_EXCLUSION_SCHEMA:
        raise B21CorpusError("preflight exclusion schema mismatch")
    if not isinstance(raw["repos"], list) or not raw["repos"]:
        raise B21CorpusError("preflight exclusion repo list must be nonempty")
    slugs = tuple(_repo_slug(item) for item in raw["repos"])
    if tuple(sorted(slugs)) != slugs or len(set(slugs)) != len(slugs):
        raise B21CorpusError("preflight exclusion repos must be sorted and unique")
    return slugs


def holdout_binding_digest(binding: Mapping[str, Any]) -> str:
    payload = dict(binding)
    payload.pop("holdout_binding_digest", None)
    return _prefixed_digest("b21holdout_", payload)


def build_holdout_binding(
    *,
    new_repo_lock: Mapping[str, Any],
    new_task_manifest: Mapping[str, Any],
    new_oracle_manifest: Mapping[str, Any],
    excluded_repo_lock: Mapping[str, Any],
    excluded_repo_lock_path: Path,
    preflight_exclusion_path: Path,
) -> dict[str, Any]:
    new_lock = b2c.validate_repo_lock(dict(new_repo_lock), require_sources=True)
    tasks = b2c.validate_task_manifest(
        dict(new_task_manifest), repo_lock_digest=new_lock["repo_lock_digest"]
    )
    excluded_lock = b2c.validate_repo_lock(dict(excluded_repo_lock), require_sources=False)
    excluded_slugs, excluded_identities = excluded_repository_sets(excluded_lock)
    preflight_slugs = set(load_preflight_exclusions(preflight_exclusion_path))
    new_slugs: set[str] = set()
    new_identities: set[tuple[str, str]] = set()
    for row in new_lock["repos"]:
        slug = _repo_slug(row["source"]["repo"])
        identity = (slug, row["commit"])
        if slug in excluded_slugs or identity in excluded_identities:
            raise B21CorpusError("selected B2.1 repository overlaps the B2 frame")
        if slug in preflight_slugs:
            raise B21CorpusError("selected B2.1 repository overlaps real preflight")
        new_slugs.add(slug)
        new_identities.add(identity)
    if len(new_slugs) != 12 or len(new_identities) != 12:
        raise B21CorpusError("B2.1 selected repository frame is not 12 distinct identities")
    if new_lock["repo_lock_digest"] == excluded_lock["repo_lock_digest"]:
        raise B21CorpusError("B2.1 repo lock must differ from B2")
    if len(tasks) != 48:
        raise B21CorpusError("B2.1 task manifest must contain 48 tasks")
    if new_oracle_manifest.get("task_manifest_digest") != new_task_manifest.get(
        "task_manifest_digest"
    ):
        raise B21CorpusError("B2.1 oracle/task binding mismatch")
    if new_oracle_manifest.get("repo_lock_digest") != new_lock["repo_lock_digest"]:
        raise B21CorpusError("B2.1 oracle/repo binding mismatch")
    binding = {
        "schema_version": B21_HOLDOUT_BINDING_SCHEMA,
        "corpus_version": B21_CORPUS_VERSION,
        "b21_spec_digest": b21_spec_digest(),
        "b21_holdout_frame_digest": b21_task_frame_digest(),
        "parent_task_authoring_spec_digest": B21_PARENT_B2_SPEC_DIGEST,
        "new_repo_lock_digest": new_lock["repo_lock_digest"],
        "new_task_manifest_digest": new_task_manifest["task_manifest_digest"],
        "new_oracle_manifest_digest": new_oracle_manifest["oracle_manifest_digest"],
        "excluded_b2_repo_lock_digest": excluded_lock["repo_lock_digest"],
        "excluded_b2_repo_lock_file_sha256": b2c.file_sha256(excluded_repo_lock_path),
        "preflight_exclusion_file_sha256": b2c.file_sha256(preflight_exclusion_path),
        "preflight_excluded_repository_count": len(preflight_slugs),
        "new_repository_count": len(new_slugs),
        "new_task_count": len(tasks),
        "repository_slug_overlap_count": 0,
        "repository_identity_overlap_count": 0,
        "preflight_repository_overlap_count": 0,
        "holdout_binding_digest": "",
    }
    binding["holdout_binding_digest"] = holdout_binding_digest(binding)
    return binding


def validate_holdout_binding(
    raw: Any,
    *,
    new_repo_lock: Mapping[str, Any],
    new_task_manifest: Mapping[str, Any],
    new_oracle_manifest: Mapping[str, Any],
    excluded_repo_lock: Mapping[str, Any],
    excluded_repo_lock_path: Path,
    preflight_exclusion_path: Path,
) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "corpus_version",
        "b21_spec_digest",
        "b21_holdout_frame_digest",
        "parent_task_authoring_spec_digest",
        "new_repo_lock_digest",
        "new_task_manifest_digest",
        "new_oracle_manifest_digest",
        "excluded_b2_repo_lock_digest",
        "excluded_b2_repo_lock_file_sha256",
        "preflight_exclusion_file_sha256",
        "preflight_excluded_repository_count",
        "new_repository_count",
        "new_task_count",
        "repository_slug_overlap_count",
        "repository_identity_overlap_count",
        "preflight_repository_overlap_count",
        "holdout_binding_digest",
    }:
        raise B21CorpusError("holdout binding has non-closed shape")
    expected = build_holdout_binding(
        new_repo_lock=new_repo_lock,
        new_task_manifest=new_task_manifest,
        new_oracle_manifest=new_oracle_manifest,
        excluded_repo_lock=excluded_repo_lock,
        excluded_repo_lock_path=excluded_repo_lock_path,
        preflight_exclusion_path=preflight_exclusion_path,
    )
    if raw != expected:
        raise B21CorpusError("holdout binding drifted from current private manifests")
    return raw


def prepare_fresh_holdout(
    *,
    candidate_plan_path: Path,
    private_root: Path,
    excluded_repo_lock_path: Path,
    preflight_exclusion_path: Path,
) -> dict[str, Any]:
    candidate_plan = b2c.load_json(candidate_plan_path)
    excluded_lock = b2c.load_json(excluded_repo_lock_path)
    preflight_slugs = load_preflight_exclusions(preflight_exclusion_path)
    validate_fresh_candidate_plan(
        candidate_plan,
        excluded_repo_lock=excluded_lock,
        preflight_excluded_slugs=preflight_slugs,
    )
    author = importlib.import_module("product_bakeoff_b2_author")
    result = author.prepare_private_manifests(
        candidate_plan=candidate_plan_path,
        private_root=private_root,
    )
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    new_repo_lock = b2c.load_json(repo_path)
    new_task_manifest = b2c.load_json(task_path)
    new_oracle_manifest = b2c.load_json(oracle_path)
    binding = build_holdout_binding(
        new_repo_lock=new_repo_lock,
        new_task_manifest=new_task_manifest,
        new_oracle_manifest=new_oracle_manifest,
        excluded_repo_lock=excluded_lock,
        excluded_repo_lock_path=excluded_repo_lock_path,
        preflight_exclusion_path=preflight_exclusion_path,
    )
    binding_path = private_root / "b21_private_holdout_binding.json"
    b2c.write_json(binding_path, binding)
    return {
        **result,
        "b21_spec_digest": b21_spec_digest(),
        "b21_holdout_frame_digest": b21_task_frame_digest(),
        "holdout_binding_digest": binding["holdout_binding_digest"],
        "holdout_binding_path": str(binding_path.resolve()),
    }


def b21_runtime_bundle_digest(cli_path: str | Path) -> str:
    path = Path(cli_path).resolve(strict=True)
    if path.is_symlink() or not path.is_file():
        raise B21CorpusError("OpenLocus CLI path is missing or unsafe")
    payload = {
        "b21_source_bundle_digest": b21_source_bundle_digest(),
        "cli_bytes": path.stat().st_size,
        "cli_sha256": b2c.file_sha256(path),
    }
    return _prefixed_digest("b21run_", payload)


def build_freeze_receipt(
    *,
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
    cli_path: str | Path,
) -> dict[str, Any]:
    receipt = {
        "schema_version": B21_FREEZE_RECEIPT_SCHEMA,
        "b21_spec_digest": b21_spec_digest(),
        "b21_holdout_frame_digest": b21_task_frame_digest(),
        "b21_execution_schedule_digest": b21_execution_schedule_digest(),
        "parent_task_authoring_spec_digest": B21_PARENT_B2_SPEC_DIGEST,
        "repo_lock_digest": repo_lock_digest,
        "task_manifest_digest": task_manifest_digest,
        "oracle_manifest_digest": oracle_manifest_digest,
        "holdout_binding_digest": holdout_binding_digest_value,
        "repo_lock_file_sha256": b2c.file_sha256(repo_lock_path),
        "task_manifest_file_sha256": b2c.file_sha256(task_manifest_path),
        "oracle_manifest_file_sha256": b2c.file_sha256(oracle_manifest_path),
        "holdout_binding_file_sha256": b2c.file_sha256(holdout_binding_path),
        "excluded_b2_repo_lock_file_sha256": b2c.file_sha256(excluded_repo_lock_path),
        "preflight_exclusion_file_sha256": b2c.file_sha256(preflight_exclusion_path),
        "source_bundle_digest": b21_source_bundle_digest(),
        "runtime_bundle_digest": b21_runtime_bundle_digest(cli_path),
    }
    receipt["freeze_receipt_digest"] = _prefixed_digest("b21freeze_", receipt)
    return receipt


def validate_freeze_receipt(
    raw: Any,
    *,
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
    cli_path: str | Path,
) -> dict[str, Any]:
    expected = build_freeze_receipt(
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
        raise B21CorpusError("B2.1 freeze receipt drifted from current locked inputs/runtime")
    return raw


def freeze_fresh_holdout(
    *,
    private_root: Path,
    excluded_repo_lock_path: Path,
    preflight_exclusion_path: Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    binding_path = private_root / "b21_private_holdout_binding.json"
    repo_lock = b2c.load_json(repo_path)
    task_manifest = b2c.load_json(task_path)
    oracle_manifest = b2c.load_json(oracle_path)
    binding = b2c.load_json(binding_path)
    excluded_lock = b2c.load_json(excluded_repo_lock_path)
    b2c.validate_repo_lock(repo_lock, require_sources=True)
    tasks = b2c.validate_task_manifest(
        task_manifest, repo_lock_digest=repo_lock["repo_lock_digest"]
    )
    oracle = importlib.import_module("product_bakeoff_b2_oracle")
    oracle.validate_oracle_manifest(
        oracle_manifest,
        tasks=tasks,
        repo_lock=repo_lock,
        task_manifest_digest=task_manifest["task_manifest_digest"],
    )
    validate_holdout_binding(
        binding,
        new_repo_lock=repo_lock,
        new_task_manifest=task_manifest,
        new_oracle_manifest=oracle_manifest,
        excluded_repo_lock=excluded_lock,
        excluded_repo_lock_path=excluded_repo_lock_path,
        preflight_exclusion_path=preflight_exclusion_path,
    )
    receipt = build_freeze_receipt(
        repo_lock_digest=repo_lock["repo_lock_digest"],
        task_manifest_digest=task_manifest["task_manifest_digest"],
        oracle_manifest_digest=oracle_manifest["oracle_manifest_digest"],
        holdout_binding_digest_value=binding["holdout_binding_digest"],
        repo_lock_path=repo_path,
        task_manifest_path=task_path,
        oracle_manifest_path=oracle_path,
        holdout_binding_path=binding_path,
        excluded_repo_lock_path=excluded_repo_lock_path,
        preflight_exclusion_path=preflight_exclusion_path,
        cli_path=cli_path,
    )
    receipt_path = private_root / "b21_private_freeze_receipt.json"
    b2c.write_json(receipt_path, receipt)
    return {**receipt, "freeze_receipt_path": str(receipt_path.resolve())}


def _synthetic_excluded_lock() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    target_total = {
        "small": 512 * 1024,
        "medium": 8 * 1024 * 1024,
        "large": 32 * 1024 * 1024,
        "xlarge": 80 * 1024 * 1024,
    }
    extension = {"rust": ".rs", "python": ".py", "typescript": ".ts"}
    for index, repo_slot in enumerate(sorted({slot.repo_slot for slot in b2p.build_task_slots()})):
        language, size_band = repo_slot.removeprefix("b2_repo_").split("_", 1)
        per_file = target_total[size_band] // 32
        files = [
            b2c.B2FileRecord(
                path=f"src/f{file_index:02d}{extension[language]}",
                bytes=per_file,
                line_count=10,
                sha256=hashlib.sha256(
                    f"{repo_slot}|{file_index}|{per_file}".encode("utf-8")
                ).hexdigest(),
                extension=extension[language],
            )
            for file_index in range(32)
        ]
        rows.append(
            {
                "repo_slot": repo_slot,
                "language": language,
                "size_band": size_band,
                "source": {
                    "type": "github_public",
                    "repo": f"old-owner/old-repo-{index}",
                    "clone_root": f"C:/private/old-{index}",
                },
                "commit": f"{index + 1:040x}",
                "license": {"detected": ["MIT"], "expected": "MIT"},
                "visible": {
                    "file_count": len(files),
                    "bytes": sum(row.bytes for row in files),
                    "manifest_digest": b2c.visible_manifest_digest(files),
                    "files": [row.to_dict() for row in files],
                },
            }
        )
    lock = {
        "schema_version": b2c.B2_REPO_LOCK_SCHEMA,
        "corpus_version": b2c.B2_CORPUS_VERSION,
        "protocol_spec_digest": b2p.b2_spec_digest(),
        "task_slot_digest": b2p.task_slot_digest(),
        "repo_lock_digest": "",
        "repos": rows,
    }
    lock["repo_lock_digest"] = b2c.compute_repo_lock_digest(lock)
    b2c.validate_repo_lock(lock, require_sources=False)
    return lock


def _synthetic_candidate_plan(*, overlap_slug: str | None = None) -> dict[str, Any]:
    slots = []
    for index, repo_slot in enumerate(sorted({slot.repo_slot for slot in b2p.build_task_slots()})):
        slug = overlap_slug if index == 0 and overlap_slug else f"new-owner/new-repo-{index}"
        slots.append(
            {
                "repo_slot": repo_slot,
                "candidates": [{"repo": slug, "expected_license": "MIT"}],
            }
        )
    return {
        "schema_version": "product_bakeoff_b2_candidate_plan.v1",
        "slots": slots,
    }


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    excluded = _synthetic_excluded_lock()
    excluded_slugs = {
        row["source"]["repo"].casefold() for row in excluded["repos"]
    }
    checks.append(("synthetic_exclusion_count", len(excluded_slugs) == 12))
    fresh_candidates = validate_fresh_candidate_plan(
        _synthetic_candidate_plan(),
        excluded_repo_lock=excluded,
    )
    checks.append(("fresh_candidate_plan_valid", len(fresh_candidates) == 12))
    checks.append(("runtime_source_digest", b21_source_bundle_digest().startswith("b21src_")))
    checks.append(("frame_digest", b21_task_frame_digest().startswith("b21frame_")))
    with tempfile.TemporaryDirectory(prefix="openlocus-b21-freeze-") as tmp:
        root = Path(tmp)
        paths = []
        for name in (
            "repo.json",
            "task.json",
            "oracle.json",
            "binding.json",
            "old.json",
            "preflight.json",
        ):
            path = root / name
            path.write_text("{}\n", encoding="utf-8")
            paths.append(path)
        cli = root / "openlocus.bin"
        cli.write_bytes(b"b21-test-runtime")
        receipt = build_freeze_receipt(
            repo_lock_digest="b2repos_" + "1" * 64,
            task_manifest_digest="b2tasks_" + "2" * 64,
            oracle_manifest_digest="b2oracles_" + "3" * 64,
            holdout_binding_digest_value="b21holdout_" + "4" * 64,
            repo_lock_path=paths[0],
            task_manifest_path=paths[1],
            oracle_manifest_path=paths[2],
            holdout_binding_path=paths[3],
            excluded_repo_lock_path=paths[4],
            preflight_exclusion_path=paths[5],
            cli_path=cli,
        )
        validated = validate_freeze_receipt(
            receipt,
            repo_lock_digest="b2repos_" + "1" * 64,
            task_manifest_digest="b2tasks_" + "2" * 64,
            oracle_manifest_digest="b2oracles_" + "3" * 64,
            holdout_binding_digest_value="b21holdout_" + "4" * 64,
            repo_lock_path=paths[0],
            task_manifest_path=paths[1],
            oracle_manifest_path=paths[2],
            holdout_binding_path=paths[3],
            excluded_repo_lock_path=paths[4],
            preflight_exclusion_path=paths[5],
            cli_path=cli,
        )
        checks.append(("freeze_roundtrip", validated == receipt))
        checks.append(("runtime_digest", receipt["runtime_bundle_digest"].startswith("b21run_")))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    # Candidate overlap is checked without calling the author or touching a repo.
    excluded_lock = _synthetic_excluded_lock()
    excluded_rows = excluded_lock["repos"]
    excluded_slugs = {row["source"]["repo"].casefold() for row in excluded_rows}
    overlap_slug = excluded_rows[0]["source"]["repo"]
    try:
        validate_fresh_candidate_plan(
            _synthetic_candidate_plan(overlap_slug=overlap_slug),
            excluded_repo_lock=excluded_lock,
        )
        overlap_rejected = False
    except B21CorpusError:
        overlap_rejected = True
    checks.append(("candidate_overlap_rejected", overlap_rejected))
    preflight_slug = "preflight-owner/preflight-repo"
    try:
        validate_fresh_candidate_plan(
            _synthetic_candidate_plan(overlap_slug=preflight_slug),
            excluded_repo_lock=excluded_lock,
            preflight_excluded_slugs=[preflight_slug],
        )
        preflight_overlap_rejected = False
    except B21CorpusError:
        preflight_overlap_rejected = True
    checks.append(("preflight_overlap_rejected", preflight_overlap_rejected))
    try:
        _repo_slug("not-a-slug")
        malformed_rejected = False
    except B21CorpusError:
        malformed_rejected = True
    checks.append(("malformed_slug_rejected", malformed_rejected))
    with tempfile.TemporaryDirectory(prefix="openlocus-b21-fault-") as tmp:
        root = Path(tmp)
        files = []
        for index in range(6):
            path = root / f"f{index}.json"
            path.write_text("{}\n", encoding="utf-8")
            files.append(path)
        cli = root / "openlocus.bin"
        cli.write_bytes(b"runtime")
        receipt = build_freeze_receipt(
            repo_lock_digest="b2repos_" + "1" * 64,
            task_manifest_digest="b2tasks_" + "2" * 64,
            oracle_manifest_digest="b2oracles_" + "3" * 64,
            holdout_binding_digest_value="b21holdout_" + "4" * 64,
            repo_lock_path=files[0],
            task_manifest_path=files[1],
            oracle_manifest_path=files[2],
            holdout_binding_path=files[3],
            excluded_repo_lock_path=files[4],
            preflight_exclusion_path=files[5],
            cli_path=cli,
        )
        files[0].write_text('{"drift":true}\n', encoding="utf-8")
        try:
            validate_freeze_receipt(
                receipt,
                repo_lock_digest="b2repos_" + "1" * 64,
                task_manifest_digest="b2tasks_" + "2" * 64,
                oracle_manifest_digest="b2oracles_" + "3" * 64,
                holdout_binding_digest_value="b21holdout_" + "4" * 64,
                repo_lock_path=files[0],
                task_manifest_path=files[1],
                oracle_manifest_path=files[2],
                holdout_binding_path=files[3],
                excluded_repo_lock_path=files[4],
                preflight_exclusion_path=files[5],
                cli_path=cli,
            )
            drift_rejected = False
        except B21CorpusError:
            drift_rejected = True
        checks.append(("receipt_file_drift_rejected", drift_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B21CorpusError",
    "B21_HOLDOUT_BINDING_SCHEMA",
    "B21_FREEZE_RECEIPT_SCHEMA",
    "validate_fresh_candidate_plan",
    "build_holdout_binding",
    "validate_holdout_binding",
    "prepare_fresh_holdout",
    "b21_runtime_bundle_digest",
    "build_freeze_receipt",
    "validate_freeze_receipt",
    "freeze_fresh_holdout",
    "run_self_test",
    "run_fault_test",
]
