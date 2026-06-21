#!/usr/bin/env python3
"""C5-E RepoQA Method-Matrix Retrieval Smoke (Public Aggregate-Only).

This module implements the **C5-E RepoQA bounded retrieval method-matrix
smoke** over the EvalPlus RepoQA/SNF release asset
(``repoqa-2024-06-23.json.gz`` from ``evalplus/repoqa_release``). It
extends C5-D (single-method RepoQA `bm25` smoke) into a bounded
multi-method matrix smoke over `bm25,regex,symbol`.

C5-E is explicitly **not** a benchmark result, **not** a leaderboard
entry, **not** a performance claim, **not** a promotion, **not** a
default/policy change, and **not** a runtime/retriever/pack/backend/
EvidenceCore semantic change. The committed artifact records only
per-method aggregate retrieval metrics (records, NOT dynamic method-key
dicts) plus aggregate-only deltas vs the fixed `bm25` baseline,
computed by `eval/score.py` over a bounded RepoQA Python needle subset.

Claim boundary (binding):

* Claim level: `repoqa_retrieval_method_matrix_smoke_only`.
* Status: `repoqa_method_matrix_smoke_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan` |
  `fail_schema_contract`.
* Mode: `repoqa_bounded_method_matrix_smoke`; phase `C5-E`.
* This is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime/retriever/pack/backend change, NOT an
  EvidenceCore semantic change, and NOT a downstream agent value claim.
* It does NOT emit `winner`, `best_method`, `recommended_default`, or
  anything implying a policy/default decision. The fixed
  `baseline_method` is `bm25` and `baseline_is_policy_candidate` is
  always `false`.

Privacy / license boundary (binding):

* The `repoqa-2024-06-23.json.gz` release asset is downloaded to
  in-memory bytes (transient; NEVER written to workspace or committed)
  and decompressed in memory.
* Raw repo records, repo names/URLs, commit SHAs, entrypoint paths,
  topics, content, dependency, needle names/descriptions/paths/start/
  end lines, generated task/label/run JSONL, evidence rows, cloned
  repos, and stdout/stderr are kept **transient only** under `/tmp` or
  CI ephemeral workspace. They are NEVER committed or uploaded.
* Aggregate metric values from `eval/score.py` are safe to publish if
  aggregate only.
* RepoQA dataset license is unknown
  (`unknown_dataset_license`); row-level redistribution is disabled
  and derived row-level publication is disabled. Aggregate metrics
  publication is allowed as aggregate-only smoke
  (`aggregate_metrics_publication=aggregate_only_smoke`).

Network / CI policy (binding):

* Default no-network self-test passes without GitHub/network.
* Real smoke requires public network access to GitHub (asset download +
  repo clones). CI must be a separate explicit `workflow_dispatch`
  job with `enable_external_benchmark_network=true`. It must NOT run on
  PR/push by default, must use no provider secrets/vars, no
  provider model env, and must upload only the
  aggregate report.

Run::

    python3 -m py_compile eval/c5e_repoqa_method_matrix_smoke.py
    python3 eval/c5e_repoqa_method_matrix_smoke.py --self-test
    python3 eval/c5e_repoqa_method_matrix_smoke.py \\
        --needle-limit 5 --language-filter python --methods bm25,regex,symbol \\
        --out artifacts/c5e_repoqa_method_matrix_smoke/\\
c5e_repoqa_method_matrix_smoke_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful `unavailable_with_reason` with a real failure
category (no stale/fake pass). Self-test/docs/diff-check still pass.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NoReturn

# Reuse C5-D helpers (asset download, gzip parse, needle extraction,
# transient repo clone/checkout, score task/label/run generation,
# scanner/failure categories). The ``eval`` directory has no
# ``__init__.py`` (it is a flat script directory), so we add this file's
# parent to ``sys.path`` and import the C5-D module directly. C5-E
# does NOT mutate C5-D; it only reuses its primitives.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (C5-E owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "c5e_repoqa_method_matrix_smoke.v1"
GENERATED_BY = "eval/c5e_repoqa_method_matrix_smoke.py"
CLAIM_LEVEL = "repoqa_retrieval_method_matrix_smoke_only"
MODE = "repoqa_bounded_method_matrix_smoke"
PHASE = "C5-E"

# C5-E pass status enum is a distinct string (NOT the generic "pass")
# to make the method-matrix smoke contract explicit in the public artifact.
STATUS_PASS = "repoqa_method_matrix_smoke_pass"
STATUS_PARTIAL = "partial"
STATUS_UNAVAILABLE = "unavailable_with_reason"
STATUS_FAIL_FORBIDDEN_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA_CONTRACT = "fail_schema_contract"

DEFAULT_OUT = Path(
    "artifacts/c5e_repoqa_method_matrix_smoke/"
    "c5e_repoqa_method_matrix_smoke_report.json"
)

# Hard caps on needle limit. Default 5; max 10 (reuse C5-D caps).
NEEDLE_LIMIT_DEFAULT = c5d.NEEDLE_LIMIT_DEFAULT  # 5
NEEDLE_LIMIT_HARD_CAP = c5d.NEEDLE_LIMIT_HARD_CAP  # 10

# Methods supported by C5-E: bm25, regex, symbol only (mirrors C5-C;
# `text` is NOT allowed).
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
BASELINE_METHOD = "bm25"

# Language filter: python only (reuse C5-D).
ALLOWED_LANGUAGE_FILTERS = c5d.ALLOWED_LANGUAGE_FILTERS
DEFAULT_LANGUAGE_FILTER = c5d.DEFAULT_LANGUAGE_FILTER

# Query mode and gold target mode reuse C5-D.
QUERY_MODE = c5d.QUERY_MODE
GOLD_TARGET_MODE = c5d.GOLD_TARGET_MODE

# RepoQA release identifiers (reuse C5-D).
BENCHMARK = c5d.BENCHMARK
DATASET_RELEASE = c5d.DATASET_RELEASE

# Delta metric allowlist: smoke deltas are computed only for these
# aggregate metric names, and only as method vs `baseline_method`.
DELTA_METRIC_ALLOWLIST: tuple[str, ...] = c5d.SCORE_METRIC_ALLOWLIST

# Per-method metric allowlist: only these metric keys may appear in a
# method result record's `metrics` block.
METHOD_METRIC_ALLOWLIST: tuple[str, ...] = DELTA_METRIC_ALLOWLIST

# Recommendation / policy field names that must NEVER be emitted by C5-E
# (anywhere in the public artifact).
FORBIDDEN_RECOMMENDATION_FIELDS: frozenset[str] = (
    c5d.FORBIDDEN_RECOMMENDATION_FIELDS
)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be true
# in the committed public artifact. C5-E uses
# `repoqa_method_matrix_smoke_performed` instead of C5-D's
# `repoqa_retrieval_smoke_performed` to reflect the method-matrix contract.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "repoqa_method_matrix_smoke_performed": False,
    "asset_downloaded_transiently": False,
    "repoqa_needles_parsed_in_memory": False,
    "repositories_materialized_transiently": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). C5-E adds `baseline_is_policy_candidate=false`
# (like C5-B/C5-C).
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

# License / redistribution fields (fixed; reuse C5-D).
LICENSE_FIELDS: dict[str, Any] = dict(c5d.LICENSE_FIELDS)

# Failure categories reuse C5-D enum.
FAILURE_CATEGORIES = c5d.FAILURE_CATEGORIES

# ---------------------------------------------------------------------------
# Method parser / validator (C5-E owned; mirrors C5-C but with C5-E
# status enums and C5-D failure categories).
# ---------------------------------------------------------------------------


class MethodConfigError(ValueError):
    """Raised when the requested methods config violates the C5-E contract."""


def parse_methods(methods_arg: str | None) -> list[str]:
    """Parse a comma-separated `--methods` argument into a method list.

    Rules (C5-E owned):

    * Empty / None -> default `["bm25", "regex", "symbol"]`.
    * Each token must be in `ALLOWED_METHODS` (bm25, regex, symbol only;
      `text` is NOT allowed); unknown methods raise `MethodConfigError`.
    * Duplicate tokens are deduplicated deterministically (preserving
      first-seen order).
    * Empty tokens (e.g. from `"bm25,,regex"`) are skipped silently.
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
            continue
        seen.add(tok)
        methods.append(tok)

    if not methods:
        raise MethodConfigError("no methods provided after dedup")
    return methods


