#!/usr/bin/env python3
"""F1-D Cross-Benchmark Retrieval Utility Robustness Smoke (Public Aggregate-Only).

This module implements the **F1-D cross-benchmark retrieval utility
robustness smoke**. It extends F1-C from point estimates to diagnostic
paired-bootstrap confidence/sign-stability estimates. F1-D reruns real
bounded external-benchmark-shaped retrieval samples (ContextBench
verified 20-row + RepoQA 10-needle Python), intercepts per-unit score
metrics **before aggregation** (in memory or ``/tmp`` only), computes a
fixed retrieval-derived utility proxy per benchmark/method, cross-
benchmark weighted means, and paired bootstrap confidence/sign-stability
statistics for five fixed effects over five metrics.

F1-D is explicitly **not** a downstream utility claim, **not** true
E/S calibration, **not** an external benchmark performance claim, **not**
a leaderboard entry, **not** a promotion/default/runtime/retriever/
pack/backend/EvidenceCore semantic change, and **not** a live/provider
claim. It makes NO provider calls and NO remote provider calls. It
reruns real bounded external data; it does NOT combine existing C5 or
F1-C aggregate artifacts. The bootstrap statistics are diagnostic
robustness estimates, NOT formal external benchmark confidence intervals.

Claim boundary (binding):

* Claim level: ``cross_benchmark_retrieval_utility_robustness_smoke_only``.
* Status enum: ``cross_benchmark_retrieval_robustness_pass`` |
  ``partial`` | ``unavailable_with_reason`` |
  ``fail_forbidden_scan`` | ``fail_schema_contract``.
* Mode: ``bounded_contextbench_repoqa_retrieval_robustness``; phase
  ``F1-D``.

Utility formula (fixed diagnostic proxy; unchanged from F1-C; NOT
downstream solve rate, NOT E/S calibration):

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

where ``file_hit = file_recall@10`` and ``span_f0.5 = span_f0.5@10``.
``empty_retrieval`` is the explicit zero-context baseline (no retrieval
run required; all metrics and utility are 0 by construction).

Bootstrap effects (fixed allowlist; records-shaped only):

* ``bm25_vs_empty``  — (bm25 - empty_retrieval).
* ``regex_vs_empty`` — (regex - empty_retrieval).
* ``symbol_vs_empty`` — (symbol - empty_retrieval).
* ``regex_vs_bm25``  — (regex - bm25).
* ``symbol_vs_bm25`` — (symbol - bm25).

Effects are computed for the cross-benchmark weighted mean of
``retrieval_utility`` and each aggregate metric
(``file_recall@10``, ``mrr``, ``span_f0.5@10``, ``success_rate``,
``retrieval_utility``).

Cross-benchmark resampling preserves benchmark sample counts: within
each bootstrap replicate, ContextBench units are resampled with
replacement to the ContextBench sample count, RepoQA units are
resampled with replacement to the RepoQA needle count, and the
cross-benchmark weighted mean is computed with the original sample
counts as weights.

Public effect record fields: ``effect_name``, ``metric``,
``point_estimate``, ``bootstrap_mean``, ``ci_p05``, ``ci_p50``,
``ci_p95``, ``sign_positive_fraction``, ``sign_negative_fraction``,
``sign_zero_fraction``, ``sample_units``, ``bootstrap_replicates``,
``bootstrap_seed``.

Allowed method labels: ``empty_retrieval``, ``bm25``, ``regex``,
``symbol``. Allowed metrics: ``file_recall@10``, ``mrr``,
``span_f0.5@10``, ``success_rate``, ``retrieval_utility``.

Privacy / license boundary (binding):

* Public artifact/docs/workflow uploads aggregate-only.
* Per-unit metrics exist only in memory or ``/tmp``; the public
  artifact emits aggregate means and bootstrap statistics only.
* No repo names/URLs, commits, task/row/needle IDs, problem statements,
  queries, needle descriptions, gold labels, label paths/spans/line
  ranges, source snippets, generated JSONL, retrieval evidence rows,
  candidate paths/spans/content hashes, stdout/stderr, clone paths, raw
  asset rows, per-row/per-needle metric arrays, row hashes, provider
  fields, raw model/routing prefixes, winner/best/default/recommended
  fields, or E/S calibration notation.
* ContextBench and RepoQA failure categories remain separate; do NOT
  merge incompatible enums.

Network / CI policy (binding):

* Default no-network self-test passes without HuggingFace/GitHub.
* Real smoke requires public network access to HF datasets-server
  (ContextBench) and GitHub (RepoQA asset + repo clones). CI must be
  a separate explicit ``workflow_dispatch`` job with
  ``enable_external_benchmark_network=true``. It must NOT run on
  PR/push by default, must use no provider secrets/vars, no provider
  model env, and must upload only the aggregate F1-D report.
* Network-enabled CI is fail-closed: status pass/partial only,
  ContextBench rows > 0, RepoQA needles > 0, bootstrap record count
  equals effect_count times metric_count, forbidden_scan pass,
  provider_calls=0.

Run::

    python3 -m py_compile eval/f1d_cross_benchmark_retrieval_robustness.py
    python3 eval/f1d_cross_benchmark_retrieval_robustness.py --self-test
    python3 eval/f1d_cross_benchmark_retrieval_robustness.py \\
        --contextbench-row-limit 20 --repoqa-needle-limit 10 \\
        --methods bm25,regex,symbol --bootstrap-replicates 1000 \\
        --out artifacts/f1d_cross_benchmark_retrieval_robustness/\\
f1d_cross_benchmark_retrieval_robustness_report.json

If the network smoke cannot complete in the environment, the default
artifact records truthful ``unavailable_with_reason`` with a real
failure category (no stale/fake pass). Self-test/docs/diff-check still
pass.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse F1-C, C5-C, C5-E, C5-A, and C5-D helpers. The ``eval`` directory
# has no ``__init__.py`` (flat script directory), so we add this file's
# parent to ``sys.path`` and import the modules directly. F1-D does NOT
# import or mutate F1-C/C5-C/C5-E result semantics; it only reuses their
# primitives and reruns real bounded external data.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5_contextbench_verified_performance_smoke as c5a  # noqa: E402
import c5c_contextbench_verified_method_matrix_scale_smoke as c5c  # noqa: E402
import c5d_repoqa_bm25_retrieval_smoke as c5d  # noqa: E402
import c5e_repoqa_method_matrix_smoke as c5e  # noqa: E402
import f1c_cross_benchmark_retrieval_utility as f1c  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (F1-D owned)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "f1d_cross_benchmark_retrieval_robustness.v1"
GENERATED_BY = "eval/f1d_cross_benchmark_retrieval_robustness.py"
CLAIM_LEVEL = "cross_benchmark_retrieval_utility_robustness_smoke_only"
MODE = "bounded_contextbench_repoqa_retrieval_robustness"
PHASE = "F1-D"

STATUS_PASS = "cross_benchmark_retrieval_robustness_pass"
STATUS_PARTIAL = "partial"
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

SELF_TEST_CHECKS_TOTAL = 185

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
    "artifacts/f1d_cross_benchmark_retrieval_robustness/"
    "f1d_cross_benchmark_retrieval_robustness_report.json"
)

# Hard caps. ContextBench default 20; hard cap 20. RepoQA default 10;
# hard cap 10. Bootstrap replicates default 1000; hard cap 2000.
CONTEXTBENCH_ROW_LIMIT_DEFAULT = f1c.CONTEXTBENCH_ROW_LIMIT_DEFAULT
CONTEXTBENCH_ROW_LIMIT_HARD_CAP = f1c.CONTEXTBENCH_ROW_LIMIT_HARD_CAP
REPOQA_NEEDLE_LIMIT_DEFAULT = f1c.REPOQA_NEEDLE_LIMIT_DEFAULT
REPOQA_NEEDLE_LIMIT_HARD_CAP = f1c.REPOQA_NEEDLE_LIMIT_HARD_CAP

BOOTSTRAP_REPLICATES_DEFAULT = 1000
BOOTSTRAP_REPLICATES_HARD_CAP = 2000
BOOTSTRAP_SEED_DEFAULT = 20240621

# Methods / metrics / effects / benchmarks: reused from F1-C (unchanged
# allowlists). F1-D does NOT change these.
ALLOWED_METHODS: tuple[str, ...] = f1c.ALLOWED_METHODS
DEFAULT_METHODS: tuple[str, ...] = f1c.DEFAULT_METHODS
BASELINE_METHOD = f1c.BASELINE_METHOD
ALL_METHOD_LABELS: tuple[str, ...] = f1c.ALL_METHOD_LABELS
BENCHMARKS: tuple[str, ...] = f1c.BENCHMARKS
CONTEXTBENCH_BENCHMARK = f1c.CONTEXTBENCH_BENCHMARK
REPOQA_BENCHMARK = f1c.REPOQA_BENCHMARK
METRIC_NAMES: tuple[str, ...] = f1c.METRIC_NAMES
EFFECT_METHOD_PAIRS: dict[str, tuple[str, str]] = f1c.EFFECT_METHOD_PAIRS
EFFECTS: tuple[str, ...] = f1c.EFFECTS

# Config labels (fixed; reused from F1-C).
CONTEXTBENCH_QUERY_MODE = f1c.CONTEXTBENCH_QUERY_MODE
REPOQA_QUERY_MODE = f1c.REPOQA_QUERY_MODE
REPOQA_GOLD_TARGET_MODE = f1c.REPOQA_GOLD_TARGET_MODE

# Utility formula constants (reused from F1-C; unchanged).
MRR_WEIGHT = f1c.MRR_WEIGHT
SPAN_F_WEIGHT = f1c.SPAN_F_WEIGHT
MISS_PENALTY = f1c.MISS_PENALTY

# Failure categories (kept SEPARATE; reused from F1-C).
CONTEXTBENCH_FAILURE_CATEGORIES: tuple[str, ...] = (
    f1c.CONTEXTBENCH_FAILURE_CATEGORIES
)
REPOQA_FAILURE_CATEGORIES: tuple[str, ...] = f1c.REPOQA_FAILURE_CATEGORIES

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). Exactly these MAY be
# true in the committed public artifact.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "retrieval_utility_robustness_smoke": False,
    "contextbench_rows_read": False,
    "repoqa_needles_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "bootstrap_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# No-claim / no-runtime-change flags (all MUST be false in the committed
# public artifact). F1-D runs NO provider, makes NO remote provider calls,
# proves NO downstream agent value, promotes NO candidate, claims NO E/S
# calibration / external benchmark performance / leaderboard entry / method
# winner / default change, and changes NO runtime/retriever/pack/backend/
# default-policy/EvidenceCore semantics.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = dict(f1c.DEFAULT_FALSE_FLAGS)

# ---------------------------------------------------------------------------
# License / redistribution fields (fixed; reused from F1-C).
# ---------------------------------------------------------------------------

LICENSE_FIELDS: dict[str, Any] = dict(f1c.LICENSE_FIELDS)

# ---------------------------------------------------------------------------
# Public artifact scanner (F1-D owned, strict, fail-closed).
#
# F1-D reuses the F1-C forbidden scanner (which itself combines C5-A/
# C5-C/C5-E scanners) and ADDS F1-D-specific scanners that:
#   * reject F1-C record container names (``benchmark_results``,
#     ``cross_benchmark_method_results``, ``counterfactual_effects``)
#     anywhere — F1-D uses its own container names;
#   * reject per-unit metric array keys (``per_row_metrics``,
#     ``per_needle_metrics``, ``row_metrics``, ``needle_metrics``,
#     ``row_hashes``, ``needle_hashes``) anywhere;
#   * reject the F1-D record containers
#     (``benchmark_method_means``, ``cross_benchmark_method_means``,
#     ``bootstrap_effect_records``) if they are dicts (must be lists of
#     records);
#   * reject the F1-C forbidden recommendation/ES-notation keys (already
#     covered by the reused F1-C scanner).
# ---------------------------------------------------------------------------

# F1-C record container names that F1-D must NEVER emit (F1-D uses its
# own container names). These are forbidden as dict keys anywhere.
F1D_FORBIDDEN_F1C_CONTAINER_KEYS: frozenset[str] = frozenset(
    {
        "benchmark_results",
        "cross_benchmark_method_results",
        "counterfactual_effects",
    }
)

# Per-unit metric array keys that must NEVER appear in the public
# artifact. Per-unit data stays in memory or /tmp only.
F1D_FORBIDDEN_PER_UNIT_KEYS: frozenset[str] = frozenset(
    {
        "per_row_metrics",
        "per_needle_metrics",
        "row_metrics",
        "needle_metrics",
        "row_hashes",
        "needle_hashes",
        "per_unit_metrics",
        "per_unit_utility",
    }
)

# F1-D record containers (must be lists of records, NOT dict-keyed
# mirrors).
F1D_RECORD_CONTAINERS: frozenset[str] = frozenset(
    {
        "benchmark_method_means",
        "cross_benchmark_method_means",
        "bootstrap_effect_records",
    }
)

# F1-D-specific safe VALUE path last-key segments (legitimate categorical
# bucket strings or fixed config labels). The F1-C scanner may flag some
# of these as ``forbidden_field_name_value``; F1-D suppresses those false
# positives.
F1D_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    f1c.F1C_SAFE_VALUE_PATH_LAST_KEYS
    | {
        "effect_name",
        "point_estimate",
        "bootstrap_mean",
        "bootstrap_replicates",
        "bootstrap_seed",
        "ci_p05",
        "ci_p50",
        "ci_p95",
        "sign_positive_fraction",
        "sign_negative_fraction",
        "sign_zero_fraction",
        "sample_units",
        "effect_count",
        "metric_count",
        "bootstrap_record_count",
        "resampling_method",
        "benchmark_method_means",
        "cross_benchmark_method_means",
        "bootstrap_effect_records",
        "bootstrap_summary",
        "sample_count",
        "contextbench_sample_count",
        "repoqa_sample_count",
        "retrieval_utility_robustness_smoke",
        "bootstrap_computed",
    }
)

# Raw model routing prefix pattern (reused from F1-C).
_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)

_SECRET_SENTINEL = c5a._SECRET_SENTINEL
_ROUTING_PREFIX_SENTINEL = "[" + "m" + "k]"


def _path_last_key(path: str) -> str:
    """Extract the last key segment from a dotted JSON path."""
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    """Check if a JSON path ends with a known-safe value key."""
    return _path_last_key(path) in F1D_SAFE_VALUE_PATH_LAST_KEYS


def _scan_f1d_forbidden_keys(obj: Any) -> list[dict[str, Any]]:
    """Scan for F1-D-specific forbidden keys.

    Rejects F1-C record container names and per-unit metric array keys
    anywhere in the object. The reused F1-C scanner already covers
    recommendation fields, ES-notation keys, and C5-A/C5-C/C5-E-shaped
    forbidden keys.
    """
    violations: list[dict[str, Any]] = []

    def _walk(o: Any, path: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                sub_path = f"{path}.{key_str}"
                if key_str in F1D_FORBIDDEN_F1C_CONTAINER_KEYS:
                    violations.append(
                        {
                            "category": "forbidden_f1c_container_key",
                            "path": sub_path,
                        }
                    )
                if key_str in F1D_FORBIDDEN_PER_UNIT_KEYS:
                    violations.append(
                        {
                            "category": "forbidden_per_unit_key",
                            "path": sub_path,
                        }
                    )
                _walk(value, sub_path)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")

    _walk(obj)
    return violations


def _scan_f1d_records_shape(obj: Any) -> list[dict[str, Any]]:
    """Reject F1-D record containers if they are not lists.

    ``benchmark_method_means``, ``cross_benchmark_method_means``, and
    ``bootstrap_effect_records`` must be lists of records (NOT dict-
    keyed mirrors).
    """
    violations: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for container in F1D_RECORD_CONTAINERS:
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


def _scan_f1d(obj: Any) -> list[dict[str, Any]]:
    """Combined F1-D scanner.

    Runs:
    * The F1-C scanner (which combines C5-A/C5-C/C5-E scanners and
      F1-C-specific forbidden keys, record-shape checks, and value-
      pattern checks).
    * F1-D-specific forbidden keys (F1-C container names, per-unit
      metric array keys).
    * F1-D record-shape checks for F1-D containers.

    False positives from the F1-C scanner
    (``forbidden_field_name_value``) are suppressed where a legitimate
    categorical bucket string appears as a value under an F1-D-specific
    safe value path.
    """
    violations: list[dict[str, Any]] = []
    for v in f1c._scan_f1c(obj):
        if v.get("category") == "forbidden_field_name_value" and _is_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    violations.extend(_scan_f1d_forbidden_keys(obj))
    violations.extend(_scan_f1d_records_shape(obj))
    return violations


def _f1d_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the F1-D forbidden scanner and return a sanitized summary."""
    violations = _scan_f1d(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_f1d_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _f1d_forbidden_scan_summary(obj)
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
# Method parser / validator (reused from F1-C; F1-D does not change it)
# ---------------------------------------------------------------------------


# Reuse F1-C's parse_methods and MethodConfigError directly.
parse_methods = f1c.parse_methods
MethodConfigError = f1c.MethodConfigError

_validate_contextbench_row_limit = f1c._validate_contextbench_row_limit
_validate_repoqa_needle_limit = f1c._validate_repoqa_needle_limit


def _validate_bootstrap_replicates(replicates: int) -> int:
    """Validate and cap --bootstrap-replicates to the hard cap (2000)."""
    if not isinstance(replicates, int):
        raise SystemExit("invalid arguments")
    if replicates < 1:
        raise SystemExit("invalid arguments")
    if replicates > BOOTSTRAP_REPLICATES_HARD_CAP:
        return BOOTSTRAP_REPLICATES_HARD_CAP
    return replicates


def _validate_bootstrap_seed(seed: int) -> int:
    """Validate --bootstrap-seed is a non-negative integer."""
    if not isinstance(seed, int):
        raise SystemExit("invalid arguments")
    if seed < 0:
        raise SystemExit("invalid arguments")
    return seed


# ---------------------------------------------------------------------------
# Utility computation (reused from F1-C; formula unchanged).
# ---------------------------------------------------------------------------

# Reuse F1-C's utility computation directly to guarantee formula
# identity.
_compute_utility = f1c._compute_utility
_extract_method_metrics = f1c._extract_method_metrics
_filter_metrics = f1c._filter_metrics


def _extract_per_unit_metrics(
    score_metrics: dict[str, Any] | None,
) -> dict[str, float]:
    """Extract per-unit F1-D metrics from a single score.py result.

    Returns a dict with all 5 F1-D metric names
    (``file_recall@10``, ``mrr``, ``span_f0.5@10``, ``success_rate``,
    ``retrieval_utility``). For ``empty_retrieval`` (no retrieval run),
    all metrics are zero by construction.

    Per-unit ``retrieval_utility`` is computed from the per-unit metric
    values using the F1-C formula (unchanged). The aggregate
    ``retrieval_utility`` is computed from aggregate metric means
    (utility of means), NOT from the mean of per-unit utilities, to
    match F1-C's aggregate semantics.
    """
    return _extract_method_metrics(score_metrics)


# ---------------------------------------------------------------------------
# Per-unit ContextBench matrix runner (mirrors c5c._run_single_method but
# captures per-unit metrics in memory before aggregation; does NOT reuse
# C5-C aggregate artifacts).
# ---------------------------------------------------------------------------


def _run_contextbench_matrix_per_unit(
    *,
    row_limit: int,
    methods: list[str],
    openlocus_bin: str,
    openlocus_binary_source: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run the real ContextBench matrix smoke and capture per-unit metrics.

    Mirrors the C5-C ``_run_single_method`` loop but stores per-unit
    metrics as ``dict[int, dict[str, float]]`` (unit index -> metrics)
    in memory only, before aggregation. Per-unit data is NEVER written
    to disk or committed.

    Returns a dict with:
    * ``status``: ``pass`` / ``partial`` / ``unavailable``.
    * ``rows_fetched``: bounded row count.
    * ``per_unit``: ``{method: {idx: metrics_dict}}`` (in-memory only).
    * ``method_results``: list of per-method aggregate record dicts
      (each with ``method``, ``rows_evaluated``, ``rows_successful``,
      ``rows_failed``, ``metrics``, ``failure_category_counts``).
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
            "per_unit": {},
            "method_results": [],
            "failure_category_counts": fcc,
            "network_calls": network_calls,
            "failure_reason_category": (
                "network_fetch_failed" if not rows else "no_python_rows"
            ),
        }

    rows_fetched = len(rows)

    # Step 2: for each method, run retrieval + scoring across all rows,
    # capturing per-unit metrics before aggregation.
    per_unit: dict[str, dict[int, dict[str, float]]] = {
        m: {} for m in methods
    }
    method_results: list[dict[str, Any]] = []
    for method in methods:
        method_fcc = {c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES}
        rows_evaluated = 0
        rows_successful = 0
        rows_failed = 0

        with tempfile.TemporaryDirectory(
            prefix=f"f1d_cb_{method}_"
        ) as work_root_str:
            work_root = Path(work_root_str)
            tasks_jsonl = work_root / "tasks.jsonl"
            labels_jsonl = work_root / "labels.jsonl"
            run_jsonl = work_root / "run.jsonl"

            for idx, row in enumerate(rows):
                rows_evaluated += 1
                gold_paths, gold_lines, gc_status = (
                    c5a._parse_gold_context(row.get("gold_context"))
                )
                if gc_status != "pass":
                    method_fcc["label_context_parse_failed"] += 1
                    rows_failed += 1
                    continue

                query = c5a._sanitize_query(
                    row.get("problem_statement", ""),
                    c5a.DEFAULT_QUERY_MODE,
                )
                if not query:
                    method_fcc["row_parse_failed"] += 1
                    rows_failed += 1
                    continue

                repo_url = row.get("repo_url", "")
                base_commit = row.get("base_commit", "")
                if (
                    not isinstance(repo_url, str)
                    or not isinstance(base_commit, str)
                    or not repo_url
                    or not base_commit
                ):
                    method_fcc["row_parse_failed"] += 1
                    rows_failed += 1
                    continue

                with tempfile.TemporaryDirectory(
                    prefix=f"f1d_cb_repo_{method}_{idx}_"
                ) as repo_root_str:
                    repo_work_dir = Path(repo_root_str)
                    clone_ok, _, clone_fcc = c5a._clone_and_checkout(
                        repo_url, base_commit, repo_work_dir
                    )
                    for k, v in clone_fcc.items():
                        if k in method_fcc:
                            method_fcc[k] += v
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
                        method_fcc["task_jsonl_write_failed"] += 1
                        rows_failed += 1
                        continue

                    metrics, _, score_fcc = c5a._run_retrieval_and_score(
                        tasks_jsonl=tasks_jsonl,
                        labels_jsonl=labels_jsonl,
                        run_jsonl=run_jsonl,
                        repo_root=repo_root,
                        openlocus_bin=openlocus_bin,
                        method=method,
                        eval_dir=eval_dir,
                    )
                    for k, v in score_fcc.items():
                        if k in method_fcc:
                            method_fcc[k] += v
                    if metrics is None:
                        rows_failed += 1
                        continue

                    # Capture per-unit metrics in memory (NOT to disk).
                    per_unit[method][idx] = _extract_per_unit_metrics(
                        metrics
                    )
                    rows_successful += 1

                try:
                    run_jsonl.unlink()
                except OSError:
                    pass

        for k, v in method_fcc.items():
            if k in fcc:
                fcc[k] += v

        # Build aggregate metrics from per-unit means (utility of means).
        unit_metrics = list(per_unit[method].values())
        agg_metrics = _aggregate_per_unit_means(unit_metrics)
        method_status = (
            c5c.STATUS_PASS
            if rows_successful > 0
            else c5c.STATUS_UNAVAILABLE
        )
        if rows_successful > 0 and rows_failed > 0:
            method_status = c5c.STATUS_PARTIAL

        method_results.append(
            {
                "method": method,
                "status": method_status,
                "rows_evaluated": rows_evaluated,
                "rows_successful": rows_successful,
                "rows_failed": rows_failed,
                "metrics": agg_metrics,
                "failure_category_counts": c5c._public_failure_counts(
                    method_fcc
                ),
            }
        )

    any_success = any(
        r.get("rows_successful", 0) > 0 for r in method_results
    )
    if not any_success:
        return {
            "status": "unavailable",
            "rows_fetched": rows_fetched,
            "per_unit": per_unit,
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
        "per_unit": per_unit,
        "method_results": method_results,
        "failure_category_counts": fcc,
        "network_calls": network_calls,
        "failure_reason_category": "",
    }


# ---------------------------------------------------------------------------
# Per-unit RepoQA matrix runner (mirrors c5e._run_single_method but
# captures per-unit metrics in memory before aggregation; does NOT reuse
# C5-E aggregate artifacts).
# ---------------------------------------------------------------------------


def _run_repoqa_matrix_per_unit(
    *,
    needle_limit: int,
    methods: list[str],
    openlocus_bin: str,
    openlocus_binary_source: str,
    eval_dir: Path,
) -> dict[str, Any]:
    """Run the real RepoQA matrix smoke and capture per-unit metrics.

    Mirrors the C5-E ``_run_single_method`` loop but stores per-unit
    metrics as ``dict[int, dict[str, float]]`` (unit index -> metrics)
    in memory only, before aggregation. Per-unit data is NEVER written
    to disk or committed.

    Returns a dict with:
    * ``status``: ``pass`` / ``partial`` / ``unavailable``.
    * ``needles_seen``: bounded needle count.
    * ``per_unit``: ``{method: {idx: metrics_dict}}`` (in-memory only).
    * ``method_results``: list of per-method aggregate record dicts.
    * ``failure_category_counts``: aggregate RepoQA fcc.
    * ``network_calls``: count of HTTP calls made.
    * ``failure_reason_category``: real failure category on unavailable.
    """
    fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
    network_calls = 0

    # Step 1: download the RepoQA release asset to in-memory bytes.
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
            "per_unit": {},
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
            "per_unit": {},
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
            "per_unit": {},
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

    # Step 4: for each method, run retrieval + scoring across all needles,
    # capturing per-unit metrics before aggregation.
    per_unit: dict[str, dict[int, dict[str, float]]] = {
        m: {} for m in methods
    }
    method_results: list[dict[str, Any]] = []
    for method in methods:
        method_fcc = {c: 0 for c in REPOQA_FAILURE_CATEGORIES}
        needles_evaluated = 0
        needles_successful = 0
        needles_failed = 0

        with tempfile.TemporaryDirectory(
            prefix=f"f1d_rq_{method}_"
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
                    method_fcc["needle_parse_failed"] += 1
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
                    method_fcc["needle_parse_failed"] += 1
                    needles_failed += 1
                    continue

                with tempfile.TemporaryDirectory(
                    prefix=f"f1d_rq_repo_{method}_{idx}_"
                ) as repo_root_str:
                    repo_work_dir = Path(repo_root_str)
                    clone_ok, _, clone_fcc = c5d._clone_and_checkout(
                        repo_url, commit_sha, repo_work_dir
                    )
                    for k, v in clone_fcc.items():
                        if k in method_fcc:
                            method_fcc[k] += v
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
                        method_fcc["task_jsonl_write_failed"] += 1
                        needles_failed += 1
                        continue

                    metrics, _, score_fcc = (
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
                        if k in method_fcc:
                            method_fcc[k] += v
                    if metrics is None:
                        needles_failed += 1
                        continue

                    # Capture per-unit metrics in memory (NOT to disk).
                    per_unit[method][idx] = _extract_per_unit_metrics(
                        metrics
                    )
                    needles_successful += 1

                try:
                    run_jsonl.unlink()
                except OSError:
                    pass

        for k, v in method_fcc.items():
            if k in fcc:
                fcc[k] += v

        # Build aggregate metrics from per-unit means (utility of means).
        unit_metrics = list(per_unit[method].values())
        agg_metrics = _aggregate_per_unit_means(unit_metrics)
        method_status = (
            c5e.STATUS_PASS
            if needles_successful > 0
            else c5e.STATUS_UNAVAILABLE
        )
        if needles_successful > 0 and needles_failed > 0:
            method_status = c5e.STATUS_PARTIAL

        method_results.append(
            {
                "method": method,
                "status": method_status,
                "needles_evaluated": needles_evaluated,
                "needles_successful": needles_successful,
                "needles_failed": needles_failed,
                "metrics": agg_metrics,
                "failure_category_counts": {
                    c: int(v)
                    for c, v in method_fcc.items()
                    if c in REPOQA_FAILURE_CATEGORIES
                },
            }
        )

    any_success = any(
        r.get("needles_successful", 0) > 0 for r in method_results
    )
    if not any_success:
        return {
            "status": "unavailable",
            "needles_seen": needles_seen,
            "per_unit": per_unit,
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
        "per_unit": per_unit,
        "method_results": method_results,
        "failure_category_counts": fcc,
        "network_calls": network_calls,
        "failure_reason_category": "",
    }


# ---------------------------------------------------------------------------
# Aggregation helpers (per-unit means; utility of means for retrieval_utility).
# ---------------------------------------------------------------------------


def _aggregate_per_unit_means(
    per_unit_metrics: list[dict[str, float]],
) -> dict[str, float]:
    """Aggregate per-unit metrics into per-method means.

    For ``file_recall@10``, ``mrr``, ``span_f0.5@10``, ``success_rate``:
    the aggregate is the mean of per-unit values.

    For ``retrieval_utility``: the aggregate is computed from the
    aggregate metric means (utility of means), matching F1-C's aggregate
    semantics. This is NOT the mean of per-unit utilities.
    """
    result: dict[str, float] = {name: 0.0 for name in METRIC_NAMES}
    if not per_unit_metrics:
        result["retrieval_utility"] = _compute_utility(result)
        return result

    n = len(per_unit_metrics)
    for name in METRIC_NAMES:
        if name == "retrieval_utility":
            continue
        values = [
            r[name]
            for r in per_unit_metrics
            if name in r and isinstance(r[name], (int, float))
        ]
        if values:
            result[name] = _round_metric(sum(values) / len(values))
        else:
            result[name] = 0.0
    # Recompute success_rate as successful / total (mean of per-unit
    # success_rate values is equivalent, since each is 0 or 1).
    result["success_rate"] = _round_metric(
        sum(
            1.0
            for r in per_unit_metrics
            if r.get("success_rate", 0.0) > 0
        )
        / n
    )
    # Compute retrieval_utility from aggregate metric means.
    result["retrieval_utility"] = _compute_utility(result)
    return result


def _weighted_mean(
    values_by_benchmark: dict[str, tuple[float, int]],
) -> float:
    """Compute a sample-count-weighted mean across benchmarks."""
    total_weight = sum(w for _, w in values_by_benchmark.values())
    if total_weight <= 0:
        return 0.0
    total = sum(v * w for v, w in values_by_benchmark.values())
    return _round_metric(total / total_weight)


# ---------------------------------------------------------------------------
# Bootstrap computation (paired, cross-benchmark, preserves sample counts).
# ---------------------------------------------------------------------------


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute the p-th percentile (p in [0, 1]) with linear interpolation."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    k = (n - 1) * p
    f = int(k)
    c = min(f + 1, n - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (
        k - f
    )


def _build_paired_units(
    treatment_units: dict[int, dict[str, float]],
    baseline_units: dict[int, dict[str, float]],
    baseline_is_empty: bool,
) -> list[tuple[dict[str, float], dict[str, float]]]:
    """Build paired (treatment, baseline) per-unit metric dicts.

    For ``*_vs_empty`` effects (``baseline_is_empty=True``), the
    baseline is synthetic zero; each treatment unit is paired with an
    all-zero baseline dict. The list has one entry per treatment unit.

    For paired effects (``baseline_is_empty=False``), units are paired
    by index where BOTH methods have per-unit metrics (paired complete-
    case analysis). The list has one entry per matched index.
    """
    pairs: list[tuple[dict[str, float], dict[str, float]]] = []
    if baseline_is_empty:
        zero_baseline = {name: 0.0 for name in METRIC_NAMES}
        for idx in sorted(treatment_units.keys()):
            pairs.append((dict(treatment_units[idx]), dict(zero_baseline)))
        return pairs

    common = sorted(
        set(treatment_units.keys()) & set(baseline_units.keys())
    )
    for idx in common:
        pairs.append(
            (dict(treatment_units[idx]), dict(baseline_units[idx]))
        )
    return pairs


def _compute_effect_from_pairs(
    cb_pairs: list[tuple[dict[str, float], dict[str, float]]],
    rq_pairs: list[tuple[dict[str, float], dict[str, float]]],
    metric: str,
    baseline_is_empty: bool,
) -> float:
    """Compute the cross-benchmark weighted mean effect for a metric.

    For linear metrics (``file_recall@10``, ``mrr``, ``span_f0.5@10``,
    ``success_rate``): the effect is the weighted cross-benchmark mean
    of (treatment_mean - baseline_mean).

    For ``retrieval_utility``: the effect is the weighted cross-benchmark
    mean of (utility(treatment_aggregate) - utility(baseline_aggregate)),
    where each benchmark's aggregate is the mean of its per-unit metrics.
    For ``empty_retrieval`` baseline, the baseline utility is 0.0 by
    construction (NOT utility(0,0,0) which would be -0.25).
    """
    cb_n = len(cb_pairs)
    rq_n = len(rq_pairs)
    total_n = cb_n + rq_n
    if total_n <= 0:
        return 0.0

    def _benchmark_effect(
        pairs: list[tuple[dict[str, float], dict[str, float]]],
    ) -> float:
        if not pairs:
            return 0.0
        if metric == "retrieval_utility":
            t_agg = _aggregate_per_unit_means(
                [t for t, b in pairs]
            )
            if baseline_is_empty:
                b_utility = 0.0
            else:
                b_agg = _aggregate_per_unit_means(
                    [b for t, b in pairs]
                )
                b_utility = _compute_utility(b_agg)
            t_utility = _compute_utility(t_agg)
            return t_utility - b_utility
        else:
            t_vals = [t.get(metric, 0.0) for t, b in pairs]
            t_mean = sum(t_vals) / len(t_vals) if t_vals else 0.0
            if baseline_is_empty:
                b_mean = 0.0
            else:
                b_vals = [b.get(metric, 0.0) for t, b in pairs]
                b_mean = sum(b_vals) / len(b_vals) if b_vals else 0.0
            return t_mean - b_mean

    cb_effect = _benchmark_effect(cb_pairs)
    rq_effect = _benchmark_effect(rq_pairs)
    return (cb_effect * cb_n + rq_effect * rq_n) / total_n


def _bootstrap_effect_record(
    *,
    effect_name: str,
    metric: str,
    cb_pairs: list[tuple[dict[str, float], dict[str, float]]],
    rq_pairs: list[tuple[dict[str, float], dict[str, float]]],
    baseline_is_empty: bool,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Compute a single bootstrap effect record.

    Cross-benchmark resampling preserves benchmark sample counts: within
    each replicate, ContextBench pairs are resampled with replacement to
    the ContextBench pair count, RepoQA pairs are resampled with
    replacement to the RepoQA pair count, and the cross-benchmark weighted
    mean is computed with the original pair counts as weights.

    For paired effects (``baseline_is_empty=False``), resampling
    preserves the treatment-baseline pairing (both are drawn from the
    same resampled index).

    Returns a record with the public effect fields only.
    """
    cb_n = len(cb_pairs)
    rq_n = len(rq_pairs)
    sample_units = cb_n + rq_n

    point_estimate = _compute_effect_from_pairs(
        cb_pairs, rq_pairs, metric, baseline_is_empty
    )

    if sample_units == 0 or replicates <= 0:
        return {
            "effect_name": effect_name,
            "metric": metric,
            "point_estimate": _round_metric(point_estimate),
            "bootstrap_mean": _round_metric(point_estimate),
            "ci_p05": _round_metric(point_estimate),
            "ci_p50": _round_metric(point_estimate),
            "ci_p95": _round_metric(point_estimate),
            "sign_positive_fraction": 0.0,
            "sign_negative_fraction": 0.0,
            "sign_zero_fraction": 1.0,
            "sample_units": 0,
            "bootstrap_replicates": int(replicates),
            "bootstrap_seed": int(seed),
        }

    rng = random.Random(seed)
    bootstrap_values: list[float] = []
    for _ in range(replicates):
        if cb_n > 0:
            cb_sample = [
                cb_pairs[rng.randrange(cb_n)] for _ in range(cb_n)
            ]
        else:
            cb_sample = []
        if rq_n > 0:
            rq_sample = [
                rq_pairs[rng.randrange(rq_n)] for _ in range(rq_n)
            ]
        else:
            rq_sample = []
        val = _compute_effect_from_pairs(
            cb_sample, rq_sample, metric, baseline_is_empty
        )
        bootstrap_values.append(val)

    bootstrap_values.sort()
    bootstrap_mean = sum(bootstrap_values) / len(bootstrap_values)
    ci_p05 = _percentile(bootstrap_values, 0.05)
    ci_p50 = _percentile(bootstrap_values, 0.50)
    ci_p95 = _percentile(bootstrap_values, 0.95)

    sign_pos = sum(1 for v in bootstrap_values if v > 0)
    sign_neg = sum(1 for v in bootstrap_values if v < 0)
    sign_zero = sum(1 for v in bootstrap_values if v == 0)
    total = len(bootstrap_values)

    return {
        "effect_name": effect_name,
        "metric": metric,
        "point_estimate": _round_metric(point_estimate),
        "bootstrap_mean": _round_metric(bootstrap_mean),
        "ci_p05": _round_metric(ci_p05),
        "ci_p50": _round_metric(ci_p50),
        "ci_p95": _round_metric(ci_p95),
        "sign_positive_fraction": _round_metric(sign_pos / total),
        "sign_negative_fraction": _round_metric(sign_neg / total),
        "sign_zero_fraction": _round_metric(sign_zero / total),
        "sample_units": int(sample_units),
        "bootstrap_replicates": int(replicates),
        "bootstrap_seed": int(seed),
    }


def _compute_all_bootstrap_effects(
    *,
    cb_per_unit: dict[str, dict[int, dict[str, float]]],
    rq_per_unit: dict[str, dict[int, dict[str, float]]],
    replicates: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Compute bootstrap effect records for all effects x metrics.

    For each effect, builds paired (treatment, baseline) per-unit metric
    pairs for ContextBench and RepoQA, then bootstraps the cross-benchmark
    weighted mean effect for each metric.
    """
    records: list[dict[str, Any]] = []
    for effect_name, (treatment, baseline) in EFFECT_METHOD_PAIRS.items():
        baseline_is_empty = baseline == "empty_retrieval"
        cb_treatment = cb_per_unit.get(treatment, {})
        cb_baseline = (
            {} if baseline_is_empty else cb_per_unit.get(baseline, {})
        )
        rq_treatment = rq_per_unit.get(treatment, {})
        rq_baseline = (
            {} if baseline_is_empty else rq_per_unit.get(baseline, {})
        )
        cb_pairs = _build_paired_units(
            cb_treatment, cb_baseline, baseline_is_empty
        )
        rq_pairs = _build_paired_units(
            rq_treatment, rq_baseline, baseline_is_empty
        )
        for metric in METRIC_NAMES:
            records.append(
                _bootstrap_effect_record(
                    effect_name=effect_name,
                    metric=metric,
                    cb_pairs=cb_pairs,
                    rq_pairs=rq_pairs,
                    baseline_is_empty=baseline_is_empty,
                    replicates=replicates,
                    seed=seed,
                )
            )
    return records


# ---------------------------------------------------------------------------
# Public report builders (fail-closed scan).
# ---------------------------------------------------------------------------


def _build_benchmark_method_mean_record(
    *,
    benchmark: str,
    method: str,
    sample_count: int,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build a single benchmark_method_means record."""
    return {
        "benchmark": benchmark,
        "method": method,
        "sample_count": int(sample_count),
        "metrics": _filter_metrics(metrics),
    }


def _build_cross_benchmark_method_mean_record(
    *,
    method: str,
    contextbench_sample_count: int,
    repoqa_sample_count: int,
    contextbench_metrics: dict[str, Any],
    repoqa_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build a cross_benchmark_method_means record with weighted-mean metrics.

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
    bootstrap_replicates: int,
    bootstrap_seed: int,
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


def _build_bootstrap_summary(
    *,
    replicates: int,
    seed: int,
    bootstrap_record_count: int,
) -> dict[str, Any]:
    """Build the ``bootstrap_summary`` block."""
    return {
        "bootstrap_replicates": int(replicates),
        "bootstrap_seed": int(seed),
        "effect_count": len(EFFECTS),
        "metric_count": len(METRIC_NAMES),
        "bootstrap_record_count": int(bootstrap_record_count),
        "resampling_method": (
            "paired_cross_benchmark_preserves_sample_counts"
        ),
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
    bootstrap_replicates: int,
    bootstrap_seed: int,
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
    safe_true["bootstrap_computed"] = False
    safe_true["retrieval_utility_robustness_smoke"] = False

    input_summary = _build_input_summary(
        contextbench_row_limit=contextbench_row_limit_requested,
        repoqa_needle_limit=repoqa_needle_limit_requested,
        methods=methods,
        contextbench_rows_fetched=contextbench_rows_fetched,
        repoqa_needles_seen=repoqa_needles_seen,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
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
        "bootstrap_replicates_requested": int(bootstrap_replicates),
        "bootstrap_seed": int(bootstrap_seed),
        "methods_count": len(methods),
        "methods_attempted": len(methods),
        "methods_successful": 0,
        "methods_succeeded": 0,
        "methods_failed": len(methods),
        "input_summary": input_summary,
        "benchmark_method_means": [],
        "cross_benchmark_method_means": [],
        "bootstrap_effect_records": [],
        "bootstrap_summary": _build_bootstrap_summary(
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
            bootstrap_record_count=0,
        ),
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
            "is_formal_benchmark_confidence_interval": False,
            "signal_strength": (
                "cross_benchmark_retrieval_utility_robustness_smoke_unavailable"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _f1d_forbidden_scan_summary(report)
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
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    """Build a pass/partial cross-benchmark robustness report."""
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

    cb_per_unit = contextbench_result.get("per_unit", {})
    rq_per_unit = repoqa_result.get("per_unit", {})

    cb_method_results = contextbench_result.get("method_results", [])
    rq_method_results = repoqa_result.get("method_results", [])
    cb_status = contextbench_result.get("status", "unavailable")
    rq_status = repoqa_result.get("status", "unavailable")

    # Build benchmark_method_means (per benchmark x per method).
    benchmark_method_means: list[dict[str, Any]] = []
    for rec in cb_method_results:
        benchmark_method_means.append(
            _build_benchmark_method_mean_record(
                benchmark=CONTEXTBENCH_BENCHMARK,
                method=rec["method"],
                sample_count=rec.get("rows_successful", 0),
                metrics=rec.get("metrics", {}),
            )
        )
    for rec in rq_method_results:
        benchmark_method_means.append(
            _build_benchmark_method_mean_record(
                benchmark=REPOQA_BENCHMARK,
                method=rec["method"],
                sample_count=rec.get("needles_successful", 0),
                metrics=rec.get("metrics", {}),
            )
        )

    # Build cross_benchmark_method_means (per method, weighted mean).
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

    cross_benchmark_method_means: list[dict[str, Any]] = [
        _build_cross_benchmark_method_mean_record(
            method="empty_retrieval",
            contextbench_sample_count=0,
            repoqa_sample_count=0,
            contextbench_metrics={},
            repoqa_metrics={},
        )
    ]
    for method in methods:
        cross_benchmark_method_means.append(
            _build_cross_benchmark_method_mean_record(
                method=method,
                contextbench_sample_count=cb_sample_count,
                repoqa_sample_count=rq_sample_count,
                contextbench_metrics=cb_metrics_by_method.get(
                    method, {}
                ),
                repoqa_metrics=rq_metrics_by_method.get(method, {}),
            )
        )

    # Compute bootstrap effect records from per-unit metrics.
    bootstrap_effect_records = _compute_all_bootstrap_effects(
        cb_per_unit=cb_per_unit,
        rq_per_unit=rq_per_unit,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )

    # Determine overall F1-D status.
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
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
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
    bootstrap_computed = len(bootstrap_effect_records) > 0

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
    safe_true["bootstrap_computed"] = bootstrap_computed
    safe_true["retrieval_utility_robustness_smoke"] = (
        cb_bm25_ok or rq_bm25_ok
    )

    input_summary = _build_input_summary(
        contextbench_row_limit=contextbench_row_limit_requested,
        repoqa_needle_limit=repoqa_needle_limit_requested,
        methods=methods,
        contextbench_rows_fetched=contextbench_rows_fetched,
        repoqa_needles_seen=repoqa_needles_seen,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    )

    bootstrap_summary = _build_bootstrap_summary(
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
        bootstrap_record_count=len(bootstrap_effect_records),
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
        "bootstrap_replicates_requested": int(bootstrap_replicates),
        "bootstrap_seed": int(bootstrap_seed),
        "methods_count": len(methods),
        "methods_attempted": methods_attempted,
        "methods_successful": methods_successful,
        "methods_succeeded": methods_successful,
        "methods_failed": max(0, methods_attempted - methods_successful),
        "input_summary": input_summary,
        "benchmark_method_means": benchmark_method_means,
        "cross_benchmark_method_means": cross_benchmark_method_means,
        "bootstrap_effect_records": bootstrap_effect_records,
        "bootstrap_summary": bootstrap_summary,
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
            "is_formal_benchmark_confidence_interval": False,
            "signal_strength": (
                "cross_benchmark_retrieval_utility_robustness_smoke_aggregate_only"
            ),
            "is_full_external_benchmark_evaluation": False,
        },
    }

    scan = _f1d_forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return report


# ---------------------------------------------------------------------------
# Cross-benchmark network smoke runner.
# ---------------------------------------------------------------------------


def _run_cross_benchmark_robustness_smoke(
    *,
    contextbench_row_limit: int,
    repoqa_needle_limit: int,
    methods: list[str],
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    """Run the real cross-benchmark network robustness smoke.

    Reruns real bounded external data for both ContextBench and RepoQA
    (does NOT combine existing C5 or F1-C aggregate artifacts).
    """
    cb_result = _run_contextbench_matrix_per_unit(
        row_limit=contextbench_row_limit,
        methods=methods,
        openlocus_bin=openlocus_bin,
        openlocus_binary_source=openlocus_binary_source,
        eval_dir=eval_dir,
    )
    rq_result = _run_repoqa_matrix_per_unit(
        needle_limit=repoqa_needle_limit,
        methods=methods,
        openlocus_bin=openlocus_bin,
        openlocus_binary_source=openlocus_binary_source,
        eval_dir=eval_dir,
    )

    network_calls = int(cb_result.get("network_calls", 0)) + int(
        rq_result.get("network_calls", 0)
    )

    cb_fetched = int(cb_result.get("rows_fetched", 0))
    rq_seen = int(rq_result.get("needles_seen", 0))
    if cb_fetched == 0 and rq_seen == 0:
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
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
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
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    )


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic data).
# ---------------------------------------------------------------------------


def _build_synthetic_per_unit_metrics(
    method: str,
    n: int,
) -> dict[int, dict[str, float]]:
    """Build synthetic per-unit metrics for self-test (in-memory only)."""
    result: dict[int, dict[str, float]] = {}
    for i in range(n):
        if method == "bm25":
            base = {
                "file_recall@10": 1.0 if i % 2 == 0 else 0.0,
                "mrr": 0.5 if i % 2 == 0 else 0.0,
                "span_f0.5@10": 0.1 if i % 2 == 0 else 0.0,
                "success_rate": 1.0,
            }
        elif method == "regex":
            base = {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 1.0,
            }
        elif method == "symbol":
            base = {
                "file_recall@10": 1.0 if i % 3 == 0 else 0.0,
                "mrr": 0.3 if i % 3 == 0 else 0.0,
                "span_f0.5@10": 0.05 if i % 3 == 0 else 0.0,
                "success_rate": 1.0,
            }
        else:
            base = {
                "file_recall@10": 0.0,
                "mrr": 0.0,
                "span_f0.5@10": 0.0,
                "success_rate": 0.0,
            }
        metrics = dict(base)
        metrics["retrieval_utility"] = _compute_utility(metrics)
        result[i] = metrics
    return result


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all F1-D self-test groups (no network)."""
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
        bootstrap_replicates=BOOTSTRAP_REPLICATES_DEFAULT,
        bootstrap_seed=BOOTSTRAP_SEED_DEFAULT,
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
            "robustness_smoke_false_when_unavailable",
            skeleton.get("retrieval_utility_robustness_smoke")
            is False,
        )
    )
    checks.append(
        _check(
            "bootstrap_computed_false_when_unavailable",
            skeleton.get("bootstrap_computed") is False,
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

    # --- Group 5: Method parser (reused from F1-C). ---
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

    # --- Group 6: Row/needle limit hard caps (reused from F1-C). ---
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

    # --- Group 7: Bootstrap replicates / seed hard caps. ---
    checks.append(
        _check(
            "bootstrap_replicates_default_1000",
            BOOTSTRAP_REPLICATES_DEFAULT == 1000,
        )
    )
    checks.append(
        _check(
            "bootstrap_replicates_hard_cap_2000",
            BOOTSTRAP_REPLICATES_HARD_CAP == 2000,
        )
    )
    checks.append(
        _check(
            "bootstrap_replicates_cap_enforced_at_2000",
            _validate_bootstrap_replicates(5000) == 2000,
        )
    )
    checks.append(
        _check(
            "bootstrap_replicates_passes_through_at_1000",
            _validate_bootstrap_replicates(1000) == 1000,
        )
    )
    try:
        _validate_bootstrap_replicates(0)
        checks.append(
            _check("bootstrap_replicates_rejects_zero", False)
        )
    except SystemExit:
        checks.append(
            _check("bootstrap_replicates_rejects_zero", True)
        )
    checks.append(
        _check(
            "bootstrap_seed_default_20240621",
            BOOTSTRAP_SEED_DEFAULT == 20240621,
        )
    )
    checks.append(
        _check(
            "bootstrap_seed_passes_through",
            _validate_bootstrap_seed(12345) == 12345,
        )
    )
    try:
        _validate_bootstrap_seed(-1)
        checks.append(
            _check("bootstrap_seed_rejects_negative", False)
        )
    except SystemExit:
        checks.append(
            _check("bootstrap_seed_rejects_negative", True)
        )

    # --- Group 8: Records-shaped containers. ---
    checks.append(
        _check(
            "benchmark_method_means_is_list",
            isinstance(skeleton["benchmark_method_means"], list),
        )
    )
    checks.append(
        _check(
            "cross_benchmark_method_means_is_list",
            isinstance(
                skeleton["cross_benchmark_method_means"], list
            ),
        )
    )
    checks.append(
        _check(
            "bootstrap_effect_records_is_list",
            isinstance(skeleton["bootstrap_effect_records"], list),
        )
    )
    checks.append(
        _check(
            "bootstrap_summary_present",
            "bootstrap_summary" in skeleton,
        )
    )
    checks.append(
        _check(
            "input_summary_present",
            "input_summary" in skeleton,
        )
    )
    checks.append(
        _check(
            "no_f1c_container_keys",
            "benchmark_results" not in skeleton
            and "cross_benchmark_method_results" not in skeleton
            and "counterfactual_effects" not in skeleton,
        )
    )

    # --- Group 9: Utility computation (reused from F1-C; unchanged). ---
    empty_metrics = _extract_per_unit_metrics(None)
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

    # --- Group 10: Per-unit aggregation (utility of means). ---
    per_unit = [
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
    agg = _aggregate_per_unit_means(per_unit)
    checks.append(
        _check(
            "aggregate_mean_correct",
            agg["file_recall@10"] == 0.75
            and agg["mrr"] == 0.45,
        )
    )
    # Utility of means: utility(mean_file_recall=0.75, mean_mrr=0.45,
    # mean_span_f0.5=0.3) = 0.75 + 0.25*0.45 + 0.5*0.3 - 0
    # = 0.75 + 0.1125 + 0.15 = 1.0125.
    expected_agg_utility = round(
        0.75 + MRR_WEIGHT * 0.45 + SPAN_F_WEIGHT * 0.3 - 0.0, 6
    )
    checks.append(
        _check(
            "aggregate_utility_of_means_correct",
            agg["retrieval_utility"] == expected_agg_utility,
        )
    )
    # Verify utility of means != mean of per-unit utilities.
    mean_per_unit_utility = round((0.65 + 1.3) / 2, 6)
    checks.append(
        _check(
            "utility_of_means_differs_from_mean_of_utilities",
            agg["retrieval_utility"] != mean_per_unit_utility,
        )
    )

    # --- Group 11: Cross-benchmark weighted means. ---
    cb_metrics = {"file_recall@10": 1.0, "mrr": 0.5, "span_f0.5@10": 0.4, "success_rate": 1.0, "retrieval_utility": 1.3}
    rq_metrics = {"file_recall@10": 0.0, "mrr": 0.0, "span_f0.5@10": 0.0, "success_rate": 0.0, "retrieval_utility": -0.25}
    cross_rec = _build_cross_benchmark_method_mean_record(
        method="bm25",
        contextbench_sample_count=20,
        repoqa_sample_count=10,
        contextbench_metrics=cb_metrics,
        repoqa_metrics=rq_metrics,
    )
    expected_recall = round(
        (1.0 * 20 + 0.0 * 10) / 30, 6
    )
    checks.append(
        _check(
            "cross_benchmark_weighted_mean_correct",
            cross_rec["metrics"]["file_recall@10"]
            == expected_recall,
        )
    )
    empty_cross = _build_cross_benchmark_method_mean_record(
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

    # --- Group 12: Bootstrap computation. ---
    # Build synthetic per-unit metrics for bootstrap tests.
    cb_pu = {
        "bm25": _build_synthetic_per_unit_metrics("bm25", 20),
        "regex": _build_synthetic_per_unit_metrics("regex", 20),
        "symbol": _build_synthetic_per_unit_metrics("symbol", 20),
    }
    rq_pu = {
        "bm25": _build_synthetic_per_unit_metrics("bm25", 10),
        "regex": _build_synthetic_per_unit_metrics("regex", 10),
        "symbol": _build_synthetic_per_unit_metrics("symbol", 10),
    }
    effects = _compute_all_bootstrap_effects(
        cb_per_unit=cb_pu,
        rq_per_unit=rq_pu,
        replicates=200,
        seed=BOOTSTRAP_SEED_DEFAULT,
    )
    checks.append(
        _check(
            "bootstrap_effects_count_correct",
            len(effects) == len(EFFECTS) * len(METRIC_NAMES),
        )
    )
    checks.append(
        _check(
            "bootstrap_effect_fields_exact",
            all(
                set(e.keys())
                == {
                    "effect_name",
                    "metric",
                    "point_estimate",
                    "bootstrap_mean",
                    "ci_p05",
                    "ci_p50",
                    "ci_p95",
                    "sign_positive_fraction",
                    "sign_negative_fraction",
                    "sign_zero_fraction",
                    "sample_units",
                    "bootstrap_replicates",
                    "bootstrap_seed",
                }
                for e in effects
            ),
        )
    )
    # bm25_vs_empty on retrieval_utility: point_estimate should be
    # positive (bm25 has nonzero retrieval).
    bm25_empty_util = next(
        e
        for e in effects
        if e["effect_name"] == "bm25_vs_empty"
        and e["metric"] == "retrieval_utility"
    )
    checks.append(
        _check(
            "bm25_vs_empty_utility_positive",
            bm25_empty_util["point_estimate"] > 0,
        )
    )
    checks.append(
        _check(
            "bm25_vs_empty_sample_units_30",
            bm25_empty_util["sample_units"] == 30,
        )
    )
    checks.append(
        _check(
            "bm25_vs_empty_replicates_200",
            bm25_empty_util["bootstrap_replicates"] == 200,
        )
    )
    checks.append(
        _check(
            "bm25_vs_empty_seed_default",
            bm25_empty_util["bootstrap_seed"]
            == BOOTSTRAP_SEED_DEFAULT,
        )
    )
    checks.append(
        _check(
            "bm25_vs_empty_sign_fractions_sum_to_1",
            round(
                bm25_empty_util["sign_positive_fraction"]
                + bm25_empty_util["sign_negative_fraction"]
                + bm25_empty_util["sign_zero_fraction"],
                6
            )
            == 1.0,
        )
    )
    checks.append(
        _check(
            "bm25_vs_empty_ci_ordered",
            bm25_empty_util["ci_p05"]
            <= bm25_empty_util["ci_p50"]
            <= bm25_empty_util["ci_p95"],
        )
    )
    # regex_vs_empty on file_recall@10: regex has 0 recall, so
    # point_estimate should be 0 and sign_zero_fraction should be 1.0.
    regex_empty_fr = next(
        e
        for e in effects
        if e["effect_name"] == "regex_vs_empty"
        and e["metric"] == "file_recall@10"
    )
    checks.append(
        _check(
            "regex_vs_empty_recall_zero",
            regex_empty_fr["point_estimate"] == 0.0,
        )
    )
    checks.append(
        _check(
            "regex_vs_empty_recall_sign_zero",
            regex_empty_fr["sign_zero_fraction"] == 1.0,
        )
    )
    # regex_vs_bm25 on file_recall@10: regex has 0, bm25 has some, so
    # point_estimate should be negative.
    regex_bm25_fr = next(
        e
        for e in effects
        if e["effect_name"] == "regex_vs_bm25"
        and e["metric"] == "file_recall@10"
    )
    checks.append(
        _check(
            "regex_vs_bm25_recall_negative",
            regex_bm25_fr["point_estimate"] < 0,
        )
    )
    checks.append(
        _check(
            "regex_vs_bm25_sample_units_paired",
            regex_bm25_fr["sample_units"] <= 30,
        )
    )
    # Bootstrap determinism: same seed -> same results.
    effects2 = _compute_all_bootstrap_effects(
        cb_per_unit=cb_pu,
        rq_per_unit=rq_pu,
        replicates=200,
        seed=BOOTSTRAP_SEED_DEFAULT,
    )
    bm25_empty_util2 = next(
        e
        for e in effects2
        if e["effect_name"] == "bm25_vs_empty"
        and e["metric"] == "retrieval_utility"
    )
    checks.append(
        _check(
            "bootstrap_deterministic_same_seed",
            bm25_empty_util == bm25_empty_util2,
        )
    )

    # --- Group 13: Percentile helper. ---
    checks.append(
        _check(
            "percentile_single_value",
            _percentile([0.5], 0.5) == 0.5,
        )
    )
    checks.append(
        _check(
            "percentile_empty_returns_zero",
            _percentile([], 0.5) == 0.0,
        )
    )
    sorted_vals = [0.1, 0.2, 0.3, 0.4, 0.5]
    checks.append(
        _check(
            "percentile_p50_median",
            _percentile(sorted_vals, 0.5) == 0.3,
        )
    )
    checks.append(
        _check(
            "percentile_p0_min",
            _percentile(sorted_vals, 0.0) == 0.1,
        )
    )
    checks.append(
        _check(
            "percentile_p1_max",
            _percentile(sorted_vals, 1.0) == 0.5,
        )
    )

    # --- Group 14: Paired unit builder. ---
    treatment = {0: {"file_recall@10": 1.0}, 1: {"file_recall@10": 0.0}}
    baseline = {0: {"file_recall@10": 0.5}, 1: {"file_recall@10": 0.5}}
    pairs = _build_paired_units(treatment, baseline, False)
    checks.append(
        _check(
            "paired_units_matched_by_index",
            len(pairs) == 2,
        )
    )
    checks.append(
        _check(
            "paired_units_preserve_pairing",
            pairs[0][0]["file_recall@10"] == 1.0
            and pairs[0][1]["file_recall@10"] == 0.5,
        )
    )
    # Unpaired (empty baseline): one entry per treatment unit.
    empty_pairs = _build_paired_units(treatment, {}, True)
    checks.append(
        _check(
            "empty_baseline_pairs_per_treatment_unit",
            len(empty_pairs) == 2
            and all(b["file_recall@10"] == 0.0 for t, b in empty_pairs),
        )
    )
    # Partial overlap: only index 1 is common.
    baseline2 = {1: {"file_recall@10": 0.5}}
    pairs2 = _build_paired_units(treatment, baseline2, False)
    checks.append(
        _check(
            "paired_units_partial_overlap",
            len(pairs2) == 1,
        )
    )

    # --- Group 15: Failure categories kept separate. ---
    checks.append(
        _check(
            "contextbench_failure_categories_separate_from_repoqa",
            CONTEXTBENCH_FAILURE_CATEGORIES
            is not REPOQA_FAILURE_CATEGORIES
            and set(CONTEXTBENCH_FAILURE_CATEGORIES)
            != set(REPOQA_FAILURE_CATEGORIES),
        )
    )
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

    # --- Group 16: Scanner rejections. ---
    checks.append(
        _check(
            "scanner_rejects_repo_url",
            bool(_scan_f1d({"leaked": "https://github.com/x/y"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha",
            bool(_scan_f1d({"leaked": "a" * 40})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug",
            bool(_scan_f1d({"leaked": "astropy/astropy"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_task_id_key",
            bool(_scan_f1d({"task_id": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_key",
            bool(_scan_f1d({"query": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_winner_key",
            bool(_scan_f1d({"winner": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_best_method_key",
            bool(_scan_f1d({"best_method": "bm25"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_es_notation_E_primary",
            bool(_scan_f1d({"E_primary": 0.5})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_routing_prefix_value",
            bool(
                _scan_f1d(
                    {"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path",
            bool(_scan_f1d({"leaked": "/tmp/f1d_smoke_0"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_provider_key",
            bool(_scan_f1d({"api_key": "abc"})),
        )
    )
    # F1-D-specific: rejects F1-C container names.
    checks.append(
        _check(
            "scanner_rejects_f1c_benchmark_results_key",
            bool(_scan_f1d({"benchmark_results": []})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_f1c_cross_benchmark_method_results_key",
            bool(
                _scan_f1d(
                    {"cross_benchmark_method_results": []}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_f1c_counterfactual_effects_key",
            bool(_scan_f1d({"counterfactual_effects": []})),
        )
    )
    # F1-D-specific: rejects per-unit metric array keys.
    checks.append(
        _check(
            "scanner_rejects_per_row_metrics_key",
            bool(_scan_f1d({"per_row_metrics": []})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_per_needle_metrics_key",
            bool(_scan_f1d({"per_needle_metrics": []})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_row_hashes_key",
            bool(_scan_f1d({"row_hashes": []})),
        )
    )

    # --- Group 17: Scanner allows legitimate aggregate values. ---
    checks.append(
        _check(
            "scanner_allows_method_name",
            not _scan_f1d({"method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_benchmark_name",
            not _scan_f1d({"benchmark": "contextbench"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_effect_name",
            not _scan_f1d({"effect_name": "bm25_vs_empty"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_metric_name",
            not _scan_f1d({"metric": "file_recall@10"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_bootstrap_fields",
            not _scan_f1d(
                {
                    "bootstrap_replicates": 1000,
                    "bootstrap_seed": 20240621,
                    "ci_p05": 0.1,
                    "ci_p50": 0.3,
                    "ci_p95": 0.5,
                    "sign_positive_fraction": 0.9,
                    "sign_negative_fraction": 0.1,
                    "sign_zero_fraction": 0.0,
                    "sample_units": 30,
                    "point_estimate": 0.3,
                    "bootstrap_mean": 0.31,
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_benchmark_method_means_records",
            not _scan_f1d(
                {
                    "benchmark_method_means": [
                        {
                            "benchmark": "contextbench",
                            "method": "bm25",
                            "sample_count": 20,
                            "metrics": {"mrr": 0.5},
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_bootstrap_effect_records",
            not _scan_f1d(
                {
                    "bootstrap_effect_records": [
                        {
                            "effect_name": "bm25_vs_empty",
                            "metric": "mrr",
                            "point_estimate": 0.3,
                            "bootstrap_mean": 0.31,
                            "ci_p05": 0.1,
                            "ci_p50": 0.3,
                            "ci_p95": 0.5,
                            "sign_positive_fraction": 0.9,
                            "sign_negative_fraction": 0.1,
                            "sign_zero_fraction": 0.0,
                            "sample_units": 30,
                            "bootstrap_replicates": 1000,
                            "bootstrap_seed": 20240621,
                        }
                    ]
                }
            ),
        )
    )
    # Scanner rejects dict-keyed F1-D containers.
    checks.append(
        _check(
            "scanner_rejects_benchmark_method_means_dict",
            bool(
                _scan_f1d(
                    {
                        "benchmark_method_means": {
                            "contextbench": {"metrics": {}}
                        }
                    }
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_cross_benchmark_method_means_dict",
            bool(
                _scan_f1d(
                    {
                        "cross_benchmark_method_means": {
                            "bm25": {"metrics": {}}
                        }
                    }
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_bootstrap_effect_records_dict",
            bool(
                _scan_f1d(
                    {
                        "bootstrap_effect_records": {
                            "bm25_vs_empty": {}
                        }
                    }
                )
            ),
        )
    )

    # --- Group 18: Fail-closed generation. ---
    try:
        _enforce_f1d_no_forbidden(skeleton)
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
        _enforce_f1d_no_forbidden(leaked_report)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(
        _check("fail_closed_raises_on_leak", leak_raises)
    )
    leaked_report2 = dict(skeleton)
    leaked_report2["winner"] = "bm25"
    try:
        _enforce_f1d_no_forbidden(leaked_report2)
        winner_raises = False
    except SystemExit:
        winner_raises = True
    checks.append(
        _check("fail_closed_raises_on_winner", winner_raises)
    )
    leaked_report3 = dict(skeleton)
    leaked_report3["E_primary"] = 0.5
    try:
        _enforce_f1d_no_forbidden(leaked_report3)
        es_raises = False
    except SystemExit:
        es_raises = True
    checks.append(
        _check("fail_closed_raises_on_es_notation", es_raises)
    )
    leaked_report4 = dict(skeleton)
    leaked_report4["per_row_metrics"] = []
    try:
        _enforce_f1d_no_forbidden(leaked_report4)
        per_unit_raises = False
    except SystemExit:
        per_unit_raises = True
    checks.append(
        _check(
            "fail_closed_raises_on_per_unit_key",
            per_unit_raises,
        )
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

    # --- Group 19: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_report_forbidden_scan_clean",
            skeleton["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 20: Build a synthetic pass report and verify shape. ---
    cb_per_unit_synth = {
        "bm25": _build_synthetic_per_unit_metrics("bm25", 20),
        "regex": _build_synthetic_per_unit_metrics("regex", 20),
        "symbol": _build_synthetic_per_unit_metrics("symbol", 20),
    }
    rq_per_unit_synth = {
        "bm25": _build_synthetic_per_unit_metrics("bm25", 10),
        "regex": _build_synthetic_per_unit_metrics("regex", 10),
        "symbol": _build_synthetic_per_unit_metrics("symbol", 10),
    }
    cb_method_results_synth = [
        {
            "method": m,
            "status": c5c.STATUS_PASS,
            "rows_evaluated": 20,
            "rows_successful": 20,
            "rows_failed": 0,
            "metrics": _aggregate_per_unit_means(
                list(cb_per_unit_synth[m].values())
            ),
            "failure_category_counts": {
                c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES
            },
        }
        for m in ALLOWED_METHODS
    ]
    rq_method_results_synth = [
        {
            "method": m,
            "status": c5e.STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _aggregate_per_unit_means(
                list(rq_per_unit_synth[m].values())
            ),
            "failure_category_counts": {
                c: 0 for c in REPOQA_FAILURE_CATEGORIES
            },
        }
        for m in ALLOWED_METHODS
    ]
    cb_result_synth = {
        "status": "pass",
        "rows_fetched": 20,
        "per_unit": cb_per_unit_synth,
        "method_results": cb_method_results_synth,
        "failure_category_counts": {
            c: 0 for c in CONTEXTBENCH_FAILURE_CATEGORIES
        },
        "network_calls": 1,
        "failure_reason_category": "",
    }
    rq_result_synth = {
        "status": "pass",
        "needles_seen": 10,
        "per_unit": rq_per_unit_synth,
        "method_results": rq_method_results_synth,
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
        bootstrap_replicates=200,
        bootstrap_seed=BOOTSTRAP_SEED_DEFAULT,
    )
    checks.append(
        _check(
            "pass_report_status_pass",
            pass_report["status"] == STATUS_PASS,
        )
    )
    checks.append(
        _check(
            "pass_report_has_benchmark_method_means",
            len(pass_report["benchmark_method_means"]) == 6,
        )
    )
    checks.append(
        _check(
            "pass_report_has_cross_benchmark_method_means",
            len(pass_report["cross_benchmark_method_means"]) == 4,
        )
    )
    checks.append(
        _check(
            "pass_report_has_bootstrap_effect_records",
            len(pass_report["bootstrap_effect_records"])
            == len(EFFECTS) * len(METRIC_NAMES),
        )
    )
    checks.append(
        _check(
            "pass_report_bootstrap_record_count_matches_summary",
            pass_report["bootstrap_summary"][
                "bootstrap_record_count"
            ]
            == len(pass_report["bootstrap_effect_records"]),
        )
    )
    checks.append(
        _check(
            "pass_report_includes_empty_retrieval",
            any(
                r["method"] == "empty_retrieval"
                for r in pass_report[
                    "cross_benchmark_method_means"
                ]
            ),
        )
    )
    checks.append(
        _check(
            "pass_report_bootstrap_computed_true",
            pass_report["bootstrap_computed"] is True,
        )
    )
    checks.append(
        _check(
            "pass_report_robustness_smoke_true",
            pass_report[
                "retrieval_utility_robustness_smoke"
            ]
            is True,
        )
    )
    checks.append(
        _check(
            "pass_report_forbidden_scan_clean",
            pass_report["forbidden_scan"]["status"] == "pass",
        )
    )
    # No winner/best_method/recommended_default/E_S keys anywhere.
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
        "per_row_metrics",
        "per_needle_metrics",
        "benchmark_results",
        "cross_benchmark_method_results",
        "counterfactual_effects",
    ):
        checks.append(
            _check(
                f"pass_report_no_{forbidden_key}_key",
                not _has_dict_key_anywhere(
                    pass_report, forbidden_key
                ),
            )
        )
    checks.append(
        _check(
            "pass_report_self_scan_clean",
            not _scan_f1d(pass_report),
        )
    )

    # --- Group 21: Partial status. ---
    cb_partial = {
        "status": "unavailable",
        "rows_fetched": 0,
        "per_unit": {},
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
        bootstrap_replicates=200,
        bootstrap_seed=BOOTSTRAP_SEED_DEFAULT,
    )
    checks.append(
        _check(
            "partial_report_status_partial",
            partial_report["status"] == STATUS_PARTIAL,
        )
    )
    checks.append(
        _check(
            "partial_report_forbidden_scan_clean",
            partial_report["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 22: CLI argument surface. ---
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
    checks.append(
        _check(
            "cli_has_bootstrap_replicates_argument",
            "--bootstrap-replicates" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_has_bootstrap_seed_argument",
            "--bootstrap-seed" in cli_opts,
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
    """Build the F1-D CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "F1-D cross-benchmark retrieval utility robustness smoke "
            "(public aggregate-only artifact; bounded ContextBench "
            "verified 20-row + RepoQA 10-needle Python subsets; "
            "transient /tmp clone + retrieval + score; methods "
            "bm25,regex,symbol only; paired cross-benchmark bootstrap "
            "preserving sample counts; no provider calls; no raw "
            "rows/queries/repo URLs/commits/gold paths/spans/needle "
            "descriptions/paths/line ranges/generated JSONL/evidence "
            "rows/cloned repos/stdout/stderr/per-unit metric arrays/"
            "row hashes/winner/best_method/recommended_default/"
            "E_S notation committed; bootstrap stats are diagnostic "
            "robustness estimates, NOT formal benchmark CIs)."
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
            "deterministically; text is NOT allowed in F1-D)"
        ),
    )
    ap.add_argument(
        "--bootstrap-replicates",
        type=int,
        default=BOOTSTRAP_REPLICATES_DEFAULT,
        help=(
            "number of bootstrap replicates (default: "
            f"{BOOTSTRAP_REPLICATES_DEFAULT}; hard cap "
            f"{BOOTSTRAP_REPLICATES_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--bootstrap-seed",
        type=int,
        default=BOOTSTRAP_SEED_DEFAULT,
        help=(
            "bootstrap RNG seed (default: "
            f"{BOOTSTRAP_SEED_DEFAULT})"
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
            bootstrap_replicates=args.bootstrap_replicates,
            bootstrap_seed=args.bootstrap_seed,
        )
        _write_json(args.out, report)
        sys.exit(1)

    contextbench_row_limit = _validate_contextbench_row_limit(
        args.contextbench_row_limit
    )
    repoqa_needle_limit = _validate_repoqa_needle_limit(
        args.repoqa_needle_limit
    )
    bootstrap_replicates = _validate_bootstrap_replicates(
        args.bootstrap_replicates
    )
    bootstrap_seed = _validate_bootstrap_seed(args.bootstrap_seed)
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
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
        )
        _enforce_f1d_no_forbidden(report)
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
        report = _run_cross_benchmark_robustness_smoke(
            contextbench_row_limit=contextbench_row_limit,
            repoqa_needle_limit=repoqa_needle_limit,
            methods=methods,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            eval_dir=eval_dir,
            self_test_passed=self_test_passed,
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
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
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
        )

    _enforce_f1d_no_forbidden(report)
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
        f"repoqa_needles_seen={report['repoqa_needles_seen']}, "
        f"bootstrap_records={len(report['bootstrap_effect_records'])})"
    )


if __name__ == "__main__":
    main()
