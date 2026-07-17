#!/usr/bin/env python3
"""Aggregate-only B3 readiness publication after private freeze."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
import product_bakeoff_b3_corpus as b3c
import product_bakeoff_b3_protocol as b3p
import product_bakeoff_b3_repeatability as b3repeat
import product_bakeoff_b3_runtime_qualification as b3rq
import product_bakeoff_b3_source as b3src


REPO = Path(__file__).resolve().parents[1]
B3_READINESS_SCHEMA = "product_bakeoff_b3_holdout_readiness.v1"
B3_READINESS_STATUS = (
    "product_bakeoff_b3_private_holdout_frozen_runtime_qualified_"
    "zero_treatment_output_launch_not_yet_authorized"
)
B3_READINESS_CLAIM = "private_holdout_readiness_only_no_tournament_result"
B3_READINESS_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "repository_candidate_task_query_oracle_identity_public": False,
    "private_holdout_or_freeze_digest_public": False,
    "exact_runner_profile_or_location_public": False,
    "treatment_output_or_intermediate_metric_public": False,
    "private_launch_authorization_public": False,
}


class B3ReadinessError(ValueError):
    """Fail-closed B3 readiness error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("readiness_digest", None)
    return "b3ready_" + hashlib.sha256(_canonical(payload)).hexdigest()


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
    runtime_publication_checkpoint: str,
    runtime_publication_ci_run_id: int,
    runtime_publication_ci_conclusion: str,
    runtime_qualification_digest: str,
    runtime_public_file_sha256: str,
    historical_repository_count: int,
    excluded_repository_count: int,
    excluded_synthetic_source_count: int,
    query_gate: Mapping[str, Any],
    observed_margins: Mapping[str, Any],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": B3_READINESS_SCHEMA,
        "phase": "product_bakeoff_b3_fresh_cluster_aware_holdout_freeze",
        "status": B3_READINESS_STATUS,
        "claim_level": B3_READINESS_CLAIM,
        "date": "2026-07-17",
        "protocol_gate": {
            "b3_spec_digest": b3p.spec_digest(),
            "b3_execution_schedule_digest": b3p.execution_schedule_digest(),
            "b3_expected_observation_plan_digest": b3p.expected_observation_plan_digest(),
            "b3_repeatability_policy_digest": b3repeat.repeatability_policy_digest(),
            "b3_control_source_bundle_digest": b3src.control_source_bundle_digest(),
            "first_durable_observation_attempt_boundary": True,
            "launch_release_alone_consumes_attempt": False,
        },
        "historical_closeout_gate": {
            "b25_closeout_remains_failed_closed_no_result": True,
            "b25_private_holdout_output_or_authorization_reused": False,
            "historical_frame_labels": list(b3c.B3_HISTORICAL_FRAME_LABELS),
        },
        "runner_qualification_gate": {
            "runtime_publication_checkpoint": runtime_publication_checkpoint,
            "runtime_publication_ci_run_id": runtime_publication_ci_run_id,
            "runtime_publication_ci_conclusion": runtime_publication_ci_conclusion,
            "runtime_qualification_digest": runtime_qualification_digest,
            "runtime_public_file_sha256": runtime_public_file_sha256,
            "current_exact_profile_frozen_privately": True,
            "same_qualified_profile_required_at_runner_admission": True,
            "exact_runner_profile_public": False,
        },
        "private_holdout": {
            "repository_cluster_count": 12,
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
            "runtime_and_control_source_frozen": True,
            "repository_or_task_identity_public": False,
            "private_digests_public": False,
        },
        "query_compatibility_gate": {
            "task_count": query_gate["task_count"],
            "tokenizable_query_count": query_gate["tokenizable_query_count"],
            "answerable_task_count": query_gate["answerable_task_count"],
            "abstain_task_count": query_gate["abstain_task_count"],
            "positive_span_count": query_gate["positive_span_count"],
            "compatible_positive_span_count": query_gate[
                "compatible_positive_span_count"
            ],
            "all_queries_tokenizable": query_gate["all_queries_tokenizable"],
            "all_positive_spans_compatible": query_gate[
                "all_positive_spans_compatible"
            ],
            "source_only_no_retrieval_or_adapter_execution": True,
            "private_query_or_gate_digest_public": False,
        },
        "experimental_design": {
            "repository_dependence_cluster_count": 12,
            "logical_task_analysis_unit_count": 48,
            "technical_repetition_count": 4,
            "treatment_arm_count": 6,
            "expected_logical_group_count": 360,
            "expected_observation_count": 1440,
            "williams_position_and_first_order_balance_frozen": True,
            "interim_quality_looks": 0,
            "forced_unique_winner": False,
            "exact_ties_share_competition_rank": True,
        },
        "task_margins": copy.deepcopy(dict(observed_margins)),
        "execution_state": {
            "launch_release_exists": False,
            "attempt_boundary_crossed": False,
            "treatment_output_count": 0,
            "logical_record_count": 0,
            "provider_network_call_count": 0,
            "scoring_executed": False,
            "ranking_executed": False,
            "public_tournament_result_exists": False,
        },
        "decision": {
            "runtime_qualified": True,
            "private_holdout_frozen": True,
            "query_compatibility_gate_passed": True,
            "treatment_output_exists": False,
            "future_tournament_execution_authorized": False,
            "launch_authorization_may_be_created_after_readiness_commit_and_green_ci": True,
        },
        "publication_limits": copy.deepcopy(B3_READINESS_PUBLICATION_LIMITS),
        "next_authorized_action": (
            "Commit this aggregate-only readiness report and obtain green public CI; "
            "then create one private launch authorization and start the disconnect-safe "
            "worker. Launch release alone does not consume the attempt."
        ),
        "readiness_digest": "",
    }
    report["readiness_digest"] = _digest(report)
    return report