def validate_method_result_records(
    records: list[dict[str, Any]],
) -> None:
    """Validate method result records against the C5-E contract.

    * `method` must be in `ALLOWED_METHODS` (bm25, regex, symbol).
    * `metrics` keys must be in `METHOD_METRIC_ALLOWLIST`.
    * No recommendation / policy field may appear.
    * Records must be a list of dicts (not a dict keyed by method name).
    * `aggregate_runtime_seconds` if present must be numeric (or null).
    """
    if not isinstance(records, list):
        raise MethodConfigError(
            "method_results must be a list of records, not a dict"
        )
    allowed_record_keys = {
        "method",
        "status",
        "needles_evaluated",
        "needles_successful",
        "needles_failed",
        "metrics",
        "failure_category_counts",
        "aggregate_runtime_seconds",
    }
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
        unexpected_keys = set(rec.keys()) - allowed_record_keys
        if unexpected_keys:
            raise MethodConfigError(
                f"method result record has unexpected keys: "
                f"{sorted(unexpected_keys)!r} (method={method!r})"
            )
        for k in rec.keys():
            if k in FORBIDDEN_RECOMMENDATION_FIELDS:
                raise MethodConfigError(
                    f"method result record must not include "
                    f"recommendation field: {k!r}"
                )
        if "aggregate_runtime_seconds" in rec:
            val = rec.get("aggregate_runtime_seconds")
            if val is not None and not isinstance(val, (int, float)):
                raise MethodConfigError(
                    f"aggregate_runtime_seconds must be numeric or null "
                    f"(method={method!r})"
                )


def validate_delta_records(
    deltas: list[dict[str, Any]],
) -> None:
    """Validate delta records against the C5-E contract.

    * Each delta record must have `baseline_method` exactly equal to
      `BASELINE_METHOD`.
    * Each delta record must have `method` in `ALLOWED_METHODS` and
      not equal to `BASELINE_METHOD`.
    * Each delta record must name exactly one `metric` from
      `DELTA_METRIC_ALLOWLIST` and one numeric `delta` value.
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
# Public artifact scanner (C5-E owned, strict, fail-closed).
#
# C5-E reuses the C5-D forbidden scanner primitives for raw key/value
# leak detection, and ADDS a C5-E-specific scanner that:
#   * rejects dynamic method-key dicts (i.e. a `method_results` value
#     that is a dict keyed by method name, instead of a list of records);
#   * rejects the FORBIDDEN_RECOMMENDATION_FIELDS keys anywhere;
#   * rejects row/repo/query/gold/path/span/snippet/content_sha/stdout/
#     stderr keys anywhere (inherited from C5-D).
# ---------------------------------------------------------------------------


# C5-E schema-key container keys (children are fixed labels, not row
# values). Extends C5-D's set with the C5-E-specific containers.
C5E_SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "failure_category_counts",
        "metrics",
        "smoke_metric_deltas_vs_baseline",
    }
)


# C5-E-specific safe VALUE path last-key segments. In C5-E, method names
# are only bm25/regex/symbol; none of these is a forbidden content/key
# name in C5-A, so no false-positive suppression is strictly needed,
# but the filter is kept for symmetry and future-proofing.
C5E_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
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
        "benchmark",
        "dataset_release",
        "language_filter",
        "query_mode",
        "gold_target_mode",
        "network_mode",
        "openlocus_binary_source",
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
        "failure_reason_category",
        "dataset_license_status",
        "aggregate_metrics_publication",
    }
)


def _is_c5e_schema_key_container(path: str) -> bool:
    """Check if the parent of the current key is a C5-E schema-key container."""
    parts = path.rsplit(".", 1)
    if len(parts) < 2:
        return False
    parent_key = parts[0].rsplit(".", 1)[-1]
    parent_key = parent_key.split("[")[0]
    return parent_key in C5E_SCHEMA_KEY_CONTAINER_KEYS


def _c5e_safe_value_path(path: str) -> bool:
    """Check if a JSON path is a C5-E-specific safe value path."""
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in C5E_SAFE_VALUE_PATH_LAST_KEYS


def _scan_c5e_method_results_shape(obj: Any) -> list[dict[str, Any]]:
    """Reject `method_results` if it is a dict keyed by method name.

    C5-E requires `method_results` to be a list of records, NOT a dict
    keyed by method name. A dict shape would leak method names as
    dynamic dict keys. This scanner enforces the list-of-records shape.
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
    return violations


