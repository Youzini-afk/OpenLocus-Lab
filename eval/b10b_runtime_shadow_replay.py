#!/usr/bin/env python3
"""B10B Runtime-Shadow Replay (ambiguous branch only).

B10B is the next step after the B10 freeze of
``balanced_policy_v1_benchmark_routed``. It does **not** run any model, does
**not** search, does **not** tune policy quality, and does **not** defaultize.

It only tests whether a fixed, predeclared runtime-feature-only shadow
predicate can reproduce the **ambiguous branch** of the frozen benchmark-routed
spec's action on the same records. The shadow predicate reads only runtime
``route_features`` and never reads ``task_bucket``/``task_risk_tags``/
``has_gold``/``score_group``/outcome metrics.

Important claim boundary: this is **ambiguous-branch runtime-shadow only**. The
default action is still ``use_p25_action`` which delegates to the P25
benchmark-routed behavior. B10B does **not** prove a runtime-clean balanced
policy; it only tests whether runtime features can shadow the ambiguous branch.

Aggregate-only public artifacts: no task/repo/candidate/path/span/snippet/
prompt/response/gold/provider keys and no raw path/digest/provider strings.

Run::

    python3 eval/b10b_runtime_shadow_replay.py --self-test
    python3 eval/b10b_runtime_shadow_replay.py --records path/to/records.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b10b_runtime_shadow_replay"
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR
    / "balanced_policy_v1_runtime_shadow_ambiguous_branch.algorithm.json"
)
REPORT_PATH = ARTIFACT_DIR / "b10b_runtime_shadow_replay_report.json"

B10_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b10_runtime_feature_audit"
    / "balanced_policy_v1_benchmark_routed.algorithm.json"
)
B10_REPORT_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b10_runtime_feature_audit"
    / "b10_runtime_feature_audit_report.json"
)

SCHEMA_VERSION = "b10b-runtime-shadow-replay-report-v0"
SPEC_SCHEMA_VERSION = "b10b-runtime-shadow-spec-v0"
GENERATED_BY = "b10b_runtime_shadow_replay"
ALGORITHM_SPEC_ID = "balanced_policy_v1_runtime_shadow_ambiguous_branch"
B10_FROZEN_SPEC_ID = "balanced_policy_v1_benchmark_routed"

# Fixed generated_at so the spec hash is stable across runs (mirrors B10).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# The algorithm spec is generated deterministically (GENERATED_AT is fixed) so
# its SHA-256 is stable across runs. The self-test verifies stability by
# loading, re-hashing, and re-loading. There is no external pinned literal: the
# pin lives on disk as the spec file itself, mirroring the B10 freeze style.

TARGET_ACTIONS = ("weak_only", "use_p25_action")
SHADOW_ACTIONS = ("weak_only", "use_p25_action", "missing")

# Runtime features the shadow predicate is allowed to read. These are the only
# features consulted when computing the shadow action.
SHADOW_RUNTIME_FEATURES = (
    "query_noise",
    "candidate_support_exists",
    "local_anchor",
    "rrf_backed_by_anchor",
)

# Required runtime features for the shadow predicate to be evaluable on a
# record. If any is missing the record is marked missing; the shadow action is
# NOT silently defaulted to false.
REQUIRED_SHADOW_FEATURES = (
    "query_noise",
    "candidate_support_exists",
    "local_anchor",
    "rrf_backed_by_anchor",
)

# Benchmark public labels the target action reads (for provenance only; the
# shadow action never reads these).
TARGET_BENCHMARK_LABELS = ("task_bucket", "task_risk_tags")

AMBIGUOUS_LABELS = frozenset({"ambiguous", "hallucination_risk", "weak_candidates"})

# Outcome-metric fields the outcome-equivalence audit reads AFTER actions are
# chosen. These are scoring outputs, NEVER routing inputs. The shadow predicate
# never reads outcome_metrics; this list is audit-only.
OUTCOME_AUDIT_NUMERIC_FIELDS = (
    "added_gold_span",
    "added_false_span",
    "span_f0_5",
    "primary_false_positive_rate",
)

# Predeclared acceptance gates. Declared upfront in the algorithm spec so the
# verdict cannot be retro-fitted to whatever the replay produced.
PREDECLARED_ACCEPTANCE_GATES: dict[str, Any] = {
    "complete_feature_rate_min": 0.95,
    "overall_action_exact_agreement_min": 0.90,
    "target_weak_only_recall_min": 0.85,
    "target_use_p25_specificity_min": 0.90,
    "label_driven_ambiguous_recall_qn0_min": 0.75,
    "label_driven_ambiguous_min_denominator": 10,
    "shadow_weak_only_precision_min": 0.80,
    "cohens_kappa_min": 0.40,
    "outcome_metrics_leakage_tested": True,
    "no_silent_failure_required": True,
}

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")

ALLOWED_SUPPORT_CLAIMS = (
    "mechanics_only_synthetic_fixture",
    "empirical_replay_support_pending",
    "empirical_replay_support",
)

ALLOWED_SUPPORT_CLAIM_REASONS = (
    "synthetic_fixture_only",
    "insufficient_agreement",
    "insufficient_label_driven_denominator",
    "silent_failure_detected",
    "leakage_guard_incomplete",
)

# Small denominator below which the qn0 label-driven recall is considered
# unreliable (the metric is still reported but the verdict ORs in denom < 10).
LABEL_DRIVEN_QN0_MIN_DENOMINATOR = 10

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


# ---------------------------------------------------------------------------
# Target action (mirrors the B10 frozen benchmark-routed spec semantics)
# ---------------------------------------------------------------------------


def _ambiguous_like(task: dict[str, Any]) -> bool:
    """Mirror b6_lite._ambiguous_like: read task_bucket + task_risk_tags."""
    labels = set()
    bucket = task.get("task_bucket")
    if isinstance(bucket, str):
        labels.add(bucket)
    tags = task.get("task_risk_tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if isinstance(tags, list):
        for t in tags:
            if isinstance(t, str):
                labels.add(t)
    return bool(labels & AMBIGUOUS_LABELS)


def _query_noise(task: dict[str, Any]) -> bool:
    """Mirror b6_lite._query_noise: read route_features.query_noise > 0.

    Returns False if the feature is missing or non-numeric (target action
    treats missing query_noise as zero, consistent with the frozen spec).
    """
    rf = task.get("route_features") or {}
    qn = rf.get("query_noise")
    try:
        return bool(float(qn) > 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def target_ambiguous_or_query_noise(task: dict[str, Any]) -> bool:
    return _ambiguous_like(task) or _query_noise(task)


def target_action(task: dict[str, Any]) -> str:
    """Frozen benchmark-routed target action.

    If ``ambiguous_or_query_noise`` (benchmark public labels OR
    route_features.query_noise) is true => ``weak_only``; else
    ``use_p25_action``.
    """
    return "weak_only" if target_ambiguous_or_query_noise(task) else "use_p25_action"


# ---------------------------------------------------------------------------
# Shadow action (runtime features only, predeclared, no search/tuning)
# ---------------------------------------------------------------------------


def _route_feature(task: dict[str, Any], name: str) -> Any:
    rf = task.get("route_features") or {}
    if not isinstance(rf, dict):
        return None
    return rf.get(name)


def _feature_present(name: str, value: Any) -> bool:
    """A required shadow feature is present iff it is non-None and (for
    booleans) actually a bool, and (for query_noise) numeric."""
    if name == "query_noise":
        if value is None:
            return False
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False
    # boolean features
    return isinstance(value, bool)


def shadow_required_features_present(task: dict[str, Any]) -> tuple[bool, dict[str, bool]]:
    """Return (all_present, per_feature_present_map)."""
    present_map: dict[str, bool] = {}
    for feat in REQUIRED_SHADOW_FEATURES:
        present_map[feat] = _feature_present(feat, _route_feature(task, feat))
    return all(present_map.values()), present_map


def anchor_disagreement_proxy(task: dict[str, Any]) -> bool:
    """Anchor disagreement proxy from runtime booleans only.

    Definition: ``local_anchor`` exists (True) but is NOT ``rrf_backed_by_anchor``
    (anchor present locally but not corroborated by RRF). This must only be
    called when both required features are present; otherwise the record is
    marked missing and the proxy is not evaluated (no silent default).
    """
    local_anchor = _route_feature(task, "local_anchor")
    rrf_backed = _route_feature(task, "rrf_backed_by_anchor")
    if not (isinstance(local_anchor, bool) and isinstance(rrf_backed, bool)):
        raise ValueError(
            "anchor_disagreement_proxy called with missing required features; "
            "caller must check shadow_required_features_present first"
        )
    return bool(local_anchor) and not bool(rrf_backed)


def runtime_shadow_ambiguous(task: dict[str, Any]) -> bool:
    """Fixed predeclared shadow predicate (no search/tuning).

    ``runtime_shadow_ambiguous = query_noise OR (candidate_support_exists AND
    anchor_disagreement_proxy)``

    Must only be called when all REQUIRED_SHADOW_FEATURES are present.
    """
    qn = _route_feature(task, "query_noise")
    try:
        qn_fire = bool(float(qn) > 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError("runtime_shadow_ambiguous called with missing query_noise")
    cse = _route_feature(task, "candidate_support_exists")
    if not isinstance(cse, bool):
        raise ValueError(
            "runtime_shadow_ambiguous called with missing candidate_support_exists"
        )
    return bool(qn_fire) or (bool(cse) and anchor_disagreement_proxy(task))


def shadow_action(task: dict[str, Any]) -> tuple[str | None, dict[str, bool]]:
    """Return (shadow_action_or_None, required_feature_present_map).

    If any required runtime feature is missing, returns (None, present_map)
    and the caller marks the record missing; the shadow action is NOT
    silently defaulted to false.
    """
    all_present, present_map = shadow_required_features_present(task)
    if not all_present:
        return None, present_map
    return (
        "weak_only" if runtime_shadow_ambiguous(task) else "use_p25_action",
        present_map,
    )


# ---------------------------------------------------------------------------
# Outcome-equivalence audit helpers (audit-only; outcomes are scoring outputs,
# NEVER routing inputs)
# ---------------------------------------------------------------------------


def _outcome_metrics_usable(om: Any) -> bool:
    """Outcome metrics are usable for the audit iff it is a non-None dict in
    which every numeric audit field is present and a real number."""
    if not isinstance(om, dict):
        return False
    for field in OUTCOME_AUDIT_NUMERIC_FIELDS:
        if field not in om:
            return False
        if not _is_number(om.get(field)):
            return False
    return True


# Per-strategy keys in a P21/P25 ephemeral record that store outcome dicts.
# The outcome_audit reads these ONLY AFTER the target/shadow actions are
# chosen; the shadow predicate NEVER reads them (audit-only).
_P21_STRATEGY_KEYS = ("weak_candidate_only", "candidate_baseline")


def _extract_outcome_metrics(record: dict[str, Any], target_action_value: str) -> Any:
    """Return a usable outcome_metrics dict for the outcome-equivalence
    audit, or None if no usable outcome data is available.

    Resolution order (audit-only; the shadow predicate never reads outcomes):

    1. ``record["outcome_metrics"]`` exists and is usable (synthetic-fixture
       format, or any record carrying a top-level outcome_metrics dict with
       all four numeric audit fields). Use it directly.
    2. Else if P21 ephemeral per-strategy dicts are present:
       - If ``record["weak_candidate_only"]`` is present AND
         ``target_action == "weak_only"``, extract the audit fields from
         ``record["weak_candidate_only"]``.
       - Else if ``record["candidate_baseline"]`` is present AND
         ``target_action == "use_p25_action"``, extract the audit fields from
         ``record["candidate_baseline"]``.
       The extraction builds a NEW dict in memory (it does NOT mutate the
       record) containing only the four OUTCOME_AUDIT_NUMERIC_FIELDS.
    3. Else, return None (record has no outcome data for the audit; the
       outcome_audit will mark the partition as ``no_outcome_data`` if no
       record contributes).

    The P21 per-strategy dicts store additional non-numeric fields (e.g.
    ``abstained``, ``file_recall_at_5``); only the four numeric audit
    fields are extracted, and only when all four are present and numeric.
    """
    om = record.get("outcome_metrics")
    if _outcome_metrics_usable(om):
        return om
    if target_action_value == "weak_only":
        strategy_dict = record.get("weak_candidate_only")
    elif target_action_value == "use_p25_action":
        strategy_dict = record.get("candidate_baseline")
    else:
        strategy_dict = None
    if isinstance(strategy_dict, dict):
        extracted: dict[str, Any] = {}
        for field in OUTCOME_AUDIT_NUMERIC_FIELDS:
            value = strategy_dict.get(field)
            if not _is_number(value):
                return None
            extracted[field] = value
        return extracted
    return None


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _outcome_partition_summary(oms: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(oms),
        "mean_added_gold_span": _mean([float(o["added_gold_span"]) for o in oms]),
        "mean_added_false_span": _mean([float(o["added_false_span"]) for o in oms]),
        "mean_span_f0_5": _mean([float(o["span_f0_5"]) for o in oms]),
        "mean_primary_false_positive_rate": _mean(
            [float(o["primary_false_positive_rate"]) for o in oms]
        ),
    }


# ---------------------------------------------------------------------------
# Replay over records (aggregate-only)
# ---------------------------------------------------------------------------


def replay(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the action-agreement replay over a list of p25-policy-record-like
    records and return the aggregate-only report payload."""
    denominator = len(records)
    missing_feature_counts: dict[str, int] = {f: 0 for f in REQUIRED_SHADOW_FEATURES}
    records_with_any_missing = 0
    complete_feature_count = 0

    target_dist: dict[str, int] = {a: 0 for a in TARGET_ACTIONS}
    shadow_dist: dict[str, int] = {a: 0 for a in SHADOW_ACTIONS}

    # confusion_matrix[target_action][shadow_action]
    confusion: dict[str, dict[str, int]] = {
        t: {s: 0 for s in SHADOW_ACTIONS} for t in TARGET_ACTIONS
    }

    agreed = 0
    complete_records_for_agreement = 0
    per_target_total: dict[str, int] = {t: 0 for t in TARGET_ACTIONS}
    per_target_agreed: dict[str, int] = {t: 0 for t in TARGET_ACTIONS}

    # Label-driven ambiguous subsets (complete records where target==weak_only).
    # Split by query_noise value: qn0 is the non-tautological subset (shadow
    # cannot trivially agree via shared query_noise), qn1 is the shared-feature
    # subset (agreement expected to be very high but partly tautological).
    label_driven_qn0_denom = 0
    label_driven_qn0_shadow_weak = 0
    label_driven_qn1_denom = 0
    label_driven_qn1_shadow_weak = 0

    # Outcome-equivalence audit partitions (audit-only; outcomes computed AFTER
    # actions are chosen, never feeding back into routing).
    outcome_partitions: dict[str, list[dict[str, Any]]] = {
        "target_weak_shadow_use_p25": [],
        "target_use_p25_shadow_weak": [],
        "agreement_weak_only": [],
        "agreement_use_p25": [],
    }

    for rec in records:
        t_act = target_action(rec)
        s_act, present_map = shadow_action(rec)

        target_dist[t_act] += 1

        any_missing = not all(present_map.values())
        for feat, present in present_map.items():
            if not present:
                missing_feature_counts[feat] += 1
        if any_missing:
            records_with_any_missing += 1
            shadow_dist["missing"] += 1
            confusion[t_act]["missing"] += 1
            continue

        complete_feature_count += 1
        complete_records_for_agreement += 1
        assert s_act is not None  # for type checkers; guaranteed by completeness
        shadow_dist[s_act] += 1
        confusion[t_act][s_act] += 1
        per_target_total[t_act] += 1
        if s_act == t_act:
            agreed += 1
            per_target_agreed[t_act] += 1

        # Label-driven subsets: target==weak_only split by query_noise value.
        if t_act == "weak_only":
            qn_val = _route_feature(rec, "query_noise")
            try:
                qn_fire = bool(float(qn_val) > 0)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                qn_fire = False
            if qn_fire:
                label_driven_qn1_denom += 1
                if s_act == "weak_only":
                    label_driven_qn1_shadow_weak += 1
            else:
                label_driven_qn0_denom += 1
                if s_act == "weak_only":
                    label_driven_qn0_shadow_weak += 1

        # Outcome audit partition assignment (audit-only). Outcomes are computed AFTER
        # actions are chosen — scoring outputs, NEVER routing inputs.
        # Resolution: top-level outcome_metrics (synthetic) OR P21 per-strategy
        # dict keyed by the chosen target_action (weak_candidate_only /
        # candidate_baseline). Built in memory; the record is never mutated.
        om = _extract_outcome_metrics(rec, t_act)
        if om is not None and _outcome_metrics_usable(om):
            if t_act == "weak_only" and s_act == "use_p25_action":
                outcome_partitions["target_weak_shadow_use_p25"].append(om)  # type: ignore[arg-type]
            elif t_act == "use_p25_action" and s_act == "weak_only":
                outcome_partitions["target_use_p25_shadow_weak"].append(om)  # type: ignore[arg-type]
            elif t_act == "weak_only" and s_act == "weak_only":
                outcome_partitions["agreement_weak_only"].append(om)  # type: ignore[arg-type]
            elif t_act == "use_p25_action" and s_act == "use_p25_action":
                outcome_partitions["agreement_use_p25"].append(om)  # type: ignore[arg-type]

    complete_feature_rate = (
        complete_feature_count / denominator if denominator else 0.0
    )
    missing_feature_rates = {
        f: (missing_feature_counts[f] / denominator if denominator else 0.0)
        for f in REQUIRED_SHADOW_FEATURES
    }
    records_with_any_missing_rate = (
        records_with_any_missing / denominator if denominator else 0.0
    )
    agreement_overall_rate = (
        agreed / complete_records_for_agreement if complete_records_for_agreement else 0.0
    )
    agreement_per_target = {
        t: (
            per_target_agreed[t] / per_target_total[t]
            if per_target_total[t]
            else 0.0
        )
        for t in TARGET_ACTIONS
    }

    # Stratified agreement totals (complete records only).
    target_weak_only_total = per_target_total["weak_only"]
    target_use_p25_total = per_target_total["use_p25_action"]
    shadow_weak_only_total = shadow_dist["weak_only"]
    shadow_use_p25_total = shadow_dist["use_p25_action"]

    cm = confusion  # alias for readability
    target_weak_only_recall = (
        cm["weak_only"]["weak_only"] / target_weak_only_total
        if target_weak_only_total > 0
        else 0.0
    )
    target_use_p25_specificity = (
        cm["use_p25_action"]["use_p25_action"] / target_use_p25_total
        if target_use_p25_total > 0
        else 0.0
    )
    shadow_weak_only_precision = (
        cm["weak_only"]["weak_only"] / shadow_weak_only_total
        if shadow_weak_only_total > 0
        else 0.0
    )

    label_driven_ambiguous_recall_qn0 = (
        label_driven_qn0_shadow_weak / label_driven_qn0_denom
        if label_driven_qn0_denom > 0
        else 0.0
    )
    label_driven_ambiguous_denominator_qn0 = label_driven_qn0_denom
    query_noise_only_recall_qn1 = (
        label_driven_qn1_shadow_weak / label_driven_qn1_denom
        if label_driven_qn1_denom > 0
        else 0.0
    )

    # Cohen's kappa for the binary is_weak_only classification, complete records
    # only. Implemented directly (no numpy/sklearn dependency).
    if complete_records_for_agreement > 0:
        target_weak_rate = target_weak_only_total / complete_records_for_agreement
        shadow_weak_rate = shadow_weak_only_total / complete_records_for_agreement
    else:
        target_weak_rate = 0.0
        shadow_weak_rate = 0.0
    p_o = agreement_overall_rate
    p_e = (target_weak_rate * shadow_weak_rate) + (
        (1.0 - target_weak_rate) * (1.0 - shadow_weak_rate)
    )
    if (1.0 - p_e) > 0.0:
        cohens_kappa = (p_o - p_e) / (1.0 - p_e)
    else:
        cohens_kappa = 0.0
    # Guard against non-finite values (shouldn't happen with finite inputs,
    # but the verdict gate compares against a threshold so it must be finite).
    if not math.isfinite(cohens_kappa):
        cohens_kappa = 0.0

    # Silent-failure checks.
    all_shadow_ambiguous = (
        shadow_dist["weak_only"] == complete_records_for_agreement
        and complete_records_for_agreement > 0
    )
    all_shadow_non_ambiguous = (
        shadow_dist["use_p25_action"] == complete_records_for_agreement
        and complete_records_for_agreement > 0
    )
    base_rate_only_suspected = (
        cohens_kappa <= 0.05 and agreement_overall_rate > 0.5
    )
    no_silent_failure = not (
        all_shadow_ambiguous or all_shadow_non_ambiguous or base_rate_only_suspected
    )
    silent_failure_checks = {
        "all_shadow_ambiguous": all_shadow_ambiguous,
        "all_shadow_non_ambiguous": all_shadow_non_ambiguous,
        "base_rate_only_suspected": base_rate_only_suspected,
        "no_silent_failure": no_silent_failure,
    }

    # Outcome-equivalence audit (audit-only). Outcomes are computed AFTER
    # actions are chosen — scoring outputs, NEVER routing inputs.
    outcome_audit: dict[str, Any] = {}
    total_outcome_collected = 0
    for name, oms in outcome_partitions.items():
        if oms:
            outcome_audit[name] = _outcome_partition_summary(oms)
            total_outcome_collected += len(oms)
    if total_outcome_collected == 0:
        outcome_audit["outcome_audit_status"] = "no_outcome_data"
    else:
        outcome_audit["outcome_audit_status"] = "ok"
        outcome_audit["total_outcome_records"] = total_outcome_collected

    # Status: insufficient_runtime_features if every record is missing some
    # required feature (i.e. no complete record on which to evaluate the
    # shadow action).
    if complete_records_for_agreement == 0:
        status = "insufficient_runtime_features"
    else:
        status = "ok"

    feature_provenance = _feature_provenance()

    return {
        "denominator": denominator,
        "complete_feature_count": complete_feature_count,
        "complete_feature_rate": complete_feature_rate,
        "missing_feature_counts": missing_feature_counts,
        "missing_feature_rates": missing_feature_rates,
        "records_with_any_missing_feature_count": records_with_any_missing,
        "records_with_any_missing_feature_rate": records_with_any_missing_rate,
        "target_action_distribution": target_dist,
        "shadow_action_distribution": shadow_dist,
        "confusion_matrix_target_x_shadow": confusion,
        "agreement_denominator": complete_records_for_agreement,
        "agreement_overall_rate": agreement_overall_rate,
        "agreement_per_target_action": agreement_per_target,
        "target_weak_only_total": target_weak_only_total,
        "target_use_p25_total": target_use_p25_total,
        "shadow_weak_only_total": shadow_weak_only_total,
        "shadow_use_p25_total": shadow_use_p25_total,
        "target_weak_only_recall": target_weak_only_recall,
        "target_use_p25_specificity": target_use_p25_specificity,
        "shadow_weak_only_precision": shadow_weak_only_precision,
        "label_driven_ambiguous_recall_qn0": label_driven_ambiguous_recall_qn0,
        "label_driven_ambiguous_denominator_qn0": label_driven_ambiguous_denominator_qn0,
        "query_noise_only_recall_qn1": query_noise_only_recall_qn1,
        "cohens_kappa": cohens_kappa,
        "silent_failure_checks": silent_failure_checks,
        "outcome_audit": outcome_audit,
        "feature_provenance": feature_provenance,
        "status": status,
    }


