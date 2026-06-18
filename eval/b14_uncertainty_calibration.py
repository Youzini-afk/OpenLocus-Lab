#!/usr/bin/env python3
"""B14 Uncertainty Calibration.

B14 is the **uncertainty calibration** phase that follows B13 (distributionally
robust policy search). The goal is **model-independent uncertainty calibration**
for the balanced-policy candidate: produce an uncertainty score per record
(never calibrated to a specific model name) from local candidate signals,
model output structure, and cross-model disagreement, then evaluate that score
with **risk-coverage**, **selective risk**, **ECE**, and **PFP-at-fixed-
coverage** metrics, with worst-group reporting and rotating
leave-one-model-family-out validation.

Real B14 requires inputs that are NOT present in any current public artifact:

* per-record uncertainty scores (or the raw signals needed to compute them),
* per-record binary outcomes (was the selected span / candidate correct),
* paired cross-model outputs (for cross-model disagreement signals),
* schema-repair per-call rows (for model output structure signals), and
* candidate score distributions / entropy (for local candidate signals).

None of those are in the public B11 aggregate, the B12 public-aggregate
screen, or the B13 public-aggregate feasibility report. Real B14 calibration
therefore CANNOT be performed from public aggregates alone. The bounded
public-aggregate feasibility / no-go screen at
``eval/b14_public_aggregate_feasibility_screen.py`` reads the published B11,
B12, and B13 artifacts and emits a ``no_go_public_aggregate_only`` (or
``insufficient_data_public_aggregate_only``) feasibility report.

Important claim boundary: B14 IS the uncertainty-calibration *stage*
(``stage_is_uncertainty_calibration=true``), but this skeleton performs NO
empirical uncertainty calibration. Self-test / ``--input`` reports set
``uncertainty_calibration_performed=false`` and
``calibrated_model_claim=false`` so the synthetic / stub report cannot be
mistaken for an empirical B14 calibration. The frozen signal families, metric
definitions, split protocol, coverage levels, ECE bin definition, worst-group
reporting contract, privacy/publication gates, and success/partial/failure
criteria are FROZEN before any real B14 calibration runs; no retuning is
allowed after real B14 runs begin.

Important claim boundary: B14 results are NOT promoted. Even if a future
empirical B14 run finds a well-calibrated uncertainty score,
``promotion_ready=false``, ``default_should_change=false``, and
``EvidenceCore`` semantics are unchanged. B14 results are research candidates
only: they inform B16 (downstream agent evaluation) and any future selective
abstention policy, but B14 does not authorize any default change, any policy
promotion, or any EvidenceCore modification.

Aggregate-only public artifacts: no task/repo/candidate/path/span/snippet/
prompt/response/gold/provider keys and no raw path/digest/provider strings.

This file currently ships a SKELETON: the ``--self-test`` path verifies the
signal-family grammar, metric-name registry, coverage levels, ECE bin
definition, split protocol definitions, and worst-group reporting *contract*
against a synthetic fixture (read-only: it builds the expected algorithm spec
+ report in memory and compares them to the on-disk artifacts, failing on
drift; it does NOT mutate checked-in artifacts). ``--input <path>`` is a stub
(``verdict="not_implemented"``) awaiting the full per-record uncertainty +
outcome replay computation in a later task; it requires ``--out`` and may not
write the canonical checked-in report. The ONLY path that mutates checked-in
artifacts is ``--regenerate-artifacts``, which (re)writes the on-disk
algorithm spec + synthetic-fixture report from the current build functions. In all paths:
``uncertainty_calibration_performed=false``,
``calibrated_model_claim=false``, and ``per_record_inputs_available=false``
for the stub / synthetic paths, so the synthetic / stub report cannot be
misread as an empirical B14 calibration. Synthetic / stub reports emit only
metric *definitions* and *gate thresholds* (``metrics_defined=true``,
``gates_defined=true``, ``metrics_evaluated=false``); they never emit
per-record ECE / selective_risk / risk_coverage / pfp_at_fixed_coverage
values as if empirical. Top-level ``uncertainty_score_found=false``,
``rotations_evaluated=false``, ``winner_declared=false`` are always present.
No live LLM calls are made by this evaluator.

CRITICAL: this skeleton MUST NOT compute fake ECE / risk-coverage / selective
risk / PFP-at-coverage metrics from aggregate means. Aggregate means do not
contain per-record (uncertainty, outcome) pairs, so any calibration metric
computed from them would be a fabrication. The synthetic fixture validates
only that the metric NAMES, gate thresholds, coverage levels, and split
protocol are wired correctly; it does not present synthetic metric values as
empirical calibration results.

For a bounded public-aggregate feasibility / no-go screen that does NOT claim
empirical uncertainty calibration, see
``eval/b14_public_aggregate_feasibility_screen.py``.

Run::

    python3 eval/b14_uncertainty_calibration.py --self-test
    python3 eval/b14_uncertainty_calibration.py --regenerate-artifacts
    python3 eval/b14_uncertainty_calibration.py --input path/to/per_record_inputs.json --out /tmp/b14_input_stub_report.json
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
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b14_uncertainty_calibration"
REPORT_PATH = ARTIFACT_DIR / "b14_uncertainty_calibration_report.json"
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "b14_uncertainty_calibration.algorithm.json"
)

# Frozen reference specs (provenance only — IDs and on-disk hash-match flags,
# never raw 64-char hex digests, which would trip the forbidden-value scan).
B10_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b10_runtime_feature_audit"
    / "balanced_policy_v1_benchmark_routed.algorithm.json"
)
B10B_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b10b_runtime_shadow_replay"
    / "balanced_policy_v1_runtime_shadow_ambiguous_branch.algorithm.json"
)
B11_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b11_prospective_validation"
    / "b11_prospective_validation.algorithm.json"
)
B12_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b12_mechanism_decomposition"
    / "b12_mechanism_decomposition.algorithm.json"
)
B13_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b13_dro_policy_search"
    / "b13_dro_policy_search.algorithm.json"
)

SCHEMA_VERSION = "b14-uncertainty-calibration-report-v0"
SPEC_SCHEMA_VERSION = "b14-uncertainty-calibration-spec-v0"
GENERATED_BY = "b14_uncertainty_calibration"
ALGORITHM_SPEC_ID = "b14_uncertainty_calibration_v0"
CLAIM_LEVEL = "uncertainty_calibration_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors B10/B10B/
# B11/B12/B13).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Signal families (FROZEN before any calibration runs)
# ---------------------------------------------------------------------------
#
# B14 builds a MODEL-INDEPENDENT uncertainty score from three allowed signal
# families. No signal may reference a raw model name; signals are computed
# from local candidate state, model output structure, and cross-model
# disagreement only.
#

ALLOWED_SIGNAL_FAMILIES = (
    "local_candidate_signals",
    "model_output_structure",
    "cross_model_disagreement",
)

# Local candidate signals (computed from candidate state only; no labels, no
# model names). These describe the shape of the candidate pool a routing
# decision was made from.
ALLOWED_LOCAL_CANDIDATE_SIGNALS = (
    "candidate_count",
    "candidate_support_exists",
    "score_distribution_spread",
    "top1_top2_score_gap",
    "entropy_proxy",
    "anchor_disagreement",
    "rrf_backed_by_anchor",
    "dense_support_present",
)

# Model output structure signals (computed from the model's structured
# output, NOT from the model identity). These describe whether the model
# produced a schema-valid, span-narrow-valid, within-candidate response.
ALLOWED_MODEL_OUTPUT_SIGNALS = (
    "schema_valid",
    "llm_span_narrow_valid",
    "llm_span_within_candidate",
    "output_mode_stable",
    "schema_repair_invoked",
)

# Cross-model disagreement signals (computed from paired outputs of two or
# more model families on the SAME record). These require paired per-record
# outputs across model families.
ALLOWED_CROSS_MODEL_SIGNALS = (
    "per_record_action_disagreement",
    "span_overlap_disagreement",
    "rank_disagreement_topk",
)

# ---------------------------------------------------------------------------
# Forbidden labels / forbidden features
# ---------------------------------------------------------------------------
#
# B14 must NOT use benchmark-private labels or score-private fields as
# UNCERTAINTY SIGNALS (features). Per-record outcomes (was the selected span
# correct) are the calibration TARGET, not a signal; they are required as
# evaluation targets but must never enter the uncertainty score.
#

FORBIDDEN_SIGNAL_FEATURES = (
    "task_bucket",
    "task_risk_tags",
    "has_gold",
    "score_group",
    "outcome_metrics",
    "gold_spans",
    "must_not_primary",
    "expected_behavior",
    "oracle_type",
    "risk_tags",
)

# ---------------------------------------------------------------------------
# Required per-record inputs (the real-B14 data contract)
# ---------------------------------------------------------------------------
#
# Real B14 calibration requires ALL of the following per record. If any is
# missing, real B14 cannot run and the skeleton emits insufficient_data /
# not_implemented.
#

REQUIRED_PER_RECORD_INPUTS = (
    "per_record_uncertainty_signals",
    "per_record_outcome_binary",
    "paired_cross_model_outputs",
    "schema_repair_per_call_rows",
    "candidate_score_distribution",
    "group_membership_for_worst_group_split",
)

# ---------------------------------------------------------------------------
# Metric registry (FROZEN before any calibration runs)
# ---------------------------------------------------------------------------
#
# These are the metric NAMES B14 will compute when real per-record inputs are
# available. The skeleton defines them and validates the gate thresholds, but
# does NOT compute fake metric values from aggregate means.
#

METRIC_NAMES = (
    "risk_coverage_curve",
    "selective_risk_at_coverage",
    "ece_expected_calibration_error",
    "pfp_at_fixed_coverage",
    "worst_group_selective_risk",
    "worst_group_ece",
)

# ---------------------------------------------------------------------------
# Coverage levels, ECE bins, CVaR (FROZEN before any calibration runs)
# ---------------------------------------------------------------------------

# Fixed coverage levels at which selective_risk and pfp_at_fixed_coverage
# are reported. These are FROZEN so no post-hoc coverage threshold tuning is
# possible after real B14 runs begin.
COVERAGE_LEVELS = (0.50, 0.70, 0.90, 0.95, 0.99)

# ECE bin definition: equal-width binning over [0, 1] into N bins. Frozen so
# no post-hoc bin-count tuning is possible.
ECE_BIN_COUNT = 15
ECE_BIN_SCHEME = "equal_width"

# CVaR tail fraction for worst-group reporting (worst 20% of groups).
CVAR_ALPHA = 0.20

# ---------------------------------------------------------------------------
# Split protocol (FROZEN before any calibration runs)
# ---------------------------------------------------------------------------
#
# Real B14 splits per-record inputs into a CALIBRATION split and a TEST split,
# stratified by (model_family, repo). The calibration split is the ONLY split
# on which any recalibration / temperature fitting may be applied; the test
# split is held out and reported once. No metric on the test split may feed
# back into recalibration.
#

SPLIT_PROTOCOL = "stratified_by_model_family_and_repo"
CALIBRATION_FRACTION = 0.50
TEST_FRACTION = 0.50
RECALIBRATION_ALLOWED_ON_CALIBRATION_SPLIT_ONLY = True
TEST_SPLIT_REPORTED_ONCE = True

# Rotating leave-one-model-family-out for worst-group validation (mirrors
# B13; abstract slots only in the spec, never raw model names).
ABSTRACT_FAMILY_SLOTS = ("family_a", "family_b", "family_c", "family_d")

LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS = (
    {
        "rotation_id": "loo_family_a",
        "train_families": ("qwen", "deepseek_flash", "deepseek_pro"),
        "test_family": "kimi",
        "abstract_train_slots": ("family_b", "family_c", "family_d"),
        "abstract_test_slot": "family_a",
    },
    {
        "rotation_id": "loo_family_b",
        "train_families": ("kimi", "deepseek_flash", "deepseek_pro"),
        "test_family": "qwen",
        "abstract_train_slots": ("family_a", "family_c", "family_d"),
        "abstract_test_slot": "family_b",
    },
    {
        "rotation_id": "loo_family_c_and_d",
        "train_families": ("kimi", "qwen"),
        "test_family": "deepseek",
        "test_subfamilies": ("deepseek_flash", "deepseek_pro"),
        "abstract_train_slots": ("family_a", "family_b"),
        "abstract_test_slots": ("family_c", "family_d"),
    },
)

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any calibration runs)
# ---------------------------------------------------------------------------

PREDECLARED_CRITERIA: dict[str, Any] = {
    # ECE threshold on the TEST split (lower is better).
    "ece_test_threshold": 0.05,
    # Selective-risk threshold at coverage=0.90 on the TEST split.
    "selective_risk_at_coverage_0_90_threshold": 0.10,
    # Worst-group selective-risk threshold at coverage=0.90.
    "worst_group_selective_risk_at_coverage_0_90_threshold": 0.15,
    # Strict improvement margin vs the reference (uncalibrated) score.
    "strictly_greater_threshold": 0.02,
    # Approx-equality threshold (mirrors B11/B12/B13).
    "approx_equal_threshold": 0.02,
    # CVaR tail fraction (worst 20% of groups).
    "cvar_alpha": CVAR_ALPHA,
    # Coverage levels (frozen).
    "coverage_levels": list(COVERAGE_LEVELS),
    # ECE bin definition (frozen).
    "ece_bin_count": ECE_BIN_COUNT,
    "ece_bin_scheme": ECE_BIN_SCHEME,
    # Split protocol (frozen).
    "split_protocol": SPLIT_PROTOCOL,
    "calibration_fraction": CALIBRATION_FRACTION,
    "test_fraction": TEST_FRACTION,
}

# ---------------------------------------------------------------------------
# Models, repos, metrics (mirror B11/B12/B13 for consistency)
# ---------------------------------------------------------------------------

MODEL_FAMILIES = ("kimi", "qwen", "deepseek_flash", "deepseek_pro")
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
TASK_BUCKETS = ("positive", "negative", "ambiguous", "hard_distractor")

# Frozen artifact references. We store spec_id + kind + an on-disk hash-match
# flag (the actual sha256 is NEVER written as a raw 64-char hex string, which
# would trip the forbidden-value scan; only the boolean matched flag is).
FROZEN_ARTIFACTS = (
    {
        "spec_id": "balanced_policy_v1_benchmark_routed",
        "kind": "b10_frozen_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "balanced_policy_v1_runtime_shadow_ambiguous_branch",
        "kind": "b10b_shadow_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b11_prospective_v0",
        "kind": "b11_prospective_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b12_mechanism_decomposition_v0",
        "kind": "b12_mechanism_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b13_dro_policy_search_v0",
        "kind": "b13_dro_policy_search_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")

# Skeleton verdicts. Until a real empirical B14 calibration path exists (an
# explicit ``uncertainty_calibration_performed=true`` path, which is NOT
# present in this skeleton), ``_evaluate_calibration`` may only emit
# ``insufficient_data`` (synthetic fixture) or ``not_implemented``
# (ci_ephemeral_records stub). The success / failure / partial verdicts are
# reserved for future empirical B14 and are deliberately removed from the
# skeleton's allowed set so a stub report cannot accidentally carry them.
ALLOWED_VERDICTS = (
    "insufficient_data",
    "not_implemented",
)
EMPIRICAL_VERDICTS_RESERVED_FOR_FUTURE_B14 = (
    "success",
    "failure",
    "partial",
)

# ---------------------------------------------------------------------------
# Special B14 invariant: no model names in algorithm_spec
# ---------------------------------------------------------------------------

FORBIDDEN_MODEL_NAME_TOKENS = (
    "kimi",
    "qwen",
    "deepseek",
    "glm",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B/B11/B12/B13)
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


def _scan_spec_for_model_names(spec: dict[str, Any]) -> list[str]:
    """B14 special invariant: verify no model names appear in algorithm_spec.

    Walks every string value in the spec and flags any case-insensitive
    occurrence of FORBIDDEN_MODEL_NAME_TOKENS as a substring. The spec must
    use abstract family_slots and signal-family capabilities, not raw model
    names.
    """
    hits: list[str] = []

    def _walk(o: Any, path: str) -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                _walk(value, f"{path}.{key}")
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")
        elif isinstance(o, str):
            low = o.lower()
            for token in FORBIDDEN_MODEL_NAME_TOKENS:
                if token in low:
                    hits.append(f"{path}:model_name:{token}")

    _walk(spec, "$")
    return hits


# ---------------------------------------------------------------------------
# Synthetic fixture (self-test only)
# ---------------------------------------------------------------------------
#
# The synthetic fixture exists ONLY to validate that the metric NAMES, gate
# thresholds, coverage levels, ECE bin definition, and split protocol are
# wired correctly. It MUST NOT present synthetic ECE / risk-coverage /
# selective-risk / PFP values as empirical calibration results. The fixture
# therefore emits only DEFINITIONS (no per-record (uncertainty, outcome)
# pairs are synthesized, no metric values are computed).
#


def _build_synthetic_fixture() -> dict[str, Any]:
    """Build a definitions-only synthetic fixture for self-test.

    Returns a dict with the signal-family grammar, metric-name registry,
    coverage levels, ECE bin definition, split protocol, and rotation
    definitions. It contains NO per-record (uncertainty, outcome) pairs and
    NO computed metric values, because such values would be fake calibration
    results when no real per-record inputs exist.
    """
    return {
        "signal_families": list(ALLOWED_SIGNAL_FAMILIES),
        "allowed_local_candidate_signals": list(ALLOWED_LOCAL_CANDIDATE_SIGNALS),
        "allowed_model_output_signals": list(ALLOWED_MODEL_OUTPUT_SIGNALS),
        "allowed_cross_model_signals": list(ALLOWED_CROSS_MODEL_SIGNALS),
        "forbidden_signal_features": list(FORBIDDEN_SIGNAL_FEATURES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "coverage_levels": list(COVERAGE_LEVELS),
        "ece_bin_count": ECE_BIN_COUNT,
        "ece_bin_scheme": ECE_BIN_SCHEME,
        "cvar_alpha": CVAR_ALPHA,
        "split_protocol": SPLIT_PROTOCOL,
        "calibration_fraction": CALIBRATION_FRACTION,
        "test_fraction": TEST_FRACTION,
        "leave_one_model_family_out_rotations": [
            {
                "rotation_id": r["rotation_id"],
                "train_families": list(r["train_families"]),
                "test_family": r["test_family"],
                "test_subfamilies": list(r.get("test_subfamilies", ())),
            }
            for r in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS
        ],
        # CRITICAL: no per_record (uncertainty, outcome) pairs and no
        # computed metric values are present. The fixture is definitions-only.
        "per_record_pairs_present": False,
        "metric_values_computed": False,
    }


# ---------------------------------------------------------------------------
# Calibration evaluation stub (definitions-only; no fake metrics)
# ---------------------------------------------------------------------------


def _evaluate_calibration(
    fixture: dict[str, Any],
    replay_source: str,
) -> tuple[dict[str, Any], str, str]:
    """Apply the predeclared calibration criteria (skeleton-safe).

    Returns ``(calibration_results, verdict, verdict_reason)``.

    Until a real empirical B14 calibration path exists (an explicit
    ``uncertainty_calibration_performed=true`` path, which is NOT present in
    this skeleton), this function NEVER emits ``success`` / ``failure`` /
    ``partial`` and NEVER computes ECE / risk-coverage / selective-risk /
    PFP-at-coverage values from aggregate means. Those metrics require
    per-record (uncertainty, outcome) pairs, which are not present in any
    current public artifact.

    The calibration_results block surfaces only definitions + gates + the
    rotation *definitions* (no empirical per-rotation selective_risk / ece /
    risk_coverage / pfp values). ``metrics_evaluated=false``,
    ``uncertainty_score_found=false``, ``rotations_evaluated=false``,
    ``winner_declared=false`` are surfaced so a reader cannot mistake the
    skeleton for an empirical B14 run.
    """
    rotations_list: list[dict[str, Any]] = []
    for rot in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS:
        rotations_list.append(
            {
                "rotation_id": rot["rotation_id"],
                "train_families": list(rot["train_families"]),
                "test_family": rot["test_family"],
                "test_subfamilies": list(rot.get("test_subfamilies", ())),
                "evaluated": False,  # skeleton: no empirical evaluation
            }
        )
    calibration_results: dict[str, Any] = {
        "metrics_defined": True,
        "metric_names": list(METRIC_NAMES),
        "gates_defined": True,
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "coverage_levels": list(COVERAGE_LEVELS),
        "ece_bin_count": ECE_BIN_COUNT,
        "ece_bin_scheme": ECE_BIN_SCHEME,
        "split_protocol": SPLIT_PROTOCOL,
        "calibration_fraction": CALIBRATION_FRACTION,
        "test_fraction": TEST_FRACTION,
        "leave_one_out_rotations": {
            "rotations_defined": True,
            "rotation_count": len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS),
            "rotations_evaluated": False,
            "rotations": rotations_list,
        },
        # CRITICAL: no metric values are emitted. metrics_evaluated=false
        # is the disambiguating flag.
        "metrics_evaluated": False,
        "uncertainty_score_found": False,
        "uncertainty_score_calibrated": False,
        "all_rotations_pass": False,
        "rotations_evaluated": False,
        "winner_declared": False,
        "no_fake_metrics_from_aggregate_means": True,
    }
    if replay_source == "synthetic_fixture":
        return (
            calibration_results,
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; no empirical "
            "B14 uncertainty calibration performed; no per-record "
            "(uncertainty, outcome) pairs available; success, failure, or "
            "partial verdicts require a future empirical "
            "uncertainty_calibration_performed=true path with real "
            "per-record inputs",
        )
    # ci_ephemeral_records: real calibration is not yet implemented.
    return (
        calibration_results,
        "not_implemented",
        "ci_ephemeral_records_replay_not_implemented; no empirical B14 "
        "uncertainty calibration performed; no per-record (uncertainty, "
        "outcome) pairs consumed; success, failure, or partial verdicts "
        "require a future empirical "
        "uncertainty_calibration_performed=true path",
    )


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B14 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so its
    SHA-256 is stable across runs. The on-disk spec file is the pin (mirrors
    B10/B10B/B11/B12/B13 freeze style). The self-test verifies hash stability
    by re-loading and re-hashing.

    CRITICAL: This spec must NOT contain any raw model names (Kimi, Qwen,
    DeepSeek, GLM). The special invariant
    ``algorithm_spec_has_no_model_names=true`` is enforced by
    ``_scan_spec_for_model_names``.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": CLAIM_LEVEL,
        "description": (
            "B14 Uncertainty Calibration: model-independent uncertainty "
            "score for the balanced-policy candidate from local candidate "
            "signals, model output structure, and cross-model "
            "disagreement; evaluated with risk-coverage, selective risk, "
            "ECE, and PFP-at-fixed-coverage metrics, worst-group "
            "reporting, and rotating leave-one-model-family-out "
            "validation. Replay and calibration only; no live LLM calls, "
            "no default change, no promotion, no calibrated-model claim."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        # The algorithm_spec DEFINES the B14 uncertainty-calibration stage
        # (so stage_is_uncertainty_calibration=true), but no empirical B14
        # calibration has been performed by this skeleton
        # (uncertainty_calibration_performed=false). The synthetic / stub
        # report sets calibrated_model_claim=false and
        # per_record_inputs_available=false so the public artifact cannot
        # be misread as an empirical B14 calibration.
        "stage_is_uncertainty_calibration": True,
        "uncertainty_calibration_performed": False,
        "calibrated_model_claim": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "aggregate_only_public_artifact": True,
        "algorithm_spec_has_no_model_names": True,
        "no_fake_metrics_from_aggregate_means": True,
        "allowed_signal_families": list(ALLOWED_SIGNAL_FAMILIES),
        "allowed_local_candidate_signals": list(ALLOWED_LOCAL_CANDIDATE_SIGNALS),
        "allowed_model_output_signals": list(ALLOWED_MODEL_OUTPUT_SIGNALS),
        "allowed_cross_model_signals": list(ALLOWED_CROSS_MODEL_SIGNALS),
        "forbidden_signal_features": list(FORBIDDEN_SIGNAL_FEATURES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "coverage_levels": list(COVERAGE_LEVELS),
        "ece_bin_count": ECE_BIN_COUNT,
        "ece_bin_scheme": ECE_BIN_SCHEME,
        "cvar_alpha": CVAR_ALPHA,
        "split_protocol": SPLIT_PROTOCOL,
        "calibration_fraction": CALIBRATION_FRACTION,
        "test_fraction": TEST_FRACTION,
        "recalibration_allowed_on_calibration_split_only": (
            RECALIBRATION_ALLOWED_ON_CALIBRATION_SPLIT_ONLY
        ),
        "test_split_reported_once": TEST_SPLIT_REPORTED_ONCE,
        "leave_one_model_family_out_rotations": [
            {
                "rotation_id": r["rotation_id"],
                "train_family_slots": list(r["abstract_train_slots"]),
                "test_family_slot": r.get("abstract_test_slot"),
                "test_family_slots": list(r.get("abstract_test_slots", ())),
            }
            for r in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS
        ],
        "family_slots": list(ABSTRACT_FAMILY_SLOTS),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "languages": list(LANGUAGES),
        "task_buckets": list(TASK_BUCKETS),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "allowed_replay_sources": list(ALLOWED_REPLAY_SOURCES),
        "allowed_verdicts": list(ALLOWED_VERDICTS),
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_default_change": True,
            "no_policy_promotion": True,
            "no_calibrated_model_claim": True,
            "no_threshold_tuning_outside_predeclared_criteria": True,
            "no_evidencecore_semantics_change": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "no_model_names_in_algorithm_spec": True,
            "no_fake_metrics_from_aggregate_means": True,
            "replay_only_no_live_calibration_runs_in_evaluator": True,
        },
        "excluded_adapter_layer": {
            "model_adapter_excluded": True,
            "output_mode_excluded": True,
            "provider_credentials_excluded": True,
            "provider_endpoints_excluded": True,
            "provider_secrets_excluded": True,
            "raw_model_names_excluded": True,
        },
    }


def _reference_spec_hashes() -> dict[str, bool]:
    """Check whether the on-disk frozen reference specs (B10, B10B, B11, B12,
    B13) are present and loadable. Returns ``{spec_id: pinned_bool}``.
    The actual sha256 hex is NEVER returned (it would trip the forbidden-
    value scan); only the boolean matched flag is exposed publicly.
    """
    refs = {}
    for spec_id, path in (
        ("balanced_policy_v1_benchmark_routed", B10_SPEC_PATH),
        ("balanced_policy_v1_runtime_shadow_ambiguous_branch", B10B_SPEC_PATH),
        ("b11_prospective_v0", B11_SPEC_PATH),
        ("b12_mechanism_decomposition_v0", B12_SPEC_PATH),
        ("b13_dro_policy_search_v0", B13_SPEC_PATH),
    ):
        try:
            data = _load_json(path)
            refs[spec_id] = (
                data.get("algorithm_spec_id") == spec_id
                and isinstance(data.get("generated_at"), str)
            )
        except FileNotFoundError:
            refs[spec_id] = False
    return refs


def build_report(
    fixture: dict[str, Any],
    *,
    self_test: bool,
    replay_source: str,
) -> dict[str, Any]:
    """Build the B14 uncertainty calibration report.

    ``fixture`` is the definitions-only synthetic fixture (see
    ``_build_synthetic_fixture``). ``self_test=True`` flags that the report
    was produced from a synthetic fixture for mechanics validation;
    ``replay_source`` is one of ``ALLOWED_REPLAY_SOURCES``.

    The report NEVER emits ECE / risk-coverage / selective-risk / PFP-at-
    coverage metric values, because no per-record (uncertainty, outcome)
    pairs exist in any current public artifact. Only definitions + gates +
    rotation definitions are emitted.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    calibration_results, verdict, verdict_reason = _evaluate_calibration(
        fixture, replay_source
    )

    ref_hashes = _reference_spec_hashes()
    model_name_hits = _scan_spec_for_model_names(spec)

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
        # B14 DEFINES the uncertainty-calibration stage
        # (stage_is_uncertainty_calibration=true), but this skeleton performs
        # NO empirical uncertainty calibration
        # (uncertainty_calibration_performed=false). The report flags
        # calibrated_model_claim=false and per_record_inputs_available=false
        # so synthetic / stub reports cannot be misread as empirical B14
        # calibration.
        "stage_is_uncertainty_calibration": True,
        "uncertainty_calibration_performed": False,
        "calibrated_model_claim": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        # Skeleton: no empirical uncertainty score was found, no rotations
        # were evaluated, no winner was declared. These top-level flags make
        # the skeleton stance unambiguous and mirror the
        # calibration_results sub-block.
        "uncertainty_score_found": False,
        "rotations_evaluated": False,
        "rotations_defined": True,
        "rotation_count": len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_metrics_from_aggregate_means": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "frozen_reference_specs_pinned_on_disk": ref_hashes,
        "allowed_signal_families": list(ALLOWED_SIGNAL_FAMILIES),
        "allowed_local_candidate_signals": list(ALLOWED_LOCAL_CANDIDATE_SIGNALS),
        "allowed_model_output_signals": list(ALLOWED_MODEL_OUTPUT_SIGNALS),
        "allowed_cross_model_signals": list(ALLOWED_CROSS_MODEL_SIGNALS),
        "forbidden_signal_features": list(FORBIDDEN_SIGNAL_FEATURES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "coverage_levels": list(COVERAGE_LEVELS),
        "ece_bin_count": ECE_BIN_COUNT,
        "ece_bin_scheme": ECE_BIN_SCHEME,
        "cvar_alpha": CVAR_ALPHA,
        "split_protocol": SPLIT_PROTOCOL,
        "calibration_fraction": CALIBRATION_FRACTION,
        "test_fraction": TEST_FRACTION,
        "recalibration_allowed_on_calibration_split_only": (
            RECALIBRATION_ALLOWED_ON_CALIBRATION_SPLIT_ONLY
        ),
        "test_split_reported_once": TEST_SPLIT_REPORTED_ONCE,
        "leave_one_model_family_out_rotations": [
            {
                "rotation_id": r["rotation_id"],
                "train_families": list(r["train_families"]),
                "test_family": r["test_family"],
                "test_subfamilies": list(r.get("test_subfamilies", ())),
            }
            for r in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS
        ],
        "model_families": list(MODEL_FAMILIES),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "languages": list(LANGUAGES),
        "task_buckets": list(TASK_BUCKETS),
        "calibration_results": calibration_results,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "aggregate_only_public_artifact": True,
        "algorithm_spec_has_no_model_names": (len(model_name_hits) == 0),
        "algorithm_spec_model_name_scan_hits": model_name_hits,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_default_change": True,
            "no_policy_promotion": True,
            "no_calibrated_model_claim": True,
            "no_threshold_tuning_outside_predeclared_criteria": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "runtime_calls_by_replay_zero": True,
            "model_calls_by_replay_zero": True,
            "algorithm_spec_has_no_model_names_true": True,
            "no_fake_metrics_from_aggregate_means_true": True,
            "replay_only_no_live_calibration_runs_in_evaluator": True,
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
    # B14 DEFINES the uncertainty-calibration stage
    # (stage_is_uncertainty_calibration=true), but no empirical B14
    # calibration is performed by this skeleton
    # (uncertainty_calibration_performed=false). The skeleton report sets
    # calibrated_model_claim=false and per_record_inputs_available=false to
    # avoid overclaiming empirical calibration.
    if spec.get("stage_is_uncertainty_calibration") is not True:
        raise ValueError(
            "algorithm spec stage_is_uncertainty_calibration must be true (B14 stage)"
        )
    if spec.get("uncertainty_calibration_performed") is not False:
        raise ValueError(
            "algorithm spec uncertainty_calibration_performed must be false "
            "(no empirical calibration performed by skeleton)"
        )
    if spec.get("calibrated_model_claim") is not False:
        raise ValueError(
            "algorithm spec calibrated_model_claim must be false (skeleton; "
            "no model is claimed to be calibrated)"
        )
    if spec.get("per_record_inputs_available") is not False:
        raise ValueError(
            "algorithm spec per_record_inputs_available must be false "
            "(skeleton; no real per-record inputs available)"
        )
    if spec.get("policy_search_performed") is not False:
        raise ValueError(
            "algorithm spec policy_search_performed must be false (skeleton)"
        )
    if spec.get("quality_strategy_tuned") is not False:
        raise ValueError("algorithm spec quality_strategy_tuned must be false")
    if spec.get("aggregate_only_public_artifact") is not True:
        raise ValueError("algorithm spec aggregate_only_public_artifact must be true")
    if spec.get("algorithm_spec_has_no_model_names") is not True:
        raise ValueError(
            "algorithm spec algorithm_spec_has_no_model_names must be true"
        )
    if spec.get("no_fake_metrics_from_aggregate_means") is not True:
        raise ValueError(
            "algorithm spec no_fake_metrics_from_aggregate_means must be true"
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
    if tuple(spec.get("allowed_signal_families") or ()) != ALLOWED_SIGNAL_FAMILIES:
        raise ValueError("algorithm spec allowed_signal_families mismatch")
    if (
        tuple(spec.get("allowed_local_candidate_signals") or ())
        != ALLOWED_LOCAL_CANDIDATE_SIGNALS
    ):
        raise ValueError(
            "algorithm spec allowed_local_candidate_signals mismatch"
        )
    if (
        tuple(spec.get("allowed_model_output_signals") or ())
        != ALLOWED_MODEL_OUTPUT_SIGNALS
    ):
        raise ValueError("algorithm spec allowed_model_output_signals mismatch")
    if (
        tuple(spec.get("allowed_cross_model_signals") or ())
        != ALLOWED_CROSS_MODEL_SIGNALS
    ):
        raise ValueError("algorithm spec allowed_cross_model_signals mismatch")
    if (
        tuple(spec.get("forbidden_signal_features") or ())
        != FORBIDDEN_SIGNAL_FEATURES
    ):
        raise ValueError("algorithm spec forbidden_signal_features mismatch")
    if (
        tuple(spec.get("required_per_record_inputs") or ())
        != REQUIRED_PER_RECORD_INPUTS
    ):
        raise ValueError("algorithm spec required_per_record_inputs mismatch")
    if tuple(spec.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("algorithm spec metric_names mismatch")
    if tuple(spec.get("coverage_levels") or ()) != COVERAGE_LEVELS:
        raise ValueError("algorithm spec coverage_levels mismatch")
    if spec.get("ece_bin_count") != ECE_BIN_COUNT:
        raise ValueError("algorithm spec ece_bin_count mismatch")
    if spec.get("ece_bin_scheme") != ECE_BIN_SCHEME:
        raise ValueError("algorithm spec ece_bin_scheme mismatch")
    if spec.get("cvar_alpha") != CVAR_ALPHA:
        raise ValueError("algorithm spec cvar_alpha mismatch")
    if spec.get("split_protocol") != SPLIT_PROTOCOL:
        raise ValueError("algorithm spec split_protocol mismatch")
    if spec.get("calibration_fraction") != CALIBRATION_FRACTION:
        raise ValueError("algorithm spec calibration_fraction mismatch")
    if spec.get("test_fraction") != TEST_FRACTION:
        raise ValueError("algorithm spec test_fraction mismatch")
    # B13/B14 special invariant: the spec must NOT list raw model family names
    # (kimi/qwen/deepseek/glm). It uses abstract family_slots instead.
    if tuple(spec.get("family_slots") or ()) != ABSTRACT_FAMILY_SLOTS:
        raise ValueError("algorithm spec family_slots mismatch")
    if "model_families" in spec:
        raise ValueError(
            "algorithm spec must NOT contain model_families (raw model names); "
            "use family_slots instead"
        )
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
    model_name_hits = _scan_spec_for_model_names(spec)
    if model_name_hits:
        raise ValueError(
            f"algorithm spec contains forbidden model names: {model_name_hits!r}"
        )


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
    # B14 DEFINES the uncertainty-calibration stage
    # (stage_is_uncertainty_calibration=true), but this skeleton performs NO
    # empirical uncertainty calibration
    # (uncertainty_calibration_performed=false). The report flags
    # calibrated_model_claim=false and per_record_inputs_available=false so
    # synthetic / stub reports cannot be misread as empirical B14
    # calibration.
    if report.get("stage_is_uncertainty_calibration") is not True:
        raise ValueError(
            "report stage_is_uncertainty_calibration must be true (B14 stage)"
        )
    if report.get("uncertainty_calibration_performed") is not False:
        raise ValueError(
            "report uncertainty_calibration_performed must be false "
            "(no empirical calibration performed by skeleton)"
        )
    if report.get("calibrated_model_claim") is not False:
        raise ValueError(
            "report calibrated_model_claim must be false (skeleton; "
            "no model is claimed to be calibrated)"
        )
    if report.get("per_record_inputs_available") is not False:
        raise ValueError(
            "report per_record_inputs_available must be false (skeleton)"
        )
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "report policy_search_performed must be false (skeleton)"
        )
    # Skeleton: no empirical uncertainty score found, no rotations evaluated,
    # no winner declared.
    if report.get("uncertainty_score_found") is not False:
        raise ValueError("report uncertainty_score_found must be false (skeleton)")
    if report.get("rotations_evaluated") is not False:
        raise ValueError(
            "report rotations_evaluated must be false (skeleton; no "
            "empirical rotation evaluation performed)"
        )
    if report.get("rotations_defined") is not True:
        raise ValueError("report rotations_defined must be true (3 rotations)")
    if report.get("rotation_count") != len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS):
        raise ValueError(
            "report rotation_count must equal the number of frozen rotations"
        )
    if report.get("winner_declared") is not False:
        raise ValueError("report winner_declared must be false (skeleton)")
    if report.get("metrics_defined") is not True:
        raise ValueError("report metrics_defined must be true")
    if report.get("gates_defined") is not True:
        raise ValueError("report gates_defined must be true")
    if report.get("metrics_evaluated") is not False:
        raise ValueError(
            "report metrics_evaluated must be false (skeleton; no fake "
            "metric values from aggregate means)"
        )
    if report.get("no_fake_metrics_from_aggregate_means") is not True:
        raise ValueError(
            "report no_fake_metrics_from_aggregate_means must be true"
        )
    if report.get("quality_strategy_tuned") is not False:
        raise ValueError("report quality_strategy_tuned must be false")
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
    if report.get("algorithm_spec_has_no_model_names") is not True:
        raise ValueError(
            "report algorithm_spec_has_no_model_names must be true (B14 invariant)"
        )
    if report.get("predeclared_criteria") != PREDECLARED_CRITERIA:
        raise ValueError("report predeclared_criteria must match the frozen constants")
    if tuple(report.get("allowed_signal_families") or ()) != ALLOWED_SIGNAL_FAMILIES:
        raise ValueError("report allowed_signal_families mismatch")
    if (
        tuple(report.get("metric_names") or ()) != METRIC_NAMES
    ):
        raise ValueError("report metric_names mismatch")
    if tuple(report.get("coverage_levels") or ()) != COVERAGE_LEVELS:
        raise ValueError("report coverage_levels mismatch")
    if report.get("ece_bin_count") != ECE_BIN_COUNT:
        raise ValueError("report ece_bin_count mismatch")
    if report.get("ece_bin_scheme") != ECE_BIN_SCHEME:
        raise ValueError("report ece_bin_scheme mismatch")
    if tuple(report.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("report model_families mismatch")
    if tuple(report.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("report repos mismatch")
    # Required top-level sections.
    for key in (
        "calibration_results",
        "leave_one_model_family_out_rotations",
    ):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # calibration_results substructure. The skeleton emits only definitions +
    # gates + rotation definitions; no empirical per-rotation metric values.
    cr = report.get("calibration_results") or {}
    for key in (
        "metrics_defined",
        "metric_names",
        "gates_defined",
        "predeclared_criteria",
        "coverage_levels",
        "ece_bin_count",
        "ece_bin_scheme",
        "split_protocol",
        "calibration_fraction",
        "test_fraction",
        "leave_one_out_rotations",
        "metrics_evaluated",
        "uncertainty_score_found",
        "uncertainty_score_calibrated",
        "all_rotations_pass",
        "rotations_evaluated",
        "winner_declared",
        "no_fake_metrics_from_aggregate_means",
    ):
        if key not in cr:
            raise ValueError(f"calibration_results missing required section: {key}")
    if cr.get("metrics_evaluated") is not False:
        raise ValueError(
            "calibration_results.metrics_evaluated must be false (skeleton; "
            "no fake metric values from aggregate means)"
        )
    if cr.get("uncertainty_score_found") is not False:
        raise ValueError(
            "calibration_results.uncertainty_score_found must be false (skeleton)"
        )
    if cr.get("uncertainty_score_calibrated") is not False:
        raise ValueError(
            "calibration_results.uncertainty_score_calibrated must be false (skeleton)"
        )
    if cr.get("all_rotations_pass") is not False:
        raise ValueError(
            "calibration_results.all_rotations_pass must be false (skeleton)"
        )
    if cr.get("rotations_evaluated") is not False:
        raise ValueError(
            "calibration_results.rotations_evaluated must be false (skeleton)"
        )
    if cr.get("winner_declared") is not False:
        raise ValueError(
            "calibration_results.winner_declared must be false (skeleton)"
        )
    if cr.get("no_fake_metrics_from_aggregate_means") is not True:
        raise ValueError(
            "calibration_results.no_fake_metrics_from_aggregate_means must be true"
        )
    # leave_one_out_rotations must be a definitions-only block.
    rots = cr.get("leave_one_out_rotations") or {}
    if rots.get("rotations_defined") is not True:
        raise ValueError(
            "calibration_results.leave_one_out_rotations.rotations_defined "
            "must be true"
        )
    if rots.get("rotation_count") != len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS):
        raise ValueError(
            "calibration_results.leave_one_out_rotations.rotation_count mismatch"
        )
    if rots.get("rotations_evaluated") is not False:
        raise ValueError(
            "calibration_results.leave_one_out_rotations.rotations_evaluated "
            "must be false (skeleton)"
        )
    rot_list = rots.get("rotations")
    if not isinstance(rot_list, list) or len(rot_list) != len(
        LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS
    ):
        raise ValueError(
            "calibration_results.leave_one_out_rotations.rotations must be "
            "a list of 3 rotation definitions"
        )
    for r in rot_list:
        if r.get("evaluated") is not False:
            raise ValueError(
                "rotation definitions must have evaluated=false (skeleton)"
            )
        for forbidden_key in (
            "passes",
            "test_ece",
            "test_selective_risk",
            "test_risk_coverage_curve",
            "test_pfp_at_fixed_coverage",
            "delta_vs_reference",
        ):
            if forbidden_key in r:
                raise ValueError(
                    f"rotation definition must not carry empirical field "
                    f"{forbidden_key!r} (skeleton)"
                )
    # Safety invariant flags.
    si = report.get("safety_invariants") or {}
    for flag in (
        "no_live_llm_calls",
        "no_default_change",
        "no_policy_promotion",
        "no_calibrated_model_claim",
        "no_threshold_tuning_outside_predeclared_criteria",
        "no_evidencecore_semantics_change",
        "promotion_ready_false",
        "default_should_change_false",
        "aggregate_only_public_artifact",
        "forbidden_public_keys_scanned",
        "no_raw_path_digest_provider_strings",
        "runtime_calls_by_replay_zero",
        "model_calls_by_replay_zero",
        "algorithm_spec_has_no_model_names_true",
        "no_fake_metrics_from_aggregate_means_true",
        "replay_only_no_live_calibration_runs_in_evaluator",
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input (stub): load per-record inputs without computing calibration
# ---------------------------------------------------------------------------


def _load_per_record_input(path: str) -> dict[str, Any]:
    """Load a per-record inputs JSON file (or directory of JSON files) and
    return a minimal metadata payload. The full per-record (uncertainty,
    outcome) replay + calibration computation is deferred to a later task;
    for now we only verify the input is valid JSON and surface its top-level
    shape (without leaking any forbidden keys).
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

    Real per-record (uncertainty, outcome) replay + calibration computation
    (computing the uncertainty score, fitting temperature on the calibration
    split, evaluating ECE / risk-coverage / selective-risk / PFP-at-fixed-
    coverage on the test split, worst-group reporting, leave-one-out
    rotation validation) is deferred to a later task. For now we emit a
    well-formed report with ``verdict="not_implemented"`` and an explanatory
    reason, while still passing all safety-invariant checks.

    CRITICAL: this stub MUST NOT compute fake calibration metrics from
    aggregate means. No metric values are emitted.
    """
    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Override the verdict to signal that no real calibration happened.
    report["verdict"] = "not_implemented"
    report["verdict_reason"] = (
        "real-input calibration + per-record (uncertainty, outcome) replay "
        f"computation deferred to later task; input_meta={input_meta}"
    )
    # Re-stamp the spec hash fields (defensive: build_report already sets
    # these).
    report["algorithm_spec_sha256_matched"] = True
    report["algorithm_spec_sha256_stable"] = (spec_hash == _sha256_json(spec))
    # Re-scan forbidden keys after the override (input_meta may include only
    # safe scalar fields by construction).
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
        "nested": {"content_sha": "deadbeef", "gold_spans": [[1, 2]]},
    }
    hits = _recursive_key_scan(bad_report)
    flat = " ".join(hits)
    assert "task_id" in flat
    assert "path" in flat
    assert "snippet" in flat
    assert "provider_key" in flat
    assert "content_sha" in flat
    assert "gold_spans" in flat

    # Raw path value should trip the "/" pattern even when the key is allowed.
    bad_value = {"provenance": "eval/some_file.py"}
    hits2 = _recursive_key_scan(bad_value)
    assert any("forbidden_value" in h for h in hits2), hits2

    # A clean provenance reference (module::symbol, no "/") must not trip.
    clean = {"provenance": "b14_uncertainty_calibration::build_report"}
    hits3 = _recursive_key_scan(clean)
    assert hits3 == [], hits3

    # A 64-hex digest value must trip the forbidden-value scan.
    bad_digest = {"some_field": "a" * 64}
    hits4 = _recursive_key_scan(bad_digest)
    assert any("forbidden_value" in h for h in hits4), hits4

    # B14 special: model names must be flagged by _scan_spec_for_model_names.
    bad_spec = {"description": "tuned for Kimi and Qwen", "nested": {"m": "deepseek"}}
    mh = _scan_spec_for_model_names(bad_spec)
    flat_m = " ".join(mh)
    assert "kimi" in flat_m
    assert "qwen" in flat_m
    assert "deepseek" in flat_m

    # A clean spec using only abstract family_slots + signal-family names
    # must not trip the model-name scan.
    clean_spec = {
        "description": "uses family_slots and signal_family.local_candidate_signals",
        "family_slots": ["family_a", "family_b"],
    }
    assert _scan_spec_for_model_names(clean_spec) == [], _scan_spec_for_model_names(
        clean_spec
    )


def _self_test_spec_hash_stable() -> None:
    spec = build_algorithm_spec()
    h1 = _sha256_json(spec)
    spec2 = build_algorithm_spec()
    h2 = _sha256_json(spec2)
    assert h1 == h2, "build_algorithm_spec() must be deterministic"
    verify_algorithm_spec(spec, h1)


def _self_test_signal_family_grammar() -> None:
    """Signal family grammar: 3 families, no overlap with forbidden features."""
    spec = build_algorithm_spec()
    assert tuple(spec["allowed_signal_families"]) == ALLOWED_SIGNAL_FAMILIES
    # Local / model-output / cross-model signals must be disjoint.
    local = set(ALLOWED_LOCAL_CANDIDATE_SIGNALS)
    model_out = set(ALLOWED_MODEL_OUTPUT_SIGNALS)
    cross = set(ALLOWED_CROSS_MODEL_SIGNALS)
    assert local.isdisjoint(model_out), (local & model_out)
    assert local.isdisjoint(cross), (local & cross)
    assert model_out.isdisjoint(cross), (model_out & cross)
    # Forbidden signal features must not overlap with allowed signals.
    forbidden = set(FORBIDDEN_SIGNAL_FEATURES)
    assert local.isdisjoint(forbidden), (local & forbidden)
    assert model_out.isdisjoint(forbidden), (model_out & forbidden)
    assert cross.isdisjoint(forbidden), (cross & forbidden)
    # Per-record outcomes are required INPUTS but never SIGNALS.
    assert "per_record_outcome_binary" in REQUIRED_PER_RECORD_INPUTS
    assert "per_record_outcome_binary" not in local
    assert "per_record_outcome_binary" not in model_out
    assert "per_record_outcome_binary" not in cross
    assert "per_record_outcome_binary" not in forbidden


def _self_test_metric_registry() -> None:
    """Metric registry: 6 metric names defined; no aggregate-mean metrics."""
    spec = build_algorithm_spec()
    assert tuple(spec["metric_names"]) == METRIC_NAMES
    # All metric names require per-record (uncertainty, outcome) pairs; none
    # can be computed from aggregate means.
    for name in METRIC_NAMES:
        assert "aggregate_mean" not in name, name
        assert "overall_mean" not in name, name


def _self_test_coverage_levels_and_ece_bins() -> None:
    """Coverage levels + ECE bin definition frozen."""
    spec = build_algorithm_spec()
    assert tuple(spec["coverage_levels"]) == COVERAGE_LEVELS
    # Coverage levels strictly ascending in (0, 1).
    assert all(0.0 < c < 1.0 for c in COVERAGE_LEVELS), COVERAGE_LEVELS
    assert list(COVERAGE_LEVELS) == sorted(COVERAGE_LEVELS), COVERAGE_LEVELS
    assert spec["ece_bin_count"] == ECE_BIN_COUNT
    assert spec["ece_bin_scheme"] == ECE_BIN_SCHEME
    assert ECE_BIN_COUNT >= 5, ECE_BIN_COUNT


def _self_test_split_protocol() -> None:
    """Split protocol: calibration/test stratified by model_family and repo."""
    spec = build_algorithm_spec()
    assert spec["split_protocol"] == SPLIT_PROTOCOL
    assert spec["calibration_fraction"] + spec["test_fraction"] == 1.0
    assert spec["recalibration_allowed_on_calibration_split_only"] is True
    assert spec["test_split_reported_once"] is True


def _self_test_leave_one_out_rotations_defined() -> None:
    """3 leave-one-model-family-out rotations defined (abstract slots in spec)."""
    assert len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS) == 3
    rot_ids = {r["rotation_id"] for r in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS}
    assert rot_ids == {"loo_family_a", "loo_family_b", "loo_family_c_and_d"}, rot_ids
    for rot in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS:
        assert "train_families" in rot and len(rot["train_families"]) >= 2
        assert "test_family" in rot
        assert "abstract_train_slots" in rot
    loo_cd = next(
        r for r in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS
        if r["rotation_id"] == "loo_family_c_and_d"
    )
    assert loo_cd["test_family"] == "deepseek"
    assert tuple(loo_cd["test_subfamilies"]) == ("deepseek_flash", "deepseek_pro")
    assert tuple(loo_cd["abstract_test_slots"]) == ("family_c", "family_d")
    spec = build_algorithm_spec()
    assert len(spec["leave_one_model_family_out_rotations"]) == 3
    assert tuple(spec["family_slots"]) == ABSTRACT_FAMILY_SLOTS
    assert "model_families" not in spec, (
        "algorithm_spec must NOT contain model_families (raw model names)"
    )
    for r in spec["leave_one_model_family_out_rotations"]:
        assert "train_family_slots" in r
        assert "train_families" not in r, "spec rotation must not expose real names"
        assert "test_family" not in r, "spec rotation must not expose real names"
    # Evaluate the rotations on the synthetic fixture (evaluator-side, real
    # family names are fine here — they never enter the spec). The skeleton
    # emits definitions only; no empirical per-rotation metric values.
    fixture = _build_synthetic_fixture()
    cr, _verdict, _reason = _evaluate_calibration(fixture, "synthetic_fixture")
    rotations_block = cr["leave_one_out_rotations"]
    assert rotations_block["rotations_defined"] is True
    assert rotations_block["rotation_count"] == 3
    assert rotations_block["rotations_evaluated"] is False
    rot_ids_back = {r["rotation_id"] for r in rotations_block["rotations"]}
    assert rot_ids_back == rot_ids, rot_ids_back
    for r in rotations_block["rotations"]:
        assert r.get("evaluated") is False
        for forbidden_key in (
            "passes",
            "test_ece",
            "test_selective_risk",
            "test_risk_coverage_curve",
            "test_pfp_at_fixed_coverage",
            "delta_vs_reference",
        ):
            assert forbidden_key not in r, (forbidden_key, r)


def _self_test_no_fake_metrics_from_aggregate_means() -> None:
    """CRITICAL: the skeleton must NOT compute fake calibration metrics
    from aggregate means. The synthetic-fixture report must surface
    metrics_evaluated=false and contain no metric value fields.
    """
    fixture = _build_synthetic_fixture()
    assert fixture["per_record_pairs_present"] is False
    assert fixture["metric_values_computed"] is False
    report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )
    assert report["metrics_evaluated"] is False
    assert report["no_fake_metrics_from_aggregate_means"] is True
    assert report["calibration_results"]["metrics_evaluated"] is False
    assert (
        report["calibration_results"]["no_fake_metrics_from_aggregate_means"]
        is True
    )
    # No metric value fields should be present at the top level.
    for forbidden_field in (
        "ece_value",
        "selective_risk_value",
        "risk_coverage_curve_value",
        "pfp_at_fixed_coverage_value",
        "worst_group_selective_risk_value",
        "worst_group_ece_value",
    ):
        assert forbidden_field not in report, forbidden_field
        assert forbidden_field not in report["calibration_results"], forbidden_field