def _scan_c5e(obj: Any) -> list[dict[str, Any]]:
    """Combined C5-E scanner: C5-D primitives + C5-E-specific checks.

    The C5-D scanner is reused for raw key/value leak detection (URLs,
    hex digests, repo slugs, /tmp paths, RepoQA-specific forbidden keys,
    recommendation fields, etc.). C5-E ADDS:
      * rejection of `method_results` as a dict keyed by method name;
      * C5-E-specific safe value path filtering (for method/metric
        names under list-of-records containers).
    """
    violations: list[dict[str, Any]] = []
    for v in c5d._scan_c5d(obj):
        # Suppress C5-D false positives where a legitimate method name
        # or metric name appears as a value under a C5-E-specific safe
        # value path.
        if v.get("category") == "forbidden_field_name_value" and _c5e_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    violations.extend(_scan_c5e_method_results_shape(obj))
    return violations


def _c5e_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the C5-E forbidden scanner and return a sanitized summary."""
    violations = _scan_c5e(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_c5e_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _c5e_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return c5d._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    c5d._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5d._check(name, ok)


def _validate_needle_limit(needle_limit: int) -> int:
    """Validate and cap --needle-limit to the C5-E hard cap (10)."""
    return c5d._validate_needle_limit(needle_limit)


# ---------------------------------------------------------------------------
# Method result aggregation
# ---------------------------------------------------------------------------


def _filter_method_metrics(
    metrics: dict[str, Any]
) -> dict[str, Any]:
    """Filter score.py metrics to the C5-E method-metric allowlist only."""
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
    per_needle_metrics: list[dict[str, Any]],
    needles_successful: int,
) -> dict[str, Any]:
    """Compute aggregate method metrics from per-needle score.py outputs.

    Reuses C5-D `_compute_aggregate_metrics` logic (mean of each
    allowlisted numeric metric; `success_rate` recomputed as
    `needles_successful / needles_evaluated`).
    """
    return c5d._compute_aggregate_metrics(
        per_needle_metrics, needles_successful
    )


def _compute_deltas_vs_baseline(
    method_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute aggregate deltas vs the fixed `baseline_method`.

    Only `DELTA_METRIC_ALLOWLIST` keys are emitted. The baseline method
    itself is excluded from the deltas list. If the baseline method is
    missing or has no metrics, no deltas are emitted (empty list, NOT
    a fake zero).
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
    """Compute the overall C5-E status from method result records.

    Semantics:

    * `repoqa_method_matrix_smoke_pass`: all requested methods have at
      least one successful evaluated needle and the scanner passes.
    * `partial`: at least one method succeeds and at least one method
      fails/unavailable.
    * `unavailable_with_reason`: no method completes retrieval+scoring.
    """
    if not method_results:
        return STATUS_UNAVAILABLE
    success_count = sum(
        1
        for r in method_results
        if r.get("status") == STATUS_PASS
        and r.get("needles_successful", 0) > 0
    )
    fail_count = sum(
        1
        for r in method_results
        if r.get("status") != STATUS_PASS
        or r.get("needles_successful", 0) == 0
    )
    if success_count == 0:
        return STATUS_UNAVAILABLE
    if fail_count == 0:
        return STATUS_PASS
    return STATUS_PARTIAL


# ---------------------------------------------------------------------------
# Public report builders (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_method_result_record(
    *,
    method: str,
    status: str,
    needles_evaluated: int,
    needles_successful: int,
    needles_failed: int,
    metrics: dict[str, Any],
    failure_category_counts: dict[str, int],
    aggregate_runtime_seconds: float | None = None,
) -> dict[str, Any]:
    """Build a single method result record (list element, NOT a dict key)."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)
    rec: dict[str, Any] = {
        "method": method,
        "status": status,
        "needles_evaluated": int(needles_evaluated),
        "needles_successful": int(needles_successful),
        "needles_failed": int(needles_failed),
        "metrics": _filter_method_metrics(metrics),
        "failure_category_counts": fcc,
    }
    if aggregate_runtime_seconds is not None:
        rec["aggregate_runtime_seconds"] = round(
            float(aggregate_runtime_seconds), 3
        )
    return rec


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    methods: list[str],
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    needles_seen: int = 0,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a truthful `unavailable_with_reason` report."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)
    if failure_reason_category in fcc:
        fcc[failure_reason_category] = max(fcc[failure_reason_category], 1)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["asset_downloaded_transiently"] = needles_seen > 0
    safe_true["repoqa_needles_parsed_in_memory"] = needles_seen > 0

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": STATUS_UNAVAILABLE,
        "mode": MODE,
        "phase": PHASE,
        "benchmark": BENCHMARK,
        "dataset_release": DATASET_RELEASE,
        "methods_requested": list(methods),
        "methods_allowed": list(ALLOWED_METHODS),
        "baseline_method": BASELINE_METHOD,
        "language_filter": language_filter,
        "query_mode": QUERY_MODE,
        "gold_target_mode": GOLD_TARGET_MODE,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "needle_limit_requested": needle_limit_requested,
        "needles_seen": needles_seen,
        "methods_count": len(methods),
        "methods_attempted": len(methods),
        "methods_successful": 0,
        "methods_succeeded": 0,
        "methods_failed": len(methods),
        "method_results": [
            {
                "method": m,
                "status": STATUS_UNAVAILABLE,
                "needles_evaluated": 0,
                "needles_successful": 0,
                "needles_failed": 0,
                "metrics": {},
                "failure_category_counts": {c: 0 for c in FAILURE_CATEGORIES},
            }
            for m in methods
        ],
        "smoke_metric_deltas_vs_baseline": [],
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_counts": fcc,
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "signal_strength": "repoqa_method_matrix_smoke_unavailable",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _c5e_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


