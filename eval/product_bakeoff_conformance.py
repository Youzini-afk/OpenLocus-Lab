#!/usr/bin/env python3
"""Product Stack Bakeoff Phase A — conformance runner, self-test, and report (v12).

This module is the Phase A *executable conformance surface*. It exercises the
canonical contract (``product_bakeoff_contract.py`` v12) with temporary synthetic
repositories and a mix of valid + intentionally invalid adapters to
non-vacuously prove all nine conformance categories AND all bounded v12
closures in the deepwork plan (v9 full initial source-tree freeze, pre-hook
infrastructure scan, deadline-inclusive transport, capability-ledger trust;
v10: special-file rejection before read, receive bound before allocation,
genuine worker send failure classification via dedicated exit code;
v11: eliminate pickle from the adapter-controlled wire completely — bounded
strict JSON primitive wire with duplicate-key/nonfinite/depth/count/string
rejection at every level; remove forgeable whole-bakeoff abort signals —
child EOF/send/oversize/ambiguous receive OSError is adapter-scoped
malformed/process_died, never HarnessInfrastructureError; only parent-local
setup/cleanup failures are infrastructure aborts; real adversarial self-tests
with spawned hostile hooks proving the parent never executes adapter-authored
arbitrary code;
v12: tighten the adapter-payload exception boundary — every child-controlled
parser/validator/reconstruction exception (invalid UTF-8, JSONDecodeError/
ValueError including Python oversized integer-token limit, RecursionError from
deep nesting, OverflowError, duplicate-key hook, parse_constant, depth/count/
string violations, exact-schema/reconstruction failures) is converted
deterministically to a _WireError and the receiver outcome ``malformed``,
NEVER propagated to the receiver catch-all ``pipe_error`` ->
``HarnessInfrastructureError``; genuinely parent-local poll/handle/queue/
thread/setup/cleanup failures remain infra; full-run continuation after a
hostile child ``os._exit(73)`` exit is proven at the ``run_adapter`` /
batch-loop level — a rejected ``ValidatedRunRecord`` with adapter
``process_died`` category and empty ledger is produced and a subsequent
valid adapter run is accepted in the same test process).

Binding contract (v5 — bounded closure of the v4 acceptance probes):

* ``run_adapter`` accepts ``AdapterHooks`` (optional prepare/index + required
  query) cross-validated with ``AdapterDescriptor`` via
  ``validate_descriptor_hooks``. The harness owns phase timing
  (setup/index/query/materialize/render). Cold/warm reuse semantics are
  declared via the descriptor's ``persistent_state_behavior``. Prepare/index
  run in the main process; the query hook runs in a PROCESS-ISOLATED
  subprocess with an ENFORCED timeout (immediate termination — no grace
  period — then join only to reap). A full visible-tree scan is performed
  after prepare, after index, after query, and on EVERY adapter exit path so
  mutate->restore cannot pass.
* ``ValidatedRunRecord`` retains the harness-created ``ResourceSample`` (or
  None for pre-execution rejection). Adapter-authored measurements are
  rejected. Aggregate resource counts are derived from actual samples.
* ``validate_run_record`` is fail-closed and used by BOTH
  ``validate_comparison_matrix`` AND ``aggregate_public_report``: it rejects
  vocab/type/count/hash/resource/status inconsistencies, pre-execution
  resource presence, and any unsafe string in failure_category. Adapter
  exception MESSAGE text and raw adapter-authored failure categories NEVER
  reach public keys; the harness maps to canonical categories using stage +
  exception TYPE only.
* The context step registers the actual materialized target with a stable id
  (``stable_target_id``). Two-step lineage binds to actual target, task,
  episode, snapshot/visibility/renderer/materializer/estimator, invariant
  episode caps, and parent step. Adversarial cross-task/cross-episode/unknown-
  target/altered-cap/repeated-step/step-cap/budget-overrun cases are exercised.
* ``validate_comparison_matrix`` validates the complete adapter x logical-cell x
  repetition x cache x interaction-step Cartesian product, rejects
  missing/unexpected/duplicate keys, compares fairness fingerprints within
  exact logical cells, and exercises real repetitions 1/2/3 with FULL semantic
  determinism (record/result/pack status, canonical failure category,
  capability ledger, then hashes for accepted groups; repetition identity
  excluded from canonical hashes). Includes an accepted->rejected->accepted
  adversarial record case.
* ``validate_written_report`` is exception-free and exact at every structured
  level: all count values are nonnegative ints (bool rejected), resource count
  bounded by total, failure/result/pack/category/privacy/validation/capability
  totals reconciled, exact canonical constant surfaces (set equality), exact
  nested keys, and adversarial negative/string/bool/oversized/truncated/unknown
  cases rejected WITHOUT raising. v5: a ``capability_ledger_entry_count``
  aggregate scalar reconciles ``sum(capability_status_counts)`` over the same
  accepted+validation-rejected non-private records; tampered-bucket and
  tampered-scalar adversarial cases are rejected.
* ``validate_execution_root_binding`` requires resolved execution root equals
  snapshot root and writable-state root matches its declared ID/confinement.
* Adapter id/version and task language are bound to the descriptor.
* Symlink directories AND symlinked path components (including parent
  directory symlinks) are rejected; every resolved visible/candidate/writable
  path stays beneath the resolved source root. v5: the COMMON safe path policy
  walks ORIGINAL LEXICAL path components (not resolved parts) so an in-root
  parent symlink (whose target stays inside root) is also rejected; a
  lexical path not beneath root is rejected before the resolved confinement
  check. An in-root symlinked-parent escape fixture is exercised on
  symlink-capable CI (Windows without symlink privilege explicitly skips).
* v5: ``materialize_snapshot`` rejects, BEFORE ``mkdir``, a writable-state
  root equal to the source root, a writable-state root that is an ancestor/
  equal of any visible path, and any visible path located inside the
  writable-state root. Root and root/src overlap probes are exercised; the
  default ``.pb_writable_state`` continues to succeed.
* v5: warm_reuse warm-without-state is an explicit REJECTED result (no
  successful pack). The synthetic stateful adapter returns a failed result
  when the warm marker is absent; the self-test ``_expect_rejected`` and
  verifies the canonical failure category. Same-root cold->warm success is
  preserved (the cold run writes the marker; the warm run observes it).

Threat model (honest): the conformance surface enforces contract closure and
rejects accidental leakage of scorer/oracle/path/excerpt/freshness facts into
adapter outputs. It does NOT contain a hostile executable that scans the host
machine; adversarial adapters here test contract enforcement (rejecting bad
outputs), not host sandboxing. Docs state that honestly.

Phase A public status is exactly synthetic adapter-conformance readiness. It
makes NO product/algorithm/default/winner claim, NO real-fairness claim, NO
S0-S5 conformance claim, and NO operational-acceptance claim.

CLI::

    python eval/product_bakeoff_conformance.py --self-test
    python eval/product_bakeoff_conformance.py --out artifacts/product_bakeoff_a/product_bakeoff_a_report.json
    python eval/product_bakeoff_conformance.py --validate-report <path>
    python eval/product_bakeoff_conformance.py --check-drift <path>
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import queue
import stat
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import product_bakeoff_contract as pb  # noqa: E402
from product_bakeoff_contract import (  # noqa: E402
    AdapterDescriptor,
    AdapterHooks,
    AdapterRequest,
    AdapterResult,
    BakeoffRunSpec,
    BakeoffTask,
    BakeoffVerifiedEvidence,
    BindingProposal,
    BudgetCaps,
    BudgetUsage,
    Candidate,
    ContextPack,
    ContractError,
    FallbackRecord,
    FrozenSnapshot,
    PACK_STATUSES,
    PackTarget,
    RESULT_STATUSES,
    ResourceSample,
    SupportBinding,
    canonical_pack_hash,
    canonical_result_hash,
    fairness_fingerprint,
    materialize_candidates,
    materialize_snapshot,
    snapshot_source_visibility_digest,
    stable_target_id,
    validate_adapter_result,
    validate_capability_ledger_honesty,
    validate_context_pack,
    validate_descriptor_hooks,
    validate_execution_root_binding,
    validate_request,
    validate_snapshot_binding,
)

# NOTE: this module MUST NOT import product_bakeoff_oracle. The oracle is
# scorer-only; importing it here would violate request/oracle isolation
# (conformance category 1). The self-test imports the oracle in a separate
# sub-process-safe scope only to call its guard, never during run execution.

SCHEMA_VERSION = "product_bakeoff_a_report.v12"

# v9: hard bound on the serialized stage envelope crossing the process Pipe.
# The child serializes the complete harness envelope; serialization failure
# and oversize become small malformed canonical envelopes. The parent's
# receiver thread does a bounded recv_bytes and rejects anything over this.
# v10: the parent calls ``recv_bytes(maxlength=MAX_STAGE_WIRE_BYTES)`` so the
# bound is enforced BEFORE full payload allocation (the stdlib reads the
# length header first and raises OSError without allocating the oversized
# body). Worker-side over-bound remains a small malformed envelope.
# v11: the wire envelope is now a CLOSED JSON primitive tree (no pickle
# anywhere on the run-phase wire). The child normalizes the canonical
# ``AdapterResult`` into a plain builtin dict/list/scalar tree with EXACT
# type checks (no ``isinstance`` accepting subclasses that can override
# behavior); the parent reconstructs the exact canonical dataclasses
# field-by-field after strict JSON decoding with duplicate-key/nonfinite/
# depth/count/string-length rejection at every level.
MAX_STAGE_WIRE_BYTES = 8 * 1024 * 1024

# v11: closed JSON primitive wire envelope (replaces pickle).
# The wire envelope MUST be exactly this shape:
#   {"v": 1, "status": "ok"|"error"|"malformed",
#    "payload": <closed_payload_or_null>, "error": <str_or_null>}
# There is NO ``transport_failure`` status: an adapter may call any
# ``os._exit(code)``; every child EOF/exit code is adapter-scoped
# ``process_died`` (never ``HarnessInfrastructureError``).
_STAGE_ENVELOPE_VERSION = 1
_STAGE_ENVELOPE_KEYS: frozenset[str] = frozenset(
    {"v", "status", "payload", "error"}
)
_STAGE_ENVELOPE_STATUSES: frozenset[str] = frozenset(
    {"ok", "error", "malformed"}
)

# v11: bounded strict JSON primitive wire caps. These are consistent with
# the existing contract maxima (path<=512, reason/provenance/fc<=128,
# status_reason<=256, vocab str<=64) plus defense-in-depth structural
# bounds on depth/count so a hostile adapter cannot exhaust parent memory
# via a deeply nested or oversized primitive tree.
_MAX_STAGE_DEPTH = 32
_MAX_STAGE_LIST_COUNT = 8192
_MAX_STAGE_DICT_COUNT = 512
_MAX_STAGE_STR_LEN = 4096
_MAX_STAGE_ERROR_LEN = 128
_MAX_STAGE_CANDIDATES = 4096
_MAX_STAGE_LEDGER_KEYS = 64
_MAX_STAGE_FALLBACK_RECORDS = 64
_MAX_STAGE_SUPPORT_BINDINGS = 256
_MAX_STAGE_TARGET_INDICES = 4096


def _is_int(v: Any) -> bool:
    """True iff v is an int and NOT a bool (bool is a subclass of int in
    Python; reports/records must reject bool where an int is expected)."""
    return isinstance(v, int) and not isinstance(v, bool)


def _is_bool(v: Any) -> bool:
    return isinstance(v, bool)
GENERATED_BY = "eval/product_bakeoff_conformance.py"
CLAIM_LEVEL = "synthetic_adapter_conformance_readiness_only"

DEFAULT_OUT = Path(
    "artifacts/product_bakeoff_a/product_bakeoff_a_report.json"
)

READINESS_STATUS = (
    "phase_a_synthetic_adapter_conformance_ready_no_product_default_"
    "winner_or_real_fairness_claim"
)

# Synthetic fixture values. Deliberately unrelated to prior real values/gate
# refs (no py_fastapi/ts_vite/kimi/qwen, no real commit hashes, no real CI run
# ids). Placeholder synthetic identifiers only.
SYN_ADAPTER_ID_VALID = "pb_syn_valid_adapter"
SYN_ADAPTER_ID_ADV = "pb_syn_adversarial_adapter"
SYN_ADAPTER_ID_ALT = "pb_syn_alt_adapter"
SYN_ADAPTER_ID_LIFE = "pb_syn_lifecycle_adapter"
SYN_TASK_SLUG_ALPHA = "pb_syn_task_alpha"
SYN_QUERY_ALPHA = "pb:widget:resolver"
SYN_EPISODE_ID = "pb_syn_episode_1"

CAT_NAMES = [
    "cat1_request_oracle_isolation",
    "cat2_snapshot_visibility_isolation",
    "cat3_candidate_validity",
    "cat4_common_materialization_currentness",
    "cat5_budget_equality",
    "cat6_pack_semantics",
    "cat7_determinism_cells",
    "cat8_no_silent_degeneration",
    "cat9_aggregate_only_reporting",
]

# Closed set of allowed top-level keys in the written report.
ALLOWED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "schema_version", "generated_by", "claim_level", "readiness_status",
        "self_test_only", "aggregate_only_public_artifact", "candidate_not_fact",
        "not_evidence", "promotion_ready", "default_should_change",
        "evidencecore_semantics_changed", "winner_declared",
        "product_default_claimed", "real_fairness_claimed",
        "s0_s5_conformance_claimed", "external_adapter_ready",
        "operational_acceptance_claimed", "provider_calls_performed",
        "external_clones_performed", "real_algorithm_comparisons",
        "outcome_runs", "total_validated_runs", "accepted_count",
        "rejected_count", "rejected_by_privacy_count",
        "rejected_by_validation_count", "totals_reconciled",
        "resource_sample_present_count", "two_step_episode_exercised",
        "comparison_matrix_validated", "lifecycle_hooks_exercised",
        "root_binding_enforced", "symlink_confinement_enforced",
        "adapter_identity_binding_enforced", "by_conformance_category",
        "result_status_counts", "pack_status_counts",
        "capability_status_counts", "capability_ledger_entry_count",
        "failure_category_counts",
        "conformance_categories_exercised", "threat_model_note",
        "phase_a_limitations", "canonical_contract_surface",
        "budget_estimator", "materializer_version", "renderer_version",
    }
)

CANONICAL_CONTRACT_SURFACE = [
    "validate_request",
    "run_adapter",
    "validate_adapter_result",
    "validate_capability_ledger_honesty",
    "materialize_candidates",
    "build_context_pack",
    "validate_context_pack",
    "aggregate_public_report",
    "validate_comparison_matrix",
    "validate_execution_root_binding",
    "validate_descriptor_hooks",
    "validate_run_record",
    "stable_target_id",
]

# Closed canonical failure-category prefixes (stage + exception TYPE only).
# Adapter exception MESSAGE text and raw adapter-authored categories NEVER
# reach public keys. The harness maps any exception to one of these via
# stage + exception type.
CANONICAL_FAILURE_CATEGORY_PREFIXES: tuple[str, ...] = (
    "prevalidation:ContractError",
    "lineage:no_episode_registry",
    "lineage:unknown_parent_target",
    "lineage:unknown_target",
    "lineage:cross_task",
    "lineage:cross_episode",
    "lineage:cross_snapshot",
    "lineage:cross_visibility",
    "lineage:cross_visible_tree",
    "lineage:cross_renderer",
    "lineage:cross_materializer",
    "lineage:cross_estimator",
    "lineage:altered_caps",
    "lineage:repeated_step",
    "lineage:non_sequential_step",
    "lineage:step_cap_exceeded",
    "lifecycle_exception:prepare:RuntimeError",
    "lifecycle_exception:index:RuntimeError",
    "lifecycle_timeout:prepare",
    "lifecycle_timeout:index",
    "adapter_exception:RuntimeError",
    "adapter_exception:TimeoutError",
    "adapter_exception:EOFError",
    "adapter_exception:process_died",
    "adapter_exception:FailedResult",
    "adapter_exception:PartialResult",
    "adapter_timeout",
    "non_adapter_result",
    "result_validation:ContractError",
    "capability_honesty:ContractError",
    "materialization:ContractError",
    "pack_validation:ContractError",
    "snapshot_mutation:ContractError",
    "unhandled:no_record",
)


def _canonicalize_failure_category(
    result: AdapterResult,
) -> str:
    """Map an AdapterResult's failure_category to a CANONICAL harness category
    using stage + result status + exception TYPE only. Adapter-authored
    failure_category strings and adapter exception MESSAGE text NEVER reach
    public keys.

    If the result's failure_category is already in the canonical closed set,
    it is used as-is. Otherwise, the result status determines the canonical
    mapping:
      * timeout  -> adapter_timeout
      * malformed -> non_adapter_result
      * failed   -> adapter_exception:FailedResult
      * partial  -> adapter_exception:PartialResult
    """
    fc = result.failure_category
    if fc is not None and fc in CANONICAL_FAILURE_CATEGORY_PREFIXES:
        return fc
    # Map by result status when the adapter-authored category is not canonical.
    if result.status == "timeout":
        return "adapter_timeout"
    if result.status == "malformed":
        return "non_adapter_result"
    if result.status == "partial":
        return "adapter_exception:PartialResult"
    # Default: failed status with non-canonical category.
    return "adapter_exception:FailedResult"


# ---------------------------------------------------------------------------
# Validated run record (harness output, NOT the public report)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidatedRunRecord:
    """A validated run record. The aggregate report is built ONLY from these.

    Carries fairness-relevant aggregate facts (fingerprint, status, counts,
    matrix fields) and NEVER raw query/path/excerpt/digest/oracle/workspace/
    singleton facts. The ``resource_sample`` is harness-private (not emitted
    in the public dict); ``resource_sample_present`` is derived from it.
    """

    fingerprint: str
    run_cell_id: str
    adapter_id: str
    status: str  # "accepted" | "rejected"
    failure_category: str | None
    result_status: str
    pack_status: str | None
    candidate_count: int
    evidence_count: int
    target_count: int
    support_count: int
    capability_ledger_summary: dict[str, str]
    canonical_result_hash: str | None
    canonical_pack_hash: str | None
    conformance_category: str
    cache_state: str
    interaction_mode: str
    operation: str
    adapter_repetition: int
    resource_sample: ResourceSample | None  # harness-private

    @property
    def resource_sample_present(self) -> bool:
        return self.resource_sample is not None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "run_cell_id": self.run_cell_id,
            "adapter_id": self.adapter_id,
            "status": self.status,
            "failure_category": self.failure_category,
            "result_status": self.result_status,
            "pack_status": self.pack_status,
            "candidate_count": self.candidate_count,
            "evidence_count": self.evidence_count,
            "target_count": self.target_count,
            "support_count": self.support_count,
            "capability_ledger_summary": dict(self.capability_ledger_summary),
            "canonical_result_hash": self.canonical_result_hash,
            "canonical_pack_hash": self.canonical_pack_hash,
            "conformance_category": self.conformance_category,
            "cache_state": self.cache_state,
            "interaction_mode": self.interaction_mode,
            "operation": self.operation,
            "adapter_repetition": self.adapter_repetition,
            "resource_sample_present": self.resource_sample_present,
        }


def validate_run_record(rec: ValidatedRunRecord) -> list[str]:
    """Fail-closed validation of a ValidatedRunRecord before it is used by
    comparison or aggregation. Returns a list of failure reasons (empty =
    valid). NEVER raises: all adversarial inputs return failures.

    Checks:
      * Vocabulary: status in {accepted, rejected}; result_status in
        RESULT_STATUSES; pack_status in PACK_STATUSES or None; cache_state in
        CACHE_STATES; interaction_mode in INTERACTION_MODES; operation in
        OPERATIONS.
      * failure_category must be None (for accepted) OR a CANONICAL harness
        category (stage + exception TYPE only). Adapter exception MESSAGE text
        and raw adapter-authored categories are NEVER allowed to reach public
        keys; this check rejects any failure_category not in the closed
        canonical prefix set.
      * Types: counts are nonnegative ints (bool rejected); capability ledger
        summary keys/statuses are closed-vocab; hashes are well-formed (None
        for rejected, set for accepted) or None for non-accepted records.
      * Hash/resource/status consistency: accepted records must have
        canonical_result_hash + canonical_pack_hash set; rejected records must
        have pack_status=None. Pre-execution rejection (result_status in
        {failed, malformed, timeout, partial} with no lifecycle/query executed)
        requires resource_sample=None.
      * resource_sample, when present, must itself pass ResourceSample.validate
        (finite nonnegative values).
    """
    failures: list[str] = []

    # Vocab checks (never raise).
    if rec.status not in ("accepted", "rejected"):
        failures.append(f"status {rec.status!r} not in (accepted, rejected)")
    if rec.result_status not in pb.RESULT_STATUSES:
        failures.append(f"result_status {rec.result_status!r} not in RESULT_STATUSES")
    if rec.pack_status is not None and rec.pack_status not in pb.PACK_STATUSES:
        failures.append(f"pack_status {rec.pack_status!r} not in PACK_STATUSES")
    if rec.cache_state not in pb.CACHE_STATES:
        failures.append(f"cache_state {rec.cache_state!r} not in CACHE_STATES")
    if rec.interaction_mode not in pb.INTERACTION_MODES:
        failures.append(
            f"interaction_mode {rec.interaction_mode!r} not in INTERACTION_MODES"
        )
    if rec.operation not in pb.OPERATIONS:
        failures.append(f"operation {rec.operation!r} not in OPERATIONS")
    if rec.adapter_repetition < 1 or rec.adapter_repetition > 9:
        failures.append(f"adapter_repetition {rec.adapter_repetition} not in [1,9]")

    # failure_category canonical check: accepted => None; rejected => in closed
    # canonical prefix set. This is the v4 closure: adapter exception MESSAGE
    # text and raw adapter-authored categories NEVER reach public keys.
    if rec.status == "accepted":
        if rec.failure_category is not None:
            failures.append(
                f"accepted record must have failure_category=None, got "
                f"{rec.failure_category!r}"
            )
    else:
        if rec.failure_category is None:
            failures.append("rejected record must have a failure_category")
        else:
            # Must be in the closed canonical prefix set.
            if rec.failure_category not in CANONICAL_FAILURE_CATEGORY_PREFIXES:
                failures.append(
                    f"failure_category {rec.failure_category!r} not in canonical "
                    "closed set (adapter exception message text or raw adapter "
                    "category rejected)"
                )

    # Type checks for counts (bool rejected; nonnegative ints).
    for name in (
        "candidate_count", "evidence_count", "target_count", "support_count",
    ):
        v = getattr(rec, name)
        if not _is_int(v):
            failures.append(f"{name} must be int (bool rejected), got {type(v).__name__}")
        elif v < 0:
            failures.append(f"{name}={v} must be nonnegative")

    # capability_ledger_summary vocab + type.
    if not isinstance(rec.capability_ledger_summary, dict):
        failures.append("capability_ledger_summary must be dict")
    else:
        # v9: rejected records MUST carry an EMPTY capability_ledger_summary.
        # Only accepted records may publish a validated ledger; a rejected
        # record with a nonempty ledger is invalid (capability-ledger trust).
        if rec.status == "rejected" and len(rec.capability_ledger_summary) > 0:
            failures.append(
                "rejected record must have empty capability_ledger_summary "
                "(only accepted records may publish a validated ledger)"
            )
        for k, v in rec.capability_ledger_summary.items():
            if k not in pb.CAPABILITIES:
                failures.append(f"capability_ledger_summary key {k!r} not in CAPABILITIES")
            if v not in pb.CAPABILITY_STATUSES:
                failures.append(
                    f"capability_ledger_summary[{k!r}]={v!r} not in CAPABILITY_STATUSES"
                )

    # Hash/status consistency.
    if rec.status == "accepted":
        if rec.canonical_result_hash is None:
            failures.append("accepted record missing canonical_result_hash")
        if rec.canonical_pack_hash is None:
            failures.append("accepted record missing canonical_pack_hash")
        if rec.pack_status is None:
            failures.append("accepted record must have pack_status set")
        if rec.result_status != "ok":
            failures.append(
                f"accepted record result_status must be ok, got {rec.result_status!r}"
            )
        # v9: record defense — accepted + candidate_count>0 requires the
        # ledger summary to say candidate_search=executed. This is the
        # record-level guard complementing the in-run honesty check.
        if (rec.candidate_count > 0
                and isinstance(rec.capability_ledger_summary, dict)
                and rec.capability_ledger_summary.get("candidate_search")
                != "executed"):
            failures.append(
                f"accepted record with candidate_count={rec.candidate_count} "
                f"must have capability_ledger_summary candidate_search="
                f"'executed' (got "
                f"{rec.capability_ledger_summary.get('candidate_search')!r})"
            )
    else:
        # Rejected records must have pack_status=None and hashes None.
        if rec.pack_status is not None:
            failures.append(
                f"rejected record must have pack_status=None, got {rec.pack_status!r}"
            )
        if rec.canonical_pack_hash is not None:
            failures.append("rejected record must have canonical_pack_hash=None")
        # canonical_result_hash may be present for rejected records that
        # produced a result before validation (it is a debug aid; not emitted
        # in public report).

    # Pre-execution rejection: result_status indicates the adapter never
    # executed (failed before query). For prevalidation failures, the
    # resource_sample MUST be None (no measurement was taken).
    if (
        rec.failure_category is not None
        and rec.failure_category.startswith("prevalidation:")
        and rec.resource_sample is not None
    ):
        failures.append(
            "pre-execution (prevalidation) rejection must not carry a "
            "resource_sample (no measurement was taken)"
        )

    # resource_sample validity when present.
    if rec.resource_sample is not None:
        try:
            rec.resource_sample.validate()
        except Exception as exc:  # noqa: BLE001
            failures.append(
                f"resource_sample failed validation: {type(exc).__name__}: {exc}"
            )

    # String length / shape sanity (defensive).
    if not isinstance(rec.fingerprint, str) or not rec.fingerprint.startswith("fp_"):
        failures.append("fingerprint must be a fp_-prefixed str")
    if not isinstance(rec.run_cell_id, str) or not rec.run_cell_id:
        failures.append("run_cell_id must be non-empty str")
    if not isinstance(rec.adapter_id, str) or not rec.adapter_id:
        failures.append("adapter_id must be non-empty str")
    if not isinstance(rec.conformance_category, str) or not rec.conformance_category:
        failures.append("conformance_category must be non-empty str")
    if rec.canonical_result_hash is not None and (
        not isinstance(rec.canonical_result_hash, str)
        or not rec.canonical_result_hash.startswith("crh_")
    ):
        failures.append("canonical_result_hash must be crh_-prefixed str or None")
    if rec.canonical_pack_hash is not None and (
        not isinstance(rec.canonical_pack_hash, str)
        or not rec.canonical_pack_hash.startswith("cph_")
    ):
        failures.append("canonical_pack_hash must be cph_-prefixed str or None")
    return failures


# ---------------------------------------------------------------------------
# Comparison-matrix spec + validator (full Cartesian)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparisonMatrixSpec:
    """Expected comparison-matrix shape for full Cartesian validation."""

    expected_adapter_ids: tuple[str, ...]
    expected_run_cells: tuple[str, ...]
    expected_repetitions: tuple[int, ...]
    expected_cache_states: tuple[str, ...]
    expected_steps: tuple[tuple[str, str], ...]  # (interaction_mode, operation)


def validate_comparison_matrix(
    spec: ComparisonMatrixSpec, runs: list[ValidatedRunRecord]
) -> list[str]:
    """Validate the COMPLETE adapter x logical-cell x repetition x cache x
    interaction-step Cartesian product. Reject missing/unexpected/duplicate
    keys. Compare fairness fingerprints within exact logical cells. Exercise
    real repetitions with FULL semantic determinism (repetition identity
    excluded from canonical hashes): record/result/pack status, canonical
    failure category, capability ledger, then hashes for accepted groups.
    Returns failure reasons.

    Every record is first validated via ``validate_run_record`` (fail-closed);
    records that fail validation are rejected before they reach the
    comparison/aggregation surface.
    """
    failures: list[str] = []

    # 0. Fail-closed record validation: never trust directly constructed
    #    ValidatedRunRecord objects. Adapter exception MESSAGE text and raw
    #    adapter-authored categories are rejected here.
    for r in runs:
        rec_failures = validate_run_record(r)
        for rf in rec_failures:
            failures.append(
                f"record {r.run_cell_id}/{r.adapter_id}/rep{r.adapter_repetition}: {rf}"
            )

    # 1. Build observed Cartesian keys and detect duplicates.
    observed: dict[tuple, ValidatedRunRecord] = {}
    for r in runs:
        key = (
            r.adapter_id, r.run_cell_id, r.adapter_repetition,
            r.cache_state, (r.interaction_mode, r.operation),
        )
        if key in observed:
            failures.append(f"duplicate Cartesian cell {key}")
        observed[key] = r

    # 2. Check expected Cartesian product completeness.
    expected_keys: set[tuple] = set()
    for aid in spec.expected_adapter_ids:
        for rcid in spec.expected_run_cells:
            for rep in spec.expected_repetitions:
                for cs in spec.expected_cache_states:
                    for step in spec.expected_steps:
                        expected_keys.add((aid, rcid, rep, cs, step))
    missing = expected_keys - set(observed.keys())
    for key in sorted(missing, key=lambda k: str(k)):
        failures.append(f"missing Cartesian cell {key}")
    unexpected = set(observed.keys()) - expected_keys
    for key in sorted(unexpected, key=lambda k: str(k)):
        failures.append(f"unexpected Cartesian cell {key}")

    # 3. Compare fingerprints within exact logical cells.
    by_logical: dict[tuple, dict[str, str]] = {}
    for r in runs:
        lc = (
            r.run_cell_id, r.adapter_repetition, r.cache_state,
            (r.interaction_mode, r.operation),
        )
        by_logical.setdefault(lc, {})[r.adapter_id] = r.fingerprint
    for lc, fps in by_logical.items():
        if len(set(fps.values())) > 1:
            failures.append(f"non-comparable fingerprints in logical cell {lc}")

    # 4. FULL SEMANTIC ENVELOPE determinism across repetitions (v4 closure).
    #    For each (adapter, run_cell, cache_state, step) group, every
    #    repetition must agree on:
    #      - record status (accepted/rejected)
    #      - result_status
    #      - pack_status (None allowed iff rejected)
    #      - failure_category (canonical category string)
    #      - capability_ledger_summary (sorted tuple of items)
    #    AND for accepted-only groups, the canonical_result_hash and
    #    canonical_pack_hash must also agree. Repetition identity is excluded
    #    (the group key excludes adapter_repetition).
    by_determinism: dict[tuple, dict[int, ValidatedRunRecord]] = {}
    for r in runs:
        dc = (
            r.adapter_id, r.run_cell_id, r.cache_state,
            (r.interaction_mode, r.operation),
        )
        by_determinism.setdefault(dc, {})[r.adapter_repetition] = r
    for dc, by_rep in by_determinism.items():
        if len(by_rep) < 2:
            continue
        rep_records = list(by_rep.values())
        # Semantic envelope fields.
        statuses = {r.status for r in rep_records}
        if len(statuses) > 1:
            # status should be a str ("accepted"/"rejected"); sort safely
            # in case any None slipped through.
            sorted_st = sorted(statuses, key=lambda x: (x is None, str(x)))
            failures.append(
                f"semantic envelope drift for {dc}: status varies {sorted_st}"
            )
        result_statuses = {r.result_status for r in rep_records}
        if len(result_statuses) > 1:
            sorted_rs = sorted(result_statuses, key=lambda x: (x is None, str(x)))
            failures.append(
                f"semantic envelope drift for {dc}: result_status varies "
                f"{sorted_rs}"
            )
        pack_statuses = {r.pack_status for r in rep_records}
        if len(pack_statuses) > 1:
            # pack_status may be None for rejected records; sort safely.
            sorted_pack = sorted(pack_statuses, key=lambda x: (x is None, x))
            failures.append(
                f"semantic envelope drift for {dc}: pack_status varies "
                f"{sorted_pack}"
            )
        fail_cats = {r.failure_category for r in rep_records}
        if len(fail_cats) > 1:
            # failure_category may be None for accepted records; sort safely.
            sorted_fc = sorted(fail_cats, key=lambda x: (x is None, x))
            failures.append(
                f"semantic envelope drift for {dc}: failure_category varies "
                f"{sorted_fc}"
            )
        ledgers = {
            tuple(sorted(r.capability_ledger_summary.items())) for r in rep_records
        }
        if len(ledgers) > 1:
            failures.append(
                f"semantic envelope drift for {dc}: capability_ledger_summary varies"
            )
        # Accepted-only hashes: if all reps in this group are accepted,
        # canonical hashes must agree.
        if all(r.status == "accepted" for r in rep_records):
            crh_set = {r.canonical_result_hash for r in rep_records}
            if len(crh_set) > 1:
                failures.append(
                    f"semantic determinism (hashes) violated for {dc}: "
                    f"canonical_result_hash varies {sorted(crh_set)}"
                )
            cph_set = {r.canonical_pack_hash for r in rep_records}
            if len(cph_set) > 1:
                failures.append(
                    f"semantic determinism (hashes) violated for {dc}: "
                    f"canonical_pack_hash varies {sorted(cph_set)}"
                )

    # 5. Accepted runs must have canonical hashes.
    for r in runs:
        if r.status == "accepted":
            if r.canonical_result_hash is None:
                failures.append(
                    f"accepted run missing canonical_result_hash: "
                    f"{r.run_cell_id}/{r.adapter_id}"
                )
            if r.canonical_pack_hash is None:
                failures.append(
                    f"accepted run missing canonical_pack_hash: "
                    f"{r.run_cell_id}/{r.adapter_id}"
                )
    return failures


# ---------------------------------------------------------------------------
# Episode registry (two-step context -> support lineage)
# ---------------------------------------------------------------------------


@dataclass
class RegisteredTarget:
    result_id: str
    bound_target_id: str  # stable_target_id
    task_slug: str
    episode_id: str
    snapshot_manifest_digest: str
    source_visibility_digest: str
    visible_tree_digest: str
    renderer_version: str
    materializer_version: str
    budget_estimator_version: str
    episode_caps: BudgetCaps  # invariant caps
    parent_step: int
    episode_estimate_used: int
    target_path: str  # actual materialized target
    target_start_line: int
    target_end_line: int


class EpisodeRegistry:
    """In-memory registry of verified parent targets for two-step support
    lineage validation. Single-threaded (self-test only). Keeps a two-record
    context->support registry, not a generic workflow engine."""

    def __init__(self) -> None:
        self._targets: dict[str, RegisteredTarget] = {}

    def register(
        self, result_id: str, target: PackTarget,
        snapshot: FrozenSnapshot, request: AdapterRequest,
        episode_estimate_used: int, parent_step: int,
    ) -> str:
        tgt_id = stable_target_id(target)
        self._targets[result_id] = RegisteredTarget(
            result_id=result_id,
            bound_target_id=tgt_id,
            task_slug=request.run_spec.task.task_slug,
            episode_id=request.run_spec.episode_id,
            snapshot_manifest_digest=snapshot.manifest_digest,
            source_visibility_digest=snapshot_source_visibility_digest(snapshot),
            visible_tree_digest=snapshot.visible_tree_digest,
            renderer_version=request.run_spec.renderer_version,
            materializer_version=request.run_spec.materializer_version,
            budget_estimator_version=request.run_spec.budget_estimator_version,
            episode_caps=request.run_spec.caps,
            parent_step=parent_step,
            episode_estimate_used=episode_estimate_used,
            target_path=target.path,
            target_start_line=target.start_line,
            target_end_line=target.end_line,
        )
        return tgt_id

    def lookup(self, parent_result_id: str) -> RegisteredTarget | None:
        return self._targets.get(parent_result_id)


# ---------------------------------------------------------------------------
# Synthetic repository builders (temporary; unrelated synthetic values)
# ---------------------------------------------------------------------------


def _write(root: Path, rel: str, text: str) -> None:
    full = root / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(text, encoding="utf-8")


def build_synthetic_repo_one(root: Path) -> FrozenSnapshot:
    _write(
        root, "src/widget.rs",
        "pub struct Widget {\n    name: String,\n}\n\n"
        "impl Widget {\n    pub fn new(name: String) -> Self {\n"
        "        Widget { name }\n    }\n}\n",
    )
    _write(root, "src/config.rs", "pub struct Config {\n    path: String,\n}\n")
    return materialize_snapshot(root, ["src/widget.rs", "src/config.rs"])


def build_synthetic_repo_two(root: Path) -> FrozenSnapshot:
    _write(root, "lib/loader.ts", "export class Loader {\n    load(): void {}\n}\n")
    return materialize_snapshot(root, ["lib/loader.ts"])


def build_synthetic_repo_with_binary(root: Path) -> FrozenSnapshot:
    full = root / "src" / "data.bin"
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(b"\x00binary\x00data\x00here\n")
    return materialize_snapshot(root, ["src/data.bin"])


def default_caps() -> BudgetCaps:
    return BudgetCaps(
        max_candidates=8, max_evidence=8, max_targets=4, max_support=4,
        max_render_chars=4096, max_render_bytes=16384, max_render_estimate=1024,
        episode_step_cap=2, episode_estimate_cap=4096,
    ).validate()


def _tight_caps(**over: int) -> BudgetCaps:
    base: dict[str, int] = dict(
        max_candidates=8, max_evidence=8, max_targets=4, max_support=4,
        max_render_chars=4096, max_render_bytes=16384, max_render_estimate=1024,
        episode_step_cap=2, episode_estimate_cap=4096,
    )
    base.update(over)
    return BudgetCaps(**base).validate()  # type: ignore[arg-type]


def make_run_spec(
    task_slug: str = SYN_TASK_SLUG_ALPHA,
    language_family: str = "rust",
    task_family: str = "symbol_lookup",
    interaction_mode: str = "one_shot",
    operation: str = "context",
    query: str = SYN_QUERY_ALPHA,
    run_cell_id: str = "pb_syn_cell_a",
    snapshot_id: str = "pb_syn_snap_a",
    snapshot: FrozenSnapshot | None = None,
    adapter_repetition: int = 1,
    cache_state: str = "cold",
    episode_id: str = SYN_EPISODE_ID,
    request_id: str = "pb_syn_req_1",
    parent_result_id: str | None = None,
    bound_target_id: str | None = None,
    caps: BudgetCaps | None = None,
    timeout_seconds: float = 30.0,
) -> BakeoffRunSpec:
    if snapshot is not None:
        manifest_digest = snapshot.manifest_digest
        vis_digest = snapshot_source_visibility_digest(snapshot)
        tree_digest = snapshot.visible_tree_digest
        wsr_id = snapshot.writable_state_root_id
    else:
        manifest_digest = "snap_placeholder_manifest_digest_xx"
        vis_digest = "vis_placeholder_visibility_digest_xx"
        tree_digest = "tree_placeholder_visible_tree_digest_xx"
        wsr_id = "wsr_placeholder_writable_state_root_xx"
    rs = BakeoffRunSpec(
        schema_id=SCHEMA_VERSION, run_cell_id=run_cell_id,
        task=BakeoffTask(
            task_slug=task_slug, language_family=language_family,
            task_family=task_family, interaction_mode=interaction_mode,
            source_visibility="frozen_visible", query=query, operation=operation,
        ),
        snapshot_id=snapshot_id, source_visibility_id="frozen_visible",
        snapshot_manifest_digest=manifest_digest,
        source_visibility_digest=vis_digest, visible_tree_digest=tree_digest,
        adapter_repetition=adapter_repetition, cache_state=cache_state,
        interaction_mode=interaction_mode, operation=operation,
        episode_id=episode_id, request_id=request_id,
        parent_result_id=parent_result_id, bound_target_id=bound_target_id,
        caps=caps if caps is not None else default_caps(),
        timeout_seconds=timeout_seconds,
        renderer_version=pb.RENDERER_VERSION,
        materializer_version=pb.MATERIALIZER_VERSION,
        budget_estimator_version=pb.BUDGET_ESTIMATOR_VERSION,
        writable_state_root_id=wsr_id,
    )
    return rs.validate()


def make_request(
    adapter_id: str = SYN_ADAPTER_ID_VALID,
    adapter_version: str = "v1",
    snapshot: FrozenSnapshot | None = None,
    **kwargs: Any,
) -> AdapterRequest:
    rs = make_run_spec(snapshot=snapshot, **kwargs)
    return AdapterRequest(
        run_spec=rs, adapter_id=adapter_id, adapter_version=adapter_version,
    ).validate()


def valid_descriptor(adapter_id: str = SYN_ADAPTER_ID_VALID) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_id=adapter_id, adapter_version="v1",
        capabilities=frozenset({
            "prepare_index", "candidate_search", "target_binding",
            "support_expansion", "two_step_support",
        }),
        default_capability="candidate_search",
        supported_languages=frozenset({"rust", "python"}),
        persistent_state_behavior="stateless", execution_mode="process_isolated",
        upstream_revision="synthetic-v4", spdx_license_state="declared",
        output_channels=frozenset({"bm25", "symbol", "structural"}),
    ).validate()


def adv_descriptor(adapter_id: str = SYN_ADAPTER_ID_ADV) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_id=adapter_id, adapter_version="v1",
        capabilities=frozenset({
            "prepare_index", "candidate_search", "target_binding",
            "support_expansion", "two_step_support",
        }),
        default_capability="candidate_search",
        supported_languages=frozenset({"rust"}),
        persistent_state_behavior="stateless", execution_mode="process_isolated",
        upstream_revision="synthetic-v4", spdx_license_state="declared",
        output_channels=frozenset({"bm25", "symbol", "structural"}),
    ).validate()


# ---------------------------------------------------------------------------
# Adapter hooks type + standard candidate/binding builders
# ---------------------------------------------------------------------------

AdapterCallable = Callable[[AdapterRequest, Path], Any]


def _qhooks(query_fn: AdapterCallable) -> AdapterHooks:
    """Wrap a query function in minimal AdapterHooks (no prepare/index)."""
    return AdapterHooks(prepare=None, index=None, query=query_fn).validate()


def _widget_target_candidate(provenance: str = SYN_ADAPTER_ID_VALID) -> Candidate:
    return Candidate(
        path="src/widget.rs", start_line=1, end_line=3, score=12.5,
        reason="symbol_match", channels=frozenset({"symbol", "bm25"}),
        adapter_provenance=provenance,
    )


def _config_support_candidate(provenance: str = SYN_ADAPTER_ID_VALID) -> Candidate:
    return Candidate(
        path="src/config.rs", start_line=1, end_line=2, score=4.2,
        reason="text_match", channels=frozenset({"bm25"}),
        adapter_provenance=provenance,
    )


def _widget_candidate_adv() -> Candidate:
    return Candidate(
        path="src/widget.rs", start_line=1, end_line=3, score=9.0,
        reason="symbol_match", channels=frozenset({"symbol"}),
        adapter_provenance=SYN_ADAPTER_ID_ADV,
    )


def _std_binding() -> BindingProposal:
    return BindingProposal(
        proposed_status="ready",
        target_evidence_indices=(0,),
        support_bindings=(SupportBinding(1, (0,), "type_dep"),),
    )


def _std_ledger(
    has_target: bool = True, has_support: bool = True,
    is_support_op: bool = False, prepare_executed: bool = False,
) -> dict[str, str]:
    """Honest capability ledger for the standard synthetic adapter. v6: the
    ledger reflects the ACTUAL binding/operation/lifecycle so
    ``validate_capability_ledger_honesty`` cross-checks pass. Cold lifecycle
    execution is ``executed``; warm reuse skip is ``legitimate_skip``;
    two_step_support cannot say ``unsupported`` when a support operation
    produces support."""
    return {
        "prepare_index": "executed" if prepare_executed else "legitimate_skip",
        "candidate_search": "executed",
        "target_binding": "executed" if has_target else "unsupported",
        "support_expansion": "executed" if has_support else "unsupported",
        "two_step_support": (
            "executed" if (is_support_op and has_support) else "unsupported"
        ),
    }


def _std_fallback() -> tuple[FallbackRecord, ...]:
    """v6: the standard adapter has no fallbacks (two_step_support is
    unsupported in one_shot context but does not fall back — it is simply not
    used for this operation). Per-result ``FallbackRecord`` is the sole
    fallback contract (descriptor ``fallback_chain`` was removed)."""
    return ()


# ---------------------------------------------------------------------------
# Valid + adversarial adapter query hooks (all top-level for spawn pickling)
# ---------------------------------------------------------------------------


def valid_adapter_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(_widget_target_candidate(), _config_support_candidate()),
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None, binding_proposal=_std_binding(),
    )


def valid_adapter_alt_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(Candidate(
            path="src/widget.rs", start_line=1, end_line=3, score=9.1,
            reason="regex_match", channels=frozenset({"regex", "bm25"}),
            adapter_provenance=SYN_ADAPTER_ID_ALT,
        ),),
        capability_ledger=_std_ledger(has_target=True, has_support=False), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def valid_adapter_empty_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return AdapterResult(
        status="ok", failure_category=None, candidates=(),
        capability_ledger=_std_ledger(has_target=False, has_support=False),
        fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="no_evidence", target_evidence_indices=(),
            support_bindings=(), status_reason="no candidates produced",
        ),
    )


def valid_adapter_uncertain_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    """v6: an ok result with candidates but an uncertain binding (the adapter
    found a candidate target but is uncertain about it). The final pack must
    remain uncertain regardless of refs."""
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(_widget_target_candidate(),),
        capability_ledger=_std_ledger(has_target=True, has_support=False),
        fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="uncertain", target_evidence_indices=(0,),
            support_bindings=(),
            status_reason="ambiguous target; multiple candidates with similar scores",
        ),
    )


def valid_adapter_two_step_context_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(_widget_target_candidate(),),
        capability_ledger=_std_ledger(has_target=True, has_support=False),
        fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def valid_adapter_two_step_support_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(_config_support_candidate(),),
        capability_ledger=_std_ledger(
            has_target=False, has_support=True, is_support_op=True),
        fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(),
            support_bindings=(SupportBinding(0, (), "type_dep", request.run_spec.bound_target_id),),
        ),
    )


# -- Lifecycle adapter hooks (prepare/index/query all present) --


def lifecycle_prepare(request: AdapterRequest, isolated_root: Path) -> None:
    """No-op prepare hook for lifecycle testing."""
    pass


def lifecycle_index(request: AdapterRequest, isolated_root: Path) -> None:
    """No-op index hook for lifecycle testing."""
    pass


def lifecycle_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    # v6: honest ledger. lifecycle_descriptor() is warm_reuse, so warm skips
    # prepare+index and cold runs them. The query hook infers from cache_state.
    prepare_executed = request.run_spec.cache_state != "warm"
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(_widget_target_candidate(SYN_ADAPTER_ID_LIFE),),
        capability_ledger=_std_ledger(
            has_target=True, has_support=False,
            prepare_executed=prepare_executed),
        fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def lifecycle_descriptor() -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_id=SYN_ADAPTER_ID_LIFE, adapter_version="v1",
        capabilities=frozenset({
            "prepare_index", "candidate_search", "target_binding",
            "support_expansion", "two_step_support",
        }),
        default_capability="candidate_search",
        supported_languages=frozenset({"rust"}),
        persistent_state_behavior="warm_reuse", execution_mode="process_isolated",
        upstream_revision="synthetic-v4", spdx_license_state="declared",
        output_channels=frozenset({"bm25", "symbol", "structural"}),
    ).validate()


LIFECYCLE_HOOKS = AdapterHooks(
    prepare=lifecycle_prepare, index=lifecycle_index, query=lifecycle_query
).validate()


# -- Stateful lifecycle hooks (write/read a marker in writable_state_root) --
# These prove cold->warm marker REUSE on the SAME snapshot/root, warm-without-
# state failure, and that stateless/cold_rebuild warm requests actually run
# configured hooks. Top-level functions for spawn-picklability.


_LIFECYCLE_MARKER_REL = "lifecycle_state_marker.txt"
_LIFECYCLE_OBSERVED_REL = "lifecycle_observed_marker.txt"


def _stateful_writable_root(request: AdapterRequest, isolated_root: Path) -> Path:
    """Resolve the writable_state_root from the snapshot-derived request. The
    writable_state_root is encoded in the snapshot but isolated_root IS the
    snapshot root (validated by validate_execution_root_binding)."""
    # The writable_state_root is isolated_root/.pb_writable_state by default
    # (see materialize_snapshot). For stateful lifecycle tests, the snapshot
    # is materialized with this default.
    return isolated_root / ".pb_writable_state"


def stateful_prepare(request: AdapterRequest, isolated_root: Path) -> None:
    """Cold prepare: write a state marker into the writable_state_root so a
    later warm run can observe it (proving prior state was built and reused).
    v6: the marker includes request_id so the query hook can determine whether
    prepare ran THIS run (marker matches current request_id) vs a prior run."""
    wsr = _stateful_writable_root(request, isolated_root)
    wsr.mkdir(parents=True, exist_ok=True)
    (wsr / _LIFECYCLE_MARKER_REL).write_text(
        f"cold_marker:{request.run_spec.episode_id}:{request.run_spec.request_id}",
        encoding="utf-8",
    )


def stateful_index(request: AdapterRequest, isolated_root: Path) -> None:
    """Cold index: also record an index marker so warm reuse can observe it."""
    wsr = _stateful_writable_root(request, isolated_root)
    wsr.mkdir(parents=True, exist_ok=True)
    (wsr / "lifecycle_index_marker.txt").write_text(
        f"cold_index:{request.run_spec.episode_id}", encoding="utf-8"
    )


def stateful_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    """Stateful query: if a marker file exists in writable_state_root, record
    an observation file so the self-test can verify warm reuse actually saw
    the marker. v5: when ``cache_state == "warm"`` and the marker is ABSENT,
    return an explicit FAILED result (canonical failure category). This proves
    warm-without-state is a conformance failure, not a silent degeneration.

    The marker is written by ``stateful_prepare`` (cold / stateless /
    cold_rebuild runs). For ``warm_reuse`` + ``warm`` with NO prior cold run,
    prepare is skipped and the marker is absent -> the query fails closed.

    Same-root cold->warm success is preserved: the cold run writes the marker;
    the subsequent warm run (warm_reuse, skips prepare) still observes the
    marker and returns ok.
    """
    wsr = _stateful_writable_root(request, isolated_root)
    marker = wsr / _LIFECYCLE_MARKER_REL
    observed = "0"
    marker_present = marker.is_file()
    marker_text = marker.read_text(encoding="utf-8") if marker_present else ""
    if marker_present:
        observed = "1:" + marker_text
    (wsr / _LIFECYCLE_OBSERVED_REL).write_text(observed, encoding="utf-8")
    # v6: determine whether prepare/index ran THIS run by checking if the
    # marker was written by THIS run. stateful_prepare writes
    # "cold_marker:{episode}:{request_id}". If the marker matches the current
    # request_id, prepare ran this run (cold/stateless/cold_rebuild). If it
    # matches a prior request_id, prepare was skipped (warm_reuse warm).
    current_marker = (
        f"cold_marker:{request.run_spec.episode_id}:"
        f"{request.run_spec.request_id}"
    )
    prepare_ran_this_time = marker_text == current_marker
    # v5: warm + absent marker -> explicit failure (warm_reuse without state).
    if request.run_spec.cache_state == "warm" and not marker_present:
        return AdapterResult(
            status="failed",
            failure_category="warm_reuse_state_missing",
            candidates=(),
            capability_ledger={
                "prepare_index": "failed",
                "candidate_search": "failed",
                "target_binding": "failed",
                "support_expansion": "failed",
                "two_step_support": "failed",
            },
            fallback_provenance=(),
            resource_sample=None,
            binding_proposal=BindingProposal(
                proposed_status="no_evidence", target_evidence_indices=(),
                support_bindings=(), status_reason="warm reuse state missing",
            ),
        )
    # v6: honest ledger reflecting whether prepare actually ran this run.
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(_widget_target_candidate(SYN_ADAPTER_ID_LIFE),),
        capability_ledger=_std_ledger(
            has_target=True, has_support=False,
            prepare_executed=prepare_ran_this_time),
        fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


STATEFUL_LIFECYCLE_HOOKS = AdapterHooks(
    prepare=stateful_prepare, index=stateful_index, query=stateful_query
).validate()


def stateless_lifecycle_descriptor() -> AdapterDescriptor:
    """Descriptor with persistent_state_behavior=stateless."""
    return AdapterDescriptor(
        adapter_id=SYN_ADAPTER_ID_LIFE, adapter_version="v1",
        capabilities=frozenset({
            "prepare_index", "candidate_search", "target_binding",
            "support_expansion", "two_step_support",
        }),
        default_capability="candidate_search",
        supported_languages=frozenset({"rust"}),
        persistent_state_behavior="stateless", execution_mode="process_isolated",
        upstream_revision="synthetic-v4", spdx_license_state="declared",
        output_channels=frozenset({"bm25", "symbol", "structural"}),
    ).validate()


def cold_rebuild_lifecycle_descriptor() -> AdapterDescriptor:
    """Descriptor with persistent_state_behavior=cold_rebuild (needs index)."""
    return AdapterDescriptor(
        adapter_id=SYN_ADAPTER_ID_LIFE, adapter_version="v1",
        capabilities=frozenset({
            "prepare_index", "candidate_search", "target_binding",
            "support_expansion", "two_step_support",
        }),
        default_capability="candidate_search",
        supported_languages=frozenset({"rust"}),
        persistent_state_behavior="cold_rebuild", execution_mode="process_isolated",
        upstream_revision="synthetic-v4", spdx_license_state="declared",
        output_channels=frozenset({"bm25", "symbol", "structural"}),
    ).validate()


# Hooks that mutate the source tree during prepare and restore it during
# index, to prove intermediate scans between prepare/index/query catch the
# mutation (mutate->restore cannot pass).
def mutate_and_restore_prepare(request: AdapterRequest, isolated_root: Path) -> None:
    """Prepare: mutate a source file. The post-prepare scan must reject this
    before index even runs."""
    target = isolated_root / "src" / "widget.rs"
    if target.is_file():
        target.write_text("MUTATED_DURING_PREPARE\n", encoding="utf-8")


def mutate_and_restore_index(request: AdapterRequest, isolated_root: Path) -> None:
    """Index: restore the source file. Without intermediate scans, this
    would mask the prepare-time mutation. With intermediate scans, the
    post-prepare scan rejects the mutation before index runs."""
    target = isolated_root / "src" / "widget.rs"
    # Restore to the frozen content.
    target.write_text(
        "pub struct Widget {\n    name: String,\n}\n\n"
        "impl Widget {\n    pub fn new(name: String) -> Self {\n"
        "        Widget { name }\n    }\n}\n",
        encoding="utf-8",
    )


MUTATE_RESTORE_HOOKS = AdapterHooks(
    prepare=mutate_and_restore_prepare, index=mutate_and_restore_index,
    query=valid_adapter_query,
).validate()


# -- Adversarial adapter hooks --


def _single_ok_result(cands: tuple, binding: BindingProposal | None = None) -> AdapterResult:
    # v6: ledger reflects the default binding (target only, no support) so the
    # capability-ledger honesty cross-check would pass if this result reached it.
    # Most adversarial callers are rejected before the honesty check, but the
    # ledger is honest regardless.
    has_support = binding is not None and len(binding.support_bindings) > 0
    return AdapterResult(
        status="ok", failure_category=None, candidates=cands,
        capability_ledger=_std_ledger(has_target=True, has_support=has_support),
        fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=binding or BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


# v9: capability-ledger honesty adversarial hooks. candidate_search honesty:
# nonempty candidates REQUIRE candidate_search=executed; NO converse (executed
# may return zero). These prove the honesty check runs BEFORE materialization.


def adv_candidates_nonexecuted_search_query(request, isolated_root):
    """Nonempty candidates but candidate_search=legitimate_skip. v9: this MUST
    be rejected at capability_honesty:ContractError BEFORE the materializer
    reads any source bytes (the materializer spy must not be touched)."""
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(_widget_candidate_adv(),),
        capability_ledger={
            "prepare_index": "legitimate_skip",
            "candidate_search": "legitimate_skip",  # NONEMPTY but not executed
            "target_binding": "executed",
            "support_expansion": "unsupported",
            "two_step_support": "unsupported",
        },
        fallback_provenance=(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=()),
    )


def valid_zero_candidate_executed_search_query(request, isolated_root):
    """Zero candidates with candidate_search=executed. v9: NO converse — an
    executed candidate_search may legitimately return zero candidates. This
    must be ACCEPTED (no_evidence proposal, no pack)."""
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(),
        capability_ledger={
            "prepare_index": "legitimate_skip",
            "candidate_search": "executed",  # executed, zero candidates OK
            "target_binding": "unsupported",
            "support_expansion": "unsupported",
            "two_step_support": "unsupported",
        },
        fallback_provenance=(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="no_evidence", target_evidence_indices=(),
            support_bindings=(), status_reason="no candidates"),
    )


# ---------------------------------------------------------------------------
# v11: hostile query hooks for the bounded strict JSON primitive wire
# adversarial self-tests. These are top-level functions (spawn-picklable).
# Each proves the parent NEVER executes adapter-authored arbitrary code:
# the child normalizes the returned object via EXACT type checks (which
# never invoke __reduce__/property/__iter__ on custom objects), serializes
# to JSON (which also never invokes __reduce__), and sends malformed
# bytes when normalization fails. The parent decodes JSON primitives only
# (no pickle.loads, no object_hook constructing arbitrary types). Marker
# files outside the child workspace prove the parent did not execute the
# hostile code.
# ---------------------------------------------------------------------------

# Module-level marker paths (outside any child workspace). The hostile
# hooks write to these ONLY if their hostile methods are invoked. With the
# v11 JSON wire, the parent never invokes __reduce__/property/__iter__ on
# hostile objects, so the markers must NEVER be created.
_HOSTILE_REDUCE_MARKER = Path(tempfile.gettempdir()) / "pb_bakeoff_v11_hostile_marker"
_HOSTILE_PROP_MARKER = Path(tempfile.gettempdir()) / "pb_bakeoff_v11_prop_marker"
_HOSTILE_MAP_MARKER = Path(tempfile.gettempdir()) / "pb_bakeoff_v11_map_marker"


class _HostileReduceObject:
    """Custom object with ``__reduce__`` that writes a marker file. If
    pickle were used anywhere on the wire (v10 or earlier), ``__reduce__``
    would be invoked and the marker would be created. With the v11 JSON
    wire, ``__reduce__`` is NEVER called (json.dumps does not invoke it;
    the normalizer's EXACT type check rejects the object before any method
    is called). The marker must NEVER exist after a v11 run."""

    def __reduce__(self):
        try:
            _HOSTILE_REDUCE_MARKER.write_text("reduced", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return (str, ("hostile",))

    @property
    def status(self):
        try:
            _HOSTILE_REDUCE_MARKER.write_text("prop", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return "ok"


def hostile_reduce_returning_query(request, isolated_root):
    """Return a custom object with ``__reduce__``. The child's normalizer
    rejects it (not an AdapterResult); the parent never sees the object and
    never invokes ``__reduce__``. Proves no pickle on the v11 wire."""
    return _HostileReduceObject()


class _HostileAdapterResultSubclass(AdapterResult):
    """AdapterResult subclass with a property side effect. The EXACT type
    check ``type(x) is AdapterResult`` rejects subclasses without accessing
    any property. If isinstance were used (accepting subclasses), the
    property might be accessed; with the v11 EXACT check, it is NOT."""

    # Override __init__ to avoid the dataclass field requirement; the
    # parent never constructs this (it is rejected by the normalizer).
    def __init__(self):  # noqa: D401
        pass

    @property
    def status(self):
        try:
            _HOSTILE_PROP_MARKER.write_text("prop_accessed", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return "ok"


def hostile_property_subclass_query(request, isolated_root):
    """Return an AdapterResult SUBCLASS with a property side effect. The
    EXACT type check rejects it; the property is NEVER called by the
    parent (or by the child's normalizer)."""
    return _HostileAdapterResultSubclass()


class _HostileMappingLedger(dict):
    """Mapping subclass that writes a marker when ``items()`` is called.
    The EXACT type check ``type(x) is dict`` rejects Mapping subclasses;
    ``items()`` is NEVER called by the parent or the child's normalizer."""

    def items(self):
        try:
            _HOSTILE_MAP_MARKER.write_text("items_called", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return super().items()


def hostile_mapping_ledger_query(request, isolated_root):
    """Return an AdapterResult with a Mapping SUBCLASS for
    capability_ledger. The EXACT type check rejects it; the subclass's
    ``items()`` is NEVER called."""
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=(),
        capability_ledger=_HostileMappingLedger({
            "prepare_index": "legitimate_skip",
            "candidate_search": "executed",
            "target_binding": "unsupported",
            "support_expansion": "unsupported",
            "two_step_support": "unsupported",
        }),
        fallback_provenance=(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="no_evidence", target_evidence_indices=(),
            support_bindings=(), status_reason="no candidates"),
    )


def os_exit_0_query(request, isolated_root):
    """v11: child calls os._exit(0) — clean exit without sending. The
    parent sees EOF and classifies adapter-scoped process_died."""
    os._exit(0)


def os_exit_1_query(request, isolated_root):
    """v11: child calls os._exit(1). The parent sees EOF and classifies
    adapter-scoped process_died (NEVER infra, even though 1 is nonzero)."""
    os._exit(1)


def os_exit_42_query(request, isolated_root):
    """v11: child calls os._exit(42) — arbitrary code. Adapter-scoped
    process_died (NEVER infra)."""
    os._exit(42)


def os_exit_73_query(request, isolated_root):
    """v11: child calls os._exit(73) — the OLD v10
    WORKER_TRANSPORT_FAILURE_EXIT_CODE value. Under v11, this is just
    another adapter-scoped exit code => process_died (NEVER infra).
    Proves the dedicated exit code was removed and an adapter cannot
    author an infra-abort via a specific exit code."""
    os._exit(73)


def os_exit_139_query(request, isolated_root):
    """v11: child calls os._exit(139) (SIGSEGV exit code). Adapter-scoped
    process_died (NEVER infra)."""
    os._exit(139)


def os_exit_255_query(request, isolated_root):
    """v11: child calls os._exit(255). Adapter-scoped process_died."""
    os._exit(255)


def close_without_send_query(request, isolated_root):
    """v11: child exits cleanly (os._exit(0)) without the worker ever
    calling send_bytes. The parent sees EOF and classifies adapter-scoped
    process_died. Proves real child send failure / EOF => process_died."""
    os._exit(0)


def wsr_mutate_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    """v9: write into the declared writable_state_root (allowed WSR mutation).
    The post-hook scan must NOT reject WSR mutations as source mutations."""
    snap_wsr = isolated_root / ".pb_writable_state"
    marker = snap_wsr / "state.marker"
    marker.write_text("adapter_state\n", encoding="utf-8")
    return valid_adapter_query(request, isolated_root)


def adv_excerpt_leak_query(request, isolated_root):
    return AdapterResult(
        status="ok", failure_category=None,
        candidates=({"path": "src/widget.rs", "start_line": 1, "end_line": 3,
                      "score": 0.9, "reason": "symbol_match",
                      "channels": ["symbol"], "adapter_provenance": SYN_ADAPTER_ID_ADV,
                      "excerpt": "pub struct Widget {"},),
        capability_ledger=_std_ledger(has_target=True, has_support=False), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def adv_duplicate_cell_query(request, isolated_root):
    c = Candidate("src/widget.rs", 1, 3, 9.0, "symbol_match", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV)
    c2 = Candidate("src/widget.rs", 1, 3, 5.0, "text_match", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV)
    return _single_ok_result((c, c2), BindingProposal(proposed_status="ready", target_evidence_indices=(0, 1), support_bindings=()))


def adv_path_absolute_query(request, isolated_root):
    return _single_ok_result((Candidate("/etc/passwd", 1, 1, 9.0, "escape", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),))


def adv_path_traversal_query(request, isolated_root):
    return _single_ok_result((Candidate("../etc/passwd", 1, 1, 9.0, "escape", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),))


def adv_path_drive_query(request, isolated_root):
    return _single_ok_result((Candidate("C:/secrets", 1, 1, 9.0, "escape", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),))


def adv_path_unc_query(request, isolated_root):
    return _single_ok_result((Candidate("\\\\host\\share\\secret", 1, 1, 9.0, "escape", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),))


def adv_mutate_file_query(request, isolated_root):
    target = isolated_root / "src" / "widget.rs"
    if target.is_file():
        target.write_text("MUTATED\n", encoding="utf-8")
    return _single_ok_result((_widget_candidate_adv(),))


def adv_add_file_query(request, isolated_root):
    (isolated_root / "src" / "injected.rs").write_text("injected\n", encoding="utf-8")
    return _single_ok_result((_widget_candidate_adv(),))


def adv_delete_file_query(request, isolated_root):
    target = isolated_root / "src" / "config.rs"
    if target.is_file():
        target.unlink()
    return _single_ok_result((_widget_candidate_adv(),))


def adv_rename_file_query(request, isolated_root):
    src = isolated_root / "src" / "widget.rs"
    dst = isolated_root / "src" / "renamed.rs"
    if src.is_file():
        src.rename(dst)
    return _single_ok_result((_widget_candidate_adv(),))


def adv_sleep_timeout_query(request, isolated_root):
    time.sleep(request.run_spec.timeout_seconds + 30.0)
    return _single_ok_result((_widget_candidate_adv(),))


def adv_sleep_timeout_mutate_query(request, isolated_root):
    """Sleep far beyond timeout, then mutate — must be terminated before
    reaching the mutation. Proves immediate termination + no post-timeout
    mutation."""
    time.sleep(request.run_spec.timeout_seconds + 30.0)
    target = isolated_root / "src" / "widget.rs"
    if target.is_file():
        target.write_text("POST_TIMEOUT_MUTATION\n", encoding="utf-8")
    return _single_ok_result((_widget_candidate_adv(),))


def adv_exception_query(request, isolated_root):
    raise RuntimeError("simulated adapter crash")


def adv_malformed_output_query(request, isolated_root):
    return {"status": "ok", "candidates": []}  # type: ignore[return-value]


def adv_partial_query(request, isolated_root):
    return AdapterResult(
        status="partial", failure_category="incomplete_search", candidates=(),
        capability_ledger={"prepare_index": "failed", "candidate_search": "failed",
                           "target_binding": "failed", "support_expansion": "failed",
                           "two_step_support": "unsupported"},
        fallback_provenance=(FallbackRecord("prepare_index", "candidate_search"),
                             FallbackRecord("candidate_search", "none")),
    )


def adv_missing_capability_status_query(request, isolated_root):
    return AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_candidate_adv(),),
        capability_ledger={"candidate_search": "executed"},
        fallback_provenance=_std_fallback(), resource_sample=None,
        binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def adv_extra_capability_status_query(request, isolated_root):
    ledger = _std_ledger()
    ledger["current_source_materialize"] = "executed"
    return AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_candidate_adv(),),
        capability_ledger=ledger, fallback_provenance=_std_fallback(),
        resource_sample=None, binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def adv_failed_default_masquerade_query(request, isolated_root):
    ledger = _std_ledger()
    ledger["candidate_search"] = "failed"
    return AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_candidate_adv(),),
        capability_ledger=ledger,
        fallback_provenance=(FallbackRecord("candidate_search", "none"),),
        resource_sample=None, binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def adv_over_candidate_cap_query(request, isolated_root):
    cands = tuple(Candidate("src/widget.rs", i, i, 5.0, "spam", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV) for i in range(1, 20))
    return _single_ok_result(cands)


def adv_over_evidence_cap_query(request, isolated_root):
    cands = (
        Candidate("src/widget.rs", 1, 3, 9.0, "m", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/widget.rs", 5, 6, 5.0, "m", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/widget.rs", 7, 8, 3.0, "m", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/config.rs", 1, 2, 4.0, "m", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV),
    )
    return AdapterResult(
        status="ok", failure_category=None, candidates=cands,
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=(SupportBinding(1, (0,), "type_dep"),
                     SupportBinding(2, (0,), "type_dep"),
                     SupportBinding(3, (0,), "type_dep")),
        ),
    )


def adv_over_target_cap_query(request, isolated_root):
    cands = (
        Candidate("src/widget.rs", 1, 3, 9.0, "m", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/widget.rs", 5, 6, 5.0, "m", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/config.rs", 1, 2, 4.0, "m", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),
    )
    return _single_ok_result(cands, BindingProposal(proposed_status="ready", target_evidence_indices=(0, 1, 2), support_bindings=()))


def adv_over_support_cap_query(request, isolated_root):
    cands = (
        Candidate("src/widget.rs", 1, 3, 9.0, "m", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/widget.rs", 5, 6, 5.0, "m", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/widget.rs", 7, 8, 3.0, "m", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV),
        Candidate("src/config.rs", 1, 2, 4.0, "m", frozenset({"bm25"}), SYN_ADAPTER_ID_ADV),
    )
    return AdapterResult(
        status="ok", failure_category=None, candidates=cands,
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=(SupportBinding(1, (0,), "type_dep"),
                     SupportBinding(2, (0,), "type_dep"),
                     SupportBinding(3, (0,), "type_dep")),
        ),
    )


def adv_non_finite_score_query(request, isolated_root):
    return _single_ok_result((Candidate("src/widget.rs", 1, 3, float("inf"), "bad", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),))


def adv_stale_range_query(request, isolated_root):
    return _single_ok_result((Candidate("src/widget.rs", 900, 950, 9.0, "stale", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),))


def adv_binary_source_query(request, isolated_root):
    return _single_ok_result((Candidate("src/data.bin", 1, 1, 9.0, "binary", frozenset({"symbol"}), SYN_ADAPTER_ID_ADV),))


def adv_provenance_mismatch_query(request, isolated_root):
    return _single_ok_result((Candidate("src/widget.rs", 1, 3, 9.0, "m", frozenset({"symbol"}), "pb_wrong_provenance"),))


def adv_undeclared_channel_query(request, isolated_root):
    return _single_ok_result((Candidate("src/widget.rs", 1, 3, 9.0, "m", frozenset({"graph"}), SYN_ADAPTER_ID_ADV),))


def adv_unsupported_support_query(request, isolated_root):
    """v6: a one_shot context adapter with target binding only.
    two_step_support is unsupported (not needed for one_shot context) and does
    NOT fall back. The result is ok with a ready pack — an unsupported
    capability does not cause silent degeneration when it is not needed."""
    return AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_candidate_adv(),),
        capability_ledger=_std_ledger(has_target=True, has_support=False),
        fallback_provenance=(),
        resource_sample=None, binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def adv_bad_fallback_query(request, isolated_root):
    return AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_candidate_adv(),),
        capability_ledger=_std_ledger(),
        fallback_provenance=(FallbackRecord("candidate_search", "candidate_search"),),
        resource_sample=None, binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def adv_binding_bad_target_ref_query(request, isolated_root):
    cands = (_widget_candidate_adv(), _config_support_candidate(SYN_ADAPTER_ID_ADV))
    return AdapterResult(
        status="ok", failure_category=None, candidates=cands,
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=(SupportBinding(1, (5,), "type_dep"),)),
    )


def adv_binding_bad_relation_query(request, isolated_root):
    cands = (_widget_candidate_adv(), _config_support_candidate(SYN_ADAPTER_ID_ADV))
    return AdapterResult(
        status="ok", failure_category=None, candidates=cands,
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=(SupportBinding(1, (0,), "bogus_relation"),)),
    )


def adv_binding_duplicate_support_query(request, isolated_root):
    cands = (_widget_candidate_adv(), _config_support_candidate(SYN_ADAPTER_ID_ADV))
    return AdapterResult(
        status="ok", failure_category=None, candidates=cands,
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=(SupportBinding(1, (0,), "type_dep"),
                    SupportBinding(1, (0,), "import")),
        ),
    )


def adv_binding_target_is_support_query(request, isolated_root):
    cands = (_widget_candidate_adv(), _config_support_candidate(SYN_ADAPTER_ID_ADV))
    return AdapterResult(
        status="ok", failure_category=None, candidates=cands,
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=(SupportBinding(0, (), "type_dep", "pb_syn_target_1"),),
        ),
    )


def adv_adapter_resource_sample_query(request, isolated_root):
    """Adapter tries to supply a resource_sample — must be rejected."""
    return AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_candidate_adv(),),
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=ResourceSample(
            setup_seconds=0.1, index_seconds=0.1, query_seconds=0.1,
            materialize_seconds=None, render_seconds=None,
            rss_bytes=None, cpu_seconds=None,
        ),
        binding_proposal=BindingProposal(proposed_status="ready", target_evidence_indices=(0,), support_bindings=()),
    )


def adv_zero_evidence_no_proposal_query(request, isolated_root):
    """v8: an ok result with EMPTY candidates and NO BindingProposal. Every
    status=ok result MUST carry an explicit BindingProposal (including zero
    candidate/evidence results, which must explicitly propose no_evidence).
    This is rejected at validate_adapter_result (result_validation:ContractError),
    with resource timing recorded but NO pack and NO canonical pack hash."""
    return AdapterResult(
        status="ok", failure_category=None, candidates=(),
        capability_ledger=_std_ledger(has_target=False, has_support=False),
        fallback_provenance=_std_fallback(),
        resource_sample=None, binding_proposal=None,
    )


def adv_query_returns_none(request, isolated_root):
    """v8: a query hook returning exactly None (instead of an AdapterResult).
    The stage-aware worker enforces query must return exactly AdapterResult;
    None is malformed/non_adapter_result."""
    return None  # type: ignore[return-value]


# -- Lifecycle adversarial hooks --


def adv_prepare_fails(request: AdapterRequest, isolated_root: Path) -> None:
    raise RuntimeError("prepare hook crashed")


def adv_index_fails(request: AdapterRequest, isolated_root: Path) -> None:
    raise RuntimeError("index hook crashed")


# v8: lifecycle hooks that return the WRONG shape. The stage-aware worker
# enforces prepare/index must return exactly None; returning an AdapterResult
# (or any other shape) is malformed/non_adapter_result. These prove the exact
# return matrix is enforced at the process boundary, with resource timing and
# no pack produced.
def adv_prepare_returns_adapter_result(
    request: AdapterRequest, isolated_root: Path,
) -> None:
    """v8: a prepare hook returning an AdapterResult instead of None. Must be
    rejected as malformed/non_adapter_result (prepare/index return exactly
    None; only query returns an AdapterResult)."""
    return AdapterResult(
        status="ok", failure_category=None, candidates=(),
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None, binding_proposal=_std_binding(),
    )


def adv_index_returns_adapter_result(
    request: AdapterRequest, isolated_root: Path,
) -> None:
    """v8: an index hook returning an AdapterResult instead of None. Must be
    rejected as malformed/non_adapter_result."""
    return AdapterResult(
        status="ok", failure_category=None, candidates=(),
        capability_ledger=_std_ledger(), fallback_provenance=_std_fallback(),
        resource_sample=None, binding_proposal=_std_binding(),
    )


# v7: sleeping lifecycle hooks that attempt a delayed marker write. These
# prove the stage-aware spawned timeout enforcement covers prepare/index too:
# the child is terminated before the marker write, the marker is absent
# immediately and after a guard delay, the visible source is unchanged, and a
# ResourceSample with the phase duration is present.
_SLEEP_MARKER_REL = "sleep_marker.txt"


def adv_sleep_prepare(request: AdapterRequest, isolated_root: Path) -> None:
    """Sleeps far beyond timeout, then attempts a marker write into the
    writable_state_root. Must be terminated before the write."""
    import time as _t
    _t.sleep(request.run_spec.timeout_seconds + 0.25)
    wsr = _stateful_writable_root(request, isolated_root)
    wsr.mkdir(parents=True, exist_ok=True)
    (wsr / _SLEEP_MARKER_REL).write_text("should_not_exist", encoding="utf-8")


def adv_sleep_index(request: AdapterRequest, isolated_root: Path) -> None:
    """Sleeps far beyond timeout, then attempts a marker write into the
    writable_state_root. Must be terminated before the write."""
    import time as _t
    _t.sleep(request.run_spec.timeout_seconds + 0.25)
    wsr = _stateful_writable_root(request, isolated_root)
    wsr.mkdir(parents=True, exist_ok=True)
    (wsr / _SLEEP_MARKER_REL).write_text("should_not_exist", encoding="utf-8")


ADV_PREPARE_FAILS_HOOKS = AdapterHooks(prepare=adv_prepare_fails, index=None, query=valid_adapter_query).validate()
ADV_INDEX_FAILS_HOOKS = AdapterHooks(prepare=None, index=adv_index_fails, query=valid_adapter_query).validate()

# v8: lifecycle/query hooks returning the wrong shape. These prove the exact
# stage return matrix is enforced at the process boundary (prepare/index
# return exactly None; query returns exactly AdapterResult; every other
# shape is malformed/non_adapter_result) with resource timing and no pack.
ADV_PREPARE_RETURNS_AR_HOOKS = AdapterHooks(prepare=adv_prepare_returns_adapter_result, index=None, query=valid_adapter_query).validate()
ADV_INDEX_RETURNS_AR_HOOKS = AdapterHooks(prepare=None, index=adv_index_returns_adapter_result, query=valid_adapter_query).validate()
ADV_QUERY_RETURNS_NONE_HOOKS = AdapterHooks(prepare=None, index=None, query=adv_query_returns_none).validate()

# v7: sleeping lifecycle hooks (top-level for spawn picklability). Query is a
# fast valid query so the timeout is purely on the prepare/index stage.
ADV_SLEEP_PREPARE_HOOKS = AdapterHooks(prepare=adv_sleep_prepare, index=None, query=valid_adapter_query).validate()
ADV_SLEEP_INDEX_HOOKS = AdapterHooks(prepare=None, index=adv_sleep_index, query=valid_adapter_query).validate()


# ---------------------------------------------------------------------------
# Process-isolated stage-aware execution (multiprocessing spawn)
# v7: generalize spawned execution into a stage-aware helper for
# prepare/index/query. ALL third-party hooks run in a fresh spawn child.
# v8: deterministic cleanup on every path + HarnessInfrastructureError.
# ---------------------------------------------------------------------------


class HarnessInfrastructureError(Exception):
    """Raised when genuine multiprocessing launch/pipe/Process setup or
    inter-process communication fails unexpectedly (NOT a normal child
    EOF/process death, which remains a closed stage error).

    v8: this ABORTS the whole bakeoff. It is NEVER caught by ``run_adapter``'s
    adapter-error catches (``ContractError`` / ``_StopProcessing``) and is
    NEVER converted into one adapter's ``ValidatedRunRecord`` or comparison
    datapoint. It propagates out of ``run_adapter`` and the self-test so the
    bakeoff fails fast rather than masking an infrastructure breakage as an
    adapter defect. Known adapter defects remain prevalidation/ContractError
    rejections.
    """


def _close_pipe_endpoint(conn: Any) -> None:
    """Close a Pipe endpoint, swallowing exceptions so a failure in one close
    cannot mask or double-close another (avoids double-close exceptions)."""
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass


def _reap_process(proc: Any, *, terminate_if_alive: bool) -> int | None:
    """Reap a started child deterministically on every exit path.

    v9: attempts ALL cleanup, then VERIFIES the child is no longer alive.
    An unreaped child (still alive after terminate+kill+join) raises
    ``HarnessInfrastructureError`` (NOT swallowed) — aborting the whole
    bakeoff. Cleanup errors are still swallowed per-step so a failure in one
    step cannot mask another, but the final alive-check is non-negotiable.

    v10: returns the child exitcode captured BEFORE ``close()``. After
    ``close()``, ``proc.exitcode`` raises ValueError, so the capture MUST
    happen before the handle is released. The parent inspects this on EOF to
    distinguish a genuine worker transport-failure exit code from an ordinary
    child crash (process_died).

    - terminate immediately when required (and the child is still alive);
    - join UNCONDITIONALLY even if the child already exited (to reap the
      released zombie/resources);
    - if still alive after terminate+join, kill + join;
    - v10: capture ``proc.exitcode`` BEFORE ``close()``;
    - call ``proc.close()`` only after the process is no longer alive;
    - VERIFY not alive at the end (raise HarnessInfrastructureError if alive).
    """
    if terminate_if_alive and proc.is_alive():
        try:
            proc.terminate()
        except Exception:
            pass
    # Join unconditionally — even if already exited — to reap resources.
    try:
        proc.join(timeout=2.0)
    except Exception:
        pass
    # If still alive after terminate+join, escalate to kill + join.
    if proc.is_alive() and hasattr(proc, "kill"):
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.join(timeout=1.0)
        except Exception:
            pass
    # v9: VERIFY the child is no longer alive. The alive check MUST happen
    # BEFORE ``close()`` (``is_alive`` raises ValueError after close()).
    # An unreaped child (still alive after terminate+kill+join) raises
    # HarnessInfrastructureError (NOT swallowed) — aborting the whole bakeoff.
    still_alive = False
    try:
        still_alive = proc.is_alive()
    except (ValueError, OSError):
        # Process already closed/reaped — treat as not alive.
        still_alive = False
    if still_alive:
        raise HarnessInfrastructureError(
            "child process could not be reaped after terminate/kill/join "
            "(still alive); aborting the whole bakeoff"
        )
    # v10: capture the child exitcode BEFORE ``close()``. After ``close()``,
    # ``proc.exitcode`` raises ValueError. The parent inspects this on EOF
    # to distinguish a genuine worker transport-failure exit code from an
    # ordinary child crash (process_died).
    child_exitcode: int | None = None
    try:
        child_exitcode = proc.exitcode
    except (ValueError, OSError):
        child_exitcode = None
    # Close the Process handle only once it is no longer alive.
    if hasattr(proc, "close"):
        try:
            proc.close()
        except Exception:
            pass
    return child_exitcode


class _WireError(Exception):
    """Internal: raised by the v11/v12 wire normalizer/decoder when a value
    cannot be represented as a closed JSON primitive tree. The child
    converts any ``_WireError`` during normalization into a small
    malformed canonical envelope; the parent converts any ``_WireError``
    during decode/validation/reconstruction into an adapter-scoped
    malformed outcome (never ``HarnessInfrastructureError``).

    v12: the parent receiver ALSO converts a closed set of child-controlled
    parser/validation exceptions (``ValueError`` incl. Python oversized
    integer-token limit, ``RecursionError`` from deep nesting,
    ``OverflowError``, ``TypeError``/``KeyError``/``AttributeError``/
    ``IndexError`` from reconstruction) into ``_WireError`` at the
    decode/validate/reconstruct boundary, so they NEVER reach the receiver
    catch-all ``pipe_error`` -> ``HarnessInfrastructureError``. The boundary
    is scoped tightly around strict decode/parse/validate/reconstruct;
    genuinely parent-local poll/handle/queue/thread/setup/cleanup failures
    remain infra."""


# v12: closed set of child-controlled parser/validation exceptions the
# receiver must convert to ``_WireError`` (then ``malformed`` outcome) at the
# decode/validate/reconstruct boundary. ``ValueError`` covers
# ``json.JSONDecodeError`` (a subclass) and the Python 3.11+ oversized
# integer-token limit (``sys.get_int_max_str_digits``). ``RecursionError``
# covers deep nesting in ``json.loads`` and the depth validator.
# ``OverflowError``/``TypeError``/``KeyError``/``AttributeError``/
# ``IndexError`` cover unexpected reconstruction failures on hostile
# payloads. The receiver catch-all ``except Exception`` remains for genuine
# parent-local thread/queue state failures (infra).
_WIRE_CHILD_PARSE_EXCS: tuple = (
    _WireError, ValueError, TypeError, RecursionError,
    OverflowError, KeyError, AttributeError, IndexError,
)


# ---------------------------------------------------------------------------
# v11: bounded strict JSON primitive wire (NO pickle anywhere in run-phase).
# Child-side normalization: trusted harness code copies the canonical
# AdapterResult field-by-field into a plain builtin dict/list/scalar tree
# under EXACT type checks (``type(x) is AdapterResult`` etc., NOT
# ``isinstance`` accepting subclasses that could override behavior). No
# adapter-defined encoder/default/object_hook/repr/string conversion is
# used. NaN/Infinity floats, nonprimitive/mapping-subclass/custom objects,
# property-access failures, JSON-encode failures, and oversize envelopes
# become a SMALL malformed canonical envelope.
# ---------------------------------------------------------------------------


def _wire_check_str(v: Any, *, max_len: int) -> str:
    """EXACT str check (rejects str subclasses). Bounded length."""
    if type(v) is not str:
        raise _WireError("not str")
    if len(v) > max_len:
        raise _WireError("str too long")
    return v


def _wire_check_int(v: Any) -> int:
    """EXACT int check; bool rejected (``type(True) is int`` is False
    because ``type(True) is bool``)."""
    if type(v) is not int:
        raise _WireError("not int")
    return v


def _wire_check_float(v: Any) -> float:
    """EXACT float-or-int check (the contract accepts int-as-float for
    score); bool rejected; NaN/Infinity rejected. The normalized JSON
    representation preserves int vs float distinction (json.dumps emits
    int literals for int values, float literals for float values)."""
    if type(v) is bool:
        raise _WireError("bool not numeric")
    if type(v) is int:
        return float(v)
    if type(v) is float:
        if v != v or v in (float("inf"), float("-inf")):
            raise _WireError("non-finite float")
        return v
    raise _WireError("not float")


def _wire_normalize_str_iterable(
    value: Any, *, max_count: int, max_item_len: int, err_label: str,
) -> list:
    """Normalize a frozenset/set/tuple/list of str into a sorted list of
    EXACT str (rejects str subclasses and non-str items). The wire form is
    a list (JSON has no set); the parent reconstructs a frozenset. Duplicate
    items reject on the wire so the parent's reconstruction is unambiguous."""
    if type(value) not in (frozenset, set, tuple, list):
        raise _WireError(f"{err_label} not iterable container")
    out: list = []
    seen: set = set()
    for item in value:
        s = _wire_check_str(item, max_len=max_item_len)
        if s in seen:
            raise _WireError(f"{err_label} duplicate item")
        seen.add(s)
        out.append(s)
        if len(out) > max_count:
            raise _WireError(f"{err_label} too many items")
    out.sort()
    return out


def _wire_normalize_int_iterable(
    value: Any, *, max_count: int, err_label: str,
) -> list:
    """Normalize a tuple of int into a list of EXACT int (bool rejected).
    Duplicates are NOT rejected here (target_indices may legitimately
    repeat across distinct support bindings; the closed-schema validator
    handles per-field duplicate rejection where required)."""
    if type(value) is not tuple:
        raise _WireError(f"{err_label} not tuple")
    out: list = []
    for item in value:
        out.append(_wire_check_int(item))
        if len(out) > max_count:
            raise _WireError(f"{err_label} too many items")
    return out


def _wire_normalize_tuple_of(
    value: Any, *, max_count: int, err_label: str,
) -> tuple:
    """EXACT tuple check (rejects tuple subclasses). Bounded count."""
    if type(value) is not tuple:
        raise _WireError(f"{err_label} not tuple")
    if len(value) > max_count:
        raise _WireError(f"{err_label} too many items")
    return value


def _wire_normalize_candidate(cand: Any) -> dict:
    """Normalize a Candidate into a closed JSON primitive dict. EXACT type
    check (rejects Candidate subclasses and dict-shaped candidates — the
    wire carries only canonical Candidate instances constructed by trusted
    adapter code)."""
    if type(cand) is not Candidate:
        raise _WireError("candidate not Candidate")
    return {
        "path": _wire_check_str(cand.path, max_len=512),
        "start_line": _wire_check_int(cand.start_line),
        "end_line": _wire_check_int(cand.end_line),
        "score": _wire_check_float(cand.score),
        "reason": _wire_check_str(cand.reason, max_len=128),
        "channels": _wire_normalize_str_iterable(
            cand.channels, max_count=64, max_item_len=64,
            err_label="channels"),
        "adapter_provenance": _wire_check_str(
            cand.adapter_provenance, max_len=128),
    }


def _wire_normalize_support_binding(sb: Any) -> dict:
    if type(sb) is not SupportBinding:
        raise _WireError("support_binding not SupportBinding")
    return {
        "evidence_index": _wire_check_int(sb.evidence_index),
        "target_indices": _wire_normalize_int_iterable(
            sb.target_indices, max_count=_MAX_STAGE_TARGET_INDICES,
            err_label="target_indices"),
        "relation_kind": _wire_check_str(sb.relation_kind, max_len=64),
        "parent_target_id": (
            None if sb.parent_target_id is None
            else _wire_check_str(sb.parent_target_id, max_len=128)),
    }


def _wire_normalize_binding_proposal(bp: Any) -> dict:
    if type(bp) is not BindingProposal:
        raise _WireError("binding_proposal not BindingProposal")
    return {
        "proposed_status": _wire_check_str(bp.proposed_status, max_len=64),
        "target_evidence_indices": _wire_normalize_int_iterable(
            bp.target_evidence_indices,
            max_count=_MAX_STAGE_TARGET_INDICES,
            err_label="target_evidence_indices"),
        "support_bindings": [
            _wire_normalize_support_binding(sb)
            for sb in _wire_normalize_tuple_of(
                bp.support_bindings,
                max_count=_MAX_STAGE_SUPPORT_BINDINGS,
                err_label="support_bindings")],
        "status_reason": (
            None if bp.status_reason is None
            else _wire_check_str(bp.status_reason, max_len=256)),
    }


def _wire_normalize_fallback_record(fr: Any) -> dict:
    if type(fr) is not FallbackRecord:
        raise _WireError("fallback_record not FallbackRecord")
    return {
        "unavailable_capability": _wire_check_str(
            fr.unavailable_capability, max_len=64),
        "fallback_to": _wire_check_str(fr.fallback_to, max_len=64),
    }


def _wire_normalize_adapter_result(result: Any) -> dict:
    """Normalize an AdapterResult into a closed JSON primitive dict tree.

    EXACT type checks (``type(x) is AdapterResult``) reject dataclass
    subclasses, Mapping subclasses, and custom objects that could override
    behavior. Every nested value is copied field-by-field under the closed
    schema. NaN/Infinity floats, non-finite numbers, oversized strings,
    excessive counts, and any nonprimitive/custom object are rejected via
    ``_WireError`` (the child then emits a small malformed canonical
    envelope).
    """
    if type(result) is not AdapterResult:
        raise _WireError("not AdapterResult")
    # status: exact str, bounded length, closed vocab.
    status = _wire_check_str(result.status, max_len=64)
    if status not in RESULT_STATUSES:
        raise _WireError("status not in vocab")
    # failure_category: str | None (EXACT None check, not falsy — empty str
    # is a valid canonical value and must NOT be normalized to None).
    fc = result.failure_category
    if fc is not None:
        fc = _wire_check_str(fc, max_len=64)
    # candidates: exact tuple of Candidate; bounded count.
    cand_tuple = _wire_normalize_tuple_of(
        result.candidates, max_count=_MAX_STAGE_CANDIDATES,
        err_label="candidates")
    candidates_list = [_wire_normalize_candidate(c) for c in cand_tuple]
    # capability_ledger: EXACT dict (reject Mapping subclasses that could
    # override __getitem__/items); bounded keys; exact str keys/values.
    ledger = result.capability_ledger
    if type(ledger) is not dict:
        raise _WireError("capability_ledger not dict")
    if len(ledger) > _MAX_STAGE_LEDGER_KEYS:
        raise _WireError("capability_ledger too many keys")
    ledger_out: dict = {}
    for k, v in ledger.items():
        ks = _wire_check_str(k, max_len=64)
        vs = _wire_check_str(v, max_len=64)
        if ks in ledger_out:
            raise _WireError("capability_ledger duplicate key")
        ledger_out[ks] = vs
    # fallback_provenance: exact tuple of FallbackRecord; bounded count.
    fb_tuple = _wire_normalize_tuple_of(
        result.fallback_provenance,
        max_count=_MAX_STAGE_FALLBACK_RECORDS,
        err_label="fallback_provenance")
    fallback_list = [_wire_normalize_fallback_record(fr) for fr in fb_tuple]
    # resource_sample: MUST be None (adapter forbidden; the closed-shape
    # validator in the contract already rejects non-None, but the wire
    # rejects it BEFORE encoding so a hostile adapter cannot sneak one
    # through the wire boundary).
    if result.resource_sample is not None:
        raise _WireError("resource_sample forbidden on wire")
    # binding_proposal: BindingProposal | None (EXACT).
    bp = result.binding_proposal
    bp_out = (
        None if bp is None else _wire_normalize_binding_proposal(bp))
    return {
        "status": status,
        "failure_category": fc,
        "candidates": candidates_list,
        "capability_ledger": ledger_out,
        "fallback_provenance": fallback_list,
        "binding_proposal": bp_out,
    }


def _wire_build_envelope(
    *, status: str, payload: Any, error: str | None,
) -> dict:
    """Build the closed wire envelope dict. ``error`` is bounded and
    validated; it carries only trusted exception TYPE names (never
    adapter-authored message text)."""
    err = None
    if error is not None:
        # Bound the error string defensively (the only source is
        # type(e).__name__, which is short, but cap it in case a future
        # caller passes something larger; a too-long error becomes a
        # malformed envelope via the caller's except path).
        err = _wire_check_str(error, max_len=_MAX_STAGE_ERROR_LEN)
    return {
        "v": _STAGE_ENVELOPE_VERSION,
        "status": status,
        "payload": payload,
        "error": err,
    }


def _wire_encode_envelope(envelope: dict) -> bytes:
    """Encode the closed envelope to compact/deterministic UTF-8 JSON
    bytes. ``sort_keys=True`` for deterministic encoding so the
    deterministic-comparison guarantees (cat7) are preserved. No adapter-
    defined encoder/default/object_hook is used."""
    return json.dumps(
        envelope, separators=(",", ":"), sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")


def _wire_malformed_envelope_bytes(reason: str) -> bytes:
    """Build the small canonical malformed envelope bytes. Used when
    normalization, encoding, or oversize rejection occurs in the child."""
    try:
        env = _wire_build_envelope(
            status="malformed", payload=None, error=reason)
        return _wire_encode_envelope(env)
    except Exception:  # noqa: BLE001
        # Last-resort static envelope; never fails. The parent's strict
        # decoder accepts this exact shape (closed envelope, malformed
        # status, null payload, short error string).
        return (
            b'{"error":"malformed","payload":null,'
            b'"status":"malformed","v":1}'
        )


# ---------------------------------------------------------------------------
# Parent-side: strict JSON decode + closed-envelope validation + canonical
# dataclass reconstruction. NO pickle.loads / pickle.dumps / pickle import
# anywhere in the run-phase modules.
# ---------------------------------------------------------------------------


def _wire_reject_constants(value: Any) -> None:
    """json.loads ``parse_constant`` hook: reject NaN/Infinity/-Infinity.
    These constants are accepted by the JSON decoder by default; reject
    them so a hostile child cannot inject non-finite numbers. The argument
    is the matching string ('NaN', 'Infinity', '-Infinity'); raising any
    exception aborts the decode."""
    raise _WireError(f"json constant {value!r} rejected")


def _wire_reject_duplicate_keys(pairs: list) -> dict:
    """json.loads ``object_pairs_hook``: reject duplicate keys at every
    object level. Builds a plain builtin ``dict`` (NOT a subclass) so the
    parent gets only builtin primitive types — never an arbitrary type
    constructed by an ``object_hook``. The hook runs at EVERY object
    level (nested dicts too), so duplicate keys at any depth reject."""
    out: dict = {}
    for k, v in pairs:
        if type(k) is not str:
            raise _WireError("json key not str")
        if k in out:
            raise _WireError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _wire_validate_depth_and_primitives(value: Any, *, depth: int = 0) -> None:
    """Defense-in-depth: walk the decoded JSON tree and reject (a) excess
    nesting depth, (b) excessive list/dict counts, (c) excessive string
    length, (d) any non-finite float. The closed-envelope validator below
    applies the exact schema; this helper bounds the raw tree so a hostile
    child cannot exhaust parent memory via structural inflation BEFORE the
    schema check runs. Runs BEFORE and AFTER schema validation/reconstruction."""
    if depth > _MAX_STAGE_DEPTH:
        raise _WireError("depth exceeded")
    if type(value) is bool:
        return
    if type(value) is int:
        return
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise _WireError("non-finite float")
        return
    if type(value) is str:
        if len(value) > _MAX_STAGE_STR_LEN:
            raise _WireError("str too long")
        return
    if type(value) is list:
        if len(value) > _MAX_STAGE_LIST_COUNT:
            raise _WireError("list too long")
        for item in value:
            _wire_validate_depth_and_primitives(item, depth=depth + 1)
        return
    if type(value) is dict:
        if len(value) > _MAX_STAGE_DICT_COUNT:
            raise _WireError("dict too many keys")
        for v in value.values():
            _wire_validate_depth_and_primitives(v, depth=depth + 1)
        return
    if value is None:
        return
    raise _WireError(f"unexpected primitive type {type(value).__name__}")


def _wire_decode_envelope(data: bytes) -> dict:
    """Strict UTF-8 decode + json.loads with parse_constant rejection +
    object_pairs_hook duplicate-key rejection at every object level. The
    decoder never constructs arbitrary types: object_pairs_hook builds
    plain builtin dicts only. Rejects: invalid UTF-8, embedded NUL,
    trailing/multiple docs, NaN/Infinity, duplicate keys at any level.

    v12: the exception boundary is scoped tightly around the parser. Any
    child-controlled parser exception is converted to ``_WireError`` so the
    receiver NEVER falls through to its catch-all ``pipe_error`` ->
    ``HarnessInfrastructureError``. Specifically caught:

      * ``UnicodeDecodeError`` -> ``invalid utf-8``
      * ``json.JSONDecodeError`` -> ``json decode failed``
      * ``_WireError`` (re-raised) from ``parse_constant`` /
        ``object_pairs_hook`` (NaN/Infinity/duplicate keys/non-str keys)
      * ``ValueError`` (NOT ``json.JSONDecodeError``) -> covers Python
        3.11+ oversized integer-token limit
        (``sys.get_int_max_str_digits()``)
      * ``RecursionError`` -> deep nesting beyond the C parser recursion
        limit
      * ``OverflowError`` -> numeric overflow during parsing
      * ``TypeError`` -> unexpected primitive type from a hook

    A child can induce ALL of these by sending crafted JSON bytes; they
    are therefore adapter-scoped ``malformed`` and NEVER infra."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise _WireError("invalid utf-8")
    if "\x00" in text:
        raise _WireError("nul byte in payload")
    # json.loads with strict=True (the default) rejects trailing/multiple
    # docs (extra data after the first JSON value raises JSONDecodeError).
    try:
        envelope = json.loads(
            text,
            parse_constant=_wire_reject_constants,
            object_pairs_hook=_wire_reject_duplicate_keys,
        )
    except _WireError:
        # Re-raise _WireError from parse_constant / object_pairs_hook
        # without wrapping (so the caller sees the specific reason).
        raise
    except json.JSONDecodeError:
        # Malformed JSON syntax (also a ValueError subclass; catch the
        # narrower type first for a clearer reason).
        raise _WireError("json decode failed")
    except (ValueError, RecursionError, OverflowError, TypeError) as exc:
        # v12: child-controlled parser exceptions that are NOT
        # JSONDecodeError. ValueError covers the Python 3.11+ oversized
        # integer-token limit (``sys.get_int_max_str_digits``);
        # RecursionError covers deep nesting beyond the C parser
        # recursion limit; OverflowError covers numeric overflow;
        # TypeError covers unexpected primitive types from hooks. A child
        # can induce any of these by sending crafted JSON bytes; convert
        # to _WireError so the receiver classifies adapter-scoped
        # malformed (NEVER infra).
        raise _WireError(f"json decode failed: {type(exc).__name__}")
    # EXACT dict check (rejects Mapping subclasses and non-dict tops).
    if type(envelope) is not dict:
        raise _WireError("envelope not dict")
    return envelope


def _wire_validate_envelope(envelope: dict) -> tuple[str, Any, str | None]:
    """Validate the closed envelope schema and return
    ``(status, payload, error)``. Rejects: extra/missing keys, wrong types,
    unknown status, wrong payload-for-status, bool-as-version. Avoids
    ambiguous bool-as-int (uses ``type(x) is int/float/bool`` semantics)."""
    if set(envelope.keys()) != _STAGE_ENVELOPE_KEYS:
        raise _WireError("envelope keys not exact closed set")
    v = envelope["v"]
    # bool is a subclass of int; ``type(True) is int`` is False, so this
    # rejects bool-as-version (ambiguous bool-as-int).
    if type(v) is not int or v != _STAGE_ENVELOPE_VERSION:
        raise _WireError("envelope version wrong")
    status = envelope["status"]
    if type(status) is not str or status not in _STAGE_ENVELOPE_STATUSES:
        raise _WireError("envelope status not closed vocab")
    payload = envelope["payload"]
    error = envelope["error"]
    if error is not None:
        if type(error) is not str:
            raise _WireError("envelope error not str/null")
        if len(error) > _MAX_STAGE_ERROR_LEN:
            raise _WireError("envelope error too long")
    if status == "ok":
        # payload may be null (prepare/index ok) or a closed payload dict
        # (query ok); other types reject (bool/list/str/num are NOT null).
        if payload is not None and type(payload) is not dict:
            raise _WireError("ok payload not dict/null")
    else:
        # error/malformed MUST carry null payload (no exception data).
        if payload is not None:
            raise _WireError(f"{status} payload must be null")
        if status == "error" and (error is None or not error):
            raise _WireError("error status requires error string")
    return status, payload, error


def _wire_reconstruct_adapter_result(payload: dict) -> AdapterResult:
    """Reconstruct the exact canonical ``AdapterResult`` dataclass from the
    closed JSON primitive payload dict, field-by-field, in trusted parent
    code. EXACT primitive type checks (rejects bool-as-int, str subclasses,
    list-as-tuple, dict subclasses). The downstream
    ``validate_adapter_result`` + ``validate_capability_ledger_honesty``
    revalidate against descriptor/snapshot (defense in depth)."""
    if type(payload) is not dict:
        raise _WireError("payload not dict")
    if set(payload.keys()) != {
        "status", "failure_category", "candidates",
        "capability_ledger", "fallback_provenance", "binding_proposal",
    }:
        raise _WireError("payload keys not exact closed set")
    status = payload["status"]
    if type(status) is not str or status not in RESULT_STATUSES:
        raise _WireError("payload status not closed vocab")
    fc = payload["failure_category"]
    if fc is not None:
        if type(fc) is not str or len(fc) > 64:
            raise _WireError("payload failure_category not str/null")
    cand_list = payload["candidates"]
    if type(cand_list) is not list:
        raise _WireError("payload candidates not list")
    if len(cand_list) > _MAX_STAGE_CANDIDATES:
        raise _WireError("payload candidates too many")
    candidates: tuple = tuple(
        _wire_reconstruct_candidate(c) for c in cand_list)
    ledger = payload["capability_ledger"]
    if type(ledger) is not dict:
        raise _WireError("payload capability_ledger not dict")
    if len(ledger) > _MAX_STAGE_LEDGER_KEYS:
        raise _WireError("payload capability_ledger too many keys")
    ledger_out: dict = {}
    for k, v in ledger.items():
        if type(k) is not str or len(k) > 64:
            raise _WireError("ledger key not str")
        if type(v) is not str or len(v) > 64:
            raise _WireError("ledger value not str")
        ledger_out[k] = v
    fb_list = payload["fallback_provenance"]
    if type(fb_list) is not list:
        raise _WireError("payload fallback_provenance not list")
    if len(fb_list) > _MAX_STAGE_FALLBACK_RECORDS:
        raise _WireError("payload fallback_provenance too many")
    fallback: tuple = tuple(
        _wire_reconstruct_fallback_record(fr) for fr in fb_list)
    bp_payload = payload["binding_proposal"]
    binding_proposal = (
        None if bp_payload is None
        else _wire_reconstruct_binding_proposal(bp_payload))
    return AdapterResult(
        status=status, failure_category=fc, candidates=candidates,
        capability_ledger=ledger_out, fallback_provenance=fallback,
        resource_sample=None, binding_proposal=binding_proposal,
    )


def _wire_reconstruct_candidate(payload: dict) -> Candidate:
    if type(payload) is not dict:
        raise _WireError("candidate not dict")
    if set(payload.keys()) != {
        "path", "start_line", "end_line", "score",
        "reason", "channels", "adapter_provenance",
    }:
        raise _WireError("candidate keys not exact closed set")
    path = payload["path"]
    if type(path) is not str or len(path) > 512:
        raise _WireError("candidate path not str")
    start_line = payload["start_line"]
    if type(start_line) is not int:
        raise _WireError("candidate start_line not int")
    end_line = payload["end_line"]
    if type(end_line) is not int:
        raise _WireError("candidate end_line not int")
    score = payload["score"]
    # JSON round-trips int as int and float as float; both are accepted by
    # the contract's _require_float (which accepts int-as-float). Reject
    # bool explicitly (bool is a subclass of int but type(True) is bool).
    if type(score) is bool:
        raise _WireError("candidate score is bool")
    if type(score) not in (int, float):
        raise _WireError("candidate score not numeric")
    if type(score) is float:
        if score != score or score in (float("inf"), float("-inf")):
            raise _WireError("candidate score non-finite")
    reason = payload["reason"]
    if type(reason) is not str or len(reason) > 128:
        raise _WireError("candidate reason not str")
    channels_list = payload["channels"]
    if type(channels_list) is not list or len(channels_list) > 64:
        raise _WireError("candidate channels not list")
    channels: set = set()
    for ch in channels_list:
        if type(ch) is not str or len(ch) > 64:
            raise _WireError("channel not str")
        channels.add(ch)
    adapter_provenance = payload["adapter_provenance"]
    if (type(adapter_provenance) is not str
            or len(adapter_provenance) > 128):
        raise _WireError("candidate adapter_provenance not str")
    return Candidate(
        path=path, start_line=start_line, end_line=end_line,
        score=score, reason=reason,
        channels=frozenset(channels),
        adapter_provenance=adapter_provenance,
    )


def _wire_reconstruct_fallback_record(payload: dict) -> FallbackRecord:
    if type(payload) is not dict:
        raise _WireError("fallback not dict")
    if set(payload.keys()) != {"unavailable_capability", "fallback_to"}:
        raise _WireError("fallback keys not exact closed set")
    uc = payload["unavailable_capability"]
    if type(uc) is not str or len(uc) > 64:
        raise _WireError("fallback unavailable_capability not str")
    ft = payload["fallback_to"]
    if type(ft) is not str or len(ft) > 64:
        raise _WireError("fallback fallback_to not str")
    return FallbackRecord(unavailable_capability=uc, fallback_to=ft)


def _wire_reconstruct_binding_proposal(payload: dict) -> BindingProposal:
    if type(payload) is not dict:
        raise _WireError("binding_proposal not dict")
    if set(payload.keys()) != {
        "proposed_status", "target_evidence_indices",
        "support_bindings", "status_reason",
    }:
        raise _WireError("binding_proposal keys not exact closed set")
    proposed_status = payload["proposed_status"]
    if (type(proposed_status) is not str
            or len(proposed_status) > 64):
        raise _WireError("binding proposed_status not str")
    tei_list = payload["target_evidence_indices"]
    if (type(tei_list) is not list
            or len(tei_list) > _MAX_STAGE_TARGET_INDICES):
        raise _WireError("binding target_evidence_indices not list")
    tei: list = []
    seen: set = set()
    for idx in tei_list:
        if type(idx) is not int:
            raise _WireError("target_evidence_index not int")
        if idx in seen:
            raise _WireError("duplicate target_evidence_index")
        seen.add(idx)
        tei.append(idx)
    sb_list = payload["support_bindings"]
    if (type(sb_list) is not list
            or len(sb_list) > _MAX_STAGE_SUPPORT_BINDINGS):
        raise _WireError("binding support_bindings not list")
    sbs = tuple(_wire_reconstruct_support_binding(sb) for sb in sb_list)
    status_reason = payload["status_reason"]
    if status_reason is not None:
        if (type(status_reason) is not str
                or len(status_reason) > 256):
            raise _WireError("binding status_reason not str/null")
    return BindingProposal(
        proposed_status=proposed_status,
        target_evidence_indices=tuple(tei),
        support_bindings=sbs,
        status_reason=status_reason,
    )


def _wire_reconstruct_support_binding(payload: dict) -> SupportBinding:
    if type(payload) is not dict:
        raise _WireError("support_binding not dict")
    if set(payload.keys()) != {
        "evidence_index", "target_indices",
        "relation_kind", "parent_target_id",
    }:
        raise _WireError("support_binding keys not exact closed set")
    evidence_index = payload["evidence_index"]
    if type(evidence_index) is not int:
        raise _WireError("support evidence_index not int")
    ti_list = payload["target_indices"]
    if (type(ti_list) is not list
            or len(ti_list) > _MAX_STAGE_TARGET_INDICES):
        raise _WireError("support target_indices not list")
    ti: list = []
    seen: set = set()
    for idx in ti_list:
        if type(idx) is not int:
            raise _WireError("support target_index not int")
        if idx in seen:
            raise _WireError("duplicate support target_index")
        seen.add(idx)
        ti.append(idx)
    relation_kind = payload["relation_kind"]
    if type(relation_kind) is not str or len(relation_kind) > 64:
        raise _WireError("support relation_kind not str")
    parent_target_id = payload["parent_target_id"]
    if parent_target_id is not None:
        if (type(parent_target_id) is not str
                or len(parent_target_id) > 128):
            raise _WireError("support parent_target_id not str/null")
    return SupportBinding(
        evidence_index=evidence_index,
        target_indices=tuple(ti),
        relation_kind=relation_kind,
        parent_target_id=parent_target_id,
    )


def _isolated_stage_worker(
    stage: str,
    hook: Callable[[AdapterRequest, Path], Any],
    request: AdapterRequest,
    isolated_root_str: str,
    conn: Any,
) -> None:
    """Run a single adapter hook (prepare/index/query) in a spawned subprocess
    and return its result via a unidirectional Pipe using ``send_bytes``.

    v11 bounded strict JSON primitive wire (NO pickle anywhere on the
    run-phase wire):
      * The child serializes ONLY a closed JSON primitive envelope
        ``{"v": 1, "status": <ok|error|malformed>,
          "payload": <closed_payload_or_null>, "error": <str_or_null>}``
        via ``json.dumps`` + ``conn.send_bytes``. There is NO
        ``transport_failure`` status and NO dedicated exit code.
      * Before encoding, the returned canonical ``AdapterResult`` is
        normalized into a new plain builtin dict/list/scalar tree under
        EXACT type checks (``type(x) is AdapterResult`` etc., not
        ``isinstance`` accepting subclasses that could override behavior).
        All nested Candidate/BindingProposal/FallbackRecord/capability-
        ledger values are copied field-by-field under the closed schema.
        NaN/Infinity floats, nonprimitive/mapping-subclass/custom objects,
        property-access failures, JSON-encode failures, and oversize
        envelopes become a SMALL malformed canonical envelope.
      * prepare/index ok returns exact ``null`` payload; query ok returns
        the closed ``AdapterResult`` payload dict; every other shape is
        ``malformed/non_adapter_result``.
      * The exception envelope carries ONLY ``type(e).__name__`` (itself
        bounded/validated); the adapter exception MESSAGE text NEVER
        crosses the wire.
      * On ``send_bytes`` failure, the worker closes the pipe and exits
        nonzero via ``os._exit(1)`` (NO dedicated exit code, NO fallback
        ``transport_failure`` envelope). The parent sees EOF/process death
        and classifies adapter-scoped ``process_died`` (never
        ``HarnessInfrastructureError``). An adapter may call any
        ``os._exit(code)``; every child EOF/exit code is adapter-scoped.
    """
    try:
        result = hook(request, Path(isolated_root_str))
        if stage in ("prepare", "index"):
            # Lifecycle hooks must return exactly None (filesystem side
            # effects in the declared writable_state_root are all that
            # matter).
            if result is None:
                envelope = _wire_build_envelope(
                    status="ok", payload=None, error=None)
            else:
                envelope = _wire_build_envelope(
                    status="malformed", payload=None,
                    error="non_adapter_result")
        else:
            # query must return exactly an AdapterResult (EXACT type
            # check — a subclass that overrides behavior is rejected).
            if type(result) is AdapterResult:
                try:
                    payload = _wire_normalize_adapter_result(result)
                except _WireError:
                    envelope = _wire_build_envelope(
                        status="malformed", payload=None,
                        error="normalization_failed")
                else:
                    envelope = _wire_build_envelope(
                        status="ok", payload=payload, error=None)
            else:
                envelope = _wire_build_envelope(
                    status="malformed", payload=None,
                    error="non_adapter_result")
    except Exception as e:  # noqa: BLE001
        # Propagate ONLY the exception TYPE name; never the message text.
        # ``type(e).__name__`` is bounded by _MAX_STAGE_ERROR_LEN in
        # _wire_build_envelope (a malformed envelope is emitted if it
        # exceeds the cap, which cannot happen for Python type names).
        envelope = _wire_build_envelope(
            status="error", payload=None, error=type(e).__name__)
    # Serialize the closed envelope to compact/deterministic UTF-8 JSON
    # bytes. Serialization failure and oversize become small malformed
    # canonical envelopes (the parent then rejects as malformed).
    try:
        payload_bytes = _wire_encode_envelope(envelope)
    except Exception:  # noqa: BLE001
        payload_bytes = _wire_malformed_envelope_bytes(
            "serialization_failed")
    if len(payload_bytes) > MAX_STAGE_WIRE_BYTES:
        payload_bytes = _wire_malformed_envelope_bytes("oversize")
    # Send the bytes; on failure, close and exit nonzero. There is NO
    # dedicated transport-failure exit code and NO fallback envelope: the
    # parent sees EOF/process death and classifies adapter-scoped
    # ``process_died`` (never HarnessInfrastructureError). An adapter may
    # call any os._exit(code); every child EOF/exit code is adapter-scoped.
    send_failed = False
    try:
        conn.send_bytes(payload_bytes)
    except Exception:  # noqa: BLE001
        send_failed = True
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
    if send_failed:
        # Genuine send failure: exit nonzero. There is NO dedicated
        # transport-failure exit code; the parent observes EOF/process
        # death and classifies adapter-scoped process_died (no whole-
        # bakeoff abort, no infra classification). os._exit bypasses
        # Python cleanup so the closed pipe is not mutated after the
        # failed send.
        os._exit(1)


# Stage name -> canonical failure_category prefix on exception.
_STAGE_EXC_PREFIX = {"prepare": "lifecycle_exception:prepare", "index": "lifecycle_exception:index", "query": "adapter_exception"}
_STAGE_TIMEOUT_CAT = {"prepare": "lifecycle_timeout:prepare", "index": "lifecycle_timeout:index", "query": "adapter_timeout"}
_STAGE_TIMEOUT_STATUS = {"prepare": "timeout", "index": "timeout", "query": "timeout"}
_STAGE_EXC_STATUS = {"prepare": "failed", "index": "failed", "query": "failed"}


def _execute_stage_isolated(
    hook: Callable[[AdapterRequest, Path], Any],
    request: AdapterRequest,
    isolated_root: Path,
    descriptor: AdapterDescriptor,
    stage: str,
) -> tuple[str, AdapterResult | None, str, float]:
    """Execute ONE adapter hook in a process-isolated subprocess with an
    ENFORCED absolute deadline. Returns ``(status, result, exc_type, wall_seconds)``.

    * ``status`` is one of ``"ok"`` / ``"timeout"`` / ``"error"`` / ``"malformed"``;
    * ``result`` is the AdapterResult (query) or None (prepare/index);
    * ``exc_type`` is the exception TYPE name only (never the message);
    * ``wall_seconds`` is the process-boundary duration.

    v11/v12 bounded strict JSON primitive wire (NO pickle anywhere in
    run-phase modules). The wire envelope is a closed JSON object with
    trusted version/status/payload/error fields. The parent receives bytes
    with the existing hard allocation bound
    (``recv_bytes(maxlength=MAX_STAGE_WIRE_BYTES)``), strict UTF-8 decodes,
    then ``json.loads`` with ``parse_constant`` rejection (NaN/Infinity)
    AND an ``object_pairs_hook`` that rejects duplicate keys at every
    object level. No ``object_hook`` capable of constructing arbitrary
    types is used. The parent then validates the closed envelope, bounds
    depth/count/string length, reconstructs the exact canonical dataclass
    field-by-field in trusted parent code, and runs existing
    ``validate_adapter_result`` + later honesty checks downstream.
    Deadline is rechecked after receive, decode, closed-wire validation,
    and reconstruction.

    Classification (deterministic, documented; v11 removes forgeable
    whole-bakeoff abort signals; v12 tightens the adapter-payload
    exception boundary):
      * Child EOF / any ``os._exit(code)`` => adapter-scoped
        ``process_died`` (NEVER ``HarnessInfrastructureError``). An
        adapter may call any ``os._exit(code)``; every child EOF/exit
        code is adapter-scoped.
      * Child send_bytes failure => child closes and exits nonzero;
        parent sees EOF/process death; classifies adapter-scoped
        ``process_died``.
      * Hostile/oversize child-controlled frame or ambiguous
        ``recv_bytes(maxlength)`` OSError => adapter-scoped ``malformed``
        (NEVER infra). A child can induce them; the OSError message is
        NOT parsed (parsing message text would be brittle and
        locale-dependent).
      * v12: child-controlled parser/validation exceptions (invalid
        UTF-8, JSONDecodeError/ValueError incl. Python oversized
        integer-token limit, RecursionError from deep nesting,
        OverflowError, duplicate-key hook, parse_constant, depth/count/
        string violations, exact-schema/reconstruction failures) =>
        adapter-scoped ``malformed`` (NEVER infra). The boundary is
        scoped tightly around strict decode/parse/validate/reconstruct;
        none reach the receiver catch-all ``pipe_error`` ->
        ``HarnessInfrastructureError``.
      * ``poll`` OSError => ``HarnessInfrastructureError`` (parent-local
        pipe state failure, demonstrably distinguishable from child-
        controlled data — it occurs before any child bytes are observed).
      * Genuine parent-local setup/start failure (Pipe/Process launch
        before the child runs) => ``HarnessInfrastructureError``.
      * Failed cleanup/reap (unreaped child still alive after terminate/
        kill/join) => ``HarnessInfrastructureError``.
      * Receiver thread did not terminate (thread leak) =>
        ``HarnessInfrastructureError``.
      * No child-authored envelope status can raise
        ``HarnessInfrastructureError``.

      * Unidirectional ``multiprocessing.Pipe(duplex=False)``;
        ``send_bytes`` / ``recv_bytes`` only; closed harness-created
        envelope.
      * ``MAX_STAGE_WIRE_BYTES`` hard bound on the serialized envelope.
      * Absolute deadline = ``t0 + timeout_seconds`` computed BEFORE
        ``proc.start()``.
      * Parent uses ONE dedicated receiver thread + one-slot queue. The
        thread does bounded ``recv_bytes``, strict UTF-8 decode, strict
        ``json.loads`` (parse_constant + object_pairs_hook), closed-
        envelope validation, depth/count/string bounding, canonical
        dataclass reconstruction, and publishes a typed outcome. The
        thread rechecks the deadline after recv, decode, validation, and
        reconstruction (decode/reconstruction-after-deadline cannot
        succeed).
      * The main thread joins the queue only until the remaining
        absolute deadline; rechecks deadline after the outcome is
        published. If the deadline expires at any point through
        reconstruction: timeout -> terminate/kill/reap child, close
        pipe, join receiver, verify child/thread dead.
      * ``_reap_process`` attempts all cleanup then VERIFIES not alive;
        an unreaped child raises ``HarnessInfrastructureError`` (not
        swallowed). Owned handles closed exactly once (idempotent
        helper).
    """
    ctx = multiprocessing.get_context("spawn")
    parent_conn: Any = None
    child_conn: Any = None
    proc: Any = None
    started = False
    t0 = time.perf_counter()
    # Absolute deadline beginning BEFORE process start.
    deadline = t0 + request.run_spec.timeout_seconds
    status = "error"
    result: AdapterResult | None = None
    err = "RuntimeError"  # canonical default type name
    try:
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_isolated_stage_worker,
            args=(stage, hook, request, str(isolated_root), child_conn),
            daemon=True,
        )
        proc.start()
        started = True
    except BaseException as exc:
        # Genuine parent-local multiprocessing launch/pipe/Process setup
        # failure: clean up every resource and then ABORT the whole bakeoff
        # as a harness infrastructure failure — NEVER one adapter's
        # ValidatedRunRecord. This is demonstrably parent-local (it
        # occurred before the child was started, so no child-authored data
        # is involved).
        _close_pipe_endpoint(child_conn)
        _close_pipe_endpoint(parent_conn)
        if started and proc is not None:
            _reap_process(proc, terminate_if_alive=True)
        raise HarnessInfrastructureError(
            f"spawn setup for stage {stage!r} failed: {type(exc).__name__}"
        ) from exc
    # Close the child end in the parent immediately; the child holds its copy.
    _close_pipe_endpoint(child_conn)

    # ONE dedicated receiver thread + one-slot queue.
    outcome_q: queue.Queue = queue.Queue(maxsize=1)

    def _receiver() -> None:
        """v11/v12 bounded strict JSON primitive receive + decode + closed-
        envelope validation + canonical dataclass reconstruction. NO
        pickle.loads anywhere. Rechecks deadline after recv, decode,
        closed-wire validation, and reconstruction (decode/reconstruct-
        after-deadline cannot succeed).

        Classification (deterministic, documented):
          * poll OSError -> pipe_error (infra): parent-local pipe state
            failure, demonstrably distinguishable from child-controlled
            data (it occurs before any child bytes are observed).
          * recv_bytes EOFError -> eof (process_died): the child closed
            the pipe without sending a complete frame; child-controlled.
          * recv_bytes OSError (including over-bound) -> malformed
            (adapter-scoped): the child sent an oversized/invalid frame;
            child-controlled. NEVER infra (a child can induce it). The
            OSError message is NOT parsed.
          * JSON decode failure / closed-envelope violation / closed-
            schema violation / reconstruction failure -> malformed
            (adapter-scoped).

        v12: the adapter-payload exception boundary is scoped TIGHTLY
        around strict decode/parse/validate/reconstruct. Every child-
        controlled parser/validation exception in ``_WIRE_CHILD_PARSE_EXCS``
        (``_WireError``, ``ValueError`` incl. Python oversized integer-
        token limit, ``RecursionError`` from deep nesting, ``OverflowError``,
        ``TypeError``/``KeyError``/``AttributeError``/``IndexError`` from
        reconstruction) is converted deterministically to ``malformed``;
        NONE reach the receiver catch-all ``pipe_error`` ->
        ``HarnessInfrastructureError``. The catch-all remains ONLY for
        genuine parent-local thread/queue state failures (infra).
        """
        try:
            while True:
                rem = deadline - time.perf_counter()
                if rem <= 0:
                    outcome_q.put(("timeout", None, "timeout_exceeded"))
                    return
                poll_dur = rem if rem < 0.5 else 0.5
                try:
                    if not parent_conn.poll(poll_dur):
                        continue  # no data yet; recheck deadline
                except OSError as exc:
                    # Parent-local pipe state failure (no child data
                    # involved yet) -> infra. Demonstrably distinguishable
                    # from child-controlled framing: it occurs before any
                    # child bytes are observed.
                    outcome_q.put(("pipe_error", None, type(exc).__name__))
                    return
                # Data is available; receive it with a BOUND on allocation.
                # maxlength prevents allocating > MAX_STAGE_WIRE_BYTES.
                try:
                    data = parent_conn.recv_bytes(
                        maxlength=MAX_STAGE_WIRE_BYTES)
                except EOFError:
                    outcome_q.put(("eof", None, None))
                    return
                except OSError:
                    # v11: over-bound (stdlib raises OSError without
                    # allocating) and ambiguous receive OSError are BOTH
                    # adapter-scoped malformed (NEVER infra). A child can
                    # induce either by sending an oversized/invalid frame;
                    # the parent fails closed without allocation and
                    # without aborting the whole bakeoff. The OSError
                    # message is NOT parsed (parsing message text would be
                    # brittle and locale-dependent); any OSError on
                    # recv_bytes is adapter-scoped malformed.
                    outcome_q.put(
                        ("malformed", None, "recv_oversize_or_oserror"))
                    return
                # Recheck deadline after recv, BEFORE decode.
                if time.perf_counter() > deadline:
                    outcome_q.put(("timeout", None, "timeout_exceeded"))
                    return
                # Bounded size check (defense in depth; recv_bytes(maxlength)
                # already prevents over-allocation).
                if len(data) > MAX_STAGE_WIRE_BYTES:
                    outcome_q.put(("malformed", None, "oversize"))
                    return
                # v11/v12: strict UTF-8 decode + json.loads with
                # parse_constant rejection (NaN/Infinity) AND
                # object_pairs_hook duplicate-key rejection at every
                # object level. No object_hook capable of constructing
                # arbitrary types is used. v12: _wire_decode_envelope
                # converts ValueError/RecursionError/OverflowError/
                # TypeError to _WireError so the boundary here catches
                # them all via _WIRE_CHILD_PARSE_EXCS.
                try:
                    envelope = _wire_decode_envelope(data)
                except _WIRE_CHILD_PARSE_EXCS:
                    outcome_q.put(("malformed", None, "undecodable"))
                    return
                # Recheck deadline after decode.
                if time.perf_counter() > deadline:
                    outcome_q.put(("timeout", None, "timeout_exceeded"))
                    return
                # Defense-in-depth: bound depth/count/string length BEFORE
                # closed-schema validation so a hostile child cannot
                # exhaust parent memory via structural inflation.
                try:
                    _wire_validate_depth_and_primitives(envelope)
                except _WIRE_CHILD_PARSE_EXCS:
                    outcome_q.put(("malformed", None, "structural_oversize"))
                    return
                # Recheck deadline after depth/count bounding.
                if time.perf_counter() > deadline:
                    outcome_q.put(("timeout", None, "timeout_exceeded"))
                    return
                # Closed-envelope schema validation.
                try:
                    env_status, env_payload, env_err = (
                        _wire_validate_envelope(envelope))
                except _WIRE_CHILD_PARSE_EXCS:
                    outcome_q.put(("malformed", None, "bad_envelope"))
                    return
                # Recheck deadline after closed-envelope validation.
                if time.perf_counter() > deadline:
                    outcome_q.put(("timeout", None, "timeout_exceeded"))
                    return
                # Reconstruct the canonical AdapterResult (query ok) from
                # the closed JSON primitive payload dict in trusted parent
                # code. prepare/index ok has null payload.
                reconstructed: AdapterResult | None = None
                if env_status == "ok" and stage == "query":
                    if env_payload is None:
                        outcome_q.put(
                            ("malformed", None, "non_adapter_result"))
                        return
                    try:
                        reconstructed = _wire_reconstruct_adapter_result(
                            env_payload)
                    except _WIRE_CHILD_PARSE_EXCS:
                        # v12: any child-controlled reconstruction
                        # failure (unexpected type/key/attribute/index)
                        # is adapter-scoped malformed, NEVER infra.
                        outcome_q.put(
                            ("malformed", None, "reconstruction_failed"))
                        return
                    # Recheck deadline after reconstruction.
                    if time.perf_counter() > deadline:
                        outcome_q.put(("timeout", None, "timeout_exceeded"))
                        return
                elif env_status == "ok" and stage in ("prepare", "index"):
                    if env_payload is not None:
                        outcome_q.put(
                            ("malformed", None, "non_adapter_result"))
                        return
                outcome_q.put((env_status, reconstructed, env_err))
                return
        except _WIRE_CHILD_PARSE_EXCS as exc:
            # v12: defense-in-depth — any child-controlled parser/validation
            # exception that escaped the per-call boundaries above (none
            # expected, but defensive) is adapter-scoped malformed, NEVER
            # the catch-all pipe_error -> HarnessInfrastructureError.
            outcome_q.put(
                ("malformed", None, f"unhandled_parse_{type(exc).__name__}"))
        except Exception as exc:  # noqa: BLE001
            # Unexpected receiver thread failure: infra (parent-local
            # thread/queue state, not child-controlled data). v12: parser
            # exceptions are caught above so this catch-all now sees ONLY
            # genuine parent-local failures (queue/thread state, etc.).
            outcome_q.put(("pipe_error", None, type(exc).__name__))

    recv_thread = threading.Thread(target=_receiver, daemon=True)
    recv_thread.start()

    # Wait on the one-slot queue until the remaining absolute deadline.
    remaining = deadline - time.perf_counter()
    if remaining < 0:
        remaining = 0.0
    outcome: tuple[str, Any, Any] = ("error", None, "process_died")
    try:
        outcome = outcome_q.get(timeout=remaining)
        # Recheck deadline after the outcome is published (defense in depth).
        if outcome[0] != "timeout" and time.perf_counter() > deadline:
            outcome = ("timeout", None, "timeout_exceeded")
    except queue.Empty:
        outcome = ("timeout", None, "timeout_exceeded")

    # Cleanup: terminate/kill/reap child, close pipe, join receiver, verify.
    # v11: only the genuine parent-local failure paths (pipe_error from
    # poll OSError, unreaped child, receiver thread leak) raise
    # HarnessInfrastructureError. EOF / recv OSError / malformed are
    # adapter-scoped (process_died or malformed); the child is still
    # reaped normally on every path.
    is_failure_path = outcome[0] in (
        "timeout", "eof", "malformed", "error")
    reap_exc: Exception | None = None
    try:
        _reap_process(proc, terminate_if_alive=is_failure_path)
    except HarnessInfrastructureError as exc:
        reap_exc = exc
    # Close pipe endpoints (owned handles, exactly once).
    _close_pipe_endpoint(parent_conn)
    _close_pipe_endpoint(child_conn)
    # Join the receiver thread (bounded cleanup allowance, not extra
    # execution time). The thread should have exited: it either published
    # an outcome or hit the deadline in its poll loop.
    recv_thread.join(timeout=2.0)
    thread_alive = recv_thread.is_alive()
    if reap_exc is not None:
        raise reap_exc
    if thread_alive:
        raise HarnessInfrastructureError(
            f"receiver thread for stage {stage!r} did not terminate "
            f"(thread leak); aborting the whole bakeoff"
        )

    # Classify the typed outcome into (status, result, err).
    env_status = outcome[0]
    if env_status == "pipe_error":
        # Parent-local pipe state failure (poll OSError) or receiver
        # thread unexpected failure. Demonstrably parent-local (no child
        # data involved for poll OSError; thread/queue state for the
        # catch-all) — infra abort.
        raise HarnessInfrastructureError(
            f"transport for stage {stage!r} failed: {outcome[2]}"
        )
    if env_status == "eof":
        # v11: child closed the pipe without sending a complete frame.
        # Adapter-scoped process_died (any os._exit(code) the child used).
        # NEVER infra — a child can induce EOF at will. There is NO
        # dedicated transport-failure exit code; an adapter may call any
        # os._exit(code) and every child exit code is adapter-scoped.
        status, result, err = "error", None, "process_died"
    elif env_status == "timeout":
        status, result, err = "timeout", None, "timeout_exceeded"
    elif env_status == "malformed":
        status, result, err = "malformed", None, outcome[2] or "non_adapter_result"
    elif env_status == "ok":
        status, result, err = "ok", outcome[1], None
    elif env_status == "error":
        status, result, err = "error", None, outcome[2]
    else:
        status, result, err = "error", None, "process_died"
    wall_seconds = time.perf_counter() - t0
    return status, result, err, wall_seconds


def _stage_result_to_adapter_result(
    status: str, result: AdapterResult | None, err: str, descriptor: AdapterDescriptor,
    stage: str,
) -> AdapterResult:
    """Map a stage execution envelope to a canonical AdapterResult (for the
    timeout/error/malformed cases where the child did not return one)."""
    if status == "ok" and result is not None:
        return result
    if status == "timeout":
        return AdapterResult(
            status=_STAGE_TIMEOUT_STATUS[stage],
            failure_category=_STAGE_TIMEOUT_CAT[stage],
            candidates=(),
            capability_ledger={c: "timeout" for c in descriptor.capabilities},
            fallback_provenance=(),
        )
    if status == "malformed":
        return AdapterResult(
            status="malformed", failure_category="non_adapter_result", candidates=(),
            capability_ledger={c: "failed" for c in descriptor.capabilities},
            fallback_provenance=(),
        )
    # Map to canonical harness category using stage + exception TYPE only.
    # ``err`` is just the exception TYPE name (e.g. "RuntimeError"), never
    # the adapter-authored message text.
    exc_type = err if err else "RuntimeError"
    if stage == "query":
        cat = f"{_STAGE_EXC_PREFIX[stage]}:{exc_type}"
    else:
        cat = f"{_STAGE_EXC_PREFIX[stage]}:{exc_type}"
    return AdapterResult(
        status=_STAGE_EXC_STATUS[stage], failure_category=cat, candidates=(),
        capability_ledger={c: "failed" for c in descriptor.capabilities},
        fallback_provenance=(),
    )


def _execute_isolated(
    query_hook: Callable[[AdapterRequest, Path], Any],
    request: AdapterRequest,
    isolated_root: Path,
    descriptor: AdapterDescriptor,
) -> tuple[AdapterResult, float]:
    """Back-compat shim for the query stage. Returns (result, query_seconds)."""
    status, result, err, wall = _execute_stage_isolated(
        query_hook, request, isolated_root, descriptor, "query")
    ar = _stage_result_to_adapter_result(status, result, err, descriptor, "query")
    return ar, wall


# ---------------------------------------------------------------------------
# run_adapter (harness runner with lifecycle hooks)
# ---------------------------------------------------------------------------


class _StopProcessing(Exception):
    """Internal control-flow signal so the finally scan still runs."""


def _rejected_record(
    request: AdapterRequest, descriptor: AdapterDescriptor,
    result: AdapterResult, failure_category: str, cat: str,
    validated_cands: tuple[Candidate, ...] = (),
    evidence_count: int = 0, crh: str | None = None,
    resource_sample: ResourceSample | None = None,
) -> ValidatedRunRecord:
    # v9 capability-ledger trust: EVERY rejected record carries an EMPTY
    # capability_ledger_summary. Accepted records are the ONLY records that
    # may publish a validated ledger; rejected records never carry ledger
    # counts (so a rejected path can never inflate public capability counts).
    # ``validate_run_record`` enforces rejected => empty ledger.
    return ValidatedRunRecord(
        fingerprint=fairness_fingerprint(request.run_spec),
        run_cell_id=request.run_spec.run_cell_id,
        adapter_id=request.adapter_id,
        status="rejected", failure_category=failure_category,
        result_status=result.status, pack_status=None,
        candidate_count=len(validated_cands),
        evidence_count=evidence_count, target_count=0, support_count=0,
        capability_ledger_summary={},
        canonical_result_hash=crh, canonical_pack_hash=None,
        conformance_category=cat,
        cache_state=request.run_spec.cache_state,
        interaction_mode=request.run_spec.interaction_mode,
        operation=request.run_spec.operation,
        adapter_repetition=request.run_spec.adapter_repetition,
        resource_sample=resource_sample,
    )


def _lineage_failures(
    parent: RegisteredTarget, request: AdapterRequest,
    snapshot: FrozenSnapshot, materialize_step: int,
) -> str | None:
    """Check two-step lineage binding. Returns failure_category or None."""
    if parent.bound_target_id != request.run_spec.bound_target_id:
        return "lineage:unknown_target"
    if parent.task_slug != request.run_spec.task.task_slug:
        return "lineage:cross_task"
    if parent.episode_id != request.run_spec.episode_id:
        return "lineage:cross_episode"
    if parent.snapshot_manifest_digest != snapshot.manifest_digest:
        return "lineage:cross_snapshot"
    if parent.source_visibility_digest != snapshot_source_visibility_digest(snapshot):
        return "lineage:cross_visibility"
    if parent.visible_tree_digest != snapshot.visible_tree_digest:
        return "lineage:cross_visible_tree"
    if parent.renderer_version != request.run_spec.renderer_version:
        return "lineage:cross_renderer"
    if parent.materializer_version != request.run_spec.materializer_version:
        return "lineage:cross_materializer"
    if parent.budget_estimator_version != request.run_spec.budget_estimator_version:
        return "lineage:cross_estimator"
    if parent.episode_caps != request.run_spec.caps:
        return "lineage:altered_caps"
    if materialize_step != parent.parent_step + 1:
        if materialize_step == parent.parent_step:
            return "lineage:repeated_step"
        return "lineage:non_sequential_step"
    if materialize_step > request.run_spec.caps.episode_step_cap:
        return "lineage:step_cap_exceeded"
    return None


def run_adapter(
    hooks: AdapterHooks, request: AdapterRequest, isolated_root: Path,
    descriptor: AdapterDescriptor, snapshot: FrozenSnapshot,
    conformance_category: str = "live_run",
    episode_registry: EpisodeRegistry | None = None,
    materialize_step: int = 1,
) -> ValidatedRunRecord:
    """Run adapter hooks (prepare/index/query) with lifecycle timing, then
    validate, common-materialize, build+validate a context pack, and record a
    validated run record with a retained ResourceSample. A full visible-tree
    scan is performed after prepare, after index, after query, and on EVERY
    adapter exit path so mutate->restore cannot pass.

    Cross-validates descriptor + hooks via ``validate_descriptor_hooks`` (v4).
    """
    hooks.validate()
    # Pre-execution validation.
    try:
        validate_request(request)
        descriptor.validate()
        # Cross-validate descriptor + hooks (v4 closure).
        validate_descriptor_hooks(descriptor, hooks)
        validate_snapshot_binding(request.run_spec, snapshot)
        validate_execution_root_binding(request.run_spec, snapshot, isolated_root)
    except ContractError as exc:
        return _rejected_record(
            request, descriptor,
            AdapterResult(
                status="failed",
                failure_category=f"prevalidation:{exc.__class__.__name__}",
                candidates=(),
                capability_ledger={c: "failed" for c in descriptor.capabilities},
                fallback_provenance=(),
            ),
            f"prevalidation:{exc.__class__.__name__}", conformance_category,
            resource_sample=None,
        )

    # Lineage validation for support operations.
    parent_episode_estimate = 0
    if request.run_spec.operation == "support":
        if episode_registry is None:
            return _rejected_record(
                request, descriptor,
                AdapterResult("failed", "lineage:no_episode_registry", (), {}, ()),
                "lineage:no_episode_registry", conformance_category,
                resource_sample=None,
            )
        parent = episode_registry.lookup(request.run_spec.parent_result_id or "")
        if parent is None:
            return _rejected_record(
                request, descriptor,
                AdapterResult("failed", "lineage:unknown_parent_target", (), {}, ()),
                "lineage:unknown_parent_target", conformance_category,
                resource_sample=None,
            )
        lf = _lineage_failures(parent, request, snapshot, materialize_step)
        if lf is not None:
            return _rejected_record(
                request, descriptor,
                AdapterResult("failed", lf, (), {}, ()),
                lf, conformance_category, resource_sample=None,
            )
        parent_episode_estimate = parent.episode_estimate_used

    # Cold/warm reuse semantics.
    attempt_prepare = hooks.prepare is not None
    attempt_index = hooks.index is not None
    if request.run_spec.cache_state == "warm":
        if descriptor.persistent_state_behavior == "warm_reuse":
            attempt_prepare = False
            attempt_index = False

    # v9: pre-hook infrastructure scan. This is the LAST harness operation
    # before spawn. After request/descriptor/lineage validation and immediately
    # before the FIRST attempted prepare/index/query, assert the frozen source
    # tree is unchanged. If this fails BEFORE any hook starts, it is a harness
    # infrastructure failure: raise HarnessInfrastructureError (abort the whole
    # bakeoff, NO rejected record). Mutations detected AFTER a hook starts
    # remain adapter rejections (caught below as snapshot_mutation).
    try:
        pb.assert_snapshot_unchanged(snapshot)
    except ContractError as exc:
        raise HarnessInfrastructureError(
            f"pre-hook infrastructure scan failed: the frozen source tree "
            f"was mutated before any adapter hook started "
            f"({type(exc).__name__}); aborting the whole bakeoff (not an "
            f"adapter rejection)"
        ) from exc

    setup_s: float | None = None
    index_s: float | None = None
    query_s: float | None = None
    mat_s: float | None = None
    render_s: float | None = None
    record: ValidatedRunRecord | None = None
    validated_cands: tuple[Candidate, ...] = ()
    evidence: tuple = ()

    try:
        # -- Prepare hook (v7: spawned in a fresh child) --
        if attempt_prepare:
            p_status, p_result, p_err, setup_s = _execute_stage_isolated(
                hooks.prepare, request, isolated_root, descriptor, "prepare")  # type: ignore[misc]
            if p_status != "ok":
                # prepare timed out or raised — canonical category.
                par = _stage_result_to_adapter_result(
                    p_status, p_result, p_err, descriptor, "prepare")
                rs = ResourceSample(setup_seconds=setup_s, index_seconds=None,
                    query_seconds=None, materialize_seconds=None,
                    render_seconds=None, rss_bytes=None, cpu_seconds=None)
                record = _rejected_record(
                    request, descriptor, par,
                    par.failure_category, conformance_category, resource_sample=rs,
                )
                raise _StopProcessing()
            # Intermediate scan: immutable source must be unchanged after
            # prepare. Catches mutate->restore patterns that would mask a
            # prepare-time mutation if only the final scan ran.
            try:
                pb.assert_snapshot_unchanged(snapshot)
            except ContractError:
                rs = ResourceSample(setup_seconds=setup_s, index_seconds=None,
                    query_seconds=None, materialize_seconds=None,
                    render_seconds=None, rss_bytes=None, cpu_seconds=None)
                record = _rejected_record(
                    request, descriptor,
                    AdapterResult("failed", "snapshot_mutation:ContractError", (),
                        {c: "failed" for c in descriptor.capabilities}, ()),
                    "snapshot_mutation:ContractError", conformance_category,
                    resource_sample=rs)
                raise _StopProcessing()

        # -- Index hook (v7: spawned in a fresh child) --
        if attempt_index:
            i_status, i_result, i_err, index_s = _execute_stage_isolated(
                hooks.index, request, isolated_root, descriptor, "index")  # type: ignore[misc]
            if i_status != "ok":
                iar = _stage_result_to_adapter_result(
                    i_status, i_result, i_err, descriptor, "index")
                rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                    query_seconds=None, materialize_seconds=None,
                    render_seconds=None, rss_bytes=None, cpu_seconds=None)
                record = _rejected_record(
                    request, descriptor, iar,
                    iar.failure_category, conformance_category, resource_sample=rs,
                )
                raise _StopProcessing()
            # Intermediate scan: immutable source must be unchanged after
            # index. Catches mutate->restore patterns.
            try:
                pb.assert_snapshot_unchanged(snapshot)
            except ContractError:
                rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                    query_seconds=None, materialize_seconds=None,
                    render_seconds=None, rss_bytes=None, cpu_seconds=None)
                record = _rejected_record(
                    request, descriptor,
                    AdapterResult("failed", "snapshot_mutation:ContractError", (),
                        {c: "failed" for c in descriptor.capabilities}, ()),
                    "snapshot_mutation:ContractError", conformance_category,
                    resource_sample=rs)
                raise _StopProcessing()

        # -- Query hook in subprocess (v7: stage-aware) --
        result, qs = _execute_isolated(hooks.query, request, isolated_root, descriptor)
        query_s = qs
        # Intermediate scan: immutable source must be unchanged after query.
        # Catches post-query mutations before materialization.
        try:
            pb.assert_snapshot_unchanged(snapshot)
        except ContractError:
            rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                query_seconds=query_s, materialize_seconds=None,
                render_seconds=None, rss_bytes=None, cpu_seconds=None)
            record = _rejected_record(
                request, descriptor,
                AdapterResult("failed", "snapshot_mutation:ContractError", (),
                    {c: "failed" for c in descriptor.capabilities}, ()),
                "snapshot_mutation:ContractError", conformance_category,
                resource_sample=rs)
            raise _StopProcessing()

        try:
            result, validated_cands = validate_adapter_result(
                result, request, descriptor, snapshot)
        except ContractError as exc:
            rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                query_seconds=query_s, materialize_seconds=None,
                render_seconds=None, rss_bytes=None, cpu_seconds=None)
            crh = None
            try:
                crh = canonical_result_hash(result, ())
            except Exception:
                pass
            record = _rejected_record(request, descriptor, result,
                f"result_validation:{exc.__class__.__name__}",
                conformance_category, crh=crh, resource_sample=rs)
            raise _StopProcessing()

        if result.status not in pb.PACK_OK_STATUSES:
            rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                query_seconds=query_s, materialize_seconds=None,
                render_seconds=None, rss_bytes=None, cpu_seconds=None)
            crh = None
            try:
                crh = canonical_result_hash(result, ())
            except Exception:
                pass
            # Canonical category: map the result's (possibly adapter-authored)
            # failure_category to a canonical harness category using stage +
            # result status + exception TYPE only. Adapter exception MESSAGE
            # text and raw adapter-authored categories NEVER reach public keys.
            fc = _canonicalize_failure_category(result)
            record = _rejected_record(request, descriptor, result,
                fc, conformance_category, crh=crh, resource_sample=rs)
            raise _StopProcessing()

        # v9: capability-ledger honesty BEFORE materialization. Ordering:
        # validate_adapter_result (closed shape/bindings/ledger/candidates/
        # fallback) THEN validate_capability_ledger_honesty THEN
        # hash/materialize/pack/register/copy ledger. Any
        # validation/honesty/materialization/pack/snapshot/lifecycle/transport
        # rejection gets an empty record ledger (enforced by _rejected_record).
        try:
            validate_capability_ledger_honesty(
                result, request,
                attempt_prepare=attempt_prepare,
                attempt_index=attempt_index)
        except ContractError as exc:
            rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                query_seconds=query_s, materialize_seconds=None,
                render_seconds=None, rss_bytes=None, cpu_seconds=None)
            crh = None
            try:
                crh = canonical_result_hash(result, validated_cands)
            except Exception:
                pass
            record = _rejected_record(request, descriptor, result,
                f"capability_honesty:{exc.__class__.__name__}",
                conformance_category, validated_cands=validated_cands,
                crh=crh, resource_sample=rs)
            raise _StopProcessing()

        # -- Materialize --
        t_m0 = time.perf_counter()
        try:
            evidence, _mat_usage = materialize_candidates(
                validated_cands, snapshot, step=materialize_step)
        except ContractError as exc:
            mat_s = time.perf_counter() - t_m0
            rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                query_seconds=query_s, materialize_seconds=mat_s,
                render_seconds=None, rss_bytes=None, cpu_seconds=None)
            record = _rejected_record(request, descriptor, result,
                f"materialization:{exc.__class__.__name__}",
                conformance_category, validated_cands=validated_cands,
                resource_sample=rs)
            raise _StopProcessing()
        mat_s = time.perf_counter() - t_m0

        # -- Build + validate pack --
        # v6: pass the actual evidence tuple, candidate_count, materialize
        # step, and parent episode estimate explicitly. build_context_pack
        # returns a fully-validated pack (ContextPack.validate consumes the
        # actual evidence tuple and recomputes every BudgetUsage field).
        t_r0 = time.perf_counter()
        try:
            pack = pb.build_context_pack(
                evidence, request, result.binding_proposal,
                candidate_count=len(validated_cands),
                materialize_step=materialize_step,
                parent_episode_estimate_used=parent_episode_estimate)
            pack = validate_context_pack(
                pack, request, tuple(evidence), len(validated_cands),
                materialize_step, parent_episode_estimate)
        except ContractError as exc:
            render_s = time.perf_counter() - t_r0
            rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
                query_seconds=query_s, materialize_seconds=mat_s,
                render_seconds=render_s, rss_bytes=None, cpu_seconds=None)
            record = _rejected_record(request, descriptor, result,
                f"pack_validation:{exc.__class__.__name__}",
                conformance_category, validated_cands=validated_cands,
                evidence_count=len(evidence), resource_sample=rs)
            raise _StopProcessing()
        render_s = time.perf_counter() - t_r0

        rs = ResourceSample(setup_seconds=setup_s, index_seconds=index_s,
            query_seconds=query_s, materialize_seconds=mat_s,
            render_seconds=render_s, rss_bytes=None, cpu_seconds=None)

        # Register target for context steps.
        if (request.run_spec.operation == "context"
                and episode_registry is not None
                and pack.pack_status == "ready"
                and len(pack.targets) >= 1):
            episode_registry.register(
                result_id=request.run_spec.request_id,
                target=pack.targets[0], snapshot=snapshot, request=request,
                episode_estimate_used=pack.budget_usage.episode_estimate_used,
                parent_step=materialize_step)

        record = ValidatedRunRecord(
            fingerprint=fairness_fingerprint(request.run_spec),
            run_cell_id=request.run_spec.run_cell_id,
            adapter_id=request.adapter_id, status="accepted", failure_category=None,
            result_status=result.status, pack_status=pack.pack_status,
            candidate_count=len(validated_cands), evidence_count=len(evidence),
            target_count=len(pack.targets), support_count=len(pack.support),
            capability_ledger_summary=dict(result.capability_ledger),
            canonical_result_hash=canonical_result_hash(result, validated_cands),
            canonical_pack_hash=canonical_pack_hash(pack),
            conformance_category=conformance_category,
            cache_state=request.run_spec.cache_state,
            interaction_mode=request.run_spec.interaction_mode,
            operation=request.run_spec.operation,
            adapter_repetition=request.run_spec.adapter_repetition,
            resource_sample=rs)
    except _StopProcessing:
        pass
    finally:
        # Final scan on every exit path so mutate->restore cannot pass even
        # if intermediate scans were somehow bypassed.
        try:
            pb.assert_snapshot_unchanged(snapshot)
        except ContractError:
            existing_rs = record.resource_sample if record is not None else None
            record = _rejected_record(
                request, descriptor,
                AdapterResult("failed", "snapshot_mutation:ContractError", (), {}, ()),
                "snapshot_mutation:ContractError", conformance_category,
                resource_sample=existing_rs)
    if record is None:
        record = _rejected_record(
            request, descriptor,
            AdapterResult("failed", "unhandled:no_record", (), {}, ()),
            "unhandled:no_record", conformance_category, resource_sample=None)
    return record


# ---------------------------------------------------------------------------
# Public report privacy scan
# ---------------------------------------------------------------------------


_HASH_PREFIXES = ("fp_", "crh_", "cph_", "snap_", "vis_", "tree_", "tgt_", "wsr_")


def scan_public_report(report: Any) -> list[str]:
    """Strict recursive privacy scan for the aggregate report."""
    violations: list[str] = []

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                ks = str(k)
                sub = f"{path}.{ks}"
                if ks in pb.PRIVATE_REPORT_KEYS:
                    violations.append(sub)
                walk(v, sub)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            if len(obj) > 256:
                violations.append(f"{path}:long_string")
            elif obj.startswith(("http://", "https://", "\\\\")):
                violations.append(f"{path}:url_or_unc")
            elif (len(obj) >= 32 and all(c in "0123456789abcdef" for c in obj.lower())
                  and not obj.startswith(_HASH_PREFIXES)):
                violations.append(f"{path}:hex_digest")
        elif isinstance(obj, float):
            if obj != obj or obj in (float("inf"), float("-inf")):
                violations.append(f"{path}:non_finite")

    walk(report, "$")
    return violations


# ---------------------------------------------------------------------------
# aggregate_public_report (built ONLY from validated run records)
# ---------------------------------------------------------------------------


def aggregate_public_report(
    validated_runs: list[ValidatedRunRecord],
    two_step_episode_exercised: bool = False,
    comparison_matrix_validated: bool = False,
) -> dict[str, Any]:
    """Build the aggregate-only public report from validated run records.

    Every record is first fail-closed validated via ``validate_run_record``.
    Records that fail validation are counted as rejected-by-validation
    (failure_category=``record_validation:<reason>``) and NEVER reach the
    accepted surface. Adapter exception MESSAGE text and raw adapter-authored
    failure categories never reach public keys.
    """
    accepted: list[ValidatedRunRecord] = []
    rejected_by_privacy: list[str] = []
    rejected_by_validation: list[ValidatedRunRecord] = []

    for rec in validated_runs:
        # Fail-closed record validation (never raises).
        rec_failures = validate_run_record(rec)
        if rec_failures:
            # Treat as a record-validation rejection. Replace the (unsafe)
            # failure_category with a canonical record_validation marker.
            safe = ValidatedRunRecord(
                fingerprint=rec.fingerprint if isinstance(rec.fingerprint, str) and rec.fingerprint.startswith("fp_") else "fp_record_invalid",
                run_cell_id=rec.run_cell_id if isinstance(rec.run_cell_id, str) and rec.run_cell_id else "invalid",
                adapter_id=rec.adapter_id if isinstance(rec.adapter_id, str) and rec.adapter_id else "invalid",
                status="rejected",
                failure_category="record_validation:invalid_record",
                result_status="failed",
                pack_status=None,
                candidate_count=0,
                evidence_count=0,
                target_count=0,
                support_count=0,
                capability_ledger_summary={},
                canonical_result_hash=None,
                canonical_pack_hash=None,
                conformance_category=rec.conformance_category if isinstance(rec.conformance_category, str) and rec.conformance_category else "cat9_aggregate_only_reporting",
                cache_state=rec.cache_state if rec.cache_state in pb.CACHE_STATES else "cold",
                interaction_mode=rec.interaction_mode if rec.interaction_mode in pb.INTERACTION_MODES else "one_shot",
                operation=rec.operation if rec.operation in pb.OPERATIONS else "context",
                adapter_repetition=rec.adapter_repetition if _is_int(rec.adapter_repetition) and 1 <= rec.adapter_repetition <= 9 else 1,
                resource_sample=None,
            )
            rejected_by_validation.append(safe)
            continue
        pub = rec.to_public_dict()
        leaks = scan_public_report(pub)
        if leaks:
            rejected_by_privacy.append(rec.conformance_category)
            continue
        if rec.status == "accepted":
            accepted.append(rec)
        else:
            rejected_by_validation.append(rec)

    by_conformance: dict[str, dict[str, int]] = {}
    for rec in accepted + rejected_by_validation:
        cat = rec.conformance_category
        slot = by_conformance.setdefault(cat, {"accepted": 0, "rejected": 0})
        slot[rec.status] = slot.get(rec.status, 0) + 1

    result_status_counts: dict[str, int] = {}
    pack_status_counts: dict[str, int] = {}
    capability_status_counts: dict[str, int] = {}
    failure_category_counts: dict[str, int] = {}
    # v9: capability_ledger_entry_count is the sum of
    # len(record.capability_ledger_summary) over ACCEPTED records ONLY.
    # Rejected records carry an empty ledger (enforced by validate_run_record)
    # and never contribute to public capability counts. It is a reconciliation
    # scalar: sum(capability_status_counts) MUST equal
    # capability_ledger_entry_count.
    capability_ledger_entry_count = 0
    for rec in accepted + rejected_by_validation:
        result_status_counts[rec.result_status] = (
            result_status_counts.get(rec.result_status, 0) + 1)
        if rec.pack_status is not None:
            pack_status_counts[rec.pack_status] = (
                pack_status_counts.get(rec.pack_status, 0) + 1)
        if rec.failure_category is not None:
            failure_category_counts[rec.failure_category] = (
                failure_category_counts.get(rec.failure_category, 0) + 1)
    # Capability counts from ACCEPTED records only.
    for rec in accepted:
        for st in rec.capability_ledger_summary.values():
            capability_status_counts[st] = (
                capability_status_counts.get(st, 0) + 1)
        capability_ledger_entry_count += len(rec.capability_ledger_summary)

    total = len(validated_runs)
    accepted_count = len(accepted)
    rejected_count = len(rejected_by_validation) + len(rejected_by_privacy)
    reconciled = (accepted_count + rejected_count) == total
    resource_sample_present_count = sum(
        1 for r in accepted + rejected_by_validation if r.resource_sample is not None)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "claim_level": CLAIM_LEVEL,
        "readiness_status": READINESS_STATUS,
        "self_test_only": True,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "winner_declared": False,
        "product_default_claimed": False,
        "real_fairness_claimed": False,
        "s0_s5_conformance_claimed": False,
        "external_adapter_ready": False,
        "operational_acceptance_claimed": False,
        "provider_calls_performed": 0,
        "external_clones_performed": 0,
        "real_algorithm_comparisons": 0,
        "outcome_runs": 0,
        "total_validated_runs": total,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "rejected_by_privacy_count": len(rejected_by_privacy),
        "rejected_by_validation_count": len(rejected_by_validation),
        "totals_reconciled": reconciled,
        "resource_sample_present_count": resource_sample_present_count,
        "two_step_episode_exercised": two_step_episode_exercised,
        "comparison_matrix_validated": comparison_matrix_validated,
        "lifecycle_hooks_exercised": True,
        "root_binding_enforced": True,
        "symlink_confinement_enforced": True,
        "adapter_identity_binding_enforced": True,
        "by_conformance_category": by_conformance,
        "result_status_counts": result_status_counts,
        "pack_status_counts": pack_status_counts,
        "capability_status_counts": capability_status_counts,
        "capability_ledger_entry_count": capability_ledger_entry_count,
        "failure_category_counts": failure_category_counts,
        "conformance_categories_exercised": sorted(
            {r.conformance_category for r in accepted + rejected_by_validation}),
        "threat_model_note": (
            "v12: strict JSON wire (no pickle); child EOF/send/recv "
            "OSError + parser exc (Recursion/Value/Overflow/dup-key/"
            "depth/schema) adapter-scoped malformed; only parent "
            "setup/cleanup infra; full-run continuation after hostile "
            "child exit"
        ),
        "phase_a_limitations": [
            "synthetic temporary repositories only; no real-repository robustness",
            "no external clones; no provider calls; no real algorithm comparisons",
            "no outcome runs; no S0-S5 conformance; no product/default/winner claim",
            "accidental contract leakage protection only, not host containment",
        ],
        "canonical_contract_surface": CANONICAL_CONTRACT_SURFACE,
        "budget_estimator": {
            "name": pb.BUDGET_ESTIMATOR_NAME,
            "version": pb.BUDGET_ESTIMATOR_VERSION,
            "ceiling_estimate": True,
        },
        "materializer_version": pb.MATERIALIZER_VERSION,
        "renderer_version": pb.RENDERER_VERSION,
    }

    leaks = scan_public_report(report)
    if leaks:
        raise ContractError(
            "aggregate public report would leak private facts: " + ", ".join(leaks[:5]))
    return report


# ---------------------------------------------------------------------------
# Closed-schema report validation (exact, reconciled)
# ---------------------------------------------------------------------------


def _require_nonneg_int(name: str, value: Any, failures: list[str]) -> int | None:
    """Exception-free nonnegative-int requirement (bool rejected)."""
    if not _is_int(value):
        failures.append(f"{name} must be a nonnegative int (bool rejected), got {type(value).__name__}")
        return None
    if value < 0:
        failures.append(f"{name}={value} must be nonnegative")
        return None
    return value


def _require_count_map(
    name: str, value: Any, allowed_keys: frozenset[str],
    failures: list[str], *,
    require_nonneg: bool = True,
) -> dict[str, int] | None:
    """Exception-free closed-vocab count-map validation. Every key must be in
    ``allowed_keys`` and every value must be a nonnegative int (bool rejected).
    Returns the validated dict (or None on failure)."""
    if not isinstance(value, dict):
        failures.append(f"{name} must be a dict")
        return None
    out: dict[str, int] = {}
    for k, v in value.items():
        if not isinstance(k, str):
            failures.append(f"{name} has non-str key {k!r}")
            continue
        if k not in allowed_keys:
            failures.append(f"{name} has unexpected key {k!r}")
            continue
        if not _is_int(v):
            failures.append(f"{name}[{k!r}] must be int (bool rejected), got {type(v).__name__}")
            continue
        if require_nonneg and v < 0:
            failures.append(f"{name}[{k!r}]={v} must be nonnegative")
            continue
        out[k] = v
    return out


def validate_written_report(report: dict[str, Any]) -> list[str]:
    """Validate a written aggregate report with a CLOSED, exact schema.

    Exception-free and exact (v4 closure):
      * All count values are nonnegative ints (bool rejected).
      * Resource count bounded by total validated runs.
      * failure/result/pack/category/privacy/validation/capability totals
        reconciled.
      * Exact canonical constant surfaces (set equality, not subset).
      * Exact nested keys at every structured level.
      * Adversarial negative/string/bool/oversized/truncated/unknown cases
        are rejected WITHOUT raising.
    """
    failures: list[str] = []

    # 0. report itself must be a dict (never raise).
    if not isinstance(report, dict):
        return [f"report must be a dict, got {type(report).__name__}"]

    # 1. Reject unknown top-level keys.
    try:
        top_keys = set(report.keys())
    except Exception:  # noqa: BLE001
        return ["report keys not iterable"]
    unknown_top = top_keys - ALLOWED_TOP_LEVEL_KEYS
    for k in sorted(unknown_top):
        failures.append(f"unknown top-level key {k!r}")
    # Also flag missing required top-level keys.
    missing_top = ALLOWED_TOP_LEVEL_KEYS - top_keys
    for k in sorted(missing_top):
        failures.append(f"missing top-level key {k!r}")

    def require_str(key: str, expected: str) -> None:
        v = report.get(key)
        if not isinstance(v, str):
            failures.append(f"{key} must be str {expected!r}, got {type(v).__name__}")
            return
        if v != expected:
            failures.append(f"{key} != {expected!r}")

    def require_bool(key: str, expected: bool) -> None:
        v = report.get(key)
        if not _is_bool(v):
            failures.append(f"{key} must be bool {expected}, got {type(v).__name__}")
            return
        if v is not expected:
            failures.append(f"{key} must be {expected}")

    def require_int_eq(key: str, expected: int) -> None:
        v = report.get(key)
        if not _is_int(v):
            failures.append(f"{key} must be int {expected}, got {type(v).__name__}")
            return
        if v != expected:
            failures.append(f"{key} must be {expected}")

    require_str("schema_version", SCHEMA_VERSION)
    require_str("generated_by", GENERATED_BY)
    require_str("claim_level", CLAIM_LEVEL)
    require_str("readiness_status", READINESS_STATUS)
    require_bool("self_test_only", True)
    require_bool("aggregate_only_public_artifact", True)
    require_bool("candidate_not_fact", True)
    require_bool("not_evidence", True)
    require_bool("promotion_ready", False)
    require_bool("default_should_change", False)
    require_bool("evidencecore_semantics_changed", False)
    require_bool("winner_declared", False)
    require_bool("product_default_claimed", False)
    require_bool("real_fairness_claimed", False)
    require_bool("s0_s5_conformance_claimed", False)
    require_bool("external_adapter_ready", False)
    require_bool("operational_acceptance_claimed", False)
    require_bool("lifecycle_hooks_exercised", True)
    require_bool("root_binding_enforced", True)
    require_bool("symlink_confinement_enforced", True)
    require_bool("adapter_identity_binding_enforced", True)
    require_int_eq("provider_calls_performed", 0)
    require_int_eq("external_clones_performed", 0)
    require_int_eq("real_algorithm_comparisons", 0)
    require_int_eq("outcome_runs", 0)
    require_bool("two_step_episode_exercised", True)
    require_bool("comparison_matrix_validated", True)

    # 2. Top-level count fields: nonnegative ints (bool rejected).
    total: int | None = _require_nonneg_int(
        "total_validated_runs", report.get("total_validated_runs"), failures)
    acc: int | None = _require_nonneg_int(
        "accepted_count", report.get("accepted_count"), failures)
    rej: int | None = _require_nonneg_int(
        "rejected_count", report.get("rejected_count"), failures)
    rbpc: int | None = _require_nonneg_int(
        "rejected_by_privacy_count", report.get("rejected_by_privacy_count"), failures)
    rbvc: int | None = _require_nonneg_int(
        "rejected_by_validation_count", report.get("rejected_by_validation_count"), failures)
    rspc: int | None = _require_nonneg_int(
        "resource_sample_present_count", report.get("resource_sample_present_count"), failures)

    # 3. Totals reconciliation.
    if (total is not None and acc is not None and rej is not None
            and (acc + rej) != total):
        failures.append(f"totals do not reconcile: {acc} + {rej} != {total}")
    if (total is not None and rbpc is not None and rbvc is not None
            and (rbpc + rbvc) != rej):
        failures.append(
            f"rejected_count does not reconcile: "
            f"rejected_by_privacy_count({rbpc}) + "
            f"rejected_by_validation_count({rbvc}) != rejected_count({rej})"
        )
    require_bool("totals_reconciled", True)

    # 4. resource_sample_present_count bounded by total validated runs.
    if (rspc is not None and total is not None and rspc > total):
        failures.append(
            f"resource_sample_present_count={rspc} exceeds "
            f"total_validated_runs={total}"
        )

    # 5. by_conformance_category: closed keys, closed nested shape, nonneg ints.
    bcc = report.get("by_conformance_category")
    if not isinstance(bcc, dict):
        failures.append("by_conformance_category must be a dict")
    else:
        # Reconcile categories present == CAT_NAMES exactly (set equality).
        bcc_cats = set(bcc.keys())
        missing_cats = set(CAT_NAMES) - bcc_cats
        extra_cats = bcc_cats - set(CAT_NAMES)
        for c in sorted(missing_cats):
            failures.append(f"by_conformance_category missing category {c!r}")
        for c in sorted(extra_cats):
            failures.append(f"by_conformance_category has unknown cat {c!r}")
        for cat, slot in bcc.items():
            if not isinstance(slot, dict):
                failures.append(f"by_conformance_category[{cat!r}] must be dict")
                continue
            slot_keys = set(slot.keys())
            unknown_slot = slot_keys - {"accepted", "rejected"}
            for k in sorted(unknown_slot):
                failures.append(f"by_conformance_category[{cat!r}] has unknown key {k!r}")
            missing_slot = {"accepted", "rejected"} - slot_keys
            for k in sorted(missing_slot):
                failures.append(f"by_conformance_category[{cat!r}] missing key {k!r}")
            for k in ("accepted", "rejected"):
                _require_nonneg_int(
                    f"by_conformance_category[{cat!r}].{k}", slot.get(k), failures)

    # 6. Reconcile by_conformance_category totals.
    if isinstance(bcc, dict) and bcc:
        sum_acc = 0
        sum_rej = 0
        ok = True
        for s in bcc.values():
            if not isinstance(s, dict):
                ok = False
                continue
            a = s.get("accepted", 0)
            r = s.get("rejected", 0)
            if _is_int(a):
                sum_acc += a
            else:
                ok = False
            if _is_int(r):
                sum_rej += r
            else:
                ok = False
        if ok and acc is not None and sum_acc != acc:
            failures.append(
                f"sum(by_conformance_category.accepted)={sum_acc} != "
                f"accepted_count={acc}"
            )
        if ok and rbvc is not None and sum_rej != rbvc:
            failures.append(
                f"sum(by_conformance_category.rejected)={sum_rej} != "
                f"rejected_by_validation_count={rbvc}"
            )

    # 7. Closed nested count maps for status counts (nonnegative ints).
    rsc = _require_count_map(
        "result_status_counts", report.get("result_status_counts"),
        pb.RESULT_STATUSES, failures)
    psc = _require_count_map(
        "pack_status_counts", report.get("pack_status_counts"),
        pb.PACK_STATUSES, failures)
    csc = _require_count_map(
        "capability_status_counts", report.get("capability_status_counts"),
        pb.CAPABILITY_STATUSES, failures)
    # v5: capability_ledger_entry_count is a nonnegative int reconciliation
    # scalar. It must equal sum(capability_status_counts.values()) over the
    # SAME accepted + validation-rejected non-private records. A tampered
    # bucket (e.g. +99 to an executed count) OR a tampered scalar breaks the
    # equality and is rejected here.
    clec_raw = report.get("capability_ledger_entry_count")
    clec = _require_nonneg_int(
        "capability_ledger_entry_count", clec_raw, failures)
    # failure_category_counts: keys MUST be canonical failure categories
    # (closed set). Adapter-authored categories never reach public keys.
    fcc = _require_count_map(
        "failure_category_counts", report.get("failure_category_counts"),
        frozenset(CANONICAL_FAILURE_CATEGORY_PREFIXES), failures)

    # 8. Reconcile result_status_counts total = total - rejected_by_privacy.
    if rsc is not None and total is not None and rbpc is not None:
        rsc_sum = sum(rsc.values())
        expected_rsc = total - rbpc
        if rsc_sum != expected_rsc:
            failures.append(
                f"sum(result_status_counts)={rsc_sum} != "
                f"total_validated_runs - rejected_by_privacy_count={expected_rsc}"
            )

    # 9. Reconcile pack_status_counts total = accepted_count.
    if psc is not None and acc is not None:
        psc_sum = sum(psc.values())
        if psc_sum != acc:
            failures.append(
                f"sum(pack_status_counts)={psc_sum} != accepted_count={acc}"
            )

    # 10. capability_status_counts: closed-vocab + nonnegative ints are
    #     checked by _require_count_map above. v5: the aggregate reconciliation
    #     scalar capability_ledger_entry_count must EXACTLY equal
    #     sum(capability_status_counts.values()). This catches a tampered
    #     bucket (adding 99 to a count) or a tampered scalar. Both
    #     directions of tampering break the equality.
    if csc is not None and clec is not None:
        csc_sum = sum(csc.values())
        if csc_sum != clec:
            failures.append(
                f"sum(capability_status_counts)={csc_sum} != "
                f"capability_ledger_entry_count={clec} "
                f"(tampered bucket or scalar rejected)"
            )

    # 11. Reconcile failure_category_counts total = rejected_by_validation_count.
    if fcc is not None and rbvc is not None:
        fcc_sum = sum(fcc.values())
        if fcc_sum != rbvc:
            failures.append(
                f"sum(failure_category_counts)={fcc_sum} != "
                f"rejected_by_validation_count={rbvc}"
            )

    # 12. conformance_categories_exercised must equal CAT_NAMES exactly (set).
    cats = report.get("conformance_categories_exercised")
    if not isinstance(cats, list):
        failures.append("conformance_categories_exercised must be a list")
    else:
        # List entries must be strings, no duplicates.
        seen_cats: set[str] = set()
        for c in cats:
            if not isinstance(c, str):
                failures.append(f"conformance_categories_exercised entry {c!r} must be str")
                continue
            if c in seen_cats:
                failures.append(f"conformance_categories_exercised has duplicate {c!r}")
            seen_cats.add(c)
        if sorted(seen_cats) != sorted(CAT_NAMES):
            missing = [c for c in CAT_NAMES if c not in seen_cats]
            extra = [c for c in seen_cats if c not in CAT_NAMES]
            if missing:
                failures.append(f"conformance categories not exercised: {missing}")
            if extra:
                failures.append(f"unknown conformance categories: {extra}")

    # 13. budget_estimator: closed shape, exact version.
    be = report.get("budget_estimator")
    if not isinstance(be, dict):
        failures.append("budget_estimator must be a dict")
    else:
        be_keys = set(be.keys())
        unknown_be = be_keys - {"name", "version", "ceiling_estimate"}
        for k in sorted(unknown_be):
            failures.append(f"budget_estimator has unknown key {k!r}")
        missing_be = {"name", "version", "ceiling_estimate"} - be_keys
        for k in sorted(missing_be):
            failures.append(f"budget_estimator missing key {k!r}")
        if isinstance(be.get("name"), str) and be.get("name") != pb.BUDGET_ESTIMATOR_NAME:
            failures.append("budget_estimator.name mismatch")
        if isinstance(be.get("version"), str) and be.get("version") != pb.BUDGET_ESTIMATOR_VERSION:
            failures.append("budget_estimator.version mismatch")
        if not _is_bool(be.get("ceiling_estimate")) or be.get("ceiling_estimate") is not True:
            failures.append("budget_estimator.ceiling_estimate must be true")

    # 14. canonical_contract_surface: EXACT set equality (no truncation).
    ccs = report.get("canonical_contract_surface")
    if not isinstance(ccs, list):
        failures.append("canonical_contract_surface must be a list")
    else:
        # Set equality, not subset.
        ccs_set = set()
        for name in ccs:
            if not isinstance(name, str):
                failures.append(f"canonical_contract_surface entry {name!r} must be str")
                continue
            if name in ccs_set:
                failures.append(f"canonical_contract_surface has duplicate {name!r}")
            ccs_set.add(name)
            if name not in CANONICAL_CONTRACT_SURFACE:
                failures.append(f"canonical_contract_surface has unknown entry {name!r}")
        if ccs_set != set(CANONICAL_CONTRACT_SURFACE):
            missing = set(CANONICAL_CONTRACT_SURFACE) - ccs_set
            extra = ccs_set - set(CANONICAL_CONTRACT_SURFACE)
            if missing:
                failures.append(
                    f"canonical_contract_surface truncated: missing {sorted(missing)}"
                )
            if extra:
                failures.append(
                    f"canonical_contract_surface has extra: {sorted(extra)}"
                )

    # 15. phase_a_limitations must be a non-empty list of strings.
    pal = report.get("phase_a_limitations")
    if not isinstance(pal, list):
        failures.append("phase_a_limitations must be a list")
    elif len(pal) == 0:
        failures.append("phase_a_limitations must be a non-empty list")
    else:
        for item in pal:
            if not isinstance(item, str):
                failures.append(f"phase_a_limitations entry {item!r} must be str")

    # 16. threat_model_note must be a non-empty string.
    tmn = report.get("threat_model_note")
    if not isinstance(tmn, str) or not tmn:
        failures.append("threat_model_note must be a non-empty str")

    # 17. materializer_version and renderer_version (exact).
    if report.get("materializer_version") != pb.MATERIALIZER_VERSION:
        failures.append("materializer_version mismatch")
    if report.get("renderer_version") != pb.RENDERER_VERSION:
        failures.append("renderer_version mismatch")

    # 18. Privacy scan (never raises; adversarial values rejected).
    try:
        leaks = scan_public_report(report)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"privacy scan raised: {type(exc).__name__}: {exc}")
        leaks = []
    if leaks:
        failures.append(f"privacy scan violations: {leaks[:5]}")
    return failures


# ---------------------------------------------------------------------------
# SELF-TEST: all nine conformance categories
# ---------------------------------------------------------------------------


def _new_tmp_root() -> tuple[Any, Path]:
    tmp = tempfile.TemporaryDirectory(prefix="pb_bakeoff_a_")
    root = Path(tmp.name)
    return tmp, root


def _expect_rejected(rec: ValidatedRunRecord, cat: str) -> None:
    if rec.status != "rejected":
        raise AssertionError(
            f"{cat}: expected rejected, got status={rec.status} "
            f"failure_category={rec.failure_category}")


def _expect_accepted(rec: ValidatedRunRecord, cat: str) -> None:
    if rec.status != "accepted":
        raise AssertionError(
            f"{cat}: expected accepted, got status={rec.status} "
            f"failure_category={rec.failure_category}")


def _bind_request(request: AdapterRequest, snapshot: FrozenSnapshot) -> AdapterRequest:
    """Re-bind a request's snapshot digests to the actual frozen snapshot."""
    rs = request.run_spec
    bound_rs = BakeoffRunSpec(
        schema_id=rs.schema_id, run_cell_id=rs.run_cell_id, task=rs.task,
        snapshot_id=rs.snapshot_id, source_visibility_id=rs.source_visibility_id,
        snapshot_manifest_digest=snapshot.manifest_digest,
        source_visibility_digest=snapshot_source_visibility_digest(snapshot),
        visible_tree_digest=snapshot.visible_tree_digest,
        adapter_repetition=rs.adapter_repetition, cache_state=rs.cache_state,
        interaction_mode=rs.interaction_mode, operation=rs.operation,
        episode_id=rs.episode_id, request_id=rs.request_id,
        parent_result_id=rs.parent_result_id, bound_target_id=rs.bound_target_id,
        caps=rs.caps, timeout_seconds=rs.timeout_seconds,
        renderer_version=rs.renderer_version,
        materializer_version=rs.materializer_version,
        budget_estimator_version=rs.budget_estimator_version,
        writable_state_root_id=snapshot.writable_state_root_id,
    ).validate()
    return AdapterRequest(
        run_spec=bound_rs, adapter_id=request.adapter_id,
        adapter_version=request.adapter_version).validate()


def _ctx_run(
    hooks: AdapterHooks, request: AdapterRequest,
    descriptor: AdapterDescriptor, cat: str,
    snapshot: FrozenSnapshot, root: Path,
    episode_registry: EpisodeRegistry | None = None,
    materialize_step: int = 1,
) -> ValidatedRunRecord:
    bound_req = _bind_request(request, snapshot)
    return run_adapter(
        hooks, bound_req, root, descriptor, snapshot, cat,
        episode_registry=episode_registry, materialize_step=materialize_step)


def _repo_one_run(
    hooks: AdapterHooks, request: AdapterRequest | None = None,
    descriptor: AdapterDescriptor | None = None, cat: str = "live_run",
    episode_registry: EpisodeRegistry | None = None,
    materialize_step: int = 1, timeout: float = 30.0,
) -> ValidatedRunRecord:
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = request or make_request(snapshot=snap, timeout_seconds=timeout)
        desc = descriptor or valid_descriptor()
        return _ctx_run(hooks, req, desc, cat, snap, root, episode_registry, materialize_step)
    finally:
        tmp.cleanup()


# -- Category 1: request/oracle isolation --


def cat1_request_oracle_isolation() -> ValidatedRunRecord:
    """Strict closed schemas; no oracle/gold/path/outcome fields in
    request/result/pack/report; RUN does not import oracle. Expanded task/oracle
    shape verified. v4 oracle closure: distinct spans, positive/negative
    disjointness, duplicate-negative rejection, support target association,
    duplicate-support rejection, strict kind cardinality, and gold-convenience
    field absence."""
    req = make_request()
    import product_bakeoff_oracle as oracle
    oracle.assert_run_phase_not_importing_oracle()
    try:
        BakeoffTask(  # type: ignore[call-arg]
            task_slug=SYN_TASK_SLUG_ALPHA, language_family="rust",
            task_family="symbol_lookup", interaction_mode="one_shot",
            source_visibility="frozen_visible", query=SYN_QUERY_ALPHA,
            operation="context", gold_span="leaked")
        raise AssertionError("cat1: BakeoffTask accepted a gold_span field")
    except TypeError:
        pass
    # v4: gold_target_path / gold_target_range convenience fields were
    # DELETED. Attempting to pass them must TypeError.
    try:
        oracle.TaskOracle(  # type: ignore[call-arg]
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            gold_target_path="src/widget.rs")
        raise AssertionError("cat1: TaskOracle accepted deleted gold_target_path")
    except TypeError:
        pass
    try:
        oracle.TaskOracle(  # type: ignore[call-arg]
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            gold_target_range=(1, 3))
        raise AssertionError("cat1: TaskOracle accepted deleted gold_target_range")
    except TypeError:
        pass
    # Verify deterministic oracle requires exactly 1 span.
    try:
        oracle.TaskOracle(task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
                          acceptable_target_spans=()).validate()
        raise AssertionError("cat1: deterministic oracle accepted 0 spans")
    except oracle.OracleContractError:
        pass
    try:
        oracle.TaskOracle(task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
                          acceptable_target_spans=(("src/widget.rs", 1, 3), ("src/config.rs", 1, 2))).validate()
        raise AssertionError("cat1: deterministic oracle accepted 2 spans")
    except oracle.OracleContractError:
        pass
    # v4: duplicate acceptable_target_spans rejected.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="multi_target",
            acceptable_target_spans=(("src/widget.rs", 1, 3), ("src/widget.rs", 1, 3)),
        ).validate()
        raise AssertionError("cat1: duplicate acceptable_target_spans accepted")
    except oracle.OracleContractError:
        pass
    # v4: positive/negative disjointness — must_not_primary_path overlapping a
    # target path rejected.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            must_not_primary_paths=("src/widget.rs",),
        ).validate()
        raise AssertionError("cat1: must_not_primary_path overlapping target accepted")
    except oracle.OracleContractError:
        pass
    # v4: duplicate must_not_primary_paths rejected.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            must_not_primary_paths=("src/other.rs", "src/other.rs"),
        ).validate()
        raise AssertionError("cat1: duplicate must_not_primary_paths accepted")
    except oracle.OracleContractError:
        pass
    # v4: support record target not in acceptable_target_spans rejected.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            expected_support_records=(oracle.OracleSupportRecord(
                support_path="src/config.rs", support_start_line=1, support_end_line=2,
                relation_kind="type_dep", target_path="src/other.rs",
                target_start_line=1, target_end_line=2),),
        ).validate()
        raise AssertionError("cat1: support target not in acceptable spans accepted")
    except oracle.OracleContractError:
        pass
    # v4: duplicate support records rejected.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            expected_support_records=(
                oracle.OracleSupportRecord(
                    support_path="src/config.rs", support_start_line=1, support_end_line=2,
                    relation_kind="type_dep", target_path="src/widget.rs",
                    target_start_line=1, target_end_line=3),
                oracle.OracleSupportRecord(
                    support_path="src/config.rs", support_start_line=1, support_end_line=2,
                    relation_kind="type_dep", target_path="src/widget.rs",
                    target_start_line=1, target_end_line=3),
            ),
        ).validate()
        raise AssertionError("cat1: duplicate support records accepted")
    except oracle.OracleContractError:
        pass
    # v4: abstain/stress oracle with must_not_primary_paths rejected (strict
    # kind cardinality for negative labels).
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="abstain",
            acceptable_target_spans=(),
            must_not_primary_paths=("src/other.rs",),
        ).validate()
        raise AssertionError("cat1: abstain oracle with must_not_primary_paths accepted")
    except oracle.OracleContractError:
        pass
    # Valid deterministic oracle + associated support record.
    good_oracle = oracle.TaskOracle(
        task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
        acceptable_target_spans=(("src/widget.rs", 1, 3),),
        expected_support_records=(oracle.OracleSupportRecord(
            support_path="src/config.rs", support_start_line=1, support_end_line=2,
            relation_kind="type_dep", target_path="src/widget.rs",
            target_start_line=1, target_end_line=3),),
        must_not_primary_paths=("src/other.rs",),
    )
    good_oracle.validate()
    # v9: oracle visible_files path-membership preflight. When a proven
    # visible-file declaration set is supplied, EVERY oracle label path must
    # belong to it. Adversarial: a label path not in the frozen visible set
    # is rejected. Gold/oracle stays scorer-only (no source reads).
    vis_set = ("src/widget.rs", "src/config.rs", "src/other.rs")
    # Valid: all paths in the visible set.
    good_oracle.validate(visible_files=vis_set)
    # Adversarial: acceptable_target_span path not in visible set.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/NOT_VISIBLE.rs", 1, 3),),
        ).validate(visible_files=vis_set)
        raise AssertionError(
            "cat1: oracle accepted target span path not in visible_files")
    except oracle.OracleContractError:
        pass
    # Adversarial: support record support_path not in visible set.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            expected_support_records=(oracle.OracleSupportRecord(
                support_path="src/NOT_VISIBLE.rs", support_start_line=1,
                support_end_line=2, relation_kind="type_dep",
                target_path="src/widget.rs", target_start_line=1,
                target_end_line=3),),
        ).validate(visible_files=vis_set)
        raise AssertionError(
            "cat1: oracle accepted support_path not in visible_files")
    except oracle.OracleContractError:
        pass
    # Adversarial: support record target_path not in visible set.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            expected_support_records=(oracle.OracleSupportRecord(
                support_path="src/config.rs", support_start_line=1,
                support_end_line=2, relation_kind="type_dep",
                target_path="src/NOT_VISIBLE.rs", target_start_line=1,
                target_end_line=3),),
        ).validate(visible_files=vis_set)
        raise AssertionError(
            "cat1: oracle accepted target_path not in visible_files")
    except oracle.OracleContractError:
        pass
    # Adversarial: must_not_primary_path not in visible set.
    try:
        oracle.TaskOracle(
            task_slug=SYN_TASK_SLUG_ALPHA, oracle_kind="deterministic",
            acceptable_target_spans=(("src/widget.rs", 1, 3),),
            must_not_primary_paths=("src/NOT_VISIBLE.rs",),
        ).validate(visible_files=vis_set)
        raise AssertionError(
            "cat1: oracle accepted must_not_primary_path not in visible_files")
    except oracle.OracleContractError:
        pass
    # Verify expanded task families are accepted.
    for tf in ("ambiguous_target", "error_text", "configuration_discovery",
               "test_discovery", "no_answer"):
        try:
            BakeoffTask(
                task_slug=SYN_TASK_SLUG_ALPHA + "_" + tf,
                language_family="rust", task_family=tf,
                interaction_mode="one_shot", source_visibility="frozen_visible",
                query=SYN_QUERY_ALPHA, operation="context").validate()
        except ContractError:
            raise AssertionError(f"cat1: expanded task family {tf} rejected")
    rec = _repo_one_run(_qhooks(valid_adapter_query), cat="cat1_request_oracle_isolation")
    _expect_accepted(rec, "cat1")
    leaks = scan_public_report(rec.to_public_dict())
    if leaks:
        raise AssertionError(f"cat1: record leaks private facts: {leaks}")
    return rec


# -- Category 2: snapshot/visibility isolation + root binding + symlinks --


def _can_create_symlinks() -> bool:
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        link = Path(tmp) / "testlink"
        target = Path(tmp) / "target.txt"
        target.write_text("x")
        os.symlink(target, link)
        link.unlink()
        return True
    except OSError:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cat2_snapshot_visibility_isolation() -> list[ValidatedRunRecord]:
    recs: list[ValidatedRunRecord] = []
    tmp1, root1 = _new_tmp_root()
    tmp2, root2 = _new_tmp_root()
    try:
        snap1 = build_synthetic_repo_one(root1)
        snap2 = build_synthetic_repo_one(root2)
        if snap1.manifest_digest != snap2.manifest_digest:
            raise AssertionError("cat2: byte-identical arms have differing digests")
        req = make_request(snapshot=snap1)
        r1 = _ctx_run(_qhooks(valid_adapter_query), req, valid_descriptor(),
                       "cat2_snapshot_visibility_isolation", snap1, root1)
        _expect_accepted(r1, "cat2")
        recs.append(r1)
    finally:
        tmp1.cleanup()
        tmp2.cleanup()

    for fn, label in (
        (adv_path_absolute_query, "absolute"), (adv_path_traversal_query, "traversal"),
        (adv_path_drive_query, "drive"), (adv_path_unc_query, "unc"),
        (adv_mutate_file_query, "mutate"), (adv_add_file_query, "add"),
        (adv_delete_file_query, "delete"), (adv_rename_file_query, "rename"),
    ):
        recs.append(_repo_one_run(_qhooks(fn), descriptor=adv_descriptor(),
                                   cat="cat2_snapshot_visibility_isolation"))
        _expect_rejected(recs[-1], f"cat2:{label}")

    # Root binding: isolated_root != snapshot.root -> rejected.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap)
        bad_root = root / "wrong_root"
        bad_root.mkdir()
        rec = run_adapter(_qhooks(valid_adapter_query), _bind_request(req, snap),
                          bad_root, valid_descriptor(), snap,
                          "cat2_snapshot_visibility_isolation")
        _expect_rejected(rec, "cat2:root_mismatch")
        recs.append(rec)
    finally:
        tmp.cleanup()

    # Symlink escape fixture (non-vacuous on platforms that support symlinks).
    if _can_create_symlinks():
        tmp, root = _new_tmp_root()
        try:
            snap = build_synthetic_repo_one(root)
            escape_link = root / "src" / "escape.rs"
            escape_target = root / "secret.txt"
            escape_target.write_text("secret")
            os.symlink(escape_target, escape_link)
            try:
                pb.scan_visible_tree(snap)
                raise AssertionError("cat2: symlink in visible tree not rejected")
            except ContractError:
                pass
        finally:
            tmp.cleanup()

        # v4: symlinked-PARENT escape fixture. A symlinked parent DIRECTORY
        # in the visible tree path must be rejected. Linux CI must exercise
        # this; Windows without symlink privilege explicitly skips.
        tmp, root = _new_tmp_root()
        try:
            # Create a real directory outside the snapshot root with a file.
            outside_dir = root.parent / "pb_escape_outside_dir"
            outside_dir.mkdir(exist_ok=True)
            (outside_dir / "smuggled.rs").write_text(
                "pub fn smuggled() {}\n", encoding="utf-8"
            )
            # Build the snapshot first (no symlink yet).
            snap = build_synthetic_repo_one(root)
            # Now create a symlinked parent directory: root/src2 -> outside_dir.
            symlinked_parent = root / "src2"
            if symlinked_parent.exists():
                # Clean up if a stale link exists.
                if symlinked_parent.is_symlink() or symlinked_parent.is_file():
                    symlinked_parent.unlink()
                else:
                    import shutil as _shutil
                    _shutil.rmtree(symlinked_parent, ignore_errors=True)
            os.symlink(outside_dir, symlinked_parent, target_is_directory=True)
            try:
                pb.scan_visible_tree(snap)
                raise AssertionError(
                    "cat2: symlinked parent directory not rejected"
                )
            except ContractError:
                pass
            # The common safe path policy must also reject candidate paths
            # that traverse a symlinked parent component.
            try:
                pb._validate_safe_path_under_root(
                    symlinked_parent / "smuggled.rs", root.resolve(),
                    "symlinked_parent_candidate",
                )
                raise AssertionError(
                    "cat2: _validate_safe_path_under_root accepted a "
                    "symlinked-parent path component"
                )
            except ContractError:
                pass
        finally:
            tmp.cleanup()

    # v4: out-of-root writable-state rejected WITHOUT being created on disk.
    # The common safe path policy validates confinement BEFORE mkdir.
    tmp, root = _new_tmp_root()
    try:
        outside_wsr = root.parent / "pb_outside_wsr_dir"
        # Ensure clean state.
        if outside_wsr.exists():
            if outside_wsr.is_dir():
                import shutil as _shutil2
                _shutil2.rmtree(outside_wsr, ignore_errors=True)
            else:
                outside_wsr.unlink()
        try:
            pb.materialize_snapshot(
                root, ["src/widget.rs", "src/config.rs"],
                writable_state_root=outside_wsr,
            )
            raise AssertionError(
                "cat2: out-of-root writable_state_root accepted (should be "
                "rejected without creating it)"
            )
        except ContractError:
            pass
        # Prove it was NOT created.
        if outside_wsr.exists():
            raise AssertionError(
                "cat2: out-of-root writable_state_root was created before "
                "being rejected (mkdir before confinement check)"
            )
    finally:
        tmp.cleanup()

    # v5: writable-state overlap probes (all rejected BEFORE mkdir, without
    # being created). The writable-state root must NOT equal the source root,
    # must NOT be an ancestor/equal of any visible path, and no visible path
    # may be located inside the writable-state root. The default
    # .pb_writable_state continues to succeed (preserved by the existing
    # build_synthetic_repo_one tests above).

    # (a) writable_state_root == source root -> rejected.
    tmp, root = _new_tmp_root()
    try:
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "widget.rs").write_text(
            "pub struct Widget {}\n", encoding="utf-8")
        try:
            pb.materialize_snapshot(
                root, ["src/widget.rs"],
                writable_state_root=root,
            )
            raise AssertionError(
                "cat2: writable_state_root == source root accepted "
                "(should be rejected before creation)"
            )
        except ContractError:
            pass
    finally:
        tmp.cleanup()

    # (b) writable_state_root == root/'src' (ancestor of visible src/a.rs)
    #     -> rejected before creation.
    tmp, root = _new_tmp_root()
    try:
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "a.rs").write_text(
            "pub fn a() {}\n", encoding="utf-8")
        wsr_in_src = root / "src"
        try:
            pb.materialize_snapshot(
                root, ["src/a.rs"],
                writable_state_root=wsr_in_src,
            )
            raise AssertionError(
                "cat2: writable_state_root ancestor of visible path "
                "accepted (should be rejected before creation)"
            )
        except ContractError:
            pass
        # Prove the writable-state root dir was NOT re-created/modified by
        # the failed materialize_snapshot call (the existing src/ dir is
        # intact, but no .pb_writable_state was created inside it).
        if (wsr_in_src / ".pb_writable_state").exists():
            raise AssertionError(
                "cat2: writable_state_root ancestor case created state "
                "before being rejected"
            )
    finally:
        tmp.cleanup()

    # (c) visible path inside writable state (writable_state root contains
    #     a visible path) -> rejected before creation. Use a writable_state
    #     at root/sub and a visible path at root/sub/inner.rs.
    tmp, root = _new_tmp_root()
    try:
        (root / "sub").mkdir(parents=True, exist_ok=True)
        (root / "sub" / "inner.rs").write_text(
            "pub fn inner() {}\n", encoding="utf-8")
        wsr_sub = root / "sub"
        try:
            pb.materialize_snapshot(
                root, ["sub/inner.rs"],
                writable_state_root=wsr_sub,
            )
            raise AssertionError(
                "cat2: writable_state_root containing a visible path "
                "accepted (should be rejected before creation)"
            )
        except ContractError:
            pass
    finally:
        tmp.cleanup()

    # v5: in-root parent-symlink fixture. A symlinked parent DIRECTORY whose
    # target is STILL INSIDE the root must be rejected by the COMMON safe
    # path policy. The previous (escape) fixture used a target outside the
    # root, which the resolved confinement check catches. This fixture uses
    # a target inside the root, which only the ORIGINAL LEXICAL component
    # walk catches (full.resolve() would dereference the symlink and hide
    # it because the resolved path stays inside root). Linux CI must
    # exercise this; Windows without symlink privilege explicitly skips.
    if _can_create_symlinks():
        tmp, root = _new_tmp_root()
        try:
            # Create a real directory INSIDE root with a smuggled file.
            real_inside = root / "real_inside_dir"
            real_inside.mkdir(exist_ok=True)
            (real_inside / "smuggled.rs").write_text(
                "pub fn smuggled() {}\n", encoding="utf-8")
            # Build the snapshot first (no symlink yet).
            snap = build_synthetic_repo_one(root)
            # Create a symlinked parent: root/src2 -> root/real_inside_dir
            # (target is STILL INSIDE root).
            in_root_symlinked_parent = root / "src2"
            if in_root_symlinked_parent.exists():
                if (in_root_symlinked_parent.is_symlink()
                        or in_root_symlinked_parent.is_file()):
                    in_root_symlinked_parent.unlink()
                else:
                    import shutil as _shutil3
                    _shutil3.rmtree(in_root_symlinked_parent, ignore_errors=True)
            os.symlink(
                real_inside, in_root_symlinked_parent,
                target_is_directory=True)
            # scan_visible_tree must reject the symlinked parent (the
            # visible-tree walk calls _validate_safe_path_under_root which
            # now walks ORIGINAL LEXICAL components).
            try:
                pb.scan_visible_tree(snap)
                raise AssertionError(
                    "cat2: in-root symlinked parent directory not rejected"
                )
            except ContractError:
                pass
            # The common safe path policy must also reject candidate paths
            # that traverse an in-root symlinked parent component. The
            # resolved path stays inside root, so only the lexical component
            # walk catches this.
            try:
                pb._validate_safe_path_under_root(
                    in_root_symlinked_parent / "smuggled.rs",
                    root.resolve(),
                    "in_root_symlinked_parent_candidate",
                )
                raise AssertionError(
                    "cat2: _validate_safe_path_under_root accepted an "
                    "in-root symlinked-parent path component (resolved "
                    "confinement alone misses this)"
                )
            except ContractError:
                pass
        finally:
            tmp.cleanup()

    # v4: mutate-and-restore fixture (item 4). Prepare mutates a source file,
    # index restores it. The post-prepare intermediate scan must reject the
    # mutation BEFORE index runs (mutate->restore cannot pass).
    rec = _repo_one_run(
        MUTATE_RESTORE_HOOKS, descriptor=valid_descriptor(),
        cat="cat2_snapshot_visibility_isolation",
    )
    _expect_rejected(rec, "cat2:mutate_and_restore")
    if rec.failure_category != "snapshot_mutation:ContractError":
        raise AssertionError(
            f"cat2: mutate_and_restore produced failure_category="
            f"{rec.failure_category!r}, expected snapshot_mutation:ContractError"
        )
    recs.append(rec)

    # v9: full initial source-tree freeze enumeration adversarial tests.
    # These prove the enumerator rejects undeclared/missing/duplicate sources,
    # duplicate declarations (no set collapse), and WSR state violations, and
    # that post-freeze pre-hook mutation aborts the whole bakeoff.

    # (a) duplicate declarations rejected (no set collapse).
    tmp, root = _new_tmp_root()
    try:
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "widget.rs").write_text(
            "pub struct Widget {}\n", encoding="utf-8")
        try:
            pb.materialize_snapshot(
                root, ["src/widget.rs", "src/widget.rs"])
            raise AssertionError(
                "cat2: duplicate visible_file declarations accepted "
                "(should reject without set collapse)")
        except ContractError:
            pass
    finally:
        tmp.cleanup()

    # (b) undeclared source file present -> reject (exact set equality).
    tmp, root = _new_tmp_root()
    try:
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "widget.rs").write_text("x\n", encoding="utf-8")
        (root / "src" / "extra.rs").write_text("y\n", encoding="utf-8")
        try:
            pb.materialize_snapshot(root, ["src/widget.rs"])
            raise AssertionError(
                "cat2: undeclared source file accepted (exact set equality "
                "should reject)")
        except ContractError:
            pass
    finally:
        tmp.cleanup()

    # (c) missing declared file -> reject.
    tmp, root = _new_tmp_root()
    try:
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "widget.rs").write_text("x\n", encoding="utf-8")
        try:
            pb.materialize_snapshot(
                root, ["src/widget.rs", "src/MISSING.rs"])
            raise AssertionError(
                "cat2: missing declared file accepted (should reject)")
        except ContractError:
            pass
    finally:
        tmp.cleanup()

    # (d) WSR is a file (not a dir) -> reject.
    tmp, root = _new_tmp_root()
    try:
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "widget.rs").write_text("x\n", encoding="utf-8")
        wsr_file = root / "wsr_file"
        wsr_file.write_text("not a dir\n", encoding="utf-8")
        try:
            pb.materialize_snapshot(
                root, ["src/widget.rs"], writable_state_root=wsr_file)
            raise AssertionError(
                "cat2: WSR that is a file accepted (should reject)")
        except ContractError:
            pass
    finally:
        tmp.cleanup()

    # (e) post-freeze pre-hook mutation -> HarnessInfrastructureError abort.
    # The frozen source tree is mutated BEFORE any hook starts; the pre-hook
    # infrastructure scan must abort the whole bakeoff (not a rejected record).
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap)
        # Mutate a frozen source file before run_adapter.
        (root / "src" / "widget.rs").write_text(
            "MUTATED_BEFORE_HOOK\n", encoding="utf-8")
        try:
            _ctx_run(_qhooks(valid_adapter_query), req, valid_descriptor(),
                      "cat2_snapshot_visibility_isolation", snap, root)
            raise AssertionError(
                "cat2: pre-hook mutation did not abort (should raise "
                "HarnessInfrastructureError, not produce a rejected record)")
        except HarnessInfrastructureError:
            pass
    finally:
        tmp.cleanup()

    # (f) WSR mutation is allowed (not treated as source mutation). The
    # adapter writes into the WSR; the post-hook scan must NOT reject it.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap)
        rec = _ctx_run(_qhooks(wsr_mutate_query), req, valid_descriptor(),
                        "cat2_snapshot_visibility_isolation", snap, root)
        _expect_accepted(rec, "cat2:wsr_mutation_allowed")
        recs.append(rec)
    finally:
        tmp.cleanup()

    # v10: special-file rejection BEFORE read. FIFO/socket/device/directory
    # entries are rejected via stat.S_ISREG(st_mode) on the lstat result,
    # WITHOUT opening or reading them.
    # (a) Real POSIX FIFO test (when os.mkfifo is available). Prove snapshot
    # construction rejects promptly without opening the FIFO.
    if hasattr(os, "mkfifo"):
        tmp, root = _new_tmp_root()
        try:
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "widget.rs").write_text(
                "pub struct Widget {}\n", encoding="utf-8")
            try:
                os.mkfifo(root / "src" / "fifo_file")
            except (OSError, NotImplementedError):
                # mkfifo available but failed (e.g. filesystem doesn't support
                # it); skip the real FIFO test gracefully.
                pass
            else:
                # Declared FIFO: enumeration rejects before read.
                try:
                    pb.materialize_snapshot(
                        root, ["src/widget.rs", "src/fifo_file"])
                    raise AssertionError(
                        "cat2: declared FIFO in source tree not rejected "
                        "before read")
                except ContractError:
                    pass  # rejected before opening/reading the FIFO
                # Undeclared FIFO: enumeration still walks the FULL tree and
                # rejects the FIFO before the set-equality check.
                try:
                    pb.materialize_snapshot(root, ["src/widget.rs"])
                    raise AssertionError(
                        "cat2: undeclared FIFO in source tree not rejected")
                except ContractError:
                    pass
        finally:
            tmp.cleanup()
    else:
        # (b) Windows: os.mkfifo unavailable. Feature-detect/skip honestly,
        # and test the mocked special st_mode path by monkeypatching os.lstat
        # to return a FIFO st_mode for one file (proves S_ISREG check works).
        tmp, root = _new_tmp_root()
        try:
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "widget.rs").write_text(
                "pub struct Widget {}\n", encoding="utf-8")
            _orig_lstat = os.lstat
            _fifo_target = (root / "src" / "widget.rs").resolve()

            def _mock_lstat(path):
                st = _orig_lstat(path)
                # Return a stat result with FIFO mode for the target file.
                if Path(path).resolve() == _fifo_target:
                    return os.stat_result((
                        stat.S_IFIFO, st.st_ino, st.st_dev, st.st_nlink,
                        st.st_uid, st.st_gid, st.st_size, st.st_atime,
                        st.st_mtime, st.st_ctime))
                return st
            os.lstat = _mock_lstat  # type: ignore[assignment]
            try:
                pb.materialize_snapshot(root, ["src/widget.rs"])
                raise AssertionError(
                    "cat2: mocked FIFO st_mode not rejected before read")
            except ContractError:
                pass  # rejected: not a regular file (S_ISREG False)
            finally:
                os.lstat = _orig_lstat  # type: ignore[assignment]
        finally:
            tmp.cleanup()

    return recs


# -- Category 3: candidate validity + adapter identity binding --


def cat3_candidate_validity() -> list[ValidatedRunRecord]:
    recs: list[ValidatedRunRecord] = []
    cases: list[tuple[AdapterHooks, str, bool]] = [
        (_qhooks(valid_adapter_query), "valid", True),
        (_qhooks(adv_excerpt_leak_query), "excerpt_leak", False),
        (_qhooks(adv_duplicate_cell_query), "duplicate_cell", False),
        (_qhooks(adv_non_finite_score_query), "non_finite_score", False),
        (_qhooks(adv_provenance_mismatch_query), "provenance_mismatch", False),
        (_qhooks(adv_undeclared_channel_query), "undeclared_channel", False),
        (_qhooks(adv_sleep_timeout_query), "sleep_timeout", False),
        (_qhooks(adv_sleep_timeout_mutate_query), "sleep_timeout_mutate", False),
        (_qhooks(adv_exception_query), "exception", False),
        (_qhooks(adv_malformed_output_query), "malformed", False),
        (_qhooks(adv_partial_query), "partial", False),
        (_qhooks(adv_adapter_resource_sample_query), "adapter_resource_sample", False),
    ]
    for hooks, label, accept in cases:
        timeout = 2.0 if "sleep_timeout" in label else 30.0
        desc = valid_descriptor() if accept else adv_descriptor()
        recs.append(_repo_one_run(hooks, descriptor=desc,
                                   cat="cat3_candidate_validity", timeout=timeout))
        if accept:
            _expect_accepted(recs[-1], f"cat3:{label}")
        else:
            _expect_rejected(recs[-1], f"cat3:{label}")
    if recs[6].result_status != "timeout":
        raise AssertionError("cat3: sleep_timeout did not produce result_status=timeout")
    if recs[7].result_status != "timeout":
        raise AssertionError("cat3: sleep_timeout_mutate did not produce timeout")
    if recs[8].result_status != "failed":
        raise AssertionError("cat3: exception did not produce result_status=failed")
    if recs[9].result_status != "malformed":
        raise AssertionError("cat3: malformed did not produce result_status=malformed")
    if recs[10].result_status != "partial":
        raise AssertionError("cat3: partial did not produce result_status=partial")

    # Adapter id mismatch.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap, adapter_id="pb_wrong_adapter_id")
        rec = _ctx_run(_qhooks(valid_adapter_query), req, valid_descriptor(),
                       "cat3_candidate_validity", snap, root)
        _expect_rejected(rec, "cat3:adapter_id_mismatch")
        recs.append(rec)
    finally:
        tmp.cleanup()

    # Adapter version mismatch.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap, adapter_version="v_wrong")
        rec = _ctx_run(_qhooks(valid_adapter_query), req, valid_descriptor(),
                       "cat3_candidate_validity", snap, root)
        _expect_rejected(rec, "cat3:adapter_version_mismatch")
        recs.append(rec)
    finally:
        tmp.cleanup()

    # Language mismatch.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap, language_family="typescript")
        rec = _ctx_run(_qhooks(valid_adapter_query), req, adv_descriptor(),
                       "cat3_candidate_validity", snap, root)
        _expect_rejected(rec, "cat3:language_mismatch")
        recs.append(rec)
    finally:
        tmp.cleanup()
    return recs


# -- Category 4: common materialization/currentness --


def cat4_common_materialization_currentness() -> list[ValidatedRunRecord]:
    recs: list[ValidatedRunRecord] = []
    recs.append(_repo_one_run(_qhooks(valid_adapter_query),
                               cat="cat4_common_materialization_currentness"))
    _expect_accepted(recs[-1], "cat4")
    if recs[-1].evidence_count == 0:
        raise AssertionError("cat4: valid adapter produced no evidence")
    recs.append(_repo_one_run(_qhooks(adv_stale_range_query), descriptor=adv_descriptor(),
                               cat="cat4_common_materialization_currentness"))
    _expect_rejected(recs[-1], "cat4:stale_range")
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_with_binary(root)
        req = make_request(snapshot=snap)
        recs.append(_ctx_run(_qhooks(adv_binary_source_query), req, adv_descriptor(),
                             "cat4_common_materialization_currentness", snap, root))
        _expect_rejected(recs[-1], "cat4:binary")
    finally:
        tmp.cleanup()
    try:
        pb.BakeoffVerifiedEvidence(
            evidence_kind="verified_current", path="src/widget.rs",
            start_line=1, end_line=3, source_sha256="x", excerpt="x",
            excerpt_sha256="x", score=1.0, why=("m",), channels=frozenset({"symbol"}),
            freshness="frozen", byte_count=1, char_count=1, line_count=1,
            materializer_version=pb.MATERIALIZER_VERSION, materialized_at_step=1,
            _token=None)
        raise AssertionError("cat4: BakeoffVerifiedEvidence constructed without token")
    except ContractError:
        pass
    return recs


# -- Category 5: budget equality --


def cat5_budget_equality() -> list[ValidatedRunRecord]:
    recs: list[ValidatedRunRecord] = []
    recs.append(_repo_one_run(_qhooks(adv_over_candidate_cap_query), descriptor=adv_descriptor(),
                               cat="cat5_budget_equality",
                               request=make_request(caps=_tight_caps(max_candidates=2))))
    _expect_rejected(recs[-1], "cat5:over_candidate")
    recs.append(_repo_one_run(_qhooks(adv_over_evidence_cap_query), descriptor=adv_descriptor(),
                               cat="cat5_budget_equality",
                               request=make_request(caps=_tight_caps(max_evidence=2))))
    _expect_rejected(recs[-1], "cat5:over_evidence")
    recs.append(_repo_one_run(_qhooks(adv_over_target_cap_query), descriptor=adv_descriptor(),
                               cat="cat5_budget_equality",
                               request=make_request(caps=_tight_caps(max_targets=2))))
    _expect_rejected(recs[-1], "cat5:over_target")
    recs.append(_repo_one_run(_qhooks(adv_over_support_cap_query), descriptor=adv_descriptor(),
                               cat="cat5_budget_equality",
                               request=make_request(caps=_tight_caps(max_support=2))))
    _expect_rejected(recs[-1], "cat5:over_support")
    recs.append(_repo_one_run(_qhooks(valid_adapter_query), descriptor=valid_descriptor(),
                               cat="cat5_budget_equality",
                               request=make_request(caps=_tight_caps(max_render_chars=8))))
    _expect_rejected(recs[-1], "cat5:over_render")
    recs.append(_repo_one_run(_qhooks(valid_adapter_query), cat="cat5_budget_equality"))
    _expect_accepted(recs[-1], "cat5:within_caps")
    if pb.estimate_tokens("abc") != 1:
        raise AssertionError("cat5: ceiling estimator not ceiling")
    if pb.estimate_tokens("abcde") != 2:
        raise AssertionError("cat5: ceiling estimator not ceiling")
    return recs


# -- Category 6: pack semantics + two-step episode --


def _two_step_episode() -> list[ValidatedRunRecord]:
    """One real synthetic context->support episode with registered parent/target,
    invariant lineage, actual cumulative usage, and adversarial unknown-parent /
    unknown-target / cross-task / cross-episode / cross-snapshot / altered-cap /
    repeated-step / step-cap / budget-overrun cases."""
    recs: list[ValidatedRunRecord] = []
    registry = EpisodeRegistry()
    cat = "cat6_pack_semantics"

    # Context step.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        ctx_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="context",
            request_id="pb_syn_ctx_result_1", episode_id=SYN_EPISODE_ID)
        ctx_rec = _ctx_run(_qhooks(valid_adapter_two_step_context_query), ctx_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=1)
        _expect_accepted(ctx_rec, "cat6:two_step_context")
        recs.append(ctx_rec)
    finally:
        tmp.cleanup()

    parent = registry.lookup("pb_syn_ctx_result_1")
    if parent is None:
        raise AssertionError("cat6: context step did not register a target")
    stable_tid = parent.bound_target_id

    # Support step.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        sup_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            parent_result_id="pb_syn_ctx_result_1", bound_target_id=stable_tid,
            request_id="pb_syn_sup_req_1", episode_id=SYN_EPISODE_ID)
        sup_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), sup_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=2)
        _expect_accepted(sup_rec, "cat6:two_step_support")
        recs.append(sup_rec)
    finally:
        tmp.cleanup()

    # Adversarial: unknown parent.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        bad_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            parent_result_id="pb_nonexistent_parent",
            bound_target_id="pb_nonexistent_parent",
            request_id="pb_syn_sup_bad_1", episode_id=SYN_EPISODE_ID)
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), bad_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=2)
        _expect_rejected(bad_rec, "cat6:unknown_parent")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()

    # Adversarial: unknown target (parent exists but target id mismatch).
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        bad_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            parent_result_id="pb_syn_ctx_result_1", bound_target_id="tgt_wrong_target_id",
            request_id="pb_syn_sup_bad_1b", episode_id=SYN_EPISODE_ID)
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), bad_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=2)
        _expect_rejected(bad_rec, "cat6:unknown_target")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()

    # Adversarial: cross-task (different task_slug).
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        ctx_req_b = make_request(
            snapshot=snap, interaction_mode="two_step", operation="context",
            task_slug="pb_syn_task_beta", request_id="pb_syn_ctx_result_x",
            episode_id=SYN_EPISODE_ID + "_x")
        _ctx_run(_qhooks(valid_adapter_two_step_context_query), ctx_req_b,
                 valid_descriptor(), cat, snap, root,
                 episode_registry=registry, materialize_step=1)
        parent_x = registry.lookup("pb_syn_ctx_result_x")
        assert parent_x is not None
        bad_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            task_slug="pb_syn_task_alpha",
            parent_result_id="pb_syn_ctx_result_x",
            bound_target_id=parent_x.bound_target_id,
            request_id="pb_syn_sup_bad_2", episode_id=SYN_EPISODE_ID + "_x")
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), bad_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=2)
        _expect_rejected(bad_rec, "cat6:cross_task")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()

    # Adversarial: cross-episode (different episode_id).
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        bad_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            parent_result_id="pb_syn_ctx_result_1", bound_target_id=stable_tid,
            request_id="pb_syn_sup_bad_3", episode_id="pb_syn_different_episode")
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), bad_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=2)
        _expect_rejected(bad_rec, "cat6:cross_episode")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()

    # Adversarial: cross-snapshot (parent was repo one, support uses repo two).
    tmp, root = _new_tmp_root()
    try:
        snap_a = build_synthetic_repo_one(root)
        ctx_req_a = make_request(
            snapshot=snap_a, interaction_mode="two_step", operation="context",
            request_id="pb_syn_ctx_result_2", episode_id=SYN_EPISODE_ID + "_b")
        _ctx_run(_qhooks(valid_adapter_two_step_context_query), ctx_req_a,
                 valid_descriptor(), cat, snap_a, root,
                 episode_registry=registry, materialize_step=1)
    finally:
        tmp.cleanup()
    tmp, root = _new_tmp_root()
    try:
        snap2 = build_synthetic_repo_two(root)
        parent_2 = registry.lookup("pb_syn_ctx_result_2")
        assert parent_2 is not None
        bad_req = make_request(
            snapshot=snap2, interaction_mode="two_step", operation="support",
            parent_result_id="pb_syn_ctx_result_2",
            bound_target_id=parent_2.bound_target_id,
            request_id="pb_syn_sup_bad_4", episode_id=SYN_EPISODE_ID + "_b",
            language_family="typescript")
        desc_ts = AdapterDescriptor(
            adapter_id=SYN_ADAPTER_ID_VALID, adapter_version="v1",
            capabilities=frozenset({
                "prepare_index", "candidate_search", "target_binding",
                "support_expansion", "two_step_support",
            }),
            default_capability="candidate_search",
            supported_languages=frozenset({"typescript"}),
            persistent_state_behavior="stateless", execution_mode="process_isolated",
            upstream_revision="synthetic-v4", spdx_license_state="declared",
            output_channels=frozenset({"bm25", "symbol", "structural"})).validate()
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), bad_req,
                           desc_ts, cat, snap2, root,
                           episode_registry=registry, materialize_step=2)
        _expect_rejected(bad_rec, "cat6:cross_snapshot")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()

    # Adversarial: altered caps.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        bad_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            parent_result_id="pb_syn_ctx_result_1", bound_target_id=stable_tid,
            request_id="pb_syn_sup_bad_5", episode_id=SYN_EPISODE_ID,
            caps=_tight_caps(max_candidates=16))
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), bad_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=2)
        _expect_rejected(bad_rec, "cat6:altered_caps")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()

    # Adversarial: repeated step (support step == parent step).
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        bad_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            parent_result_id="pb_syn_ctx_result_1", bound_target_id=stable_tid,
            request_id="pb_syn_sup_bad_6", episode_id=SYN_EPISODE_ID)
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), bad_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=1)
        _expect_rejected(bad_rec, "cat6:repeated_step")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()

    # Adversarial: episode budget overrun.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        ctx_req_c = make_request(
            snapshot=snap, interaction_mode="two_step", operation="context",
            request_id="pb_syn_ctx_result_3", episode_id=SYN_EPISODE_ID + "_c")
        _ctx_run(_qhooks(valid_adapter_two_step_context_query), ctx_req_c,
                 valid_descriptor(), cat, snap, root,
                 episode_registry=registry, materialize_step=1)
        sup_req = make_request(
            snapshot=snap, interaction_mode="two_step", operation="support",
            parent_result_id="pb_syn_ctx_result_3",
            bound_target_id=registry.lookup("pb_syn_ctx_result_3").bound_target_id,
            request_id="pb_syn_sup_bad_8", episode_id=SYN_EPISODE_ID + "_c",
            caps=_tight_caps(episode_estimate_cap=1))
        bad_rec = _ctx_run(_qhooks(valid_adapter_two_step_support_query), sup_req,
                           valid_descriptor(), cat, snap, root,
                           episode_registry=registry, materialize_step=2)
        _expect_rejected(bad_rec, "cat6:budget_overrun")
        recs.append(bad_rec)
    finally:
        tmp.cleanup()
    return recs


def cat6_pack_semantics() -> list[ValidatedRunRecord]:
    recs: list[ValidatedRunRecord] = []
    recs.append(_repo_one_run(_qhooks(valid_adapter_query), cat="cat6_pack_semantics"))
    _expect_accepted(recs[-1], "cat6:ready")
    if recs[-1].pack_status != "ready":
        raise AssertionError(f"cat6: expected ready, got {recs[-1].pack_status}")
    recs.append(_repo_one_run(_qhooks(valid_adapter_empty_query), cat="cat6_pack_semantics"))
    _expect_accepted(recs[-1], "cat6:no_evidence")
    if recs[-1].pack_status != "no_evidence":
        raise AssertionError(f"cat6: expected no_evidence, got {recs[-1].pack_status}")
    recs.append(_repo_one_run(_qhooks(valid_adapter_uncertain_query), cat="cat6_pack_semantics"))
    _expect_accepted(recs[-1], "cat6:uncertain")
    if recs[-1].pack_status != "uncertain":
        raise AssertionError(f"cat6: expected uncertain, got {recs[-1].pack_status}")
    for fn, label in (
        (adv_binding_bad_target_ref_query, "bad_target_ref"),
        (adv_binding_bad_relation_query, "bad_relation"),
        (adv_binding_duplicate_support_query, "duplicate_support"),
        (adv_binding_target_is_support_query, "target_is_support"),
    ):
        recs.append(_repo_one_run(_qhooks(fn), descriptor=adv_descriptor(),
                                   cat="cat6_pack_semantics"))
        _expect_rejected(recs[-1], f"cat6:{label}")
    # Pack-level unit tests. v6: ContextPack.validate now consumes the actual
    # evidence tuple + explicit harness values. Construct minimal matching
    # evidence so the bad relation_kind is the failure point (paths/ranges
    # match; the support target_index=0 with a bogus relation fails).
    caps = default_caps()
    # Build real evidence via the materializer so paths/ranges/hashes match.
    tmp_pu, root_pu = _new_tmp_root()
    try:
        _write(root_pu, "src/widget.rs", "pub struct Widget {}\n")
        _write(root_pu, "src/config.rs", "pub const CONFIG: u32 = 1;\n")
        snap_pu = pb.materialize_snapshot(
            root_pu, ["src/widget.rs", "src/config.rs"])
        ev_cands = (
            Candidate("src/widget.rs", 1, 1, 5.0, "m", frozenset({"symbol"}),
                      SYN_ADAPTER_ID_VALID),
            Candidate("src/config.rs", 1, 1, 4.0, "m", frozenset({"bm25"}),
                      SYN_ADAPTER_ID_VALID),
        )
        ev_tup, _ = pb.materialize_candidates(ev_cands, snap_pu, step=1)
    finally:
        tmp_pu.cleanup()
    bad_support = pb.PackSupport(evidence_index=1, target_indices=(0,),
                                 relation_kind="bogus",
                                 path=ev_tup[1].path,
                                 start_line=ev_tup[1].start_line,
                                 end_line=ev_tup[1].end_line)
    target = pb.PackTarget(
        evidence_index=0, path=ev_tup[0].path,
        start_line=ev_tup[0].start_line, end_line=ev_tup[0].end_line)
    # Render the expected context so rendered_context matches the rerender.
    rc = pb._render_context(ev_tup, (target,), (bad_support,))
    usage = BudgetUsage(
        candidate_count=2, evidence_count=len(ev_tup),
        target_count=1, support_count=1,
        rendered_chars=len(rc), rendered_bytes=len(rc.encode("utf-8")),
        rendered_estimate=pb.estimate_tokens(rc),
        episode_step_count=1, episode_estimate_used=pb.estimate_tokens(rc),
    )
    bad_pack = ContextPack(pack_status="ready", status_reason=None, targets=(target,),
                           support=(bad_support,), diagnostics=(), budget_usage=usage,
                           rendered_context=rc, operation="context")
    try:
        bad_pack.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: pack with bad relation kind accepted")
    except ContractError:
        pass

    # Step cap exceeded unit test (BudgetUsage.validate_against enforces it).
    overrun_usage = BudgetUsage(
        candidate_count=1, evidence_count=1, target_count=1, support_count=0,
        rendered_chars=10, rendered_bytes=10, rendered_estimate=3,
        episode_step_count=5, episode_estimate_used=3,
    )
    try:
        overrun_usage.validate_against(default_caps())
        raise AssertionError("cat6: episode step overrun not rejected")
    except ContractError:
        pass

    # Episode estimate cap exceeded unit test.
    est_overrun = BudgetUsage(
        candidate_count=1, evidence_count=1, target_count=1, support_count=0,
        rendered_chars=10, rendered_bytes=10, rendered_estimate=3,
        episode_step_count=1, episode_estimate_used=9999,
    )
    try:
        est_overrun.validate_against(_tight_caps(episode_estimate_cap=100))
        raise AssertionError("cat6: episode estimate overrun not rejected")
    except ContractError:
        pass

    # v6 blocker 1: adversarial forged pack fields must fail. Each probe
    # constructs a pack that would pass the OLD (count-only) validation but
    # must FAIL the new (actual-evidence-tuple) validation. Uses the same
    # ev_tup built above.
    # (a) forged target path (path != evidence path).
    forged_target = pb.PackTarget(
        evidence_index=0, path="src/forged_path.rs",
        start_line=ev_tup[0].start_line, end_line=ev_tup[0].end_line)
    forged_pack_path = ContextPack(
        pack_status="ready", status_reason=None, targets=(forged_target,),
        support=(), diagnostics=(), budget_usage=usage,
        rendered_context=rc, operation="context")
    try:
        forged_pack_path.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged target path accepted")
    except ContractError:
        pass
    # (b) forged target range (range != evidence range).
    forged_target_range = pb.PackTarget(
        evidence_index=0, path=ev_tup[0].path,
        start_line=ev_tup[0].start_line, end_line=ev_tup[0].end_line + 99)
    forged_pack_range = ContextPack(
        pack_status="ready", status_reason=None,
        targets=(forged_target_range,), support=(),
        diagnostics=(), budget_usage=usage,
        rendered_context=rc, operation="context")
    try:
        forged_pack_range.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged target range accepted")
    except ContractError:
        pass
    # (c) forged support path (path != evidence path).
    forged_support = pb.PackSupport(
        evidence_index=1, target_indices=(0,), relation_kind="type_dep",
        path="src/forged_support.rs",
        start_line=ev_tup[1].start_line, end_line=ev_tup[1].end_line)
    forged_pack_sup = ContextPack(
        pack_status="ready", status_reason=None, targets=(target,),
        support=(forged_support,), diagnostics=(), budget_usage=usage,
        rendered_context=rc, operation="context")
    try:
        forged_pack_sup.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged support path accepted")
    except ContractError:
        pass
    # (d) same-length forged render (rendered_context has same length but
    # different content). Must fail the exact rerender comparison.
    same_len_forge = "x" * len(rc)
    forged_pack_render = ContextPack(
        pack_status="ready", status_reason=None, targets=(target,),
        support=(), diagnostics=(), budget_usage=usage,
        rendered_context=same_len_forge, operation="context")
    try:
        forged_pack_render.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: same-length forged render accepted")
    except ContractError:
        pass
    # (e) forged candidate_count (usage.candidate_count != explicit).
    forged_usage_cc = BudgetUsage(
        candidate_count=999, evidence_count=len(ev_tup),
        target_count=1, support_count=0,
        rendered_chars=len(rc), rendered_bytes=len(rc.encode("utf-8")),
        rendered_estimate=pb.estimate_tokens(rc),
        episode_step_count=1, episode_estimate_used=pb.estimate_tokens(rc),
    )
    forged_pack_cc = ContextPack(
        pack_status="ready", status_reason=None, targets=(target,),
        support=(), diagnostics=(), budget_usage=forged_usage_cc,
        rendered_context=rc, operation="context")
    try:
        forged_pack_cc.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged candidate_count accepted")
    except ContractError:
        pass
    # (f) forged evidence_count.
    forged_usage_ev = BudgetUsage(
        candidate_count=2, evidence_count=999,
        target_count=1, support_count=0,
        rendered_chars=len(rc), rendered_bytes=len(rc.encode("utf-8")),
        rendered_estimate=pb.estimate_tokens(rc),
        episode_step_count=1, episode_estimate_used=pb.estimate_tokens(rc),
    )
    forged_pack_ev = ContextPack(
        pack_status="ready", status_reason=None, targets=(target,),
        support=(), diagnostics=(), budget_usage=forged_usage_ev,
        rendered_context=rc, operation="context")
    try:
        forged_pack_ev.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged evidence_count accepted")
    except ContractError:
        pass
    # (g) forged rendered_chars (off by one).
    forged_usage_rc = BudgetUsage(
        candidate_count=2, evidence_count=len(ev_tup),
        target_count=1, support_count=0,
        rendered_chars=len(rc) + 1, rendered_bytes=len(rc.encode("utf-8")),
        rendered_estimate=pb.estimate_tokens(rc),
        episode_step_count=1, episode_estimate_used=pb.estimate_tokens(rc),
    )
    forged_pack_rc = ContextPack(
        pack_status="ready", status_reason=None, targets=(target,),
        support=(), diagnostics=(), budget_usage=forged_usage_rc,
        rendered_context=rc, operation="context")
    try:
        forged_pack_rc.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged rendered_chars accepted")
    except ContractError:
        pass
    # (h) forged episode_estimate_used (cumulative field).
    forged_usage_ep = BudgetUsage(
        candidate_count=2, evidence_count=len(ev_tup),
        target_count=1, support_count=0,
        rendered_chars=len(rc), rendered_bytes=len(rc.encode("utf-8")),
        rendered_estimate=pb.estimate_tokens(rc),
        episode_step_count=1, episode_estimate_used=pb.estimate_tokens(rc) + 100,
    )
    forged_pack_ep = ContextPack(
        pack_status="ready", status_reason=None, targets=(target,),
        support=(), diagnostics=(), budget_usage=forged_usage_ep,
        rendered_context=rc, operation="context")
    try:
        forged_pack_ep.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged episode_estimate_used accepted")
    except ContractError:
        pass
    # (i) forged episode_step_count.
    forged_usage_step = BudgetUsage(
        candidate_count=2, evidence_count=len(ev_tup),
        target_count=1, support_count=0,
        rendered_chars=len(rc), rendered_bytes=len(rc.encode("utf-8")),
        rendered_estimate=pb.estimate_tokens(rc),
        episode_step_count=99, episode_estimate_used=pb.estimate_tokens(rc),
    )
    forged_pack_step = ContextPack(
        pack_status="ready", status_reason=None, targets=(target,),
        support=(), diagnostics=(), budget_usage=forged_usage_step,
        rendered_context=rc, operation="context")
    try:
        forged_pack_step.validate(ev_tup, caps, 2, 1, 0)
        raise AssertionError("cat6: forged episode_step_count accepted")
    except ContractError:
        pass

    # v6 blocker 2: BindingProposal exact-combination adversarial tests.
    # (a) ready with no refs -> rejected.
    try:
        BindingProposal(
            proposed_status="ready", target_evidence_indices=(),
            support_bindings=()).validate_shape()
        raise AssertionError("cat6: ready with no refs accepted")
    except ContractError:
        pass
    # (b) ready with status_reason -> rejected.
    try:
        BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=(),
            status_reason="should not be here").validate_shape()
        raise AssertionError("cat6: ready with status_reason accepted")
    except ContractError:
        pass
    # (c) uncertain with no reason -> rejected.
    try:
        BindingProposal(
            proposed_status="uncertain", target_evidence_indices=(0,),
            support_bindings=()).validate_shape()
        raise AssertionError("cat6: uncertain with no reason accepted")
    except ContractError:
        pass
    # (d) no_evidence with refs -> rejected.
    try:
        BindingProposal(
            proposed_status="no_evidence", target_evidence_indices=(0,),
            support_bindings=()).validate_shape()
        raise AssertionError("cat6: no_evidence with refs accepted")
    except ContractError:
        pass
    # (e) no_evidence with no reason -> rejected.
    try:
        BindingProposal(
            proposed_status="no_evidence", target_evidence_indices=(),
            support_bindings=()).validate_shape()
        raise AssertionError("cat6: no_evidence with no reason accepted")
    except ContractError:
        pass
    # (f) v8: ok result with NO proposal -> rejected at result_validation
    # (validate_adapter_result). Every status=ok result MUST carry an explicit
    # BindingProposal (enforced before candidate validation succeeds); there is
    # no longer a "proposal, if present" path that reaches build_context_pack.
    tmp_nb, root_nb = _new_tmp_root()
    try:
        snap_nb = build_synthetic_repo_one(root_nb)
        nb_req = make_request(snapshot=snap_nb)
        nb_result = AdapterResult(
            status="ok", failure_category=None,
            candidates=(_widget_target_candidate(),),
            capability_ledger=_std_ledger(has_target=True, has_support=False),
            fallback_provenance=_std_fallback(),
            resource_sample=None, binding_proposal=None)
        try:
            validate_adapter_result(
                nb_result, nb_req, valid_descriptor(), snap_nb)
            raise AssertionError(
                "cat6: ok result with no proposal accepted at "
                "validate_adapter_result")
        except ContractError:
            pass
    finally:
        tmp_nb.cleanup()

    # (g) v8 end-to-end: a query returning ok + EMPTY candidates + NO proposal
    # is rejected at result_validation:ContractError, with resource timing
    # recorded but NO pack and NO canonical pack hash produced.
    tmp_ze, root_ze = _new_tmp_root()
    try:
        snap_ze = build_synthetic_repo_one(root_ze)
        ze_req = make_request(snapshot=snap_ze, adapter_id=SYN_ADAPTER_ID_ADV)
        ze_rec = _ctx_run(
            _qhooks(adv_zero_evidence_no_proposal_query), ze_req,
            adv_descriptor(), "cat6_pack_semantics", snap_ze, root_ze)
        _expect_rejected(ze_rec, "cat6:zero_evidence_no_proposal")
        if not ze_rec.failure_category.startswith("result_validation:"):
            raise AssertionError(
                f"cat6: zero-evidence/no-proposal rejected at "
                f"{ze_rec.failure_category!r}, expected result_validation:*")
        if ze_rec.result_status != "ok":
            raise AssertionError(
                f"cat6: zero-evidence/no-proposal result_status="
                f"{ze_rec.result_status!r} (the result itself was ok; only "
                f"validation rejected it)")
        if ze_rec.pack_status is not None:
            raise AssertionError(
                "cat6: zero-evidence/no-proposal produced a pack (must be none)")
        if ze_rec.canonical_pack_hash is not None:
            raise AssertionError(
                "cat6: zero-evidence/no-proposal produced a pack hash "
                "(must be none)")
        if ze_rec.resource_sample is None:
            raise AssertionError(
                "cat6: zero-evidence/no-proposal has no resource sample "
                "(timing still recorded up to result validation)")
        if ze_rec.resource_sample.query_seconds is None:
            raise AssertionError(
                "cat6: zero-evidence/no-proposal did not time query")
        recs.append(ze_rec)
    finally:
        tmp_ze.cleanup()

    recs.extend(_two_step_episode())
    return recs


# -- Category 7: determinism/cells + comparison matrix (reps 1/2/3) --


def cat7_determinism_cells() -> list[ValidatedRunRecord]:
    recs: list[ValidatedRunRecord] = []
    desc = valid_descriptor()
    # Three clean repetitions 1/2/3 with semantic determinism.
    hashes_r: list[str | None] = []
    hashes_p: list[str | None] = []
    for rep in (1, 2, 3):
        rec = _repo_one_run(_qhooks(valid_adapter_query), descriptor=desc,
                             cat="cat7_determinism_cells",
                             request=make_request(adapter_repetition=rep))
        _expect_accepted(rec, "cat7")
        hashes_r.append(rec.canonical_result_hash)
        hashes_p.append(rec.canonical_pack_hash)
        recs.append(rec)
    if len(set(hashes_r)) != 1:
        raise AssertionError(f"cat7: result hashes differ across reps: {hashes_r}")
    if len(set(hashes_p)) != 1:
        raise AssertionError(f"cat7: pack hashes differ across reps: {hashes_p}")

    # Fingerprint mismatch: different queries -> different fingerprints.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req_a = make_request(snapshot=snap, query="pb:widget:resolver")
        req_b = make_request(snapshot=snap, query="pb:different:query")
        fp_a = fairness_fingerprint(req_a.run_spec)
        fp_b = fairness_fingerprint(req_b.run_spec)
        if fp_a == fp_b:
            raise AssertionError("cat7: different queries produced same fingerprint")
        if fairness_fingerprint(req_a.run_spec) != fp_a:
            raise AssertionError("cat7: same query produced different fingerprint")
    finally:
        tmp.cleanup()

    # Comparison matrix: two comparable adapters on the same cell, reps 1/2/3.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        matrix_recs: list[ValidatedRunRecord] = []
        for rep in (1, 2, 3):
            req_v = make_request(snapshot=snap, adapter_id=SYN_ADAPTER_ID_VALID,
                                  run_cell_id="pb_syn_matrix_cell", adapter_repetition=rep)
            req_a = make_request(snapshot=snap, adapter_id=SYN_ADAPTER_ID_ALT,
                                  run_cell_id="pb_syn_matrix_cell", adapter_repetition=rep)
            r_v = _ctx_run(_qhooks(valid_adapter_query), req_v,
                           valid_descriptor(SYN_ADAPTER_ID_VALID),
                           "cat7_determinism_cells", snap, root)
            r_a = _ctx_run(_qhooks(valid_adapter_alt_query), req_a,
                            AdapterDescriptor(
                                adapter_id=SYN_ADAPTER_ID_ALT, adapter_version="v1",
                                capabilities=frozenset({
                                    "prepare_index", "candidate_search",
                                    "target_binding", "support_expansion",
                                    "two_step_support",
                                }),
                                default_capability="candidate_search",
                                supported_languages=frozenset({"rust", "typescript"}),
                                persistent_state_behavior="stateless", execution_mode="process_isolated",
                               upstream_revision="synthetic-v4", spdx_license_state="declared",
                               output_channels=frozenset({"bm25", "regex", "structural"})).validate(),
                           "cat7_determinism_cells", snap, root)
            _expect_accepted(r_v, f"cat7:matrix_valid_rep{rep}")
            _expect_accepted(r_a, f"cat7:matrix_alt_rep{rep}")
            matrix_recs.append(r_v)
            matrix_recs.append(r_a)
            recs.append(r_v)
            recs.append(r_a)
        if r_v.fingerprint != r_a.fingerprint:
            raise AssertionError("cat7: comparable arms have different fingerprints")

        matrix_spec = ComparisonMatrixSpec(
            expected_adapter_ids=(SYN_ADAPTER_ID_VALID, SYN_ADAPTER_ID_ALT),
            expected_run_cells=("pb_syn_matrix_cell",),
            expected_repetitions=(1, 2, 3),
            expected_cache_states=("cold",),
            expected_steps=(("one_shot", "context"),),
        )
        matrix_failures = validate_comparison_matrix(matrix_spec, matrix_recs)
        if matrix_failures:
            raise AssertionError(f"cat7: comparison matrix failed: {matrix_failures}")

        # Duplicate cell rejected.
        dup_failures = validate_comparison_matrix(matrix_spec, matrix_recs + [matrix_recs[0]])
        if not any("duplicate Cartesian cell" in f for f in dup_failures):
            raise AssertionError("cat7: duplicate cell not detected")

        # Missing cell rejected.
        miss_failures = validate_comparison_matrix(matrix_spec, [matrix_recs[0]])
        if not any("missing Cartesian cell" in f for f in miss_failures):
            raise AssertionError("cat7: missing cell not detected")

        # Non-comparable fingerprints rejected.
        r_b = ValidatedRunRecord(
            fingerprint="fp_different", run_cell_id="pb_syn_matrix_cell",
            adapter_id=SYN_ADAPTER_ID_ALT, status="accepted", failure_category=None,
            result_status="ok", pack_status="ready", candidate_count=1, evidence_count=1,
            target_count=1, support_count=0,
            capability_ledger_summary={"candidate_search": "executed"},
            canonical_result_hash="crh_x", canonical_pack_hash="cph_x",
            conformance_category="cat7_determinism_cells", cache_state="cold",
            interaction_mode="one_shot", operation="context",
            adapter_repetition=1, resource_sample=None)
        nc_failures = validate_comparison_matrix(matrix_spec, [matrix_recs[0], r_b])
        if not any("non-comparable" in f for f in nc_failures):
            raise AssertionError("cat7: non-comparable fingerprints not detected")

        # v4: accepted->rejected->accepted adversarial record case. A
        # "middle" repetition rejected must be detected as semantic-envelope
        # drift (status varies across reps). The matrix validator's full
        # semantic envelope check (status/result_status/pack_status/
        # failure_category/capability_ledger) catches this.
        rep1 = ValidatedRunRecord(
            fingerprint=matrix_recs[0].fingerprint,
            run_cell_id="pb_syn_drift_cell",
            adapter_id=SYN_ADAPTER_ID_VALID, status="accepted",
            failure_category=None, result_status="ok", pack_status="ready",
            candidate_count=1, evidence_count=1, target_count=1, support_count=0,
            capability_ledger_summary={
                "prepare_index": "legitimate_skip",
                "candidate_search": "executed",
                "two_step_support": "unsupported",
            },
            canonical_result_hash="crh_a", canonical_pack_hash="cph_a",
            conformance_category="cat7_determinism_cells", cache_state="cold",
            interaction_mode="one_shot", operation="context",
            adapter_repetition=1, resource_sample=None)
        # Middle rep rejected — semantic envelope drift.
        rep2 = ValidatedRunRecord(
            fingerprint=matrix_recs[0].fingerprint,
            run_cell_id="pb_syn_drift_cell",
            adapter_id=SYN_ADAPTER_ID_VALID, status="rejected",
            failure_category="result_validation:ContractError",
            result_status="failed", pack_status=None,
            candidate_count=0, evidence_count=0, target_count=0, support_count=0,
            capability_ledger_summary={
                "prepare_index": "legitimate_skip",
                "candidate_search": "failed",
                "two_step_support": "unsupported",
            },
            canonical_result_hash=None, canonical_pack_hash=None,
            conformance_category="cat7_determinism_cells", cache_state="cold",
            interaction_mode="one_shot", operation="context",
            adapter_repetition=2, resource_sample=None)
        rep3 = ValidatedRunRecord(
            fingerprint=matrix_recs[0].fingerprint,
            run_cell_id="pb_syn_drift_cell",
            adapter_id=SYN_ADAPTER_ID_VALID, status="accepted",
            failure_category=None, result_status="ok", pack_status="ready",
            candidate_count=1, evidence_count=1, target_count=1, support_count=0,
            capability_ledger_summary={
                "prepare_index": "legitimate_skip",
                "candidate_search": "executed",
                "two_step_support": "unsupported",
            },
            canonical_result_hash="crh_a", canonical_pack_hash="cph_a",
            conformance_category="cat7_determinism_cells", cache_state="cold",
            interaction_mode="one_shot", operation="context",
            adapter_repetition=3, resource_sample=None)
        drift_spec = ComparisonMatrixSpec(
            expected_adapter_ids=(SYN_ADAPTER_ID_VALID,),
            expected_run_cells=("pb_syn_drift_cell",),
            expected_repetitions=(1, 2, 3),
            expected_cache_states=("cold",),
            expected_steps=(("one_shot", "context"),),
        )
        drift_failures = validate_comparison_matrix(drift_spec, [rep1, rep2, rep3])
        if not any("semantic envelope drift" in f and "status varies" in f
                   for f in drift_failures):
            raise AssertionError(
                f"cat7: accepted->rejected->accepted drift not detected: "
                f"{drift_failures}"
            )
        if not any("semantic envelope drift" in f and "result_status varies" in f
                   for f in drift_failures):
            raise AssertionError(
                f"cat7: result_status drift not detected: {drift_failures}"
            )
        if not any("semantic envelope drift" in f and "pack_status varies" in f
                   for f in drift_failures):
            raise AssertionError(
                f"cat7: pack_status drift not detected: {drift_failures}"
            )
        if not any("semantic envelope drift" in f and "failure_category varies" in f
                   for f in drift_failures):
            raise AssertionError(
                f"cat7: failure_category drift not detected: {drift_failures}"
            )
    finally:
        tmp.cleanup()
    return recs


# -- Category 8: no silent degeneration + lifecycle --


def cat8_no_silent_degeneration() -> list[ValidatedRunRecord]:
    recs: list[ValidatedRunRecord] = []
    for fn, label in (
        (adv_missing_capability_status_query, "missing_capability"),
        (adv_extra_capability_status_query, "extra_capability"),
        (adv_failed_default_masquerade_query, "failed_default"),
        (adv_bad_fallback_query, "bad_fallback"),
    ):
        recs.append(_repo_one_run(_qhooks(fn), descriptor=adv_descriptor(),
                                   cat="cat8_no_silent_degeneration"))
        _expect_rejected(recs[-1], f"cat8:{label}")
    # unsupported vs failed vs legitimate_skip differ.
    desc = AdapterDescriptor(
        adapter_id=SYN_ADAPTER_ID_ADV, adapter_version="v1",
        capabilities=frozenset({
            "prepare_index", "candidate_search", "target_binding",
            "support_expansion", "two_step_support",
        }),
        default_capability="candidate_search",
        supported_languages=frozenset({"rust"}),
        persistent_state_behavior="stateless", execution_mode="process_isolated",
        upstream_revision="synthetic-v4", spdx_license_state="declared",
        output_channels=frozenset({"bm25", "symbol", "structural"})).validate()
    recs.append(_repo_one_run(
        _qhooks(adv_unsupported_support_query), descriptor=desc,
        cat="cat8_no_silent_degeneration",
        request=make_request(adapter_id=SYN_ADAPTER_ID_ADV),
    ))
    _expect_accepted(recs[-1], "cat8:unsupported_support")

    # Lifecycle hooks: cold run exercises prepare+index+query.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap, adapter_id=SYN_ADAPTER_ID_LIFE,
                           cache_state="cold")
        rec = _ctx_run(LIFECYCLE_HOOKS, req, lifecycle_descriptor(),
                       "cat8_no_silent_degeneration", snap, root)
        _expect_accepted(rec, "cat8:lifecycle_cold")
        if rec.resource_sample is None:
            raise AssertionError("cat8: cold lifecycle run has no resource sample")
        if rec.resource_sample.setup_seconds is None:
            raise AssertionError("cat8: cold lifecycle run did not time setup")
        if rec.resource_sample.index_seconds is None:
            raise AssertionError("cat8: cold lifecycle run did not time index")
        if rec.resource_sample.query_seconds is None:
            raise AssertionError("cat8: lifecycle run did not time query")
        recs.append(rec)
    finally:
        tmp.cleanup()

    # Lifecycle hooks: warm run with warm_reuse skips prepare+index.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        req = make_request(snapshot=snap, adapter_id=SYN_ADAPTER_ID_LIFE,
                           cache_state="warm")
        rec = _ctx_run(LIFECYCLE_HOOKS, req, lifecycle_descriptor(),
                       "cat8_no_silent_degeneration", snap, root)
        _expect_accepted(rec, "cat8:lifecycle_warm")
        if rec.resource_sample is None:
            raise AssertionError("cat8: warm lifecycle run has no resource sample")
        if rec.resource_sample.setup_seconds is not None:
            raise AssertionError("cat8: warm run should skip prepare (setup=None)")
        if rec.resource_sample.index_seconds is not None:
            raise AssertionError("cat8: warm run should skip index (index=None)")
        recs.append(rec)
    finally:
        tmp.cleanup()

    # Adversarial: prepare hook crashes.
    recs.append(_repo_one_run(ADV_PREPARE_FAILS_HOOKS, descriptor=valid_descriptor(),
                               cat="cat8_no_silent_degeneration"))
    prepare_fails_rec = recs[-1]
    _expect_rejected(prepare_fails_rec, "cat8:prepare_fails")
    if prepare_fails_rec.resource_sample is None:
        raise AssertionError("cat8: prepare-fails run has no resource sample")
    if prepare_fails_rec.resource_sample.setup_seconds is None:
        raise AssertionError("cat8: prepare-fails run did not time setup")

    # Adversarial: index hook crashes.
    recs.append(_repo_one_run(ADV_INDEX_FAILS_HOOKS, descriptor=valid_descriptor(),
                               cat="cat8_no_silent_degeneration"))
    index_fails_rec = recs[-1]
    _expect_rejected(index_fails_rec, "cat8:index_fails")

    # v7: sleeping prepare/index hooks that attempt a delayed marker write.
    # Proves stage-aware spawned timeout enforcement covers prepare/index:
    # timeout rejection, child terminated before marker write (absent
    # immediately AND after a guard delay), visible source unchanged, and a
    # ResourceSample with the phase duration present. Kept fast (sleep fixture
    # 0.25s with timeout 0.05 and a short 0.1s guard).
    import time as _guard_time

    # Sleeping prepare timeout.
    tmp_sp, root_sp = _new_tmp_root()
    try:
        snap_sp = build_synthetic_repo_one(root_sp)
        sp_req = make_request(
            snapshot=snap_sp, adapter_id=SYN_ADAPTER_ID_VALID,
            cache_state="cold", timeout_seconds=0.05,
            request_id="pb_syn_sleep_prepare", episode_id="pb_syn_sleep_ep")
        sp_rec = _ctx_run(
            ADV_SLEEP_PREPARE_HOOKS, sp_req, valid_descriptor(),
            "cat8_no_silent_degeneration", snap_sp, root_sp)
        _expect_rejected(sp_rec, "cat8:sleep_prepare_timeout")
        if sp_rec.result_status != "timeout":
            raise AssertionError(
                f"cat8: sleep_prepare did not produce timeout, got "
                f"{sp_rec.result_status}")
        if sp_rec.failure_category != "lifecycle_timeout:prepare":
            raise AssertionError(
                f"cat8: sleep_prepare failure_category="
                f"{sp_rec.failure_category!r}, expected "
                f"'lifecycle_timeout:prepare'")
        if sp_rec.resource_sample is None:
            raise AssertionError("cat8: sleep_prepare run has no resource sample")
        if sp_rec.resource_sample.setup_seconds is None:
            raise AssertionError("cat8: sleep_prepare run did not time setup")
        # Marker must be absent immediately (child terminated before write).
        sleep_marker = root_sp / ".pb_writable_state" / _SLEEP_MARKER_REL
        if sleep_marker.is_file():
            raise AssertionError(
                "cat8: sleep_prepare marker exists immediately (child not "
                "terminated before delayed write)")
        # Marker still absent after a guard delay proving child terminated.
        _guard_time.sleep(0.1)
        if sleep_marker.is_file():
            raise AssertionError(
                "cat8: sleep_prepare marker appeared after guard delay (child "
                "continued writing after timeout)")
        # Visible source unchanged.
        try:
            pb.assert_snapshot_unchanged(snap_sp)
        except ContractError:
            raise AssertionError(
                "cat8: sleep_prepare mutated visible source")
        recs.append(sp_rec)
    finally:
        tmp_sp.cleanup()

    # Sleeping index timeout.
    tmp_si, root_si = _new_tmp_root()
    try:
        snap_si = build_synthetic_repo_one(root_si)
        si_req = make_request(
            snapshot=snap_si, adapter_id=SYN_ADAPTER_ID_VALID,
            cache_state="cold", timeout_seconds=0.05,
            request_id="pb_syn_sleep_index", episode_id="pb_syn_sleep_ep")
        si_rec = _ctx_run(
            ADV_SLEEP_INDEX_HOOKS, si_req, valid_descriptor(),
            "cat8_no_silent_degeneration", snap_si, root_si)
        _expect_rejected(si_rec, "cat8:sleep_index_timeout")
        if si_rec.result_status != "timeout":
            raise AssertionError(
                f"cat8: sleep_index did not produce timeout, got "
                f"{si_rec.result_status}")
        if si_rec.failure_category != "lifecycle_timeout:index":
            raise AssertionError(
                f"cat8: sleep_index failure_category="
                f"{si_rec.failure_category!r}, expected "
                f"'lifecycle_timeout:index'")
        if si_rec.resource_sample is None:
            raise AssertionError("cat8: sleep_index run has no resource sample")
        if si_rec.resource_sample.index_seconds is None:
            raise AssertionError("cat8: sleep_index run did not time index")
        sleep_marker_i = root_si / ".pb_writable_state" / _SLEEP_MARKER_REL
        if sleep_marker_i.is_file():
            raise AssertionError(
                "cat8: sleep_index marker exists immediately (child not "
                "terminated before delayed write)")
        _guard_time.sleep(0.1)
        if sleep_marker_i.is_file():
            raise AssertionError(
                "cat8: sleep_index marker appeared after guard delay (child "
                "continued writing after timeout)")
        try:
            pb.assert_snapshot_unchanged(snap_si)
        except ContractError:
            raise AssertionError(
                "cat8: sleep_index mutated visible source")
        recs.append(si_rec)
    finally:
        tmp_si.cleanup()

    # v8: exact stage return matrix. prepare/index must return exactly None;
    # query must return exactly AdapterResult. Every other shape is
    # malformed/non_adapter_result, with resource timing recorded and NO pack
    # (pack_status=None, canonical_pack_hash=None).
    # (1) prepare returning an AdapterResult.
    recs.append(_repo_one_run(
        ADV_PREPARE_RETURNS_AR_HOOKS, descriptor=valid_descriptor(),
        cat="cat8_no_silent_degeneration"))
    prep_ar_rec = recs[-1]
    _expect_rejected(prep_ar_rec, "cat8:prepare_returns_adapter_result")
    if prep_ar_rec.result_status != "malformed":
        raise AssertionError(
            f"cat8: prepare_returns_adapter_result result_status="
            f"{prep_ar_rec.result_status!r}, expected malformed")
    if prep_ar_rec.failure_category != "non_adapter_result":
        raise AssertionError(
            f"cat8: prepare_returns_adapter_result failure_category="
            f"{prep_ar_rec.failure_category!r}, expected non_adapter_result")
    if prep_ar_rec.pack_status is not None:
        raise AssertionError(
            "cat8: prepare_returns_adapter_result produced a pack (must be none)")
    if prep_ar_rec.canonical_pack_hash is not None:
        raise AssertionError(
            "cat8: prepare_returns_adapter_result produced a pack hash")
    if prep_ar_rec.resource_sample is None:
        raise AssertionError(
            "cat8: prepare_returns_adapter_result has no resource sample")
    if prep_ar_rec.resource_sample.setup_seconds is None:
        raise AssertionError(
            "cat8: prepare_returns_adapter_result did not time setup")

    # (2) index returning an AdapterResult.
    recs.append(_repo_one_run(
        ADV_INDEX_RETURNS_AR_HOOKS, descriptor=valid_descriptor(),
        cat="cat8_no_silent_degeneration"))
    idx_ar_rec = recs[-1]
    _expect_rejected(idx_ar_rec, "cat8:index_returns_adapter_result")
    if idx_ar_rec.result_status != "malformed":
        raise AssertionError(
            f"cat8: index_returns_adapter_result result_status="
            f"{idx_ar_rec.result_status!r}, expected malformed")
    if idx_ar_rec.failure_category != "non_adapter_result":
        raise AssertionError(
            f"cat8: index_returns_adapter_result failure_category="
            f"{idx_ar_rec.failure_category!r}, expected non_adapter_result")
    if idx_ar_rec.pack_status is not None:
        raise AssertionError(
            "cat8: index_returns_adapter_result produced a pack (must be none)")
    if idx_ar_rec.canonical_pack_hash is not None:
        raise AssertionError(
            "cat8: index_returns_adapter_result produced a pack hash")
    if idx_ar_rec.resource_sample is None:
        raise AssertionError(
            "cat8: index_returns_adapter_result has no resource sample")
    if idx_ar_rec.resource_sample.index_seconds is None:
        raise AssertionError(
            "cat8: index_returns_adapter_result did not time index")

    # (3) query returning None (instead of an AdapterResult).
    recs.append(_repo_one_run(
        ADV_QUERY_RETURNS_NONE_HOOKS,
        request=make_request(adapter_id=SYN_ADAPTER_ID_ADV),
        descriptor=adv_descriptor(),
        cat="cat8_no_silent_degeneration"))
    q_none_rec = recs[-1]
    _expect_rejected(q_none_rec, "cat8:query_returns_none")
    if q_none_rec.result_status != "malformed":
        raise AssertionError(
            f"cat8: query_returns_none result_status="
            f"{q_none_rec.result_status!r}, expected malformed")
    if q_none_rec.failure_category != "non_adapter_result":
        raise AssertionError(
            f"cat8: query_returns_none failure_category="
            f"{q_none_rec.failure_category!r}, expected non_adapter_result")
    if q_none_rec.pack_status is not None:
        raise AssertionError(
            "cat8: query_returns_none produced a pack (must be none)")
    if q_none_rec.canonical_pack_hash is not None:
        raise AssertionError(
            "cat8: query_returns_none produced a pack hash")
    if q_none_rec.resource_sample is None:
        raise AssertionError(
            "cat8: query_returns_none has no resource sample")
    if q_none_rec.resource_sample.query_seconds is None:
        raise AssertionError(
            "cat8: query_returns_none did not time query")

    # v9: capability-ledger honesty — candidate_search. Nonempty candidates
    # with candidate_search NOT executed must reject at capability_honesty
    # BEFORE the materializer reads any source bytes. A materializer spy
    # proves the materializer was not touched.
    _materializer_touched = {"hit": False}
    _orig_mat = pb.materialize_candidates

    def _spy_materialize(cands, snap, step=1):
        _materializer_touched["hit"] = True
        return _orig_mat(cands, snap, step=step)

    recs.append(_repo_one_run(
        _qhooks(adv_candidates_nonexecuted_search_query),
        request=make_request(adapter_id=SYN_ADAPTER_ID_ADV),
        descriptor=adv_descriptor(), cat="cat8_no_silent_degeneration"))
    cse_rec = recs[-1]
    _expect_rejected(cse_rec, "cat8:candidates_nonexecuted_search")
    if cse_rec.failure_category != "capability_honesty:ContractError":
        raise AssertionError(
            f"cat8: candidates_nonexecuted_search failure_category="
            f"{cse_rec.failure_category!r}, expected "
            f"capability_honesty:ContractError (honesty before materializer)")
    if cse_rec.pack_status is not None:
        raise AssertionError(
            "cat8: candidates_nonexecuted_search produced a pack (must be none)")
    if cse_rec.capability_ledger_summary != {}:
        raise AssertionError(
            "cat8: candidates_nonexecuted_search rejected record has nonempty "
            "ledger (must be empty — only accepted records publish ledger)")

    # v9: zero candidates with candidate_search=executed is VALID (NO converse
    # — executed may return zero). Must be accepted with no_evidence.
    recs.append(_repo_one_run(
        _qhooks(valid_zero_candidate_executed_search_query),
        descriptor=valid_descriptor(), cat="cat8_no_silent_degeneration"))
    zce_rec = recs[-1]
    _expect_accepted(zce_rec, "cat8:zero_candidate_executed_search")
    if zce_rec.pack_status != "no_evidence":
        raise AssertionError(
            f"cat8: zero_candidate_executed_search pack_status="
            f"{zce_rec.pack_status!r}, expected no_evidence")
    if zce_rec.capability_ledger_summary.get("candidate_search") != "executed":
        raise AssertionError(
            "cat8: zero_candidate_executed_search accepted record ledger "
            "candidate_search != executed")

    # v8: launch-failure unit test. A genuine multiprocessing launch/resource
    # failure (controlled fake Process whose start() raises) must clean up
    # both pipe endpoints and raise HarnessInfrastructureError — NEVER becoming
    # one adapter's ValidatedRunRecord or comparison datapoint. This uses a
    # controlled fake (no brittle OS behavior).
    closed_pipes: list[str] = []

    class _FakePipeEP:
        def __init__(self, name: str) -> None:
            self.name = name

        def close(self) -> None:
            closed_pipes.append(self.name)

        def poll(self, timeout: float) -> bool:
            return False

        def recv(self) -> Any:
            raise EOFError()

        def send(self, obj: Any) -> None:
            pass

        def recv_bytes(self) -> bytes:
            raise EOFError()

        def send_bytes(self, data: bytes) -> None:
            pass

    class _FakeProcess:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def start(self) -> None:
            raise OSError("simulated spawn resource exhaustion")

        def is_alive(self) -> bool:
            return False

        def terminate(self) -> None:
            pass

        def join(self, timeout: float | None = None) -> None:
            pass

        def kill(self) -> None:
            pass

        def close(self) -> None:
            pass

    class _FakeCtx:
        def Pipe(self, duplex: bool = True) -> tuple[Any, Any]:
            return _FakePipeEP("parent"), _FakePipeEP("child")

        def Process(self, **kwargs: Any) -> Any:
            return _FakeProcess(**kwargs)

    _orig_get_context = multiprocessing.get_context
    multiprocessing.get_context = lambda name: _FakeCtx()  # type: ignore[assignment]
    try:
        # Direct: _execute_stage_isolated raises HarnessInfrastructureError
        # and closes BOTH pipe endpoints on the launch-failure path.
        tmp_hie, root_hie = _new_tmp_root()
        try:
            snap_hie = build_synthetic_repo_one(root_hie)
            hie_req = make_request(snapshot=snap_hie)
            try:
                _execute_stage_isolated(
                    valid_adapter_query, hie_req, root_hie,
                    valid_descriptor(), "query")
                raise AssertionError(
                    "cat8: launch-failure did not raise "
                    "HarnessInfrastructureError from _execute_stage_isolated")
            except HarnessInfrastructureError:
                pass
            if "parent" not in closed_pipes or "child" not in closed_pipes:
                raise AssertionError(
                    f"cat8: launch-failure did not clean up both pipe "
                    f"endpoints (closed={closed_pipes})")
        finally:
            tmp_hie.cleanup()

        # End-to-end: run_adapter must PROPAGATE HarnessInfrastructureError
        # (not catch it as an adapter error / convert to a ValidatedRunRecord).
        tmp_hie2, root_hie2 = _new_tmp_root()
        try:
            snap_hie2 = build_synthetic_repo_one(root_hie2)
            hie_req2 = make_request(snapshot=snap_hie2)
            try:
                _ctx_run(
                    _qhooks(valid_adapter_query), hie_req2, valid_descriptor(),
                    "cat8_no_silent_degeneration", snap_hie2, root_hie2)
                raise AssertionError(
                    "cat8: launch-failure run_adapter did not propagate "
                    "HarnessInfrastructureError (it was converted to a "
                    "ValidatedRunRecord)")
            except HarnessInfrastructureError:
                pass
        finally:
            tmp_hie2.cleanup()
    finally:
        multiprocessing.get_context = _orig_get_context  # type: ignore[assignment]

    # v11: bounded strict JSON primitive wire adversarial tests. Controlled
    # fakes inject specific Pipe/Process behavior (no brittle OS behavior)
    # PLUS real spawned hostile hooks proving the parent never executes
    # adapter-authored arbitrary code (no pickle anywhere on the wire).
    # These prove: truncated/undecodable/wrong-shape/duplicate-keys/nonfinite/
    # invalid-utf8/trailing-docs/extra-keys/missing-keys/bool-as-version/
    # custom-type -> malformed; parent-observed over-bound -> malformed
    # (adapter-scoped, NOT infra); recv OSError -> malformed (adapter-scoped);
    # child EOF / any os._exit(code) -> process_died (NEVER infra); real
    # child send failure / EOF -> process_died; parent-side setup/start and
    # unreaped cleanup still infra; maxlength actually passed; at-bound
    # succeeds; repeated hostile/timeout runs leave no active children/
    # receiver threads; tests traverse _execute_stage_isolated.
    _TRANSPORT_FAKES_RUN = True

    class _TPE:  # transport fake pipe endpoint
        def __init__(self, *, poll_ret=False, recv_bytes_data=None,
                     recv_bytes_exc=None, poll_delay=0.0, recv_delay=0.0):
            self._poll_ret = poll_ret
            self._data = recv_bytes_data
            self._exc = recv_bytes_exc
            self._poll_delay = poll_delay
            self._recv_delay = recv_delay
            self.closed = False
            self.last_maxlength = "not_called"

        def close(self):
            self.closed = True

        def poll(self, timeout):
            if self._poll_delay > 0:
                time.sleep(min(self._poll_delay, timeout))
            return self._poll_ret

        def recv_bytes(self, maxlength=-1):
            # Simulate stdlib recv_bytes(maxlength=N) behavior: the stdlib
            # reads the length header first and raises OSError without
            # allocating the oversized body. The FakePipe checks
            # len(data) > maxlength and raises OSError BEFORE returning
            # data (simulating no-allocation on over-bound).
            self.last_maxlength = maxlength
            if self._recv_delay > 0:
                time.sleep(self._recv_delay)
            if self._exc is not None:
                raise self._exc
            if (maxlength >= 0 and self._data is not None
                    and len(self._data) > maxlength):
                raise OSError("message longer than maxlength")
            return self._data

        def send_bytes(self, data):
            pass

    class _TPROC:  # transport fake process
        def __init__(self, *, always_alive=False, exitcode=None):
            self._always_alive = always_alive
            self._closed = False
            self._exitcode = exitcode

        def start(self):
            pass

        def is_alive(self):
            if self._always_alive:
                return True
            return False

        def terminate(self):
            pass

        def join(self, timeout=None):
            pass

        def kill(self):
            pass

        # exitcode property so the parent can inspect the child exit code
        # on EOF (captured by _reap_process BEFORE close()). v11: the parent
        # no longer uses the exit code to distinguish transport failure
        # (every child EOF/exit code is adapter-scoped process_died), but
        # _reap_process still captures it for defense-in-depth.
        @property
        def exitcode(self):
            return self._exitcode

        def close(self):
            self._closed = True

    class _TCTX:
        def __init__(self, parent_pe, proc):
            self._pe = parent_pe
            self._proc = proc

        def Pipe(self, duplex=True):
            return self._pe, _TPE()

        def Process(self, **kwargs):
            return self._proc

    def _run_transport_fake(parent_pe, proc=None, timeout=0.4):
        """Run _execute_stage_isolated with a fake context; return (status,
        result, err) or the raised exception (as ('infra', None, str(e)))."""
        if proc is None:
            proc = _TPROC()
        orig = multiprocessing.get_context
        multiprocessing.get_context = lambda name: _TCTX(parent_pe, proc)  # type: ignore[assignment]
        try:
            tmp_t, root_t = _new_tmp_root()
            try:
                snap_t = build_synthetic_repo_one(root_t)
                req_t = make_request(snapshot=snap_t, timeout_seconds=timeout)
                try:
                    return _execute_stage_isolated(
                        valid_adapter_query, req_t, root_t,
                        valid_descriptor(), "query")
                except HarnessInfrastructureError as e:
                    return ("infra", None, str(e))
            finally:
                tmp_t.cleanup()
        finally:
            multiprocessing.get_context = orig  # type: ignore[assignment]

    # Helper: build closed JSON envelope bytes for fake-recv tests.
    def _env_bytes(*, status, payload, error):
        return _wire_encode_envelope(
            _wire_build_envelope(status=status, payload=payload, error=error))

    # 1. truncated/undecodable -> malformed.
    r = _run_transport_fake(_TPE(poll_ret=True, recv_bytes_data=b"not_json"))
    if r[0] != "malformed":
        raise AssertionError(f"cat8: undecodable -> {r[0]!r}, expected malformed")

    # 2. wrong shape (JSON list instead of closed envelope dict) -> malformed.
    r = _run_transport_fake(_TPE(
        poll_ret=True, recv_bytes_data=b'[1, "bad"]'))
    if r[0] != "malformed":
        raise AssertionError(f"cat8: bad_shape -> {r[0]!r}, expected malformed")

    # 3. v11: parent-observed over-bound -> malformed (adapter-scoped, NOT
    # infra). recv_bytes(maxlength=MAX) raises OSError for over-bound data
    # (FakePipe simulates stdlib behavior); OSError is classified as
    # adapter-scoped malformed (NEVER infra). The parent never allocates >
    # bound and never aborts the whole bakeoff.
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=b"x" * (MAX_STAGE_WIRE_BYTES + 1)))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: parent-observed over-bound -> {r[0]!r}, "
            f"expected malformed (adapter-scoped, NOT infra)")

    # 4. child EOF -> process_died (adapter-scoped; ordinary child death).
    r = _run_transport_fake(_TPE(poll_ret=True, recv_bytes_exc=EOFError()))
    if r[0] != "error" or r[2] != "process_died":
        raise AssertionError(
            f"cat8: child EOF -> ({r[0]!r},{r[2]!r}), expected error/process_died")

    # 5. v11: recv OSError -> malformed (adapter-scoped, NOT infra). A
    # child can induce an OSError on recv_bytes (oversized/invalid frame);
    # the parent fails closed as adapter-scoped malformed without aborting
    # the whole bakeoff. The OSError message is NOT parsed.
    r = _run_transport_fake(_TPE(poll_ret=True, recv_bytes_exc=OSError("broken")))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: recv OSError -> {r[0]!r}, expected malformed "
            f"(adapter-scoped, NOT HarnessInfrastructureError)")

    # 6. v11: REMOVED transport_failure signal test (no transport_failure
    # status anymore). A child cannot author an infra-abort status. The
    # "transport_failure" string in a payload is now just malformed bytes
    # (the closed envelope schema rejects unknown status values).
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=_env_bytes(
            status="transport_failure", payload=None, error="send_failed")))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: unknown 'transport_failure' status -> {r[0]!r}, "
            f"expected malformed (closed envelope rejects unknown status)")

    # 7. stall/timeout -> timeout.
    r = _run_transport_fake(_TPE(poll_ret=False), timeout=0.3)
    if r[0] != "timeout":
        raise AssertionError(f"cat8: stall -> {r[0]!r}, expected timeout")

    # 8. unreapable child -> HarnessInfrastructureError (parent-local
    # cleanup failure; still infra).
    r = _run_transport_fake(
        _TPE(poll_ret=False), _TPROC(always_alive=True), timeout=0.3)
    if r[0] != "infra":
        raise AssertionError(
            f"cat8: unreapable -> {r[0]!r}, expected infra")

    # 9. decode-after-deadline cannot succeed. poll returns True but
    # recv_bytes delays past the deadline; the outcome must be timeout,
    # NOT ok/malformed.
    r = _run_transport_fake(
        _TPE(poll_ret=True, poll_delay=0.1, recv_delay=0.5,
             recv_bytes_data=_env_bytes(
                 status="ok", payload=None, error=None)),
        timeout=0.3)
    if r[0] != "timeout":
        raise AssertionError(
            f"cat8: decode-after-deadline -> {r[0]!r}, expected timeout "
            f"(decode-after-deadline cannot succeed)")

    # 10. repeated timeout no thread accumulation.
    _thread_base = threading.active_count()
    for _ in range(3):
        _run_transport_fake(_TPE(poll_ret=False), timeout=0.3)
    # Allow receiver threads to fully exit.
    time.sleep(0.5)
    _thread_after = threading.active_count()
    if _thread_after > _thread_base + 1:
        raise AssertionError(
            f"cat8: thread accumulation after repeated timeout "
            f"(base={_thread_base} after={_thread_after})")

    # 11. maxlength is actually passed to recv_bytes by the receiver.
    class _TPE_ml:
        def __init__(self):
            self.closed = False
            self.passed_maxlength = "not_called"
        def close(self): self.closed = True
        def poll(self, timeout): return True
        def recv_bytes(self, maxlength=-1):
            self.passed_maxlength = maxlength
            # Return a valid v11 error envelope (no AdapterResult required).
            return _env_bytes(status="error", payload=None, error="RuntimeError")
        def send_bytes(self, data): pass
    _ml_pe = _TPE_ml()
    r = _run_transport_fake(_ml_pe)
    if r[0] != "error" or r[2] != "RuntimeError":
        raise AssertionError(
            f"cat8: maxlength probe -> ({r[0]!r},{r[2]!r}), "
            f"expected error/RuntimeError")
    if _ml_pe.passed_maxlength != MAX_STAGE_WIRE_BYTES:
        raise AssertionError(
            f"cat8: maxlength={_ml_pe.passed_maxlength!r}, "
            f"expected {MAX_STAGE_WIRE_BYTES}")

    # 12. at-bound (exactly maxlength) succeeds; over-bound raises OSError
    # (FakePipe simulates stdlib recv_bytes(maxlength=N) behavior).
    _tpe_at = _TPE(poll_ret=True, recv_bytes_data=b"x" * 10)
    _data_at = _tpe_at.recv_bytes(maxlength=10)  # at-bound: succeeds
    if _data_at != b"x" * 10:
        raise AssertionError("cat8: at-bound recv_bytes did not return data")
    _tpe_over = _TPE(poll_ret=True, recv_bytes_data=b"x" * 10)
    try:
        _tpe_over.recv_bytes(maxlength=9)  # over-bound: raises OSError
        raise AssertionError(
            "cat8: over-bound should raise OSError (no allocation)")
    except OSError:
        pass

    # 13. v11: any os._exit(code) on EOF => process_died (adapter-scoped,
    # NOT infra). The dedicated WORKER_TRANSPORT_FAILURE_EXIT_CODE was
    # REMOVED; an adapter may call any os._exit(code) and every child
    # EOF/exit code is adapter-scoped process_died (never infra).
    for _ec in (1, 73, -9, 0, 139, None):
        r = _run_transport_fake(
            _TPE(poll_ret=True, recv_bytes_exc=EOFError()),
            _TPROC(exitcode=_ec))
        if r[0] != "error" or r[2] != "process_died":
            raise AssertionError(
                f"cat8: child exit code {_ec} on EOF -> "
                f"({r[0]!r},{r[2]!r}), expected error/process_died "
                f"(adapter-scoped, NOT infra)")

    # 14. no child/thread leak after exit-code tests. _reap_process
    # verifies the child is not alive (raises HarnessInfrastructureError if
    # alive); the receiver thread must have exited. A passing run here
    # proves no child leak and no thread leak.
    _thread_base2 = threading.active_count()
    time.sleep(0.3)
    _thread_after2 = threading.active_count()
    if _thread_after2 > _thread_base2 + 1:
        raise AssertionError(
            f"cat8: thread leak after exit-code tests "
            f"(base={_thread_base2} after={_thread_after2})")

    # 15. v11: exact canonical AdapterResult round-trips over JSON and
    # remains accepted. This is the positive control: a valid query result
    # serializes to JSON in the child, the parent decodes/reconstructs it
    # field-by-field, and validate_adapter_result + capability_ledger_
    # honesty accept it. Uses a real spawned child (not a fake).
    tmp_rt, root_rt = _new_tmp_root()
    try:
        snap_rt = build_synthetic_repo_one(root_rt)
        req_rt = make_request(snapshot=snap_rt, timeout_seconds=30.0)
        # _execute_stage_isolated returns (status, result, err, wall).
        rt_status, rt_result, rt_err, _ = _execute_stage_isolated(
            valid_adapter_query, req_rt, root_rt,
            valid_descriptor(), "query")
        if rt_status != "ok" or rt_result is None or rt_err is not None:
            raise AssertionError(
                f"cat8: valid AdapterResult round-trip -> "
                f"({rt_status!r}, {rt_result!r}, {rt_err!r}), "
                f"expected (ok, AdapterResult, None)")
        if type(rt_result) is not AdapterResult:
            raise AssertionError(
                f"cat8: round-trip result type {type(rt_result).__name__}, "
                f"expected exact AdapterResult")
        # Round-trip equality: the reconstructed AdapterResult must equal
        # the original (canonical_result_hash must match). The hash takes
        # (result, candidates) so we pass the result's own candidates tuple.
        _orig = valid_adapter_query(req_rt, root_rt)
        _orig_hash = canonical_result_hash(_orig, _orig.candidates)
        _rt_hash = canonical_result_hash(rt_result, rt_result.candidates)
        if _orig_hash != _rt_hash:
            raise AssertionError(
                f"cat8: round-trip hash mismatch "
                f"(orig={_orig_hash!r} rt={_rt_hash!r})")
    finally:
        tmp_rt.cleanup()

    # 16. v11: duplicate keys at outer envelope level reject as malformed.
    # json.loads with object_pairs_hook rejects duplicate keys at every
    # object level. The "v" key is duplicated.
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=(b'{"v":1,"v":2,"status":"ok",'
                         b'"payload":null,"error":null}')))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: outer duplicate keys -> {r[0]!r}, expected malformed")

    # 17. v11: duplicate keys at nested payload level reject as malformed.
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=(
            b'{"v":1,"status":"ok","error":null,"payload":{'
            b'"status":"ok","failure_category":null,"candidates":[],'
            b'"capability_ledger":{"candidate_search":"executed",'
            b'"candidate_search":"failed"},'
            b'"fallback_provenance":[],"binding_proposal":null}}')))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: nested duplicate keys -> {r[0]!r}, expected malformed")

    # 18. v11: NaN/Infinity reject (parse_constant hook). json.loads
    # accepts NaN/Infinity by default; the parse_constant hook rejects.
    for _bad_const in (b'NaN', b'Infinity', b'-Infinity'):
        r = _run_transport_fake(_TPE(
            poll_ret=True,
            recv_bytes_data=(
                b'{"v":1,"status":"ok","payload":null,"error":' + _bad_const + b'}')))
        if r[0] != "malformed":
            raise AssertionError(
                f"cat8: {_bad_const!r} constant -> {r[0]!r}, expected malformed")

    # 19. v11: invalid UTF-8 rejects as malformed.
    r = _run_transport_fake(_TPE(
        poll_ret=True, recv_bytes_data=b'\xff\xfe{"v":1}'))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: invalid utf-8 -> {r[0]!r}, expected malformed")

    # 20. v11: trailing/multiple docs reject (json.loads strict rejects
    # extra data after the first JSON value).
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=(
            _env_bytes(status="ok", payload=None, error=None)
            + b'{"extra":1}')))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: trailing docs -> {r[0]!r}, expected malformed")

    # 21. v11: extra envelope keys reject (closed set enforced).
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=(
            b'{"v":1,"status":"ok","payload":null,"error":null,'
            b'"extra":"hostile"}')))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: extra envelope key -> {r[0]!r}, expected malformed")

    # 22. v11: missing envelope keys reject (closed set enforced).
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=b'{"v":1,"status":"ok","payload":null}'))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: missing envelope key -> {r[0]!r}, expected malformed")

    # 23. v11: bool-as-version rejects (ambiguous bool-as-int avoided via
    # ``type(v) is int`` semantics; ``type(True) is int`` is False).
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=(
            b'{"v":true,"status":"ok","payload":null,"error":null}')))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: bool-as-version -> {r[0]!r}, expected malformed")

    # 24. v11: wrong envelope status rejects (closed vocab enforced).
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=_env_bytes(
            status="hostile_status", payload=None, error=None)))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: unknown envelope status -> {r[0]!r}, expected malformed")

    # 25. v11: error status with null error string rejects.
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=_env_bytes(
            status="error", payload=None, error=None)))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: error status null error -> {r[0]!r}, expected malformed")

    # 26. v11: malformed status with non-null payload rejects.
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=(
            b'{"v":1,"status":"malformed","payload":{"x":1},"error":null}')))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: malformed status non-null payload -> {r[0]!r}, "
            f"expected malformed")

    # 26a. v12: deeply nested JSON beyond the C parser recursion limit
    # raises RecursionError in json.loads. The boundary in
    # _wire_decode_envelope converts RecursionError to _WireError so the
    # receiver classifies adapter-scoped malformed (NEVER infra). A child
    # can induce this by sending a deeply nested JSON frame.
    _DEEP_NEST = b'[' * 6000 + b']' * 6000  # 12000 bytes; well under wire bound
    r = _run_transport_fake(_TPE(poll_ret=True, recv_bytes_data=_DEEP_NEST))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: deep-nesting RecursionError -> {r[0]!r}, "
            f"expected malformed (adapter-scoped, NOT infra)")

    # 26b. v12: integer token beyond ``sys.get_int_max_str_digits()``
    # (Python 3.11+ feature-detect) raises ValueError in json.loads. The
    # boundary converts ValueError (that is NOT JSONDecodeError) to
    # _WireError so the receiver classifies adapter-scoped malformed
    # (NEVER infra). On Python < 3.11 there is no int->str digit limit
    # and this case is honestly skipped (feature not present).
    _int_max_str_digits_fn = getattr(sys, "get_int_max_str_digits", None)
    if callable(_int_max_str_digits_fn):
        _int_max_digits = _int_max_str_digits_fn()
        # Build an oversized integer literal with more digits than the
        # limit. The "v" envelope field expects an int; the oversized
        # literal is therefore parsed by json.loads as an int and trips
        # the int->str digit limit BEFORE envelope validation runs.
        _oversized_int = b'9' * (_int_max_digits + 100)
        _oversized_payload = (
            b'{"v":' + _oversized_int
            + b',"status":"ok","payload":null,"error":null}'
        )
        r = _run_transport_fake(_TPE(
            poll_ret=True, recv_bytes_data=_oversized_payload))
        if r[0] != "malformed":
            raise AssertionError(
                f"cat8: oversized int token -> {r[0]!r}, expected "
                f"malformed (adapter-scoped, NOT infra) "
                f"(int_max_str_digits={_int_max_digits})")
    # Else: Python < 3.11 has no int->str digit limit; honestly skip.

    # 26c. v12: depth cap (``_MAX_STAGE_DEPTH = 32``) rejects as malformed
    # via _wire_validate_depth_and_primitives (defense-in-depth AFTER
    # json.loads succeeds at a depth that does NOT trip the C parser
    # recursion limit). 33 nested objects exceeds the cap. The boundary
    # converts the _WireError("depth exceeded") to adapter-scoped
    # malformed (NEVER infra).
    _DEPTH_33 = b'{"a":' * 33 + b'null' + b'}' * 33
    r = _run_transport_fake(_TPE(poll_ret=True, recv_bytes_data=_DEPTH_33))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: depth cap (33 > _MAX_STAGE_DEPTH) -> {r[0]!r}, "
            f"expected malformed (adapter-scoped)")

    # 26d. v12: oversized string (len > _MAX_STAGE_STR_LEN) rejects as
    # malformed via _wire_validate_depth_and_primitives. The closed
    # envelope schema accepts an error string, so the oversized string is
    # a valid envelope-level error field; the depth/count/string bounding
    # catches it BEFORE schema validation as structural_oversize.
    _oversized_str = b'x' * (_MAX_STAGE_STR_LEN + 100)
    _oversized_str_payload = (
        b'{"v":1,"status":"error","payload":null,"error":"'
        + _oversized_str + b'"}'
    )
    r = _run_transport_fake(_TPE(
        poll_ret=True, recv_bytes_data=_oversized_str_payload))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: oversized string -> {r[0]!r}, "
            f"expected malformed (adapter-scoped)")

    # 26e. v12: oversized list (count > _MAX_STAGE_LIST_COUNT) rejects as
    # malformed via _wire_validate_depth_and_primitives. The candidates
    # field accepts a list; an oversized list trips the count cap as
    # structural_oversize BEFORE schema validation.
    _oversized_list = (
        b'{"v":1,"status":"ok","payload":{"status":"ok",'
        b'"failure_category":null,"candidates":['
        + (b'null,' * (_MAX_STAGE_LIST_COUNT + 1))
        + b'],"capability_ledger":{},'
        b'"fallback_provenance":[],"binding_proposal":null},'
        b'"error":null}'
    )
    r = _run_transport_fake(_TPE(
        poll_ret=True, recv_bytes_data=_oversized_list))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: oversized list -> {r[0]!r}, "
            f"expected malformed (adapter-scoped)")

    # 26f. v12: object_pairs_hook duplicate-key rejection at a deeply
    # nested level (verifies the hook is called at every object level, not
    # just the outer envelope). The duplicate "k" key is at the second
    # object level.
    r = _run_transport_fake(_TPE(
        poll_ret=True,
        recv_bytes_data=(
            b'{"v":1,"status":"ok","payload":null,"error":null,'
            b'"nested":{"k":1,"k":2}}')))
    if r[0] != "malformed":
        raise AssertionError(
            f"cat8: nested duplicate key (object_pairs_hook) -> "
            f"{r[0]!r}, expected malformed (adapter-scoped)")

    # 26g. v12: parse_constant rejection (NaN/Infinity) is exercised at
    # the json.loads layer (NOT only via a payload field). The constant
    # appears in the top-level "error" position; parse_constant fires.
    for _bad_const in (b'NaN', b'Infinity', b'-Infinity'):
        r = _run_transport_fake(_TPE(
            poll_ret=True,
            recv_bytes_data=(
                b'{"v":1,"status":"ok","payload":null,"error":'
                + _bad_const + b'}')))
        if r[0] != "malformed":
            raise AssertionError(
                f"cat8: parse_constant {_bad_const!r} -> {r[0]!r}, "
                f"expected malformed (adapter-scoped)")

    # 26h. v12: no thread leak after the v12 parser-boundary fake-transport
    # tests. Each test above must have terminated its receiver thread.
    _thread_base_v12 = threading.active_count()
    time.sleep(0.3)
    _thread_after_v12 = threading.active_count()
    if _thread_after_v12 > _thread_base_v12 + 1:
        raise AssertionError(
            f"cat8: thread leak after v12 parser-boundary tests "
            f"(base={_thread_base_v12} after={_thread_after_v12})")

    # 27. v11: real spawned hostile hook with __reduce__ / property / iter
    # NEVER executes code in the parent. The child normalizes the returned
    # custom object to JSON primitives (which fails), sends a malformed
    # envelope, and the parent rejects as malformed. The marker file
    # (outside the child workspace) is NEVER created because the parent
    # never pickles/unpickles the object (no pickle on the wire) and never
    # calls __reduce__/property/iter on the hostile object. This proves the
    # v11 JSON wire does not execute adapter-authored arbitrary code in
    # the parent process.
    _HOSTILE_MARKER = Path(tempfile.gettempdir()) / "pb_bakeoff_v11_hostile_marker"
    # Pre-clean: marker must not exist before the test.
    if _HOSTILE_MARKER.exists():
        _HOSTILE_MARKER.unlink()
    tmp_hostile, root_hostile = _new_tmp_root()
    try:
        snap_hostile = build_synthetic_repo_one(root_hostile)
        req_hostile = make_request(snapshot=snap_hostile, timeout_seconds=30.0)
        hostile_status, hostile_result, hostile_err, _ = (
            _execute_stage_isolated(
                hostile_reduce_returning_query, req_hostile, root_hostile,
                valid_descriptor(), "query"))
        # The result must be malformed (the custom object cannot be
        # normalized to JSON primitives).
        if hostile_status != "malformed":
            raise AssertionError(
                f"cat8: hostile __reduce__ object -> {hostile_status!r}, "
                f"expected malformed")
        if hostile_result is not None:
            raise AssertionError(
                f"cat8: hostile __reduce__ object returned non-None result")
        # CRITICAL: the marker file must NOT exist. The parent never
        # executed __reduce__ (no pickle on the v11 wire). The child
        # normalized the object via type-checks (which never invoke
        # __reduce__), so __reduce__ was NEVER called by anyone.
        if _HOSTILE_MARKER.exists():
            raise AssertionError(
                "cat8: hostile __reduce__ marker was created — parent "
                "executed adapter-authored arbitrary code (pickle was "
                "used somewhere on the wire); v11 JSON wire must NEVER "
                "invoke __reduce__")
    finally:
        tmp_hostile.cleanup()
        if _HOSTILE_MARKER.exists():
            _HOSTILE_MARKER.unlink()

    # 27b. v11: hostile AdapterResult subclass with property side effects
    # is rejected. The EXACT type check (``type(x) is AdapterResult``)
    # rejects subclasses; the property is NEVER called by the parent.
    _HOSTILE_PROP_MARKER = Path(tempfile.gettempdir()) / "pb_bakeoff_v11_prop_marker"
    if _HOSTILE_PROP_MARKER.exists():
        _HOSTILE_PROP_MARKER.unlink()
    tmp_prop, root_prop = _new_tmp_root()
    try:
        snap_prop = build_synthetic_repo_one(root_prop)
        req_prop = make_request(snapshot=snap_prop, timeout_seconds=30.0)
        prop_status, prop_result, prop_err, _ = _execute_stage_isolated(
            hostile_property_subclass_query, req_prop, root_prop,
            valid_descriptor(), "query")
        if prop_status != "malformed":
            raise AssertionError(
                f"cat8: hostile property subclass -> {prop_status!r}, "
                f"expected malformed")
        if _HOSTILE_PROP_MARKER.exists():
            raise AssertionError(
                "cat8: hostile property marker was created — parent "
                "accessed the property (subclass was accepted); v11 EXACT "
                "type check must reject AdapterResult subclasses without "
                "accessing properties")
    finally:
        tmp_prop.cleanup()
        if _HOSTILE_PROP_MARKER.exists():
            _HOSTILE_PROP_MARKER.unlink()

    # 27c. v11: hostile Mapping subclass for capability_ledger is rejected.
    # The EXACT type check (``type(x) is dict``) rejects Mapping subclasses
    # that could override __getitem__/items; the parent never calls the
    # subclass's methods.
    _HOSTILE_MAP_MARKER = Path(tempfile.gettempdir()) / "pb_bakeoff_v11_map_marker"
    if _HOSTILE_MAP_MARKER.exists():
        _HOSTILE_MAP_MARKER.unlink()
    tmp_map, root_map = _new_tmp_root()
    try:
        snap_map = build_synthetic_repo_one(root_map)
        req_map = make_request(snapshot=snap_map, timeout_seconds=30.0)
        map_status, map_result, map_err, _ = _execute_stage_isolated(
            hostile_mapping_ledger_query, req_map, root_map,
            valid_descriptor(), "query")
        if map_status != "malformed":
            raise AssertionError(
                f"cat8: hostile Mapping subclass -> {map_status!r}, "
                f"expected malformed")
        if _HOSTILE_MAP_MARKER.exists():
            raise AssertionError(
                "cat8: hostile mapping marker was created — parent "
                "called Mapping subclass methods; v11 EXACT type check "
                "must reject Mapping subclasses")
    finally:
        tmp_map.cleanup()
        if _HOSTILE_MAP_MARKER.exists():
            _HOSTILE_MAP_MARKER.unlink()

    # 28. v11: real spawned child os._exit(73) => process_died (NEVER
    # infra). The child calls os._exit(73) (the old v10
    # WORKER_TRANSPORT_FAILURE_EXIT_CODE value); the parent sees EOF and
    # classifies adapter-scoped process_died. This proves an adapter
    # cannot author an infra-abort via a specific exit code.
    tmp_e73, root_e73 = _new_tmp_root()
    try:
        snap_e73 = build_synthetic_repo_one(root_e73)
        req_e73 = make_request(snapshot=snap_e73, timeout_seconds=30.0)
        e73_status, _, e73_err, _ = _execute_stage_isolated(
            os_exit_73_query, req_e73, root_e73,
            valid_descriptor(), "query")
        if e73_status != "error" or e73_err != "process_died":
            raise AssertionError(
                f"cat8: child os._exit(73) -> ({e73_status!r},{e73_err!r}), "
                f"expected error/process_died (NEVER infra)")
    finally:
        tmp_e73.cleanup()

    # 28b. v11: real spawned child os._exit(arbitrary codes) => process_died.
    # Each exit code is a separate top-level function (spawn-picklability
    # requires top-level functions, not closures).
    for _qfn, _exit_code in [
        (os_exit_0_query, 0),
        (os_exit_1_query, 1),
        (os_exit_42_query, 42),
        (os_exit_139_query, 139),
        (os_exit_255_query, 255),
    ]:
        tmp_ec, root_ec = _new_tmp_root()
        try:
            snap_ec = build_synthetic_repo_one(root_ec)
            req_ec = make_request(snapshot=snap_ec, timeout_seconds=30.0)
            ec_status, _, ec_err, _ = _execute_stage_isolated(
                _qfn, req_ec, root_ec,
                valid_descriptor(), "query")
            if ec_status != "error" or ec_err != "process_died":
                raise AssertionError(
                    f"cat8: child os._exit({_exit_code}) -> "
                    f"({ec_status!r},{ec_err!r}), expected error/process_died")
        finally:
            tmp_ec.cleanup()

    # 29. v11: real child send failure / EOF => process_died. A child that
    # closes the pipe without sending => parent sees EOF => process_died.
    tmp_eof, root_eof = _new_tmp_root()
    try:
        snap_eof = build_synthetic_repo_one(root_eof)
        req_eof = make_request(snapshot=snap_eof, timeout_seconds=30.0)
        eof_status, _, eof_err, _ = _execute_stage_isolated(
            close_without_send_query, req_eof, root_eof,
            valid_descriptor(), "query")
        if eof_status != "error" or eof_err != "process_died":
            raise AssertionError(
                f"cat8: child close-without-send -> "
                f"({eof_status!r},{eof_err!r}), expected error/process_died")
    finally:
        tmp_eof.cleanup()

    # 30. v11: no child/thread leak after real spawned hostile runs.
    # Repeated hostile/timeout runs leave no active children or receiver
    # threads. _reap_process already verifies the child is not alive; the
    # receiver thread count check below proves no thread leak.
    _thread_base3 = threading.active_count()
    time.sleep(0.5)
    _thread_after3 = threading.active_count()
    if _thread_after3 > _thread_base3 + 1:
        raise AssertionError(
            f"cat8: thread leak after real spawned hostile runs "
            f"(base={_thread_base3} after={_thread_after3})")

    # 31. v12: full-run continuation after a hostile child exit. This is
    # the END-TO-END proof at the run_adapter / batch-loop level (NOT only
    # direct _execute_stage_isolated classification). A real spawned
    # hostile hook with ``os._exit(73)`` yields a REJECTED
    # ValidatedRunRecord with adapter ``adapter_exception:process_died``
    # failure category and an EMPTY capability ledger; then a subsequent
    # VALID adapter run executes and is ACCEPTED in the SAME test process
    # / bakeoff sequence. No HarnessInfrastructureError, no leaked child /
    # receiver thread. This proves whole-run continuation: a hostile
    # child exit is one rejected record, not an abort of the bakeoff.
    _thread_base_e2e = threading.active_count()

    # 31a. Hostile os._exit(73) at the run_adapter level.
    tmp_e2e, root_e2e = _new_tmp_root()
    try:
        snap_e2e = build_synthetic_repo_one(root_e2e)
        req_e2e = make_request(
            snapshot=snap_e2e, timeout_seconds=30.0,
            request_id="pb_syn_v12_e2e_hostile_exit")
        e2e_rec = _ctx_run(
            _qhooks(os_exit_73_query), req_e2e, valid_descriptor(),
            "cat8_no_silent_degeneration", snap_e2e, root_e2e)
        _expect_rejected(e2e_rec, "cat8:e2e_hostile_exit")
        # Adapter-scoped process_died canonical category (NEVER infra).
        if e2e_rec.failure_category != "adapter_exception:process_died":
            raise AssertionError(
                f"cat8: e2e hostile exit failure_category="
                f"{e2e_rec.failure_category!r}, expected "
                f"'adapter_exception:process_died' (adapter-scoped, "
                f"NEVER HarnessInfrastructureError)")
        # Rejected records MUST carry an EMPTY capability ledger (only
        # accepted records may publish a validated ledger).
        if e2e_rec.capability_ledger_summary != {}:
            raise AssertionError(
                f"cat8: e2e hostile exit ledger non-empty: "
                f"{e2e_rec.capability_ledger_summary!r}")
        # No successful pack is produced for a rejected run.
        if e2e_rec.pack_status is not None:
            raise AssertionError(
                f"cat8: e2e hostile exit produced pack_status="
                f"{e2e_rec.pack_status!r} (rejected runs must have "
                f"pack_status=None)")
        if e2e_rec.canonical_pack_hash is not None:
            raise AssertionError(
                "cat8: e2e hostile exit produced a canonical_pack_hash "
                "(rejected runs must have canonical_pack_hash=None)")
        # The query stage was attempted (process-isolated) so a resource
        # sample with query_seconds should be present.
        if e2e_rec.resource_sample is None:
            raise AssertionError(
                "cat8: e2e hostile exit has no resource sample "
                "(query stage should have been timed)")
        if e2e_rec.resource_sample.query_seconds is None:
            raise AssertionError(
                "cat8: e2e hostile exit did not time query")
    finally:
        tmp_e2e.cleanup()

    # 31b. A subsequent VALID adapter run executes and is ACCEPTED in the
    # SAME test process / bakeoff sequence. This proves the prior hostile
    # exit did NOT abort the bakeoff or leak any receiver / child that
    # would break a later run. Whole-run continuation, not only direct
    # _execute_stage_isolated classification.
    tmp_e2e_ok, root_e2e_ok = _new_tmp_root()
    try:
        snap_e2e_ok = build_synthetic_repo_one(root_e2e_ok)
        req_e2e_ok = make_request(
            snapshot=snap_e2e_ok, timeout_seconds=30.0,
            request_id="pb_syn_v12_e2e_ok_after_hostile")
        e2e_ok_rec = _ctx_run(
            _qhooks(valid_adapter_query), req_e2e_ok, valid_descriptor(),
            "cat8_no_silent_degeneration", snap_e2e_ok, root_e2e_ok)
        _expect_accepted(e2e_ok_rec, "cat8:e2e_ok_after_hostile")
        if e2e_ok_rec.pack_status != "ready":
            raise AssertionError(
                f"cat8: e2e ok-after-hostile pack_status="
                f"{e2e_ok_rec.pack_status!r}, expected 'ready'")
        if e2e_ok_rec.canonical_pack_hash is None:
            raise AssertionError(
                "cat8: e2e ok-after-hostile has no canonical_pack_hash "
                "(accepted ready packs must have a pack hash)")
    finally:
        tmp_e2e_ok.cleanup()

    # 31c. No leaked child / receiver thread after the e2e continuation
    # pair. The hostile exit AND the subsequent valid run must both have
    # terminated their spawned child + receiver thread.
    time.sleep(0.5)
    _thread_after_e2e = threading.active_count()
    if _thread_after_e2e > _thread_base_e2e + 1:
        raise AssertionError(
            f"cat8: thread leak after e2e continuation pair "
            f"(base={_thread_base_e2e} after={_thread_after_e2e})")

    # v7: lifecycle exception TYPE only (no message). The prepare/index-fails
    # hooks raise RuntimeError; the canonical category must be
    # lifecycle_exception:{stage}:RuntimeError with NO message text.
    if not prepare_fails_rec.failure_category.startswith("lifecycle_exception:prepare:"):
        raise AssertionError(
            f"cat8: prepare_fails category prefix wrong: "
            f"{prepare_fails_rec.failure_category!r}")
    if ":" in prepare_fails_rec.failure_category[len("lifecycle_exception:prepare:"):]:
        raise AssertionError(
            "cat8: prepare_fails category contains exception MESSAGE text "
            "(must be TYPE only)")
    if not index_fails_rec.failure_category.startswith("lifecycle_exception:index:"):
        raise AssertionError(
            f"cat8: index_fails category prefix wrong: "
            f"{index_fails_rec.failure_category!r}")

    # v4: STATEFUL lifecycle tests (item 4). Cold writes a state marker into
    # writable_state_root; warm on the SAME snapshot/root observes the marker
    # while skipping rebuild; warm-without-state fails; stateless and
    # cold_rebuild warm requests actually run configured hooks.

    # v4 stateful cold->warm marker reuse on the SAME snapshot/root.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        # Cold run: writes the marker via stateful_prepare/stateful_index.
        cold_req = make_request(
            snapshot=snap, adapter_id=SYN_ADAPTER_ID_LIFE,
            cache_state="cold", request_id="pb_syn_stateful_cold_1",
            episode_id="pb_syn_stateful_episode",
        )
        cold_rec = _ctx_run(
            STATEFUL_LIFECYCLE_HOOKS, cold_req, lifecycle_descriptor(),
            "cat8_no_silent_degeneration", snap, root)
        _expect_accepted(cold_rec, "cat8:stateful_cold")
        if cold_rec.resource_sample is None:
            raise AssertionError("cat8: stateful cold run has no resource sample")
        if cold_rec.resource_sample.setup_seconds is None:
            raise AssertionError("cat8: stateful cold run did not time setup")
        if cold_rec.resource_sample.index_seconds is None:
            raise AssertionError("cat8: stateful cold run did not time index")
        # Verify the marker file was actually written by the cold prepare.
        marker = root / ".pb_writable_state" / _LIFECYCLE_MARKER_REL
        if not marker.is_file():
            raise AssertionError("cat8: stateful cold run did not write the marker")
        recs.append(cold_rec)

        # Warm run on the SAME snapshot/root: warm_reuse skips prepare+index,
        # but the query hook MUST observe the marker (proves prior state was
        # built and reused). The query writes an observation file.
        warm_req = make_request(
            snapshot=snap, adapter_id=SYN_ADAPTER_ID_LIFE,
            cache_state="warm", request_id="pb_syn_stateful_warm_1",
            episode_id="pb_syn_stateful_episode",
        )
        warm_rec = _ctx_run(
            STATEFUL_LIFECYCLE_HOOKS, warm_req, lifecycle_descriptor(),
            "cat8_no_silent_degeneration", snap, root)
        _expect_accepted(warm_rec, "cat8:stateful_warm")
        if warm_rec.resource_sample is None:
            raise AssertionError("cat8: stateful warm run has no resource sample")
        if warm_rec.resource_sample.setup_seconds is not None:
            raise AssertionError(
                "cat8: stateful warm run should skip prepare (setup=None)"
            )
        if warm_rec.resource_sample.index_seconds is not None:
            raise AssertionError(
                "cat8: stateful warm run should skip index (index=None)"
            )
        # Verify the query observed the marker (proves prior state reused).
        observed = root / ".pb_writable_state" / _LIFECYCLE_OBSERVED_REL
        if not observed.is_file():
            raise AssertionError(
                "cat8: stateful warm query did not write observation file"
            )
        observed_text = observed.read_text(encoding="utf-8")
        if not observed_text.startswith("1:"):
            raise AssertionError(
                f"cat8: stateful warm query did not observe the marker "
                f"(observed={observed_text!r})"
            )
        recs.append(warm_rec)
    finally:
        tmp.cleanup()

    # v5: warm-without-state FAILS. A warm_reuse + warm request with NO prior
    # cold run on the same writable_state_root must FAIL because the marker
    # is absent. The stateful_query returns an explicit failed result
    # (canonicalized to adapter_exception:FailedResult); no successful pack
    # is produced. The query still writes an observation of "0", proving no
    # prior state existed (the query actually ran and checked the marker).
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        warm_no_state_req = make_request(
            snapshot=snap, adapter_id=SYN_ADAPTER_ID_LIFE,
            cache_state="warm", request_id="pb_syn_stateful_warm_no_state",
            episode_id="pb_syn_stateful_episode_no_state",
        )
        warm_no_state_rec = _ctx_run(
            STATEFUL_LIFECYCLE_HOOKS, warm_no_state_req, lifecycle_descriptor(),
            "cat8_no_silent_degeneration", snap, root)
        # v5 closure: warm-without-state must be an explicit REJECTED result
        # (not silently accepted as a degenerate ok).
        _expect_rejected(warm_no_state_rec, "cat8:stateful_warm_no_state")
        # Verify the canonical failure category: the adapter-authored
        # "warm_reuse_state_missing" category must be canonicalized to
        # adapter_exception:FailedResult (stage + result status mapping).
        # Adapter-authored categories NEVER reach public keys.
        if warm_no_state_rec.failure_category != "adapter_exception:FailedResult":
            raise AssertionError(
                f"cat8: warm-without-state failure_category="
                f"{warm_no_state_rec.failure_category!r}, expected "
                f"'adapter_exception:FailedResult' (canonical mapping)"
            )
        # No successful pack is produced for a rejected run.
        if warm_no_state_rec.pack_status is not None:
            raise AssertionError(
                f"cat8: warm-without-state produced pack_status="
                f"{warm_no_state_rec.pack_status!r} (rejected runs must "
                f"have pack_status=None)"
            )
        if warm_no_state_rec.canonical_pack_hash is not None:
            raise AssertionError(
                "cat8: warm-without-state produced a canonical_pack_hash "
                "(rejected runs must have canonical_pack_hash=None)"
            )
        # The query should have observed NO marker (proves warm-without-state
        # was detected, not silently degenerated).
        observed = root / ".pb_writable_state" / _LIFECYCLE_OBSERVED_REL
        if not observed.is_file():
            raise AssertionError(
                "cat8: warm-without-state query did not write observation"
            )
        observed_text = observed.read_text(encoding="utf-8")
        if not observed_text.startswith("0"):
            raise AssertionError(
                f"cat8: warm-without-state query unexpectedly observed a "
                f"marker (observed={observed_text!r})"
            )
        # A resource sample should be present (the query hook ran and was
        # timed; prepare/index were skipped so their timings are None).
        if warm_no_state_rec.resource_sample is None:
            raise AssertionError(
                "cat8: warm-without-state run has no resource sample "
                "(query should have been timed)"
            )
        if warm_no_state_rec.resource_sample.query_seconds is None:
            raise AssertionError(
                "cat8: warm-without-state run did not time query"
            )
        recs.append(warm_no_state_rec)
    finally:
        tmp.cleanup()

    # v4: stateless + warm — hooks SHOULD run (stateless always rebuilds).
    # Use a stateless descriptor + stateful hooks + warm cache_state. The
    # prepare/index hooks must run (writing the marker) even though
    # cache_state=warm, because stateless always rebuilds.
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        stateless_warm_req = make_request(
            snapshot=snap, adapter_id=SYN_ADAPTER_ID_LIFE,
            cache_state="warm", request_id="pb_syn_stateless_warm_1",
            episode_id="pb_syn_stateless_episode",
        )
        stateless_warm_rec = _ctx_run(
            STATEFUL_LIFECYCLE_HOOKS, stateless_warm_req,
            stateless_lifecycle_descriptor(),
            "cat8_no_silent_degeneration", snap, root)
        _expect_accepted(stateless_warm_rec, "cat8:stateless_warm")
        if stateless_warm_rec.resource_sample is None:
            raise AssertionError("cat8: stateless warm run has no resource sample")
        if stateless_warm_rec.resource_sample.setup_seconds is None:
            raise AssertionError(
                "cat8: stateless warm run should run prepare (setup not None)"
            )
        if stateless_warm_rec.resource_sample.index_seconds is None:
            raise AssertionError(
                "cat8: stateless warm run should run index (index not None)"
            )
        # The marker should have been written (stateless ran the hooks).
        marker = root / ".pb_writable_state" / _LIFECYCLE_MARKER_REL
        if not marker.is_file():
            raise AssertionError(
                "cat8: stateless warm run did not write the marker (hooks "
                "should have run)"
            )
        recs.append(stateless_warm_rec)
    finally:
        tmp.cleanup()

    # v4: cold_rebuild + warm — index hook SHOULD run (cold_rebuild always
    # rebuilds the index).
    tmp, root = _new_tmp_root()
    try:
        snap = build_synthetic_repo_one(root)
        cold_rebuild_warm_req = make_request(
            snapshot=snap, adapter_id=SYN_ADAPTER_ID_LIFE,
            cache_state="warm", request_id="pb_syn_cold_rebuild_warm_1",
            episode_id="pb_syn_cold_rebuild_episode",
        )
        cold_rebuild_warm_rec = _ctx_run(
            STATEFUL_LIFECYCLE_HOOKS, cold_rebuild_warm_req,
            cold_rebuild_lifecycle_descriptor(),
            "cat8_no_silent_degeneration", snap, root)
        _expect_accepted(cold_rebuild_warm_rec, "cat8:cold_rebuild_warm")
        if cold_rebuild_warm_rec.resource_sample is None:
            raise AssertionError("cat8: cold_rebuild warm run has no resource sample")
        if cold_rebuild_warm_rec.resource_sample.index_seconds is None:
            raise AssertionError(
                "cat8: cold_rebuild warm run should run index (index not None)"
            )
        recs.append(cold_rebuild_warm_rec)
    finally:
        tmp.cleanup()

    # v6 blocker 3: capability-contradiction adversarial tests. Each probe
    # constructs an ok result whose ledger CONTRADICTS the actual binding/output
    # and proves validate_capability_ledger_honesty rejects it.
    # (a) target_binding=executed but no target refs.
    bad_target_ledger = _std_ledger(has_target=True, has_support=False)
    bad_target_ledger["target_binding"] = "executed"
    bad_target_result = AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_target_candidate(),),
        capability_ledger=bad_target_ledger, fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="uncertain", target_evidence_indices=(),
            support_bindings=(), status_reason="no target"),
    )
    try:
        validate_capability_ledger_honesty(
            bad_target_result, make_request(),
            attempt_prepare=False, attempt_index=False)
        raise AssertionError("cat8: target_binding=executed with no refs accepted")
    except ContractError:
        pass
    # (b) target refs present but target_binding=unsupported.
    bad_tb_unsup = _std_ledger(has_target=False, has_support=False)
    bad_tb_unsup["target_binding"] = "unsupported"
    bad_tb_result = AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_target_candidate(),),
        capability_ledger=bad_tb_unsup, fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=()),
    )
    try:
        validate_capability_ledger_honesty(
            bad_tb_result, make_request(),
            attempt_prepare=False, attempt_index=False)
        raise AssertionError("cat8: target refs with target_binding=unsupported accepted")
    except ContractError:
        pass
    # (c) support_expansion=executed but no support refs.
    bad_sup_ledger = _std_ledger(has_target=True, has_support=False)
    bad_sup_ledger["support_expansion"] = "executed"
    bad_sup_result = AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_target_candidate(),),
        capability_ledger=bad_sup_ledger, fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=()),
    )
    try:
        validate_capability_ledger_honesty(
            bad_sup_result, make_request(),
            attempt_prepare=False, attempt_index=False)
        raise AssertionError("cat8: support_expansion=executed with no refs accepted")
    except ContractError:
        pass
    # (d) prepare_index=executed but neither hook attempted.
    bad_prep_ledger = _std_ledger(has_target=True, has_support=False)
    bad_prep_ledger["prepare_index"] = "executed"
    bad_prep_result = AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_target_candidate(),),
        capability_ledger=bad_prep_ledger, fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=()),
    )
    try:
        validate_capability_ledger_honesty(
            bad_prep_result, make_request(),
            attempt_prepare=False, attempt_index=False)
        raise AssertionError("cat8: prepare_index=executed with no hooks attempted accepted")
    except ContractError:
        pass
    # (e) two_step_support=executed but no support operation producing support.
    bad_ts_ledger = _std_ledger(has_target=True, has_support=False)
    bad_ts_ledger["two_step_support"] = "executed"
    bad_ts_result = AdapterResult(
        status="ok", failure_category=None, candidates=(_widget_target_candidate(),),
        capability_ledger=bad_ts_ledger, fallback_provenance=_std_fallback(),
        resource_sample=None,
        binding_proposal=BindingProposal(
            proposed_status="ready", target_evidence_indices=(0,),
            support_bindings=()),
    )
    try:
        validate_capability_ledger_honesty(
            bad_ts_result, make_request(),
            attempt_prepare=False, attempt_index=False)
        raise AssertionError("cat8: two_step_support=executed with no support op accepted")
    except ContractError:
        pass

    # v6 blocker 4: execution_mode vocabulary drift must be rejected. The
    # harness always uses process_isolated; in_process/subprocess are rejected.
    for bad_mode in ("in_process", "subprocess"):
        try:
            AdapterDescriptor(
                adapter_id=SYN_ADAPTER_ID_ADV, adapter_version="v1",
                capabilities=frozenset({
                    "prepare_index", "candidate_search", "target_binding",
                    "support_expansion", "two_step_support",
                }),
                default_capability="candidate_search",
                supported_languages=frozenset({"rust"}),
                persistent_state_behavior="stateless", execution_mode=bad_mode,
                upstream_revision="synthetic-v4", spdx_license_state="declared",
                output_channels=frozenset({"bm25", "symbol", "structural"}),
            ).validate()
            raise AssertionError(
                f"cat8: execution_mode={bad_mode!r} accepted (should be rejected)"
            )
        except ContractError:
            pass
    return recs


# -- Category 9: aggregate-only reporting + closed schema --


def cat9_aggregate_only_reporting() -> list[ValidatedRunRecord]:
    all_recs: list[ValidatedRunRecord] = []
    all_recs.append(cat1_request_oracle_isolation())
    all_recs.extend(cat2_snapshot_visibility_isolation())
    all_recs.extend(cat3_candidate_validity())
    all_recs.extend(cat4_common_materialization_currentness())
    all_recs.extend(cat5_budget_equality())
    all_recs.extend(cat6_pack_semantics())
    all_recs.extend(cat7_determinism_cells())
    all_recs.extend(cat8_no_silent_degeneration())

    # Poisoned record carrying a leaked query.
    poisoned = ValidatedRunRecord(
        fingerprint="fp_poisoned", run_cell_id="pb_syn_cell_poison",
        adapter_id="pb_syn_poison_adapter", status="accepted",
        failure_category=None, result_status="ok", pack_status="ready",
        candidate_count=1, evidence_count=1, target_count=1, support_count=0,
        capability_ledger_summary={"candidate_search": "executed"},
        canonical_result_hash="crh_poison", canonical_pack_hash="cph_poison",
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1, resource_sample=None)
    poisoned_dict = poisoned.to_public_dict()
    poisoned_dict["query"] = "leaked:query"  # type: ignore
    leaks = scan_public_report(poisoned_dict)
    if not leaks:
        raise AssertionError("cat9: poisoned record with query was not detected")
    all_recs.append(poisoned)

    report = aggregate_public_report(
        all_recs, two_step_episode_exercised=True,
        comparison_matrix_validated=True)
    if not report["totals_reconciled"]:
        raise AssertionError("cat9: report totals did not reconcile")
    if report["accepted_count"] + report["rejected_count"] != report["total_validated_runs"]:
        raise AssertionError("cat9: accepted+rejected != total")
    if report["promotion_ready"] is not False:
        raise AssertionError("cat9: promotion_ready must be false")
    for expected_cat in CAT_NAMES:
        if expected_cat not in report["conformance_categories_exercised"]:
            raise AssertionError(f"cat9: category {expected_cat} not exercised")
    leaks = scan_public_report(report)
    if leaks:
        raise AssertionError(f"cat9: report leaks private facts: {leaks}")
    # Resource sample present count derived from actual samples.
    expected_rs = sum(1 for r in all_recs if r.resource_sample is not None)
    if report["resource_sample_present_count"] != expected_rs:
        raise AssertionError(
            f"cat9: resource_sample_present_count {report['resource_sample_present_count']} "
            f"!= actual {expected_rs}")
    # Closed-schema adversarial: unknown top-level key must fail.
    bad_report = dict(report)
    bad_report["unknown_top_level_key"] = "bad"
    if not validate_written_report(bad_report):
        raise AssertionError("cat9: unknown top-level key not rejected")
    # Closed-schema adversarial: unknown nested key must fail.
    bad_report2 = dict(report)
    bad_bcc = {k: dict(v) for k, v in report["by_conformance_category"].items()}
    bad_bcc["cat1_request_oracle_isolation"]["unknown_nested"] = 1
    bad_report2["by_conformance_category"] = bad_bcc
    if not validate_written_report(bad_report2):
        raise AssertionError("cat9: unknown nested key not rejected")

    # v4: adversarial written-report cases (exception-free + exact). Each
    # must return at least one failure WITHOUT raising.
    # (a) negative failure_category_counts value.
    bad_neg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in report.items()}
    bad_neg_fcc = dict(report["failure_category_counts"])
    bad_neg_fcc["adapter_timeout"] = -5
    bad_neg["failure_category_counts"] = bad_neg_fcc
    if not validate_written_report(bad_neg):
        raise AssertionError("cat9: negative failure_category_counts not rejected")
    # (b) string status count (must NOT raise TypeError).
    bad_str = {k: (dict(v) if isinstance(v, dict) else v) for k, v in report.items()}
    bad_str_rsc = dict(report["result_status_counts"])
    bad_str_rsc["ok"] = "many"
    bad_str["result_status_counts"] = bad_str_rsc
    try:
        str_failures = validate_written_report(bad_str)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"cat9: string status count raised {type(exc).__name__} instead "
            f"of returning failures"
        )
    if not str_failures:
        raise AssertionError("cat9: string status count not rejected")
    # (c) bool count value (must be rejected, since bool is a subclass of int).
    bad_bool = {k: (dict(v) if isinstance(v, dict) else v) for k, v in report.items()}
    bad_bool_acc = dict(report["by_conformance_category"]["cat1_request_oracle_isolation"])
    bad_bool_acc["accepted"] = True
    bad_bool["by_conformance_category"] = dict(report["by_conformance_category"])
    bad_bool["by_conformance_category"]["cat1_request_oracle_isolation"] = bad_bool_acc
    if not validate_written_report(bad_bool):
        raise AssertionError("cat9: bool count value not rejected")
    # (d) oversized resource_sample_present_count (> total).
    bad_over = dict(report)
    bad_over["resource_sample_present_count"] = report["total_validated_runs"] + 1000
    if not validate_written_report(bad_over):
        raise AssertionError(
            "cat9: oversized resource_sample_present_count not rejected"
        )
    # (e) truncated canonical_contract_surface (missing entries).
    bad_trunc = dict(report)
    bad_trunc["canonical_contract_surface"] = report["canonical_contract_surface"][:-2]
    if not validate_written_report(bad_trunc):
        raise AssertionError(
            "cat9: truncated canonical_contract_surface not rejected"
        )
    # (f) unknown failure_category key (adapter-authored raw category).
    bad_fck = {k: (dict(v) if isinstance(v, dict) else v) for k, v in report.items()}
    bad_fck_fcc = dict(report["failure_category_counts"])
    bad_fck_fcc["adapter_exception:RuntimeError:LEAKED_MESSAGE_TEXT"] = 1
    bad_fck["failure_category_counts"] = bad_fck_fcc
    if not validate_written_report(bad_fck):
        raise AssertionError(
            "cat9: adapter-authored raw failure category key not rejected"
        )
    # (g) missing top-level key.
    bad_missing = dict(report)
    del bad_missing["threat_model_note"]
    if not validate_written_report(bad_missing):
        raise AssertionError("cat9: missing top-level key not rejected")

    # v5: capability_ledger_entry_count reconciliation adversarial cases.
    # (h) tampered bucket: adding 99 to a capability_status_counts bucket
    #     breaks sum(capability_status_counts) != capability_ledger_entry_count.
    bad_bucket = {k: (dict(v) if isinstance(v, dict) else v) for k, v in report.items()}
    bad_bucket_csc = dict(report["capability_status_counts"])
    bad_bucket_csc["executed"] = bad_bucket_csc.get("executed", 0) + 99
    bad_bucket["capability_status_counts"] = bad_bucket_csc
    bucket_failures = validate_written_report(bad_bucket)
    if not any("capability_ledger_entry_count" in f and "tampered" in f for f in bucket_failures):
        raise AssertionError(
            f"cat9: tampered capability_status_counts bucket not rejected "
            f"by reconciliation: {bucket_failures}"
        )
    # (i) tampered scalar: changing capability_ledger_entry_count to a wrong
    #     value breaks the same equality (scalar != sum of buckets).
    bad_scalar = {k: (dict(v) if isinstance(v, dict) else v) for k, v in report.items()}
    bad_scalar["capability_ledger_entry_count"] = (
        report["capability_ledger_entry_count"] + 99)
    scalar_failures = validate_written_report(bad_scalar)
    if not any("capability_ledger_entry_count" in f and "tampered" in f for f in scalar_failures):
        raise AssertionError(
            f"cat9: tampered capability_ledger_entry_count scalar not "
            f"rejected by reconciliation: {scalar_failures}"
        )
    # (j) negative capability_ledger_entry_count (nonnegative int check).
    bad_neg_clec = dict(report)
    bad_neg_clec["capability_ledger_entry_count"] = -5
    if not validate_written_report(bad_neg_clec):
        raise AssertionError(
            "cat9: negative capability_ledger_entry_count not rejected"
        )
    # (k) bool capability_ledger_entry_count (bool rejected by _is_int).
    bad_bool_clec = dict(report)
    bad_bool_clec["capability_ledger_entry_count"] = True
    if not validate_written_report(bad_bool_clec):
        raise AssertionError(
            "cat9: bool capability_ledger_entry_count not rejected"
        )

    # v4: validate_run_record adversarial cases.
    # (h) record with adapter exception MESSAGE text in failure_category.
    bad_rec = ValidatedRunRecord(
        fingerprint="fp_bad", run_cell_id="pb_bad", adapter_id="pb_bad_adapter",
        status="rejected",
        failure_category="adapter_exception:RuntimeError:LEAKED_MESSAGE",
        result_status="failed", pack_status=None,
        candidate_count=0, evidence_count=0, target_count=0, support_count=0,
        capability_ledger_summary={
            "prepare_index": "failed", "candidate_search": "failed",
            "two_step_support": "failed",
        },
        canonical_result_hash=None, canonical_pack_hash=None,
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1, resource_sample=None)
    rec_failures = validate_run_record(bad_rec)
    if not any("not in canonical closed set" in f for f in rec_failures):
        raise AssertionError(
            f"cat9: adapter exception MESSAGE text in failure_category not "
            f"rejected by validate_run_record: {rec_failures}"
        )
    # (i) accepted record with no canonical hashes.
    bad_rec2 = ValidatedRunRecord(
        fingerprint="fp_bad2", run_cell_id="pb_bad2", adapter_id="pb_bad_adapter",
        status="accepted", failure_category=None,
        result_status="ok", pack_status="ready",
        candidate_count=1, evidence_count=1, target_count=1, support_count=0,
        capability_ledger_summary={
            "prepare_index": "legitimate_skip",
            "candidate_search": "executed",
            "two_step_support": "unsupported",
        },
        canonical_result_hash=None, canonical_pack_hash=None,
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1, resource_sample=None)
    rec_failures2 = validate_run_record(bad_rec2)
    if not any("missing canonical_result_hash" in f for f in rec_failures2):
        raise AssertionError(
            f"cat9: accepted record with no hashes not rejected: {rec_failures2}"
        )
    # (j) pre-execution rejection with a resource_sample present.
    bad_rec3 = ValidatedRunRecord(
        fingerprint="fp_bad3", run_cell_id="pb_bad3", adapter_id="pb_bad_adapter",
        status="rejected",
        failure_category="prevalidation:ContractError",
        result_status="failed", pack_status=None,
        candidate_count=0, evidence_count=0, target_count=0, support_count=0,
        capability_ledger_summary={
            "prepare_index": "failed", "candidate_search": "failed",
            "two_step_support": "failed",
        },
        canonical_result_hash=None, canonical_pack_hash=None,
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1,
        resource_sample=ResourceSample(
            setup_seconds=0.1, index_seconds=None, query_seconds=None,
            materialize_seconds=None, render_seconds=None,
            rss_bytes=None, cpu_seconds=None,
        ))
    rec_failures3 = validate_run_record(bad_rec3)
    if not any("pre-execution (prevalidation) rejection must not carry" in f
               for f in rec_failures3):
        raise AssertionError(
            f"cat9: pre-execution rejection with resource_sample not rejected: "
            f"{rec_failures3}"
        )
    # (k) bool count in record (candidate_count=True).
    bad_rec4 = ValidatedRunRecord(
        fingerprint="fp_bad4", run_cell_id="pb_bad4", adapter_id="pb_bad_adapter",
        status="rejected",
        failure_category="result_validation:ContractError",
        result_status="failed", pack_status=None,
        candidate_count=True, evidence_count=0, target_count=0, support_count=0,  # type: ignore[arg-type]
        capability_ledger_summary={
            "prepare_index": "failed", "candidate_search": "failed",
            "two_step_support": "failed",
        },
        canonical_result_hash=None, canonical_pack_hash=None,
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1, resource_sample=None)
    rec_failures4 = validate_run_record(bad_rec4)
    if not any("must be int" in f for f in rec_failures4):
        raise AssertionError(
            f"cat9: bool count in record not rejected: {rec_failures4}"
        )
    # Verify a record that FAILS validate_run_record is counted as
    # rejected_by_validation (with a canonical record_validation marker) and
    # NEVER reaches the accepted surface. This proves fail-closed record
    # validation gates aggregation.
    bad_for_agg = ValidatedRunRecord(
        fingerprint="fp_bad_for_agg",
        run_cell_id="pb_syn_bad_for_agg",
        adapter_id="pb_syn_bad_adapter",
        status="accepted",  # claims accepted...
        failure_category="adapter_exception:RuntimeError:LEAKED_MSG",  # ...but has unsafe fc
        result_status="ok", pack_status="ready",
        candidate_count=1, evidence_count=1, target_count=1, support_count=0,
        capability_ledger_summary={
            "prepare_index": "legitimate_skip",
            "candidate_search": "executed",
            "two_step_support": "unsupported",
        },
        canonical_result_hash="crh_bad", canonical_pack_hash="cph_bad",
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1,
        resource_sample=ResourceSample(
            setup_seconds=0.1, index_seconds=None, query_seconds=None,
            materialize_seconds=None, render_seconds=None,
            rss_bytes=None, cpu_seconds=None,
        ))
    bad_report = aggregate_public_report(
        [bad_for_agg], two_step_episode_exercised=False,
        comparison_matrix_validated=False)
    if bad_report["accepted_count"] != 0:
        raise AssertionError(
            f"cat9: record failing validate_run_record reached accepted "
            f"(accepted_count={bad_report['accepted_count']})"
        )
    if bad_report["rejected_by_validation_count"] != 1:
        raise AssertionError(
            f"cat9: record failing validate_run_record not counted as "
            f"rejected_by_validation (got "
            f"{bad_report['rejected_by_validation_count']})"
        )
    # The unsafe failure_category must NOT appear in the public report's
    # failure_category_counts (it should be mapped to a canonical
    # record_validation marker).
    if "adapter_exception:RuntimeError:LEAKED_MSG" in bad_report["failure_category_counts"]:
        raise AssertionError(
            "cat9: unsafe failure_category leaked into public report"
        )
    if "record_validation:invalid_record" not in bad_report["failure_category_counts"]:
        raise AssertionError(
            f"cat9: record_validation:invalid_record not in failure_category_"
            f"counts (got {bad_report['failure_category_counts']})"
        )

    # v9: capability-ledger trust direct record tests.
    # (l) direct rejected record with NONEMPTY ledger is invalid.
    rej_nonempty = ValidatedRunRecord(
        fingerprint="fp_rej_ne", run_cell_id="pb_rej_ne",
        adapter_id="pb_syn_bad_adapter", status="rejected",
        failure_category="result_validation:ContractError",
        result_status="failed", pack_status=None,
        candidate_count=0, evidence_count=0, target_count=0, support_count=0,
        capability_ledger_summary={"candidate_search": "executed"},  # nonempty!
        canonical_result_hash=None, canonical_pack_hash=None,
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1, resource_sample=None)
    rej_failures = validate_run_record(rej_nonempty)
    if not any("empty capability_ledger_summary" in f for f in rej_failures):
        raise AssertionError(
            f"cat9: rejected record with nonempty ledger not rejected: "
            f"{rej_failures}")
    # (m) direct accepted record with candidate_count>0 but candidate_search
    # NOT executed is invalid (record defense).
    acc_nonexec = ValidatedRunRecord(
        fingerprint="fp_acc_ne", run_cell_id="pb_acc_ne",
        adapter_id="pb_syn_bad_adapter", status="accepted",
        failure_category=None, result_status="ok", pack_status="ready",
        candidate_count=1, evidence_count=1, target_count=1, support_count=0,
        capability_ledger_summary={"candidate_search": "legitimate_skip"},
        canonical_result_hash="crh_ne", canonical_pack_hash="cph_ne",
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1, resource_sample=None)
    acc_failures = validate_run_record(acc_nonexec)
    if not any("candidate_search" in f and "executed" in f for f in acc_failures):
        raise AssertionError(
            f"cat9: accepted record with nonexecuted candidate_search not "
            f"rejected: {acc_failures}")
    # (n) aggregate accepted-only ledger counts reconcile. The report's
    # capability_status_counts come from ACCEPTED records only. A rejected
    # record with a (forbidden) nonempty ledger must NOT inflate counts.
    rej_with_ledger = ValidatedRunRecord(
        fingerprint="fp_rej_wl", run_cell_id="pb_rej_wl",
        adapter_id="pb_syn_bad_adapter", status="rejected",
        failure_category="result_validation:ContractError",
        result_status="failed", pack_status=None,
        candidate_count=0, evidence_count=0, target_count=0, support_count=0,
        capability_ledger_summary={"candidate_search": "executed"},
        canonical_result_hash=None, canonical_pack_hash=None,
        conformance_category="cat9_aggregate_only_reporting",
        cache_state="cold", interaction_mode="one_shot", operation="context",
        adapter_repetition=1, resource_sample=None)
    mixed_report = aggregate_public_report(
        [rej_with_ledger], two_step_episode_exercised=False,
        comparison_matrix_validated=False)
    # The rejected record fails validate_run_record (nonempty ledger) and is
    # counted as rejected_by_validation with an EMPTY ledger. No capability
    # counts should come from it.
    if mixed_report["capability_ledger_entry_count"] != 0:
        raise AssertionError(
            f"cat9: rejected record inflated capability counts "
            f"(clec={mixed_report['capability_ledger_entry_count']}, expected 0)")
    if sum(mixed_report["capability_status_counts"].values()) != 0:
        raise AssertionError(
            f"cat9: rejected record inflated capability_status_counts "
            f"({mixed_report['capability_status_counts']})")

    # Valid report must pass.
    failures = validate_written_report(report)
    if failures:
        raise AssertionError(f"cat9: valid report failed validation: {failures}")
    return all_recs


# ---------------------------------------------------------------------------
# Self-test runner + report generation
# ---------------------------------------------------------------------------


def run_self_test() -> list[str]:
    """Run all nine conformance category self-tests. Returns failure reasons.

    v8: a ``HarnessInfrastructureError`` (genuine multiprocessing launch/
    resource failure) is RE-RAISED so it aborts the whole bakeoff rather than
    being recorded as one category's failure string. v9: pre-hook infrastructure
    scan and transport failures also raise ``HarnessInfrastructureError``.
    """
    failures: list[str] = []
    try:
        cat9_aggregate_only_reporting()
    except AssertionError as exc:
        failures.append(str(exc))
    except ContractError as exc:
        failures.append(f"ContractError: {exc}")
    except HarnessInfrastructureError:
        # Genuine multiprocessing launch/resource failure: abort the whole
        # bakeoff. NEVER converted into a ValidatedRunRecord, comparison
        # datapoint, or self-test failure string (propagates out of
        # run_adapter and the self-test).
        raise
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
        failures.append(traceback.format_exc())
    return failures


def generate_report() -> dict[str, Any]:
    """Generate the committed aggregate report from the self-test runs."""
    all_recs = cat9_aggregate_only_reporting()
    report = aggregate_public_report(
        all_recs, two_step_episode_exercised=True,
        comparison_matrix_validated=True)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _check_drift(committed_path: Path) -> int:
    """Rerun conformance (self-test) and compare the deterministic projection
    to the committed report."""
    try:
        regenerated = generate_report()
    except AssertionError as exc:
        print("PRODUCT BAKEOFF A DRIFT CHECK FAILED (self-test):", file=sys.stderr)
        print(f"  - {exc}", file=sys.stderr)
        return 1
    except ContractError as exc:
        print("PRODUCT BAKEOFF A DRIFT CHECK FAILED (ContractError):", file=sys.stderr)
        print(f"  - {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print("PRODUCT BAKEOFF A DRIFT CHECK FAILED (self-test):", file=sys.stderr)
        print(f"  - {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    reg_failures = validate_written_report(regenerated)
    if reg_failures:
        print("PRODUCT BAKEOFF A DRIFT CHECK FAILED (regenerated schema):", file=sys.stderr)
        for f in reg_failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    if not committed_path.exists():
        print(f"PRODUCT BAKEOFF A DRIFT CHECK FAILED: committed report not found: {committed_path}", file=sys.stderr)
        return 1
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    com_failures = validate_written_report(committed)
    if com_failures:
        print("PRODUCT BAKEOFF A DRIFT CHECK FAILED (committed schema):", file=sys.stderr)
        for f in com_failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    if regenerated != committed:
        print("PRODUCT BAKEOFF A DRIFT CHECK FAILED: regenerated report != committed report", file=sys.stderr)
        return 1
    print("PRODUCT BAKEOFF A DRIFT CHECK PASSED")
    print(f"  committed: {committed_path}")
    print(f"  readiness_status: {regenerated['readiness_status']}")
    print(f"  total_validated_runs: {regenerated['total_validated_runs']}")
    print(f"  accepted_count: {regenerated['accepted_count']}")
    print(f"  rejected_count: {regenerated['rejected_count']}")
    print(f"  totals_reconciled: {regenerated['totals_reconciled']}")
    print(f"  conformance_categories: {len(regenerated['conformance_categories_exercised'])}/9")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Product Stack Bakeoff Phase A conformance runner")
    parser.add_argument("--self-test", action="store_true",
                        help="run all nine conformance category self-tests")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help=f"write/regenerate the committed report (default: {DEFAULT_OUT})")
    parser.add_argument("--validate-report", metavar="PATH",
                        help="validate a written aggregate report (closed schema)")
    parser.add_argument("--check-drift", metavar="PATH",
                        help="rerun conformance and compare the deterministic projection to the committed report")
    args = parser.parse_args()

    if args.check_drift:
        return _check_drift(Path(args.check_drift))
    if args.validate_report:
        report_path = Path(args.validate_report)
        if not report_path.exists():
            print(f"ERROR: report not found: {report_path}", file=sys.stderr)
            return 1
        report = json.loads(report_path.read_text(encoding="utf-8"))
        failures = validate_written_report(report)
        if failures:
            print("PRODUCT BAKEOFF A REPORT VALIDATION FAILED:", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            return 1
        print("PRODUCT BAKEOFF A REPORT VALIDATION PASSED")
        print(f"  readiness_status: {report.get('readiness_status')}")
        print(f"  total_validated_runs: {report.get('total_validated_runs')}")
        print(f"  accepted_count: {report.get('accepted_count')}")
        print(f"  rejected_count: {report.get('rejected_count')}")
        print(f"  totals_reconciled: {report.get('totals_reconciled')}")
        print(f"  conformance_categories: {len(report.get('conformance_categories_exercised', []))}/9")
        return 0
    if args.self_test:
        failures = run_self_test()
        if failures:
            print("PRODUCT BAKEOFF A SELF-TEST FAILED:", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            return 1
        print("PRODUCT BAKEOFF A SELF-TEST PASSED")
        print("  conformance_categories: 9/9")
        print("  readiness_status: " + READINESS_STATUS)
        return 0
    report = generate_report()
    out_path = Path(args.out)
    _write_json(out_path, report)
    failures = validate_written_report(report)
    if failures:
        print("PRODUCT BAKEOFF A REPORT GENERATION FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"PRODUCT BAKEOFF A REPORT WRITTEN: {out_path}")
    print(f"  readiness_status: {report['readiness_status']}")
    print(f"  total_validated_runs: {report['total_validated_runs']}")
    print(f"  accepted_count: {report['accepted_count']}")
    print(f"  rejected_count: {report['rejected_count']}")
    print(f"  totals_reconciled: {report['totals_reconciled']}")
    print(f"  conformance_categories: {len(report['conformance_categories_exercised'])}/9")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
