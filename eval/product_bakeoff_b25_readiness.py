#!/usr/bin/env python3
"""Aggregate-only B2.5 private holdout readiness publication."""

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
import product_bakeoff_b25_corpus as b25c  # noqa: E402
import product_bakeoff_b25_query_gate as b25q  # noqa: E402
import product_bakeoff_b25_runtime_qualification as b25rq  # noqa: E402
from product_bakeoff_b25_protocol import (  # noqa: E402
    B25_PARENT_B23_QUALIFICATION_DIGEST,
    B25_PARENT_B24_FAILURE_DIGEST,
    B25_PARENT_B24_REPAIR_DIGEST,
    b25_execution_schedule_digest,
    b25_holdout_frame_digest,
    b25_source_bundle_digest,
    b25_spec_digest,
)


B25_READINESS_SCHEMA = "product_bakeoff_b25_holdout_readiness.v1"
B25_READINESS_STATUS = (
    "product_bakeoff_b25_private_holdout_frozen_query_compatible_"
    "no_treatment_output_no_result"
)
B25_READINESS_CLAIM = "private_holdout_readiness_only_no_tournament_result"
B25_READINESS_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "repository_identity_public": False,
    "task_text_query_oracle_public": False,
    "source_location_range_or_excerpt_public": False,
    "candidate_plan_or_failover_public": False,
    "private_manifest_query_freeze_or_runtime_digest_public": False,
    "exact_runner_profile_or_location_public": False,
}
B25_READINESS_NEXT_ACTION = (
    "commit this aggregate-only readiness checkpoint, obtain green public "
    "CI, create one private launch authorization bound to that checkpoint "
    "and CI run, revalidate the qualified machine, and then cross the formal "
    "attempt boundary exactly once"
)
DEFAULT_PUBLIC_PATH = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "product_bakeoff_b25_readiness"
    / "product_bakeoff_b25_holdout_readiness.json"
)


class B25ReadinessError(ValueError):
    """Fail-closed B2.5 readiness/publication error."""


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
    preauthoring_checkpoint: str,
    preauthoring_ci_run_id: int,
    preauthoring_ci_conclusion: str,
    runtime_qualification_digest: str,
    runtime_qualification_file_sha256: str,
    observed_margins: Mapping[str, Any],
    historical_repository_count: int,
    excluded_repository_count: int,
    excluded_synthetic_source_count: int,
    query_gate: Mapping[str, Any],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": B25_READINESS_SCHEMA,
        "phase": "product_bakeoff_b25_fresh_holdout_freeze",
        "status": B25_READINESS_STATUS,
        "claim_level": B25_READINESS_CLAIM,
        "date": "2026-07-16",
        "preauthoring_publication_gate": {
            "checkpoint": preauthoring_checkpoint,
            "ci_run_id": preauthoring_ci_run_id,
            "ci_conclusion": preauthoring_ci_conclusion,
            "b25_spec_digest": b25_spec_digest(),
            "b25_source_bundle_digest": b25_source_bundle_digest(),
            "b25_holdout_frame_digest": b25_holdout_frame_digest(),
            "b25_execution_schedule_digest": b25_execution_schedule_digest(),
        },
        "historical_closeout_gate": {
            "b24_failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
            "b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
            "b24_result_reopened": False,
            "b24_incomplete_output_reused": False,
        },
        "runner_qualification_gate": {
            "parent_b23_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
            "runtime_qualification_digest": runtime_qualification_digest,
            "runtime_qualification_file_sha256": runtime_qualification_file_sha256,
            "repaired_runtime_qualified": True,
            "same_machine_instance_required_for_future_tournament": True,
            "exact_runner_profile_public": False,
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
            "private_query_path_or_gate_digest_public": False,
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
            "repaired_runtime_qualified": True,
            "private_holdout_frozen": True,
            "query_compatibility_gate_passed": True,
            "treatment_output_exists": False,
            "future_tournament_execution_authorized": False,
            "launch_authorization_may_be_created_after_readiness_commit_and_green_ci": True,
        },
        "publication_limits": copy.deepcopy(B25_READINESS_PUBLICATION_LIMITS),
        "next_authorized_action": B25_READINESS_NEXT_ACTION,
        "readiness_digest": "",
    }
    report["readiness_digest"] = _digest(
        "b25ready_",
        {key: value for key, value in report.items() if key != "readiness_digest"},
    )
    return report


