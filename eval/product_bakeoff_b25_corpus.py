#!/usr/bin/env python3
"""B2.5 private holdout admission, query gate, freeze, and launch control."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
import product_bakeoff_b24_corpus as b24c
import product_bakeoff_b25_query_gate as b25q
import product_bakeoff_b25_runtime_qualification as b25rq
from product_bakeoff_b25_protocol import (
    B25_ADAPTER_COMMAND_TIMEOUT_SECONDS,
    B25_PARENT_B23_QUALIFICATION_DIGEST,
    B25_PARENT_B24_FAILURE_DIGEST,
    B25_PARENT_B24_REPAIR_DIGEST,
    B25_REQUEST_TIMEOUT_SECONDS,
    b25_execution_schedule_digest,
    b25_holdout_frame_digest,
    b25_source_bundle_digest,
    b25_spec_digest,
)


B25_CORPUS_VERSION = "product_bakeoff_b25_corpus.v1"
B25_CANDIDATE_PLAN_SCHEMA = "product_bakeoff_b2_private_candidate_plan.v1"
B25_EXCLUSION_REGISTRY_SCHEMA = b24c.B24_EXCLUSION_REGISTRY_SCHEMA
B25_HOLDOUT_BINDING_SCHEMA = "product_bakeoff_b25_private_holdout_binding.v1"
B25_FREEZE_RECEIPT_SCHEMA = "product_bakeoff_b25_private_freeze_receipt.v1"
B25_LAUNCH_AUTHORIZATION_SCHEMA = (
    "product_bakeoff_b25_private_launch_authorization.v1"
)
HISTORICAL_FRAME_LABELS = ("b2", "b21", "b24")


class B25CorpusError(ValueError):
    """Fail-closed B2.5 private corpus/freeze error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _repo_slug(value: Any) -> str:
    if not isinstance(value, str) or not value or "/" not in value:
        raise B25CorpusError("repository slug is missing or malformed")
    owner, repo = value.split("/", 1)
    pattern = r"[A-Za-z0-9_.-]+"
    if not owner or not repo or not re.fullmatch(pattern, owner) or not re.fullmatch(
        pattern, repo
    ):
        raise B25CorpusError("repository slug is missing or malformed")
    return value.casefold()


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
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise B25CorpusError("current source checkpoint could not be verified")
    return head


def _paths_overlap(left: Path, right: Path) -> bool:
    left_resolved = left.resolve(strict=False)
    right_resolved = right.resolve(strict=False)
    try:
        left_resolved.relative_to(right_resolved)
        return True
    except ValueError:
        pass
    try:
        right_resolved.relative_to(left_resolved)
        return True
    except ValueError:
        return False


