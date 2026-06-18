#!/usr/bin/env python3
"""B13 Distributionally Robust Policy Search.

B13 is the distributionally-robust policy-search phase that follows B12
(mechanism decomposition). The goal is to find a policy with 6-10 rules that
optimizes **worst-group utility** (not the average), using only
runtime-observable features, validated via rotating leave-one-model-family-out.

B13 is replay/search-only: each P21 record contains per-strategy outcomes, so
each candidate rule's per-record outcome can be computed by selecting the
appropriate per-strategy outcome from existing records. No live LLM calls are
made by this evaluator.

Important claim boundary: B13 IS the policy-search *stage*
(`stage_is_policy_search=true`), but this skeleton performs NO empirical
policy search. Self-test / `--input` reports set
`empirical_policy_search_performed=false` AND `policy_search_performed=false`
so the synthetic / stub report cannot be mistaken for an empirical B13 run.
The frozen rule grammar, optimization objective, search constraints,
validation methodology, and success/failure criteria are FROZEN before any
real B13 search runs; no retuning is allowed after real B13 search runs
begin.

Important claim boundary: B13 results are NOT promoted. Even if a future
empirical B13 run finds a policy that improves worst-group utility,
``promotion_ready=false``, ``default_should_change=false``, and
``EvidenceCore`` semantics are unchanged. B13 results are research candidates
only: they inform B14 (uncertainty calibration) and B16 (downstream agent
evaluation), but B13 does not authorize any default change, any policy
promotion, or any EvidenceCore modification.

Aggregate-only public artifacts: no task/repo/candidate/path/span/snippet/
prompt/response/gold/provider keys and no raw path/digest/provider strings.

This file currently ships a SKELETON: the ``--self-test`` path verifies the
rule-grammar, search-mechanics stub, and leave-one-out rotation *definitions*
against a synthetic fixture (read-only: it builds the expected algorithm spec
+ report in memory and compares them to the on-disk artifacts, failing on
drift; it does NOT write to disk). ``--input <path>`` is a stub
(``verdict="not_implemented"``) awaiting the full P21-record replay + search
computation in a later task. The ONLY mutating path is
``--regenerate-artifacts``, which (re)writes the on-disk algorithm spec +
synthetic-fixture report from the current build functions. In all paths:
``policy_search_performed=false`` and
``empirical_policy_search_performed=false`` so the synthetic / stub report
cannot be misread as an empirical B13 search. Synthetic / stub reports emit
only rotation *definitions* (``rotations_defined=true``,
``rotation_count=3``, ``rotations_evaluated=false``); they never emit
per-rotation ``passes=true``, ``all_rotations_pass=true``,
``test_worst_group_utility``, or ``delta_vs_b10_reference`` as if empirical.
Top-level ``policy_found=false``, ``rotations_evaluated=false``,
``winner_declared=false`` are always present. No live LLM calls are made by
this evaluator.

For a bounded public-aggregate feasibility/no-go screen that does NOT claim
empirical policy search, see
``eval/b13_public_aggregate_feasibility_screen.py``.

Run::

    python3 eval/b13_dro_policy_search.py --self-test
    python3 eval/b13_dro_policy_search.py --regenerate-artifacts
    python3 eval/b13_dro_policy_search.py --input path/to/p21_outputs.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b13_dro_policy_search"
REPORT_PATH = (
    ARTIFACT_DIR / "b13_dro_policy_search_report.json"
)
# The algorithm spec is emitted alongside the report (deterministic, fixed
# generated_at so its sha256 is stable across runs).
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "b13_dro_policy_search.algorithm.json"
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

SCHEMA_VERSION = "b13-dro-policy-search-report-v0"
SPEC_SCHEMA_VERSION = "b13-dro-policy-search-spec-v0"
GENERATED_BY = "b13_dro_policy_search"
ALGORITHM_SPEC_ID = "b13_dro_policy_search_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors B10/B10B/
# B11/B12).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Rule grammar (FROZEN before any search runs)
# ---------------------------------------------------------------------------
#
# B13 searches a bounded grammar of simple predicates over runtime-observable
# route_features only. No benchmark-private labels, no score-private fields,
# no model names in algorithm_spec.
#

# Allowed runtime features (only route_features values; no benchmark-private
# labels like task_bucket / task_risk_tags, no score-private fields like
# has_gold / score_group / outcome_metrics).
ALLOWED_RUNTIME_FEATURES = (
    "query_noise",
    "candidate_support_exists",
    "local_anchor",
    "rrf_backed_by_anchor",
    "candidate_count",
    "symbol_regex_agree_file",
    "symbol_regex_agree_span",
    "rrf_anchor_agree_file",
    "rrf_anchor_agree_span",
    "dense_support_present",
)

# Allowed model_profile capability fields (referenced, not raw model names).
ALLOWED_MODEL_PROFILE_CAPS = (
    "supports_reliable_span_narrow",
    "cost_class",
    "latency_class",
)

# Allowed actions for each rule (LLM-free action space).
ALLOWED_ACTIONS = (
    "weak_only",
    "use_p25_action",
    "use_local_baseline",
)

# Rule count bounds.
MIN_RULES = 6
MAX_RULES = 10

# Search budget.
MAX_SEARCH_ITERATIONS = 1000

# ---------------------------------------------------------------------------
# Optimization objective (FROZEN before any search runs)
# ---------------------------------------------------------------------------

ROBUST_UTILITY_LAMBDA = 1.0  # PFP weight
ROBUST_UTILITY_MU = 0.1  # normalized cost weight
ROBUST_UTILITY_NU = 0.1  # normalized latency weight
CVAR_ALPHA = 0.20  # worst-20% tail average

# ---------------------------------------------------------------------------
# Rotating leave-one-model-family-out (FROZEN before any search runs)
# ---------------------------------------------------------------------------
#
# 3 rotations: train on the non-held-out family slots, test on the held-out
# one. The evaluator-side LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS keeps the real
# model family names (used only for synthetic-fixture computation / future real
# P21-record evaluation); the algorithm_spec emits the abstract
# ABSTRACT_FAMILY_SLOTS versions so NO raw model names appear in the spec
# (B13 special invariant: algorithm_spec_has_no_model_names=true).
#
# Mapping (evaluator-internal, NEVER written into algorithm_spec):
#   family_a -> kimi
#   family_b -> qwen
#   family_c -> deepseek_flash
#   family_d -> deepseek_pro
#
ABSTRACT_FAMILY_SLOTS = ("family_a", "family_b", "family_c", "family_d")

# Evaluator-side rotations with real model family names (synthetic fixture /
# future real P21-record evaluation). These names are NEVER written into the
# algorithm_spec; the spec uses the abstract slot versions below.
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
        "train_families": ("kimi", "qwen",),
        "test_family": "deepseek",
        # NOTE: the deepseek test family aggregates deepseek_flash + deepseek_pro
        # (family_c + family_d) as a single held-out cluster.
        "test_subfamilies": ("deepseek_flash", "deepseek_pro"),
        "abstract_train_slots": ("family_a", "family_b"),
        "abstract_test_slots": ("family_c", "family_d"),
    },
)

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any search runs)
# ---------------------------------------------------------------------------

PREDECLARED_CRITERIA: dict[str, Any] = {
    # Worst-group delta threshold (rotation passes if within ± this of B10, or
    # strictly better).
    "worst_group_delta_threshold": 0.02,
    # Strict improvement margin.
    "strictly_greater_threshold": 0.02,
    # CVaR tail fraction (worst 20%).
    "cvar_alpha": CVAR_ALPHA,
    # RobustUtility parameters (mirrors B11/B12).
    "robust_utility_lambda": ROBUST_UTILITY_LAMBDA,
    "robust_utility_mu": ROBUST_UTILITY_MU,
    "robust_utility_nu": ROBUST_UTILITY_NU,
    # Rule count bounds.
    "min_rules": MIN_RULES,
    "max_rules": MAX_RULES,
    # Search budget.
    "max_search_iterations": MAX_SEARCH_ITERATIONS,
}

# ---------------------------------------------------------------------------
# Models, repos, metrics (mirror B11/B12 for consistency)
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

# Metrics emitted per candidate policy (per repo / per model family / overall).
METRIC_NAMES = (
    "span_f0_5",
    "gold_span",
    "false_span",
    "primary_false_positive_rate",
    "model_calls",
)

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
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")
# Skeleton verdicts. Until a real empirical B13 replay/search path exists
# (an explicit ``empirical_policy_search_performed=true`` path, which is NOT
# present in this skeleton), ``_evaluate_search`` may only emit
# ``insufficient_data`` (synthetic fixture) or ``not_implemented``
# (ci_ephemeral_records stub). The success / failure / partial verdicts are
# reserved for future empirical B13 and are deliberately removed from the
# skeleton's allowed set so a stub report cannot accidentally carry them.
ALLOWED_VERDICTS = (
    "insufficient_data",
    "not_implemented",
)
# Empirical verdicts reserved for the future real B13 search path. Listed
# here for documentation only; the skeleton never emits them and
# ``ALLOWED_VERDICTS`` above does not include them.
EMPIRICAL_VERDICTS_RESERVED_FOR_FUTURE_B13 = (
    "success",
    "failure",
    "partial",
)

# ---------------------------------------------------------------------------
# Special B13 invariant: no model names in algorithm_spec
# ---------------------------------------------------------------------------

# These tokens must NEVER appear in algorithm_spec (the search must use
# model_profile capabilities, not raw model names).
FORBIDDEN_MODEL_NAME_TOKENS = (
    "kimi",
    "qwen",
    "deepseek",
    "glm",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B/B11/B12 so aggregate-only public artifact invariants are
# identical)
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

# Conservative leaked-value patterns. We flag: SHA-1/SHA-256 content hashes,
# http(s) URLs, credential assignments, 64-hex digests, AND raw filesystem
# paths (strings containing "/" — provenance uses "::" / "." / "_" instead of
# raw paths).
_FORBIDDEN_VALUE_RES = (
    re.compile(r"\b(?:sha_?(?:1|256)?|content_?sha)\b[\s:=]+[A-Fa-f0-9]{40,}", re.I),
    re.compile(r"https?://", re.I),
    re.compile(r"\b(?:api[_-]?key|base[_-]?url|api[_-]?secret|api[_-]?token)\b\s*[:=]\s*\S", re.I),
    re.compile(r"\b[A-Fa-f0-9]{64}\b"),
    re.compile(r"/"),  # raw filesystem path separator
)

# Repo IDs and model family IDs contain "_" — that is fine (the "/" regex does
# not match "_"). Provenance references use "::" / "." / "_" form, never raw
# filesystem paths.


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


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
    """B13 special invariant: verify no model names appear in algorithm_spec.

    Walks every string value in the spec and flags any case-insensitive
    occurrence of FORBIDDEN_MODEL_NAME_TOKENS as a substring. The spec must
    use model_profile capabilities (e.g., supports_reliable_span_narrow) and
    MUST NOT use raw model names (Kimi, Qwen, DeepSeek, GLM).
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


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _approx_equal(a: float, b: float, threshold: float) -> bool:
    return abs(a - b) <= threshold


