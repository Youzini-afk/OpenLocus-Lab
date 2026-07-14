#!/usr/bin/env python3
"""Scorer-only B2 oracle schema and private manifest validation.

The RUN phase must not import this module.  It carries target, negative, and
support labels and is loaded only by the authoring/scoring phases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from product_bakeoff_b2_protocol import (
    B2_ANSWERABLE_TASK_COUNT,
    B2_AMBIGUOUS_TASK_COUNT,
    B2_NO_ANSWER_TASK_COUNT,
    B2_TASK_COUNT,
    B2_TWO_STEP_TASK_COUNT,
    b2_spec_digest,
    build_task_slots,
)
from product_bakeoff_b2_corpus import (
    B2CorpusError,
    B2PublicTask,
    prefixed_digest,
    validate_relative_path,
)


B2_ORACLE_SCHEMA = "product_bakeoff_b2_private_oracle_manifest.v1"
B2_ORACLE_VERSION = "product_bakeoff_b2_oracle.v1"
RELATION_KINDS = frozenset({"import"})


class B2OracleError(ValueError):
    """Fail-closed scorer-only oracle error."""


@dataclass(frozen=True)
class B2Span:
    path: str
    start_line: int
    end_line: int

    def validate(self) -> "B2Span":
        try:
            validate_relative_path(self.path)
        except B2CorpusError as exc:
            raise B2OracleError(str(exc)) from exc
        for name, value in (("start_line", self.start_line), ("end_line", self.end_line)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise B2OracleError(f"{name} must be a positive integer")
        if self.start_line > self.end_line:
            raise B2OracleError("span start_line exceeds end_line")
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "B2Span":
        if set(raw) != {"path", "start_line", "end_line"}:
            raise B2OracleError("span has non-closed shape")
        return cls(
            path=raw["path"], start_line=raw["start_line"], end_line=raw["end_line"]
        ).validate()

    def atoms(self) -> frozenset[tuple[str, int]]:
        return frozenset(
            (self.path, line) for line in range(self.start_line, self.end_line + 1)
        )


@dataclass(frozen=True)
class B2SupportRelation:
    support: B2Span
    relation_kind: str
    target: B2Span

    def validate(self) -> "B2SupportRelation":
        self.support.validate()
        self.target.validate()
        if self.relation_kind not in RELATION_KINDS:
            raise B2OracleError("unsupported B2 relation kind")
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "support": self.support.to_dict(),
            "relation_kind": self.relation_kind,
            "target": self.target.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "B2SupportRelation":
        if set(raw) != {"support", "relation_kind", "target"}:
            raise B2OracleError("support relation has non-closed shape")
        if not isinstance(raw["support"], dict) or not isinstance(raw["target"], dict):
            raise B2OracleError("support relation spans must be objects")
        return cls(
            support=B2Span.from_dict(raw["support"]),
            relation_kind=raw["relation_kind"],
            target=B2Span.from_dict(raw["target"]),
        ).validate()


@dataclass(frozen=True)
class B2TaskOracle:
    slot_id: str
    task_slug: str
    oracle_kind: str
    positive_spans: tuple[B2Span, ...]
    negative_spans: tuple[B2Span, ...]
    support_relations: tuple[B2SupportRelation, ...] = ()

    def validate(self, *, task: B2PublicTask | None = None) -> "B2TaskOracle":
        slots = {slot.slot_id: slot for slot in build_task_slots()}
        slot = slots.get(self.slot_id)
        if slot is None:
            raise B2OracleError("unknown oracle slot")
        if self.oracle_kind != slot.oracle_kind:
            raise B2OracleError("oracle kind does not match frozen slot")
        if task is not None and (
            task.slot_id != self.slot_id or task.task_slug != self.task_slug
        ):
            raise B2OracleError("oracle/task identity binding mismatch")
        if not isinstance(self.task_slug, str) or not self.task_slug:
            raise B2OracleError("oracle task_slug missing")
        for span in self.positive_spans:
            span.validate()
        for span in self.negative_spans:
            span.validate()
        for relation in self.support_relations:
            relation.validate()
        if len(set(self.positive_spans)) != len(self.positive_spans):
            raise B2OracleError("positive spans must be pairwise distinct")
        if len(set(self.negative_spans)) != len(self.negative_spans):
            raise B2OracleError("negative spans must be pairwise distinct")
        if len(set(self.support_relations)) != len(self.support_relations):
            raise B2OracleError("support relations must be pairwise distinct")
        if len(self.negative_spans) < 2:
            raise B2OracleError("every B2 task requires at least two negative spans")
        positive_atoms = set().union(*(span.atoms() for span in self.positive_spans)) \
            if self.positive_spans else set()
        negative_atoms = set().union(*(span.atoms() for span in self.negative_spans))
        if positive_atoms & negative_atoms:
            raise B2OracleError("positive and negative spans overlap")

        if self.oracle_kind == "deterministic":
            if len(self.positive_spans) != 1:
                raise B2OracleError("deterministic oracle requires exactly one positive span")
        elif self.oracle_kind == "multi_target":
            if len(self.positive_spans) < 2:
                raise B2OracleError("multi-target oracle requires at least two positive spans")
        elif self.oracle_kind == "abstain":
            if self.positive_spans:
                raise B2OracleError("abstain oracle must not contain positive spans")
        else:
            raise B2OracleError("unknown oracle kind")

        if slot.interaction_mode == "two_step":
            if len(self.support_relations) < 1:
                raise B2OracleError("two-step oracle requires support relation")
            positives = set(self.positive_spans)
            for relation in self.support_relations:
                if relation.target not in positives:
                    raise B2OracleError("support target must exactly match a positive span")
        elif self.support_relations:
            raise B2OracleError("one-shot oracle must not contain support relations")
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "task_slug": self.task_slug,
            "oracle_kind": self.oracle_kind,
            "positive_spans": [span.to_dict() for span in self.positive_spans],
            "negative_spans": [span.to_dict() for span in self.negative_spans],
            "support_relations": [relation.to_dict() for relation in self.support_relations],
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "B2TaskOracle":
        if set(raw) != {
            "slot_id", "task_slug", "oracle_kind", "positive_spans",
            "negative_spans", "support_relations",
        }:
            raise B2OracleError("oracle task row has non-closed shape")
        for key in ("positive_spans", "negative_spans", "support_relations"):
            if not isinstance(raw[key], list):
                raise B2OracleError(f"{key} must be a list")
        return cls(
            slot_id=raw["slot_id"],
            task_slug=raw["task_slug"],
            oracle_kind=raw["oracle_kind"],
            positive_spans=tuple(B2Span.from_dict(item) for item in raw["positive_spans"]),
            negative_spans=tuple(B2Span.from_dict(item) for item in raw["negative_spans"]),
            support_relations=tuple(
                B2SupportRelation.from_dict(item) for item in raw["support_relations"]
            ),
        )


def oracle_manifest_digest(manifest: Mapping[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("oracle_manifest_digest", None)
    return prefixed_digest("b2oracles_", payload)


def _repo_file_rows(repo_lock: Mapping[str, Any]) -> dict[str, dict[str, Mapping[str, Any]]]:
    result: dict[str, dict[str, Mapping[str, Any]]] = {}
    for repo in repo_lock["repos"]:
        result[repo["repo_slot"]] = {
            row["path"]: row for row in repo["visible"]["files"]
        }
    return result


def validate_oracle_manifest(
    manifest: Any,
    *,
    tasks: Sequence[B2PublicTask],
    repo_lock: Mapping[str, Any],
    task_manifest_digest: str,
) -> tuple[B2TaskOracle, ...]:
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "oracle_version", "protocol_spec_digest",
        "repo_lock_digest", "task_manifest_digest", "oracle_manifest_digest",
        "tasks",
    }:
        raise B2OracleError("oracle manifest has non-closed shape")
    if manifest["schema_version"] != B2_ORACLE_SCHEMA:
        raise B2OracleError("oracle manifest schema mismatch")
    if manifest["oracle_version"] != B2_ORACLE_VERSION:
        raise B2OracleError("oracle version mismatch")
    if manifest["protocol_spec_digest"] != b2_spec_digest():
        raise B2OracleError("oracle protocol digest drift")
    if manifest["repo_lock_digest"] != repo_lock["repo_lock_digest"]:
        raise B2OracleError("oracle/repo lock digest mismatch")
    if manifest["task_manifest_digest"] != task_manifest_digest:
        raise B2OracleError("oracle/task manifest digest mismatch")
    if not isinstance(manifest["tasks"], list) or len(manifest["tasks"]) != B2_TASK_COUNT:
        raise B2OracleError(f"oracle manifest must contain {B2_TASK_COUNT} rows")
    task_by_slot = {task.slot_id: task for task in tasks}
    rows = tuple(B2TaskOracle.from_dict(raw) for raw in manifest["tasks"])
    if len({row.slot_id for row in rows}) != len(rows):
        raise B2OracleError("duplicate oracle slot")
    if {row.slot_id for row in rows} != set(task_by_slot):
        raise B2OracleError("oracle slot coverage differs from task manifest")
    file_rows = _repo_file_rows(repo_lock)
    for row in rows:
        task = task_by_slot[row.slot_id]
        row.validate(task=task)
        visible = file_rows[task.repo_slot]
        spans = [*row.positive_spans, *row.negative_spans]
        for relation in row.support_relations:
            spans.extend((relation.support, relation.target))
        for span in spans:
            file_row = visible.get(span.path)
            if file_row is None:
                raise B2OracleError(f"oracle span path {span.path!r} is not visible")
            if span.end_line > file_row["line_count"]:
                raise B2OracleError(f"oracle span exceeds current source: {span.path!r}")

    kind_counts = {
        kind: sum(row.oracle_kind == kind for row in rows)
        for kind in ("deterministic", "multi_target", "abstain")
    }
    if kind_counts != {
        "deterministic": B2_ANSWERABLE_TASK_COUNT - B2_AMBIGUOUS_TASK_COUNT,
        "multi_target": B2_AMBIGUOUS_TASK_COUNT,
        "abstain": B2_NO_ANSWER_TASK_COUNT,
    }:
        raise B2OracleError("oracle kind margins drifted")
    if sum(bool(row.support_relations) for row in rows) != B2_TWO_STEP_TASK_COUNT:
        raise B2OracleError("support oracle margin drifted")
    if manifest["oracle_manifest_digest"] != oracle_manifest_digest(manifest):
        raise B2OracleError("oracle manifest digest mismatch")
    return rows


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    task = B2PublicTask(
        slot_id="b2_slot_01", task_slug="b2_t01_0123456789ab",
        repo_slot="b2_repo_rust_small", language="rust", size_band="small",
        role="direct", task_family="symbol_lookup", interaction_mode="one_shot",
        query="StableSymbol",
    ).validate()
    oracle = B2TaskOracle(
        slot_id=task.slot_id,
        task_slug=task.task_slug,
        oracle_kind="deterministic",
        positive_spans=(B2Span("src/a.rs", 3, 3),),
        negative_spans=(B2Span("src/b.rs", 4, 4), B2Span("src/c.rs", 5, 5)),
    ).validate(task=task)
    checks.append(("deterministic_valid", oracle.oracle_kind == "deterministic"))
    checks.append(("line_atoms", len(oracle.positive_spans[0].atoms()) == 1))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    task = B2PublicTask(
        slot_id="b2_slot_01", task_slug="b2_t01_0123456789ab",
        repo_slot="b2_repo_rust_small", language="rust", size_band="small",
        role="direct", task_family="symbol_lookup", interaction_mode="one_shot",
        query="StableSymbol",
    ).validate()
    try:
        B2TaskOracle(
            slot_id=task.slot_id,
            task_slug=task.task_slug,
            oracle_kind="deterministic",
            positive_spans=(B2Span("src/a.rs", 3, 3),),
            negative_spans=(B2Span("src/a.rs", 3, 3), B2Span("src/c.rs", 5, 5)),
        ).validate(task=task)
        overlap_rejected = False
    except B2OracleError:
        overlap_rejected = True
    checks.append(("positive_negative_overlap_rejected", overlap_rejected))
    try:
        B2TaskOracle(
            slot_id=task.slot_id,
            task_slug=task.task_slug,
            oracle_kind="deterministic",
            positive_spans=(),
            negative_spans=(B2Span("src/b.rs", 4, 4), B2Span("src/c.rs", 5, 5)),
        ).validate(task=task)
        cardinality_rejected = False
    except B2OracleError:
        cardinality_rejected = True
    checks.append(("deterministic_cardinality_rejected", cardinality_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B2OracleError", "B2Span", "B2SupportRelation", "B2TaskOracle",
    "B2_ORACLE_SCHEMA", "B2_ORACLE_VERSION", "RELATION_KINDS",
    "oracle_manifest_digest", "validate_oracle_manifest",
    "run_self_test", "run_fault_test",
]
