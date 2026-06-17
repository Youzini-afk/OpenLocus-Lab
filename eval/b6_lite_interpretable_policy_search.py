#!/usr/bin/env python3
"""B6-lite interpretable policy search.

B6-lite is a live diagnostic stage that searches a small, pre-registered grammar
of interpretable routing rules over B3-style paired P21 ephemeral records.  It
runs P21 twice (``topk_plain_v0`` and ``hard_distractor_contrast_v0``) inside
the same workflow job, consumes the two ephemeral per-task record files, and
emits an aggregate-only public report and markdown doc.

The evaluator does not produce gates or promotions.  It publishes only
aggregate quality/cost/failure information and a Pareto frontier over the
searched policies.  Per-task details, candidate identifiers, paths, line ranges,
digests, snippets, prompts, responses, and gold spans stay inside ephemeral
records that are retained only in ``$RUNNER_TEMP`` and never uploaded.

Routing uses only public RUN-phase fields: ``task_bucket``, ``task_risk_tags``,
and allowlisted ``route_features`` booleans.  ``has_gold``, ``score_group``, and
outcome metrics are used only after a candidate policy is frozen, for scoring.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import p25_bucket_policy as p25

SCHEMA_VERSION = "b6-lite-interpretable-policy-search-v0"
GENERATED_BY = "b6_lite_interpretable_policy_search"
DEFAULT_OUT = Path(
    "artifacts/b6_lite_interpretable_policy_search/b6_lite_interpretable_policy_search_report.json"
)
DEFAULT_DOC = Path("docs/real-provider-ci/b6-lite-interpretable-policy-search.md")

B6_ROUTING_ACTIONS = [
    "use_p25_action",
    "candidate_baseline",
    "plain_span_narrow",
    "hard_distractor_filter",
    "abstain_filter",
    "weak_only",
]

# Public RUN-phase route features the policy search may consult.  Matches the
# allowlist used by P30 admission so that B6 stays consistent with upstream.
B6_ROUTE_FEATURE_ALLOWLIST = {
    "candidate_count",
    "candidate_support_exists",
    "unique_symbol_anchor",
    "exact_unique_symbol_anchor",
    "symbol_anchor",
    "regex_anchor",
    "local_anchor",
    "symbol_regex_agree_file",
    "symbol_regex_agree_span",
    "rrf_anchor_agree_file",
    "rrf_anchor_agree_span",
    "rrf_backed_by_anchor",
    "query_noise",
    "llm_span_narrow_valid",
    "llm_span_within_candidate",
    "dense_support_present",
    "graph_support_present",
}

FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "test_id",
    "candidate_id",
    "repo_id",
    "query",
    "path",
    "candidate_path",
    "start_line",
    "end_line",
    "line_range",
    "content_sha",
    "digest",
    "snippet",
    "prompt",
    "response",
    "raw_response",
    "gold_spans",
    "label",
    "labels",
    "private_labels",
    "decision_records",
    "candidate_meta",
    "score_group",
    "raw_query",
    "provider_key",
    "base_url",
    "api_key",
    "api_token",
    "api_secret",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/[A-Za-z0-9._/\-]{3,}"),
    re.compile(r"[A-Fa-f0-9]{32,}"),
    re.compile(r"https?://", re.I),
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"base[_-]?url", re.I),
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _safe_div(num: float, den: float) -> float | None:
    return num / den if den else None


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_outcome(raw: dict[str, Any], name: str) -> dict[str, Any]:
    src = raw.get(name)
    if isinstance(src, dict):
        return src
    for key in ("strategies", "outcomes", "strategy_results", "results", "metrics"):
        container = raw.get(key) or {}
        if isinstance(container, dict) and isinstance(container.get(name), dict):
            return container[name]
    return {}


def _outcome_from_dict(src: dict[str, Any]) -> dict[str, Any]:
    """Normalize an outcome dict with the scalar fields B6 needs."""
    floats: dict[str, float | None] = {}
    for k in (
        "file_recall_at_5",
        "span_f0_5",
        "primary_false_positive_rate",
        "no_gold_false_primary_rate",
        "abstain_rate",
    ):
        floats[k] = _as_float(src.get(k))
    ints: dict[str, int] = {}
    for k in ("added_gold_span", "added_false_span"):
        ints[k] = _as_int(src.get(k))
    return {
        **floats,
        **ints,
        "abstained": bool(src.get("abstained", False)),
    }


def _zero_abstain_outcome() -> dict[str, Any]:
    return {
        "file_recall_at_5": 0.0,
        "span_f0_5": 0.0,
        "primary_false_positive_rate": 0.0,
        "no_gold_false_primary_rate": 0.0,
        "abstain_rate": 1.0,
        "added_gold_span": 0,
        "added_false_span": 0,
        "abstained": True,
    }


# ---------------------------------------------------------------------------
# Task normalization (aggregate-safe fields only)
# ---------------------------------------------------------------------------


def _normalize_task(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Extract public fields and per-strategy outcomes from an ephemeral P21 record."""
    tid = raw.get("task_id") or raw.get("test_id")
    if not tid:
        return None

    task_bucket = p25.sanitize_public_bucket(raw.get("task_bucket", "unknown"))
    risk_tags = raw.get("task_risk_tags") or []
    if isinstance(risk_tags, str):
        risk_tags = [risk_tags]
    if not isinstance(risk_tags, list):
        risk_tags = []
    risk_tags = p25.sanitize_public_tags(risk_tags)

    if raw.get("score_group") == "positive":
        has_gold = True
    elif raw.get("score_group") == "no_gold":
        has_gold = False
    else:
        has_gold = bool(raw.get("has_gold", False))

    route_features_raw = raw.get("route_features")
    route_features = (
        {k: v for k, v in route_features_raw.items() if k in B6_ROUTE_FEATURE_ALLOWLIST}
        if isinstance(route_features_raw, dict)
        else {}
    )

    weak_src = _extract_outcome(raw, "weak_candidate_only") or _extract_outcome(
        raw, "supporting_only"
    )
    weak_outcome = (
        _outcome_from_dict(weak_src)
        if weak_src
        else {**_zero_abstain_outcome(), "source": "fallback_zero_abstain"}
    )

    outcomes: dict[str, Any] = {
        "candidate_baseline": _outcome_from_dict(_extract_outcome(raw, "candidate_baseline")),
        "llm_span_narrow": _outcome_from_dict(_extract_outcome(raw, "llm_span_narrow")),
        "llm_filter": _outcome_from_dict(_extract_outcome(raw, "llm_filter")),
        "llm_abstain_filter": _outcome_from_dict(_extract_outcome(raw, "llm_abstain_filter")),
        "weak_candidate_only": weak_outcome,
        "supporting_only": _outcome_from_dict(
            _extract_outcome(raw, "supporting_only") or _zero_abstain_outcome()
        ),
    }

    return {
        "task_id": tid,
        # repo_id is kept only in memory for leave-one-repo diagnostics; it is
        # never emitted in the public report.
        "repo_id": raw.get("repo_id"),
        "task_bucket": task_bucket,
        "task_risk_tags": risk_tags,
        "has_gold": has_gold,
        "route_features": route_features,
        "outcomes": outcomes,
    }


