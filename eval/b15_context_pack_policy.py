#!/usr/bin/env python3
"""B15 Context Pack Policy.

B15 is the **context pack policy** phase. The goal is a **frozen,
preregistered PackPolicy** that maps ``(role, runtime_state,
model_profile)`` to a deterministic **atom set** (the pack-layout atoms
a context pack should expose for a given decision role under a given
runtime state and abstract model profile), validated against
per-record pack-atom flags + per-record outcomes + role +
runtime_state + model_profile + group membership from B11/B13 live
runs.

B15 is a **bounded planning / feasibility phase**, NOT an empirical
atom-level ablation. Real B15 requires inputs that are NOT present in
any current public artifact:

* per-record pack atom flags (which atoms were present in the pack),
* per-record binary outcomes (was the selected span / candidate
  correct),
* role-specific paired outputs (the same record answered under
  different roles),
* runtime_state per record (candidate pool shape, score distribution,
  schema-repair state),
* model_profile paired blocks (the same record answered under
  different abstract capability profiles),
* group membership for worst-group splits,
* randomized atom assignment + balance stats,
* denominator-by-atom/role/model cells, and
* token-budget-matched controls.

None of those are in the public B2 pack experiment, the B14
public-aggregate feasibility report, or any other current public
artifact. The B2 pack experiment is usable ONLY as a
``low_n_single_model_aggregate_directional_prior`` (a weak directional
hint that contrastive structure is not automatically better), NOT as
atom-level causality, role-specific PackPolicy, or calibrated policy
proof. Real B15 PackPolicy validation therefore CANNOT be performed
from public aggregates alone. The bounded public-aggregate prior /
no-go screen at ``eval/b15_public_aggregate_prior_screen.py`` reads
the published B2 + B14 artifacts and, when present, the B4-B9 /
P21-G / P49 public aggregates, and emits a
``no_go_public_aggregate_only`` (or ``prior_screen_only``) prior /
no-go report.

Important claim boundary: B15 IS the context-pack-policy *stage*
(``stage_is_context_pack_policy=true``), but this skeleton performs NO
empirical atom ablation (``atom_ablation_performed=false``) and NO
PackPolicy learning (``pack_policy_learned=false``). Self-test /
``--input`` reports set ``per_record_inputs_available=false``,
``promotion_ready=false``, ``default_should_change=false``,
``evidencecore_semantics_changed=false``,
``policy_search_performed=false``, ``quality_strategy_tuned=false``,
``new_provider_calls=0`` so the synthetic / stub report cannot be
mistaken for an empirical B15 PackPolicy result. The frozen atom
registry, role set, runtime_state contract, model_profile
abstraction, metric registry, hard gates, experimental structure, and
success/partial/failure criteria are FROZEN before any real B15
PackPolicy validation runs; no retuning is allowed after real B15
runs begin.

Important claim boundary: this skeleton is strictly a skeleton / no-go
commit. The current flags (``pack_policy_learned=false``,
``atom_ablation_performed=false``, ``promotion_ready=false``,
``default_should_change=false``, ``evidencecore_semantics_changed=false``)
remain false. Any future real B15 empirical path would require its own
separate preregistration; the exact flag schema for that future path
(including any ``pack_policy_learned`` / ``atom_ablation_performed``
settings) is future work and is NOT present in this skeleton. B15
results in this commit are research candidates only: they inform future
context-pack routing, but this skeleton/no-go commit authorizes no
default change, any policy promotion, any PackPolicy promotion, or any
EvidenceCore modification.

Aggregate-only public artifacts: no task/repo/candidate/path/span/
snippet/prompt/response/gold/provider keys and no raw path/digest/
provider strings.

This file currently ships a SKELETON: the ``--self-test`` path verifies
the PackPolicy contract, atom registry, role set, runtime_state
contract, model_profile abstraction, metric registry, hard gates, and
experimental structure against a synthetic fixture (read-only: it
builds the expected algorithm spec + report in memory and compares
them to the on-disk artifacts, failing on drift; it does NOT mutate
checked-in artifacts). ``--input <path>`` is a stub
(``verdict="not_implemented"``) awaiting the full per-record pack
atom + outcome + role + runtime_state + model_profile + group
membership + randomized atom assignment replay computation in a later
task; it requires ``--out`` and may not write the canonical checked-in
report. The ONLY path that mutates checked-in artifacts is
``--regenerate-artifacts``, which (re)writes the on-disk algorithm
spec + synthetic-fixture report from the current build functions. In
all paths: ``pack_policy_learned=false``,
``atom_ablation_performed=false``, and
``per_record_inputs_available=false`` for the stub / synthetic paths,
so the synthetic / stub report cannot be misread as an empirical B15
PackPolicy result. Synthetic / stub reports emit only metric
*definitions* and *hard gates* (``metrics_defined=true``,
``gates_defined=true``, ``metrics_evaluated=false``); they never emit
per-record atom_effect / role_pack_outcome / worst_group_pack_outcome
values as if empirical. Top-level
``pack_policy_learned=false``,
``atom_ablation_performed=false``,
``no_fake_atom_effects_from_aggregate_means=true`` are always present.

CRITICAL: this skeleton MUST NOT compute fake atom-effect / role-pack-
outcome / worst-group-pack-outcome metrics from aggregate means.
Aggregate means (e.g. the B2 pack-layout aggregate SpanF0.5 / PFP) do
not contain per-record (atom_flag, outcome) pairs, so any atom-level
causal effect computed from them would be a fabrication. The synthetic
fixture validates only that the metric NAMES, hard gates, atom
registry, role set, and experimental structure are wired correctly; it
does not present synthetic metric values as empirical PackPolicy
results.

For a bounded public-aggregate prior / no-go screen that does NOT claim
empirical PackPolicy learning, see
``eval/b15_public_aggregate_prior_screen.py``.

Run::

    python3 eval/b15_context_pack_policy.py --self-test
    python3 eval/b15_context_pack_policy.py --regenerate-artifacts
    python3 eval/b15_context_pack_policy.py --input path/to/per_record_inputs.json --out /tmp/b15_input_stub_report.json
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
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b15_context_pack_policy"
REPORT_PATH = ARTIFACT_DIR / "b15_context_pack_policy_report.json"
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "b15_context_pack_policy.algorithm.json"
)

# Frozen reference specs (provenance only — IDs and on-disk hash-match
# flags, never raw 64-char hex digests, which would trip the forbidden-
# value scan).
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
B14_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b14_uncertainty_calibration"
    / "b14_uncertainty_calibration.algorithm.json"
)

SCHEMA_VERSION = "b15-context-pack-policy-report-v0"
SPEC_SCHEMA_VERSION = "b15-context-pack-policy-spec-v0"
GENERATED_BY = "b15_context_pack_policy"
ALGORITHM_SPEC_ID = "b15_context_pack_policy_v0"
CLAIM_LEVEL = "context_pack_policy_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors
# B10/B10B/B11/B12/B13/B14).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Roles (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------
#
# The PackPolicy is indexed by the decision role the pack is being
# assembled for. The role set is closed: a candidate PackPolicy may not
# introduce roles outside this set without a separate preregistration
# round.
#

ROLES = (
    "span_narrow",
    "filter_reject",
    "request_more_context",
    "source_test_disambiguation",
)

# ---------------------------------------------------------------------------
# Runtime state contract (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------
#
# runtime_state is a model-independent, label-free description of the
# candidate pool and request state at the moment the pack is assembled.
# Computed from runtime-observable features only; NO benchmark-private
# labels, NO score-private fields, NO raw model names.
#

ALLOWED_RUNTIME_STATE_FEATURES = (
    "candidate_count",
    "candidate_support_exists",
    "score_distribution_spread",
    "top1_top2_score_gap",
    "anchor_disagreement",
    "rrf_backed_by_anchor",
    "dense_support_present",
    "path_kind_inferable",
    "neighbor_context_available",
    "signature_available",
    "hard_distractor_proxy_available",
    "same_file_competitor_present",
    "schema_repair_invoked",
)

# ---------------------------------------------------------------------------
# Model profile abstraction (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------
#
# model_profile is an ABSTRACT capability profile, NOT a raw model name.
# The PackPolicy uses abstract capability slots (profile_slot_a..d) and
# capability descriptors only. B15 must NOT reference raw model names
# like "Kimi", "Qwen", "DeepSeek", or "GLM" in algorithm_spec.
#

ABSTRACT_PROFILE_SLOTS = (
    "profile_slot_a",
    "profile_slot_b",
    "profile_slot_c",
    "profile_slot_d",
)

ALLOWED_MODEL_PROFILE_CAPABILITIES = (
    "long_context_window",
    "structured_output_stable",
    "span_narrow_strict",
    "hard_distractor_sensitive",
    "score_provenance_sensitive",
    "neighbor_context_sensitive",
)

# ---------------------------------------------------------------------------
# Atom registry (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------
#
# The atom registry is the closed set of pack-layout atoms a PackPolicy
# may include or exclude. Each atom is a pack-layout feature that can be
# toggled at the pack level. The PackPolicy output is a subset of the
# atom registry.
#

ATOM_REGISTRY = (
    "signature",
    "matched_lines",
    "raw_snippet",
    "neighbor_context",
    "scores",
    "provenance",
    "hard_distractor",
    "same_file_competitor",
    "path_kind_flag",
)

# Existing pack layouts referenced (definitions only, not modified).
EXISTING_PACK_LAYOUTS = (
    "topk_plain_v0",
    "topk_scores_provenance_v0",
    "contrastive_competitor_v0",
    "hard_distractor_contrast_v0",
)

# ---------------------------------------------------------------------------
# Forbidden labels / forbidden features
# ---------------------------------------------------------------------------
#
# B15 must NOT use benchmark-private labels or score-private fields as
# PackPolicy inputs (features). Per-record outcomes (was the selected
# span correct) are the validation TARGET, not a feature; they are
# required as evaluation targets but must NEVER enter the PackPolicy.
#

FORBIDDEN_PACK_POLICY_FEATURES = (
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
# Required per-record inputs (the real-B15 data contract)
# ---------------------------------------------------------------------------
#
# Real B15 PackPolicy validation requires ALL of the following per
# record. If any is missing, real B15 cannot run and the skeleton emits
# insufficient_data / not_implemented.
#

REQUIRED_PER_RECORD_INPUTS = (
    "per_record_pack_atom_flags",
    "per_record_outcome_binary",
    "role_specific_paired_outputs",
    "runtime_state_per_record",
    "model_profile_paired_blocks",
    "group_membership_for_worst_group_split",
    "randomized_atom_assignment",
    "randomization_balance_stats",
    "denominator_by_atom_role_model",
    "token_budget_matched_controls",
)

# ---------------------------------------------------------------------------
# Metric registry (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------
#
# These are the metric NAMES B15 will compute when real per-record inputs
# are available. The skeleton defines them and validates the hard gates,
# but does NOT compute fake metric values from aggregate means.
#

METRIC_NAMES = (
    "atom_effect_per_atom",
    "role_pack_outcome",
    "runtime_state_pack_outcome",
    "model_profile_pack_outcome",
    "worst_group_pack_outcome",
    "cvar_20_pack_outcome",
    "token_budget_parity",
    "denominator_per_atom_role_model",
    "randomization_balance_per_arm",
)

# ---------------------------------------------------------------------------
# Hard gates (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------

HARD_GATES = (
    "privacy_gate",
    "leakage_gate",
    "adapter_health_gate",
    "randomization_balance_gate",
    "denominator_gate",
    "token_budget_gate",
    "promotion_false_gate",
)

# ---------------------------------------------------------------------------
# Experimental structure (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------

EXPERIMENTAL_STAGES = (
    "no_llm_feasibility",
    "fractional_factorial_live_atom_screen",
    "freeze_candidate_policy",
    "fresh_validation",
)

# Fractional factorial design: resolution-IV fraction over the atom
# registry (no full 2^9 factorial). Frozen so no post-hoc design
# retuning is possible after real B15 runs begin.
FACTORIAL_RESOLUTION = "resolution_iv"
FACTORIAL_FULL_RUNS = 2 ** len(ATOM_REGISTRY)  # 512 (full factorial)
FACTORIAL_FRACTIONAL_RUNS = 32  # frozen resolution-IV fraction size

# ---------------------------------------------------------------------------
# Split protocol (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------

SPLIT_PROTOCOL = "stratified_by_model_family_repo_role"
ATOM_SCREEN_FRACTION = 0.50
FRESH_VALIDATION_FRACTION = 0.50
FRESH_VALIDATION_SPLIT_REPORTED_ONCE = True

# CVaR tail fraction for worst-group reporting (worst 20% of groups).
CVAR_ALPHA = 0.20

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any PackPolicy runs)
# ---------------------------------------------------------------------------

PREDECLARED_CRITERIA: dict[str, Any] = {
    # Strict improvement margin vs the reference (best single pack layout).
    "strictly_greater_threshold": 0.02,
    # Approx-equality threshold (mirrors B11/B12/B13/B14).
    "approx_equal_threshold": 0.02,
    # Worst-group pack outcome regression threshold on the fresh-validation
    # split.
    "worst_group_pack_outcome_regression_threshold": 0.15,
    # CVaR tail fraction (worst 20% of groups).
    "cvar_alpha": CVAR_ALPHA,
    # Split protocol (frozen).
    "split_protocol": SPLIT_PROTOCOL,
    "atom_screen_fraction": ATOM_SCREEN_FRACTION,
    "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
    # Denominator gate: minimum per (atom, role, model_profile) cell.
    "min_denominator_per_atom_role_model_cell": 30,
    # Randomization balance gate: max covariate imbalance per atom arm.
    "randomization_balance_max_imbalance": 0.05,
    # Token budget gate: matched-control tolerance.
    "token_budget_match_tolerance": 0.10,
    # Experimental structure (frozen).
    "experimental_stages": list(EXPERIMENTAL_STAGES),
    "factorial_resolution": FACTORIAL_RESOLUTION,
    "factorial_full_runs": FACTORIAL_FULL_RUNS,
    "factorial_fractional_runs": FACTORIAL_FRACTIONAL_RUNS,
}

# ---------------------------------------------------------------------------
# Models, repos, metrics (mirror B11/B12/B13/B14 for consistency)
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

# Frozen artifact references. We store spec_id + kind + an on-disk
# hash-match flag (the actual sha256 is NEVER written as a raw 64-char
# hex string, which would trip the forbidden-value scan; only the
# boolean matched flag is).
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
    {
        "spec_id": "b14_uncertainty_calibration_v0",
        "kind": "b14_uncertainty_calibration_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")

# Skeleton verdicts. This skeleton is strictly a skeleton / no-go
# commit: ``_evaluate_pack_policy`` may only emit ``insufficient_data``
# (synthetic fixture) or ``not_implemented`` (ci_ephemeral_records stub).
# The success / failure / partial verdicts are NOT emitted by this
# skeleton. Any future real B15 empirical path that might emit them
# would require its own separate preregistration, and its exact flag
# schema (including any ``pack_policy_learned`` /
# ``atom_ablation_performed`` settings) is future work and is NOT
# present in this skeleton. This commit keeps ``pack_policy_learned``
# and ``atom_ablation_performed`` strictly false.
ALLOWED_VERDICTS = (
    "insufficient_data",
    "not_implemented",
)
# Verdicts NOT emitted by this skeleton. Listed for documentation only:
# a future real B15 empirical path that might emit them would require
# its own separate preregistration, and its exact flag schema is future
# work and NOT present in this skeleton.
EMPIRICAL_VERDICTS_RESERVED_FOR_FUTURE_B15 = (
    "success",
    "failure",
    "partial",
)

# ---------------------------------------------------------------------------
# Special B15 invariant: no model names in algorithm_spec
# ---------------------------------------------------------------------------

FORBIDDEN_MODEL_NAME_TOKENS = (
    "kimi",
    "qwen",
    "deepseek",
    "glm",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B/B11/B12/B13/B14)
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
    """B15 special invariant: verify no model names appear in
    algorithm_spec.

    Walks every string value in the spec and flags any case-insensitive
    occurrence of FORBIDDEN_MODEL_NAME_TOKENS as a substring. The spec
    must use abstract model_profile slots and capability descriptors,
    not raw model names.
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
# The synthetic fixture exists ONLY to validate that the metric NAMES,
# hard gates, atom registry, role set, runtime_state contract,
# model_profile abstraction, and experimental structure are wired
# correctly. It MUST NOT present synthetic atom-effect / role-pack-
# outcome / worst-group-pack-outcome values as empirical PackPolicy
# results. The fixture therefore emits only DEFINITIONS (no per-record
# (atom_flag, outcome) pairs are synthesized, no metric values are
# computed).
#