def _feature_provenance() -> list[dict[str, Any]]:
    """Aggregate-only feature provenance list. No raw paths/digests/providers."""
    return [
        {
            "feature": "route_features.query_noise",
            "dependency_class": "deterministic_runtime",
            "read_by_target_action": True,
            "read_by_shadow_action": True,
            "required_by_shadow_action": True,
        },
        {
            "feature": "route_features.candidate_support_exists",
            "dependency_class": "deterministic_runtime",
            "read_by_target_action": False,
            "read_by_shadow_action": True,
            "required_by_shadow_action": True,
        },
        {
            "feature": "route_features.local_anchor",
            "dependency_class": "deterministic_runtime",
            "read_by_target_action": False,
            "read_by_shadow_action": True,
            "required_by_shadow_action": True,
        },
        {
            "feature": "route_features.rrf_backed_by_anchor",
            "dependency_class": "deterministic_runtime",
            "read_by_target_action": False,
            "read_by_shadow_action": True,
            "required_by_shadow_action": True,
        },
        {
            "feature": "task_bucket",
            "dependency_class": "benchmark_public",
            "read_by_target_action": True,
            "read_by_shadow_action": False,
            "required_by_shadow_action": False,
        },
        {
            "feature": "task_risk_tags",
            "dependency_class": "benchmark_public",
            "read_by_target_action": True,
            "read_by_shadow_action": False,
            "required_by_shadow_action": False,
        },
    ]


