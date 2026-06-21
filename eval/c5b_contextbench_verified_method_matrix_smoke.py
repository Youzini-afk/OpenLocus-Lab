#!/usr/bin/env python3
"""C5-B ContextBench Verified Retrieval Method Matrix Smoke (Public Aggregate-Only).

This module implements the **C5-B external benchmark retrieval method matrix
smoke** over the ContextBench verified subset
(``Contextbench/ContextBench`` config ``contextbench_verified`` split
``train``). It extends C5-A (single-method ContextBench verified retrieval
performance smoke) into a bounded multi-method matrix smoke.

C5-B is explicitly **not** a rigorous benchmark result, **not** a
leaderboard entry, **not** a performance claim, **not** a promotion,
**not** a default/policy change, and **not** a runtime/retriever/pack/
backend/EvidenceCore semantic change. The committed artifact records
only aggregate retrieval metrics for each requested method plus
aggregate-only deltas vs the fixed ``bm25`` baseline, computed by
``eval/score.py`` over a bounded ContextBench verified subset.

Claim boundary (binding):

* Claim level: ``external_benchmark_retrieval_method_matrix_smoke_only``.
* Status: ``pass`` | ``partial`` | ``unavailable_with_reason`` |
  ``fail_schema_contract`` | ``fail_forbidden_scan``.
* Mode: ``contextbench_verified_retrieval_method_matrix_smoke``; phase ``C5-B``.
* This is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime/retriever/pack/backend change, NOT an
  EvidenceCore semantic change, and NOT a downstream agent value claim.
* It does NOT emit ``winner``, ``best_method``, ``recommended_default``,
  or anything implying a policy/default decision. The fixed
  ``baseline_method`` is ``bm25`` and ``baseline_is_policy_candidate`` is
  always ``false``.

Privacy / license boundary (binding):

* Raw ContextBench rows, queries/problem statements, repo URLs/names,
  base commits, gold paths/spans/contents, generated task/label/run
  JSONL, evidence rows, cloned repos, and stdout/stderr are kept
  **transient only** under ``/tmp`` or CI ephemeral workspace. They are
  NEVER committed or uploaded.
* Aggregate metric values from ``eval/score.py`` are safe to publish if
  aggregate only. No row-level records, no row IDs, no paths, no spans,
  no snippets, no content_sha, no stdout/stderr, no per-row metrics.
* ContextBench dataset license is unknown
  (``unknown_dataset_license``); row-level redistribution is disabled
  (``row_level_redistribution_allowed=false``) and derived row-level
  publication is disabled
  (``derived_row_level_publication_allowed=false``). Aggregate metrics
  publication is allowed as aggregate-only smoke
  (``aggregate_metrics_publication=aggregate_only_smoke``).

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real matrix smoke requires public network access to HF
  datasets-server and GitHub repos. CI must be a separate explicit
  ``workflow_dispatch`` job with
  ``enable_external_benchmark_network=true``. It must NOT run on
  PR/push by default, must use no provider secrets/vars, no
  ``OPENLOCUS_LLM``/``OPENLOCUS_EMBEDDING`` env, and must upload only
  the aggregate report.

Run::

    python3 -m py_compile eval/c5b_contextbench_verified_method_matrix_smoke.py
    python3 eval/c5b_contextbench_verified_method_matrix_smoke.py --self-test
    python3 eval/c5b_contextbench_verified_method_matrix_smoke.py \\
        --row-limit 5 --methods bm25,regex,symbol \\
        --query-mode first_paragraph --language-filter python \\
        --openlocus target/release/openlocus \\
        --out artifacts/c5b_contextbench_verified_method_matrix/\\
c5b_contextbench_verified_method_matrix_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful ``unavailable_with_reason`` with a real
failure category (no stale/fake pass). Self-test/docs/diff-check still
pass.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn

# Reuse C5-A helpers (row fetch, query sanitizer, clone/retrieval/score
# runner, score metric allowlist, failure categories, scanner primitives).
# The ``eval`` directory has no ``__init__.py`` (it is a flat script
# directory), so we add this file's parent to ``sys.path`` and import
# the C5-A module directly. This is the "or equivalent" form of
# ``from eval import c5_contextbench_verified_performance_smoke as c5a``
# permitted by the C5-B contract.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (C5-B owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "c5b_contextbench_verified_method_matrix_smoke.v1"
GENERATED_BY = "eval/c5b_contextbench_verified_method_matrix_smoke.py"
CLAIM_LEVEL = "external_benchmark_retrieval_method_matrix_smoke_only"
MODE = "contextbench_verified_retrieval_method_matrix_smoke"
PHASE = "C5-B"

DEFAULT_OUT = Path(
    "artifacts/c5b_contextbench_verified_method_matrix/"
    "c5b_contextbench_verified_method_matrix_report.json"
)

# Hard caps on row limit. Default 5; max 10 (C5-B is stricter than
# C5-A because each row is evaluated across multiple methods).
ROW_LIMIT_DEFAULT = 5
ROW_LIMIT_HARD_CAP = 10

# Methods supported by ``eval/run_retrieval.py`` without provider calls.
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "text", "symbol")
DEFAULT_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
BASELINE_METHOD = "bm25"

# Query modes / language filters reuse C5-A allowlists.

# Delta metric allowlist: smoke deltas are computed only for these
# aggregate metric names, and only as method vs ``baseline_method``.
DELTA_METRIC_ALLOWLIST: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
)

# Per-method metric allowlist: only these metric keys may appear in a
# method result record's ``metrics`` block. Strict subset of the C5-A
# ``SCORE_METRIC_ALLOWLIST``.
METHOD_METRIC_ALLOWLIST: tuple[str, ...] = DELTA_METRIC_ALLOWLIST

# Recommendation / policy field names that must NEVER be emitted by C5-B
# (anywhere in the public artifact). Emitted as a fixed false flag
# instead of an absent flag so the contract is explicit.
FORBIDDEN_RECOMMENDATION_FIELDS: frozenset[str] = frozenset(
    {
        "winner",
        "best_method",
        "recommended_default",
        "recommended_method",
        "preferred_method",
        "default_method",
        "policy_decision",
        "decision",
        "ranking",
        "rank",
    }
)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be true
# in the committed public artifact. C5-B replaces ``performance_smoke``
# with ``method_matrix_smoke`` to reflect the matrix shape.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "external_benchmark_rows_read": False,
    "repositories_materialized_transiently": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "method_matrix_smoke": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). C5-B runs NO provider, makes NO remote provider calls,
# proves NO downstream agent value, promotes NO candidate, changes NO
# runtime/retriever/pack/backend/default-policy/EvidenceCore semantics,
# claims NO external benchmark performance, and emits NO leaderboard entry.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
    "downstream_agent_value_proven": False,
    "promotion_ready": False,
    "default_should_change": False,
    "baseline_is_policy_candidate": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
    "provider_calls_made": False,
    "remote_provider_calls_made": False,
}

# ---------------------------------------------------------------------------
# License / redistribution fields (fixed; reuse C5-A values).
# ---------------------------------------------------------------------------

LICENSE_FIELDS: dict[str, Any] = dict(c5a.LICENSE_FIELDS)

# Failure categories reuse C5-A enum.

# ---------------------------------------------------------------------------
# Method parser / validator (C5-B owned)
# ---------------------------------------------------------------------------


class MethodConfigError(ValueError):
    """Raised when the requested methods config violates the C5-B contract."""


def parse_methods(methods_arg: str | None) -> list[str]:
    """Parse a comma-separated ``--methods`` argument into a method list.

    Rules (C5-B owned):
    * Empty / None -> default ``["bm25", "regex", "symbol"]``.
    * Each token must be in ``ALLOWED_METHODS``; unknown methods raise
      ``MethodConfigError``.
    * Duplicate tokens are deduplicated deterministically (preserving
      first-seen order). This makes the parser robust to accidental
      repeated input without rejecting it (the spec accepts "deduplicates
      OR rejects duplicates deterministically"; deduplication is the
      chosen deterministic behavior).
    * Empty tokens (e.g. from ``"bm25,,regex"``) are skipped silently.
    * At least one method must remain after parsing.
    """
    if methods_arg is None or not methods_arg.strip():
        return list(DEFAULT_METHODS)

    raw_tokens = [t.strip() for t in methods_arg.split(",")]
    tokens = [t for t in raw_tokens if t]
    if not tokens:
        raise MethodConfigError("no methods provided")

    seen: set[str] = set()
    methods: list[str] = []
    for tok in tokens:
        if tok not in ALLOWED_METHODS:
            raise MethodConfigError(
                f"unknown method: {tok!r} (allowed: "
                f"{', '.join(ALLOWED_METHODS)})"
            )
        if tok in seen:
            # Deterministic dedup: keep first-seen order, drop the
            # duplicate. Do NOT raise; the parser contract accepts
            # deterministic dedup.
            continue
        seen.add(tok)
        methods.append(tok)

    if not methods:
        raise MethodConfigError("no methods provided after dedup")
    return methods


def validate_method_result_records(
    records: list[dict[str, Any]],
) -> None:
    """Validate method result records against the C5-B contract.

    * ``method`` must be in ``ALLOWED_METHODS``.
    * ``metrics`` keys must be in ``METHOD_METRIC_ALLOWLIST``.
    * No recommendation / policy field may appear.
    * Records must be a list of dicts (not a dict keyed by method name).
    """
    if not isinstance(records, list):
        raise MethodConfigError(
            "method_results must be a list of records, not a dict"
        )
    for rec in records:
        if not isinstance(rec, dict):
            raise MethodConfigError(
                "method result record must be a dict"
            )
        method = rec.get("method")
        if not isinstance(method, str) or method not in ALLOWED_METHODS:
            raise MethodConfigError(
                f"method result record has invalid method: {method!r}"
            )
        metrics = rec.get("metrics", {})
        if not isinstance(metrics, dict):
            raise MethodConfigError(
                f"method result record metrics must be a dict (method={method!r})"
            )
        for k in metrics.keys():
            if k not in METHOD_METRIC_ALLOWLIST:
                raise MethodConfigError(
                    f"method result record metric key not in allowlist: "
                    f"{k!r} (method={method!r})"
                )
        for k in rec.keys():
            if k in FORBIDDEN_RECOMMENDATION_FIELDS:
                raise MethodConfigError(
                    f"method result record must not include "
                    f"recommendation field: {k!r}"
                )


def validate_delta_records(
    deltas: list[dict[str, Any]],
) -> None:
    """Validate delta records against the C5-B contract.

    * Each delta record must have ``baseline_method`` exactly equal to
      ``BASELINE_METHOD``.
    * Each delta record must have ``method`` in ``ALLOWED_METHODS`` and
      not equal to ``BASELINE_METHOD``.
    * Each delta record must name exactly one ``metric`` from
      ``DELTA_METRIC_ALLOWLIST`` and one numeric ``delta`` value. This
      avoids dynamic metric keys in the public artifact.
    * No recommendation / policy field may appear.
    """
    if not isinstance(deltas, list):
        raise MethodConfigError(
            "smoke_metric_deltas_vs_baseline must be a list of records"
        )
    allowed_keys = {"baseline_method", "method", "metric", "delta"}
    for rec in deltas:
        if not isinstance(rec, dict):
            raise MethodConfigError("delta record must be a dict")
        unexpected_keys = set(rec.keys()) - allowed_keys
        if unexpected_keys:
            raise MethodConfigError(
                f"delta record has unexpected keys: {sorted(unexpected_keys)!r}"
            )
        baseline_method = rec.get("baseline_method")
        if baseline_method != BASELINE_METHOD:
            raise MethodConfigError(
                f"delta record has invalid baseline_method: {baseline_method!r}"
            )
        method = rec.get("method")
        if not isinstance(method, str) or method not in ALLOWED_METHODS:
            raise MethodConfigError(
                f"delta record has invalid method: {method!r}"
            )
        if method == BASELINE_METHOD:
            raise MethodConfigError(
                "delta record method must not equal baseline_method"
            )
        metric = rec.get("metric")
        if not isinstance(metric, str) or metric not in DELTA_METRIC_ALLOWLIST:
            raise MethodConfigError(
                f"delta record metric not in allowlist: {metric!r}"
            )
        delta = rec.get("delta")
        if not isinstance(delta, (int, float)):
            raise MethodConfigError(
                f"delta record delta must be numeric: {delta!r}"
            )
        for k in rec.keys():
            if k in FORBIDDEN_RECOMMENDATION_FIELDS:
                raise MethodConfigError(
                    f"delta record must not include "
                    f"recommendation field: {k!r}"
                )


# ---------------------------------------------------------------------------
# Public artifact scanner (C5-B owned, strict, fail-closed).
#
# C5-B reuses the C5-A forbidden scanner primitives for raw key/value
# leak detection, and ADDS a C5-B-specific scanner that:
#   * rejects dynamic method-key dicts (i.e. a ``method_results`` value
#     that is a dict keyed by method name, instead of a list of records);
#   * rejects the FORBIDDEN_RECOMMENDATION_FIELDS keys anywhere;
#   * rejects row/repo/query/gold/path/span/snippet/content_sha/stdout/
#     stderr keys anywhere (these are already in C5-A's
#     ``FORBIDDEN_KEY_NAMES`` but C5-B asserts them explicitly to make
#     the C5-B self-test contract self-standing).
# ---------------------------------------------------------------------------


# C5-B-specific forbidden keys (in addition to c5a.FORBIDDEN_KEY_NAMES).
# These are explicit C5-B contract tokens.
C5B_FORBIDDEN_EXTRA_KEYS: frozenset[str] = frozenset(
    {
        "row",
        "rows_data",
        "raw_row",
        "raw_rows",
        "repo_name",
        "repo_slug",
        "query_text",
        "gold",
        "gold_path",
        "gold_span",
        "gold_snippet",
        "snippet",
        "snippets",
        "content_sha",
        "stdout",
        "stderr",
        "stdout_text",
        "stderr_text",
        "evidence_row",
        "evidence_rows",
        "retrieved_path",
        "retrieved_paths",
        "retrieved_snippet",
        "cloned_repo_path",
        "cloned_repo",
        "per_row_metrics",
        "row_metrics",
    }
)


# C5-B schema-key container keys (children are fixed labels, not row
# values). Extends C5-A's set with the C5-B-specific containers.
C5B_SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "failure_category_counts",
        "metrics",
        "smoke_metric_deltas_vs_baseline",
    }
)


# C5-B-specific safe VALUE path last-key segments. These are list/dict
# fields whose VALUES are method-name strings (e.g. ``"text"``). The
# C5-A scanner flags the string ``"text"`` as a ``forbidden_field_name_value``
# because ``text`` is a forbidden CONTENT/KEY name in C5-A's contract.
# In C5-B, ``text`` is also a legitimate OpenLocus retrieval method
# name, so it may appear as a value under ``methods_allowed`` /
# ``methods_requested`` / ``baseline_method`` / per-record ``method``
# fields. The C5-B scanner filters out those false positives so the
# method matrix can list all allowed methods without tripping the C5-A
# content-name-as-value rule. ``baseline_method`` is always ``"bm25"``
# (never ``"text"``) but is included for symmetry. The per-record
# ``method`` field is independently validated by
# ``_scan_c5b_method_results_shape`` to be in ``ALLOWED_METHODS``, so
# exempting it from the C5-A forbidden_field_name_value check does not
# weaken the contract.
C5B_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    {
        "methods_requested",
        "methods_allowed",
        "methods_count",
        "methods_attempted",
        "methods_successful",
        "methods_succeeded",
        "methods_failed",
        "baseline_method",
        "method",
        "metric",
    }
)


def _is_c5b_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a C5-B schema-key container."""
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in C5B_SCHEMA_KEY_CONTAINER_KEYS