def build_public_readiness(
    *,
    private_root: Path,
    candidate_plan_path: Path,
    historical_repo_lock_paths: Mapping[str, Path],
    exclusion_registry_path: Path,
    runtime_qualification_report_path: Path,
    runtime_qualification_private_receipt_path: Path,
    qualification_private_receipt_path: Path,
    runtime_admission_scratch_root: Path,
    cli_path: str | Path,
    treatment_runs_dir: Path,
    preauthoring_checkpoint: str,
    preauthoring_ci_run_id: int,
    preauthoring_ci_conclusion: str,
) -> dict[str, Any]:
    if treatment_runs_dir.exists() and any(treatment_runs_dir.iterdir()):
        raise B25ReadinessError("treatment output exists before readiness publication")
    b25c._validate_private_layout(Path(private_root), Path(runtime_admission_scratch_root))
    b25c.validate_qualification_publication_gate(
        runtime_qualification_report_path=runtime_qualification_report_path,
        runtime_qualification_checkpoint=preauthoring_checkpoint,
        runtime_qualification_ci_run_id=preauthoring_ci_run_id,
        runtime_qualification_ci_conclusion=preauthoring_ci_conclusion,
        require_current_head=True,
    )
    runtime_public, runtime_private = b25rq.validate_runtime_binding(
        public_report_path=runtime_qualification_report_path,
        private_receipt_path=runtime_qualification_private_receipt_path,
        cli_path=Path(cli_path),
        qualification_private_receipt_path=qualification_private_receipt_path,
        scratch_root=runtime_admission_scratch_root,
    )
    private_root = Path(private_root)
    repo_path = private_root / "b2_private_repo_lock.json"
    task_path = private_root / "b2_private_task_manifest.json"
    oracle_path = private_root / "b2_private_oracle_manifest.json"
    query_path = private_root / "b25_private_query_compatibility.json"
    binding_path = private_root / "b25_private_holdout_binding.json"
    freeze_path = private_root / "b25_private_freeze_receipt.json"
    repo_lock = b2c.load_json(repo_path)
    task_manifest = b2c.load_json(task_path)
    oracle_manifest = b2c.load_json(oracle_path)
    query_report = b2c.load_json(query_path)
    binding = b2c.load_json(binding_path)
    freeze = b2c.load_json(freeze_path)
    candidate_plan = b2c.load_json(candidate_plan_path)
    historical_locks = {
        label: b2c.load_json(historical_repo_lock_paths[label])
        for label in b25c.HISTORICAL_FRAME_LABELS
    }
    registry = b25c.validate_exclusion_registry(b2c.load_json(exclusion_registry_path))
    lock = b2c.validate_repo_lock(repo_lock, require_sources=True)
    tasks = b2c.validate_task_manifest(
        task_manifest, repo_lock_digest=lock["repo_lock_digest"]
    )
    oracle = importlib.import_module("product_bakeoff_b2_oracle")
    oracle_rows = oracle.validate_oracle_manifest(
        oracle_manifest,
        tasks=tasks,
        repo_lock=lock,
        task_manifest_digest=task_manifest["task_manifest_digest"],
    )
    recomputed_query = b25q.build_query_compatibility_report(
        repo_lock=repo_lock,
        task_manifest=task_manifest,
        oracle_manifest=oracle_manifest,
    )
    if recomputed_query != query_report:
        raise B25ReadinessError("query compatibility report drifted before readiness")
    b25c.validate_holdout_binding(
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
        runtime_qualification_checkpoint=preauthoring_checkpoint,
        runtime_qualification_ci_run_id=preauthoring_ci_run_id,
        runtime_qualification_ci_conclusion=preauthoring_ci_conclusion,
    )
    freeze_kwargs = {
        "repo_lock_digest": repo_lock["repo_lock_digest"],
        "task_manifest_digest": task_manifest["task_manifest_digest"],
        "oracle_manifest_digest": oracle_manifest["oracle_manifest_digest"],
        "holdout_binding_digest_value": binding["holdout_binding_digest"],
        "query_gate_digest_value": query_report["query_gate_digest"],
        "runtime_qualification_digest": runtime_public["qualification_digest"],
        "runtime_qualification_private_receipt_digest": runtime_private[
            "private_receipt_digest"
        ],
        "repo_lock_path": repo_path,
        "task_manifest_path": task_path,
        "oracle_manifest_path": oracle_path,
        "holdout_binding_path": binding_path,
        "query_report_path": query_path,
        "candidate_plan_path": candidate_plan_path,
        "historical_repo_lock_paths": historical_repo_lock_paths,
        "exclusion_registry_path": exclusion_registry_path,
        "runtime_qualification_report_path": runtime_qualification_report_path,
        "runtime_qualification_private_receipt_path": (
            runtime_qualification_private_receipt_path
        ),
        "cli_path": cli_path,
    }
    b25c.validate_freeze_receipt(freeze, **freeze_kwargs)
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
        raise B25ReadinessError("private holdout task margins drifted")
    report = _build_report(
        preauthoring_checkpoint=preauthoring_checkpoint,
        preauthoring_ci_run_id=preauthoring_ci_run_id,
        preauthoring_ci_conclusion=preauthoring_ci_conclusion,
        runtime_qualification_digest=runtime_public["qualification_digest"],
        runtime_qualification_file_sha256=b2c.file_sha256(
            runtime_qualification_report_path
        ),
        observed_margins=margins,
        historical_repository_count=binding["historical_repository_count"],
        excluded_repository_count=binding["excluded_repository_count"],
        excluded_synthetic_source_count=binding["excluded_synthetic_source_count"],
        query_gate=query_report,
    )
    errors = validate_public_readiness(report)
    if errors:
        raise B25ReadinessError("generated public readiness invalid: " + "; ".join(errors))
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
        "preauthoring_publication_gate",
        "historical_closeout_gate",
        "runner_qualification_gate",
        "private_holdout",
        "query_compatibility_gate",
        "task_margins",
        "execution_state",
        "decision",
        "publication_limits",
        "next_authorized_action",
        "readiness_digest",
    }
    if set(report) != expected_keys:
        errors.append("public readiness top-level shape drift")
    if report.get("schema_version") != B25_READINESS_SCHEMA:
        errors.append("public readiness schema mismatch")
    if report.get("status") != B25_READINESS_STATUS:
        errors.append("public readiness status mismatch")
    if report.get("phase") != "product_bakeoff_b25_fresh_holdout_freeze":
        errors.append("public readiness phase mismatch")
    if report.get("claim_level") != B25_READINESS_CLAIM:
        errors.append("public readiness claim mismatch")
    if report.get("date") != "2026-07-16":
        errors.append("public readiness date mismatch")
    gate = report.get("preauthoring_publication_gate") or {}
    if set(gate) != {
        "checkpoint",
        "ci_run_id",
        "ci_conclusion",
        "b25_spec_digest",
        "b25_source_bundle_digest",
        "b25_holdout_frame_digest",
        "b25_execution_schedule_digest",
    }:
        errors.append("preauthoring publication gate shape drift")
    if not re.fullmatch(r"[0-9a-f]{40}", str(gate.get("checkpoint", ""))):
        errors.append("preauthoring checkpoint malformed")
    if not isinstance(gate.get("ci_run_id"), int) or gate.get("ci_run_id", 0) <= 0:
        errors.append("preauthoring CI run id malformed")
    if gate.get("ci_conclusion") != "success":
        errors.append("preauthoring CI did not succeed")
    expected_locks = {
        "b25_spec_digest": b25_spec_digest(),
        "b25_source_bundle_digest": b25_source_bundle_digest(),
        "b25_holdout_frame_digest": b25_holdout_frame_digest(),
        "b25_execution_schedule_digest": b25_execution_schedule_digest(),
    }
    for key, expected in expected_locks.items():
        if gate.get(key) != expected:
            errors.append(f"preauthoring gate {key} drifted")
    expected_history = {
        "b24_failure_digest": B25_PARENT_B24_FAILURE_DIGEST,
        "b24_repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
        "b24_result_reopened": False,
        "b24_incomplete_output_reused": False,
    }
    if report.get("historical_closeout_gate") != expected_history:
        errors.append("historical closeout gate drifted")
    runner = report.get("runner_qualification_gate") or {}
    if set(runner) != {
        "parent_b23_qualification_digest",
        "runtime_qualification_digest",
        "runtime_qualification_file_sha256",
        "repaired_runtime_qualified",
        "same_machine_instance_required_for_future_tournament",
        "exact_runner_profile_public",
    }:
        errors.append("runner qualification gate shape drift")
    if runner.get("parent_b23_qualification_digest") != B25_PARENT_B23_QUALIFICATION_DIGEST:
        errors.append("runner parent qualification drifted")
    if not isinstance(runner.get("runtime_qualification_digest"), str) or not str(
        runner.get("runtime_qualification_digest")
    ).startswith("b25qual_"):
        errors.append("runtime qualification digest malformed")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(runner.get("runtime_qualification_file_sha256", ""))
    ):
        errors.append("runtime qualification file digest malformed")
    for key, expected in (
        ("repaired_runtime_qualified", True),
        ("same_machine_instance_required_for_future_tournament", True),
        ("exact_runner_profile_public", False),
    ):
        if runner.get(key) is not expected:
            errors.append(f"runner qualification {key} drifted")
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
        "historical_repository_count": 36,
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
    query = report.get("query_compatibility_gate") or {}
    expected_query_keys = {
        "task_count",
        "tokenizable_query_count",
        "answerable_task_count",
        "abstain_task_count",
        "positive_span_count",
        "compatible_positive_span_count",
        "all_queries_tokenizable",
        "all_positive_spans_compatible",
        "source_only_no_retrieval_or_adapter_execution",
        "private_query_path_or_gate_digest_public",
    }
    if set(query) != expected_query_keys:
        errors.append("query compatibility public shape drift")
    exact_query = {
        "task_count": 48,
        "tokenizable_query_count": 48,
        "answerable_task_count": 42,
        "abstain_task_count": 6,
        "all_queries_tokenizable": True,
        "all_positive_spans_compatible": True,
        "source_only_no_retrieval_or_adapter_execution": True,
        "private_query_path_or_gate_digest_public": False,
    }
    for key, expected in exact_query.items():
        if query.get(key) != expected:
            errors.append(f"query compatibility {key} drifted")
    positives = query.get("positive_span_count")
    compatible = query.get("compatible_positive_span_count")
    if not isinstance(positives, int) or not 48 <= positives <= 60:
        errors.append("query compatibility positive span count malformed")
    if compatible != positives:
        errors.append("query compatibility positive spans do not reconcile")
    if report.get("task_margins") != _frozen_margins():
        errors.append("public readiness task margins drifted")
    expected_execution = {
        "treatment_output_count": 0,
        "logical_record_count": 0,
        "provider_network_call_count": 0,
        "scoring_executed": False,
        "ranking_executed": False,
        "public_tournament_result_exists": False,
    }
    if report.get("execution_state") != expected_execution:
        errors.append("public readiness execution state drifted")
    expected_decision = {
        "repaired_runtime_qualified": True,
        "private_holdout_frozen": True,
        "query_compatibility_gate_passed": True,
        "treatment_output_exists": False,
        "future_tournament_execution_authorized": False,
        "launch_authorization_may_be_created_after_readiness_commit_and_green_ci": True,
    }
    if report.get("decision") != expected_decision:
        errors.append("public readiness decision drifted")
    if report.get("publication_limits") != B25_READINESS_PUBLICATION_LIMITS:
        errors.append("public readiness publication limits drifted")
    if report.get("next_authorized_action") != B25_READINESS_NEXT_ACTION:
        errors.append("public readiness next action drifted")
    payload = dict(report)
    observed = payload.pop("readiness_digest", None)
    if observed != _digest("b25ready_", payload):
        errors.append("public readiness digest mismatch")
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "b25_private_freeze",
        "b25_private_launch",
        "b25_private_query",
        "b25_private_repo",
        "clone_root",
        "task_slug",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "freeze_receipt_digest",
        "runtime_bundle_digest",
        "query_gate_digest",
        "b25qpriv_",
    ):
        if token in raw:
            errors.append(f"private token forbidden in public readiness: {token}")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    query = {
        "task_count": 48,
        "tokenizable_query_count": 48,
        "answerable_task_count": 42,
        "abstain_task_count": 6,
        "positive_span_count": 48,
        "compatible_positive_span_count": 48,
        "all_queries_tokenizable": True,
        "all_positive_spans_compatible": True,
    }
    report = _build_report(
        preauthoring_checkpoint="1" * 40,
        preauthoring_ci_run_id=1,
        preauthoring_ci_conclusion="success",
        runtime_qualification_digest="b25qual_" + "2" * 64,
        runtime_qualification_file_sha256="3" * 64,
        observed_margins=_frozen_margins(),
        historical_repository_count=36,
        excluded_repository_count=2,
        excluded_synthetic_source_count=1,
        query_gate=query,
    )
    checks = [
        ("report_valid", not validate_public_readiness(report)),
        ("repo_count", report["private_holdout"]["repository_count"] == 12),
        ("historical_count", report["private_holdout"]["historical_repository_count"] == 36),
        ("query_gate", report["query_compatibility_gate"]["all_queries_tokenizable"]),
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
    query = {
        "task_count": 48,
        "tokenizable_query_count": 48,
        "answerable_task_count": 42,
        "abstain_task_count": 6,
        "positive_span_count": 48,
        "compatible_positive_span_count": 48,
        "all_queries_tokenizable": True,
        "all_positive_spans_compatible": True,
    }
    base = _build_report(
        preauthoring_checkpoint="1" * 40,
        preauthoring_ci_run_id=1,
        preauthoring_ci_conclusion="success",
        runtime_qualification_digest="b25qual_" + "2" * 64,
        runtime_qualification_file_sha256="3" * 64,
        observed_margins=_frozen_margins(),
        historical_repository_count=36,
        excluded_repository_count=2,
        excluded_synthetic_source_count=1,
        query_gate=query,
    )
    checks: list[tuple[str, bool]] = []
    mutations = {
        "historical_count": lambda value: value["private_holdout"].__setitem__("historical_repository_count", 24),
        "query_failure": lambda value: value["query_compatibility_gate"].__setitem__("all_queries_tokenizable", False),
        "treatment_output": lambda value: value["execution_state"].__setitem__("treatment_output_count", 1),
        "execution_authorized": lambda value: value["decision"].__setitem__("future_tournament_execution_authorized", True),
        "private_digest": lambda value: value.__setitem__("leak", "b25qpriv_secret"),
        "digest_drift": lambda value: value.__setitem__("readiness_digest", "b25ready_" + "0" * 64),
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
        raise B25ReadinessError("refusing to write invalid readiness")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B25ReadinessError("public readiness output already exists")
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
            raise B25ReadinessError("public readiness output appeared concurrently")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.5 aggregate-only holdout readiness")
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
    "B25_READINESS_SCHEMA",
    "B25_READINESS_STATUS",
    "DEFAULT_PUBLIC_PATH",
    "build_public_readiness",
    "validate_public_readiness",
    "write_public",
    "run_self_test",
    "run_fault_test",
]
