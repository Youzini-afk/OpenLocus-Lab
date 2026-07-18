#!/usr/bin/env python3
"""Exact Linux runtime qualification for the B4 multi-panel control plane."""

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


HERE = Path(__file__).resolve().parent
if str(HERE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(HERE))

import product_bakeoff_b2_corpus as b2c  # noqa: E402
import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b23_protocol as b23p  # noqa: E402
import product_bakeoff_b23_runner_qualification as b23q  # noqa: E402
import product_bakeoff_b25_runtime_qualification as b25rq  # noqa: E402
import product_bakeoff_b3_runtime_qualification as b3rq  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402
import product_bakeoff_b4_source as b4src  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
GIB = 1024**3
B4_RUNTIME_VERSION = "product_bakeoff_b4_runtime_qualification.v1"
B4_RUNTIME_PUBLIC_SCHEMA = "product_bakeoff_b4_runtime_qualification_public.v1"
B4_RUNTIME_PRIVATE_SCHEMA = "product_bakeoff_b4_runtime_qualification_private.v1"
B4_RUNTIME_STATUS = (
    "product_bakeoff_b4_exact_linux_runtime_qualified_"
    "private_multi_panel_authoring_allowed_after_publication_ci"
)
B4_RUNTIME_CLAIM = "public_synthetic_runtime_integrity_only_no_private_holdout"
B4_RUNTIME_CASE_CATEGORIES = tuple(
    str(row["category"]) for row in b25rq.B25_RUNTIME_CASES
)

# This is a calculated serial working-set gate, not a paid-disk reservation.
# Frozen repositories already occupy the data volume when the gate is checked;
# only one repository lifecycle is expanded at a time and is deleted afterward.
B4_SCRATCH_CAPACITY_POLICY = {
    "policy_version": "product_bakeoff_b4_measured_serial_working_set.v1",
    "largest_visible_snapshot_bytes": max(
        upper - 1 for _, upper in b2p.B2_SIZE_BAND_VISIBLE_BYTES.values()
    ),
    "concurrent_arm_snapshot_count": len(b4p.B4_ARMS),
    "snapshot_index_and_render_multiplier": 4,
    "control_receipt_margin_multiplier": 1,
    "filesystem_margin_fraction_ppm": 250_000,
    "filesystem_margin_minimum_bytes": GIB,
    "groups_are_serial_and_deleted_after_completion": True,
    "authoring_clone_storage_is_measured_separately": True,
    "arbitrary_fixed_disk_floor_forbidden": True,
}
_CORE_WORKING_SET = (
    B4_SCRATCH_CAPACITY_POLICY["largest_visible_snapshot_bytes"]
    * B4_SCRATCH_CAPACITY_POLICY["concurrent_arm_snapshot_count"]
    * B4_SCRATCH_CAPACITY_POLICY["snapshot_index_and_render_multiplier"]
)
_CONTROL_MARGIN = (
    B4_SCRATCH_CAPACITY_POLICY["largest_visible_snapshot_bytes"]
    * B4_SCRATCH_CAPACITY_POLICY["concurrent_arm_snapshot_count"]
    * B4_SCRATCH_CAPACITY_POLICY["control_receipt_margin_multiplier"]
)
_FILESYSTEM_MARGIN = max(
    B4_SCRATCH_CAPACITY_POLICY["filesystem_margin_minimum_bytes"],
    _CORE_WORKING_SET
    * B4_SCRATCH_CAPACITY_POLICY["filesystem_margin_fraction_ppm"]
    // 1_000_000,
)
B4_SCRATCH_CAPACITY_POLICY["calculated_peak_working_set_bytes"] = (
    _CORE_WORKING_SET + _CONTROL_MARGIN
)
B4_SCRATCH_CAPACITY_POLICY["calculated_filesystem_margin_bytes"] = _FILESYSTEM_MARGIN
B4_SCRATCH_CAPACITY_POLICY["minimum_free_local_scratch_bytes_at_start"] = (
    _CORE_WORKING_SET + _CONTROL_MARGIN + _FILESYSTEM_MARGIN
)

