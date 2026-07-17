#!/usr/bin/env python3
"""Exact Linux runtime qualification for the B3 control plane.

Qualification is deliberately independent of any historical machine identity.
The current runner must satisfy the frozen B2.3 minimum class, remain stable
across the public synthetic tokenizer matrix, and expose the exact OpenLocus
CLI bytes that will later be admitted.  Exact profile and CLI details are kept
only in the private receipt; the public report contains closed aggregates.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b23_runner_qualification as b23q
import product_bakeoff_b25_runtime_qualification as b25rq
import product_bakeoff_b3_protocol as b3p
import product_bakeoff_b3_source as b3src


REPO = Path(__file__).resolve().parents[1]
PROTOCOL_REPORT = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_protocol"
    / "product_bakeoff_b3_protocol_report.json"
)

B3_RUNTIME_VERSION = "product_bakeoff_b3_runtime_qualification.v1"
B3_RUNTIME_PUBLIC_SCHEMA = "product_bakeoff_b3_runtime_qualification_public.v1"
B3_RUNTIME_PRIVATE_SCHEMA = "product_bakeoff_b3_runtime_qualification_private.v1"
B3_RUNTIME_STATUS = (
    "product_bakeoff_b3_exact_linux_runtime_qualified_"
    "private_authoring_allowed_after_publication_ci"
)
B3_RUNTIME_CLAIM = "public_synthetic_runtime_integrity_only_no_private_holdout"
B3_RUNTIME_CASE_CATEGORIES = tuple(
    str(row["category"]) for row in b25rq.B25_RUNTIME_CASES
)
B3_RUNTIME_PROFILE_KEYS = frozenset(
    {
        *b23q.STABLE_PROFILE_KEYS,
        "host_total_memory_bytes",
        "host_available_memory_bytes",
        "cgroup_memory_current_bytes",
        "cgroup_available_memory_bytes",
        "scratch_free_bytes",
        "active_idle_cgroup_cpu_millicores",
    }
)
B3_RUNTIME_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "exact_synthetic_query_or_source_public": False,
    "exact_cli_or_runtime_fingerprint_public": False,
    "exact_runner_profile_or_location_public": False,
    "private_receipt_digest_public": False,
    "private_repository_task_or_oracle_public": False,
}


class B3RuntimeQualificationError(ValueError):
    """Fail-closed B3 runtime qualification error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    return b2c.file_sha256(Path(path))


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
        raise B3RuntimeQualificationError("current source checkpoint unavailable")
    return value