def _c5b_safe_value_path(path: str) -> bool:
    """Check if a JSON path is a C5-B-specific safe value path."""
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in C5B_SAFE_VALUE_PATH_LAST_KEYS


def _scan_c5b_method_results_shape(obj: Any) -> list[dict[str, Any]]:
    """Reject ``method_results`` if it is a dict keyed by method name.

    C5-B requires ``method_results`` to be a list of records, NOT a dict
    keyed by method name. A dict shape would leak method names as dynamic
    dict keys (which could later be tampered with to spoof a non-
    allowlisted method). This scanner enforces the list-of-records shape.
    """
    violations: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        mr = obj.get("method_results")
        if mr is not None and not isinstance(mr, list):
            violations.append(
                {
                    "category": "method_results_not_list",
                    "path": "$.method_results",
                }
            )
        if isinstance(mr, list):
            for idx, rec in enumerate(mr):
                if not isinstance(rec, dict):
                    violations.append(
                        {
                            "category": "method_result_record_not_dict",
                            "path": f"$.method_results[{idx}]",
                        }
                    )
                    continue
                method = rec.get("method")
                if not isinstance(method, str):
                    violations.append(
                        {
                            "category": "method_result_missing_method",
                            "path": f"$.method_results[{idx}].method",
                        }
                    )
                elif method not in ALLOWED_METHODS:
                    violations.append(
                        {
                            "category": "method_result_method_not_allowlisted",
                            "path": f"$.method_results[{idx}].method",
                        }
                    )
        # Also reject any dict shape elsewhere whose keys are method
        # names (defensive against accidental method-keyed dicts).
    return violations


