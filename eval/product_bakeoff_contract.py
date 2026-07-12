#!/usr/bin/env python3
"""Product Stack Bakeoff Phase A — canonical contract surface (v12).

This module defines the public, fairness-relevant contract surface that every
product-stack bakeoff adapter must satisfy. It is the Phase A *executable
surface*, not a report shell.

Binding contract (v9 — full initial source-tree freeze, pre-hook
infrastructure scan, capability-ledger trust, and deadline-inclusive transport):

v10 closures (three narrow gaps in already-claimed v9 guarantees):

* ``_enumerate_source_tree`` rejects special files (FIFO, socket, device,
  directory, unknown file types) BEFORE ``read_bytes`` via
  ``stat.S_ISREG(st_mode)`` on the lstat result — without opening or reading
  the entry. After read, the after-lstat is required to still be a regular
  file with identical ``(st_dev, st_ino, st_mode, st_size)`` identity; any
  replacement/mode/type/size change rejects. Available identity fields are
  compared consistently (``st_ino`` is 0 on some Windows filesystems; the
  comparison still holds because both sides are 0). Root and writable-state-
  root existing type validation fail closed on lstat errors.

* ``BakeoffTask`` is public and adapter-visible; it carries NO gold/target/
  support labels (those live in the scorer-only ``TaskOracle`` in
  ``product_bakeoff_oracle.py``).
* ``AdapterRequest`` / ``BakeoffRunSpec`` freeze the comparison cell: schema,
  run-cell, task, snapshot/source-visibility/visible-tree IDs AND digests, query
  (via the task), language/task family, adapter repetition, closed cold/warm
  cache state, interaction mode and lineage, candidate/evidence/target/support/
  rendered-context/episode/step caps, timeout, renderer/materializer/budget-
  estimator versions, and a separately declared writable-state-root id. The
  run-spec task/interaction/operation duplication IS cross-validated.
* ``fairness_fingerprint`` is derived from every fairness-relevant run-spec
  field EXCEPT adapter identity and measured resources; comparable arms must
  match exactly.
* ``Candidate`` carries only ``path``, range, ``score`` (finite adapter-local
  higher-is-better; NOT forced to [0,1]), ``reason``, ``channels`` (a subset of
  the descriptor-declared output channels), and adapter provenance (which must
  match the descriptor identity). It CANNOT supply excerpt, hash, freshness, or
  verified claims. There is ONE candidate collection on the result.
* Only the common materializer (``materialize_candidates``) may construct
  ``BakeoffVerifiedEvidence`` from a single source-byte read. This is a
  BAKEOFF-ONLY schema (NOT production EvidenceCore): it uses unambiguous
  ``source_sha256`` (full-file SHA-256), ``excerpt_sha256`` (excerpt SHA-256),
  and tuple ``why`` (tuple[str, ...]) plus the actual selected source excerpt
  and freshness metadata. Exact production EvidenceCore projection
  (``content_sha`` BLAKE3, ``why[]`` list, production channels) is DEFERRED to
  landing integration; bakeoff results CANNOT be passed directly as production
  EvidenceCore. No BLAKE3 dependency is added.
* ``ContextPack`` carries targets, support, uncertainty/status, diagnostics,
  exact harness-recomputed budget usage over the ACTUAL rendered context, and
  the rendered context itself. A pack hash covers the actual rendered context.
  v6: pack validation consumes the ACTUAL bakeoff evidence tuple and
  deterministically verifies every target/support path+range against its
  referenced evidence, exact rerendered context, and EVERY ``BudgetUsage``
  field (including caller-supplied candidate count and cumulative episode
  fields). No externally forged ``BudgetUsage`` field can pass.
* An untrusted ``BindingProposal`` (candidate references/roles only) is the
  strategy-owned pack-assembly boundary; common code validates references,
  materializes, and renders. v6: the proposal carries a closed
  ``proposed_status`` (``ready`` / ``uncertain`` / ``no_evidence``) plus
  ``status_reason``; exact combinations are enforced; an ``ok`` result MUST
  carry an explicit proposal; the harness derives the final pack from the
  proposal and actual evidence. S0-S3 vs S4-S5 pack policies are NOT erased by
  hardcoded first-target/all-definition behaviour.
* ``AdapterDescriptor`` carries supported languages, persistent-state behaviour
  (cold/warm reuse semantics), execution mode, upstream revision, SPDX/license
  state, and descriptor-declared output channels. v6: ``fallback_chain`` is
  REMOVED entirely (no second fallback contract); per-result ``FallbackRecord``
  is kept and validated. ``AdapterHooks`` wraps optional prepare/index hooks
  and a REQUIRED query hook; hooks must be top-level functions for Windows
  spawn-picklability. The harness owns phase timing
  (setup/index/query/materialize/render).
* ``AdapterDescriptor`` and ``AdapterHooks`` are cross-validated via
  ``validate_descriptor_hooks``: a lifecycle hook requires the ``prepare_index``
  capability; ``warm_reuse`` requires a real state-building hook (prepare or
  index); ``cold_rebuild`` requires index; hook absence cannot claim
  executable prepare/index.
* v7: ``execution_mode`` is narrowed to exactly ONE truthful value
  (``process_isolated``). The harness spawns a FRESH ``multiprocessing.spawn``
  child per attempted prepare/index/query hook (skipped warm hooks spawn
  nothing). Each phase independently uses the existing frozen
  ``timeout_seconds`` with immediate terminate/kill/reap on timeout; only the
  exception TYPE (never the message) crosses the process boundary. Lifecycle
  state is shared only through the declared ``writable_state_root``. This is
  NOT an OS security sandbox.
* ``AdapterResult`` carries ONE candidate collection, an exact capability ledger
  (keys must EXACTLY equal descriptor capabilities), structured unavailable->
  executed fallback provenance, and NO adapter-authored resource sample (only
  the harness measures resources). The closed capability ledger uses
  ``executed``/``legitimate_skip``/``unsupported``/``failed``/``timeout``;
  common harness capabilities are NOT adapter ledger entries. v6: the adapter
  capability set is ``prepare_index`` / ``candidate_search`` /
  ``target_binding`` / ``support_expansion`` / ``two_step_support``;
  ``validate_capability_ledger_honesty`` cross-checks the ledger against actual
  execution (prepare/index attempted, target/support refs present, support
  operation producing support) and conversely.
* ``validate_execution_root_binding`` requires the resolved execution root
  equals the snapshot root and the writable-state root matches its declared id
  and stays confined beneath the snapshot root.
* ``validate_adapter_result`` binds request adapter id/version to descriptor
  id/version and requires the task language in descriptor-supported languages.
* ``scan_visible_tree`` rejects symlink directories AND symlinked path
  components; every resolved visible/candidate/writable path must stay beneath
  the resolved source root. ``_validate_safe_path_under_root`` is the COMMON
  safe path policy applied before any snapshot read or directory creation in
  manifest/snapshot/tree/candidate/writable validation. Out-of-root
  writable-state roots are rejected WITHOUT being created. v5: the component
  walk inspects ORIGINAL LEXICAL path components (not resolved parts) so an
  in-root parent symlink (whose target stays inside root) is also rejected;
  a lexical path not beneath root is rejected before the resolved confinement
  check. ``materialize_snapshot`` additionally rejects, BEFORE ``mkdir``, a
  writable-state root equal to the source root, a writable-state root that is
  an ancestor/equal of any visible path, and any visible path inside the
  writable-state root.

Threat model (honest): the conformance surface enforces contract closure and
rejects accidental leakage of scorer/oracle/path/excerpt/freshness facts into
adapter outputs. It does NOT contain a hostile executable that scans the host
machine; adversarial adapters here test contract enforcement, not host
sandboxing. Phase A makes no product/algorithm/default/winner claim.

Run::

    python -m py_compile eval/product_bakeoff_contract.py
    python eval/product_bakeoff_conformance.py --self-test
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

# ---------------------------------------------------------------------------
# Closed enums / vocabularies
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "product_bakeoff_contract.v12"
GENERATED_BY = "eval/product_bakeoff_contract.py"
CLAIM_LEVEL = "synthetic_adapter_conformance_contract_only"

INTERACTION_MODES: frozenset[str] = frozenset({"one_shot", "two_step"})
OPERATIONS: frozenset[str] = frozenset({"context", "support"})
LANGUAGE_FAMILIES: frozenset[str] = frozenset(
    {"rust", "python", "typescript", "go", "java", "csharp", "ruby"}
)
# Phase-B-sufficient task families, including the expanded query/task strata:
# ambiguous target, error text, configuration/test discovery, no-answer.
TASK_FAMILIES: frozenset[str] = frozenset(
    {
        "symbol_lookup",
        "definition_find",
        "caller_trace",
        "type_resolution",
        "cross_file_dependency",
        "refactor_target_find",
        # Expanded Phase-B-facing strata:
        "ambiguous_target",
        "error_text",
        "configuration_discovery",
        "test_discovery",
        "no_answer",
    }
)
SOURCE_VISIBILITY: frozenset[str] = frozenset({"frozen_visible"})

# Closed cold/warm cache state.
CACHE_STATES: frozenset[str] = frozenset({"cold", "warm"})

# Descriptor execution modes. v7: narrowed to exactly ONE truthful value
# (``process_isolated``). The harness spawns a fresh multiprocessing.spawn
# child per attempted prepare/index/query hook (skipped warm hooks spawn
# nothing); each phase independently uses the existing frozen timeout_seconds
# with immediate terminate/kill/reap. There is NO in-process code path;
# vocabulary drift (``in_process`` / ``subprocess``) is rejected. This is
# process separation + timeout enforcement, NOT an OS security sandbox.
# v8: spawned-process cleanup is deterministic on every path (proc.start()
# inside a cleanup-protected boundary; child/parent pipe endpoints closed on
# all paths; started tracked; terminate-if-required, unconditional join,
# kill+join, proc.close() after reaping). A genuine multiprocessing
# launch/resource failure cleans up and then aborts the whole bakeoff as a
# HarnessInfrastructureError — never one adapter's ValidatedRunRecord.
EXECUTION_MODES: frozenset[str] = frozenset({"process_isolated"})

# SPDX / license state.
SPDX_STATES: frozenset[str] = frozenset({"declared", "missing", "not_applicable"})

# Declared persistent-state behaviour for cold/warm reuse semantics.
#   stateless    — no persistent state; prepare+index always run if present.
#   cold_rebuild — index rebuilt each run; prepare+index always run if present.
#   warm_reuse   — persistent state may be reused; warm cache_state may skip
#                  prepare (state assumed to exist) and index (reused).
PERSISTENT_STATE_BEHAVIORS: frozenset[str] = frozenset(
    {"stateless", "cold_rebuild", "warm_reuse"}
)

# Broad canonical candidate channels; the descriptor declares its output_channels
# as a subset, and every candidate's channels must be a subset of that.
CHANNELS: frozenset[str] = frozenset(
    {"bm25", "regex", "text", "symbol", "graph", "structural", "support", "two_step"}
)

# Adapter-owned capabilities ONLY. Common harness capabilities
# (current_source_materialize, context_pack_build) are NOT adapter ledger
# entries; the harness performs them, not the adapter.
# v6: ``target_binding`` and ``support_expansion`` added as minimal
# capabilities so the capability ledger can be cross-checked against actual
# binding/support output. ``two_step_support`` remains for real two-step
# support operations.
CAPABILITIES: frozenset[str] = frozenset(
    {
        "prepare_index",
        "candidate_search",
        "target_binding",
        "support_expansion",
        "two_step_support",
    }
)

# Closed capability-ledger statuses.
CAPABILITY_STATUSES: frozenset[str] = frozenset(
    {"executed", "legitimate_skip", "unsupported", "failed", "timeout"}
)
# Statuses that are "unavailable" (could trigger a fallback).
UNAVAILABLE_STATUSES: frozenset[str] = frozenset(
    {"unsupported", "failed", "timeout"}
)

# AdapterResult statuses (closed).
RESULT_STATUSES: frozenset[str] = frozenset(
    {"ok", "failed", "timeout", "malformed", "partial"}
)
# Statuses that may produce a context pack: only ``ok``.
PACK_OK_STATUSES: frozenset[str] = frozenset({"ok"})

# Pack statuses (closed).
PACK_STATUSES: frozenset[str] = frozenset({"ready", "no_evidence", "uncertain"})

# Support relation kinds (closed).
RELATION_KINDS: frozenset[str] = frozenset(
    {"definition", "caller", "import", "type_dep"}
)

# Deterministic budget estimator name + version (ceiling estimate).
BUDGET_ESTIMATOR_NAME = "char_div_4_ceil"
BUDGET_ESTIMATOR_VERSION = "v4"
MATERIALIZER_VERSION = "harness_common_v4"
RENDERER_VERSION = "harness_renderer_v4"

# Candidate fields that are FORBIDDEN on a Candidate. The adapter must never
# supply these; only the harness materializer may derive current-source facts.
FORBIDDEN_CANDIDATE_KEYS: frozenset[str] = frozenset(
    {
        "excerpt",
        "snippet",
        "content",
        "text",
        "hash",
        "content_sha",
        "digest",
        "freshness",
        "fresh",
        "verified",
        "verified_current",
        "materialized",
        "byte_count",
        "char_count",
        "line_count",
        "full_source_hash",
        "source_sha256",
        "excerpt_hash",
        "excerpt_sha256",
        "gold_span",
        "gold",
        "label",
        "oracle",
        "outcome",
    }
)

# Keys that must NEVER appear in a public aggregate report row (privacy scan).
PRIVATE_REPORT_KEYS: frozenset[str] = frozenset(
    {
        "query",
        "path",
        "candidate_path",
        "start_line",
        "end_line",
        "line_range",
        "excerpt",
        "snippet",
        "content",
        "text",
        "rendered_context",
        "hash",
        "content_sha",
        "digest",
        "freshness",
        "gold_span",
        "gold",
        "label",
        "oracle",
        "outcome",
        "task_id",
        "test_id",
        "repo_id",
        "candidate_id",
        "run_id",
        "request_id",
        "episode_id",
        "workspace",
        "singleton",
        "prompt",
        "response",
        "raw_response",
        "provider_key",
        "api_key",
        "base_url",
    }
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


class ContractError(ValueError):
    """Raised when an adapter/request/result/pack violates the contract."""


def _require_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{name} must be bool, got {type(value).__name__}")
    return value


def _require_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{name} must be int, got {type(value).__name__}")
    return value


def _require_float(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be finite float")
    f = float(value)
    if f != f or f in (float("inf"), float("-inf")):
        raise ContractError(f"{name} must be finite")
    return f


def _require_str(name: str, value: Any, max_len: int = 256) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be str, got {type(value).__name__}")
    if len(value) > max_len:
        raise ContractError(f"{name} exceeds max_len {max_len}")
    return value


def _require_in_vocab(name: str, value: Any, vocab: frozenset[str]) -> str:
    s = _require_str(name, value, max_len=64)
    if s not in vocab:
        raise ContractError(f"{name}={s!r} not in closed vocab {sorted(vocab)}")
    return s


def _require_finite_score(name: str, value: Any) -> float:
    """Scores are finite adapter-local higher-is-better; NOT forced to [0,1]."""
    return _require_float(name, value)


def _require_frozenset_str(
    name: str, value: Any, vocab: frozenset[str] | None
) -> frozenset[str]:
    if not isinstance(value, (frozenset, set, tuple, list)):
        raise ContractError(f"{name} must be a set/tuple/list of str")
    out: set[str] = set()
    for v in value:
        s = _require_str(f"{name}[item]", v, max_len=64)
        if vocab is not None and s not in vocab:
            raise ContractError(f"{name} item {s!r} not in closed vocab")
        if s in out:
            raise ContractError(f"{name} duplicate item {s!r}")
        out.add(s)
    return frozenset(out)


# ---------------------------------------------------------------------------
# Path safety (snapshot/visibility isolation + symlink confinement)
# ---------------------------------------------------------------------------

_NUL_RE = re.compile(r"\x00")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_TRAVERSAL_RE = re.compile(r"(?:^|/)\.\.(?:/|$)")

# Windows FILE_ATTRIBUTE_REPARSE_POINT bit (0x400). Junctions and some symlink
# forms surface here; ``Path.is_symlink()`` catches POSIX symlinks. Combining
# both rejects reparse points (junctions) that ``is_symlink()`` may miss on
# Windows. Cross-platform: ``st_file_attributes`` is absent on POSIX so the
# bit check is skipped there.
_FILE_ATTR_REPARSE_POINT = 0x400


def _is_reparse_or_link(path: Path) -> bool:
    """True if ``path`` is a symlink OR a Windows reparse point (junction).

    Every stat/lstat error is treated as a special-file rejection: the caller
    cannot trust an unreadable/unstat-able entry during a full enumeration.
    """
    try:
        if path.is_symlink():
            return True
    except (OSError, RuntimeError):
        return True
    try:
        st = os.lstat(path)
    except (OSError, ValueError):
        return True
    fa = getattr(st, "st_file_attributes", 0) or 0
    if fa & _FILE_ATTR_REPARSE_POINT:
        return True
    return False


def _validate_lexical_relative_path(name: str, p: str) -> str:
    """Lexical validation of a relative POSIX path string. Rejects: empty,
    NUL bytes, UNC prefix, absolute (leading /), drive letters (C:), traversal
    (..), backslashes, and dot-only paths. This is the lexical half of the
    common safe path policy; it does NOT touch the filesystem.
    """
    if not isinstance(p, str):
        raise ContractError(f"{name} must be str, got {type(p).__name__}")
    if not p:
        raise ContractError(f"{name} must be non-empty")
    if len(p) > 512:
        raise ContractError(f"{name} exceeds 512 chars")
    if _NUL_RE.search(p):
        raise ContractError(f"{name} contains NUL byte")
    if p.startswith("\\\\"):
        raise ContractError(f"{name} rejects UNC prefix")
    if p.startswith("/"):
        raise ContractError(f"{name} rejects absolute prefix")
    if _DRIVE_RE.match(p):
        raise ContractError(f"{name} rejects drive letter")
    if "\\" in p:
        raise ContractError(f"{name} must use posix separators")
    if _TRAVERSAL_RE.search(p):
        raise ContractError(f"{name} rejects traversal")
    if p in (".", ".."):
        raise ContractError(f"{name} rejects dot-only path")
    return p


def _validate_safe_path_under_root(
    full: Path, root_resolved: Path, label: str
) -> Path:
    """COMMON safe path policy (lexical + resolved confinement + all
    components checked for symlinks). Applied before any snapshot read or
    directory creation in manifest/snapshot/tree/candidate/writable
    validation. Returns the resolved path on success.

    Stages (v5 closure):
      1. The ORIGINAL LEXICAL relative path of ``full`` beneath
         ``root_resolved`` is computed. A lexical path that is not beneath
         ``root_resolved`` is REJECTED (catches symlinked prefixes that
         resolve into root — ``full.resolve()`` would hide them).
      2. Each ORIGINAL LEXICAL prefix component beneath ``root_resolved`` is
         checked for symlinks (rejects parent symlinks AND symlinked path
         components, even when the symlink target is still inside the root —
         ``full.resolve()`` would hide those because it dereferences first).
      3. The fully resolved path must stay beneath ``root_resolved`` (catches
          symlinked components that escape).
    """
    # Stage 1: lexical relative path MUST be beneath root_resolved. A lexical
    # path not beneath root indicates a symlinked prefix that resolves into
    # root (or a path that escapes); reject rather than silently accepting.
    # On Windows, 8.3 short-name aliasing in the root prefix can cause
    # ``full`` (constructed from an unresolved root) to differ lexically
    # from ``root_resolved``. In that case, fall back to the RESOLVED relative
    # path: if the resolved path is also not beneath root_resolved, reject
    # (escape). The in-root parent-symlink fixture is exercised on symlink-
    # capable CI (Linux), where short-name aliasing does not occur and the
    # lexical path is available for the component walk.
    try:
        rel = full.relative_to(root_resolved)
    except ValueError:
        try:
            rel = full.resolve().relative_to(root_resolved)
        except ValueError as exc:
            raise ContractError(
                f"{label}: lexical path {full} is not beneath root "
                f"{root_resolved} (symlinked prefix or escape rejected)"
            ) from exc
    rel_posix = rel.as_posix()
    # rel_posix may legitimately start with a drive on Windows if
    # root_resolved is on a different drive (already rejected above); apply
    # lexical validation to the relative portion.
    if not (rel_posix.startswith("/") or _DRIVE_RE.match(rel_posix)):
        _validate_lexical_relative_path(label + ".relative", rel_posix)
    # Stage 2: Walk ORIGINAL LEXICAL path components beneath the root. This
    # catches symlink components that resolve to a location still inside the
    # root (which full.resolve() would hide, because resolve() dereferences
    # the symlink before walking). We walk the LEXICAL parts, NOT the
    # resolved parts.
    cur = root_resolved
    for part in rel.parts:
        cur = cur / part
        try:
            is_link = cur.is_symlink()
        except OSError as exc:
            raise ContractError(
                f"{label}: cannot stat component {cur}: {exc}"
            ) from exc
        if is_link:
            raise ContractError(
                f"{label}: path component {cur} is a symlink "
                "(parent symlink rejected)"
            )
    # Stage 3: resolved confinement (catches symlinked components that escape).
    _check_resolved_under_root(full, root_resolved, label)
    return full.resolve()


def validate_relative_path(raw: Any, visible_files: Iterable[str]) -> str:
    """Validate a candidate path is a frozen visible relative file.

    Rejects: non-str, absolute (leading /), drive letters (C:), UNC (\\\\),
    traversal (..), NUL bytes, backslashes, symlink targets, and files not in
    the frozen visible set. Returns the canonical POSIX-style relative path.

    The lexical half of the COMMON safe path policy is applied via
    ``_validate_lexical_relative_path``; resolved confinement + component
    symlink checks are applied later by the materializer via
    ``_validate_safe_path_under_root`` (which needs the resolved root).
    """
    p = _validate_lexical_relative_path("candidate path", raw)
    visible = set(visible_files)
    if p not in visible:
        raise ContractError(
            "candidate path not in frozen visible set (path escape rejected)"
        )
    return p


def validate_line_range(start_raw: Any, end_raw: Any) -> tuple[int, int]:
    """Validate a 1-indexed inclusive line range with start <= end."""
    s = _require_int("start_line", start_raw)
    e = _require_int("end_line", end_raw)
    if s < 1:
        raise ContractError(f"start_line {s} must be >= 1")
    if e < 1:
        raise ContractError(f"end_line {e} must be >= 1")
    if s > e:
        raise ContractError(f"line range start {s} > end {e}")
    return (s, e)


def _check_resolved_under_root(full: Path, root_resolved: Path, label: str) -> None:
    """Require a resolved path to stay beneath the resolved source root.

    This catches symlinked path components that escape the source root.
    """
    try:
        resolved = full.resolve()
    except (OSError, RuntimeError) as exc:
        raise ContractError(f"{label}: cannot resolve path {full}: {exc}") from exc
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        raise ContractError(
            f"{label}: resolved path {resolved} escapes source root {root_resolved}"
        )


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BakeoffTask:
    """Public, adapter-visible task. Carries NO gold/target/support labels."""

    task_slug: str
    language_family: str
    task_family: str
    interaction_mode: str
    source_visibility: str
    query: str  # public query; never emitted in the aggregate report
    operation: str = "context"

    def validate(self) -> "BakeoffTask":
        _require_str("task_slug", self.task_slug, max_len=128)
        _require_in_vocab("language_family", self.language_family, LANGUAGE_FAMILIES)
        _require_in_vocab("task_family", self.task_family, TASK_FAMILIES)
        _require_in_vocab("interaction_mode", self.interaction_mode, INTERACTION_MODES)
        _require_in_vocab("source_visibility", self.source_visibility, SOURCE_VISIBILITY)
        _require_str("query", self.query, max_len=512)
        _require_in_vocab("operation", self.operation, OPERATIONS)
        # Cross-field: support operation requires two_step mode.
        if self.operation == "support" and self.interaction_mode != "two_step":
            raise ContractError(
                "support operation requires two_step interaction_mode"
            )
        return self


@dataclass(frozen=True)
class BudgetCaps:
    """Frozen per-arm budget caps. Over-cap is conformance failure."""

    max_candidates: int
    max_evidence: int
    max_targets: int
    max_support: int
    max_render_chars: int
    max_render_bytes: int
    max_render_estimate: int
    episode_step_cap: int
    episode_estimate_cap: int

    def validate(self) -> "BudgetCaps":
        for name in (
            "max_candidates",
            "max_evidence",
            "max_targets",
            "max_support",
            "max_render_chars",
            "max_render_bytes",
            "max_render_estimate",
            "episode_step_cap",
            "episode_estimate_cap",
        ):
            v = _require_int(name, getattr(self, name))
            if v < 1:
                raise ContractError(f"{name}={v} must be >= 1")
            if v > 1_000_000:
                raise ContractError(f"{name}={v} exceeds hard cap")
        return self

    def fingerprint_dict(self) -> dict[str, int]:
        return {
            "max_candidates": self.max_candidates,
            "max_evidence": self.max_evidence,
            "max_targets": self.max_targets,
            "max_support": self.max_support,
            "max_render_chars": self.max_render_chars,
            "max_render_bytes": self.max_render_bytes,
            "max_render_estimate": self.max_render_estimate,
            "episode_step_cap": self.episode_step_cap,
            "episode_estimate_cap": self.episode_estimate_cap,
        }


@dataclass(frozen=True)
class BakeoffRunSpec:
    """Frozen comparison cell (fairness-relevant fields)."""

    schema_id: str
    run_cell_id: str
    task: BakeoffTask
    snapshot_id: str
    source_visibility_id: str
    # Actual per-file frozen manifest digest (binds the snapshot to the request).
    snapshot_manifest_digest: str
    source_visibility_digest: str
    visible_tree_digest: str
    adapter_repetition: int
    cache_state: str  # closed cold/warm
    interaction_mode: str
    operation: str
    episode_id: str
    request_id: str
    parent_result_id: str | None
    bound_target_id: str | None
    caps: BudgetCaps
    timeout_seconds: float
    renderer_version: str
    materializer_version: str
    budget_estimator_version: str
    writable_state_root_id: str

    def validate(self) -> "BakeoffRunSpec":
        _require_str("schema_id", self.schema_id, max_len=128)
        _require_str("run_cell_id", self.run_cell_id, max_len=128)
        self.task.validate()
        _require_str("snapshot_id", self.snapshot_id, max_len=128)
        _require_str("source_visibility_id", self.source_visibility_id, max_len=128)
        _require_str("snapshot_manifest_digest", self.snapshot_manifest_digest, max_len=128)
        _require_str("source_visibility_digest", self.source_visibility_digest, max_len=128)
        _require_str("visible_tree_digest", self.visible_tree_digest, max_len=128)
        ar = _require_int("adapter_repetition", self.adapter_repetition)
        if ar < 1 or ar > 9:
            raise ContractError(f"adapter_repetition {ar} must be in [1,9]")
        _require_in_vocab("cache_state", self.cache_state, CACHE_STATES)
        _require_in_vocab(
            "interaction_mode", self.interaction_mode, INTERACTION_MODES
        )
        _require_in_vocab("operation", self.operation, OPERATIONS)
        # Cross-validate duplicated task/interaction/operation fields.
        if self.task.interaction_mode != self.interaction_mode:
            raise ContractError(
                f"task.interaction_mode {self.task.interaction_mode!r} != "
                f"run_spec.interaction_mode {self.interaction_mode!r}"
            )
        if self.task.operation != self.operation:
            raise ContractError(
                f"task.operation {self.task.operation!r} != "
                f"run_spec.operation {self.operation!r}"
            )
        _require_str("episode_id", self.episode_id, max_len=128)
        _require_str("request_id", self.request_id, max_len=128)
        if self.parent_result_id is not None:
            _require_str("parent_result_id", self.parent_result_id, max_len=128)
        if self.bound_target_id is not None:
            _require_str("bound_target_id", self.bound_target_id, max_len=128)
        self.caps.validate()
        t = _require_float("timeout_seconds", self.timeout_seconds)
        if t <= 0.0 or t > 3600.0:
            raise ContractError(f"timeout_seconds {t} must be in (0, 3600]")
        _require_str("renderer_version", self.renderer_version, max_len=64)
        _require_str("materializer_version", self.materializer_version, max_len=64)
        _require_str(
            "budget_estimator_version", self.budget_estimator_version, max_len=64
        )
        _require_str("writable_state_root_id", self.writable_state_root_id, max_len=128)
        # Cross-field lineage: support operation requires parent + bound target.
        if self.operation == "support":
            if self.parent_result_id is None or self.bound_target_id is None:
                raise ContractError(
                    "support operation requires parent_result_id and "
                    "bound_target_id"
                )
            if self.interaction_mode != "two_step":
                raise ContractError(
                    "support operation requires two_step interaction_mode"
                )
        else:
            if self.parent_result_id is not None or self.bound_target_id is not None:
                raise ContractError(
                    "context operation must not carry parent/bound_target lineage"
                )
        if self.interaction_mode == "two_step" and self.caps.episode_step_cap < 2:
            raise ContractError(
                "two_step interaction_mode requires episode_step_cap >= 2"
            )
        return self


@dataclass(frozen=True)
class AdapterRequest:
    """Adapter-visible request = run-spec + adapter identity (adapter identity
    is EXCLUDED from the fairness fingerprint)."""

    run_spec: BakeoffRunSpec
    adapter_id: str
    adapter_version: str

    def validate(self) -> "AdapterRequest":
        self.run_spec.validate()
        _require_str("adapter_id", self.adapter_id, max_len=128)
        _require_str("adapter_version", self.adapter_version, max_len=64)
        return self


# ---------------------------------------------------------------------------
# Fairness fingerprint
# ---------------------------------------------------------------------------


def fairness_fingerprint(run_spec: BakeoffRunSpec) -> str:
    """Derive the fairness fingerprint from every fairness-relevant run-spec
    field EXCEPT adapter identity and measured resources.

    Two arms with the same fingerprint are comparable. The fingerprint is a
    short ``fp_``-prefixed hex token; it does not reveal the raw query.
    """
    run_spec.validate()
    fp_input = {
        "schema_id": run_spec.schema_id,
        "run_cell_id": run_spec.run_cell_id,
        "task": {
            "task_slug": run_spec.task.task_slug,
            "language_family": run_spec.task.language_family,
            "task_family": run_spec.task.task_family,
            "interaction_mode": run_spec.task.interaction_mode,
            "source_visibility": run_spec.task.source_visibility,
            "query": run_spec.task.query,
            "operation": run_spec.task.operation,
        },
        "snapshot_id": run_spec.snapshot_id,
        "source_visibility_id": run_spec.source_visibility_id,
        "snapshot_manifest_digest": run_spec.snapshot_manifest_digest,
        "source_visibility_digest": run_spec.source_visibility_digest,
        "visible_tree_digest": run_spec.visible_tree_digest,
        "adapter_repetition": run_spec.adapter_repetition,
        "cache_state": run_spec.cache_state,
        "interaction_mode": run_spec.interaction_mode,
        "operation": run_spec.operation,
        "episode_id": run_spec.episode_id,
        # request_id is an ID -> excluded (determinism/cells excludes IDs).
        # parent/bound_target carry lineage that is fairness-relevant for
        # support comparison, so included when present.
        "parent_result_id": run_spec.parent_result_id,
        "bound_target_id": run_spec.bound_target_id,
        "caps": run_spec.caps.fingerprint_dict(),
        "timeout_seconds": run_spec.timeout_seconds,
        "renderer_version": run_spec.renderer_version,
        "materializer_version": run_spec.materializer_version,
        "budget_estimator_version": run_spec.budget_estimator_version,
        "writable_state_root_id": run_spec.writable_state_root_id,
    }
    canon = json.dumps(fp_input, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]
    return f"fp_{digest}"


# ---------------------------------------------------------------------------
# Candidate (adapter-supplied; no excerpt/hash/freshness/verified)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    path: str
    start_line: int
    end_line: int
    score: float
    reason: str
    channels: frozenset[str]
    adapter_provenance: str

    def validate(self, visible_files: Iterable[str]) -> "Candidate":
        p = validate_relative_path(self.path, visible_files)
        s, e = validate_line_range(self.start_line, self.end_line)
        sc = _require_finite_score("score", self.score)
        _require_str("reason", self.reason, max_len=128)
        ch = _require_frozenset_str("channels", self.channels, CHANNELS)
        if len(ch) == 0:
            raise ContractError("channels must be non-empty")
        _require_str("adapter_provenance", self.adapter_provenance, max_len=128)
        return Candidate(
            path=p,
            start_line=s,
            end_line=e,
            score=sc,
            reason=self.reason,
            channels=ch,
            adapter_provenance=self.adapter_provenance,
        )

    def normalized_cell(self) -> tuple[str, int, int]:
        """Normalized comparison cell (path, start, end). Duplicate cells
        across candidates in the same result are rejected."""
        return (self.path, self.start_line, self.end_line)


def validate_candidate_obj(obj: Any, visible_files: Iterable[str]) -> Candidate:
    """Validate a candidate supplied as a Candidate instance OR a dict.

    Dicts are rejected if they carry any forbidden key (excerpt/hash/
    freshness/verified/...). This is the adversarial entry point: an adapter
    that tries to leak current-source facts via a dict is rejected.
    """
    visible = list(visible_files)
    if isinstance(obj, Candidate):
        return obj.validate(visible)
    if isinstance(obj, dict):
        extra = set(obj.keys()) - {
            "path",
            "start_line",
            "end_line",
            "score",
            "reason",
            "channels",
            "adapter_provenance",
        }
        if extra:
            raise ContractError(
                f"candidate dict has extra keys {sorted(extra)}; only the "
                "common materializer may derive current-source facts"
            )
        forbidden = set(obj.keys()) & FORBIDDEN_CANDIDATE_KEYS
        if forbidden:
            raise ContractError(
                f"candidate dict carries forbidden keys {sorted(forbidden)}"
            )
        for required in (
            "path",
            "start_line",
            "end_line",
            "score",
            "reason",
            "channels",
            "adapter_provenance",
        ):
            if required not in obj:
                raise ContractError(f"candidate dict missing key {required!r}")
        cand = Candidate(
            path=obj["path"],
            start_line=obj["start_line"],
            end_line=obj["end_line"],
            score=obj["score"],
            reason=obj["reason"],
            channels=obj["channels"],
            adapter_provenance=obj["adapter_provenance"],
        )
        return cand.validate(visible)
    raise ContractError(
        f"candidate must be Candidate or dict, got {type(obj).__name__}"
    )


# ---------------------------------------------------------------------------
# Adapter descriptor + hooks + result + resource sample + binding proposal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterDescriptor:
    adapter_id: str
    adapter_version: str
    capabilities: frozenset[str]
    default_capability: str | None
    # v6: ``fallback_chain`` REMOVED entirely. Per-result ``FallbackRecord``
    # is the sole fallback contract; descriptors do not declare a fallback chain.
    # Descriptor-declared metadata.
    supported_languages: frozenset[str]
    persistent_state_behavior: str  # stateless | cold_rebuild | warm_reuse
    execution_mode: str
    upstream_revision: str
    spdx_license_state: str
    output_channels: frozenset[str]

    def validate(self) -> "AdapterDescriptor":
        _require_str("adapter_id", self.adapter_id, max_len=128)
        _require_str("adapter_version", self.adapter_version, max_len=64)
        caps = _require_frozenset_str(
            "capabilities", self.capabilities, CAPABILITIES
        )
        if len(caps) == 0:
            raise ContractError("capabilities must be non-empty")
        if self.default_capability is not None:
            _require_in_vocab(
                "default_capability", self.default_capability, CAPABILITIES
            )
            if self.default_capability not in caps:
                raise ContractError(
                    "default_capability must be in declared capabilities"
                )
        langs = _require_frozenset_str(
            "supported_languages", self.supported_languages, LANGUAGE_FAMILIES
        )
        if len(langs) == 0:
            raise ContractError("supported_languages must be non-empty")
        _require_in_vocab(
            "persistent_state_behavior",
            self.persistent_state_behavior,
            PERSISTENT_STATE_BEHAVIORS,
        )
        _require_in_vocab("execution_mode", self.execution_mode, EXECUTION_MODES)
        _require_str("upstream_revision", self.upstream_revision, max_len=128)
        _require_in_vocab("spdx_license_state", self.spdx_license_state, SPDX_STATES)
        och = _require_frozenset_str("output_channels", self.output_channels, CHANNELS)
        if len(och) == 0:
            raise ContractError("output_channels must be non-empty")
        return AdapterDescriptor(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            capabilities=caps,
            default_capability=self.default_capability,
            supported_languages=langs,
            persistent_state_behavior=self.persistent_state_behavior,
            execution_mode=self.execution_mode,
            upstream_revision=self.upstream_revision,
            spdx_license_state=self.spdx_license_state,
            output_channels=och,
        )


@dataclass(frozen=True)
class AdapterHooks:
    """Minimal adapter hook container. ``prepare`` and ``index`` are optional;
    ``query`` is required. Hooks MUST be top-level functions (not lambdas or
    closures) for Windows spawn-picklability — the query hook is passed to a
    spawned subprocess.

    The common harness does ALL source reading/materialization/rendering;
    adapters only emit untrusted candidates/binding via the query hook. Prepare
    and index hooks are lifecycle-only (setup/index state); they must not
    produce candidates or evidence.

    Cross-validated with ``AdapterDescriptor`` via ``validate_descriptor_hooks``:
    a lifecycle hook requires the ``prepare_index`` capability;
    ``persistent_state_behavior=warm_reuse`` requires a real state-building
    hook (prepare or index); ``cold_rebuild`` requires index; hook absence
    cannot claim executable prepare/index.

    v7: ``execution_mode`` is narrowed to exactly ``process_isolated``. The
    harness spawns a FRESH ``multiprocessing.spawn`` child for EVERY attempted
    prepare/index/query hook (skipped warm hooks spawn nothing). Each phase
    independently uses the existing frozen ``timeout_seconds`` with immediate
    terminate/kill/reap on timeout; only the exception TYPE (never the
    message) crosses the process boundary. Lifecycle state is shared only
    through the declared ``writable_state_root``. This is NOT an OS security
    sandbox.
    """

    prepare: Callable[[AdapterRequest, Path], None] | None
    index: Callable[[AdapterRequest, Path], None] | None
    query: Callable[[AdapterRequest, Path], Any]

    def validate(self) -> "AdapterHooks":
        if self.prepare is not None and not callable(self.prepare):
            raise ContractError("prepare hook must be callable or None")
        if self.index is not None and not callable(self.index):
            raise ContractError("index hook must be callable or None")
        if not callable(self.query):
            raise ContractError("query hook must be callable")
        # Spawn-picklability: query hook must be a top-level function (have a
        # __module__ and __qualname__ without <locals>).
        q = self.query
        qual = getattr(q, "__qualname__", "")
        if "<locals>" in qual or "<lambda>" in qual:
            raise ContractError(
                "query hook must be a top-level function for spawn-picklability"
            )
        if self.prepare is not None:
            pq = getattr(self.prepare, "__qualname__", "")
            if "<locals>" in pq or "<lambda>" in pq:
                raise ContractError(
                    "prepare hook must be a top-level function"
                )
        if self.index is not None:
            iq = getattr(self.index, "__qualname__", "")
            if "<locals>" in iq or "<lambda>" in iq:
                raise ContractError(
                    "index hook must be a top-level function"
                )
        return self


def validate_descriptor_hooks(
    descriptor: AdapterDescriptor, hooks: AdapterHooks
) -> tuple[AdapterDescriptor, AdapterHooks]:
    """Cross-validate descriptor + hooks (v4 bounded closure).

    Enforces:
      * A lifecycle hook (prepare or index) requires the ``prepare_index``
        capability. A descriptor that declares no ``prepare_index`` capability
        cannot carry lifecycle hooks.
      * ``persistent_state_behavior=warm_reuse`` requires a real state-building
        hook (at least one of prepare/index must be present) so warm reuse can
        observe a previously-built marker rather than skip a no-op.
      * ``persistent_state_behavior=cold_rebuild`` requires the index hook
        (always rebuilds).
      * Hook absence cannot claim EXECUTABLE prepare_index: if the descriptor
        declares ``prepare_index`` as the DEFAULT capability (the adapter's
        primary capability), at least one lifecycle hook must be present. (If
        prepare_index is declared but legitimately skipped, no hook is
        required; the closed capability ledger enforces that no hook = the
        ledger must say ``legitimate_skip``.)
      * v7: ``execution_mode`` is exactly ``process_isolated``; the harness
        spawns a fresh spawn child per attempted prepare/index/query hook and
        independently enforces the existing frozen ``timeout_seconds``. It
        does NOT spawn a new execution framework and there is NO in-process
        code path. This is NOT an OS security sandbox.
    """
    descriptor.validate()
    hooks.validate()
    has_prepare = hooks.prepare is not None
    has_index = hooks.index is not None
    has_any_lifecycle = has_prepare or has_index
    declared_prepare_index = "prepare_index" in descriptor.capabilities
    # A lifecycle hook requires the prepare_index capability.
    if has_any_lifecycle and not declared_prepare_index:
        raise ContractError(
            "lifecycle hook present but descriptor does not declare "
            "prepare_index capability (hook requires prepare_index)"
        )
    # Hook absence cannot claim EXECUTABLE prepare_index: if prepare_index is
    # the DEFAULT capability, a lifecycle hook must be present to actually
    # execute it. (A non-default prepare_index capability may be legitimately
    # skipped with no hook present.)
    if (
        descriptor.default_capability == "prepare_index"
        and not has_any_lifecycle
    ):
        raise ContractError(
            "descriptor default_capability=prepare_index but neither prepare "
            "nor index hook is present (hook absence cannot claim executable "
            "prepare_index as the default capability)"
        )
    # warm_reuse needs a real state-building hook.
    if (
        descriptor.persistent_state_behavior == "warm_reuse"
        and not has_any_lifecycle
    ):
        raise ContractError(
            "persistent_state_behavior=warm_reuse requires a real "
            "state-building hook (prepare or index) so warm reuse can "
            "observe a previously-built marker"
        )
    # cold_rebuild needs index.
    if (
        descriptor.persistent_state_behavior == "cold_rebuild"
        and not has_index
    ):
        raise ContractError(
            "persistent_state_behavior=cold_rebuild requires the index "
            "hook (cold_rebuild always rebuilds the index)"
        )
    return descriptor, hooks


@dataclass(frozen=True)
class ResourceSample:
    """Harness-measured lifecycle/resource sample. Unavailable measurements
    stay explicit (None) rather than becoming zero. Only the harness constructs
    this; adapter-authored measurements are forbidden."""

    setup_seconds: float | None
    index_seconds: float | None
    query_seconds: float | None
    materialize_seconds: float | None
    render_seconds: float | None
    rss_bytes: int | None
    cpu_seconds: float | None

    def validate(self) -> "ResourceSample":
        for name in (
            "setup_seconds",
            "index_seconds",
            "query_seconds",
            "materialize_seconds",
            "render_seconds",
            "cpu_seconds",
        ):
            v = getattr(self, name)
            if v is not None:
                f = _require_float(name, v)
                if f < 0.0:
                    raise ContractError(f"{name} must be non-negative, got {f}")
        if self.rss_bytes is not None:
            ri = _require_int("rss_bytes", self.rss_bytes)
            if ri < 0:
                raise ContractError("rss_bytes must be >= 0")
        return self


@dataclass(frozen=True)
class SupportBinding:
    """Untrusted support reference: which evidence, which targets, what
    relation. ``parent_target_id`` is set for two_step support runs where the
    support references a parent target (not a local target index)."""

    evidence_index: int
    target_indices: tuple[int, ...]
    relation_kind: str
    parent_target_id: str | None = None

    def validate_shape(self) -> "SupportBinding":
        _require_int("support.evidence_index", self.evidence_index)
        if self.evidence_index < 0:
            raise ContractError("support.evidence_index must be >= 0")
        for ti in self.target_indices:
            _require_int("support.target_index", ti)
            if ti < 0:
                raise ContractError("support.target_index must be >= 0")
        _require_in_vocab("support.relation_kind", self.relation_kind, RELATION_KINDS)
        if self.parent_target_id is not None:
            _require_str("support.parent_target_id", self.parent_target_id, max_len=128)
        # At least one reference kind.
        if len(self.target_indices) == 0 and self.parent_target_id is None:
            raise ContractError("support must reference >= 1 target")
        # parent-bound support must not also carry local target indices.
        if self.parent_target_id is not None and len(self.target_indices) > 0:
            raise ContractError(
                "support with parent_target_id must not carry local target_indices"
            )
        return self


@dataclass(frozen=True)
class BindingProposal:
    """Untrusted target/support binding proposal (candidate references/roles
    only). The common code validates references against actual materialized
    evidence. This is the strategy-owned pack-assembly boundary so S0-S5 pack
    policies can differ while common materialization/rendering stays fixed.

    v6: the proposal carries a closed ``proposed_status``
    (``ready`` / ``uncertain`` / ``no_evidence``) plus ``status_reason``.
    Exact combinations are enforced:
      * ``ready`` requires >= 1 reference (target or support) AND no
        ``status_reason``;
      * ``uncertain`` requires a ``status_reason`` (may carry refs if
        unresolved ambiguity is intentionally represented, but its final pack
        must remain uncertain);
      * ``no_evidence`` requires a ``status_reason``, NO references, and is
        only valid when no evidence materialized.

    An ``ok`` adapter result MUST carry an explicit ``BindingProposal``. The
    harness derives the final pack from the proposal and actual evidence.
    """

    proposed_status: str
    target_evidence_indices: tuple[int, ...]
    support_bindings: tuple[SupportBinding, ...]
    status_reason: str | None = None

    def validate_shape(self) -> "BindingProposal":
        _require_in_vocab("proposed_status", self.proposed_status, PACK_STATUSES)
        seen: set[int] = set()
        for idx in self.target_evidence_indices:
            _require_int("target_evidence_index", idx)
            if idx < 0:
                raise ContractError("target_evidence_index must be >= 0")
            if idx in seen:
                raise ContractError(
                    f"duplicate target_evidence_index {idx}"
                )
            seen.add(idx)
        for sb in self.support_bindings:
            sb.validate_shape()
        if self.status_reason is not None:
            _require_str("binding.status_reason", self.status_reason, max_len=256)
        has_refs = (
            len(self.target_evidence_indices) > 0
            or len(self.support_bindings) > 0
        )
        # Exact combination enforcement.
        if self.proposed_status == "ready":
            if not has_refs:
                raise ContractError(
                    "proposed_status=ready requires >= 1 reference "
                    "(target or support)"
                )
            if self.status_reason is not None:
                raise ContractError(
                    "proposed_status=ready requires no status_reason"
                )
        elif self.proposed_status == "uncertain":
            if not self.status_reason:
                raise ContractError(
                    "proposed_status=uncertain requires a status_reason"
                )
        elif self.proposed_status == "no_evidence":
            if has_refs:
                raise ContractError(
                    "proposed_status=no_evidence requires no references"
                )
            if not self.status_reason:
                raise ContractError(
                    "proposed_status=no_evidence requires a status_reason"
                )
        return self


@dataclass(frozen=True)
class FallbackRecord:
    """Structured unavailable->executed fallback provenance."""

    unavailable_capability: str
    fallback_to: str  # capability name or "none"

    def validate_shape(self) -> "FallbackRecord":
        _require_in_vocab(
            "fallback.unavailable_capability", self.unavailable_capability, CAPABILITIES
        )
        if self.fallback_to != "none":
            _require_in_vocab("fallback.fallback_to", self.fallback_to, CAPABILITIES)
        return self


@dataclass(frozen=True)
class AdapterResult:
    status: str
    failure_category: str | None
    # ONE candidate collection (Candidate instances or dicts; harness validates).
    candidates: tuple[Any, ...]
    capability_ledger: Mapping[str, str]
    fallback_provenance: tuple[FallbackRecord, ...]
    # Adapter-authored resource_sample is FORBIDDEN; only the harness measures.
    # This field exists only so the closed-shape validator can reject it.
    resource_sample: ResourceSample | None = None
    binding_proposal: BindingProposal | None = None

    def validate_closed_shape(self) -> "AdapterResult":
        _require_in_vocab("status", self.status, RESULT_STATUSES)
        if self.failure_category is not None:
            _require_str("failure_category", self.failure_category, max_len=64)
        if not isinstance(self.candidates, tuple):
            raise ContractError("candidates must be a tuple (one collection)")
        if not isinstance(self.capability_ledger, Mapping):
            raise ContractError("capability_ledger must be a mapping")
        for cap, st in self.capability_ledger.items():
            _require_in_vocab("capability_ledger key", cap, CAPABILITIES)
            _require_in_vocab("capability_ledger status", st, CAPABILITY_STATUSES)
        if not isinstance(self.fallback_provenance, tuple):
            raise ContractError("fallback_provenance must be a tuple")
        for fr in self.fallback_provenance:
            if not isinstance(fr, FallbackRecord):
                raise ContractError("fallback_provenance items must be FallbackRecord")
            fr.validate_shape()
        # Reject adapter-authored resource measurements — only the harness
        # measures resources; adapter measurements are not trusted values.
        if self.resource_sample is not None:
            raise ContractError(
                "adapter-authored resource_sample is forbidden; only the "
                "harness measures resources (adapter measurements are not "
                "trusted values)"
            )
        if self.binding_proposal is not None:
            if not isinstance(self.binding_proposal, BindingProposal):
                raise ContractError("binding_proposal must be BindingProposal or None")
            self.binding_proposal.validate_shape()
        return self


# ---------------------------------------------------------------------------
# Frozen snapshot (byte-identical arm isolation + full visible-tree scan)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrozenSnapshot:
    root: Path
    visible_files: tuple[str, ...]
    per_file_digests: Mapping[str, str]
    manifest_digest: str
    visible_tree_digest: str
    writable_state_root: Path
    writable_state_root_id: str

    def visible_set(self) -> set[str]:
        return set(self.visible_files)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_manifest_digest(root: Path, visible_files: Iterable[str]) -> str:
    """Compute a digest over the sorted (path, sha256(bytes)) manifest.

    In-memory validation only; the digest is never emitted in the public
    aggregate report. Applies the COMMON safe path policy to each visible
    file before reading.
    """
    root_resolved = root.resolve()
    entries: list[tuple[str, str]] = []
    for rel in sorted(set(visible_files)):
        _validate_lexical_relative_path("visible_file", rel)
        full = root / rel
        _validate_safe_path_under_root(full, root_resolved, f"manifest:{rel}")
        if not full.is_file() or full.is_symlink():
            raise ContractError(f"visible file {rel!r} missing or symlink")
        data = full.read_bytes()
        entries.append((rel, _sha256_bytes(data)))
    canon = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32]


def _is_ancestor_or_equal(ancestor: Path, descendant: Path) -> bool:
    """True iff ``ancestor`` is an ancestor of (or equal to) ``descendant``
    by resolved-path comparison. Used by writable-state overlap rejection."""
    try:
        descendant.relative_to(ancestor)
    except ValueError:
        return False
    return True


def _writable_state_root_id(root_resolved: Path, wsr_resolved: Path) -> str:
    """Derive a deterministic ID from the actual writable-state root path
    relative to the snapshot root."""
    try:
        rel = wsr_resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        raise ContractError(
            "writable_state_root must be confined beneath snapshot.root"
        )
    return "wsr_" + hashlib.sha256(rel.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class _TreeEnumeration:
    """Full enumeration of the source tree beneath ``root`` (excluding the
    exact writable-state-root subtree when it exists as a real directory).

    Built by ``_enumerate_source_tree`` and shared by ``materialize_snapshot``
    and ``scan_visible_tree`` so the freeze and every post-freeze scan use ONE
    enumeration policy: os.walk(topdown=True, followlinks=False) with sorted
    names and onerror raising; symlink/reparse/special files and every
    traversal/lstat/open/read/stat error rejected; bytes hashed with
    before/after identity/size checks.

    v10: special files (FIFO/socket/device/directory/unknown) are rejected
    BEFORE ``read_bytes`` via ``stat.S_ISREG(st_mode)`` on the lstat result.
    After read, the after-lstat must still be regular with identical
    ``(st_dev, st_ino, st_mode, st_size)`` identity; replacement/mode/type/
    size changes reject.
    """

    entries: tuple[tuple[str, str, int], ...]  # (rel_path, sha256, size) sorted
    path_set: frozenset[str]
    digests: Mapping[str, str]  # path -> sha256
    sizes: Mapping[str, int]  # path -> size
    tree_digest: str


def _enumerate_source_tree(
    root: Path, writable_state_root: Path
) -> _TreeEnumeration:
    """Enumerate EVERY file beneath ``root`` using os.walk(topdown=True,
    followlinks=False) with sorted names and onerror raising. Reject
    symlink/reparse/special files and every traversal/lstat/open/read/stat
    error. Hash bytes and size with before/after identity/size checks.

    v10: special files (FIFO/socket/device/directory/unknown) are rejected
    BEFORE ``read_bytes`` via ``stat.S_ISREG(st_mode)`` on the lstat result.
    After read, the after-lstat must still be regular with identical
    ``(st_dev, st_ino, st_mode, st_size)`` identity; replacement/mode/type/
    size changes reject. Available identity fields are compared consistently;
    ``st_ino`` may be 0 on some Windows filesystems (both sides are 0, so
    the comparison still holds).

    The exact writable-state-root subtree is pruned from descent when it
    exists as a real directory; an absent WSR is not traversed (and not
    pruned). This is the ONE enumeration helper used by both
    ``materialize_snapshot`` (freeze) and ``scan_visible_tree`` (post-freeze
    unchanged assertion).
    """
    root_resolved = root.resolve()
    try:
        wsr_resolved = writable_state_root.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ContractError(
            f"writable_state_root cannot be resolved: {exc}"
        ) from exc
    # Determine whether the WSR exists as a real directory. If it exists but
    # is not a directory (a file/link) or is a reparse point, that is an error
    # (the WSR must be a real directory when present). An absent WSR is simply
    # not traversed (and not pruned). v10: lstat/stat errors fail CLOSED
    # (raise) rather than treating an unreadable entry as absent.
    wsr_exists = False
    try:
        wsr_exists = wsr_resolved.exists()
    except (OSError, RuntimeError) as exc:
        raise ContractError(
            f"writable_state_root cannot be stat-checked: {exc}"
        ) from exc
    if wsr_exists:
        if not wsr_resolved.is_dir():
            raise ContractError(
                "writable_state_root exists but is not a real directory"
            )
        if _is_reparse_or_link(wsr_resolved):
            raise ContractError(
                "writable_state_root is a symlink/reparse (rejected)"
            )

    entries: list[tuple[str, str, int]] = []

    def _on_error(err: OSError) -> None:
        # No silent walk errors: every traversal error is a contract failure.
        raise ContractError(
            f"source tree walk error at {err.filename!r}: {err}"
        ) from err

    for dirpath, dirnames, filenames in os.walk(
        root_resolved, topdown=True, followlinks=False, onerror=_on_error
    ):
        dp = Path(dirpath)
        try:
            dp_resolved = dp.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise ContractError(
                f"cannot resolve source directory {dp}: {exc}"
            ) from exc
        # Prune the exact writable-state-root subtree from descent. Only the
        # exact lexical WSR subtree may be excluded (when it exists).
        if wsr_exists and dp_resolved == wsr_resolved:
            dirnames[:] = []
            continue
        # Reject symlink/reparse directories (symlinked path components).
        kept_dirs: list[str] = []
        for dn in dirnames:
            full = dp / dn
            if _is_reparse_or_link(full):
                raise ContractError(
                    f"symlink/reparse directory found in source tree: {full}"
                )
            kept_dirs.append(dn)
        # Sort for deterministic descent.
        dirnames[:] = sorted(kept_dirs)
        for fn in sorted(filenames):
            full = dp / fn
            if _is_reparse_or_link(full):
                raise ContractError(
                    f"symlink/reparse file found in source tree: {full}"
                )
            # COMMON safe path policy: resolved confinement + components.
            _validate_safe_path_under_root(
                full, root_resolved, "source tree file")
            # v10: special-file rejection BEFORE read. Use os.lstat (no
            # follow) so the type check reflects the entry itself, not a
            # symlink target (symlinks were already rejected above, but
            # lstat also surfaces FIFO/socket/device/unknown types). Require
            # a regular file via stat.S_ISREG; reject FIFO/socket/device/
            # directory/unknown WITHOUT opening or reading the entry.
            try:
                st_before = os.lstat(full)
            except OSError as exc:
                raise ContractError(
                    f"cannot lstat source file {full}: {exc}"
                ) from exc
            if not stat.S_ISREG(st_before.st_mode):
                raise ContractError(
                    f"source tree entry {full} is not a regular file "
                    f"(mode=0{st_before.st_mode:o}); special files "
                    "(FIFO/socket/device/directory) rejected before read"
                )
            # Read bytes only after the regular-file check passes.
            try:
                data = full.read_bytes()
            except OSError as exc:
                raise ContractError(
                    f"cannot read source file {full}: {exc}"
                ) from exc
            # v10: After read, require still regular AND identical identity
            # (st_dev, st_ino, st_mode, st_size) — reject replacement, mode
            # change, type change, or size change (TOCTOU). st_ino may be 0
            # on some Windows filesystems; the comparison still holds because
            # both sides are 0. Available identity fields are compared
            # consistently; do not assume st_ino nonzero means unsupported.
            try:
                st_after = os.lstat(full)
            except OSError as exc:
                raise ContractError(
                    f"cannot re-lstat source file {full}: {exc}"
                ) from exc
            if not stat.S_ISREG(st_after.st_mode):
                raise ContractError(
                    f"source tree entry {full} changed type during read "
                    f"(before-mode=0{st_before.st_mode:o} "
                    f"after-mode=0{st_after.st_mode:o}); "
                    f"replacement rejected"
                )
            size = len(data)
            before_id = (
                st_before.st_dev, st_before.st_ino,
                st_before.st_mode, st_before.st_size)
            after_id = (
                st_after.st_dev, st_after.st_ino,
                st_after.st_mode, st_after.st_size)
            if before_id != after_id:
                raise ContractError(
                    f"source file {full} identity changed during read "
                    f"(before={before_id} after={after_id}); "
                    f"replacement/mode/type/size change rejected"
                )
            try:
                rel = full.relative_to(root_resolved).as_posix()
            except ValueError as exc:
                raise ContractError(
                    f"source file {full} not beneath root {root_resolved}"
                ) from exc
            entries.append((rel, _sha256_bytes(data), size))

    entries.sort()
    path_set = frozenset(e[0] for e in entries)
    digests: dict[str, str] = {e[0]: e[1] for e in entries}
    sizes: dict[str, int] = {e[0]: e[2] for e in entries}
    tree_canon = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    tree_digest = "tree_" + hashlib.sha256(
        tree_canon.encode("utf-8")).hexdigest()[:24]
    return _TreeEnumeration(
        entries=tuple(entries), path_set=path_set,
        digests=digests, sizes=sizes, tree_digest=tree_digest)


def _manifest_digest_from_enum(
    enum: _TreeEnumeration, decl_tuple: tuple[str, ...]
) -> str:
    """Build the manifest digest from the enumeration's already-hashed bytes
    (not declaration-only rereads). The manifest covers the declared visible
    files; after the equality check in ``materialize_snapshot`` the declared
    set exactly equals the enumerated set."""
    manifest_entries = sorted(
        (rel, enum.digests[rel]) for rel in decl_tuple)
    canon = json.dumps(manifest_entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def materialize_snapshot(
    root: Path,
    visible_files: Iterable[str],
    writable_state_root: Path | None = None,
) -> FrozenSnapshot:
    """Freeze a snapshot: record per-file digests, the manifest digest, and the
    full visible-tree digest. A separately declared writable-state root is
    created (empty) and excluded from the visible-tree scan. The writable-state
    root MUST be confined beneath the snapshot root.

    v9 closure (full initial source-tree freeze):
      * The declaration iterable is materialized ONCE (no ``set`` collapse).
        Nonempty strings are required; duplicate declarations are rejected
        (do NOT ``set`` collapse). Declarations are kept meaningful and are
        NEVER derived/repaired from the filesystem.
      * Every visible path is lexical-validated before any read or directory
        creation.
      * The root must preexist as a real non-link/non-reparse directory.
      * The writable-state root is validated WITHOUT being created: strict
        in-root confinement, no symlink/junction/reparse components, no
        overlap (ancestor/equal or contained) with any declared visible file;
        an existing writable-state root must be a real directory.
      * The FULL source tree is enumerated (via ``_enumerate_source_tree``)
        BEFORE ``mkdir``. Exact set equality declarations == enumeration is
        required: any undeclared source file OR any missing declared file
        rejects. Only the exact lexical WSR subtree may be excluded (when it
        exists); an absent WSR is not traversed because absent.
      * Manifest/tree digests are built from this enumeration, not
        declaration-only rereads.
      * ONLY after set equality does the harness create the writable-state
        root, then revalidate identity/confinement/type.
    """
    # 1. Materialize declaration iterable ONCE (no set collapse).
    decl_list = list(visible_files)
    if not decl_list:
        raise ContractError("snapshot must have >= 1 visible file")
    # 2. Require nonempty strings; reject duplicate declarations.
    seen_decl: set[str] = set()
    for rel in decl_list:
        if not isinstance(rel, str) or not rel:
            raise ContractError("visible_file must be a non-empty str")
        _validate_lexical_relative_path("visible_file", rel)
        if rel in seen_decl:
            raise ContractError(
                f"duplicate visible_file declaration {rel!r} "
                "(declarations are not set-collapsed)"
            )
        seen_decl.add(rel)
    decl_tuple = tuple(decl_list)
    # 3. Root must preexist as a real non-link/non-reparse directory.
    root_resolved = root.resolve()
    try:
        root_exists = root.exists()
    except (OSError, RuntimeError) as exc:
        # v10: lstat/stat error fails CLOSED (raise) rather than treating an
        # unreadable root as absent.
        raise ContractError(
            f"snapshot root {root} cannot be stat-checked: {exc}"
        ) from exc
    if not root_exists or not root.is_dir():
        raise ContractError(
            f"snapshot root {root} must preexist as a real directory"
        )
    if _is_reparse_or_link(root):
        raise ContractError(
            f"snapshot root {root} is a symlink/reparse (rejected)"
        )
    # 4. Resolve writable_state_root WITHOUT creating it; validate confinement
    # before mkdir. If None, default to root/.pb_writable_state.
    if writable_state_root is None:
        writable_state_root = root / ".pb_writable_state"
    try:
        wsr_resolved = writable_state_root.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ContractError(
            f"writable_state_root cannot be resolved: {exc}"
        ) from exc
    # Strict in-root confinement (rejected before creation).
    try:
        wsr_resolved.relative_to(root_resolved)
    except ValueError:
        raise ContractError(
            "writable_state_root must be confined beneath snapshot.root "
            "(rejected before creation)"
        )
    # COMMON safe path policy: walk ORIGINAL LEXICAL components to reject
    # in-root parent symlinks (a symlinked parent whose target is still
    # inside root).
    _validate_safe_path_under_root(
        writable_state_root, root_resolved, "writable_state_root.pre_create")
    # Writable-state root must NOT equal the source root.
    if wsr_resolved == root_resolved:
        raise ContractError(
            "writable_state_root must not equal source root "
            "(rejected before creation)"
        )
    # Overlap rejection (all checks BEFORE mkdir): writable-state root must
    # NOT be an ancestor/equal of any visible path; no visible path may be
    # located inside the writable-state root.
    for rel in decl_tuple:
        vis_full = root / rel
        try:
            vis_resolved = vis_full.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise ContractError(
                f"visible file {rel!r} cannot be resolved: {exc}"
            ) from exc
        if _is_ancestor_or_equal(wsr_resolved, vis_resolved):
            raise ContractError(
                f"writable_state_root {wsr_resolved} is an ancestor of "
                f"(or equal to) visible path {rel!r} "
                f"({vis_resolved}); rejected before creation"
            )
        if _is_ancestor_or_equal(vis_resolved, wsr_resolved):
            raise ContractError(
                f"visible path {rel!r} ({vis_resolved}) is an ancestor of "
                f"(or equal to) writable_state_root {wsr_resolved}; "
                f"rejected before creation"
            )
    # Existing writable-state root must be a real directory (if it exists).
    try:
        wsr_exists_pre = wsr_resolved.exists()
    except (OSError, RuntimeError) as exc:
        # v10: lstat/stat error fails CLOSED (raise) rather than treating an
        # unreadable WSR as absent.
        raise ContractError(
            f"existing writable_state_root {wsr_resolved} cannot be "
            f"stat-checked: {exc}"
        ) from exc
    if wsr_exists_pre:
        if not wsr_resolved.is_dir():
            raise ContractError(
                "existing writable_state_root must be a real directory"
            )
        if _is_reparse_or_link(wsr_resolved):
            raise ContractError(
                "existing writable_state_root is a symlink/reparse (rejected)"
            )
    # 5. Enumerate the FULL source tree BEFORE mkdir. The WSR is absent at
    # this point (created only after equality), so it is not traversed. If the
    # WSR already exists (prior run), its exact subtree is excluded.
    enum = _enumerate_source_tree(root_resolved, writable_state_root)
    # 6. Exact set equality declarations == enumeration.
    enum_paths = set(enum.path_set)
    missing = seen_decl - enum_paths  # declared but not on disk
    undeclared = enum_paths - seen_decl  # on disk but not declared
    if missing:
        raise ContractError(
            f"declared visible files missing from source tree: {sorted(missing)}"
        )
    if undeclared:
        raise ContractError(
            f"undeclared source files present in tree: {sorted(undeclared)}"
        )
    # 7. Build manifest/tree digests from this enumeration (not rereads).
    manifest = _manifest_digest_from_enum(enum, decl_tuple)
    visible_tree_digest = enum.tree_digest
    manifest_digest = "snap_" + manifest[:24]
    source_visibility_digest = "vis_" + hashlib.sha256(
        ("frozen_visible:" + manifest).encode("utf-8")
    ).hexdigest()[:24]
    # 8. ONLY after equality, create the writable-state root, then revalidate.
    writable_state_root.mkdir(parents=True, exist_ok=True)
    if not writable_state_root.is_dir():
        raise ContractError("writable_state_root creation failed")
    # Revalidate identity/confinement/type after creation (defense in depth).
    _validate_safe_path_under_root(
        writable_state_root, root_resolved, "writable_state_root.post_create")
    if _is_reparse_or_link(writable_state_root):
        raise ContractError(
            "writable_state_root became a symlink/reparse after creation"
        )
    wsr_id = _writable_state_root_id(root_resolved, wsr_resolved)
    per_file: dict[str, str] = {rel: enum.digests[rel] for rel in decl_tuple}
    return FrozenSnapshot(
        root=root,
        visible_files=decl_tuple,
        per_file_digests=per_file,
        manifest_digest=manifest_digest,
        visible_tree_digest=visible_tree_digest,
        writable_state_root=writable_state_root,
        writable_state_root_id=wsr_id,
    )


def snapshot_source_visibility_digest(snapshot: FrozenSnapshot) -> str:
    return "vis_" + hashlib.sha256(
        ("frozen_visible:" + snapshot.manifest_digest).encode("utf-8")
    ).hexdigest()[:24]


def scan_visible_tree(snapshot: FrozenSnapshot) -> None:
    """Full visible-tree scan via the SAME ``_enumerate_source_tree`` enumerator
    used by ``materialize_snapshot``. Compares the full (path, digest, size)
    tuple, the path set, the per-file digest, and the per-file size against the
    frozen snapshot. Rejects additions, deletes (missing frozen files), content
    mutations (digest mismatch), size changes, and symlink/reparse/special
    files. No silent walk errors (onerror raises).

    The exact writable-state-root subtree is excluded (when it exists as a real
    directory); WSR mutation is allowed and not treated as a source mutation.
    """
    root = snapshot.root
    root_resolved = root.resolve()
    enum = _enumerate_source_tree(root_resolved, snapshot.writable_state_root)
    frozen = set(snapshot.visible_files)
    enum_paths = set(enum.path_set)
    # Additions: a file under root that is not a frozen visible file (and not
    # inside the writable-state root, which was pruned). Renames surface as a
    # delete (frozen file gone) plus an addition (new path present).
    extra = enum_paths - frozen
    if extra:
        raise ContractError(
            f"unexpected files added to visible tree: {sorted(extra)}"
        )
    # Deletes: a frozen file missing.
    missing = frozen - enum_paths
    if missing:
        raise ContractError(
            f"visible files missing from source tree: {sorted(missing)}"
        )
    # Content mutation + size: every enumerated file must match the frozen
    # digest AND size. The tree digest (path+digest+size tuple) is the
    # structural equality check; the per-file checks give clear errors.
    for rel in snapshot.visible_files:
        if enum.digests.get(rel) != snapshot.per_file_digests.get(rel):
            raise ContractError(
                f"visible file {rel!r} content changed (mutation detected)"
            )
    if enum.tree_digest != snapshot.visible_tree_digest:
        raise ContractError(
            f"visible tree digest mismatch (mutation detected): "
            f"{enum.tree_digest} != {snapshot.visible_tree_digest}"
        )


def assert_snapshot_unchanged(snapshot: FrozenSnapshot) -> None:
    """Full visible-tree scan. Raises on any mutation/add/delete/rename."""
    scan_visible_tree(snapshot)


def validate_snapshot_binding(run_spec: BakeoffRunSpec, snapshot: FrozenSnapshot) -> None:
    """Bind the run spec to the actual snapshot digests. The run spec's
    declared manifest/visibility/visible-tree digests must match the actual
    frozen snapshot."""
    run_spec.validate()
    if run_spec.snapshot_manifest_digest != snapshot.manifest_digest:
        raise ContractError(
            "run_spec.snapshot_manifest_digest does not match the actual "
            "frozen snapshot (snapshot not bound to request)"
        )
    if run_spec.source_visibility_digest != snapshot_source_visibility_digest(snapshot):
        raise ContractError(
            "run_spec.source_visibility_digest does not match the actual "
            "frozen snapshot"
        )
    if run_spec.visible_tree_digest != snapshot.visible_tree_digest:
        raise ContractError(
            "run_spec.visible_tree_digest does not match the actual frozen snapshot"
        )


def validate_execution_root_binding(
    run_spec: BakeoffRunSpec,
    snapshot: FrozenSnapshot,
    isolated_root: Path,
) -> None:
    """Require resolved execution root equals snapshot root and writable-state
    root matches its declared ID/confinement. Adversarial mismatched-root
    execution is rejected.

    COMMON safe path policy (v4): the writable-state root is validated via
    ``_validate_safe_path_under_root`` (lexical + resolved confinement + all
    components checked for symlinks).
    """
    run_spec.validate()
    if isolated_root.resolve() != snapshot.root.resolve():
        raise ContractError(
            f"isolated_root {isolated_root.resolve()} != snapshot.root "
            f"{snapshot.root.resolve()} (execution root binding)"
        )
    wsr = snapshot.writable_state_root
    wsr_resolved = wsr.resolve(strict=False)
    root_resolved = snapshot.root.resolve()
    try:
        wsr_resolved.relative_to(root_resolved)
    except ValueError:
        raise ContractError(
            "writable_state_root must be confined beneath snapshot.root"
        )
    # COMMON safe path policy: walk components to reject parent symlinks.
    _validate_safe_path_under_root(wsr, root_resolved, "writable_state_root")
    if run_spec.writable_state_root_id != snapshot.writable_state_root_id:
        raise ContractError(
            f"run_spec.writable_state_root_id "
            f"{run_spec.writable_state_root_id!r} does not match actual "
            f"writable-state root id {snapshot.writable_state_root_id!r}"
        )


# ---------------------------------------------------------------------------
# Budget estimator + usage (harness-recomputed)
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Deterministic named ceiling estimator (char_div_4_ceil_v3).

    Uses a documented CEILING estimate so over-budget packs fail rather than
    silently pass on a floor rounding.
    """
    _require_str("estimate_input", text, max_len=10_000_000)
    if not text:
        return 0
    return math.ceil(len(text) / 4)