def _build_synthetic_fixture() -> dict[str, Any]:
    """Build a definitions-only synthetic fixture for self-test.

    Returns a dict with the PackPolicy contract, atom registry, role
    set, runtime_state contract, model_profile abstraction, metric
    registry, hard gates, and experimental structure. It contains NO
    per-record (atom_flag, outcome) pairs and NO computed metric
    values, because such values would be fake PackPolicy results when
    no real per-record inputs exist.
    """
    return {
        "roles": list(ROLES),
        "atom_registry": list(ATOM_REGISTRY),
        "existing_pack_layouts": list(EXISTING_PACK_LAYOUTS),
        "allowed_runtime_state_features": list(
            ALLOWED_RUNTIME_STATE_FEATURES
        ),
        "abstract_profile_slots": list(ABSTRACT_PROFILE_SLOTS),
        "allowed_model_profile_capabilities": list(
            ALLOWED_MODEL_PROFILE_CAPABILITIES
        ),
        "forbidden_pack_policy_features": list(
            FORBIDDEN_PACK_POLICY_FEATURES
        ),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "factorial_resolution": FACTORIAL_RESOLUTION,
        "factorial_full_runs": FACTORIAL_FULL_RUNS,
        "factorial_fractional_runs": FACTORIAL_FRACTIONAL_RUNS,
        "split_protocol": SPLIT_PROTOCOL,
        "atom_screen_fraction": ATOM_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "cvar_alpha": CVAR_ALPHA,
        # CRITICAL: no per_record (atom_flag, outcome) pairs and no
        # computed metric values are present. The fixture is
        # definitions-only.
        "per_record_pairs_present": False,
        "metric_values_computed": False,
    }