def _load_records(path: Path) -> list[dict[str, Any]]:
    raw_rows = p25.load_p21_inputs([path])
    normalized: list[dict[str, Any]] = []
    for row in raw_rows:
        if isinstance(row, dict) and row.get("_p25_input_summary_marker"):
            continue
        if isinstance(row, dict) and row.get("_p25_unsupported_schema_marker"):
            continue
        if isinstance(row, dict) and row.get("_p25_input_empty_marker"):
            continue
        norm = _normalize_task(row)
        if norm is not None:
            normalized.append(norm)
    return normalized


# ---------------------------------------------------------------------------
# Routing features (label/outcome free, except where noted)
# ---------------------------------------------------------------------------


def _labels(task: dict[str, Any]) -> set[str]:
    return p25.bucket_labels(task)


def _has_support(task: dict[str, Any]) -> bool:
    rf = task.get("route_features") or {}
    return bool(rf.get("candidate_support_exists")) or int(rf.get("candidate_count") or 0) > 0


def _exact_unique(task: dict[str, Any]) -> bool:
    labels = _labels(task)
    return bool(
        (labels & {"exact_symbol", "exact_symbol_unique", "exact_symbol_match"})
        and (labels & {"unique", "unique_symbol", "symbol_anchor"})
    )


def _positive_like(task: dict[str, Any]) -> bool:
    return bool(_labels(task) & p25.POSITIVE_BUCKET_KEYS)


def _negative_like(task: dict[str, Any]) -> bool:
    # Do not route on the gold-equivalent `no_gold` label. Public negative-like
    # buckets/tags such as `negative`, `dense_false_positive`, or
    # `hard_distractor` remain allowed RUN-phase routing features.
    allowed_negative_keys = set(p25.NEGATIVE_BUCKET_KEYS) - {"no_gold"}
    return bool(_labels(task) & allowed_negative_keys)


def _hard_distractor_like(task: dict[str, Any]) -> bool:
    """Hard/dense/negative cases WITHOUT using has_gold (routing invariant)."""
    labels = _labels(task)
    return bool(
        labels
        & {"hard_distractor", "dense_false_positive", "dense_quiver_trap"}
    ) or _negative_like(task)


def _ambiguous_like(task: dict[str, Any]) -> bool:
    return bool(_labels(task) & {"ambiguous", "hallucination_risk", "weak_candidates"})