B4_MEMORY_CAPACITY_POLICY = copy.deepcopy(b3rq.B3_MEMORY_CAPACITY_POLICY)
B4_MEMORY_CAPACITY_POLICY["policy_version"] = (
    "product_bakeoff_b4_reclaimable_memory_headroom.v1"
)
B4_MINIMUM_RUNNER_CLASS = copy.deepcopy(b23p.B23_RUNNER_CLASS)
B4_MINIMUM_RUNNER_CLASS["minimum_free_local_scratch_bytes_at_start"] = (
    B4_SCRATCH_CAPACITY_POLICY["minimum_free_local_scratch_bytes_at_start"]
)
B4_MINIMUM_RUNNER_CLASS["cgroup_available_memory_measurement"] = (
    "raw_limit_headroom_plus_inactive_file_cache_capped_at_limit"
)
B4_RUNTIME_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "exact_synthetic_query_or_source_public": False,
    "exact_cli_or_runtime_fingerprint_public": False,
    "exact_runner_profile_or_location_public": False,
    "private_receipt_digest_public": False,
    "private_repository_task_or_oracle_public": False,
}


class B4RuntimeQualificationError(ValueError):
    """Fail-closed B4 runtime qualification error."""


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
        raise B4RuntimeQualificationError("current git checkpoint is unavailable")
    return value


def collect_runner_profile(
    *, repo_root: Path, scratch_root: Path, cli_path: Path
) -> dict[str, Any]:
    return b3rq.collect_b3_runner_profile(
        repo_root=repo_root, scratch_root=scratch_root, cli_path=cli_path
    )


def validate_runner_profile(profile: Mapping[str, Any]) -> list[str]:
    failures = set(b23q.validate_runner_profile(profile))
    failures.discard("scratch_free_space_below_minimum")
    failures.discard("cgroup_available_memory_below_minimum")
    effective_memory = profile.get("cgroup_effective_available_memory_bytes")
    required_memory = B4_MEMORY_CAPACITY_POLICY[
        "minimum_effective_available_memory_bytes_at_start"
    ]
    if (
        not isinstance(effective_memory, int)
        or isinstance(effective_memory, bool)
        or effective_memory < required_memory
    ):
        failures.add("cgroup_effective_available_memory_below_minimum")
    observed = profile.get("scratch_free_bytes")
    required = B4_SCRATCH_CAPACITY_POLICY[
        "minimum_free_local_scratch_bytes_at_start"
    ]
    if (
        not isinstance(observed, int)
        or isinstance(observed, bool)
        or observed < required
    ):
        failures.add("scratch_free_space_below_b4_calculated_working_set")
    return sorted(failures)


def qualification_digest(report: Mapping[str, Any]) -> str:
    return _digest("b4qual_", report, "qualification_digest")


def private_receipt_digest(receipt: Mapping[str, Any]) -> str:
    return _digest("b4runtime_", receipt, "private_receipt_digest")


def runtime_bundle_digest(receipt: Mapping[str, Any]) -> str:
    payload = {
        "control_source_bundle_digest": receipt["control_source_bundle_digest"],
        "public_qualification_digest": receipt["public_qualification_digest"],
        "cli_bytes": receipt["cli_bytes"],
        "cli_sha256": receipt["cli_sha256"],
        "source_checkpoint": receipt["source_checkpoint"],
        "scratch_capacity_policy": B4_SCRATCH_CAPACITY_POLICY,
        "memory_capacity_policy": B4_MEMORY_CAPACITY_POLICY,
    }
    return "b4run_" + hashlib.sha256(_canonical(payload)).hexdigest()