@dataclass(frozen=True)
class BudgetUsage:
    candidate_count: int
    evidence_count: int
    target_count: int
    support_count: int
    rendered_chars: int
    rendered_bytes: int
    rendered_estimate: int
    episode_step_count: int
    episode_estimate_used: int

    def validate_against(self, caps: BudgetCaps) -> "BudgetUsage":
        if self.candidate_count > caps.max_candidates:
            raise ContractError(
                f"candidate_count {self.candidate_count} > cap "
                f"{caps.max_candidates}"
            )
        if self.evidence_count > caps.max_evidence:
            raise ContractError(
                f"evidence_count {self.evidence_count} > cap {caps.max_evidence}"
            )
        if self.target_count > caps.max_targets:
            raise ContractError(
                f"target_count {self.target_count} > cap {caps.max_targets}"
            )
        if self.support_count > caps.max_support:
            raise ContractError(
                f"support_count {self.support_count} > cap {caps.max_support}"
            )
        if self.rendered_chars > caps.max_render_chars:
            raise ContractError(
                f"rendered_chars {self.rendered_chars} > cap "
                f"{caps.max_render_chars}"
            )
        if self.rendered_bytes > caps.max_render_bytes:
            raise ContractError(
                f"rendered_bytes {self.rendered_bytes} > cap "
                f"{caps.max_render_bytes}"
            )
        if self.rendered_estimate > caps.max_render_estimate:
            raise ContractError(
                f"rendered_estimate {self.rendered_estimate} > cap "
                f"{caps.max_render_estimate}"
            )
        if self.episode_step_count > caps.episode_step_cap:
            raise ContractError(
                f"episode_step_count {self.episode_step_count} > cap "
                f"{caps.episode_step_cap}"
            )
        if self.episode_estimate_used > caps.episode_estimate_cap:
            raise ContractError(
                f"episode_estimate_used {self.episode_estimate_used} > cap "
                f"{caps.episode_estimate_cap}"
            )
        return self