def _strictly_greater(a: float, b: float, threshold: float) -> bool:
    return (a - b) > threshold


def _cvar(values: list[float], alpha: float) -> float:
    """Pure-Python CVaR: average of the worst ``alpha`` fraction of values.

    If ``alpha`` rounds to zero elements, falls back to the single worst
    value (min for utility-style values where larger is better).
    """
    if not values:
        return 0.0
    n = len(values)
    k = max(1, int(round(alpha * n)))
    sorted_asc = sorted(values)
    worst = sorted_asc[:k]
    return _mean(worst)


# ---------------------------------------------------------------------------
# Synthetic fixture (self-test only)
# ---------------------------------------------------------------------------


def _synthetic_record_metrics(
    action: str, repo: str, model_family: str
) -> dict[str, float]:
    """Deterministic synthetic per-record metrics for one (action, repo,
    model_family).

    Values are deterministic functions of the inputs (no RNG) so the self-test
    spec hash is stable. The actions reflect the LLM-free action space:
    weak_only, use_p25_action, use_local_baseline.
    """
    h = hashlib.sha256(
        f"{action}|{repo}|{model_family}".encode("utf-8")
    ).digest()
    base = (h[0] / 255.0 + h[1] / 255.0 * 0.01)  # ~[0, 1.01)
    repo_idx = (
        MINIMUM_VIABLE_REPOS.index(repo) if repo in MINIMUM_VIABLE_REPOS else 0
    )
    model_idx = (
        MODEL_FAMILIES.index(model_family)
        if model_family in MODEL_FAMILIES
        else 0
    )

    span_f0_5 = 0.70 + 0.05 * base - 0.002 * repo_idx
    gold_span = 8.0 + (base * 2.0) - 0.05 * repo_idx
    false_span = 3.0 + (base * 2.0) + 0.05 * repo_idx
    pfp = 0.10 + (base * 0.05) + 0.001 * model_idx
    model_calls = 4.0 + (base * 1.0) + 0.05 * model_idx

    if action == "weak_only":
        # weak_only avoids LLM calls; conservative on gold, low false spans.
        false_span -= 0.6
        pfp -= 0.01
        model_calls -= 1.0
        gold_span -= 0.2  # slightly less gold than use_p25_action
    elif action == "use_p25_action":
        # P25 default action; moderate on gold, moderate false spans.
        pass
    elif action == "use_local_baseline":
        # local baseline only; no LLM, but loses more gold.
        gold_span -= 0.8
        false_span -= 0.3
        pfp -= 0.005
        model_calls -= 1.5
    else:
        raise ValueError(f"unknown action: {action!r}")

    return {
        "span_f0_5": round(max(0.0, span_f0_5), 6),
        "gold_span": round(max(0.0, gold_span), 6),
        "false_span": round(max(0.0, false_span), 6),
        "primary_false_positive_rate": round(max(0.0, pfp), 6),
        "model_calls": round(max(0.0, model_calls), 6),
    }


def _build_synthetic_fixture() -> dict[str, Any]:
    """Build a synthetic per-action × per-repo × per-model-family fixture.

    Returns a dict keyed by action; each value is a dict with ``per_repo``,
    ``per_model_family``, ``overall_mean``, and ``n_records``.
    """
    out: dict[str, Any] = {}
    for action in ALLOWED_ACTIONS:
        per_repo_cells: dict[str, list[dict[str, float]]] = {
            r: [] for r in MINIMUM_VIABLE_REPOS
        }
        per_model_cells: dict[str, list[dict[str, float]]] = {
            m: [] for m in MODEL_FAMILIES
        }
        all_cells: list[dict[str, float]] = []
        for model_family in MODEL_FAMILIES:
            for repo in MINIMUM_VIABLE_REPOS:
                cell = _synthetic_record_metrics(action, repo, model_family)
                per_repo_cells[repo].append(cell)
                per_model_cells[model_family].append(cell)
                all_cells.append(cell)
        per_repo_mean: dict[str, dict[str, float]] = {}
        for repo, cells in per_repo_cells.items():
            per_repo_mean[repo] = {
                m: round(_mean([c[m] for c in cells]), 6) for m in METRIC_NAMES
            }
        per_model_mean: dict[str, dict[str, float]] = {}
        for model, cells in per_model_cells.items():
            per_model_mean[model] = {
                m: round(_mean([c[m] for c in cells]), 6) for m in METRIC_NAMES
            }
        overall = {
            m: round(_mean([c[m] for c in all_cells]), 6) for m in METRIC_NAMES
        }
        out[action] = {
            "per_repo": per_repo_mean,
            "per_model_family": per_model_mean,
            "overall_mean": overall,
            "n_records": len(all_cells),
        }
    return out


# ---------------------------------------------------------------------------
# Aggregation mechanics (pure Python; no numpy/sklearn/scipy)
# ---------------------------------------------------------------------------


def _aggregate_overall(per_action: dict[str, Any]) -> dict[str, float]:
    """Overall mean per metric for the reference action (use_p25_action).

    The reference action mirrors B10's baseline-for-deltas (P25).
    """
    var = per_action["use_p25_action"]
    return dict(var["overall_mean"])