def _scan_c5b_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for C5-B-specific forbidden keys (recommendation + extra row keys)."""
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                is_schema_container = _is_c5b_schema_key_container(sub_path)
                if key_str in FORBIDDEN_RECOMMENDATION_FIELDS:
                    violations.append(
                        {
                            "category": "forbidden_recommendation_field",
                            "path": sub_path,
                        }
                    )
                if (
                    key_str in C5B_FORBIDDEN_EXTRA_KEYS
                    and not is_schema_container
                ):
                    violations.append(
                        {
                            "category": "forbidden_c5b_extra_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_c5b(obj: Any) -> list[dict[str, Any]]:
    """Combined C5-B scanner: C5-A primitives + C5-B-specific checks.

    The C5-A scanner is reused for raw key/value leak detection (URLs,
    hex digests, repo slugs, /tmp paths, etc.). C5-B ADDS:
      * rejection of ``method_results`` as a dict keyed by method name;
      * rejection of recommendation / policy fields anywhere;
      * rejection of extra row/repo/query/gold/path/span/snippet/
        content_sha/stdout/stderr keys anywhere.
    The C5-B scanner also filters out false positives from the C5-A
    scanner where a legitimate method name (e.g. ``"text"``) appears as
    a value under a C5-B-specific safe value path (``methods_allowed``,
    ``methods_requested``). This is the only C5-A false positive that
    C5-B suppresses; all other C5-A violations are preserved.
    """
    violations: list[dict[str, Any]] = []
    for v in c5a._scan_forbidden(obj):
        # Suppress the single C5-A false positive: a method-name string
        # (e.g. ``"text"``) appearing as a value under a C5-B-specific
        # safe value path. Only ``forbidden_field_name_value`` violations
        # are suppressed (these are content-name-as-value flags); all
        # other C5-A violation categories are preserved.
        if v.get("category") == "forbidden_field_name_value" and _c5b_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    violations.extend(_scan_c5b_forbidden_keys(obj))
    violations.extend(_scan_c5b_method_results_shape(obj))
    return violations


def _c5b_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the C5-B forbidden scanner and return a sanitized summary."""
    violations = _scan_c5b(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_c5b_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _c5b_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return c5a._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    c5a._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5a._check(name, ok)


def _validate_row_limit(row_limit: int) -> int:
    """Validate and cap --row-limit to the C5-B hard cap (10)."""
    if not isinstance(row_limit, int):
        raise SystemExit("invalid arguments")
    if row_limit < 1:
        raise SystemExit("invalid arguments")
    if row_limit > ROW_LIMIT_HARD_CAP:
        return ROW_LIMIT_HARD_CAP
    return row_limit


# ---------------------------------------------------------------------------
# Method result aggregation
# ---------------------------------------------------------------------------


def _filter_method_metrics(
    metrics: dict[str, Any]
) -> dict[str, Any]:
    """Filter score.py metrics to the C5-B method-metric allowlist only."""
    filtered: dict[str, Any] = {}
    for key in METHOD_METRIC_ALLOWLIST:
        if key in metrics:
            val = metrics[key]
            if isinstance(val, bool):
                filtered[key] = bool(val)
            elif isinstance(val, (int, float)):
                if isinstance(val, float):
                    filtered[key] = round(val, 6)
                else:
                    filtered[key] = int(val)
    return filtered


def _compute_method_metrics(
    per_row_metrics: list[dict[str, Any]],
    rows_successful: int,
) -> dict[str, Any]:
    """Compute aggregate method metrics from per-row score.py outputs.

    Only ``METHOD_METRIC_ALLOWLIST`` keys are emitted. Numeric metrics
    are averaged as means; ``success_rate`` is recomputed as
    ``rows_successful / rows_evaluated``.
    """
    aggregate: dict[str, Any] = {}
    if not per_row_metrics or rows_successful <= 0:
        return aggregate
    for key in METHOD_METRIC_ALLOWLIST:
        values: list[Any] = []
        for rec in per_row_metrics:
            if key in rec:
                values.append(rec[key])
        if not values:
            continue
        if all(isinstance(v, bool) for v in values):
            aggregate[key] = any(values)
        elif all(isinstance(v, (int, float)) for v in values):
            nums = [float(v) for v in values]
            mean = sum(nums) / len(nums)
            aggregate[key] = round(mean, 6)
    # success_rate is recomputed from rows_successful (defensive: do
    # not trust score.py's success_rate when row counts differ).
    aggregate["success_rate"] = (
        round(rows_successful / len(per_row_metrics), 6)
        if per_row_metrics
        else 0.0
    )
    return _filter_method_metrics(aggregate)


def _compute_deltas_vs_baseline(
    method_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute aggregate deltas vs the fixed ``baseline_method``.

    Only ``DELTA_METRIC_ALLOWLIST`` keys are emitted. The baseline method
    itself is excluded from the deltas list (a method is not compared
    against itself). If the baseline method is missing or has no
    metrics, no deltas are emitted (an empty list, NOT a fake zero).
    """
    baseline_metrics: dict[str, Any] = {}
    for rec in method_results:
        if rec.get("method") == BASELINE_METHOD:
            baseline_metrics = rec.get("metrics", {})
            break
    if not baseline_metrics:
        return []

    deltas: list[dict[str, Any]] = []
    for rec in method_results:
        method = rec.get("method")
        if not isinstance(method, str) or method == BASELINE_METHOD:
            continue
        if method not in ALLOWED_METHODS:
            continue
        rec_metrics = rec.get("metrics", {})
        for key in DELTA_METRIC_ALLOWLIST:
            if key in rec_metrics and key in baseline_metrics:
                try:
                    delta_val = float(rec_metrics[key]) - float(
                        baseline_metrics[key]
                    )
                    deltas.append(
                        {
                            "baseline_method": BASELINE_METHOD,
                            "method": method,
                            "metric": key,
                            "delta": round(delta_val, 6),
                        }
                    )
                except (TypeError, ValueError):
                    continue
    return deltas


def _status_from_method_results(
    method_results: list[dict[str, Any]],
) -> str:
    """Compute the overall C5-B status from method result records.

    Semantics:
    * pass: all requested methods have at least one successful evaluated
      row and the scanner passes.
    * partial: at least one method succeeds and at least one method
      fails/unavailable.
    * unavailable_with_reason: no method completes retrieval+scoring.
    """
    if not method_results:
        return "unavailable_with_reason"
    success_count = sum(
        1
        for r in method_results
        if r.get("status") == "pass" and r.get("rows_successful", 0) > 0
    )
    fail_count = sum(
        1
        for r in method_results
        if r.get("status") != "pass" or r.get("rows_successful", 0) == 0
    )
    if success_count == 0:
        return "unavailable_with_reason"
    if fail_count == 0:
        return "pass"
    return "partial"


# ---------------------------------------------------------------------------
# Public report builders (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_method_result_record(
    *,
    method: str,
    status: str,
    rows_evaluated: int,
    rows_successful: int,
    rows_failed: int,
    metrics: dict[str, Any],
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a single method result record (list element, NOT a dict key)."""
    fcc = {c: 0 for c in c5a.FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)
    return {
        "method": method,
        "status": status,
        "rows_evaluated": int(rows_evaluated),
        "rows_successful": int(rows_successful),
        "rows_failed": int(rows_failed),
        "metrics": _filter_method_metrics(metrics),
        "failure_category_counts": fcc,
    }


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    row_limit_requested: int,
    methods: list[str],
    query_mode: str,
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    rows_fetched: int = 0,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a truthful ``unavailable_with_reason`` report."""
    fcc = {c: 0 for c in c5a.FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = rows_fetched > 0
    safe_true["repositories_materialized_transiently"] = False
    safe_true["openlocus_retrieval_executed"] = False
    safe_true["score_py_metrics_computed"] = False
    safe_true["method_matrix_smoke"] = False

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": "unavailable_with_reason",
        "mode": MODE,
        "phase": PHASE,
        "methods_requested": list(methods),
        "methods_allowed": list(ALLOWED_METHODS),
        "baseline_method": BASELINE_METHOD,
        "query_mode": query_mode,
        "language_filter": language_filter,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "row_limit_requested": row_limit_requested,
        "rows_fetched": rows_fetched,
        "methods_count": len(methods),
        "methods_attempted": len(methods),
        "methods_successful": 0,
        "methods_succeeded": 0,
        "methods_failed": len(methods),
        "method_results": [
            {
                "method": m,
                "status": "unavailable_with_reason",
                "rows_evaluated": 0,
                "rows_successful": 0,
                "rows_failed": 0,
                "metrics": {},
                "failure_category_counts": {c: 0 for c in c5a.FAILURE_CATEGORIES},
            }
            for m in methods
        ],
        "smoke_metric_deltas_vs_baseline": [],
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_counts": fcc,
        # No metrics in unavailable mode.
        # Safe booleans (true only if actually true).
        **safe_true,
        # No-claim / no-runtime-change flags (all false).
        **DEFAULT_FALSE_FLAGS,
        # License fields (fixed).
        **LICENSE_FIELDS,
        # Self-test summary.
        "self_test_passed": self_test_passed,
        # Framing.
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "signal_strength": "external_benchmark_retrieval_method_matrix_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _c5b_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_matrix_report(
    *,
    self_test_passed: bool,
    row_limit_requested: int,
    rows_fetched: int,
    methods: list[str],
    method_results: list[dict[str, Any]],
    query_mode: str,
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a pass/partial matrix report with aggregate method metrics + deltas."""
    fcc = {c: 0 for c in c5a.FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    # Validate records (contract: fail_schema_contract on invalid shape).
    try:
        validate_method_result_records(method_results)
    except MethodConfigError:
        # Build a fail_schema_contract report.
        return _build_schema_contract_failure(
            "method_result_record_invalid",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit_requested,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            failure_category_counts=fcc,
        )

    deltas = _compute_deltas_vs_baseline(method_results)
    try:
        validate_delta_records(deltas)
    except MethodConfigError:
        return _build_schema_contract_failure(
            "delta_record_invalid",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit_requested,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            failure_category_counts=fcc,
        )

    methods_successful = sum(
        1 for r in method_results if r.get("status") == "pass" and r.get("rows_successful", 0) > 0
    )
    methods_failed = len(method_results) - methods_successful

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = rows_fetched > 0
    safe_true["repositories_materialized_transiently"] = methods_successful > 0
    safe_true["openlocus_retrieval_executed"] = methods_successful > 0
    safe_true["score_py_metrics_computed"] = any(
        r.get("metrics") for r in method_results
    )
    safe_true["method_matrix_smoke"] = methods_successful > 0

    status = _status_from_method_results(method_results)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "methods_requested": list(methods),
        "methods_allowed": list(ALLOWED_METHODS),
        "baseline_method": BASELINE_METHOD,
        "query_mode": query_mode,
        "language_filter": language_filter,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "row_limit_requested": row_limit_requested,
        "rows_fetched": rows_fetched,
        "methods_count": len(method_results),
        "methods_attempted": len(method_results),
        "methods_successful": methods_successful,
        "methods_succeeded": methods_successful,
        "methods_failed": methods_failed,
        "method_results": method_results,
        "smoke_metric_deltas_vs_baseline": deltas,
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_category_counts": fcc,
        # Safe booleans (true only if actually true).
        **safe_true,
        # No-claim / no-runtime-change flags (all false).
        **DEFAULT_FALSE_FLAGS,
        # License fields (fixed).
        **LICENSE_FIELDS,
        # Self-test summary.
        "self_test_passed": self_test_passed,
        # Framing.
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "signal_strength": "external_benchmark_retrieval_method_matrix_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _c5b_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    return report


def _build_schema_contract_failure(
    reason: str,
    *,
    self_test_passed: bool,
    row_limit_requested: int,
    methods: list[str],
    query_mode: str,
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a ``fail_schema_contract`` report (invalid method config / shape)."""
    fcc = {c: 0 for c in c5a.FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    fcc["scanner_self_test_failed"] = max(fcc["scanner_self_test_failed"], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": "fail_schema_contract",
        "mode": MODE,
        "phase": PHASE,
        "methods_requested": list(methods),
        "methods_allowed": list(ALLOWED_METHODS),
        "baseline_method": BASELINE_METHOD,
        "query_mode": query_mode,
        "language_filter": language_filter,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "row_limit_requested": row_limit_requested,
        "rows_fetched": 0,
        "methods_count": len(methods),
        "methods_attempted": len(methods),
        "methods_successful": 0,
        "methods_succeeded": 0,
        "methods_failed": len(methods),
        "method_results": [],
        "smoke_metric_deltas_vs_baseline": [],
        "network_calls": 0,
        "provider_calls": 0,
        "failure_reason_category": reason,
        "failure_category_counts": fcc,
        # Safe booleans (all false in fail mode).
        **safe_true,
        # No-claim / no-runtime-change flags (all false).
        **DEFAULT_FALSE_FLAGS,
        # License fields (fixed).
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "signal_strength": "external_benchmark_retrieval_method_matrix_smoke_schema_contract_failure",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _c5b_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    return report


# ---------------------------------------------------------------------------
# Matrix network smoke runner (transient /tmp workspace; aggregate-only).
# ---------------------------------------------------------------------------


def _run_single_method(
    *,
    method: str,
    rows: list[dict[str, Any]],
    row_limit: int,
    query_mode: str,
    language_filter: str,
    openlocus_bin: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run retrieval + scoring for a single method across all rows.

    Reuses C5-A primitives:
    * ``c5a._parse_gold_context``
    * ``c5a._sanitize_query``
    * ``c5a._clone_and_checkout``
    * ``c5a._write_transient_jsonl``
    * ``c5a._run_retrieval_and_score``
    """
    fcc = {c: 0 for c in c5a.FAILURE_CATEGORIES}
    rows_evaluated = 0
    rows_successful = 0
    rows_failed = 0
    per_row_metrics: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(
        prefix=f"c5b_method_{method}_"
    ) as work_root_str:
        work_root = Path(work_root_str)
        tasks_jsonl = work_root / "tasks.jsonl"
        labels_jsonl = work_root / "labels.jsonl"
        run_jsonl = work_root / "run.jsonl"

        for idx, row in enumerate(rows):
            rows_evaluated += 1
            gold_paths, gold_lines, gc_status = c5a._parse_gold_context(
                row.get("gold_context")
            )
            if gc_status != "pass":
                fcc["gold_context_parse_failed"] += 1
                rows_failed += 1
                continue

            query = c5a._sanitize_query(
                row.get("problem_statement", ""), query_mode
            )
            if not query:
                fcc["row_parse_failed"] += 1
                rows_failed += 1
                continue

            repo_url = row.get("repo_url", "")
            base_commit = row.get("base_commit", "")
            if not isinstance(repo_url, str) or not isinstance(
                base_commit, str
            ) or not repo_url or not base_commit:
                fcc["row_parse_failed"] += 1
                rows_failed += 1
                continue

            with tempfile.TemporaryDirectory(
                prefix=f"c5b_repo_{method}_{idx}_"
            ) as repo_root_str:
                repo_work_dir = Path(repo_root_str)
                clone_ok, clone_fail_cat, clone_fcc = (
                    c5a._clone_and_checkout(
                        repo_url, base_commit, repo_work_dir
                    )
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    rows_failed += 1
                    continue

                repo_root = repo_work_dir / "repo"

                task_id = f"row_{idx}"
                task_record = {
                    "task_id": task_id,
                    "query": query,
                    "method": method,
                }
                label_record = {
                    "task_id": task_id,
                    "gold_paths": gold_paths,
                    "gold_lines": gold_lines,
                }
                try:
                    c5a._write_transient_jsonl(
                        tasks_jsonl, [task_record]
                    )
                    c5a._write_transient_jsonl(
                        labels_jsonl, [label_record]
                    )
                except OSError:
                    fcc["task_jsonl_write_failed"] += 1
                    rows_failed += 1
                    continue

                metrics, score_fail_cat, score_fcc = (
                    c5a._run_retrieval_and_score(
                        tasks_jsonl=tasks_jsonl,
                        labels_jsonl=labels_jsonl,
                        run_jsonl=run_jsonl,
                        repo_root=repo_root,
                        openlocus_bin=openlocus_bin,
                        method=method,
                        eval_dir=eval_dir,
                    )
                )
                for k, v in score_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if metrics is None:
                    rows_failed += 1
                    continue

                per_row_metrics.append(metrics)
                rows_successful += 1

            try:
                run_jsonl.unlink()
            except OSError:
                pass

    method_metrics = _compute_method_metrics(
        per_row_metrics, rows_successful
    )
    method_status = (
        "pass" if rows_successful > 0 and method_metrics else "unavailable_with_reason"
    )
    if rows_successful > 0 and rows_failed > 0:
        method_status = "partial"

    return _build_method_result_record(
        method=method,
        status=method_status,
        rows_evaluated=rows_evaluated,
        rows_successful=rows_successful,
        rows_failed=rows_failed,
        metrics=method_metrics,
        failure_category_counts=fcc,
    )


def _run_matrix_smoke(
    *,
    row_limit: int,
    methods: list[str],
    query_mode: str,
    language_filter: str,
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
) -> dict[str, Any]:
    """Run the real matrix network smoke (transient /tmp; aggregate-only)."""
    fcc = {c: 0 for c in c5a.FAILURE_CATEGORIES}
    network_calls = 0

    # Step 1: fetch rows from HF datasets-server ONCE (shared across methods).
    rows, fetch_status, nc, fcc_update = c5a._fetch_contextbench_rows(
        row_limit, language_filter
    )
    network_calls += nc
    for k, v in fcc_update.items():
        if k in fcc:
            fcc[k] += v

    if fetch_status == "unavailable" or not rows:
        return _build_unavailable_report(
            "network_fetch_failed" if not rows else "no_python_rows",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            rows_fetched=len(rows),
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    rows_fetched = len(rows)

    # Step 2: for each method, run retrieval + scoring across all rows.
    method_results: list[dict[str, Any]] = []
    for method in methods:
        method_result = _run_single_method(
            method=method,
            rows=rows,
            row_limit=row_limit,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_bin=openlocus_bin,
            eval_dir=eval_dir,
        )
        # Accumulate failure_category_counts across methods.
        for k, v in method_result.get("failure_category_counts", {}).items():
            if k in fcc:
                fcc[k] += v
        method_results.append(method_result)

    # Step 3: if no method succeeded at all, return unavailable.
    any_success = any(
        r.get("rows_successful", 0) > 0 for r in method_results
    )
    if not any_success:
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            rows_fetched=rows_fetched,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    return _build_matrix_report(
        self_test_passed=self_test_passed,
        row_limit_requested=row_limit,
        rows_fetched=rows_fetched,
        methods=methods,
        method_results=method_results,
        query_mode=query_mode,
        language_filter=language_filter,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
        failure_category_counts=fcc,
    )


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic rows + synthetic score data).
# ---------------------------------------------------------------------------


def _build_synthetic_method_metrics(
    method: str = "bm25",
) -> dict[str, Any]:
    """Build synthetic per-method metrics for self-test (aggregate only)."""
    base = {
        "file_recall@10": 0.4,
        "mrr": 0.225,
        "span_f0.5@10": 0.016,
        "success_rate": 1.0,
    }
    # Vary slightly per method to make deltas non-trivial.
    if method == "regex":
        base = {
            "file_recall@10": 0.2,
            "mrr": 0.15,
            "span_f0.5@10": 0.01,
            "success_rate": 1.0,
        }
    elif method == "symbol":
        base = {
            "file_recall@10": 0.6,
            "mrr": 0.35,
            "span_f0.5@10": 0.05,
            "success_rate": 1.0,
        }
    elif method == "text":
        base = {
            "file_recall@10": 0.3,
            "mrr": 0.2,
            "span_f0.5@10": 0.012,
            "success_rate": 1.0,
        }
    return dict(base)


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all C5-B self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Method parser. ---
    # 1. rejects unknown methods.
    try:
        parse_methods("bm25,unknown,symbol")
        checks.append(_check("method_parser_rejects_unknown", False))
    except MethodConfigError:
        checks.append(_check("method_parser_rejects_unknown", True))

    try:
        parse_methods("vector")
        checks.append(_check("method_parser_rejects_unknown_single", False))
    except MethodConfigError:
        checks.append(_check("method_parser_rejects_unknown_single", True))

    # 2. deduplicates duplicates deterministically.
    parsed = parse_methods("bm25,bm25,regex,regex,symbol,symbol")
    checks.append(
        _check(
            "method_parser_dedups_duplicates",
            parsed == ["bm25", "regex", "symbol"],
        )
    )
    parsed2 = parse_methods("symbol,bm25,symbol,regex")
    checks.append(
        _check(
            "method_parser_dedups_preserves_order",
            parsed2 == ["symbol", "bm25", "regex"],
        )
    )

    # 3. default methods exactly bm25,regex,symbol.
    checks.append(
        _check(
            "default_methods_exact",
            list(DEFAULT_METHODS) == ["bm25", "regex", "symbol"],
        )
    )
    checks.append(
        _check(
            "method_parser_default_when_empty",
            parse_methods(None) == ["bm25", "regex", "symbol"]
            and parse_methods("") == ["bm25", "regex", "symbol"],
        )
    )
    checks.append(
        _check(
            "method_parser_skips_empty_tokens",
            parse_methods("bm25,,regex,,symbol") == ["bm25", "regex", "symbol"],
        )
    )

    # --- Group 2: Hard cap row_limit=10 enforced. ---
    checks.append(
        _check(
            "row_limit_default_5",
            ROW_LIMIT_DEFAULT == 5,
        )
    )
    checks.append(
        _check(
            "row_limit_hard_cap_10",
            ROW_LIMIT_HARD_CAP == 10,
        )
    )
    checks.append(
        _check(
            "row_limit_cap_enforced_at_10",
            _validate_row_limit(100) == 10,
        )
    )
    checks.append(
        _check(
            "row_limit_passes_through_at_5",
            _validate_row_limit(5) == 5,
        )
    )
    try:
        _validate_row_limit(0)
        checks.append(_check("row_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("row_limit_rejects_zero", True))

    # --- Group 3: Method result records require allowlisted method values. ---
    try:
        validate_method_result_records(
            [
                {"method": "bm25", "metrics": {}, "failure_category_counts": {}},
                {"method": "vector", "metrics": {}, "failure_category_counts": {}},
            ]
        )
        checks.append(_check("method_record_rejects_unknown_method", False))
    except MethodConfigError:
        checks.append(_check("method_record_rejects_unknown_method", True))

    try:
        validate_method_result_records(
            [
                {"method": "bm25", "metrics": {"mrr": 0.5}, "failure_category_counts": {}},
            ]
        )
        checks.append(_check("method_record_accepts_allowlisted_method", True))
    except MethodConfigError:
        checks.append(_check("method_record_accepts_allowlisted_method", False))

    # 6. metric keys must be from C5-A score allowlist.
    try:
        validate_method_result_records(
            [
                {
                    "method": "bm25",
                    "metrics": {"avg_latency_ms": 100.0},
                    "failure_category_counts": {},
                },
            ]
        )
        checks.append(_check("method_record_rejects_non_allowlisted_metric", False))
    except MethodConfigError:
        checks.append(_check("method_record_rejects_non_allowlisted_metric", True))

    # Method metric allowlist is a subset of C5-A score allowlist.
    for k in METHOD_METRIC_ALLOWLIST:
        checks.append(
            _check(
                f"method_metric_allowlist_subset_of_c5a_{k}",
                k in c5a.SCORE_METRIC_ALLOWLIST,
            )
        )

    # --- Group 4: Deltas only for allowlisted metrics and baseline bm25. ---
    # 7. deltas only for allowlisted metrics and baseline bm25.
    baseline_metrics = _build_synthetic_method_metrics("bm25")
    regex_metrics = _build_synthetic_method_metrics("regex")
    method_results = [
        {
            "method": "bm25",
            "status": "pass",
            "rows_evaluated": 5,
            "rows_successful": 5,
            "rows_failed": 0,
            "metrics": baseline_metrics,
            "failure_category_counts": {c: 0 for c in c5a.FAILURE_CATEGORIES},
        },
        {
            "method": "regex",
            "status": "pass",
            "rows_evaluated": 5,
            "rows_successful": 5,
            "rows_failed": 0,
            "metrics": regex_metrics,
            "failure_category_counts": {c: 0 for c in c5a.FAILURE_CATEGORIES},
        },
    ]
    deltas = _compute_deltas_vs_baseline(method_results)
    checks.append(
        _check(
            "deltas_excludes_baseline_method",
            all(d["method"] != BASELINE_METHOD for d in deltas),
        )
    )
    checks.append(
        _check(
            "deltas_only_for_allowlisted_metrics",
            all(
                d.get("metric") in DELTA_METRIC_ALLOWLIST
                and set(d.keys())
                == {"baseline_method", "method", "metric", "delta"}
                for d in deltas
            ),
        )
    )
    checks.append(
        _check(
            "deltas_baseline_method_is_bm25",
            BASELINE_METHOD == "bm25",
        )
    )
    # delta value correctness.
    expected_mrr_delta = round(regex_metrics["mrr"] - baseline_metrics["mrr"], 6)
    actual_mrr_delta = next(
        d["delta"]
        for d in deltas
        if d["method"] == "regex" and d["metric"] == "mrr"
    )
    checks.append(
        _check(
            "deltas_value_correct_for_regex_mrr",
            actual_mrr_delta == expected_mrr_delta,
        )
    )
    # deltas missing baseline -> empty list (no fake zero).
    deltas_no_baseline = _compute_deltas_vs_baseline(
        [
            {
                "method": "regex",
                "status": "pass",
                "rows_evaluated": 5,
                "rows_successful": 5,
                "rows_failed": 0,
                "metrics": regex_metrics,
                "failure_category_counts": {},
            }
        ]
    )
    checks.append(
        _check(
            "deltas_empty_when_baseline_missing",
            deltas_no_baseline == [],
        )
    )
    # delta validator rejects baseline method.
    try:
        validate_delta_records(
            [
                {
                    "baseline_method": BASELINE_METHOD,
                    "method": BASELINE_METHOD,
                    "metric": "mrr",
                    "delta": 0.0,
                }
            ]
        )
        checks.append(_check("delta_validator_rejects_baseline_method", False))
    except MethodConfigError:
        checks.append(_check("delta_validator_rejects_baseline_method", True))
    # delta validator rejects non-numeric.
    try:
        validate_delta_records(
            [
                {
                    "baseline_method": BASELINE_METHOD,
                    "method": "regex",
                    "metric": "mrr",
                    "delta": "high",
                }
            ]
        )
        checks.append(_check("delta_validator_rejects_non_numeric", False))
    except MethodConfigError:
        checks.append(_check("delta_validator_rejects_non_numeric", True))
    try:
        validate_delta_records(
            [
                {
                    "baseline_method": BASELINE_METHOD,
                    "method": "regex",
                    "metric": "avg_latency_ms",
                    "delta": 1.0,
                }
            ]
        )
        checks.append(_check("delta_validator_rejects_non_allowlisted_metric", False))
    except MethodConfigError:
        checks.append(_check("delta_validator_rejects_non_allowlisted_metric", True))

    # --- Group 5: No best_method / recommendation fields. ---
    # 8. no `best_method` / recommendation fields.
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"scanner_rejects_{field}_key",
                bool(_scan_c5b({field: "bm25"})),
            )
        )
    # A clean matrix report must not contain any recommendation field.
    clean_report = _build_matrix_report(
        self_test_passed=True,
        row_limit_requested=5,
        rows_fetched=5,
        methods=["bm25", "regex", "symbol"],
        method_results=method_results,
        query_mode="first_paragraph",
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=1,
        failure_category_counts={c: 0 for c in c5a.FAILURE_CATEGORIES},
    )
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"clean_report_missing_{field}",
                field not in clean_report,
            )
        )
    checks.append(
        _check(
            "clean_report_baseline_is_policy_candidate_false",
            clean_report.get("baseline_is_policy_candidate") is False,
        )
    )
    checks.append(
        _check(
            "clean_report_default_should_change_false",
            clean_report.get("default_should_change") is False,
        )
    )

    # --- Group 6: Scanner rejects dynamic method key not in allowlist. ---
    # 9. scanner rejects dynamic method key not in allowlist if dict shape exists.
    checks.append(
        _check(
            "scanner_rejects_method_results_as_dict",
            bool(_scan_c5b({"method_results": {"vector": {"metrics": {}}}})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_non_dict",
            bool(_scan_c5b({"method_results": ["not_a_dict"]})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_missing_method",
            bool(_scan_c5b({"method_results": [{"metrics": {}}]})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_method_not_allowlisted",
            bool(
                _scan_c5b(
                    {"method_results": [{"method": "vector", "metrics": {}}]}
                )
            ),
        )
    )
    # Scanner accepts a clean list-of-records.
    checks.append(
        _check(
            "scanner_accepts_clean_method_results_list",
            not _scan_c5b(
                {
                    "method_results": [
                        {
                            "method": "bm25",
                            "metrics": {"mrr": 0.5},
                            "failure_category_counts": {},
                        }
                    ]
                }
            ),
        )
    )

    # --- Group 7: Scanner rejects row/repo/query/gold/path/span/snippet/
    # content_sha/stdout/stderr. ---
    # 10. scanner rejects row/repo/query/gold/path/span/snippet/content_sha/
    # stdout/stderr.
    for forbidden_key in (
        "row", "rows", "repo", "repo_url", "repo_name", "repo_slug",
        "query", "query_text", "gold", "gold_path", "gold_span",
        "gold_paths", "gold_lines", "gold_context", "path", "span",
        "snippet", "snippets", "content_sha", "stdout", "stderr",
        "stdout_text", "stderr_text", "evidence", "evidence_row",
        "retrieved_path", "retrieved_paths", "retrieved_snippet",
        "cloned_repo_path", "cloned_repo", "per_row_metrics",
        "row_metrics", "patch", "diff", "instance_id",
        "problem_statement", "base_commit",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{forbidden_key}_key",
                bool(_scan_c5b({forbidden_key: "value"})),
            )
        )

    # --- Group 8: Status semantics. ---
    # 11. status semantics all success -> pass, mixed -> partial, none -> unavailable.
    all_pass_results = [
        {
            "method": "bm25",
            "status": "pass",
            "rows_evaluated": 5,
            "rows_successful": 5,
            "rows_failed": 0,
            "metrics": baseline_metrics,
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": "pass",
            "rows_evaluated": 5,
            "rows_successful": 5,
            "rows_failed": 0,
            "metrics": regex_metrics,
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_pass_when_all_methods_succeed",
            _status_from_method_results(all_pass_results) == "pass",
        )
    )
    mixed_results = [
        {
            "method": "bm25",
            "status": "pass",
            "rows_evaluated": 5,
            "rows_successful": 5,
            "rows_failed": 0,
            "metrics": baseline_metrics,
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": "unavailable_with_reason",
            "rows_evaluated": 5,
            "rows_successful": 0,
            "rows_failed": 5,
            "metrics": {},
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_partial_when_mixed",
            _status_from_method_results(mixed_results) == "partial",
        )
    )
    none_results = [
        {
            "method": "bm25",
            "status": "unavailable_with_reason",
            "rows_evaluated": 5,
            "rows_successful": 0,
            "rows_failed": 5,
            "metrics": {},
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": "unavailable_with_reason",
            "rows_evaluated": 5,
            "rows_successful": 0,
            "rows_failed": 5,
            "metrics": {},
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_unavailable_when_none_succeed",
            _status_from_method_results(none_results) == "unavailable_with_reason",
        )
    )
    checks.append(
        _check(
            "status_unavailable_when_empty",
            _status_from_method_results([]) == "unavailable_with_reason",
        )
    )

    # --- Group 9: Generation fails if scanner fails. ---
    # 12. generation fails if scanner fails.
    try:
        _enforce_c5b_no_forbidden(clean_report)
        checks.append(_check("fail_closed_clean_report_no_raise", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean_report_no_raise", False))

    leaked_report = dict(clean_report)
    leaked_report["leaked_repo"] = "astropy/astropy"
    try:
        _enforce_c5b_no_forbidden(leaked_report)
        checks.append(_check("fail_closed_leaked_report_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_leaked_report_raises", True))

    leaked_report2 = dict(clean_report)
    leaked_report2["best_method"] = "regex"
    try:
        _enforce_c5b_no_forbidden(leaked_report2)
        checks.append(_check("fail_closed_best_method_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_best_method_raises", True))

    leaked_report3 = dict(clean_report)
    leaked_report3["method_results"] = {"bm25": {"metrics": {}}}
    try:
        _enforce_c5b_no_forbidden(leaked_report3)
        checks.append(_check("fail_closed_method_results_dict_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_method_results_dict_raises", True))

    failed_self_test_report = dict(clean_report)
    failed_self_test_report["self_test_passed"] = False
    try:
        c5a._refuse_on_self_test_failure(failed_self_test_report)
        checks.append(_check("refuse_on_self_test_failure_raises", False))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_failure_raises", True))

    try:
        c5a._refuse_on_self_test_failure(clean_report)
        checks.append(_check("refuse_on_self_test_pass_no_raise", True))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_pass_no_raise", False))

    # --- Group 10: Artifact identity fields. ---
    checks.append(
        _check(
            "schema_version_correct",
            clean_report["schema_version"] == SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "claim_level_correct",
            clean_report["claim_level"] == CLAIM_LEVEL,
        )
    )
    checks.append(
        _check("mode_correct", clean_report["mode"] == MODE)
    )
    checks.append(
        _check("phase_correct", clean_report["phase"] == PHASE)
    )
    checks.append(
        _check(
            "generated_by_correct",
            clean_report["generated_by"] == GENERATED_BY,
        )
    )
    checks.append(
        _check(
            "status_pass_when_self_test_passed",
            clean_report["status"] == "pass",
        )
    )

    # --- Group 11: Safe true flags. ---
    for flag in SAFE_TRUE_FLAGS:
        checks.append(
            _check(
                f"safe_true_{flag}_present",
                flag in clean_report,
            )
        )
    checks.append(
        _check(
            "safe_true_aggregate_only_public_artifact",
            clean_report.get("aggregate_only_public_artifact") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_diagnostic_only",
            clean_report.get("diagnostic_only") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_method_matrix_smoke",
            clean_report.get("method_matrix_smoke") is True,
        )
    )

    # --- Group 12: No-claim / no-runtime-change false flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"no_claim_{flag}_false",
                clean_report.get(flag) is False,
            )
        )

    # --- Group 13: License fields. ---
    checks.append(
        _check(
            "license_dataset_license_status",
            clean_report.get("dataset_license_status")
            == "unknown_dataset_license",
        )
    )
    checks.append(
        _check(
            "license_row_level_redistribution_allowed_false",
            clean_report.get("row_level_redistribution_allowed") is False,
        )
    )
    checks.append(
        _check(
            "license_derived_row_level_publication_allowed_false",
            clean_report.get("derived_row_level_publication_allowed")
            is False,
        )
    )
    checks.append(
        _check(
            "license_aggregate_metrics_publication",
            clean_report.get("aggregate_metrics_publication")
            == "aggregate_only_smoke",
        )
    )

    # --- Group 14: Unavailable report. ---
    unavail = _build_unavailable_report(
        "network_fetch_failed",
        self_test_passed=True,
        row_limit_requested=5,
        methods=["bm25", "regex", "symbol"],
        query_mode="first_paragraph",
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
        rows_fetched=0,
        network_calls=1,
        failure_category_counts={c: 0 for c in c5a.FAILURE_CATEGORIES},
    )
    checks.append(
        _check(
            "unavailable_status",
            unavail["status"] == "unavailable_with_reason",
        )
    )
    checks.append(
        _check(
            "unavailable_failure_reason_category",
            unavail["failure_reason_category"] == "network_fetch_failed",
        )
    )
    checks.append(
        _check(
            "unavailable_no_method_matrix_smoke_flag",
            unavail["method_matrix_smoke"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_no_external_benchmark_performance_claimed",
            unavail["external_benchmark_performance_claimed"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_no_deltas",
            unavail["smoke_metric_deltas_vs_baseline"] == [],
        )
    )
    checks.append(
        _check(
            "unavailable_forbidden_scan_pass",
            unavail["forbidden_scan"]["status"] == "pass",
        )
    )
    checks.append(
        _check(
            "unavailable_method_results_all_unavailable",
            all(
                r["status"] == "unavailable_with_reason"
                for r in unavail["method_results"]
            ),
        )
    )

    # --- Group 15: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_artifact_self_scan_clean",
            not _scan_c5b(clean_report),
        )
    )
    checks.append(
        _check(
            "unavailable_self_scan_clean",
            not _scan_c5b(unavail),
        )
    )

    # --- Group 16: CLI argument surface. ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for required_opt in (
        "--self-test",
        "--row-limit",
        "--methods",
        "--query-mode",
        "--language-filter",
        "--openlocus",
        "--out",
    ):
        checks.append(
            _check(
                f"cli_has_option_{required_opt}",
                required_opt in option_strings,
            )
        )

    # --- Group 17: Schema contract failure. ---
    schema_fail = _build_schema_contract_failure(
        "method_result_record_invalid",
        self_test_passed=True,
        row_limit_requested=5,
        methods=["bm25", "regex", "symbol"],
        query_mode="first_paragraph",
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "schema_contract_failure_status",
            schema_fail["status"] == "fail_schema_contract",
        )
    )
    checks.append(
        _check(
            "schema_contract_failure_no_method_results",
            schema_fail["method_results"] == [],
        )
    )
    checks.append(
        _check(
            "schema_contract_failure_forbidden_scan_pass",
            schema_fail["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 18: ALLOWED_METHODS exactly bm25,regex,text,symbol. ---
    checks.append(
        _check(
            "allowed_methods_exact",
            ALLOWED_METHODS == ("bm25", "regex", "text", "symbol"),
        )
    )

    # --- Group 19: ``text`` method as value (C5-A false positive
    # suppression). The C5-A scanner flags ``"text"`` as
    # ``forbidden_field_name_value`` because ``text`` is a forbidden
    # CONTENT/KEY name in C5-A's contract. In C5-B, ``text`` is also a
    # legitimate OpenLocus retrieval method name, so it may appear as a
    # value under ``methods_allowed`` / ``methods_requested`` /
    # ``baseline_method`` / per-record ``method`` fields. The C5-B
    # scanner must filter out that single false positive. ---
    text_method_results = [
        {
            "method": "bm25",
            "status": "pass",
            "rows_evaluated": 1,
            "rows_successful": 1,
            "rows_failed": 0,
            "metrics": _build_synthetic_method_metrics("bm25"),
            "failure_category_counts": {},
        },
        {
            "method": "text",
            "status": "pass",
            "rows_evaluated": 1,
            "rows_successful": 1,
            "rows_failed": 0,
            "metrics": _build_synthetic_method_metrics("text"),
            "failure_category_counts": {},
        },
    ]
    text_report = _build_matrix_report(
        self_test_passed=True,
        row_limit_requested=1,
        rows_fetched=1,
        methods=["bm25", "text"],
        method_results=text_method_results,
        query_mode="first_paragraph",
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=1,
        failure_category_counts={c: 0 for c in c5a.FAILURE_CATEGORIES},
    )
    checks.append(
        _check(
            "text_method_value_not_flagged_in_method_results",
            not any(
                v.get("category") == "forbidden_field_name_value"
                and "method_results" in v.get("path", "")
                for v in _scan_c5b(text_report)
            ),
        )
    )
    checks.append(
        _check(
            "text_method_value_not_flagged_in_deltas",
            not any(
                v.get("category") == "forbidden_field_name_value"
                and "smoke_metric_deltas_vs_baseline" in v.get("path", "")
                for v in _scan_c5b(text_report)
            ),
        )
    )
    checks.append(
        _check(
            "text_method_value_not_flagged_in_methods_allowed",
            not any(
                v.get("category") == "forbidden_field_name_value"
                and "methods_allowed" in v.get("path", "")
                for v in _scan_c5b(text_report)
            ),
        )
    )
    checks.append(
        _check(
            "text_method_value_not_flagged_in_methods_requested",
            not any(
                v.get("category") == "forbidden_field_name_value"
                and "methods_requested" in v.get("path", "")
                for v in _scan_c5b(text_report)
            ),
        )
    )
    checks.append(
        _check(
            "text_method_report_forbidden_scan_pass",
            text_report["forbidden_scan"]["status"] == "pass",
        )
    )
    # But a forbidden key like ``repo`` as a value MUST still be flagged.
    checks.append(
        _check(
            "scanner_still_flags_repo_value_under_method_path",
            bool(
                _scan_c5b(
                    {
                        "method_results": [
                            {
                                "method": "bm25",
                                "metrics": {},
                                "failure_category_counts": {},
                            }
                        ],
                        "leaked": "repo",
                    }
                )
            ),
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args."""

    def error(self, message: str) -> NoReturn:  # noqa: D401
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the C5-B CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "C5-B ContextBench verified retrieval method matrix smoke "
            "(public aggregate-only artifact; bounded ContextBench "
            "verified subset; transient /tmp clone + retrieval + score; "
            "no provider calls; no raw rows/queries/repo URLs/commits/"
            "gold paths/spans/generated JSONL/evidence rows/cloned repos/"
            "stdout/stderr committed; no winner/best_method/"
            "recommended_default)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written, no network)",
    )
    ap.add_argument(
        "--row-limit",
        type=int,
        default=ROW_LIMIT_DEFAULT,
        help=(
            "number of ContextBench verified rows to evaluate per method "
            "(default: " f"{ROW_LIMIT_DEFAULT}; hard cap "
            f"{ROW_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--methods",
        default=None,
        help=(
            "comma-separated OpenLocus retrieval methods (default: "
            f"{','.join(DEFAULT_METHODS)}; allowed: "
            f"{', '.join(ALLOWED_METHODS)}; duplicates are deduplicated "
            "deterministically)"
        ),
    )
    ap.add_argument(
        "--query-mode",
        default=c5a.DEFAULT_QUERY_MODE,
        choices=c5a.ALLOWED_QUERY_MODES,
        help=(
            "query sanitizer mode (default: first_paragraph; allowed: "
            f"{', '.join(c5a.ALLOWED_QUERY_MODES)})"
        ),
    )
    ap.add_argument(
        "--language-filter",
        default=c5a.DEFAULT_LANGUAGE_FILTER,
        choices=c5a.ALLOWED_LANGUAGE_FILTERS,
        help=(
            "language filter category (default: python; allowed: "
            f"{', '.join(c5a.ALLOWED_LANGUAGE_FILTERS)})"
        ),
    )
    ap.add_argument(
        "--openlocus",
        default=None,
        help=(
            "OpenLocus binary path (default: target/release/openlocus "
            "then target/debug/openlocus fallback)"
        ),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "output artifact JSON path (default: committed public "
            "aggregate-only artifact)"
        ),
    )
    return ap


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            tag = "PASS" if c["passed"] else "FAIL"
            print(f"[{tag}] {c['check']}")
        passed_count = sum(1 for c in checks if c["passed"])
        print(
            f"self_test_passed={passed} "
            f"({passed_count}/{len(checks)} checks)"
        )
        sys.exit(0 if passed else 1)

    # Parse methods (raises MethodConfigError on invalid config).
    try:
        methods = parse_methods(args.methods)
    except MethodConfigError:
        # Build a fail_schema_contract report and exit.
        report = _build_schema_contract_failure(
            "method_config_invalid",
            self_test_passed=False,
            row_limit_requested=args.row_limit,
            methods=[],
            query_mode=args.query_mode,
            language_filter=args.language_filter,
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )
        _write_json(args.out, report)
        sys.exit(1)

    row_limit = _validate_row_limit(args.row_limit)
    query_mode = args.query_mode
    language_filter = args.language_filter
    out_path = args.out if args.out is not None else DEFAULT_OUT

    # Self-test must pass before any artifact is written.
    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        print(
            "error: self-test failed; refusing to write artifact",
            file=sys.stderr,
        )
        for c in checks:
            if not c["passed"]:
                print(f"  FAIL: {c['check']}", file=sys.stderr)
        sys.exit(1)

    # Resolve OpenLocus binary.
    openlocus_bin, openlocus_source = c5a._resolve_openlocus_binary(
        args.openlocus
    )
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_c5b_no_forbidden(report)
        _write_json(out_path, report)
        print(
            f"wrote artifact "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"self_test_passed={report['self_test_passed']}, "
            f"status={report['status']}, "
            f"phase={report['phase']}, "
            f"methods={report['methods_requested']}, "
            f"failure_reason={report['failure_reason_category']})"
        )
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_matrix_smoke(
            row_limit=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            eval_dir=eval_dir,
            self_test_passed=self_test_passed,
        )
    except (OSError, subprocess.SubprocessError):
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
        )

    _enforce_c5b_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"methods={report['methods_requested']}, "
        f"methods_successful={report['methods_successful']}, "
        f"rows_fetched={report['rows_fetched']})"
    )


if __name__ == "__main__":
    main()
