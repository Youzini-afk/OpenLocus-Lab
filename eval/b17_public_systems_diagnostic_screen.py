#!/usr/bin/env python3
"""B17 Public Systems Diagnostic Carry-Forward / No-Go Screen (bounded).

This is a **bounded public-systems diagnostic carry-forward / no-go
screen**, NOT a real B17 QuIVer systems bakeoff. Real B17 (the frozen
preregistration in ``eval/b17_quiver_systems_track.py`` and
``docs/en/b17-quiver-systems-track.md``) requires per-backend systems
bakeoff inputs: per-backend index build records, per-backend search
latency records, per-backend hot memory records, per-backend index size
records, per-backend update cost records, per-backend candidate-set-at-
K records, per-backend gold retention records, per-backend span F0.5
records, per-backend PFP records, per-backend citation validity
records, per-backend stale rejection records, per-backend EvidenceCore
rejection records, per-backend recall tolerance violation records,
per-backend randomized run order proof, per-backend isolated index
workspace proof, and a shared frozen candidate-quality manifest. None
of those are present in the existing public R33 readiness, R34/R36
anchor-proto, real-provider P3/P4 quiver diagnostics, or the R24
QuIVer/TDB/dense probe, so real B17 QuIVer systems bakeoff cannot be
performed from public aggregates alone.

What this screen DOES: read the already-published public diagnostic
artifacts (R33 readiness, R34/R36 anchor proto, real-provider P3/P4
quiver diagnostics, R24 QuIVer/TDB/dense probe if present) and emit a
**public-systems diagnostic carry-forward / no-go report** for B17.
The guard for each artifact is optional: if an artifact is absent the
screen reports it as ``not_present`` rather than failing.

The screen preserves the public-artifact contract:

* **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, diffs, patches, test execution
  results, solve labels, agent event logs, gold spans, private labels,
  provider keys, base URLs, API keys, or digests are read or emitted;
* **no** provider calls (``new_provider_calls == 0``);
* **no** live ANN backend bakeoff, no QuIVer/Vamana graph
  implementation, no HNSW backend run, no candidate-set equivalence
  validation, no update-cost benchmark, no build-time/index-size
  benchmark, no stale/citation cross-backend validation, no backend
  quality promotion, no retrieval policy change, no winner
  declaration;
* ``ann_backend_bakeoff_performed=false``,
  ``candidate_set_equivalence_validated=false``,
  ``quiver_graph_implemented=false``,
  ``backend_quality_promoted=false``,
  ``retrieval_policy_changed=false``,
  ``metrics_evaluated=false``.

CRITICAL: the screen MUST NOT compute fake candidate_set_overlap_at_k /
gold_retention_delta / span_f0_5_delta / primary_false_positive_delta /
p50_latency / p95_latency / hot_memory / build_time / update_cost /
index_size / recall_tolerance_violation_count metrics from the
existing R33/R34/R36/R24 diagnostics. Those diagnostics are BQ /
flat_f32 / bq_topk_f32_rerank diagnostics only; they do NOT contain a
Vamana/QuIVer graph implementation, an HNSW run, or a candidate-set
equivalence matrix across backends, so any B17 systems metric computed
from them would be a fabrication. The screen enumerates the specific
missing inputs that block real B17 and carries forward the existing
diagnostics only as pre-B17 signals, not promotion.

Important claim boundary: the existing R33/R34/R36/R24 diagnostics do
NOT prove QuIVer implementation, ANN quality/promotion, or default
change. They are diagnostic-only carry-forward. This screen makes no
claim that any retrieval variant, QuIVer, or any backend candidate
improves a downstream agent, changes a default, promotes a backend,
changes retrieval policy, or changes EvidenceCore semantics.

Run::

    python3 eval/b17_public_systems_diagnostic_screen.py --self-test
    python3 eval/b17_public_systems_diagnostic_screen.py \
        --out artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_VERSION = "b17-public-systems-diagnostic-screen-v0"
GENERATED_BY = "b17_public_systems_diagnostic_screen"
CLAIM_LEVEL = (
    "bounded_public_systems_diagnostic_carry_forward_screen_of_r33_r34_r36_real_p3_p4_r24"
)

# Input schemas (provenance only).
INPUT_R33_SCHEMA = "r33-quiver-readiness-v1"
INPUT_R34_R36_SCHEMA = "r34-r36-quiver-anchor-proto-v1"

DEFAULT_INPUT_R33 = Path("artifacts/r33/quiver_readiness.json")
DEFAULT_INPUT_R34_R36 = Path("artifacts/r34_r36/quiver_anchor_proto.json")
DEFAULT_INPUT_REAL_P3 = Path(
    "artifacts/real_provider/p3_real_quiver_readiness.json"
)
DEFAULT_INPUT_REAL_P4 = Path(
    "artifacts/real_provider/p4_real_quiver_anchor_proto.json"
)
DEFAULT_INPUT_R24 = Path("runs/r24-quiver-tdb-probe.json")
DEFAULT_OUT = Path(
    "artifacts/b17_quiver_systems_track/"
    "b17_public_systems_diagnostic_screen_report.json"
)

# Verdicts emitted by this screen. The screen NEVER emits success /
# failure / partial as a systems-bakeoff verdict; it emits only
# diagnostic carry-forward / no-go statuses that make clear no
# empirical B17 systems bakeoff happened.
ALLOWED_VERDICTS = (
    "diagnostic_carry_forward_only",
    "no_go_quiver_graph_missing",
)

# Missing inputs that block real B17 from the public diagnostics. Each
# entry is a self-contained reason so a reader cannot mistake the
# screen for a B17 systems bakeoff result. Descriptions are kept under
# 256 chars to satisfy the public forbidden-value scan (long_string
# guard) and avoid the path-separator pattern.
MISSING_INPUTS = (
    {
        "gap_id": "no_quiver_or_vamana_graph_backend_implementation",
        "description": (
            "real B17 needs a QuIVer or Vamana graph backend "
            "implementation; the public diagnostics only emit BQ and "
            "flat_f32 and bq_topk_f32_rerank diagnostics and report "
            "quiver_graph_implemented false"
        ),
    },
    {
        "gap_id": "no_hnsw_backend_run",
        "description": (
            "real B17 needs an HNSW candidate backend run with measured "
            "latency memory build update and index size; no HNSW run "
            "exists in the public diagnostics"
        ),
    },
    {
        "gap_id": "no_candidate_set_equivalence_matrix_across_backends",
        "description": (
            "real B17 needs a candidate-set equivalence matrix across "
            "backends with overlap gold retention PFP SpanF0.5 "
            "tolerance checks versus a reference backend; the public "
            "diagnostics contain no such matrix"
        ),
    },
    {
        "gap_id": "no_update_cost_benchmark",
        "description": (
            "real B17 needs a per-backend update-cost benchmark with "
            "isolated index workspace proof; the public diagnostics "
            "contain no update-cost benchmark"
        ),
    },
    {
        "gap_id": "no_build_time_index_size_benchmark",
        "description": (
            "real B17 needs a per-backend build-time and index-size "
            "benchmark; the public diagnostics contain no build-time "
            "or index-size benchmark"
        ),
    },
    {
        "gap_id": "no_stale_citation_cross_backend_validation",
        "description": (
            "real B17 needs stale and citation validation across "
            "backends; the public diagnostics carry single-backend "
            "citation validity but no cross-backend stale validation"
        ),
    },
    {
        "gap_id": "no_shared_frozen_candidate_quality_manifest",
        "description": (
            "real B17 needs a shared frozen candidate-quality manifest "
            "so all backends are compared under the same candidate-"
            "quality policy; the public diagnostics contain no such "
            "manifest"
        ),
    },
    {
        "gap_id": "no_large_repo_repeatable_systems_matrix",
        "description": (
            "real B17 needs a large-repo repeatable systems matrix so "
            "backend latency memory build update index size are "
            "measured under realistic scale; the public diagnostics "
            "contain no large-repo repeatable systems matrix"
        ),
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _as_bool(value: Any) -> bool:
    return bool(value)


def _base_report(self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "input_r33_schema": INPUT_R33_SCHEMA,
        "input_r34_r36_schema": INPUT_R34_R36_SCHEMA,
        # Safety fields preserved verbatim. The screen makes NO
        # empirical B17 systems bakeoff claim; the B17 stage IS quiver
        # systems track, but no empirical ANN backend bakeoff was
        # performed by this screen.
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
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
        # Forbidden content never read or emitted.
        "candidate_ids_in_artifact": False,
        "task_ids_in_artifact": False,
        "raw_repo_ids_in_artifact": False,
        "run_ids_in_artifact": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_patches_diffs_stored": False,
        "raw_test_results_stored": False,
        "raw_solve_labels_stored": False,
        "raw_agent_event_logs_stored": False,
        "raw_backend_event_logs_stored": False,
        "raw_index_build_records_stored": False,
        "raw_search_latency_records_stored": False,
        "raw_hot_memory_records_stored": False,
        "raw_index_size_records_stored": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "promotion_declared": False,
        "default_recommendation_declared": False,
        "backend_quality_promotion_declared": False,
        "retrieval_variant_promotion_declared": False,
        "winner_declared": False,
        # Bounded-screen stance.
        "is_full_b17_quiver_systems_bakeoff": False,
        "full_b17_systems_bakeoff_possible_from_public_artifacts": False,
        "metrics_defined": True,
        "gates_defined": True,
        "no_fake_ann_metrics_from_diagnostics": True,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the forbidden-key/value scan on the public output."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b17-public-systems-diagnostic-screen public output would "
            f"contain forbidden keys/values; first violations: "
            f"{violations[:5]}"
        )


# ---------------------------------------------------------------------------
# Input loaders (guard optional)
# ---------------------------------------------------------------------------


def _load_optional(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Load an optional JSON diagnostic artifact.

    Returns ``(parsed_or_None, status)`` where status is one of:
      * ``"loaded"`` — the artifact was loaded
      * ``"not_present"`` — the file does not exist
    """
    if not path.exists():
        return None, "not_present"
    try:
        return json.loads(path.read_text(encoding="utf-8")), "loaded"
    except (OSError, json.JSONDecodeError) as exc:
        return {"load_error_kind": type(exc).__name__}, "load_failed"


