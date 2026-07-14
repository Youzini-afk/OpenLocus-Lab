#!/usr/bin/env python3
"""Product Stack Bakeoff B1 — frozen executable mechanics spec (v2).

V2 supersedes v1 per the oracle PASS-DESIGN in
``.slim/deepwork/product-bakeoff-b1.md``.  The first reported 504/504 result
is VOID; do not preserve its private output or claim a new full result until
the Rust ``bakeoff-query`` subcommand exists and integration is verified.

Frozen parameters (V2 cumulative stacks):

* All six adapters are ``warm_reuse``.  Cold builds persistent BM25 once per
  task/arm/repetition; warm reuses that exact state.  No adapter is stateless.
* S0 persistent BM25; S1 S0+literal text; S2 S1+exact-name AST symbol under
  the frozen identifier predicate; S3 S2+conditional depth-1 graph; S4 S2
  pool plus one-primary bounded support; S5 S3 pool plus the same support
  policy.
* Every context pool, including S0, passes through the production RRF K=60
  variant where exact native-score ties share competition rank (1, 1, 3)
  and verified graph evidence has an explicit weight of 2 (all other
  channels have weight 1).
  No Python RRF, temporary BM25, post-fusion resort, AST-to-text fallback,
  synthesized
  candidate, query-derived path, or fallback provenance is permitted in v2.
* Component receipts are closed: executed (zero is legal), legitimate skip
  only when a frozen predicate is false, or error.  Configured errors fail the
  cell.  ``no_evidence`` is legal only when all configured executed components
  returned zero and fusion is empty.
* Two neutral fixtures (Rust + TypeScript), 12 opaque tasks: 2 each prose,
  literal, symbol, graph, two-step, status.  Exactly one high-entropy
  impossible (no_evidence) and one deliberate equal cross-path top-tie
  (uncertain).  Queries contain no source path or role hint.
* Exact matrix: 10 one-shot × 6 × 3 × 2 = 360; 2 two-step × 6 × 3 × 2 × 2 =
  144; total exactly 504.
* Persistent state at the cell root so ``.openlocus/index`` is WSR.  Seal
  exact index inventory/digests after cold; warm must not rebuild or mutate
  index.  Before/after every production call: source immutability + strict
  WSR inventory.
* One result only: ``mechanics_pass``.  No recall/MRR/composite/arm delta.

Run::

    python -m py_compile eval/product_bakeoff_b1_spec.py
"""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema identity
# ---------------------------------------------------------------------------

B1_SPEC_VERSION = "product_bakeoff_b1.v2.4"
B1_GENERATED_BY = "eval/product_bakeoff_b1_spec.py"
B1_CLAIM_LEVEL = "b1_mechanics_screen_only"

# Re-export canonical schema version for run-spec binding.
from product_bakeoff_contract import SCHEMA_VERSION as _CANONICAL_SCHEMA_VERSION  # noqa: F401,E402

# ---------------------------------------------------------------------------
# Common caps (frozen)
# ---------------------------------------------------------------------------

B1_MAX_CANDIDATES = 8
B1_MAX_EVIDENCE = 8
B1_MAX_TARGETS = 4
B1_MAX_SUPPORT = 4
B1_MAX_RENDER_CHARS = 4096
B1_MAX_RENDER_BYTES = 16384
B1_MAX_RENDER_ESTIMATE = 1024
B1_EPISODE_STEP_CAP = 2
B1_EPISODE_ESTIMATE_CAP = 4096
B1_TIMEOUT_SECONDS = 30.0

# ---------------------------------------------------------------------------
# RRF and ranking (frozen, unchanged deterministic production)
# ---------------------------------------------------------------------------

B1_RRF_K = 60
B1_RRF_DETERMINISTIC = True
# Production RRF marker expected in every bakeoff-query receipt.
B1_RRF_MARKER = "production_rrf_combine_rank_ties_weighted_graph"
B1_RRF_VERSION = (
    "openlocus-retrieval/rrf.rs:K=60:competition_ties_v1:graph_weight_2")