def _query_noise(task: dict[str, Any]) -> bool:
    qn = (task.get("route_features") or {}).get("query_noise")
    try:
        return bool(float(qn) > 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _noisy_or_ambiguous(task: dict[str, Any]) -> bool:
    return _ambiguous_like(task) or _query_noise(task)


# ---------------------------------------------------------------------------
# Actions -> outcomes
# ---------------------------------------------------------------------------


def _p25_action(task: dict[str, Any]) -> str:
    """Resolve the P25 bucket-routed action for a plain record."""
    calibrated = p25.choose_negative_strategy([task])
    return p25.route_bucket_routed_v0(task, calibrated)


def _resolve_outcome(
    action: str, plain: dict[str, Any], hard: dict[str, Any]
) -> dict[str, Any]:
    if action == "use_p25_action":
        p25_action = _p25_action(plain)
        if p25_action == "candidate_baseline":
            return plain["outcomes"]["candidate_baseline"]
        if p25_action == "llm_span_narrow":
            return plain["outcomes"]["llm_span_narrow"]
        if p25_action == "llm_filter":
            return plain["outcomes"]["llm_filter"]
        if p25_action == "llm_abstain_filter":
            return plain["outcomes"]["llm_abstain_filter"]
        raise ValueError(f"unexpected p25 action: {p25_action}")
    if action == "candidate_baseline":
        return plain["outcomes"]["candidate_baseline"]
    if action == "plain_span_narrow":
        return plain["outcomes"]["llm_span_narrow"]
    if action == "hard_distractor_filter":
        return hard["outcomes"]["llm_filter"]
    if action == "abstain_filter":
        return plain["outcomes"]["llm_abstain_filter"]
    if action == "weak_only":
        return plain["outcomes"]["weak_candidate_only"]
    raise ValueError(f"unknown action: {action}")


def _action_costs_llm(action: str, plain: dict[str, Any]) -> bool:
    """Return True if the selected action requires a provider LLM call."""
    if action in {"plain_span_narrow", "hard_distractor_filter", "abstain_filter"}:
        return True
    if action in {"candidate_baseline", "weak_only"}:
        return False
    if action == "use_p25_action":
        return _p25_action(plain) != "candidate_baseline"
    return False


# ---------------------------------------------------------------------------
# Policy representation
# ---------------------------------------------------------------------------


@dataclass
class Policy:
    name: str
    source: str  # "baseline" or "searched"
    rules: list[dict[str, Any]]
    action_fn: Callable[[dict[str, Any]], str]
    action_list: list[str] = field(default_factory=list)

    def action_for(self, task: dict[str, Any]) -> str:
        return self.action_fn(task)


def _rule(name: str, predicates: list[str], condition: Callable[[dict], bool], action: str) -> dict[str, Any]:
    return {
        "name": name,
        "predicates": predicates,
        "condition": condition,
        "action": action,
    }


def _make_first_match_action_fn(rules: list[dict[str, Any]]) -> Callable[[dict], str]:
    def fn(task: dict[str, Any]) -> str:
        for rule in rules:
            if rule["condition"](task):
                return rule["action"]
        raise RuntimeError("policy reached end without a default rule")

    return fn


def _policy_name(rules: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for rule in rules:
        if rule.get("is_default"):
            parts.append(f"default_{rule['action']}")
        else:
            parts.append(rule["name"])
    return "_".join(parts)[:200]


# ---------------------------------------------------------------------------
# Fixed baseline policies
# ---------------------------------------------------------------------------


def _fixed_policies() -> list[Policy]:
    policies: list[Policy] = []

    # P25 reference: always delegate to P25 bucket routing over the plain pack.
    p25_default_rules = [
        _rule(
            "p25_reference_default",
            ["always_true"],
            lambda _t: True,
            "use_p25_action",
        )
    ]
    p25_default_rules[0]["is_default"] = True
    policies.append(
        Policy(
            name="p25_bucket_routed_v0_plain",
            source="baseline",
            rules=p25_default_rules,
            action_fn=_make_first_match_action_fn(p25_default_rules),
        )
    )

    # rmc_local_conservative_v0
    rmc_local_rules = [
        _rule(
            "rmc_local_hard",
            ["hard_distractor_like"],
            _hard_distractor_like,
            "weak_only",
        ),
        _rule("rmc_local_default", ["always_true"], lambda _t: True, "candidate_baseline"),
    ]
    rmc_local_rules[-1]["is_default"] = True
    policies.append(
        Policy(
            name="rmc_local_conservative_v0",
            source="baseline",
            rules=rmc_local_rules,
            action_fn=_make_first_match_action_fn(rmc_local_rules),
        )
    )

    # rmc_llm_pack_routed_v0
    rmc_pack_rules = [
        _rule("rmc_pack_exact", ["exact_unique"], _exact_unique, "candidate_baseline"),
        _rule(
            "rmc_pack_hard",
            ["hard_distractor_like"],
            _hard_distractor_like,
            "hard_distractor_filter",
        ),
        _rule(
            "rmc_pack_positive",
            ["positive_like", "support_exists"],
            lambda t: _positive_like(t) and _has_support(t),
            "plain_span_narrow",
        ),
        _rule("rmc_pack_default", ["always_true"], lambda _t: True, "candidate_baseline"),
    ]
    rmc_pack_rules[-1]["is_default"] = True
    policies.append(
        Policy(
            name="rmc_llm_pack_routed_v0",
            source="baseline",
            rules=rmc_pack_rules,
            action_fn=_make_first_match_action_fn(rmc_pack_rules),
        )
    )

    # rmc_hybrid_v0
    rmc_hybrid_rules = [
        _rule("rmc_hybrid_exact", ["exact_unique"], _exact_unique, "candidate_baseline"),
        _rule(
            "rmc_hybrid_unsupported",
            ["no_support"],
            lambda t: not _has_support(t),
            "weak_only",
        ),
        _rule(
            "rmc_hybrid_hard",
            ["hard_distractor_like"],
            _hard_distractor_like,
            "hard_distractor_filter",
        ),
        _rule(
            "rmc_hybrid_positive",
            ["positive_like"],
            _positive_like,
            "plain_span_narrow",
        ),
        _rule("rmc_hybrid_default", ["always_true"], lambda _t: True, "candidate_baseline"),
    ]
    rmc_hybrid_rules[-1]["is_default"] = True
    policies.append(
        Policy(
            name="rmc_hybrid_v0",
            source="baseline",
            rules=rmc_hybrid_rules,
            action_fn=_make_first_match_action_fn(rmc_hybrid_rules),
        )
    )

    return policies


# ---------------------------------------------------------------------------
# Searched rule grammar
# ---------------------------------------------------------------------------


def _min_rule_support(task_count: int) -> int:
    return max(1, min(3, task_count))


def _support(condition: Callable[[dict], bool], tasks: list[dict[str, Any]]) -> int:
    return sum(1 for t in tasks if condition(t))


def _generate_candidate_rules(
    tasks: list[dict[str, Any]],
) -> tuple[list[Policy], int, int]:
    """Return (searched policies, rules_considered, rules_pruned_by_min_support)."""
    min_support = _min_rule_support(len(tasks))
    rules_considered = 0
    rules_pruned = 0

    slots: list[list[dict[str, Any] | None]] = [[] for _ in range(4)]

    # Slot 0: exact-unique rule.
    rules_considered += 1
    if _support(_exact_unique, tasks) >= min_support:
        slots[0].append(
            _rule(
                "exact_unique_baseline",
                ["exact_symbol", "unique_symbol"],
                _exact_unique,
                "candidate_baseline",
            )
        )
    else:
        rules_pruned += 1
    slots[0].append(None)

    # Slot 1: positive supported -> span narrow.
    rules_considered += 1
    if _support(lambda t: _positive_like(t) and _has_support(t), tasks) >= min_support:
        slots[1].append(
            _rule(
                "positive_span_narrow",
                ["bucket_in_positive_set", "candidate_support_exists"],
                lambda t: _positive_like(t) and _has_support(t),
                "plain_span_narrow",
            )
        )
    else:
        rules_pruned += 1
    slots[1].append(None)

    # Slot 2: hard/dense/negative -> {hard_filter, abstain, weak}.
    rules_considered += 1
    if _support(_hard_distractor_like, tasks) >= min_support:
        for action in ("hard_distractor_filter", "abstain_filter", "weak_only"):
            slots[2].append(
                _rule(
                    f"negative_{action}",
                    ["hard_distractor_like"],
                    _hard_distractor_like,
                    action,
                )
            )
    else:
        rules_pruned += 3
    slots[2].append(None)

    # Slot 3: ambiguous or query_noise -> {use_p25, abstain, weak}.
    rules_considered += 1
    if _support(_noisy_or_ambiguous, tasks) >= min_support:
        for action in ("use_p25_action", "abstain_filter", "weak_only"):
            slots[3].append(
                _rule(
                    f"ambiguous_query_{action}",
                    ["ambiguous_or_query_noise"],
                    _noisy_or_ambiguous,
                    action,
                )
            )
    else:
        rules_pruned += 3
    slots[3].append(None)

    # Slot 4: default rule (required).
    default_rules = [
        _rule("default_use_p25", ["always_true"], lambda _t: True, "use_p25_action"),
        _rule("default_baseline", ["always_true"], lambda _t: True, "candidate_baseline"),
    ]
    for dr in default_rules:
        dr["is_default"] = True

    policies: list[Policy] = []
    seen_names: set[str] = set()
    for combo in itertools.product(*slots, default_rules):
        rules = [r for r in combo if r is not None]
        # Default rule must be present and last.
        if not rules or not rules[-1].get("is_default"):
            continue
        if len(rules) > 5:
            continue
        name = _policy_name(rules)
        if name in seen_names:
            continue
        seen_names.add(name)
        policies.append(
            Policy(
                name=name,
                source="searched",
                rules=rules,
                action_fn=_make_first_match_action_fn(rules),
            )
        )

    return policies, rules_considered, rules_pruned


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _metrics_from_action_list(
    plain_tasks: list[dict[str, Any]],
    hard_by_task: dict[str, dict[str, Any]],
    action_list: list[str],
    p25_action_list: list[str] | None = None,
) -> dict[str, Any]:
    task_count = len(plain_tasks)
    pos_count = sum(1 for t in plain_tasks if t.get("has_gold"))
    no_gold_count = task_count - pos_count
    action_counts: Counter[str] = Counter()
    spans: list[float] = []
    pfps: list[float] = []
    no_gold_pfps: list[float] = []
    added_gold = 0
    added_false = 0
    effective_llm = 0
    fallback_count = 0
    missing_count = 0
    gold_kill = 0
    p25_added_false = 0

    for i, plain in enumerate(plain_tasks):
        tid = str(plain["task_id"])
        hard = hard_by_task[tid]
        action = action_list[i]
        action_counts[action] += 1
        outcome = _resolve_outcome(action, plain, hard)
        if outcome.get("source") == "fallback_zero_abstain":
            fallback_count += 1
        ag = int(outcome.get("added_gold_span") or 0)
        af = int(outcome.get("added_false_span") or 0)
        added_gold += ag
        added_false += af

        sf = outcome.get("span_f0_5")
        if sf is not None:
            spans.append(float(sf))
        pfp = outcome.get("primary_false_positive_rate")
        if pfp is not None:
            pfps.append(float(pfp))
        if not plain.get("has_gold"):
            ng = outcome.get("no_gold_false_primary_rate")
            if ng is None:
                ng = pfp
            if ng is not None:
                no_gold_pfps.append(float(ng))

        if _action_costs_llm(action, plain):
            effective_llm += 1
        if action == "weak_only" and outcome.get("source") == "fallback_zero_abstain":
            missing_count += 1

        if p25_action_list is not None:
            p25_action = p25_action_list[i]
            p25_outcome = _resolve_outcome(p25_action, plain, hard)
            p25_ag = int(p25_outcome.get("added_gold_span") or 0)
            p25_af = int(p25_outcome.get("added_false_span") or 0)
            p25_added_false += p25_af
            if plain.get("has_gold") and p25_ag > 0 and ag == 0:
                gold_kill += 1

    mean_span_f05 = _avg(spans)
    mean_pfp = _avg(pfps)
    no_gold_pfp = _avg(no_gold_pfps)

    return {
        "task_count": task_count,
        "positive_task_count": pos_count,
        "no_gold_task_count": no_gold_count,
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "false_per_gold": _safe_div(added_false, added_gold),
        "mean_span_f05": mean_span_f05,
        "mean_primary_false_positive_rate": mean_pfp,
        "no_gold_false_primary_rate": no_gold_pfp,
        "action_counts": {a: int(action_counts.get(a, 0)) for a in B6_ROUTING_ACTIONS},
        "action_rates": {a: _safe_div(action_counts.get(a, 0), task_count) for a in B6_ROUTING_ACTIONS},
        "effective_llm_action_count": effective_llm,
        "effective_llm_action_rate": _safe_div(effective_llm, task_count),
        "provider_call_estimate": effective_llm,
        "provider_call_estimate_not_measured": True,
        "net_span_value_2x": added_gold - 2 * added_false,
        "gold_kill_vs_p25": gold_kill,
        "false_reduction_vs_p25": (p25_added_false - added_false) if p25_action_list is not None else None,
        "comparable_task_count": task_count,
        "missing_action_outcome_count": missing_count,
        "fallback_to_baseline_count": fallback_count,
        "excluded_task_count": 0,
    }


def _evaluate_policies(
    plain_tasks: list[dict[str, Any]],
    hard_by_task: dict[str, dict[str, Any]],
    policies: list[Policy],
) -> dict[str, dict[str, Any]]:
    """Evaluate every policy and attach its per-task action list in place."""
    # P25 baseline action list (for gold-kill/false-reduction comparisons).
    p25_action_list = ["use_p25_action"] * len(plain_tasks)

    metrics_by_name: dict[str, dict[str, Any]] = {}
    for policy in policies:
        policy.action_list = [policy.action_for(t) for t in plain_tasks]
        seen: set[str] = set()
        for p in policies:
            if p is policy:
                continue
            if tuple(p.action_list) == tuple(policy.action_list):
                seen.add(p.name)
        metrics = _metrics_from_action_list(
            plain_tasks, hard_by_task, policy.action_list, p25_action_list
        )
        metrics["source"] = policy.source
        metrics["policy_rules"] = [
            {
                "name": r["name"],
                "predicates": list(r["predicates"]),
                "action": r["action"],
                "is_default": bool(r.get("is_default")),
            }
            for r in policy.rules
        ]
        metrics["duplicate_action_signature_policies"] = sorted(seen)
        metrics_by_name[policy.name] = metrics
    return metrics_by_name


# ---------------------------------------------------------------------------
# Pareto frontier
# ---------------------------------------------------------------------------


def _dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Return True if a is no worse in all objectives and strictly better in one."""
    dims: list[tuple[float, float, bool]] = [
        (_as_float(a.get("mean_span_f05")) or 0.0, _as_float(b.get("mean_span_f05")) or 0.0, True),
        (float(a.get("net_span_value_2x") or 0), float(b.get("net_span_value_2x") or 0), True),
        (float(a.get("added_false_span") or 0), float(b.get("added_false_span") or 0), False),
        (_as_float(a.get("mean_primary_false_positive_rate")) or 0.0, _as_float(b.get("mean_primary_false_positive_rate")) or 0.0, False),
        (float(a.get("provider_call_estimate") or 0), float(b.get("provider_call_estimate") or 0), False),
    ]
    strict = False
    for av, bv, maximize in dims:
        if maximize:
            if av < bv:
                return False
            if av > bv:
                strict = True
        else:
            if av > bv:
                return False
            if av < bv:
                strict = True
    return strict


def _compute_frontier(
    metrics_by_name: dict[str, dict[str, Any]],
    p25_name: str = "p25_bucket_routed_v0_plain",
) -> dict[str, Any]:
    names = list(metrics_by_name)
    dominated_by: dict[str, set[str]] = {n: set() for n in names}
    for a in names:
        for b in names:
            if a == b:
                continue
            if _dominates(metrics_by_name[a], metrics_by_name[b]):
                dominated_by[b].add(a)

    frontier = [n for n in names if not dominated_by[n]]
    p25_metrics = metrics_by_name.get(p25_name)
    dominated_by_p25: list[str] = []
    if p25_metrics:
        for n in names:
            if n == p25_name:
                continue
            if _dominates(p25_metrics, metrics_by_name[n]):
                dominated_by_p25.append(n)

    return {
        "frontier": sorted(frontier),
        "frontier_size": len(frontier),
        "dominated_by_p25": sorted(dominated_by_p25),
        "policies_dominated_by_p25": len(dominated_by_p25),
        "non_dominated_observed": sorted(frontier),
    }


# ---------------------------------------------------------------------------
# Overfit diagnostics
# ---------------------------------------------------------------------------


def _rank_order(metrics_by_name: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        metrics_by_name,
        key=lambda n: float(metrics_by_name[n].get("net_span_value_2x") or 0),
        reverse=True,
    )


def _mean_rank_delta(
    full: dict[str, dict[str, Any]], subset: dict[str, dict[str, Any]]
) -> float | None:
    names = [n for n in full if n in subset]
    if not names:
        return None
    full_order = _rank_order(full)
    sub_order = _rank_order(subset)
    full_rank = {n: i for i, n in enumerate(full_order)}
    sub_rank = {n: i for i, n in enumerate(sub_order)}
    deltas = [abs(full_rank[n] - sub_rank[n]) for n in names]
    return sum(deltas) / len(deltas)


def _leave_one_out_diagnostics(
    policies: list[Policy],
    plain_tasks: list[dict[str, Any]],
    hard_by_task: dict[str, dict[str, Any]],
    full_metrics: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    # repo leave-one-out (repo_id stays in memory only).
    repo_ids: list[str] = sorted({str(t.get("repo_id")) for t in plain_tasks if t.get("repo_id")})
    repo_diagnostics: dict[str, Any] = {
        "available_repo_count": len(repo_ids),
        "leave_one_repo_unavailable_reason": None,
        "mean_rank_delta": None,
        "repo_fold_count": 0,
    }
    if len(repo_ids) > 1:
        deltas: list[float] = []
        for rid in repo_ids:
            sub_plain = [t for t in plain_tasks if t.get("repo_id") != rid]
            sub_hard = {str(t["task_id"]): hard_by_task[str(t["task_id"])] for t in sub_plain}
            sub_metrics = _subset_metrics(policies, sub_plain, sub_hard)
            delta = _mean_rank_delta(full_metrics, sub_metrics)
            if delta is not None:
                deltas.append(delta)
        if deltas:
            repo_diagnostics["mean_rank_delta"] = sum(deltas) / len(deltas)
            repo_diagnostics["repo_fold_count"] = len(deltas)
    else:
        repo_diagnostics["leave_one_repo_unavailable_reason"] = (
            "insufficient_repo_variety_for_leave_one_repo_out"
        )

    # bucket leave-one-out (buckets are public, but still only aggregate summaries).
    buckets = sorted({t["task_bucket"] for t in plain_tasks})
    bucket_diagnostics: dict[str, Any] = {
        "available_bucket_count": len(buckets),
        "leave_one_bucket_unavailable_reason": None,
        "mean_rank_delta": None,
        "bucket_fold_count": 0,
    }
    if len(buckets) > 1:
        deltas = []
        for bucket in buckets:
            sub_plain = [t for t in plain_tasks if t["task_bucket"] != bucket]
            sub_hard = {str(t["task_id"]): hard_by_task[str(t["task_id"])] for t in sub_plain}
            sub_metrics = _subset_metrics(policies, sub_plain, sub_hard)
            delta = _mean_rank_delta(full_metrics, sub_metrics)
            if delta is not None:
                deltas.append(delta)
        if deltas:
            bucket_diagnostics["mean_rank_delta"] = sum(deltas) / len(deltas)
            bucket_diagnostics["bucket_fold_count"] = len(deltas)
    else:
        bucket_diagnostics["leave_one_bucket_unavailable_reason"] = (
            "insufficient_bucket_variety_for_leave_one_bucket_out"
        )

    return {
        "leave_one_repo_out": repo_diagnostics,
        "leave_one_bucket_out": bucket_diagnostics,
    }


def _subset_metrics(
    policies: list[Policy],
    sub_plain: list[dict[str, Any]],
    sub_hard: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    p25_action_list = ["use_p25_action"] * len(sub_plain)
    metrics: dict[str, dict[str, Any]] = {}
    for policy in policies:
        action_list = [policy.action_for(t) for t in sub_plain]
        metrics[policy.name] = _metrics_from_action_list(
            sub_plain, sub_hard, action_list, p25_action_list
        )
    return metrics


def _routing_invariance_check(
    policies: list[Policy], plain_tasks: list[dict[str, Any]]
) -> dict[str, Any]:
    """Ensure selected actions do not depend on SCORE/gold-only fields.

    This checks the routing action strings only. Outcome scoring may still use
    labels/gold after policy actions are frozen.
    """
    mutated = json.loads(json.dumps(plain_tasks))
    for idx, task in enumerate(mutated):
        task["has_gold"] = not bool(task.get("has_gold"))
        task["score_group"] = "no_gold" if idx % 2 == 0 else "positive"
        task.pop("gold_spans", None)
        task.pop("private_labels", None)
        task.pop("label", None)
        task.pop("labels", None)
        tags = [t for t in task.get("task_risk_tags", []) if t != "no_gold"]
        if idx % 2 == 0:
            tags.append("no_gold")
        task["task_risk_tags"] = tags

    changed = 0
    changed_policies: list[str] = []
    for policy in policies:
        original_actions = [policy.action_for(t) for t in plain_tasks]
        mutated_actions = [policy.action_for(t) for t in mutated]
        if original_actions != mutated_actions:
            changed += 1
            changed_policies.append(policy.name)
    return {
        "score_fields_removed_or_flipped": True,
        "selected_actions_invariant": changed == 0,
        "changed_policy_count": changed,
        "changed_policy_examples": changed_policies[:5],
    }


# ---------------------------------------------------------------------------
# Report assembly and safety
# ---------------------------------------------------------------------------


def _base_report(status: str, self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "status": status,
        "self_test": bool(self_test),
        "live_quality_experiment": not self_test,
        "diagnostic_policy_search": True,
        "aggregate_only_public_artifact": True,
        "public_per_task_rows": False,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "policy_search_not_admission": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "remote_calls_by_policy_search": 0,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "task_ids_in_artifact": False,
        "candidate_ids_in_artifact": False,
        "repo_ids_in_artifact": False,
    }


def _walk_forbidden(obj: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key) in FORBIDDEN_PUBLIC_KEYS:
                violations.append(f"{path}.{key}")
            violations.extend(_walk_forbidden(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_walk_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        if len(obj) > 256:
            violations.append(f"{path}:long_string")
        elif any(p.search(obj) for p in FORBIDDEN_VALUE_PATTERNS):
            violations.append(f"{path}:private_like_value")
    return violations


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("bad schema_version")
    if report.get("status") not in {"ok", "self_test_only", "blocked_task_set_mismatch"}:
        raise ValueError("bad status")

    must_be_true = [
        "not_evidence",
        "llm_output_not_evidence",
        "aggregate_only_public_artifact",
        "candidate_not_fact",
        "policy_search_not_admission",
        "diagnostic_policy_search",
    ]
    for key in must_be_true:
        if report.get(key) is not True:
            raise ValueError(f"{key} must be true")

    must_be_false = [
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "task_ids_in_artifact",
        "candidate_ids_in_artifact",
        "repo_ids_in_artifact",
        "raw_prompts_stored",
        "raw_responses_stored",
        "raw_snippets_stored",
        "raw_snippets_committed",
        "raw_paths_in_artifact",
        "raw_line_ranges_in_artifact",
        "raw_digests_in_artifact",
        "private_labels_committed",
        "gold_spans_in_artifact",
        "public_per_task_rows",
    ]
    for key in must_be_false:
        if report.get(key) is not False:
            raise ValueError(f"{key} must be false")

    if report.get("remote_calls_by_policy_search") != 0:
        raise ValueError("remote_calls_by_policy_search must be 0")

    violations = _walk_forbidden(report)
    if violations:
        raise ValueError("public report contains forbidden fields: " + ", ".join(violations[:5]))

    if report.get("status") == "ok":
        policies = report.get("policies") or {}
        if "p25_bucket_routed_v0_plain" not in policies:
            raise ValueError("P25 baseline missing from policies")
        search = report.get("search_accounting") or {}
        required_search_keys = [
            "candidate_policy_count",
            "rules_considered",
            "rules_pruned_by_min_support",
            "frontier_size",
            "policies_dominated_by_p25",
        ]
        for k in required_search_keys:
            if k not in search:
                raise ValueError(f"missing search_accounting.{k}")
        frontier = report.get("pareto_frontier") or {}
        if "frontier" not in frontier:
            raise ValueError("missing pareto_frontier.frontier")

        for name, metrics in policies.items():
            tc = metrics.get("task_count")
            if not isinstance(tc, int) or tc <= 0:
                raise ValueError(f"{name} has invalid task_count")
            if sum((metrics.get("action_counts") or {}).values()) != tc:
                raise ValueError(f"{name} action counts do not sum to {tc}")
            if "policy_rules" not in metrics:
                raise ValueError(f"{name} missing policy_rules")

        if "winner" in report or "default_recommendation" in report:
            raise ValueError("report must not declare a winner or default recommendation")
        inv = report.get("routing_invariance") or {}
        if inv.get("selected_actions_invariant") is not True:
            raise ValueError("routing changed when SCORE/gold fields were mutated")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.self_test:
        plain_tasks, hard_tasks, _ = _write_self_test_inputs()
    else:
        plain_tasks = _load_records(args.plain_records)
        hard_tasks = _load_records(args.hard_records)

    plain_ids = [str(t["task_id"]) for t in plain_tasks]
    hard_ids = [str(t["task_id"]) for t in hard_tasks]
    same_task_set = sorted(plain_ids) == sorted(hard_ids) and len(set(plain_ids)) == len(plain_ids)

    if not same_task_set:
        report = _base_report("blocked_task_set_mismatch", args.self_test)
        report.update({
            "same_task_set": False,
            "plain_task_count": len(plain_ids),
            "hard_task_count": len(hard_ids),
            "comparable_task_count": 0,
        })
        validate_report(report)
        return report

    hard_by_task = {str(t["task_id"]): t for t in hard_tasks}

    # Fixed baseline policies first.
    policies: list[Policy] = _fixed_policies()

    # Then generate searched policies from the pre-registered rule grammar.
    searched, rules_considered, rules_pruned = _generate_candidate_rules(plain_tasks)

    # Deduplicate searched policies by action signature against fixed baselines.
    fixed_sigs = {tuple(p.action_list) for p in policies if p.action_list}
    # Need to evaluate baselines to get signatures, but we haven't built action_list yet.
    # Easier: evaluate all policies together, then deduplicate.  For now append and dedupe after eval.
    policies.extend(searched)

    metrics_by_name = _evaluate_policies(plain_tasks, hard_by_task, policies)

    # Deduplicate by action signature; prefer baseline source names.
    deduped: dict[str, dict[str, Any]] = {}
    seen_sigs: dict[tuple[str, ...], str] = {}
    # Order matters: fixed policies were evaluated first, so prefer them.
    for name, metrics in metrics_by_name.items():
        sig = tuple(metrics.get("_action_list_marker", []))  # not stored; use policy action_list from object.
        # Re-derive signature from policy object.
        policy_obj = next(p for p in policies if p.name == name)
        sig = tuple(policy_obj.action_list)
        if sig in seen_sigs:
            continue
        seen_sigs[sig] = name
        deduped[name] = metrics

    # Update candidate count after deduplication.
    searched_names = {p.name for p in searched}
    candidate_policy_count = sum(
        1 for name in deduped if name in searched_names
    )

    frontier_info = _compute_frontier(deduped)

    # Mark each policy with frontier/dominance metadata.
    frontier_set = set(frontier_info["frontier"])
    dominated_by_p25_set = set(frontier_info["dominated_by_p25"])
    for name, metrics in deduped.items():
        metrics["dominated_by_p25"] = name in dominated_by_p25_set
        metrics["non_dominated_observed"] = name in frontier_set
        metrics["unstable_low_n"] = (
            metrics["task_count"] < 20
            or any(
                metrics["action_counts"].get(a, 0) > 0
                and metrics["action_counts"].get(a, 0) < _min_rule_support(metrics["task_count"])
                for a in B6_ROUTING_ACTIONS
            )
        )
        metrics["insufficient_support"] = False
        metrics["quality_cost_tradeoff"] = (
            "higher_span_value_tends_to_raise_false_or_cost"
            if metrics["net_span_value_2x"] is not None and metrics["provider_call_estimate"] > 0
            else "low_cost_low_return"
        )

    search_accounting = {
        "candidate_policy_count": candidate_policy_count,
        "rules_considered": rules_considered,
        "rules_pruned_by_min_support": rules_pruned,
        "frontier_size": frontier_info["frontier_size"],
        "policies_dominated_by_p25": frontier_info["policies_dominated_by_p25"],
    }

    overfit = _leave_one_out_diagnostics(
        [p for p in policies if p.name in deduped], plain_tasks, hard_by_task, deduped
    )
    routing_invariance = _routing_invariance_check(
        [p for p in policies if p.name in deduped], plain_tasks
    )

    claim_level = "observed_low_n_diagnostic_only"

    report = _base_report("self_test_only" if args.self_test else "ok", args.self_test)
    report.update({
        "same_task_set": True,
        "task_count": len(plain_tasks),
        "positive_task_count": sum(1 for t in plain_tasks if t.get("has_gold")),
        "no_gold_task_count": sum(1 for t in plain_tasks if not t.get("has_gold")),
        "comparable_task_count": len(plain_tasks),
        "claim_level": claim_level,
        "search_accounting": search_accounting,
        "policies": deduped,
        "pareto_frontier": {
            "frontier": sorted(frontier_info["frontier"]),
            "frontier_size": frontier_info["frontier_size"],
            "policies_dominated_by_p25": frontier_info["policies_dominated_by_p25"],
            "non_dominated_observed": sorted(frontier_info["non_dominated_observed"]),
        },
        "overfit_diagnostics": overfit,
        "routing_invariance": routing_invariance,
        "comparability": {
            "plain_pack_layout": "topk_plain_v0",
            "hard_pack_layout": "hard_distractor_contrast_v0",
            "same_model_required": True,
            "same_task_set_required": True,
            "same_task_set_observed": True,
        },
    })
    validate_report(report)
    return report


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# B6-lite Interpretable Policy Search")
    lines.append("")
    lines.append(f"Status: `{report['status']}`")
    lines.append("")
    lines.append(
        "B6-lite searches a small grammar of interpretable routing rules over paired "
        "P21 plain and hard-distractor ephemeral records.  It is a live diagnostic, not a "
        "gate or promotion.  The report is aggregate-only; per-task records stay in "
        "`$RUNNER_TEMP`."
    )
    lines.append("")
    if report.get("status") != "ok" and report.get("status") != "self_test_only":
        lines.append("Task-set mismatch blocked evaluation; no policies were scored.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("## Search accounting")
    search = report.get("search_accounting", {})
    for k, v in sorted(search.items()):
        lines.append(f"- `{k}`: {v}")
    lines.append("")

    lines.append("## Policies")
    header = (
        "| Policy | source | +gold | +false | F/G | SpanF0.5 | PFP | no-gold PFP | "
        "LLM calls | net 2x | gold kill vs P25 | false reduction vs P25 |"
    )
    lines.append(header)
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name in sorted(report.get("policies", {})):
        m = report["policies"][name]
        source = m.get("source", "unknown")
        lines.append(
            f"| `{name}` | {source} | {m['added_gold_span']} | {m['added_false_span']} | "
            f"{_fmt(m['false_per_gold'])} | {_fmt(m['mean_span_f05'])} | "
            f"{_fmt(m['mean_primary_false_positive_rate'])} | {_fmt(m['no_gold_false_primary_rate'])} | "
            f"{m['provider_call_estimate']} | {m['net_span_value_2x']} | "
            f"{m['gold_kill_vs_p25']} | {m['false_reduction_vs_p25']} |"
        )
    lines.append("")

    lines.append("## Pareto frontier")
    frontier = report.get("pareto_frontier", {})
    lines.append(f"Frontier size: {frontier.get('frontier_size')}")
    lines.append(f"Policies dominated by P25: {frontier.get('policies_dominated_by_p25')}")
    lines.append(f"Non-dominated policies: {', '.join(frontier.get('non_dominated_observed', []))}")
    lines.append("")

    lines.append("## Overfit diagnostics")
    ood = report.get("overfit_diagnostics", {})
    repo = ood.get("leave_one_repo_out", {})
    bucket = ood.get("leave_one_bucket_out", {})
    lines.append(f"- leave-one-repo-out folds: {repo.get('repo_fold_count')} "
                 f"(mean rank delta: {_fmt(repo.get('mean_rank_delta'))})")
    lines.append(f"- leave-one-bucket-out folds: {bucket.get('bucket_fold_count')} "
                 f"(mean rank delta: {_fmt(bucket.get('mean_rank_delta'))})")
    inv = report.get("routing_invariance", {})
    lines.append(
        f"- SCORE-field routing invariance: {inv.get('selected_actions_invariant')} "
        f"(changed policies: {inv.get('changed_policy_count')})"
    )
    lines.append("")

    lines.append("## Safety notes")
    lines.append("- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`.")
    lines.append("- `remote_calls_by_policy_search=0`; P21 makes calls, this evaluator does not.")
    lines.append("- Routing uses only public `task_bucket`, `task_risk_tags`, and allowlisted `route_features`.")
    lines.append("- Gold/SCORE fields are used only after a policy is frozen for aggregate scoring.")
    lines.append("- The public artifact is aggregate-only: no task IDs, repo IDs, paths, candidates, snippets, prompts, responses, or gold spans.")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Self-test inputs
# ---------------------------------------------------------------------------


def _write_self_test_inputs(
    tmp: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if tmp is None:
        tmp = Path("/tmp/opencode/b6-lite-self-test")
    rows = p25.make_self_test_tasks()
    plain_payload = {
        "schema_version": "p25-policy-records-ephemeral-v1",
        "not_artifact_for_commit": True,
        "records": rows,
    }
    plain_path = tmp / "plain.private.json"
    hard_path = tmp / "hard.private.json"
    tmp.mkdir(parents=True, exist_ok=True)
    plain_path.write_text(json.dumps(plain_payload), encoding="utf-8")

    # Hard records share the same tasks but expose a hard-distractor filter outcome.
    hard_rows = json.loads(json.dumps(rows))
    for row in hard_rows:
        # Make the hard pack's llm_filter look stronger on negative/hard rows.
        labels = set(row.get("task_risk_tags") or []) | {row.get("task_bucket")}
        if labels & {"negative", "hard_distractor", "ambiguous", "dense_false_positive"}:
            row["llm_filter"] = {
                "file_recall_at_5": 0.0,
                "span_f0_5": 0.0,
                "primary_false_positive_rate": 0.0,
                "no_gold_false_primary_rate": 0.0,
                "added_gold_span": 0,
                "added_false_span": 0,
            }
    hard_payload = {**plain_payload, "records": hard_rows}
    hard_path.write_text(json.dumps(hard_payload), encoding="utf-8")

    return _load_records(plain_path), _load_records(hard_path), {
        "plain": str(plain_path),
        "hard": str(hard_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plain-records", type=Path)
    parser.add_argument("--hard-records", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if not args.self_test and (not args.plain_records or not args.hard_records):
        parser.error("--plain-records and --hard-records are required unless --self-test")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, args.doc)
    print(json.dumps({
        "status": report["status"],
        "task_count": report.get("task_count"),
        "candidate_policy_count": report.get("search_accounting", {}).get("candidate_policy_count"),
        "frontier_size": report.get("pareto_frontier", {}).get("frontier_size") if report.get("pareto_frontier") else None,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
