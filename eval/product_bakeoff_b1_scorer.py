#!/usr/bin/env python3
"""Hidden B1 v2.4 fixture scorer.

This module is imported only after every structural, execution, resource,
state, lineage, provider and privacy gate has passed. It contains the exact
synthetic expectations and may import ``product_bakeoff_oracle``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from product_bakeoff_contract import ContextPack, stable_target_id
from product_bakeoff_b1_spec import (
    B1_ADAPTER_IDS,
    B1_CACHE_STATES,
    B1_REPETITIONS,
    B1_TOTAL_RECORDS,
    B1_PARENT_RECEIPT_SCHEMA_VERSION,
    B1_RRF_K,
    B1_RRF_MARKER,
    B1_RRF_VERSION,
    B1_RRF_TIE_ORDER_WIRE,
    B1_RRF_RANK_TIE_POLICY,
    B1_RRF_CHANNEL_WEIGHTS,
    B1_RRF_INPUT_NORMALIZATION,
    B1_GRAPH_ELIGIBLE_TASK_FAMILIES,
    S0_ADAPTER_ID,
    S1_ADAPTER_ID,
    S2_ADAPTER_ID,
    S3_ADAPTER_ID,
    S4_ADAPTER_ID,
    S5_ADAPTER_ID,
    S0_OUTPUT_CHANNELS,
    S1_OUTPUT_CHANNELS,
    S2_OUTPUT_CHANNELS,
    S3_OUTPUT_CHANNELS,
    S4_OUTPUT_CHANNELS,
    S5_OUTPUT_CHANNELS,
    adapter_context_components,
    adapter_supports_support,
)
from product_bakeoff_b1_fixtures import B1_ALL_TASKS, B1Task
from product_bakeoff_oracle import (
    ORACLE_SCHEMA_VERSION,
    OracleSupportRecord,
    TaskOracle,
    assert_run_phase_not_importing_oracle,
)

SCORER_VERSION = "product_bakeoff_b1_scorer.v2.4"

B1_RUN_PHASE_MODULES = (
    "product_bakeoff_contract",
    "product_bakeoff_conformance",
    "product_bakeoff_b1_spec",
    "product_bakeoff_b1_fixtures",
    "product_bakeoff_b1_adapters",
    "product_bakeoff_b1_runner",
    "product_bakeoff_b1_cli",
)


def assert_b1_run_phase_isolation() -> None:
    assert_run_phase_not_importing_oracle(B1_RUN_PHASE_MODULES)


_ALL = tuple(B1_ADAPTER_IDS)
_SUPPORT = {S4_ADAPTER_ID, S5_ADAPTER_ID}
_OUTPUT_CHANNELS = {
    S0_ADAPTER_ID: S0_OUTPUT_CHANNELS,
    S1_ADAPTER_ID: S1_OUTPUT_CHANNELS,
    S2_ADAPTER_ID: S2_OUTPUT_CHANNELS,
    S3_ADAPTER_ID: S3_OUTPUT_CHANNELS,
    S4_ADAPTER_ID: S4_OUTPUT_CHANNELS,
    S5_ADAPTER_ID: S5_OUTPUT_CHANNELS,
}


def _all_span(path: str, start: int, end: int) -> dict[str, tuple[str, int, int]]:
    return {adapter: (path, start, end) for adapter in _ALL}


_PRIMARY_SPANS: dict[str, dict[str, tuple[str, int, int]]] = {
    "b1_t01": {
        S0_ADAPTER_ID: ("src/a17.rs", 1, 3),
        **{adapter: ("src/a17.rs", 2, 2) for adapter in _ALL[1:]},
    },
    "b1_t02": {
        S0_ADAPTER_ID: ("src/a19.ts", 1, 3),
        **{adapter: ("src/a19.ts", 2, 2) for adapter in _ALL[1:]},
    },
    "b1_t03": _all_span("src/b29.rs", 1, 1),
    "b1_t04": _all_span("src/b31.ts", 1, 1),
    "b1_t05": {
        S0_ADAPTER_ID: ("src/c41.rs", 1, 2),
        **{adapter: ("src/c41.rs", 1, 1) for adapter in _ALL[1:]},
    },
    "b1_t06": {
        S0_ADAPTER_ID: ("src/c43.ts", 1, 2),
        **{adapter: ("src/c43.ts", 1, 1) for adapter in _ALL[1:]},
    },
    "b1_t07": {
        **_all_span("src/d53.rs", 1, 1),
        S3_ADAPTER_ID: ("src/e67.rs", 1, 1),
        S5_ADAPTER_ID: ("src/e67.rs", 1, 1),
    },
    "b1_t08": {
        **_all_span("src/d59.ts", 1, 1),
        S3_ADAPTER_ID: ("src/e71.ts", 1, 1),
        S5_ADAPTER_ID: ("src/e71.ts", 1, 1),
    },
    "b1_t11": _all_span("src/h03.rs", 1, 1),
    "b1_t12": _all_span("src/h05.ts", 1, 1),
}

_TIE_CELLS = {
    ("src/j11.rs", 1, 1),
    ("src/k23.rs", 1, 1),
}

_SUPPORT_EXPECTATIONS = {
    "b1_t11": (
        ("src/z97.rs", 1, 1),
        ("src/h03.rs", 1, 1),
    ),
    "b1_t12": (
        ("src/z99.ts", 1, 1),
        ("src/h05.ts", 1, 1),
    ),
}


@dataclass(frozen=True)
class B1TaskOracle:
    task_slug: str
    oracle_kind: str
    primary_spans: dict[str, tuple[str, int, int]] = field(default_factory=dict)
    tie_cells: frozenset[tuple[str, int, int]] = frozenset()
    support_cell: tuple[str, int, int] | None = None
    support_target: tuple[str, int, int] | None = None

    def _support_records(self) -> tuple[OracleSupportRecord, ...]:
        support: tuple[OracleSupportRecord, ...] = ()
        if self.support_cell is not None and self.support_target is not None:
            sp, ss, se = self.support_cell
            tp, ts, te = self.support_target
            support = (OracleSupportRecord(
                support_path=sp,
                support_start_line=ss,
                support_end_line=se,
                relation_kind="import",
                target_path=tp,
                target_start_line=ts,
                target_end_line=te,
            ),)
        return support

    def to_task_oracles(self) -> tuple[TaskOracle, ...]:
        """Project adapter-specific B1 spans into valid Phase A oracles."""
        support = self._support_records()
        if self.oracle_kind == "deterministic":
            unique_spans = sorted(set(self.primary_spans.values()))
            return tuple(
                TaskOracle(
                    task_slug=self.task_slug,
                    oracle_kind="deterministic",
                    acceptable_target_spans=(span,),
                    expected_support_records=support,
                    must_not_primary_paths=(),
                    scorer_notes="B1 adapter-specific mechanics expectation",
                ).validate()
                for span in unique_spans
            )
        return (TaskOracle(
            task_slug=self.task_slug,
            oracle_kind=self.oracle_kind,
            acceptable_target_spans=tuple(sorted(self.tie_cells)),
            expected_support_records=support,
            must_not_primary_paths=(),
            scorer_notes="B1 synthetic mechanics expectation",
        ).validate(),)

    def validate(self) -> "B1TaskOracle":
        if self.oracle_kind not in {"deterministic", "multi_target", "abstain"}:
            raise ValueError(f"unknown B1 oracle kind {self.oracle_kind!r}")
        if self.oracle_kind == "deterministic":
            if set(self.primary_spans) != set(_ALL) or self.tie_cells:
                raise ValueError("deterministic B1 oracle must bind every adapter")
        elif self.oracle_kind == "multi_target":
            if self.primary_spans or len(self.tie_cells) != 2:
                raise ValueError("multi-target B1 oracle must contain exactly two tie cells")
            if len({path for path, _, _ in self.tie_cells}) != 2:
                raise ValueError("B1 tie cells must be cross-path")
        elif self.primary_spans or self.tie_cells:
            raise ValueError("abstain B1 oracle must not contain target spans")
        if (self.support_cell is None) != (self.support_target is None):
            raise ValueError("B1 support cell/target must be both present or absent")
        for path, start, end in (
                list(self.primary_spans.values()) + list(self.tie_cells)):
            if not path or start < 1 or end < start:
                raise ValueError("invalid B1 oracle span")
        if not self.to_task_oracles():
            raise ValueError("B1 oracle produced no Phase A validation projections")
        return self


B1_ORACLES: dict[str, B1TaskOracle] = {}
for _task in B1_ALL_TASKS:
    if _task.task_slug == "b1_t09":
        _oracle = B1TaskOracle(
            task_slug=_task.task_slug,
            oracle_kind="multi_target",
            tie_cells=frozenset(_TIE_CELLS),
        )
    elif _task.task_slug == "b1_t10":
        _oracle = B1TaskOracle(
            task_slug=_task.task_slug,
            oracle_kind="abstain",
        )
    else:
        support = _SUPPORT_EXPECTATIONS.get(_task.task_slug)
        _oracle = B1TaskOracle(
            task_slug=_task.task_slug,
            oracle_kind="deterministic",
            primary_spans=dict(_PRIMARY_SPANS[_task.task_slug]),
            support_cell=support[0] if support else None,
            support_target=support[1] if support else None,
        )
    _oracle.validate()
    B1_ORACLES[_task.task_slug] = _oracle


@dataclass
class B1ScoreResult:
    mechanics_pass: bool = False
    canary: str = ""
    assertion_failures: list[str] = field(default_factory=list)
    assertion_count: int = 0
    assertion_passed: int = 0


def _identifier_predicate(query: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", query))


def _capture_pack(capture: Any) -> ContextPack:
    output = capture.output
    if output is None or not isinstance(output.pack, ContextPack):
        raise AssertionError("missing same-execution context pack")
    return output.pack


def _capture_cells(capture: Any) -> list[tuple[str, int, int]]:
    output = capture.output
    if output is None:
        return []
    return [candidate.normalized_cell() for candidate in output.validated_candidates]


def _receipt_map(parent_receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    receipts = parent_receipt.get("component_receipts")
    if not isinstance(receipts, list):
        raise AssertionError("parent receipt component list missing")
    result: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("component"), str):
            raise AssertionError("malformed parent component receipt")
        component = receipt["component"]
        if component in result:
            raise AssertionError("duplicate parent component receipt")
        result[component] = receipt
    return result


def _assert_parent_receipt_binding(
    record: Any,
    capture: Any,
    parent_receipt: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    output = capture.output
    expected_keys = {
        "schema_version", "request_id", "adapter_id", "task_slug",
        "operation", "cache_state", "adapter_repetition",
        "record_fingerprint", "canonical_result_hash",
        "canonical_pack_hash", "semantic_hash", "component_receipts",
        "rrf_receipt", "provider_network_call_count", "trace_written",
        "sentinel_expected", "sentinel_passed", "index_inventory_digest",
        "prepare_transcript_sha256", "query_transcript_sha256",
        "capture_candidate_count", "capture_target_count",
        "capture_support_count",
    }
    if set(parent_receipt) != expected_keys:
        failures.append("parent receipt closed key set mismatch")
    if record.interaction_mode == "one_shot":
        request_prefix = "b1_req"
    elif record.operation == "context":
        request_prefix = "b1_ctx"
    else:
        request_prefix = "b1_sup"
    if record.interaction_mode == "two_step" \
            and record.operation == "context":
        expected_request_id = (
            f"{request_prefix}_{record.run_cell_id}_"
            f"rep{record.adapter_repetition}_{record.cache_state}")
    else:
        expected_request_id = (
            f"{request_prefix}_{record.run_cell_id}_{record.adapter_id}_"
            f"rep{record.adapter_repetition}_{record.cache_state}")
    expected_fields = {
        "schema_version": B1_PARENT_RECEIPT_SCHEMA_VERSION,
        "request_id": expected_request_id,
        "adapter_id": record.adapter_id,
        "task_slug": record.run_cell_id,
        "operation": record.operation,
        "cache_state": record.cache_state,
        "adapter_repetition": record.adapter_repetition,
        "record_fingerprint": record.fingerprint,
        "canonical_result_hash": record.canonical_result_hash,
        "canonical_pack_hash": record.canonical_pack_hash,
    }
    for key, expected in expected_fields.items():
        if parent_receipt.get(key) != expected:
            failures.append(f"parent receipt {key} binding mismatch")
    if output is None:
        return failures + ["parent receipt has no same-execution output"]
    if parent_receipt.get("canonical_result_hash") != output.canonical_result_hash:
        failures.append("parent receipt result hash does not bind capture")
    if parent_receipt.get("canonical_pack_hash") != output.canonical_pack_hash:
        failures.append("parent receipt pack hash does not bind capture")
    expected_counts = {
        "capture_candidate_count": len(output.validated_candidates),
        "capture_target_count": len(output.pack.targets),
        "capture_support_count": len(output.pack.support),
    }
    for key, expected in expected_counts.items():
        if parent_receipt.get(key) != expected:
            failures.append(f"parent receipt {key} mismatch")
    for key, pattern in (
        ("semantic_hash", r"b1sem_[0-9a-f]{64}"),
        ("index_inventory_digest", r"idx_[0-9a-f]{64}"),
        ("query_transcript_sha256", r"[0-9a-f]{64}"),
    ):
        value = parent_receipt.get(key)
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            failures.append(f"parent receipt {key} format mismatch")
    prepare_digest = parent_receipt.get("prepare_transcript_sha256")
    if record.cache_state == "cold":
        if not isinstance(prepare_digest, str) or not re.fullmatch(
                r"[0-9a-f]{64}", prepare_digest):
            failures.append("cold parent receipt lacks prepare transcript digest")
    elif prepare_digest is not None:
        failures.append("warm parent receipt unexpectedly has prepare transcript")
    expected_sentinels = len(parent_receipt.get("component_receipts", ())) + 1
    if parent_receipt.get("trace_written") is True:
        expected_sentinels += 1
    if parent_receipt.get("sentinel_expected") != expected_sentinels \
            or parent_receipt.get("sentinel_passed") != expected_sentinels:
        failures.append("parent receipt sentinel counts are not measured consistently")
    if parent_receipt.get("provider_network_call_count") != 0:
        failures.append("parent receipt reports provider/network activity")
    rrf_receipt = parent_receipt.get("rrf_receipt")
    if parent_receipt.get("trace_written") is True:
        expected_rrf = {
            "marker": B1_RRF_MARKER,
            "version": B1_RRF_VERSION,
            "k": B1_RRF_K,
            "tie_order": B1_RRF_TIE_ORDER_WIRE,
            "rank_tie_policy": B1_RRF_RANK_TIE_POLICY,
            "channel_weights": B1_RRF_CHANNEL_WEIGHTS,
            "input_normalization": B1_RRF_INPUT_NORMALIZATION,
        }
        if not isinstance(rrf_receipt, dict) \
                or set(rrf_receipt) != set(expected_rrf) | {"input_rewrites"}:
            failures.append("parent receipt RRF sentinel shape mismatch")
        else:
            for key, expected in expected_rrf.items():
                if rrf_receipt.get(key) != expected:
                    failures.append(f"parent receipt RRF {key} mismatch")
            rewrites = rrf_receipt.get("input_rewrites")
            if not isinstance(rewrites, int) or isinstance(rewrites, bool) \
                    or rewrites < 0:
                failures.append("parent receipt RRF input_rewrites invalid")
    elif rrf_receipt is not None:
        failures.append("local support skip unexpectedly carries RRF receipt")
    return failures


def _expected_context_receipts(
    task: B1Task,
    adapter_id: str,
) -> dict[str, tuple[str, int]]:
    expected: dict[str, tuple[str, int]] = {}
    for component in adapter_context_components(adapter_id):
        if component == "symbol" and not _identifier_predicate(task.query):
            expected[component] = ("legitimate_skip", 0)
        elif component == "graph" \
                and task.task_family not in B1_GRAPH_ELIGIBLE_TASK_FAMILIES:
            expected[component] = ("legitimate_skip", 0)
        elif task.task_slug == "b1_t03" and component == "bm25":
            expected[component] = ("executed", 0)
        elif task.task_slug == "b1_t10":
            expected[component] = ("executed", 0)
        else:
            expected[component] = ("executed", 1)
    return expected


def _canonical_channel(component: str) -> str:
    return {
        "bm25": "bm25",
        "literal": "text",
        "symbol": "symbol",
        "graph": "graph",
        "support": "support",
    }[component]


def _assert_component_receipts(
    task: B1Task,
    adapter_id: str,
    operation: str,
    capture: Any,
    parent_receipt: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    actual = _receipt_map(parent_receipt)
    if operation == "context":
        expected = _expected_context_receipts(task, adapter_id)
    elif adapter_supports_support(adapter_id):
        expected = {"support": ("executed", 1)}
    else:
        expected = {"support": ("legitimate_skip", 0)}
    if set(actual) != set(expected):
        failures.append(
            f"component set {sorted(actual)} != {sorted(expected)}")
        return failures
    for component, (status, minimum_count) in expected.items():
        receipt = actual[component]
        if receipt.get("status") != status:
            failures.append(
                f"{component} status {receipt.get('status')!r} != {status!r}")
        count = receipt.get("evidence_count")
        if not isinstance(count, int) or count < minimum_count:
            failures.append(
                f"{component} evidence_count {count!r} < {minimum_count}")
        if status == "legitimate_skip" and count != 0:
            failures.append(f"{component} legitimate skip has nonzero evidence")
    output = capture.output
    candidates = () if output is None else output.validated_candidates
    observed_channels = {
        channel for candidate in candidates for channel in candidate.channels
    }
    allowed = (
        _OUTPUT_CHANNELS[adapter_id]
        if operation == "context" else frozenset({"support"}))
    if not observed_channels <= allowed:
        failures.append(
            f"candidate channels {sorted(observed_channels)} exceed {sorted(allowed)}")
    for component, (status, minimum_count) in expected.items():
        channel = _canonical_channel(component)
        if status == "executed" and minimum_count > 0 and channel not in observed_channels:
            failures.append(f"executed {component} sentinel channel {channel!r} absent")
        if status == "legitimate_skip" and channel in observed_channels:
            failures.append(f"skipped {component} falsely claimed channel {channel!r}")
    return failures


def _assert_context_cell(
    task: B1Task,
    oracle: B1TaskOracle,
    adapter_id: str,
    record: Any,
    capture: Any,
    parent_receipt: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if record.status != "accepted" or record.result_status != "ok":
        return ["context record is not accepted/ok"]
    pack = _capture_pack(capture)
    failures.extend(_assert_parent_receipt_binding(
        record, capture, parent_receipt))
    failures.extend(_assert_component_receipts(
        task, adapter_id, "context", capture, parent_receipt))
    if pack.support:
        failures.append("context pack contains support")
    cells = _capture_cells(capture)
    if task.task_slug == "b1_t09":
        if pack.pack_status != "uncertain":
            failures.append(f"tie pack_status {pack.pack_status!r} != 'uncertain'")
        if not _TIE_CELLS <= set(cells):
            failures.append("tie candidate cells are incomplete")
        candidates = list(capture.output.validated_candidates)
        tied = [candidate for candidate in candidates
                if candidate.normalized_cell() in _TIE_CELLS]
        if len(tied) != 2 or tied[0].score != tied[1].score:
            failures.append("cross-path top tie is not exact")
        if len(candidates) < 2 or {
                candidate.normalized_cell() for candidate in candidates[:2]
        } != _TIE_CELLS:
            failures.append("cross-path tie cells are not the top two candidates")
        if len(pack.targets) != 1 or (
            pack.targets[0].path,
            pack.targets[0].start_line,
            pack.targets[0].end_line,
        ) not in _TIE_CELLS:
            failures.append("uncertain tie does not bind one tied primary")
    elif task.task_slug == "b1_t10" \
            or (task.task_slug == "b1_t03" and adapter_id == S0_ADAPTER_ID):
        if pack.pack_status != "no_evidence":
            failures.append(
                f"expected-empty pack_status {pack.pack_status!r} "
                "!= 'no_evidence'")
        if cells or pack.targets or pack.support:
            failures.append(
                "expected-empty cell contains evidence/targets/support")
    else:
        if pack.pack_status != "ready" or not pack.targets:
            failures.append("deterministic context is not ready with a target")
        else:
            primary = pack.targets[0]
            actual = (primary.path, primary.start_line, primary.end_line)
            expected = oracle.primary_spans[adapter_id]
            if actual != expected:
                failures.append(f"primary span {actual!r} != {expected!r}")
        if task.interaction_mode == "two_step" and len(pack.targets) != 1:
            failures.append("two-step context must bind exactly one primary target")
        if task.interaction_mode == "one_shot" and not 1 <= len(pack.targets) <= 4:
            failures.append("one-shot context target count is outside 1..=4")
    return failures


def _assert_support_cell(
    task: B1Task,
    oracle: B1TaskOracle,
    adapter_id: str,
    record: Any,
    capture: Any,
    parent_receipt: dict[str, Any],
    context_capture: Any,
) -> list[str]:
    failures: list[str] = []
    if record.status != "accepted" or record.result_status != "ok":
        return ["support record is not accepted/ok"]
    pack = _capture_pack(capture)
    failures.extend(_assert_parent_receipt_binding(
        record, capture, parent_receipt))
    failures.extend(_assert_component_receipts(
        task, adapter_id, "support", capture, parent_receipt))
    context_pack = _capture_pack(context_capture)
    expected_parent_id = stable_target_id(context_pack.targets[0])
    if adapter_id not in _SUPPORT:
        if pack.pack_status != "no_evidence" or pack.targets or pack.support \
                or _capture_cells(capture):
            failures.append("S0-S3 support must be an empty legitimate skip")
        if parent_receipt.get("trace_written") is not False:
            failures.append("local support skip unexpectedly claims a Rust trace")
        return failures
    if pack.pack_status != "ready" or pack.targets:
        failures.append("S4/S5 support must be ready with no primary targets")
    expected_support = oracle.support_cell
    if expected_support is None or oracle.support_target is None:
        failures.append("support oracle is incomplete")
        return failures
    support_cells = {
        (support.path, support.start_line, support.end_line)
        for support in pack.support
    }
    if support_cells != {expected_support}:
        failures.append(
            f"support cells {sorted(support_cells)} != {[expected_support]}")
    if len(pack.support) != 1:
        failures.append("S4/S5 support must contain exactly one import edge")
    for support in pack.support:
        if support.relation_kind != "import":
            failures.append("support relation is not canonical import")
        if support.parent_target_id != expected_parent_id:
            failures.append("support parent_target_id does not bind context primary")
    if parent_receipt.get("trace_written") is not True:
        failures.append("production support request lacks checked trace evidence")
    return failures


def score_b1(
    records: list[Any],
    captures: list[Any],
    parent_receipts: list[dict[str, Any]],
    *,
    canary: str,
    public_aggregate_text: str,
) -> B1ScoreResult:
    result = B1ScoreResult(canary=canary)
    if not re.fullmatch(r"canary_[0-9a-f]{32}", canary):
        result.assertion_failures.append("private canary format invalid")
    if canary in public_aggregate_text:
        result.assertion_failures.append("private canary present in public aggregate")
    result.assertion_count += 2
    result.assertion_passed += 2 - len(result.assertion_failures)

    if not (len(records) == len(captures) == len(parent_receipts) == B1_TOTAL_RECORDS):
        result.assertion_failures.append(
            f"score inputs are not exact 504-tuples: "
            f"{len(records)}/{len(captures)}/{len(parent_receipts)}")
        result.assertion_count += 1
        return result

    record_lookup: dict[tuple[str, str, str, int, str], tuple[Any, Any]] = {}
    for record, capture in zip(records, captures):
        key = (
            record.adapter_id, record.run_cell_id, record.operation,
            record.adapter_repetition, record.cache_state)
        if key in record_lookup:
            result.assertion_failures.append(f"duplicate score cell {key!r}")
        record_lookup[key] = (record, capture)
    receipt_lookup: dict[tuple[str, str, str, int, str], dict[str, Any]] = {}
    for receipt in parent_receipts:
        key = (
            receipt.get("adapter_id"), receipt.get("task_slug"),
            receipt.get("operation"), receipt.get("adapter_repetition"),
            receipt.get("cache_state"))
        if key in receipt_lookup:
            result.assertion_failures.append(f"duplicate parent receipt {key!r}")
        receipt_lookup[key] = receipt

    for task in B1_ALL_TASKS:
        oracle = B1_ORACLES[task.task_slug]
        for adapter_id in B1_ADAPTER_IDS:
            for repetition in B1_REPETITIONS:
                for cache in B1_CACHE_STATES:
                    context_key = (
                        adapter_id, task.task_slug, "context", repetition, cache)
                    entry = record_lookup.get(context_key)
                    parent_receipt = receipt_lookup.get(context_key)
                    result.assertion_count += 1
                    if entry is None or parent_receipt is None:
                        result.assertion_failures.append(
                            f"missing context score cell {context_key!r}")
                    else:
                        failures = _assert_context_cell(
                            task, oracle, adapter_id, entry[0], entry[1],
                            parent_receipt)
                        if failures:
                            result.assertion_failures.extend(
                                f"{context_key!r}: {failure}" for failure in failures)
                        else:
                            result.assertion_passed += 1
                    if task.interaction_mode != "two_step":
                        continue
                    support_key = (
                        adapter_id, task.task_slug, "support", repetition, cache)
                    support_entry = record_lookup.get(support_key)
                    support_receipt = receipt_lookup.get(support_key)
                    result.assertion_count += 1
                    if entry is None or support_entry is None or support_receipt is None:
                        result.assertion_failures.append(
                            f"missing support score cell {support_key!r}")
                    else:
                        failures = _assert_support_cell(
                            task, oracle, adapter_id, support_entry[0],
                            support_entry[1], support_receipt, entry[1])
                        if failures:
                            result.assertion_failures.extend(
                                f"{support_key!r}: {failure}" for failure in failures)
                        else:
                            result.assertion_passed += 1

    result.mechanics_pass = not result.assertion_failures
    return result


def write_private_scorer_output(
    runs_dir: Path,
    canary: str,
    score: B1ScoreResult,
) -> None:
    out = {
        "scorer_version": SCORER_VERSION,
        "oracle_schema_version": ORACLE_SCHEMA_VERSION,
        "canary": canary,
        "mechanics_pass": score.mechanics_pass,
        "assertion_count": score.assertion_count,
        "assertion_passed": score.assertion_passed,
        "assertion_failures": score.assertion_failures[:100],
    }
    path = Path(runs_dir) / "private" / "b1_private_scorer.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "SCORER_VERSION", "B1TaskOracle", "B1_ORACLES",
    "assert_b1_run_phase_isolation", "score_b1", "B1ScoreResult",
    "write_private_scorer_output",
]