B1_RRF_RANK_TIE_POLICY = "equal_native_score_competition_rank_v1"
B1_RRF_CHANNEL_WEIGHTS = "bm25=1,regex=1,tree_sitter=1,graph=2"
# Deterministic path/range tie ordering: lexicographic path, then ascending
# start_line, then ascending end_line.
B1_TIE_ORDER = ("path", "start_line", "end_line")
B1_RRF_TIE_ORDER_WIRE = "score_desc_path_asc_start_asc_end_asc"
B1_COMPONENT_TIE_ORDER_WIRE = B1_RRF_TIE_ORDER_WIRE
B1_BM25_OVERFETCH_FACTOR = 8
B1_BM25_OVERFETCH_MAX = 64
B1_COMPONENT_EXACT_CELL_DEDUP = True
B1_RRF_INPUT_NORMALIZATION = "contained_span_to_narrowest_path_range_v1"

# ---------------------------------------------------------------------------
# Tie / fallback rules (frozen)
# ---------------------------------------------------------------------------

# Zero candidates (all configured executed components returned zero, fusion
# empty) => explicit no_evidence.
B1_ZERO_CANDIDATES_STATUS = "no_evidence"
# Cross-path exact top tie (same score, different path) => uncertain.
B1_TOP_TIE_STATUS = "uncertain"

# ---------------------------------------------------------------------------
# Pack policies (frozen)
# ---------------------------------------------------------------------------

# S0-S3: ranked-prefix targets (max 4), no support.
B1_ONE_SHOT_MAX_TARGETS = 4
B1_ONE_SHOT_SUPPORT = False
# S4-S5: one primary target plus max 4 one-hop support.
B1_TWO_STEP_PRIMARY_TARGETS = 1
B1_TWO_STEP_MAX_SUPPORT = 4

# ---------------------------------------------------------------------------
# Repetitions and cache sequencing (frozen)
# ---------------------------------------------------------------------------

B1_REPETITIONS = (1, 2, 3)
B1_CACHE_STATES = ("cold", "warm")
# Each repetition uses fresh adapter-specific state; cold then warm reuse same
# state; two-step context/support in each cache cell.
B1_COLD_THEN_WARM_REUSE = True

# ---------------------------------------------------------------------------
# Matrix dimensions (frozen)
# ---------------------------------------------------------------------------

B1_ONE_SHOT_TASK_COUNT = 10
B1_TWO_STEP_TASK_COUNT = 2
B1_ADAPTER_COUNT = 6
B1_REPETITION_COUNT = 3
B1_CACHE_STATE_COUNT = 2
B1_TWO_STEP_STEP_COUNT = 2  # context + support

B1_ONE_SHOT_RECORDS = (
    B1_ONE_SHOT_TASK_COUNT * B1_ADAPTER_COUNT * B1_REPETITION_COUNT
    * B1_CACHE_STATE_COUNT
)  # 10 * 6 * 3 * 2 = 360
B1_TWO_STEP_RECORDS = (
    B1_TWO_STEP_TASK_COUNT * B1_ADAPTER_COUNT * B1_REPETITION_COUNT
    * B1_CACHE_STATE_COUNT * B1_TWO_STEP_STEP_COUNT
)  # 2 * 6 * 3 * 2 * 2 = 144
B1_TOTAL_RECORDS = B1_ONE_SHOT_RECORDS + B1_TWO_STEP_RECORDS  # 504

# ---------------------------------------------------------------------------
# Adapter IDs (frozen S0-S5, all warm_reuse cumulative stacks)
# ---------------------------------------------------------------------------

S0_ADAPTER_ID = "b1_s0_bm25"
S1_ADAPTER_ID = "b1_s1_bm25_text"
S2_ADAPTER_ID = "b1_s2_bm25_text_symbol"
S3_ADAPTER_ID = "b1_s3_bm25_text_symbol_graph"
S4_ADAPTER_ID = "b1_s4_s2pool_support"
S5_ADAPTER_ID = "b1_s5_s3pool_support"

B1_ADAPTER_IDS = (
    S0_ADAPTER_ID,
    S1_ADAPTER_ID,
    S2_ADAPTER_ID,
    S3_ADAPTER_ID,
    S4_ADAPTER_ID,
    S5_ADAPTER_ID,
)
B1_ADAPTER_VERSION = "v2.4"