def _build_public_report(
    *,
    source_checkpoint: str,
    source_ci_run_id: int,
    source_ci_conclusion: str,
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    passed = len(case_rows) == len(B4_RUNTIME_CASE_CATEGORIES) and all(
        row.get("passed") is True for row in case_rows
    )
    report: dict[str, Any] = {
        "schema_version": B4_RUNTIME_PUBLIC_SCHEMA,
        "qualification_version": B4_RUNTIME_VERSION,
        "phase": "product_bakeoff_b4_exact_linux_runtime_qualification",
        "status": B4_RUNTIME_STATUS,
        "claim_level": B4_RUNTIME_CLAIM,
        "date": "2026-07-18",
        "source_gate": {
            "checkpoint": source_checkpoint,
            "ci_run_id": source_ci_run_id,
            "ci_conclusion": source_ci_conclusion,
            "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        },
        "runner_gate": {
            "minimum_runner_class": copy.deepcopy(B4_MINIMUM_RUNNER_CLASS),
            "scratch_capacity_policy": copy.deepcopy(B4_SCRATCH_CAPACITY_POLICY),
            "memory_capacity_policy": copy.deepcopy(B4_MEMORY_CAPACITY_POLICY),
            "current_runner_class_admitted": True,
            "stable_profile_unchanged_during_qualification": True,
            "exact_current_profile_frozen_privately": True,
            "historical_machine_identity_required": False,
            "exact_runner_profile_public": False,
        },
        "synthetic_matrix": {
            "case_count": len(case_rows),
            "case_categories": list(B4_RUNTIME_CASE_CATEGORIES),
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
            "private_multi_panel_authoring_allowed_after_green_publication_ci": passed,
            "formal_execution_authorized": False,
            "private_holdout_read": False,
            "treatment_output_exists": False,
            "empirical_result_exists": False,
        },
        "publication_limits": copy.deepcopy(B4_RUNTIME_PUBLICATION_LIMITS),
        "next_authorized_action": (
            "Commit this aggregate-only qualification and obtain green public CI; "
            "then author and freeze the twelve mutually disjoint private B4 panels."
        ),
        "qualification_digest": "",
    }
    report["qualification_digest"] = qualification_digest(report)
    return report


def validate_public_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B4 runtime public report must be an object"]
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
    errors: list[str] = []
    if set(report) != expected_keys:
        return ["B4 runtime public report shape drifted"]
    if report["schema_version"] != B4_RUNTIME_PUBLIC_SCHEMA:
        errors.append("B4 runtime public schema drifted")
    if report["qualification_version"] != B4_RUNTIME_VERSION:
        errors.append("B4 runtime qualification version drifted")
    if report["status"] != B4_RUNTIME_STATUS or report["claim_level"] != B4_RUNTIME_CLAIM:
        errors.append("B4 runtime public status or claim drifted")
    source = report["source_gate"]
    if not isinstance(source, dict) or set(source) != {
        "checkpoint",
        "ci_run_id",
        "ci_conclusion",
        "control_source_bundle_digest",
    }:
        errors.append("B4 runtime source gate shape drifted")
    else:
        if not re.fullmatch(r"[0-9a-f]{40}", str(source["checkpoint"])):
            errors.append("B4 runtime source checkpoint malformed")
        if type(source["ci_run_id"]) is not int or source["ci_run_id"] <= 0:
            errors.append("B4 runtime source CI id invalid")
        if source["ci_conclusion"] != "success":
            errors.append("B4 runtime source CI is not green")
        if source["control_source_bundle_digest"] != b4src.control_source_bundle_digest():
            errors.append("B4 runtime control source digest drifted")
    runner = report["runner_gate"]
    if not isinstance(runner, dict) or runner.get("minimum_runner_class") != B4_MINIMUM_RUNNER_CLASS:
        errors.append("B4 runtime minimum runner class drifted")
    elif runner.get("scratch_capacity_policy") != B4_SCRATCH_CAPACITY_POLICY:
        errors.append("B4 runtime scratch policy drifted")
    elif runner.get("memory_capacity_policy") != B4_MEMORY_CAPACITY_POLICY:
        errors.append("B4 runtime memory policy drifted")
    else:
        for key in (
            "current_runner_class_admitted",
            "stable_profile_unchanged_during_qualification",
            "exact_current_profile_frozen_privately",
        ):
            if runner.get(key) is not True:
                errors.append("B4 runtime runner admission drifted")
        if runner.get("historical_machine_identity_required") is not False:
            errors.append("B4 runtime inherited a historical machine identity")
        if runner.get("exact_runner_profile_public") is not False:
            errors.append("B4 runtime published an exact runner profile")
    matrix = report["synthetic_matrix"]
    if not isinstance(matrix, dict) or matrix.get("case_categories") != list(
        B4_RUNTIME_CASE_CATEGORIES
    ):
        errors.append("B4 runtime synthetic matrix drifted")
    else:
        if matrix.get("case_count") != len(B4_RUNTIME_CASE_CATEGORIES):
            errors.append("B4 runtime synthetic case count drifted")
        if matrix.get("passed_case_count") != matrix.get("case_count"):
            errors.append("B4 runtime synthetic matrix did not pass")
        for key in (
            "actual_production_cli_used",
            "actual_production_bakeoff_query_parser_used",
            "all_cases_returned_current_evidence",
            "all_bm25_receipts_executed",
            "all_stale_hits_skipped_zero",
            "all_invalid_hits_skipped_zero",
        ):
            if matrix.get(key) is not True:
                errors.append("B4 runtime synthetic integrity drifted")
        if matrix.get("private_input_read") is not False:
            errors.append("B4 runtime synthetic matrix read private input")
        if matrix.get("provider_network_call_count") != 0:
            errors.append("B4 runtime synthetic matrix used provider network")
    decision = report["decision"]
    if not isinstance(decision, dict) or decision != {
        "runtime_qualified": True,
        "private_multi_panel_authoring_allowed_after_green_publication_ci": True,
        "formal_execution_authorized": False,
        "private_holdout_read": False,
        "treatment_output_exists": False,
        "empirical_result_exists": False,
    }:
        errors.append("B4 runtime decision drifted")
    if report["publication_limits"] != B4_RUNTIME_PUBLICATION_LIMITS:
        errors.append("B4 runtime publication limits drifted")
    if report["qualification_digest"] != qualification_digest(report):
        errors.append("B4 runtime qualification digest mismatch")
    errors.extend(b2p.scan_public_report(report))
    raw = json.dumps(report, sort_keys=True).casefold()
    for token in (
        "runtime_bundle_digest",
        "cli_sha256",
        "scratch_mount_source",
        "openlocus_version",
    ):
        if token in raw:
            errors.append("B4 runtime public report contains a private runtime token")
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
    cli = Path(cli_path).resolve(strict=True)
    receipt: dict[str, Any] = {
        "schema_version": B4_RUNTIME_PRIVATE_SCHEMA,
        "qualification_version": B4_RUNTIME_VERSION,
        "control_source_bundle_digest": b4src.control_source_bundle_digest(),
        "source_checkpoint": public_report["source_gate"]["checkpoint"],
        "public_qualification_digest": public_report["qualification_digest"],
        "public_report_file_sha256": public_report_file_sha256,
        "cli_bytes": cli.stat().st_size,
        "cli_sha256": _file_sha256(cli),
        "profile_before": dict(profile_before),
        "profile_after": dict(profile_after),
        "synthetic_case_rows": [dict(row) for row in case_rows],
        "runtime_bundle_digest": "",
        "private_receipt_digest": "",
    }
    receipt["runtime_bundle_digest"] = runtime_bundle_digest(receipt)
    receipt["private_receipt_digest"] = private_receipt_digest(receipt)
    return receipt


def validate_private_receipt(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict):
        return ["B4 runtime private receipt must be an object"]
    expected = {
        "schema_version",
        "qualification_version",
        "control_source_bundle_digest",
        "source_checkpoint",
        "public_qualification_digest",
        "public_report_file_sha256",
        "cli_bytes",
        "cli_sha256",
        "profile_before",
        "profile_after",
        "synthetic_case_rows",
        "runtime_bundle_digest",
        "private_receipt_digest",
    }
    errors: list[str] = []
    if set(receipt) != expected:
        return ["B4 runtime private receipt shape drifted"]
    if receipt["schema_version"] != B4_RUNTIME_PRIVATE_SCHEMA:
        errors.append("B4 runtime private schema drifted")
    if receipt["qualification_version"] != B4_RUNTIME_VERSION:
        errors.append("B4 runtime private version drifted")
    if receipt["control_source_bundle_digest"] != b4src.control_source_bundle_digest():
        errors.append("B4 runtime private source digest drifted")
    if not re.fullmatch(r"[0-9a-f]{40}", str(receipt["source_checkpoint"])):
        errors.append("B4 runtime private source checkpoint malformed")
    if not str(receipt["public_qualification_digest"]).startswith("b4qual_"):
        errors.append("B4 runtime private public digest malformed")
    for key in ("public_report_file_sha256", "cli_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(receipt[key])):
            errors.append("B4 runtime private SHA-256 malformed")
    if type(receipt["cli_bytes"]) is not int or receipt["cli_bytes"] <= 0:
        errors.append("B4 runtime private CLI size invalid")
    before = receipt["profile_before"]
    after = receipt["profile_after"]
    if not isinstance(before, dict) or validate_runner_profile(before):
        errors.append("B4 runtime private initial profile invalid")
    if not isinstance(after, dict) or validate_runner_profile(after):
        errors.append("B4 runtime private final profile invalid")
    if isinstance(before, dict) and isinstance(after, dict):
        if b23q.stable_runner_profile_changes(before, after):
            errors.append("B4 runtime private stable profile drifted")
    cases = receipt["synthetic_case_rows"]
    if not isinstance(cases, list) or len(cases) != len(B4_RUNTIME_CASE_CATEGORIES):
        errors.append("B4 runtime private synthetic case count drifted")
    elif [row.get("category") for row in cases] != list(B4_RUNTIME_CASE_CATEGORIES):
        errors.append("B4 runtime private synthetic case order drifted")
    elif not all(row.get("passed") is True for row in cases):
        errors.append("B4 runtime private synthetic case failed")
    if receipt["runtime_bundle_digest"] != runtime_bundle_digest(receipt):
        errors.append("B4 runtime bundle digest mismatch")
    if receipt["private_receipt_digest"] != private_receipt_digest(receipt):
        errors.append("B4 runtime private receipt digest mismatch")
    return sorted(set(errors))


def qualify_runtime(
    *,
    cli_path: Path,
    scratch_root: Path,
    source_checkpoint: str,
    source_ci_run_id: int,
    source_ci_conclusion: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(source_ci_run_id) is not int or source_ci_run_id <= 0:
        raise B4RuntimeQualificationError("B4 source CI run id must be positive")
    if source_ci_conclusion != "success":
        raise B4RuntimeQualificationError("B4 source CI must conclude success")
    if _git_head() != source_checkpoint:
        raise B4RuntimeQualificationError("checkout is not the B4 source checkpoint")
    b4src.validate_source_checkpoint(source_checkpoint)
    cli_path = Path(cli_path).resolve(strict=True)
    if cli_path.is_symlink() or not cli_path.is_file():
        raise B4RuntimeQualificationError("OpenLocus CLI path is missing or unsafe")
    scratch_root = Path(scratch_root)
    if os.path.lexists(scratch_root) and (
        scratch_root.is_symlink()
        or not scratch_root.is_dir()
        or any(scratch_root.iterdir())
    ):
        raise B4RuntimeQualificationError("B4 runtime scratch must be absent or empty")
    scratch_root.mkdir(parents=True, exist_ok=True)
    profile_before = collect_runner_profile(
        repo_root=REPO, scratch_root=scratch_root, cli_path=cli_path
    )
    if validate_runner_profile(profile_before):
        raise B4RuntimeQualificationError("current B4 runner class admission failed")
    fixture_root = scratch_root / "b4_public_synthetic_runtime_fixture"
    try:
        case_rows = b25rq._run_synthetic_cases(cli_path, fixture_root)
    finally:
        if fixture_root.exists():
            resolved = fixture_root.resolve(strict=True)
            resolved.relative_to(scratch_root.resolve(strict=True))
            shutil.rmtree(resolved)
    profile_after = collect_runner_profile(
        repo_root=REPO, scratch_root=scratch_root, cli_path=cli_path
    )
    if validate_runner_profile(profile_after):
        raise B4RuntimeQualificationError("post-matrix B4 runner admission failed")
    if b23q.stable_runner_profile_changes(profile_before, profile_after):
        raise B4RuntimeQualificationError("stable B4 runner profile changed")
    public = _build_public_report(
        source_checkpoint=source_checkpoint,
        source_ci_run_id=source_ci_run_id,
        source_ci_conclusion=source_ci_conclusion,
        case_rows=case_rows,
    )
    if validate_public_report(public):
        raise B4RuntimeQualificationError("generated B4 runtime public report is invalid")
    public_raw = (json.dumps(public, indent=2, sort_keys=True) + "\n").encode("utf-8")
    private = _build_private_receipt(
        public_report=public,
        public_report_file_sha256=hashlib.sha256(public_raw).hexdigest(),
        cli_path=cli_path,
        profile_before=profile_before,
        profile_after=profile_after,
        case_rows=case_rows,
    )
    if validate_private_receipt(private):
        raise B4RuntimeQualificationError("generated B4 runtime private receipt is invalid")
    return public, private


def _write_atomic(path: Path, raw: bytes, *, mode: int) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B4RuntimeQualificationError("B4 runtime output already exists")
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
            raise B4RuntimeQualificationError("B4 runtime output appeared concurrently")
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
        raise B4RuntimeQualificationError("public B4 runtime report must be in checkout") from exc
    try:
        private_resolved.relative_to(REPO.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise B4RuntimeQualificationError("private B4 runtime receipt must stay outside checkout")
    if validate_public_report(public_report) or validate_private_receipt(private_receipt):
        raise B4RuntimeQualificationError("refusing to write invalid B4 runtime pair")
    public_raw = (json.dumps(public_report, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if private_receipt["public_report_file_sha256"] != hashlib.sha256(public_raw).hexdigest():
        raise B4RuntimeQualificationError("B4 runtime public/private bytes do not bind")
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
    public_path = Path(public_report_path)
    private_path = Path(private_receipt_path)
    cli = Path(cli_path).resolve(strict=True)
    for path, label in (
        (public_path, "public runtime report"),
        (private_path, "private runtime receipt"),
    ):
        if path.is_symlink() or not path.is_file():
            raise B4RuntimeQualificationError(f"B4 {label} is missing or unsafe")
    public = b2c.load_json(public_path)
    private = b2c.load_json(private_path)
    if validate_public_report(public) or validate_private_receipt(private):
        raise B4RuntimeQualificationError("B4 runtime binding inputs are invalid")
    if private["public_qualification_digest"] != public["qualification_digest"]:
        raise B4RuntimeQualificationError("B4 runtime public/private digest mismatch")
    if private["public_report_file_sha256"] != _file_sha256(public_path):
        raise B4RuntimeQualificationError("B4 runtime public file bytes drifted")
    if private["cli_bytes"] != cli.stat().st_size or private["cli_sha256"] != _file_sha256(cli):
        raise B4RuntimeQualificationError("B4 admitted CLI bytes drifted")
    b4src.validate_source_checkpoint(private["source_checkpoint"])
    scratch = Path(scratch_root)
    if os.path.lexists(scratch) and (
        scratch.is_symlink() or not scratch.is_dir() or any(scratch.iterdir())
    ):
        raise B4RuntimeQualificationError("B4 runtime binding scratch must be absent or empty")
    scratch.mkdir(parents=True, exist_ok=True)
    current = collect_runner_profile(repo_root=REPO, scratch_root=scratch, cli_path=cli)
    if validate_runner_profile(current):
        raise B4RuntimeQualificationError("current B4 runner no longer meets admission")
    if b23q.stable_runner_profile_changes(private["profile_after"], current):
        raise B4RuntimeQualificationError("B4 runner stable profile changed since qualification")
    return public, private


def _synthetic_profile(**overrides: Any) -> dict[str, Any]:
    profile = b3rq._mock_b3_profile()
    profile["scratch_free_bytes"] = (
        B4_SCRATCH_CAPACITY_POLICY["minimum_free_local_scratch_bytes_at_start"]
        + GIB
    )
    profile.update(overrides)
    return profile


def _synthetic_case_rows() -> list[dict[str, Any]]:
    return b3rq._synthetic_case_rows()


def run_self_test() -> dict[str, Any]:
    profile = _synthetic_profile()
    cases = _synthetic_case_rows()
    public = _build_public_report(
        source_checkpoint="a" * 40,
        source_ci_run_id=1,
        source_ci_conclusion="success",
        case_rows=cases,
    )
    public_raw = (json.dumps(public, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tempfile.TemporaryDirectory() as raw:
        cli = Path(raw) / "openlocus"
        cli.write_bytes(b"synthetic-b4-cli")
        private = _build_private_receipt(
            public_report=public,
            public_report_file_sha256=hashlib.sha256(public_raw).hexdigest(),
            cli_path=cli,
            profile_before=profile,
            profile_after=copy.deepcopy(profile),
            case_rows=cases,
        )
    checks = {
        "profile_valid": not validate_runner_profile(profile),
        "public_valid": not validate_public_report(public),
        "private_valid": not validate_private_receipt(private),
        "calculated_disk_gate_small": B4_SCRATCH_CAPACITY_POLICY[
            "minimum_free_local_scratch_bytes_at_start"
        ]
        < 8 * GIB,
        "no_arbitrary_disk_floor": B4_SCRATCH_CAPACITY_POLICY[
            "arbitrary_fixed_disk_floor_forbidden"
        ],
        "three_arm_working_set": B4_SCRATCH_CAPACITY_POLICY[
            "concurrent_arm_snapshot_count"
        ]
        == 3,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
        "minimum_free_scratch_bytes": B4_SCRATCH_CAPACITY_POLICY[
            "minimum_free_local_scratch_bytes_at_start"
        ],
    }


def run_fault_test() -> dict[str, Any]:
    cases = _synthetic_case_rows()
    base = _build_public_report(
        source_checkpoint="a" * 40,
        source_ci_run_id=1,
        source_ci_conclusion="success",
        case_rows=cases,
    )
    checks: dict[str, bool] = {}
    drift = copy.deepcopy(base)
    drift["runner_gate"]["scratch_capacity_policy"][
        "minimum_free_local_scratch_bytes_at_start"
    ] += 1
    checks["scratch_policy_drift_rejected"] = bool(validate_public_report(drift))
    leaked = copy.deepcopy(base)
    leaked["next_authorized_action"] += " cli_sha256"
    checks["private_token_rejected"] = bool(validate_public_report(leaked))
    low_disk = _synthetic_profile(
        scratch_free_bytes=B4_SCRATCH_CAPACITY_POLICY[
            "minimum_free_local_scratch_bytes_at_start"
        ]
        - 1
    )
    checks["calculated_low_disk_rejected"] = (
        "scratch_free_space_below_b4_calculated_working_set"
        in validate_runner_profile(low_disk)
    )
    failed_case = copy.deepcopy(cases)
    failed_case[0]["passed"] = False
    failed_public = _build_public_report(
        source_checkpoint="a" * 40,
        source_ci_run_id=1,
        source_ci_conclusion="success",
        case_rows=failed_case,
    )
    checks["failed_synthetic_matrix_rejected"] = bool(
        validate_public_report(failed_public)
    )
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--fault-test", action="store_true")
    group.add_argument("--check-public", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        report = run_self_test()
    elif args.fault_test:
        report = run_fault_test()
    else:
        errors = validate_public_report(b2c.load_json(args.check_public))
        report = {"passed": not errors, "errors": errors}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B4_RUNTIME_VERSION",
    "B4_RUNTIME_PUBLIC_SCHEMA",
    "B4_RUNTIME_PRIVATE_SCHEMA",
    "B4_SCRATCH_CAPACITY_POLICY",
    "B4_MEMORY_CAPACITY_POLICY",
    "B4_MINIMUM_RUNNER_CLASS",
    "B4RuntimeQualificationError",
    "collect_runner_profile",
    "validate_runner_profile",
    "qualification_digest",
    "private_receipt_digest",
    "runtime_bundle_digest",
    "validate_public_report",
    "validate_private_receipt",
    "qualify_runtime",
    "write_qualification_pair",
    "validate_runtime_binding",
    "run_self_test",
    "run_fault_test",
]
