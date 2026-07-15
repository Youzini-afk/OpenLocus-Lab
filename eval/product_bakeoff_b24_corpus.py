#!/usr/bin/env python3
"""B2.4 private holdout admission, freeze, and launch authorization.

The frozen B2 author remains the only task author.  This overlay adds a closed
candidate registry, excludes both historical empirical repository frames plus
all preflight/qualification repositories, binds the passed B2.3 qualification,
freezes the B2.4 runtime, and requires a later public-readiness CI receipt
before execution can begin.

Private repository identities, queries, oracle rows, and all private digests
stay outside the checkout and are never emitted by this module's public tests.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
from product_bakeoff_b24_protocol import (
    B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
    B24_PARENT_B23_QUALIFICATION_DIGEST,
    B24_PARENT_B23_QUALIFICATION_SHA256,
    B24_REQUEST_TIMEOUT_SECONDS,
    b24_execution_schedule_digest,
    b24_holdout_frame_digest,
    b24_source_bundle_digest,
    b24_spec_digest,
)


B24_CORPUS_VERSION = "product_bakeoff_b24_corpus.v1"
B24_CANDIDATE_PLAN_SCHEMA = "product_bakeoff_b2_private_candidate_plan.v1"
B24_EXCLUSION_REGISTRY_SCHEMA = "product_bakeoff_b24_repository_exclusions.v1"
B24_HOLDOUT_BINDING_SCHEMA = "product_bakeoff_b24_private_holdout_binding.v1"
B24_FREEZE_RECEIPT_SCHEMA = "product_bakeoff_b24_private_freeze_receipt.v1"
B24_LAUNCH_AUTHORIZATION_SCHEMA = (
    "product_bakeoff_b24_private_launch_authorization.v1"
)
HISTORICAL_FRAME_LABELS = ("b2", "b21")
EXCLUSION_REASONS = frozenset(
    {
        "real_preflight",
        "qualification_repository",
        "operator_practice",
        "historical_candidate_failover",
    }
)


class B24CorpusError(ValueError):
    """Fail-closed B2.4 private corpus/freeze error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _repo_slug(value: Any) -> str:
    if not isinstance(value, str) or not value or "/" not in value:
        raise B24CorpusError("repository slug is missing or malformed")
    owner, repo = value.split("/", 1)
    if not owner or not repo or not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(
        r"[A-Za-z0-9_.-]+", repo
    ):
        raise B24CorpusError("repository slug is missing or malformed")
    return value.casefold()


def historical_repository_sets(
    historical_repo_locks: Mapping[str, Mapping[str, Any]],
) -> tuple[set[str], set[tuple[str, str]], dict[str, str]]:
    if tuple(sorted(historical_repo_locks)) != tuple(sorted(HISTORICAL_FRAME_LABELS)):
        raise B24CorpusError("historical repository lock labels must be exactly b2 and b21")
    slugs: set[str] = set()
    identities: set[tuple[str, str]] = set()
    digests: dict[str, str] = {}
    for label in HISTORICAL_FRAME_LABELS:
        validated = b2c.validate_repo_lock(
            dict(historical_repo_locks[label]), require_sources=False
        )
        frame_slugs: set[str] = set()
        frame_identities: set[tuple[str, str]] = set()
        for row in validated["repos"]:
            slug = _repo_slug(row["source"]["repo"])
            identity = (slug, row["commit"])
            frame_slugs.add(slug)
            frame_identities.add(identity)
        if len(frame_slugs) != 12 or len(frame_identities) != 12:
            raise B24CorpusError(
                f"historical {label} frame is not an exact 12-repository identity set"
            )
        if slugs & frame_slugs or identities & frame_identities:
            raise B24CorpusError("historical B2 and B2.1 frames unexpectedly overlap")
        slugs.update(frame_slugs)
        identities.update(frame_identities)
        digests[label] = validated["repo_lock_digest"]
    if len(slugs) != 24 or len(identities) != 24:
        raise B24CorpusError("historical frame union is not 24 distinct repositories")
    return slugs, identities, digests