def _build_schema_contract_failure(
    reason: str,
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    methods: list[str],
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a `fail_schema_contract` report (invalid method config / shape)."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
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
        "status": STATUS_FAIL_SCHEMA_CONTRACT,
        "mode": MODE,
        "phase": PHASE,
        "benchmark": BENCHMARK,
        "dataset_release": DATASET_RELEASE,
        "methods_requested": list(methods),
        "methods_allowed": list(ALLOWED_METHODS),
        "baseline_method": BASELINE_METHOD,
        "language_filter": language_filter,
        "query_mode": QUERY_MODE,
        "gold_target_mode": GOLD_TARGET_MODE,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "needle_limit_requested": needle_limit_requested,
        "needles_seen": 0,
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
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "signal_strength": "repoqa_method_matrix_smoke_schema_contract_failure",
            "is_full_external_benchmark_evaluation": False,
        },
    }
    scan = _c5e_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    return report


def _build_matrix_report(
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    needles_seen: int,
    methods: list[str],
    method_results: list[dict[str, Any]],
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a pass/partial matrix report with aggregate method metrics + deltas."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    # Validate records (contract: fail_schema_contract on invalid shape).
    try:
        validate_method_result_records(method_results)
    except MethodConfigError:
        return _build_schema_contract_failure(
            "method_result_record_invalid",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit_requested,
            methods=methods,
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
            needle_limit_requested=needle_limit_requested,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            failure_category_counts=fcc,
        )

    methods_successful = sum(
        1
        for r in method_results
        if r.get("status") == STATUS_PASS
        and r.get("needles_successful", 0) > 0
    )
    methods_failed = len(method_results) - methods_successful

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["repoqa_method_matrix_smoke_performed"] = methods_successful > 0
    safe_true["asset_downloaded_transiently"] = True
    safe_true["repoqa_needles_parsed_in_memory"] = needles_seen > 0
    safe_true["repositories_materialized_transiently"] = methods_successful > 0
    safe_true["openlocus_retrieval_executed"] = methods_successful > 0
    safe_true["score_py_metrics_computed"] = any(
        r.get("metrics") for r in method_results
    )

    status = _status_from_method_results(method_results)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "benchmark": BENCHMARK,
        "dataset_release": DATASET_RELEASE,
        "methods_requested": list(methods),
        "methods_allowed": list(ALLOWED_METHODS),
        "baseline_method": BASELINE_METHOD,
        "language_filter": language_filter,
        "query_mode": QUERY_MODE,
        "gold_target_mode": GOLD_TARGET_MODE,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "needle_limit_requested": needle_limit_requested,
        "needles_seen": needles_seen,
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
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "signal_strength": "repoqa_method_matrix_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _c5e_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


# ---------------------------------------------------------------------------
# Matrix network smoke runner (transient /tmp workspace; aggregate-only).
# ---------------------------------------------------------------------------


def _run_single_method(
    *,
    method: str,
    needles: list[dict[str, Any]],
    needle_limit: int,
    language_filter: str,
    openlocus_bin: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run retrieval + scoring for a single method across all needles.

    Reuses C5-D primitives:
    * `c5d._sanitize_needle_description`
    * `c5d._clone_and_checkout`
    * `c5d._write_transient_jsonl`
    * `c5d._run_retrieval_and_score` (C5-E wrapper that remaps C5-D
      failure categories and uses C5-E `_run_retrieval_and_score`).
    """
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    needles_evaluated = 0
    needles_successful = 0
    needles_failed = 0
    per_needle_metrics: list[dict[str, Any]] = []
    method_start_time = time.perf_counter()

    with tempfile.TemporaryDirectory(
        prefix=f"c5e_method_{method}_"
    ) as work_root_str:
        work_root = Path(work_root_str)
        tasks_jsonl = work_root / "tasks.jsonl"
        labels_jsonl = work_root / "labels.jsonl"
        run_jsonl = work_root / "run.jsonl"

        for idx, needle in enumerate(needles):
            needles_evaluated += 1
            query = c5d._sanitize_needle_description(
                needle.get("needle_description", "")
            )
            if not query:
                fcc["needle_parse_failed"] += 1
                needles_failed += 1
                continue

            repo_url = needle.get("repo_url", "")
            commit_sha = needle.get("commit_sha", "")
            needle_path = needle.get("needle_path", "")
            start_line = needle.get("needle_start_line", 0)
            end_line = needle.get("needle_end_line", 0)
            if (
                not isinstance(repo_url, str)
                or not isinstance(commit_sha, str)
                or not isinstance(needle_path, str)
                or not repo_url
                or not commit_sha
                or not needle_path
            ):
                fcc["needle_parse_failed"] += 1
                needles_failed += 1
                continue

            with tempfile.TemporaryDirectory(
                prefix=f"c5e_repo_{method}_{idx}_"
            ) as repo_root_str:
                repo_work_dir = Path(repo_root_str)
                clone_ok, clone_fail_cat, clone_fcc = (
                    c5d._clone_and_checkout(
                        repo_url, commit_sha, repo_work_dir
                    )
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    needles_failed += 1
                    continue

                repo_root = repo_work_dir / "repo"

                task_id = f"needle_{idx}"
                task_record = {
                    "task_id": task_id,
                    "query": query,
                    "method": method,
                }
                label_record = {
                    "task_id": task_id,
                    "gold_paths": [needle_path],
                    "gold_lines": [[start_line, end_line]],
                }
                try:
                    c5d._write_transient_jsonl(
                        tasks_jsonl, [task_record]
                    )
                    c5d._write_transient_jsonl(
                        labels_jsonl, [label_record]
                    )
                except OSError:
                    fcc["task_jsonl_write_failed"] += 1
                    needles_failed += 1
                    continue

                metrics, score_fail_cat, score_fcc = (
                    c5d._run_retrieval_and_score(
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
                    needles_failed += 1
                    continue

                per_needle_metrics.append(metrics)
                needles_successful += 1

            try:
                run_jsonl.unlink()
            except OSError:
                pass

    aggregate_runtime_seconds = time.perf_counter() - method_start_time
    method_metrics = _compute_method_metrics(
        per_needle_metrics, needles_successful
    )
    method_status = (
        STATUS_PASS
        if needles_successful > 0 and method_metrics
        else STATUS_UNAVAILABLE
    )
    if needles_successful > 0 and needles_failed > 0:
        method_status = STATUS_PARTIAL

    return _build_method_result_record(
        method=method,
        status=method_status,
        needles_evaluated=needles_evaluated,
        needles_successful=needles_successful,
        needles_failed=needles_failed,
        metrics=method_metrics,
        failure_category_counts=fcc,
        aggregate_runtime_seconds=aggregate_runtime_seconds,
    )


def _run_matrix_smoke(
    *,
    needle_limit: int,
    methods: list[str],
    language_filter: str,
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
) -> dict[str, Any]:
    """Run the real RepoQA matrix network smoke (transient /tmp; aggregate-only)."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0

    # Step 1: download the release asset to in-memory bytes (transient).
    asset_bytes, dl_status, dl_fcc = c5d._download_asset_to_bytes(
        c5d.ASSET_URL
    )
    network_calls += 1
    for k, v in dl_fcc.items():
        if k in fcc:
            fcc[k] += v
    if dl_status != "pass" or asset_bytes is None:
        return _build_unavailable_report(
            "asset_download_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    # Step 2: decompress + parse in memory (transient).
    parsed, parse_status, parse_fcc = c5d._decompress_asset(asset_bytes)
    del asset_bytes
    for k, v in parse_fcc.items():
        if k in fcc:
            fcc[k] += v
    if parse_status != "pass" or parsed is None:
        return _build_unavailable_report(
            "asset_parse_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    # Step 3: parse needles in memory (transient).
    needles, needle_status, needle_fcc = c5d._parse_repoqa_needles(
        parsed, language_filter, needle_limit
    )
    del parsed
    for k, v in needle_fcc.items():
        if k in fcc:
            fcc[k] += v
    if needle_status != "pass" or not needles:
        return _build_unavailable_report(
            "no_python_needles" if needle_status == "unavailable_no_python_needles" else "needle_parse_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            needles_seen=len(needles),
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    needles_seen = len(needles)

    # Step 4: for each method, run retrieval + scoring across all needles.
    method_results: list[dict[str, Any]] = []
    for method in methods:
        method_result = _run_single_method(
            method=method,
            needles=needles,
            needle_limit=needle_limit,
            language_filter=language_filter,
            openlocus_bin=openlocus_bin,
            eval_dir=eval_dir,
        )
        for k, v in method_result.get("failure_category_counts", {}).items():
            if k in fcc:
                fcc[k] += v
        method_results.append(method_result)

    # Step 5: if no method succeeded at all, return unavailable.
    any_success = any(
        r.get("needles_successful", 0) > 0 for r in method_results
    )
    if not any_success:
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            needles_seen=needles_seen,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    return _build_matrix_report(
        self_test_passed=self_test_passed,
        needle_limit_requested=needle_limit,
        needles_seen=needles_seen,
        methods=methods,
        method_results=method_results,
        language_filter=language_filter,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
        failure_category_counts=fcc,
    )


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic data).
# ---------------------------------------------------------------------------


def _build_synthetic_method_metrics(
    method: str = "bm25",
) -> dict[str, Any]:
    """Build synthetic per-method metrics for self-test (aggregate only)."""
    base = {
        "file_recall@10": 0.6,
        "mrr": 0.46,
        "span_f0.5@10": 0.041634,
        "success_rate": 1.0,
    }
    if method == "regex":
        base = {
            "file_recall@10": 0.0,
            "mrr": 0.0,
            "span_f0.5@10": 0.0,
            "success_rate": 1.0,
        }
    elif method == "symbol":
        base = {
            "file_recall@10": 0.0,
            "mrr": 0.0,
            "span_f0.5@10": 0.0,
            "success_rate": 1.0,
        }
    return dict(base)


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all C5-E self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Method parser. ---
    # rejects unknown methods.
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

    # deduplicates duplicates deterministically.
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

    # default methods exactly bm25,regex,symbol.
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

    # C5-E does NOT allow text method.
    try:
        parse_methods("bm25,text,symbol")
        checks.append(_check("method_parser_rejects_text_method", False))
    except MethodConfigError:
        checks.append(_check("method_parser_rejects_text_method", True))

    # --- Group 2: Needle limit hard cap 10. ---
    checks.append(
        _check("needle_limit_default_5", NEEDLE_LIMIT_DEFAULT == 5)
    )
    checks.append(
        _check("needle_limit_hard_cap_10", NEEDLE_LIMIT_HARD_CAP == 10)
    )
    checks.append(
        _check(
            "needle_limit_cap_enforced_at_10",
            _validate_needle_limit(100) == 10,
        )
    )
    checks.append(
        _check(
            "needle_limit_passes_through_at_5",
            _validate_needle_limit(5) == 5,
        )
    )
    try:
        _validate_needle_limit(0)
        checks.append(_check("needle_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("needle_limit_rejects_zero", True))

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

    # C5-E rejects text method in method result records.
    try:
        validate_method_result_records(
            [
                {"method": "text", "metrics": {}, "failure_category_counts": {}},
            ]
        )
        checks.append(_check("method_record_rejects_text_method", False))
    except MethodConfigError:
        checks.append(_check("method_record_rejects_text_method", True))

    try:
        validate_method_result_records(
            [
                {"method": "bm25", "metrics": {"mrr": 0.5}, "failure_category_counts": {}},
            ]
        )
        checks.append(_check("method_record_accepts_allowlisted_method", True))
    except MethodConfigError:
        checks.append(_check("method_record_accepts_allowlisted_method", False))

    # metric keys must be from C5-D score allowlist.
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

    # Method metric allowlist is a subset of C5-D score allowlist.
    for k in METHOD_METRIC_ALLOWLIST:
        checks.append(
            _check(
                f"method_metric_allowlist_subset_of_c5d_{k}",
                k in c5d.SCORE_METRIC_ALLOWLIST,
            )
        )

    # Method result record allows aggregate_runtime_seconds.
    try:
        validate_method_result_records(
            [
                {
                    "method": "bm25",
                    "metrics": {"mrr": 0.5},
                    "failure_category_counts": {},
                    "aggregate_runtime_seconds": 12.34,
                },
            ]
        )
        checks.append(_check("method_record_accepts_runtime_seconds", True))
    except MethodConfigError:
        checks.append(_check("method_record_accepts_runtime_seconds", False))

    # Method result record rejects non-numeric aggregate_runtime_seconds.
    try:
        validate_method_result_records(
            [
                {
                    "method": "bm25",
                    "metrics": {"mrr": 0.5},
                    "failure_category_counts": {},
                    "aggregate_runtime_seconds": "fast",
                },
            ]
        )
        checks.append(_check("method_record_rejects_non_numeric_runtime", False))
    except MethodConfigError:
        checks.append(_check("method_record_rejects_non_numeric_runtime", True))

    # Method result record rejects unexpected keys.
    try:
        validate_method_result_records(
            [
                {
                    "method": "bm25",
                    "metrics": {"mrr": 0.5},
                    "failure_category_counts": {},
                    "unexpected_field": "value",
                },
            ]
        )
        checks.append(_check("method_record_rejects_unexpected_key", False))
    except MethodConfigError:
        checks.append(_check("method_record_rejects_unexpected_key", True))

    # --- Group 4: Deltas only for allowlisted metrics and baseline bm25. ---
    baseline_metrics = _build_synthetic_method_metrics("bm25")
    regex_metrics = _build_synthetic_method_metrics("regex")
    method_results = [
        {
            "method": "bm25",
            "status": STATUS_PASS,
            "needles_evaluated": 5,
            "needles_successful": 5,
            "needles_failed": 0,
            "metrics": baseline_metrics,
            "failure_category_counts": {c: 0 for c in FAILURE_CATEGORIES},
        },
        {
            "method": "regex",
            "status": STATUS_PASS,
            "needles_evaluated": 5,
            "needles_successful": 5,
            "needles_failed": 0,
            "metrics": regex_metrics,
            "failure_category_counts": {c: 0 for c in FAILURE_CATEGORIES},
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
                "status": STATUS_PASS,
                "needles_evaluated": 5,
                "needles_successful": 5,
                "needles_failed": 0,
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
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"scanner_rejects_{field}_key",
                bool(_scan_c5e({field: "bm25"})),
            )
        )
    # A clean matrix report must not contain any recommendation field.
    clean_report = _build_matrix_report(
        self_test_passed=True,
        needle_limit_requested=5,
        needles_seen=5,
        methods=["bm25", "regex", "symbol"],
        method_results=method_results,
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=1,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
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
    checks.append(
        _check(
            "scanner_rejects_method_results_as_dict",
            bool(_scan_c5e({"method_results": {"vector": {"metrics": {}}}})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_non_dict",
            bool(_scan_c5e({"method_results": ["not_a_dict"]})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_missing_method",
            bool(_scan_c5e({"method_results": [{"metrics": {}}]})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_method_not_allowlisted",
            bool(
                _scan_c5e(
                    {"method_results": [{"method": "vector", "metrics": {}}]}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_text_method",
            bool(
                _scan_c5e(
                    {"method_results": [{"method": "text", "metrics": {}}]}
                )
            ),
        )
    )
    # Scanner accepts a clean list-of-records.
    checks.append(
        _check(
            "scanner_accepts_clean_method_results_list",
            not _scan_c5e(
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

    # --- Group 7: Scanner rejects forbidden row-level/provider/default strings. ---
    for forbidden_key in (
        "repo", "commit_sha", "entrypoint_path", "topic", "content",
        "dependency", "needles", "needle", "needle_name", "needle_path",
        "needle_description", "needle_id", "name", "start_line", "end_line",
        "start_byte", "end_byte", "global_start_line", "global_end_line",
        "global_start_byte", "global_end_byte", "code_ratio", "path",
        "description", "row", "rows_data", "raw_row", "raw_rows",
        "repo_name", "repo_slug", "repo_url", "base_commit", "instance_id",
        "task_id", "query", "query_text", "problem_statement",
        "gold", "gold_path", "gold_span", "gold_snippet", "gold_paths",
        "gold_lines", "gold_context", "snippet", "snippets", "content_sha",
        "stdout", "stderr", "stdout_text", "stderr_text", "evidence",
        "evidence_row", "evidence_rows", "retrieved_path",
        "retrieved_paths", "retrieved_snippet", "cloned_repo_path",
        "cloned_repo", "per_row_metrics", "row_metrics",
        "per_needle_metrics", "needle_metrics", "patch", "diff",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{forbidden_key}_key",
                bool(_scan_c5e({forbidden_key: "value"})),
            )
        )
    # Recommendation fields.
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"scanner_rejects_{field}_key",
                bool(_scan_c5e({field: "bm25"})),
            )
        )
    # Value patterns.
    checks.append(
        _check(
            "scanner_rejects_repo_url_value",
            bool(_scan_c5e({"leaked": "https://github.com/foo/bar"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug_value",
            bool(_scan_c5e({"leaked": "psf/black"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha_value",
            bool(
                _scan_c5e(
                    {"leaked": "f03ee113c9f3dfeb477f2d4247bfb7de2e5f465c"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_c5e({"leaked": "src/black/trans.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            bool(_scan_c5e({"leaked": "585-639"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_hex_digest_value",
            bool(_scan_c5e({"leaked": "a" * 32})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path_value",
            bool(_scan_c5e({"leaked": "/tmp/foo"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_multiline_value",
            bool(_scan_c5e({"leaked": "line1\nline2"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_json_fragment",
            bool(_scan_c5e({"leaked": '{"key": "value"}'})),
        )
    )

    # --- Group 8: Scanner allows safe values. ---
    checks.append(
        _check(
            "scanner_allows_benchmark_value",
            not _scan_c5e({"benchmark": "repoqa"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_dataset_release_value",
            not _scan_c5e({"dataset_release": "repoqa-2024-06-23"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_baseline_method_value",
            not _scan_c5e({"baseline_method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_language_filter_value",
            not _scan_c5e({"language_filter": "python"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_query_mode_value",
            not _scan_c5e({"query_mode": "needle_description"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_gold_target_mode_value",
            not _scan_c5e({"gold_target_mode": "needle_path_line_range"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_network_mode_value",
            not _scan_c5e({"network_mode": "local_explicit"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_failure_category_count",
            not _scan_c5e(
                {
                    "failure_category_counts": {
                        "repo_clone_failed": 1,
                        "asset_download_failed": 0,
                    }
                }
            ),
        )
    )

    # --- Group 9: Status semantics. ---
    all_pass_results = [
        {
            "method": "bm25",
            "status": STATUS_PASS,
            "needles_evaluated": 5,
            "needles_successful": 5,
            "needles_failed": 0,
            "metrics": baseline_metrics,
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": STATUS_PASS,
            "needles_evaluated": 5,
            "needles_successful": 5,
            "needles_failed": 0,
            "metrics": regex_metrics,
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_pass_when_all_methods_succeed",
            _status_from_method_results(all_pass_results) == STATUS_PASS,
        )
    )
    mixed_results = [
        {
            "method": "bm25",
            "status": STATUS_PASS,
            "needles_evaluated": 5,
            "needles_successful": 5,
            "needles_failed": 0,
            "metrics": baseline_metrics,
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": STATUS_UNAVAILABLE,
            "needles_evaluated": 5,
            "needles_successful": 0,
            "needles_failed": 5,
            "metrics": {},
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_partial_when_mixed",
            _status_from_method_results(mixed_results) == STATUS_PARTIAL,
        )
    )
    none_results = [
        {
            "method": "bm25",
            "status": STATUS_UNAVAILABLE,
            "needles_evaluated": 5,
            "needles_successful": 0,
            "needles_failed": 5,
            "metrics": {},
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": STATUS_UNAVAILABLE,
            "needles_evaluated": 5,
            "needles_successful": 0,
            "needles_failed": 5,
            "metrics": {},
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_unavailable_when_none_succeed",
            _status_from_method_results(none_results) == STATUS_UNAVAILABLE,
        )
    )
    checks.append(
        _check(
            "status_unavailable_when_empty",
            _status_from_method_results([]) == STATUS_UNAVAILABLE,
        )
    )
    checks.append(
        _check(
            "status_pass_enum_is_repoqa_method_matrix_smoke_pass",
            STATUS_PASS == "repoqa_method_matrix_smoke_pass",
        )
    )

    # --- Group 10: Fail-closed generation. ---
    try:
        _enforce_c5e_no_forbidden(clean_report)
        checks.append(_check("fail_closed_clean_report_no_raise", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean_report_no_raise", False))

    leaked_report = dict(clean_report)
    leaked_report["leaked_repo"] = "psf/black"
    try:
        _enforce_c5e_no_forbidden(leaked_report)
        checks.append(_check("fail_closed_leaked_repo_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_leaked_repo_raises", True))

    leaked_report2 = dict(clean_report)
    leaked_report2["best_method"] = "regex"
    try:
        _enforce_c5e_no_forbidden(leaked_report2)
        checks.append(_check("fail_closed_best_method_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_best_method_raises", True))

    leaked_report3 = dict(clean_report)
    leaked_report3["winner"] = "symbol"
    try:
        _enforce_c5e_no_forbidden(leaked_report3)
        checks.append(_check("fail_closed_winner_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_winner_raises", True))

    leaked_report4 = dict(clean_report)
    leaked_report4["recommended_default"] = "bm25"
    try:
        _enforce_c5e_no_forbidden(leaked_report4)
        checks.append(_check("fail_closed_recommended_default_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_recommended_default_raises", True))

    leaked_report5 = dict(clean_report)
    leaked_report5["method_results"] = {"bm25": {"metrics": {}}}
    try:
        _enforce_c5e_no_forbidden(leaked_report5)
        checks.append(_check("fail_closed_method_results_dict_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_method_results_dict_raises", True))

    leaked_report6 = dict(clean_report)
    leaked_report6["commit_sha"] = "0" * 40
    try:
        _enforce_c5e_no_forbidden(leaked_report6)
        checks.append(_check("fail_closed_commit_sha_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_commit_sha_raises", True))

    failed_self_test_report = dict(clean_report)
    failed_self_test_report["self_test_passed"] = False
    try:
        c5d.c5a._refuse_on_self_test_failure(failed_self_test_report)
        checks.append(_check("refuse_on_self_test_failure_raises", False))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_failure_raises", True))

    try:
        c5d.c5a._refuse_on_self_test_failure(clean_report)
        checks.append(_check("refuse_on_self_test_pass_no_raise", True))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_pass_no_raise", False))

    # --- Group 11: Artifact identity fields. ---
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
            "benchmark_correct",
            clean_report["benchmark"] == BENCHMARK,
        )
    )
    checks.append(
        _check(
            "dataset_release_correct",
            clean_report["dataset_release"] == DATASET_RELEASE,
        )
    )
    checks.append(
        _check(
            "query_mode_correct",
            clean_report["query_mode"] == QUERY_MODE,
        )
    )
    checks.append(
        _check(
            "gold_target_mode_correct",
            clean_report["gold_target_mode"] == GOLD_TARGET_MODE,
        )
    )
    checks.append(
        _check(
            "status_pass_when_self_test_passed",
            clean_report["status"] == STATUS_PASS,
        )
    )

    # --- Group 12: Safe true flags. ---
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
            "safe_true_repoqa_method_matrix_smoke_performed",
            clean_report.get("repoqa_method_matrix_smoke_performed") is True,
        )
    )
    # C5-E does NOT use C5-D's repoqa_retrieval_smoke_performed flag.
    checks.append(
        _check(
            "no_c5d_repoqa_retrieval_smoke_performed_flag",
            "repoqa_retrieval_smoke_performed" not in clean_report,
        )
    )

    # --- Group 13: No-claim / no-runtime-change false flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"no_claim_{flag}_false",
                clean_report.get(flag) is False,
            )
        )

    # --- Group 14: License fields. ---
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

    # --- Group 15: Unavailable report. ---
    unavail = _build_unavailable_report(
        "asset_download_failed",
        self_test_passed=True,
        needle_limit_requested=5,
        methods=["bm25", "regex", "symbol"],
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "unavailable_status",
            unavail["status"] == STATUS_UNAVAILABLE,
        )
    )
    checks.append(
        _check(
            "unavailable_failure_reason_category",
            unavail["failure_reason_category"] == "asset_download_failed",
        )
    )
    checks.append(
        _check(
            "unavailable_no_repoqa_method_matrix_smoke_performed_flag",
            unavail["repoqa_method_matrix_smoke_performed"] is False,
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
                r["status"] == STATUS_UNAVAILABLE
                for r in unavail["method_results"]
            ),
        )
    )

    # --- Group 16: Schema contract failure. ---
    schema_fail = _build_schema_contract_failure(
        "method_result_record_invalid",
        self_test_passed=True,
        needle_limit_requested=5,
        methods=["bm25", "regex", "symbol"],
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "schema_contract_failure_status",
            schema_fail["status"] == STATUS_FAIL_SCHEMA_CONTRACT,
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

    # --- Group 17: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_artifact_self_scan_clean",
            not _scan_c5e(clean_report),
        )
    )
    checks.append(
        _check(
            "unavailable_self_scan_clean",
            not _scan_c5e(unavail),
        )
    )

    # --- Group 18: CLI argument surface. ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for required_opt in (
        "--self-test",
        "--needle-limit",
        "--methods",
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

    # --- Group 19: ALLOWED_METHODS exactly bm25,regex,symbol. ---
    checks.append(
        _check(
            "allowed_methods_exact",
            ALLOWED_METHODS == ("bm25", "regex", "symbol"),
        )
    )
    checks.append(
        _check(
            "allowed_methods_excludes_text",
            "text" not in ALLOWED_METHODS,
        )
    )

    # --- Group 20: aggregate_runtime_seconds in method result records. ---
    method_rec_with_runtime = _build_method_result_record(
        method="bm25",
        status=STATUS_PASS,
        needles_evaluated=5,
        needles_successful=5,
        needles_failed=0,
        metrics=baseline_metrics,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
        aggregate_runtime_seconds=12.345,
    )
    checks.append(
        _check(
            "method_record_has_aggregate_runtime_seconds",
            "aggregate_runtime_seconds" in method_rec_with_runtime
            and isinstance(
                method_rec_with_runtime["aggregate_runtime_seconds"],
                (int, float),
            ),
        )
    )
    # Scanner accepts method record with runtime seconds.
    checks.append(
        _check(
            "scanner_accepts_method_record_with_runtime",
            not _scan_c5e(
                {"method_results": [method_rec_with_runtime]}
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
    """Build the C5-E CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "C5-E RepoQA method-matrix retrieval smoke "
            "(public aggregate-only artifact; bounded RepoQA Python "
            "needle subset; transient /tmp asset download + clone + "
            "retrieval + score; methods bm25,regex,symbol only; no "
            "provider calls; no raw repo/commit/path/description/line/"
            "source/needle IDs/row IDs/hashes/winner/best_method/"
            "recommended_default committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written, no network)",
    )
    ap.add_argument(
        "--needle-limit",
        type=int,
        default=NEEDLE_LIMIT_DEFAULT,
        help=(
            "number of RepoQA Python needles to evaluate per method "
            "(default: " f"{NEEDLE_LIMIT_DEFAULT}; hard cap "
            f"{NEEDLE_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--methods",
        default=None,
        help=(
            "comma-separated OpenLocus retrieval methods (default: "
            f"{','.join(DEFAULT_METHODS)}; allowed: "
            f"{', '.join(ALLOWED_METHODS)}; duplicates are deduplicated "
            "deterministically; text is NOT allowed in C5-E)"
        ),
    )
    ap.add_argument(
        "--language-filter",
        default=DEFAULT_LANGUAGE_FILTER,
        choices=ALLOWED_LANGUAGE_FILTERS,
        help=(
            "language filter category (default: python; allowed: "
            f"{', '.join(ALLOWED_LANGUAGE_FILTERS)}; C5-E does NOT "
            "silently fall back to all languages)"
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
            needle_limit_requested=args.needle_limit,
            methods=[],
            language_filter=args.language_filter,
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )
        _write_json(args.out, report)
        sys.exit(1)

    needle_limit = _validate_needle_limit(args.needle_limit)
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
    openlocus_bin, openlocus_source = c5d.c5a._resolve_openlocus_binary(
        args.openlocus
    )
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_c5e_no_forbidden(report)
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
            needle_limit=needle_limit,
            methods=methods,
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
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
        )

    _enforce_c5e_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"methods={report['methods_requested']}, "
        f"methods_successful={report['methods_successful']}, "
        f"needles_seen={report['needles_seen']})"
    )


if __name__ == "__main__":
    main()
