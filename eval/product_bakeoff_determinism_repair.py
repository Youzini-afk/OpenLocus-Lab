#!/usr/bin/env python3
"""Aggregate-only publication for the post-B2.5 determinism repair."""

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
import product_bakeoff_terminal_archive as archive


REPO_ROOT = Path(__file__).resolve().parents[1]
B25_FAILURE_PATH = (
    REPO_ROOT
    / "artifacts"
    / "product_bakeoff_b25"
    / "product_bakeoff_b25_failed_closed_aggregate.json"
)

REPAIR_SCHEMA = "product_bakeoff_postcloseout_determinism_repair.v1"
REPAIR_STATUS = (
    "product_bakeoff_postcloseout_determinism_repair_complete_"
    "no_b25_result_change"
)
REPAIR_PHASE = (
    "product_bakeoff_postcloseout_retrieval_determinism_and_"
    "comparability_repair"
)
REPAIR_DATE = "2026-07-17"
REPAIR_CLAIM = "engineering_determinism_and_gate_design_only_no_tournament_result"

B25_CLOSEOUT_CHECKPOINT = "9d5df3fca8e952f8933ff8694113d83e7cf82b9e"
B25_CLOSEOUT_CI_RUN_ID = 29530318657
B25_FAILURE_DIGEST = (
    "b25failure_012f59fc4d7d717b4f1d4f0da5513430637d4a6cc6eaf8a326a35adc339302fd"
)
REPAIR_SOURCE_CHECKPOINT = "85f284a5248d5b066e11405a2453c85f84fc1e6a"
REPAIR_CI_RUN_ID = 29537075918

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
    "Keep B2.5 closed as failed_closed_no_result. Before any separately "
    "preregistered future tournament, run public synthetic Linux scale and "
    "cross-process stress for the repaired retrieval boundaries, freeze the "
    "scorer-equivalent comparability policy before treatment output, qualify "
    "the exact future runtime, and author a fresh holdout that reuses no B2.5 "
    "treatment output or launch authorization."
)


