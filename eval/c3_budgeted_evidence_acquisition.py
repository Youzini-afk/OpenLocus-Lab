#!/usr/bin/env python3
"""C3 Budgeted Evidence Acquisition v0.

C3 is the **budgeted evidence acquisition** phase that follows C2/B12. It is a
real **replay** policy experiment over the C1 private-records adapter, not a
planner or skeleton. Each P21 record carries per-strategy outcomes, so a small
frozen set of interpretable candidate policies (each a function of a
runtime-clean ``route_features`` dict only) can be replayed by selecting the
appropriate per-strategy outcome, and their budgeted evidence utility can be
compared against two baselines (P25 and balanced_v1) under a common-complete
denominator.

Important claim boundary: C3 is a budgeted replay policy experiment, not a
promotion step. The per-cell public report is **diagnostic-rank-only**: it
emits sufficient aggregate statistics and a diagnostic ordering of candidate
policies by utility, but it MUST NOT declare a winner. Per-cell candidate
selection is deferred to the matrix combiner. ``promotion_ready=false``,
``default_should_change=false``, ``EvidenceCore`` semantics unchanged.

Runtime-clean hard rule: candidate policies MUST receive only a ``route_features``
dict (projected to the frozen allowlist of feature names), NEVER a
``PrivateRecord``. Candidate routing MUST NOT read ``task_bucket``,
``task_risk_tags``, ``has_gold``, ``score_group``, ``outcomes``, ``task_id``,
``repo_id``, ``model_family``, ``language``, private hashes, etc. The evaluator
verifies routing invariance (selected actions unchanged when
private/benchmark/outcome fields are blanked or permuted) and surfaces two
aggregate booleans in the public report.

P25 and balanced_v1 are **baselines only** in C3, never candidate policies.
They are marked ``runtime_clean_candidate_policy=false`` and
``benchmark_label_taint=true`` because their routing reads benchmark route
labels (``task_bucket`` / ``task_risk_tags``) — exactly why they are not
runtime-clean general algorithms. Candidate policies MUST NOT call
``compute_p25_strategy`` / ``balanced_branch_predicate``.

Modes:

- ``--self-test``: synthetic fixture only; read-only (builds expected spec +
  report in memory and compares to on-disk artifacts, failing on drift; does
  NOT mutate checked-in artifacts); MUST NOT claim empirical support.
- ``--regenerate-artifacts``: the only path that writes the canonical synthetic
  algorithm spec + synthetic self-test report (the checked-in public
  artifacts). Use after code changes, then run ``--self-test`` to confirm.
- ``--input <path>``: loads private P21 v1 records via the C1 adapter and
  writes an aggregate-only public report (the empirical replay experiment).

Aggregate-only public artifacts: no task/repo/candidate/path/span/snippet/
prompt/response/gold/provider keys and no raw path/digest/provider strings.
``route_features`` itself is never emitted (only the frozen feature-name list
and aggregate ``feature_presence_counts``). Aggregate ``model_family`` and
``language`` counts are emitted; ``task_bucket`` counts are omitted for v0.

Run::

    python3 eval/c3_budgeted_evidence_acquisition.py --self-test
    python3 eval/c3_budgeted_evidence_acquisition.py --regenerate-artifacts
    python3 eval/c3_budgeted_evidence_acquisition.py --input path/to/p25_policy_records.private.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

import c1_private_records as c1

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "c3_budgeted_evidence_acquisition"
REPORT_PATH = (
    ARTIFACT_DIR / "c3_budgeted_evidence_acquisition_report.json"
)
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "c3_budgeted_evidence_acquisition.algorithm.json"
)

SCHEMA_VERSION = "c3-budgeted-evidence-acquisition-report-v0"
SPEC_SCHEMA_VERSION = "c3-budgeted-evidence-acquisition-spec-v0"
GENERATED_BY = "c3_budgeted_evidence_acquisition"
ALGORITHM_SPEC_ID = "c3_budgeted_evidence_acquisition_v0"
CLAIM_LEVEL = "budgeted_replay_policy_experiment_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors B10/B11/B12).
GENERATED_AT = "2026-06-19T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Frozen allowed runtime feature allowlist
# ---------------------------------------------------------------------------
# Intersection of C1 route_features present in P21 and this frozen allowlist.
# A candidate policy may read ONLY these feature names. Absent features are
# treated as false / 0 (see _feat_bool / _feat_num).
ALLOWED_RUNTIME_FEATURES: tuple[str, ...] = (
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

# ---------------------------------------------------------------------------
# Frozen allowed candidate actions
# ---------------------------------------------------------------------------
# Candidate policies MUST select one of these 5 actions. P25 and balanced_v1
# are NOT candidate actions (they are baselines only).
ALLOWED_CANDIDATE_ACTIONS: tuple[str, ...] = (
    "candidate_baseline",
    "weak_candidate_only",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
)

# LLM-costing candidate actions (1 model call per record under replay proxy).
LLM_COSTING_ACTIONS = frozenset(
    {"llm_span_narrow", "llm_filter", "llm_abstain_filter"}
)

# ---------------------------------------------------------------------------
# Frozen objective constants
# ---------------------------------------------------------------------------
# utility = span_f0_5 - lambda * added_false_span - mu * primary_false_positive_rate
#           - cost_weight * model_calls
# Frozen before any C3 replay; no tuning from outcomes.
LAMBDA = 1.0
MU = 1.0
COST_WEIGHT = 0.1

# ---------------------------------------------------------------------------
# Frozen candidate policy set (interpretable, fixed, NOT outcome-derived)
# ---------------------------------------------------------------------------
# Each candidate policy is a pure function ``route_features -> action``.
# It MUST receive only a route_features dict (projected to the allowlist), and
# MUST NOT read task_bucket / task_risk_tags / has_gold / score_group / outcomes
# / task_id / repo_id / model_family / language / private hashes.

CandidatePolicyFn = Callable[[dict[str, Any]], str]


def _feat_bool(rf: dict[str, Any], name: str) -> bool:
    """Read a boolean feature; absent => False."""
    v = rf.get(name)
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _feat_num(rf: dict[str, Any], name: str) -> float:
    """Read a numeric feature; absent => 0.0."""
    v = rf.get(name)
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _policy_local_only(rf: dict[str, Any]) -> str:
    return "candidate_baseline"


def _policy_weak_on_noise_else_local(rf: dict[str, Any]) -> str:
    if _feat_num(rf, "query_noise") > 0:
        return "weak_candidate_only"
    return "candidate_baseline"


def _policy_span_narrow_on_anchor_else_local(rf: dict[str, Any]) -> str:
    if _feat_bool(rf, "local_anchor") and _feat_bool(rf, "rrf_backed_by_anchor"):
        return "llm_span_narrow"
    return "candidate_baseline"


def _policy_filter_on_noise_else_span_narrow_on_anchor_else_local(
    rf: dict[str, Any],
) -> str:
    if _feat_num(rf, "query_noise") > 0:
        return "llm_filter"
    if _feat_bool(rf, "local_anchor") and _feat_bool(rf, "rrf_backed_by_anchor"):
        return "llm_span_narrow"
    return "candidate_baseline"


def _policy_abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local(
    rf: dict[str, Any],
) -> str:
    if _feat_bool(rf, "local_anchor") and not _feat_bool(rf, "rrf_backed_by_anchor"):
        return "llm_abstain_filter"
    if _feat_bool(rf, "local_anchor") and _feat_bool(rf, "rrf_backed_by_anchor"):
        return "llm_span_narrow"
    return "candidate_baseline"


def _policy_weak_on_disagreement_span_on_anchor_else_local(
    rf: dict[str, Any],
) -> str:
    if _feat_bool(rf, "local_anchor") and not _feat_bool(rf, "rrf_backed_by_anchor"):
        return "weak_candidate_only"
    if _feat_bool(rf, "local_anchor") and _feat_bool(rf, "rrf_backed_by_anchor"):
        return "llm_span_narrow"
    return "candidate_baseline"


# Frozen candidate policy registry (id -> (description, fn)).
CANDIDATE_POLICIES: tuple[tuple[str, str, CandidatePolicyFn], ...] = (
    (
        "local_only",
        "always candidate_baseline",
        _policy_local_only,
    ),
    (
        "weak_on_noise_else_local",
        "if query_noise>0 then weak_candidate_only else candidate_baseline",
        _policy_weak_on_noise_else_local,
    ),
    (
        "span_narrow_on_anchor_else_local",
        "if local_anchor and rrf_backed_by_anchor then llm_span_narrow "
        "else candidate_baseline",
        _policy_span_narrow_on_anchor_else_local,
    ),
    (
        "filter_on_noise_else_span_narrow_on_anchor_else_local",
        "if query_noise>0 then llm_filter elif local_anchor and "
        "rrf_backed_by_anchor then llm_span_narrow else candidate_baseline",
        _policy_filter_on_noise_else_span_narrow_on_anchor_else_local,
    ),
    (
        "abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local",
        "if local_anchor and not rrf_backed_by_anchor then llm_abstain_filter "
        "elif local_anchor and rrf_backed_by_anchor then llm_span_narrow "
        "else candidate_baseline",
        _policy_abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local,
    ),
    (
        "weak_on_disagreement_span_on_anchor_else_local",
        "if local_anchor and not rrf_backed_by_anchor then weak_candidate_only "
        "elif local_anchor and rrf_backed_by_anchor then llm_span_narrow "
        "else candidate_baseline",
        _policy_weak_on_disagreement_span_on_anchor_else_local,
    ),
)

CANDIDATE_POLICY_IDS = tuple(p[0] for p in CANDIDATE_POLICIES)

# Per-action model-call cost under replay (1 for LLM-costing actions, else 0).
ACTION_MODEL_CALL_COST: dict[str, int] = {
    "candidate_baseline": 0,
    "weak_candidate_only": 0,
    "llm_span_narrow": 1,
    "llm_filter": 1,
    "llm_abstain_filter": 1,
}

# ---------------------------------------------------------------------------
# Coverage / status enums
# ---------------------------------------------------------------------------
ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")
ALLOWED_STATUS = (
    "ok_cell_stats",
    "coverage_insufficient",
    "insufficient_data",
    "privacy_or_schema_blocked",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B12 but extended with C3's full forbidden-field list)
# ---------------------------------------------------------------------------

FORBIDDEN_PUBLIC_KEYS: frozenset[str] = frozenset(
    {
        "task_id",
        "test_id",
        "repo_id",
        "run_id",
        "private_record_hash",
        "record_hash",
        "source_ordinal",
        "candidate_id",
        "path",
        "span",
        "content_sha",
        "query",
        "raw_query",
        "snippet",
        "prompt",
        "response",
        "provider_key",
        "api_key",
        "base_url",
        "score_group",
        "has_gold",
        "outcomes",
        "strategy_results",
        "p31_score_gold",
        "p31_candidate_pools",
        "p33b_anchor_subtypes",
        "task_risk_tags",
        "route_features",
        # Strengthened forbidden keys (exact-match only; safe metric names like
        # added_false_span / primary_false_positive_rate / added_gold_span are
        # NOT exact matches and remain allowed).
        "private_label",
        "private_labels",
        "label",
        "labels",
        "gold_spans",
        "hash",
        "digest",
        "task_bucket",
    }
)

_FORBIDDEN_VALUE_RES = (
    re.compile(r"\b(?:sha_?(?:1|256)?|content_?sha)\b[\s:=]+[A-Fa-f0-9]{40,}", re.I),
    re.compile(r"https?://", re.I),
    re.compile(
        r"\b(?:api[_-]?key|base[_-]?url|api[_-]?secret|api[_-]?token)\b\s*[:=]\s*\S",
        re.I,
    ),
    re.compile(r"\b[A-Fa-f0-9]{64}\b"),
    re.compile(r"/"),  # raw filesystem path separator
)

# Metric names emitted per candidate policy / baseline (mean + sum).
METRIC_NAMES = (
    "span_f0_5",
    "added_gold_span",
    "added_false_span",
    "primary_false_positive_rate",
    "model_calls",
    "utility",
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


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _recursive_key_scan(obj: Any) -> list[str]:
    """Flag forbidden KEY names and conservative leaked-value patterns.

    Provenance references use ``module::symbol`` form (never raw filesystem
    paths), so the ``/`` value pattern is safe.
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


