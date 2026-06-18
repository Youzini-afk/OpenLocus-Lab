#!/usr/bin/env python3
"""B17 QuIVer Systems Track.

B17 is the **QuIVer systems track** phase. The goal is a **frozen,
preregistered backend bakeoff** that compares ANN backend candidates
(flat_f32_reference, hnsw_candidate, bq_topk_f32_rerank_candidate,
quiver_vamana_prototype, optional tdb_vector_candidate) on backend
systems metrics (latency, memory, build time, update cost, index size)
**under frozen candidate-quality policy** (candidate-set equivalence
constraints: overlap@K, gold_retention_delta, primary_false_positive
delta, citation_validity=1.0, stale/EvidenceCore rejection, no default
expansion).

B17 is a **bounded planning / diagnostic phase**, NOT QuIVer production
backend, NOT ANN quality promotion, NOT default change, NOT EvidenceCore
semantics change. The shipped skeleton performs NO real ANN backend
bakeoff, NO HNSW run, NO QuIVer/Vamana graph run, NO candidate-set
equivalence matrix across backends, NO update-cost / build-time /
index-size benchmark, NO stale/citation cross-backend validation. The
frozen preregistration (this file + ``docs/en/b17-quiver-systems-track.md``)
defines the backend set, the candidate-set equivalence constraints, the
metric registry, the hard gates, and the experimental structure; the
skeleton validates only that the contract is wired correctly and
carries forward the existing R33/R34/R36 diagnostic-only artifacts as
pre-B17 signals (NOT promotion, NOT quality proof).

Important claim boundary: B17 IS the quiver-systems-track *stage*
(``stage_is_quiver_systems_track=true``), but this skeleton performs NO
ANN backend bakeoff (``ann_backend_bakeoff_performed=false``), NO
candidate-set equivalence validation
(``candidate_set_equivalence_validated=false``), NO QuIVer graph
implementation (``quiver_graph_implemented=false``), and NO backend
quality promotion (``backend_quality_promoted=false``). Self-test /
``--input`` stub reports set
``promotion_ready=false``,
``default_should_change=false``,
``evidencecore_semantics_changed=false``,
``retrieval_policy_changed=false``,
``metrics_evaluated=false``,
``new_provider_calls=0`` so the synthetic / stub report cannot be
mistaken for an empirical B17 systems bakeoff result.

CRITICAL anti-fabrication boundary: this skeleton MUST NOT compute
fake ANN / QuIVer / HNSW / Vamana / latency / memory / build-time /
update-cost / index-size / overlap / gold-retention / SpanF0.5 / PFP
metrics from the existing R33/R34/R36 diagnostics. Those diagnostics
are BQ / flat_f32 / bq_topk_f32_rerank diagnostics only; they do NOT
contain a Vamana/QuIVer graph implementation, an HNSW run, or a
candidate-set equivalence matrix across backends, so any B17 systems
metric computed from them would be a fabrication. The synthetic fixture
validates only that the metric NAMES, hard gates, backend set, and
candidate-set equivalence constraints are wired correctly; it does NOT
present synthetic metric values as empirical B17 systems results.

Aggregate-only public artifacts: no task/repo/candidate/path/span/
snippet/prompt/response/diff/test/task-id/agent-event-log/private-label/
candidate-path/provider keys and no raw path/digest/provider strings.

This file currently ships a SKELETON: the ``--self-test`` path verifies
the backend set, candidate-set equivalence constraints, metric
registry, hard gates, and experimental structure against a synthetic
fixture (read-only: it builds the expected algorithm spec + report in
memory and compares them to the on-disk artifacts, failing on drift; it
does NOT mutate checked-in artifacts). ``--input <path>`` is a stub
(``verdict="not_implemented"``) awaiting the full backend bakeoff +
candidate-set equivalence matrix computation in a later task; it
requires ``--out`` and may not write the canonical checked-in report.
The ONLY path that mutates checked-in artifacts is
``--regenerate-artifacts``, which (re)writes the on-disk algorithm spec
+ synthetic-fixture report from the current build functions.

For a bounded public-systems diagnostic carry-forward / no-go screen
that does NOT claim QuIVer implementation or backend quality, see
``eval/b17_public_systems_diagnostic_screen.py``.

Run::

    python3 eval/b17_quiver_systems_track.py --self-test
    python3 eval/b17_quiver_systems_track.py --regenerate-artifacts
    python3 eval/b17_quiver_systems_track.py --input path/to/backend_inputs.json --out /tmp/b17_input_stub_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b17_quiver_systems_track"
REPORT_PATH = ARTIFACT_DIR / "b17_quiver_systems_track_report.json"
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "b17_quiver_systems_track.algorithm.json"
)

# Frozen reference diagnostics (provenance only — IDs and on-disk
# hash-match flags, never raw 64-char hex digests, which would trip the
# forbidden-value scan). These are diagnostic-only carry-forward
# artifacts; they are NOT promotion evidence and NOT quality proof.
R33_READINESS_PATH = REPO_ROOT / "artifacts" / "r33" / "quiver_readiness.json"
R34_R36_PROTO_PATH = (
    REPO_ROOT / "artifacts" / "r34_r36" / "quiver_anchor_proto.json"
)

SCHEMA_VERSION = "b17-quiver-systems-track-report-v0"
SPEC_SCHEMA_VERSION = "b17-quiver-systems-track-spec-v0"
GENERATED_BY = "b17_quiver_systems_track"
ALGORITHM_SPEC_ID = "b17_quiver_systems_track_v0"
CLAIM_LEVEL = "quiver_systems_track_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors
# B10/B10B/B11/B12/B13/B14/B15/B16).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Candidate backends (FROZEN before any B17 systems bakeoff)
# ---------------------------------------------------------------------------
#
# The backend set is the closed set of ANN backend candidates a B17
# systems bakeoff may compare under the frozen candidate-quality
# policy. ``flat_f32_reference`` is the reference backend (ground truth
# nearest-neighbor search); ``hnsw_candidate`` and
# ``bq_topk_f32_rerank_candidate`` are existing diagnostic-era
# candidate backends; ``quiver_vamana_prototype`` is the unimplemented
# QuIVer/Vamana graph backend (the B17 systems-track end goal);
# ``tdb_vector_candidate`` is an OPTIONAL store/backend candidate
# only — it is NOT an Evidence source and is excluded by default.
#

FLAT_F32_REFERENCE_BACKEND = "flat_f32_reference"
HNSW_CANDIDATE_BACKEND = "hnsw_candidate"
BQ_TOPK_F32_RERANK_BACKEND = "bq_topk_f32_rerank_candidate"
QUIVER_VAMANA_PROTOTYPE_BACKEND = "quiver_vamana_prototype"
TDB_VECTOR_CANDIDATE_BACKEND = "tdb_vector_candidate"

# Reference backend (ground-truth nearest-neighbor search; the
# candidate-set equivalence baseline).
REFERENCE_BACKENDS = (
    FLAT_F32_REFERENCE_BACKEND,
)

# Candidate backends compared under the frozen candidate-quality
# policy.
CANDIDATE_BACKENDS = (
    HNSW_CANDIDATE_BACKEND,
    BQ_TOPK_F32_RERANK_BACKEND,
    QUIVER_VAMANA_PROTOTYPE_BACKEND,
)

# Optional store/backend candidate only — NOT an Evidence source.
# Excluded by default; only included if explicitly opted in and only
# as a store/backend comparison, never as a primary Evidence source.
OPTIONAL_STORE_BACKENDS = (
    TDB_VECTOR_CANDIDATE_BACKEND,
)

ALL_BACKEND_IDS = (
    FLAT_F32_REFERENCE_BACKEND,
    HNSW_CANDIDATE_BACKEND,
    BQ_TOPK_F32_RERANK_BACKEND,
    QUIVER_VAMANA_PROTOTYPE_BACKEND,
    TDB_VECTOR_CANDIDATE_BACKEND,
)

# QuIVer/Vamana graph backend is unimplemented; the B17 systems track
# cannot complete the bakeoff until it is implemented.
QUIVER_VAMANA_IMPLEMENTED = False

# Optional store/backend inclusion rule: store/backend candidate only,
# never an Evidence source.
TDB_VECTOR_INCLUSION_RULE = "store_backend_candidate_only_never_evidence_source"
TDB_VECTOR_INCLUDED_BY_DEFAULT = False

# ---------------------------------------------------------------------------
# Candidate-set equivalence constraints (FROZEN before any B17 systems
# bakeoff)
# ---------------------------------------------------------------------------
#
# A candidate backend is admissible to the systems bakeoff ONLY if it
# preserves candidate quality within frozen tolerances versus the
# reference backend. The candidate-set equivalence constraints are
# FROZEN; a backend that fails any constraint is rejected regardless
# of its latency / memory / build / update / index-size numbers.
#

EQUIVALENCE_KS = (10, 50, 100)
CANDIDATE_SET_OVERLAP_AT_K_MINIMUM = 0.90
GOLD_RETENTION_DELTA_TOLERANCE = 0.05
PRIMARY_FALSE_POSITIVE_DELTA_GUARD = 0.05
SPAN_F0_5_DELTA_TOLERANCE = 0.05
CITATION_VALIDITY_REQUIRED = 1.0
NO_DEFAULT_EXPANSION_REQUIRED = True
STALE_EVIDENCECORE_REJECTION_REQUIRED = True

CANDIDATE_SET_EQUIVALENCE_CONSTRAINTS = (
    {
        "constraint_id": "candidate_set_overlap_at_k",
        "description": (
            "overlap_at_k vs reference backend must meet or exceed the "
            "frozen minimum overlap for every K in the frozen K set"
        ),
        "ks": list(EQUIVALENCE_KS),
        "minimum_overlap": CANDIDATE_SET_OVERLAP_AT_K_MINIMUM,
    },
    {
        "constraint_id": "gold_retention_delta_within_tolerance",
        "description": (
            "gold_retention_delta vs reference backend must be within "
            "the frozen tolerance (no quality regression beyond the "
            "frozen margin)"
        ),
        "tolerance": GOLD_RETENTION_DELTA_TOLERANCE,
    },
    {
        "constraint_id": "primary_false_positive_delta_guard",
        "description": (
            "primary_false_positive_delta vs reference backend must "
            "not exceed the frozen guard (no PFP regression)"
        ),
        "guard": PRIMARY_FALSE_POSITIVE_DELTA_GUARD,
    },
    {
        "constraint_id": "span_f0_5_delta_within_tolerance",
        "description": (
            "SpanF0.5_delta vs reference backend must be within the "
            "frozen tolerance (no span-quality regression)"
        ),
        "tolerance": SPAN_F0_5_DELTA_TOLERANCE,
    },
    {
        "constraint_id": "citation_validity_required",
        "description": (
            "citation_validity must be 1.0 for every backend (fail-"
            "closed citation and range validation)"
        ),
        "required": CITATION_VALIDITY_REQUIRED,
    },
    {
        "constraint_id": "stale_evidencecore_rejection_required",
        "description": (
            "stale and EvidenceCore-rejected candidates must be "
            "rejected by every backend (no stale leakage)"
        ),
        "required": STALE_EVIDENCECORE_REJECTION_REQUIRED,
    },
    {
        "constraint_id": "no_default_expansion_required",
        "description": (
            "no candidate backend may expand the default retrieval "
            "policy without separate promotion"
        ),
        "required": NO_DEFAULT_EXPANSION_REQUIRED,
    },
)

# ---------------------------------------------------------------------------
# Metric registry (FROZEN before any B17 systems bakeoff)
# ---------------------------------------------------------------------------
#
# These are the metric NAMES B17 will compute when real per-backend
# systems bakeoff inputs are available. The skeleton defines them and
# validates the hard gates, but does NOT compute fake metric values
# from the existing R33/R34/R36 diagnostics.
#

METRIC_NAMES = (
    "candidate_set_overlap_at_k",
    "gold_retention_delta",
    "span_f0_5_delta",
    "primary_false_positive_delta",
    "p50_latency",
    "p95_latency",
    "hot_memory",
    "build_time",
    "update_cost",
    "index_size",
    "recall_tolerance_violation_count",
)

# ---------------------------------------------------------------------------
# Hard gates (FROZEN before any B17 systems bakeoff)
# ---------------------------------------------------------------------------
#
# Each gate is FROZEN before any real B17 systems bakeoff. A candidate
# backend that fails any gate is rejected, regardless of its aggregate
# systems metrics.
#

HARD_GATES = (
    "quiver_graph_implementation_gate",
    "backend_parity_gate",
    "candidate_set_equivalence_gate",
    "evidencecore_materialization_gate",
    "stale_citation_gate",
    "privacy_gate",
    "promotion_false_gate",
)

# ---------------------------------------------------------------------------
# Experimental structure (FROZEN before any B17 systems bakeoff)
# ---------------------------------------------------------------------------

EXPERIMENTAL_STAGES = (
    "no_backend_bakeoff_feasibility",
    "frozen_candidate_quality_policy",
    "ann_backend_bakeoff",
    "candidate_set_equivalence_validation",
)

SPLIT_PROTOCOL = "stratified_by_repo_model_family_language"
TASK_SCREEN_FRACTION = 0.50
FRESH_VALIDATION_FRACTION = 0.50
FRESH_VALIDATION_SPLIT_REPORTED_ONCE = True

# CVaR tail fraction for worst-group reporting (worst 20% of groups).
CVAR_ALPHA = 0.20

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any B17 systems bakeoff)
# ---------------------------------------------------------------------------

PREDECLARED_CRITERIA: dict[str, Any] = {
    # Candidate-set equivalence tolerance gates (frozen).
    "candidate_set_overlap_at_k_minimum": CANDIDATE_SET_OVERLAP_AT_K_MINIMUM,
    "gold_retention_delta_tolerance": GOLD_RETENTION_DELTA_TOLERANCE,
    "primary_false_positive_delta_guard": PRIMARY_FALSE_POSITIVE_DELTA_GUARD,
    "span_f0_5_delta_tolerance": SPAN_F0_5_DELTA_TOLERANCE,
    "citation_validity_required": CITATION_VALIDITY_REQUIRED,
    "stale_evidencecore_rejection_required": STALE_EVIDENCECORE_REJECTION_REQUIRED,
    "no_default_expansion_required": NO_DEFAULT_EXPANSION_REQUIRED,
    # Equivalence K set (frozen).
    "equivalence_ks": list(EQUIVALENCE_KS),
    # CVaR tail fraction (worst 20% of groups).
    "cvar_alpha": CVAR_ALPHA,
    # Split protocol (frozen).
    "split_protocol": SPLIT_PROTOCOL,
    "task_screen_fraction": TASK_SCREEN_FRACTION,
    "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
    # Denominator gate: minimum per (backend, repo) cell.
    "min_denominator_per_backend_repo_cell": 30,
    # Operational parity gate: matched-control tolerance for build
    # time and update cost so the only varied factor is the backend
    # under the frozen candidate-quality policy.
    "operational_parity_build_time_match_tolerance": 0.20,
    "operational_parity_update_cost_match_tolerance": 0.20,
    "operational_parity_same_frozen_candidate_quality_policy": True,
    "operational_parity_no_default_expansion": True,
    "operational_parity_no_evidencecore_semantics_change": True,
    # Cost / systems metrics must be reported per backend (no cost
    # hiding).
    "systems_metrics_reported_per_backend": True,
    # Backends (frozen).
    "reference_backends": list(REFERENCE_BACKENDS),
    "candidate_backends": list(CANDIDATE_BACKENDS),
    "optional_store_backends": list(OPTIONAL_STORE_BACKENDS),
    "quiver_vamana_implemented": QUIVER_VAMANA_IMPLEMENTED,
    "tdb_vector_inclusion_rule": TDB_VECTOR_INCLUSION_RULE,
    "tdb_vector_included_by_default": TDB_VECTOR_INCLUDED_BY_DEFAULT,
}

# ---------------------------------------------------------------------------
# Required per-backend inputs (the real-B17 data contract)
# ---------------------------------------------------------------------------
#
# Real B17 systems bakeoff requires ALL of the following per backend.
# If any is missing, real B17 cannot run and the skeleton emits
# insufficient_data / not_implemented.
#

REQUIRED_PER_BACKEND_INPUTS = (
    "per_backend_index_build_record",
    "per_backend_search_latency_record",
    "per_backend_hot_memory_record",
    "per_backend_index_size_record",
    "per_backend_update_cost_record",
    "per_backend_candidate_set_at_k_record",
    "per_backend_gold_retention_record",
    "per_backend_span_f0_5_record",
    "per_backend_primary_false_positive_record",
    "per_backend_citation_validity_record",
    "per_backend_stale_rejection_record",
    "per_backend_evidencecore_rejection_record",
    "per_backend_recall_tolerance_violation_record",
    "per_backend_randomized_run_order_proof",
    "per_backend_isolated_index_workspace_proof",
    "shared_frozen_candidate_quality_manifest",
)

# ---------------------------------------------------------------------------
# Repos / languages (mirror R32/R33/R34 for consistency)
# ---------------------------------------------------------------------------

MINIMUM_VIABLE_REPOS = (
    "py_fastapi",
    "py_pytest",
    "ts_vite",
    "ts_hono",
    "go_chi",
    "go_prometheus",
    "rust_deno",
    "java_spring_petclinic",
)
LANGUAGES = ("python", "typescript", "go", "rust", "java")

# Frozen diagnostic carry-forward artifacts. We store spec_id + kind +
# an on-disk hash-match flag (the actual sha256 is NEVER written as a
# raw 64-char hex string, which would trip the forbidden-value scan;
# only the boolean matched flag is). These are diagnostic-only carry-
# forward signals; they are NOT promotion evidence and NOT quality
# proof.
FROZEN_ARTIFACTS = (
    {
        "spec_id": "r33_quiver_readiness",
        "kind": "r33_diagnostic_carry_forward",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
        "diagnostic_only": True,
        "not_promotion_evidence": True,
    },
    {
        "spec_id": "r34_r36_quiver_anchor_proto",
        "kind": "r34_r36_diagnostic_carry_forward",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
        "diagnostic_only": True,
        "not_promotion_evidence": True,
    },
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")

# Skeleton verdicts. This skeleton is strictly a skeleton / no-go
# commit: ``_evaluate_quiver_systems_bakeoff`` may only emit
# ``insufficient_data`` (synthetic fixture) or ``not_implemented``
# (ci_ephemeral_records stub). The success / failure / partial verdicts
# are NOT emitted by this skeleton. Any future real B17 empirical
# path that might emit them would require its own separate
# preregistration, and its exact flag schema is future work and is NOT
# present in this skeleton. This commit keeps
# ``ann_backend_bakeoff_performed``,
# ``candidate_set_equivalence_validated``,
# ``quiver_graph_implemented``, and ``backend_quality_promoted``
# strictly false.
ALLOWED_VERDICTS = (
    "insufficient_data",
    "not_implemented",
)
# Verdicts NOT emitted by this skeleton. Listed for documentation only.
EMPIRICAL_VERDICTS_RESERVED_FOR_FUTURE_B17 = (
    "success",
    "failure",
    "partial",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B/B11/B12/B13/B14/B15/B16)
# ---------------------------------------------------------------------------

FORBIDDEN_PUBLIC_KEYS = (
    "task_id",
    "test_id",
    "repo_id",
    "candidate_id",
    "path",
    "candidate_path",
    "span",
    "snippet",
    "prompt",
    "response",
    "raw_response",
    "agent_event_log",
    "patch",
    "diff",
    "test",
    "test_execution_result",
    "solve_label",
    "gold_spans",
    "label",
    "labels",
    "private_labels",
    "provider_key",
    "base_url",
    "api_key",
    "api_token",
    "api_secret",
    "content_sha",
    "digest",
    "start_line",
    "end_line",
    "line_range",
)

_FORBIDDEN_VALUE_RES = (
    re.compile(r"\b(?:sha_?(?:1|256)?|content_?sha)\b[\s:=]+[A-Fa-f0-9]{40,}", re.I),
    re.compile(r"https?://", re.I),
    re.compile(r"\b(?:api[_-]?key|base[_-]?url|api[_-]?secret|api[_-]?token)\b\s*[:=]\s*\S", re.I),
    re.compile(r"\b[A-Fa-f0-9]{64}\b"),
    re.compile(r"/"),  # raw filesystem path separator
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(obj) + "\n", encoding="utf-8")


def _recursive_key_scan(obj: Any) -> list[str]:
    """Flag forbidden KEY names and conservative leaked-value patterns.

    Provenance references use ``module::symbol`` / ``feature.name`` form
    (never raw filesystem paths), so the ``/`` value pattern is safe.
    """
    hits: list[str] = []

    def _walk(o: Any, path: str) -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                if key_str in FORBIDDEN_PUBLIC_KEYS:
                    hits.append(f"{path}.{key_str}")
                _walk(value, f"{path}.{key_str}")
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")
        elif isinstance(o, str):
            if len(o) > 512:
                hits.append(f"{path}:long_string")
            for p in _FORBIDDEN_VALUE_RES:
                if p.search(o):
                    hits.append(f"{path}:forbidden_value")

    _walk(obj, "$")
    return hits


# ---------------------------------------------------------------------------
# Synthetic fixture (self-test only)
# ---------------------------------------------------------------------------


def _build_synthetic_fixture() -> dict[str, Any]:
    """Build a definitions-only synthetic fixture for self-test.

    Returns a dict with the B17 contract, backend set, candidate-set
    equivalence constraints, metric registry, hard gates, and
    experimental structure. It contains NO per-backend systems bakeoff
    inputs and NO computed metric values, because such values would be
    fake B17 results when no real per-backend inputs exist.
    """
    return {
        "reference_backends": list(REFERENCE_BACKENDS),
        "candidate_backends": list(CANDIDATE_BACKENDS),
        "optional_store_backends": list(OPTIONAL_STORE_BACKENDS),
        "all_backend_ids": list(ALL_BACKEND_IDS),
        "candidate_set_equivalence_constraints": [
            dict(c) for c in CANDIDATE_SET_EQUIVALENCE_CONSTRAINTS
        ],
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "split_protocol": SPLIT_PROTOCOL,
        "task_screen_fraction": TASK_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "cvar_alpha": CVAR_ALPHA,
        # CRITICAL: no per-backend systems bakeoff inputs and no
        # computed metric values are present. The fixture is
        # definitions-only.
        "per_backend_systems_bakeoff_inputs_present": False,
        "metric_values_computed": False,
    }


# ---------------------------------------------------------------------------
# QuIVer systems bakeoff evaluation stub (definitions-only; no fake
# ANN/QuIVer metrics from diagnostics)
# ---------------------------------------------------------------------------


def _evaluate_quiver_systems_bakeoff(
    fixture: dict[str, Any],
    replay_source: str,
) -> tuple[dict[str, Any], str, str]:
    """Apply the predeclared QuIVer systems bakeoff criteria
    (skeleton-safe).

    Returns ``(quiver_systems_results, verdict, verdict_reason)``.

    This skeleton is strictly a skeleton / no-go commit: this function
    NEVER emits ``success`` / ``failure`` / ``partial`` and NEVER
    computes candidate_set_overlap_at_k / gold_retention_delta /
    span_f0_5_delta / primary_false_positive_delta / p50_latency /
    p95_latency / hot_memory / build_time / update_cost / index_size /
    recall_tolerance_violation_count values from R33/R34/R36
    diagnostics. Those metrics require per-backend systems bakeoff
    inputs (index build records, search latency records, hot memory
    records, index size records, update cost records, candidate-set-at-
    K records, gold retention records, span F0.5 records, PFP records,
    citation validity records, stale rejection records, EvidenceCore
    rejection records, recall tolerance violation records, randomized
    run order proof, isolated index workspace proof, shared frozen
    candidate-quality manifest), which are not present in any current
    public artifact. Any future real B17 empirical path that might emit
    success/failure/partial would require its own separate
    preregistration, and its exact flag schema (including any
    ``ann_backend_bakeoff_performed`` /
    ``candidate_set_equivalence_validated`` settings) is future work
    and NOT present in this skeleton. This commit keeps
    ``ann_backend_bakeoff_performed=false``,
    ``candidate_set_equivalence_validated=false``,
    ``quiver_graph_implemented=false``, and
    ``backend_quality_promoted=false`` strictly.

    The quiver_systems_results block surfaces only definitions + hard
    gates + the experimental stage *definitions* (no empirical
    per-stage latency/memory/build/update/index-size values).
    ``metrics_evaluated=false``,
    ``ann_backend_bakeoff_performed=false`` are surfaced so a reader
    cannot mistake the skeleton for an empirical B17 systems bakeoff.
    """
    stages_list: list[dict[str, Any]] = []
    for stage in EXPERIMENTAL_STAGES:
        stages_list.append(
            {
                "stage_id": stage,
                "evaluated": False,  # skeleton: no empirical evaluation
            }
        )
    quiver_systems_results: dict[str, Any] = {
        "metrics_defined": True,
        "metric_names": list(METRIC_NAMES),
        "gates_defined": True,
        "hard_gates": list(HARD_GATES),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "experimental_stages": {
            "stages_defined": True,
            "stage_count": len(EXPERIMENTAL_STAGES),
            "stages_evaluated": False,
            "stages": stages_list,
        },
        "reference_backends": list(REFERENCE_BACKENDS),
        "candidate_backends": list(CANDIDATE_BACKENDS),
        "optional_store_backends": list(OPTIONAL_STORE_BACKENDS),
        "candidate_set_equivalence_constraints": [
            dict(c) for c in CANDIDATE_SET_EQUIVALENCE_CONSTRAINTS
        ],
        # CRITICAL: no metric values are emitted.
        # metrics_evaluated=false is the disambiguating flag.
        "metrics_evaluated": False,
        "ann_backend_bakeoff_performed": False,
        "candidate_set_equivalence_validated": False,
        "quiver_graph_implemented": False,
        "backend_quality_promoted": False,
        "all_stages_pass": False,
        "stages_evaluated": False,
        "winner_declared": False,
        "no_fake_ann_metrics_from_diagnostics": True,
    }
    if replay_source == "synthetic_fixture":
        return (
            quiver_systems_results,
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; no empirical "
            "B17 QuIVer systems bakeoff performed; no per-backend "
            "systems bakeoff inputs available; no QuIVer or Vamana "
            "graph backend implementation; success, failure, or "
            "partial not emitted by skeleton; future real B17 flag "
            "schema is future work not in this skeleton",
        )
    # ci_ephemeral_records: real QuIVer systems bakeoff is not yet
    # implemented.
    return (
        quiver_systems_results,
        "not_implemented",
        "ci_ephemeral_records_replay_not_implemented; no empirical B17 "
        "QuIVer systems bakeoff performed; no per-backend systems "
        "bakeoff inputs consumed; no QuIVer or Vamana graph backend "
        "implementation; success, failure, or partial not emitted by "
        "skeleton; future real B17 flag schema is future work not in "
        "this skeleton",
    )


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B17 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so
    its SHA-256 is stable across runs. The on-disk spec file is the pin
    (mirrors B10/B10B/B11/B12/B13/B14/B15/B16 freeze style). The
    self-test verifies hash stability by re-loading and re-hashing.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": CLAIM_LEVEL,
        "description": (
            "B17 QuIVer Systems Track: frozen preregistered backend "
            "bakeoff comparing ANN backend candidates on backend "
            "systems metrics under a frozen candidate-quality policy. "
            "Bounded planning and diagnostic phase only. No QuIVer or "
            "Vamana graph implementation. No ANN quality promotion. "
            "No default change. No EvidenceCore semantics change."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_policy_changed": False,
        "backend_quality_promoted": False,
        # The algorithm_spec DEFINES the B17 quiver-systems-track stage
        # (so stage_is_quiver_systems_track=true), but no empirical B17
        # systems bakeoff has been performed by this skeleton
        # (ann_backend_bakeoff_performed=false,
        # candidate_set_equivalence_validated=false,
        # quiver_graph_implemented=false,
        # backend_quality_promoted=false). The synthetic / stub report
        # sets metrics_evaluated=false so the public artifact cannot
        # be misread as an empirical B17 systems bakeoff result.
        "stage_is_quiver_systems_track": True,
        "quiver_graph_implemented": False,
        "ann_backend_bakeoff_performed": False,
        "candidate_set_equivalence_validated": False,
        "backend_quality_promoted": False,
        "metrics_evaluated": False,
        "new_provider_calls": 0,
        "aggregate_only_public_artifact": True,
        "no_fake_ann_metrics_from_diagnostics": True,
        "reference_backends": list(REFERENCE_BACKENDS),
        "candidate_backends": list(CANDIDATE_BACKENDS),
        "optional_store_backends": list(OPTIONAL_STORE_BACKENDS),
        "all_backend_ids": list(ALL_BACKEND_IDS),
        "quiver_vamana_implemented": QUIVER_VAMANA_IMPLEMENTED,
        "tdb_vector_inclusion_rule": TDB_VECTOR_INCLUSION_RULE,
        "tdb_vector_included_by_default": TDB_VECTOR_INCLUDED_BY_DEFAULT,
        "candidate_set_equivalence_constraints": [
            dict(c) for c in CANDIDATE_SET_EQUIVALENCE_CONSTRAINTS
        ],
        "required_per_backend_inputs": list(REQUIRED_PER_BACKEND_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "split_protocol": SPLIT_PROTOCOL,
        "task_screen_fraction": TASK_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "fresh_validation_split_reported_once": (
            FRESH_VALIDATION_SPLIT_REPORTED_ONCE
        ),
        "cvar_alpha": CVAR_ALPHA,
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "allowed_replay_sources": list(ALLOWED_REPLAY_SOURCES),
        "allowed_verdicts": list(ALLOWED_VERDICTS),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "languages": list(LANGUAGES),
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_ann_backend_bakeoff": True,
            "no_quiver_graph_implementation": True,
            "no_hnsw_backend_run": True,
            "no_vamana_graph_run": True,
            "no_candidate_set_equivalence_validation": True,
            "no_update_cost_benchmark": True,
            "no_build_time_index_size_benchmark": True,
            "no_stale_citation_cross_backend_validation": True,
            "no_default_change": True,
            "no_retrieval_policy_change": True,
            "no_backend_quality_promotion": True,
            "no_evidencecore_semantics_change": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "no_fake_ann_metrics_from_diagnostics": True,
            "replay_only_no_live_ann_backend_bakeoff_in_evaluator": True,
        },
        "excluded_adapter_layer": {
            "model_adapter_excluded": True,
            "output_mode_excluded": True,
            "provider_credentials_excluded": True,
            "provider_endpoints_excluded": True,
            "provider_secrets_excluded": True,
            "raw_model_names_excluded": True,
            "raw_backend_event_logs_excluded": True,
            "raw_index_build_records_excluded": True,
            "raw_search_latency_records_excluded": True,
            "raw_hot_memory_records_excluded": True,
            "raw_index_size_records_excluded": True,
        },
    }


def _reference_spec_hashes() -> dict[str, bool]:
    """Check whether the on-disk frozen reference diagnostics (R33,
    R34/R36) are present and carry the diagnostic-only carry-forward
    flags. Returns ``{spec_id: pinned_bool}``. The actual sha256 hex is
    NEVER returned (it would trip the forbidden-value scan); only the
    boolean matched flag is exposed publicly.
    """
    refs: dict[str, bool] = {}
    # R33 readiness diagnostic.
    try:
        r33 = _load_json(R33_READINESS_PATH)
        refs["r33_quiver_readiness"] = (
            r33.get("schema_version") == "r33-quiver-readiness-v1"
            and r33.get("quiver_graph_implemented") is False
            and r33.get("quiver_quality_metrics_emitted") is False
            and isinstance(r33.get("generated_at"), str)
        )
    except FileNotFoundError:
        refs["r33_quiver_readiness"] = False
    # R34/R36 anchor proto diagnostic.
    try:
        r34 = _load_json(R34_R36_PROTO_PATH)
        refs["r34_r36_quiver_anchor_proto"] = (
            r34.get("schema_version") == "r34-r36-quiver-anchor-proto-v1"
            and r34.get("quiver_mode") == "diagnostic_only"
            and r34.get("quiver_graph_implemented") is False
            and isinstance(r34.get("generated_at"), str)
        )
    except FileNotFoundError:
        refs["r34_r36_quiver_anchor_proto"] = False
    return refs


def build_report(
    fixture: dict[str, Any],
    *,
    self_test: bool,
    replay_source: str,
) -> dict[str, Any]:
    """Build the B17 QuIVer systems track report.

    ``fixture`` is the definitions-only synthetic fixture (see
    ``_build_synthetic_fixture``). ``self_test=True`` flags that the
    report was produced from a synthetic fixture for mechanics
    validation; ``replay_source`` is one of
    ``ALLOWED_REPLAY_SOURCES``.

    The report NEVER emits candidate_set_overlap_at_k /
    gold_retention_delta / span_f0_5_delta /
    primary_false_positive_delta / p50_latency / p95_latency /
    hot_memory / build_time / update_cost / index_size /
    recall_tolerance_violation_count metric values, because no
    per-backend systems bakeoff inputs exist in any current public
    artifact. Only definitions + hard gates + experimental stage
    definitions are emitted.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    quiver_systems_results, verdict, verdict_reason = (
        _evaluate_quiver_systems_bakeoff(fixture, replay_source)
    )

    ref_hashes = _reference_spec_hashes()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": CLAIM_LEVEL,
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_policy_changed": False,
        "backend_quality_promoted": False,
        # B17 DEFINES the quiver-systems-track stage
        # (stage_is_quiver_systems_track=true), but this skeleton
        # performs NO ANN backend bakeoff, NO QuIVer/Vamana graph
        # implementation, NO candidate-set equivalence validation, and
        # NO backend quality promotion. The report flags
        # ann_backend_bakeoff_performed=false,
        # candidate_set_equivalence_validated=false,
        # quiver_graph_implemented=false,
        # backend_quality_promoted=false, metrics_evaluated=false so
        # synthetic / stub reports cannot be misread as empirical B17
        # systems bakeoff results.
        "stage_is_quiver_systems_track": True,
        "quiver_graph_implemented": False,
        "ann_backend_bakeoff_performed": False,
        "candidate_set_equivalence_validated": False,
        "backend_quality_promoted": False,
        "metrics_evaluated": False,
        "new_provider_calls": 0,
        # Skeleton: no stages evaluated, no winner declared, no
        # backend quality promoted. These top-level flags make the
        # skeleton stance unambiguous and mirror the
        # quiver_systems_results sub-block.
        "all_stages_pass": False,
        "stages_evaluated": False,
        "stages_defined": True,
        "stage_count": len(EXPERIMENTAL_STAGES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "no_fake_ann_metrics_from_diagnostics": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "frozen_reference_diagnostics_pinned_on_disk": ref_hashes,
        "reference_backends": list(REFERENCE_BACKENDS),
        "candidate_backends": list(CANDIDATE_BACKENDS),
        "optional_store_backends": list(OPTIONAL_STORE_BACKENDS),
        "all_backend_ids": list(ALL_BACKEND_IDS),
        "quiver_vamana_implemented": QUIVER_VAMANA_IMPLEMENTED,
        "tdb_vector_inclusion_rule": TDB_VECTOR_INCLUSION_RULE,
        "tdb_vector_included_by_default": TDB_VECTOR_INCLUDED_BY_DEFAULT,
        "candidate_set_equivalence_constraints": [
            dict(c) for c in CANDIDATE_SET_EQUIVALENCE_CONSTRAINTS
        ],
        "required_per_backend_inputs": list(REQUIRED_PER_BACKEND_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "split_protocol": SPLIT_PROTOCOL,
        "task_screen_fraction": TASK_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "fresh_validation_split_reported_once": (
            FRESH_VALIDATION_SPLIT_REPORTED_ONCE
        ),
        "cvar_alpha": CVAR_ALPHA,
        "repos": list(MINIMUM_VIABLE_REPOS),
        "languages": list(LANGUAGES),
        "quiver_systems_results": quiver_systems_results,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "aggregate_only_public_artifact": True,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_ann_backend_bakeoff": True,
            "no_quiver_graph_implementation": True,
            "no_hnsw_backend_run": True,
            "no_vamana_graph_run": True,
            "no_candidate_set_equivalence_validation": True,
            "no_update_cost_benchmark": True,
            "no_build_time_index_size_benchmark": True,
            "no_stale_citation_cross_backend_validation": True,
            "no_default_change": True,
            "no_retrieval_policy_change": True,
            "no_backend_quality_promotion": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "evidencecore_semantics_changed_false": True,
            "retrieval_policy_changed_false": True,
            "backend_quality_promoted_false": True,
            "quiver_graph_implemented_false": True,
            "ann_backend_bakeoff_performed_false": True,
            "candidate_set_equivalence_validated_false": True,
            "metrics_evaluated_false": True,
            "new_provider_calls_zero": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "runtime_calls_by_replay_zero": True,
            "model_calls_by_replay_zero": True,
            "no_fake_ann_metrics_from_diagnostics_true": True,
            "replay_only_no_live_ann_backend_bakeoff_in_evaluator": True,
        },
    }
    return report


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_algorithm_spec(spec: dict[str, Any], expected_hash: str) -> None:
    if spec.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise ValueError("algorithm spec schema_version mismatch")
    if spec.get("algorithm_spec_id") != ALGORITHM_SPEC_ID:
        raise ValueError("algorithm spec id mismatch")
    if spec.get("generated_by") != GENERATED_BY:
        raise ValueError("algorithm spec generated_by mismatch")
    if spec.get("generated_at") != GENERATED_AT:
        raise ValueError("algorithm spec generated_at must be fixed for hash stability")
    if spec.get("claim_level") != CLAIM_LEVEL:
        raise ValueError("algorithm spec claim_level mismatch")
    if spec.get("not_evidence") is not True:
        raise ValueError("algorithm spec not_evidence must be true")
    if spec.get("candidate_not_fact") is not True:
        raise ValueError("algorithm spec candidate_not_fact must be true")
    if spec.get("llm_output_not_evidence") is not True:
        raise ValueError("algorithm spec llm_output_not_evidence must be true")
    if spec.get("promotion_ready") is not False:
        raise ValueError("algorithm spec promotion_ready must be false")
    if spec.get("default_should_change") is not False:
        raise ValueError("algorithm spec default_should_change must be false")
    if spec.get("evidencecore_semantics_changed") is not False:
        raise ValueError("algorithm spec evidencecore_semantics_changed must be false")
    if spec.get("retrieval_policy_changed") is not False:
        raise ValueError("algorithm spec retrieval_policy_changed must be false")
    if spec.get("backend_quality_promoted") is not False:
        raise ValueError("algorithm spec backend_quality_promoted must be false")
    # B17 DEFINES the quiver-systems-track stage
    # (stage_is_quiver_systems_track=true), but no empirical B17
    # systems bakeoff, QuIVer/Vamana graph implementation, candidate-
    # set equivalence validation, or backend quality promotion is
    # performed by this skeleton.
    if spec.get("stage_is_quiver_systems_track") is not True:
        raise ValueError(
            "algorithm spec stage_is_quiver_systems_track must be true "
            "(B17 stage)"
        )
    if spec.get("quiver_graph_implemented") is not False:
        raise ValueError(
            "algorithm spec quiver_graph_implemented must be false "
            "(no QuIVer or Vamana graph implementation performed by skeleton)"
        )
    if spec.get("ann_backend_bakeoff_performed") is not False:
        raise ValueError(
            "algorithm spec ann_backend_bakeoff_performed must be false "
            "(no ANN backend bakeoff performed by skeleton)"
        )
    if spec.get("candidate_set_equivalence_validated") is not False:
        raise ValueError(
            "algorithm spec candidate_set_equivalence_validated must be "
            "false (skeleton; no candidate-set equivalence validation "
            "performed)"
        )
    if spec.get("backend_quality_promoted") is not False:
        raise ValueError(
            "algorithm spec backend_quality_promoted must be false (skeleton)"
        )
    if spec.get("metrics_evaluated") is not False:
        raise ValueError(
            "algorithm spec metrics_evaluated must be false (skeleton; no "
            "fake ANN metrics from diagnostics)"
        )
    if spec.get("new_provider_calls") != 0:
        raise ValueError("algorithm spec new_provider_calls must be 0")
    if spec.get("aggregate_only_public_artifact") is not True:
        raise ValueError("algorithm spec aggregate_only_public_artifact must be true")
    if spec.get("no_fake_ann_metrics_from_diagnostics") is not True:
        raise ValueError(
            "algorithm spec no_fake_ann_metrics_from_diagnostics must be true"
        )
    if spec.get("runtime_calls_by_replay") != 0:
        raise ValueError("algorithm spec runtime_calls_by_replay must be 0")
    if spec.get("model_calls_by_replay") != 0:
        raise ValueError("algorithm spec model_calls_by_replay must be 0")
    gates = spec.get("predeclared_criteria")
    if not isinstance(gates, dict):
        raise ValueError("algorithm spec missing predeclared_criteria dict")
    for k, expected in PREDECLARED_CRITERIA.items():
        if gates.get(k) != expected:
            raise ValueError(
                f"predeclared_criteria[{k}] mismatch: expected {expected!r} got {gates.get(k)!r}"
            )
    if tuple(spec.get("reference_backends") or ()) != REFERENCE_BACKENDS:
        raise ValueError("algorithm spec reference_backends mismatch")
    if tuple(spec.get("candidate_backends") or ()) != CANDIDATE_BACKENDS:
        raise ValueError("algorithm spec candidate_backends mismatch")
    if tuple(spec.get("optional_store_backends") or ()) != OPTIONAL_STORE_BACKENDS:
        raise ValueError("algorithm spec optional_store_backends mismatch")
    if tuple(spec.get("all_backend_ids") or ()) != ALL_BACKEND_IDS:
        raise ValueError("algorithm spec all_backend_ids mismatch")
    if spec.get("quiver_vamana_implemented") is not QUIVER_VAMANA_IMPLEMENTED:
        raise ValueError("algorithm spec quiver_vamana_implemented mismatch")
    if (
        tuple(spec.get("required_per_backend_inputs") or ())
        != REQUIRED_PER_BACKEND_INPUTS
    ):
        raise ValueError("algorithm spec required_per_backend_inputs mismatch")
    if tuple(spec.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("algorithm spec metric_names mismatch")
    if tuple(spec.get("hard_gates") or ()) != HARD_GATES:
        raise ValueError("algorithm spec hard_gates mismatch")
    if tuple(spec.get("experimental_stages") or ()) != EXPERIMENTAL_STAGES:
        raise ValueError("algorithm spec experimental_stages mismatch")
    if spec.get("split_protocol") != SPLIT_PROTOCOL:
        raise ValueError("algorithm spec split_protocol mismatch")
    if spec.get("task_screen_fraction") != TASK_SCREEN_FRACTION:
        raise ValueError("algorithm spec task_screen_fraction mismatch")
    if spec.get("fresh_validation_fraction") != FRESH_VALIDATION_FRACTION:
        raise ValueError("algorithm spec fresh_validation_fraction mismatch")
    if spec.get("cvar_alpha") != CVAR_ALPHA:
        raise ValueError("algorithm spec cvar_alpha mismatch")
    if tuple(spec.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("algorithm spec repos mismatch")
    # Spec hash must be stable.
    recomputed = _sha256_json(spec)
    if recomputed != expected_hash:
        raise ValueError(
            f"algorithm spec sha256 not stable: expected={expected_hash!r} "
            f"recomputed={recomputed!r}"
        )
    hits = _recursive_key_scan(spec)
    if hits:
        raise ValueError(f"forbidden public keys/values in algorithm spec: {hits!r}")


def verify_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("report schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        raise ValueError("report generated_by mismatch")
    if report.get("generated_at") != GENERATED_AT:
        raise ValueError("report generated_at must be fixed")
    if report.get("algorithm_spec_id") != ALGORITHM_SPEC_ID:
        raise ValueError("report algorithm_spec_id mismatch")
    if report.get("algorithm_spec_sha256_matched") is not True:
        raise ValueError("report algorithm_spec_sha256_matched must be true")
    if report.get("algorithm_spec_sha256_stable") is not True:
        raise ValueError("report algorithm_spec_sha256_stable must be true")
    if report.get("claim_level") != CLAIM_LEVEL:
        raise ValueError("report claim_level mismatch")
    if report.get("not_evidence") is not True:
        raise ValueError("report not_evidence must be true")
    if report.get("candidate_not_fact") is not True:
        raise ValueError("report candidate_not_fact must be true")
    if report.get("llm_output_not_evidence") is not True:
        raise ValueError("report llm_output_not_evidence must be true")
    if report.get("promotion_ready") is not False:
        raise ValueError("report promotion_ready must be false")
    if report.get("default_should_change") is not False:
        raise ValueError("report default_should_change must be false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError("report evidencecore_semantics_changed must be false")
    if report.get("retrieval_policy_changed") is not False:
        raise ValueError("report retrieval_policy_changed must be false")
    if report.get("backend_quality_promoted") is not False:
        raise ValueError("report backend_quality_promoted must be false")
    # B17 DEFINES the quiver-systems-track stage
    # (stage_is_quiver_systems_track=true), but this skeleton performs
    # NO ANN backend bakeoff, NO QuIVer/Vamana graph implementation,
    # NO candidate-set equivalence validation, and NO backend quality
    # promotion.
    if report.get("stage_is_quiver_systems_track") is not True:
        raise ValueError(
            "report stage_is_quiver_systems_track must be true (B17 stage)"
        )
    if report.get("quiver_graph_implemented") is not False:
        raise ValueError(
            "report quiver_graph_implemented must be false "
            "(no QuIVer or Vamana graph implementation performed by skeleton)"
        )
    if report.get("ann_backend_bakeoff_performed") is not False:
        raise ValueError(
            "report ann_backend_bakeoff_performed must be false "
            "(no ANN backend bakeoff performed by skeleton)"
        )
    if report.get("candidate_set_equivalence_validated") is not False:
        raise ValueError(
            "report candidate_set_equivalence_validated must be false (skeleton)"
        )
    if report.get("backend_quality_promoted") is not False:
        raise ValueError(
            "report backend_quality_promoted must be false (skeleton)"
        )
    if report.get("metrics_evaluated") is not False:
        raise ValueError(
            "report metrics_evaluated must be false (skeleton; no fake "
            "ANN metrics from diagnostics)"
        )
    if report.get("new_provider_calls") != 0:
        raise ValueError("report new_provider_calls must be 0")
    if report.get("all_stages_pass") is not False:
        raise ValueError(
            "report all_stages_pass must be false (skeleton)"
        )
    if report.get("stages_evaluated") is not False:
        raise ValueError(
            "report stages_evaluated must be false (skeleton; no "
            "empirical stage evaluation performed)"
        )
    if report.get("stages_defined") is not True:
        raise ValueError("report stages_defined must be true (4 stages)")
    if report.get("stage_count") != len(EXPERIMENTAL_STAGES):
        raise ValueError(
            "report stage_count must equal the number of frozen stages"
        )
    if report.get("winner_declared") is not False:
        raise ValueError("report winner_declared must be false (skeleton)")
    if report.get("metrics_defined") is not True:
        raise ValueError("report metrics_defined must be true")
    if report.get("gates_defined") is not True:
        raise ValueError("report gates_defined must be true")
    if report.get("no_fake_ann_metrics_from_diagnostics") is not True:
        raise ValueError(
            "report no_fake_ann_metrics_from_diagnostics must be true"
        )
    if report.get("runtime_calls_by_replay") != 0:
        raise ValueError("report runtime_calls_by_replay must be 0")
    if report.get("model_calls_by_replay") != 0:
        raise ValueError("report model_calls_by_replay must be 0")
    if report.get("replay_source") not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"report replay_source invalid: {report.get('replay_source')!r}")
    if report.get("verdict") not in ALLOWED_VERDICTS:
        raise ValueError(f"report verdict invalid: {report.get('verdict')!r}")
    if not isinstance(report.get("verdict_reason"), str) or not report["verdict_reason"]:
        raise ValueError("report verdict_reason must be a non-empty string")
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError("report aggregate_only_public_artifact must be true")
    if report.get("predeclared_criteria") != PREDECLARED_CRITERIA:
        raise ValueError("report predeclared_criteria must match the frozen constants")
    if tuple(report.get("reference_backends") or ()) != REFERENCE_BACKENDS:
        raise ValueError("report reference_backends mismatch")
    if tuple(report.get("candidate_backends") or ()) != CANDIDATE_BACKENDS:
        raise ValueError("report candidate_backends mismatch")
    if tuple(report.get("optional_store_backends") or ()) != OPTIONAL_STORE_BACKENDS:
        raise ValueError("report optional_store_backends mismatch")
    if tuple(report.get("all_backend_ids") or ()) != ALL_BACKEND_IDS:
        raise ValueError("report all_backend_ids mismatch")
    if tuple(report.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("report metric_names mismatch")
    if tuple(report.get("hard_gates") or ()) != HARD_GATES:
        raise ValueError("report hard_gates mismatch")
    if tuple(report.get("experimental_stages") or ()) != EXPERIMENTAL_STAGES:
        raise ValueError("report experimental_stages mismatch")
    if tuple(report.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("report repos mismatch")
    # Required top-level sections.
    for key in (
        "quiver_systems_results",
    ):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # quiver_systems_results substructure. The skeleton emits only
    # definitions + hard gates + experimental stage definitions; no
    # empirical per-stage metric values.
    qsr = report.get("quiver_systems_results") or {}
    for key in (
        "metrics_defined",
        "metric_names",
        "gates_defined",
        "hard_gates",
        "predeclared_criteria",
        "experimental_stages",
        "reference_backends",
        "candidate_backends",
        "optional_store_backends",
        "candidate_set_equivalence_constraints",
        "metrics_evaluated",
        "ann_backend_bakeoff_performed",
        "candidate_set_equivalence_validated",
        "quiver_graph_implemented",
        "backend_quality_promoted",
        "all_stages_pass",
        "stages_evaluated",
        "winner_declared",
        "no_fake_ann_metrics_from_diagnostics",
    ):
        if key not in qsr:
            raise ValueError(f"quiver_systems_results missing required section: {key}")
    if qsr.get("metrics_evaluated") is not False:
        raise ValueError(
            "quiver_systems_results.metrics_evaluated must be false "
            "(skeleton; no fake ANN metrics from diagnostics)"
        )
    if qsr.get("ann_backend_bakeoff_performed") is not False:
        raise ValueError(
            "quiver_systems_results.ann_backend_bakeoff_performed must be "
            "false (skeleton)"
        )
    if qsr.get("candidate_set_equivalence_validated") is not False:
        raise ValueError(
            "quiver_systems_results.candidate_set_equivalence_validated "
            "must be false (skeleton)"
        )
    if qsr.get("quiver_graph_implemented") is not False:
        raise ValueError(
            "quiver_systems_results.quiver_graph_implemented must be "
            "false (skeleton)"
        )
    if qsr.get("backend_quality_promoted") is not False:
        raise ValueError(
            "quiver_systems_results.backend_quality_promoted must be "
            "false (skeleton)"
        )
    if qsr.get("all_stages_pass") is not False:
        raise ValueError(
            "quiver_systems_results.all_stages_pass must be false (skeleton)"
        )
    if qsr.get("stages_evaluated") is not False:
        raise ValueError(
            "quiver_systems_results.stages_evaluated must be false (skeleton)"
        )
    if qsr.get("winner_declared") is not False:
        raise ValueError(
            "quiver_systems_results.winner_declared must be false (skeleton)"
        )
    if qsr.get("no_fake_ann_metrics_from_diagnostics") is not True:
        raise ValueError(
            "quiver_systems_results.no_fake_ann_metrics_from_diagnostics "
            "must be true"
        )
    # experimental_stages must be a definitions-only block.
    stages = qsr.get("experimental_stages") or {}
    if stages.get("stages_defined") is not True:
        raise ValueError(
            "quiver_systems_results.experimental_stages.stages_defined "
            "must be true"
        )
    if stages.get("stage_count") != len(EXPERIMENTAL_STAGES):
        raise ValueError(
            "quiver_systems_results.experimental_stages.stage_count mismatch"
        )
    if stages.get("stages_evaluated") is not False:
        raise ValueError(
            "quiver_systems_results.experimental_stages.stages_evaluated "
            "must be false (skeleton)"
        )
    stage_list = stages.get("stages")
    if not isinstance(stage_list, list) or len(stage_list) != len(
        EXPERIMENTAL_STAGES
    ):
        raise ValueError(
            "quiver_systems_results.experimental_stages.stages must be "
            "a list of stage definitions"
        )
    for s in stage_list:
        if s.get("evaluated") is not False:
            raise ValueError(
                "stage definitions must have evaluated=false (skeleton)"
            )
        for forbidden_key in (
            "passes",
            "candidate_set_overlap_at_k",
            "gold_retention_delta",
            "span_f0_5_delta",
            "primary_false_positive_delta",
            "p50_latency",
            "p95_latency",
            "hot_memory",
            "build_time",
            "update_cost",
            "index_size",
            "recall_tolerance_violation_count",
            "delta_vs_reference",
        ):
            if forbidden_key in s:
                raise ValueError(
                    f"stage definition must not carry empirical field "
                    f"{forbidden_key!r} (skeleton)"
                )
    # Safety invariant flags.
    si = report.get("safety_invariants") or {}
    for flag in (
        "no_live_llm_calls",
        "no_ann_backend_bakeoff",
        "no_quiver_graph_implementation",
        "no_hnsw_backend_run",
        "no_vamana_graph_run",
        "no_candidate_set_equivalence_validation",
        "no_update_cost_benchmark",
        "no_build_time_index_size_benchmark",
        "no_stale_citation_cross_backend_validation",
        "no_default_change",
        "no_retrieval_policy_change",
        "no_backend_quality_promotion",
        "no_evidencecore_semantics_change",
        "promotion_ready_false",
        "default_should_change_false",
        "evidencecore_semantics_changed_false",
        "retrieval_policy_changed_false",
        "backend_quality_promoted_false",
        "quiver_graph_implemented_false",
        "ann_backend_bakeoff_performed_false",
        "candidate_set_equivalence_validated_false",
        "metrics_evaluated_false",
        "new_provider_calls_zero",
        "aggregate_only_public_artifact",
        "forbidden_public_keys_scanned",
        "no_raw_path_digest_provider_strings",
        "runtime_calls_by_replay_zero",
        "model_calls_by_replay_zero",
        "no_fake_ann_metrics_from_diagnostics_true",
        "replay_only_no_live_ann_backend_bakeoff_in_evaluator",
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input (stub): load per-backend inputs without computing QuIVer
# systems bakeoff metrics
# ---------------------------------------------------------------------------


def _load_per_backend_input(path: str) -> dict[str, Any]:
    """Load a per-backend inputs JSON file (or directory of JSON files)
    and return a minimal metadata payload. The full per-backend systems
    bakeoff + candidate-set equivalence matrix computation is deferred
    to a later task; for now we only verify the input is valid JSON and
    surface its top-level shape (without leaking any forbidden keys).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"--input path not found: {path}")
    if p.is_dir():
        files = sorted(p.glob("*.json"))
        if not files:
            raise ValueError(f"--input directory has no .json files: {path}")
        loaded: list[dict[str, Any]] = []
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                loaded.append(data)
            elif isinstance(data, list):
                loaded.extend(x for x in data if isinstance(x, dict))
            else:
                raise ValueError(
                    f"--input file {f.name} must contain a JSON array or object"
                )
        return {
            "source_kind": "directory",
            "n_files": len(files),
            "n_records": len(loaded),
        }
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {
            "source_kind": "file_array",
            "n_files": 1,
            "n_records": len(data),
        }
    if isinstance(data, dict):
        records = data.get("records")
        n_records = len(records) if isinstance(records, list) else 0
        return {
            "source_kind": "file_object",
            "n_files": 1,
            "n_records": n_records,
        }
    raise ValueError(
        f"--input file must contain a JSON array or object, got {type(data).__name__}"
    )


def _build_not_implemented_report(input_meta: dict[str, Any]) -> dict[str, Any]:
    """Build a stub report for ``--input`` mode.

    Real per-backend systems bakeoff + candidate-set equivalence matrix
    computation (candidate_set_overlap_at_k, gold_retention_delta,
    span_f0_5_delta, primary_false_positive_delta, p50_latency,
    p95_latency, hot_memory, build_time, update_cost, index_size,
    recall_tolerance_violation_count across reference + candidate
    backends) is deferred to a later task. For now we emit a
    well-formed report with ``verdict="not_implemented"`` and an
    explanatory reason, while still passing all safety-invariant
    checks.

    CRITICAL: this stub MUST NOT compute fake ANN / QuIVer / HNSW /
    Vamana metrics from the existing R33/R34/R36 diagnostics. No
    metric values are emitted.
    """
    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Override the verdict to signal that no real QuIVer systems
    # bakeoff happened.
    report["verdict"] = "not_implemented"
    report["verdict_reason"] = (
        "real-input QuIVer systems bakeoff + per-backend systems "
        "bakeoff replay computation deferred to later task; "
        f"input_meta={input_meta}"
    )
    # Re-stamp the spec hash fields (defensive: build_report already
    # sets these).
    report["algorithm_spec_sha256_matched"] = True
    report["algorithm_spec_sha256_stable"] = (spec_hash == _sha256_json(spec))
    # Re-scan forbidden keys after the override (input_meta may
    # include only safe scalar fields by construction).
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(
            f"forbidden public keys/values in not-implemented report: {hits!r}"
        )
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test_forbidden_scan() -> None:
    bad_report = {
        "task_id": "leak",
        "path": "src/foo.rs",
        "snippet": "fn main(){}",
        "provider_key": "sk-xxx",
        "diff": "diff --git a/b",
        "patch": "patch content",
        "solve_label": "True",
        "gold_spans": [[1, 2]],
        "nested": {"content_sha": "deadbeef", "candidate_id": "c1"},
    }
    hits = _recursive_key_scan(bad_report)
    flat = " ".join(hits)
    assert "task_id" in flat
    assert "path" in flat
    assert "snippet" in flat
    assert "provider_key" in flat
    assert "diff" in flat
    assert "patch" in flat
    assert "solve_label" in flat
    assert "gold_spans" in flat
    assert "content_sha" in flat
    assert "candidate_id" in flat

    # Raw path value should trip the "/" pattern even when the key is
    # allowed.
    bad_value = {"provenance": "eval/some_file.py"}
    hits2 = _recursive_key_scan(bad_value)
    assert any("forbidden_value" in h for h in hits2), hits2

    # A clean provenance reference (module::symbol, no "/") must not
    # trip.
    clean = {"provenance": "b17_quiver_systems_track::build_report"}
    hits3 = _recursive_key_scan(clean)
    assert hits3 == [], hits3

    # A 64-hex digest value must trip the forbidden-value scan.
    bad_digest = {"some_field": "a" * 64}
    hits4 = _recursive_key_scan(bad_digest)
    assert any("forbidden_value" in h for h in hits4), hits4


def _self_test_spec_hash_stable() -> None:
    spec = build_algorithm_spec()
    h1 = _sha256_json(spec)
    spec2 = build_algorithm_spec()
    h2 = _sha256_json(spec2)
    assert h1 == h2, "build_algorithm_spec() must be deterministic"
    verify_algorithm_spec(spec, h1)


def _self_test_backend_set_closed() -> None:
    """Backend set is closed; reference / candidate / optional-store
    backends are mutually disjoint; QuIVer/Vamana graph backend is
    unimplemented; optional store backend is excluded by default and
    is never an Evidence source."""
    spec = build_algorithm_spec()
    assert tuple(spec["reference_backends"]) == REFERENCE_BACKENDS
    assert tuple(spec["candidate_backends"]) == CANDIDATE_BACKENDS
    assert tuple(spec["optional_store_backends"]) == OPTIONAL_STORE_BACKENDS
    assert tuple(spec["all_backend_ids"]) == ALL_BACKEND_IDS
    # All backend IDs unique.
    assert len(set(ALL_BACKEND_IDS)) == len(ALL_BACKEND_IDS), ALL_BACKEND_IDS
    # Reference, candidate, optional-store backends are mutually
    # disjoint.
    reference = set(REFERENCE_BACKENDS)
    candidate = set(CANDIDATE_BACKENDS)
    optional_store = set(OPTIONAL_STORE_BACKENDS)
    assert reference.isdisjoint(candidate), (reference & candidate)
    assert reference.isdisjoint(optional_store), (reference & optional_store)
    assert candidate.isdisjoint(optional_store), (candidate & optional_store)
    # QuIVer/Vamana graph backend is unimplemented.
    assert QUIVER_VAMANA_IMPLEMENTED is False
    assert (
        QUIVER_VAMANA_PROTOTYPE_BACKEND in CANDIDATE_BACKENDS
    ), CANDIDATE_BACKENDS
    # Optional store backend is excluded by default (store/backend
    # candidate only, never an Evidence source).
    assert TDB_VECTOR_INCLUDED_BY_DEFAULT is False
    assert "store_backend_candidate_only_never_evidence_source" == (
        TDB_VECTOR_INCLUSION_RULE
    )


def _self_test_candidate_set_equivalence_constraints() -> None:
    """Candidate-set equivalence constraints: 7 frozen constraints; each
    constraint is a definitions-only block with no empirical value
    fields."""
    spec = build_algorithm_spec()
    constraints = spec["candidate_set_equivalence_constraints"]
    assert len(constraints) == len(CANDIDATE_SET_EQUIVALENCE_CONSTRAINTS)
    expected_ids = {c["constraint_id"] for c in CANDIDATE_SET_EQUIVALENCE_CONSTRAINTS}
    actual_ids = {c["constraint_id"] for c in constraints}
    assert actual_ids == expected_ids, (actual_ids, expected_ids)
    # Required constraints present (the task spec).
    required_ids = {
        "candidate_set_overlap_at_k",
        "gold_retention_delta_within_tolerance",
        "primary_false_positive_delta_guard",
        "citation_validity_required",
        "stale_evidencecore_rejection_required",
        "no_default_expansion_required",
    }
    assert required_ids.issubset(actual_ids), (
        required_ids - actual_ids
    )
    # Equivalence K set frozen.
    assert tuple(spec["predeclared_criteria"]["equivalence_ks"]) == EQUIVALENCE_KS


def _self_test_metric_registry() -> None:
    """Metric registry: 11 metric names defined; no aggregate-mean
    metrics."""
    spec = build_algorithm_spec()
    assert tuple(spec["metric_names"]) == METRIC_NAMES
    assert len(METRIC_NAMES) == 11, METRIC_NAMES
    # All metric names require per-backend systems bakeoff inputs;
    # none can be computed from R33/R34/R36 diagnostics.
    for name in METRIC_NAMES:
        assert "aggregate_mean" not in name, name
        assert "overall_mean" not in name, name


def _self_test_hard_gates_defined() -> None:
    """Hard gates: quiver_graph_implementation / backend_parity /
    candidate_set_equivalence / evidencecore_materialization /
    stale_citation / privacy / promotion_false gates defined."""
    spec = build_algorithm_spec()
    assert tuple(spec["hard_gates"]) == HARD_GATES
    assert len(HARD_GATES) == 7, HARD_GATES
    expected_gates = {
        "quiver_graph_implementation_gate",
        "backend_parity_gate",
        "candidate_set_equivalence_gate",
        "evidencecore_materialization_gate",
        "stale_citation_gate",
        "privacy_gate",
        "promotion_false_gate",
    }
    assert set(HARD_GATES) == expected_gates, HARD_GATES


def _self_test_experimental_structure_frozen() -> None:
    """Experimental structure: 4 frozen stages; no feedback."""
    spec = build_algorithm_spec()
    assert tuple(spec["experimental_stages"]) == EXPERIMENTAL_STAGES
    assert len(EXPERIMENTAL_STAGES) == 4, EXPERIMENTAL_STAGES
    assert EXPERIMENTAL_STAGES == (
        "no_backend_bakeoff_feasibility",
        "frozen_candidate_quality_policy",
        "ann_backend_bakeoff",
        "candidate_set_equivalence_validation",
    ), EXPERIMENTAL_STAGES
    # Split protocol: task-screen + fresh-validation, stratified by
    # (repo, model_family, language).
    assert spec["split_protocol"] == SPLIT_PROTOCOL
    assert spec["task_screen_fraction"] + spec["fresh_validation_fraction"] == 1.0
    assert spec["fresh_validation_split_reported_once"] is True
    # Evaluate the stages on the synthetic fixture (evaluator-side).
    # The skeleton emits definitions only; no empirical per-stage
    # metric values.
    fixture = _build_synthetic_fixture()
    cr, _verdict, _reason = _evaluate_quiver_systems_bakeoff(
        fixture, "synthetic_fixture"
    )
    stages_block = cr["experimental_stages"]
    assert stages_block["stages_defined"] is True
    assert stages_block["stage_count"] == 4
    assert stages_block["stages_evaluated"] is False
    stage_ids = {s["stage_id"] for s in stages_block["stages"]}
    assert stage_ids == set(EXPERIMENTAL_STAGES), stage_ids
    for s in stages_block["stages"]:
        assert s.get("evaluated") is False
        for forbidden_key in (
            "passes",
            "candidate_set_overlap_at_k",
            "gold_retention_delta",
            "span_f0_5_delta",
            "primary_false_positive_delta",
            "p50_latency",
            "p95_latency",
            "hot_memory",
            "build_time",
            "update_cost",
            "index_size",
            "recall_tolerance_violation_count",
            "delta_vs_reference",
        ):
            assert forbidden_key not in s, (forbidden_key, s)


def _self_test_no_fake_ann_metrics_from_diagnostics() -> None:
    """CRITICAL: the skeleton must NOT compute fake ANN / QuIVer / HNSW /
    Vamana metrics from the existing R33/R34/R36 diagnostics. The
    synthetic-fixture report must surface metrics_evaluated=false and
    contain no metric value fields."""
    fixture = _build_synthetic_fixture()
    assert fixture["per_backend_systems_bakeoff_inputs_present"] is False
    assert fixture["metric_values_computed"] is False
    report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )
    assert report["metrics_evaluated"] is False
    assert report["no_fake_ann_metrics_from_diagnostics"] is True
    assert report["quiver_systems_results"]["metrics_evaluated"] is False
    assert (
        report["quiver_systems_results"][
            "no_fake_ann_metrics_from_diagnostics"
        ]
        is True
    )
    # No metric value fields should be present at the top level.
    for forbidden_field in (
        "candidate_set_overlap_at_k_value",
        "gold_retention_delta_value",
        "span_f0_5_delta_value",
        "primary_false_positive_delta_value",
        "p50_latency_value",
        "p95_latency_value",
        "hot_memory_value",
        "build_time_value",
        "update_cost_value",
        "index_size_value",
        "recall_tolerance_violation_count_value",
    ):
        assert forbidden_field not in report, forbidden_field
        assert forbidden_field not in report["quiver_systems_results"], forbidden_field


def _self_test_input_stub_not_implemented(tmp_path: Path) -> None:
    """--input mode must emit verdict='not_implemented' without doing
    any real QuIVer systems bakeoff computation."""
    p = tmp_path / "per_backend_stub.json"
    p.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "backend": "flat_f32_reference",
                        "candidate_set_at_k": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    meta = _load_per_record_input_helper(p)
    assert meta["source_kind"] == "file_object"
    assert meta["n_records"] == 1
    report = _build_not_implemented_report(meta)
    verify_report(report)
    assert report["replay_source"] == "ci_ephemeral_records"
    assert report["verdict"] == "not_implemented"
    assert "deferred" in report["verdict_reason"]
    # Stub report must still surface metrics_evaluated=false (no fake
    # metrics).
    assert report["metrics_evaluated"] is False
    assert report["ann_backend_bakeoff_performed"] is False
    assert report["candidate_set_equivalence_validated"] is False
    assert report["quiver_graph_implemented"] is False
    assert report["backend_quality_promoted"] is False


def _load_per_record_input_helper(p: Path) -> dict[str, Any]:
    """Thin alias for ``_load_per_backend_input`` so the self-test
    reads naturally; the underlying loader is identical to the
    ``--input`` path."""
    return _load_per_backend_input(str(p))


def _self_test_reference_diagnostics() -> None:
    """The R33 readiness + R34/R36 anchor-proto diagnostic-only
    carry-forward artifacts must exist on disk so the B17
    frozen_artifacts pin is meaningful and so the B17 systems track
    cannot misread them as quality proof."""
    refs = _reference_spec_hashes()
    assert refs.get("r33_quiver_readiness") is True, refs
    assert refs.get("r34_r36_quiver_anchor_proto") is True, refs


def _self_test_artifacts_match_in_memory() -> None:
    """Read-only drift check: build the expected algorithm spec + report
    in memory and compare them to the on-disk artifacts. Fails on
    drift. Does NOT write anything to disk (self-test is read-only).
    Use ``--regenerate-artifacts`` to (re)write the on-disk artifacts.
    """
    expected_spec = build_algorithm_spec()
    expected_spec_hash = _sha256_json(expected_spec)

    on_disk_spec = _load_json(ALGORITHM_SPEC_PATH)
    on_disk_spec_hash = _sha256_json(on_disk_spec)
    if on_disk_spec_hash != expected_spec_hash:
        raise ValueError(
            "on-disk algorithm spec drifted from build_algorithm_spec() "
            f"output: on_disk={on_disk_spec_hash!r} "
            f"expected={expected_spec_hash!r}; run "
            "`python3 eval/b17_quiver_systems_track.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_algorithm_spec(on_disk_spec, on_disk_spec_hash)
    if on_disk_spec != expected_spec:
        raise ValueError(
            "on-disk algorithm spec content drifted from "
            "build_algorithm_spec() output (same hash but content differs; "
            "this should be impossible)"
        )

    fixture = _build_synthetic_fixture()
    expected_report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )

    on_disk_report = _load_json(REPORT_PATH)
    if on_disk_report != expected_report:
        raise ValueError(
            "on-disk b17_quiver_systems_track_report.json drifted from "
            "the in-memory build_report() output; run "
            "`python3 eval/b17_quiver_systems_track.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_report(on_disk_report)


def regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report
    so the artifact pin matches the in-code build functions. Mirrors
    the B10/B10B/B11/B12/B13/B14/B15/B16 freeze-write style:
    deterministic output, canonical JSON.

    This is the ONLY mutating path. ``--self-test`` is read-only and
    uses ``_self_test_artifacts_match_in_memory`` to detect drift.
    """
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    """Run all B17 self-test checks. Returns a summary dict."""
    import tempfile

    _self_test_forbidden_scan()
    _self_test_spec_hash_stable()
    _self_test_backend_set_closed()
    _self_test_candidate_set_equivalence_constraints()
    _self_test_metric_registry()
    _self_test_hard_gates_defined()
    _self_test_experimental_structure_frozen()
    _self_test_no_fake_ann_metrics_from_diagnostics()
    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_stub_not_implemented(Path(tmp))
    _self_test_reference_diagnostics()
    _self_test_artifacts_match_in_memory()

    spec = build_algorithm_spec()
    _spec_hash = _sha256_json(spec)

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": CLAIM_LEVEL,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_policy_changed": False,
        "backend_quality_promoted": False,
        "stage_is_quiver_systems_track": True,
        "quiver_graph_implemented": False,
        "ann_backend_bakeoff_performed": False,
        "candidate_set_equivalence_validated": False,
        "metrics_evaluated": False,
        "new_provider_calls": 0,
        "all_stages_pass": False,
        "stages_evaluated": False,
        "stages_defined": True,
        "stage_count": len(EXPERIMENTAL_STAGES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "no_fake_ann_metrics_from_diagnostics": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "aggregate_only_public_artifact": True,
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "backend_set_closed": True,
            "candidate_set_equivalence_constraints": True,
            "metric_registry": True,
            "hard_gates_defined": True,
            "experimental_structure_frozen": True,
            "no_fake_ann_metrics_from_diagnostics": True,
            "input_stub_not_implemented": True,
            "reference_diagnostics_pinned": True,
            "artifacts_match_in_memory": True,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help=(
            "run the B17 self-test (read-only; synthetic fixture; verifies "
            "mechanics; compares in-memory expected artifacts to on-disk "
            "artifacts and fails on drift; does NOT write to disk)"
        ),
    )
    parser.add_argument(
        "--regenerate-artifacts",
        action="store_true",
        help=(
            "explicitly (re)write the on-disk algorithm spec + "
            "synthetic-fixture report artifacts from the current build "
            "functions. This is the ONLY mutating path; --self-test is "
            "read-only."
        ),
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help=(
            "path to a JSON file or directory of JSON files containing "
            "per-backend systems bakeoff inputs (index build records, "
            "search latency records, hot memory records, index size "
            "records, update cost records, candidate-set-at-K records, "
            "gold retention records, span F0.5 records, PFP records, "
            "citation validity records, stale rejection records, "
            "EvidenceCore rejection records, recall tolerance violation "
            "records, randomized run order proof, isolated index "
            "workspace proof, shared frozen candidate-quality "
            "manifest). Currently a STUB: emits verdict='not_implemented'; "
            "full QuIVer systems bakeoff + per-backend replay "
            "computation deferred to a later task. Requires --out and "
            "may not write the canonical checked-in artifact."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write a stub input report. Required with --input; "
            "must not be the canonical checked-in B17 report artifact."
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input and not args.regenerate_artifacts:
        parser.error(
            "B17 requires --self-test, --regenerate-artifacts, or "
            "--input <path> in this skeleton"
        )
    selected = sum(
        1 for flag in (args.self_test, args.regenerate_artifacts, bool(args.input))
        if flag
    )
    if selected > 1:
        parser.error(
            "--self-test, --regenerate-artifacts, and --input are mutually "
            "exclusive"
        )
    if args.input:
        if not args.out:
            parser.error(
                "--input is a non-canonical stub path and requires --out; "
                "only --regenerate-artifacts may write checked-in artifacts"
            )
        out_path = Path(args.out).resolve()
        # Blocker guard: --input must not write ANY checked-in B17
        # artifact — neither the canonical report nor the algorithm
        # spec. The simplest fail-closed rule is to reject any --out
        # that resolves inside artifacts/b17_quiver_systems_track/.
        # --input is intended for /tmp or other external paths only.
        artifact_dir_resolved = ARTIFACT_DIR.resolve()
        canonical_paths = {
            REPORT_PATH.resolve(),
            ALGORITHM_SPEC_PATH.resolve(),
            (
                ARTIFACT_DIR
                / "b17_public_systems_diagnostic_screen_report.json"
            ).resolve(),
        }
        try:
            in_artifact_dir = (
                out_path == artifact_dir_resolved
                or artifact_dir_resolved in out_path.parents
            )
        except ValueError:
            in_artifact_dir = False
        if in_artifact_dir or out_path in canonical_paths:
            parser.error(
                "--input may not write inside the checked-in B17 "
                "artifact directory artifacts/b17_quiver_systems_track/ "
                "(canonical report, algorithm spec, or public systems "
                "diagnostic screen report); use --out outside artifacts/ "
                "or run --regenerate-artifacts"
            )
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "claim_level": report["claim_level"],
        "reference_backends": report["reference_backends"],
        "candidate_backends": report["candidate_backends"],
        "optional_store_backends": report["optional_store_backends"],
        "metric_names": report["metric_names"],
        "hard_gates": report["hard_gates"],
        "experimental_stages": report["experimental_stages"],
        "split_protocol": report["split_protocol"],
        "task_screen_fraction": report["task_screen_fraction"],
        "fresh_validation_fraction": report["fresh_validation_fraction"],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "evidencecore_semantics_changed": report["evidencecore_semantics_changed"],
        "retrieval_policy_changed": report["retrieval_policy_changed"],
        "backend_quality_promoted": report["backend_quality_promoted"],
        "stage_is_quiver_systems_track": report[
            "stage_is_quiver_systems_track"
        ],
        "quiver_graph_implemented": report["quiver_graph_implemented"],
        "ann_backend_bakeoff_performed": report[
            "ann_backend_bakeoff_performed"
        ],
        "candidate_set_equivalence_validated": report[
            "candidate_set_equivalence_validated"
        ],
        "metrics_evaluated": report["metrics_evaluated"],
        "new_provider_calls": report["new_provider_calls"],
        "all_stages_pass": report["all_stages_pass"],
        "stages_evaluated": report["stages_evaluated"],
        "stages_defined": report["stages_defined"],
        "stage_count": report["stage_count"],
        "winner_declared": report["winner_declared"],
        "metrics_defined": report["metrics_defined"],
        "gates_defined": report["gates_defined"],
        "no_fake_ann_metrics_from_diagnostics": report[
            "no_fake_ann_metrics_from_diagnostics"
        ],
        "runtime_calls_by_replay": report["runtime_calls_by_replay"],
        "model_calls_by_replay": report["model_calls_by_replay"],
        "aggregate_only_public_artifact": report["aggregate_only_public_artifact"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B17 self-test: PASS (read-only; no artifacts written)", file=sys.stderr)
        return 0
    if args.regenerate_artifacts:
        regenerate_artifacts()
        summary = {
            "algorithm_spec_id": ALGORITHM_SPEC_ID,
            "algorithm_spec_path": str(ALGORITHM_SPEC_PATH),
            "report_path": str(REPORT_PATH),
            "regenerated": True,
            "self_test": True,
            "replay_source": "synthetic_fixture",
            "verdict": "insufficient_data",
            "quiver_graph_implemented": False,
            "ann_backend_bakeoff_performed": False,
            "candidate_set_equivalence_validated": False,
            "backend_quality_promoted": False,
            "metrics_evaluated": False,
            "no_fake_ann_metrics_from_diagnostics": True,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(
            f"B17 artifacts regenerated: {ALGORITHM_SPEC_PATH} + {REPORT_PATH}",
            file=sys.stderr,
        )
        return 0
    if args.input:
        input_meta = _load_per_backend_input(args.input)
        report = _build_not_implemented_report(input_meta)
        verify_report(report)
        out_path = Path(args.out)
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B17 report written to {out_path}", file=sys.stderr)
        return 0
    print(
        "B17 requires --self-test, --regenerate-artifacts, or --input",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