# Upstream revision (the B0 substrate this screen traverses).
B1_UPSTREAM_REVISION = "b0_substrate"

# ---------------------------------------------------------------------------
# Cumulative component sets per adapter (frozen)
# ---------------------------------------------------------------------------
# These are the component sets each adapter requests from the production
# ``bakeoff-query`` Rust subcommand.  They are CUMULATIVE: each stack adds
# exactly one component to the previous stack's pool (except S4/S5 which add
# support to S2/S3 pools respectively).

# Component identifiers passed to bakeoff-query (closed set).
B1_COMPONENTS = ("bm25", "literal", "symbol", "graph", "support")

# Context component sets (for context operations).  Component names match
# the Rust bakeoff-query CLI: bm25, literal, symbol, graph.
S0_COMPONENTS = frozenset({"bm25"})
S1_COMPONENTS = frozenset({"bm25", "literal"})
S2_COMPONENTS = frozenset({"bm25", "literal", "symbol"})
S3_COMPONENTS = frozenset({"bm25", "literal", "symbol", "graph"})
# S4 context uses the S2 pool; S5 context uses the S3 pool.
S4_CONTEXT_COMPONENTS = frozenset({"bm25", "literal", "symbol"})
S5_CONTEXT_COMPONENTS = frozenset({"bm25", "literal", "symbol", "graph"})
# S4/S5 support uses the support component.
S4_S5_SUPPORT_COMPONENTS = frozenset({"support"})

# ---------------------------------------------------------------------------
# Task family mapping (frozen)
# ---------------------------------------------------------------------------

# 12 logical tasks: 2 each prose, literal text, exact symbol, graph relation,
# two-step support, abstention/status.  Adapter-visible tasks carry no labels.
B1_PHASE_A_TASK_FAMILIES = frozenset({
    "symbol_lookup", "definition_find", "caller_trace", "type_resolution",
    "cross_file_dependency", "refactor_target_find", "ambiguous_target",
    "error_text", "configuration_discovery", "test_discovery", "no_answer",
})
B1_GRAPH_ELIGIBLE_TASK_FAMILIES = frozenset({
    "caller_trace", "cross_file_dependency", "configuration_discovery",
    "test_discovery",
})
B1_IDENTIFIER_PREDICATE = "ascii_identifier_v1"
B1_GRAPH_PREDICATE = "phase_a_graph_task_family_v1"
B1_COMPONENT_ORDER = ("bm25", "literal", "symbol", "graph")
B1_RAW_CHANNEL_MAP = {
    "bm25": "bm25",
    "regex": "text",
    "tree_sitter": "symbol",
    "graph": "graph",
}

# ---------------------------------------------------------------------------
# Writable-state root + index layout (frozen, V2)
# ---------------------------------------------------------------------------
# The writable-state root IS the ``.openlocus`` marker directory.  Persistent
# index lives at ``.openlocus/index``, NOT a sibling directory.  This ensures:
# 1. repo discovery cannot escape to an ancestor repository;
# 2. generated state (traces) is excluded from visible-tree scans;
# 3. the writable_state_root_id is common across comparable arms.

B1_WSR_REL = ".openlocus"
B1_INDEX_REL = ".openlocus/index"
B1_TRACES_REL = ".openlocus/traces"

# Generated state is closed to the production index/traces plus the private
# B1 audit, transcript, index-seal and transient lineage surfaces.
B1_GENERATED_WHITELIST = (".openlocus",)
B1_GENERATED_SUBDIR_WHITELIST = ("index", "traces", "audit", "b1")
B1_TRAJECTORY_PATTERN = "trajectory-"
B1_PROVIDER_AUDIT_REL = ".openlocus/audit/embeddings.jsonl"
B1_TRANSCRIPT_DIR_REL = ".openlocus/b1/transcripts"
B1_INDEX_SEAL_REL = ".openlocus/b1/index_seal.json"
B1_LINEAGE_RECEIPT_REL = ".openlocus/b1/lineage_receipt.json"
B1_PARENT_RESULT_ID_POLICY = "logical_cell_common_across_adapters_v1"
B1_TRANSCRIPT_SCHEMA_VERSION = "product_bakeoff_b1_invocation.v1"
B1_PARENT_RECEIPT_SCHEMA_VERSION = "product_bakeoff_b1_parent_receipt.v1.3"
B1_INDEX_SEAL_SCHEMA_VERSION = "product_bakeoff_b1_index_seal.v1"

