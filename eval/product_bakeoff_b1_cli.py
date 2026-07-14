#!/usr/bin/env python3
"""Command-line entry point for the B1 v2.3 mechanics screen.

The run phase intentionally has no scorer/oracle import. Hidden scoring is
loaded dynamically only after every parent-owned pre-score gate passes.
"""

from __future__ import annotations

import argparse
import copy
import importlib
import json
import os
import re
import secrets
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from product_bakeoff_conformance import require_scoreable, scan_public_report
from product_bakeoff_b1_spec import (
    B1_ADAPTER_IDS,
    B1_ADAPTER_VERSION,
    B1_AGGREGATE_KEYS,
    B1_AGGREGATE_SCHEMA_VERSION,
    B1_CACHE_STATES,
    B1_CLAIM_LEVEL,
    B1_ONE_SHOT_RECORDS,
    B1_REPETITIONS,
    B1_RRF_MARKER,
    B1_RRF_INPUT_NORMALIZATION,
    B1_RRF_RANK_TIE_POLICY,
    B1_RRF_CHANNEL_WEIGHTS,
    B1_RRF_TIE_ORDER_WIRE,
    B1_RRF_VERSION,
    B1_RUST_SCHEMA_VERSION,
    B1_PARENT_RECEIPT_SCHEMA_VERSION,
    B1_SPEC_VERSION,
    B1_TOTAL_RECORDS,
    B1_TWO_STEP_RECORDS,
    S0_COMPONENTS,
    S4_S5_SUPPORT_COMPONENTS,
    B1_TWO_STEP_MAX_SUPPORT,
    b1_runtime_bundle_digest,
    b1_source_bundle_digest,
    b1_spec_digest,
)
from product_bakeoff_b1_fixtures import B1_ALL_TASKS, fixture_digest
from product_bakeoff_b1_adapters import (
    B1_ADAPTERS,
    RustReceiptError,
    _bakeoff_query_available,
    _check_wsr_inventory,
    _find_cli,
    _snapshot_source_digests,
    initialize_b1_wsr,
    parse_bakeoff_query,
    verify_index_seal,
    write_index_seal,
)
from product_bakeoff_b1_runner import (
    B1RunResult,
    PreScoreGateResult,
    _check_cold_warm_equality,
    _check_pre_score_gates,
    run_full_matrix,
    run_preflight_probe,
)


def generate_private_canary() -> str:
    return "canary_" + secrets.token_hex(16)


def _scoreable_count(result: B1RunResult) -> int:
    count = 0
    for record, capture in zip(result.records, result.captures):
        try:
            require_scoreable(record, capture)
        except Exception:
            continue
        count += 1
    return count


def _resource_complete_count(result: B1RunResult) -> int:
    return sum(
        1 for record in result.records
        if record.status == "accepted"
        and record.resource_sample is not None
        and record.resource_sample.cpu_seconds is not None
        and record.resource_sample.rss_bytes is not None
    )


def _gate_passed(result: B1RunResult, name: str) -> bool:
    return bool(
        result.gate_result is not None
        and name not in result.gate_result.gate_failures)


def build_sanitized_aggregate(
    result: B1RunResult,
    *,
    mechanics_pass: bool,
    canary_private_only: bool,
) -> dict[str, Any]:
    records = result.records
    accepted = sum(1 for record in records if record.status == "accepted")
    rejected = len(records) - accepted
    one_shot = sum(1 for record in records if record.interaction_mode == "one_shot")
    two_step = sum(1 for record in records if record.interaction_mode == "two_step")
    passing_adapters = {
        adapter for adapter in B1_ADAPTER_IDS
        if any(record.adapter_id == adapter for record in records)
        and all(record.status == "accepted" for record in records
                if record.adapter_id == adapter)
    }
    sentinel_expected = sum(
        int(receipt.get("sentinel_expected", 0))
        for receipt in result.parent_receipts)
    sentinel_passed = sum(
        int(receipt.get("sentinel_passed", 0))
        for receipt in result.parent_receipts)
    aggregate = {
        "schema_version": B1_AGGREGATE_SCHEMA_VERSION,
        "b1_spec_version": B1_SPEC_VERSION,
        "b1_claim_level": B1_CLAIM_LEVEL,
        "mechanics_pass": mechanics_pass,
        "total_records": len(records),
        "one_shot_records": one_shot,
        "two_step_records": two_step,
        "accepted_count": accepted,
        "rejected_count": rejected,
        "adapter_count": len(B1_ADAPTER_IDS),
        "task_count": len(B1_ALL_TASKS),
        "repetition_count": len(B1_REPETITIONS),
        "cache_state_count": len(B1_CACHE_STATES),
        "all_six_stacks_passing": len(passing_adapters) == len(B1_ADAPTER_IDS),
        "all_sentinels_passing": (
            sentinel_expected > 0 and sentinel_expected == sentinel_passed),
        "all_two_step_episodes_passing": _gate_passed(
            result, "two_step_lineage_valid"),
        "zero_provider_network_calls": result.provider_network_call_count == 0,
        "provider_network_call_count": result.provider_network_call_count,
        "resource_complete_count": _resource_complete_count(result),
        "same_execution_scoreable_count": _scoreable_count(result),
        "canary_present_in_private_only": canary_private_only,
        "sentinel_expected": sentinel_expected,
        "sentinel_passed": sentinel_passed,
        "all_lineages_valid": _gate_passed(result, "two_step_lineage_valid"),
        "privacy_absent": (
            result.privacy_canary_occurrences_before_score == 0),
        "determinism_confirmed": (
            _gate_passed(result, "cold_warm_semantic_equality")
            and _gate_passed(result, "repetition_determinism")),
        "fixture_digest": fixture_digest(),
        "spec_digest": b1_spec_digest(),
        "source_bundle_digest": result.source_bundle_digest,
        "runtime_bundle_digest": result.runtime_bundle_digest,
    }
    return aggregate