def _validate_source_checkpoint(checkpoint: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", checkpoint):
        raise B3RuntimeQualificationError("source checkpoint must be a full commit SHA")
    if b3p.validate_parent_locks():
        raise B3RuntimeQualificationError("B3 parent locks are invalid")
    try:
        b3src.validate_source_checkpoint(checkpoint)
    except b3src.B3SourceError as exc:
        raise B3RuntimeQualificationError(
            "B3 control source differs from source checkpoint"
        ) from exc
    protocol = b2c.load_json(PROTOCOL_REPORT)
    if b3p.validate_report(protocol):
        raise B3RuntimeQualificationError("B3 protocol report is invalid")
    relative = PROTOCOL_REPORT.relative_to(REPO).as_posix()
    completed = subprocess.run(
        ["git", "show", f"{checkpoint}:{relative}"],
        cwd=REPO,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise B3RuntimeQualificationError("B3 protocol report absent from checkpoint")
    frozen_raw = completed.stdout.replace(b"\r\n", b"\n")
    current_raw = PROTOCOL_REPORT.read_bytes().replace(b"\r\n", b"\n")
    if frozen_raw != current_raw:
        raise B3RuntimeQualificationError("B3 protocol report differs from checkpoint")


def qualification_digest(report: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(report))
    payload.pop("qualification_digest", None)
    return _digest("b3qual_", payload)


def private_receipt_digest(receipt: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(receipt))
    payload.pop("private_receipt_digest", None)
    return _digest("b3qpriv_", payload)


def _build_public_report(
    *,
    source_checkpoint: str,
    source_ci_run_id: int,
    source_ci_conclusion: str,
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    passed = len(case_rows) == len(B3_RUNTIME_CASE_CATEGORIES) and all(
        row.get("passed") is True for row in case_rows
    )
    report: dict[str, Any] = {
        "schema_version": B3_RUNTIME_PUBLIC_SCHEMA,
        "qualification_version": B3_RUNTIME_VERSION,
        "phase": "product_bakeoff_b3_exact_linux_runtime_qualification",
        "status": B3_RUNTIME_STATUS,
        "claim_level": B3_RUNTIME_CLAIM,
        "date": "2026-07-17",
        "source_gate": {
            "checkpoint": source_checkpoint,
            "ci_run_id": source_ci_run_id,
            "ci_conclusion": source_ci_conclusion,
            "b3_spec_digest": b3p.spec_digest(),
            "b3_control_source_bundle_digest": b3src.control_source_bundle_digest(),
        },
        "runner_gate": {
            "minimum_runner_class": copy.deepcopy(b23q.B23_RUNNER_CLASS),
            "current_runner_class_admitted": True,
            "stable_profile_unchanged_during_qualification": True,
            "exact_current_profile_frozen_privately": True,
            "historical_machine_identity_required": False,
            "exact_runner_profile_public": False,
        },
        "synthetic_matrix": {
            "case_count": len(case_rows),
            "case_categories": list(B3_RUNTIME_CASE_CATEGORIES),
            "passed_case_count": sum(row.get("passed") is True for row in case_rows),
            "actual_production_cli_used": True,
            "actual_production_bakeoff_query_parser_used": True,
            "private_input_read": False,
            "all_cases_returned_current_evidence": all(
                row.get("current_evidence") is True for row in case_rows
            ),
            "all_bm25_receipts_executed": all(
                row.get("bm25_executed") is True for row in case_rows
            ),
            "all_stale_hits_skipped_zero": all(
                row.get("stale_hits_skipped") == 0 for row in case_rows
            ),
            "all_invalid_hits_skipped_zero": all(
                row.get("invalid_hits_skipped") == 0 for row in case_rows
            ),
            "provider_network_call_count": sum(
                int(row.get("provider_remote_calls", 0))
                + int(row.get("provider_outbound_calls", 0))
                for row in case_rows
            ),
        },
        "decision": {
            "runtime_qualified": passed,
            "fresh_private_holdout_authoring_allowed_after_green_publication_ci": passed,
            "tournament_execution_authorized": False,
            "private_holdout_read": False,
            "treatment_output_exists": False,
            "tournament_result_exists": False,
        },
        "publication_limits": copy.deepcopy(B3_RUNTIME_PUBLICATION_LIMITS),
        "next_authorized_action": (
            "Commit this aggregate-only qualification and obtain green public CI; "
            "then author and freeze one new B3 holdout excluding B2, B2.1, B2.4, "
            "and B2.5 repositories."
        ),
        "qualification_digest": "",
    }
    report["qualification_digest"] = qualification_digest(report)
    return report


def validate_public_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 runtime public report must be an object"]
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "qualification_version",
        "phase",
        "status",
        "claim_level",
        "date",
        "source_gate",
        "runner_gate",
        "synthetic_matrix",
        "decision",
        "publication_limits",
        "next_authorized_action",
        "qualification_digest",
    }
    if set(report) != expected_keys:
        errors.append("B3 runtime public report shape drifted")
    if report.get("schema_version") != B3_RUNTIME_PUBLIC_SCHEMA:
        errors.append("B3 runtime public schema drifted")
    if report.get("qualification_version") != B3_RUNTIME_VERSION:
        errors.append("B3 runtime qualification version drifted")
    if report.get("status") != B3_RUNTIME_STATUS:
        errors.append("B3 runtime public status drifted")
    if report.get("claim_level") != B3_RUNTIME_CLAIM:
        errors.append("B3 runtime claim drifted")
    source = report.get("source_gate") or {}
    if set(source) != {
        "checkpoint",
        "ci_run_id",
        "ci_conclusion",
        "b3_spec_digest",
        "b3_control_source_bundle_digest",
    }:
        errors.append("B3 runtime source gate shape drifted")
    if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("checkpoint", ""))):
        errors.append("B3 runtime source checkpoint malformed")
    if not isinstance(source.get("ci_run_id"), int) or source.get("ci_run_id", 0) <= 0:
        errors.append("B3 runtime source CI run id malformed")
    if source.get("ci_conclusion") != "success":
        errors.append("B3 runtime source CI did not succeed")
    if source.get("b3_spec_digest") != b3p.spec_digest():
        errors.append("B3 runtime spec binding drifted")
    if source.get("b3_control_source_bundle_digest") != b3src.control_source_bundle_digest():
        errors.append("B3 runtime control source binding drifted")
    expected_runner = {
        "minimum_runner_class": copy.deepcopy(b23q.B23_RUNNER_CLASS),
        "current_runner_class_admitted": True,
        "stable_profile_unchanged_during_qualification": True,
        "exact_current_profile_frozen_privately": True,
        "historical_machine_identity_required": False,
        "exact_runner_profile_public": False,
    }
    if report.get("runner_gate") != expected_runner:
        errors.append("B3 runtime runner gate drifted")
    matrix = report.get("synthetic_matrix") or {}
    expected_matrix = {
        "case_count": len(B3_RUNTIME_CASE_CATEGORIES),
        "case_categories": list(B3_RUNTIME_CASE_CATEGORIES),
        "passed_case_count": len(B3_RUNTIME_CASE_CATEGORIES),
        "actual_production_cli_used": True,
        "actual_production_bakeoff_query_parser_used": True,
        "private_input_read": False,
        "all_cases_returned_current_evidence": True,
        "all_bm25_receipts_executed": True,
        "all_stale_hits_skipped_zero": True,
        "all_invalid_hits_skipped_zero": True,
        "provider_network_call_count": 0,
    }
    if matrix != expected_matrix:
        errors.append("B3 runtime synthetic matrix drifted")
    expected_decision = {
        "runtime_qualified": True,
        "fresh_private_holdout_authoring_allowed_after_green_publication_ci": True,
        "tournament_execution_authorized": False,
        "private_holdout_read": False,
        "treatment_output_exists": False,
        "tournament_result_exists": False,
    }
    if report.get("decision") != expected_decision:
        errors.append("B3 runtime decision drifted")
    if report.get("publication_limits") != B3_RUNTIME_PUBLICATION_LIMITS:
        errors.append("B3 runtime publication limits drifted")
    if report.get("qualification_digest") != qualification_digest(report):
        errors.append("B3 runtime qualification digest mismatch")
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "_hidden_symbol",
        "public_symbol",
        "feature.flag",
        "b3qpriv_",
        "openlocus_sha256",
        "clone_root",
        "task_slug",
        "repo_lock_digest",
        "oracle_manifest_digest",
        "scratch_mount_source",
    ):
        if token in raw:
            errors.append(f"private or exact B3 runtime token is public: {token}")
    return sorted(set(errors))


