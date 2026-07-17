#!/usr/bin/env python3
"""Aggregate-only Linux scale closure for the post-B2.5 determinism repair."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_protocol as b2p
import product_bakeoff_determinism_repair as repair


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_REPAIR_PATH = (
    REPO_ROOT
    / "artifacts"
    / "product_bakeoff_determinism_repair"
    / "product_bakeoff_postcloseout_determinism_repair.json"
)

SCALE_SCHEMA = "product_bakeoff_postcloseout_determinism_linux_scale.v1"
SCALE_STATUS = (
    "product_bakeoff_postcloseout_determinism_linux_scale_complete_"
    "no_tournament_authorization"
)
SCALE_PHASE = "product_bakeoff_postcloseout_determinism_linux_scale_closure"
SCALE_DATE = "2026-07-17"
SCALE_CLAIM = "engineering_scale_validation_only_no_tournament_result"

PARENT_REPAIR_DIGEST = (
    "detrepair_b05b51b37631baa5e7d744be511e3368e4e56bab4f37a0a3cfb8748b853cedeb"
)
PARENT_PUBLICATION_CHECKPOINT = "9fb3012b85b786cb63ec83ba4cb81be1ce123760"
PARENT_PUBLICATION_CI_RUN_ID = 29537550039
SCALE_SOURCE_CHECKPOINT = "59275615e15578a56dcc0ee6133629bb55f85019"
SCALE_SOURCE_CI_RUN_ID = 29559398560
INITIAL_SCALE_HARNESS_CHECKPOINT = "3cf0567cc53367ff7bcdbd8be9a94f22b12bd2c4"
INITIAL_SCALE_HARNESS_CI_RUN_ID = 29537958748

PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "candidate_or_repository_identity_public": False,
    "exact_private_failed_gate_or_divergence_public": False,
    "intermediate_arm_quality_resource_or_ranking_metric_public": False,
    "private_manifest_freeze_launch_or_run_digest_public": False,
    "private_run_path_or_runner_identity_public": False,
    "source_location_range_excerpt_or_query_public": False,
}

NEXT_ACTION = (
    "Keep B2.5 closed as failed_closed_no_result. For a separately "
    "preregistered future tournament, freeze the scorer-equivalent "
    "repeatability projection in both the pre-score gate and scorer, qualify "
    "the exact future runtime, and author a fresh holdout without reusing "
    "B2.5 treatment output or launch authorization."
)


class DeterminismLinuxScaleError(ValueError):
    """Fail-closed error for the public Linux scale aggregate."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop("scale_digest", None)
    return "detlinux_" + hashlib.sha256(_canonical(payload)).hexdigest()


def _validate_parent() -> dict[str, Any]:
    parent = b2c.load_json(PARENT_REPAIR_PATH)
    if repair.validate_public_report(parent):
        raise DeterminismLinuxScaleError("parent determinism repair is invalid")
    if (
        parent.get("status") != repair.REPAIR_STATUS
        or parent.get("repair_digest") != PARENT_REPAIR_DIGEST
        or parent.get("parent_closeout", {}).get("b25_result_reopened") is not False
    ):
        raise DeterminismLinuxScaleError("parent determinism repair drifted")
    return parent


def _tier(
    *,
    tier_id: str,
    file_count: int,
    rrf_span_count: int,
    process_iterations: int,
) -> dict[str, Any]:
    invocations_per_process = 4
    return {
        "tier_id": tier_id,
        "file_count": file_count,
        "rrf_span_count": rrf_span_count,
        "process_iterations": process_iterations,
        "test_invocations_per_process": invocations_per_process,
        "test_invocations_total": process_iterations * invocations_per_process,
        "passed": True,
    }