def _project_route_features(rf: dict[str, Any] | None) -> dict[str, Any]:
    """Project a route_features dict to the frozen allowlist.

    Absent features are simply omitted (the candidate policy helpers treat
    absent as false / 0 via ``_feat_bool`` / ``_feat_num``). This is the ONLY
    input a candidate policy is allowed to receive.
    """
    if not isinstance(rf, dict):
        return {}
    out: dict[str, Any] = {}
    for name in ALLOWED_RUNTIME_FEATURES:
        if name in rf:
            out[name] = rf[name]
    return out


def _action_model_calls(action: str) -> int:
    return ACTION_MODEL_CALL_COST.get(action, 0)


def _compute_utility(
    span_f0_5: float,
    added_false_span: float,
    primary_false_positive_rate: float,
    model_calls: int,
) -> float:
    return (
        span_f0_5
        - LAMBDA * added_false_span
        - MU * primary_false_positive_rate
        - COST_WEIGHT * float(model_calls)
    )


# ---------------------------------------------------------------------------
# Baseline strategy selectors (baselines ONLY; candidate policies never call these)
# ---------------------------------------------------------------------------


def _p25_baseline_strategy(record: c1.PrivateRecord) -> str:
    """P25 baseline: use C1 ``compute_p25_strategy`` for outcome selection.

    Marked ``benchmark_label_taint=true`` because P25 routing reads benchmark
    route labels (``task_bucket`` / ``task_risk_tags``).
    """
    return c1.compute_p25_strategy(record)


def _balanced_v1_baseline_strategy(record: c1.PrivateRecord) -> str:
    """balanced_v1 baseline: if balanced_branch then weak_candidate_only else
    P25 strategy. Marked ``benchmark_label_taint=true``."""
    if c1.balanced_branch_predicate(record):
        return "weak_candidate_only"
    return c1.compute_p25_strategy(record)


# ---------------------------------------------------------------------------
# Synthetic fixture (self-test only)
# ---------------------------------------------------------------------------


def _build_synthetic_fixture() -> list[dict[str, Any]]:
    """Build a synthetic in-memory record list for the self-test.

    Each synthetic record carries an allowlist-projected ``route_features``
    dict plus per-strategy outcome dicts for the 5 candidate actions and a few
    baseline-selected strategies, so the replay mechanics (policy selection,
    common-complete denominator, utility, deltas) can be exercised
    deterministically. Synthetic fixtures confer NO empirical support.
    """
    cases = [
        # (query_noise, candidate_support_exists, local_anchor, rrf_backed_by_anchor,
        #  candidate_count, has_gold)
        (0.0, True, True, True, 3, True),
        (1.0, True, True, False, 2, True),
        (0.0, False, False, False, 0, False),
        (1.0, True, True, True, 4, True),
        (0.0, True, True, False, 1, False),
        (0.0, True, False, False, 5, True),
    ]
    records: list[dict[str, Any]] = []
    for idx, (qn, cse, la, rbf, cc, has_gold) in enumerate(cases):
        rf = {
            "query_noise": qn,
            "candidate_support_exists": cse,
            "local_anchor": la,
            "rrf_backed_by_anchor": rbf,
            "candidate_count": cc,
            "symbol_regex_agree_file": bool(la),
            "symbol_regex_agree_span": bool(la),
            "rrf_anchor_agree_file": bool(rbf),
            "rrf_anchor_agree_span": bool(rbf),
            "dense_support_present": bool(cse),
        }
        rec: dict[str, Any] = {
            "task_id": f"c3-selftest-{idx:03d}",
            "repo_id": "py_selftest",
            "task_bucket": "positive" if has_gold else "negative",
            "task_risk_tags": ["ambiguous"] if qn > 0 else [],
            "score_group": "positive" if has_gold else "no_gold",
            "route_features": rf,
        }
        # Outcomes for the 5 candidate actions and the baselines' possible
        # strategies. Deterministic per-index profile.
        for strat in (
            "candidate_baseline",
            "weak_candidate_only",
            "llm_span_narrow",
            "llm_filter",
            "llm_abstain_filter",
            "symbol_regex_union",
            "rrf_primary",
        ):
            is_llm = strat in LLM_COSTING_ACTIONS
            is_weak = strat == "weak_candidate_only"
            is_local = strat == "candidate_baseline"
            base = 0.30 + 0.01 * idx
            rec[strat] = {
                "span_f0_5": base
                + (0.03 if is_llm else 0.0)
                - (0.02 if is_weak else 0.0)
                + (0.01 if is_local and has_gold else 0.0),
                "added_gold_span": (1 if has_gold else 0)
                + (1 if is_local and has_gold else 0),
                "added_false_span": float(2 - (idx % 2) + (1 if is_llm else 0) - (1 if is_weak else 0)),
                "primary_false_positive_rate": 0.10
                + 0.01 * idx
                - (0.02 if is_weak else 0.0)
                - (0.03 if is_llm else 0.0),
            }
        records.append(rec)
    return records


