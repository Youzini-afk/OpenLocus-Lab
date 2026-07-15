#!/usr/bin/env python3
"""Create and validate the aggregate-only B2.4 holdout readiness checkpoint."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_corpus as b2c  # noqa: E402
import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b24_corpus as b24c  # noqa: E402
from product_bakeoff_b24_protocol import (  # noqa: E402
    B24_PARENT_B23_QUALIFICATION_DIGEST,
    B24_PARENT_B23_QUALIFICATION_SHA256,
    b24_execution_schedule_digest,
    b24_holdout_frame_digest,
    b24_source_bundle_digest,
    b24_spec_digest,
)


B24_READINESS_SCHEMA = "product_bakeoff_b24_holdout_readiness.v1"
B24_READINESS_STATUS = (
    "product_bakeoff_b24_private_holdout_frozen_no_treatment_output_no_result"
)
B24_READINESS_CLAIM = "private_holdout_readiness_only_no_tournament_result"
DEFAULT_PUBLIC_PATH = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "product_bakeoff_b24_readiness"
    / "product_bakeoff_b24_holdout_readiness.json"
)


class B24ReadinessError(ValueError):
    """Fail-closed readiness/publication error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _frozen_margins() -> dict[str, Any]:
    return {
        "languages": {language: 16 for language in b2p.B2_LANGUAGES},
        "size_bands": {size: 12 for size in b2p.B2_SIZE_BANDS},
        "roles": {role: 12 for role in b2p.B2_TASK_ROLES},
        "interaction_modes": {"one_shot": 36, "two_step": 12},
        "oracle_kinds": {"abstain": 6, "deterministic": 36, "multi_target": 6},
    }


def _build_report(
    *,
    protocol_checkpoint: str,
    protocol_ci_run_id: int,
    protocol_ci_conclusion: str,
    observed_margins: Mapping[str, Any],
    historical_repository_count: int,
    excluded_repository_count: int,
    excluded_synthetic_source_count: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": B24_READINESS_SCHEMA,
        "phase": "product_bakeoff_b24_fresh_holdout_freeze",
        "status": B24_READINESS_STATUS,
        "claim_level": B24_READINESS_CLAIM,
        "date": "2026-07-15",
        "protocol_gate": {
            "checkpoint": protocol_checkpoint,
            "ci_run_id": protocol_ci_run_id,
            "ci_conclusion": protocol_ci_conclusion,
            "b24_spec_digest": b24_spec_digest(),
            "b24_source_bundle_digest": b24_source_bundle_digest(),
            "b24_holdout_frame_digest": b24_holdout_frame_digest(),
            "b24_execution_schedule_digest": b24_execution_schedule_digest(),
        },
        "runner_qualification_gate": {
            "qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
            "qualification_file_sha256": B24_PARENT_B23_QUALIFICATION_SHA256,
            "runner_qualified": True,
            "same_machine_instance_required_for_future_tournament": True,
        },
        "private_holdout": {
            "repository_count": 12,
            "logical_task_count": 48,
            "oracle_record_count": 48,
            "historical_repository_count": historical_repository_count,
            "excluded_repository_count": excluded_repository_count,
            "excluded_synthetic_source_count": excluded_synthetic_source_count,
            "selected_candidate_membership_count": 12,
            "historical_repository_slug_overlap_count": 0,
            "historical_repository_identity_overlap_count": 0,
            "exclusion_registry_overlap_count": 0,
            "candidate_failover_complete": True,
            "runtime_frozen": True,
            "private_digests_public": False,
            "repository_or_task_identity_public": False,
        },
        "task_margins": copy.deepcopy(dict(observed_margins)),
        "execution_state": {
            "treatment_output_count": 0,
            "logical_record_count": 0,
            "provider_network_call_count": 0,
            "scoring_executed": False,
            "ranking_executed": False,
            "public_tournament_result_exists": False,
        },
        "decision": {
            "private_holdout_frozen": True,
            "treatment_output_exists": False,
            "future_tournament_execution_authorized": False,
            "launch_authorization_may_be_created_after_readiness_commit_and_green_ci": True,
        },
        "publication_limits": {
            "aggregate_only": True,
            "repository_identity_public": False,
            "task_text_query_oracle_public": False,
            "source_location_range_or_excerpt_public": False,
            "candidate_plan_or_failover_public": False,
            "private_manifest_freeze_or_runtime_digest_public": False,
            "exact_runner_profile_or_location_public": False,
        },
        "next_authorized_action": (
            "commit this aggregate-only readiness checkpoint, obtain green public "
            "CI, create one private launch-authorization receipt bound to that "
            "checkpoint and CI run, revalidate the qualified machine profile, and "
            "then start exactly one standalone tournament attempt"
        ),
        "readiness_digest": "",
    }
    report["readiness_digest"] = _digest(
        "b24ready_",
        {key: value for key, value in report.items() if key != "readiness_digest"},
    )
    return report