def build_public_report() -> dict[str, Any]:
    _validate_parent()
    tiers = [
        _tier(
            tier_id="default_production_scale",
            file_count=20_000,
            rrf_span_count=4_096,
            process_iterations=3,
        ),
        _tier(
            tier_id="elevated_scale",
            file_count=50_000,
            rrf_span_count=8_192,
            process_iterations=2,
        ),
        _tier(
            tier_id="declared_parameter_ceiling",
            file_count=100_000,
            rrf_span_count=20_000,
            process_iterations=1,
        ),
    ]
    report: dict[str, Any] = {
        "schema_version": SCALE_SCHEMA,
        "phase": SCALE_PHASE,
        "date": SCALE_DATE,
        "status": SCALE_STATUS,
        "claim_level": SCALE_CLAIM,
        "parent_repair": {
            "repair_digest": PARENT_REPAIR_DIGEST,
            "publication_checkpoint": PARENT_PUBLICATION_CHECKPOINT,
            "publication_ci_run_id": PARENT_PUBLICATION_CI_RUN_ID,
            "b25_result_reopened": False,
            "b25_failure_reclassified_as_diagnostic_only": False,
            "b25_launch_authorization_reused": False,
        },
        "source_and_ci": {
            "initial_scale_harness_checkpoint": INITIAL_SCALE_HARNESS_CHECKPOINT,
            "initial_scale_harness_ci_run_id": INITIAL_SCALE_HARNESS_CI_RUN_ID,
            "final_scale_source_checkpoint": SCALE_SOURCE_CHECKPOINT,
            "final_scale_source_ci_run_id": SCALE_SOURCE_CI_RUN_ID,
            "final_scale_source_ci_conclusion": "success",
            "linux_package_tests_passed": True,
            "windows_package_tests_passed": True,
            "linux_relevant_package_test_count": 291,
            "windows_relevant_package_test_count": 299,
            "warnings_denied_clippy_passed": True,
            "rustfmt_passed": True,
            "public_privacy_audit_passed": True,
            "bilingual_docs_validation_passed": True,
        },
        "residual_path_repair": {
            "residual_issue_found_during_comprehensive_review": True,
            "pre_fusion_ambiguous_containment_selected_one_position": True,
            "ambiguous_descendants_now_deferred_to_rrf_even_split": True,
            "unique_minimal_descendant_canonicalization_retained": True,
            "rrf_total_score_mass_conserved": True,
            "positional_or_hash_order_winner_created": False,
        },
        "linux_scale_stress": {
            "stress_schema_version": "product_bakeoff_determinism_linux_stress.v1",
            "synthetic_only": True,
            "private_input_read": False,
            "ignored_runs_used_as_input": False,
            "release_profile": True,
            "fresh_process_iterations_total": sum(
                tier["process_iterations"] for tier in tiers
            ),
            "test_invocations_total": sum(
                tier["test_invocations_total"] for tier in tiers
            ),
            "test_surfaces": [
                "persistent_bm25_complete_equal_score_boundary",
                "temporary_bm25_complete_equal_score_boundary",
                "rrf_ambiguous_overlap_score_conservation",
                "bakeoff_pre_fusion_ambiguous_overlap_normalization",
            ],
            "tiers": tiers,
            "declared_parameter_ceiling_exercised": True,
            "all_tiers_passed": True,
            "runner_identity_or_remote_path_public": False,
            "hardware_identity_or_exact_resource_metric_public": False,
        },
        "comprehensive_review": {
            "reviewed_scope": "exact_B2_through_B2_5_frozen_tournament_component_path",
            "reviewed_surfaces": [
                "persistent_and_temporary_bm25_boundary_collection",
                "literal_symbol_and_ast_capped_ordering",
                "graph_build_expansion_support_ordering_and_caps",
                "bakeoff_component_canonicalization_and_pre_fusion_overlap_handling",
                "rrf_rank_ties_exact_cells_containment_and_final_order",
                "adapter_candidate_order_and_two_step_support_projection",
                "future_scorer_equivalent_comparability_projection",
                "terminal_public_archive_validation",
            ],
            "known_remaining_order_dependent_cap_in_reviewed_scope": False,
            "whole_repository_determinism_claim_made": False,
            "unrelated_non_tournament_product_surface_changed": False,
        },
        "research_interpretation": {
            "historical_exact_semantic_gate_overinclusive_in_principle": True,
            "future_gate_and_scorer_must_share_projection": True,
            "b25_failure_reclassified_as_diagnostic_only": False,
            "b25_closeout_remains_authoritative": True,
            "b25_matrix_scored_or_ranked": False,
            "public_tournament_result_created": False,
        },
        "remaining_limits": {
            "production_scale_linux_stress_completed": True,
            "future_runtime_qualified": False,
            "future_holdout_authored": False,
            "future_tournament_authorized": False,
            "product_default_changed": False,
            "public_tournament_result_created": False,
        },
        "publication_limits": copy.deepcopy(PUBLICATION_LIMITS),
        "next_authorized_action": NEXT_ACTION,
        "scale_digest": "",
    }
    report["scale_digest"] = _digest(report)
    return report