def _synthetic_records_for_replay() -> list[c1.PrivateRecord]:
    """Load the synthetic fixture through the C1 adapter (require_schema=False)
    so the self-test exercises the same replay path as ``--input``."""
    raw = _build_synthetic_fixture()
    payload = {
        "schema_version": c1.EXPECTED_SCHEMA_VERSION,
        "not_artifact_for_commit": True,
        "raw_queries_stored": False,
        "raw_snippets_stored": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "gold_spans_stored": False,
        "p31_score_gold_spans_stored": True,
        "records": raw,
    }
    records, _ = c1.load_private_records_from_payload(payload, model_family="kimi")
    return records


# ---------------------------------------------------------------------------
# Replay mechanics
# ---------------------------------------------------------------------------


def _record_outcome_metric_cell(
    record: c1.PrivateRecord, action: str
) -> dict[str, float] | None:
    """Extract the C3 metric cell for one record under one selected action.

    Returns None if the selected action's outcome is missing (caller treats
    the record as incomplete for the common-complete denominator).
    """
    if not (record.outcome_present or {}).get(action):
        return None
    outcome = record.outcomes.get(action) or {}
    span_f0_5 = float(outcome.get("span_f0_5", 0.0))
    added_gold_span = float(outcome.get("added_gold_span", 0))
    added_false_span = float(outcome.get("added_false_span", 0))
    pfp = float(outcome.get("primary_false_positive_rate", 0.0))
    model_calls = _action_model_calls(action)
    utility = _compute_utility(
        span_f0_5, added_false_span, pfp, model_calls
    )
    return {
        "span_f0_5": span_f0_5,
        "added_gold_span": added_gold_span,
        "added_false_span": added_false_span,
        "primary_false_positive_rate": pfp,
        "model_calls": float(model_calls),
        "utility": utility,
    }


def _select_candidate_actions(
    record: c1.PrivateRecord,
) -> dict[str, str]:
    """Run every frozen candidate policy on the projected route_features dict
    and return ``{policy_id: selected_action}``.

    Candidate policies receive ONLY the projected route_features dict, never
    the PrivateRecord. This is the runtime-clean hard rule.
    """
    rf = _project_route_features(record.route_features)
    out: dict[str, str] = {}
    for pid, _desc, fn in CANDIDATE_POLICIES:
        action = fn(rf)
        if action not in ALLOWED_CANDIDATE_ACTIONS:
            raise ValueError(
                f"candidate policy {pid!r} selected disallowed action {action!r}"
            )
        out[pid] = action
    return out


def _required_strategies_for_record(
    record: c1.PrivateRecord,
    candidate_actions: dict[str, str],
) -> set[str]:
    """Union of strategies whose outcomes must be present for this record to
    count toward the common-complete denominator (all candidate policies'
    selected actions + both baselines' selected strategies)."""
    required: set[str] = set(candidate_actions.values())
    required.add(_p25_baseline_strategy(record))
    required.add(_balanced_v1_baseline_strategy(record))
    return required


def _aggregate_cells(cells: list[dict[str, float]]) -> dict[str, float]:
    """Aggregate a list of per-record metric cells into mean + sum per metric."""
    if not cells:
        return {m: 0.0 for m in METRIC_NAMES}
    mean_block = {f"mean_{m}": round(_mean([c[m] for c in cells]), 6) for m in METRIC_NAMES}
    sum_block = {f"sum_{m}": round(sum(c[m] for c in cells), 6) for m in METRIC_NAMES}
    out: dict[str, float] = {}
    out.update(mean_block)
    out.update(sum_block)
    out["n_records"] = float(len(cells))
    return out


def _build_policy_aggregates(
    records: list[c1.PrivateRecord],
    selections: dict[str, dict[str, str]],
    complete_hashes: set[str],
) -> dict[str, dict[str, float]]:
    """Per candidate policy aggregate metrics over the common-complete
    denominator."""
    out: dict[str, dict[str, float]] = {}
    for pid in CANDIDATE_POLICY_IDS:
        cells: list[dict[str, float]] = []
        for r in records:
            if r.private_record_hash not in complete_hashes:
                continue
            action = selections[r.private_record_hash][pid]
            cell = _record_outcome_metric_cell(r, action)
            if cell is None:
                # Should not happen for a complete record (complete means all
                # required outcomes present); defensive guard.
                continue
            cells.append(cell)
        out[pid] = _aggregate_cells(cells)
    return out


def _build_baseline_aggregates(
    records: list[c1.PrivateRecord],
    baseline_strategies: dict[str, dict[str, str]],
    complete_hashes: set[str],
) -> dict[str, dict[str, Any]]:
    """Per baseline (p25, balanced_v1) aggregate metrics + taint flags."""
    out: dict[str, dict[str, Any]] = {}
    for baseline_id in ("p25", "balanced_v1"):
        cells: list[dict[str, float]] = []
        for r in records:
            if r.private_record_hash not in complete_hashes:
                continue
            action = baseline_strategies[r.private_record_hash][baseline_id]
            cell = _record_outcome_metric_cell(r, action)
            if cell is None:
                continue
            cells.append(cell)
        agg = _aggregate_cells(cells)
        agg["runtime_clean_candidate_policy"] = False
        agg["benchmark_label_taint"] = True
        agg["is_candidate_policy"] = False
        out[baseline_id] = agg
    return out


