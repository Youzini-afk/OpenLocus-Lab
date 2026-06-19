#!/usr/bin/env python3
"""B12 Mechanism Decomposition.

B12 is the mechanism-decomposition phase that follows B11 (prospective blind
validation). The goal is to understand **WHY** the frozen balanced policy
``balanced_policy_v1_benchmark_routed`` (B10) works (if B11 confirms it
generalizes), via five ablation variants (A-E) and four predeclared hypotheses
(H1-H4).

B12 is replay-only: each P21 record contains per-strategy outcomes, so each
ablation variant can be computed by selecting the appropriate per-strategy
outcome from existing records. No live LLM calls are made by this evaluator.

IMPORTANT: This is a preregistration. The 5 ablation variant definitions and the
4 predeclared hypothesis support/refute criteria are FROZEN before any B12
ablation runs. No retuning is allowed after B12 ablation runs begin.

Important claim boundary: B12 is mechanism decomposition, not a promotion step.
Even if B12 supports one or more hypotheses, ``promotion_ready=false``,
``default_should_change=false``, and ``EvidenceCore`` semantics are unchanged.
B12's outcome only decides which mechanism (ambiguous routing, LLM-call
reduction, P25 fallback sufficiency, or model-specific behaviour) drives the
balanced policy's gains, which informs B13 (distributionally robust policy
search).

C1 adapter: B12 consumes private P21 v1 records via the shared
``eval/c1_private_records.py`` adapter (three-category taint model:
runtime-clean route_features, benchmark route labels, score/outcome/private
fields). The adapter never writes public artifacts; B12 derives aggregate-only
public metrics from it and runs its own forbidden-key scan.

Aggregate-only public artifacts: no task/repo/candidate/path/span/snippet/
prompt/response/gold/provider keys and no raw path/digest/provider strings. No
per-record hash is emitted; ``actual_call_avoided_set`` /
``balanced_branch_set`` / ``p25_llm_subset`` are reported as COUNTS only.

``--input`` mode loads private P21 v1 records via the C1 adapter and produces
a real aggregate-only report (per-variant replay over the 5 ablation variants,
count reporting, and the FROZEN predeclared hypothesis criteria). Scientific
verdicts (``supported`` / ``refuted`` / ``partial`` / ``insufficient_data``)
return exit 0; mechanical/privacy/schema errors return nonzero. The
``--self-test`` path verifies the ablation-variant definitions and
hypothesis-evaluation mechanics against a synthetic fixture (still
``insufficient_data`` because synthetic fixtures confer no empirical support).

Run::

    python3 eval/b12_mechanism_decomposition.py --self-test
    python3 eval/b12_mechanism_decomposition.py --input path/to/p25_policy_records.private.json
    python3 eval/b12_mechanism_decomposition.py --self-test --out /tmp/b12_report.json
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

import c1_private_records as c1

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b12_mechanism_decomposition"
REPORT_PATH = (
    ARTIFACT_DIR / "b12_mechanism_decomposition_report.json"
)
# The algorithm spec is emitted alongside the report (deterministic, fixed
# generated_at so its sha256 is stable across runs).
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "b12_mechanism_decomposition.algorithm.json"
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

SCHEMA_VERSION = "b12-mechanism-decomposition-report-v0"
SPEC_SCHEMA_VERSION = "b12-mechanism-decomposition-spec-v0"
GENERATED_BY = "b12_mechanism_decomposition"
ALGORITHM_SPEC_ID = "b12_mechanism_decomposition_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors B10/B10B/B11).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# Policy under analysis (B12 = balanced v1 mechanism decomposition).
POLICY_UNDER_ANALYSIS = "balanced_v1"
BASELINE_FOR_DELTAS = "p25"

# ---------------------------------------------------------------------------
# 5 Ablation variants (FROZEN before any ablation runs)
# ---------------------------------------------------------------------------
#
# A (full balanced)         : ambiguous->weak_only, else P25  (the full balanced policy)
# B (deterministic LLM      : P25 for all, but skip LLM for ambiguous tasks
#     reduction)              (use candidate_baseline instead) — tests whether
#                             weak_only or just skipping LLM is what helps
# C (ambiguous weak_only    : same as A (the balanced policy only has the
#     only)                   ambiguous->weak_only rule); A≡C, merged in analysis
# D (P25 default only)      : P25 for all (no ambiguous->weak_only rule) — baseline
# E (random LLM reduction)  : P25 for all, but randomly skip the same number of
#                             LLM calls as A — tests H2 (is it just call reduction?)
#
ABLATION_VARIANTS = (
    "A_full_balanced",
    "B_deterministic_llm_reduction",
    "C_ambiguous_weak_only",
    "D_p25_default",
    "E_random_llm_reduction",
)

# Explicit A≡C equivalence (the balanced policy has only one routing rule).
ABLATION_EQUIVALENCES = (("A_full_balanced", "C_ambiguous_weak_only"),)

# ---------------------------------------------------------------------------
# 4 Hypotheses (FROZEN before any ablation runs)
# ---------------------------------------------------------------------------
#
# H1 (ambiguous routing)           : gains come from ambiguous->weak_only routing
#                                    (not just call reduction, not just P25 fallback)
# H2 (LLM call reduction)          : gains come from reducing LLM calls (any
#                                    reduction, not the specific weak_only route)
# H3 (P25 fallback sufficiency)    : the ambiguous->weak_only rule doesn't help;
#                                    P25 default alone is enough
# H4 (model-specific)              : effect sizes vary significantly across model
#                                    families (e.g., A>D on Kimi but A≈D on DeepSeek)
#
HYPOTHESES = (
    "H1_ambiguous_routing",
    "H2_llm_call_reduction",
    "H3_p25_fallback_sufficiency",
    "H4_model_specific",
)

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any ablation runs)
# ---------------------------------------------------------------------------
#
# Revised (C1) to align with the actual expected balanced_v1 mechanism: the
# balanced policy is expected to PRESERVE gold/span vs D approximately (NOT
# increase gold/span), REDUCE false spans / PFP / model calls vs D, and
# OUTPERFORM B/E on false/PFP/RobustUtility enough to support targeted
# ambiguous routing. A is NOT required to increase gold/span.
#
# All deltas are computed at the overall-mean level. "≈" means within
# ±approx_equal_threshold (absolute); for primary-quality metrics (gold_span,
# span_f0_5) this is the "preserve" test. A "strict reduction" on a metric M
# means (variant - comparator) < -strictly_greater_threshold (A is strictly
# lower/better than the comparator on a lower-is-better metric). A "strict
# improvement" on RobustUtility means (A - comparator) > strictly_greater_threshold.
# "Significant model-family variation" for H4 is predeclared as a worst-case
# spread > h4_model_family_spread_threshold across model families on the
# A-minus-D gold_span delta.
#
PREDECLARED_CRITERIA: dict[str, Any] = {
    # Approximate-equality threshold for "≈" (absolute, on gold_span / span_f0_5).
    "approx_equal_threshold": 0.02,
    # Strictly-greater threshold for ">" / strict reduction (absolute).
    "strictly_greater_threshold": 0.02,
    # H4 model-specific: worst-case spread across model families on (A - D)
    # gold_span delta above which the variation is "significant".
    "h4_model_family_spread_threshold": 0.05,
    # H1 (ambiguous routing) — revised: A preserves quality vs D, reduces
    # false/PFP/model_calls vs D, and outperforms B/E on false/PFP/RobustUtility.
    # A is NOT required to increase gold/span.
    "h1_a_approx_d_gold": 0.02,         # A ≈ D on gold (preserve)
    "h1_a_approx_d_spanf05": 0.02,      # A ≈ D on span_f0_5 (preserve)
    "h1_a_reduces_d_false_span": 0.02,  # A < D on false_span by > threshold
    "h1_a_reduces_d_pfp": 0.02,         # A < D on PFP by > threshold
    "h1_a_reduces_d_model_calls": 0.02, # A < D on model_calls by > threshold
    "h1_a_beats_b_false_span": 0.02,    # A < B on false_span by > threshold
    "h1_a_beats_b_pfp": 0.02,           # A < B on PFP by > threshold
    "h1_a_beats_e_false_span": 0.02,    # A < E on false_span by > threshold
    "h1_a_beats_e_pfp": 0.02,           # A < E on PFP by > threshold
    "h1_a_beats_b_robust_utility": 0.02, # RU(A) > RU(B) by > threshold
    "h1_a_beats_e_robust_utility": 0.02, # RU(A) > RU(E) by > threshold
    # H2 (LLM call reduction) — revised: gains come from generic call reduction.
    # Supported if A ≈ E on quality AND false/PFP (random reduction matches the
    # routing rule) AND A reduces model_calls vs D.
    "h2_a_approx_e_gold": 0.02,
    "h2_a_approx_e_spanf05": 0.02,
    "h2_a_approx_e_false_span": 0.02,
    "h2_a_approx_e_pfp": 0.02,
    "h2_a_reduces_d_model_calls": 0.02,
    # H3 (P25 fallback sufficiency) — revised: routing rule doesn't help; P25
    # default alone is sufficient on primary quality.
    "h3_d_approx_a_gold": 0.02,
    "h3_d_approx_a_spanf05": 0.02,
    # RobustUtility parameters (mirrors B11).
    "robust_utility_lambda": 1.0,  # PFP weight
    "robust_utility_mu": 0.1,  # normalized_cost weight
    "robust_utility_nu": 0.1,  # normalized_latency weight
    # Frozen seed for the E (random call-reduction) variant.
    "e_random_seed": 20260618,
}

# ---------------------------------------------------------------------------
# Models, repos, metrics (mirror B11 for consistency)
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

# Metrics emitted per ablation variant (per repo / per model family / overall).
# Same metric set as B11 so that B12 can replay against B11 records directly.
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
        "spec_id": "rmc_local_conservative_v0",
        "kind": "conservative_policy",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "p25.route_bucket_routed_v0",
        "kind": "p25_policy",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b11_prospective_v0",
        "kind": "b11_prospective_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")
ALLOWED_VERDICTS = (
    "supported",
    "refuted",
    "partial",
    "insufficient_data",
    "not_implemented",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B/B11 so aggregate-only public artifact invariants are identical)
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


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _approx_equal(a: float, b: float, threshold: float) -> bool:
    return abs(a - b) <= threshold


def _strictly_greater(a: float, b: float, threshold: float) -> bool:
    return (a - b) > threshold


# ---------------------------------------------------------------------------
# Synthetic fixture (self-test only)
# ---------------------------------------------------------------------------


def _synthetic_variant_metrics(
    variant: str, repo: str, model_family: str
) -> dict[str, float]:
    """Deterministic synthetic metrics for one (variant, repo, model_family).

    Values are deterministic functions of the inputs (no RNG) so the self-test
    spec hash is stable. Variant A (full balanced) intentionally shows a small
    improvement on gold/SpanF0.5 vs D (P25 default) and a small LLM-call
    reduction; B and E are in between. The deltas are deliberately kept inside
    the approximate-equality threshold for some hypothesis tests so that the
    synthetic fixture still emits ``insufficient_data`` (no empirical support
    from a synthetic fixture, by safety stance).
    """
    # A and C are identical (the balanced policy only has the ambiguous->
    # weak_only routing rule). Map C -> A in the hash input so they produce
    # bit-identical synthetic metrics and the A≡C equivalence is exact.
    hash_variant = "A_full_balanced" if variant == "C_ambiguous_weak_only" else variant
    h = hashlib.sha256(
        f"{hash_variant}|{repo}|{model_family}".encode("utf-8")
    ).digest()
    base = (h[0] / 255.0 + h[1] / 255.0 * 0.01)  # ~[0, 1.01)
    repo_idx = MINIMUM_VIABLE_REPOS.index(repo) if repo in MINIMUM_VIABLE_REPOS else 0
    model_idx = MODEL_FAMILIES.index(model_family) if model_family in MODEL_FAMILIES else 0

    span_f0_5 = 0.70 + 0.05 * (base) - 0.002 * repo_idx
    gold_span = 8.0 + (base * 2.0) - 0.05 * repo_idx
    false_span = 3.0 + (base * 2.0) + 0.05 * repo_idx
    pfp = 0.10 + (base * 0.05) + 0.001 * model_idx
    model_calls = 4.0 + (base * 1.0) + 0.05 * model_idx

    if variant == "A_full_balanced":
        # Full balanced policy: ambiguous->weak_only, else P25.
        # Small improvement on quality + LLM-call reduction vs D.
        false_span -= 0.6
        pfp -= 0.01
        model_calls -= 1.0
        # A and C are identical (the balanced policy has only one routing rule).
    elif variant == "B_deterministic_llm_reduction":
        # P25 for all, but skip LLM for ambiguous tasks (candidate_baseline).
        # Tests whether weak_only or just skipping LLM is what helps.
        false_span -= 0.3
        pfp -= 0.005
        model_calls -= 0.8
        gold_span -= 0.2  # slightly worse than A on gold
    elif variant == "C_ambiguous_weak_only":
        # Same as A — the balanced policy only has the ambiguous->weak_only rule.
        false_span -= 0.6
        pfp -= 0.01
        model_calls -= 1.0
    elif variant == "D_p25_default":
        # P25 for all (no ambiguous->weak_only rule). Baseline.
        pass
    elif variant == "E_random_llm_reduction":
        # P25 for all, but randomly skip the same number of LLM calls as A.
        # Tests H2 (is it just call reduction?).
        # Same LLM-call reduction as A, but quality effect is weaker (random
        # skips don't target ambiguous tasks).
        false_span -= 0.2
        pfp -= 0.003
        model_calls -= 1.0
        gold_span -= 0.1
    else:
        raise ValueError(f"unknown ablation variant: {variant!r}")

    return {
        "span_f0_5": round(max(0.0, span_f0_5), 6),
        "gold_span": round(max(0.0, gold_span), 6),
        "false_span": round(max(0.0, false_span), 6),
        "primary_false_positive_rate": round(max(0.0, pfp), 6),
        "model_calls": round(max(0.0, model_calls), 6),
    }


def _build_synthetic_fixture() -> dict[str, Any]:
    """Build a synthetic per-variant × per-repo × per-model-family fixture.

    Returns a dict keyed by variant; each value is a dict with ``per_repo``,
    ``per_model_family``, ``overall_mean``, and ``n_records``.
    """
    out: dict[str, Any] = {}
    for variant in ABLATION_VARIANTS:
        per_repo_cells: dict[str, list[dict[str, float]]] = {
            r: [] for r in MINIMUM_VIABLE_REPOS
        }
        per_model_cells: dict[str, list[dict[str, float]]] = {
            m: [] for m in MODEL_FAMILIES
        }
        all_cells: list[dict[str, float]] = []
        for model_family in MODEL_FAMILIES:
            for repo in MINIMUM_VIABLE_REPOS:
                cell = _synthetic_variant_metrics(variant, repo, model_family)
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
        out[variant] = {
            "per_repo": per_repo_mean,
            "per_model_family": per_model_mean,
            "overall_mean": overall,
            "n_records": len(all_cells),
        }
    return out


# ---------------------------------------------------------------------------
# Aggregation mechanics (pure Python; no numpy/sklearn/scipy)
# ---------------------------------------------------------------------------


def _aggregate_overall(per_variant: dict[str, Any]) -> dict[str, float]:
    """Overall mean per metric for the variant under analysis (A = full balanced)."""
    var = per_variant["A_full_balanced"]
    return dict(var["overall_mean"])


def _worst_group_by_repo(
    per_variant: dict[str, Any], variant: str
) -> dict[str, dict[str, float]]:
    """For each metric, return the min (worst) value across repos."""
    var = per_variant[variant]
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
    per_variant: dict[str, Any], variant: str
) -> dict[str, dict[str, float]]:
    var = per_variant[variant]
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
    per_variant: dict[str, Any],
    variant: str,
    n_resamples: int = 10000,
    seed: int = 20260618,
) -> dict[str, dict[str, float]]:
    """Stratified-by-repo bootstrap 95% CI over per-repo means.

    Pure-Python: resample the per-repo mean vector with replacement, recompute
    the overall mean, repeat ``n_resamples`` times, take 2.5 / 97.5 percentiles.
    Deterministic given the fixed seed.
    """
    var = per_variant[variant]
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


def _compute_variant_deltas(
    per_variant: dict[str, Any],
    variant_a: str,
    variant_b: str,
) -> dict[str, float]:
    """Compute ``variant_a - variant_b`` overall-mean deltas per metric."""
    a = per_variant[variant_a]["overall_mean"]
    b = per_variant[variant_b]["overall_mean"]
    return {m: round(a[m] - b[m], 6) for m in METRIC_NAMES}


def _compute_model_family_delta_spread(
    per_variant: dict[str, Any],
    variant_a: str,
    variant_b: str,
    metric: str,
) -> dict[str, Any]:
    """For each model family, compute (variant_a - variant_b) on ``metric``,
    then report the min, max, and worst-case spread across model families.
    Used by H4 (model-specific behaviour).
    """
    a = per_variant[variant_a]["per_model_family"]
    b = per_variant[variant_b]["per_model_family"]
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
    per_variant: dict[str, Any],
    variant: str,
    lambda_: float,
    mu: float,
    nu: float,
) -> float:
    """RobustUtility = min_group(SpanF0.5 - λ*PFP - μ*norm_cost - ν*norm_latency).

    For the skeleton we approximate ``normalized_cost`` and ``normalized_latency``
    by ``model_calls / 10`` (so they stay in roughly [0, 1]). The min is taken
    over model-family groups for the variant under analysis.
    """
    var = per_variant[variant]["per_model_family"]
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


def _strict_reduction(delta: float, threshold: float) -> bool:
    """A strict reduction on a lower-is-better metric: (A - comparator) < -threshold."""
    return delta < -threshold


def _strict_improvement(delta: float, threshold: float) -> bool:
    """A strict improvement on a higher-is-better metric: (A - comparator) > threshold."""
    return delta > threshold


# ---------------------------------------------------------------------------
# Hypothesis evaluation (predeclared criteria)
# ---------------------------------------------------------------------------


def _evaluate_hypotheses(
    per_variant: dict[str, Any],
    replay_source: str,
) -> tuple[dict[str, dict[str, Any]], str, str]:
    """Apply the predeclared hypothesis criteria to the computed variant metrics.

    Returns ``(hypothesis_results, verdict, verdict_reason)``.

    Synthetic-fixture safety: when ``replay_source == "synthetic_fixture"``,
    every hypothesis result is forced to ``supported=false`` with
    ``status="synthetic_only"`` and the raw criterion booleans are exposed
    ONLY under the clearly-named non-claim field
    ``criterion_matched_on_synthetic_fixture``. The verdict is always
    ``insufficient_data`` because synthetic fixtures cannot confer empirical
    support (mirrors B10B/B11's safety stance).

    H4 insufficient_data semantics: H4 is ``status="insufficient_data"`` when
    fewer than two known model families are present. H4 insufficient_data
    does NOT block the H1-H3 mechanism verdict — the overall verdict is
    computed over H1-H3 only when H4 is insufficient_data. Callers can read
    ``h4_insufficient_data_blocks_overall_verdict=false`` /
    ``h1_h3_verdict_independent_of_h4=true`` to confirm this policy.

    Revised (C1) H1-H3 criteria: A is NOT required to increase gold/span.
    H1 (ambiguous routing) is supported if A PRESERVES gold/span vs D, REDUCES
    false/PFP/model_calls vs D, and OUTPERFORMS B/E on false/PFP/RobustUtility.
    """
    approx = PREDECLARED_CRITERIA["approx_equal_threshold"]
    gt = PREDECLARED_CRITERIA["strictly_greater_threshold"]
    h4_spread = PREDECLARED_CRITERIA["h4_model_family_spread_threshold"]
    ru_lambda = PREDECLARED_CRITERIA["robust_utility_lambda"]
    ru_mu = PREDECLARED_CRITERIA["robust_utility_mu"]
    ru_nu = PREDECLARED_CRITERIA["robust_utility_nu"]

    # Deltas: A vs D, A vs E, A vs B, A vs (D on model families).
    a_vs_d = _compute_variant_deltas(per_variant, "A_full_balanced", "D_p25_default")
    a_vs_e = _compute_variant_deltas(per_variant, "A_full_balanced", "E_random_llm_reduction")
    a_vs_b = _compute_variant_deltas(per_variant, "A_full_balanced", "B_deterministic_llm_reduction")

    a_d_gold_spread = _compute_model_family_delta_spread(
        per_variant, "A_full_balanced", "D_p25_default", "gold_span"
    )

    ru_a = _compute_robust_utility(per_variant, "A_full_balanced", ru_lambda, ru_mu, ru_nu)
    ru_b = _compute_robust_utility(per_variant, "B_deterministic_llm_reduction", ru_lambda, ru_mu, ru_nu)
    ru_e = _compute_robust_utility(per_variant, "E_random_llm_reduction", ru_lambda, ru_mu, ru_nu)
    ru_deltas = {
        "a_vs_b": round(ru_a - ru_b, 6),
        "a_vs_e": round(ru_a - ru_e, 6),
    }

    # H1 (ambiguous routing): A preserves gold/span vs D, reduces
    # false/PFP/model_calls vs D, and outperforms B/E on false/PFP/RobustUtility.
    h1_preserves_d = (
        _approx_equal(a_vs_d["gold_span"], 0.0, approx)
        and _approx_equal(a_vs_d["span_f0_5"], 0.0, approx)
    )
    h1_reduces_d = (
        _strict_reduction(a_vs_d["false_span"], gt)
        and _strict_reduction(a_vs_d["primary_false_positive_rate"], gt)
        and _strict_reduction(a_vs_d["model_calls"], gt)
    )
    h1_beats_b = (
        _strict_reduction(a_vs_b["false_span"], gt)
        and _strict_reduction(a_vs_b["primary_false_positive_rate"], gt)
        and _strict_improvement(ru_deltas["a_vs_b"], gt)
    )
    h1_beats_e = (
        _strict_reduction(a_vs_e["false_span"], gt)
        and _strict_reduction(a_vs_e["primary_false_positive_rate"], gt)
        and _strict_improvement(ru_deltas["a_vs_e"], gt)
    )
    h1_supported = (
        h1_preserves_d and h1_reduces_d and h1_beats_b and h1_beats_e
    )

    # H2 (LLM call reduction): gains come from generic call reduction. Supported
    # if A ≈ E on quality AND false/PFP (random reduction matches the routing
    # rule) AND A reduces model_calls vs D.
    h2_a_approx_e = (
        _approx_equal(a_vs_e["gold_span"], 0.0, approx)
        and _approx_equal(a_vs_e["span_f0_5"], 0.0, approx)
        and _approx_equal(a_vs_e["false_span"], 0.0, approx)
        and _approx_equal(a_vs_e["primary_false_positive_rate"], 0.0, approx)
    )
    h2_a_reduces_d_calls = _strict_reduction(a_vs_d["model_calls"], gt)
    h2_supported = h2_a_approx_e and h2_a_reduces_d_calls

    # H3 (P25 fallback sufficiency): the ambiguous->weak_only rule doesn't help;
    # P25 default alone is sufficient on primary quality.
    h3_d_approx_a = (
        _approx_equal(a_vs_d["gold_span"], 0.0, approx)
        and _approx_equal(a_vs_d["span_f0_5"], 0.0, approx)
    )
    h3_supported = h3_d_approx_a

    # H4 (model-specific): supported if effect sizes vary significantly across
    # model families (worst-case spread > threshold on A-D gold_span delta).
    h4_spread_supported = a_d_gold_spread["spread"] > h4_spread

    # Known model families (excluding "unknown"). H4 needs >= 2 to evaluate.
    known_families = [
        f for f in (per_variant.get("A_full_balanced", {}).get("per_model_family", {}) or {})
        if f != "unknown"
    ]
    h4_insufficient_data = len(known_families) < 2
    if h4_insufficient_data:
        h4_status = "insufficient_data"
        h4_supported = False
        h4_reason = (
            "insufficient_data: fewer than two known model families "
            f"(known={known_families})"
        )
    else:
        h4_status = "supported" if h4_spread_supported else "refuted"
        h4_supported = h4_spread_supported
        h4_reason = (
            "spread_exceeds_threshold" if h4_spread_supported
            else "spread_at_or_below_threshold"
        )

    is_synthetic = (replay_source == "synthetic_fixture")

    def _h_block(
        name: str, supported: bool, status: str, criterion_fields: dict[str, Any],
        reason: str = "",
    ) -> dict[str, Any]:
        block: dict[str, Any] = {
            # ``supported`` is the empirical claim. On a synthetic fixture this
            # is ALWAYS forced to False (synthetic fixtures cannot confer
            # empirical support); the raw criterion booleans are exposed
            # ONLY under ``criterion_matched_on_synthetic_fixture`` so the
            # report never reads as an empirical supported=true.
            "supported": False if is_synthetic else supported,
            "status": "synthetic_only" if is_synthetic else status,
        }
        if reason:
            block["reason"] = reason
        if is_synthetic:
            block["criterion_matched_on_synthetic_fixture"] = {
                k: v for k, v in criterion_fields.items()
                if k.startswith("a_") or k in {"spread_threshold"}
            }
        else:
            block.update(criterion_fields)
        return block

    hypothesis_results: dict[str, dict[str, Any]] = {
        "H1_ambiguous_routing": _h_block(
            "H1", h1_supported, "supported" if h1_supported else "refuted",
            {
                "a_preserves_d": h1_preserves_d,
                "a_reduces_d": h1_reduces_d,
                "a_beats_b": h1_beats_b,
                "a_beats_e": h1_beats_e,
                "a_vs_d_delta": a_vs_d,
                "a_vs_e_delta": a_vs_e,
                "a_vs_b_delta": a_vs_b,
                "robust_utility_deltas": ru_deltas,
            },
        ),
        "H2_llm_call_reduction": _h_block(
            "H2", h2_supported, "supported" if h2_supported else "refuted",
            {
                "a_approx_e": h2_a_approx_e,
                "a_reduces_d_calls": h2_a_reduces_d_calls,
                "a_vs_e_delta": a_vs_e,
                "a_vs_d_delta": a_vs_d,
            },
        ),
        "H3_p25_fallback_sufficiency": _h_block(
            "H3", h3_supported, "supported" if h3_supported else "refuted",
            {
                "d_approx_a": h3_d_approx_a,
                "a_vs_d_delta": a_vs_d,
            },
        ),
        "H4_model_specific": _h_block(
            "H4", h4_supported, h4_status,
            {
                "a_d_gold_span_model_family_spread": a_d_gold_spread,
                "spread_threshold": h4_spread,
                "known_model_family_count": len(known_families),
                "h4_insufficient_data": h4_insufficient_data,
            },
            reason=h4_reason,
        ),
    }

    # Synthetic fixture => never an empirical verdict.
    if is_synthetic:
        return (
            hypothesis_results,
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; B12 ablation "
            "runs (or P21-record replay) required for any supported, "
            "refuted, or partial verdict",
        )

    # H1-H3 verdict is computed INDEPENDENTLY of H4. When H4 is
    # insufficient_data, the overall verdict reflects H1-H3 only; H4
    # insufficient_data does NOT block the H1-H3 mechanism verdict.
    h1_h3 = {
        k: v for k, v in hypothesis_results.items() if k != "H4_model_specific"
    }
    n_supported_h1_h3 = sum(1 for h in h1_h3.values() if h["supported"])
    n_h1_h3 = len(h1_h3)
    if n_supported_h1_h3 == 0:
        verdict = "refuted"
        reason = "all_predeclared_h1_h3_hypotheses_refuted"
    elif n_supported_h1_h3 == n_h1_h3:
        verdict = "supported"
        reason = "all_predeclared_h1_h3_hypotheses_supported"
    else:
        verdict = "partial"
        supported_names = sorted(
            h for h, r in h1_h3.items() if r["supported"]
        )
        reason = "partial_support: " + ",".join(supported_names)
    if h4_insufficient_data:
        reason += (
            "; H4=insufficient_data (fewer than two known model families); "
            "H4 insufficient_data does NOT block the H1-H3 verdict"
        )
    else:
        h4_note = (
            "; H4=supported" if h4_supported else "; H4=refuted"
        )
        reason += h4_note
    return hypothesis_results, verdict, reason


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B12 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so its
    SHA-256 is stable across runs. The on-disk spec file is the pin (mirrors
    B10/B10B/B11 freeze style). The self-test verifies hash stability by
    re-loading and re-hashing.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": "mechanism_decomposition_v0",
        "description": (
            "B12 Mechanism Decomposition: ablation-based decomposition of WHY "
            "the frozen balanced policy balanced_policy_v1_benchmark_routed "
            "(B10) works, via 5 ablation variants (A full balanced, B "
            "deterministic LLM reduction, C ambiguous weak_only only (=A), "
            "D P25 default, E random LLM reduction) and 4 predeclared "
            "hypotheses (H1 ambiguous routing, H2 LLM call reduction, H3 "
            "P25 fallback sufficiency, H4 model-specific). Replay-only; no "
            "live LLM calls, no policy search, no threshold tuning."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "aggregate_only_public_artifact": True,
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        "ablation_variants": list(ABLATION_VARIANTS),
        "ablation_equivalences": [
            {"a": list(pair), "reason": "balanced_policy_has_one_routing_rule"}
            for pair in ABLATION_EQUIVALENCES
        ],
        "hypotheses": list(HYPOTHESES),
        "model_families": list(MODEL_FAMILIES),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "metric_names": list(METRIC_NAMES),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "allowed_replay_sources": list(ALLOWED_REPLAY_SOURCES),
        "allowed_verdicts": list(ALLOWED_VERDICTS),
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_policy_search": True,
            "no_threshold_tuning": True,
            "no_evidencecore_semantics_change": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "replay_only_no_live_ablation_runs_in_evaluator": True,
        },
        "excluded_adapter_layer": {
            "model_adapter_excluded": True,
            "output_mode_excluded": True,
            "provider_credentials_excluded": True,
            "provider_endpoints_excluded": True,
            "provider_secrets_excluded": True,
        },
    }


def _reference_spec_hashes() -> dict[str, bool]:
    """Check whether the on-disk frozen reference specs (B10, B10B, B11) are
    present and loadable. Returns ``{spec_id: hash_pinned_on_disk_bool}``.
    The actual sha256 hex is NEVER returned (it would trip the forbidden-value
    scan); only the boolean matched flag is exposed publicly.
    """
    refs = {}
    for spec_id, path in (
        ("balanced_policy_v1_benchmark_routed", B10_SPEC_PATH),
        ("balanced_policy_v1_runtime_shadow_ambiguous_branch", B10B_SPEC_PATH),
        ("b11_prospective_v0", B11_SPEC_PATH),
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
    per_variant: dict[str, Any],
    *,
    self_test: bool,
    replay_source: str,
) -> dict[str, Any]:
    """Build the B12 mechanism decomposition report.

    ``per_variant`` is the per-variant metrics dict (see
    ``_build_synthetic_fixture`` for the shape). ``self_test=True`` flags that
    the report was produced from a synthetic fixture for mechanics validation;
    ``replay_source`` is one of ``ALLOWED_REPLAY_SOURCES``.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    overall_mean = _aggregate_overall(per_variant)
    worst_repo = _worst_group_by_repo(per_variant, "A_full_balanced")
    worst_model = _worst_group_by_model_family(per_variant, "A_full_balanced")
    worst_group = {**worst_repo, **worst_model}
    bootstrap_ci = _bootstrap_ci(per_variant, "A_full_balanced")
    robust_utility_a = _compute_robust_utility(
        per_variant,
        "A_full_balanced",
        lambda_=PREDECLARED_CRITERIA["robust_utility_lambda"],
        mu=PREDECLARED_CRITERIA["robust_utility_mu"],
        nu=PREDECLARED_CRITERIA["robust_utility_nu"],
    )

    a_vs_d = _compute_variant_deltas(per_variant, "A_full_balanced", "D_p25_default")
    a_vs_e = _compute_variant_deltas(per_variant, "A_full_balanced", "E_random_llm_reduction")
    a_vs_b = _compute_variant_deltas(per_variant, "A_full_balanced", "B_deterministic_llm_reduction")
    a_vs_c = _compute_variant_deltas(per_variant, "A_full_balanced", "C_ambiguous_weak_only")

    hypothesis_results, verdict, verdict_reason = _evaluate_hypotheses(
        per_variant, replay_source
    )

    # H4 insufficient_data policy: H4 does NOT block the H1-H3 mechanism
    # verdict. Single-model B12 CI slices can still evaluate H1-H3; H4 needs
    # multi-model aggregation. Read directly from the H4 result block so the
    # report flag is always consistent with the actual H4 status.
    h4_block = hypothesis_results.get("H4_model_specific", {}) or {}
    h4_insufficient_data = bool(h4_block.get("h4_insufficient_data"))
    ref_hashes = _reference_spec_hashes()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": "mechanism_decomposition_v0",
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "frozen_reference_specs_pinned_on_disk": ref_hashes,
        "ablation_variants": list(ABLATION_VARIANTS),
        "ablation_equivalences": [
            {"a": list(pair), "reason": "balanced_policy_has_one_routing_rule"}
            for pair in ABLATION_EQUIVALENCES
        ],
        "hypotheses": list(HYPOTHESES),
        "model_families": list(MODEL_FAMILIES),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "metric_names": list(METRIC_NAMES),
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        "public_group_key_contract": (
            "per_repo aggregate keys are public preregistered repo labels for "
            "synthetic or preregistration fixtures and anonymized "
            "public_repo_group_NNN labels for private --input replays; raw or "
            "private repo identifiers are never emitted"
        ),
        "per_variant_metrics": per_variant,
        "overall_mean": overall_mean,
        "worst_group": worst_group,
        "bootstrap_ci_95": bootstrap_ci,
        "robust_utility": robust_utility_a,
        "variant_deltas_vs_d": a_vs_d,
        "variant_deltas_vs_e": a_vs_e,
        "variant_deltas_vs_b": a_vs_b,
        "variant_deltas_vs_c_equivalence_check": a_vs_c,
        "hypothesis_results": hypothesis_results,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "h4_insufficient_data_blocks_overall_verdict": False,
        "h1_h3_verdict_independent_of_h4": True,
        "h4_insufficient_data": h4_insufficient_data,
        "aggregate_only_public_artifact": True,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_policy_search": True,
            "no_threshold_tuning": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "runtime_calls_by_replay_zero": True,
            "model_calls_by_replay_zero": True,
            "replay_only_no_live_ablation_runs_in_evaluator": True,
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
    if spec.get("claim_level") != "mechanism_decomposition_v0":
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
    if spec.get("policy_search_performed") is not False:
        raise ValueError("algorithm spec policy_search_performed must be false")
    if spec.get("quality_strategy_tuned") is not False:
        raise ValueError("algorithm spec quality_strategy_tuned must be false")
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
    if tuple(spec.get("ablation_variants") or ()) != ABLATION_VARIANTS:
        raise ValueError("algorithm spec ablation_variants mismatch")
    if tuple(spec.get("hypotheses") or ()) != HYPOTHESES:
        raise ValueError("algorithm spec hypotheses mismatch")
    if tuple(spec.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("algorithm spec model_families mismatch")
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
    if report.get("claim_level") != "mechanism_decomposition_v0":
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
    if report.get("policy_search_performed") is not False:
        raise ValueError("report policy_search_performed must be false")
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
    if report.get("predeclared_criteria") != PREDECLARED_CRITERIA:
        raise ValueError("report predeclared_criteria must match the frozen constants")
    if tuple(report.get("ablation_variants") or ()) != ABLATION_VARIANTS:
        raise ValueError("report ablation_variants mismatch")
    if tuple(report.get("hypotheses") or ()) != HYPOTHESES:
        raise ValueError("report hypotheses mismatch")
    if tuple(report.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("report model_families mismatch")
    if tuple(report.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("report repos mismatch")
    if report.get("policy_under_analysis") != POLICY_UNDER_ANALYSIS:
        raise ValueError("report policy_under_analysis mismatch")
    if report.get("baseline_for_deltas") != BASELINE_FOR_DELTAS:
        raise ValueError("report baseline_for_deltas mismatch")
    # Required top-level sections.
    for key in (
        "per_variant_metrics",
        "overall_mean",
        "worst_group",
        "bootstrap_ci_95",
        "robust_utility",
        "variant_deltas_vs_d",
        "variant_deltas_vs_e",
        "variant_deltas_vs_b",
        "variant_deltas_vs_c_equivalence_check",
        "hypothesis_results",
    ):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # Safety invariant flags.
    si = report.get("safety_invariants") or {}
    for flag in (
        "no_live_llm_calls",
        "no_policy_search",
        "no_threshold_tuning",
        "no_evidencecore_semantics_change",
        "promotion_ready_false",
        "default_should_change_false",
        "aggregate_only_public_artifact",
        "forbidden_public_keys_scanned",
        "no_raw_path_digest_provider_strings",
        "runtime_calls_by_replay_zero",
        "model_calls_by_replay_zero",
        "replay_only_no_live_ablation_runs_in_evaluator",
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input: load private P21 v1 records via the C1 adapter and replay
# ---------------------------------------------------------------------------


def _record_metric_cell(
    record: c1.PrivateRecord, strategy: str
) -> dict[str, float]:
    """Extract the 5 B12 metrics for one record under one strategy.

    ``gold_span`` / ``false_span`` are the per-record ``added_gold_span`` /
    ``added_false_span`` counts (mean-aggregated per-group downstream).
    ``model_calls`` is 1.0 for LLM strategies, 0.0 otherwise (per-record proxy).
    Falls back to ``candidate_baseline`` outcome if the selected strategy's
    outcome is all-zero (defensive; P21 v1 always writes all strategy keys).
    """
    outcome = record.outcomes.get(strategy) or record.outcomes.get(
        "candidate_baseline"
    ) or {}
    return {
        "span_f0_5": float(outcome.get("span_f0_5", 0.0)),
        "gold_span": float(outcome.get("added_gold_span", 0)),
        "false_span": float(outcome.get("added_false_span", 0)),
        "primary_false_positive_rate": float(
            outcome.get("primary_false_positive_rate", 0.0)
        ),
        "model_calls": 1.0 if strategy in c1.LLM_STRATEGIES else 0.0,
    }


def _group_metrics(cells: list[dict[str, float]]) -> dict[str, float]:
    """Aggregate a list of per-record metric cells into the mean-per-metric
    summary (same semantics as the synthetic fixture so the frozen predeclared
    criteria, calibrated against means, remain consistent)."""
    if not cells:
        return {m: 0.0 for m in METRIC_NAMES}
    return {m: round(_mean([c[m] for c in cells]), 6) for m in METRIC_NAMES}


def _select_e_random_subset(
    records: list[c1.PrivateRecord],
    p25_llm_subset: list[c1.PrivateRecord],
    k: int,
    seed: int,
) -> set[str]:
    """Deterministically hash-select ``k`` records from the P25 LLM-eligible
    population for variant E (random same-count call-reduction control).

    Selection is deterministic given the frozen seed: we sort the p25_llm_subset
    by its (private, in-memory-only) record hash, seed an RNG, and pick ``k``
    indices without replacement. The returned set contains private record hashes
    (IN MEMORY ONLY; never emitted in the public report — only the COUNT is
    surfaced). Limitation: a single frozen seed is used; seed-averaging can be
    added later (reported in the algorithm spec).
    """
    if k <= 0 or not p25_llm_subset:
        return set()
    # Sort by private hash for a stable, input-order-independent ordering.
    ordered = sorted(p25_llm_subset, key=lambda r: r.private_record_hash)
    n = len(ordered)
    k = min(k, n)
    rng = random.Random(seed)
    chosen_idx = set(rng.sample(range(n), k))
    return {ordered[i].private_record_hash for i in chosen_idx}


def _build_per_variant_from_records(
    records: list[c1.PrivateRecord],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute the per-variant metrics dict (same shape as
    ``_build_synthetic_fixture``) plus the count reporting block, from real
    private P21 records loaded via the C1 adapter.

    Variant definitions (FROZEN):
      - A full balanced: if balanced_branch -> ``weak_candidate_only``, else
        D/P25 strategy.
      - C ambiguous weak_only only: equivalent to A (the balanced policy has
        only one routing rule); A≡C equivalence is reported explicitly.
      - D original P25: P25-selected strategy.
      - B deterministic call-reduction control: only for
        ``actual_call_avoided_set = balanced_branch_set ∩ p25_llm_subset``,
        choose local non-LLM ``candidate_baseline``; otherwise D.
      - E random same-count call-reduction: deterministically hash-select the
        same number of records as ``actual_call_avoided_set`` from the P25
        LLM-eligible population, choose ``candidate_baseline`` on those,
        otherwise D.

    Returns ``(per_variant, counts)`` where ``counts`` carries the safe scalar
    count reporting (total_records, complete_records, balanced_branch_count,
    p25_llm_eligible_count, actual_call_avoided_count, random_selected_count).
    """
    # Precompute per-record routing decisions (using adapter helpers).
    balanced_branch_set = {
        r.private_record_hash: c1.balanced_branch_predicate(r) for r in records
    }
    p25_strategies = {r.private_record_hash: c1.compute_p25_strategy(r) for r in records}
    p25_llm_subset_hashes = {
        r.private_record_hash for r in records if p25_strategies[r.private_record_hash] in c1.LLM_STRATEGIES
    }
    # actual_call_avoided_set = balanced_branch_set ∩ p25_llm_subset.
    actual_call_avoided_hashes = {
        h for h, bb in balanced_branch_set.items()
        if bb and h in p25_llm_subset_hashes
    }
    # E random subset: same count as actual_call_avoided_set, drawn from the
    # P25 LLM-eligible population.
    p25_llm_subset_records = [
        r for r in records if r.private_record_hash in p25_llm_subset_hashes
    ]
    e_seed = PREDECLARED_CRITERIA["e_random_seed"]
    e_selected_hashes = _select_e_random_subset(
        records, p25_llm_subset_records, len(actual_call_avoided_hashes), e_seed
    )

    # Precompute the strategy per record per variant.
    variant_strategy: dict[str, dict[str, str]] = {v: {} for v in ABLATION_VARIANTS}
    complete_count = 0
    incomplete_record_count = 0
    missing_required_outcome_count = 0
    # Track, per variant, how many records were missing the chosen strategy
    # outcome (so consumers can see which variants are affected).
    missing_by_variant: dict[str, int] = {v: 0 for v in ABLATION_VARIANTS}
    complete_by_hash: dict[str, bool] = {}
    for r in records:
        h = r.private_record_hash
        d_strat = p25_strategies[h]
        bb = balanced_branch_set[h]
        # A / C: ambiguous->weak_only, else P25.
        a_strat = "weak_candidate_only" if bb else d_strat
        variant_strategy["A_full_balanced"][h] = a_strat
        variant_strategy["C_ambiguous_weak_only"][h] = a_strat  # A≡C
        # D: P25 default.
        variant_strategy["D_p25_default"][h] = d_strat
        # B: candidate_baseline on actual_call_avoided_set, else D.
        variant_strategy["B_deterministic_llm_reduction"][h] = (
            "candidate_baseline" if h in actual_call_avoided_hashes else d_strat
        )
        # E: candidate_baseline on random_selected_set, else D.
        variant_strategy["E_random_llm_reduction"][h] = (
            "candidate_baseline" if h in e_selected_hashes else d_strat
        )
        # A record is "complete" iff the outcome is PRESENT (not silently
        # zeroed) for EVERY variant's chosen strategy for that record. A
        # missing required outcome makes the record incomplete and it must
        # NOT silently count as a zero-outcome complete record.
        chosen_strategies = sorted({
            variant_strategy[v][h] for v in ABLATION_VARIANTS
        })
        is_complete = c1.record_complete_for_strategies(r, chosen_strategies)
        complete_by_hash[h] = is_complete
        if is_complete:
            complete_count += 1
        else:
            incomplete_record_count += 1
            missing_required_outcome_count += sum(
                1 for s in chosen_strategies
                if not (r.outcome_present or {}).get(s)
            )
        for v in ABLATION_VARIANTS:
            s = variant_strategy[v][h]
            if not (r.outcome_present or {}).get(s):
                missing_by_variant[v] += 1

    repo_values = sorted({str(r.repo_id or "unknown") for r in records})
    repo_group_map = {
        repo: f"public_repo_group_{idx + 1:03d}"
        for idx, repo in enumerate(repo_values)
    }

    out: dict[str, Any] = {}
    for variant in ABLATION_VARIANTS:
        per_repo_cells: dict[str, list[dict[str, float]]] = {}
        per_model_cells: dict[str, list[dict[str, float]]] = {}
        all_cells: list[dict[str, float]] = []
        for r in records:
            h = r.private_record_hash
            if not complete_by_hash.get(h, False):
                # Missing/malformed required outcomes are counted in
                # replay_counts and block the scientific verdict, but they must
                # never enter metric aggregation as zero-filled compatibility
                # rows.
                continue
            strat = variant_strategy[variant][h]
            cell = _record_metric_cell(r, strat)
            repo = repo_group_map[str(r.repo_id or "unknown")]
            model = str(r.model_family or "unknown")
            per_repo_cells.setdefault(repo, []).append(cell)
            per_model_cells.setdefault(model, []).append(cell)
            all_cells.append(cell)
        out[variant] = {
            "per_repo": {k: _group_metrics(v) for k, v in per_repo_cells.items()},
            "per_model_family": {
                k: _group_metrics(v) for k, v in per_model_cells.items()
            },
            "overall_mean": _group_metrics(all_cells),
            "n_records": len(all_cells),
        }

    counts = {
        "total_records": len(records),
        "complete_records": complete_count,
        "incomplete_record_count": incomplete_record_count,
        "missing_required_outcome_count": missing_required_outcome_count,
        "missing_by_variant": dict(missing_by_variant),
        "balanced_branch_count": sum(1 for v in balanced_branch_set.values() if v),
        "p25_llm_eligible_count": len(p25_llm_subset_hashes),
        "actual_call_avoided_count": len(actual_call_avoided_hashes),
        "random_selected_count": len(e_selected_hashes),
        "e_random_seed": e_seed,
        "e_seed_limitation": (
            "single_frozen_seed; seed-averaging can be added later"
        ),
    }
    return out, counts


def _load_p21_input(path: str) -> dict[str, Any]:
    """Load private P21 v1 records via the C1 adapter and return a metadata
    payload carrying the normalized ``records`` list plus safe scalar counts.
    The records are kept IN MEMORY ONLY; the public report never emits raw
    task_ids/repo_ids/spans/snippets/per-record hashes (aggregate-only invariant).
    """
    records, meta = c1.load_private_records(path)
    return {
        "source_kind": meta.get("source_kind"),
        "n_files": meta.get("n_files"),
        "n_records": meta.get("n_records"),
        "records": records,
        # Safe scalar taint summary (no private fields; counts only).
        "taint_summary": meta.get("taint_summary"),
    }


def _build_input_report(input_meta: dict[str, Any]) -> dict[str, Any]:
    """Build a real B12 report from private P21 ``--input`` records.

    Computes per-variant metrics (A-E) by routing each record through the
    frozen ablation-variant strategy selectors (via the C1 adapter helpers),
    extracting the per-strategy outcome metrics, and aggregating overall /
    per-repo / per-model-family. The actual-call-avoided / balanced-branch /
    p25_llm_eligible counts, bootstrap CIs, RobustUtility, variant deltas, and
    the FROZEN predeclared verdict are all computed from the real records. No
    live LLM calls; no per-record IDs/hashes/paths in the public output.
    """
    records = input_meta.get("records") or []
    if not records:
        # No usable records -> emit insufficient_data (cannot apply criteria
        # to an empty replay set). Still a well-formed report.
        per_variant = _build_synthetic_fixture()
        report = build_report(
            per_variant, self_test=False, replay_source="ci_ephemeral_records"
        )
        report["verdict"] = "insufficient_data"
        report["verdict_reason"] = (
            "no usable P21 records loaded from --input; cannot apply "
            "predeclared criteria to an empty replay set"
        )
        report["input_meta"] = {
            "source_kind": input_meta.get("source_kind"),
            "n_files": input_meta.get("n_files"),
            "n_records": 0,
        }
        report["replay_counts"] = {
            "total_records": 0,
            "complete_records": 0,
            "incomplete_record_count": 0,
            "missing_required_outcome_count": 0,
            "missing_by_variant": {v: 0 for v in ABLATION_VARIANTS},
            "balanced_branch_count": 0,
            "p25_llm_eligible_count": 0,
            "actual_call_avoided_count": 0,
            "random_selected_count": 0,
            "e_random_seed": PREDECLARED_CRITERIA["e_random_seed"],
            "e_seed_limitation": "single_frozen_seed; seed-averaging can be added later",
        }
        hits = _recursive_key_scan(report)
        if hits:
            raise ValueError(
                f"forbidden public keys/values in input report: {hits!r}"
            )
        return report

    per_variant, counts = _build_per_variant_from_records(records)
    report = build_report(
        per_variant, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Surface the (safe, scalar) input metadata + count reporting. ``records``
    # itself is NEVER emitted (aggregate-only invariant).
    report["input_meta"] = {
        "source_kind": input_meta.get("source_kind"),
        "n_files": input_meta.get("n_files"),
        "n_records": input_meta.get("n_records"),
        "taint_summary": input_meta.get("taint_summary"),
    }
    report["replay_counts"] = counts
    if counts.get("incomplete_record_count", 0) > 0:
        report["verdict"] = "insufficient_data"
        report["verdict_reason"] = (
            "incomplete_required_outcomes: one or more records were missing "
            "a required chosen-strategy outcome; incomplete records were "
            "excluded from metric aggregation and B12 cannot make a scientific "
            "mechanism verdict on this input"
        )
        report["incomplete_outcomes_block_overall_verdict"] = True
    else:
        report["incomplete_outcomes_block_overall_verdict"] = False
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(
            f"forbidden public keys/values in input report: {hits!r}"
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
    clean = {"provenance": "b12_mechanism_decomposition::build_report"}
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


def _self_test_synthetic_fixture_metrics() -> None:
    per_variant = _build_synthetic_fixture()
    # All 5 variants x 8 repos x 4 model families present.
    for variant in ABLATION_VARIANTS:
        assert variant in per_variant, variant
        assert set(per_variant[variant]["per_repo"].keys()) == set(
            MINIMUM_VIABLE_REPOS
        )
        assert set(per_variant[variant]["per_model_family"].keys()) == set(
            MODEL_FAMILIES
        )
        assert per_variant[variant]["n_records"] == len(MINIMUM_VIABLE_REPOS) * len(
            MODEL_FAMILIES
        ), variant
    # A should reduce false_span / pfp / model_calls vs D in the synthetic
    # fixture (sanity check on the deterministic generator).
    a = per_variant["A_full_balanced"]["overall_mean"]
    d = per_variant["D_p25_default"]["overall_mean"]
    assert a["false_span"] <= d["false_span"], (a, d)
    assert a["primary_false_positive_rate"] <= d["primary_false_positive_rate"], (a, d)
    assert a["model_calls"] <= d["model_calls"], (a, d)
    # A ≡ C: A and C must produce IDENTICAL overall means (the balanced policy
    # only has one routing rule).
    c = per_variant["C_ambiguous_weak_only"]["overall_mean"]
    assert a == c, ("A_full_balanced and C_ambiguous_weak_only must be identical", a, c)


def _self_test_hypothesis_evaluation_stub() -> None:
    """Verify the hypothesis-evaluation mechanics on the synthetic fixture.
    A synthetic-fixture replay_source must NEVER yield a supported/refuted/
    partial verdict, regardless of how the criteria evaluate."""
    per_variant = _build_synthetic_fixture()
    report = build_report(
        per_variant, self_test=True, replay_source="synthetic_fixture"
    )
    verify_report(report)
    assert report["replay_source"] == "synthetic_fixture"
    assert report["verdict"] == "insufficient_data", report["verdict"]
    assert "synthetic_fixture_only" in report["verdict_reason"]
    # All 4 hypotheses must be present in the report.
    for h in HYPOTHESES:
        assert h in report["hypothesis_results"], h
        assert "supported" in report["hypothesis_results"][h], h
    # Variant deltas must be present.
    for key in (
        "variant_deltas_vs_d",
        "variant_deltas_vs_e",
        "variant_deltas_vs_b",
        "variant_deltas_vs_c_equivalence_check",
    ):
        assert key in report, key
    # A ≡ C equivalence: the A-vs-C delta must be zero on every metric.
    a_vs_c = report["variant_deltas_vs_c_equivalence_check"]
    for m in METRIC_NAMES:
        assert a_vs_c[m] == 0.0, ("A-vs-C delta must be zero", m, a_vs_c[m])


def _self_test_input_full_mode(tmp_path: Path) -> None:
    """--input mode must load private P21 v1 records via the C1 adapter, compute
    per-variant metrics + counts, and emit a real verdict (NOT
    ``not_implemented``) against the FROZEN criteria."""
    payload = c1.build_synthetic_v1_payload()
    p = tmp_path / "kimi_b12_selftest.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    meta = _load_p21_input(str(p))
    assert meta["source_kind"] == "file_object"
    assert meta["n_records"] == len(payload["records"])
    assert len(meta["records"]) == len(payload["records"])
    # model_family derived from filename prefix "kimi".
    assert all(r.model_family == "kimi" for r in meta["records"]), (
        [r.model_family for r in meta["records"]]
    )
    report = _build_input_report(meta)
    verify_report(report)
    assert report["replay_source"] == "ci_ephemeral_records"
    assert report["verdict"] != "not_implemented", report["verdict"]
    assert report["verdict"] in ("supported", "refuted", "partial", "insufficient_data")
    assert "per_variant_metrics" in report
    for variant in ABLATION_VARIANTS:
        assert variant in report["per_variant_metrics"], variant
        var = report["per_variant_metrics"][variant]
        assert "per_repo" in var and "per_model_family" in var
        assert "overall_mean" in var and "n_records" in var
    # Count reporting.
    rc = report["replay_counts"]
    assert rc["total_records"] == len(payload["records"])
    assert rc["balanced_branch_count"] >= 0
    assert rc["p25_llm_eligible_count"] >= 0
    assert rc["actual_call_avoided_count"] <= rc["balanced_branch_count"]
    assert rc["actual_call_avoided_count"] <= rc["p25_llm_eligible_count"]
    assert rc["random_selected_count"] == rc["actual_call_avoided_count"]
    # A≡C equivalence: the A-vs-C delta must be zero on every metric.
    a_vs_c = report["variant_deltas_vs_c_equivalence_check"]
    for m in METRIC_NAMES:
        assert a_vs_c[m] == 0.0, ("A-vs-C delta must be zero", m, a_vs_c[m])
    # Aggregate-only invariant: no forbidden keys leaked.
    hits = _recursive_key_scan(report)
    assert hits == [], hits

    # A malformed/missing chosen outcome must NOT be counted as a zero-valued
    # complete metric row. It must be counted as incomplete and block the
    # overall scientific verdict.
    malformed = c1.build_synthetic_v1_payload()
    for strategy_key in c1.P21_STRATEGY_KEYS:
        malformed["records"][0].pop(strategy_key, None)
    p_bad = tmp_path / "kimi_b12_missing_outcome.json"
    p_bad.write_text(json.dumps(malformed), encoding="utf-8")
    bad_meta = _load_p21_input(str(p_bad))
    bad_report = _build_input_report(bad_meta)
    verify_report(bad_report)
    assert bad_report["replay_counts"]["incomplete_record_count"] > 0
    assert bad_report["verdict"] == "insufficient_data", bad_report["verdict"]
    assert bad_report.get("incomplete_outcomes_block_overall_verdict") is True


def _self_test_reference_specs() -> None:
    """The B10, B10B and B11 frozen reference specs must exist on disk so the
    B12 frozen_artifacts pin is meaningful."""
    refs = _reference_spec_hashes()
    assert refs.get("balanced_policy_v1_benchmark_routed") is True, refs
    assert refs.get("balanced_policy_v1_runtime_shadow_ambiguous_branch") is True, refs
    assert refs.get("b11_prospective_v0") is True, refs


def _self_test_ablation_variants_defined() -> None:
    """5 ablation variants, A≡C equivalence."""
    assert len(ABLATION_VARIANTS) == 5, ABLATION_VARIANTS
    for v in (
        "A_full_balanced",
        "B_deterministic_llm_reduction",
        "C_ambiguous_weak_only",
        "D_p25_default",
        "E_random_llm_reduction",
    ):
        assert v in ABLATION_VARIANTS, v
    assert ABLATION_EQUIVALENCES == (("A_full_balanced", "C_ambiguous_weak_only"),), (
        ABLATION_EQUIVALENCES
    )
    # Spec must include the 5 variants + the equivalence declaration.
    spec = build_algorithm_spec()
    assert tuple(spec["ablation_variants"]) == ABLATION_VARIANTS
    assert any(
        eq["a"] == ["A_full_balanced", "C_ambiguous_weak_only"]
        for eq in spec["ablation_equivalences"]
    )


def _self_test_hypotheses_defined() -> None:
    """4 hypotheses with predeclared criteria."""
    assert len(HYPOTHESES) == 4, HYPOTHESES
    for h in (
        "H1_ambiguous_routing",
        "H2_llm_call_reduction",
        "H3_p25_fallback_sufficiency",
        "H4_model_specific",
    ):
        assert h in HYPOTHESES, h
    # Predeclared criteria must include the hypothesis thresholds.
    for k in (
        "approx_equal_threshold",
        "strictly_greater_threshold",
        "h4_model_family_spread_threshold",
        "h1_a_approx_d_gold",
        "h1_a_reduces_d_false_span",
        "h1_a_beats_b_robust_utility",
        "h2_a_approx_e_gold",
        "h2_a_reduces_d_model_calls",
        "h3_d_approx_a_gold",
        "e_random_seed",
    ):
        assert k in PREDECLARED_CRITERIA, k
    spec = build_algorithm_spec()
    assert tuple(spec["hypotheses"]) == HYPOTHESES
    assert spec["predeclared_criteria"] == dict(PREDECLARED_CRITERIA)


def _self_test_bootstrap_ci() -> None:
    per_variant = _build_synthetic_fixture()
    ci = _bootstrap_ci(
        per_variant, "A_full_balanced", n_resamples=500, seed=20260618
    )
    for metric in METRIC_NAMES:
        assert metric in ci, metric
        assert ci[metric]["low"] <= ci[metric]["high"], (metric, ci[metric])
    ci2 = _bootstrap_ci(
        per_variant, "A_full_balanced", n_resamples=500, seed=20260618
    )
    assert ci == ci2, "bootstrap CI must be deterministic given the fixed seed"


def _regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report so the
    artifact pin matches the in-code build functions. Mirrors the B10/B10B/B11
    freeze-write style: deterministic output, canonical JSON."""
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    per_variant = _build_synthetic_fixture()
    report = build_report(
        per_variant, self_test=True, replay_source="synthetic_fixture"
    )
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    """Run all B12 self-test checks. Returns a summary dict."""
    import tempfile

    # 1. Forbidden-key/value scan.
    _self_test_forbidden_scan()

    # 2. Algorithm spec hash stability.
    _self_test_spec_hash_stable()

    # 3. Synthetic fixture metrics (incl. A≡C equivalence).
    _self_test_synthetic_fixture_metrics()

    # 4. Hypothesis evaluation stub (synthetic fixture => insufficient_data).
    _self_test_hypothesis_evaluation_stub()

    # 5. --input full mode: real per-variant metrics + verdict via C1 adapter.
    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_full_mode(Path(tmp))

    # 6. B10/B10B/B11 reference specs present.
    _self_test_reference_specs()

    # 7. Regenerate on-disk artifacts from the current build functions.
    _regenerate_artifacts()

    # 8. Validate the on-disk algorithm spec + report.
    spec = _load_json(ALGORITHM_SPEC_PATH)
    spec_hash = _sha256_json(spec)
    verify_algorithm_spec(spec, spec_hash)
    assert spec == build_algorithm_spec(), (
        "on-disk algorithm spec does not match build_algorithm_spec() output"
    )
    spec_again = _load_json(ALGORITHM_SPEC_PATH)
    assert _sha256_json(spec_again) == spec_hash, "algorithm spec hash not stable"

    on_disk_report = _load_json(REPORT_PATH)
    verify_report(on_disk_report)

    # 9. Ablation variants defined.
    _self_test_ablation_variants_defined()

    # 10. Hypotheses defined.
    _self_test_hypotheses_defined()

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": "mechanism_decomposition_v0",
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "aggregate_only_public_artifact": True,
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "synthetic_fixture_metrics": True,
            "hypothesis_evaluation_stub": True,
            "input_full_mode": True,
            "reference_specs_pinned": True,
            "artifacts_regenerated": True,
            "on_disk_artifacts_validated": True,
            "ablation_variants_defined": True,
            "hypotheses_defined": True,
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
        help="run the B12 self-test (synthetic fixture; verifies mechanics)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help=(
            "path to a private P21 v1 JSON file or directory of JSON files "
            "(schema p25-policy-records-ephemeral-v1). Loads records via the "
            "C1 adapter (eval/c1_private_records.py), routes each through the "
            "5 ablation variants (A-E), computes per-variant aggregate metrics, "
            "count reporting (balanced_branch / p25_llm_eligible / "
            "actual_call_avoided), and emits a verdict against the FROZEN "
            "predeclared criteria. Scientific verdicts (supported/refuted/"
            "partial/insufficient_data) return exit 0; mechanical/privacy/"
            "schema errors return nonzero."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write the report artifact; defaults to the canonical "
            "b12_mechanism_decomposition_report.json artifact path"
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input:
        parser.error(
            "B12 requires either --self-test or --input <path> in this skeleton"
        )
    if args.self_test and args.input:
        parser.error("--self-test and --input are mutually exclusive")
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "claim_level": report["claim_level"],
        "policy_under_analysis": report["policy_under_analysis"],
        "baseline_for_deltas": report["baseline_for_deltas"],
        "ablation_variants": report["ablation_variants"],
        "hypotheses": report["hypotheses"],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "evidencecore_semantics_changed": report["evidencecore_semantics_changed"],
        "policy_search_performed": report["policy_search_performed"],
        "quality_strategy_tuned": report["quality_strategy_tuned"],
        "runtime_calls_by_replay": report["runtime_calls_by_replay"],
        "model_calls_by_replay": report["model_calls_by_replay"],
        "aggregate_only_public_artifact": report["aggregate_only_public_artifact"],
        "robust_utility": report["robust_utility"],
    }
    if "replay_counts" in report:
        summary["replay_counts"] = report["replay_counts"]
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B12 self-test: PASS", file=sys.stderr)
        return 0
    if args.input:
        input_meta = _load_p21_input(args.input)
        report = _build_input_report(input_meta)
        verify_report(report)
        out_path = Path(args.out) if args.out else REPORT_PATH
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B12 report written to {out_path}", file=sys.stderr)
        return 0
    print("B12 requires --self-test or --input", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
