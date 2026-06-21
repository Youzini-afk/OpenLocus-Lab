#!/usr/bin/env python3
"""F1-B Retrieval-Derived Counterfactual Utility Smoke (Public Aggregate-Only Artifact).

This module implements the **F1-B retrieval-derived counterfactual
utility smoke**. It moves F1 from purely synthetic context variants to
**retrieval-derived** counterfactual utility: it uses real ContextBench
verified rows, transient public repo clones, real OpenLocus retrieval
outputs, and ``eval/score.py`` metrics to estimate the aggregate
marginal utility of candidate-set variants.

F1-B is explicitly **not** a downstream utility claim, **not** true
E/S calibration, **not** an external benchmark performance claim, **not**
a leaderboard entry, **not** a promotion/default/runtime/retriever/
pack/backend/EvidenceCore semantic change, and **not** a live/provider
claim. It makes NO provider calls and NO remote provider calls.

Claim boundary (binding):

* Claim level: ``retrieval_derived_counterfactual_utility_smoke_only``.
* Mode: ``public_aggregate_contextbench_retrieval_counterfactual``;
  phase ``F1-B``.
* Status enum: ``retrieval_derived_counterfactual_utility_smoke_pass``
  on success (all required variants have >=1 successful row + scanner
  pass); ``partial`` if some but not all variants succeed;
  ``unavailable_with_reason`` if none/blocked/network unavailable;
  ``fail_forbidden_scan`` on scanner failure.

Variants (fixed allowlist; records-shaped only):

* ``baseline_empty_candidate_set`` — empty candidate set (no retrieval).
* ``bm25_topk`` — BM25 retrieval candidates.
* ``regex_topk`` — regex retrieval candidates.
* ``symbol_topk`` — symbol retrieval candidates.
* ``bm25_plus_symbol_topk`` — BM25 + symbol union candidates.

Effects (fixed allowlist; records-shaped only):

* ``bm25_candidates_vs_empty`` — (bm25_topk - baseline_empty).
* ``regex_candidates_vs_empty`` — (regex_topk - baseline_empty).
* ``symbol_candidates_vs_empty`` — (symbol_topk - baseline_empty).
* ``symbol_added_to_bm25`` — (bm25_plus_symbol_topk - bm25_topk).

Metrics (aggregate-only retrieval/score utility metrics):

* ``file_recall@10``, ``mrr``, ``span_f0.5@10``, ``success_rate``.

Run::

    python3 -m py_compile eval/f1b_retrieval_derived_counterfactual_utility_smoke.py
    python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py --self-test
    python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py \\
        --out artifacts/f1b_retrieval_derived_counterfactual_utility/\\
f1b_retrieval_derived_counterfactual_utility_report.json

The default mode runs a real network smoke (transient HF rows + GitHub
clones + retrieval + score into ``/tmp``). If network/openlocus is
unavailable, it produces a truthful ``unavailable_with_reason`` report.
No provider calls are ever made.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Reuse C5-A helpers (backward-compatible import; C5-A is NOT modified).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c5_contextbench_verified_performance_smoke as c5  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "f1b_retrieval_derived_counterfactual_utility_smoke.v1"
GENERATED_BY = "eval/f1b_retrieval_derived_counterfactual_utility_smoke.py"
CLAIM_LEVEL = "retrieval_derived_counterfactual_utility_smoke_only"
MODE = "public_aggregate_contextbench_retrieval_counterfactual"
PHASE = "F1-B"

STATUS_PASS = "retrieval_derived_counterfactual_utility_smoke_pass"
STATUS_PARTIAL = "partial"
STATUS_UNAVAILABLE = "unavailable_with_reason"
STATUS_FAIL_LEAK = "fail_forbidden_scan"

ALL_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_PASS,
        STATUS_PARTIAL,
        STATUS_UNAVAILABLE,
        STATUS_FAIL_LEAK,
    }
)

DEFAULT_OUT = Path(
    "artifacts/f1b_retrieval_derived_counterfactual_utility/"
    "f1b_retrieval_derived_counterfactual_utility_report.json"
)

ROW_LIMIT_DEFAULT = 5
ROW_LIMIT_HARD_CAP = 10

# Methods supported by run_retrieval.py without provider calls.
ALLOWED_METHODS: tuple[str, ...] = ("bm25", "regex", "symbol")
DEFAULT_METHODS = "bm25,regex,symbol"

# Candidate-set variants (fixed allowlist; records-shaped only).
VARIANTS: tuple[str, ...] = (
    "baseline_empty_candidate_set",
    "bm25_topk",
    "regex_topk",
    "symbol_topk",
    "bm25_plus_symbol_topk",
)

# Counterfactual effects (fixed allowlist; records-shaped only).
# Each effect is (treatment_variant - baseline_variant).
EFFECT_VARIANT_PAIRS: dict[str, tuple[str, str]] = {
    "bm25_candidates_vs_empty": (
        "bm25_topk",
        "baseline_empty_candidate_set",
    ),
    "regex_candidates_vs_empty": (
        "regex_topk",
        "baseline_empty_candidate_set",
    ),
    "symbol_candidates_vs_empty": (
        "symbol_topk",
        "baseline_empty_candidate_set",
    ),
    "symbol_added_to_bm25": (
        "bm25_plus_symbol_topk",
        "bm25_topk",
    ),
}
EFFECTS: tuple[str, ...] = tuple(EFFECT_VARIANT_PAIRS.keys())

# Aggregate retrieval/score utility metrics (subset of score.py
# output; NOT downstream-agent metrics).
METRIC_NAMES: tuple[str, ...] = (
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "success_rate",
)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true).
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "retrieval_derived_counterfactual_utility_smoke": False,
    "external_benchmark_rows_read": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# ---------------------------------------------------------------------------
# Always-false no-claim flags.
# ---------------------------------------------------------------------------

DEFAULT_FALSE_FLAGS: dict[str, bool] = {
    "true_e_s_calibration_claimed": False,
    "automated_e_s_full_calibration_claimed": False,
    "human_e_s_calibration_claimed": False,
    "downstream_agent_value_proven": False,
    "live_llm_agent": False,
    "provider_calls_made": False,
    "remote_provider_calls_made": False,
    "external_benchmark_performance_claimed": False,
    "leaderboard_entry_claimed": False,
    "promotion_ready": False,
    "default_should_change": False,
    "runtime_behavior_changed": False,
    "retriever_changed": False,
    "pack_builder_changed": False,
    "backend_changed": False,
    "default_policy_changed": False,
    "evidencecore_semantics_changed": False,
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
# Fixed failure-category enum.
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES: tuple[str, ...] = tuple(
    "label_context_parse_failed"
    if category == "gold_context_parse_failed"
    else category
    for category in c5.FAILURE_CATEGORIES
)

# ---------------------------------------------------------------------------
# Public artifact scanner (strict, fail-closed). Reuses C5-A scanner
# patterns; adds F1-B-specific forbidden keys (winner/best/default).
# ---------------------------------------------------------------------------

# Extend C5-A forbidden keys with F1-B-specific terms.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    c5.FORBIDDEN_KEY_NAMES
    | {
        # No winner/best/recommended-default fields.
        "winner", "best", "best_variant", "best_method",
        "recommended_default", "preferred_variant", "preferred_method",
        "best_arm", "best_family",
        # No raw model routing prefix keys.
        "model_id_raw", "routing_prefix",
        # No E/S calibration notation.
        "E_primary", "S_support", "e_score", "s_score",
    }
)

# Known-safe provenance value paths.
SAFE_VALUE_KEY_NAMES: frozenset[str] = frozenset(
    c5.SAFE_VALUE_KEY_NAMES
    | {
        "variant",
        "baseline_variant",
        "treatment_variant",
        "effect_name",
        "metric",
    }
)

# Schema-key container keys whose child keys are fixed schema-only
# category labels (NOT row-level values).
SCHEMA_KEY_CONTAINER_KEYS: frozenset[str] = frozenset(
    c5.SCHEMA_KEY_CONTAINER_KEYS
    | {
        "failure_category_counts",
        "variant_failure_category_counts",
    }
)

# Reuse C5-A value patterns.
_RE_URL_VALUE = c5._RE_URL_VALUE
_RE_HEX_DIGEST = c5._RE_HEX_DIGEST
_RE_SECRET_LIKE = c5._RE_SECRET_LIKE
_RE_FILE_PATH_VALUE = c5._RE_FILE_PATH_VALUE
_RE_LINE_RANGE_VALUE = c5._RE_LINE_RANGE_VALUE
_RE_RAW_JSON = c5._RE_RAW_JSON
_RE_TMP_PATH_VALUE = c5._RE_TMP_PATH_VALUE
_RE_TASK_ID_VALUE = c5._RE_TASK_ID_VALUE
_RE_PATCH_MARKER = c5._RE_PATCH_MARKER
_RE_STACK_TRACE = c5._RE_STACK_TRACE
_RE_COMMIT_SHA_VALUE = c5._RE_COMMIT_SHA_VALUE
_RE_REPO_SLUG_VALUE = c5._RE_REPO_SLUG_VALUE
_RE_RAW_MODEL_PREFIX = re.compile(r"\[mk\]", re.IGNORECASE)

_SECRET_SENTINEL = c5._SECRET_SENTINEL
_ROUTING_PREFIX_SENTINEL = "[" + "m" + "k]"


def _path_last_key(path: str) -> str:
    last = path.rsplit(".", 1)[-1]
    return last.split("[")[0]


def _is_safe_value_path(path: str) -> bool:
    return _path_last_key(path) in SAFE_VALUE_KEY_NAMES


def _is_schema_key_container(path: str) -> bool:
    for seg in path.split("."):
        base = seg.split("[")[0]
        if base in SCHEMA_KEY_CONTAINER_KEYS:
            return True
    return False


def _scan_forbidden(obj: Any, path: str = "$") -> list[dict[str, Any]]:
    """Strict recursive scanner for public artifact JSON."""
    violations: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            sub_path = f"{path}.{key_str}"
            if (
                key_str in FORBIDDEN_KEY_NAMES
                and not _is_schema_key_container(sub_path)
            ):
                violations.append(
                    {"category": "forbidden_key", "path": sub_path}
                )
            violations.extend(_scan_forbidden(value, sub_path))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        safe_value = _is_safe_value_path(path)
        if obj in FORBIDDEN_KEY_NAMES and not _is_schema_key_container(path):
            violations.append(
                {"category": "forbidden_field_name_value", "path": path}
            )
        elif len(obj) > 256:
            violations.append({"category": "long_string", "path": path})
        elif _RE_URL_VALUE.search(obj) and not safe_value:
            violations.append({"category": "url_value", "path": path})
        elif not safe_value and _RE_HEX_DIGEST.search(obj):
            violations.append(
                {"category": "hex_digest_value", "path": path}
            )
        elif not safe_value and _RE_COMMIT_SHA_VALUE.search(obj):
            violations.append(
                {"category": "commit_sha_value", "path": path}
            )
        elif _RE_SECRET_LIKE.search(obj) and not safe_value:
            violations.append({"category": "secret_like_value", "path": path})
        elif not safe_value and _RE_FILE_PATH_VALUE.search(obj):
            violations.append({"category": "path_like_value", "path": path})
        elif "\n" in obj:
            violations.append({"category": "multiline_value", "path": path})
        elif _RE_RAW_JSON.search(obj):
            violations.append(
                {"category": "raw_json_fragment", "path": path}
            )
        elif not safe_value and _RE_TMP_PATH_VALUE.search(obj):
            violations.append(
                {"category": "tmp_path_value", "path": path}
            )
        elif not safe_value and _RE_TASK_ID_VALUE.search(obj):
            violations.append(
                {"category": "task_identifier_value", "path": path}
            )
        elif _RE_PATCH_MARKER.search(obj):
            violations.append(
                {"category": "patch_marker_value", "path": path}
            )
        elif _RE_STACK_TRACE.search(obj):
            violations.append(
                {"category": "stack_trace_value", "path": path}
            )
        elif _RE_RAW_MODEL_PREFIX.search(obj):
            violations.append(
                {"category": "raw_model_prefix_value", "path": path}
            )
        elif _SECRET_SENTINEL in obj:
            violations.append({"category": "sentinel_value", "path": path})
        elif not safe_value and _RE_REPO_SLUG_VALUE.search(obj):
            violations.append(
                {"category": "repo_slug_value", "path": path}
            )
        else:
            stripped_val = obj.strip()
            if (
                3 <= len(stripped_val) <= 16
                and _RE_LINE_RANGE_VALUE.fullmatch(stripped_val)
                and not stripped_val.replace(" ", "").isdigit()
            ):
                violations.append(
                    {"category": "line_range_value", "path": path}
                )
    return violations


def _forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_forbidden(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_no_forbidden(obj: Any) -> None:
    scan = _forbidden_scan_summary(obj)
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


def _self_test_category_summary(
    checks: list[dict[str, Any]],
) -> dict[str, int]:
    passed = sum(1 for c in checks if c.get("passed"))
    return {
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
    }


def _round_metric(value: float) -> float:
    return round(float(value), 6)


# ---------------------------------------------------------------------------
# Variant metric extraction and aggregation
# ---------------------------------------------------------------------------


def _extract_variant_metrics(
    score_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract the F1-B allowlisted metrics from a score.py result.

    For ``baseline_empty_candidate_set`` (no retrieval), all metrics
    are zero (empty candidate set has no recall/mrr/span_f0.5/success).
    """
    if score_metrics is None:
        return {name: 0.0 for name in METRIC_NAMES}
    result: dict[str, Any] = {}
    for name in METRIC_NAMES:
        val = score_metrics.get(name)
        if isinstance(val, bool):
            result[name] = 1.0 if val else 0.0
        elif isinstance(val, (int, float)):
            result[name] = _round_metric(float(val))
        else:
            result[name] = 0.0
    return result