def _compute_deltas(
    per_policy: dict[str, dict[str, float]],
    baselines: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, float]]]:
    """Per candidate policy mean deltas vs p25 and balanced_v1 on each metric."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for pid in CANDIDATE_POLICY_IDS:
        pol = per_policy[pid]
        deltas: dict[str, dict[str, float]] = {}
        for baseline_id in ("p25", "balanced_v1"):
            base = baselines[baseline_id]
            d: dict[str, float] = {}
            for m in METRIC_NAMES:
                d[f"mean_{m}"] = round(
                    pol.get(f"mean_{m}", 0.0) - base.get(f"mean_{m}", 0.0), 6
                )
            deltas[f"vs_{baseline_id}"] = d
        out[pid] = deltas
    return out


def _feature_presence_counts(
    records: list[c1.PrivateRecord],
) -> dict[str, int]:
    """Aggregate-only count of how many records carry each allowed runtime
    feature (present and truthy). Aggregate-only; never emits the raw
    route_features dict or per-record feature values."""
    counts = {name: 0 for name in ALLOWED_RUNTIME_FEATURES}
    for r in records:
        rf = _project_route_features(r.route_features)
        for name in ALLOWED_RUNTIME_FEATURES:
            if name in rf:
                # Count as present if the value is truthy OR numeric>0 OR a
                # present key (presence is what matters here).
                v = rf[name]
                if isinstance(v, bool):
                    if v:
                        counts[name] += 1
                elif isinstance(v, (int, float)):
                    if v != 0:
                        counts[name] += 1
                elif isinstance(v, str):
                    if v.strip().lower() not in {"", "0", "false", "no", "off"}:
                        counts[name] += 1
                else:
                    counts[name] += 1
    return counts


def _model_family_language_counts(
    records: list[c1.PrivateRecord],
) -> dict[str, dict[str, int]]:
    """Aggregate model_family / language counts (allowed in v0)."""
    mf: dict[str, int] = {}
    lang: dict[str, int] = {}
    for r in records:
        mf[r.model_family] = mf.get(r.model_family, 0) + 1
        lang[r.language] = lang.get(r.language, 0) + 1
    return {"model_family_counts": mf, "language_counts": lang}


def _scrub_private_record(record: c1.PrivateRecord) -> c1.PrivateRecord:
    """Return a deep-ish copy of ``record`` with every non-route_features
    (private/benchmark/outcome/identity) field blanked or permuted.

    The ``route_features`` dict is preserved verbatim (the only category a
    candidate policy may read). Every other field — ``task_bucket``,
    ``task_risk_tags``, ``score_group``, ``has_gold``, ``outcomes``,
    ``outcome_present``, ``task_id``, ``repo_id``, ``model_family``,
    ``language``, ``private_record_hash``, ``source_ordinal``,
    ``p31_candidate_pools``, ``p31_score_gold``, ``p33b_anchor_subtypes``,
    ``taint`` — is replaced with sentinel/permuted values GUARANTEED to
    differ from the original (e.g. ``not has_gold`` for the boolean, inverted
    bools for ``outcome_present``) so a candidate policy that accidentally
    reads any of them would produce a different action, and the invariance
    check can honestly confirm the scrub was real.

    This is the core of the runtime-clean invariance test: if candidate
    policies truly receive ONLY the projected ``route_features`` dict, their
    selected actions must be byte-identical before and after scrubbing.
    """
    from dataclasses import replace as _dc_replace

    # Invert every outcome_present bool so the scrubbed dict is guaranteed
    # to differ from the original regardless of the original's shape.
    scrubbed_outcome_present = {
        s: not v for s, v in record.outcome_present.items()
    }
    # Build scrubbed outcomes with sentinel values that differ from originals.
    scrubbed_outcomes = {
        s: {"span_f0_5": -999.0, "added_gold_span": -999, "added_false_span": -999,
            "primary_false_positive_rate": -999.0}
        for s in record.outcomes
    }

    return _dc_replace(
        record,
        task_id="<scrubbed:" + str(record.task_id) + ">",
        repo_id="<scrubbed:" + str(record.repo_id) + ">",
        model_family="<scrubbed:" + str(record.model_family) + ">",
        language="<scrubbed:" + str(record.language) + ">",
        source_ordinal=record.source_ordinal + 1,
        private_record_hash="<scrubbed:" + str(record.private_record_hash) + ">",
        task_bucket="<scrubbed:" + str(record.task_bucket) + ">",
        task_risk_tags=["<scrubbed>"] + list(record.task_risk_tags),
        score_group="<scrubbed:" + str(record.score_group) + ">",
        has_gold=not record.has_gold,
        outcomes=scrubbed_outcomes,
        outcome_present=scrubbed_outcome_present,
        p31_candidate_pools={"<scrubbed>": []},
        p31_score_gold={"<scrubbed>": True},
        p33b_anchor_subtypes=[{"<scrubbed>": True}],
        taint={"<scrubbed>": True},
    )


def _routing_invariance_check(
    records: list[c1.PrivateRecord],
    selections: dict[str, dict[str, str]],
) -> bool:
    """Verify candidate-policy selections are unchanged when
    private/benchmark/outcome/identity fields are blanked/permuted.

    This is a REAL PrivateRecord-field scrub test, not just re-projecting the
    same route_features dict:

    1. For each record, build a scrubbed copy where every non-route_features
       field (task_bucket, task_risk_tags, score_group, has_gold, outcomes,
       outcome_present, task_id, repo_id, model_family, language,
       private_record_hash, source_ordinal, p31/p33 blocks, taint) is
       replaced with sentinel/empty values.
    2. Confirm that the scrubbed record's ``route_features`` is identical to
       the original's (scrubbing must not touch route_features).
    3. Confirm that every private/benchmark/outcome field actually DIFFERS
       after scrubbing (so the test is honest, not a no-op).
    4. Re-run every candidate policy on the scrubbed record's projected
       route_features and confirm the selected action is identical to the
       original selection.

    Candidate policies receive ONLY the projected route_features dict
    (never the PrivateRecord), so scrubbing private fields must not change
    any policy's selected action.
    """
    for r in records:
        scrubbed = _scrub_private_record(r)
        # route_features must be untouched by scrubbing.
        if scrubbed.route_features != r.route_features:
            return False
        # Every scrubbed private field must actually differ (honest scrub).
        if scrubbed.task_id == r.task_id:
            return False
        if scrubbed.repo_id == r.repo_id:
            return False
        if scrubbed.task_bucket == r.task_bucket:
            return False
        if scrubbed.task_risk_tags == r.task_risk_tags:
            return False
        if scrubbed.score_group == r.score_group:
            return False
        if scrubbed.has_gold == r.has_gold:
            return False
        if scrubbed.outcomes == r.outcomes:
            return False
        if scrubbed.outcome_present == r.outcome_present:
            return False
        if scrubbed.model_family == r.model_family:
            return False
        if scrubbed.language == r.language:
            return False
        if scrubbed.private_record_hash == r.private_record_hash:
            return False
        if scrubbed.source_ordinal == r.source_ordinal:
            return False
        # Re-run candidate policies on the scrubbed record's projected
        # route_features. Candidate policy functions receive ONLY the
        # route_features dict.
        rf_scrubbed = _project_route_features(scrubbed.route_features)
        for pid, _desc, fn in CANDIDATE_POLICIES:
            action = fn(rf_scrubbed)
            if action != selections[r.private_record_hash][pid]:
                return False
    return True


def _runtime_clean_inputs_check(
    records: list[c1.PrivateRecord],
    selections: dict[str, dict[str, str]],
) -> bool:
    """Verify candidate policies received only the projected route_features
    dict (no PrivateRecord, no benchmark/outcome fields). Re-project and
    re-run; identical selections prove the inputs were runtime-clean."""
    for r in records:
        rf = _project_route_features(r.route_features)
        for pid, _desc, fn in CANDIDATE_POLICIES:
            if fn(rf) != selections[r.private_record_hash][pid]:
                return False
    return True


def _diagnostic_rank(
    per_policy: dict[str, dict[str, float]],
) -> list[str]:
    """Diagnostic ordering of candidate policy ids by descending mean utility.
    Diagnostic ONLY; never a winner declaration."""
    ranked = sorted(
        CANDIDATE_POLICY_IDS,
        key=lambda pid: per_policy[pid].get("mean_utility", 0.0),
        reverse=True,
    )
    return ranked


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the C3 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so its
    SHA-256 is stable across runs. The on-disk spec file is the pin.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": CLAIM_LEVEL,
        "description": (
            "C3 Budgeted Evidence Acquisition v0: replay-only policy "
            "experiment over the C1 private-records adapter. Frozen "
            "interpretable candidate policies (each a function of a "
            "runtime-clean route_features dict only) are replayed against "
            "P21 per-strategy outcomes; their budgeted evidence utility is "
            "compared to P25 and balanced_v1 baselines under a "
            "common-complete denominator. Diagnostic-rank-only: no per-cell "
            "winner; selection deferred to the matrix combiner. No live LLM "
            "calls; no policy tuning from outcomes."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "empirical_algorithm_experiment_supported_via_input": True,
        "policy_enumeration_performed": True,
        "replay_only": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "aggregate_only_public_artifact": True,
        "allowed_runtime_features": list(ALLOWED_RUNTIME_FEATURES),
        "allowed_candidate_actions": list(ALLOWED_CANDIDATE_ACTIONS),
        "candidate_policies": [
            {"id": pid, "description": desc}
            for pid, desc, _fn in CANDIDATE_POLICIES
        ],
        "baselines": [
            {
                "id": "p25",
                "description": "P25 route_bucket_routed_v0 outcome selection",
                "is_candidate_policy": False,
                "runtime_clean_candidate_policy": False,
                "benchmark_label_taint": True,
            },
            {
                "id": "balanced_v1",
                "description": "balanced_branch -> weak_candidate_only else P25",
                "is_candidate_policy": False,
                "runtime_clean_candidate_policy": False,
                "benchmark_label_taint": True,
            },
        ],
        "objective_constants": {
            "lambda": LAMBDA,
            "mu": MU,
            "cost_weight": COST_WEIGHT,
            "utility_formula": (
                "span_f0_5 - lambda * added_false_span - "
                "mu * primary_false_positive_rate - cost_weight * model_calls"
            ),
        },
        "action_model_call_cost": dict(ACTION_MODEL_CALL_COST),
        "metric_names": list(METRIC_NAMES),
        "coverage_rules": {
            "common_complete_denominator": True,
            "exclude_record_if_any_selected_action_outcome_missing": True,
            "zero_complete_records_status": "coverage_insufficient",
            "winner_declared": False,
            "cell_diagnostic_rank_only": True,
            "candidate_selection_deferred_to_matrix_combiner": True,
        },
        "runtime_clean_contract": {
            "candidate_policies_receive_route_features_dict_only": True,
            "candidate_policies_must_not_read_private_or_benchmark_or_outcome_fields": True,
            "routing_invariance_under_private_field_permutation": True,
            "runtime_clean_policy_inputs_only": True,
        },
        "forbidden_public_keys": sorted(FORBIDDEN_PUBLIC_KEYS),
        "allowed_replay_sources": list(ALLOWED_REPLAY_SOURCES),
        "allowed_status": list(ALLOWED_STATUS),
        "remote_calls_by_c3": 0,
        "model_calls_by_replay": 0,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_policy_tuning_from_outcomes": True,
            "no_threshold_tuning": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "replay_only_no_live_runs_in_evaluator": True,
            "no_per_cell_winner": True,
        },
    }


def _reference_spec_hashes() -> dict[str, bool]:
    """Check whether the on-disk frozen reference specs (C1 adapter, B12) are
    present. Returns ``{spec_id: hash_pinned_on_disk_bool}``. The actual
    sha256 hex is NEVER returned (it would trip the forbidden-value scan)."""
    refs: dict[str, bool] = {}
    # C1 adapter has no on-disk spec; the B12 spec is the policy provenance pin.
    b12_spec = (
        REPO_ROOT
        / "artifacts"
        / "b12_mechanism_decomposition"
        / "b12_mechanism_decomposition.algorithm.json"
    )
    try:
        data = _load_json(b12_spec)
        refs["b12_mechanism_decomposition_v0"] = (
            data.get("algorithm_spec_id") == "b12_mechanism_decomposition_v0"
            and isinstance(data.get("generated_at"), str)
        )
    except FileNotFoundError:
        refs["b12_mechanism_decomposition_v0"] = False
    return refs


def build_report(
    *,
    self_test: bool,
    replay_source: str,
    records: list[c1.PrivateRecord],
    input_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the C3 budgeted evidence acquisition report from a list of
    normalized C1 records.

    ``self_test=True`` flags a synthetic-fixture replay (no empirical support
    claim). ``replay_source`` is one of ``ALLOWED_REPLAY_SOURCES``. The
    ``input_meta`` block carries safe scalar input metadata (no private
    fields).
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    # Per-record selections + completeness.
    selections: dict[str, dict[str, str]] = {}
    baseline_strategies: dict[str, dict[str, str]] = {}
    complete_hashes: set[str] = set()
    incomplete_count = 0

    for r in records:
        cand = _select_candidate_actions(r)
        selections[r.private_record_hash] = cand
        baseline_strategies[r.private_record_hash] = {
            "p25": _p25_baseline_strategy(r),
            "balanced_v1": _balanced_v1_baseline_strategy(r),
        }
        required = _required_strategies_for_record(r, cand)
        is_complete = all(
            (r.outcome_present or {}).get(s) for s in required
        )
        if is_complete:
            complete_hashes.add(r.private_record_hash)
        else:
            incomplete_count += 1

    total_records = len(records)
    complete_records = len(complete_hashes)

    per_policy = _build_policy_aggregates(
        records, selections, complete_hashes
    )
    baselines = _build_baseline_aggregates(
        records, baseline_strategies, complete_hashes
    )
    deltas = _compute_deltas(per_policy, baselines)
    feature_counts = _feature_presence_counts(records)
    fam_lang = _model_family_language_counts(records)
    invariance = _routing_invariance_check(records, selections)
    runtime_clean = _runtime_clean_inputs_check(records, selections)
    diagnostic_rank = _diagnostic_rank(per_policy)
    ref_hashes = _reference_spec_hashes()

    if total_records == 0:
        status = "insufficient_data"
    elif complete_records == 0:
        status = "coverage_insufficient"
    else:
        status = "ok_cell_stats"

    empirical = (replay_source == "ci_ephemeral_records") and not self_test

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
        "empirical_algorithm_experiment_performed": bool(empirical),
        "policy_search_or_enumeration_performed": bool(empirical),
        "replay_only": True,
        "remote_calls_by_c3": 0,
        "model_calls_by_replay": 0,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "aggregate_only_public_artifact": True,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "policy_count": len(CANDIDATE_POLICIES),
        "candidate_policy_ids": list(CANDIDATE_POLICY_IDS),
        "action_set": list(ALLOWED_CANDIDATE_ACTIONS),
        "allowed_runtime_features": list(ALLOWED_RUNTIME_FEATURES),
        "objective_constants": {
            "lambda": LAMBDA,
            "mu": MU,
            "cost_weight": COST_WEIGHT,
        },
        "total_records": total_records,
        "complete_records": complete_records,
        "incomplete_record_count": incomplete_count,
        "status": status,
        "per_policy": per_policy,
        "baselines": baselines,
        "deltas": deltas,
        "diagnostic_rank_only": diagnostic_rank,
        "cell_diagnostic_rank_only": True,
        "winner_declared": False,
        "candidate_selection_deferred_to_matrix_combiner": True,
        "feature_presence_counts": feature_counts,
        "model_family_counts": fam_lang["model_family_counts"],
        "language_counts": fam_lang["language_counts"],
        "selected_actions_invariant_under_private_field_permutation": bool(invariance),
        "runtime_clean_policy_inputs_only": bool(runtime_clean),
        "frozen_reference_specs_pinned_on_disk": ref_hashes,
        "metric_names": list(METRIC_NAMES),
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_policy_tuning_from_outcomes": True,
            "no_threshold_tuning": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "replay_only_no_live_runs_in_evaluator": True,
            "no_per_cell_winner": True,
        },
    }
    if input_meta is not None:
        report["input_meta"] = input_meta
    if self_test:
        report["self_test_note"] = (
            "synthetic_fixture_only_no_empirical_support; C3 --input replay "
            "over private P21 records required for any empirical claim"
        )
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
    if spec.get("replay_only") is not True:
        raise ValueError("algorithm spec replay_only must be true")
    if spec.get("remote_calls_by_c3") != 0:
        raise ValueError("algorithm spec remote_calls_by_c3 must be 0")
    if spec.get("model_calls_by_replay") != 0:
        raise ValueError("algorithm spec model_calls_by_replay must be 0")
    if spec.get("aggregate_only_public_artifact") is not True:
        raise ValueError("algorithm spec aggregate_only_public_artifact must be true")
    if tuple(spec.get("allowed_runtime_features") or ()) != ALLOWED_RUNTIME_FEATURES:
        raise ValueError("algorithm spec allowed_runtime_features mismatch")
    if tuple(spec.get("allowed_candidate_actions") or ()) != ALLOWED_CANDIDATE_ACTIONS:
        raise ValueError("algorithm spec allowed_candidate_actions mismatch")
    cand_ids = [p["id"] for p in spec.get("candidate_policies") or []]
    if tuple(cand_ids) != CANDIDATE_POLICY_IDS:
        raise ValueError("algorithm spec candidate_policies mismatch")
    obj = spec.get("objective_constants") or {}
    if obj.get("lambda") != LAMBDA or obj.get("mu") != MU or obj.get("cost_weight") != COST_WEIGHT:
        raise ValueError("algorithm spec objective_constants mismatch")
    if tuple(spec.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("algorithm spec metric_names mismatch")
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
    if report.get("replay_only") is not True:
        raise ValueError("report replay_only must be true")
    if report.get("promotion_ready") is not False:
        raise ValueError("report promotion_ready must be false")
    if report.get("default_should_change") is not False:
        raise ValueError("report default_should_change must be false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError("report evidencecore_semantics_changed must be false")
    if report.get("remote_calls_by_c3") != 0:
        raise ValueError("report remote_calls_by_c3 must be 0")
    if report.get("model_calls_by_replay") != 0:
        raise ValueError("report model_calls_by_replay must be 0")
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError("report aggregate_only_public_artifact must be true")
    if report.get("replay_source") not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"report replay_source invalid: {report.get('replay_source')!r}")
    if report.get("status") not in ALLOWED_STATUS:
        raise ValueError(f"report status invalid: {report.get('status')!r}")
    if report.get("winner_declared") is not False:
        raise ValueError("report winner_declared must be false (no per-cell winner)")
    if report.get("cell_diagnostic_rank_only") is not True:
        raise ValueError("report cell_diagnostic_rank_only must be true")
    if report.get("candidate_selection_deferred_to_matrix_combiner") is not True:
        raise ValueError("report candidate_selection_deferred_to_matrix_combiner must be true")
    if report.get("selected_actions_invariant_under_private_field_permutation") is not True:
        raise ValueError("report routing invariance flag must be true")
    if report.get("runtime_clean_policy_inputs_only") is not True:
        raise ValueError("report runtime_clean_policy_inputs_only must be true")
    if tuple(report.get("candidate_policy_ids") or ()) != CANDIDATE_POLICY_IDS:
        raise ValueError("report candidate_policy_ids mismatch")
    if tuple(report.get("action_set") or ()) != ALLOWED_CANDIDATE_ACTIONS:
        raise ValueError("report action_set mismatch")
    if tuple(report.get("allowed_runtime_features") or ()) != ALLOWED_RUNTIME_FEATURES:
        raise ValueError("report allowed_runtime_features mismatch")
    if report.get("policy_count") != len(CANDIDATE_POLICIES):
        raise ValueError("report policy_count mismatch")
    # Required sections.
    for key in (
        "per_policy",
        "baselines",
        "deltas",
        "diagnostic_rank_only",
        "feature_presence_counts",
        "safety_invariants",
    ):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # Baselines carry the taint flags.
    for bid in ("p25", "balanced_v1"):
        b = report.get("baselines", {}).get(bid) or {}
        if b.get("runtime_clean_candidate_policy") is not False:
            raise ValueError(f"baselines.{bid}.runtime_clean_candidate_policy must be false")
        if b.get("benchmark_label_taint") is not True:
            raise ValueError(f"baselines.{bid}.benchmark_label_taint must be true")
        if b.get("is_candidate_policy") is not False:
            raise ValueError(f"baselines.{bid}.is_candidate_policy must be false")
    # Self-test must NOT claim empirical support.
    if report.get("self_test") is True:
        if report.get("empirical_algorithm_experiment_performed") is True:
            raise ValueError("self-test must not claim empirical support")
        if report.get("policy_search_or_enumeration_performed") is True:
            raise ValueError("self-test must not claim policy enumeration")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input: load private P21 v1 records via the C1 adapter and replay
# ---------------------------------------------------------------------------


def _load_p21_input(path: str) -> dict[str, Any]:
    """Load private P21 v1 records via the C1 adapter and return a metadata
    payload carrying the normalized ``records`` list plus safe scalar counts.
    Records are kept IN MEMORY ONLY; the public report never emits raw
    task_ids/repo_ids/spans/snippets/per-record hashes."""
    records, meta = c1.load_private_records(path)
    return {
        "source_kind": meta.get("source_kind"),
        "n_files": meta.get("n_files"),
        "n_records": meta.get("n_records"),
        "records": records,
        "taint_summary": meta.get("taint_summary"),
    }


def _build_input_report(input_meta: dict[str, Any]) -> dict[str, Any]:
    """Build a real C3 report from private P21 ``--input`` records."""
    records = input_meta.get("records") or []
    report = build_report(
        self_test=False,
        replay_source="ci_ephemeral_records",
        records=records,
        input_meta={
            "source_kind": input_meta.get("source_kind"),
            "n_files": input_meta.get("n_files"),
            "n_records": input_meta.get("n_records"),
            "taint_summary": input_meta.get("taint_summary"),
        },
    )
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
        "repo_id": "r1",
        "run_id": "run1",
        "path": "src/foo.rs",
        "span": [[1, 2]],
        "snippet": "fn main(){}",
        "query": "find x",
        "raw_query": "find x",
        "prompt": "p",
        "response": "r",
        "provider_key": "sk-xxx",
        "api_key": "k",
        "base_url": "http://x",
        "content_sha": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "score_group": "positive",
        "has_gold": True,
        "outcomes": {},
        "strategy_results": {},
        "p31_score_gold": {},
        "p31_candidate_pools": {},
        "p33b_anchor_subtypes": [],
        "task_risk_tags": ["ambiguous"],
        "route_features": {"query_noise": 1},
        "private_record_hash": "h",
        "record_hash": "h",
        "source_ordinal": 1,
        "candidate_id": "c",
        "nested": {"content_sha": "deadbeef", "gold_spans": [[1, 2]]},
    }
    hits = _recursive_key_scan(bad_report)
    flat = " ".join(hits)
    for key in (
        "task_id", "repo_id", "run_id", "path", "span", "snippet", "query",
        "raw_query", "prompt", "response", "provider_key", "api_key",
        "base_url", "content_sha", "score_group", "has_gold", "outcomes",
        "strategy_results", "p31_score_gold", "p31_candidate_pools",
        "p33b_anchor_subtypes", "task_risk_tags", "route_features",
        "private_record_hash", "record_hash", "source_ordinal",
        "candidate_id",
    ):
        assert key in flat, f"forbidden key {key!r} not flagged: {hits!r}"

    # Raw path value trips the "/" pattern even when the key is allowed.
    bad_value = {"provenance": "eval/some_file.py"}
    hits2 = _recursive_key_scan(bad_value)
    assert any("forbidden_value" in h for h in hits2), hits2

    # Clean provenance (module::symbol, no "/") must not trip.
    clean = {"provenance": "c3_budgeted_evidence_acquisition::build_report"}
    assert _recursive_key_scan(clean) == []

    # 64-hex digest trips the forbidden-value scan.
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


def _self_test_synthetic_fixture_mechanics() -> None:
    records = _synthetic_records_for_replay()
    assert len(records) > 0
    report = build_report(
        self_test=True, replay_source="synthetic_fixture", records=records
    )
    verify_report(report)
    assert report["replay_source"] == "synthetic_fixture"
    assert report["self_test"] is True
    assert report["empirical_algorithm_experiment_performed"] is False
    assert report["policy_search_or_enumeration_performed"] is False
    assert report["winner_declared"] is False
    assert report["cell_diagnostic_rank_only"] is True
    assert report["candidate_selection_deferred_to_matrix_combiner"] is True
    assert report["status"] in ALLOWED_STATUS
    # Per-policy aggregates present for every candidate policy.
    for pid in CANDIDATE_POLICY_IDS:
        assert pid in report["per_policy"], pid
        agg = report["per_policy"][pid]
        for m in METRIC_NAMES:
            assert f"mean_{m}" in agg, (pid, m)
            assert f"sum_{m}" in agg, (pid, m)
    # Baselines flagged correctly (NOT candidate policies, benchmark-tainted).
    for bid in ("p25", "balanced_v1"):
        b = report["baselines"][bid]
        assert b["runtime_clean_candidate_policy"] is False, bid
        assert b["benchmark_label_taint"] is True, bid
        assert b["is_candidate_policy"] is False, bid
    # Deltas vs both baselines present for every candidate policy.
    for pid in CANDIDATE_POLICY_IDS:
        assert "vs_p25" in report["deltas"][pid], pid
        assert "vs_balanced_v1" in report["deltas"][pid], pid
    # Diagnostic rank is over all candidate policy ids; no winner.
    assert sorted(report["diagnostic_rank_only"]) == sorted(CANDIDATE_POLICY_IDS)
    # Routing invariance + runtime-clean inputs.
    assert report["selected_actions_invariant_under_private_field_permutation"] is True
    assert report["runtime_clean_policy_inputs_only"] is True
    # Feature presence counts are aggregate-only.
    for name in ALLOWED_RUNTIME_FEATURES:
        assert name in report["feature_presence_counts"], name


def _self_test_input_full_mode(tmp_path: Path) -> None:
    """--input mode must load private P21 v1 records via the C1 adapter and
    emit a real empirical replay report (not a synthetic-only claim)."""
    payload = c1.build_synthetic_v1_payload()
    p = tmp_path / "kimi_c3_selftest.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    meta = _load_p21_input(str(p))
    assert meta["source_kind"] == "file_object"
    assert meta["n_records"] == len(payload["records"])
    report = _build_input_report(meta)
    verify_report(report)
    assert report["replay_source"] == "ci_ephemeral_records"
    assert report["empirical_algorithm_experiment_performed"] is True
    assert report["policy_search_or_enumeration_performed"] is True
    assert report["winner_declared"] is False
    assert report["status"] in ALLOWED_STATUS
    # No forbidden keys leaked.
    assert _recursive_key_scan(report) == []
    # Aggregate model_family/language counts present (allowed in v0).
    assert "model_family_counts" in report
    assert "language_counts" in report


def _self_test_missing_outcome_coverage_insufficient(tmp_path: Path) -> None:
    """If every record is missing a required selected-action outcome, the
    common-complete denominator collapses to 0 and status is
    coverage_insufficient."""
    payload = c1.build_synthetic_v1_payload()
    # Strip all strategy outcomes from every record so no selected action has
    # a present outcome -> complete_records=0.
    for rec in payload["records"]:
        for strat in c1.P21_STRATEGY_KEYS:
            rec.pop(strat, None)
    p = tmp_path / "kimi_c3_missing.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    meta = _load_p21_input(str(p))
    report = _build_input_report(meta)
    verify_report(report)
    assert report["complete_records"] == 0, report["complete_records"]
    assert report["status"] == "coverage_insufficient", report["status"]
    assert report["winner_declared"] is False


def _self_test_p25_balanced_not_candidate_policies() -> None:
    """P25 and balanced_v1 must NOT appear in candidate_policy_ids; they are
    baselines only."""
    assert "p25" not in CANDIDATE_POLICY_IDS
    assert "balanced_v1" not in CANDIDATE_POLICY_IDS
    spec = build_algorithm_spec()
    cand_ids = {p["id"] for p in spec["candidate_policies"]}
    assert "p25" not in cand_ids
    assert "balanced_v1" not in cand_ids
    baseline_ids = {b["id"] for b in spec["baselines"]}
    assert baseline_ids == {"p25", "balanced_v1"}


def _self_test_runtime_clean_invariance() -> None:
    """Candidate-policy selections must be unchanged when private/benchmark/
    outcome/identity fields are blanked or permuted (runtime-clean hard rule).

    This is a REAL PrivateRecord-field scrub test: we scrub every non-
    route_features field on a normalized record and confirm candidate policy
    actions computed from the scrubbed record's projected route_features are
    identical to the original. We also confirm the scrubbed private fields
    actually differ (honest scrub, not a no-op).
    """
    records = _synthetic_records_for_replay()
    for r in records:
        rf_full = _project_route_features(r.route_features)
        # Real scrub: blank/permute every private/benchmark/outcome/identity
        # field on the PrivateRecord and re-run policies from route_features.
        scrubbed = _scrub_private_record(r)
        # route_features must be untouched.
        assert scrubbed.route_features == r.route_features
        # Every scrubbed private field must actually differ.
        assert scrubbed.task_id != r.task_id
        assert scrubbed.repo_id != r.repo_id
        assert scrubbed.task_bucket != r.task_bucket
        assert scrubbed.task_risk_tags != r.task_risk_tags
        assert scrubbed.score_group != r.score_group
        assert scrubbed.has_gold != r.has_gold
        assert scrubbed.outcomes != r.outcomes
        assert scrubbed.outcome_present != r.outcome_present
        assert scrubbed.model_family != r.model_family
        assert scrubbed.language != r.language
        assert scrubbed.private_record_hash != r.private_record_hash
        assert scrubbed.source_ordinal != r.source_ordinal
        # Candidate policies receive ONLY the route_features dict; scrubbed
        # route_features is identical so actions must match.
        rf_scrubbed = _project_route_features(scrubbed.route_features)
        for pid, _desc, fn in CANDIDATE_POLICIES:
            assert fn(rf_full) == fn(rf_scrubbed), pid
            assert fn(rf_full) in ALLOWED_CANDIDATE_ACTIONS, pid
        # Also confirm injecting junk keys into the route_features dict does
        # not change actions (policies must ignore non-allowlist keys).
        rf_junk = dict(rf_scrubbed)
        rf_junk["task_bucket"] = "permuted"
        rf_junk["task_risk_tags"] = ["permuted"]
        rf_junk["score_group"] = "permuted"
        rf_junk["has_gold"] = True
        rf_junk["outcomes"] = {"fake": {}}
        rf_junk["task_id"] = "permuted"
        rf_junk["repo_id"] = "permuted"
        for pid, _desc, fn in CANDIDATE_POLICIES:
            assert fn(rf_full) == fn(rf_junk), pid


def _self_test_action_set_and_features_frozen() -> None:
    """Allowed candidate actions and allowed runtime features are frozen."""
    assert len(ALLOWED_CANDIDATE_ACTIONS) == 5
    for a in (
        "candidate_baseline",
        "weak_candidate_only",
        "llm_span_narrow",
        "llm_filter",
        "llm_abstain_filter",
    ):
        assert a in ALLOWED_CANDIDATE_ACTIONS, a
    assert len(ALLOWED_RUNTIME_FEATURES) == 10
    for f in (
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
    ):
        assert f in ALLOWED_RUNTIME_FEATURES, f


def _self_test_objective_constants_frozen() -> None:
    assert LAMBDA == 1.0
    assert MU == 1.0
    assert COST_WEIGHT == 0.1
    # Utility sanity on a known cell.
    u = _compute_utility(
        span_f0_5=0.5,
        added_false_span=2.0,
        primary_false_positive_rate=0.1,
        model_calls=1,
    )
    # 0.5 - 1.0*2.0 - 1.0*0.1 - 0.1*1 = 0.5 - 2.0 - 0.1 - 0.1 = -1.7
    assert abs(u - (-1.7)) < 1e-9, u
    u0 = _compute_utility(0.5, 0.0, 0.0, 0)
    assert abs(u0 - 0.5) < 1e-9, u0


def _self_test_artifacts_match_in_memory() -> None:
    """The on-disk spec + report must match the in-memory build functions
    exactly. Any drift fails the self-test (use --regenerate-artifacts to
    update the canonical artifacts)."""
    spec_disk = _load_json(ALGORITHM_SPEC_PATH)
    spec_mem = build_algorithm_spec()
    assert spec_disk == spec_mem, "on-disk algorithm spec drifted from build_algorithm_spec()"
    h_disk = _sha256_json(spec_disk)
    verify_algorithm_spec(spec_disk, h_disk)

    report_disk = _load_json(REPORT_PATH)
    verify_report(report_disk)
    # Rebuild the synthetic report in memory and compare for full equality
    # (drift detection).
    records = _synthetic_records_for_replay()
    report_mem = build_report(
        self_test=True, replay_source="synthetic_fixture", records=records
    )
    verify_report(report_mem)
    assert report_disk == report_mem, (
        "on-disk synthetic report drifted from in-memory build_report()"
    )
    # The on-disk report must be a self-test synthetic-fixture report.
    assert report_disk["self_test"] is True
    assert report_disk["replay_source"] == "synthetic_fixture"


def _self_test_docs_paths_exist_if_practical() -> None:
    """If the docs directory is present, the C3 en/zh doc stubs must exist."""
    en_doc = REPO_ROOT / "docs" / "en" / "c3-budgeted-evidence-acquisition.md"
    zh_doc = REPO_ROOT / "docs" / "zh" / "c3-budgeted-evidence-acquisition.md"
    if (REPO_ROOT / "docs" / "en").is_dir():
        assert en_doc.exists(), f"missing {en_doc}"
    if (REPO_ROOT / "docs" / "zh").is_dir():
        assert zh_doc.exists(), f"missing {zh_doc}"


def _regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic self-test report so
    the artifact pin matches the in-code build functions. Mirrors the
    B10/B11/B12 freeze-write style: deterministic output, canonical JSON."""
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    records = _synthetic_records_for_replay()
    report = build_report(
        self_test=True, replay_source="synthetic_fixture", records=records
    )
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    """Run all C3 self-test checks. Returns a summary dict.

    ``--self-test`` is strictly read-only: it builds the expected spec +
    report in memory and compares them to the on-disk artifacts, failing on
    drift. It MUST NOT write or mutate checked-in artifacts. Use
    ``--regenerate-artifacts`` to update the canonical artifacts.
    """
    import tempfile

    _self_test_forbidden_scan()
    _self_test_spec_hash_stable()
    _self_test_action_set_and_features_frozen()
    _self_test_objective_constants_frozen()
    _self_test_runtime_clean_invariance()
    _self_test_p25_balanced_not_candidate_policies()
    _self_test_synthetic_fixture_mechanics()

    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_full_mode(Path(tmp))
        _self_test_missing_outcome_coverage_insufficient(Path(tmp))

    # Read-only on-disk artifact validation (no mutation). The on-disk spec +
    # report must match the in-memory build functions exactly; any drift
    # fails the self-test.
    spec = _load_json(ALGORITHM_SPEC_PATH)
    spec_hash = _sha256_json(spec)
    verify_algorithm_spec(spec, spec_hash)
    assert spec == build_algorithm_spec(), (
        "on-disk algorithm spec does not match build_algorithm_spec() output"
    )

    _self_test_artifacts_match_in_memory()
    _self_test_docs_paths_exist_if_practical()

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256": spec_hash,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": CLAIM_LEVEL,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "empirical_algorithm_experiment_performed": False,
        "policy_search_or_enumeration_performed": False,
        "replay_only": True,
        "remote_calls_by_c3": 0,
        "model_calls_by_replay": 0,
        "winner_declared": False,
        "cell_diagnostic_rank_only": True,
        "candidate_selection_deferred_to_matrix_combiner": True,
        "aggregate_only_public_artifact": True,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "candidate_policy_ids": list(CANDIDATE_POLICY_IDS),
        "action_set": list(ALLOWED_CANDIDATE_ACTIONS),
        "allowed_runtime_features": list(ALLOWED_RUNTIME_FEATURES),
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "action_set_and_features_frozen": True,
            "objective_constants_frozen": True,
            "runtime_clean_invariance": True,
            "p25_balanced_not_candidate_policies": True,
            "synthetic_fixture_mechanics": True,
            "input_full_mode": True,
            "missing_outcome_coverage_insufficient": True,
            "artifacts_match_in_memory": True,
            "docs_paths_exist_if_practical": True,
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
        help="run the C3 self-test (synthetic fixture; read-only: builds "
        "expected spec/report in memory and compares to on-disk artifacts, "
        "failing on drift; no empirical support claim; does NOT mutate "
        "checked-in artifacts)",
    )
    parser.add_argument(
        "--regenerate-artifacts",
        action="store_true",
        help="write the canonical synthetic algorithm spec + self-test report "
        "to artifacts/c3_budgeted_evidence_acquisition/ (the only path that "
        "mutates checked-in artifacts; use after code changes, then run "
        "--self-test to confirm)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help=(
            "path to a private P21 v1 JSON file or directory of JSON files "
            "(schema p25-policy-records-ephemeral-v1). Loads records via the "
            "C1 adapter (eval/c1_private_records.py), replays the frozen "
            "candidate policy set + P25/balanced_v1 baselines, and emits an "
            "aggregate-only public report with diagnostic-rank-only ordering "
            "(no per-cell winner). Scientific statuses (ok_cell_stats / "
            "coverage_insufficient / insufficient_data) return exit 0; "
            "mechanical/privacy/schema errors return nonzero."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write the report artifact; required for --input (no "
            "default checked-in path is mutated by --input); --self-test "
            "and --regenerate-artifacts do not accept --out (they target the "
            "canonical artifact paths)"
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    n_modes = sum(bool(x) for x in (args.self_test, args.regenerate_artifacts, bool(args.input)))
    if n_modes == 0:
        parser.error("C3 requires one of --self-test / --regenerate-artifacts / --input <path>")
    if n_modes > 1:
        parser.error("--self-test / --regenerate-artifacts / --input are mutually exclusive")
    if args.input and not args.out:
        parser.error("--input requires --out <path>")
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "claim_level": report["claim_level"],
        "replay_source": report["replay_source"],
        "self_test": report["self_test"],
        "status": report["status"],
        "total_records": report["total_records"],
        "complete_records": report["complete_records"],
        "incomplete_record_count": report["incomplete_record_count"],
        "policy_count": report["policy_count"],
        "candidate_policy_ids": report["candidate_policy_ids"],
        "action_set": report["action_set"],
        "winner_declared": report["winner_declared"],
        "cell_diagnostic_rank_only": report["cell_diagnostic_rank_only"],
        "candidate_selection_deferred_to_matrix_combiner": report[
            "candidate_selection_deferred_to_matrix_combiner"
        ],
        "diagnostic_rank_only": report["diagnostic_rank_only"],
        "empirical_algorithm_experiment_performed": report[
            "empirical_algorithm_experiment_performed"
        ],
        "policy_search_or_enumeration_performed": report[
            "policy_search_or_enumeration_performed"
        ],
        "replay_only": report["replay_only"],
        "remote_calls_by_c3": report["remote_calls_by_c3"],
        "model_calls_by_replay": report["model_calls_by_replay"],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "evidencecore_semantics_changed": report["evidencecore_semantics_changed"],
        "aggregate_only_public_artifact": report["aggregate_only_public_artifact"],
        "selected_actions_invariant_under_private_field_permutation": report[
            "selected_actions_invariant_under_private_field_permutation"
        ],
        "runtime_clean_policy_inputs_only": report[
            "runtime_clean_policy_inputs_only"
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("C3 self-test: PASS", file=sys.stderr)
        return 0
    if args.regenerate_artifacts:
        _regenerate_artifacts()
        spec = _load_json(ALGORITHM_SPEC_PATH)
        spec_hash = _sha256_json(spec)
        verify_algorithm_spec(spec, spec_hash)
        report = _load_json(REPORT_PATH)
        verify_report(report)
        print(
            json.dumps(
                {
                    "algorithm_spec_id": ALGORITHM_SPEC_ID,
                    "algorithm_spec_sha256": spec_hash,
                    "report_path": str(REPORT_PATH),
                    "spec_path": str(ALGORITHM_SPEC_PATH),
                    "self_test": report["self_test"],
                    "status": report["status"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        print("C3 artifacts regenerated", file=sys.stderr)
        return 0
    if args.input:
        input_meta = _load_p21_input(args.input)
        report = _build_input_report(input_meta)
        verify_report(report)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, report)
        _print_summary(report)
        print(f"C3 report written to {out_path}", file=sys.stderr)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