def validate_exclusion_registry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "repositories",
        "synthetic_sources",
    }:
        raise B24CorpusError("repository exclusion registry has non-closed shape")
    if raw["schema_version"] != B24_EXCLUSION_REGISTRY_SCHEMA:
        raise B24CorpusError("repository exclusion registry schema mismatch")
    repositories = raw["repositories"]
    if not isinstance(repositories, list) or not repositories:
        raise B24CorpusError("repository exclusion registry must be nonempty")
    normalized: list[tuple[str, str]] = []
    for row in repositories:
        if not isinstance(row, dict) or set(row) != {"repo", "reason"}:
            raise B24CorpusError("repository exclusion row has non-closed shape")
        slug = _repo_slug(row["repo"])
        reason = row["reason"]
        if reason not in EXCLUSION_REASONS:
            raise B24CorpusError("repository exclusion reason is not frozen")
        normalized.append((slug, reason))
    if normalized != sorted(normalized) or len({slug for slug, _ in normalized}) != len(
        normalized
    ):
        raise B24CorpusError("repository exclusions must be sorted and slug-unique")
    synthetic = raw["synthetic_sources"]
    if (
        not isinstance(synthetic, list)
        or not synthetic
        or not all(isinstance(item, str) and item for item in synthetic)
        or synthetic != sorted(set(synthetic))
    ):
        raise B24CorpusError("synthetic source exclusions must be sorted and unique")
    return raw


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
        raise B24CorpusError("candidate plan has non-closed shape")
    if candidate_plan["schema_version"] != B24_CANDIDATE_PLAN_SCHEMA:
        raise B24CorpusError("candidate plan schema mismatch")
    if not isinstance(candidate_plan["slots"], list) or len(candidate_plan["slots"]) != 12:
        raise B24CorpusError("candidate plan must contain exactly 12 slot rows")
    historical_slugs, _, _ = historical_repository_sets(historical_repo_locks)
    excluded_slugs = exclusion_repository_slugs(exclusion_registry)
    expected_slots = {slot.repo_slot for slot in b2p.build_task_slots()}
    seen_slots: set[str] = set()
    candidates: list[str] = []
    for slot in candidate_plan["slots"]:
        if not isinstance(slot, dict) or set(slot) != {"repo_slot", "candidates"}:
            raise B24CorpusError("candidate slot has non-closed shape")
        repo_slot = slot["repo_slot"]
        if repo_slot not in expected_slots or repo_slot in seen_slots:
            raise B24CorpusError("candidate slot is unknown or duplicated")
        seen_slots.add(repo_slot)
        rows = slot["candidates"]
        if not isinstance(rows, list) or len(rows) < 2:
            raise B24CorpusError("each B2.4 slot requires at least two frozen candidates")
        for candidate in rows:
            if not isinstance(candidate, dict) or set(candidate) != {
                "repo",
                "expected_license",
            }:
                raise B24CorpusError("candidate row has non-closed shape")
            slug = _repo_slug(candidate["repo"])
            license_text = candidate["expected_license"]
            if not isinstance(license_text, str) or not license_text.strip():
                raise B24CorpusError("candidate expected license is missing")
            if slug in historical_slugs:
                raise B24CorpusError("historical repository reused in B2.4 candidate plan")
            if slug in excluded_slugs:
                raise B24CorpusError("excluded repository reused in B2.4 candidate plan")
            candidates.append(slug)
    if seen_slots != expected_slots:
        raise B24CorpusError("candidate plan slot coverage is incomplete")
    if len(set(candidates)) != len(candidates):
        raise B24CorpusError("candidate repositories must not repeat across slots")
    return tuple(candidates)


def holdout_binding_digest(binding: Mapping[str, Any]) -> str:
    payload = dict(binding)
    payload.pop("holdout_binding_digest", None)
    return _prefixed_digest("b24holdout_", payload)