# ---------------------------------------------------------------------------
# Algorithm spec + report assembly
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Build the frozen B10B runtime-shadow algorithm spec dict.

    Deterministic; generated_at is fixed so the spec hash is stable.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "spec_kind": "runtime_shadow_algorithm_spec",
        "claim_level": "ambiguous_branch_runtime_shadow_only",
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "full_runtime_clean_policy": False,
        "ambiguous_branch_runtime_shadow_only": True,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "b10_frozen_spec_id": B10_FROZEN_SPEC_ID,
        "b10_frozen_spec_hash_matched": True,
        "description": (
            "B10B runtime-shadow replay: fixed predeclared runtime-feature-only "
            "shadow predicate for the ambiguous branch of the frozen B10 spec "
            "balanced_policy_v1_benchmark_routed. Reads only runtime route_features "
            "(query_noise, candidate_support_exists, local_anchor, "
            "rrf_backed_by_anchor); never reads task_bucket, task_risk_tags, "
            "has_gold, score_group, or outcome metrics. Ambiguous-branch "
            "runtime-shadow only; default use_p25_action still delegates to P25. "
            "Does NOT prove a runtime-clean balanced policy."
        ),
        "target_action": {
            "source_spec": B10_FROZEN_SPEC_ID,
            "definition": (
                "if ambiguous_or_query_noise (benchmark public labels OR "
                "route_features.query_noise) then weak_only else use_p25_action"
            ),
            "reads": [
                "task_bucket",
                "task_risk_tags",
                "route_features.query_noise",
            ],
            "benchmark_public_dependencies": list(TARGET_BENCHMARK_LABELS),
            "deterministic_runtime_dependencies": ["route_features.query_noise"],
        },
        "shadow_action": {
            "definition": (
                "if runtime_shadow_ambiguous then weak_only else use_p25_action"
            ),
            "runtime_shadow_ambiguous_definition": (
                "query_noise OR (candidate_support_exists AND anchor_disagreement_proxy)"
            ),
            "anchor_disagreement_proxy_definition": (
                "local_anchor AND NOT rrf_backed_by_anchor"
            ),
            "reads": [f"route_features.{f}" for f in SHADOW_RUNTIME_FEATURES],
            "required_runtime_features": list(REQUIRED_SHADOW_FEATURES),
            "missing_feature_policy": (
                "if any required runtime feature is missing the record is marked "
                "missing and the shadow action is NOT silently defaulted to false"
            ),
            "forbidden_shadow_inputs": [
                "task_bucket",
                "task_risk_tags",
                "has_gold",
                "score_group",
                "outcome_metrics",
            ],
            "reads_benchmark_public_labels": False,
            "reads_score_private_fields": False,
        },
        "shadow_runtime_features": list(SHADOW_RUNTIME_FEATURES),
        "required_shadow_features": list(REQUIRED_SHADOW_FEATURES),
        "forbidden_shadow_inputs": [
            "task_bucket",
            "task_risk_tags",
            "has_gold",
            "score_group",
            "outcome_metrics",
        ],
        "predeclared_acceptance_gates": dict(PREDECLARED_ACCEPTANCE_GATES),
        "aggregate_only_public_artifact": True,
        "excluded_adapter_layer": {
            "model_adapter_excluded": True,
            "output_mode_excluded": True,
            "provider_credentials_excluded": True,
            "provider_endpoints_excluded": True,
            "provider_secrets_excluded": True,
        },
    }


