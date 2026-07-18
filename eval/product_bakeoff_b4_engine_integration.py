#!/usr/bin/env python3
"""Aggregate-only B4 analysis/publication engine integration checkpoint."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402
import product_bakeoff_b4_publication as b4pub  # noqa: E402
import product_bakeoff_b4_runner as b4runner  # noqa: E402
import product_bakeoff_b4_scorer as b4scorer  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b4_engine_integration"
    / "product_bakeoff_b4_engine_integration.json"
)
PARENT_PROTOCOL_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b4_protocol"
    / "product_bakeoff_b4_protocol_report.json"
)

B4_ENGINE_REPORT_SCHEMA = "product_bakeoff_b4_engine_integration.v1"
B4_ENGINE_STATUS = (
    "product_bakeoff_b4_analysis_publication_engine_complete_"
    "no_runtime_no_holdout_no_execution"
)
B4_ENGINE_PHASE = "product_bakeoff_b4_closed_matrix_cluster_analysis_publication"
B4_ENGINE_DATE = "2026-07-18"
B4_ENGINE_CLAIM = "engineering_contract_and_synthetic_fault_tests_only"

B4_PARENT_PROTOCOL_CHECKPOINT = "e5e72cf8dcca0d1a1426fc22ef3133cb0ba0d747"
B4_PARENT_PROTOCOL_CI_RUN_ID = 29639800266
B4_PARENT_PROTOCOL_FILE_SHA256 = (
    "8521232e02ab32fed0d275aa77c6135c892671887171d3f0f138308e8ae00108"
)
B4_PARENT_PROTOCOL_CANONICAL_SHA256 = (
    "4bb3a0d1c673ee684e39e8a3c323cd796d46f27bda5638e209e01b21c6a83f42"
)
B4_PARENT_PROTOCOL_DIGEST = b4scorer.B4_PARENT_PROTOCOL_DIGEST

B4_ENGINE_SOURCE_PATHS = (
    "eval/product_bakeoff_b2_protocol.py",
    "eval/product_bakeoff_b4_protocol.py",
    "eval/product_bakeoff_b4_runner.py",
    "eval/product_bakeoff_b4_scorer.py",
    "eval/product_bakeoff_b4_publication.py",
    "eval/product_bakeoff_b4_engine_integration.py",
    "artifacts/product_bakeoff_b4_protocol/product_bakeoff_b4_protocol_report.json",
    ".github/workflows/product-bakeoff-b4-engine.yml",
)

B4_ENGINE_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "private_holdout_manifest_or_freeze_digest_public": False,
    "repository_task_query_or_oracle_identity_public": False,
    "source_location_range_excerpt_or_raw_output_public": False,
    "per_task_per_repository_or_per_cell_empirical_detail_public": False,
    "intermediate_arm_quality_resource_or_ranking_metric_public": False,
    "private_runner_identity_endpoint_or_working_location_public": False,
    "provider_payload_secret_or_credential_public": False,
}


class B4EngineIntegrationError(ValueError):
    """Fail-closed B4 engine integration error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Mapping[str, Any], key: str) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _normalized_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B4EngineIntegrationError("B4 public parent must be an object")
    return value