def build_public_readiness(
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
    treatment_runs_dir: Path,
) -> dict[str, Any]:
    treatment_runs_dir = Path(treatment_runs_dir)
    if os.path.lexists(treatment_runs_dir) and (
        treatment_runs_dir.is_symlink()
        or not treatment_runs_dir.is_dir()
        or any(treatment_runs_dir.iterdir())
    ):
        raise B3ReadinessError("treatment output exists before B3 readiness")
    state = b3c.validate_frozen_state(
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
    authorization = state["paths"]["authorization"]
    if os.path.lexists(authorization):
        raise B3ReadinessError("launch authorization exists before readiness publication")
    lock = b2c.validate_repo_lock(state["repo_lock"], require_sources=True)
    tasks = b2c.validate_task_manifest(
        state["task_manifest"], repo_lock_digest=lock["repo_lock_digest"]
    )
    oracle = importlib.import_module("product_bakeoff_b2_oracle")
    oracle_rows = oracle.validate_oracle_manifest(
        state["oracle_manifest"],
        tasks=tasks,
        repo_lock=lock,
        task_manifest_digest=state["task_manifest"]["task_manifest_digest"],
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
        raise B3ReadinessError("private B3 task margins drifted")
    binding = state["binding"]
    report = _build_report(
        runtime_publication_checkpoint=runtime_publication_checkpoint,
        runtime_publication_ci_run_id=runtime_publication_ci_run_id,
        runtime_publication_ci_conclusion=runtime_publication_ci_conclusion,
        runtime_qualification_digest=state["runtime_public"]["qualification_digest"],
        runtime_public_file_sha256=b2c.file_sha256(runtime_public_path),
        historical_repository_count=binding["historical_repository_count"],
        excluded_repository_count=binding["excluded_repository_count"],
        excluded_synthetic_source_count=binding["excluded_synthetic_source_count"],
        query_gate=state["query_report"],
        observed_margins=margins,
    )
    errors = validate_public_readiness(report)
    if errors:
        raise B3ReadinessError("generated B3 readiness is invalid: " + "; ".join(errors))
    return report


def validate_public_readiness(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 readiness must be an object"]
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "phase",
        "status",
        "claim_level",
        "date",
        "protocol_gate",
        "historical_closeout_gate",
        "runner_qualification_gate",
        "private_holdout",
        "query_compatibility_gate",
        "experimental_design",
        "task_margins",
        "execution_state",
        "decision",
        "publication_limits",
        "next_authorized_action",
        "readiness_digest",
    }
    if set(report) != expected_keys:
        errors.append("B3 readiness top-level shape drifted")
    if report.get("schema_version") != B3_READINESS_SCHEMA:
        errors.append("B3 readiness schema drifted")
    if report.get("status") != B3_READINESS_STATUS:
        errors.append("B3 readiness status drifted")
    if report.get("claim_level") != B3_READINESS_CLAIM:
        errors.append("B3 readiness claim drifted")
    protocol = report.get("protocol_gate") or {}
    expected_protocol = {
        "b3_spec_digest": b3p.spec_digest(),
        "b3_execution_schedule_digest": b3p.execution_schedule_digest(),
        "b3_expected_observation_plan_digest": b3p.expected_observation_plan_digest(),
        "b3_repeatability_policy_digest": b3repeat.repeatability_policy_digest(),
        "b3_control_source_bundle_digest": b3src.control_source_bundle_digest(),
        "first_durable_observation_attempt_boundary": True,
        "launch_release_alone_consumes_attempt": False,
    }
    if protocol != expected_protocol:
        errors.append("B3 readiness protocol gate drifted")
    history = report.get("historical_closeout_gate") or {}
    if history != {
        "b25_closeout_remains_failed_closed_no_result": True,
        "b25_private_holdout_output_or_authorization_reused": False,
        "historical_frame_labels": list(b3c.B3_HISTORICAL_FRAME_LABELS),
    }:
        errors.append("B3 readiness historical closeout drifted")
    runner = report.get("runner_qualification_gate") or {}
    if set(runner) != {
        "runtime_publication_checkpoint",
        "runtime_publication_ci_run_id",
        "runtime_publication_ci_conclusion",
        "runtime_qualification_digest",
        "runtime_public_file_sha256",
        "current_exact_profile_frozen_privately",
        "same_qualified_profile_required_at_runner_admission",
        "exact_runner_profile_public",
    }:
        errors.append("B3 readiness runner gate shape drifted")
    if not re.fullmatch(
        r"[0-9a-f]{40}", str(runner.get("runtime_publication_checkpoint", ""))
    ):
        errors.append("B3 readiness runtime checkpoint malformed")
    if not isinstance(runner.get("runtime_publication_ci_run_id"), int) or runner.get(
        "runtime_publication_ci_run_id", 0
    ) <= 0:
        errors.append("B3 readiness runtime CI run id malformed")
    if runner.get("runtime_publication_ci_conclusion") != "success":
        errors.append("B3 readiness runtime CI did not succeed")
    if not str(runner.get("runtime_qualification_digest", "")).startswith("b3qual_"):
        errors.append("B3 readiness runtime digest malformed")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(runner.get("runtime_public_file_sha256", ""))
    ):
        errors.append("B3 readiness runtime file digest malformed")
    for key, expected in (
        ("current_exact_profile_frozen_privately", True),
        ("same_qualified_profile_required_at_runner_admission", True),
        ("exact_runner_profile_public", False),
    ):
        if runner.get(key) is not expected:
            errors.append(f"B3 readiness runner gate {key} drifted")
    holdout = report.get("private_holdout") or {}
    expected_holdout = {
        "repository_cluster_count": 12,
        "logical_task_count": 48,
        "oracle_record_count": 48,
        "historical_repository_count": 48,
        "selected_candidate_membership_count": 12,
        "historical_repository_slug_overlap_count": 0,
        "historical_repository_identity_overlap_count": 0,
        "exclusion_registry_overlap_count": 0,
        "candidate_failover_complete": True,
        "runtime_and_control_source_frozen": True,
        "repository_or_task_identity_public": False,
        "private_digests_public": False,
    }
    for key, expected in expected_holdout.items():
        if holdout.get(key) != expected:
            errors.append(f"B3 readiness holdout {key} drifted")
    for key in ("excluded_repository_count", "excluded_synthetic_source_count"):
        if not isinstance(holdout.get(key), int) or holdout.get(key, -1) < 0:
            errors.append(f"B3 readiness holdout {key} malformed")
    query = report.get("query_compatibility_gate") or {}
    if query.get("task_count") != 48 or query.get("tokenizable_query_count") != 48:
        errors.append("B3 readiness query task counts drifted")
    if query.get("answerable_task_count") != 42 or query.get("abstain_task_count") != 6:
        errors.append("B3 readiness query oracle counts drifted")
    positives = query.get("positive_span_count")
    if not isinstance(positives, int) or not 48 <= positives <= 60:
        errors.append("B3 readiness positive span count malformed")
    if query.get("compatible_positive_span_count") != positives:
        errors.append("B3 readiness compatible span count drifted")
    for key in ("all_queries_tokenizable", "all_positive_spans_compatible"):
        if query.get(key) is not True:
            errors.append(f"B3 readiness query {key} failed")
    if report.get("task_margins") != _frozen_margins():
        errors.append("B3 readiness task margins drifted")
    if report.get("experimental_design") != {
        "repository_dependence_cluster_count": 12,
        "logical_task_analysis_unit_count": 48,
        "technical_repetition_count": 4,
        "treatment_arm_count": 6,
        "expected_logical_group_count": 360,
        "expected_observation_count": 1440,
        "williams_position_and_first_order_balance_frozen": True,
        "interim_quality_looks": 0,
        "forced_unique_winner": False,
        "exact_ties_share_competition_rank": True,
    }:
        errors.append("B3 readiness experimental design drifted")
    if report.get("execution_state") != {
        "launch_release_exists": False,
        "attempt_boundary_crossed": False,
        "treatment_output_count": 0,
        "logical_record_count": 0,
        "provider_network_call_count": 0,
        "scoring_executed": False,
        "ranking_executed": False,
        "public_tournament_result_exists": False,
    }:
        errors.append("B3 readiness execution state drifted")
    if report.get("decision") != {
        "runtime_qualified": True,
        "private_holdout_frozen": True,
        "query_compatibility_gate_passed": True,
        "treatment_output_exists": False,
        "future_tournament_execution_authorized": False,
        "launch_authorization_may_be_created_after_readiness_commit_and_green_ci": True,
    }:
        errors.append("B3 readiness decision drifted")
    if report.get("publication_limits") != B3_READINESS_PUBLICATION_LIMITS:
        errors.append("B3 readiness publication limits drifted")
    if report.get("readiness_digest") != _digest(report):
        errors.append("B3 readiness digest mismatch")
    errors.extend(b2p.scan_public_report(report))
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "b3_private_freeze_receipt",
        "b3_private_holdout_binding",
        "b3_private_launch_authorization",
        "b3_private_query_compatibility",
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "query_gate_digest",
        "launch_authorization_digest",
        "clone_root",
    ):
        if token in raw:
            errors.append(f"private B3 readiness token is public: {token}")
    return sorted(set(errors))


