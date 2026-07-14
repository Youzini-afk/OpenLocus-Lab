#!/usr/bin/env python3
"""Product Stack Bakeoff B1 — S0-S5 cumulative-stack adapters (v2).

V2 changes from v1:
* All six adapters are ``warm_reuse`` with persistent BM25 at
  ``.openlocus/index`` (NOT a sibling directory).
* S0-S5 are CUMULATIVE: S0={bm25}, S1={bm25,text}, S2={bm25,text,symbol},
  S3={bm25,text,symbol,graph}, S4=S2 pool+support, S5=S3 pool+support.
* Adapters consume ONLY the production Rust ``bakeoff-query`` closed JSON
  surface.  No direct per-channel CLI composition, no Python RRF/resort, no
  AST fallback, no synthesized/path-derived candidate, no query-derived
  support path, no swallowed configured error.
* Before/after every production call: source immutability + strict WSR
  inventory (checked regular files/dirs only, expected index inventory,
  expected trace append, optional closed lineage receipt; reject sibling
  state/symlink/reparse/special/extra files).
* Validate exact component receipt set/status/count/diagnostics, production
  RRF marker, remote/provider count, output channels, hashes, relation
  provenance and flattened EvidenceCore shape before constructing Candidate.

All hooks are top-level functions for Windows spawn-picklability.

Run::

    python -m py_compile eval/product_bakeoff_b1_adapters.py
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import hashlib
import base64
import binascii
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from product_bakeoff_contract import (
    AdapterDescriptor,
    AdapterHooks,
    AdapterRequest,
    AdapterResult,
    BindingProposal,
    Candidate,
    ContractError,
    FallbackRecord,
    SupportBinding,
    CHANNELS,
    RELATION_KINDS,
    assert_snapshot_unchanged,
)

from product_bakeoff_b1_spec import (
    S0_ADAPTER_ID, S0_OUTPUT_CHANNELS, S0_CAPABILITIES, S0_PERSISTENT_STATE,
    S1_ADAPTER_ID, S1_OUTPUT_CHANNELS, S1_CAPABILITIES, S1_PERSISTENT_STATE,
    S2_ADAPTER_ID, S2_OUTPUT_CHANNELS, S2_CAPABILITIES, S2_PERSISTENT_STATE,
    S3_ADAPTER_ID, S3_OUTPUT_CHANNELS, S3_CAPABILITIES, S3_PERSISTENT_STATE,
    S4_ADAPTER_ID, S4_OUTPUT_CHANNELS, S4_CAPABILITIES, S4_PERSISTENT_STATE,
    S5_ADAPTER_ID, S5_OUTPUT_CHANNELS, S5_CAPABILITIES, S5_PERSISTENT_STATE,
    B1_ADAPTER_VERSION, B1_UPSTREAM_REVISION,
    B1_MAX_CANDIDATES, B1_ONE_SHOT_MAX_TARGETS, B1_TWO_STEP_MAX_SUPPORT,
    B1_TIMEOUT_SECONDS, B1_WSR_REL, B1_INDEX_REL, B1_TRACES_REL,
    B1_RRF_MARKER, B1_RRF_VERSION, B1_RRF_TIE_ORDER_WIRE,
    B1_RRF_RANK_TIE_POLICY, B1_RRF_CHANNEL_WEIGHTS,
    B1_COMPONENT_TIE_ORDER_WIRE, B1_BM25_OVERFETCH_FACTOR,
    B1_BM25_OVERFETCH_MAX, B1_COMPONENT_EXACT_CELL_DEDUP,
    B1_RRF_INPUT_NORMALIZATION,
    B1_RUST_SCHEMA_VERSION,
    B1_RECEIPT_STATUSES, B1_COMPONENTS,
    B1_COMPONENT_ORDER, B1_RAW_CHANNEL_MAP,
    B1_IDENTIFIER_PREDICATE, B1_GRAPH_PREDICATE,
    B1_GRAPH_ELIGIBLE_TASK_FAMILIES,
    B1_PROVIDER_AUDIT_REL, B1_TRANSCRIPT_DIR_REL,
    B1_INDEX_SEAL_REL, B1_LINEAGE_RECEIPT_REL,
    B1_TRANSCRIPT_SCHEMA_VERSION, B1_INDEX_SEAL_SCHEMA_VERSION,
    adapter_context_components, adapter_support_components,
    adapter_supports_support,
)
from product_bakeoff_b1_fixtures import B1_ALL_TASKS

ADAPTER_VERSION = B1_ADAPTER_VERSION
SUPPORTED_LANGS = frozenset({"rust", "typescript"})

# CLI subprocess timeout (must be < run_spec.timeout_seconds = 30s).
_CLI_TIMEOUT = 25.0


# ===========================================================================
# CLI binary discovery
# ===========================================================================

_CLI_PATH: str | None = None


def _find_cli() -> str:
    """Find the openlocus CLI binary."""
    global _CLI_PATH
    if _CLI_PATH is not None:
        return _CLI_PATH
    env_path = os.environ.get("OPENLOCUS_CLI")
    if env_path and Path(env_path).is_file():
        _CLI_PATH = env_path
        return _CLI_PATH
    here = Path(__file__).resolve().parent
    for parent in [here] + list(here.parents):
        for mode in ("debug", "release"):
            exe = parent / "target" / mode / "openlocus"
            if exe.is_file():
                _CLI_PATH = str(exe)
                return _CLI_PATH
            exe_win = parent / "target" / mode / "openlocus.exe"
            if exe_win.is_file():
                _CLI_PATH = str(exe_win)
                return _CLI_PATH
    raise RuntimeError(
        "openlocus CLI binary not found; set OPENLOCUS_CLI env var or "
        "build with `cargo build`")


def _bakeoff_query_available(cli_path: str | None = None) -> bool:
    """Check if the bakeoff-query subcommand exists in the CLI."""
    if cli_path is None:
        cli_path = _find_cli()
    try:
        result = subprocess.run(
            [cli_path, "bakeoff-query", "--help"],
            capture_output=True, timeout=10.0,
        )
        return result.returncode == 0
    except Exception:
        return False


# ===========================================================================
# STRICT RUST JSON PARSER (isolated — orchestrator reconciles field names)
# ===========================================================================
# This is the ONE strict parser for the expected ``bakeoff-query`` closed JSON
# surface.  It validates the schema version, mode, component receipts,
# evidence items, RRF marker, provider/remote counts, graph diagnostics, and
# support relation provenance.  Any schema violation raises ContractError
# (a configured error that fails the cell — NEVER swallowed).
#
# The v2 envelope is a closed object with canonical source/state roots,
# requested/executed component lists, ordered flattened evidence, ordered
# component receipts, the production tie-aware RRF marker, zero-provider
# diagnostics, and checked trace evidence. Support mode additionally binds a
# confined parent object and one structured relation per evidence item.


class RustReceiptError(ContractError):
    """Raised when a bakeoff-query receipt violates the closed schema."""


@dataclass(frozen=True)
class ComponentReceipt:
    """Parsed component receipt from bakeoff-query."""
    component: str
    status: str  # executed | legitimate_skip | error
    evidence_count: int
    reason: str | None
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class RustEvidenceItem:
    """Parsed evidence item from bakeoff-query (flattened EvidenceCore)."""
    path: str
    start_line: int
    end_line: int
    content_sha: str
    score: float
    why: tuple[str, ...]
    channels: tuple[str, ...]


@dataclass(frozen=True)
class SupportRelation:
    """Parsed support relation provenance from bakeoff-query."""
    support_path: str
    support_start_line: int
    support_end_line: int
    relation_kind: str
    production_edge_kind: str
    target_path: str
    target_start_line: int
    target_end_line: int


@dataclass(frozen=True)
class GraphDiagnostics:
    """Parsed graph diagnostics from bakeoff-query."""
    skipped_path_unsafe: int
    skipped_stale: int
    edge_count: int
    saturated: bool


@dataclass(frozen=True)
class ProviderDiagnostics:
    remote_calls: int
    outbound_calls: int
    audit_path: str
    audit_events_before: int
    audit_events_after: int


@dataclass(frozen=True)
class TraceDiagnostics:
    routed_to: str
    event: str
    written: bool


@dataclass(frozen=True)
class ParsedBakeoffQuery:
    """Strictly parsed bakeoff-query result."""
    schema_version: str
    mode: str
    request_id: str
    source_root: str
    state_root: str
    query: str | None
    task_family: str | None
    max_results: int
    components_requested: tuple[str, ...]
    components_executed: tuple[str, ...]
    receipts: tuple[ComponentReceipt, ...]
    evidence: tuple[RustEvidenceItem, ...]
    evidence_count: int
    rrf_k: int
    rrf_version: str
    rrf_marker: str
    rrf_tie_order: str
    rrf_rank_tie_policy: str
    rrf_channel_weights: str
    rrf_input_normalization: str
    rrf_input_rewrites: int
    provider: ProviderDiagnostics
    trace: TraceDiagnostics
    graph_diagnostics: GraphDiagnostics | None
    support_relations: tuple[SupportRelation, ...]
    parent_path: str | None
    parent_start_line: int | None
    parent_end_line: int | None


def _require_str_field(data: dict, key: str, name: str, max_len: int = 512) -> str:
    v = data.get(key)
    if not isinstance(v, str) or not v:
        raise RustReceiptError(f"{name}: missing or non-string {key!r}")
    if len(v) > max_len:
        raise RustReceiptError(f"{name}: {key!r} exceeds {max_len} chars")
    return v


def _require_int_field(data: dict, key: str, name: str) -> int:
    v = data.get(key)
    if not isinstance(v, int) or isinstance(v, bool):
        raise RustReceiptError(f"{name}: missing or non-int {key!r}")
    return v


def _require_float_field(data: dict, key: str, name: str) -> float:
    v = data.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise RustReceiptError(f"{name}: missing or non-numeric {key!r}")
    f = float(v)
    if f != f or f in (float("inf"), float("-inf")):
        raise RustReceiptError(f"{name}: {key!r} must be finite")
    return f


def _require_exact_keys(
    data: dict[str, Any], expected: set[str], name: str,
) -> None:
    actual = set(data)
    if actual != expected:
        raise RustReceiptError(
            f"{name}: closed keys mismatch: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RustReceiptError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _ordered_components(components: frozenset[str]) -> tuple[str, ...]:
    if components == frozenset({"support"}):
        return ("support",)
    ordered = tuple(c for c in B1_COMPONENT_ORDER if c in components)
    if frozenset(ordered) != components:
        raise RustReceiptError(
            f"unknown or non-context component set: {sorted(components)}")
    if ordered != B1_COMPONENT_ORDER[:len(ordered)]:
        raise RustReceiptError(
            f"non-cumulative component set: {list(ordered)}")
    return ordered


def _identifier_predicate(query: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", query))


def _wire_path(value: str | Path) -> Path:
    raw = str(value)
    if raw.startswith("\\\\?\\UNC\\"):
        raw = "\\\\" + raw[8:]
    elif raw.startswith("\\\\?\\"):
        raw = raw[4:]
    return Path(raw).resolve()


def _require_nonneg_int(data: dict[str, Any], key: str, name: str) -> int:
    value = _require_int_field(data, key, name)
    if value < 0:
        raise RustReceiptError(f"{name}: {key} must be nonnegative")
    return value


def _validate_receipt_diagnostics(
    component: str,
    status: str,
    diagnostics: Any,
    *,
    expected_state_root: Path,
    expected_query: str | None,
    expected_task_family: str | None,
    expected_parent: tuple[str, int, int] | None,
    expected_max_results: int,
) -> dict[str, Any]:
    if not isinstance(diagnostics, dict):
        raise RustReceiptError(f"component {component!r}: diagnostics must be object")
    diag = dict(diagnostics)
    if component == "bm25":
        _require_exact_keys(diag, {
            "index_source", "state_root", "separated", "stale_hits_skipped",
            "invalid_hits_skipped", "query_ms", "materialize_ms",
            "deterministic_tie_order", "exact_cell_dedup",
            "overfetch_limit", "raw_evidence_count",
            "canonical_evidence_count",
        }, "bm25 diagnostics")
        if diag["index_source"] != "persistent_state_root":
            raise RustReceiptError("bm25 diagnostics: persistent state marker missing")
        if _wire_path(str(diag["state_root"])) != expected_state_root:
            raise RustReceiptError("bm25 diagnostics: state_root mismatch")
        if diag["separated"] is not False:
            raise RustReceiptError("bm25 diagnostics: B1 requires colocated source/state")
        if diag["deterministic_tie_order"] != B1_COMPONENT_TIE_ORDER_WIRE:
            raise RustReceiptError("bm25 diagnostics: deterministic tie order mismatch")
        if diag["exact_cell_dedup"] is not B1_COMPONENT_EXACT_CELL_DEDUP:
            raise RustReceiptError("bm25 diagnostics: exact-cell dedup marker missing")
        expected_overfetch = min(
            expected_max_results * B1_BM25_OVERFETCH_FACTOR,
            B1_BM25_OVERFETCH_MAX,
        )
        if _require_nonneg_int(
                diag, "overfetch_limit", "bm25 diagnostics") != expected_overfetch:
            raise RustReceiptError("bm25 diagnostics: overfetch limit mismatch")
        raw_count = _require_nonneg_int(
            diag, "raw_evidence_count", "bm25 diagnostics")
        canonical_count = _require_nonneg_int(
            diag, "canonical_evidence_count", "bm25 diagnostics")
        if canonical_count > expected_max_results or raw_count < canonical_count:
            raise RustReceiptError("bm25 diagnostics: evidence count relationship invalid")
        if _require_nonneg_int(diag, "stale_hits_skipped", "bm25 diagnostics") != 0:
            raise RustReceiptError("bm25 diagnostics: stale hits were skipped")
        if _require_nonneg_int(diag, "invalid_hits_skipped", "bm25 diagnostics") != 0:
            raise RustReceiptError("bm25 diagnostics: invalid hits were skipped")
        for key in ("query_ms", "materialize_ms"):
            if _require_float_field(diag, key, "bm25 diagnostics") < 0:
                raise RustReceiptError(f"bm25 diagnostics: {key} must be nonnegative")
    elif component == "literal":
        _require_exact_keys(diag, {
            "channel", "text_escaped_once", "escape_count",
            "post_fusion_resort", "fallback",
        }, "literal diagnostics")
        if diag != {
            "channel": "regex_escaped_literal",
            "text_escaped_once": True,
            "escape_count": 1,
            "post_fusion_resort": False,
            "fallback": False,
        }:
            raise RustReceiptError("literal diagnostics do not prove one production call")
    elif component == "symbol":
        if status == "executed":
            _require_exact_keys(diag, {
                "predicate", "predicate_matched", "match", "post_filter",
                "case_sensitive", "substring_rejected", "ast_to_text_fallback",
            }, "symbol diagnostics")
            expected = {
                "predicate": B1_IDENTIFIER_PREDICATE,
                "predicate_matched": True,
                "match": "exact_name",
                "post_filter": "frozen_identifier_predicate",
                "case_sensitive": True,
                "substring_rejected": True,
                "ast_to_text_fallback": False,
            }
        else:
            _require_exact_keys(diag, {
                "predicate", "predicate_matched", "match", "case_sensitive",
                "substring_rejected", "ast_to_text_fallback",
            }, "symbol skip diagnostics")
            expected = {
                "predicate": B1_IDENTIFIER_PREDICATE,
                "predicate_matched": False,
                "match": "exact_name",
                "case_sensitive": True,
                "substring_rejected": True,
                "ast_to_text_fallback": False,
            }
        if diag != expected:
            raise RustReceiptError("symbol diagnostics mismatch")
    elif component == "graph":
        common = {
            "predicate", "predicate_matched", "depth", "seed_source",
            "seed_count", "skipped_stale", "skipped_path_unsafe",
            "inspect_saturated", "unsafe_skips_present",
            "parent_path_inferred_from_query",
        }
        if status == "executed":
            _require_exact_keys(diag, common | {
                "seed_paths", "edge_count", "node_count", "materialized",
                "materialization_skipped", "candidate_edges",
            }, "graph diagnostics")
            if diag["predicate_matched"] is not True:
                raise RustReceiptError("graph diagnostics: predicate did not fire")
            if expected_task_family not in B1_GRAPH_ELIGIBLE_TASK_FAMILIES:
                raise RustReceiptError("graph executed outside frozen task-family predicate")
            seed_count = _require_nonneg_int(diag, "seed_count", "graph diagnostics")
            if seed_count < 1:
                raise RustReceiptError("graph executed without a real pre-graph seed")
            seed_paths = diag.get("seed_paths")
            if not isinstance(seed_paths, list) or len(seed_paths) != seed_count:
                raise RustReceiptError("graph diagnostics: seed_paths/count mismatch")
            if len(seed_paths) != len(set(seed_paths)) or not all(
                isinstance(path, str) and path for path in seed_paths
            ):
                raise RustReceiptError("graph diagnostics: invalid seed_paths")
            for key in ("edge_count", "node_count", "materialized", "candidate_edges"):
                _require_nonneg_int(diag, key, "graph diagnostics")
            if _require_nonneg_int(
                diag, "materialization_skipped", "graph diagnostics") != 0:
                raise RustReceiptError("graph diagnostics: materialization skipped")
        else:
            _require_exact_keys(diag, common | {"eligible_task_families"},
                                "graph skip diagnostics")
            if diag["predicate_matched"] is not False:
                raise RustReceiptError("graph skip diagnostics: predicate unexpectedly true")
            if expected_task_family in B1_GRAPH_ELIGIBLE_TASK_FAMILIES:
                raise RustReceiptError("graph skipped even though frozen predicate fired")
            if sorted(diag.get("eligible_task_families", [])) != sorted(
                B1_GRAPH_ELIGIBLE_TASK_FAMILIES
            ):
                raise RustReceiptError("graph skip diagnostics: eligible vocabulary drift")
            if _require_nonneg_int(diag, "seed_count", "graph skip diagnostics") != 0:
                raise RustReceiptError("graph skip diagnostics: nonzero seed_count")
        if diag.get("predicate") != B1_GRAPH_PREDICATE:
            raise RustReceiptError("graph diagnostics: predicate marker mismatch")
        if diag.get("depth") != 1 or diag.get("seed_source") != "pre_graph_evidence":
            raise RustReceiptError("graph diagnostics: depth/seed source mismatch")
        if _require_nonneg_int(diag, "skipped_stale", "graph diagnostics") != 0:
            raise RustReceiptError("graph diagnostics: stale graph records")
        if _require_nonneg_int(diag, "skipped_path_unsafe", "graph diagnostics") != 0:
            raise RustReceiptError("graph diagnostics: unsafe graph paths")
        if diag.get("inspect_saturated") is not False:
            raise RustReceiptError("graph diagnostics: unexpected saturation")
        if diag.get("unsafe_skips_present") is not False:
            raise RustReceiptError("graph diagnostics: unsafe skips present")
        if diag.get("parent_path_inferred_from_query") is not False:
            raise RustReceiptError("graph diagnostics: query-derived path")
    elif component == "support":
        _require_exact_keys(diag, {
            "depth", "parent_path", "parent_start_line", "parent_end_line",
            "parent_confinement", "parent_path_inferred_from_query",
            "skipped_stale", "skipped_path_unsafe", "inspect_saturated",
            "unsafe_skips_present", "edge_count", "node_count",
            "candidate_edges_all_relations", "candidate_import_edges",
            "materialized", "materialization_skipped",
        }, "support diagnostics")
        if expected_parent is None:
            raise RustReceiptError("support diagnostics without expected parent")
        parent_path, parent_start, parent_end = expected_parent
        if (diag.get("parent_path"), diag.get("parent_start_line"),
                diag.get("parent_end_line")) != (
                parent_path, parent_start, parent_end):
            raise RustReceiptError("support diagnostics: parent mismatch")
        if diag.get("depth") != 1:
            raise RustReceiptError("support diagnostics: depth must be 1")
        if diag.get("parent_confinement") != "validated_under_source_root":
            raise RustReceiptError("support diagnostics: confinement marker mismatch")
        if diag.get("parent_path_inferred_from_query") is not False:
            raise RustReceiptError("support diagnostics: query-derived parent")
        for key in ("skipped_stale", "skipped_path_unsafe", "materialization_skipped"):
            if _require_nonneg_int(diag, key, "support diagnostics") != 0:
                raise RustReceiptError(f"support diagnostics: {key} must be zero")
        if diag.get("inspect_saturated") is not False or diag.get(
                "unsafe_skips_present") is not False:
            raise RustReceiptError("support diagnostics: saturation/unsafe skip")
        for key in (
            "edge_count", "node_count", "candidate_edges_all_relations",
            "candidate_import_edges", "materialized",
        ):
            _require_nonneg_int(diag, key, "support diagnostics")
        if diag["candidate_import_edges"] != diag["materialized"]:
            raise RustReceiptError("support diagnostics: import/materialized mismatch")
    else:
        raise RustReceiptError(f"unknown receipt component {component!r}")
    return diag


def _parse_component_receipt(
    comp_name: str,
    raw: Any,
    *,
    expected_state_root: Path,
    expected_query: str | None,
    expected_task_family: str | None,
    expected_parent: tuple[str, int, int] | None,
    expected_max_results: int,
) -> ComponentReceipt:
    """Parse and strictly validate a single component receipt."""
    if not isinstance(raw, dict):
        raise RustReceiptError(
            f"component {comp_name!r}: receipt must be a dict")
    expected_keys = {"component", "status", "evidence_count", "diagnostics"}
    if "reason" in raw:
        expected_keys.add("reason")
    _require_exact_keys(raw, expected_keys, f"component {comp_name!r} receipt")
    if raw.get("component") != comp_name:
        raise RustReceiptError(f"component {comp_name!r}: identity mismatch")
    status = raw.get("status")
    if status not in B1_RECEIPT_STATUSES:
        raise RustReceiptError(
            f"component {comp_name!r}: status {status!r} not in "
            f"{sorted(B1_RECEIPT_STATUSES)}")
    ec = raw.get("evidence_count")
    if not isinstance(ec, int) or isinstance(ec, bool) or ec < 0:
        raise RustReceiptError(
            f"component {comp_name!r}: evidence_count must be non-neg int")
    reason = raw.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise RustReceiptError(
            f"component {comp_name!r}: reason must be str or None")
    if reason is not None and len(reason) > 256:
        raise RustReceiptError(
            f"component {comp_name!r}: reason exceeds 256 chars")
    # executed with zero is legal; legitimate_skip requires a reason;
    # error requires a reason.
    if status == "legitimate_skip" and not reason:
        raise RustReceiptError(
            f"component {comp_name!r}: legitimate_skip requires a reason")
    if status == "error" and not reason:
        raise RustReceiptError(
            f"component {comp_name!r}: error requires a reason")
    if status == "error" and ec != 0:
        raise RustReceiptError(
            f"component {comp_name!r}: error must have evidence_count=0")
    if status == "executed" and reason is not None:
        raise RustReceiptError(
            f"component {comp_name!r}: executed receipt must omit reason")
    if status == "error":
        raise RustReceiptError(
            f"component {comp_name!r}: error receipt cannot appear in success envelope")
    if comp_name in {"bm25", "literal", "support"} and status != "executed":
        raise RustReceiptError(f"component {comp_name!r} cannot legitimately skip")
    if comp_name == "symbol":
        predicate = _identifier_predicate(expected_query or "")
        expected_status = "executed" if predicate else "legitimate_skip"
        if status != expected_status:
            raise RustReceiptError("symbol receipt contradicts identifier predicate")
        if status == "legitimate_skip" and reason != "identifier_predicate_false":
            raise RustReceiptError("symbol skip reason mismatch")
    if comp_name == "graph":
        predicate = expected_task_family in B1_GRAPH_ELIGIBLE_TASK_FAMILIES
        expected_status = "executed" if predicate else "legitimate_skip"
        if status != expected_status:
            raise RustReceiptError("graph receipt contradicts task-family predicate")
        if status == "legitimate_skip" and reason != "graph_task_family_predicate_false":
            raise RustReceiptError("graph skip reason mismatch")
    diagnostics = _validate_receipt_diagnostics(
        comp_name, status, raw.get("diagnostics"),
        expected_state_root=expected_state_root,
        expected_query=expected_query,
        expected_task_family=expected_task_family,
        expected_parent=expected_parent,
        expected_max_results=expected_max_results,
    )
    if comp_name == "bm25" and diagnostics["canonical_evidence_count"] != ec:
        raise RustReceiptError("bm25 receipt count does not match canonical evidence")
    return ComponentReceipt(
        component=comp_name, status=status,
        evidence_count=ec, reason=reason, diagnostics=diagnostics,
    )


def _parse_evidence_item(
    raw: Any, visible_files: set[str]
) -> RustEvidenceItem:
    """Parse and strictly validate a single flattened EvidenceCore item."""
    if not isinstance(raw, dict):
        raise RustReceiptError("evidence item must be a dict")
    path = raw.get("path")
    if not isinstance(path, str) or not path:
        raise RustReceiptError("evidence path missing/empty")
    if path not in visible_files:
        raise RustReceiptError(
            f"evidence path {path!r} not in frozen visible set")
    sl = raw.get("start_line")
    el = raw.get("end_line")
    if not isinstance(sl, int) or isinstance(sl, bool) or sl < 1:
        raise RustReceiptError(f"evidence {path!r}: start_line invalid")
    if not isinstance(el, int) or isinstance(el, bool) or el < 1:
        raise RustReceiptError(f"evidence {path!r}: end_line invalid")
    if sl > el:
        raise RustReceiptError(f"evidence {path!r}: start > end")
    content_sha = raw.get("content_sha")
    if not isinstance(content_sha, str) or not content_sha:
        raise RustReceiptError(f"evidence {path!r}: content_sha missing")
    if len(content_sha) > 128:
        raise RustReceiptError(f"evidence {path!r}: content_sha too long")
    score = _require_float_field(raw, "score", f"evidence {path!r}")
    _require_exact_keys(raw, {
        "path", "start_line", "end_line", "content_sha", "score", "why",
        "channels",
    }, f"evidence {path!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", content_sha):
        raise RustReceiptError(f"evidence {path!r}: content_sha format invalid")
    if score < 0:
        raise RustReceiptError(f"evidence {path!r}: score must be nonnegative")
    why_raw = raw.get("why")
    if not isinstance(why_raw, list):
        raise RustReceiptError(f"evidence {path!r}: why must be a list")
    if not all(isinstance(w, str) and 0 < len(w) <= 512 for w in why_raw):
        raise RustReceiptError(f"evidence {path!r}: why entries invalid")
    why = tuple(why_raw)
    ch_raw = raw.get("channels")
    if not isinstance(ch_raw, list):
        raise RustReceiptError(f"evidence {path!r}: channels must be a list")
    ch_set: set[str] = set()
    for c in ch_raw:
        if not isinstance(c, str) or not c:
            raise RustReceiptError(f"evidence {path!r}: channel item invalid")
        if c not in B1_RAW_CHANNEL_MAP:
            raise RustReceiptError(
                f"evidence {path!r}: raw channel {c!r} not in "
                f"{sorted(B1_RAW_CHANNEL_MAP)}")
        ch_set.add(c)
    if not ch_set:
        raise RustReceiptError(f"evidence {path!r}: channels must be non-empty")
    if len(ch_set) != len(ch_raw):
        raise RustReceiptError(f"evidence {path!r}: duplicate channels")
    return RustEvidenceItem(
        path=path, start_line=sl, end_line=el,
        content_sha=content_sha, score=score,
        why=why, channels=tuple(ch_raw),
    )


def _parse_support_relation(
    raw: Any, visible_files: set[str]
) -> SupportRelation:
    """Parse and strictly validate a support relation provenance record."""
    if not isinstance(raw, dict):
        raise RustReceiptError("support relation must be a dict")
    _require_exact_keys(raw, {
        "relation_kind", "production_edge_kind", "support_path",
        "support_start_line", "support_end_line", "target_path",
        "target_start_line", "target_end_line",
    }, "support relation")
    sp = raw.get("support_path")
    if not isinstance(sp, str) or sp not in visible_files:
        raise RustReceiptError(
            f"support relation: support_path {sp!r} not in visible set")
    ssl = raw.get("support_start_line")
    sel = raw.get("support_end_line")
    if not isinstance(ssl, int) or isinstance(ssl, bool) or ssl < 1:
        raise RustReceiptError("support relation: support_start_line invalid")
    if not isinstance(sel, int) or isinstance(sel, bool) or sel < 1:
        raise RustReceiptError("support relation: support_end_line invalid")
    if ssl > sel:
        raise RustReceiptError("support relation: support start > end")
    rk = raw.get("relation_kind")
    if rk not in RELATION_KINDS:
        raise RustReceiptError(
            f"support relation: relation_kind {rk!r} not in "
            f"{sorted(RELATION_KINDS)}")
    if rk != "import":
        raise RustReceiptError(
            f"support relation: B1 admits canonical 'import', got {rk!r}")
    pek = raw.get("production_edge_kind")
    if pek != "imports":
        raise RustReceiptError(
            f"support relation: production_edge_kind {pek!r} != 'imports'")
    tp = raw.get("target_path")
    if not isinstance(tp, str) or tp not in visible_files:
        raise RustReceiptError(
            f"support relation: target_path {tp!r} not in visible set")
    tsl = raw.get("target_start_line")
    tel = raw.get("target_end_line")
    if not isinstance(tsl, int) or isinstance(tsl, bool) or tsl < 1:
        raise RustReceiptError("support relation: target_start_line invalid")
    if not isinstance(tel, int) or isinstance(tel, bool) or tel < 1:
        raise RustReceiptError("support relation: target_end_line invalid")
    if tsl > tel:
        raise RustReceiptError("support relation: target start > end")
    return SupportRelation(
        support_path=sp, support_start_line=ssl, support_end_line=sel,
        relation_kind=rk, production_edge_kind=pek, target_path=tp,
        target_start_line=tsl, target_end_line=tel,
    )


def parse_bakeoff_query(
    raw_json: str | bytes,
    expected_components: frozenset[str],
    visible_files: tuple[str, ...],
    expected_mode: str,
    request_id: str,
    *,
    expected_source_root: str | Path,
    expected_state_root: str | Path,
    expected_query: str | None,
    expected_task_family: str | None,
    expected_max_results: int,
) -> ParsedBakeoffQuery:
    """Strictly parse and validate a bakeoff-query JSON result.

    This is the ONE isolated parser.  The orchestrator reconciles exact field
    names after the Rust writer finishes.  Any schema violation raises
    RustReceiptError (a configured error that fails the cell — NEVER
    swallowed).

    Actual Rust schema (reconciled from integration probe):
    * schema_version = ``B1_RUST_SCHEMA_VERSION``;
    * success (bool) — must be true for a valid result;
    * mode = "context" | "support";
    * receipts: LIST of {component, status, evidence_count, diagnostics};
    * evidence: LIST of flattened EvidenceCore items;
    * rrf: {marker, version, k: 60, tie_order, rank_tie_policy,
      channel_weights,
      input_normalization, input_rewrites};
    * provider: {remote_calls, outbound_calls, audit_path, ...};
    * trace: {routed_to, event, written};
    * support mode: parent_path, parent_start_line, parent_end_line,
      support_relations.

    Validates:
    * schema_version matches B1_RUST_SCHEMA_VERSION;
    * success == true (fail-closed on false);
    * mode matches expected_mode;
    * component receipts: exactly the expected component set, each with valid
      status/evidence_count;
    * evidence items: path in visible set, valid ranges, content_sha, score,
      why, channels;
    * RRF: k=60, production tie-aware marker/version/policy match;
    * provider.remote_calls == 0, provider.outbound_calls == 0;
    * support_relations: valid relation_kind, paths in visible set;
    * parent path/range (support mode only).
    """
    if isinstance(raw_json, bytes):
        raw_json = raw_json.decode("utf-8", errors="strict")
    if len(raw_json.encode("utf-8")) > 1024 * 1024:
        raise RustReceiptError("bakeoff-query JSON exceeds 1 MiB")
    try:
        data = json.loads(raw_json, object_pairs_hook=_reject_duplicate_pairs)
    except (json.JSONDecodeError, UnicodeDecodeError, RustReceiptError) as exc:
        raise RustReceiptError(
            f"bakeoff-query JSON decode failed: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RustReceiptError("bakeoff-query result must be a JSON object")

    context_keys = {
        "schema_version", "success", "mode", "source_root", "state_root",
        "query", "task_family", "max_results", "components_requested",
        "components_executed", "evidence", "evidence_count", "rrf",
        "receipts", "provider", "trace",
    }
    support_keys = {
        "schema_version", "success", "mode", "source_root", "state_root",
        "max_results", "components_requested", "components_executed",
        "evidence", "evidence_count", "rrf", "receipts", "parent",
        "relations", "provider", "trace",
    }
    _require_exact_keys(
        data, context_keys if expected_mode == "context" else support_keys,
        "bakeoff-query envelope")

    # Schema version.
    sv = _require_str_field(data, "schema_version", "bakeoff-query", 64)
    if sv != B1_RUST_SCHEMA_VERSION:
        raise RustReceiptError(
            f"schema_version {sv!r} != expected {B1_RUST_SCHEMA_VERSION!r}")

    # Success flag (must be true — fail-closed).
    success = data.get("success")
    if not isinstance(success, bool) or not success:
        err = data.get("error", "(no error field)")
        raise RustReceiptError(
            f"bakeoff-query success=false: {str(err)[:200]}")

    # Mode.
    mode = _require_str_field(data, "mode", "bakeoff-query", 32)
    if mode != expected_mode:
        raise RustReceiptError(
            f"mode {mode!r} != expected {expected_mode!r}")

    vis = set(visible_files)
    source_root = _wire_path(_require_str_field(
        data, "source_root", "bakeoff-query", 4096))
    state_root = _wire_path(_require_str_field(
        data, "state_root", "bakeoff-query", 4096))
    expected_source = _wire_path(expected_source_root)
    expected_state = _wire_path(expected_state_root)
    if source_root != expected_source or state_root != expected_state:
        raise RustReceiptError(
            f"source/state root mismatch: {(source_root, state_root)} != "
            f"{(expected_source, expected_state)}")
    max_results = _require_int_field(data, "max_results", "bakeoff-query")
    if max_results != expected_max_results:
        raise RustReceiptError(
            f"max_results {max_results} != expected {expected_max_results}")
    if expected_mode == "context":
        if data.get("query") != expected_query:
            raise RustReceiptError("context query echo mismatch")
        if data.get("task_family") != expected_task_family:
            raise RustReceiptError("context task_family echo mismatch")

    # Component receipts: a LIST of {component, status, evidence_count,
    # diagnostics}.  Validate exactly the expected component set.
    expected_order = _ordered_components(expected_components)
    requested_raw = data.get("components_requested")
    if requested_raw != list(expected_order):
        raise RustReceiptError(
            f"components_requested {requested_raw!r} != {list(expected_order)!r}")
    receipts_raw = data.get("receipts")
    if not isinstance(receipts_raw, list):
        raise RustReceiptError("receipts must be a list")
    receipt_components: list[str] = []
    receipts: list[ComponentReceipt] = []
    for r in receipts_raw:
        if not isinstance(r, dict):
            raise RustReceiptError("receipt item must be a dict")
        comp_name = r.get("component")
        if not isinstance(comp_name, str) or not comp_name:
            raise RustReceiptError("receipt component name missing")
        if comp_name in receipt_components:
            raise RustReceiptError(
                f"duplicate receipt for component {comp_name!r}")
        receipt_components.append(comp_name)
        parent_tuple: tuple[str, int, int] | None = None
        if expected_mode == "support":
            parent_raw = data.get("parent")
            if isinstance(parent_raw, dict):
                parent_tuple = (
                    parent_raw.get("path"), parent_raw.get("start_line"),
                    parent_raw.get("end_line"))  # type: ignore[assignment]
        receipts.append(_parse_component_receipt(
            comp_name, r,
            expected_state_root=expected_state,
            expected_query=expected_query,
            expected_task_family=expected_task_family,
            expected_parent=parent_tuple,
            expected_max_results=expected_max_results,
        ))
    if tuple(receipt_components) != expected_order:
        missing = set(expected_order) - set(receipt_components)
        extra = set(receipt_components) - set(expected_order)
        raise RustReceiptError(
            f"component receipt set mismatch: missing={sorted(missing)} "
            f"extra={sorted(extra)} expected={list(expected_order)}")
    executed = tuple(r.component for r in receipts if r.status == "executed")
    if data.get("components_executed") != list(executed):
        raise RustReceiptError("components_executed does not match receipt statuses")

    # Evidence items.
    ev_raw = data.get("evidence")
    if not isinstance(ev_raw, list):
        raise RustReceiptError("evidence must be a list")
    evidence = tuple(
        _parse_evidence_item(item, vis) for item in ev_raw
    )
    evidence_count = _require_nonneg_int(data, "evidence_count", "bakeoff-query")
    if evidence_count != len(evidence):
        raise RustReceiptError("evidence_count does not match evidence list")
    if len(evidence) > expected_max_results:
        raise RustReceiptError("evidence exceeds requested max_results")
    cells = [(e.path, e.start_line, e.end_line) for e in evidence]
    if len(cells) != len(set(cells)):
        raise RustReceiptError("fused evidence contains duplicate cells")
    if expected_mode == "context":
        expected_sorted = sorted(
            evidence,
            key=lambda e: (-e.score, e.path, e.start_line, e.end_line),
        )
        if list(evidence) != expected_sorted:
            raise RustReceiptError("fused context evidence violates production RRF order")

    # RRF marker/version.
    rrf_raw = data.get("rrf")
    if not isinstance(rrf_raw, dict):
        raise RustReceiptError("rrf must be a dict")
    _require_exact_keys(rrf_raw, {
        "marker", "version", "k", "tie_order",
        "rank_tie_policy", "channel_weights",
        "input_normalization", "input_rewrites",
    }, "rrf")
    rrf_k = _require_int_field(rrf_raw, "k", "rrf")
    if rrf_k != 60:
        raise RustReceiptError(f"rrf.k {rrf_k} != 60 (production K=60)")
    rrf_version = _require_str_field(rrf_raw, "version", "rrf", 128)
    if rrf_version != B1_RRF_VERSION:
        raise RustReceiptError(
            f"rrf.version {rrf_version!r} != {B1_RRF_VERSION!r}")
    rrf_marker = _require_str_field(rrf_raw, "marker", "rrf", 64)
    if rrf_marker != B1_RRF_MARKER:
        raise RustReceiptError(
            f"rrf.marker {rrf_marker!r} != {B1_RRF_MARKER!r}")
    if rrf_raw.get("tie_order") != B1_RRF_TIE_ORDER_WIRE:
        raise RustReceiptError("rrf.tie_order mismatch")
    rank_tie_policy = _require_str_field(
        rrf_raw, "rank_tie_policy", "rrf", 96)
    if rank_tie_policy != B1_RRF_RANK_TIE_POLICY:
        raise RustReceiptError("rrf.rank_tie_policy mismatch")
    channel_weights = _require_str_field(
        rrf_raw, "channel_weights", "rrf", 128)
    if channel_weights != B1_RRF_CHANNEL_WEIGHTS:
        raise RustReceiptError("rrf.channel_weights mismatch")
    if rrf_raw.get("input_normalization") != B1_RRF_INPUT_NORMALIZATION:
        raise RustReceiptError("rrf.input_normalization mismatch")
    input_rewrites = _require_nonneg_int(
        rrf_raw, "input_rewrites", "rrf")
    if expected_mode == "support" and input_rewrites != 0:
        raise RustReceiptError("support envelope reported RRF input rewrites")

    # Provider call counts (must be zero).  The Rust schema nests these
    # under a "provider" object.
    provider_raw = data.get("provider")
    if not isinstance(provider_raw, dict):
        raise RustReceiptError("provider must be a dict")
    _require_exact_keys(provider_raw, {
        "remote_calls", "outbound_calls", "audit_path",
        "audit_events_before", "audit_events_after",
    }, "provider")
    remote_calls = _require_nonneg_int(provider_raw, "remote_calls", "provider")
    if remote_calls != 0:
        raise RustReceiptError(
            f"provider.remote_calls must be 0, got {remote_calls!r}")
    outbound_calls = _require_nonneg_int(provider_raw, "outbound_calls", "provider")
    if outbound_calls != 0:
        raise RustReceiptError(
            f"provider.outbound_calls must be 0, got {outbound_calls!r}")
    audit_path = _require_str_field(provider_raw, "audit_path", "provider", 4096)
    if _wire_path(audit_path) != (expected_state / Path(B1_PROVIDER_AUDIT_REL)).resolve():
        raise RustReceiptError("provider.audit_path mismatch")
    audit_before = _require_nonneg_int(
        provider_raw, "audit_events_before", "provider")
    audit_after = _require_nonneg_int(
        provider_raw, "audit_events_after", "provider")
    if audit_before != audit_after:
        raise RustReceiptError("provider audit count changed during request")
    if audit_before != 0:
        raise RustReceiptError("provider audit must remain empty for B1")
    provider = ProviderDiagnostics(
        remote_calls=remote_calls, outbound_calls=outbound_calls,
        audit_path=audit_path, audit_events_before=audit_before,
        audit_events_after=audit_after,
    )

    trace_raw = data.get("trace")
    if not isinstance(trace_raw, dict):
        raise RustReceiptError("trace must be a dict")
    _require_exact_keys(trace_raw, {"routed_to", "event", "written"}, "trace")
    routed_to = _require_str_field(trace_raw, "routed_to", "trace", 4096)
    if _wire_path(routed_to) != (expected_state / B1_TRACES_REL).resolve():
        raise RustReceiptError("trace.routed_to mismatch")
    expected_event = f"bakeoff_query_{expected_mode}"
    if trace_raw.get("event") != expected_event or trace_raw.get("written") is not True:
        raise RustReceiptError("trace event/written evidence mismatch")
    trace = TraceDiagnostics(
        routed_to=routed_to, event=expected_event, written=True)

    # Graph diagnostics (optional but if present must be clean).  In the
    # actual schema, graph diagnostics may be nested in receipt diagnostics
    # rather than a top-level field.  We check the graph receipt's diagnostics
    # if a graph component was requested.
    graph_diag: GraphDiagnostics | None = None
    for receipt in receipts:
        if (
            receipt.component in {"graph", "support"}
            and receipt.status == "executed"
        ):
            diag = receipt.diagnostics
            graph_diag = GraphDiagnostics(
                skipped_path_unsafe=int(diag["skipped_path_unsafe"]),
                skipped_stale=int(diag["skipped_stale"]),
                edge_count=int(diag["edge_count"]),
                saturated=bool(diag["inspect_saturated"]),
            )

    # Support relations (support mode only).
    support_relations: tuple[SupportRelation, ...] = ()
    parent_path: str | None = None
    parent_start: int | None = None
    parent_end: int | None = None
    if expected_mode == "support":
        parent_raw = data.get("parent")
        if not isinstance(parent_raw, dict):
            raise RustReceiptError("support parent must be an object")
        _require_exact_keys(parent_raw, {
            "path", "start_line", "end_line", "confinement",
        }, "support parent")
        pp = parent_raw.get("path")
        if not isinstance(pp, str) or pp not in vis:
            raise RustReceiptError(
                f"parent_path {pp!r} missing or not in visible set")
        psl = parent_raw.get("start_line")
        pel = parent_raw.get("end_line")
        if not isinstance(psl, int) or isinstance(psl, bool) or psl < 1:
            raise RustReceiptError("parent_start_line invalid")
        if not isinstance(pel, int) or isinstance(pel, bool) or pel < 1:
            raise RustReceiptError("parent_end_line invalid")
        if psl > pel:
            raise RustReceiptError("parent start > end")
        if parent_raw.get("confinement") != "validated_under_source_root":
            raise RustReceiptError("support parent confinement marker mismatch")
        parent_path = pp
        parent_start = psl
        parent_end = pel
        sr_raw = data.get("relations")
        if not isinstance(sr_raw, list):
            raise RustReceiptError("support_relations must be a list")
        support_relations = tuple(
            _parse_support_relation(item, vis) for item in sr_raw
        )
        if len(support_relations) != len(evidence):
            raise RustReceiptError("support relation/evidence count mismatch")
        for ev, relation in zip(evidence, support_relations):
            if (ev.path, ev.start_line, ev.end_line) != (
                relation.support_path, relation.support_start_line,
                relation.support_end_line,
            ):
                raise RustReceiptError("support relation does not bind evidence cell")
            if (relation.target_path, relation.target_start_line,
                    relation.target_end_line) != (pp, psl, pel):
                raise RustReceiptError("support relation does not bind parent target")

    return ParsedBakeoffQuery(
        schema_version=sv, mode=mode, request_id=request_id,
        source_root=str(source_root), state_root=str(state_root),
        query=expected_query if expected_mode == "context" else None,
        task_family=(expected_task_family if expected_mode == "context" else None),
        max_results=max_results,
        components_requested=expected_order,
        components_executed=executed,
        receipts=tuple(receipts), evidence=evidence,
        evidence_count=evidence_count,
        rrf_k=rrf_k, rrf_version=rrf_version, rrf_marker=rrf_marker,
        rrf_tie_order=B1_RRF_TIE_ORDER_WIRE,
        rrf_rank_tie_policy=rank_tie_policy,
        rrf_channel_weights=channel_weights,
        rrf_input_normalization=B1_RRF_INPUT_NORMALIZATION,
        rrf_input_rewrites=input_rewrites,
        provider=provider, trace=trace,
        graph_diagnostics=graph_diag,
        support_relations=support_relations,
        parent_path=parent_path, parent_start_line=parent_start,
        parent_end_line=parent_end,
    )


# ===========================================================================
# Source immutability + WSR inventory enforcement
# ===========================================================================


def _is_reparse_or_link(path: Path) -> bool:
    """True if path is a symlink or Windows reparse point."""
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
    if fa & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
        return True
    return False


def _snapshot_source_digests(root: Path) -> dict[str, str]:
    """Compute SHA-256 of every regular source file under root (excluding
    .openlocus/).  Used for before/after source immutability checks."""
    root_resolved = root.resolve(strict=True)
    if not root_resolved.is_dir() or _is_reparse_or_link(root_resolved):
        raise ContractError("source root is not a safe ordinary directory")
    digests: dict[str, str] = {}

    def visit(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise ContractError(f"cannot enumerate source directory {directory}: {exc}") from exc
        for entry in entries:
            full = Path(entry.path)
            rel = full.relative_to(root_resolved).as_posix()
            if rel == B1_WSR_REL:
                continue
            if _is_reparse_or_link(full):
                raise ContractError(f"source entry {rel!r} is a link/reparse point")
            try:
                st = os.lstat(full)
            except OSError as exc:
                raise ContractError(f"cannot stat source entry {rel!r}: {exc}") from exc
            if stat.S_ISDIR(st.st_mode):
                digests[f"{rel}/"] = "directory"
                visit(full)
            elif stat.S_ISREG(st.st_mode):
                try:
                    raw = full.read_bytes()
                except OSError as exc:
                    raise ContractError(f"cannot read source file {rel!r}: {exc}") from exc
                digests[rel] = hashlib.sha256(raw).hexdigest()
            else:
                raise ContractError(f"source entry {rel!r} is a special file")

    visit(root_resolved)
    return digests


def _inventory_entry(path: Path, rel: str) -> tuple[str, str]:
    if _is_reparse_or_link(path):
        raise ContractError(f"WSR entry {rel!r} is a link/reparse point")
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise ContractError(f"cannot stat WSR entry {rel!r}: {exc}") from exc
    if stat.S_ISDIR(st.st_mode):
        return rel + "/", "directory"
    if stat.S_ISREG(st.st_mode):
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ContractError(f"cannot read WSR file {rel!r}: {exc}") from exc
        return rel, f"{len(raw)}:{hashlib.sha256(raw).hexdigest()}"
    raise ContractError(f"WSR entry {rel!r} is a special file")


def _snapshot_subtree(base: Path, relative_to: Path) -> dict[str, str]:
    inventory: dict[str, str] = {}
    stack = [base]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name,
                             reverse=True)
        except OSError as exc:
            raise ContractError(f"cannot enumerate WSR directory {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            rel = path.relative_to(relative_to).as_posix()
            key, value = _inventory_entry(path, rel)
            if key in inventory:
                raise ContractError(f"duplicate WSR inventory path {key!r}")
            inventory[key] = value
            if key.endswith("/"):
                stack.append(path)
    return dict(sorted(inventory.items()))


def _snapshot_index_inventory(root: Path) -> dict[str, str]:
    index_root = root / B1_INDEX_REL
    if not index_root.is_dir() or _is_reparse_or_link(index_root):
        raise ContractError(f"persistent index {B1_INDEX_REL} is missing or unsafe")
    inventory = _snapshot_subtree(index_root, index_root)
    if not inventory:
        raise ContractError("persistent index inventory is empty")
    return inventory


def _index_inventory_digest(inventory: dict[str, str]) -> str:
    canon = json.dumps(inventory, sort_keys=True, separators=(",", ":"))
    return "idx_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def write_index_seal(root: Path) -> dict[str, Any]:
    inventory = _snapshot_index_inventory(root)
    seal = {
        "schema_version": B1_INDEX_SEAL_SCHEMA_VERSION,
        "inventory": inventory,
        "inventory_digest": _index_inventory_digest(inventory),
    }
    path = root / B1_INDEX_SEAL_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_reparse_or_link(path.parent):
        raise ContractError("unsafe B1 seal directory")
    if path.exists() and _is_reparse_or_link(path):
        raise ContractError("unsafe pre-existing B1 index seal")
    path.write_text(json.dumps(seal, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8")
    verify_index_seal(root)
    return seal


def verify_index_seal(root: Path) -> dict[str, Any]:
    path = root / B1_INDEX_SEAL_REL
    if not path.is_file() or _is_reparse_or_link(path):
        raise ContractError("B1 index seal is missing or unsafe")
    try:
        seal = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_reject_duplicate_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, RustReceiptError) as exc:
        raise ContractError(f"cannot parse B1 index seal: {type(exc).__name__}") from exc
    if not isinstance(seal, dict):
        raise ContractError("B1 index seal must be an object")
    if set(seal) != {"schema_version", "inventory", "inventory_digest"}:
        raise ContractError("B1 index seal has a non-closed shape")
    if seal["schema_version"] != B1_INDEX_SEAL_SCHEMA_VERSION:
        raise ContractError("B1 index seal schema mismatch")
    inventory = seal["inventory"]
    if not isinstance(inventory, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in inventory.items()
    ):
        raise ContractError("B1 index seal inventory is malformed")
    if seal["inventory_digest"] != _index_inventory_digest(inventory):
        raise ContractError("B1 index seal digest does not bind its inventory")
    current = _snapshot_index_inventory(root)
    if current != inventory:
        raise ContractError("persistent index inventory changed after cold seal")
    return seal


def initialize_b1_wsr(root: Path) -> None:
    wsr = root / B1_WSR_REL
    wsr.mkdir(parents=True, exist_ok=True)
    if not wsr.is_dir() or _is_reparse_or_link(wsr):
        raise ContractError("B1 WSR is not a safe ordinary directory")
    audit = root / B1_PROVIDER_AUDIT_REL
    audit.parent.mkdir(parents=True, exist_ok=True)
    if _is_reparse_or_link(audit.parent):
        raise ContractError("provider audit directory is unsafe")
    if audit.exists():
        if not audit.is_file() or _is_reparse_or_link(audit) or audit.read_bytes() != b"":
            raise ContractError("provider audit must begin as an empty ordinary file")
    else:
        audit.write_bytes(b"")
    transcripts = root / B1_TRANSCRIPT_DIR_REL
    transcripts.mkdir(parents=True, exist_ok=True)
    if _is_reparse_or_link(transcripts):
        raise ContractError("B1 transcript directory is unsafe")
    enforce_wsr_inventory(root)


def _check_wsr_inventory(
    root: Path, expected_index_sealed: bool = False
) -> list[str]:
    """Strict WSR inventory check.  Returns a list of violations (empty = ok).

    Checks regular files/dirs only under ``root/.openlocus/``:
    * Only expected subdirectories (index, traces) are allowed;
    * No sibling state/symlink/reparse/special/extra files;
    * If expected_index_sealed, the index directory must exist and not have
      been modified since the cold build (the caller checks this by comparing
      digests).
    """
    violations: list[str] = []
    wsr = root / B1_WSR_REL
    if not wsr.exists():
        violations.append(f"WSR {B1_WSR_REL} does not exist")
        return violations
    if not wsr.is_dir():
        violations.append(f"WSR {B1_WSR_REL} is not a directory")
        return violations
    if _is_reparse_or_link(wsr):
        violations.append(f"WSR {B1_WSR_REL} is a symlink/reparse")
        return violations

    try:
        inventory = _snapshot_subtree(wsr, wsr)
        top_entries = {key.rstrip("/").split("/", 1)[0] for key in inventory}
        if not top_entries <= {"index", "traces", "audit", "b1"}:
            violations.append(
                f"unexpected WSR top-level entries: {sorted(top_entries - {'index', 'traces', 'audit', 'b1'})}")
        if "audit/" not in inventory or "audit/embeddings.jsonl" not in inventory:
            violations.append("provider audit inventory is incomplete")
        audit_entries = {
            key for key in inventory if key.startswith("audit/")
        }
        if audit_entries != {"audit/", "audit/embeddings.jsonl"}:
            violations.append(f"provider audit inventory is not closed: {sorted(audit_entries)}")
        empty_audit = f"0:{hashlib.sha256(b'').hexdigest()}"
        if inventory.get("audit/embeddings.jsonl") != empty_audit:
            violations.append("provider audit is not empty")
        if "b1/" not in inventory or "b1/transcripts/" not in inventory:
            violations.append("B1 transcript inventory is incomplete")
        for key in inventory:
            if key.startswith("traces/") and key != "traces/":
                name = key.removeprefix("traces/")
                if key.endswith("/") or not re.fullmatch(r"trajectory-\d{8}\.jsonl", name):
                    violations.append(f"unexpected trace inventory entry {key!r}")
            if key.startswith("b1/") and key not in {
                "b1/", "b1/transcripts/", "b1/index_seal.json",
                "b1/lineage_receipt.json",
            }:
                name = key.removeprefix("b1/transcripts/")
                if key.endswith("/") or not re.fullmatch(
                    r"[A-Za-z0-9_.-]{1,180}\.json", name):
                    violations.append(f"unexpected B1 inventory entry {key!r}")
        if expected_index_sealed:
            verify_index_seal(root)
    except ContractError as exc:
        violations.append(str(exc))
    return violations


def enforce_source_immutability(
    root: Path, before_digests: dict[str, str] | None = None,
) -> dict[str, str]:
    """Before/after source immutability check.

    If ``before_digests`` is None, this is a BEFORE check: snapshot the
    current source digests and return them.  If provided, this is an AFTER
    check: verify the source digests match exactly.

    Raises ContractError on any mutation.
    """
    current = _snapshot_source_digests(root)
    if before_digests is None:
        return current
    if set(current.keys()) != set(before_digests.keys()):
        added = set(current.keys()) - set(before_digests.keys())
        removed = set(before_digests.keys()) - set(current.keys())
        raise ContractError(
            f"source file set changed: added={sorted(added)} "
            f"removed={sorted(removed)}")
    for rel, before_hash in before_digests.items():
        if current.get(rel) != before_hash:
            raise ContractError(
                f"source file {rel!r} content changed (mutation detected)")
    return current


def enforce_wsr_inventory(
    root: Path, expected_index_sealed: bool = False
) -> dict[str, str]:
    """Strict WSR inventory enforcement.  Raises ContractError on violation."""
    violations = _check_wsr_inventory(root, expected_index_sealed)
    if violations:
        raise ContractError(
            f"WSR inventory violations: {'; '.join(violations)}")
    return _snapshot_subtree(root / B1_WSR_REL, root / B1_WSR_REL)


# ===========================================================================
# bakeoff-query invocation
# ===========================================================================


_ENV_ALLOWLIST = (
    "PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "HOME",
    "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA",
)


def _b1_subprocess_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in _ENV_ALLOWLIST if key in os.environ}
    env["OPENLOCUS_ALLOW_REMOTE"] = "0"
    return env


def _safe_request_token(request_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", request_id):
        raise ContractError("unsafe B1 request_id for private transcript")
    return request_id


def _index_digest_if_present(root: Path) -> str | None:
    index = root / B1_INDEX_REL
    if not index.exists():
        return None
    return _index_inventory_digest(_snapshot_index_inventory(root))


def _write_transcript(
    request: AdapterRequest,
    isolated_root: Path,
    *,
    phase: str,
    command_kind: str,
    argv: list[str],
    env_keys: list[str],
    returncode: int | None,
    timed_out: bool,
    stdout: bytes,
    stderr: bytes,
    source_before: dict[str, str],
    source_after: dict[str, str],
    index_before_digest: str | None,
    index_after_digest: str | None,
    local_receipt: dict[str, Any] | None = None,
) -> Path:
    request_id = _safe_request_token(request.run_spec.request_id)
    if phase not in {"prepare", "query"}:
        raise ContractError(f"invalid B1 transcript phase {phase!r}")
    payload = {
        "schema_version": B1_TRANSCRIPT_SCHEMA_VERSION,
        "request_id": request_id,
        "adapter_id": request.adapter_id,
        "task_slug": request.run_spec.task.task_slug,
        "operation": request.run_spec.operation,
        "cache_state": request.run_spec.cache_state,
        "phase": phase,
        "command_kind": command_kind,
        "argv": argv,
        "env_keys": sorted(env_keys),
        "remote_allowed": False,
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout_b64": base64.b64encode(stdout).decode("ascii"),
        "stderr_b64": base64.b64encode(stderr).decode("ascii"),
        "source_before": source_before,
        "source_after": source_after,
        "index_before_digest": index_before_digest,
        "index_after_digest": index_after_digest,
        "local_receipt": local_receipt,
    }
    path = isolated_root / B1_TRANSCRIPT_DIR_REL / f"{request_id}.{phase}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_reparse_or_link(path.parent):
        raise ContractError("unsafe B1 transcript directory")
    if path.exists() and _is_reparse_or_link(path):
        raise ContractError("unsafe pre-existing B1 transcript")
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8")
    return path


def _run_transcribed_command(
    request: AdapterRequest,
    isolated_root: Path,
    *,
    phase: str,
    command_kind: str,
    command: list[str],
    cwd: str | Path | None,
    timeout: float,
) -> bytes:
    source_before = _snapshot_source_digests(isolated_root)
    enforce_wsr_inventory(isolated_root)
    index_before = _index_digest_if_present(isolated_root)
    env = _b1_subprocess_env()
    returncode: int | None = None
    timed_out = False
    stdout = b""
    stderr = b""
    try:
        completed = subprocess.run(
            command, capture_output=True, cwd=cwd, timeout=timeout, env=env,
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    source_after = _snapshot_source_digests(isolated_root)
    index_after = _index_digest_if_present(isolated_root)
    _write_transcript(
        request, isolated_root, phase=phase, command_kind=command_kind,
        argv=command, env_keys=list(env), returncode=returncode,
        timed_out=timed_out, stdout=stdout, stderr=stderr,
        source_before=source_before, source_after=source_after,
        index_before_digest=index_before, index_after_digest=index_after,
    )
    enforce_source_immutability(isolated_root, source_before)
    enforce_wsr_inventory(isolated_root)
    if timed_out:
        raise RuntimeError(f"{command_kind} timed out")
    if returncode != 0:
        raise RuntimeError(f"{command_kind} failed with returncode {returncode}")
    if stderr:
        raise RuntimeError(f"{command_kind} emitted unexpected stderr")
    if not stdout.strip():
        raise RuntimeError(f"{command_kind} produced no stdout")
    return stdout


def _write_local_transcript(
    request: AdapterRequest,
    isolated_root: Path,
    *,
    phase: str,
    command_kind: str,
    local_receipt: dict[str, Any],
) -> None:
    source_before = _snapshot_source_digests(isolated_root)
    enforce_wsr_inventory(isolated_root, expected_index_sealed=True)
    index_before = _index_digest_if_present(isolated_root)
    source_after = _snapshot_source_digests(isolated_root)
    index_after = _index_digest_if_present(isolated_root)
    _write_transcript(
        request, isolated_root, phase=phase, command_kind=command_kind,
        argv=[], env_keys=[], returncode=0, timed_out=False,
        stdout=b"", stderr=b"", source_before=source_before,
        source_after=source_after, index_before_digest=index_before,
        index_after_digest=index_after, local_receipt=local_receipt,
    )
    enforce_source_immutability(isolated_root, source_before)
    enforce_wsr_inventory(isolated_root, expected_index_sealed=True)


def _run_bakeoff_query(
    request: AdapterRequest,
    isolated_root: Path,
    args: list[str],
    *,
    expected_components: frozenset[str],
    expected_mode: str,
    expected_parent: tuple[str, int, int] | None = None,
) -> ParsedBakeoffQuery:
    cli = _find_cli()
    stdout = _run_transcribed_command(
        request, isolated_root, phase="query",
        command_kind="rust_bakeoff_query",
        command=[cli, "bakeoff-query", *args],
        cwd=str(isolated_root.resolve()), timeout=_CLI_TIMEOUT,
    )
    return parse_bakeoff_query(
        stdout, expected_components, _get_visible_files(request), expected_mode,
        request.run_spec.request_id,
        expected_source_root=isolated_root,
        expected_state_root=isolated_root,
        expected_query=(request.run_spec.task.query if expected_mode == "context" else None),
        expected_task_family=(
            request.run_spec.task.task_family if expected_mode == "context" else None),
        expected_max_results=(
            B1_MAX_CANDIDATES if expected_mode == "context"
            else B1_TWO_STEP_MAX_SUPPORT),
    )


_TRANSCRIPT_KEYS = {
    "schema_version", "request_id", "adapter_id", "task_slug", "operation",
    "cache_state", "phase", "command_kind", "argv", "env_keys",
    "remote_allowed", "returncode", "timed_out", "stdout_b64", "stderr_b64",
    "source_before", "source_after", "index_before_digest",
    "index_after_digest", "local_receipt",
}


def load_invocation_transcript(
    request: AdapterRequest,
    isolated_root: Path,
    phase: str,
) -> dict[str, Any]:
    request_id = _safe_request_token(request.run_spec.request_id)
    path = isolated_root / B1_TRANSCRIPT_DIR_REL / f"{request_id}.{phase}.json"
    if not path.is_file() or _is_reparse_or_link(path):
        raise ContractError(f"missing or unsafe B1 {phase} transcript")
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_reject_duplicate_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, RustReceiptError) as exc:
        raise ContractError(f"cannot parse B1 {phase} transcript") from exc
    if not isinstance(data, dict) or set(data) != _TRANSCRIPT_KEYS:
        raise ContractError(f"B1 {phase} transcript has non-closed shape")
    expected_bindings = {
        "schema_version": B1_TRANSCRIPT_SCHEMA_VERSION,
        "request_id": request_id,
        "adapter_id": request.adapter_id,
        "task_slug": request.run_spec.task.task_slug,
        "operation": request.run_spec.operation,
        "cache_state": request.run_spec.cache_state,
        "phase": phase,
        "remote_allowed": False,
    }
    for key, expected in expected_bindings.items():
        if data.get(key) != expected:
            raise ContractError(f"B1 transcript binding mismatch for {key}")
    if not isinstance(data.get("argv"), list) or not all(
        isinstance(item, str) for item in data["argv"]
    ):
        raise ContractError("B1 transcript argv is malformed")
    env_keys = data.get("env_keys")
    if not isinstance(env_keys, list) or env_keys != sorted(set(env_keys)) or not all(
        isinstance(item, str) for item in env_keys
    ):
        raise ContractError("B1 transcript env key inventory is malformed")
    allowed_env_keys = set(_ENV_ALLOWLIST) | {"OPENLOCUS_ALLOW_REMOTE"}
    if any(key not in allowed_env_keys for key in env_keys):
        raise ContractError("non-allowlisted environment leaked into B1 subprocess")
    if data.get("timed_out") is not False or data.get("returncode") != 0:
        raise ContractError("B1 transcript records timeout/nonzero execution")
    for key in ("stdout_b64", "stderr_b64"):
        if not isinstance(data.get(key), str):
            raise ContractError(f"B1 transcript {key} is malformed")
        try:
            base64.b64decode(data[key], validate=True)
        except (ValueError, binascii.Error) as exc:  # type: ignore[name-defined]
            raise ContractError(f"B1 transcript {key} is invalid base64") from exc
    before = data.get("source_before")
    after = data.get("source_after")
    if not isinstance(before, dict) or not isinstance(after, dict) or before != after:
        raise ContractError("B1 transcript source before/after mismatch")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in before.items()):
        raise ContractError("B1 transcript source inventory is malformed")
    if before != _snapshot_source_digests(isolated_root):
        raise ContractError("B1 transcript source inventory does not bind current source")
    command_kind = data.get("command_kind")
    if command_kind not in {
        "rust_index_build", "local_index_seal_verify",
        "rust_bakeoff_query", "local_support_predicate_skip",
    }:
        raise ContractError(f"unknown B1 transcript command_kind {command_kind!r}")
    before_index = data.get("index_before_digest")
    after_index = data.get("index_after_digest")
    if command_kind == "rust_index_build":
        if before_index is not None or not isinstance(after_index, str):
            raise ContractError("cold index build transcript lifecycle mismatch")
        root_text = str(isolated_root.resolve())
        expected_argv = [
            _find_cli(), "index", "build",
            "--source-root", root_text,
            "--state-root", root_text,
            "--json",
        ]
        if data["argv"] != expected_argv:
            raise ContractError("cold index build transcript argv mismatch")
    else:
        if not isinstance(before_index, str) or before_index != after_index:
            raise ContractError("B1 transcript observed index mutation/replacement")
    if after_index != _index_digest_if_present(isolated_root):
        raise ContractError("B1 transcript index digest does not bind current state")
    stdout = base64.b64decode(data["stdout_b64"], validate=True)
    stderr = base64.b64decode(data["stderr_b64"], validate=True)
    if stderr:
        raise ContractError("successful B1 transcript contains stderr")
    if command_kind.startswith("local_"):
        if stdout or data.get("argv") or data.get("env_keys"):
            raise ContractError("local B1 transcript carries subprocess output/env")
        if not isinstance(data.get("local_receipt"), dict):
            raise ContractError("local B1 transcript missing receipt")
    else:
        if not stdout or data.get("local_receipt") is not None:
            raise ContractError("Rust B1 transcript output/receipt mismatch")
        if env_keys != sorted(_b1_subprocess_env()):
            raise ContractError("Rust B1 transcript environment allowlist mismatch")
    data["_stdout_bytes"] = stdout
    return data


def parse_query_transcript(
    request: AdapterRequest,
    isolated_root: Path,
) -> tuple[dict[str, Any], ParsedBakeoffQuery | None]:
    transcript = load_invocation_transcript(request, isolated_root, "query")
    if transcript["command_kind"] == "local_support_predicate_skip":
        receipt = transcript["local_receipt"]
        if receipt != {
            "component": "support",
            "status": "legitimate_skip",
            "reason": "adapter_support_predicate_false",
            "evidence_count": 0,
        }:
            raise ContractError("local support skip receipt mismatch")
        if adapter_supports_support(request.adapter_id):
            raise ContractError("support-capable adapter used local skip transcript")
        return transcript, None
    if transcript["command_kind"] != "rust_bakeoff_query":
        raise ContractError("query transcript does not describe a B1 query")
    mode = request.run_spec.operation
    components = (
        adapter_context_components(request.adapter_id)
        if mode == "context" else adapter_support_components(request.adapter_id))
    parsed = parse_bakeoff_query(
        transcript["_stdout_bytes"], components, _get_visible_files(request),
        mode, request.run_spec.request_id,
        expected_source_root=isolated_root,
        expected_state_root=isolated_root,
        expected_query=(request.run_spec.task.query if mode == "context" else None),
        expected_task_family=(
            request.run_spec.task.task_family if mode == "context" else None),
        expected_max_results=(
            B1_MAX_CANDIDATES if mode == "context"
            else B1_TWO_STEP_MAX_SUPPORT),
    )
    root_text = str(isolated_root.resolve())
    if mode == "context":
        expected_argv = [
            _find_cli(), "bakeoff-query", "context",
            "--source-root", root_text,
            "--state-root", root_text,
            "--query", request.run_spec.task.query,
            "--components", ",".join(_ordered_components(components)),
            "--task-family", request.run_spec.task.task_family,
            "--max-results", str(B1_MAX_CANDIDATES),
            "--json",
        ]
    else:
        expected_argv = [
            _find_cli(), "bakeoff-query", "support",
            "--source-root", root_text,
            "--state-root", root_text,
            "--parent-path", parsed.parent_path or "",
            "--parent-range",
            f"{parsed.parent_start_line}-{parsed.parent_end_line}",
            "--max-results", str(B1_TWO_STEP_MAX_SUPPORT),
            "--json",
        ]
    if transcript["argv"] != expected_argv:
        raise ContractError("B1 query transcript argv mismatch")
    return transcript, parsed


# ===========================================================================
# Candidate construction from parsed Rust evidence
# ===========================================================================


def _evidence_to_candidates(
    evidence: tuple[RustEvidenceItem, ...],
    adapter_id: str,
    descriptor_channels: frozenset[str],
    cap: int,
    *,
    mode: str,
) -> tuple[Candidate, ...]:
    """Convert parsed Rust evidence items to untrusted Candidate objects.

    Normalizes canonical relative path/range/channels into Candidates.  The
    adapter provenance matches the descriptor identity. Every production
    channel is mapped through the frozen canonical map, and the complete
    mapped set must be declared by the adapter descriptor.
    """
    if len(evidence) > cap:
        raise RustReceiptError(
            f"production evidence count {len(evidence)} exceeds cap {cap}")
    cands: list[Candidate] = []
    seen: set[tuple[str, int, int]] = set()
    for ev in evidence:
        if mode == "support":
            if set(ev.channels) != {"graph"}:
                raise RustReceiptError(
                    f"support evidence carries non-production-graph channels: "
                    f"{list(ev.channels)}")
            ch = frozenset({"support"})
        else:
            try:
                ch = frozenset(B1_RAW_CHANNEL_MAP[channel] for channel in ev.channels)
            except KeyError as exc:
                raise RustReceiptError(
                    f"unknown production evidence channel {exc.args[0]!r}") from exc
        if not ch or not ch <= descriptor_channels:
            raise RustReceiptError(
                f"mapped channels {sorted(ch)} not in descriptor "
                f"{sorted(descriptor_channels)}")
        reason = "; ".join(ev.why)[:128] if ev.why else "bakeoff_query_match"
        if len(reason) > 128:
            reason = reason[:128]
        cell = (ev.path, ev.start_line, ev.end_line)
        if cell in seen:
            raise RustReceiptError(f"duplicate production candidate cell {cell}")
        seen.add(cell)
        cands.append(Candidate(
            path=ev.path,
            start_line=ev.start_line,
            end_line=ev.end_line,
            score=ev.score,
            reason=reason,
            channels=ch,
            adapter_provenance=adapter_id,
        ))
    return tuple(cands)


# ===========================================================================
# Binding proposal construction
# ===========================================================================


def _no_evidence_binding(reason: str) -> BindingProposal:
    return BindingProposal(
        proposed_status="no_evidence",
        target_evidence_indices=(),
        support_bindings=(),
        status_reason=reason,
    )


def _context_binding(
    candidates: tuple[Candidate, ...], max_targets: int,
    check_tie: bool = True,
) -> BindingProposal:
    """Build binding for one-shot context (ranked-prefix targets, max 4).
    Zero candidates => no_evidence; cross-path exact top tie => uncertain.
    For two-step context (check_tie=False), always select the top candidate
    as ready (one primary target)."""
    if not candidates:
        return _no_evidence_binding("all executed components returned zero")
    if check_tie:
        top = candidates[0]
        tied_diff_path = [
            c for c in candidates[1:max_targets + 1]
            if c.score == top.score and c.path != top.path
        ]
        if tied_diff_path:
            return BindingProposal(
                proposed_status="uncertain",
                target_evidence_indices=(0,),
                support_bindings=(),
                status_reason="cross-path exact top tie",
            )
    indices = tuple(range(min(len(candidates), max_targets)))
    return BindingProposal(
        proposed_status="ready",
        target_evidence_indices=indices,
        support_bindings=(),
    )


def _support_binding(
    candidates: tuple[Candidate, ...], relations: tuple[SupportRelation, ...],
    max_support: int, bound_target_id: str,
) -> BindingProposal:
    """Build binding for two-step support (parent-bound, max 4 one-hop)."""
    if not candidates:
        return _no_evidence_binding("no support candidates found")
    if len(candidates) != len(relations) or len(candidates) > max_support:
        raise RustReceiptError("support candidates/relations/cap mismatch")
    bindings: list[SupportBinding] = []
    for index, (candidate, relation) in enumerate(zip(candidates, relations)):
        if candidate.normalized_cell() != (
            relation.support_path, relation.support_start_line,
            relation.support_end_line,
        ):
            raise RustReceiptError("support candidate/relation cell mismatch")
        bindings.append(SupportBinding(
            evidence_index=index,
            target_indices=(),
            relation_kind=relation.relation_kind,
            parent_target_id=bound_target_id,
        ))
    sbs = tuple(bindings)
    return BindingProposal(
        proposed_status="ready",
        target_evidence_indices=(),
        support_bindings=sbs,
    )


# ===========================================================================
# Capability ledger construction (V2: all adapters declare 5 capabilities)
# ===========================================================================


def _build_ledger(
    adapter_id: str,
    is_support: bool,
    has_candidates: bool,
    has_target_refs: bool,
    has_support_refs: bool,
    prepare_executed: bool,
) -> dict[str, str]:
    """Build the capability ledger for a V2 cumulative-stack adapter.

    All adapters declare the same 5 capabilities.  The ledger records:
    * prepare_index: executed if lifecycle ran, else legitimate_skip;
    * candidate_search: executed if candidates found, else legitimate_skip
      (executed returning zero is legal — but if the query hook ran and
      produced a result, candidate_search was executed);
    * target_binding: executed if target refs present, else legitimate_skip
      for context with zero candidates;
    * support_expansion: executed if support refs present, else
      legitimate_skip (frozen predicate: support operation AND adapter
      supports support);
    * two_step_support: same as support_expansion but only for support op.
    """
    supports_support = adapter_supports_support(adapter_id)
    ledger: dict[str, str] = {}

    if prepare_executed:
        ledger["prepare_index"] = "executed"
    else:
        ledger["prepare_index"] = "legitimate_skip"

    # candidate_search is always executed when the query hook runs (even if
    # it returns zero candidates).
    ledger["candidate_search"] = "executed"

    if has_target_refs:
        ledger["target_binding"] = "executed"
    elif has_candidates:
        # Candidates found but no target refs (e.g. uncertain with a tie).
        ledger["target_binding"] = "legitimate_skip"
    else:
        # Zero candidates: target_binding is legitimate_skip.
        ledger["target_binding"] = "legitimate_skip"

    if has_support_refs:
        ledger["support_expansion"] = "executed"
    elif is_support and supports_support:
        # Support op ran but no support candidates found.
        ledger["support_expansion"] = "legitimate_skip"
    else:
        # Not a support op or adapter doesn't support support.
        ledger["support_expansion"] = "legitimate_skip"

    if is_support and supports_support and has_support_refs:
        ledger["two_step_support"] = "executed"
    else:
        ledger["two_step_support"] = "legitimate_skip"

    return ledger


# ===========================================================================
# Visible files lookup (frozen fixture definition, no filesystem enumeration)
# ===========================================================================


def _get_visible_files(request: AdapterRequest) -> tuple[str, ...]:
    """Get the frozen visible files for this task from the frozen fixture
    definition (deterministic, no filesystem enumeration in the subprocess)."""
    task_slug = request.run_spec.task.task_slug
    for task in B1_ALL_TASKS:
        if task.task_slug == task_slug:
            return task.visible_files()
    raise ContractError(f"unknown task_slug {task_slug!r}")


# ===========================================================================
# S0-S5 prepare/index hooks (all warm_reuse, persistent BM25 at .openlocus/index)
# ===========================================================================


def _b1_prepare(request: AdapterRequest, isolated_root: Path) -> None:
    """Cold prepare: build persistent BM25 index at .openlocus/index.

    V2: persistent state lives at the cell root (.openlocus/index), NOT a
    sibling directory.  Cold builds the index; warm reuses it (no rebuild).
    """
    if request.run_spec.cache_state != "cold":
        raise RuntimeError("warm_reuse prepare hook must be skipped by Phase A")
    if request.run_spec.operation == "support":
        verify_index_seal(isolated_root)
        _write_local_transcript(
            request, isolated_root, phase="prepare",
            command_kind="local_index_seal_verify",
            local_receipt={
                "component": "prepare_index",
                "status": "executed",
                "action": "verify_without_rebuild",
            },
        )
        return

    if (isolated_root / B1_INDEX_REL).exists():
        raise RuntimeError("cold context found a pre-existing persistent index")
    if (isolated_root / B1_INDEX_SEAL_REL).exists():
        raise RuntimeError("cold context found a pre-existing index seal")
    cli = _find_cli()
    root_text = str(isolated_root.resolve())
    _run_transcribed_command(
        request, isolated_root, phase="prepare",
        command_kind="rust_index_build",
        command=[
            cli, "index", "build",
            "--source-root", root_text,
            "--state-root", root_text,
            "--json",
        ],
        cwd=str(isolated_root.resolve()), timeout=_CLI_TIMEOUT,
    )
    _snapshot_index_inventory(isolated_root)


def _b1_index(request: AdapterRequest, isolated_root: Path) -> None:
    """Unused compatibility hook; B1 uses a single real prepare lifecycle."""
    raise RuntimeError("B1 index hook must not be invoked")


# ===========================================================================
# S0-S5 query hooks (all call bakeoff-query with cumulative component sets)
# ===========================================================================


def _b1_context_query(
    request: AdapterRequest, isolated_root: Path, adapter_id: str,
    descriptor_channels: frozenset[str],
) -> AdapterResult:
    """Context query via bakeoff-query with the adapter's cumulative component
    set.  V2: all context pools go through production RRF; no Python RRF."""
    query = request.run_spec.task.query
    vis = _get_visible_files(request)
    components = adapter_context_components(adapter_id)
    request_id = request.run_spec.request_id

    sealed = (isolated_root / B1_INDEX_SEAL_REL).is_file()
    if sealed:
        verify_index_seal(isolated_root)

    # Invoke bakeoff-query in context mode.
    args = [
        "context",
        "--source-root", str(isolated_root.resolve()),
        "--state-root", str(isolated_root.resolve()),
        "--query", query,
        "--components", ",".join(_ordered_components(components)),
        "--task-family", request.run_spec.task.task_family,
        "--max-results", str(B1_MAX_CANDIDATES),
        "--json",
    ]
    try:
        parsed = _run_bakeoff_query(
            request, isolated_root, args,
            expected_components=components, expected_mode="context")
    except (RuntimeError, RustReceiptError, ContractError) as exc:
        # Configured error: fails the cell (NOT swallowed into ok/no_evidence).
        return AdapterResult(
            status="failed",
            failure_category=f"adapter_exception:{type(exc).__name__}",
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id, False, False, False, False,
                request.run_spec.cache_state != "warm"),
            fallback_provenance=(),
        )

    finally:
        if sealed:
            verify_index_seal(isolated_root)

    # Validate receipts: any error status fails the cell.
    for receipt in parsed.receipts:
        if receipt.status == "error":
            return AdapterResult(
                status="failed",
                failure_category="adapter_exception:FailedResult",
                candidates=(),
                capability_ledger=_build_ledger(
                    adapter_id, False, False, False, False,
                    request.run_spec.cache_state != "warm"),
                fallback_provenance=(),
            )

    # Construct candidates from parsed evidence.
    cands = _evidence_to_candidates(
        parsed.evidence, adapter_id, descriptor_channels, B1_MAX_CANDIDATES,
        mode="context")

    # Build binding proposal.
    if request.run_spec.interaction_mode == "two_step":
        # Two-step context: one primary target (no tie check).
        binding = _context_binding(cands, 1, check_tie=False)
    else:
        binding = _context_binding(cands, B1_ONE_SHOT_MAX_TARGETS)

    has_target_refs = len(binding.target_evidence_indices) > 0
    ledger = _build_ledger(
        adapter_id, False, len(cands) > 0, has_target_refs, False,
        request.run_spec.cache_state != "warm")

    return AdapterResult(
        status="ok", failure_category=None,
        candidates=cands,
        capability_ledger=ledger,
        fallback_provenance=(),
        binding_proposal=binding,
    )


def _b1_support_query(
    request: AdapterRequest, isolated_root: Path, adapter_id: str,
    descriptor_channels: frozenset[str],
    parent_path: str, parent_start: int, parent_end: int,
    bound_target_id: str,
) -> AdapterResult:
    """Support query via bakeoff-query with the support component.  Only
    S4/S5 support support; S0-S3 return legitimate_skip (no_evidence)."""
    supports_support = adapter_supports_support(adapter_id)
    vis = _get_visible_files(request)
    request_id = request.run_spec.request_id

    if not supports_support:
        # S0-S3: support is legitimate_skip (frozen predicate false).
        # No_evidence is legal: all configured executed components returned
        # zero and fusion is empty (no support component was executed).
        _write_local_transcript(
            request, isolated_root, phase="query",
            command_kind="local_support_predicate_skip",
            local_receipt={
                "component": "support",
                "status": "legitimate_skip",
                "reason": "adapter_support_predicate_false",
                "evidence_count": 0,
            },
        )
        return AdapterResult(
            status="ok", failure_category=None,
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id, True, False, False, False,
                request.run_spec.cache_state != "warm"),
            fallback_provenance=(),
            binding_proposal=_no_evidence_binding(
                "adapter does not support support expansion"),
        )

    # S4/S5: invoke bakeoff-query in support mode.
    components = adapter_support_components(adapter_id)
    verify_index_seal(isolated_root)

    args = [
        "support",
        "--source-root", str(isolated_root.resolve()),
        "--state-root", str(isolated_root.resolve()),
        "--parent-path", parent_path,
        "--parent-range", f"{parent_start}-{parent_end}",
        "--max-results", str(B1_TWO_STEP_MAX_SUPPORT),
        "--json",
    ]
    try:
        parsed = _run_bakeoff_query(
            request, isolated_root, args,
            expected_components=components, expected_mode="support",
            expected_parent=(parent_path, parent_start, parent_end))
    except (RuntimeError, RustReceiptError, ContractError) as exc:
        return AdapterResult(
            status="failed",
            failure_category=f"adapter_exception:{type(exc).__name__}",
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id, True, False, False, False,
                request.run_spec.cache_state != "warm"),
            fallback_provenance=(),
        )

    finally:
        verify_index_seal(isolated_root)

    # Validate receipts.
    for receipt in parsed.receipts:
        if receipt.status == "error":
            return AdapterResult(
                status="failed",
                failure_category="adapter_exception:FailedResult",
                candidates=(),
                capability_ledger=_build_ledger(
                    adapter_id, True, False, False, False,
                    request.run_spec.cache_state != "warm"),
                fallback_provenance=(),
            )

    # Validate parent path/range matches what was passed.
    if parsed.parent_path != parent_path:
        raise RustReceiptError(
            f"parent_path {parsed.parent_path!r} != {parent_path!r}")
    if parsed.parent_start_line != parent_start:
        raise RustReceiptError(
            f"parent_start_line {parsed.parent_start_line} != {parent_start}")
    if parsed.parent_end_line != parent_end:
        raise RustReceiptError(
            f"parent_end_line {parsed.parent_end_line} != {parent_end}")

    # Construct support candidates from parsed evidence.
    cands = _evidence_to_candidates(
        parsed.evidence, adapter_id, descriptor_channels,
        B1_TWO_STEP_MAX_SUPPORT, mode="support")
    binding = _support_binding(
        cands, parsed.support_relations, B1_TWO_STEP_MAX_SUPPORT,
        bound_target_id)
    has_support_refs = len(binding.support_bindings) > 0
    ledger = _build_ledger(
        adapter_id, True, len(cands) > 0, False, has_support_refs,
        request.run_spec.cache_state != "warm")

    return AdapterResult(
        status="ok", failure_category=None,
        candidates=cands,
        capability_ledger=ledger,
        fallback_provenance=(),
        binding_proposal=binding,
    )


# ===========================================================================
# Per-adapter query hooks (top-level functions for spawn-picklability)
# ===========================================================================


def _dispatch_query(
    request: AdapterRequest,
    isolated_root: Path,
    adapter_id: str,
    descriptor_channels: frozenset[str],
) -> AdapterResult:
    if request.run_spec.operation == "context":
        return _b1_context_query(
            request, isolated_root, adapter_id, descriptor_channels)
    parent = _read_parent_receipt(request, isolated_root)
    if parent is None:
        return AdapterResult(
            status="failed",
            failure_category="lineage:unknown_parent_target",
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id, True, False, False, False,
                request.run_spec.cache_state != "warm"),
            fallback_provenance=(),
        )
    return _b1_support_query(
        request, isolated_root, adapter_id, descriptor_channels,
        parent["path"], parent["start_line"], parent["end_line"],
        request.run_spec.bound_target_id or "",
    )


def s0_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch_query(
        request, isolated_root, S0_ADAPTER_ID, S0_OUTPUT_CHANNELS)


def s1_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch_query(
        request, isolated_root, S1_ADAPTER_ID, S1_OUTPUT_CHANNELS)


def s2_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch_query(
        request, isolated_root, S2_ADAPTER_ID, S2_OUTPUT_CHANNELS)


def s3_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch_query(
        request, isolated_root, S3_ADAPTER_ID, S3_OUTPUT_CHANNELS)


def s4_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch_query(
        request, isolated_root, S4_ADAPTER_ID, S4_OUTPUT_CHANNELS)


def s5_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch_query(
        request, isolated_root, S5_ADAPTER_ID, S5_OUTPUT_CHANNELS)


def _read_parent_receipt(
    request: AdapterRequest, isolated_root: Path,
) -> dict[str, Any] | None:
    """Read and cross-check the private WSR lineage receipt for two-step
    support.  The runner writes ``.openlocus/b1/lineage_receipt.json`` before
    the support step, binding request/result/target/path/range/output/snapshot
    digests.  The query hook reads and cross-checks before support.

    Returns a dict with keys: path, start_line, end_line.
    Returns None if the receipt is missing (the caller returns a failed
    result — never tgt_unknown).
    """
    receipt_path = isolated_root / B1_LINEAGE_RECEIPT_REL
    if not receipt_path.is_file() or _is_reparse_or_link(receipt_path):
        return None
    try:
        data = json.loads(
            receipt_path.read_bytes().decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, RustReceiptError):
        return None
    if not isinstance(data, dict):
        return None
    if set(data) != {
        "schema_version", "request_id", "parent_result_id",
        "bound_target_id", "target_path", "target_start_line",
        "target_end_line", "snapshot_manifest_digest",
        "parent_canonical_result_hash", "parent_canonical_pack_hash",
    }:
        return None
    if data.get("schema_version") != "product_bakeoff_b1_lineage.v1":
        return None
    # Cross-check: request_id, bound_target_id, snapshot digest.
    if data.get("request_id") != request.run_spec.request_id:
        return None
    btid = request.run_spec.bound_target_id
    if data.get("bound_target_id") != btid:
        return None
    if data.get("parent_result_id") != request.run_spec.parent_result_id:
        return None
    if data.get("snapshot_manifest_digest") != request.run_spec.snapshot_manifest_digest:
        return None
    for key, prefix in (
        ("parent_canonical_result_hash", "crh_"),
        ("parent_canonical_pack_hash", "cph_"),
    ):
        value = data.get(key)
        if not isinstance(value, str) or not re.fullmatch(
                rf"{re.escape(prefix)}[0-9a-f]{{16}}", value):
            return None
    path = data.get("target_path")
    sl = data.get("target_start_line")
    el = data.get("target_end_line")
    vis = _get_visible_files(request)
    if not isinstance(path, str) or path not in set(vis):
        return None
    if not isinstance(sl, int) or isinstance(sl, bool) or sl < 1:
        return None
    if not isinstance(el, int) or isinstance(el, bool) or el < 1:
        return None
    if sl > el:
        return None
    return {"path": path, "start_line": sl, "end_line": el}


# ===========================================================================
# Adapter descriptors and hooks
# ===========================================================================


def _make_descriptor(
    adapter_id: str, capabilities: frozenset[str],
    output_channels: frozenset[str], persistent_state: str,
) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_id=adapter_id,
        adapter_version=ADAPTER_VERSION,
        capabilities=capabilities,
        default_capability="candidate_search",
        supported_languages=SUPPORTED_LANGS,
        persistent_state_behavior=persistent_state,
        execution_mode="process_isolated",
        upstream_revision=B1_UPSTREAM_REVISION,
        spdx_license_state="declared",
        output_channels=output_channels,
    ).validate()


def s0_descriptor() -> AdapterDescriptor:
    return _make_descriptor(S0_ADAPTER_ID, S0_CAPABILITIES, S0_OUTPUT_CHANNELS,
                           S0_PERSISTENT_STATE)


def s1_descriptor() -> AdapterDescriptor:
    return _make_descriptor(S1_ADAPTER_ID, S1_CAPABILITIES, S1_OUTPUT_CHANNELS,
                           S1_PERSISTENT_STATE)


def s2_descriptor() -> AdapterDescriptor:
    return _make_descriptor(S2_ADAPTER_ID, S2_CAPABILITIES, S2_OUTPUT_CHANNELS,
                           S2_PERSISTENT_STATE)


def s3_descriptor() -> AdapterDescriptor:
    return _make_descriptor(S3_ADAPTER_ID, S3_CAPABILITIES, S3_OUTPUT_CHANNELS,
                           S3_PERSISTENT_STATE)


def s4_descriptor() -> AdapterDescriptor:
    return _make_descriptor(S4_ADAPTER_ID, S4_CAPABILITIES, S4_OUTPUT_CHANNELS,
                           S4_PERSISTENT_STATE)


def s5_descriptor() -> AdapterDescriptor:
    return _make_descriptor(S5_ADAPTER_ID, S5_CAPABILITIES, S5_OUTPUT_CHANNELS,
                           S5_PERSISTENT_STATE)


def s0_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s0_query).validate()


def s1_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s1_query).validate()


def s2_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s2_query).validate()


def s3_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s3_query).validate()


def s4_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s4_query).validate()


def s5_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s5_query).validate()


# Registry: adapter_id -> (descriptor_factory, hooks_factory)
B1_ADAPTERS: tuple[tuple[str, Any, Any], ...] = (
    (S0_ADAPTER_ID, s0_descriptor, s0_hooks),
    (S1_ADAPTER_ID, s1_descriptor, s1_hooks),
    (S2_ADAPTER_ID, s2_descriptor, s2_hooks),
    (S3_ADAPTER_ID, s3_descriptor, s3_hooks),
    (S4_ADAPTER_ID, s4_descriptor, s4_hooks),
    (S5_ADAPTER_ID, s5_descriptor, s5_hooks),
)


__all__ = [
    "S0_ADAPTER_ID", "S1_ADAPTER_ID", "S2_ADAPTER_ID",
    "S3_ADAPTER_ID", "S4_ADAPTER_ID", "S5_ADAPTER_ID",
    "s0_descriptor", "s1_descriptor", "s2_descriptor",
    "s3_descriptor", "s4_descriptor", "s5_descriptor",
    "s0_hooks", "s1_hooks", "s2_hooks",
    "s3_hooks", "s4_hooks", "s5_hooks",
    "s0_query", "s1_query", "s2_query",
    "s3_query", "s4_query", "s5_query",
    "_b1_prepare", "_b1_index",
    "B1_ADAPTERS", "_find_cli", "_bakeoff_query_available",
    "_run_bakeoff_query", "parse_bakeoff_query",
    "RustReceiptError", "ComponentReceipt", "RustEvidenceItem",
    "SupportRelation", "GraphDiagnostics", "ProviderDiagnostics",
    "TraceDiagnostics", "ParsedBakeoffQuery",
    "initialize_b1_wsr", "write_index_seal", "verify_index_seal",
    "load_invocation_transcript", "parse_query_transcript",
    "enforce_source_immutability", "enforce_wsr_inventory",
    "_check_wsr_inventory", "_snapshot_source_digests",
    "_is_reparse_or_link",
    "_evidence_to_candidates",
    "_context_binding", "_support_binding", "_no_evidence_binding",
    "_build_ledger", "_get_visible_files", "_read_parent_receipt",
]