def source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative in B4_ENGINE_SOURCE_PATHS:
        if relative in seen:
            raise B4EngineIntegrationError("duplicate B4 engine source entry")
        seen.add(relative)
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise B4EngineIntegrationError(f"missing B4 engine source: {relative}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise B4EngineIntegrationError("B4 engine source escapes repository") from exc
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "source": relative,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def source_bundle_digest(repo_root: Path | None = None) -> str:
    return "b4engsrc_" + hashlib.sha256(_canonical(source_rows(repo_root))).hexdigest()


def validate_parent_protocol() -> list[str]:
    errors: list[str] = []
    try:
        parent = _load_json(PARENT_PROTOCOL_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"B4 parent protocol unreadable: {type(exc).__name__}"]
    if _normalized_file_sha256(PARENT_PROTOCOL_PATH) != B4_PARENT_PROTOCOL_FILE_SHA256:
        errors.append("B4 parent protocol file lock drifted")
    if hashlib.sha256(_canonical(parent)).hexdigest() != B4_PARENT_PROTOCOL_CANONICAL_SHA256:
        errors.append("B4 parent protocol canonical lock drifted")
    if parent.get("protocol_digest") != B4_PARENT_PROTOCOL_DIGEST:
        errors.append("B4 parent protocol digest drifted")
    if parent.get("status") != b4p.B4_STATUS:
        errors.append("B4 parent protocol status drifted")
    if parent.get("implementation_readiness", {}).get("formal_execution_authorized") is not False:
        errors.append("B4 parent protocol execution boundary drifted")
    return sorted(set(errors))


def _module_reports() -> dict[str, dict[str, Any]]:
    return {
        "runner_self": b4runner.run_self_test(),
        "runner_fault": b4runner.run_fault_test(),
        "scorer_self": b4scorer.run_self_test(),
        "scorer_fault": b4scorer.run_fault_test(),
        "publication_self": b4pub.run_self_test(),
        "publication_fault": b4pub.run_fault_test(),
    }


def build_report() -> dict[str, Any]:
    parent_errors = validate_parent_protocol()
    if parent_errors:
        raise B4EngineIntegrationError(
            "invalid B4 parent protocol: " + "; ".join(parent_errors)
        )
    modules = _module_reports()
    if not all(report["passed"] for report in modules.values()):
        raise B4EngineIntegrationError("B4 engine synthetic validation failed")

    success_analysis = b4scorer.score_b4(b4runner.synthetic_run_result())
    success_public = b4pub.build_public_result(success_analysis)
    tie_public = b4pub.build_public_result(
        b4scorer.score_b4(b4runner.synthetic_run_result(tie=True))
    )
    resource_public = b4pub.build_public_result(
        b4scorer.score_b4(
            b4runner.synthetic_run_result(s1_resource_regression=True)
        )
    )
    report: dict[str, Any] = {
        "schema_version": B4_ENGINE_REPORT_SCHEMA,
        "phase": B4_ENGINE_PHASE,
        "date": B4_ENGINE_DATE,
        "status": B4_ENGINE_STATUS,
        "claim_level": B4_ENGINE_CLAIM,
        "parent_protocol": {
            "checkpoint": B4_PARENT_PROTOCOL_CHECKPOINT,
            "ci_run_id": B4_PARENT_PROTOCOL_CI_RUN_ID,
            "ci_conclusion": "success",
            "file_sha256": B4_PARENT_PROTOCOL_FILE_SHA256,
            "canonical_sha256": B4_PARENT_PROTOCOL_CANONICAL_SHA256,
            "protocol_digest": B4_PARENT_PROTOCOL_DIGEST,
        },
        "runner_contract": {
            "runner_version": b4runner.B4_RUNNER_VERSION,
            "identity_free_task_outcome_surface": True,
            "exact_task_outcome_count": b4runner.B4_TASK_OUTCOME_COUNT,
            "exact_logical_group_count": b4p.B4_LOGICAL_GROUP_COUNT,
            "exact_index_build_count": b4p.B4_INDEX_BUILD_COUNT,
            "exact_pre_score_gate_set_required": True,
            "provider_network_call_count_must_be_zero": True,
            "same_task_technical_pseudoreplication_absent": True,
            "raw_repository_execution_adapter_implemented": False,
        },
        "scorer_contract": {
            "scorer_version": b4scorer.B4_SCORER_VERSION,
            "repository_cluster_level_intervals": True,
            "ordinary_95_and_simultaneous_97_5_intervals": True,
            "two_planned_candidate_comparisons_only": True,
            "panel_direction_guard_implemented": True,
            "conservative_zero_event_harm_upper_bound_implemented": True,
            "quality_and_resource_competition_ranks_always_nonempty": True,
            "exact_ties_share_rank": True,
            "pareto_frontier_always_computed": True,
            "deployment_gates_run_after_ranking": True,
        },
        "publication_contract": {
            "success_schema": b4pub.B4_RESULT_SCHEMA,
            "failure_schema": b4pub.B4_FAILURE_SCHEMA,
            "aggregate_success_validator_implemented": True,
            "aggregate_failed_closeout_validator_implemented": True,
            "success_always_contains_effects_intervals_ranks_pareto_and_gates": True,
            "gate_failure_cannot_erase_comparative_result": True,
            "preboundary_failure_cannot_publish_treatment_counts": True,
            "postboundary_failure_cannot_authorize_retry_resume_or_recompute": True,
        },
        "synthetic_validation": {
            "module_reports": modules,
            "success_arm_count": len(success_public["arms"]),
            "success_comparison_count": len(success_public["comparisons"]),
            "success_phase_c_shortlist_count": len(success_public["phase_c_shortlist"]),
            "tie_quality_rank_values": sorted(
                set(tie_public["quality_competition_ranks"].values())
            ),
            "tie_resource_rank_values": sorted(
                set(tie_public["resource_competition_ranks"].values())
            ),
            "tie_pareto_arm_count": len(tie_public["pareto_frontier"]),
            "tie_shortlist_count": len(tie_public["phase_c_shortlist"]),
            "resource_gate_failure_still_has_quality_ranks": bool(
                resource_public["quality_competition_ranks"]
            ),
            "resource_gate_failure_still_has_resource_ranks": bool(
                resource_public["resource_competition_ranks"]
            ),
        },
        "implementation_readiness": {
            "closed_task_outcome_matrix_implemented": True,
            "cluster_analysis_and_ranking_implemented": True,
            "aggregate_success_and_failure_publication_implemented": True,
            "raw_repository_execution_adapter_implemented": False,
            "source_runtime_corpus_readiness_execution_control_implemented": False,
            "exact_linux_runtime_qualified": False,
            "private_holdout_authored_or_frozen": False,
            "formal_execution_authorized": False,
            "treatment_output_exists": False,
            "empirical_b4_result_exists": False,
        },
        "publication_limits": copy.deepcopy(B4_ENGINE_PUBLICATION_LIMITS),
        "source_bundle_digest": source_bundle_digest(),
        "next_authorized_action": (
            "implement_and_fault_test_the_b4_raw_repository_execution_adapter_"
            "and_offline_source_runtime_corpus_readiness_execution_control_"
            "without_creating_a_private_holdout_or_treatment_output"
        ),
        "integration_digest": "",
    }
    report["integration_digest"] = _digest(
        "b4engine_", report, "integration_digest"
    )
    return report


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B4 engine integration report must be an object"]
    errors = list(b2.scan_public_report(report))
    try:
        expected = build_report()
    except (B4EngineIntegrationError, OSError, ValueError, TypeError) as exc:
        errors.append(f"cannot rebuild B4 engine report: {type(exc).__name__}")
        return sorted(set(errors))
    if report != expected:
        errors.append("B4 engine integration report drifted")
    if report.get("integration_digest") != _digest(
        "b4engine_", report, "integration_digest"
    ):
        errors.append("B4 engine integration digest mismatch")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = [
        not validate_parent_protocol(),
        not validate_report(report),
        report["runner_contract"]["raw_repository_execution_adapter_implemented"]
        is False,
        report["scorer_contract"]["exact_ties_share_rank"],
        report["publication_contract"][
            "gate_failure_cannot_erase_comparative_result"
        ],
        report["synthetic_validation"]["tie_quality_rank_values"] == [1],
        report["synthetic_validation"]["tie_resource_rank_values"] == [1],
        report["synthetic_validation"]["tie_pareto_arm_count"] == 3,
        report["implementation_readiness"]["formal_execution_authorized"]
        is False,
        report["integration_digest"].startswith("b4engine_"),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def run_fault_test() -> dict[str, Any]:
    base = build_report()
    checks: list[bool] = []
    mutators = (
        lambda value: value["runner_contract"].__setitem__(
            "raw_repository_execution_adapter_implemented", True
        ),
        lambda value: value["scorer_contract"].__setitem__(
            "exact_ties_share_rank", False
        ),
        lambda value: value["publication_contract"].__setitem__(
            "gate_failure_cannot_erase_comparative_result", False
        ),
        lambda value: value["implementation_readiness"].__setitem__(
            "formal_execution_authorized", True
        ),
        lambda value: value["publication_limits"].__setitem__(
            "repository_task_query_or_oracle_identity_public", True
        ),
        lambda value: value.__setitem__(
            "integration_digest", "b4engine_" + "0" * 64
        ),
    )
    for mutator in mutators:
        value = copy.deepcopy(base)
        mutator(value)
        checks.append(bool(validate_report(value)))
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def write_report(path: Path = REPORT_PATH) -> Path:
    report = build_report()
    errors = validate_report(report)
    if errors:
        raise B4EngineIntegrationError("refusing to write invalid B4 engine report")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B4 engine integration checkpoint")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--write-report", action="store_true")
    mode.add_argument("--validate-report", type=Path)
    mode.add_argument("--check-drift", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    if args.fault_test:
        print(json.dumps(run_fault_test(), sort_keys=True))
        return 0
    if args.write_report:
        print(write_report(args.output))
        return 0
    path = args.validate_report or args.check_drift
    report = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_report(report)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(("Drift check" if args.check_drift else "Validation") + f" passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B4_ENGINE_REPORT_SCHEMA",
    "B4_ENGINE_STATUS",
    "B4EngineIntegrationError",
    "source_bundle_digest",
    "validate_parent_protocol",
    "build_report",
    "validate_report",
    "run_self_test",
    "run_fault_test",
]
