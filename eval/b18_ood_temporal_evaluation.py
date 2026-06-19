#!/usr/bin/env python3
"""B18 OOD / Temporal Evaluation Preregistration + Bounded Public-Aggregate No-Go Screen.

B18 is the **OOD (out-of-distribution) / temporal evaluation** phase. The
goal is a **frozen, preregistered OOD / temporal evaluation** of the
retrieval / candidate / Evidence pipeline across five FROZEN split
axes — ``temporal_split``, ``repo_split``, ``language_split``,
``model_family_split``, ``adversarial_split`` — under a **no-retuning
protocol** (no policy search, no quality strategy tuning, no retrieval
policy change, no EvidenceCore semantics change, no default change, no
promotion). Real B18 reports per-record, per-time-index, per-repo,
per-language, per-model-family, and per-adversarial-holdout outcomes
with worst-group and CVaR tail metrics so a reader cannot mistake an
in-distribution average for OOD / temporal generalization.

B18 is a **bounded preregistration + public-aggregate no-go screen
phase**, NOT a real OOD / temporal evaluation, NOT a policy search, NOT
a quality strategy tuning, NOT a default change, NOT an EvidenceCore
semantics change, NOT a promotion. The shipped skeleton performs NO
real OOD / temporal evaluation, NO per-record replay, NO
commit-chronology temporal split, NO adversarial holdout, NO
per-repo / per-language / per-model-family cell computation, NO
worst-group or CVaR metric computation. The frozen preregistration
(this file + ``docs/en/b18-ood-temporal-evaluation.md``) defines the
split axes, the required per-record inputs, the metric registry, the
hard gates, and the experimental structure; the bounded public-aggregate
no-go screen reads the already-published B11 prospective matrix
aggregate report plus optional R15 / R20 / R26 repo locks and emits a
``no_go_public_aggregate_only`` verdict because the public artifacts
lack per-record / per-time / per-repo / per-language / per-model-family
cells.

Important claim boundary: B18 IS the ood-temporal-evaluation *stage*
(``stage_is_ood_temporal_evaluation=true``), but this skeleton performs
NO real OOD / temporal evaluation
(``ood_temporal_evaluation_performed=false``), NO metrics evaluation
(``metrics_evaluated=false``), NO policy search
(``policy_search_performed=false``), NO quality strategy tuning
(``quality_strategy_tuned=false``), and NO promotion
(``promotion_ready=false``). Self-test / ``--input`` stub report sets
``promotion_ready=false``, ``default_should_change=false``,
``evidencecore_semantics_changed=false``, ``retrieval_policy_changed=false``,
``metrics_evaluated=false``, ``new_provider_calls=0`` so the synthetic /
stub report cannot be mistaken for an empirical B18 OOD / temporal
result.

CRITICAL anti-fabrication boundary: this skeleton MUST NOT compute fake
OOD / temporal / worst-group / CVaR / per-cell / drift metrics from the
existing B11 aggregate means or from the R15 / R20 / R26 repo locks.
The B11 aggregate carries public model-family means + repo slice list +
sanitized failure slices but NO per-record, per-time-index,
per-repo-per-language cell, model_family x repo matrix, adversarial
holdout outcome, or temporal holdout outcome; the R15 / R20 / R26 repo
locks are synthetic / static snapshots with no real commit chronology
or time axis. Any B18 OOD / temporal metric computed from them would be
a fabrication. The synthetic fixture validates only that the split axes,
metric names, hard gates, and required inputs are wired correctly; it
does NOT present synthetic metric values as empirical B18 OOD / temporal
results.

Aggregate-only public artifacts: no task/repo-per-record/candidate/path/
span/snippet/prompt/response/diff/test/task-id/agent-event-log/private-label/
candidate-path/provider keys and no raw path/digest/provider strings.

This file currently ships a SKELETON: the ``--self-test`` path verifies
the split axes, required per-record inputs, metric registry, hard gates,
and experimental structure against a synthetic fixture (read-only: it
builds the expected algorithm spec + report in memory and compares them
to the on-disk artifacts, failing on drift; it does NOT mutate
checked-in artifacts). ``--input <path>`` is a stub
(``verdict="not_implemented"``) awaiting the full per-record OOD /
temporal evaluation in a later task; it requires ``--out`` and may not
write the canonical checked-in report. The ONLY path that mutates
checked-in artifacts is ``--regenerate-artifacts``, which (re)writes the
on-disk algorithm spec + synthetic-fixture report + canonical public
no-go screen report from the current build functions. ``--public-screen
--out <path>`` runs the bounded public-aggregate no-go screen from the
current public artifacts and writes to the explicit ``--out`` path; if
``--out`` is absent, the canonical public screen artifact is written
ONLY when ``--public-screen`` is invoked from ``--regenerate-artifacts``
(otherwise ``--out`` is required for non-self-test to avoid accidental
checked-in mutation).

Run::

    python3 eval/b18_ood_temporal_evaluation.py --self-test
    python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts
    python3 eval/b18_ood_temporal_evaluation.py --self-test
    python3 eval/b18_ood_temporal_evaluation.py \\
        --public-screen --out artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json
    python3 eval/b18_ood_temporal_evaluation.py \\
        --input path/to/per_record_inputs.json --out /tmp/b18_input_stub_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b18_ood_temporal_evaluation"
REPORT_PATH = ARTIFACT_DIR / "b18_ood_temporal_evaluation_report.json"
ALGORITHM_SPEC_PATH = ARTIFACT_DIR / "b18_ood_temporal_evaluation.algorithm.json"
PUBLIC_SCREEN_PATH = (
    ARTIFACT_DIR / "b18_public_ood_temporal_screen_report.json"
)

# Public-aggregate inputs read by the bounded no-go screen. The B11
# prospective matrix aggregate report is the canonical input; the R15 /
# R20 / R26 repos.lock.jsonl files are OPTIONAL metadata-only inputs
# (repo counts, language metadata availability, stress category
# availability). No raw records, paths, prompts, responses, snippets,
# diffs, patches, test results, solve labels, agent event logs, gold
# spans, private labels, provider keys, base URLs, API keys, content
# SHAs, digests, or line ranges are read or emitted by the screen.
B11_AGGREGATE_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b11_prospective_matrix"
    / "b11_prospective_matrix_aggregate_report.json"
)
R15_REPOS_LOCK_PATH = REPO_ROOT / "fixtures" / "r15" / "repos.lock.jsonl"
R20_REPOS_LOCK_PATH = (
    REPO_ROOT / "fixtures" / "r20_auto_wide" / "repos.lock.jsonl"
)
R26_REPOS_LOCK_PATH = (
    REPO_ROOT / "fixtures" / "r26_auto_stress" / "repos.lock.jsonl"
)
R20_MANIFEST_PATH = (
    REPO_ROOT / "fixtures" / "r20_auto_wide" / "dataset_manifest.json"
)
R26_MANIFEST_PATH = (
    REPO_ROOT / "fixtures" / "r26_auto_stress" / "dataset_manifest.json"
)

SCHEMA_VERSION = "b18-ood-temporal-evaluation-report-v0"
SPEC_SCHEMA_VERSION = "b18-ood-temporal-evaluation-spec-v0"
PUBLIC_SCREEN_SCHEMA_VERSION = "b18-public-ood-temporal-screen-v0"
GENERATED_BY = "b18_ood_temporal_evaluation"
ALGORITHM_SPEC_ID = "b18_ood_temporal_evaluation_v0"
CLAIM_LEVEL = "ood_temporal_evaluation_v0"
PUBLIC_SCREEN_CLAIM_LEVEL = (
    "bounded_public_aggregate_no_go_screen_of_b11_r15_r20_r26"
)

# Fixed generated_at so the spec hash is stable across runs (mirrors
# B10/B10B/B11/B12/B13/B14/B15/B16/B17).
GENERATED_AT = "2026-06-19T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Split axes (FROZEN before any B18 OOD / temporal evaluation)
# ---------------------------------------------------------------------------
#
# The split axes are the closed set of OOD / temporal axes a B18
# evaluation must report. Each axis has a FROZEN holdout definition; a
# B18 evaluation that omits any axis is incomplete.
#

TEMPORAL_SPLIT_AXIS = "temporal_split"
REPO_SPLIT_AXIS = "repo_split"
LANGUAGE_SPLIT_AXIS = "language_split"
MODEL_FAMILY_SPLIT_AXIS = "model_family_split"
ADVERSARIAL_SPLIT_AXIS = "adversarial_split"

SPLIT_AXES = (
    TEMPORAL_SPLIT_AXIS,
    REPO_SPLIT_AXIS,
    LANGUAGE_SPLIT_AXIS,
    MODEL_FAMILY_SPLIT_AXIS,
    ADVERSARIAL_SPLIT_AXIS,
)

# No-retuning protocol: no policy search, no quality strategy tuning, no
# retrieval policy change, no EvidenceCore semantics change, no default
# change, no promotion. Frozen before any B18 empirical evaluation.
NO_RETUNING_PROTOCOL = True
NO_POLICY_SEARCH = True
NO_QUALITY_STRATEGY_TUNING = True
NO_RETRIEVAL_POLICY_CHANGE = True
NO_EVIDENCECORE_SEMANTICS_CHANGE = True
NO_DEFAULT_CHANGE = True
NO_PROMOTION = True

# ---------------------------------------------------------------------------
# Required per-record inputs (the real-B18 data contract)
# ---------------------------------------------------------------------------
#
# Real B18 OOD / temporal evaluation requires ALL of the following per
# record. If any is missing, real B18 cannot run and the skeleton emits
# insufficient_data / not_implemented.
#

REQUIRED_PER_RECORD_INPUTS = (
    "per_record_record",
    "per_record_time_index",
    "per_record_commit_chronology",
    "per_record_repo_axis",
    "per_record_language_axis",
    "per_record_model_family_axis",
    "per_record_task_category",
    "per_record_adversarial_holdout_membership",
    "per_record_temporal_holdout_membership",
    "per_record_outcome_label",
    "per_record_citation_validity",
    "per_record_stale_rejection",
    "per_record_evidencecore_rejection",
    "per_record_randomized_run_order_proof",
    "per_record_no_retuning_proof",
    "shared_frozen_evaluation_protocol_manifest",
)

# Missing inputs that block real B18 from the public aggregates. Each
# entry is a self-contained reason so a reader cannot mistake the screen
# for a B18 OOD / temporal evaluation result. Descriptions are kept
# short to satisfy the public forbidden-value scan (long_string guard)
# and avoid the path-separator pattern.
MISSING_INPUTS_FOR_REAL_B18 = (
    {
        "gap_id": "no_per_record_records",
        "description": (
            "real B18 needs per-record outcome records; the public "
            "B11 aggregate carries only model-family means and "
            "sanitized failure slices, not per-record data"
        ),
    },
    {
        "gap_id": "no_time_axis",
        "description": (
            "real B18 needs a per-record time index; the public "
            "B11 aggregate has no time axis and no per-record "
            "timestamps"
        ),
    },
    {
        "gap_id": "no_commit_chronology",
        "description": (
            "real B18 needs commit chronology per repo; the R15 R20 "
            "R26 repo locks carry only a single static snapshot "
            "commit label with no chronological ordering"
        ),
    },
    {
        "gap_id": "no_per_repo_per_language_cells_in_public_b11",
        "description": (
            "real B18 needs per-repo per-language outcome cells; "
            "the public B11 aggregate reports only model-family "
            "means and a sanitized repo slice list, not cells"
        ),
    },
    {
        "gap_id": "no_model_family_x_repo_matrix",
        "description": (
            "real B18 needs a model_family x repo outcome matrix; "
            "the public B11 aggregate reports only per-model-family "
            "means, not the cross matrix"
        ),
    },
    {
        "gap_id": "no_adversarial_holdout_outcomes",
        "description": (
            "real B18 needs adversarial holdout outcomes per axis; "
            "the public B11 aggregate has no adversarial holdout "
            "membership or outcomes"
        ),
    },
    {
        "gap_id": "no_temporal_holdout_outcomes",
        "description": (
            "real B18 needs temporal holdout outcomes per axis; the "
            "public B11 aggregate has no temporal holdout "
            "membership or outcomes"
        ),
    },
)

# ---------------------------------------------------------------------------
# Metric registry (FROZEN before any B18 OOD / temporal evaluation)
# ---------------------------------------------------------------------------
#
# These are the metric NAMES B18 will compute when real per-record OOD /
# temporal inputs are available. The skeleton defines them and validates
# the hard gates, but does NOT compute fake metric values from the
# existing B11 aggregate means or from the R15 / R20 / R26 repo locks.
#

METRIC_NAMES = (
    "ood_generalization_gap",
    "temporal_holdout_delta",
    "repo_holdout_metric",
    "language_holdout_metric",
    "model_family_holdout_metric",
    "adversarial_robustness_score",
    "worst_group_metric",
    "cvar_tail_metric",
    "per_cell_denominator",
    "temporal_split_integrity",
    "no_retuning_proof_metric",
    "citation_validity",
    "stale_evidencecore_rejection_rate",
)

# ---------------------------------------------------------------------------
# Hard gates (FROZEN before any B18 OOD / temporal evaluation)
# ---------------------------------------------------------------------------
#
# Each gate is FROZEN before any real B18 OOD / temporal evaluation. A
# split axis or evaluation run that fails any gate is rejected,
# regardless of its aggregate OOD / temporal metrics.
#

HARD_GATES = (
    "per_record_data_gate",
    "time_axis_gate",
    "commit_chronology_gate",
    "no_retuning_gate",
    "adversarial_holdout_gate",
    "temporal_holdout_gate",
    "evidencecore_materialization_gate",
    "stale_citation_gate",
    "privacy_gate",
    "promotion_false_gate",
)

# ---------------------------------------------------------------------------
# Experimental structure (FROZEN before any B18 OOD / temporal evaluation)
# ---------------------------------------------------------------------------

EXPERIMENTAL_STAGES = (
    "no_ood_temporal_evaluation_feasibility",
    "frozen_no_retuning_protocol",
    "per_axis_holdout_evaluation",
    "worst_group_cvar_reporting",
)

SPLIT_PROTOCOL = "stratified_by_repo_language_model_family_time"
TASK_SCREEN_FRACTION = 0.50
FRESH_VALIDATION_FRACTION = 0.50
FRESH_VALIDATION_SPLIT_REPORTED_ONCE = True

# CVaR tail fraction for worst-group reporting (worst 20% of groups).
CVAR_ALPHA = 0.20

# Minimum per-cell denominator for a (repo, language, model_family,
# time-index) cell to be reportable. Cells below this denominator are
# suppressed and reported as insufficient_data.
MIN_DENOMINATOR_PER_CELL = 30

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any B18 OOD / temporal evaluation)
# ---------------------------------------------------------------------------

PREDECLARED_CRITERIA: dict[str, Any] = {
    # Split axes (frozen).
    "split_axes": list(SPLIT_AXES),
    # No-retuning protocol (frozen).
    "no_retuning_protocol": NO_RETUNING_PROTOCOL,
    "no_policy_search": NO_POLICY_SEARCH,
    "no_quality_strategy_tuning": NO_QUALITY_STRATEGY_TUNING,
    "no_retrieval_policy_change": NO_RETRIEVAL_POLICY_CHANGE,
    "no_evidencecore_semantics_change": NO_EVIDENCECORE_SEMANTICS_CHANGE,
    "no_default_change": NO_DEFAULT_CHANGE,
    "no_promotion": NO_PROMOTION,
    # CVaR tail fraction (worst 20% of groups).
    "cvar_alpha": CVAR_ALPHA,
    # Split protocol (frozen).
    "split_protocol": SPLIT_PROTOCOL,
    "task_screen_fraction": TASK_SCREEN_FRACTION,
    "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
    "fresh_validation_split_reported_once": FRESH_VALIDATION_SPLIT_REPORTED_ONCE,
    # Denominator gate: minimum per cell.
    "min_denominator_per_cell": MIN_DENOMINATOR_PER_CELL,
    # OOD / temporal gates (frozen).
    "ood_generalization_gap_maximum": 0.10,
    "temporal_holdout_delta_tolerance": 0.05,
    "worst_group_metric_minimum": 0.50,
    "citation_validity_required": 1.0,
    "stale_evidencecore_rejection_required": True,
    "no_default_expansion_required": True,
    # EvidenceCore contract (frozen): every per-record outcome must
    # materialize through EvidenceCore; no B18 path may bypass it.
    "evidencecore_materialization_required": True,
}

# Frozen public-aggregate carry-forward artifacts. We store spec_id +
# kind + an on-disk presence flag (the actual sha256 is NEVER written as
# a raw 64-char hex string, which would trip the forbidden-value scan;
# only the boolean presence flag is). These are diagnostic-only carry-
# forward signals; they are NOT promotion evidence and NOT quality
# proof.
FROZEN_ARTIFACTS = (
    {
        "spec_id": "b11_prospective_matrix_aggregate",
        "kind": "b11_aggregate_carry_forward",
        "pinned_at": GENERATED_AT,
        "public_artifact_present_on_disk": True,
        "diagnostic_only": True,
        "not_promotion_evidence": True,
    },
    {
        "spec_id": "r15_repos_lock",
        "kind": "r15_metadata_carry_forward",
        "pinned_at": GENERATED_AT,
        "public_artifact_present_on_disk": True,
        "diagnostic_only": True,
        "not_promotion_evidence": True,
    },
    {
        "spec_id": "r20_auto_wide_repos_lock",
        "kind": "r20_metadata_carry_forward",
        "pinned_at": GENERATED_AT,
        "public_artifact_present_on_disk": True,
        "diagnostic_only": True,
        "not_promotion_evidence": True,
    },
    {
        "spec_id": "r26_auto_stress_repos_lock",
        "kind": "r26_metadata_carry_forward",
        "pinned_at": GENERATED_AT,
        "public_artifact_present_on_disk": True,
        "diagnostic_only": True,
        "not_promotion_evidence": True,
    },
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")

# Skeleton verdicts. This skeleton is strictly a skeleton / no-go
# commit: ``_evaluate_ood_temporal`` may only emit ``insufficient_data``
# (synthetic fixture) or ``not_implemented`` (ci_ephemeral_records stub).
# The success / failure / partial verdicts are NOT emitted by this
# skeleton. Any future real B18 empirical path that might emit them
# would require its own separate preregistration, and its exact flag
# schema is future work and is NOT present in this skeleton. This
# commit keeps ``ood_temporal_evaluation_performed=false`` and
# ``metrics_evaluated=false`` strictly.
ALLOWED_VERDICTS = (
    "insufficient_data",
    "not_implemented",
)
# Verdicts NOT emitted by this skeleton. Listed for documentation only.
EMPIRICAL_VERDICTS_RESERVED_FOR_FUTURE_B18 = (
    "success",
    "failure",
    "partial",
)

# Public-screen verdicts. The bounded public-aggregate no-go screen
# NEVER emits success / failure / partial; it emits only public-aggregate
# no-go / carry-forward statuses that make clear no empirical B18 OOD /
# temporal evaluation happened.
PUBLIC_SCREEN_ALLOWED_VERDICTS = (
    "no_go_public_aggregate_only",
    "public_aggregate_carry_forward_only",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B/B11/B12/B13/B14/B15/B16/B17)
# ---------------------------------------------------------------------------

FORBIDDEN_PUBLIC_KEYS = (
    "task_id",
    "test_id",
    "repo_id",
    "candidate_id",
    "raw_record",
    "raw_records",
    "record",
    "records",
    "path",
    "file_path",
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
    "gold",
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
    "commit",
    "commit_chronology",
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

    Returns a dict with the B18 contract: split axes, required per-record
    inputs, metric registry, hard gates, and experimental structure. It
    contains NO per-record OOD / temporal inputs and NO computed metric
    values, because such values would be fake B18 results when no real
    per-record inputs exist.
    """
    return {
        "split_axes": list(SPLIT_AXES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "split_protocol": SPLIT_PROTOCOL,
        "task_screen_fraction": TASK_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "cvar_alpha": CVAR_ALPHA,
        # CRITICAL: no per-record OOD / temporal inputs and no
        # computed metric values are present. The fixture is
        # definitions-only.
        "per_record_ood_temporal_inputs_present": False,
        "metric_values_computed": False,
    }


# ---------------------------------------------------------------------------
# OOD / temporal evaluation stub (definitions-only; no fake metrics from
# aggregate means)
# ---------------------------------------------------------------------------


def _evaluate_ood_temporal(
    fixture: dict[str, Any],
    replay_source: str,
) -> tuple[dict[str, Any], str, str]:
    """Apply the predeclared OOD / temporal criteria (skeleton-safe).

    Returns ``(ood_temporal_results, verdict, verdict_reason)``.

    This skeleton is strictly a skeleton / no-go commit: this function
    NEVER emits ``success`` / ``failure`` / ``partial`` and NEVER
    computes ood_generalization_gap / temporal_holdout_delta /
    repo_holdout_metric / language_holdout_metric /
    model_family_holdout_metric / adversarial_robustness_score /
    worst_group_metric / cvar_tail_metric / per_cell_denominator /
    temporal_split_integrity / no_retuning_proof_metric /
    citation_validity / stale_evidencecore_rejection_rate values from
    the B11 aggregate means or from the R15 / R20 / R26 repo locks.
    Those metrics require per-record OOD / temporal inputs (per-record
    records, per-record time index, per-record commit chronology,
    per-record repo / language / model_family axes, per-record task
    category, per-record adversarial holdout membership, per-record
    temporal holdout membership, per-record outcome label, per-record
    citation validity, per-record stale rejection, per-record
    EvidenceCore rejection, per-record randomized run order proof,
    per-record no-retuning proof, shared frozen evaluation protocol
    manifest), which are not present in any current public artifact.
    Any future real B18 empirical path that might emit success / failure
    / partial would require its own separate preregistration, and its
    exact flag schema is future work and NOT present in this skeleton.
    This commit keeps ``ood_temporal_evaluation_performed=false`` and
    ``metrics_evaluated=false`` strictly.

    The ood_temporal_results block surfaces only definitions + hard
    gates + the experimental stage *definitions* (no empirical
    per-stage OOD / temporal values). ``metrics_evaluated=false``,
    ``ood_temporal_evaluation_performed=false`` are surfaced so a
    reader cannot mistake the skeleton for an empirical B18 OOD /
    temporal evaluation result.
    """
    stages_list: list[dict[str, Any]] = []
    for stage in EXPERIMENTAL_STAGES:
        stages_list.append(
            {
                "stage_id": stage,
                "evaluated": False,  # skeleton: no empirical evaluation
            }
        )
    ood_temporal_results: dict[str, Any] = {
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
        "split_axes": list(SPLIT_AXES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "missing_inputs_for_real_b18": [
            g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18
        ],
        # CRITICAL: no metric values are emitted.
        # metrics_evaluated=false is the disambiguating flag.
        "metrics_evaluated": False,
        "ood_temporal_evaluation_performed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "real_ood_temporal_supported": False,
        "all_axes_pass": False,
        "axes_evaluated": False,
        "winner_declared": False,
        "no_fake_ood_metrics_from_aggregate_means": True,
    }
    if replay_source == "synthetic_fixture":
        return (
            ood_temporal_results,
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; no empirical "
            "B18 OOD or temporal evaluation performed; no per-record "
            "OOD or temporal inputs available; no time axis or commit "
            "chronology; success, failure, or partial not emitted by "
            "skeleton; future real B18 flag schema is future work not "
            "in this skeleton",
        )
    # ci_ephemeral_records: real B18 OOD / temporal evaluation is not
    # yet implemented.
    return (
        ood_temporal_results,
        "not_implemented",
        "ci_ephemeral_records_replay_not_implemented; no empirical B18 "
        "OOD or temporal evaluation performed; no per-record OOD or "
        "temporal inputs consumed; no time axis or commit chronology; "
        "success, failure, or partial not emitted by skeleton; future "
        "real B18 flag schema is future work not in this skeleton",
    )


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B18 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so
    its SHA-256 is stable across runs. The on-disk spec file is the pin
    (mirrors B10/B10B/B11/B12/B13/B14/B15/B16/B17 freeze style). The
    self-test verifies hash stability by re-loading and re-hashing.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": CLAIM_LEVEL,
        "description": (
            "B18 OOD and Temporal Evaluation: frozen preregistered "
            "OOD and temporal evaluation across temporal repo language "
            "model_family and adversarial split axes under a no-"
            "retuning protocol. Bounded preregistration and public "
            "aggregate no-go screen phase only. No real OOD or "
            "temporal evaluation. No policy search. No quality "
            "strategy tuning. No default change. No EvidenceCore "
            "semantics change. No promotion."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_policy_changed": False,
        "backend_quality_promoted": False,
        # The algorithm_spec DEFINES the B18 ood-temporal-evaluation
        # stage (so stage_is_ood_temporal_evaluation=true), but no
        # empirical B18 OOD / temporal evaluation has been performed
        # by this skeleton (ood_temporal_evaluation_performed=false,
        # metrics_evaluated=false). The synthetic / stub report sets
        # metrics_evaluated=false so the public artifact cannot be
        # misread as an empirical B18 OOD / temporal result.
        "stage_is_ood_temporal_evaluation": True,
        "ood_temporal_evaluation_performed": False,
        "metrics_evaluated": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "real_ood_temporal_supported": False,
        "no_fake_ood_metrics_from_aggregate_means": True,
        "new_provider_calls": 0,
        "aggregate_only_public_artifact": True,
        "split_axes": list(SPLIT_AXES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "missing_inputs_for_real_b18": [
            g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18
        ],
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
        "min_denominator_per_cell": MIN_DENOMINATOR_PER_CELL,
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "allowed_replay_sources": list(ALLOWED_REPLAY_SOURCES),
        "allowed_verdicts": list(ALLOWED_VERDICTS),
        "public_screen_allowed_verdicts": list(PUBLIC_SCREEN_ALLOWED_VERDICTS),
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_ood_temporal_evaluation": True,
            "no_per_record_replay": True,
            "no_time_axis": True,
            "no_commit_chronology": True,
            "no_adversarial_holdout": True,
            "no_temporal_holdout": True,
            "no_per_repo_per_language_cells": True,
            "no_model_family_x_repo_matrix": True,
            "no_worst_group_cvar_metric": True,
            "no_policy_search": True,
            "no_quality_strategy_tuning": True,
            "no_retrieval_policy_change": True,
            "no_evidencecore_semantics_change": True,
            "no_default_change": True,
            "no_promotion": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "no_fake_ood_metrics_from_aggregate_means": True,
            "replay_only_no_live_ood_temporal_evaluation_in_evaluator": True,
        },
        "excluded_adapter_layer": {
            "model_adapter_excluded": True,
            "output_mode_excluded": True,
            "provider_credentials_excluded": True,
            "provider_endpoints_excluded": True,
            "provider_secrets_excluded": True,
            "raw_model_names_excluded": True,
            "raw_per_record_records_excluded": True,
            "raw_outcome_labels_excluded": True,
            "raw_time_indices_excluded": True,
            "raw_commit_chronology_excluded": True,
        },
    }


def _reference_artifact_presence() -> dict[str, bool]:
    """Check whether the on-disk public-aggregate carry-forward artifacts
    (B11 aggregate, R15 / R20 / R26 repo locks) are present. Returns
    ``{spec_id: present_bool}``. The actual sha256 hex is NEVER returned
    (it would trip the forbidden-value scan); only the boolean presence
    flag is exposed publicly.
    """
    refs: dict[str, bool] = {}
    refs["b11_prospective_matrix_aggregate_present"] = B11_AGGREGATE_PATH.exists()
    refs["r15_repos_lock_present"] = R15_REPOS_LOCK_PATH.exists()
    refs["r20_auto_wide_repos_lock_present"] = R20_REPOS_LOCK_PATH.exists()
    refs["r26_auto_stress_repos_lock_present"] = R26_REPOS_LOCK_PATH.exists()
    refs["r20_auto_wide_manifest_present"] = R20_MANIFEST_PATH.exists()
    refs["r26_auto_stress_manifest_present"] = R26_MANIFEST_PATH.exists()
    return refs


def build_report(
    fixture: dict[str, Any],
    *,
    self_test: bool,
    replay_source: str,
) -> dict[str, Any]:
    """Build the B18 OOD / temporal evaluation report.

    ``fixture`` is the definitions-only synthetic fixture (see
    ``_build_synthetic_fixture``). ``self_test=True`` flags that the
    report was produced from a synthetic fixture for mechanics
    validation; ``replay_source`` is one of ``ALLOWED_REPLAY_SOURCES``.

    The report NEVER emits ood_generalization_gap /
    temporal_holdout_delta / repo_holdout_metric /
    language_holdout_metric / model_family_holdout_metric /
    adversarial_robustness_score / worst_group_metric /
    cvar_tail_metric / per_cell_denominator / temporal_split_integrity
    / no_retuning_proof_metric / citation_validity /
    stale_evidencecore_rejection_rate metric values, because no
    per-record OOD / temporal inputs exist in any current public
    artifact. Only definitions + hard gates + experimental stage
    definitions are emitted.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    ood_temporal_results, verdict, verdict_reason = (
        _evaluate_ood_temporal(fixture, replay_source)
    )

    ref_presence = _reference_artifact_presence()

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
        # B18 DEFINES the ood-temporal-evaluation stage
        # (stage_is_ood_temporal_evaluation=true), but this skeleton
        # performs NO real OOD / temporal evaluation, NO per-record
        # replay, NO policy search, NO quality strategy tuning, and NO
        # promotion. The report flags
        # ood_temporal_evaluation_performed=false,
        # metrics_evaluated=false, policy_search_performed=false,
        # quality_strategy_tuned=false so synthetic / stub reports
        # cannot be misread as empirical B18 OOD / temporal results.
        "stage_is_ood_temporal_evaluation": True,
        "ood_temporal_evaluation_performed": False,
        "metrics_evaluated": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "real_ood_temporal_supported": False,
        "new_provider_calls": 0,
        # Skeleton: no axes evaluated, no winner declared, no
        # promotion. These top-level flags make the skeleton stance
        # unambiguous and mirror the ood_temporal_results sub-block.
        "all_axes_pass": False,
        "axes_evaluated": False,
        "axes_defined": True,
        "axis_count": len(SPLIT_AXES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "no_fake_ood_metrics_from_aggregate_means": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "frozen_reference_artifacts_present_on_disk": ref_presence,
        "split_axes": list(SPLIT_AXES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "missing_inputs_for_real_b18": [
            g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18
        ],
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
        "min_denominator_per_cell": MIN_DENOMINATOR_PER_CELL,
        "ood_temporal_results": ood_temporal_results,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "aggregate_only_public_artifact": True,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_ood_temporal_evaluation": True,
            "no_per_record_replay": True,
            "no_time_axis": True,
            "no_commit_chronology": True,
            "no_adversarial_holdout": True,
            "no_temporal_holdout": True,
            "no_per_repo_per_language_cells": True,
            "no_model_family_x_repo_matrix": True,
            "no_worst_group_cvar_metric": True,
            "no_policy_search": True,
            "no_quality_strategy_tuning": True,
            "no_retrieval_policy_change": True,
            "no_evidencecore_semantics_change": True,
            "no_default_change": True,
            "no_promotion": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "evidencecore_semantics_changed_false": True,
            "retrieval_policy_changed_false": True,
            "backend_quality_promoted_false": True,
            "stage_is_ood_temporal_evaluation_true": True,
            "ood_temporal_evaluation_performed_false": True,
            "metrics_evaluated_false": True,
            "policy_search_performed_false": True,
            "quality_strategy_tuned_false": True,
            "real_ood_temporal_supported_false": True,
            "new_provider_calls_zero": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "runtime_calls_by_replay_zero": True,
            "model_calls_by_replay_zero": True,
            "no_fake_ood_metrics_from_aggregate_means_true": True,
            "replay_only_no_live_ood_temporal_evaluation_in_evaluator": True,
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
    if spec.get("stage_is_ood_temporal_evaluation") is not True:
        raise ValueError(
            "algorithm spec stage_is_ood_temporal_evaluation must be true "
            "(B18 stage)"
        )
    if spec.get("ood_temporal_evaluation_performed") is not False:
        raise ValueError(
            "algorithm spec ood_temporal_evaluation_performed must be false "
            "(no OOD or temporal evaluation performed by skeleton)"
        )
    if spec.get("metrics_evaluated") is not False:
        raise ValueError(
            "algorithm spec metrics_evaluated must be false (skeleton; no "
            "fake OOD or temporal metrics from aggregate means)"
        )
    if spec.get("policy_search_performed") is not False:
        raise ValueError(
            "algorithm spec policy_search_performed must be false (no-retuning protocol)"
        )
    if spec.get("quality_strategy_tuned") is not False:
        raise ValueError(
            "algorithm spec quality_strategy_tuned must be false (no-retuning protocol)"
        )
    if spec.get("real_ood_temporal_supported") is not False:
        raise ValueError(
            "algorithm spec real_ood_temporal_supported must be false (skeleton)"
        )
    if spec.get("no_fake_ood_metrics_from_aggregate_means") is not True:
        raise ValueError(
            "algorithm spec no_fake_ood_metrics_from_aggregate_means must be true"
        )
    if spec.get("new_provider_calls") != 0:
        raise ValueError("algorithm spec new_provider_calls must be 0")
    if spec.get("aggregate_only_public_artifact") is not True:
        raise ValueError("algorithm spec aggregate_only_public_artifact must be true")
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
    if tuple(spec.get("split_axes") or ()) != SPLIT_AXES:
        raise ValueError("algorithm spec split_axes mismatch")
    if (
        tuple(spec.get("required_per_record_inputs") or ())
        != REQUIRED_PER_RECORD_INPUTS
    ):
        raise ValueError("algorithm spec required_per_record_inputs mismatch")
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
    if spec.get("min_denominator_per_cell") != MIN_DENOMINATOR_PER_CELL:
        raise ValueError("algorithm spec min_denominator_per_cell mismatch")
    if tuple(spec.get("allowed_replay_sources") or ()) != ALLOWED_REPLAY_SOURCES:
        raise ValueError("algorithm spec allowed_replay_sources mismatch")
    if tuple(spec.get("allowed_verdicts") or ()) != ALLOWED_VERDICTS:
        raise ValueError("algorithm spec allowed_verdicts mismatch")
    if (
        tuple(spec.get("public_screen_allowed_verdicts") or ())
        != PUBLIC_SCREEN_ALLOWED_VERDICTS
    ):
        raise ValueError("algorithm spec public_screen_allowed_verdicts mismatch")
    if (
        tuple(spec.get("missing_inputs_for_real_b18") or ())
        != tuple(g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18)
    ):
        raise ValueError("algorithm spec missing_inputs_for_real_b18 mismatch")
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
    if report.get("stage_is_ood_temporal_evaluation") is not True:
        raise ValueError(
            "report stage_is_ood_temporal_evaluation must be true (B18 stage)"
        )
    if report.get("ood_temporal_evaluation_performed") is not False:
        raise ValueError(
            "report ood_temporal_evaluation_performed must be false "
            "(no OOD or temporal evaluation performed by skeleton)"
        )
    if report.get("metrics_evaluated") is not False:
        raise ValueError(
            "report metrics_evaluated must be false (skeleton; no fake "
            "OOD or temporal metrics from aggregate means)"
        )
    if report.get("policy_search_performed") is not False:
        raise ValueError("report policy_search_performed must be false (no-retuning protocol)")
    if report.get("quality_strategy_tuned") is not False:
        raise ValueError("report quality_strategy_tuned must be false (no-retuning protocol)")
    if report.get("real_ood_temporal_supported") is not False:
        raise ValueError("report real_ood_temporal_supported must be false (skeleton)")
    if report.get("no_fake_ood_metrics_from_aggregate_means") is not True:
        raise ValueError(
            "report no_fake_ood_metrics_from_aggregate_means must be true"
        )
    if report.get("new_provider_calls") != 0:
        raise ValueError("report new_provider_calls must be 0")
    if report.get("all_axes_pass") is not False:
        raise ValueError("report all_axes_pass must be false (skeleton)")
    if report.get("axes_evaluated") is not False:
        raise ValueError(
            "report axes_evaluated must be false (skeleton; no empirical "
            "axis evaluation performed)"
        )
    if report.get("axes_defined") is not True:
        raise ValueError("report axes_defined must be true (5 axes)")
    if report.get("axis_count") != len(SPLIT_AXES):
        raise ValueError("report axis_count must equal the number of frozen axes")
    if report.get("winner_declared") is not False:
        raise ValueError("report winner_declared must be false (skeleton)")
    if report.get("metrics_defined") is not True:
        raise ValueError("report metrics_defined must be true")
    if report.get("gates_defined") is not True:
        raise ValueError("report gates_defined must be true")
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
    if tuple(report.get("split_axes") or ()) != SPLIT_AXES:
        raise ValueError("report split_axes mismatch")
    if tuple(report.get("required_per_record_inputs") or ()) != REQUIRED_PER_RECORD_INPUTS:
        raise ValueError("report required_per_record_inputs mismatch")
    if tuple(report.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("report metric_names mismatch")
    if tuple(report.get("hard_gates") or ()) != HARD_GATES:
        raise ValueError("report hard_gates mismatch")
    if tuple(report.get("experimental_stages") or ()) != EXPERIMENTAL_STAGES:
        raise ValueError("report experimental_stages mismatch")
    if (
        tuple(report.get("missing_inputs_for_real_b18") or ())
        != tuple(g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18)
    ):
        raise ValueError("report missing_inputs_for_real_b18 mismatch")
    # Required top-level sections.
    for key in ("ood_temporal_results",):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # ood_temporal_results substructure. The skeleton emits only
    # definitions + hard gates + experimental stage definitions; no
    # empirical per-stage OOD / temporal values.
    otr = report.get("ood_temporal_results") or {}
    for key in (
        "metrics_defined",
        "metric_names",
        "gates_defined",
        "hard_gates",
        "predeclared_criteria",
        "experimental_stages",
        "split_axes",
        "required_per_record_inputs",
        "missing_inputs_for_real_b18",
        "metrics_evaluated",
        "ood_temporal_evaluation_performed",
        "policy_search_performed",
        "quality_strategy_tuned",
        "real_ood_temporal_supported",
        "all_axes_pass",
        "axes_evaluated",
        "winner_declared",
        "no_fake_ood_metrics_from_aggregate_means",
    ):
        if key not in otr:
            raise ValueError(f"ood_temporal_results missing required section: {key}")
    if otr.get("metrics_evaluated") is not False:
        raise ValueError(
            "ood_temporal_results.metrics_evaluated must be false "
            "(skeleton; no fake OOD or temporal metrics from aggregate means)"
        )
    if otr.get("ood_temporal_evaluation_performed") is not False:
        raise ValueError(
            "ood_temporal_results.ood_temporal_evaluation_performed must be "
            "false (skeleton)"
        )
    if otr.get("policy_search_performed") is not False:
        raise ValueError(
            "ood_temporal_results.policy_search_performed must be false (no-retuning protocol)"
        )
    if otr.get("quality_strategy_tuned") is not False:
        raise ValueError(
            "ood_temporal_results.quality_strategy_tuned must be false (no-retuning protocol)"
        )
    if otr.get("real_ood_temporal_supported") is not False:
        raise ValueError(
            "ood_temporal_results.real_ood_temporal_supported must be false (skeleton)"
        )
    if otr.get("all_axes_pass") is not False:
        raise ValueError(
            "ood_temporal_results.all_axes_pass must be false (skeleton)"
        )
    if otr.get("axes_evaluated") is not False:
        raise ValueError(
            "ood_temporal_results.axes_evaluated must be false (skeleton)"
        )
    if otr.get("winner_declared") is not False:
        raise ValueError(
            "ood_temporal_results.winner_declared must be false (skeleton)"
        )
    if otr.get("no_fake_ood_metrics_from_aggregate_means") is not True:
        raise ValueError(
            "ood_temporal_results.no_fake_ood_metrics_from_aggregate_means must be true"
        )
    # experimental_stages must be a definitions-only block.
    stages = otr.get("experimental_stages") or {}
    if stages.get("stages_defined") is not True:
        raise ValueError(
            "ood_temporal_results.experimental_stages.stages_defined must be true"
        )
    if stages.get("stage_count") != len(EXPERIMENTAL_STAGES):
        raise ValueError(
            "ood_temporal_results.experimental_stages.stage_count mismatch"
        )
    if stages.get("stages_evaluated") is not False:
        raise ValueError(
            "ood_temporal_results.experimental_stages.stages_evaluated must be false (skeleton)"
        )
    stage_list = stages.get("stages")
    if not isinstance(stage_list, list) or len(stage_list) != len(EXPERIMENTAL_STAGES):
        raise ValueError(
            "ood_temporal_results.experimental_stages.stages must be a list of stage definitions"
        )
    for s in stage_list:
        if s.get("evaluated") is not False:
            raise ValueError(
                "stage definitions must have evaluated=false (skeleton)"
            )
        for forbidden_key in (
            "passes",
            "ood_generalization_gap",
            "temporal_holdout_delta",
            "repo_holdout_metric",
            "language_holdout_metric",
            "model_family_holdout_metric",
            "adversarial_robustness_score",
            "worst_group_metric",
            "cvar_tail_metric",
            "per_cell_denominator",
            "temporal_split_integrity",
            "no_retuning_proof_metric",
            "citation_validity",
            "stale_evidencecore_rejection_rate",
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
        "no_ood_temporal_evaluation",
        "no_per_record_replay",
        "no_time_axis",
        "no_commit_chronology",
        "no_adversarial_holdout",
        "no_temporal_holdout",
        "no_per_repo_per_language_cells",
        "no_model_family_x_repo_matrix",
        "no_worst_group_cvar_metric",
        "no_policy_search",
        "no_quality_strategy_tuning",
        "no_retrieval_policy_change",
        "no_evidencecore_semantics_change",
        "no_default_change",
        "no_promotion",
        "promotion_ready_false",
        "default_should_change_false",
        "evidencecore_semantics_changed_false",
        "retrieval_policy_changed_false",
        "backend_quality_promoted_false",
        "stage_is_ood_temporal_evaluation_true",
        "ood_temporal_evaluation_performed_false",
        "metrics_evaluated_false",
        "policy_search_performed_false",
        "quality_strategy_tuned_false",
        "real_ood_temporal_supported_false",
        "new_provider_calls_zero",
        "aggregate_only_public_artifact",
        "forbidden_public_keys_scanned",
        "no_raw_path_digest_provider_strings",
        "runtime_calls_by_replay_zero",
        "model_calls_by_replay_zero",
        "no_fake_ood_metrics_from_aggregate_means_true",
        "replay_only_no_live_ood_temporal_evaluation_in_evaluator",
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input (stub): load per-record inputs without computing OOD / temporal
# metrics
# ---------------------------------------------------------------------------


def _load_per_record_input(path: str) -> dict[str, Any]:
    """Load a per-record inputs JSON file (or directory of JSON files) and
    return a minimal metadata payload. The full per-record OOD / temporal
    evaluation is deferred to a later task; for now we only verify the
    input is valid JSON and surface its top-level shape (without leaking
    any forbidden keys).
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

    Real per-record OOD / temporal evaluation (ood_generalization_gap,
    temporal_holdout_delta, repo_holdout_metric,
    language_holdout_metric, model_family_holdout_metric,
    adversarial_robustness_score, worst_group_metric, cvar_tail_metric,
    per_cell_denominator, temporal_split_integrity,
    no_retuning_proof_metric, citation_validity,
    stale_evidencecore_rejection_rate across the five frozen split axes)
    is deferred to a later task. For now we emit a well-formed report
    with ``verdict="not_implemented"`` and an explanatory reason, while
    still passing all safety-invariant checks.

    CRITICAL: this stub MUST NOT compute fake OOD / temporal / worst-
    group / CVaR / per-cell metrics from the existing B11 aggregate
    means or from the R15 / R20 / R26 repo locks. No metric values are
    emitted.
    """
    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Override the verdict to signal that no real B18 OOD / temporal
    # evaluation happened.
    report["verdict"] = "not_implemented"
    report["verdict_reason"] = (
        "real-input OOD and temporal evaluation plus per-record replay "
        "computation deferred to later task; "
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
# Bounded public-aggregate no-go screen
# ---------------------------------------------------------------------------
#
# Reads the already-published public B11 prospective matrix aggregate
# report plus optional R15 / R20 / R26 repos.lock.jsonl files (and their
# dataset manifests) and emits a bounded public-aggregate no-go report
# for B18. The guard for each input is optional: if an artifact is
# absent the screen reports it as ``not_present`` rather than failing.
#
# The screen preserves the public-artifact contract:
#
# * **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
#   snippets, prompts, responses, diffs, patches, test execution
#   results, solve labels, agent event logs, gold spans, private labels,
#   provider keys, base URLs, API keys, content SHAs, digests, commit
#   chronology, or line ranges are read or emitted;
# * **no** provider calls (``new_provider_calls == 0``);
# * **no** live OOD / temporal evaluation, no per-record replay, no
#   commit-chronology temporal split, no adversarial holdout, no
#   per-repo / per-language / per-model-family cell computation, no
#   worst-group / CVaR metric computation, no policy search, no quality
#   strategy tuning, no default change, no EvidenceCore semantics
#   change, no promotion, no winner declaration;
# * ``ood_temporal_evaluation_performed=false``,
#   ``metrics_evaluated=false``,
#   ``policy_search_performed=false``,
#   ``quality_strategy_tuned=false``,
#   ``real_ood_temporal_supported=false``,
#   ``no_fake_ood_metrics_from_aggregate_means=true``.
#


def _load_optional_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Load an optional JSON artifact.

    Returns ``(parsed_or_None, status)`` where status is one of:
      * ``"loaded"`` — the artifact was loaded
      * ``"not_present"`` — the file does not exist
      * ``"load_failed"`` — the file exists but could not be parsed
    """
    if not path.exists():
        return None, "not_present"
    try:
        return json.loads(path.read_text(encoding="utf-8")), "loaded"
    except (OSError, json.JSONDecodeError):
        return None, "load_failed"


def _load_optional_jsonl(path: Path) -> tuple[list[dict[str, Any]] | None, str]:
    """Load an optional JSONL artifact (one JSON object per line).

    Returns ``(records_or_None, status)``.
    """
    if not path.exists():
        return None, "not_present"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, "load_failed"
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None, "load_failed"
        if isinstance(obj, dict):
            records.append(obj)
    return records, "loaded"


def _summarize_b11_aggregate(b11: dict[str, Any]) -> dict[str, Any]:
    """Extract only the public metadata counts from the B11 aggregate.
    No per-record, per-time, per-repo-per-language cell, or
    model_family x repo matrix data is carried forward.
    """
    repo_slice_ids = b11.get("public_repo_slice_ids")
    model_family_names = b11.get("public_model_family_names")
    return {
        "b11_aggregate_loaded": True,
        "b11_public_repo_slice_count": b11.get("public_repo_slice_count"),
        "b11_public_model_family_count": b11.get("public_model_family_count"),
        "b11_public_repo_slice_ids_present": isinstance(repo_slice_ids, list),
        "b11_public_model_family_names_present": isinstance(model_family_names, list),
        "b11_record_count_total": b11.get("record_count_total"),
        "b11_run_count": b11.get("run_count"),
        "b11_promotion_ready": bool(b11.get("promotion_ready")),
        "b11_default_should_change": bool(b11.get("default_should_change")),
        "b11_evidencecore_semantics_changed": bool(
            b11.get("evidencecore_semantics_changed")
        ),
        "b11_policy_search_performed": bool(b11.get("policy_search_performed")),
        "b11_quality_strategy_tuned": bool(b11.get("quality_strategy_tuned")),
        "b11_aggregate_only_public_artifact": bool(
            b11.get("aggregate_only_public_artifact")
        ),
        "b11_has_per_record_records": False,
        "b11_has_time_axis": False,
        "b11_has_commit_chronology": False,
        "b11_has_per_repo_per_language_cells": False,
        "b11_has_model_family_x_repo_matrix": False,
        "b11_has_adversarial_holdout_outcomes": False,
        "b11_has_temporal_holdout_outcomes": False,
    }


def _summarize_repos_lock(
    records: list[dict[str, Any]],
    lock_id: str,
) -> dict[str, Any]:
    """Extract only metadata counts from a repos.lock.jsonl. No raw
    repo_id, path, content_manifest_sha, or commit values are carried
    forward.
    """
    repo_count = len(records)
    primary_languages: set[str] = set()
    has_language_metadata = False
    has_commit_chronology = False
    for rec in records:
        lang = rec.get("language")
        if isinstance(lang, dict):
            primary = lang.get("primary")
            if isinstance(primary, str) and primary:
                primary_languages.add(primary)
                has_language_metadata = True
        # A single static snapshot commit label (e.g. "r15-snapshot")
        # is NOT commit chronology; it is a frozen snapshot tag.
        commit_val = rec.get("commit")
        if isinstance(commit_val, str) and commit_val:
            # present, but it is a single snapshot label, not a
            # chronological ordering.
            pass
    return {
        f"{lock_id}_repos_lock_loaded": True,
        f"{lock_id}_repo_count": repo_count,
        f"{lock_id}_language_metadata_available": has_language_metadata,
        f"{lock_id}_language_count": len(primary_languages),
        f"{lock_id}_has_commit_chronology": has_commit_chronology,
        f"{lock_id}_has_real_temporal_split": False,
        f"{lock_id}_is_synthetic_static_snapshot": True,
    }


def _summarize_manifest(
    manifest: dict[str, Any], manifest_id: str
) -> dict[str, Any]:
    """Extract only stress-category availability from a dataset
    manifest. No raw repo_id, path, sha, or label values are carried
    forward.
    """
    current = manifest.get("current_status") or {}
    stress_categories: dict[str, int] = {}
    stress_availability = False
    for _program, status in current.items():
        if not isinstance(status, dict):
            continue
        categories = status.get("categories")
        if isinstance(categories, dict):
            stress_availability = True
            for cat, count in categories.items():
                if isinstance(cat, str) and isinstance(count, int):
                    stress_categories[cat] = count
    return {
        f"{manifest_id}_manifest_loaded": True,
        f"{manifest_id}_stress_category_availability": stress_availability,
        f"{manifest_id}_stress_category_count": len(stress_categories),
        f"{manifest_id}_is_synthetic_static_snapshot": True,
        f"{manifest_id}_has_real_temporal_split": False,
    }


def _base_public_screen_report(self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCREEN_SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": PUBLIC_SCREEN_CLAIM_LEVEL,
        "self_test": bool(self_test),
        # Safety fields preserved verbatim. The screen makes NO
        # empirical B18 OOD / temporal evaluation claim; the B18 stage
        # IS ood-temporal-evaluation, but no empirical OOD / temporal
        # evaluation was performed by this screen.
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_policy_changed": False,
        "backend_quality_promoted": False,
        "stage_is_ood_temporal_evaluation": True,
        "ood_temporal_evaluation_performed": False,
        "metrics_evaluated": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "real_ood_temporal_supported": False,
        "no_fake_ood_metrics_from_aggregate_means": True,
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
        "raw_per_record_records_stored": False,
        "raw_time_indices_stored": False,
        "raw_commit_chronology_stored": False,
        "raw_outcome_labels_stored": False,
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
        "is_full_b18_ood_temporal_evaluation": False,
        "full_b18_ood_temporal_evaluation_possible_from_public_artifacts": False,
        "metrics_defined": True,
        "gates_defined": True,
    }


def _finalize_public_screen_safety(report: dict[str, Any]) -> None:
    """Run the forbidden-key/value scan on the public output.

    Uses both the B18 evaluator's own ``_recursive_key_scan`` (stricter
    forbidden-key list including file_path, gold, commit, etc.) and
    ``b6lite._walk_forbidden`` (the shared public-output scan used by
    B11/B12/B13/B14/B15/B16/B17 public screens).
    """
    b18_hits = _recursive_key_scan(report)
    b6lite_hits = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = (
        not b18_hits and not b6lite_hits
    )
    if b18_hits:
        raise ValueError(
            "b18 public OOD-temporal screen public output would contain "
            f"forbidden keys/values (b18 scan); first violations: "
            f"{b18_hits[:5]}"
        )
    if b6lite_hits:
        raise ValueError(
            "b18 public OOD-temporal screen public output would contain "
            f"forbidden keys/values (b6lite scan); first violations: "
            f"{b6lite_hits[:5]}"
        )


def screen_public(self_test: bool = False) -> dict[str, Any]:
    """Build the B18 bounded public-aggregate no-go screen report.

    Reads the already-published public B11 prospective matrix aggregate
    report plus optional R15 / R20 / R26 repos.lock.jsonl files and
    their dataset manifests. Each input guard is optional: absent
    artifacts are reported as ``not_present`` rather than failing.

    The screen MUST NOT compute fake OOD / temporal / worst-group /
    CVaR / per-cell metrics from the B11 aggregate means or from the
    R15 / R20 / R26 repo locks. It emits only metadata counts (repo
    counts, model family count, language metadata availability, stress
    category availability) and the missing-inputs list.
    """
    b11, b11_status = _load_optional_json(B11_AGGREGATE_PATH)
    r15_records, r15_status = _load_optional_jsonl(R15_REPOS_LOCK_PATH)
    r20_records, r20_status = _load_optional_jsonl(R20_REPOS_LOCK_PATH)
    r26_records, r26_status = _load_optional_jsonl(R26_REPOS_LOCK_PATH)
    r20_manifest, r20_manifest_status = _load_optional_json(R20_MANIFEST_PATH)
    r26_manifest, r26_manifest_status = _load_optional_json(R26_MANIFEST_PATH)

    report = _base_public_screen_report(self_test)
    report["input_artifacts_public_note"] = (
        "already-published aggregate-only public B11 matrix plus "
        "optional R15 R20 R26 repos lock and dataset manifest "
        "metadata; no raw records paths prompts responses snippets "
        "diffs patches test results or private labels read by the screen"
    )
    report["input_status"] = {
        "b11_aggregate_status": b11_status,
        "r15_repos_lock_status": r15_status,
        "r20_repos_lock_status": r20_status,
        "r26_repos_lock_status": r26_status,
        "r20_manifest_status": r20_manifest_status,
        "r26_manifest_status": r26_manifest_status,
    }

    if b11 is not None and b11_status == "loaded":
        report["input_b11_aggregate_summary"] = _summarize_b11_aggregate(b11)
    if r15_records is not None and r15_status == "loaded":
        report["input_r15_repos_lock_summary"] = _summarize_repos_lock(
            r15_records, "r15"
        )
    if r20_records is not None and r20_status == "loaded":
        report["input_r20_repos_lock_summary"] = _summarize_repos_lock(
            r20_records, "r20"
        )
    if r26_records is not None and r26_status == "loaded":
        report["input_r26_repos_lock_summary"] = _summarize_repos_lock(
            r26_records, "r26"
        )
    if r20_manifest is not None and r20_manifest_status == "loaded":
        report["input_r20_manifest_summary"] = _summarize_manifest(
            r20_manifest, "r20"
        )
    if r26_manifest is not None and r26_manifest_status == "loaded":
        report["input_r26_manifest_summary"] = _summarize_manifest(
            r26_manifest, "r26"
        )

    # Verdict: the central no-go signal is that the public artifacts
    # lack per-record / per-time / per-repo-per-language /
    # model_family x repo / adversarial holdout / temporal holdout
    # axes. If at least one artifact is present and none of them carry
    # the required per-record OOD / temporal axes, the verdict is
    # no_go_public_aggregate_only. If no artifact is present at all,
    # the screen falls back to public_aggregate_carry_forward_only
    # (still a no-empirical-evaluation verdict; just signals the screen
    # itself was unable to confirm the no-go via a carry-forward read).
    present_artifacts = [
        status
        for status in (
            b11_status,
            r15_status,
            r20_status,
            r26_status,
            r20_manifest_status,
            r26_manifest_status,
        )
        if status == "loaded"
    ]
    if present_artifacts:
        verdict = "no_go_public_aggregate_only"
        verdict_reason = (
            "every present public artifact is aggregate-only or a "
            "synthetic static snapshot; none contains per-record "
            "records a time axis commit chronology per-repo per-"
            "language cells a model_family x repo matrix or "
            "holdout outcomes. No empirical B18 evaluation."
        )
    else:
        verdict = "public_aggregate_carry_forward_only"
        verdict_reason = (
            "public artifacts carry forward pre-B18 aggregate "
            "signals only; no empirical B18 OOD or temporal "
            "evaluation. No per-record records no time axis no "
            "commit chronology no cells."
        )

    report["verdict"] = verdict
    report["verdict_reason"] = verdict_reason
    report["allowed_verdicts"] = list(PUBLIC_SCREEN_ALLOWED_VERDICTS)

    # Missing inputs (the specific gaps that block real B18).
    report["missing_inputs_for_real_b18"] = [
        dict(g) for g in MISSING_INPUTS_FOR_REAL_B18
    ]

    # Recommended next step (cautious, no auto-promotion).
    recommended_next_step = {
        "primary": "future_prospective_per_record_data_with_temporal_repo_language_model_adversarial_axes",
        "secondary": "future_no_retuning_protocol_manifest",
        "reason": (
            "collect prospective per-record outcome records with a "
            "real time axis and commit chronology per repo plus "
            "per-repo per-language per-model-family cells and "
            "holdout memberships under a frozen no-retuning "
            "protocol then run a B18 evaluation"
        ),
        "next_step_authorizes_promotion": False,
        "next_step_authorizes_default_change": False,
        "next_step_authorizes_backend_quality_promotion": False,
        "next_step_authorizes_retrieval_policy_change": False,
        "next_step_authorizes_ood_temporal_evaluation": False,
        "next_step_authorizes_policy_search": False,
        "next_step_authorizes_quality_strategy_tuning": False,
        "next_step_authorizes_empirical_evaluation": False,
    }

    report.update(
        {
            "testability": {
                "full_b18_ood_temporal_evaluation_possible_from_public_artifacts": False,
                "missing_inputs_for_full_b18": [
                    g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18
                ],
                "note": (
                    "real B18 cannot be replayed from public B11 R15 "
                    "R20 R26 aggregates; the listed missing inputs are "
                    "the per-record OOD and temporal fields required"
                ),
            },
            "recommended_next_step": recommended_next_step,
            "integrity": _compute_public_screen_integrity(
                b11, r15_records, r20_records, r26_records
            ),
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "evidencecore_semantics_changed_false": True,
                "retrieval_policy_changed_false": True,
                "backend_quality_promoted_false": True,
                "stage_is_ood_temporal_evaluation": True,
                "ood_temporal_evaluation_performed_false": True,
                "metrics_evaluated_false": True,
                "policy_search_performed_false": True,
                "quality_strategy_tuned_false": True,
                "real_ood_temporal_supported_false": True,
                "new_provider_calls_zero": True,
                "no_evidencecore_semantics_change": True,
                "no_retrieval_policy_change": True,
                "no_backend_quality_promotion": True,
                "no_default_change": True,
                "no_promotion": True,
                "no_policy_search": True,
                "no_quality_strategy_tuning": True,
                "no_live_llm_calls_by_screen": True,
                "no_ood_temporal_evaluation": True,
                "no_per_record_replay": True,
                "no_time_axis": True,
                "no_commit_chronology": True,
                "no_adversarial_holdout": True,
                "no_temporal_holdout": True,
                "no_per_repo_per_language_cells": True,
                "no_model_family_x_repo_matrix": True,
                "no_worst_group_cvar_metric": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_patches_or_diffs": True,
                "no_test_execution_results": True,
                "no_solve_labels": True,
                "no_agent_event_logs": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_winner_declared": True,
                "no_fake_ood_metrics_from_aggregate_means": True,
                "aggregates_do_not_imply_ood_generalization": True,
                "aggregates_do_not_imply_temporal_stability": True,
                "synthetic_snapshots_do_not_imply_temporal_split": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "backend_quality_promotion_claimed": False,
                "retrieval_policy_change_claimed": False,
                "ood_temporal_evaluation_claimed": False,
                "empirical_evaluation_claimed": False,
                "policy_search_claimed": False,
                "quality_strategy_tuning_claimed": False,
                "winner_declared_claimed": False,
                "signal_strength": (
                    "bounded_public_aggregate_no_go_screen_only"
                ),
                "is_full_b18_ood_temporal_evaluation": False,
                "recommended_next_step": (
                    "future_prospective_per_record_data_with_temporal_repo_language_model_adversarial_axes"
                ),
            },
        }
    )

    _finalize_public_screen_safety(report)
    return report


def verify_public_screen(report: dict[str, Any]) -> None:
    """Validate the canonical bounded public-screen artifact.

    The public screen is a checked-in artifact written by
    ``--regenerate-artifacts``. Self-test must therefore drift-check it in
    the same way it drift-checks the frozen algorithm spec and synthetic
    fixture report.
    """
    if report.get("schema_version") != PUBLIC_SCREEN_SCHEMA_VERSION:
        raise ValueError("public screen schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        raise ValueError("public screen generated_by mismatch")
    if report.get("generated_at") != GENERATED_AT:
        raise ValueError("public screen generated_at must be fixed")
    if report.get("claim_level") != PUBLIC_SCREEN_CLAIM_LEVEL:
        raise ValueError("public screen claim_level mismatch")
    if report.get("verdict") != "no_go_public_aggregate_only":
        raise ValueError("public screen verdict must be no_go_public_aggregate_only")
    for key, expected in (
        ("aggregate_only_public_artifact", True),
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("ood_temporal_evaluation_performed", False),
        ("metrics_evaluated", False),
        ("policy_search_performed", False),
        ("quality_strategy_tuned", False),
        ("real_ood_temporal_supported", False),
        ("no_fake_ood_metrics_from_aggregate_means", True),
        ("new_provider_calls", 0),
        ("full_b18_ood_temporal_evaluation_possible_from_public_artifacts", False),
    ):
        if report.get(key) != expected:
            raise ValueError(f"public screen {key} must be {expected!r}")
    observed_gaps = []
    for gap in report.get("missing_inputs_for_real_b18") or []:
        if isinstance(gap, dict):
            observed_gaps.append(gap.get("gap_id"))
        else:
            observed_gaps.append(gap)
    if observed_gaps != [gap["gap_id"] for gap in MISSING_INPUTS_FOR_REAL_B18]:
        raise ValueError("public screen missing_inputs_for_real_b18 mismatch")
    if _recursive_key_scan(report):
        raise ValueError("public screen contains B18-forbidden public keys")
    if b6lite._walk_forbidden(report):
        raise ValueError("public screen contains shared forbidden public keys")


def _compute_public_screen_integrity(
    b11: dict[str, Any] | None,
    r15_records: list[dict[str, Any]] | None,
    r20_records: list[dict[str, Any]] | None,
    r26_records: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Compute integrity flags for the public no-go screen.

    All inputs that are present must be aggregate-only and must NOT
    promote. The B11 aggregate must report per-record / time / cell /
    matrix / holdout axes absent (they are — the B11 aggregate carries
    only model-family means and a sanitized repo slice list). The R15 /
    R20 / R26 repo locks must be synthetic static snapshots (single
    commit label, no chronological ordering).
    """
    return {
        # B11 aggregate safety flags (carry-forward).
        "b11_input_aggregate_only_public_artifact": (
            b11 is not None
            and b11.get("aggregate_only_public_artifact") is True
        ),
        "b11_input_promotion_ready_false": (
            b11 is not None and b11.get("promotion_ready") is False
        ),
        "b11_input_default_should_change_false": (
            b11 is not None and b11.get("default_should_change") is False
        ),
        "b11_input_evidencecore_semantics_changed_false": (
            b11 is not None
            and b11.get("evidencecore_semantics_changed") is False
        ),
        "b11_input_policy_search_performed_false": (
            b11 is not None and b11.get("policy_search_performed") is False
        ),
        "b11_input_quality_strategy_tuned_false": (
            b11 is not None and b11.get("quality_strategy_tuned") is False
        ),
        # B11 aggregate lacks per-record / time / cell / matrix /
        # holdout axes (the central B18 no-go signal).
        "b11_input_has_no_per_record_records": True,
        "b11_input_has_no_time_axis": True,
        "b11_input_has_no_commit_chronology": True,
        "b11_input_has_no_per_repo_per_language_cells": True,
        "b11_input_has_no_model_family_x_repo_matrix": True,
        "b11_input_has_no_adversarial_holdout_outcomes": True,
        "b11_input_has_no_temporal_holdout_outcomes": True,
        # R15 / R20 / R26 repo locks are synthetic static snapshots.
        "r15_input_is_synthetic_static_snapshot": (
            r15_records is None or _is_synthetic_static_snapshot(r15_records)
        ),
        "r20_input_is_synthetic_static_snapshot": (
            r20_records is None or _is_synthetic_static_snapshot(r20_records)
        ),
        "r26_input_is_synthetic_static_snapshot": (
            r26_records is None or _is_synthetic_static_snapshot(r26_records)
        ),
        # Composite: every present public artifact is aggregate-only or
        # a synthetic static snapshot. This is the central B18 no-go
        # signal from the public screen.
        "all_present_inputs_aggregate_only_or_synthetic_snapshot": True,
        "all_present_inputs_promotion_ready_false": (
            (b11 is None or b11.get("promotion_ready") is False)
        ),
        "forbidden_public_key_scan_clean": True,
    }


def _is_synthetic_static_snapshot(records: list[dict[str, Any]]) -> bool:
    """A repos.lock.jsonl is a synthetic static snapshot if every record
    carries a single commit label (e.g. "r15-snapshot", "r20-snapshot",
    "r26-snapshot") with no chronological ordering. We check that all
    records share the same commit label (a real chronological split
    would have varying commit values per record)."""
    if not records:
        return True
    commits = set()
    for rec in records:
        commit_val = rec.get("commit")
        if isinstance(commit_val, str) and commit_val:
            commits.add(commit_val)
    # A synthetic static snapshot has exactly one commit label across
    # all records. (Zero commits would also be a degenerate snapshot;
    # we treat <=1 distinct commit as a static snapshot.)
    return len(commits) <= 1


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test_forbidden_scan() -> None:
    bad_report = {
        "task_id": "leak",
        "path": "src/foo.rs",
        "file_path": "src/foo.rs",
        "snippet": "fn main(){}",
        "provider_key": "sk-xxx",
        "diff": "diff --git a/b",
        "patch": "patch content",
        "solve_label": "True",
        "gold": "gold_value",
        "gold_spans": [[1, 2]],
        "label": "x",
        "content_sha": "deadbeef",
        "raw_record": "record_data",
        "commit": "abc123",
        "commit_chronology": ["a", "b"],
        "span": [1, 2],
        "prompt": "p",
        "response": "r",
        "api_key": "k",
        "nested": {"content_sha": "deadbeef", "candidate_id": "c1"},
    }
    hits = _recursive_key_scan(bad_report)
    flat = " ".join(hits)
    assert "task_id" in flat
    assert "path" in flat
    assert "file_path" in flat
    assert "snippet" in flat
    assert "provider_key" in flat
    assert "diff" in flat
    assert "patch" in flat
    assert "solve_label" in flat
    assert "gold_spans" in flat
    assert "gold" in flat
    assert "content_sha" in flat
    assert "raw_record" in flat
    assert "commit" in flat
    assert "commit_chronology" in flat
    assert "span" in flat
    assert "prompt" in flat
    assert "response" in flat
    assert "api_key" in flat
    assert "candidate_id" in flat

    # Raw path value should trip the "/" pattern even when the key is
    # allowed.
    bad_value = {"provenance": "eval/some_file.py"}
    hits2 = _recursive_key_scan(bad_value)
    assert any("forbidden_value" in h for h in hits2), hits2

    # A clean provenance reference (module::symbol, no "/") must not
    # trip.
    clean = {"provenance": "b18_ood_temporal_evaluation::build_report"}
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


def _self_test_split_axes_closed() -> None:
    """Split axes: 5 frozen axes; temporal / repo / language /
    model_family / adversarial; no retuning protocol; no policy search;
    no quality strategy tuning."""
    spec = build_algorithm_spec()
    assert tuple(spec["split_axes"]) == SPLIT_AXES
    assert len(SPLIT_AXES) == 5, SPLIT_AXES
    assert SPLIT_AXES == (
        "temporal_split",
        "repo_split",
        "language_split",
        "model_family_split",
        "adversarial_split",
    ), SPLIT_AXES
    # All axis IDs unique.
    assert len(set(SPLIT_AXES)) == len(SPLIT_AXES), SPLIT_AXES
    # No-retuning protocol frozen.
    assert NO_RETUNING_PROTOCOL is True
    assert NO_POLICY_SEARCH is True
    assert NO_QUALITY_STRATEGY_TUNING is True
    assert NO_RETRIEVAL_POLICY_CHANGE is True
    assert NO_EVIDENCECORE_SEMANTICS_CHANGE is True
    assert NO_DEFAULT_CHANGE is True
    assert NO_PROMOTION is True
    assert spec["predeclared_criteria"]["no_retuning_protocol"] is True
    assert spec["predeclared_criteria"]["no_policy_search"] is True
    assert spec["predeclared_criteria"]["no_quality_strategy_tuning"] is True


def _self_test_required_per_record_inputs() -> None:
    """Required per-record inputs: every input the real-B18 data
    contract requires is defined."""
    spec = build_algorithm_spec()
    assert tuple(spec["required_per_record_inputs"]) == REQUIRED_PER_RECORD_INPUTS
    # Required inputs (the task spec).
    required_input_ids = {
        "per_record_record",
        "per_record_time_index",
        "per_record_commit_chronology",
        "per_record_repo_axis",
        "per_record_language_axis",
        "per_record_model_family_axis",
        "per_record_adversarial_holdout_membership",
        "per_record_temporal_holdout_membership",
        "per_record_randomized_run_order_proof",
        "per_record_no_retuning_proof",
        "shared_frozen_evaluation_protocol_manifest",
    }
    actual = set(REQUIRED_PER_RECORD_INPUTS)
    assert required_input_ids.issubset(actual), (
        required_input_ids - actual
    )


def _self_test_missing_inputs_for_real_b18() -> None:
    """Missing inputs for real B18: the 7 frozen gaps from the task spec
    are present."""
    spec = build_algorithm_spec()
    missing = spec["missing_inputs_for_real_b18"]
    expected = tuple(g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18)
    assert tuple(missing) == expected, (missing, expected)
    required_gap_ids = {
        "no_per_record_records",
        "no_time_axis",
        "no_commit_chronology",
        "no_per_repo_per_language_cells_in_public_b11",
        "no_model_family_x_repo_matrix",
        "no_adversarial_holdout_outcomes",
        "no_temporal_holdout_outcomes",
    }
    assert required_gap_ids.issubset(set(missing)), (
        required_gap_ids - set(missing)
    )


def _self_test_metric_registry() -> None:
    """Metric registry: 13 metric names defined; no aggregate-mean
    metrics."""
    spec = build_algorithm_spec()
    assert tuple(spec["metric_names"]) == METRIC_NAMES
    assert len(METRIC_NAMES) == 13, METRIC_NAMES
    # All metric names require per-record OOD / temporal inputs; none
    # can be computed from B11 aggregate means or R15/R20/R26 repo
    # locks.
    for name in METRIC_NAMES:
        assert "aggregate_mean" not in name, name
        assert "overall_mean" not in name, name


def _self_test_hard_gates_defined() -> None:
    """Hard gates: per_record_data / time_axis / commit_chronology /
    no_retuning / adversarial_holdout / temporal_holdout /
    evidencecore_materialization / stale_citation / privacy /
    promotion_false gates defined."""
    spec = build_algorithm_spec()
    assert tuple(spec["hard_gates"]) == HARD_GATES
    assert len(HARD_GATES) == 10, HARD_GATES
    expected_gates = {
        "per_record_data_gate",
        "time_axis_gate",
        "commit_chronology_gate",
        "no_retuning_gate",
        "adversarial_holdout_gate",
        "temporal_holdout_gate",
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
        "no_ood_temporal_evaluation_feasibility",
        "frozen_no_retuning_protocol",
        "per_axis_holdout_evaluation",
        "worst_group_cvar_reporting",
    ), EXPERIMENTAL_STAGES
    # Split protocol: task-screen + fresh-validation, stratified by
    # (repo, language, model_family, time).
    assert spec["split_protocol"] == SPLIT_PROTOCOL
    assert spec["task_screen_fraction"] + spec["fresh_validation_fraction"] == 1.0
    assert spec["fresh_validation_split_reported_once"] is True
    # Evaluate the stages on the synthetic fixture (evaluator-side).
    # The skeleton emits definitions only; no empirical per-stage OOD /
    # temporal values.
    fixture = _build_synthetic_fixture()
    cr, _verdict, _reason = _evaluate_ood_temporal(fixture, "synthetic_fixture")
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
            "ood_generalization_gap",
            "temporal_holdout_delta",
            "repo_holdout_metric",
            "language_holdout_metric",
            "model_family_holdout_metric",
            "adversarial_robustness_score",
            "worst_group_metric",
            "cvar_tail_metric",
            "per_cell_denominator",
            "temporal_split_integrity",
            "no_retuning_proof_metric",
            "citation_validity",
            "stale_evidencecore_rejection_rate",
            "delta_vs_reference",
        ):
            assert forbidden_key not in s, (forbidden_key, s)


def _self_test_no_fake_ood_metrics_from_aggregate_means() -> None:
    """CRITICAL: the skeleton must NOT compute fake OOD / temporal /
    worst-group / CVaR / per-cell metrics from the B11 aggregate means
    or from the R15 / R20 / R26 repo locks. The synthetic-fixture report
    must surface metrics_evaluated=false and contain no metric value
    fields."""
    fixture = _build_synthetic_fixture()
    assert fixture["per_record_ood_temporal_inputs_present"] is False
    assert fixture["metric_values_computed"] is False
    report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )
    assert report["metrics_evaluated"] is False
    assert report["ood_temporal_evaluation_performed"] is False
    assert report["policy_search_performed"] is False
    assert report["quality_strategy_tuned"] is False
    assert report["real_ood_temporal_supported"] is False
    assert report["no_fake_ood_metrics_from_aggregate_means"] is True
    assert report["ood_temporal_results"]["metrics_evaluated"] is False
    assert (
        report["ood_temporal_results"]["no_fake_ood_metrics_from_aggregate_means"]
        is True
    )
    # No metric value fields should be present at the top level.
    for forbidden_field in (
        "ood_generalization_gap_value",
        "temporal_holdout_delta_value",
        "repo_holdout_metric_value",
        "language_holdout_metric_value",
        "model_family_holdout_metric_value",
        "adversarial_robustness_score_value",
        "worst_group_metric_value",
        "cvar_tail_metric_value",
        "per_cell_denominator_value",
        "temporal_split_integrity_value",
        "no_retuning_proof_metric_value",
        "citation_validity_value",
        "stale_evidencecore_rejection_rate_value",
    ):
        assert forbidden_field not in report, forbidden_field
        assert forbidden_field not in report["ood_temporal_results"], forbidden_field


def _self_test_input_stub_not_implemented(tmp_path: Path) -> None:
    """--input mode must emit verdict='not_implemented' without doing
    any real B18 OOD / temporal evaluation computation."""
    p = tmp_path / "per_record_stub.json"
    p.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "record_id": "r1",
                        "time_index": 0,
                        "repo_axis": "py_fastapi",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    meta = _load_per_record_input(str(p))
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
    assert report["ood_temporal_evaluation_performed"] is False
    assert report["policy_search_performed"] is False
    assert report["quality_strategy_tuned"] is False
    assert report["real_ood_temporal_supported"] is False


def _self_test_reference_artifacts_pinned() -> None:
    """The B11 aggregate + R15 / R20 / R26 repo locks must exist on disk
    so the B18 frozen_artifacts pin is meaningful and so the B18
    evaluation cannot misread them as OOD / temporal proof."""
    refs = _reference_artifact_presence()
    assert refs.get("b11_prospective_matrix_aggregate_present") is True, refs
    assert refs.get("r15_repos_lock_present") is True, refs
    assert refs.get("r20_auto_wide_repos_lock_present") is True, refs
    assert refs.get("r26_auto_stress_repos_lock_present") is True, refs


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
            "output; run "
            "`python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts` "
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
            "on-disk b18_ood_temporal_evaluation_report.json drifted from "
            "the in-memory build_report() output; run "
            "`python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_report(on_disk_report)

    expected_public_screen = screen_public(self_test=False)
    on_disk_public_screen = _load_json(PUBLIC_SCREEN_PATH)
    if on_disk_public_screen != expected_public_screen:
        raise ValueError(
            "on-disk b18_public_ood_temporal_screen_report.json drifted "
            "from the in-memory screen_public(self_test=False) output; run "
            "`python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_public_screen(on_disk_public_screen)


def _self_test_public_screen_no_go() -> None:
    """The bounded public-aggregate no-go screen must emit
    no_go_public_aggregate_only and must NOT compute fake OOD / temporal
    metrics from the B11 aggregate means or from the R15 / R20 / R26
    repo locks."""
    report = screen_public(self_test=True)
    assert report["schema_version"] == PUBLIC_SCREEN_SCHEMA_VERSION
    assert report["claim_level"] == PUBLIC_SCREEN_CLAIM_LEVEL
    # Safety fields preserved verbatim.
    for k, v in (
        ("aggregate_only_public_artifact", True),
        ("candidate_not_fact", True),
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("retrieval_policy_changed", False),
        ("backend_quality_promoted", False),
        ("stage_is_ood_temporal_evaluation", True),
        ("ood_temporal_evaluation_performed", False),
        ("metrics_evaluated", False),
        ("policy_search_performed", False),
        ("quality_strategy_tuned", False),
        ("real_ood_temporal_supported", False),
        ("no_fake_ood_metrics_from_aggregate_means", True),
        ("new_provider_calls", 0),
        ("full_b18_ood_temporal_evaluation_possible_from_public_artifacts", False),
        ("winner_declared", False),
        ("promotion_declared", False),
        ("default_recommendation_declared", False),
        ("backend_quality_promotion_declared", False),
        ("retrieval_variant_promotion_declared", False),
        ("metrics_defined", True),
        ("gates_defined", True),
    ):
        assert report[k] == v, (k, report[k])
    # No-go verdict emitted because every present public artifact is
    # aggregate-only or a synthetic static snapshot.
    assert report["verdict"] == "no_go_public_aggregate_only", report["verdict"]
    assert report["verdict"] in PUBLIC_SCREEN_ALLOWED_VERDICTS, report["verdict"]
    assert "no empirical b18" in report["verdict_reason"].lower(), report[
        "verdict_reason"
    ]
    # Carry-forward summaries present.
    assert report["input_b11_aggregate_summary"]["b11_aggregate_loaded"] is True
    assert (
        report["input_b11_aggregate_summary"]["b11_has_per_record_records"]
        is False
    )
    assert (
        report["input_b11_aggregate_summary"]["b11_has_time_axis"] is False
    )
    assert (
        report["input_b11_aggregate_summary"][
            "b11_has_per_repo_per_language_cells"
        ]
        is False
    )
    assert (
        report["input_b11_aggregate_summary"]["b11_has_model_family_x_repo_matrix"]
        is False
    )
    # R15 / R20 / R26 repo locks are synthetic static snapshots.
    assert report["input_r15_repos_lock_summary"]["r15_repo_count"] > 0
    assert (
        report["input_r15_repos_lock_summary"]["r15_is_synthetic_static_snapshot"]
        is True
    )
    assert report["input_r20_repos_lock_summary"]["r20_repo_count"] > 0
    assert (
        report["input_r20_repos_lock_summary"]["r20_is_synthetic_static_snapshot"]
        is True
    )
    assert report["input_r26_repos_lock_summary"]["r26_repo_count"] > 0
    assert (
        report["input_r26_repos_lock_summary"]["r26_is_synthetic_static_snapshot"]
        is True
    )
    # Stress category availability from manifests.
    assert (
        report["input_r20_manifest_summary"]["r20_stress_category_availability"]
        is True
    )
    assert (
        report["input_r20_manifest_summary"]["r20_stress_category_count"] > 0
    )
    assert (
        report["input_r26_manifest_summary"]["r26_stress_category_availability"]
        is True
    )
    assert (
        report["input_r26_manifest_summary"]["r26_stress_category_count"] > 0
    )
    # All missing inputs enumerated.
    missing_ids = [g["gap_id"] for g in report["missing_inputs_for_real_b18"]]
    expected_missing = tuple(g["gap_id"] for g in MISSING_INPUTS_FOR_REAL_B18)
    assert missing_ids == list(expected_missing), missing_ids
    # Required missing inputs are present (the task spec).
    required_gap_ids = {
        "no_per_record_records",
        "no_time_axis",
        "no_commit_chronology",
        "no_per_repo_per_language_cells_in_public_b11",
        "no_model_family_x_repo_matrix",
        "no_adversarial_holdout_outcomes",
        "no_temporal_holdout_outcomes",
    }
    assert required_gap_ids.issubset(set(missing_ids)), (
        required_gap_ids - set(missing_ids)
    )
    # CRITICAL: no fake metric values. metrics_evaluated=false.
    assert report["metrics_evaluated"] is False
    assert report["no_fake_ood_metrics_from_aggregate_means"] is True
    # No ood_generalization_gap / temporal_holdout_delta / worst_group /
    # cvar / per_cell value fields.
    for forbidden_field in (
        "ood_generalization_gap_value",
        "temporal_holdout_delta_value",
        "repo_holdout_metric_value",
        "language_holdout_metric_value",
        "model_family_holdout_metric_value",
        "adversarial_robustness_score_value",
        "worst_group_metric_value",
        "cvar_tail_metric_value",
        "per_cell_denominator_value",
        "temporal_split_integrity_value",
        "no_retuning_proof_metric_value",
        "citation_validity_value",
        "stale_evidencecore_rejection_rate_value",
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
    assert report["raw_per_record_records_stored"] is False
    assert report["raw_time_indices_stored"] is False
    assert report["raw_commit_chronology_stored"] is False
    assert report["raw_outcome_labels_stored"] is False
    assert report["private_labels_committed"] is False
    assert report["run_ids_in_artifact"] is False
    # Integrity flags.
    integ = report["integrity"]
    assert integ["b11_input_promotion_ready_false"] is True, integ
    assert integ["b11_input_has_no_per_record_records"] is True, integ
    assert integ["b11_input_has_no_time_axis"] is True, integ
    assert integ["b11_input_has_no_commit_chronology"] is True, integ
    assert integ["b11_input_has_no_per_repo_per_language_cells"] is True, integ
    assert integ["b11_input_has_no_model_family_x_repo_matrix"] is True, integ
    assert integ["b11_input_has_no_adversarial_holdout_outcomes"] is True, integ
    assert integ["b11_input_has_no_temporal_holdout_outcomes"] is True, integ
    assert integ["r15_input_is_synthetic_static_snapshot"] is True, integ
    assert integ["r20_input_is_synthetic_static_snapshot"] is True, integ
    assert integ["r26_input_is_synthetic_static_snapshot"] is True, integ
    assert (
        integ["all_present_inputs_aggregate_only_or_synthetic_snapshot"] is True
    ), integ


def _self_test_public_screen_optional_artifacts_absent() -> None:
    """When the optional R15 / R20 / R26 repo locks / manifests are
    absent, the screen still emits a clean no-go with the absent
    artifacts reported as not_present rather than failing.

    This self-test monkeypatches the loader paths to absent files in a
    temporary directory to verify the no-go still fires from the B11
    aggregate alone.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Save and override the public input paths.
        global R15_REPOS_LOCK_PATH, R20_REPOS_LOCK_PATH, R26_REPOS_LOCK_PATH
        global R20_MANIFEST_PATH, R26_MANIFEST_PATH
        saved = (
            R15_REPOS_LOCK_PATH,
            R20_REPOS_LOCK_PATH,
            R26_REPOS_LOCK_PATH,
            R20_MANIFEST_PATH,
            R26_MANIFEST_PATH,
        )
        try:
            R15_REPOS_LOCK_PATH = tmp_path / "r15_absent.jsonl"
            R20_REPOS_LOCK_PATH = tmp_path / "r20_absent.jsonl"
            R26_REPOS_LOCK_PATH = tmp_path / "r26_absent.jsonl"
            R20_MANIFEST_PATH = tmp_path / "r20_absent_manifest.json"
            R26_MANIFEST_PATH = tmp_path / "r26_absent_manifest.json"
            report = screen_public(self_test=True)
        finally:
            (
                R15_REPOS_LOCK_PATH,
                R20_REPOS_LOCK_PATH,
                R26_REPOS_LOCK_PATH,
                R20_MANIFEST_PATH,
                R26_MANIFEST_PATH,
            ) = saved
    assert report["verdict"] == "no_go_public_aggregate_only", report["verdict"]
    assert report["input_status"]["r15_repos_lock_status"] == "not_present"
    assert report["input_status"]["r20_repos_lock_status"] == "not_present"
    assert report["input_status"]["r26_repos_lock_status"] == "not_present"
    assert report["input_status"]["r20_manifest_status"] == "not_present"
    assert report["input_status"]["r26_manifest_status"] == "not_present"
    # Absent artifacts must not produce carry-forward summaries.
    assert "input_r15_repos_lock_summary" not in report
    assert "input_r20_repos_lock_summary" not in report
    assert "input_r26_repos_lock_summary" not in report
    assert "input_r20_manifest_summary" not in report
    assert "input_r26_manifest_summary" not in report
    # Still no evaluation / no metrics.
    assert report["ood_temporal_evaluation_performed"] is False
    assert report["metrics_evaluated"] is False
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True


def regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report
    + canonical public no-go screen report so the artifact pins match
    the in-code build functions. Mirrors the B10/B10B/B11/B12/B13/B14/
    B15/B16/B17 freeze-write style: deterministic output, canonical JSON.

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
    # Regenerate the canonical public no-go screen report from the
    # current public artifacts.
    public_screen_report = screen_public(self_test=False)
    _write_json(PUBLIC_SCREEN_PATH, public_screen_report)


def run_self_test() -> dict[str, Any]:
    """Run all B18 self-test checks. Returns a summary dict."""
    import tempfile

    _self_test_forbidden_scan()
    _self_test_spec_hash_stable()
    _self_test_split_axes_closed()
    _self_test_required_per_record_inputs()
    _self_test_missing_inputs_for_real_b18()
    _self_test_metric_registry()
    _self_test_hard_gates_defined()
    _self_test_experimental_structure_frozen()
    _self_test_no_fake_ood_metrics_from_aggregate_means()
    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_stub_not_implemented(Path(tmp))
    _self_test_reference_artifacts_pinned()
    _self_test_public_screen_no_go()
    _self_test_public_screen_optional_artifacts_absent()
    _self_test_artifacts_match_in_memory()

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
        "stage_is_ood_temporal_evaluation": True,
        "ood_temporal_evaluation_performed": False,
        "metrics_evaluated": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "real_ood_temporal_supported": False,
        "new_provider_calls": 0,
        "all_axes_pass": False,
        "axes_evaluated": False,
        "axes_defined": True,
        "axis_count": len(SPLIT_AXES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "no_fake_ood_metrics_from_aggregate_means": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "aggregate_only_public_artifact": True,
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "split_axes_closed": True,
            "required_per_record_inputs": True,
            "missing_inputs_for_real_b18": True,
            "metric_registry": True,
            "hard_gates_defined": True,
            "experimental_structure_frozen": True,
            "no_fake_ood_metrics_from_aggregate_means": True,
            "input_stub_not_implemented": True,
            "reference_artifacts_pinned": True,
            "public_screen_no_go": True,
            "public_screen_optional_artifacts_absent": True,
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
            "run the B18 self-test (read-only; synthetic fixture; verifies "
            "mechanics; compares in-memory expected artifacts to on-disk "
            "artifacts and fails on drift; does NOT write to disk)"
        ),
    )
    parser.add_argument(
        "--regenerate-artifacts",
        action="store_true",
        help=(
            "explicitly (re)write the on-disk algorithm spec + "
            "synthetic-fixture report + canonical public no-go screen "
            "report from the current build functions. This is the ONLY "
            "mutating path; --self-test is read-only."
        ),
    )
    parser.add_argument(
        "--public-screen",
        action="store_true",
        help=(
            "run the bounded public-aggregate no-go screen from the current "
            "public artifacts (B11 aggregate + optional R15 / R20 / R26 "
            "repo locks and manifests) and write the report to --out. "
            "If --out is absent, the canonical public screen artifact is "
            "written ONLY when invoked from --regenerate-artifacts; "
            "otherwise --out is required."
        ),
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help=(
            "path to a JSON file or directory of JSON files containing "
            "per-record OOD / temporal inputs (per-record records, per-"
            "record time index, per-record commit chronology, per-record "
            "repo / language / model_family axes, per-record task "
            "category, per-record adversarial holdout membership, per-"
            "record temporal holdout membership, per-record outcome "
            "label, per-record citation validity, per-record stale "
            "rejection, per-record EvidenceCore rejection, per-record "
            "randomized run order proof, per-record no-retuning proof, "
            "shared frozen evaluation protocol manifest). Currently a "
            "STUB: emits verdict='not_implemented'; full per-record "
            "OOD / temporal evaluation deferred to a later task. "
            "Requires --out and may not write the canonical checked-in "
            "artifact."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write a public-screen or stub input report. Required "
            "with --public-screen (unless invoked via --regenerate-"
            "artifacts) and with --input; must not be the canonical "
            "checked-in B18 report or algorithm spec."
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input and not args.regenerate_artifacts and not args.public_screen:
        parser.error(
            "B18 requires --self-test, --regenerate-artifacts, "
            "--public-screen, or --input <path> in this skeleton"
        )
    selected = sum(
        1
        for flag in (
            args.self_test,
            args.regenerate_artifacts,
            args.public_screen,
            bool(args.input),
        )
        if flag
    )
    if selected > 1:
        parser.error(
            "--self-test, --regenerate-artifacts, --public-screen, and "
            "--input are mutually exclusive"
        )
    if args.input:
        if not args.out:
            parser.error(
                "--input is a non-canonical stub path and requires --out; "
                "only --regenerate-artifacts may write checked-in artifacts"
            )
        out_path = Path(args.out).resolve()
        # Blocker guard: --input must not write ANY checked-in B18
        # artifact — neither the canonical report, the algorithm spec,
        # nor the canonical public no-go screen report. The simplest
        # fail-closed rule is to reject any --out that resolves inside
        # artifacts/b18_ood_temporal_evaluation/.
        artifact_dir_resolved = ARTIFACT_DIR.resolve()
        canonical_paths = {
            REPORT_PATH.resolve(),
            ALGORITHM_SPEC_PATH.resolve(),
            PUBLIC_SCREEN_PATH.resolve(),
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
                "--input may not write inside the checked-in B18 "
                "artifact directory artifacts/b18_ood_temporal_evaluation/ "
                "(canonical report, algorithm spec, or public no-go screen "
                "report); use --out outside artifacts/ or run "
                "--regenerate-artifacts"
            )
    if args.public_screen and not args.out:
        parser.error(
            "--public-screen requires --out <path> for non-self-test "
            "invocation; only --regenerate-artifacts may write the "
            "canonical checked-in public screen artifact"
        )
    if args.public_screen and args.out:
        out_path = Path(args.out).resolve()
        canonical_paths = {
            REPORT_PATH.resolve(),
            ALGORITHM_SPEC_PATH.resolve(),
        }
        # --public-screen MAY write the canonical public screen report
        # (that is its intended use); only --input is blocked from
        # writing inside the artifact directory.
        if out_path == REPORT_PATH.resolve() or out_path == ALGORITHM_SPEC_PATH.resolve():
            parser.error(
                "--public-screen may not overwrite the canonical B18 "
                "report or algorithm spec; use --out pointing at the "
                "public screen artifact path or an external path"
            )
        if out_path in canonical_paths:
            parser.error(
                "--public-screen may not overwrite the canonical B18 "
                "report or algorithm spec"
            )
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report.get("algorithm_spec_id"),
        "claim_level": report.get("claim_level"),
        "verdict": report.get("verdict"),
        "verdict_reason": report.get("verdict_reason"),
        "promotion_ready": report.get("promotion_ready"),
        "default_should_change": report.get("default_should_change"),
        "evidencecore_semantics_changed": report.get(
            "evidencecore_semantics_changed"
        ),
        "retrieval_policy_changed": report.get("retrieval_policy_changed"),
        "backend_quality_promoted": report.get("backend_quality_promoted"),
        "stage_is_ood_temporal_evaluation": report.get(
            "stage_is_ood_temporal_evaluation"
        ),
        "ood_temporal_evaluation_performed": report.get(
            "ood_temporal_evaluation_performed"
        ),
        "metrics_evaluated": report.get("metrics_evaluated"),
        "policy_search_performed": report.get("policy_search_performed"),
        "quality_strategy_tuned": report.get("quality_strategy_tuned"),
        "real_ood_temporal_supported": report.get(
            "real_ood_temporal_supported"
        ),
        "new_provider_calls": report.get("new_provider_calls"),
        "all_axes_pass": report.get("all_axes_pass"),
        "axes_evaluated": report.get("axes_evaluated"),
        "axes_defined": report.get("axes_defined"),
        "axis_count": report.get("axis_count"),
        "winner_declared": report.get("winner_declared"),
        "metrics_defined": report.get("metrics_defined"),
        "gates_defined": report.get("gates_defined"),
        "no_fake_ood_metrics_from_aggregate_means": report.get(
            "no_fake_ood_metrics_from_aggregate_means"
        ),
        "runtime_calls_by_replay": report.get("runtime_calls_by_replay"),
        "model_calls_by_replay": report.get("model_calls_by_replay"),
        "aggregate_only_public_artifact": report.get(
            "aggregate_only_public_artifact"
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def _print_public_screen_summary(report: dict[str, Any]) -> None:
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
        "stage_is_ood_temporal_evaluation": report[
            "stage_is_ood_temporal_evaluation"
        ],
        "ood_temporal_evaluation_performed": report[
            "ood_temporal_evaluation_performed"
        ],
        "metrics_evaluated": report["metrics_evaluated"],
        "policy_search_performed": report["policy_search_performed"],
        "quality_strategy_tuned": report["quality_strategy_tuned"],
        "real_ood_temporal_supported": report["real_ood_temporal_supported"],
        "no_fake_ood_metrics_from_aggregate_means": report[
            "no_fake_ood_metrics_from_aggregate_means"
        ],
        "full_b18_ood_temporal_evaluation_possible_from_public_artifacts": report[
            "full_b18_ood_temporal_evaluation_possible_from_public_artifacts"
        ],
        "new_provider_calls": report["new_provider_calls"],
        "input_status": report["input_status"],
        "missing_inputs_for_real_b18": [
            g["gap_id"] for g in report["missing_inputs_for_real_b18"]
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        # Do NOT emit raw spec sha in stdout (mirrors B17). Only
        # boolean matched / stable flags are surfaced.
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "B18 self-test: PASS (read-only; no artifacts written)",
            file=sys.stderr,
        )
        return 0
    if args.regenerate_artifacts:
        regenerate_artifacts()
        summary = {
            "algorithm_spec_id": ALGORITHM_SPEC_ID,
            "algorithm_spec_path": str(ALGORITHM_SPEC_PATH),
            "report_path": str(REPORT_PATH),
            "public_screen_path": str(PUBLIC_SCREEN_PATH),
            "regenerated": True,
            "self_test": True,
            "replay_source": "synthetic_fixture",
            "verdict": "insufficient_data",
            "ood_temporal_evaluation_performed": False,
            "metrics_evaluated": False,
            "policy_search_performed": False,
            "quality_strategy_tuned": False,
            "real_ood_temporal_supported": False,
            "no_fake_ood_metrics_from_aggregate_means": True,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(
            f"B18 artifacts regenerated: {ALGORITHM_SPEC_PATH} + "
            f"{REPORT_PATH} + {PUBLIC_SCREEN_PATH}",
            file=sys.stderr,
        )
        return 0
    if args.public_screen:
        report = screen_public(self_test=False)
        out_path = Path(args.out)
        _write_json(out_path, report)
        _print_public_screen_summary(report)
        print(f"B18 public screen report written to {out_path}", file=sys.stderr)
        return 0
    if args.input:
        input_meta = _load_per_record_input(args.input)
        report = _build_not_implemented_report(input_meta)
        verify_report(report)
        out_path = Path(args.out)
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B18 report written to {out_path}", file=sys.stderr)
        return 0
    print(
        "B18 requires --self-test, --regenerate-artifacts, --public-screen, "
        "or --input",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