def validate_b1_aggregate(aggregate: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if set(aggregate) != set(B1_AGGREGATE_KEYS):
        failures.append(
            f"aggregate closed keys mismatch: missing="
            f"{sorted(B1_AGGREGATE_KEYS - set(aggregate))} extra="
            f"{sorted(set(aggregate) - B1_AGGREGATE_KEYS)}")
        return failures
    if aggregate["schema_version"] != B1_AGGREGATE_SCHEMA_VERSION:
        failures.append("aggregate schema_version mismatch")
    if aggregate["b1_spec_version"] != B1_SPEC_VERSION:
        failures.append("aggregate b1_spec_version mismatch")
    if aggregate["b1_claim_level"] != B1_CLAIM_LEVEL:
        failures.append("aggregate b1_claim_level mismatch")
    integer_keys = {
        "total_records", "one_shot_records", "two_step_records",
        "accepted_count", "rejected_count", "adapter_count", "task_count",
        "repetition_count", "cache_state_count", "provider_network_call_count",
        "resource_complete_count", "same_execution_scoreable_count",
        "sentinel_expected", "sentinel_passed",
    }
    for key in integer_keys:
        value = aggregate[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            failures.append(f"aggregate {key} must be a nonnegative integer")
    boolean_keys = B1_AGGREGATE_KEYS - integer_keys - {
        "schema_version", "b1_spec_version", "b1_claim_level",
        "fixture_digest", "spec_digest", "source_bundle_digest",
        "runtime_bundle_digest",
    }
    for key in boolean_keys:
        if not isinstance(aggregate[key], bool):
            failures.append(f"aggregate {key} must be boolean")
    if aggregate["total_records"] != (
            aggregate["one_shot_records"] + aggregate["two_step_records"]):
        failures.append("aggregate record partition mismatch")
    if aggregate["total_records"] != (
            aggregate["accepted_count"] + aggregate["rejected_count"]):
        failures.append("aggregate accepted/rejected mismatch")
    if aggregate["zero_provider_network_calls"] != (
            aggregate["provider_network_call_count"] == 0):
        failures.append("aggregate provider boolean/count mismatch")
    if aggregate["all_sentinels_passing"] != (
            aggregate["sentinel_expected"] > 0
            and aggregate["sentinel_expected"] == aggregate["sentinel_passed"]):
        failures.append("aggregate sentinel boolean/count mismatch")
    if aggregate["sentinel_passed"] > aggregate["sentinel_expected"]:
        failures.append("aggregate sentinel_passed exceeds expected")
    if aggregate["all_lineages_valid"] != aggregate["all_two_step_episodes_passing"]:
        failures.append("aggregate lineage booleans disagree")
    if aggregate["resource_complete_count"] > aggregate["accepted_count"]:
        failures.append("aggregate resource count exceeds accepted")
    if aggregate["same_execution_scoreable_count"] > aggregate["accepted_count"]:
        failures.append("aggregate scoreable count exceeds accepted")
    fixed_dimensions = {
        "adapter_count": len(B1_ADAPTER_IDS),
        "task_count": len(B1_ALL_TASKS),
        "repetition_count": len(B1_REPETITIONS),
        "cache_state_count": len(B1_CACHE_STATES),
    }
    for key, expected in fixed_dimensions.items():
        if aggregate[key] != expected:
            failures.append(f"aggregate {key} mismatch")
    if aggregate["mechanics_pass"]:
        required_counts = {
            "total_records": B1_TOTAL_RECORDS,
            "one_shot_records": B1_ONE_SHOT_RECORDS,
            "two_step_records": B1_TWO_STEP_RECORDS,
            "accepted_count": B1_TOTAL_RECORDS,
            "rejected_count": 0,
            "resource_complete_count": B1_TOTAL_RECORDS,
            "same_execution_scoreable_count": B1_TOTAL_RECORDS,
        }
        for key, expected in required_counts.items():
            if aggregate[key] != expected:
                failures.append(f"mechanics_pass requires {key}={expected}")
        required_true = {
            "all_six_stacks_passing", "all_sentinels_passing",
            "all_two_step_episodes_passing", "zero_provider_network_calls",
            "canary_present_in_private_only", "all_lineages_valid",
            "privacy_absent", "determinism_confirmed",
        }
        for key in required_true:
            if aggregate[key] is not True:
                failures.append(f"mechanics_pass requires {key}=true")
    expected_digests = {
        "fixture_digest": fixture_digest(),
        "spec_digest": b1_spec_digest(),
        "source_bundle_digest": b1_source_bundle_digest(),
        "runtime_bundle_digest": b1_runtime_bundle_digest(_find_cli()),
    }
    for key, expected in expected_digests.items():
        value = aggregate[key]
        if value != expected:
            failures.append(f"aggregate {key} mismatch")
    encoded = json.dumps(aggregate, sort_keys=True)
    if re.search(r"canary_[0-9a-f]{32}", encoded):
        failures.append("aggregate contains a private canary token")
    failures.extend(scan_public_report(aggregate))
    return failures


def _valid_parser_envelope(root: Path) -> dict[str, Any]:
    return {
        "schema_version": B1_RUST_SCHEMA_VERSION,
        "success": True,
        "mode": "context",
        "source_root": str(root.resolve()),
        "state_root": str(root.resolve()),
        "query": "harbor cadence ledger",
        "task_family": "definition_find",
        "max_results": 8,
        "components_requested": ["bm25"],
        "components_executed": ["bm25"],
        "evidence": [],
        "evidence_count": 0,
        "rrf": {
            "marker": B1_RRF_MARKER,
            "version": B1_RRF_VERSION,
            "k": 60,
            "tie_order": B1_RRF_TIE_ORDER_WIRE,
            "rank_tie_policy": B1_RRF_RANK_TIE_POLICY,
            "channel_weights": B1_RRF_CHANNEL_WEIGHTS,
            "input_normalization": B1_RRF_INPUT_NORMALIZATION,
            "input_rewrites": 0,
        },
        "receipts": [{
            "component": "bm25",
            "status": "executed",
            "evidence_count": 0,
            "diagnostics": {
                "index_source": "persistent_state_root",
                "state_root": str(root.resolve()),
                "separated": False,
                "deterministic_tie_order": B1_RRF_TIE_ORDER_WIRE,
                "exact_cell_dedup": True,
                "overfetch_limit": 64,
                "raw_evidence_count": 0,
                "canonical_evidence_count": 0,
                "stale_hits_skipped": 0,
                "invalid_hits_skipped": 0,
                "query_ms": 0.0,
                "materialize_ms": 0.0,
            },
        }],
        "provider": {
            "remote_calls": 0,
            "outbound_calls": 0,
            "audit_path": str((root / ".openlocus/audit/embeddings.jsonl").resolve()),
            "audit_events_before": 0,
            "audit_events_after": 0,
        },
        "trace": {
            "routed_to": str((root / ".openlocus/traces").resolve()),
            "event": "bakeoff_query_context",
            "written": True,
        },
    }


def _valid_support_parser_envelope(root: Path) -> dict[str, Any]:
    parent = "src/a17.rs"
    support = "src/z97.rs"
    return {
        "schema_version": B1_RUST_SCHEMA_VERSION,
        "success": True,
        "mode": "support",
        "source_root": str(root.resolve()),
        "state_root": str(root.resolve()),
        "max_results": B1_TWO_STEP_MAX_SUPPORT,
        "components_requested": ["support"],
        "components_executed": ["support"],
        "evidence": [{
            "path": support,
            "start_line": 1,
            "end_line": 1,
            "content_sha": "0" * 64,
            "score": 1.0,
            "why": ["production import edge"],
            "channels": ["graph"],
        }],
        "evidence_count": 1,
        "rrf": {
            "marker": B1_RRF_MARKER,
            "version": B1_RRF_VERSION,
            "k": 60,
            "tie_order": B1_RRF_TIE_ORDER_WIRE,
            "rank_tie_policy": B1_RRF_RANK_TIE_POLICY,
            "channel_weights": B1_RRF_CHANNEL_WEIGHTS,
            "input_normalization": B1_RRF_INPUT_NORMALIZATION,
            "input_rewrites": 0,
        },
        "receipts": [{
            "component": "support",
            "status": "executed",
            "evidence_count": 1,
            "diagnostics": {
                "depth": 1,
                "parent_path": parent,
                "parent_start_line": 1,
                "parent_end_line": 1,
                "parent_confinement": "validated_under_source_root",
                "parent_path_inferred_from_query": False,
                "skipped_stale": 0,
                "skipped_path_unsafe": 0,
                "inspect_saturated": False,
                "unsafe_skips_present": False,
                "edge_count": 1,
                "node_count": 2,
                "candidate_edges_all_relations": 1,
                "candidate_import_edges": 1,
                "materialized": 1,
                "materialization_skipped": 0,
            },
        }],
        "parent": {
            "path": parent,
            "start_line": 1,
            "end_line": 1,
            "confinement": "validated_under_source_root",
        },
        "relations": [{
            "relation_kind": "import",
            "production_edge_kind": "imports",
            "support_path": support,
            "support_start_line": 1,
            "support_end_line": 1,
            "target_path": parent,
            "target_start_line": 1,
            "target_end_line": 1,
        }],
        "provider": {
            "remote_calls": 0,
            "outbound_calls": 0,
            "audit_path": str(
                (root / ".openlocus/audit/embeddings.jsonl").resolve()),
            "audit_events_before": 0,
            "audit_events_after": 0,
        },
        "trace": {
            "routed_to": str((root / ".openlocus/traces").resolve()),
            "event": "bakeoff_query_support",
            "written": True,
        },
    }


def run_self_test() -> int:
    failures: list[str] = []
    if "product_bakeoff_b1_scorer" in sys.modules \
            or "product_bakeoff_oracle" in sys.modules:
        failures.append("CLI import loaded scorer/oracle")
    if len(B1_ALL_TASKS) != 12 or B1_TOTAL_RECORDS != 504:
        failures.append("frozen B1 matrix dimensions drifted")
    if fixture_digest() != fixture_digest() or b1_spec_digest() != b1_spec_digest():
        failures.append("fixture/spec digest is nondeterministic")
    if b1_source_bundle_digest() != b1_source_bundle_digest():
        failures.append("source bundle digest is nondeterministic")
    for task in B1_ALL_TASKS:
        if not re.fullmatch(r"b1_t\d{2}", task.task_slug):
            failures.append(f"non-opaque task slug {task.task_slug!r}")
        lowered_query = task.query.lower()
        for path in task.visible_files():
            if lowered_query and lowered_query in path.lower():
                failures.append(f"query token leaked into fixture path for {task.task_slug}")
            if any(role in path.lower() for role in (
                "target", "support", "answer", "oracle", "winner", "tie")):
                failures.append(f"role-shaped fixture path {path!r}")
    for adapter_id, descriptor_factory, hooks_factory in B1_ADAPTERS:
        descriptor = descriptor_factory()
        hooks = hooks_factory()
        if descriptor.adapter_id != adapter_id or hooks.index is not None:
            failures.append(f"adapter lifecycle shape drift for {adapter_id}")
    probe = {
        "schema_version": B1_AGGREGATE_SCHEMA_VERSION,
        "b1_spec_version": B1_SPEC_VERSION,
        "b1_claim_level": B1_CLAIM_LEVEL,
        "mechanics_pass": False,
        "total_records": 0,
        "one_shot_records": 0,
        "two_step_records": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "adapter_count": 6,
        "task_count": 12,
        "repetition_count": 3,
        "cache_state_count": 2,
        "all_six_stacks_passing": False,
        "all_sentinels_passing": False,
        "all_two_step_episodes_passing": False,
        "zero_provider_network_calls": True,
        "provider_network_call_count": 0,
        "resource_complete_count": 0,
        "same_execution_scoreable_count": 0,
        "canary_present_in_private_only": False,
        "sentinel_expected": 0,
        "sentinel_passed": 0,
        "all_lineages_valid": False,
        "privacy_absent": True,
        "determinism_confirmed": False,
        "fixture_digest": fixture_digest(),
        "spec_digest": b1_spec_digest(),
        "source_bundle_digest": b1_source_bundle_digest(),
        "runtime_bundle_digest": b1_runtime_bundle_digest(_find_cli()),
    }
    failures.extend(validate_b1_aggregate(probe))
    print(json.dumps({
        "self_test_pass": not failures,
        "failure_count": len(failures),
        "failures": failures,
    }))
    return 0 if not failures else 1


def run_fault_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="b1_fault_") as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src/a17.rs").write_text("x\n", encoding="utf-8")
        (root / "src/z97.rs").write_text("use crate::a17;\n", encoding="utf-8")
        initialize_b1_wsr(root)
        (root / ".openlocus/traces").mkdir(parents=True, exist_ok=True)
        good = _valid_parser_envelope(root)
        parser_kwargs = {
            "expected_source_root": root,
            "expected_state_root": root,
            "expected_query": "harbor cadence ledger",
            "expected_task_family": "definition_find",
            "expected_max_results": 8,
        }
        try:
            parse_bakeoff_query(
                json.dumps(good), S0_COMPONENTS, ("src/a17.rs",),
                "context", "req", **parser_kwargs)
        except Exception as exc:
            failures.append(f"valid strict parser fixture rejected: {type(exc).__name__}")
        mutations = []
        missing_component = copy.deepcopy(good)
        missing_component["receipts"] = []
        mutations.append(("stack omission", json.dumps(missing_component)))
        wrong_rrf = copy.deepcopy(good)
        wrong_rrf["rrf"]["marker"] = "python_rrf"
        mutations.append(("wrong fusion", json.dumps(wrong_rrf)))
        extra_key = copy.deepcopy(good)
        extra_key["unexpected"] = True
        mutations.append(("outer envelope", json.dumps(extra_key)))
        remote = copy.deepcopy(good)
        remote["provider"]["remote_calls"] = 1
        mutations.append(("provider call", json.dumps(remote)))
        stale_audit = copy.deepcopy(good)
        stale_audit["provider"]["audit_events_before"] = 1
        stale_audit["provider"]["audit_events_after"] = 1
        mutations.append(("nonempty provider audit", json.dumps(stale_audit)))
        trace_false = copy.deepcopy(good)
        trace_false["trace"]["written"] = False
        mutations.append(("missing checked trace", json.dumps(trace_false)))
        component_error = copy.deepcopy(good)
        component_error["receipts"][0].update({
            "status": "error", "reason": "configured failure",
        })
        mutations.append(("component error", json.dumps(component_error)))
        duplicate_key = json.dumps(good).replace(
            '"success": true', '"success": true, "success": true', 1)
        mutations.append(("duplicate JSON key", duplicate_key))
        mutations.append(("extra stdout", json.dumps(good) + "\n{}"))
        for label, raw in mutations:
            try:
                parse_bakeoff_query(
                    raw, S0_COMPONENTS, ("src/a17.rs",),
                    "context", "req", **parser_kwargs)
            except RustReceiptError:
                pass
            else:
                failures.append(f"strict parser accepted {label} fault")

        support_good = _valid_support_parser_envelope(root)
        support_kwargs = {
            "expected_source_root": root,
            "expected_state_root": root,
            "expected_query": None,
            "expected_task_family": None,
            "expected_max_results": B1_TWO_STEP_MAX_SUPPORT,
        }
        try:
            parse_bakeoff_query(
                json.dumps(support_good), S4_S5_SUPPORT_COMPONENTS,
                ("src/a17.rs", "src/z97.rs"), "support", "support_req",
                **support_kwargs,
            )
        except Exception as exc:
            failures.append(
                f"valid support parser fixture rejected: {type(exc).__name__}")
        support_mutations: list[tuple[str, dict[str, Any]]] = []
        forged_parent = copy.deepcopy(support_good)
        forged_parent["relations"][0]["target_path"] = "src/z97.rs"
        support_mutations.append(("forged relation target", forged_parent))
        forged_relation = copy.deepcopy(support_good)
        forged_relation["relations"][0]["relation_kind"] = "caller"
        support_mutations.append(("forged relation kind", forged_relation))
        forged_edge = copy.deepcopy(support_good)
        forged_edge["relations"][0]["production_edge_kind"] = "tests"
        support_mutations.append(("forged production edge", forged_edge))
        path_inferred = copy.deepcopy(support_good)
        path_inferred["receipts"][0]["diagnostics"][
            "parent_path_inferred_from_query"] = True
        support_mutations.append(("query-derived parent path", path_inferred))
        duplicate_channel = copy.deepcopy(support_good)
        duplicate_channel["evidence"][0]["channels"] = ["graph", "graph"]
        support_mutations.append(("duplicate evidence channel", duplicate_channel))
        for label, envelope in support_mutations:
            try:
                parse_bakeoff_query(
                    json.dumps(envelope), S4_S5_SUPPORT_COMPONENTS,
                    ("src/a17.rs", "src/z97.rs"), "support", "support_req",
                    **support_kwargs,
                )
            except RustReceiptError:
                pass
            else:
                failures.append(f"support parser accepted {label} fault")

        index = root / ".openlocus/index"
        index.mkdir(parents=True)
        (index / "segment.bin").write_bytes(b"sealed")
        write_index_seal(root)
        verify_index_seal(root)
        (index / "segment.bin").write_bytes(b"replaced")
        try:
            verify_index_seal(root)
        except Exception:
            pass
        else:
            failures.append("index seal accepted replacement")
        (index / "segment.bin").write_bytes(b"sealed")
        write_index_seal(root)
        sibling = root / ".openlocus/sibling"
        sibling.mkdir()
        if not _check_wsr_inventory(root):
            failures.append("WSR inventory accepted undeclared sibling")
        sibling.rmdir()
        audit_path = root / ".openlocus/audit/embeddings.jsonl"
        audit_path.write_text("{}\n", encoding="utf-8")
        if not _check_wsr_inventory(root):
            failures.append("WSR inventory accepted nonempty provider audit")
        audit_path.write_bytes(b"")
        link_path = root / ".openlocus/b1/transcripts/linked.json"
        link_target = root / "link-target.json"
        link_target.write_text("{}", encoding="utf-8")
        try:
            os.symlink(link_target, link_path)
        except OSError:
            pass  # Windows may deny symlink creation without Developer Mode.
        else:
            if not _check_wsr_inventory(root):
                failures.append("WSR inventory accepted a symlink/reparse entry")

    before_modules = set(sys.modules)
    gate = _check_pre_score_gates(
        [], [], [], [], [], [], [], [],
        preflight_passed=False, privacy_canary_occurrences=0)
    if gate.passed:
        failures.append("empty/503-equivalent pre-score matrix passed")
    required_gate_failures = {
        "preflight_converged", "disjoint_union_504",
        "all_resource_complete", "require_scoreable_all",
    }
    if not required_gate_failures <= set(gate.gate_failures):
        failures.append("503/resource/capture pre-score faults were not isolated")
    newly_loaded = set(sys.modules) - before_modules
    if "product_bakeoff_b1_scorer" in newly_loaded \
            or "product_bakeoff_oracle" in newly_loaded:
        failures.append("pre-score failure loaded scorer/oracle")

    cold_record = types.SimpleNamespace(
        adapter_id=B1_ADAPTER_IDS[0], run_cell_id="b1_t01",
        adapter_repetition=1, cache_state="cold",
        interaction_mode="one_shot", operation="context",
        canonical_pack_hash="cph_0000000000000000",
    )
    warm_record = copy.copy(cold_record)
    warm_record.cache_state = "warm"
    determinism_gate = PreScoreGateResult(passed=True)
    _check_cold_warm_equality([
        types.SimpleNamespace(
            record=cold_record, semantic_hash="b1sem_" + "1" * 64,
            parent_receipt={"index_inventory_digest": "idx_" + "1" * 64}),
        types.SimpleNamespace(
            record=warm_record, semantic_hash="b1sem_" + "2" * 64,
            parent_receipt={"index_inventory_digest": "idx_" + "2" * 64}),
    ], determinism_gate)
    if determinism_gate.passed:
        failures.append("cold/warm determinism-state corruption passed")

    aggregate_seed = B1RunResult(
        source_bundle_digest=b1_source_bundle_digest(),
        runtime_bundle_digest=b1_runtime_bundle_digest(_find_cli()),
    )
    aggregate_good = build_sanitized_aggregate(
        aggregate_seed, mechanics_pass=False, canary_private_only=False)
    if validate_b1_aggregate(aggregate_good):
        failures.append("valid failure aggregate was rejected")
    aggregate_faults: list[tuple[str, dict[str, Any]]] = []
    extra_aggregate = copy.deepcopy(aggregate_good)
    extra_aggregate["unexpected"] = True
    aggregate_faults.append(("extra key", extra_aggregate))
    count_aggregate = copy.deepcopy(aggregate_good)
    count_aggregate["total_records"] = 1
    aggregate_faults.append(("count inconsistency", count_aggregate))
    provider_aggregate = copy.deepcopy(aggregate_good)
    provider_aggregate["provider_network_call_count"] = 1
    aggregate_faults.append(("provider inconsistency", provider_aggregate))
    canary_aggregate = copy.deepcopy(aggregate_good)
    canary_aggregate["source_bundle_digest"] = generate_private_canary()
    aggregate_faults.append(("canary leak", canary_aggregate))
    digest_aggregate = copy.deepcopy(aggregate_good)
    digest_aggregate["spec_digest"] = "b1spec_0000000000000000"
    aggregate_faults.append(("digest substitution", digest_aggregate))
    false_pass = copy.deepcopy(aggregate_good)
    false_pass["mechanics_pass"] = True
    aggregate_faults.append(("hard-coded pass", false_pass))
    for label, aggregate in aggregate_faults:
        if not validate_b1_aggregate(aggregate):
            failures.append(f"aggregate validator accepted {label} fault")

    scorer = importlib.import_module("product_bakeoff_b1_scorer")
    from product_bakeoff_contract import (
        BudgetUsage, Candidate, ContextPack, PackTarget,
    )

    adapter_id = B1_ADAPTER_IDS[0]
    record = types.SimpleNamespace(
        adapter_id=adapter_id,
        run_cell_id="b1_t09",
        interaction_mode="one_shot",
        operation="context",
        cache_state="cold",
        adapter_repetition=1,
        fingerprint="fp_0000000000000000",
        canonical_result_hash="crh_0000000000000000",
        canonical_pack_hash="cph_0000000000000000",
        status="accepted",
        result_status="ok",
    )
    candidates = (
        Candidate(
            path="src/j11.rs", start_line=1, end_line=1, score=1.0,
            reason="tie", channels=frozenset({"bm25"}),
            adapter_provenance=adapter_id,
        ),
        Candidate(
            path="src/k23.rs", start_line=1, end_line=1, score=1.0,
            reason="tie", channels=frozenset({"bm25"}),
            adapter_provenance=adapter_id,
        ),
    )
    budget = BudgetUsage(
        candidate_count=2, evidence_count=2, target_count=1,
        support_count=0, rendered_chars=0, rendered_bytes=0,
        rendered_estimate=0, episode_step_count=1,
        episode_estimate_used=0,
    )
    pack = ContextPack(
        pack_status="uncertain", status_reason="cross-path exact top tie",
        targets=(PackTarget(0, "src/j11.rs", 1, 1),), support=(),
        diagnostics=(), budget_usage=budget, rendered_context="",
        operation="context",
    )
    output = types.SimpleNamespace(
        canonical_result_hash=record.canonical_result_hash,
        canonical_pack_hash=record.canonical_pack_hash,
        validated_candidates=candidates,
        pack=pack,
    )
    capture = types.SimpleNamespace(output=output)
    parent_receipt = {
        "schema_version": B1_PARENT_RECEIPT_SCHEMA_VERSION,
        "request_id": f"b1_req_b1_t09_{adapter_id}_rep1_cold",
        "adapter_id": adapter_id,
        "task_slug": "b1_t09",
        "operation": "context",
        "cache_state": "cold",
        "adapter_repetition": 1,
        "record_fingerprint": record.fingerprint,
        "canonical_result_hash": record.canonical_result_hash,
        "canonical_pack_hash": record.canonical_pack_hash,
        "semantic_hash": "b1sem_" + "a" * 64,
        "component_receipts": [{
            "component": "bm25", "status": "executed",
            "evidence_count": 2,
        }],
        "rrf_receipt": {
            "marker": B1_RRF_MARKER,
            "version": B1_RRF_VERSION,
            "k": 60,
            "tie_order": B1_RRF_TIE_ORDER_WIRE,
            "rank_tie_policy": B1_RRF_RANK_TIE_POLICY,
            "channel_weights": B1_RRF_CHANNEL_WEIGHTS,
            "input_normalization": B1_RRF_INPUT_NORMALIZATION,
            "input_rewrites": 0,
        },
        "provider_network_call_count": 0,
        "trace_written": True,
        "sentinel_expected": 3,
        "sentinel_passed": 3,
        "index_inventory_digest": "idx_" + "b" * 64,
        "prepare_transcript_sha256": "c" * 64,
        "query_transcript_sha256": "d" * 64,
        "capture_candidate_count": 2,
        "capture_target_count": 1,
        "capture_support_count": 0,
    }
    if scorer._assert_parent_receipt_binding(  # noqa: SLF001
            record, capture, parent_receipt):
        failures.append("valid scorer parent binding fixture was rejected")
    warm_bound_record = copy.copy(record)
    warm_bound_record.cache_state = "warm"
    warm_parent_receipt = copy.deepcopy(parent_receipt)
    warm_parent_receipt["request_id"] = (
        f"b1_req_b1_t09_{adapter_id}_rep1_warm")
    warm_parent_receipt["cache_state"] = "warm"
    warm_parent_receipt["prepare_transcript_sha256"] = None
    if scorer._assert_parent_receipt_binding(  # noqa: SLF001
            warm_bound_record, capture, warm_parent_receipt):
        failures.append("valid warm parent binding fixture was rejected")
    warm_rebuild_receipt = copy.deepcopy(warm_parent_receipt)
    warm_rebuild_receipt["prepare_transcript_sha256"] = "e" * 64
    if not scorer._assert_parent_receipt_binding(  # noqa: SLF001
            warm_bound_record, capture, warm_rebuild_receipt):
        failures.append("scorer accepted a warm lifecycle rebuild")
    corrupted_receipt = copy.deepcopy(parent_receipt)
    corrupted_receipt["capture_candidate_count"] = 1
    if not scorer._assert_parent_receipt_binding(  # noqa: SLF001
            record, capture, corrupted_receipt):
        failures.append("scorer accepted receipt-to-capture corruption")
    task = next(task for task in B1_ALL_TASKS if task.task_slug == "b1_t09")
    oracle = scorer.B1_ORACLES[task.task_slug]
    tie_failures = scorer._assert_context_cell(  # noqa: SLF001
        task, oracle, adapter_id, record, capture, parent_receipt)
    if tie_failures:
        failures.append("valid exact-tie scorer fixture was rejected")
    perturbed_output = copy.copy(output)
    perturbed_output.validated_candidates = (
        candidates[0],
        Candidate(
            path="src/k23.rs", start_line=1, end_line=1, score=0.5,
            reason="tie", channels=frozenset({"bm25"}),
            adapter_provenance=adapter_id,
        ),
    )
    perturbed_capture = types.SimpleNamespace(output=perturbed_output)
    if not scorer._assert_context_cell(  # noqa: SLF001
            task, oracle, adapter_id, record, perturbed_capture,
            parent_receipt):
        failures.append("scorer accepted one-cell tie perturbation")

    canary = generate_private_canary()
    if not re.fullmatch(r"canary_[0-9a-f]{32}", canary):
        failures.append("canary format fault")
    print(json.dumps({
        "fault_test_pass": not failures,
        "failure_count": len(failures),
        "failures": failures,
    }))
    return 0 if not failures else 1


def _count_canary_files(root: Path, canary: str) -> int:
    needle = canary.encode("utf-8")
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            count += path.read_bytes().count(needle)
    return count


def run_probe(runs_dir: Path | None) -> int:
    cli = _find_cli()
    os.environ["OPENLOCUS_CLI"] = cli
    root = runs_dir or Path("runs") / "b1_v2_probe"
    result = run_preflight_probe(root)
    public = {
        "preflight_pass": bool(result.get("passed")),
        "record_count": int(result.get("record_count", 0)),
        "parent_receipt_count": int(result.get("parent_receipt_count", 0)),
        "failure_count": len(result.get("failures", [])),
    }
    print(json.dumps(public, sort_keys=True, separators=(",", ":")))
    return 0 if public["preflight_pass"] else 1


def run_full_screen(runs_dir: Path | None) -> int:
    if "product_bakeoff_b1_scorer" in sys.modules \
            or "product_bakeoff_oracle" in sys.modules:
        raise RuntimeError("scorer/oracle loaded before B1 execution")
    cli = _find_cli()
    os.environ["OPENLOCUS_CLI"] = cli
    canary = generate_private_canary()
    result = run_full_matrix(runs_dir, canary=canary)
    gate_passed = bool(result.gate_result and result.gate_result.passed)
    if not gate_passed:
        aggregate = build_sanitized_aggregate(
            result, mechanics_pass=False, canary_private_only=False)
        aggregate_failures = validate_b1_aggregate(aggregate)
        if aggregate_failures:
            aggregate["mechanics_pass"] = False
        print(json.dumps(aggregate, sort_keys=True, separators=(",", ":")))
        return 1

    if "product_bakeoff_b1_scorer" in sys.modules \
            or "product_bakeoff_oracle" in sys.modules:
        raise RuntimeError("pre-score gates did not preserve scorer isolation")
    scorer = importlib.import_module("product_bakeoff_b1_scorer")
    scorer.assert_b1_run_phase_isolation()
    placeholder = json.dumps({"mechanics_pass": False}, sort_keys=True)
    score = scorer.score_b1(
        result.records, result.captures, result.parent_receipts,
        canary=canary, public_aggregate_text=placeholder)
    scorer.write_private_scorer_output(Path(result.runs_dir), canary, score)
    canary_count = _count_canary_files(Path(result.runs_dir), canary)
    canary_private_only = (
        result.privacy_canary_occurrences_before_score == 0
        and canary_count == 1)
    mechanics_pass = bool(score.mechanics_pass and canary_private_only)
    aggregate = build_sanitized_aggregate(
        result, mechanics_pass=mechanics_pass,
        canary_private_only=canary_private_only)
    failures = validate_b1_aggregate(aggregate)
    if failures:
        aggregate["mechanics_pass"] = False
        mechanics_pass = False
    aggregate_text = json.dumps(aggregate, sort_keys=True, separators=(",", ":"))
    if canary in aggregate_text:
        raise RuntimeError("private canary leaked into final aggregate")
    private_aggregate = Path(result.runs_dir) / "private" / "b1_sanitized_aggregate.json"
    private_aggregate.write_text(aggregate_text, encoding="utf-8")
    print(aggregate_text)
    return 0 if mechanics_pass else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenLocus B1 mechanics screen")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--full-screen", action="store_true")
    parser.add_argument("--runs-dir", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_test()
    if args.fault_test:
        return run_fault_test()
    if args.probe:
        return run_probe(args.runs_dir)
    return run_full_screen(args.runs_dir)


if __name__ == "__main__":
    raise SystemExit(main())