# ---------------------------------------------------------------------------
# BakeoffVerifiedEvidence (bakeoff-only schema; harness-only; common
# materializer constructs it)
# ---------------------------------------------------------------------------

# Module-private token. Only materialize_candidates holds a reference.
_HARNESS_TOKEN = object()


@dataclass(frozen=True)
class BakeoffVerifiedEvidence:
    """Bakeoff-only verified evidence. Constructed ONLY by the common harness
    materializer from a single source-byte read.

    This is NOT production EvidenceCore. It is a bakeoff-only schema using
    unambiguous SHA-256 naming:
      * ``source_sha256`` — SHA-256 of the FULL source file bytes;
      * ``excerpt_sha256`` — SHA-256 of the excerpt bytes;
      * ``why`` — tuple[str, ...] (NOT a production ``why[]`` list);
      * ``excerpt`` — the actual selected source excerpt;
      * ``freshness`` — ``"frozen"`` (bakeoff current-source marker).

    Exact production EvidenceCore projection (``content_sha`` BLAKE3,
    ``why[]`` list, production channels) is DEFERRED to landing integration.
    Bakeoff results CANNOT be passed directly as production EvidenceCore. No
    BLAKE3 dependency is added.
    """

    evidence_kind: str  # "verified_current"
    path: str
    start_line: int
    end_line: int
    source_sha256: str  # sha256 of the FULL source file bytes
    excerpt: str  # actual selected source excerpt (lines start..end)
    excerpt_sha256: str  # sha256 of the excerpt bytes
    score: float  # the candidate score carried forward
    why: tuple[str, ...]  # tuple of reasons (NOT a production why[] list)
    channels: frozenset[str]
    freshness: str  # "frozen"
    byte_count: int  # full file bytes
    char_count: int  # full file chars
    line_count: int  # full file lines
    materializer_version: str
    materialized_at_step: int
    _token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _HARNESS_TOKEN:
            raise ContractError(
                "BakeoffVerifiedEvidence may only be constructed by the common "
                "harness materializer (materialize_candidates); adapter-"
                "supplied verified claims are forbidden"
            )
        self.validate()

    def validate(self) -> "BakeoffVerifiedEvidence":
        if self.evidence_kind != "verified_current":
            raise ContractError(
                f"evidence_kind must be 'verified_current', got {self.evidence_kind!r}"
            )
        validate_relative_path(self.path, [self.path])  # shape-only check
        validate_line_range(self.start_line, self.end_line)
        _require_str("source_sha256", self.source_sha256, max_len=128)
        _require_str("excerpt_sha256", self.excerpt_sha256, max_len=128)
        _require_finite_score("score", self.score)
        # why must be a tuple of str (NOT a scalar; NOT a production why[] list).
        if not isinstance(self.why, tuple):
            raise ContractError(
                f"why must be a tuple[str, ...], got {type(self.why).__name__}"
            )
        for w in self.why:
            _require_str("why[item]", w, max_len=128)
        ch = _require_frozenset_str("channels", self.channels, CHANNELS)
        if self.freshness != "frozen":
            raise ContractError(f"freshness must be 'frozen', got {self.freshness!r}")
        _require_int("byte_count", self.byte_count)
        _require_int("char_count", self.char_count)
        _require_int("line_count", self.line_count)
        _require_str("materializer_version", self.materializer_version, max_len=64)
        _require_int("materialized_at_step", self.materialized_at_step)
        if self._token is not _HARNESS_TOKEN:
            raise ContractError(
                "BakeoffVerifiedEvidence may only be constructed by the common "
                "harness materializer (materialize_candidates); adapter-"
                "supplied verified claims are forbidden"
            )
        # Rebind channels to the validated frozenset.
        object.__setattr__(self, "channels", ch)
        return self