class DeterminismRepairError(ValueError):
    """Fail-closed error for the public repair aggregate."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop("repair_digest", None)
    return "detrepair_" + hashlib.sha256(_canonical(payload)).hexdigest()


def _validate_parent() -> dict[str, Any]:
    if archive.validate_archive("b25"):
        raise DeterminismRepairError("terminal archive is invalid")
    parent = b2c.load_json(B25_FAILURE_PATH)
    if (
        parent.get("status") != "product_bakeoff_b25_execution_failed_closed_no_result"
        or parent.get("failure_aggregate_digest") != B25_FAILURE_DIGEST
    ):
        raise DeterminismRepairError("B2.5 closeout parent drifted")
    return parent


def build_public_report() -> dict[str, Any]:
    _validate_parent()
    report: dict[str, Any] = {
        "schema_version": REPAIR_SCHEMA,
        "phase": REPAIR_PHASE,
        "date": REPAIR_DATE,
        "status": REPAIR_STATUS,
        "claim_level": REPAIR_CLAIM,
        "parent_closeout": {
            "checkpoint": B25_CLOSEOUT_CHECKPOINT,
            "ci_run_id": B25_CLOSEOUT_CI_RUN_ID,
            "ci_conclusion": "success",
            "failure_aggregate_digest": B25_FAILURE_DIGEST,
            "b25_result_reopened": False,
            "b25_matrix_scored_or_ranked": False,
            "b25_launch_authorization_reused": False,
        },
        "repair_checkpoint": {
            "source_checkpoint": REPAIR_SOURCE_CHECKPOINT,
            "ci_run_id": REPAIR_CI_RUN_ID,
            "ci_conclusion": "success",
            "linux_package_tests_passed": True,
            "windows_package_tests_passed": True,
            "package_test_count_per_os": 297,
            "package_test_os_count": 2,
            "deterministic_process_iterations": 8,
            "deterministic_boundary_tests_per_iteration": 6,
            "warnings_denied_clippy_passed": True,
            "rustfmt_passed": True,
            "public_privacy_audit_passed": True,
            "bilingual_docs_validation_passed": True,
        },
        "root_cause_classes": {
            "persistent_bm25_equal_score_boundary_used_document_address_ties": True,
            "temporary_bm25_equal_score_boundary_used_document_address_ties": True,
            "rrf_containment_transfer_depended_on_unordered_map_iteration": True,
            "graph_config_edge_cap_selected_from_unordered_set": True,
            "capped_text_symbol_ast_and_context_seed_paths_inherited_input_order": True,
            "terminal_artifact_validation_rebound_historical_source_to_current_head": True,
        },
        "engineering_repairs": {
            "bm25_complete_boundary_tie_expansion_before_stable_sort": True,
            "bm25_stable_score_path_range_and_content_tiebreak": True,
            "bm25_exact_cell_dedup_before_cap": True,
            "rrf_sorted_channel_and_exact_cell_accumulation": True,
            "rrf_ambiguous_wider_vote_split_evenly_across_minimal_descendants": True,
            "rrf_total_score_mass_conserved": True,
            "graph_records_edges_caps_and_serialized_kind_counts_ordered": True,
            "capped_text_symbol_ast_and_context_seed_paths_ordered": True,
            "terminal_archive_uses_canonical_artifact_locks_and_cross_links": True,
            "terminal_archive_current_source_rebinding_used": False,
        },
        "comparability_review": {
            "historical_exact_semantic_hash_overinclusive_in_principle": True,
            "diagnostic_only_drift_can_be_scorer_equivalent": True,
            "future_policy_is_oracle_blind_and_scorer_equivalent": True,
            "future_context_projection_includes": [
                "admission_envelope",
                "candidate_set_empty_or_nonempty",
                "pack_status",
                "evidence_line_union",
                "target_line_union",
                "support_set_empty_or_nonempty",
            ],
            "future_support_projection_includes": [
                "admission_envelope",
                "relation_kind",
                "parent_target_id",
                "support_path_and_line_union",
            ],
            "diagnostic_only_examples_excluded_from_future_score_projection": [
                "candidate_native_score_and_order",
                "duplicate_span_segmentation",
                "excerpt_channel_and_explanation_metadata",
                "pack_status_reason_text",
            ],
            "source_currentness_lineage_fairness_and_provider_isolation_remain_separate_gates": True,
            "future_policy_must_be_preregistered_before_treatment_output": True,
            "future_scorer_must_use_the_same_repeatability_projection": True,
            "b25_gate_relaxed_retroactively": False,
            "b25_failure_reclassified_as_diagnostic_only": False,
            "b25_closeout_remains_authoritative": True,
        },
        "historical_archive": {
            "public_artifact_count": 15,
            "canonical_json_locks_verified": True,
            "self_digests_verified_where_canonically_constructed": True,
            "cross_phase_public_bindings_verified": True,
            "private_input_read": False,
        },
        "remaining_limits": {
            "production_scale_linux_stress_completed": False,
            "future_runtime_qualified": False,
            "future_holdout_authored": False,
            "future_tournament_authorized": False,
            "product_default_changed": False,
            "public_tournament_result_created": False,
        },
        "publication_limits": copy.deepcopy(PUBLICATION_LIMITS),
        "next_authorized_action": NEXT_ACTION,
        "repair_digest": "",
    }
    report["repair_digest"] = _digest(report)
    return report


def validate_public_report(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["determinism repair report must be an object"]
    errors = list(b2p.scan_public_report(value))
    try:
        expected = build_public_report()
    except (DeterminismRepairError, OSError, ValueError) as exc:
        errors.append(f"cannot rebuild determinism repair report: {type(exc).__name__}")
        return sorted(set(errors))
    if value != expected:
        errors.append("determinism repair report drifted")
    if value.get("repair_digest") != _digest(value):
        errors.append("determinism repair digest mismatch")
    return sorted(set(errors))


def write_public(path: Path, report: Mapping[str, Any]) -> Path:
    if validate_public_report(dict(report)):
        raise DeterminismRepairError("refusing to write invalid repair report")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise DeterminismRepairError("repair report already exists")
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
            raise DeterminismRepairError("repair report appeared concurrently")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def run_self_test() -> dict[str, Any]:
    first = build_public_report()
    second = build_public_report()
    checks = [
        first == second,
        not validate_public_report(first),
        first["parent_closeout"]["b25_result_reopened"] is False,
        first["comparability_review"]["b25_gate_relaxed_retroactively"] is False,
        first["remaining_limits"]["future_tournament_authorized"] is False,
        first["repair_digest"] == _digest(first),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def run_fault_test() -> dict[str, Any]:
    mutators: dict[str, Callable[[dict[str, Any]], None]] = {
        "reopen": lambda value: value["parent_closeout"].__setitem__(
            "b25_result_reopened", True
        ),
        "ci": lambda value: value["repair_checkpoint"].__setitem__(
            "ci_conclusion", "failure"
        ),
        "stress": lambda value: value["repair_checkpoint"].__setitem__(
            "deterministic_process_iterations", 0
        ),
        "retroactive_gate": lambda value: value["comparability_review"].__setitem__(
            "b25_gate_relaxed_retroactively", True
        ),
        "private": lambda value: value["publication_limits"].__setitem__(
            "exact_private_failed_gate_or_divergence_public", True
        ),
        "digest": lambda value: value.__setitem__(
            "repair_digest", "detrepair_" + "0" * 64
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
        description="Post-B2.5 retrieval determinism repair publication"
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
    "REPAIR_SCHEMA",
    "REPAIR_STATUS",
    "DeterminismRepairError",
    "build_public_report",
    "validate_public_report",
    "write_public",
    "run_self_test",
    "run_fault_test",
]
