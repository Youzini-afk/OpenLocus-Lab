#!/usr/bin/env python3
"""Aggregate-only publication for B3 runner/scorer engine integration."""

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

import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b21_runner as b21r  # noqa: E402
import product_bakeoff_b3_protocol as b3p  # noqa: E402
import product_bakeoff_b3_repeatability as b3r  # noqa: E402
import product_bakeoff_b3_runner as b3runner  # noqa: E402
import product_bakeoff_b3_scorer as b3scorer  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_engine_integration"
    / "product_bakeoff_b3_engine_integration.json"
)
PARENT_PROTOCOL_PATH = (
    REPO
    / "artifacts"
    / "product_bakeoff_b3_protocol"
    / "product_bakeoff_b3_protocol_report.json"
)

B3_ENGINE_REPORT_SCHEMA = "product_bakeoff_b3_engine_integration.v1"
B3_ENGINE_STATUS = (
    "product_bakeoff_b3_runner_scorer_integration_complete_"
    "no_runtime_no_holdout_no_execution_no_result"
)
B3_ENGINE_PHASE = "product_bakeoff_b3_shared_gate_scorer_engine_integration"
B3_ENGINE_DATE = "2026-07-17"
B3_ENGINE_CLAIM = "engineering_integration_and_synthetic_fault_tests_only"

B3_PARENT_PROTOCOL_CHECKPOINT = "291c5a0041d94224a6dfff10838c6ed50110ddb4"
B3_PARENT_PROTOCOL_CI_RUN_ID = 29565270451
B3_PARENT_PROTOCOL_CANONICAL_SHA256 = (
    "350041bb2eb3bafc891a1d92e2ee3e2689427a3fb4296d5ae8bb9bec81301363"
)
B3_PARENT_PROTOCOL_DIGEST = (
    "b3protocol_d65a62e6755eaac93c1792df906b1d23ade494044d03377c74559c9bddfd2ec9"
)
B3_PARENT_SPEC_DIGEST = "b3spec_df6c9be0648df4bc"

B3_ENGINE_SOURCE_PATHS = (
    "eval/product_bakeoff_contract.py",
    "eval/product_bakeoff_b2_protocol.py",
    "eval/product_bakeoff_b2_runner.py",
    "eval/product_bakeoff_b2_scorer.py",
    "eval/product_bakeoff_b21_protocol.py",
    "eval/product_bakeoff_b21_runner.py",
    "eval/product_bakeoff_b21_scorer.py",
    "eval/product_bakeoff_b24_runner.py",
    "eval/product_bakeoff_b3_protocol.py",
    "eval/product_bakeoff_b3_repeatability.py",
    "eval/product_bakeoff_b3_runner.py",
    "eval/product_bakeoff_b3_scorer.py",
    "eval/product_bakeoff_b3_engine_integration.py",
    ".github/workflows/product-bakeoff-b3-engine.yml",
)

B3_ENGINE_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "private_holdout_manifest_or_freeze_digest_public": False,
    "repository_task_query_or_oracle_identity_public": False,
    "source_location_range_excerpt_or_raw_output_public": False,
    "per_task_per_repository_or_per_cell_empirical_detail_public": False,
    "intermediate_arm_quality_resource_or_ranking_metric_public": False,
    "private_runner_identity_endpoint_or_working_location_public": False,
    "provider_payload_secret_or_credential_public": False,
}

B3_ENGINE_NEXT_ACTION = (
    "Keep the server off while implementing the B3 private freeze/readiness, "
    "launch-admission, first-durable-observation attempt receipt, CLI, and "
    "disconnect-safe launcher. After those local surfaces and public CI pass, "
    "start the server only for exact Linux runtime qualification."
)