# ---------------------------------------------------------------------------
# ContextPack
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PackTarget:
    evidence_index: int
    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class PackSupport:
    evidence_index: int
    target_indices: tuple[int, ...]
    relation_kind: str
    path: str
    start_line: int
    end_line: int
    parent_target_id: str | None = None


@dataclass(frozen=True)
class ContextPack:
    pack_status: str
    status_reason: str | None
    targets: tuple[PackTarget, ...]
    support: tuple[PackSupport, ...]
    diagnostics: tuple[str, ...]
    budget_usage: BudgetUsage
    rendered_context: str  # actual rendered source context
    operation: str = "context"

    def validate(
        self,
        evidence: tuple["BakeoffVerifiedEvidence", ...],
        caps: BudgetCaps,
        candidate_count: int,
        materialize_step: int,
        parent_episode_estimate_used: int,
    ) -> "ContextPack":
        """v6: validate against the ACTUAL bakeoff evidence tuple and explicit
        harness execution values. Every target/support path+range is verified
        against its referenced evidence; the rendered context is
        deterministically rerendered and compared; every ``BudgetUsage`` field
        is recomputed from the actual evidence + explicit inputs. No
        externally forged ``BudgetUsage`` field can pass.
        """
        _require_in_vocab("pack_status", self.pack_status, PACK_STATUSES)
        _require_in_vocab("pack.operation", self.operation, OPERATIONS)
        if self.status_reason is not None:
            _require_str("status_reason", self.status_reason, max_len=256)
        # ready requires >= 1 verified target (one_shot) OR >= 1 parent-bound
        # support item (two_step support run).
        if self.pack_status == "ready":
            has_target = len(self.targets) >= 1
            has_parent_support = any(
                s.parent_target_id is not None for s in self.support
            )
            if not (has_target or has_parent_support):
                raise ContractError(
                    "pack_status=ready requires >= 1 target or parent-bound support"
                )
        if self.pack_status == "no_evidence":
            if len(self.targets) != 0 or len(self.support) != 0:
                raise ContractError(
                    "pack_status=no_evidence must have no targets and no support"
                )
            if not self.status_reason:
                raise ContractError(
                    "pack_status=no_evidence requires a status_reason"
                )
        if self.pack_status == "uncertain":
            if not self.status_reason:
                raise ContractError(
                    "pack_status=uncertain requires a status_reason explaining "
                    "the unresolved binding"
                )
        # v6: verify EVERY target path+range equals its referenced evidence.
        seen_target_evidence: set[int] = set()
        for t in self.targets:
            _require_int("target.evidence_index", t.evidence_index)
            if not (0 <= t.evidence_index < len(evidence)):
                raise ContractError(
                    f"target evidence_index {t.evidence_index} out of range "
                    f"(evidence_count={len(evidence)})"
                )
            if t.evidence_index in seen_target_evidence:
                raise ContractError(
                    f"duplicate target evidence_index {t.evidence_index}"
                )
            seen_target_evidence.add(t.evidence_index)
            ev = evidence[t.evidence_index]
            if t.path != ev.path:
                raise ContractError(
                    f"target path {t.path!r} != evidence path {ev.path!r} "
                    f"(forged target path rejected)"
                )
            if t.start_line != ev.start_line or t.end_line != ev.end_line:
                raise ContractError(
                    f"target range {t.start_line}-{t.end_line} != evidence "
                    f"range {ev.start_line}-{ev.end_line} for {t.path!r} "
                    f"(forged target range rejected)"
                )
        # v6: verify EVERY support path+range equals its referenced evidence.
        target_index_set = {i for i in range(len(self.targets))}
        seen_support_evidence: set[int] = set()
        for sp in self.support:
            _require_int("support.evidence_index", sp.evidence_index)
            if not (0 <= sp.evidence_index < len(evidence)):
                raise ContractError(
                    f"support evidence_index {sp.evidence_index} out of range"
                )
            if sp.evidence_index in seen_target_evidence:
                raise ContractError(
                    f"support evidence_index {sp.evidence_index} is also a target "
                    "(an evidence cannot be both target and support)"
                )
            if sp.evidence_index in seen_support_evidence:
                raise ContractError(
                    f"duplicate support evidence_index {sp.evidence_index} "
                    "(duplicate source not rendered twice for roles)"
                )
            seen_support_evidence.add(sp.evidence_index)
            _require_in_vocab("support.relation_kind", sp.relation_kind, RELATION_KINDS)
            if sp.parent_target_id is not None:
                _require_str(
                    "support.parent_target_id", sp.parent_target_id, max_len=128
                )
                if len(sp.target_indices) > 0:
                    raise ContractError(
                        "parent-bound support must not carry local target_indices"
                    )
            else:
                if len(sp.target_indices) == 0:
                    raise ContractError("support must reference >= 1 target")
                for ti in sp.target_indices:
                    _require_int("support.target_index", ti)
                    if ti not in target_index_set:
                        raise ContractError(
                            f"support target_index {ti} not a valid target"
                        )
            ev = evidence[sp.evidence_index]
            if sp.path != ev.path:
                raise ContractError(
                    f"support path {sp.path!r} != evidence path {ev.path!r} "
                    f"(forged support path rejected)"
                )
            if sp.start_line != ev.start_line or sp.end_line != ev.end_line:
                raise ContractError(
                    f"support range {sp.start_line}-{sp.end_line} != evidence "
                    f"range {ev.start_line}-{ev.end_line} for {sp.path!r} "
                    f"(forged support range rejected)"
                )
        # v6: deterministically RERENDER the context and compare EXACT.
        expected_render = _render_context(
            tuple(evidence), tuple(self.targets), tuple(self.support)
        )
        if self.rendered_context != expected_render:
            raise ContractError(
                "rendered_context does not match the deterministically "
                "rerendered context (forged render rejected)"
            )
        # v6: recompute EVERY budget field from actual evidence + explicit
        # harness inputs and compare. No externally forged field can pass.
        exp_rendered_chars = len(expected_render)
        exp_rendered_bytes = len(expected_render.encode("utf-8"))
        exp_rendered_estimate = estimate_tokens(expected_render)
        if (
            self.operation == "support"
        ):
            exp_episode_estimate_used = (
                parent_episode_estimate_used + exp_rendered_estimate
            )
        else:
            exp_episode_estimate_used = exp_rendered_estimate
        bu = self.budget_usage
        if bu.candidate_count != candidate_count:
            raise ContractError(
                f"budget_usage.candidate_count {bu.candidate_count} != explicit "
                f"harness candidate_count {candidate_count}"
            )
        if bu.evidence_count != len(evidence):
            raise ContractError(
                f"budget_usage.evidence_count {bu.evidence_count} != actual "
                f"evidence count {len(evidence)}"
            )
        if bu.target_count != len(self.targets):
            raise ContractError(
                f"budget_usage.target_count {bu.target_count} != actual "
                f"target count {len(self.targets)}"
            )
        if bu.support_count != len(self.support):
            raise ContractError(
                f"budget_usage.support_count {bu.support_count} != actual "
                f"support count {len(self.support)}"
            )
        if bu.rendered_chars != exp_rendered_chars:
            raise ContractError(
                f"budget_usage.rendered_chars {bu.rendered_chars} != recomputed "
                f"{exp_rendered_chars} (forged rendered_chars rejected)"
            )
        if bu.rendered_bytes != exp_rendered_bytes:
            raise ContractError(
                f"budget_usage.rendered_bytes {bu.rendered_bytes} != recomputed "
                f"{exp_rendered_bytes} (forged rendered_bytes rejected)"
            )
        if bu.rendered_estimate != exp_rendered_estimate:
            raise ContractError(
                f"budget_usage.rendered_estimate {bu.rendered_estimate} != "
                f"recomputed {exp_rendered_estimate} "
                f"(forged rendered_estimate rejected)"
            )
        if bu.episode_step_count != materialize_step:
            raise ContractError(
                f"budget_usage.episode_step_count {bu.episode_step_count} != "
                f"explicit materialize_step {materialize_step}"
            )
        if bu.episode_estimate_used != exp_episode_estimate_used:
            raise ContractError(
                f"budget_usage.episode_estimate_used {bu.episode_estimate_used} "
                f"!= recomputed {exp_episode_estimate_used} "
                f"(forged episode_estimate_used rejected)"
            )
        # Budget usage validated against caps.
        self.budget_usage.validate_against(caps)
        # rendered_context must be a str (actual rendered context).
        _require_str("rendered_context", self.rendered_context, max_len=10_000_000)
        return self


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------