def _evaluate_verdict(
    aggregate: dict[str, Any], replay_source: str
) -> tuple[bool, str, str | None]:
    """Compute (supported, support_claim, support_claim_reason).

    support_claim_reason is None when the verdict is True (no failure reason).

    The label-driven denominator floor is a HARD gate: if the qn0 denominator
    is below ``LABEL_DRIVEN_QN0_MIN_DENOMINATOR`` the recall metric is too thin
    to trust, so the verdict is False with reason
    ``insufficient_label_driven_denominator`` — empirical replay support remains
    pending rather than being asserted under an escape clause.
    """
    if replay_source == "synthetic_fixture":
        return False, "mechanics_only_synthetic_fixture", "synthetic_fixture_only"

    # ci_ephemeral_records path.
    complete_feature_rate = aggregate["complete_feature_rate"]
    agreement_overall = aggregate["agreement_overall_rate"]
    target_weak_recall = aggregate["target_weak_only_recall"]
    target_use_p25_spec = aggregate["target_use_p25_specificity"]
    shadow_precision = aggregate["shadow_weak_only_precision"]
    kappa = aggregate["cohens_kappa"]
    label_recall_qn0 = aggregate["label_driven_ambiguous_recall_qn0"]
    label_denom_qn0 = aggregate["label_driven_ambiguous_denominator_qn0"]
    no_silent_failure = aggregate["silent_failure_checks"]["no_silent_failure"]

    agreement_gates_ok = (
        complete_feature_rate >= PREDECLARED_ACCEPTANCE_GATES["complete_feature_rate_min"]
        and agreement_overall
        >= PREDECLARED_ACCEPTANCE_GATES["overall_action_exact_agreement_min"]
        and target_weak_recall
        >= PREDECLARED_ACCEPTANCE_GATES["target_weak_only_recall_min"]
        and target_use_p25_spec
        >= PREDECLARED_ACCEPTANCE_GATES["target_use_p25_specificity_min"]
        and shadow_precision
        >= PREDECLARED_ACCEPTANCE_GATES["shadow_weak_only_precision_min"]
        and kappa >= PREDECLARED_ACCEPTANCE_GATES["cohens_kappa_min"]
    )
    # The label-driven gate is a HARD AND: the qn0 subset must BOTH clear the
    # recall threshold AND have a sufficient denominator. A small denominator
    # makes the recall metric unreliable, so the verdict cannot pass on a thin
    # qn0 subset — empirical replay support stays pending in that case.
    label_gate_ok = (
        label_recall_qn0
        >= PREDECLARED_ACCEPTANCE_GATES["label_driven_ambiguous_recall_qn0_min"]
        and label_denom_qn0
        >= PREDECLARED_ACCEPTANCE_GATES["label_driven_ambiguous_min_denominator"]
    )
    silent_ok = no_silent_failure
    leakage_ok = bool(
        PREDECLARED_ACCEPTANCE_GATES["outcome_metrics_leakage_tested"]
    )

    verdict = agreement_gates_ok and label_gate_ok and silent_ok and leakage_ok

    if verdict:
        return True, "empirical_replay_support", None

    # Verdict is False: pick the most informative failure reason. Priority
    # order (highest first):
    #   1. synthetic_fixture_only       (handled above; only ci_ephemeral here)
    #   2. silent_failure_detected       (silent-failure audit caught a problem)
    #   3. insufficient_label_driven_denominator (qn0 subset too thin)
    #   4. insufficient_agreement       (agreement gates failed)
    #   5. leakage_guard_incomplete     (unreachable fallback)
    if not silent_ok:
        reason = "silent_failure_detected"
    elif label_denom_qn0 < PREDECLARED_ACCEPTANCE_GATES[
        "label_driven_ambiguous_min_denominator"
    ]:
        reason = "insufficient_label_driven_denominator"
    elif not agreement_gates_ok:
        reason = "insufficient_agreement"
    else:
        # Should never happen if the leakage guard patch is in place.
        reason = "leakage_guard_incomplete"
    return False, "empirical_replay_support_pending", reason