def validate_public_report(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["determinism Linux scale report must be an object"]
    errors = list(b2p.scan_public_report(value))
    try:
        expected = build_public_report()
    except (DeterminismLinuxScaleError, OSError, ValueError) as exc:
        errors.append(f"cannot rebuild Linux scale report: {type(exc).__name__}")
        return sorted(set(errors))
    if value != expected:
        errors.append("determinism Linux scale report drifted")
    if value.get("scale_digest") != _digest(value):
        errors.append("determinism Linux scale digest mismatch")
    return sorted(set(errors))


def write_public(path: Path, report: Mapping[str, Any]) -> Path:
    if validate_public_report(dict(report)):
        raise DeterminismLinuxScaleError("refusing to write invalid Linux scale report")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise DeterminismLinuxScaleError("Linux scale report already exists")
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
        if os.path.lexists(target):
            raise DeterminismLinuxScaleError("Linux scale report appeared concurrently")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def run_self_test() -> dict[str, Any]:
    first = build_public_report()
    second = build_public_report()
    stress = first["linux_scale_stress"]
    checks = [
        first == second,
        not validate_public_report(first),
        first["parent_repair"]["b25_result_reopened"] is False,
        first["remaining_limits"]["production_scale_linux_stress_completed"] is True,
        first["remaining_limits"]["future_tournament_authorized"] is False,
        stress["all_tiers_passed"] is True,
        stress["declared_parameter_ceiling_exercised"] is True,
        first["scale_digest"] == _digest(first),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def run_fault_test() -> dict[str, Any]:
    mutators: dict[str, Callable[[dict[str, Any]], None]] = {
        "reopen": lambda value: value["parent_repair"].__setitem__(
            "b25_result_reopened", True
        ),
        "tier_fail": lambda value: value["linux_scale_stress"]["tiers"][
            1
        ].__setitem__("passed", False),
        "private_read": lambda value: value["linux_scale_stress"].__setitem__(
            "private_input_read", True
        ),
        "ceiling": lambda value: value["linux_scale_stress"].__setitem__(
            "declared_parameter_ceiling_exercised", False
        ),
        "overauthorize": lambda value: value["remaining_limits"].__setitem__(
            "future_tournament_authorized", True
        ),
        "checkpoint": lambda value: value["source_and_ci"].__setitem__(
            "final_scale_source_checkpoint", "0" * 40
        ),
        "scope": lambda value: value["comprehensive_review"].__setitem__(
            "whole_repository_determinism_claim_made", True
        ),
        "digest": lambda value: value.__setitem__(
            "scale_digest", "detlinux_" + "0" * 64
        ),
    }
    checks: list[bool] = []
    for mutate in mutators.values():
        value = build_public_report()
        mutate(value)
        checks.append(bool(validate_public_report(value)))
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post-B2.5 determinism Linux scale publication"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-public", type=Path)
    mode.add_argument("--validate-public", type=Path)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = run_self_test()
        _print(result)
        return 0 if result["passed"] else 1
    if args.fault_test:
        result = run_fault_test()
        _print(result)
        return 0 if result["passed"] else 1
    if args.validate_public:
        value = b2c.load_json(args.validate_public)
        errors = validate_public_report(value)
        _print({"passed": not errors, "errors": errors})
        return 0 if not errors else 1
    report = build_public_report()
    write_public(args.write_public, report)
    _print(
        {
            "written": True,
            "aggregate_only": True,
            "b25_result_reopened": False,
            "private_details_printed": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SCALE_SCHEMA",
    "SCALE_STATUS",
    "DeterminismLinuxScaleError",
    "build_public_report",
    "validate_public_report",
    "write_public",
    "run_self_test",
    "run_fault_test",
]