def validate_request(request: AdapterRequest) -> AdapterRequest:
    """Validate an adapter request strictly. Raises ContractError on any
    closed-schema, type, range, vocab, lineage, or budget violation."""
    return request.validate()


def validate_adapter_result(
    result: AdapterResult,
    request: AdapterRequest,
    descriptor: AdapterDescriptor,
    snapshot: FrozenSnapshot,
) -> tuple[AdapterResult, tuple[Candidate, ...]]:
    """Validate an adapter result against the request, descriptor, and frozen
    snapshot. Returns (result, validated_candidates).

    Rejects: exception/nonzero/malformed/timeout/partial outputs (they become
    explicit failures and cannot produce packs); duplicate candidate cells;
    adapter-supplied excerpt/hash/freshness/verified; capability ledger keys
    that do not EXACTLY equal descriptor capabilities; failed default
    masquerading as success; adapter identity/provenance mismatch; candidate
    channels outside the descriptor-declared output channels; structurally
    invalid fallback provenance; adapter id/version mismatch with descriptor;
    task language not in descriptor-supported languages; adapter-authored
    resource_sample.

    v8: every ``status=ok`` result MUST carry an explicit ``BindingProposal``
    (``binding_proposal is not None``), including zero candidate/evidence
    results. There is no "proposal, if present" path for ok results: zero-
    candidate/evidence results must explicitly propose ``no_evidence``. The
    proposal is shape-validated here (defense in depth) and again in
    ``build_context_pack`` before the evidence branch.
    """
    result.validate_closed_shape()
    descriptor.validate()

    # Bind request adapter id/version to descriptor id/version.
    if request.adapter_id != descriptor.adapter_id:
        raise ContractError(
            f"request.adapter_id {request.adapter_id!r} != "
            f"descriptor.adapter_id {descriptor.adapter_id!r}"
        )
    if request.adapter_version != descriptor.adapter_version:
        raise ContractError(
            f"request.adapter_version {request.adapter_version!r} != "
            f"descriptor.adapter_version {descriptor.adapter_version!r}"
        )
    # Task language must be in descriptor-supported languages.
    if request.run_spec.task.language_family not in descriptor.supported_languages:
        raise ContractError(
            f"task language_family {request.run_spec.task.language_family!r} "
            f"not in descriptor supported_languages "
            f"{sorted(descriptor.supported_languages)}"
        )

    # Exact capability-ledger key equality (no missing, no extra keys).
    ledger = dict(result.capability_ledger)
    declared = set(descriptor.capabilities)
    ledger_keys = set(ledger.keys())
    missing = declared - ledger_keys
    extra = ledger_keys - declared
    if missing:
        raise ContractError(
            f"capability ledger missing statuses for {sorted(missing)} "
            "(exact key equality; no silent degeneration)"
        )
    if extra:
        raise ContractError(
            f"capability ledger has extra keys {sorted(extra)}; common harness "
            "capabilities are not adapter ledger entries (exact key equality)"
        )

    # Only ``ok`` may proceed to materialization/pack.
    if result.status not in PACK_OK_STATUSES:
        if result.status in {"failed", "timeout", "malformed", "partial"}:
            if not result.failure_category:
                raise ContractError(
                    f"status={result.status} requires a failure_category"
                )
            if len(result.candidates) > 0:
                raise ContractError(
                    f"status={result.status} must not carry candidates "
                    "(failures cannot produce packs)"
                )
        return result, ()

    # status == ok: v8 requires an EXPLICIT BindingProposal on every ok
    # result, including zero candidate/evidence results. There is no
    # "proposal, if present" path; zero-candidate/evidence results must
    # explicitly propose no_evidence (validated here as defense in depth and
    # again in build_context_pack before the evidence branch).
    if result.binding_proposal is None:
        raise ContractError(
            "status=ok requires an explicit BindingProposal "
            "(zero candidate/evidence results must propose no_evidence; "
            "no proposal supplied)"
        )
    result.binding_proposal.validate_shape()

    # status == ok: validate every candidate against the frozen snapshot.
    validated: list[Candidate] = []
    seen_cells: set[tuple[str, int, int]] = set()
    for item in result.candidates:
        cand = validate_candidate_obj(item, snapshot.visible_files)
        # adapter identity/provenance must match the descriptor.
        if cand.adapter_provenance != descriptor.adapter_id:
            raise ContractError(
                f"candidate adapter_provenance {cand.adapter_provenance!r} != "
                f"descriptor adapter_id {descriptor.adapter_id!r}"
            )
        # candidate channels must be a subset of descriptor-declared output
        # channels.
        undeclared = set(cand.channels) - set(descriptor.output_channels)
        if undeclared:
            raise ContractError(
                f"candidate channels {sorted(undeclared)} not in descriptor "
                "output_channels (descriptor-declared channels)"
            )
        cell = cand.normalized_cell()
        if cell in seen_cells:
            raise ContractError(
                f"duplicate candidate cell {cell} (duplicate cells rejected)"
            )
        seen_cells.add(cell)
        validated.append(cand)
    # Candidate cap.
    if len(validated) > request.run_spec.caps.max_candidates:
        raise ContractError(
            f"candidate count {len(validated)} > cap "
            f"{request.run_spec.caps.max_candidates}"
        )

    # If the default capability failed/timed out/unsupported, the overall
    # status must not be ``ok``.
    if descriptor.default_capability is not None:
        dst = ledger.get(descriptor.default_capability)
        if dst in UNAVAILABLE_STATUSES and result.status == "ok":
            raise ContractError(
                f"default capability {descriptor.default_capability!r} status "
                f"{dst!r} cannot masquerade as ok (no silent degeneration)"
            )

    # v6: Structured fallback provenance (per-result; descriptor
    # ``fallback_chain`` was REMOVED — this is the sole fallback contract).
    # Each referenced cap must be declared; unavailable_capability must have an
    # unavailable status; fallback_to must be executed or "none"; no duplicate
    # unavailable capability; exactly one record for each unavailable
    # capability that falls back (fallback_to != "none").
    seen_unavailable: set[str] = set()
    for fr in result.fallback_provenance:
        # Each referenced cap must be a declared descriptor capability.
        if fr.unavailable_capability not in declared:
            raise ContractError(
                f"fallback record unavailable_capability "
                f"{fr.unavailable_capability!r} not in declared capabilities"
            )
        if fr.fallback_to != "none" and fr.fallback_to not in declared:
            raise ContractError(
                f"fallback record fallback_to {fr.fallback_to!r} not in "
                f"declared capabilities"
            )
        if fr.unavailable_capability in seen_unavailable:
            raise ContractError(
                f"duplicate fallback record for unavailable capability "
                f"{fr.unavailable_capability!r}"
            )
        seen_unavailable.add(fr.unavailable_capability)
        ust = ledger.get(fr.unavailable_capability)
        if ust not in UNAVAILABLE_STATUSES:
            raise ContractError(
                f"fallback record unavailable_capability "
                f"{fr.unavailable_capability!r} has status {ust!r}; must be "
                f"unavailable {sorted(UNAVAILABLE_STATUSES)}"
            )
        if fr.fallback_to != "none":
            fst = ledger.get(fr.fallback_to)
            if fst != "executed":
                raise ContractError(
                    f"fallback record fallback_to {fr.fallback_to!r} has status "
                    f"{fst!r}; must be executed (structured unavailable->executed)"
                )

    return result, tuple(validated)