def build_report(
    records: list[dict[str, Any]],
    *,
    self_test: bool,
    replay_source: str = "synthetic_fixture",
) -> dict[str, Any]:
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")
    spec = build_algorithm_spec()
    # The spec hash is verified for stability by the self-test (re-load +
    # re-hash of the on-disk spec). It is NOT emitted as a literal value in
    # the public artifact, mirroring B10's `frozen_spec_hash_matched` style.
    aggregate = replay(records)

    supported, support_claim, support_claim_reason = _evaluate_verdict(
        aggregate, replay_source
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": "ambiguous_branch_runtime_shadow_only",
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "aggregate_only_public_artifact": True,
        "self_test": bool(self_test),
        "status": aggregate["status"],
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "b10_frozen_spec_id": B10_FROZEN_SPEC_ID,
        "b10_frozen_spec_hash_matched": True,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "full_runtime_clean_policy": False,
        "ambiguous_branch_runtime_shadow_only": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "gold_spans_in_artifact": False,
        "task_ids_in_artifact": False,
        "candidate_ids_in_artifact": False,
        "repo_ids_in_artifact": False,
        "private_labels_committed": False,
        "replay_source": replay_source,
        "predeclared_gates": dict(PREDECLARED_ACCEPTANCE_GATES),
        "runtime_shadow_ambiguous_supported": bool(supported),
        "support_claim": support_claim,
        "replay": aggregate,
    }
    if support_claim_reason is not None:
        report["support_claim_reason"] = support_claim_reason
    return report


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def verify_algorithm_spec(spec: dict[str, Any], expected_hash: str) -> None:
    if spec.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise ValueError("algorithm spec schema_version mismatch")
    if spec.get("generated_by") != GENERATED_BY:
        raise ValueError("algorithm spec generated_by mismatch")
    if spec.get("algorithm_spec_id") != ALGORITHM_SPEC_ID:
        raise ValueError("algorithm spec algorithm_spec_id mismatch")
    if spec.get("claim_level") != "ambiguous_branch_runtime_shadow_only":
        raise ValueError("algorithm spec claim_level mismatch")
    if spec.get("promotion_ready") is not False:
        raise ValueError("algorithm spec promotion_ready must be false")
    if spec.get("default_should_change") is not False:
        raise ValueError("algorithm spec default_should_change must be false")
    if spec.get("evidencecore_semantics_changed") is not False:
        raise ValueError("algorithm spec evidencecore_semantics_changed must be false")
    if spec.get("full_runtime_clean_policy") is not False:
        raise ValueError("algorithm spec full_runtime_clean_policy must be false")
    if spec.get("ambiguous_branch_runtime_shadow_only") is not True:
        raise ValueError(
            "algorithm spec ambiguous_branch_runtime_shadow_only must be true"
        )
    if spec.get("policy_search_performed") is not False:
        raise ValueError("algorithm spec policy_search_performed must be false")
    if spec.get("quality_strategy_tuned") is not False:
        raise ValueError("algorithm spec quality_strategy_tuned must be false")
    if spec.get("b10_frozen_spec_id") != B10_FROZEN_SPEC_ID:
        raise ValueError("algorithm spec b10_frozen_spec_id mismatch")
    if spec.get("b10_frozen_spec_hash_matched") is not True:
        raise ValueError("algorithm spec b10_frozen_spec_hash_matched must be true")
    shadow = spec.get("shadow_action") or {}
    if shadow.get("reads_benchmark_public_labels") is not False:
        raise ValueError("shadow_action must not read benchmark public labels")
    if shadow.get("reads_score_private_fields") is not False:
        raise ValueError("shadow_action must not read score private fields")
    forbidden_inputs = set(shadow.get("forbidden_shadow_inputs") or [])
    for required in (
        "task_bucket",
        "task_risk_tags",
        "has_gold",
        "score_group",
        "outcome_metrics",
    ):
        if required not in forbidden_inputs:
            raise ValueError(
                f"shadow_action must list {required} in forbidden_shadow_inputs"
            )
    gates = spec.get("predeclared_acceptance_gates")
    if not isinstance(gates, dict):
        raise ValueError("algorithm spec missing predeclared_acceptance_gates dict")
    for required_key, required_val in PREDECLARED_ACCEPTANCE_GATES.items():
        if required_key not in gates:
            raise ValueError(
                f"predeclared_acceptance_gates missing key: {required_key}"
            )
        if gates[required_key] != required_val:
            raise ValueError(
                f"predeclared_acceptance_gates[{required_key}] mismatch: "
                f"expected {required_val!r}, got {gates[required_key]!r}"
            )
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
    if report.get("algorithm_spec_id") != ALGORITHM_SPEC_ID:
        raise ValueError("report algorithm_spec_id mismatch")
    if report.get("claim_level") != "ambiguous_branch_runtime_shadow_only":
        raise ValueError("report claim_level mismatch")
    if report.get("b10_frozen_spec_id") != B10_FROZEN_SPEC_ID:
        raise ValueError("report b10_frozen_spec_id mismatch")
    if report.get("b10_frozen_spec_hash_matched") is not True:
        raise ValueError("report b10_frozen_spec_hash_matched must be true")
    if report.get("algorithm_spec_sha256_matched") is not True:
        raise ValueError("report algorithm_spec_sha256_matched must be true")
    if report.get("algorithm_spec_sha256_stable") is not True:
        raise ValueError("report algorithm_spec_sha256_stable must be true")
    if report.get("full_runtime_clean_policy") is not False:
        raise ValueError("report full_runtime_clean_policy must be false")
    if report.get("ambiguous_branch_runtime_shadow_only") is not True:
        raise ValueError("report ambiguous_branch_runtime_shadow_only must be true")
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
    if report.get("status") not in {"ok", "insufficient_runtime_features"}:
        raise ValueError(f"report unexpected status: {report.get('status')!r}")
    # replay_source
    replay_source = report.get("replay_source")
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"report replay_source invalid: {replay_source!r}")
    # Verdict + support claim.
    supported = report.get("runtime_shadow_ambiguous_supported")
    if not isinstance(supported, bool):
        raise ValueError("runtime_shadow_ambiguous_supported must be a bool")
    support_claim = report.get("support_claim")
    if support_claim not in ALLOWED_SUPPORT_CLAIMS:
        raise ValueError(f"support_claim invalid: {support_claim!r}")
    if not supported and "support_claim_reason" not in report:
        raise ValueError("support_claim_reason required when verdict is False")
    if "support_claim_reason" in report:
        reason = report["support_claim_reason"]
        if reason not in ALLOWED_SUPPORT_CLAIM_REASONS:
            raise ValueError(f"support_claim_reason invalid: {reason!r}")
    # Predeclared gates.
    gates = report.get("predeclared_gates")
    if not isinstance(gates, dict):
        raise ValueError("report predeclared_gates must be a dict")
    for required_key, required_val in PREDECLARED_ACCEPTANCE_GATES.items():
        if required_key not in gates:
            raise ValueError(f"predeclared_gates missing key: {required_key}")
        if gates[required_key] != required_val:
            raise ValueError(
                f"predeclared_gates[{required_key}] mismatch: "
                f"expected {required_val!r}, got {gates[required_key]!r}"
            )
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")
    # Validate aggregate structure.
    replay_block = report.get("replay") or {}
    for key in (
        "denominator",
        "complete_feature_count",
        "complete_feature_rate",
        "missing_feature_counts",
        "missing_feature_rates",
        "records_with_any_missing_feature_count",
        "records_with_any_missing_feature_rate",
        "target_action_distribution",
        "shadow_action_distribution",
        "confusion_matrix_target_x_shadow",
        "agreement_denominator",
        "agreement_overall_rate",
        "agreement_per_target_action",
        "target_weak_only_total",
        "target_use_p25_total",
        "shadow_weak_only_total",
        "shadow_use_p25_total",
        "target_weak_only_recall",
        "target_use_p25_specificity",
        "shadow_weak_only_precision",
        "label_driven_ambiguous_recall_qn0",
        "label_driven_ambiguous_denominator_qn0",
        "query_noise_only_recall_qn1",
        "cohens_kappa",
        "silent_failure_checks",
        "outcome_audit",
        "feature_provenance",
        "status",
    ):
        if key not in replay_block:
            raise ValueError(f"report replay missing key: {key}")
    # cohens_kappa range.
    kappa = replay_block.get("cohens_kappa")
    if not isinstance(kappa, (int, float)) or isinstance(kappa, bool):
        raise ValueError("cohens_kappa must be a number")
    if not (-1.0 <= float(kappa) <= 1.0):
        raise ValueError(f"cohens_kappa out of [-1.0, 1.0]: {kappa!r}")
    # silent_failure_checks structure.
    sfc = replay_block.get("silent_failure_checks")
    if not isinstance(sfc, dict):
        raise ValueError("silent_failure_checks must be a dict")
    for required_key in (
        "all_shadow_ambiguous",
        "all_shadow_non_ambiguous",
        "base_rate_only_suspected",
        "no_silent_failure",
    ):
        if required_key not in sfc:
            raise ValueError(f"silent_failure_checks missing key: {required_key}")
        if not isinstance(sfc[required_key], bool):
            raise ValueError(
                f"silent_failure_checks[{required_key}] must be a bool"
            )
    # outcome_audit structure (loose: must be a dict).
    oa = replay_block.get("outcome_audit")
    if not isinstance(oa, dict):
        raise ValueError("outcome_audit must be a dict")


# ---------------------------------------------------------------------------
# Self-test: synthesize p25-policy-record-like records in memory
# ---------------------------------------------------------------------------


