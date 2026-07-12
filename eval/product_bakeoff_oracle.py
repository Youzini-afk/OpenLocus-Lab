#!/usr/bin/env python3
"""Product Stack Bakeoff Phase A — scorer-only TaskOracle envelope (v12).

This module is the SCORER-ONLY side of the public-task / oracle separation.
``TaskOracle`` carries gold/target/support labels that the scorer uses to
evaluate validated run records AFTER the run phase. It must NEVER be imported
by the contract surface (``product_bakeoff_contract.py``) or by the
conformance runner (``product_bakeoff_conformance.py``) during normal adapter
execution.

Binding contract (v4 — closed oracle envelope):

* ``TaskOracle`` is a frozen dataclass carrying ONLY scorer-relevant labels:
  ``acceptable_target_spans`` (the ONE canonical target representation:
  multiple distinct (path, start, end) spans), ``expected_support_records``
  (associated support records containing support span + relation + target
  reference rather than parallel ambiguous lists), ``must_not_primary_paths``
  (negative / must-not-primary labels with safe relative paths), and
  ``oracle_kind``. It carries no candidate/evidence/pack fields and no
  gold-convenience aliases (gold_target_path/gold_target_range were removed;
  the canonical representation is acceptable_target_spans alone).
  Outcome/patch schemas remain deferred.
* Oracle kinds enforce strict deterministic-oracle requirements:
  ``deterministic`` requires EXACTLY 1 acceptable_target_span;
  ``multi_target`` requires >= 2; ``abstain``/``stress`` require 0.
* ``OracleSupportRecord`` is an associated support record: support_path +
  support range + relation_kind + target_path + target range. This replaces
  the v2 parallel lists with an unambiguous associated representation.
* Internal consistency (v4 closure):
  - acceptable_target_spans are pairwise distinct (no duplicate (path, s, e));
  - must_not_primary_paths are pairwise distinct (duplicate-negative rejected);
  - positive/negative disjointness: every path appearing in
    acceptable_target_spans or as a support target_path must NOT appear in
    must_not_primary_paths;
  - every OracleSupportRecord's target (target_path + target range) is
    EXACTLY a member of acceptable_target_spans when acceptable spans are
    non-empty (abstain/stress carry no spans and no support records);
  - support records are pairwise distinct (no duplicate
    (support_path, support range, relation, target_path, target range));
  - strict kind cardinality per oracle_kind (deterministic exactly 1,
    multi_target >= 2, abstain/stress 0 spans AND 0 support records AND
    no must_not_primary_paths for abstain/stress).
* ``assert_run_phase_not_importing_oracle()`` is a guard the conformance
  self-test calls to prove the run phase modules do not import this module.
* The oracle envelope performs NO source reads, NO materialization, and NO
  adapter calls. It is read-only scorer metadata.

Threat model (honest): this separation protects against ACCIDENTAL contract
leakage of scorer labels into adapter-visible request/result/pack objects. It
does NOT prevent a hostile executable from reading this file from disk; the
conformance surface is not a host sandbox.

Phase A makes no product/algorithm/default/winner claim. The oracle is
included only to freeze the public-task / scorer-only separation; no scoring
is performed in Phase A.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping

ORACLE_SCHEMA_VERSION = "product_bakeoff_oracle.v12"
GENERATED_BY = "eval/product_bakeoff_oracle.py"
CLAIM_LEVEL = "scorer_only_oracle_envelope_no_run_phase_import"

# Closed oracle kinds.
#   deterministic — EXACTLY 1 acceptable target span.
#   multi_target  — >= 2 acceptable target spans (ambiguous target stratum).
#   abstain       — 0 acceptable spans (no-answer stratum).
#   stress        — 0 acceptable spans (stress bucket only).
ORACLE_KINDS: frozenset[str] = frozenset(
    {"deterministic", "multi_target", "abstain", "stress"}
)

# Oracle-local relation kinds (mirrors the contract's RELATION_KINDS but does
# NOT import the contract module to preserve scorer-only isolation).
ORACLE_RELATION_KINDS: frozenset[str] = frozenset(
    {"definition", "caller", "import", "type_dep"}
)


class OracleContractError(ValueError):
    """Raised when an oracle envelope violates its contract."""


# Path-safety for oracle label paths (safe relative POSIX paths only).
_NUL_RE = re.compile(r"\x00")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_TRAVERSAL_RE = re.compile(r"(?:^|/)\.\.(?:/|$)")


def _safe_relative_path(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise OracleContractError(f"{name} must be a non-empty str")
    if len(value) > 512:
        raise OracleContractError(f"{name} exceeds 512 chars")
    if _NUL_RE.search(value):
        raise OracleContractError(f"{name} contains NUL byte")
    if value.startswith("\\\\"):
        raise OracleContractError(f"{name} rejects UNC prefix")
    if value.startswith("/"):
        raise OracleContractError(f"{name} rejects absolute prefix")
    if _DRIVE_RE.match(value):
        raise OracleContractError(f"{name} rejects drive letter")
    if "\\" in value:
        raise OracleContractError(f"{name} must use posix separators")
    if _TRAVERSAL_RE.search(value):
        raise OracleContractError(f"{name} rejects traversal")
    if value in (".", ".."):
        raise OracleContractError(f"{name} rejects dot-only path")
    return value


def _safe_int(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise OracleContractError(f"{name} must be int")
    return value


def _safe_range(name: str, s: int, e: int) -> tuple[int, int]:
    if s < 1 or e < 1 or s > e:
        raise OracleContractError(f"{name} ({s},{e}) invalid")
    return (s, e)


@dataclass(frozen=True)
class OracleSupportRecord:
    """Associated support record: support span + relation + target reference.

    This replaces the v2 parallel lists (expected_support_paths /
    expected_support_relation_kinds / expected_support_target_links) with an
    unambiguous associated representation where each record self-containedly
    links a support span to a target span via a relation kind.
    """

    support_path: str
    support_start_line: int
    support_end_line: int
    relation_kind: str
    target_path: str
    target_start_line: int
    target_end_line: int

    def validate(self) -> "OracleSupportRecord":
        _safe_relative_path("support_path", self.support_path)
        _safe_int("support_start_line", self.support_start_line)
        _safe_int("support_end_line", self.support_end_line)
        _safe_range("support_range", self.support_start_line, self.support_end_line)
        if self.relation_kind not in ORACLE_RELATION_KINDS:
            raise OracleContractError(
                f"relation_kind {self.relation_kind!r} not in "
                f"{sorted(ORACLE_RELATION_KINDS)}"
            )
        _safe_relative_path("target_path", self.target_path)
        _safe_int("target_start_line", self.target_start_line)
        _safe_int("target_end_line", self.target_end_line)
        _safe_range("target_range", self.target_start_line, self.target_end_line)
        return self


@dataclass(frozen=True)
class TaskOracle:
    """Scorer-only oracle envelope for a single BakeoffTask.

    Carries gold target/support labels AND negative (must-not-primary) labels.
    NEVER adapter-visible; NEVER imported during the run phase. Used only by a
    future scorer phase to evaluate validated run records. Outcome/patch
    schemas remain deferred.

    The ONE canonical target representation is ``acceptable_target_spans``.
    Gold-convenience aliases (gold_target_path / gold_target_range) were
    REMOVED in v4 because no compatibility use existed; the canonical
    representation alone carries the target. Support labels use associated
    ``OracleSupportRecord`` entries (support span + relation + target
    reference), not parallel ambiguous lists.

    Internal consistency (v4 closure):
      * acceptable_target_spans are pairwise distinct;
      * must_not_primary_paths are pairwise distinct (duplicate-negative
        rejected);
      * positive/negative disjointness: a path in acceptable_target_spans (or
        a support target_path) must not appear in must_not_primary_paths;
      * every support record's (target_path, target range) is EXACTLY a member
        of acceptable_target_spans (when acceptable spans are non-empty);
      * support records are pairwise distinct;
      * strict kind cardinality per oracle_kind.
    """

    task_slug: str
    oracle_kind: str
    # Canonical target representation.
    acceptable_target_spans: tuple[tuple[str, int, int], ...] = ()
    # Associated support records.
    expected_support_records: tuple[OracleSupportRecord, ...] = ()
    # Negative / must-not-primary labels (safe relative paths).
    must_not_primary_paths: tuple[str, ...] = ()
    scorer_notes: str = ""

    def validate(
        self, visible_files: Any = None
    ) -> "TaskOracle":
        """Validate the oracle envelope.

        v9: when ``visible_files`` (an iterable of relative POSIX paths from
        the frozen snapshot) is supplied, EVERY label path — acceptable target
        span paths, support record support_path + target_path, and
        must_not_primary_paths — must belong to that frozen visible set. This
        is the scorer-side preflight that oracle labels reference only files
        that actually existed in the frozen snapshot. The oracle stays
        scorer-only: it performs NO source reads and is never imported during
        the run phase.
        """
        if not isinstance(self.task_slug, str) or not self.task_slug:
            raise OracleContractError("task_slug must be non-empty str")
        if self.oracle_kind not in ORACLE_KINDS:
            raise OracleContractError(
                f"oracle_kind {self.oracle_kind!r} not in {sorted(ORACLE_KINDS)}"
            )
        # Acceptable target spans: each is (path, start, end) with safe path.
        if not isinstance(self.acceptable_target_spans, tuple):
            raise OracleContractError("acceptable_target_spans must be a tuple")
        seen_spans: set[tuple[str, int, int]] = set()
        for span in self.acceptable_target_spans:
            if not isinstance(span, tuple) or len(span) != 3:
                raise OracleContractError(
                    "each acceptable_target_span must be a (path, start, end) tuple"
                )
            sp, ss, se = span
            _safe_relative_path("acceptable_target_span.path", sp)
            _safe_int("acceptable_target_span.start", ss)
            _safe_int("acceptable_target_span.end", se)
            _safe_range("acceptable_target_span.range", ss, se)
            if span in seen_spans:
                raise OracleContractError(
                    f"duplicate acceptable_target_span {span!r} (canonical "
                    "spans must be pairwise distinct)"
                )
            seen_spans.add(span)
        # Associated support records.
        if not isinstance(self.expected_support_records, tuple):
            raise OracleContractError("expected_support_records must be a tuple")
        seen_support: set[tuple[str, int, int, str, str, int, int]] = set()
        for rec in self.expected_support_records:
            if not isinstance(rec, OracleSupportRecord):
                raise OracleContractError(
                    "expected_support_records items must be OracleSupportRecord"
                )
            rec.validate()
            # Each support record's target (target_path + target range) must
            # be EXACTLY a member of acceptable_target_spans (when acceptable
            # spans are non-empty).
            if len(seen_spans) > 0:
                target_span = (
                    rec.target_path,
                    rec.target_start_line,
                    rec.target_end_line,
                )
                if target_span not in seen_spans:
                    raise OracleContractError(
                        f"support record target {target_span!r} not exactly "
                        "in acceptable_target_spans (every support target "
                        "must be associated with an acceptable target span)"
                    )
            # Duplicate-support rejection.
            support_key = (
                rec.support_path, rec.support_start_line, rec.support_end_line,
                rec.relation_kind,
                rec.target_path, rec.target_start_line, rec.target_end_line,
            )
            if support_key in seen_support:
                raise OracleContractError(
                    f"duplicate OracleSupportRecord {support_key!r} (support "
                    "records must be pairwise distinct)"
                )
            seen_support.add(support_key)
        # must_not_primary_paths: pairwise distinct (duplicate-negative rejected).
        if not isinstance(self.must_not_primary_paths, tuple):
            raise OracleContractError("must_not_primary_paths must be a tuple")
        seen_negative: set[str] = set()
        for p in self.must_not_primary_paths:
            _safe_relative_path("must_not_primary_path", p)
            if p in seen_negative:
                raise OracleContractError(
                    f"duplicate must_not_primary_path {p!r} (duplicate-"
                    "negative rejected)"
                )
            seen_negative.add(p)
        if not isinstance(self.scorer_notes, str):
            raise OracleContractError("scorer_notes must be str")
        if len(self.scorer_notes) > 512:
            raise OracleContractError("scorer_notes exceeds 512 chars")
        # Positive/negative disjointness: a path appearing in acceptable
        # target spans (or as a support target path) must NOT appear in
        # must_not_primary_paths.
        positive_paths: set[str] = {span[0] for span in seen_spans}
        for rec in self.expected_support_records:
            positive_paths.add(rec.target_path)
        overlap = positive_paths & seen_negative
        if overlap:
            raise OracleContractError(
                f"must_not_primary_paths overlaps positive target paths: "
                f"{sorted(overlap)} (positive/negative disjointness)"
            )
        # Strict deterministic-oracle requirements per oracle_kind.
        span_count = len(self.acceptable_target_spans)
        if self.oracle_kind == "deterministic":
            if span_count != 1:
                raise OracleContractError(
                    f"oracle_kind=deterministic requires EXACTLY 1 "
                    f"acceptable_target_span, got {span_count}"
                )
        elif self.oracle_kind == "multi_target":
            if span_count < 2:
                raise OracleContractError(
                    f"oracle_kind=multi_target requires >= 2 acceptable_target_spans, "
                    f"got {span_count}"
                )
        elif self.oracle_kind in {"abstain", "stress"}:
            if span_count > 0:
                raise OracleContractError(
                    f"oracle_kind={self.oracle_kind} must not carry acceptable "
                    f"target spans (got {span_count})"
                )
            if len(self.expected_support_records) > 0:
                raise OracleContractError(
                    f"oracle_kind={self.oracle_kind} must not carry support "
                    f"records (got {len(self.expected_support_records)})"
                )
            if len(self.must_not_primary_paths) > 0:
                raise OracleContractError(
                    f"oracle_kind={self.oracle_kind} must not carry "
                    f"must_not_primary_paths (got {len(self.must_not_primary_paths)})"
                )
        # v9: when a proven visible-file declaration set is supplied, every
        # oracle label path must belong to it. This is the scorer-side preflight
        # that oracle labels reference only files that existed in the frozen
        # snapshot. ``visible_files`` may be None (no proven set available);
        # in that case this check is skipped (internal-consistency checks
        # above still run).
        if visible_files is not None:
            vis: set[str] = set()
            for p in visible_files:
                if not isinstance(p, str) or not p:
                    raise OracleContractError(
                        "visible_files entries must be non-empty str"
                    )
                vis.add(p)
            # Acceptable target span paths.
            for span in self.acceptable_target_spans:
                if span[0] not in vis:
                    raise OracleContractError(
                        f"acceptable_target_span path {span[0]!r} not in "
                        f"frozen visible_files (oracle labels must reference "
                        f"only frozen snapshot files)"
                    )
            # Support record support_path + target_path.
            for rec in self.expected_support_records:
                if rec.support_path not in vis:
                    raise OracleContractError(
                        f"support record support_path {rec.support_path!r} "
                        f"not in frozen visible_files (oracle labels must "
                        f"reference only frozen snapshot files)"
                    )
                if rec.target_path not in vis:
                    raise OracleContractError(
                        f"support record target_path {rec.target_path!r} "
                        f"not in frozen visible_files (oracle labels must "
                        f"reference only frozen snapshot files)"
                    )
            # must_not_primary_paths.
            for p in self.must_not_primary_paths:
                if p not in vis:
                    raise OracleContractError(
                        f"must_not_primary_path {p!r} not in frozen "
                        f"visible_files (oracle labels must reference only "
                        f"frozen snapshot files)"
                    )
        return self


def assert_run_phase_not_importing_oracle(
    run_phase_modules: tuple[str, ...] = (
        "product_bakeoff_contract",
        "product_bakeoff_conformance",
    ),
) -> None:
    """Guard: prove the run-phase modules have NOT imported this oracle module.

    The conformance self-test calls this to prove the run phase does not import
    or receive oracle data/files. Raises OracleContractError if this module
    appears in the run-phase modules' loaded ``sys.modules`` entries.
    """
    loaded = set(sys.modules.keys())
    for mod_name in run_phase_modules:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        mod_file = getattr(mod, "__file__", None) or ""
        if "product_bakeoff_oracle" in mod_file:
            continue  # this is the oracle module itself, not a run-phase module
        for attr_name in dir(mod):
            if attr_name.startswith("__"):
                continue
            try:
                attr = getattr(mod, attr_name)
            except Exception:
                continue
            attr_mod = getattr(attr, "__module__", "")
            if attr_mod == "product_bakeoff_oracle":
                raise OracleContractError(
                    f"run-phase module {mod_name!r} references "
                    f"product_bakeoff_oracle via attribute {attr_name!r}; "
                    "normal adapter RUN execution must not import or receive "
                    "oracle data/files"
                )
    if "product_bakeoff_oracle" in loaded:
        # Loaded now because this function is running; the guard is that
        # run-phase modules do not HOLD a reference.
        pass


def oracle_to_public_envelope(oracle: TaskOracle) -> Mapping[str, Any]:
    """Return a scorer-only envelope dict (aggregate-safe, no raw labels).

    This is the ONLY public serialization of an oracle; it carries only coarse
    presence booleans and the oracle_kind. It is never emitted in the Phase A
    aggregate report (the report is built from validated run records only, not
    oracle envelopes).
    """
    oracle.validate()
    return {
        "oracle_schema_version": ORACLE_SCHEMA_VERSION,
        "task_slug": oracle.task_slug,
        "oracle_kind": oracle.oracle_kind,
        "acceptable_target_span_count": len(oracle.acceptable_target_spans),
        "expected_support_record_count": len(oracle.expected_support_records),
        "must_not_primary_count": len(oracle.must_not_primary_paths),
    }


def serialize_oracle_envelope(oracle: TaskOracle) -> str:
    """Serialize the public oracle envelope to canonical JSON. Scorer-only;
    never committed in Phase A (no Phase A scoring is performed)."""
    return json.dumps(
        dict(oracle_to_public_envelope(oracle)), sort_keys=True
    )


__all__ = [
    "ORACLE_SCHEMA_VERSION",
    "GENERATED_BY",
    "CLAIM_LEVEL",
    "ORACLE_KINDS",
    "ORACLE_RELATION_KINDS",
    "OracleContractError",
    "OracleSupportRecord",
    "TaskOracle",
    "assert_run_phase_not_importing_oracle",
    "oracle_to_public_envelope",
    "serialize_oracle_envelope",
]