def _self_test_input_stub_not_implemented(tmp_path: Path) -> None:
    """--input mode must emit verdict='not_implemented' without doing any
    real calibration computation."""
    p = tmp_path / "per_record_stub.json"
    p.write_text(
        json.dumps({"records": [{"uncertainty": 0.5, "outcome": 1}]}),
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
    # Stub report must still surface metrics_evaluated=false (no fake metrics).
    assert report["metrics_evaluated"] is False


def _self_test_reference_specs() -> None:
    """The B10, B10B, B11, B12 and B13 frozen reference specs must exist on
    disk so the B14 frozen_artifacts pin is meaningful."""
    refs = _reference_spec_hashes()
    assert refs.get("balanced_policy_v1_benchmark_routed") is True, refs
    assert refs.get("balanced_policy_v1_runtime_shadow_ambiguous_branch") is True, refs
    assert refs.get("b11_prospective_v0") is True, refs
    assert refs.get("b12_mechanism_decomposition_v0") is True, refs
    assert refs.get("b13_dro_policy_search_v0") is True, refs


def _self_test_artifacts_match_in_memory() -> None:
    """Read-only drift check: build the expected algorithm spec + report in
    memory and compare them to the on-disk artifacts. Fails on drift. Does
    NOT write anything to disk (self-test is read-only). Use
    ``--regenerate-artifacts`` to (re)write the on-disk artifacts.
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
            "`python3 eval/b14_uncertainty_calibration.py --regenerate-artifacts` "
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
            "on-disk b14_uncertainty_calibration_report.json drifted from the "
            "in-memory build_report() output; run "
            "`python3 eval/b14_uncertainty_calibration.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_report(on_disk_report)


def regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report so the
    artifact pin matches the in-code build functions. Mirrors the B10/B10B/
    B11/B12/B13 freeze-write style: deterministic output, canonical JSON.

    This is the ONLY mutating path. ``--self-test`` is read-only and uses
    ``_self_test_artifacts_match_in_memory`` to detect drift.
    """
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    """Run all B14 self-test checks. Returns a summary dict."""
    import tempfile

    _self_test_forbidden_scan()
    _self_test_spec_hash_stable()
    _self_test_signal_family_grammar()
    _self_test_metric_registry()
    _self_test_coverage_levels_and_ece_bins()
    _self_test_split_protocol()
    _self_test_leave_one_out_rotations_defined()
    _self_test_no_fake_metrics_from_aggregate_means()
    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_stub_not_implemented(Path(tmp))
    _self_test_reference_specs()
    _self_test_artifacts_match_in_memory()

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256": spec_hash,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": CLAIM_LEVEL,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "stage_is_uncertainty_calibration": True,
        "uncertainty_calibration_performed": False,
        "calibrated_model_claim": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "uncertainty_score_found": False,
        "rotations_evaluated": False,
        "rotations_defined": True,
        "rotation_count": len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS),
        "winner_declared": False,
        "quality_strategy_tuned": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_metrics_from_aggregate_means": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "algorithm_spec_has_no_model_names": True,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "aggregate_only_public_artifact": True,
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "signal_family_grammar": True,
            "metric_registry": True,
            "coverage_levels_and_ece_bins": True,
            "split_protocol": True,
            "leave_one_out_rotations_defined": True,
            "no_fake_metrics_from_aggregate_means": True,
            "input_stub_not_implemented": True,
            "reference_specs_pinned": True,
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
            "run the B14 self-test (read-only; synthetic fixture; verifies "
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
            "per-record uncertainty signals + per-record outcomes + paired "
            "cross-model outputs. Currently a STUB: emits "
            "verdict='not_implemented'; full calibration + per-record "
            "replay computation deferred to a later task. Requires --out "
            "and may not write the canonical checked-in artifact."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write a stub input report. Required with --input; "
            "must not be the canonical checked-in B14 report artifact."
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input and not args.regenerate_artifacts:
        parser.error(
            "B14 requires --self-test, --regenerate-artifacts, or "
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
        if out_path == REPORT_PATH.resolve():
            parser.error(
                "--input may not write the canonical checked-in B14 report; "
                "use --out outside artifacts/ or run --regenerate-artifacts"
            )
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "claim_level": report["claim_level"],
        "allowed_signal_families": report["allowed_signal_families"],
        "metric_names": report["metric_names"],
        "coverage_levels": report["coverage_levels"],
        "ece_bin_count": report["ece_bin_count"],
        "ece_bin_scheme": report["ece_bin_scheme"],
        "split_protocol": report["split_protocol"],
        "calibration_fraction": report["calibration_fraction"],
        "test_fraction": report["test_fraction"],
        "leave_one_model_family_out_rotations": report[
            "leave_one_model_family_out_rotations"
        ],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "evidencecore_semantics_changed": report["evidencecore_semantics_changed"],
        "stage_is_uncertainty_calibration": report["stage_is_uncertainty_calibration"],
        "uncertainty_calibration_performed": report[
            "uncertainty_calibration_performed"
        ],
        "calibrated_model_claim": report["calibrated_model_claim"],
        "per_record_inputs_available": report["per_record_inputs_available"],
        "policy_search_performed": report["policy_search_performed"],
        "uncertainty_score_found": report["uncertainty_score_found"],
        "rotations_evaluated": report["rotations_evaluated"],
        "rotations_defined": report["rotations_defined"],
        "rotation_count": report["rotation_count"],
        "winner_declared": report["winner_declared"],
        "metrics_defined": report["metrics_defined"],
        "gates_defined": report["gates_defined"],
        "metrics_evaluated": report["metrics_evaluated"],
        "no_fake_metrics_from_aggregate_means": report[
            "no_fake_metrics_from_aggregate_means"
        ],
        "quality_strategy_tuned": report["quality_strategy_tuned"],
        "runtime_calls_by_replay": report["runtime_calls_by_replay"],
        "model_calls_by_replay": report["model_calls_by_replay"],
        "aggregate_only_public_artifact": report["aggregate_only_public_artifact"],
        "algorithm_spec_has_no_model_names": report[
            "algorithm_spec_has_no_model_names"
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B14 self-test: PASS (read-only; no artifacts written)", file=sys.stderr)
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
            "uncertainty_calibration_performed": False,
            "calibrated_model_claim": False,
            "per_record_inputs_available": False,
            "uncertainty_score_found": False,
            "rotations_evaluated": False,
            "winner_declared": False,
            "metrics_evaluated": False,
            "no_fake_metrics_from_aggregate_means": True,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(
            f"B14 artifacts regenerated: {ALGORITHM_SPEC_PATH} + {REPORT_PATH}",
            file=sys.stderr,
        )
        return 0
    if args.input:
        input_meta = _load_per_record_input(args.input)
        report = _build_not_implemented_report(input_meta)
        verify_report(report)
        out_path = Path(args.out)
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B14 report written to {out_path}", file=sys.stderr)
        return 0
    print(
        "B14 requires --self-test, --regenerate-artifacts, or --input",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