def build_holdout_binding(
    *,
    new_repo_lock: Mapping[str, Any],
    new_task_manifest: Mapping[str, Any],
    new_oracle_manifest: Mapping[str, Any],
    candidate_plan: Mapping[str, Any],
    candidate_plan_path: Path,
    historical_repo_locks: Mapping[str, Mapping[str, Any]],
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry: Mapping[str, Any],
    exclusion_registry_path: Path,
    qualification_report_path: Path,
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
    historical_slugs, historical_identities, historical_digests = (
        historical_repository_sets(historical_repo_locks)
    )
    excluded_slugs = exclusion_repository_slugs(exclusion_registry)
    new_slugs: set[str] = set()
    new_identities: set[tuple[str, str]] = set()
    for row in new_lock["repos"]:
        slug = _repo_slug(row["source"]["repo"])
        identity = (slug, row["commit"])
        if slug not in candidates:
            raise B24CorpusError("selected repository is absent from frozen candidate plan")
        if slug in historical_slugs or identity in historical_identities:
            raise B24CorpusError("selected B2.4 repository overlaps a historical frame")
        if slug in excluded_slugs:
            raise B24CorpusError("selected B2.4 repository overlaps exclusion registry")
        new_slugs.add(slug)
        new_identities.add(identity)
    if len(new_slugs) != 12 or len(new_identities) != 12:
        raise B24CorpusError("B2.4 selected frame is not 12 distinct identities")
    if len(tasks) != 48:
        raise B24CorpusError("B2.4 task manifest must contain 48 tasks")
    if new_oracle_manifest.get("task_manifest_digest") != new_task_manifest.get(
        "task_manifest_digest"
    ):
        raise B24CorpusError("B2.4 oracle/task binding mismatch")
    if new_oracle_manifest.get("repo_lock_digest") != new_lock["repo_lock_digest"]:
        raise B24CorpusError("B2.4 oracle/repository binding mismatch")
    if b2c.file_sha256(qualification_report_path) != B24_PARENT_B23_QUALIFICATION_SHA256:
        raise B24CorpusError("B2.3 qualification aggregate bytes drifted")
    expected_path_labels = set(HISTORICAL_FRAME_LABELS)
    if set(historical_repo_lock_paths) != expected_path_labels:
        raise B24CorpusError("historical repository lock paths are incomplete")
    binding = {
        "schema_version": B24_HOLDOUT_BINDING_SCHEMA,
        "corpus_version": B24_CORPUS_VERSION,
        "b24_spec_digest": b24_spec_digest(),
        "b24_holdout_frame_digest": b24_holdout_frame_digest(),
        "b24_execution_schedule_digest": b24_execution_schedule_digest(),
        "parent_b23_qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
        "parent_b23_qualification_file_sha256": B24_PARENT_B23_QUALIFICATION_SHA256,
        "new_repo_lock_digest": new_lock["repo_lock_digest"],
        "new_task_manifest_digest": new_task_manifest["task_manifest_digest"],
        "new_oracle_manifest_digest": new_oracle_manifest["oracle_manifest_digest"],
        "candidate_plan_file_sha256": b2c.file_sha256(candidate_plan_path),
        "historical_repo_lock_digests": {
            label: historical_digests[label] for label in HISTORICAL_FRAME_LABELS
        },
        "historical_repo_lock_file_sha256": {
            label: b2c.file_sha256(historical_repo_lock_paths[label])
            for label in HISTORICAL_FRAME_LABELS
        },
        "exclusion_registry_file_sha256": b2c.file_sha256(exclusion_registry_path),
        "historical_repository_count": len(historical_slugs),
        "excluded_repository_count": len(excluded_slugs),
        "excluded_synthetic_source_count": len(exclusion_registry["synthetic_sources"]),
        "new_repository_count": len(new_slugs),
        "new_task_count": len(tasks),
        "selected_candidate_membership_count": len(new_slugs),
        "historical_repository_slug_overlap_count": 0,
        "historical_repository_identity_overlap_count": 0,
        "exclusion_registry_overlap_count": 0,
        "holdout_binding_digest": "",
    }
    binding["holdout_binding_digest"] = holdout_binding_digest(binding)
    return binding


def validate_holdout_binding(
    raw: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    expected = build_holdout_binding(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B24CorpusError("B2.4 holdout binding drifted from current private inputs")
    return raw


def prepare_fresh_holdout(
    *,
    candidate_plan_path: Path,
    private_root: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    qualification_report_path: Path,
) -> dict[str, Any]:
    private_root = Path(private_root)
    if private_root.exists() and any(private_root.iterdir()):
        raise B24CorpusError("B2.4 private root must be absent or empty before authoring")
    candidate_plan = b2c.load_json(candidate_plan_path)
    historical_locks = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in HISTORICAL_FRAME_LABELS
    }
    exclusion_registry = validate_exclusion_registry(
        b2c.load_json(exclusion_registry_path)
    )
    validate_fresh_candidate_plan(
        candidate_plan,
        historical_repo_locks=historical_locks,
        exclusion_registry=exclusion_registry,
    )
    author = importlib.import_module("product_bakeoff_b2_author")
    if getattr(author, "B2_CANDIDATE_PLAN_SCHEMA", None) != B24_CANDIDATE_PLAN_SCHEMA:
        raise B24CorpusError("candidate plan schema drifted from frozen B2 author")
    result = author.prepare_private_manifests(
        candidate_plan=candidate_plan_path,
        private_root=private_root,
    )
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    binding = build_holdout_binding(
        new_repo_lock=b2c.load_json(repo_path),
        new_task_manifest=b2c.load_json(task_path),
        new_oracle_manifest=b2c.load_json(oracle_path),
        candidate_plan=candidate_plan,
        candidate_plan_path=candidate_plan_path,
        historical_repo_locks=historical_locks,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry=exclusion_registry,
        exclusion_registry_path=exclusion_registry_path,
        qualification_report_path=qualification_report_path,
    )
    binding_path = private_root / "b24_private_holdout_binding.json"
    b2c.write_json(binding_path, binding)
    return {
        **result,
        "holdout_binding_path": str(binding_path.resolve()),
        "repo_count": 12,
        "task_count": 48,
    }


def b24_runtime_bundle_digest(cli_path: str | Path) -> str:
    path = Path(cli_path).resolve(strict=True)
    if path.is_symlink() or not path.is_file():
        raise B24CorpusError("OpenLocus CLI path is missing or unsafe")
    return _prefixed_digest(
        "b24run_",
        {
            "b24_source_bundle_digest": b24_source_bundle_digest(),
            "cli_bytes": path.stat().st_size,
            "cli_sha256": b2c.file_sha256(path),
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
    repo_lock_path: Path,
    task_manifest_path: Path,
    oracle_manifest_path: Path,
    holdout_binding_path: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    qualification_report_path: Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    if set(historical_repo_lock_paths) != set(HISTORICAL_FRAME_LABELS):
        raise B24CorpusError("historical repository lock paths are incomplete")
    receipt = {
        "schema_version": B24_FREEZE_RECEIPT_SCHEMA,
        "b24_spec_digest": b24_spec_digest(),
        "b24_holdout_frame_digest": b24_holdout_frame_digest(),
        "b24_execution_schedule_digest": b24_execution_schedule_digest(),
        "b21_execution_schedule_digest": b24_execution_schedule_digest(),
        "parent_b23_qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
        "parent_b23_qualification_file_sha256": b2c.file_sha256(
            qualification_report_path
        ),
        "repo_lock_digest": repo_lock_digest,
        "task_manifest_digest": task_manifest_digest,
        "oracle_manifest_digest": oracle_manifest_digest,
        "holdout_binding_digest": holdout_binding_digest_value,
        "repo_lock_file_sha256": b2c.file_sha256(repo_lock_path),
        "task_manifest_file_sha256": b2c.file_sha256(task_manifest_path),
        "oracle_manifest_file_sha256": b2c.file_sha256(oracle_manifest_path),
        "holdout_binding_file_sha256": b2c.file_sha256(holdout_binding_path),
        "candidate_plan_file_sha256": b2c.file_sha256(candidate_plan_path),
        "historical_repo_lock_file_sha256": {
            label: b2c.file_sha256(historical_repo_lock_paths[label])
            for label in HISTORICAL_FRAME_LABELS
        },
        "exclusion_registry_file_sha256": b2c.file_sha256(exclusion_registry_path),
        "request_timeout_seconds": B24_REQUEST_TIMEOUT_SECONDS,
        "adapter_command_timeout_seconds": B24_ADAPTER_COMMAND_TIMEOUT_SECONDS,
        "source_bundle_digest": b24_source_bundle_digest(),
        "runtime_bundle_digest": b24_runtime_bundle_digest(cli_path),
    }
    if receipt["parent_b23_qualification_file_sha256"] != (
        B24_PARENT_B23_QUALIFICATION_SHA256
    ):
        raise B24CorpusError("B2.3 qualification aggregate changed before freeze")
    receipt["freeze_receipt_digest"] = _prefixed_digest("b24freeze_", receipt)
    return receipt


def validate_freeze_receipt(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_freeze_receipt(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B24CorpusError("B2.4 freeze receipt drifted from locked inputs/runtime")
    return raw


def freeze_fresh_holdout(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    qualification_report_path: Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    private_root = Path(private_root)
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    binding_path = private_root / "b24_private_holdout_binding.json"
    receipt_path = private_root / "b24_private_freeze_receipt.json"
    if receipt_path.exists():
        raise B24CorpusError("B2.4 freeze receipt already exists")
    repo_lock = b2c.load_json(repo_path)
    task_manifest = b2c.load_json(task_path)
    oracle_manifest = b2c.load_json(oracle_path)
    binding = b2c.load_json(binding_path)
    candidate_plan = b2c.load_json(candidate_plan_path)
    historical_locks = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in HISTORICAL_FRAME_LABELS
    }
    exclusion_registry = validate_exclusion_registry(
        b2c.load_json(exclusion_registry_path)
    )
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
        candidate_plan=candidate_plan,
        candidate_plan_path=candidate_plan_path,
        historical_repo_locks=historical_locks,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry=exclusion_registry,
        exclusion_registry_path=exclusion_registry_path,
        qualification_report_path=qualification_report_path,
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
        candidate_plan_path=candidate_plan_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        qualification_report_path=qualification_report_path,
        cli_path=cli_path,
    )
    b2c.write_json(receipt_path, receipt)
    return {**receipt, "freeze_receipt_path": str(receipt_path.resolve())}


def launch_authorization_digest(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("launch_authorization_digest", None)
    return _prefixed_digest("b24launch_", payload)


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
    if not re.fullmatch(r"[0-9a-f]{40}", readiness_checkpoint):
        raise B24CorpusError("readiness checkpoint must be a full lowercase commit SHA")
    if not isinstance(readiness_ci_run_id, int) or readiness_ci_run_id <= 0:
        raise B24CorpusError("readiness CI run id must be positive")
    if readiness_ci_conclusion != "success":
        raise B24CorpusError("readiness CI must conclude success")
    readiness = importlib.import_module("product_bakeoff_b24_readiness")
    errors = readiness.validate_public_readiness(dict(readiness_report))
    if errors:
        raise B24CorpusError("public readiness report is invalid")
    if readiness_report["decision"]["private_holdout_frozen"] is not True:
        raise B24CorpusError("public readiness did not freeze the private holdout")
    if readiness_report["decision"]["treatment_output_exists"] is not False:
        raise B24CorpusError("public readiness already contains treatment output")
    authorization = {
        "schema_version": B24_LAUNCH_AUTHORIZATION_SCHEMA,
        "b24_spec_digest": b24_spec_digest(),
        "source_bundle_digest": freeze_receipt["source_bundle_digest"],
        "runtime_bundle_digest": freeze_receipt["runtime_bundle_digest"],
        "freeze_receipt_digest": freeze_receipt["freeze_receipt_digest"],
        "freeze_receipt_file_sha256": b2c.file_sha256(freeze_receipt_path),
        "readiness_report_digest": readiness_report["readiness_digest"],
        "readiness_report_file_sha256": b2c.file_sha256(readiness_report_path),
        "readiness_checkpoint": readiness_checkpoint,
        "readiness_ci_run_id": readiness_ci_run_id,
        "readiness_ci_conclusion": readiness_ci_conclusion,
        "tournament_attempt_number": 1,
        "launch_authorization_digest": "",
    }
    authorization["launch_authorization_digest"] = launch_authorization_digest(
        authorization
    )
    return authorization


def validate_launch_authorization(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_launch_authorization(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B24CorpusError("B2.4 launch authorization drifted")
    return raw


def create_launch_authorization(
    *,
    private_root: Path,
    readiness_report_path: Path,
    readiness_checkpoint: str,
    readiness_ci_run_id: int,
    readiness_ci_conclusion: str,
) -> dict[str, Any]:
    private_root = Path(private_root)
    freeze_path = private_root / "b24_private_freeze_receipt.json"
    authorization_path = private_root / "b24_private_launch_authorization.json"
    if authorization_path.exists():
        raise B24CorpusError("B2.4 launch authorization already exists")
    freeze = b2c.load_json(freeze_path)
    readiness = b2c.load_json(readiness_report_path)
    authorization = build_launch_authorization(
        freeze_receipt=freeze,
        freeze_receipt_path=freeze_path,
        readiness_report=readiness,
        readiness_report_path=readiness_report_path,
        readiness_checkpoint=readiness_checkpoint,
        readiness_ci_run_id=readiness_ci_run_id,
        readiness_ci_conclusion=readiness_ci_conclusion,
    )
    b2c.write_json(authorization_path, authorization)
    return {
        **authorization,
        "launch_authorization_path": str(authorization_path.resolve()),
    }


def _synthetic_lock(label: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    target_total = {
        "small": 512 * 1024,
        "medium": 8 * 1024 * 1024,
        "large": 32 * 1024 * 1024,
        "xlarge": 80 * 1024 * 1024,
    }
    extension = {"rust": ".rs", "python": ".py", "typescript": ".ts"}
    repo_slots = sorted({slot.repo_slot for slot in b2p.build_task_slots()})
    for index, repo_slot in enumerate(repo_slots):
        language, size_band = repo_slot.removeprefix("b2_repo_").split("_", 1)
        per_file = target_total[size_band] // 32
        files = [
            b2c.B2FileRecord(
                path=f"src/f{file_index:02d}{extension[language]}",
                bytes=per_file,
                line_count=10,
                sha256=hashlib.sha256(
                    f"{label}|{repo_slot}|{file_index}|{per_file}".encode("utf-8")
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
                    "repo": f"{label}-owner/{label}-repo-{index}",
                    "clone_root": f"C:/private/{label}-{index}",
                },
                "commit": hashlib.sha1(f"{label}-{index}".encode()).hexdigest(),
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


def _synthetic_registry() -> dict[str, Any]:
    return {
        "schema_version": B24_EXCLUSION_REGISTRY_SCHEMA,
        "repositories": [
            {"repo": "probe-owner/probe-repo", "reason": "real_preflight"}
        ],
        "synthetic_sources": ["deterministic_public_synthetic_typescript"],
    }


def _synthetic_candidate_plan(*, first_slug: str | None = None) -> dict[str, Any]:
    slots = []
    for index, repo_slot in enumerate(
        sorted({slot.repo_slot for slot in b2p.build_task_slots()})
    ):
        primary = first_slug if index == 0 and first_slug else f"new-owner/new-repo-{index}-a"
        slots.append(
            {
                "repo_slot": repo_slot,
                "candidates": [
                    {"repo": primary, "expected_license": "MIT"},
                    {
                        "repo": f"new-owner/new-repo-{index}-b",
                        "expected_license": "MIT",
                    },
                ],
            }
        )
    return {"schema_version": B24_CANDIDATE_PLAN_SCHEMA, "slots": slots}


def run_self_test() -> dict[str, Any]:
    locks = {"b2": _synthetic_lock("b2old"), "b21": _synthetic_lock("b21old")}
    slugs, identities, digests = historical_repository_sets(locks)
    registry = _synthetic_registry()
    candidates = validate_fresh_candidate_plan(
        _synthetic_candidate_plan(),
        historical_repo_locks=locks,
        exclusion_registry=registry,
    )
    checks: list[tuple[str, bool]] = [
        ("historical_slug_count", len(slugs) == 24),
        ("historical_identity_count", len(identities) == 24),
        ("historical_digest_count", len(digests) == 2),
        ("candidate_count", len(candidates) == 24),
        ("candidate_schema_matches_author", B24_CANDIDATE_PLAN_SCHEMA == "product_bakeoff_b2_private_candidate_plan.v1"),
        ("registry_valid", validate_exclusion_registry(registry) == registry),
        ("source_digest", b24_source_bundle_digest().startswith("b24src_")),
    ]
    with tempfile.TemporaryDirectory(prefix="openlocus-b24-freeze-") as tmp:
        root = Path(tmp)
        files: list[Path] = []
        for index in range(9):
            path = root / f"f{index}.json"
            path.write_text("{}\n", encoding="utf-8")
            files.append(path)
        cli = root / "openlocus.bin"
        cli.write_bytes(b"b24-test-runtime")
        receipt = build_freeze_receipt(
            repo_lock_digest="b2repos_" + "1" * 64,
            task_manifest_digest="b2tasks_" + "2" * 64,
            oracle_manifest_digest="b2oracles_" + "3" * 64,
            holdout_binding_digest_value="b24holdout_" + "4" * 64,
            repo_lock_path=files[0],
            task_manifest_path=files[1],
            oracle_manifest_path=files[2],
            holdout_binding_path=files[3],
            candidate_plan_path=files[4],
            historical_repo_lock_paths={"b2": files[5], "b21": files[6]},
            exclusion_registry_path=files[7],
            qualification_report_path=(
                Path(__file__).resolve().parents[1]
                / "artifacts"
                / "product_bakeoff_b23_runner_qualification"
                / "product_bakeoff_b23_runner_qualification.json"
            ),
            cli_path=cli,
        )
        validated = validate_freeze_receipt(
            receipt,
            repo_lock_digest="b2repos_" + "1" * 64,
            task_manifest_digest="b2tasks_" + "2" * 64,
            oracle_manifest_digest="b2oracles_" + "3" * 64,
            holdout_binding_digest_value="b24holdout_" + "4" * 64,
            repo_lock_path=files[0],
            task_manifest_path=files[1],
            oracle_manifest_path=files[2],
            holdout_binding_path=files[3],
            candidate_plan_path=files[4],
            historical_repo_lock_paths={"b2": files[5], "b21": files[6]},
            exclusion_registry_path=files[7],
            qualification_report_path=(
                Path(__file__).resolve().parents[1]
                / "artifacts"
                / "product_bakeoff_b23_runner_qualification"
                / "product_bakeoff_b23_runner_qualification.json"
            ),
            cli_path=cli,
        )
        checks.append(("freeze_roundtrip", validated == receipt))
        checks.append(("runtime_digest", receipt["runtime_bundle_digest"].startswith("b24run_")))
        checks.append(("timeout_bridge", receipt["adapter_command_timeout_seconds"] == 570.0 and receipt["request_timeout_seconds"] == 600.0))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    locks = {"b2": _synthetic_lock("b2old"), "b21": _synthetic_lock("b21old")}
    registry = _synthetic_registry()
    checks: list[tuple[str, bool]] = []

    def candidate_rejected(name: str, slug: str) -> None:
        try:
            validate_fresh_candidate_plan(
                _synthetic_candidate_plan(first_slug=slug),
                historical_repo_locks=locks,
                exclusion_registry=registry,
            )
            rejected = False
        except B24CorpusError:
            rejected = True
        checks.append((name, rejected))

    candidate_rejected("b2_overlap_rejected", locks["b2"]["repos"][0]["source"]["repo"])
    candidate_rejected("b21_overlap_rejected", locks["b21"]["repos"][0]["source"]["repo"])
    candidate_rejected("registry_overlap_rejected", registry["repositories"][0]["repo"])
    try:
        malformed = _synthetic_candidate_plan()
        malformed["slots"][0]["candidates"] = malformed["slots"][0]["candidates"][:1]
        validate_fresh_candidate_plan(
            malformed,
            historical_repo_locks=locks,
            exclusion_registry=registry,
        )
        one_candidate_rejected = False
    except B24CorpusError:
        one_candidate_rejected = True
    checks.append(("single_candidate_slot_rejected", one_candidate_rejected))
    try:
        validate_exclusion_registry(
            {"schema_version": B24_EXCLUSION_REGISTRY_SCHEMA, "repositories": [], "synthetic_sources": []}
        )
        empty_registry_rejected = False
    except B24CorpusError:
        empty_registry_rejected = True
    checks.append(("empty_registry_rejected", empty_registry_rejected))
    with tempfile.TemporaryDirectory(prefix="openlocus-b24-fault-") as tmp:
        root = Path(tmp)
        files = []
        for index in range(8):
            path = root / f"f{index}.json"
            path.write_text("{}\n", encoding="utf-8")
            files.append(path)
        cli = root / "openlocus.bin"
        cli.write_bytes(b"runtime")
        qualification = (
            Path(__file__).resolve().parents[1]
            / "artifacts"
            / "product_bakeoff_b23_runner_qualification"
            / "product_bakeoff_b23_runner_qualification.json"
        )
        receipt = build_freeze_receipt(
            repo_lock_digest="b2repos_" + "1" * 64,
            task_manifest_digest="b2tasks_" + "2" * 64,
            oracle_manifest_digest="b2oracles_" + "3" * 64,
            holdout_binding_digest_value="b24holdout_" + "4" * 64,
            repo_lock_path=files[0],
            task_manifest_path=files[1],
            oracle_manifest_path=files[2],
            holdout_binding_path=files[3],
            candidate_plan_path=files[4],
            historical_repo_lock_paths={"b2": files[5], "b21": files[6]},
            exclusion_registry_path=files[7],
            qualification_report_path=qualification,
            cli_path=cli,
        )
        files[0].write_text('{"drift":true}\n', encoding="utf-8")
        try:
            validate_freeze_receipt(
                receipt,
                repo_lock_digest="b2repos_" + "1" * 64,
                task_manifest_digest="b2tasks_" + "2" * 64,
                oracle_manifest_digest="b2oracles_" + "3" * 64,
                holdout_binding_digest_value="b24holdout_" + "4" * 64,
                repo_lock_path=files[0],
                task_manifest_path=files[1],
                oracle_manifest_path=files[2],
                holdout_binding_path=files[3],
                candidate_plan_path=files[4],
                historical_repo_lock_paths={"b2": files[5], "b21": files[6]},
                exclusion_registry_path=files[7],
                qualification_report_path=qualification,
                cli_path=cli,
            )
            drift_rejected = False
        except B24CorpusError:
            drift_rejected = True
        checks.append(("freeze_file_drift_rejected", drift_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B24CorpusError",
    "B24_CANDIDATE_PLAN_SCHEMA",
    "B24_EXCLUSION_REGISTRY_SCHEMA",
    "B24_HOLDOUT_BINDING_SCHEMA",
    "B24_FREEZE_RECEIPT_SCHEMA",
    "B24_LAUNCH_AUTHORIZATION_SCHEMA",
    "HISTORICAL_FRAME_LABELS",
    "validate_exclusion_registry",
    "validate_fresh_candidate_plan",
    "build_holdout_binding",
    "validate_holdout_binding",
    "prepare_fresh_holdout",
    "b24_runtime_bundle_digest",
    "build_freeze_receipt",
    "validate_freeze_receipt",
    "freeze_fresh_holdout",
    "build_launch_authorization",
    "validate_launch_authorization",
    "create_launch_authorization",
    "run_self_test",
    "run_fault_test",
]