def validate_capability_ledger_honesty(
    result: AdapterResult,
    request: AdapterRequest,
    attempt_prepare: bool,
    attempt_index: bool,
) -> None:
    """v6: cross-check the capability ledger against ACTUAL execution. Called
    by the harness (``run_adapter``) after ``validate_adapter_result`` for
    results that went through the query hook.

    Cross-checks:
      * actual prepare/index attempted successfully => ``prepare_index``
        executed; neither attempted => it must NOT claim ``executed``
        (``legitimate_skip`` acceptable for a declared capability);
      * target refs (binding target_evidence_indices non-empty) =>
        ``target_binding`` executed;
      * support refs (binding support_bindings non-empty) =>
        ``support_expansion`` executed;
      * support operation producing support (operation == "support" AND
        binding has support) => ``two_step_support`` executed;
      * Conversely: executed ``target_binding`` / ``support_expansion`` /
        ``two_step_support`` must correspond to actual output/operation.

    Raises ``ContractError`` on any contradiction. Does NOT invent a generic
    routing framework.
    """
    ledger = dict(result.capability_ledger)
    binding = result.binding_proposal
    has_target_refs = (
        binding is not None and len(binding.target_evidence_indices) > 0
    )
    has_support_refs = (
        binding is not None and len(binding.support_bindings) > 0
    )
    is_support_op = request.run_spec.operation == "support"
    produces_support = is_support_op and has_support_refs
    # v9: candidate_search honesty. Nonempty candidates REQUIRE the ledger to
    # say ``candidate_search=executed``. There is NO converse: an executed
    # candidate_search may legitimately return zero candidates.
    has_candidates = len(result.candidates) > 0
    if has_candidates and ledger.get("candidate_search") != "executed":
        raise ContractError(
            f"capability ledger honesty: candidate_search="
            f"{ledger.get('candidate_search')!r} but the result carries "
            f"{len(result.candidates)} candidate(s) (must be 'executed' when "
            f"candidates are nonempty; no converse — executed may return zero)"
        )

    # prepare_index honesty.
    if attempt_prepare or attempt_index:
        # Lifecycle hooks ran and succeeded (we would not be here otherwise).
        if ledger.get("prepare_index") != "executed":
            raise ContractError(
                f"capability ledger honesty: prepare_index="
                f"{ledger.get('prepare_index')!r} but lifecycle hooks were "
                f"attempted (must be 'executed')"
            )
    else:
        # Neither attempted => must NOT claim executed.
        if ledger.get("prepare_index") == "executed":
            raise ContractError(
                "capability ledger honesty: prepare_index='executed' but "
                "neither prepare nor index hook was attempted (must not "
                "claim executed; legitimate_skip acceptable)"
            )

    # target_binding honesty (forward + converse).
    if has_target_refs:
        if ledger.get("target_binding") != "executed":
            raise ContractError(
                f"capability ledger honesty: target_binding="
                f"{ledger.get('target_binding')!r} but binding has target refs "
                f"(must be 'executed')"
            )
    else:
        if ledger.get("target_binding") == "executed":
            raise ContractError(
                "capability ledger honesty: target_binding='executed' but "
                "binding has no target refs (executed capability must "
                "correspond to actual output)"
            )

    # support_expansion honesty (forward + converse).
    if has_support_refs:
        if ledger.get("support_expansion") != "executed":
            raise ContractError(
                f"capability ledger honesty: support_expansion="
                f"{ledger.get('support_expansion')!r} but binding has support "
                f"refs (must be 'executed')"
            )
    else:
        if ledger.get("support_expansion") == "executed":
            raise ContractError(
                "capability ledger honesty: support_expansion='executed' but "
                "binding has no support refs (executed capability must "
                "correspond to actual output)"
            )

    # two_step_support honesty (forward + converse).
    if produces_support:
        if ledger.get("two_step_support") != "executed":
            raise ContractError(
                f"capability ledger honesty: two_step_support="
                f"{ledger.get('two_step_support')!r} but support operation "
                f"produces support (must be 'executed')"
            )
    else:
        if ledger.get("two_step_support") == "executed":
            raise ContractError(
                "capability ledger honesty: two_step_support='executed' but "
                "no support operation producing support (executed capability "
                "must correspond to actual operation)"
            )