# Expected top-level WSR inventory after initialization/cold build.
B1_EXPECTED_INDEX_ENTRIES = frozenset({"index", "traces", "audit", "b1"})

# ---------------------------------------------------------------------------
# Sanitized aggregate schema (frozen, V2 closed)
# ---------------------------------------------------------------------------

B1_AGGREGATE_SCHEMA_VERSION = "product_bakeoff_b1_aggregate.v2.4"

# Public stdout carries ONLY sanitized aggregate (exactly one JSON object).
# No banners, paths, runtime, or assertion details.  Private full
# records/captures/oracles/timings under ignored ``runs/``.
B1_AGGREGATE_KEYS = frozenset({
    "schema_version",
    "b1_spec_version",
    "b1_claim_level",
    "mechanics_pass",
    "total_records",
    "one_shot_records",
    "two_step_records",
    "accepted_count",
    "rejected_count",
    "adapter_count",
    "task_count",
    "repetition_count",
    "cache_state_count",
    "all_six_stacks_passing",
    "all_sentinels_passing",
    "all_two_step_episodes_passing",
    "zero_provider_network_calls",
    "provider_network_call_count",
    "resource_complete_count",
    "same_execution_scoreable_count",
    "canary_present_in_private_only",
    "sentinel_expected",
    "sentinel_passed",
    "all_lineages_valid",
    "privacy_absent",
    "determinism_confirmed",
    "fixture_digest",
    "spec_digest",
    "source_bundle_digest",
    "runtime_bundle_digest",
})

# ---------------------------------------------------------------------------
# Frozen descriptor metadata (V2: all warm_reuse, cumulative channels)
# ---------------------------------------------------------------------------

# ALL six adapters declare the same 5 capabilities.  The capability ledger
# records executed/legitimate_skip per cell based on the frozen predicate
# (operation and component set).
B1_ALL_CAPABILITIES = frozenset({
    "prepare_index", "candidate_search", "target_binding",
    "support_expansion", "two_step_support",
})

# Output channels are CUMULATIVE per stack (the channels that the adapter's
# component pool can produce).  S4 adds "support"; S5 adds "graph"+"support".
S0_OUTPUT_CHANNELS = frozenset({"bm25"})
S1_OUTPUT_CHANNELS = frozenset({"bm25", "text"})
S2_OUTPUT_CHANNELS = frozenset({"bm25", "text", "symbol"})
S3_OUTPUT_CHANNELS = frozenset({"bm25", "text", "symbol", "graph"})
S4_OUTPUT_CHANNELS = frozenset({"bm25", "text", "symbol", "support"})
S5_OUTPUT_CHANNELS = frozenset({"bm25", "text", "symbol", "graph", "support"})

# All six are warm_reuse (persistent BM25 state).
S0_PERSISTENT_STATE = "warm_reuse"
S1_PERSISTENT_STATE = "warm_reuse"
S2_PERSISTENT_STATE = "warm_reuse"
S3_PERSISTENT_STATE = "warm_reuse"
S4_PERSISTENT_STATE = "warm_reuse"
S5_PERSISTENT_STATE = "warm_reuse"

# ---------------------------------------------------------------------------
# Component receipt statuses (closed, mirrors contract CAPABILITY_STATUSES)
# ---------------------------------------------------------------------------

B1_RECEIPT_STATUSES = frozenset({"executed", "legitimate_skip", "error"})
# A configured error (timeout/nonzero/malformed/success=false/disabled/missing)
# fails the cell.
B1_RECEIPT_ERROR_FAILS_CELL = True

# ---------------------------------------------------------------------------
# Expected Rust bakeoff-query JSON schema version (for parser isolation)
# ---------------------------------------------------------------------------

# The orchestrator reconciles exact field names after the Rust writer finishes.
# This is the EXPECTED schema version; the strict parser validates against it.
B1_RUST_SCHEMA_VERSION = "openlocus.bakeoff_query.v2.3"
B1_RUST_SCHEMA_MODES = frozenset({"context", "support"})