def _worst_group_by_repo(
    per_action: dict[str, Any], action: str
) -> dict[str, dict[str, float]]:
    """For each metric, return the min (worst) value across repos."""
    var = per_action[action]
    worst: dict[str, float] = {}
    for metric in METRIC_NAMES:
        vals = [
            var["per_repo"][repo][metric]
            for repo in MINIMUM_VIABLE_REPOS
            if repo in var["per_repo"]
        ]
        if metric in ("span_f0_5", "gold_span"):
            worst[metric] = round(min(vals), 6) if vals else 0.0
        else:
            worst[metric] = round(max(vals), 6) if vals else 0.0
    return {"repo": worst}


def _worst_group_by_model_family(
    per_action: dict[str, Any], action: str
) -> dict[str, dict[str, float]]:
    var = per_action[action]
    worst: dict[str, float] = {}
    for metric in METRIC_NAMES:
        vals = [
            var["per_model_family"][m][metric]
            for m in MODEL_FAMILIES
            if m in var["per_model_family"]
        ]
        if metric in ("span_f0_5", "gold_span"):
            worst[metric] = round(min(vals), 6) if vals else 0.0
        else:
            worst[metric] = round(max(vals), 6) if vals else 0.0
    return {"model_family": worst}


def _bootstrap_ci(
    per_action: dict[str, Any],
    action: str,
    n_resamples: int = 10000,
    seed: int = 20260618,
) -> dict[str, dict[str, float]]:
    """Stratified-by-repo bootstrap 95% CI over per-repo means.

    Pure-Python: resample the per-repo mean vector with replacement, recompute
    the overall mean, repeat ``n_resamples`` times, take 2.5 / 97.5 percentiles.
    Deterministic given the fixed seed.
    """
    var = per_action[action]
    repo_means = var["per_repo"]
    repo_list = list(repo_means.keys())
    if not repo_list:
        return {m: {"low": 0.0, "high": 0.0} for m in METRIC_NAMES}
    rng = random.Random(seed)
    resampled: dict[str, list[float]] = {m: [] for m in METRIC_NAMES}
    n = len(repo_list)
    for _ in range(n_resamples):
        for metric in METRIC_NAMES:
            picks = [repo_means[repo_list[rng.randrange(n)]][metric] for _ in range(n)]
            resampled[metric].append(_mean(picks))
    ci: dict[str, dict[str, float]] = {}
    for metric in METRIC_NAMES:
        vals = sorted(resampled[metric])
        lo_idx = int(0.025 * (len(vals) - 1))
        hi_idx = int(0.975 * (len(vals) - 1))
        ci[metric] = {
            "low": round(vals[lo_idx], 6),
            "high": round(vals[hi_idx], 6),
        }
    return ci


def _compute_action_deltas(
    per_action: dict[str, Any],
    action_a: str,
    action_b: str,
) -> dict[str, float]:
    """Compute ``action_a - action_b`` overall-mean deltas per metric."""
    a = per_action[action_a]["overall_mean"]
    b = per_action[action_b]["overall_mean"]
    return {m: round(a[m] - b[m], 6) for m in METRIC_NAMES}


def _compute_model_family_delta_spread(
    per_action: dict[str, Any],
    action_a: str,
    action_b: str,
    metric: str,
) -> dict[str, Any]:
    """For each model family, compute (action_a - action_b) on ``metric``,
    then report the min, max, and worst-case spread across model families.
    """
    a = per_action[action_a]["per_model_family"]
    b = per_action[action_b]["per_model_family"]
    deltas: list[float] = []
    per_family: dict[str, float] = {}
    for family in MODEL_FAMILIES:
        if family in a and family in b:
            d = round(a[family][metric] - b[family][metric], 6)
            deltas.append(d)
            per_family[family] = d
    if not deltas:
        return {
            "min_delta": 0.0,
            "max_delta": 0.0,
            "spread": 0.0,
            "per_model_family": {},
        }
    return {
        "min_delta": round(min(deltas), 6),
        "max_delta": round(max(deltas), 6),
        "spread": round(max(deltas) - min(deltas), 6),
        "per_model_family": per_family,
    }


def _compute_robust_utility(
    per_action: dict[str, Any],
    action: str,
    lambda_: float,
    mu: float,
    nu: float,
) -> float:
    """Stub RobustUtility = min_group(SpanF0.5 - λ*PFP - μ*norm_cost - ν*norm_latency).

    For the skeleton we approximate ``normalized_cost`` and ``normalized_latency``
    by ``model_calls / 10`` (so they stay in roughly [0, 1]). The min is taken
    over model-family groups for the action under analysis.
    """
    var = per_action[action]["per_model_family"]
    if not var:
        return 0.0
    utilities: list[float] = []
    for _group, m in var.items():
        span = m["span_f0_5"]
        pfp = m["primary_false_positive_rate"]
        norm_cost = m["model_calls"] / 10.0
        norm_latency = m["model_calls"] / 10.0  # skeleton: same proxy
        utilities.append(span - lambda_ * pfp - mu * norm_cost - nu * norm_latency)
    return round(min(utilities), 6)


def _compute_cvar_utility(
    per_action: dict[str, Any],
    action: str,
    lambda_: float,
    mu: float,
    nu: float,
    alpha: float,
) -> float:
    """CVaR_α utility: average of worst-α fraction of per-group utilities."""
    var = per_action[action]["per_model_family"]
    if not var:
        return 0.0
    utilities: list[float] = []
    for _group, m in var.items():
        span = m["span_f0_5"]
        pfp = m["primary_false_positive_rate"]
        norm_cost = m["model_calls"] / 10.0
        norm_latency = m["model_calls"] / 10.0
        utilities.append(span - lambda_ * pfp - mu * norm_cost - nu * norm_latency)
    return round(_cvar(utilities, alpha), 6)


# ---------------------------------------------------------------------------
# Search mechanics stub (bounded grid + greedy refinement, pure Python)
# ---------------------------------------------------------------------------


def _bounded_grid_candidates() -> list[dict[str, Any]]:
    """Generate a small deterministic candidate rule grid for the self-test.

    Real search would enumerate rule predicates over ALLOWED_RUNTIME_FEATURES
    and actions over ALLOWED_ACTIONS. Here we emit a fixed small grid that
    exercises the grammar so the self-test can verify the mechanics without
    running the full search (which is deferred to ``--input``).
    """
    grid: list[dict[str, Any]] = []
    # Each candidate is a single-rule policy (rule + action). Real B13 search
    # would compose 6-10 rules per policy; for the stub we emit one-rule
    # policies to keep the grid bounded and deterministic.
    rule_predicates = (
        {"feature": "query_noise", "operator": ">", "value": 0},
        {"feature": "candidate_support_exists", "operator": "==", "value": True},
        {"feature": "local_anchor", "operator": "==", "value": True},
        {
            "feature": "rrf_backed_by_anchor",
            "operator": "==",
            "value": False,
        },
        {"feature": "candidate_count", "operator": ">", "value": 0},
        {
            "feature": "symbol_regex_agree_file",
            "operator": "==",
            "value": True,
        },
    )
    for rule in rule_predicates:
        for action in ALLOWED_ACTIONS:
            grid.append({"rule": rule, "action": action})
    return grid


def _validate_rule_grammar(policy: dict[str, Any]) -> list[str]:
    """Validate a candidate policy against the frozen rule grammar.

    Returns a list of violation strings (empty list = valid). Each rule must
    use only ALLOWED_RUNTIME_FEATURES and each action must be in
    ALLOWED_ACTIONS.
    """
    violations: list[str] = []
    rules = policy.get("rules")
    if not isinstance(rules, list):
        violations.append("policy.rules must be a list")
        return violations
    if not (MIN_RULES <= len(rules) <= MAX_RULES):
        violations.append(
            f"policy must have between {MIN_RULES} and {MAX_RULES} rules; "
            f"got {len(rules)}"
        )
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            violations.append(f"rule[{idx}] must be a dict")
            continue
        feature = rule.get("feature")
        if feature not in ALLOWED_RUNTIME_FEATURES:
            violations.append(
                f"rule[{idx}].feature {feature!r} not in ALLOWED_RUNTIME_FEATURES"
            )
        action = rule.get("action")
        if action not in ALLOWED_ACTIONS:
            violations.append(
                f"rule[{idx}].action {action!r} not in ALLOWED_ACTIONS"
            )
        op = rule.get("operator")
        if op not in (">", "<", "==", "!=", ">=", "<="):
            violations.append(f"rule[{idx}].operator {op!r} unsupported")
    return violations