def _extract_excerpt(text: str, start_line: int, end_line: int) -> str:
    """Extract the actual selected source excerpt (1-indexed inclusive)."""
    lines = text.splitlines()
    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        raise ContractError(
            f"excerpt range {start_line}-{end_line} invalid for {len(lines)} lines"
        )
    return "\n".join(lines[start_line - 1 : end_line])


def materialize_candidates(
    candidates: tuple[Candidate, ...],
    snapshot: FrozenSnapshot,
    step: int = 1,
) -> tuple[tuple[BakeoffVerifiedEvidence, ...], BudgetUsage]:
    """Common materializer: read source bytes ONCE per candidate and construct
    canonical ``verified_current`` bakeoff evidence. Only this function may
    construct BakeoffVerifiedEvidence (via the module-private token).

    Fail-closed (rejection): any candidate whose source is missing, a symlink,
    a symlinked path component, binary, undecodable, or whose range exceeds
    the current file raises ContractError (a malformed/stale candidate is a
    conformance failure, NOT a silent no-evidence pack).

    v6: returns a ``BudgetUsage`` with ``candidate_count`` honestly set to
    ``len(candidates)`` and ``evidence_count`` set to the actual materialized
    count. Target/support/rendered/episode fields are zero (filled by
    ``build_context_pack`` and validated against the actual evidence tuple by
    ``ContextPack.validate``).
    """
    # Pre-check: snapshot must be unchanged since freeze.
    assert_snapshot_unchanged(snapshot)

    root_resolved = snapshot.root.resolve()
    evidence: list[BakeoffVerifiedEvidence] = []
    for cand in candidates:
        full = snapshot.root / cand.path
        # COMMON safe path policy: lexical + resolved confinement + all
        # components checked for symlinks. Rejects parent symlinks AND
        # symlinked path components that escape the source root.
        _validate_safe_path_under_root(
            full, root_resolved, f"candidate {cand.path!r}"
        )
        if not full.is_file():
            raise ContractError(
                f"candidate path {cand.path!r} not a readable file (stale/missing)"
            )
        if full.is_symlink():
            raise ContractError(
                f"candidate path {cand.path!r} is a symlink (escape rejected)"
            )
        data = full.read_bytes()
        # Binary policy: reject NUL bytes in the first 8KB (text-only policy).
        if b"\x00" in data[:8192]:
            raise ContractError(
                f"candidate source {cand.path!r} is binary (NUL in head)"
            )
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError(
                f"candidate source {cand.path!r} not UTF-8 decodable"
            ) from exc
        lines = text.splitlines()
        # Range beyond current file -> stale/changed source -> REJECT.
        if cand.end_line > len(lines) or cand.start_line < 1:
            raise ContractError(
                f"candidate range {cand.start_line}-{cand.end_line} exceeds "
                f"current source ({len(lines)} lines) for {cand.path!r} "
                "(stale/changed source; candidate-range rejection)"
            )
        excerpt = _extract_excerpt(text, cand.start_line, cand.end_line)
        ev = BakeoffVerifiedEvidence(
            evidence_kind="verified_current",
            path=cand.path,
            start_line=cand.start_line,
            end_line=cand.end_line,
            source_sha256=_sha256_bytes(data),
            excerpt=excerpt,
            excerpt_sha256=_sha256_bytes(excerpt.encode("utf-8")),
            score=cand.score,
            why=(cand.reason,),
            channels=cand.channels,
            freshness="frozen",
            byte_count=len(data),
            char_count=len(text),
            line_count=len(lines),
            materializer_version=MATERIALIZER_VERSION,
            materialized_at_step=step,
            _token=_HARNESS_TOKEN,
        )
        evidence.append(ev)

    # Post-check: snapshot still unchanged (no mutation during materialize).
    assert_snapshot_unchanged(snapshot)

    usage = BudgetUsage(
        candidate_count=len(candidates),
        evidence_count=len(evidence),
        target_count=0,  # filled by build_context_pack
        support_count=0,  # filled by build_context_pack
        rendered_chars=0,  # filled by build_context_pack
        rendered_bytes=0,  # filled by build_context_pack
        rendered_estimate=0,  # filled by build_context_pack
        episode_step_count=step,
        episode_estimate_used=0,  # filled by build_context_pack
    )
    return tuple(evidence), usage