# ---------------------------------------------------------------------------
# Pre-score gates (frozen, all must pass before scorer import)
# ---------------------------------------------------------------------------

# The exact set of pre-score gates checked before dynamic scorer import.
# On any gate fail, scorer must remain unimported and run exits nonzero.
B1_PRE_SCORE_GATES = (
    "preflight_converged",
    "matrix_360_records",
    "matrix_144_records",
    "disjoint_union_504",
    "all_records_accepted",
    "all_records_ok",
    "all_resource_complete",
    "require_scoreable_all",
    "source_immutability",
    "wsr_inventory_strict",
    "cold_warm_semantic_equality",
    "repetition_determinism",
    "two_step_lineage_valid",
    "provider_count_zero",
    "privacy_canary_absent",
    "sentinel_expected_passed",
)

# The project owner authorized aggregate-only publication of the synthetic B1
# mechanics result on 2026-07-14.  This does not authorize publishing private
# rows, task/query/path details, receipts, traces, or resource samples, and it
# does not upgrade the B1 mechanics result into a product winner/default or
# effectiveness claim.
B1_SYNTHETIC_PUBLICATION_DECISION = (
    "owner_authorized_aggregate_only_publication"
)

B1_SOURCE_BUNDLE_PATHS = (
    "eval/product_bakeoff_b1_spec.py",
    "eval/product_bakeoff_b1_fixtures.py",
    "eval/product_bakeoff_b1_adapters.py",
    "eval/product_bakeoff_b1_runner.py",
    "eval/product_bakeoff_b1_scorer.py",
    "eval/product_bakeoff_b1_cli.py",
    "eval/product_bakeoff_contract.py",
    "eval/product_bakeoff_conformance.py",
    "crates/openlocus-cli/src/bakeoff_query.rs",
    "crates/openlocus-cli/src/lib.rs",
    "crates/openlocus-ast/src/symbol.rs",
    "crates/openlocus-retrieval/src/rrf.rs",
    "Cargo.lock",
)

# ---------------------------------------------------------------------------
# Digest computation
# ---------------------------------------------------------------------------