def _validate_private_layout(private_root: Path, runtime_scratch: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if _paths_overlap(private_root, repo_root):
        raise B25CorpusError("B2.5 private root must remain outside the checkout")
    if _paths_overlap(private_root, runtime_scratch):
        raise B25CorpusError("runtime admission scratch must be separate from private root")


def validate_qualification_publication_gate(
    *,
    runtime_qualification_report_path: Path,
    runtime_qualification_checkpoint: str,
    runtime_qualification_ci_run_id: int,
    runtime_qualification_ci_conclusion: str,
    require_current_head: bool,
) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", runtime_qualification_checkpoint):
        raise B25CorpusError("runtime qualification checkpoint must be a full commit SHA")
    if not isinstance(runtime_qualification_ci_run_id, int) or (
        runtime_qualification_ci_run_id <= 0
    ):
        raise B25CorpusError("runtime qualification CI run id must be positive")
    if runtime_qualification_ci_conclusion != "success":
        raise B25CorpusError("runtime qualification publication CI must succeed")
    repo_root = Path(__file__).resolve().parents[1]
    if require_current_head and _git_head(repo_root) != runtime_qualification_checkpoint:
        raise B25CorpusError("checkout is not the runtime qualification checkpoint")
    report_path = Path(runtime_qualification_report_path).resolve(strict=True)
    try:
        relative = report_path.relative_to(repo_root.resolve(strict=True)).as_posix()
    except ValueError as exc:
        raise B25CorpusError("runtime qualification report must be tracked in checkout") from exc
    completed = subprocess.run(
        ["git", "show", f"{runtime_qualification_checkpoint}:{relative}"],
        cwd=repo_root,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise B25CorpusError("runtime qualification report is absent from checkpoint")
    if hashlib.sha256(completed.stdout).hexdigest() != b2c.file_sha256(report_path):
        raise B25CorpusError("runtime qualification report bytes differ from checkpoint")


def historical_repository_sets(
    historical_repo_locks: Mapping[str, Mapping[str, Any]],
) -> tuple[set[str], set[tuple[str, str]], dict[str, str]]:
    if tuple(sorted(historical_repo_locks)) != tuple(sorted(HISTORICAL_FRAME_LABELS)):
        raise B25CorpusError("historical repository lock labels must be b2, b21, and b24")
    slugs: set[str] = set()
    identities: set[tuple[str, str]] = set()
    digests: dict[str, str] = {}
    for label in HISTORICAL_FRAME_LABELS:
        validated = b2c.validate_repo_lock(
            dict(historical_repo_locks[label]), require_sources=False
        )
        frame_slugs = {_repo_slug(row["source"]["repo"]) for row in validated["repos"]}
        frame_identities = {
            (_repo_slug(row["source"]["repo"]), row["commit"])
            for row in validated["repos"]
        }
        if len(frame_slugs) != 12 or len(frame_identities) != 12:
            raise B25CorpusError(
                f"historical {label} frame is not an exact 12-repository identity set"
            )
        if slugs & frame_slugs or identities & frame_identities:
            raise B25CorpusError("historical B2, B2.1, and B2.4 frames overlap")
        slugs.update(frame_slugs)
        identities.update(frame_identities)
        digests[label] = validated["repo_lock_digest"]
    if len(slugs) != 36 or len(identities) != 36:
        raise B25CorpusError("historical frame union is not 36 distinct repositories")
    return slugs, identities, digests


def validate_exclusion_registry(raw: Any) -> dict[str, Any]:
    try:
        return b24c.validate_exclusion_registry(raw)
    except b24c.B24CorpusError as exc:
        raise B25CorpusError(str(exc)) from exc


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
        raise B25CorpusError("candidate plan has non-closed shape")
    if candidate_plan["schema_version"] != B25_CANDIDATE_PLAN_SCHEMA:
        raise B25CorpusError("candidate plan schema mismatch")
    slots = candidate_plan["slots"]
    if not isinstance(slots, list) or len(slots) != 12:
        raise B25CorpusError("candidate plan must contain exactly 12 slot rows")
    historical_slugs, _, _ = historical_repository_sets(historical_repo_locks)
    excluded_slugs = exclusion_repository_slugs(exclusion_registry)
    expected_slots = {slot.repo_slot for slot in b2p.build_task_slots()}
    seen_slots: set[str] = set()
    candidates: list[str] = []
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"repo_slot", "candidates"}:
            raise B25CorpusError("candidate slot has non-closed shape")
        repo_slot = slot["repo_slot"]
        if repo_slot not in expected_slots or repo_slot in seen_slots:
            raise B25CorpusError("candidate slot is unknown or duplicated")
        seen_slots.add(repo_slot)
        rows = slot["candidates"]
        if not isinstance(rows, list) or len(rows) < 2:
            raise B25CorpusError("each B2.5 slot requires at least two frozen candidates")
        for candidate in rows:
            if not isinstance(candidate, dict) or set(candidate) != {
                "repo",
                "expected_license",
            }:
                raise B25CorpusError("candidate row has non-closed shape")
            slug = _repo_slug(candidate["repo"])
            if not isinstance(candidate["expected_license"], str) or not candidate[
                "expected_license"
            ].strip():
                raise B25CorpusError("candidate expected license is missing")
            if slug in historical_slugs:
                raise B25CorpusError("historical repository reused in B2.5 candidate plan")
            if slug in excluded_slugs:
                raise B25CorpusError("excluded repository reused in B2.5 candidate plan")
            candidates.append(slug)
    if seen_slots != expected_slots:
        raise B25CorpusError("candidate plan slot coverage is incomplete")
    if len(candidates) != len(set(candidates)):
        raise B25CorpusError("candidate repositories must not repeat across slots")
    return tuple(candidates)


def holdout_binding_digest(binding: Mapping[str, Any]) -> str:
    payload = dict(binding)
    payload.pop("holdout_binding_digest", None)
    return _prefixed_digest("b25holdout_", payload)


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
    runtime_qualification_report: Mapping[str, Any],
    runtime_qualification_report_path: Path,
    runtime_qualification_private_receipt: Mapping[str, Any],
    runtime_qualification_private_receipt_path: Path,
    runtime_qualification_checkpoint: str,
    runtime_qualification_ci_run_id: int,
    runtime_qualification_ci_conclusion: str,
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
    public_errors = b25rq.validate_public_report(runtime_qualification_report)
    private_errors = b25rq.validate_private_receipt(
        runtime_qualification_private_receipt
    )
    if public_errors or private_errors:
        raise B25CorpusError("runtime qualification inputs are invalid")
    if runtime_qualification_private_receipt["public_qualification_digest"] != (
        runtime_qualification_report["qualification_digest"]
    ):
        raise B25CorpusError("runtime qualification public/private binding mismatch")
    historical_slugs, historical_identities, historical_digests = (
        historical_repository_sets(historical_repo_locks)
    )
    if set(historical_repo_lock_paths) != set(HISTORICAL_FRAME_LABELS):
        raise B25CorpusError("historical repository lock paths are incomplete")
    excluded_slugs = exclusion_repository_slugs(exclusion_registry)
    new_slugs: set[str] = set()
    new_identities: set[tuple[str, str]] = set()
    for row in new_lock["repos"]:
        slug = _repo_slug(row["source"]["repo"])
        identity = (slug, row["commit"])
        if slug not in candidates:
            raise B25CorpusError("selected repository is absent from candidate plan")
        if slug in historical_slugs or identity in historical_identities:
            raise B25CorpusError("selected B2.5 repository overlaps a historical frame")
        if slug in excluded_slugs:
            raise B25CorpusError("selected B2.5 repository overlaps exclusion registry")
        new_slugs.add(slug)
        new_identities.add(identity)
    if len(new_slugs) != 12 or len(new_identities) != 12:
        raise B25CorpusError("B2.5 selected frame is not 12 distinct identities")
    binding: dict[str, Any] = {
        "schema_version": B25_HOLDOUT_BINDING_SCHEMA,
        "corpus_version": B25_CORPUS_VERSION,
        "b25_spec_digest": b25_spec_digest(),
        "b25_holdout_frame_digest": b25_holdout_frame_digest(),
        "b25_execution_schedule_digest": b25_execution_schedule_digest(),
        "parent_b24_failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
        "parent_b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
        "parent_b23_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
        "runtime_qualification_digest": runtime_qualification_report[
            "qualification_digest"
        ],
        "runtime_qualification_report_file_sha256": b2c.file_sha256(
            runtime_qualification_report_path
        ),
        "runtime_qualification_private_receipt_digest": (
            runtime_qualification_private_receipt["private_receipt_digest"]
        ),
        "runtime_qualification_private_receipt_file_sha256": b2c.file_sha256(
            runtime_qualification_private_receipt_path
        ),
        "runtime_qualification_checkpoint": runtime_qualification_checkpoint,
        "runtime_qualification_ci_run_id": runtime_qualification_ci_run_id,
        "runtime_qualification_ci_conclusion": runtime_qualification_ci_conclusion,
        "new_repo_lock_digest": new_lock["repo_lock_digest"],
        "new_task_manifest_digest": new_task_manifest["task_manifest_digest"],
        "new_oracle_manifest_digest": new_oracle_manifest["oracle_manifest_digest"],
        "query_gate_digest": query["query_gate_digest"],
        "query_gate_file_sha256": b2c.file_sha256(query_report_path),
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
        "all_queries_tokenizable": True,
        "all_positive_spans_compatible": True,
        "holdout_binding_digest": "",
    }
    binding["holdout_binding_digest"] = holdout_binding_digest(binding)
    return binding


def validate_holdout_binding(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_holdout_binding(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B25CorpusError("B2.5 holdout binding drifted from private inputs")
    return raw


def _runtime_inputs(
    *,
    runtime_qualification_report_path: Path,
    runtime_qualification_private_receipt_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        b2c.load_json(runtime_qualification_report_path),
        b2c.load_json(runtime_qualification_private_receipt_path),
    )


def prepare_fresh_holdout(
    *,
    candidate_plan_path: Path,
    private_root: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_qualification_report_path: Path,
    runtime_qualification_private_receipt_path: Path,
    qualification_private_receipt_path: Path,
    runtime_admission_scratch_root: Path,
    runtime_qualification_checkpoint: str,
    runtime_qualification_ci_run_id: int,
    runtime_qualification_ci_conclusion: str,
    cli_path: Path,
) -> dict[str, Any]:
    private_root = Path(private_root)
    _validate_private_layout(private_root, Path(runtime_admission_scratch_root))
    if private_root.exists() and any(private_root.iterdir()):
        raise B25CorpusError("B2.5 private root must be absent or empty before authoring")
    validate_qualification_publication_gate(
        runtime_qualification_report_path=runtime_qualification_report_path,
        runtime_qualification_checkpoint=runtime_qualification_checkpoint,
        runtime_qualification_ci_run_id=runtime_qualification_ci_run_id,
        runtime_qualification_ci_conclusion=runtime_qualification_ci_conclusion,
        require_current_head=True,
    )
    b25rq.validate_runtime_binding(
        public_report_path=runtime_qualification_report_path,
        private_receipt_path=runtime_qualification_private_receipt_path,
        cli_path=cli_path,
        qualification_private_receipt_path=qualification_private_receipt_path,
        scratch_root=runtime_admission_scratch_root,
    )
    candidate_plan = b2c.load_json(candidate_plan_path)
    historical_locks = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in HISTORICAL_FRAME_LABELS
    }
    registry = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    validate_fresh_candidate_plan(
        candidate_plan,
        historical_repo_locks=historical_locks,
        exclusion_registry=registry,
    )
    author = importlib.import_module("product_bakeoff_b2_author")
    if getattr(author, "B2_CANDIDATE_PLAN_SCHEMA", None) != B25_CANDIDATE_PLAN_SCHEMA:
        raise B25CorpusError("candidate plan schema drifted from frozen B2 author")
    result = author.prepare_private_manifests(
        candidate_plan=candidate_plan_path,
        private_root=private_root,
    )
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    query_path = private_root / "b25_private_query_compatibility.json"
    query_report = b25q.build_query_compatibility_report(
        repo_lock=b2c.load_json(repo_path),
        task_manifest=b2c.load_json(task_path),
        oracle_manifest=b2c.load_json(oracle_path),
    )
    b25q.write_private_report(query_path, query_report)
    runtime_public, runtime_private = _runtime_inputs(
        runtime_qualification_report_path=runtime_qualification_report_path,
        runtime_qualification_private_receipt_path=(
            runtime_qualification_private_receipt_path
        ),
    )
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
        runtime_qualification_report=runtime_public,
        runtime_qualification_report_path=runtime_qualification_report_path,
        runtime_qualification_private_receipt=runtime_private,
        runtime_qualification_private_receipt_path=(
            runtime_qualification_private_receipt_path
        ),
        runtime_qualification_checkpoint=runtime_qualification_checkpoint,
        runtime_qualification_ci_run_id=runtime_qualification_ci_run_id,
        runtime_qualification_ci_conclusion=runtime_qualification_ci_conclusion,
    )
    binding_path = private_root / "b25_private_holdout_binding.json"
    b2c.write_json(binding_path, binding)
    return {
        **result,
        "holdout_binding_path": str(binding_path.resolve()),
        "query_gate_path": str(query_path.resolve()),
        "repo_count": 12,
        "task_count": 48,
    }


def b25_runtime_bundle_digest(
    cli_path: str | Path,
    *,
    runtime_qualification_digest: str,
    runtime_qualification_private_receipt_digest: str,
) -> str:
    path = Path(cli_path).resolve(strict=True)
    if path.is_symlink() or not path.is_file():
        raise B25CorpusError("OpenLocus CLI path is missing or unsafe")
    return _prefixed_digest(
        "b25run_",
        {
            "b25_source_bundle_digest": b25_source_bundle_digest(),
            "cli_bytes": path.stat().st_size,
            "cli_sha256": b2c.file_sha256(path),
            "runtime_qualification_digest": runtime_qualification_digest,
            "runtime_qualification_private_receipt_digest": (
                runtime_qualification_private_receipt_digest
            ),
            "request_timeout_seconds": B25_REQUEST_TIMEOUT_SECONDS,
            "adapter_command_timeout_seconds": B25_ADAPTER_COMMAND_TIMEOUT_SECONDS,
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
    runtime_qualification_private_receipt_digest: str,
    repo_lock_path: Path,
    task_manifest_path: Path,
    oracle_manifest_path: Path,
    holdout_binding_path: Path,
    query_report_path: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_qualification_report_path: Path,
    runtime_qualification_private_receipt_path: Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    if set(historical_repo_lock_paths) != set(HISTORICAL_FRAME_LABELS):
        raise B25CorpusError("historical repository lock paths are incomplete")
    receipt: dict[str, Any] = {
        "schema_version": B25_FREEZE_RECEIPT_SCHEMA,
        "b25_spec_digest": b25_spec_digest(),
        "b25_holdout_frame_digest": b25_holdout_frame_digest(),
        "b25_execution_schedule_digest": b25_execution_schedule_digest(),
        "b21_execution_schedule_digest": b25_execution_schedule_digest(),
        "parent_b24_failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
        "parent_b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
        "parent_b23_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
        "runtime_qualification_digest": runtime_qualification_digest,
        "runtime_qualification_private_receipt_digest": (
            runtime_qualification_private_receipt_digest
        ),
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
            for label in HISTORICAL_FRAME_LABELS
        },
        "exclusion_registry_file_sha256": b2c.file_sha256(exclusion_registry_path),
        "runtime_qualification_report_file_sha256": b2c.file_sha256(
            runtime_qualification_report_path
        ),
        "runtime_qualification_private_receipt_file_sha256": b2c.file_sha256(
            runtime_qualification_private_receipt_path
        ),
        "request_timeout_seconds": B25_REQUEST_TIMEOUT_SECONDS,
        "adapter_command_timeout_seconds": B25_ADAPTER_COMMAND_TIMEOUT_SECONDS,
        "source_bundle_digest": b25_source_bundle_digest(),
        "runtime_bundle_digest": b25_runtime_bundle_digest(
            cli_path,
            runtime_qualification_digest=runtime_qualification_digest,
            runtime_qualification_private_receipt_digest=(
                runtime_qualification_private_receipt_digest
            ),
        ),
        "freeze_receipt_digest": "",
    }
    receipt["freeze_receipt_digest"] = _prefixed_digest("b25freeze_", receipt)
    return receipt


def validate_freeze_receipt(raw: Any, **kwargs: Any) -> dict[str, Any]:
    expected = build_freeze_receipt(**kwargs)
    if not isinstance(raw, dict) or raw != expected:
        raise B25CorpusError("B2.5 freeze receipt drifted from locked inputs/runtime")
    return raw


def _loaded_private_inputs(
    private_root: Path,
) -> tuple[Path, Path, Path, Path, Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    query_path = private_root / "b25_private_query_compatibility.json"
    binding_path = private_root / "b25_private_holdout_binding.json"
    return (
        repo_path,
        task_path,
        oracle_path,
        query_path,
        binding_path,
        b2c.load_json(repo_path),
        b2c.load_json(task_path),
        b2c.load_json(oracle_path),
        b2c.load_json(query_path),
        b2c.load_json(binding_path),
    )


def freeze_fresh_holdout(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_qualification_report_path: Path,
    runtime_qualification_private_receipt_path: Path,
    qualification_private_receipt_path: Path,
    runtime_admission_scratch_root: Path,
    runtime_qualification_checkpoint: str,
    runtime_qualification_ci_run_id: int,
    runtime_qualification_ci_conclusion: str,
    cli_path: str | Path,
) -> dict[str, Any]:
    private_root = Path(private_root)
    _validate_private_layout(private_root, Path(runtime_admission_scratch_root))
    receipt_path = private_root / "b25_private_freeze_receipt.json"
    if receipt_path.exists():
        raise B25CorpusError("B2.5 freeze receipt already exists")
    validate_qualification_publication_gate(
        runtime_qualification_report_path=runtime_qualification_report_path,
        runtime_qualification_checkpoint=runtime_qualification_checkpoint,
        runtime_qualification_ci_run_id=runtime_qualification_ci_run_id,
        runtime_qualification_ci_conclusion=runtime_qualification_ci_conclusion,
        require_current_head=True,
    )
    runtime_public, runtime_private = b25rq.validate_runtime_binding(
        public_report_path=runtime_qualification_report_path,
        private_receipt_path=runtime_qualification_private_receipt_path,
        cli_path=Path(cli_path),
        qualification_private_receipt_path=qualification_private_receipt_path,
        scratch_root=runtime_admission_scratch_root,
    )
    (
        repo_path,
        task_path,
        oracle_path,
        query_path,
        binding_path,
        repo_lock,
        task_manifest,
        oracle_manifest,
        query_report,
        binding,
    ) = _loaded_private_inputs(private_root)
    candidate_plan = b2c.load_json(candidate_plan_path)
    historical_locks = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in HISTORICAL_FRAME_LABELS
    }
    registry = validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    recomputed_query = b25q.build_query_compatibility_report(
        repo_lock=repo_lock,
        task_manifest=task_manifest,
        oracle_manifest=oracle_manifest,
    )
    if recomputed_query != query_report:
        raise B25CorpusError("B2.5 query compatibility report drifted before freeze")
    validate_holdout_binding(
        binding,
        new_repo_lock=repo_lock,
        new_task_manifest=task_manifest,
        new_oracle_manifest=oracle_manifest,
        query_report=query_report,
        query_report_path=query_path,
        candidate_plan=candidate_plan,
        candidate_plan_path=candidate_plan_path,
        historical_repo_locks=historical_locks,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry=registry,
        exclusion_registry_path=exclusion_registry_path,
        runtime_qualification_report=runtime_public,
        runtime_qualification_report_path=runtime_qualification_report_path,
        runtime_qualification_private_receipt=runtime_private,
        runtime_qualification_private_receipt_path=(
            runtime_qualification_private_receipt_path
        ),
        runtime_qualification_checkpoint=runtime_qualification_checkpoint,
        runtime_qualification_ci_run_id=runtime_qualification_ci_run_id,
        runtime_qualification_ci_conclusion=runtime_qualification_ci_conclusion,
    )
    receipt = build_freeze_receipt(
        repo_lock_digest=repo_lock["repo_lock_digest"],
        task_manifest_digest=task_manifest["task_manifest_digest"],
        oracle_manifest_digest=oracle_manifest["oracle_manifest_digest"],
        holdout_binding_digest_value=binding["holdout_binding_digest"],
        query_gate_digest_value=query_report["query_gate_digest"],
        runtime_qualification_digest=runtime_public["qualification_digest"],
        runtime_qualification_private_receipt_digest=runtime_private[
            "private_receipt_digest"
        ],
        repo_lock_path=repo_path,
        task_manifest_path=task_path,
        oracle_manifest_path=oracle_path,
        holdout_binding_path=binding_path,
        query_report_path=query_path,
        candidate_plan_path=candidate_plan_path,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry_path=exclusion_registry_path,
        runtime_qualification_report_path=runtime_qualification_report_path,
        runtime_qualification_private_receipt_path=(
            runtime_qualification_private_receipt_path
        ),
        cli_path=cli_path,
    )
    b2c.write_json(receipt_path, receipt)
    return {**receipt, "freeze_receipt_path": str(receipt_path.resolve())}


def launch_authorization_digest(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("launch_authorization_digest", None)
    return _prefixed_digest("b25launch_", payload)


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
        raise B25CorpusError("readiness checkpoint must be a full commit SHA")
    if not isinstance(readiness_ci_run_id, int) or readiness_ci_run_id <= 0:
        raise B25CorpusError("readiness CI run id must be positive")
    if readiness_ci_conclusion != "success":
        raise B25CorpusError("readiness CI must conclude success")
    readiness = importlib.import_module("product_bakeoff_b25_readiness")
    if readiness.validate_public_readiness(dict(readiness_report)):
        raise B25CorpusError("public readiness report is invalid")
    decision = readiness_report["decision"]
    if decision["private_holdout_frozen"] is not True:
        raise B25CorpusError("public readiness did not freeze the holdout")
    if decision["treatment_output_exists"] is not False:
        raise B25CorpusError("public readiness already contains treatment output")
    authorization: dict[str, Any] = {
        "schema_version": B25_LAUNCH_AUTHORIZATION_SCHEMA,
        "b25_spec_digest": b25_spec_digest(),
        "source_bundle_digest": freeze_receipt["source_bundle_digest"],
        "runtime_bundle_digest": freeze_receipt["runtime_bundle_digest"],
        "runtime_qualification_digest": freeze_receipt[
            "runtime_qualification_digest"
        ],
        "query_gate_digest": freeze_receipt["query_gate_digest"],
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
        raise B25CorpusError("B2.5 launch authorization drifted")
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
    freeze_path = private_root / "b25_private_freeze_receipt.json"
    authorization_path = private_root / "b25_private_launch_authorization.json"
    if authorization_path.exists():
        raise B25CorpusError("B2.5 launch authorization already exists")
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


def _synthetic_locks() -> dict[str, dict[str, Any]]:
    return {
        "b2": b24c._synthetic_lock("b2old"),
        "b21": b24c._synthetic_lock("b21old"),
        "b24": b24c._synthetic_lock("b24old"),
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
                    {"repo": f"new-owner/new-repo-{index}-b", "expected_license": "MIT"},
                ],
            }
        )
    return {"schema_version": B25_CANDIDATE_PLAN_SCHEMA, "slots": slots}


def run_self_test() -> dict[str, Any]:
    locks = _synthetic_locks()
    slugs, identities, digests = historical_repository_sets(locks)
    registry = b24c._synthetic_registry()
    candidates = validate_fresh_candidate_plan(
        _synthetic_candidate_plan(),
        historical_repo_locks=locks,
        exclusion_registry=registry,
    )
    checks: list[tuple[str, bool]] = [
        ("historical_slug_count", len(slugs) == 36),
        ("historical_identity_count", len(identities) == 36),
        ("historical_digest_count", len(digests) == 3),
        ("candidate_count", len(candidates) == 24),
        ("registry_valid", validate_exclusion_registry(registry) == registry),
    ]
    with tempfile.TemporaryDirectory(prefix="openlocus-b25-freeze-") as temporary:
        root = Path(temporary)
        files = []
        for index in range(12):
            path = root / f"f{index}.json"
            path.write_text("{}\n", encoding="utf-8")
            files.append(path)
        cli = root / "openlocus.bin"
        cli.write_bytes(b"b25-test-runtime")
        kwargs = {
            "repo_lock_digest": "b2repos_" + "1" * 64,
            "task_manifest_digest": "b2tasks_" + "2" * 64,
            "oracle_manifest_digest": "b2oracles_" + "3" * 64,
            "holdout_binding_digest_value": "b25holdout_" + "4" * 64,
            "query_gate_digest_value": "b25query_" + "5" * 64,
            "runtime_qualification_digest": "b25qual_" + "6" * 64,
            "runtime_qualification_private_receipt_digest": "b25qpriv_" + "7" * 64,
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
            },
            "exclusion_registry_path": files[9],
            "runtime_qualification_report_path": files[10],
            "runtime_qualification_private_receipt_path": files[11],
            "cli_path": cli,
        }
        receipt = build_freeze_receipt(**kwargs)
        checks.append(("freeze_roundtrip", validate_freeze_receipt(receipt, **kwargs) == receipt))
        checks.append(("runtime_digest", receipt["runtime_bundle_digest"].startswith("b25run_")))
        checks.append(("query_bound", receipt["query_gate_digest"].startswith("b25query_")))
        readiness = importlib.import_module("product_bakeoff_b25_readiness")
        readiness_report = readiness._build_report(
            preauthoring_checkpoint="a" * 40,
            preauthoring_ci_run_id=1,
            preauthoring_ci_conclusion="success",
            runtime_qualification_digest="b25qual_" + "6" * 64,
            runtime_qualification_file_sha256="8" * 64,
            observed_margins=readiness._frozen_margins(),
            historical_repository_count=36,
            excluded_repository_count=2,
            excluded_synthetic_source_count=1,
            query_gate={
                "task_count": 48,
                "tokenizable_query_count": 48,
                "answerable_task_count": 42,
                "abstain_task_count": 6,
                "positive_span_count": 48,
                "compatible_positive_span_count": 48,
                "all_queries_tokenizable": True,
                "all_positive_spans_compatible": True,
            },
        )
        freeze_path = root / "freeze.json"
        readiness_path = root / "readiness.json"
        b2c.write_json(freeze_path, receipt)
        b2c.write_json(readiness_path, readiness_report)
        authorization_kwargs = {
            "freeze_receipt": receipt,
            "freeze_receipt_path": freeze_path,
            "readiness_report": readiness_report,
            "readiness_report_path": readiness_path,
            "readiness_checkpoint": "b" * 40,
            "readiness_ci_run_id": 2,
            "readiness_ci_conclusion": "success",
        }
        authorization = build_launch_authorization(**authorization_kwargs)
        checks.append(
            (
                "launch_authorization_roundtrip",
                validate_launch_authorization(
                    authorization, **authorization_kwargs
                )
                == authorization,
            )
        )
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    locks = _synthetic_locks()
    registry = b24c._synthetic_registry()
    checks: list[tuple[str, bool]] = []
    for name, slug in (
        ("b2_overlap", locks["b2"]["repos"][0]["source"]["repo"]),
        ("b21_overlap", locks["b21"]["repos"][0]["source"]["repo"]),
        ("b24_overlap", locks["b24"]["repos"][0]["source"]["repo"]),
        ("registry_overlap", registry["repositories"][0]["repo"]),
    ):
        try:
            validate_fresh_candidate_plan(
                _synthetic_candidate_plan(first_slug=slug),
                historical_repo_locks=locks,
                exclusion_registry=registry,
            )
            rejected = False
        except B25CorpusError:
            rejected = True
        checks.append((name, rejected))
    malformed = _synthetic_candidate_plan()
    malformed["slots"][0]["candidates"] = malformed["slots"][0]["candidates"][:1]
    try:
        validate_fresh_candidate_plan(
            malformed,
            historical_repo_locks=locks,
            exclusion_registry=registry,
        )
        one_candidate_rejected = False
    except B25CorpusError:
        one_candidate_rejected = True
    checks.append(("single_candidate_slot_rejected", one_candidate_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B25CorpusError",
    "B25_CANDIDATE_PLAN_SCHEMA",
    "B25_EXCLUSION_REGISTRY_SCHEMA",
    "B25_HOLDOUT_BINDING_SCHEMA",
    "B25_FREEZE_RECEIPT_SCHEMA",
    "B25_LAUNCH_AUTHORIZATION_SCHEMA",
    "HISTORICAL_FRAME_LABELS",
    "validate_qualification_publication_gate",
    "historical_repository_sets",
    "validate_exclusion_registry",
    "validate_fresh_candidate_plan",
    "build_holdout_binding",
    "validate_holdout_binding",
    "prepare_fresh_holdout",
    "b25_runtime_bundle_digest",
    "build_freeze_receipt",
    "validate_freeze_receipt",
    "freeze_fresh_holdout",
    "build_launch_authorization",
    "validate_launch_authorization",
    "create_launch_authorization",
    "run_self_test",
    "run_fault_test",
]
