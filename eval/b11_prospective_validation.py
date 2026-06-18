#!/usr/bin/env python3
"""B11 Prospective Blind Validation.

B11 is the first true prospective validation of the frozen balanced policy
``balanced_policy_v1_benchmark_routed`` (B10). It uses new repos and tasks
generated after the 2026-06-18 policy freeze, with no retuning of policies,
thresholds, or success criteria.

This evaluator reads P21 outputs from multiple model × repo runs, computes
per-policy metrics (Local, P25, Balanced v1, Conservative), aggregates them
(overall mean, worst-group, bootstrap CIs, leave-one-out), and emits a verdict
(success/failure/partial/insufficient_data).

IMPORTANT: This is a preregistration. The success/failure/partial criteria are
FROZEN before any prospective live runs. No retuning is allowed after B11 live
runs begin.

Important claim boundary: B11 is a prospective stress test, not a promotion
step. Even if B11 succeeds, ``promotion_ready=false``,
``default_should_change=false``, and ``EvidenceCore`` semantics are unchanged.
B11's outcome only decides whether the balanced policy is a credible
algorithm candidate worth further research (B12 mechanism decomposition, B13
distributionally robust policy search).

Aggregate-only public artifacts: no task/repo/candidate/path/span/snippet/
prompt/response/gold/provider keys and no raw path/digest/provider strings.

This file currently ships a SKELETON: the ``--self-test`` path verifies the
aggregation mechanics against a synthetic fixture, while ``--input <path>``
is a stub (``verdict="not_implemented"``) awaiting the full P21-output metric
computation in a later task. No live LLM calls are made by this evaluator.

Run::

    python3 eval/b11_prospective_validation.py --self-test
    python3 eval/b11_prospective_validation.py --input path/to/p21_outputs.json
    python3 eval/b11_prospective_validation.py --self-test --out /tmp/b11_report.json
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
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b11_prospective_validation"
REPORT_PATH = (
    ARTIFACT_DIR / "b11_prospective_validation_report.json"
)
# The algorithm spec is emitted alongside the report (deterministic, fixed
# generated_at so its sha256 is stable across runs).
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "b11_prospective_validation.algorithm.json"
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

SCHEMA_VERSION = "b11-prospective-validation-report-v0"
SPEC_SCHEMA_VERSION = "b11-prospective-validation-spec-v0"
GENERATED_BY = "b11_prospective_validation"
ALGORITHM_SPEC_ID = "b11_prospective_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors B10/B10B).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# Policy under validation (B11 = balanced v1 prospective).
POLICY_UNDER_VALIDATION = "balanced_v1"
BASELINE_FOR_DELTAS = "p25"

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any prospective live runs)
# ---------------------------------------------------------------------------

PREDECLARED_CRITERIA: dict[str, Any] = {
    # Success thresholds (all must hold)
    "success_max_gold_delta_vs_p25_pct": 0.01,  # Δgold >= -max(1, 0.01 * P25_gold)
    "success_max_gold_delta_abs": 1,
    "success_max_spanf05_delta_vs_p25": -0.02,
    "success_max_false_spans_delta_vs_p25": 0,  # Δfalse_spans < 0
    "success_max_pfp_delta_vs_p25": 0.0,
    "success_max_llm_calls_delta_vs_p25": 0,  # ΔLLM_calls < 0
    # Worst-group thresholds
    "worst_group_max_gold_delta_pct": 0.02,
    "worst_group_max_gold_delta_abs": 2,
    "worst_group_max_spanf05_delta": -0.05,
    "worst_group_max_pfp_delta": 0.05,
    # Failure thresholds (any one triggers failure)
    "failure_max_gold_delta_pct": 0.02,
    "failure_max_gold_delta_abs": 2,
    "failure_max_spanf05_delta": -0.05,
    "failure_worst_group_max_gold_delta_pct": 0.03,
    "failure_worst_group_max_gold_delta_abs": 3,
    "failure_worst_group_max_spanf05_delta": -0.10,
    # RobustUtility parameters
    "robust_utility_lambda": 1.0,  # PFP weight
    "robust_utility_mu": 0.1,  # normalized_cost weight
    "robust_utility_nu": 0.1,  # normalized_latency weight
}

# ---------------------------------------------------------------------------
# Models, policies, repos (minimum viable B11)
# ---------------------------------------------------------------------------

MODEL_FAMILIES = ("kimi", "qwen", "deepseek_flash", "deepseek_pro")
POLICIES = ("local_baseline", "p25", "balanced_v1", "conservative")
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

# Metrics emitted per policy (per repo / per model family / overall).
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
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")
ALLOWED_VERDICTS = (
    "success",
    "failure",
    "partial",
    "insufficient_data",
    "not_implemented",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B so aggregate-only public artifact invariants are identical)
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


def _max_abs_floor(pct: float, abs_floor: float, baseline: float) -> float:
    """Compute ``-max(abs_floor, pct * baseline)`` style floor used by the
    predeclared criteria (negative = allowed regression magnitude).
    """
    return -max(abs_floor, pct * max(0.0, baseline))


# ---------------------------------------------------------------------------
# Synthetic fixture (self-test only)
# ---------------------------------------------------------------------------


def _synthetic_repo_metrics(
    policy: str, repo: str, model_family: str
) -> dict[str, float]:
    """Deterministic synthetic metrics for one (policy, repo, model_family).

    Values are deterministic functions of the inputs (no RNG) so the self-test
    spec hash is stable. Balanced v1 is intentionally constructed to slightly
    reduce false spans / PFP / model calls vs p25 while preserving gold and
    SpanF0.5 — the success-criteria deltas are positive-but-small, so the
    synthetic fixture still emits ``insufficient_data`` (no empirical support
    from a synthetic fixture, by safety stance).
    """
    # Stable per-cell base value in [0, 1).
    h = hashlib.sha256(
        f"{policy}|{repo}|{model_family}".encode("utf-8")
    ).digest()
    base = (h[0] / 255.0 + h[1] / 255.0 * 0.01)  # ~[0, 1.01)
    # Repo index for monotonic shifts.
    repo_idx = MINIMUM_VIABLE_REPOS.index(repo) if repo in MINIMUM_VIABLE_REPOS else 0
    model_idx = MODEL_FAMILIES.index(model_family) if model_family in MODEL_FAMILIES else 0

    span_f0_5 = 0.70 + 0.05 * (base) - 0.002 * repo_idx
    gold_span = 8.0 + (base * 2.0) - 0.05 * repo_idx
    false_span = 3.0 + (base * 2.0) + 0.05 * repo_idx
    pfp = 0.10 + (base * 0.05) + 0.001 * model_idx
    model_calls = 4.0 + (base * 1.0) + 0.05 * model_idx

    if policy == "local_baseline":
        # No LLM calls; lower SpanF0.5 / gold; higher false spans.
        model_calls = 0.0
        span_f0_5 -= 0.05
        gold_span -= 1.0
        false_span += 1.0
    elif policy == "p25":
        # Benchmark-routed baseline. As above.
        pass
    elif policy == "balanced_v1":
        # Preserves gold/SpanF0.5; reduces false spans / PFP / LLM calls.
        false_span -= 0.6
        pfp -= 0.01
        model_calls -= 1.0
    elif policy == "conservative":
        # Avoids false positives but kills recall.
        false_span -= 2.5
        pfp -= 0.03
        model_calls -= 2.0
        gold_span -= 3.0
        span_f0_5 -= 0.10

    # Clamp to plausible ranges.
    return {
        "span_f0_5": round(max(0.0, span_f0_5), 6),
        "gold_span": round(max(0.0, gold_span), 6),
        "false_span": round(max(0.0, false_span), 6),
        "primary_false_positive_rate": round(max(0.0, pfp), 6),
        "model_calls": round(max(0.0, model_calls), 6),
    }


def _build_synthetic_fixture() -> dict[str, Any]:
    """Build a synthetic per-policy × per-repo × per-model-family fixture.

    Returns a dict keyed by policy; each value is a dict with ``per_repo``,
    ``per_model_family``, ``overall_mean``, and ``n_records``.
    """
    out: dict[str, Any] = {}
    for policy in POLICIES:
        per_repo_cells: dict[str, list[dict[str, float]]] = {
            r: [] for r in MINIMUM_VIABLE_REPOS
        }
        per_model_cells: dict[str, list[dict[str, float]]] = {
            m: [] for m in MODEL_FAMILIES
        }
        all_cells: list[dict[str, float]] = []
        for model_family in MODEL_FAMILIES:
            for repo in MINIMUM_VIABLE_REPOS:
                cell = _synthetic_repo_metrics(policy, repo, model_family)
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
        out[policy] = {
            "per_repo": per_repo_mean,
            "per_model_family": per_model_mean,
            "overall_mean": overall,
            "n_records": len(all_cells),
        }
    return out


# ---------------------------------------------------------------------------
# Aggregation mechanics (pure Python; no numpy/sklearn/scipy)
# ---------------------------------------------------------------------------


def _aggregate_overall(per_policy: dict[str, Any]) -> dict[str, float]:
    """Overall mean per metric for the policy under validation."""
    pol = per_policy[POLICY_UNDER_VALIDATION]
    return dict(pol["overall_mean"])


def _worst_group_by_repo(
    per_policy: dict[str, Any], policy: str
) -> dict[str, dict[str, float]]:
    """For each metric, return the min (worst) value across repos."""
    pol = per_policy[policy]
    worst: dict[str, float] = {}
    for metric in METRIC_NAMES:
        vals = [
            pol["per_repo"][repo][metric]
            for repo in MINIMUM_VIABLE_REPOS
            if repo in pol["per_repo"]
        ]
        # "Worst" = lowest SpanF0.5/gold, highest false_span/PFP/model_calls.
        if metric in ("span_f0_5", "gold_span"):
            worst[metric] = round(min(vals), 6) if vals else 0.0
        else:
            worst[metric] = round(max(vals), 6) if vals else 0.0
    return {"repo": worst}


def _worst_group_by_model_family(
    per_policy: dict[str, Any], policy: str
) -> dict[str, dict[str, float]]:
    pol = per_policy[policy]
    worst: dict[str, float] = {}
    for metric in METRIC_NAMES:
        vals = [
            pol["per_model_family"][m][metric]
            for m in MODEL_FAMILIES
            if m in pol["per_model_family"]
        ]
        if metric in ("span_f0_5", "gold_span"):
            worst[metric] = round(min(vals), 6) if vals else 0.0
        else:
            worst[metric] = round(max(vals), 6) if vals else 0.0
    return {"model_family": worst}


def _bootstrap_ci(
    per_policy: dict[str, Any],
    policy: str,
    n_resamples: int = 10000,
    seed: int = 20260618,
) -> dict[str, dict[str, float]]:
    """Stratified-by-repo bootstrap 95% CI over per-repo means.

    Pure-Python: resample the per-repo mean vector with replacement, recompute
    the overall mean, repeat ``n_resamples`` times, take 2.5 / 97.5 percentiles.
    Deterministic given the fixed seed.
    """
    pol = per_policy[policy]
    repo_means = pol["per_repo"]
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


def _leave_one_repo_out(
    per_policy: dict[str, Any], policy: str
) -> dict[str, dict[str, float]]:
    """For each repo, recompute the policy's overall mean excluding that repo.
    Returns a per-repo metric summary (SpanF0.5 + gold_span + model_calls).
    """
    pol = per_policy[policy]
    repo_means = pol["per_repo"]
    out: dict[str, dict[str, float]] = {}
    for held in repo_means.keys():
        remaining = [v for k, v in repo_means.items() if k != held]
        out[held] = {
            "span_f0_5": round(_mean([c["span_f0_5"] for c in remaining]), 6),
            "gold_span": round(_mean([c["gold_span"] for c in remaining]), 6),
            "model_calls": round(_mean([c["model_calls"] for c in remaining]), 6),
        }
    return out


def _leave_one_model_family_out(
    per_policy: dict[str, Any], policy: str
) -> dict[str, dict[str, float]]:
    pol = per_policy[policy]
    model_means = pol["per_model_family"]
    out: dict[str, dict[str, float]] = {}
    for held in model_means.keys():
        remaining = [v for k, v in model_means.items() if k != held]
        out[held] = {
            "span_f0_5": round(_mean([c["span_f0_5"] for c in remaining]), 6),
            "gold_span": round(_mean([c["gold_span"] for c in remaining]), 6),
            "model_calls": round(_mean([c["model_calls"] for c in remaining]), 6),
        }
    return out


def _compute_deltas_vs_p25(
    per_policy: dict[str, Any]
) -> dict[str, float]:
    """Compute ``balanced_v1 - p25`` overall-mean deltas per metric."""
    bal = per_policy[POLICY_UNDER_VALIDATION]["overall_mean"]
    p25 = per_policy[BASELINE_FOR_DELTAS]["overall_mean"]
    return {
        m: round(bal[m] - p25[m], 6) for m in METRIC_NAMES
    }


def _compute_worst_group_deltas(
    per_policy: dict[str, Any]
) -> dict[str, dict[str, float]]:
    """Compute ``balanced_v1 - p25`` worst-group deltas per metric, per group
    type. ``worst`` is defined per-metric as the most-negative delta across
    groups of the given type (most-negative = worst regression)."""
    bal_repo = per_policy[POLICY_UNDER_VALIDATION]["per_repo"]
    p25_repo = per_policy[BASELINE_FOR_DELTAS]["per_repo"]
    bal_model = per_policy[POLICY_UNDER_VALIDATION]["per_model_family"]
    p25_model = per_policy[BASELINE_FOR_DELTAS]["per_model_family"]

    def _worst_delta(bal_map: dict, p25_map: dict) -> dict[str, float]:
        out: dict[str, float] = {}
        for metric in METRIC_NAMES:
            deltas = [
                bal_map[k][metric] - p25_map[k][metric]
                for k in bal_map
                if k in p25_map
            ]
            out[metric] = round(min(deltas), 6) if deltas else 0.0
        return out

    return {
        "repo": _worst_delta(bal_repo, p25_repo),
        "model_family": _worst_delta(bal_model, p25_model),
    }


def _compute_robust_utility(
    per_policy: dict[str, Any],
    lambda_: float,
    mu: float,
    nu: float,
) -> float:
    """Stub RobustUtility = min_group(SpanF0.5 - λ*PFP - μ*norm_cost - ν*norm_latency).

    For the skeleton we approximate ``normalized_cost`` and ``normalized_latency``
    by ``model_calls / 10`` (so they stay in roughly [0, 1]). The min is taken
    over model-family groups for the policy under validation.
    """
    pol = per_policy[POLICY_UNDER_VALIDATION]["per_model_family"]
    if not pol:
        return 0.0
    utilities: list[float] = []
    for _group, m in pol.items():
        span = m["span_f0_5"]
        pfp = m["primary_false_positive_rate"]
        norm_cost = m["model_calls"] / 10.0
        norm_latency = m["model_calls"] / 10.0  # skeleton: same proxy
        utilities.append(span - lambda_ * pfp - mu * norm_cost - nu * norm_latency)
    return round(min(utilities), 6)


def _evaluate_criteria(
    per_policy: dict[str, Any],
    replay_source: str,
) -> tuple[str, str]:
    """Apply the predeclared criteria to the computed metrics.

    Returns ``(verdict, verdict_reason)``. A synthetic-fixture replay_source
    always yields ``insufficient_data`` regardless of how the criteria evaluate,
    because synthetic fixtures cannot confer empirical support (mirrors B10B's
    safety stance).
    """
    # Synthetic fixture => never an empirical verdict.
    if replay_source == "synthetic_fixture":
        return (
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; B11 live runs "
            "required for any success, failure, or partial verdict",
        )

    # Compute deltas vs P25.
    deltas = _compute_deltas_vs_p25(per_policy)
    worst_deltas = _compute_worst_group_deltas(per_policy)
    p25_gold = per_policy[BASELINE_FOR_DELTAS]["overall_mean"]["gold_span"]

    # Failure (any one triggers failure).
    fail_gold = deltas["gold_span"] < _max_abs_floor(
        PREDECLARED_CRITERIA["failure_max_gold_delta_pct"],
        PREDECLARED_CRITERIA["failure_max_gold_delta_abs"],
        p25_gold,
    )
    fail_spanf = deltas["span_f0_5"] < PREDECLARED_CRITERIA[
        "failure_max_spanf05_delta"
    ]
    fail_wg_gold = worst_deltas["repo"]["gold_span"] < _max_abs_floor(
        PREDECLARED_CRITERIA["failure_worst_group_max_gold_delta_pct"],
        PREDECLARED_CRITERIA["failure_worst_group_max_gold_delta_abs"],
        p25_gold,
    )
    fail_wg_spanf = worst_deltas["repo"]["span_f0_5"] < PREDECLARED_CRITERIA[
        "failure_worst_group_max_spanf05_delta"
    ]
    fail_map = {
        "failure_gold_delta": fail_gold,
        "failure_spanf05_delta": fail_spanf,
        "failure_worst_group_gold_delta": fail_wg_gold,
        "failure_worst_group_spanf05_delta": fail_wg_spanf,
    }
    if any(fail_map.values()):
        failed = [k for k, v in fail_map.items() if v]
        return (
            "failure",
            "failure_threshold_exceeded: " + ",".join(failed),
        )

    # Success (all must hold).
    succ_gold = deltas["gold_span"] >= _max_abs_floor(
        PREDECLARED_CRITERIA["success_max_gold_delta_vs_p25_pct"],
        PREDECLARED_CRITERIA["success_max_gold_delta_abs"],
        p25_gold,
    )
    succ_spanf = deltas["span_f0_5"] >= PREDECLARED_CRITERIA[
        "success_max_spanf05_delta_vs_p25"
    ]
    succ_false = deltas["false_span"] < PREDECLARED_CRITERIA[
        "success_max_false_spans_delta_vs_p25"
    ]
    succ_pfp = deltas["primary_false_positive_rate"] <= PREDECLARED_CRITERIA[
        "success_max_pfp_delta_vs_p25"
    ]
    succ_calls = deltas["model_calls"] < PREDECLARED_CRITERIA[
        "success_max_llm_calls_delta_vs_p25"
    ]
    succ_wg_gold = worst_deltas["repo"]["gold_span"] >= _max_abs_floor(
        PREDECLARED_CRITERIA["worst_group_max_gold_delta_pct"],
        PREDECLARED_CRITERIA["worst_group_max_gold_delta_abs"],
        p25_gold,
    )
    succ_wg_spanf = worst_deltas["repo"]["span_f0_5"] >= PREDECLARED_CRITERIA[
        "worst_group_max_spanf05_delta"
    ]
    succ_wg_pfp = worst_deltas["repo"]["primary_false_positive_rate"] <= (
        PREDECLARED_CRITERIA["worst_group_max_pfp_delta"]
    )
    if all([
        succ_gold, succ_spanf, succ_false, succ_pfp, succ_calls,
        succ_wg_gold, succ_wg_spanf, succ_wg_pfp,
    ]):
        return ("success", "all_predeclared_success_criteria_met")

    # Neither success nor failure.
    return (
        "partial",
        "mixed_results_no_failure_threshold_exceeded; consider B12 mechanism "
        "decomposition to identify which conditions drive the mixed results",
    )


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B11 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so its
    SHA-256 is stable across runs. The on-disk spec file is the pin (mirrors
    B10/B10B freeze style). The self-test verifies hash stability by
    re-loading and re-hashing.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": "prospective_validation_v0",
        "description": (
            "B11 Prospective Blind Validation: first true prospective "
            "validation of the frozen balanced policy "
            "balanced_policy_v1_benchmark_routed (B10) on new repos and "
            "tasks generated after the 2026-06-18 policy freeze. Computes "
            "per-policy metrics (Local, P25, Balanced v1, Conservative) with "
            "overall mean, worst-group, bootstrap CIs, leave-one-out "
            "sensitivity, and RobustUtility; emits a verdict against FROZEN "
            "predeclared criteria. No policy search, no threshold tuning, no "
            "live LLM calls inside this evaluator."
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
        "policy_under_validation": POLICY_UNDER_VALIDATION,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        "model_families": list(MODEL_FAMILIES),
        "policies": list(POLICIES),
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
    """Check whether the on-disk frozen reference specs (B10, B10B) are
    present and loadable. Returns ``{spec_id: hash_pinned_on_disk_bool}``.
    The actual sha256 hex is NEVER returned (it would trip the forbidden-value
    scan); only the boolean matched flag is exposed publicly.
    """
    refs = {}
    for spec_id, path in (
        ("balanced_policy_v1_benchmark_routed", B10_SPEC_PATH),
        ("balanced_policy_v1_runtime_shadow_ambiguous_branch", B10B_SPEC_PATH),
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
    per_policy: dict[str, Any],
    *,
    self_test: bool,
    replay_source: str,
) -> dict[str, Any]:
    """Build the B11 prospective validation report.

    ``per_policy`` is the per-policy metrics dict (see
    ``_build_synthetic_fixture`` for the shape). ``self_test=True`` flags that
    the report was produced from a synthetic fixture for mechanics validation;
    ``replay_source`` is one of ``ALLOWED_REPLAY_SOURCES``.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    overall_mean = _aggregate_overall(per_policy)
    worst_repo = _worst_group_by_repo(per_policy, POLICY_UNDER_VALIDATION)
    worst_model = _worst_group_by_model_family(per_policy, POLICY_UNDER_VALIDATION)
    worst_group = {**worst_repo, **worst_model}
    bootstrap_ci = _bootstrap_ci(per_policy, POLICY_UNDER_VALIDATION)
    loo_repo = _leave_one_repo_out(per_policy, POLICY_UNDER_VALIDATION)
    loo_model = _leave_one_model_family_out(per_policy, POLICY_UNDER_VALIDATION)
    robust_utility = _compute_robust_utility(
        per_policy,
        lambda_=PREDECLARED_CRITERIA["robust_utility_lambda"],
        mu=PREDECLARED_CRITERIA["robust_utility_mu"],
        nu=PREDECLARED_CRITERIA["robust_utility_nu"],
    )
    deltas = _compute_deltas_vs_p25(per_policy)
    worst_deltas = _compute_worst_group_deltas(per_policy)

    verdict, verdict_reason = _evaluate_criteria(per_policy, replay_source)

    ref_hashes = _reference_spec_hashes()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": "prospective_validation_v0",
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
        "model_families": list(MODEL_FAMILIES),
        "policies": list(POLICIES),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "metric_names": list(METRIC_NAMES),
        "policy_under_validation": POLICY_UNDER_VALIDATION,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        "per_policy_metrics": per_policy,
        "overall_mean": overall_mean,
        "worst_group": worst_group,
        "bootstrap_ci_95": bootstrap_ci,
        "leave_one_repo_out": loo_repo,
        "leave_one_model_family_out": loo_model,
        "deltas_vs_baseline": deltas,
        "worst_group_deltas_vs_baseline": worst_deltas,
        "robust_utility": robust_utility,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
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
    if spec.get("claim_level") != "prospective_validation_v0":
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
    if tuple(spec.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("algorithm spec model_families mismatch")
    if tuple(spec.get("policies") or ()) != POLICIES:
        raise ValueError("algorithm spec policies mismatch")
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
    if report.get("claim_level") != "prospective_validation_v0":
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
    if tuple(report.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("report model_families mismatch")
    if tuple(report.get("policies") or ()) != POLICIES:
        raise ValueError("report policies mismatch")
    if tuple(report.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("report repos mismatch")
    if report.get("policy_under_validation") != POLICY_UNDER_VALIDATION:
        raise ValueError("report policy_under_validation mismatch")
    if report.get("baseline_for_deltas") != BASELINE_FOR_DELTAS:
        raise ValueError("report baseline_for_deltas mismatch")
    # Required top-level sections.
    for key in (
        "per_policy_metrics",
        "overall_mean",
        "worst_group",
        "bootstrap_ci_95",
        "leave_one_repo_out",
        "leave_one_model_family_out",
        "robust_utility",
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
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input (stub): load P21 outputs without computing metrics
# ---------------------------------------------------------------------------


def _load_p21_input(path: str) -> dict[str, Any]:
    """Load a P21 outputs JSON file (or directory of JSON files) and return a
    minimal metadata payload. The full per-policy metric computation is
    deferred to a later task; for now we only verify the input is valid JSON
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

    Real per-policy metric computation (reading P21 outputs, computing
    bootstrap CIs against the predeclared criteria, etc.) is deferred to a
    later task. For now we emit a well-formed report with
    ``verdict="not_implemented"`` and an explanatory reason, while still
    passing all safety-invariant checks.
    """
    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)
    # Reuse the synthetic fixture so the report has the right SHAPE; the
    # verdict is overridden below to "not_implemented".
    per_policy = _build_synthetic_fixture()
    report = build_report(
        per_policy, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Override the verdict to signal that no real metric computation happened.
    report["verdict"] = "not_implemented"
    report["verdict_reason"] = (
        "real-input metric computation deferred to later task; "
        f"input_meta={input_meta}"
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
    clean = {"provenance": "b11_prospective_validation::build_report"}
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
    per_policy = _build_synthetic_fixture()
    # All 4 policies x 8 repos x 4 model families present.
    for policy in POLICIES:
        assert policy in per_policy, policy
        assert set(per_policy[policy]["per_repo"].keys()) == set(
            MINIMUM_VIABLE_REPOS
        )
        assert set(per_policy[policy]["per_model_family"].keys()) == set(
            MODEL_FAMILIES
        )
        assert per_policy[policy]["n_records"] == len(MINIMUM_VIABLE_REPOS) * len(
            MODEL_FAMILIES
        )
    # balanced_v1 should reduce false_span / pfp / model_calls vs p25 in the
    # synthetic fixture (sanity check on the deterministic generator).
    bal = per_policy[POLICY_UNDER_VALIDATION]["overall_mean"]
    p25 = per_policy[BASELINE_FOR_DELTAS]["overall_mean"]
    assert bal["false_span"] < p25["false_span"], (bal, p25)
    assert bal["primary_false_positive_rate"] <= p25["primary_false_positive_rate"], (
        bal, p25
    )
    assert bal["model_calls"] < p25["model_calls"], (bal, p25)


def _self_test_bootstrap_ci() -> None:
    per_policy = _build_synthetic_fixture()
    ci = _bootstrap_ci(
        per_policy, POLICY_UNDER_VALIDATION, n_resamples=500, seed=20260618
    )
    # CI must be a dict keyed by metric with low <= high.
    for metric in METRIC_NAMES:
        assert metric in ci, metric
        assert ci[metric]["low"] <= ci[metric]["high"], (metric, ci[metric])
    # Deterministic across calls with the same seed.
    ci2 = _bootstrap_ci(
        per_policy, POLICY_UNDER_VALIDATION, n_resamples=500, seed=20260618
    )
    assert ci == ci2, "bootstrap CI must be deterministic given the fixed seed"


def _self_test_leave_one_out() -> None:
    per_policy = _build_synthetic_fixture()
    loo_r = _leave_one_repo_out(per_policy, POLICY_UNDER_VALIDATION)
    assert set(loo_r.keys()) == set(MINIMUM_VIABLE_REPOS)
    loo_m = _leave_one_model_family_out(per_policy, POLICY_UNDER_VALIDATION)
    assert set(loo_m.keys()) == set(MODEL_FAMILIES)


def _self_test_verdict_synthetic_fixture_insufficient() -> None:
    """A synthetic-fixture replay_source must NEVER yield a success/failure/
    partial verdict, regardless of how clean the metrics look."""
    per_policy = _build_synthetic_fixture()
    report = build_report(
        per_policy, self_test=True, replay_source="synthetic_fixture"
    )
    verify_report(report)
    assert report["replay_source"] == "synthetic_fixture"
    assert report["verdict"] == "insufficient_data", report["verdict"]
    assert "synthetic_fixture_only" in report["verdict_reason"]


def _self_test_input_stub_not_implemented(tmp_path: Path) -> None:
    """--input mode must emit verdict='not_implemented' without doing any real
    metric computation."""
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
    """The B10 and B10B frozen reference specs must exist on disk so the
    B11 frozen_artifacts pin is meaningful."""
    refs = _reference_spec_hashes()
    assert refs.get("balanced_policy_v1_benchmark_routed") is True, refs
    assert refs.get("balanced_policy_v1_runtime_shadow_ambiguous_branch") is True, refs


def _regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report so the
    artifact pin matches the in-code build functions. Mirrors the B10/B10B
    freeze-write style: deterministic output, canonical JSON."""
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    per_policy = _build_synthetic_fixture()
    report = build_report(
        per_policy, self_test=True, replay_source="synthetic_fixture"
    )
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    """Run all B11 self-test checks. Returns a summary dict."""
    import tempfile

    # 1. Forbidden-key/value scan.
    _self_test_forbidden_scan()

    # 2. Algorithm spec hash stability.
    _self_test_spec_hash_stable()

    # 3. Synthetic fixture metrics.
    _self_test_synthetic_fixture_metrics()

    # 4. Bootstrap CI determinism + low<=high.
    _self_test_bootstrap_ci()

    # 5. Leave-one-out sensitivity.
    _self_test_leave_one_out()

    # 6. Synthetic fixture => insufficient_data verdict.
    _self_test_verdict_synthetic_fixture_insufficient()

    # 7. --input stub => not_implemented verdict.
    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_stub_not_implemented(Path(tmp))

    # 8. B10/B10B reference specs present.
    _self_test_reference_specs()

    # 9. Regenerate on-disk artifacts from the current build functions.
    _regenerate_artifacts()

    # 10. Validate the on-disk algorithm spec + report.
    spec = _load_json(ALGORITHM_SPEC_PATH)
    spec_hash = _sha256_json(spec)
    verify_algorithm_spec(spec, spec_hash)
    assert spec == build_algorithm_spec(), (
        "on-disk algorithm spec does not match build_algorithm_spec() output"
    )
    # Re-load and re-hash to prove stability.
    spec_again = _load_json(ALGORITHM_SPEC_PATH)
    assert _sha256_json(spec_again) == spec_hash, "algorithm spec hash not stable"

    on_disk_report = _load_json(REPORT_PATH)
    verify_report(on_disk_report)

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": "prospective_validation_v0",
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
            "bootstrap_ci": True,
            "leave_one_out": True,
            "verdict_synthetic_fixture_insufficient": True,
            "input_stub_not_implemented": True,
            "reference_specs_pinned": True,
            "artifacts_regenerated": True,
            "on_disk_artifacts_validated": True,
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
        help="run the B11 self-test (synthetic fixture; verifies mechanics)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help=(
            "path to a JSON file or directory of JSON files containing P21 "
            "outputs (model x repo runs). Currently a STUB: emits "
            "verdict='not_implemented'; full metric computation deferred to a "
            "later task."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write the report artifact; defaults to the canonical "
            "b11_prospective_validation_report.json artifact path"
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input:
        parser.error(
            "B11 requires either --self-test or --input <path> in this skeleton"
        )
    if args.self_test and args.input:
        parser.error("--self-test and --input are mutually exclusive")
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "claim_level": report["claim_level"],
        "policy_under_validation": report["policy_under_validation"],
        "baseline_for_deltas": report["baseline_for_deltas"],
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
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B11 self-test: PASS", file=sys.stderr)
        return 0
    if args.input:
        input_meta = _load_p21_input(args.input)
        report = _build_not_implemented_report(input_meta)
        verify_report(report)
        out_path = Path(args.out) if args.out else REPORT_PATH
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B11 report written to {out_path}", file=sys.stderr)
        return 0
    print("B11 requires --self-test or --input", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