def _validate_r33(report: dict[str, Any]) -> None:
    if report.get("schema_version") != INPUT_R33_SCHEMA:
        raise ValueError(
            f"unexpected R33 schema_version: {report.get('schema_version')!r}"
        )
    if report.get("quiver_graph_implemented") is not False:
        raise ValueError("R33 input must have quiver_graph_implemented=false")
    if report.get("quiver_quality_metrics_emitted") is not False:
        raise ValueError(
            "R33 input must have quiver_quality_metrics_emitted=false"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("R33 input must have promotion_ready=false")
    if report.get("default_should_change") is not False:
        raise ValueError("R33 input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "R33 input must have evidencecore_semantics_changed=false"
        )
    if report.get("BQ_diagnostics_only") is not True:
        raise ValueError("R33 input must have BQ_diagnostics_only=true")


def _validate_r34_r36(report: dict[str, Any]) -> None:
    if report.get("schema_version") != INPUT_R34_R36_SCHEMA:
        raise ValueError(
            f"unexpected R34/R36 schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("quiver_mode") != "diagnostic_only":
        raise ValueError("R34/R36 input must have quiver_mode=diagnostic_only")
    if report.get("quiver_graph_implemented") is not False:
        raise ValueError(
            "R34/R36 input must have quiver_graph_implemented=false"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("R34/R36 input must have promotion_ready=false")
    if report.get("default_should_change") is not False:
        raise ValueError("R34/R36 input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "R34/R36 input must have evidencecore_semantics_changed=false"
        )


def _validate_real_p3(report: dict[str, Any]) -> None:
    if report.get("schema_version") != INPUT_R33_SCHEMA:
        raise ValueError(
            f"unexpected real-provider P3 schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("quiver_graph_implemented") is not False:
        raise ValueError(
            "real-provider P3 input must have quiver_graph_implemented=false"
        )
    if report.get("quiver_quality_metrics_emitted") is not False:
        raise ValueError(
            "real-provider P3 input must have "
            "quiver_quality_metrics_emitted=false"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError(
            "real-provider P3 input must have promotion_ready=false"
        )
    if report.get("default_should_change") is not False:
        raise ValueError(
            "real-provider P3 input must have default_should_change=false"
        )
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "real-provider P3 input must have "
            "evidencecore_semantics_changed=false"
        )


def _validate_real_p4(report: dict[str, Any]) -> None:
    if report.get("schema_version") != INPUT_R34_R36_SCHEMA:
        raise ValueError(
            f"unexpected real-provider P4 schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("quiver_mode") != "diagnostic_only":
        raise ValueError(
            "real-provider P4 input must have quiver_mode=diagnostic_only"
        )
    if report.get("quiver_graph_implemented") is not False:
        raise ValueError(
            "real-provider P4 input must have quiver_graph_implemented=false"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError(
            "real-provider P4 input must have promotion_ready=false"
        )
    if report.get("default_should_change") is not False:
        raise ValueError(
            "real-provider P4 input must have default_should_change=false"
        )
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "real-provider P4 input must have "
            "evidencecore_semantics_changed=false"
        )
    # quiver_default_allowed is an optional field; if present it must
    # be false (no default expansion).
    if "quiver_default_allowed" in report and report.get(
        "quiver_default_allowed"
    ) is not False:
        raise ValueError(
            "real-provider P4 input must have quiver_default_allowed=false "
            "when present"
        )


# QuIVer-implemented flag names that, if true in an R24 artifact,
# would contradict the B17 no-go signal. Each is optional; if
# present and true the artifact is rejected.
_R24_QUIVER_IMPLEMENTED_FLAGS = (
    "quiver_implemented_in_rust",
    "quiver_graph_implemented",
    "quiver_quality_metrics_emitted",
    "quiver_available",
)


def _validate_r24(report: dict[str, Any]) -> None:
    """R24 (QuIVer/TDB/Dense Probe) is optional. If present, it must
    report QuIVer not implemented and not promote. Each safety field
    is optional (R24 historical artifacts may not carry every flag),
    but if present it must have the safe value; any QuIVer-implemented
    flag true is rejected fail-closed."""
    if report.get("schema_version") != "r24-v1":
        raise ValueError(
            f"unexpected R24 schema_version: {report.get('schema_version')!r}"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("R24 input must have promotion_ready=false")
    if (
        "default_should_change" in report
        and report.get("default_should_change") is not False
    ):
        raise ValueError(
            "R24 input must have default_should_change=false when present"
        )
    if (
        "evidencecore_semantics_changed" in report
        and report.get("evidencecore_semantics_changed") is not False
    ):
        raise ValueError(
            "R24 input must have evidencecore_semantics_changed=false "
            "when present"
        )
    # Any QuIVer-implemented flag present and true is rejected fail-
    # closed. We check both the top-level flags and a nested
    # ``quiver_status`` dict (R24 historically nests some QuIVer
    # status fields).
    for flag in _R24_QUIVER_IMPLEMENTED_FLAGS:
        if report.get(flag) is True:
            raise ValueError(
                f"R24 input must have {flag}=false or absent; "
                f"got {report.get(flag)!r}"
            )
    nested = report.get("quiver_status")
    if isinstance(nested, dict):
        for flag in (
            "quiver_implemented",
            "quiver_graph_implemented",
            "quiver_quality_metrics_emitted",
            "quiver_available",
        ):
            if nested.get(flag) is True:
                raise ValueError(
                    f"R24 input must have quiver_status.{flag}=false or "
                    f"absent; got {nested.get(flag)!r}"
                )


# ---------------------------------------------------------------------------
# Carry-forward summaries (aggregate-only)
# ---------------------------------------------------------------------------


def _carry_forward_r33(r33: dict[str, Any]) -> dict[str, Any]:
    return {
        "r33_quiver_graph_implemented": _as_bool(r33.get("quiver_graph_implemented")),
        "r33_quiver_quality_metrics_emitted": _as_bool(
            r33.get("quiver_quality_metrics_emitted")
        ),
        "r33_BQ_diagnostics_only": _as_bool(r33.get("BQ_diagnostics_only")),
        "r33_promotion_ready": _as_bool(r33.get("promotion_ready")),
        "r33_default_should_change": _as_bool(r33.get("default_should_change")),
        "r33_evidencecore_semantics_changed": _as_bool(
            r33.get("evidencecore_semantics_changed")
        ),
        "r33_not_promotion_evidence": _as_bool(r33.get("not_promotion_evidence")),
        "r33_quiver_fit": (r33.get("diagnostics") or {}).get("quiver_fit"),
        "r33_recommendation": (r33.get("diagnostics") or {}).get("recommendation"),
    }


def _carry_forward_r34_r36(r34: dict[str, Any]) -> dict[str, Any]:
    return {
        "r34_quiver_mode": r34.get("quiver_mode"),
        "r34_quiver_graph_implemented": _as_bool(
            r34.get("quiver_graph_implemented")
        ),
        "r34_vamana_pruning_implemented": _as_bool(
            r34.get("vamana_pruning_implemented")
        ),
        "r34_bq_topk_implemented": _as_bool(r34.get("bq_topk_implemented")),
        "r34_f32_rerank_implemented": _as_bool(r34.get("f32_rerank_implemented")),
        "r34_quiver_default_allowed": _as_bool(r34.get("quiver_default_allowed")),
        "r34_quiver_supporting_channel_allowed": _as_bool(
            r34.get("quiver_supporting_channel_allowed")
        ),
        "r34_dense_or_quiver_supporting_only": (
            r34.get("dense_or_quiver_role") == "candidate/supporting-only"
        ),
        "r34_promotion_ready": _as_bool(r34.get("promotion_ready")),
        "r34_default_should_change": _as_bool(r34.get("default_should_change")),
        "r34_evidencecore_semantics_changed": _as_bool(
            r34.get("evidencecore_semantics_changed")
        ),
    }


def _carry_forward_real_p3(p3: dict[str, Any]) -> dict[str, Any]:
    return {
        "real_p3_quiver_graph_implemented": _as_bool(
            p3.get("quiver_graph_implemented")
        ),
        "real_p3_quiver_quality_metrics_emitted": _as_bool(
            p3.get("quiver_quality_metrics_emitted")
        ),
        "real_p3_BQ_diagnostics_only": _as_bool(p3.get("BQ_diagnostics_only")),
        "real_p3_promotion_ready": _as_bool(p3.get("promotion_ready")),
        "real_p3_quiver_fit": (p3.get("diagnostics") or {}).get("quiver_fit"),
        "real_p3_recommendation": (p3.get("diagnostics") or {}).get(
            "recommendation"
        ),
    }


def _carry_forward_real_p4(p4: dict[str, Any]) -> dict[str, Any]:
    return {
        "real_p4_quiver_mode": p4.get("quiver_mode"),
        "real_p4_quiver_graph_implemented": _as_bool(
            p4.get("quiver_graph_implemented")
        ),
        "real_p4_quiver_default_allowed": _as_bool(
            p4.get("quiver_default_allowed")
        ),
        "real_p4_quiver_supporting_channel_allowed": _as_bool(
            p4.get("quiver_supporting_channel_allowed")
        ),
        "real_p4_promotion_ready": _as_bool(p4.get("promotion_ready")),
    }


def _carry_forward_r24(r24: dict[str, Any]) -> dict[str, Any]:
    """R24 carry-forward. R24 reports QuIVer unavailable/not-
    implemented and TDB as a feature-gated metadata/chunk store
    placeholder. Safety fields are surfaced as booleans; absent
    fields surface as False (which is the safe default for the
    forbidden-direction flags)."""
    nested = r24.get("quiver_status")
    if not isinstance(nested, dict):
        nested = {}
    return {
        "r24_promotion_ready": _as_bool(r24.get("promotion_ready")),
        "r24_default_should_change": _as_bool(r24.get("default_should_change")),
        "r24_evidencecore_semantics_changed": _as_bool(
            r24.get("evidencecore_semantics_changed")
        ),
        "r24_quiver_implemented_in_rust": _as_bool(
            r24.get("quiver_implemented_in_rust")
            if "quiver_implemented_in_rust" in r24
            else nested.get("quiver_implemented")
        ),
        "r24_quiver_graph_implemented": _as_bool(
            r24.get("quiver_graph_implemented")
        ),
        "r24_quiver_quality_metrics_emitted": _as_bool(
            r24.get("quiver_quality_metrics_emitted")
        ),
        "r24_quiver_available": _as_bool(r24.get("quiver_available")),
    }


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------


def _compute_integrity(
    r33: dict[str, Any] | None,
    r34: dict[str, Any] | None,
    real_p3: dict[str, Any] | None,
    real_p4: dict[str, Any] | None,
    r24: dict[str, Any] | None,
) -> dict[str, Any]:
    # R24 nested quiver_status dict (if present) for the quiver-
    # implemented flag check.
    r24_nested: dict[str, Any] = {}
    if isinstance(r24, dict) and isinstance(r24.get("quiver_status"), dict):
        r24_nested = r24["quiver_status"]
    r24_quiver_implemented_in_rust = _as_bool(
        r24.get("quiver_implemented_in_rust")
        if r24 and "quiver_implemented_in_rust" in r24
        else (r24_nested.get("quiver_implemented") if r24 else None)
    )
    integrity: dict[str, Any] = {
        # All inputs that are present must be aggregate-only and not
        # promote.
        "r33_input_quiver_graph_implemented_false": (
            r33 is not None and r33.get("quiver_graph_implemented") is False
        ),
        "r33_input_quiver_quality_metrics_emitted_false": (
            r33 is not None and r33.get("quiver_quality_metrics_emitted") is False
        ),
        "r33_input_promotion_ready_false": (
            r33 is not None and r33.get("promotion_ready") is False
        ),
        "r34_input_quiver_mode_diagnostic_only": (
            r34 is not None and r34.get("quiver_mode") == "diagnostic_only"
        ),
        "r34_input_quiver_graph_implemented_false": (
            r34 is not None and r34.get("quiver_graph_implemented") is False
        ),
        "r34_input_promotion_ready_false": (
            r34 is not None and r34.get("promotion_ready") is False
        ),
        # real-provider P3: every safety flag fail-closed.
        "real_p3_input_quiver_graph_implemented_false": (
            real_p3 is not None
            and real_p3.get("quiver_graph_implemented") is False
        ),
        "real_p3_input_quiver_quality_metrics_emitted_false": (
            real_p3 is not None
            and real_p3.get("quiver_quality_metrics_emitted") is False
        ),
        "real_p3_input_promotion_ready_false": (
            real_p3 is not None and real_p3.get("promotion_ready") is False
        ),
        "real_p3_input_default_should_change_false": (
            real_p3 is not None
            and real_p3.get("default_should_change") is False
        ),
        "real_p3_input_evidencecore_semantics_changed_false": (
            real_p3 is not None
            and real_p3.get("evidencecore_semantics_changed") is False
        ),
        # real-provider P4: every safety flag fail-closed.
        "real_p4_input_quiver_mode_diagnostic_only": (
            real_p4 is not None and real_p4.get("quiver_mode") == "diagnostic_only"
        ),
        "real_p4_input_quiver_graph_implemented_false": (
            real_p4 is not None
            and real_p4.get("quiver_graph_implemented") is False
        ),
        "real_p4_input_promotion_ready_false": (
            real_p4 is not None and real_p4.get("promotion_ready") is False
        ),
        "real_p4_input_default_should_change_false": (
            real_p4 is not None
            and real_p4.get("default_should_change") is False
        ),
        "real_p4_input_evidencecore_semantics_changed_false": (
            real_p4 is not None
            and real_p4.get("evidencecore_semantics_changed") is False
        ),
        "real_p4_input_quiver_default_allowed_false_or_absent": (
            real_p4 is None or real_p4.get("quiver_default_allowed") is False
        ),
        # R24: promotion / default / EvidenceCore fail-closed when
        # present; any QuIVer-implemented flag true is a no-go
        # violation.
        "r24_input_promotion_ready_false": (
            r24 is not None and r24.get("promotion_ready") is False
        ),
        "r24_input_default_should_change_false_or_absent": (
            r24 is None or r24.get("default_should_change") in (False, None)
        ),
        "r24_input_evidencecore_semantics_changed_false_or_absent": (
            r24 is None
            or r24.get("evidencecore_semantics_changed") in (False, None)
        ),
        "r24_input_quiver_implemented_in_rust_false": (
            not r24_quiver_implemented_in_rust
        ),
        "r24_input_quiver_graph_implemented_false_or_absent": (
            r24 is None
            or r24.get("quiver_graph_implemented") in (False, None)
        ),
        "r24_input_quiver_quality_metrics_emitted_false_or_absent": (
            r24 is None
            or r24.get("quiver_quality_metrics_emitted") in (False, None)
        ),
        "r24_input_quiver_available_false_or_absent": (
            r24 is None or r24.get("quiver_available") in (False, None)
        ),
        "r24_input_no_quiver_implemented_flag_true": (
            # Composite flag: every QuIVer-implemented flag in R24
            # (top-level or nested quiver_status) must be false or
            # absent.
            r24 is None
            or (
                r24.get("quiver_implemented_in_rust") is not True
                and r24.get("quiver_graph_implemented") is not True
                and r24.get("quiver_quality_metrics_emitted") is not True
                and r24.get("quiver_available") is not True
                and r24_nested.get("quiver_implemented") is not True
                and r24_nested.get("quiver_graph_implemented") is not True
                and r24_nested.get("quiver_quality_metrics_emitted") is not True
                and r24_nested.get("quiver_available") is not True
            )
        ),
        # Aggregate flags: every input present must report quiver graph
        # NOT implemented. This is the central B17 no-go signal. R24 is
        # included via its quiver-implemented composite (an R24
        # artifact with any QuIVer-implemented flag true would flip
        # this to false).
        "all_present_inputs_quiver_graph_implemented_false": (
            all(
                inp is None or inp.get("quiver_graph_implemented") is False
                for inp in (r33, r34, real_p3, real_p4)
            )
            and (
                r24 is None
                or (
                    r24.get("quiver_graph_implemented") is not True
                    and r24.get("quiver_implemented_in_rust") is not True
                    and r24.get("quiver_available") is not True
                    and r24_nested.get("quiver_implemented") is not True
                )
            )
        ),
        "all_present_inputs_promotion_ready_false": all(
            inp is None or inp.get("promotion_ready") is False
            for inp in (r33, r34, real_p3, real_p4, r24)
        ),
        "forbidden_public_key_scan_clean": True,
    }
    return integrity


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


def screen(
    r33: dict[str, Any] | None,
    r34: dict[str, Any] | None,
    real_p3: dict[str, Any] | None,
    real_p4: dict[str, Any] | None,
    r24: dict[str, Any] | None,
    *,
    r33_status: str,
    r34_status: str,
    real_p3_status: str,
    real_p4_status: str,
    r24_status: str,
    self_test: bool = False,
) -> dict[str, Any]:
    """Build the B17 public-systems diagnostic carry-forward / no-go
    screen report.

    Each input is the parsed JSON for that diagnostic artifact, or
    ``None`` if the artifact was absent (the corresponding
    ``*_status`` is then ``"not_present"``).
    """
    if r33 is not None and r33_status == "loaded":
        _validate_r33(r33)
    if r34 is not None and r34_status == "loaded":
        _validate_r34_r36(r34)
    if real_p3 is not None and real_p3_status == "loaded":
        _validate_real_p3(real_p3)
    if real_p4 is not None and real_p4_status == "loaded":
        _validate_real_p4(real_p4)
    if r24 is not None and r24_status == "loaded":
        _validate_r24(r24)

    report = _base_report(self_test)
    report["input_artifacts_public_note"] = (
        "already-published aggregate-only public R33 R34 R36 real-"
        "provider P3 P4 and optional R24 diagnostic artifacts; no raw "
        "records paths prompts responses snippets diffs patches test "
        "results or private labels read by the screen"
    )
    report["input_status"] = {
        "r33_status": r33_status,
        "r34_r36_status": r34_status,
        "real_p3_status": real_p3_status,
        "real_p4_status": real_p4_status,
        "r24_status": r24_status,
    }

    if r33 is not None and r33_status == "loaded":
        report["input_r33_summary"] = _carry_forward_r33(r33)
    if r34 is not None and r34_status == "loaded":
        report["input_r34_r36_summary"] = _carry_forward_r34_r36(r34)
    if real_p3 is not None and real_p3_status == "loaded":
        report["input_real_p3_summary"] = _carry_forward_real_p3(real_p3)
    if real_p4 is not None and real_p4_status == "loaded":
        report["input_real_p4_summary"] = _carry_forward_real_p4(real_p4)
    if r24 is not None and r24_status == "loaded":
        report["input_r24_summary"] = _carry_forward_r24(r24)

    # Verdict: the central no-go signal is that the QuIVer/Vamana graph
    # backend is missing from every present public diagnostic. If at
    # least one diagnostic is present and all present diagnostics
    # confirm quiver_graph_implemented=false (and R24, if present,
    # carries no QuIVer-implemented flag true), the verdict is
    # no_go_quiver_graph_missing. If no diagnostic is present at all,
    # the screen falls back to diagnostic_carry_forward_only (still a
    # no-empirical-bakeoff verdict; just signals the screen itself was
    # unable to confirm the no-go via a carry-forward read).
    present_inputs = [
        inp
        for inp, status in (
            (r33, r33_status),
            (r34, r34_status),
            (real_p3, real_p3_status),
            (real_p4, real_p4_status),
        )
        if inp is not None and status == "loaded"
    ]
    r24_present = r24 is not None and r24_status == "loaded"
    r24_quiver_clean = True
    if r24 is not None and r24_present:
        r24_nested_v = r24.get("quiver_status")
        if not isinstance(r24_nested_v, dict):
            r24_nested_v = {}
        r24_quiver_clean = (
            r24.get("quiver_implemented_in_rust") is not True
            and r24.get("quiver_graph_implemented") is not True
            and r24.get("quiver_quality_metrics_emitted") is not True
            and r24.get("quiver_available") is not True
            and r24_nested_v.get("quiver_implemented") is not True
            and r24_nested_v.get("quiver_graph_implemented") is not True
            and r24_nested_v.get("quiver_quality_metrics_emitted") is not True
            and r24_nested_v.get("quiver_available") is not True
        )
    if present_inputs and all(
        inp.get("quiver_graph_implemented") is False for inp in present_inputs
    ) and r24_quiver_clean:
        verdict = "no_go_quiver_graph_missing"
        verdict_reason = (
            "every present public diagnostic reports "
            "quiver_graph_implemented false; the B17 QuIVer systems "
            "track cannot proceed without a QuIVer or Vamana graph "
            "backend implementation. No empirical B17 systems bakeoff "
            "was performed."
        )
    else:
        verdict = "diagnostic_carry_forward_only"
        verdict_reason = (
            "public diagnostics carry forward pre-B17 signals only; no "
            "empirical B17 QuIVer systems bakeoff was performed. No "
            "QuIVer or Vamana graph backend implementation; no HNSW "
            "backend run; no candidate-set equivalence matrix across "
            "backends."
        )

    report["verdict"] = verdict
    report["verdict_reason"] = verdict_reason
    report["allowed_verdicts"] = list(ALLOWED_VERDICTS)

    # Missing inputs (the specific gaps that block real B17).
    report["missing_inputs_for_real_b17"] = [dict(g) for g in MISSING_INPUTS]

    # Recommended next step (cautious, no auto-promotion).
    recommended_next_step = {
        "primary": "future_quiver_or_vamana_graph_backend_implementation_then_b17_systems_bakeoff",
        "secondary": "future_shared_frozen_candidate_quality_manifest",
        "reason": (
            "implement a QuIVer or Vamana graph backend and a shared "
            "frozen candidate-quality manifest, then run a B17 systems "
            "bakeoff with per-backend latency memory build update "
            "index size and candidate-set equivalence matrix versus a "
            "reference backend"
        ),
        "next_step_authorizes_promotion": False,
        "next_step_authorizes_default_change": False,
        "next_step_authorizes_backend_quality_promotion": False,
        "next_step_authorizes_retrieval_policy_change": False,
        "next_step_authorizes_quiver_graph_implementation": False,
        "next_step_authorizes_ann_backend_bakeoff": False,
        "next_step_authorizes_candidate_set_equivalence_validation": False,
        "next_step_authorizes_empirical_systems_bakeoff": False,
    }

    report.update(
        {
            "testability": {
                "full_b17_systems_bakeoff_possible_from_public_artifacts": False,
                "missing_inputs_for_full_b17": [
                    g["gap_id"] for g in MISSING_INPUTS
                ],
                "note": (
                    "real B17 cannot be replayed from public R33 R34 "
                    "R36 real-provider P3 P4 and optional R24 "
                    "diagnostics; the listed missing inputs are the "
                    "per-backend systems fields required"
                ),
            },
            "recommended_next_step": recommended_next_step,
            "integrity": _compute_integrity(r33, r34, real_p3, real_p4, r24),
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "evidencecore_semantics_changed_false": True,
                "retrieval_policy_changed_false": True,
                "backend_quality_promoted_false": True,
                "stage_is_quiver_systems_track": True,
                "quiver_graph_implemented_false": True,
                "ann_backend_bakeoff_performed_false": True,
                "candidate_set_equivalence_validated_false": True,
                "metrics_evaluated_false": True,
                "new_provider_calls_zero": True,
                "no_evidencecore_semantics_change": True,
                "no_retrieval_policy_change": True,
                "no_backend_quality_promotion": True,
                "no_live_llm_calls_by_screen": True,
                "no_ann_backend_bakeoff": True,
                "no_quiver_graph_implementation": True,
                "no_hnsw_backend_run": True,
                "no_vamana_graph_run": True,
                "no_candidate_set_equivalence_validation": True,
                "no_update_cost_benchmark": True,
                "no_build_time_index_size_benchmark": True,
                "no_stale_citation_cross_backend_validation": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_patches_or_diffs": True,
                "no_test_execution_results": True,
                "no_solve_labels": True,
                "no_agent_event_logs": True,
                "no_backend_event_logs": True,
                "no_index_build_records": True,
                "no_search_latency_records": True,
                "no_hot_memory_records": True,
                "no_index_size_records": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_winner_declared": True,
                "no_fake_ann_metrics_from_diagnostics": True,
                "diagnostics_do_not_imply_quiver_implementation": True,
                "diagnostics_do_not_imply_ann_quality": True,
                "diagnostics_do_not_imply_backend_promotion": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "backend_quality_promotion_claimed": False,
                "retrieval_policy_change_claimed": False,
                "quiver_graph_implementation_claimed": False,
                "empirical_systems_bakeoff_claimed": False,
                "ann_backend_bakeoff_claimed": False,
                "candidate_set_equivalence_validation_claimed": False,
                "winner_declared_claimed": False,
                "signal_strength": (
                    "bounded_public_systems_diagnostic_carry_forward_screen_only"
                ),
                "is_full_b17_quiver_systems_bakeoff": False,
                "recommended_next_step": (
                    "future_quiver_or_vamana_graph_backend_implementation_then_b17_systems_bakeoff"
                ),
            },
        }
    )

    _finalize_safety(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _build_synthetic_r33() -> dict[str, Any]:
    return {
        "schema_version": INPUT_R33_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "BQ_diagnostics_only": True,
        "quiver_graph_implemented": False,
        "quiver_quality_metrics_emitted": False,
        "not_promotion_evidence": True,
        "diagnostics": {
            "quiver_fit": "mixed",
            "recommendation": "continue_diagnostics_then_proto",
        },
    }


def _build_synthetic_r34_r36() -> dict[str, Any]:
    return {
        "schema_version": INPUT_R34_R36_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "quiver_mode": "diagnostic_only",
        "quiver_graph_implemented": False,
        "vamana_pruning_implemented": False,
        "bq_topk_implemented": True,
        "f32_rerank_implemented": True,
        "quiver_default_allowed": False,
        "quiver_supporting_channel_allowed": True,
        "dense_or_quiver_role": "candidate/supporting-only",
    }


def _build_synthetic_real_p3() -> dict[str, Any]:
    return {
        "schema_version": INPUT_R33_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "BQ_diagnostics_only": True,
        "quiver_graph_implemented": False,
        "quiver_quality_metrics_emitted": False,
        "diagnostics": {
            "quiver_fit": "mixed",
            "recommendation": "continue_diagnostics_then_proto",
        },
    }


def _build_synthetic_real_p4() -> dict[str, Any]:
    return {
        "schema_version": INPUT_R34_R36_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "quiver_mode": "diagnostic_only",
        "quiver_graph_implemented": False,
        "quiver_default_allowed": False,
        "quiver_supporting_channel_allowed": True,
    }


def _build_synthetic_r24() -> dict[str, Any]:
    return {
        "schema_version": "r24-v1",
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "quiver_implemented": False,
        "quiver_status": {
            "quiver_implemented": False,
            "quiver_graph_implemented": False,
            "quiver_quality_metrics_emitted": False,
            "quiver_available": False,
        },
    }


def _self_test_happy_path_no_go() -> dict[str, Any]:
    r33 = _build_synthetic_r33()
    r34 = _build_synthetic_r34_r36()
    real_p3 = _build_synthetic_real_p3()
    real_p4 = _build_synthetic_real_p4()
    r24 = _build_synthetic_r24()
    report = screen(
        r33=r33,
        r34=r34,
        real_p3=real_p3,
        real_p4=real_p4,
        r24=r24,
        r33_status="loaded",
        r34_status="loaded",
        real_p3_status="loaded",
        real_p4_status="loaded",
        r24_status="loaded",
        self_test=True,
    )
    assert report["schema_version"] == SCHEMA_VERSION, report["schema_version"]
    assert report["claim_level"] == CLAIM_LEVEL, report["claim_level"]
    # Safety fields preserved verbatim.
    for k, v in (
        ("aggregate_only_public_artifact", True),
        ("candidate_not_fact", True),
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("retrieval_policy_changed", False),
        ("backend_quality_promoted", False),
        ("stage_is_quiver_systems_track", True),
        ("quiver_graph_implemented", False),
        ("ann_backend_bakeoff_performed", False),
        ("candidate_set_equivalence_validated", False),
        ("metrics_evaluated", False),
        ("new_provider_calls", 0),
        ("full_b17_systems_bakeoff_possible_from_public_artifacts", False),
        ("winner_declared", False),
        ("promotion_declared", False),
        ("default_recommendation_declared", False),
        ("backend_quality_promotion_declared", False),
        ("retrieval_variant_promotion_declared", False),
        ("metrics_defined", True),
        ("gates_defined", True),
        ("no_fake_ann_metrics_from_diagnostics", True),
    ):
        assert report[k] == v, (k, report[k])
    # No-go verdict emitted because every present diagnostic confirms
    # quiver_graph_implemented=false.
    assert report["verdict"] == "no_go_quiver_graph_missing", report["verdict"]
    assert report["verdict"] in ALLOWED_VERDICTS, report["verdict"]
    assert "no empirical b17" in report["verdict_reason"].lower(), report[
        "verdict_reason"
    ]
    # Carry-forward summaries present and carry the expected flags.
    assert report["input_r33_summary"]["r33_quiver_graph_implemented"] is False
    assert (
        report["input_r33_summary"]["r33_quiver_quality_metrics_emitted"] is False
    )
    assert report["input_r34_r36_summary"]["r34_quiver_mode"] == "diagnostic_only"
    assert (
        report["input_r34_r36_summary"]["r34_quiver_graph_implemented"] is False
    )
    assert (
        report["input_r34_r36_summary"]["r34_dense_or_quiver_supporting_only"]
        is True
    )
    assert report["input_real_p3_summary"]["real_p3_quiver_graph_implemented"] is False
    assert report["input_real_p4_summary"]["real_p4_quiver_mode"] == "diagnostic_only"
    assert report["input_r24_summary"]["r24_promotion_ready"] is False
    # All missing inputs enumerated.
    missing_ids = [g["gap_id"] for g in report["missing_inputs_for_real_b17"]]
    expected_missing = tuple(g["gap_id"] for g in MISSING_INPUTS)
    assert missing_ids == list(expected_missing), missing_ids
    # Required missing inputs are present (the task spec).
    required_gap_ids = {
        "no_quiver_or_vamana_graph_backend_implementation",
        "no_hnsw_backend_run",
        "no_candidate_set_equivalence_matrix_across_backends",
        "no_update_cost_benchmark",
        "no_build_time_index_size_benchmark",
        "no_stale_citation_cross_backend_validation",
        "no_shared_frozen_candidate_quality_manifest",
        "no_large_repo_repeatable_systems_matrix",
    }
    assert required_gap_ids.issubset(set(missing_ids)), (
        required_gap_ids - set(missing_ids)
    )
    # CRITICAL: no fake metric values. metrics_evaluated=false.
    assert report["metrics_evaluated"] is False
    assert report["no_fake_ann_metrics_from_diagnostics"] is True
    # No candidate_set_overlap / gold_retention / latency / memory /
    # build_time / update_cost / index_size value fields.
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
    # Forbidden-key/value scan clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # No raw data carried.
    assert report["raw_paths_in_artifact"] is False
    assert report["raw_patches_diffs_stored"] is False
    assert report["raw_test_results_stored"] is False
    assert report["raw_solve_labels_stored"] is False
    assert report["raw_agent_event_logs_stored"] is False
    assert report["raw_backend_event_logs_stored"] is False
    assert report["raw_index_build_records_stored"] is False
    assert report["raw_search_latency_records_stored"] is False
    assert report["raw_hot_memory_records_stored"] is False
    assert report["raw_index_size_records_stored"] is False
    assert report["private_labels_committed"] is False
    assert report["run_ids_in_artifact"] is False
    # Integrity flags.
    integ = report["integrity"]
    assert integ["all_present_inputs_quiver_graph_implemented_false"] is True, integ
    assert integ["all_present_inputs_promotion_ready_false"] is True, integ
    assert integ["r33_input_quiver_graph_implemented_false"] is True, integ
    assert integ["r34_input_quiver_mode_diagnostic_only"] is True, integ
    assert integ["real_p3_input_quiver_graph_implemented_false"] is True, integ
    assert integ["real_p3_input_quiver_quality_metrics_emitted_false"] is True, integ
    assert integ["real_p3_input_promotion_ready_false"] is True, integ
    assert integ["real_p3_input_default_should_change_false"] is True, integ
    assert (
        integ["real_p3_input_evidencecore_semantics_changed_false"] is True
    ), integ
    assert integ["real_p4_input_quiver_mode_diagnostic_only"] is True, integ
    assert integ["real_p4_input_quiver_graph_implemented_false"] is True, integ
    assert integ["real_p4_input_promotion_ready_false"] is True, integ
    assert integ["real_p4_input_default_should_change_false"] is True, integ
    assert (
        integ["real_p4_input_evidencecore_semantics_changed_false"] is True
    ), integ
    assert (
        integ["real_p4_input_quiver_default_allowed_false_or_absent"] is True
    ), integ
    assert integ["r24_input_promotion_ready_false"] is True, integ
    assert (
        integ["r24_input_default_should_change_false_or_absent"] is True
    ), integ
    assert (
        integ["r24_input_evidencecore_semantics_changed_false_or_absent"]
        is True
    ), integ
    assert integ["r24_input_quiver_implemented_in_rust_false"] is True, integ
    assert (
        integ["r24_input_quiver_graph_implemented_false_or_absent"] is True
    ), integ
    assert (
        integ["r24_input_quiver_quality_metrics_emitted_false_or_absent"]
        is True
    ), integ
    assert (
        integ["r24_input_quiver_available_false_or_absent"] is True
    ), integ
    assert integ["r24_input_no_quiver_implemented_flag_true"] is True, integ
    print("self-test happy path (no_go_quiver_graph_missing): ok")
    return report


def _self_test_optional_artifacts_absent() -> None:
    """When r24 (and real-provider variants) are absent, the screen
    still emits a clean no-go with the absent artifacts reported as
    not_present rather than failing."""
    r33 = _build_synthetic_r33()
    r34 = _build_synthetic_r34_r36()
    report = screen(
        r33=r33,
        r34=r34,
        real_p3=None,
        real_p4=None,
        r24=None,
        r33_status="loaded",
        r34_status="loaded",
        real_p3_status="not_present",
        real_p4_status="not_present",
        r24_status="not_present",
        self_test=True,
    )
    assert report["verdict"] == "no_go_quiver_graph_missing", report["verdict"]
    assert report["input_status"]["real_p3_status"] == "not_present"
    assert report["input_status"]["real_p4_status"] == "not_present"
    assert report["input_status"]["r24_status"] == "not_present"
    # Absent artifacts must not produce carry-forward summaries.
    assert "input_real_p3_summary" not in report
    assert "input_real_p4_summary" not in report
    assert "input_r24_summary" not in report
    # Still no bakeoff / no metrics.
    assert report["ann_backend_bakeoff_performed"] is False
    assert report["candidate_set_equivalence_validated"] is False
    assert report["quiver_graph_implemented"] is False
    assert report["metrics_evaluated"] is False
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    print("self-test optional artifacts absent: ok")


def _self_test_no_artifacts_at_all() -> None:
    """When every artifact is absent, the screen falls back to
    diagnostic_carry_forward_only (still no empirical bakeoff)."""
    report = screen(
        r33=None,
        r34=None,
        real_p3=None,
        real_p4=None,
        r24=None,
        r33_status="not_present",
        r34_status="not_present",
        real_p3_status="not_present",
        real_p4_status="not_present",
        r24_status="not_present",
        self_test=True,
    )
    assert report["verdict"] == "diagnostic_carry_forward_only", report["verdict"]
    assert "no empirical b17" in report["verdict_reason"].lower()
    assert report["ann_backend_bakeoff_performed"] is False
    assert report["metrics_evaluated"] is False
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    print("self-test no artifacts at all: ok")


def _self_test_input_validation_blocks() -> None:
    """Input validation blocks for each upstream diagnostic artifact."""
    # Wrong R33 schema_version.
    bad = _build_synthetic_r33()
    bad["schema_version"] = "wrong"
    try:
        screen(
            r33=bad,
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert "unexpected R33 schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong R33 schema_version")

    # R33 quiver_graph_implemented=true rejected.
    bad = _build_synthetic_r33()
    bad["quiver_graph_implemented"] = True
    try:
        screen(
            r33=bad,
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert "quiver_graph_implemented=false" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject R33 quiver_graph_implemented=true"
        )

    # R34 quiver_mode=production rejected.
    bad34 = _build_synthetic_r34_r36()
    bad34["quiver_mode"] = "production"
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=bad34,
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert "quiver_mode=diagnostic_only" in str(exc), exc
    else:
        raise AssertionError("screen should reject R34 quiver_mode=production")

    # real-provider P3 schema_version wrong.
    bad_p3 = _build_synthetic_real_p3()
    bad_p3["schema_version"] = "wrong"
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=bad_p3,
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert "unexpected real-provider P3 schema_version" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject wrong real-provider P3 schema_version"
        )

    # real-provider P4 quiver_graph_implemented=true rejected.
    bad_p4 = _build_synthetic_real_p4()
    bad_p4["quiver_graph_implemented"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=bad_p4,
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P4 input must have quiver_graph_implemented=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject real-provider P4 quiver_graph_implemented=true"
        )

    # R24 promotion_ready=true rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["promotion_ready"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert "promotion_ready=false" in str(exc), exc
    else:
        raise AssertionError("screen should reject R24 promotion_ready=true")

    # ----- real-provider P3 fail-closed safety-field checks -----

    # P3 quiver_quality_metrics_emitted=true rejected.
    bad_p3 = _build_synthetic_real_p3()
    bad_p3["quiver_quality_metrics_emitted"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=bad_p3,
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P3 input must have "
            "quiver_quality_metrics_emitted=false"
        ) in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject P3 quiver_quality_metrics_emitted=true"
        )

    # P3 promotion_ready=true rejected.
    bad_p3 = _build_synthetic_real_p3()
    bad_p3["promotion_ready"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=bad_p3,
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P3 input must have promotion_ready=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P3 promotion_ready=true"
        )

    # P3 default_should_change=true rejected.
    bad_p3 = _build_synthetic_real_p3()
    bad_p3["default_should_change"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=bad_p3,
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P3 input must have default_should_change=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P3 default_should_change=true"
        )

    # P3 evidencecore_semantics_changed=true rejected.
    bad_p3 = _build_synthetic_real_p3()
    bad_p3["evidencecore_semantics_changed"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=bad_p3,
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P3 input must have "
            "evidencecore_semantics_changed=false"
        ) in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject P3 evidencecore_semantics_changed=true"
        )

    # P3 quiver_graph_implemented=true rejected.
    bad_p3 = _build_synthetic_real_p3()
    bad_p3["quiver_graph_implemented"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=bad_p3,
            real_p4=_build_synthetic_real_p4(),
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P3 input must have quiver_graph_implemented=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P3 quiver_graph_implemented=true"
        )

    # ----- real-provider P4 fail-closed safety-field checks -----

    # P4 quiver_mode=production rejected.
    bad_p4 = _build_synthetic_real_p4()
    bad_p4["quiver_mode"] = "production"
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=bad_p4,
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P4 input must have quiver_mode=diagnostic_only"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P4 quiver_mode=production"
        )

    # P4 default_should_change=true rejected.
    bad_p4 = _build_synthetic_real_p4()
    bad_p4["default_should_change"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=bad_p4,
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P4 input must have default_should_change=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P4 default_should_change=true"
        )

    # P4 evidencecore_semantics_changed=true rejected.
    bad_p4 = _build_synthetic_real_p4()
    bad_p4["evidencecore_semantics_changed"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=bad_p4,
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P4 input must have "
            "evidencecore_semantics_changed=false"
        ) in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject P4 evidencecore_semantics_changed=true"
        )

    # P4 promotion_ready=true rejected.
    bad_p4 = _build_synthetic_real_p4()
    bad_p4["promotion_ready"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=bad_p4,
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P4 input must have promotion_ready=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P4 promotion_ready=true"
        )

    # P4 quiver_graph_implemented=true rejected.
    bad_p4 = _build_synthetic_real_p4()
    bad_p4["quiver_graph_implemented"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=bad_p4,
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P4 input must have quiver_graph_implemented=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P4 quiver_graph_implemented=true"
        )

    # P4 quiver_default_allowed=true (when present) rejected.
    bad_p4 = _build_synthetic_real_p4()
    bad_p4["quiver_default_allowed"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=bad_p4,
            r24=_build_synthetic_r24(),
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "real-provider P4 input must have quiver_default_allowed=false"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject P4 quiver_default_allowed=true"
        )

    # ----- R24 fail-closed safety-field checks -----

    # R24 default_should_change=true (when present) rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["default_should_change"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "R24 input must have default_should_change=false when present"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject R24 default_should_change=true"
        )

    # R24 evidencecore_semantics_changed=true (when present) rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["evidencecore_semantics_changed"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "R24 input must have evidencecore_semantics_changed=false "
            "when present"
        ) in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject R24 evidencecore_semantics_changed=true"
        )

    # R24 top-level quiver_implemented_in_rust=true rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["quiver_implemented_in_rust"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "R24 input must have quiver_implemented_in_rust=false or absent"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject R24 quiver_implemented_in_rust=true"
        )

    # R24 top-level quiver_graph_implemented=true rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["quiver_graph_implemented"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "R24 input must have quiver_graph_implemented=false or absent"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject R24 quiver_graph_implemented=true"
        )

    # R24 top-level quiver_quality_metrics_emitted=true rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["quiver_quality_metrics_emitted"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "R24 input must have quiver_quality_metrics_emitted=false or "
            "absent"
        ) in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject R24 quiver_quality_metrics_emitted=true"
        )

    # R24 top-level quiver_available=true rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["quiver_available"] = True
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "R24 input must have quiver_available=false or absent"
            in str(exc)
        ), exc
    else:
        raise AssertionError(
            "screen should reject R24 quiver_available=true"
        )

    # R24 nested quiver_status.quiver_implemented=true rejected.
    bad_r24 = _build_synthetic_r24()
    bad_r24["quiver_status"] = {"quiver_implemented": True}
    try:
        screen(
            r33=_build_synthetic_r33(),
            r34=_build_synthetic_r34_r36(),
            real_p3=_build_synthetic_real_p3(),
            real_p4=_build_synthetic_real_p4(),
            r24=bad_r24,
            r33_status="loaded",
            r34_status="loaded",
            real_p3_status="loaded",
            real_p4_status="loaded",
            r24_status="loaded",
            self_test=True,
        )
    except ValueError as exc:
        assert (
            "R24 input must have quiver_status.quiver_implemented=false "
            "or absent"
        ) in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject R24 quiver_status.quiver_implemented=true"
        )

    print("self-test input validation blocks: ok")