def _aggregate_variant_metrics(
    per_row_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-row metrics into per-variant means."""
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


def _compute_counterfactual_effects(
    variant_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute counterfactual effects as fixed records.

    Each record: ``{baseline_variant, treatment_variant, effect_name,
    metric, delta}``.
    """
    variant_map = {r["variant"]: r for r in variant_results}
    effects: list[dict[str, Any]] = []
    for effect_name, (treatment, baseline) in EFFECT_VARIANT_PAIRS.items():
        t_metrics = variant_map.get(treatment, {})
        b_metrics = variant_map.get(baseline, {})
        for metric in METRIC_NAMES:
            t_val = t_metrics.get(metric, 0.0)
            b_val = b_metrics.get(metric, 0.0)
            effects.append(
                {
                    "baseline_variant": baseline,
                    "treatment_variant": treatment,
                    "effect_name": effect_name,
                    "metric": metric,
                    "delta": _round_metric(
                        float(t_val) - float(b_val)
                    ),
                }
            )
    return effects


# ---------------------------------------------------------------------------
# Network smoke runner (transient /tmp; aggregate-only output).
# ---------------------------------------------------------------------------


def _run_network_smoke(
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
    """Run the real network smoke (transient /tmp; aggregate-only output)."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    network_calls = 0

    # Step 1: fetch rows from HF datasets-server.
    rows, fetch_status, nc, fcc_update = c5._fetch_contextbench_rows(
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
    rows_evaluated = 0
    rows_successful = 0
    rows_failed = 0

    # per_variant_per_row_metrics[variant] = list of per-row metric dicts.
    per_variant_per_row_metrics: dict[str, list[dict[str, Any]]] = {
        v: [] for v in VARIANTS
    }
    # per_method_inputs[method] = count of rows that used this method.
    per_method_inputs: dict[str, int] = {m: 0 for m in methods}
    # per_variant_failure_counts[variant] = dict of failure counts.
    per_variant_failure_counts: dict[str, dict[str, int]] = {
        v: {c: 0 for c in FAILURE_CATEGORIES} for v in VARIANTS
    }

    with tempfile.TemporaryDirectory(
        prefix="f1b_smoke_"
    ) as work_root_str:
        work_root = Path(work_root_str)
        tasks_jsonl = work_root / "tasks.jsonl"
        labels_jsonl = work_root / "labels.jsonl"
        run_jsonl = work_root / "run.jsonl"

        for idx, row in enumerate(rows):
            rows_evaluated += 1
            # Parse gold_context (transient).
            gold_paths, gold_lines, gc_status = c5._parse_gold_context(
                row.get("gold_context")
            )
            if gc_status != "pass":
                fcc["label_context_parse_failed"] += 1
                for v in VARIANTS:
                    per_variant_failure_counts[v][
                        "label_context_parse_failed"
                    ] += 1
                rows_failed += 1
                continue

            # Sanitize query (transient).
            query = c5._sanitize_query(
                row.get("problem_statement", ""), query_mode
            )
            if not query:
                fcc["row_parse_failed"] += 1
                for v in VARIANTS:
                    per_variant_failure_counts[v][
                        "row_parse_failed"
                    ] += 1
                rows_failed += 1
                continue

            repo_url = row.get("repo_url", "")
            base_commit = row.get("base_commit", "")
            if not isinstance(repo_url, str) or not isinstance(
                base_commit, str
            ) or not repo_url or not base_commit:
                fcc["row_parse_failed"] += 1
                for v in VARIANTS:
                    per_variant_failure_counts[v][
                        "row_parse_failed"
                    ] += 1
                rows_failed += 1
                continue

            # Materialize repo under a per-row TemporaryDirectory.
            with tempfile.TemporaryDirectory(
                prefix=f"f1b_repo_{idx}_"
            ) as repo_root_str:
                repo_work_dir = Path(repo_root_str)
                clone_ok, clone_fail_cat, clone_fcc = (
                    c5._clone_and_checkout(
                        repo_url, base_commit, repo_work_dir
                    )
                )
                for k, v in clone_fcc.items():
                    if k in fcc:
                        fcc[k] += v
                if not clone_ok:
                    fcc[clone_fail_cat] += 1
                    for variant in VARIANTS:
                        per_variant_failure_counts[variant][
                            clone_fail_cat
                        ] += 1
                    rows_failed += 1
                    continue

                repo_root = repo_work_dir / "repo"

                # Write transient task/label JSONL for this single row.
                task_id = f"row_{idx}"
                task_record = {
                    "task_id": task_id,
                    "query": query,
                }
                label_record = {
                    "task_id": task_id,
                    "gold_paths": gold_paths,
                    "gold_lines": gold_lines,
                }
                try:
                    c5._write_transient_jsonl(
                        tasks_jsonl, [task_record]
                    )
                    c5._write_transient_jsonl(
                        labels_jsonl, [label_record]
                    )
                except OSError:
                    fcc["task_jsonl_write_failed"] += 1
                    rows_failed += 1
                    continue

                # Run retrieval + score for each method.
                method_metrics: dict[str, dict[str, Any] | None] = {}
                for method in methods:
                    per_method_inputs[method] += 1
                    metrics, score_fail_cat, score_fcc = (
                        c5._run_retrieval_and_score(
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
                        fcc[score_fail_cat] += 1
                        method_metrics[method] = None
                    else:
                        method_metrics[method] = c5._filter_score_metrics(
                            metrics
                        )

                # Build per-variant metrics for this row.
                # baseline_empty_candidate_set: all metrics zero.
                per_variant_per_row_metrics[
                    "baseline_empty_candidate_set"
                ].append(_extract_variant_metrics(None))
                # bm25_topk / regex_topk / symbol_topk: from method results.
                per_variant_per_row_metrics["bm25_topk"].append(
                    _extract_variant_metrics(
                        method_metrics.get("bm25")
                    )
                )
                per_variant_per_row_metrics["regex_topk"].append(
                    _extract_variant_metrics(
                        method_metrics.get("regex")
                    )
                )
                per_variant_per_row_metrics["symbol_topk"].append(
                    _extract_variant_metrics(
                        method_metrics.get("symbol")
                    )
                )
                # bm25_plus_symbol_topk: max of bm25 and symbol metrics
                # (union candidate set; approximate aggregation).
                bm25_m = method_metrics.get("bm25")
                symbol_m = method_metrics.get("symbol")
                union_metrics: dict[str, Any] = {}
                if bm25_m or symbol_m:
                    for name in METRIC_NAMES:
                        vals = []
                        if bm25_m and isinstance(
                            bm25_m.get(name), (int, float)
                        ):
                            vals.append(float(bm25_m[name]))
                        if symbol_m and isinstance(
                            symbol_m.get(name), (int, float)
                        ):
                            vals.append(float(symbol_m[name]))
                        union_metrics[name] = (
                            max(vals) if vals else 0.0
                        )
                else:
                    union_metrics = {
                        name: 0.0 for name in METRIC_NAMES
                    }
                per_variant_per_row_metrics[
                    "bm25_plus_symbol_topk"
                ].append(_extract_variant_metrics(union_metrics))

                rows_successful += 1

            # Cleanup the per-row run.jsonl for the next iteration.
            try:
                run_jsonl.unlink()
            except OSError:
                pass

    if rows_successful == 0:
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
            rows_evaluated=rows_evaluated,
            rows_successful=rows_successful,
            rows_failed=rows_failed,
            network_calls=network_calls,
            failure_category_counts=fcc,
        )

    # Aggregate per-variant metrics.
    variant_results: list[dict[str, Any]] = []
    for variant in VARIANTS:
        per_row = per_variant_per_row_metrics[variant]
        agg = _aggregate_variant_metrics(per_row)
        variant_results.append(
            {
                "variant": variant,
                "row_count": agg["row_count"],
                "file_recall@10": agg["file_recall@10"],
                "mrr": agg["mrr"],
                "span_f0.5@10": agg["span_f0.5@10"],
                "success_rate": agg["success_rate"],
                "failure_category_counts": per_variant_failure_counts[
                    variant
                ],
            }
        )

    # Compute counterfactual effects.
    counterfactual_effects = _compute_counterfactual_effects(
        variant_results
    )

    # Build method_inputs records.
    method_inputs = [
        {
            "method": method,
            "row_count": per_method_inputs.get(method, 0),
        }
        for method in methods
    ]

    # Determine status: pass if all variants have >=1 row, else partial.
    all_variants_have_rows = all(
        r["row_count"] > 0 for r in variant_results
    )
    status = STATUS_PASS if all_variants_have_rows else STATUS_PARTIAL

    return _build_pass_report(
        self_test_passed=self_test_passed,
        row_limit_requested=row_limit,
        rows_fetched=rows_fetched,
        rows_evaluated=rows_evaluated,
        rows_successful=rows_successful,
        rows_failed=rows_failed,
        methods=methods,
        query_mode=query_mode,
        language_filter=language_filter,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
        variant_results=variant_results,
        counterfactual_effects=counterfactual_effects,
        method_inputs=method_inputs,
        failure_category_counts=fcc,
        partial=(status == STATUS_PARTIAL),
        status=status,
    )


# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


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
    rows_evaluated: int = 0,
    rows_successful: int = 0,
    rows_failed: int = 0,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a truthful ``unavailable_with_reason`` report."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    if failure_category_counts:
        for k, v in failure_category_counts.items():
            if k in fcc:
                fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = rows_fetched > 0
    safe_true["openlocus_retrieval_executed"] = rows_successful > 0
    safe_true["score_py_metrics_computed"] = False
    safe_true["retrieval_derived_counterfactual_utility_smoke"] = False

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": STATUS_UNAVAILABLE,
        "mode": MODE,
        "phase": PHASE,
        "methods": list(methods),
        "query_mode": query_mode,
        "language_filter": language_filter,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "row_limit_requested": row_limit_requested,
        "rows_fetched": rows_fetched,
        "rows_evaluated": rows_evaluated,
        "rows_successful": rows_successful,
        "rows_failed": rows_failed,
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_reason_category": failure_reason_category,
        "failure_category_counts": fcc,
        "variant_results": [],
        "counterfactual_effects": [],
        "method_inputs": [],
        "input_summary": {
            "row_limit_requested": row_limit_requested,
            "methods": list(methods),
            "query_mode": query_mode,
            "language_filter": language_filter,
            "variants": list(VARIANTS),
            "effects": list(EFFECTS),
            "metrics": list(METRIC_NAMES),
            "rows_fetched": rows_fetched,
            "rows_evaluated": rows_evaluated,
            "rows_successful": rows_successful,
            "rows_failed": rows_failed,
            "network_calls": network_calls,
        },
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
            "signal_strength": "retrieval_derived_counterfactual_utility_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_true_e_s_calibration": False,
        },
    }

    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


def _build_pass_report(
    *,
    self_test_passed: bool,
    row_limit_requested: int,
    rows_fetched: int,
    rows_evaluated: int,
    rows_successful: int,
    rows_failed: int,
    methods: list[str],
    query_mode: str,
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
    variant_results: list[dict[str, Any]],
    counterfactual_effects: list[dict[str, Any]],
    method_inputs: list[dict[str, Any]],
    failure_category_counts: dict[str, int],
    partial: bool,
    status: str,
) -> dict[str, Any]:
    """Build a pass/partial report with aggregate metrics."""
    fcc = {c: 0 for c in FAILURE_CATEGORIES}
    for k, v in failure_category_counts.items():
        if k in fcc:
            fcc[k] = int(v)

    safe_true = dict(SAFE_TRUE_FLAGS)
    safe_true["external_benchmark_rows_read"] = rows_fetched > 0
    safe_true["openlocus_retrieval_executed"] = rows_successful > 0
    safe_true["score_py_metrics_computed"] = rows_successful > 0
    safe_true["retrieval_derived_counterfactual_utility_smoke"] = (
        rows_successful > 0
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "methods": list(methods),
        "query_mode": query_mode,
        "language_filter": language_filter,
        "network_mode": network_mode,
        "openlocus_binary_source": openlocus_binary_source,
        "row_limit_requested": row_limit_requested,
        "rows_fetched": rows_fetched,
        "rows_evaluated": rows_evaluated,
        "rows_successful": rows_successful,
        "rows_failed": rows_failed,
        "network_calls": network_calls,
        "provider_calls": 0,
        "failure_category_counts": fcc,
        "variant_results": variant_results,
        "counterfactual_effects": counterfactual_effects,
        "method_inputs": method_inputs,
        "input_summary": {
            "row_limit_requested": row_limit_requested,
            "methods": list(methods),
            "query_mode": query_mode,
            "language_filter": language_filter,
            "variants": list(VARIANTS),
            "effects": list(EFFECTS),
            "metrics": list(METRIC_NAMES),
            "rows_fetched": rows_fetched,
            "rows_evaluated": rows_evaluated,
            "rows_successful": rows_successful,
            "rows_failed": rows_failed,
            "network_calls": network_calls,
        },
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
            "signal_strength": "retrieval_derived_counterfactual_utility_smoke_aggregate_only",
            "is_full_external_benchmark_evaluation": False,
            "is_true_e_s_calibration": False,
        },
    }

    scan = _forbidden_scan_summary(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


def build_report(
    *,
    row_limit: int,
    methods: list[str],
    query_mode: str,
    language_filter: str,
    openlocus: str | None,
) -> dict[str, Any]:
    """Assemble the public aggregate-only report.

    Runs self-test, resolves the openlocus binary, and runs the real
    network smoke. On any failure, produces a truthful
    ``unavailable_with_reason`` report.
    """
    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        return _build_unavailable_report(
            "scanner_self_test_failed",
            self_test_passed=False,
            row_limit_requested=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )

    openlocus_bin, openlocus_source = c5._resolve_openlocus_binary(
        openlocus
    )
    if openlocus_bin is None:
        return _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            row_limit_requested=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_network_smoke(
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
    return report


# ---------------------------------------------------------------------------
# Self-test checks (no network; uses synthetic data)
# ---------------------------------------------------------------------------


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all F1-B self-test groups (no network)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    skeleton = _build_unavailable_report(
        "network_fetch_failed",
        self_test_passed=True,
        row_limit_requested=ROW_LIMIT_DEFAULT,
        methods=list(ALLOWED_METHODS),
        query_mode="first_paragraph",
        language_filter="python",
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

    # --- Group 3: No-claim flags false. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"default_false_{flag}",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 4: Variants and effects are fixed allowlists. ---
    checks.append(
        _check(
            "variants_are_fixed_allowlist",
            tuple(skeleton["input_summary"]["variants"]) == VARIANTS,
        )
    )
    checks.append(
        _check(
            "effects_are_fixed_allowlist",
            tuple(skeleton["input_summary"]["effects"]) == EFFECTS,
        )
    )
    checks.append(
        _check(
            "metrics_are_fixed_allowlist",
            tuple(skeleton["input_summary"]["metrics"]) == METRIC_NAMES,
        )
    )
    # All five variants present.
    for variant in VARIANTS:
        checks.append(
            _check(
                f"variant_present_{variant}",
                variant in skeleton["input_summary"]["variants"],
            )
        )
    # All four effects present.
    for effect in EFFECTS:
        checks.append(
            _check(
                f"effect_present_{effect}",
                effect in skeleton["input_summary"]["effects"],
            )
        )

    # --- Group 5: Records-shaped containers. ---
    checks.append(
        _check(
            "variant_results_is_list",
            isinstance(skeleton["variant_results"], list),
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
            "method_inputs_is_list",
            isinstance(skeleton["method_inputs"], list),
        )
    )
    # No dynamic dict keyed by method/variant for results/effects.
    checks.append(
        _check(
            "no_dynamic_dict_mirror_for_variants",
            not any(
                isinstance(v, dict) and all(
                    isinstance(k, str) and k in VARIANTS
                    for k in v.keys()
                )
                for v in [skeleton.get("variant_results")]
                if isinstance(v, dict)
            ),
        )
    )

    # --- Group 6: Variant metric extraction. ---
    # Empty candidate set -> all metrics zero.
    empty_metrics = _extract_variant_metrics(None)
    checks.append(
        _check(
            "empty_candidate_set_metrics_zero",
            all(v == 0.0 for v in empty_metrics.values()),
        )
    )
    # Synthetic score metrics.
    synth_score = {
        "file_recall@10": 0.5,
        "mrr": 0.3,
        "span_f0.5@10": 0.2,
        "success_rate": 1.0,
    }
    extracted = _extract_variant_metrics(synth_score)
    checks.append(
        _check(
            "extract_metrics_from_score",
            extracted["file_recall@10"] == 0.5
            and extracted["mrr"] == 0.3
            and extracted["success_rate"] == 1.0,
        )
    )
    # Missing metric -> 0.0.
    partial_score = {"file_recall@10": 0.7}
    extracted_partial = _extract_variant_metrics(partial_score)
    checks.append(
        _check(
            "missing_metric_defaults_zero",
            extracted_partial["mrr"] == 0.0
            and extracted_partial["file_recall@10"] == 0.7,
        )
    )

    # --- Group 7: Variant aggregation. ---
    per_row = [
        {"file_recall@10": 0.5, "mrr": 0.3, "span_f0.5@10": 0.2, "success_rate": 1.0},
        {"file_recall@10": 1.0, "mrr": 0.6, "span_f0.5@10": 0.4, "success_rate": 1.0},
    ]
    agg = _aggregate_variant_metrics(per_row)
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

    # --- Group 8: Counterfactual effects computation. ---
    variant_results_synth = [
        {
            "variant": "baseline_empty_candidate_set",
            "row_count": 2,
            "file_recall@10": 0.0, "mrr": 0.0,
            "span_f0.5@10": 0.0, "success_rate": 0.0,
        },
        {
            "variant": "bm25_topk",
            "row_count": 2,
            "file_recall@10": 0.75, "mrr": 0.45,
            "span_f0.5@10": 0.3, "success_rate": 1.0,
        },
        {
            "variant": "regex_topk",
            "row_count": 2,
            "file_recall@10": 0.5, "mrr": 0.25,
            "span_f0.5@10": 0.2, "success_rate": 0.5,
        },
        {
            "variant": "symbol_topk",
            "row_count": 2,
            "file_recall@10": 0.6, "mrr": 0.35,
            "span_f0.5@10": 0.25, "success_rate": 0.5,
        },
        {
            "variant": "bm25_plus_symbol_topk",
            "row_count": 2,
            "file_recall@10": 0.8, "mrr": 0.5,
            "span_f0.5@10": 0.35, "success_rate": 1.0,
        },
    ]
    effects = _compute_counterfactual_effects(variant_results_synth)
    checks.append(
        _check(
            "effects_records_shaped",
            all(
                set(e.keys()) == {
                    "baseline_variant", "treatment_variant",
                    "effect_name", "metric", "delta"
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
    # bm25_candidates_vs_empty: bm25 - baseline = 0.75.
    bm25_effect = next(
        e for e in effects
        if e["effect_name"] == "bm25_candidates_vs_empty"
        and e["metric"] == "file_recall@10"
    )
    checks.append(
        _check(
            "bm25_vs_empty_delta_correct",
            bm25_effect["delta"] == 0.75,
        )
    )
    # symbol_added_to_bm25: bm25_plus_symbol - bm25 = 0.8 - 0.75 = 0.05.
    symbol_added = next(
        e for e in effects
        if e["effect_name"] == "symbol_added_to_bm25"
        and e["metric"] == "file_recall@10"
    )
    checks.append(
        _check(
            "symbol_added_to_bm25_delta_correct",
            symbol_added["delta"] == 0.05,
        )
    )

    # --- Group 9: Scanner rejections. ---
    checks.append(
        _check(
            "scanner_rejects_repo_url",
            bool(_scan_forbidden({"leaked": "https://github.com/x/y"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_forbidden({"leaked_file": "target.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha",
            bool(_scan_forbidden({"leaked": "a" * 40})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug",
            bool(_scan_forbidden({"leaked": "astropy/astropy"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_task_id_key",
            bool(_scan_forbidden({"task_id": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_query_key",
            bool(_scan_forbidden({"query": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_gold_key",
            bool(_scan_forbidden({"gold": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_content_sha_key",
            bool(_scan_forbidden({"content_sha": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_candidate_key",
            bool(_scan_forbidden({"candidate": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_evidence_key",
            bool(_scan_forbidden({"evidence": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_winner_key",
            bool(_scan_forbidden({"winner": "bm25_topk"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_best_key",
            bool(_scan_forbidden({"best": "bm25_topk"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_recommended_default_key",
            bool(_scan_forbidden({"recommended_default": "bm25_topk"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_raw_routing_prefix",
            bool(_scan_forbidden({"leaked": _ROUTING_PREFIX_SENTINEL + "Kimi"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_url_value",
            bool(_scan_forbidden({"leaked": "https://example.com"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_tmp_path",
            bool(_scan_forbidden({"leaked": "/tmp/f1b_smoke_0"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_stdout_key",
            bool(_scan_forbidden({"stdout": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_provider_key",
            bool(_scan_forbidden({"api_key": "abc"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_secret_sentinel",
            bool(_scan_forbidden({"leaked": _SECRET_SENTINEL})),
        )
    )

    # --- Group 10: Scanner allows legitimate aggregate values. ---
    checks.append(
        _check(
            "scanner_allows_variant_name",
            not _scan_forbidden({"variant": "bm25_topk"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_effect_name",
            not _scan_forbidden({"effect_name": "bm25_candidates_vs_empty"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_metric_name",
            not _scan_forbidden({"metric": "file_recall@10"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_method_name",
            not _scan_forbidden({"method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_variant_results_records",
            not _scan_forbidden(
                {
                    "variant_results": [
                        {
                            "variant": "symbol_topk",
                            "row_count": 5,
                            "file_recall@10": 0.6,
                            "mrr": 0.35,
                            "span_f0.5@10": 0.25,
                            "success_rate": 0.5,
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_counterfactual_effects_records",
            not _scan_forbidden(
                {
                    "counterfactual_effects": [
                        {
                            "baseline_variant": "baseline_empty_candidate_set",
                            "treatment_variant": "bm25_topk",
                            "effect_name": "bm25_candidates_vs_empty",
                            "metric": "mrr",
                            "delta": 0.45,
                        }
                    ]
                }
            ),
        )
    )
    checks.append(
        _check(
            "scanner_allows_failure_category_token",
            not _scan_forbidden({"failure_category": "pass"}),
        )
    )

    # --- Group 11: Fail-closed generation. ---
    try:
        _enforce_no_forbidden(skeleton)
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
        _enforce_no_forbidden(leaked_report)
        leak_raises = False
    except SystemExit:
        leak_raises = True
    checks.append(
        _check("fail_closed_raises_on_leak", leak_raises)
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

    # --- Group 12: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_report_forbidden_scan_clean",
            skeleton["forbidden_scan"]["status"] == "pass",
        )
    )
    checks.append(
        _check(
            "public_report_no_forbidden_key_anywhere",
            not any(
                _has_dict_key_anywhere(skeleton, bad)
                for bad in (
                    "task_id", "repo_url", "base_commit", "query",
                    "gold_paths", "gold_lines", "gold_context",
                    "path", "file", "snippet", "code", "patch",
                    "diff", "stdout", "stderr", "content_sha",
                    "candidate", "evidence", "winner", "best",
                    "recommended_default", "api_key", "base_url",
                    "provider_key", "secret", "token",
                    "model_id_raw", "E_primary", "S_support",
                )
            ),
        )
    )

    # --- Group 13: CLI argument surface. ---
    cli_opts = _cli_argument_option_strings()
    checks.append(
        _check("cli_has_self_test_argument", "--self-test" in cli_opts)
    )
    checks.append(_check("cli_has_out_argument", "--out" in cli_opts))
    checks.append(
        _check("cli_has_row_limit_argument", "--row-limit" in cli_opts)
    )
    checks.append(
        _check("cli_has_methods_argument", "--methods" in cli_opts)
    )
    checks.append(
        _check("cli_has_query_mode_argument", "--query-mode" in cli_opts)
    )
    checks.append(
        _check(
            "cli_has_language_filter_argument",
            "--language-filter" in cli_opts,
        )
    )
    checks.append(
        _check(
            "cli_has_openlocus_argument",
            "--openlocus" in cli_opts,
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args."""

    def error(self, message: str) -> NoReturn:  # noqa: D401
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    ap = SafeArgumentParser(
        description=(
            "F1-B retrieval-derived counterfactual utility smoke "
            "(public aggregate-only artifact; bounded ContextBench "
            "verified rows; transient /tmp clone + retrieval + score; "
            "no provider calls; no raw rows/queries/repo URLs/commits/"
            "gold paths/spans/candidates/stdout/stderr committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run no-network self-test and exit (no artifact written)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="output artifact JSON path",
    )
    ap.add_argument(
        "--row-limit",
        type=int,
        default=ROW_LIMIT_DEFAULT,
        help=(
            f"number of ContextBench rows (default {ROW_LIMIT_DEFAULT}; "
            f"hard cap {ROW_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--methods",
        default=DEFAULT_METHODS,
        help=f"comma-separated methods (default: {DEFAULT_METHODS})",
    )
    ap.add_argument(
        "--query-mode",
        default=c5.DEFAULT_QUERY_MODE,
        choices=c5.ALLOWED_QUERY_MODES,
        help=f"query mode (default: {c5.DEFAULT_QUERY_MODE})",
    )
    ap.add_argument(
        "--language-filter",
        default=c5.DEFAULT_LANGUAGE_FILTER,
        choices=c5.ALLOWED_LANGUAGE_FILTERS,
        help=f"language filter (default: {c5.DEFAULT_LANGUAGE_FILTER})",
    )
    ap.add_argument(
        "--openlocus",
        default=None,
        help="OpenLocus binary path (default: target/release/openlocus)",
    )
    return ap


def _cli_argument_option_strings() -> set[str]:
    parser = build_parser()
    strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            strings.add(opt)
    return strings


def _validate_row_limit(row_limit: int) -> int:
    if not isinstance(row_limit, int):
        raise SystemExit("invalid arguments")
    if row_limit < 1:
        raise SystemExit("invalid arguments")
    if row_limit > ROW_LIMIT_HARD_CAP:
        return ROW_LIMIT_HARD_CAP
    return row_limit


def _validate_methods(methods_str: str) -> list[str]:
    methods = [m.strip() for m in methods_str.split(",") if m.strip()]
    if not methods:
        raise SystemExit("invalid arguments")
    for m in methods:
        if m not in ALLOWED_METHODS:
            raise SystemExit("invalid arguments")
    return methods


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

    row_limit = _validate_row_limit(args.row_limit)
    methods = _validate_methods(args.methods)
    query_mode = args.query_mode
    language_filter = args.language_filter
    out_path = args.out if args.out is not None else DEFAULT_OUT

    try:
        report = build_report(
            row_limit=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus=args.openlocus,
        )
    except (OSError, subprocess.SubprocessError):
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=False,
            row_limit_requested=row_limit,
            methods=methods,
            query_mode=query_mode,
            language_filter=language_filter,
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )

    _enforce_no_forbidden(report)
    _refuse_on_self_test_failure(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"rows_fetched={report['rows_fetched']}, "
        f"rows_successful={report['rows_successful']})"
    )


if __name__ == "__main__":
    main()