def write_public(path: Path, report: Mapping[str, Any]) -> Path:
    if validate_public_readiness(dict(report)):
        raise B3ReadinessError("refusing to write invalid B3 readiness")
    try:
        path.resolve(strict=False).relative_to(REPO.resolve(strict=True))
    except ValueError as exc:
        raise B3ReadinessError("B3 readiness must be written inside checkout") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B3ReadinessError("B3 readiness output already exists")
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


def _synthetic_query_gate() -> dict[str, Any]:
    return {
        "task_count": 48,
        "tokenizable_query_count": 48,
        "answerable_task_count": 42,
        "abstain_task_count": 6,
        "positive_span_count": 48,
        "compatible_positive_span_count": 48,
        "all_queries_tokenizable": True,
        "all_positive_spans_compatible": True,
    }


def run_self_test() -> dict[str, Any]:
    report = _build_report(
        runtime_publication_checkpoint="a" * 40,
        runtime_publication_ci_run_id=1,
        runtime_publication_ci_conclusion="success",
        runtime_qualification_digest="b3qual_" + "b" * 64,
        runtime_public_file_sha256="c" * 64,
        historical_repository_count=48,
        excluded_repository_count=2,
        excluded_synthetic_source_count=2,
        query_gate=_synthetic_query_gate(),
        observed_margins=_frozen_margins(),
    )
    checks = {
        "report_valid": not validate_public_readiness(report),
        "zero_treatment_output": report["execution_state"]["treatment_output_count"] == 0,
        "launch_not_authorized": report["decision"]["future_tournament_execution_authorized"]
        is False,
        "launch_release_not_boundary": report["protocol_gate"][
            "launch_release_alone_consumes_attempt"
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
    report = _build_report(
        runtime_publication_checkpoint="a" * 40,
        runtime_publication_ci_run_id=1,
        runtime_publication_ci_conclusion="success",
        runtime_qualification_digest="b3qual_" + "b" * 64,
        runtime_public_file_sha256="c" * 64,
        historical_repository_count=48,
        excluded_repository_count=2,
        excluded_synthetic_source_count=2,
        query_gate=_synthetic_query_gate(),
        observed_margins=_frozen_margins(),
    )
    drifted = copy.deepcopy(report)
    drifted["execution_state"]["treatment_output_count"] = 1
    leaked = copy.deepcopy(report)
    leaked["next_authorized_action"] += " b3_private_holdout_binding.json"
    checks = {
        "treatment_output_rejected": bool(validate_public_readiness(drifted)),
        "private_token_rejected": bool(validate_public_readiness(leaked)),
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
        errors = validate_public_readiness(b2c.load_json(args.check_public))
        report = {"passed": not errors, "errors": errors}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B3ReadinessError",
    "build_public_readiness",
    "validate_public_readiness",
    "write_public",
]
