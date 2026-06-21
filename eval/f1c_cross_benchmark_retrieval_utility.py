#!/usr/bin/env python3
"""F1-C Cross-Benchmark Retrieval-Derived Utility Smoke (Public Aggregate-Only).

This module implements the **F1-C cross-benchmark retrieval-derived
utility smoke**. It reruns two bounded external-benchmark-shaped
retrieval samples (ContextBench verified 20-row + RepoQA 10-needle
Python) and computes a fixed retrieval-derived utility proxy per
benchmark/method, plus cross-benchmark weighted means and
counterfactual effects vs the synthetic ``empty_retrieval`` baseline
and the fixed ``bm25`` baseline.

F1-C is explicitly **not** a downstream utility claim, **not** true
E/S calibration, **not** an external benchmark performance claim, **not**
a leaderboard entry, **not** a promotion/default/runtime/retriever/
pack/backend/EvidenceCore semantic change, and **not** a live/provider
claim. It makes NO provider calls and NO remote provider calls. It
reruns real bounded external data; it does NOT combine existing C5
aggregate artifacts.

Claim boundary (binding):

* Claim level: ``cross_benchmark_retrieval_derived_utility_smoke_only``.
* Status enum: ``cross_benchmark_retrieval_utility_pass`` |
  ``partial_with_exclusions`` | ``unavailable_with_reason`` |
  ``fail_forbidden_scan`` | ``fail_schema_contract``.
* Mode: ``bounded_contextbench_repoqa_retrieval_utility``; phase ``F1-C``.

Utility formula (fixed diagnostic proxy; NOT downstream solve rate,
NOT E/S calibration):

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

where ``file_hit = file_recall@10`` and ``span_f0.5 = span_f0.5@10``.
``empty_retrieval`` is the explicit zero-context baseline (no retrieval
run required; all metrics/utility 0).

Counterfactual effects (fixed allowlist; records-shaped only):

* ``bm25_vs_empty``  — (bm25 - empty_retrieval).
* ``regex_vs_empty`` — (regex - empty_retrieval).
* ``symbol_vs_empty`` — (symbol - empty_retrieval).
* ``regex_vs_bm25``  — (regex - bm25).
* ``symbol_vs_bm25`` — (symbol - bm25).

Effects are computed for the cross-benchmark weighted mean of
``retrieval_utility`` and each aggregate metric
(``file_recall@10``, ``mrr``, ``span_f0.5@10``, ``success_rate``,
``retrieval_utility``).

Allowed method labels: ``empty_retrieval``, ``bm25``, ``regex``,
``symbol``. Allowed metrics: ``file_recall@10``, ``mrr``,
``span_f0.5@10``, ``success_rate``, ``retrieval_utility``.

Privacy / license boundary (binding):

* Public artifact/docs/workflow uploads aggregate-only.
* No repo names/URLs, commits, task/row/needle IDs, problem statements,
  queries, needle descriptions, gold labels, label paths/spans/line
  ranges, source snippets, generated JSONL, retrieval evidence rows,
  candidate paths/spans/content hashes, stdout/stderr, clone paths, raw
  asset rows, row hashes, provider fields, raw model/routing prefixes,
  winner/best/default/recommended fields.
* Fixed config labels ``needle_description``,
  ``needle_path_line_range``, and ``first_paragraph`` are OK only as
  config labels.
* ContextBench and RepoQA failure categories remain separate; do NOT
  merge incompatible enums.

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real smoke requires public network access to HF datasets-server
  (ContextBench) and GitHub (RepoQA asset + repo clones). CI must be
  a separate explicit ``workflow_dispatch`` job with
  ``enable_external_benchmark_network=true``. It must NOT run on
  PR/push by default, must use no provider secrets/vars, no provider
  model env, and must upload only the aggregate F1-C report.
* Network-enabled CI is fail-closed: status pass/partial only,
  ContextBench rows > 0, RepoQA needles > 0, bm25 succeeds on both
  benchmarks, forbidden_scan pass, provider_calls=0.

Run::

    python3 -m py_compile eval/f1c_cross_benchmark_retrieval_utility.py
    python3 eval/f1c_cross_benchmark_retrieval_utility.py --self-test
    python3 eval/f1c_cross_benchmark_retrieval_utility.py \\
        --contextbench-row-limit 20 --repoqa-needle-limit 10 \\
        --methods bm25,regex,symbol \\
        --out artifacts/f1c_cross_benchmark_retrieval_utility/\\
f1c_cross_benchmark_retrieval_utility_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful ``unavailable_with_reason`` with a real
failure category (no stale/fake pass). Self-test/docs/diff-check still
pass.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse C5-C (ContextBench verified matrix scale smoke) and C5-E
# (RepoQA method matrix smoke) helpers. The ``eval`` directory has no
# ``__init__.py`` (flat script directory), so we add this file's
# parent to ``sys.path`` and import the C5-C / C5-E modules directly.
# F1-C does NOT import or mutate C5-C/C5-E; it only reuses their
# primitives and reruns real bounded external data.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5c_contextbench_verified_method_matrix_scale_smoke as c5c  # noqa: E402
import c5e_repoqa_method_matrix_smoke as c5e  # noqa: E402
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (F1-C owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "f1c_cross_benchmark_retrieval_utility.v1"
GENERATED_BY = "eval/f1c_cross_benchmark_retrieval_utility.py"
CLAIM_LEVEL = "cross_benchmark_retrieval_derived_utility_smoke_only"
MODE = "bounded_contextbench_repoqa_retrieval_utility"
PHASE = "F1-C"

STATUS_PASS = "cross_benchmark_retrieval_utility_pass"
STATUS_PARTIAL = "partial_with_exclusions"
STATUS_UNAVAILABLE = "unavailable_with_reason"
STATUS_FAIL_FORBIDDEN_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA_CONTRACT = "fail_schema_contract"

ALL_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_PASS,
        STATUS_PARTIAL,
        STATUS_UNAVAILABLE,
        STATUS_FAIL_FORBIDDEN_SCAN,
        STATUS_FAIL_SCHEMA_CONTRACT,
    }
)

SELF_TEST_CHECKS_TOTAL = 167

COMPONENT_STATUS_PASS = "pass"
COMPONENT_STATUS_PARTIAL = "partial"
COMPONENT_STATUS_UNAVAILABLE = "unavailable"
COMPONENT_STATUSES: frozenset[str] = frozenset(
    {
        COMPONENT_STATUS_PASS,
        COMPONENT_STATUS_PARTIAL,
        COMPONENT_STATUS_UNAVAILABLE,
    }
)

DEFAULT_OUT = Path(
    "artifacts/f1c_cross_benchmark_retrieval_utility/"
    "f1c_cross_benchmark_retrieval_utility_report.json"
)

# Hard caps. ContextBench default 20; hard cap 20. RepoQA default 10;
# hard cap 10.
CONTEXTBENCH_ROW_LIMIT_DEFAULT = 20
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = 20
REPOQA_NEEDLE_LIMIT_DEFAULT = 10
REPOQA_NEEDLE_LIMIT_HARD_CAP = 10

# Methods supported by F1-C: bm25, regex, symbol only (mirrors C5-C/C5-E;
# text NOT allowed).
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
BASELINE_METHOD = "bm25"

# Method labels for F1-C (includes empty_retrieval baseline).
ALL_METHOD_LABELS: tuple[str, ...] = (
    "empty_retrieval",
    "bm25",
    "regex",
    "symbol",
)

# Benchmarks.
BENCHMARKS: tuple[str, ...] = ("contextbench", "repoqa")
CONTEXTBENCH_BENCHMARK = "contextbench"
REPOQA_BENCHMARK = "repoqa"

# Query / gold target config labels (fixed config labels only).
CONTEXTBENCH_QUERY_MODE = "first_paragraph"
REPOQA_QUERY_MODE = "needle_description"
REPOQA_GOLD_TARGET_MODE = "needle_path_line_range"

# Counterfactual effects (fixed allowlist; records-shaped only).
# Each effect is (treatment_method - baseline_method).
EFFECT_METHOD_PAIRS: dict[str, tuple[str, str]] = {
    "bm25_vs_empty": ("bm25", "empty_retrieval"),
    "regex_vs_empty": ("regex", "empty_retrieval"),
    "symbol_vs_empty": ("symbol", "empty_retrieval"),
    "regex_vs_bm25": ("regex", "bm25"),
    "symbol_vs_bm25": ("symbol", "bm25"),
}
EFFECTS: tuple[str, ...] = tuple(EFFECT_METHOD_PAIRS.keys())

# Metrics (aggregate retrieval/score utility proxy; NOT downstream-agent
# metrics). ``retrieval_utility`` is the F1-C fixed utility proxy.
METRIC_NAMES: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
    "retrieval_utility",
)

# Utility formula constants (fixed; do NOT change).
MRR_WEIGHT = 0.25
SPAN_F_WEIGHT = 0.5
MISS_PENALTY = 0.25

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be
# true in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "retrieval_derived_counterfactual_utility_smoke": False,
    "contextbench_rows_read": False,
    "repoqa_needles_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). F1-C runs NO provider, makes NO remote provider
# calls, proves NO downstream agent value, promotes NO candidate, claims
# NO E/S calibration / external benchmark performance / leaderboard
# entry / method winner / default change, and changes NO runtime/
# retriever/pack/backend/default-policy/EvidenceCore semantics.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "true_e_s_calibration_claimed": False,
    "automated_e_s_full_calibration_claimed": False,
    "human_e_s_calibration_claimed": False,
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
    "method_winner_claimed": False,
    "baseline_is_policy_candidate": False,
    "downstream_agent_value_proven": False,
    "promotion_ready": False,
    "default_should_change": False,
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
# License / redistribution fields (fixed).
# ---------------------------------------------------------------------------

LICENSE_FIELDS: dict[str, Any] = {
    "dataset_license_status": "unknown_dataset_license",
    "row_level_redistribution_allowed": False,
    "derived_row_level_publication_allowed": False,
    "aggregate_metrics_publication": "aggregate_only_smoke",
}

# ---------------------------------------------------------------------------
# Failure category enums (kept SEPARATE for ContextBench and RepoQA;
# do NOT merge incompatible enums). ContextBench reuses C5-C public
# failure categories; RepoQA reuses C5-D/C5-E failure categories.
# ---------------------------------------------------------------------------

CONTEXTBENCH_FAILURE_CATEGORIES: tuple[str, ...] = (
    c5c.PUBLIC_FAILURE_CATEGORIES
)
REPOQA_FAILURE_CATEGORIES: tuple[str, ...] = tuple(c5d.FAILURE_CATEGORIES)

# ---------------------------------------------------------------------------
# Public artifact scanner (F1-C owned, strict, fail-closed).
#
# F1-C reuses the C5-C and C5-E forbidden scanner primitives for raw
# key/value leak detection (URLs, hex digests, repo slugs, /tmp paths,
# ContextBench-specific forbidden keys, RepoQA-specific forbidden keys,
# recommendation fields, etc.) and ADDS F1-C-specific scanners that:
#   * reject ``benchmark_results`` / ``cross_benchmark_method_results``
#     if they are dicts keyed by method/benchmark name (must be lists
#     of records);
#   * reject the FORBIDDEN_RECOMMENDATION_FIELDS keys anywhere;
#   * reject E/S calibration notation keys anywhere;
#   * reject raw model routing prefix values anywhere.
# ---------------------------------------------------------------------------

# Recommendation / policy field names that must NEVER be emitted by F1-C
# (anywhere in the public artifact).
FORBIDDEN_RECOMMENDATION_FIELDS: frozenset[str] = frozenset(
    c5c.FORBIDDEN_RECOMMENDATION_FIELDS
    | {
        "winner",
        "best",
        "best_method",
        "best_variant",
        "recommended_default",
        "preferred_variant",
        "preferred_method",
        "best_arm",
        "best_family",
    }
)

# E/S calibration notation keys (never emitted).
ES_NOTATION_KEYS: frozenset[str] = frozenset(
    {
        "E_primary",
        "S_support",
        "e_score",
        "s_score",
        "model_id_raw",
        "routing_prefix",
    }
)

# Schema-key container keys whose CHILD KEYS are fixed schema-only
# category labels (NOT row-level values). The forbidden_key check is
# relaxed for keys nested directly under these containers, because those
# keys are fixed category labels used as count buckets. The values under
# these containers are still scanned (they must be ints/counts only).
F1C_SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "failure_category_counts",
        "contextbench_failure_category_counts",
        "repoqa_failure_category_counts",
        "metrics",
        "benchmark_results",
        "cross_benchmark_method_results",
        "counterfactual_effects",
    }
)

# F1-C-specific safe VALUE path last-key segments. These are list/dict
# fields whose VALUES are categorical bucket strings (e.g. ``"python"``,
# ``"bm25"``, ``"contextbench"``). The C5-A scanner may flag some of
# these as ``forbidden_field_name_value``; F1-C suppresses those false
# positives.
F1C_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "generated_by",
        "generated_at",
        "claim_level",
        "status",
        "mode",
        "phase",
        "method",
        "baseline_method",
        "benchmark",
        "metric",
        "effect_name",
        "baseline_method_label",
        "treatment_method",
        "baseline_method",
        "language_filter",
        "query_mode",
        "gold_target_mode",
        "network_mode",
        "openlocus_binary_source",
        "failure_reason_category",
        "dataset_license_status",
        "aggregate_metrics_publication",
        "methods_requested",
        "methods_allowed",
        "methods_count",
        "methods_attempted",
        "methods_successful",
        "methods_succeeded",
        "methods_failed",
        "contextbench_query_mode",
        "repoqa_query_mode",
        "repoqa_gold_target_mode",
    }
)

# Reuse C5-A value patterns via C5-C/C5-D.
_RE_URL_VALUE = c5a._RE_URL_VALUE
_RE_HEX_DIGEST = c5a._RE_HEX_DIGEST
_RE_SECRET_LIKE = c5a._RE_SECRET_LIKE
_RE_FILE_PATH_VALUE = c5a._RE_FILE_PATH_VALUE
_RE_LINE_RANGE_VALUE = c5a._RE_LINE_RANGE_VALUE
_RE_RAW_JSON = c5a._RE_RAW_JSON
_RE_TMP_PATH_VALUE = c5a._RE_TMP_PATH_VALUE
_RE_TASK_ID_VALUE = c5a._RE_TASK_ID_VALUE
_RE_PATCH_MARKER = c5a._RE_PATCH_MARKER
_RE_STACK_TRACE = c5a._RE_STACK_TRACE
_RE_COMMIT_SHA_VALUE = c5a._RE_COMMIT_SHA_VALUE
_RE_REPO_SLUG_VALUE = c5a._RE_REPO_SLUG_VALUE
_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)

_SECRET_SENTINEL = c5a._SECRET_SENTINEL
_ROUTING_PREFIX_SENTINEL = "[" + "m" + "k]"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in F1C_SAFE_VALUE_PATH_LAST_KEYS


def _is_schema_key_container(path: str) -> bool:
    """Check if any segment of the path is a schema-key container."""
    for seg in path.split("."):
        base = seg.split("[")[0]
        if base in F1C_SCHEMA_KEY_CONTAINER_KEYS:
            return True
    return False


def _scan_f1c_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for F1-C-specific forbidden keys (recommendation + ES notation)."""
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                if key_str in FORBIDDEN_RECOMMENDATION_FIELDS:
                    violations.append(
                        {
                            "category": "forbidden_recommendation_field",
                            "path": sub_path,
                        }
                    )
                if key_str in ES_NOTATION_KEYS:
                    violations.append(
                        {
                            "category": "forbidden_es_notation_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_f1c_records_shape(obj: Any) -> list[dict[str, Any]]:
    """Reject ``benchmark_results`` / ``cross_benchmark_method_results``
    / ``counterfactual_effects`` if they are not lists of records.
    """
    violations: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for container in (
            "benchmark_results",
            "cross_benchmark_method_results",
            "counterfactual_effects",
        ):
            val = obj.get(container)
            if val is None:
                continue
            if not isinstance(val, list):
                violations.append(
                    {
                        "category": f"{container}_not_list",
                        "path": f"$.{container}",
                    }
                )
    return violations


def _scan_f1c_value_patterns(obj: Any) -> list[dict[str, Any]]:
    """Scan for F1-C-specific forbidden value patterns.

    Adds the raw model routing prefix check on top of the
    C5-A/C5-C/C5-E scanners (which already cover URLs, hex digests,
    repo slugs, /tmp paths, patch markers, stack traces, etc.).
    """
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                sub_path = f"{path}.{key}"
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")
        elif isinstance(o, str):
            safe_value = _is_safe_value_path(path)
            if not safe_value and _RE_RAW_MODEL_PREFIX.search(o):
                violations.append(
                    {
                        "category": "raw_model_prefix_value",
                        "path": path,
                    }
                )

    _walk(obj)
    return violations


def _scan_f1c(obj: Any) -> list[dict[str, Any]]:
    """Combined F1-C scanner.

    Runs:
    * C5-A forbidden scanner primitives (raw key/value leak detection).
    * C5-C-specific forbidden keys (extra row keys, recommendation
      fields) — these cover ContextBench-shaped leaks.
    * C5-D/C5-E-specific forbidden keys (RepoQA-shaped leaks).
    * F1-C-specific forbidden keys (ES notation, recommendation fields).
    * F1-C records-shape check (lists, not dict-keyed mirrors).

    False positives from C5-A (``forbidden_field_name_value``) are
    suppressed where a legitimate categorical bucket string appears as
    a value under an F1-C-specific safe value path.
    """
    violations: list[dict[str, Any]] = []
    # Run C5-C scanner (covers C5-A + C5-C-specific forbidden keys).
    for v in c5c._scan_c5c(obj):
        if v.get("category") == "forbidden_field_name_value" and _is_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    # Run C5-E scanner (covers C5-D + C5-E-specific RepoQA keys).
    for v in c5e._scan_c5e(obj):
        if v.get("category") == "forbidden_field_name_value" and _is_safe_value_path(
            v.get("path", "")
        ):
            continue
        # C5-E may add duplicate findings for keys already caught by
        # C5-C; deduplicate by (category, path).
        key = (v.get("category"), v.get("path"))
        if not any(
            (vv.get("category"), vv.get("path")) == key for vv in violations
        ):
            violations.append(v)
    # F1-C-specific scanners.
    violations.extend(_scan_f1c_forbidden_keys(obj))
    violations.extend(_scan_f1c_records_shape(obj))
    violations.extend(_scan_f1c_value_patterns(obj))
    return violations


def _f1c_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the F1-C forbidden scanner and return a sanitized summary."""
    violations = _scan_f1c(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_f1c_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _f1c_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


def _refuse_on_self_test_failure(report: dict[str, Any]) -> None:
    if report.get("self_test_passed") is not True:
        raise SystemExit(
            "self-test failed; refusing to write artifact"
        )


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return {"check": name, "passed": bool(ok)}


def _round_metric(value: float) -> float:
    return round(float(value), 6)


# ---------------------------------------------------------------------------
# Method parser / validator (F1-C owned)
# ---------------------------------------------------------------------------


class MethodConfigError(ValueError):
    """Raised when the requested methods config violates the F1-C contract."""


def parse_methods(methods_arg: str | None) -> list[str]:
    """Parse a comma-separated ``--methods`` argument into a method list.

    Rules (F1-C owned):

    * Empty / None -> default ``["bm25", "regex", "symbol"]``.
    * Each token must be in ``ALLOWED_METHODS`` (bm25, regex, symbol
      only; ``text`` NOT allowed); unknown methods raise
      ``MethodConfigError``.
    * Duplicate tokens are deduplicated deterministically (preserving
      first-seen order).
    * Empty tokens are skipped silently.
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


def _validate_contextbench_row_limit(row_limit: int) -> int:
    """Validate and cap --contextbench-row-limit to the hard cap (20)."""
    if not isinstance(row_limit, int):
        raise SystemExit("invalid arguments")
    if row_limit < 1:
        raise SystemExit("invalid arguments")
    if row_limit > CONTEXTBENCH_ROW_LIMIT_HARD_CAP:
        return CONTEXTBENCH_ROW_LIMIT_HARD_CAP
    return row_limit


def _validate_repoqa_needle_limit(needle_limit: int) -> int:
    """Validate and cap --repoqa-needle-limit to the hard cap (10)."""
    if not isinstance(needle_limit, int):
        raise SystemExit("invalid arguments")
    if needle_limit < 1:
        raise SystemExit("invalid arguments")
    if needle_limit > REPOQA_NEEDLE_LIMIT_HARD_CAP:
        return REPOQA_NEEDLE_LIMIT_HARD_CAP
    return needle_limit


# ---------------------------------------------------------------------------
# Utility computation (fixed diagnostic proxy; NOT downstream value).
# ---------------------------------------------------------------------------


def _extract_method_metrics(
    score_metrics: dict[str, Any] | None,
) -> dict[str, float]:
    """Extract allowlisted metrics from a score.py result.

    For ``empty_retrieval`` (no retrieval run), all metrics are zero
    by construction.
    """
    result: dict[str, float] = {
        name: 0.0 for name in METRIC_NAMES
    }
    if score_metrics is None:
        return result
    for name in METRIC_NAMES:
        if name == "retrieval_utility":
            continue
        val = score_metrics.get(name)
        if isinstance(val, bool):
            result[name] = 1.0 if val else 0.0
        elif isinstance(val, (int, float)):
            result[name] = _round_metric(float(val))
        else:
            result[name] = 0.0
    result["retrieval_utility"] = _compute_utility(result)
    return result


def _compute_utility(metrics: dict[str, Any]) -> float:
    """Compute the F1-C fixed diagnostic utility proxy.

    ``utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty``
    where ``file_hit = file_recall@10``,
    ``span_f0.5 = span_f0.5@10``, and
    ``miss_penalty = 0.25 if file_recall@10 == 0 else 0``.

    This is a retrieval-derived diagnostic proxy, NOT downstream solve
    rate, NOT E/S calibration.
    """
    file_recall = float(metrics.get("file_recall@10", 0.0) or 0.0)
    mrr = float(metrics.get("mrr", 0.0) or 0.0)
    span_f = float(metrics.get("span_f0.5@10", 0.0) or 0.0)
    miss_penalty = MISS_PENALTY if file_recall == 0.0 else 0.0
    utility = (
        file_recall
        + MRR_WEIGHT * mrr
        + SPAN_F_WEIGHT * span_f
        - miss_penalty
    )
    return _round_metric(utility)


def _aggregate_method_metrics(
    per_row_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-row metrics into per-method means.

    Returns a dict with ``row_count`` and the mean of each allowlisted
    metric (including the recomputed ``retrieval_utility`` mean over
    per-row utilities).
    """
    n = len(per_row_metrics)
    result: dict[str, Any] = {"row_count": n}
    for name in METRIC_NAMES:
        values = [
            r[name]
            for r in per_row_metrics
            if name in r and isinstance(r[name], (int, float))
        ]
        if values:
            result[name] = _round_metric(sum(values) / len(values))
        else:
            result[name] = 0.0
    return result


def _weighted_mean(
    values_by_benchmark: dict[str, tuple[float, int]],
) -> float:
    """Compute a sample-count-weighted mean across benchmarks.

    ``values_by_benchmark`` maps benchmark -> (value, sample_count).
    """
    total_weight = sum(w for _, w in values_by_benchmark.values())
    if total_weight <= 0:
        return 0.0
    total = sum(v * w for v, w in values_by_benchmark.values())
    return _round_metric(total / total_weight)


def _compute_counterfactual_effects(
    cross_benchmark_method_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute counterfactual effects as fixed records.

    Each record: ``{effect_name, baseline_method, treatment_method,
    metric, delta}`` where ``delta`` is the cross-benchmark weighted
    mean of (treatment - baseline) for that metric.
    """
    method_map = {
        r["method"]: r for r in cross_benchmark_method_results
    }
    effects: list[dict[str, Any]] = []
    for effect_name, (treatment, baseline) in EFFECT_METHOD_PAIRS.items():
        t_record = method_map.get(treatment, {})
        b_record = method_map.get(baseline, {})
        t_metrics = t_record.get("metrics", {}) if isinstance(
            t_record, dict
        ) else {}
        b_metrics = b_record.get("metrics", {}) if isinstance(
            b_record, dict
        ) else {}
        for metric in METRIC_NAMES:
            t_val = float(t_metrics.get(metric, 0.0) or 0.0)
            b_val = float(b_metrics.get(metric, 0.0) or 0.0)
            effects.append(
                {
                    "effect_name": effect_name,
                    "baseline_method": baseline,
                    "treatment_method": treatment,
                    "metric": metric,
                    "delta": _round_metric(t_val - b_val),
                }
            )
    return effects


# ---------------------------------------------------------------------------
# ContextBench real-run matrix runner (reruns real bounded external data;
# does NOT reuse C5-C aggregate artifacts).
# ---------------------------------------------------------------------------


def _run_contextbench_matrix(
    *,
    row_limit: int,
    methods: list[str],
    openlocus_bin: str,
    openlocus_binary_source: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run the real ContextBench matrix smoke (transient /tmp; aggregate-only).

    Returns a dict with:
    * ``status``: ``pass`` / ``partial`` / ``unavailable``.
    * ``rows_fetched``: bounded row count.
    * ``method_results``: list of per-method aggregate record dicts
      (each with ``method``, ``rows_evaluated``, ``rows_successful``,
      ``rows_failed``, ``metrics`` (F1-C allowlist with
      ``retrieval_utility``), ``failure_category_counts``).
    * ``failure_category_counts``: aggregate ContextBench fcc.
    * ``network_calls``: count of HF HTTP calls made.
    * ``failure_reason_category``: real failure category on unavailable.
    """
    fcc = {c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES}
    network_calls = 0

    # Step 1: fetch rows from HF datasets-server ONCE (shared across
    # methods).
    rows, fetch_status, nc, fcc_update = c5a._fetch_contextbench_rows(
        row_limit, c5a.DEFAULT_LANGUAGE_FILTER
    )
    network_calls += nc
    for k, v in c5c._public_failure_counts(fcc_update).items():
        if k in fcc:
            fcc[k] += v

    if fetch_status == "unavailable" or not rows:
        return {
            "status": "unavailable",
            "rows_fetched": len(rows),
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": (
                "network_fetch_failed" if not rows else "no_python_rows"
            ),
        }

    rows_fetched = len(rows)

    # Step 2: for each method, run retrieval + scoring across all rows.
    # Reuse C5-C ``_run_single_method`` to drive the per-method matrix
    # (clone + retrieval + score); then re-extract F1-C allowlisted
    # metrics with the ``retrieval_utility`` proxy.
    method_results: list[dict[str, Any]] = []
    for method in methods:
        c5c_result = c5c._run_single_method(
            method=method,
            rows=rows,
            row_limit=row_limit,
            query_mode=c5a.DEFAULT_QUERY_MODE,
            language_filter=c5a.DEFAULT_LANGUAGE_FILTER,
            openlocus_bin=openlocus_bin,
            eval_dir=eval_dir,
        )
        for k, v in c5c._public_failure_counts(
            c5c_result.get("failure_category_counts", {})
        ).items():
            if k in fcc:
                fcc[k] += v
        # Re-extract F1-C metrics from the C5-C record.
        c5c_metrics = c5c_result.get("metrics", {}) or {}
        f1c_metrics = _extract_method_metrics(c5c_metrics)
        # Re-mark success_rate using C5-C's value (it is recomputed
        # from rows_successful / rows_evaluated in C5-C).
        if "success_rate" in c5c_metrics:
            f1c_metrics["success_rate"] = _round_metric(
                float(c5c_metrics["success_rate"])
            )
        # Recompute utility with the final metrics (in case success_rate
        # changed).
        f1c_metrics["retrieval_utility"] = _compute_utility(f1c_metrics)
        method_results.append(
            {
                "method": method,
                "rows_evaluated": c5c_result.get(
                    "rows_evaluated", 0
                ),
                "rows_successful": c5c_result.get(
                    "rows_successful", 0
                ),
                "rows_failed": c5c_result.get("rows_failed", 0),
                "metrics": f1c_metrics,
                "failure_category_counts": c5c._public_failure_counts(
                    c5c_result.get("failure_category_counts", {})
                ),
                "status": c5c_result.get("status", ""),
            }
        )

    any_success = any(
        r.get("rows_successful", 0) > 0 for r in method_results
    )
    if not any_success:
        return {
            "status": "unavailable",
            "rows_fetched": rows_fetched,
            "method_results": method_results,
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "retrieval_failed",
        }

    all_succeed = all(
        r.get("rows_successful", 0) > 0 for r in method_results
    )
    status = "pass" if all_succeed else "partial"
    return {
        "status": status,
        "rows_fetched": rows_fetched,
        "method_results": method_results,
        "failure_category_counts": fcc,
        "network_calls": network_calls,
        "failure_reason_category": "",
    }


# ---------------------------------------------------------------------------
# RepoQA real-run matrix runner (reruns real bounded external data;
# does NOT reuse C5-E aggregate artifacts).
# ---------------------------------------------------------------------------


def _run_repoqa_matrix(
    *,
    needle_limit: int,
    methods: list[str],
    openlocus_bin: str,
    openlocus_binary_source: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run the real RepoQA matrix smoke (transient /tmp; aggregate-only).

    Returns a dict with:
    * ``status``: ``pass`` / ``partial`` / ``unavailable``.
    * ``needles_seen``: bounded needle count.
    * ``method_results``: list of per-method aggregate record dicts.
    * ``failure_category_counts``: aggregate RepoQA fcc.
    * ``network_calls``: count of HTTP calls made.
    * ``failure_reason_category``: real failure category on unavailable.
    """
    fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
    network_calls = 0

    # Step 1: download the RepoQA release asset to in-memory bytes
    # (transient).
    asset_bytes, dl_status, dl_fcc = c5d._download_asset_to_bytes(
        c5d.ASSET_URL
    )
    network_calls += 1
    for k, v in dl_fcc.items():
        if k in fcc:
            fcc[k] += v
    if dl_status != "pass" or asset_bytes is None:
        return {
            "status": "unavailable",
            "needles_seen": 0,
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "asset_download_failed",
        }

    # Step 2: decompress + parse in memory (transient).
    parsed, parse_status, parse_fcc = c5d._decompress_asset(asset_bytes)
    del asset_bytes
    for k, v in parse_fcc.items():
        if k in fcc:
            fcc[k] += v
    if parse_status != "pass" or parsed is None:
        return {
            "status": "unavailable",
            "needles_seen": 0,
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "asset_parse_failed",
        }

    # Step 3: parse needles in memory (transient).
    needles, needle_status, needle_fcc = c5d._parse_repoqa_needles(
        parsed, c5d.DEFAULT_LANGUAGE_FILTER, needle_limit
    )
    del parsed
    for k, v in needle_fcc.items():
        if k in fcc:
            fcc[k] += v
    if needle_status != "pass" or not needles:
        return {
            "status": "unavailable",
            "needles_seen": len(needles),
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": (
                "no_python_needles"
                if needle_status == "unavailable_no_python_needles"
                else "needle_parse_failed"
            ),
        }

    needles_seen = len(needles)

    # Step 4: for each method, run retrieval + scoring across all needles.
    method_results: list[dict[str, Any]] = []
    for method in methods:
        c5e_result = c5e._run_single_method(
            method=method,
            needles=needles,
            needle_limit=needle_limit,
            language_filter=c5d.DEFAULT_LANGUAGE_FILTER,
            openlocus_bin=openlocus_bin,
            eval_dir=eval_dir,
        )
        for k, v in c5e_result.get(
            "failure_category_counts", {}
        ).items():
            if k in fcc:
                fcc[k] += v
        c5e_metrics = c5e_result.get("metrics", {}) or {}
        f1c_metrics = _extract_method_metrics(c5e_metrics)
        if "success_rate" in c5e_metrics:
            f1c_metrics["success_rate"] = _round_metric(
                float(c5e_metrics["success_rate"])
            )
        f1c_metrics["retrieval_utility"] = _compute_utility(f1c_metrics)
        method_results.append(
            {
                "method": method,
                "needles_evaluated": c5e_result.get(
                    "needles_evaluated", 0
                ),
                "needles_successful": c5e_result.get(
                    "needles_successful", 0
                ),
                "needles_failed": c5e_result.get(
                    "needles_failed", 0
                ),
                "metrics": f1c_metrics,
                "failure_category_counts": {
                    c: int(v)
                    for c, v in c5e_result.get(
                        "failure_category_counts", {}
                    ).items()
                    if c in REPOQA_FAILURE_CATEGORIES
                },
                "status": c5e_result.get("status", ""),
            }
        )

    any_success = any(
        r.get("needles_successful", 0) > 0 for r in method_results
    )
    if not any_success:
        return {
            "status": "unavailable",
            "needles_seen": needles_seen,
            "method_results": method_results,
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": "retrieval_failed",
        }

    all_succeed = all(
        r.get("needles_successful", 0) > 0 for r in method_results
    )
    status = "pass" if all_succeed else "partial"
    return {
        "status": status,
        "needles_seen": needles_seen,
        "method_results": method_results,
        "failure_category_counts": fcc,
        "network_calls": network_calls,
        "failure_reason_category": "",
    }


# ---------------------------------------------------------------------------
# Public report builders (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_empty_retrieval_record() -> dict[str, Any]:
    """Build the synthetic ``empty_retrieval`` baseline record.

    ``empty_retrieval`` is the explicit zero-context baseline. No
    retrieval run is required; all metrics and utility are 0 by
    construction. It is a synthetic baseline for the utility formula,
    NOT a retrieval method.
    """
    metrics = {name: 0.0 for name in METRIC_NAMES}
    metrics["retrieval_utility"] = 0.0
    return {
        "method": "empty_retrieval",
        "contextbench_row_count": 0,
        "repoqa_needle_count": 0,
        "metrics": metrics,
    }


def _build_benchmark_result_record(
    *,
    benchmark: str,
    method: str,
    status: str,
    sample_count: int,
    successful_count: int,
    failed_count: int,
    metrics: dict[str, Any],
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a single benchmark-result record (list element)."""
    component_status = _normalize_component_status(status)
    if benchmark == CONTEXTBENCH_BENCHMARK:
        fcc = c5c._public_failure_counts(failure_category_counts)
        return {
            "benchmark": benchmark,
            "method": method,
            "status": component_status,
            "rows_evaluated": int(sample_count),
            "rows_successful": int(successful_count),
            "rows_failed": int(failed_count),
            "metrics": _filter_metrics(metrics),
            "failure_category_counts": fcc,
        }
    # RepoQA.
    fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)
    return {
        "benchmark": benchmark,
        "method": method,
        "status": component_status,
        "needles_evaluated": int(sample_count),
        "needles_successful": int(successful_count),
        "needles_failed": int(failed_count),
        "metrics": _filter_metrics(metrics),
        "failure_category_counts": fcc,
    }


def _normalize_component_status(status: str) -> str:
    """Normalize upstream benchmark statuses into F1-C component buckets."""
    text = str(status).lower()
    if text in {"pass", STATUS_PASS} or text.endswith("_pass"):
        return COMPONENT_STATUS_PASS
    if "partial" in text:
        return COMPONENT_STATUS_PARTIAL
    return COMPONENT_STATUS_UNAVAILABLE


def _filter_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Filter metrics to the F1-C allowlist only (with rounding)."""
    filtered: dict[str, Any] = {}
    for key in METRIC_NAMES:
        if key in metrics:
            val = metrics[key]
            if isinstance(val, bool):
                filtered[key] = 1.0 if val else 0.0
            elif isinstance(val, (int, float)):
                filtered[key] = _round_metric(float(val))
            else:
                filtered[key] = 0.0
    return filtered


def _build_cross_benchmark_method_record(
    *,
    method: str,
    contextbench_sample_count: int,
    repoqa_sample_count: int,
    contextbench_metrics: dict[str, Any],
    repoqa_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build a cross-benchmark method record with weighted-mean metrics.

    Weights are sample counts: ContextBench row count and RepoQA needle
    count. ``empty_retrieval`` has sample_count=0 on both benchmarks;
    its weighted mean is 0 by construction.
    """
    metrics: dict[str, Any] = {}
    total_weight = (
        contextbench_sample_count + repoqa_sample_count
    )
    for name in METRIC_NAMES:
        if total_weight <= 0:
            metrics[name] = 0.0
            continue
        cb_val = float(contextbench_metrics.get(name, 0.0) or 0.0)
        rq_val = float(repoqa_metrics.get(name, 0.0) or 0.0)
        weighted = (
            cb_val * contextbench_sample_count
            + rq_val * repoqa_sample_count
        ) / total_weight
        metrics[name] = _round_metric(weighted)
    return {
        "method": method,
        "contextbench_sample_count": int(contextbench_sample_count),
        "repoqa_sample_count": int(repoqa_sample_count),
        "metrics": metrics,
    }


def _build_input_summary(
    *,
    contextbench_row_limit: int,
    repoqa_needle_limit: int,
    methods: list[str],
    contextbench_rows_fetched: int,
    repoqa_needles_seen: int,
) -> dict[str, Any]:
    """Build the ``input_summary`` block (aggregate counts only)."""
    return {
        "contextbench_row_limit": int(contextbench_row_limit),
        "repoqa_needle_limit": int(repoqa_needle_limit),
        "methods": list(methods),
        "benchmarks": list(BENCHMARKS),
        "contextbench_rows_fetched": int(contextbench_rows_fetched),
        "repoqa_needles_seen": int(repoqa_needles_seen),
        "method_labels": list(ALL_METHOD_LABELS),
        "effect_labels": list(EFFECTS),
        "metric_labels": list(METRIC_NAMES),
        "contextbench_query_mode": CONTEXTBENCH_QUERY_MODE,
        "repoqa_query_mode": REPOQA_QUERY_MODE,
        "repoqa_gold_target_mode": REPOQA_GOLD_TARGET_MODE,
    }


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    contextbench_row_limit_requested: int,
    repoqa_needle_limit_requested: int,
    methods: list[str],
    openlocus_binary_source: str,
    network_mode: str,
    contextbench_rows_fetched: int = 0,
    repoqa_needles_seen: int = 0,
    network_calls: int = 0,
    contextbench_failure_category_counts: dict[str, int]
    | None = None,
    repoqa_failure_category_counts: dict[str, int]
    | None = None,
) -> dict[str, Any]:
    """Build a truthful ``unavailable_with_reason`` report."""
    cb_fcc = c5c._public_failure_counts(
        contextbench_failure_category_counts
    )
    rq_fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
    if repoqa_failure_category_counts:
        for k, v in repoqa_failure_category_counts.items():
            if k in rq_fcc:
                rq_fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["contextbench_rows_read"] = contextbench_rows_fetched > 0
    safe_true["repoqa_needles_read"] = repoqa_needles_seen > 0
    safe_true["openlocus_retrieval_executed"] = False
    safe_true["score_py_metrics_computed"] = False
    safe_true[
        "retrieval_derived_counterfactual_utility_smoke"
    ] = False

    input_summary = _build_input_summary(
        contextbench_row_limit=contextbench_row_limit_requested,
        repoqa_needle_limit=repoqa_needle_limit_requested,
        methods=methods,
        contextbench_rows_fetched=contextbench_rows_fetched,
        repoqa_needles_seen=repoqa_needles_seen,
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": STATUS_UNAVAILABLE,
        "mode": MODE,
        "phase": PHASE,
        "methods_requested": list(methods),
        "methods_allowed": list(ALLOWED_METHODS),
        "baseline_method": BASELINE_METHOD,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_limit_requested": (
            contextbench_row_limit_requested
        ),
        "repoqa_needle_limit_requested": (
            repoqa_needle_limit_requested
        ),
        "contextbench_rows_fetched": contextbench_rows_fetched,
        "repoqa_needles_seen": repoqa_needles_seen,
        "methods_count": len(methods),
        "methods_attempted": len(methods),
        "methods_successful": 0,
        "methods_succeeded": 0,
        "methods_failed": len(methods),
        "input_summary": input_summary,
        "benchmark_results": [],
        "cross_benchmark_method_results": [],
        "counterfactual_effects": [],
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "contextbench_failure_category_counts": cb_fcc,
        "repoqa_failure_category_counts": rq_fcc,
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": SELF_TEST_CHECKS_TOTAL,
        "self_test_checks_passed": (
            SELF_TEST_CHECKS_TOTAL if self_test_passed else 0
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "method_winner_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "is_true_e_s_calibration": False,
            "signal_strength": (
                "cross_benchmark_retrieval_derived_utility_smoke_unavailable"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _f1c_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    contextbench_row_limit_requested: int,
    repoqa_needle_limit_requested: int,
    methods: list[str],
    contextbench_result: dict[str, Any],
    repoqa_result: dict[str, Any],
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
) -> dict[str, Any]:
    """Build a pass/partial cross-benchmark report."""
    cb_fcc = c5c._public_failure_counts(
        contextbench_result.get("failure_category_counts", {})
    )
    rq_fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
    for k, v in repoqa_result.get(
        "failure_category_counts", {}
    ).items():
        if k in rq_fcc:
            rq_fcc[k] = int(v)

    contextbench_rows_fetched = int(
        contextbench_result.get("rows_fetched", 0)
    )
    repoqa_needles_seen = int(
        repoqa_result.get("needles_seen", 0)
    )

    # Build benchmark_results (per benchmark x per method).
    benchmark_results: list[dict[str, Any]] = []
    cb_method_results = contextbench_result.get("method_results", [])
    rq_method_results = repoqa_result.get("method_results", [])
    cb_status = contextbench_result.get("status", "unavailable")
    rq_status = repoqa_result.get("status", "unavailable")
    for rec in cb_method_results:
        benchmark_results.append(
            _build_benchmark_result_record(
                benchmark=CONTEXTBENCH_BENCHMARK,
                method=rec["method"],
                status=rec.get("status", cb_status),
                sample_count=rec.get("rows_evaluated", 0),
                successful_count=rec.get("rows_successful", 0),
                failed_count=rec.get("rows_failed", 0),
                metrics=rec.get("metrics", {}),
                failure_category_counts=rec.get(
                    "failure_category_counts", {}
                ),
            )
        )
    for rec in rq_method_results:
        benchmark_results.append(
            _build_benchmark_result_record(
                benchmark=REPOQA_BENCHMARK,
                method=rec["method"],
                status=rec.get("status", rq_status),
                sample_count=rec.get("needles_evaluated", 0),
                successful_count=rec.get("needles_successful", 0),
                failed_count=rec.get("needles_failed", 0),
                metrics=rec.get("metrics", {}),
                failure_category_counts=rec.get(
                    "failure_category_counts", {}
                ),
            )
        )

    # Build cross_benchmark_method_results (per method, weighted mean
    # across benchmarks). Include the synthetic empty_retrieval
    # baseline at position 0.
    cb_metrics_by_method = {
        r["method"]: r.get("metrics", {})
        for r in cb_method_results
    }
    rq_metrics_by_method = {
        r["method"]: r.get("metrics", {})
        for r in rq_method_results
    }
    cb_sample_count = contextbench_rows_fetched
    rq_sample_count = repoqa_needles_seen

    cross_benchmark_method_results: list[dict[str, Any]] = [
        _build_cross_benchmark_method_record(
            method="empty_retrieval",
            contextbench_sample_count=0,
            repoqa_sample_count=0,
            contextbench_metrics={},
            repoqa_metrics={},
        )
    ]
    for method in methods:
        cross_benchmark_method_results.append(
            _build_cross_benchmark_method_record(
                method=method,
                contextbench_sample_count=cb_sample_count,
                repoqa_sample_count=rq_sample_count,
                contextbench_metrics=cb_metrics_by_method.get(
                    method, {}
                ),
                repoqa_metrics=rq_metrics_by_method.get(method, {}),
            )
        )

    # Compute counterfactual effects from the cross-benchmark weighted
    # means.
    counterfactual_effects = _compute_counterfactual_effects(
        cross_benchmark_method_results
    )

    # Determine overall F1-C status:
    # * pass: both benchmarks pass AND bm25 succeeds on both.
    # * partial_with_exclusions: at least one benchmark passes AND bm25
    #   succeeds on at least one benchmark.
    # * unavailable_with_reason: neither benchmark passes / bm25 fails
    #   everywhere.
    cb_pass = cb_status == "pass"
    rq_pass = rq_status == "pass"
    cb_bm25_ok = any(
        r.get("method") == "bm25"
        and r.get("rows_successful", 0) > 0
        for r in cb_method_results
    )
    rq_bm25_ok = any(
        r.get("method") == "bm25"
        and r.get("needles_successful", 0) > 0
        for r in rq_method_results
    )

    if cb_pass and rq_pass and cb_bm25_ok and rq_bm25_ok:
        status = STATUS_PASS
    elif (cb_pass or rq_pass) and (cb_bm25_ok or rq_bm25_ok):
        status = STATUS_PARTIAL
    else:
        # Build unavailable report instead.
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            contextbench_row_limit_requested=(
                contextbench_row_limit_requested
            ),
            repoqa_needle_limit_requested=(
                repoqa_needle_limit_requested
            ),
            methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            contextbench_rows_fetched=contextbench_rows_fetched,
            repoqa_needles_seen=repoqa_needles_seen,
            network_calls=network_calls,
            contextbench_failure_category_counts=cb_fcc,
            repoqa_failure_category_counts=rq_fcc,
        )

    methods_successful = sum(
        1
        for r in cb_method_results + rq_method_results
        if (
            r.get("rows_successful", 0) > 0
            or r.get("needles_successful", 0) > 0
        )
    )
    methods_attempted = len(cb_method_results) + len(rq_method_results)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["contextbench_rows_read"] = contextbench_rows_fetched > 0
    safe_true["repoqa_needles_read"] = repoqa_needles_seen > 0
    safe_true["openlocus_retrieval_executed"] = (
        cb_bm25_ok or rq_bm25_ok
    )
    safe_true["score_py_metrics_computed"] = (
        any(r.get("metrics") for r in cb_method_results)
        or any(r.get("metrics") for r in rq_method_results)
    )
    safe_true[
        "retrieval_derived_counterfactual_utility_smoke"
    ] = (cb_bm25_ok or rq_bm25_ok)

    input_summary = _build_input_summary(
        contextbench_row_limit=contextbench_row_limit_requested,
        repoqa_needle_limit=repoqa_needle_limit_requested,
        methods=methods,
        contextbench_rows_fetched=contextbench_rows_fetched,
        repoqa_needles_seen=repoqa_needles_seen,
    )

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
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "contextbench_row_limit_requested": (
            contextbench_row_limit_requested
        ),
        "repoqa_needle_limit_requested": (
            repoqa_needle_limit_requested
        ),
        "contextbench_rows_fetched": contextbench_rows_fetched,
        "repoqa_needles_seen": repoqa_needles_seen,
        "methods_count": len(methods),
        "methods_attempted": methods_attempted,
        "methods_successful": methods_successful,
        "methods_succeeded": methods_successful,
        "methods_failed": max(0, methods_attempted - methods_successful),
        "input_summary": input_summary,
        "benchmark_results": benchmark_results,
        "cross_benchmark_method_results": (
            cross_benchmark_method_results
        ),
        "counterfactual_effects": counterfactual_effects,
        "network_calls": network_calls,
        "provider_calls": 0,
        "contextbench_failure_category_counts": cb_fcc,
        "repoqa_failure_category_counts": rq_fcc,
        **safe_true,
        **DEFAULT_FALSE_FLAGS,
        **LICENSE_FIELDS,
        "self_test_passed": self_test_passed,
        "self_test_checks_total": SELF_TEST_CHECKS_TOTAL,
        "self_test_checks_passed": (
            SELF_TEST_CHECKS_TOTAL if self_test_passed else 0
        ),
        "framing": {
            "external_benchmark_performance_claimed": False,
            "leaderboard_entry_claimed": False,
            "method_winner_claimed": False,
            "promotion_claimed": False,
            "default_change_claimed": False,
            "downstream_agent_value_claimed": False,
            "is_true_e_s_calibration": False,
            "signal_strength": (
                "cross_benchmark_retrieval_derived_utility_smoke_aggregate_only"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _f1c_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


# ---------------------------------------------------------------------------
# Cross-benchmark network smoke runner.
# ---------------------------------------------------------------------------


def _run_cross_benchmark_smoke(
    *,
    contextbench_row_limit: int,
    repoqa_needle_limit: int,
    methods: list[str],
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
) -> dict[str, Any]:
    """Run the real cross-benchmark network smoke.

    Reruns real bounded external data for both ContextBench and RepoQA
    (does NOT combine existing C5 aggregate artifacts).
    """
    # ContextBench real run.
    cb_result = _run_contextbench_matrix(
        row_limit=contextbench_row_limit,
        methods=methods,
        openlocus_bin=openlocus_bin,
        openlocus_binary_source=openlocus_binary_source,
        eval_dir=eval_dir,
    )
    # RepoQA real run.
    rq_result = _run_repoqa_matrix(
        needle_limit=repoqa_needle_limit,
        methods=methods,
        openlocus_bin=openlocus_bin,
        openlocus_binary_source=openlocus_binary_source,
        eval_dir=eval_dir,
    )

    network_calls = int(cb_result.get("network_calls", 0)) + int(
        rq_result.get("network_calls", 0)
    )

    # If neither benchmark produced any real data, build unavailable.
    cb_fetched = int(cb_result.get("rows_fetched", 0))
    rq_seen = int(rq_result.get("needles_seen", 0))
    if cb_fetched == 0 and rq_seen == 0:
        # Pick the more-specific failure reason.
        cb_reason = cb_result.get(
            "failure_reason_category", "network_fetch_failed"
        )
        rq_reason = rq_result.get(
            "failure_reason_category", "asset_download_failed"
        )
        reason = cb_reason or rq_reason or "unexpected_exception"
        return _build_unavailable_report(
            reason,
            self_test_passed=self_test_passed,
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source=openlocus_binary_source,
            network_mode=network_mode,
            contextbench_rows_fetched=cb_fetched,
            repoqa_needles_seen=rq_seen,
            network_calls=network_calls,
            contextbench_failure_category_counts=cb_result.get(
                "failure_category_counts", {}
            ),
            repoqa_failure_category_counts=rq_result.get(
                "failure_category_counts", {}
            ),
        )

    return _build_pass_report(
        self_test_passed=self_test_passed,
        contextbench_row_limit_requested=contextbench_row_limit,
        repoqa_needle_limit_requested=repoqa_needle_limit,
        methods=methods,
        contextbench_result=cb_result,
        repoqa_result=rq_result,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
    )


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic data).
# ---------------------------------------------------------------------------


def _build_synthetic_method_metrics(
    method: str = "bm25",
) -> dict[str, Any]:
    """Build synthetic per-method metrics for self-test (aggregate only)."""
    base = {
        "file_recall@10": 0.5,
        "mrr": 0.3,
        "span_f0.5@10": 0.2,
        "success_rate": 1.0,
    }
    if method == "regex":
        base = {
            "file_recall@10": 0.2,
            "mrr": 0.15,
            "span_f0.5@10": 0.05,
            "success_rate": 0.6,
        }
    elif method == "symbol":
        base = {
            "file_recall@10": 0.4,
            "mrr": 0.25,
            "span_f0.5@10": 0.1,
            "success_rate": 0.8,
        }
    elif method == "empty_retrieval":
        base = {
            "file_recall@10": 0.0,
            "mrr": 0.0,
            "span_f0.5@10": 0.0,
            "success_rate": 0.0,
        }
    metrics = dict(base)
    metrics["retrieval_utility"] = _compute_utility(metrics)
    return metrics


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all F1-C self-test groups (no network)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_unavailable_report(
        "network_fetch_failed",
        self_test_passed=True,
        contextbench_row_limit_requested=(
            CONTEXTBENCH_ROW_LIMIT_DEFAULT
        ),
        repoqa_needle_limit_requested=REPOQA_NEEDLE_LIMIT_DEFAULT,
        methods=list(ALLOWED_METHODS),
        openlocus_binary_source="missing",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "schema_version_correct",
            skeleton["schema_version"] == SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "claim_level_correct",
            skeleton["claim_level"] == CLAIM_LEVEL,
        )
    )
    checks.append(
        _check("mode_correct", skeleton["mode"] == MODE)
    )
    checks.append(
        _check("phase_correct", skeleton["phase"] == PHASE)
    )
    checks.append(
        _check(
            "generated_by_correct",
            skeleton["generated_by"] == GENERATED_BY,
        )
    )
    checks.append(
        _check(
            "status_unavailable_when_no_network",
            skeleton["status"] == STATUS_UNAVAILABLE,
        )
    )

    # --- Group 2: Safe true flags. ---
    for flag in SAFE_TRUE_FLAGS:
        checks.append(
            _check(
                f"safe_true_{flag}_present",
                flag in skeleton,
            )
        )
    checks.append(
        _check(
            "diagnostic_only_true",
            skeleton.get("diagnostic_only") is True,
        )
    )
    checks.append(
        _check(
            "aggregate_only_true",
            skeleton.get("aggregate_only_public_artifact") is True,
        )
    )
    checks.append(
        _check(
            "retrieval_smoke_false_when_unavailable",
            skeleton.get(
                "retrieval_derived_counterfactual_utility_smoke"
            )
            is False,
        )
    )
    checks.append(
        _check(
            "contextbench_rows_read_false_when_unavailable",
            skeleton.get("contextbench_rows_read") is False,
        )
    )
    checks.append(
        _check(
            "repoqa_needles_read_false_when_unavailable",
            skeleton.get("repoqa_needles_read") is False,
        )
    )

    # --- Group 3: No-claim flags false. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"default_false_{flag}",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 4: Methods / effects / metrics are fixed allowlists. ---
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
    checks.append(
        _check(
            "default_methods_exact",
            list(DEFAULT_METHODS) == ["bm25", "regex", "symbol"],
        )
    )
    checks.append(
        _check(
            "all_method_labels_include_empty_retrieval",
            "empty_retrieval" in ALL_METHOD_LABELS,
        )
    )
    checks.append(
        _check(
            "effects_are_fixed_allowlist",
            tuple(skeleton["input_summary"]["effect_labels"]) == EFFECTS,
        )
    )
    checks.append(
        _check(
            "metrics_are_fixed_allowlist",
            tuple(
                skeleton["input_summary"]["metric_labels"]
            )
            == METRIC_NAMES,
        )
    )
    checks.append(
        _check(
            "benchmarks_are_fixed_allowlist",
            tuple(skeleton["input_summary"]["benchmarks"])
            == BENCHMARKS,
        )
    )
    for effect in EFFECTS:
        checks.append(
            _check(
                f"effect_present_{effect}",
                effect in skeleton["input_summary"]["effect_labels"],
            )
        )
    for metric in METRIC_NAMES:
        checks.append(
            _check(
                f"metric_present_{metric}",
                metric in skeleton["input_summary"]["metric_labels"],
            )
        )

    # --- Group 5: Method parser. ---
    try:
        parse_methods("bm25,unknown,symbol")
        checks.append(_check("method_parser_rejects_unknown", False))
    except MethodConfigError:
        checks.append(_check("method_parser_rejects_unknown", True))

    try:
        parse_methods("vector")
        checks.append(
            _check("method_parser_rejects_unknown_single", False)
        )
    except MethodConfigError:
        checks.append(
            _check("method_parser_rejects_unknown_single", True)
        )

    parsed = parse_methods("bm25,bm25,regex,regex,symbol,symbol")
    checks.append(
        _check(
            "method_parser_dedups_duplicates",
            parsed == ["bm25", "regex", "symbol"],
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
            parse_methods("bm25,,regex,,symbol")
            == ["bm25", "regex", "symbol"],
        )
    )

    try:
        parse_methods("bm25,text,symbol")
        checks.append(
            _check("method_parser_rejects_text_method", False)
        )
    except MethodConfigError:
        checks.append(
            _check("method_parser_rejects_text_method", True)
        )

    # --- Group 6: Row/needle limit hard caps. ---
    checks.append(
        _check(
            "contextbench_row_limit_default_20",
            CONTEXTBENCH_ROW_LIMIT_DEFAULT == 20,
        )
    )
    checks.append(
        _check(
            "contextbench_row_limit_hard_cap_20",
            CONTEXTBENCH_ROW_LIMIT_HARD_CAP == 20,
        )
    )
    checks.append(
        _check(
            "contextbench_row_limit_cap_enforced_at_20",
            _validate_contextbench_row_limit(100) == 20,
        )
    )
    checks.append(
        _check(
            "contextbench_row_limit_passes_through_at_20",
            _validate_contextbench_row_limit(20) == 20,
        )
    )
    try:
        _validate_contextbench_row_limit(0)
        checks.append(
            _check("contextbench_row_limit_rejects_zero", False)
        )
    except SystemExit:
        checks.append(
            _check("contextbench_row_limit_rejects_zero", True)
        )

    checks.append(
        _check(
            "repoqa_needle_limit_default_10",
            REPOQA_NEEDLE_LIMIT_DEFAULT == 10,
        )
    )
    checks.append(
        _check(
            "repoqa_needle_limit_hard_cap_10",
            REPOQA_NEEDLE_LIMIT_HARD_CAP == 10,
        )
    )
    checks.append(
        _check(
            "repoqa_needle_limit_cap_enforced_at_10",
            _validate_repoqa_needle_limit(100) == 10,
        )
    )
    checks.append(
        _check(
            "repoqa_needle_limit_passes_through_at_10",
            _validate_repoqa_needle_limit(10) == 10,
        )
    )
    try:
        _validate_repoqa_needle_limit(0)
        checks.append(
            _check("repoqa_needle_limit_rejects_zero", False)
        )
    except SystemExit:
        checks.append(
            _check("repoqa_needle_limit_rejects_zero", True)
        )

    # --- Group 7: Records-shaped containers. ---
    checks.append(
        _check(
            "benchmark_results_is_list",
            isinstance(skeleton["benchmark_results"], list),
        )
    )
    checks.append(
        _check(
            "cross_benchmark_method_results_is_list",
            isinstance(
                skeleton["cross_benchmark_method_results"], list
            ),
        )
    )
    checks.append(
        _check(
            "counterfactual_effects_is_list",
            isinstance(skeleton["counterfactual_effects"], list),
        )
    )
    checks.append(
        _check(
            "no_dynamic_dict_mirror_for_methods",
            not any(
                isinstance(v, dict)
                and all(
                    isinstance(k, str) and k in ALL_METHOD_LABELS
                    for k in v.keys()
                )
                for v in [
                    skeleton.get("cross_benchmark_method_results")
                ]
                if isinstance(v, dict)
            ),
        )
    )

    # --- Group 8: Utility computation. ---
    empty_metrics = _extract_method_metrics(None)
    checks.append(
        _check(
            "empty_retrieval_metrics_zero",
            all(v == 0.0 for v in empty_metrics.values()),
        )
    )
    checks.append(
        _check(
            "empty_retrieval_utility_zero",
            empty_metrics["retrieval_utility"] == 0.0,
        )
    )
    # Zero file_recall -> miss_penalty 0.25 -> utility = 0 + 0 + 0 - 0.25 = -0.25.
    zero_recall_metrics = {
        "file_recall@10": 0.0,
        "mrr": 0.0,
        "span_f0.5@10": 0.0,
        "success_rate": 0.0,
    }
    zero_utility = _compute_utility(zero_recall_metrics)
    checks.append(
        _check(
            "zero_recall_has_miss_penalty",
            zero_utility == -0.25,
        )
    )
    # Nonzero file_recall -> no miss_penalty.
    nonzero_metrics = {
        "file_recall@10": 0.5,
        "mrr": 0.4,
        "span_f0.5@10": 0.2,
        "success_rate": 1.0,
    }
    nonzero_utility = _compute_utility(nonzero_metrics)
    expected = round(
        0.5 + MRR_WEIGHT * 0.4 + SPAN_F_WEIGHT * 0.2 - 0.0, 6
    )
    checks.append(
        _check(
            "nonzero_recall_no_miss_penalty",
            nonzero_utility == expected,
        )
    )
    # Extract from synthetic score metrics.
    synth_score = {
        "file_recall@10": 0.5,
        "mrr": 0.3,
        "span_f0.5@10": 0.2,
        "success_rate": 1.0,
    }
    extracted = _extract_method_metrics(synth_score)
    checks.append(
        _check(
            "extract_metrics_from_score",
            extracted["file_recall@10"] == 0.5
            and extracted["mrr"] == 0.3
            and extracted["success_rate"] == 1.0,
        )
    )
    checks.append(
        _check(
            "extract_metrics_computes_utility",
            extracted["retrieval_utility"]
            == round(
                0.5 + MRR_WEIGHT * 0.3 + SPAN_F_WEIGHT * 0.2 - 0.0, 6
            ),
        )
    )
    # Missing metric -> 0.0.
    partial_score = {"file_recall@10": 0.7}
    extracted_partial = _extract_method_metrics(partial_score)
    checks.append(
        _check(
            "missing_metric_defaults_zero",
            extracted_partial["mrr"] == 0.0
            and extracted_partial["file_recall@10"] == 0.7,
        )
    )

    # --- Group 9: Aggregation. ---
    per_row = [
        {
            "file_recall@10": 0.5,
            "mrr": 0.3,
            "span_f0.5@10": 0.2,
            "success_rate": 1.0,
            "retrieval_utility": 0.65,
        },
        {
            "file_recall@10": 1.0,
            "mrr": 0.6,
            "span_f0.5@10": 0.4,
            "success_rate": 1.0,
            "retrieval_utility": 1.3,
        },
    ]
    agg = _aggregate_method_metrics(per_row)
    checks.append(
        _check(
            "aggregate_row_count_correct",
            agg["row_count"] == 2,
        )
    )
    checks.append(
        _check(
            "aggregate_mean_correct",
            agg["file_recall@10"] == 0.75 and agg["mrr"] == 0.45,
        )
    )
    checks.append(
        _check(
            "aggregate_utility_mean_correct",
            agg["retrieval_utility"] == 0.975,
        )
    )

    # --- Group 10: Cross-benchmark weighted means. ---
    # Build synthetic pass report for cross-benchmark record checks.
    cb_metrics = _build_synthetic_method_metrics("bm25")
    rq_metrics = _build_synthetic_method_metrics("bm25")
    # Use different sample counts to verify weighting.
    cb_count = 20
    rq_count = 10
    cross_rec = _build_cross_benchmark_method_record(
        method="bm25",
        contextbench_sample_count=cb_count,
        repoqa_sample_count=rq_count,
        contextbench_metrics=cb_metrics,
        repoqa_metrics=rq_metrics,
    )
    # Same metrics on both benchmarks -> weighted mean equals metric.
    checks.append(
        _check(
            "cross_benchmark_weighted_mean_equal_metrics",
            cross_rec["metrics"]["file_recall@10"] == 0.5,
        )
    )
    # Different metrics -> weighted by sample counts.
    cb_metrics2 = {
        "file_recall@10": 1.0,
        "mrr": 0.5,
        "span_f0.5@10": 0.4,
        "success_rate": 1.0,
        "retrieval_utility": 1.3,
    }
    rq_metrics2 = {
        "file_recall@10": 0.0,
        "mrr": 0.0,
        "span_f0.5@10": 0.0,
        "success_rate": 0.0,
        "retrieval_utility": -0.25,
    }
    cross_rec2 = _build_cross_benchmark_method_record(
        method="bm25",
        contextbench_sample_count=cb_count,
        repoqa_sample_count=rq_count,
        contextbench_metrics=cb_metrics2,
        repoqa_metrics=rq_metrics2,
    )
    expected_recall = round(
        (1.0 * 20 + 0.0 * 10) / 30, 6
    )
    checks.append(
        _check(
            "cross_benchmark_weighted_mean_different_metrics",
            cross_rec2["metrics"]["file_recall@10"]
            == expected_recall,
        )
    )
    # empty_retrieval: sample counts 0 -> all metrics 0.
    empty_cross = _build_cross_benchmark_method_record(
        method="empty_retrieval",
        contextbench_sample_count=0,
        repoqa_sample_count=0,
        contextbench_metrics={},
        repoqa_metrics={},
    )
    checks.append(
        _check(
            "empty_retrieval_cross_benchmark_zero",
            all(
                v == 0.0
                for k, v in empty_cross["metrics"].items()
            ),
        )
    )

    # --- Group 11: Counterfactual effects. ---
    cross_results = [
        _build_cross_benchmark_method_record(
            method="empty_retrieval",
            contextbench_sample_count=0,
            repoqa_sample_count=0,
            contextbench_metrics={},
            repoqa_metrics={},
        ),
        _build_cross_benchmark_method_record(
            method="bm25",
            contextbench_sample_count=2,
            repoqa_sample_count=2,
            contextbench_metrics=cb_metrics,
            repoqa_metrics=rq_metrics,
        ),
        _build_cross_benchmark_method_record(
            method="regex",
            contextbench_sample_count=2,
            repoqa_sample_count=2,
            contextbench_metrics=_build_synthetic_method_metrics(
                "regex"
            ),
            repoqa_metrics=_build_synthetic_method_metrics("regex"),
        ),
        _build_cross_benchmark_method_record(
            method="symbol",
            contextbench_sample_count=2,
            repoqa_sample_count=2,
            contextbench_metrics=_build_synthetic_method_metrics(
                "symbol"
            ),
            repoqa_metrics=_build_synthetic_method_metrics("symbol"),
        ),
    ]
    effects = _compute_counterfactual_effects(cross_results)
    checks.append(
        _check(
            "effects_records_shaped",
            all(
                set(e.keys())
                == {
                    "effect_name",
                    "baseline_method",
                    "treatment_method",
                    "metric",
                    "delta",
                }
                for e in effects
            ),
        )
    )
    checks.append(
        _check(
            "effects_count_correct",
            len(effects) == len(EFFECTS) * len(METRIC_NAMES),
        )
    )
    # bm25_vs_empty: bm25 utility - empty utility = 0.65 - 0.0.
    bm25_effect = next(
        e
        for e in effects
        if e["effect_name"] == "bm25_vs_empty"
        and e["metric"] == "retrieval_utility"
    )
    expected_bm25_utility = cb_metrics["retrieval_utility"]
    checks.append(
        _check(
            "bm25_vs_empty_utility_delta_correct",
            bm25_effect["delta"] == expected_bm25_utility,
        )
    )
    # regex_vs_bm25: regex utility - bm25 utility.
    regex_effect = next(
        e
        for e in effects
        if e["effect_name"] == "regex_vs_bm25"
        and e["metric"] == "retrieval_utility"
    )
    expected_regex_delta = round(
        _build_synthetic_method_metrics("regex")[
            "retrieval_utility"
        ]
        - cb_metrics["retrieval_utility"],
        6,
    )
    checks.append(
        _check(
            "regex_vs_bm25_utility_delta_correct",
            regex_effect["delta"] == expected_regex_delta,
        )
    )

    # --- Group 12: Failure categories kept separate. ---
    checks.append(
        _check(
            "contextbench_failure_categories_separate_from_repoqa",
            CONTEXTBENCH_FAILURE_CATEGORIES
            is not REPOQA_FAILURE_CATEGORIES
            and set(CONTEXTBENCH_FAILURE_CATEGORIES)
            != set(REPOQA_FAILURE_CATEGORIES),
        )
    )
    # ContextBench uses label_context_parse_failed (renamed from
    # gold_context_parse_failed).
    checks.append(
        _check(
            "contextbench_uses_label_context_parse_failed",
            "label_context_parse_failed"
            in CONTEXTBENCH_FAILURE_CATEGORIES,
        )
    )
    checks.append(
        _check(
            "contextbench_omits_gold_context_parse_failed",
            "gold_context_parse_failed"
            not in CONTEXTBENCH_FAILURE_CATEGORIES,
        )
    )
    # RepoQA uses its own asset/needle categories.
    checks.append(
        _check(
            "repoqa_uses_asset_download_failed",
            "asset_download_failed" in REPOQA_FAILURE_CATEGORIES,
        )
    )
    checks.append(
        _check(
            "repoqa_uses_needle_parse_failed",
            "needle_parse_failed" in REPOQA_FAILURE_CATEGORIES,
        )
    )
    # Unavailable report keeps both fcc containers separate.
    checks.append(
        _check(
            "unavailable_has_contextbench_failure_category_counts",
            "contextbench_failure_category_counts" in skeleton,
        )
    )
    checks.append(
        _check(
            "unavailable_has_repoqa_failure_category_counts",
            "repoqa_failure_category_counts" in skeleton,
        )
    )

    # --- Group 13: Scanner rejections. ---
    checks.append(
        _check(
            "scanner_rejects_repo_url",
            bool(_scan_f1c({"leaked": "https://github.com/x/y"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_f1c({"leaked_file": "target.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha",
            bool(_scan_f1c({"leaked": "a" * 40})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug",
            bool(_scan_f1c({"leaked": "astropy/astropy"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_task_id_key",
            bool(_scan_f1c({"task_id": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_key",
            bool(_scan_f1c({"query": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_gold_key",
            bool(_scan_f1c({"gold": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_content_sha_key",
            bool(_scan_f1c({"content_sha": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_candidate_key",
            bool(_scan_f1c({"candidate": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_evidence_key",
            bool(_scan_f1c({"evidence": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_winner_key",
            bool(_scan_f1c({"winner": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_best_method_key",
            bool(_scan_f1c({"best_method": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_recommended_default_key",
            bool(_scan_f1c({"recommended_default": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_es_notation_E_primary",
            bool(_scan_f1c({"E_primary": 0.5})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_es_notation_S_support",
            bool(_scan_f1c({"S_support": 0.5})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_model_id_raw_key",
            bool(_scan_f1c({"model_id_raw": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_routing_prefix_key",
            bool(_scan_f1c({"routing_prefix": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_routing_prefix_value",
            bool(
                _scan_f1c(
                    {"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_url_value",
            bool(_scan_f1c({"leaked": "https://example.com"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path",
            bool(_scan_f1c({"leaked": "/tmp/f1c_smoke_0"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_stdout_key",
            bool(_scan_f1c({"stdout": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_provider_key",
            bool(_scan_f1c({"api_key": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_sentinel",
            bool(_scan_f1c({"leaked": _SECRET_SENTINEL})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_key",
            bool(_scan_f1c({"repo": "astropy/astropy"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha_key",
            bool(_scan_f1c({"commit_sha": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_needle_path_key",
            bool(_scan_f1c({"needle_path": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_needle_description_key",
            bool(_scan_f1c({"needle_description": "abc"})),
        )
    )

    # --- Group 14: Scanner allows legitimate aggregate values. ---
    checks.append(
        _check(
            "scanner_allows_method_name",
            not _scan_f1c({"method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_benchmark_name",
            not _scan_f1c({"benchmark": "contextbench"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_effect_name",
            not _scan_f1c({"effect_name": "bm25_vs_empty"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_metric_name",
            not _scan_f1c({"metric": "file_recall@10"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_query_mode_label",
            not _scan_f1c({"query_mode": "first_paragraph"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_needle_description_label",
            not _scan_f1c({"query_mode": "needle_description"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_needle_path_line_range_label",
            not _scan_f1c(
                {"gold_target_mode": "needle_path_line_range"}
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_benchmark_results_records",
            not _scan_f1c(
                {
                    "benchmark_results": [
                        {
                            "benchmark": "contextbench",
                            "method": "bm25",
                            "metrics": {"mrr": 0.5},
                            "failure_category_counts": {},
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_cross_benchmark_method_results_records",
            not _scan_f1c(
                {
                    "cross_benchmark_method_results": [
                        {
                            "method": "bm25",
                            "metrics": {"mrr": 0.5},
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_counterfactual_effects_records",
            not _scan_f1c(
                {
                    "counterfactual_effects": [
                        {
                            "effect_name": "bm25_vs_empty",
                            "baseline_method": "empty_retrieval",
                            "treatment_method": "bm25",
                            "metric": "mrr",
                            "delta": 0.45,
                        }
                    ]
                }
            ),
        )
    )
    # Scanner rejects dict-keyed mirrors.
    checks.append(
        _check(
            "scanner_rejects_benchmark_results_dict",
            bool(
                _scan_f1c(
                    {
                        "benchmark_results": {
                            "contextbench": {"metrics": {}}
                        }
                    }
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_cross_benchmark_method_results_dict",
            bool(
                _scan_f1c(
                    {
                        "cross_benchmark_method_results": {
                            "bm25": {"metrics": {}}
                        }
                    }
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_counterfactual_effects_dict",
            bool(
                _scan_f1c(
                    {
                        "counterfactual_effects": {
                            "bm25_vs_empty": {}
                        }
                    }
                )
            ),
        )
    )

    # --- Group 15: Fail-closed generation. ---
    try:
        _enforce_f1c_no_forbidden(skeleton)
        clean_passes = True
    except SystemExit:
        clean_passes = False
    checks.append(
        _check(
            "fail_closed_clean_report_does_not_raise",
            clean_passes,
        )
    )
    leaked_report = dict(skeleton)
    leaked_report["leaked_path"] = "src/openlocus/lib.rs"
    try:
        _enforce_f1c_no_forbidden(leaked_report)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(
        _check("fail_closed_raises_on_leak", leak_raises)
    )
    leaked_report2 = dict(skeleton)
    leaked_report2["winner"] = "bm25"
    try:
        _enforce_f1c_no_forbidden(leaked_report2)
        winner_raises = False
    except SystemExit:
        winner_raises = True
    checks.append(
        _check("fail_closed_raises_on_winner", winner_raises)
    )
    leaked_report3 = dict(skeleton)
    leaked_report3["E_primary"] = 0.5
    try:
        _enforce_f1c_no_forbidden(leaked_report3)
        es_raises = False
    except SystemExit:
        es_raises = True
    checks.append(
        _check("fail_closed_raises_on_es_notation", es_raises)
    )
    failed_report = dict(skeleton)
    failed_report["self_test_passed"] = False
    try:
        _refuse_on_self_test_failure(failed_report)
        refuse_failed_raises = False
    except SystemExit:
        refuse_failed_raises = True
    checks.append(
        _check(
            "refuse_on_self_test_failure_raises",
            refuse_failed_raises,
        )
    )

    # --- Group 16: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_report_forbidden_scan_clean",
            skeleton["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 17: Build a synthetic pass report and verify shape. ---
    cb_method_results = [
        {
            "method": "bm25",
            "status": c5c.STATUS_PASS,
            "rows_evaluated": 20,
            "rows_successful": 20,
            "rows_failed": 0,
            "metrics": _build_synthetic_method_metrics("bm25"),
            "failure_category_counts": {
                c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES
            },
        },
        {
            "method": "regex",
            "status": c5c.STATUS_PASS,
            "rows_evaluated": 20,
            "rows_successful": 20,
            "rows_failed": 0,
            "metrics": _build_synthetic_method_metrics("regex"),
            "failure_category_counts": {
                c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES
            },
        },
        {
            "method": "symbol",
            "status": c5c.STATUS_PASS,
            "rows_evaluated": 20,
            "rows_successful": 20,
            "rows_failed": 0,
            "metrics": _build_synthetic_method_metrics("symbol"),
            "failure_category_counts": {
                c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES
            },
        },
    ]
    rq_method_results = [
        {
            "method": "bm25",
            "status": c5e.STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("bm25"),
            "failure_category_counts": {
                c: 0 for c in REPOQA_FAILURE_CATEGORIES
            },
        },
        {
            "method": "regex",
            "status": c5e.STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("regex"),
            "failure_category_counts": {
                c: 0 for c in REPOQA_FAILURE_CATEGORIES
            },
        },
        {
            "method": "symbol",
            "status": c5e.STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("symbol"),
            "failure_category_counts": {
                c: 0 for c in REPOQA_FAILURE_CATEGORIES
            },
        },
    ]
    cb_result_synth = {
        "status": "pass",
        "rows_fetched": 20,
        "method_results": cb_method_results,
        "failure_category_counts": {
            c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES
        },
        "network_calls": 1,
        "failure_reason_category": "",
    }
    rq_result_synth = {
        "status": "pass",
        "needles_seen": 10,
        "method_results": rq_method_results,
        "failure_category_counts": {
            c: 0 for c in REPOQA_FAILURE_CATEGORIES
        },
        "network_calls": 1,
        "failure_reason_category": "",
    }
    pass_report = _build_pass_report(
        self_test_passed=True,
        contextbench_row_limit_requested=20,
        repoqa_needle_limit_requested=10,
        methods=["bm25", "regex", "symbol"],
        contextbench_result=cb_result_synth,
        repoqa_result=rq_result_synth,
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=2,
    )
    checks.append(
        _check(
            "pass_report_status_pass",
            pass_report["status"] == STATUS_PASS,
        )
    )
    checks.append(
        _check(
            "pass_report_has_benchmark_results",
            len(pass_report["benchmark_results"]) == 6,
        )
    )
    checks.append(
        _check(
            "pass_report_component_statuses_normalized",
            {
                rec["status"]
                for rec in pass_report["benchmark_results"]
            }
            <= COMPONENT_STATUSES,
        )
    )
    checks.append(
        _check(
            "pass_report_no_upstream_component_status_leak",
            all(
                "contextbench_" not in rec["status"]
                and "repoqa_" not in rec["status"]
                for rec in pass_report["benchmark_results"]
            ),
        )
    )
    checks.append(
        _check(
            "pass_report_has_cross_benchmark_method_results",
            len(pass_report["cross_benchmark_method_results"]) == 4,
        )
    )
    checks.append(
        _check(
            "pass_report_has_counterfactual_effects",
            len(pass_report["counterfactual_effects"])
            == len(EFFECTS) * len(METRIC_NAMES),
        )
    )
    checks.append(
        _check(
            "pass_report_includes_empty_retrieval",
            any(
                r["method"] == "empty_retrieval"
                for r in pass_report[
                    "cross_benchmark_method_results"
                ]
            ),
        )
    )
    checks.append(
        _check(
            "pass_report_forbidden_scan_clean",
            pass_report["forbidden_scan"]["status"] == "pass",
        )
    )
    # ``winner``/``best_method``/``recommended_default`` must NOT
    # appear as dict keys anywhere in the report. (They may appear as
    # substrings of legitimate flag names like ``method_winner_claimed``.)
    def _has_dict_key_anywhere(obj: Any, key: str) -> bool:
        if isinstance(obj, dict):
            if key in obj:
                return True
            for value in obj.values():
                if _has_dict_key_anywhere(value, key):
                    return True
        elif isinstance(obj, list):
            for value in obj:
                if _has_dict_key_anywhere(value, key):
                    return True
        return False

    for forbidden_key in (
        "winner",
        "best_method",
        "recommended_default",
        "E_primary",
        "S_support",
        "model_id_raw",
        "routing_prefix",
    ):
        checks.append(
            _check(
                f"pass_report_no_{forbidden_key}_key",
                not _has_dict_key_anywhere(pass_report, forbidden_key),
            )
        )
    checks.append(
        _check(
            "pass_report_self_scan_clean",
            not _scan_f1c(pass_report),
        )
    )

    # --- Group 18: Partial-with-exclusions status. ---
    # One benchmark fails, other passes + bm25 ok on the passing one.
    cb_partial = {
        "status": "unavailable",
        "rows_fetched": 0,
        "method_results": [],
        "failure_category_counts": {
            c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES
        },
        "network_calls": 1,
        "failure_reason_category": "network_fetch_failed",
    }
    partial_report = _build_pass_report(
        self_test_passed=True,
        contextbench_row_limit_requested=20,
        repoqa_needle_limit_requested=10,
        methods=["bm25", "regex", "symbol"],
        contextbench_result=cb_partial,
        repoqa_result=rq_result_synth,
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=2,
    )
    checks.append(
        _check(
            "partial_report_status_partial_with_exclusions",
            partial_report["status"] == STATUS_PARTIAL,
        )
    )
    checks.append(
        _check(
            "partial_report_forbidden_scan_clean",
            partial_report["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 19: CLI argument surface. ---
    cli_opts = _cli_argument_option_strings()
    checks.append(
        _check("cli_has_self_test_argument", "--self-test" in cli_opts)
    )
    checks.append(_check("cli_has_out_argument", "--out" in cli_opts))
    checks.append(
        _check(
            "cli_has_contextbench_row_limit_argument",
            "--contextbench-row-limit" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_has_repoqa_needle_limit_argument",
            "--repoqa-needle-limit" in cli_opts,
        )
    )
    checks.append(
        _check("cli_has_methods_argument", "--methods" in cli_opts)
    )
    checks.append(
        _check(
            "cli_has_openlocus_argument",
            "--openlocus" in cli_opts,
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
    """Build the F1-C CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "F1-C cross-benchmark retrieval-derived utility smoke "
            "(public aggregate-only artifact; bounded ContextBench "
            "verified 20-row + RepoQA 10-needle Python subsets; "
            "transient /tmp clone + retrieval + score; methods "
            "bm25,regex,symbol only; no provider calls; no raw "
            "rows/queries/repo URLs/commits/gold paths/spans/needle "
            "descriptions/paths/line ranges/generated JSONL/evidence "
            "rows/cloned repos/stdout/stderr/winner/best_method/"
            "recommended_default/E_S notation committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written, no network)",
    )
    ap.add_argument(
        "--contextbench-row-limit",
        type=int,
        default=CONTEXTBENCH_ROW_LIMIT_DEFAULT,
        help=(
            "number of ContextBench verified rows to evaluate per "
            "method (default: "
            f"{CONTEXTBENCH_ROW_LIMIT_DEFAULT}; hard cap "
            f"{CONTEXTBENCH_ROW_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--repoqa-needle-limit",
        type=int,
        default=REPOQA_NEEDLE_LIMIT_DEFAULT,
        help=(
            "number of RepoQA Python needles to evaluate per method "
            "(default: " f"{REPOQA_NEEDLE_LIMIT_DEFAULT}; hard cap "
            f"{REPOQA_NEEDLE_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--methods",
        default=None,
        help=(
            "comma-separated OpenLocus retrieval methods (default: "
            f"{','.join(DEFAULT_METHODS)}; allowed: "
            f"{', '.join(ALLOWED_METHODS)}; duplicates are deduplicated "
            "deterministically; text is NOT allowed in F1-C)"
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


def _cli_argument_option_strings() -> set[str]:
    parser = build_parser()
    strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            strings.add(opt)
    return strings


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
        report = _build_unavailable_report(
            "scanner_self_test_failed",
            self_test_passed=False,
            contextbench_row_limit_requested=args.contextbench_row_limit,
            repoqa_needle_limit_requested=args.repoqa_needle_limit,
            methods=[],
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )
        _write_json(args.out, report)
        sys.exit(1)

    contextbench_row_limit = _validate_contextbench_row_limit(
        args.contextbench_row_limit
    )
    repoqa_needle_limit = _validate_repoqa_needle_limit(
        args.repoqa_needle_limit
    )
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
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_f1c_no_forbidden(report)
        _write_json(out_path, report)
        print(
            f"wrote artifact "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"self_test_passed={report['self_test_passed']}, "
            f"status={report['status']}, "
            f"phase={report['phase']}, "
            f"failure_reason={report['failure_reason_category']})"
        )
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_cross_benchmark_smoke(
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
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
            contextbench_row_limit_requested=contextbench_row_limit,
            repoqa_needle_limit_requested=repoqa_needle_limit,
            methods=methods,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
        )

    _enforce_f1c_no_forbidden(report)
    _refuse_on_self_test_failure(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"methods={report['methods_requested']}, "
        f"contextbench_rows_fetched={report['contextbench_rows_fetched']}, "
        f"repoqa_needles_seen={report['repoqa_needles_seen']})"
    )


if __name__ == "__main__":
    main()