def _render_context(
    evidence: tuple[BakeoffVerifiedEvidence, ...],
    targets: tuple[PackTarget, ...],
    support: tuple[PackSupport, ...],
) -> str:
    """Render the actual context: deterministic concatenation of the real
    source excerpts (targets first, then support), with a compact provenance
    frame. The budget and pack hash cover THIS rendered context."""
    parts: list[str] = []
    for t in targets:
        ev = evidence[t.evidence_index]
        parts.append(
            f">>> target {ev.path}:{ev.start_line}-{ev.end_line}\n{ev.excerpt}"
        )
    for s in support:
        ev = evidence[s.evidence_index]
        tag = "support" if s.parent_target_id is None else "support-for-parent"
        parts.append(
            f">>> {tag} {ev.path}:{ev.start_line}-{ev.end_line}\n{ev.excerpt}"
        )
    return "\n".join(parts)


def build_context_pack(
    evidence: tuple[BakeoffVerifiedEvidence, ...],
    request: AdapterRequest,
    binding: BindingProposal | None,
    candidate_count: int,
    materialize_step: int = 1,
    parent_episode_estimate_used: int = 0,
) -> ContextPack:
    """Build a context pack from verified evidence + an UNTRUSTED binding
    proposal + request + explicit harness execution values.

    v8: an explicit ``BindingProposal`` is REQUIRED before branching on
    evidence (defense in depth — the ok-result requirement is also enforced
    at ``validate_adapter_result``). There is no "proposal, if present"
    path. Pack semantics:
      * If no evidence materialized: pack_status = ``no_evidence``; the
        proposal MUST be ``proposed_status=no_evidence`` with a nonempty
        validated reason and NO refs (the latter two are enforced by
        ``BindingProposal.validate_shape``). The pack carries the proposal's
        validated reason.
      * If evidence materialized: the proposal's ``proposed_status``
        determines the final pack status (``ready`` requires refs;
        ``uncertain`` requires a reason and the final pack remains
        uncertain; ``no_evidence`` is only valid when no evidence
        materialized).
      * Common code validates references (evidence indices in range, support
        references valid targets or a parent target, closed relation kinds, no
        duplicate source rendered twice), materializes, and renders.

    v6: ``candidate_count`` is an explicit harness argument (NOT derived from
    the pack). Every ``BudgetUsage`` field is computed from the actual evidence
    + explicit inputs and validated by ``ContextPack.validate`` against the
    ACTUAL evidence tuple. No externally forged field can pass.
    """
    caps = request.run_spec.caps
    targets: list[PackTarget] = []
    support: list[PackSupport] = []
    diagnostics: list[str] = []
    status_reason: str | None = None
    pack_status: str

    # v8: require an explicit BindingProposal BEFORE branching on evidence
    # (defense in depth). There is no "proposal, if present" path.
    if binding is None:
        raise ContractError(
            "ok result must carry an explicit BindingProposal "
            "(no proposal supplied; target/support binding unresolved)"
        )
    binding.validate_shape()

    if len(evidence) == 0:
        # Zero evidence requires proposed_status=no_evidence, a nonempty
        # validated reason, and no refs (the reason/refs are enforced by
        # validate_shape for no_evidence; the status is enforced here).
        if binding.proposed_status != "no_evidence":
            raise ContractError(
                "proposed_status != no_evidence but no evidence materialized"
            )
        pack_status = "no_evidence"
        status_reason = binding.status_reason
    else:
        if binding.proposed_status == "no_evidence":
            raise ContractError(
                "proposed_status=no_evidence but evidence materialized "
                "(no_evidence is only valid when no evidence materialized)"
            )
        # Validate target references against actual evidence.
        ev_count = len(evidence)
        for idx in binding.target_evidence_indices:
            if not (0 <= idx < ev_count):
                raise ContractError(
                    f"binding target_evidence_index {idx} out of range "
                    f"(evidence_count={ev_count})"
                )
        # Build targets from binding target indices.
        for idx in binding.target_evidence_indices:
            ev = evidence[idx]
            targets.append(
                PackTarget(
                    evidence_index=idx,
                    path=ev.path,
                    start_line=ev.start_line,
                    end_line=ev.end_line,
                )
            )
        # Validate support references.
        target_index_set = {i for i in range(len(targets))}
        seen_support_evidence: set[int] = set()
        for sb in binding.support_bindings:
            if not (0 <= sb.evidence_index < ev_count):
                raise ContractError(
                    f"binding support evidence_index {sb.evidence_index} out "
                    f"of range (evidence_count={ev_count})"
                )
            if sb.evidence_index in {t.evidence_index for t in targets}:
                raise ContractError(
                    f"binding support evidence_index {sb.evidence_index} is "
                    "also a target (an evidence cannot be both)"
                )
            if sb.evidence_index in seen_support_evidence:
                raise ContractError(
                    f"duplicate support evidence_index {sb.evidence_index}"
                )
            seen_support_evidence.add(sb.evidence_index)
            if sb.parent_target_id is not None:
                # Parent-bound support: must match the request lineage.
                if sb.parent_target_id != request.run_spec.bound_target_id:
                    raise ContractError(
                        "support parent_target_id does not match "
                        "run_spec.bound_target_id"
                    )
            else:
                for ti in sb.target_indices:
                    if ti not in target_index_set:
                        raise ContractError(
                            f"binding support target_index {ti} not a valid "
                            "target"
                        )
            ev = evidence[sb.evidence_index]
            support.append(
                PackSupport(
                    evidence_index=sb.evidence_index,
                    target_indices=sb.target_indices,
                    relation_kind=sb.relation_kind,
                    path=ev.path,
                    start_line=ev.start_line,
                    end_line=ev.end_line,
                    parent_target_id=sb.parent_target_id,
                )
            )
        # Derive final pack status from the proposal's proposed_status.
        if binding.proposed_status == "ready":
            pack_status = "ready"
            status_reason = None
        else:
            # uncertain: final pack remains uncertain regardless of refs.
            pack_status = "uncertain"
            status_reason = binding.status_reason

    rendered_context = _render_context(tuple(evidence), tuple(targets), tuple(support))
    rendered_chars = len(rendered_context)
    rendered_bytes = len(rendered_context.encode("utf-8"))
    rendered_estimate = estimate_tokens(rendered_context)

    # Cumulative episode usage for two_step support runs.
    episode_step_count = materialize_step
    if (
        request.run_spec.interaction_mode == "two_step"
        and request.run_spec.operation == "support"
    ):
        episode_estimate_used = parent_episode_estimate_used + rendered_estimate
    else:
        episode_estimate_used = rendered_estimate

    usage = BudgetUsage(
        candidate_count=candidate_count,
        evidence_count=len(evidence),
        target_count=len(targets),
        support_count=len(support),
        rendered_chars=rendered_chars,
        rendered_bytes=rendered_bytes,
        rendered_estimate=rendered_estimate,
        episode_step_count=episode_step_count,
        episode_estimate_used=episode_estimate_used,
    )

    pack = ContextPack(
        pack_status=pack_status,
        status_reason=status_reason,
        targets=tuple(targets),
        support=tuple(support),
        diagnostics=tuple(diagnostics),
        budget_usage=usage,
        rendered_context=rendered_context,
        operation=request.run_spec.operation,
    )
    pack.validate(
        tuple(evidence), caps, candidate_count,
        materialize_step, parent_episode_estimate_used,
    )
    return pack


def validate_context_pack(
    pack: ContextPack, request: AdapterRequest,
    evidence: tuple[BakeoffVerifiedEvidence, ...],
    candidate_count: int,
    materialize_step: int,
    parent_episode_estimate_used: int,
) -> ContextPack:
    """v6: validate a context pack against the ACTUAL bakeoff evidence tuple
    and explicit harness execution values. Every target/support path+range is
    verified against its referenced evidence; the rendered context is
    deterministically rerendered and compared; every ``BudgetUsage`` field is
    recomputed. No externally forged field can pass."""
    pack.validate(
        tuple(evidence), request.run_spec.caps, candidate_count,
        materialize_step, parent_episode_estimate_used,
    )
    return pack


def stable_target_id(target: PackTarget) -> str:
    """Derive a stable id from an actual materialized target (path+range).

    This id is used for two-step lineage binding: the context step's target
    gets a stable id, and the support step's ``bound_target_id`` must match.
    """
    payload = f"{target.path}:{target.start_line}-{target.end_line}"
    return "tgt_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Determinism: canonical hashes excluding measurements and IDs
# ---------------------------------------------------------------------------


def canonical_result_hash(
    result: AdapterResult, candidates: tuple[Candidate, ...]
) -> str:
    """Canonical hash of (result, candidates) EXCLUDING measured resources and
    IDs. Three clean repetitions must produce identical hashes. Repetition
    identity is excluded (the hash covers only result/candidate content)."""
    payload = {
        "status": result.status,
        "failure_category": result.failure_category,
        "capability_ledger": dict(sorted(result.capability_ledger.items())),
        "fallback_provenance": [
            {"unavailable_capability": f.unavailable_capability, "fallback_to": f.fallback_to}
            for f in result.fallback_provenance
        ],
        "candidates": [
            {
                "path": c.path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "score": c.score,
                "reason": c.reason,
                "channels": sorted(c.channels),
                "adapter_provenance": c.adapter_provenance,
            }
            for c in candidates
        ],
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "crh_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def canonical_pack_hash(pack: ContextPack) -> str:
    """Canonical hash of a pack EXCLUDING measured resources and IDs, but
    COVERING the actual rendered context (via its hash). Repetition identity
    is excluded."""
    payload = {
        "pack_status": pack.pack_status,
        "status_reason": pack.status_reason,
        "operation": pack.operation,
        "targets": [
            {
                "evidence_index": t.evidence_index,
                "path": t.path,
                "start_line": t.start_line,
                "end_line": t.end_line,
            }
            for t in pack.targets
        ],
        "support": [
            {
                "evidence_index": s.evidence_index,
                "target_indices": list(s.target_indices),
                "relation_kind": s.relation_kind,
                "path": s.path,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "parent_target_id": s.parent_target_id,
            }
            for s in pack.support
        ],
        "diagnostics": list(pack.diagnostics),
        "rendered_context_hash": hashlib.sha256(
            pack.rendered_context.encode("utf-8")
        ).hexdigest()[:24],
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "cph_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


__all__ = [
    "SCHEMA_VERSION",
    "GENERATED_BY",
    "CLAIM_LEVEL",
    "INTERACTION_MODES",
    "OPERATIONS",
    "LANGUAGE_FAMILIES",
    "TASK_FAMILIES",
    "SOURCE_VISIBILITY",
    "CACHE_STATES",
    "EXECUTION_MODES",
    "SPDX_STATES",
    "PERSISTENT_STATE_BEHAVIORS",
    "CHANNELS",
    "CAPABILITIES",
    "CAPABILITY_STATUSES",
    "UNAVAILABLE_STATUSES",
    "RESULT_STATUSES",
    "PACK_OK_STATUSES",
    "PACK_STATUSES",
    "RELATION_KINDS",
    "BUDGET_ESTIMATOR_NAME",
    "BUDGET_ESTIMATOR_VERSION",
    "MATERIALIZER_VERSION",
    "RENDERER_VERSION",
    "FORBIDDEN_CANDIDATE_KEYS",
    "PRIVATE_REPORT_KEYS",
    "ContractError",
    "_validate_lexical_relative_path",
    "_validate_safe_path_under_root",
    "BakeoffTask",
    "BudgetCaps",
    "BakeoffRunSpec",
    "AdapterRequest",
    "fairness_fingerprint",
    "Candidate",
    "validate_candidate_obj",
    "AdapterDescriptor",
    "AdapterHooks",
    "validate_descriptor_hooks",
    "ResourceSample",
    "SupportBinding",
    "BindingProposal",
    "FallbackRecord",
    "AdapterResult",
    "FrozenSnapshot",
    "compute_manifest_digest",
    "materialize_snapshot",
    "snapshot_source_visibility_digest",
    "scan_visible_tree",
    "assert_snapshot_unchanged",
    "validate_snapshot_binding",
    "validate_execution_root_binding",
    "estimate_tokens",
    "BudgetUsage",
    "BakeoffVerifiedEvidence",
    "PackTarget",
    "PackSupport",
    "ContextPack",
    "validate_request",
    "validate_adapter_result",
    "validate_capability_ledger_honesty",
    "materialize_candidates",
    "build_context_pack",
    "validate_context_pack",
    "stable_target_id",
    "canonical_result_hash",
    "canonical_pack_hash",
]