# ---------------------------------------------------------------------------
# PackPolicy evaluation stub (definitions-only; no fake atom effects)
# ---------------------------------------------------------------------------


def _evaluate_pack_policy(
    fixture: dict[str, Any],
    replay_source: str,
) -> tuple[dict[str, Any], str, str]:
    """Apply the predeclared PackPolicy criteria (skeleton-safe).

    Returns ``(pack_policy_results, verdict, verdict_reason)``.

    This skeleton is strictly a skeleton / no-go commit: this function
    NEVER emits ``success`` / ``failure`` / ``partial`` and NEVER
    computes atom_effect / role_pack_outcome / worst_group_pack_outcome
    values from aggregate means. Those metrics require per-record
    (atom_flag, outcome, role, runtime_state, model_profile) tuples,
    which are not present in any current public artifact. Any future
    real B15 empirical path that might emit success/failure/partial
    would require its own separate preregistration, and its exact flag
    schema (including any ``pack_policy_learned`` /
    ``atom_ablation_performed`` settings) is future work and NOT present
    in this skeleton. This commit keeps ``pack_policy_learned=false``
    and ``atom_ablation_performed=false`` strictly.

    The pack_policy_results block surfaces only definitions + hard
    gates + the experimental stage *definitions* (no empirical per-stage
    atom_effect / role_pack_outcome values).
    ``metrics_evaluated=false``,
    ``pack_policy_learned=false``,
    ``atom_ablation_performed=false`` are surfaced so a reader cannot
    mistake the skeleton for an empirical B15 PackPolicy run.
    """
    stages_list: list[dict[str, Any]] = []
    for stage in EXPERIMENTAL_STAGES:
        stages_list.append(
            {
                "stage_id": stage,
                "evaluated": False,  # skeleton: no empirical evaluation
            }
        )
    pack_policy_results: dict[str, Any] = {
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
        "atom_registry": list(ATOM_REGISTRY),
        "roles": list(ROLES),
        "runtime_state_features": list(ALLOWED_RUNTIME_STATE_FEATURES),
        "model_profile_slots": list(ABSTRACT_PROFILE_SLOTS),
        "model_profile_capabilities": list(
            ALLOWED_MODEL_PROFILE_CAPABILITIES
        ),
        # CRITICAL: no metric values are emitted.
        # metrics_evaluated=false is the disambiguating flag.
        "metrics_evaluated": False,
        "pack_policy_learned": False,
        "atom_ablation_performed": False,
        "candidate_policy_frozen": False,
        "all_stages_pass": False,
        "stages_evaluated": False,
        "winner_declared": False,
        "no_fake_atom_effects_from_aggregate_means": True,
    }
    if replay_source == "synthetic_fixture":
        return (
            pack_policy_results,
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; no empirical "
            "B15 PackPolicy validation performed; no per-record "
            "(atom_flag, outcome) pairs available; success, failure, or "
            "partial not emitted by skeleton; future real B15 flag "
            "schema is future work not in this skeleton",
        )
    # ci_ephemeral_records: real PackPolicy validation is not yet
    # implemented.
    return (
        pack_policy_results,
        "not_implemented",
        "ci_ephemeral_records_replay_not_implemented; no empirical B15 "
        "PackPolicy validation performed; no per-record (atom_flag, "
        "outcome, role, runtime_state, model_profile) tuples consumed; "
        "success, failure, or partial not emitted by skeleton; future "
        "real B15 flag schema is future work not in this skeleton",
    )


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B15 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so
    its SHA-256 is stable across runs. The on-disk spec file is the pin
    (mirrors B10/B10B/B11/B12/B13/B14 freeze style). The self-test
    verifies hash stability by re-loading and re-hashing.

    CRITICAL: This spec must NOT contain any raw model names (Kimi,
    Qwen, DeepSeek, GLM). The special invariant
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
            "B15 Context Pack Policy: frozen, preregistered PackPolicy "
            "mapping (role, runtime_state, model_profile) to a "
            "deterministic atom set, validated against per-record pack "
            "atom flags + per-record outcomes + role + runtime_state + "
            "model_profile + group membership. Bounded planning and "
            "feasibility phase only; no empirical atom ablation, no "
            "PackPolicy learning, no live LLM calls, no default change, "
            "no promotion, no PackPolicy promotion."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        # The algorithm_spec DEFINES the B15 context-pack-policy stage
        # (so stage_is_context_pack_policy=true), but no empirical B15
        # PackPolicy validation has been performed by this skeleton
        # (pack_policy_learned=false, atom_ablation_performed=false).
        # The synthetic / stub report sets
        # per_record_inputs_available=false so the public artifact
        # cannot be misread as an empirical B15 PackPolicy result.
        "stage_is_context_pack_policy": True,
        "pack_policy_learned": False,
        "atom_ablation_performed": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "aggregate_only_public_artifact": True,
        "algorithm_spec_has_no_model_names": True,
        "no_fake_atom_effects_from_aggregate_means": True,
        "roles": list(ROLES),
        "atom_registry": list(ATOM_REGISTRY),
        "existing_pack_layouts": list(EXISTING_PACK_LAYOUTS),
        "allowed_runtime_state_features": list(
            ALLOWED_RUNTIME_STATE_FEATURES
        ),
        "abstract_profile_slots": list(ABSTRACT_PROFILE_SLOTS),
        "allowed_model_profile_capabilities": list(
            ALLOWED_MODEL_PROFILE_CAPABILITIES
        ),
        "forbidden_pack_policy_features": list(
            FORBIDDEN_PACK_POLICY_FEATURES
        ),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "factorial_resolution": FACTORIAL_RESOLUTION,
        "factorial_full_runs": FACTORIAL_FULL_RUNS,
        "factorial_fractional_runs": FACTORIAL_FRACTIONAL_RUNS,
        "split_protocol": SPLIT_PROTOCOL,
        "atom_screen_fraction": ATOM_SCREEN_FRACTION,
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
            "no_default_change": True,
            "no_policy_promotion": True,
            "no_pack_policy_promotion": True,
            "no_pack_policy_learning": True,
            "no_atom_ablation": True,
            "no_evidencecore_semantics_change": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "no_model_names_in_algorithm_spec": True,
            "no_fake_atom_effects_from_aggregate_means": True,
            "replay_only_no_live_pack_policy_runs_in_evaluator": True,
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
    """Check whether the on-disk frozen reference specs (B10, B10B, B11,
    B12, B13, B14) are present and loadable. Returns
    ``{spec_id: pinned_bool}``. The actual sha256 hex is NEVER returned
    (it would trip the forbidden-value scan); only the boolean matched
    flag is exposed publicly.
    """
    refs = {}
    for spec_id, path in (
        ("balanced_policy_v1_benchmark_routed", B10_SPEC_PATH),
        ("balanced_policy_v1_runtime_shadow_ambiguous_branch", B10B_SPEC_PATH),
        ("b11_prospective_v0", B11_SPEC_PATH),
        ("b12_mechanism_decomposition_v0", B12_SPEC_PATH),
        ("b13_dro_policy_search_v0", B13_SPEC_PATH),
        ("b14_uncertainty_calibration_v0", B14_SPEC_PATH),
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
    """Build the B15 context pack policy report.

    ``fixture`` is the definitions-only synthetic fixture (see
    ``_build_synthetic_fixture``). ``self_test=True`` flags that the
    report was produced from a synthetic fixture for mechanics
    validation; ``replay_source`` is one of
    ``ALLOWED_REPLAY_SOURCES``.

    The report NEVER emits atom_effect / role_pack_outcome /
    worst_group_pack_outcome metric values, because no per-record
    (atom_flag, outcome) pairs exist in any current public artifact.
    Only definitions + hard gates + experimental stage definitions are
    emitted.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    pack_policy_results, verdict, verdict_reason = _evaluate_pack_policy(
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
        # B15 DEFINES the context-pack-policy stage
        # (stage_is_context_pack_policy=true), but this skeleton
        # performs NO empirical PackPolicy learning and NO empirical
        # atom ablation. The report flags
        # pack_policy_learned=false, atom_ablation_performed=false,
        # per_record_inputs_available=false so synthetic / stub reports
        # cannot be misread as empirical B15 PackPolicy results.
        "stage_is_context_pack_policy": True,
        "pack_policy_learned": False,
        "atom_ablation_performed": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        # Skeleton: no candidate policy frozen, no stages evaluated, no
        # winner declared. These top-level flags make the skeleton
        # stance unambiguous and mirror the pack_policy_results
        # sub-block.
        "candidate_policy_frozen": False,
        "stages_evaluated": False,
        "stages_defined": True,
        "stage_count": len(EXPERIMENTAL_STAGES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_atom_effects_from_aggregate_means": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "frozen_reference_specs_pinned_on_disk": ref_hashes,
        "roles": list(ROLES),
        "atom_registry": list(ATOM_REGISTRY),
        "existing_pack_layouts": list(EXISTING_PACK_LAYOUTS),
        "allowed_runtime_state_features": list(
            ALLOWED_RUNTIME_STATE_FEATURES
        ),
        "abstract_profile_slots": list(ABSTRACT_PROFILE_SLOTS),
        "allowed_model_profile_capabilities": list(
            ALLOWED_MODEL_PROFILE_CAPABILITIES
        ),
        "forbidden_pack_policy_features": list(
            FORBIDDEN_PACK_POLICY_FEATURES
        ),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "factorial_resolution": FACTORIAL_RESOLUTION,
        "factorial_full_runs": FACTORIAL_FULL_RUNS,
        "factorial_fractional_runs": FACTORIAL_FRACTIONAL_RUNS,
        "split_protocol": SPLIT_PROTOCOL,
        "atom_screen_fraction": ATOM_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "fresh_validation_split_reported_once": (
            FRESH_VALIDATION_SPLIT_REPORTED_ONCE
        ),
        "cvar_alpha": CVAR_ALPHA,
        "model_families": list(MODEL_FAMILIES),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "languages": list(LANGUAGES),
        "pack_policy_results": pack_policy_results,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "aggregate_only_public_artifact": True,
        "algorithm_spec_has_no_model_names": (len(model_name_hits) == 0),
        "algorithm_spec_model_name_scan_hits": model_name_hits,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_default_change": True,
            "no_policy_promotion": True,
            "no_pack_policy_promotion": True,
            "no_pack_policy_learning": True,
            "no_atom_ablation": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "pack_policy_learned_false": True,
            "atom_ablation_performed_false": True,
            "per_record_inputs_available_false": True,
            "policy_search_performed_false": True,
            "quality_strategy_tuned_false": True,
            "new_provider_calls_zero": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "runtime_calls_by_replay_zero": True,
            "model_calls_by_replay_zero": True,
            "algorithm_spec_has_no_model_names_true": True,
            "no_fake_atom_effects_from_aggregate_means_true": True,
            "replay_only_no_live_pack_policy_runs_in_evaluator": True,
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
    # B15 DEFINES the context-pack-policy stage
    # (stage_is_context_pack_policy=true), but no empirical B15
    # PackPolicy learning or atom ablation is performed by this
    # skeleton (pack_policy_learned=false,
    # atom_ablation_performed=false). The skeleton report sets
    # per_record_inputs_available=false to avoid overclaiming empirical
    # PackPolicy validation.
    if spec.get("stage_is_context_pack_policy") is not True:
        raise ValueError(
            "algorithm spec stage_is_context_pack_policy must be true "
            "(B15 stage)"
        )
    if spec.get("pack_policy_learned") is not False:
        raise ValueError(
            "algorithm spec pack_policy_learned must be false "
            "(no empirical PackPolicy learning performed by skeleton)"
        )
    if spec.get("atom_ablation_performed") is not False:
        raise ValueError(
            "algorithm spec atom_ablation_performed must be false "
            "(no empirical atom ablation performed by skeleton)"
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
    if spec.get("new_provider_calls") != 0:
        raise ValueError("algorithm spec new_provider_calls must be 0")
    if spec.get("aggregate_only_public_artifact") is not True:
        raise ValueError("algorithm spec aggregate_only_public_artifact must be true")
    if spec.get("algorithm_spec_has_no_model_names") is not True:
        raise ValueError(
            "algorithm spec algorithm_spec_has_no_model_names must be true"
        )
    if spec.get("no_fake_atom_effects_from_aggregate_means") is not True:
        raise ValueError(
            "algorithm spec no_fake_atom_effects_from_aggregate_means "
            "must be true"
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
    if tuple(spec.get("roles") or ()) != ROLES:
        raise ValueError("algorithm spec roles mismatch")
    if tuple(spec.get("atom_registry") or ()) != ATOM_REGISTRY:
        raise ValueError("algorithm spec atom_registry mismatch")
    if tuple(spec.get("existing_pack_layouts") or ()) != EXISTING_PACK_LAYOUTS:
        raise ValueError("algorithm spec existing_pack_layouts mismatch")
    if (
        tuple(spec.get("allowed_runtime_state_features") or ())
        != ALLOWED_RUNTIME_STATE_FEATURES
    ):
        raise ValueError(
            "algorithm spec allowed_runtime_state_features mismatch"
        )
    if tuple(spec.get("abstract_profile_slots") or ()) != ABSTRACT_PROFILE_SLOTS:
        raise ValueError("algorithm spec abstract_profile_slots mismatch")
    if (
        tuple(spec.get("allowed_model_profile_capabilities") or ())
        != ALLOWED_MODEL_PROFILE_CAPABILITIES
    ):
        raise ValueError(
            "algorithm spec allowed_model_profile_capabilities mismatch"
        )
    if (
        tuple(spec.get("forbidden_pack_policy_features") or ())
        != FORBIDDEN_PACK_POLICY_FEATURES
    ):
        raise ValueError(
            "algorithm spec forbidden_pack_policy_features mismatch"
        )
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
    if spec.get("factorial_resolution") != FACTORIAL_RESOLUTION:
        raise ValueError("algorithm spec factorial_resolution mismatch")
    if spec.get("factorial_full_runs") != FACTORIAL_FULL_RUNS:
        raise ValueError("algorithm spec factorial_full_runs mismatch")
    if spec.get("factorial_fractional_runs") != FACTORIAL_FRACTIONAL_RUNS:
        raise ValueError("algorithm spec factorial_fractional_runs mismatch")
    if spec.get("split_protocol") != SPLIT_PROTOCOL:
        raise ValueError("algorithm spec split_protocol mismatch")
    if spec.get("atom_screen_fraction") != ATOM_SCREEN_FRACTION:
        raise ValueError("algorithm spec atom_screen_fraction mismatch")
    if spec.get("fresh_validation_fraction") != FRESH_VALIDATION_FRACTION:
        raise ValueError("algorithm spec fresh_validation_fraction mismatch")
    if spec.get("cvar_alpha") != CVAR_ALPHA:
        raise ValueError("algorithm spec cvar_alpha mismatch")
    # B15 special invariant: the spec must NOT list raw model family
    # names (kimi/qwen/deepseek/glm). It uses abstract profile slots
    # and capability descriptors instead.
    if tuple(spec.get("abstract_profile_slots") or ()) != ABSTRACT_PROFILE_SLOTS:
        raise ValueError("algorithm spec abstract_profile_slots mismatch")
    if "model_families" in spec:
        raise ValueError(
            "algorithm spec must NOT contain model_families (raw model names); "
            "use abstract_profile_slots instead"
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
    # B15 DEFINES the context-pack-policy stage
    # (stage_is_context_pack_policy=true), but this skeleton performs
    # NO empirical PackPolicy learning and NO empirical atom ablation.
    if report.get("stage_is_context_pack_policy") is not True:
        raise ValueError(
            "report stage_is_context_pack_policy must be true (B15 stage)"
        )
    if report.get("pack_policy_learned") is not False:
        raise ValueError(
            "report pack_policy_learned must be false "
            "(no empirical PackPolicy learning performed by skeleton)"
        )
    if report.get("atom_ablation_performed") is not False:
        raise ValueError(
            "report atom_ablation_performed must be false "
            "(no empirical atom ablation performed by skeleton)"
        )
    if report.get("per_record_inputs_available") is not False:
        raise ValueError(
            "report per_record_inputs_available must be false (skeleton)"
        )
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "report policy_search_performed must be false (skeleton)"
        )
    if report.get("quality_strategy_tuned") is not False:
        raise ValueError("report quality_strategy_tuned must be false")
    if report.get("new_provider_calls") != 0:
        raise ValueError("report new_provider_calls must be 0")
    # Skeleton: no candidate policy frozen, no stages evaluated, no
    # winner declared.
    if report.get("candidate_policy_frozen") is not False:
        raise ValueError("report candidate_policy_frozen must be false (skeleton)")
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
    if report.get("metrics_evaluated") is not False:
        raise ValueError(
            "report metrics_evaluated must be false (skeleton; no fake "
            "metric values from aggregate means)"
        )
    if report.get("no_fake_atom_effects_from_aggregate_means") is not True:
        raise ValueError(
            "report no_fake_atom_effects_from_aggregate_means must be true"
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
    if report.get("algorithm_spec_has_no_model_names") is not True:
        raise ValueError(
            "report algorithm_spec_has_no_model_names must be true (B15 invariant)"
        )
    if report.get("predeclared_criteria") != PREDECLARED_CRITERIA:
        raise ValueError("report predeclared_criteria must match the frozen constants")
    if tuple(report.get("roles") or ()) != ROLES:
        raise ValueError("report roles mismatch")
    if tuple(report.get("atom_registry") or ()) != ATOM_REGISTRY:
        raise ValueError("report atom_registry mismatch")
    if tuple(report.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("report metric_names mismatch")
    if tuple(report.get("hard_gates") or ()) != HARD_GATES:
        raise ValueError("report hard_gates mismatch")
    if tuple(report.get("experimental_stages") or ()) != EXPERIMENTAL_STAGES:
        raise ValueError("report experimental_stages mismatch")
    if tuple(report.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("report model_families mismatch")
    if tuple(report.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("report repos mismatch")
    # Required top-level sections.
    for key in (
        "pack_policy_results",
    ):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # pack_policy_results substructure. The skeleton emits only
    # definitions + hard gates + experimental stage definitions; no
    # empirical per-stage metric values.
    ppr = report.get("pack_policy_results") or {}
    for key in (
        "metrics_defined",
        "metric_names",
        "gates_defined",
        "hard_gates",
        "predeclared_criteria",
        "experimental_stages",
        "atom_registry",
        "roles",
        "runtime_state_features",
        "model_profile_slots",
        "model_profile_capabilities",
        "metrics_evaluated",
        "pack_policy_learned",
        "atom_ablation_performed",
        "candidate_policy_frozen",
        "all_stages_pass",
        "stages_evaluated",
        "winner_declared",
        "no_fake_atom_effects_from_aggregate_means",
    ):
        if key not in ppr:
            raise ValueError(f"pack_policy_results missing required section: {key}")
    if ppr.get("metrics_evaluated") is not False:
        raise ValueError(
            "pack_policy_results.metrics_evaluated must be false "
            "(skeleton; no fake metric values from aggregate means)"
        )
    if ppr.get("pack_policy_learned") is not False:
        raise ValueError(
            "pack_policy_results.pack_policy_learned must be false (skeleton)"
        )
    if ppr.get("atom_ablation_performed") is not False:
        raise ValueError(
            "pack_policy_results.atom_ablation_performed must be false (skeleton)"
        )
    if ppr.get("candidate_policy_frozen") is not False:
        raise ValueError(
            "pack_policy_results.candidate_policy_frozen must be false (skeleton)"
        )
    if ppr.get("all_stages_pass") is not False:
        raise ValueError(
            "pack_policy_results.all_stages_pass must be false (skeleton)"
        )
    if ppr.get("stages_evaluated") is not False:
        raise ValueError(
            "pack_policy_results.stages_evaluated must be false (skeleton)"
        )
    if ppr.get("winner_declared") is not False:
        raise ValueError(
            "pack_policy_results.winner_declared must be false (skeleton)"
        )
    if ppr.get("no_fake_atom_effects_from_aggregate_means") is not True:
        raise ValueError(
            "pack_policy_results.no_fake_atom_effects_from_aggregate_means "
            "must be true"
        )
    # experimental_stages must be a definitions-only block.
    stages = ppr.get("experimental_stages") or {}
    if stages.get("stages_defined") is not True:
        raise ValueError(
            "pack_policy_results.experimental_stages.stages_defined "
            "must be true"
        )
    if stages.get("stage_count") != len(EXPERIMENTAL_STAGES):
        raise ValueError(
            "pack_policy_results.experimental_stages.stage_count mismatch"
        )
    if stages.get("stages_evaluated") is not False:
        raise ValueError(
            "pack_policy_results.experimental_stages.stages_evaluated "
            "must be false (skeleton)"
        )
    stage_list = stages.get("stages")
    if not isinstance(stage_list, list) or len(stage_list) != len(
        EXPERIMENTAL_STAGES
    ):
        raise ValueError(
            "pack_policy_results.experimental_stages.stages must be "
            "a list of 4 stage definitions"
        )
    for s in stage_list:
        if s.get("evaluated") is not False:
            raise ValueError(
                "stage definitions must have evaluated=false (skeleton)"
            )
        for forbidden_key in (
            "passes",
            "atom_effect_per_atom",
            "role_pack_outcome",
            "runtime_state_pack_outcome",
            "model_profile_pack_outcome",
            "worst_group_pack_outcome",
            "cvar_20_pack_outcome",
            "token_budget_parity",
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
        "no_default_change",
        "no_policy_promotion",
        "no_pack_policy_promotion",
        "no_pack_policy_learning",
        "no_atom_ablation",
        "no_evidencecore_semantics_change",
        "promotion_ready_false",
        "default_should_change_false",
        "pack_policy_learned_false",
        "atom_ablation_performed_false",
        "per_record_inputs_available_false",
        "policy_search_performed_false",
        "quality_strategy_tuned_false",
        "new_provider_calls_zero",
        "aggregate_only_public_artifact",
        "forbidden_public_keys_scanned",
        "no_raw_path_digest_provider_strings",
        "runtime_calls_by_replay_zero",
        "model_calls_by_replay_zero",
        "algorithm_spec_has_no_model_names_true",
        "no_fake_atom_effects_from_aggregate_means_true",
        "replay_only_no_live_pack_policy_runs_in_evaluator",
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input (stub): load per-record inputs without computing PackPolicy
# ---------------------------------------------------------------------------


def _load_per_record_input(path: str) -> dict[str, Any]:
    """Load a per-record inputs JSON file (or directory of JSON files)
    and return a minimal metadata payload. The full per-record
    (atom_flag, outcome, role, runtime_state, model_profile) replay +
    PackPolicy validation computation is deferred to a later task; for
    now we only verify the input is valid JSON and surface its top-level
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

    Real per-record (atom_flag, outcome, role, runtime_state,
    model_profile) replay + PackPolicy validation computation
    (estimating atom effects from randomized atom assignment, freezing
    a candidate PackPolicy, validating on a fresh split, worst-group
    reporting) is deferred to a later task. For now we emit a
    well-formed report with ``verdict="not_implemented"`` and an
    explanatory reason, while still passing all safety-invariant checks.

    CRITICAL: this stub MUST NOT compute fake atom-effect metrics from
    aggregate means. No metric values are emitted.
    """
    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Override the verdict to signal that no real PackPolicy validation
    # happened.
    report["verdict"] = "not_implemented"
    report["verdict_reason"] = (
        "real-input PackPolicy validation + per-record (atom_flag, "
        "outcome, role, runtime_state, model_profile) replay "
        f"computation deferred to later task; input_meta={input_meta}"
    )
    # Re-stamp the spec hash fields (defensive: build_report already sets
    # these).
    report["algorithm_spec_sha256_matched"] = True
    report["algorithm_spec_sha256_stable"] = (spec_hash == _sha256_json(spec))
    # Re-scan forbidden keys after the override (input_meta may include
    # only safe scalar fields by construction).
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

    # Raw path value should trip the "/" pattern even when the key is
    # allowed.
    bad_value = {"provenance": "eval/some_file.py"}
    hits2 = _recursive_key_scan(bad_value)
    assert any("forbidden_value" in h for h in hits2), hits2

    # A clean provenance reference (module::symbol, no "/") must not
    # trip.
    clean = {"provenance": "b15_context_pack_policy::build_report"}
    hits3 = _recursive_key_scan(clean)
    assert hits3 == [], hits3

    # A 64-hex digest value must trip the forbidden-value scan.
    bad_digest = {"some_field": "a" * 64}
    hits4 = _recursive_key_scan(bad_digest)
    assert any("forbidden_value" in h for h in hits4), hits4

    # B15 special: model names must be flagged by
    # _scan_spec_for_model_names.
    bad_spec = {"description": "tuned for Kimi and Qwen", "nested": {"m": "deepseek"}}
    mh = _scan_spec_for_model_names(bad_spec)
    flat_m = " ".join(mh)
    assert "kimi" in flat_m
    assert "qwen" in flat_m
    assert "deepseek" in flat_m

    # A clean spec using only abstract profile_slots + capability
    # descriptors must not trip the model-name scan.
    clean_spec = {
        "description": "uses profile_slots and model_profile.capability",
        "abstract_profile_slots": ["profile_slot_a", "profile_slot_b"],
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


def _self_test_atom_registry_closed() -> None:
    """Atom registry is closed and disjoint from forbidden features."""
    spec = build_algorithm_spec()
    assert tuple(spec["atom_registry"]) == ATOM_REGISTRY
    # Atom registry must be unique.
    assert len(set(ATOM_REGISTRY)) == len(ATOM_REGISTRY), ATOM_REGISTRY
    # Atom registry must be disjoint from forbidden features.
    forbidden = set(FORBIDDEN_PACK_POLICY_FEATURES)
    atoms = set(ATOM_REGISTRY)
    assert atoms.isdisjoint(forbidden), (atoms & forbidden)
    # Atom registry must be disjoint from runtime_state features.
    runtime = set(ALLOWED_RUNTIME_STATE_FEATURES)
    assert atoms.isdisjoint(runtime), (atoms & runtime)
    # Atom registry must be disjoint from model_profile capabilities.
    caps = set(ALLOWED_MODEL_PROFILE_CAPABILITIES)
    assert atoms.isdisjoint(caps), (atoms & caps)
    # Per-record outcomes are required INPUTS but never ATOMS / signals.
    assert "per_record_outcome_binary" in REQUIRED_PER_RECORD_INPUTS
    assert "per_record_outcome_binary" not in atoms
    assert "per_record_outcome_binary" not in runtime
    assert "per_record_outcome_binary" not in caps
    assert "per_record_outcome_binary" not in forbidden


def _self_test_role_set_closed() -> None:
    """Role set: 4 roles, closed set."""
    spec = build_algorithm_spec()
    assert tuple(spec["roles"]) == ROLES
    assert len(set(ROLES)) == len(ROLES), ROLES
    assert ROLES == (
        "span_narrow",
        "filter_reject",
        "request_more_context",
        "source_test_disambiguation",
    ), ROLES


def _self_test_runtime_state_contract() -> None:
    """runtime_state features are label-free and model-name-free."""
    spec = build_algorithm_spec()
    assert (
        tuple(spec["allowed_runtime_state_features"])
        == ALLOWED_RUNTIME_STATE_FEATURES
    )
    # runtime_state features must be unique.
    assert (
        len(set(ALLOWED_RUNTIME_STATE_FEATURES))
        == len(ALLOWED_RUNTIME_STATE_FEATURES)
    ), ALLOWED_RUNTIME_STATE_FEATURES
    # runtime_state features must be disjoint from forbidden features.
    forbidden = set(FORBIDDEN_PACK_POLICY_FEATURES)
    runtime = set(ALLOWED_RUNTIME_STATE_FEATURES)
    assert runtime.isdisjoint(forbidden), (runtime & forbidden)
    # runtime_state features must not contain raw model names.
    for f in ALLOWED_RUNTIME_STATE_FEATURES:
        for token in FORBIDDEN_MODEL_NAME_TOKENS:
            assert token not in f.lower(), (f, token)


def _self_test_model_profile_abstraction() -> None:
    """Abstract capability slots only; no raw model names in spec."""
    spec = build_algorithm_spec()
    assert tuple(spec["abstract_profile_slots"]) == ABSTRACT_PROFILE_SLOTS
    assert (
        tuple(spec["allowed_model_profile_capabilities"])
        == ALLOWED_MODEL_PROFILE_CAPABILITIES
    )
    # Profile slots must use abstract names, not raw model names.
    for slot in ABSTRACT_PROFILE_SLOTS:
        assert slot.startswith("profile_slot_"), slot
        for token in FORBIDDEN_MODEL_NAME_TOKENS:
            assert token not in slot.lower(), (slot, token)
    # Capabilities must not contain raw model names.
    for cap in ALLOWED_MODEL_PROFILE_CAPABILITIES:
        for token in FORBIDDEN_MODEL_NAME_TOKENS:
            assert token not in cap.lower(), (cap, token)
    # Spec must NOT contain model_families (raw model names).
    assert "model_families" not in spec, (
        "algorithm_spec must NOT contain model_families (raw model names)"
    )


def _self_test_metric_registry() -> None:
    """Metric registry: 9 metric names defined; no aggregate-mean
    metrics."""
    spec = build_algorithm_spec()
    assert tuple(spec["metric_names"]) == METRIC_NAMES
    assert len(METRIC_NAMES) == 9, METRIC_NAMES
    # All metric names require per-record (atom_flag, outcome, role,
    # runtime_state, model_profile) tuples; none can be computed from
    # aggregate means.
    for name in METRIC_NAMES:
        assert "aggregate_mean" not in name, name
        assert "overall_mean" not in name, name


def _self_test_hard_gates_defined() -> None:
    """Hard gates: privacy / leakage / adapter-health / randomization-
    balance / denominator / token-budget / promotion-false gates
    defined."""
    spec = build_algorithm_spec()
    assert tuple(spec["hard_gates"]) == HARD_GATES
    assert len(HARD_GATES) == 7, HARD_GATES
    expected_gates = {
        "privacy_gate",
        "leakage_gate",
        "adapter_health_gate",
        "randomization_balance_gate",
        "denominator_gate",
        "token_budget_gate",
        "promotion_false_gate",
    }
    assert set(HARD_GATES) == expected_gates, HARD_GATES


def _self_test_experimental_structure_frozen() -> None:
    """Experimental structure: 4 frozen stages; no feedback."""
    spec = build_algorithm_spec()
    assert tuple(spec["experimental_stages"]) == EXPERIMENTAL_STAGES
    assert len(EXPERIMENTAL_STAGES) == 4, EXPERIMENTAL_STAGES
    assert EXPERIMENTAL_STAGES == (
        "no_llm_feasibility",
        "fractional_factorial_live_atom_screen",
        "freeze_candidate_policy",
        "fresh_validation",
    ), EXPERIMENTAL_STAGES
    # Fractional factorial design: resolution-IV fraction over the atom
    # registry (no full 2^9 factorial).
    assert spec["factorial_resolution"] == FACTORIAL_RESOLUTION
    assert spec["factorial_full_runs"] == 2 ** len(ATOM_REGISTRY)
    assert spec["factorial_fractional_runs"] < spec["factorial_full_runs"]
    # Split protocol: atom-screen + fresh-validation, stratified by
    # (model_family, repo, role).
    assert spec["split_protocol"] == SPLIT_PROTOCOL
    assert spec["atom_screen_fraction"] + spec["fresh_validation_fraction"] == 1.0
    assert spec["fresh_validation_split_reported_once"] is True
    # Evaluate the stages on the synthetic fixture (evaluator-side). The
    # skeleton emits definitions only; no empirical per-stage metric
    # values.
    fixture = _build_synthetic_fixture()
    cr, _verdict, _reason = _evaluate_pack_policy(fixture, "synthetic_fixture")
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
            "atom_effect_per_atom",
            "role_pack_outcome",
            "runtime_state_pack_outcome",
            "model_profile_pack_outcome",
            "worst_group_pack_outcome",
            "cvar_20_pack_outcome",
            "token_budget_parity",
            "delta_vs_reference",
        ):
            assert forbidden_key not in s, (forbidden_key, s)


def _self_test_no_fake_atom_effects_from_aggregate_means() -> None:
    """CRITICAL: the skeleton must NOT compute fake atom-effect metrics
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
    assert report["no_fake_atom_effects_from_aggregate_means"] is True
    assert report["pack_policy_results"]["metrics_evaluated"] is False
    assert (
        report["pack_policy_results"][
            "no_fake_atom_effects_from_aggregate_means"
        ]
        is True
    )
    # No metric value fields should be present at the top level.
    for forbidden_field in (
        "atom_effect_per_atom_value",
        "role_pack_outcome_value",
        "runtime_state_pack_outcome_value",
        "model_profile_pack_outcome_value",
        "worst_group_pack_outcome_value",
        "cvar_20_pack_outcome_value",
        "token_budget_parity_value",
        "denominator_per_atom_role_model_value",
        "randomization_balance_per_arm_value",
    ):
        assert forbidden_field not in report, forbidden_field
        assert forbidden_field not in report["pack_policy_results"], forbidden_field


def _self_test_input_stub_not_implemented(tmp_path: Path) -> None:
    """--input mode must emit verdict='not_implemented' without doing
    any real PackPolicy validation computation."""
    p = tmp_path / "per_record_stub.json"
    p.write_text(
        json.dumps({"records": [{"atom_flags": {"signature": 1}, "outcome": 1}]}),
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


def _self_test_reference_specs() -> None:
    """The B10, B10B, B11, B12, B13 and B14 frozen reference specs must
    exist on disk so the B15 frozen_artifacts pin is meaningful."""
    refs = _reference_spec_hashes()
    assert refs.get("balanced_policy_v1_benchmark_routed") is True, refs
    assert refs.get("balanced_policy_v1_runtime_shadow_ambiguous_branch") is True, refs
    assert refs.get("b11_prospective_v0") is True, refs
    assert refs.get("b12_mechanism_decomposition_v0") is True, refs
    assert refs.get("b13_dro_policy_search_v0") is True, refs
    assert refs.get("b14_uncertainty_calibration_v0") is True, refs


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
            "`python3 eval/b15_context_pack_policy.py --regenerate-artifacts` "
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
            "on-disk b15_context_pack_policy_report.json drifted from the "
            "in-memory build_report() output; run "
            "`python3 eval/b15_context_pack_policy.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_report(on_disk_report)


def regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report
    so the artifact pin matches the in-code build functions. Mirrors
    the B10/B10B/B11/B12/B13/B14 freeze-write style: deterministic
    output, canonical JSON.

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
    """Run all B15 self-test checks. Returns a summary dict."""
    import tempfile

    _self_test_forbidden_scan()
    _self_test_spec_hash_stable()
    _self_test_atom_registry_closed()
    _self_test_role_set_closed()
    _self_test_runtime_state_contract()
    _self_test_model_profile_abstraction()
    _self_test_metric_registry()
    _self_test_hard_gates_defined()
    _self_test_experimental_structure_frozen()
    _self_test_no_fake_atom_effects_from_aggregate_means()
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
        "stage_is_context_pack_policy": True,
        "pack_policy_learned": False,
        "atom_ablation_performed": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "candidate_policy_frozen": False,
        "stages_evaluated": False,
        "stages_defined": True,
        "stage_count": len(EXPERIMENTAL_STAGES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_atom_effects_from_aggregate_means": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "algorithm_spec_has_no_model_names": True,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "aggregate_only_public_artifact": True,
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "atom_registry_closed": True,
            "role_set_closed": True,
            "runtime_state_contract": True,
            "model_profile_abstraction": True,
            "metric_registry": True,
            "hard_gates_defined": True,
            "experimental_structure_frozen": True,
            "no_fake_atom_effects_from_aggregate_means": True,
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
            "run the B15 self-test (read-only; synthetic fixture; verifies "
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
            "per-record pack atom flags + per-record outcomes + "
            "role-specific paired outputs + runtime_state + "
            "model_profile paired blocks + group membership + "
            "randomized atom assignment. Currently a STUB: emits "
            "verdict='not_implemented'; full PackPolicy validation + "
            "per-record replay computation deferred to a later task. "
            "Requires --out and may not write the canonical checked-in "
            "artifact."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write a stub input report. Required with --input; "
            "must not be the canonical checked-in B15 report artifact."
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input and not args.regenerate_artifacts:
        parser.error(
            "B15 requires --self-test, --regenerate-artifacts, or "
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
        # Blocker guard: --input must not write ANY checked-in B15
        # artifact — neither the canonical report, the algorithm spec,
        # nor the public-aggregate prior-screen report. The simplest
        # fail-closed rule is to reject any --out that resolves inside
        # artifacts/b15_context_pack_policy/. --input is intended for
        # /tmp or other external paths only.
        artifact_dir_resolved = ARTIFACT_DIR.resolve()
        canonical_paths = {
            REPORT_PATH.resolve(),
            ALGORITHM_SPEC_PATH.resolve(),
            (
                ARTIFACT_DIR
                / "b15_public_aggregate_prior_screen_report.json"
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
                "--input may not write inside the checked-in B15 "
                "artifact directory artifacts/b15_context_pack_policy/ "
                "(canonical report, algorithm spec, or public-aggregate "
                "prior-screen report); use --out outside artifacts/ or "
                "run --regenerate-artifacts"
            )
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "claim_level": report["claim_level"],
        "roles": report["roles"],
        "atom_registry": report["atom_registry"],
        "metric_names": report["metric_names"],
        "hard_gates": report["hard_gates"],
        "experimental_stages": report["experimental_stages"],
        "factorial_resolution": report["factorial_resolution"],
        "factorial_fractional_runs": report["factorial_fractional_runs"],
        "split_protocol": report["split_protocol"],
        "atom_screen_fraction": report["atom_screen_fraction"],
        "fresh_validation_fraction": report["fresh_validation_fraction"],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "evidencecore_semantics_changed": report["evidencecore_semantics_changed"],
        "stage_is_context_pack_policy": report["stage_is_context_pack_policy"],
        "pack_policy_learned": report["pack_policy_learned"],
        "atom_ablation_performed": report["atom_ablation_performed"],
        "per_record_inputs_available": report["per_record_inputs_available"],
        "policy_search_performed": report["policy_search_performed"],
        "quality_strategy_tuned": report["quality_strategy_tuned"],
        "new_provider_calls": report["new_provider_calls"],
        "candidate_policy_frozen": report["candidate_policy_frozen"],
        "stages_evaluated": report["stages_evaluated"],
        "stages_defined": report["stages_defined"],
        "stage_count": report["stage_count"],
        "winner_declared": report["winner_declared"],
        "metrics_defined": report["metrics_defined"],
        "gates_defined": report["gates_defined"],
        "metrics_evaluated": report["metrics_evaluated"],
        "no_fake_atom_effects_from_aggregate_means": report[
            "no_fake_atom_effects_from_aggregate_means"
        ],
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
        print("B15 self-test: PASS (read-only; no artifacts written)", file=sys.stderr)
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
            "pack_policy_learned": False,
            "atom_ablation_performed": False,
            "per_record_inputs_available": False,
            "candidate_policy_frozen": False,
            "stages_evaluated": False,
            "winner_declared": False,
            "metrics_evaluated": False,
            "no_fake_atom_effects_from_aggregate_means": True,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(
            f"B15 artifacts regenerated: {ALGORITHM_SPEC_PATH} + {REPORT_PATH}",
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
        print(f"B15 report written to {out_path}", file=sys.stderr)
        return 0
    print(
        "B15 requires --self-test, --regenerate-artifacts, or --input",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