def _make_record(
    *,
    task_bucket: str = "plain",
    task_risk_tags: list[str] | None = None,
    has_gold: bool = False,
    score_group: str = "no_gold",
    query_noise: float | None = 0.0,
    candidate_support_exists: bool | None = True,
    local_anchor: bool | None = False,
    rrf_backed_by_anchor: bool | None = True,
    outcome_metrics: dict[str, Any] | None = None,
    p21_strategies: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a synthetic p25-policy-record-like record for self-tests.

    ``outcome_metrics`` carries the synthetic-fixture top-level outcome dict
    (used by the legacy outcome_audit path). ``p21_strategies`` carries P21
    ephemeral per-strategy outcome dicts (``weak_candidate_only``,
    ``candidate_baseline``, etc.) — when present AND ``outcome_metrics`` is
    None, the outcome_audit will extract audit fields from the strategy dict
    matching the chosen target_action. At most one of ``outcome_metrics`` and
    ``p21_strategies`` should be populated.
    """
    if task_risk_tags is None:
        task_risk_tags = []
    route_features: dict[str, Any] = {}
    if query_noise is not None:
        route_features["query_noise"] = query_noise
    if candidate_support_exists is not None:
        route_features["candidate_support_exists"] = candidate_support_exists
    if local_anchor is not None:
        route_features["local_anchor"] = local_anchor
    if rrf_backed_by_anchor is not None:
        route_features["rrf_backed_by_anchor"] = rrf_backed_by_anchor
    rec: dict[str, Any] = {
        "task_id": f"t-{id(task_bucket)}-{id(tuple(task_risk_tags))}",
        "repo_id": "synthetic",
        "task_bucket": task_bucket,
        "task_risk_tags": list(task_risk_tags),
        "has_gold": has_gold,
        "score_group": score_group,
        "route_features": route_features,
    }
    if outcome_metrics is not None:
        rec["outcome_metrics"] = outcome_metrics
    elif p21_strategies is not None:
        # P21 ephemeral format: per-strategy outcome dicts, no top-level
        # outcome_metrics field. The outcome_audit extracts audit fields from
        # the strategy dict matching the chosen target_action.
        for strategy_name, strategy_payload in p21_strategies.items():
            rec[strategy_name] = strategy_payload
    else:
        rec["outcome_metrics"] = {
            "added_gold_span": 999,
            "added_false_span": 999,
            "span_f0_5": 0.0,
            "primary_false_positive_rate": 1.0,
        }
    return rec


def _self_test_perfect_agreement() -> None:
    # query_noise fires => both target and shadow weak_only
    rec = _make_record(
        task_bucket="ambiguous",
        task_risk_tags=[],
        query_noise=1.0,
        candidate_support_exists=True,
        local_anchor=False,
        rrf_backed_by_anchor=True,
    )
    assert target_action(rec) == "weak_only", target_action(rec)
    s_act, present = shadow_action(rec)
    assert all(present.values()), present
    assert s_act == "weak_only", s_act

    # No noise, no ambiguous labels, no anchor disagreement => both use_p25
    rec2 = _make_record(
        task_bucket="plain",
        task_risk_tags=[],
        query_noise=0.0,
        candidate_support_exists=True,
        local_anchor=False,
        rrf_backed_by_anchor=True,
    )
    assert target_action(rec2) == "use_p25_action"
    s_act2, present2 = shadow_action(rec2)
    assert all(present2.values()), present2
    assert s_act2 == "use_p25_action", s_act2


def _self_test_disagreement() -> None:
    # Target weak_only (ambiguous label), shadow use_p25_action
    # (query_noise=0, candidate_support_exists=True, local_anchor=False =>
    #  anchor_disagreement_proxy=False => shadow use_p25)
    rec = _make_record(
        task_bucket="ambiguous",
        task_risk_tags=[],
        query_noise=0.0,
        candidate_support_exists=True,
        local_anchor=False,
        rrf_backed_by_anchor=True,
    )
    assert target_action(rec) == "weak_only"
    s_act, present = shadow_action(rec)
    assert all(present.values())
    assert s_act == "use_p25_action", s_act
    assert s_act != target_action(rec)

    # Target use_p25 (no labels, no noise), shadow weak_only (anchor
    # disagreement proxy fires: local_anchor=True, rrf_backed_by_anchor=False)
    rec2 = _make_record(
        task_bucket="plain",
        task_risk_tags=[],
        query_noise=0.0,
        candidate_support_exists=True,
        local_anchor=True,
        rrf_backed_by_anchor=False,
    )
    assert target_action(rec2) == "use_p25_action"
    s_act2, present2 = shadow_action(rec2)
    assert all(present2.values())
    assert s_act2 == "weak_only", s_act2
    assert s_act2 != target_action(rec2)


def _self_test_missing_feature() -> None:
    # local_anchor missing => record marked missing, shadow not computed
    rec = _make_record(
        task_bucket="ambiguous",
        task_risk_tags=[],
        query_noise=0.0,
        candidate_support_exists=True,
        local_anchor=None,  # missing
        rrf_backed_by_anchor=True,
    )
    s_act, present = shadow_action(rec)
    assert s_act is None, s_act
    assert present["local_anchor"] is False
    assert not all(present.values())

    # query_noise missing => record marked missing (no silent default to false)
    rec2 = _make_record(
        task_bucket="plain",
        task_risk_tags=[],
        query_noise=None,  # missing
        candidate_support_exists=True,
        local_anchor=False,
        rrf_backed_by_anchor=True,
    )
    s_act2, present2 = shadow_action(rec2)
    assert s_act2 is None, s_act2
    assert present2["query_noise"] is False

    # All records missing => status insufficient_runtime_features
    report = build_report([rec, rec2], self_test=True)
    assert report["status"] == "insufficient_runtime_features", report["status"]
    verify_report(report)


def _self_test_leakage_guard() -> None:
    """Mutating task_bucket/task_risk_tags/has_gold/score_group/outcome_metrics
    must NOT change the shadow action. Mutating benchmark-public labels MUST
    change the target action when relevant; mutating outcome_metrics must NOT
    change either shadow or target (outcomes are scoring outputs, never routing
    inputs)."""
    base = _make_record(
        task_bucket="plain",
        task_risk_tags=[],
        has_gold=False,
        score_group="no_gold",
        query_noise=0.0,
        candidate_support_exists=True,
        local_anchor=True,
        rrf_backed_by_anchor=False,
    )
    base_shadow, base_present = shadow_action(base)
    base_target = target_action(base)
    assert all(base_present.values())
    assert base_shadow == "weak_only", base_shadow
    assert base_target == "use_p25_action", base_target

    # Mutate the forbidden inputs to the shadow predicate, INCLUDING
    # outcome_metrics (the leakage-guard gap from the prior review).
    mutated = json.loads(json.dumps(base))
    mutated["task_bucket"] = "ambiguous"
    mutated["task_risk_tags"] = ["hallucination_risk", "weak_candidates"]
    mutated["has_gold"] = not base["has_gold"]
    mutated["score_group"] = "positive" if base["score_group"] != "positive" else "no_gold"
    mutated["outcome_metrics"] = {
        "added_gold_span": 12345,
        "added_false_span": 67890,
        "span_f0_5": 0.99,
        "primary_false_positive_rate": 0.01,
    }

    m_shadow, m_present = shadow_action(mutated)
    m_target = target_action(mutated)

    # Shadow action MUST be invariant to these mutations (including
    # outcome_metrics).
    assert m_shadow == base_shadow, (m_shadow, base_shadow)
    assert m_present == base_present
    # Target action MUST change (we flipped ambiguous labels).
    assert m_target != base_target, (m_target, base_target)
    assert m_target == "weak_only", m_target

    # Sub-test: mutate ONLY outcome_metrics (everything else at base values).
    # Both shadow and target MUST be invariant — outcomes are scoring outputs,
    # never routing inputs, and neither the shadow nor the target predicate
    # reads outcome_metrics.
    only_outcome = json.loads(json.dumps(base))
    only_outcome["outcome_metrics"] = {
        "added_gold_span": 12345,
        "added_false_span": 67890,
        "span_f0_5": 0.99,
        "primary_false_positive_rate": 0.01,
    }
    oo_shadow, _ = shadow_action(only_outcome)
    oo_target = target_action(only_outcome)
    assert oo_shadow == base_shadow, (oo_shadow, base_shadow)
    assert oo_target == base_target, (oo_target, base_target)

    # Reverse mutation of bucket/tags back to non-ambiguous, keep has_gold
    # flipped and score_group flipped. Target should still change relative to
    # the all-flipped case but shadow must remain invariant.
    only_score = json.loads(json.dumps(base))
    only_score["has_gold"] = not base["has_gold"]
    only_score["score_group"] = "positive"
    os_shadow, _ = shadow_action(only_score)
    os_target = target_action(only_score)
    assert os_shadow == base_shadow
    # Target should not depend on has_gold/score_group either.
    assert os_target == base_target, (os_target, base_target)


def _self_test_replay_aggregate() -> None:
    records = [
        # 0: agreement weak_only (target weak via label AND qn=1)
        _make_record(
            task_bucket="ambiguous",
            query_noise=1.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        # 1: agreement use_p25
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        # 2: disagreement (target weak_only via label, shadow use_p25)
        _make_record(
            task_bucket="ambiguous",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        # 3: disagreement (target use_p25, shadow weak_only via anchor proxy)
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=True,
            rrf_backed_by_anchor=False,
        ),
        # 4: missing feature (local_anchor absent)
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=None,
            rrf_backed_by_anchor=True,
        ),
    ]
    report = build_report(records, self_test=True)
    rep = report["replay"]
    assert rep["denominator"] == 5
    assert rep["complete_feature_count"] == 4, rep["complete_feature_count"]
    assert rep["records_with_any_missing_feature_count"] == 1
    assert rep["missing_feature_counts"]["local_anchor"] == 1
    assert rep["target_action_distribution"] == {
        "weak_only": 2,
        "use_p25_action": 3,
    }, rep["target_action_distribution"]
    assert rep["shadow_action_distribution"] == {
        "weak_only": 2,
        "use_p25_action": 2,
        "missing": 1,
    }, rep["shadow_action_distribution"]
    cm = rep["confusion_matrix_target_x_shadow"]
    # target weak_only: rec0 weak_only (agree), rec2 use_p25 (disagree)
    assert cm["weak_only"]["weak_only"] == 1, cm
    assert cm["weak_only"]["use_p25_action"] == 1, cm
    # target use_p25: rec1 use_p25 (agree), rec3 weak_only (disagree), rec4 missing
    assert cm["use_p25_action"]["use_p25_action"] == 1, cm
    assert cm["use_p25_action"]["weak_only"] == 1, cm
    assert cm["use_p25_action"]["missing"] == 1, cm
    # agreement_overall: 2 agreed out of 4 complete records
    assert rep["agreement_denominator"] == 4
    assert rep["agreement_overall_rate"] == 0.5, rep["agreement_overall_rate"]

    # Stratified agreement metrics.
    assert rep["target_weak_only_total"] == 2, rep["target_weak_only_total"]
    assert rep["target_use_p25_total"] == 2, rep["target_use_p25_total"]
    assert rep["shadow_weak_only_total"] == 2, rep["shadow_weak_only_total"]
    assert rep["shadow_use_p25_total"] == 2, rep["shadow_use_p25_total"]
    # target_weak_only_recall = cm[weak][weak]/target_weak_total = 1/2
    assert rep["target_weak_only_recall"] == 0.5, rep["target_weak_only_recall"]
    assert rep["target_use_p25_specificity"] == 0.5, rep["target_use_p25_specificity"]
    assert rep["shadow_weak_only_precision"] == 0.5, rep["shadow_weak_only_precision"]

    # Label-driven subsets. qn0 subset: only rec2 (target weak, qn=0). Shadow
    # said use_p25, so recall_qn0 = 0/1 = 0.0, denom = 1.
    assert rep["label_driven_ambiguous_denominator_qn0"] == 1, (
        rep["label_driven_ambiguous_denominator_qn0"]
    )
    assert rep["label_driven_ambiguous_recall_qn0"] == 0.0, (
        rep["label_driven_ambiguous_recall_qn0"]
    )
    # qn1 subset: only rec0 (target weak, qn=1). Shadow said weak_only, so
    # recall_qn1 = 1/1 = 1.0.
    assert rep["query_noise_only_recall_qn1"] == 1.0, rep["query_noise_only_recall_qn1"]

    # Cohen's kappa: target_weak_rate = shadow_weak_rate = 2/4 = 0.5,
    # p_e = 0.25 + 0.25 = 0.5, p_o = 0.5 => kappa = 0.0.
    assert rep["cohens_kappa"] == 0.0, rep["cohens_kappa"]

    # Silent-failure checks: not all-weak, not all-use_p25; kappa==0 and
    # agreement==0.5 (NOT > 0.5) so base_rate_only_suspected is False.
    sfc = rep["silent_failure_checks"]
    assert sfc["all_shadow_ambiguous"] is False
    assert sfc["all_shadow_non_ambiguous"] is False
    assert sfc["base_rate_only_suspected"] is False
    assert sfc["no_silent_failure"] is True

    # Outcome audit: rec4 is missing so only 4 complete records, each with
    # default outcome_metrics. Each of the 4 partitions gets exactly 1 record.
    oa = rep["outcome_audit"]
    assert oa["outcome_audit_status"] == "ok", oa
    assert oa["total_outcome_records"] == 4, oa
    for part in (
        "target_weak_shadow_use_p25",
        "target_use_p25_shadow_weak",
        "agreement_weak_only",
        "agreement_use_p25",
    ):
        assert part in oa, (part, oa)
        assert oa[part]["count"] == 1, (part, oa[part])
        # Default outcome_metrics means added_gold_span=999, added_false_span=999,
        # span_f0_5=0.0, primary_false_positive_rate=1.0.
        assert oa[part]["mean_added_gold_span"] == 999, (part, oa[part])
        assert oa[part]["mean_added_false_span"] == 999, (part, oa[part])
        assert oa[part]["mean_span_f0_5"] == 0.0, (part, oa[part])
        assert oa[part]["mean_primary_false_positive_rate"] == 1.0, (part, oa[part])

    # Verdict fields on the report.
    assert report["replay_source"] == "synthetic_fixture"
    assert report["runtime_shadow_ambiguous_supported"] is False
    assert report["support_claim"] == "mechanics_only_synthetic_fixture"
    assert report["support_claim_reason"] == "synthetic_fixture_only"
    assert report["predeclared_gates"] == PREDECLARED_ACCEPTANCE_GATES

    verify_report(report)


def _self_test_verdict_synthetic_fixture_unsupported() -> None:
    """Synthetic fixture replay must never produce an empirical-support
    verdict, regardless of how clean the metrics look."""
    records = [
        _make_record(
            task_bucket="ambiguous",
            query_noise=1.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
    ]
    report = build_report(records, self_test=True, replay_source="synthetic_fixture")
    verify_report(report)
    assert report["replay_source"] == "synthetic_fixture"
    assert report["runtime_shadow_ambiguous_supported"] is False
    assert report["support_claim"] == "mechanics_only_synthetic_fixture"
    assert report["support_claim_reason"] == "synthetic_fixture_only"


def _self_test_verdict_insufficient_denominator_unsupported() -> None:
    """A CI-ephemeral replay whose label-driven qn0 denominator is below the
    floor must NOT yield an empirical-support verdict, and must surface the
    insufficient-label-driven-denominator reason rather than a mixed-signal
    support_claim.

    Constructs a record set where every other gate passes (perfect agreement,
    no silent failure) but the qn0 subset is too thin (denom < 10) — exactly
    the case the @oracle review flagged. The verdict must be False with
    support_claim=empirical_replay_support_pending and
    support_claim_reason=insufficient_label_driven_denominator.
    """
    records = [
        # 0: target weak_only (ambiguous label, qn=0), shadow weak_only via
        #    anchor disagreement proxy. Counts toward qn0 label-driven subset.
        _make_record(
            task_bucket="ambiguous",
            task_risk_tags=[],
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=True,
            rrf_backed_by_anchor=False,
        ),
        # 1: same as rec 0 — second label-driven qn0 record.
        _make_record(
            task_bucket="ambiguous",
            task_risk_tags=[],
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=True,
            rrf_backed_by_anchor=False,
        ),
        # 2: target use_p25 (no ambiguous labels, qn=0), shadow use_p25.
        #    Ensures shadow_dist is not all-weak_only (avoids
        #    all_shadow_ambiguous silent-failure trip) and provides the
        #    use_p25 confusion-mass needed for the agreement gates.
        _make_record(
            task_bucket="plain",
            task_risk_tags=[],
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
    ]
    report = build_report(
        records, self_test=True, replay_source="ci_ephemeral_records"
    )
    verify_report(report)

    rep = report["replay"]
    # Sanity-check the synthesized metric landscape: agreement gates should
    # pass (so the only thing failing the verdict is the denominator floor).
    assert rep["complete_feature_rate"] == 1.0, rep["complete_feature_rate"]
    assert rep["agreement_overall_rate"] == 1.0, rep["agreement_overall_rate"]
    assert rep["target_weak_only_recall"] == 1.0, rep["target_weak_only_recall"]
    assert rep["target_use_p25_specificity"] == 1.0, rep[
        "target_use_p25_specificity"
    ]
    assert rep["shadow_weak_only_precision"] == 1.0, rep[
        "shadow_weak_only_precision"
    ]
    assert rep["cohens_kappa"] == 1.0, rep["cohens_kappa"]
    sfc = rep["silent_failure_checks"]
    assert sfc["no_silent_failure"] is True, sfc
    # The qn0 subset is exactly the two ambiguous/qn0 records.
    assert rep["label_driven_ambiguous_denominator_qn0"] == 2, (
        rep["label_driven_ambiguous_denominator_qn0"]
    )
    assert rep["label_driven_ambiguous_recall_qn0"] == 1.0, (
        rep["label_driven_ambiguous_recall_qn0"]
    )

    # Verdict: hard denominator gate fires.
    assert report["replay_source"] == "ci_ephemeral_records"
    assert report["runtime_shadow_ambiguous_supported"] is False
    assert report["support_claim"] == "empirical_replay_support_pending"
    assert report["support_claim_reason"] == "insufficient_label_driven_denominator"
    assert report["predeclared_gates"] == PREDECLARED_ACCEPTANCE_GATES
    # The new gate is predeclared on the report.
    assert (
        report["predeclared_gates"]["label_driven_ambiguous_min_denominator"] == 10
    )


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
    clean = {"provenance": "b6_lite_interpretable_policy_search::_noisy_or_ambiguous"}
    hits3 = _recursive_key_scan(clean)
    assert hits3 == [], hits3


def _self_test_b10_reference() -> None:
    """Verify the B10 frozen spec exists and the B10B spec/refer report
    reference its id and hash-matched flag."""
    b10_spec = _load_json(B10_SPEC_PATH)
    assert b10_spec.get("algorithm_spec_id") == B10_FROZEN_SPEC_ID, b10_spec.get(
        "algorithm_spec_id"
    )
    assert b10_spec.get("frozen_spec_hash_matched") is True
    b10_report = _load_json(B10_REPORT_PATH)
    assert b10_report.get("algorithm_spec_id") == B10_FROZEN_SPEC_ID


def _regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report so
    the artifact pin matches the in-code build functions. Mirrors the B10
    freeze-write style: deterministic output, canonical JSON."""
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    # Synthetic-fixture report used by the self-test freeze artifact.
    records = [
        _make_record(
            task_bucket="ambiguous",
            query_noise=1.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=True,
            rrf_backed_by_anchor=False,
        ),
        _make_record(
            task_bucket="ambiguous",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=None,
            rrf_backed_by_anchor=True,
        ),
    ]
    report = build_report(records, self_test=True, replay_source="synthetic_fixture")
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    # 1. Functional cases.
    _self_test_perfect_agreement()
    _self_test_disagreement()
    _self_test_missing_feature()
    _self_test_leakage_guard()
    _self_test_replay_aggregate()
    _self_test_verdict_synthetic_fixture_unsupported()
    _self_test_verdict_insufficient_denominator_unsupported()

    # 2. Forbidden scan + B10 reference.
    _self_test_forbidden_scan()
    _self_test_b10_reference()

    # 3. Regenerate on-disk artifacts from the current build functions so the
    # artifact pin matches the code (the spec hash is stable across runs).
    _regenerate_artifacts()

    # 4. Validate the on-disk algorithm spec + a synthesized report.
    spec = _load_json(ALGORITHM_SPEC_PATH)
    spec_hash = _sha256_json(spec)
    verify_algorithm_spec(spec, spec_hash)
    # The on-disk spec must equal the deterministically-generated spec dict so
    # that the report's spec_sha256 (computed from build_algorithm_spec())
    # references the frozen on-disk spec.
    assert spec == build_algorithm_spec(), (
        "on-disk algorithm spec does not match build_algorithm_spec() output"
    )
    # Re-load and re-hash to prove stability.
    spec_again = _load_json(ALGORITHM_SPEC_PATH)
    assert _sha256_json(spec_again) == spec_hash, "algorithm spec hash not stable"

    # Validate the on-disk report too (regenerated above).
    on_disk_report = _load_json(REPORT_PATH)
    verify_report(on_disk_report)

    records = [
        _make_record(
            task_bucket="ambiguous",
            query_noise=1.0,
            candidate_support_exists=True,
            local_anchor=False,
            rrf_backed_by_anchor=True,
        ),
        _make_record(
            task_bucket="plain",
            query_noise=0.0,
            candidate_support_exists=True,
            local_anchor=True,
            rrf_backed_by_anchor=False,
        ),
    ]
    report = build_report(records, self_test=True)
    verify_report(report)

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256": spec_hash,
        "b10_frozen_spec_id": B10_FROZEN_SPEC_ID,
        "b10_frozen_spec_hash_matched": True,
        "algorithm_spec_sha256_stable": True,
        "ambiguous_branch_runtime_shadow_only": True,
        "full_runtime_clean_policy": False,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "self_test_checks": {
            "perfect_agreement": True,
            "disagreement": True,
            "missing_feature": True,
            "leakage_guard": True,
            "replay_aggregate": True,
            "verdict_synthetic_fixture_unsupported": True,
            "verdict_insufficient_denominator_unsupported": True,
            "forbidden_scan": True,
            "b10_reference": True,
            "spec_hash_stable": True,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test", action="store_true", help="run the B10B self-test"
    )
    parser.add_argument(
        "--records",
        type=str,
        default=None,
        help=(
            "path to a JSON array of p25-policy-record-like records OR a JSON "
            "object with a 'records' field (P21/P25 ephemeral payload format); "
            "runs the replay in ci_ephemeral_records mode and writes the "
            "report artifact"
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write the report artifact; defaults to the canonical "
            "b10b_runtime_shadow_replay_report.json artifact path"
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.records:
        parser.error(
            "B10B requires either --self-test or --records <path> in this freeze"
        )
    if args.self_test and args.records:
        parser.error("--self-test and --records are mutually exclusive")
    return args


def _load_records(path: str) -> list[dict[str, Any]]:
    """Load records from a JSON file.

    Accepts either:
    - A JSON array of record objects (legacy/synthetic-fixture format).
    - A JSON object with a ``records`` field (P21/P25 ephemeral payload
      format, schema_version ``p25-policy-records-ephemeral-v1``).

    Detects the format by checking whether the top-level JSON value is a
    list (array) or dict (object).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"records file not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "records" not in data:
            raise ValueError(
                "records file is a JSON object but has no 'records' field "
                "(expected P21/P25 ephemeral payload format with a 'records' "
                "array); refusing to silently treat as zero records"
            )
        items = data["records"]
        if not isinstance(items, list):
            raise ValueError(
                f"'records' field must be a JSON array, got {type(items).__name__}"
            )
    else:
        raise ValueError(
            f"records file must contain a JSON array or object, got "
            f"{type(data).__name__}"
        )
    records: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each record must be a JSON object")
        records.append(item)
    return records


def _print_summary(report: dict[str, Any]) -> None:
    rep = report["replay"]
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "status": report["status"],
        "denominator": rep["denominator"],
        "complete_feature_rate": rep["complete_feature_rate"],
        "agreement_overall_rate": rep["agreement_overall_rate"],
        "target_weak_only_recall": rep["target_weak_only_recall"],
        "target_use_p25_specificity": rep["target_use_p25_specificity"],
        "shadow_weak_only_precision": rep["shadow_weak_only_precision"],
        "label_driven_ambiguous_recall_qn0": rep["label_driven_ambiguous_recall_qn0"],
        "label_driven_ambiguous_denominator_qn0": rep[
            "label_driven_ambiguous_denominator_qn0"
        ],
        "cohens_kappa": rep["cohens_kappa"],
        "silent_failure_checks": rep["silent_failure_checks"],
        "runtime_shadow_ambiguous_supported": report[
            "runtime_shadow_ambiguous_supported"
        ],
        "support_claim": report["support_claim"],
    }
    if "support_claim_reason" in report:
        summary["support_claim_reason"] = report["support_claim_reason"]
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B10B self-test: PASS", file=sys.stderr)
        return 0
    if args.records:
        records = _load_records(args.records)
        report = build_report(
            records, self_test=False, replay_source="ci_ephemeral_records"
        )
        verify_report(report)
        out_path = Path(args.out) if args.out else REPORT_PATH
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B10B replay report written to {out_path}", file=sys.stderr)
        return 0
    print("B10B requires --self-test or --records", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