class B3EngineIntegrationError(ValueError):
    """Fail-closed error for the public B3 engine-integration aggregate."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B3EngineIntegrationError("public report must be an object")
    return value


def _normalized_source_rows(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = (repo_root or REPO).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in B3_ENGINE_SOURCE_PATHS:
        if rel in seen:
            raise B3EngineIntegrationError("duplicate B3 engine source entry")
        seen.add(rel)
        source = root / rel
        if source.is_symlink() or not source.is_file():
            raise B3EngineIntegrationError(f"missing B3 engine source: {rel}")
        resolved = source.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise B3EngineIntegrationError("B3 engine source escapes repository") from exc
        raw = source.read_bytes().replace(b"\r\n", b"\n")
        rows.append(
            {
                "source": rel,
                "normalized_bytes": len(raw),
                "normalized_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def source_bundle_digest(repo_root: Path | None = None) -> str:
    return _prefixed_digest("b3engsrc_", _normalized_source_rows(repo_root))


def validate_parent_protocol() -> list[str]:
    errors: list[str] = []
    try:
        parent = _load_json(PARENT_PROTOCOL_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"parent B3 protocol unreadable: {type(exc).__name__}"]
    if hashlib.sha256(_canonical(parent)).hexdigest() != B3_PARENT_PROTOCOL_CANONICAL_SHA256:
        errors.append("parent B3 protocol canonical JSON drifted")
    if parent.get("protocol_digest") != B3_PARENT_PROTOCOL_DIGEST:
        errors.append("parent B3 protocol digest drifted")
    if parent.get("spec_digest") != B3_PARENT_SPEC_DIGEST:
        errors.append("parent B3 spec digest drifted")
    if parent.get("status") != b3p.B3_STATUS:
        errors.append("parent B3 protocol status drifted")
    errors.extend(f"parent B3 protocol: {error}" for error in b3p.validate_report(parent))
    return sorted(set(errors))


def _build_report_without_digest() -> dict[str, Any]:
    inherited_runner_self = b21r.run_self_test()
    inherited_runner_fault = b21r.run_fault_test()
    runner_self = b3runner.run_self_test()
    runner_fault = b3runner.run_fault_test()
    scorer_self = b3scorer.run_self_test()
    scorer_fault = b3scorer.run_fault_test()
    if not all(
        report["passed"]
        for report in (
            inherited_runner_self,
            inherited_runner_fault,
            runner_self,
            runner_fault,
            scorer_self,
            scorer_fault,
        )
    ):
        raise B3EngineIntegrationError("B3 engine synthetic validation failed")
    return {
        "schema_version": B3_ENGINE_REPORT_SCHEMA,
        "phase": B3_ENGINE_PHASE,
        "date": B3_ENGINE_DATE,
        "status": B3_ENGINE_STATUS,
        "claim_level": B3_ENGINE_CLAIM,
        "parent_protocol": {
            "checkpoint": B3_PARENT_PROTOCOL_CHECKPOINT,
            "ci_run_id": B3_PARENT_PROTOCOL_CI_RUN_ID,
            "ci_conclusion": "success",
            "canonical_sha256": B3_PARENT_PROTOCOL_CANONICAL_SHA256,
            "protocol_digest": B3_PARENT_PROTOCOL_DIGEST,
            "spec_digest": B3_PARENT_SPEC_DIGEST,
        },
        "historical_boundary": {
            "b25_closeout_remains_failed_closed_no_result": True,
            "b25_matrix_restarted_resumed_scored_or_ranked": False,
            "b25_private_holdout_or_launch_authorization_reused": False,
            "historical_b2_b21_b24_b25_modules_modified": False,
        },
        "runner_integration": {
            "runner_version": b3runner.B3_RUNNER_VERSION,
            "engine_policy_version": b3runner.B3_ENGINE_POLICY_VERSION,
            "historical_b21_execution_loop_reused": True,
            "scoped_williams_schedule_override": True,
            "scoped_shared_repeatability_gate_override": True,
            "historical_function_references_restored_on_success_and_exception": True,
            "b21_source_currentness_scoreability_split_plot_lineage_fairness_provider_gates_retained": True,
            "b24_longrun_timeout_and_adapter_envelope_reused": True,
            "closed_future_freeze_receipt_validator_required": True,
            "private_launch_and_attempt_boundary_owned_by_future_outer_envelope": True,
        },
        "scorer_integration": {
            "scorer_version": b3scorer.B3_SCORER_VERSION,
            "shared_repeatability_policy_digest": b3r.repeatability_policy_digest(),
            "same_canonicalize_for_scoring_entry_point_as_gate_core": True,
            "historical_b21_exact_hash_canonicalizers_called": False,
            "frozen_b2_task_scoring_reused": True,
            "frozen_b21_own_parent_terminal_scoring_reused": True,
            "frozen_arm_aggregation_resource_percentiles_and_tournament_decision_reused": True,
            "public_tournament_result_builder_implemented": False,
        },
        "synthetic_validation": {
            "logical_group_count": 360,
            "observation_count": 1440,
            "diagnostic_hash_drift_groups_accepted_when_score_and_routing_equal": 360,
            "target_cardinality_routing_drift_rejected": True,
            "missing_group_and_repetition_signature_drift_rejected": True,
            "historical_exact_gate_proven_to_fail_the_equivalent_diagnostic_fixture": True,
            "b3_shared_gate_proven_to_pass_the_same_fixture": True,
            "historical_exact_scorer_canonicalizers_poisoned_and_not_called": True,
            "runner_self_test_checks": runner_self["checks_total"],
            "runner_fault_checks": runner_fault["checks_total"],
            "scorer_self_test_checks": scorer_self["checks_total"],
            "scorer_fault_checks": scorer_fault["checks_total"],
            "inherited_b21_runner_self_test_checks": inherited_runner_self[
                "checks_total"
            ],
            "inherited_b21_runner_fault_checks": inherited_runner_fault[
                "checks_total"
            ],
        },
        "implementation_readiness": {
            "b3_runner_engine_integrated": True,
            "b3_scorer_shared_core_integrated": True,
            "private_freeze_and_readiness_implemented": False,
            "attempt_boundary_receipt_implemented": False,
            "disconnect_safe_launcher_implemented": False,
            "public_synthetic_runtime_qualification_complete": False,
            "exact_linux_runtime_qualified": False,
            "private_holdout_authored_or_frozen": False,
            "future_tournament_execution_authorized": False,
            "treatment_output_exists": False,
            "tournament_result_exists": False,
        },
        "publication_limits": copy.deepcopy(B3_ENGINE_PUBLICATION_LIMITS),
        "source_bundle_digest": source_bundle_digest(),
        "next_authorized_action": B3_ENGINE_NEXT_ACTION,
    }


def build_report() -> dict[str, Any]:
    parent_errors = validate_parent_protocol()
    if parent_errors:
        raise B3EngineIntegrationError(
            "parent B3 protocol invalid: " + "; ".join(parent_errors)
        )
    report = _build_report_without_digest()
    report["integration_digest"] = _prefixed_digest("b3engine_", report)
    return report


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B3 engine integration report must be an object"]
    errors = list(b2p.scan_public_report(report))
    try:
        expected = build_report()
    except (B3EngineIntegrationError, OSError, ValueError) as exc:
        errors.append(f"cannot rebuild B3 engine report: {type(exc).__name__}")
        return sorted(set(errors))
    if report != expected:
        errors.append("B3 engine integration report drifted")
    payload = copy.deepcopy(report)
    observed = payload.pop("integration_digest", None)
    if observed != _prefixed_digest("b3engine_", payload):
        errors.append("B3 engine integration digest mismatch")
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    report = build_report()
    checks = [
        not validate_parent_protocol(),
        not validate_report(report),
        report["historical_boundary"]["historical_b2_b21_b24_b25_modules_modified"]
        is False,
        report["runner_integration"]["scoped_williams_schedule_override"],
        report["scorer_integration"][
            "historical_b21_exact_hash_canonicalizers_called"
        ]
        is False,
        report["synthetic_validation"]["logical_group_count"] == 360,
        report["synthetic_validation"]["observation_count"] == 1440,
        report["implementation_readiness"]["future_tournament_execution_authorized"]
        is False,
        report["integration_digest"].startswith("b3engine_"),
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
        lambda value: value["historical_boundary"].__setitem__(
            "b25_matrix_restarted_resumed_scored_or_ranked", True
        ),
        lambda value: value["runner_integration"].__setitem__(
            "scoped_shared_repeatability_gate_override", False
        ),
        lambda value: value["scorer_integration"].__setitem__(
            "historical_b21_exact_hash_canonicalizers_called", True
        ),
        lambda value: value["synthetic_validation"].__setitem__(
            "target_cardinality_routing_drift_rejected", False
        ),
        lambda value: value["implementation_readiness"].__setitem__(
            "future_tournament_execution_authorized", True
        ),
        lambda value: value["publication_limits"].__setitem__(
            "private_holdout_manifest_or_freeze_digest_public", True
        ),
        lambda value: value.__setitem__("integration_digest", "b3engine_" + "0" * 64),
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
        raise B3EngineIntegrationError("refusing to write invalid B3 engine report")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B3 engine integration publication")
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
    "B3_ENGINE_REPORT_SCHEMA",
    "B3_ENGINE_STATUS",
    "B3EngineIntegrationError",
    "source_bundle_digest",
    "validate_parent_protocol",
    "build_report",
    "validate_report",
    "run_self_test",
    "run_fault_test",
]