def b1_spec_digest() -> str:
    """Compute a deterministic digest of the frozen B1 v2 spec parameters."""
    payload = {
        "spec_version": B1_SPEC_VERSION,
        "caps": {
            "max_candidates": B1_MAX_CANDIDATES,
            "max_evidence": B1_MAX_EVIDENCE,
            "max_targets": B1_MAX_TARGETS,
            "max_support": B1_MAX_SUPPORT,
            "max_render_chars": B1_MAX_RENDER_CHARS,
            "max_render_bytes": B1_MAX_RENDER_BYTES,
            "max_render_estimate": B1_MAX_RENDER_ESTIMATE,
            "episode_step_cap": B1_EPISODE_STEP_CAP,
            "episode_estimate_cap": B1_EPISODE_ESTIMATE_CAP,
            "timeout_seconds": B1_TIMEOUT_SECONDS,
        },
        "rrf": {
            "k": B1_RRF_K,
            "deterministic": B1_RRF_DETERMINISTIC,
            "tie_order": list(B1_TIE_ORDER),
            "marker": B1_RRF_MARKER,
            "version": B1_RRF_VERSION,
            "wire_tie_order": B1_RRF_TIE_ORDER_WIRE,
            "rank_tie_policy": B1_RRF_RANK_TIE_POLICY,
            "channel_weights": B1_RRF_CHANNEL_WEIGHTS,
        },
        "component_normalization": {
            "tie_order": B1_COMPONENT_TIE_ORDER_WIRE,
            "bm25_overfetch_factor": B1_BM25_OVERFETCH_FACTOR,
            "bm25_overfetch_max": B1_BM25_OVERFETCH_MAX,
            "exact_cell_dedup": B1_COMPONENT_EXACT_CELL_DEDUP,
            "rrf_input_normalization": B1_RRF_INPUT_NORMALIZATION,
        },
        "tie_rules": {
            "zero_candidates": B1_ZERO_CANDIDATES_STATUS,
            "top_tie": B1_TOP_TIE_STATUS,
        },
        "pack_policy": {
            "one_shot_max_targets": B1_ONE_SHOT_MAX_TARGETS,
            "one_shot_support": B1_ONE_SHOT_SUPPORT,
            "two_step_primary_targets": B1_TWO_STEP_PRIMARY_TARGETS,
            "two_step_max_support": B1_TWO_STEP_MAX_SUPPORT,
        },
        "repetitions": list(B1_REPETITIONS),
        "cache_states": list(B1_CACHE_STATES),
        "matrix": {
            "one_shot": B1_ONE_SHOT_RECORDS,
            "two_step": B1_TWO_STEP_RECORDS,
            "total": B1_TOTAL_RECORDS,
        },
        "adapters": list(B1_ADAPTER_IDS),
        "adapter_version": B1_ADAPTER_VERSION,
        "components": {
            "s0": sorted(S0_COMPONENTS),
            "s1": sorted(S1_COMPONENTS),
            "s2": sorted(S2_COMPONENTS),
            "s3": sorted(S3_COMPONENTS),
            "s4_context": sorted(S4_CONTEXT_COMPONENTS),
            "s5_context": sorted(S5_CONTEXT_COMPONENTS),
            "s4_s5_support": sorted(S4_S5_SUPPORT_COMPONENTS),
        },
        "channels": {
            "s0": sorted(S0_OUTPUT_CHANNELS),
            "s1": sorted(S1_OUTPUT_CHANNELS),
            "s2": sorted(S2_OUTPUT_CHANNELS),
            "s3": sorted(S3_OUTPUT_CHANNELS),
            "s4": sorted(S4_OUTPUT_CHANNELS),
            "s5": sorted(S5_OUTPUT_CHANNELS),
        },
        "persistent_state": {
            "s0": S0_PERSISTENT_STATE,
            "s1": S1_PERSISTENT_STATE,
            "s2": S2_PERSISTENT_STATE,
            "s3": S3_PERSISTENT_STATE,
            "s4": S4_PERSISTENT_STATE,
            "s5": S5_PERSISTENT_STATE,
        },
        "wsr_rel": B1_WSR_REL,
        "index_rel": B1_INDEX_REL,
        "traces_rel": B1_TRACES_REL,
        "generated_subdirs": list(B1_GENERATED_SUBDIR_WHITELIST),
        "provider_audit_rel": B1_PROVIDER_AUDIT_REL,
        "transcript_dir_rel": B1_TRANSCRIPT_DIR_REL,
        "index_seal_rel": B1_INDEX_SEAL_REL,
        "lineage_receipt_rel": B1_LINEAGE_RECEIPT_REL,
        "parent_result_id_policy": B1_PARENT_RESULT_ID_POLICY,
        "transcript_schema": B1_TRANSCRIPT_SCHEMA_VERSION,
        "parent_receipt_schema": B1_PARENT_RECEIPT_SCHEMA_VERSION,
        "index_seal_schema": B1_INDEX_SEAL_SCHEMA_VERSION,
        "phase_a_task_families": sorted(B1_PHASE_A_TASK_FAMILIES),
        "graph_eligible_task_families": sorted(B1_GRAPH_ELIGIBLE_TASK_FAMILIES),
        "identifier_predicate": B1_IDENTIFIER_PREDICATE,
        "graph_predicate": B1_GRAPH_PREDICATE,
        "raw_channel_map": dict(sorted(B1_RAW_CHANNEL_MAP.items())),
        "rust_schema_version": B1_RUST_SCHEMA_VERSION,
        "aggregate_schema": B1_AGGREGATE_SCHEMA_VERSION,
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "b1spec_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _repo_root(repo_root: Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    return root.resolve()


def b1_source_bundle_digest(repo_root: Path | None = None) -> str:
    """Bind the complete B1 source implementation and its canonical substrate.

    This digest is stable across platforms and intentionally excludes build
    artifacts. Missing, linked, non-file, duplicate or out-of-root entries
    fail closed.
    """
    root = _repo_root(repo_root)
    rows: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for rel in B1_SOURCE_BUNDLE_PATHS:
        if rel in seen:
            raise RuntimeError(f"duplicate B1 source bundle path: {rel}")
        seen.add(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"missing or unsafe B1 source bundle file: {rel}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"B1 source bundle path escapes repo: {rel}") from exc
        raw = path.read_bytes()
        rows.append({
            "path": rel,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    canon = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return "b1src_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def b1_runtime_bundle_digest(
    cli_path: str | Path,
    repo_root: Path | None = None,
) -> str:
    """Bind the source bundle to the exact executable used by a B1 run."""
    binary = Path(cli_path)
    if binary.is_symlink() or not binary.is_file():
        raise RuntimeError(f"missing or unsafe OpenLocus executable: {binary}")
    raw = binary.read_bytes()
    payload = {
        "source_bundle_digest": b1_source_bundle_digest(repo_root),
        "binary_sha256": hashlib.sha256(raw).hexdigest(),
        "binary_bytes": len(raw),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "b1run_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Component-set resolution per adapter + operation
# ---------------------------------------------------------------------------


def adapter_context_components(adapter_id: str) -> frozenset[str]:
    """Return the cumulative context component set for an adapter."""
    if adapter_id == S0_ADAPTER_ID:
        return S0_COMPONENTS
    if adapter_id == S1_ADAPTER_ID:
        return S1_COMPONENTS
    if adapter_id == S2_ADAPTER_ID:
        return S2_COMPONENTS
    if adapter_id == S3_ADAPTER_ID:
        return S3_COMPONENTS
    if adapter_id == S4_ADAPTER_ID:
        return S4_CONTEXT_COMPONENTS
    if adapter_id == S5_ADAPTER_ID:
        return S5_CONTEXT_COMPONENTS
    raise ValueError(f"unknown adapter_id {adapter_id!r}")


def adapter_support_components(adapter_id: str) -> frozenset[str]:
    """Return the support component set for an adapter.

    S0-S3 do NOT include support (their frozen predicate is false); they
    return an empty set, and the support component is ``legitimate_skip``.
    S4/S5 include the support component.
    """
    if adapter_id in (S4_ADAPTER_ID, S5_ADAPTER_ID):
        return S4_S5_SUPPORT_COMPONENTS
    return frozenset()


def adapter_supports_support(adapter_id: str) -> bool:
    """True iff this adapter's pool includes support expansion (S4/S5)."""
    return adapter_id in (S4_ADAPTER_ID, S5_ADAPTER_ID)


__all__ = [
    "B1_SPEC_VERSION", "B1_GENERATED_BY", "B1_CLAIM_LEVEL",
    "B1_MAX_CANDIDATES", "B1_MAX_EVIDENCE", "B1_MAX_TARGETS", "B1_MAX_SUPPORT",
    "B1_MAX_RENDER_CHARS", "B1_MAX_RENDER_BYTES", "B1_MAX_RENDER_ESTIMATE",
    "B1_EPISODE_STEP_CAP", "B1_EPISODE_ESTIMATE_CAP", "B1_TIMEOUT_SECONDS",
    "B1_RRF_K", "B1_RRF_DETERMINISTIC", "B1_TIE_ORDER",
    "B1_RRF_MARKER", "B1_RRF_VERSION", "B1_RRF_TIE_ORDER_WIRE",
    "B1_RRF_RANK_TIE_POLICY", "B1_RRF_CHANNEL_WEIGHTS",
    "B1_COMPONENT_TIE_ORDER_WIRE", "B1_BM25_OVERFETCH_FACTOR",
    "B1_BM25_OVERFETCH_MAX", "B1_COMPONENT_EXACT_CELL_DEDUP",
    "B1_RRF_INPUT_NORMALIZATION",
    "B1_ZERO_CANDIDATES_STATUS", "B1_TOP_TIE_STATUS",
    "B1_ONE_SHOT_MAX_TARGETS", "B1_ONE_SHOT_SUPPORT",
    "B1_TWO_STEP_PRIMARY_TARGETS", "B1_TWO_STEP_MAX_SUPPORT",
    "B1_REPETITIONS", "B1_CACHE_STATES", "B1_COLD_THEN_WARM_REUSE",
    "B1_ONE_SHOT_RECORDS", "B1_TWO_STEP_RECORDS", "B1_TOTAL_RECORDS",
    "B1_ADAPTER_IDS", "B1_ADAPTER_VERSION", "B1_UPSTREAM_REVISION",
    "B1_COMPONENTS",
    "S0_COMPONENTS", "S1_COMPONENTS", "S2_COMPONENTS", "S3_COMPONENTS",
    "S4_CONTEXT_COMPONENTS", "S5_CONTEXT_COMPONENTS", "S4_S5_SUPPORT_COMPONENTS",
    "B1_PHASE_A_TASK_FAMILIES", "B1_GRAPH_ELIGIBLE_TASK_FAMILIES",
    "B1_IDENTIFIER_PREDICATE", "B1_GRAPH_PREDICATE",
    "B1_COMPONENT_ORDER", "B1_RAW_CHANNEL_MAP",
    "B1_WSR_REL", "B1_INDEX_REL", "B1_TRACES_REL",
    "B1_GENERATED_WHITELIST", "B1_GENERATED_SUBDIR_WHITELIST",
    "B1_TRAJECTORY_PATTERN", "B1_EXPECTED_INDEX_ENTRIES",
    "B1_PROVIDER_AUDIT_REL", "B1_TRANSCRIPT_DIR_REL",
    "B1_INDEX_SEAL_REL", "B1_LINEAGE_RECEIPT_REL",
    "B1_PARENT_RESULT_ID_POLICY",
    "B1_TRANSCRIPT_SCHEMA_VERSION", "B1_PARENT_RECEIPT_SCHEMA_VERSION",
    "B1_INDEX_SEAL_SCHEMA_VERSION",
    "B1_AGGREGATE_SCHEMA_VERSION", "B1_AGGREGATE_KEYS",
    "B1_ALL_CAPABILITIES", "B1_RECEIPT_STATUSES", "B1_RECEIPT_ERROR_FAILS_CELL",
    "B1_RUST_SCHEMA_VERSION", "B1_RUST_SCHEMA_MODES",
    "B1_PRE_SCORE_GATES", "B1_SYNTHETIC_PUBLICATION_DECISION",
    "B1_SOURCE_BUNDLE_PATHS",
    "S0_ADAPTER_ID", "S0_OUTPUT_CHANNELS", "S0_CAPABILITIES",
    "S0_PERSISTENT_STATE", "S0_COMPONENTS",
    "S1_ADAPTER_ID", "S1_OUTPUT_CHANNELS", "S1_CAPABILITIES",
    "S1_PERSISTENT_STATE", "S1_COMPONENTS",
    "S2_ADAPTER_ID", "S2_OUTPUT_CHANNELS", "S2_CAPABILITIES",
    "S2_PERSISTENT_STATE", "S2_COMPONENTS",
    "S3_ADAPTER_ID", "S3_OUTPUT_CHANNELS", "S3_CAPABILITIES",
    "S3_PERSISTENT_STATE", "S3_COMPONENTS",
    "S4_ADAPTER_ID", "S4_OUTPUT_CHANNELS", "S4_CAPABILITIES",
    "S4_PERSISTENT_STATE", "S4_CONTEXT_COMPONENTS",
    "S5_ADAPTER_ID", "S5_OUTPUT_CHANNELS", "S5_CAPABILITIES",
    "S5_PERSISTENT_STATE", "S5_CONTEXT_COMPONENTS",
    "b1_spec_digest", "b1_source_bundle_digest", "b1_runtime_bundle_digest",
    "adapter_context_components", "adapter_support_components",
    "adapter_supports_support",
]

# Aliases for backwards compatibility with descriptor factories that reference
# S*_CAPABILITIES (all adapters declare the same 5 capabilities in V2).
S0_CAPABILITIES = B1_ALL_CAPABILITIES
S1_CAPABILITIES = B1_ALL_CAPABILITIES
S2_CAPABILITIES = B1_ALL_CAPABILITIES
S3_CAPABILITIES = B1_ALL_CAPABILITIES
S4_CAPABILITIES = B1_ALL_CAPABILITIES
S5_CAPABILITIES = B1_ALL_CAPABILITIES