def _self_test_forbidden_scan() -> None:
    """Forbidden-key scan catches injected raw paths / labels /
    backend-bakeoff artifacts."""
    bad_report = {
        "task_id": "leak",
        "path": "src/foo.rs",
        "snippet": "fn main(){}",
        "patch": "patch content",
        "solve_label": "True",
        "gold_spans": [[1, 2]],
        "private_labels": "x",
    }
    hits = b6lite._walk_forbidden(bad_report)
    flat = " ".join(hits)
    assert "task_id" in flat
    assert "path" in flat
    assert "snippet" in flat
    assert "gold_spans" in flat
    assert "private_labels" in flat
    print("self-test forbidden scan: ok")


def run_self_tests() -> dict[str, Any]:
    _self_test_happy_path_no_go()
    _self_test_optional_artifacts_absent()
    _self_test_no_artifacts_at_all()
    _self_test_input_validation_blocks()
    _self_test_forbidden_scan()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "happy_path_no_go": True,
            "optional_artifacts_absent": True,
            "no_artifacts_at_all": True,
            "input_validation_blocks": True,
            "forbidden_scan": True,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-r33",
        type=Path,
        default=DEFAULT_INPUT_R33,
        help=(
            "path to the R33 readiness diagnostic JSON (default: the "
            "canonical artifacts/r33/quiver_readiness.json)"
        ),
    )
    parser.add_argument(
        "--input-r34-r36",
        type=Path,
        default=DEFAULT_INPUT_R34_R36,
        help=(
            "path to the R34/R36 anchor proto diagnostic JSON (default: "
            "artifacts/r34_r36/quiver_anchor_proto.json)"
        ),
    )
    parser.add_argument(
        "--input-real-p3",
        type=Path,
        default=DEFAULT_INPUT_REAL_P3,
        help=(
            "path to the real-provider P3 quiver readiness diagnostic "
            "JSON (default: artifacts/real_provider/"
            "p3_real_quiver_readiness.json)"
        ),
    )
    parser.add_argument(
        "--input-real-p4",
        type=Path,
        default=DEFAULT_INPUT_REAL_P4,
        help=(
            "path to the real-provider P4 quiver anchor proto diagnostic "
            "JSON (default: artifacts/real_provider/"
            "p4_real_quiver_anchor_proto.json)"
        ),
    )
    parser.add_argument(
        "--input-r24",
        type=Path,
        default=DEFAULT_INPUT_R24,
        help=(
            "path to the R24 QuIVer/TDB/Dense probe JSON (default: "
            "runs/r24-quiver-tdb-probe.json). Optional; absent is "
            "reported as not_present."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the B17 public systems diagnostic screen "
            "report (default: artifacts/b17_quiver_systems_track/"
            "b17_public_systems_diagnostic_screen_report.json)"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the B17 public systems diagnostic screen self-test "
        "(synthetic fixture)",
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.self_test and (
        str(args.input_r33) != str(DEFAULT_INPUT_R33)
        or str(args.input_r34_r36) != str(DEFAULT_INPUT_R34_R36)
        or str(args.input_real_p3) != str(DEFAULT_INPUT_REAL_P3)
        or str(args.input_real_p4) != str(DEFAULT_INPUT_REAL_P4)
        or str(args.input_r24) != str(DEFAULT_INPUT_R24)
    ):
        parser.error(
            "--self-test ignores --input-r33/--input-r34-r36/"
            "--input-real-p3/--input-real-p4/--input-r24; do not pass "
            "both"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "B17 public systems diagnostic screen self-test: PASS",
            file=sys.stderr,
        )
        return 0
    r33, r33_status = _load_optional(args.input_r33)
    r34, r34_status = _load_optional(args.input_r34_r36)
    real_p3, real_p3_status = _load_optional(args.input_real_p3)
    real_p4, real_p4_status = _load_optional(args.input_real_p4)
    r24, r24_status = _load_optional(args.input_r24)
    report = screen(
        r33=r33,
        r34=r34,
        real_p3=real_p3,
        real_p4=real_p4,
        r24=r24,
        r33_status=r33_status,
        r34_status=r34_status,
        real_p3_status=real_p3_status,
        real_p4_status=real_p4_status,
        r24_status=r24_status,
        self_test=False,
    )
    _write_json(args.out, report)
    summary = {
        "schema_version": report["schema_version"],
        "claim_level": report["claim_level"],
        "self_test": report["self_test"],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "aggregate_only_public_artifact": report[
            "aggregate_only_public_artifact"
        ],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
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
        "backend_quality_promoted": report["backend_quality_promoted"],
        "retrieval_policy_changed": report["retrieval_policy_changed"],
        "metrics_evaluated": report["metrics_evaluated"],
        "no_fake_ann_metrics_from_diagnostics": report[
            "no_fake_ann_metrics_from_diagnostics"
        ],
        "full_b17_systems_bakeoff_possible_from_public_artifacts": report[
            "full_b17_systems_bakeoff_possible_from_public_artifacts"
        ],
        "new_provider_calls": report["new_provider_calls"],
        "input_status": report["input_status"],
        "missing_inputs_for_real_b17": [
            g["gap_id"] for g in report["missing_inputs_for_real_b17"]
        ],
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