def _build_private_receipt(
    *,
    public_report: Mapping[str, Any],
    public_report_file_sha256: str,
    cli_path: Path,
    profile_before: Mapping[str, Any],
    profile_after: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": B3_RUNTIME_PRIVATE_SCHEMA,
        "qualification_version": B3_RUNTIME_VERSION,
        "source_checkpoint": public_report["source_gate"]["checkpoint"],
        "control_source_bundle_digest": b3src.control_source_bundle_digest(),
        "profile_before": dict(profile_before),
        "profile_after": dict(profile_after),
        "stable_profile_changes": b23q.stable_runner_profile_changes(
            profile_before, profile_after
        ),
        "cli_bytes": cli_path.stat().st_size,
        "cli_sha256": _file_sha256(cli_path),
        "synthetic_fixture_digest": _digest(
            "b3fixture_", b25rq._synthetic_fixture_payload()
        ),
        "case_rows": [dict(row) for row in case_rows],
        "private_input_read": False,
        "public_qualification_digest": public_report["qualification_digest"],
        "public_report_file_sha256": public_report_file_sha256,
        "private_receipt_digest": "",
    }
    receipt["private_receipt_digest"] = private_receipt_digest(receipt)
    return receipt


def validate_private_receipt(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict):
        return ["B3 runtime private receipt must be an object"]
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "qualification_version",
        "source_checkpoint",
        "control_source_bundle_digest",
        "profile_before",
        "profile_after",
        "stable_profile_changes",
        "cli_bytes",
        "cli_sha256",
        "synthetic_fixture_digest",
        "case_rows",
        "private_input_read",
        "public_qualification_digest",
        "public_report_file_sha256",
        "private_receipt_digest",
    }
    if set(receipt) != expected_keys:
        errors.append("B3 runtime private receipt shape drifted")
    if receipt.get("schema_version") != B3_RUNTIME_PRIVATE_SCHEMA:
        errors.append("B3 runtime private schema drifted")
    if receipt.get("qualification_version") != B3_RUNTIME_VERSION:
        errors.append("B3 runtime private version drifted")
    if not re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("source_checkpoint", ""))):
        errors.append("B3 runtime private source checkpoint malformed")
    if receipt.get("control_source_bundle_digest") != b3src.control_source_bundle_digest():
        errors.append("B3 runtime private source bundle drifted")
    before = receipt.get("profile_before")
    after = receipt.get("profile_after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        errors.append("B3 runtime profiles malformed")
    else:
        if set(before) != B3_RUNTIME_PROFILE_KEYS or set(after) != B3_RUNTIME_PROFILE_KEYS:
            errors.append("B3 runtime profile shape drifted")
        if b23q.validate_runner_profile(before) or b23q.validate_runner_profile(after):
            errors.append("B3 runtime private profile failed runner class")
        if b23q.stable_runner_profile_changes(before, after):
            errors.append("B3 runtime stable profile changed")
    if receipt.get("stable_profile_changes") != []:
        errors.append("B3 runtime private stable change list is nonempty")
    if not isinstance(receipt.get("cli_bytes"), int) or receipt.get("cli_bytes", 0) <= 0:
        errors.append("B3 runtime private CLI byte count malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("cli_sha256", ""))):
        errors.append("B3 runtime private CLI digest malformed")
    if receipt.get("synthetic_fixture_digest") != _digest(
        "b3fixture_", b25rq._synthetic_fixture_payload()
    ):
        errors.append("B3 runtime private fixture binding drifted")
    rows = receipt.get("case_rows")
    if not isinstance(rows, list) or len(rows) != len(B3_RUNTIME_CASE_CATEGORIES):
        errors.append("B3 runtime private case rows malformed")
    else:
        expected_row_keys = {
            "category",
            "query",
            "task_family",
            "expected_path",
            "expected_line",
            "evidence_count",
            "current_evidence",
            "bm25_executed",
            "stale_hits_skipped",
            "invalid_hits_skipped",
            "provider_remote_calls",
            "provider_outbound_calls",
            "passed",
        }
        for row, case in zip(rows, b25rq.B25_RUNTIME_CASES):
            if not isinstance(row, dict) or set(row) != expected_row_keys:
                errors.append("B3 runtime private case row shape drifted")
                continue
            if row.get("category") != case["category"] or row.get("query") != case["query"]:
                errors.append("B3 runtime private case binding drifted")
            exact = {
                "current_evidence": True,
                "bm25_executed": True,
                "stale_hits_skipped": 0,
                "invalid_hits_skipped": 0,
                "provider_remote_calls": 0,
                "provider_outbound_calls": 0,
                "passed": True,
            }
            if any(row.get(key) != value for key, value in exact.items()):
                errors.append("B3 runtime private case failed")
    if receipt.get("private_input_read") is not False:
        errors.append("B3 runtime qualification read private input")
    if not str(receipt.get("public_qualification_digest", "")).startswith("b3qual_"):
        errors.append("B3 runtime public digest malformed")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(receipt.get("public_report_file_sha256", ""))
    ):
        errors.append("B3 runtime public file digest malformed")
    if receipt.get("private_receipt_digest") != private_receipt_digest(receipt):
        errors.append("B3 runtime private receipt digest mismatch")
    return sorted(set(errors))


def qualify_runtime(
    *,
    cli_path: Path,
    scratch_root: Path,
    source_checkpoint: str,
    source_ci_run_id: int,
    source_ci_conclusion: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(source_ci_run_id, int) or source_ci_run_id <= 0:
        raise B3RuntimeQualificationError("source CI run id must be positive")
    if source_ci_conclusion != "success":
        raise B3RuntimeQualificationError("source CI must conclude success")
    if _git_head() != source_checkpoint:
        raise B3RuntimeQualificationError("checkout is not the qualified source checkpoint")
    _validate_source_checkpoint(source_checkpoint)
    cli_path = Path(cli_path).resolve(strict=True)
    if cli_path.is_symlink() or not cli_path.is_file():
        raise B3RuntimeQualificationError("OpenLocus CLI path is missing or unsafe")
    scratch_root = Path(scratch_root)
    if os.path.lexists(scratch_root) and (
        scratch_root.is_symlink()
        or not scratch_root.is_dir()
        or any(scratch_root.iterdir())
    ):
        raise B3RuntimeQualificationError("runtime scratch must be absent or empty")
    scratch_root.mkdir(parents=True, exist_ok=True)
    profile_before = b23q.collect_runner_profile(
        repo_root=REPO, scratch_root=scratch_root, cli_path=cli_path
    )
    failures = b23q.validate_runner_profile(profile_before)
    if failures:
        raise B3RuntimeQualificationError("current runner class admission failed")
    fixture_root = scratch_root / "b3_public_synthetic_runtime_fixture"
    try:
        case_rows = b25rq._run_synthetic_cases(cli_path, fixture_root)
    finally:
        if fixture_root.exists():
            resolved = fixture_root.resolve(strict=True)
            resolved.relative_to(scratch_root.resolve(strict=True))
            shutil.rmtree(resolved)
    profile_after = b23q.collect_runner_profile(
        repo_root=REPO, scratch_root=scratch_root, cli_path=cli_path
    )
    if b23q.validate_runner_profile(profile_after):
        raise B3RuntimeQualificationError("post-matrix runner class admission failed")
    if b23q.stable_runner_profile_changes(profile_before, profile_after):
        raise B3RuntimeQualificationError("stable runner profile changed during qualification")
    public = _build_public_report(
        source_checkpoint=source_checkpoint,
        source_ci_run_id=source_ci_run_id,
        source_ci_conclusion=source_ci_conclusion,
        case_rows=case_rows,
    )
    public_errors = validate_public_report(public)
    if public_errors:
        raise B3RuntimeQualificationError("generated public runtime report is invalid")
    public_raw = (json.dumps(public, indent=2, sort_keys=True) + "\n").encode("utf-8")
    private = _build_private_receipt(
        public_report=public,
        public_report_file_sha256=hashlib.sha256(public_raw).hexdigest(),
        cli_path=cli_path,
        profile_before=profile_before,
        profile_after=profile_after,
        case_rows=case_rows,
    )
    private_errors = validate_private_receipt(private)
    if private_errors:
        raise B3RuntimeQualificationError("generated private runtime receipt is invalid")
    return public, private


def _write_atomic(path: Path, raw: bytes, *, mode: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B3RuntimeQualificationError("runtime qualification output already exists")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        if os.path.lexists(target):
            raise B3RuntimeQualificationError("runtime output appeared concurrently")
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


def write_qualification_pair(
    *,
    public_path: Path,
    private_path: Path,
    public_report: Mapping[str, Any],
    private_receipt: Mapping[str, Any],
) -> tuple[Path, Path]:
    public_resolved = Path(public_path).resolve(strict=False)
    private_resolved = Path(private_path).resolve(strict=False)
    try:
        public_resolved.relative_to(REPO.resolve(strict=True))
    except ValueError as exc:
        raise B3RuntimeQualificationError("public runtime report must be inside checkout") from exc
    try:
        private_resolved.relative_to(REPO.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise B3RuntimeQualificationError("private runtime receipt must stay outside checkout")
    if validate_public_report(dict(public_report)) or validate_private_receipt(
        dict(private_receipt)
    ):
        raise B3RuntimeQualificationError("refusing to write invalid runtime pair")
    public_raw = (json.dumps(public_report, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if private_receipt.get("public_report_file_sha256") != hashlib.sha256(
        public_raw
    ).hexdigest():
        raise B3RuntimeQualificationError("runtime private/public bytes do not bind")
    private_raw = (json.dumps(private_receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    private_target = _write_atomic(private_path, private_raw, mode=0o600)
    try:
        public_target = _write_atomic(public_path, public_raw, mode=0o644)
    except Exception:
        if private_target.is_file() and not private_target.is_symlink():
            private_target.unlink()
        raise
    return public_target, private_target


def validate_runtime_binding(
    *,
    public_report_path: Path,
    private_receipt_path: Path,
    cli_path: Path,
    scratch_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    for path, label in (
        (public_report_path, "public runtime report"),
        (private_receipt_path, "private runtime receipt"),
    ):
        candidate = Path(path)
        if candidate.is_symlink() or not candidate.is_file():
            raise B3RuntimeQualificationError(f"B3 {label} is missing or unsafe")
    public = b2c.load_json(public_report_path)
    private = b2c.load_json(private_receipt_path)
    if validate_public_report(public) or validate_private_receipt(private):
        raise B3RuntimeQualificationError("B3 runtime binding is invalid")
    if private["public_qualification_digest"] != public["qualification_digest"]:
        raise B3RuntimeQualificationError("B3 runtime public digest drifted")
    if private["public_report_file_sha256"] != _file_sha256(public_report_path):
        raise B3RuntimeQualificationError("B3 runtime public bytes drifted")
    if b3src.control_source_bundle_digest() != private["control_source_bundle_digest"]:
        raise B3RuntimeQualificationError("B3 control source drifted after qualification")
    cli_path = Path(cli_path).resolve(strict=True)
    if cli_path.is_symlink() or not cli_path.is_file():
        raise B3RuntimeQualificationError("qualified OpenLocus CLI is missing or unsafe")
    if cli_path.stat().st_size != private["cli_bytes"] or _file_sha256(cli_path) != private[
        "cli_sha256"
    ]:
        raise B3RuntimeQualificationError("qualified OpenLocus CLI bytes drifted")
    scratch_root = Path(scratch_root)
    if os.path.lexists(scratch_root) and (
        scratch_root.is_symlink()
        or not scratch_root.is_dir()
        or any(scratch_root.iterdir())
    ):
        raise B3RuntimeQualificationError("runtime admission scratch must be absent or empty")
    scratch_root.mkdir(parents=True, exist_ok=True)
    current = b23q.collect_runner_profile(
        repo_root=REPO, scratch_root=scratch_root, cli_path=cli_path
    )
    if b23q.validate_runner_profile(current):
        raise B3RuntimeQualificationError("current runner profile gate failed")
    if b23q.stable_runner_profile_changes(private["profile_after"], current):
        raise B3RuntimeQualificationError("current runner differs from qualified profile")
    return public, private


def _synthetic_case_rows() -> list[dict[str, Any]]:
    return [
        {
            "category": case["category"],
            "query": case["query"],
            "task_family": case["task_family"],
            "expected_path": case["path"],
            "expected_line": case["line"],
            "evidence_count": 1,
            "current_evidence": True,
            "bm25_executed": True,
            "stale_hits_skipped": 0,
            "invalid_hits_skipped": 0,
            "provider_remote_calls": 0,
            "provider_outbound_calls": 0,
            "passed": True,
        }
        for case in b25rq.B25_RUNTIME_CASES
    ]


def run_self_test() -> dict[str, Any]:
    rows = _synthetic_case_rows()
    public = _build_public_report(
        source_checkpoint="a" * 40,
        source_ci_run_id=1,
        source_ci_conclusion="success",
        case_rows=rows,
    )
    profile = b23q._mock_profile()
    with tempfile.TemporaryDirectory(prefix="openlocus-b3-runtime-test-") as temporary:
        cli = Path(temporary) / "openlocus"
        cli.write_bytes(b"synthetic-cli")
        private = _build_private_receipt(
            public_report=public,
            public_report_file_sha256="b" * 64,
            cli_path=cli,
            profile_before=profile,
            profile_after=copy.deepcopy(profile),
            case_rows=rows,
        )
    checks = {
        "public_valid": not validate_public_report(public),
        "private_valid": not validate_private_receipt(private),
        "historical_machine_not_required": public["runner_gate"][
            "historical_machine_identity_required"
        ]
        is False,
        "private_input_not_read": public["synthetic_matrix"]["private_input_read"]
        is False,
        "tournament_not_authorized": public["decision"][
            "tournament_execution_authorized"
        ]
        is False,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    rows = _synthetic_case_rows()
    public = _build_public_report(
        source_checkpoint="a" * 40,
        source_ci_run_id=1,
        source_ci_conclusion="success",
        case_rows=rows,
    )
    drifted = copy.deepcopy(public)
    drifted["synthetic_matrix"]["passed_case_count"] = 3
    profile = b23q._mock_profile()
    with tempfile.TemporaryDirectory(prefix="openlocus-b3-runtime-fault-") as temporary:
        cli = Path(temporary) / "openlocus"
        cli.write_bytes(b"synthetic-cli")
        private = _build_private_receipt(
            public_report=public,
            public_report_file_sha256="b" * 64,
            cli_path=cli,
            profile_before=profile,
            profile_after=copy.deepcopy(profile),
            case_rows=rows,
        )
    private_drift = copy.deepcopy(private)
    private_drift["profile_after"]["effective_cpu_quota_count"] = 9
    checks = {
        "public_case_loss_rejected": bool(validate_public_report(drifted)),
        "private_profile_drift_rejected": bool(validate_private_receipt(private_drift)),
        "failed_case_rejected": bool(
            validate_public_report(
                _build_public_report(
                    source_checkpoint="a" * 40,
                    source_ci_run_id=1,
                    source_ci_conclusion="success",
                    case_rows=[*rows[:-1], {**rows[-1], "passed": False}],
                )
            )
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--fault-test", action="store_true")
    actions.add_argument("--check-public", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        report = run_self_test()
    elif args.fault_test:
        report = run_fault_test()
    else:
        report = {"errors": validate_public_report(b2c.load_json(args.check_public))}
        report["passed"] = not report["errors"]
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B3_RUNTIME_PRIVATE_SCHEMA",
    "B3_RUNTIME_PUBLIC_SCHEMA",
    "B3_RUNTIME_VERSION",
    "B3RuntimeQualificationError",
    "private_receipt_digest",
    "qualification_digest",
    "qualify_runtime",
    "validate_private_receipt",
    "validate_public_report",
    "validate_runtime_binding",
    "write_qualification_pair",
]