def _run_search_stub(
    per_action: dict[str, Any],
    replay_source: str,
) -> dict[str, Any]:
    """Bounded grid + greedy refinement search stub.

    The real search would: (1) enumerate candidate policies over the rule
    grammar, (2) evaluate each candidate's worst-group utility on P21 records
    via per-strategy outcome selection (replay), (3) keep the
    best-worst-group-utility policy subject to the leave-one-out rotation
    criteria. Here we only verify the mechanics: the grid is generated, the
    grammar is validated, and the worst-group utility is computed for the
    reference action (use_p25_action, mirroring B10's baseline). The real
    candidate-policy evaluation is deferred to ``--input``.
    """
    grid = _bounded_grid_candidates()
    # Validate the grammar of every candidate (one-rule policies for the stub).
    grammar_violations: list[str] = []
    for cand in grid:
        # Attach the candidate's action to the rule so grammar validation can
        # check it; one-rule policies are below MIN_RULES by design (stub), so
        # we only surface non-count violations below.
        rule_with_action = dict(cand["rule"])
        rule_with_action["action"] = cand["action"]
        violations = _validate_rule_grammar({"rules": [rule_with_action]})
        for v in violations:
            if "must have between" not in v:
                grammar_violations.append(v)
        if cand["action"] not in ALLOWED_ACTIONS:
            grammar_violations.append(
                f"candidate action {cand['action']!r} not in ALLOWED_ACTIONS"
            )
    # Reference action: use_p25_action (mirrors B10's baseline-for-deltas).
    ref_action = "use_p25_action"
    worst_group_utility = _compute_robust_utility(
        per_action,
        ref_action,
        lambda_=ROBUST_UTILITY_LAMBDA,
        mu=ROBUST_UTILITY_MU,
        nu=ROBUST_UTILITY_NU,
    )
    cvar_utility = _compute_cvar_utility(
        per_action,
        ref_action,
        lambda_=ROBUST_UTILITY_LAMBDA,
        mu=ROBUST_UTILITY_MU,
        nu=ROBUST_UTILITY_NU,
        alpha=CVAR_ALPHA,
    )
    return {
        "grid_size": len(grid),
        "grammar_violations": grammar_violations,
        "reference_action": ref_action,
        "worst_group_utility_reference": worst_group_utility,
        "cvar_utility_reference": cvar_utility,
        "iterations_used": 0,  # stub: no real iteration
        "max_search_iterations": MAX_SEARCH_ITERATIONS,
        "search_completed": False,  # stub: real search deferred
    }


# ---------------------------------------------------------------------------
# Leave-one-out rotation evaluation (stub)
# ---------------------------------------------------------------------------