def build_public_readiness(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    qualification_report_path: Path,
    cli_path: str | Path,
    treatment_runs_dir: Path,
    protocol_checkpoint: str,
    protocol_ci_run_id: int,
    protocol_ci_conclusion: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", protocol_checkpoint):
        raise B24ReadinessError("protocol checkpoint must be a full lowercase commit SHA")
    if not isinstance(protocol_ci_run_id, int) or protocol_ci_run_id <= 0:
        raise B24ReadinessError("protocol CI run id must be positive")
    if protocol_ci_conclusion != "success":
        raise B24ReadinessError("protocol CI must conclude success")
    if treatment_runs_dir.exists() and any(treatment_runs_dir.iterdir()):
        raise B24ReadinessError("treatment output exists before readiness publication")
    private_root = Path(private_root)
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    binding_path = private_root / "b24_private_holdout_binding.json"
    freeze_path = private_root / "b24_private_freeze_receipt.json"
    repo_lock = b2c.load_json(repo_path)
    task_manifest = b2c.load_json(task_path)
    oracle_manifest = b2c.load_json(oracle_path)
    binding = b2c.load_json(binding_path)
    freeze = b2c.load_json(freeze_path)
    candidate_plan = b2c.load_json(candidate_plan_path)
    historical_locks = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in b24c.HISTORICAL_FRAME_LABELS
    }
    registry = b24c.validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    b2c.validate_repo_lock(repo_lock, require_sources=True)
    tasks = b2c.validate_task_manifest(
        task_manifest, repo_lock_digest=repo_lock["repo_lock_digest"]
    )
    oracle = importlib.import_module("product_bakeoff_b2_oracle")
    oracle_rows = oracle.validate_oracle_manifest(
        oracle_manifest,
        tasks=tasks,
        repo_lock=repo_lock,
        task_manifest_digest=task_manifest["task_manifest_digest"],
    )
    b24c.validate_holdout_binding(
        binding,
        new_repo_lock=repo_lock,
        new_task_manifest=task_manifest,
        new_oracle_manifest=oracle_manifest,
        candidate_plan=candidate_plan,
        candidate_plan_path=candidate_plan_path,
        historical_repo_locks=historical_locks,
        historical_repo_lock_paths=historical_repo_lock_paths,
        exclusion_registry=registry,
        exclusion_registry_path=exclusion_registry_path,
        qualification_report_path=qualification_report_path,
    )
    b24c.validate_freeze_receipt(
        freeze,
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
    margins = {
        "languages": dict(sorted(Counter(task.language for task in tasks).items())),
        "size_bands": dict(sorted(Counter(task.size_band for task in tasks).items())),
        "roles": dict(sorted(Counter(task.role for task in tasks).items())),
        "interaction_modes": dict(
            sorted(Counter(task.interaction_mode for task in tasks).items())
        ),
        "oracle_kinds": dict(
            sorted(Counter(row.oracle_kind for row in oracle_rows).items())
        ),
    }
    if margins != _frozen_margins():
        raise B24ReadinessError("private holdout task margins drifted")
    report = _build_report(
        protocol_checkpoint=protocol_checkpoint,
        protocol_ci_run_id=protocol_ci_run_id,
        protocol_ci_conclusion=protocol_ci_conclusion,
        observed_margins=margins,
        historical_repository_count=binding["historical_repository_count"],
        excluded_repository_count=binding["excluded_repository_count"],
        excluded_synthetic_source_count=binding["excluded_synthetic_source_count"],
    )
    errors = validate_public_readiness(report)
    if errors:
        raise B24ReadinessError("generated public readiness is invalid: " + "; ".join(errors))
    return report


def validate_public_readiness(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["public readiness must be an object"]
    errors = list(b2p.scan_public_report(report))
    expected_keys = {
        "schema_version",
        "phase",
        "status",
        "claim_level",
        "date",
        "protocol_gate",
        "runner_qualification_gate",
        "private_holdout",
        "task_margins",
        "execution_state",
        "decision",
        "publication_limits",
        "next_authorized_action",
        "readiness_digest",
    }
    if set(report) != expected_keys:
        errors.append("public readiness top-level shape drift")
    if report.get("schema_version") != B24_READINESS_SCHEMA:
        errors.append("public readiness schema mismatch")
    if report.get("status") != B24_READINESS_STATUS:
        errors.append("public readiness status mismatch")
    protocol = report.get("protocol_gate") or {}
    if not re.fullmatch(r"[0-9a-f]{40}", str(protocol.get("checkpoint", ""))):
        errors.append("protocol checkpoint malformed")
    if not isinstance(protocol.get("ci_run_id"), int) or protocol.get("ci_run_id", 0) <= 0:
        errors.append("protocol CI run id malformed")
    if protocol.get("ci_conclusion") != "success":
        errors.append("protocol CI did not succeed")
    expected_protocol_locks = {
        "b24_spec_digest": b24_spec_digest(),
        "b24_source_bundle_digest": b24_source_bundle_digest(),
        "b24_holdout_frame_digest": b24_holdout_frame_digest(),
        "b24_execution_schedule_digest": b24_execution_schedule_digest(),
    }
    for key, expected in expected_protocol_locks.items():
        if protocol.get(key) != expected:
            errors.append(f"protocol gate {key} drifted")
    qualification = report.get("runner_qualification_gate") or {}
    expected_qualification = {
        "qualification_digest": B24_PARENT_B23_QUALIFICATION_DIGEST,
        "qualification_file_sha256": B24_PARENT_B23_QUALIFICATION_SHA256,
        "runner_qualified": True,
        "same_machine_instance_required_for_future_tournament": True,
    }
    if qualification != expected_qualification:
        errors.append("runner qualification gate drifted")
    holdout = report.get("private_holdout") or {}
    expected_holdout_keys = {
        "repository_count",
        "logical_task_count",
        "oracle_record_count",
        "historical_repository_count",
        "excluded_repository_count",
        "excluded_synthetic_source_count",
        "selected_candidate_membership_count",
        "historical_repository_slug_overlap_count",
        "historical_repository_identity_overlap_count",
        "exclusion_registry_overlap_count",
        "candidate_failover_complete",
        "runtime_frozen",
        "private_digests_public",
        "repository_or_task_identity_public",
    }
    if set(holdout) != expected_holdout_keys:
        errors.append("private holdout readiness shape drift")
    exact_holdout = {
        "repository_count": 12,
        "logical_task_count": 48,
        "oracle_record_count": 48,
        "historical_repository_count": 24,
        "selected_candidate_membership_count": 12,
        "historical_repository_slug_overlap_count": 0,
        "historical_repository_identity_overlap_count": 0,
        "exclusion_registry_overlap_count": 0,
        "candidate_failover_complete": True,
        "runtime_frozen": True,
        "private_digests_public": False,
        "repository_or_task_identity_public": False,
    }
    for key, expected in exact_holdout.items():
        if holdout.get(key) != expected:
            errors.append(f"private holdout {key} drifted")
    for key in ("excluded_repository_count", "excluded_synthetic_source_count"):
        if not isinstance(holdout.get(key), int) or holdout.get(key, 0) <= 0:
            errors.append(f"private holdout {key} malformed")
    if report.get("task_margins") != _frozen_margins():
        errors.append("public readiness task margins drifted")
    execution = report.get("execution_state") or {}
    expected_execution = {
        "treatment_output_count": 0,
        "logical_record_count": 0,
        "provider_network_call_count": 0,
        "scoring_executed": False,
        "ranking_executed": False,
        "public_tournament_result_exists": False,
    }
    if execution != expected_execution:
        errors.append("public readiness execution state drifted")
    decision = report.get("decision") or {}
    expected_decision = {
        "private_holdout_frozen": True,
        "treatment_output_exists": False,
        "future_tournament_execution_authorized": False,
        "launch_authorization_may_be_created_after_readiness_commit_and_green_ci": True,
    }
    if decision != expected_decision:
        errors.append("public readiness decision drifted")
    payload = dict(report)
    observed = payload.pop("readiness_digest", None)
    if observed != _digest("b24ready_", payload):
        errors.append("public readiness digest mismatch")
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "b24_private_freeze",
        "b24_private_launch",
        "b24_private_repo",
        "clone_root",
        "task_slug",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "freeze_receipt_digest",
        "runtime_bundle_digest",
    ):
        if token in raw:
            errors.append(f"private token forbidden in public readiness: {token}")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = _build_report(
        protocol_checkpoint="1" * 40,
        protocol_ci_run_id=1,
        protocol_ci_conclusion="success",
        observed_margins=_frozen_margins(),
        historical_repository_count=24,
        excluded_repository_count=2,
        excluded_synthetic_source_count=1,
    )
    checks = [
        ("report_valid", not validate_public_readiness(report)),
        ("repo_count", report["private_holdout"]["repository_count"] == 12),
        ("task_count", report["private_holdout"]["logical_task_count"] == 48),
        ("historical_count", report["private_holdout"]["historical_repository_count"] == 24),
        ("no_treatment", report["execution_state"]["treatment_output_count"] == 0),
        ("not_execution_authorized", not report["decision"]["future_tournament_execution_authorized"]),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    base = _build_report(
        protocol_checkpoint="1" * 40,
        protocol_ci_run_id=1,
        protocol_ci_conclusion="success",
        observed_margins=_frozen_margins(),
        historical_repository_count=24,
        excluded_repository_count=2,
        excluded_synthetic_source_count=1,
    )
    checks: list[tuple[str, bool]] = []
    mutations = {
        "identity_public": lambda value: value["private_holdout"].__setitem__("repository_or_task_identity_public", True),
        "overlap": lambda value: value["private_holdout"].__setitem__("historical_repository_slug_overlap_count", 1),
        "treatment_output": lambda value: value["execution_state"].__setitem__("treatment_output_count", 1),
        "execution_authorized": lambda value: value["decision"].__setitem__("future_tournament_execution_authorized", True),
        "margin_drift": lambda value: value["task_margins"]["languages"].__setitem__("rust", 15),
        "digest_drift": lambda value: value.__setitem__("readiness_digest", "b24ready_" + "0" * 64),
    }
    for name, mutator in mutations.items():
        value = copy.deepcopy(base)
        mutator(value)
        checks.append((name, bool(validate_public_readiness(value))))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def write_public(path: Path, report: Mapping[str, Any]) -> Path:
    errors = validate_public_readiness(dict(report))
    if errors:
        raise B24ReadinessError("refusing to write invalid readiness: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B24ReadinessError("public readiness output already exists")
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
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
            raise B24ReadinessError("public readiness output appeared concurrently")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.4 aggregate-only holdout readiness")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--validate-public", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    if args.fault_test:
        print(json.dumps(run_fault_test(), sort_keys=True))
        return 0
    report = json.loads(args.validate_public.read_text(encoding="utf-8"))
    errors = validate_public_readiness(report)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Validation passed: {args.validate_public}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B24_READINESS_SCHEMA",
    "B24_READINESS_STATUS",
    "DEFAULT_PUBLIC_PATH",
    "build_public_readiness",
    "validate_public_readiness",
    "write_public",
    "run_self_test",
    "run_fault_test",
]