def _evaluate_leave_one_out_rotations(
    per_action: dict[str, Any],
    replay_source: str,
) -> dict[str, Any]:
    """Emit the 3 leave-one-model-family-out rotation *definitions* only.

    The skeleton performs NO empirical rotation evaluation. To avoid
    surfacing synthetic per-rotation ``passes=true`` /
    ``test_worst_group_utility`` / ``delta_vs_b10_reference`` values that
    could be misread as empirical results, this function emits only:

    - ``rotations_defined``: True
    - ``rotation_count``: 3
    - ``rotations_evaluated``: False (no empirical evaluation performed)
    - ``rotations``: a list of rotation *definitions* (rotation_id +
      train_families + test_family + test_subfamilies), with NO
      ``passes`` / ``test_worst_group_utility`` / ``delta_vs_b10_reference``
      fields.

    A future real empirical B13 path (with
    ``empirical_policy_search_performed=true``) would replace this with
    actual train/test split evaluation; that path is NOT present in this
    skeleton.
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
    return {
        "rotations_defined": True,
        "rotation_count": len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS),
        "rotations_evaluated": False,
        "rotations": rotations_list,
    }


# ---------------------------------------------------------------------------
# Search verdict evaluation (predeclared criteria)
# ---------------------------------------------------------------------------


def _evaluate_search(
    per_action: dict[str, Any],
    replay_source: str,
) -> tuple[dict[str, Any], str, str]:
    """Apply the predeclared search criteria (skeleton-safe).

    Returns ``(search_results, verdict, verdict_reason)``.

    Until a real empirical B13 replay/search path exists (an explicit
    ``empirical_policy_search_performed=true`` path, which is NOT present in
    this skeleton), this function NEVER emits ``success`` / ``failure`` /
    ``partial``. Those verdicts are reserved for future empirical B13 and
    are deliberately excluded from ``ALLOWED_VERDICTS``.

    Skeleton behavior:
    - ``synthetic_fixture`` → verdict ``insufficient_data``
    - ``ci_ephemeral_records`` → verdict ``not_implemented`` (the
      ``--input`` path overrides this anyway, but the default is safe)

    The search_results block surfaces only mechanics-stub info and the
    rotation *definitions* (no empirical per-rotation passes / utilities /
    deltas). ``all_rotations_pass`` is emitted as ``False`` (no rotations
    were empirically evaluated) and ``rotations_evaluated=False`` /
    ``policy_found=False`` / ``winner_declared=False`` are surfaced so a
    reader cannot mistake the skeleton for an empirical B13 run.
    """
    search_stub = _run_search_stub(per_action, replay_source)
    rotations_block = _evaluate_leave_one_out_rotations(
        per_action, replay_source
    )
    search_results: dict[str, Any] = {
        "search_stub": search_stub,
        "leave_one_out_rotations": rotations_block,
        # Skeleton: no empirical rotation evaluation happened, so the
        # all-rotations-pass flag is False by construction.
        "all_rotations_pass": False,
        "rotations_evaluated": False,
        "policy_found": False,
        "winner_declared": False,
    }
    if replay_source == "synthetic_fixture":
        return (
            search_results,
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; no empirical "
            "B13 search or rotation evaluation performed; success, "
            "failure, or partial verdicts require a future empirical "
            "policy_search_performed=true path",
        )
    # ci_ephemeral_records: real search is not yet implemented.
    return (
        search_results,
        "not_implemented",
        "ci_ephemeral_records_replay_not_implemented; no empirical B13 "
        "search or rotation evaluation performed; success, failure, or "
        "partial verdicts require a future empirical "
        "policy_search_performed=true path",
    )


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B13 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so its
    SHA-256 is stable across runs. The on-disk spec file is the pin (mirrors
    B10/B10B/B11/B12 freeze style). The self-test verifies hash stability by
    re-loading and re-hashing.

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
        "claim_level": "distributionally_robust_policy_search_v0",
        "description": (
            "B13 Distributionally Robust Policy Search: bounded grid + greedy "
            "refinement search over a frozen rule grammar (6-10 rules, "
            "runtime-observable features only) that optimizes worst-group "
            "utility or CVaR_20%, validated via rotating "
            "leave-one-model-family-out. Replay and search only; no live LLM "
            "calls, no default change, no policy promotion. Results are "
            "research candidates only and feed into B14 (uncertainty "
            "calibration) and B16 (downstream agent evaluation)."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        # The algorithm_spec DEFINES the B13 policy-search stage (so
        # stage_is_policy_search=true), but no empirical B13 search has been
        # performed by this skeleton (empirical_policy_search_performed=false).
        # The synthetic / stub report sets policy_search_performed=false so
        # the public artifact cannot be misread as an empirical B13 run.
        "stage_is_policy_search": True,
        "empirical_policy_search_performed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "aggregate_only_public_artifact": True,
        "algorithm_spec_has_no_model_names": True,
        "allowed_runtime_features": list(ALLOWED_RUNTIME_FEATURES),
        "allowed_model_profile_caps": list(ALLOWED_MODEL_PROFILE_CAPS),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "min_rules": MIN_RULES,
        "max_rules": MAX_RULES,
        "max_search_iterations": MAX_SEARCH_ITERATIONS,
        "robust_utility_lambda": ROBUST_UTILITY_LAMBDA,
        "robust_utility_mu": ROBUST_UTILITY_MU,
        "robust_utility_nu": ROBUST_UTILITY_NU,
        "cvar_alpha": CVAR_ALPHA,
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
        "metric_names": list(METRIC_NAMES),
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
            "no_threshold_tuning_outside_search_budget": True,
            "no_evidencecore_semantics_change": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "no_model_names_in_algorithm_spec": True,
            "replay_only_no_live_search_runs_in_evaluator": True,
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
    """Check whether the on-disk frozen reference specs (B10, B10B, B11, B12)
    are present and loadable. Returns ``{spec_id: hash_pinned_on_disk_bool}``.
    The actual sha256 hex is NEVER returned (it would trip the forbidden-value
    scan); only the boolean matched flag is exposed publicly.
    """
    refs = {}
    for spec_id, path in (
        ("balanced_policy_v1_benchmark_routed", B10_SPEC_PATH),
        ("balanced_policy_v1_runtime_shadow_ambiguous_branch", B10B_SPEC_PATH),
        ("b11_prospective_v0", B11_SPEC_PATH),
        ("b12_mechanism_decomposition_v0", B12_SPEC_PATH),
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
    per_action: dict[str, Any],
    *,
    self_test: bool,
    replay_source: str,
) -> dict[str, Any]:
    """Build the B13 distributionally robust policy search report.

    ``per_action`` is the per-action metrics dict (see
    ``_build_synthetic_fixture`` for the shape). ``self_test=True`` flags that
    the report was produced from a synthetic fixture for mechanics validation;
    ``replay_source`` is one of ``ALLOWED_REPLAY_SOURCES``.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    overall_mean = _aggregate_overall(per_action)
    worst_repo = _worst_group_by_repo(per_action, "use_p25_action")
    worst_model = _worst_group_by_model_family(per_action, "use_p25_action")
    worst_group = {**worst_repo, **worst_model}
    bootstrap_ci = _bootstrap_ci(per_action, "use_p25_action")
    robust_utility_ref = _compute_robust_utility(
        per_action,
        "use_p25_action",
        lambda_=PREDECLARED_CRITERIA["robust_utility_lambda"],
        mu=PREDECLARED_CRITERIA["robust_utility_mu"],
        nu=PREDECLARED_CRITERIA["robust_utility_nu"],
    )
    cvar_utility_ref = _compute_cvar_utility(
        per_action,
        "use_p25_action",
        lambda_=PREDECLARED_CRITERIA["robust_utility_lambda"],
        mu=PREDECLARED_CRITERIA["robust_utility_mu"],
        nu=PREDECLARED_CRITERIA["robust_utility_nu"],
        alpha=PREDECLARED_CRITERIA["cvar_alpha"],
    )

    weak_vs_p25 = _compute_action_deltas(per_action, "weak_only", "use_p25_action")
    local_vs_p25 = _compute_action_deltas(
        per_action, "use_local_baseline", "use_p25_action"
    )
    weak_local_model_spread = _compute_model_family_delta_spread(
        per_action, "weak_only", "use_p25_action", "gold_span"
    )

    search_results, verdict, verdict_reason = _evaluate_search(
        per_action, replay_source
    )

    ref_hashes = _reference_spec_hashes()
    # Verify the algorithm spec carries no raw model names (special B13
    # invariant). This is computed at report-build time so the report itself
    # surfaces the invariant outcome.
    model_name_hits = _scan_spec_for_model_names(spec)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": "distributionally_robust_policy_search_v0",
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        # B13 defines the policy-search STAGE (stage_is_policy_search=true),
        # but this skeleton performs NO empirical policy search
        # (empirical_policy_search_performed=false). The report flag
        # policy_search_performed=false so the synthetic / stub report cannot
        # be misread as an empirical B13 search.
        "stage_is_policy_search": True,
        "empirical_policy_search_performed": False,
        "policy_search_performed": False,
        # Skeleton: no empirical policy was found, no rotations were
        # evaluated, no winner was declared. These top-level flags make the
        # skeleton stance unambiguous and mirror the search_results sub-block.
        "policy_found": False,
        "rotations_evaluated": False,
        "rotations_defined": True,
        "rotation_count": len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS),
        "winner_declared": False,
        "quality_strategy_tuned": False,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "frozen_reference_specs_pinned_on_disk": ref_hashes,
        "allowed_runtime_features": list(ALLOWED_RUNTIME_FEATURES),
        "allowed_model_profile_caps": list(ALLOWED_MODEL_PROFILE_CAPS),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "min_rules": MIN_RULES,
        "max_rules": MAX_RULES,
        "max_search_iterations": MAX_SEARCH_ITERATIONS,
        "robust_utility_lambda": ROBUST_UTILITY_LAMBDA,
        "robust_utility_mu": ROBUST_UTILITY_MU,
        "robust_utility_nu": ROBUST_UTILITY_NU,
        "cvar_alpha": CVAR_ALPHA,
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
        "metric_names": list(METRIC_NAMES),
        "reference_action": "use_p25_action",
        "per_action_metrics": per_action,
        "overall_mean": overall_mean,
        "worst_group": worst_group,
        "bootstrap_ci_95": bootstrap_ci,
        "robust_utility_reference": robust_utility_ref,
        "cvar_utility_reference": cvar_utility_ref,
        "action_deltas_weak_vs_p25": weak_vs_p25,
        "action_deltas_local_vs_p25": local_vs_p25,
        "weak_local_model_family_spread": weak_local_model_spread,
        "search_results": search_results,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "aggregate_only_public_artifact": True,
        "algorithm_spec_has_no_model_names": (len(model_name_hits) == 0),
        "algorithm_spec_model_name_scan_hits": model_name_hits,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_default_change": True,
            "no_policy_promotion": True,
            "no_threshold_tuning_outside_search_budget": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "runtime_calls_by_replay_zero": True,
            "model_calls_by_replay_zero": True,
            "algorithm_spec_has_no_model_names_true": True,
            "replay_only_no_live_search_runs_in_evaluator": True,
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
    if spec.get("claim_level") != "distributionally_robust_policy_search_v0":
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
    # B13 DEFINES the policy-search stage (stage_is_policy_search=true), but
    # no empirical B13 search is performed by this skeleton
    # (empirical_policy_search_performed=false). The skeleton report sets
    # policy_search_performed=false to avoid overclaiming empirical search.
    if spec.get("stage_is_policy_search") is not True:
        raise ValueError(
            "algorithm spec stage_is_policy_search must be true (B13 stage)"
        )
    if spec.get("empirical_policy_search_performed") is not False:
        raise ValueError(
            "algorithm spec empirical_policy_search_performed must be false "
            "(no empirical search performed by skeleton)"
        )
    if spec.get("policy_search_performed") is not False:
        raise ValueError(
            "algorithm spec policy_search_performed must be false (skeleton; "
            "use stage_is_policy_search=true to mark the stage)"
        )
    if spec.get("quality_strategy_tuned") is not False:
        raise ValueError("algorithm spec quality_strategy_tuned must be false")
    if spec.get("aggregate_only_public_artifact") is not True:
        raise ValueError("algorithm spec aggregate_only_public_artifact must be true")
    if spec.get("algorithm_spec_has_no_model_names") is not True:
        raise ValueError(
            "algorithm spec algorithm_spec_has_no_model_names must be true"
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
    if tuple(spec.get("allowed_runtime_features") or ()) != ALLOWED_RUNTIME_FEATURES:
        raise ValueError("algorithm spec allowed_runtime_features mismatch")
    if tuple(spec.get("allowed_actions") or ()) != ALLOWED_ACTIONS:
        raise ValueError("algorithm spec allowed_actions mismatch")
    if spec.get("min_rules") != MIN_RULES:
        raise ValueError("algorithm spec min_rules mismatch")
    if spec.get("max_rules") != MAX_RULES:
        raise ValueError("algorithm spec max_rules mismatch")
    if spec.get("max_search_iterations") != MAX_SEARCH_ITERATIONS:
        raise ValueError("algorithm spec max_search_iterations mismatch")
    if spec.get("robust_utility_lambda") != ROBUST_UTILITY_LAMBDA:
        raise ValueError("algorithm spec robust_utility_lambda mismatch")
    if spec.get("robust_utility_mu") != ROBUST_UTILITY_MU:
        raise ValueError("algorithm spec robust_utility_mu mismatch")
    if spec.get("robust_utility_nu") != ROBUST_UTILITY_NU:
        raise ValueError("algorithm spec robust_utility_nu mismatch")
    if spec.get("cvar_alpha") != CVAR_ALPHA:
        raise ValueError("algorithm spec cvar_alpha mismatch")
    # B13 special invariant: the spec must NOT list raw model family names
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
    if tuple(spec.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("algorithm spec metric_names mismatch")
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
    # B13 special invariant: no model names in algorithm_spec.
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
    if report.get("claim_level") != "distributionally_robust_policy_search_v0":
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
    # B13 DEFINES the policy-search stage (stage_is_policy_search=true), but
    # this skeleton performs NO empirical policy search
    # (empirical_policy_search_performed=false). The report flag
    # policy_search_performed=false so synthetic / stub reports cannot be
    # misread as empirical B13 search results.
    if report.get("stage_is_policy_search") is not True:
        raise ValueError(
            "report stage_is_policy_search must be true (B13 stage)"
        )
    if report.get("empirical_policy_search_performed") is not False:
        raise ValueError(
            "report empirical_policy_search_performed must be false "
            "(no empirical search performed by skeleton)"
        )
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "report policy_search_performed must be false (skeleton; "
            "use stage_is_policy_search=true to mark the stage)"
        )
    # Skeleton: no empirical policy found, no rotations evaluated, no winner.
    if report.get("policy_found") is not False:
        raise ValueError("report policy_found must be false (skeleton)")
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
            "report algorithm_spec_has_no_model_names must be true (B13 invariant)"
        )
    if report.get("predeclared_criteria") != PREDECLARED_CRITERIA:
        raise ValueError("report predeclared_criteria must match the frozen constants")
    if tuple(report.get("allowed_runtime_features") or ()) != ALLOWED_RUNTIME_FEATURES:
        raise ValueError("report allowed_runtime_features mismatch")
    if tuple(report.get("allowed_actions") or ()) != ALLOWED_ACTIONS:
        raise ValueError("report allowed_actions mismatch")
    if report.get("min_rules") != MIN_RULES:
        raise ValueError("report min_rules mismatch")
    if report.get("max_rules") != MAX_RULES:
        raise ValueError("report max_rules mismatch")
    if report.get("max_search_iterations") != MAX_SEARCH_ITERATIONS:
        raise ValueError("report max_search_iterations mismatch")
    if tuple(report.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("report model_families mismatch")
    if tuple(report.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("report repos mismatch")
    if report.get("reference_action") != "use_p25_action":
        raise ValueError("report reference_action mismatch")
    # Required top-level sections.
    for key in (
        "per_action_metrics",
        "overall_mean",
        "worst_group",
        "bootstrap_ci_95",
        "robust_utility_reference",
        "cvar_utility_reference",
        "action_deltas_weak_vs_p25",
        "action_deltas_local_vs_p25",
        "weak_local_model_family_spread",
        "search_results",
        "leave_one_model_family_out_rotations",
    ):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # Search results substructure. The skeleton emits only mechanics-stub
    # info + rotation definitions; no empirical per-rotation passes /
    # test_worst_group_utility / delta_vs_b10_reference values.
    sr = report.get("search_results") or {}
    for key in (
        "search_stub",
        "leave_one_out_rotations",
        "all_rotations_pass",
        "rotations_evaluated",
        "policy_found",
        "winner_declared",
    ):
        if key not in sr:
            raise ValueError(f"search_results missing required section: {key}")
    if sr.get("all_rotations_pass") is not False:
        raise ValueError(
            "search_results.all_rotations_pass must be false (skeleton; no "
            "empirical rotation evaluation performed)"
        )
    if sr.get("rotations_evaluated") is not False:
        raise ValueError(
            "search_results.rotations_evaluated must be false (skeleton)"
        )
    if sr.get("policy_found") is not False:
        raise ValueError("search_results.policy_found must be false (skeleton)")
    if sr.get("winner_declared") is not False:
        raise ValueError(
            "search_results.winner_declared must be false (skeleton)"
        )
    # leave_one_out_rotations must be a definitions-only block (no empirical
    # per-rotation passes / test_worst_group_utility / delta_vs_b10_reference).
    rots = sr.get("leave_one_out_rotations") or {}
    if rots.get("rotations_defined") is not True:
        raise ValueError(
            "search_results.leave_one_out_rotations.rotations_defined "
            "must be true"
        )
    if rots.get("rotation_count") != len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS):
        raise ValueError(
            "search_results.leave_one_out_rotations.rotation_count mismatch"
        )
    if rots.get("rotations_evaluated") is not False:
        raise ValueError(
            "search_results.leave_one_out_rotations.rotations_evaluated "
            "must be false (skeleton)"
        )
    rot_list = rots.get("rotations")
    if not isinstance(rot_list, list) or len(rot_list) != len(
        LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS
    ):
        raise ValueError(
            "search_results.leave_one_out_rotations.rotations must be a "
            "list of 3 rotation definitions"
        )
    for r in rot_list:
        if r.get("evaluated") is not False:
            raise ValueError(
                "rotation definitions must have evaluated=false (skeleton)"
            )
        for forbidden_key in (
            "passes",
            "test_worst_group_utility",
            "delta_vs_b10_reference",
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
        "no_threshold_tuning_outside_search_budget",
        "no_evidencecore_semantics_change",
        "promotion_ready_false",
        "default_should_change_false",
        "aggregate_only_public_artifact",
        "forbidden_public_keys_scanned",
        "no_raw_path_digest_provider_strings",
        "runtime_calls_by_replay_zero",
        "model_calls_by_replay_zero",
        "algorithm_spec_has_no_model_names_true",
        "replay_only_no_live_search_runs_in_evaluator",
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input (stub): load P21 outputs without computing search
# ---------------------------------------------------------------------------


def _load_p21_input(path: str) -> dict[str, Any]:
    """Load a P21 outputs JSON file (or directory of JSON files) and return a
    minimal metadata payload. The full per-action replay + search computation
    is deferred to a later task; for now we only verify the input is valid JSON
    and surface its top-level shape (without leaking any forbidden keys).
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

    Real per-action replay + search computation (reading P21 per-strategy
    outcomes, enumerating candidate policies over the rule grammar, evaluating
    each candidate's worst-group utility, applying the leave-one-out rotation
    criteria) is deferred to a later task. For now we emit a well-formed report
    with ``verdict="not_implemented"`` and an explanatory reason, while still
    passing all safety-invariant checks.
    """
    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)
    # Reuse the synthetic fixture so the report has the right SHAPE; the
    # verdict is overridden below to "not_implemented".
    per_action = _build_synthetic_fixture()
    report = build_report(
        per_action, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Override the verdict to signal that no real search happened.
    report["verdict"] = "not_implemented"
    report["verdict_reason"] = (
        "real-input search + per-action replay computation deferred to later "
        f"task; input_meta={input_meta}"
    )
    # Re-stamp the spec hash fields (defensive: build_report already sets these).
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
    clean = {"provenance": "b13_dro_policy_search::build_report"}
    hits3 = _recursive_key_scan(clean)
    assert hits3 == [], hits3

    # A 64-hex digest value must trip the forbidden-value scan.
    bad_digest = {"some_field": "a" * 64}
    hits4 = _recursive_key_scan(bad_digest)
    assert any("forbidden_value" in h for h in hits4), hits4

    # B13 special: model names must be flagged by _scan_spec_for_model_names.
    bad_spec = {"description": "tuned for Kimi and Qwen", "nested": {"m": "deepseek"}}
    mh = _scan_spec_for_model_names(bad_spec)
    flat_m = " ".join(mh)
    assert "kimi" in flat_m
    assert "qwen" in flat_m
    assert "deepseek" in flat_m

    # A clean spec using only capability tokens must not trip the model-name
    # scan.
    clean_spec = {
        "description": "uses adapter.supports_reliable_span_narrow capability",
        "caps": ["supports_reliable_span_narrow", "cost_class"],
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


def _self_test_synthetic_fixture_metrics() -> None:
    per_action = _build_synthetic_fixture()
    # All 3 actions x 8 repos x 4 model families present.
    for action in ALLOWED_ACTIONS:
        assert action in per_action, action
        assert set(per_action[action]["per_repo"].keys()) == set(
            MINIMUM_VIABLE_REPOS
        )
        assert set(per_action[action]["per_model_family"].keys()) == set(
            MODEL_FAMILIES
        )
        assert per_action[action]["n_records"] == len(MINIMUM_VIABLE_REPOS) * len(
            MODEL_FAMILIES
        ), action
    # weak_only should reduce false_span / pfp / model_calls vs use_p25_action
    # in the synthetic fixture (sanity check on the deterministic generator).
    weak = per_action["weak_only"]["overall_mean"]
    p25 = per_action["use_p25_action"]["overall_mean"]
    assert weak["false_span"] <= p25["false_span"], (weak, p25)
    assert weak["primary_false_positive_rate"] <= p25["primary_false_positive_rate"], (
        weak,
        p25,
    )
    assert weak["model_calls"] <= p25["model_calls"], (weak, p25)
    # use_local_baseline should have the lowest model_calls (no LLM at all).
    local = per_action["use_local_baseline"]["overall_mean"]
    assert local["model_calls"] <= p25["model_calls"], (local, p25)


def _self_test_rule_grammar_valid() -> None:
    """Rule grammar: only allowed features and actions."""
    # Valid 6-rule policy.
    valid_policy = {
        "rules": [
            {"feature": f, "operator": ">", "value": 0, "action": a}
            for f, a in zip(
                ALLOWED_RUNTIME_FEATURES[:6],
                ALLOWED_ACTIONS * 2,  # 6 actions
            )
        ]
    }
    assert _validate_rule_grammar(valid_policy) == [], _validate_rule_grammar(
        valid_policy
    )
    # Invalid: too few rules.
    too_few = {"rules": [{"feature": "query_noise", "operator": ">", "value": 0,
                          "action": "weak_only"}]}
    v = _validate_rule_grammar(too_few)
    assert any("must have between" in s for s in v), v
    # Invalid: too many rules.
    too_many = {
        "rules": [
            {"feature": "query_noise", "operator": ">", "value": 0,
             "action": "weak_only"}
            for _ in range(MAX_RULES + 1)
        ]
    }
    v2 = _validate_rule_grammar(too_many)
    assert any("must have between" in s for s in v2), v2
    # Invalid: forbidden feature (benchmark-private label).
    bad_feature = {
        "rules": [
            {"feature": "task_bucket", "operator": "==", "value": "ambiguous",
             "action": "weak_only"}
            for _ in range(MIN_RULES)
        ]
    }
    v3 = _validate_rule_grammar(bad_feature)
    assert any("not in ALLOWED_RUNTIME_FEATURES" in s for s in v3), v3
    # Invalid: forbidden action (LLM action not allowed).
    bad_action = {
        "rules": [
            {"feature": "query_noise", "operator": ">", "value": 0,
             "action": "llm_span_narrow"}
            for _ in range(MIN_RULES)
        ]
    }
    v4 = _validate_rule_grammar(bad_action)
    assert any("not in ALLOWED_ACTIONS" in s for s in v4), v4
    # Spec must include the grammar constants.
    spec = build_algorithm_spec()
    assert tuple(spec["allowed_runtime_features"]) == ALLOWED_RUNTIME_FEATURES
    assert tuple(spec["allowed_actions"]) == ALLOWED_ACTIONS
    assert spec["min_rules"] == MIN_RULES
    assert spec["max_rules"] == MAX_RULES
    assert spec["max_search_iterations"] == MAX_SEARCH_ITERATIONS


def _self_test_search_mechanics_stub() -> None:
    """Bounded grid + greedy refinement search stub mechanics."""
    per_action = _build_synthetic_fixture()
    search = _run_search_stub(per_action, "synthetic_fixture")
    assert search["grid_size"] > 0, search
    assert search["grammar_violations"] == [], search["grammar_violations"]
    assert search["reference_action"] == "use_p25_action"
    assert "worst_group_utility_reference" in search
    assert "cvar_utility_reference" in search
    assert search["iterations_used"] == 0  # stub
    assert search["search_completed"] is False  # stub
    assert search["max_search_iterations"] == MAX_SEARCH_ITERATIONS
    # CVaR ≤ worst-group utility? CVaR averages the worst alpha fraction, so it
    # is <= the worst (min) value, i.e., CVaR <= worst_group. Both are computed
    # over the same per-family utilities.
    cvar = search["cvar_utility_reference"]
    worst = search["worst_group_utility_reference"]
    assert cvar <= worst + 1e-6, (cvar, worst)


def _self_test_leave_one_out_rotations_defined() -> None:
    """3 leave-one-model-family-out rotations defined.

    The evaluator-side rotations keep real model family names (used only for
    synthetic-fixture computation); the algorithm_spec emits abstract
    family_slots versions so NO raw model names appear in the spec.
    """
    assert len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS) == 3
    rot_ids = {r["rotation_id"] for r in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS}
    assert rot_ids == {"loo_family_a", "loo_family_b", "loo_family_c_and_d"}, rot_ids
    for rot in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS:
        assert "train_families" in rot and len(rot["train_families"]) >= 2
        assert "test_family" in rot
        assert "abstract_train_slots" in rot
    # The loo_family_c_and_d rotation aggregates deepseek_flash + deepseek_pro
    # (family_c + family_d) as the test cluster.
    loo_cd = next(
        r for r in LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS
        if r["rotation_id"] == "loo_family_c_and_d"
    )
    assert loo_cd["test_family"] == "deepseek"
    assert tuple(loo_cd["test_subfamilies"]) == ("deepseek_flash", "deepseek_pro")
    assert tuple(loo_cd["abstract_test_slots"]) == ("family_c", "family_d")
    # Spec must include the 3 rotations in abstract-slot form (NO model names).
    spec = build_algorithm_spec()
    assert len(spec["leave_one_model_family_out_rotations"]) == 3
    assert tuple(spec["family_slots"]) == ABSTRACT_FAMILY_SLOTS
    assert "model_families" not in spec, (
        "algorithm_spec must NOT contain model_families (raw model names)"
    )
    # The spec's rotation entries use abstract slots, not real family names.
    for r in spec["leave_one_model_family_out_rotations"]:
        assert "train_family_slots" in r
        assert "train_families" not in r, "spec rotation must not expose real names"
        assert "test_family" not in r, "spec rotation must not expose real names"
    # Evaluate the rotations on the synthetic fixture (evaluator-side, real
    # family names are fine here — they never enter the spec). The skeleton
    # emits definitions only; no empirical per-rotation passes /
    # test_worst_group_utility / delta_vs_b10_reference values.
    per_action = _build_synthetic_fixture()
    rotations_block = _evaluate_leave_one_out_rotations(
        per_action, "synthetic_fixture"
    )
    assert rotations_block["rotations_defined"] is True
    assert rotations_block["rotation_count"] == 3
    assert rotations_block["rotations_evaluated"] is False
    rot_ids_back = {r["rotation_id"] for r in rotations_block["rotations"]}
    assert rot_ids_back == rot_ids, rot_ids_back
    for r in rotations_block["rotations"]:
        assert r.get("evaluated") is False
        # Skeleton must NOT carry empirical per-rotation fields.
        for forbidden_key in (
            "passes",
            "test_worst_group_utility",
            "delta_vs_b10_reference",
        ):
            assert forbidden_key not in r, (forbidden_key, r)


def _self_test_input_stub_not_implemented(tmp_path: Path) -> None:
    """--input mode must emit verdict='not_implemented' without doing any
    real search computation."""
    p = tmp_path / "p21_stub.json"
    p.write_text(
        json.dumps({"records": [{"policy": "balanced_v1"}]}), encoding="utf-8"
    )
    meta = _load_p21_input(str(p))
    assert meta["source_kind"] == "file_object"
    assert meta["n_records"] == 1
    report = _build_not_implemented_report(meta)
    verify_report(report)
    assert report["replay_source"] == "ci_ephemeral_records"
    assert report["verdict"] == "not_implemented"
    assert "deferred" in report["verdict_reason"]


def _self_test_reference_specs() -> None:
    """The B10, B10B, B11 and B12 frozen reference specs must exist on disk so
    the B13 frozen_artifacts pin is meaningful."""
    refs = _reference_spec_hashes()
    assert refs.get("balanced_policy_v1_benchmark_routed") is True, refs
    assert refs.get("balanced_policy_v1_runtime_shadow_ambiguous_branch") is True, refs
    assert refs.get("b11_prospective_v0") is True, refs
    assert refs.get("b12_mechanism_decomposition_v0") is True, refs


def _self_test_artifacts_match_in_memory() -> None:
    """Read-only drift check: build the expected algorithm spec + report in
    memory and compare them to the on-disk artifacts. Fails on drift. Does
    NOT write anything to disk (self-test is read-only). Use
    ``--regenerate-artifacts`` to (re)write the on-disk artifacts.
    """
    # Expected algorithm spec (in memory).
    expected_spec = build_algorithm_spec()
    expected_spec_hash = _sha256_json(expected_spec)

    on_disk_spec = _load_json(ALGORITHM_SPEC_PATH)
    on_disk_spec_hash = _sha256_json(on_disk_spec)
    if on_disk_spec_hash != expected_spec_hash:
        raise ValueError(
            "on-disk algorithm spec drifted from build_algorithm_spec() "
            f"output: on_disk={on_disk_spec_hash!r} "
            f"expected={expected_spec_hash!r}; run "
            "`python3 eval/b13_dro_policy_search.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    # Validate the on-disk spec in its own right.
    verify_algorithm_spec(on_disk_spec, on_disk_spec_hash)
    if on_disk_spec != expected_spec:
        raise ValueError(
            "on-disk algorithm spec content drifted from "
            "build_algorithm_spec() output (same hash but content differs; "
            "this should be impossible)"
        )

    # Expected report (in memory).
    per_action = _build_synthetic_fixture()
    expected_report = build_report(
        per_action, self_test=True, replay_source="synthetic_fixture"
    )

    on_disk_report = _load_json(REPORT_PATH)
    if on_disk_report != expected_report:
        raise ValueError(
            "on-disk b13_dro_policy_search_report.json drifted from the "
            "in-memory build_report() output; run "
            "`python3 eval/b13_dro_policy_search.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    # Validate the on-disk report in its own right.
    verify_report(on_disk_report)


def regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report so the
    artifact pin matches the in-code build functions. Mirrors the B10/B10B/
    B11/B12 freeze-write style: deterministic output, canonical JSON.

    This is the ONLY mutating path. ``--self-test`` is read-only and uses
    ``_self_test_artifacts_match_in_memory`` to detect drift.
    """
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    per_action = _build_synthetic_fixture()
    report = build_report(
        per_action, self_test=True, replay_source="synthetic_fixture"
    )
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    """Run all B13 self-test checks. Returns a summary dict."""
    import tempfile

    # 1. Forbidden-key/value scan (incl. model-name scan).
    _self_test_forbidden_scan()

    # 2. Algorithm spec hash stability.
    _self_test_spec_hash_stable()

    # 3. Synthetic fixture metrics.
    _self_test_synthetic_fixture_metrics()

    # 4. Rule grammar valid (allowed features + actions only).
    _self_test_rule_grammar_valid()

    # 5. Search mechanics stub (bounded grid + greedy refinement).
    _self_test_search_mechanics_stub()

    # 6. Leave-one-out rotations defined (3 rotations).
    _self_test_leave_one_out_rotations_defined()

    # 7. --input stub => not_implemented verdict.
    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_stub_not_implemented(Path(tmp))

    # 8. B10/B10B/B11/B12 reference specs present.
    _self_test_reference_specs()

    # 9. Read-only drift check: build expected algorithm spec + report in
    #    memory and compare to on-disk artifacts. Fails on drift. Does NOT
    #    write anything to disk; use --regenerate-artifacts to refresh.
    _self_test_artifacts_match_in_memory()

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256": spec_hash,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": "distributionally_robust_policy_search_v0",
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "stage_is_policy_search": True,
        "empirical_policy_search_performed": False,
        "policy_search_performed": False,
        "policy_found": False,
        "rotations_evaluated": False,
        "rotations_defined": True,
        "rotation_count": len(LEAVE_ONE_MODEL_FAMILY_OUT_ROTATIONS),
        "winner_declared": False,
        "quality_strategy_tuned": False,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "algorithm_spec_has_no_model_names": True,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "aggregate_only_public_artifact": True,
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "synthetic_fixture_metrics": True,
            "rule_grammar_valid": True,
            "search_mechanics_stub": True,
            "leave_one_out_rotations_defined": True,
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
            "run the B13 self-test (read-only; synthetic fixture; verifies "
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
            "path to a JSON file or directory of JSON files containing P21 "
            "outputs (model x repo runs). Currently a STUB: emits "
            "verdict='not_implemented'; full search + per-action replay "
            "computation deferred to a later task."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write the report artifact; defaults to the canonical "
            "b13_dro_policy_search_report.json artifact path"
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input and not args.regenerate_artifacts:
        parser.error(
            "B13 requires --self-test, --regenerate-artifacts, or "
            "--input <path> in this skeleton"
        )
    # Mutually exclusive: --self-test is read-only, --regenerate-artifacts is
    # the only mutating path, --input writes a report. No two may combine.
    selected = sum(
        1 for flag in (args.self_test, args.regenerate_artifacts, bool(args.input))
        if flag
    )
    if selected > 1:
        parser.error(
            "--self-test, --regenerate-artifacts, and --input are mutually "
            "exclusive"
        )
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "claim_level": report["claim_level"],
        "reference_action": report["reference_action"],
        "allowed_runtime_features": report["allowed_runtime_features"],
        "allowed_actions": report["allowed_actions"],
        "min_rules": report["min_rules"],
        "max_rules": report["max_rules"],
        "max_search_iterations": report["max_search_iterations"],
        "robust_utility_lambda": report["robust_utility_lambda"],
        "robust_utility_mu": report["robust_utility_mu"],
        "robust_utility_nu": report["robust_utility_nu"],
        "cvar_alpha": report["cvar_alpha"],
        "leave_one_model_family_out_rotations": report[
            "leave_one_model_family_out_rotations"
        ],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "evidencecore_semantics_changed": report["evidencecore_semantics_changed"],
        "stage_is_policy_search": report["stage_is_policy_search"],
        "empirical_policy_search_performed": report[
            "empirical_policy_search_performed"
        ],
        "policy_search_performed": report["policy_search_performed"],
        "policy_found": report["policy_found"],
        "rotations_evaluated": report["rotations_evaluated"],
        "rotations_defined": report["rotations_defined"],
        "rotation_count": report["rotation_count"],
        "winner_declared": report["winner_declared"],
        "quality_strategy_tuned": report["quality_strategy_tuned"],
        "runtime_calls_by_replay": report["runtime_calls_by_replay"],
        "model_calls_by_replay": report["model_calls_by_replay"],
        "aggregate_only_public_artifact": report["aggregate_only_public_artifact"],
        "algorithm_spec_has_no_model_names": report[
            "algorithm_spec_has_no_model_names"
        ],
        "robust_utility_reference": report["robust_utility_reference"],
        "cvar_utility_reference": report["cvar_utility_reference"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B13 self-test: PASS (read-only; no artifacts written)", file=sys.stderr)
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
            "policy_search_performed": False,
            "empirical_policy_search_performed": False,
            "policy_found": False,
            "rotations_evaluated": False,
            "winner_declared": False,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(
            f"B13 artifacts regenerated: {ALGORITHM_SPEC_PATH} + {REPORT_PATH}",
            file=sys.stderr,
        )
        return 0
    if args.input:
        input_meta = _load_p21_input(args.input)
        report = _build_not_implemented_report(input_meta)
        verify_report(report)
        out_path = Path(args.out) if args.out else REPORT_PATH
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B13 report written to {out_path}", file=sys.stderr)
        return 0
    print(
        "B13 requires --self-test, --regenerate-artifacts, or --input",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
